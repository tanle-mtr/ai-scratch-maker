# 游戏手感与交互（第七册：§75–§82）

> 来源：Scratch Wiki《Sound》《Music Extension》《Cloning》《When Green Flag Clicked》、
> Scratch 论坛「How to make a smooth trail」「best way to make a menu without asking」、
> Kids Coding Tutor《Scratch Sound Tips》、Ch Scratch《Sound Effects》系列等公开资料，
> 以及社区反复验证的「询问积木 vs 角色按钮」「克隆体生命周期」经验。
>
> 本册专注**让作品"手感变好"**的四件套：
> **拖尾（视觉反馈）、背景音乐（听觉氛围）、多角色选项菜单（替代"询问"积木）、克隆的正确用法（性能与可维护性）**。
> 这四样东西单看都不难，但**组合起来就是一个游戏从"作业"变成"作品"的分界线**。
>
> 与前面各册的关系：
> - 拖尾 = 第一册 §7（克隆粒子）**视觉化**，第六册 §67（画笔拖尾）的**玩法化**；
> - 背景音乐 = 第五册 §60（程序化音乐）的**工程化**，第一册 §12（音频控制）的**场景化**；
> - 多角色选项菜单 = 第三册 §45（菜单系统与暂停）的**替代实现**（不用"询问"积木）；
> - 克隆的正确用法 = 第一册 §7（克隆粒子）的**方法论补充**（何时**不该**用克隆）。

## 速查表

| 想做什么 | 章节 |
|---|---|
| 主角身后拖出一条彩带 / 残影 | §75 拖尾系统（三种拖尾 + 残影 + 拖尾回收） |
| 游戏有背景音乐，切换场景要换曲 | §76 背景音乐系统（BGM 状态机 + 淡入淡出 + 分层） |
| 让玩家点选项，但**不要用"询问"积木** | §77 多角色选项菜单（每个选项一个角色按钮） |
| 不知道什么时候该用克隆、什么时候不该 | §78 克隆的正确用法（决策树 + 生命周期 + 预算） |
| 打中敌人要有"打击感" | §79 受击反馈（顿帧 + 闪白 + 击退 + 音效） |
| 菜单要有开合动画 / 角色出场动画 | §80 演出与转场（配合 §66 的转场） |
| 让玩家按节奏操作 | §81 节奏输入判定（时间窗 + 判定等级） |
| 一堆角色想共用一套逻辑 | §82 广播驱动的解耦架构 |

---

## 75. 拖尾系统：彩带、残影与回收

拖尾是**性价比最高的视觉升级**：一个 `forever` 循环 + 几个变量，效果立刻从"色块在飞"变成"有速度感"。

### 75.1 三种拖尾，选一种就够

| 方案 | 原理 | 适合 | 成本 |
|---|---|---|---|
| **A. 画笔拖尾**（推荐做光带） | 落笔后角色移动，笔迹留在画笔图层 | 主角划过的光带、赛车尾迹、剑光 | 极低（不产生克隆体） |
| **B. 克隆残影** | 定时生成克隆体，逐渐变淡后删除 | 飞船残影、幽灵分身、弹跳留下的印子 | 中（每帧 ≤ 5 个克隆） |
| **C. 造型拖尾**（无克隆） | 一个角色带多套"越来越淡"的造型，循环切换 | 像素风、8 位机风格 | 低（零克隆） |

### 75.2 方案 A：画笔拖尾（不产生任何克隆体）

```yaml
- name: 主角
  costumes:
    - { name: 点, asset: assets/dot.svg }
  scripts:
    - - when_green_flag_clicked:
      - hide: null
      - set_pen_size: { size: 4 }
      - set_pen_hue: { hue: 60 }
      - forever:
          do:
            - pen_down: null
            - move_steps: { steps: 4 }
            - change_pen_hue: { hue: 2 }
```

⚠️ **画笔拖尾会永久留在舞台上**。要每帧重画（比如赛车圈速、绘图游戏），
就必须**每帧 `pen_clear`** —— 但那样拖尾也就没了。两种解法：

- **要拖尾就不要每帧清**：让拖尾自然积累成一条长带（画笔图层无限长 = 记录路径）；
- **要每帧重画就分两个角色**：一个专责画笔（每帧 `pen_clear` 后重绘轨迹），
  一个负责显示。详见第六册 §70 的"每帧重画"模式。

### 75.3 方案 B：克隆残影（重点：克隆体要能"退休"）

⚠️ **残影最容易犯的错：克隆体只增不减**，几十秒后卡死。三条铁律：

1. **克隆体必须有寿命**（到点 `delete this clone`）；
2. **克隆体不能再生克隆体**（否则指数爆炸）；
3. **生成频率要限流**（不是每帧都生成）。

```yaml
- name: 主角
  variables:
    残影间隔: 0.05     # 秒
    残影寿命: 12       # 帧
    残影计数: 0
  costumes:
    - { name: 点, asset: assets/dot.svg }
  scripts:
    # —— 本体：移动 + 定期生成残影 ——
    - - when_green_flag_clicked:
      - hide: null
      - forever:
          do:
            - move_steps: { steps: 5 }
            - wait: { secs: { var: 残影间隔 } }
            - create_clone_of: { clone: _myself_ }
    # —— 克隆体：出现 → 变淡 → 删除 ——
    - - control_start_as_clone:
      - set_ghost: { ghost: 30 }
      - repeat: { times: { var: 残影寿命 }, do:
          [ { change_variable: { var: 残影计数, by: -1 } }
          , { change_effect: { effect: GHOST, value: 5 } } ] }
      - delete_this_clone: null
```

