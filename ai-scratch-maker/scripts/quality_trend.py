#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""质量趋势看板：把每次交付的质量评分按版本归档，跟踪「质量有没有在变好」。

治本改造的教训是「全绿≠作品好」——但「好」仍需要可量化的趋势线，否则每次都从零判断。
本脚本把一份作品（或目录下最新一份）在多个质量维度上的得分，按版本/日期归档进一个
JSON 时序库；`report` 模式打印趋势表，一眼看出每个版本相比上一版涨了还是跌了。

归档维度（全部复用 quality_gate / scorecard）：
  · scorecard 总分 + 评级
  · 六维度分（资产密度/玩法/观感/动画/音效/质感）
  · A 层计数（造型/音效/角色/场景/积木）+ 动画数 + 音效比 + 位图数 + 观感分

用法：
    python scripts/quality_trend.py archive --sb3 examples/output/whack_a_mole.sb3 --version v0.21.0
    python scripts/quality_trend.py archive --dir examples/output --version v0.21.0 --pick-best
    python scripts/quality_trend.py report
    python scripts/quality_trend.py report --archive refs.json
"""
import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import quality_gate as qg  # noqa: E402
import scorecard  # noqa: E402

DEFAULT_ARCHIVE = os.path.join(ROOT, "quality_trends.json")


def _sample(sb3):
    m = qg.measure(sb3)
    sc = scorecard.score(sb3)
    return {
        "sb3": os.path.basename(sb3),
        "date": datetime.date.today().isoformat(),
        "score_total": sc["total"],
        "grade": sc["grade"],
        "dimensions": sc["dimensions"],
        "costumes": m["costumes"], "sounds": m["sounds"],
        "sprites": m["sprites"], "scenes": m["scenes"], "blocks": m["blocks"],
        "animated": sc["raw"]["animated"], "sound_per_sprite": sc["raw"]["sound_per_sprite"],
        "bitmap": sc["raw"]["bitmap"], "appearance": sc["raw"]["appearance"],
    }


def archive(sb3_or_dir, version, archive_path, pick_best):
    rec = {"version": version}
    if os.path.isdir(sb3_or_dir):
        cands = [os.path.join(sb3_or_dir, n) for n in os.listdir(sb3_or_dir)
                 if n.lower().endswith(".sb3")]
        if pick_best:
            best, best_sc = None, -1
            for c in cands:
                try:
                    s = scorecard.score(c)["total"]
                    if s > best_sc:
                        best_sc, best = s, c
                except Exception:
                    continue
            cands = [best] if best else []
        rec.update(_sample(cands[0])) if cands else rec.update({"sb3": None})
    else:
        rec.update(_sample(sb3_or_dir))
    data = []
    if os.path.exists(archive_path):
        try:
            data = json.load(open(archive_path, encoding="utf-8"))
        except Exception:
            data = []
    data.append(rec)
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("ARCHIVE_OK  版本 %s 归档 -> %s（共 %d 条记录）" % (version, archive_path, len(data)))
    print("  总分 %.2f 评级 %s | 造型%d 音效%d 角色%d 场景%d 积木%d 动画%d 位图%d 观感%d"
          % (rec.get("score_total", 0), rec.get("grade", "?"), rec.get("costumes", 0),
             rec.get("sounds", 0), rec.get("sprites", 0), rec.get("scenes", 0),
             rec.get("blocks", 0), rec.get("animated", 0), rec.get("bitmap", 0),
             rec.get("appearance", 0)))
    return 0


def report(archive_path):
    if not os.path.exists(archive_path):
        print("没有归档记录：%s" % archive_path, file=sys.stderr)
        return 1
    data = json.load(open(archive_path, encoding="utf-8"))
    data.sort(key=lambda r: r.get("date", ""))
    print("=" * 78)
    print("质量趋势看板（按日期，共 %d 个版本）" % len(data))
    print("=" * 78)
    hdr = "%-10s %-9s %-5s %-5s %-4s %-4s %-4s %-4s %-5s %-4s %-4s" % (
        "版本", "日期", "总分", "评级", "造型", "音效", "角色", "场景", "积木", "动画", "位图")
    print(hdr)
    print("-" * 78)
    prev = None
    for r in data:
        delta = ""
        if prev is not None and "score_total" in r and "score_total" in prev:
            d = round(r["score_total"] - prev["score_total"], 2)
            delta = " (%+g)" % d
        print("%-10s %-9s %-5.2f %-5s %-4d %-4d %-4d %-4d %-5d %-4d %-4d%s" % (
            r.get("version", "?"), r.get("date", ""), r.get("score_total", 0), r.get("grade", "?"),
            r.get("costumes", 0), r.get("sounds", 0), r.get("sprites", 0), r.get("scenes", 0),
            r.get("blocks", 0), r.get("animated", 0), r.get("bitmap", 0), delta))
        prev = r
    print("-" * 78)
    if len(data) >= 2:
        first, last = data[0], data[-1]
        print("趋势：%s → %s  总分 %s → %s" % (
            first.get("version"), last.get("version"),
            first.get("score_total"), last.get("score_total")))
    print("QUALITY_TREND_OK")
    return 0


def main():
    ap = argparse.ArgumentParser(description="质量趋势看板：版本化归档 + 趋势报告")
    ap.add_argument("action", choices=["archive", "report"])
    ap.add_argument("--sb3", help="归档：单个 .sb3")
    ap.add_argument("--dir", help="归档：目录下最新/最优一份")
    ap.add_argument("--version", default="dev", help="版本标签")
    ap.add_argument("--pick-best", action="store_true", help="--dir 时挑 scorecard 总分最高的一份")
    ap.add_argument("--archive", default=DEFAULT_ARCHIVE, help="归档 JSON 路径")
    args = ap.parse_args()
    if args.action == "archive":
        target = args.sb3 or args.dir
        if not target:
            ap.error("archive 需要 --sb3 或 --dir")
        return archive(target, args.version, args.archive, args.pick_best)
    return report(args.archive)


if __name__ == "__main__":
    sys.exit(main())
