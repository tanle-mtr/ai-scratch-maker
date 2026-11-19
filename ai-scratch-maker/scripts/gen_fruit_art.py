#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「自产水果 + 装饰 + 果园背景」矢量素材（铁律17 合规）。

为什么需要它
------------
旗舰示例《水果篮子》《星空拾贝》原先引用社区素材包（`community:<id>`）。
社区素材来自第三方社区公开作品，其授权声明写明「对外分发或商用前须回溯原作者授权」，
因此**不能随开源仓库分发**。本脚本生成一批**完全自产**的替代素材：
造型语言与原包一致（水果按形状区分、装饰为小元素），但版权归本项目。

配色严格取自 `references/ui-design-spec.md` §198 的 18 色板（铁律13）：
  #FFCF4D #FFEDB3 #FAF19B #C6FF2A #8CE243 #5FD100 #32AF00 #216E09
  #5CD9BA #67F6D5 #3A8E7D #C4FFE3 #2F7365 #4F4A47 #675D5D #767171 #7F7F7F #876C26
其中 #216E09 / #2F7365 **只用于描边**，绝不作为填充（§198：仅限文字）。
所有颜色字面量均为 6 位 HEX（铁律14）。
禁用标签：text / filter / mask / clipPath / pattern / image / foreignObject。

五层体积感（铁律17，顺序不可换）：投影 → 外描边 → 渐变 → 顶高光 → 底内阴。

用法：
    python scripts/gen_fruit_art.py --out-dir examples/assets
    python scripts/gen_fruit_art.py --out-dir examples/assets --selftest
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------- §198 色板
YELLOW = "#FFCF4D"
YELLOW_LT = "#FFEDB3"
CREAM = "#FAF19B"
LIME = "#C6FF2A"
GREEN = "#8CE243"
GREEN_MD = "#5FD100"
GREEN_DK = "#32AF00"
GREEN_STROKE = "#216E09"      # 仅描边
TEAL = "#5CD9BA"
TEAL_LT = "#67F6D5"
TEAL_DK = "#3A8E7D"
TEAL_STROKE = "#2F7365"       # 仅描边
MINT = "#C4FFE3"
INK = "#4F4A47"
INK_2 = "#675D5D"
GRAY = "#7F7F7F"
BROWN = "#876C26"
WHITE = "#FFFFFF"

PALETTE = {
    YELLOW, YELLOW_LT, CREAM, LIME, GREEN, GREEN_MD, GREEN_DK, GREEN_STROKE,
    TEAL, TEAL_LT, TEAL_DK, TEAL_STROKE, MINT, INK, INK_2, GRAY, BROWN, WHITE,
}
FORBIDDEN_FILL = {GREEN_STROKE.lower(), TEAL_STROKE.lower()}
FORBIDDEN_TAGS = ("text", "filter", "mask", "clipPath", "pattern", "image",
                  "foreignObject")


def svg_open(w, h):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'width="%d" height="%d">\n' % (w, h, w, h))


def svg_close():
    """闭合标签。必须成对——漏 </svg> 会让浏览器/Scratch 直接拒绝渲染。"""
    return "</svg>\n"


def grad(gid, c1, c2, x2=0, y2=1):
    """纵向线性渐变（铁律17 第二层「渐变」）。"""
    return ('  <linearGradient id="%s" x1="0" y1="0" x2="%s" y2="%s">\n'
            '    <stop offset="0" stop-color="%s"/>\n'
            '    <stop offset="1" stop-color="%s"/>\n'
            '  </linearGradient>\n' % (gid, x2, y2, c1, c2))


def shadow(cx, cy, rx, ry, op=0.16):
    """第一层：投影（暖调深灰低透明，§198 合规）。"""
    return ('  <ellipse cx="%g" cy="%g" rx="%g" ry="%g" fill="%s" opacity="%g"/>\n'
            % (cx, cy, rx, ry, INK, op))


def highlight(cx, cy, rx, ry, op=0.5, color=WHITE):
    """第四层：顶部受光高光。"""
    return ('  <ellipse cx="%g" cy="%g" rx="%g" ry="%g" fill="%s" opacity="%g"/>\n'
            % (cx, cy, rx, ry, color, op))