⚠️ **⚠️ 最大的坑：克隆体也会触发本体的事件帽子**。
本体有「当绿旗被点击」不影响克隆体（克隆体不重跑绿旗），
但本体有「当按下空格键」「当收到消息」这类**帽子**时，克隆体**也会响应**。
后果：按一次空格 → 生成 10 个残影 → 10 个残影又各自响应空格 → 生成 100 个 → 爆炸。

标准解法是加一个**私有标志位**：

```yaml
- name: 主角
  variables:
    是克隆: 0
  scripts:
    - - when_green_flag_clicked:
      - set_variable: { var: 是克隆, value: 0 }
    - - control_start_as_clone:
      - set_variable: { var: 是克隆, value: 1 }
    - - when_key_pressed: { key: space }
      - if: { cond: { equals: [ { var: 是克隆 }, 0 ] }, do:
          [ { create_clone_of: { clone: _myself_ } } ] }
```

> 📌 第一册 §7 讲过同样的坑，这里补充**为什么**：`control_start_as_clone` 这个帽子
> 是在克隆发生时由 VM 触发的，它**只属于克隆体**；而 `when_key_pressed` 这类帽子
> 属于**角色的脚本**，克隆体是同一个角色的实例，所以会一起响应。
> 标志位必须是**私有变量**（"仅适用于此角色"），否则所有角色共享一个值就没意义了。

### 75.4 拖尾"回收"的两种思路

| 思路 | 做法 | 适合 |
|---|---|---|
| **缩短寿命** | 克隆体 N 帧后自删 | 通用，残影标准做法 |
| **环形复用** | 固定 N 个克隆体循环使用（用完"传送"到下一个位置） | 极致性能要求（弹幕游戏） |

环形复用的关键是：**不删克隆，而是改它的位置**。
```yaml
# 固定 8 个克隆体当"残影池"，本体每移动一格就把最老的那个挪过来
- - when_green_flag_clicked:
  - repeat: { times: 8, do: [ { create_clone_of: { clone: _myself_ } } ] }
```

### 75.5 拖尾与"速度感"的关系

一个反直觉但很重要的规律：**拖尾长度应该和速度挂钩，不是固定值**。
角色慢时拖尾短（贴着身体），角色快时拖尾长（被拉长），这样才有"加速"的物理感。

做法：把残影生成间隔和角色的速度变量关联：
```
残影间隔 = 0.15 / (速度 + 1)      # 速度越快，间隔越短 → 残影越密
```
用 `divide` + `add` 即可，⚠️ 记得给速度加 1 防除零。

### 75.6 IR 写法要点 ✅

| 积木 | IR 写法 |
|---|---|
| 生成克隆体 | `{ create_clone_of: { clone: _myself_ } }` |
| 当作为克隆体启动 | `{ control_start_as_clone: null }` |
| 删除克隆体 | `{ delete_this_clone: null }` |
| 变淡 | `{ change_effect: { effect: GHOST, value: 5 } }` |
| 等待 | `{ wait: { secs: 0.05 } }` |

---

## 76. 背景音乐系统：状态机 + 淡入淡出 + 分层

背景音乐不是"放个声音就完事"。一个像样的 BGM 系统要解决三件事：
**① 场景切换时换曲 ② 换曲不突兀（淡入淡出） ③ 音效和 BGM 不打架（分层音量）**。

### 76.1 ⚠️ 先记住 Scratch 音频的两个硬限制

| 限制 | 后果 | 应对 |
|---|---|---|
| **音量是全局的**（Scratch 3.0 没有"每个声音独立音量"） | BGM 和音效共用一个音量旋钮 | 把 BGM 素材**预先**压低音量，音效保持原样 |
| **`stop all sounds` 一刀切** | 一停就把 BGM 也停了 | 换曲时**不要**用它，用"播新的 + 旧的自然结束" |

> ✅ **好消息**：Scratch 3.0 的 `播放声音 [xxx] 等待播完` 是**可以打断**的，
> 而 `开始播放声音 [xxx]` 是后台播放、互不阻塞。
> **BGM 用"开始播放"，音效用"开始播放"，只有需要严格串行的才用"等待播完"。**

### 76.2 BGM 状态机：场景 → 对应曲目

思路和第三册 §44「场景管理与跨场景数据」一致：**用一个变量存"当前应该放哪首"**。

```yaml
# 舞台
- name: 舞台
  variables:
    当前BGM: 0
  scripts:
    # —— 场景一：BGM 1 ——
    - - when_receive:
          message: 进入森林
      - set_variable: { var: 当前BGM, value: 1 }
      - start_sound: { sound: 森林 }
    # —— 场景二：BGM 2 ——
    - - when_receive:
          message: 进入战斗
      - set_variable: { var: 当前BGM, value: 2 }
      - start_sound: { sound: 战斗 }
```

⚠️ **旧曲不会自己停**。要么让旧曲自然播完（BGM 通常是循环曲，听起来就断），
要么在换曲时 `stop_all_sounds`（但会连带停掉正在播的音效）。

**折中方案（推荐）**：把 BGM 做成**短循环片段**（10–30 秒），
用"播放到完 + 立刻再播"的方式续播，换曲时 `stop_all_sounds` 的影响就很小。

```yaml
- - when_receive:
      message: 播放BGM
  - forever:
      do:
        - if: { cond: { greater_than: [ { var: 当前BGM }, 0 ] }, do:
            [ { play_sound_until_done: { sound: 森林 } } ] }
```

