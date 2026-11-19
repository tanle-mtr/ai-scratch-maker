# 玩法设计进阶（第三册：§43–§50）

> 来源：Scratch Wiki《Turn-Based RPG》《Raycaster》《Object Attraction》、scratch-discuss
> 节奏游戏与 AI 讨论帖、Kids Coding Tutor（开始/结束/暂停菜单三件套）、
> Advaspire 教程（L32 菜单与最佳分）、jrcode 等教学站、
> juniorcoderz（宝可梦式对战、敌人 AI）、TrueSight（AI 决策修复指南）、
> kidtech（Scratch RPG 回合制）、iD Tech（切换背景）、Alura（重力）、
> EducaWeb（重力与弹跳物理）、moegirl OverRapid（节奏判定窗口表）等公开资料。
>
> 本册补齐「玩法层面」的系统：**战斗、场景、菜单、节奏、AI 决策、视线、吸引力、成长**。
> 每节都给出本 skill 的 IR 写法（能直接生成 sb3 的标 ✅）。

## 速查表

| 想做什么 | 章节 |
|---|---|
| 打回合制的战斗（伤害公式、属性克制、状态异常） | §43 回合制战斗系统 |
| 换场景、传送门、跨场景带数据 | §44 场景管理与跨场景数据 |
| 开始/暂停/重试/设置/选关按钮 | §45 菜单系统与暂停 |
| 打节奏游戏（节拍、判定窗口、连击） | §46 节奏游戏 |
| 敌人会思考、听觉、搜索、协作 | §47 敌人 AI 决策进阶 |
| 敌人能看见你吗（墙体遮挡视线） | §48 射线检测与视线 |
| 磁力吸取、引力、重力弹跳 | §49 吸引力与物理效果 |
| 升级、装备、技能树、随机词条 | §50 成长与装备系统 |

---

## 43. 回合制战斗系统

### 43.1 属性变量的命名规范（社区做法）

Scratch Wiki《Turn-Based RPG》用**前缀**把变量分成三组，一眼就知道是谁的：

| 前缀 | 归属 | 例子 |
|---|---|---|
| `C_` | 角色（玩家） | `C_Atk` `C_Def` `C_MaxHP` `C_HP` `C_MaxMP` `C_MP` `C_MGAtk` `C_MGDef` |
| `C_Wep_` | 玩家的武器 | `C_Wep_Atk`（固定加成） `C_Wep_P`（随机加成上限） |
| `E_` | 敌人 | `E_Atk` `E_Def` `E_MaxHP` `E_HP` |

**为什么用前缀而不是中文名**：以后要做多角色（比如 3 个可操作角色）时，
`C1_HP` `C2_HP` `C3_HP` 比三个都叫 `HP` 好维护太多。

⚠️ **所有属性变量都放舞台（全局）**，不要放角色里 —— 战斗逻辑写在舞台上，
需要读写双方的属性。

### 43.2 伤害公式

```
玩家近战伤害 = (C_Atk + C_Wep_Atk + 随机(0..C_Wep_P)) - E_Def
玩家魔法伤害 = (C_MGAtk + 技能强度) - E_MGDef
敌人近战伤害 = E_Atk - C_Def
```

⚠️ **必须有「最低伤害保底」**：伤害算出来是负数时钳到 **1**。
否则高防角色打高防角色永远是 0 伤害 → 战斗永远打不完 → 玩家卡死。
社区做法（juniorcoderz 的宝可梦式对战）：

```yaml
# rawDamage 先算，负数则改为 1
- set_variable: { var: rawDamage, value: { subtract: [ {var: 攻击力}, {var: 对方防御} ] } }
- if: { cond: { less_than: { a: {var: rawDamage}, b: 1 } }, do: [ { set_variable: { var: rawDamage, value: 1 } } ] }
```

### 43.3 属性克制（查表法）

不要写 `if 火克水 then ... else if ...` 的长链 —— 加一个属性就要改一整条链。
**用「独立的一串 if」**：每个 if 都独立判断，命中就设倍率，最后统一算。

```yaml
# typeMod 初始 1（中性），命中克制则改为 2，命中被克则改为 0.5
- set_variable: { var: typeMod, value: 1 }
- if: { cond: { equals: { a: {var: 攻击方属性}, b: "火" } }, do: [ { if: { cond: { equals: { a: {var: 防守方属性}, b: "水" } }, do: [ { set_variable: { var: typeMod, value: 2 } } ] } } ] }
- if: { cond: { equals: { a: {var: 攻击方属性}, b: "火" } }, do: [ { if: { cond: { equals: { a: {var: 防守方属性}, b: "草" } }, do: [ { set_variable: { var: typeMod, value: 0.5 } } ] } } ] }
```

关键：**每个 `if` 独立**（不是 elseif），所以加属性只需再加一个 if，
不会动到已有的判断。

### 43.4 回合流程状态机

用 `battle_state` 变量控制「现在该谁动」：

| 值 | 含义 |
|---|---|
| 0 | 战斗结束 |
| 1 | 等待玩家选择行动 |
| 2 | 播放玩家攻击动画 |
| 3 | 敌人选择并执行行动 |
| 4 | 播放敌人攻击动画 |

