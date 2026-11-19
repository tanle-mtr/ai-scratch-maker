<!-- 归档说明：本文件是 2026-11-08 之前的 SKILL.md 全文（955 行）。
  现行入口 SKILL.md 已精简为「必读 + 命令链」；本文件保留全部历史细节，
  供按需检索：IR 完整语法、积木名查法、扩展积木表、素材生成参数、云变量、
  八层校验逐层说明、目录结构、手册索引等。信息零删减，仅不再作为默认加载内容。 -->

---
name: ai-scratch-maker
version: 0.19.0
description: >
  让 AI 生成 Scratch 3.0 作品（.sb3 文件）。原理：AI 编写一份「中间表示（IR）」描述
  角色、舞台、积木脚本，由本 skill 的序列化器把易错的 sb3 数组结构编译成合法且可被
  Scratch 打开/运行的 project.json + 素材，并打包成 .sb3。本 skill 还让 agent 拥有
  生成图片（背景/角色）与音频（音效/音乐）的能力，用于作品素材。支持全部 188 个
  Scratch 积木（含画笔/音乐/朗读/翻译扩展），以及云变量。
  触发场景：用户想「做一个 Scratch 小游戏/动画/互动作品」「生成 .sb3」「用 Scratch
  做一个…」。当用户要求可视化、动画、儿童编程类产物时也适用。
type: skill
---

# AI Scratch Maker

把「让 AI 直接手写 .sb3 的 JSON 数组」这件极易出错的事，改成「AI 写一份人类可读的
中间表示（IR，YAML/JSON），由脚本编译成合法 .sb3」。

所有易错的序列化细节（积木数组结构、变量/列表的引用方式、下拉菜单的编码、
子栈接线、自定义积木的 mutation、云变量作用域）都由 `scripts/build_sb3.py`
收敛到被测试覆盖的代码里。

**积木规范不是手写的**：`references/blocks-spec.json` 由
`scripts/extract_blocks_spec.js` 从 **Scratch 官方源码**（scratch-blocks /
scratch-vm）直接抽取，并交叉校验「运行时支持的原语 100% 收录」。

---

## 何时使用

- 用户要「做一个 Scratch 作品 / 小游戏 / 动画 / 互动课件」，并产出 `.sb3`。
- 用户要在 Scratch 里实现某个逻辑（移动、克隆、画笔、自定义积木、列表、侦测等）。
- 需要为作品生成背景、角色（图片）或音效、音乐（音频）。
- 需要云变量（多人共享计分等）。

---

## 工作流程（标准 6 步）

> 完整可复现范例与命令清单（以 `examples/fruit_basket.yaml` 接水果游戏为样例）见
> `references/golden-path.md`：从定规格、写 IR、生成素材、编译到八层校验 + 质量门禁一条跑通。

1. **设计 + 定规格**：和用户确认要做什么 —— 玩法、舞台、角色、需要哪几类积木
   （运动/外观/控制/侦测/运算/数据/画笔/自定义积木/克隆…）。
   需要多人共享数据时，确认是否用云变量。
   **游戏类作品必须有首页**（见 `references/hard-requirements.md`）。
   **动手写 IR 之前，先生成一份作品规格表**，把「高质量」变成可验收的数字：
   ```bash
   python scripts/quality_gate.py --init --profile game --out <作品>.quality.json
   ```
   档位 `demo / mini / game / showcase` 见 `references/quality-spec.md`；可按题材手改 `min_*`。
   这一步是**默认链路的关键**：以前素材是可选项，导致 82% 的示例零音效、造型中位 2–4 个。
   > **📋 编写前必读 `references/quality-checklist.md`**：把决定「观感质量」的铁律 8/9/11/12
   > （配色 18 色板 / 窗口圆角 / 质感曲线 / UI 矢量五层体积感 / 音效四层响度）浓缩成
   > 写每个作品时**逐条自检**的可执行清单（含错误写法 vs 正确写法、自检命令）。这是让 AI
   > 默认写出高质量作品的关键——技术完整但观感拉胯，往往是漏了这几条。
2. **写 IR**：产出一份 IR 文件（推荐 YAML，见 `references/ir-format.md`）。
   AI 用积木的「友好名」或原始 opcode 描述每个脚本。
   - **先抄模板再自己写**：`references/ir-patterns.md` 有 7 个已验证的可抄片段
     （状态机主循环 / 物理积分 / UI 按钮 / 音频四层 / 相机 Lerp / 克隆生命周期 / 碰撞收窄），
     每个都标注了服务的铁律与手册 §，直接改参数比自己从零拼快且不出错。
   - **按题材查卡**：`references/genre-quickref.md` 给出平台跳跃/音游/射击/解谜/叙事/桌游等
     11 类题材的「必看章节 + 必须有 + 必避坑」。
   - **每个脚本都要以帽子积木开头**（绿旗 / 接收广播 / 按键 / 点击 / 作为克隆体启动）——
     顶层裸积木不会被绿旗启动，属于静默失效。
   - **给关键积木加注释**（`comment:` 键），说明这段逻辑在干什么。
   - **用 `stage.comments` 写一段悬空的操作指引**（给玩的人看）。
   - 顶层脚本的位置由序列化器**自动整理**（网格排布），不用操心。
3. **生成素材（必选，按第 1 步规格表凑够资产密度）**：
   - **先查社区素材包**（§C6）：`python scripts/asset_pack.py search <关键词>`，
     有现成真实素材就写 `asset: community:<id>`，别从零画。
     5 个已验证模板：`python scripts/gen_community_template.py --list`。
   - 背景/角色图片：调用 **ImageGen** 生成 PNG（**🔒 默认最高质量 `quality: high` + 大 `size`，
     除非用户明确要求降级**；参数模板见 `references/asset-guide.md` §一.1），
     再用 `scripts/prep_asset.py` 整理成标准尺寸（舞台 480×360，角色保持比例），
     把产物路径写进 IR 的 `asset`。
   - 音效/音乐：调用 `scripts/gen_audio.py` 离线合成 WAV
    （17 种音效预设 + 7 种程序化 BGM，**无需外部服务**）。
   - 首页/聊天框/数字牌面：调用 `scripts/make_ui_assets.py` 生成
    （见「UI 素材」一节）。
4. **编译**：`python3 scripts/build_sb3.py --ir <你的IR> --out <产物>.sb3`
   编译前会做 IR 校验（积木名是否存在、脚本是否以帽子积木开头、
   变量/广播是否指明、造型是否齐备、云变量是否超限）。
   编译时自动完成**整理积木**（顶层脚本排成网格）与**写入注释**，
   并把声明式的 `title_screen` / `digit_display` / `chat_box` 展开成真实积木。
   > 所有脚本命令都在 **skill 根目录**（本 SKILL.md 所在目录）下执行；
   > Windows 上用 `python` 而非 `python3`。
5. **结构校验**：`python3 scripts/validate_sb3.py --sb3 <产物>.sb3`
   - **结构与编码检查**：ZIP/project.json/资产 MD5、opcode 合法性、输入数组形态、
     变量是否被二次编码、字段是否放对位置、**注释关联是否双向**、
     **影子积木是否 topLevel**、**角色尺寸是否过大**、云变量数量。
   - **官方 JSON Schema**：用 `scratch-parser` 的 `sb3_schema.json` 校验。
   - **官方 scratch-parser**：走编辑器打开项目时**同一条** `validate()` 路径，
     确认「编辑器能不能打开这个 sb3」。
   - **运行时**：用 scratch-vm 真正加载、绿旗启动、步进 60 帧（无异常即通过）。
   四项全过只说明「能打开、不崩」，**不代表像作品**。
6. **质量门禁（交付前必过）**：
   ```bash
   python scripts/quality_gate.py --sb3 <产物>.sb3 --spec <规格表>.json --strict
   ```
   规格表（见 `references/quality-spec.md` §C7）分三层：
   - **A. 资产密度六项**（所有品类）：造型数 / 音效数 / 角色数 / 产物体积 / 场景数 / 积木数；
   - **B. 玩法完整度三项**（仅 `genre=game` 强制）：玩家可操控 / 胜负条件 / 重玩价值
     —— 保证不是零交互幻灯片、不能操控的展示。
   - **C. 观感质量**（启发式评分 + 明确违规 WARN，所有品类都分析，默认不硬拦）：
     渐变体积感（SVG 含 linearGradient/radialGradient）/ 窗口圆角（rect 带 rx）/
     缓动过渡（glide / GHOST 渐显 / 阻尼 multiply / 缓动关键词）/ 配色合规
     （冷灰、深绿填充，§198）。`game`/`showcase` 品类在 `--strict` 下，出现冷灰或深绿填充
     这类**明确 §198 违规**会阻止交付；纯启发式观感分仅作建议、不硬拦（避免误杀标杆）。
     写的时候对照 `references/quality-checklist.md` 模块三/四提前规避。
   逐项给实测值、门槛与补齐命令；`--strict` 下未达标**阻止交付**。
   不达标先按报告补素材（`references/community-asset-pack.md` §C6 与 5 个模板），再重跑。
   音乐 / 动画 / 剧情类在规格表设 `genre=music/animation/story` 自动跳过 B 层；
   纯技术验证可用 `--profile demo` 显式豁免，并在交付说明里注明档位。
   无头测不到的（size / 克隆 / 画笔 / 音频 / 悬停 / 中文排版 / 手感）仍需人工目视。
   > **✅ 交付前逐条过一遍 `references/self-review.md`**：硬件规则由脚本兜，
   > 但「开场有没有引导 / 边界会不会卡住 / 难度曲线有没有断层 / 有没有软锁 /
   > 可访问性够不够 / 架构清不清楚」这些软性维度只能靠自查清单。九类逐项打勾再交付。
   > 已踩过的坑（IR 语法 / 铁律 / LitterBox 臭味 / 已知误报）见 `references/failure-modes.md`。