### 76.3 淡入淡出（消除"啪"的一声）

`set volume` 是全局的，所以淡入淡出要**成对使用**：
进场景 → 音量 0 → 每帧 +5 涨到 100；出场景 → 每帧 -5 降到 0 → `stop_all_sounds`。

```yaml
- name: 音乐控制
  variables:
    目标音量: 100
    当前音量: 0
  scripts:
    # —— 淡入 ——
    - - when_receive:
          message: 音乐淡入
      - set_variable: { var: 目标音量, value: 100 }
      - forever:
          do:
            - if: { cond: { less_than: [ { var: 当前音量 }, { var: 目标音量 } ] }, do:
                [ { change_variable: { var: 当前音量, by: 4 } }
                , { set_volume: { value: { var: 当前音量 } } } ] }
    # —— 淡出 ——
    - - when_receive:
          message: 音乐淡出
      - set_variable: { var: 目标音量, value: 0 }
      - forever:
          do:
            - if: { cond: { greater_than: [ { var: 当前音量 }, 0 ] }, do:
                [ { change_variable: { var: 当前音量, by: -4 } }
                , { set_volume: { value: { var: 当前音量 } } } ] }
            - if: { cond: { less_than: [ { var: 当前音量 }, 0 ] }, do:
                [ { stop_all_sounds: null } ] }
```

⚠️ **两个 `forever` 会打架**：两个循环都在改音量。
**正确做法是合并成一个循环**，用 `目标音量` 决定往哪边走：

```yaml
- - when_green_flag_clicked:
  - set_variable: { var: 目标音量, value: 100 }
  - forever:
      do:
        - if: { cond: { less_than: [ { var: 当前音量 }, { var: 目标音量 } ] }, do:
            [ { change_variable: { var: 当前音量, by: 4 } } ] }
        - if: { cond: { greater_than: [ { var: 当前音量 }, { var: 目标音量 } ] }, do:
            [ { change_variable: { var: 当前音量, by: -4 } } ] }
        - set_volume: { value: { var: 当前音量 } }
        - if: { cond: { less_than: [ { var: 当前音量 }, 1 ] }, do:
            [ { stop_all_sounds: null } ] }
```

### 76.4 用音乐扩展做"程序化 BGM"（零素材）

第五册 §60 讲过音符序列器，这里补**做背景音乐**的要点：

```yaml
- name: BGM
  variables:
    旋律: [60, 62, 64, 65, 67, 65, 64, 62]
    时值: [0.5, 0.5, 0.5, 0.5, 1, 0.5, 0.5, 1]
    序号: 0
  scripts:
    - - when_green_flag_clicked:
      - set_tempo: { tempo: 120 }
      - set_instrument: { instrument: 1 }
      - forever:
          do:
            - set_variable: { var: 序号, value: 0 }
            - repeat: { times: { var: 旋律长度 }, do:
                [ { play_note:
                    note: { item_of_list: { index: { var: 序号 }, list: 旋律 } }
                    beats: { item_of_list: { index: { var: 序号 }, list: 时值 } } }
                , { change_variable: { var: 序号, by: 1 } } ] }
```

⚠️ **两个坑**：
1. `repeat times` 的次数**不能是列表长度**（Scratch 积木不能读列表长度），
   要单独维护一个 `旋律长度` 变量，或者用 `repeat until 序号 > 上限`；
2. `play note` 是**阻塞**的（要等这一拍播完），所以这个循环是天然串行的，不用 `wait`。

### 76.5 分层：BGM + 音效的音量平衡

因为音量全局，平衡只能靠**素材预处理**：

| 层 | 做法 |
|---|---|
| BGM | 导入时把音量压到 **30–40%** |
| 音效 | 保持 100% |
| 关键提示音 | 保持 100%（短促，不刺耳） |

> 💡 **也可以用"音乐扩展 + 声音素材"混用**：音乐扩展的音符不受 `set volume` 影响吗？
> **会受影响** —— 音乐扩展最终也是走音频引擎的，音量同样是全局的。
> 所以唯一可靠的办法还是**素材层面压低 BGM**。

### 76.6 IR 写法要点 ✅

| 积木 | IR 写法 |
|---|---|
| 开始播放声音 | `{ start_sound: { sound: 森林 } }` |
| 播放到完 | `{ play_sound_until_done: { sound: 森林 } }` |
| 停止所有声音 | `{ stop_all_sounds: null }` |
| 设音量 | `{ set_volume: { value: 60 } }` |
| 改音量 | `{ change_volume: { value: -5 } }` |
| 播放音符 | `{ play_note: { note: 60, beats: 0.5 } }` |
| 设乐器 / 速度 | `{ set_instrument: { instrument: 1 } }` / `{ set_tempo: { tempo: 120 } }` |

> ⚠️ 声音名必须和工程里的**音效素材名**完全一致；素材由 `scripts/gen_audio.py` 生成。
> 详见 `references/asset-guide.md` 第二节。

---

## 77. 多角色选项菜单：不用"询问"积木

### 77.1 为什么要抛弃"询问"积木

Scratch 有 `询问 [文字] 并等待`（IR：`{ ask: { question: 你要哪个？ } }`）。
它能用，但做正式作品时几乎总是错的选择：

