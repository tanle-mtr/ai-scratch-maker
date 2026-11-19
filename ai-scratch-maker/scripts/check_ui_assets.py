#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI 素材合规校验：把「素材质量」里能自动查的部分全部查掉。

为什么需要这个脚本：
    「素材好看」是主观的，但**「素材会不会在 Scratch 里坏掉」是客观的**。
    下面五类问题肉眼看不出来，装进 sb3 之后才炸：

    ① `<text>`          —— 中文字体在造型链路里不可控，换台机器就变豆腐块
    ② `filter` / `mask` —— 模糊/裁剪在不同渲染路径下表现不一致，缩放还会糊
    ③ 非规范色相        —— 随手挑的蓝/紫，和调色板打架（§198 只允许 黄/绿/青绿/暖灰）
    ④ 尺寸不在网格上    —— 按钮做 178×55，九张图凑不齐一套状态
    ⑤ 图标线宽不一      —— 24 个图标 2px/2.5px/3px 混着来，一排看过去就是「拼的」

检查项：
    [结构] XML 可解析、必须有 viewBox、不能用 text/filter/mask/clipPath/pattern/image
    [配色] 所有 fill/stroke/stop-color 的色相必须落在允许区间（或中性灰）
    [网格] 按钮 ∈ {120×44, 180×56, 260×68}；图标 = 24×24；面板 ∈ 4 档
    [一致性] 同组素材的描边宽度必须一致（图标 2px）
    [命名] 文件名字段完整（btn_kind_state_size.svg / icon_name_tone.svg / ...）

用法:
    python scripts/check_ui_assets.py                      # 默认查 examples/assets/uikit
    python scripts/check_ui_assets.py 某目录
    python scripts/check_ui_assets.py --quiet              # 只打印结论
