# 进阶 Scratch 技巧手册（第一册：核心技巧）

> **第二册**见 `game-systems.md`（§16–§42）：敌人 AI / 平台跳跃物理 / 打击感 /
> 网格移动 / 克隆分身 / 背包商店 / 随机迷宫 / 存档进度 / 教学引导 / 数学工具箱。
>
> 来源：Scratch Wiki（中文/英文）、MIT Scratch 帮助中心与社区指南、scratch-discuss 论坛、
> Scratch Wiki "Using Clones for Particle Effects"、"Car Race Game III"（Advaspire 教程）、
> Scratch 3D 恐怖游戏与美术攻略（hqwc.cn）、TrueSight 避坑指南、
> ItsMyBot 阴影教学、Griffpatch 多点触控教程、Cognito Coding 状态机文章等公开资料。
>
> 本文件把社区里验证过的进阶做法沉淀成「可直接照抄」的配方。
> **每节都标注了本 skill 的 IR 写法**（能直接生成 sb3 的标 ✅，需在 Scratch 里手工补的标 ✍）。

---

## 速查：想做什么 → 看哪节

| 需求 | 章节 | IR |
|---|---|---|
| 世界比舞台大、想滚动 | §1 大地图 + 小地图 | ✅ |
| 角色移动生硬、没有惯性 | §2 平滑移动 | ✅ |
| 逻辑乱、加新模式就崩 | §3 开关设计（状态机） | ✅ |
| 恐怖氛围、手电筒、只能看见一小块 | §4 视野阴影与光照 | ✅ |
| 设置面板、帮助弹窗、想点右上角 × 关掉 | §5 弹窗与「当关闭被点击」 | ✅ |
| 担心作品被抄、想留署名 | §6 防搬作品（合规做法） | ✅ |
| 爆炸、火花、烟雾、尾迹 | §7 克隆粒子系统 | ✅ |
| 手机上也能玩、要做屏幕按钮 | §8 触屏适配与虚拟摇杆 | ✅ |
| 血条、体力条、进度条 | §9 血条 / 进度条 | ✅ |
| 多关卡、想改关卡配置表 | §10 关卡系统：列表当数据表 | ✅ |
| 跳跃、弹跳、落地、斜坡 | §11 缓动与物理 | ✅ |
| 静音、音量渐变、切歌 | §12 音频控制 | ✅ |
| 角色要有影子、层次不清 | §13 投影与遮挡层次 | ✅ |
| 手机卡顿、画面花屏 | §14 性能红线 | — |
| **玩家穿墙、障碍物没反应** | **§15 碰撞箱与障碍物** | ✅ |

---

## 1. 大地图 + 小地图（滚动世界）

### 问题
Scratch 舞台固定 480×360，但很多游戏世界比舞台大（大地图、迷宫、开放场景）。
做法不是把舞台变大，而是**让世界「滚动」**：角色基本不动，背景/地图反向移动，
制造「相机跟着走」的错觉。

### 核心概念：相机变量
- 用两个全局变量 `camera_x` / `camera_y` 表示「当前屏幕中心对应的世界坐标」。
- 世界坐标约定：x∈[-W/2, W/2]，y∈[-H/2, H/2]（中心为原点，y 向上）。
- **渲染公式**（每个实体每帧执行）：
  - 地图精灵：`go to x: (0 - camera_x) y: (0 - camera_y)`
  - 任意实体：`go to x: (世界x - camera_x) y: (世界y - camera_y)`
  - 于是「世界点 P」总显示在屏幕 `(P - 相机)` 处。

### 相机跟随（含边界夹紧 + 缓动）
- 世界比屏幕大，相机不能无限走，要夹紧在 `[±(W/2 - 240), ±(H/2 - 180)]`：
  ```
  set [目标x v] to (cat_wx)
  if <(cat_wx) > [240]> then set [目标x v] to [240]
  if <(cat_wx) < [-240]> then set [目标x v] to [-240]
  ```
- **平滑相机**（缓动，避免生硬）：
  ```
  set [camera_x v] to ((camera_x) + (((目标x) - (camera_x)) * (0.15)))
  ```
  0.15 是「跟随系数」，越大跟得越紧、越小越拖尾。
- ⚠️ 夹紧值按 **舞台尺寸** 算，不是世界尺寸：480 宽的舞台 → 240；360 高 → 180。

### 小地图（minimap）
- 一张缩小的世界底图（比例 `m = 底图宽 / 世界宽`，如 120/960 = 0.125）。
- 用一个**始终置顶**的角色显示底图，再放两个小圆点角色分别标出猫/鼠：
  ```
  猫标记 x = 底图中心x + ((cat_wx + 世界半宽) * m - 底图半宽)
  猫标记 y = 底图中心y + ((cat_wy + 世界半高) * m - 底图半高)
  ```
- **置顶技巧**：在角色 forever 里第一句 `go to front`（IR：`go_to_front_back: front`），
  保证小地图/标记永远盖在地图和角色之上。或者在 `sprites` 列表里把它排在最后
  （Scratch 里后声明的角色层级更高）。

### 图层顺序（z-order）
- 不靠 `go to front` 也能控制层级：**`sprites` 数组越靠后，角色越靠前**。
  推荐顺序：`[地图, 玩家, 敌人, 聊天框, 数字显示, 小地图, 标记...]`。
- 若同一时刻要动态换层级（如「点中的角色置顶」），再用 `go to front` / `go back N layers`。

### IR 写法要点 ✅
```yaml
sprites:
  - name: 地图
    size: 100
    rotationStyle: don't rotate
    costumes: [{ name: 世界, asset: assets/x/bigmap.png }]
    scripts:
      - - when_receive: { message: 游戏开始 }
        - show: null
        - forever:
            do:
              - set_variable: { var: camera_x, value: { add: [ {var: camera_x},
                  { multiply: [ {subtract: [{var: 目标x}, {var: camera_x}]}, 0.15 ] } ] } }
              - goto_xy: { x: { subtract: [0, {var: camera_x}] },
                           y: { subtract: [0, {var: camera_y}] } }
  - name: 猫
    scripts:
      - - when_receive: { message: 游戏开始 }
        - forever:
            do:
              # ... 更新 cat_wx / cat_wy（世界坐标）...
              - goto_xy: { x: { subtract: [{var: cat_wx}, {var: camera_x}] },
                           y: { subtract: [{var: cat_wy}, {var: camera_y}] } }
```