| 问题 | "询问"积木 | 多角色按钮 |
|---|---|---|
| **样式** | 只能用系统默认输入框，丑 | 自己做美术，风格统一 |
| **选项有限** | 玩家只能打字，不能点 | 点一下就选 |
| **移动端** | 弹键盘，体验差 | 点按钮，友好 |
| **脚本阻塞** | 「询问并等待」会**停下当前脚本**直到玩家输入 | 只是一个广播，完全不阻塞 |
| **可扩展** | 改选项要改文本 | 加一个角色就多一个选项 |

> 📌 **关键洞察**：「询问并等待」会**阻塞当前脚本**。
> 如果它在 `forever` 里，整个角色就卡死了。菜单应该用**广播 + 状态变量**，不是询问。

### 77.2 标准架构：每个选项一个角色

**核心设计**：一个菜单不是"一个东西"，而是"**一个数据表 + 一堆按钮角色**"。

```
数据表（列表）：选项名称 = [开始游戏, 难度设置, 音效说明, 退出]
索引映射：     选项1=开始游戏 / 选项2=难度设置 / ...
按钮角色：     按钮1 按钮2 按钮3 按钮4（各自是独立角色，各自有美术）
```

每个按钮角色的脚本只有三行：
```yaml
- name: 按钮1
  variables:
    选项序号: 1
  costumes:
    - { name: 普通, asset: assets/btn_normal.svg }
    - { name: 高亮, asset: assets/btn_hover.svg }
  scripts:
    # ① 被点击 → 广播"选择选项"
    - - event_whenthisspriteclicked:
      - broadcast: { message: 选择选项 }
    # ② 鼠标悬停 → 切高亮造型（用克隆或造型切换）
    - - when_green_flag_clicked:
      - switch_costume: { costume: 普通 }
```

"选择选项"由**舞台**统一处理：
```yaml
- name: 舞台
  variables:
    菜单状态: 0        # 0=未开 1=主菜单 2=难度菜单 3=游戏中
    当前选项: 0
  scripts:
    - - when_receive:
          message: 选择选项
      - set_variable: { var: 当前选项, value: { var: 当前按钮序号 } }
      - broadcast: { message: 确认选项 }
```

### 77.3 ⚠️ 悬停高亮：用克隆，别用"改变造型再改回来"

**悬停高亮是新手最常做错的地方。** 直觉写法是：

```
当角色被点击 → 换高亮造型
（想改回来？）
```

问题：鼠标移开时怎么知道要换回来？加"当鼠标移出"帽子？**Scratch 没有"鼠标移出"帽子。**

**三种可行解法**：

**解法 A：造型 + 造型编号记录（最简单）**
```yaml
# 按钮角色
- - event_whenthisspriteclicked:
  - switch_costume: { costume: 高亮 }
```
点击后永久高亮，进入下一级菜单时由统一逻辑复位。

**解法 B：克隆做"高亮框"（最通用）**
```yaml
# 按钮本体
- - event_whenthisspriteclicked:
  - create_clone_of: { clone: _myself_ }
# 克隆体 = 高亮框，它自己消失
- - control_start_as_clone:
  - switch_costume: { costume: 高亮 }
  - set_ghost: { ghost: 0 }
  - wait: { secs: 0.1 }
  - delete_this_clone: null
```
⚠️ 这招的原理是：**按下鼠标的那一瞬间复制一个高亮副本**，本体不动。
纯视觉反馈，不改变游戏状态，是最稳的写法。

**解法 C：鼠标位置检测（适合"键盘/手柄"式选择）**
```yaml
- - when_green_flag_clicked:
  - forever:
      do:
        - if: { cond: { touching_mouse_pointer: { object: _mouse_ } }, do:
            [ { switch_costume: { costume: 高亮 } } ] }
        - if: { cond: { not: { operand: { touching_mouse_pointer: { object: _mouse_ } } } }, do:
            [ { switch_costume: { costume: 普通 } } ] }
```
⚠️ **「碰到鼠标指针」在 Scratch 里就是「碰到 [鼠标指针]」**，
IR 写法是 `{ touching_mouse_pointer: { object: _mouse_ } }`（下拉值必须是 `_mouse_`）。
⚠️ **`not` 必须写成 `operand:`**：`{ not: { operand: { touching_mouse_pointer: { object: _mouse_ } } } }`。
⚠️ 这个写法每帧切造型，**造型数 ≥ 3 时会闪**（Scratch 切造型有 1 帧延迟）。
建议改成"只检测到变化时才切"。

### 77.4 用键盘也能选（不只是鼠标）

社区最常见的加强版：**上下键移动高亮 + 空格确认**。
```yaml
# 舞台
- - when_key_pressed: { key: down arrow }
  - change_variable: { var: 当前选项, by: 1 }
  - if: { cond: { greater_than: [ { var: 当前选项 }, { var: 选项总数 } ] }, do:
      [ { set_variable: { var: 当前选项, value: 1 } } ]
  - broadcast: { message: 移动高亮 }
- - when_key_pressed: { key: space }
  - broadcast: { message: 确认选项 }
```

⚠️ **Scratch 3.0 的按键名**：方向键是 `up arrow` / `down arrow` / `left arrow` / `right arrow`
（带空格），**没有 Esc 键**（社区惯例是用 `P` 做暂停）。

### 77.5 层级菜单：状态机 + 广播

多级菜单（主菜单 → 难度 → 存档）用**状态变量 + 分层广播**：

