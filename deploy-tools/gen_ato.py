#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《ATO 自动驾驶（多站全自动运行）》示例 ato_train.yaml。

与 gen_metro_drive.py（手动驾驶 + ATP 保护）的分工：
- metro_drive：玩家掰手柄，ATP 只在超速时介入 —— 讲「人怎么开」。
- ato_train  ：没人碰方向盘，ATO 自己跑完全程 —— 讲「机器怎么开」。

机制说明见 references/ato-autopilot.md（第二十七册 §222–§234）。

ATO 的三层结构（缺一层就会「要么冲标、要么半路停死」）：
    ┌ 安全层（ATP）  ：允许速度包络，永远取 min，ATO 不能越权。
    ├ 规划层（ATO）  ：目标速度 = min(巡航, 包络)，末段再压三段爬行。
    └ 执行层（控制） ：误差带回差 → 牵引 / 惰行 / 制动，防抖。

关键：**不写「牵引/巡航/制动」三个状态**，那是把控制律硬编码。
只写「运行/停站」两个状态，加/减速方向由 (目标速度 - 当前速度) 的符号决定。

用法: python gen_ato.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "ato_train.yaml")

# ------------------------------------------------------------------ 线路数据
# (站名, 到下一站距离/米, 区间限速 km/h)；末站距离 0 占位
STATIONS = [
    ("前海湾", 1200, 80),
    ("桂湾",   1500, 75),
    ("前湾",      0, 80),
]
NSEG = len(STATIONS) - 1
NAMES = [s[0] for s in STATIONS]
DISTS = [s[1] for s in STATIONS[:-1]]
LIMITS = [s[2] for s in STATIONS[:-1]]

COL_TRACK = "#7F7F7F"
COL_TRAIN = "#FFCF4D"
COL_STOP = "#5CD9BA"

# 状态机（只描述「车在干什么」，不描述「用多大劲」）
ST_IDLE, ST_RUN, ST_STOP, ST_OPEN, ST_DWELL, ST_CLOSE, ST_DONE, ST_OVER = 0, 1, 2, 3, 4, 5, 6, 7

