#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成分支叙事示例 story.yaml（视觉小说 / 互动叙事，用 yaml.dump 避免手写 YAML 踩坑）。

设计要点见 references/story-narrative.md（第十九册 §148–§155）。
关键决策：
- 剧情图用「平行列表」描述：节点文本 / 节点类型 / 自动下一 / 选项A·B文本 / 选项A·B跳转 / 结局值。
  运行时只维护一个「当前节点」变量，所有显示与跳转都从列表读 —— 改剧情只动列表、不动逻辑。
- 打字机逐字显示用 REPEAT_UNTIL + letter_of + join（绝不用固定次数 REPEAT）。
- 分支用「选项广播 → 改写当前节点 → 重播演节点」；选项用按钮角色而非「询问」积木（铁律 11）。
- 「对话锁」：对话进行中 对话中=1，玩家移动被挡；结局后 对话中=0 才放开。

剧情（6 节点 / 双结局）：
  1 旁白「你醒来在神秘森林。」  → 2
  2 精灵「你要往哪走？」 选项: 向左走→3 / 向右走→4
  3 旁白「左边有一只宝箱！」  → 5 (结局一)
  4 旁白「右边有一只怪物……」  → 6 (结局二)
  5 结局「【结局一：获得宝藏】」  结局值=1
  6 结局「【结局二：险胜怪物】」  结局值=2

用法: python gen_story.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "story.yaml")

# ---- 剧情图（平行列表，长度=节点数；1-based 索引）----
N = 6
节点文本 = [
    "你醒来在神秘森林。",
    "精灵：你要往哪走？",
    "左边有一只宝箱！",
    "右边有一只怪物……",
    "【结局一：获得宝藏】",
    "【结局二：险胜怪物】",
]
节点类型 = [0, 1, 0, 0, 2, 2]          # 0=对话自动推进 1=二选一 2=结局
自动下一 = [2, 0, 5, 6, 0, 0]
选项A文本 = ["", "向左走", "", "", "", ""]
选项B文本 = ["", "向右走", "", "", "", ""]
选项A跳转 = [0, 3, 0, 0, 0, 0]
选项B跳转 = [0, 4, 0, 0, 0, 0]
结局值 = [0, 0, 0, 0, 1, 2]


def stage_scripts():
    return [
        # 一局开始：复位所有剧情状态，然后从节点 1 开始演出
        [{"when_green_flag_clicked": None},
         SET("当前节点", 1), SET("显示文本", ""), SET("打字进度", 0), SET("当前文本", ""),
         SET("对话中", 1), SET("待推进", 0), SET("待选择", 0),
         SET("结局", 0), SET("结局1计数", 0), SET("结局2计数", 0),
         BR("演节点")],

        # 演节点：先按节点类型提前置位「等待态」标志（打字前就确定，避免打完字才置位导致一帧延迟），再打字机逐字显示，结局节点一进入即结算
        [RECV("演节点"),
         SET("当前文本", ITEM("节点文本", V("当前节点"))),
         SET("显示文本", ""), SET("打字进度", 0),
         # 类型 0：对话，等「推进」广播（打字前就置位）
         IF(EQ(ITEM("节点类型", V("当前节点")), 0), SET("待推进", 1)),
         # 类型 1：选择，等「选A/选B」，并亮出选项按钮
         IF(EQ(ITEM("节点类型", V("当前节点")), 1), SET("待选择", 1), BR("显示选项")),
         # 类型 2：结局，一进入就赋值 + 计数 + 放开对话锁 + 进结算（在打字前完成，避免延迟）
         IF(EQ(ITEM("节点类型", V("当前节点")), 2),
            SET("结局", ITEM("结局值", V("当前节点"))),
            IF(EQ(V("结局"), 1), CHG("结局1计数", 1)),
            IF(EQ(V("结局"), 2), CHG("结局2计数", 1)),
            SET("对话中", 0),
            BR("结算")),
         # 打字机逐字显示（标志已就绪，玩家可在打完字后操作）
         REPEAT_UNTIL(EQ(V("打字进度"), LEN(V("当前文本"))),
                      SET("显示文本", JOIN(V("显示文本"), LETTER_OF(ADD(V("打字进度"), 1), V("当前文本")))),
                      CHG("打字进度", 1),
                      W())],

        # 推进（对话节点看完后点击/按键/空格触发）
        [RECV("推进"),
         IF(EQ(V("待推进"), 1),
            SET("待推进", 0),
            SET("当前节点", ITEM("自动下一", V("当前节点"))),
            BR("演节点"))],

        # 选 A（选项左按钮）：改写当前节点后重播
        [RECV("选A"),
         IF(EQ(V("待选择"), 1),
            SET("待选择", 0),
            SET("当前节点", ITEM("选项A跳转", V("当前节点"))),
            BR("演节点"))],

        # 选 B（选项右按钮）
        [RECV("选B"),
         IF(EQ(V("待选择"), 1),
            SET("待选择", 0),
            SET("当前节点", ITEM("选项B跳转", V("当前节点"))),
            BR("演节点"))],
    ]


project = {
    "project": {
        "name": "分支叙事示例",
        "stage": {
            "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
            "variables": {
                "当前节点": 1, "显示文本": "", "打字进度": 0, "当前文本": "",
                "对话中": 1, "待推进": 0, "待选择": 0,
                "结局": 0, "结局1计数": 0, "结局2计数": 0,
            },
            "lists": {
                "节点文本": 节点文本,
                "节点类型": 节点类型,
                "自动下一": 自动下一,
                "选项A文本": 选项A文本,
                "选项B文本": 选项B文本,
                "选项A跳转": 选项A跳转,
                "选项B跳转": 选项B跳转,
                "结局值": 结局值,
            },
            "scripts": stage_scripts(),
        },
        "sprites": [
            # 玩家：对话锁演示 —— 对话中=1 时移动被挡，结局后(对话中=0)才放开
            {"name": "玩家", "x": 0, "y": -100,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, GOTO(0, -100)],
                 [RECV("移动"), IF(EQ(V("对话中"), 0), CHX(10))],
             ]},
            # 选项 A 按钮（点击广播 选A，不用「询问」积木 —— 铁律 11）
            {"name": "选项A", "x": -100, "y": -120,
             "costumes": [{"name": "btnA", "asset": "assets/btnA.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, {"hide": None}],
                 [RECV("显示选项"), {"show": None}],
                 [WHENCLICK(), BR("选A")],
             ]},
            # 选项 B 按钮
            {"name": "选项B", "x": 100, "y": -120,
             "costumes": [{"name": "btnB", "asset": "assets/btnB.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, {"hide": None}],
                 [RECV("显示选项"), {"show": None}],
                 [WHENCLICK(), BR("选B")],
             ]},
        ],
    }
}


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT, "节点数=", N, "结局数=", len([v for v in 结局值 if v]))