```yaml
# 玩家按 A 键攻击
- - when_key_pressed: { key: a }
  - if:
      cond: { equals: { a: {var: battle_state}, b: 1 } }
      do:
        - set_variable: { var: battle_state, value: 2 }
        - set_variable: { var: rawDamage, value: { subtract: [ {var: C_Atk}, {var: E_Def} ] } }
        - if: { cond: { less_than: { a: {var: rawDamage}, b: 1 } }, do: [ { set_variable: { var: rawDamage, value: 1 } } ] }
        - change_variable: { var: E_HP, by: { multiply: [ {var: rawDamage}, -1 ] } }
        - broadcast: 更新血条
        - if: { cond: { less_than: { a: {var: E_HP}, b: 1 } }, do: [ { set_variable: { var: battle_state, value: 0 } } ] }
```

### 43.5 状态异常（中毒/灼烧/眩晕）

**用一个列表存「状态名 + 剩余回合」**，成对存放：

```yaml
# 列表「异常状态」：第 1 项 = 状态名，第 2 项 = 剩余回合，第 3 项 = 下一个状态名……
- add_to_list: { item: "中毒", list: 异常状态 }
- add_to_list: { item: 3, list: 异常状态 }
```

每回合结算：对列表里的每个状态，扣血（中毒/灼烧）或跳过行动（眩晕），
然后剩余回合 -1，到 0 就移除（用 `item_num_of_list` 找位置 → `delete_of_list` 删两项）。

⚠️ **不要用 4 个布尔变量**（中毒中/灼烧中/眩晕中/冰冻中）—— 组合会爆炸，
而且「剩余回合」没地方放。

### 43.6 技能冷却

```
技能冷却 = 3
使用技能时：技能冷却 = 3
每回合：if 技能冷却 > 0 then 技能冷却 = 技能冷却 - 1
能不能用：if 技能冷却 = 0 then 可用
```

冷却要**每回合减 1**，不是每帧减 1 —— 回合制里按帧算冷却毫无意义。

### 43.7 战斗与探索的切换

碰到敌人 → 切到战斗背景 → 广播「进入战斗」→ 战斗结束后广播「战斗结束」→
切回探索背景并把角色坐标放回原位。

⚠️ **战斗场景要用不同的背景**，不要在探索背景上弹个对话框 ——
玩家会看不清战况。社区做法是「切背景 + 隐藏探索角色 + 显示战斗角色」。

### ⚠️ 坑

- **自定义积木没有返回值**！Scratch 3 的自定义积木**不能 return**。
  所以伤害公式要么写在舞台上（用全局变量），要么用自定义积木 + 全局变量当返回值
  （积木里 `set [结果] to ...`，调用方再读 `结果`）。这是 Scratch 的硬限制，
  很多从 Python/JS 转过来的人第一次都会栽。
- **属性变量必须初始化到 Max 值**：绿旗时 `C_HP = C_MaxHP`、`C_MP = C_MaxMP`，
  否则第一次进战斗血是 0。
- **动画期间要锁输入**：按 A 触发的攻击动画有 1 秒，这 1 秒内再按 A 会连击两次。
  用 `battle_state` 挡住（只有 state=1 才接受输入）。

---

## 44. 场景管理与跨场景数据

### 44.1 切背景的三种积木

| 积木 | IR | 用途 |
|---|---|---|
| 切换背景到 X | `{ switch_backdrop: { backdrop: 名称 } }` | 直接跳到指定背景 |
| 下一个背景 | `{ next_backdrop: null }` | 顺序往下走（章节切换） |
| 切换背景到 X 并等待 | `{ switch_backdrop_and_wait: { backdrop: 名称 } }` | 等背景切换完（带画笔/造型变化时） |

配合 `当背景切换到 X` 这个帽子：

```yaml
- - when_backdrop_switches_to: { backdrop: 战斗场景 }
  - broadcast: 进入战斗
- - when_backdrop_switches_to: { backdrop: 探索场景 }
  - broadcast: 回到探索
```

**「当背景切换到」是比广播更好的场景钩子** —— 它自动触发，
不会出现「广播名字拼错 → 静默不响应」的问题。

### 44.2 传送门（无缝走图）

两张背景上下相接，玩家走到边缘就切背景并换位置：

```yaml
# 边界线角色
- - when_receive:
      message: 传送向下
  - switch_backdrop: { backdrop: 区域2 }
  - broadcast: 玩家落到区域2
# 玩家角色
- - when_receive:
      message: 玩家落到区域2
  - goto_xy: { x: 0, y: 120 }
```

⚠️ **切换背景后要重新定位角色**：切背景只换背景图，角色坐标不变 →
玩家会出现在错误的位置（iD Tech 的教程就专门讲这一步）。

⚠️ **要判断当前是哪个场景再传送**，否则玩家站在边界上会反复触发：

```yaml
- if: { cond: { equals: { a: { backdrop_name: null }, b: "区域1" } }, do: [ ... ] }
```

### 44.3 跨场景带数据

