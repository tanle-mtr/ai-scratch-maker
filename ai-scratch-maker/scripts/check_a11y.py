#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""可访问性静态检查（Accessibility Heuristics）。

依据 Game Accessibility Guidelines / Microsoft 游戏可访问性：
  · 色盲安全：红/绿/棕/橙易混，若作品同时出现「红系 + 绿系」填充，警示
              「不要仅靠颜色区分关键信息（用形状/图案/文字标签）」。
  · SVG 文字：铁律17 本就禁止 <text>，这里作为可访问性 + 硬规则交叉检查。
  · 可见状态：作品若有音效/状态，应有可见变量（分数/生命…）呈现，避免「只靠声音传信息」。
  · 闪烁：SVG 内 <animate> 极短 dur 反复 → 光敏风险（轻量提示）。

用法：
    python scripts/check_a11y.py examples/output/x.sb3
    python scripts/check_a11y.py examples/output/x.sb3 --strict   # 色盲对 + SVG文字 致命
    python scripts/check_a11y.py examples/output/x.sb3 --json

默认只出报告、退出码 0（与质量门禁 C 层一致，可访问性是「软性」维度）；
--strict 时把「色盲对」「SVG 文字」升为致命（返回 1）。
"""
import argparse
import json
import re
import sys
import zipfile

# 可见状态变量名（出现其中之一，视为「信息有可见通道」）
_STATUS_VARS = ["分数", "得分", "生命", "血量", "关卡", "score", "lives", "hp", "health", "level", "time", "时间"]
# 状态广播名（胜负/状态切换，证明有逻辑状态机）
_STATUS_BROADCAST = ["胜利", "失败", "通关", "过关", "赢", "输", "gameover", "win", "lose", "clear", "重置", "开始"]


def hex_family(hexc):
    """把 #rrggbb 粗略归类到色系，用于色盲风险判断。"""
    try:
        h = hexc.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return None
    # 红系：R 高，G/B 低
    if r > 120 and g < 95 and b < 95:
        return "red"
    # 绿系：G 高，R/B 低
    if g > 120 and r < 115 and b < 115:
        return "green"
    # 橙：R 高 G 中 B 低
    if r > 150 and 80 <= g <= 165 and b < 90:
        return "orange"
    # 棕：R 中高 G 中低 B 低
    if 90 <= r <= 170 and 40 <= g <= 115 and b < 85:
        return "brown"
    # 蓝系 / 黄系（色盲安全组合）
    if b > 120 and r < 115:
        return "blue"
    if r > 180 and g > 180 and b < 130:
        return "yellow"
    return None


def analyze(sb3):
    with zipfile.ZipFile(sb3) as z:
        names = z.namelist()
        d = json.loads(z.read("project.json"))
        # 只扫被引用的 SVG（与质量门禁一致，排除孤儿）
        ref_md5 = set()
        for t in d.get("targets", []):
            for c in t.get("costumes", []) + t.get("backdrops", []):
                a = c.get("assetId") or c.get("md5ext", "")
                ref_md5.add(str(a).split(".")[0].lower())
        svgs = [n for n in names if n.lower().endswith(".svg")
                and n[:-4].lower().split("/")[-1] in ref_md5]

        families = set()
        has_svg_text = False
        has_animate = False
        for n in svgs:
            try:
                txt = z.read(n).decode("utf-8", "ignore")
            except Exception:
                continue
            for m in re.finditer(r'(?:fill|stroke)\s*=\s*["\']?(#[0-9a-fA-F]{3,6})', txt):
                fam = hex_family(m.group(1))
                if fam:
                    families.add(fam)
            if "<text" in txt:
                has_svg_text = True
            if re.search(r"<animate[^>]*\bdur\s*=\s*[\"']?0?\.[01]", txt):
                has_animate = True

    # 状态可见性：变量 / 广播名里是否有状态信号
    var_names = []
    bc_names = []
    for t in d.get("targets", []):
        for v in (t.get("variables") or {}).values():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                var_names.append(str(v[1]))
        for bc in (t.get("broadcasts") or {}).values():
            # 序列化格式：{ id: "广播名" }（字符串），也可能包成 [id, name]
            if isinstance(bc, str):
                bc_names.append(bc)
            elif isinstance(bc, (list, tuple)) and len(bc) >= 1:
                bc_names.append(str(bc[-1]))
    has_status_var = any(any(k in n.lower() for k in _STATUS_VARS) for n in var_names)
    has_status_bc = any(any(k in n.lower() for k in _STATUS_BROADCAST) for n in bc_names)
    has_sound = len(d.get("targets", [{}])[0].get("sounds", [])) > 0 or any(
        t.get("sounds") for t in d.get("targets", []))

    return {
        "families": sorted(families),
        "colorblind_pair": ("red" in families and "green" in families) or
                          ("orange" in families and "green" in families) or
                          ("brown" in families and "green" in families),
        "has_svg_text": has_svg_text,
        "has_animate": has_animate,
        "has_status_var": has_status_var,
        "has_status_bc": has_status_bc,
        "has_sound": has_sound,
    }


