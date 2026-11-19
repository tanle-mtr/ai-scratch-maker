"""把 ai-scratch-maker skill 一次安装/同步到本机所有 agent 环境。

用法：
    python scripts/install_all_envs.py            # 安装/同步（覆盖已有同名目录）
    python scripts/install_all_envs.py --check    # 只检查，不改动
    python scripts/install_all_envs.py --dry-run  # 试运行，打印将执行的动作

环境清单（自动探测存在性）：
    WorkBuddy   ~/.workbuddy/skills/ai-scratch-maker
    Claude      ~/.claude/skills/ai-scratch-maker
    Codex       ~/.codex/skills/ai-scratch-maker
    Cursor      ~/.cursor/skills/ai-scratch-maker
    opencode    ~/.config/opencode/skill/ai-scratch-maker
    avlcode     ~/.config/avlcode/skills/ai-scratch-maker

跨环境适配（自动完成）：
    1. frontmatter 收敛为各环境通行的 name + description（去掉 WorkBuddy 专属的 type/version）
    2. 「安装位置」段落改写为环境无关表述（skill 根目录 = SKILL.md 所在目录）
    3. 清理 __pycache__
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)

ENVS = [
    ('WorkBuddy', '~/.workbuddy/skills/ai-scratch-maker'),
    ('Claude', '~/.claude/skills/ai-scratch-maker'),
    ('Codex', '~/.codex/skills/ai-scratch-maker'),
    ('Cursor', '~/.cursor/skills/ai-scratch-maker'),
    ('opencode', '~/.config/opencode/skill/ai-scratch-maker'),
    ('avlcode', '~/.config/avlcode/skills/ai-scratch-maker'),
]

ADAPT_SCRIPT = os.path.join(HERE, 'adapt_skill_md.py')
PORTABLE_SCRIPT = os.path.join(HERE, 'make_portable_md.py')


def count_files(root):
    n = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != '__pycache__']
        n += len(fns)
    return n


def copy_tree(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.workbuddy'))


def run_script(path, target, args):
    if not os.path.exists(path):
        return None
    cmd = [sys.executable, path, target] + args
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def main():
    check_only = '--check' in sys.argv
    dry = '--dry-run' in sys.argv

    src_n = count_files(SKILL_ROOT)
    print('源 skill: %s  (%d 个文件)\n' % (SKILL_ROOT, src_n))

    print('%-12s %-52s %-10s' % ('环境', '目标路径', '状态'))
    print('-' * 80)

    ok_all = True
    for name, rel in ENVS:
        target = os.path.expanduser(rel)
        base = os.path.dirname(target)
        if not os.path.isdir(base):
            print('%-12s %-52s %-10s' % (name, rel, '跳过(无目录)'))
            continue

        if check_only:
            if not os.path.isdir(target):
                print('%-12s %-52s %-10s' % (name, rel, '未安装'))
                ok_all = False
                continue
            n = count_files(target)
            state = 'OK' if n == src_n else '差异(%d)' % n
            print('%-12s %-52s %-10s' % (name, rel, state))
            if n != src_n:
                ok_all = False
            continue

        if dry:
            print('%-12s %-52s %-10s' % (name, rel, '将安装'))
            continue

        try:
            # 源与目标可能是同一目录（如 WorkBuddy 本体）→ 跳过复制，只做校验
            same = os.path.normcase(os.path.abspath(target)) == os.path.normcase(os.path.abspath(SKILL_ROOT))
            if same:
                print('%-12s %-52s %-10s' % (name, rel, '即源目录(跳过)'))
                continue
            copy_tree(SKILL_ROOT, target)
            # WorkBuddy 本体保留自身的 frontmatter 与安装段落，不做适配
            if name != 'WorkBuddy':
                run_script(ADAPT_SCRIPT, target, ['--mode', 'minimal'])
                run_script(PORTABLE_SCRIPT, target, [])
            for dp, dns, _ in os.walk(target):
                for d in list(dns):
                    if d == '__pycache__':
                        shutil.rmtree(os.path.join(dp, d), ignore_errors=True)
                        dns.remove(d)
            n = count_files(target)
            print('%-12s %-52s %-10s' % (name, rel, '已安装(%d)' % n))
        except Exception as e:
            ok_all = False
            print('%-12s %-52s %-10s' % (name, rel, '失败:%s' % e))

    if check_only:
        print('\n检查结果: %s' % ('全部正常 ✅' if ok_all else '存在差异 ❌'))
        return 0 if ok_all else 1
    print('\n完成。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
