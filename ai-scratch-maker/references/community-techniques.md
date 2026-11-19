# 第九册 · 社区作品提炼的实战技巧（§93–§105）

> 本册的技巧**全部来自真实社区作品**：从 24 个 .sb3（3D引擎Plus、Minecraft 3D、超级玛丽（转载）、挖矿猫4、视野盲区引擎、[每周一水]滚动歌词输出引擎、加载特效 / 加载圈引擎、上海地铁1号线开关门模拟器、F_code的开关教程、[拓展]hxb的输入框、跑酷之「坑人の跑酷」、UP主模拟器 RC、羊了个羊、跳一跳3D、纪念碑谷S 瀑布、百吨王-登山赛车、忍者冒险、双人Apple跑酷 ……）里逐块反编译、提炼而成。
>
> 它们补全了前八册没覆盖的四条主线：**状态列表化、UI 克隆化、物理参数化、地图/相机分层化、渲染射线化**——也就是「中大型作品怎么工程化」的套路。
>
> 配套示教工程：`examples/technique_probe11.yaml`（开关阵列 + 平台跳跃 + 阴影光追 + 加载圈，已通过五层校验）。

---

## 社区作品里的「通用铁律」（先看这段，能少踩 80% 坑）

我统计了这 24 个作品的指纹，结论非常一致：

1. **状态进列表，不进零散变量。** 开关状态、地图、歌词、排行榜、关卡进度……几乎全部用「列表」存。一个列表 + 一个 `长度` 就能描述任意复杂的世界。
2. **克隆当一个「单元」用。** 敌人、按钮、粒子、歌词行、UI 卡片——能批量出现的，都用 `create_clone_of` + `start_as_clone`，绝不手写第 2、3、4 个。
3. **能用 `touching 颜色` 就不用 `touching 角色`。** 障碍/碰撞用颜色判定，开销低一个数量级（跑酷、玛丽都这么干）。
4. **⚠️ 别迷信社区扩展。** 滚动歌词用了 `enhance`（画笔增强，提供无限克隆 + 高帧率）。它**不在官方 VM / 本 skill 的无头校验里**，离线跑不了。本册所有配方都用**官方兼容写法**（必要时分页/回收克隆），保证能在标准 Scratch 编辑器里运行。
5. **大项目几乎都「重度广播」+「自定义积木封装」**（24 个项目平均每个 1600+ 次自定义积木调用）。本 skill 的 IR 支持自定义积木，但示例优先用基础积木，保证可读、可校验。

---

## §93 数据驱动的开关 / 门状态机（列表 + 克隆 ID + 广播切换）

**来源**：`F_code的开关教程`、`[开源]上海地铁1号线开关门模拟器v1.2`
**解决的问题**：N 个开关/门，每个状态独立，逐个手写脚本会爆炸。

**思路**：舞台持有 `开关数量` 和一个列表 `开关状态`（每项 0/1）。绿旗时生成 `开关数量` 个克隆，每个克隆带一个 `ID`（= 第几个）；`start_as_clone` 时读 `开关状态[ID]` 决定造型/颜色；收到「切换」广播时按 `ID` 翻转对应格子并刷新外观。上海地铁的「开门/关门」就是每个门 = 列表里一个状态格。

**IR 配方（核心）**：
```yaml
project:
  name: 开关阵列示范
  stage:
    variables: { 开关数量: 4 }
    lists: { 开关状态: [1, 0, 1, 0] }
    broadcasts: { 切换: "切换" }
    scripts:
      - - when_green_flag_clicked: null
        - set_variable: { var: ID计数器, value: 0 }        # 舞台临时计数
        - repeat: { times: { var: 开关数量 }, do:
            [ { change_variable: { var: ID计数器, value: 1 } }
            , { create_clone_of: { clone: 开关 } } ] }
  sprites:
    - name: 开关
      variables: { ID: 0 }
      scripts:
        - - when_green_flag_clicked: null
          - hide: null
        - - start_as_clone: null
          - set_variable: { var: ID, value: { var: ID计数器 } }   # 继承当前计数
          - show: null
          - if: { cond: { equals: [ { item_of_list: { index: { var: ID }, list: 开关状态 } }, 1 ] }
                 , do: [ { set_effect: { effect: COLOR, value: 0 } } ]   # 开=本色
                 , else: [ { set_effect: { effect: COLOR, value: 100 } } ] } # 关=灰
        - - when_receive: { message: 切换 }
          - if: { cond: { equals: [ { var: ID }, { var: 目标ID } ] }   # 只切被点那个
                 , do:
            [ { replace_item_of_list: { index: { var: ID }, list: 开关状态
                  , item: { subtract: [ 1, { item_of_list: { index: { var: ID }, list: 开关状态 } } ] } } } ] }
```
> 简化示意：`目标ID` 由点击逻辑给出（见 §101）。真实作品里「切换」广播只带一个目标编号，所有克隆各自比对 `ID`，只有命中的那个翻转——这就是「广播群发 + 克隆各自过滤」的解耦套路（呼应第七册 §82）。

**坑**：
- Scratch 列表索引**从 1 开始**，循环计数也要从 1。
- 克隆的 `ID` 必须在 `create_clone_of` **之前**用 `change_variable` 递增并让克隆在 `start_as_clone` 里读「生成那一刻的计数器值」；否则所有克隆共享同一初值。
- 翻转用 `1 - 当前值`（纯 0/1 时），别用 `not`（布尔与数字混用会出 bug）。

---