> 注意：实体必须存「世界坐标」变量，每帧用 `goto_xy` 重算屏幕位置；
> 不要直接 `move steps` 改屏幕坐标，否则滚动时坐标会错乱。
> `safe_spawn` 把精灵随机挪到屏幕点后，要立刻把世界坐标同步回去：
> `set cat_wx = (x position) + camera_x`（详见 examples/cat_mouse.yaml 的鼠）。

---

## 2. 平滑移动（Smooth Movement）

「瞬间位移」（`change x by 50`）看起来像瞬移、很生硬。专业手感靠**速度 + 摩擦**或**缓动**。

### 配方 A：速度 + 摩擦（最有「惯性」手感，推荐用于玩家角色）
```
when green flag:
  set [vx v] to [0]
  forever:
    if <key (right) pressed?> then change [vx v] by (0.8)   # 加速度
    if <key (left)  pressed?> then change [vx v] by (-0.8)
    set [vx v] to ((vx) * (0.85))                           # 摩擦：每帧衰减
    change x by (vx)                                        # 用速度驱动位移
```
- 0.8 = 加速度，0.85 = 摩擦系数（越接近 1 滑行越远）。
- 想「踩油门提速、松手缓停」，就是这套。

### 配方 B：缓动（Easing，自然加减速）
- 朝目标移动：`repeat until <touching 目标?> move ((distance to 目标) / 8) steps`
  每帧走剩余距离的 1/8，自动「先快后慢」。
- 通用 lerp：`值 = 值 + (目标 - 值) * 系数`（系数 0.1~0.2），用于相机、血量条、UI 过渡。

### 配方 C：对角线归一化（避免斜着走更快）
- 同时按上下+左右时，合速度会是单轴的 √2 倍。修正：
  ```
  if <<(abs vx) > [0.1]> and <(abs vy) > [0.1]>> then
    set [vx v] to ((vx) * (0.707))
    set [vy v] to ((vy) * (0.707))
  end
  ```
  `abs` 用 `mathop: {operator: abs, num: ...}`，`0.707 ≈ 1/√2`。

### 配方 D：朝向与翻转
- 用 `rotationStyle: left-right` + 单一朝右造型即可：朝左时 Scratch 自动水平镜像，
  **绝不会上下颠倒**（解决「角色面向某个方向时整个倒过来」）。
- 若要更精细，可准备「原图 + 镜像图」两套造型，按 `direction < 0` 切换。

### IR 写法要点 ✅
```yaml
- if: { cond: { key_pressed: { key: right arrow } },
        do: [ { change_variable: { var: vx, by: 0.8 } } ] }
- set_variable: { var: vx, value: { multiply: [{var: vx}, 0.85] } }
- set_variable: { var: cat_wx, value: { add: [{var: cat_wx}, {var: vx}] } }
```

---

## 3. 开关设计（State Machine & Toggles）

### 3.1 状态机（游戏类作品必用）
把游戏拆成**互不相干的状态**，用全局变量 `game_state` 记录当前状态，
**每个脚本开头都先问一句「我现在该动吗」**，避免逻辑绞成意大利面。

- 典型三态：`title`（标题屏）/ `playing`（游戏中）/ `over`（结算）。
- 状态切换用**广播**通知所有人，不要硬编码：
  ```
  点开始按钮 -> set game_state = "playing" -> broadcast 游戏开始
  时间到     -> set game_state = "over"     -> broadcast 游戏结束
  ```
- 每个角色脚本用 `if <(game_state) = ["playing"]>` 守卫，标题屏/结算时一律装死。
- 参考：Pac-Man 的鬼用 `ghost_mode`（1=追/2=散/3=怕）驱动完全不同的移动逻辑；
  赛车游戏用 `游戏状态` 变量调度「标题→运行→结束」主循环。

### 3.2 布尔开关（Toggle / 开关）
「按一下开、再按一下关」的开关，用 0/1 变量 + **边沿检测**实现：
```
when green flag: set [开关M v] to [1]   # 默认开
forever:
  if <<key (m) pressed?> and <(上一次M) = [0]>> then   # 刚按下这一帧
    set [开关M v] to ((1) - (开关M))                    # 翻转 1<->0
    set [上一次M v] to [1]
  end
  if <not <key (m) pressed?>> then set [上一次M v] to [0] end  # 松开才能再触发
```
- 经典开关例子：**小地图开关**（按 M 隐藏/显示小地图）、**音效开关**（按 S 静音）。
- 用开关的地方：`if <(开关M) = [1]> then show else hide`。

### 3.3 为什么不用一长串 if
状态一多，嵌套 if 会「在重叠处藏 bug」。状态机让每个状态只管自己的一摊事，
加「暂停」「关卡选择」等新状态也只需新增分支，不动老逻辑。

### IR 写法要点 ✅
```yaml
stage.variables:
  game_state: "title"
  小地图开: 1
  音效开: 1
sprites:
  - name: 猫
    scripts:
      - - when_receive: { message: 游戏开始 }
        - forever:
            do:
              - if: { cond: { equals: { a: {var: game_state}, b: "playing" } },
                      do: [ /* 只有游戏中才执行移动/碰撞 */ ] }
```

---

## 4. 视野阴影与光照（手电筒 / 黑暗遮罩）

> 社区最经典的「恐怖游戏」做法：**光不是光，而是一块盖在最上面的黑布，
> 中间挖了一个透明的洞，洞跟着玩家走。**

### 原理
1. 一张 **480×360 的黑幕 PNG**，正中央挖一个**真透明**的圆洞（alpha = 0）。
2. 这个角色 `go to front`，永远盖在所有角色之上。
3. 每帧把它的中心挪到玩家身上（洞就跟着玩家走）。
4. 想更暗就加 `set ghost effect to 10`（黑幕半透明，能隐约看见房间）。

