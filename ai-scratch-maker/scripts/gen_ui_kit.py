#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""矢量 UI 素材套件生成器（第二十八册配套）。

产出 `examples/assets/uikit/` 下的**纯矢量**素材，直接给 Scratch 用：

    btn_{kind}_{state}_{size}.svg     按钮底板  4 类型 × 4 状态 × 3 尺寸
    panel_{name}.svg                  面板      4 个固定尺寸（Scratch 没有九宫格）
    bar_{kind}_{pct}.svg              进度条    10 档填充（换档而不是拉伸）
    icon_{name}_{tone}.svg            图标      18 个 × 2 色调，24 网格
    badge_{name}.svg / decor_{name}.svg  角标 / 装饰
    text_{slug}.png                   文字条    3× 超采样 + 描边（PIL，可选）

三条设计约束（`scripts/check_ui_assets.py` 会强制检查）：

1. **只用确定可控的 SVG 子集**：`path/rect/circle/ellipse/g/linearGradient/radialGradient`。
   **禁止** `<text>`（中文字体在 Scratch 造型链路里不可控）、`filter`（模糊/阴影在不同渲染路径下
   表现不一致，缩放时还会糊）、`mask`/`clipPath`/`pattern`。
2. **颜色只从 `references/ui-design-spec.md` §198 的 18 个 HEX 派生**
   （同色系调明度，不引入新色相）。唯一例外是 §199 的状态暖红 `#D9603F`。
3. **体积感靠叠加，不靠特效**。每块控件都是「投影 → 外描边 → 主体渐变 → 顶部高光 → 底部内阴影」
   五层叠出来的，零 filter。

用法:
    python scripts/gen_ui_kit.py                  # 输出到 examples/assets/uikit/
    python scripts/gen_ui_kit.py --out 某目录
    python scripts/gen_ui_kit.py --preview        # 额外生成 preview.html
