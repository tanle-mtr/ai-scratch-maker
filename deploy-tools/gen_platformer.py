#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成平台跳跃示例 platformer.yaml（用 yaml.dump，避免手写 YAML 踩坑）。

设计要点见 references/platformer.md。关键决策：
- **帧循环用广播分发**（§156）：舞台是唯一时钟，`广播 帧` 驱动所有子系统，两条独立
  `forever` 会让物理跑双倍速。
- **碰撞一律用矩形数学，不用 `碰到`**（§158 + 铁律 4）：`touching` 只认角色，
  画在背景里的地形根本碰不到，而且无头环境测不到。
- **分轴解算**：先水平（撞墙回退）再垂直（落地/撞头），两轴各自独立回退。
- **输入抽象层**：按键 → `输入_左/右/跳` 三个变量，再由物理读变量。
  好处：行为校验可以不碰键盘直接驱动（scratch-vm 无头下按键注入不可靠），
  顺带天然支持改键/触屏/双人。
- 平台与金币数据全在舞台平行列表里（§157），地面用画笔按列表画（不占克隆体）。

用法: python gen_platformer.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "platformer.yaml")

# ------------------------------------------------------------------ 关卡数据
# (名字, 中心x, 中心y, 宽, 高)  —— 世界坐标，y+ 朝上
PLATFORMS = [
    ("地面", -60, -140, 700, 40),    # 顶面 y=-120
    ("矮墙", -20, -90, 40, 60),      # 可跳过：墙顶 -60
    ("平台2", 140, -40, 180, 30),    # 顶面 y=-25
    ("平台3", 380, 20, 160, 30),     # 顶面 y=35
]
COINS = [(-150, -80), (140, 20), (380, 130)]

STAGE_VARS = {
    # 世界坐标与速度
    "玩家x": -200, "玩家y": 40, "vx": 0, "vy": 0,
    "上帧y": 0,
    # 地面状态（土狼时间用）
    "在地面": 0, "离地计时": 9,
    # 输入抽象层
    "输入_左": 0, "输入_右": 0, "输入_跳": 0, "使用键盘": 1,
    # 帧循环开关（行为校验关掉它，自己发帧）
    "自动帧": 1,
    # 循环/尺寸
    "i": 0, "平台数": len(PLATFORMS), "金币总数": len(COINS),
    "玩家半宽": 14, "玩家半高": 18,
    "移动速度": 6, "重力": 1.2, "最大下落": 18, "跳跃力度": 16,
    # 镜头
    "镜头x": -260, "关卡左": -260, "关卡右": 640, "半屏宽": 160, "屏宽": 320,
    # 状态
    "得分": 0, "命数": 3, "金币数": 0, "允许操作": 1,
    "出生x": -200, "出生y": 40, "方向键": 0,
}

STAGE_LISTS = {
    "平台x": [p[1] for p in PLATFORMS],
    "平台y": [p[2] for p in PLATFORMS],
    "平台宽": [p[3] for p in PLATFORMS],
    "平台高": [p[4] for p in PLATFORMS],
    "金币x": [c[0] for c in COINS],
    "金币y": [c[1] for c in COINS],
    "金币活": [1] * len(COINS),
}

# 配色取自 references/ui-design-spec.md
COL_PLATFORM = "#3A8E7D"   # 蓝绿色系 = 主体
COL_COIN = "#FFCF4D"       # 黄色系 = 主操作/奖励
COL_PLAYER = "#FFEDB3"     # 浅黄


# ------------------------------------------------------------------ 条件片段
def AABB_overlap():
    """玩家与第 i 块平台的矩形重叠判定（用移动后的坐标！）。"""
    return AND(
        LT(ABS(SUB(V("玩家x"), ITEM("平台x", V("i")))),
           ADD(V("玩家半宽"), DIV(ITEM("平台宽", V("i")), 2))),
        LT(ABS(SUB(V("玩家y"), ITEM("平台y", V("i")))),
           ADD(V("玩家半高"), DIV(ITEM("平台高", V("i")), 2))),
    )


def coin_hit():
    """金币判定：用半径盒而不是 touching，无头可测。"""
    return ANDn(
        EQ(ITEM("金币活", V("i")), 1),
        LT(ABS(SUB(V("玩家x"), ITEM("金币x", V("i")))), 24),
        LT(ABS(SUB(V("玩家y"), ITEM("金币y", V("i")))), 28),
    )


