# -*- coding: utf-8 -*-
"""先用 Python 验证「迭代回溯」算法，再翻译成 Scratch 积木。

这个文件不是交付物，是翻译前的正确性基线：
Scratch 里调试回溯非常痛苦（看不到中间状态），
先在 Python 里把「行/列/回退」的推进规则跑对，再一比一翻成 IR。
"""
import sys


def n_queens(n, limit=10 ** 9):
    """迭代回溯（不用递归）：返回 (解数, 访问节点数)。

    状态：cols[i] = 第 i 行皇后所在列（1-based，0 = 未放）
    """
    cols = [0] * (n + 1)
    row = 1
    count = 0
    nodes = 0
    while row >= 1 and count < limit:
        nodes += 1
        trial = cols[row] + 1          # 从上一轮的下一个列开始试
        found = False
        while trial <= n:
            conflict = False
            for k in range(1, row):
                if cols[k] == trial or abs(cols[k] - trial) == row - k:
                    conflict = True
                    break
            if not conflict:
                found = True
                break
            trial += 1
        if found:
            cols[row] = trial
            row += 1
            if row > n:                 # 找到一个解
                count += 1
                row = n                 # 回到最后一行，继续找下一个
        else:
            # ⚠️ 回退时**只清空本行**，不要在这里 cols[row] += 1：
            #    上一轮的「下一列」由循环开头的 trial = cols[row] + 1 负责，
            #    这里再加一次就跳过一个候选列（n=8 只能找到 14 个解而不是 92）。
            cols[row] = 0
            row -= 1
    return count, nodes


def gcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def frac_add(a, b, c, d):
    """a/b + c/d，返回化简后的 (分子, 分母)。"""
    num = a * d + c * b
    den = b * d
    g = gcd(num, den) or 1
    num, den = num // g, den // g
    if den < 0:
        num, den = -num, -den
    return num, den


def primes_upto(n):
    if n < 2:
        return []
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    i = 2
    while i * i <= n:
        if sieve[i]:
            j = i * i
            while j <= n:
                sieve[j] = False
                j += i
        i += 1
    return [i for i in range(2, n + 1) if sieve[i]]


if __name__ == "__main__":
    print("== N 皇后（已知解数：4→2, 5→10, 6→4, 7→40, 8→92）")
    ok = True
    for n, want in ((4, 2), (5, 10), (6, 4), (7, 40), (8, 92)):
        got, nodes = n_queens(n)
        flag = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print("  n=%d 解数=%d（期望 %d）节点=%d  %s" % (n, got, want, nodes, flag))

    print("== 分数运算")
    cases = [((1, 2, 1, 3), (5, 6)), ((3, 4, -1, 6), (7, 12)),
             ((1, 3, 2, 3), (1, 1)), ((2, 6, 1, 6), (1, 2))]
    for (a, b, c, d), want in cases:
        got = frac_add(a, b, c, d)
        flag = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print("  %d/%d + %d/%d = %d/%d（期望 %d/%d）%s" % (a, b, c, d, got[0], got[1],
                                                          want[0], want[1], flag))

    print("== 质数筛")
    ps = primes_upto(100)
    print("  2..100 质数个数 = %d（期望 25）  %s" % (len(ps), "OK " if len(ps) == 25 else "FAIL"))
    if len(ps) != 25:
        ok = False

    print("\n基线:", "ALL_OK" if ok else "HAS_FAIL")
    sys.exit(0 if ok else 1)