| 数据类型 | 怎么带过去 |
|---|---|
| 金币、分数、道具 | **舞台全局变量**（切背景不清空） |
| 当前关卡号、玩家坐标 | 全局变量 |
| 场景专属配置 | **列表当数据表**，用场景号做索引 |
| 「我刚从哪个场景来」 | 全局变量存 `来自场景` |

⚠️ **角色私有变量不会因为切背景被清空**，但也不会自动刷新。
如果你希望「回到探索场景时血量回满」，要**显式在「当背景切换到 探索场景」里重置**，
不能指望它自动重置。

### 44.4 场景配置表

一个场景要配的东西多（背景名、敌人数量、道具、目标分数…）时，
**用一条列表存「场景号 → 配置」**，加场景只加数据不改代码：

```yaml
# 列表「场景配置」：每关 5 项 [背景名, 敌人数, 道具数, 目标分, 说明]
- add_to_list: { item: "森林", list: 场景配置 }
- add_to_list: { item: 3, list: 场景配置 }
- add_to_list: { item: 2, list: 场景配置 }
- add_to_list: { item: 100, list: 场景配置 }
- add_to_list: { item: "找到钥匙", list: 场景配置 }
# 第 N 关的背景名在第 (N-1)*5+1 项
```

⚠️ **这种「一条列表切成多个字段」的取法很难读**，
推荐用**多条平行列表**（场景名、敌人数、道具数…各一条），
索引统一用场景号 → 更好维护。

### ⚠️ 坑

- **背景名里的中文/空格在 IR 里要注意引号**：`{ switch_backdrop: { backdrop: "森林 空地" } }`。
- **同名背景要避免**：Scratch 按名字切背景，两个背景同名会切错。
- **背景切换会清掉「画笔」？** 不会 —— 画笔是角色的，会保留；
  但**画笔扩展的图章会留在舞台上**，切场景后要 `pen_clear`。
- **切背景时正在跑的克隆体会继续跑**（它们不属于背景），
  要在切场景时广播「清理敌人」让克隆体自杀。

---

## 45. 菜单系统与暂停

### 45.1 四层菜单结构

社区最稳的菜单架构是**四种状态 + 一个 state 变量**：

| state | 场景 | 谁能点 |
|---|---|---|
| 0 | 标题页 | 开始按钮 |
| 1 | 游戏中 | 暂停按钮 |
| 2 | 暂停中 | 继续 / 设置 / 回标题 |
| 3 | 结算页 | 重玩 / 回标题 |

```yaml
# 舞台
- - when_green_flag_clicked:
  - set_variable: { var: state, value: 0 }
  - switch_backdrop: { backdrop: 标题页 }
```

### 45.2 暂停 = 只改状态变量

**Scratch 没有「暂停所有脚本」积木**（有 `停止其他脚本`，但那是针对单个角色的）。
暂停的标准做法就是**改状态变量**，让每个运动脚本自己检查：

```yaml
# 猫的运动脚本
- forever:
    do:
      - if: { cond: { equals: { a: {var: state}, b: 1 } }, do: [ ...移动逻辑... ] }
```

按 P 键：

```yaml
- - when_key_pressed: { key: p }
  - if: { cond: { equals: { a: {var: state}, b: 1 } }, do: [ { set_variable: { var: state, value: 2 } } ] }
```

⚠️ **Scratch 的按键积木没有 Esc 键**（只有字母、数字、方向键、空格、any），
所以社区都用 **P** 做暂停。

### 45.3 ⚠️ 最重要的坑：重置逻辑要挂在「广播」上，不能挂在绿旗上

Kids Coding Tutor 把这个称为最常见的 Retry bug：

> 如果石头的出生位置写在「当绿旗被点击」下而不是「当收到 reset」下，
> 点 Retry 时石头不会归位 —— 因为点 Retry 不是点绿旗。
> 石头还压在猫身上，你一进游戏就立刻又 Game Over。

**规则：任何「一局开始时要复位」的东西，都必须写在「当收到 [重置]」下面，
不能写在绿旗下面。**

```yaml
# 绿旗：只做全局初始化（进标题页）
- - when_green_flag_clicked:
  - set_variable: { var: state, value: 0 }
  - switch_backdrop: { backdrop: 标题页 }

# 重置：所有「一局开始要复位」的东西
- - when_receive:
      message: 重置
  - set_variable: { var: state, value: 1 }
  - set_variable: { var: 分数, value: 0 }
  - switch_backdrop: { backdrop: 游戏场景 }
  - broadcast: 玩家出生

# 开始按钮
- - when_this_sprite_clicked:
  - broadcast: 重置
```

⚠️ **最佳分数不能挂在绿旗上**：绿旗会清空它，
最佳分就只活到下一次绿旗。正确做法是**只在新纪录时更新**，其他时候完全不碰它：

```yaml
- if: { cond: { greater_than: { a: {var: 分数}, b: {var: best_easy} } }, do: [ { set_variable: { var: best_easy, value: {var: 分数} } } ] }
```

### 45.4 设置面板

设置面板 = **面板 + 遮罩 + 若干开关按钮**（与 §5 的弹窗三件套一样）：

