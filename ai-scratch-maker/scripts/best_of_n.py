#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Best-of-N：从 N 个候选 .sb3 里挑总分最高的交付。

配合「Best-of-N + 评分卡」生成策略——AI 一次出 N 个变体，本脚本跑 scorecard 排序，
把最优者标为交付候选（--copy-best 可直接复制到指定路径）。

用法：
    python scripts/best_of_n.py a.sb3 b.sb3 c.sb3
    python scripts/best_of_n.py --dir examples/output --top 5
    python scripts/best_of_n.py a.sb3 b.sb3 --copy-best examples/output/best.sb3
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scorecard  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Best-of-N：从候选 .sb3 里挑质量总分最高的")
    ap.add_argument("candidates", nargs="*", help="候选 .sb3 文件")
    ap.add_argument("--dir", help="从目录下所有 .sb3 取候选")
    ap.add_argument("--top", type=int, default=0, help="只打印前 N 名（0=全部）")
    ap.add_argument("--copy-best", help="把最优者复制到该路径")
    ap.add_argument("--json", help="把排名写成 JSON")
    ap.add_argument("--genre", default="game")
    args = ap.parse_args()

    files = list(args.candidates)
    if args.dir:
        for name in sorted(os.listdir(args.dir)):
            if name.lower().endswith(".sb3"):
                files.append(os.path.join(args.dir, name))
    if not files:
        ap.error("需要候选文件或 --dir")

    rows = []
    for f in files:
        if not os.path.exists(f):
            print("[跳过] 不存在: %s" % f, file=sys.stderr)
            continue
        try:
            rep = scorecard.score(f)
        except Exception as e:
            print("[跳过] 解析失败 %s: %s" % (f, e), file=sys.stderr)
            continue
        rows.append(rep)
    if not rows:
        print("没有可评分的候选", file=sys.stderr)
        return 2

    rows.sort(key=lambda r: r["total"], reverse=True)
    print("=" * 60)
    print("Best-of-N 排名（共 %d 个候选）" % len(rows))
    print("=" * 60)
    print("%-3s %-34s %-5s %-3s" % ("排名", "文件", "总分", "评级"))
    print("-" * 60)
    for i, r in enumerate(rows[:args.top] if args.top else rows, 1):
        print("%-3d %-34s %-5.2f %-3s" % (
            i, os.path.basename(r["sb3"])[:34], r["total"], r["grade"]))
    best = rows[0]
    print("-" * 60)
    print("最优: %s  总分 %.2f  评级 %s" % (
        os.path.basename(best["sb3"]), best["total"], best["grade"]))
    print("BEST_OF_N_OK")

    if args.copy_best:
        shutil.copyfile(best["sb3"], args.copy_best)
        print("已复制最优到: %s" % args.copy_best)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print("排名 -> %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