## §94 列表驱动的滚动歌词（每行造型 + 克隆铺排 + 整体上移）

**来源**：`[每周一水]滚动歌词输出引擎`（用了 `enhance` 扩展）
**解决的问题**：一大段歌词随音乐往上滚，当前行高亮。

**思路**：每行歌词做成一张造型（或一段画笔文字），生成克隆铺满屏幕，再让整组随时间上移；当前行放大/变色，越界回收。原作品靠 `enhance` 的「无限克隆 + 60fps」才流畅。

**IR（官方兼容写法，不用 enhance）**：
```yaml
project:
  name: 滚动歌词示范
  stage:
    lists: { 歌词: ["第一句", "第二句", "第三句", "第四句"] }
    variables: { 行号: 1, 滚动Y: 0, 行间距: 40, 速度: 1 }
    scripts:
      - - when_green_flag_clicked: null
        - set_variable: { var: 行号, value: 1 }
        - repeat: { times: { length_of_list: { list: 歌词 } }, do:
            [ { create_clone_of: { clone: 行 } }
            , { change_variable: { var: 行号, value: 1 } } ] }
  sprites:
    - name: 行
      variables: { 我的行号: 1 }
      scripts:
        - - start_as_clone: null
          - set_variable: { var: 我的行号, value: { var: 行号 } }   # 继承
          - say: { text: { item_of_list: { index: { var: 我的行号 }, list: 歌词 } }, secs: 999 }
          - set_variable: { var: y, value: { subtract: [ 180, { multiply: [ { subtract: [ { var: 我的行号 }, 1 ] }, { var: 行间距 } ] } ] } }
          - forever:
            [ { change_variable: { var: y, value: { var: 速度 } } } ]   # 整体上移
```
> 官方兼容要点：用 `say` 气泡显示每行（避免依赖 `enhance` 的无限克隆）。真正要「精美字幕」请用第六册画笔笔迹逐字排版。

**坑**：
- 官方 VM 克隆上限 **300**。歌词行数多要分页（只保留屏幕上 ±N 行）或越界 `delete_this_clone` 回收。
- `enhance` 的「无限克隆 + 高帧率」在官方编辑器里没有；别在交付作品里依赖它，否则别人打不开/卡死。

---

## §95 键盘逐字输入框（缓冲 / 光标 / 数字与文本模式 / 退格）

**来源**：`[拓展]hxb的输入框`（48 变量、22 列表，最完整的输入系统）
**解决的问题**：Scratch 没有原生「输入框」，要做能打字的框。

**思路**：用一个列表当「已输入字符缓冲」；绿旗循环里对需要的键做 `key_pressed` 轮询，按下就 `add_to_list`；退格 `delete` 末项；`input-type` 区分「仅数字 / 文本」，非法字符不接收；另起画笔 sprite 每帧读缓冲拼成字符串（join）画出输入框。

**IR 核心**：
```yaml
project:
  name: 输入框示范
  stage:
    lists: { 输入缓冲: [] }
    variables: { 输入模式: "text", 光标闪烁: 0, 数字白名单: "0123456789", 刚按键: "" }
    scripts:
      - - when_green_flag_clicked: null
        - forever:
          [ { if: { cond: { key_pressed: { key: "a" } }, do: [ { add_to_list: { list: 输入缓冲, item: "a" } } ] }
            , { if: { cond: { key_pressed: { key: "backspace" } }, do:
                [ { if: { cond: { greater_than: [ { length_of_list: { list: 输入缓冲 } }, 0 ] }
                         , do: [ { delete_of_list: { index: { length_of_list: { list: 输入缓冲 } }, list: 输入缓冲 } } ] } ] }
            , { if: { cond: { equals: [ { var: 输入模式 }, "num" ] }
                 , do: [ { if: { cond: { not: { operand: { list_contains: { a: { var: 数字白名单 }, b: { var: 刚按键 } } } } }
                              , do: [ /* 当前键不在白名单 → 拒绝接收 */ ] } ] } } ]
```
> 简化示意：数字模式用一个「白名单字符串 `0123456789`」配合 `list_contains`（输入键 `a`=白名单、`b`=刚按下的键）过滤；文本模式全收。`刚按键` 由轮询逻辑在真正接收前填好。

**坑**：
- Scratch **没有输入框原生控件**，只能 `key_pressed` 逐个键轮询——开销大，**别同时轮询几十个键**，否则掉帧。
- 退格用 `delete_of_list`（索引 = `length_of_list`）删末项，不是 `replace`。
- 实时显示要用画笔（第六册）或把缓冲 `join` 成字符串后 `say` / 画到造型。

---

## §96 平台跳跃核心物理（X/Y 速度 + 重力 + 落地 + 造型状态）

**来源**：`超级玛丽（转载）`、`BallJump`
**解决的问题**：会跳、会落地、会被墙挡、有大小/无敌等状态。

**思路**：玩家持 `XVelocity` / `YVelocity` / `Gravity`；每帧 `YVelocity -= Gravity`、`y += YVelocity`；当 `y <= 地面` 且 `YVelocity < 0` → 落地（速度归零、允许跳）。`AllowPlayerMovement` / `AllowPlayerDamage` / `AllowPlayerPowerup` 等**状态标志**控制时机；`PlayerCostumeNo` 切造型表现状态。

