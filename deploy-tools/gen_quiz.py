#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成答题系统示例 quiz.yaml（用 yaml.dump，避免手写 YAML 踩坑）。

设计要点见 references/quiz-systems.md。
用法：python gen_quiz.py <输出 yaml 路径>
"""
import sys
import yaml

Q = [
    # (造型名, 题干, 选项串, 正确答案序号 1..4)
    ('题1', '1 + 1 = ?',       'A. 1    B. 2    C. 3    D. 4',      2),
    ('题2', '一周有几天？',     'A. 5    B. 6    C. 7    D. 8',      3),
    ('题3', '太阳从哪边升起？', 'A. 东   B. 南   C. 西   D. 北',      1),
    ('题4', '水的化学式是？',   'A. CO2  B. O2   C. H2O2 D. H2O',    4),
]

V = lambda n: {'var': n}
ITEM = lambda lst: {'item_of_list': {'index': V('题号'), 'list': lst}}
EQ = lambda a, b: {'equals': [a, b]}

stage_scripts = [
    # ① 一局开始：复位挂「广播」，不挂绿旗（绿旗会重复触发）
    [
        {'when_receive': {'message': '开始答题'}},
        {'broadcast': {'message': '重置'}},
    ],
    # ② 复位集中在一个广播里，重开一局不会残留上局状态
    [
        {'when_receive': {'message': '重置'}},
        {'set_variable': {'var': '题号', 'value': 1}},
        {'set_variable': {'var': '分数', 'value': 0}},
        {'set_variable': {'var': '答对数', 'value': 0}},
        {'set_variable': {'var': '连对', 'value': 0}},
        {'set_variable': {'var': '最高连对', 'value': 0}},
        {'set_variable': {'var': '当前选项', 'value': 0}},
        {'broadcast': {'message': '出题'}},
    ],
    # ③ 出题：解除「已答」锁，进入答题态
    [
        {'when_receive': {'message': '出题'}},
        {'set_variable': {'var': 'game_state', 'value': 1}},
        {'set_variable': {'var': '已答', 'value': 0}},
        {'set_variable': {'var': '当前选项', 'value': 0}},
    ],
    # ④ 判题：单点集中，带状态锁，防连点重复计分
    [
        {'when_receive': {'message': '提交答案'}},
        {'if': {
            'cond': {'and': [EQ(V('已答'), 0), EQ(V('game_state'), 1)]},
            'do': [
                {'set_variable': {'var': '已答', 'value': 1}},
                {'set_variable': {'var': 'game_state', 'value': 2}},
                {'if_else': {
                    'cond': EQ(V('当前选项'), ITEM('正确答案')),
                    'do': [
                        {'change_variable': {'var': '分数', 'by': 10}},
                        {'change_variable': {'var': '答对数', 'by': 1}},
                        {'change_variable': {'var': '连对', 'by': 1}},
                        {'if': {
                            'cond': {'gt': [V('连对'), V('最高连对')]},
                            'do': [{'set_variable': {'var': '最高连对', 'value': V('连对')}}],
                        }},
                        {'broadcast': {'message': '答对了'}},
                    ],
                    'else': [
                        {'set_variable': {'var': '连对', 'value': 0}},
                        {'broadcast': {'message': '答错了'}},
                    ],
                }},
                {'wait': 1.0},
                {'broadcast': {'message': '下一题'}},
            ],
        }},
    ],
    # ⑤ 推进：越界检查必须在读列表之前，否则读空串会静默算错
    [
        {'when_receive': {'message': '下一题'}},
        {'change_variable': {'var': '题号', 'by': 1}},
        {'if_else': {
            'cond': {'gt': [V('题号'), V('题目总数')]},
            'do': [
                {'set_variable': {'var': 'game_state', 'value': 3}},
                {'broadcast': {'message': '结算'}},
            ],
            'else': [
                {'broadcast': {'message': '出题'}},
            ],
        }},
    ],
]

sprites = []

# 题板：造型名列表驱动，题号 → 造型名，加题不用改脚本
sprites.append({
    'name': '题板',
    'x': 0, 'y': 65,
    'costumes': [{'name': n, 'asset': 'assets/quiz/q%d.png' % i}
                 for i, (n, _, _, _) in enumerate(Q, 1)],
    'scripts': [
        [{'when_green_flag_clicked': None}, {'hide': None}],
        [{'when_receive': {'message': '出题'}},
         {'switch_costume': {'costume': ITEM('题板名')}},
         {'show': None}],
        [{'when_receive': {'message': '结算'}}, {'hide': None}],
    ],
})

# 反馈牌：对/错两套造型
sprites.append({
    'name': '反馈牌',
    'x': 0, 'y': -10,
    'costumes': [
        {'name': '对', 'asset': 'assets/quiz/right.png'},
        {'name': '错', 'asset': 'assets/quiz/wrong.png'},
    ],
    'scripts': [
        [{'when_green_flag_clicked': None}, {'hide': None}],
        [{'when_receive': {'message': '答对了'}},
         {'switch_costume': {'costume': '对'}}, {'show': None}],
        [{'when_receive': {'message': '答错了'}},
         {'switch_costume': {'costume': '错'}}, {'show': None}],
        [{'when_receive': {'message': '出题'}}, {'hide': None}],
    ],
})

# 结算牌
sprites.append({
    'name': '结算牌',
    'x': 0, 'y': 30,
    'costumes': [{'name': '结束', 'asset': 'assets/quiz/final.png'}],
    'scripts': [
        [{'when_green_flag_clicked': None}, {'hide': None}],
        [{'when_receive': {'message': '结算'}}, {'show': None}],
        [{'when_receive': {'message': '重置'}}, {'hide': None}],
    ],
})

# 四个选项按钮：只负责「把自己的序号写进全局变量 + 广播」，判题全在舞台
for i, letter in enumerate('ABCD', 1):
    sprites.append({
        'name': '选项' + letter,
        'x': -165 + (i - 1) * 110,
        'y': -95,
        'costumes': [{'name': letter, 'asset': 'assets/quiz/btn_%d.png' % i}],
        'scripts': [
            [{'when_green_flag_clicked': None}, {'hide': None}],
            [{'when_receive': {'message': '开始答题'}}, {'show': None}],
            [{'when_receive': {'message': '结算'}}, {'hide': None}],
            # ⚠️ 防连点锁必须放在**按钮侧**：Scratch 的 broadcast 会重启同名帽子线程，
            # 若反馈期间再次广播「提交答案」，正在 wait 的判题脚本会被杀掉，
            # 「broadcast 下一题」永远不执行 → 游戏卡死。锁在舞台判题脚本里来不及。
            [{'when_this_sprite_clicked': None},
             {'if': {
                 'cond': {'and': [EQ(V('已答'), 0), EQ(V('game_state'), 1)]},
                 'do': [
                     {'set_variable': {'var': '当前选项', 'value': i}},
                     {'broadcast': {'message': '提交答案'}},
                 ],
             }}],
        ],
    })

ir = {'project': {
    'name': '四题测验',
    'title_screen': {
        'backdrop': 'assets/quiz/title_bg.png',
        'button': {'asset': 'assets/quiz/btn_start.png', 'x': 0, 'y': -110},
        'game_backdrop': '答题',
        'broadcast': '开始答题',
    },
    'stage': {
        'backdrops': [{'name': '答题', 'asset': 'assets/backdrop1.svg'}],
        'variables': {
            'game_state': 0,   # 0首页 1答题 2反馈 3结算
            '题号': 1,
            '题目总数': len(Q),
            '当前选项': 0,
            '已答': 0,        # 防连点锁
            '分数': 0,
            '答对数': 0,
            '连对': 0,
            '最高连对': 0,
        },
        'lists': {
            '正确答案': [a for _, _, _, a in Q],
            '题板名': [n for n, _, _, _ in Q],
        },
        'scripts': stage_scripts,
    },
    'sprites': sprites,
}}

out = sys.argv[1]
with open(out, 'w', encoding='utf-8') as f:
    yaml.safe_dump(ir, f, allow_unicode=True, sort_keys=False)
print('已生成 %s（%d 题，%d 角色）' % (out, len(Q), len(sprites)))
