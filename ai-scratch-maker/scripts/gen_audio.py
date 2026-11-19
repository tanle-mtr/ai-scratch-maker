#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线音频生成 —— agent 自己产出行之有效的 Scratch 音频，**不依赖任何外部服务/API**。

设计取舍
--------
- 只用 Python 标准库（math / wave / struct），零第三方依赖，离线可跑。
- 输出统一的 16-bit PCM 单声道 WAV，Scratch 直接可用。
- 面向「做游戏」的常用需求：音效预设 + 程序化背景音乐（BGM）+ 自由组合。

用法
----
  # 基础波形
  python3 gen_audio.py tone   --freq 440 --dur 0.2 --wave square --out beep.wav
  python3 gen_audio.py sweep  --from-freq 800 --to-freq 300 --dur 0.12 --out swoosh.wav

  # 旋律（音名可用升降号：C4 / D#4 / Eb4 / A3 …，用 : 分隔节奏）
  python3 gen_audio.py melody --notes "C4:1 E4:1 G4:2" --bpm 120 --out jingle.wav

  # 音效预设
  python3 gen_audio.py sfx    --name coin --out coin.wav
  python3 gen_audio.py sfx    --name pop --out pop.wav

  # 背景音乐（循环无缝）
  python3 gen_audio.py bgm    --mood chase --bars 4 --out bgm.wav
  python3 gen_audio.py bgm    --mood happy --bars 2 --out happy.wav

  # 列出所有可用预设
  python3 gen_audio.py list