```yaml
- name: 舞台
  variables:
    菜单层级: 0     # 0=主 1=难度 2=说明 3=游戏
  scripts:
    - - when_receive: { message: 打开主菜单 }
      - set_variable: { var: 菜单层级, value: 0 }
      - show: null
    - - when_receive: { message: 打开难度菜单 }
      - set_variable: { var: 菜单层级, value: 1 }
    - - when_receive: { message: 返回主菜单 }
      - set_variable: { var: 菜单层级, value: 0 }
```

每个按钮角色**只负责发意图**，不负责决定去哪：
```yaml
# 按钮「难度设置」
- - event_whenthisspriteclicked:
  - broadcast: { message: 打开难度菜单 }
```
→ **好处**：以后要改菜单流程，只改舞台的广播处理，不动按钮。

### 77.6 ⚠️ 遮罩与穿透（和第一册 §5 呼应）

如果菜单是**覆盖在游戏上**的（不是独立场景），必须：
1. 加一个**遮罩**（半透明黑色）拦截点击；
2. 菜单和遮罩要 `go to front`（置于最前）。

否则**点击会穿透**：点到菜单按钮的同时，下面的角色也被点到了。
详见第一册 §5「弹窗与当关闭被点击」。

### 77.7 IR 写法要点 ✅

| 积木 | IR 写法 |
|---|---|
| 当角色被点击 | `{ event_whenthisspriteclicked: null }` |
| 询问并等待（**不推荐**） | `{ ask: { question: 选哪个？ } }` |
| 广播 | `{ broadcast: { message: 选择选项 } }` |
| 当收到消息 | `{ when_receive: { message: 选择选项 } }` |
| 切换造型 | `{ switch_costume: { costume: 高亮 } }` |
| 碰到鼠标指针 | `{ touching_mouse_pointer: { object: _mouse_ } }` |
| 取反 | `{ not: { operand: { touching_mouse_pointer: { object: _mouse_ } } } }` |
| 置于最前 | `{ go_to_front: null }` |

> ⚠️ **无头测试盲区**：克隆体在 headless VM 里会被立刻回收，
> 所以"克隆做高亮框"只能做结构级校验，最终效果要在 Scratch 编辑器目视确认。

---

## 78. 克隆的正确用法：什么时候**不该**用克隆

第一册 §7 讲了克隆粒子系统（**怎么用**）。这一节讲**什么时候不该用**——
这才是决定作品能不能跑得动、能不能维护的关键。

### 78.1 决策树：先问自己 4 个问题

```
需要"很多个同时存在、且各自状态不同"的东西吗？
├─ 否 → 用「造型切换」（同一个角色换造型）
│        角色是弹匣里只有一颗的子弹？→ 造型
│        角色是一排血条格子？→ 造型（见第一册 §9）
│
└─ 是 → 需要各自独立运动/独立计时吗？
   ├─ 否 → 用「列表 + 编号」批量管理
   │        棋盘格子、卡牌手牌、网格地图 → 列表
   │        （见第五册 §59「数据驱动瓦片地图」）
   │
   └─ 是 → 数量 ≤ 30 且生命周期短？→ 用「克隆」
            子弹、粒子、飘字、残影 → 克隆 ✅
            数量可能上百？→ 先考虑「对象池」或「粒子用画笔」
```

### 78.2 三种"批量"的对照

| 方案 | 内存 | 独立状态 | 适用 |
|---|---|---|---|
| **造型切换** | 1 个角色 | ❌ 只有当前造型 | 血条、子弹种类少、卡牌背 |
| **列表 + 编号** | 1 个角色 + N 个列表项 | ✅（数据在列表里） | 棋盘、地图、棋局状态 |
| **克隆** | N 个角色 | ✅（私有变量） | 子弹、敌人、粒子 |

⚠️ **列表的隐藏成本**：每个列表项的读写都要 `item_of_list`，
100 个格子的棋盘每帧更新 = 100 次列表读写 + 100 次 `replace_item_of_list`（**很慢**）。
**静态数据放列表，动态实体放克隆。**

### 78.3 克隆的三个生命周期阶段

一个规范的克隆体脚本必须覆盖这三段：

```yaml
- name: 子弹
  variables:
    速度: 8
    寿命: 60
    已克隆: 0
  scripts:
    # 阶段 0：本体 —— 只负责"生产"
    - - when_green_flag_clicked:
      - hide: null
      - set_variable: { var: 已克隆, value: 0 }
    # 阶段 1：克隆 —— 出生
    - - control_start_as_clone:
      - set_variable: { var: 已克隆, value: 1 }
      - show: null
      - set_variable: { var: 寿命, value: 60 }
      - point_in_direction: 90
    # 阶段 2：克隆 —— 生存 + 消亡
    - - control_start_as_clone:
      - repeat_until: { cond: { less_than: [ { var: 寿命 }, 1 ] }, do:
          [ { change_variable: { var: 寿命, by: -1 } }
          , { move_steps: { steps: { var: 速度 } } } ] }
      - delete_this_clone: null
```

⚠️ **「克隆体也会触发本体的事件帽子」** —— 见 §75.3 的 `是克隆` 标志位。
⚠️ **本体必须 `hide`** —— 否则本体自己也会在场上乱跑。
⚠️ **本体在 `当绿旗被点击` 里不能被"生产逻辑"污染** —— 见第三册 §45.3：
「一局开始要复位」的东西挂「当收到 [重置]」，不挂绿旗。

### 78.4 克隆预算：300 是硬红线

| 数量 | 表现 |
|---|---|
| < 50 | 安全区，随便用 |
| 50–150 | 明显卡顿（尤其移动端） |
| 150–300 | 濒死，随时可能丢克隆 |
| > 300 | **Scratch 直接丢弃新克隆**（不报错！）→ 看起来像"子弹发不出去" |