```yaml
- - when_receive:
      message: 打开设置
  - show: null
  - go_to_front_back: front
```

开关按钮用一个 0/1 变量驱动：

```yaml
# 音效开关按钮
- - when_this_sprite_clicked:
  - set_variable: { var: 音效开, value: { subtract: [1, {var: 音效开}] } }
  - if: { cond: { equals: { a: {var: 音效开}, b: 1 } }, do: [ { switch_costume: { costume: 开 } } ] }
  - else: [ { switch_costume: { costume: 关 } } ]
```

### 45.5 选关界面

**一个按钮角色 + 多个造型**，造型号 = 关卡号：

```yaml
# 选关按钮
- - when_key_pressed: { key: right arrow }
  - next_costume: null
- - when_key_pressed: { key: left arrow }
  - change_variable: { var: 造型序号, by: -1 }
  - if: { cond: { less_than: { a: {var: 造型序号}, b: 1 } }, do: [ { set_variable: { var: 造型序号, value: { costume_number_name: null } } } ] }
  - switch_costume: { costume: { var: 造型序号 } }
- - when_this_sprite_clicked:
  - set_variable: { var: 当前关卡, value: { costume_number_name: null } }
  - broadcast: 开始关卡
```

⚠️ **`costume_number_name` 要选「编号」不是「名称」** —— 名称会返回中文造型名。
IR 里默认走 `NUMBER_NAME` 字段时值写 `number`。

### 45.6 菜单要「可穿透」时的处理

⚠️ **Scratch 的点击会穿透**（点上层按钮，下层角色也收到点击）。
菜单盖住游戏时，**必须有遮罩**（§5）挡住下层的点击。

---

## 46. 节奏游戏

### 46.1 节拍要靠计时器，不能靠 wait 累加

社区共识（scratch-discuss 节奏游戏帖）：
**用 `wait until timer > 目标时刻`**，不要用 `wait 0.5` 一层层叠。

```yaml
# 120 BPM → 每拍 0.5 秒
- - when_green_flag_clicked:
  - reset_timer: null
  - set_variable: { var: 拍数, value: 1 }
  - forever:
      do:
        - wait_until: { cond: { greater_than: { a: {timer: null}, b: { multiply: [ {var: 拍数}, 0.5 ] } } } }
        - broadcast: 拍点
        - change_variable: { var: 拍数, by: 1 }
```

⚠️ **必须用 `>` 而不是 `=`**：计时器不会正好停在 0.5，
`wait until timer = 0.5` 可能永远等不到（Scratch 论坛原话）。

⚠️ **每次演出/关卡开始必须 `reset_timer`**，否则计时器还带着上一段的时间。

### 46.2 判定窗口（用距离分级）

节奏游戏的核心是「按得准不准」。社区做法是**算音符到判定线的距离，按距离分段给分**：

```
距离 < 0.5  → Perfect（100 分）
距离 < 2    → Great（75 分）
距离 < 4    → Good（50 分）
距离 < 6    → Okay（25 分）
距离 < 8    → Bad（5 分）
否则        → Miss（0 分）
```

```yaml
- - when_key_pressed: { key: a }
  - set_variable: { var: 判定差, value: { distance_to: { object: 判定点 } } }
  - if:
      cond: { less_than: { a: {var: 判定差}, b: 8 } }
      do:
        - if: { cond: { less_than: { a: {var: 判定差}, b: 0.5 } }, do: [ { change_variable: { var: 分数, by: 100 } } ] }
        - if: { cond: { and: [ { greater_than: { a: {var: 判定差}, b: 0.5 } }, { less_than: { a: {var: 判定差}, b: 2 } } ] }, do: [ { change_variable: { var: 分数, by: 75 } } ] }
        - change_variable: { var: 连击, by: 1 }
  - else:
      - change_variable: { var: 连击, by: -1 }
```

⚠️ **注意「距离 = 0 会除零」**：如果用 `分数 / 距离` 的公式，
必须先判距离 > 0，或者像上面那样改成「固定分段给分」（社区建议），
分段法还顺带避免了「越近分越离谱」。

⚠️ **判定点的位置必须和音符的判定线重合**，否则玩家看着 A 键但实际判的是别处。
做法：判定点是**固定不动的**，音符从右边飞过来，命中判定点才算。

### 46.3 长按（Hold）

长按音符需要**三段逻辑**：按下 → 持续判定 → 松开判定。

```
按下时：判定距离 → 命中则记 hold_start = 计时器，hold_ok = 1
持续中（forever）：if hold_ok = 1 则每 0.1 秒加分（长按奖励）
松手时：if hold_ok = 1 且 (计时器 - hold_start) < 音符时长 then 判失败
```

⚠️ **长按的松手判定要看「持续时间够不够」**，
提前松手是 MISS（但不断连击 —— 这是 OverRapid 等游戏的做法）。

### 46.4 谱面用列表存

一首歌几百个音符，硬写不可能。**每条轨道一条列表，存「第几拍 + 音符类型」**：

```yaml
# 列表「谱面A」：每 2 项 [拍号, 类型(1=单击 2=长按)]
- add_to_list: { item: 1, list: 谱面A }
- add_to_list: { item: 1, list: 谱面A }
- add_to_list: { item: 2, list: 谱面A }
- add_to_list: { item: 2, list: 谱面A }
```