7. **一键验收（交付前全链路回归）**：把「全量构建 → 八层结构校验 → 铁律检查器 → 语义回归 →
   全量启动冒烟 + 逐作品行为回归 → 质量门禁 → 增量嗅觉」串成一条命令，给出统一 PASS/FAIL 与退出码：
   ```bash
   bash scripts/verify_project.sh                 # 全链路（约 12+ 分钟，含行为回归）
   bash scripts/verify_project.sh --skip-regress   # 只跑前 5 阶段（不含 12 分钟行为回归）
   bash scripts/verify_project.sh --jobs 4         # 行为回归并行提速（失败自动串行重试甄别假红）
   bash scripts/verify_project.sh --with-playtest  # 额外跑阶段6 抽样 VM 试玩
   bash scripts/verify_project.sh --strict-advisory # 阶段6 建议项升级为 FAIL（CI 用）
   bash scripts/verify_project.sh --only-advisory  # 只跑阶段6（秒级，调建议层阈值时用）
   ```
   - **阶段 6 增量嗅觉**（默认 advisory，不影响退出码）：三个「有没有更好的写法」的检查器
     ——`scripts/check_perf_budget.py`（Long Script / Busy Waiting / 克隆逼近 300 / 广播风暴）、
     `scripts/check_a11y.py`（色盲红绿对 / SVG `<text>` / 可见状态通道 / 闪烁）、
     `scripts/playtest_bot.mjs`（真跑 VM 断言不崩 + 脚本在运行）。
     两者都支持传**目录批量扫**（56 个作品约 1.2 秒）。它们报的是「建议」不是「对错」，
     命中不阻断交付，但建议在交付说明里注明。
   - **铁律检查器** `scripts/check_hard_rules.mjs`：不启动 VM，静态扫描 **9 条**机器可检铁律
     （6 位 HEX 颜色 / 障碍碰撞箱 / say 显示数字 / 署名禁语 / 复位广播 / 结算页按钮 / 克隆生命周期 / SVG 禁标签 / 长文本气泡），
     WARN 不致命，`--strict` 升 FAIL 接 CI。
   - **全量启动冒烟** `scripts/boot_smoke_check.mjs`：把 `examples/output` 全部 54 个作品加载进 scratch-vm、
     绿旗 + 开始游戏启动，断言不崩溃（**宽网**），补齐「深网」行为回归只覆盖 23 个作品的缺口。
   - **单进程批量构建** `scripts/build_all.py`：一个 Python 进程内循环构建 `examples/*.{yaml,json}`
     （同时扫 JSON 源），复用产物缓存，比逐条 `build_sb3.py` 快很多。
   - **逐作品行为回归** `scripts/regress_behavior.sh`：深网校验 23 个游戏/交互作品（含交付件 `cat_mouse`）
     的真实玩法逻辑（状态机 / 复位 / 胜负 / 关键角色），`--jobs N` 并行且失败自动重试。

   可选：单作品快速冒烟，确认脚本真的跑起来了：
   ```bash
   node scripts/smoke_test.mjs <产物>.sb3 --seconds 3
   ```

---

## 安装位置与运行环境

**skill 根目录 = 本 SKILL.md 所在目录**。所有脚本命令都从这个目录下执行，
用相对路径 `scripts/xxx.py` 引用，**不要写死绝对路径**（本 skill 可被安装到任意位置）。

把 skill 目录放到对应 agent 的 skill 目录即可生效：

| 环境 | skill 目录 |
| --- | --- |
| WorkBuddy | `~/.workbuddy/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| Cursor | `~/.cursor/skills/` |
| opencode | `~/.config/opencode/skill/` |
| avlcode | `~/.config/avlcode/skills/` |

**运行时依赖**：

- `python` 3.13+ —— 必需；需 `PyYAML`、`Pillow`（IR 解析与图片处理）
- `node` 18+ —— 跑 `*.mjs` 校验脚本
- **无需额外安装 npm 包**：`ajv`（官方 Schema 校验所需）已内置在 `node_modules/`，
  随 skill 一起分发，Schema 校验层开箱即用
- scratch-vm 运行时 —— 供 **parser 与运行时**两层校验使用（可选）。
  定位顺序：`SCRATCH_VM_PATH` → skill 内置 `node_modules` → 当前目录 `node_modules`
  → 本机常见位置（`~/.workbuddy/sb3_poc_runtime` 等）。
  **找不到时这两层自动跳过**（输出 `SKIP_PARSER` / `SKIP_RUNTIME`），其余层照常执行，
  不会出现 Node 报错堆栈打断流程
- 官方 sb3 Schema —— 已内置在 `references/sb3-schema/`，校验器会按
  `SB3_SCHEMA_DIR` → skill 内置目录 → 脚本相对路径 的顺序自动探测，
  **因此 skill 可以被复制到任意位置而不失效**

> 如果本机缺少 scratch-vm 运行时，运行时/解析器两层校验会自动跳过（其余层仍会执行）；
> 此时可用 `node scripts/validate_schema.mjs <project.json>` 单独做官方 Schema 校验。

---

## 游戏类作品的硬性要求（必读 4 条）

用户要「游戏/互动作品」时，下面四条**不是可选项**。完整配置与代码示例见
`references/hard-requirements.md`；涉及首页、对话、数值展示或角色尺寸时，**生成前打开它**。

1. **必须有首页 / 标题页**：用 `title_screen` 声明式配置，别让玩家一进来就在游戏里。
2. **对话用自制聊天框角色**，不要用 `say` / `think` 气泡（中文排版差、挡画面）。
3. **变量和列表用角色展示**（`digit_display` / `stage.monitors`），不要只留监视器。
4. **角色尺寸算清楚**（≤ 屏高 1/3），并按朝向准备原图 / 镜像图两套造型。

### 手册按需加载索引

四十一册手册的**详细摘要**已移到 `references/handbook-index.md`，**不要一次全读**。
按题材查下表，只打开需要的那几册；节号跨册连续，§1–§529 为主编，§C1–§C6 为社区补编。

| 题材 / 册 | 手册 | 节号 |
|---|---|---|
| 第一册 — | `references/advanced-techniques.md` | §1–§15 |
| 第二册 — | `references/game-systems.md` | §16–§42 |
| 第三册 — | `references/game-design.md` | §43–§50 |
| 第四册 手搓物理引擎 | `references/physics-engine.md` | §51–§58 |
| 第五册 — | `references/more-techniques.md` | §59–§66 |
| 第六册 画笔扩展与伪 3D | `references/pen-techniques.md` | §67–§74 |
| 第七册 游戏手感与交互 | `references/game-feel-and-interaction.md` | §75–§82 |
| 第八册 Scratch 自带扩展积木 | `references/extension-techniques.md` | §83–§92 |
| 第九册 社区作品提炼的实战技巧 | `references/community-techniques.md` | §93–§105 |
| 第十册 答题 / 测验系统 | `references/quiz-systems.md` | §106–§110 |
| 第十一册 消除 / 三消游戏 | `references/elimination-games.md` | §111–§115 |
| 第十二册 射击 / 弹幕游戏 | `references/shooter-games.md` | §116–§120 |
| 第十三册 教育课件通用范式（含数据可视化） | `references/edu-courseware.md` | §121–§126 |
| 第十四册 联机功能 | `references/multiplayer.md` | §127–§131 |
| 第十五册 3D 游戏 | `references/3d-games.md` | §132–§136 |
| 第十六册 第一人称 | `references/first-person.md` | §137–§141 |
| 第十七册 棋类游戏 | `references/board-games.md` | §142–§146 |
| 第十八册 结算页与返回按钮 | `references/results-screen.md` | §147 |
| 第十九册 剧情故事 / 互动叙事（视觉小说） | `references/story-narrative.md` | §148–§155 |
| 第二十册 平台跳跃 / 横版关卡 | `references/platformer.md` | §156–§166 |
| 第二十一册 地铁 / 交通模拟 | `references/metro-sim.md` | §167–§176 |
| 第二十二册 大型工程架构 | `references/game-architecture.md` | §177–§186 |
| 第二十三册 特殊玩法硬技术 | `references/voxel-and-light.md` | §187–§196 |
| 第二十四册 UI 设计规范 | `references/ui-design-spec.md` | §197–§206 |
| 第二十五册 地铁驾驶模拟：从里程到 ATP | `references/metro-driving-deep.md` | §207–§221 |
| 第二十六册 质感与手感打磨 | `references/polish-and-feel.md` | §222–§235 |
| 第二十七册 ATO 自动驾驶：让机器把车停准 | `references/ato-autopilot.md` | §236–§248 |
| 第二十八册 UI 素材制作：从「能看」到「能卖」 | `references/ui-asset-craft.md` | §249–§262 |
| 第二十九册 声音设计：让作品「有质感」的另一半 | `references/audio-design.md` | §263–§276 |
| 第三十册 数学与推理：让作品「算得对」 | `references/math-and-reasoning.md` | §277–§290 |
| 第三十一册 桌游：卡牌、手牌与隐藏信息 | `references/tabletop-games.md` | §291–§304 |
| 第三十二册 乐器与编曲：把乐谱变成演奏 | `references/music-and-instruments.md` | §305–§319 |
| 第三十八册 — | `references/rhythm-games.md` | §433–§456 |
| 第三十三册 狼人杀完全手册：身份、板子、警徽流与自爆 | `references/werewolf-complete.md` | §320–§348 |
| 第三十四册 桌游规则库与通用引擎 | `references/boardgame-library.md` | §349–§372 |
| 第三十五册 红狼（狼人杀经典版）完全手册 | `references/werewolf-classic.md` | §373–§393 |
| 第三十六册 网易觉醒体系完全手册 | `references/werewolf-awakening.md` | §394–§412 |
| 第三十七册 新月事件卡与运行时规则改写引擎 | `references/newmoon-events.md` | §413–§432 |
| 第三十九册 — | `references/rhythm-replicas.md` | §457–§478 |
| 第四十册 射击与摸金（搜打撤）游戏复刻手册 | `references/shooter-replicas.md` | §479–§502 |
| 第四十一册 MOBA 与策略游戏复刻手册 | `references/moba-strategy-replicas.md` | §503–§528 |
| 补编 社区作品提炼 | `references/community-techniques.md` | §C1–§C5 |
| 补编 社区素材包 | `references/community-asset-pack.md` | §C6 |

---

## IR 速览（详见 `references/ir-format.md`）

```yaml
project:
  name: 我的作品
  extensions: [pen]          # 用到画笔扩展时声明
  stage:                     # 舞台（全局作用域）
    backdrops: [{ name: 草地, asset: assets/bg.png }]
    variables:
      最高分: { value: 0, cloud: true }   # ← 云变量（最多 10 个）
    scripts:
      - - when_green_flag_clicked:        # 脚本 = 积木 repr 的平铺列表，首个是帽子积木
        - broadcast: 开始
  sprites:
    - name: 小猫
      x: 0; y: 0; size: 100; direction: 90
      costumes: [{ name: cat1, asset: assets/cat.svg }]
      sounds:   [{ name: beep, asset: assets/beep.wav }]
      variables: { score: 0 }              # 该角色的局部变量
      procedures:                           # 自定义积木
        - name: 画正方形 %n
          args: [边长]
          script:
            - repeat: { times: 4, do: [ { move_steps: { var: 边长 } }, { turn_right: 90 } ] }
      scripts:
        - - when_green_flag_clicked:
          - pen_down:
          - repeat: { times: 50, do: [ { move_steps: 10 }, { turn_left: { degrees: { random: [-15,15] } } } ] }
          - pen_up:
        - - when_receive: 开始
          - say: { text: 出发啦！, secs: 2 }