⚠️ **超限不报错**是 Scratch 3.0 最坑的行为之一：
你的"发射"逻辑明明执行了，但屏幕上就是没有子弹。
**排查方法**：加一个计数器变量，每次 `create_clone_of` 前 +1，出生时 -1，
在监视器上就能看到是不是被丢了。

### 78.5 用画笔替代克隆（省资源的终极方案）

粒子有 3 万个？用画笔。

```yaml
# 撒花：用画笔 + 图章，不产生任何克隆体
- - when_green_flag_clicked:
  - repeat: { times: 50, do:
      [ { goto_xy: { x: { random: -230, 230 }, y: { random: -170, 170 } } }
      , { stamp: null } ] }
```
⚠️ 图章是**静态**的（不会动、不会消失，除非 `pen_clear`）。
所以：**要动的实体用克隆，不要动的装饰用图章**。

### 78.6 IR 写法要点 ✅

| 积木 | IR 写法 |
|---|---|
| 生成克隆体 | `{ create_clone_of: { clone: _myself_ } }` |
| 当作为克隆体启动 | `{ control_start_as_clone: null }` |
| 删除克隆体 | `{ delete_this_clone: null }` |
| 克隆"自己" | `clone: _myself_`（下拉值） |
| 克隆"其他角色" | `clone: 玩家`（角色名） |

---

## 79. 受击反馈：顿帧、闪白、击退

游戏"手感"的关键不是画面多精细，而是**被打中时的那一瞬间有没有反馈**。
这一节给出四种反馈的最小实现。

### 79.1 四种反馈的最小配方

| 反馈 | 做法 | 代码量 |
|---|---|---|
| **闪白** | `change effect [COLOR] by 50` → 归零 | 3 块 |
| **闪红** | `change effect [COLOR] by 25`（配合红色造型） | 3 块 |
| **击退** | 反方向 `move` 一点点 | 4 块 |
| **顿帧**（hitstop） | 全局 `停止` 标记 + 所有角色 `wait` | 需广播 |
| **掉血数字** | 克隆一个数字造型往上飘 | 见 §75.3 |

### 79.2 闪白 + 击退（敌人被打中）

```yaml
- name: 敌人
  variables:
    血量: 3
  scripts:
    - - when_receive:
          message: 受到攻击
      - change_variable: { var: 血量, by: -1 }
      # 闪白
      - change_effect: { effect: COLOR, value: 50 }
      - wait: { secs: 0.08 }
      - change_effect: { effect: COLOR, value: -50 }
      # 击退：朝远离玩家的方向弹一下
      - move_steps: { steps: -8 }
      # 死亡
      - if: { cond: { less_than: [ { var: 血量 }, 1 ] }, do:
          [ { broadcast: { message: 敌人死亡 } }
          , { delete_this_clone: null } ] }
```

⚠️ **`change_effect` 的 `effect` 字段值**：Scratch 3.0 用的是
`color` / `fisheye` / `whirl` / `pixelate` / `mosaic` / `brightness` / `ghost`。
IR 里写 `{ change_effect: { effect: COLOR, value: 50 } }`。
⚠️ **`move_steps` 的负数 = 后退**（沿当前朝的反方向），
所以击退要**先转向玩家**再后退，才是"被推走"而不是"往自己方向退"。

### 79.3 顿帧（hitstop）：全局暂停一小会儿

**顿帧** = 命中瞬间整个游戏"卡住" 0.05–0.1 秒，是动作游戏的灵魂。

```yaml
# 舞台
- name: 舞台
  variables:
    顿帧: 0
  scripts:
    - - when_receive:
          message: 命中
      - set_variable: { var: 顿帧, value: 6 }
    # 所有会动的角色都要检查这个标记
```
```yaml
# 玩家
- - when_green_flag_clicked:
  - forever:
      do:
        - if: { cond: { equals: [ { var: 顿帧 }, 0 ] }, do:
            [ { move_steps: { steps: 3 } } ]
            , else:
            [ { change_variable: { var: 顿帧, by: -1 } } ]
```
⚠️ **但 `顿帧` 必须是舞台级变量**（全局）才能让所有角色一起停。
⚠️ **别忘了敌人和子弹也要检查**，否则只有玩家被冻住，效果很怪。

### 79.4 命中判定放在哪：广播 vs 碰撞检测

| 方式 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| **碰撞检测** | 子弹角色 `touching 敌人?` | 直接 | 每个子弹都要检测，O(n×m) |
| **广播** | 子弹碰到敌人 → `broadcast 命中` | 简单、O(1) | 敌人不在场就收不到广播 |

社区常用**广播 + 冷却**：子弹碰到敌人 → 广播 → 敌人扣血 → 子弹删自己。

⚠️ **广播的坑**：**所有**接收该消息的角色都会响应（包括别的敌人）。
解法：广播消息里带**目标编号**（`广播 [命中] 并把 目标编号 作为参数`），
接收方检查"是不是我"。

### 79.5 IR 写法要点 ✅

| 积木 | IR 写法 |
|---|---|
| 改变外观特效 | `{ change_effect: { effect: COLOR, value: 50 } }` |
| 等待 | `{ wait: { secs: 0.08 } }` |
| 广播并带参数 | `{ broadcast_and_wait: { message: 命中 } }` 或 `{ broadcast: { message: 命中 } }` |
| 碰到某角色 | `{ touching: { object: 敌人 } }` |
| 移到某位置 | `{ goto_xy: { x: 0, y: 0 } }` |

