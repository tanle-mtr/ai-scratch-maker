# 更多进阶技巧（第五册：§59–§66）

> 来源：Scratch Wiki《Switching Between Screens》《Glide（ease out）》、scratch-discuss
> 讨论帖（Tilemap / Minimap / Branching dialogue）、RottenWiFi（Minecraft 式瓦片地图）、
> Advaspire（L04 瓦片绘制）、Scratch Music 教程（音符序列器）、EducaWeb（程序化音乐）、
> Sekin.in（摄像机死区与边界）、TrueSight（工业级手感）、Scratch Coach（Dino Runner 昼夜循环）、
> ClassX（昼夜模式 / 分支剧情）、hqwc.cn（亮度特效速查 / 程序化美术）、Pinnguaq（Iris wipe 转场）等公开资料。
>
> 本册补齐「世界渲染、音频、镜头、表现层」的系统：**瓦片地图、程序化音乐、平滑摄像机、
> 缓动补间、昼夜光照、分支对话、迷你地图、过场转场**。
> 每节都给出本 skill 的 IR 写法（能直接生成 sb3 的标 ✅）。

## 速查表

| 想做什么 | 章节 |
|---|---|
| 用数据生成地图、读格子、做碰撞 | §59 数据驱动瓦片地图 |
| 用列表自动演奏整首歌、多声部 | §60 程序化音乐 / 音符序列器 |
| 镜头跟随不僵硬、有死区、不露边 | §61 平滑摄像机（deadzone + lerp） |
| 平滑移动 / 弹窗 / 大小变化有缓动 | §62 缓动与补间系统（tween） |
| 白天黑夜切换、压暗、呼吸灯 | §63 昼夜循环与动态光照 |
| 对话有选项、分支、记住玩家选择 | §64 分支对话树 |
| 右上角小地图显示玩家位置 | §65 迷你地图（mini-map） |
| 切场景黑屏淡入淡出、圆形转场 | §66 屏幕过场与转场 |

---

## 59. 数据驱动瓦片地图

### 59.1 地图是「数据」，不是图片

社区做法（RottenWiFi 的 Minecraft 式教程、boby12346 在讨论帖的总结）：
**用列表保存地图**，每一行是一个字符串，每个字符代表一格：

```
1 1 1 1 1 1 1 1 1 1
1 0 0 0 0 0 0 0 0 1
1 0 1 1 1 0 1 1 0 1
1 0 0 0 0 0 0 0 0 1
1 1 1 1 1 1 1 1 1 1
```

- `1` = 墙，`0` = 空地，可加 `2` = 门（移动逻辑里单独判断）。
- **最外圈必须是墙**，保证玩家走不出去。
- 每行字符数必须相等，否则读取会错位。

### 59.2 读某一格：用 `letter … of …`（✅ 本 skill 支持）

Scratch 列表从 1 开始，而世界坐标从 0 开始，所以要 `+1`：

```yaml
# 读 (col, row) 这一格的字符
- set_variable:
    var: 格子
    value: { letter_of: [ {var: 列}, { item_of_list: [ {var: 行}, 地图 ] } ] }
# 世界坐标 → 格子号（注意 +1）
- set_variable: { var: 列, value: { add: [ { round: { x_position } }, 1 ] } }
- set_variable: { var: 行, value: { add: [ { round: { y_position } }, 1 ] } }
```

### 59.3 渲染：嵌套循环 + stamp（必须「不刷新屏幕」）

Advaspire 教学的关键：**把整张地图的绘制放进一个「不刷新屏幕」的自定义积木**，
否则 Scratch 每画一格就刷新一次，几百格要卡好几秒。

