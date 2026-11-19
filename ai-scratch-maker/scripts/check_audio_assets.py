#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""音效素材合规校验：把「听感问题」变成可测量的指标。

为什么需要它：
    「音效好不好听」是主观的，但**「音效会不会有爆音、咔哒、断音、一样响」是客观的**。
    这五类问题在波形上都有明确特征，而且**耳朵听不出来、装进作品才发现**：

    ① 首尾不为零     → 播放起止有「咔哒」声（DC 突变）
    ② DC 偏移        → 波形整体偏离 0，Scratch 播放会有低频嗡嗡声
    ③ 中间静音段     → 「嘀…（空）…嘀」听着像卡带
    ④ 峰值超 0 dBFS  → 削波，变成刺耳的方波
    ⑤ 响度不分层     → 点击和爆炸一样响，玩家两分钟就关声音

检查项：
    [格式] 44100Hz / 单声道 / 16bit
    [响度] 峰值必须在所属层的 ±2 dB 内（ui -18 / fx -9 / ev -3 / amb -15）
    [包络] 首尾 20ms 内必须收敛到接近 0；中间不得有 > 100ms 的静音
    [直流] |mean| < 0.01
    [削波] 峰值 <= 0.99
    [时长] 在所属层的合理区间内
    [清单] manifest.json 与实际 wav 文件一一对应

用法:
    python scripts/check_audio_assets.py                # 默认查 examples/assets/audio
    python scripts/check_audio_assets.py 某目录
    python scripts/check_audio_assets.py --quiet
