#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成第一人称迷宫示例 firstperson.yaml（用 yaml.dump，避免手写 YAML 踩坑）。

设计要点见 references/first-person.md（深入射线投射见 references/deep-shadow-raycasting.md）。
关键决策：
- 地图用一维列表 迷宫（5x5，1=墙 0=地板）表示；格子 = 行*5+列+1。
- 射线/前方探测：forward = (px+round(cos pdir), py+round(sin pdir))，命中墙或越界即挡路。
- 用「位置数学 + 列表」而非 touching，无头也能验证撞墙与移动守卫。

用法: python gen_firstperson.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "firstperson.yaml")

# 5x5 迷宫：外圈墙，内部留通道，中心(2,2)放一格墙做遮挡
MAZE = [
    1, 1, 1, 1, 1,
    1, 0, 0, 0, 1,
    1, 0, 1, 0, 1,
    1, 0, 0, 0, 1,
    1, 1, 1, 1, 1,
]


def stage_scripts():
    return [
        [{"when_green_flag_clicked": None},
         SET("px", 1), SET("py", 1), SET("pdir", 0),   # 起点(1,1) 朝东(pdir=0)
         SET("前方墙", 0), SET("步长", 1)],
        # 探测正前方：forward=(px+round(cos pdir), py+round(sin pdir))
        [RECV("探测"),
         SET("fx", ADD(V("px"), ROUND(COS(V("pdir"))))),
         SET("fy", ADD(V("py"), ROUND(SIN(V("pdir"))))),
         IFELSE(ORn(LT(V("fx"), 0), GT(V("fx"), 4), LT(V("fy"), 0), GT(V("fy"), 4)),
                SET("前方墙", 1),                                       # 越界视为墙
                SET("前方墙", ITEM("迷宫", ADD(ADD(MUL(V("fy"), 5), V("fx")), 1))))],
        # 前进：只有前方没墙才移动
        [RECV("前进"),
         IF(EQ(V("前方墙"), 0),
            SET("px", ADD(V("px"), ROUND(COS(V("pdir"))))),
            SET("py", ADD(V("py"), ROUND(SIN(V("pdir"))))))],
        [RECV("左转"), SET("pdir", MOD(ADD(V("pdir"), 90), 360))],
        [RECV("右转"), SET("pdir", MOD(SUB(V("pdir"), 90), 360))],
        # 真实游戏里的按键（无头不测，但让作品可玩）
        [WHENKEY("up arrow"), BR("探测"), BR("前进")],
        [WHENKEY("left arrow"), BR("左转")],
        [WHENKEY("right arrow"), BR("右转")],
    ]


project = {
    "project": {
        "name": "第一人称迷宫示例",
        "stage": {
            "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
            "variables": {
                "px": 1, "py": 1, "pdir": 0, "前方墙": 0, "步长": 1,
                "fx": 0, "fy": 0,
            },
            # 列表必须给 Python 列表，yaml.safe_dump(default_flow_style=False) 会块式写出
            "lists": {"迷宫": list(MAZE)},
            "scripts": stage_scripts(),
        },
        "sprites": [
            {"name": "玩家", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {"是克隆": 0},
             "scripts": [
                 [{"when_green_flag_clicked": None}, {"hide": None}],
             ]},
        ],
    }
}


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT, "迷宫=", MAZE)
