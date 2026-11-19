#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 Scratch 造型 SVG 自动加「五层体积感」（铁律17 观感硬要求）。

铁律17 规定 UI 矢量 + 五层体积感：投影 → 外描边 → 渐变 → 顶高光 → 底内阴（序不可换）。
同时铁律17 明令 SVG 禁止 text / filter / mask / clipPath / pattern / image——
所以本脚本**只用基础图元 + 线性渐变**实现体积感，绝不动用 filter/mask/clip：

  1. 投影      复制主轮廓（主体 shape）平移偏移 + 深色低透明，置于主体之后；
  2. 外描边    给主体加 stroke（中性描边 #4F4A47）+ paint-order=stroke，描边落在填充外侧；
  3. 渐变      用 linearGradient 替换主体纯色填充；
  4. 顶高光    渐变顶部停色比原色提亮（≈+28%），天然形成顶部受光；
  5. 底内阴    渐变底部停色比原色压暗（≈-28%），天然形成底部内阴。

设计取舍：
  · 真正的五层体积感应当「作者绘制时就分层」，本脚本是**事后兜底**——把扁平程序化
    SVG 拉到一个及格的体积底线，不能替代规范作画（见 references/quality-checklist.md）。
  · 主体选取：面积最大的实心图元（ellipse/circle/rect/polygon；path 退化为次选）。
    多图元精灵（如角色含眼睛/嘴）只对主轮廓做体积，细节图元保留，避免把眼睛也渐变掉。
  · 若主体已是渐变填充（url(#..)），跳过渐变注入、保留原渐变，只补描边 + 投影。

用法：
    python scripts/enhance_svg.py in.svg -o out.svg
    python scripts/enhance_svg.py --in-dir assets/raw --out-dir assets/enhanced
    python scripts/enhance_svg.py in.svg -o out.svg --strip-text   # 移除 <text>（铁律17 违例）
    python scripts/enhance_svg.py --selftest
"""
import argparse
import copy
import os
import sys
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

# §198 中性描边色；投影用同色低透明（暖调深灰，非冷灰，合规）。
STROKE_COLOR = "#4F4A47"
SHADOW_COLOR = "#4F4A47"
SHADOW_OPACITY = 0.22
SHADOW_DX = 1.5
SHADOW_DY = 2.5
LIGHTEN = 0.28
DARKEN = 0.30

SHAPE_TAGS = ("path", "rect", "circle", "ellipse", "polygon", "polyline")


def _ln(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join("%02x" % max(0, min(255, int(round(c)))) for c in rgb)


def _lighten(rgb, amt):
    return tuple(c + (255 - c) * amt for c in rgb)


def _darken(rgb, amt):
    return tuple(c * (1 - amt) for c in rgb)


def _area(el):
    """粗略估算图元面积，用于挑主体。"""
    t = _ln(el.tag)
    try:
        if t == "ellipse":
            rx, ry = float(el.get("rx", 0)), float(el.get("ry", 0))
            return 3.14159 * rx * ry
        if t == "circle":
            r = float(el.get("r", 0))
            return 3.14159 * r * r
        if t == "rect":
            w, h = float(el.get("width", 0)), float(el.get("height", 0))
            return w * h
        if t == "polygon":
            pts = el.get("points", "").split()
            xs = [float(p.split(",")[0]) for p in pts if "," in p]
            ys = [float(p.split(",")[1]) for p in pts if "," in p]
            if not xs:
                return 0
            return (max(xs) - min(xs)) * (max(ys) - min(ys))
    except (ValueError, TypeError):
        return 0
    return 0


def _pick_primary(root):
    """挑面积最大的实心图元作为主体；全是 path 时退化为第一个 path。"""
    best, best_area = None, -1
    first_path = None
    for el in root.iter():
        t = _ln(el.tag)
        if t in SHAPE_TAGS:
            if t == "path" and first_path is None:
                first_path = el
            fill = (el.get("fill") or "").lower()
            if fill in ("none", "") and t != "path":
                continue
            a = _area(el)
            if a > best_area:
                best, best_area = el, a
    if best is None:
        return first_path
    return best


def _ensure_defs(root):
    for el in root:
        if _ln(el.tag) == "defs":
            return el
    d = ET.SubElement(root, "{%s}defs" % SVG_NS)
    root.remove(d)
    root.insert(0, d)
    return d


def _inject_gradient(defs, fill_hex):
    rgb = _hex_to_rgb(fill_hex)
    top = _rgb_to_hex(_lighten(rgb, LIGHTEN))
    bot = _rgb_to_hex(_darken(rgb, DARKEN))
    grad = ET.SubElement(defs, "{%s}linearGradient" % SVG_NS)
    gid = "vol_grad_%d" % (abs(hash(fill_hex)) % 100000)
    grad.set("id", gid)
    grad.set("x1", "0"); grad.set("y1", "0")
    grad.set("x2", "0"); grad.set("y2", "1")
    for off, col in (("0%", top), ("55%", fill_hex), ("100%", bot)):
        s = ET.SubElement(grad, "{%s}stop" % SVG_NS)
        s.set("offset", off)
        s.set("stop-color", col)
    return "url(#%s)" % gid


def enhance_tree(root, strip_text=False):
    if strip_text:
        for el in list(root.iter()):
            if _ln(el.tag) == "text":
                parent = None
                # 找到父节点移除（ET 无 parent 指针，从根遍历）
                for p in root.iter():
                    if el in list(p):
                        p.remove(el)
                        break
    primary = _pick_primary(root)
    if primary is None:
        return root  # 无图元可增强（可能是纯背景），原样返回
    w = float(root.get("width", "100").replace("px", "")) if root.get("width") else 100
    h = float(root.get("height", "100").replace("px", "")) if root.get("height") else 100
    stroke_w = max(2.0, round(min(w, h) * 0.05, 1))

    cur_fill = (primary.get("fill") or "").strip()
    if cur_fill and not cur_fill.lower().startswith("url(") and cur_fill.lower() != "none":
        if cur_fill.lower().startswith("#") or len(cur_fill) in (3, 6, 8):
            try:
                defs = _ensure_defs(root)
                grad_ref = _inject_gradient(defs, cur_fill if cur_fill.startswith("#") else "#888888")
                primary.set("fill", grad_ref)
            except Exception:
                pass  # 颜色解析失败则保留原填充

    # 外描边（若已有 stroke，仅在其过细时加粗；否则新增）
    if not primary.get("stroke") or primary.get("stroke").lower() == "none":
        primary.set("stroke", STROKE_COLOR)
        primary.set("stroke-width", str(stroke_w))
        primary.set("stroke-linejoin", "round")
        primary.set("paint-order", "stroke")
    else:
        try:
            if float(primary.get("stroke-width", "0")) < stroke_w:
                primary.set("stroke-width", str(stroke_w))
        except ValueError:
            pass

    # 投影：克隆主体，置深色低透明 + 偏移，置于主体之前（在底层）
    shadow = copy.deepcopy(primary)
    shadow.set("fill", SHADOW_COLOR)
    shadow.set("opacity", str(SHADOW_OPACITY))
    shadow.set("stroke", "none")
    shadow.attrib.pop("id", None)
    shadow.set("transform", "translate(%s %s)" % (SHADOW_DX, SHADOW_DY))
    parent = None
    for p in root.iter():
        kids = list(p)
        if primary in kids:
            parent = p
            break
    if parent is not None:
        idx = list(parent).index(primary)
        parent.insert(idx, shadow)
    return root


def enhance_file(in_path, out_path, strip_text=False):
    tree = ET.parse(in_path)
    root = tree.getroot()
    enhance_tree(root, strip_text=strip_text)
    # 序列化：保留 xmlns
    body = ET.tostring(root, encoding="unicode")
    out = '<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return out_path


def _has_forbidden(out_text):
    low = out_text.lower()
    return any(t in low for t in ("<filter", "<text", "clip-path", "<pattern", "<mask", "<image"))


def main():
    ap = argparse.ArgumentParser(description="给 Scratch 造型 SVG 自动加五层体积感（铁律17 合规）")
    ap.add_argument("input", nargs="?", help="输入 SVG 文件")
    ap.add_argument("-o", "--output", help="输出 SVG 文件")
    ap.add_argument("--in-dir", help="批量：输入目录")
    ap.add_argument("--out-dir", help="批量：输出目录")
    ap.add_argument("--strip-text", action="store_true", help="移除 <text>（铁律17 违例，Scratch 里会糊成方块）")
    ap.add_argument("--selftest", action="store_true", help="内置自测：生成一个扁平 SVG 增强后断言合规")
    args = ap.parse_args()

    if args.selftest:
        import tempfile
        sample = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">'
                  '<ellipse cx="20" cy="20" rx="14" ry="14" fill="#32AF00"/>'
                  '<circle cx="15" cy="18" r="3" fill="#FFFFFF"/></svg>')
        tmp = tempfile.mkdtemp()
        src = os.path.join(tmp, "s.svg")
        with open(src, "w", encoding="utf-8") as f:
            f.write(sample)
        dst = os.path.join(tmp, "o.svg")
        enhance_file(src, dst, strip_text=False)
        out = open(dst, encoding="utf-8").read()
        assert "linearGradient" in out, "自测失败：未注入渐变"
        assert not _has_forbidden(out), "自测失败：输出含铁律17 违例图元"
        assert 'stroke="#4F4A47"' in out, "自测失败：未加外描边"
        print("SELFTEST_OK  渐变+描边+投影已注入，且零 filter/mask/clip/text")
        return 0

    if args.in_dir:
        if not args.out_dir:
            ap.error("--in-dir 需要 --out-dir")
        os.makedirs(args.out_dir, exist_ok=True)
        n = 0
        for name in sorted(os.listdir(args.in_dir)):
            if not name.lower().endswith(".svg"):
                continue
            enhance_file(os.path.join(args.in_dir, name),
                         os.path.join(args.out_dir, name), strip_text=args.strip_text)
            n += 1
        print("ENHANCE_DIR_OK  增强 %d 个 SVG -> %s" % (n, args.out_dir))
        return 0

    if not args.input or not args.output:
        ap.error("需要 input 与 -o，或用 --in-dir/--out-dir，或 --selftest")
    enhance_file(args.input, args.output, strip_text=args.strip_text)
    out = open(args.output, encoding="utf-8").read()
    if _has_forbidden(out):
        print("[警告] 输出含铁律17 违例图元（filter/mask/clip/text），请检查输入", file=sys.stderr)
    print("ENHANCE_OK  %s -> %s" % (args.input, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
