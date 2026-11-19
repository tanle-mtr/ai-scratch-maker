#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《数学实验室》示例 math_lab.yaml。

三个模式，都对应一个**有唯一正确答案**的数学问题 —— 这样才能被自动校验：
  1. N 皇后（迭代回溯）      已知解数：4→2, 5→10, 6→4, 7→40, 8→92
  2. 分数加法（gcd 化简）    1/2+1/3=5/6, 3/4−1/6=7/12
  3. 埃氏筛（1..100 质数）   共 25 个

算法先在 `deploy-tools/math_reference.py` 里用 Python 跑对，再一比一翻成 IR
（Scratch 里调试回溯非常痛苦：看不到中间状态，只能靠解数猜）。

机制说明见 references/math-and-reasoning.md（第三十册 §277–§290）。

用法: python gen_math_lab.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "math_lab.yaml")


def cat(*parts):
    s = parts[0]
    for p in parts[1:]:
        s = JOIN(s, p)
    return s


SHOW = lambda: {"show": None}
HIDE = lambda: {"hide": None}


# 列表积木（build_sb3 把 list 当字段名处理）
DELALL = lambda l: {"delete_all_of_list": {"list": l}}
LADD = lambda l, v: {"add_to_list": {"list": l, "item": v}}
LLEN = lambda l: {"length_of_list": {"list": l}}

STAGE_VARS = {
    # 通用
    "模式": 0, "帧计数": 0, "自动帧": 1, "结果": "",
    # N 皇后
    "n": 8, "行": 0, "试用": 0, "找到": 0, "冲突": 0, "k": 0,
    "解数": 0, "节点数": 0, "解上限": 100000,
    # 分数
    "fa": 1, "fb": 2, "fc": 1, "fd": 3,
    "分子": 0, "分母": 0, "g": 0, "r": 0, "tmp": 0,
    # 质数
    "上限": 100, "质数个数": 0, "i": 0, "j": 0,
    # 画面
    "格子": 30,
}
STAGE_LISTS = {
    "皇后列": [0],      # 长度 = n，索引 1..n（用时重建）
    "筛表": [0],        # 长度 = 上限
    "质数表": [0],
}

X0 = -120      # 棋盘左上角 x
TOP = 100      # 棋盘左上角 y（给顶部状态气泡留位置）
COL_LINE = "#4F4A47"
COL_Q = "#FFCF4D"
COL_BG = "#FFFDF7"


# ------------------------------------------------------------------ N 皇后
def queens_script():
    """迭代回溯：不用递归（Scratch 没有返回值），用一个「行号 + 列数组」手动回退。

    推进规则（与 math_reference.py 完全一致）：
      每轮开头 trial = 皇后列[行] + 1  →  找本行下一个不冲突的列
      找到   →  落子、行+1；若 行>n 则 解数+1 且 行=n（回到最后一行继续找）
      找不到 →  清空本行、行-1（**不要在这里 +1**，否则跳过候选列）
    """
    return [
        RECV("跑皇后"),
        SET("解数", 0), SET("节点数", 0),
        DELALL("皇后列"),
        REPEAT(V("n"), LADD("皇后列", 0)),
        SET("行", 1),
        REPEAT_UNTIL(ORn(LT(V("行"), 1), GE(V("解数"), V("解上限"))), [
            CHG("节点数", 1),
            SET("试用", ADD(ITEM("皇后列", V("行")), 1)),
            SET("找到", 0),
            # 找本行下一个不冲突的列
            REPEAT_UNTIL(ORn(GT(V("试用"), V("n")), EQ(V("找到"), 1)), [
                SET("冲突", 0),
                SET("k", 0),
                REPEAT(SUB(V("行"), 1), [
                    CHG("k", 1),
                    IF(ORn(EQ(ITEM("皇后列", V("k")), V("试用")),
                           EQ(ABS(SUB(ITEM("皇后列", V("k")), V("试用"))),
                              SUB(V("行"), V("k")))),
                       SET("冲突", 1)),
                ]),
                IFELSE(EQ(V("冲突"), 0), SET("找到", 1), CHG("试用", 1)),
            ]),
            IFELSE(EQ(V("找到"), 1),
                   [REP("皇后列", V("行"), V("试用")),
                    CHG("行", 1),
                    IF(GT(V("行"), V("n")), [CHG("解数", 1), SET("行", V("n"))])],
                   [REP("皇后列", V("行"), 0),
                    CHG("行", -1)]),
        ]),
        SET("结果", cat("N 皇后 n=", V("n"), "  解数=", V("解数"), "  访问节点=", V("节点数"))),
        BR("画棋盘"),
    ]


# ------------------------------------------------------------------ 分数
def frac_script():
    """a/b + c/d：通分 → 相加 → 辗转相除求 gcd → 化简。

    ⚠️ 化简必须用 ROUND(分子/g)：Scratch 的除法是浮点，
       8/4 会得到 2，但 6/3 也可能出现 1.9999999 这种尾数。
    """
    return [
        RECV("跑分数"),
        SET("分子", ADD(MUL(V("fa"), V("fd")), MUL(V("fc"), V("fb")))),
        SET("分母", MUL(V("fb"), V("fd"))),
        # 辗转相除：g = gcd(|分子|, |分母|)
        SET("g", ABS(V("分子"))),
        SET("tmp", ABS(V("分母"))),
        REPEAT_UNTIL(EQ(V("tmp"), 0), [
            SET("r", MOD(V("g"), V("tmp"))),
            SET("g", V("tmp")),
            SET("tmp", V("r")),
        ]),
        IF(EQ(V("g"), 0), SET("g", 1)),
        SET("分子", ROUND(DIV(V("分子"), V("g")))),
        SET("分母", ROUND(DIV(V("分母"), V("g")))),
        # 分母恒正
        IF(LT(V("分母"), 0), [SET("分子", SUB(0, V("分子"))),
                              SET("分母", SUB(0, V("分母")))]),
        SET("结果", cat(V("fa"), "/", V("fb"), " + ", V("fc"), "/", V("fd"),
                       " = ", V("分子"), "/", V("分母"))),
    ]


