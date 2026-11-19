#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成三消（Match-3）示例的 IR：棋盘匹配 / 交换 / 消除 / 下落 / 连锁 / 计分。
同时生成 5 张水果造型素材（果1~果4 + 空），输出到 examples/assets/match3/。
用法: python deploy-tools/gen_match3.py [输出yaml路径]
"""
import os, sys, yaml

# 以「当前工作目录」（即正在构建的 skill 副本）为基准，
# 这样素材与 IR 都落在同一副本内，避免跨目录找不到。
ROOT = os.getcwd()
ASSET_DIR = os.path.join(ROOT, "examples", "assets", "match3")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "examples", "match3.yaml")

# ---------- IR 小工具 ----------
def setv(var, val):       return {"set_variable": {"var": var, "value": val}}
def rep(times, *do):      return {"repeat": {"times": times, "do": list(do)}}
def repv(var, n, *do):    # 计数器 var 从 1 跑到 n
    return [setv(var, 0), rep(n, setv(var, {"add": [{"var": var}, 1]}), *do)]
def ife(cond, *do):       return {"if": {"cond": cond, "do": list(do)}}
def ife_else(cond, do, el):
    if not isinstance(do, list): do = [do]
    if not isinstance(el, list): el = [el]
    return {"if_else": {"cond": cond, "do": do, "else": el}}
def br(msg):              return {"broadcast": {"message": msg}}
def recv(msg):            return {"when_receive": {"message": msg}}
def call(proc, args=None):return {"call": {"proc": proc, "args": args or []}}
def item(lst, idx):       return {"item_of_list": {"list": lst, "index": idx}}
def replace(lst, idx, v): return {"replace_item_of_list": {"list": lst, "index": idx, "item": v}}
def eq(a, b):             return {"equals": [a, b]}
def neq(a, b):            return {"not": {"operand": {"equals": [a, b]}}}
def gt(a, b):             return {"greater_than": {"a": a, "b": b}}
def lt(a, b):             return {"less_than": {"a": a, "b": b}}
def rand(a, b):           return {"random": {"from": a, "to": b}}
def _v(x):
    # 裸字符串（变量名）在算术里必须包成 {"var": 名}，否则构建器会把它当成
    # 字面量字符串「r1」写进积木（[1,[4,"r1"]]），运行时读不到变量值。
    # 已经是 dict（{var:..} / 计算式）或数字则原样返回。
    if isinstance(x, str):
        return {"var": x}
    return x
def add(a, b):            return {"add": [_v(a), _v(b)]}
def sub(a, b):            return {"subtract": [_v(a), _v(b)]}
def mul(a, b):            return {"multiply": [_v(a), _v(b)]}
def div(a, b):            return {"divide": [_v(a), _v(b)]}
def floor(x):             return {"mathop": {"operator": "floor", "num": x}}
def and_(conds):          # 两输入，多于 2 个嵌套
    c = conds[0]
    for nxt in conds[1:]:
        c = {"and": [c, nxt]}
    return c
def or_(conds):
    c = conds[0]
    for nxt in conds[1:]:
        c = {"or": [c, nxt]}
    return c

# 1-based 行/列 (r1,c1 ∈ 1..6) -> 序号
def idx(r1, c1):
    return add(add(mul(sub(r1, 1), 6), sub(c1, 1)), 1)
# 0-based 行 r0 (0..5) + 1-based 列 c1 -> 序号  (下落循环里 r1 已是 0-based)
def idx0(r0, c1):
    return add(add(mul(r0, 6), sub(c1, 1)), 1)

V = lambda name: {"var": name}

# ---------- 过程：生成棋盘（保证开局无三连） ----------
def proc_gen_board():
    k = "k"; r1 = "r1"; c1 = "c1"
    # 逐格生成：每格候选值避开「会构成三连」的情况。
    # 规则：若左侧两格同色，则本格不能等于左1；若上方两格同色，则本格不能等于上1。
    # 4 种颜色下，禁止集合最多 2 个，必剩 ≥2 个合法值，所以一定能生成。
    # 用「最多重试 8 次」的方式取到合法值；填过(棋盘[k]≠0)后 accept 条件失效，停止写入。
    body = [
        *repv(k, 36, replace("棋盘", V(k), 0)),
        *repv(r1, 6,
            *repv(c1, 6,
                setv("k", idx(r1, c1)),
                setv("__l1", item("棋盘", sub(V("k"), 1))),
                setv("__l2", item("棋盘", sub(V("k"), 2))),
                setv("__u1", item("棋盘", sub(V("k"), 6))),
                setv("__u2", item("棋盘", sub(V("k"), 12))),
                rep(8,
                    setv("__cand", rand(1, 4)),
                    ife(and_([
                            eq(item("棋盘", V("k")), 0),
                            or_([neq(V("__cand"), V("__l1")), neq(V("__l1"), V("__l2"))]),
                            or_([neq(V("__cand"), V("__u1")), neq(V("__u1"), V("__u2"))]),
                        ]),
                        replace("棋盘", V("k"), V("__cand"))),
                ),
            )
        ),
    ]
    return {"name": "生成棋盘", "script": body}

# ---------- 过程：检测并消除（标记 -> 消除 -> 下落补充 -> 计分） ----------
def proc_clear():
    k = "k"; r1 = "r1"; c1 = "c1"; cnt = "cnt"
    body = [
        setv("本轮消除", 0),
        *repv(k, 36, replace("掩码", V(k), 0)),
        # 行扫描：c1 从 1 到 4，窗口 [c1, c1+1, c1+2]
        *repv(r1, 6,
            *repv(c1, 4,
                ife(and_([
                        eq(item("棋盘", idx(r1, c1)),
                           item("棋盘", add(idx(r1, c1), 1))),
                        eq(item("棋盘", idx(r1, c1)),
                           item("棋盘", add(idx(r1, c1), 2))),
                        neq(item("棋盘", idx(r1, c1)), 0),
                    ]),
                    replace("掩码", idx(r1, c1), 1),
                    replace("掩码", add(idx(r1, c1), 1), 1),
                    replace("掩码", add(idx(r1, c1), 2), 1)),
            )
        ),
        # 列扫描：r1 从 1 到 4，窗口 [r1, r1+1, r1+2] 行
        *repv(c1, 6,
            *repv(r1, 4,
                ife(and_([
                        eq(item("棋盘", idx(r1, c1)),
                           item("棋盘", add(idx(r1, c1), 6))),
                        eq(item("棋盘", idx(r1, c1)),
                           item("棋盘", add(idx(r1, c1), 12))),
                        neq(item("棋盘", idx(r1, c1)), 0),
                    ]),
                    replace("掩码", idx(r1, c1), 1),
                    replace("掩码", add(idx(r1, c1), 6), 1),
                    replace("掩码", add(idx(r1, c1), 12), 1)),
            )
        ),
        # 消除被标记格（本轮消除 = 本回合被消除的格子数）
        *repv(k, 36,
            ife(eq(item("掩码", V(k)), 1),
                replace("棋盘", V(k), 0),
                setv("本轮消除", add(V("本轮消除"), 1))),
        ),
        # 计分：每消 1 格得 10 分，并加连锁奖励（消除越多奖励越高）
        setv("分数", add(V("分数"), mul(V("本轮消除"), 10))),
        setv("分数", add(V("分数"), mul(V("本轮消除"), V("本轮消除")))),
        # 下落：仅当本回合确有消除时才做重力（收集非0到列缓存，再从底部回填，顶部补随机）。
        # 注意：本轮消除=0 时绝不能跑这一段——否则所有格子都非0，cnt 恒为 0，
        # 回填分支（p<cnt 恒假）会把整盘随机重填，破坏「交换无效换回」的棋盘。
        ife(gt(V("本轮消除"), 0),
            *repv(c1, 6,
                setv(cnt, 0),
                # 从底(r1=5)到顶(r1=0)扫描：非0 的格子存进 列缓存(1-based= cnt+1)，cnt 只在遇到0时自增
                setv(r1, 6),
                rep(6,
                    setv(r1, sub(V(r1), 1)),   # r1: 5..0
                    ife(neq(item("棋盘", idx0(r1, c1)), 0),
                        replace("列缓存", add(V(cnt), 1), item("棋盘", idx0(r1, c1))),
                        setv(cnt, add(V(cnt), 1))),
                ),
                # 回填：底部 p=0 对应 列缓存[1]，p<cnt 用缓存，否则补随机
                setv(r1, 6),
                rep(6,
                    setv(r1, sub(V(r1), 1)),   # r1: 5..0 -> p = 5-r1
                    ife(lt(sub(5, V(r1)), V(cnt)),
                        replace("棋盘", idx0(r1, c1), item("列缓存", add(sub(5, V(r1)), 1))),
                        replace("棋盘", idx0(r1, c1), rand(1, 4))),
                ),
            ),
        ),
    ]
    return {"name": "检测并消除", "script": body}

# ---------- 格子精灵：刷新本格造型 ----------
def proc_refresh_cell():
    s = "序号"
    body = []
    for v in (1, 2, 3, 4):
        body.append(ife(eq(item("棋盘", V(s)), v),
                        {"switch_costume": {"costume": str(v)}}))
    body.append(ife(eq(item("棋盘", V(s)), 0),
                    {"switch_costume": {"costume": "空"}}))
    return {"name": "刷新本格", "script": body}

# ---------- 相邻判定（选中逻辑用） ----------
def adjacent(a, b):
    # 行差 + 列差 == 1
    row_a = floor(div(sub(a, 1), 6))
    col_a = sub(sub(a, 1), mul(row_a, 6))
    row_b = floor(div(sub(b, 1), 6))
    col_b = sub(sub(b, 1), mul(row_b, 6))
    return eq(add(abs_(sub(row_a, row_b)), abs_(sub(col_a, col_b))), 1)
def abs_(x):
    return {"mathop": {"operator": "abs", "num": x}}

# ---------- 组装 IR ----------
def build():
    project = {
        "project": {
            "name": "三消游戏",
            "stage": {
                "backdrops": [{"name": "背景1", "asset": "assets/backdrop1.svg"}],
                "variables": {
                    "分数": 0, "选中": 0, "交换A": 0, "交换B": 0, "点击序号": 0,
                    "本轮消除": 0, "步数": 0,
                    "k": 0, "r1": 0, "c1": 0, "cnt": 0,
                    "__l1": 0, "__l2": 0, "__u1": 0, "__u2": 0, "__cand": 0,
                },
                "lists": {
                    "棋盘": [0] * 36,
                    "掩码": [0] * 36,
                    "列缓存": [0] * 6,
                },
                "procedures": [proc_gen_board(), proc_clear()],
                "scripts": [
                    # 绿旗自动开新局：广播 重置
                    [{"when_green_flag_clicked": None}, br("重置")],
                    # 重置：生成棋盘 -> 让格子克隆 -> 刷新
                    [recv("重置"),
                     call("生成棋盘"), br("生成棋盘克隆"), br("刷新")],
                    # 格子被点：选中 / 交换
                    [recv("格子被点"),
                     ife(eq(V("选中"), 0),
                         setv("选中", V("点击序号")),
                         ife_else(adjacent(V("选中"), V("点击序号")),
                             [setv("交换A", V("选中")), setv("交换B", V("点击序号")),
                              setv("选中", 0), br("交换并检测")],
                             setv("选中", V("点击序号"))))],
                    # 交换并检测：交换 -> 检测 -> 无效则换回 -> 刷新
                    [recv("交换并检测"),
                     setv("k", item("棋盘", V("交换A"))),
                     replace("棋盘", V("交换A"), item("棋盘", V("交换B"))),
                     replace("棋盘", V("交换B"), V("k")),
                     call("检测并消除"),
                     ife_else(eq(V("本轮消除"), 0),
                         [setv("k", item("棋盘", V("交换A"))),
                          replace("棋盘", V("交换A"), item("棋盘", V("交换B"))),
                          replace("棋盘", V("交换B"), V("k"))],
                         []),
                     setv("步数", add(V("步数"), 1)),
                     br("刷新")],
                ],
            },
            "sprites": [
                {
                    "name": "格子",
                    "x": 0, "y": 0,
                    "costumes": [
                        {"name": "1", "asset": "assets/match3/果1.png"},
                        {"name": "2", "asset": "assets/match3/果2.png"},
                        {"name": "3", "asset": "assets/match3/果3.png"},
                        {"name": "4", "asset": "assets/match3/果4.png"},
                        {"name": "空", "asset": "assets/match3/空.png"},
                    ],
                    "variables": {"序号": 0, "是克隆": 0},
                    "procedures": [proc_refresh_cell()],
                    "scripts": [
                        [{"when_green_flag_clicked": None}, {"hide": None}],
                        # 生成本体克隆 36 个（每个克隆继承本体当时的 序号）
                        [recv("生成棋盘克隆"),
                         ife_else(eq(V("是克隆"), 0),
                             [setv("序号", 0),
                              rep(36, setv("序号", add(V("序号"), 1)),
                                  {"create_clone_of": {"clone": "_myself_"}})],
                             [])],
                        # 克隆体启动：定位 + 显示 + 刷新
                        [{"when_start_as_clone": None},
                         setv("是克隆", 1),
                         setv("r1", floor(div(sub(V("序号"), 1), 6))),   # 0-based 行
                         setv("c1", sub(sub(V("序号"), 1), mul(V("r1"), 6))),  # 0-based 列
                         {"set_x": {"x": add(-150, mul(V("c1"), 60))}},
                         {"set_y": {"y": sub(150, mul(V("r1"), 60))}},
                         {"show": None},
                         call("刷新本格")],
                        # 刷新：仅克隆体更新造型
                        [recv("刷新"),
                         ife_else(eq(V("是克隆"), 1), [call("刷新本格")], [])],
                        # 点击：仅克隆体上报序号
                        [{"when_this_sprite_clicked": None},
                         ife_else(eq(V("是克隆"), 1),
                             [setv("点击序号", V("序号")), br("格子被点")],
                             [])],
                    ],
                },
            ],
        }
    }
    return project

def gen_assets():
    try:
        from PIL import Image, ImageDraw
    except Exception as e:
        print("⚠ PIL 不可用，跳过素材生成:", e)
        return
    os.makedirs(ASSET_DIR, exist_ok=True)
    colors = [(220, 70, 70), (240, 200, 60), (80, 190, 110), (90, 150, 230)]
    size = 60
    for i, col in enumerate(colors, 1):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([6, 6, size - 6, size - 6], fill=col + (255,),
                  outline=(40, 40, 40, 255), width=3)
        # 简单区分标记
        d.ellipse([size//2 - 8, size//2 - 8, size//2 + 8, size//2 + 8],
                  fill=(255, 255, 255, 200))
        img.save(os.path.join(ASSET_DIR, "果%d.png" % i))
    # 空格：淡灰透明
    img = Image.new("RGBA", (size, size), (230, 230, 230, 90))
    d = ImageDraw.Draw(img)
    d.rectangle([4, 4, size - 4, size - 4], outline=(180, 180, 180, 200), width=2)
    img.save(os.path.join(ASSET_DIR, "空.png"))
    print("素材已生成:", os.listdir(ASSET_DIR))

if __name__ == "__main__":
    gen_assets()
    proj = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        yaml.safe_dump(proj, f, allow_unicode=True, sort_keys=False)
    print("IR 已写出:", OUT)
