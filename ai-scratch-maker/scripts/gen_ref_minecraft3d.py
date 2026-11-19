#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 examples/ref_minecraft3d.yaml —— 完整可玩的第一人称体素光线投射参考工程。

灵感来源（社区作品《Minecraft 3D》反编译）：
  · TestRay        —— DDA 射线：x/y 按 Delta 步进累加距离，命中体素
  · TestCollision  —— 贴墙碰撞（前进前先查目标格是否空）
  · NorthEast      —— 画笔列渲染：motion_sety + penDown + change_y 画墙体竖条
操作：WASD / 方向键 移动与转向；空格 挖掉正前方方块；B 在命中处放置方块。
headless 可构建 + 四层校验 + 冒烟；首射线距离 / 碰撞测试 / 测试后px 用于运行时自检。
"""
import yaml

# ---------------- 基础表达式 ----------------
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
def mathop(op, n): return {"mathop": {"op": op, "num": n}}
def item(lst, idx): return {"item_of_list": {"index": idx, "list": lst}}
def cos_d(d): return mathop("cos", d)
def sin_d(d): return mathop("sin", d)
def floor_e(e): return mathop("floor", e)
def abs_e(e): return mathop("abs", e)
def key(k): return {"key_pressed": {"key": k}}

# ---------------- 语句 DSL（保证括号平衡） ----------------
def I(cond, do, els=None):
    p = {"cond": cond, "do": do}
    if els is not None:
        p["else"] = els
    return {"if": p}
def R(times, do): return {"repeat": {"times": times, "do": do}}
def F(do): return {"forever": {"do": do}}
def SV(v, val): return {"set_variable": {"var": v, "value": val}}
def CV(v, val): return {"change_variable": {"var": v, "value": val}}
def PC(name, *args): return {"call": {"proc": name, "args": list(args)}}
def REPL(lst, idx, it): return {"replace_item_of_list": {"index": idx, "list": lst, "item": it}}

# ---------------- 迷宫 16x16 ----------------
W = H = 16
grid = []
for y in range(H):
    for x in range(W):
        if x == 0 or y == 0 or x == W - 1 or y == H - 1:
            grid.append(1)            # 外墙
        elif x % 2 == 0 and y % 2 == 0:
            grid.append(1)            # 内部柱子（留出开阔走廊）
        else:
            grid.append(0)            # 空气

# ---------------- 查格(格X,格Y) -> 格值 ----------------
查格 = {
    "name": "查格 %n %n",
    "args": ["格X", "格Y"],
    "warp": True,
    "script": [
        I(Or(lt(V("格X"), 0), Or(gt(V("格X"), W - 1), Or(lt(V("格Y"), 0), gt(V("格Y"), H - 1)))),
          [SV("格值", 1)]),
        I(And(gt(V("格X"), -1), And(lt(V("格X"), W), And(gt(V("格Y"), -1), lt(V("格Y"), H)))),
          [SV("格值", item("地图", add(add(mul(V("格Y"), W), V("格X")), 1)))]),
    ],
}

# ---------------- 投射射线(角度) -> 命中距离 / 命中格X / 命中格Y ----------------
投射射线 = {
    "name": "投射射线 %n",
    "args": ["角度"],
    "warp": True,
    "script": [
        SV("射线X", cos_d(V("角度"))),
        SV("射线Y", sin_d(V("角度"))),
        SV("地图X", floor_e(V("px"))),
        SV("地图Y", floor_e(V("py"))),
        # deltaDist 防除零
        SV("绝X", abs_e(V("射线X"))),
        SV("ddx", 1000000),
        I(gt(V("绝X"), 0.0001), [SV("ddx", abs_e(div(N(1), V("射线X"))))]),
        SV("绝Y", abs_e(V("射线Y"))),
        SV("ddy", 1000000),
        I(gt(V("绝Y"), 0.0001), [SV("ddy", abs_e(div(N(1), V("射线Y"))))]),
        # step / sideDist
        SV("步X", 1),
        I(lt(V("射线X"), 0), [SV("步X", -1)]),
        SV("边距X", mul(sub(add(V("地图X"), 1), V("px")), V("ddx"))),
        I(lt(V("射线X"), 0), [SV("边距X", mul(sub(V("px"), V("地图X")), V("ddx")))]),
        SV("步Y", 1),
        I(lt(V("射线Y"), 0), [SV("步Y", -1)]),
        SV("边距Y", mul(sub(add(V("地图Y"), 1), V("py")), V("ddy"))),
        I(lt(V("射线Y"), 0), [SV("边距Y", mul(sub(V("py"), V("地图Y")), V("ddy")))]),
        # DDA 主循环
        SV("命中", 0),
        SV("面", 0),
        R(32, [
            I(eq(V("命中"), 0), [
                I(lt(V("边距X"), V("边距Y")),
                  [CV("边距X", V("ddx")), CV("地图X", V("步X")), SV("面", 0)],
                  [CV("边距Y", V("ddy")), CV("地图Y", V("步Y")), SV("面", 1)]),
                PC("查格 %n %n", V("地图X"), V("地图Y")),
                I(eq(V("格值"), 1), [SV("命中", 1)]),
            ]),
        ]),
        # 垂直距离消鱼眼
        SV("命中距离", sub(V("边距X"), V("ddx"))),
        I(eq(V("面"), 1), [SV("命中距离", sub(V("边距Y"), V("ddy")))]),
        I(lt(V("命中距离"), 0.0001), [SV("命中距离", 0.0001)]),
        SV("命中格X", V("地图X")),
        SV("命中格Y", V("地图Y")),
    ],
}

# ---------------- 渲染（画笔列） ----------------
渲染 = {
    "name": "渲染",
    "args": [],
    "warp": True,
    "script": [
        {"pen_up": None},
        {"pen_clear": None},
        SV("列号", 0),
        R(48, [
            CV("列号", 1),
            SV("相机X", sub(mul(div(V("列号"), 48), 2), 1)),
            SV("射线角", add(V("dir"), mul(V("相机X"), 30))),
            PC("投射射线 %n", V("射线角")),
            SV("墙高", div(160, V("命中距离"))),
            SV("顶Y", mul(V("墙高"), 0.5)),
            SV("底Y", mul(V("墙高"), -0.5)),
            SV("屏X", add(-240, mul(V("列号"), 10))),
            SV("g", 30),
            SV("暗", sub(220, mul(V("命中距离"), 12))),
            I(gt(V("暗"), 30), [SV("g", V("暗"))]),
            SV("色", add(add(mul(V("g"), 65536), mul(V("g"), 256)), V("g"))),
            {"set_pen_color": {"COLOR": V("色")}},
            {"pen_up": None},
            {"set_x": {"x": V("屏X")}},
            {"set_y": {"y": V("顶Y")}},
            {"pen_down": None},
            {"set_y": {"y": V("底Y")}},
            {"pen_up": None},
        ]),
    ],
}

# ---------------- 玩家动作 ----------------
def 前进():
    return [
        SV("新x", add(V("px"), mul(cos_d(V("dir")), 0.2))),
        SV("新y", add(V("py"), mul(sin_d(V("dir")), 0.2))),
        PC("查格 %n %n", floor_e(V("新x")), floor_e(V("新y"))),
        I(eq(V("格值"), 0), [SV("px", V("新x")), SV("py", V("新y"))]),
    ]

def 后退():
    return [
        SV("新x", sub(V("px"), mul(cos_d(V("dir")), 0.2))),
        SV("新y", sub(V("py"), mul(sin_d(V("dir")), 0.2))),
        PC("查格 %n %n", floor_e(V("新x")), floor_e(V("新y"))),
        I(eq(V("格值"), 0), [SV("px", V("新x")), SV("py", V("新y"))]),
    ]

def 挖():
    return [
        PC("投射射线 %n", V("dir")),
        I(eq(V("格值"), 1), [REPL("地图", add(add(mul(V("命中格Y"), W), V("命中格X")), 1), 0)]),
    ]

def 放():
    return [
        PC("投射射线 %n", V("dir")),
        REPL("地图", add(add(mul(V("命中格Y"), W), V("命中格X")), 1), 1),
    ]

玩家脚本 = [
    [
        {"when_receive": {"message": "开始"}},
        {"hide": None},
        # ---- 运行时自检（不影响游戏，仅验证光追 / 碰撞 / 移动逻辑） ----
        PC("投射射线 %n", V("dir")),
        SV("首射线距离", V("命中距离")),
        SV("存档px", V("px")),
        SV("存档py", V("py")),
        SV("新x", add(V("px"), mul(cos_d(V("dir")), 0.2))),
        PC("查格 %n %n", floor_e(V("新x")), floor_e(V("py"))),
        I(eq(V("格值"), 0), [SV("px", V("新x"))]),
        SV("测试后px", V("px")),
        SV("px", V("存档px")),
        SV("py", V("存档py")),
        PC("查格 %n %n", 0, 1),
        SV("碰撞测试", V("格值")),
        # ---- 主循环 ----
        F([
            I(Or(key("up"), key("w")), 前进()),
            I(Or(key("down"), key("s")), 后退()),
            I(Or(key("left"), key("a")), [CV("dir", -4)]),
            I(Or(key("right"), key("d")), [CV("dir", 4)]),
            I(key("space"), 挖()),
            I(key("b"), 放()),
            PC("渲染"),
        ]),
    ],
]

# ---------------- 舞台 ----------------
stage = {
    "name": "舞台",
    "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
    "variables": {
        "地图宽": W, "地图高": H,
        "px": 1.5, "py": 1.5, "dir": 0,
        "首射线距离": 0, "碰撞测试": 0, "测试后px": 0,
        "命中距离": 0, "命中格X": 0, "命中格Y": 0, "格值": 0,
        "存档px": 0, "存档py": 0,
        "地图X": 0, "地图Y": 0, "射线X": 0, "射线Y": 0, "绝X": 0, "绝Y": 0,
        "ddx": 0, "ddy": 0, "步X": 0, "步Y": 0, "边距X": 0, "边距Y": 0,
        "命中": 0, "面": 0, "新x": 0, "新y": 0,
        "列号": 0, "相机X": 0, "射线角": 0, "墙高": 0, "顶Y": 0, "底Y": 0,
        "屏X": 0, "g": 0, "暗": 0, "色": 0,
    },
    "lists": {"地图": grid},
    "broadcasts": {"开始": "开始"},
    "scripts": [
        [
            {"when_green_flag_clicked": None},
            {"pen_clear": None},
            SV("px", 1.5),
            SV("py", 1.5),
            SV("dir", 0),
            {"broadcast": {"message": "开始"}},
        ],
    ],
}

player = {
    "name": "玩家",
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "procedures": [查格, 投射射线, 渲染],
    "scripts": 玩家脚本,
}

project = {
    "project": {
        "name": "第一人称体素光线投射参考工程",
        "extensions": ["pen"],
        "stage": stage,
        "sprites": [player],
    }
}

out = "examples/ref_minecraft3d.yaml"
with open(out, "w", encoding="utf-8") as f:
    yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False)
print("wrote", out, "| grid cells =", len(grid))