**IR**：
```yaml
project:
  name: 平台跳跃示范
  stage:
    variables: { XVelocity: 0, YVelocity: 0, Gravity: 0.6, 地面Y: -120, 允许跳: 1 }
    scripts:
      - - when_green_flag_clicked: null
        - forever:
          [ { set_variable: { var: YVelocity, value: { subtract: [ { var: YVelocity }, { var: Gravity } ] } } }
          , { change_variable: { var: y, value: { var: YVelocity } } }
          , { if: { cond: { less_than: [ { var: y }, { var: 地面Y } ] }     # 落地
                 , do:
              [ { set_variable: { var: y, value: { var: 地面Y } } }
              , { set_variable: { var: YVelocity, value: 0 } }
              , { set_variable: { var: 允许跳, value: 1 } } ] }
          , { if: { cond: { and: [ { key_pressed: { key: "up" } }, { equals: [ { var: 允许跳 }, 1 ] } ] }
                 , do:
              [ { set_variable: { var: YVelocity, value: 12 } }
              , { set_variable: { var: 允许跳, value: 0 } } ] } ]
```
**坑**：
- 重力每帧减、速度每帧加位移，数值在「逻辑帧」下标定（官方约 30fps 逻辑步）。
- 落地判定用 `y <= 地面Y` 比 `touching 颜色` 更稳（不会卡墙角）。
- 多段跳用计数器限制次数；横向移动同理加 `XVelocity` 再做边界 clamp。

---

## §97 无限跑酷生成器（克隆序列 + 加速度 + 难度递增 + 颜色碰撞）

**来源**：`跑酷之「坑人の跑酷」`、`双人Apple跑酷`
**解决的问题**：障碍源源不断从右往左来，越来越快，且不能让克隆堆爆。

**思路**：用 `关卡数` / `克隆序列` 控制已生成数；定时触发 `create_clone_of` 生成下一个障碍（从右向左移）；`加速度` 随 `关卡` 提升；障碍与玩家用 `touching 颜色` 判定碰撞（比 touching 角色省开销）。

**IR 核心**：
```yaml
project:
  name: 跑酷生成示范
  stage:
    variables: { 关卡: 1, 加速度: 1, 克隆序列: 0, 生成间隔: 40 }
    scripts:
      - - when_green_flag_clicked: null
        - forever:
          [ { set_variable: { var: 克隆序列, value: { add: [ { var: 克隆序列 }, 1 ] } } }
          , { if: { cond: { equals: [ { mod: [ { var: 克隆序列 }, { var: 生成间隔 } ] }, 0 ] }
                 , do: [ { create_clone_of: { clone: 障碍 } } ] }
          , { if: { cond: { equals: [ { var: 克隆序列 }, { multiply: [ { var: 关卡 }, 200 ] } ] }
                 , do: [ { change_variable: { var: 加速度, value: 0.05 } }
                       , { change_variable: { var: 关卡, value: 1 } } ] } ]
  sprites:
    - name: 障碍
      scripts:
        - - start_as_clone: null
          - set_variable: { var: x, value: 240 }
          - forever:
            [ { change_variable: { var: x, value: { subtract: [ 0, { var: 加速度 } ] } } }
            , { if: { cond: { less_than: [ { var: x }, -240 ] }, do: [ { delete_this_clone: null } ] } } ]
```
**坑**：
- 障碍**必须 `delete_this_clone` 回收**，否则 300 上限瞬间填满。
- 碰撞用颜色（`touching 颜色`）而非 `touching 角色`，开销低。
- 难度递增别让 `加速度` 无上限（会穿模/瞬移）。

---

## §98 体素 3D 与射线步进（第三人称方块世界）

**来源**：`Minecraft 3D`（151 变量、23 列表）
**解决的问题**：在 Scratch 里渲染一个能走、能挖、能放的方块世界。

**思路**：世界是网格（`MazeWidth` / `TileIndex`），玩家持 `PlayerX/Y/Z` 与朝向 `PlayerRot`；从眼睛沿 `RayAngle` 做射线步进（DDA）撞到方块就停，按距离着色（远暗近亮）画出该列 → 第一/三人称体素渲染。`BoxHighlighted` / `BlockTypeSelected` 用于放置/破坏。

**IR（射线步进一列，简化为 2D 俯视射线）**：
```yaml
project:
  name: 体素射线示范
  stage:
    lists: { 地图: [0,1,1,0, 1,1,0,1, 0,0,1,1, 1,1,1,0] }   # 4x4 瓦片，1=墙
    variables: { 玩家X: 1.5, 玩家Y: 1.5, 射线角: 0, 距离: 0, 命中: 0, 最大距离: 16, 步长: 0.2 }
    scripts:
      - - when_green_flag_clicked: null
        - repeat: { times: 60, do:                          # 每列一束射线
            [ { set_variable: { var: 射线角, value: { subtract: [ { multiply: [ { var: 列 }, 1.2 ] }, 36 ] } } }
            , { set_variable: { var: 距离, value: 0 } }, { set_variable: { var: 命中, value: 0 } }
            , { repeat_until: { cond: { or: [ { equals: [ { var: 命中 }, 1 ] }, { greater_than: [ { var: 距离 }, { var: 最大距离 } ] } ] }
                , do:
              [ { change_variable: { var: 距离, value: { var: 步长 } } }
              , { set_variable: { var: 采样X, value: { add: [ { var: 玩家X }, { multiply: [ { mathop: { op: cos, num: { var: 射线角 } } }, { var: 距离 } ] } ] } } }
              , { set_variable: { var: 采样Y, value: { add: [ { var: 玩家Y }, { multiply: [ { mathop: { op: sin, num: { var: 射线角 } } }, { var: 距离 } ] } ] } } }
              , { if: { cond: { equals: [ { item_of_list: { index: { add: [ { multiply: [ { floor: [ { var: 采样Y } ] }, 4 ] }, { floor: [ { var: 采样X } ] } ] }, list: 地图 } }, 1 ] }
                     , do: [ { set_variable: { var: 命中, value: 1 } } ] } ] } ] }
```
> 这是第六册 §70「射线迷宫」的 **3D 升级**：世界用列表存方块 ID（瓦片地图），射线步进注意**除零**与**最大距离熔断**（否则死循环）。

