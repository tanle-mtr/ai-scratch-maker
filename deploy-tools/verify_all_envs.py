"""校验各 agent 环境里的 ai-scratch-maker 安装是否完整可用。

检查项：
1. 目录存在且文件数与源一致
2. SKILL.md 的 frontmatter 可解析、name 正确、description 非空
3. 关键文件齐全（build_sb3.py / validate_sb3.py / references/blocks-spec.json / examples）
4. 正文与源一致（允许 frontmatter 与「安装位置」段落有差异）
"""
import os
import re
import sys
import yaml

SRC = os.path.expanduser('~/.workbuddy/skills/ai-scratch-maker')

ENVS = [
    ('WorkBuddy', os.path.expanduser('~/.workbuddy/skills/ai-scratch-maker')),
    ('Claude', os.path.expanduser('~/.claude/skills/ai-scratch-maker')),
    ('Codex', os.path.expanduser('~/.codex/skills/ai-scratch-maker')),
    ('Cursor', os.path.expanduser('~/.cursor/skills/ai-scratch-maker')),
    ('opencode', os.path.expanduser('~/.config/opencode/skill/ai-scratch-maker')),
    ('avlcode', os.path.expanduser('~/.config/avlcode/skills/ai-scratch-maker')),
]

KEY_FILES = [
    'SKILL.md',
    'scripts/build_sb3.py',
    'scripts/validate_sb3.py',
    'scripts/validate_schema.mjs',
    'scripts/adapt_skill_md.py',
    'scripts/make_portable_md.py',
    'references/blocks-spec.json',
    'references/blocks.md',
    'references/ir-format.md',
    'references/sb3-schema/sb3_schema.json',
    'references/sb3-schema/sb3_definitions.json',
    'examples/cat_mouse.yaml',
    'examples/ref_minecraft3d.yaml',
]


def count_files(root):
    n = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != '__pycache__']
        n += len(fns)
    return n


def body_of(path):
    t = open(path, encoding='utf-8').read()
    m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n(.*)$', t, re.S)
    return (m.group(2) if m else t), (m.group(1) if m else '')


def main():
    src_n = count_files(SRC)
    src_body, _ = body_of(os.path.join(SRC, 'SKILL.md'))
    # 源含「安装位置」段落，其它环境为环境无关版本，比较时剔除该段
    def strip_env_block(s):
        return re.sub(r'## 安装位置与运行环境.*?(?=\n## )', '', s, flags=re.S)

    src_cmp = strip_env_block(src_body)
    all_ok = True
    print('源文件数: %d\n' % src_n)
    print('%-12s %-8s %-9s %-9s %-9s' % ('环境', '文件数', 'frontmatter', '关键文件', '正文一致'))
    print('-' * 56)
    for name, root in ENVS:
        if not os.path.isdir(root):
            print('%-12s MISSING' % name)
            all_ok = False
            continue
        n = count_files(root)
        fm_ok = 'OK'
        try:
            t = open(os.path.join(root, 'SKILL.md'), encoding='utf-8').read()
            m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', t, re.S)
            d = yaml.safe_load(m.group(1)) if m else {}
            if not d.get('name') == 'ai-scratch-maker':
                fm_ok = 'BAD_NAME'
            elif not (d.get('description') or '').strip():
                fm_ok = 'EMPTY_DESC'
        except Exception as e:
            fm_ok = 'ERR'
        miss = [f for f in KEY_FILES if not os.path.exists(os.path.join(root, f))]
        key_ok = 'OK' if not miss else 'MISS:%d' % len(miss)
        body, _ = body_of(os.path.join(root, 'SKILL.md'))
        body_ok = 'YES' if strip_env_block(body).strip() == src_cmp.strip() else 'DIFF'
        if fm_ok != 'OK' or key_ok != 'OK' or body_ok != 'YES':
            all_ok = False
        print('%-12s %-8s %-9s %-9s %-9s' % (
            name, '%d%s' % (n, '' if n == src_n else '!'), fm_ok, key_ok, body_ok))
        if miss:
            print('    缺失: %s' % ', '.join(miss[:4]))
    print('\n总体: %s' % ('全部一致 ✅' if all_ok else '存在问题 ❌'))
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
