"""把 WorkBuddy 版 SKILL.md 的 frontmatter 适配成各 agent 环境的通行格式。

WorkBuddy:  name / version / description / type
Claude/Codex/opencode/Cursor/avlcode 主流约定: name / description（未知字段通常被忽略，
但 type: skill 这类字段可能被误当枚举解析，故统一收敛到最小可用集）。

用法：python adapt_skill_md.py <skill目录> [--mode minimal|keep]
"""
import re
import sys
import os


def main():
    if len(sys.argv) < 2:
        print('用法: python adapt_skill_md.py <skill目录> [--mode minimal|keep]')
        sys.exit(2)
    root = sys.argv[1]
    mode = 'minimal'
    if '--mode' in sys.argv:
        mode = sys.argv[sys.argv.index('--mode') + 1]

    path = os.path.join(root, 'SKILL.md')
    if not os.path.exists(path):
        print('SKIP 未找到 SKILL.md: ' + path)
        return

    text = open(path, encoding='utf-8').read()
    m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n(.*)$', text, re.S)
    if not m:
        print('SKIP 无 frontmatter: ' + path)
        return

    head, body = m.group(1), m.group(2)

    # 解析出 name / description，保留原始描述文本（含中文与换行块）
    name = ''
    mname = re.search(r'^name:\s*(.+)$', head, re.M)
    if mname:
        name = mname.group(1).strip()

    desc = ''
    mdesc = re.search(r'^description:\s*>?\s*\n((?:\s{2,}.*\n?)+)', head, re.M)
    if mdesc:
        desc = mdesc.group(1)
    else:
        mdesc = re.search(r'^description:\s*(.+)$', head, re.M)
        if mdesc:
            desc = mdesc.group(1).strip()

    if not name or not desc:
        print('SKIP 无法解析 name/description: ' + path)
        return

    desc_lines = [ln.strip() for ln in desc.strip().split('\n')]
    desc_flat = ' '.join(ln for ln in desc_lines if ln).strip()
    desc_flat = re.sub(r'\s+', ' ', desc_flat)

    if mode == 'minimal':
        fm = 'name: %s\ndescription: %s' % (name, desc_flat)
    else:
        fm = head.rstrip('\n')

    out = '---\n%s\n---\n%s' % (fm, body)
    open(path, 'w', encoding='utf-8', newline='\n').write(out)
    print('OK %s  (mode=%s, desc=%d字)' % (path, mode, len(desc_flat)))


if __name__ == '__main__':
    main()
