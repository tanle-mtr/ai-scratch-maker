"""从各 agent 环境里删除部署元脚本（它们不属于 skill 本体）。

部署元脚本包含本机绝对路径与特定环境探测逻辑，随 skill 分发会造成误导：
    install_all_envs.py / verify_all_envs.py / adapt_skill_md.py / make_portable_md.py

这些脚本保存在项目的 deploy-tools/ 目录，不随 skill 分发。
"""
import os
import sys

DEPLOY_SCRIPTS = [
    'install_all_envs.py',
    'verify_all_envs.py',
    'adapt_skill_md.py',
    'make_portable_md.py',
]

ENVS = [
    '~/.workbuddy/skills/ai-scratch-maker',
    '~/.claude/skills/ai-scratch-maker',
    '~/.codex/skills/ai-scratch-maker',
    '~/.cursor/skills/ai-scratch-maker',
    '~/.config/opencode/skill/ai-scratch-maker',
    '~/.config/avlcode/skills/ai-scratch-maker',
]

removed = 0
for rel in ENVS:
    root = os.path.expanduser(rel)
    scripts = os.path.join(root, 'scripts')
    if not os.path.isdir(scripts):
        print('跳过(无 scripts 目录): ' + rel)
        continue
    hits = []
    for name in DEPLOY_SCRIPTS:
        p = os.path.join(scripts, name)
        if os.path.exists(p):
            os.remove(p)
            hits.append(name)
            removed += 1
    print('%-46s 移除 %d 个: %s' % (rel, len(hits), ', '.join(hits) if hits else '无'))

print('\n合计移除 %d 个文件' % removed)
