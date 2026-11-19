#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成地铁模拟示例 metro.yaml（用 yaml.dump，避免手写 YAML 踩坑）。

设计要点见 references/metro-sim.md。关键决策：
- **里程是唯一真相**（§168）：速度积分成里程，屏幕位置由里程插值算出来，
  绝不直接改 x/y —— 否则到站判定、报站、线路图三处数据会打架。
- **km/h ÷ 3.6 = m/s**（§168）：漏这一步会让列车一帧飞过整站，到站判定永不触发。
- **到站判定 = 位置够近 且 基本停稳**（§170）：只判位置会「边滑边开门」。
- **车门四态状态机**（§171）：0关 1开门中 2已开 3关门中；门没关不许牵引。
- 表针用 point_in_direction 映射 0~满量程 → -90°~+90°（§173）。
- 站台用画笔按列表画，不占克隆体。

用法: python gen_metro.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "metro.yaml")

# ------------------------------------------------------------------ 线路数据
# 一条线就是一张表（§167）：加站 = 加一行，代码零改动
STATIONS = [
    # 站名,     里程(米), 屏幕x, 屏幕y, 换乘,      停站帧
    ("海傍",      0,     -200,  -40,  "4号线",    60),
    ("海涌路",    800,      0,  -40,  "",         60),
    ("石碁南",   1800,    200,  -40,  "18号线",   60),
]

COL_TRAIN = "#FFCF4D"    # 黄色系 = 主操作/载具
COL_TRACK = "#7F7F7F"    # 灰色系 = 辅助设施
COL_NEEDLE = "#5CD9BA"   # 蓝绿色系 = 主体强调

STAGE_VARS = {
    # 车辆状态（里程是唯一真相）
    "里程": 0, "速度": 0, "档位": 0, "限速": 80,
    # 站点
    "段": 1, "当前站": 1, "下一站": 2, "站总数": len(STATIONS),
    "报站": "下一站：海涌路", "通关": 0,
    # 车门四态状态机
    "车门状态": 0, "门开度": 0, "停站计时": 0,
    "停车偏差": 0, "到站次数": 0, "允许牵引": 1,
    # 派生量
    "列车x": -200, "列车y": -40, "t": 0, "表针角": -90,
    "帧计数": 0, "i": 0,
    # 手感参数
    "加速": 0.6, "制动": 0.9, "时间倍率": 8,
    "表盘满量程": 100, "米每像素": 5,
    # 循环开关
    "自动帧": 1, "使用键盘": 1, "已画": 0,
}

STAGE_LISTS = {
    "站名": [s[0] for s in STATIONS],
    "站里程": [s[1] for s in STATIONS],
    "站x": [s[2] for s in STATIONS],
    "站y": [s[3] for s in STATIONS],
    "换乘": [s[4] for s in STATIONS],
    "停站帧": [s[5] for s in STATIONS],
}


# ------------------------------------------------------------------ 主帧逻辑
def frame_script():
    return [
        RECV("帧"),
        CHG("帧计数", 1),

        # ① 门没关死 → 不许牵引（§171 铁律：别靠玩家自觉）
        IFELSE(EQ(V("车门状态"), 0), SET("允许牵引", 1), SET("允许牵引", 0)),

        # ② 档位 → 速度：+1 牵引 / 0 惰行 / -1 制动
        IF(ANDn(EQ(V("档位"), 1), EQ(V("允许牵引"), 1)), CHG("速度", V("加速"))),
        IF(EQ(V("档位"), -1), SET("速度", SUB(V("速度"), V("制动")))),
        IF(LT(V("速度"), 0), SET("速度", 0)),
        IF(GT(V("速度"), V("限速")), SET("速度", V("限速"))),

        # ③ 速度积分成里程：km/h ÷ 3.6 = m/s，再乘每帧秒数（§168）
        CHG("里程", MUL(MUL(DIV(V("速度"), 3.6), 0.0333), V("时间倍率"))),

        # ④ 里程 → 屏幕坐标：折线插值（§169）
        SET("段", SUB(V("下一站"), 1)),
        IF(LT(V("段"), 1), SET("段", 1)),
        SET("t", DIV(SUB(V("里程"), ITEM("站里程", V("段"))),
                     SUB(ITEM("站里程", V("下一站")), ITEM("站里程", V("段"))))),
        SET("列车x", ADD(ITEM("站x", V("段")),
                        MUL(SUB(ITEM("站x", V("下一站")), ITEM("站x", V("段"))), V("t")))),
        SET("列车y", ADD(ITEM("站y", V("段")),
                        MUL(SUB(ITEM("站y", V("下一站")), ITEM("站y", V("段"))), V("t")))),

        # ⑤ 到站判定：位置够近 且 停稳 且 门是关的（防重复触发）
        IF(ANDn(EQ(V("通关"), 0),
                EQ(V("车门状态"), 0),
                LT(ABS(SUB(V("里程"), ITEM("站里程", V("下一站")))), 15),
                LT(V("速度"), 2)), [
            # 停车偏差单独留档：|偏差|<=0.5m 算完美对标
            SET("停车偏差", ROUND(SUB(V("里程"), ITEM("站里程", V("下一站"))))),
            CHG("到站次数", 1),
            SET("速度", 0),
            SET("车门状态", 1),          # 转「开门中」
            BR("到站"),
        ]),

        # ⑥ 车门四态状态机（§171）
        IF(EQ(V("车门状态"), 1), [       # 开门中
            CHG("门开度", 10),
            IF(GE(V("门开度"), 100), [
                SET("门开度", 100),
                SET("车门状态", 2),
                SET("停站计时", ITEM("停站帧", V("下一站"))),
            ]),
        ]),
        IF(EQ(V("车门状态"), 2), [       # 已开：倒计时
            CHG("停站计时", -1),
            IF(LT(V("停站计时"), 1), SET("车门状态", 3)),
        ]),
        IF(EQ(V("车门状态"), 3), [       # 关门中
            CHG("门开度", -10),
            IF(LE(V("门开度"), 0), [
                SET("门开度", 0),
                SET("车门状态", 0),
                IFELSE(GT(ADD(V("下一站"), 1), V("站总数")),
                       SET("通关", 1),
                       [SET("下一站", ADD(V("下一站"), 1)),
                        CHG("当前站", 1)]),
            ]),
        ]),

        # ⑦ 报站 + 速度表针角度（§173/§174）
        IF(EQ(V("通关"), 0),
           SET("报站", JOIN("下一站：", ITEM("站名", V("下一站"))))),
        SET("表针角", SUB(MUL(DIV(V("速度"), V("表盘满量程")), 180), 90)),
    ]


