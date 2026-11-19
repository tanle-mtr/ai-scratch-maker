#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一个 .sb3 的脚本以可读树状打印出来（仅顶层脚本，沿 next 链展开，递归 inputs/substack）。
用法: python3 dump_scripts.py <file.sb3> [--target 名称] [--max 行数]
"""
import sys, os, json, zipfile

def val_to_str(v):
    # v: [type, value] or [type, value, ...]
    if not isinstance(v, list):
        return str(v)
    if len(v) < 2:
        return ''
    t, value = v[0], v[1]
    if t == 12 or t == 13:
        return repr(value)  # broadcast / var-ref placeholder
    if t in (4,5,6,7,8,9,10,11):
        # 4=pos num,5=pos int,6=num,7=int,8=posint,9=num,10=str,11=str? just print
        return str(value)
    if t == 10 or t == 11:
        return json.dumps(value, ensure_ascii=False) if isinstance(value,str) else str(value)
    return str(value)

def input_to_str(inp):
    # inp: [type, value] or [type, value, shadow?]
    if not isinstance(inp, list):
        return str(inp)
    if len(inp) < 2:
        return ''
    t, value = inp[0], inp[1]
    if t == 1:  # shadow/block ref -> 实际是 block id 或 value
        # 1 means a block reference (nested) or inline
        if isinstance(value, list):
            return '(' + input_to_str(value) + ')'
        return str(value)
    if t in (4,5,6,7,8,9):
        return str(value)
    if t == 10 or t == 11:
        return json.dumps(value, ensure_ascii=False) if isinstance(value,str) else str(value)
    if t == 12:  # broadcast id string
        return str(value)
    if t == 13:  # variable
        return str(value)
    return str(value)

def render_block(targets_map, blocks, bid, depth, out, seen):
    if bid in seen:
        out.append('  '*depth + '↺(循环引用)')
        return
    seen = seen | {bid}
    b = blocks.get(bid)
    if not isinstance(b, dict):
        return
    op = b.get('opcode','?')
    line = '  '*depth + op
    # 输入
    ins = b.get('inputs') or {}
    if ins:
        parts = []
        for k, v in ins.items():
            s = input_to_str(v)
            if s:
                parts.append(f'{k}={s}')
        if parts:
            line += ' | ' + ' '.join(parts)
    out.append(line)
    # 递归 substack
    for sub in ('SUBSTACK','SUBSTACK2','CONDITION','VALUE'):
        if sub in ins:
            sv = ins[sub]
            child = sv[2] if isinstance(sv, list) and len(sv) > 2 else (sv[1] if isinstance(sv,list) else None)
            if isinstance(child, str):
                out.append('  '*(depth+1) + f'└[{sub}]')
                render_block(targets_map, blocks, child, depth+2, out, seen)
    # next
    nxt = b.get('next')
    if nxt:
        render_block(targets_map, blocks, nxt, depth, out, seen)

def main():
    args = sys.argv[1:]
    path = None; target=None; mx=200
    i=0
    while i < len(args):
        if args[i]=='--target': target=args[i+1]; i+=2
        elif args[i]=='--max': mx=int(args[i+1]); i+=2
        else: path=args[i]; i+=1
    if not path:
        print('usage'); sys.exit(1)
    with zipfile.ZipFile(path) as z:
        pj = json.loads(z.read([n for n in z.namelist() if n.lower().endswith('project.json')][0]))
    targets = pj.get('targets', [])
    for t in targets:
        name = t.get('name') or ('舞台' if t.get('isStage') else '?')
        if target and name != target:
            continue
        blocks = t.get('blocks') or {}
        out=[]
        out.append(f"\n########## 角色: {name}  (isStage={t.get('isStage')}) 变量={list((t.get('variables') or {}).values())[:6]} 列表={list((t.get('lists') or {}).values())[:4]}")
        tops=[bid for bid,b in blocks.items() if isinstance(b,dict) and b.get('topLevel')]
        for bid in tops[:mx]:
            out.append('-- 脚本 --')
            render_block({}, blocks, bid, 0, out, set())
        print('\n'.join(out))

if __name__ == '__main__':
    main()