```

### 积木（block）的写法

每个积木是一个映射 `{ <积木名>: <值> }`。`<值>` 的写法按输入而定：

- **无输入**：`{ pen_down: null }`
- **单个输入**：`{ move_steps: 10 }`
- **多个输入**：字典按输入别名写，例如 `{ say: { text: 你好, secs: 2 } }`
- **子栈（C 形积木）**：`do:` 写循环/分支体；`if_else` 的否则分支用 `else:`
- **条件（布尔）**：`cond:` 接布尔积木或表达式
- **变量/列表引用**：任意输入处写 `{ var: 分数 }` / `{ list: 排行榜 }`
- **表达式嵌套**：`{ turn_left: { degrees: { random: [-15,15] } } }`
- ⚠️ **单操作数运算（`not`）必须写 `operand:`**：
  `{ not: { operand: { equals: { a: 1, b: 2 } } } }`
  写成 `{ not: { equals: ... } }` 会**静默生成空操作数**（条件恒为真/假，不报错）。
  （`and` / `or` 用列表形式：`{ and: [A, B] }`，最多两个操作数。）
- ⚠️ **带 `else` 的分支必须用 `if_else`**：
  `{ if: { cond: ..., do: [...], else: [...] } }` 里的 `else` 会被**静默丢弃**
  （`control_if` 只有 SUBSTACK 一个子栈槽位，没有 SUBSTACK2）。
  正确写法：`{ if_else: { cond: ..., do: [...], else: [...] } }`。
  （构建器现在会自动升级并给出警告，但请直接写 `if_else`。）
- ⚠️ **Scratch 3 没有 `atan2` 积木**（scratch-vm 未实现，写了会静默返回 0）：
  角度只能用 `mathop` 的 `atan`（**单位是度**）自己拼，或改用向量 +
  叉积（见 `references/deep-shadow-raycasting.md`）。
  同样**没有** `>=` / `<=`（用 `not(<)` / `not(>)` 代替），也**没有** reporter 级 if/else。
- **动态下拉菜单**：直接写字符串值，`{ goto: { to: _mouse_ } }`
- **静态下拉菜单**：`{ set_effect: { effect: COLOR, value: 25 } }`
- **广播**：`{ broadcast: 开始 }` / `{ when_receive: 开始 }`
- **变量/列表积木**：名字单独给，`{ set_variable: { var: 分数, value: 10 } }`
- **自定义积木调用**：`{ call: { proc: 画正方形 %n, args: [100] } }`

### 积木名怎么查

**`references/blocks.md` 覆盖全部 188 个积木**（9 大类 + 画笔/音乐/朗读/翻译/
视频感应/语音转文字扩展），每个积木都给出：opcode、形状、友好名、Scratch 官方
英文原文、每个输入/字段的类型与 sb3 编码示例、以及完整的 sb3 积木 JSON。

- 友好名/原始 opcode 对照：`references/blocks.md`
- 机器可读规范：`references/blocks-spec.json`（`blocks` / `aliases` / `input_aliases`）

### 扩展积木（Scratch 自带的 6 个扩展，34 个积木）

Scratch 内置：画笔(13) / 音乐(9) / 朗读(3) / 翻译(2) / 视频感应(4) / 语音转文字(3)。

```yaml
project:
  extensions: [pen]          # ← 用了扩展必须登记，否则 Scratch 里积木报错
  sprites:
    - name: 画笔人
      scripts:
        - - when_green_flag_clicked: null
          - set_pen_size: { size: 4 }
          - pen_down: null
          - repeat: { times: 36, do: [{ move_steps: 10 }, { turn_right: 10 }] }
```

**自制积木（自定义积木）**用 `target.procedures` 声明，不要手写 `procedures_*`：

```yaml
    - name: 猫
      procedures:
        - name: 画正方形 %n      # ← %n 表示带参数
          args: [边长]
          warp: true             # 不逐帧执行，循环多时必开
          script:
            - repeat: { times: 4, do: [{ move_steps: { var: 边长 } }, { turn_right: 90 }] }
      scripts:
        - - when_green_flag_clicked: null
          - call: { proc: 画正方形 %n, args: [60] }
```

完整清单与坑（扩展 id 大小写敏感、画笔是全局的、帽子积木要放最前…）见
**`references/extensions.md`**。

---

## 素材生成

### 社区素材包（有现成素材时优先复用）

11 个真实社区作品提炼的 **1410 个去重素材**与 **5 个已验证可编译的 IR 模板**，见
`references/community-asset-pack.md`（§C6）。做有画面/有声音要求的作品时，**先检索再决定要不要生图**——
现有示例 82% 零音效、造型中位 2–4 个，这是成品「不像作品」的主因，不是逻辑不够。

```bash
python scripts/asset_pack.py stats
python scripts/asset_pack.py search 办公室 --kind backdrop
python scripts/gen_community_template.py --list
```

IR 里直接写 `asset: "community:<id>"`，`build_sb3.py` 会在编译前自动展开成实际文件；
不写 `name` 时自动补素材原名。样本层（63 个 / 0.76 MB）随 skill 分发，全量库在本机
`../community-crawler/data/asset_pack/library/`（351 MB，**不进分发包**），
也可用环境变量 `COMMUNITY_ASSET_LIBRARY` 指定。

> ⚠️ 素材来自社区公开作品，**仅供学习参考**。`assets/community/manifest.json` 每条带来源 CID、
> 作品名与作品页 URL；对外分发/商用前须回溯原作者授权，「转载」「改编」作品尤其要确认原始授权链。

> ## 🔒 铁律：生图默认最高质量
>
> **除非用户明确要求更低质量 / 更快出图，一律用最高质量生图。**
> 用户没提画质要求时按最高质量走，**不得因为省时间、省积分、赶进度自行降级**。
> 只有用户明确说「随便出一张」「要快」「低质量就行」等，才允许降级，
> 且降级时要在回复里说明用的是低质量。
>
> 具体默认参数与可直接复制的调用模板 → `references/asset-guide.md` §一

### 图片（背景 / 角色）

1. 用 **ImageGen** 生成 PNG，**必须显式传参数**（不写就是低画质）：
   - `quality: high`、`size: 1536x1024`（背景）/ `1024x1024`（角色）—— **实测唯一稳定有效的画质开关**
   - `footnote` 留空、提示词带 `crisp edges, sharp focus, high detail, no watermark`
   - **⚠ 实测两个坑**：本机 `background: transparent` 不生效（输出仍是 RGB 无 alpha），
     `footnote` 也挡不住右下角强制水印 → 角色照旧 `--remove-bg`（会顺带抠掉浅色水印），
     背景图用 `--crop-watermark` 裁掉水印区。详见 `references/asset-guide.md` §一.0
   - 角色提示词另需 `isolated on transparent background, no ground, no shadow` ——
     AI 常把「透明」画成浅灰棋盘格，直接用会在 Scratch 里出现灰方块底
   - **保留原始大图**，只把整理后的图写进 IR，以后换尺寸能从原图重导
   - 完整参数表与提示词模板见 `references/asset-guide.md` §一.1
2. 用 `scripts/prep_asset.py` 整理：
   ```bash
   # 角色：抠背景（连水印一起） + 裁透明边 + 画质增强 + 自检
   python3 scripts/prep_asset.py --in cat_raw.png --out cat.png \
       --mode sprite --max 300 --remove-bg --trim --hq --check-alpha
   # 舞台背景：裁掉右下角水印 + 裁填到 480×360（不抠背景，舞台背景本来不透明）
   python3 scripts/prep_asset.py --in bg_raw.png --out bg.png \
       --mode stage --fill --hq --crop-watermark
   # 镜像造型（角色朝左时用，见下）
   python3 scripts/prep_asset.py --in cat.png --out cat_left.png --mode sprite --flip-h
   ```

### 角色的朝向与翻转（**容易做错，务必看**）

Scratch 有三种旋转风格（见 scratch-vm `RenderedTarget._getRenderedDirectionAndScale`）：

| `rotationStyle` | 行为 | 适合 |
|---|---|---|
| `all around`（默认） | 角色**整个旋转**，朝上走就头朝下 | 球、纸片 |
| **`left-right`** | 始终站立，但 `direction < 0` 时**整个造型水平镜像** | **人物、动物** |
| `don't rotate` | 不转不翻 | 图标、UI |

**做角色时必须写 `rotationStyle: left-right`**，否则角色朝上走会整个倒过来。

而 `left-right` 会把**整个造型**镜像 —— 举起的爪子、身上的字、手里的东西
全会翻到另一边。标准解法是**两套造型 + 按朝向切换**：

