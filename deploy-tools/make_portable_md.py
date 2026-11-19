"""把 SKILL.md 里的「安装位置」段落改成环境无关表述。

WorkBuddy 版写死了本机绝对路径；复制到 Claude / Codex / Cursor / opencode / avlcode
后这些路径是错的，会误导 agent 去读不存在的目录。改为「skill 根目录 = SKILL.md 所在目录」。
"""
import re
import sys
import os

WORKBUDDY_BLOCK = '''## 安装位置与运行环境

本 skill 已安装到 **用户级目录**，对所有项目生效：

| 项目 | 路径 |
| --- | --- |
| skill 根目录 | `C:\\Users\\Administrator\\.workbuddy\\skills\\ai-scratch-maker` |
| 原始开发副本 | `E:\\编程作品\\作品\\豆包\\AI制作schatch作品的skill\\ai-scratch-maker` |

**运行时依赖**（本机已就绪）：
'''

GENERIC_BLOCK = '''## 安装位置与运行环境

本 skill 已安装到**本机所有 agent 环境**的 skill 目录，对各 agent 全局生效：

| 环境 | 路径 |
| --- | --- |
| WorkBuddy | `~/.workbuddy/skills/ai-scratch-maker` |
| Claude Code | `~/.claude/skills/ai-scratch-maker` |
| Codex | `~/.codex/skills/ai-scratch-maker` |
| Cursor | `~/.cursor/skills/ai-scratch-maker` |
| opencode | `~/.config/opencode/skill/ai-scratch-maker` |
| avlcode | `~/.config/avlcode/skills/ai-scratch-maker` |

**skill 根目录 = SKILL.md 所在目录**。所有脚本命令都从这个目录下执行，
用相对路径 `scripts/xxx.py` 引用，**不要写死绝对路径**（本 skill 可能被安装到任意位置）。

重新同步到全部环境 / 检查一致性：

```bash
python scripts/install_all_envs.py            # 一键安装/同步（含跨环境适配）
python scripts/install_all_envs.py --check    # 只检查各环境是否一致
python scripts/verify_all_envs.py            # 逐环境核对 frontmatter / 关键文件 / 正文一致性
```

跨环境适配由脚本自动完成：frontmatter 收敛为各环境通行的 `name` + `description`，
「安装位置」段落改写为环境无关表述。

**运行时依赖**：
'''

TAIL_OLD = '''- scratch-vm 运行时 —— 位于 `C:\\Users\\Administrator\\.workbuddy\\sb3_poc_runtime\\node_modules\\scratch-vm`，
  可用环境变量 `SCRATCH_VM_PATH` 覆盖
'''

TAIL_NEW = '''- scratch-vm 运行时 —— 供 parser / 运行时两层校验使用，默认探测本机常见位置；
  若不在默认位置，用环境变量 `SCRATCH_VM_PATH` 指向 `.../node_modules/scratch-vm`
'''


def main():
    if len(sys.argv) < 2:
        print('用法: python make_portable_md.py <skill目录>')
        sys.exit(2)
    path = os.path.join(sys.argv[1], 'SKILL.md')
    if not os.path.exists(path):
        print('SKIP 未找到: ' + path)
        return
    text = open(path, encoding='utf-8').read()

    if '## 安装位置与运行环境' not in text:
        print('SKIP 无安装段落: ' + path)
        return

    before = text
    text = text.replace(WORKBUDDY_BLOCK, GENERIC_BLOCK)
    text = text.replace(TAIL_OLD, TAIL_NEW)

    if text == before:
        print('SKIP 内容已是环境无关版本: ' + path)
        return

    open(path, 'w', encoding='utf-8', newline='\n').write(text)
    print('OK 已改为环境无关表述: ' + path)


if __name__ == '__main__':
    main()
