#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成五子棋示例 board_gomoku.yaml（用 yaml.dump，避免手写 YAML 踩坑）。

设计要点见 references/board-games.md。
关键决策：
- 棋盘用一维列表 棋盘（9x9=81，0=空 1=黑 2=白），格子 = 行*9+列+1（Scratch 列表 1 基）。
- 落子走「广播 + 全局变量」；胜负判定在落子时扫描四方向连子（每方向前/后各数 4 格）。
- 用「位置数学 + 列表」而非 touching，无头也能验证棋盘表示、落子轮换与五连珠判定。

用法: python gen_board.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "board_gomoku.yaml")

N = 9


def win_dir(dx, dy):
    """从落子点沿 (dx,dy) 正反各数 4 格，连续的同色子计入 连数。
    命中同色且仍在盘内 → 连数+1（继续）；否则 → 继续=0（停止扫描）。
    """
    blocks = []
    # 正方向
    blocks += [SET("检查行", V("行")), SET("检查列", V("列")), SET("继续", 1)]
    for _ in range(4):
        blocks.append(SET("检查列", ADD(V("检查列"), dx)))
        blocks.append(SET("检查行", ADD(V("检查行"), dy)))
        cond = ANDn(
            GE(V("检查行"), 0), LE(V("检查行"), N - 1),
            GE(V("检查列"), 0), LE(V("检查列"), N - 1),
            EQ(ITEM("棋盘", ADD(ADD(MUL(V("检查行"), N), V("检查列")), 1)), V("轮到")),
        )
        blocks.append(IFELSE(AND(EQ(V("继续"), 1), cond),
                             CHG("连数", 1),          # 命中同色 → 计数并继续
                             SET("继续", 0)))         # 未命中/已停 → 停止本方向
    # 反方向
    blocks += [SET("检查行", V("行")), SET("检查列", V("列")), SET("继续", 1)]
    for _ in range(4):
        blocks.append(SET("检查列", SUB(V("检查列"), dx)))
        blocks.append(SET("检查行", SUB(V("检查行"), dy)))
        cond = ANDn(
            GE(V("检查行"), 0), LE(V("检查行"), N - 1),
            GE(V("检查列"), 0), LE(V("检查列"), N - 1),
            EQ(ITEM("棋盘", ADD(ADD(MUL(V("检查行"), N), V("检查列")), 1)), V("轮到")),
        )
        blocks.append(IFELSE(AND(EQ(V("继续"), 1), cond),
                             CHG("连数", 1),
                             SET("继续", 0)))
    return blocks


def stage_scripts():
    reset_board = repv("__k", N * N, REP("棋盘", V("__k"), 0))
    return [
        # 一局开始：清空棋盘、轮换归位、胜负复位
        [{"when_green_flag_clicked": None},
         SET("轮到", 1), SET("胜者", 0), SET("局结束", 0),
         SET("行", 0), SET("列", 0), SET("连数", 0),
         *reset_board],
        # 落子：仅当本局未结束、目标格为空才落子，随后判定胜负并换手
        [RECV("落子"),
         IF(EQ(V("局结束"), 0),                       # 守卫：本局未结束才处理
            [SET("idx", ADD(ADD(MUL(V("行"), N), V("列")), 1)),   # 1 基索引
             IF(EQ(ITEM("棋盘", V("idx")), 0),        # 守卫：目标格为空
                [REP("棋盘", V("idx"), V("轮到")),    # 写入棋盘
                 SET("连数", 1),                      # 自己这一子先算 1
                 *win_dir(1, 0), *win_dir(0, 1), *win_dir(1, 1), *win_dir(1, -1),
                 IF(GE(V("连数"), 5),                 # 五连珠（>=5 也判胜）
                    SET("胜者", V("轮到")), SET("局结束", 1)),
                 SET("轮到", SUB(3, V("轮到")))])])], # 换手 1<->2
        # 悔棋/重开：直接复位（真实作品可改成「弹出最后一手」）
        [RECV("重开"), SET("轮到", 1), SET("胜者", 0), SET("局结束", 0),
         *repv("__k", N * N, REP("棋盘", V("__k"), 0))],
    ]


project = {
    "project": {
        "name": "五子棋示例",
        "stage": {
            "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
            "variables": {
                "轮到": 1, "胜者": 0, "局结束": 0,
                "行": 0, "列": 0, "idx": 0, "连数": 0,
                "检查行": 0, "检查列": 0, "继续": 1,
            },
            "lists": {"棋盘": [0] * (N * N)},
            "scripts": stage_scripts(),
        },
        "sprites": [
            {"name": "棋子", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {"是克隆": 0, "格行": 0, "格列": 0, "自身值": 0},
             "scripts": [
                 [{"when_green_flag_clicked": None}, {"hide": None}],
                 # 每落一子生成一个克隆（克隆守卫：本体才生成，防指数爆炸）
                 [RECV("落子"), IF(EQ(V("是克隆"), 0), CLONE())],
                 # 重开时清掉所有棋子克隆
                 [RECV("重开"), IF(EQ(V("是克隆"), 1), DEL())],
                 # 克隆捕获落子时的格子，并从棋盘读自身颜色（1=黑 2=白）
                 [{"when_start_as_clone": None},
                  SET("是克隆", 1),
                  SET("格行", V("行")), SET("格列", V("列")),
                  SET("自身值", ITEM("棋盘", ADD(ADD(MUL(V("格行"), N), V("格列")), 1))),
                  {"show": None}],
             ]},
        ],
    }
}


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT, "棋盘格数=", N * N)