```yaml
- name: 猫
  rotationStyle: left-right
  costumes:
    - {name: 猫-右, asset: assets/cat.png}       # 原始
    - {name: 猫-左, asset: assets/cat_left.png}   # --flip-h 生成的镜像
  scripts:
    - - when_green_flag_clicked: null
      - forever:
          do:
            - if:
                cond: {less_than: {a: {direction}, b: 0}}   # 朝左
                do:
                  - switch_costume: {costume: 猫-左}
                else:
                  - switch_costume: {costume: 猫-右}
```

详见 **`references/sprite-art.md`**（角色美术规范：背景 / 翻转 / 多造型）。

### UI 素材（首页 / 聊天框 / 数字牌面）

```bash
# 首页背景（整屏 480×360）
python3 scripts/make_ui_assets.py titlebg --out assets/ui/title_bg.png \
    --title "猫抓老鼠" --subtitle "用方向键控制猫" --tip "点击「开始游戏」进入"
# 按钮 / 标题卡
python3 scripts/make_ui_assets.py panel --out assets/ui/btn_start.png \
    --w 150 --h 50 --text "开始游戏" --radius 25
# 数字 0~9（给「数字精灵」角色用）
python3 scripts/make_ui_assets.py digits --out-dir assets/ui --size 44
# 聊天框台词（每句一张 + 一张空白底板）
python3 scripts/make_ui_assets.py chatlines --out-dir assets/ui/chat \
    --lines-file lines.txt --blank assets/ui/chat/chat_blank.png
# 大地图（滚动世界，比舞台大）+ 小地图底图与标记点
python3 scripts/make_ui_assets.py world --out assets/ui/bigmap.png --w 960 --h 720
python3 scripts/make_ui_assets.py minimap --out-dir assets/ui
# 家具（独立障碍角色：背景图里的家具没有碰撞箱，必须单独做成角色）
python3 scripts/make_ui_assets.py furniture --out-dir assets/ui
# 视野阴影遮罩（整屏黑幕 + 中央透明洞，手电筒效果）
python3 scripts/make_ui_assets.py darkness --out assets/ui/dark_overlay.png --hole-r 72
# 弹窗右上角的关闭按钮（×）
python3 scripts/make_ui_assets.py closebtn --out assets/ui/btn_close.png
```

### 音频（音效 / 音乐）

**全部由 agent 本地离线生成，不接入任何外部 TTS / 音乐 API。**

```bash
python3 scripts/gen_audio.py list                     # 列出全部预设
python3 scripts/gen_audio.py sfx --name coin   --out assets/coin.wav    # 17 种音效预设
python3 scripts/gen_audio.py bgm --mood chase --bars 4 --out assets/bgm.wav  # 7 种程序化 BGM（无缝循环）
python3 scripts/gen_audio.py melody --notes "C4:1 E4:1 G4:2" --dur 0.2 --out assets/jingle.wav
```

生成的 WAV 直接作为 sprite 的 `sounds[].asset`；BGM 放舞台上，
用「播放 声音直到播放完毕」放进 `forever` 即可无缝循环。

详见 `references/asset-guide.md`。

---

## 云变量与云列表

- **云变量**：IR 里写 `{ value: 0, cloud: true }`，**必须声明在 `stage.variables`**，
  这样所有角色共用同一个变量。sb3 编码为 `["最高分", 0, true]`。
  Scratch 3.0 限制：**每个项目最多 10 个云变量**（编译时会检查并报错）。
- **云列表**：**Scratch 3.0 不支持**。官方 sb3 规范的 list 定义只允许
  `[名字, 内容]` 两项，scratch-vm 也只给标量变量加 `isCloud`。
  如果写了 `cloud: true` 的列表，序列化器会打印明确告警并按普通列表生成。
  需要共享列表时，用「全局列表 + 云变量存版本号」或「云变量存 JSON 字符串」。

---

## 重要约束

- **不要手写 project.json 或 sb3 数组结构**——那是序列化器的工作。AI 只写 IR。
- IR 根必须是 `{ project: ... }`，且至少包含 `stage` 或 `sprites` 之一。
- **每个 target 至少要有一个造型**（舞台用 `stage.backdrops`，角色用 `costumes`）——
  官方 sb3 规范要求 `costumes` 至少 1 项。
  （`digit_display` / `chat_box` / `list_display` 会自动补齐造型，也算有造型。）
- **每个脚本必须以帽子积木开头**。scratch-vm 的 `greenFlag()` 只启动帽子积木，
  顶层放裸的 `forever` 会**静默不执行**。要「一直重复」就挂在绿旗帽子下面。
- **游戏类作品必须有首页**（`project.title_screen`），对话必须用**自制聊天框角色**
  （`chat_box` + `chat_say`），变量/列表用**角色展示**（`digit_display` / `list_display`）
  而不是监视器，角色尺寸要控制在屏高 1/3 以内，重现点要用 `safe_spawn` 避开玩家。
  详见 `references/hard-requirements.md`。
- **数字精灵必须完整显示且带文字标签**：`digit_display` 的多位数字会自动把 `gap`
  调到 ≥ 数字屏宽 + 6（不重叠/不裁切），并**必须**加 `label` 字段生成「这是什么变量」
  的文字标签角色；构建后要用 Scratch 目视确认。详见上方「⚠️ 铁律 1 / 铁律 2」。
- **中大型作品用进阶技巧**：世界比舞台大就做「大地图 + 小地图」滚动（相机变量 + 小地图标记）；
  角色移动用「速度 + 摩擦 / 缓动」而不是瞬移；用 `game_state` 状态机 + 广播调度各阶段，
  并用 0/1 变量做可切换开关（如小地图开关、音效开关）。
  恐怖/潜行题材加「视野阴影」（黑幕 + 透明洞 + 洞跟玩家走，注意先切小造型再设 size 绕 150% 上限）；
  有设置/帮助面板就加「面板 + 遮罩 + 关闭按钮」三件套（遮罩防穿透点击）；
  要署名就在标题屏放署名卡并在致谢栏写清作者（**不要**写「禁止改编」，违反 Scratch 社区规范）；
  爆炸/火花用克隆粒子（速度必须是角色级私有变量，否则所有克隆共享一个值）。
  配方见 `references/advanced-techniques.md`。
- **⚠️ 选项菜单不要用「询问」积木**：「询问并等待」会**阻塞当前脚本**、
  样式不可控、移动端弹键盘。正确做法是**每个选项一个角色按钮**，
  按钮只广播意图、由舞台统一决定去哪（§77）。
- **⚠️ 克隆体也会响应本体的事件帽子**：本体有「当按下空格键」时，
  按一次会生成 N 个克隆 → N 个克隆各生成 N 个 → 指数爆炸。
  必须加**私有标志位**（`是克隆`）挡住（§75 / §78）。
- **⚠️ 克隆上限 300，超限 Scratch 会静默丢弃新克隆**（不报错）：
  看起来像"子弹发不出去"。排查靠计数器变量（生成 +1、销毁 -1）（§78）。
- **背景音乐要一个 `forever` 管淡入淡出**：两个循环各改一次音量会互相打架；
  用「目标音量」变量决定往哪边走。⚠️ **Scratch 音量是全局的**，
  BGM 与音效共用一个旋钮，BGM 要在**素材层面**压低（§76）。
- **手感类作品参照第七册**：受击要有闪白 + 击退 + 顿帧（全局标记，所有角色一起停）；
  缓动滑入用 `divide` 指数逼近时**必须加停止条件**；
  节奏判定的 `and` **只有 2 个输入**。详见 `references/game-feel-and-interaction.md`。
- **玩法类作品参照第三册**：回合制战斗要**伤害保底 + 独立 if 的属性克制表**；
  换场景用 `当背景切换到` 钩子并**重新定位角色**；
  菜单用**四态 state 变量**；节奏游戏用**计时器**做节拍（必须 `>` 不是 `=`）；
  敌人决策可用**效用 AI**（打分取最高）；视线遮挡用「步进 + 碰到颜色」。
  配方见 `references/game-design.md`。
- **作品要能署名与溯源**：`build_sb3.py` 会在 `meta` 里写 `agent` 字段，
  涉及用户原创的题材/美术时，在标题屏放署名角色，并在「说明与致谢」注明作者与素材来源。
- **平台跳跃/物理要把规则拆开**：重力、地面检测、跳跃、水平移动**各写一个 forever**，
  不要塞进一个大积木堆；地面检测用「脚下感应点」或颜色，别用整个造型（否则角色会浮着）。
  详见 `references/game-systems.md` §17。
- **敌人 AI 的视野锥要归一化角度**：方向是环形量，`359°` 与 `1°` 只差 2°，
  直接相减会得到 -358，必须折算回 ±180（`((差+180) mod 360) - 180`）。
  视野检测**每 0.1 秒做一次**就够，别每帧算。详见 `references/game-systems.md` §16。
- **云变量只在离散时刻写**：更新太频繁会被服务器丢连接；
  云变量最多 10 个、只能存数字、离线编辑器不可用。详见 `references/game-systems.md` §23。
- **⚠️ 摩擦/阻尼/衰减一律用「乘」，绝不能用「减」**：
  `vx -= 0.2` 会让速度一路减到负无穷、物体**反向加速飞走**（实测 3 秒跑到 x=-69000）；
  正确写法是 `vx = vx * 0.99`。只有**重力/加速度**才用「加/减」——
  分清「谁在变」：摩擦改的是速度本身，重力改的是速度的变化率。
  详见 `references/game-design.md` §49.3.1。
- **⚠️ 一切「一局开始要复位」的东西必须挂在「当收到 [重置]」下，不能挂绿旗**：
  点「重试」不是点绿旗，上局的石头还压在猫身上 → 一进游戏立刻又 Game Over。
  最佳分数则**只在新纪录时更新**，绝不能挂在绿旗上（绿旗会清空它）。
  详见 `references/game-design.md` §45.3。
- **⚠️ 积木的输入键名要对**：`change_x` / `change_y` 的输入名是 **`dx` / `dy`**，
  写成 `{ change_x: { value: 10 } }` 会被**静默忽略**（编译成「移动 0」，角色完全不动）。
  `build_sb3.py` 现在会对无法识别的键打警告，但仍以 `references/blocks-spec.json`
  的 `input_aliases` 为准。详见 `references/game-design.md` 附录。
