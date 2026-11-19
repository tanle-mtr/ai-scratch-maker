"""生成语义探针 IR：一批典型表达式，编译后由 scratch-vm 实跑，对比期望值。

用法: python semantic_probe_gen.py <输出yaml>
"""
import sys
import yaml

CASES = []  # (变量名, 表达式, 期望值)


def add(name, expr, expect):
    CASES.append((name, expr, expect))


# --- 算术 ---
add('t01', {'add': [2, 3]}, 5)
add('t02', {'subtract': [10, 4]}, 6)
add('t03', {'multiply': [3, 4]}, 12)
add('t04', {'divide': [12, 4]}, 3)
add('t05', {'mod': [17, 5]}, 2)
add('t06', {'round': [3.6]}, 4)
add('t07', {'mathop': {'op': 'abs', 'num': -7}}, 7)
add('t08', {'mathop': {'op': 'sqrt', 'num': 9}}, 3)
add('t09', {'add': [1, {'add': [2, 3]}]}, 6)
add('t10', {'subtract': [10, {'subtract': [3, 1]}]}, 8)
# --- 比较 ---
add('t11', {'equals': [5, 5]}, True)
add('t12', {'lt': [3, 5]}, True)
add('t13', {'gt': [3, 5]}, False)
add('t14', {'equals': ['5', 5]}, True)   # Scratch 里字符串数字相等
# --- 逻辑 ---
add('t15', {'and': [{'equals': [1, 1]}, {'equals': [2, 2]}]}, True)
add('t16', {'or': [{'equals': [1, 2]}, {'equals': [3, 3]}]}, True)
add('t17', {'not': {'operand': {'equals': [1, 2]}}}, True)
# --- 字符串 ---
add('t18', {'join': ['ab', 'cd']}, 'abcd')
add('t19', {'letter_of': [2, 'abc']}, 'b')
add('t20', {'length_of': ['hello']}, 5)
add('t21', {'contains': ['hello', 'ell']}, True)
# --- 变量引用 ---
add('t22', {'add': [{'var': '基数'}, 7]}, 17)

scripts = []
body = [{'when_green_flag_clicked': None}]
for name, expr, _ in CASES:
    body.append({'set_variable': {'var': name, 'value': expr}})

# 控制流探针
body.append({'set_variable': {'var': 'c01', 'value': 0}})
body.append({'repeat': {'times': 3, 'do': [{'change_variable': {'var': 'c01', 'value': 2}}]}})

body.append({'set_variable': {'var': 'c02', 'value': 0}})
body.append({'if_else': {
    'cond': {'equals': [1, 1]},
    'do': [{'set_variable': {'var': 'c02', 'value': 11}}],
    'else': [{'set_variable': {'var': 'c02', 'value': 22}}],
}})

body.append({'set_variable': {'var': 'c03', 'value': 0}})
body.append({'if_else': {
    'cond': {'equals': [1, 2]},
    'do': [{'set_variable': {'var': 'c03', 'value': 11}}],
    'else': [{'set_variable': {'var': 'c03', 'value': 33}}],
}})

# 列表操作
body.append({'add_to_list': {'item': 'apple', 'list': '测试列表'}})
body.append({'add_to_list': {'item': 'banana', 'list': '测试列表'}})
body.append({'set_variable': {'var': 'c04', 'value': {
    'item_of_list': {'index': 2, 'list': '测试列表'}}}})
body.append({'set_variable': {'var': 'c05', 'value': {
    'length_of_list': {'list': '测试列表'}}}})

variables = {'基数': 10}
for name, _, _ in CASES:
    variables[name] = 0
variables.update({'c01': 0, 'c02': 0, 'c03': 0, 'c04': 0, 'c05': 0})

ir = {
    'project': {
        'name': '语义探针',
        'stage': {
            'backdrops': [{'name': '背景1', 'asset': 'assets/backdrop1.svg'}],
            'variables': variables,
            'lists': {'测试列表': []},
            'scripts': [body],
        },
    }
}

out = sys.argv[1]
with open(out, 'w', encoding='utf-8') as f:
    yaml.safe_dump(ir, f, allow_unicode=True, sort_keys=False)

expected = {n: e for n, _, e in CASES}
expected.update({'c01': 6, 'c02': 11, 'c03': 33, 'c04': 'banana', 'c05': 2})
with open(out + '.expected.yaml', 'w', encoding='utf-8') as f:
    yaml.safe_dump(expected, f, allow_unicode=True, sort_keys=False)
print('已生成 %d 个语义用例 -> %s' % (len(expected), out))
