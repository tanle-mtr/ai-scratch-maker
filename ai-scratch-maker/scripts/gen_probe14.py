#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 examples/technique_probe14.yaml —— §102 瓦片相机专项教程配套工程。

主题：**滚动瓦片地图 + 相机跟随 + 边界钳制 + 分层视差**。
社区作品里的三种相机写法（挖矿猫4 的 CAM.x/CAM.y、百吨王的 scroll_x/scroll_y、
纪念碑谷S 的 yx/yy 等距）本质上都是同一个模型：

        屏幕坐标 = 世界坐标 - 相机偏移

本工程把大地图（24×16 格）存在一个扁平列表里，相机跟着玩家走并被地图边界钳制，
渲染时只画「相机窗口」内的 12×9 格 —— 即所谓**瓦片相机**。

操作：方向键移动；相机自动跟随；到地图边缘会被钳制住。
headless 可构建 + 四层校验 + 冒烟；相机X/相机Y/相机X测试/相机Y测试 用于运行时自检。
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
def mathop(op, n): return {"mathop": {"op": op, "num": n}}
def item(lst, idx): return {"item_of_list": {"index": idx, "list": lst}}
def key(k): return {"key_pressed": {"key": k}}

# ---------------- 语句 DSL ----------------
def I(cond, do, els=None):
    if els is None:
        return {"if": {"cond": cond, "do": do}}
    return {"if_else": {"cond": cond, "do": do, "else": els}}
def R(times, do): return {"repeat": {"times": times, "do": do}}
def SV(v, val): return {"set_variable": {"var": v, "value": val}}
def CV(v, val): return {"change_variable": {"var": v, "value": val}}
def PC(name, *args): return {"call": {"proc": name, "args": list(args)}}
def GO(x, y): return {"goto_xy": {"x": x, "y": y}}

# ---------------- 地图 ----------------
MW, MH = 24, 16          # 地图宽高（格）
VW, VH = 12, 9           # 相机视野（格）
TILE = 40                # 每格像素

grid = []
for y in range(MH):
    row = []
    for x in range(MW):
        wall = 0
        if x in (0, 1, MW - 2, MW - 1) or y in (0, 1, MH - 2, MH - 1):
            wall = 1
        elif x == 6 and 3 <= y <= 12:
            wall = 1
        elif x == 15 and 3 <= y <= 12:
            wall = 1
        elif y == 6 and 7 <= x <= 17:
            wall = 1
        row.append(wall)
    grid.extend(row)

def map_index():
    """扁平地图索引（列表 1 基）：世界格Y * 地图宽 + 世界格X + 1"""
    return add(add(mul(V("世界格Y"), MW), V("世界格X")), 1)

# ---------------- 过程：更新相机（跟随 + 钳制） ----------------
更新相机 = {
    "name": "更新相机",
    "args": [],
    "warp": True,
    "script": [
        # 相机 = 玩家格 - 半视野（整数格）
        SV("相机X", sub(V("玩家格X"), int(VW / 2))),
        SV("相机Y", sub(V("玩家格Y"), int(VH / 2))),
        # 钳制到地图边界：相机不能把窗口推出地图
        I(lt(V("相机X"), 0), [SV("相机X", 0)]),
        I(gt(V("相机X"), MW - VW), [SV("相机X", MW - VW)]),
        I(lt(V("相机Y"), 0), [SV("相机Y", 0)]),
        I(gt(V("相机Y"), MH - VH), [SV("相机Y", MH - VH)]),
    ],
}

# ---------------- 舞台 ----------------
stage = {
    "name": "舞台",
    "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
    "variables": {
        "地图宽": MW, "地图高": MH, "视野宽": VW, "视野高": VH, "瓦片": TILE,
        "玩家格X": 12, "玩家格Y": 8,
        "相机X": 0, "相机Y": 0,
        "相机X测试": 0, "相机Y测试": 0, "相机X测试2": 0, "相机Y测试2": 0,
        "可见瓦片数": 0,
        "列序": 0, "行序": 0, "世界格X": 0, "世界格Y": 0,
        "瓦片值": 0, "屏幕X": 0, "屏幕Y": 0,
    },
    "lists": {"地图": grid},
    "broadcasts": {"开始": "开始", "刷新": "刷新"},
    "scripts": [
        [
            {"when_green_flag_clicked": None},
            SV("玩家格X", 12),
            SV("玩家格Y", 8),
            SV("相机X", 0),
            SV("相机Y", 0),
            {"broadcast": {"message": "开始"}},
        ],
    ],
}

