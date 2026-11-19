#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单进程批量构建 examples/*.{yaml,json} -> examples/output/*.sb3。

相对逐条 `python build_sb3.py`，本脚本在**一个 Python 进程**里循环，
省掉 N× 解释器启动 + 重复 import 的开销（约 30–50s）。
复用 build_sb3.build_one（含产物缓存）：未改动的重构建直接命中缓存。

IR 源同时支持 .yaml 与 .json（按 stem 去重，同名时 .yaml 优先）。

用法：
    python scripts/build_all.py
    python scripts/build_all.py --only fruit_basket,cat_mouse
    python scripts/build_all.py --no-cache
    python scripts/build_all.py --out-dir /tmp/out --workdir /tmp/wd
"""
import argparse
import glob
import os
import sys
import time
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_sb3 import build_one, REPO_ROOT  # noqa: E402

EXAMPLES_DIR = os.path.join(os.path.dirname(HERE), "examples")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", default=EXAMPLES_DIR, help="含 *.yaml 的目录")
    ap.add_argument("--out-dir", default=None, help="默认 <examples>/output")
    ap.add_argument("--workdir", default=None, help="共用临时目录（默认每次新建一个，结束清理）")
    ap.add_argument("--no-cache", action="store_true", help="禁用产物缓存")
    ap.add_argument("--only", default=None, help="只构建逗号分隔的名字（不含扩展名）")
    args = ap.parse_args()

    examples = os.path.abspath(args.examples)
    out_dir = os.path.abspath(args.out_dir or os.path.join(examples, "output"))
    os.makedirs(out_dir, exist_ok=True)

    # IR 源：.yaml 与 .json 都支持。同名 stem 时 .yaml 优先（避免两个源重复构建）。
    # 注意：examples/ 下还有 *.quality.json、*.expected.json 等元数据文件，
    # 它们不是 IR，必须排除（仅当 JSON 顶层含 project 键时才视为 IR 源）。
    def _is_ir_json(path):
        try:
            import json as _json
            with open(path, "r", encoding="utf-8") as f:
                return "project" in _json.load(f)
        except Exception:
            return False

    srcs = {}
    for pat in ("*.yaml", "*.json"):
        for p in glob.glob(os.path.join(examples, pat)):
            if p.endswith(".json") and not _is_ir_json(p):
                continue
            stem = os.path.splitext(os.path.basename(p))[0]
            if stem not in srcs or p.endswith(".yaml"):
                srcs[stem] = p
    yamls = sorted(srcs.values())
    if args.only:
        names = set(n.strip() for n in args.only.split(",") if n.strip())
        yamls = [y for y in yamls if os.path.splitext(os.path.basename(y))[0] in names]

    # 共用一个根临时目录、但每个作品用独立子目录：既省去 N 次 mkdtemp，
    # 又避免中间资产残留串到下一个作品（build_sb3.Builder.build 已改为只打包
    # 本次引用的 emitted 资产，这里是第二道保险，也防止临时文件无限堆积）。
    shared_wd = args.workdir or tempfile.mkdtemp(prefix="build_all_")
    ok = 0
    fail = 0
    fails = []
    t0 = time.time()
    for y in yamls:
        name = os.path.splitext(os.path.basename(y))[0]
        out = os.path.join(out_dir, name + ".sb3")
        one_wd = os.path.join(shared_wd, name)
        os.makedirs(one_wd, exist_ok=True)
        okf, msg, code = build_one(y, out, workdir=one_wd, no_cache=args.no_cache)
        if okf:
            ok += 1
            print("OK   %-34s %s" % (name, msg))
        else:
            fail += 1
            fails.append((name, msg))
            print("FAIL %-34s %s" % (name, msg))
    dt = time.time() - t0
    if not args.workdir:
        shutil.rmtree(shared_wd, ignore_errors=True)
    print("--------------------------------------------------")
    print("构建 %d 成功 / %d 失败 | 总耗时 %.1fs" % (ok, fail, dt))
    if fail:
        print("失败项:")
        for n, m in fails:
            print("  %s: %s" % (n, m))
        sys.exit(1)
    print("BUILD_ALL_OK")


if __name__ == "__main__":
    sys.exit(main())
