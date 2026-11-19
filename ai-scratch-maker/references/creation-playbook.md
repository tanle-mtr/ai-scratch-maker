# 创作方法论（Creation Playbook）· 从一句话需求到高质量 .sb3

> 本文回答一个问题：**AI 怎样才能「创作」出一件高质量 Scratch 作品，而不只是能「验收」别人写的？**
>
> 背景：本 skill 早期重兵在验收侧（八层校验 + 9 条铁律 + 质量门禁 + 深网），能拦住废品；
> 但「从零做出一件像样的成品」长期是短板。本方法轮是把**实战踩过的坑**蒸馏成可复用的
> 创作步骤与速查表。配套范例：`examples/whack_a_mole.yaml`（打地鼠，动作/计时类，端到端跑通全部 8 层 +
> 深网 + 9 条铁律 + 质量门禁 9/9 优秀）、`examples/platformer.yaml`（平台跳跃，**物理/手感类**，
> 已增强 Jump Buffering / 可变跳跃 / 挤压拉伸 / 震屏）、`examples/fruit_basket.yaml`（接水果，计分/命类）。
> 三类题材覆盖「动作、物理、计分」，可任选其一当模板抄。

---

## 0. 核心心法（先读这段，少走 2 小时弯路）

1. **验收侧已经很强，创作侧才是瓶颈。** 不要一上来就写 IR——先定「这件作品要展示哪些质量维度」。
2. **题材要能同时展示「玩法完整度」和「观感质量」**。打地鼠这类机制天然具备：倒计时胜负、
   命中顿帧 + 震屏、连击、关卡递进、结算重玩（玩法）；缓动升降、粒子爆裂、矢量体积感（观感）。
3. **资产策略决定观感下限。** 手绘 SVG 必须过 §198 调色板 + 五层体积感 + 无禁用标签；
   数字/面板用 `make_ui_assets.py`；音效复用 `examples/assets/audio/*`（四层响度）；BGM 用
   `gen_audio.py bgm --mood calm`。**AI 自己生成素材才是端到端的正路**，别指望外部素材。
4. **IR 语法错会直接让构建失败。** 真正卡住构建的从来不是「创意」，而是 `if_else` 写法、
   裸 `forever`、错了的 `rotationStyle` 值。把这些写进肌肉记忆（见第 5 节速查表）。
5. **构建失败先抓「第一个报错」。** 构建器遇到第一个错误就退出，修完再跑会暴露下一个——
   这是正常的「逐错递减」过程，不是连环崩溃。

---

## 1. 六步创作循环（与 SKILL.md / golden-path.md 对齐）

| 步 | 动作 | 关键命令 / 产物 | 本范例（whack_a_mole） |
|---|---|---|---|
| 1 | 定规格 | `quality_gate.py --init --profile game --out <x>.quality.json` | 游戏档，品类 game |
| 2 | 写 IR | `<x>.yaml`，每脚本以帽子开头 + `comment:` | 430 行，22 目标，525 积木 |
| 3 | 生成素材 | SVG 手绘 / `make_ui_assets.py` / `gen_audio.py` / 复用 `examples/assets/audio/*` | 5 SVG + 17 PNG + 1 BGM |
| 4 | 编译 | `build_sb3.py --ir <x>.yaml --out <x>.sb3 --workdir /tmp/w` | `examples/output/whack_a_mole.sb3` |
| 5 | 校验循环 | L1–L8 + 铁律 + 质量门禁，逐错修复 | 全过，9/9 优秀 |
| 6 | 沉淀 | 写深网探针 + 把作品列为范例 | `whack_a_mole_behavior_check.mjs` |

> 详细命令模板见 `references/golden-path.md`；本文只补「创作侧」独有的判断与坑。

---

## 2. 第 1 步：题材与机制设计（决定上限）

选题材时自问三件事，全中才是好题材：

- **有没有清晰的胜负/目标？**（倒计时、生命、得分阈值）——直接决定铁律7 结算页 + 质量门禁 B 层「胜负条件」。
- **有没有「手感」可打磨的空间？**（命中反馈、缓动、粒子、震屏）——决定观感质量分（§9/§11/§231）。
- **有没有「重玩价值」？**（随机、关卡递进、计分排行）——决定质量门禁 B 层「重玩价值」。

