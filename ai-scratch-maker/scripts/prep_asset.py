#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""素材预处理助手：把 AI 生成的位图（背景/角色 PNG）整理成 Scratch 标准尺寸。

为什么需要它？
- 舞台背景在 Scratch 里是固定 480x360；直接塞一张任意尺寸的图会出现黑边或错位。
- 角色（sprite）建议保持原始比例，并控制在合理像素范围（太大拖慢编辑器）。
- 本脚本统一做「裁剪填充 / 等比缩放」，输出 PNG，并打印用于 IR 的 asset 路径。

依赖：Pillow（pip install -i https://pypi.org/simple Pillow）。
未安装时本脚本会给出明确提示，不会静默失败。

用法：
  python prep_asset.py --in bg.png --out bg_ready.png --mode stage
  python prep_asset.py --in cat.png --out cat_ready.png --mode sprite --max 480
  python prep_asset.py --in x.png --out y.png --width 200 --height 200 --fill
"""
import argparse
import hashlib
import os
import sys

STAGE_W, STAGE_H = 480, 360


def _require_pil():
    try:
        from PIL import Image
    except Exception as e:  # pragma: no cover
        sys.stderr.write(
            "缺少依赖 Pillow：请运行  python3 -m pip install -i https://pypi.org/simple Pillow\n"
            "原始错误：%s\n" % e
        )
        sys.exit(3)
    try:
        RESAMPLE = Image.Resampling.LANCZOS
    except AttributeError:  # 旧版 Pillow
        RESAMPLE = Image.LANCZOS
    return Image, RESAMPLE


_IMAGE = None
_RESAMPLE = None


def prep(in_path, out_path, mode, width, height, fill, max_side,
         remove_bg=False, trim=False, bg_brightness=175, bg_saturation=30,
         flip_h=False, check_alpha=False, defringe=False, sharpen=False,
         crop_watermark=False):
    global _IMAGE, _RESAMPLE
    _IMAGE, _RESAMPLE = _require_pil()
    if not os.path.exists(in_path):
        sys.stderr.write("输入文件不存在: %s\n" % in_path)
        sys.exit(2)

    im = _IMAGE.open(in_path).convert("RGBA")

    # 顺序很重要：裁水印 → 抠背景 → 去脏边 → 裁透明边 → 缩放 → 锐化
    # 去脏边必须在缩放前（后续 LANCZOS 会重建平滑的抗锯齿边缘）；
    # 锐化必须在缩放后（补偿缩小时损失的高频细节）。
    if crop_watermark:
        im = _crop_watermark(im)
    if remove_bg:
        im = _remove_background(im, bg_brightness, bg_saturation)
    if defringe:
        im = _defringe(im)
    if trim:
        im = _trim(im)
    if flip_h:
        im = _flip_h(im)
    if check_alpha:
        _report_alpha(im, os.path.basename(out_path))

    if mode == "stage":
        tw, th = STAGE_W, STAGE_H
        if width:
            tw = width
        if height:
            th = height
        if fill:
            im = _cover(im, tw, th)
        else:
            im = _contain(im, tw, th)
    elif mode == "sprite":
        if width and height:
            im = _cover(im, width, height) if fill else _contain(im, width, height)
        elif max_side:
            im = _fit_max(im, max_side)
        # 否则保持原尺寸
    else:  # custom
        if width and height:
            im = _cover(im, width, height) if fill else _contain(im, width, height)
        elif width or height:
            im = _fit_one(im, width, height)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    if sharpen:
        im = _sharpen_after_downscale(im)
    im.save(out_path, "PNG", optimize=True, compress_level=9)
    with open(out_path, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    print("OK %s  %dx%d  md5=%s" % (out_path, im.width, im.height, md5))


def _crop_watermark(im, right=0.14, bottom=0.12):
    """裁掉图像生成工具在右下角强制盖的水印区。

    实测：ImageGen 即使不传 footnote，也会在右下角加浅色「AI 生成」标记；
    `background: transparent` 也不生效（输出仍是 RGB）。
    角色图靠 `--remove-bg` 会顺带把浅色水印抠掉（水印与边缘浅色区连通），
    但**背景图不抠背景，水印会保留** —— 所以背景图需要这一步。

    裁掉右侧 14% / 底部 12% 后，再由 `_cover` 居中裁填到目标尺寸，
    构图损失有限，但能彻底去掉水印。
    """
    w, h = im.size
    nw, nh = max(1, round(w * (1 - right))), max(1, round(h * (1 - bottom)))
    return im.crop((0, 0, nw, nh))


def _defringe(im):
    """去掉抠图留下的白边/灰晕。

    AI 生成图常带浅灰棋盘格底，_remove_background 是二值判定，
    最外圈半透明像素的 RGB 仍混着背景色 → 缩小后在角色轮廓上形成一圈白边。

    做法：对 alpha 做一次 3x3 最小值腐蚀，把受污染的最外圈剥掉 1px。
    **必须在缩放前执行** —— 后续 LANCZOS 会重新生成平滑的抗锯齿边缘，
    所以视觉上不会变锯齿，只是去掉那层脏色。
    """
    from PIL import ImageFilter
    a = im.split()[-1]
    eroded = a.filter(ImageFilter.MinFilter(3))
    out = im.copy()
    out.putalpha(eroded)
    return out


def _sharpen_after_downscale(im, radius=0.6, percent=90, threshold=2):
    """补偿缩小造成的高频细节损失（只作用于 RGB，保护 alpha 边缘）。

    大图（1024~1536）缩到 Scratch 尺寸（角色 200~300、舞台 480x360）时，
    LANCZOS 会让线条变软。轻微 UnsharpMask 能把轮廓拉回来。
    threshold 用于避免放大噪点/渐变色带。
    """
    from PIL import ImageFilter
    rgb = im.convert("RGB").filter(
        ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))
    out = rgb.convert("RGBA")
    out.putalpha(im.split()[-1])
    return out


def _cover(im, w, h):
    """裁剪填充：保持比例，裁掉多余部分，铺满 w x h。"""
    iw, ih = im.size
    scale = max(w / iw, h / ih)
    nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
    im = im.resize((nw, nh), _RESAMPLE)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return im.crop((left, top, left + w, top + h))


def _contain(im, w, h):
    """等比缩放并居中放置到 w x h 的画布（其余透明）。"""
    iw, ih = im.size
    scale = min(w / iw, h / ih)
    nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
    im = im.resize((nw, nh), _RESAMPLE)
    canvas = _IMAGE.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(im, ((w - nw) // 2, (h - nh) // 2), im)
    return canvas


def _fit_max(im, max_side):
    iw, ih = im.size
    if max(iw, ih) <= max_side:
        return im
    scale = max_side / max(iw, ih)
    return im.resize((max(1, round(iw * scale)), max(1, round(ih * scale))), _RESAMPLE)


def _fit_one(im, w, h):
    if w and not h:
        return im.resize((w, max(1, round(im.size[1] * w / im.size[0]))), _RESAMPLE)
    if h and not w:
        return im.resize((max(1, round(im.size[0] * h / im.size[1])), h), _RESAMPLE)
    return im


def _remove_background(im, brightness=175, saturation=30):
    """把「浅色低饱和」的背景抠成透明。

    很多 AI 生成的图片并不带真正的 alpha 通道，而是画了一层浅灰棋盘格，
    直接塞进 Scratch 会出现一个灰方块背景。

    做法：
      1. 标出「亮且低饱和」的像素作为背景候选（棋盘格、深色轮廓都不满足）；
      2. 从图片四边向内做连通域扩散，只把与边界连通的候选像素抠掉
         （这样角色身上���白色肚子、白爪子不会被误删）；
      3. 把抠掉的像素 alpha 置 0。
    """
    from collections import deque

    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()

    cand = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            mx, mn = max(r, g, b), min(r, g, b)
            if mx >= brightness and (mx - mn) <= saturation:
                cand[y * w + x] = 1

    seen = bytearray(w * h)
    q = deque()

    def push(x, y):
        i = y * w + x
        if cand[i] and not seen[i]:
            seen[i] = 1
            q.append(i)

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while q:
        i = q.popleft()
        x, y = i % w, i // w
        if x > 0:
            push(x - 1, y)
        if x < w - 1:
            push(x + 1, y)
        if y > 0:
            push(x, y - 1)
        if y < h - 1:
            push(x, y + 1)

    out = rgb.convert("RGBA")
    op = out.load()
    n = 0
    for y in range(h):
        for x in range(w):
            if seen[y * w + x]:
                op[x, y] = (op[x, y][0], op[x, y][1], op[x, y][2], 0)
                n += 1
    sys.stderr.write("  抠掉背景像素 %d / %d (%.1f%%)\n"
                     % (n, w * h, 100.0 * n / (w * h)))
    return out


def _trim(im, pad=2):
    """裁掉四周完全透明的区域，让角色尽量填满造型框。"""
    bbox = im.split()[-1].getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(im.width, r + pad)
    b = min(im.height, b + pad)
    return im.crop((l, t, r, b))


def _flip_h(im):
    """水平镜像。

    Scratch 的 left-right 旋转风格会把**整个造型**水平翻转
    （见 scratch-vm RenderedTarget._getRenderedDirectionAndScale：
      direction < 0 时 scale.x 取 -1）。角色身上左右不对称的部分
    （举起的爪子、身上的字、拿的东西）会被错误地翻到另一边。

    标准解法：准备「原图 + 水平镜像」两套造型，朝左时切到镜像造型。
    这个函数就是用来生成那套镜像造型的。
    """
    return im.transpose(_IMAGE.FLIP_LEFT_RIGHT)


def _report_alpha(im, name):
    """检查背景是不是真透明，并给出结论。"""
    if im.mode != "RGBA":
        sys.stderr.write("  [%s] 不是 RGBA 模式（%s），没有 alpha 通道，背景无法抠\n"
                         % (name, im.mode))
        return
    a = im.split()[-1]
    w, h = im.size
    total = w * h
    hist = a.histogram()
    opaque = sum(hist[251:])
    border = []
    for x in range(w):
        border.append(a.getpixel((x, 0)))
        border.append(a.getpixel((x, h - 1)))
    for y in range(h):
        border.append(a.getpixel((0, y)))
        border.append(a.getpixel((w - 1, y)))
    border_opaque = sum(1 for p in border if p > 250)
    sys.stderr.write(
        "  [%s] 尺寸=%dx%d 不透明像素=%.1f%% 边缘不透明=%d/%d\n"
        % (name, w, h, 100.0 * opaque / total, border_opaque, len(border)))
    if border_opaque > 0:
        sys.stderr.write(
            "  [!] 角色四周仍有不透明像素 —— 在 Scratch 里会看到一个方块底。\n"
            "      建议：生成时要求「isolated on transparent background, no ground, no shadow」，\n"
            "            或用 --remove-bg 再抠一次（--bg-brightness / --bg-saturation 可调阈值）。\n")
    else:
        sys.stderr.write("  [ok] 背景干净（四边全透明）\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["stage", "sprite", "custom"], default="custom")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--fill", action="store_true", help="裁剪填充（而非等比留白）")
    ap.add_argument("--max", dest="max_side", type=int, default=None,
                   help="sprite 模式：限制最长边像素")
    ap.add_argument("--remove-bg", action="store_true",
                   help="抠掉浅色背景（AI 生成图常带棋盘格底，需要抠成真透明）")
    ap.add_argument("--trim", action="store_true",
                   help="裁掉四周透明区域，让角色填满造型框")
    ap.add_argument("--bg-brightness", type=int, default=175,
                   help="背景判定：最小亮度（默认 175）")
    ap.add_argument("--bg-saturation", type=int, default=30,
                   help="背景判定：最大饱和度（默认 30）")
    ap.add_argument("--flip-h", action="store_true",
                   help="水平镜像输出（用于生成「朝左」那套造型）")
    ap.add_argument("--check-alpha", action="store_true",
                    help="检查背景是否真透明，并打印结论")
    ap.add_argument("--defringe", action="store_true",
                    help="去掉抠图残留的白边/灰晕（缩放前腐蚀 alpha 1px）")
    ap.add_argument("--sharpen", action="store_true",
                    help="缩放后轻微锐化，补偿细节损失")
    ap.add_argument("--hq", action="store_true",
                    help="画质组合：等价于 --defringe --sharpen（AI 生成图推荐）")
    ap.add_argument("--crop-watermark", action="store_true",
                    help="裁掉右下角的 AI 水印区（背景图用；角色图靠 --remove-bg 就能抠掉）")
    args = ap.parse_args()
    defringe = args.defringe or args.hq
    sharpen = args.sharpen or args.hq
    prep(args.inp, args.out, args.mode, args.width, args.height, args.fill,
         args.max_side, args.remove_bg, args.trim, args.bg_brightness,
         args.bg_saturation, args.flip_h, args.check_alpha, defringe, sharpen,
         args.crop_watermark)


if __name__ == "__main__":
    main()
