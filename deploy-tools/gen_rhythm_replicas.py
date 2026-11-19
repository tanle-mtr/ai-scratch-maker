#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《五款代表作音游复刻引擎》示例 rhythm_replicas.yaml（第三十九册 §457–§478）。

一份引擎 + 五张配置表，可切换：
  1 Phigros（无轨 / 可动判定线 / 切向投影命中）
  2 PJSK（定轨 12 格 / 五档 / Life / GOOD 断连）
  3 Milthm（不定轨 / 判定圈 / 六档 / Ξ-Φ 双序列 / 水面反射）
  4 跳舞的线（单键转角窗口 / 扫描指针 / 检查点）
  5 滚动的天空（5 列离散网格 / 自动前进 / 跳板 / 无地板判定）

全部判定是「输入 → 输出」纯函数，用已知答案硬校验。
机制见 references/rhythm-replicas.md。

用法: python gen_rhythm_replicas.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "rhythm_replicas.yaml")


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

STAGE_VARS = {
    "结果": "", "帧计数": 0, "自动帧": 1,
    "模式": 1,
    # 唯一时钟
    "songTime": 0, "输入时刻": 0, "有效时刻": 0, "目标时刻": 0,
    "误差": 0, "绝对误差": 0, "帧长ms": 33, "校准ms": 0,
    # 档位窗口（设模式时装载）
    "窗1": 80, "窗2": 180, "窗3": 220, "窗4": 220, "窗5": 220,
    "权1": 100, "权2": 65, "权3": 0, "权4": 0, "权5": 0, "权6": 0,
    "断连阈值": 3, "档位数": 4, "候选窗口": 300,
    "档1名": "Perfect", "档2名": "Good", "档3名": "Bad",
    "档4名": "-", "档5名": "-", "档6名": "Miss",
    "档位": 0, "档名词": "", "本档权重": 0, "临时": 0,
    # 判定体
    "体类型": 1, "线X": 0, "线Y": 0, "线角": 0,
    "圈X": 0, "圈Y": 0, "圈半径": 100, "全屏判定": 0,
    "不透明度": 255, "切向坐标": 0, "法向坐标": 0, "距离平方": 0,
    "半径平方": 0, "半宽": 50, "宽度单位": 1,
    # 输入
    "输入X": 0, "输入Y": 0, "输入格": 0, "输入列": 0,
    "输入动作": 1, "输入方向": 0, "音符方向": 0,
    # 谱面 / 扫描
    "音符数": 0, "最近索引": 0, "最近误差": 0, "扫描指针": 1,
    "音符类型": 0, "音符参数": 0, "音符时长": 0, "音符线号": 0,
    "i": 0, "j": 0, "临时时刻": 0, "尾索引": 0,
    # 计分
    "分数": 0, "裸分": 0, "连击": 0, "最大连击": 0,
    "准确率": 0, "评级": "", "满分总分": 0,
    "档1数": 0, "档2数": 0, "档3数": 0,
    "档4数": 0, "档5数": 0, "档Miss数": 0,
    "生命": 1000, "生命扣减": 0,
    # Phigros 官谱换算
    "bpm": 100, "Tms": 18.75, "timeT": 0,
    # 判定线事件
    "事件起": 0, "事件止": 0, "事件起值": 0, "事件终值": 0,
    "事件数": 0, "事件插值": 0,
    # Milthm 专用
    "闪电HP": 3, "闪电Exact": 0, "闪电Miss": 0, "Ξ数": 0,
    "活跃雨丝": 0, "屏上手指": 0, "闪电溢出": 0,
    # 亚音游专用
    "当前行": 0, "每行ms": 500, "当前列": 2, "连续列": 2.0,
    "地板": 1, "障碍": 0, "跳板": 0, "收集": 0,
    "当前段": 0, "转角时刻": 0, "转向窗口": 100,
    "检查点": 0, "失败数": 0, "完成度": 0, "腾空": 0,
    "跳高": 0, "跳远": 0, "格宽": 60, "行收集数": 0,
}

