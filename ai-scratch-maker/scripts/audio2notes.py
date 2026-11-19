#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把音频（WAV）转成乐器能演奏的音符序列 —— 「音频 → 乐器音乐」的转换器。

用途：手里只有一段旋律的音频（自己录的、网上下的一段），想用 Scratch 的乐器扩展
重新演奏它（换音色、变速、加声部）。本脚本把音频分析成「音高 + 时长」列表，
直接喂给 `设定乐器为 … / 演奏音符 … 拍` 即可。

算法（纯 Python，不依赖 numpy / scipy）：

    ① 读 WAV → 单声道浮点 → 降采样到 8 kHz（基频检测不需要高频）
    ② 分帧：帧长 512（64 ms），跳步 256（32 ms，50% 重叠）
    ③ 每帧做**自相关**，在 lag ∈ [rate/1200, rate/60] 里找第一个显著峰
       → 峰值位置做**抛物线插值**，把 lag 精度提到 0.01 样本
    ④ f0 = rate / lag；MIDI = round(69 + 12·log2(f0/440))
    ⑤ 中值滤波（窗口 5）去掉倍频/半频毛刺
    ⑥ 音符切分：连续相同 MIDI 且时长 ≥ 60 ms 才算一个音
    ⑦ 量化到拍：拍数 = round(时长 / (60/BPM) / 0.25) × 0.25

用法:
    python scripts/audio2notes.py 输入.wav                    # 打印音符表
    python scripts/audio2notes.py 输入.wav --json out.json    # 存 JSON
    python scripts/audio2notes.py 输入.wav --scratch          # 打印可粘进 IR 的列表
    python scripts/audio2notes.py --selftest                  # 自测（生成已知旋律再识别）
