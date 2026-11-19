#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""round_ui_alpha.py — 给不透明 UI 位图加「圆角 alpha 遮罩」，使其成为合适资产。

背景 / 为什么需要
------------------------------------------------------------------
quality_gate.analyze_bitmap_usage 把「角色位图无透明通道」判为**不合适**：
这类图缩进 480x360 舞台后会带一整块不透明方块（四角尤甚），正是用户说的
「AI 生成的图片很多不适合做 Scratch 素材」。

有一批程序化绘制的 UI 位图（按钮 / 结算页 / 飘字 / 篮子）是
「纯渐变矩形 + 烤进去的中文文字」，四角无圆角、alpha 恒 255。它们不能直接
矢量化——铁律17 禁止 SVG 里的 <text>，转 SVG 会把文字丢掉，而要补 say 文字
得大改 IR 脚本，风险高。

本工具用**圆角 alpha 遮罩**把四角外部抠成透明（4x 超采样抗锯齿）：
  · 保留原渐变与文字，不丢任何信息；
  · 四角 alpha=0 → PIL getextrema()[-1] 最小值 0 → 门禁判「合适」；
  · 形状圆角化，符合铁律14「窗口圆角」/ 铁律17「UI 圆角」；
  · 画布尺寸不变 → Scratch 造型旋转中心不变，IR / 脚本零改动。

用法
------------------------------------------------------------------
  # 只体检（打印每张图的 alpha 状态，不写文件）
  python scripts/round_ui_alpha.py --check examples/assets/ui/*.png

  # 处理指定文件（默认只动 alpha 全不透明的；自动跳过已合适的）
  python scripts/round_ui_alpha.py --backup-dir build_tmp/ui_alpha_bak \
      examples/assets/ui/win.png examples/assets/ui/lose.png

  # 自定义圆角半径比例（相对短边，默认 0.18），或强制重做已透明图
  python scripts/round_ui_alpha.py --radius 0.22 examples/assets/ui/*.png
  python scripts/round_ui_alpha.py --force examples/assets/ui/*.png
"""
import argparse
import os
import shutil
import sys

try:
    from PIL import Image, ImageChops, ImageDraw
except ImportError:
    print("[错误] 需要 Pillow：pip install Pillow", file=sys.stderr)
    sys.exit(2)


def rounded_mask(w, h, radius_px, supersample=4):
    """生成圆角矩形 L 遮罩，超采样后 LANCZOS 缩回 → 边缘抗锯齿。"""
    sw, sh = w * supersample, h * supersample
    m = Image.new("L", (sw, sh), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle(
        [0, 0, sw - 1, sh - 1],
        radius=max(1, int(radius_px * supersample)),
        fill=255,
    )
    return m.resize((w, h), Image.LANCZOS)


def alpha_extrema(im):
    """返回 alpha 通道 (min, max)；无 alpha 通道的图像返回 (255, 255)。"""
    if im.mode in ("RGBA", "LA", "RGBa"):
        return im.getextrema()[-1]
    if im.mode == "P" and "transparency" in im.info:
        return im.convert("RGBA").getextrema()[-1]
    return (255, 255)


def is_suitable(im):
    """与 quality_gate.analyze_bitmap_usage 同口径：存在透明像素即算合适。"""
    lo = alpha_extrema(im)[0]
    return lo < 250


def process(path, radius_ratio, backup_dir, force=False, check_only=False):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    lo, hi = alpha_extrema(im)
    suitable = is_suitable(im)
    tag = "合适" if suitable else "不合适"
    print(f"  {os.path.basename(path):20s} {w:4d}x{h:<4d} alpha={lo:3d}..{hi:<3d} {tag}", end="")

    if check_only:
        print("  [体检]")
        return "check"

    if suitable and not force:
        print("  [跳过：已合适]")
        return "skip"

    r = max(6, round(min(w, h) * radius_ratio))
    mask = rounded_mask(w, h, r)
    red, green, blue, alpha = im.split()
    alpha = ImageChops.multiply(alpha, mask)
    out = Image.merge("RGBA", (red, green, blue, alpha))

    if not is_suitable(out):
        print("  [失败：处理后仍无透明像素，未写回]")
        return "fail"

    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)
        dst = os.path.join(backup_dir, os.path.basename(path))
        if not os.path.exists(dst):
            shutil.copy2(path, dst)

    out.save(path)
    print(f"  -> 圆角 r={r}px alpha={alpha_extrema(out)[0]}..255 [已写回]")
    return "done"


def main():
    ap = argparse.ArgumentParser(description="给不透明 UI 位图加圆角透明遮罩")
    ap.add_argument("files", nargs="+", help="待处理 PNG")
    ap.add_argument("--radius", type=float, default=0.18,
                    help="圆角半径 / 短边，默认 0.18")
    ap.add_argument("--backup-dir", default=None,
                    help="写回前把原图备份到该目录（可回滚）")
    ap.add_argument("--check", action="store_true", help="只体检，不写文件")
    ap.add_argument("--force", action="store_true",
                    help="已合适的图也强制重做（默认跳过）")
    args = ap.parse_args()

    ok = bad = skip = 0
    print(f"=== 圆角透明化（radius={args.radius}, check={args.check}）===")
    for p in args.files:
        if not os.path.isfile(p):
            print(f"  [缺失] {p}")
            bad += 1
            continue
        try:
            r = process(p, args.radius, args.backup_dir, args.force, args.check)
        except Exception as e:
            print(f"  [异常] {p}: {e}")
            bad += 1
            continue
        if r == "done":
            ok += 1
        elif r == "skip" or r == "check":
            skip += 1
    print(f"=== 完成：写回 {ok} / 跳过·体检 {skip} / 失败 {bad} ===")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
