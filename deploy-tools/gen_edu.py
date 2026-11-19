#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成教育课件示例 edu_demo.yaml（用 yaml.dump，避免手写 YAML 踩坑）。

设计要点见 references/edu-courseware.md。
关键决策：
- 翻页/答题都走「广播 + 变量」，按钮只广播意图（不用 ask/answer，无头可验）。
- 数据可视化用「柱子克隆 + 列表驱动高度」，每根柱子把自身高度写进可见变量，
  无头 scratch-vm 也能真实验证「柱子数=数据长度、每柱高度=数据值」。
- 随堂测验复用答题范式（§106–§110）：当前答案==正确答案 才得分。

用法: python gen_edu.py [输出yaml路径]
"""
import os
import sys
import yaml

ROOT = os.getcwd()
ASSET_DIR = os.path.join(ROOT, "examples", "assets", "edu")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "edu_demo.yaml")

V = lambda n: {"var": n}
SET = lambda v, x: {"set_variable": {"var": v, "value": x}}
CHG = lambda v, d: {"change_variable": {"var": v, "by": d}}
IF = lambda c, *d: {"if": {"cond": c, "do": list(d)}}
BR = lambda m: {"broadcast": {"message": m}}
RECV = lambda m: {"when_receive": {"message": m}}
GT = lambda a, b: {"gt": [a, b]}
LT = lambda a, b: {"lt": [a, b]}
EQ = lambda a, b: {"equals": [a, b]}
ITEM = lambda lst, idx: {"item_of_list": {"list": lst, "index": idx}}
CLONE = lambda: {"create_clone_of": {"clone": "_myself_"}}
W = lambda: {"wait": {"secs": 0.02}}  # 节流，保证无头每步跑一次身体


def repv(var, n, *do):
    return [SET(var, 0), {"repeat": {"times": n, "do": [CHG(var, 1), *do]}}]


# 示例数据：5 根柱子（课件里的「某班学生成绩」之类）
DATA = [5, 8, 3, 9, 6]
PAGES = 3


# ---------- 舞台 ----------
def stage_scripts():
    return [
        # 一次打开：复位集中在这里；并广播生成柱子
        [{"when_green_flag_clicked": None},
         SET("页码", 1), SET("得分", 0), SET("当前答案", 0), SET("总页", PAGES),
         SET("正确答案", 2),  # 第 2 个选项为正确答案
         BR("生成柱子")],
        # 翻页
        [RECV("下一页"), IF(LT(V("页码"), V("总页")), CHG("页码", 1))],
        [RECV("上一页"), IF(GT(V("页码"), 1), CHG("页码", -1))],
        # 随堂测验：当前答案 == 正确答案 才得分
        [RECV("提交"), IF(EQ(V("当前答案"), V("正确答案")), CHG("得分", 1))],
    ]


# ---------- 柱子（数据可视化）----------
def bar_scripts():
    return [
        [{"when_green_flag_clicked": None}, {"hide": None}],
        # 只有本体生成克隆；编号随循环递增，克隆在创建时拷贝该值
        [RECV("生成柱子"),
         IF(EQ(V("是克隆"), 0), *repv("编号", len(DATA), CLONE()))],
        [{"when_start_as_clone": None},
         SET("是克隆", 1),
         SET("高度", ITEM("数据", V("编号"))),   # 自身高度取自数据列表
         {"show": None}],
        # 选项按钮（随堂测验）：点哪个就置对应答案
        [RECV("选项A"), SET("当前答案", 1)],
        [RECV("选项B"), SET("当前答案", 2)],
        [RECV("选项C"), SET("当前答案", 3)],
        [RECV("选项D"), SET("当前答案", 4)],
    ]


def gen_assets():
    try:
        from PIL import Image, ImageDraw
    except Exception as e:
        print("⚠ PIL 不可用，跳过素材生成:", e)
        return
    os.makedirs(ASSET_DIR, exist_ok=True)
    # 柱子：一个细高的浅蓝矩形（高度由 clone 的 高度 变量驱动缩放/位置）
    img = Image.new("RGBA", (40, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([4, 4, 36, 116], fill=(90, 160, 240, 255), outline=(30, 90, 180, 255), width=3)
    img.save(os.path.join(ASSET_DIR, "bar.png"))
    print("素材已生成:", os.listdir(ASSET_DIR))


def build():
    project = {
        "project": {
            "name": "教育课件示例",
            "stage": {
                "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
                "variables": {
                    "页码": 1, "得分": 0, "当前答案": 0, "正确答案": 2, "总页": PAGES,
                },
                # 列表必须块式声明（每行一个元素），builder 才会正确生成数组
                "lists": {"数据": list(DATA)},
                "scripts": stage_scripts(),
            },
            "sprites": [
                {"name": "柱子", "x": 0, "y": 0,
                 "costumes": [{"name": "造型1", "asset": "assets/edu/bar.png"}],
                 "variables": {"是克隆": 0, "编号": 0, "高度": 0},
                 "scripts": bar_scripts()},
            ],
        }
    }
    return project


if __name__ == "__main__":
    gen_assets()
    proj = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(proj, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print("IR 已写出:", OUT, " 数据=", DATA)
