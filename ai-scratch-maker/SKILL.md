---
name: ai-scratch-maker
version: 0.23.0
description: >
  让 AI 生成高质量 Scratch 3.0 作品（.sb3）。AI 不直接写 sb3，而是编写「中间表示（IR）」，
  由本 skill 的序列化器编译成合法 project.json + 素材并打包。核心工作流是
  **从已验收的完整作品骨架起手**（scripts/new_project.py），而不是从零拼 IR，
  因此产出自带首页、状态机、结算、复位、手感层与生图素材硬闸。支持全部 188 个
  Scratch 积木（含画笔/音乐/朗读/翻译扩展）与云变量。
  触发场景：用户想「做一个 Scratch 小游戏/动画/互动作品」「生成 .sb3」「用 Scratch 做一个…」；
  当用户要求可视化、动画、儿童编程类产物时也适用。
type: skill
---

# ai-scratch-maker

把 AI 的创作意图编译成能被 Scratch 打开、且**能看能玩**的 .sb3。

> 全部命令都在 **skill 根目录**执行；Windows 用 `python`（不是 `python3`）。

---

## 🔴 第 0 步：起手必须跑脚手架（不要从零写 IR）

**这是本 skill 最重要的一条。** 过去 AI 从一张白纸开始写 IR，天然倾向最省事的路线：
程序化纯色 SVG + 最小可跑逻辑，于是产出永远是「能打开但画面糙、玩法空、手感生硬」。
脚手架把高质量前置到生成之前——直接复制一份**八层校验 / 深网行为断言 / 质量门禁全过**
的完整作品作为起点，AI 只改玩法差异和素材。

```bash
python scripts/new_project.py --list                                # 看可用骨架
python scripts/new_project.py --genre catch      --name 星空拾贝      # 接物/收集
python scripts/new_project.py --genre platformer --name 云间跳跃      # 平台跳跃（含手感层）
python scripts/new_project.py --genre whack      --name 欢乐敲击      # 点击/限时
```

产出三份文件（都在 `examples/`，与模板同目录以保证素材相对路径有效）：

| 文件 | 作用 |
|---|---|
| `examples/<slug>.yaml` | **完整可编译 IR**，已含首页 / 状态机 / 结算页与返回按钮 / 复位广播 / 胜负判定 / 计分生命 / 音频四层；platformer 还含跳跃缓冲、可变跳、挤压拉伸、震屏、相机跟随 |
| `examples/<slug>.quality.json` | 规格表，带 `require_bitmap: true` —— **门禁 D 层会拦纯程序化 SVG** |
| `examples/<slug>.assets.md` | 素材替换清单 + 生图提示词（§198 配色、画风统一、禁文字等约束） |

**不要跳过素材替换**：模板里的素材是上一部作品的，照搬等于换了个名字。
按 `assets.md` 用 ImageGen 生成背景 / 主角 / 道具 / 首页 / 按钮，经 `prep_asset.py` 整理后写回 `asset:`。

---

## 四条硬性要求（游戏/互动作品，非可选）

完整配置与代码示例：`references/hard-requirements.md`。

1. **必须有首页 / 标题页**：`title_screen` 声明式配置，别让玩家一进来就在游戏里。
2. **对话用自制聊天框角色**，不要用 `say` / `think` 气泡（中文排版差、挡画面）。
3. **变量和列表用角色展示**（`digit_display` / `stage.monitors`），不要只留监视器。
4. **角色尺寸 ≤ 屏高 1/3**，按朝向准备原图 / 镜像图两套造型。

## 🔒 生图默认最高质量

调用 ImageGen 时**默认 `quality: high` + 大尺寸**，除非用户明确要求更快 / 更低画质。
不要因为「省时间」自行降级。参数模板见 `references/asset-guide.md` §一.1。

### 🎮 手感层 juice（声明式，编译期自动展开，跳不过去）

这是治「手感糙」的根本手段：**不用靠 AI 自觉加手感**。在 IR 顶层写 `juice:` 列表，
构建器 `expand_juice` 自动展开成真实积木（挤压拉伸 / 白闪 / 震屏）。三个模板骨架
（catch / platformer / whack）已内置，脚手架复制出来的作品**自带手感**，AI 删不掉。

```yaml
juice:
  - sprite: 挡板        # 受影响的角色（必须已存在）
    trigger: 加分       # 触发广播（键名用 trigger，别用 on——YAML 1.1 把 on 当布尔 True）
    squash: 18          # 挤压拉伸幅度(%)，快速放大回弹
    shake: 4            # 震屏幅度(px)，短暂随机抖动
  - sprite: 结算页
    trigger: 通关
    squash: 20
    flash: 40           # 白闪幅度(BRIGHTNESS)，短暂提亮再还原
```

字段：`sprite`(目标角色名) · `trigger`(广播名) · `squash`(挤压%) · `flash`(白闪) · `shake`(震屏)。
更多手感模式（相机 Lerp / 粒子爆发 / 顿帧）见 `references/ir-patterns.md`「手感」章。

### 🎞 帧动画 animations（声明式，编译期自动展开，跳不过去）

