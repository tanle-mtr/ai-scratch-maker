#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量分析一批 .sb3 作品，提取技术指纹（扩展/积木/变量/列表/自定义积木/克隆/画笔/广播/询问）。
输出每个文件的摘要 JSON 到 stdout，并在末尾打印全局聚合。
用法: python3 analyze_corpus.py <sb3路径...> [--out 目录]
"""
import sys, os, json, zipfile, io, re, collections

EXT_LABEL = {
    'pen': '画笔', 'music': '音乐', 'text2speech': '朗读', 'translate': '翻译',
    'videoSensing': '视频感应', 'speech2text': '语音转文字',
    'makeymakey': 'MakeyMakey', 'microbit': 'micro:bit', 'boost': 'BOOST',
    'wedo2': 'WeDo2', 'gdxfor': 'GoDirect', 'ev3': 'EV3', 'scp': 'Scratch 硬件',
}

# 自定义积木定义
def iter_blocks(targets):
    for t in targets:
        for bid, b in (t.get('blocks') or {}).items():
            yield t, bid, b

def analyze_one(path):
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            pj = None
            for n in names:
                if n.lower().endswith('project.json'):
                    pj = json.loads(z.read(n).decode('utf-8'))
                    break
            if pj is None:
                return {'error': 'no project.json', 'name': os.path.basename(path)}
    except Exception as e:
        return {'error': 'unzip:%s' % e, 'name': os.path.basename(path)}

    targets = pj.get('targets', [])
    extensions = pj.get('extensions', [])
    opcodes = collections.Counter()
    var_names = []
    list_names = []
    custom_names = []
    clone = False
    pen = False
    ask = False
    broadcast_count = 0
    touching_color = False
    color_touching = False
    pen_down = False
    list_char_count = 0

    for t in targets:
        for vname in (t.get('variables') or {}).values():
            # variables: id -> [name, value]
            if isinstance(vname, list) and vname:
                var_names.append(vname[0])
        for lname in (t.get('lists') or {}).values():
            if isinstance(lname, list) and lname:
                list_names.append(lname[0])
                val = lname[1] if len(lname) > 1 else []
                if isinstance(val, list):
                    list_char_count += sum(len(str(x)) for x in val)

    def walk_blocks():
        nonlocal clone, pen, ask, broadcast_count, touching_color, color_touching, pen_down
        for t in targets:
            for bid, b in (t.get('blocks') or {}).items():
                if not isinstance(b, dict):
                    continue
                op = b.get('opcode', '')
                opcodes[op] += 1
                if op == 'control_create_clone_of':
                    clone = True
                if op.startswith('pen_'):
                    pen = True
                    if op == 'pen_penDown':
                        pen_down = True
                if op == 'sensing_askandwait':
                    ask = True
                if op == 'control_broadcast' or op == 'control_broadcastandwait':
                    broadcast_count += 1
                if op == 'sensing_touchingcolor':
                    touching_color = True
                if op == 'sensing_coloristouchingcolor':
                    color_touching = True
                if op == 'procedures_definition':
                    mut = b.get('mutation') or {}
                    proc = mut.get('proccode') or ''
                    if proc:
                        custom_names.append(proc)

    walk_blocks()

    sprite_count = sum(1 for t in targets if not t.get('isStage'))
    costume_total = sum(len(t.get('costumes') or []) for t in targets)
    # 估计脚本数（顶层积木）
    toplevel = sum(1 for t in targets for b in (t.get('blocks') or {}).values()
                   if isinstance(b, dict) and b.get('topLevel'))

    # 技术标签推断
    tags = []
    if pen: tags.append('画笔')
    if clone: tags.append('克隆')
    if ask: tags.append('询问/输入')
    if broadcast_count > 5: tags.append('重度广播')
    if touching_color or color_touching: tags.append('颜色碰撞')
    if any('3d' in (n.lower()) or 'camera' in n.lower() or 'yaw' in n.lower() or 'pitch' in n.lower() for n in var_names):
        tags.append('3D数学')
    if any(('歌词' in n) or ('lyric' in n.lower()) for n in list_names+var_names):
        tags.append('滚动歌词')
    if any(('门' in n) or ('开关' in n) for n in list_names+var_names):
        tags.append('开关/门状态机')
    if any(('加载' in n) or ('loading' in n.lower()) or ('圈' in n) for n in list_names+var_names+var_names):
        tags.append('加载特效')
    if any(('阴影' in n) or ('shadow' in n.lower()) or ('光' in n) or ('ray' in n.lower()) or ('射线' in n) for n in list_names+var_names):
        tags.append('光影/射线')
    if any(('地铁' in n) or ('站' in n) or ('线路' in n) for n in list_names+var_names):
        tags.append('线路/站点')
    if any(('输入' in n) or ('框' in n) for n in list_names+var_names):
        tags.append('输入框')
    if any(('分' in n) or ('关' in n) or ('level' in n.lower()) for n in list_names+var_names):
        tags.append('关卡/分关')

    return {
        'name': os.path.basename(path),
        'size_kb': round(os.path.getsize(path)/1024, 1),
        'extensions': extensions,
        'targets': len(targets),
        'sprites': sprite_count,
        'costumes': costume_total,
        'toplevel_scripts': toplevel,
        'var_count': len(var_names),
        'list_count': len(list_names),
        'list_char_total': list_char_count,
        'custom_blocks': custom_names,
        'custom_block_count': len(custom_names),
        'clone': clone, 'pen': pen, 'pen_down': pen_down, 'ask': ask,
        'broadcast_count': broadcast_count,
        'touching_color': touching_color, 'color_touching': color_touching,
        'tags': tags,
        'top_opcodes': opcodes.most_common(12),
        'var_names_sample': var_names[:40],
        'list_names_sample': list_names[:30],
    }

def main():
    args = sys.argv[1:]
    out_dir = None
    paths = []
    i = 0
    while i < len(args):
        if args[i] == '--out':
            out_dir = args[i+1]; i += 2
        else:
            paths.append(args[i]); i += 1
    if not paths:
        print('usage: analyze_corpus.py <sb3...> [--out dir]'); sys.exit(1)

    results = []
    for p in paths:
        if not os.path.exists(p):
            results.append({'error': 'missing', 'name': p}); continue
        try:
            r = analyze_one(p)
            results.append(r)
        except Exception as e:
            results.append({'error': 'analyze:%s' % e, 'name': p})

    # 全局聚合
    ext_union = collections.Counter()
    tag_union = collections.Counter()
    opcode_union = collections.Counter()
    name_union_vars = collections.Counter()
    name_union_lists = collections.Counter()
    custom_union = collections.Counter()
    for r in results:
        if 'error' in r: continue
        for e in r.get('extensions', []):
            ext_union[e] += 1
        for tg in r.get('tags', []):
            tag_union[tg] += 1
        for op, c in r.get('top_opcodes', []):
            opcode_union[op] += c
        for v in r.get('var_names_sample', []):
            name_union_vars[v] += 1
        for l in r.get('list_names_sample', []):
            name_union_lists[l] += 1
        for cb in r.get('custom_blocks', []):
            custom_union[cb] += 1

    out = {
        'files': results,
        'aggregate': {
            'ext_union': ext_union.most_common(),
            'tag_union': tag_union.most_common(),
            'opcode_union_top': opcode_union.most_common(30),
            'var_names_freq': name_union_vars.most_common(60),
            'list_names_freq': name_union_lists.most_common(50),
            'custom_blocks_freq': custom_union.most_common(80),
        }
    }
    text = json.dumps(out, ensure_ascii=False, indent=1)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        fp = os.path.join(out_dir, 'corpus_analysis.json')
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(text)
        print('wrote', fp)
    else:
        print(text)

if __name__ == '__main__':
    main()
