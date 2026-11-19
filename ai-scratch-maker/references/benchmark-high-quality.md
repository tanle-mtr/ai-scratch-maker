# 高质量标杆（High-Quality Benchmark）

> 目标：把「顶级 Scratch 作品长什么样」量化成可对照的技术清单，指导本项目 skill
> 的 IR 特性与模板往哪里补齐。替代「实时拉 griffpatch 真·作品 .sb3」这一步——
> 因为本沙箱网络**访问不到 scratch.mit.edu**（直链 CDN 403、编辑器注入被屏蔽），
> 所以改以**可下载的本地标杆 + 公开技术清单**交付「标杆精神」。

---

## 1 · 网络约束与替代方案

- **不可达**：`scratch.mit.edu` 在本沙箱被网络策略挡住，无法用 `community-wscdn` 直链
  或编辑器「保存到电脑」下载 griffpatch 的真·作品源文件（详见 `community-crawler/README.md`
  的「小码王路线」同理受阻说明）。不要反复尝试这条路。
- **可下载的本地标杆**（已入库，直接可拆）：
  - `references/gh_reference_works/`（19 个 GitHub 开源 .sb3，**教学级**天花板，
    适合学结构与积木组织，不是 griffpatch 顶级水准）。
  - `examples/platformer.yaml` —— **本项目自己的多帧动画标杆**：玩家四帧
    （idle / walk1 / walk2 / jump）跑通 `animations:` 声明式帧动画（IR 特性见
    `ir-patterns.md` P9），是「会动的主角」的本地样板。
- **技术清单来源**（公开、可检索）：`CodeLabClub/awesome-scratch-projects` 策展清单 +
  griffpatch 的公开教程与引擎设计（Box2D 扩展、Platformer Tutorial v0.12、滚动背景教程）。
  这些给出了顶级作品**共用**的工程方法，不依赖下载源文件也能对齐。

---

## 2 · 顶级作品清单（griffpatch 代表作，来自 awesome-scratch-projects）

按「技术含量」挑代表作，作为我们努力的对标对象：

| 作品 | 技术看点 | 对我们最有价值的借鉴 |
|---|---|---|
| **Paper Minecraft v11.3** | 2D 沙盒、瓦片引擎、程序化生成、世界存档 | 瓦片地图数据结构、列表驱动关卡 |
| **Geometry Dash v1.5** | 节奏平台、精确计时、动态关卡 | 固定节拍帧驱动、判定窗口毫秒化（铁律27） |
| **Impulse 2D Physics Engine 1.3** | 完整 2D 物理（重力/碰撞/关节/力） | 速度积分 + 碰撞回退（我们的 P2 同思路） |
| **Super Mario Bros / Tower Defence / Bomberman** | 完整游戏循环、敌人 AI、波次 | 状态机（P1）、克隆生命周期（P6）、UI 规范 |
| **3D Laser Tag / Top Down 3D City** | 伪 3D 投影、分层渲染 | 相机 lerp（P5）、深度排序 |
| **Ball Pool / Ball Physics Playground** | 实时多体碰撞、弹性 | 碰撞收窄（P7）、克隆上限 300（铁律12） |
| **Massive Multiplayer Platformer** | 云变量同步多人、AI 对手 | 云变量上限约束、确定性逻辑 |
| **Fireworks (Particle Slow Motion)** | 粒子系统、慢动作 | 克隆粒子（P6）、缓动 |

> 一句话：griffpatch 级作品 = **自制积木模块化引擎 + 严谨物理/计时 + 相机与粒子
> + 完整游戏状态机 + 分层音效 + 规范 UI**。下面把这拆成 8 根技术支柱。

---

## 3 · 顶级作品共用技术栈（8 大支柱）

### 支柱 1 · 物理引擎（速度积分 + 碰撞回退）
- 存 `x 速度 / y 速度` 变量做欧拉积分，**不**瞬移；重力与加速度用加/减，摩擦/阻尼用**乘**（铁律5）。
- 碰撞分轴处理：`change x` 后若 `碰到` 就回退并把 x 速度清零；y 同理（含反弹系数）。
- 进阶：终端速度（限制下落上限）、土狼时间（离地后仍可跳几帧）、跳跃缓冲（落地前预输入）、
  可变跳跃高度（松键 `vy *= 0.4`）。
- **本项目已覆盖**：`ir-patterns.md` P2 物理积分循环 + `platformer.yaml` 全量落地
  （含土狼时间/跳跃缓冲/落地挤压）。铁律8（y+ 朝上重力取负）对齐。

### 支柱 2 · 自制积木模块化（"run without screen refresh"）
- 把物理、碰撞、生成敌人等抽成**自制积木**，勾选「不刷新屏幕运行」避免卡顿；
  参数化（friction / bounce / gravity）复用。
- 命名描述性、关注点分离（每个角色管一类事）。
- **本项目对应**：IR 无 `define` 语法时用「独立角色一次性脚本 + 广播调度」实现模块化
  （`ir-patterns.md` 末节）。可在未来 IR 加 `procedures`（待办）。

### 支柱 3 · 相机 Lerp 跟随（只动绘制坐标）
- 全局 `CAMERA X / CAMERA Y` + 每角色私有 `SCROLL X / SCROLL Y`；绘制位置 =
  `SCROLL - CAMERA`；相机用 lerp（`镜头x += (玩家x - 镜头x - 160) * 0.1`）平滑。