生成时按拍号算 x 坐标：`x = 240 - (拍号 - 当前拍) * 间距`。

### 46.5 连击与评价

- 连击：命中 +1，Miss 时清零（长按提前松手**不清零**）
- 评价：按连击数分档（50/100/200/300 连击 → S/A/B/C）
- ⚠️ **连击数要用「显示数字」还是文本精灵** —— 别用监视器（见 SKILL 铁律）。

---

## 47. 敌人 AI 决策进阶

§16 讲了「视野锥 + 巡逻 + 三态状态机」。这一节讲**让敌人真的会想**。

### 47.1 效用 AI（Utility AI）：给每个选项打分，选最高的

社区（scratch-discuss 敌人 AI 帖）给的做法：
**不写死优先级，而是给每个行动算一个分数，选分数最高的执行。**

```
追击分 = 100 - 距离玩家        （越近分越高）
攻击分 = 50 + (玩家HP低 ? 30 : 0)
逃跑分 = (自己HP低 ? 80 : 0)
巡逻分 = 10
```

```yaml
- - when_receive:
      message: 决策
  - set_variable: { var: 追击分, value: { subtract: [ 100, { distance_to: { object: 玩家 } } ] } }
  - set_variable: { var: 攻击分, value: 50 }
  - if: { cond: { less_than: { a: {var: 玩家HP}, b: 30 } }, do: [ { change_variable: { var: 攻击分, by: 30 } } ] }
  - set_variable: { var: 逃跑分, value: 0 }
  - if: { cond: { less_than: { a: {var: 自身HP}, b: 30 } }, do: [ { set_variable: { var: 逃跑分, value: 80 } } ] }
  - set_variable: { var: 最好分, value: 10 }
  - set_variable: { var: 最好行动, value: "巡逻" }
  - if: { cond: { greater_than: { a: {var: 追击分}, b: {var: 最好分} } }, do: [ { set_variable: { var: 最好分, value: {var: 追击分} } } ] }
  - if: { cond: { greater_than: { a: {var: 攻击分}, b: {var: 最好分} } }, do: [ { set_variable: { var: 最好分, value: {var: 攻击分} } } ] }
  - if: { cond: { greater_than: { a: {var: 逃跑分}, b: {var: 最好分} } }, do: [ { set_variable: { var: 最好分, value: {var: 逃跑分} } } ] }
```

⚠️ **`最好分` 要先设成巡逻分（基准），否则所有行动分都可能低于 0 而都不选。**

⚠️ **决策不要每帧做** —— 每 0.2~0.5 秒决策一次（性能 + 避免抖动）。

### 47.2 听觉：背后也能发现你

敌人不只看视野，还「听得到」：

```
玩家速度 > 8 且 距离 < 120 → 敌人听到，朝玩家方向看
```

```yaml
- if:
    cond: { and: [ { greater_than: { a: {var: 玩家速度}, b: 8 } },
                   { less_than: { a: { distance_to: { object: 玩家 } }, b: 120 } } ] }
    do:
      - set_variable: { var: AI状态, value: 1 }
```

⚠️ 玩家速度是**世界坐标差分**算出来的（§2 平滑移动的 vx/vy），
不要用「位置有没有变」判断 —— 站着不动也会被判成在跑。

### 47.3 搜索状态：不要一丢就回巡逻

TrueSight 的建议：玩家从视野消失时，
**不要立刻回巡逻**，先去「最后看到玩家的位置」附近搜索 3 秒。

```yaml
# 失去视野时记下最后位置
- set_variable: { var: 最后看到X, value: { of: { object: 玩家, property: "x position" } } }
- set_variable: { var: 最后看到Y, value: { of: { object: 玩家, property: "y position" } } }
- set_variable: { var: AI状态, value: 2 }   # 2 = 搜索
```

搜索状态里在最后位置周围随机徘徊（§25 洗牌 + §16 巡逻点），
搜索计时器归零后才回巡逻。

### 47.4 敌人协作：一个发现，全体响应

克隆体之间要共享信息，用**全局变量 + 广播**：

```yaml
# 任何敌人发现玩家
- - when_receive:
      message: 发现玩家
  - set_variable: { var: 玩家已暴露, value: 1 }   # 全局变量
  - broadcast: 全体追击
```

⚠️ **「玩家已暴露」要用 `wait until` 复位** —— 否则玩家一躲起来，
所有敌人都会一直追。

### 47.5 让敌人「像人」的两个小招

- **决策延迟**：`wait (随机 0 到 0.3) 秒` 再行动 → 不像机器人一样瞬间反应。
- **随机攻击模式**：攻击方式用 `pick random 1 到 3` 选，
  并加随机停顿 → 玩家猜不到下一次会怎样。

---

## 48. 射线检测与视线

### 48.1 Scratch 没有射线，但可以「步进」模拟

Scratch Wiki《Raycaster》的核心思路：**射线不是算出来的，是走出来的**。