- **伤害公式要有最低伤害保底**：算出来是负数就钳到 1，
  否则高防角色打高防角色永远 0 伤害 → 战斗永远打不完 → 玩家卡死。
  详见 `references/game-design.md` §43.2。
- **⚠️ 算术积木只有 2 个操作数**：Scratch 的「加/减/乘/除」都只有两个输入槽，
  写 `{add: [a, b, c]}` 会**静默丢掉 c**（不报错，但结果不对）。
  三项以上必须**嵌套**：`{add: [a, {add: [b, c]}]}`。
  同理「与/或」也只有 2 个输入。
  详见 `references/physics-engine.md` 附录。
- **物理引擎项目注意三件事**：
  ① Scratch 的「碰到」是**像素级比对**，引擎级项目要自己算 **AABB 包围盒**；
  ② **摩擦/阻尼用「乘」**（见铁律 5）；
  ③ **Verlet 的重力加速度要取负值**（Scratch 的 y+ 朝上），
  且**引力方向必须指向中心**，否则物体会被推出去。
  详见 `references/physics-engine.md` §51–§58。
- **性能红线**：同一克隆体上外观特效 ≤ 3 层；同屏克隆 ≤ 300（一次生成 ≤ 30）；
  同屏多个按钮**不要**用画笔实时写字，用「一张底板 + 克隆 + 私有编号 + 预制文字造型」。
- **不要用 `say` / `think` 做对话**——Scratch 气泡不能排版中文且会挡画面。
- **屏幕读数**用 `stage.monitors` 声明（`{var: 分数, x: 8, y: 8}`），引用不存在的变量会报错。
  但**游戏里优先用 `digit_display` 角色展示**，监视器只适合调试。
- **角色要写 `rotationStyle: left-right`**，并按朝向在「原图 / 镜像图」两套造型间切换，
  否则角色朝上会整个倒过来、朝左时身上左右不对称的部分会被镜像错位。
- **给积木加注释**：在积木的值里写 `comment: "..."`（附在该积木上），
  或用 `stage.comments` 写悬空的操作指引。注释是 Scratch 的便签，能让人读懂作品。
- **积木位置会自动整理**：顶层脚本会被排成网格，不会在 Scratch 里全叠在左上角。
  影子积木（下拉菜单）必须 `topLevel:false`，否则画布上会多出孤立的小下拉框。
- 舞台背景写在 `stage.backdrops`（序列化器会映射到 Scratch 内部的 costumes 数组）。
- 用画笔等扩展积木时必须声明 `extensions: [pen]`（等等），
  扩展 id 大小写敏感（`videoSensing` / `text2speech` / `speech2text` 是驼峰）。
- **自定义积木用 `target.procedures` 声明**，不要手写 `procedures_*` opcode；
  带参数的积木名字里要有 `%n`，循环多时开 `warp: true`。
- 默认 `assets-src` 是 IR 文件所在目录；素材路径相对于它解析。
- 变量作用域：舞台上是全局，角色上是局部。角色引用全局变量时用名字即可。
- YAML 里流式集合（`[...]`）内部不能用 `- 条目`；子栈请用块状写法（见 ir-format.md）。

---

## 校验通过标准

**八层校验，全过才算交付：**

| # | 命令 | 通过标志 |
|---|---|---|
| 1 | `python scripts/validate_sb3.py --sb3 <作品.sb3>` | `全部校验通过 ✅` |
| 2 | `node scripts/validate_schema.mjs <project.json>` | `SCHEMA_OK` |
| 3 | `node scripts/validate_parser.mjs <作品.sb3>` | `PARSER_OK` |
| 4 | `node scripts/validate_runtime.mjs <project.json>` | `RUNTIME_OK` |
| 5 | `node scripts/smoke_test.mjs <作品.sb3> --catch` | `SMOKE_OK` + 变量符合预期 |
| 6 | `node scripts/verify_techniques.mjs <作品.sb3> <out.txt>` | `ALL_NEW_TECH_OK` |
| 7 | `python scripts/semantic_check.py` | `SEMANTIC_OK` |
| 8 | `python scripts/quality_gate.py --sb3 <作品.sb3> --spec <规格表>.json --strict` | `QUALITY_GATE_OK`（六项资产密度达标） |

> 前七层保证「能打开、逻辑对」；**第 8 层才保证「像作品」**。
> 不做质量门禁的话，一个零音效、2 个几何造型的 demo 可以全过前七层被交付。

- 第 2/4 层要的是**解压后的 `project.json`**（sb3 是 zip）：
  `python -c "import zipfile;zipfile.ZipFile('x.sb3').extract('project.json','out/')"`。
- 第 5 层 `--catch` 会模拟点开始按钮 + 把猫和鼠的世界坐标同步，从而触发碰撞计分。
- 第 6 层专测进阶技巧：视野阴影（黑幕结构与层级）、帮助弹窗与「当关闭被点击」、
  克隆粒子的结构与私有变量。
- 第 7 层是**积木语义回归**：前六层只保证「能打开、不崩」，
  这一层才保证「1+2 真的等于 3」。改动构建器、别名表、输入映射后必跑。
- **答题/测验类作品额外必跑** `node scripts/quiz_behavior_check.mjs <作品.sb3>` →
  `QUIZ_LOGIC_OK`（模拟点开始、逐题作答、反馈期重复点击、越界结算）。
  它抓的是「广播重启线程导致卡死」「wait 期间重复计分」这类四层校验看不见的逻辑错。
  完整范式见 `references/quiz-systems.md` §109。
- **消除 / 三消类作品额外必跑** `node scripts/match3_behavior_check.mjs <作品.sb3>` →
  `MATCH3_LOGIC_OK`（模拟绿旗生成、检查满盘/无初始三连/36 克隆、构造横/纵三连消除并计分、
  无匹配交换验证棋盘完好换回）。
  它抓的是「下落无守卫导致整盘随机重填」「裸变量名被当字面量导致扫描落空」这类四层校验看不见的逻辑错。
  完整范式见 `references/elimination-games.md` §115。
- **射击 / 弹幕类作品额外必跑** `node scripts/shooter_behavior_check.mjs <作品.sb3>` →
  `SHOOTER_LOGIC_OK`（模拟绿旗生成、连发 3 次验证子弹克隆守卫、生成 2 敌人、子弹上飞/敌人下落、
  位置碰撞计分且敌人被销毁、撞玩家触发游戏结束）。
  它抓的是「克隆无守卫导致指数爆炸」「嵌套 IF 里 CLONE 被漏编译导致敌人造不出来」
  「碰撞用 touching 无头测不到」这类四层校验看不见的逻辑错。
  完整范式见 `references/shooter-games.md` §120。
- **教育课件 / 数据可视化类作品额外必跑** `node scripts/edu_behavior_check.mjs <作品.sb3>` →
  `EDU_LOGIC_OK`（模拟绿旗生成、检查 页码/得分 复位、柱子数=数据长度且每柱高度=数据值、
  翻页 页码 1→2→1、答对得分且答错不加分）。
  它抓的是「翻页用 ask 无头测不到」「图表用 set size 无头看不到」「克隆无守卫指数爆炸」
  这类四层校验看不见的逻辑错。完整范式见 `references/edu-courseware.md` §126。
- **联机 / 双人对战类作品额外必跑** `node scripts/multiplayer_behavior_check.mjs <作品.sb3>` →
  `MULTIPLAYER_LOGIC_OK`（模拟绿旗初始化、本方回合写云_进度并换手、非本方回合忽略、进度到 5 结束）。
  它抓的是「回合守卫缺失导致双端都动」「进度累加逻辑错」这类四层校验看不见的逻辑错。
  完整范式见 `references/multiplayer.md` §129。
- **伪 3D / 透视类作品额外必跑** `node scripts/3d_behavior_check.mjs <作品.sb3>` →
  `D3_LOGIC_OK`（模拟绿旗生成、深度递减、屏幕坐标/尺寸随逼近变化、飞过摄像机触发重置）。
  它抓的是「深度下不到阈值导致 passed 不触发」「尺寸 ∝ 1/z 方向反了」这类逻辑错。
  完整范式见 `references/3d-games.md` §135。
- **第一人称 / 迷宫类作品额外必跑** `node scripts/firstperson_behavior_check.mjs <作品.sb3>` →
  `FP_LOGIC_OK`（模拟绿旗、朝西探测到边界墙、朝东探测为空地、撞墙不移动、空地才移动、左转 90°）。
  它抓的是「if/else 被并到 do 导致撞墙检测失效」「方向数学错」这类逻辑错。
  完整范式见 `references/first-person.md` §141。
- **棋类 / 棋盘对弈类作品额外必跑** `node scripts/board_behavior_check.mjs <作品.sb3>` →
  `BOARD_LOGIC_OK`（模拟绿旗清空棋盘、落子写入与换手、五连珠判黑胜、结束守卫）。
  它抓的是「落子四段式守卫缺失」「五连珠扫描的 if/else 陷阱导致连数到不了 5」这类逻辑错。
  完整范式见 `references/board-games.md` §145。
- **剧情故事 / 视觉小说类作品额外必跑** `node scripts/story_behavior_check.mjs <作品.sb3>` →
  `STORY_LOGIC_OK`（模拟绿旗、打字机逐字显示、分支跳转、双结局到达、对话锁：对话中=1 时移动被挡、结束后放开）。
  它抓的是「用『询问』积木做选项导致阻塞」「打字机用固定次数 REPEAT 文字错位」「多结局有死支永远点不到」
  「对话期间不锁操作导致穿帮」这类四层校验看不见的逻辑错。完整范式见 `references/story-narrative.md` §155。