**坑**：
- 体素射线要算 `floor(采样Y)*宽 + floor(采样X)` 当列表索引，越界要先 clamp。
- 第三人称要把玩家位置从视野中心偏移，否则永远看自己脚底。
- 着色按 `距离` 做亮度衰减（远暗近亮），才有体积感。

---

## §99 ★ 视野盲区引擎：2D 可见性多边形与阴影光追

**来源**：`视野盲区引擎（纯原版可运行 模拟阴影光追）` —— **本册最稀缺、八册均未覆盖**
**解决的问题**：一盏「眼睛/手电筒」放在房间里，要算出「哪些区域看得见、哪些被墙挡成盲区」，并画出阴影。

**思路（经典 visibility polygon）**：给每堵墙的每个「墙角」算「玩家→墙角」的夹角；把墙角按夹角排序，沿相邻墙角连射线，所有射线围成的区域就是可见多边形。实体（怪/道具）若落在「某墙角与玩家之间、且更近」就判定为盲区。

> ⚠️ **Scratch 3 没有 `atan2` 积木**（scratch-vm 未实现），写 `atan2` 会**静默返回 0**，
> 整个算法看起来跑通了但结果全错。角度要用 `mathop` 的 `atan`（单位：度）自己拼，
> 详见下面的 `算角度` 过程；或者干脆**用向量代替角度**（见专项教程）。
> 严谨版（线段求交 + 可见性多边形）见 **`references/deep-shadow-raycasting.md`**，
> 配套可运行工程 **`examples/technique_probe13.yaml`**。

**简化可构建版（玩家 + 若干墙角 + 一个待测实体）**：
```yaml
project:
  name: 阴影光追示范
  stage:
    variables: { 玩家X: 0, 玩家Y: 0, 序号: 1, 实体X: 80, 实体Y: 30, 实体在阴影: 0
               , 最近角差: 999, 最近墙距: 999, 实体角: 0, 实体距: 0, 角度: 0, dX: 0, dY: 0 }
    lists: { 墙角X: [100, -100, 100, -100], 墙角Y: [100, 100, -100, -100], 与玩家夹角: [0, 0, 0, 0] }
    # ⚠️ 自定义积木用 atan + 分支拼出 atan2（Scratch 没有 atan2）
    procedures:
      - name: 算角度 %n %n
        args: [入Y, 入X]
        warp: true
        script:
          - if: { cond: { greater_than: [ { var: 入X }, 0 ] }, do: [
              - set_variable: { var: 角度, value: { mathop: { op: atan, num: { divide: [ { var: 入Y }, { var: 入X } ] } } } } ] }
          - if: { cond: { less_than: [ { var: 入X }, 0 ] }, do: [
              - set_variable: { var: 角度, value: { mathop: { op: atan, num: { divide: [ { var: 入Y }, { var: 入X } ] } } } }
              - if: { cond: { less_than: [ { var: 入Y }, 0 ] }, do: [
                  - set_variable: { var: 角度, value: { subtract: [ { var: 角度 }, 180 ] } } ] }
              - if: { cond: { greater_than: [ { var: 入Y }, 0 ] }, do: [
                  - set_variable: { var: 角度, value: { add: [ { var: 角度 }, 180 ] } } ] } ] }
    scripts:
      - - when_green_flag_clicked: null
        # 1) 算所有墙角与玩家的夹角
        - set_variable: { var: 序号, value: 1 }
        - repeat: { times: { length_of_list: { list: 墙角X } }, do:
            [ { set_variable: { var: dX, value: { subtract: [ { item_of_list: { index: { var: 序号 }, list: 墙角X } }, { var: 玩家X } ] } } }
            , { set_variable: { var: dY, value: { subtract: [ { item_of_list: { index: { var: 序号 }, list: 墙角Y } }, { var: 玩家Y } ] } } }
            , { call: { proc: 算角度 %n %n, args: [ { var: dY }, { var: dX } ] } }
            , { replace_item_of_list: { index: { var: 序号 }, list: 与玩家夹角, item: { var: 角度 } } }
            , { change_variable: { var: 序号, value: 1 } } ] }
        # 2) 判实体是否被某墙角遮挡
        - call: { proc: 算角度 %n %n, args: [ { subtract: [ { var: 实体Y }, { var: 玩家Y } ] }, { subtract: [ { var: 实体X }, { var: 玩家X } ] } ] }
        - set_variable: { var: 实体角, value: { var: 角度 } }
        - set_variable: { var: 实体距, value: { mathop: { op: sqrt, num: { add: [ { multiply: [ { subtract: [ { var: 实体X }, { var: 玩家X } ] }, { subtract: [ { var: 实体X }, { var: 玩家X } ] } ] }, { multiply: [ { subtract: [ { var: 实体Y }, { var: 玩家Y } ] }, { subtract: [ { var: 实体Y }, { var: 玩家Y } ] } ] } ] } } } }
        - set_variable: { var: 序号, value: 1 }
        - set_variable: { var: 最近角差, value: 999 }
        - set_variable: { var: 最近墙距, value: 999 }
        - repeat: { times: { length_of_list: { list: 墙角X } }, do:
            [ { set_variable: { var: 角差, value: { mathop: { op: abs, num: { subtract: [ { var: 实体角 }, { item_of_list: { index: { var: 序号 }, list: 与玩家夹角 } } ] } } } } }
            # 角度环绕：170° 与 -170° 的实际夹角是 20°，不是 340°
            , { if: { cond: { greater_than: [ { var: 角差 }, 180 ] }, do:
                  [ { set_variable: { var: 角差, value: { subtract: [ 360, { var: 角差 } ] } } } ] } }
            , { set_variable: { var: 墙距, value: { mathop: { op: sqrt, num: { add: [ { multiply: [ { subtract: [ { item_of_list: { index: { var: 序号 }, list: 墙角X } }, { var: 玩家X } ] }, { subtract: [ { item_of_list: { index: { var: 序号 }, list: 墙角X } }, { var: 玩家X } ] } ] }, { multiply: [ { subtract: [ { item_of_list: { index: { var: 序号 }, list: 墙角Y } }, { var: 玩家Y } ] }, { subtract: [ { item_of_list: { index: { var: 序号 }, list: 墙角Y } }, { var: 玩家Y } ] } ] } ] } } } }
            , { if: { cond: { less_than: [ { var: 角差 }, { var: 最近角差 } ] }
                   , do: [ { set_variable: { var: 最近角差, value: { var: 角差 } } }, { set_variable: { var: 最近墙距, value: { var: 墙距 } } } ] }
            , { change_variable: { var: 序号, value: 1 } } ] }
        # 3) 最近的那堵墙若比实体更近 → 实体在阴影/盲区
        # ⚠️ 带 else 必须写 if_else：control_if 没有 else 槽位，写 if 会把 else 静默丢弃
        - if_else: { cond: { less_than: [ { var: 最近墙距 }, { var: 实体距 } ] }
              , do: [ { set_variable: { var: 实体在阴影, value: 1 } } ]
              , else: [ { set_variable: { var: 实体在阴影, value: 0 } } ] }
```
**为什么比第六册的 DDA 射线迷宫更强**：
- DDA（§70）只回答「沿**某一条**射线撞到什么」——用于迷宫第一人称。
- 本技巧回答「眼睛**整个能看见的区域**」——用于 2D 光照、潜行游戏的视野、塔防的侦测范围。
- 真实作品还做了「按墙角夹角排序 → 相邻墙角连射线 → 填充多边形」来画出阴影；headless 看不到画面，需在编辑器目视确认。