```yaml
# 射线精灵：从玩家位置出发，沿方向一步步走，碰到墙就停
- - when_receive:
      message: 探测
  - goto_xy: { x: { of: { object: 玩家, property: "x position" } }, y: { of: { object: 玩家, property: "y position" } } }
  - point_towards: { TOWARDS: 目标点 }
  - set_variable: { var: 距离, value: 0 }
  - repeat_until:
      cond: { touching_color: { COLOR: "#2a2a2aff" } }
      do:
        - move: { steps: 1 }
        - change_variable: { var: 距离, by: 1 }
```

⚠️ **步长决定精度也决定速度**：步长 5 太糙、步长 1 慢。
hqwc.cn 的实测结论：步长 0.1 精度高但卡顿，0.2 快但墙边有锯齿，
**0.1 是平衡点**（在普通笔记本上能跑 60fps）。

⚠️ **三角函数精度**：Scratch 的 `sin`/`cos` 精度不稳，
hqwc.cn 的做法是**预存 0~360 度的 sin/cos 到列表，用角度当索引查表**。
只要几个方向的话，直接用 `point towards` + `move` 更省事。

### 48.2 视线遮挡：敌人能不能看见玩家

最实用的简化版：**只判断「敌人和玩家之间有没有墙」**。
做法是让一个「探针」在敌人和玩家之间走，看会不会撞墙：

```yaml
# 敌人每 0.2 秒检查一次
- - when_receive:
      message: 视线检查
  - goto_xy: { x: {var: 敌人X}, y: {var: 敌人Y} }
  - point_towards: { TOWARDS: 玩家 }
  - set_variable: { var: 距离, value: 0 }
  - repeat_until:
      cond: { or: [ { touching_color: { COLOR: "#2a2a2aff" } },
                   { greater_than: { a: {var: 距离}, b: 200 } } ] }
      do:
        - move: { steps: 5 }
        - change_variable: { var: 距离, by: 5 }
  - if:
      cond: { greater_than: { a: {var: 距离}, b: 200 } }   # 没撞墙 → 看得见
      do:
        - set_variable: { var: 看得见, value: 1 }
```

⚠️ **「碰到颜色」比「碰到角色」更适合做视线**：
墙画成一张位图（墙=黑色，空地=白色），探针走上去检测颜色 ——
不用给每堵墙都做角色。

⚠️ **探针必须设成「不影响画面」**：`ghost 100`（全透明）+ `go behind other`。
否则玩家会看到一个飞来飞去的点。

### 48.3 更省的替代：连线判定（凸多边形/矩形）

如果场景里的墙都是轴对齐的矩形，**不需要射线**：
判断「敌人和玩家的连线是否穿过墙矩形」用简单的几何判定更快。
但 Scratch 里做这个要自己算交点，**性价比不高** ——
除非场景很简单，否则还是用步进 + 碰到颜色。

### 48.4 3D 伪透视（进阶）

《Wolfenstein 3D》式第一人称恐怖游戏在 Scratch 里能跑：
逐列发射射线测墙距离 → 按距离画垂直柱子。

```
柱子高度 = 焦距 / 距离      （焦距常量，如 6000）
```

⚠️ **深度排序**：怪物在墙后面时不该画出来。
简单策略：先画墙，再画怪物，但**画怪物前判断「怪物所在列是否被墙挡住且怪物更远」**。

⚠️ **每帧只算一部分列**（如 1/4 列），否则 480 列全算会卡。

---

## 49. 吸引力与物理效果

### 49.1 物体吸引（磁铁、重力、吸尘器）

Scratch Wiki《Object Attraction》给了四种方法，按准确度排序：

| 方法 | 做法 | 准确度 | 适合 |
|---|---|---|---|
| **椭圆轨道法** | 用 sin/cos 算位置，跟着中心转 | 100% 准 | 卫星绕行星 |
| **速度法** | 速度朝目标方向累加 | 不准 | 需要同时处理多个吸引源 |
| **三角法** | `point towards` + `move` | 准 | **最常用** |
| **直接法** | `go to x: 鼠标x*10 y: 鼠标y*10` | 特殊 | 鼠标吸引 |

**最常用的是三角法**：

```yaml
- forever:
    do:
      - point_towards: { TOWARDS: 磁铁 }
      - move: { steps: 3 }
```

⚠️ **直接法会让物体永远到不了目标点**（越靠近走得越慢），
但做「橡皮筋」效果正好。

### 49.2 磁力吸取（拾取范围 + 强度衰减）

游戏里的「吸金币」通常是**距离衰减的吸引**：

```yaml
- - when_receive:
      message: 磁力
  - set_variable: { var: 距离, value: { distance_to: { object: 玩家 } } }
  - if:
      cond: { less_than: { a: {var: 距离}, b: 100 } }
      do:
        - point_towards: { TOWARDS: 玩家 }
        - set_variable: { var: 力度, value: { divide: [ {var: 吸取范围}, {var: 距离} ] } }
        - move: { steps: {var: 力度} }
```

⚠️ **力度 = 范围 / 距离，距离接近 0 会爆炸（除零）**。
必须夹紧：`if 距离 < 2 then 距离 = 2`。

