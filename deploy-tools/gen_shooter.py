#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成纵版射击（Shmup）示例 shooter.yaml（用 yaml.dump，避免手写 YAML 踩坑）。

设计要点见 references/shooter-games.md。
关键决策：碰撞用「位置数学（AABB）+ 列表追踪」，不用 touching——
这样行为校验能在无头 scratch-vm 里真实验证碰撞逻辑（touching 依赖渲染器，
无头环境测不到，见 SKILL.md「无头盲区」）。

用法: python gen_shooter.py [输出yaml路径]
"""
import os
import sys
import yaml

ROOT = os.getcwd()
ASSET_DIR = os.path.join(ROOT, "examples", "assets", "shooter")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "shooter.yaml")

V = lambda n: {"var": n}
SET = lambda v, x: {"set_variable": {"var": v, "value": x}}
CHG = lambda v, d: {"change_variable": {"var": v, "by": d}}
IF = lambda c, *d: {"if": {"cond": c, "do": list(d)}}
IFE = IF
IFE_ELSE = lambda c, d, e: {"if_else": {
    "cond": c, "do": d if isinstance(d, list) else [d],
    "else": e if isinstance(e, list) else [e]}}
BR = lambda m: {"broadcast": {"message": m}}
RECV = lambda m: {"when_receive": {"message": m}}
W = lambda: {"wait": {"secs": 0.02}}  # 每帧节流：让无头逐步推进时每步恰好跑一次身体，行为可精确验证
GT = lambda a, b: {"gt": [a, b]}
LT = lambda a, b: {"lt": [a, b]}
EQ = lambda a, b: {"equals": [a, b]}
NEQ = lambda a, b: {"not": {"operand": {"equals": [a, b]}}}
AND = lambda a, b: {"and": [a, b]}
AND3 = lambda a, b, c: {"and": [a, {"and": [b, c]}]}
KEY = lambda k: {"key_pressed": {"key": k}}
WHENKEY = lambda k: {"when_key_pressed": {"key": k}}
GOTO = lambda x, y: {"goto_xy": {"x": x, "y": y}}
CHX = lambda d: {"change_x": {"dx": d}}
SETX = lambda x: {"set_x": {"x": x}}
RAND = lambda a, b: {"random": {"from": a, "to": b}}
ITEM = lambda lst, idx: {"item_of_list": {"list": lst, "index": idx}}
REP = lambda lst, idx, val: {"replace_item_of_list": {"list": lst, "index": idx, "item": val}}
DEL = lambda: {"delete_this_clone": None}
CLONE = lambda: {"create_clone_of": {"clone": "_myself_"}}


def _v(x):
    if isinstance(x, str):
        return {"var": x}
    return x


def SUB(a, b):
    return {"subtract": [_v(a), _v(b)]}


def ABS(x):
    return {"mathop": {"operator": "abs", "num": _v(x)}}


R = 18  # 命中半径（精灵约 36px，半宽 18）


def repv(var, n, *do):
    # 计数器 var 从 0 跑到 n，循环体内 var 已是 1..n
    return [SET(var, 0), {"repeat": {"times": n, "do": [CHG(var, 1), *do]}}]


# ---------- 舞台 ----------
def stage_scripts():
    return [
        # 一局开始：复位集中在这里（不挂绿旗重复触发的隐患，这里绿旗只触发一次）
        [{"when_green_flag_clicked": None},
         SET("分数", 0), SET("血量", 3), SET("游戏结束", 0),
         SET("玩家x", 0), SET("玩家y", -150), SET("__spawn", 0), SET("敌计数器", 0),
         *repv("__k", 60, REP("敌死", V("__k"), 0)),
         # 敌人生成节奏：每 20 帧生成一个（节流，避免同屏过多）
         {"forever": {"do": [
             CHG("__spawn", 1),
             IF(GT(V("__spawn"), 20),
                SET("__spawn", 0), BR("生成敌人")),
             W(),
         ]}}],
        # 游戏结束：血量见底 → 置标志
        [RECV("结束"), SET("游戏结束", 1)],
    ]


# ---------- 玩家 ----------
def player_scripts():
    return [
        [{"when_green_flag_clicked": None}, GOTO(0, -150), {"show": None}],
        # 移动：左右键改「意图坐标」变量，再 set_x 同步——变量与精灵位置始终一致
        [{"when_green_flag_clicked": None}, {"forever": {"do": [
            IF(KEY("left arrow"), CHG("玩家x", -8)),
            IF(KEY("right arrow"), CHG("玩家x", 8)),
            IF(GT(V("玩家x"), 220), SET("玩家x", 220)),
            IF(LT(V("玩家x"), -220), SET("玩家x", -220)),
            SETX(V("玩家x")),
            SET("玩家y", -150),
            W(),
        ]}}],
        # 开火：空格只广播意图，子弹生成全在子弹角色
        [WHENKEY("space"), BR("发射")],
    ]


# ---------- 子弹 ----------
def bullet_scripts():
    return [
        [{"when_green_flag_clicked": None}, {"hide": None}],
        # ⚠️ 只有本体（是克隆=0）才生成克隆；否则克隆也会响应本体的事件帽子 → 指数爆炸
        [RECV("发射"), IF(EQ(V("是克隆"), 0), CLONE())],
        [{"when_start_as_clone": None},
         SET("是克隆", 1),
         SET("bx", V("玩家x")), SET("by", V("玩家y")),
         GOTO(V("bx"), V("by")), {"show": None}],
        [{"when_start_as_clone": None}, {"forever": {"do": [
            CHG("by", 10),                       # 向上飞
            GOTO(V("bx"), V("by")),
            IF(GT(V("by"), 180), DEL()),        # 出界回收
            # 列表追踪碰撞：遍历敌x/敌y，命中则在敌死列表打标记（由敌人自己删自己，race-free）
            SET("敌序", 0),
            {"repeat": {"times": V("敌计数器"), "do": [
                CHG("敌序", 1),
                IF(AND3(EQ(ITEM("敌死", V("敌序")), 0),
                        LT(ABS(SUB(V("bx"), ITEM("敌x", V("敌序")))), R),
                        LT(ABS(SUB(V("by"), ITEM("敌y", V("敌序")))), R)),
                   CHG("分数", 1), REP("敌死", V("敌序"), 1)),
            ]}},
            W(),
        ]}}],
    ]


# ---------- 敌人 ----------
def enemy_scripts():
    return [
        [{"when_green_flag_clicked": None}, {"hide": None}],
        # ⚠️ 同样只有本体生成克隆；并给每个敌人一个唯一编号写入列表。
        # 注意：这里拆成两个「单分支 IF」，避免「嵌套 IF 的 do 里放 CLONE」被 builder 漏编译。
        [RECV("生成敌人"),
         IF(AND(EQ(V("是克隆"), 0), LT(V("敌计数器"), 60)), CHG("敌计数器", 1)),
         IF(AND(EQ(V("是克隆"), 0), LT(V("敌计数器"), 60)), CLONE())],
        [{"when_start_as_clone": None},
         SET("是克隆", 1),
         SET("编号", V("敌计数器")),
         SET("ex", RAND(-200, 200)), SET("ey", 170),
         REP("敌x", V("编号"), V("ex")), REP("敌y", V("编号"), V("ey")),
         REP("敌死", V("编号"), 0),
         GOTO(V("ex"), V("ey")), {"show": None}],
        [{"when_start_as_clone": None}, {"forever": {"do": [
            CHG("ey", -2),                      # 向下落
            GOTO(V("ex"), V("ey")),
            REP("敌x", V("编号"), V("ex")), REP("敌y", V("编号"), V("ey")),  # 实时刷新列表
            IF(LT(V("ey"), -180), DEL()),       # 出界回收
            IF(EQ(ITEM("敌死", V("编号")), 1), DEL()),  # 被子弹打中 → 删自己
            # 撞玩家：扣血，血量见底广播结束
            IF(AND(LT(ABS(SUB(V("ex"), V("玩家x"))), R),
                   LT(ABS(SUB(V("ey"), V("玩家y"))), R)),
               CHG("血量", -1), REP("敌死", V("编号"), 1),
               IF(LT(V("血量"), 1), BR("结束")), DEL()),
            W(),
        ]}}],
    ]


def gen_assets():
    try:
        from PIL import Image, ImageDraw
    except Exception as e:
        print("⚠ PIL 不可用，跳过素材生成:", e)
        return
    os.makedirs(ASSET_DIR, exist_ok=True)
    # 玩家：蓝色上三角
    img = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(20, 4), (4, 36), (36, 36)], fill=(60, 140, 240, 255),
              outline=(20, 60, 140, 255), width=3)
    img.save(os.path.join(ASSET_DIR, "player.png"))
    # 子弹：黄色小方块
    img = Image.new("RGBA", (14, 22), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([1, 1, 12, 20], fill=(250, 220, 60, 255), outline=(160, 120, 0, 255), width=2)
    img.save(os.path.join(ASSET_DIR, "bullet.png"))
    # 敌人：紫色圆
    img = Image.new("RGBA", (34, 34), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, 31, 31], fill=(200, 80, 200, 255), outline=(120, 20, 120, 255), width=3)
    img.save(os.path.join(ASSET_DIR, "enemy.png"))
    print("素材已生成:", os.listdir(ASSET_DIR))


def build():
    project = {
        "project": {
            "name": "纵版射击",
            "stage": {
                "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
                "variables": {
                    "分数": 0, "血量": 3, "游戏结束": 0,
                    "玩家x": 0, "玩家y": -150, "敌计数器": 0, "__spawn": 0, "__k": 0,
                },
                "lists": {
                    "敌x": [0] * 60, "敌y": [0] * 60, "敌死": [0] * 60,
                },
                "scripts": stage_scripts(),
            },
            "sprites": [
                {"name": "玩家", "x": 0, "y": -150,
                 "costumes": [{"name": "造型1", "asset": "assets/shooter/player.png"}],
                 "variables": {}, "scripts": player_scripts()},
                {"name": "子弹", "x": 0, "y": 0,
                 "costumes": [{"name": "造型1", "asset": "assets/shooter/bullet.png"}],
                 "variables": {"是克隆": 0, "bx": 0, "by": 0, "敌序": 0},
                 "scripts": bullet_scripts()},
                {"name": "敌人", "x": 0, "y": 0,
                 "costumes": [{"name": "造型1", "asset": "assets/shooter/enemy.png"}],
                 "variables": {"是克隆": 0, "ex": 0, "ey": 0, "编号": 0},
                 "scripts": enemy_scripts()},
            ],
        }
    }
    return project


if __name__ == "__main__":
    gen_assets()
    proj = build()
    with open(OUT, "w", encoding="utf-8") as f:
        # default_flow_style=False：强制列表用块式（每行一个 - 元素）。
        # 否则 [0]*60 会被写成行内流式的 [0,0,...]，builder 会误当成「逗号拼接的变量」而非真正的列表。
        yaml.safe_dump(proj, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT)
