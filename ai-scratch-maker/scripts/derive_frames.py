#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单帧 → 多帧派生：把一张静态造型，派生出循环动画的多帧。

## 解决什么问题
P9 帧动画要求角色有「多帧造型」才能「会动」。但 ImageGen 一次只出一张图，
美术同学手 K 帧又慢。本脚本用**确定性身体振荡器**（整体上下浮动 + 轻微左右倾 +
呼吸式挤压拉伸）从单张 pose 派生 K 帧，直接喂给 ir-patterns.md P9 的 animations:。

这不能替代专业逐帧动画（肢体不会真的摆动），但能让「只会一张图」的角色立刻拥有
「呼吸 / 走路晃动」的活感，是 P9 的低成本兜底方案。纯 SVG 基础图元变换，铁律17 合规
（不动用 filter/mask/clip）。

用法：
    python scripts/derive_frames.py pose.svg --out-dir assets/hero_walk --frames 4 --mode walk
    python scripts/derive_frames.py pose.svg --out-dir assets/hero_idle --frames 6 --mode idle \
        --ir-out assets/hero_idle/anim.yaml --var 状态 --state 待机
"""
import argparse
import math
import os
import sys
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def _center(root):
    vb = root.get("viewBox")
    if vb:
        parts = vb.split()
        if len(parts) == 4:
            x, y, w, h = (float(p) for p in parts)
            return x + w / 2, y + h / 2
    try:
        w = float(root.get("width", "100").replace("px", ""))
        h = float(root.get("height", "100").replace("px", ""))
        return w / 2, h / 2
    except ValueError:
        return 50, 50


def _wrap_with_transform(root, transform):
    g = ET.Element("{%s}g" % SVG_NS)
    g.set("transform", transform)
    kids = list(root)
    for k in kids:
        root.remove(k)
        g.append(k)
    root.append(g)
    return g


def _frame_transform(cx, cy, phase, amp, bob, squash):
    angle = amp * math.sin(phase)
    bob_y = bob * math.sin(phase)
    sx = 1.0 + squash * math.sin(phase)
    sy = 1.0 - squash * math.sin(phase)
    return ("translate(%g %g) rotate(%g) scale(%g %g) translate(%g %g) translate(0 %g)"
            % (cx, cy, angle, sx, sy, -cx, -cy, bob_y))


def derive(base_svg, out_dir, frames, mode, prefix, amp, bob, squash):
    tree = ET.parse(base_svg)
    root = tree.getroot()
    cx, cy = _center(root)
    if mode == "idle":
        amp, bob, squash = (amp or 2.0), (bob or 1.5), (squash or 0.03)
    elif mode == "walk":
        amp, bob, squash = (amp or 6.0), (bob or 2.5), (squash or 0.05)
    else:  # bob
        amp, bob, squash = (amp or 0.0), (bob or 3.0), (squash or 0.02)
    os.makedirs(out_dir, exist_ok=True)
    names = []
    for i in range(frames):
        t = ET.parse(base_svg).getroot()
        ph = 2 * math.pi * i / frames
        tr = _frame_transform(cx, cy, ph, amp, bob, squash)
        _wrap_with_transform(t, tr)
        nm = "%s%d" % (prefix, i)
        fname = nm + ".svg"
        body = ET.tostring(t, encoding="unicode")
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n")
        names.append((nm, fname))
    return names, (cx, cy)


def emit_ir(names, out_dir, var, state, fps):
    lines = ["    costumes:"]
    for nm, fname in names:
        lines.append('    - name: %s' % nm)
        lines.append('      asset: %s' % os.path.join(out_dir, fname).replace("\\", "/"))
    if var and state:
        lines += [
            "    variables:",
            "      %s: %s" % (var, state),
            "    animations:",
            "      var: %s" % var,
            "      fps: %s" % (fps or 12),
            "      states:",
            "        %s: [%s]" % (state, ", ".join(nm for nm, _ in names)),
        ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="单帧 → 多帧派生（确定性身体振荡器，铁律17 合规）")
    ap.add_argument("base", help="基础静态造型 SVG")
    ap.add_argument("--out-dir", required=True, help="帧输出目录")
    ap.add_argument("--frames", type=int, default=4, help="派生帧数（默认 4）")
    ap.add_argument("--mode", default="walk", choices=["walk", "idle", "bob"])
    ap.add_argument("--prefix", default="frame", help="帧名前缀")
    ap.add_argument("--amp", type=float, default=None, help="最大倾角(度)，默认按 mode")
    ap.add_argument("--bob", type=float, default=None, help="上下浮动(px)，默认按 mode")
    ap.add_argument("--squash", type=float, default=None, help="挤压幅度，默认按 mode")
    ap.add_argument("--ir-out", help="输出 P9 兼容的 IR 片段（costumes+animations）")
    ap.add_argument("--var", default="状态", help="驱动变量名")
    ap.add_argument("--state", default="动画", help="动画状态名")
    ap.add_argument("--fps", type=int, default=12)
    args = ap.parse_args()

    names, (cx, cy) = derive(args.base, args.out_dir, args.frames, args.mode,
                             args.prefix, args.amp, args.bob, args.squash)
    print("DERIVE_FRAMES_OK  从 %s 派生 %d 帧 -> %s（中心 %.0f,%.0f，mode=%s）"
          % (args.base, args.frames, args.out_dir, cx, cy, args.mode))
    if args.ir_out:
        ir = emit_ir(names, args.out_dir, args.var, args.state, args.fps)
        with open(args.ir_out, "w", encoding="utf-8") as f:
            f.write(ir + "\n")
        print("[IR] P9 片段 -> %s" % args.ir_out)
        print(ir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
