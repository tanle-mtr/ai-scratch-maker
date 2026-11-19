#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 examples/technique_probe13.yaml —— §99 阴影光追专项教程配套工程。

主题：**可见性多边形（Visibility Polygon）+ 线段求交阴影**。
比第九册 §99 的「最近角遮挡」更严格、更通用：

  1. 墙角方向 D = normalize(墙角 - 玩家)；对它做 ±ε 旋转，各投一条射线，
     取三条射线命中距离的最小值 → 该墙角方向的可见距离（这是经典可见性多边形算法）；
  2. 所有墙角的可见点依次相连 = 玩家真正能看见的区域；
  3. 实体判定：朝实体投一条射线，若命中墙的距离 < 实体距离 → 实体在阴影里。

射线与线段求交用叉积（不需要开方、不需要 atan2、也不需要角度）：
  denom = cross(D, E)
  t     = cross(A-O, E) / denom      （沿射线方向的命中距离）
  u     = cross(A-O, D) / denom      （命中点在线段上的比例，0<=u<=1）
⚠️ Scratch 3 **没有 atan2 积木**（也没有 sin/cos 面板积木），
   本工程全程用向量 + 叉积，绕开角度，彻底避开这类坑。
headless 可构建 + 四层校验 + 冒烟；实体1/2/3在阴影 用于运行时自检。
"""
import yaml

# ---------------- 表达式 ----------------
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
def Or(a, b): return {"or": [a, b]}
def Not(a): return {"not": {"operand": a}}
def mathop(op, n): return {"mathop": {"op": op, "num": n}}
def item(lst, idx): return {"item_of_list": {"index": idx, "list": lst}}
def cos_d(d): return mathop("cos", d)
def sin_d(d): return mathop("sin", d)
def abs_e(e): return mathop("abs", e)
def sqrt_e(e): return mathop("sqrt", e)

# ---------------- 语句 DSL ----------------
def I(cond, do, els=None):
    # ⚠️ 带 else 分支时必须用 if_else（control_if_else）——
    #    control_if 没有 SUBSTACK2 槽位，写成 if 会把 else 分支**静默丢弃**。
    if els is None:
        return {"if": {"cond": cond, "do": do}}
    return {"if_else": {"cond": cond, "do": do, "else": els}}
def R(times, do): return {"repeat": {"times": times, "do": do}}
def SV(v, val): return {"set_variable": {"var": v, "value": val}}
def CV(v, val): return {"change_variable": {"var": v, "value": val}}
def PC(name, *args): return {"call": {"proc": name, "args": list(args)}}
def REPL(lst, idx, it): return {"replace_item_of_list": {"index": idx, "list": lst, "item": it}}
def GO(x, y): return {"goto_xy": {"x": x, "y": y}}

# ---------------- 场景数据 ----------------
WALLS = [
    (100, -60, 100, 60),      # 右侧竖墙
    (-100, -60, -100, 60),    # 左侧竖墙
    (-40, 140, 40, 140),      # 上方横墙
]
# 墙角（可见性多边形候选顶点，按角度逆时针排好）
CORNERS = [
    (-100, -60), (100, -60), (100, 60), (-40, 140), (40, 140), (-100, 60),
]
# 实体：前两个被墙挡住，第三个在空隙里（应判定为可见）
ENTITIES = [(170, 0), (0, 200), (150, 170)]
EPS = 0.5   # 角度扰动（度）

# ---------------- 过程：投射方向(方向X,方向Y) -> 最近距离 ----------------
投射方向 = {
    "name": "投射方向 %n %n",
    "args": ["方向X", "方向Y"],
    "warp": True,
    "script": [
        SV("最近距离", V("最大距离")),
        # ⚠️ 过程内部用**独立**的循环变量：复用外层的「序号」会把它冲掉，
        #    导致调用方的循环索引错乱（Scratch 里过程共享全局变量）。
        SV("墙序号", 1),
        R(V("墙数"), [
            SV("AX", item("墙AX", V("墙序号"))),
            SV("AY", item("墙AY", V("墙序号"))),
            SV("BX", item("墙BX", V("墙序号"))),
            SV("BY", item("墙BY", V("墙序号"))),
            SV("EX", sub(V("BX"), V("AX"))),
            SV("EY", sub(V("BY"), V("AY"))),
            # denom = cross(D, E) = Dx*Ey - Dy*Ex
            SV("分母", sub(mul(V("方向X"), V("EY")), mul(V("方向Y"), V("EX")))),
            I(gt(abs_e(V("分母")), 0.0001), [
                SV("AOx", sub(V("AX"), V("玩家X"))),
                SV("AOy", sub(V("AY"), V("玩家Y"))),
                # t = cross(A-O, E) / denom —— 沿射线距离（D 是单位向量）
                SV("t", div(sub(mul(V("AOx"), V("EY")), mul(V("AOy"), V("EX"))), V("分母"))),
                # u = cross(A-O, D) / denom —— 命中点在线段上的比例
                SV("u", div(sub(mul(V("AOx"), V("方向Y")), mul(V("AOy"), V("方向X"))), V("分母"))),
                # Scratch 3 没有 >= / <=，用 not 表达 0 <= u <= 1
                I(And(gt(V("t"), 0), And(Not(lt(V("u"), 0)), Not(gt(V("u"), 1)))), [
                    I(lt(V("t"), V("最近距离")), [SV("最近距离", V("t"))]),
                ]),
            ]),
            CV("墙序号", 1),
        ]),
    ],
}

# ---------------- 过程：算顶点(点X,点Y) -> 可见点X / 可见点Y ----------------
算顶点 = {
    "name": "算顶点 %n %n",
    "args": ["点X", "点Y"],
    "warp": True,
    "script": [
        SV("dx", sub(V("点X"), V("玩家X"))),
        SV("dy", sub(V("点Y"), V("玩家Y"))),
        SV("len", sqrt_e(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy"))))),
        SV("ux", div(V("dx"), V("len"))),
        SV("uy", div(V("dy"), V("len"))),
        # 旋转矩阵常数：c = cos(ε)，s = sin(ε)
        SV("c", mathop("cos", EPS)),
        SV("s", mathop("sin", EPS)),
        # 方向 -ε：rx = ux*c + uy*s , ry = -ux*s + uy*c
        SV("rx", add(mul(V("ux"), V("c")), mul(V("uy"), V("s")))),
        SV("ry", add(mul(V("uy"), V("c")), mul(mul(V("ux"), V("s")), -1))),
        PC("投射方向 %n %n", V("rx"), V("ry")),
        SV("d1", V("最近距离")),
        # 方向 0
        PC("投射方向 %n %n", V("ux"), V("uy")),
        SV("d2", V("最近距离")),
        # 方向 +ε：rx = ux*c - uy*s , ry = ux*s + uy*c
        SV("rx2", sub(mul(V("ux"), V("c")), mul(V("uy"), V("s")))),
        SV("ry2", add(mul(V("ux"), V("s")), mul(V("uy"), V("c")))),
        PC("投射方向 %n %n", V("rx2"), V("ry2")),
        SV("d3", V("最近距离")),
        SV("dmin", V("d1")),
        I(lt(V("d2"), V("dmin")), [SV("dmin", V("d2"))]),
        I(lt(V("d3"), V("dmin")), [SV("dmin", V("d3"))]),
        SV("可见点X", add(V("玩家X"), mul(V("ux"), V("dmin")))),
        SV("可见点Y", add(V("玩家Y"), mul(V("uy"), V("dmin")))),
    ],
}

# ---------------- 过程：实体判定(实体X,实体Y) -> 实体在阴影 ----------------
实体判定 = {
    "name": "实体判定 %n %n",
    "args": ["实体X", "实体Y"],
    "warp": True,
    "script": [
        SV("dx", sub(V("实体X"), V("玩家X"))),
        SV("dy", sub(V("实体Y"), V("玩家Y"))),
        SV("实体距", sqrt_e(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy"))))),
        SV("ux", div(V("dx"), V("实体距"))),
        SV("uy", div(V("dy"), V("实体距"))),
        PC("投射方向 %n %n", V("ux"), V("uy")),
        I(lt(V("最近距离"), V("实体距")), [SV("实体在阴影", 1)], [SV("实体在阴影", 0)]),
    ],
}

# ---------------- 主脚本 ----------------
主脚本 = [
    {"pen_clear": None},
    # 1) 计算所有墙角的可见点
    SV("序号", 1),
    R(V("点数"), [
        PC("算顶点 %n %n", item("角点X", V("序号")), item("角点Y", V("序号"))),
        REPL("顶点X", V("序号"), V("可见点X")),
        REPL("顶点Y", V("序号"), V("可见点Y")),
        CV("序号", 1),
    ]),
    # 2) 画可见性多边形（玩家 -> 顶点1 -> ... -> 顶点N -> 玩家）
    {"set_pen_color": {"COLOR": 120}},
    GO(V("玩家X"), V("玩家Y")),
    {"pen_down": None},
    SV("序号", 1),
    R(V("点数"), [
        GO(item("顶点X", V("序号")), item("顶点Y", V("序号"))),
        CV("序号", 1),
    ]),
    GO(V("玩家X"), V("玩家Y")),
    {"pen_up": None},
    # 3) 画墙
    {"set_pen_color": {"COLOR": 0}},
    SV("序号", 1),
    R(V("墙数"), [
        GO(item("墙AX", V("序号")), item("墙AY", V("序号"))),
        {"pen_down": None},
        GO(item("墙BX", V("序号")), item("墙BY", V("序号"))),
        {"pen_up": None},
        CV("序号", 1),
    ]),
    # 4) 实体阴影判定
    PC("实体判定 %n %n", N(ENTITIES[0][0]), N(ENTITIES[0][1])),
    SV("实体1在阴影", V("实体在阴影")),
    PC("实体判定 %n %n", N(ENTITIES[1][0]), N(ENTITIES[1][1])),
    SV("实体2在阴影", V("实体在阴影")),
    PC("实体判定 %n %n", N(ENTITIES[2][0]), N(ENTITIES[2][1])),
    SV("实体3在阴影", V("实体在阴影")),
    # 5) 画三个实体（阴影=红，可见=绿）
    SV("序号", 1),
    R(3, [
        I(eq(V("序号"), 1), [
            SV("实体X", N(ENTITIES[0][0])), SV("实体Y", N(ENTITIES[0][1])),
            SV("阴影标记", V("实体1在阴影")),
        ]),
        I(eq(V("序号"), 2), [
            SV("实体X", N(ENTITIES[1][0])), SV("实体Y", N(ENTITIES[1][1])),
            SV("阴影标记", V("实体2在阴影")),
        ]),
        I(eq(V("序号"), 3), [
            SV("实体X", N(ENTITIES[2][0])), SV("实体Y", N(ENTITIES[2][1])),
            SV("阴影标记", V("实体3在阴影")),
        ]),
        I(eq(V("阴影标记"), 1), [{"set_pen_color": {"COLOR": 0}}], [{"set_pen_color": {"COLOR": 100}}]),
        GO(V("实体X"), V("实体Y")),
        {"pen_down": None},
        GO(V("玩家X"), V("玩家Y")),
        {"pen_up": None},
        CV("序号", 1),
    ]),
]

# ---------------- 舞台 ----------------
stage = {
    "name": "舞台",
    "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
    "variables": {
        "玩家X": 0, "玩家Y": 0,
        "墙数": len(WALLS), "点数": len(CORNERS),
        "最大距离": 3000,
        "最近距离": 0, "序号": 1, "墙序号": 1,
        "AX": 0, "AY": 0, "BX": 0, "BY": 0, "EX": 0, "EY": 0,
        "AOx": 0, "AOy": 0, "分母": 0, "t": 0, "u": 0,
        "dx": 0, "dy": 0, "len": 0, "ux": 0, "uy": 0,
        "rx": 0, "ry": 0, "rx2": 0, "ry2": 0, "c": 1, "s": 0,
        "d1": 0, "d2": 0, "d3": 0, "dmin": 0,
        "可见点X": 0, "可见点Y": 0,
        "实体X": 0, "实体Y": 0, "实体距": 0, "实体在阴影": 0,
        "实体1在阴影": 0, "实体2在阴影": 0, "实体3在阴影": 0,
        "阴影标记": 0,
    },
    "lists": {
        "墙AX": [w[0] for w in WALLS],
        "墙AY": [w[1] for w in WALLS],
        "墙BX": [w[2] for w in WALLS],
        "墙BY": [w[3] for w in WALLS],
        "角点X": [c[0] for c in CORNERS],
        "角点Y": [c[1] for c in CORNERS],
        "顶点X": [0] * len(CORNERS),
        "顶点Y": [0] * len(CORNERS),
    },
    "scripts": [
        [
            {"when_green_flag_clicked": None},
            {"pen_clear": None},
            SV("玩家X", 0),
            SV("玩家Y", 0),
            {"broadcast": {"message": "开始"}},
        ],
    ],
}

光追 = {
    "name": "光追",
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "procedures": [投射方向, 算顶点, 实体判定],
    "scripts": [
        [
            {"when_receive": {"message": "开始"}},
            {"hide": None},
        ] + 主脚本,
    ],
}

project = {
    "project": {
        "name": "阴影光追·可见性多边形示教",
        "extensions": ["pen"],
        "stage": stage,
        "sprites": [光追],
    }
}

out = "examples/technique_probe13.yaml"
with open(out, "w", encoding="utf-8") as f:
    yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False)
print("wrote", out, "| walls =", len(WALLS), "| corners =", len(CORNERS), "| entities =", len(ENTITIES))
