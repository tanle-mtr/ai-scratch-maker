# -*- coding: utf-8 -*-
"""桌游判定基线：斗地主牌型 / UNO 可出牌 / 狼人杀投票统计。

和 math_reference.py 一样，这是「翻译成积木之前」的正确性参照：
牌型判定有十几个分支，直接对着 Scratch 调等于自找麻烦。

牌值编码（全工程统一，1 副牌 54 张）：
    3..10 → 3..10      J=11  Q=12  K=13  A=14  2=15  小王=16  大王=17
（用 15 表示 2，是为了让「顺子比较」天然连续：3..15 只有 3..14 能连，
  2 不能进顺子 —— 这条规则用数值就能表达）
"""
import sys
from collections import Counter

# ------------------------------------------------------------------ 斗地主
RANK_NAME = {11: "J", 12: "Q", 13: "K", 14: "A", 15: "2", 16: "小王", 17: "大王"}


def rank_name(v):
    return RANK_NAME.get(v, str(v))


def combo_of(cards):
    """返回 (牌型名, 主值)。主值用于同型比大小；炸弹/王炸给特殊大值。

    判定顺序很关键：先判「张数固定的特型」，再判「张数可变的连型」，
    最后判「按计数组合」的型。顺序错了会把「三带二」误判成「三张」。
    """
    n = len(cards)
    if n == 0:
        return ("空", 0)
    cnt = Counter(cards)
    vals = sorted(cnt)
    counts = sorted(cnt.values(), reverse=True)
    n4 = counts.count(4)
    n3 = counts.count(3)
    n2 = counts.count(2)
    n1 = counts.count(1)

    # 王炸：两张都是王
    if n == 2 and set(cards) == {16, 17}:
        return ("王炸", 100)
    # 炸弹：四张同点
    if n == 4 and n4 == 1:
        return ("炸弹", vals[0] + 50)

    # 单 / 对 / 三
    if n == 1:
        return ("单张", vals[0])
    if n == 2 and n2 == 1:
        return ("对子", vals[0])
    if n == 3 and n3 == 1:
        return ("三张", vals[0])

    # 三带一 / 三带二
    if n == 4 and n3 == 1 and n1 == 1:
        return ("三带一", [v for v in vals if cnt[v] == 3][0])
    if n == 5 and n3 == 1 and n2 == 1:
        return ("三带二", [v for v in vals if cnt[v] == 3][0])

    # 四带二（两单）
    if n == 6 and n4 == 1 and n1 == 2:
        return ("四带二", [v for v in vals if cnt[v] == 4][0])

    # 顺子：≥5 张连续、每张恰 1 次、不含 2(15) 和王
    if n >= 5 and n1 == n and all(cnt[v] == 1 for v in vals) and vals[-1] <= 14:
        if vals[-1] - vals[0] + 1 == n:
            return ("顺子", vals[0])

    # 连对：≥3 对连续、不含 2
    if n >= 6 and n % 2 == 0 and n2 == n // 2 and vals[-1] <= 14:
        if vals[-1] - vals[0] + 1 == len(vals):
            return ("连对", vals[0])

    # 飞机（纯三顺，≥2 组）
    if n >= 6 and n % 3 == 0 and n3 == n // 3 and vals[-1] <= 14:
        if vals[-1] - vals[0] + 1 == len(vals):
            return ("飞机", vals[0])

    # 飞机带单（n = 3k + k）
    if n >= 8 and n % 4 == 0:
        k = n // 4
        triples = [v for v in vals if cnt[v] == 3 and v <= 14]
        if len(triples) >= k and triples[-1] - triples[0] + 1 >= k:
            return ("飞机带单", triples[0])

    return ("不成牌型", 0)


def can_beat(play, prev):
    """play 能否压过 prev。空 prev 表示自己先手。"""
    if prev is None or prev[0] == "空":
        return True
    a, av = play
    b, bv = prev
    if a == "不成牌型":
        return False
    if a == "王炸":
        return True
    if b == "王炸":
        return False
    if a == "炸弹" and b != "炸弹":
        return True
    if b == "炸弹" and a != "炸弹":
        return False
    if a != b:
        return False
    return av > bv


# ------------------------------------------------------------------ UNO
# UNO 牌编码：颜色 1..4（红黄绿蓝），数字 0..9，,+2=10 跳过=11 反转=12 变色=13 王牌+4=14
UNO_COLORS = {1: "红", 2: "黄", 3: "绿", 4: "蓝"}


