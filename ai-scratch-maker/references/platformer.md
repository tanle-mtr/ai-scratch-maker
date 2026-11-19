# 平台跳跃与横版关卡（第二十册，§156–§166）

> **用户要做「超级玛丽、跑酷、横版闯关、跳跃过关、蛋仔类」时先读这一册。**
> 这是 Scratch 里需求量最大、但最容易做「飘」的品类。本册结论来自对 4 个真实工程
> 逐块反编译：`超级玛丽（转载）`（5307 块 / 14 个克隆体角色）、`忍者冒险（开源）`
> （12731 块 / 17 个克隆体角色）、`BallJump`、`双人Apple跑酷`（19191 块）。
> 配套可运行工程 `examples/platformer.yaml` + 行为校验 `scripts/platformer_behavior_check.mjs`
> （`PLATFORMER_LOGIC_OK`）。

- **§156 帧循环必须用「广播分发」，不要各角色一个 `forever`**
  超级玛丽的骨架是 6 条广播：`Tick` → `WorldTick` / `MapUpdate` / `PlayerUpdate` /
  `SolidsUpdate` / `PlatformsUpdate`；双人Apple跑酷更彻底，把一帧拆成
  `game loop - scroll` / `- players` / `- spawn` / `- particles` / `- obj` 五条。
  用一个**总时钟**负责发令：
  ```yaml
  # 舞台：唯一的时钟
  - when_flag_clicked:
    - forever:
        - broadcast: {message: 帧}
        - wait: {secs: 0.033}      # 30fps
  ```
  ```yaml
  # 每个子系统只认「帧」，自己的 forever 全部删掉
  - when_receive: {message: 帧}
  - 物理: ...
  ```
  **三个好处**：① 执行顺序由广播顺序决定（可复现）；② 任何子系统在体内 `wait` 不会拖累
  别人；③ **暂停 = 停止发 `帧`**，一行搞定（比给每个角色加 `如果 暂停` 干净得多）。
  ⚠️ 总时钟**只能有一个**。两个 `forever` 同时广播同一条消息 → 一帧执行两次，物理直接翻倍。
  ⚠️ **写行为校验时**：无头 scratch-vm 里 `startHats` 只是把线程入队，真正执行落在**下一个**
  `_step`。所以「一帧」= `broadcast("帧")` **+ `stepN(2)`**；用 `stepN(1)` 会让物理隔帧才推进，
  跳跃高度、落地时机全部对不上（实测：y 每两帧才变一次）。另外给舞台加一个 `自动帧` 开关，
  校验时置 0 由脚本逐帧驱动，否则自带时钟和校验脚本会同时发帧。

- **§157 平行列表就是实体数据库（`Form*` 工厂）**
  超级玛丽的实体全部躺在舞台的平行列表里：
  `PlatformX / PlatformY / PlatformDir / PlatformType / PlatformLength / PlatformActivated`、
  `GoombaX / GoombaY / GoombaDir`、`ItemX / ItemY / ItemType`、`CoinX / CoinY`、`PipeX / PipeY`。
  每个实体角色一个 **`Form<实体>`** 自制积木：按列表长度循环，每轮克隆自己并写私有变量
  `我的编号 = i`，克隆体从列表第 i 项读自己的坐标/类型。
  ```yaml
  - define: {name: 生成平台}
  - set_variable: {var: i, value: 0}
  - repeat: {times: {length_of_list: {list: 平台X}}, do:
      - change_variable: {var: i, by: 1}
      - create_clone_of: {clone: _myself_}}
  # 克隆体启动：从列表读自己的数据（是克隆守卫！铁律 11）
  - when_start_as_clone:
    - if: {cond: {equals: [{var: 我的编号}, 0]}, do: [{delete_this_clone: null}]}
    - goto_xy: {x: {item_of_list: {list: 平台X, index: {var: 我的编号}}},
                y: {item_of_list: {list: 平台Y, index: {var: 我的编号}}}}
  ```
  ⚠️ **克隆体上限 300**（铁律 12）→ 平台/敌人多的关卡必须分批生成，或改用「一块平台一个造型
  画在背景里 + 只用一个碰撞箱列表」（`BallJump` 就是这么省的）。