def key_script():
    """键盘 → 档位。放在物理之前；行为校验会关掉它改用变量注入。"""
    return [
        RECV("帧"),
        IF(EQ(V("使用键盘"), 1), [
            IFELSE(KEY("up arrow"), SET("档位", 1),
                   IFELSE(KEY("down arrow"), SET("档位", -1),
                          SET("档位", 0))),
        ]),
    ]


def train_scripts():
    return [
        key_script(),
        frame_script(),
        [RECV("帧"), GOTO(V("列车x"), V("列车y"))],
        [{"when_green_flag_clicked": None}, {"show": None}],
    ]


def door_scripts(side):
    """两侧车门由同一个 门开度 驱动（左 - / 右 +），不是各自的布尔值。"""
    sign = -1 if side == "left" else 1
    return [
        [{"when_green_flag_clicked": None}, {"show": None}],
        [RECV("帧"),
         GOTO(ADD(V("列车x"), ADD(sign * 20, MUL(V("门开度"), 0.35 * sign))),
              V("列车y"))],
    ]


def needle_scripts():
    return [
        [{"when_green_flag_clicked": None},
         {"show": None},
         {"goto_xy": {"x": -200, "y": 110}}],
        [RECV("帧"),
         {"goto_xy": {"x": -200, "y": 110}},
         {"point_in_direction": {"direction": V("表针角")}}],
    ]


def track_scripts():
    """站台线 + 站点刻度用画笔（不占克隆体），只在第一帧画一次。"""
    return [
        [{"when_green_flag_clicked": None},
         {"hide": None},
         {"set_pen_size": {"size": 1}}],
        [RECV("帧"),
         IF(EQ(V("已画"), 0), [
             {"pen_clear": None},
             SET("已画", 1),
             # 轨道主线
             {"set_pen_size": {"size": 6}},
             {"set_pen_color": {"COLOR": COL_TRACK}},
             {"pen_up": None},
             {"goto_xy": {"x": -235, "y": -46}},
             {"pen_down": None},
             {"goto_xy": {"x": 235, "y": -46}},
             {"pen_up": None},
             # 每个站一根刻度
             *repv("i", V("站总数"), *[
                 {"set_pen_size": {"size": 4}},
                 {"set_pen_color": {"COLOR": COL_TRAIN}},
                 {"pen_up": None},
                 GOTO(ITEM("站x", V("i")), -58),
                 {"pen_down": None},
                 GOTO(ITEM("站x", V("i")), -34),
                 {"pen_up": None},
             ]),
         ])],
        [RECV("重画"), SET("已画", 0)],
    ]


def stage_scripts():
    reset_round = [
        SET("里程", 0), SET("速度", 0), SET("档位", 0),
        SET("段", 1), SET("当前站", 1), SET("下一站", 2), SET("通关", 0),
        SET("车门状态", 0), SET("门开度", 0), SET("停站计时", 0),
        SET("停车偏差", 0), SET("到站次数", 0), SET("允许牵引", 1),
        SET("列车x", ITEM("站x", 1)), SET("列车y", ITEM("站y", 1)),
        SET("表针角", -90), SET("报站", JOIN("下一站：", ITEM("站名", 2))),
        SET("已画", 0),
        BR("重画"),
    ]
    return [
        [{"when_green_flag_clicked": None},
         SET("自动帧", 1), SET("使用键盘", 1), SET("帧计数", 0),
         SET("站总数", {"length_of_list": {"list": "站名"}}),
         *reset_round,
         # 唯一时钟（§156）
         FOREVER(IF(EQ(V("自动帧"), 1), BR("帧")), W())],
        # 铁律 6：一局开始要复位的东西挂「重置」，不挂绿旗
        [RECV("重置"), *reset_round],
        [RECV("暂停"), SET("自动帧", 0)],
        [RECV("继续"), SET("自动帧", 1)],
    ]


project = {
    "project": {
        "name": "地铁模拟示例",
        "stage": {
            "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
            "variables": STAGE_VARS,
            "lists": STAGE_LISTS,
            "scripts": stage_scripts(),
        },
        "sprites": [
            {"name": "列车", "x": -200, "y": -40,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": train_scripts()},
            {"name": "左门", "x": -220, "y": -40,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": door_scripts("left")},
            {"name": "右门", "x": -180, "y": -40,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": door_scripts("right")},
            {"name": "速度表针", "x": -200, "y": 110,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": needle_scripts()},
            {"name": "轨道", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": track_scripts()},
        ],
    }
}


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT, "站数=", len(STATIONS))