"""
import argparse
import math
import os
import sys

# --------------------------------------------------------------------------- #
# 调色板：严格取自 ui-design-spec.md §198（18 色）+ §199 状态暖红
# --------------------------------------------------------------------------- #
PAL = {
    "yellow":        "#FFCF4D",
    "yellow_light":  "#FFEDB3",
    "yellow_pale":   "#FAF19B",
    "ink":           "#4F4A47",
    "green":         "#32AF00",
    "green_bright":  "#5FD100",
    "green_soft":    "#8CE243",
    "green_lime":    "#C6FF2A",
    "green_deep":    "#216E09",
    "teal":          "#3A8E7D",
    "teal_light":    "#5CD9BA",
    "teal_pale":     "#C4FFE3",
    "teal_mint":     "#67F6D5",
    "teal_deep":     "#2F7365",
    "gray_warm":     "#767171",
    "gray_warm2":    "#675D5D",
    "gray":          "#7F7F7F",
}
# §199 状态色：唯一允许的 18 色之外的扩展（仅错误/危险）
DANGER = "#D9603F"
ALLOWED = {v.lower() for v in PAL.values()} | {DANGER.lower()}


def _clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(round(v))))


def hex2rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb2hex(r, g, b):
    return "#%02X%02X%02X" % (_clamp(r), _clamp(g), _clamp(b))


def shade(color, f):
    """f > 0 变亮（朝白），f < 0 变暗（朝黑）。f 取 -1..1。

    这是「18 色做出 5 阶明度」的唯一手段：只改明度，不改色相，
    所以整套素材看上去是同一个色系，而不是「调色板打架」。
    """
    r, g, b = hex2rgb(color)
    if f >= 0:
        return rgb2hex(r + (255 - r) * f, g + (255 - g) * f, b + (255 - b) * f)
    k = 1 + f
    return rgb2hex(r * k, g * k, b * k)


def mix(c1, c2, t):
    r1, g1, b1 = hex2rgb(c1)
    r2, g2, b2 = hex2rgb(c2)
    return rgb2hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def desaturate(color, t=0.75):
    """去饱和：向同亮度灰靠拢（disabled 态用）。"""
    r, g, b = hex2rgb(color)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return rgb2hex(r + (lum - r) * t, g + (lum - g) * t, b + (lum - b) * t)


# --------------------------------------------------------------------------- #
# SVG 构造小工具
# --------------------------------------------------------------------------- #
class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.defs = []
        self.body = []
        self._n = 0

    def _id(self, prefix):
        self._n += 1
        return "%s%d" % (prefix, self._n)

    def lin(self, stops, x1=0, y1=0, x2=0, y2=1):
        """垂直线性渐变。stops = [(offset, color, opacity), ...]"""
        gid = self._id("lg")
        s = ['<linearGradient id="%s" x1="%s" y1="%s" x2="%s" y2="%s">' %
             (gid, x1, y1, x2, y2)]
        for item in stops:
            off, col = item[0], item[1]
            op = item[2] if len(item) > 2 else 1
            s.append('<stop offset="%s" stop-color="%s" stop-opacity="%s"/>' % (off, col, op))
        s.append("</linearGradient>")
        self.defs.append("".join(s))
        return "url(#%s)" % gid

    def rad(self, stops, cx=0.5, cy=0.5, r=0.5):
        gid = self._id("rg")
        s = ['<radialGradient id="%s" cx="%s" cy="%s" r="%s">' % (gid, cx, cy, r)]
        for item in stops:
            off, col = item[0], item[1]
            op = item[2] if len(item) > 2 else 1
            s.append('<stop offset="%s" stop-color="%s" stop-opacity="%s"/>' % (off, col, op))
        s.append("</radialGradient>")
        self.defs.append("".join(s))
        return "url(#%s)" % gid

    def add(self, s):
        self.body.append(s)

    def rect(self, x, y, w, h, rx=0, fill="none", stroke=None, sw=0, opacity=None):
        a = ['<rect x="%s" y="%s" width="%s" height="%s"' % (_f(x), _f(y), _f(w), _f(h))]
        if rx:
            a.append(' rx="%s"' % _f(rx))
        a.append(' fill="%s"' % fill)
        if stroke:
            a.append(' stroke="%s" stroke-width="%s"' % (stroke, _f(sw)))
        if opacity is not None:
            a.append(' opacity="%s"' % opacity)
        a.append("/>")
        self.add("".join(a))

    def render(self):
        head = ('<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
                'width="%s" height="%s" viewBox="0 0 %s %s">' %
                (_f(self.w), _f(self.h), _f(self.w), _f(self.h)))
        parts = [head]
        if self.defs:
            parts.append("<defs>" + "".join(self.defs) + "</defs>")
        parts.extend(self.body)
        parts.append("</svg>")
        return "\n".join(parts)


def _f(v):
    """数字格式化：去掉无意义的小数尾巴，避免 SVG 里出现 12.000000000000002。"""
    if isinstance(v, int):
        return str(v)
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


# --------------------------------------------------------------------------- #
# 按钮：4 类型 × 4 状态 × 3 尺寸
# --------------------------------------------------------------------------- #
BTN_SIZES = {"s": (120, 44), "m": (180, 56), "l": (260, 68)}
BTN_KINDS = {
    "primary":   PAL["yellow"],      # 主操作键（§197：黄=主操作，不做主体色）
    "secondary": PAL["teal"],        # 主体大模块
    "success":   PAL["green_bright"],# 次要 / 验证通过
    "ghost":     PAL["gray_warm2"],        # 设置类 / 弱化
    "danger":    DANGER,             # §199 状态暖红（唯一扩展色）
}
BTN_STATES = ("normal", "hover", "pressed", "disabled")


def button_svg(w, h, base, state):
    """按钮底板：五层叠加做出体积感，无 filter。

    层序（从下往上，顺序不能换）：
        ① 投影        黑色 18%，y 偏移 3，圆角比本体大 1
        ② 外描边      基色暗 42%，宽 2.5（这是「有厚度」的关键，纯平涂最缺这一层）
        ③ 主体渐变    顶 = 基色 +10%，底 = 基色 −14%
        ④ 顶部高光    白色 26%，高 ≈ 本体 26%，两侧内缩
        ⑤ 底部内阴影  黑色 14%，贴底，制造「凹进去」的错觉
    """
    s = Svg(w, h)
    r = h * 0.30                      # 按钮圆角 = 短边 30%（控件比窗口更圆）
    if state == "disabled":
        # 去饱和 0.62 就够：去太狠会变成纯白，玩家分不出这是哪个按钮
        base = desaturate(base, 0.62)
    lift = 0.0 if state in ("pressed",) else 3.0
    if state == "hover":
        base = shade(base, 0.10)          # 悬停要看得见
    if state == "pressed":
        base = shade(base, -0.10)         # 按下要明确变暗

    ink = shade(base, -0.45)
    # ★ pressed 的渐变必须**反转**（上暗下亮）：光从上面来，凹进去的东西上沿在阴影里。
    #   不反转的话，按下只是「变暗一点」，玩家感觉不到「按了」。
    top = shade(base, 0.12 if state != "pressed" else -0.16)
    bot = shade(base, -0.15 if state != "pressed" else 0.10)

    # ① 投影：按下时收掉，视觉上「按进去了」
    if state != "pressed" and state != "disabled":
        s.rect(0, lift, w, h, rx=r, fill="#000000", opacity=0.18)
    oy = 2.0 if state == "pressed" else 0.0

    # ② 外描边（深 42%）—— 这一层让按钮「有边」，否则在浅背景上会糊成一团
    s.rect(0, oy, w, h, rx=r, fill=ink)
    # ③ 主体渐变（内缩 2.5 = 描边宽度）
    bw = 2.5
    body = s.rect(bw, oy + bw, w - bw * 2, h - bw * 2, rx=max(0, r - bw),
                  fill=s.lin([("0", top), ("1", bot)]))
    # ④ 顶部高光（只在上半部，且左右内缩更多，像圆柱受光）
    gh = (h - bw * 2) * 0.42
    s.rect(bw + 4, oy + bw + 1.5, w - (bw + 4) * 2, gh,
           rx=max(0, r - bw - 2), fill="#FFFFFF",
           opacity=0.26 if state != "pressed" else 0.05)
    # ⑤ 底部内阴影（贴底，短一点，像被压住）
    sh = (h - bw * 2) * 0.22
    s.rect(bw + 2, oy + h - bw - sh - 1, w - (bw + 2) * 2, sh,
           rx=max(0, r - bw - 1), fill="#000000",
           opacity=0.10 if state != "pressed" else 0.18)
    if state == "disabled":
        # disabled 整体压一层浅灰蒙版（不用 filter，用半透明矩形）
        s.rect(0, 0, w, h, rx=r, fill="#FFFFFF", opacity=0.30)
    return s.render()


# --------------------------------------------------------------------------- #
# 面板：Scratch 没有九宫格，只能出成套固定尺寸
# --------------------------------------------------------------------------- #
PANELS = {
    "toast":  (260, 72, 12),
    "tip":    (320, 96, 12),
    "card":   (360, 200, 14),
    "dialog": (440, 280, 18),
}


def panel_svg(w, h, rx, accent=None, kind="normal"):
    """面板：投影 + 外描边 + 渐变底 + 顶部内高光 + 底部内阴影 + 四角点缀。

    小窗（toast/tip）用浅底深字；大窗（dialog）用 25% 透明感（§201）：
    这里用「深底 + 低不透明度」表达，Scratch 里再叠角色 GHOST=25。
    """
    s = Svg(w, h)
    accent = accent or PAL["teal"]
    deep = kind == "dialog"
    base = PAL["ink"] if deep else "#FFFDF7"
    edge = shade(accent, -0.30) if not deep else shade(accent, -0.55)
    top = shade(base, 0.06 if not deep else 0.10)
    bot = shade(base, -0.06 if not deep else -0.10)

    s.rect(0, 4, w, h, rx=rx, fill="#000000", opacity=0.20)          # 投影
    s.rect(0, 0, w, h, rx=rx, fill=edge)                             # 外描边
    bw = 3
    s.rect(bw, bw, w - bw * 2, h - bw * 2, rx=max(0, rx - bw),       # 主体
           fill=s.lin([("0", top), ("1", bot)]))
    # 顶部内高光：一条细长圆角，亮面
    s.rect(bw + 6, bw + 2, w - (bw + 6) * 2, 4, rx=2,
           fill="#FFFFFF", opacity=0.22 if not deep else 0.14)
    # 底部内阴影
    s.rect(bw + 4, h - bw - 8, w - (bw + 4) * 2, 5, rx=2.5,
           fill="#000000", opacity=0.10 if not deep else 0.18)
    # 四角点缀：短角标（比整圈描边轻，但立刻「有设计」）
    cl = max(10, min(w, h) * 0.12)
    cw = 3
    for (cx, cy, dx, dy) in ((bw + 4, bw + 4, 1, 1), (w - bw - 4, bw + 4, -1, 1),
                             (bw + 4, h - bw - 4, 1, -1), (w - bw - 4, h - bw - 4, -1, -1)):
        x1 = cx if dx > 0 else cx - cl
        y1 = cy if dy > 0 else cy - cw
        s.rect(x1, y1, cl, cw, rx=cw / 2, fill=accent, opacity=0.85)
        x2 = cx if dx > 0 else cx - cw
        y2 = cy if dy > 0 else cy - cl
        s.rect(x2, y2, cw, cl, rx=cw / 2, fill=accent, opacity=0.85)
    return s.render()


# --------------------------------------------------------------------------- #
# 进度条：10 档填充（换档，不拉伸）
# --------------------------------------------------------------------------- #
BAR_SPECS = {
    "hp":  (240, 22, PAL["green_bright"]),
    "xp":  (240, 14, PAL["teal_light"]),
    "boss":(320, 26, DANGER),
}


def bar_svg(kind, pct):
    w, h, base = BAR_SPECS[kind]
    s = Svg(w, h)
    r = h / 2
    # 轨道：外描边 + 内凹（顶部压暗、底部提亮 = 凹槽）
    s.rect(0, 0, w, h, rx=r, fill=shade(PAL["ink"], 0.25))
    s.rect(2, 2, w - 4, h - 4, rx=r - 2,
           fill=s.lin([("0", shade(base, -0.55)), ("1", shade(base, -0.72))]))
    s.rect(4, 3, w - 8, (h - 6) * 0.45, rx=(h - 6) * 0.22, fill="#000000", opacity=0.22)
    if pct <= 0:
        return s.render()
    # 填充：宽度按档，圆角跟着变（避免了「拉伸导致圆角变形」）
    fw = max(h, (w - 6) * pct / 100.0)
    fx, fy, fh = 3, 3, h - 6
    fr = fh / 2
    s.rect(fx, fy, fw, fh, rx=fr, fill=shade(base, -0.30))
    s.rect(fx + 1.5, fy + 1.5, fw - 3, fh - 3, rx=fr - 1.5,
           fill=s.lin([("0", shade(base, 0.14)), ("1", shade(base, -0.12))]))
    s.rect(fx + 5, fy + 2.5, max(0, fw - 10), fh * 0.34, rx=fh * 0.17,
           fill="#FFFFFF", opacity=0.34)      # 高光
    return s.render()


# --------------------------------------------------------------------------- #
# 图标：24 网格 / 线宽 2 / round cap
# --------------------------------------------------------------------------- #
def star_path(cx, cy, r_out, r_in, points=5, rot=-90):
    pts = []
    for i in range(points * 2):
        ang = math.radians(rot + i * 180.0 / points)
        rr = r_out if i % 2 == 0 else r_in
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d = "M%s %s" % (_f(pts[0][0]), _f(pts[0][1]))
    for p in pts[1:]:
        d += " L%s %s" % (_f(p[0]), _f(p[1]))
    return d + " Z"


def gear_path(cx, cy, r_out, r_in, teeth=8, rot=0):
    """齿轮：内外半径交替 + 齿顶做成梯形（比纯多边形更像齿轮）。"""
    step = 360.0 / teeth
    pts = []
    for i in range(teeth):
        a0 = rot + i * step
        for (frac, rr) in ((0.00, r_in), (0.16, r_out), (0.36, r_out), (0.52, r_in)):
            ang = math.radians(a0 + frac * step)
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d = "M%s %s" % (_f(pts[0][0]), _f(pts[0][1]))
    for p in pts[1:]:
        d += " L%s %s" % (_f(p[0]), _f(p[1]))
    return d + " Z"


STROKE_ICONS = {
    "close":   '<path d="M7 7 L17 17 M17 7 L7 17"/>',
    "back":    '<path d="M15 5 L8 12 L15 19"/>',
    "next":    '<path d="M9 5 L16 12 L9 19"/>',
    "up":      '<path d="M5 15 L12 8 L19 15"/>',
    "down":    '<path d="M5 9 L12 16 L19 9"/>',
    "check":   '<path d="M5 12.5 L10 17.5 L19 6.5"/>',
    "plus":    '<path d="M12 5 L12 19 M5 12 L19 12"/>',
    "minus":   '<path d="M5 12 L19 12"/>',
    "menu":    '<path d="M5 7 L19 7 M5 12 L19 12 M5 17 L19 17"/>',
    "refresh": '<path d="M19 12 A7 7 0 1 1 16.5 6.6"/><path d="M16.5 3 L16.5 7.2 L12.3 7.2"/>',
    "sound":   '<path d="M5 10 L9 10 L14 6 L14 18 L9 14 L5 14 Z"/>'
               '<path d="M17 9 A4 4 0 0 1 17 15"/>',
    "mute":    '<path d="M5 10 L9 10 L14 6 L14 18 L9 14 L5 14 Z"/><path d="M17 9 L21 15 M21 9 L17 15"/>',
    "lock":    '<rect x="5" y="11" width="14" height="9" rx="2.5"/>'
               '<path d="M8.5 11 L8.5 8 A3.5 3.5 0 0 1 15.5 8 L15.5 11"/>',
    "unlock":  '<rect x="5" y="11" width="14" height="9" rx="2.5"/>'
               '<path d="M8.5 11 L8.5 8 A3.5 3.5 0 0 1 15.5 8"/>',
    "clock":   '<circle cx="12" cy="12" r="8"/><path d="M12 7.5 L12 12 L15.5 14"/>',
    "home":    '<path d="M4 11.5 L12 4.5 L20 11.5"/><path d="M7 11 L7 19.5 L17 19.5 L17 11"/>',
    "user":    '<circle cx="12" cy="8.5" r="3.6"/><path d="M5 19.5 A7 7 0 0 1 19 19.5"/>',
    "info":    '<circle cx="12" cy="12" r="8"/><path d="M12 11 L12 16.5"/>'
               '<circle cx="12" cy="7.6" r="1"/>',
    "map":     '<path d="M4 7 L9 4.5 L15 7 L20 4.5 L20 17 L15 19.5 L9 17 L4 19.5 Z"/>'
               '<path d="M9 4.5 L9 17 M15 7 L15 19.5"/>',
    "bag":     '<path d="M5.5 8.5 L18.5 8.5 L20 20 L4 20 Z"/><path d="M9 8.5 A3 3 0 0 1 15 8.5"/>',
    "sword":   '<path d="M18.5 4.5 L11 12"/><path d="M9 10 L14 15"/><path d="M10.5 13.5 L5 19"/>',
    "shield":  '<path d="M12 4 L19 7 L19 12.5 C19 16.5 15.8 19 12 20.5 '
               'C8.2 19 5 16.5 5 12.5 L5 7 Z"/>',
    "heart":   '<path d="M12 19.5 C4 14 4.5 8 8 6.8 C10 6.1 11.4 7.4 12 8.6 '
               'C12.6 7.4 14 6.1 16 6.8 C19.5 8 20 14 12 19.5 Z"/>',
    "trophy":  '<path d="M7 5 L17 5 L17 10 A5 5 0 0 1 7 10 Z"/>'
               '<path d="M7 6.5 L4.5 6.5 L4.5 8.5 A3 3 0 0 0 7.5 11.5"/>'
               '<path d="M17 6.5 L19.5 6.5 L19.5 8.5 A3 3 0 0 1 16.5 11.5"/>'
               '<path d="M12 15 L12 18.5 M9 19.5 L15 19.5"/>',
    "settings":'<path d="%s"/><circle cx="12" cy="12" r="3.2"/>' % gear_path(12, 12, 9.2, 7.2, 8, -90),
    "star":    '<path d="%s"/>' % star_path(12, 12.4, 8.4, 3.6),
    "coin":    '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4.6"/>',
    "play":    '<path d="M8.5 5.5 L18.5 12 L8.5 18.5 Z"/>',
    "pause":   '<path d="M9 5.5 L9 18.5 M15 5.5 L15 18.5"/>',
    "stop":    '<rect x="6.5" y="6.5" width="11" height="11" rx="2"/>',
}


def icon_svg(name, tone="light", scale=1.0, sw=2.0):
    """图标：24 网格，stroke-linecap/join = round。tone = light（浅色）/ dark（深色）/ accent。"""
    colors = {"light": "#FFFFFF", "dark": PAL["ink"], "accent": PAL["teal"]}
    col = colors.get(tone, "#FFFFFF")
    s = Svg(24 * scale, 24 * scale)
    body = STROKE_ICONS[name]
    s.add('<g transform="scale(%s)" fill="none" stroke="%s" stroke-width="%s" '
          'stroke-linecap="round" stroke-linejoin="round">%s</g>' %
          (_f(scale), col, _f(sw), body))
    return s.render()


# --------------------------------------------------------------------------- #
# 角标 / 装饰
# --------------------------------------------------------------------------- #
def badge_new():
    """右上角「NEW」角标：缎带 + 折角，纯几何。"""
    s = Svg(72, 48)
    s.rect(6, 6, 60, 26, rx=7, fill=s.lin([("0", DANGER), ("1", shade(DANGER, -0.22))]))
    s.rect(10, 9, 52, 9, rx=4.5, fill="#FFFFFF", opacity=0.28)
    # 两条缎带尾巴
    s.add('<path d="M14 30 L20 30 L20 44 L14 40 Z" fill="%s"/>' % shade(DANGER, -0.30))
    s.add('<path d="M58 30 L52 30 L52 44 L58 40 Z" fill="%s"/>' % shade(DANGER, -0.30))
    return s.render()


def badge_star_rating():
    """三星评级底座：三颗星 + 底板。"""
    s = Svg(120, 40)
    s.rect(0, 6, 120, 28, rx=14, fill=PAL["ink"], opacity=0.55)
    for i, cx in enumerate((32, 60, 88)):
        s.add('<path d="%s" fill="%s" stroke="%s" stroke-width="1.5"/>'
              % (star_path(cx, 20, 9, 3.9), PAL["yellow"], shade(PAL["yellow"], -0.35)))
    return s.render()


def decor_glow():
    """径向光斑：做「光源 / 高亮区」氛围，比贴一张模糊图轻。"""
    s = Svg(160, 160)
    s.rect(0, 0, 160, 160, rx=80,
           fill=s.rad([("0", "#FFFFFF", 0.55), ("0.55", PAL["yellow_light"], 0.18),
                       ("1", PAL["yellow_light"], 0)]))
    return s.render()


def decor_spark():
    """四角星芒：比圆点有「闪耀感」，可散落做粒子。"""
    s = Svg(32, 32)
    s.add('<path d="M16 2 L18.6 13.4 L30 16 L18.6 18.6 L16 30 L13.4 18.6 L2 16 L13.4 13.4 Z" '
          'fill="#FFFFFF" opacity="0.95"/>')
    s.add('<circle cx="16" cy="16" r="3.2" fill="#FFFFFF"/>')
    return s.render()


def decor_ribbon():
    """标题缎带：承载标题文字的底，中间宽、两端燕尾。"""
    s = Svg(300, 64)
    base = PAL["teal_light"]
    s.add('<path d="M18 10 L282 10 L282 54 L18 54 L2 32 Z" fill="%s"/>' % PAL["teal_deep"])
    s.add('<path d="M22 14 L278 14 L278 50 L22 50 L8 32 Z" fill="%s"/>'
          % s.lin([("0", shade(base, 0.10)), ("1", shade(base, -0.16))]))
    s.rect(30, 18, 240, 7, rx=3.5, fill="#FFFFFF", opacity=0.34)
    s.rect(30, 41, 240, 5, rx=2.5, fill="#000000", opacity=0.10)
    return s.render()


def bg_menu(w=480, h=360):
    """菜单背景：径向渐变 + 三圈弧线 + 底部压暗。

    背景的三个硬要求（§260）：尺寸是舞台整数倍、主视觉留白、对比度比 UI 低。
    这里把「视觉内容」全推到边缘，中间完全留白给标题和按钮。
    """
    s = Svg(w, h)
    s.rect(0, 0, w, h, fill=s.rad([("0", shade(PAL["teal"], 0.22)),
                                   ("0.55", PAL["teal"]),
                                   ("1", PAL["teal_deep"])], cx=0.5, cy=0.18, r=0.95))
    # 三圈同心弧：给画面「纵深」，但不抢注意力（透明度都低于 0.12）
    for i, rr in enumerate((110, 170, 235)):
        s.add('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" '
              'stroke-width="%s" opacity="%s"/>' %
              (_f(w * 0.5), _f(h * 0.12), rr, PAL["teal_pale"],
               _f(1.6), _f(0.12 - i * 0.03)))
    # 底部压暗：让底部提示文字有对比
    s.rect(0, h - 96, w, 96, fill=s.lin([("0", "#000000", 0), ("1", "#000000", 0.34)]))
    # 左右两条竖边光带
    s.rect(0, 0, 6, h, fill=shade(PAL["teal"], 0.25), opacity=0.25)
    s.rect(w - 6, 0, 6, h, fill=shade(PAL["teal"], 0.25), opacity=0.25)
    return s.render()


def btn_close(size=44):
    """关闭按钮：圆底 + X。§201 要求大窗口右上角必须有 ≥80% 透明的关闭图标。"""
    s = Svg(size, size)
    r = size / 2
    s.add('<circle cx="%s" cy="%s" r="%s" fill="#000000" opacity="0.20"/>'
          % (_f(r), _f(r + 1.5), _f(r - 1)))
    s.rect(1, 1, size - 2, size - 2, rx=r - 1, fill=PAL["ink"])
    s.rect(2.5, 2.5, size - 5, size - 5, rx=r - 2.5,
           fill=s.lin([("0", shade(PAL["ink"], 0.18)), ("1", shade(PAL["ink"], -0.12))]))
    s.add('<path d="M%s %s L%s %s M%s %s L%s %s" stroke="#FFFFFF" stroke-width="3.2" '
          'stroke-linecap="round"/>' %
          (_f(size * 0.32), _f(size * 0.32), _f(size * 0.68), _f(size * 0.68),
           _f(size * 0.68), _f(size * 0.32), _f(size * 0.32), _f(size * 0.68)))
    return s.render()


def decor_mask(w=480, h=360, alpha=0.55):
    """弹窗遮罩：480×360 半透明黑。用它把背景压下去，弹窗才有「浮起来」的感觉。"""
    s = Svg(w, h)
    s.rect(0, 0, w, h, fill="#000000", opacity=alpha)
    return s.render()


def decor_corner():
    """面板角饰：一对斜角括号，替代「整圈加粗描边」。"""
    s = Svg(40, 40)
    for (x, y, sx, sy) in ((6, 6, 1, 1), (34, 34, -1, -1)):
        s.add('<path d="M%s %s L%s %s L%s %s" fill="none" stroke="%s" stroke-width="3.5" '
              'stroke-linecap="round" stroke-linejoin="round"/>'
              % (_f(x), _f(y + 12 * sy), _f(x), _f(y), _f(x + 12 * sx), _f(y), PAL["yellow"]))
    return s.render()


# --------------------------------------------------------------------------- #
# 文字条：3× 超采样 + 描边（PIL）
# --------------------------------------------------------------------------- #
FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
]


def load_font(size):
    from PIL import ImageFont
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def render_text_png(text, out_path, font_px=28, color="#FFFFFF", stroke="#4F4A47",
                    stroke_w=3, scale=3, pad=6):
    """文字条：先按 scale 倍画，再 LANCZOS 缩回 —— 这是「小字号不糊」的唯一办法。

    直接按目标字号画，中文的横竖笔画会掉像素，边缘出锯齿或断笔。
    3 倍超采样后缩回，相当于免费拿到 3× 抗锯齿。
    """
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return False
    big = font_px * scale
    font = load_font(big)
    if font is None:
        return False
    sw = stroke_w * scale
    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    box = d.textbbox((0, 0), text, font=font, stroke_width=sw)
    tw, th = box[2] - box[0], box[3] - box[1]
    W = tw + pad * 2 * scale
    H = th + pad * 2 * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((pad * scale - box[0], pad * scale - box[1]), text, font=font,
           fill=color, stroke_width=sw, stroke_fill=stroke)
    img = img.resize((max(1, W // scale), max(1, H // scale)), Image.LANCZOS)
    img.save(out_path)
    return True


def slugify(text):
    keep = []
    for ch in text:
        if ch.isalnum() or ch in "-_":
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep).strip("_") or "text"


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    out = args.out or os.path.join(os.getcwd(), "examples", "assets", "uikit")
    os.makedirs(out, exist_ok=True)
    n = 0

    def w(name, content):
        nonlocal n
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(content)
        n += 1

    # 按钮
    for kind, base in BTN_KINDS.items():
        for size, (bw, bh) in BTN_SIZES.items():
            for state in BTN_STATES:
                w("btn_%s_%s_%s.svg" % (kind, state, size), button_svg(bw, bh, base, state))

    # 面板
    for name, (pw, ph, prx) in PANELS.items():
        acc = PAL["yellow"] if name in ("dialog",) else PAL["teal"]
        w("panel_%s.svg" % name, panel_svg(pw, ph, prx, accent=acc,
                                           kind="dialog" if name == "dialog" else "normal"))

    # 进度条
    for kind in BAR_SPECS:
        for pct in (0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100):
            w("bar_%s_%03d.svg" % (kind, pct), bar_svg(kind, pct))

    # 图标（浅色 + 深色）
    for name in STROKE_ICONS:
        for tone in ("light", "dark"):
            w("icon_%s_%s.svg" % (name, tone), icon_svg(name, tone))

    # 角标 / 装饰
    w("badge_new.svg", badge_new())
    w("badge_stars.svg", badge_star_rating())
    w("decor_glow.svg", decor_glow())
    w("decor_spark.svg", decor_spark())
    w("decor_ribbon.svg", decor_ribbon())
    w("decor_corner.svg", decor_corner())
    w("decor_mask.svg", decor_mask())
    w("bg_menu.svg", bg_menu())
    w("ctrl_close.svg", btn_close())

    # 文字条（PIL 可选）
    # 文字条按「字号」分别出图：按钮字 / 标题字 / 大标题字，不靠缩放复用
    # （缩放会把描边一起缩掉，小字号会糊）
    # 文字条按「文案 × 字号 × 底色」分别出图。d = 深字（配浅底），l = 浅字（配深底）。
    # ⚠️ 不要用一张白字图去配浅底面板：描边再粗也会「发灰」。
    texts = [
        ("开始游戏", 30, "d"), ("开始游戏", 20, "d"), ("设置", 17, "d"),
        ("继续", 17, "l"), ("游戏结束", 40, "l"), ("游戏结束", 28, "d"),
        ("恭喜通关", 22, "d"), ("设置", 28, "l"),
        ("继续", 16, "d"), ("退出", 17, "l"),
    ]
    made = 0
    for t, px, tone in texts:
        p = os.path.join(out, "text_%s_%d_%s.png" % (slugify(t), px, tone))
        col, st = ("#4F4A47", "#FFFDF7") if tone == "d" else ("#FFFFFF", PAL["ink"])
        if render_text_png(t, p, font_px=px, color=col, stroke=st, stroke_w=2):
            made += 1
    print("素材已生成: %s" % out)
    print("  按钮 %d · 面板 %d · 进度条 %d · 图标 %d · 装饰 7 · 背景 1 · 关闭键 1 · 文字 %d"
          % (len(BTN_KINDS) * len(BTN_SIZES) * len(BTN_STATES), len(PANELS),
             len(BAR_SPECS) * 11, len(STROKE_ICONS) * 2, made))
    print("  合计 %d 个文件" % n)
    if args.preview:
        pv = os.path.join(out, "preview.html")
        with open(pv, "w", encoding="utf-8") as f:
            f.write(build_preview())
        print("  预览: %s" % pv)


HTML_TPL = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>UI Kit 预览</title>
<style>
 html{zoom:.56}
 @media (min-width:1200px){ html{zoom:1} }
 body{margin:0;background:#2B2724;font:14px/1.65 "Microsoft YaHei",sans-serif;color:#EDE6DC}
 .wrap{max-width:1060px;margin:0 auto;padding:30px 30px 60px}
 h2{color:#FFCF4D;font-size:14px;letter-spacing:2px;margin:36px 0 6px;font-weight:600}
 .hint{font-size:12px;color:#8E8478;margin:0 0 14px}
 .scr{position:relative;width:960px;height:540px;border-radius:20px;overflow:hidden;
      background:radial-gradient(115% 85% at 50% 0%, #3A8E7D 0%, #2F7365 52%, #262220 100%);
      box-shadow:0 20px 55px rgba(0,0,0,.5)}
 .abs{position:absolute}
 .btn{position:absolute;display:flex;align-items:center;justify-content:center}
 .btn .bg{position:absolute;left:0;top:0;width:100%;height:100%}
 .btn .tx{position:relative}
 .pnl{position:relative;display:flex;align-items:center;justify-content:center;
      flex-direction:column;gap:10px}
 .pnl .bg{position:absolute;left:0;top:0;width:100%;height:100%}
 .pnl .tx,.pnl .row{position:relative}
 .pnl .row{display:flex;gap:12px;align-items:center}
 .ribbon{position:absolute;left:330px;top:46px;width:300px;height:64px;display:flex;
         align-items:center;justify-content:center}
 .ribbon .bg{position:absolute;left:0;top:0;width:100%;height:100%}
 .ribbon .tx{position:relative;margin-top:-4px}
 .matrix{display:grid;grid-template-columns:92px repeat(4,190px);gap:10px 16px;
         align-items:center;margin-bottom:6px}
 .matrix .st{font-size:11px;color:#8E8478;letter-spacing:1px}
 .matrix .tag{font-size:12px;color:#FFCF4D;font-family:Consolas,monospace}
 .matrix .v img{display:block}
 .row{display:flex;gap:16px;align-items:flex-end;flex-wrap:wrap}
 .bar{text-align:center}
 .bar img{display:block;margin-bottom:4px}
 .bar em{font-style:normal;font-size:11px;color:#8E8478}
 .ic{width:82px;text-align:center}
 .ic img{width:40px;height:40px;display:block;margin:0 auto 4px}
 .ic em{font-style:normal;font-size:10px;color:#8E8478}
</style></head><body><div class="wrap">

<h2>一、装进屏幕看（素材清单看不出质量，这一屏才看得出）</h2>
<p class="hint">960×540 菜单屏：缎带标题 + 大主键 + 两次键 + 底部提示 + 左上 HUD + 角标</p>
<div class="scr">
  <img class="abs" src="decor_glow.svg" style="left:-40px;top:-60px;width:260px;opacity:.42">
  <img class="abs" src="decor_spark.svg" style="left:760px;top:64px;width:20px">
  <img class="abs" src="decor_spark.svg" style="left:128px;top:168px;width:13px;opacity:.7">
  <img class="abs" src="decor_spark.svg" style="left:832px;top:352px;width:17px;opacity:.85">
  <div class="ribbon"><img class="bg" src="decor_ribbon.svg">
    <img class="tx" src="text_开始游戏_30_d.png"></div>
  @MAINBTN@
  @SUBBTNS@
  <div class="abs" style="left:320px;top:392px">
    <div class="pnl" style="width:320px;height:96px">
      <img class="bg" src="panel_tip.svg">
      <img class="tx" src="text_恭喜通关_22_d.png"></div>
  </div>
  <img class="abs" src="bar_hp_100.svg" style="left:34px;top:26px;width:156px">
  <img class="abs" src="badge_stars.svg" style="left:34px;top:58px;width:104px">
  <div class="abs" style="left:836px;top:28px;display:flex;gap:10px;align-items:center">
    <img src="icon_play_light.svg" style="width:24px">
    <img src="icon_settings_light.svg" style="width:24px">
  </div>
  <img class="abs" src="badge_new.svg" style="left:806px;top:118px;width:78px">
</div>

<h2>二、按钮 5 类型 × 4 状态</h2>
<p class="hint">normal / hover（提亮+投影） / pressed（下沉+渐变反转） / disabled（去饱和+蒙版）</p>
@MATRIX@

<h2>三、面板成套尺寸（Scratch 没有九宫格，只能出固定尺寸）</h2>
<p class="hint">tip 320×96 / card 360×200 / dialog 440×280（需配 decor_mask 压暗背景）</p>
<div class="row">
  <div class="pnl" style="width:320px;height:96px">
    <img class="bg" src="panel_tip.svg"><img class="tx" src="text_恭喜通关_22_d.png"></div>
  <div class="pnl" style="width:360px;height:200px">
    <img class="bg" src="panel_card.svg"><img class="tx" src="text_游戏结束_28_d.png"></div>
</div>
<div class="row">
  <div class="pnl" style="width:440px;height:280px">
    <img class="bg" src="panel_dialog.svg">
    <img class="tx" src="text_游戏结束_40_l.png">
    <div class="row">
      @DLGBTN@
    </div>
  </div>
</div>

<h2>四、进度条换档（不拉伸，圆角不变形）</h2>
<p class="hint">10% / 40% / 70% / 100%，10 档各一张图</p>
<div class="row">@BARS@</div>

<h2>五、图标（24 网格 / 线宽 2 / round；下面按 40px 显示，矢量不糊）</h2>
<div class="row">@ICONS@</div>
</div></body></html>"""