- 无限滚动靠 `mod` 把 CAMERA 值循环；视差层用不同滚动速度（远景慢、近景快）。
- **本项目已覆盖**：`ir-patterns.md` P5 相机 Lerp（只改绘制坐标、不动状态量，避免探针失准）。
  视差层为待补。

### 支柱 4 · 粒子拖尾（克隆 + 离屏即删）
- 火花/爆炸用克隆，速度私有、渐隐（GHOST 效果）、出屏或寿命到立即删克隆（铁律11/12）。
- 慢动作靠全局时间缩放。
- **本项目已覆盖**：`ir-patterns.md` P6 克隆生命周期 + P8 juice 的震屏/白闪。

### 支柱 5 · 状态机驱动（标题→游戏→暂停→结算）
- 单个 `游戏状态` 变量驱动一切；复位挂 `[重置]` 广播不挂绿旗（铁律6）；结算页有
  「再来一局」按钮（铁律7）。
- **本项目已覆盖**：`ir-patterns.md` P1 状态机主循环。

### 支柱 6 · 帧动画（多造型 + 状态机翻帧）
- 角色多造型（idle/walk/jump…），用 `状态` 变量 + 翻帧器按 `fps` 切造型；
  一角色多帧**必须同风格同描边**（否则观感撕裂）。
- **本项目已覆盖（新）**：`expand_animations` 声明式 `animations:` + `ir-patterns.md` P9
  + `platformer.yaml` 四帧样板 + `scripts/slice_sheet.py` 精灵表切片。这是本次 A/B/C
  落地里最直接对标「会动主角」的成果。

### 支柱 7 · 音效四层（ui / fx / ev / amb 响度 + 渐变）
- 四层响度（ui≈-18 / fx≈-9 / ev≈-3 / amb≈-15 dBFS，层间 6–9 dB）、UI 音效 ≤0.25s、
  首尾归零、DC<0.01、音高方向=语义；UI 音效禁「播放直到结束」。
- **本项目已覆盖**：`ir-patterns.md` P4 + 铁律18 + `gen_sfx_kit.py`(22) / `gen_audio.py`。

### 支柱 8 · UI 规范（窗口圆角 + 矢量五层 + 四态按钮）
- 窗口圆角 + 大窗、UI 矢量五层体积感（投影→外描边→渐变→顶高光→底内阴）、
  按钮四态换造型不缩放、pressed 渐变反转、§198 十八色板合规。
- **本项目已覆盖**：铁律13/14/15/16/17 + `make_ui_assets.py` + `quality_gate.py` C 层观感门禁
  + `ir-patterns.md` P3 UI 按钮。

---

## 4 · 能力对照表（已覆盖 vs 待补）

| 支柱 | 本项目 skill 状态 | 缺口 |
|---|---|---|
| 物理引擎 | ✅ P2 + platformer 全量 | 斜坡检测（slope）待补 |
| 自制积木模块化 | ⚠️ 用广播+角色模拟 | 原生 `procedures` 语法（待办） |
| 相机 lerp | ✅ P5 | 视差层、缩放相机待补 |
| 粒子拖尾 | ✅ P6 + P8 juice | 慢动作时间缩放待补 |
| 状态机 | ✅ P1 | — |
| 帧动画 | ✅ P9（新） | 骨骼/程序化补间待补 |
| 音效分层 | ✅ P4 + 铁律18 | — |
| UI 规范 | ✅ 铁律13–17 + C 层门禁 | — |

**结论**：8 大支柱里本项目已实质覆盖 7 根（帧动画是本次新补的最关键一根）；
主要剩余缺口是「原生自制积木语法」「视差/缩放相机」「斜坡物理」「慢动作」——均为
增强项，不影响「达到教学级以上的观感与手感」这一交付目标。

---

## 5 · 行动建议

1. **以 `platformer.yaml` 为动画样板**：新作品主角默认四帧起，套 P9 `animations:` 即可，
   不要退回单造型。
2. **拆 `gh_reference_works/` 学结构**：用 `scripts/digest_sb3.py` 看广播表/自制积木表，
   用 `scripts/decompile_sb3.py --all` 看数据流，对齐支柱 1/2/5 的组织方式。
3. **待办（不阻塞当前交付）**：
   - 给 IR 加 `procedures`（自制积木）原生语法，取代广播模拟。
   - `expand_animations` 扩到支持「程序化补间」（两帧间插值）与「骨骼父子」。
   - 相机扩视差层 + 缩放（zoom）变量。
4. **网络恢复后**：若沙箱能访问 scratch.mit.edu，再补一条「拉 griffpatch 真·作品做
   字节级对照」的路线（届时改 `community-crawler/` 加 Scratch 官方源）。

---

> 参考来源（公开可检索，未下载源文件）：
> - CodeLabClub/awesome-scratch-projects（griffpatch 代表作策展清单）
> - griffpatch Platformer Tutorial v0.12（重力/斜坡/墙跳/命中箱）
> - griffpatch 滚动背景教程（CAMERA X/Y + SCROLL X/Y + mod 无限循环 + 视差）
> - griffpatch Box2D 物理扩展（2D 物理引擎设计）
> - ItsMyBot《Physics-Based Games in Scratch》（土狼时间/跳跃缓冲/终端速度实现）
