"""把 ai-scratch-maker skill 打包成可分发的 zip。

排除项：
  - __pycache__ / *.pyc            编译缓存
  - scripts/_*.py / *.bak / *.tmp  一次性补丁与临时文件
  - .workbuddy/                     项目记忆（不属于 skill 本体）
  - 根目录 猫抓老鼠.sb3             遗留产物，与 examples/output/cat_mouse.sb3 重复且无文档引用
  - agents/openai.yaml             WorkBuddy 专属 agent 定义（其他环境不识别）
  - .build_cache/ build_tmp/       产物缓存与构建临时目录（实测可达 200MB+，纯临时）
  - _anim_test/ _t.sb3 *.log       调试产物 / 临时 sb3 副本 / verify 运行日志
  注：.scaffold_index.json 被 retrieve_scaffold.py 当索引读取，raw_assets/ 是
  generate_staged --raw-assets 的可选输入样本，两者都不能排除。

用法：
    python pack_skill.py                 # 输出 ai-scratch-maker-v<version>.zip
    python pack_skill.py --out custom.zip
    python pack_skill.py --portable --out x.zip  # 通用两字段 frontmatter（跨 agent）
    python pack_skill.py --exclude-outputs   # 不打包 examples/output（体积可降约 4MB）
"""
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
# deploy-tools/ 与 skill 目录同级 → 上两级才是 skill 根；
# 若本脚本被放进 skill/scripts/ 内，则上一级就是 skill 根。
_PARENT = os.path.dirname(HERE)
_GRAND = os.path.dirname(_PARENT)
_CANDIDATES = [
    os.path.join(_PARENT, 'ai-scratch-maker'),   # deploy-tools/../ai-scratch-maker
    _PARENT,                                      # skill/scripts/..  (脚本在 skill 内时)
    _GRAND,                                       # skill/..          (脚本在 skill 内时)
]
SKILL_ROOT = next((c for c in _CANDIDATES
                    if os.path.exists(os.path.join(c, 'SKILL.md'))), _PARENT)

# 仓库根（LICENSE / THIRD-PARTY-NOTICES.md 所在层）。标准布局是 repo/ai-scratch-maker/，
# 故仓库根 = skill 根的上一级。
REPO_ROOT = os.path.dirname(SKILL_ROOT)
# 分发包必须自带许可与第三方声明：仓库本身以 CC BY-SA 4.0 授权，且社区素材包有
# 「对外分发前须回溯原作者授权」的明确限制（见 THIRD-PARTY-NOTICES.md）。
# 2026-11-19 体检发现 v0.22.0 包里只有 node_modules 自带的 LICENSE，
# 仓库自己的许可与第三方声明**根本没进包**——接收方无从得知授权条款。
EXTRA_FILES = ['LICENSE', 'THIRD-PARTY-NOTICES.md']

EXCLUDE_DIRS = {'__pycache__', '.workbuddy', '.git',
                '.build_cache', 'build_tmp', '_anim_test'}
# 相对 skill 根的路径（不含分隔符差异），逐项精确排除
EXCLUDE_PATHS = {
    '猫抓老鼠.sb3',              # 根目录交付件（examples/output/cat_mouse.sb3 才是标准位置）
    'agents/openai.yaml',        # WorkBuddy 专属界面定义，其他 agent 不识别
    '_t.sb3',                    # 构建调试用的临时 sb3 副本
}
EXCLUDE_SUFFIX = ('.pyc', '.pyo', '.bak', '.tmp', '.orig', '.log')
# 前缀排除（相对 skill 根）。用于「同目录下按编号/前缀区分、但整体不可分发」的成组文件。
EXCLUDE_PATH_PREFIXES = {
    # 社区素材样本：第三方作品的二进制，公开分发前须回溯原作者授权（见 THIRD-PARTY-NOTICES.md）
    'assets/community/samples',
    # 社区素材占位降级时运行时生成的占位图/音，不进包
    'assets/community/generated',
    # GitHub 参考作品里来自**无许可证**仓库（SilkRoad/Scratch，license=NONE）的 8 个 .sb3：
    # 无授权即不可再分发，故不进包；同目录其余 8 个来自 Unlicense 仓库，可分发。
    'references/gh_reference_works/00',
}
# 一次性补丁脚本（_patch_xxx.py / _splice_xxx.py / _fix_xxx.py …）改完应当删除，
# 漏删也绝不能进交付包：2026-11-06 体检发现 _add_deal.py / _fix_rules.py 混进 v0.15.0 包。
EXCLUDE_TEMP_DIRS = {'scripts'}
EXCLUDE_TEMP_PREFIXES = ('_',)
# 已淘汰的旧 AI 原图（画质差、带水印，2026-11-04 已被新素材取代）
EXCLUDE_PREFIXES = ('Cartoon_', '_staged')  # _staged* 是 verify 自测产物(SELFTEST_SLUG=_staged_selftest)，不进包


