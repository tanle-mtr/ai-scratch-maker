"""把 ai-scratch-maker skill 一次安装/同步到本机所有 agent 环境。

用法：
    python scripts/install_all_envs.py            # 安装/同步（覆盖已有同名目录）
    python scripts/install_all_envs.py --check    # 只检查，不改动
    python scripts/install_all_envs.py --dry-run  # 试运行，打印将执行的动作
    python scripts/install_all_envs.py --no-prune # 保留目标里的源外文件（默认会清理残留）

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

同步语义：
    - 跳过 .build_cache / build_tmp / _anim_test / *.log / _t.sb3 等编译缓存与调试残留，
      否则实测会把 243MB 缓存灌进每个环境。
    - 默认「精确镜像」：删除目标中源已不存在的文件，保证多副本字节对齐且无历史残留。
    """
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# skill 根目录解析：deploy-tools/ 与 skill 目录同级 → 上两级才是仓库根，仓库根下才是
# ai-scratch-maker/。这里必须显式找「含 SKILL.md 的那一层」，否则会把**仓库根**
# （含 deploy-tools/、历史 zip、.git 等）当成 skill 源同步出去，把各环境副本弄脏。
# （历史事故：2026-11-19 用 os.path.dirname(HERE) 直接取仓库根，导致 5 个环境副本
#  里的 scripts/ references/ examples/ 被误判为「源外文件」而整目录删除。）
_PARENT = os.path.dirname(HERE)
_GRAND = os.path.dirname(_PARENT)
_CANDIDATES = [
    os.path.join(_PARENT, 'ai-scratch-maker'),   # deploy-tools/../ai-scratch-maker（标准布局）
    _PARENT,                                     # deploy-tools/..  （脚本在 skill 内时）
    _GRAND,                                      # deploy-tools/../..（skill 在仓库根时）
]
SKILL_ROOT = next((c for c in _CANDIDATES
                    if os.path.exists(os.path.join(c, 'SKILL.md'))), _PARENT)
if not os.path.exists(os.path.join(SKILL_ROOT, 'SKILL.md')):
    sys.exit('[FATAL] 未定位到 skill 根目录（含 SKILL.md）：%s' % SKILL_ROOT)

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


# 同步时必须忽略的目录/文件：编译缓存与临时产物。
# 实测 .build_cache 158MB + build_tmp 85MB，原样拷贝会往 5 个环境各灌 243MB 垃圾，
# 还会把 _t.sb3 / *.log 这类调试残留带进交付副本。
# .workbuddy 不复制也不清理：各 agent 可能在自己的副本里放工程记忆，属agent 私有状态。
IGNORE_PATTERNS = [
    '__pycache__', '*.pyc', '*.pyo', '.workbuddy', '.git',
    '.build_cache', 'build_tmp', '_anim_test',
    '_t.sb3', '*.log',
]
# 「精确镜像」清理时：这些目录属于运行时产物，源里没有 → 直接从目标删除。
RUNTIME_DIRS = {'__pycache__', '.build_cache', 'build_tmp', '_anim_test'}
# 这些目录既不清理也不动内容（agent 私有状态）。
PROTECTED_DIRS = {'.workbuddy', '.git'}


def count_files(root):
    n = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in ('__pycache__', '.build_cache',
                                              'build_tmp', '_anim_test')]
        n += len(fns)
    return n


def copy_tree(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))


def prune_stale(src, dst):
    """删除 dst 中源已不存在的文件，让副本与源「精确镜像」。

    shutil.copytree(dirs_exist_ok=True) 只覆盖同名文件，历史残留会永久滞留：
    实测 work 副本因此多出 88 个 assets/community/generated/ 占位文件。

    安全阀：src 与 dst 必须都像 skill 根（含 SKILL.md），否则直接拒绝清理。
    历史上正是因为源被误解析成仓库根，把各环境副本的 scripts/ references/ examples/
    整目录当成「源外文件」删掉了。
    返回删除的条目数。
    """
    for root in (src, dst):
        if not os.path.exists(os.path.join(root, 'SKILL.md')):
            raise RuntimeError('prune_stale 安全阀：%s 不含 SKILL.md，疑似不是 skill 根' % root)
    removed = 0
    for dp, dns, fns in os.walk(dst, topdown=False):
        rel = os.path.relpath(dp, dst)
        if rel == '.':
            # 目标根目录：也要清理「源里没有的顶层文件」。
            # 历史上这里直接 continue，导致 LICENSE / 历史 zip / 开发文档 等
            # 仓库根残留永远清不掉（work 副本实测多出 12 个）。
            for f in fns:
                if f.endswith(('.pyc', '.pyo', '.log')) or f == '_t.sb3':
                    continue
                if not os.path.exists(os.path.join(src, f)):
                    try:
                        os.remove(os.path.join(dp, f))
                        removed += 1
                    except OSError:
                        pass
            continue
        parts = rel.replace('\\', '/').split('/')
        if any(p in PROTECTED_DIRS for p in parts):
            continue
        if any(p in RUNTIME_DIRS for p in parts):
            shutil.rmtree(dp, ignore_errors=True)
            removed += 1
            continue
        src_dir = os.path.join(src, rel)
        if not os.path.isdir(src_dir):
            shutil.rmtree(dp, ignore_errors=True)
            removed += 1
            continue
        for f in fns:
            if f.endswith(('.pyc', '.pyo', '.log')) or f == '_t.sb3':
                continue
            if not os.path.exists(os.path.join(src_dir, f)):
                try:
                    os.remove(os.path.join(dp, f))
                    removed += 1
                except OSError:
                    pass
    return removed


def run_script(path, target, args):
    if not os.path.exists(path):
        return None
    cmd = [sys.executable, path, target] + args
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def main():
    check_only = '--check' in sys.argv
    dry = '--dry-run' in sys.argv
    # 默认精确镜像：删除目标里源已不存在的文件，保证多副本「字节对齐」。
    # 若某个环境副本放了自有文件，加 --no-prune 保留它们。
    prune = '--no-prune' not in sys.argv

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
            pruned = prune_stale(SKILL_ROOT, target) if prune else 0
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
            extra = ' (清理残留%d)' % pruned if pruned else ''
            print('%-12s %-52s %-10s' % (name, rel, '已安装(%d)%s' % (n, extra)))
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