- **§158 碰撞解算：分轴扫描（`FindFloor` / `FindCeiling`）**
  超级玛丽给每个可动实体都配了 `FindFloor` / `FindCeiling` 自制积木，`Player` 额外有
  `FindXPosition`。`忍者冒险` 的 `All Tiles` 把碰撞箱拆成三个列表
  `>> TOP HB / >> BOTTOM HB / >> RIGHT HB`。核心不是 `碰到` 积木，**是矩形重叠的纯数学判断**：
  ```
  重叠 ⇔ |px - bx| < 玩家半宽 + 平台半宽  且  |py - by| < 玩家半高 + 平台半高
  ```
  **必须分两趟**，先横后竖，各自独立回退：
  ```yaml
  # ① 水平：先假设移动成功，撞到就退回来
  - change_variable: {var: 玩家x, by: {var: vx}}
  - set_variable: {var: i, value: 0}
  - repeat: {times: {var: 平台数}, do:
      - change_variable: {var: i, by: 1}
      - if: {cond: {and: [ 重叠判断, {not: {operand: {equals: [{var: vx}, 0]}}} ]},
          do: [{set_variable: {var: 玩家x, value: {subtract: [{var: 玩家x}, {var: vx}]}}}]}}
  # ② 垂直：落地 / 撞头两个分支
  - change_variable: {var: 玩家y, by: {var: vy}}
  - set_variable: {var: i, value: 0}
  - repeat: {times: {var: 平台数}, do:
      - change_variable: {var: i, by: 1}
      - if: {cond: {and: [ 重叠判断, {less_than: [{var: vy}, 0]} ]}, do:
          - set_variable: {var: 玩家y, value: {add: [平台y_i, 平台半高_i, 玩家半高]}}
          - set_variable: {var: vy, value: 0}
          - set_variable: {var: 在地面, value: 1}}
      - if: {cond: {and: [ 重叠判断, {greater_than: [{var: vy}, 0]} ]}, do:
          - set_variable: {var: 玩家y, value: {subtract: [平台y_i, 平台半高_i, 玩家半高]}}
          - set_variable: {var: vy, value: 0}}}
  ```
  ⚠️ **三个必踩的坑**：
  1. **先横后竖，且每趟都要「独立回退」**——两轴一起判会把玩家卡在墙角、或者穿墙。
  2. **「重叠判断」用的是移动后的坐标**，别用移动前的（否则永远不重叠、直接穿墙）。
  3. `add` / `subtract` **只有 2 个操作数**（见 SKILL.md「IR 约定与坑」）→ 三项必须嵌套
     `ADD(ADD(平台y, 平台半高), 玩家半高)`，写成三项 `[a,b,c]` 会静默丢第三项。

- **§159 跳跃手感三件套（决定「飘不飘」）**
  1. **可变跳跃高度**：按住跳得高、松开就截断上升速度。
     ```yaml
     - when_receive: {message: 帧}
     - if: {cond: {and: [{key_pressed: {key: space}}, {not: {operand: {greater_than: [{var: vy}, 0]}}}]},
         do: [{set_variable: {var: vy, value: {multiply: [{var: vy}, 0.5]}}}]}
     ```
  2. **土狼时间（coyote time）**：刚离开平台边缘的 0.1s 内仍可起跳。
     维护 `离开地面计时`：每帧 `在地面=1 → 计时=0；否则 计时+1`，起跳条件写
     `在地面 = 1 或 离开地面计时 < 4`。
  3. **跳跃缓冲（jump buffer）**：落地前按跳，落地瞬间自动起跳。
     `按跳 → 缓冲计时=8`；每帧 `缓冲计时>0 → 缓冲计时-1`；起跳条件加一条
     `缓冲计时 > 0`，起跳后清零。
  超级玛丽的 `Gravity = -3` + `YSmooth` / `YSmoothing` 自制积木就是在做「重力平滑」：
  直接 `y += vy` 会有颗粒感，把 `vy` 做一次指数平均（`vy平滑 = vy平滑*0.7 + vy*0.3`）再移动就顺了。
  ⚠️ 平滑系数**只能乘不能减**（铁律 5），减法会发散。

- **§160 单向平台（从下面穿过去、从上面站住）**
  只在下落且**上一帧脚在平台顶上方**时才碰撞：
  ```yaml
  - if: {cond: {and: [
       {less_than: [{var: vy}, 0]},
       {greater_than: [{var: 移动前y}, {subtract: [平台y_i, 平台半高_i, 玩家半高]}]}
     ]}, do: [ 正常落地解算 ]}
  ```
  关键点是**必须存档「移动前的 y」**——先用 `移动前y = 玩家y` 记下，再改 `玩家y`。
  `超级玛丽` 的 `SemiSolids` 角色就是专门管这类平台的。

- **§161 移动平台必须「带人」**
  平台每帧算出 `平台位移 = 本帧位置 - 上帧位置`，然后把站在它上面的实体一起平移：
  ```yaml
  - if: {cond: {and: [{var: 站在我上面}, {equals: [{var: 在地面}, 1]}]}, do:
      - change_variable: {var: 玩家x, by: {var: 本帧位移x}}
      - change_variable: {var: 玩家y, by: {var: 本帧位移y}}}
  ```
  ⚠️ 「站在我上面」要**由玩家自己判定后写进平台的私有变量**，不能让平台去反查玩家——
  平台不知道自己身上站着谁（Scratch 没有 `碰到我` 的反向查询）。
  超级玛丽的 `Platforms` 有私有列表 `PlatformSpeed`，`双人Apple跑酷` 有 `EDIT - convey speed`
  （传送带速度），都是同一套。