### 49.3 重力（Alura / EducaWeb 的经典写法）

重力 = **速度变量每帧累加**：

```yaml
- - when_green_flag_clicked:
  - set_variable: { var: vy, value: 0 }
- - forever:
    do:
      - change_variable: { var: vy, by: -2 }        # 重力加速度（负=向下）
      - change_y: { dy: {var: vy} }                # 用速度移动
      - if:
          cond: { less_than: { a: { y_position }, b: -160 } }
          do:
            - set_variable: { var: vy, value: { multiply: [ {var: vy}, -0.8 ] } }  # 反弹+失能
            - goto_xy: { x: { x_position }, y: -160 }                             # 贴回地面
```

⚠️ **必须分「速度」和「位置」两个变量**。
新手常犯的错是直接 `change y by -5` → 匀速下落 → 完全不像重力。

⚠️ **反弹要损失能量**：`vy = vy * -0.8`（乘 0.8）或 `vy = vy * -1` 之后 `vy -= 0.5`。
否则球会永远弹一样高。

⚠️ **重力加速度（-2）是每帧的**，Scratch 一秒 30 帧 → 实际约 -60/秒²。
数值要自己调。

### 49.3.1 ⚠️⚠️ 摩擦必须「乘」，绝不能「减」

这是本册最容易踩、后果最严重的一个坑：

```yaml
# ❌ 错：这是「减法摩擦」，速度会一路减到 -∞，物体反而越走越快、飞出屏幕
- change_variable: { var: vx, by: -0.2 }

# ✅ 对：乘性阻尼，速度按比例衰减，会自然停住
- set_variable: { var: vx, value: { multiply: [ {var: vx}, 0.99 ] } }
```

**区别**：
- 减法摩擦 `vx -= 0.2`：速度**匀速**减少 → 变成负数后继续减 → 无限增大 → 物体反向加速飞走。
  （实测：0.2/帧的减法能让小球在 3 秒内跑到 x = -69000。）
- 乘性摩擦 `vx *= 0.99`：速度**按比例**衰减 → 指数收敛到 0 → 物体自然停下。

**记忆点：摩擦/阻尼/衰减一律用「乘」，只有重力/加速度才用「加/减」。**

（重力为什么可以用减法？因为重力是**加速度**（每帧加一个固定的量），
它改变的是速度的变化率；而摩擦是**速度的比例衰减**，
改的��是速度本身。分清「谁在变」就不会混。）

### 49.3.2 反弹时要「贴回边界」

只翻转速度不够 —— 那一帧角色已经陷进墙里了，会卡住或抖动。
标准做法是**翻转速度 + 立刻贴回边界**：

```yaml
- if:
    cond: { less_than: { a: { y_position }, b: -160 } }
    do:
      - set_variable: { var: vy, value: { multiply: [ {var: vy}, -0.8 ] } }
      - goto_xy: { x: { x_position }, y: -160 }
```

### 49.4 弹性球 vs 固定球

- **弹性球**：撞墙 `vx = vx * -0.9`（乘性失能，见 §49.3.1）
- **固定球**：把球放在一个「碰到就反弹」的角色里，用广播让球改方向
  （适合破砖块）

⚠️ **Scratch 的碰撞是「重叠判定」不是「物理接触」**，
高速物体可能穿墙（§33 的 10 像素问题同源）。
解法：**每帧分步移动**（速度 10 时拆成 10 次 move 1），
或用 `重复执行直到 碰到 ...` 停下。

⚠️ **不要用「碰到颜色」当墙**做高速弹球 —— 颜色判定同样有像素级漏检，
高速下会穿过去。要做高速物理，用「位置越界」判定 + 贴回边界（§49.3.2），
不用颜色。

---

## 50. 成长与装备系统

### 50.1 等级与经验曲线

```yaml
# 升级判定
- if: { cond: { greater_than: { a: {var: 玩家XP}, b: {var: xpToLevel} } }, do: [ ... ] }
- change_variable: { var: 玩家等级, by: 1 }
- change_variable: { var: 玩家攻击, by: 2 }
- change_variable: { var: 玩家防御, by: 1 }
- change_variable: { var: 玩家最大HP, by: 5 }
- set_variable: { var: 玩家XP, value: 0 }
- change_variable: { var: xpToLevel, by: 0.3 }   # 需求 ×1.3
```

⚠️ **升级阈值要乘一个系数**（如 1.3），
否则线性增长会让后期升级跟前期一样快，没有「变难」的感觉。

### 50.2 装备：换造型 + 改属性

Scratch 里「装备」通常有两条效果线：
**视觉**（换造型）+ **数值**（改属性变量）。

```yaml
# 穿上「铁剑」
- switch_costume: { costume: 持铁剑 }
- change_variable: { var: 攻击力, by: 5 }
```

⚠️ **换造型时数值要一起改**，而且**脱下时要减回去**。
最稳的做法是**每次都从「基础值 + 装备加成」重算**，而不是增量加减：

```
攻击力 = 基础攻击力 + 装备1加成 + 装备2加成 + 等级加成
```

这样穿脱装备不会累积出奇怪的数值。

### 50.3 技能树：布尔变量当解锁标记