"""
import argparse
import json
import math
import os
import struct
import sys
import wave

LEVEL_DB = {"ui": -18.0, "fx": -9.0, "ev": -3.0, "amb": -15.0}
LEVEL_TOL = 2.0          # 允许 ±2 dB
DUR_RANGE = {
    "ui": (0.03, 0.25),
    "fx": (0.08, 0.60),
    "ev": (0.30, 1.60),
    "amb": (1.00, 4.00),
}
EDGE_SILENT = 0.02       # 首尾样本绝对值上限
DC_LIMIT = 0.01
PEAK_LIMIT = 0.99
GAP_MS = 100             # 中间静音超过这个时长就算断音


def read_wav(path):
    with wave.open(path, "rb") as w:
        ch = w.getnchannels()
        sw = w.getsampwidth()
        rate = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        return {"ch": ch, "sw": sw, "rate": rate, "n": n, "samples": None}
    vals = struct.unpack("<%dh" % (len(raw) // 2), raw)
    return {"ch": ch, "sw": sw, "rate": rate, "n": n,
            "samples": [v / 32768.0 for v in vals]}


def longest_gap(samples, rate):
    """最长连续静音（毫秒）。"""
    thr = 0.0015
    cur = best = 0
    for s in samples:
        if abs(s) < thr:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best * 1000.0 / rate


def check_one(path, group):
    errs, warns = [], []
    try:
        d = read_wav(path)
    except Exception as e:
        return ["读不了 WAV：%s" % e], warns
    if d["samples"] is None:
        return ["位深不是 16bit（实为 %d bit）" % (d["sw"] * 8)], warns
    if d["rate"] != 44100:
        errs.append("采样率应为 44100，实为 %d" % d["rate"])
    if d["ch"] != 1:
        errs.append("必须单声道（Scratch 会混成单声道，双声道白占一倍体积），实为 %d 声道" % d["ch"])

    s = d["samples"]
    if not s:
        return ["空文件"], warns
    n = len(s)
    dur = n / float(d["rate"])
    pk = max(abs(v) for v in s)
    dc = sum(s) / n
    head = abs(s[0])
    tail = abs(s[-1])
    gap = longest_gap(s, d["rate"])

    # 响度分层
    target = LEVEL_DB.get(group)
    if target is not None:
        db = 20 * math.log10(pk) if pk > 0 else -99
        if abs(db - target) > LEVEL_TOL:
            errs.append("峰值 %.1f dBFS 偏离本层目标 %.0f dBFS 超过 ±%.0f（层间不分层 = 听感业余）"
                        % (db, target, LEVEL_TOL))

    if pk > PEAK_LIMIT:
        errs.append("峰值 %.3f 超过 %.2f，会削波" % (pk, PEAK_LIMIT))
    if abs(dc) > DC_LIMIT:
        errs.append("DC 偏移 %.4f 超过 %.2f（会有低频嗡嗡声）" % (dc, DC_LIMIT))
    if head > EDGE_SILENT:
        errs.append("首个样本 %.3f 不为 0（起播会「咔」一声）" % head)
    if tail > EDGE_SILENT:
        errs.append("末个样本 %.3f 不为 0（结束会「咔」一声）" % tail)
    # 尾部必须「在衰减」：最后 10% 时长的能量要明显低于峰值，否则是硬切
    tw = max(1, int(n * 0.10))
    tail_rms = (sum(v * v for v in s[-tw:]) / tw) ** 0.5
    body_rms = (sum(v * v for v in s) / n) ** 0.5
    if body_rms > 1e-6 and tail_rms > body_rms * 1.6 and tail_rms > 0.02:
        errs.append("尾部能量（%.4f）高于整体 RMS（%.4f），收尾是硬切而非衰减" % (tail_rms, body_rms))

    lo, hi = DUR_RANGE.get(group, (0.01, 60))
    if dur < lo or dur > hi:
        errs.append("时长 %.3fs 超出本层区间 %.2f~%.2fs" % (dur, lo, hi))

    if gap > GAP_MS:
        warns.append("中间有 %.0fms 连续静音（听感像断音）" % gap)

    return errs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    base = args.dir or os.path.join(os.getcwd(), "examples", "assets", "audio")
    if not os.path.isdir(base):
        print("目录不存在: %s" % base)
        return 2

    mp = os.path.join(base, "manifest.json")
    manifest = {}
    if os.path.exists(mp):
        manifest = json.load(open(mp, encoding="utf-8"))
    by_file = {s["file"]: s for s in manifest.get("sounds", [])}

    wavs = sorted(f for f in os.listdir(base) if f.lower().endswith(".wav"))
    if not wavs:
        print("没找到 WAV：%s" % base)
        return 2

    total_err = total_warn = 0
    bad = []
    for f in wavs:
        meta = by_file.get(f)
        if meta:
            group = meta["group"]
        else:
            group = f.split("_")[0]
            if group not in LEVEL_DB:
                group = "fx"
        errs, warns = check_one(os.path.join(base, f), group)
        total_err += len(errs)
        total_warn += len(warns)
        if errs:
            bad.append(f)
        if errs or (warns and not args.quiet):
            print("%s %-18s [%s]" % ("✗" if errs else "⚠", f, group))
            for e in errs:
                print("    ✗ %s" % e)
            for w in warns:
                print("    ⚠ %s" % w)
        elif not args.quiet:
            print("✓ %-18s [%s]" % (f, group))

    # 清单一致性
    if manifest:
        listed = set(by_file)
        actual = set(wavs)
        for m in sorted(listed - actual)[:5]:
            print("✗ manifest 列了但文件不存在：%s" % m)
            total_err += 1
        for m in sorted(actual - listed)[:5]:
            print("✗ 文件存在但 manifest 没登记：%s" % m)
            total_err += 1
        # 层内数量分布（信息性）
        cnt = {}
        for s in manifest["sounds"]:
            cnt[s["group"]] = cnt.get(s["group"], 0) + 1
        print("层分布: " + " / ".join("%s %d" % (k, cnt[k]) for k in ("ui", "fx", "ev", "amb") if k in cnt))

    print("-" * 56)
    print("检查 %d 个音效：错误 %d，警告 %d" % (len(wavs), total_err, total_warn))
    if total_err == 0:
        print("AUDIO_ASSETS_OK  音效合规（格式 / 分层响度 / 包络 / 直流 / 时长 全部通过）")
        return 0
    print("AUDIO_ASSETS_FAIL  不合规：%s" % ", ".join(bad[:8]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
