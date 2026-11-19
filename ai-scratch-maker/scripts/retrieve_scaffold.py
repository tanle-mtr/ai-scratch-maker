#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风格/题材检索脚手架：从「已验收作品库」里挑最合适的骨架起手。

new_project.py 只内置 3 个硬编码模板（catch/platformer/whack）。本脚本把检索范围
扩到**整个 examples/ 里可构建的 IR**，按「题材关键词」或「风格契合度」排序，推荐最优
骨架——把「从零写」的概率再压低一截。

检索维度：
  · 题材（--genre / --keyword）：从文件名 + IR 特征推断题材标签（横版跳跃/收集/点击/
    射击/音游/棋类…），关键词命中即候选；
  · 质量（scorecard 总分）：候选里挑总分最高的，确保起点是好的；
  · 风格（--style-lock）：若给了风格锁，额外按 style_profile 契合度排序。

用法：
    python scripts/retrieve_scaffold.py --genre platformer
    python scripts/retrieve_scaffold.py --keyword 收集
    python scripts/retrieve_scaffold.py --keyword 点击 --style-lock lock.json
    python scripts/retrieve_scaffold.py --build-index     # 预计算候选索引（缓存）
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAMPLES = os.path.join(ROOT, "examples")
sys.path.insert(0, HERE)
import scorecard  # noqa: E402

INDEX_PATH = os.path.join(ROOT, ".scaffold_index.json")

# 题材推断：文件名关键词 → 题材标签
_GENRE_HINTS = {
    "platformer": ["platform", "横版", "跳跃"],
    "catch": ["catch", "fruit", "收集", "拾", "篮"],
    "whack": ["whack", "打地鼠", "点击", "tap", "mole"],
    "shooter": ["shooter", "射击", "弹幕", "bullet"],
    "rhythm": ["rhythm", "音游", "节奏"],
    "board": ["board", "棋", "gomoku", "桌游", "card", "卡"],
    "quiz": ["quiz", "答题", "考"],
    "metro": ["metro", "地铁"],
    "music": ["music", "band", "乐", "音乐"],
    "story": ["story", "剧情", "叙事"],
    "edu": ["edu", "课件", "教学"],
    "3d": ["3d", "体素", "minecraft"],
    "match3": ["match", "三消", "消除"],
    "multiplayer": ["multi", "联机", "多人"],
}


def _infer_genre(stem):
    tags = []
    low = stem.lower()
    for g, kws in _GENRE_HINTS.items():
        if any(k.lower() in low for k in kws):
            tags.append(g)
    return tags or ["misc"]


def _candidate_irs():
    out = []
    for name in sorted(os.listdir(EXAMPLES)):
        if not name.endswith((".yaml", ".json")):
            continue
        if name.endswith(".quality.json") or name.endswith(".expected.json"):
            continue
        stem = name[:-5] if name.endswith(".yaml") else name[:-5]
        sb3 = os.path.join(EXAMPLES, "output", stem + ".sb3")
        if not os.path.exists(sb3):
            continue
        out.append((stem, os.path.join(EXAMPLES, name), sb3))
    return out


def build_index():
    rows = []
    for stem, ir_path, sb3 in _candidate_irs():
        try:
            sc = scorecard.score(sb3)
        except Exception as e:
            print("[跳过] %s: %s" % (stem, e), file=sys.stderr)
            continue
        rows.append({
            "stem": stem, "ir": os.path.relpath(ir_path, ROOT), "sb3": os.path.basename(sb3),
            "genres": _infer_genre(stem),
            "total": sc["total"], "grade": sc["grade"],
            "animated": sc["raw"]["animated"], "bitmap": sc["raw"]["bitmap"],
            "appearance": sc["raw"]["appearance"],
        })
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print("INDEX_OK  索引 %d 个可构建骨架 -> %s" % (len(rows), INDEX_PATH))
    return rows


def _load_index():
    if not os.path.exists(INDEX_PATH):
        return build_index()
    return json.load(open(INDEX_PATH, encoding="utf-8"))


def _match(rows, genre, keyword):
    res = []
    for r in rows:
        if genre and genre not in r["genres"]:
            continue
        if keyword:
            hay = (r["stem"] + " " + " ".join(r["genres"])).lower()
            if keyword.lower() not in hay:
                continue
        res.append(r)
    return res


def _style_sort(rows, lock):
    if not lock:
        return sorted(rows, key=lambda r: r["total"], reverse=True)
    sys.path.insert(0, HERE)
    import style_profile
    lock_d = json.load(open(lock, encoding="utf-8"))
    for r in rows:
        try:
            rep = style_profile.check_adherence(
                os.path.join(EXAMPLES, "output", r["sb3"]), lock_d)
            r["adherence"] = rep["adherence"]
        except Exception:
            r["adherence"] = 0
    return sorted(rows, key=lambda r: (r.get("adherence", 0), r["total"]), reverse=True)


def main():
    ap = argparse.ArgumentParser(description="风格/题材检索脚手架")
    ap.add_argument("--genre", help="题材标签（platformer/catch/whack/shooter/rhythm/board/…）")
    ap.add_argument("--keyword", help="关键词（在文件名+题材里子串匹配）")
    ap.add_argument("--style-lock", help="风格锁 JSON（额外按契合度排序）")
    ap.add_argument("--top", type=int, default=5, help="展示前 N 名")
    ap.add_argument("--build-index", action="store_true", help="预计算候选索引")
    args = ap.parse_args()

    if args.build_index:
        build_index()
        return 0

    rows = _load_index()
    matched = _match(rows, args.genre, args.keyword)
    if not matched:
        print("[无候选] 题材/关键词 %s/%s 无匹配的可构建骨架"
              % (args.genre or "-", args.keyword or "-"), file=sys.stderr)
        return 1
    matched = _style_sort(matched, args.style_lock)
    print("=" * 70)
    print("检索脚手架 · 候选 %d 个（题材=%s 关键词=%s%s）"
          % (len(matched), args.genre or "-", args.keyword or "-",
             " +风格锁" if args.style_lock else ""))
    print("=" * 70)
    print("%-22s %-5s %-4s %-6s %-5s %-5s %-5s" % (
        "骨架(stem)", "总分", "评级", "题材", "动画", "位图", "观感"))
    print("-" * 70)
    for r in matched[:args.top]:
        print("%-22s %-5.2f %-4s %-6s %-5d %-5d %-5d" % (
            r["stem"][:22], r["total"], r["grade"], ",".join(r["genres"])[:6],
            r["animated"], r["bitmap"], r["appearance"]))
    best = matched[0]
    print("-" * 70)
    mapped = {"catch": "catch", "platformer": "platformer", "whack": "whack"}
    if best["genres"][0] in mapped:
        print("推荐骨架: %s（已内置模板，直接起手）：" % best["stem"])
        print("  python scripts/new_project.py --genre %s --name <你的作品名>"
              % mapped[best["genres"][0]])
    else:
        print("推荐骨架: %s（无内置模板，复制其 IR 起手）：" % best["stem"])
        print("  cp %s examples/<你的作品>.yaml   # 再改 project.name 与玩法" % best["ir"])
    print("RETRIEVE_SCAFFOLD_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
