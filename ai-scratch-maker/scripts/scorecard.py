#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作品评分卡：把「质量」压成一张 1–5 分维度表 + 总分。

配合生成策略「Best-of-N + 评分卡」：AI 一次生成 N 个变体，跑本卡挑总分最高的交付。
六个维度全部复用 quality_gate.py 的静态分析（不重复造轮子）：

  1. 资产密度   A 层计数（造型/音效/角色/场景/积木）归一化
  2. 玩法完整度 B 层（玩家可操控 / 胜负条件 / 重玩价值）
  3. 观感质量   C 层 score（含冷灰/深绿硬违例封顶）
  4. 动画完备性 E 层（在播动画角色数）
  5. 音效密度   F 层（音效/角色比）
  6. 生图质感   D 层（被引用的位图造型数）

总分 = 加权（观感/玩法/动画权重高，密度/音效/质感中）。输出 JSON + 人类可读表。

用法：
    python scripts/scorecard.py x.sb3
    python scripts/scorecard.py x.sb3 --genre game --json out.json
    python scripts/scorecard.py --dir examples/output --genre game   # 批量打分
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import quality_gate as qg  # noqa: E402


def _clamp(v, lo=1, hi=5):
    return max(lo, min(hi, v))


def _dens_score(m):
    # 各计数相对「健康基线」归一，取均值映射到 1–5
    parts = [
        min(m["costumes"] / 20.0, 1.0),
        min(m["sounds"] / 8.0, 1.0),
        min(m["sprites"] / 4.0, 1.0),
        min(m["scenes"] / 2.0, 1.0),
        min(m["blocks"] / 150.0, 1.0),
    ]
    return _clamp(round(sum(parts) / len(parts) * 5))


def _comp_score(comp):
    n = sum(1 for k in ("player_control", "win_lose", "replay_value") if comp[k])
    return {0: 1, 1: 3, 2: 4, 3: 5}[n]


def _appr_score(appr):
    if appr["cold_gray"] or appr["deep_green"]:
        return 2  # 硬违例封顶
    return _clamp(round(appr["score"] / 100.0 * 5))


def _anim_score(anim):
    a = anim["animated_sprites"]
    return 1 if a == 0 else (3 if a <= 2 else 5)


def _sfx_score(sfx):
    r = sfx["sound_per_sprite"]
    return 1 if r < 0.2 else (3 if r < 0.5 else 5)


def _asset_score(bm):
    """生图质感：认「合适资产」（矢量 SVG + 带透明通道的位图），不认白底未抠位图。"""
    b = bm["suitable_assets"]
    return 1 if b == 0 else (3 if b < 3 else 5)


WEIGHTS = {
    "资产密度": 0.15, "玩法完整度": 0.20, "观感质量": 0.25,
    "动画完备性": 0.20, "音效密度": 0.10, "生图质感": 0.10,
}


def score(sb3):
    m = qg.measure(sb3)
    comp = qg.analyze_completeness(sb3)
    appr = qg.analyze_appearance(sb3)
    anim = qg.analyze_animation(sb3)
    sfx = qg.analyze_sfx_density(sb3)
    bm = qg.analyze_bitmap_usage(sb3)
    dims = {
        "资产密度": _dens_score(m),
        "玩法完整度": _comp_score(comp),
        "观感质量": _appr_score(appr),
        "动画完备性": _anim_score(anim),
        "音效密度": _sfx_score(sfx),
        "生图质感": _asset_score(bm),
    }
    total = round(sum(dims[k] * WEIGHTS[k] for k in dims), 2)
    grade = "S" if total >= 4.5 else ("A" if total >= 4 else ("B" if total >= 3 else ("C" if total >= 2 else "D")))
    return {
        "sb3": sb3,
        "dimensions": dims,
        "total": total,
        "grade": grade,
        "raw": {
            "costumes": m["costumes"], "sounds": m["sounds"], "sprites": m["sprites"],
            "scenes": m["scenes"], "blocks": m["blocks"],
            "animated": anim["animated_sprites"], "sound_per_sprite": sfx["sound_per_sprite"],
            "bitmap": bm["suitable_assets"], "unsuitable_bitmap": bm["unsuitable_bitmap"],
            "appearance": appr["score"],
        },
    }


def _print(report):
    d = report["dimensions"]
    print("=" * 56)
    print("评分卡 · %s" % os.path.basename(report["sb3"]))
    print("=" * 56)
    for k in ("资产密度", "玩法完整度", "观感质量", "动画完备性", "音效密度", "生图质感"):
        bar = "★" * int(d[k]) + "☆" * (5 - int(d[k]))
        print("  %-6s %s  %d/5" % (k, bar, d[k]))
    print("-" * 56)
    print("  总分 %.2f / 5   评级 %s" % (report["total"], report["grade"]))
    r = report["raw"]
    print("  (造型%d 音效%d 角色%d 场景%d 积木%d | 动画%d 音效比%.2f 合适%d 不合适%d 观感%d)"
          % (r["costumes"], r["sounds"], r["sprites"], r["scenes"], r["blocks"],
             r["animated"], r["sound_per_sprite"], r["bitmap"], r["unsuitable_bitmap"], r["appearance"]))
    print("SCORECARD_OK")


def main():
    ap = argparse.ArgumentParser(description="作品质量评分卡（1–5 维度 + 总分）")
    ap.add_argument("sb3", nargs="?", help="待评分 .sb3")
    ap.add_argument("--dir", help="批量：对目录下所有 .sb3 打分")
    ap.add_argument("--json", help="把结果写成 JSON（单文件或批量都支持）")
    ap.add_argument("--genre", default="game", help="品类（仅影响打印，维度算法与品类无关）")
    args = ap.parse_args()

    if args.dir:
        reports = []
        for name in sorted(os.listdir(args.dir)):
            if not name.lower().endswith(".sb3"):
                continue
            reports.append(score(os.path.join(args.dir, name)))
        reports.sort(key=lambda r: r["total"], reverse=True)
        for r in reports:
            _print(r)
            print()
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(reports, f, ensure_ascii=False, indent=2)
            print("批量报告 -> %s" % args.json)
        return 0

    if not args.sb3:
        ap.error("需要 sb3 或 --dir")
    rep = score(args.sb3)
    _print(rep)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        print("报告 -> %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