打地鼠为什么好：
- 胜负：60 秒倒计时，归零结算（铁律7 天然成立）。
- 手感：地鼠缓动冒头/缩回（`当前y += (目标y-当前y)*0.3` 阻尼）、命中顿帧（全局冻结几帧）、
  震屏偏移、火花粒子（私有 vx/vy + `*0.92` 阻尼 + GHOST 渐隐）。
- 重玩：连击封顶、分数跨阈值升关、最高分持久（刷新到舞台变量，回标题不丢）。

---

## 3. 第 3 步：资产策略（决定观感下限）

### 3.1 手绘 SVG（角色/场景/背景）——必须过三关
- **§198 调色板**：只用黄/绿/青绿/灰的指定 6 位 HEX。注意 `#C6FF2A`（色相 ~76°，落在黄(62)与
  绿(84)间隙）会被 `check_ui_assets.py` 判违规——改 `#8CE243`。
- **五层体积感**（铁律11）：投影 → 外描边 → 渐变 → 顶高光 → 底内阴，顺序不可换。
- **无禁用标签**（铁律17）：SVG 里禁止 `text / filter / mask / clipPath / pattern / image / font-family`。
  所有文字（数字、标签、署名）都走 `digit_display` / `chat_box` 伪积木或 PNG，绝不写进 SVG。
- 角色 SVG 无 `btn_/icon_/panel_/bar_/ctrl_/decor_` 前缀时，只须保 `viewBox` + 合规色 + 无禁用标签。

### 3.2 复用生成器与现成资产
- 数字精灵：`make_ui_assets.py digits --color #FFFFFF` → `d0.png..d9.png`（给 `digit_display` 用）。
- 标题/面板/按钮：`make_ui_assets.py titlebg/world/panel/...`（或自己画 PNG）。
- 音效：直接复用 `examples/assets/audio/*`（四层响度 ui-18/fx-9/ev-3/amb-15 dBFS，首尾归零，
  ui≤0.25s）。需要时 `gen_audio.py sfx --name coin/pop/...` 现造。
- BGM：`gen_audio.py bgm --mood calm --bars 4 --out examples/assets/audio/bgm_calm.wav`
  （calm/happy/chase/spooky/victory/defeat/explore 七种情绪可选；循环无缝）。
- 第三方社区素材仅供学习参考，对外分发/商用须回溯原作者授权（见 `community-asset-pack.md`）。

> 资产相对 **IR 文件所在目录** 解析。IR 写在 `examples/`，资产就放 `examples/assets/<作品>/`。

---

## 4. 第 4 步：构建与第 5 步：校验循环

构建命令（**必须 `--workdir`，否则留 `_proj` 临时目录**）：
```bash
python scripts/build_sb3.py --ir examples/whack_a_mole.yaml \
  --out examples/output/whack_a_mole.sb3 --workdir /tmp/whack_work
```
成功后输出形如：`OK 生成 .../whack_a_mole.sb3 | targets=22 blocks=525 extensions=[]`。

八层 + 铁律 + 门禁一条命令（全量，含 23 作品行为回归，约 12+ 分钟）：
```bash
bash scripts/verify_project.sh
```
只验单个作品可手动跑（见 golden-path.md 第 6 节）。本范例单验结果：
`L1✓ L2✓ L3✓ L4✓ L5(SMOKE_OK)✓ L6(WHACK_LOGIC_OK)✓ L7(SEMANTIC_OK)✓ L8(9/9 优秀)✓`，
铁律 1/2/3/6/7/11/17/18 全 ✓（铁律19 障碍碰撞 N/A：打地鼠无墙类障碍）。

---

## 5. IR 编写速查表（最常卡构建的坑）

| 坑 | 错法 | 正解 |
|---|---|---|
| if/else | 写 `if:` 块后再另起一行 `- else:` | 用 **`if_else:`**，把 `cond/do/else` 作为同一块的键 |
| 裸循环 | 顶层直接 `- forever:` / `- repeat:` | 必须挂在帽子下：`when_green_flag_clicked:` → `forever:` |
| 旋转样式 | `rotationStyle: all` | 只能是 `all around` / `don't rotate` / `left-right` |
| 未知积木 | 把 `else` 当独立积木 | `else` 只作 `if_else` 的子键，不是积木 |
| 阻尼/衰减 | 用 `减` 近似摩擦 | 用**乘**：`x += (目标-x)*0.3`；粒子 `vx *= 0.92`（铁律5） |
| 坐标/朝向 | 依赖 `glide_secs_to_xy` / `mouse_down` | scratch-vm 不支持；用 `goto_xy` + `鼠标x/鼠标y` 报告符替代 |
| 比较/逻辑 | `>=` / `<=` / `atan2` / `min` / `max` | 不支持；用 `not less_than` / `not greater_than` / 嵌套 `and`/`or` |
| 菜单/参数 | 写中文菜单值 | `stop→option:`、`touching→object:`、`create_clone_of→clone:` 用英文枚举 |
| 列表 | 当成普通变量 | 列表是「存数组的变量」；IR 里按变量读，1 基索引 |
| 无参积木 | `show:` | 必须 `{ show: null }`（积木恒为 `{名:值}` 字典） |
| 嵌套 if | `嵌套IF的do里放CLONE` | 漏编译；拆成平级单分支 |