```yaml
# 列表「技能」：每 2 项 [技能名, 是否解锁(0/1), 消耗SP]
- if: { cond: { equals: { a: { item_of_list: { index: 2, list: 技能 } }, b: 1 } }, do: [ ...生效逻辑... ] }
```

⚠️ **前置技能要检查**：解锁「火球」要先有「火种」。
检查方式：`item_num_of_list` 找前置技能在第几项 → 读那一项的状态。

### 50.4 随机词条（肉鸽式构筑）

肉鸽（Roguelike）的核心是「每局随机 + 构筑（build）」。
在 Scratch 里做「三选一升级」：

```yaml
# 列表「词条池」：每个词条 3 项 [名字, 类型, 数值]
- set_variable: { var: 候选1, value: { item_of_list: { index: { random: { from: 1, to: { length_of_list: { list: 词条池 } } } }, list: 词条池 } } }
```

⚠️ **随机抽 3 个不重复的词条**：
不能「一直随机直到不重复」（会死循环）。
正确做法是**洗牌**（§25 Fisher-Yates）后取前 3 个。

⚠️ **词条池用「一条列表每项多字段」还是「多条平行列表」**：
词条有名字+类型+数值+描述 4 个字段，
用**多条平行列表**（词条名、词条类型、词条数值）比一条列表切 4 段好维护。

### 50.5 随机装备的属性区间

```
词条数值 = 随机(下限, 上限)
```
下限/上限本身也可以随机（品质）：
普通（0~2）、稀有（3~6）、传说（7~12）。

⚠️ **品质概率用「随机 1 到 100」判定**：
```
r = 随机(1, 100)
r <= 60 → 普通
r <= 90 → 稀有
else     → 传说
```

### 50.6 局内成长 vs 局外成长

| 类型 | 存哪 | 例子 |
|---|---|---|
| 局内（这局） | 普通变量 | 本局捡到的金币、临时 buff |
| 局外（永久） | **云变量** | 最高分、解锁的角色、永久天赋 |

⚠️ **局外成长用云变量，但别每帧写**（§23 的硬限制：每秒最多 10 次）。
只在「关卡结束」「购买成功」这种离散时刻写。

⚠️ **云变量只存数字**（§42）——
「已解锁的角色」要编码成 1/2/4/8… 的位掩码，或者用「已解锁数量 + 列表」组合。

---

## 附录：本册用到的积木速查

| 用途 | IR 写法 |
|---|---|
| 切换背景 | `{ switch_backdrop: { backdrop: 名称 } }` |
| 当背景切换到 | `{ when_backdrop_switches_to: { backdrop: 名称 } }` |
| 停止本角色其他脚本 | `{ stop: { stop_option: other scripts in sprite } }` |
| 停止所有脚本 | `{ stop: { stop_option: all } }` |
| 面向某角色 | `{ point_towards: { TOWARDS: 角色名 } }` |
| 两点距离 | `{ distance_to: { object: 角色名 } }` |
| 造型编号 | `{ costume_number_name: null }` |
| 某角色的属性 | `{ of: { object: 角色名, property: "x position" } }` |
| 计时器 | `{ timer: null }` / `{ reset_timer: null }` |
| 等待直到 | `{ wait_until: { cond: 条件 } }` |
| 重复直到 | `{ repeat_until: { cond: 条件, do: [...] } }` |
| 碰到颜色 | `{ touching_color: { COLOR: "#rrggbb" } }` |
| 取余 | `{ mod: { a: x, b: y } }` |
| 绝对值 | `{ mathop: { operator: abs, num: 值 } }` |
| 列表：加入 | `{ add_to_list: { item: 值, list: 列表名 } }` |
| 列表：删除第 n 项 | `{ delete_of_list: { index: n, list: 列表名 } }` |
| 列表：某值在第几项 | `{ item_num_of_list: { item: 值, list: 列表名 } }` |
| 列表：长度 | `{ length_of_list: { list: 列表名 } }` |
| 键按下 | `{ when_key_pressed: { key: p } }` |
| 克隆 | `{ create_clone_of: { clone: 角色名 } }` / `{ when_start_as_clone: { clone: _myself_ } }` |
| 改变 x / y | `{ change_x: { dx: 值 } }` / `{ change_y: { dy: 值 } }`（**是 dx/dy，不是 value**）|
| 摩擦/衰减 | `{ set_variable: { var: vx, value: { multiply: [ {var: vx}, 0.99 ] } } }`（**必须用乘**）|

> ⚠️ **单操作数运算必须写 `operand:`**：`not` 的输入名是 `OPERAND`，
> 写成 `{ not: { equals: ... } }` 会静默生成空操作数。

> ⚠️ **`change_x` / `change_y` 的输入名是 `dx` / `dy`**：
> 写 `{ change_x: { value: 10 } }` 会被**静默忽略**（编译成「移动 0」），
> 角色**完全不动**。正确写法：`{ change_x: { dx: 10 } }`。

> ⚠️ **自定义积木没有返回值**（Scratch 3 限制）：
> 需要「函数返回值」时，用「全局变量 + 自定义积木」组合。
