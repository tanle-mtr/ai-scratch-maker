#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 references/blocks-spec.json 生成 references/blocks.md —— 全部积木的完整参考。

每个积木都给出：
  * 原始 opcode、形状（帽子/命令/上报/布尔）
  * 可用的友好名（IR 里可以直接用）
  * Scratch 官方英文原文
  * 每个输入/字段的名字、类型、下拉选项，以及它在 sb3 里被编码成的实际 JSON
  * 一段完整的 sb3 积木 JSON 示例

用法：python3 scripts/make_blocks_doc.py
"""
import json
import os
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC = os.path.join(ROOT, 'references', 'blocks-spec.json')
OUT = os.path.join(ROOT, 'references', 'blocks.md')

CATEGORY_CN = {
    'events': '事件 (Events)',
    'control': '控制 (Control)',
    'motion': '运动 (Motion)',
    'looks': '外观 (Looks)',
    'sound': '声音 (Sound)',
    'sensing': '侦测 (Sensing)',
    'operators': '运算 (Operators)',
    'data': '变量与列表 (Data)',
    'procedures': '自定义积木 (Procedures)',
    'pen': '画笔扩展 (Pen)',
    'music': '音乐扩展 (Music)',
    'text2speech': '朗读扩展 (Text to Speech)',
    'translate': '翻译扩展 (Translate)',
    'videoSensing': '视频感应扩展 (Video Sensing)',
    'speech2text': '语音转文字扩展 (Speech to Text)',
    'other': '其它',
}

CATEGORY_ORDER = ['events', 'control', 'motion', 'looks', 'sound', 'sensing',
                  'operators', 'data', 'procedures', 'pen', 'music',
                  'text2speech', 'translate', 'videoSensing', 'speech2text', 'other']

SHAPE_CN = {
    'hat': '帽子积木（脚本起点）',
    'command': '命令积木',
    'reporter': '上报积木（圆角）',
    'boolean': '布尔积木（六边形）',
    'menu-source': '下拉菜单影子积木',
}

# 输入类型 -> (中文说明, sb3 编码示例值)
INPUT_TYPE_DOC = {
    'number':    ('数字', [1, [4, "10"]]),
    'angle':     ('角度', [1, [8, "90"]]),
    'color':     ('颜色', [1, [9, "#ff0000"]]),
    'text':      ('文本', [1, [10, "你好"]]),
    'value':     ('任意值（文本/数字）', [1, [10, "值"]]),
    'broadcast': ('广播消息', [1, [11, "开始", "开始"]]),
    'variable':  ('变量引用', [3, [12, "分数", "变量id"]]),
    'list':      ('列表引用', [3, [13, "排行榜", "列表id"]]),
    'boolean':   ('布尔积木', [2, "子积木id"]),
    'substack':  ('子栈（积木堆）', [2, "子积木id"]),
    'menu':      ('动态下拉菜单', [1, "_mouse_"]),
}

FIELD_TYPE_DOC = {
    'varfield':  ('变量下拉', ["分数", "变量id"]),
    'listfield': ('列表下拉', ["排行榜", "列表id"]),
    'menu':      ('静态下拉菜单', ["COLOR", None]),
}


def jdump(v):
    return json.dumps(v, ensure_ascii=False)


def pretty_json(v, indent=0):
    """字典展开、数组压成一行，便于人读。"""
    pad = ' ' * indent
    if isinstance(v, dict):
        if not v:
            return '{}'
        items = ['%s  %s: %s' % (pad, json.dumps(k, ensure_ascii=False),
                                  pretty_json(val, indent + 2))
                 for k, val in v.items()]
        return '{\n' + ',\n'.join(items) + '\n' + pad + '}'
    if isinstance(v, list):
        return '[' + ', '.join(pretty_json(x, indent) for x in v) + ']'
    return json.dumps(v, ensure_ascii=False)


def example_value(itype):
    """给输入生成一个示例值。"""
    return {
        'number': 10, 'angle': 90, 'color': '#ff0000', 'text': '你好',
        'value': '值', 'broadcast': '开始', 'variable': '分数', 'list': '排行榜',
        'boolean': None, 'substack': None, 'menu': '_mouse_',
    }.get(itype)


def render_block(opcode, b, aliases_by_target):
    lines = []
    lines.append('#### `%s`%s' % (opcode, '  —  ' + b['text'] if b.get('text') else ''))
    lines.append('')
    shape = b.get('shape')
    meta = ['- 形状：**%s**' % SHAPE_CN.get(shape, shape)]
    if b.get('extension'):
        meta.append('- 扩展：`%s`' % b['extension'])
    names = aliases_by_target.get(opcode) or []
    if names:
        shown = names[:6]
        meta.append('- 友好名（IR 里可直接用）：%s' % '、'.join('`%s`' % n for n in shown))
    lines.extend(meta)
    lines.append('')

    if b.get('inputs'):
        lines.append('**输入（写在 sb3 的 `inputs`）**')
        lines.append('')
        lines.append('| 名称 | 类型 | 说明 | sb3 编码示例 |')
        lines.append('|---|---|---|---|')
        for iname, idef in b['inputs'].items():
            t = idef.get('type', 'value')
            desc, enc = INPUT_TYPE_DOC.get(t, (t, '-'))
            lines.append('| `%s` | %s | %s | `%s` |' % (iname, t, desc, jdump(enc)))
        lines.append('')

    if b.get('fields'):
        lines.append('**字段（写在 sb3 的 `fields`）**')
        lines.append('')
        lines.append('| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |')
        lines.append('|---|---|---|---|---|')
        for fname, fdef in b['fields'].items():
            t = fdef.get('type', 'menu')
            desc, enc = FIELD_TYPE_DOC.get(t, (t, '-'))
            opts = fdef.get('options') or []
            if opts:
                opt_txt = '、'.join('`%s`' % o[1] for o in opts[:14])
                if len(opts) > 14:
                    opt_txt += ' …（共 %d 项）' % len(opts)
            else:
                opt_txt = '（运行时填充，如角色名/造型名）'
            lines.append('| `%s` | %s | %s | `%s` | %s |'
                         % (fname, t, desc, jdump(enc), opt_txt))
        lines.append('')

    # 完整 sb3 示例
    inputs = OrderedDict()
    for iname, idef in b['inputs'].items():
        t = idef.get('type', 'value')
        inputs[iname] = INPUT_TYPE_DOC.get(t, ('', [1, [10, "值"]]))[1]
    fields = OrderedDict()
    for fname, fdef in b['fields'].items():
        t = fdef.get('type', 'menu')
        fields[fname] = FIELD_TYPE_DOC.get(t, ('', ["值", None]))[1]
    sample = OrderedDict()
    sample['opcode'] = opcode
    sample['next'] = None
    sample['parent'] = None
    sample['inputs'] = inputs
    sample['fields'] = fields
    sample['topLevel'] = True
    sample['x'] = 0
    sample['y'] = 0
    lines.append('**生成出的 sb3 积木**')
    lines.append('')
    lines.append('```json')
    lines.append(pretty_json(sample))
    lines.append('```')
    lines.append('')
    return lines


def main():
    with open(SPEC, encoding='utf-8') as f:
        spec = json.load(f)
    blocks = spec['blocks']
    aliases = spec.get('aliases') or {}

    aliases_by_target = {}
    for friendly, op in aliases.items():
        aliases_by_target.setdefault(op, []).append(friendly)
    for op in aliases_by_target:
        aliases_by_target[op].sort(key=lambda n: (n == op, len(n), n))

    by_cat = {}
    for op, b in blocks.items():
        by_cat.setdefault(b.get('category', 'other'), []).append(op)

    L = []
    L.append('# Scratch 3.0 全部积木速查表')
    L.append('')
    L.append('> 本文件由 `scripts/make_blocks_doc.py` 从 `references/blocks-spec.json` 自动生成，')
    L.append('> 而 `blocks-spec.json` 又由 `scripts/extract_blocks_spec.js` 直接从 **Scratch 官方源码** 抽取：')
    L.append('>')
    L.append('> - 积木形状、输入名、字段名、下拉选项 ← `scratch-blocks/src/blocks/*.ts`')
    L.append('> - 运行时原语清单（保证不漏积木）、输入原始类型 ← `scratch-vm/src/blocks/scratch3_*.js`')
    L.append('> - 扩展积木 ← `scratch-vm/src/extensions/*/index.js`')
    L.append('')
    L.append('共 **%d** 个积木（含 %d 个下拉影子积木），覆盖 9 大类别 + 画笔/音乐/朗读/翻译/视频感应/语音转文字扩展。'
             % (len(blocks), sum(1 for b in blocks.values() if b.get('shape') == 'menu-source')))
    L.append('')
    L.append('## 阅读方式')
    L.append('')
    L.append('- **opcode**：Scratch 内部的积木唯一标识，IR 里写它最保险。')
    L.append('- **友好名**：语义化的英文别名（如 `move_steps`），IR 里写它更易读。')
    L.append('- **输入（inputs）**：会出现在 sb3 的 `inputs` 字典里，值是 `[状态, ...]`。')
    L.append('- **字段（fields）**：下拉选择类的输入（变量名、造型名、特效类型…），')
    L.append('  在 sb3 里写在 `fields` 字典里，值是 `[值, id]`。')
    L.append('')
    L.append('### sb3 编码速查')
    L.append('')
    L.append('| 概念 | sb3 写法 |')
    L.append('|---|---|')
    L.append('| 输入里的影子值 | `[1, [4,"10"]]` — 状态 1 + 基元 |')
    L.append('| 输入里嵌套了积木 | `[2, "块id"]` — 状态 2（只有积木） |')
    L.append('| 变量/列表引用 | `[3, [12,"分数","变量id"]]` — 状态 3 |')
    L.append('| 动态下拉菜单 | `[1, "_mouse_"]` — 裸字符串 |')
    L.append('| 广播 | `[1, [11,"开始","开始"]]` |')
    L.append('| 变量字段 | `fields.VARIABLE = ["分数","变量id"]` |')
    L.append('| 普通下拉字段 | `fields.EFFECT = ["COLOR", null]` |')
    L.append('| 静态下拉 id | `null` |')
    L.append('')
    L.append('基元类型码：`4`=数字、`8`=角度、`9`=颜色、`10`=文本、`11`=广播、`12`=变量、`13`=列表。')
    L.append('')
    L.append('---')
    L.append('')

    for cat in CATEGORY_ORDER:
        ops = sorted(by_cat.get(cat, []))
        if not ops:
            continue
        L.append('## %s（%d 个）' % (CATEGORY_CN.get(cat, cat), len(ops)))
        L.append('')
        if cat == 'pen':
            L.append('> 使用画笔积木时，必须在 IR 根节点声明 `extensions: [pen]`。')
            L.append('')
        for op in ops:
            L.extend(render_block(op, blocks[op], aliases_by_target))

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print('写入 %s：%d 个积木，%d 行' % (OUT, len(blocks), len(L)))


if __name__ == '__main__':
    main()
