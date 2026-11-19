"""清理各 agent 环境里已淘汰的旧素材，并把根目录交付件同步为最新版。

背景：2026-11-04 重出全部关键素材后，旧的三张 AI 原图（Cartoon_*.png，
画质差、带水印）仍留在 examples/assets/cat_mouse/ 里，还被打进了 zip。
"""
import os
import shutil
import glob

HOME = os.path.expanduser('~')
DEV = r'E:\编程作品\作品\豆包\AI制作schatch作品的skill'

ENVS = [
    os.path.join(HOME, '.workbuddy', 'skills', 'ai-scratch-maker'),
    os.path.join(HOME, '.claude', 'skills', 'ai-scratch-maker'),
    os.path.join(HOME, '.codex', 'skills', 'ai-scratch-maker'),
    os.path.join(HOME, '.cursor', 'skills', 'ai-scratch-maker'),
    os.path.join(HOME, '.config', 'opencode', 'skill', 'ai-scratch-maker'),
    os.path.join(HOME, '.config', 'avlcode', 'skills', 'ai-scratch-maker'),
    os.path.join(DEV, 'ai-scratch-maker'),
]

# 最新交付件（从 WorkBuddy 权威副本取）
FRESH_SB3 = os.path.join(HOME, '.workbuddy', 'skills', 'ai-scratch-maker',
                         'examples', 'output', 'cat_mouse.sb3')


def main():
    removed = 0
    for root in ENVS:
        if not os.path.isdir(root):
            print('跳过(不存在): ' + root)
            continue
        hits = []
        # 1) 旧 AI 原图
        d = os.path.join(root, 'examples', 'assets', 'cat_mouse')
        for p in glob.glob(os.path.join(d, 'Cartoon_*.png')):
            os.remove(p)
            hits.append(os.path.basename(p)[:24])
            removed += 1
        # 2) __pycache__
        for p in glob.glob(os.path.join(root, '**', '__pycache__'), recursive=True):
            shutil.rmtree(p, ignore_errors=True)
        # 3) 根目录旧交付件 → 同步为最新
        legacy = os.path.join(root, '猫抓老鼠.sb3')
        if os.path.exists(legacy) and os.path.exists(FRESH_SB3):
            shutil.copy2(FRESH_SB3, legacy)
            hits.append('猫抓老鼠.sb3 已更新')
        print('%-62s %s' % (root[-60:], ('清理 %d 项' % len(hits)) if hits else '无需清理'))

    # 项目根的交付件也同步
    proj = os.path.join(DEV, '猫抓老鼠.sb3')
    if os.path.exists(FRESH_SB3):
        shutil.copy2(FRESH_SB3, proj)
        print('项目根 猫抓老鼠.sb3 已更新')
    print('\n共删除 %d 个旧文件' % removed)


if __name__ == '__main__':
    main()