def inner_shade(cx, cy, rx, ry, op=0.22, color=BROWN):
    """第五层：底部内阴影。"""
    return ('  <ellipse cx="%g" cy="%g" rx="%g" ry="%g" fill="%s" opacity="%g"/>\n'
            % (cx, cy, rx, ry, color, op))


def leaf(x, y, rot=-24, scale=1.0, color=GREEN_DK, edge=GREEN_STROKE):
    """叶片：填充用绿系，描边用深绿（§198：深绿不得做填充，但可做描边）。"""
    return (
        '  <g transform="translate(%g %g) rotate(%g) scale(%g)">\n'
        '    <path d="M0 0 C 14 -12, 34 -8, 40 4 C 30 16, 10 14, 0 0 Z" '
        'fill="%s" stroke="%s" stroke-width="3" stroke-linejoin="round"/>\n'
        '    <path d="M2 1 C 14 -3, 26 -2, 37 3" fill="none" stroke="%s" '
        'stroke-width="2" opacity="0.55"/>\n'
        '  </g>\n' % (x, y, rot, scale, color, edge, color))


def stem(x, y, h=14, color=BROWN):
    return ('  <path d="M%g %g q 3 -%g 8 -%g" fill="none" stroke="%s" '
            'stroke-width="6" stroke-linecap="round"/>\n' % (x, y, h, h, color))


# ------------------------------------------------------------------ 8 种水果
def fruit_apple():
    """苹果：圆身 + 缺口 + 叶片 + 梗。"""
    return (
        svg_open(120, 120) +
        grad("body", YELLOW_LT, YELLOW) +
        shadow(60, 104, 34, 8) +
        '  <path d="M60 26 C 76 26, 96 40, 96 64 C 96 88, 78 100, 60 100 '
        'C 42 100, 24 88, 24 64 C 24 40, 44 26, 60 26 Z" fill="%s"/>\n' % BROWN +
        '  <path d="M60 30 C 74 30, 92 42, 92 64 C 92 86, 76 96, 60 96 '
        'C 44 96, 28 86, 28 64 C 28 42, 46 30, 60 30 Z" fill="url(#body)"/>\n' +
        highlight(47, 48, 13, 8, 0.55) +
        inner_shade(60, 86, 30, 13, 0.20) +
        stem(60, 30, 12) +
        leaf(62, 24, -28, 0.72, GREEN_DK)
    )


def fruit_lemon():
    """柠檬：横向椭圆 + 两端小凸起。"""
    return (
        svg_open(120, 120) +
        grad("body", YELLOW_LT, YELLOW) +
        shadow(60, 100, 36, 8) +
        '  <ellipse cx="60" cy="62" rx="42" ry="30" fill="%s"/>\n' % BROWN +
        '  <ellipse cx="60" cy="62" rx="38" ry="26" fill="url(#body)"/>\n' +
        '  <ellipse cx="24" cy="62" rx="7" ry="8" fill="%s"/>\n' % BROWN +
        '  <ellipse cx="96" cy="62" rx="7" ry="8" fill="%s"/>\n' % BROWN +
        '  <ellipse cx="25" cy="61" rx="5" ry="6" fill="%s"/>\n' % YELLOW +
        '  <ellipse cx="95" cy="61" rx="5" ry="6" fill="%s"/>\n' % YELLOW +
        highlight(44, 46, 14, 7, 0.55) +
        inner_shade(60, 82, 28, 11, 0.18)
    )


def fruit_banana():
    """香蕉：新月形（外凸下弧 + 内凹上弧，两端收细）。"""
    outer = ("M26 16 C24 58 48 94 92 92 C98 92 101 88 99 83 L93 70 "
             "C64 74 46 52 44 16 Z")
    body = ("M30 20 C28 56 50 88 90 87 C95 87 97 85 96 81 L91 70 "
            "C66 73 49 52 47 20 Z")
    return (
        svg_open(120, 120) +
        grad("body", YELLOW, YELLOW_LT) +
        shadow(60, 100, 32, 7) +
        '  <path d="%s" fill="%s"/>\n' % (outer, BROWN) +
        '  <path d="%s" fill="url(#body)"/>\n' % body +
        '  <path d="M24 8 L46 12 L44 24 L24 21 Z" fill="%s"/>\n' % INK_2 +
        '  <path d="M94 64 C99 66 102 71 101 76 L95 74 C95 71 94 67 92 64 Z" '
        'fill="%s"/>\n' % INK_2 +
        highlight(52, 58, 15, 6, 0.38, YELLOW_LT) +
        inner_shade(66, 82, 17, 7, 0.15, BROWN)
    )