```yaml
procedures:
  - name: 绘制地图
    warp: true          # ⚠️ 关键：Run without screen refresh
    do:
      - pen_clear: {}           # 清屏（画笔扩展）
      - set_variable: { var: 行号, value: 1 }
      - repeat: 12
          do:
            - set_variable: { var: 列号, value: 1 }
            - repeat: 16
                do:
                  - set_variable:
                      var: 字符
                      value: { letter_of: [ {var: 列号}, { item_of_list: [ {var: 行号}, 地图 ] } ] }
                  - switch_costume: { costume: {var: 字符} }   # 每个字符对应一个造型名
                  - goto_xy: { x: {var: 屏幕X}, y: {var: 屏幕Y} }
                  - stamp: {}                  # 画笔：盖个章
                  - change_variable: { var: 屏幕X, by: 30 }
                  - change_variable: { var: 列号, by: 1 }
            - change_variable: { var: 屏幕Y, by: -30 }
            - change_variable: { var: 行号, by: 1 }
```

⚠️ **造型名必须和地图字符一致**：`1` 造型 = 墙，`0` 造型 = 地板，`2` 造型 = 门。
Scratch 的 `switch costume to (letter …)` 会自动找同名造型。

### 59.4 摄像机偏移（大地图滚动）

```yaml
# 屏幕坐标 = 世界坐标 − 摄像机坐标
- set_variable: { var: 屏幕X, value: { subtract: [ {var: 世界X}, {var: 摄像机X} ] } }
- set_variable: { var: 屏幕Y, value: { subtract: [ {var: 世界Y}, {var: 摄像机Y} ] } }
```

⚠️ **玩家移动用世界坐标，显示时才减摄像机**。
别用 `change x by` 当世界移动 —— 否则摄像机滚动时角色会「漂」。

⚠️ **碰撞箱判定也要读格子**：玩家想移动时，先算目标格字符，是 `1` 就不动。
画在背景图里的家具**挡不住人**（「碰到」只认角色），所以一切实体碰撞都得走瓦片数据。

---

## 60. 程序化音乐 / 音符序列器

### 60.1 把一首歌拆成两个列表

EducaWeb / Scratch Music 教程的通用做法：一个**音符列表** + 一个**时值列表**，
循环播放。音符编号 60 = 中央 C（do），67 = sol，57 = 低音 mi，以此类推。

```yaml
# stage.lists（或任一角色）：
#   旋律音符 = [60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60]
#   旋律时值 = [0.5,0.5,0.5,0.5,0.5,0.5,1,  0.5,0.5,0.5,0.5,0.5,0.5,1]
```

### 60.2 播放引擎（✅ 本 skill 支持音乐扩展）

```yaml
- - when_green_flag_clicked:
    - set_instrument: { instrument: 1 }     # 1 = 钢琴
    - set_tempo: { tempo: 120 }             # 速度（bpm）
    - broadcast: { message: 演奏列表旋律 }
- - when_receive: { message: 演奏列表旋律 }
    - set_variable: { var: i, value: 1 }
    - repeat: { length_of_list: 旋律音符 }      # 循环次数 = 列表项目数
        do:
          - play_note:                        # ✅ music_playNoteForBeats
              note: { item_of_list: [ {var: i}, 旋律音符 ] }
              beats: { item_of_list: [ {var: i}, 旋律时值 ] }
          - change_variable: { var: i, by: 1 }
```

⚠️ `play_note` / `set_tempo` / `set_instrument` 来自**音乐扩展**，本 skill 已支持
（`music_playNoteForBeats` / `music_setTempo` / `music_setInstrument`）。

### 60.3 多声部：每个角色各放一个旋律列表

让「钢琴声部」和「鼓声部」**同时**广播开始，它们各自循环自己的列表。
鼓声部用 `play_drum`（✅ `music_playDrumForBeats`）：

```yaml
- play_drum: { drum: 2, beats: 0.25 }       # 2 = 底鼓
```

⚠️ **Scratch 同时发声的音符约 20 个**：太密的和弦或太多克隆体会被切掉部分声音。
声部要克制。切换段落时用 `stop_all_sounds`（✅ `sound_stopallsounds`）清理残留。
⚠️ **休止符**：时值给 0 不够自然，直接用 `rest`（✅ `music_restForBeats`）。