**坑**：
- ⚠️ **Scratch 3 没有 `atan2` 积木**（scratch-vm 只实现 add/sub/mul/div/比较/逻辑/mathop 等），
  写 `atan2` 会静默返回 0。只能用 `mathop` 的 `atan` 自己拼，或改用向量（见专项教程）。
- ⚠️ `if` 带 `else` 必须用 `if_else`：`control_if` 只有 SUBSTACK 一个子栈槽位，else 会被**静默丢弃**。
- ⚠️ 角度要处理环绕：170° 与 -170° 的夹角是 20°，不是 340°。
- ⚠️ 自定义积木**共享全局变量**：过程内部的循环变量不要和调用方重名，否则会把调用方的索引冲掉。
- 排序墙角后才能正确连成可见多边形；不排序会得到乱线。
- 多个实体要各自跑一遍「2)+3)」，建议封装成自定义积木（输入：实体X/Y）。

---

## §100 加载特效与旋转圈（画笔弧线累积 / 克隆分段旋转）

**来源**：`加载特效`、`加载圈引擎（win10 ,win8）`、`加载特效（改编）`
**解决的问题**：做一个「加载中…」的动画。

**两种做法**：
**做法 A（画笔弧）**：一个 sprite 落笔、把方向转一圈（repeat 画弧），`pen_size` + 颜色做进度环。
```yaml
project:
  name: 加载弧示范
  stage:
    variables: { 画笔方向: 0 }
    scripts:
      - - when_green_flag_clicked: null
        - pen_clear: null; pen_down: null; set_pen_size: { size: 8 }
        - repeat: { times: 27, do:        # 画 27 段弧
            [ { change_variable: { var: 画笔方向, value: 1 } }
            , { turn_right: { degrees: { var: 画笔方向 } } }
            , { move_steps: { steps: 4 } } ] }
```
**做法 B（克隆分段）**：错峰生成若干克隆，每个只负责画一段弧（repeat 转固定角度），相位不同 → 形成转动的加载环。
```yaml
project:
  name: 加载圈示范
  stage:
    variables: { 旋转: 0 }
    scripts:
      - - when_green_flag_clicked: null
        - repeat: { times: 6, do: [ { create_clone_of: { clone: 加载 } }, { wait: { secs: 0.13 } } ] }
  sprites:
    - name: 加载
      scripts:
        - - start_as_clone: null
          - show: null; set_variable: { var: 旋转, value: 25 }
          - repeat: { times: 12, do: [ { turn_right: { degrees: { var: 旋转 } } }, { move_steps: { steps: 3 } } ] }
          - delete_this_clone: null
```
**坑**：
- 画笔在 headless 不渲染但能跑通；正式效果需在编辑器看。
- 克隆分段法**必须 `delete_this_clone`** 收尾，否则无限堆积。
- 想要「转得顺」就把段数调细、克隆数调多。

