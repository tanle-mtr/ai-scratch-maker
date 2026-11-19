# IR 模式库（Reusable IR Patterns）

> 把高频结构抽成「可抄模板」。AI 直接套模板，少写错、风格更统一。
> 下面每一段都是**可粘贴的 IR 片段**（YAML），按本 skill 的 `build_sb3.py` 语法；
> `cond`/`do`/`else` 与所有运算积木的写法见 `ir_schema.py` 与 `SKILL.md` 速查表。
> 每个模式都标注了它服务的铁律 / 手册章节，方便溯源。

---

## P1 · 状态机主循环（标题 → 游戏 → 暂停 → 结算）

核心：用 `游戏状态` 变量驱动；**一切「一局开始要复位的东西」挂 `[重置]` 广播，绝不挂绿旗**（铁律6 / §45）。

```yaml
角色: 主控
scripts:
  - 当绿旗被点击:
      - broadcast: 重置
      - set_variable: { var: 游戏状态, value: "标题" }
  - 当接收到 重置:
      - set_variable: { var: 游戏状态, value: "标题" }
      - set_variable: { var: 分数, value: 0 }
      - set_variable: { var: 生命, value: 3 }
  - 当接收到 开始游戏:
      - set_variable: { var: 游戏状态, value: "游戏" }
  - 当接收到 结束:
      - set_variable: { var: 游戏状态, value: "结算" }
      # 结算页显示后，靠「再来一局」按钮再 broadcast 重置 + 开始游戏（铁律7）
  - 当接收到 帧:                       # 统一帧节拍，所有角色订阅同一广播
      - if: { cond: {equals:[{var:游戏状态},"游戏"]}, do:[ ...玩法更新... ] }
```

要点：菜单/暂停/结算只改 `游戏状态` 变量，不打断别人脚本（§45）；`帧` 广播由舞台统一发、各角色订阅，避免各算各的节拍（§35 计时器节拍同理）。

---

## P2 · 物理积分循环（vy + 重力 + 地面 + 碰撞回退）

核心：存**速度变量**做欧拉积分，**不要** `change y by 5` 式瞬移（§2 平滑移动）；重力与加速度用「加/减」，摩擦/阻尼一律用「乘」（铁律5 / §49）。

```yaml
  - 当接收到 帧:
      - if: { cond: {equals:[{var:在地面},0]}, do:[
          - change_variable: { var: vy, by: {var:重力} }     # 重力为负（铁律8：y+ 朝上取负）
        ] }
      - change_variable: { var: 玩家y, by: {var:vy} }
      # 地面/障碍碰撞回退：先算目标位置，越界就回退并把 vy 清零
      - if: { cond: {greater_than:[{var:玩家y},{var:地面y}]}, do:[
          - set_variable: { var: 玩家y, value: {var:地面y} }
          - set_variable: { var: vy, value: 0 }
          - set_variable: { var: 在地面, value: 1 }
        ] }
```

进阶手感（已在 `platformer.yaml` 落地，探针安全）：土狼时间 + 跳跃缓冲（§17）、可变跳跃高度（松开跳键把 `vy *= 0.4`）、落地挤压拉伸（`拉伸` 变量驱动 `set_size`），震屏只动**绘制坐标**不碰状态量（详见 `creation-playbook.md` §9）。

---

## P3 · UI 按钮（克隆体 + 私有变量挡本体事件）

核心：克隆体必须用**私有变量** `是克隆` 挡住本体事件帽，否则指数级爆炸（铁律11）；四态换造型不缩放、pressed 渐变反转（铁律17）；菜单用角色按钮而非「询问」（铁律10）。

```yaml
角色: 按钮_开始
scripts:
  - 当绿旗被点击:
      - set_variable: { var: 是克隆, value: 0 }
  - 当角色被点击:
      - if: { cond: {equals:[{var:是克隆},0]}, do:[ - broadcast: 开始游戏 ] }
  - 当接收到 帧:
      - if: { cond: {equals:[{var:是克隆},1]}, do:[
          - if: { cond: {touching:{object:_mouse_}}, do:[ 换 pressed 造型 ], else:[ 换 normal 造型 ] }
        ] }
```

---

## P4 · 音频四层（ui / fx / ev / amb 响度 + 渐变 + 首尾归零）

核心：四层响度（ui≈-18 / fx≈-9 / ev≈-3 / amb≈-15 dBFS，层间 6–9 dB）、UI 音效 ≤0.25s、首尾归零、DC<0.01、音高方向=语义；**UI 音效禁止「播放声音直到结束」**；BGM 直接挂（铁律18 / §263–§276）。