# ------------------------------------------------------------------ 质数筛
def prime_script():
    """埃氏筛：筛表[i]=1 表示 i 还「可能是质数」。

    只筛到 √n（`i*i > 上限` 就停）：后面的数如果还有倍数，
    它自己的最小质因子一定小于 √n，早被划掉了。
    """
    return [
        RECV("跑质数"),
        SET("质数个数", 0),
        DELALL("筛表"), DELALL("质数表"),
        REPEAT(V("上限"), LADD("筛表", 1)),
        REP("筛表", 1, 0),
        SET("i", 2),
        REPEAT_UNTIL(GT(MUL(V("i"), V("i")), V("上限")), [
            IF(EQ(ITEM("筛表", V("i")), 1), [
                SET("j", MUL(V("i"), V("i"))),
                REPEAT_UNTIL(GT(V("j"), V("上限")), [
                    REP("筛表", V("j"), 0),
                    CHG("j", V("i")),
                ]),
            ]),
            CHG("i", 1),
        ]),
        SET("i", 1),
        REPEAT(V("上限"), [
            IF(EQ(ITEM("筛表", V("i")), 1), [
                CHG("质数个数", 1),
                LADD("质数表", V("i")),
            ]),
            CHG("i", 1),
        ]),
        SET("结果", cat("1~", V("上限"), " 的质数共 ", V("质数个数"), " 个")),
    ]


# ------------------------------------------------------------------ 棋盘（画笔）
def board_scripts():
    """静态网格 + 最后一个解的皇后位置。

    只在「跑完」后画一次（收到 画棋盘）：
    回溯过程中每帧重画 64 格会把校验拖慢几十倍，而玩家其实看不清中间态。
    """
    grid = []
    grid.append({"pen_clear": None})
    grid.append({"set_pen_color": {"COLOR": COL_LINE}})
    grid.append({"set_pen_size": {"size": 2}})
    grid.append({"pen_up": None})
    # 横线：y = TOP - 格子*(i-1)，i=1..n+1
    grid += repv("i", ADD(V("n"), 1), *[
        GOTO(X0, SUB(TOP, MUL(V("格子"), SUB(V("i"), 1)))),
        {"pen_down": None},
        GOTO(SUB(0, X0), SUB(TOP, MUL(V("格子"), SUB(V("i"), 1)))),
        {"pen_up": None},
    ])
    # 竖线：x = X0 + 格子*(i-1)
    grid += repv("i", ADD(V("n"), 1), *[
        GOTO(ADD(X0, MUL(V("格子"), SUB(V("i"), 1))), TOP),
        {"pen_down": None},
        GOTO(ADD(X0, MUL(V("格子"), SUB(V("i"), 1))), SUB(TOP, MUL(V("格子"), V("n")))),
        {"pen_up": None},
    ])
    # 皇后：格心画粗点
    grid += [{"set_pen_color": {"COLOR": COL_Q}},
             {"set_pen_size": {"size": 18}}]
    grid += repv("i", V("n"), *[
        GOTO(ADD(X0, MUL(V("格子"), SUB(ITEM("皇后列", V("i")), 0.5))),
             SUB(TOP, MUL(V("格子"), SUB(V("i"), 0.5)))),
        {"pen_down": None},
        {"pen_up": None},
    ])
    return [
        [{"when_green_flag_clicked": None}, {"hide": None}, {"pen_clear": None}],
        [RECV("画棋盘"), *grid],
    ]


def stage_scripts():
    return [
        [{"when_green_flag_clicked": None},
         SET("自动帧", 1), SET("模式", 0), SET("结果", "按 1/2/3 切换：N 皇后 / 分数 / 质数"),
         SHOW(),
         FOREVER(IF(EQ(V("自动帧"), 1), [CHG("帧计数", 1), BR("帧")]), W())],
        [RECV("重置"), SET("结果", "已重置")],
    ]


project = {
    "project": {
        "name": "数学实验室（回溯 / 分数 / 质数）",
        "stage": {
            "backdrops": [{"name": "实验室", "asset": "assets/uikit/bg_menu.svg"}],
            "variables": STAGE_VARS,
            "lists": STAGE_LISTS,
            "scripts": stage_scripts(),
        },
        "sprites": [
            # 所有数学逻辑集中在一个角色：跨角色 = 跨时序 = bug
            {"name": "数学引擎", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [queens_script(), frac_script(), prime_script(),
                         [{"when_green_flag_clicked": None}, {"hide": None}]]},

            {"name": "棋盘", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": board_scripts()},

            {"name": "显示板", "x": -232, "y": 168,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None},
                  GOTO(-232, 168), SETSIZE(70), SHOW()],
                 [RECV("帧"), {"looks_say": {"MESSAGE": V("结果")}}],
             ]},
        ],
    }
}

if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False)
    print("IR 已写出:", OUT, " 角色数=", len(project["project"]["sprites"]))