治「角色是死的（单造型）」的根本手段：**不用靠 AI 自觉切造型**。在 sprite 下声明
`animations:`（驱动变量 + `fps` + `states: 状态名→造型序列`），构建器 `expand_animations`
自动注入变量/列表并生成**状态机 + 翻帧器**两段脚本，`looks_switchcostumeto` 按名切造型。
`examples/platformer.yaml` 的玩家已用四帧（idle/walk1/walk2/jump）跑通；手头是网格精灵表时
用 `scripts/slice_sheet.py` 切出单帧再接 IR。完整写法与约束见 `references/ir-patterns.md` P9。

---

## 工作流（6 步，命令链）

以 `examples/<slug>` 为例，把 `<slug>` 换成脚手架输出的名字。

**1 · 起手 + 定规格**
```bash
python scripts/new_project.py --genre catch --name 星空拾贝
```
规格表已由脚手架生成（`demo / mini / game / showcase` 档位见 `references/quality-profiles.json`）。
写之前逐条过 `references/quality-checklist.md`：配色 18 色板 / 窗口圆角 / 质感曲线 /
UI 矢量五层体积感 / 音效四层响度——**技术完整但观感拉胯，通常是漏了这几条**。

**2 · 换素材（治「画面丑」的关键一步）**
- **矢量优先**：按钮 / 面板 / 题卡 / 结算页 / 飘字等 UI 一律用 §198 合规矢量 SVG
  （铁律17 五层体积感）。AI 生图位图只用于**全屏背景**与**主角 / 道具**，且必须抠掉
  白底、带透明通道——白底未抠或整块不透明的位图缩进 480x360 舞台会带方块，
  门禁 D 层判「不合适」，不计入达标数（矢量 SVG 与透明位图都算合适；
  舞台背景、以及尺寸为 480×360 整数倍的全屏铺底图免抠，本来就该不透明）。
- 按 `examples/<slug>.assets.md` 生图 → `scripts/prep_asset.py` 整理尺寸/抠图 → 写回 `asset:`。
- 已有的不透明 UI 位图（纯渐变矩形 + 烤进去的文字，矢量化会丢字）：
  `python scripts/round_ui_alpha.py --backup-dir <备份目录> <文件...>` 加圆角 alpha
  遮罩，保留文字的同时变「合适资产」；`--check` 只体检不写。
- 音效：`scripts/gen_audio.py <mood>` 或 `scripts/gen_sfx_kit.py`（22 预设），
  四层响度 ui-18 / fx-9 / ev-3 / amb-15 dBFS（铁律18）。
- ATO / 自动驾驶类工程用 `scripts/gen_ato.py` 生成（`--line` 换线路：站名/站距/限速表参数化，
  `--list-lines` 看内置线路）；**模板初值一律 `item_of_list` 从列表取，不要写死**。
- 有现成真实素材优先 `python scripts/asset_pack.py search <关键词>`（§C6），
  IR 写 `asset: community:<id>`。
- 首页/聊天框/数字牌面可用 `scripts/make_ui_assets.py`。

**3 · 编译**（`--workdir` 必填，否则会在仓库里留 `_proj` 目录）
```bash
python scripts/build_sb3.py --ir examples/<slug>.yaml \
       --out examples/output/<slug>.sb3 --workdir <临时目录>
```
编译前自动校验 IR（积木名、帽子开头、变量/广播声明、造型齐备、云变量上限），
报错带**源文件行号**和「你是不是想写：X / Y」提示。`title_screen` / `digit_display` /
`chat_box` 会展开成真实积木。

**4 · 结构校验**
```bash
python scripts/validate_sb3.py --sb3 examples/output/<slug>.sb3
```
四项：ZIP/project.json/资产 MD5、opcode 合法性 → 官方 JSON Schema → scratch-parser
`validate()`（编辑器同一条路径）→ scratch-vm 真加载绿旗步进 60 帧。
**全过只说明「能打开、不崩」，不代表像作品。**

**5 · 质量门禁（交付前必过）**
```bash
python scripts/quality_gate.py --sb3 examples/output/<slug>.sb3 \
       --spec examples/<slug>.quality.json --strict
```
四层：**A** 资产密度六项（其中 `min_bytes` 统一 150000，只作防构建空壳下限，**非质量指标**）/
**B** 玩法完整度三项（仅 `genre=game`）/
**C** 观感质量（渐变/圆角/缓动/配色评分 + §198 明确违规）/
**D** 素材硬闸（规格表 `require_bitmap=true` 时启用）：只认被 `project.json` 真正引用的
**合适资产**——矢量 SVG、带透明通道位图，以及舞台背景 / 尺寸为 480×360 整数倍的
全屏铺底图；白底未抠的不计，zip 里的孤儿素材一律不算。`--strict` 下未达标**阻止交付**，
逐项给实测值与补齐命令。
音乐/动画/剧情类把规格表 `genre` 改为 `music/animation/story` 可跳过 B 层。

**6 · 交付前自查 + 全链路回归**
- 逐条过 `references/self-review.md`（9 类软性核查：开场引导 / 边界稳定 / 难度曲线 /
  玩法完整度 / 观感手感 / 可访问性 / 音效 / 架构 / 合规发布）。
