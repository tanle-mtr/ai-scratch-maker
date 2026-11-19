#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 examples/technique_probe9.yaml（第七册《游戏手感与交互》§75–§82 示教工程）。

用 Python 的 yaml.dump 生成，保证 YAML 语法 100% 正确；
再对关键块做人工可读性检查。
"""
import os
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ══════════════════════════════════════════════════════════════════════
# §75 拖尾系统
# ══════════════════════════════════════════════════════════════════════

彩带主角 = {
    "name": "彩带主角",
    "x": -120, "y": -120, "size": 70,
    "rotationStyle": "left-right",
    "variables": {"笔粗": 5},
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "scripts": [
        [{"when_green_flag_clicked": None},
         {"hide": None},
         {"set_pen_size": {"size": 5}},
         {"set_pen_hue": {"hue": 60}},
         {"pen_down": None},
         {"forever": {"do": [
             {"move_steps": {"steps": 3}},
             {"turn_right": 2},
             {"change_pen_hue": {"hue": 1}},
             {"if": {"cond": {"greater_than": [
                 {"sensing_of": {"object": "_myself_", "property": "x position"}}, 200]},
                 "do": [
                 {"goto_xy": {"x": -200, "y": {"random": [-140, 140]}}},
             ]}},
         ]}}],
    ],
}

残影主角 = {
    "name": "残影主角",
    "x": 120, "y": -120, "size": 60,
    "rotationStyle": "left-right",
    "variables": {
        "是克隆": 0,        # ⚠️ 私有变量：只有本体能生成残影
        "残影寿命": 14,
        "残影间隔": 0.06,
        "移动速度": 4,
    },
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "scripts": [
        # —— 阶段 0：本体（只负责生产 + 移动）——
        [{"when_green_flag_clicked": None},
         {"hide": None},
         {"set_variable": {"var": "是克隆", "value": 0}},
         {"set_variable": {"var": "残影间隔", "value": 0.06}},
         {"forever": {"do": [
             {"move_steps": {"steps": {"var": "移动速度"}}},
             {"turn_right": 3},
             {"wait": {"secs": {"var": "残影间隔"}}},
             {"create_clone_of": {"clone": "_myself_"}},
         ]}}],
        # —— 阶段 1：克隆出生 ——
        [{"when_start_as_clone": None},
         {"set_variable": {"var": "是克隆", "value": 1}},
         {"set_variable": {"var": "残影寿命", "value": 14}},
         {"show": None},
         {"set_ghost": {"ghost": 35}}],
        # —— 阶段 2：克隆生存 + 消亡（必须 delete this clone）——
        [{"when_start_as_clone": None},
         {"repeat": {"times": {"var": "残影寿命"}, "do": [
             {"change_effect": {"effect": "GHOST", "value": 5}},
             {"change_size": {"value": -1}},
         ]}},
         {"delete_this_clone": None}],
        # —— ⚠️ 本体的事件帽子也会被克隆体触发 → 用私有标志位挡住 ——
        [{"when_key_pressed": {"key": "space"}},
         {"if": {"cond": {"equals": [{"var": "是克隆"}, 0]}, "do": [
             {"create_clone_of": {"clone": "_myself_"}},
         ]}}],
    ],
}

克隆监控 = {
    "name": "克隆监控",
    "x": 200, "y": 150, "size": 30,
    "variables": {"存活克隆": 0},
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "scripts": [
        [{"when_receive": {"message": "生成克隆"}},
         {"change_variable": {"var": "克隆计数", "by": 1}}],
        [{"when_receive": {"message": "克隆销毁"}},
         {"change_variable": {"var": "克隆计数", "by": -1}}],
        [{"when_green_flag_clicked": None},
         {"forever": {"do": [
             {"if": {"cond": {"greater_than": [{"var": "克隆计数"}, 200]}, "do": [
                 {"broadcast": {"message": "克隆过多"}},
             ]}},
             {"wait": {"secs": 0.5}},
         ]}}],
    ],
}

# ══════════════════════════════════════════════════════════════════════
# §76 背景音乐
# ══════════════════════════════════════════════════════════════════════

音乐控制 = {
    "name": "音乐控制",
    "x": -200, "y": 150, "size": 30,
    "variables": {"循环中": 0},
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "sounds": [
        {"name": "平静", "asset": "assets/bgm_calm.wav"},
        {"name": "追逐", "asset": "assets/bgm_chase.wav"},
        {"name": "点击", "asset": "assets/sfx_click.wav"},
    ],
    "scripts": [
        [{"when_green_flag_clicked": None},
         {"set_variable": {"var": "目标音量", "value": 0}},
         {"set_variable": {"var": "当前音量", "value": 0}},
         {"set_volume": {"value": 0}}],
        [{"when_receive": {"message": "播放平静"}},
         {"set_variable": {"var": "当前BGM", "value": 1}},
         {"set_variable": {"var": "目标音量", "value": 70}},
         {"start_sound": {"sound": "平静"}},
         {"set_variable": {"var": "循环中", "value": 1}}],
        [{"when_receive": {"message": "播放追逐"}},
         {"set_variable": {"var": "当前BGM", "value": 2}},
         {"set_variable": {"var": "目标音量", "value": 70}},
         {"start_sound": {"sound": "追逐"}},
         {"set_variable": {"var": "循环中", "value": 1}}],
        [{"when_receive": {"message": "音乐淡出"}},
         {"set_variable": {"var": "目标音量", "value": 0}}],
        # ⚠️ 只用一个 forever 管音量，避免两个循环互相打架
        [{"when_green_flag_clicked": None},
         {"forever": {"do": [
             {"if": {"cond": {"less_than": [{"var": "当前音量"}, {"var": "目标音量"}]}, "do": [
                 {"change_variable": {"var": "当前音量", "by": 3}},
             ]}},
             {"if": {"cond": {"greater_than": [{"var": "当前音量"}, {"var": "目标音量"}]}, "do": [
                 {"change_variable": {"var": "当前音量", "by": -3}},
             ]}},
             {"set_volume": {"value": {"var": "当前音量"}}},
             {"if": {"cond": {"less_than": [{"var": "当前音量"}, 1]}, "do": [
                 {"stop_all_sounds": None},
             ]}},
         ]}}],
        # §76.4 程序化旋律（音乐扩展，零素材）
        [{"when_receive": {"message": "程序化旋律"}},
         {"set_tempo": {"tempo": 110}},
         {"set_instrument": {"instrument": 1}},
         {"repeat": {"times": 8, "do": [
             {"play_note": {"note": 60, "beats": 0.5}},
             {"play_note": {"note": 64, "beats": 0.5}},
             {"play_note": {"note": 67, "beats": 1}},
         ]}}],
        [{"when_receive": {"message": "播放点击音"}},
         {"start_sound": {"sound": "点击"}}],
    ],
}

# ══════════════════════════════════════════════════════════════════════
# §77 多角色选项菜单（每个选项一个角色按钮，全程不用「询问」积木）
# ══════════════════════════════════════════════════════════════════════


def 按钮(name, 序号, 素材, x):
    return {
        "name": name,
        "x": x, "y": 60, "size": 90,
        "variables": {"选项序号": 序号},
        "costumes": [{"name": "普通", "asset": 素材}],
        "scripts": [
            # ① 被点击 → 广播意图（不在这里决定去哪）
            [{"event_whenthisspriteclicked": None},
             {"broadcast": {"message": "菜单点击"}},
             {"start_sound": {"sound": "点击"}}],
            # ② 悬停高亮（方案 C：碰到鼠标指针 → 放大）
            [{"when_green_flag_clicked": None},
             {"forever": {"do": [
                 {"if": {"cond": {"touching_mouse_pointer": {"object": "_mouse_"}}, "do": [
                     {"change_size": {"value": 12}},
                 ]}},
                 {"if": {"cond": {"not": {"operand": {"touching_mouse_pointer": {"object": "_mouse_"}}}}, "do": [
                     {"change_size": {"value": -12}},
                 ]}},
             ]}}],
        ],
    }


按钮一 = 按钮("按钮一", 1, "assets/btnA.svg", -120)
按钮二 = 按钮("按钮二", 2, "assets/btnB.svg", 0)
按钮三 = 按钮("按钮三", 3, "assets/btnA.svg", 120)

# ══════════════════════════════════════════════════════════════════════
# §80 演出与转场：缓动滑入
# ══════════════════════════════════════════════════════════════════════

登场角色 = {
    "name": "登场角色",
    "x": 300, "y": -180, "size": 80,
    "variables": {
        "目标X": 0, "目标Y": 0,
        "当前位置X": 300, "当前位置Y": -180,
    },
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "scripts": [
        [{"when_receive": {"message": "角色登场"}},
         {"set_variable": {"var": "目标X", "value": 0}},
         {"set_variable": {"var": "目标Y", "value": 0}},
         {"show": None},
         {"forever": {"do": [
             {"set_variable": {"var": "当前位置X", "value": {"add": [
                 {"var": "当前位置X"},
                 {"divide": [{"subtract": [{"var": "目标X"}, {"var": "当前位置X"}]}, 8]},
             ]}}},
             {"set_variable": {"var": "当前位置Y", "value": {"add": [
                 {"var": "当前位置Y"},
                 {"divide": [{"subtract": [{"var": "目标Y"}, {"var": "当前位置Y"}]}, 8]},
             ]}}},
             {"goto_xy": {"x": {"var": "当前位置X"}, "y": {"var": "当前位置Y"}}},
             {"if": {"cond": {"less_than": [
                 {"subtract": [{"var": "目标X"}, {"var": "当前位置X"}]}, 2]}, "do": [
                 {"stop": {"stop": "this script"}},
             ]}},
         ]}}],
    ],
}

# ══════════════════════════════════════════════════════════════════════
# §79 受击反馈：闪白 + 击退
# ══════════════════════════════════════════════════════════════════════

受击目标 = {
    "name": "受击目标",
    "x": -200, "y": -150, "size": 70,
    "variables": {"血量": 3},
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "sounds": [{"name": "受击", "asset": "assets/sfx_hit.wav"}],
    "scripts": [
        [{"when_receive": {"message": "受到攻击"}},
         {"change_variable": {"var": "血量", "by": -1}},
         {"change_effect": {"effect": "COLOR", "value": 50}},
         {"wait": {"secs": 0.08}},
         {"change_effect": {"effect": "COLOR", "value": -50}},
         {"move_steps": {"steps": -10}},
         {"if": {"cond": {"less_than": [{"var": "血量"}, 1]}, "do": [
             {"broadcast": {"message": "敌人死亡"}},
         ]}}],
    ],
}

顿帧角色 = {
    "name": "顿帧角色",
    "x": 200, "y": -150, "size": 50,
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "scripts": [
        [{"when_green_flag_clicked": None},
         {"forever": {"do": [
             {"if": {"cond": {"equals": [{"var": "顿帧"}, 0]},
                     "do": [
                         {"move_steps": {"steps": 2}},
                         {"turn_right": 2},
                     ],
                     "else": [
                         {"change_variable": {"var": "顿帧", "by": -1}},
                     ]}},
         ]}}],
    ],
}

# ══════════════════════════════════════════════════════════════════════
# 舞台：菜单状态机 / 受击反馈 / 广播解耦 / 节奏判定
# ══════════════════════════════════════════════════════════════════════

stage_scripts = [
    # —— §77 菜单点击统一处理（按钮只发意图，这里决定去哪）——
    [{"when_receive": {"message": "菜单点击"}},
     {"if": {"cond": {"equals": [{"var": "当前选项"}, 1]}, "do": [
         {"broadcast": {"message": "打开难度菜单"}},
     ]}},
     {"if": {"cond": {"equals": [{"var": "当前选项"}, 2]}, "do": [
         {"broadcast": {"message": "开始游戏"}},
     ]}},
     {"if": {"cond": {"equals": [{"var": "当前选项"}, 3]}, "do": [
         {"broadcast": {"message": "音效说明"}},
     ]}}],
    # —— §77.4 键盘也能选：方向键移动 + 空格确认 ——
    [{"when_key_pressed": {"key": "right arrow"}},
     {"change_variable": {"var": "当前选项", "by": 1}},
     {"if": {"cond": {"greater_than": [{"var": "当前选项"}, {"var": "选项总数"}]}, "do": [
         {"set_variable": {"var": "当前选项", "value": 1}},
     ]}}],
    [{"when_key_pressed": {"key": "left arrow"}},
     {"change_variable": {"var": "当前选项", "by": -1}},
     {"if": {"cond": {"less_than": [{"var": "当前选项"}, 1]}, "do": [
         {"set_variable": {"var": "当前选项", "value": {"var": "选项总数"}}},
     ]}}],
    [{"when_key_pressed": {"key": "space"}},
     {"broadcast": {"message": "菜单点击"}}],
    # —— §77.5 分层菜单：打开主菜单 / 难度菜单 / 开始游戏 ——
    [{"when_receive": {"message": "打开主菜单"}},
     {"set_variable": {"var": "菜单层级", "value": 0}},
     {"set_variable": {"var": "当前选项", "value": 1}},
     {"broadcast": {"message": "音乐淡出"}}],
    [{"when_receive": {"message": "打开难度菜单"}},
     {"set_variable": {"var": "菜单层级", "value": 1}},
     {"set_variable": {"var": "当前选项", "value": 2}},
     {"broadcast": {"message": "音乐淡出"}}],
    [{"when_receive": {"message": "开始游戏"}},
     {"set_variable": {"var": "菜单层级", "value": 2}},
     {"broadcast": {"message": "播放追逐"}},
     {"broadcast": {"message": "角色登场"}}],
    # —— §79 受击反馈：顿帧 ——
    [{"when_receive": {"message": "受到攻击"}},
     {"set_variable": {"var": "顿帧", "value": 6}},
     {"broadcast": {"message": "顿帧开始"}}],
    # —— §81 节奏判定：Perfect / Good / Miss ——
    [{"when_receive": {"message": "判定请求"}},
     {"set_variable": {"var": "判定误差", "value": 0.12}},
     {"if": {"cond": {"less_than": [{"var": "判定误差"}, 0.1]}, "do": [
         {"broadcast": {"message": "判定Perfect"}},
     ]}},
     {"if": {"cond": {"and": [
         {"greater_than": [{"var": "判定误差"}, 0.1]},
         {"less_than": [{"var": "判定误差"}, 0.25]},
     ]}, "do": [
         {"broadcast": {"message": "判定Good"}},
     ]}},
     {"if": {"cond": {"greater_than": [{"var": "判定误差"}, 0.25]}, "do": [
         {"broadcast": {"message": "判定Miss"}},
     ]}}],
    # —— §81.3 连击累计（全局变量才能跨角色累计）——
    [{"when_receive": {"message": "判定Perfect"}},
     {"change_variable": {"var": "连击", "by": 1}},
     {"if": {"cond": {"greater_than": [{"var": "连击"}, {"var": "最大连击"}]}, "do": [
         {"set_variable": {"var": "最大连击", "value": {"var": "连击"}}},
     ]}}],
    [{"when_receive": {"message": "判定Miss"}},
     {"set_variable": {"var": "连击", "value": 0}}],
    # —— §82 广播解耦示例：统一处理「敌人死亡」，订阅者各自响应 ——
    [{"when_receive": {"message": "敌人死亡"}},
     {"change_variable": {"var": "克隆计数", "by": -1}},
     {"broadcast": {"message": "分数增加"}}],
]

project = {
    "name": "手感与交互示例",
    "extensions": ["pen", "music"],
    "stage": {
        "backdrops": [{"name": "底", "asset": "assets/backdrop1.svg"}],
        "variables": {
            "当前BGM": 0,
            "目标音量": 0,
            "当前音量": 0,
            "菜单层级": 0,
            "当前选项": 1,
            "选项总数": 3,
            "已选难度": 1,
            "当前按钮序号": 0,
            "克隆计数": 0,
            "顿帧": 0,
            "判定误差": 999,
            "连击": 0,
            "最大连击": 0,
        },
        "lists": {
            "菜单选项": ["开始游戏", "难度设置", "音效说明"],
            "难度名称": ["简单", "普通", "困难"],
        },
        "scripts": stage_scripts,
    },
    "sprites": [
        彩带主角, 残影主角, 克隆监控, 音乐控制,
        按钮一, 按钮二, 按钮三,
        登场角色, 受击目标, 顿帧角色,
    ],
}

out = os.path.join(ROOT, "examples", "technique_probe9.yaml")
header = """# ══════════════════════════════════════════════════════════════════════
# technique_probe9 —— 第七册《游戏手感与交互》§75–§82 示教工程
#
#   §75 拖尾系统      —— 画笔拖尾（彩带主角）+ 克隆残影（带寿命与回收）
#   §76 背景音乐      —— BGM 状态机 + 淡入淡出 + 程序化旋律（音乐扩展）
#   §77 多角色选项菜单 —— 每个选项一个角色按钮（**不用「询问」积木**）
#   §78 克隆的正确用法 —— 三阶段生命周期 + 私有标志位 + 克隆预算计数
#   §79 受击反馈      —— 闪白 + 击退 + 顿帧
#   §80 演出与转场    —— 缓动滑入（divide 指数逼近）
#   §81 节奏输入判定  —— 时间窗 Perfect / Good / Miss
#   §82 广播解耦      —— 事件广播 + 全局变量中转
#
# ⚠️ 本文件由 scripts/gen_probe9.py 生成（用 yaml.dump 保证语法正确）。
# ══════════════════════════════════════════════════════════════════════
"""
body = yaml.dump({"project": project}, allow_unicode=True,
                  sort_keys=False, default_flow_style=False, width=200)
with open(out, "w", encoding="utf-8") as f:
    f.write(header + body)
print("写入 %s" % out)
