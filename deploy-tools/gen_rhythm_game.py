#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《音游判定台》示例 rhythm_game.yaml（第三十八册 §433–§456）。

这是一个「输入 → 输出」的纯判定引擎，可以拿已知答案硬校验：
  1. BPM / 拍长 / 十六分 / 三连音数学
  2. 谱面生成（BPM 网格 × pattern → 五条平行列表）
  3. 判定函数（帧量化 / 校准 / abs / 四档边界 / 找最近 / 去重）
  4. 漏击扫描（扫描指针，O(n)）
  5. 长按头尾两次判定
  6. 分数 / 连击 / 准确率 / 评级

★ 核心约束：全工程只有一个时间源 songTime；音符位置由 (目标 - songTime) 公式算，
  绝不每帧 y +=。判定窗口是「帧长的整数倍」，因为 Scratch 30fps ≈ 33ms/帧，
  ±30ms 的 Perfect 窗口物理上不可实现（§435）。

机制说明见 references/rhythm-games.md（第三十八册 §433–§456）。

用法: python gen_rhythm_game.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "rhythm_game.yaml")


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

# ------------------------------------------------------------------ 变量
STAGE_VARS = {
    "结果": "", "帧计数": 0, "自动帧": 1,
    # 唯一时钟
    "BPM": 120, "拍长ms": 500, "十六分ms": 125, "三连音ms": 167,
    "谱面偏移ms": 0, "校准ms": 0, "帧长ms": 33,
    "songTime": 0, "输入时刻": 0, "有效时刻": 0,
    "误差": 0, "绝对误差": 0, "临时": 0,
    # 判定窗口（帧长整数倍）
    "窗口P": 33, "窗口G": 66, "窗口Good": 99, "窗口Miss": 132,
    # 判定
    "判定档": 0, "判定词": "", "当前轨道": 0, "最近索引": 0, "最近误差": 0,
    "i": 0, "j": 0, "小节": 0, "位": 0, "格值": 0, "临时时刻": 0,
    # 计分
    "分数": 0, "裸分": 0, "加成连击": 0, "连击": 0, "最大连击": 0,
    "准确率": 0, "评级": "", "满分总分": 0, "单音符满分": 300,
    "档P数": 0, "档G数": 0, "档Good数": 0, "档Miss数": 0,
    # 谱面 / 扫描
    "音符数": 0, "轨道数": 4, "小节数": 2, "扫描指针": 1,
    # 长按
    "长按索引": 0, "抬手时刻": 0, "尾时刻": 0, "长按结果": "",
}

# 一小节 16 个十六分位：0=空，1..4=轨道，24 表示 2 轨+4 轨同时押（示教用简化为 2）
STAGE_LISTS = {
    "音符时刻": [0] * 48,
    "音符轨道": [0] * 48,
    "音符类型": [0] * 48,       # 1 tap / 2 hold / 3 flick
    "音符时长": [0] * 48,       # hold 尾巴 ms
    "已判定": [0] * 48,         # 0 未判 / 1P 2G 3Good 4Miss / 5 长按头已接
    "误差表": [0] * 48,
    "判定档表": [0] * 48,
    "谱面格": [1, 0, 2, 0, 3, 0, 4, 0, 1, 0, 2, 0, 3, 0, 4, 0],
    "输入队列": [0],
}


# ------------------------------------------------------------------ 1. BPM 数学
def bpm_script():
    """§437：拍长 = 60000/BPM；窗口一律取帧长整数倍（§435）。"""
    return [
        RECV("算BPM"),
        SET("拍长ms", ROUND(DIV(60000, V("BPM")))),
        SET("十六分ms", ROUND(DIV(V("拍长ms"), 4))),
        SET("三连音ms", ROUND(DIV(V("拍长ms"), 3))),
        SET("窗口P", V("帧长ms")),
        SET("窗口G", MUL(V("帧长ms"), 2)),
        SET("窗口Good", MUL(V("帧长ms"), 3)),
        SET("窗口Miss", MUL(V("帧长ms"), 4)),
        SET("结果", cat("BPM ", V("BPM"), " → 拍 ", V("拍长ms"),
                        "ms / 16分 ", V("十六分ms"), "ms / 三连音 ", V("三连音ms"),
                        "ms / 窗口 ", V("窗口P"), "-", V("窗口G"), "-",
                        V("窗口Good"), "-", V("窗口Miss"))),
    ]