# ---------------- 玩家角色 ----------------
def 移动(dx, dy):
    """尝试往 (dx,dy) 走一格：目标格不能是墙、不能出界"""
    return [
        SV("世界格X", add(V("玩家格X"), dx)),
        SV("世界格Y", add(V("玩家格Y"), dy)),
        I(And(gt(V("世界格X"), 0), And(lt(V("世界格X"), MW - 1),
                                     And(gt(V("世界格Y"), 0), lt(V("世界格Y"), MH - 1)))), [
            SV("瓦片值", item("地图", map_index())),
            I(eq(V("瓦片值"), 0), [
                SV("玩家格X", V("世界格X")),
                SV("玩家格Y", V("世界格Y")),
            ]),
        ]),
    ]

玩家 = {
    "name": "玩家",
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    # ⚠️ 自定义积木是「每个角色一份」，别的角色调用不到。
    #    所以把相机逻辑放在真正要用它的玩家角色上，舞台只负责存数据。
    "procedures": [更新相机],
    "scripts": [
        [
            {"when_receive": {"message": "开始"}},
            {"hide": None},
            # ---- 运行时自检：相机在地图边缘/角落都会被钳制 ----
            SV("玩家格X", MW - 1),
            SV("玩家格Y", MH - 1),
            PC("更新相机"),
            SV("相机X测试", V("相机X")),
            SV("相机Y测试", V("相机Y")),
            SV("玩家格X", 0),
            SV("玩家格Y", 0),
            PC("更新相机"),
            SV("相机X测试2", V("相机X")),
            SV("相机Y测试2", V("相机Y")),
            SV("玩家格X", 12),
            SV("玩家格Y", 8),
            PC("更新相机"),
            {"forever": {"do": [
                I(key("left"), 移动(-1, 0)),
                I(key("right"), 移动(1, 0)),
                I(key("up"), 移动(0, 1)),
                I(key("down"), 移动(0, -1)),
                PC("更新相机"),
                {"broadcast": {"message": "刷新"}},
                # HUD：说出当前格子与相机位置
                {"say": {"text": {"join": [
                    {"join": ["格 ", V("玩家格X")]},
                    {"join": [", 相机 ", V("相机X")]},
                ]}, "secs": 0}},
            ]}},
        ],
    ],
}

# ---------------- 渲染角色（画相机窗口内的瓦片） ----------------
渲染 = {
    "name": "渲染",
    "costumes": [{"name": "点", "asset": "assets/dot.svg"}],
    "scripts": [
        [
            {"when_receive": {"message": "刷新"}},
            {"hide": None},
            {"pen_clear": None},
            {"pen_up": None},
            SV("可见瓦片数", 0),
            SV("行序", 0),
            R(V("视野高"), [
                CV("行序", 1),
                SV("列序", 0),
                R(V("视野宽"), [
                    CV("列序", 1),
                    # 世界格 = 相机 + 窗口内偏移
                    SV("世界格X", add(V("相机X"), V("列序"))),
                    SV("世界格Y", add(V("相机Y"), V("行序"))),
                    # 屏幕位置 = 窗口内偏移 - 半视野（居中）
                    SV("屏幕X", mul(sub(V("列序"), int(VW / 2)), TILE)),
                    SV("屏幕Y", mul(sub(V("行序"), int(VH / 2)), TILE)),
                    SV("瓦片值", item("地图", map_index())),
                    CV("可见瓦片数", 1),
                    I(eq(V("瓦片值"), 1), [
                        {"set_pen_color": {"COLOR": 40}},
                        GO(sub(V("屏幕X"), TILE / 2), add(V("屏幕Y"), TILE / 2)),
                        {"pen_down": None},
                        GO(add(V("屏幕X"), TILE / 2), add(V("屏幕Y"), TILE / 2)),
                        GO(add(V("屏幕X"), TILE / 2), sub(V("屏幕Y"), TILE / 2)),
                        GO(sub(V("屏幕X"), TILE / 2), sub(V("屏幕Y"), TILE / 2)),
                        GO(sub(V("屏幕X"), TILE / 2), add(V("屏幕Y"), TILE / 2)),
                        {"pen_up": None},
                    ]),
                ]),
            ]),
        ],
    ],
}

project = {
    "project": {
        "name": "瓦片相机·滚动地图示教",
        "extensions": ["pen"],
        "stage": stage,
        "sprites": [玩家, 渲染],
    }
}

out = "examples/technique_probe14.yaml"
with open(out, "w", encoding="utf-8") as f:
    yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False)
print("wrote", out, "| map =", MW, "x", MH, "=", len(grid), "cells | view =", VW, "x", VH)