def _expand(targets):
    """把 CLI 参数展开成 .sb3 路径列表：目录 -> 目录下 *.sb3，文件原样保留。"""
    import os
    out = []
    for t in targets:
        if os.path.isdir(t):
            for n in sorted(os.listdir(t)):
                if n.lower().endswith(".sb3"):
                    out.append(os.path.join(t, n))
        else:
            out.append(t)
    return out


def _findings(r):
    """把分析结果翻成「人可读的告警列表」。"""
    warns = []
    if r["colorblind_pair"]:
        warns.append("色盲风险：同时出现红/绿系填充 —— 勿仅靠颜色区分关键信息（改用形状/图案/文字标签）")
    if r["has_svg_text"]:
        warns.append("SVG 含 <text>：违反铁律17（SVG 禁用 text/filter…），且文字不可访问")
    if r["has_animate"]:
        warns.append("SVG 含极短 dur 的 <animate>：闪烁光敏风险，建议放缓或移除")
    if r["has_sound"] and not (r["has_status_var"] or r["has_status_bc"]):
        warns.append("有音效但未见可见状态变量/广播：避免「只靠声音传信息」，加分/生命等可见显示")
    return warns


def _is_fatal(r):
    """--strict 下真正拦交付的只有两项（其余是软性提示，不该阻断）。"""
    return bool(r["colorblind_pair"] or r["has_svg_text"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sb3", nargs="+", help="一个或多个 .sb3，或一个目录（批量扫描）")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    paths = _expand(args.sb3)
    batch = len(paths) > 1

    total_ok = 0
    total_warn = 0
    total_fatal = 0
    warn_lines = []
    last_r = None
    for p in paths:
        try:
            r = analyze(p)
        except Exception as e:
            print(f"[check_a11y] 解析失败（跳过）{p}: {e}")
            continue
        last_r = r

        warns = _findings(r)
        if warns:
            total_warn += 1
        else:
            total_ok += 1
        if _is_fatal(r):
            total_fatal += 1

        if args.json:
            print(json.dumps({"sb3": p, "findings": r, "warns": warns}, ensure_ascii=False, indent=2))
            continue

        if batch:
            if warns:
                import os as _os
                warn_lines.append((_os.path.basename(p), warns))
            continue

        print("== 可访问性 ==")
        print(f"  色系           : {', '.join(r['families']) or '(无)'}")
        print(f"  色盲风险对     : {'是' if r['colorblind_pair'] else '否'}")
        print(f"  SVG 文字       : {'是(违规)' if r['has_svg_text'] else '否'}")
        print(f"  可见状态通道   : {'有' if (r['has_status_var'] or r['has_status_bc']) else '无'}")
        print("--")
        if warns:
            print("  建议（默认非致命）：")
            for w in warns:
                print(f"    ! {w}")
            # 机器可读令牌：与 --strict 退出码对齐，便于编排器统计
            print(f"  A11Y_WARN：{len(warns)} 项建议（非致命）")
        else:
            print("  A11Y_OK：未触发可访问性嗅觉")

    if batch and not args.json:
        print("== 可访问性（批量） ==")
        for name, warns in warn_lines:
            print(f"  · {name}: {'; '.join(warns)}")
        print(f"  合计 {len(paths)} 个：OK {total_ok} / WARN {total_warn}（其中致命项 {total_fatal} 个）")
        if total_warn:
            print(f"  A11Y_WARN：{total_warn} 个作品有建议（非致命）")
        else:
            print("  A11Y_OK：未触发可访问性嗅觉")

    fatal_n = total_fatal if batch else (1 if (last_r and _is_fatal(last_r)) else 0)
    sys.exit(1 if (args.strict and fatal_n > 0) else 0)


if __name__ == "__main__":
    main()
