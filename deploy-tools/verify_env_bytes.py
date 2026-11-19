"""逐字节校验各 agent 环境里的 ai-scratch-maker 副本与开发副本是否一致。

检查项：
1. 文件集合一致（源有副本也要有，副本不能有源没有的残留）
2. 除 SKILL.md 外，所有文件内容字节一致
3. SKILL.md 正文一致（frontmatter 允许按环境适配差异；WorkBuddy 本体允许完全一致）

用法：
    python deploy-tools/verify_env_bytes.py            # 校验全部环境
    python deploy-tools/verify_env_bytes.py --json     # 机器可读输出
退出码：0 = 全部一致；1 = 存在差异。
"""
import hashlib
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, 'ai-scratch-maker')

ENVS = [
    ('WorkBuddy', '~/.workbuddy/skills/ai-scratch-maker'),
    ('Claude', '~/.claude/skills/ai-scratch-maker'),
    ('Codex', '~/.codex/skills/ai-scratch-maker'),
    ('Cursor', '~/.cursor/skills/ai-scratch-maker'),
    ('opencode', '~/.config/opencode/skill/ai-scratch-maker'),
    ('avlcode', '~/.config/avlcode/skills/ai-scratch-maker'),
]

SKIP_DIRS = {'__pycache__', '.build_cache', 'build_tmp', '_anim_test', '.git'}
# .workbuddy 是 agent 私有状态，不参与比对。
PROTECTED = {'.workbuddy'}


def files(root):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for f in fns:
            if f.endswith(('.pyc', '.pyo', '.log')) or f == '_t.sb3':
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root).replace(os.sep, '/')
            if any(seg in PROTECTED for seg in rel.split('/')):
                continue
            out[rel] = p
    return out


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def body_of(path):
    """去掉 frontmatter 后的正文，用于跨环境比对（各环境 frontmatter 会被适配）。"""
    try:
        t = open(path, encoding='utf-8').read()
    except (OSError, UnicodeDecodeError):
        return None
    m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n(.*)$', t, re.S)
    return m.group(2) if m else t


def check(name, target):
    if not os.path.isdir(target):
        return {'env': name, 'status': 'MISSING'}
    s, t = files(SRC), files(target)
    only_src = sorted(set(s) - set(t))
    only_dst = sorted(set(t) - set(s))
    diff = []
    for rel in sorted(set(s) & set(t)):
        if rel == 'SKILL.md':
            if body_of(s[rel]) != body_of(t[rel]):
                diff.append(rel)
            continue
        if sha(s[rel]) != sha(t[rel]):
            diff.append(rel)
    ok = not (only_src or only_dst or diff)
    return {
        'env': name,
        'status': 'OK' if ok else 'DIFF',
        'src_files': len(s),
        'dst_files': len(t),
        'only_src': only_src[:20],
        'only_dst': only_dst[:20],
        'diff': diff[:20],
    }


def main():
    as_json = '--json' in sys.argv
    results = []
    for name, rel in ENVS:
        results.append(check(name, os.path.expanduser(rel)))

    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print('源 skill: %s\n' % SRC)
        print('%-12s %-10s %-10s %s' % ('环境', '状态', '文件数', '差异'))
        print('-' * 72)
        for r in results:
            if r['status'] == 'MISSING':
                print('%-12s %-10s' % (r['env'], '未安装'))
                continue
            detail = ''
            if r['only_src']:
                detail += '缺:%d ' % len(r['only_src'])
            if r['only_dst']:
                detail += '多:%d ' % len(r['only_dst'])
            if r['diff']:
                detail += '内容差异:%d ' % len(r['diff'])
            print('%-12s %-10s %-10s %s' % (r['env'], r['status'],
                                           '%d/%d' % (r['dst_files'], r['src_files']),
                                           detail or '无'))
            for x in (r['only_src'] + r['only_dst'] + r['diff'])[:8]:
                print('        ·', x)
    ok = all(r['status'] in ('OK', 'MISSING') for r in results)
    if not as_json:
        print('\n结果: %s' % ('全部一致 ✅' if ok else '存在差异 ❌'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