### ⚠️ 最大的坑：造型尺寸上限 150%
Scratch 规定「精灵在任一轴上的可视尺寸不得超过舞台的 150%」。
一块 480×360 的遮罩最多放到 150%（720×540），玩家走到舞台边缘就**漏光**。

**官方绕过办法（Scratch Wiki: overriding the costume size limit）**：
```
when green flag clicked:
  switch costume to [点 v]      # 先切到一张极小的造型（1×1 像素）
  set size to (250) %           # 尺寸上限按"当前造型"算，小造型可以放到 250%
  switch costume to [暗 v]      # 再切回黑幕造型，尺寸保持 250%
  show
  go to [front v] layer
  forever:
    go to [玩家 v]              # 洞跟着玩家走
```
> 所以遮罩角色需要**两张造型**：一张 480×360 黑幕（带洞），一张 1×1 的小点。
> `make_ui_assets.py darkness` 生成的黑幕；小点可复用 `cat_dot.png`。

### 变体
- **8 宫格拼贴**：不想用 250% 尺寸，就做 8 个偏移的黑块角色跟着鼠标走，拼满舞台。
- **克隆偏移法**：只做 2 个角色，一个带洞 + 一个纯黑，克隆 8 份并给每个克隆
  一个**私有编号**（for this sprite only），按编号偏移。
- **灯光过渡**（进暗区变暗、出来变亮）：
  ```
  重复执行:
    将 [亮度 v] 设定为 ((亮度) + ((目标亮度 - (亮度)) * 0.1))
    将 [亮度特效 v] 设定为 (亮度)
  ```

### 性能红线
- **同一个克隆体上不要叠超过 3 层外观特效**，否则低端设备会花屏/掉帧。
- 特效可叠加但要克制：黑幕（1 层）+ 角色自身特效（1 层）通常安全。

### IR 写法要点 ✅
```yaml
- name: 黑暗
  rotationStyle: don't rotate
  costumes:
    - { name: 暗, asset: assets/x/dark_overlay.png }   # 480x360 黑幕带透明洞
    - { name: 点, asset: assets/x/cat_dot.png }        # 1x1 小点，用来绕尺寸上限
  scripts:
    - - when_green_flag_clicked:
        - hide: null
        - switch_costume: { costume: 点 }
        - set_size: { value: 250 }
        - switch_costume: { costume: 暗 }
        - set_effect: { effect: GHOST, value: 10 }
    - - when_receive: { message: 游戏开始 }
      - show: null
      - go_to_front_back: front
      - forever:
          do:
            - goto_xy: { x: { of: { object: 猫, property: x position } },
                         y: { of: { object: 猫, property: y position } } }
```

### ⚠️ 层级：黑幕要不要 `go to front`？
- **纯黑幕作品**（没有 UI）：要 `go to front`，黑幕必须盖住一切。
- **有 UI 的作品**（小地图 / 血条 / 数字牌面）：**不要** `go to front`，
  否则会把 UI 一起盖黑。改用 **`sprites` 数组顺序**把黑幕放在
  「游戏实体之上、UI 之下」：
  ```
  sprites: [地图, 玩家, 敌人, 黑暗, 聊天框, 数字牌面, 小地图, 标记...]
  ```
  数组越靠后层级越高。**每帧 `go to front` 还可能让层级顺序变得不确定。**

### ⚠️ 无头测试环境测不出 size
`RenderedTarget.setSize()` 里 `this.size = ...` 的赋值写在 `if (this.renderer)` 内部，
headless scratch-vm 没有渲染器 → **无头环境看不到 size 变化**。
所以黑幕的「先切小造型再设 size」只能做**结构级**校验（看积木链对不对），
最终效果要在 Scratch 编辑器里目视确认。

---

## 5. 弹窗与「当关闭被点击」（UI 面板 / 遮罩拦截）

### 场景
玩家点了「设置」或「帮助」，弹出一个面板，面板右上角有个 **×**，点它就关掉面板。
这就是**当角色被点击（关闭按钮）** 的典型用法。

### 三件套：面板 + 遮罩 + 关闭按钮
| 角色 | 作用 |
|---|---|
| `弹窗遮罩` | 半透明黑板，盖住游戏区，**拦截误点击** |
| `设置面板` | 面板本体（标题栏 + 内容 + 关闭按钮） |
| `关闭按钮` | 右上角的 ×（单独一个角色，方便做点击热区） |

### 关键坑 1：Scratch 的点击会「穿透」
Scratch 里点到上层精灵，**下层精灵也会收到点击**（点击按 z 顺序广播给所有命中精灵）。
所以弹窗打开时，必须有一层**遮罩**挡住下面的角色，否则玩家点 × 的同时
会「顺便」点到游戏里的老鼠。

### 关键坑 2：背景的「当背景被点击」会立刻关掉菜单
「点空白处关闭菜单」很常见，但如果背景有 `when stage clicked → 隐藏菜单`，
点开始按钮时**背景的点击也可能触发**，菜单会「一闪就没」。
解决办法：用**全局锁定变量**：
```
when stage clicked:
  if <(菜单锁定) = [0]> then 隐藏菜单
```
点开菜单时先 `设 菜单锁定 为 1`，关闭时置 0。

### 关键坑 3：窗口必须置顶
`go to front` 要放在**每次打开**时（`when I receive [打开面板]`），不是只在绿旗时做一次。
多个窗口同时打开时，后开的会盖在先开的上面——这正是期望行为。

### 双击判定（桌面图标）
```
when this sprite clicked:
  if <((计时器) - (上次点击时间)) < [0.5]> then
    broadcast [打开我的电脑 v]
    set [上次点击时间 v] to [0]
  else
    set [上次点击时间 v] to (计时器)
  end
```
- 0.5 秒可能太短，图标还在动的话调到 0.6~0.7。
- 别给图标加「碰到边缘就反弹」，会导致位置漂移、点不中。