STAGE_VARS = {
    # ---- 唯一真相：本段剩余里程（出站 = 整段长度，到站 ≈ 0，冲标 < 0）----
    "剩余里程": DISTS[0],
    "速度": 0,                       # km/h
    "里程系数": 30,                  # 速度/系数 = 米/帧。30 → 60km/h 时 2 米/帧
    # ---- 站点 ----
    "站点": 1, "总段数": NSEG, "完成数": 0,
    "当前站": NAMES[0], "下一站": NAMES[1],
    # ---- 规划层 ----
    "区间限速": LIMITS[0], "巡航速度": 62, "推荐速度": LIMITS[0], "目标速度": 0, "误差": 0,
    # ---- 控制层 ----
    "档位": 0,                       # 0 惰行 / 1 牵引 / 3 制动
    "牵引加": 1.2, "制动减": 1.5, "制动率": 0.6,
    # ★ 死区必须非对称：加速侧宽（防抖、省能耗），制动侧窄（必须能停住）。
    #   对称死区会让速度卡在 (0, 死区) 之间：目标 0 但误差 -1.2 落在死区内 →
    #   既不牵引也不制动 → 车以 1.2 km/h 永远往前蹭，剩余里程一路磨到 -38 米。
    "牵引死区": 1.5, "制动死区": 0.3,
    # ---- 状态机 ----
    "状态": ST_IDLE, "状态名": "待发车",
    "起步延时": 20, "开门帧": 0, "门位": 0, "车门": 0,
    # ★ 欠标爬行是「显式子模式」，必须用标志位记住，不能靠瞬时条件推断（否则脉冲蹭行）
    # ★ 爬行段要一套独立的 ATP 余量：停车标在制动包络零点前方 5 米，不放开余量，
    #   车会被包络钉死在 d=5.0x 处 —— 差 5 厘米进不了 ±5 窗口，永远停不下来。
    "爬行": 0, "钳制余量": 2,
    # ---- 统计（质感：让玩家看见「开得好不好」）----
    "对标误差": 0, "停车结果": "—", "分值": 0, "完美数": 0,
    "牵引帧数": 0, "总帧数": 0, "能耗率": 0,
    # ---- 信号（演示 ATP 降级）----
    "信号": 3, "信号名": "绿",
    # ---- 派生 ----
    "列车x": -215, "已画": 0, "帧计数": 0, "临时": 0, "i": 0,
    # ---- 循环开关（行为校验关掉，改为脚本直接发帧）----
    "自动帧": 1,
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
    """var = expr；若 < 0 则置 0（Scratch 没有 max()）。"""
    return [SET(var, expr), IF(LT(V(var), 0), SET(var, 0))]


def min_into(var, expr):
    """var = min(var, expr)。"""
    return IF(GT(V(var), expr), SET(var, expr))


# ------------------------------------------------------------------ 主 Tick
def tick():
    """一帧九个阶段，顺序就是数据流顺序，不能换（换一步就多一帧滞后）。"""
    return [
        RECV("帧"),
        CHG("帧计数", 1),
        CHG("总帧数", 1),

        # 完成后彻底停摆（不再耗帧、不再改状态）
        IF(EQ(V("状态"), ST_DONE), {"stop": {"option": "this script"}}),

        # ============ ① 安全层：ATP 允许速度包络 ============
        # 制动曲线 v = 3.6·√(2a·max(0, d - 5))：在 d=5 处归零，即停车标前 5 米就该停住。
        *clamp_nonneg("临时", SUB(V("剩余里程"), 5)),
        SET("推荐速度", MUL(3.6, SQRT(MUL(MUL(2, V("制动率")), V("临时"))))),
        min_into("推荐速度", V("区间限速")),
        # 三显示信号（外部给定，本示例无前车；真实工程按 §214 移动闭塞算）
        # 红灯 = 包络归零，ATO 只能停；黄灯 = 限 45。ATO 无权改信号，只能服从。
        IF(EQ(V("信号"), 3), SET("信号名", "绿")),
        IF(EQ(V("信号"), 2), [SET("信号名", "黄"), min_into("推荐速度", 45)]),
        IF(EQ(V("信号"), 1), [SET("信号名", "红"), SET("推荐速度", 0)]),

        # ============ ② 规划层：目标速度 = min(巡航, 包络)，末段三段爬行 ============
        SET("目标速度", V("巡航速度")),
        min_into("目标速度", V("推荐速度")),
        # 末段压速：把「追曲线」的滞后一节一节吃掉，落点才收得紧
        IF(LE(V("剩余里程"), 60), min_into("目标速度", 22)),
        IF(LE(V("剩余里程"), 22), min_into("目标速度", 9)),
        IF(LE(V("剩余里程"), 9), min_into("目标速度", 3)),

        # ============ ③ 停站/待发车：目标速度归零 + 速度硬清零 + 起步延时 ============
        IF(EQ(V("状态"), ST_IDLE), [
            SET("目标速度", 0), SET("速度", 0),
            CHG("起步延时", -1),
            IF(LE(V("起步延时"), 0), [SET("状态", ST_RUN), SET("状态名", "运行")]),
        ]),
        # 停站/开门/关门/冲标/完成：车必须绝对静止（残留 0.3 km/h 会让车慢慢蹭）
        IF(GT(V("状态"), ST_RUN), [SET("目标速度", 0), SET("速度", 0)]),

        # ============ ④ 二次对标：停稳了但欠标 → 进入「低速爬行」子模式 ============
        # ⚠️ 爬行必须是一个显式标志（爬行=1），不能用 (速度<=0.3 且 d>5) 这种瞬时条件推。
        #   靠瞬时条件会变成「脉冲蹭行」：一帧目标 5 → 加速；速度一过 0.3 → 条件失效 →
        #   下一帧目标回 0 → 制动。速度在 0~1.2 抖动，每帧只挪几厘米，58 帧才蹭 4 米，
        #   而且红灯停住时也会被它重新推起来（速度永远停在 1.2，停不住）。
        # ⚠️ 退出阈值(3) 必须比停车窗口(±5) 更靠里：两者相等时车会停在窗口边缘外侧，
        #   判定进不去、爬行又已退出 —— 死锁在 d=5.05。
        IF(ANDn(EQ(V("状态"), ST_RUN), LE(V("剩余里程"), 40), GT(V("剩余里程"), 3),
                LE(V("速度"), 0.3), NEQ(V("信号"), 1)), SET("爬行", 1)),
        IF(ORn(NEQ(V("状态"), ST_RUN), LE(V("剩余里程"), 3), EQ(V("信号"), 1),
                ANDn(EQ(V("推荐速度"), 0), GT(V("剩余里程"), 8))),
           SET("爬行", 0)),
        # 爬行中目标速度恒为 5，不会一帧一变；ATP 余量放宽到 6 才能真的挪到标上
        IF(EQ(V("爬行"), 1),
           [SET("目标速度", 5), SET("钳制余量", 6)]),
        IF(EQ(V("爬行"), 0), SET("钳制余量", 2)),
        # 状态名跟着子模式走，玩家能看见「它为什么这么慢」
        IF(EQ(V("状态"), ST_RUN),
           IFELSE(EQ(V("爬行"), 1), SET("状态名", "爬行对标"), SET("状态名", "运行"))),

        # ============ ⑤ 执行层：误差带回差 → 档位（回差防抖是质感，不是优化）============
        SET("误差", SUB(V("目标速度"), V("速度"))),
        IF(GT(V("误差"), V("牵引死区")), [SET("档位", 1), CHG("牵引帧数", 1)]),
        IF(LT(V("误差"), SUB(0, V("制动死区"))), SET("档位", 3)),
        # 目标已经压到 0 就不留任何余量：这一条是「停得住」的最终保证
        IF(ANDn(LE(V("目标速度"), 0.5), GT(V("速度"), 0)), SET("档位", 3)),
        IF(ANDn(LE(V("误差"), V("牵引死区")), GE(V("误差"), SUB(0, V("制动死区")))),
           SET("档位", 0)),

        IF(EQ(V("档位"), 1), CHG("速度", V("牵引加"))),
        IF(EQ(V("档位"), 3), CHG("速度", SUB(0, V("制动减")))),

        # ============ ⑥ ATP 硬钳制：ATO 再努力也不许越过包络 ============
        IF(GT(V("速度"), ADD(V("推荐速度"), V("钳制余量"))), SET("速度", V("推荐速度"))),
        IF(LT(V("速度"), 0), SET("速度", 0)),
        IF(GT(V("速度"), V("区间限速")), SET("速度", V("区间限速"))),

        # ============ ⑦ 里程积分（唯一的一行物理）============
        CHG("剩余里程", SUB(0, DIV(V("速度"), V("里程系数")))),

        # ============ ⑧ 停车判定（浮窗 ±5 米，铁标是 ±1）============
        # ⚠️ 判「速度 = 0」是浮点陷阱：速度永远精确不到 0，要用 <= 阈值。
        IF(EQ(V("状态"), ST_RUN), [
            IF(ANDn(LE(V("速度"), 0.3), LE(ABS(V("剩余里程")), 5)), [
                SET("对标误差", ROUND(V("剩余里程"))),
                IFELSE(LE(ABS(V("对标误差")), 1),
                       [CHG("完美数", 1), CHG("分值", 100), SET("停车结果", "完美对标")],
                       [IFELSE(LE(ABS(V("对标误差")), 3),
                               [CHG("分值", 70), SET("停车结果", "对标良好")],
                               [CHG("分值", 40), SET("停车结果", "对标合格")])]),
                SET("速度", 0), SET("爬行", 0), SET("开门帧", 0),
                SET("状态", ST_STOP), SET("状态名", "停稳"),
            ]),
            IF(ANDn(LE(V("速度"), 0.3), LT(V("剩余里程"), -5)), [
                SET("对标误差", ROUND(V("剩余里程"))),
                SET("停车结果", "冲标"), CHG("分值", -30),
                SET("速度", 0), SET("爬行", 0), SET("开门帧", 0),
                SET("状态", ST_OVER), SET("状态名", "冲标"),
            ]),
        ]),

        # ============ ⑨ 车门状态机（停稳保持 → 开门 → 保持 → 关门 → 推进站点）============
        # 「停稳」要占 8 帧，不能一帧穿过去：真实列车对标后先停一下再弹门，
        # 而且状态如果零时长存在，外部（玩家 / 校验 / 存档）永远观测不到它。
        IF(EQ(V("状态"), ST_STOP), [
            CHG("开门帧", 1),
            IF(GE(V("开门帧"), 8),
               [SET("状态", ST_OPEN), SET("状态名", "开门"), SET("开门帧", 0)]),
        ]),

        IF(EQ(V("状态"), ST_OPEN), [
            CHG("门位", 6),
            IF(GE(V("门位"), 100),
               [SET("门位", 100), SET("车门", 1),
                SET("状态", ST_DWELL), SET("状态名", "停站"), SET("开门帧", 0)]),
        ]),

        IF(EQ(V("状态"), ST_DWELL), [
            CHG("开门帧", 1),
            IF(GE(V("开门帧"), 60), [SET("状态", ST_CLOSE), SET("状态名", "关门")]),
        ]),

        IF(EQ(V("状态"), ST_CLOSE), [
            CHG("门位", -6),
            IF(LE(V("门位"), 0), [
                SET("门位", 0), SET("车门", 0),
                CHG("站点", 1), CHG("完成数", 1),
                IFELSE(GT(V("站点"), V("总段数")),
                       [SET("状态", ST_DONE), SET("状态名", "完成"), BR("结算")],
                       [SET("剩余里程", ITEM("站距", V("站点"))),
                        SET("区间限速", ITEM("限速表", V("站点"))),
                        SET("当前站", ITEM("站名", V("站点"))),
                        SET("下一站", ITEM("站名", ADD(V("站点"), 1))),
                        SET("状态", ST_IDLE), SET("状态名", "待发车"),
                        SET("起步延时", 20)]),
            ]),
        ]),

        # 冲标：扣完分直接开门，绝不让流程卡死（卡死比冲标更伤体验）
        IF(EQ(V("状态"), ST_OVER),
           [SET("状态", ST_OPEN), SET("状态名", "开门"), SET("开门帧", 0)]),

        # ============ ⑩ 派生显示量 ============
        SET("能耗率", ROUND(MUL(100, DIV(V("牵引帧数"), ADD(V("总帧数"), 1))))),
        IFELSE(LE(V("站点"), V("总段数")), [
            SET("临时", SUB(1, DIV(V("剩余里程"), ITEM("站距", V("站点"))))),
            IF(LT(V("临时"), 0), SET("临时", 0)),
            IF(GT(V("临时"), 1), SET("临时", 1)),
            SET("列车x", ADD(-215, MUL(430, DIV(ADD(V("完成数"), V("临时")), V("总段数"))))),
        ], [SET("列车x", 215)]),
    ]


# ------------------------------------------------------------------ 线路图 / HUD
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
             {"pen_up": None}, GOTO(-215, 120),
             {"pen_down": None}, GOTO(215, 120),
             {"pen_up": None},
             *repv("i", ADD(V("总段数"), 1), *[
                 {"set_pen_size": {"size": 3}},
                 {"set_pen_color": {"COLOR": COL_STOP}},
                 {"pen_up": None},
                 GOTO(ADD(-215, MUL(430, DIV(SUB(V("i"), 1), V("总段数")))), 120),
                 {"pen_down": None},
                 GOTO(ADD(-215, MUL(430, DIV(SUB(V("i"), 1), V("总段数")))), 134),
                 {"pen_up": None},
             ]),
         ])],
        [RECV("重置"), SET("已画", 0)],
    ]