---

## 61. 平滑摄像机（deadzone + lerp + 夹紧）

### 61.1 别让镜头坐标 = 角色坐标

TrueSight 的「工业级手感」第一条：**用线性插值（lerp）**，让镜头有轻微滞后与弹性：

```yaml
# 每帧：摄像机的 X 朝目标靠近一点，系数 0.1 = 平滑、0.02 = 很黏
- set_variable:
    var: 摄像机X
    value:
      add:
        - {var: 目标X}
        - multiply: [ { subtract: [ {var: 目标X}, {var: 摄像机X} ] }, -0.1 ]
```

拆解：`新 = 旧 + (目标 − 旧) × 0.1` 等价 `旧 + (旧−目标)×−0.1`。

### 61.2 死区（dead zone）：玩家先走，镜头再跟

Sekin.in 的做法：玩家在屏幕 ±100 内移动时镜头不动，超出边界才修正：

```yaml
- if:
    cond: { greater_than: [ { subtract: [ {var: 世界X}, {var: 摄像机X} ] }, 100 ] }
    do:
      - set_variable:
          var: 摄像机X
          value: { subtract: [ {var: 世界X}, 100 ] }    # 把世界X 拉回死区右边界
- if:
    cond: { less_than: [ { subtract: [ {var: 世界X}, {var: 摄像机X} ] }, -100 ] }
    do:
      - set_variable:
          var: 摄像机X
          value: { add: [ {var: 世界X}, 100 ] }          # 拉回死区左边界
```

### 61.3 夹紧：镜头不能露出地图外

```yaml
- if:
    cond: { less_than: [ {var: 摄像机X}, 0 ] }
    do:
      - set_variable: { var: 摄像机X, value: 0 }
- if:
    cond: { greater_than: [ {var: 摄像机X}, {var: 摄像机X最大值} ] }
    do:
      - set_variable: { var: 摄像机X, value: {var: 摄像机X最大值} }
```

⚠️ **摄像机最大值 = 世界宽 × 瓦片尺寸 − 舞台宽**（默认舞台 480×360，半宽 240）。
⚠️ **所有实体（敌人、道具、子弹）都用世界坐标存储，显示时 `go to x: (世界X − 摄像机X)`**，
克隆体出生时要先把自己的世界坐标从关卡数据里读好（见 §59）。

---

## 62. 缓动与补间系统（tween / ease）

### 62.1 Scratch 的 `glide` 是线性的（无 ease）

Scratch Wiki 明确指出：`glide` 积木是**纯线性**补间，不会缓入缓出。要「靠近目标时减速」得自己写。

### 62.2 ease-out（靠近时减速）

社区最通用的 smooth block：每帧移动**剩余距离的 1/n**，越近走得越慢：

```yaml
define 缓动到 { 目标x } { 目标y }         # 自定义积木，warp: false
  repeat until { equals: [ { round: { x_position } }, {var: 目标x} ] }
    do:
      - change_x: { dx: { divide: [ { subtract: [ {var: 目标x}, { x_position } ] }, 2 ] } }
      - change_y: { dy: { divide: [ { subtract: [ {var: 目标y}, { y_position } ] }, 2 ] } }
      - goto_xy: { x: { x_position }, y: { y_position } }
```

### 62.3 ease-in（起步慢、后段加速）

把除数做成**逐帧增大**的变量：

```yaml
define 缓入到 { 目标x } { 目标y }
  set_variable: { var: 系数, value: 1 }
  repeat until { equals: [ { round: { x_position } }, {var: 目标x} ] }
    do:
      - change_variable: { var: 系数, by: 0.1 }
      - change_x: { dx: { divide: [ { subtract: [ {var: 目标x}, { x_position } ] }, {var: 系数} ] } }
      - goto_xy: { x: { x_position }, y: { y_position } }
```

### 62.4 ease-in-out（贝塞尔，RokCoder 公式）

