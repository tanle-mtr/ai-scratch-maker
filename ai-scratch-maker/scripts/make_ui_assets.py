#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Scratch 里「用角色显示文本 / 数字」需要的素材。

Scratch 3.0 的角色没法直接画字（积木里没有文字渲染），
所以显示数字 / 对话框的做法是：把字预先渲染成图片，再让角色换造型。

本脚本生成三类素材：

1. digits  —— 0~9 十个数字（每个一张透明 PNG）。
   角色配 0..9 十套造型，配合「换成 X 造型」传计算值，
   就能把变量的个位实时显示在舞台上（见 references/ui-display.md）。

2. counter —— 一个「数字牌」：把 0~9 拼成 0~99 的两位数牌面。
   舞台上一共 100 张图，角色通过「第几位 + 数字」换造型。

3. chatbox —— 对话框底板（半透明圆角矩形 + 描边）。
   对话文字本身仍然是运行时用「说」积木显示在角色旁边，
   底板只负责把气泡区域框起来。

用法示例：
    python3 scripts/make_ui_assets.py digits --out-dir assets/ui
    python3 scripts/make_ui_assets.py counter --out-dir assets/ui --max 99
    python3 scripts/make_ui_assets.py chatbox --out assets/ui/chatbox.png --w 220 --h 64