def fruit_pineapple():
    """菠萝：椭圆身 + 网格纹 + 皇冠叶。"""
    hatch = []
    for i in range(4):
        y = 48 + i * 15
        hatch.append('  <path d="M36 %g L84 %g" fill="none" stroke="%s" '
                     'stroke-width="2" opacity="0.45"/>\n' % (y, y - 6, BROWN))
    for i in range(3):
        x = 44 + i * 16
        hatch.append('  <path d="M%g 44 L%g 96" fill="none" stroke="%s" '
                     'stroke-width="2" opacity="0.35"/>\n' % (x, x + 6, BROWN))
    return (
        svg_open(120, 120) +
        grad("body", CREAM, YELLOW) +
        shadow(60, 104, 30, 7) +
        '  <ellipse cx="60" cy="68" rx="32" ry="38" fill="%s"/>\n' % BROWN +
        '  <ellipse cx="60" cy="68" rx="28" ry="34" fill="url(#body)"/>\n' +
        ''.join(hatch) +
        highlight(48, 50, 9, 12, 0.4, WHITE) +
        inner_shade(60, 94, 22, 8, 0.16) +
        '  <path d="M60 34 C 58 22, 50 14, 42 8 C 48 20, 52 26, 54 34 Z" fill="%s"/>\n' % GREEN_DK +
        '  <path d="M60 34 C 62 22, 70 14, 78 8 C 72 20, 68 26, 66 34 Z" fill="%s"/>\n' % GREEN_MD +
        '  <path d="M60 36 C 58 24, 58 16, 60 6 C 62 16, 62 24, 60 36 Z" fill="%s"/>\n' % GREEN
    )


def fruit_grape():
    """葡萄：七颗聚成的果串。"""
    pts = [(60, 40), (44, 56), (76, 56), (52, 74), (68, 74), (60, 90)]
    outer = "".join(
        '  <circle cx="%g" cy="%g" r="16" fill="%s"/>\n' % (x, y, TEAL_DK)
        for x, y in pts)
    body = "".join(
        '  <circle cx="%g" cy="%g" r="13" fill="url(#body)"/>\n' % (x, y)
        for x, y in pts)
    glint = "".join(
        '  <circle cx="%g" cy="%g" r="4" fill="%s" opacity="0.6"/>\n' % (x - 4, y - 5, TEAL_LT)
        for x, y in pts)
    return (
        svg_open(120, 120) +
        grad("body", TEAL_LT, TEAL_DK) +
        shadow(60, 104, 30, 7) +
        outer + body + glint +
        '  <path d="M60 28 C 59 20, 62 14, 68 10" fill="none" stroke="%s" '
        'stroke-width="5" stroke-linecap="round"/>\n' % GREEN_STROKE +
        leaf(60, 16, -18, 0.62, GREEN_DK)
    )


def fruit_watermelon():
    """西瓜：三角切片（绿皮 + 奶白瓤 + 籽）。"""
    seeds = "".join(
        '  <ellipse cx="%g" cy="%g" rx="3" ry="4" fill="%s" opacity="0.75"/>\n'
        % (x, y, INK) for x, y in [(48, 58), (60, 66), (72, 58), (54, 78), (68, 78)])
    return (
        svg_open(120, 120) +
        grad("body", YELLOW_LT, CREAM) +
        shadow(60, 100, 32, 7) +
        '  <path d="M22 40 L98 40 L60 100 Z" fill="%s"/>\n' % GREEN_DK +
        '  <path d="M29 44 L91 44 L60 92 Z" fill="%s"/>\n' % GREEN +
        '  <path d="M36 47 L84 47 L60 86 Z" fill="url(#body)"/>\n' +
        seeds +
        highlight(46, 52, 10, 5, 0.45) +
        inner_shade(60, 82, 16, 7, 0.14, GREEN_DK)
    )