```yaml
define 缓入缓出 { 起点x } { 起点y } { 终点x } { 终点y } { 秒数 }
  set_variable: { var: 步数, value: { multiply: [ {var: 秒数}, 30 ] } }   # 30 fps
  set_variable: { var: t, value: 0 }
  set_variable: { var: dt, value: { divide: [ 1, {var: 步数} ] } }
  repeat: {var: 步数}
    do:
      # v = t²·(3 − 2t)  —— 经典 smoothstep
      - set_variable:
          var: v
          value:
            subtract:
              - { multiply: [ { multiply: [ {var: t}, {var: t} ] }, 3 ] }
              - { multiply: [ 2, { multiply: [ {var: t}, {var: t} ] } ] }
      - set_variable: { var: t, by: {var: dt} }
      - goto_xy:
          x: { add: [ {var: 起点x}, { multiply: [ { subtract: [ {var: 终点x}, {var: 起点x} ] }, {var: v} ] } ] }
          y: { add: [ {var: 起点y}, { multiply: [ { subtract: [ {var: 终点y}, {var: 起点y} ] }, {var: v} ] } ] }
```

⚠️ **算术运算只有 2 个输入槽**（见 §19 铁律 7）：公式里 `t²·(3−2t)` 必须**嵌套**，
写平了 `{subtract:[a,b,c]}` 第 3 项会被静默丢掉。
⚠️ **自定义积木要勾「不刷新屏幕」**才会瞬间算完；否则会一帧一帧卡给你看。
⚠️ 最后 `round` 后 `go to` 一次，防止停在非整数坐标上抖动。

---

## 63. 昼夜循环与动态光照

### 63.1 覆盖层 + 特效：最省事的做法

ClassX / hqwc.cn 的做法：画一个**覆盖全屏的黑色矩形**精灵，用 **ghost 特效**或 **brightness 特效**压暗：

```yaml
# 黑幕精灵：夜晚 = 压暗，白天 = 透明
- set_ghost: { ghost: 50 }        # 50 = 半透明夜幕；100 = 完全透明（白天）
- set_effect: { effect: brightness, value: -60 }   # brightness -100=纯黑，0=正常
```

⚠️ **覆盖层要 `go to front layer`（置最前层）**，否则压不住别的角色。

### 63.2 平滑过渡：每帧微调一点点

Scratch Coach（Dino Runner）的做法：不要瞬间切，而是每帧 `change brightness by -4` 直到 -100，
过渡就很顺。用「灯光强度」变量更可控（hqwc.cn 的呼吸灯做法）：

```yaml
# 夜晚：每帧把灯光强度往 -100 推一点
- repeat until { less_than: [ {var: 灯光强度}, -96 ] }
    do:
      - change_variable: { var: 灯光强度, by: -4 }        # ✅ 朝 -100 压暗
      - set_effect: { effect: brightness, value: {var: 灯光强度} }
      - wait: { secs: 0.1 }
# 白天：每帧往 0 推回来
- repeat until { greater_than: [ {var: 灯光强度}, -4 ] }
    do:
      - change_variable: { var: 灯光强度, by: 4 }
      - set_effect: { effect: brightness, value: {var: 灯光强度} }
      - wait: { secs: 0.1 }
```

### 63.3 用 brightness 做昼夜，比重画夜景背景省力

hqwc.cn 的「程序化美术」速查：
- **亮度** −100~100：负值压暗、正值变亮，做呼吸灯 / 夜间模式 / 压暗背景。
- **颜色** 0~200：改变色相（200 与 0 相同，色环循环），做黄昏 tint、受伤变红。
- **虚像** 0~100：越大越透明，做渐隐、幽灵、拖尾消散。

⚠️ **「将特效增加」和「将特效设定为」别混用**，否则调不回来。
⚠️ 想要「开局自动定昼夜」：用 `current [小时]`（✅ `sensing_current`）读真实时钟，
`小时 > 5 且 < 18` 算白天（Scratch Coach 的玩法，把玩家现实生活变成了游戏氛围）。