构建报 `未知积木名 'else'（你是不是想写：...）` 或 `脚本必须以帽子积木开头` 时，按上表修。
`[警告] 积木 if 带了 else 分支，已自动升级` 无害，但建议顺手改成 `if_else` 保持整洁。

---

## 6. 第 6 步：沉淀范例与深网（让作品「可当模板抄」）

交付级作品应带一个 **深网行为探针**（`*_behavior_check.mjs`），在 scratch-vm 里断言关键状态机：
- 绿旗 → 标题态（游戏状态=0）
- 开始游戏 → 进入游戏态且分数/时间/关卡干净复位
- 再来一局（重复开始）→ 仍完全复位（状态机复位逻辑核心）
- 关键角色存在（缺一则跑不起来）
- 结束态可达（广播 时间到 → 游戏状态=2，并刷新最高分）
- 回标题 → 游戏状态=0（铁律7 闭环）

然后在 `scripts/regress_behavior.sh` 的 `MAP` / `KEYS` 注册该作品，使其进入全量回归。
本范例探针：`scripts/whack_a_mole_behavior_check.mjs`（令牌 `WHACK_LOGIC_OK`）。

---

## 7. 交付前自检清单（质量维度）

- [ ] **玩法完整度**：玩家可操控？有胜负/目标？有重玩价值？（质量门禁 B 层三项必有）
- [ ] **资产密度**：造型≥20、音效≥8、角色≥4、场景≥2、积木≥150、体积合理（质量门禁 A 层）
- [ ] **铁律**：署名 CC BY-SA（铁律3）；结算页有返回/再来一局（铁律7）；复位挂广播不挂绿旗（铁律6）；
      克隆体私有 `is_clone` 挡本体事件帽（铁律11）；SVG 无禁用标签（铁律17）；颜色 6 位 HEX（铁律18）
- [ ] **观感**：缓动/顿帧/震屏衰减有体现；矢量五层体积感；配色合规（质量门禁 C 层观感分）
- [ ] **八层全过 + 深网 + 铁律全过 + 质量门禁 9/9**

---

## 8. 上网萃取的高质量秘诀（Game Juice / 工业级手感）

> 2026-11-07 检索 Scratch 高质量创作（Scratch 官方论坛、TrueSight《拒绝玩具感/砖头感》系列、
> CSDN《用 Scratch 复刻马里奥》、Papai《How To Make A Platformer》）后，把社区公认的「手感秘诀」
> 与本项目铁律做了对照。**结论：社区强调的 Game Juice 与本项目 铁律15/16 高度同源，本项目已用铁律
> 把它们制度化；下面补几条社区特有、本项目此前没显式写进范例的实战招式。**

