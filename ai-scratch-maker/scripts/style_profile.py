#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风格指纹提取 + 风格锁：把「已验收作品的统一画风」变成可复用的契约。

## 为什么
铁律13/17 要求统一配色（§198 18 HEX）与五层体积感，但「统一」至今只靠人工自觉。
本脚本把一份已验收旗舰的画风抽成**指纹 JSON**，并能据此生成**风格锁**配置——
新作品交付前用 `--check` 比对，量化「你离目标画风有多远」，而不是凭感觉。

## 指纹内容（从被 project.json 真正引用的 SVG 抽）
  · palette      : 出现频率最高的若干主色（hex）
  · stroke_colors: 用到的描边色（应基本统一为 §198 中性描边 #4F4A47）
  · gradient_rate: 含渐变的 SVG 比例（体积感信号）
  · stroke_rate  : 含描边的 SVG 比例（外描边信号）
  · avg_colors   : 每张 SVG 平均不同颜色数（画风复杂度）

## 风格锁（--lock）
固化成「新作品必须满足」的契约：
  · palette 取 §198 18 色（强制）；stroke 强制 #4F4A47；gradient_rate≥阈值；stroke_rate≥阈值。
  `--check` 时逐项比对候选，给出 0–100 的「风格契合度」。

用法：
    python scripts/style_profile.py x.sb3                      # 抽指纹
    python scripts/style_profile.py x.sb3 --save-fp fp.json
    python scripts/style_profile.py --lock fp.json --out lock.json
    python scripts/style_profile.py --check candidate.sb3 --lock lock.json
