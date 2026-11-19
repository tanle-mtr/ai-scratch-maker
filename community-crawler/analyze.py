#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 sb3 用到的进阶技巧，并汇总「非 Scratch 积木」情况。

用于把爬来的社区作品「读薄」：快速看出每个作品精通了哪些 Scratch 技巧，
便于后续借鉴/教学。配合 filter_scratch_blocks 给出非 Scratch 积木统计。

用法：
  python analyze.py file.sb3                 # 单文件分析（打印）
  python analyze.py file.sb3 --json out.json # 输出 JSON
  python analyze.py ./folder/                # 批量目录分析（汇总）
"""
import sys, os, json, zipfile, glob, argparse
from collections import Counter

# 技巧信号：opcode 前缀/具体 opcode -> 技巧名
SIGNAL = [
    ("克隆", {"control_create_clone_of", "control_start_as_clone", "control_delete_this_clone"}),
    ("广播解耦", {"event_broadcast", "event_broadcastandwait", "event_whenbroadcastreceived"}),
    ("自制积木", {"procedures_definition", "procedures_call"}),
    ("画笔", None),  # 用前缀 pen_
    ("音乐", None),  # 前缀 music_
    ("列表即数据结构", {"data_listcontents", "data_addtolist", "data_deleteoflist",
                     "data_insertatlist", "data_replaceitemoflist", "data_itemnumoflist",
                     "data_lengthoflist", "data_listcontainsitem"}),
    ("云变量", None),  # 变量被标 cloud（在变量元组第3项）
    ("物理/数学运算", None),  # operator 高频 + 自定义
    ("计时器/响度传感", {"sensing_timer", "sensing_loudness", "sensing_videoOn"}),
    ("键盘/鼠标交互", {"event_whenkeypressed", "sensing_mousedown", "sensing_touchingobject"}),
]


def _load(path):
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read("project.json").decode("utf-8"))


def analyze(path):
    pj = _load(path)
    blocks_all = {}
    n_sprites = 0
    n_stage = 0
    var_total = 0
    list_total = 0
    cloud_vars = 0
    op_counter = Counter()
    tech = Counter()
    for t in pj.get("targets", []):
        if t.get("isStage"):
            n_stage += 1
        else:
            n_sprites += 1
        for v in t.get("variables", {}).values():
            var_total += 1
            if isinstance(v, list) and len(v) > 2 and v[2] == "cloud":
                cloud_vars += 1
        list_total += len(t.get("lists", {}))
        for bid, b in t.get("blocks", {}).items():
            if not isinstance(b, dict):
                continue
            op = b.get("opcode", "")
            op_counter[op] += 1
            blocks_all[bid] = op
            # 技巧信号
            for name, ops in SIGNAL:
                if ops and op in ops:
                    tech[name] += 1
            if op.startswith("pen_"):
                tech["画笔"] += 1
            if op.startswith("music_"):
                tech["音乐"] += 1
            if op.startswith("operator_"):
                tech["运算符"] += 1
    # 广播消息种类
    broadcasts = set()
    for t in pj.get("targets", []):
        for b in t.get("blocks", {}).values():
            if isinstance(b, dict) and b.get("opcode") in ("event_broadcast", "event_broadcastandwait"):
                inp = b.get("inputs", {})
                if "BROADCAST_INPUT" in inp and isinstance(inp["BROADCAST_INPUT"], list) and len(inp["BROADCAST_INPUT"]) > 1:
                    _bv = inp["BROADCAST_INPUT"][1]
                    if isinstance(_bv, str):
                        broadcasts.add(_bv)
                    elif isinstance(_bv, list) and len(_bv) > 1 and isinstance(_bv[1], str):
                        broadcasts.add(_bv[1])
    return {
        "file": os.path.basename(path),
        "sprites": n_sprites,
        "stage": n_stage,
        "blocks": sum(op_counter.values()),
        "variables": var_total,
        "lists": list_total,
        "cloud_vars": cloud_vars,
        "broadcasts": len(broadcasts),
        "techniques": {k: v for k, v in tech.items() if v},
        "top_opcodes": op_counter.most_common(12),
    }


def main():
    ap = argparse.ArgumentParser(description="sb3 技巧分析")
    ap.add_argument("path")
    ap.add_argument("--json", help="输出 JSON 路径")
    args = ap.parse_args()
    if os.path.isdir(args.path):
        results = []
        for f in sorted(glob.glob(os.path.join(args.path, "*.sb3"))):
            results.append(analyze(f))
        # 汇总技巧出现频次
        agg = Counter()
        for r in results:
            for k in r["techniques"]:
                agg[k] += 1
        print(f"共分析 {len(results)} 个作品。各技巧出现的作品数：")
        for k, v in agg.most_common():
            print(f"  {k:12s} {v}")
        if args.json:
            json.dump(results, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return
    r = analyze(args.path)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if args.json:
        json.dump(r, open(args.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