"""
import argparse
import math
import os
import random
import re
import struct
import wave

RATE = 44100

# ---------------------------------------------------------------- 音名转频率
_NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_freq(name):
    """'C4' / 'D#4' / 'Eb4' / 'A#3' -> 频率(Hz)。"""
    s = str(name).strip().replace("-", "#")
    if not s:
        return 440.0
    letter = s[0].upper()
    if letter not in _NOTE_BASE:
        return 440.0
    i = 1
    semi = _NOTE_BASE[letter]
    while i < len(s) and s[i] in "#b":
        semi += 1 if s[i] == "#" else -1
        i += 1
    octave = 4
    if i < len(s):
        try:
            octave = int(s[i:])
        except ValueError:
            octave = 4
    midi = (octave + 1) * 12 + semi
    return 440.0 * (2 ** ((midi - 69) / 12.0))


# ---------------------------------------------------------------- 波形
def _wave(kind, phase):
    p = phase % 1.0
    if kind == "triangle":
        kind = "tri"
    if kind == "square":
        return 1.0 if p < 0.5 else -1.0
    if kind == "saw":
        return 2.0 * p - 1.0
    if kind == "tri":
        return 4.0 * abs(p - 0.5) - 1.0
    return math.sin(2 * math.pi * p)


def osc(freq, dur, wave_type="sine", rate=RATE, detune=0.0):
    """基础振荡器。detune 为失谐（Hz），用于做出「厚」的合音。"""
    n = int(rate * dur)
    out = []
    ph = 0.0
    ph2 = 0.0
    for i in range(n):
        f = freq(i / n) if callable(freq) else freq
        ph += f / rate
        ph2 += (f + detune) / rate
        v = _wave(wave_type, ph)
        if detune:
            v = 0.6 * v + 0.4 * _wave(wave_type, ph2)
        out.append(v)
    return out


def noise(dur, rate=RATE, decay=True, seed=None):
    rnd = random.Random(seed)
    n = int(rate * dur)
    if decay:
        return [rnd.uniform(-1, 1) * (1 - i / n) ** 1.6 for i in range(n)]
    return [rnd.uniform(-1, 1) for i in range(n)]


def lowpass(samples, cutoff, rate=RATE):
    """一阶低通滤波（可做扫频滤波）。"""
    if callable(cutoff):
        out = []
        prev = 0.0
        for i, s in enumerate(samples):
            fc = max(60.0, min(rate / 2 - 100, cutoff(i / len(samples))))
            a = 1 - math.exp(-2 * math.pi * fc / rate)
            prev += a * (s - prev)
            out.append(prev)
        return out
    a = 1 - math.exp(-2 * math.pi * max(60.0, cutoff) / rate)
    out = []
    prev = 0.0
    for s in samples:
        prev += a * (s - prev)
        out.append(prev)
    return out


def env(samples, rate=RATE, attack=0.005, release=0.04, sustain=1.0):
    """ADSR 简化包络。"""
    n = len(samples)
    a = max(1, int(rate * attack))
    r = max(1, int(rate * release))
    out = list(samples)
    for i in range(min(a, n)):
        out[i] *= i / a
    for i in range(min(r, n)):
        out[n - 1 - i] *= (i / r) ** 0.7
    if sustain != 1.0:
        s_start = min(a, n)
        s_end = max(s_start, n - r)
        for i in range(s_start, s_end):
            out[i] *= sustain
    return out


def mix(*layers):
    """把多层波形混合到同一长度。"""
    n = max(len(l) for l in layers) if layers else 0
    out = [0.0] * n
    for layer in layers:
        for i, s in enumerate(layer):
            out[i] += s
    return out


def seq(*parts):
    """把若干段首尾相接。"""
    out = []
    for p in parts:
        out.extend(p)
    return out


def silence(dur, rate=RATE):
    return [0.0] * int(rate * dur)


def normalize(samples, peak=0.85):
    m = max((abs(s) for s in samples), default=0.0)
    if m <= 1e-9:
        return samples
    k = peak / m
    return [s * k for s in samples]


def fade_edges(samples, rate=RATE, ms=8):
    """首尾淡入淡出，避免爆音（Scratch 循环播放时尤其重要）。"""
    n = len(samples)
    k = max(1, int(rate * ms / 1000))
    out = list(samples)
    for i in range(min(k, n)):
        out[i] *= i / k
        out[n - 1 - i] *= i / k
    return out


# ---------------------------------------------------------------- 音效预设
def _pop(dur, rate):
    return env(osc(lambda t: 900 - 600 * t, dur, "sine", rate))


def _click(dur, rate):
    return env(osc(1400, dur, "square", rate), attack=0.001, release=0.01)


def _coin(dur, rate):
    a = env(osc(note_freq("B5"), dur * 0.45, "square", rate))
    b = env(osc(note_freq("E6"), dur * 0.55, "square", rate))
    return seq(a, b)


def _swoosh(dur, rate):
    n = noise(dur, rate, decay=False)
    return env(lowpass(n, lambda t: 400 + 3000 * t, rate), attack=0.02, release=0.05)


def _whoosh(dur, rate):
    n = noise(dur, rate, decay=False)
    return env(lowpass(n, lambda t: 4000 - 3200 * t, rate), attack=0.01, release=0.08)


def _hit(dur, rate):
    thud = env(osc(lambda t: 160 - 110 * t, dur * 0.8, "sine", rate))
    crack = env(lowpass(noise(dur, rate), 2500, rate), release=0.02)
    return mix(thud, [c * 0.6 for c in crack])


def _jump(dur, rate):
    return env(osc(lambda t: 320 + 620 * t, dur, "sine", rate))


def _laser(dur, rate):
    return env(osc(lambda t: 2200 - 1900 * t, dur, "square", rate), release=0.03)


def _powerup(dur, rate):
    notes = ("C5", "E5", "G5", "C6")
    step = dur / len(notes)
    return seq(*[env(osc(note_freq(nt), step * 0.92, "square", rate)) for nt in notes])


def _explosion(dur, rate):
    boom = env(osc(lambda t: 110 - 70 * t, dur, "sine", rate), release=0.12)
    hiss = env(lowpass(noise(dur, rate, decay=True), 3000, rate), release=0.1)
    return mix(boom, [h * 0.7 for h in hiss])


def _footstep(dur, rate):
    return env(lowpass(noise(dur, rate), 900, rate), attack=0.002, release=0.02)


def _error(dur, rate):
    a = env(osc(note_freq("A3"), dur * 0.5, "square", rate))
    b = env(osc(note_freq("F3"), dur * 0.5, "square", rate))
    return seq(a, b)


def _blip(dur, rate):
    return env(osc(note_freq("A5"), dur, "sine", rate))


def _win(dur, rate):
    notes = ("C5", "E5", "G5", "C6")
    step = dur / (len(notes) + 1.2)
    parts = [env(osc(note_freq(nt), step * 0.9, "square", rate)) for nt in notes]
    parts.append(env(osc(note_freq("C6"), step * 1.1, "square", rate), release=0.12))
    return seq(*parts)


def _lose(dur, rate):
    notes = ("G4", "F4", "E4", "C4")
    step = dur / len(notes)
    return seq(*[env(osc(note_freq(nt), step * 0.95, "tri", rate)) for nt in notes])


def _boing(dur, rate):
    return env(osc(lambda t: 180 + 420 * math.sin(math.pi * t), dur, "sine", rate))


def _sparkle(dur, rate):
    notes = ("E6", "C6", "D6", "G6")
    step = dur / len(notes)
    return seq(*[env(osc(note_freq(nt), step * 0.9, "sine", rate)) for nt in notes])


SFX = {
    "pop": _pop, "click": _click, "coin": _coin, "swoosh": _swoosh,
    "whoosh": _whoosh, "hit": _hit, "jump": _jump, "laser": _laser,
    "powerup": _powerup, "explosion": _explosion, "footstep": _footstep,
    "error": _error, "blip": _blip, "win": _win, "lose": _lose,
    "boing": _boing, "sparkle": _sparkle,
}

# ---------------------------------------------------------------- BGM 预设
# 每个 mood = (主旋律音型, 和弦/低音音型, 每拍秒数, 波形)
BGM = {
    # 轻快明亮：跳跃式三音
    "happy": (["C5", "E5", "G5", "E5"], ["C3", "C3", "G2", "G2"], 0.26, "square"),
    # 追逐紧张：快速八分音符 + 低音
    "chase": (["E4", "E4", "F4", "F4", "G4", "G4", "F4", "E4"],
              ["A2", "A2", "G2", "G2", "A2", "A2", "E2", "E2"], 0.16, "square"),
    # 诡异悬疑：慢速小调 + 失谐
    "spooky": (["A4", "C5", "B4", "G#4"], ["A2", "F2", "E2", "E2"], 0.5, "sine"),
    # 安静舒缓：慢速长音铺底
    "calm": (["C4", "G4", "A4", "E4"], ["C2", "C2", "A2", "A2"], 0.75, "tri"),
    # 胜利小号
    "victory": (["G4", "G4", "G4", "C5", "E5", "G5"], ["C3", "C3", "C3", "C3", "C3", "C3"], 0.24, "square"),
    # 失败下行
    "defeat": (["E4", "D4", "C4", "A3"], ["A2", "A2", "F2", "F2"], 0.42, "tri"),
    # 神秘探索：五声音阶
    "explore": (["C5", "D5", "E5", "G5", "A5", "G5", "E5", "D5"],
                ["C3", "C3", "G2", "G2", "F2", "F2", "G2", "G2"], 0.22, "tri"),
}


def gen_melody(notes, dur, out, bpm=120, wave_type="square", gap=0.02, rate=RATE):
    """notes 支持 "C4:1 E4:1 G4:2"（逗号或空格分隔），冒号后是拍数；
    也支持纯音名（等长）。"""
    beat = 60.0 / bpm
    items = [t for t in re.split(r"[,\s]+", str(notes).strip()) if t]
    samples = []
    for item in items:
        if ":" in item:
            name, _, beats = item.partition(":")
            try:
                length = float(beats)
            except ValueError:
                length = 1.0
        else:
            name, length = item, 1.0
        f = note_freq(name)
        d = max(0.03, dur * length)
        samples += env(osc(f, d, wave_type, rate))
        samples += silence(gap, rate)
    write_wav(out, normalize(samples))
    print("wrote %s  (%.2fs)" % (out, len(samples) / float(rate)))


def gen_tone(freq, dur, out, wave_type="sine", amp=0.5, rate=RATE):
    s = [v * amp for v in osc(freq, dur, wave_type, rate)]
    write_wav(out, normalize(fade_edges(env(s, rate))))
    print("wrote %s  (%.2fs)" % (out, len(s) / float(rate)))


def gen_sweep(f0, f1, dur, out, wave_type="sine", rate=RATE):
    s = env(osc(lambda t: f0 + (f1 - f0) * t, dur, wave_type, rate))
    write_wav(out, normalize(fade_edges(s, rate)))
    print("wrote %s  (%.2fs)" % (out, len(s) / float(rate)))


def gen_noise(dur, out, rate=RATE):
    s = env(lowpass(noise(dur, rate), 3000, rate))
    write_wav(out, normalize(fade_edges(s, rate)))
    print("wrote %s  (%.2fs)" % (out, len(s) / float(rate)))


def gen_sfx(name, out, rate=RATE):
    if name not in SFX:
        raise SystemExit("未知音效预设 %r，可用：%s" % (name, ", ".join(sorted(SFX))))
    dur = {"coin": 0.28, "powerup": 0.36, "win": 0.85, "lose": 0.7,
           "explosion": 0.55, "sparkle": 0.3}.get(name, 0.18)
    s = SFX[name](dur, rate)
    write_wav(out, normalize(fade_edges(s, rate)))
    print("wrote %s  (%.2fs, 预设=%s)" % (out, len(s) / float(rate), name))


def gen_bgm(mood, bars, out, rate=RATE):
    """程序化背景音乐。bars 指循环包含几个小节（4 拍 = 1 小节）。"""
    if mood not in BGM:
        raise SystemExit("未知 BGM 情绪 %r，可用：%s" % (mood, ", ".join(sorted(BGM))))
    mel, bass, beat, wave_type = BGM[mood]
    total_beats = bars * 4
    samples = []
    for i in range(total_beats):
        # 主旋律
        m = mel[i % len(mel)]
        samples += env(osc(note_freq(m), beat * 0.9, wave_type, rate), rate)
        # 低音（每 2 拍换一个）
        if i % 2 == 0:
            b = bass[(i // 2) % len(bass)]
            samples += env(osc(note_freq(b), beat * 1.8, "sine", rate), rate)
    # 无缝循环：把尾巴淡出并把开头 12ms 交叉淡入
    s = normalize(samples, 0.8)
    k = int(rate * 0.012)
    if len(s) > 2 * k:
        head = s[:k]
        tail = s[-k:]
        blended = []
        for i in range(k):
            w = i / float(k)
            blended.append(tail[i] * (1 - w) + head[i] * w)
        s = blended + s[k:-k]
    write_wav(out, s)
    print("wrote %s  (%.2fs, 情绪=%s, %d 小节)" % (out, len(s) / float(rate), mood, bars))


def write_wav(path, samples, rate=RATE):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    frames = bytearray()
    for s in samples:
        v = int(max(-32768, min(32767, s * 32767)))
        frames += struct.pack("<h", v)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def main():
    ap = argparse.ArgumentParser(description="离线音频生成（不依赖外部服务）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("tone", help="单个音")
    t.add_argument("--freq", type=float, default=440)
    t.add_argument("--dur", type=float, default=0.2)
    t.add_argument("--wave", default="sine", choices=["sine", "square", "saw", "tri", "triangle"])
    t.add_argument("--out", required=True)

    sw = sub.add_parser("sweep", help="滑音")
    sw.add_argument("--from-freq", type=float, default=800)
    sw.add_argument("--to-freq", type=float, default=300)
    sw.add_argument("--dur", type=float, default=0.15)
    sw.add_argument("--wave", default="sine", choices=["sine", "square", "saw", "tri", "triangle"])
    sw.add_argument("--out", required=True)

    m = sub.add_parser("melody", help="旋律")
    m.add_argument("--notes", default="C4,E4,G4", help='如 "C4:1 E4:1 G4:2"')
    m.add_argument("--dur", type=float, default=0.18, help="每个音符的基础时长（秒）")
    m.add_argument("--bpm", type=float, default=120)
    m.add_argument("--wave", default="square", choices=["sine", "square", "saw", "tri", "triangle"])
    m.add_argument("--out", required=True)

    ns = sub.add_parser("noise", help="噪声")
    ns.add_argument("--dur", type=float, default=0.12)
    ns.add_argument("--out", required=True)

    s = sub.add_parser("sfx", help="音效预设")
    s.add_argument("--name", required=True)
    s.add_argument("--out", required=True)

    b = sub.add_parser("bgm", help="程序化背景音乐")
    b.add_argument("--mood", required=True)
    b.add_argument("--bars", type=int, default=4)
    b.add_argument("--out", required=True)

    sub.add_parser("list", help="列出全部预设")

    args = ap.parse_args()
    if args.cmd == "tone":
        gen_tone(args.freq, args.dur, args.out, args.wave)
    elif args.cmd == "sweep":
        gen_sweep(args.from_freq, args.to_freq, args.dur, args.out, args.wave)
    elif args.cmd == "melody":
        gen_melody(args.notes, args.dur, args.out, args.bpm, args.wave)
    elif args.cmd == "noise":
        gen_noise(args.dur, args.out)
    elif args.cmd == "sfx":
        gen_sfx(args.name, args.out)
    elif args.cmd == "bgm":
        gen_bgm(args.mood, args.bars, args.out)
    elif args.cmd == "list":
        print("音效预设 (%d):" % len(SFX))
        for k in sorted(SFX):
            print("  %-10s %s" % (k, SFX[k].__doc__ or ""))
        print("BGM 情绪 (%d):" % len(BGM))
        for k in sorted(BGM):
            print("  %-10s 旋律=%s" % (k, BGM[k][0]))


if __name__ == "__main__":
    main()
