#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《乐器编曲台》示例 music_band.yaml。

核心是「音乐转乐器」：把**简谱**解析成 MIDI 音高，再用**变量指定的乐器**演奏。

三个可硬校验的点：
  1. 简谱 → MIDI：1 1 5 5 6 6 5（C 调 4 组）→ 60 60 67 67 69 69 67
  2. 八度偏移：八度=5 时全部 +12
  3. 乐器切换：set instrument to (变量) 后，VM 里 currentInstrument 真的变了

⚠️ 「演奏」积木（play note for beats）按虚拟时间阻塞，无头环境也会等 ——
   所以校验只测解析与换乐器，不触发演奏（否则测一个长谱会超时）。

机制说明见 references/music-and-instruments.md（第三十二册 §305–§318）。

用法: python gen_music_band.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "music_band.yaml")


def cat(*parts):
    s = parts[0]
    for p in parts[1:]:
        s = JOIN(s, p)
    return s


DELALL = lambda l: {"delete_all_of_list": {"list": l}}
LADD = lambda l, v: {"add_to_list": {"list": l, "item": v}}
LLEN = lambda l: {"length_of_list": {"list": l}}
SHOW = lambda: {"show": None}
HIDE = lambda: {"hide": None}

# 音乐扩展
SETINST = lambda x: {"music_set_instrument": {"INSTRUMENT": x}}
PLAYNOTE = lambda n, b: {"music_play_note_for_beats": {"NOTE": n, "BEATS": b}}
SETTEMPO = lambda t: {"music_set_tempo": {"TEMPO": t}}

# 简谱 1..7 → 半音偏移（C 大调）
SEMITONE = [0, 2, 4, 5, 7, 9, 11]
# 小星星（1 1 5 5 6 6 5 | 4 4 3 3 2 2 1）
TWINKLE = [1, 1, 5, 5, 6, 6, 5, 4, 4, 3, 3, 2, 2, 1]

STAGE_VARS = {
    "乐器": 1,          # 1=钢琴 … 21=管弦乐（Scratch 乐器编号从 1 开始）
    "低音乐器": 6,      # 6=贝斯
    "八度": 4,          # 4 = C4 起（MIDI 60）
    "节拍": 0.25,       # 每个音符几拍
    "音符数": 0,
    "状态": "就绪",
    "i": 0, "v": 0, "偏移": 0, "音高": 0,
    "帧计数": 0, "自动帧": 1,
}
STAGE_LISTS = {
    "简谱": TWINKLE,
    "偏移表": SEMITONE,
    "音高表": [0],
}


def parse_script():
    """简谱 → MIDI。休止（0）写 0，让演奏脚本能跳过。"""
    return [
        RECV("解析简谱"),
        SET("音符数", LLEN("简谱")),
        DELALL("音高表"),
        *repv("i", V("音符数"), *[
            SET("v", ITEM("简谱", V("i"))),
            IFELSE(EQ(V("v"), 0),
                   LADD("音高表", 0),
                   [SET("偏移", ITEM("偏移表", V("v"))),
                    # MIDI = 60 + 半音偏移 + 12 × (八度 − 4)
                    SET("音高", ADD(ADD(60, V("偏移")), MUL(12, SUB(V("八度"), 4)))),
                    LADD("音高表", V("音高"))]),
        ]),
        SET("状态", cat("已解析 ", V("音符数"), " 个音，乐器 ", V("乐器"), " 八度 ", V("八度"))),
    ]


def instrument_script():
    """换乐器：**用变量驱动**（这是「音乐转乐器」的关键）。

    Scratch 的 set instrument 下拉菜单可以插入一个数字/变量，
    所以「同一段旋律换不同乐器」不需要复制脚本，只改变量就行。
    """
    return [
        RECV("换乐器"),
        SETINST(V("乐器")),
        SET("状态", cat("乐器已切到 ", V("乐器"))),
    ]


def play_script():
    """演奏旋律：逐个音播放，遇到 0（休止）就只走时值。"""
    return [
        RECV("演奏旋律"),
        SETTEMPO(120),
        SETINST(V("乐器")),
        SET("音符数", LLEN("音高表")),
        *repv("i", V("音符数"), *[
            SET("音高", ITEM("音高表", V("i"))),
            IF(EQ(V("音高"), 0),
               {"music_rest_for_beats": {"BEATS": V("节拍")}},
               PLAYNOTE(V("音高"), V("节拍"))),
        ]),
        SET("状态", "旋律演奏完"),
    ]


def bass_script():
    """低音声部：同一份音高表降八度，用贝斯演奏（多声部的第二层）。"""
    return [
        RECV("演奏低音"),
        SETTEMPO(120),
        SETINST(V("低音乐器")),
        SET("音符数", LLEN("音高表")),
        *repv("i", V("音符数"), *[
            SET("音高", ITEM("音高表", V("i"))),
            IF(GT(V("音高"), 12),
               PLAYNOTE(SUB(V("音高"), 12), MUL(V("节拍"), 2))),
        ]),
    ]


def stage_scripts():
    return [
        [{"when_green_flag_clicked": None},
         SET("自动帧", 1), SET("乐器", 1), SET("八度", 4), SET("节拍", 0.25),
         SET("状态", "乐器编曲台：简谱 → 音高 → 演奏"),
         SHOW(),
         FOREVER(IF(EQ(V("自动帧"), 1), [CHG("帧计数", 1), BR("帧")]), W())],
        [RECV("重置"), SET("状态", "已重置")],
    ]


project = {
    "project": {
        "name": "乐器编曲台（简谱转乐器演奏）",
        "stage": {
            "backdrops": [{"name": "舞台", "asset": "assets/uikit/bg_menu.svg"}],
            "variables": STAGE_VARS,
            "lists": STAGE_LISTS,
            "scripts": stage_scripts(),
        },
        "sprites": [
            # 逻辑集中在一个角色：跨角色 = 跨时序
            {"name": "编曲台", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [parse_script(), instrument_script(), play_script(),
                         [{"when_green_flag_clicked": None}, HIDE()]]},

            # 低音声部：独立角色 = 独立乐器状态（Scratch 的音乐状态是「每个 target 一份」）
            {"name": "低音声部", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [bass_script(),
                         [{"when_green_flag_clicked": None}, HIDE()]]},

            {"name": "显示板", "x": -226, "y": 166,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, GOTO(-226, 166), SETSIZE(56), SHOW()],
                 [RECV("帧"), {"looks_say": {"MESSAGE": V("状态")}}],
             ]},
        ],
    }
}

if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False)
    print("IR 已写出:", OUT, " 角色数=", len(project["project"]["sprites"]),
          " 简谱=", TWINKLE)