- **平台跳跃 / 横版闯关类作品额外必跑** `node scripts/platformer_behavior_check.mjs <作品.sb3>` →
  `PLATFORMER_LOGIC_OK`（模拟绿旗、自由落体精确停在地面顶面、跳跃 vy 转正且 y 上升、松键回落、
  持续右移撞墙不穿透、路上金币计数+得分、镜头跟随与左端钳制、重置回出生点且金币复活）。
  它抓的是「帧循环用两条 forever 导致双倍速」「碰撞用 touching 无头测不到/背景地形碰不到」
  「分轴解算没独立回退导致墙角卡穿」这类四层校验看不见的逻辑错。
  ⚠️ 校验驱动必须「广播 帧 + stepN(2)」，用 stepN(1) 会让物理隔帧推进。完整范式见 `references/platformer.md` §158/§166。
- **地铁 / 交通模拟类作品额外必跑** `node scripts/metro_behavior_check.mjs <作品.sb3>` →
  `METRO_LOGIC_OK`（牵引加速、限速封顶、表针角度映射、制动减速、里程→折线插值定位、
  到站判定=位置+停稳双条件、高速通过不开门、开门四态推进到全开、门未关禁止牵引、关门后下一站推进并恢复牵引）。
  它抓的是「漏 ÷3.6 导致一帧飞过整站」「只判位置不判停稳就开门」「门没关能牵引」
  「表针角色设了不旋转」这类四层校验看不见的逻辑错。完整范式见 `references/metro-sim.md` §168/§170/§171。
- **地铁「驾驶」类（要能真开、要对标停车）再跑** `node scripts/metro_drive_behavior_check.mjs <作品.sb3>` →
  `METRO_DRIVE_LOGIC_OK`（剩余里程初始化 / 牵引加速 / 限速封顶 / 里程积分 `Δ=速度÷系数` /
  制动到零不回退 / 推荐速度闭式 `v=3.6√(2a(d-5))` / 超速自动干预 / 到站握手（停稳且 |d|≤5）/
  开门重置里程+站点推进 / 冲标 `d<-5` 扣分 / 退回两步才进窗口 / 三显示 9000·5000 阈值 /
  前车推进与间距扣车长 / 终点结算）。它抓的是「漏 1400 车长」「站点先推进后重置的顺序错」
  「推荐速度滞后一帧导致冲过保护点」「恰好 5000 判成黄灯」这类四层校验看不见的逻辑错。
  完整范式见 `references/metro-driving-deep.md` §212/§214/§215。
- **自动驾驶 / ATO / 全自动运行类作品额外必跑** `node scripts/ato_behavior_check.mjs <作品.sb3>` →
  `ATO_LOGIC_OK`（起步延时到点发车 / 牵引加速 / 限速封顶不超速 / 进站前 260 米已减速 /
  第一段精确停车在 ±5 米且速度归零 / 开门逐帧到 100 且保持 ≥30 帧 / 关门后站点推进+里程重置+限速切换 /
  第二段自动发车 / 跑完全程状态=完成 / **红灯降级到 0 km/h** / **欠标 9 米自动爬行补标并停稳**）。
  它抓的是「对称死区导致卡在 1.2 km/h 停不下来」「用瞬时条件推断爬行导致脉冲蹭行」
  「爬行退出阈值 = 停车窗口导致死锁在 5.05 米」「停稳状态零时长导致校验读不到」这类**肉眼完全看不见**的控制逻辑错。
  ⚠️ 四个坑全部属于「四层校验 + 冒烟测试都过、但行为就是不对」，写自动控制类必跑。
  完整范式见 `references/ato-autopilot.md` §236–§248。
- **任何作品的 UI 素材，交付前必跑** `python scripts/check_ui_assets.py` →
  `UI_ASSETS_OK`（结构 / 配色 / 网格 / 一致性）。
  它抓的是「四层校验完全看不见、装进 sb3 才炸」的五类问题：SVG 里写了 `<text>`（中文变豆腐块）、
  用了 `filter`/`mask`（缩放糊）、颜色不在四色系（黄/绿/青绿/暖灰）、按钮尺寸不在三档网格、
  图标线宽不统一。完整规范见 `references/ui-asset-craft.md` §251/§257/§261。
- **用了 `assets/uikit/` 素材或自建 UI 套件的作品再加跑** `node scripts/ui_kit_behavior_check.mjs <作品.sb3>` →
  `UI_KIT_LOGIC_OK`（角色数 / 开局状态 / 帧循环推进 / 按钮造型名 / 进度条换档 /
  弹窗组同时显示隐藏 / 弹窗打开时挡住帧逻辑 / 关窗后恢复 / 重开复位 / 造型齐全性）。
  它抓的是「造型名拼错导致 `switch costume` 静默失败、界面永远停在第一帧」这类**素材工程的典型错**。
  完整范式见 `references/ui-asset-craft.md` §254/§256。
- **任何作品只要加了声音，交付前必跑** `python scripts/check_audio_assets.py` → `AUDIO_ASSETS_OK`
  （格式 44.1k/单声道/16bit · **四层响度 ±2dB** · 首尾归零 · 尾部衰减 · DC 偏移 · 削波 · 时长区间）。
  它抓的是「耳朵听不出来、但一听就觉得廉价」的五类问题：**所有音效一样响**（点按钮=爆炸）、
  首尾硬切（咔哒）、DC 偏移（嗡嗡）、中间断音、UI 音过长（连点糊成一片）。
  完整规范见 `references/audio-design.md` §264/§267/§274。
- **数学 / 算法 / 解题类作品额外必跑** `node scripts/math_behavior_check.mjs <作品.sb3>` → `MATH_LOGIC_OK`
  （N 皇后 4/5/6/8 的解数为 2/10/4/92 + 皇后列长度 = n · 分数 4 组（含负数与约分）· 质数 25 个 / 前 5 个 / 第 25 个 = 97）。
  它抓的是「四层校验完全看不见」的错：**回溯回退时多 +1（8 皇后只得 14 个解）**、
  找到解后行号不归位（死循环）、列表长度与 n 不同步、化简没取整（`5.000000001`）、筛法边界错。
  ⚠️ 数学类**必须用已知答案当断言**，不能写「跑出来多少就断言多少」。
  完整范式见 `references/math-and-reasoning.md` §284/§290。
- **桌游 / 卡牌 / 牌桌类作品额外必跑** `node scripts/card_behavior_check.mjs <作品.sb3>` → `CARD_LOGIC_OK`
  （斗地主牌型 14 例：单/对/三/三带一/三带二/顺子/连对/飞机/飞机带单/炸弹/王炸/`JQKA2` 不能成顺 ·
  比大小 7 例 · UNO 2 例 · 狼人杀投票 3 例含平票与「已出局不计票」· **发牌 12 张且身份计数正确、洗牌两次顺序不同**）。
  它抓的是「判定顺序错（`6666` 当三带一）」「飞机带单主值取错」「炸弹不通吃」
  「UNO 只判数字忘同色」「投死人」「平票只取一人」这类四层校验看不见的规则错。
  完整范式见 `references/tabletop-games.md` §295/§296/§304。
- **音乐 / 演奏 / 编曲类作品额外必跑** `node scripts/music_behavior_check.mjs <作品.sb3>` → `MUSIC_LOGIC_OK`
  （简谱→MIDI：`1 1 5 5 6 6 5` 八度 4 → `60 60 67 67 69 69 67` · 休止符解析成 0 ·
  八度 5 全部 +12 / 八度 3 首音 48 · 乐器 5/1/21 → 内部 `currentInstrument` 4/0/20 · 音乐状态按角色隔离）。
  它抓的是「乐器编号从 0 起（选钢琴出来是小提琴）」「越界以为钳到两端（实际是环绕）」
  「休止符写成 60」「多声部塞在一个角色里」这类错。
  ⚠️ 校验**不要触发演奏**：`play note for beats` 按虚拟时间阻塞，测长谱会超时。
  完整范式见 `references/music-and-instruments.md` §306/§307/§318。

- **狼人杀 / 桌游作品额外必跑** `node scripts/card_behavior_check.mjs` → `CARD_LOGIC_OK`
  （牌型 14 / 比大小 7 / UNO 2 / 投票 3 / 板子装载 / 警长竞选 6 / 警徽流 5 / 自爆 5 / 屠边 5）。
  它抓的是「四层校验完全看不见」的错：**身份位表多一个占位 0 导致阵营统计整体错位**、
  **两个平级 IF 互相覆盖导致双爆退化成单爆**、**无民板子开局判狼人胜**、
  接徽人已死却随机挑一个、自爆复用「放逐」死因让猎人错误地能开枪。
  完整规则见 `references/werewolf-complete.md` §335–§344；品类库见 `references/boardgame-library.md`。

> ### ⚠️ 「能打开」≠「逻辑对」
>
> 过去四类问题只会发 `[警告]` 却照样打印 `OK 生成`、四层校验也全过，
> 结果作品能打开但**行为和 IR 意图不符**。现在构建器默认**直接中止**（退出码 3，
> 不生成 `.sb3`）：
>
> 1. 算术/逻辑积木写 3 个以上操作数 → 第 3 项起被丢弃（`{add: [1,2,100]}` 算成 3）。
>    必须嵌套：`{add: [1, {add: [2, 100]}]}`。
> 2. 未知键被忽略 → 分支/参数整个丢掉。最常见：`if_else` 写了 `then`，
>    正确是 `do` + `else`。
> 3. 输入别名写错 → 生成空操作数（静默变 0/空串）。
> 4. `else` 与 `if` 同级 → 构建器会自动升级为 `if_else`（这个**不改变语义**，仍只是警告）。
>
> 看到 `IR 语义错误（N 处，构建已中止）` 就按提示改 IR，**不要用 `--lenient` 绕过** ——
> 那只会把错误重新藏起来。交付前再跑 `python scripts/semantic_check.py` 确认积木语义没偏。

> ⚠️ **无头环境的两个已知盲区**（不是作品的问题）：
> ① `setSize()` 的赋值写在 `if (this.renderer)` 里 → 无头环境**看不到 size 变化**；
> ② `makeClone()` 依赖渲染器登记 `isClone` → 无头环境**克隆会被立刻回收**。
> 这两项只能做**结构级**校验，最终效果要在 Scratch 编辑器里目视确认。