def fruit_peach():
    """桃：圆身 + 桃缝 + 叶片。"""
    return (
        svg_open(120, 120) +
        grad("body", CREAM, YELLOW_LT) +
        shadow(60, 104, 32, 8) +
        '  <circle cx="60" cy="64" r="36" fill="%s"/>\n' % BROWN +
        '  <circle cx="60" cy="64" r="32" fill="url(#body)"/>\n' +
        '  <path d="M60 32 C 54 48, 54 80, 60 96" fill="none" stroke="%s" '
        'stroke-width="3" opacity="0.55"/>\n' % YELLOW +
        highlight(46, 48, 11, 8, 0.5) +
        inner_shade(60, 88, 26, 11, 0.16) +
        stem(60, 30, 10) +
        leaf(62, 24, -30, 0.66, GREEN_MD)
    )


def fruit_berry():
    """浆果：三颗聚合的小果 + 叶片。"""
    pts = [(46, 70), (74, 70), (60, 46)]
    outer = "".join(
        '  <circle cx="%g" cy="%g" r="20" fill="%s"/>\n' % (x, y, TEAL_DK)
        for x, y in pts)
    body = "".join(
        '  <circle cx="%g" cy="%g" r="17" fill="url(#body)"/>\n' % (x, y)
        for x, y in pts)
    glint = "".join(
        '  <circle cx="%g" cy="%g" r="5" fill="%s" opacity="0.6"/>\n' % (x - 5, y - 6, MINT)
        for x, y in pts)
    return (
        svg_open(120, 120) +
        grad("body", TEAL_LT, TEAL_DK) +
        shadow(60, 96, 28, 7) +
        outer + body + glint +
        leaf(60, 22, -20, 0.6, GREEN_DK)
    )


# ------------------------------------------------------------------ 4 个装饰
def deco_star():
    """装饰1：星星。"""
    pts = []
    import math
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = 44 if i % 2 == 0 else 19
        pts.append((60 + r * math.cos(ang), 60 + r * math.sin(ang)))
    path = "M" + " L".join("%g %g" % p for p in pts) + " Z"
    return (
        svg_open(120, 120) +
        grad("body", YELLOW, YELLOW_LT) +
        shadow(60, 106, 26, 6, 0.14) +
        '  <path d="%s" fill="%s" stroke="%s" stroke-width="6" '
        'stroke-linejoin="round"/>\n' % (path, BROWN, BROWN) +
        '  <path d="%s" fill="url(#body)"/>\n' % path +
        highlight(46, 42, 11, 8, 0.5) +
        inner_shade(60, 80, 22, 10, 0.18)
    )


def deco_cloud():
    """装饰2：云朵。"""
    return (
        svg_open(120, 120) +
        grad("body", WHITE, MINT) +
        shadow(60, 84, 34, 7, 0.12) +
        '  <path d="M32 82 C 14 82, 8 66, 22 56 C 22 38, 42 30, 54 40 '
        'C 62 24, 92 26, 94 46 C 110 48, 108 82, 90 82 Z" fill="%s"/>\n' % MINT +
        '  <path d="M34 78 C 18 78, 13 64, 25 55 C 25 40, 43 33, 54 42 '
        'C 62 28, 88 30, 90 47 C 103 49, 101 78, 87 78 Z" fill="url(#body)"/>\n' +
        highlight(44, 48, 13, 7, 0.55)
    )


def deco_leaf():
    """装饰3：叶片。"""
    return (
        svg_open(120, 120) +
        grad("body", GREEN, GREEN_MD) +
        shadow(60, 104, 28, 6, 0.14) +
        '  <path d="M60 96 C 26 84, 22 38, 60 24 C 98 38, 94 84, 60 96 Z" '
        'fill="%s"/>\n' % GREEN_DK +
        '  <path d="M60 90 C 32 79, 29 41, 60 30 C 91 41, 88 79, 60 90 Z" '
        'fill="url(#body)"/>\n' +
        '  <path d="M60 30 L60 90" fill="none" stroke="%s" stroke-width="4" '
        'opacity="0.75"/>\n' % GREEN_DK +
        '  <path d="M60 48 L44 38 M60 48 L76 38 M60 66 L46 58 M60 66 L74 58" '
        'fill="none" stroke="%s" stroke-width="3" opacity="0.5"/>\n' % GREEN_DK +
        highlight(46, 44, 10, 12, 0.4, MINT)
    )