STAGE_LISTS = {
    # 通用谱面（索引 1..N）
    "谱时刻": [0] * 40, "谱类型": [0] * 40, "谱位置": [0] * 40,
    "谱线号": [0] * 40, "谱时长": [0] * 40, "谱方向": [0] * 40,
    "谱参数": [0] * 40, "已判定": [0] * 40,
    # Phigros 判定线事件
    "事件线": [0] * 12, "事件型": [0] * 12,
    "事件起表": [0] * 12, "事件止表": [0] * 12,
    "事件起值表": [0] * 12, "事件终值表": [0] * 12,
    # 跳舞的线转角表 / 滚动的天空行表
    "转角时刻": [0] * 20, "已转": [0] * 20, "段检查点": [0] * 20,
    "行地板": [1] * 20, "行障碍": [0] * 20,
    "行跳板": [0] * 20, "行收集": [0] * 20, "行障碍列": [0] * 20,
    "行地板列": [0] * 20,
}


def tier_blocks():
    """统一分档：a ≤ 窗1→1 … ≤ 窗5→5，否则 6。IFELSE 链防同帧覆盖。"""
    def set_tier(n, name, weight):
        return [SET("档位", n), SET("档名词", name), SET("本档权重", weight)]
    return [
        IFELSE(LE(V("绝对误差"), V("窗1")),
               set_tier(1, V("档1名"), V("权1")),
               [
                   IFELSE(LE(V("绝对误差"), V("窗2")),
                          set_tier(2, V("档2名"), V("权2")),
                          [
                              IFELSE(LE(V("绝对误差"), V("窗3")),
                                     set_tier(3, V("档3名"), V("权3")),
                                     [
                                         IFELSE(LE(V("绝对误差"), V("窗4")),
                                                set_tier(4, V("档4名"), V("权4")),
                                                [
                                                    IFELSE(LE(V("绝对误差"), V("窗5")),
                                                           set_tier(5, V("档5名"), V("权5")),
                                                           set_tier(6, V("档6名"), V("权6")))
                                                ])
                                     ])
                          ])
               ])
    ]


def score_blocks():
    """计分：裸分按权重、各档计数、连击按阈值断、Life 扣减（仅 PJSK 有值）。"""
    return [
        CHG("裸分", V("本档权重")),
        CHG("分数", V("本档权重")),
        IF(EQ(V("档位"), 1), CHG("档1数", 1)),
        IF(EQ(V("档位"), 2), CHG("档2数", 1)),
        IF(EQ(V("档位"), 3), CHG("档3数", 1)),
        IF(EQ(V("档位"), 4), CHG("档4数", 1)),
        IF(EQ(V("档位"), 5), CHG("档5数", 1)),
        IF(EQ(V("档位"), 6), CHG("档Miss数", 1)),
        IFELSE(GE(V("档位"), V("断连阈值")),
               SET("连击", 0),
               [CHG("连击", 1),
                IF(GT(V("连击"), V("最大连击")), SET("最大连击", V("连击")))]),
        SET("生命扣减", 0),
        IF(ANDn(EQ(V("模式"), 2), EQ(V("档位"), 4)), SET("生命扣减", 50)),
        IF(ANDn(EQ(V("模式"), 2), EQ(V("档位"), 6)), SET("生命扣减", 80)),
        SET("生命", SUB(V("生命"), V("生命扣减"))),
    ]


# ------------------------------------------------------------------ 1. 设模式
def mode_script():
    """一张模式表切五款：窗口 / 权重 / 断连阈值 / 判定体 / 生命。"""
    def cfg(mode, w, weights, brk, names, body, hp, cw):
        return IF(EQ(V("模式"), mode), [
            SET("窗1", w[0]), SET("窗2", w[1]), SET("窗3", w[2]),
            SET("窗4", w[3]), SET("窗5", w[4]),
            SET("权1", weights[0]), SET("权2", weights[1]), SET("权3", weights[2]),
            SET("权4", weights[3]), SET("权5", weights[4]), SET("权6", weights[5]),
            SET("断连阈值", brk),
            SET("档1名", names[0]), SET("档2名", names[1]), SET("档3名", names[2]),
            SET("档4名", names[3]), SET("档5名", names[4]), SET("档6名", names[5]),
            SET("体类型", body), SET("生命", hp), SET("候选窗口", cw),
        ])
    return [
        RECV("设模式"),
        cfg(1, [80, 180, 220, 220, 220], [100, 65, 0, 0, 0, 0], 3,
            ["Perfect", "Good", "Bad", "-", "-", "Miss"], 1, 0, 300),
        cfg(2, [41.7, 83.3, 108.3, 125, 125], [100, 70, 50, 0, 0, 0], 3,
            ["PERFECT", "GREAT", "GOOD", "BAD", "-", "MISS"], 1, 1000, 200),
        cfg(3, [35, 70, 105, 140, 155], [100, 100, 60, 30, 15, 0], 5,
            ["Exact", "Perfect", "Great", "Good", "Bad", "Miss"], 2, 0, 200),
        cfg(4, [100, 100, 100, 100, 100], [100, 0, 0, 0, 0, 0], 6,
            ["通过", "-", "-", "-", "-", "失败"], 4, 0, 200),
        cfg(5, [100, 100, 100, 100, 100], [100, 0, 0, 0, 0, 0], 6,
            ["通过", "-", "-", "-", "-", "失败"], 3, 0, 200),
        SET("结果", cat("模式 ", V("模式"), " 窗口 ", V("窗1"), "/", V("窗2"),
                        "/", V("窗3"), "/", V("窗4"), "/", V("窗5"),
                        " 断连阈值 ", V("断连阈值"))),
    ]