### 8.1 社区共识 → 本项目映射
| 社区秘诀 | 要点 | 对应铁律 / 落地 |
|---|---|---|
| **别用「当按下 X 键」帽子** | 该帽子带操作系统按键重复延迟（按住先动一下、停一拍再连发），平台游戏是致命伤 | 改用 `when_green_flag_clicked` + `forever` + `if key_pressed:` 轮询（每帧检测，零延迟）。本项目 cat_mouse/platformer 已用 `key_pressed` 报告符轮询 |
| **速度向量而非坐标直移** | 用 `vx/vy` 变量累加重力/摩擦，别写「将 y 改变 10」 | 铁律5（阻尼用乘）、铁律8（y+ 朝上重力取负）；platformer 已有 `vy -= 重力` |
| **土狼时间 Coyote Time** | 踏空后 0.1s 内仍允许跳，宽容操作误差 | platformer 已有 `离地计时<4`（≈0.08s）实现 |
| **跳跃缓冲 Jump Buffering** | 落地前 0.1s 按下跳跃，落地瞬间立即起跳 | **本次新增**：platformer 加 `跳缓冲` 跨帧标志（按跳置 6 帧，落地前有效） |
| **可变跳跃高度 Variable Jump** | 松键早则跳得矮（上升中把 vy 砍掉一截），长按跳满 | **本次新增**：platformer 中 `prev_jump` 检测松键瞬间，`vy *= 0.4` |
| **挤压与拉伸 Squash & Stretch** | 起跳拉长、落地压扁，用 size 的 x/y 扰动告诉玩家「物理在生效」 | **本次新增**：platformer 用 `拉伸` 变量（跳 130 / 落 70 / 回 100 缓动）+ `set_size` |
| **屏幕抖动 Screen Shake** | 重击/落地瞬间把所有对象随机偏移几像素 | **本次新增**：platformer 用 `震屏` 变量，渲染时给玩家坐标加 `random(-震屏,震屏)`，每帧 `*0.7` 衰减 |
| **动态相机用 Lerp** | 镜头别贴死角色，用 `镜头 += (目标-镜头)*0.1` 滞后跟随 | 铁律15。注意：会动 `镜头x` 会破坏既有「镜头==玩家-半屏」严格探针，启用须同步放宽探针容差 |
| **碰撞微调回退** | 撞墙别瞬移回原位（易卡死），用极小步长回退到不碰 | platformer 已用「重叠则 `玩家x -= vx`」回退一格，等价于微调回退 |
| **300 克隆上限** | 别给每个金币/敌人建克隆，用滚动引擎只渲染屏内 | 铁律12（克隆上限 300 静默丢）；platformer 用列表坐标 + 笔绘，几乎零克隆 |
| **小反馈大不同** | 受击闪一下、吃币弹个分数，体验立刻完整 | 铁律15（顿帧/震屏）+ 铁律12 粒子；whack_a_mole 的火花粒子即此 |
| **统一调色板** | 全作只用一套有限色，一致性即「完成感」 | 铁律13/§198 十八色；`check_ui_assets.py` 强制 |
| **增量构建** | 先动起来→加对象→加计分→最后打磨，逐个验证 | 本项目六步循环同构；深网探针就是「逐个验证」的自动化 |

### 8.2 本次给 platformer 落地的四招（已在 `examples/platformer.yaml` 实现）
1. **Jump Buffering**：`跳缓冲` 跨帧标志。按跳即置 6 帧；落地/土狼窗口内只要 `跳缓冲>0` 就起跳；起跳即清零。消除「差一帧没跳上」的挫败。
2. **Variable Jump**：`prev_jump` 记录上帧按键；松键瞬间且仍在上升（`vy>4`）则 `vy *= 0.4`，轻点矮跳、长按满跳。
3. **Squash & Stretch**：`拉伸` 变量，跳起设 130、落地设 70、之后每帧 `拉伸 += (100-拉伸)*0.3` 缓回 100，`set_size` 作用于角色 SVG（已把玩家从白点换成 `player.svg` 萌物，拉伸可见）。
4. **Screen Shake**：`震屏` 变量，落地置 2，渲染时 `x/y += random(-震屏,震屏)`，每帧 `*0.7` 衰减；**只偏移玩家绘制坐标、不动 `镜头x`**，故既有严格探针 `镜头x==玩家-半屏` 仍然成立。

> 这四类全部是「不影响物理状态量、只动观感层」的探针安全增强——这是给既有范例做手感增强的黄金准则：
> **改观感别动会被探针断言的状态量**（如 `镜头x`、`玩家x/y`、`金币数`）。

### 8.3 本轮新增检索的「评审 / 可访问性 / 静态检查」维度

> 2026-11-07 第二轮检索：Scratch 赛事评分标准（MASTERCO/Scratch Olympiad/青少年图形化编程赛事）、
> Game Accessibility Guidelines、LitterBox（Scratch 静态分析，74,830 公开作品上 87% 精度）、
> Harvard CS50 Scratch 评分、kidscoding8《如何做出优质作品》。**这些与本项目的铁律/八层同源互补，
> 已沉淀进下方配套资产，并在验收侧新增三个脚本。**