"""
import argparse
import os
import sys

# Windows 自带的中文字体；找不到就退回到 Pillow 默认位图字体
FONT_CANDIDATES = [
    ("C:/Windows/Fonts/msyhbd.ttc", 0),   # 微软雅黑 Bold
    ("C:/Windows/Fonts/msyh.ttc", 0),     # 微软雅黑
    ("C:/Windows/Fonts/simhei.ttf", 0),    # 黑体
    ("C:/Windows/Fonts/simsun.ttc", 0),    # 宋体
    ("/System/Library/Fonts/PingFang.ttc", 0),
    ("/usr/share/fonts/truetype/arphic/uming.ttc", 0),
]


def _require_pil():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        sys.stderr.write("需要 Pillow：python3 -m pip install -i https://pypi.org/simple Pillow\n")
        sys.exit(2)
    return Image, ImageDraw, ImageFont


def load_font(ImageFont, size, bold=True):
    """载入中文字体；找不到任何候选时返回 None（调用方自行处理）。"""
    order = FONT_CANDIDATES if bold else list(reversed(FONT_CANDIDATES))
    for path, index in order:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=index)
            except Exception:
                continue
    return None


def _text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def make_digits(out_dir, cell_h, color, bold=True):
    """生成 0~9 的数字 PNG（透明底，白色描边效果由描边色实现）。

    每个数字都画进一个**统一尺寸**的方框并**严格居中**，保证：
      1) 数字绝不会被画到方框外（不裁切）；
      2) 切换造型时数字不会跳动、不会偏到边缘。
    以前出现过「数字显示不全」就是这里把文字偏移了 + padding 翻倍导致的。
    """
    Image, ImageDraw, ImageFont = _require_pil()
    os.makedirs(out_dir, exist_ok=True)
    font = load_font(ImageFont, cell_h, bold=bold)
    if font is None:
        sys.stderr.write("找不到中文字体，数字可能显示为方块\n")
        font = ImageFont.load_default()

    pad = max(3, cell_h // 12)
    cell_w = max(int(cell_h * 0.66), 24)   # 数字方框宽；窄字（如 1）也居中
    w = cell_w + pad * 2
    h = cell_h + pad * 2

    written = []
    for d in range(10):
        ch = str(d)
        probe = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        pd = ImageDraw.Draw(probe)
        tw, th = _text_size(pd, ch, font)
        # 把数字严格居中放进方框（不带任何魔法偏移）
        tx = (w - tw) / 2
        ty = (h - th) / 2
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        # 描边：先画多层偏移的深色轮廓，再画本体
        for dx in range(-pad, pad + 1):
            for dy in range(-pad, pad + 1):
                if dx * dx + dy * dy <= pad * pad:
                    dr.text((tx + dx, ty + dy), ch, font=font,
                            fill=(26, 28, 44, 255))
        dr.text((tx, ty), ch, font=font, fill=color)
        path = os.path.join(out_dir, "d%d.png" % d)
        img.save(path)
        written.append((path, img.size))
    for p, s in written:
        print("  %s  %dx%d" % (os.path.basename(p), s[0], s[1]))
    return [p for p, _ in written]


def make_counter(out_dir, max_val, cell_w, cell_h, color, bold=True):
    """生成 0..max_val 的「两位数牌面」PNG（每个数字用同样字体，排成一行）。"""
    Image, ImageDraw, ImageFont = _require_pil()
    os.makedirs(out_dir, exist_ok=True)
    font = load_font(ImageFont, cell_h, bold=bold)
    if font is None:
        sys.stderr.write("找不到中文字体，数字可能显示为方块\n")
        font = ImageFont.load_default()

    probe = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    pd = ImageDraw.Draw(probe)
    tw, th = _text_size(pd, "0", font)
    pad = max(3, cell_h // 12)
    dw = tw + pad * 2
    dh = th + pad * 2

    written = []
    for v in range(max_val + 1):
        # 固定两位：不足前面补 0，这样位数不会跳动
        s = "%02d" % v
        img = Image.new("RGBA", (dw * len(s), dh), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        for i, ch in enumerate(s):
            x = i * dw
            for dx in range(-pad, pad + 1):
                for dy in range(-pad, pad + 1):
                    if dx * dx + dy * dy <= pad * pad:
                        dr.text((x + pad + dx, pad + dy - 4), ch, font=font,
                                fill=(30, 32, 48, 255))
            dr.text((x + pad, pad - 4), ch, font=font, fill=color)
        path = os.path.join(out_dir, "n%02d.png" % v)
        img.save(path)
        written.append(path)
    print("  共 %d 张（0..%d），每张 %dx%d" % (len(written), max_val, dw * 2, dh))
    return written


def make_titlebg(out_path, w, h, title, subtitle, tip,
                 top, bottom, title_color, sub_color, tip_color):
    """生成整屏标题页（首页背景）：渐变底 + 主标题 + 副标题 + 操作提示。"""
    Image, ImageDraw, ImageFont = _require_pil()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    dr = ImageDraw.Draw(img)
    for y in range(h):
        t = y / float(max(1, h - 1))
        col = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(4))
        dr.line([(0, y), (w, y)], fill=col)
    # 几颗装饰星点
    for i in range(26):
        sx = (i * 97) % w
        sy = (i * 53) % h
        r = 2 + (i % 3)
        dr.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 255, 255, 60))
    tfont = load_font(ImageFont, int(h * 0.19))
    sfont = load_font(ImageFont, int(h * 0.058))
    pfont = load_font(ImageFont, int(h * 0.05))
    if tfont is None:
        tfont = ImageFont.load_default()
    if sfont is None:
        sfont = ImageFont.load_default()
    if pfont is None:
        pfont = ImageFont.load_default()
    for text, font, color, dy in ((title, tfont, title_color, 0.30),
                                   (subtitle, sfont, sub_color, 0.56),
                                   (tip, pfont, tip_color, 0.78)):
        if not text:
            continue
        tw, th = _text_size(dr, text, font)
        dr.text(((w - tw) // 2, int(h * dy)), text, font=font, fill=color)
    img.save(out_path)
    print("  %s  %dx%d  «%s»" % (os.path.basename(out_path), w, h, title))
    return out_path


def make_chatbox(out_path, w, h, fill, border, radius, border_w):
    """生成一个圆角对话框底板（半透明）。"""
    Image, ImageDraw, ImageFont = _require_pil()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([border_w, border_w, w - border_w - 1, h - border_w - 1],
                         radius=radius, fill=fill, outline=border, width=border_w)
    img.save(out_path)
    print("  %s  %dx%d" % (os.path.basename(out_path), w, h))
    return out_path


def make_chatlines(out_dir, lines, w, h, fill, border, radius, border_w,
                   font_size, text_color, name_prefix="", start_index=1):
    """为「自制聊天框」生成每一句台词的 PNG。

    对话不要用「说」气泡（气泡是 Scratch 内置造型，无法排版中文、
    也会挡住画面）。自制聊天框的做法是：
      · 一块底板 + 每句台词渲染成一张透明 PNG
      · 聊天框角色有 N+1 套造型：第 0 套是空底板，1..N 是各句台词
      · 用「换成 (计算值) 造型」按台词序号切换
    这里把台词图渲染好，文件名用**从 1 开始**的序号
    （chat_01.png / chat_02.png …），和造型序号一一对应。
    """
    Image, ImageDraw, ImageFont = _require_pil()
    os.makedirs(out_dir, exist_ok=True)
    font = load_font(ImageFont, font_size)
    if font is None:
        font = ImageFont.load_default()

    written = []
    for idx, text in enumerate(lines):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.rounded_rectangle([border_w, border_w, w - border_w - 1, h - border_w - 1],
                             radius=radius, fill=fill, outline=border, width=border_w)
        tw, th = _text_size(dr, text, font)
        dr.text(((w - tw) // 2, (h - th) // 2), text, font=font, fill=text_color)
        path = os.path.join(out_dir, "%s%02d.png" % (name_prefix, idx + start_index))
        img.save(path)
        written.append(path)
        print("  %s  %dx%d  «%s»" % (os.path.basename(path), w, h, text))
    return written


def make_chatblank(out_path, w, h, fill, border, radius, border_w):
    """生成空白聊天框底板（没有文字），用作「隐藏台词」时的造型。"""
    Image, ImageDraw, ImageFont = _require_pil()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle([border_w, border_w, w - border_w - 1, h - border_w - 1],
                         radius=radius, fill=fill, outline=border, width=border_w)
    img.save(out_path)
    print("  %s  %dx%d  （空白底板）" % (os.path.basename(out_path), w, h))
    return out_path


def make_panel(out_path, w, h, text, fill, border, radius, border_w,
               font_size, text_color, sub_text=None, sub_size=None,
               sub_color=None, bg_top=None, bg_bottom=None):
    """生成带文字的圆角面板（标题卡 / 按钮 / 消息条都靠它）。"""
    Image, ImageDraw, ImageFont = _require_pil()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    if bg_top is not None and bg_bottom is not None:
        # 竖向渐变底（标题卡用）
        for y in range(h):
            t = y / float(max(1, h - 1))
            col = tuple(int(bg_top[i] + (bg_bottom[i] - bg_top[i]) * t) for i in range(4))
            dr.line([(0, y), (w, y)], fill=col)
    else:
        dr.rounded_rectangle([border_w, border_w, w - border_w - 1, h - border_w - 1],
                             radius=radius, fill=fill, outline=border, width=border_w)
    font = load_font(ImageFont, font_size)
    if font is None:
        font = ImageFont.load_default()
    tw, th = _text_size(dr, text, font)
    tx = (w - tw) // 2
    if sub_text:
        sfont = load_font(ImageFont, sub_size or max(14, font_size // 2))
        if sfont is None:
            sfont = ImageFont.load_default()
        sw, sh = _text_size(dr, sub_text, sfont)
        ty = (h - th - sh) // 2
        dr.text((tx, ty), text, font=font, fill=text_color)
        dr.text(((w - sw) // 2, ty + th + 4), sub_text, font=sfont,
                fill=sub_color or text_color)
    else:
        ty = (h - th) // 2
        dr.text((tx, ty), text, font=font, fill=text_color)
    img.save(out_path)
    print("  %s  %dx%d  «%s»" % (os.path.basename(out_path), w, h, text))
    return out_path


# 大地图里 4 件家具的「世界规格」：名称、颜色、世界坐标矩形 (x1,y1,x2,y2)
# 家具必须做成**独立角色**才有碰撞箱 —— 画进地图图片里的家具是挡不住人的。
FURNITURE = [
    ("沙发", (120, 150, 200, 255), (-360, 140, -180, 240)),
    ("柜子", (150, 130, 190, 255), (160, 110, 340, 220)),
    ("书桌", (120, 180, 150, 255), (-320, -240, -120, -110)),
    ("地毯", (190, 160, 120, 255), (120, -260, 320, -100)),
]


def make_world(out_path, w=960, h=720, furniture=True):
    """生成「大地图」：一张比舞台(480x360)大的世界图，靠相机滚动来浏览。

    做法：世界坐标 x∈[-W/2, W/2], y∈[-H/2, H/2]。地图精灵把这个图当唯一造型，
    每帧放到 (-相机x, -相机y)，于是「世界点 P」就显示在屏幕 (P - 相机)。

    ⚠️ `furniture=False`（默认给大地图用）时**不画家具**：
    画进图片里的家具只是像素，**没有碰撞箱**，玩家会直接穿过去。
    想要能挡住路的家具，必须用 `make_furniture` 单独生成，
    在 IR 里做成**独立角色**，再用「碰到 [家具]?」检测。
    """
    Image, ImageDraw, ImageFont = _require_pil()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img = Image.new("RGBA", (w, h), (58, 74, 110, 255))
    dr = ImageDraw.Draw(img)
    grid = (90, 110, 150, 255)
    step = 60
    for x in range(0, w + 1, step):
        dr.line([(x, 0), (x, h)], fill=grid)
    for y in range(0, h + 1, step):
        dr.line([(0, y), (w, y)], fill=grid)
    wall = (36, 46, 70, 255)
    dr.rectangle([0, 0, w - 1, h - 1], outline=wall, width=18)
    if furniture:
        for name, c, (wx1, wy1, wx2, wy2) in FURNITURE:
            x0, y0 = wx1 + w // 2, h // 2 - wy2
            x1, y1 = wx2 + w // 2, h // 2 - wy1
            dr.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=c,
                                 outline=(20, 24, 40, 255), width=4)
    cx, cy = w // 2, h // 2
    dr.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], outline=(255, 220, 120, 255), width=6)
    dr.line([(cx, cy - 40), (cx, cy + 40)], fill=(255, 220, 120, 255), width=4)
    dr.line([(cx - 40, cy), (cx + 40, cy)], fill=(255, 220, 120, 255), width=4)
    img.save(out_path)
    print("  %s  %dx%d%s" % (os.path.basename(out_path), w, h,
                             "" if furniture else "（不含家具：家具要单独做成障碍角色）"))
    return out_path


def make_furniture(out_dir, w=960, h=720):
    """把大地图里的 4 件家具**各自单独生成 PNG**，用来做「独立障碍角色」。

    为什么必须单独生成：Scratch 的碰撞检测只发生在**角色之间**
    （「碰到 [某角色]?」）。画在地图图片里的家具只是像素，不会挡住任何人。
    所以每件家具都要是一个独立角色，存自己的世界坐标，
    每帧放到 (世界坐标 - 相机) 跟着地图滚动，再和玩家做「碰到」检测。

    生成的文件：assets 目录下 沙发.png / 柜子.png / 书桌.png / 地毯.png
    像素尺寸 = 世界尺寸（1:1），角色 size 保持 100 即为正确大小。
    """
    Image, ImageDraw = _require_pil()[:2]
    os.makedirs(out_dir, exist_ok=True)
    for name, c, (wx1, wy1, wx2, wy2) in FURNITURE:
        fw, fh = wx2 - wx1, wy2 - wy1
        img = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.rounded_rectangle([2, 2, fw - 3, fh - 3], radius=16, fill=c,
                             outline=(20, 24, 40, 255), width=4)
        # 顶部高光，让它看起来像有体积的家具
        dr.rounded_rectangle([10, 8, fw - 11, fh // 3], radius=12,
                             fill=(min(c[0] + 26, 255), min(c[1] + 26, 255),
                                   min(c[2] + 26, 255), 200))
        p = os.path.join(out_dir, "%s.png" % name)
        img.save(p)
        print("  %s.png  %dx%d  世界矩形 x[%d,%d] y[%d,%d]  中心(%d,%d)"
              % (name, fw, fh, wx1, wx2, wy1, wy2, (wx1 + wx2) // 2, (wy1 + wy2) // 2))
    return out_dir


def make_darkness(out_path, w=480, h=360, hole_r=70, alpha=225,
                  soft_edge=10):
    """生成「视野阴影」遮罩：整屏黑幕 + 正中央一个**透明圆洞**。

    社区标准做法（Scratch Wiki / 手电筒教程）：光不是真的光，而是
    「一块盖在最上面的黑布，中间挖了个透明的洞」，洞跟着玩家走。

    坑：Scratch 规定「精灵在任一轴上的可视尺寸不得超过舞台的 150%」，
    所以一块 480x360 的遮罩最多放到 150%（720x540），玩家走到边上就漏光。
    绕过办法（官方 Wiki 的 overriding the costume size limit）：
        先切成极小的造型 → 设 size 250% → 再切回这张黑幕造型
    （因为尺寸上限按「当前造型」算，用小造型就能设出超大尺寸）。

    注意：图片必须带 alpha 通道，洞要是**真透明**（alpha=0）而不是白色。
    """
    Image, ImageDraw = _require_pil()[:2]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img = Image.new("RGBA", (w, h), (0, 0, 0, alpha))
    dr = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2
    # 中心挖一个透明洞（逐层擦出软边，比直接挖硬边更像光锥）
    for i in range(soft_edge, 0, -1):
        r = hole_r + i
        a = int(alpha * (1 - i / float(soft_edge + 1)) * 0.55)
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, a))
    dr.ellipse([cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r], fill=(0, 0, 0, 0))
    img.save(out_path)
    print("  %s  %dx%d  洞半径=%d 透明度=%d" % (os.path.basename(out_path), w, h, hole_r, alpha))
    return out_path


def make_closebtn(out_path, size=28, color=(226, 78, 78, 255),
                  cross=(255, 255, 255, 255), width=4):
    """生成「关闭按钮」（弹窗右上角的 ×）：红色圆底 + 白色叉。"""
    Image, ImageDraw = _require_pil()[:2]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    m = size * 2
    dr.ellipse([m - size, m - size, m + size, m + size], fill=color,
               outline=(120, 30, 30, 255), width=3)
    r = size * 0.5
    dr.line([(m - r, m - r), (m + r, m + r)], fill=cross, width=width)
    dr.line([(m + r, m - r), (m - r, m + r)], fill=cross, width=width)
    img.save(out_path)
    print("  %s  %dx%d" % (os.path.basename(out_path), size * 4, size * 4))
    return out_path


def make_mask(out_path, w=480, h=360, alpha=110):
    """生成「UI 遮罩」：一整块半透明黑板。

    用途：**拦截穿透点击**。Scratch 里点到上层精灵，下层精灵也会收到点击，
    所以弹窗/暂停面板打开时必须盖一层遮罩，否则玩家点右上角「×」
    会顺手点中底下的游戏角色。

    alpha 建议 100~140：太黑看不清游戏，太透明又不够明显。
    """
    Image, ImageDraw = _require_pil()[:2]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img = Image.new("RGBA", (w, h), (0, 0, 0, alpha))
    ImageDraw.Draw(img)
    img.save(out_path)
    print("  %s  %dx%d  透明度=%d" % (os.path.basename(out_path), w, h, alpha))
    return out_path


def make_minimap(out_dir, mw=120, mh=90, world=None):
    """生成「小地图」：一张缩小的世界底图 + 猫/鼠两个标记点 PNG。

    底图比例 = mw / 世界宽。运行时把世界坐标按比例映射到这块底图上，
    再用两个始终「置顶」的小圆点角色标出猫和鼠的当前位置。
    """
    Image, ImageDraw, ImageFont = _require_pil()
    os.makedirs(out_dir, exist_ok=True)
    img = Image.new("RGBA", (mw, mh), (58, 74, 110, 255))
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, mw - 1, mh - 1], outline=(255, 255, 255, 160), width=2)
    dr.rectangle([15, 15, 40, 35], fill=(120, 150, 200, 255))
    dr.rectangle([80, 18, 105, 38], fill=(150, 130, 190, 255))
    dr.rectangle([20, 60, 45, 80], fill=(120, 180, 150, 255))
    dr.rectangle([78, 58, 103, 82], fill=(190, 160, 120, 255))
    dr.ellipse([mw // 2 - 5, mh // 2 - 5, mw // 2 + 5, mh // 2 + 5],
               outline=(255, 220, 120, 255), width=2)
    base = os.path.join(out_dir, "mini_map.png")
    img.save(base)
    print("  %s  %dx%d" % (os.path.basename(base), mw, mh))
    for name, color in (("cat_dot.png", (255, 150, 60, 255)),
                        ("mouse_dot.png", (210, 210, 210, 255))):
        d = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        dd = ImageDraw.Draw(d)
        dd.ellipse([1, 1, 14, 14], fill=color, outline=(20, 20, 20, 255), width=2)
        p = os.path.join(out_dir, name)
        d.save(p)
        print("  %s  16x16" % name)
    return base


def _parse_color(s):
    """支持 #rrggbb / #rrggbbaa / r,g,b[,a]。"""
    s = s.strip()
    if s.startswith("#"):
        s = s[1:]
        if len(s) == 6:
            s += "ff"
        if len(s) != 8:
            raise ValueError("颜色格式不对：%s" % s)
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4, 6))
    parts = [int(x) for x in s.replace(",", " ").split()]
    if len(parts) == 3:
        parts.append(255)
    if len(parts) != 4:
        raise ValueError("颜色格式不对：%s" % s)
    return tuple(parts)