# ------------------------------------------------------------------ 2. 谱面生成
def chart_script():
    """§438：BPM 网格 × pattern → 五条平行列表，时刻升序。

    ★ 谱面偏移ms 加在目标时刻里；校准ms 只作用于输入侧（§446），两者绝不合并。
    """
    return [
        RECV("生成谱面"),
        DELALL("音符时刻"), DELALL("音符轨道"), DELALL("音符类型"),
        DELALL("音符时长"), DELALL("已判定"), DELALL("误差表"),
        DELALL("判定档表"),
        SET("音符数", 0), SET("扫描指针", 1),
        *repv("小节", V("小节数"), *[
            *repv("位", 16, *[
                SET("格值", ITEM("谱面格", V("位"))),
                IF(GT(V("格值"), 0), *[
                    SET("临时时刻", ADD(V("谱面偏移ms"),
                                        ADD(MUL(SUB(V("小节"), 1), MUL(4, V("拍长ms"))),
                                            MUL(SUB(V("位"), 1), V("十六分ms"))))),
                    LADD("音符时刻", V("临时时刻")),
                    LADD("音符轨道", V("格值")),
                    LADD("音符类型", 1),
                    LADD("音符时长", 0),
                    LADD("已判定", 0),
                    LADD("误差表", 0),
                    LADD("判定档表", 0),
                    CHG("音符数", 1),
                ]),
            ]),
        ]),
        SET("结果", cat("谱面生成 ", V("音符数"), " 个音符 / 小节数 ", V("小节数"))),
    ]


# ------------------------------------------------------------------ 3. 判定（核心纯函数）
def judge_script():
    """§441/§442：量化 → 找最近未判定音符 → 四档 → 计分 → 去重。

    ★ 用 IFELSE 链而不是一串平级 IF：档位互斥，平级 IF 会互相覆盖（项目实踩）。
    ★ 空击（无候选）不判 Miss、不断连击。
    """
    return [
        RECV("判一击"),
        # ① 校准只减在输入侧；② 先按帧长量化，再取误差
        SET("有效时刻", SUB(V("输入时刻"), V("校准ms"))),
        SET("有效时刻", MUL(ROUND(DIV(V("有效时刻"), V("帧长ms"))), V("帧长ms"))),
        # 找最近（带 窗口Miss 剪枝）
        SET("最近索引", 0), SET("最近误差", 999999),
        *repv("i", V("音符数"), *[
            SET("临时", ABS(SUB(V("有效时刻"), ITEM("音符时刻", V("i"))))),
            IF(ANDn(EQ(ITEM("音符轨道", V("i")), V("当前轨道")),
                    EQ(ITEM("已判定", V("i")), 0),
                    LE(V("临时"), V("窗口Miss")),
                    LT(V("临时"), V("最近误差"))),
               [SET("最近误差", V("临时")), SET("最近索引", V("i"))]),
        ]),
        IFELSE(EQ(V("最近索引"), 0),
               [SET("判定档", 0), SET("判定词", "空击"),
                SET("结果", "空击：不判不计分、不断连击")],
               [
                   SET("误差", SUB(V("有效时刻"), ITEM("音符时刻", V("最近索引")))),
                   SET("绝对误差", ABS(V("误差"))),
                   REP("误差表", V("最近索引"), V("误差")),
                   # 长按头：只接住，不结算（§444）
                   IFELSE(EQ(ITEM("音符类型", V("最近索引")), 2),
                          [SET("判定档", 5), SET("判定词", "长按头已接"),
                           REP("已判定", V("最近索引"), 5),
                           SET("结果", "长按头已接，等抬手判尾")],
                          [
                              # 四档：全部用 ≤ 边界
                              IFELSE(LE(V("绝对误差"), V("窗口P")), SET("判定档", 1),
                                     [IFELSE(LE(V("绝对误差"), V("窗口G")), SET("判定档", 2),
                                             [IFELSE(LE(V("绝对误差"), V("窗口Good")),
                                                     SET("判定档", 3), SET("判定档", 4))])]),
                              REP("已判定", V("最近索引"), V("判定档")),
                              REP("判定档表", V("最近索引"), V("判定档")),
                              # 计分：裸分用于准确率，分数含连击加成（§447）
                              SET("临时", 0),
                              IFELSE(EQ(V("判定档"), 1),
                                     [SET("临时", 300), CHG("档P数", 1), CHG("连击", 1),
                                      SET("判定词", "PERFECT")],
                                     [IFELSE(EQ(V("判定档"), 2),
                                             [SET("临时", 200), CHG("档G数", 1), CHG("连击", 1),
                                              SET("判定词", "GREAT")],
                                             [IFELSE(EQ(V("判定档"), 3),
                                                     [SET("临时", 100), CHG("档Good数", 1),
                                                      CHG("连击", 1), SET("判定词", "GOOD")],
                                                     [SET("临时", 0), CHG("档Miss数", 1),
                                                      SET("连击", 0), SET("判定词", "MISS")])])]),
                              CHG("裸分", V("临时")),
                              SET("加成连击", V("连击")),
                              IF(GT(V("加成连击"), 100), SET("加成连击", 100)),
                              CHG("分数", ROUND(MUL(V("临时"),
                                                    ADD(1, MUL(DIV(V("加成连击"), 100), 0.5))))),
                              IF(GT(V("连击"), V("最大连击")), SET("最大连击", V("连击"))),
                              SET("结果", cat(V("判定词"), " 误差 ", V("误差"),
                                              "ms / 档 ", V("判定档"),
                                              " / COMBO ", V("连击"))),
                          ]),
               ]),
    ]