---

## 64. 分支对话树

### 64.1 选项 = 按钮 + 广播

iD Tech / ClassX 的「选择你自己的冒险」做法：每个选项是**一个按钮精灵**，点击就广播：

```yaml
# 选项A 按钮：被问到时显示，点击就广播自己的选择
- - when_receive: { message: 提问1 }
    - show: {}
- - when_this_sprite_clicked:
    - broadcast: { message: 选了A }
    - hide: {}
```

⚠️ **广播名必须大小写完全一致**：「选了A」≠「选了a」≠「 选了A」（多了空格也不行）。
拼错不会报错，只是接收方永远不响应 —— 这是新手最常见的「对话卡死」原因。

### 64.2 节点跳转：用背景切换 / 变量

```yaml
# 舞台：收到选择 → 切背景 + 推进剧情
- - when_receive: { message: 选了A }
    - switch_backdrop: { backdrop: 森林 }
    - broadcast: { message: 森林问题 }      # 进入下一层提问
```

### 64.3 记住玩家选择、多次对话不一样

TechClass4Kids 的做法：用变量记录交互次数与历史选择：

```yaml
- when_receive: { message: 和铁匠对话 }
    - change_variable: { var: 已对话次数, by: 1 }     # 私有变量
    - if:
        cond: { equals: [ {var: 已对话次数}, 1 ] }
        do:                             # 第一次：问「你喜欢鱼吗？」
          - ask: { question: 你喜欢鱼吗？ }   # ✅ sensing ask（需先开麦克风权限/在编辑器内）
    - else:
        - if:                           # 之后：根据上次回答说不同的话
            cond: { equals: [ {var: 鱼回答}, 是 ] }
            do:
              - say: { message: 上次你说喜欢鱼，这桶鱼便宜卖你！, secs: 2 }
              - ask_and_wait: { question: 要来一桶吗？ }   # ✅ sensing_askandwait（无独立 ask 积木，用并等待版）
```

⚠️ **对话要轮流说**：用 `广播并等待`（✅ `broadcast_and_wait` → `event_broadcastandwait`）而不是普通 `broadcast`，
否则两个角色同时开口像吵架（微信小程序那篇教程的「NG 镜头 3」）。
⚠️ `ask` / `ask and wait`（✅ `sensing_askandwait`）积木在无头/嵌入环境可能不可用，纯点击选项（广播）更稳。

---

## 65. 迷你地图（mini-map）

### 65.1 世界坐标 → 缩放 + 偏移

Scratch 讨论帖（deck26 / LeadToGold）的统一公式：

```
小地图X = minimap左边界 + (世界X − 世界左边界) × 缩放
小地图Y = minimap上边界 + (世界Y − 世界上边界) × 缩放
```

缩放 = `minimap宽 / 世界宽`。比如世界 480 宽、minimap 100 宽 → 缩放 100/480 = 5/24。

```yaml
- set_variable:
    var: 小地图X
    value:
      add:
        - 150                                  # minimap 左上角屏幕 X
        - { multiply: [ { add: [ { x_position }, 240 ] }, 0.208 ] }   # (世界X+240)×缩放
- set_variable:
    var: 小地图Y
    value:
      add:
        - 90                                   # minimap 左上角屏幕 Y
        - { multiply: [ { add: [ { y_position }, 180 ] }, 0.25 ] }
- goto_xy: { x: {var: 小地图X}, y: {var: 小地图Y} }   # 指针角色永远跟着玩家缩放位置
```

### 65.2 坑

⚠️ **原点必须对齐**：minimap 的左上角要对应世界坐标的原点，否则指针会偏。
⚠️ 指针角色要 `go to front layer`，盖在地图图片**上面**（deck26 强调 Z 序）。
⚠️ 缩放系数要同时作用于 X 和 Y，且 Y 方向可能因舞台「下为负」需要单独调偏移，靠运行里微调。
⚠️ 想显示多个实体（敌人/宝箱）？每个都按同一公式算一个独立指针，别共用变量。