# ------------------------------------------------------------------ 玩家脚本
def player_frame():
    """一帧的完整物理：输入 → 重力 → 水平分轴 → 垂直分轴 → 跳跃 → 金币 → 掉落 → 镜头 → 渲染。"""
    return [
        RECV("帧"),
        # 行为闸门（§165）：过场/暂停/死亡动画都能一句话冻结全部物理
        IF(EQ(V("允许操作"), 0), {"stop": {"option": "this script"}}),

        # ① 输入 → 水平速度
        SET("方向键", SUB(V("输入_右"), V("输入_左"))),
        SET("vx", MUL(V("方向键"), V("移动速度"))),

        # ② 重力（存正值，向上为正 → 每帧减）
        SET("vy", SUB(V("vy"), V("重力"))),
        IF(LT(V("vy"), SUB(0, V("最大下落"))), SET("vy", SUB(0, V("最大下落")))),
        SET("上帧y", V("玩家y")),

        # ③ 水平分轴：先假设移动成功，撞到就整段退回
        CHG("玩家x", V("vx")),
        *repv("i", V("平台数"),
              IF(AND(AABB_overlap(), NEQ(V("vx"), 0)),
                 SET("玩家x", SUB(V("玩家x"), V("vx"))))),

        # ④ 垂直分轴：落地 / 撞头 两个互斥分支（必须真 if/else，见 §145）
        SET("在地面", 0),
        CHG("玩家y", V("vy")),
        *repv("i", V("平台数"),
              IF(AND(AABB_overlap(), LE(V("vy"), 0)), [
                  # 三项相加必须嵌套（铁律 7：add 只有 2 个操作数）
                  SET("玩家y", ADD(ADD(ITEM("平台y", V("i")),
                                       DIV(ITEM("平台高", V("i")), 2)),
                                   V("玩家半高"))),
                  SET("vy", 0),
                  SET("在地面", 1),
              ]),
              IF(AND(AABB_overlap(), GT(V("vy"), 0)), [
                  SET("玩家y", SUB(SUB(ITEM("平台y", V("i")),
                                       DIV(ITEM("平台高", V("i")), 2)),
                                   V("玩家半高"))),
                  SET("vy", 0),
              ])),

        # ⑤ 土狼时间 + 跳跃
        IFELSE(EQ(V("在地面"), 1),
               SET("离地计时", 0),
               CHG("离地计时", 1)),
        IF(AND(EQ(V("输入_跳"), 1),
               ORn(EQ(V("在地面"), 1), LT(V("离地计时"), 4))), [
            SET("vy", V("跳跃力度")),
            SET("在地面", 0),
            SET("离地计时", 9),        # 起跳后立即封死土狼窗口，防连跳
        ]),

        # ⑥ 金币（吃一个计一个）
        *repv("i", V("金币总数"),
              IF(coin_hit(), [
                  REP("金币活", V("i"), 0),
                  CHG("得分", 10),
                  CHG("金币数", 1),
              ])),

        # ⑦ 掉出关卡 → 扣命 + 回出生点
        IF(LT(V("玩家y"), -260), [
            CHG("命数", -1),
            SET("玩家x", V("出生x")),
            SET("玩家y", V("出生y")),
            SET("vx", 0),
            SET("vy", 0),
        ]),

        # ⑧ 镜头跟随 + 两端钳制（只写一边会把镜头推到反方向，见 §162）
        SET("镜头x", SUB(V("玩家x"), V("半屏宽"))),
        IF(LT(V("镜头x"), V("关卡左")), SET("镜头x", V("关卡左"))),
        IF(GT(V("镜头x"), SUB(V("关卡右"), V("屏宽"))),
           SET("镜头x", SUB(V("关卡右"), V("屏宽")))),

        # ⑨ 渲染：屏幕坐标 = 世界坐标 - 镜头
        GOTO(SUB(V("玩家x"), V("镜头x")), V("玩家y")),
    ]


def player_scripts():
    return [
        # 读键盘要在物理之前：脚本顺序 = 执行顺序，反了就有一帧延迟
        [RECV("帧"),
         IF(EQ(V("使用键盘"), 1), [
             IFELSE(KEY("left arrow"), SET("输入_左", 1), SET("输入_左", 0)),
             IFELSE(KEY("right arrow"), SET("输入_右", 1), SET("输入_右", 0)),
             IFELSE(KEY("space"), SET("输入_跳", 1), SET("输入_跳", 0)),
         ])],
        player_frame(),
        [{"when_green_flag_clicked": None},
         {"show": None},
         SET("是克隆", 0)],
    ]


