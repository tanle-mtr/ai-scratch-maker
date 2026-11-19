#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 examples/technique_probe11.yaml —— 第九册示教工程。
覆盖：§93 数据驱动开关阵列 / §96 平台跳跃物理 / §99 视野盲区阴影光追 / §100 加载圈。
全部用官方兼容积木，headless 可构建+校验+冒烟。
"""
import yaml, os

def V(n): return {"var": n}
def N(x): return x
def sub(a, b): return {"subtract": [a, b]}
def add(a, b): return {"add": [a, b]}
def mul(a, b): return {"multiply": [a, b]}
def div(a, b): return {"divide": [a, b]}
def eq(a, b): return {"equals": [a, b]}
def lt(a, b): return {"less_than": [a, b]}
def gt(a, b): return {"greater_than": [a, b]}
def And(a, b): return {"and": [a, b]}
def Not(a): return {"not": {"operand": a}}
def item(lst, idx): return {"item_of_list": {"index": idx, "list": lst}}
def len_(lst): return {"length_of_list": {"list": lst}}
def mathop(op, n): return {"mathop": {"op": op, "num": n}}
def dist2(ax, ay, bx, by):
    return add(mul(sub(ax, bx), sub(ax, bx)), mul(sub(ay, by), sub(ay, by)))


# ---------------- 自定义积木：算角度 %n %n -> 角度 ----------------
# ⚠️ Scratch 3 **没有 atan2 积木**（scratch-vm 只实现 add/sub/mul/div/比较/逻辑/
#    join/letter/length/contains/mod/round/mathop），写 atan2 会静默返回 0。
#    mathop 的 atan（有）返回「度」，用下面的分支拼出 atan2：
#       x>0            -> atan(y/x)
#       x<0, y>=0      -> atan(y/x) + 180
#       x<0, y<0       -> atan(y/x) - 180
#       x=0, y>0       -> 90 ；x=0, y<0 -> -90 ；x=0, y=0 -> 0
算角度 = {
    "name": "算角度 %n %n",
    "args": ["入Y", "入X"],
    "warp": True,
    "script": [
        {"if": {"cond": gt(V("入X"), 0), "do": [
            {"set_variable": {"var": "角度", "value": mathop("atan", div(V("入Y"), V("入X")))}},
        ]}},
        {"if": {"cond": lt(V("入X"), 0), "do": [
            {"set_variable": {"var": "角度", "value": mathop("atan", div(V("入Y"), V("入X")))}},
            {"if": {"cond": lt(V("入Y"), 0), "do": [
                {"set_variable": {"var": "角度", "value": sub(V("角度"), 180)}},
            ]}},
            {"if": {"cond": gt(V("入Y"), 0), "do": [
                {"set_variable": {"var": "角度", "value": add(V("角度"), 180)}},
            ]}},
            {"if": {"cond": eq(V("入Y"), 0), "do": [
                {"set_variable": {"var": "角度", "value": 180}},
            ]}},
        ]}},
        {"if": {"cond": eq(V("入X"), 0), "do": [
            {"if": {"cond": gt(V("入Y"), 0), "do": [
                {"set_variable": {"var": "角度", "value": 90}},
            ]}},
            {"if": {"cond": lt(V("入Y"), 0), "do": [
                {"set_variable": {"var": "角度", "value": -90}},
            ]}},
            {"if": {"cond": eq(V("入Y"), 0), "do": [
                {"set_variable": {"var": "角度", "value": 0}},
            ]}},
        ]}},
    ],
}

# ---------------- 舞台 ----------------
stage = {
    "name": "舞台",
    "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
    "variables": {
        "开关数量": 4, "ID计数器": 0, "目标ID": 2,
        "YVelocity": 0, "Gravity": 0.6, "地面Y": -120, "允许跳": 1,
        "序号": 1, "玩家X": 0, "玩家Y": 0,
        "实体X": 80, "实体Y": 30, "实体在阴影": 0,
        "最近角差": 999, "最近墙距": 999, "实体角": 0, "实体距": 0,
        "dX": 0, "dY": 0, "角差": 0, "墙距": 0, "阴影已算": 0,
        "画笔方向": 0, "角度": 0,
    },
    "lists": {
        "开关状态": [1, 0, 1, 0],
        "墙角X": [100, -100, 100, -100],
        "墙角Y": [100, 100, -100, -100],
        "与玩家夹角": [0, 0, 0, 0],
    },
    "broadcasts": {"切换": "切换"},
    "procedures": [算角度],
    "scripts": [
        # 1) 生成开关阵列（§93）
        [{"when_green_flag_clicked": None},
         {"set_variable": {"var": "ID计数器", "value": 0}},
         {"repeat": {"times": V("开关数量"), "do": [
             {"change_variable": {"var": "ID计数器", "value": 1}},
             {"create_clone_of": {"clone": "开关"}},
         ]}},
         # 2) 阴影光追（§99）一次性计算
         {"set_variable": {"var": "序号", "value": 1}},
         {"repeat": {"times": len_("墙角X"), "do": [
             {"set_variable": {"var": "dX", "value": sub(item("墙角X", V("序号")), V("玩家X"))}},
             {"set_variable": {"var": "dY", "value": sub(item("墙角Y", V("序号")), V("玩家Y"))}},
             # ⚠️ Scratch 3 没有 atan2 积木，用自定义积木「算角度」算（atan + 分支）
             {"call": {"proc": "算角度 %n %n", "args": [V("dY"), V("dX")]}},
             {"replace_item_of_list": {"index": V("序号"), "list": "与玩家夹角", "item": V("角度")}},
             {"change_variable": {"var": "序号", "value": 1}},
         ]}},
         {"call": {"proc": "算角度 %n %n", "args": [sub(V("实体Y"), V("玩家Y")), sub(V("实体X"), V("玩家X"))]}},
         {"set_variable": {"var": "实体角", "value": V("角度")}},
         {"set_variable": {"var": "实体距", "value": mathop("sqrt", dist2(V("实体X"), V("实体Y"), V("玩家X"), V("玩家Y")))}},
         {"set_variable": {"var": "序号", "value": 1}},
         {"set_variable": {"var": "最近角差", "value": 999}},
         {"set_variable": {"var": "最近墙距", "value": 999}},
         {"repeat": {"times": len_("墙角X"), "do": [
             {"set_variable": {"var": "角差", "value": mathop("abs", sub(V("实体角"), item("与玩家夹角", V("序号"))))}},
             # 角度环绕：170° 与 -170° 的实际夹角是 20°，不是 340°
             {"if": {"cond": gt(V("角差"), 180), "do": [
                 {"set_variable": {"var": "角差", "value": sub(360, V("角差"))}},
             ]}},
             {"set_variable": {"var": "墙距", "value": mathop("sqrt", dist2(item("墙角X", V("序号")), item("墙角Y", V("序号")), V("玩家X"), V("玩家Y")))}},
             {"if": {"cond": lt(V("角差"), V("最近角差")), "do": [
                 {"set_variable": {"var": "最近角差", "value": V("角差")}},
                 {"set_variable": {"var": "最近墙距", "value": V("墙距")}},
             ]}},
             {"change_variable": {"var": "序号", "value": 1}},
         ]}},
         # ⚠️ 带 else 必须用 if_else（control_if_else）；写成 if 会把 else 分支静默丢弃
         {"if_else": {"cond": lt(V("最近墙距"), V("实体距")),
                 "do": [{"set_variable": {"var": "实体在阴影", "value": 1}}],
                 "else": [{"set_variable": {"var": "实体在阴影", "value": 0}}]}},
         {"set_variable": {"var": "阴影已算", "value": 1}},
         # 3) 生成加载圈克隆（§100）
         {"repeat": {"times": 6, "do": [
             {"create_clone_of": {"clone": "加载"}},
             {"wait": {"secs": 0.13}},
         ]}},
        ],
        # 平台跳跃物理（§96）—— 放在舞台 forever 里驱动玩家（玩家是独立 sprite，变量全局可读）
        [{"when_green_flag_clicked": None},
         {"forever": {"do": [
             {"set_variable": {"var": "YVelocity", "value": sub(V("YVelocity"), V("Gravity"))}},
             {"change_variable": {"var": "玩家Y", "value": V("YVelocity")}},
             {"if": {"cond": lt(V("玩家Y"), V("地面Y")), "do": [
                 {"set_variable": {"var": "玩家Y", "value": V("地面Y")}},
                 {"set_variable": {"var": "YVelocity", "value": 0}},
                 {"set_variable": {"var": "允许跳", "value": 1}},
             ]}},
             {"if": {"cond": And(eq(V("允许跳"), 1), gt(V("玩家Y"), V("地面Y"))), "do": [
                 # 模拟一次起跳（headless 无键盘，用「离地即给初速」代替按键）
                 {"set_variable": {"var": "YVelocity", "value": 12}},
                 {"set_variable": {"var": "允许跳", "value": 0}},
             ]}},
         ]}}],
        # 切换广播：翻转 目标ID 对应的开关状态（§93）
        [{"when_receive": {"message": "切换"}},
         {"replace_item_of_list": {"index": V("目标ID"), "list": "开关状态",
                                  "item": sub(1, item("开关状态", V("目标ID")))}}],
    ],
}

# ---------------- 开关 sprite（§93）----------------
switch = {
    "name": "开关", "x": 0, "y": 100,
    "costumes": [{"name": "框", "asset": "assets/dot.svg"}],
    "variables": {"ID": 0},
    "scripts": [
        [{"when_green_flag_clicked": None}, {"hide": None}],
        [{"when_start_as_clone": None},
         {"set_variable": {"var": "ID", "value": V("ID计数器")}},
         {"show": None},
         {"if_else": {"cond": eq(item("开关状态", V("ID")), 1),
                 "do": [{"set_effect": {"effect": "COLOR", "value": 0}}],
                 "else": [{"set_effect": {"effect": "COLOR", "value": 100}}]}}],
        [{"when_receive": {"message": "切换"}},
         {"if": {"cond": eq(V("ID"), V("目标ID")), "do": [
             {"if_else": {"cond": eq(item("开关状态", V("ID")), 1),
                     "do": [{"set_effect": {"effect": "COLOR", "value": 100}}],
                     "else": [{"set_effect": {"effect": "COLOR", "value": 0}}]}},
         ]}}],
    ],
}

# ---------------- 玩家 sprite（§96 平台跳跃，动作承接舞台物理）----------------
player = {
    "name": "玩家", "x": 0, "y": 0,
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "scripts": [
        [{"when_green_flag_clicked": None},
         {"set_variable": {"var": "玩家Y", "value": 0}},
         {"set_variable": {"var": "YVelocity", "value": 0}},
         {"set_variable": {"var": "允许跳", "value": 1}},
         {"forever": {"do": [
             # 把全局物理算出的 玩家Y 同步到本 sprite 的 y（视觉），并限制在地面以上
             {"set_y": {"y": V("玩家Y")}},
         ]}}],
    ],
}

# ---------------- 加载 sprite（§100 克隆分段旋转描弧）----------------
loader = {
    "name": "加载", "x": 0, "y": -120,
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "variables": {"旋转": 25},
    "scripts": [
        [{"when_start_as_clone": None},
         {"show": None},
         {"pen_clear": None}, {"pen_down": None}, {"set_pen_size": {"size": 8}},
         {"repeat": {"times": 12, "do": [
             {"turn_right": {"degrees": V("旋转")}},
             {"move_steps": {"steps": 3}},
         ]}},
         {"pen_up": None},
         {"delete_this_clone": None}],
    ],
}

project = {
    "project": {
        "name": "第九册示教 probe11",
        "stage": stage,
        "sprites": [switch, player, loader],
    }
}

out = "examples/technique_probe11.yaml"
with open(out, "w", encoding="utf-8") as f:
    yaml.dump(project, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
print("wrote", out)
