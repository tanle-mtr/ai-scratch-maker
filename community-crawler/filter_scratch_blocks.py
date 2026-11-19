#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""过滤 sb3 中「不是 Scratch 的积木」（第三方/平台自定义扩展积木）。

==================== 原理 ====================
Scratch 3 的 project.json 里，每个积木有 opcode，形如 `<namespace>_<blockName>`：
  · 核心分类：  motion / looks / sound / events / control / sensing / operators / data / procedures / argument
  · 官方内置扩展（scratch.mit.edu 自带）：pen / wedo2 / music / text2speech / translate /
    makeymakey / microbit(mbit) / ev3 / boost / videoSensing
积木的 namespace（opcode 第一个下划线前的内容）如果在上述白名单内 -> 保留；
否则即「不是 Scratch 的积木」（如小码王的云变量扩展、共创世界 Gandi 的 MMO/物理/云库等自定义扩展）-> 删除。

删除时做「积木图手术」：
  · 把被删积木的 next 指针交给它的前驱（prevBlock.next = deleted.next）
  · 把以被删积木为 parent 的子积木重挂到祖父（parent=deleted.parent），若祖父为空则置为顶层
  · 清掉其它积木 inputs/fields/mutations 里对被删积木的引用
  · 解除指向被删积木的评论
  · 可选 --strip-ext：把 project.extensions 里非白名单的扩展条目一并删掉

==================== 用法 ====================
  python filter_scratch_blocks.py in.sb3 --out out.sb3 --report report.json
  python filter_scratch_blocks.py in.sb3 --report-only --report report.json
  # 若想保留某些 mod 扩展（如 TurboWarp 常见扩展），用 --extra-allow：
  python filter_scratch_blocks.py in.sb3 --extra-allow mqtt,makeymakey --out out.sb3
"""
import sys, os, json, zipfile, io, argparse
from collections import defaultdict

CORE = {"motion", "looks", "sound", "event", "control", "sensing",
        "operator", "data", "procedures", "argument"}
OFFICIAL_EXT = {"pen", "wedo2", "music", "text2speech", "translate",
                "makeymakey", "microbit", "mbit", "ev3", "boost", "videoSensing"}
DEFAULT_ALLOW = CORE | OFFICIAL_EXT
# 既无下划线、又是核心的特例（自定义积木相关）
KEEP_OPS = {"procedures_definition", "procedures_call", "procedures_prototype",
            "argument_reporter_boolean", "argument_reporter_string_number",
            "argument_reporter_custom"}


def _load_project(sb3_path):
    with zipfile.ZipFile(sb3_path) as z:
        return json.loads(z.read("project.json").decode("utf-8"))


def _save_project(sb3_path, project, out_path):
    with zipfile.ZipFile(sb3_path) as zin:
        info = {i.filename: i for i in zin.infolist()}
        data = {i.filename: zin.read(i.filename) for i in zin.infolist()}
    data["project.json"] = json.dumps(project, ensure_ascii=False).encode("utf-8")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, content in data.items():
            zout.writestr(info[name], content)


def filter_project(project, allow, report):
    removed = 0
    targets = project.get("targets", [])
    for t in targets:
        blocks = t.get("blocks", {})
        if not isinstance(blocks, dict):
            continue
        removable = set()
        for bid, b in blocks.items():
            if not isinstance(b, dict):
                continue
            op = b.get("opcode", "")
            if op in KEEP_OPS:
                continue
            prefix = op.split("_", 1)[0] if "_" in op else op
            ext = b.get("extension")
            if prefix in allow or (ext and ext in allow):
                continue
            removable.add(bid)
            report["by_namespace"][prefix] = report["by_namespace"].get(prefix, 0) + 1
        if not removable:
            continue
        # 前驱 / 父 / 引用 修复
        for bid in removable:
            b = blocks.get(bid)
            if b is None:
                continue
            nxt = b.get("next")
            parent = b.get("parent")
            # 前驱：把 next 接上
            for other, ob in blocks.items():
                if isinstance(ob, dict) and ob.get("next") == bid:
                    ob["next"] = nxt
                    break
            # 子积木：重挂祖父
            for other, ob in blocks.items():
                if isinstance(ob, dict) and ob.get("parent") == bid:
                    ob["parent"] = parent
                    if parent is None and b.get("topLevel"):
                        ob["topLevel"] = True
                        if "x" in b:
                            ob["x"] = b["x"]
                        if "y" in b:
                            ob["y"] = b["y"]
            # 清理引用
            for other, ob in blocks.items():
                if isinstance(ob, dict):
                    for slot in ("inputs", "fields", "mutations"):
                        val = ob.get(slot)
                        if isinstance(val, dict):
                            for k, v in list(val.items()):
                                if isinstance(v, list):
                                    for i in range(len(v)):
                                        if v[i] == bid:
                                            v[i] = None
            del blocks[bid]
            removed += 1
        # 评论解绑
        comments = t.get("comments", {})
        if isinstance(comments, dict):
            for cid, c in comments.items():
                if isinstance(c, dict) and c.get("blockId") in removable:
                    c["blockId"] = None
    return removed


def strip_extensions(project, allow, report):
    exts = project.get("extensions")
    if not isinstance(exts, list):
        return
    kept = []
    for e in exts:
        es = e.split("/")[-1].split(".")[0] if isinstance(e, str) else ""
        if es in allow or es in OFFICIAL_EXT or es in CORE:
            kept.append(e)
        else:
            report["stripped_extensions"].append(e)
    project["extensions"] = kept


def run(in_path, out_path, report_path, extra_allow, strip_ext, report_only):
    allow = set(DEFAULT_ALLOW)
    for a in (extra_allow or "").split(","):
        a = a.strip()
        if a:
            allow.add(a)
    project = _load_project(in_path)
    report = {"file": os.path.basename(in_path), "by_namespace": {}, "stripped_extensions": [],
              "removed_blocks": 0}
    # 报告原始扩展
    report["orig_extensions"] = project.get("extensions", [])
    removed = filter_project(project, allow, report)
    report["removed_blocks"] = removed
    if strip_ext:
        strip_extensions(project, allow, report)
    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    if report_only or not out_path:
        print(f"[报告] {os.path.basename(in_path)}: 删除 {removed} 个非 Scratch 积木; "
              f"涉及扩展命名空间 {sorted(report['by_namespace'])}; 剥离扩展 {report['stripped_extensions']}")
    else:
        _save_project(in_path, project, out_path)
        print(f"[完成] {os.path.basename(in_path)}: 删除 {removed} 个非 Scratch 积木 -> {out_path}")
    if report_path:
        print(f"        详细报告 -> {report_path}")
    return report


def main():
    ap = argparse.ArgumentParser(description="过滤 sb3 中不是 Scratch 的积木")
    ap.add_argument("input")
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--extra-allow", help="额外保留的扩展命名空间，逗号分隔")
    ap.add_argument("--strip-ext", action="store_true", help="同时删除 project.extensions 里的非白名单条目")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()
    run(args.input, args.out, args.report, args.extra_allow, args.strip_ext, args.report_only)


if __name__ == "__main__":
    main()