---

## 66. 屏幕过场与转场

### 66.1 黑屏淡入淡出（最稳）

Scratch Wiki《Switching Between Screens》的标准做法：一个黑屏精灵，ghost 从 100→0 再 0→100：

```yaml
- - when_receive: { message: 转场 }
    - go_to_front: { front_back: front }        # ✅ looks_gotofrontback，置最前层
    - set_ghost: { ghost: 100 }                 # 先全透明（looks_setghostto）
    - show: {}
    - repeat: 20
        do:
          - set_effect: { effect: ghost, value: 95 }   # 渐显？不——应是 change，见下
    - switch_backdrop: { backdrop: 新场景 }     # 看不见时换场景
    - repeat: 20
        do:
          - set_ghost: { ghost: 0 }             # 再亮起来
    - hide: {}
```

⚠️ 上面第 8 行应写成 `change_effect: { effect: ghost, value: -5 }`（每帧 -5，20 次到 0 全黑），
而不是 `set_effect` 写死 95。**渐变必须用「改变」积木逐步调**，一次性 set 没有过渡。
完整正确版：

```yaml
- repeat: 20
    do:
      - change_effect: { effect: ghost, value: -5 }   # 100 → 0，全黑
- switch_backdrop: { backdrop: 新场景 }
- repeat: 20
    do:
      - change_effect: { effect: ghost, value: 5 }    # 0 → 100，亮起
```

### 66.2 圆形转场（iris wipe）

Pinnguaq / RootAndStem 的做法：用一个「实心黑矩形 + 中间挖洞」造型，靠 **size** 缩放做开合。
⚠️ **Scratch 限定 sprite 最大尺寸 = 舞台对应维度的 150%**（即宽 ≤ 720、高 ≤ 540），
所以做大圆要先切到**极小的「Tiny Hack」造型**去设/改 size（换大造型不会重置 size），
做完再换回 Iris 造型。

```yaml
# iris wipe in（圆从一点张开）：
- set_size: { size: 100 }
- go_to_front: { front_back: front }
- switch_costume: { costume: 实心黑 }
- repeat: 50
    do:
      - switch_costume: { costume: 小洞 }        # 切小造型突破 150% 上限
      - change_size: { size: 45 }                # 放大（负方向缩小则是 wipe out）
      - switch_costume: { costume: 洞 }
```

### 66.3 通用坑

⚠️ **转场时对话/动画必须用「广播并等待」**，否则场景换了角色还在念上一句。
⚠️ 黑屏精灵要 `go to front layer` 且**覆盖整个舞台**（比舞台大一圈），否则露边穿帮。
⚠️ 滑动转场同理：一个比舞台大的黑色矩形，用 `glide` 从左滑到右。
⚠️ 转场精灵**不要**放在会被场景逻辑 `hide` 的角色列表里，它只受转场脚本控制。

---

## 附录：本册用到的积木速查

| 功能 | IR 写法 |
|---|---|
| 读字符串某字符 | `{ letter_of: [ 列, { item_of_list: [ 行, 地图 ] } ] }` |
| 播放音符 | `{ play_note: { note: 60, beats: 0.5 } }`（音乐扩展） |
| 设乐器/速度 | `{ set_instrument: { instrument: 1 } }` / `{ set_tempo: { tempo: 120 } }` |
| 置最前层 | `{ go_to_front: { front_back: front } }` |
| 缓动/特效 | `{ set_effect: { effect: ghost, value: 50 } }` / `{ change_effect: { effect: brightness, value: -4 } }` |
| 提问 | `{ ask_and_wait: { question: … } }` |
| 切换背景 | `{ switch_backdrop: { backdrop: 森林 } }` |
| 圆形转场 | `set_size` + 切小造型突破上限 |