"""
import argparse
import json
import math
import os
import struct
import sys
import wave

# ---------------------------------------------------------------- 参数
DST_RATE = 8000        # 分析采样率
FRAME = 256            # 帧长（样本，32 ms @8k）
HOP = 128              # 跳步（50% 重叠）
F_MIN = 60.0           # 最低检测频率（Hz）
F_MAX = 1200.0         # 最高检测频率（Hz）
PEAK_RATIO = 0.45      # 自相关峰值阈值（相对最大值）
MIN_NOTE_MS = 60       # 短于这个时长的「音」当噪声丢掉
SILENCE_RMS = 0.004    # 低于这个 RMS 当静音

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# 简谱（C 大调）：MIDI 相对 C 的半音 → 简谱数字
SEMI_TO_JIANPU = {0: "1", 2: "2", 4: "3", 5: "4", 7: "5", 9: "6", 11: "7"}


# ---------------------------------------------------------------- 读与降采样
def read_wav_mono(path):
    """返回 (samples float list in [-1,1], rate)。支持 8/16/32bit、单/双声道。"""
    with wave.open(path, "rb") as w:
        ch = w.getnchannels()
        sw = w.getsampwidth()
        rate = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        vals = struct.unpack("<%dh" % (len(raw) // 2), raw)
        samples = [v / 32768.0 for v in vals]
    elif sw == 1:
        samples = [(b - 128) / 128.0 for b in raw]
    elif sw == 4:
        vals = struct.unpack("<%di" % (len(raw) // 4), raw)
        samples = [v / 2147483648.0 for v in vals]
    else:
        raise ValueError("不支持的位深: %d bit" % (sw * 8))

    if ch > 1:
        mono = []
        for i in range(0, len(samples), ch):
            chunk = samples[i:i + ch]
            mono.append(sum(chunk) / len(chunk))
        samples = mono
    return samples, rate


def downsample(samples, src_rate, dst_rate=DST_RATE):
    """整数倍抽取 + 滑动平均抗混叠。

    不做低通直接抽取会把高频折叠到低频（混叠），检出的音高会偏。
    这里用「窗口 = 抽取倍数」的移动平均做最简低通，够用且 O(n)。
    """
    if src_rate <= dst_rate:
        return samples, src_rate
    step = int(round(src_rate / float(dst_rate)))
    if step < 2:
        return samples, src_rate
    # 移动平均（窗口 = step）
    acc = 0.0
    buf = []
    out = []
    for i, v in enumerate(samples):
        acc += v
        buf.append(v)
        if len(buf) > step:
            acc -= buf.pop(0)
        if i % step == step - 1:
            out.append(acc / step)
    return out, src_rate // step


# ---------------------------------------------------------------- 基频检测
def rms(frame):
    if not frame:
        return 0.0
    return math.sqrt(sum(v * v for v in frame) / len(frame))


def acf_pitch(frame, rate):
    """自相关法估基频。返回 (f0, confidence)；无周期返回 (None, 0)。"""
    n = len(frame)
    mean = sum(frame) / n
    x = [v - mean for v in frame]

    lag_min = max(2, int(rate / F_MAX))
    lag_max = min(n // 2, int(rate / F_MIN))
    if lag_max <= lag_min + 2:
        return None, 0.0

    # 归一化自相关（除以重叠长度，避免长 lag 天然偏小）
    r = []
    for tau in range(lag_min - 1, lag_max + 2):
        if tau <= 0 or tau >= n:
            r.append(0.0)
            continue
        s = 0.0
        for i in range(n - tau):
            s += x[i] * x[i + tau]
        r.append(s / (n - tau))
    if not r:
        return None, 0.0

    rmax = max(r)
    if rmax <= 1e-9:
        return None, 0.0

    # 找「第一个」显著局部峰，而不是全局最大 —— 全局最大常在 2 倍周期处（低八度错误）
    best = None
    for i in range(1, len(r) - 1):
        if r[i] >= r[i - 1] and r[i] >= r[i + 1] and r[i] > PEAK_RATIO * rmax:
            best = i
            break
    if best is None:
        return None, 0.0

    # 抛物线插值：把 lag 精度从 1 个样本提到 ~0.01 个样本
    y0, y1, y2 = r[best - 1], r[best], r[best + 1]
    denom = (y0 - 2 * y1 + y2)
    delta = 0.5 * (y0 - y2) / denom if abs(denom) > 1e-12 else 0.0
    tau = (lag_min - 1) + best + delta
    if tau <= 0:
        return None, 0.0

    f0 = rate / tau
    conf = y1 / rmax
    if f0 < F_MIN * 0.8 or f0 > F_MAX * 1.25:
        return None, 0.0
    return f0, conf


def median_filter(vals, win=5):
    """中值滤波：去倍频跳变。**None 保持 None** —— 静音帧被填平会导致同音高连音被合并。

    这是本脚本踩过的真坑：小星星开头 `C5 C5` 被识别成一个长音，
    因为窗口 5 的中值滤波把中间那帧静音用邻居的 MIDI 值补上了。
    """
    out = []
    half = win // 2
    for i in range(len(vals)):
        if vals[i] is None:
            out.append(None)
            continue
        seg = [v for v in vals[max(0, i - half):i + half + 1] if v is not None]
        seg.sort()
        out.append(seg[len(seg) // 2])
    return out


def hz_to_midi(f):
    return int(round(69 + 12 * math.log(f / 440.0, 2)))


def midi_to_hz(m):
    return 440.0 * (2 ** ((m - 69) / 12.0))


def midi_name(m):
    return "%s%d" % (NOTE_NAMES[m % 12], m // 12 - 1)


def midi_to_jianpu(m):
    """C 大调简谱；非音阶内的音加 #。"""
    semi = m % 12
    if semi in SEMI_TO_JIANPU:
        return SEMI_TO_JIANPU[semi]
    return "#" + SEMI_TO_JIANPU.get((semi - 1) % 12, "?")