### 批量按钮（10 个关卡 / 3 个难度）的正确架构
**不要一个按钮建一个角色**（素材乱、改样式要全改），
**也不要用画笔实时写字**（每次开窗全部重绘，30 个按钮必卡）。
社区最优解（MVC）：
1. **1 张通用按钮底板**造型，所有按钮都用它；
2. 用**克隆**批量生成按钮；
3. 用**私有变量（for this sprite only）按钮编号**区分每个克隆的身份（1/2/3…30）；
4. 提前做好所有固定文字的**静态造型**，靠编号切换造型 —— **零画笔、零实时渲染**；
5. 用 1 个**全局二进制变量**（如 `面板掩码`）统一管控所有按钮的显隐：
   `0 = 关闭（全部隐藏）`，`1 = 开启（全部显示）`；
6. 非按钮克隆（面板本体、取消按钮）私有编号统一置 0，代码里加
   `if <(按钮编号) != [0]>` 前置判断，**防止多余克隆执行按钮逻辑**。

### IR 写法要点 ✅
```yaml
- name: 关闭按钮
  x: 180
  y: 120
  costumes: [{ name: 叉, asset: assets/x/btn_close.png }]
  scripts:
    - - when_green_flag_clicked:
        - hide: null
      - when_receive: { message: 打开面板 }
        - show: null
        - go_to_front_back: front
      - when_this_sprite_clicked:
          comment: 「当关闭被点击」——核心就这一句
        - broadcast: { message: 关闭面板 }
        - delete_this_clone: null        # 若是克隆按钮，删掉自己
- name: 设置面板
  scripts:
    - - when_receive: { message: 打开面板 }
        - show: null
        - go_to_front_back: front
      - when_receive: { message: 关闭面板 }
        - hide: null
```
- 面板本体也可以做成「底板 + 若干克隆按钮」，克隆用 `create_clone_of` + 私有编号。
- `make_ui_assets.py closebtn` 可生成 × 按钮图；`panel` 可生成面板底板。

---

## 6. 防搬作品（合规做法）

### 先记住官方规则（否则会被官方警告）
- Scratch 上的作品全部采用 **CC BY-SA（相同方式共享）** 授权：
  **一旦分享到网站，就无法禁止别人改编**。Scratch 团队明确拒绝过「禁止改编」功能。
- ❌ **禁止在「说明与致谢」里写「禁止改编 / 请勿复制」** —— 官方会警告甚至处理作品。
- ✅ 官方会自动给改编作品加 **「改编自 XXX」** 署名标签，这是最有效的归属声明。

### 所以「防搬」= 让署名无法被抹掉 + 留证据
| 手段 | 做法 | 效果 |
|---|---|---|
| **致谢栏署名** | 说明与致谢写清「全部代码与美术由 XXX 创作，引用请注明出处」 | 最重要，官方推荐 |
| **首页署名卡** | 标题屏放一个署名角色/面板（`panel` 素材） | 一进游戏就看到 |
| **素材清单** | 列出用到的每个素材来源（CC0 站点/自己画的） | 明确素材归属 |
| **水印** | 美术上加不显眼的小署名；代码里写「作者：XXX」注释 | 搬运时容易露出 |
| **自定义积木封装** | 核心玩法封装成命名清晰的自定义积木 | 被搬时「看得出是你的」 |
| **私密保底** | 不想被搬就**不分享**（un-share），只有自己能看 | 绝对安全但没人看得到 |
| **官方举报** | 被原样搬运 → 举报「作品的完全复制」；被用图 → 举报「未注明出处使用图片/音乐」 | 官方处理 |

> 合规提醒：**不要**在作品里写「禁止改编」，**不要**用代码阻止他人打开/运行你的作品
> （例如检测到非预期环境就锁死）——这类做法违反社区规范。
> 正确姿势是「署名 + 致谢 + 保留官方改编署名链」。

### IR 写法要点 ✅
```yaml
# 标题屏旁边放一个署名角色
- name: 署名
  x: 0
  y: -175
  costumes: [{ name: 署名, asset: assets/x/byline.png }]
  scripts:
    - - when_green_flag_clicked:
        - show: null
```
- 素材：`make_ui_assets.py panel --text "原作：XXX" --sub-text "美术/音效：XXX"`。
- sb3 的 `meta` 里也可以写上作者，便于程序化追踪：
  `build_sb3.py` 写入 `meta: {agent: ai-scratch-maker/...}`，可自行补充 `author` 字段。

---

## 7. 克隆粒子系统（火花 / 爆炸 / 尾迹 / 烟雾）

### 原理
- **本体**当"粒子工厂"，绿旗时 `hide`；
- 用 `create clone of [自己]` 批量造**克隆体**，每个克隆就是一个粒子；
- 克隆体脚本在 `when I start as a clone` 里跑，寿命到了 `delete this clone`。

### ⚠️ 关键 1：私有变量才能每个克隆各有一份
变量选 **「仅适用于此角色」（for this sprite only）** 时，
**每个克隆体都有自己独立的一份数值**；选「适用于所有角色」则所有克隆共享一个值。
所以粒子的 `vx / vy / 寿命` 必须是私有变量。

### ⚠️ 关键 2：克隆也会触发本体的事件帽子
如果本体有「当按下空格键 → 生成粒子」，克隆体也会触发它 → 粒子无限增殖。
解决办法：加一个私有布尔标志 `是否克隆`：
```
when green flag:
  set [是否克隆 v] to [0]
when I start as a clone:
  set [是否克隆 v] to [1]
when space key pressed:
  if <(是否克隆) = [0]> then       # 只有本体能生成
    repeat 10: create clone of [myself]
```

### 粒子运动模板
```
when I start as a clone:
  show
  set [vx v] to (pick random -5 to 5)
  set [vy v] to (pick random 1 to 10)
  repeat 20:
    change [ghost effect v] by (5)      # 渐隐
    change x by (vx)
    change y by (vy)
    change [vy v] by (-1)              # 重力
  delete this clone
```

### 进阶：渐变生成（不要一坨全冒出来）
```
set [创建延时 v] to [0.03]
repeat 10:
  change [创建延时 v] by (0.001)
  wait (创建延时 * 创建延时) secs
  create clone of [myself]
```
延时平方增长 → 越到后面越密，像真的火花。

### 性能红线
- Scratch 同屏克隆上限约 **300 个**，超了会直接丢克隆或卡死。
- 一次生成 10~30 个，寿命 20 帧左右，是安全区。
- 更省的做法：**画笔扩展的「图章」**把造型一次性印到舞台上（不产生克隆体），
  适合静态星空、地面装饰。