# ------------------------------------------------------------------ 2. Phigros 官谱换算 + 事件求值
def phigros_util_script():
    return [
        RECV("官谱换算"),
        SET("Tms", DIV(1875, V("bpm"))),
        SET("目标时刻", ROUND(MUL(V("timeT"), V("Tms")))),
        SET("结果", cat("bpm ", V("bpm"), " / T=", V("Tms"),
                        "ms / timeT ", V("timeT"), " → ", V("目标时刻"), "ms")),
    ]


def line_eval_script():
    """§460：事件线性插值（官谱无缓动）。不透明度 ≤0 只关渲染，判定仍生效。"""
    return [
        RECV("判定线求值"),
        SET("事件插值", 0),
        *repv("i", V("事件数"), *[
            SET("事件起", ITEM("事件起表", V("i"))),
            SET("事件止", ITEM("事件止表", V("i"))),
            SET("事件起值", ITEM("事件起值表", V("i"))),
            SET("事件终值", ITEM("事件终值表", V("i"))),
            IFELSE(LE(V("songTime"), V("事件起")),
                   SET("事件插值", V("事件起值")),
                   [IFELSE(GE(V("songTime"), V("事件止")),
                           SET("事件插值", V("事件终值")),
                           SET("事件插值", ADD(V("事件起值"),
                                               MUL(SUB(V("事件终值"), V("事件起值")),
                                                   DIV(SUB(V("songTime"), V("事件起")),
                                                       SUB(V("事件止"), V("事件起")))))))]),
            # 事件型：1移动X 2移动Y 3旋转 4透明度 5速度
            IF(EQ(ITEM("事件型", V("i")), 1), SET("线X", V("事件插值"))),
            IF(EQ(ITEM("事件型", V("i")), 2), SET("线Y", V("事件插值"))),
            IF(EQ(ITEM("事件型", V("i")), 3), SET("线角", V("事件插值"))),
            IF(EQ(ITEM("事件型", V("i")), 4), SET("不透明度", V("事件插值"))),
        ]),
        SET("结果", cat("线 X", V("线X"), " Y", V("线Y"), " 角", V("线角"),
                        " 透明度", V("不透明度"))),
    ]