---

## 80. 演出与转场

菜单要有开合动画、角色要有出场动画 —— 这些"演出"是让作品显得"被设计过"的关键。

### 80.1 角色出场：从屏幕外滑入

```yaml
- - when_receive:
      message: 角色登场
  - set_variable: { var: 目标X, value: 0 }
  - set_variable: { var: 目标Y, value: 0 }
  - show: null
  - goto_xy: { x: 300, y: -180 }
  - forever:
      do:
        - change_variable: { var: 当前位置X, by: { divide: [ { subtract: [ { var: 目标X }, { var: 当前位置X } ] }, 8 ] } }
        - goto_xy: { x: { var: 当前位置X }, y: { var: 当前位置Y } }
        - if: { cond: { less_than: [ { subtract: [ { var: 目标X }, { var: 当前位置X } ] }, 2 ] }, do: [ { stop: { option: this script } } ] }
```
⚠️ **`divide` 除以 8 = 缓动（每帧走剩余距离的 1/8）**，
这是"指数逼近"，永远不会精确到达 → 必须加停止条件（见上）。
⚠️ **`stop` 的选项值是英文**：`this script` / `other scripts in sprite` / `all`
（**不是** `this_block`），键名写 `option:`。

### 80.2 菜单开合动画：缩放 + 淡入

```yaml
# 菜单面板
- - when_receive:
      message: 打开菜单
  - show: null
  - set_ghost: { ghost: 100 }
  - set_size: { size: 50 }
  - repeat: { times: 12, do:
      [ { change_effect: { effect: GHOST, value: -8 } }
      , { change_size: { value: 5 } } ] }
```
⚠️ **在 headless VM 里测不出 `setSize` 的变化**（赋值写在 `if (this.renderer)` 里），
只能做结构级校验，最终效果要在编辑器目视确认。
详见第一册 §4 的说明。

### 80.3 转场：黑幕淡入淡出

比第六册/第五册的 §66 更通用的"万能转场"：用一个全屏黑幕角色。

```yaml
# 转场遮罩（全屏黑色矩形）
- - when_receive:
      message: 转场开始
  - show: null
  - go_to_front: null
  - repeat: { times: 15, do: [ { change_effect: { effect: GHOST, value: -7 } } ] }
  - broadcast: { message: 换场景完成 }
- - when_receive:
      message: 转场结束
  - repeat: { times: 15, do: [ { change_effect: { effect: GHOST, value: 7 } } ] }
  - hide: null
```
⚠️ **遮罩必须 `go_to_front`**（否则会被角色盖住）。
⚠️ **黑幕要盖满舞台**：用 `set_size` 把一个 1×1 的方块放大到 1000%（Scratch 上限 150%，
所以要用一个**本来就很大的**造型，或用画笔画一个全屏矩形）。

---

## 81. 节奏输入判定

第三册 §46 讲过节奏游戏的设计，这里补**判定窗口的实现**。

### 81.1 时间窗判定（Perfect / Good / Miss）

核心是**时间差 → 判定等级**：

```yaml
- name: 判定器
  variables:
    目标时间: 0        # 音符应该被按下的时刻（秒）
    误差: 999
  scripts:
    - - when_receive:
          message: 判定
      - set_variable: { var: 误差, value:
          { subtract: [ { timer }, { var: 目标时间 } ] } }
      # 取绝对值
      - if: { cond: { less_than: [ { var: 误差 }, 0 ] }, do:
          [ { change_variable: { var: 误差, by: { multiply: [ { var: 误差 }, -1 ] } } ] }
      # 分级
      - if: { cond: { less_than: [ { var: 误差 }, 0.1 ] }, do:
          [ { broadcast: { message: 判定Perfect } } ] }
      - if: { cond: { and: [ { greater_than: [ { var: 误差 }, 0.1 ] }, { less_than: [ { var: 误差 }, 0.25 ] } ] }, do:
          [ { broadcast: { message: 判定Good } } ] }
      - if: { cond: { greater_than: [ { var: 误差 }, 0.25 ] }, do:
          [ { broadcast: { message: 判定Miss } } ] }
```

⚠️ **`and` 只有 2 个输入**（Scratch 的逻辑积木就两个槽）。
三个条件要**嵌套**：`{ and: [A, { and: [B, C] }] }`。
⚠️ **`timer` 是从绿旗开始的秒数**，不是从某个自定义时刻。
如果游戏有暂停/重开，`timer` 不可靠 → 改用 `timer - 暂停累计时间`。

### 81.2 提前量（音符需要提前按下）

下落式音游里，音符在**到达判定线之前**就该被按下。做法：
把判定时刻设为"音符到达判定线的时刻 - 提前量"。

```
目标时间 = 音符到达时间 - 提前量(0.15)
```

⚠️ 提前量过大 → 玩家会"抢拍"，过大就变成"预判游戏"，失去节奏感。
0.1–0.2 秒是比较稳的范围。

### 81.3 连击（Combo）

```yaml
- - when_receive:
      message: 判定Perfect
  - change_variable: { var: 连击, by: 1 }
  - if: { cond: { greater_than: [ { var: 连击 }, { var: 最大连击 } ] }, do:
      [ { set_variable: { var: 最大连击, value: { var: 连击 } } } ]
- - when_receive:
      message: 判定Miss
  - set_variable: { var: 连击, value: 0 }
```
⚠️ **连击必须是私有变量还是全局变量？**
**全局**（舞台）—— 因为要跨角色累计（不同音符由不同角色判定）。
如果每个音符是独立角色并各自持有连击，就永远无法累计。

