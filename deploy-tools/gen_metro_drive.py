#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《地铁驾驶模拟（进阶）》示例 metro_drive.yaml。

忠实复刻真实工程《深圳地铁5号线》（150 角色 / 14134 块）的核心驾驶闭环，
机制说明见 references/metro-driving-deep.md（第二十五册 §207–§221）。

与入门版 gen_metro.py 的三个关键差别（这正是「AI 写不出高质量驾驶模拟」的原因）：
1. **剩余里程**（从整段长度递减到 0，可为负）而不是累计里程 —— 误差信号天然存在（§207）。
2. **手柄是位移→加速度**（1px 死区、10px 线性、饱和 1.5 制动）而不是离散档位（§209）。
3. **推荐速度是 min(区间限速, 制动曲线, 信号限速, 前车净空)** 的闭式 ATP（§215），
   超速自动干预；到站用「不变量握手」推进站点（§212）。

线路数据用 5 号线后段真实站距（前海湾→铁路公园），站距 = 到下一站的距离。

用法: python gen_metro_drive.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "metro_drive.yaml")

# ------------------------------------------------------------------ 线路数据
# (站名, 到下一站距离/米, 区间限速 km/h)  末站距离 0 占位
STATIONS = [
    ("前海湾",   5090,  80),
    ("桂湾",    12500,  80),
    ("前湾",     9790,  75),
    ("前湾公园", 11800,  80),
    ("妈湾",     6370,  70),
    ("铁路公园",     0,  80),
]
NSEG = len(STATIONS) - 1          # 段数 = 5
NAMES = [s[0] for s in STATIONS]
DISTS = [s[1] for s in STATIONS[:-1]]
LIMITS = [s[2] for s in STATIONS[:-1]]

COL_TRACK = "#7F7F7F"
COL_TRAIN = "#FFCF4D"
COL_STOP = "#5CD9BA"

STAGE_VARS = {
    # ---- 唯一真相：本段剩余里程（出站=整段长度，到站≈0，冲标<0）----
    "剩余里程": DISTS[0],
    "速度": 0,                       # km/h
    "档位": 0,                       # 0 惰行 / 1 牵引 / 3 制动 / 4 紧急
    # ---- 站点（站点 = 当前所在段起点站在 站名 里的下标，1-based）----
    "站点": 1, "总段数": NSEG, "完成数": 0,
    "当前站": NAMES[0], "下一站": NAMES[1],
    # ---- 限速 / ATP ----
    "区间限速": LIMITS[0], "推荐速度": LIMITS[0], "制动率": 0.6, "信号": 3, "信号名": "绿",
    # ---- 移动闭塞 ----
    "本车里程": 0, "前车里程": 20000, "前车速度": 80, "间距": 18600, "车长": 1400,
    # ---- 到站 ----
    "车门": 0,                       # 0 关 / 1 开
    "运行状态": 0,                   # 0 驾驶 / 1 停站待开门 / 2 冲标待退回 / 3 结算
    "对标误差": 0, "停车结果": "—", "分值": 0,
    # ---- 手感参数 ----
    "里程系数": 12,                  # §208：12 = 9 倍压缩；真物理 36；深圳5号线 4.9
    "牵引加": 1.2, "制动减": 1.5, "紧急减": 3.5,
    # ---- 派生显示量 ----
    "列车x": -215, "已画": 0, "帧计数": 0, "临时": 0, "i": 0,
    # ---- 循环开关（行为校验关掉 自动帧/使用键盘，改为直接注入）----
    "自动帧": 1, "使用键盘": 1, "暂停": 0,
}

STAGE_LISTS = {
    "站名": NAMES,
    "站距": DISTS,
    "限速表": LIMITS,
}


def cat(*parts):
    """把多段拼成一个 join 链（JOIN 只有 2 个输入，必须嵌套）。"""
    s = parts[0]
    for p in parts[1:]:
        s = JOIN(s, p)
    return s


def clamp_nonneg(var, expr):
    """临时 = expr；若 <0 则置 0（Scratch 没有 max()）。"""
    return [SET(var, expr), IF(LT(V(var), 0), SET(var, 0))]


