#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ai-scratch-maker 各 gen_*.py 共用的 IR 积木 helper。

统一封装成「积木名 -> IR 字典」，避免每个生成器重复定义、也避免手写 YAML 踩坑。
所有 helper 都产出 build_sb3.py 能识别的短名 IR（见 references/blocks-spec.json 的 aliases）。
"""
V = lambda n: {"var": n}
SET = lambda v, x: {"set_variable": {"var": v, "value": x}}
CHG = lambda v, d: {"change_variable": {"var": v, "by": d}}
def _as_blocks(d):
    """允许「IF(c, [a,b,c])」式单列表传参：解开一层；多块则原样成列表。"""
    if len(d) == 1 and isinstance(d[0], list):
        return list(d[0])
    return list(d)


IF = lambda c, *d: {"if": {"cond": c, "do": _as_blocks(d)}}


def IFELSE(cond, then, els):
    """真正的 if/else。then / els 各自可以是「单个积木 dict」或「积木 dict 的 list」。
    builder 会自动把带 else 的 if 升级成 control_if_else。"""
    t = then if isinstance(then, list) else [then]
    e = els if isinstance(els, list) else [els]
    return {"if": {"cond": cond, "do": list(t), "else": list(e)}}


# 比较便捷封装
GE = lambda a, b: NEQ(LT(a, b), True)   # a >= b
LE = lambda a, b: NEQ(GT(a, b), True)   # a <= b
BR = lambda m: {"broadcast": {"message": m}}
RECV = lambda m: {"when_receive": {"message": m}}
W = lambda: {"wait": {"secs": 0.02}}  # 节流：让无头逐步推进时每步恰好跑一次身体
GT = lambda a, b: {"greater_than": [a, b]}
LT = lambda a, b: {"less_than": [a, b]}
EQ = lambda a, b: {"equals": [a, b]}
NEQ = lambda a, b: {"not": {"operand": {"equals": [a, b]}}}
AND = lambda a, b: {"and": [a, b]}
OR = lambda a, b: {"or": [a, b]}
KEY = lambda k: {"key_pressed": {"key": k}}
WHENKEY = lambda k: {"when_key_pressed": {"key": k}}
WHENCLICK = lambda: {"when_this_sprite_clicked": None}
GOTO = lambda x, y: {"goto_xy": {"x": x, "y": y}}
CHX = lambda d: {"change_x": {"dx": d}}
CHY = lambda d: {"change_y": {"dy": d}}
SETX = lambda x: {"set_x": {"x": x}}
SETY = lambda y: {"set_y": {"y": y}}
SETSIZE = lambda s: {"set_size": {"value": s}}
RAND = lambda a, b: {"random": {"from": a, "to": b}}
ITEM = lambda lst, idx: {"item_of_list": {"list": lst, "index": idx}}
REP = lambda lst, idx, val: {"replace_item_of_list": {"list": lst, "index": idx, "item": val}}
DEL = lambda: {"delete_this_clone": None}
CLONE = lambda: {"create_clone_of": {"clone": "_myself_"}}
ADD = lambda a, b: {"add": [a, b]}
SUB = lambda a, b: {"subtract": [a, b]}
MUL = lambda a, b: {"multiply": [a, b]}
DIV = lambda a, b: {"divide": [a, b]}
MOD = lambda a, b: {"mod": [a, b]}
COS = lambda x: {"mathop": {"operator": "cos", "num": x}}
SIN = lambda x: {"mathop": {"operator": "sin", "num": x}}
ABS = lambda x: {"mathop": {"operator": "abs", "num": x}}
SQRT = lambda x: {"mathop": {"operator": "sqrt", "num": x}}
ROUND = lambda x: {"round": [x]}
FOREVER = lambda *d: {"forever": {"do": _as_blocks(d)}}
REPEAT = lambda n, *d: {"repeat": {"times": n, "do": _as_blocks(d)}}
REPEAT_UNTIL = lambda c, *d: {"repeat_until": {"cond": c, "do": _as_blocks(d)}}


# 文本/字符串类（视觉小说打字机、对话拼接用）
# operator_letter_of: 取字符串第 n 个字符
LETTER_OF = lambda n, s: {"letter_of": {"letter": n, "word": s}}
# operator_join: 连接两段文本
JOIN = lambda a, b: {"join": {"a": a, "b": b}}
# operator_length: 字符串长度
LEN = lambda s: {"length_of": {"string": s}}


def _v(x):
    if isinstance(x, str):
        return {"var": x}
    return x


def ANDn(*args):
    """任意长度的逻辑与（Scratch 的 and 只有 2 个输入，多于 2 项要嵌套）。"""
    if len(args) == 0:
        return {"equals": [1, 1]}
    if len(args) == 1:
        return args[0]
    if len(args) == 2:
        return {"and": [args[0], args[1]]}
    return {"and": [args[0], ANDn(*args[1:])]}


def ORn(*args):
    """任意长度的逻辑或（Scratch 的 or 只有 2 个输入，多于 2 项要嵌套）。"""
    if len(args) == 0:
        return {"equals": [1, 0]}
    if len(args) == 1:
        return args[0]
    if len(args) == 2:
        return {"or": [args[0], args[1]]}
    return {"or": [args[0], ORn(*args[1:])]}


def repv(var, n, *do):
    """计数器 var 从 0 跑到 n，循环体内 var 已是 1..n。"""
    return [SET(var, 0), REPEAT(n, CHG(var, 1), *do)]