---

## 82. 广播驱动的解耦架构

### 82.1 问题：一个游戏脚本会变成什么样

如果每个角色都直接控制别的角色：

```
玩家碰到敌人 → 直接改敌人的血量变量
敌人死亡 → 直接隐藏所有子弹
子弹碰到敌人 → 直接改玩家分数
```

改成广播后：

```
玩家碰到敌人 → 广播「我被攻击了」
敌人死亡     → 广播「敌人死了」
子弹碰到敌人 → 广播「我打中了」
```

好处：**任何角色都能对任何事件作出反应**，而发送方不需要知道谁在听。

### 82.2 Scratch 广播的两个限制

| 限制 | 说明 | 应对 |
|---|---|---|
| **广播是"群发"** | 所有监听者都收到 | 消息名要具体（`敌人A死亡` vs `敌人死亡`）；或带参数校验 |
| **消息是全局的** | 角色自己发的消息，自己也会收到 | 发送方要能识别"这是我发的" |

带参数的广播（Scratch 3.0 的 `broadcast [msg] and wait` 不支持参数，
但**自定义积木可以**）：

```yaml
# 自定义积木模拟带参广播
- name: 通知 %n
  args: [目标]
  script:
    - set_variable: { var: 通知目标, value: { var: 目标 } }
    - broadcast: { message: 通知 }
# 接收方检查
- - when_receive:
      message: 通知
  - if: { cond: { equals: [ { var: 通知目标 }, { var: 我的编号 } ] }, do:
      [ ... ]
```
⚠️ **自定义积木没有返回值**（Scratch 3.0 的限制），
所以"带参数广播"要靠**全局变量**中转 —— 每个接收方读同一个 `通知目标`。
⚠️ **但全局变量中转有竞态**：如果两个通知连续发出，接收方可能读到后一个。
**更稳的办法：用不同的消息名**（`通知敌人1` / `通知敌人2`），或者**广播后立刻处理**。

### 82.3 什么时候**不该**用广播

⚠️ **广播不是越多越好**：
- 广播多了，任何角色的任何帽子都会被触发 → 性能下降 + 逻辑缠绕；
- **高频事件**（每帧的碰撞检测）不要用广播，用 `touching` 积木直接问。

**判断标准**：
| 事件类型 | 用什么 |
|---|---|
| 一次性、有明确接收者的事件（敌人死了） | ✅ 广播 |
| 高频、多接收者（每帧碰撞） | ❌ 直接 `touching` 查询 |
| 需要顺序执行（等对方做完） | `broadcast and wait` |
| 需要传数据 | 自定义积木 + 全局变量中转 |

---

## 附录：第七册积木支持对照

| 技巧 | 关键积木 | 本 skill 支持 |
|---|---|---|
| §75 拖尾 | `pen_down`/`pen_up`/`create_clone_of`/`control_start_as_clone`/`delete_this_clone`/`change_effect` | ✅ |
| §76 背景音乐 | `start_sound`/`play_sound_until_done`/`stop_all_sounds`/`set_volume`/`change_volume`/`play_note`/`set_tempo`/`set_instrument` | ✅ |
| §77 多角色选项菜单 | `event_whenthisspriteclicked`/`broadcast`/`when_receive`/`switch_costume`/`touching_mouse_pointer`/`not` | ✅ |
| §78 克隆的正确用法 | `create_clone_of`/`control_start_as_clone`/`delete_this_clone`/`stamp`/`item_of_list` | ✅ |
| §79 受击反馈 | `change_effect`/`wait`/`broadcast`/`touching`/`move_steps` | ✅ |
| §80 演出与转场 | `goto_xy`/`divide`/`change_effect`/`change_size`/`go_to_front`/`stop` | ✅ |
| §81 节奏判定 | `timer`/`subtract`/`less_than`/`greater_than`/`and`/`broadcast` | ✅ |
| §82 广播解耦 | `broadcast`/`broadcast_and_wait`/`when_receive`/自定义积木 | ✅ |

### 本册新增的 IR 约定

```yaml
# 布尔取反：必须用 operand:
{ not: { operand: { touching_mouse_pointer: { object: _mouse_ } } } }

# 外观特效：effect 字段是固定英文值
{ change_effect: { effect: COLOR, value: 50 } }
# 幽灵/大小特效用同一个积木，effect 换成 ghost / size
{ change_effect: { effect: GHOST, value: 5 } }
{ change_size: { value: 5 } }

# 停止脚本：stop 字段值是英文
{ stop: { option: this script } }
{ stop: { option: other scripts in sprite } }
{ stop: { option: all } }

# 广播并等待
{ broadcast_and_wait: { message: 换场景完成 } }

# 克隆其他角色
{ create_clone_of: { clone: 玩家 } }
```

> ⚠️ 全册「无头测试盲区」：
> - **克隆体**在 headless VM 里会被立刻回收 → 拖尾/残影/克隆菜单只能结构级校验；
> - **`setSize` 的变化**看不到（赋值写在 `if (this.renderer)` 内）→ 缩放动画只能结构级校验；
> - **音频**不播放（无 AudioContext）→ 只能结构级校验；
> - **鼠标悬停**检测不到真实指针 → 只能结构级校验。
>
> 上述四项的最终效果**必须在 Scratch 编辑器里目视确认**。