若运行时报 `Non-ascii character in FixedAsciiString`，说明 project.json 未通过
scratch-parser 结构校验而回退到了 SB1 解析——**这只是症状不是原因**。
真正的原因通常是某个积木写错了（菜单值写成数组、变量该放 field 却放了 input、
opcode 拼错）。用 `references/blocks.md` 核对，或直接跑 `scripts/validate_sb3.py`
看它报的具体位置。

> ⚠️ **另一个静默失效坑**：IR 里 `- repeat: 16` + `do:`（标量 + 兄弟键）这种写法，
> 如果序列化器没把友好名解析成规范 opcode，标量会被丢掉 → 编译成「重复 0 次」，
> **不报错、只是什么都不发生**。写 `repeat` 请用完整写法
> `- repeat: {times: 16, do: [...]}`。

---

## 目录结构

> 📌 **关于 `deploy-tools/gen_*.py`**：各册「配套」里提到的生成器是**开发仓库的 source**，
> 只存在于项目 `deploy-tools/`，**不随交付包 / agent 环境分发**（同步只带 `scripts/ references/ examples/`）。
> 拿到包后直接看 `examples/*.yaml`（IR）与 `examples/output/*.sb3`（成品）即可，
> 修改 IR 后用 `python scripts/build_sb3.py --ir ... --out ... --workdir <临时目录>` 重建。
> 包内 `scripts/gen_*.py` 是另一批**素材/探针生成器**，不要与前者混淆。

