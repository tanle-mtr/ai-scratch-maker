#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""精灵表切片工具（多帧美术管线的第二步）。

用途：把一张横向/网格排布的「精灵表」（sprite sheet）切成单帧 PNG，
并直接打印出可粘进 IR 的 `costumes:` 与 `animations:` 片段，省去手算坐标。

配套 `ai-scratch-maker` 的多帧动画能力（`build_sb3.py` 的 `expand_animations`）：
  1) 美术阶段用生图/手绘出一张 N 帧的精灵表（或 3D 渲多视角导出表）；
  2) 本工具切片 -> 每帧一个 PNG；
  3) IR 里写 `animations:`（指一个驱动变量 + 各状态的造型名列表），
     构建器自动展开「按状态循环切造型」脚本（详见 references/ir-patterns.md 的 P9）。

示例：
  python slice_sheet.py --sheet run.png --cols 6 --rows 1 \
      --out-dir assets/hero_run --prefix hero_run
  # 输出 assets/hero_run/hero_run_0.png ... 并打印 IR 片段

  # 指定每帧的造型名（否则用 prefix_0..prefix_N-1）
  python slice_sheet.py --sheet run.png --cols 6 --rows 1 \
      --names run0,run1,run2,run3,run4,run5 --out-dir assets/hero_run

  # 同时导出 IR 片段到文件，便于直接 include
  python slice_sheet.py --sheet run.png --cols 6 --rows 1 \
      --names run0..run5 --ir-out assets/hero_run/anim.yaml --var 状态 --states 跑:run0..run5
"""
import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.stderr.write("[错误] 需要 Pillow：pip install Pillow\n")
    sys.exit(2)


def slice(sheet_path, cols, rows, out_dir, prefix, names=None, start=0):
    if not os.path.exists(sheet_path):
        sys.stderr.write("[错误] 精灵表不存在：%s\n" % sheet_path)
        sys.exit(2)
    img = Image.open(sheet_path).convert("RGBA")
    W, H = img.size
    cw, ch = W // cols, H // rows
    if cw <= 0 or ch <= 0:
        sys.stderr.write("[错误] 单元格尺寸非正（表 %dx%d 与 %dx%d 不匹配）\n" % (W, H, cols, rows))
        sys.exit(2)
    os.makedirs(out_dir, exist_ok=True)
    frames = []
    idx = 0
    for r in range(rows):
        for c in range(cols):
            cell = img.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
            if names and idx < len(names):
                nm = names[idx]
            else:
                nm = "%s_%d" % (prefix, start + idx)
            # 造型名里不要带扩展名；asset 用 png
            fname = nm + ".png"
            cell.save(os.path.join(out_dir, fname))
            frames.append((nm, fname))
            idx += 1
            if names and idx >= len(names):
                break
        if names and idx >= len(names):
            break
    return frames, (cw, ch)


def emit_ir(frames, out_dir, var, states_spec, fps, prefix):
    """打印 costumes + animations 片段。states_spec: {状态名: [造型名,...]}。"""
    lines = []
    lines.append("    costumes:")
    for nm, fname in frames:
        lines.append('    - name: %s' % nm)
        lines.append('      asset: %s' % os.path.join(out_dir, fname).replace("\\", "/"))
    if var and states_spec:
        lines.append("    variables:")
        lines.append("      %s: %s" % (var, list(states_spec.keys())[0]))
        lines.append("    animations:")
        lines.append("      var: %s" % var)
        lines.append("      fps: %s" % (fps or 12))
        lines.append("      states:")
        for st, cs in states_spec.items():
            lines.append("        %s: [%s]" % (st, ", ".join(cs)))
    return "\n".join(lines)


def parse_states(spec, frames):
    """支持两种写法：
       --states 跑:run0,run1,run2,run3,run4,run5        （逗号：显式造型名）
       --states 跑:0..5                                 （整数范围：帧序号）
       --states 跑:run0..run5                           （名称范围：自动定位起止帧）
    多段用 ; 分隔：待机:idle;跑:run0..run5
    """
    out = {}
    if not spec:
        # 默认：全部帧作为一个名为 prefix 的状态
        out["动画"] = [nm for nm, _ in frames]
        return out
    names = [nm for nm, _ in frames]
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            sys.stderr.write("[警告] states 段缺少冒号，已跳过：%r\n" % part)
            continue
        st, body = part.split(":", 1)
        st = st.strip()
        body = body.strip()
        if ".." in body:
            a, b = body.split("..", 1)
            a, b = a.strip(), b.strip()
            try:
                ia, ib = int(a), int(b)
            except ValueError:
                # 名称范围：在帧列表里找到起止索引
                ia = names.index(a) if a in names else None
                ib = names.index(b) if b in names else None
                if ia is None or ib is None:
                    sys.stderr.write("[警告] states 名称范围无法定位：%r\n" % body)
                    continue
            cs = [frames[i][0] for i in range(ia, ib + 1) if i < len(frames)]
        else:
            cs = [x.strip() for x in body.split(",") if x.strip()]
        out[st] = cs
    return out


def main():
    ap = argparse.ArgumentParser(description="精灵表切片 + 输出 IR 片段")
    ap.add_argument("--sheet", required=True, help="精灵表 PNG 路径")
    ap.add_argument("--cols", type=int, required=True, help="列数（横向帧数）")
    ap.add_argument("--rows", type=int, default=1, help="行数（默认 1）")
    ap.add_argument("--out-dir", required=True, help="切片输出目录")
    ap.add_argument("--prefix", default="frame", help="默认造型名前缀")
    ap.add_argument("--names", default=None,
                    help="逗号分隔的造型名（数量需 == cols*rows，否则超出的帧用前缀命名）")
    ap.add_argument("--start", type=int, default=0, help="默认命名起始序号")
    ap.add_argument("--var", default=None, help="（可选）动画驱动变量名")
    ap.add_argument("--states", default=None,
                    help="（可选）状态->造型 映射，如 '跑:run0..run5;待机:idle'")
    ap.add_argument("--fps", type=int, default=12, help="动画帧率（默认 12）")
    ap.add_argument("--ir-out", default=None, help="（可选）把 IR 片段写入该 YAML 文件")
    args = ap.parse_args()

    names = [x.strip() for x in args.names.split(",")] if args.names else None
    frames, (cw, ch) = slice(args.sheet, args.cols, args.rows,
                             args.out_dir, args.prefix, names, args.start)
    print("[切片] %s -> %d 帧，单元 %dx%d，输出 %s"
          % (args.sheet, len(frames), cw, ch, os.path.abspath(args.out_dir)))
    for nm, fn in frames:
        print("  %s" % fn)

    states = parse_states(args.states, frames) if (args.var or args.states) else None
    ir = emit_ir(frames, args.out_dir, args.var, states, args.fps, args.prefix)
    if args.ir_out:
        with open(args.ir_out, "w", encoding="utf-8") as f:
            f.write(ir + "\n")
        print("[IR] 片段已写入 %s" % args.ir_out)
    else:
        print("---- 可粘进 IR 的片段 ----")
        print(ir)


if __name__ == "__main__":
    main()
