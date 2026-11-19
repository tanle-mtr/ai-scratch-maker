"""第二轮语义探针：字段、菜单、别名、过程、列表编辑、克隆开关。

生成两个角色 + 舞台，全部结果写进全局变量，便于运行时比对。
"""
import sys
import yaml

# ---------- 舞台 ----------
stage_body = [{'when_green_flag_clicked': None}]

# 1) 自定义过程：无返回值，用全局变量模拟
stage_body += [
    {'set_variable': {'var': 'p01', 'value': 0}},
    {'call': {'proc': 'addtwo %n %n', 'args': [3, 4]}},
]

# 2) 列表编辑：add / insert / replace / delete / item / length / index_of
stage_body += [
    {'add_to_list': {'item': 'A', 'list': 'L'}},
    {'add_to_list': {'item': 'B', 'list': 'L'}},
    {'add_to_list': {'item': 'C', 'list': 'L'}},
    {'insert_at_list': {'item': 'X', 'index': 2, 'list': 'L'}},
    {'set_variable': {'var': 'l01', 'value': {'item_of_list': {'index': 2, 'list': 'L'}}}},
    {'replace_item_of_list': {'index': 3, 'item': 'Y', 'list': 'L'}},
    {'set_variable': {'var': 'l02', 'value': {'item_of_list': {'index': 3, 'list': 'L'}}}},
    {'set_variable': {'var': 'l03', 'value': {'length_of_list': {'list': 'L'}}}},
    {'set_variable': {'var': 'l04', 'value': {'item_num_of_list': {'item': 'Y', 'list': 'L'}}}},
    {'delete_of_list': {'index': 1, 'list': 'L'}},
    {'set_variable': {'var': 'l05', 'value': {'item_of_list': {'index': 1, 'list': 'L'}}}},
    {'set_variable': {'var': 'l06', 'value': {'list_contains': {'item': 'Y', 'list': 'L'}}}},
]

# 3) 侦测/输入字段
stage_body += [
    {'set_variable': {'var': 's01', 'value': {'key_pressed': {'key': 'space'}}}},
    {'set_variable': {'var': 's02', 'value': {'mousedown': None}}},
    {'set_variable': {'var': 's03', 'value': {'timer': None}}},
    {'set_variable': {'var': 's04', 'value': {'answer': None}}},
]

# 4) 运算字段（mathop 菜单）
stage_body += [
    {'set_variable': {'var': 'm01', 'value': {'mathop': {'op': 'floor', 'num': 3.9}}}},
    {'set_variable': {'var': 'm02', 'value': {'mathop': {'op': 'ceiling', 'num': 3.1}}}},
    {'set_variable': {'var': 'm03', 'value': {'mathop': {'op': 'sin', 'num': 90}}}},
]

# 5) 广播 + 接收
stage_body += [
    {'broadcast': {'message': '测试广播'}},
]

vars_ = {}
for n in ['p01', 'l01', 'l02', 'l03', 'l04', 'l05', 'l06',
          's01', 's02', 's03', 's04', 'm01', 'm02', 'm03', 'b01']:
    vars_[n] = 0

stage = {
    'backdrops': [{'name': '背景1', 'asset': 'assets/backdrop1.svg'}],
    'variables': vars_,
    'lists': {'L': []},
    'procedures': [{
        'name': 'addtwo %n %n',
        'args': ['a', 'b'],
        'script': [
            {'set_variable': {'var': 'p01', 'value': {
                'add': [{'var': 'a'},
                        {'var': 'b'}]}}},
        ],
    }],
    'scripts': [stage_body, [
        {'when_receive': {'message': '测试广播'}},
        {'set_variable': {'var': 'b01', 'value': 77}},
    ]],
}

# ---------- 角色：运动/外观/克隆字段 ----------
sprite_body = [
    {'when_green_flag_clicked': None},
    {'goto_xy': {'x': 10, 'y': 20}},
    {'change_x': {'dx': 5}},
    {'change_y': {'dy': 7}},
    {'set_variable': {'var': 'x01', 'value': {'x_position': None}}},
    {'set_variable': {'var': 'y01', 'value': {'y_position': None}}},
    {'set_size': {'value': 150}},
    {'set_variable': {'var': 'z01', 'value': {'size': None}}},
    {'create_clone_of': {'clone': '_myself_'}},
]

sprite = {
    'name': '测试角色',
    'x': 0, 'y': 0,
    'rotationStyle': 'all around',
    'costumes': [{'name': '造型1', 'asset': 'assets/dot.svg'}],
    'variables': {'x01': 0, 'y01': 0, 'z01': 0, 'c01': 0},
    'scripts': [sprite_body, [
        {'when_start_as_clone': None},
        {'set_variable': {'var': 'c01', 'value': 1}},
    ]],
}

ir = {'project': {
    'name': '字段语义探针',
    'stage': stage,
    'sprites': [sprite],
}}

out = sys.argv[1]
with open(out, 'w', encoding='utf-8') as f:
    yaml.safe_dump(ir, f, allow_unicode=True, sort_keys=False)
print('第二轮探针已生成 ->', out)