| 外部维度 | 要点 | 本项目落地 |
|---|---|---|
| **赛事评分四维度** | 创意30%·玩法30%（直觉操作/参与感）·设计20%（观感/音效/主题融合）·打磨20%（无 bug/清晰指引/完整） | 映射到 `self-review.md` 第 1/4/5/9 条；玩法完整度已是质量门禁 B 层 |
| **可访问性四痛点** | 最常被抱怨＝按键重映射/文字尺寸/色盲/字幕；色盲以红绿为主→用蓝黄组合，**绝不只靠颜色区分信息**（配形状/图案/标签）；文字大字号+强描边+阴影；信息不只靠声音；避免高频闪烁 | `self-review.md` §6（可访问性）+ **新脚本 `check_a11y.py`** |
| **静态臭味 LitterBox** | Long Script / Duplicated Script / Busy Waiting（循环内极小 `wait`）/ Missing Termination / Call Without Definition / Missing Resource / Comparing Literals | `failure-modes.md` §C + **新脚本 `check_perf_budget.py`** |
| **难度曲线三问** | 难度适中（可经计算设数值：敌机血量、炸弹间隔）、有重玩价值（随机/计分/递进），避免「必败」或「白给」 | `self-review.md` §3 |
| **Clean-as-you-code** | 质量门禁即 CI 门禁，新作品合并前必过静态检查 | 本项目 `verify_project.sh` 已是；新脚本接进阶段 4/5（见 §10） |

### 8.4 配套资产与工具（本轮新增，纯新增、不改动既有管线）

- `references/ir-patterns.md` —— 7 个可抄 IR 模板（状态机主循环 / 物理积分 / UI 按钮 / 音频四层 / 相机 Lerp / 克隆生命周期 / 碰撞收窄）。
- `references/self-review.md` —— 交付前 9 类软性核查清单（开场引导 / 边界稳定 / 难度平衡 / 玩法完整度 / 观感手感 / **可访问性** / 音效 / 架构 / 合规发布）。
- `references/genre-quickref.md` —— 题材速查卡（按手册 § 给「必看章节 + 必须有 + 必避坑」，覆盖平台跳跃/音游/射击/解谜/叙事/桌游/模拟/联机/UI/声音/数学）。
- `references/failure-modes.md` —— 易错点 → 正确写法速查（IR 语法 / 铁律 / LitterBox 静态臭味 / 验收侧已知误报）。
- `scripts/check_perf_budget.py` —— 性能预算静态嗅探（Long Script / Busy Waiting / 克隆风暴 / 广播风暴），默认 advisory，`--strict` 可接 CI。
- `scripts/check_a11y.py` —— 可访问性启发式（色盲对 / SVG `<text>` / 可见状态通道 / 闪烁），默认 advisory。
- `scripts/playtest_bot.mjs` —— 自动化试玩活性探针（真跑 scratch-vm，断言不崩溃 + 脚本在运行；**胜利态断言仍由各作品 `*_behavior_check.mjs` 负责**，本脚本只证「活着」）。

> 用法：写 IR 前先翻 `ir-patterns.md` 套骨架 + `genre-quickref.md` 找对应 §；写完后逐条过 `self-review.md`；
> 交付前除八层+铁律+门禁外，再跑 `check_perf_budget.py` / `check_a11y.py` / `playtest_bot.mjs` 三件套做加固。

---

## 9. 三个端到端范例对照

| 维度 | `fruit_basket.yaml`（接水果） | `whack_a_mole.yaml`（打地鼠） | `platformer.yaml`（平台跳跃） |
|---|---|---|---|
| 题材类 | 计分/命 | 动作/计时 | **物理/手感** |
| 角色数 | 9 | 21（含数字/标签/按钮克隆） | 4（玩家/地面/金币/舞台）+ 笔绘 |
| 积木数 | 244 | 525 | ~900 |
| 核心机制 | 接落体计分、漏接扣命 | 倒计时打地鼠、连击、升关 | 速度向量物理、土狼时间、跳跃缓冲、可变跳 |
| 手感亮点 | 物理下落、命中判定 | 缓动升降、顿帧、震屏、粒子 | 可变跳跃、挤压拉伸、震屏、相机跟随 |
| 深网探针 | `fruit_basket_behavior_check.mjs` | `whack_a_mole_behavior_check.mjs` | `platformer_behavior_check.mjs` |
| 质量门禁 | 9/9 优秀 | 9/9 优秀 | 物理回归 PASS（demo 档，未挂 game 门禁） |

三者分别覆盖「计分、动作、物理」三类题材，都跑通「设计→IR→素材→编译→八层→门禁→深网」全链路，
可任选其一当模板抄。物理类（platformer）最适合演示 铁律15/16 的「手感增强」如何落地。