# ------------------------------------------------------------------ 4. 漏击扫描
def miss_script():
    """§443：扫描指针只前进，复杂度 O(n)，不是每帧全表扫。"""
    return [
        RECV("推进"),
        REPEAT_UNTIL(ORn(GT(V("扫描指针"), V("音符数")),
                         LE(V("songTime"),
                            ADD(ITEM("音符时刻", V("扫描指针")), V("窗口Miss")))), *[
            IF(EQ(ITEM("已判定", V("扫描指针")), 0), *[
                REP("已判定", V("扫描指针"), 4),
                REP("判定档表", V("扫描指针"), 4),
                CHG("档Miss数", 1),
                SET("连击", 0),
            ]),
            CHG("扫描指针", 1),
        ]),
        SET("结果", cat("推进到 ", V("songTime"), "ms / Miss ", V("档Miss数"),
                        " / 指针 ", V("扫描指针"))),
    ]


# ------------------------------------------------------------------ 5. 长按抬手
def hold_script():
    """§444：长按判两次。抬手太早或太晚都失败，不能只按一下就满分。"""
    return [
        RECV("长按抬手"),
        SET("长按结果", ""),
        IFELSE(NEQ(ITEM("已判定", V("长按索引")), 5),
               [SET("长按结果", "没有接住的头，长按无效")],
               [
                   SET("尾时刻", ADD(ITEM("音符时刻", V("长按索引")),
                                    ITEM("音符时长", V("长按索引")))),
                   SET("误差", SUB(V("抬手时刻"), V("尾时刻"))),
                   SET("绝对误差", ABS(V("误差"))),
                   IFELSE(LE(V("绝对误差"), V("窗口Good")),
                          [
                              REP("已判定", V("长按索引"), 1),
                              REP("判定档表", V("长按索引"), 1),
                              CHG("裸分", 300), CHG("分数", 300),
                              CHG("档P数", 1), CHG("连击", 1),
                              IF(GT(V("连击"), V("最大连击")), SET("最大连击", V("连击"))),
                              SET("长按结果", "长按成功"),
                          ],
                          [
                              REP("已判定", V("长按索引"), 4),
                              REP("判定档表", V("长按索引"), 4),
                              CHG("档Miss数", 1), SET("连击", 0),
                              SET("长按结果", "长按失败（抬手太早/太晚）"),
                          ]),
               ]),
        SET("结果", cat(V("长按结果"), " / 误差 ", V("误差"), "ms")),
    ]


# ------------------------------------------------------------------ 6. 结算
def result_script():
    """§447：准确率用「未加成裸分」，否则跨曲不可比；评级 + 全连。"""
    return [
        RECV("结算"),
        SET("满分总分", MUL(V("单音符满分"), V("音符数"))),
        IFELSE(EQ(V("满分总分"), 0),
               SET("准确率", 0),
               SET("准确率", ROUND(MUL(DIV(V("裸分"), V("满分总分")), 100)))),
        IFELSE(ANDn(GE(V("准确率"), 98), EQ(V("档Miss数"), 0)), SET("评级", "S"),
               [IFELSE(GE(V("准确率"), 90), SET("评级", "A"),
                       [IFELSE(GE(V("准确率"), 75), SET("评级", "B"),
                               [IFELSE(GE(V("准确率"), 60), SET("评级", "C"),
                                       SET("评级", "D"))])])]),
        SET("结果", cat("准确率 ", V("准确率"), "% / 评级 ", V("评级"),
                        " / 分数 ", V("分数"), " / 最大COMBO ", V("最大连击"),
                        " / P", V("档P数"), " G", V("档G数"),
                        " Good", V("档Good数"), " Miss", V("档Miss数"))),
    ]


# ------------------------------------------------------------------ 7. 舞台
def stage_scripts():
    return [
        [{"when_green_flag_clicked": None},
         SET("自动帧", 1), SET("结果", "音游判定台：BPM / 谱面 / 判定 / 长按 / 结算"),
         SHOW(),
         FOREVER(IF(EQ(V("自动帧"), 1), [CHG("帧计数", 1), BR("帧")]), W())],
        [RECV("重置"),
         SET("分数", 0), SET("裸分", 0), SET("连击", 0), SET("最大连击", 0),
         SET("准确率", 0), SET("评级", ""),
         SET("档P数", 0), SET("档G数", 0), SET("档Good数", 0), SET("档Miss数", 0),
         SET("songTime", 0), SET("扫描指针", 1), SET("判定档", 0),
         SET("长按索引", 0), SET("加成连击", 0),
         SET("结果", "已重置")],
    ]


project = {
    "project": {
        "name": "音游判定台（BPM / 谱面 / 判定 / 长按 / 结算）",
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
             "scripts": [bpm_script(), chart_script(), judge_script(),
                         miss_script(), hold_script(), result_script(),
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