def build_preview():
    """预览页：排成真实界面，而不是素材清单。

    三个刻意的设计：
    1. **按钮用 flex 居中套文字条**，不手算坐标 —— 手算一定会错位。
    2. **按钮矩阵按「类型为行、状态为列」**，一眼能比出四种状态的差别。
    3. **图标放大到 40px 展示** —— 矢量放大不糊，这本身就是卖点。
    """
    def wrap(cls, size, bg, label, extra=""):
        wh = {"s": (120, 44), "m": (180, 56), "l": (260, 68)}[size]
        return ('<div class="%s" style="width:%dpx;height:%dpx;%s">'
                '<img class="bg" src="%s"><img class="tx" src="%s"></div>'
                % (cls, wh[0], wh[1], extra, bg, label))

    # ---- 按钮矩阵：行 = 类型，列 = 状态
    head = "".join('<span class="st">%s</span>' % st for st in BTN_STATES)
    rows = []
    for k in BTN_KINDS:
        cells = "".join('<div class="v"><img src="btn_%s_%s_m.svg"></div>' % (k, st)
                        for st in BTN_STATES)
        rows.append('<span class="tag">%s</span>%s' % (k, cells))
    matrix = '<div class="matrix"><span></span>%s</div>' % head
    matrix += "".join('<div class="matrix">%s</div>' % r for r in rows)

    # ---- 进度条：4 档并排，原尺寸
    bars = "".join('<div class="bar"><img src="bar_hp_%03d.svg"><em>%d%%</em></div>' % (p, p)
                   for p in (100, 70, 40, 10))

    # ---- 图标：放大到 40px
    icons = "".join('<div class="ic"><img src="icon_%s_light.svg"><em>%s</em></div>'
                    % (n, n) for n in STROKE_ICONS)

    html = HTML_TPL

    main_btn = wrap("btn", "l", "btn_primary_normal_l.svg", "text_开始游戏_20_d.png",
                    "left:350px;top:170px")
    sub1 = wrap("btn", "m", "btn_secondary_normal_m.svg", "text_设置_17_d.png",
                "left:298px;top:270px")
    sub2 = wrap("btn", "m", "btn_ghost_normal_m.svg", "text_继续_17_l.png",
                "left:490px;top:270px")
    dlg = wrap("btn", "s", "btn_primary_normal_s.svg", "text_继续_17_l.png", "")

    return (html.replace("@MAINBTN@", main_btn)
                .replace("@SUBBTNS@", sub1 + sub2)
                .replace("@DLGBTN@", dlg)
                .replace("@MATRIX@", matrix)
                .replace("@BARS@", bars)
                .replace("@ICONS@", icons))


if __name__ == "__main__":
    sys.exit(main())
