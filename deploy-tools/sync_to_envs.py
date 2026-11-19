"""把 skill 本体的变更同步到各 agent 环境与开发副本。

同步内容：scripts/、references/、examples/、node_modules/、SKILL.md、README.md。
外部环境的 SKILL.md 需做 frontmatter 适配（name + description）。
"""
import os
import shutil
import subprocess
import sys

HOME = os.path.expanduser('~')
SRC = os.path.join(HOME, '.workbuddy', 'skills', 'ai-scratch-maker')
DEV = r'E:\编程作品\作品\豆包\AI制作schatch作品的skill\ai-scratch-maker'
TOOLS = r'E:\编程作品\作品\豆包\AI制作schatch作品的skill\deploy-tools'

ENVS = [
    os.path.join(HOME, '.claude', 'skills', 'ai-scratch-maker'),
    os.path.join(HOME, '.codex', 'skills', 'ai-scratch-maker'),
    os.path.join(HOME, '.cursor', 'skills', 'ai-scratch-maker'),
    os.path.join(HOME, '.config', 'opencode', 'skill', 'ai-scratch-maker'),
    os.path.join(HOME, '.config', 'avlcode', 'skills', 'ai-scratch-maker'),
]

# 顶层同步的内容
TOP_ITEMS = ['scripts', 'references', 'examples', 'node_modules', 'SKILL.md', 'README.md']
SKIP_DIRS = {'__pycache__', '.workbuddy'}


def sync_tree(src, dst):
    """把 src 目录内容同步到 dst（覆盖同名，保留 dst 其它内容）。"""
    n = 0
    for dp, dns, fns in os.walk(src):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        rel = os.path.relpath(dp, src)
        target_dir = dst if rel == '.' else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for f in fns:
            if f.endswith(('.pyc', '.pyo')):
                continue
            s = os.path.join(dp, f)
            d = os.path.join(target_dir, f)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    return n


def adapt(target):
    """把 frontmatter 收敛为 name + description。"""
    script = os.path.join(TOOLS, 'adapt_skill_md.py')
    if not os.path.exists(script):
        return
    subprocess.run([sys.executable, script, target, '--mode', 'minimal'],
                   capture_output=True, text=True)


def main():
    total = 0
    print('同步源（唯一权威副本）: %s' % SRC)
    print('⚠ 改动请先写到这里，再运行本脚本；直接改开发副本会被覆盖。\n')
    print('=== 开发副本 ===')
    n = 0
    for item in TOP_ITEMS:
        s = os.path.join(SRC, item)
        d = os.path.join(DEV, item)
        if os.path.isdir(s):
            n += sync_tree(s, d)
        elif os.path.exists(s):
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    print('  同步 %d 个文件 -> %s' % (n, DEV))
    total += n

    print('\n=== 各 agent 环境 ===')
    for env in ENVS:
        if not os.path.isdir(os.path.dirname(env)):
            print('  跳过(无父目录): %s' % env)
            continue
        n = 0
        for item in TOP_ITEMS:
            s = os.path.join(SRC, item)
            d = os.path.join(env, item)
            if os.path.isdir(s):
                n += sync_tree(s, d)
            elif os.path.exists(s):
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
                n += 1
        adapt(env)
        print('  %-56s 同步 %d 个文件' % (os.path.basename(os.path.dirname(env)), n))
        total += n

    print('\n合计同步 %d 个文件' % total)


if __name__ == '__main__':
    main()