# ------------------------------------------------------------------ 主 Tick
def tick():
    """§208/§214/§215/§212：一帧内跑完 手柄→ATP→积分→闭塞→推荐速度→到站。"""
    return [
        RECV("帧"),
        CHG("帧计数", 1),

        # 键盘映射（手动模式；校验里 使用键盘=0 走变量注入）
        IF(EQ(V("使用键盘"), 1), [
            IF(KEY("o"), BR("开门")),
            IF(KEY("c"), BR("关门")),
            IF(KEY("r"), BR("退回")),
            IFELSE(KEY("up arrow"), SET("档位", 1),
                   IFELSE(KEY("down arrow"), SET("档位", 3),
                          IFELSE(KEY("left arrow"), SET("档位", 4), SET("档位", 0)))),
        ]),

        # 结算后停摆
        IF(EQ(V("运行状态"), 3), {"stop": {"option": "this script"}}),
        # §212 停站中锁死速度（门没关不许动）
        IF(EQ(V("运行状态"), 1), SET("速度", 0)),

        # ================= 先算「允许跑多快」，再改速度，最后积分 =================
        # 顺序很重要：若先改速度再算推荐速度，超速保护会滞后一帧（实跑会冲过保护点）。

        # ---------- ① 移动闭塞三显示（§214，必须减车长）----------
        SET("间距", ROUND(SUB(SUB(V("前车里程"), V("本车里程")), V("车长")))),
        IFELSE(GT(V("间距"), 9000),
               [SET("信号", 3), SET("信号名", "绿")],
               [IFELSE(GT(V("间距"), 5000),
                       [SET("信号", 2), SET("信号名", "黄")],
                       [SET("信号", 1), SET("信号名", "红")])]),

        # ---------- ② 推荐速度 = min(区间限速, 制动曲线, 信号, 前车净空) ----------
        SET("推荐速度", V("区间限速")),
        # 2.1 本车到停车标：v = 3.6*sqrt(2*a*max(0, d-5))
        *clamp_nonneg("临时", SUB(V("剩余里程"), 5)),
        SET("临时", MUL(3.6, SQRT(MUL(MUL(2, V("制动率")), V("临时"))))),
        IF(LT(V("临时"), V("推荐速度")), SET("推荐速度", V("临时"))),
        # 2.2 信号限速
        IF(ANDn(EQ(V("信号"), 2), GT(V("推荐速度"), 45)), SET("推荐速度", 45)),
        IF(EQ(V("信号"), 1), SET("推荐速度", 0)),
        # 2.3 前车净空（间距已扣车长，再留 100m 余量）
        *clamp_nonneg("临时", SUB(V("间距"), 100)),
        SET("临时", MUL(3.6, SQRT(MUL(MUL(2, V("制动率")), V("临时"))))),
        IF(LT(V("临时"), V("推荐速度")), SET("推荐速度", V("临时"))),
        # 停站时推荐速度归零，避免仪表乱跳
        IF(EQ(V("运行状态"), 1), SET("推荐速度", 0)),

        # ---------- ③ 手柄 → 速度（§209：位移即加速度，这里用离散等效）----------
        IF(ANDn(EQ(V("档位"), 1), EQ(V("车门"), 0), EQ(V("运行状态"), 0)),
           CHG("速度", V("牵引加"))),
        IF(EQ(V("档位"), 3), CHG("速度", SUB(0, V("制动减")))),
        IF(EQ(V("档位"), 4), CHG("速度", SUB(0, V("紧急减")))),

        # ---------- ④ ATP 超速保护（§215）----------
        IF(GT(V("速度"), ADD(V("推荐速度"), 3)), CHG("速度", SUB(0, V("紧急减")))),
        IF(ANDn(GT(V("速度"), ADD(V("推荐速度"), 0.5)), LT(V("速度"), ADD(V("推荐速度"), 3))),
           CHG("速度", SUB(0, MUL(V("制动减"), 0.5)))),

        # ---------- ⑤ 夹紧：不许为负、不许超区间限速（§221-7）----------
        IF(LT(V("速度"), 0), SET("速度", 0)),
        IF(GT(V("速度"), V("区间限速")), SET("速度", V("区间限速"))),

        # ---------- ⑥ 里程积分（§208 唯一的一行物理）----------
        CHG("剩余里程", SUB(0, DIV(V("速度"), V("里程系数")))),
        CHG("本车里程", DIV(V("速度"), V("里程系数"))),
        CHG("前车里程", DIV(V("前车速度"), V("里程系数"))),

        # ---------- ⑦ 到站 / 冲标判定（§212 三段握手的前两段）----------
        IF(ANDn(EQ(V("运行状态"), 0), EQ(V("速度"), 0)), [
            IFELSE(LE(ABS(V("剩余里程")), 5), [
                # ★ 停稳 且 |剩余里程| <= 5 → 对标成功
                SET("对标误差", ROUND(V("剩余里程"))),
                IFELSE(LE(ABS(V("对标误差")), 1),
                       [SET("停车结果", "完美对标"), CHG("分值", 100)],
                       [SET("停车结果", "对标良好"), CHG("分值", 60)]),
                SET("运行状态", 1),
            ], [
                IF(ANDn(LT(V("剩余里程"), -5), EQ(V("运行状态"), 0)), [
                    SET("对标误差", ROUND(V("剩余里程"))),
                    SET("停车结果", "冲标"),
                    CHG("分值", -50),
                    SET("运行状态", 2),
                ]),
            ]),
        ]),
        # 冲标后退回，重新落入窗口
        IF(ANDn(EQ(V("运行状态"), 2), LE(ABS(V("剩余里程")), 5)), [
            SET("对标误差", ROUND(V("剩余里程"))),
            SET("停车结果", "退回对标"),
            CHG("分值", 40),
            SET("运行状态", 1),
        ]),

        # ---------- ⑧ 列车在线路图上的位置 ----------
        # 段内进度 = 1 - 剩余/站距，夹到 [0,1]
        SET("临时", SUB(1, DIV(V("剩余里程"), ITEM("站距", V("站点"))))),
        IF(LT(V("临时"), 0), SET("临时", 0)),
        IF(GT(V("临时"), 1), SET("临时", 1)),
        SET("列车x", ADD(-215, MUL(430, DIV(ADD(V("完成数"), V("临时")), V("总段数"))))),
    ]