# ------------------------------------------------------------------ 3. Phigros 判定
def phigros_judge_script():
    """§461/§462：切向投影命中（法向不参与）+ 四音符类型 + 单次点击只判一个。"""
    return [
        RECV("P判一击"),
        SET("有效时刻", MUL(ROUND(DIV(SUB(V("输入时刻"), V("校准ms")),
                                     V("帧长ms"))), V("帧长ms"))),
        # 切向坐标 t = dx·cosθ + dy·sinθ（Scratch 三角函数吃角度）
        SET("切向坐标", ADD(MUL(SUB(V("输入X"), V("线X")), COS(V("线角"))),
                            MUL(SUB(V("输入Y"), V("线Y")), SIN(V("线角"))))),
        SET("最近索引", 0), SET("最近误差", 999999),
        *repv("i", V("音符数"), *[
            SET("临时", ABS(SUB(V("有效时刻"), ITEM("谱时刻", V("i"))))),
            IF(ANDn(EQ(ITEM("已判定", V("i")), 0),
                    LE(ABS(SUB(V("切向坐标"), ITEM("谱位置", V("i")))), V("半宽")),
                    LE(V("临时"), V("候选窗口")),
                    LT(V("临时"), V("最近误差"))),
               [SET("最近误差", V("临时")), SET("最近索引", V("i"))]),
        ]),
        IFELSE(EQ(V("最近索引"), 0),
               [SET("档位", 0), SET("档名词", "空击"), SET("结果", "切向未命中任何音符")],
               [
                   SET("音符类型", ITEM("谱类型", V("最近索引"))),
                   SET("目标时刻", ITEM("谱时刻", V("最近索引"))),
                   SET("误差", SUB(V("有效时刻"), V("目标时刻"))),
                   SET("绝对误差", ABS(V("误差"))),
                   # Drag(2)/Flick(4) 只有 P/Miss；Hold(3) 无 Bad
                   IFELSE(ORn(EQ(V("音符类型"), 2), EQ(V("音符类型"), 4)),
                          [IFELSE(LE(V("绝对误差"), V("窗1")),
                                  [SET("档位", 1), SET("档名词", "Perfect"), SET("本档权重", 100)],
                                  [SET("档位", 6), SET("档名词", "Miss"), SET("本档权重", 0)])],
                          [*tier_blocks(),
                           IF(ANDn(EQ(V("音符类型"), 3), EQ(V("档位"), 3)),
                              [SET("档位", 6), SET("档名词", "Miss"), SET("本档权重", 0)])]),
                   REP("已判定", V("最近索引"), V("档位")),
                   *score_blocks(),
                   SET("结果", cat("Phigros ", V("档名词"), " 误差 ", V("误差"),
                                   "ms 切向 ", V("切向坐标"))),
               ]),
    ]


# ------------------------------------------------------------------ 4. PJSK 判定
def pjsk_judge_script():
    """§464/§465：12 格区间匹配 + 五档 + GOOD 断连 + Trace/Flick/Hold 尾 + Life。"""
    return [
        RECV("S判一击"),
        SET("有效时刻", MUL(ROUND(DIV(SUB(V("输入时刻"), V("校准ms")),
                                     V("帧长ms"))), V("帧长ms"))),
        SET("最近索引", 0), SET("最近误差", 999999),
        *repv("i", V("音符数"), *[
            SET("临时", ABS(SUB(V("有效时刻"), ITEM("谱时刻", V("i"))))),
            # 格区间匹配：起始格 ≤ 输入格 < 起始格 + 宽度(谱参数)
            IF(ANDn(EQ(ITEM("已判定", V("i")), 0),
                    GE(V("输入格"), ITEM("谱位置", V("i"))),
                    LT(V("输入格"), ADD(ITEM("谱位置", V("i")),
                                       ITEM("谱参数", V("i")))),
                    LE(V("临时"), V("候选窗口")),
                    LT(V("临时"), V("最近误差"))),
               [SET("最近误差", V("临时")), SET("最近索引", V("i"))]),
        ]),
        IFELSE(EQ(V("最近索引"), 0),
               [SET("档位", 0), SET("档名词", "空击"), SET("结果", "该格无候选音符")],
               [
                   SET("音符类型", ITEM("谱类型", V("最近索引"))),  # 1Tap 2Hold 3Flick 4Trace
                   SET("音符方向", ITEM("谱方向", V("最近索引"))),
                   SET("目标时刻", ITEM("谱时刻", V("最近索引"))),
                   SET("误差", SUB(V("有效时刻"), V("目标时刻"))),
                   SET("绝对误差", ABS(V("误差"))),
                   # Flick 方向不符 → Miss
                   IF(ANDn(EQ(V("音符类型"), 3), NEQ(V("输入方向"), V("音符方向"))),
                      SET("绝对误差", 9999)),
                   # Trace 只出 P/Miss（任何接触即通过）
                   IFELSE(EQ(V("音符类型"), 4),
                          [SET("档位", 1), SET("档名词", "PERFECT"), SET("本档权重", 100)],
                          [*tier_blocks()]),
                   REP("已判定", V("最近索引"), V("档位")),
                   *score_blocks(),
                   # Hold 头命中后标记「等尾判」，尾判由 S尾判 广播结算
                   IF(EQ(V("音符类型"), 2), REP("已判定", V("最近索引"), 5)),
                   SET("结果", cat("PJSK ", V("档名词"), " 格 ", V("输入格"),
                                   " Life ", V("生命"), " 连击 ", V("连击"))),
               ]),
    ]