def deco_flower():
    """装饰3：五瓣花。"""
    petals = ""
    import math
    for i in range(5):
        ang = -math.pi / 2 + i * 2 * math.pi / 5
        cx = 60 + 22 * math.cos(ang)
        cy = 58 + 22 * math.sin(ang)
        petals += ('  <ellipse cx="%g" cy="%g" rx="17" ry="20" fill="%s"/>\n'
                   % (cx, cy, BROWN))
    petals2 = ""
    for i in range(5):
        ang = -math.pi / 2 + i * 2 * math.pi / 5
        cx = 60 + 21 * math.cos(ang)
        cy = 58 + 21 * math.sin(ang)
        petals2 += ('  <ellipse cx="%g" cy="%g" rx="14" ry="17" fill="url(#body)"/>\n'
                    % (cx, cy))
    return (
        svg_open(120, 120) +
        grad("body", YELLOW_LT, CREAM) +
        shadow(60, 100, 26, 6, 0.14) +
        petals + petals2 +
        '  <circle cx="60" cy="58" r="15" fill="%s"/>\n' % LIME +
        '  <circle cx="60" cy="58" r="11" fill="%s"/>\n' % YELLOW +
        highlight(54, 51, 5, 4, 0.6)
    )


def backdrop_orchard():
    """果园背景（480×360）：天空 / 太阳 / 云 / 远山 / 草地 / 树丛。"""
    clouds = ""
    for cx, cy, s in [(90, 52, 1.0), (300, 38, 0.8), (400, 74, 0.65), (200, 30, 0.55)]:
        clouds += (
            '  <g transform="translate(%g %g) scale(%g)" opacity="0.92">\n'
            '    <path d="M-38 12 C -58 12, -64 -2, -50 -12 C -50 -28, -32 -36, -20 -27 '
            'C -12 -41, 16 -39, 19 -22 C 34 -20, 32 12, 16 12 Z" fill="%s"/>\n'
            '    <path d="M-34 8 C -52 8, -57 -4, -45 -12 C -45 -25, -30 -32, -19 -25 '
            'C -12 -37, 12 -35, 15 -21 C 28 -19, 27 8, 13 8 Z" fill="%s"/>\n'
            '  </g>\n' % (cx, cy, s, WHITE, WHITE))
    trees = ""
    for cx, s, c1, c2 in [(58, 1.0, GREEN, GREEN_MD), (420, 0.85, GREEN, GREEN_MD),
                          (150, 0.6, GREEN_MD, GREEN_DK), (330, 0.55, GREEN_MD, GREEN_DK)]:
        trees += (
            '  <g transform="translate(%g 250) scale(%g)">\n'
            '    <rect x="-7" y="-6" width="14" height="46" rx="4" fill="%s"/>\n'
            '    <circle cx="0" cy="-32" r="34" fill="%s"/>\n'
            '    <circle cx="-22" cy="-16" r="22" fill="%s"/>\n'
            '    <circle cx="22" cy="-16" r="22" fill="%s"/>\n'
            '    <circle cx="-9" cy="-46" r="20" fill="%s"/>\n'
            '    <circle cx="9" cy="-46" r="20" fill="%s"/>\n'
            '  </g>\n' % (cx, s, BROWN, c2, c1, c1, c2, c1))
    bushes = ""
    for cx, cy, r in [(70, 318, 22), (150, 330, 18), (250, 322, 20),
                      (330, 334, 17), (410, 320, 23)]:
        bushes += ('  <circle cx="%g" cy="%g" r="%g" fill="%s"/>\n' % (cx, cy, r, GREEN_DK))
        bushes += ('  <circle cx="%g" cy="%g" r="%g" fill="%s"/>\n'
                   % (cx - r * 0.5, cy + 2, r * 0.62, GREEN))
    return (
        svg_open(480, 360) +
        grad("sky", MINT, CREAM) +
        grad("grass", GREEN, GREEN_MD) +
        '  <rect x="0" y="0" width="480" height="360" fill="url(#sky)"/>\n' +
        '  <circle cx="400" cy="56" r="40" fill="%s" opacity="0.35"/>\n' % YELLOW_LT +
        '  <circle cx="400" cy="56" r="28" fill="%s"/>\n' % YELLOW +
        '  <circle cx="392" cy="48" r="9" fill="%s" opacity="0.7"/>\n' % YELLOW_LT +
        clouds +
        '  <path d="M0 246 C 70 208, 140 232, 200 214 C 270 194, 330 224, 400 210 '
        'C 440 202, 462 214, 480 206 L480 262 L0 262 Z" fill="%s" opacity="0.75"/>\n' % GREEN_MD +
        '  <path d="M0 262 C 90 240, 170 258, 250 244 C 330 230, 410 254, 480 242 '
        'L480 300 L0 300 Z" fill="%s"/>\n' % GREEN +
        '  <rect x="0" y="292" width="480" height="68" fill="url(#grass)"/>\n' +
        '  <rect x="0" y="292" width="480" height="6" fill="%s" opacity="0.35"/>\n' % GREEN_DK +
        trees +
        bushes +
        '  <ellipse cx="240" cy="350" rx="200" ry="26" fill="%s" opacity="0.12"/>\n' % INK
    )