```yaml
角色: 音频总线
scripts:
  - 当接收到 点击UI:
      - change_effect: { effect: PAN, by: 0 }          # 占位：实际由 gen_audio 控制响度
      - broadcast: 播放_ui_音效                       # 克隆跑音效避免抢占（§39）
  - 当绿旗被点击:
      - broadcast: 播放BGM                            # BGM 用 play sound until done（§39）
```

落地：音效文件用 `gen_sfx_kit.py`（22 音效）与 `gen_audio.py <mood>`（BGM），复用 `examples/assets/audio/*`，不要外链。

---

## P5 · 相机 Lerp 跟随（只动绘制坐标，不碰状态量）

核心：镜头用变量 `镜头x`，角色**绘制位置** = `玩家x - 镜头x`；做相机平滑时**只改绘制坐标，不改 `镜头x` 本身**，否则深网探针（`镜头x == 玩家x - 160`）失准。

```yaml
  - 当接收到 帧:
      - set_variable: { var: 镜头x, value: {add:[{var:镜头x},{multiply:[{subtract:[{var:玩家x},{var:镜头x},{var:160}]},0.1]}]} }
      - goto_xy: { x: {subtract:[{var:玩家x},{var:镜头x}]}, y: {var:玩家y} }
```

---

## P6 · 克隆生命周期（私有 vx/vy + 离屏即删 + 上限 300）

核心：粒子/子弹用克隆，速度必须**私有变量**（§7）；任务完成（飞出屏/被击中/寿命到）**立即删除此克隆**，绝不留隐形无限循环克隆（LitterBox「Missing Termination」臭味）；**静默上限 300**（铁律12）。

```yaml
角色: 火花
scripts:
  - 当接收到 生成火花:
      - create_clone_of: 火花
  - 当本角色被点击: []                       # 占位避免裸脚本
  - 当作为克隆体启动时:
      - set_variable: { var: vx, value: {random:{from:-5,to:5}} }   # 私有
      - set_variable: { var: vy, value: {random:{from:2,to:6}} }
      - forever:
          - change_variable: { var: x, by: {var:vx} }
          - change_variable: { var: y, by: {var:vy} }
          - change_variable: { var: vy, by: -0.3 }                  # 重力
          - change_effect: { effect: GHOST, by: 8 }                 # 渐隐
          - if: { cond: {greater_than:[{var:虚像},95]}, do:[ - delete_clone_of: 火花 ] }
          - if: { cond: {or:[{less_than:[{var:x},-260]},{greater_than:[{var:x},260]}]}, do:[ - delete_clone_of: 火花 ] }
          - wait: 0.02
```

---

## P7 · 碰撞检测收窄（移动子弹检测敌人，非两两）

核心：角色多时，频繁 `碰到` 两两检测会卡；**只让移动的子弹去检测敌机**，敌人之间不互检（§33）。用 `abs(dx)<R and abs(dy)<R` 在无头环境也能测（铁律相关性能铁律14）。

```yaml
角色: 子弹
scripts:
  - 当接收到 帧:
      - if: { cond: {touching:{object:敌人}}, do:[ - broadcast: 击中敌人, - delete_clone_of: 子弹 ] }
```

---

## P8 · 手感层 juice（声明式，编译期自动展开，跳不过去）

治「手感糙」的根本手段：**不靠 AI 自觉写效果积木**。在 IR 顶层写 `juice:` 列表，
构建器 `expand_juice` 自动把每条规则展开成真实积木（挤压拉伸 / 白闪 / 震屏），挂在
目标角色的 `当接收到 <trigger>` 帽下。三个模板骨架已内置，脚手架复制出来的作品自带手感。

```yaml
juice:
  - sprite: 挡板          # 受影响的角色（必须已存在）
    trigger: 加分         # 触发广播（键名用 trigger，别用 on——YAML 1.1 把 on 当布尔 True）
    squash: 18            # 挤压拉伸幅度(%)，快速放大再回弹，制造打击感
    shake: 4              # 震屏幅度(px)，短暂随机抖动（持续被重定位的角色自行归位）
  - sprite: 结算页
    trigger: 通关
    squash: 20
    flash: 40             # 白闪幅度(BRIGHTNESS)，短暂提亮再还原
```

字段：`sprite`(目标角色名) · `trigger`(广播名) · `squash`(挤压%) · `flash`(白闪) · `shake`(震屏)。
> 注意：`trigger` 误写成 `on` 会被 YAML 解析成布尔 `True`，导致规则静默失效；构建器已兼容 `True` 键，但仍建议用 `trigger`。

---

## P9 · 帧动画（声明式 animations:，编译期自动展开多帧切换）