---

## §101 克隆驱动的 UI 组件系统（按编号路由点击 / 网格行列）

**来源**：`UP主模拟器 RC`（`*克隆体_克隆编号/_x/_y/_身份`）、`羊了个羊`（点击行号/列号）
**解决的问题**：一大片按钮/卡片/格子，点击要精准路由到对应逻辑。

**思路**：UI 元素都用克隆；每个克隆带唯一 `克隆编号` / `身份`，并记录自己的 `x,y`。点击时用 `touching_mouse_pointer` + `mousedown` 命中该克隆，再按 `克隆编号` 路由。`羊了个羊` 这类网格用「坐标→行列」反算：
`点击行号 = floor((起点Y - mouse_y) / 格高)`、`点击列号 = floor((mouse_x - 起点X) / 格宽)`，比逐格 `touching` 快得多（O(1) vs O(格子数)）。

**IR 核心（网格点击）**：
```yaml
project:
  name: 网格点击示范
  stage:
    variables: { 起点X: -180, 起点Y: 150, 格宽: 60, 格高: 60, 点击行号: 0, 点击列号: 0 }
    scripts:
      - - when_green_flag_clicked: null
        - forever:
          [ { if: { cond: { mousedown: null }, do:
              [ { set_variable: { var: 点击行号, value: { mathop: { op: floor, num: { divide: [ { subtract: [ { var: 起点Y }, { mouse_y: null } ] }, { var: 格高 } ] } } } } }
              , { set_variable: { var: 点击列号, value: { mathop: { op: floor, num: { divide: [ { subtract: [ { mouse_x: null }, { var: 起点X } ] }, { var: 格宽 } ] } } } } } ] } ]
```
**坑**：
- 网格点击用「坐标→行列」反算，O(1)，**远快于**逐个 `touching`。注意 y 轴朝上，行号公式里用 `起点Y - mouse_y`。
- 克隆 UI 的「编号」必须唯一且**生成时赋值**，否则点击路由错乱。
- `mousedown` 是 Scratch 的「鼠标是否按下」积木（本 skill 别名 `mousedown`）。

---

## §102 滚动瓦片地图相机（CAM 偏移 + 多层 + 洞穴分层）

**来源**：`挖矿猫4`（`CAM.x/y`、`WORLD tile size`、`Layers to create`、`_cave x/y`）
**解决的问题**：世界比屏幕大得多，要平滑卷动。

**思路**：用 `CAM.x/CAM.y` 当相机左上角；每个 tile 的「世界坐标」减相机坐标得「屏幕坐标」再绘制。多层（地表/洞穴）用 `Layers to create` 控制生成哪几层；玩家移动时改 CAM 实现卷动。**关键**：相机偏移后做「屏幕外隐藏」，否则 tile 爆炸。

**IR 核心**：
```yaml
project:
  name: 瓦片相机示范
  stage:
    variables: { CAMx: 0, CAMy: 0, 瓦片: 40, 玩家X: 0, 玩家Y: 0 }
    scripts:
      - - when_green_flag_clicked: null
        - forever:
          [ { set_variable: { var: CAMx, value: { subtract: [ { var: 玩家X }, 240 ] } }   # 玩家居中
            , { set_variable: { var: CAMy, value: { subtract: [ { var: 玩家Y }, 180 ] } } } ]
  sprites:
    - name: 地块
      variables: { 世界X: 0, 世界Y: 0 }
      scripts:
        - - when_green_flag_clicked: null
          - forever:
            [ { set_variable: { var: x, value: { subtract: [ { var: 世界X }, { var: CAMx } ] } } }
            , { set_variable: { var: y, value: { subtract: [ { var: 世界Y }, { var: CAMy } ] } } }
            , { if: { cond: { or: [ { greater_than: [ { var: x }, 240 ] }, { less_than: [ { var: x }, -240 ] } ] }
                   , do: [ { hide: null } ], else: [ { show: null } ] } ]
```
**坑**：相机偏移后**必须屏幕外隐藏/显示**，否则几十上百个 tile 同时渲染直接卡死。多层切换用变量控制渲染哪一层。

---

## §103 本地排行榜（列表排序 / 名次 / 我的排行）

**来源**：`跳一跳3D`（`排行榜变量`、`我的排行`）
**解决的问题**：记录成绩并告诉玩家排第几。

**思路**：成绩存列表 `排行榜`；新成绩进来后插入并排序；`我的排行 = item_num_of_list(排行榜, 我的成绩)` 得到名次（`item_num_of_list` 返回某值首次出现的位置 = 名次）。

**IR**：
```yaml
project:
  name: 排行榜示范
  stage:
    lists: { 排行榜: [120, 95, 80, 60] }
    variables: { 我的成绩: 88, 我的排行: 0 }
    scripts:
      - - when_green_flag_clicked: null
        - add_to_list: { list: 排行榜, item: { var: 我的成绩 } }
        - set_variable: { var: 我的排行, value: { item_num_of_list: { list: 排行榜, item: { var: 我的成绩 } } } }
```
**坑**：
- `item_num_of_list` 找的是「首次出现」，若列表有**重复成绩**名次会偏前。
- 要精确名次：先排序（冒泡/选择）再查，或直接维护有序插入（找到第一个比自己小的位置插入）。
- 跨局持久化要用「云变量」或本地存档（超出本技巧范围）。

---

## §104 等距多层机关关卡（yx/yy 等距坐标 + 机关锁 + 路径）