# ------------------------------------------------------------------ 车门 / 结算
def door_logic():
    """§212 第三段握手：开门重置里程 + 站点推进（用不变量而非标志位）。"""
    return [
        [RECV("开门"),
         IF(ANDn(EQ(V("运行状态"), 1), EQ(V("车门"), 0)), [SET("车门", 1)])],

        [RECV("关门"),
         IF(EQ(V("车门"), 1), [
             SET("车门", 0),
             IF(EQ(V("运行状态"), 1), [
                 CHG("完成数", 1),
                 IFELSE(GE(V("站点"), V("总段数")),
                        [SET("运行状态", 3), BR("结算")],
                        [# ★ 先推进站点，再把剩余里程重置成"新段全长"
                         CHG("站点", 1),
                         SET("剩余里程", ITEM("站距", V("站点"))),
                         SET("区间限速", ITEM("限速表", V("站点"))),
                         SET("推荐速度", ITEM("限速表", V("站点"))),
                         SET("当前站", ITEM("站名", V("站点"))),
                         SET("下一站", ITEM("站名", ADD(V("站点"), 1))),
                         SET("对标误差", 0),
                         SET("停车结果", "—"),
                         SET("运行状态", 0)]),
             ]),
         ])],

        # 冲标退回：直接回退里程（真工程是挂倒档，示例简化成按钮）
        [RECV("退回"),
         IF(EQ(V("运行状态"), 2), [
             SET("速度", 0),
             CHG("剩余里程", 12),
             IF(GT(V("剩余里程"), 5), SET("剩余里程", 5)),
         ])],
    ]


def hud_script():
    """仪表：数字 + 文字标签（铁律 1）。用 looks_say 常驻显示。"""
    line1 = cat("速度 ", ROUND(V("速度")), " km/h   限速 ", V("区间限速"))
    line2 = cat("推荐 ", ROUND(V("推荐速度")), " km/h   信号 ", V("信号名"))
    line3 = cat("剩余 ", ROUND(V("剩余里程")), " m   ", V("当前站"), "→", V("下一站"))
    line4 = cat("对标 ", V("对标误差"), " m   ", V("停车结果"), "   得分 ", V("分值"))
    text = cat(line1, "\n", line2, "\n", line3, "\n", line4)
    return [
        [{"when_green_flag_clicked": None},
         GOTO(-235, 178), {"point_in_direction": {"direction": 90}}, SETSIZE(70), {"show": None}],
        [RECV("帧"),
         {"looks_say": {"MESSAGE": text}}],
    ]