def pjsk_tail_script():
    """§465：Hold 尾判（平尾 / Flick 尾 / Trace 尾）。"""
    return [
        RECV("S尾判"),
        SET("尾索引", 0),
        *repv("i", V("音符数"), *[
            IF(EQ(ITEM("已判定", V("i")), 5), SET("尾索引", V("i"))),
        ]),
        IFELSE(EQ(V("尾索引"), 0),
               [SET("结果", "没有等待尾判的 Hold")],
               [
                   SET("目标时刻", ADD(ITEM("谱时刻", V("尾索引")),
                                      ITEM("谱时长", V("尾索引")))),
                   SET("误差", SUB(V("输入时刻"), V("目标时刻"))),
                   SET("绝对误差", ABS(V("误差"))),
                   *tier_blocks(),
                   REP("已判定", V("尾索引"), V("档位")),
                   *score_blocks(),
                   SET("结果", cat("Hold 尾判 ", V("档名词"), " 误差 ", V("误差"), "ms")),
               ]),
    ]


# ------------------------------------------------------------------ 5. Milthm 判定
def milthm_judge_script():
    """§466–§468：圆命中 + 六档 + Ξ/Φ 双序列 + 水面反射 + 闪电最后判。"""
    return [
        RECV("M判一击"),
        SET("有效时刻", MUL(ROUND(DIV(SUB(V("输入时刻"), V("校准ms")),
                                     V("帧长ms"))), V("帧长ms"))),
        SET("距离平方", ADD(MUL(SUB(V("输入X"), V("圈X")), SUB(V("输入X"), V("圈X"))),
                            MUL(SUB(V("输入Y"), V("圈Y")), SUB(V("输入Y"), V("圈Y"))))),
        SET("半径平方", MUL(V("圈半径"), V("圈半径"))),
        IFELSE(ORn(LE(V("距离平方"), V("半径平方")), EQ(V("全屏判定"), 1)),
               [SET("临时", 1)], [SET("临时", 0)]),
        SET("最近索引", 0), SET("最近误差", 999999),
        *repv("i", V("音符数"), *[
            SET("临时时刻", ABS(SUB(V("有效时刻"), ITEM("谱时刻", V("i"))))),
            IF(ANDn(EQ(ITEM("已判定", V("i")), 0),
                    EQ(V("临时"), 1),
                    LE(V("临时时刻"), V("候选窗口")),
                    LT(V("临时时刻"), V("最近误差"))),
               [SET("最近误差", V("临时时刻")), SET("最近索引", V("i"))]),
        ]),
        IFELSE(EQ(V("最近索引"), 0),
               [SET("档位", 0), SET("档名词", "空击"), SET("结果", "圈外，未命中")],
               [
                   SET("音符类型", ITEM("谱类型", V("最近索引"))),  # 1雨露 2雨丝 3雨滴 4闪电
                   # ★ 闪电最后判定：普通候选优先，闪电留到 M闪电 广播
                   IFELSE(EQ(V("音符类型"), 4),
                          [SET("档位", 0), SET("档名词", "闪电待后判"),
                           SET("结果", "闪电最后判定，交给 M闪电")],
                          [
                              SET("目标时刻", ITEM("谱时刻", V("最近索引"))),
                              SET("误差", SUB(V("有效时刻"), V("目标时刻"))),
                              SET("绝对误差", ABS(V("误差"))),
                              *tier_blocks(),
                              REP("已判定", V("最近索引"), V("档位")),
                              *score_blocks(),
                              CHG("Ξ数", 1),
                              # 雨丝命中 → 水面反射：全屏判定 + 记活跃
                              IF(EQ(V("音符类型"), 2),
                                 [SET("全屏判定", 1), CHG("活跃雨丝", 1),
                                  CHG("屏上手指", 1)]),
                              SET("结果", cat("Milthm ", V("档名词"), " 误差 ", V("误差"),
                                              "ms 距离² ", V("距离平方"))),
                          ]),
               ]),
    ]