**来源**：`纪念碑谷S 瀑布`（`yx/yy`、`机关锁`、`关三层数`、`F_地图x/y`、`总路径`、`F_i最近距离`）
**解决的问题**：做纪念碑谷式等距迷宫 + 可移动机关 + 多层。

**思路**：用等距坐标 `yx/yy`（第六册 §71 等距投影的**逆**：屏幕↔网格）表示可走格；`机关锁` / `柱子移动状态` 驱动谜题；`F_地图x1/y1/x2/y2` 存路径点，`F_i最近距离` 做「找最近可达点」的自动吸附/寻路。

**IR（等距网格 ↔ 屏幕）**：
```yaml
project:
  name: 等距关卡示范
  stage:
    variables: { 格宽: 40, 格高: 20, 原点X: 0, 原点Y: 0, gx: 0, gy: 0 }
    scripts:
      - - when_green_flag_clicked: null
        # 网格(gx,gy) -> 屏幕
        - set_variable: { var: 屏幕x, value: { add: [ { var: 原点X }, { multiply: [ { subtract: [ { var: gx }, { var: gy } ] }, { divide: [ { var: 格宽 }, 2 ] } ] } ] } }
        - set_variable: { var: 屏幕y, value: { add: [ { var: 原点Y }, { multiply: [ { add: [ { var: gx }, { var: gy } ] }, { divide: [ { var: 格高 }, 2 ] } ] } ] } }
```
**坑**：
- 等距的**深度排序**必须用 `gx + gy` 决定前后（值大的后画），否则遮挡错乱。
- 多层（`关三层数`）要按层分别管理「可走集合」，别让不同层的格子互相穿。
- 自动寻路用「最近可达点」（`F_i最近距离`）做吸附，比全图 A* 轻量，适合解谜。

---

## §105 滚动相机 + 地形视差（scroll_x/y + 电视背景层 + 旋转车体）

**来源**：`百吨王-登山赛车`（`scroll_x/scroll_y`、`tv_x/tv_y`、`sx/sy`、`lx/ly`）
**解决的问题**：赛车沿地形前进，背景要有「远近层次」的纵深感。

**思路**：`scroll_x/y` 是相机滚动量；背景分「远层(tv)」「近层(lx/ly)」以**不同速度**移动实现视差（远慢近快）；车体用 `旋转` 随坡度倾斜。

**IR 核心**：
```yaml
project:
  name: 视差滚动示范
  stage:
    variables: { scroll_x: 0, 速度: 3, 视差远: 0.3, 视差近: 1, tv_x: 0, lx: 0 }
    scripts:
      - - when_green_flag_clicked: null
        - forever:
          [ { change_variable: { var: scroll_x, value: { var: 速度 } } }
          , { set_variable: { var: x, value: { subtract: [ { var: tv_x }, { multiply: [ { var: scroll_x }, { var: 视差远 } ] } } } }   # 远层
          , { set_variable: { var: x, value: { subtract: [ { var: lx }, { multiply: [ { var: scroll_x }, { var: 视差近 } ] } } } } ]   # 近层
```
**坑**：
- 视差就是「不同层 × 不同滚动系数」，系数**远 < 近**。
- 地形坡度用 `mathop` 的 `atan` 算车体倾角：坡度(度) = `atan(Δy / Δx)`（`Δx>0` 时），
  再 `turn_right` 或直接设 `direction`。⚠️ Scratch 3 **没有 `atan2`**，
  `Δx<0` 时需自己补 ±180°（做法见 §99 的 `算角度` 过程）。
- 背景层要**平铺/循环**，否则滚一段就空了（用 `如果 x < -宽 then x += 宽` 做循环）。

---

## 本册小结

这 13 套（§93–§105）把「大项目工程化」的主线补全：

| 主线 | 对应技巧 |
|---|---|
| 状态列表化 | §93 开关状态机、§94 歌词、§103 排行榜 |
| UI 克隆化 | §93/§94 克隆阵列、§97 障碍、§100 加载环、§101 克隆 UI |
| 物理参数化 | §96 平台跳跃、§97 难度递增、§105 坡度 |
| 地图/相机分层化 | §98 体素、§102 瓦片相机、§104 等距多层、§105 视差 |
| 渲染射线化 | §98 体素射线、§99 可见性多边形、§100 画笔弧 |

配合前八册，即可覆盖社区 **90% 中大型作品**的核心套路。所有配方遵循同一铁律：**能进列表的别散成变量，能克隆的别手写，能用颜色的别用角色，能在官方 VM 跑的别依赖社区扩展。**

---

# 补充册（2026-11-06 增补）：11 个新开源作品提炼 · §C1–§C5

> 本批 11 个作品全部从小码王探索页（`type=3` 开源）下载，经 `filter_scratch_blocks.py` 过滤（仅 FNAF 含 3 个非 Scratch 积木被剔除，其余 0 剔除）后用 `analyze.py` 拆解。

## §C1 背景驱动的场景 / 房间状态机（`当背景换成` × N，无精灵房间系统）

**来源**：`FNAF Never Along(0.24)`（pGeJJ66J；29 角色 / 1005 积木 / `当背景换成` 触发 85 次 / 13 条广播）

**解决的问题**：恐怖 / 生存 / 剧情游戏要在很多"房间 / 场景"间切换。若为每个房间摆精灵，角色数与遮挡逻辑会爆炸。