# ------------------------------------------------------------------- 输出表
ASSETS = {
    "fruit_basket/fruit_apple.svg": fruit_apple,
    "fruit_basket/fruit_lemon.svg": fruit_lemon,
    "fruit_basket/fruit_banana.svg": fruit_banana,
    "fruit_basket/fruit_pineapple.svg": fruit_pineapple,
    "fruit_basket/fruit_grape.svg": fruit_grape,
    "fruit_basket/fruit_watermelon.svg": fruit_watermelon,
    "fruit_basket/fruit_peach.svg": fruit_peach,
    "fruit_basket/fruit_berry.svg": fruit_berry,
    "deco/deco_star.svg": deco_star,
    "deco/deco_cloud.svg": deco_cloud,
    "deco/deco_leaf.svg": deco_leaf,
    "deco/deco_flower.svg": deco_flower,
    "fruit_basket/backdrop_orchard.svg": backdrop_orchard,
}


def check_svg(text, name):
    """自检：XML 合法 / 禁标签 / 3 位 HEX / 深绿填充 / 冷灰。"""
    errs = []
    # ① XML 合法性（漏闭合标签是最容易被忽略的致命错）
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(text)
    except Exception as e:
        errs.append("%s: XML 不合法 -> %s" % (name, e))
    for tag in FORBIDDEN_TAGS:
        if re.search(r"<%s\b" % tag, text, re.I):
            errs.append("%s: 禁用标签 <%s>" % (name, tag))
    for m in re.finditer(r"#[0-9a-fA-F]{3}\b", text):
        errs.append("%s: 3 位 HEX %s" % (name, m.group(0)))
    for fg in FORBIDDEN_FILL:
        if re.search(r'fill=["\']' + fg + r'["\']', text, re.I):
            errs.append("%s: 深绿/深青做填充（§198 仅限描边/文字）" % name)
    # 冷灰检测（与 quality_gate.py 同判据）
    for h in set(x.lower() for x in re.findall(r"#[0-9a-fA-F]{6}\b", text)):
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        lo, hi = min(r, g, b), max(r, g, b)
        if (hi - lo) <= 20 and b > r + 12 and b >= g:
            errs.append("%s: 冷灰 %s" % (name, h))
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(SKILL_ROOT, "examples", "assets"),
                    help="素材输出根目录（默认 examples/assets）")
    ap.add_argument("--selftest", action="store_true", help="只做合规自检，不写盘")
    a = ap.parse_args()

    all_errs = []
    for rel, fn in ASSETS.items():
        text = fn() + svg_close()
        errs = check_svg(text, rel)
        all_errs.extend(errs)
        if a.selftest:
            continue
        out = os.path.join(a.out_dir, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print("写入 %s (%d 字节)" % (rel, len(text.encode("utf-8"))))

    if all_errs:
        print("合规自检失败：")
        for e in all_errs:
            print("  ! " + e)
        return 1
    print("合规自检通过：%d 个素材全部合规（无禁标签 / 6位HEX / 深绿仅描边 / 无冷灰）" % len(ASSETS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