### ⚠️ 无头测试环境跑不了克隆
`RenderedTarget.makeClone()` 依赖渲染器做 `isClone` / 销毁登记，
headless scratch-vm 里克隆会被立刻回收 → **无头环境测不出粒子效果**。
所以克隆相关功能只能做**结构级**校验：
- 有「当作为克隆体启动」帽子（`control_start_as_clone`，下拉要填 `_myself_`）；
- 有「创建克隆体」积木（`control_create_clone_of`，下拉填**角色名**）；
- 有「删除此克隆体」积木；
- `repeat` 的次数不是 0（**这里最容易静默出错，见下**）；
- 速度变量确实是**角色级私有变量**（每个克隆各一份）。

> ⚠️ **静默失效陷阱**：IR 里写 `- repeat: 16` + `do:`（标量 + 兄弟键）时，
> 如果序列化器没把友好名解析成规范 opcode，标量会**被丢掉**，
> 编译成「重复 0 次」——不报错、只是什么都不发生。
> 写 `repeat` 时建议用完整写法：
> ```yaml
> - repeat:
>     times: 16
>     do:
>       - ...
> ```

### IR 写法要点 ✅
```yaml
- name: 火花
  costumes: [{ name: 点, asset: assets/x/cat_dot.png }]
  variables:            # 私有变量（sprite 级）→ 每个克隆各一份
    vx: 0
    vy: 0
    是否克隆: 0
  scripts:
    - - when_green_flag_clicked:
        - hide: null
        - set_variable: { var: 是否克隆, value: 0 }
      - when_start_as_clone: { clone: _myself_ }
        - show: null
        - set_variable: { var: 是否克隆, value: 1 }
        - set_variable: { var: vx, value: { random: { from: -5, to: 5 } } }
        - set_variable: { var: vy, value: { random: { from: 1, to: 10 } } }
        - repeat: 20
            do:
              - change_effect: { effect: GHOST, value: 5 }
              - change_x: { value: { var: vx } }
              - change_y: { value: { var: vy } }
              - change_variable: { var: vy, by: -1 }
        - delete_this_clone: null
      - when_this_sprite_clicked:
        - if: { cond: { equals: { a: { var: 是否克隆 }, b: 0 } },
                do: [ { repeat: 10, do: [ { create_clone_of: { clone: 火花 } } ] } ] }
```

---

## 8. 触屏适配与虚拟摇杆（手机上也能玩）

### ⚠️ 第一条硬约束：Scratch 没有多点触控
触屏在 Scratch 里被当成**一只鼠标**，只能在一个位置。
所以**两件事不能同时做**（边走边跳、边移动边射击）——任何积木都绕不过去。

### 因此要「为单指设计玩法」
| 方案 | 做法 |
|---|---|
| 自动跑 + 点击跳 | 角色自己往前跑，玩家只管跳（无尽跑酷的经典解） |
| 点击跳 + 拖拽转向 | 一根手指：横向位置跟手，轻点触发跳 |
| 转向代替平移 | 一个按钮改变方向，角色始终朝前走（经典单输入） |
| 点一下开/再点一下停 | 切换式移动，手指空出来做别的 |
| 回合制 / 解谜 / 点选 | 本来就一次一个输入，几乎不用改 |

### 按住移动怎么写（不能只用「当角色被点击」）
点击只触发一次，**按住不放不会持续移动**。正确写法是**循环里同时判断两个条件**：
```
forever:
  if <<mouse down?> and <touching [mouse-pointer]?>> then
    change x by (6)
```
- `touching [mouse-pointer]?` = 判断指针是否在这个按钮上（IR：`touching: {object: _mouse_}`）。
- 每个方向一个按钮精灵，放在**屏幕底部两角**（拇指够得到的地方），不要放中间。

### 虚拟摇杆（左右两半都能玩）
- **底盘**角色（固定在左下角，不写逻辑）+ **中心**角色（跟着指针动）。
- 中心角色的逻辑：
  ```
  forever:
    if <mouse down?> then
      if <(到鼠标距离) < [60]> then      # 手指在底盘范围内
        if <(到鼠标距离) > [12]> then    # 死区：太小就不动，防止抖动
          面向鼠标
          设 [方向x v] 到 ((鼠标x - 底盘x) / 60)
          设 [方向y v] 到 ((鼠标y - 底盘y) / 60)
    else:
      设 [方向x v] 到 0
      设 [方向y v] 到 0
  ```
- 「底盘到鼠标距离」要用勾股定理自己算（Scratch 只有「到鼠标的距离」，没有「到某角色的距离」）：
  `sqrt((鼠标x-底盘x)² + (鼠标y-底盘y)²)`（IR 用 `mathop: {operator: sqrt}`）。
- 玩家角色只读 `方向x / 方向y` 两个全局变量来走。

### IR 写法要点 ✅
```yaml
# 按钮角色：把「按住状态」写进全局变量，玩家角色每帧读它
- name: 左按钮
  costumes: [{ name: 左, asset: assets/ui/arrow_left.png }]
  scripts:
    - - when_green_flag_clicked:
        - set_variable: { var: 左按, value: 0 }
      - forever:
          do:
            - if: { cond: { and: [ { mousedown: null },
                                   { touching: { object: _mouse_ } } ] },
                    do: [ { set_variable: { var: 左按, value: 1 } } ] }
            - if: { cond: { not: { operand: { and: [ { mousedown: null },
                                         { touching: { object: _mouse_ } } ] } },
                    do: [ { set_variable: { var: 左按, value: 0 } } ] }
```
> 玩家角色每帧读 `左按`：`if <(左按) = [1]> then change [vx v] by (-0.8)`。
> 这样「按住」和「点一下」是同一个入口，手机和电脑通用。

---

## 9. 血条 / 进度条

### 三种做法，按场景选
| 做法 | 优点 | 缺点 |
|---|---|---|
| **多造型法**（推荐入门） | 简单、零额外角色 | 精度只到档位 |
| **克隆拼接法** | 精度高、不被遮挡 | 每个敌人要配一个克隆 |
| **画笔法** | 一个角色画全场血条 | 需画笔扩展，每帧重绘 |

