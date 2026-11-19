#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""积木语义回归：编译 examples/semantic_check.yaml，用 scratch-vm 实跑，比对期望值。

为什么需要它
------------
四层校验（结构 / Schema / parser / 运行时）只保证「能打开、不崩」，
**不保证积木算出来的值是对的**。改构建器的输入映射、别名、运算编码时，
很容易出现「全都通过校验，但 1+2 算成别的」这种静默偏差。

本脚本把 27 个典型表达式（算术/比较/逻辑/字符串/嵌套/控制流/列表）
编译成 .sb3，交给 scratch-vm 真跑，再逐项对比 examples/semantic_check.expected.yaml。

用法：
    python scripts/semantic_check.py
    python scripts/semantic_check.py --keep       # 保留临时 .sb3
退出码：0 = 全部符合；1 = 存在不符；2 = 环境/流程错误。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IR = os.path.join(ROOT, 'examples', 'semantic_check.yaml')
EXPECTED = os.path.join(ROOT, 'examples', 'semantic_check.expected.json')
SMOKE = os.path.join(HERE, 'smoke_test.mjs')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep', action='store_true', help='保留临时 sb3')
    args = ap.parse_args()

    if not os.path.exists(IR) or not os.path.exists(EXPECTED):
        print('缺少探针文件：%s / %s' % (IR, EXPECTED), file=sys.stderr)
        return 2

    # 把每个语义用例（t01..t22 / c01..c05）关联到探针 YAML 里 set_variable 的源码行，
    # 失败时直接定位到哪条表达式。load_ir_marked 失败则降级为「无行号」。
    assign_lines = {}
    try:
        sys.path.insert(0, HERE)
        from ir_schema import load_ir_marked
        _ir, _marks = load_ir_marked(IR)

        def _collect(node, out):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "set_variable" and isinstance(v, dict) \
                            and isinstance(v.get("var"), str):
                        out[v["var"]] = _marks.get(id(v))
                    _collect(v, out)
            elif isinstance(node, list):
                for it in node:
                    _collect(it, out)

        _collect(_ir, assign_lines)
    except Exception:
        assign_lines = {}

    tmp = os.path.join(tempfile.gettempdir(), 'semantic_check.sb3')

    build = subprocess.run(
        [sys.executable, os.path.join(HERE, 'build_sb3.py'),
         '--ir', IR, '--out', tmp],
        capture_output=True, text=True)
    if build.returncode != 0:
        combined = build.stdout + build.stderr
        # 构建期 IR 校验已带「第N行」源码行号，前置展示便于直接定位。
        val_lines = [l for l in combined.splitlines()
                     if '第' in l and '行' in l]
        if val_lines:
            print('构建期 IR 校验（带源码行号）：', file=sys.stderr)
            for l in val_lines:
                print('  ' + l, file=sys.stderr)
        print('探针编译失败：', file=sys.stderr)
        print(combined[-1500:], file=sys.stderr)
        return 2

    run = subprocess.run(
        ['node', SMOKE, tmp, '--seconds', '3'],
        capture_output=True, text=True)
    text = run.stdout + run.stderr
    if 'SMOKE_OK' not in text:
        print('运行时冒烟失败：', file=sys.stderr)
        print(text[-1500:], file=sys.stderr)
        return 2

    m = re.search(r'Stage:\s*(\{.*\})', text)
    if not m:
        print('未能从冒烟输出中读到 Stage 变量', file=sys.stderr)
        print(text[-1500:], file=sys.stderr)
        return 2
    actual = json.loads(m.group(1))
    expected = json.load(open(EXPECTED, encoding='utf-8'))

    bad = []
    for key, want in expected.items():
        got = actual.get(key, '<缺失>')
        ok = (got == want
              or isinstance(want, bool) and str(got).lower() == str(want).lower()
              or str(got) == str(want))
        if not ok:
            bad.append((key, want, got))

    print('语义用例 %d 项：符合 %d，不符合 %d'
          % (len(expected), len(expected) - len(bad), len(bad)))
    for key, want, got in bad:
        ln = assign_lines.get(key)
        loc = (' (第%d行)' % ln) if ln else ''
        print('  ✗ %-5s%s 期望=%-12r 实际=%r' % (key, loc, want, got))
    if not bad:
        print('SEMANTIC_OK')
    if not args.keep:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