核心：**不靠 AI 自觉切造型**。在 sprite 下声明 `animations:`，构建器 `expand_animations`
自动注入私有变量 `动画帧` / `动画上一状态` 和列表 `动画序列`，并生成两段绿旗脚本——
**状态机**（检测驱动变量 `状态` 变化时才重建序列）+ **翻帧器**（按 `fps` 每 `1/fps` 秒推进
帧、用 `item_of_list` 按名切造型）。`looks_switchcostumeto` 原生支持按造型名字符串切换，
所以"按计算值切造型"是合法路径，无需手写一堆 `如果…切换造型`。

```yaml
角色: 玩家
costumes:                                    # 必须是多个造型，且名字与动画引用一致
  - name: idle
    asset: assets/player_frames/idle.svg
  - name: walk1
    asset: assets/player_frames/walk1.svg
  - name: walk2
    asset: assets/player_frames/walk2.svg
  - name: jump
    asset: assets/player_frames/jump.svg
variables:
  状态: 待机                                  # 驱动变量，初值取某个状态名
animations:                                   # 声明式：驱动变量 + 状态名 -> 造型序列
  var: 状态                                   # 驱动动画切换的变量（必须已声明）
  fps: 12                                     # 翻帧频率（秒/帧 = 1/fps）
  states:
    待机: [idle]
    走:   [walk1, walk2]                       # 多帧循环
    跳:   [jump]
scripts:
  - 当接收到 帧:
      # 在物理更新后设置 状态，expand_animations 的展开脚本会据此自动翻帧
      - if: { cond: {not:{operand:{equals:[{var:在地面},1]}}}, do:[
          - set_variable: { var: 状态, value: 跳 }
        ], else:[
          - if: { cond: {not:{operand:{equals:[{var:方向键},0]}}}, do:[
              - set_variable: { var: 状态, value: 走 }
            ], else:[
              - set_variable: { var: 状态, value: 待机 }
            ] }
        ] }
```

展开后等价脚本（构建器已自动生成，无需手写）：
- 状态机：`当绿旗` → `set 动画上一状态 ""` → `forever` → `if not(状态 == 动画上一状态)`：
  `delete_all_of_list 动画序列` + 各 `if 状态==X add_to_list 动画序列 [X的造型…]` + `set 动画上一状态 状态`。
- 翻帧器：`当绿旗` → `forever` → `wait 1/fps` → `change 动画帧 by 1` →
  `if length_of_list 动画序列 > 0`：`switch_costume costume: item_of_list 动画序列 index: (动画帧 mod 长度)+1`。

要点与约束：
1. **造型必须先齐备**：`states` 里引用的每个造型名必须存在于该角色 `costumes`，否则该状态被跳过并告警（不会崩，但那一段不播）。
2. **一角色多帧必须同风格**（§198 观感铁律）：同描边色、同调色板、同体积感，否则观感撕裂。
   `examples/assets/player_frames/*.svg` 由生成脚本统一产出（黄脸 + 绿身 + 浅绿四肢 + 中性灰描边 `#4F4A47`），保证一致。
3. **驱动变量初值**取某个状态名；未声明时构建器自动补建（初值 = 首个状态）。
4. **精灵表切片**：手头是网格精灵表（一张图含多帧）时，用 `scripts/slice_sheet.py` 切出单帧再接 IR：
   ```bash
   python scripts/slice_sheet.py --sheet sheet.png --cols 4 --rows 1 \
       --out-dir assets/frames --prefix run --names run0,run1,run2,run3 \
       --var 状态 --states "跑:run0,run1,run2,run3" --fps 12
   ```
   支持 `跑:0..5`（整数帧范围）与 `跑:run0..run5`（名称范围，按帧列表定位）；`--ir-out` 可直接吐出可粘贴的 `costumes:` + `animations:` 片段。
5. **状态机只在变化时才重建列表**，所以翻帧器与状态机解耦：即使某帧内 `状态` 多次被设成同一值，序列不会反复重建，避免掉帧。

---

## 何时抽成「自制积木 / 子程序」

IR 没有 `define` 语法时，把重复逻辑抽成**独立角色的一次性脚本 + 广播调度**（如「生成一波敌人」「播放得分动画」），主脚本只需广播触发，可读性高、易维护（CS50 评分也看重「自制积木/模块化」）。
命名用描述性中文（变量/广播/角色一致），初始化与复位集中在 `当绿旗` + `当接收到 重置`，每角色只管一类关注点（§「角色即模块」）。

> 这 9 个模式覆盖了 80% 作品的骨架。先套模板跑通，再在观感层（P2 手感 / P4 音频 / P6 粒子 / P8 juice / P9 帧动画）做差异化打磨。