def milthm_lightning_script():
    """§467：闪电独立序列 Φ —— 不进 Ξ、不计物量、不影响 AP/FC。"""
    return [
        RECV("M闪电"),
        SET("档位", 0),
        IFELSE(LE(ABS(SUB(V("输入时刻"), V("目标时刻"))), V("窗2")),
               [SET("档位", 1), CHG("闪电Exact", 1), SET("结果", "Lightning Exact")],
               [SET("档位", 6), CHG("闪电Miss", 1),
                SET("闪电溢出", 0),
                IF(LE(V("闪电HP"), 0), SET("闪电溢出", 1)),
                SET("闪电HP", SUB(V("闪电HP"), 1)),
                # ★ 只有「伤害溢出」才影响连击分状态；不影响 Ξ / AP / FC
                SET("结果", cat("Lightning Miss / HP ", V("闪电HP"),
                                " / 溢出 ", V("闪电溢出")))]),
        # Ξ数 不变（验证用）
    ]


def milthm_water_script():
    """§468 水面反射：有活跃雨丝时至少一根手指；无雨丝时继续按住不产生判定。"""
    return [
        RECV("水面反射"),
        IFELSE(ANDn(GT(V("活跃雨丝"), 0), LT(V("屏上手指"), 1)),
               [CHG("档Miss数", V("活跃雨丝")), SET("连击", 0),
                SET("结果", "有雨丝接触判定圈却没有手指 → Miss")],
               [IFELSE(GT(V("活跃雨丝"), 0),
                       [SET("全屏判定", 1), SET("结果", "水面反射生效：全屏判定、允许换手")],
                       [SET("全屏判定", 0), SET("结果", "无活跃雨丝：继续按住不产生判定，也不惩罚")])]),
    ]


# ------------------------------------------------------------------ 6. 跳舞的线
def dancing_script():
    """§469：单键转角窗口 + 扫描指针 + 检查点。无空间项、无误差分级。"""
    return [
        RECV("D一步"),
        SET("当前段", V("扫描指针")),
        IFELSE(GT(V("当前段"), LLEN("转角时刻")),
               [SET("结果", "已抵达终点")],
               [
                   SET("转角时刻", ITEM("转角时刻", V("当前段"))),
                   SET("误差", SUB(V("输入时刻"), V("转角时刻"))),
                   SET("绝对误差", ABS(V("误差"))),
                   IFELSE(ANDn(EQ(ITEM("已转", V("当前段")), 0),
                               LE(V("绝对误差"), V("转向窗口"))),
                          [
                              REP("已转", V("当前段"), 1),
                              CHG("扫描指针", 1),
                              CHG("完成度", 1),
                              IF(EQ(ITEM("段检查点", V("当前段")), 1),
                                 SET("检查点", V("当前段"))),
                              SET("档位", 1), SET("档名词", "转向成功"),
                              SET("结果", cat("转向成功 第", V("当前段"), " 转角 / 误差 ", V("误差"), "ms")),
                          ],
                          [
                              CHG("失败数", 1),
                              SET("扫描指针", ADD(V("检查点"), 1)),
                              SET("档位", 6), SET("档名词", "撞墙"),
                              SET("结果", cat("失败 → 回检查点 ", V("检查点"))),
                          ]),
               ]),
    ]


# ------------------------------------------------------------------ 7. 滚动的天空
def rolling_script():
    """§470：5 列离散网格；列取整后查表；无地板/障碍/跳板；障碍需地板支撑。"""
    return [
        RECV("R一步"),
        SET("当前行", ADD(ROUND(DIV(V("songTime"), V("每行ms"))), 1)),
        # ★ 拖动是连续量、判定是离散量：取整
        SET("当前列", ROUND(V("连续列"))),
        SET("地板", ITEM("行地板", V("当前行"))),
        SET("障碍", ITEM("行障碍", V("当前行"))),
        SET("跳板", ITEM("行跳板", V("当前行"))),
        SET("收集", ITEM("行收集", V("当前行"))),
        SET("临时", 0),
        # 障碍列匹配（行障碍列存列号，0 表示无）
        IF(ANDn(GT(V("障碍"), 0),
                EQ(V("当前列"), ITEM("行障碍列", V("当前行")))),
           SET("临时", 2)),
        # 地板缺失（行地板列存缺失列，-1 表示全有）
        IF(ANDn(EQ(V("地板"), 0), EQ(V("当前列"), ITEM("行地板列", V("当前行")))),
           SET("临时", 1)),
        # ★ 障碍必须有一个地板支撑，否则无伤害判定
        IF(ANDn(EQ(V("临时"), 2), EQ(V("地板"), 0)), SET("临时", 0)),
        IFELSE(EQ(V("临时"), 0),
               [
                   SET("档位", 1), SET("档名词", "通过"),
                   CHG("完成度", 1),
                   IF(EQ(V("收集"), 1), CHG("行收集数", 1)),
                   IF(EQ(V("跳板"), 1),
                      [SET("腾空", 1), SET("跳高", 3), SET("跳远", 4)]),
                   SET("结果", cat("通过 行", V("当前行"), " 列", V("当前列"),
                                   " 完成度 ", V("完成度"))),
               ],
               [
                   SET("档位", 6), SET("档名词", "失败"),
                   CHG("失败数", 1),
                   SET("结果", cat("失败 行", V("当前行"), " 列", V("当前列"),
                                   " 原因 ", V("临时"))),
               ]),
    ]