def track_scripts():
    """线路图：一条横线 + 每个站一根刻度（画笔，不占克隆体）。"""
    return [
        [{"when_green_flag_clicked": None}, {"hide": None},
         {"set_pen_size": {"size": 1}}, {"pen_up": None}],
        [RECV("帧"),
         IF(EQ(V("已画"), 0), [
             {"pen_clear": None}, SET("已画", 1),
             {"set_pen_size": {"size": 4}},
             {"set_pen_color": {"COLOR": COL_TRACK}},
             {"pen_up": None}, {"goto_xy": {"x": -215, "y": 120}},
             {"pen_down": None}, {"goto_xy": {"x": 215, "y": 120}},
             {"pen_up": None},
             *repv("i", ADD(V("总段数"), 1), *[
                 {"set_pen_size": {"size": 3}},
                 {"set_pen_color": {"COLOR": COL_STOP}},
                 {"pen_up": None},
                 GOTO(ADD(-215, MUL(430, DIV(SUB(V("i"), 1), V("总段数")))), 120),
                 {"pen_down": None},
                 GOTO(ADD(-215, MUL(430, DIV(SUB(V("i"), 1), V("总段数")))), 132),
                 {"pen_up": None},
             ]),
         ])],
        [RECV("重置"), SET("已画", 0)],
    ]


def stage_scripts():
    reset = [
        SET("剩余里程", ITEM("站距", 1)),
        SET("速度", 0), SET("档位", 0),
        SET("站点", 1), SET("完成数", 0),
        SET("当前站", ITEM("站名", 1)), SET("下一站", ITEM("站名", 2)),
        SET("区间限速", ITEM("限速表", 1)), SET("推荐速度", ITEM("限速表", 1)),
        SET("信号", 3), SET("信号名", "绿"),
        SET("本车里程", 0), SET("前车里程", 20000), SET("前车速度", 80), SET("间距", 18600),
        SET("车门", 0), SET("运行状态", 0),
        SET("对标误差", 0), SET("停车结果", "—"), SET("分值", 0),
        SET("列车x", -215), SET("已画", 0), SET("帧计数", 0),
    ]
    return [
        [{"when_green_flag_clicked": None},
         SET("自动帧", 1), SET("使用键盘", 1),
         SET("总段数", {"length_of_list": {"list": "站距"}}),
         *reset,
         BR("重置"),
         # 唯一时钟（§156）：暂停 = 停发帧
         FOREVER(IF(EQ(V("自动帧"), 1), BR("帧")), W())],
        # 铁律 6：一局要复位的东西挂「重置」，不挂绿旗
        [RECV("重置"), *reset],
        [RECV("暂停"), SET("自动帧", 0)],
        [RECV("继续"), SET("自动帧", 1)],
    ]


project = {
    "project": {
        "name": "地铁驾驶模拟（进阶）",
        "stage": {
            "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
            "variables": STAGE_VARS,
            "lists": STAGE_LISTS,
            "scripts": stage_scripts(),
        },
        "sprites": [
            # 行车电脑：所有物理与判定都在这一个角色里（跨角色 = 跨时序 = bug）
            {"name": "行车电脑", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [tick(), *door_logic(),
                         [{"when_green_flag_clicked": None}, {"hide": None}]]},
            {"name": "列车", "x": -215, "y": 120,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, {"show": None}, SETSIZE(160)],
                 [RECV("帧"), GOTO(V("列车x"), 120)],
             ]},
            {"name": "线路图", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": track_scripts()},
            {"name": "仪表", "x": -235, "y": 178,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": hud_script()},
            # 铁律 13：结算页必须有「再来一局」按钮
            {"name": "结算面板", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, {"hide": None}],
                 [RECV("结算"),
                  {"show": None}, GOTO(0, 0), SETSIZE(1200),
                  {"looks_say": {"MESSAGE": cat("全部 ", V("总段数"), " 段跑完！\n得分 ", V("分值"),
                                                "\n\n▶ 点击本面板 = 再来一局")}}],
                 [RECV("重置"), {"hide": None}],
                 # 广播「重置」而不是绿旗（铁律 6）
                 [{"when_this_sprite_clicked": None}, BR("重置")],
             ]},
        ],
    }
}


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT, " 段数=", NSEG, " 站名=", NAMES)
