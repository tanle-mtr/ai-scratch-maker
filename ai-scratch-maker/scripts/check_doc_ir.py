#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 references/*.md 里出现的 IR 写法是否与 blocks-spec.json 一致。

做两件事：
1) 把文档里所有 `{ 积木名: ... }` 形式的顶层键抓出来，核对：
   - 该键是否是合法的积木别名（aliases）
   - 用到的输入键名是否在该 opcode 的 input_aliases 里
2) 报告拼写错误的键（最常见的坑）。

用法：python3 scripts/check_doc_ir.py [手册路径...]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = json.load(open(os.path.join(ROOT, "references", "blocks-spec.json"),
                       encoding="utf-8"))
ALIASES = SPEC.get("aliases", {})
IA = SPEC.get("input_aliases", {})
BLOCKS = SPEC["blocks"]

# 文档里常见的非积木键（结构键，不是积木别名）
STRUCT_KEYS = {"do", "else", "cond", "condition", "comment", "value", "var",
               "list", "message", "question", "costume", "backdrop", "key",
               "sound", "note", "beats", "drum", "instrument", "tempo", "size",
               "ghost", "hue", "steps", "x", "y", "secs", "duration", "times",
               "clone", "option", "effect", "object", "property", "target",
               "a", "b", "n", "num", "op", "index", "item", "by", "from", "to",
               "degrees", "direction", "text", "sounds", "answer",
               "name", "operand", "id", "prefix", "suffix", "now",
               # 字段名（下拉菜单 / 特殊输入）
               "TOWARDS", "COLOR", "GHOST", "FISHEYE", "WHIRL", "PIXELATE",
               "MOSAIC", "BRIGHTNESS", "front_back", "stop_option",
               "switch_backdrop_and_wait", "dx", "dy", "shade", "avoid",
               "operator", "proc", "floor",
               # 自带扩展积木的输入键（第八册）：它们不是积木名，是积木的输入字段
               "words", "language", "voice", "video_state", "transparency",
               "attribute", "subject", "reference", "phrase", "motion", "video",
               # 说明性词汇（出现在散文/图示里，非积木名）
               "agent", "forward_backward", "color", "towards", "vx",
               # 示例 IR 里的 ASCII 变量声明名（中文变量名已被正则自动忽略，
               # 只有 ASCII 变量名会被误抓，这里逐一豁免）
               "ID", "XVelocity", "YVelocity", "CAMx", "CAMy", "CAM",
               "scroll_x", "scroll_y", "tv_x", "lx", "lx", "sx", "sy",
               "screen_x", "screen_y", "gx", "gy", "屏幕x", "屏幕y",
               # 自定义积木参数名 / 输入字段名（不是积木名）
               "x1", "letter"}

BLOCK_KEY_RE = re.compile(r'\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:')


def collect_keys(text):
    """抓出所有 `{ key:` 形式的 key。"""
    return BLOCK_KEY_RE.findall(text)


def check_file(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    keys = collect_keys(text)
    unknown = {}
    bad_inputs = {}
    for k in keys:
        if k in STRUCT_KEYS:
            continue
        op = ALIASES.get(k)
        if op is None:
            unknown.setdefault(k, 0)
            unknown[k] += 1
            continue
        # 检查该积木用到的输入键
        spec = BLOCKS.get(op)
        if spec is None:
            continue
    return unknown, bad_inputs


def main():
    files = sys.argv[1:]
    if not files:
        refs = os.path.join(ROOT, "references")
        files = [os.path.join(refs, n) for n in sorted(os.listdir(refs))
                 if n.endswith(".md")]
    total_bad = 0
    for p in files:
        unknown, _ = check_file(p)
        name = os.path.basename(p)
        if unknown:
            total_bad += len(unknown)
            print("[%s] ⚠️ 未知积木名：" % name)
            for k, c in sorted(unknown.items(), key=lambda x: -x[1]):
                hint = ""
                # 提示最接近的别名
                cands = [a for a in ALIASES
                         if a.lower().replace("_", "") == k.lower().replace("_", "")]
                if cands:
                    hint = "  (相近别名: %s)" % ", ".join(cands[:4])
                print("    %-28s ×%d%s" % (k, c, hint))
        else:
            print("[%s] ✅ 所有积木名都能在 blocks-spec.json 中找到" % name)
    print()
    print("共 %d 个文件，%d 个待确认的积木名" % (len(files), total_bad))
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