# ------------------------------------------------------------------ 8. 结算
def result_script():
    return [
        RECV("结算"),
        SET("满分总分", MUL(100, V("音符数"))),
        IFELSE(EQ(V("满分总分"), 0), SET("准确率", 0),
               SET("准确率", ROUND(MUL(DIV(V("裸分"), V("满分总分")), 100)))),
        IFELSE(ANDn(GE(V("准确率"), 98), EQ(V("档Miss数"), 0)), SET("评级", "S"),
               [IFELSE(GE(V("准确率"), 90), SET("评级", "A"),
                       [IFELSE(GE(V("准确率"), 75), SET("评级", "B"),
                               [IFELSE(GE(V("准确率"), 60), SET("评级", "C"),
                                       SET("评级", "F"))])])]),
        SET("结果", cat("准确率 ", V("准确率"), "% 评级 ", V("评级"),
                        " 连击 ", V("最大连击"), " Miss ", V("档Miss数"),
                        " 完成度 ", V("完成度"))),
    ]


def stage_scripts():
    return [
        [{"when_green_flag_clicked": None},
         SET("自动帧", 1), SET("结果", "五款音游复刻引擎：Phigros/PJSK/Milthm/跳舞的线/滚动的天空"),
         SHOW(), FOREVER(IF(EQ(V("自动帧"), 1), [CHG("帧计数", 1), BR("帧")]), W())],
        [RECV("重置"),
         SET("分数", 0), SET("裸分", 0), SET("连击", 0), SET("最大连击", 0),
         SET("准确率", 0), SET("评级", ""), SET("songTime", 0),
         SET("档1数", 0), SET("档2数", 0), SET("档3数", 0),
         SET("档4数", 0), SET("档5数", 0), SET("档Miss数", 0),
         SET("扫描指针", 1), SET("档位", 0), SET("全屏判定", 0),
         SET("候选窗口", 300),
         SET("活跃雨丝", 0), SET("屏上手指", 0), SET("检查点", 0),
         SET("失败数", 0), SET("完成度", 0), SET("腾空", 0),
         SET("Ξ数", 0), SET("闪电HP", 3), SET("闪电Exact", 0), SET("闪电Miss", 0),
         SET("结果", "已重置")],
    ]


project = {
    "project": {
        "name": "五款代表作音游复刻引擎（Phigros / PJSK / Milthm / 跳舞的线 / 滚动的天空）",
        "stage": {
            "backdrops": [{"name": "舞台", "asset": "assets/uikit/bg_menu.svg"}],
            "variables": STAGE_VARS,
            "lists": STAGE_LISTS,
            "scripts": stage_scripts(),
        },
        "sprites": [
            {"name": "裁判", "x": 0, "y": 0,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [mode_script(), phigros_util_script(), line_eval_script(),
                         phigros_judge_script(), pjsk_judge_script(),
                         pjsk_tail_script(), milthm_judge_script(),
                         milthm_lightning_script(), milthm_water_script(),
                         dancing_script(), rolling_script(), result_script(),
                         [{"when_green_flag_clicked": None}, HIDE()]]},
            {"name": "显示板", "x": -226, "y": 166,
             "costumes": [{"name": "dot", "asset": "assets/dot.svg"}],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, GOTO(-226, 166), SETSIZE(60), SHOW()],
                 [RECV("帧"), {"looks_say": {"MESSAGE": V("结果")}}],
             ]},
        ],
    }
}

if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False)
    print("IR 已写出:", OUT, " 角色数=", len(project["project"]["sprites"]))
