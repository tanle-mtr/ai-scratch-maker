#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《UI Kit 演示》示例 ui_kit_demo.yaml。

用 gen_ui_kit.py 产出的矢量素材拼一屏真实界面，演示三件事：
1. 按钮的 hover / pressed 反馈（换造型，不是缩放）
2. 弹窗的四件套（遮罩 + 面板 + 关闭键 + 内容）与开关流程
3. 进度条换档（10 档图，不拉伸）

素材来源：examples/assets/uikit/（先跑 `python scripts/gen_ui_kit.py`）

用法: python gen_ui_kit_demo.py [输出yaml路径]
"""
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from ir_helpers import *

ROOT = os.getcwd()
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "ui_kit_demo.yaml")
A = "assets/uikit/"


def cos(name, asset, size=None):
    c = {"name": name, "asset": A + asset}
    if size is not None:
        c["size"] = size
    return c


def SWITCH(name):
    return {"looks_switchcostumeto": {"COSTUME": name}}


def PLAY(name):
    """播放声音（不等待）。UI 音一律用它，不要用「直到结束」（会阻塞脚本）。"""
    return {"sound_play": {"SOUND_MENU": name}}


def snd(name):
    return {"name": name, "asset": "assets/audio/%s.wav" % name}


def TOUCH_MOUSE():
    return {"touching": {"object": "_mouse_"}}


def MOUSEDOWN():
    return {"sensing_mousedown": None}


def SHOW():
    return {"show": None}


def HIDE():
    return {"hide": None}


STAGE_VARS = {
    "弹窗": 0,          # 0 关 / 1 开（所有按钮的 hover 都要看它）
    "血量": 100,
    "档": 100,
    "自动帧": 1,
    "帧计数": 0,
}


# ------------------------------------------------------------------ 按钮
def button_scripts(kind, size, click_msg, label_w=0):
    """一个按钮 = 三个造型（normal/hover/pressed） + 三条平级判定。

    ⚠️ 三条 IF 必须平级，不能嵌套：后写的覆盖先写的，
       所以顺序是 pressed → hover → normal（兜底）。
    """
    n = "%s_normal_%s" % (kind, size)
    h = "%s_hover_%s" % (kind, size)
    p = "%s_pressed_%s" % (kind, size)
    scripts = [
        [{"when_green_flag_clicked": None}, SHOW(), SWITCH(n)],
        [RECV("帧"),
         IF(ANDn(EQ(V("弹窗"), 0), TOUCH_MOUSE(), MOUSEDOWN()), SWITCH(p)),
         IF(ANDn(EQ(V("弹窗"), 0), TOUCH_MOUSE(), NEQ(MOUSEDOWN(), True)), SWITCH(h)),
         IF(ORn(EQ(V("弹窗"), 1), NEQ(TOUCH_MOUSE(), True)), SWITCH(n))],
    ]
    if click_msg:
        # 音效绑在「点击当帧」：等视觉反馈完再响，听感会「卡」
        scripts.append([{"when_this_sprite_clicked": None},
                        IF(EQ(V("弹窗"), 0), [PLAY("ui_click"), BR(click_msg)])])
    return scripts


def modal_group_scripts():
    """弹窗组：绿旗隐藏，开设置时显示，关设置时隐藏。"""
    return [
        [{"when_green_flag_clicked": None}, HIDE()],
        [RECV("开设置"), SHOW()],
        [RECV("关设置"), HIDE()],
    ]


def hp_bar_scripts():
    """血条：血量降到 5 就回满；按 10 档换造型（不拉伸）。"""
    return [
        [{"when_green_flag_clicked": None}, SHOW(), SWITCH("bar_hp_100")],
        [RECV("帧"),
         IF(EQ(V("弹窗"), 0), CHG("血量", -0.5)),
         IF(LT(V("血量"), 5), SET("血量", 100)),
         SET("档", MUL(ROUND(DIV(V("血量"), 10)), 10)),
         IFELSE(GE(V("档"), 100),
                SWITCH("bar_hp_100"),
                SWITCH(JOIN("bar_hp_0", V("档"))))],
        [RECV("重开"), SET("血量", 100)],
    ]


def stage_scripts():
    return [
        [{"when_green_flag_clicked": None},
         SET("自动帧", 1), SET("弹窗", 0), SET("血量", 100), SET("档", 100),
         SET("帧计数", 0),
         SHOW(),
         FOREVER(IF(EQ(V("自动帧"), 1), [CHG("帧计数", 1), BR("帧")]), W())],
        # 事件音跟状态同帧：开门/关门用 ev 层（−3 dBFS），不要用 ui_click 顶替
        [RECV("开设置"), SET("弹窗", 1), PLAY("ev_open")],
        [RECV("关设置"), SET("弹窗", 0), PLAY("ev_close")],
        [RECV("重开"), SET("血量", 100)],
    ]


project = {
    "project": {
        "name": "UI Kit 演示（矢量素材 + 四状态按钮 + 弹窗 + 进度条）",
        "stage": {
            "backdrops": [{"name": "菜单背景", "asset": A + "bg_menu.svg"}],
            "variables": STAGE_VARS,
            "lists": {},
            "scripts": stage_scripts(),
        },
        "sprites": [
            # ---------------- 菜单层（在弹窗下面）----------------
            {"name": "血条", "x": -168, "y": 158,
             "costumes": [cos("bar_hp_100", "bar_hp_100.svg")] +
                         [cos("bar_hp_0%02d" % p, "bar_hp_0%02d.svg" % p)
                          for p in range(10, 100, 10)] +
                         [cos("bar_hp_000", "bar_hp_000.svg")],
             "size": 70, "variables": {}, "scripts": hp_bar_scripts()},

            {"name": "星级", "x": -168, "y": 126, "size": 70,
             "costumes": [cos("stars", "badge_stars.svg")],
             "variables": {},
             "scripts": [[{"when_green_flag_clicked": None}, SHOW()]]},

            {"name": "缎带", "x": 0, "y": 112,
             "costumes": [cos("ribbon", "decor_ribbon.svg")],
             "variables": {},
             "scripts": [[{"when_green_flag_clicked": None}, SHOW()]]},

            {"name": "标题文字", "x": 0, "y": 112,
             "costumes": [cos("title", "text_开始游戏_30_d.png")],
             "variables": {},
             "scripts": [[{"when_green_flag_clicked": None}, SHOW()]]},

            {"name": "主按钮", "x": 0, "y": 20,
             "costumes": [cos("primary_normal_l", "btn_primary_normal_l.svg"),
                          cos("primary_hover_l", "btn_primary_hover_l.svg"),
                          cos("primary_pressed_l", "btn_primary_pressed_l.svg")],
             "variables": {}, "scripts": button_scripts("primary", "l", "重开")},

            {"name": "主按钮文字", "x": 0, "y": 20,
             "costumes": [cos("t", "text_开始游戏_20_d.png")],
             "variables": {},
             "scripts": [[{"when_green_flag_clicked": None}, SHOW()]]},

            {"name": "设置按钮", "x": -100, "y": -60,
             "costumes": [cos("secondary_normal_m", "btn_secondary_normal_m.svg"),
                          cos("secondary_hover_m", "btn_secondary_hover_m.svg"),
                          cos("secondary_pressed_m", "btn_secondary_pressed_m.svg")],
             "variables": {}, "scripts": button_scripts("secondary", "m", "开设置")},

            {"name": "设置按钮文字", "x": -100, "y": -60,
             "costumes": [cos("t", "text_设置_17_d.png")],
             "variables": {},
             "scripts": [[{"when_green_flag_clicked": None}, SHOW()]]},

            {"name": "退出按钮", "x": 100, "y": -60,
             "costumes": [cos("ghost_normal_m", "btn_ghost_normal_m.svg"),
                          cos("ghost_hover_m", "btn_ghost_hover_m.svg"),
                          cos("ghost_pressed_m", "btn_ghost_pressed_m.svg")],
             "variables": {}, "scripts": button_scripts("ghost", "m", "关设置")},

            {"name": "退出按钮文字", "x": 100, "y": -60,
             "costumes": [cos("t", "text_退出_17_l.png")],
             "variables": {},
             "scripts": [[{"when_green_flag_clicked": None}, SHOW()]]},

            {"name": "提示条", "x": 0, "y": -132,
             "costumes": [cos("tip", "panel_tip.svg")],
             "variables": {},
             "scripts": [[{"when_green_flag_clicked": None}, SHOW()]]},

            {"name": "提示文字", "x": 0, "y": -132,
             "costumes": [cos("t", "text_恭喜通关_22_d.png")],
             "variables": {},
             "scripts": [[{"when_green_flag_clicked": None}, SHOW()]]},

            # ---------------- 弹窗层（盖住菜单）----------------
            {"name": "遮罩", "x": 0, "y": 0,
             "costumes": [cos("mask", "decor_mask.svg")],
             "variables": {}, "scripts": modal_group_scripts()},

            {"name": "设置窗", "x": 0, "y": 0,
             "costumes": [cos("dialog", "panel_dialog.svg")],
             "variables": {}, "scripts": modal_group_scripts()},

            {"name": "窗标题", "x": 0, "y": 76,
             "costumes": [cos("t", "text_设置_28_l.png")],
             "variables": {}, "scripts": modal_group_scripts()},

            {"name": "关闭键", "x": 188, "y": 112,
             "costumes": [cos("close", "ctrl_close.svg")],
             "variables": {},
             "scripts": modal_group_scripts() +
                        [[{"when_this_sprite_clicked": None}, BR("关设置")]]},

            {"name": "窗内按钮", "x": 0, "y": -74,
             "costumes": [cos("ok_normal_s", "btn_primary_normal_s.svg"),
                          cos("ok_hover_s", "btn_primary_hover_s.svg"),
                          cos("ok_pressed_s", "btn_primary_pressed_s.svg")],
             "variables": {},
             "scripts": [
                 [{"when_green_flag_clicked": None}, HIDE()],
                 [RECV("开设置"), SHOW()],
                 [RECV("关设置"), HIDE()],
                 [RECV("帧"),
                  IF(ANDn(EQ(V("弹窗"), 1), TOUCH_MOUSE(), MOUSEDOWN()),
                     SWITCH("ok_pressed_s")),
                  IF(ANDn(EQ(V("弹窗"), 1), TOUCH_MOUSE(), NEQ(MOUSEDOWN(), True)),
                     SWITCH("ok_hover_s")),
                  IF(ORn(EQ(V("弹窗"), 0), NEQ(TOUCH_MOUSE(), True)),
                     SWITCH("ok_normal_s"))],
                 [{"when_this_sprite_clicked": None},
                  IF(EQ(V("弹窗"), 1), BR("关设置"))],
             ]},

            {"name": "窗内按钮文字", "x": 0, "y": -74,
             "costumes": [cos("t", "text_继续_16_d.png")],
             "variables": {}, "scripts": modal_group_scripts()},
        ],
    }
}


# ------------------------------------------------------------------ 音效挂载
# Scratch 的声音是「角色级」的：同一个音效文件要挂在会播它的角色身上。
# 这里统一后处理，避免每个角色定义里重复写 sounds 字段。
_BTN_SOUNDS = ("主按钮", "设置按钮", "退出按钮", "关闭键", "窗内按钮")
for _sp in project["project"]["sprites"]:
    if _sp["name"] in _BTN_SOUNDS:
        _sp["sounds"] = [snd("ui_click")]
# 事件音挂舞台：开/关窗是「场景级事件」，不属于某个按钮
project["project"]["stage"]["sounds"] = [snd("ev_open"), snd("ev_close")]


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False)
    print("IR 已写出:", OUT, " 角色数=", len(project["project"]["sprites"]))