def uno_playable(hand, top_color, top_num):
    """返回能出的牌（下标列表）。规则：同色 或 同数字 或 万能牌。"""
    out = []
    for i, (c, num) in enumerate(hand):
        if c == 0:                                  # 万能（变色 / +4）
            out.append(i)
        elif c == top_color or num == top_num:
            out.append(i)
    return out


# ------------------------------------------------------------------ 狼人杀
def vote_result(votes, alive):
    """votes: [(投票者, 被投者)]；alive: 存活玩家列表。返回 (最高票数, [出局候选])。
    只统计「被投者是存活玩家」的票；平票返回多个候选（进入 PK）。"""
    tally = Counter()
    for _who, target in votes:
        if target in alive:
            tally[target] += 1
    if not tally:
        return (0, [])
    top = max(tally.values())
    return (top, sorted([p for p, c in tally.items() if c == top]))


if __name__ == "__main__":
    ok = True

    print("== 斗地主牌型")
    cases = [
        ([5], ("单张", 5)),
        ([7, 7], ("对子", 7)),
        ([9, 9, 9], ("三张", 9)),
        ([9, 9, 9, 4], ("三带一", 9)),
        ([9, 9, 9, 4, 4], ("三带二", 9)),
        ([3, 4, 5, 6, 7], ("顺子", 3)),
        ([3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14], ("顺子", 3)),
        ([11, 12, 13, 14, 15], ("不成牌型", 0)),        # 含 2 不能成顺
        ([3, 3, 4, 4, 5, 5], ("连对", 3)),
        ([9, 9, 9, 10, 10, 10], ("飞机", 9)),
        ([6, 6, 6, 6], ("炸弹", 56)),
        ([16, 17], ("王炸", 100)),
        ([3, 5, 7, 9], ("不成牌型", 0)),
        ([5, 5, 5, 8, 8, 8, 3, 4], ("飞机带单", 5)),
    ]
    for cards, want in cases:
        got = combo_of(cards)
        flag = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print("  %-28s → %-8s 值%-3s (期望 %s/%s) %s" %
              (str([rank_name(c) for c in cards]), got[0], got[1], want[0], want[1], flag))

    print("== 比大小")
    beat_cases = [
        (("对子", 9), ("对子", 7), True),
        (("对子", 7), ("对子", 9), False),
        (("炸弹", 53), ("对子", 14), True),
        (("对子", 14), ("炸弹", 53), False),
        (("王炸", 100), ("炸弹", 56), True),
        (("顺子", 5), ("顺子", 3), True),
        (("三张", 9), ("对子", 9), False),
    ]
    for a, b, want in beat_cases:
        got = can_beat(a, b)
        flag = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print("  %s vs %s → %s (期望 %s) %s" % (a, b, got, want, flag))

    print("== UNO 可出牌")
    hand = [(1, 5), (1, 9), (2, 5), (3, 2), (0, 13)]
    # 红5 台面：红5(同色同数)、红9(同色)、黄5(同数)、万能 都能出；蓝2 不能
    got = uno_playable(hand, top_color=1, top_num=5)
    want = [0, 1, 2, 4]
    print("  手牌 %s 台面 红5 → 可出下标 %s (期望 %s) %s" %
          (hand, got, want, "OK " if got == want else "FAIL"))
    if got != want:
        ok = False

    print("== 狼人杀投票")
    alive = ["A", "B", "C", "D"]
    votes = [("A", "B"), ("B", "B"), ("C", "D"), ("D", "B")]
    got = vote_result(votes, alive)
    print("  票型 %s → 最高%s票，候选 %s" % (votes, got[0], got[1]))
    if got != (3, ["B"]):
        ok = False
        print("    FAIL（期望 3 票 / ['B']）")
    votes2 = [("A", "B"), ("B", "C"), ("C", "B"), ("D", "C")]
    got2 = vote_result(votes2, alive)
    print("  平票票型 → 最高%s票，候选 %s（应为平票两人）" % (got2[0], got2[1]))
    if got2 != (2, ["B", "C"]):
        ok = False
        print("    FAIL（期望 2 票 / ['B','C']）")

    print("\n基线:", "ALL_OK" if ok else "HAS_FAIL")
    sys.exit(0 if ok else 1)