### 多造型法（5 档）
做一个血条角色，准备 5 套造型：满血 / 3/4 / 1/2 / 1/4 / 空血。
```
when green flag: switch costume to [满血 v]
forever:
  if   <(生命值) > [(生命上限 * 0.75)]> then switch costume to [满血 v]
  else if <(生命值) > [(生命上限 * 0.5)]> then switch costume to [3/4 v]
  ...
```
- 也可以用**两段精灵**（灰底 + 红条）做连续血条：底条固定，红条用
  `set size to ((生命值 / 生命上限) * 100)`，再 `go to x` 修正左端对齐。

### 克隆拼接法（多敌人）
- 建一张**列表**存所有敌人的血量与坐标（`add ... to [生命值列表]`）。
- 血条角色克隆时，先 `add` 坐标再 `create clone`，克隆体启动时读列表最后一项定位。
- 敌人死亡 → `delete this clone` + 列表 `delete` 对应项。

### IR 写法要点 ✅
```yaml
- name: 血条底
  costumes: [{ name: 条, asset: assets/x/hp_bg.png }]
- name: 血条
  costumes: [{ name: 条, asset: assets/x/hp_fill.png }]
  scripts:
    - - when_green_flag_clicked:
        - forever:
            do:
              - set_size: { value: { multiply: [ { divide: [ {var: 生命值}, {var: 生命上限} ] }, 100 ] } }
              - set_x: { x: { add: [ {var: 血条左端}, { multiply: [ { divide: [ {var: 生命值}, {var: 生命上限} ] }, 50 ] } ] } }
```

---

## 10. 关卡系统：列表当数据表

### 问题
「切换背景 + 重置所有角色变量」这种写法，关卡一多就**漏重置**、脚本爆炸。

### 解法：数据与逻辑分离
把一张列表当作**关卡配置表**，每关占固定长度的若干项：

| 项 | 含义 |
|---|---|
| 1 | 背景编号 |
| 2 | 玩家初始 x |
| 3 | 玩家初始 y |
| 4 | 敌人类型 |
| 5 | 敌人刷新 x |
| 6 | 敌人刷新 y |
| 7 | 刷新间隔 |
| 8 | 通关条件 |

再写一个「加载关卡」的自定义积木，读这张表 → 切背景 → 摆角色 → 开敌人 → 计时。
**加新关卡 = 往表里加 8 个数**，不用碰任何逻辑代码。

### IR 写法要点 ✅
```yaml
stage:
  lists:
    关卡表: []          # 关卡 1 占用第 1~8 项，关卡 2 占用第 9~16 项……
- name: 关卡控制
  procedures:
    - name: 加载关卡
      args: [{name: 序号, type: number}]
  scripts:
    - - when_green_flag_clicked:
        - forever:
            do:
              - if: { cond: { greater_than: { a: {var: 关卡序号}, b: 0 } },
                      do: [ { proc: 加载关卡, args: [{var: 关卡序号}] } ] }
```
- 列表读写积木：`item_of_list` / `add_to_list` / `delete_of_list` / `length_of_list` / `list_contains_item`。

---

## 11. 缓动与物理（重力 / 弹跳 / 落地）

### 弹跳：速度衰减 + 落地反向
```
重复执行:
  将 [垂直速度 v] 设定为 (12)
  重复执行:
    将 [垂直速度 v] 增加 (-1)      # 重力
    将 y 增加 (垂直速度)
    如果 <碰到地面?> 那么
      将 [垂直速度 v] 设定为 ((垂直速度) * (-0.7))   # 落地反弹 + 衰减
    end
  end
```
- 关键：**落地时乘 -0.7**，速度逐次变小，角色自然「越弹越低」直到停住。
- 同一个思路可以移植到**缩放、旋转、透明度**上。
  口诀：**任何「移动类」动画都加加速度或减速度，不要固定步数**。

### 地形摩擦（赛车类）
草地和公路用不同摩擦系数，用 `touching color` 判断：
```
if <碰到 草地色?> then
  set [vx v] to ((vx) * 0.7)
else
  set [vx v] to ((vx) * 0.8)
```

### IR 写法要点 ✅
```yaml
- set_variable: { var: vy, value: 12 }
- repeat:
    do:
      - change_variable: { var: vy, by: -1 }
      - change_y: { value: { var: vy } }
      - if: { cond: { touching: { object: 地面 } },
              do: [ { set_variable: { var: vy,
                       value: { multiply: [ {var: vy}, -0.7 ] } } } ] }
```

---

## 12. 音频控制（音量 / 静音 / 淡出 / 切歌）

### 静音开关
用 §3.2 的 0/1 变量 + 边沿检测切换，比「循环播放 + 音量 0」更省性能：
```
when green flag: set [音效开 v] to [1]
forever:
  if <(音效开) = [1]> then
    forever: play sound [追逐 v] until done
  else:
    stop all sounds
```
> ⚠️ Scratch 里 `forever play sound until done` 是**独占**的：它会占住该线程，
> 期间该角色的其他脚本仍能跑，但**再写一个 forever 播音就会互相打断**。
> 背景音乐只放一个线程。

### 音量渐变（淡入淡出）
```
repeat 10:
  change [volume v] by (-5)      # 淡出
```
- `set volume to (100)` 是全局音量（0~100）。
- **近距离音效**：心跳声随敌人靠近而加快/变大：
  ```
  set [心跳间隔 v] to ((1) - (1 / (与怪物距离 + 0.5)))
  wait (心跳间隔) secs
  play sound [心跳 v]
  ```

### 切歌（用变量当播放列表下标）
```
when green flag: set [音乐 v] to [0]
when m key pressed:
  change [音乐 v] by (1)
  if <(音乐) > [3]> then set [音乐 v] to [1]     # 循环回第一首
  stop all sounds
  if <(音乐) = [1]> then forever: play sound [曲1 v] until done
  if <(音乐) = [2]> then forever: play sound [曲2 v] until done
  if <(音乐) = [3]> then forever: play sound [曲3 v] until done
```