**思路**：把**房间画进背景造型**，切房间 = `换成背景 X`；场景逻辑不挂精灵，而用 `当背景换成 [X]` 事件帽触发——背景一变，对应脚本组自动跑（显示哪些道具、刷新 HUD、播环境音）。FNAF 的监控室 / 走廊 / 门厅全靠这套驱动，85 个 `当背景换成 X` 就是 85 个房间钩子。

**要点**
- 背景造型名带语义（`room_office` / `hall_left`…），`当背景换成` 里填同名造型。
- HUD / 固定 UI 用"永远在最上层"的独立精灵，切房间只改背景不动 UI。
- 房间内可交互物用克隆按房间号显隐，避免为每个房间建角色。
- 跨房间事件走广播（如电力耗尽 → 广播 → 各房间钩子响应）。

**适用**：FNAF 类监控/恐怖、点击式解谜、多场景剧情。

---

## §C2 克隆海生存循环（克隆当实体 + 列表当世界 + 碰撞判定）

**来源**：`小猫生存1.0.3`（jmIo666J；16 角色 / 808 积木 / 克隆 41 / 列表操作 37 / 广播 43 / `碰到角色` 24）

**思路**：生存游戏三件套——
1. **世界数据进列表**（资源点、敌人刷新表、背包）；
2. **实体用克隆批量生成**（食物/敌人/掉落各一个母体，按列表刷克隆并带私有 `ID`）；
3. **碰撞用 `碰到 [角色]` + 距离**判定，命中后改列表/变量并回收克隆。
生存压力（饥饿/血量/时间）走全局变量，`重复执行` 每帧递减，归零触发结算广播；`广播 43` 主要做"刷怪/结算/切阶段"解耦。

**坑**：克隆上限 300，刷怪要"回收+复用"而非无限 `create_clone`；克隆体必须用私有 `是克隆` 挡住本体事件帽（铁律 11）。

---

## §C3 列表即迷宫网格（一维列表存二维地图 + 索引换算）

**来源**：`迷宫寻宝`（2SwJJ66J；3 角色 / 115 积木 / 列表操作 21）

**思路**：把 `宽×高` 迷宫塞进**一个一维列表**（行优先），格子 `(x,y)` 的索引 = `y*宽 + x + 1`。移动只改玩家 `(x,y)`，再查列表判断该格是墙/路/宝藏。比"每格一个克隆"省几百个克隆，也回避 Scratch 无原生二维列表的问题。

**要点**
- 地图初始化：把地图表格/字符串展开成一维列表（`data_addtolist` 循环）。
- 越界先判 `x<0 或 x>=宽` 再查列表，避免索引错位。
- 墙/路/宝藏/终点用不同数值编码（0/1/2/3），一列数值走天下。

---

## §C4 极简音频序列播放器（单精灵 `播放声音`+`等待` 链 + 造型同步）

**来源**：`双阶乘简版素材+0!!-37!!音乐`（3AwJJ66J；1 角色 / 211 积木 / 无广播，几乎全是 `播放声音`+`等待`）

**思路**：当"音乐本身就是内容"时不需要状态机——一个精灵按序 `换成造型 → 播放声音 X → 等待 N 秒`，展开整首曲子；造型只是"当前音符/数字"的视觉反馈。这是做**音乐教学 / 数字方块儿歌 / 节奏演示**最省事的写法。

**要点**
- 每个音符一条"播放声音 + 等待 = 该音符时值"，等待值 = `60/BPM × 拍数`。
- `停止该角色的其他脚本` 处理"切曲时打断上一首"。
- 音高方向遵循铁律 18（音高升 = 语义升）。
- 曲子长时把序列拆成多段自制积木，避免单脚本过长。

---

## §C5 广播编排的"数字方块乐队"音乐可视化（指挥者 + 方块接收者）

**来源**：`Number blocks Band 51-60`（rMwJJ66J）、`数字方块 Ultra Omega Giga 不同 100 / 41`（NGwJJ66J / bkiJJ66J）、`数字方块恐怖扭曲 1-10/11-20/21-30`（JCS6J66J / hKS6J66J / fSS6J66J）——7 个同源作品，12–21 角色 / 300–730 积木 / **广播 34–75 次**

**思路**：数字方块系列的统一骨架——**一个指挥者按乐谱发广播，每个方块是接收者**：
1. 指挥者（或舞台）按节拍 `广播 [音符 N]`，`广播并等待` 保证严格顺序；
2. 每个方块 `当接收到 [自己的音符]` → `换成造型(发声态) → 播放声音 → 等待时值 → 换成造型(静默态)/隐藏`；
3. 序号/音高大量用 `运算符`（`编号 = 起始 + 序号`）与 `随机数`，做出"不同 100 / 不同 41"的花样；
4. 视觉上用 `将 [颜色/亮度] 特效设定为` + `面向方向` 做扭曲/发光（恐怖扭曲系列靠这个）。

**为什么值得学**：它把"多声部音乐"拆成"广播 + 每角色一个接收帽"，天然并行、天然可扩到 100 个方块，且**全部官方积木**（不依赖扩展乐器）。做音乐可视化 / 节奏打击 / 数字方块儿歌直接套此骨架。

**坑**
- 用 `广播并等待` 而非 `广播` 才能保证音符严格按谱走；只有和弦才用普通 `广播` 让多方块同响。
- 方块上百时注意克隆上限，用"母体按编号换造型"而非每方块一个克隆。
- "扭曲感"来自高 `颜色特效` + `亮度` + 逐帧 `面向方向` 抖动，不是换素材（呼应铁律 15：质感靠曲线）。