- **§162 镜头跟随 + 边界钳制**
  超级玛丽用 `MapX = 600` / `MapY = -140` 做世界偏移，`Map` 角色带 `CloneNo.`；
  忍者冒险给**每个**克隆体一个 `Scroll #`，让每个克隆体自己按镜头位置重算屏幕坐标。
  两种做法选一种，别混：
  ```yaml
  # 做法 A（推荐，简单）：镜头是一个偏移量，所有世界物体 屏幕坐标 = 世界坐标 - 镜头
  - set_variable: {var: 镜头x, value: {subtract: [{var: 玩家x}, 160}}}
  - if: {cond: {less_than: [{var: 镜头x}, 关卡左边界]}, do: [{set_variable: {var: 镜头x, value: 关卡左边界}}]}
  - if: {cond: {greater_than: [{var: 镜头x}, {subtract: [关卡右边界, 320]}]},
      do: [{set_variable: {var: 镜头x, value: {subtract: [关卡右边界, 320]}}}]}
  - goto_xy: {x: {subtract: [{var: 玩家x}, {var: 镜头x}]}, y: {subtract: [{var: 玩家y}, {var: 镜头y}]}}
  ```
  **边界钳制必须两段都写**（左和右），只写左边 → 走到关底镜头一路飞出去、看不见人。
  半屏宽度取 160（480×360 下）——写死 320 会把镜头推到反方向。

- **§163 敌人：踩踏判定必须先比高度再比方向**
  ```yaml
  - if: {cond: {and: [
       {less_than: [{var: vy}, 0]},                                   # 玩家在下落
       {greater_than: [{var: 玩家y}, {add: [{var: 敌人y}, 10]}]}       # 玩家脚在敌人头顶之上
     ]}, do: [
       - 敌人死亡: ...,
       - set_variable: {var: vy, value: 12}                            # 踩一下弹起来
     ]}
  - else: [ 玩家受伤: ... ]
  ```
  ⚠️ 只判「重叠」不判「在下落 + 在上方」→ 从侧面走过去也会把敌人踩死，手感诡异。
  `双人Apple跑酷` 为此单独开了广播 `bounce on head` / `bounce on head 2`（两个玩家各一条）。

- **§164 死亡与检查点：一键「复位到检查点」**
  超级玛丽有 `TimeSinceDeath`、`Death` 广播、`SpawnX/SpawnY`（重生点）；
  忍者冒险有 `delete all clones!!` + `delete clones` + `Able to delete still? >:((` 三重保障；
  双人Apple跑酷有 `reset after death` / `reset to point`。
  标准流程（**别用绿旗重开**，铁律 6）：
  ```yaml
  - when_receive: {message: 复位到检查点}
  - set_variable: {var: 玩家x, value: {var: 检查点x}}
  - set_variable: {var: 玩家y, value: {var: 检查点y}}
  - set_variable: {var: vx, value: 0}
  - set_variable: {var: vy, value: 0}
  - set_variable: {var: 允许操作, value: 1}      # 松开行为闸门
  ```
  检查点判定：`玩家x > 检查点x + 200 → 检查点x = 玩家x`。

- **§165 行为闸门标志（`Allow*` 家族，专业工程的标志）**
  超级玛丽有一整套全局开关：`AllowPlayerMovement` / `AllowPlayerDamage` / `AllowMapChanges` /
  `AllowPlayerPowerup`，忍者冒险有 `Able to Jump` / `Currently Sword Swinging` / `Cutscene going?`，
  我的世界S 有 `BOOL-暂停？` / `BOOL-UI开启？`。作用是**让所有子系统在同一时刻集体闭嘴**：
  ```yaml
  - when_receive: {message: 帧}
  - if: {cond: {equals: [{var: 允许操作}, 0]}, do: [{stop: {option: this script}}]}
  - 真正的物理: ...
  ```
  **过场、对话、菜单、死亡动画全部靠它**，比到处写 `如果 在过场里` 干净一个数量级。
  ⚠️ `stop {option: this script}` 里的选项值必须是英文（`this script` / `all` / `other scripts in sprite`）。

- **§166 五个致命坑**：
  1. **两个总时钟**（§156）→ 物理跑双倍速，跳跃高度翻倍且不稳定。检查方法：把 `帧` 广播的
     发送次数打印出来，一帧只能是 1。
  2. **`forever` 里不节流**（`wait 0.02` 都不给）→ turbo 模式下 `forever` 一帧跑几十次，
     物理穿透。必须给总时钟 `wait 0.033`。
  3. **碰撞用 `碰到` 积木**：背景图里的地形**根本碰不到**（铁律 4：`碰到` 只认角色），
     而且无头校验测不到 → 一律用 §158 的矩形数学。
  4. **`add`/`subtract` 三项静默丢项**（见 SKILL.md「IR 约定与坑」）：写 `{add: [a, b, c]}` 会**悄悄少算 c**
     （不报错！），表现为「落地位置总是差半个身位」。
  5. **克隆体不设上限**：敌人/金币每帧生成 → 撞 300 上限后**静默不生成**，
     表现为「越玩越少怪」。必须用计数器 + 复用池（见 `references/game-architecture.md` §181）。