```
ai-scratch-maker/
├── SKILL.md                     # 本文件
├── README.md                   # 快速上手
├── agents/openai.yaml           # agent 定义（界面与策略）
├── references/
│   ├── blocks.md                # ★ 全部 188 个积木的完整速查表
│   ├── blocks-spec.json         # 机器可读积木规范（blocks / aliases / input_aliases）
│   ├── blocks-spec.md           # sb3 编码规则详解（inputs vs fields、基元、云变量…）
│   ├── blocks-aliases.json      # 友好名对照表（由 scripts/make_aliases.py 维护）
│   ├── ir-format.md             # IR 完整格式说明
│   ├── advanced-techniques.md   # ★ 第一册 15 套进阶技巧（大地图+小地图/平滑移动/开关设计/
│   │                             #   视野阴影/弹窗关闭按钮/防搬/克隆粒子/触屏/血条/
│   │                             #   关卡数据表/缓动物理/音频/投影/性能红线/碰撞箱）
│   ├── game-systems.md          # ★ 第二册 27 套游戏系统与 AI（敌人视野 AI/平台跳跃物理/
│   │                             #   打击感Juice/网格移动/克隆分身/背包商店/随机迷宫/
│   │                             #   存档进度/教学引导/数学工具箱/滑块/波次/对话/成就/
│   │                             #   推箱子/多人同步/动画/子弹/演出/镜头/视差/寻路/
│   │                             #   塔防/音频优先级/八方向/无尽生成/云变量编码）
│   ├── game-design.md           # ★ 第三册 8 套玩法设计（回合制战斗/场景管理/菜单系统/
│   │                             #   节奏游戏/敌人 AI 决策/射线视线/吸引力物理/成长装备）
│   ├── physics-engine.md        # ★ 第四册 8 套物理引擎（AABB 碰撞/Verlet 积分/绳索布料/
│   │                             #   万有引力/弹性碰撞/斜坡检测/对象池/空间分桶）
│   ├── more-techniques.md       # ★ 第五册 8 套进阶技巧（数据驱动瓦片/程序化音乐/
│   │                             #   平滑摄像机/缓动补间/昼夜循环/对话树/迷你地图/转场）
│   ├── pen-techniques.md        # ★ 第六册 8 套画笔与伪 3D（画笔基础/3D 线框/等距投影/
│   │                             #   射线投射迷宫/星空隧道/海龟分形/贝塞尔/笔刷粒子）
│   ├── game-feel-and-interaction.md # ★ 第七册 8 套手感与交互（拖尾/背景音乐/多角色选项
│   │                             #   菜单/克隆的正确用法/受击反馈/演出转场/节奏判定/广播解耦）
│   ├── extension-techniques.md  # ★ 第八册 10 套自带扩展积木（音乐旋律/鼓点/BGM/朗读/翻译/
│   │                             #   视频叠加/动作触发/语音指令；标注 ✅/⚠️/❌ 无头可行性）
│   ├── community-techniques.md  # ★ 第九册 13 套社区作品提炼（数据驱动开关/滚动歌词/输入框/
│   │                             #   平台跳跃/跑酷生成/体素射线/★视野盲区阴影光追/加载圈/
│   │                             #   克隆UI/瓦片相机/排行榜/等距机关/视差）
│   ├── quiz-systems.md          # ★ 第十册 答题/测验系统（四态状态机/题库平行列表/索引判题/
│   │                             #   ★广播重启线程致卡死/无头虚拟时钟/变体），配 quiz.yaml
│   ├── deep-shadow-raycasting.md # ★★ 阴影光追专项教程（线段求交/可见性多边形/±ε 三射线/
│   │                             #   五个必踩的坑：atan2 不存在/if+else 要 if_else/
│   │                             #   自定义积木参数不是变量/过程变量重名/角度环绕）
│   ├── deep-tile-camera.md      # ★★ 瓦片相机专项教程（屏幕=世界-相机/三种地图存法/
│   │                             #   边界钳制/只画窗口/分层视差/等距变体）
│   ├── tabletop-games.md        # ★ 第三十一册 桌游通用方法（牌值编码/牌型/隐藏信息/状态机）
│   ├── werewolf-complete.md     # ★ 第三十三册 狼人杀完全手册（60+身份/板子表/警徽流/自爆/屠边）
│   ├── boardgame-library.md     # ★ 第三十四册 桌游规则库（斗地主/UNO/麻将/德州/三国杀/大富翁…）
│   ├── werewolf-classic.md      # ★ 第三十五册 红狼（狼人杀经典版）：30+身份/15板子/12处差异
│   ├── werewolf-awakening.md    # ★ 第三十六册 网易觉醒体系：13觉醒角色/16板子/四张新表
│   ├── newmoon-events.md        # ★ 第三十七册 新月事件卡：36张经典卡/网易五类事件/快照栈
│   ├── rhythm-games.md          # ★ 第三十八册 音游：唯一时钟/帧量化窗口/谱面/长按/校准
│   ├── rhythm-replicas.md       # ★ 第三十九册 五款代表作复刻：Phigros/PJSK/Milthm/跳舞的线/滚动的天空
│   ├── shooter-replicas.md      # ★ 第四十册 射击与摸金复刻：CS2/和平精英/三角洲/超自然行动组
│   ├── moba-strategy-replicas.md # ★ 第四十一册 MOBA与策略复刻：王者/LOL/三国杀/金铲铲
│   ├── music-and-instruments.md # ★ 第三十二册 乐器与编曲（简谱→MIDI/变量换乐器/多声部/音频转乐器）
│   ├── math-and-reasoning.md    # ★ 第三十册 数学与推理（回溯/筛法/分数/浮点/几何/排列组合）
│   ├── polish-and-feel.md       # ★ 第二十六册 质感与手感（缓动/过冲/顿帧/错峰/微交互/20条清单）
│   ├── ato-autopilot.md         # ★ 第二十七册 ATO 自动驾驶（三层/包络/精确停车/爬行补标）
│   ├── ui-asset-craft.md        # ★ 第二十八册 UI 素材工艺（安全SVG子集/五层体积感/四状态）
│   ├── audio-design.md          # ★ 第二十九册 声音设计（四层响度/时长预算/包络/音高语义）
│   ├── sprite-art.md            # ★ 角色美术规范（透明背景 / 左右翻转 / 多造型 / 尺寸）
│   ├── 早期 15 册：advanced-techniques / game-systems / game-design / physics-engine /
│   │   more-techniques / pen-techniques / game-feel-and-interaction / community-techniques /
│   │   quiz / elimination / shooter / edu / multiplayer / 3d / firstperson / board-games /
│   │   results-screen / story-narrative / platformer / metro-sim / metro-driving-deep /
│   │   game-architecture / voxel-and-light / ui-design-spec / first-person（详见目录）
│   ├── extensions.md            # ★ 扩展积木（6 个扩展 34 积木）与自制积木
│   ├── sb3-schema/              # ★ 官方 sb3 JSON Schema（随 skill 分发，schema 校验自包含）
│   │   ├── sb3_schema.json
│   │   └── sb3_definitions.json
│   └── asset-guide.md           # 图片/音频生成与使用指南
├── scripts/
│   ├── build_sb3.py             # IR -> 合法 .sb3 序列化器（核心）
│   ├── validate_sb3.py          # 结构 + Schema + parser + 运行时 四重校验
│   ├── validate_schema.mjs      # 官方 sb3 JSON Schema 校验
│   ├── validate_parser.mjs      # 官方 scratch-parser 校验（编辑器能否打开）
│   ├── validate_runtime.mjs     # scratch-vm 运行时加载运行
│   ├── smoke_test.mjs           # 行为冒烟测试（变量/位置/监视器是否按预期变化）
│   ├── semantic_check.py        # ★ 积木语义回归（27 例：编译→VM实跑→比对期望值）
│   ├── quiz_behavior_check.mjs   # ★ 答题（逐题点击/防连点/越界结算）
│   ├── match3_behavior_check.mjs # ★ 三消（满盘/无初始三连/横纵消除/换回不损坏）
│   ├── shooter_behavior_check.mjs # ★ 射击（克隆守卫/移动/位置碰撞计分/撞玩家结束）
│   ├── edu_behavior_check.mjs    # ★ 课件（翻页/数据可视化/随堂测验计分）
│   ├── story_behavior_check.mjs  # ★ 剧情（打字机/分支/双结局/对话锁）
│   ├── platformer_behavior_check.mjs # ★ 平台跳跃（落地/跳跃/撞墙不穿透/金币/镜头钳制）
│   ├── metro_behavior_check.mjs  # ★ 地铁入门（牵引/限速/表针/四态门/到站双条件）
│   ├── metro_drive_behavior_check.mjs # ★ 地铁驾驶（里程积分/ATP/三显示/对标/冲标）
│   ├── multiplayer_behavior_check.mjs # ★ 联机（回合守卫/云变量同步/进度推进）
│   ├── 3d_behavior_check.mjs     # ★ 3D（透视除法/深度方向/z 守卫/尺寸∝1/z）
│   ├── firstperson_behavior_check.mjs # ★ 第一人称（前后探测/撞墙不移动/转向数学）
│   ├── board_behavior_check.mjs  # ★ 棋类（落子四段式/五连珠判胜/结束守卫）
│   ├── ato_behavior_check.mjs    # ★ ATO 自动驾驶（包络/精确停车/爬行补标/红灯降级/多站）
│   ├── ui_kit_behavior_check.mjs # ★ UI 套件（造型名/进度条换档/弹窗组同步/镜头挡住帧逻辑）
│   ├── math_behavior_check.mjs   # ★ 数学（N 皇后解数/分数化简/质数筛，用已知答案断言）
│   ├── card_behavior_check.mjs   # ★ 桌游（牌型/UNO/板子/竞选/警徽流/自爆/屠边/红狼/觉醒/新月，120+ 断言）
│   ├── rhythm_behavior_check.mjs # ★ 音游（BPM/谱面/四档/校准/帧量化/去重/漏击/长按/结算）
│   ├── rhythm_replicas_behavior_check.mjs # ★ 五款代表作复刻（判定线/圈/12格/5列/双序列）
│   ├── shooter_replicas_behavior_check.mjs # ★ 射击/摸金（射线伤害/圈/经济/撤离/怪物AI）
│   ├── regress_behavior.sh       # ★ 20 项 behavior check 一键全量回归 → ALL_BEHAVIOR_OK
│   ├── scratch_vm_path.mjs       # 定位 scratch-vm（校验脚本共用）
│   ├── extract_blocks_spec.js    # 从 VM 抽取 blocks-spec.json
│   ├── music_behavior_check.mjs  # ★ 乐器（简谱→MIDI/八度偏移/变量换乐器/状态隔离）
│   ├── verify_techniques.mjs    # 进阶技巧专项校验（视野阴影/弹窗关闭按钮/克隆粒子/碰撞箱）
│   ├── extract_blocks_spec.js   # 从 Scratch 官方源码抽取全量积木规范
│   ├── make_aliases.py          # 生成/维护友好名对照表
│   ├── make_blocks_doc.py       # 由规范生成 references/blocks.md
│   ├── prep_asset.py            # 图片尺寸整理 + 抠背景 + 裁透明边 + 镜像
│   ├── make_ui_assets.py        # UI 素材：首页背景/按钮/数字/聊天框台词/
│   │                             #   大地图/小地图/视野阴影遮罩/UI遮罩/关闭按钮
│   ├── gen_audio.py             # 离线音频合成（17 音效预设 + 7 程序化 BGM）
│   ├── check_doc_ir.py          # 校验手册里的 IR 写法与 blocks-spec.json 是否一致
│   ├── gen_ui_kit.py            # ★ 生成 166 个矢量 UI 素材（按钮/面板/进度条/图标/文字条）
│   ├── check_ui_assets.py       # ★ UI 素材闸门（禁 text/filter、色相合规、网格、线宽）
│   ├── gen_sfx_kit.py           # ★ 生成 22 个分层音效（ui -18 / fx -9 / ev -3 / amb -15 dBFS）
│   ├── math_reference.py        # ★ 算法基线（Python 版 N 皇后/分数/筛法，翻译前的正确性参照）
│   ├── card_reference.py        # ★ 桌游判定基线（牌型/比大小/UNO/投票）
│   ├── audio2notes.py           # ★ 音频转音符（自相关基频 + 切音 + 量化，可输出音高表）
│   ├── check_audio_assets.py    # ★ 音效闸门（分层响度/首尾归零/DC 偏移/削波/时长）
│   ├── gen_probe9.py            # 生成第七册示教工程（technique_probe9.yaml）
│   ├── gen_probe11.py           # 生成第九册示教工程（technique_probe11.yaml：开关阵列/平台跳跃/阴影光追/加载圈）
│   ├── gen_probe13.py           # 生成阴影光追专项示教（technique_probe13.yaml：线段求交/可见性多边形）
│   ├── gen_probe14.py           # 生成瓦片相机专项示教（technique_probe14.yaml：滚动地图/相机跟随/边界钳制）
│   ├── gen_ato.py              # ★ 生成 ATO 自动驾驶工程（--line 换线路：站名/站距/限速表参数化）
│   ├── gen_ref_minecraft3d.py   # 生成完整可玩参考工程（ref_minecraft3d.yaml：第一人称体素光线投射）
│   ├── analyze_corpus.py        # 批量反编译社区 .sb3，抽取技术指纹（扩展/积木频谱/变量/克隆/画笔）
│   ├── digest_sb3.py            # 大工程速读：广播表/自制积木表/注释/opcode 直方图（先看架构）
│   ├── decompile_sb3.py         # 大工程精读：--all 全脚本 / --target 单角色（中缀表达式+缩进）
│   ├── dump_scripts.py          # 把任意 .sb3 的脚本转成可读树，逐块看实现手法
│   └── ir_schema.py             # IR 校验（积木名、帽子积木、造型、监视器、云变量上限）
└── examples/                    # 可运行的示例 IR 与产物 .sb3
    ├── cat_mouse.yaml            # ★ 猫抓老鼠（大地图版）：第一册 15 套技巧全用上
    ├── technique_probe.yaml      # 第一册技巧最小示教工程
    ├── technique_probe2.yaml     # 第二册技巧示教（AI/物理/网格/商店/存档）
    ├── technique_probe3.yaml     # 第二册示教②（推箱子/多人/动画/子弹/演出/镜头）
    ├── technique_probe4.yaml     # 第二册示教③（视差/寻路/塔防/音频/八方向/无尽/云编码）
    ├── technique_probe5.yaml     # 第三册示教（回合制战斗/场景管理/菜单/节奏/AI/装备）
    ├── technique_probe6.yaml     # 第四册示教（AABB/Verlet/绳索/引力/弹性/斜坡/对象池/分桶）
    ├── technique_probe7.yaml     # 第五册示教（瓦片地图/音乐/摄像机/缓动/昼夜/对话/小地图）
    ├── technique_probe8.yaml     # 第六册示教（画笔/3D 线框/等距/射线投射/星空/分形/贝塞尔）
    ├── technique_probe9.yaml     # 第七册示教（拖尾/背景音乐/多角色菜单/克隆用法/受击/节奏）
    ├── technique_probe10.yaml    # 第八册示教（音乐旋律/复调鼓点/视频叠加/朗读/翻译）
    ├── technique_probe11.yaml    # 第九册示教（数据驱动开关阵列/平台跳跃/★视野盲区阴影光追/加载圈）
    ├── technique_probe13.yaml    # 阴影光追专项示教（线段求交/可见性多边形/实体遮挡判定）
    ├── technique_probe14.yaml    # 瓦片相机专项示教（24×16 滚动地图/相机跟随/边界钳制/只画窗口）
    ├── story.yaml                # 第十九册示教（分支剧情/打字机/双结局/对话锁）
    ├── platformer.yaml           # 第二十册示教（Tick 广播/分轴碰撞/可变跳跃/踩踏/镜头钳制）
    ├── metro.yaml                # 第二十一册示教（里程→折线插值/四态门/表针）
    ├── metro_drive.yaml          # 第二十五册示教（手柄/ATP/移动闭塞/到站握手/假滚动，5 段真实站距）
    ├── ato_train.yaml            # 第二十七册示教（ATO 全自动：包络/精确停车/爬行补标/多站循环）
    ├── ui_kit_demo.yaml          # 第二十八册示教（矢量 UI：四状态按钮/弹窗/进度条换档）
    ├── math_lab.yaml             # 第三十册示教（N 皇后回溯/分数化简/埃氏筛，4 角色 298 块）
    ├── card_game.yaml            # 第三十一/三十三/三十五/三十六册示教（牌型/UNO/板子/竞选/警徽流/自爆/屠边/觉醒，1566 块）
    ├── music_band.yaml           # 第三十二册示教（简谱→乐器演奏/多声部，4 角色 112 块）
    ├── rhythm_game.yaml          # 第三十八册示教（BPM/谱面/四档判定/长按/结算，453 块）
    ├── rhythm_replicas.yaml      # 第三十九册示教（五模式复刻引擎/官谱换算/判定圈/双序列，1420 块）
    ├── shooter_replicas.yaml     # 第四十册示教（四模式射击引擎/伤害管线/圈/撤离/AI，706 块）
    ├── strategy_replicas.yaml    # 第四十一册示教（四模式策略引擎/兵线/塔仇恨/回合/经济/羁绊/音效/得分，986 块）
    ├── strategy_replicas.quality.json  # 第四十一册规格表（门禁 9/9 优秀）
    ├── 早期/专项示例：cat_chase / edu_demo / match3 / shooter / semantic_check /
    │   example_clones / example_cloud / example_lists / example_operators_sensing /
    │   example_pen_sound / example_procedures / example_with_bg（共 34 个 yaml）
    ├── multiplayer.yaml / 3d_demo.yaml / firstperson.yaml / board_gomoku.yaml  # 第十四~十七册示教
    ├── ref_minecraft3d.yaml      # ★ 完整可玩参考工程（第一人称体素光线投射：DDA 射线/碰撞/画笔渲染）
    └── output/                   # 产物 .sb3
```

### 维护积木规范

官方源码下载到 `../reference/scratch-sources/` 后，可随时重新抽取：

```bash
node scripts/extract_blocks_spec.js \
  --scratch-blocks ../reference/scratch-sources/scratch-blocks \
  --scratch-vm     ../reference/scratch-sources/scratch-vm \
  --aliases        references/blocks-aliases.json \
  --out            references/blocks-spec.json
python3 scripts/make_blocks_doc.py
```

脚本会交叉校验「scratch-vm 运行时支持的原语 100% 被收录」，有遗漏会以退出码 2 报警。