### IR 写法要点 ✅
```yaml
- set_volume: { value: 60 }
- change_volume: { value: -5 }
- play_sound_until_done: { sound: 追逐 }
- play_sound: { sound: 喵 }
- stop_all_sounds: null
```
> 本 skill 的硬性要求：**音效/音乐一律由 agent 用 `scripts/gen_audio.py` 本地生成**，
> 不调用外部 TTS/音乐 API。

---

## 13. 投影与遮挡层次

### 给角色加影子
复制一份角色造型 → 涂黑 → 建一个「影子」角色：
```
when green flag: hide
forever:
  if <(本体可见)> then
    show
    go to [本体 v]
    go [back] (1) layers
    set [ghost effect v] to (50)
    set [brightness effect v] to (-100)
  else
    hide
```
- 关键：`go back 1 layers` 让影子在本体**下面**一层；
  `brightness -100` 变黑，`ghost 50` 半透明。

### 层次感的通用配方
- **地图（底）→ 地面装饰 → 实体 → 影子/特效 → UI（聊天框、数字、小地图）→ 遮罩（黑幕）**。
- 需要动态置顶时用 `go to front`；但**每帧 `go to front` 会打断层级排序**，
  只在「打开时」置顶一次。

---

## 14. 性能与稳定性红线（踩过的坑）

| 坑 | 症状 | 对策 |
|---|---|---|
| 外观特效叠太多 | 低端设备花屏/局部变色 | 同一克隆 ≤ 3 层特效 |
| 克隆数超限 | 克隆凭空消失、卡死 | 同屏 ≤ 300；一次生成 ≤ 30 |
| 画笔实时写字 | 界面切换闪烁、按钮一多就掉帧 | 用**预制造型**替代画笔渲染 |
| 大地图没夹紧相机 | 走到世界边缘露出黑边 | 相机夹紧在 ±(W/2-240) |
| 实体用屏幕坐标移动 | 滚动时坐标错乱 | 实体存世界坐标 + `goto_xy` 渲染 |
| `safe_spawn` 后不同步坐标 | 角色一出生就瞬移 | 立刻 `世界坐标 = x位置 + camera_x` |
| 多个 forever 播音 | 音乐互相打断 | 背景音乐只留一个线程 |
| 弹窗没有遮罩 | 点 × 时误触底下的角色 | 加半透明遮罩层 |
| 背景「当背景被点击」抢事件 | 菜单一闪就没 | 加全局锁定变量 |
| 造型尺寸超 150% | 设 size 被静默截断 | 先切小造型设 size 再切回 |

---

## 15. 碰撞箱与障碍物（背景图里的家具挡不住人）

### 问题（本 skill 的猫抓老鼠踩过的坑）
大地图 `bigmap.png` 里画了沙发、柜子、书桌、地毯，玩家却**直接穿过去**。

**根因：背景图 / 地图精灵里的障碍物没有碰撞箱。**
地图只是一张位图；Scratch 的碰撞检测只发生在**角色之间**
（「碰到 [某角色]?」「碰到 [颜色]?」），位图里的像素不是角色，永远不会被检测到。

> 记忆点：**「碰到」只认角色，不认背景。**
> 连舞台背景（backdrop）也一样——背景里的墙也挡不住人。

### 三种方案

| 方案 | 怎么做 | 优点 | 缺点 |
|---|---|---|---|
| **A. 障碍做成独立角色** ⭐ | 每件家具一个 sprite，存世界坐标，每帧 `goto_xy (世界 - 相机)` 跟随滚动；玩家 `touching [家具]?` | 合 Scratch 口味、像素级精确、改一个家具只改一个角色 | 角色多；同一件家具要用重复脚本 |
| **B. 颜色碰撞** | 玩家 `touching color? [家具色]?` | 一行搞定，不用建角色 | 颜色必须唯一；玩家描边也会参与判定；家具改色就失效 |
| **C. AABB 碰撞箱** | 变量存每件家具的 `x1,y1,x2,y2`（世界坐标），和玩家半宽半高做矩形相交 | 最精确、可做非矩形/斜坡、可做「站在平台上」 | 变量多、代码长 |

### 方案 A：独立障碍角色（推荐）

**第 1 步：把家具从地图图片里拿出来，单独生成 PNG。**
用 `make_ui_assets.py furniture` 一次生成 4 件家具，每件 PNG 的**像素尺寸 = 世界尺寸**（1:1），
这样角色 `size: 100` 就是正确大小。
`make_ui_assets.py world` 默认**不再把家具画进地图**（加 `--with-furniture` 才会画进去）。

**第 2 步：每件家具做成一个角色，存自己的世界坐标，每帧跟着相机滚。**
```yaml
- name: 沙发
  x: -270
  y: 190
  size: 100
  rotationStyle: don't rotate
  costumes: [{ name: 沙发, asset: assets/cat_mouse/沙发.png }]
  variables:
    wx: -270          # 世界坐标（固定）
    wy: 190
  scripts:
    - - when_green_flag_clicked:
      - hide: null
    - - when_receive:
          message: 游戏开始
      - show: null
      - forever:
          do:
            - goto_xy: { x: { subtract: [{var: wx}, {var: camera_x}] },
                         y: { subtract: [{var: wy}, {var: camera_y}] } }
```
> ⚠️ **障碍也必须跟着相机滚动**：它存的是**世界坐标**，每帧渲染成 `世界 - 相机`。
> 如果直接把它放在固定屏幕位置不滚动，碰撞判定就会「隔空撞人」。

**第 3 步：玩家分轴碰撞（先移动 → 再判定 → 撞了退回）。**
```yaml
# X 轴
- set_variable: { var: 旧x, value: {var: cat_wx} }
- set_variable: { var: cat_wx, value: { add: [{var: cat_wx}, {var: cat_vx}] } }
- goto_xy: { x: { subtract: [{var: cat_wx}, {var: camera_x}] },
             y: { subtract: [{var: cat_wy}, {var: camera_y}] } }     # ← 先摆到新位置！
- if:
    cond:
      or:
        - or:
            - touching: { object: 沙发 }
            - touching: { object: 柜子 }
        - or:
            - touching: { object: 书桌 }
            - touching: { object: 地毯 }
    do:
      - set_variable: { var: cat_wx, value: {var: 旧x} }
      - set_variable: { var: cat_vx, value: 0 }
      - goto_xy: { x: { subtract: [{var: cat_wx}, {var: camera_x}] },
                   y: { subtract: [{var: cat_wy}, {var: camera_y}] } }
# Y 轴同理
```