def hud_script():
    """行车电脑：模式 / 状态 / 速度双读数 / 里程 / 站点 / 能耗 / 得分。"""
    line1 = cat("【ATO】", V("状态名"), "   门 ", ROUND(V("门位")), "%")
    line2 = cat("速度 ", ROUND(V("速度")), " → 目标 ", ROUND(V("目标速度")), " km/h")
    line3 = cat("限速 ", V("区间限速"), "   包络 ", ROUND(V("推荐速度")), "   信号 ", V("信号名"))
    line4 = cat("剩余 ", ROUND(V("剩余里程")), " m   ", V("当前站"), " → ", V("下一站"))
    line5 = cat("站点 ", V("站点"), "/", V("总段数"), "   能耗 ", V("能耗率"), "%   得分 ", V("分值"))
    text = cat(line1, "\n", line2, "\n", line3, "\n", line4, "\n", line5)
    return [
        [{"when_green_flag_clicked": None},
         GOTO(-232, 176), {"point_in_direction": {"direction": 90}}, SETSIZE(66), {"show": None}],
        [RECV("帧"), {"looks_say": {"MESSAGE": text}}],
    ]


def reset_blocks():
    return [
        SET("剩余里程", DISTS[0]), SET("速度", 0), SET("档位", 0),
        SET("站点", 1), SET("完成数", 0),
        SET("当前站", NAMES[0]), SET("下一站", NAMES[1]),
        SET("区间限速", LIMITS[0]), SET("推荐速度", LIMITS[0]), SET("目标速度", 0),
        SET("状态", ST_IDLE), SET("状态名", "待发车"),
        SET("起步延时", 20), SET("门位", 0), SET("车门", 0), SET("开门帧", 0),
        SET("爬行", 0), SET("钳制余量", 2),
        SET("对标误差", 0), SET("停车结果", "—"), SET("分值", 0), SET("完美数", 0),
        SET("牵引帧数", 0), SET("总帧数", 0), SET("能耗率", 0),
        SET("信号", 3), SET("信号名", "绿"),
        SET("列车x", -215), SET("已画", 0), SET("帧计数", 0),
    ]


