#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成伪3D透视投影示例 3d_demo.yaml（用 yaml.dump，避免手写 YAML 踩坑）。

设计要点见 references/3d-games.md。
关键决策：
- 伪3D 用「透视除法」：屏幕坐标 = 世界坐标 / 深度 * K；尺寸 ∝ 1/深度。
- 所有计算在「球」精灵里跑（读取舞台全局变量 obj_*），无头也能验证投影数学。
- depth 小于阈值即「飞过摄像机」→ 重置到远处，形成无限逼近的伪3D效果。

用法: python gen_3d.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "3d_demo.yaml")


def ball_scripts():
    return [
        # 初始化世界坐标 + 投影参数，然后开始投影循环
        [{"when_green_flag_clicked": None},
         SET("obj_x", 50), SET("obj_y", 30), SET("obj_z", 200),
         SET("K", 100), SET("speed", 4), SET("passed", 0),
         BR("跑投影")],
        [RECV("跑投影"),
         FOREVER(
             SET("obj_z", SUB(V("obj_z"), V("speed"))),              # 朝摄像机逼近
            # 飞过摄像机（深度过小）→ 标记 passed 并重置到远处，循环往复
            IF(LT(V("obj_z"), 20), SET("passed", 1), SET("obj_z", 200)),
             # 透视投影：sx = x/z*K, sy = y/z*K
             SET("obj_sx", DIV(MUL(V("obj_x"), V("K")), V("obj_z"))),
             SET("obj_sy", DIV(MUL(V("obj_y"), V("K")), V("obj_z"))),
             # 距离缩放：尺寸 ∝ 1/z（物体越近越大）
             SET("obj_ssize", DIV(MUL(40, V("K")), V("obj_z"))),
             SETX(V("obj_sx")), SETY(V("obj_sy")), SETSIZE(V("obj_ssize")),
             W(),
         )],
    ]


project = {
    "project": {
        "name": "伪3D透视示例",
        "stage": {
            "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
            "variables": {
                "obj_x": 50, "obj_y": 30, "obj_z": 200,
                "K": 100, "speed": 4, "passed": 0,
                "obj_sx": 0, "obj_sy": 0, "obj_ssize": 0,
            },
            "scripts": [],
        },
        "sprites": [
            {"name": "球", "x": 0, "y": 0, "size": 100,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": ball_scripts()},
        ],
    }
}


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT)