"""
import argparse
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# §198 18 色板（铁律13 强制统一配色）
PALETTE_18 = {
    "#ffcf4d", "#ffedb3", "#faf19b", "#4f4a47", "#876c26",
    "#32af00", "#5fd100", "#8ce243", "#c6ff2a", "#216e09",
    "#3a8e7d", "#5cd9ba", "#c4ffe3", "#67f6d5", "#2f7365",
    "#767171", "#675d5d", "#7f7f7f",
}
STROKE_EXPECTED = "#4f4a47"


def _referenced_svgs(z):
    try:
        d = json.loads(z.read("project.json"))
    except Exception:
        return []
    ref = set()
    for t in d.get("targets", []):
        for c in t.get("costumes", []) + t.get("backdrops", []):
            a = c.get("assetId") or c.get("md5ext", "")
            ref.add(str(a).split(".")[0].lower())
    return [n for n in z.namelist() if n.lower().endswith(".svg")
            and n[:-4].lower().split("/")[-1] in ref]


def extract(sb3):
    with zipfile.ZipFile(sb3) as z:
        svgs = _referenced_svgs(z)
        color_freq = {}
        stroke_colors = {}
        grad = 0
        stroked = 0
        color_counts = []
        for n in svgs:
            try:
                txt = z.read(n).decode("utf-8", "ignore")
            except Exception:
                continue
            if "linearGradient" in txt or "radialGradient" in txt:
                grad += 1
            if re.search(r"\bstroke\s*=", txt) or "stroke-width" in txt:
                stroked += 1
            for h in re.findall(r"#[0-9a-fA-F]{6}\b", txt):
                h = h.lower()
                color_freq[h] = color_freq.get(h, 0) + 1
            for h in re.findall(r'stroke=["\']#([0-9a-fA-F]{6})["\']', txt):
                stroke_colors["#" + h.lower()] = stroke_colors.get("#" + h.lower(), 0) + 1
            color_counts.append(len(set(re.findall(r"#[0-9a-fA-F]{6}\b", txt))))
    total = len(svgs) or 1
    top = sorted(color_freq.items(), key=lambda kv: kv[1], reverse=True)[:12]
    top_strokes = sorted(stroke_colors.items(), key=lambda kv: kv[1], reverse=True)[:6]
    return {
        "sb3": os.path.basename(sb3),
        "svg_count": len(svgs),
        "palette_top": [c for c, _ in top],
        "stroke_colors": [c for c, _ in top_strokes],
        "gradient_rate": round(grad / total, 3),
        "stroke_rate": round(stroked / total, 3),
        "avg_colors": round(sum(color_counts) / total, 2) if color_counts else 0,
    }


def make_lock(fp, gradient_min=0.5, stroke_min=0.8, palette_from_fp=False):
    palette = (fp.get("palette_top") or []) if palette_from_fp else sorted(PALETTE_18)
    return {
        "label": "风格锁（基于 %s 的%s）" % (
            fp.get("sb3", "?"),
            "实际主色（风格匹配模式）" if palette_from_fp else "§198 18 色（铁律13 强制）"),
        "palette": palette,
        "palette_from_fp": palette_from_fp,
        "stroke_expected": STROKE_EXPECTED,
        "gradient_rate_min": gradient_min,
        "stroke_rate_min": stroke_min,
        "_src_fingerprint": fp,
    }


def check_adherence(sb3, lock):
    fp = extract(sb3)
    palette = set(lock.get("palette", []))
    if not palette:
        palette = PALETTE_18
    # 颜色契合：主色落在区间内的比例
    near = 0
    for c in fp["palette_top"]:
        if c in palette:
            near += 1
            continue
        try:
            r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
        except ValueError:
            continue
        for p in palette:
            pr, pg, pb = int(p[1:3], 16), int(p[3:5], 16), int(p[5:7], 16)
            if abs(r - pr) <= 24 and abs(g - pg) <= 24 and abs(b - pb) <= 24:
                near += 1
                break
    color_fit = round(100.0 * near / len(fp["palette_top"])) if fp["palette_top"] else 100
    stroke_ok = STROKE_EXPECTED in [s.lower() for s in fp["stroke_colors"]]
    grad_ok = fp["gradient_rate"] >= lock.get("gradient_rate_min", 0.5)
    stroked_ok = fp["stroke_rate"] >= lock.get("stroke_rate_min", 0.8)
    score = round(0.5 * color_fit + 0.2 * (100 if stroke_ok else 0)
                  + 0.15 * (100 if grad_ok else 0) + 0.15 * (100 if stroked_ok else 0))
    return {
        "sb3": os.path.basename(sb3),
        "adherence": score,
        "color_fit": color_fit,
        "stroke_ok": stroke_ok,
        "gradient_ok": grad_ok,
        "stroke_rate_ok": stroked_ok,
        "fingerprint": fp,
    }


def main():
    ap = argparse.ArgumentParser(description="风格指纹提取 + 风格锁")
    ap.add_argument("sb3", nargs="?", help="抽指纹的 .sb3（或 --check 的候选）")
    ap.add_argument("--save-fp", help="把指纹写成 JSON")
    ap.add_argument("--lock", help="由指纹生成/比对用的风格锁 JSON")
    ap.add_argument("--out", help="--lock 时的输出路径")
    ap.add_argument("--palette-from-fp", action="store_true",
                    help="风格锁用参考作品的实际主色而非 §198（风格匹配模式）")
    ap.add_argument("--check", action="store_true", help="用 --lock 比对 sb3 的风格契合度")
    args = ap.parse_args()

    if args.check:
        if not args.lock or not args.sb3:
            ap.error("--check 需要 sb3 与 --lock")
        lock = json.load(open(args.lock, encoding="utf-8"))
        rep = check_adherence(args.sb3, lock)
        print("风格契合度: %d / 100" % rep["adherence"])
        print("  颜色契合   : %d%%" % rep["color_fit"])
        print("  中性描边   : %s" % ("OK" if rep["stroke_ok"] else "缺失 %s" % STROKE_EXPECTED))
        print("  渐变体积感 : %s (rate=%.2f, 要求≥%.2f)" % (
            "OK" if rep["gradient_ok"] else "不足", rep["fingerprint"]["gradient_rate"],
            lock.get("gradient_rate_min", 0.5)))
        print("  外描边覆盖 : %s (rate=%.2f, 要求≥%.2f)" % (
            "OK" if rep["stroke_rate_ok"] else "不足", rep["fingerprint"]["stroke_rate"],
            lock.get("stroke_rate_min", 0.8)))
        print("STYLE_CHECK_%s" % ("OK" if rep["adherence"] >= 70 else "WARN"))
        return 0

    if not args.sb3:
        ap.error("需要 sb3")
    fp = extract(args.sb3)
    if args.save_fp:
        with open(args.save_fp, "w", encoding="utf-8") as f:
            json.dump(fp, f, ensure_ascii=False, indent=2)
        print("指纹 -> %s" % args.save_fp)
    if args.lock:
        lock = make_lock(fp, palette_from_fp=args.palette_from_fp)
        out = args.out or args.lock
        with open(out, "w", encoding="utf-8") as f:
            json.dump(lock, f, ensure_ascii=False, indent=2)
        print("风格锁 -> %s" % out)
    print("STYLE_FP_OK  svg=%d 渐变率=%.2f 描边率=%.2f 主色=%s"
          % (fp["svg_count"], fp["gradient_rate"], fp["stroke_rate"], fp["palette_top"][:6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