# ---------------------------------------------------------------- 主流程
def analyze(path, bpm=120.0):
    samples, rate = read_wav_mono(path)
    samples, rate = downsample(samples, rate)
    if len(samples) < FRAME:
        raise ValueError("音频太短（< %d 样本）" % FRAME)

    # 逐帧基频 + 能量
    f0s, energies = [], []
    for start in range(0, len(samples) - FRAME + 1, HOP):
        frame = samples[start:start + FRAME]
        e = rms(frame)
        energies.append(e)
        if e < SILENCE_RMS:
            f0s.append(None)
            continue
        f, conf = acf_pitch(frame, rate)
        f0s.append(f if conf >= 0.3 else None)

    # 中值滤波 + 转 MIDI
    f0s = median_filter(f0s, 5)
    midis = [hz_to_midi(f) if f else None for f in f0s]

    # 音符切分：MIDI 变化 **或** 能量低谷都算断音。
    # ⚠️ 只靠 MIDI 变化切不开「同音高连音」（C5 C5 会粘成一个长音），
    #    必须用能量包络补一刀。
    live = sorted(e for e in energies if e > SILENCE_RMS)
    e_med = live[len(live) // 2] if live else 0.0
    e_gate = max(SILENCE_RMS, e_med * 0.30)
    frame_ms = 1000.0 * HOP / rate
    notes = []
    cur, cnt = None, 0
    for m, e in list(zip(midis, energies)) + [(None, 0.0)]:
        voiced = m is not None and e >= e_gate
        if voiced and m == cur:
            cnt += 1
        else:
            if cur is not None and cnt * frame_ms >= MIN_NOTE_MS:
                notes.append({"midi": cur, "ms": cnt * frame_ms,
                              "name": midi_name(cur)})
            cur, cnt = (m if voiced else None), 1

    # 量化到拍
    beat_ms = 60000.0 / bpm
    for n in notes:
        beats = n["ms"] / beat_ms
        n["beats"] = max(0.25, round(beats / 0.25) * 0.25)

    return {
        "file": os.path.basename(path),
        "src_rate": rate,
        "frame_ms": round(frame_ms, 1),
        "bpm": bpm,
        "count": len(notes),
        "notes": notes,
    }


def fmt_table(res):
    lines = ["# %s  →  %d 个音（分析帧 %.0f ms，BPM %s）" %
             (res["file"], res["count"], res["frame_ms"], res["bpm"])]
    lines.append("%-6s %-6s %-8s %-8s %s" % ("序号", "音名", "MIDI", "时长(ms)", "拍"))
    for i, n in enumerate(res["notes"], 1):
        lines.append("%-6d %-6s %-8d %-8.0f %s" %
                     (i, n["name"], n["midi"], n["ms"], n["beats"]))
    return "\n".join(lines)


def fmt_scratch(res):
    """输出可以直接粘进 IR / 写进列表的形式。"""
    midis = [n["midi"] for n in res["notes"]]
    beats = [n["beats"] for n in res["notes"]]
    jp = " ".join(midi_to_jianpu(m) for m in midis)
    out = []
    out.append("# 音高表（MIDI）")
    out.append("音高表: [%s]" % ", ".join(str(m) for m in midis))
    out.append("")
    out.append("# 时值表（拍）")
    out.append("时值表: [%s]" % ", ".join(str(b) for b in beats))
    out.append("")
    out.append("# 简谱（C 大调，非音阶内音带 #）")
    out.append(jp)
    out.append("")
    out.append("# 演奏（伪代码，配合第三十二册 §307 的变量换乐器）")
    out.append("设定乐器为 (乐器)")
    for m, b in zip(midis, beats):
        out.append("演奏音符 %d %s 拍" % (m, b))
    return "\n".join(out)


# ---------------------------------------------------------------- 自测
def selftest():
    """闭环自测：用 gen_audio 合成一段已知旋律，再识别回来比对。

    这是本脚本「可信」的唯一证据 —— 不比对就只是「能跑」。
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gen_audio as g
    import tempfile

    cases = [
        ("C 大调音阶", ["C5", "D5", "E5", "F5", "G5"], 0.4),
        ("小星星开头", ["C5", "C5", "G5", "G5", "A5", "A5", "G5"], 0.35),
        ("低音区", ["C4", "E4", "G4"], 0.45),
    ]
    ok = True
    tmpdir = tempfile.mkdtemp(prefix="a2n_")
    for label, names, dur in cases:
        samples = []
        for nm in names:
            samples += g.env(g.osc(g.note_freq(nm), dur, "sine"), attack=0.005, release=0.05)
            samples += g.silence(0.05, g.RATE)   # 音间留一点空隙，便于切分
        path = os.path.join(tmpdir, "t.wav")
        g.write_wav(path, g.normalize(samples, 0.7))

        res = analyze(path, bpm=120)
        got = [n["midi"] for n in res["notes"]]
        want = [int(round(69 + 12 * math.log(g.note_freq(nm) / 440.0, 2))) for nm in names]
        hit = got == want
        if not hit:
            ok = False
        print("[%s] %s" % ("OK " if hit else "FAIL", label))
        print("   期望 %s" % want)
        print("   识别 %s" % got)
    print("\n自测:", "ALL_OK" if ok else "HAS_FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav", nargs="?")
    ap.add_argument("--json", default=None)
    ap.add_argument("--scratch", action="store_true")
    ap.add_argument("--bpm", type=float, default=120.0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.wav:
        ap.print_help()
        return 2

    res = analyze(a.wav, a.bpm)
    if a.scratch:
        print(fmt_scratch(res))
    else:
        print(fmt_table(res))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print("\n已写入 %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
