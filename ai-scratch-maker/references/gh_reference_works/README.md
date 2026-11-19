# GitHub 高质量 Scratch 作品参考库

> 用途：给 AI 生成 Scratch 作品做「真作品」对照参考，而不是只看我们自己写的模板。
> 下载时间：2026-11-08
> 来源：GitHub 公开仓库（已用 `digest_sb3.py` / `decompile_sb3.py` 拆过结构）

## 〇、许可说明（分发前必读）

本目录里的 .sb3 分属两个上游仓库，**许可不同**，因此**只随仓库分发其中可再分发的部分**：

| 上游仓库 | 许可 | 本目录中的文件 | 是否随仓库分发 |
|---|---|---|---|
| `learning-game-development/learning-scratch-game-development` | **Unlicense**（公有领域奉献） | `Platformer` / `Fruit_Slicer` / `Brick-Breaker` / `Asteroid-Breaker` / `Basketball` / `Maze-Runner` / `Snaaaaaake` / `Rainbow-Lines` | ✅ 是 |
| `SilkRoad/Scratch` | **无许可证**（GitHub API `license=NONE`） | `001星星猎手` / `002小猫吃鱼` / `003迷宫型-追逐小鱼` / `004圆圈战争` / `004圆圈战争-2` / `005跳跃的猴子` / `006猴子吃水果` / `007扫帚上的厄运` | ❌ 否 |

无许可证 = 未授予复制与再分发权，故编号 `001`–`007` 的 8 个作品**不随本仓库分发**，
但可自行从 <https://github.com/SilkRoad/Scratch> 获取后放入本目录。

## 一、来源仓库

| 仓库 | 类型 | 质量定位 |
|---|---|---|
| `SilkRoad/Scratch` | 8 个中文游戏实例（带难度编号） | 入门→中级教学级 |
| `learning-game-development/learning-scratch-game-development` | 经典游戏合集（街机/平台/切水果等） | 教学级，但部分结构规范 |

> 注：搜索到的 `CreatorAcademyAu/50_Scratch_Games`（号称 50 个游戏）实际 404 不存在。
> `awesome-scratch-projects` 收录的 griffpatch 等**顶级作品**都在 scratch.mit.edu，**不在 GitHub 上以 .sb3 形式发布**——这部分由 `community-crawler/` 已覆盖的「Scratch 官方」源负责。

## 二、文件清单（本地共 16 个 .sb3，其中 8 个随仓库分发）

### SilkRoad/Scratch（中文，按难度编号）
- `001星星猎手.sb3` — 章鱼接星星（接物类，75 块/22 造型/14 音效）
- `002小猫吃鱼.sb3` — 小猫接鱼（接物类）
- `003迷宫型-追逐小鱼.sb3` — 迷宫追逐（283K）
- `004圆圈战争.sb3` / `004圆圈战争-2.sb3` — 圆圈战争（含改版）
- `005跳跃的猴子.sb3` — 跳跃接香蕉（含克隆+重力，80 块）
- `006猴子吃水果.sb3` — 猴子吃水果
- `007扫帚上的厄运.sb3` — 扫帚主题

### learning-game-development（经典游戏）
- `Platformer.sb3` — **★最有参考价值**：多帧走路动画（Cat 12 造型）+ 自制积木模块化（handle ground / set correct costume / walk）+ 重力物理。292 块/18 造型/5 音效。
- `Fruit_Slicer.sb3` — 切水果（对应我们 star_catch 类）
- `Brick-Breaker.sb3` — 打砖块（1.3M，最大）
- `Asteroid-Breaker.sb3` — 打小行星（1.1M）
- `Basketball.sb3` — 篮球
- `Maze-Runner.sb3` — 迷宫
- `Snaaaaaake.sb3` — 贪吃蛇
- `Rainbow-Lines.sb3` — 彩虹连线

## 三、关键结论（对照我们 skill 的现状）

1. **GitHub 上能直接下载的 .sb3 天花板是「教学示例」级**，普遍 75~130 块、全平铺、无广播/无状态机/无自制积木。
   - 例：`001星星猎手` 只有 75 块、无广播、无自制积木；而我们 `star_catch` 已有状态机+关卡+结算+手感（293 块）。**我们的模板已经比这些 GitHub 示例更复杂。**

2. **唯一真正可借鉴的技术**：`Platformer.sb3` 的**帧动画**做法——
   - 维护 `frame` 计数器 + `frames per costume`（每动作几帧）
   - 自制积木 `set correct costume` 按状态（站/走 8 帧循环/跳/落）切造型
   - 这比我们平台模板「靠改大小做拉伸」更接近真游戏的动画手感。
   - **但它要求美术是多造型精灵表（sprite sheet），我们当前 ImageGen 单图管线做不到**，这是我们的真实短板。

3. **真正的顶级作品（griffpatch 的物理引擎 / 3D / 平台跳跃）在 scratch.mit.edu，不在 GitHub**。想拿到「高质量」标杆，应走 `community-crawler` 的官方源拉取，而不是 GitHub。

## 四、怎么用这些文件

直接用 Scratch 3 编辑器 / TurboWarp 打开 `.sb3` 即可看内部积木。
想拆结构：`python scripts/digest_sb3.py <file>`（架构）或 `python scripts/decompile_sb3.py <file> --target <角色名>`（脚本）。