### ⚠️ 三个必踩的坑
1. **判定顺序**：Scratch 的「碰到」比较的是**屏幕坐标**。
   先改内部坐标、最后才渲染 → 判定用的是**上一帧的旧位置** → **漏判穿墙**。
   正确顺序 = 社区标准写法「先 move，再判断，撞了就退回」。
2. **4 个以上障碍要用嵌套 `or`**：Scratch 的 `或` 积木只有 2 个输入，
   4 路判断要写成 `或 [ 或[A B] 或[C D] ]`。
   IR 里 `or: [a, b, c]` 只会取前两个，**多出来的会被静默丢弃**。
3. **分轴处理才能「沿墙滑动」**：先解 X 再解 Y，撞 X 只回退 X。
   如果两轴一起判，玩家会「卡死在墙角」，贴着墙完全走不动。

### 方案 B：颜色碰撞
```
if <碰到颜色 [家具色]?> then
  停止移动 / 退回
```
- 家具颜色必须**唯一**（否则地板、墙也会被判成障碍）。
- `touching color?` 会拿角色**描边**去采样，描边不同结果就不同 → 不稳定。
- 适合「快速原型」，不适合精细作品。

### 方案 C：AABB 碰撞箱（自己算矩形）
变量里存每件家具的**世界矩形**：
`障碍1左 / 障碍1右 / 障碍1下 / 障碍1上`（或用列表当数据表，见 §10）。
玩家有自己的半宽 `hw`、半高 `hh`，矩形相交判定：
```
if <<(玩家x + hw) > (障碍1左)>> and <<(玩家x - hw) < (障碍1右)>>
   and <<(玩家y + hh) > (障碍1下)>> and <<(玩家y - hh) < (障碍1上)>> then
  撞到了
end
```
- 优点：世界坐标直接算，**不受相机与渲染时序影响**，无头环境也能测；
  还能扩展成「站在平台上」「斜坡」「可推动的箱子」。
- 缺点：变量多、代码长；家具多起来建议用**列表 + 循环**存数据表。

### 无头测试怎么验
无头 scratch-vm 没有渲染器，`isTouchingSprite` 会抛错，
所以要像 `scripts/smoke_test.mjs` 那样**打补丁**用包围盒近似。
注意大件障碍要单独给半径，否则会漏判：
```js
const HIT_RADIUS = { "沙发": 90, "柜子": 90, "书桌": 100, "地毯": 100 };
proto.isTouchingSprite = function (name) {
  const other = runtime.getSpriteTargetByName(String(name));
  if (!other) return false;
  const r = HIT_RADIUS[otherName] ?? 45;
  return Math.abs(other.x - this.x) < r && Math.abs(other.y - this.y) < r;
};
```

---

## 附录 A：本 skill 已支持的对应积木（IR 速查）

**运动**：`move_steps` / `goto_xy` / `glide_xy` / `point_in_direction` / `point_towards` /
`turn_right` / `turn_left` / `change_x` / `change_y` / `set_x` / `set_y` / `if_on_edge_bounce`
**运算**：`add` `subtract` `multiply` `divide` `mod` `random` `round`
`mathop: {operator: sqrt|abs|sin|cos|..., num: ...}`
**外观/层级**：`set_size` / `change_size` / `switch_costume` / `next_costume` /
`set_effect: {effect: COLOR|FISHEYE|WHIRL|PIXELATE|MOSAIC|BRIGHTNESS|GHOST, value: n}` /
`change_effect` / `clear_effects` / `go_to_front_back: front|back` /
`go_back_layers: {forward_backward: backward, layers: n}`
**克隆**：`create_clone_of: {clone: 角色名}` / `when_start_as_clone` / `delete_this_clone`
**声音**：`play_sound_until_done: {sound: 名}` / `play_sound` / `set_volume` / `change_volume` / `stop_all_sounds`
**侦测**：`touching: {object: 角色名 | _mouse_}` / `mousedown` / `key_pressed: {key: m}` /
`mouse_x` / `mouse_y` / `distance_to` / `timer` / `of: {object: 角色, property: "x position"}`
**控制**：`wait` / `wait_until` / `repeat` / `repeat_until` / `forever` / `if` / `if_else` / `stop`
**广播/状态**：`broadcast: {message: 名}` / `broadcast_and_wait` / `when_receive: {message: 名}`
**变量/列表**：`set_variable` / `change_variable` / `item_of_list` / `add_to_list` /
`delete_of_list` / `length_of_list` / `list_contains_item` / 自定义积木 `procedures`

> 私有变量（仅本角色）：写在 **sprite 级** `variables:` 里 → 每个克隆体各有一份。
> 全局变量：写在 **stage 级** `variables:` 里 → 所有角色共用。

## 附录 B：配套素材生成命令

```bash
python scripts/make_ui_assets.py world     --out assets/x/bigmap.png --w 960 --h 720   # 大地图（不含家具）
python scripts/make_ui_assets.py furniture --out-dir assets/x                              # 家具（独立障碍角色）
python scripts/make_ui_assets.py minimap   --out-dir assets/x                          # 小地图+标记点
python scripts/make_ui_assets.py darkness  --out assets/x/dark_overlay.png --hole-r 72 # 视野阴影遮罩
python scripts/make_ui_assets.py closebtn  --out assets/x/btn_close.png                # 关闭按钮 ×
python scripts/make_ui_assets.py panel     --out assets/x/panel.png --text "..."        # 面板/署名卡
python scripts/make_ui_assets.py titlebg   --out assets/x/title_bg.png --title "..."   # 标题页
python scripts/make_ui_assets.py digits    --out-dir assets/x                          # 0~9 数字
python scripts/make_ui_assets.py chatbox   --out assets/x/chatbox.png                  # 对话框底板
python scripts/make_ui_assets.py chatlines --out-dir assets/x --lines-file l.txt        # 台词图
```
