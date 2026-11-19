#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成联机回合示例 multiplayer.yaml（用 yaml.dump，避免手写 YAML 踩坑）。

设计要点见 references/multiplayer.md。
关键决策：
- 联机唯一的共享通道是「云变量」：云_回合（该谁走）、云_进度（共享进度）。
- 回合守卫：只有 本机玩家==云_回合 时才写共享通道并交换回合；否则输入被忽略。
- 这能在无头 scratch-vm 里验证「云变量写入 + 回合交换 + 非己方回合忽略」的核心逻辑。

用法: python gen_multiplayer.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "multiplayer.yaml")


def stage_scripts():
    return [
        # 一局开始：复位集中在这里
        [{"when_green_flag_clicked": None},
         SET("本机玩家", 1), SET("云_回合", 1), SET("云_进度", 0),
         SET("局结束", 0), SET("本机步进", 0)],
        # 本地玩家行动：只有轮到自己（本机玩家==云_回合）才写共享通道
        [RECV("我的回合行动"),
         IF(EQ(V("局结束"), 0),
            IF(EQ(V("本机玩家"), V("云_回合")),
               SET("本机步进", 1),
               SET("云_进度", ADD(V("云_进度"), 1)),        # 写入共享通道（云变量）
               SET("云_回合", SUB(3, V("云_回合"))),         # 把回合交给对方（1<->2）
               IF(EQ(V("云_进度"), 5), SET("局结束", 1))     # 进度到 5 即结束
            )
         )],
    ]


project = {
    "project": {
        "name": "联机回合示例",
        "stage": {
            "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
            "variables": {
                "本机玩家": 1,
                # 云变量：联机唯一的共享通道（isCloud=true）
                "云_回合": {"value": 1, "cloud": True},
                "云_进度": {"value": 0, "cloud": True},
                "局结束": 0,
                "本机步进": 0,
            },
            "scripts": stage_scripts(),
        },
        "sprites": [
            {"name": "客户端A", "x": 0, "y": 0,
             "costumes": [{"name": "c", "asset": "assets/dot.svg"}],
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
    print("IR 已写出:", OUT)