def parse_version(root):
    t = open(os.path.join(root, 'SKILL.md'), encoding='utf-8').read()
    m = re.search(r'^version:\s*(.+)$', t, re.M)
    return m.group(1).strip() if m else '0.0.0'


def split_frontmatter(text):
    """把 SKILL.md 拆成 (frontmatter dict, body)。"""
    m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n(.*)$', text, re.S)
    if not m:
        return {'frontmatter': {}, 'body': text}
    import yaml
    fm = yaml.safe_load(m.group(1)) or {}
    return {'frontmatter': fm, 'body': m.group(2)}


def collect(root, include_outputs):
    """返回 (归档内路径, 磁盘路径) 列表。"""
    items = []
    for dp, dns, fns in os.walk(root):
        rel_dir = os.path.relpath(dp, root)
        parts = rel_dir.split(os.sep) if rel_dir != '.' else []
        if any(p in EXCLUDE_DIRS for p in parts):
            continue
        # 运行时生成的社区占位素材（assets/community/generated/）不进包
        if len(parts) >= 3 and parts[:3] == ['assets', 'community', 'generated']:
            continue
        if not include_outputs and parts and parts[0] == 'examples':
            # 只排除 examples/output 下的产物，保留 yaml 与 assets
            if 'output' in parts:
                continue
        for f in fns:
            if f.endswith(EXCLUDE_SUFFIX) or f.startswith(EXCLUDE_PREFIXES):
                continue
            if (parts and parts[0] in EXCLUDE_TEMP_DIRS
                    and f.startswith(EXCLUDE_TEMP_PREFIXES)):
                continue
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, root).replace(os.sep, '/')
            if rel in EXCLUDE_PATHS:
                continue
            if any(rel.startswith(p) for p in EXCLUDE_PATH_PREFIXES):
                continue
            items.append((rel, full))
    return items


def write_portable_skill_md(data, name):
    """把 frontmatter 收敛为各 agent 通行的 name + description 两字段。

    打包分发时去掉 WorkBuddy 专属的 type / version，
    避免其它 agent 把 type 当枚举误解析。
    """
    fm = data['frontmatter']
    name = fm.get('name') or name
    desc = (fm.get('description') or '').strip()
    if isinstance(desc, str):
        desc = ' '.join(desc.split())
    new_fm = '---\nname: %s\ndescription: %s\n---\n' % (name, desc)
    return new_fm + data['body']


def main():
    args = sys.argv[1:]
    include_outputs = '--exclude-outputs' not in args
    portable = '--portable' in args
    out = 'ai-scratch-maker-v%s.zip' % parse_version(SKILL_ROOT)
    if '--out' in args:
        i = args.index('--out')
        if i + 1 < len(args):
            out = args[i + 1]

    items = collect(SKILL_ROOT, include_outputs)
    extras = []
    for fn in EXTRA_FILES:
        p = os.path.join(REPO_ROOT, fn)
        if os.path.exists(p):
            extras.append((fn, p))
        else:
            sys.stderr.write('  [warn] 仓库根缺少 %s，分发包将不带该文件\n' % fn)

    out_path = os.path.abspath(out)
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, full in sorted(items):
            if portable and rel == 'SKILL.md':
                data = split_frontmatter(open(full, encoding='utf-8').read())
                z.writestr(rel, write_portable_skill_md(data, 'ai-scratch-maker'))
                continue
            try:
                z.write(full, rel)
            except FileNotFoundError:
                # 并发 verify 可能正在 create/delete 临时文件（如 _staged_selftest.*），
                # collect 时存在、write 时消失 → 跳过并告警，不中断打包。
                sys.stderr.write('  [warn] 跳过已消失的文件: %s\n' % rel)
        for rel, full in extras:
            z.write(full, rel)

    size = os.path.getsize(out_path)
    print('打包完成: %s' % out_path)
    print('  文件数: %d' % (len(items) + len(extras)))
    print('  体积: %.1f MB' % (size / 1024 / 1024))
    print('  examples/output 产物: %s' % ('包含' if include_outputs else '不含'))
    print('  frontmatter: %s' % ('通用两字段(portable)' if portable else '原样(含 type/version)'))
    print('  许可与声明: %s' % (', '.join(r for r, _ in extras) or '缺失！'))


if __name__ == '__main__':
    main()