def main():
    ap = argparse.ArgumentParser(description="生成 Scratch 角色显示文本/数字用的素材")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("digits", help="生成 0~9 数字图")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--size", type=int, default=48, help="数字高度（像素）")
    p.add_argument("--color", default="#ffffff", help="数字颜色")
    p.add_argument("--regular", action="store_true", help="用常规字重而非粗体")

    p = sub.add_parser("counter", help="生成 0~N 的两位数牌面")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--max", type=int, default=99, help="最大显示值")
    p.add_argument("--size", type=int, default=40, help="单个数字高度")
    p.add_argument("--color", default="#ffffff")

    p = sub.add_parser("titlebg", help="生成整屏标题页（首页背景）")
    p.add_argument("--out", required=True)
    p.add_argument("--w", type=int, default=480)
    p.add_argument("--h", type=int, default=360)
    p.add_argument("--title", default="")
    p.add_argument("--subtitle", default="")
    p.add_argument("--tip", default="")
    p.add_argument("--top", default="#4a6fd8ff")
    p.add_argument("--bottom", default="#1b2450ff")
    p.add_argument("--title-color", default="#ffffffff")
    p.add_argument("--sub-color", default="#dbe4ffff")
    p.add_argument("--tip-color", default="#b9c6f5ff")

    p = sub.add_parser("world", help="生成大地图（可滚动世界）PNG")
    p.add_argument("--out", required=True)
    p.add_argument("--w", type=int, default=960)
    p.add_argument("--h", type=int, default=720)
    p.add_argument("--with-furniture", action="store_true",
                   help="把家具直接画进地图（注意：这样家具没有碰撞箱，玩家能穿过去）")

    p = sub.add_parser("furniture", help="单独生成家具 PNG（做独立障碍角色用）")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--w", type=int, default=960)
    p.add_argument("--h", type=int, default=720)

    p = sub.add_parser("minimap", help="生成小地图底图与猫/鼠标记点")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--w", type=int, default=120)
    p.add_argument("--h", type=int, default=90)

    p = sub.add_parser("darkness", help="生成视野阴影遮罩（整屏黑幕+中央透明洞）")
    p.add_argument("--out", required=True)
    p.add_argument("--w", type=int, default=480)
    p.add_argument("--h", type=int, default=360)
    p.add_argument("--hole-r", type=int, default=70, help="透明洞半径（像素）")
    p.add_argument("--alpha", type=int, default=225, help="黑幕不透明度 0~255")
    p.add_argument("--soft-edge", type=int, default=10, help="洞口软边宽度（像素）")

    p = sub.add_parser("closebtn", help="生成弹窗右上角的关闭按钮（×）")
    p.add_argument("--out", required=True)
    p.add_argument("--size", type=int, default=28, help="圆形直径（生成图为其 4 倍）")
    p.add_argument("--color", default="#e24e4eff")
    p.add_argument("--cross", default="#ffffffff")
    p.add_argument("--width", type=int, default=4)

    p = sub.add_parser("mask", help="生成半透明遮罩板（拦截穿透点击）")
    p.add_argument("--out", required=True)
    p.add_argument("--w", type=int, default=480)
    p.add_argument("--h", type=int, default=360)
    p.add_argument("--alpha", type=int, default=110)

    p = sub.add_parser("chatbox", help="生成对话框底板")
    p.add_argument("--out", required=True)
    p.add_argument("--w", type=int, default=220)
    p.add_argument("--h", type=int, default=64)
    p.add_argument("--fill", default="#ffffffee")
    p.add_argument("--border", default="#3a3f58ff")
    p.add_argument("--radius", type=int, default=14)
    p.add_argument("--border-w", type=int, default=3)

    p = sub.add_parser("panel", help="生成带文字的圆角面板（标题卡/按钮/消息条）")
    p.add_argument("--out", required=True)
    p.add_argument("--w", type=int, default=320)
    p.add_argument("--h", type=int, default=80)
    p.add_argument("--text", default="")
    p.add_argument("--sub-text", default=None, help="副标题（第二行小字）")
    p.add_argument("--fill", default="#ffffffee")
    p.add_argument("--border", default="#3a3f58ff")
    p.add_argument("--radius", type=int, default=14)
    p.add_argument("--border-w", type=int, default=3)
    p.add_argument("--font-size", type=int, default=32)
    p.add_argument("--text-color", default="#2b3040ff")
    p.add_argument("--sub-size", type=int, default=16)
    p.add_argument("--sub-color", default="#5a6080ff")
    p.add_argument("--gradient-top", default=None, help="#rrggbbaa，做竖向渐变底")
    p.add_argument("--gradient-bottom", default=None)

    p = sub.add_parser("chatlines", help="生成自制聊天框的每句台词图")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--lines-file", required=True,
                   help="UTF-8 文本文件，一行一句台词（空行忽略）")
    p.add_argument("--w", type=int, default=300)
    p.add_argument("--h", type=int, default=64)
    p.add_argument("--fill", default="#ffffffee")
    p.add_argument("--border", default="#3a3f58ff")
    p.add_argument("--radius", type=int, default=14)
    p.add_argument("--border-w", type=int, default=3)
    p.add_argument("--font-size", type=int, default=22)
    p.add_argument("--text-color", default="#2b3040ff")
    p.add_argument("--prefix", default="chat_")
    p.add_argument("--blank", default=None,
                   help="额外生成一张空白底板（聊天框第 0 套造型）")

    args = ap.parse_args()
    color = _parse_color(args.color) if hasattr(args, "color") else None

    if args.cmd == "digits":
        print("生成数字图（0~9）-> %s" % args.out_dir)
        make_digits(args.out_dir, args.size, color, bold=not args.regular)
    elif args.cmd == "counter":
        print("生成数字牌面（0~%d）-> %s" % (args.max, args.out_dir))
        make_counter(args.out_dir, args.max, 0, args.size, color)
    elif args.cmd == "chatbox":
        print("生成对话框底板 -> %s" % args.out)
        make_chatbox(args.out, args.w, args.h, _parse_color(args.fill),
                     _parse_color(args.border), args.radius, args.border_w)
    elif args.cmd == "chatlines":
        print("生成聊天框台词图 -> %s" % args.out_dir)
        with open(args.lines_file, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
        make_chatlines(args.out_dir, lines, args.w, args.h,
                       _parse_color(args.fill), _parse_color(args.border),
                       args.radius, args.border_w, args.font_size,
                       _parse_color(args.text_color), args.prefix)
        if args.blank:
            make_chatblank(args.blank, args.w, args.h,
                           _parse_color(args.fill), _parse_color(args.border),
                           args.radius, args.border_w)
    elif args.cmd == "panel":
        print("生成文字面板 -> %s" % args.out)
        grad = None
        if args.gradient_top and args.gradient_bottom:
            grad = (_parse_color(args.gradient_top), _parse_color(args.gradient_bottom))
        make_panel(args.out, args.w, args.h, args.text,
                   _parse_color(args.fill), _parse_color(args.border),
                   args.radius, args.border_w, args.font_size,
                   _parse_color(args.text_color), args.sub_text, args.sub_size,
                   _parse_color(args.sub_color),
                   grad[0] if grad else None, grad[1] if grad else None)
    elif args.cmd == "titlebg":
        print("生成标题页背景 -> %s" % args.out)
        make_titlebg(args.out, args.w, args.h, args.title, args.subtitle, args.tip,
                     _parse_color(args.top), _parse_color(args.bottom),
                     _parse_color(args.title_color), _parse_color(args.sub_color),
                     _parse_color(args.tip_color))
    elif args.cmd == "world":
        print("生成大地图 -> %s" % args.out)
        make_world(args.out, args.w, args.h, furniture=args.with_furniture)
    elif args.cmd == "furniture":
        print("生成家具（独立障碍角色）-> %s" % args.out_dir)
        make_furniture(args.out_dir, args.w, args.h)
    elif args.cmd == "minimap":
        print("生成小地图 -> %s" % args.out_dir)
        make_minimap(args.out_dir, args.w, args.h)
    elif args.cmd == "darkness":
        print("生成视野阴影遮罩 -> %s" % args.out)
        make_darkness(args.out, args.w, args.h, args.hole_r, args.alpha,
                      args.soft_edge)
    elif args.cmd == "closebtn":
        print("生成关闭按钮 -> %s" % args.out)
        make_closebtn(args.out, args.size, _parse_color(args.color),
                      _parse_color(args.cross), args.width)
    elif args.cmd == "mask":
        print("生成 UI 遮罩 -> %s" % args.out)
        make_mask(args.out, args.w, args.h, args.alpha)


if __name__ == "__main__":
    main()