- 硬件规则由脚本兜，但「好不好玩、有没有软锁」只能靠这份清单。
```bash
bash scripts/verify_project.sh --jobs 4          # 全链路，交付前跑一次
bash scripts/verify_project.sh --only-advisory   # 只跑阶段6 建议层（秒级调试）
```
七阶段：全量构建 → 八层校验 → 铁律检查器 → L7 语义回归 → 启动冒烟 + 行为深网
→ 质量门禁 → 增量嗅觉（性能预算 / 可访问性 / 抽样 VM 试玩，默认 advisory 不阻断）。
其他开关：`--with-playtest`、`--strict-advisory`、`--skip-build`、`--skip-regress`、`--no-cache`。

---

## IR 关键坑（写之前先看这 10 条）

完整语法见 `references/full-manual.md` 或 `references/ir-format.md`；
**可抄模板**见 `references/ir-patterns.md`（状态机 / 物理积分 / UI 按钮 / 音频四层 /
相机 Lerp / 克隆生命周期 / 碰撞收窄 / 帧动画 animations）。

1. **每个脚本必须以帽子积木开头**（绿旗 / 接收广播 / 按键 / 点击 / 作为克隆体启动）；
   顶层裸积木不会被绿旗启动，静默失效。
2. 积木必须是 `{名: 值}` 字典；`else:` 与 `if:` **同级、同一个列表项**里的同一块
   （`cond` / `do` / `else` 同块），不能另起一个 `- else:`。
3. `and` / `or` **只有 2 个输入**，多条件必须嵌套；`not` 用 `operand:`，别包 `equals`。
4. 输入别名：`dx`/`dy`、`颜色#rrggbb`（**6 位 HEX**，铁律8）、`create_clone_of`→`clone:`、
   `touching`→`object:`、`stop`→`option:`（英文）、`change_effect` 的 effect 大写、
   「碰到鼠标」→`object:_mouse_`。
5. `lists:` 实为变量存数组，校验读 `target.variables`（1-based-1）；列表块式声明每行 `- 0`。
6. 菜单/首页用**角色按钮**，不要用「询问…并等待」（铁律10）。
7. 复位挂 `[重置]` 广播，**不要挂绿旗**（铁律6）；结算页必须有返回 / 再来一局按钮（铁律7）。
8. 克隆体用私有变量 `是克隆` 挡住本体事件帽（否则指数爆炸，铁律11）；
   克隆硬上限 300，静默丢弃，离屏即删（铁律12）。
9. `forever` 内加 `wait 0.02` 节流；摩擦/阻尼用**乘**不用减（铁律5）；
   碰撞判定用 `abs(dx)<R and abs(dy)<R`，别用 `touching`（无头测不到）。
10. 障碍角色必须被碰撞检测引用（背景上画的挡不住人，铁律4）；
    SVG 禁 `text/filter/mask/clipPath/pattern/image/foreignObject`（铁律17）。

无头测不到的：size / 克隆 / 画笔 / 音频 / 悬停 / 中文排版 / 手感——**仍需人工目视**。

---

## 失败时查哪里（按需，不要一次全读）

| 症状 | 打开 |
|---|---|
| 编译报「未知积木名 / 第N行」 | 报错自带行号 + 建议名；`references/ir-format.md` |
| 画面糙 / 配色被拦 | `references/quality-checklist.md`、`references/hard-requirements.md` |
| 不知道某题材怎么写 | `references/genre-quickref.md`（11 类速查）、`references/ir-patterns.md` |
| 反复踩同一个坑 | `references/failure-modes.md`（易错→正确写法 + 已知误报 + 既有欠债清单） |
| 41 册手册某册在讲什么 | `references/handbook-index.md`（§1–§529 + §C1–§C7） |
| 铁律全文（29 条） | `references/hard-requirements.md` |
| 端到端可复现命令链 | `references/golden-path.md` |
| 创作方法论 / 网络秘诀 / 三范例对照 | `references/creation-playbook.md` |
| 旧版 SKILL.md 全部细节 | `references/full-manual.md`（960 行归档，信息零删减） |
| 检查器脚本用法 | 各脚本 `--help`，或 `references/full-manual.md`「校验通过标准」 |

> **原则**：文档由**命令调用**或**失败时回溯**，不靠「建议阅读」。
> 生成质量靠第 0 步的骨架 + 第 2 步的生图 + 第 5 步的硬闸保证，不靠读更多文档。

---

## 运行环境与打包

- 依赖：`node_modules`（scratch-vm / scratch-parser / jszip），由 `scripts/scratch_vm_path.mjs`
  解析；也可用 `reference/scratch-sources`。
- 交付包：`python deploy-tools/pack_skill.py --portable`（顶层只含 SKILL / README /
  scripts / references / examples / node_modules；社区素材库 351MB 不进包，只带 manifest + 样本）。
- 第三方社区素材**仅供学习参考**，对外分发 / 商用须回溯原作者授权。
- 署名用 CC BY-SA，**禁止写「禁止改编 / 请勿复制 / 私人作品 / 禁止转载」**（铁律3）。