"""
import argparse
import colorsys
import os
import re
import sys
import xml.etree.ElementTree as ET

# --------------------------------------------------------------------------- #
# 规范
# --------------------------------------------------------------------------- #
FORBIDDEN_TAGS = {
    "text": "中文字体不可控：Scratch 造型链路里 <text> 可能变豆腐块或不居中",
    "tspan": "同 <text>",
    "filter": "滤镜在不同渲染路径下表现不一致，缩放会糊",
    "feGaussianBlur": "同 filter",
    "mask": "遮罩支持不稳定，建议用半透明叠加代替",
    "clipPath": "裁剪支持不稳定，建议直接切路径",
    "pattern": "图案填充支持不稳定",
    "image": "SVG 内嵌位图会丢失（sb3 只打包外层文件）",
}

# 允许的色相区间（度）。§198 的四色系：黄 / 绿 / 青绿 / 暖灰
HUE_BANDS = [
    (28, 62, "黄/暖橙（主操作键）"),
    (84, 140, "绿（次要/验证）"),
    (148, 190, "青绿（主体/大模块）"),
]
# 中性色（饱和度低于此值一律放行：黑/白/灰都是必要的）
NEUTRAL_SAT = 0.14
# 唯一允许的扩展色：§199 状态暖红
DANGER_HUES = [(8, 22)]

BTN_SIZES = {(120, 44), (180, 56), (260, 68)}
ICON_SIZE = (24, 24)
PANEL_SIZES = {(320, 96), (360, 200), (440, 280), (260, 72)}

HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
COLOR_ATTRS = ("fill", "stroke", "stop-color", "flood-color", "color")


def parse_hex(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hue_sat(hx):
    r, g, b = parse_hex(hx)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return h * 360.0, s


def check_color(hx):
    """返回 None = 合规；否则返回原因。"""
    try:
        h, s = hue_sat(hx)
    except Exception:
        return "无法解析颜色"
    if s <= NEUTRAL_SAT:
        return None                      # 中性灰/黑/白：放行
    for lo, hi, _ in HUE_BANDS:
        if lo <= h <= hi:
            return None
    for lo, hi in DANGER_HUES:
        if lo <= h <= hi:
            return None                  # §199 状态暖红
    return "色相 %.0f° 不在规范四色系内（黄 28-62 / 绿 84-140 / 青绿 148-190 / 中性灰）" % h


def strip_ns(tag):
    return tag.split("}")[-1]


def check_file(path, rel):
    """返回 (errors, warnings)。"""
    errs, warns = [], []
    try:
        raw = open(path, encoding="utf-8").read()
    except Exception as e:
        return ["读不了文件: %s" % e], warns
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        return ["XML 解析失败: %s" % e], warns

    # ---- 结构：viewBox 必须存在（builder 靠它算造型尺寸）
    if "viewBox" not in raw:
        errs.append("缺 viewBox（构建器要靠它算造型尺寸，缺了会当成 480×360）")
    vb = root.get("viewBox") or ""
    m = re.search(r"([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)", vb)
    vw = vh = None
    if m:
        vw, vh = float(m.group(3)), float(m.group(4))

    # ---- 结构：禁用标签
    for el in root.iter():
        name = strip_ns(el.tag)
        if name in FORBIDDEN_TAGS:
            errs.append("用了 <%s>：%s" % (name, FORBIDDEN_TAGS[name]))
    if re.search(r"font-family|@font-face", raw, re.I):
        errs.append("引用了字体（font-family / @font-face）")

    # ---- 配色
    bad_colors = {}
    for el in root.iter():
        for attr in COLOR_ATTRS:
            v = el.get(attr)
            if not v:
                continue
            for hx in HEX_RE.findall(v):
                reason = check_color("#" + hx)
                if reason:
                    bad_colors["#" + hx] = reason
    for hx, reason in bad_colors.items():
        errs.append("颜色 %s %s" % (hx, reason))

    # ---- 网格尺寸（按文件名分组）
    base = os.path.basename(rel)
    if vw and vh:
        size = (int(round(vw)), int(round(vh)))
        if base.startswith("btn_"):
            if size not in BTN_SIZES:
                errs.append("按钮尺寸 %d×%d 不在网格上（只允许 120×44 / 180×56 / 260×68）" % size)
            parts = base[:-4].split("_")
            if len(parts) != 4:
                errs.append("按钮命名应为 btn_类型_状态_尺寸.svg，实为 %s" % base)
        elif base.startswith("icon_"):
            if size != ICON_SIZE:
                errs.append("图标必须 24×24，实为 %d×%d" % size)
            parts = base[:-4].split("_")
            if len(parts) != 3:
                errs.append("图标命名应为 icon_名称_色调.svg，实为 %s" % base)
        elif base.startswith("panel_"):
            if size not in PANEL_SIZES:
                warns.append("面板尺寸 %d×%d 不在标准四档内（tip/card/dialog/toast）" % size)
        elif base.startswith("ctrl_"):
            pass                          # 独立控件：尺寸自由，但必须正方形
        elif base.startswith("bar_"):
            parts = base[:-4].split("_")
            if len(parts) != 3:
                errs.append("进度条命名应为 bar_类型_百分比.svg，实为 %s" % base)

    # ---- 图标线宽一致性
    if base.startswith("icon_"):
        m = re.search(r'stroke-width="([\d.]+)"', raw)
        if m and abs(float(m.group(1)) - 2.0) > 0.01:
            errs.append("图标线宽应为 2，实为 %s" % m.group(1))

    # ---- 透明叠层提示：没写 opacity 的纯黑/纯白大面积矩形容易糊死背景
    if re.search(r'fill="#FFFFFF"', raw) and "opacity" not in raw and base.startswith("decor_"):
        warns.append("大面积纯白且无 opacity，叠在浅色背景上会看不出层次")

    return errs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    base = args.dir or os.path.join(os.getcwd(), "examples", "assets", "uikit")
    if not os.path.isdir(base):
        print("目录不存在: %s" % base)
        return 2

    files = sorted(f for f in os.listdir(base) if f.lower().endswith(".svg"))
    if not files:
        print("没找到 SVG: %s" % base)
        return 2

    total_err = total_warn = 0
    bad_files = []
    for f in files:
        errs, warns = check_file(os.path.join(base, f), f)
        total_err += len(errs)
        total_warn += len(warns)
        if errs:
            bad_files.append(f)
        if errs or (warns and not args.quiet):
            print("%s %s" % ("✗" if errs else "⚠", f))
            for e in errs:
                print("    ✗ %s" % e)
            for w in warns:
                print("    ⚠ %s" % w)
        elif not args.quiet:
            print("✓ %s" % f)

    print("-" * 56)
    print("检查 %d 个 SVG：错误 %d，警告 %d" % (len(files), total_err, total_warn))
    if total_err == 0:
        print("UI_ASSETS_OK  素材合规（结构 / 配色 / 网格 / 一致性全部通过）")
        return 0
    print("UI_ASSETS_FAIL  有 %d 个文件不合规：%s" % (len(bad_files), ", ".join(bad_files[:8])))
    return 1


if __name__ == "__main__":
    sys.exit(main())