# ------------------------------------------------------------------ 地面绘制
def ground_scripts():
    """用画笔把平台按列表画成粗线（不占克隆体，也演示 §205 的配色）。"""
    return [
        [{"when_green_flag_clicked": None},
         {"hide": None},
         {"set_pen_size": {"size": 1}}],
        [RECV("帧"),
         # 只重画一次：靠 已画 标志，别每帧 clear（会闪）
         IF(EQ(V("已画"), 0), [
             {"pen_clear": None},
             SET("已画", 1),
             *repv("i", V("平台数"), *[
                 {"set_pen_size": {"size": ITEM("平台高", V("i"))}},
                 {"set_pen_color": {"COLOR": COL_PLATFORM}},
                 {"pen_up": None},
                 GOTO(SUB(SUB(ITEM("平台x", V("i")), DIV(ITEM("平台宽", V("i")), 2)),
                          V("镜头x")),
                      ITEM("平台y", V("i"))),
                 {"pen_down": None},
                 GOTO(SUB(ADD(ITEM("平台x", V("i")), DIV(ITEM("平台宽", V("i")), 2)),
                          V("镜头x")),
                      ITEM("平台y", V("i"))),
                 {"pen_up": None},
             ]),
         ])],
        [RECV("重画场景"), SET("已画", 0)],
    ]


def coin_scripts():
    return [
        [{"when_green_flag_clicked": None},
         {"hide": None},
         SET("是克隆", 0)],
        [RECV("生成金币"),
         IF(EQ(V("是克隆"), 0),
            repv("i", V("金币总数"), CLONE()))],
        [RECV("清金币"),
         IF(EQ(V("是克隆"), 1), DEL())],
        [{"when_start_as_clone": None},
         SET("是克隆", 1),
         # 克隆体读自己的编号，再从列表拿坐标（§157 Form* 工厂）
         GOTO(SUB(ITEM("金币x", V("i")), V("镜头x")), ITEM("金币y", V("i"))),
         {"set_size": {"value": 60}},
         {"show": None},
         IF(EQ(ITEM("金币活", V("i")), 0), DEL())],
        [RECV("帧"),
         IF(EQ(V("是克隆"), 1),
            IF(EQ(ITEM("金币活", V("i")), 0), DEL()))],
    ]


def stage_scripts():
    reset_round = [
        SET("玩家x", V("出生x")), SET("玩家y", V("出生y")),
        SET("vx", 0), SET("vy", 0), SET("在地面", 0), SET("离地计时", 9),
        SET("输入_左", 0), SET("输入_右", 0), SET("输入_跳", 0),
        SET("允许操作", 1), SET("已画", 0),
        *repv("__k", V("金币总数"), REP("金币活", V("__k"), 1)),
        BR("重画场景"), BR("清金币"), BR("生成金币"),
    ]
    return [
        # 绿旗：完整初始化 + 启动唯一时钟
        [{"when_green_flag_clicked": None},
         SET("得分", 0), SET("命数", 3), SET("金币数", 0),
         SET("使用键盘", 1), SET("自动帧", 1),
         SET("平台数", {"length_of_list": {"list": "平台x"}}),
         SET("金币总数", {"length_of_list": {"list": "金币x"}}),
         *reset_round,
         # 唯一时钟（§156）：两条 forever 会让物理双倍速
         FOREVER(IF(EQ(V("自动帧"), 1), BR("帧")),
                 W())],
        # 铁律 6：一局开始要复位的东西挂「重置」，不挂绿旗
        [RECV("重置"), *reset_round],
        # 行为闸门示例：暂停 = 不发帧
        [RECV("暂停"), SET("自动帧", 0)],
        [RECV("继续"), SET("自动帧", 1)],
    ]


project = {
    "project": {
        "name": "平台跳跃示例",
        "stage": {
            "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
            "variables": dict(STAGE_VARS, **{"已画": 0}),
            "lists": STAGE_LISTS,
            "scripts": stage_scripts(),
        },
        "sprites": [
            {"name": "玩家", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {"是克隆": 0},
             "scripts": player_scripts()},
            {"name": "地面", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": ground_scripts()},
            {"name": "金币", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {"是克隆": 0},
             "scripts": coin_scripts()},
        ],
    }
}


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT, "平台=", len(PLATFORMS), "金币=", len(COINS))