def stage_scripts():
    reset = reset_blocks()
    return [
        [{"when_green_flag_clicked": None},
         SET("自动帧", 1),
         SET("总段数", {"length_of_list": {"list": "站距"}}),
         *reset,
         BR("重置"),
         # 唯一时钟：暂停 = 停发帧
         FOREVER(IF(EQ(V("自动帧"), 1), BR("帧")), W())],
        [RECV("重置"), *reset],
        [RECV("暂停"), SET("自动帧", 0)],
        [RECV("继续"), SET("自动帧", 1)],
    ]


project = {
    "project": {
        "name": "ATO 自动驾驶（多站全自动）",
        "stage": {
            "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
            "variables": STAGE_VARS,
            "lists": STAGE_LISTS,
            "scripts": stage_scripts(),
        },
        "sprites": [
            # ATO 控制器：所有逻辑集中在一个角色（跨角色 = 跨时序 = bug）
            {"name": "ATO 控制器", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [tick(), [{"when_green_flag_clicked": None}, {"hide": None}]]},
            {"name": "列车", "x": -215, "y": 120,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, {"show": None}, SETSIZE(150)],
                 [RECV("帧"), GOTO(V("列车x"), 120)],
             ]},
            # 车门：尺寸 = 门位，开合是看得见的（质感：状态要可视化）
            {"name": "车门", "x": 0, "y": 92,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, {"show": None}, SETSIZE(1)],
                 [RECV("帧"), SETSIZE(ADD(1, MUL(V("门位"), 1.6)))],
             ]},
            {"name": "线路图", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": track_scripts()},
            {"name": "行车电脑", "x": -232, "y": 176,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": hud_script()},
            # 铁律 13：结算页必须有「返回 / 再来一局」按钮
            {"name": "结算面板", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, {"hide": None}],
                 [RECV("结算"),
                  {"show": None}, GOTO(0, 0), SETSIZE(1150),
                  {"looks_say": {"MESSAGE": cat(
                      "全程自动驾驶完成\n\n完美对标 ", V("完美数"), " / ", V("总段数"),
                      " 次\n牵引能耗占比 ", V("能耗率"), "%\n总分 ", V("分值"),
                      "\n\n▶ 点击本面板 = 再来一局")}}],
                 [RECV("重置"), {"hide": None}],
                 [{"when_this_sprite_clicked": None}, BR("重置")],
             ]},
        ],
    }
}


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT, " 段数=", NSEG, " 站名=", NAMES)
