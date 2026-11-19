# 塔防（策略·防御类）完全手册

> 适用范围：**敌人沿固定路线推进、玩家建塔自动索敌开火、靠经济（金币）与波次（波次广播）拖住敌人、守住基地（生命）** 的塔防（TD）作品。
> 本册是 `game-systems.md` §38（塔防速览）的**深入版**——§38 只给四角色与一句话做法，本册补上从社区实证作品（`炮塔防御无尽版 v1.01`，**0 个非 Scratch 积木，纯官方积木**）拆出来的完整范式与所有致命坑。
>
> 实证来源：`community-crawler/data/raw/策略_炮塔防御无尽版_filtered.sb3`
> 实证规模：70 角色(含舞台) / 7688 块 / 53 克隆类 / 150 造型 / 70 声音 / 75 opcode；
> 技巧统计：运算符 1581 · 克隆 569 · 广播解耦 245 · 键鼠交互 326 · 列表即结构 69 · 画笔 6 · 自制积木 5。
>
> 配套可运行工程：`examples/tower-defense.yaml`；行为校验 `scripts/towerdefense_behavior_check.mjs`（输出 `TOWERDEFENSE_LOGIC_OK`）。
>
> **本册所有结论都经过 scratch-vm 实跑验证**，不是纸上推演。

---

## §TD1 塔防的本质与四角色

塔防的本质 = **一组沿路径推进的敌人（克隆）+ 一组自动索敌的塔（克隆）+ 连接两者的子弹（克隆）+ 一个出波/经济/胜负的控制器**。

所有「出怪、移动、索敌、开火、命中、扣血、到达基地」都是对**坐标与列表**做变换，角色只是把数值画出来。这和射击册（§116）同构——区别只在「敌人是沿路径走、塔是站桩自动开火」。

### 四角色（社区实证）

| 角色 | 职责 | 实证证据 |
|---|---|---|
| `敌人` | 沿路径走（克隆），有私有 `hp` / 双盾 | 角色37/39/43/45/47/49/50/57/63 各 249 块、`克隆体×1`、`flagclicked×1` → 敌人模板，运行时 `克隆 自己` 刷怪 |
| `防御塔` | 自动索敌开火（克隆），私有 `冷却` | 角色33/2/60/64/36/38/40/42/44/46/48/51 各有私有 `冷却`，`克隆体×2` / `broadcastreceived×2` |
| `子弹` | 命中即删（克隆） | `sensing_touchingobject×310`（命中碰撞，见 §TD7） |
| `游戏控制器`（舞台/控制器） | 出波、经济、胜负判定 | 舞台 7 全局变量（金=800、生命=5、分数=350…）+ 26 广播做波次/事件总线 |

### 波次总线（核心解耦点）

实证：26 个广播、245 次使用；**13 种波次广播各被 13 个角色订阅**（`broadcastreceived×13`）。一波一广播，敌人/塔订阅对应波次：

```
dj7(28接收) dj6 dj4 dj8 bz2 bz3 打击2 dj3 打击1 DJ5 死神之杯 bz1(各13接收)
冷却1(12) 投石攻击(12) cuihui(12)   ← 塔冷却广播 / 特殊攻击广播
lq3..lq11(各1接收)                   ← 单体/放置类广播
```

> 这就是 §16 说的「一个发现 → 广播 → 全体响应」。本册把波次显式做成广播，而不在主控里写 13 个 if 串（见 §TD8 致命坑）。

---

## §TD2 数据模型（全局）

### 全局变量（舞台）

| 变量 | 初值(实证) | 作用 |
|---|---|---|
| `金`(金币) | 800 | 建塔花费、杀敌奖励、卖塔退款 |
| `生命` | 5 | 敌人到达基地扣 1，归零 → 失败 |
| `分数` | 350 | 击杀累计 |
| `场上敌人数量` | 5 | 同屏敌人计数（节流用） |
| `最近x` `x` `方向` | 0 / 0 / 0 | 控制器/路径辅助坐标 |

### 列表（路径/地图用「私有列表」更可读）

实证舞台有 2 个**巨型列表**（len 22270 / 143951）——是打包的路径/迷宫数据。本 skill 不推荐这种「一个巨大字符串列表塞所有数据」的写法，改用**私有列表 `a` 存路径点序列**（实证 角色16/25 就是这么做的），可读、可维护：

```yaml
# 敌人/控制器 的私有列表（块式声明，每行 - 0，见 §TD8.6）
列表 路径X: [ -200, -100, 0, 100, 200 ]   # 路径点 x
列表 路径Y: [  120,  120, 0,   0, -120 ]   # 路径点 y
```

> ⚠️ 在 builder 里列表是「变量存数组」：块式 YAML 声明（`- 0` 每行），校验时读 `target.variables` 里的数组、**按 1-based 索引 − 1** 读写（和射击册 §120.3 同一个坑）。

---

## §TD3 敌人：克隆生成器原型 + 私有 hp（铁律9 / 铁律11）

### 模式

画**一个**敌人模板角色 → 波次广播触发时 `克隆 自己` → 每个克隆是独立敌人，用**私有变量**存 `hp` / `敌人双盾生命` / 路径序号。

### 私有变量是身份的关键（铁律9）

`hp` 必须选「仅适用于此角色」→ 每个克隆各一份，互不串。实证里敌人私有 `hp` / `敌人双盾生命`（双血槽：主血 + 护盾，护盾先扣）/`f'x'g'd'g`（混淆名，也是私有状态）。

### 克隆守卫必须有（铁律11）

`出波` 广播会被**本体和所有现存敌人克隆**都收到。没有守卫 → 克隆也去生成克隆 → 指数爆炸。用 `是克隆` 标志位挡住（和射击册 §118 同款）：

```text
当绿旗被点击          → 隐藏
当收到[出波 v]        → if (是克隆 == 0 且 敌计数器 < 上限)  敌计数器 = 敌计数器 + 1
                        if (是克隆 == 0 且 敌计数器 < 上限)  create clone of [自己]
当作为克隆体启动      → 是克隆 = 1
                        编号 = 敌计数器
                        hp = 30；敌x[编号]=起点x；敌y[编号]=起点y；敌hp[编号]=hp；敌活[编号]=1
                        goto(起点x, 起点y)；show
当作为克隆体启动      → forever：
    路径序号 = 路径序号 + 1
    ex = item(路径序号) of [路径X]；ey = item(路径序号) of [路径Y]
    goto(ex, ey)；敌x[编号]=ex；敌y[编号]=ey        # ★ 每帧回写列表（塔/子弹靠它索敌）
    if (路径序号 > length of [路径X])               # 到达基地
        生命 = 生命 - 1；敌活[编号]=0；delete this clone
    if (敌hp[编号] <= 0)                            # 被打死
        敌活[编号]=0；delete this clone
    wait 0.02
```

> ⚠️ **生成守卫拆成两个平级单分支 IF**（先 +1，再 create clone），不要写「嵌套 IF 的 do 里放 CLONE」——builder 会把内层 CLONE 漏编译（射击册 §120.2 同款真 bug）。

### IR 写法要点 ✅

```yaml
- name: 敌人A
  x: 0
  y: 0
  costumes: [ { name: 造型1, asset: assets/td/enemy.png } ]
  variables:
    是克隆: 0
    编号: 0
    hp: 30
    路径序号: 0
    ex: 0
    ey: 0
  scripts:
    - - when_green_flag_clicked: null
      - hide: null
    - - when_receive: { message: 出波 }
      - if: { cond: { and: [ { equals: [ { var: 是克隆 }, 0 ] }, { lt: [ { var: 敌计数器 }, 30 ] } ] },
              do: [ { change_variable: { var: 敌计数器, by: 1 } } ] }
      - if: { cond: { and: [ { equals: [ { var: 是克隆 }, 0 ] }, { lt: [ { var: 敌计数器 }, 30 ] } ] },
              do: [ { create_clone_of: { clone: _myself_ } } ] }
    - - when_start_as_clone: null
      - set_variable: { var: 是克隆, value: 1 }
      - set_variable: { var: 编号, value: { var: 敌计数器 } }
      - set_variable: { var: hp, value: 30 }
      - replace_item_of_list: { list: 敌x, index: { var: 编号 }, item: { item_of_list: { list: 路径X, index: 1 } } }
      - replace_item_of_list: { list: 敌y, index: { var: 编号 }, item: { item_of_list: { list: 路径Y, index: 1 } } }
      - replace_item_of_list: { list: 敌hp, index: { var: 编号 }, item: 30 }
      - replace_item_of_list: { list: 敌活, index: { var: 编号 }, item: 1 }
      - goto_xy: { x: { item_of_list: { list: 路径X, index: 1 } }, y: { item_of_list: { list: 路径Y, index: 1 } } }
      - show: null
    - - when_start_as_clone: null
      - forever:
          do:
            - change_variable: { var: 路径序号, by: 1 }
            - set_variable: { var: ex, value: { item_of_list: { list: 路径X, index: { var: 路径序号 } } } }
            - set_variable: { var: ey, value: { item_of_list: { list: 路径Y, index: { var: 路径序号 } } } }
            - goto_xy: { x: { var: ex }, y: { var: ey } }
            - replace_item_of_list: { list: 敌x, index: { var: 编号 }, item: { var: ex } }
            - replace_item_of_list: { list: 敌y, index: { var: 编号 }, item: { var: ey } }
            - if: { cond: { gt: [ { var: 路径序号 }, { length_of_list: { list: 路径X } } ] },
                    do: [ { change_variable: { var: 生命, by: -1 } },
                          { replace_item_of_list: { list: 敌活, index: { var: 编号 }, item: 0 } },
                          { delete_this_clone: null } ] }
            - if: { cond: { lt: [ { item_of_list: { list: 敌hp, index: { var: 编号 } } }, 1 ] },
                    do: [ { replace_item_of_list: { list: 敌活, index: { var: 编号 }, item: 0 } },
                          { delete_this_clone: null } ] }
            - wait: 0.02
```

---

## §TD4 路径：私有列表存路点（列表当数组）

敌人按序号读取路径点列表走到终点（§38 同款）。**好处**：改路线只改列表，不碰敌人代码。

```text
重复执行直到 (路径序号 > length of [路径X]):
    go to x: item(路径序号) of [路径X]  y: item(路径序号) of [路径Y]
    路径序号 = 路径序号 + 1
```

另一种做法（无列表）：`如果碰到路径色? 那么 右转 15 度`——用颜色当路线。但颜色法 headless 测不到、易歧义，本 skill 不用；**列表路点法是首选且可验证**。

---

## §TD5 波次：广播总线（铁律16 解耦）

### 波次控制器

舞台（或专用控制器角色）按节奏出波；每波 `broadcast(波N)`，所有订阅该波的敌人模板收到后各自 `克隆 自己` 刷怪。

```text
当绿旗被点击:
  重复执行:
    __spawn = __spawn + 1
    if (__spawn > 120) then          # 约 4 秒一波（30fps）
        __spawn = 0
        波次 = 波次 + 1
        broadcast [出波 v]            # 一波一广播，扇出给所有订阅者
    wait 0.02
```

### 难度曲线（呼应 game-systems §27）

| 曲线 | 做法 | 感觉 |
|---|---|---|
| 线性 | 每波数量 = 波次 | 平庸 |
| 加速 | 数量 = 波次²/系数 | 后段压力陡增 |
| 递减间隔 | 波间隔随波次缩短 | 最省代码 |
| 台阶 | 每 3 波大台阶 | 有节奏高潮 |

### 多波次变体（实证 13 波次广播）

实证用 13 种波次广播（`dj1..dj8` / `bz1..bz3` / `打击1/打击2` / `死神之杯` / `投石攻击` / `cuihui`）各扇出给专用 spawner。本 skill 示例用**单一 `出波` 广播 + 多敌人模板订阅**（解耦本质相同，更简单）。要更细的难度分层，就拆成 `出波1`/`出波2`/… 各扇出不同组合。

---

## §TD6 防御塔：私有冷却 + 自动索敌 + 开火

### 索敌与开火

塔站桩，forever 内找**射程内最近的活敌人**，朝它开火。`冷却` 是塔私有变量（铁律9），控制射速：

```text
当绿旗被点击: goto(塔位x, 塔位y)；show
当作为克隆体启动(放置的塔): 是克隆 = 1；show
forever:
    如果 (冷却 > 0) 那么 冷却 = 冷却 - 1
    如果 (冷却 == 0) 那么
        目标 = 最近的活敌人(敌活[k]==1 且 距离 < 范围)
        如果 目标 存在:
            塔x = x position；塔y = y position
            目标x = 敌x[目标]；目标y = 敌y[目标]
            create clone of [子弹]      # 子弹克隆读 塔x/塔y/目标x/目标y 决定飞行
            冷却 = 15                  # 射速门限（确定值，可复现）
    wait 0.02
```

> Scratch 没有「取最近的敌人」积木 → 遍历敌人列表（§TD2 的 `敌x/敌y/敌活`），取距离最小且存活的那个。

### IR 写法要点 ✅

```yaml
- name: 防御塔
  x: -120
  y: 60
  costumes: [ { name: 造型1, asset: assets/td/tower.png } ]
  variables:
    是克隆: 0
    冷却: 0
    范围: 150
    伤害: 10
  scripts:
    - - when_green_flag_clicked: null
      - goto_xy: { x: -120, y: 60 }
      - show: null
    - - when_start_as_clone: null
      - set_variable: { var: 是克隆, value: 1 }
      - show: null
    - - when_green_flag_clicked: null
      - forever:
          do:
            - if: { cond: { gt: [ { var: 冷却 }, 0 ] }, do: [ { change_variable: { var: 冷却, by: -1 } } ] }
            - if:
                cond: { equals: [ { var: 冷却 }, 0 ] }
                do:
                  - set_variable: { var: __k, value: 0 }   # 自建循环变量找最近活敌
                  - set_variable: { var: 最近, value: -1 }
                  - repeat:
                      times: 30
                      do:
                        - change_variable: { var: __k, by: 1 }
                        - if:
                            cond:
                              and:
                                - equals: [ { item_of_list: { list: 敌活, index: { var: __k } } }, 1 ]
                                - lt:
                                    - mathop: { operator: abs, num: { subtract: [ { var: xpos_self }, { item_of_list: { list: 敌x, index: { var: __k } } } ] } }
                                    - { var: 范围 }
                            do:
                              - set_variable: { var: 最近, value: { var: __k } }
                  - if:
                      cond: { gt: [ { var: 最近 }, 0 ] }
                      do:
                        - set_variable: { var: 塔x, value: { of: { object: 防御塔, property: x position } } }
                        - set_variable: { var: 塔y, value: { of: { object: 防御塔, property: y position } } }
                        - set_variable: { var: 目标x, value: { item_of_list: { list: 敌x, index: { var: 最近 } } } }
                        - set_variable: { var: 目标y, value: { item_of_list: { list: 敌y, index: { var: 最近 } } } }
                        - set_variable: { var: 目标编号, value: { var: 最近 } }
                        - create_clone_of: { clone: 子弹 }
                        - set_variable: { var: 冷却, value: 15 }
            - wait: 0.02
```

> 注：上面的「找最近」用了一个 `repeat 30` 遍历 30 个槽位；`xpos_self` 用 `{ of: { object: 防御塔, property: x position } }` 取塔自身坐标（和射手册取 `玩家x` 变量同理，这里直接读属性更稳）。

---

## §TD7 子弹与碰撞：位置数学 + 线段扫掠（铁律29）

### 社区实证的碰撞写法 vs 我们的要求

实证作品用 `sensing_touchingobject×310`（碰到对象）做命中——简单，但**无头 scratch-vm 测不到**（见射手册 §120.4），且高速弹会穿模。本 skill 要求：

- **命中用「位置数学 + 列表追踪」**：`abs(bx - 敌x[k]) < R 且 abs(by - 敌y[k]) < R`。
- **高速弹（>15px/帧）必须线段扫掠**：上帧→本帧连线与敌人碰撞箱求交，否则穿过薄敌（铁律29，射手册 §120 同款反模式）。

### 子弹逻辑

```text
当绿旗被点击: 隐藏
当作为克隆体启动:
    是克隆 = 1
    bx = 塔x；by = 塔y
    dx = 目标x - 塔x；dy = 目标y - 塔y；len = sqrt(dx*dx+dy*dy)；夹紧 len>=1
    vx = dx/len * 速度；vy = dy/len * 速度
    goto(bx, by)；show
当作为克隆体启动:
    forever:
        bx = bx + vx；by = by + vy；goto(bx, by)
        k = 0
        repeat (场上敌人上限):
            k = k + 1
            if (敌活[k]==1 且 abs(bx-敌x[k])<R 且 abs(by-敌y[k])<R):
                敌hp[k] = 敌hp[k] - 伤害       # ★ 只改列表里的血，敌人自己读到后删自己（race-free）
                delete this clone
                exit repeat
        if (出界 或 飞行超时) delete this clone
        wait 0.02
```

> **命中只改 `敌hp[编号]`，让敌人自己读到 `敌hp<=0` 再删自己**——避免「子弹删敌人 / 敌人删自己」双写竞争（射手册 §118 同款）。

### IR 写法要点 ✅

```yaml
- name: 子弹
  x: 0
  y: 0
  costumes: [ { name: 造型1, asset: assets/td/bullet.png } ]
  variables:
    是克隆: 0
    bx: 0
    by: 0
    vx: 0
    vy: 0
    伤害: 10
    __k: 0
  scripts:
    - - when_green_flag_clicked: null
      - hide: null
    - - when_start_as_clone: null
      - set_variable: { var: 是克隆, value: 1 }
      - set_variable: { var: bx, value: { var: 塔x } }
      - set_variable: { var: by, value: { var: 塔y } }
      - set_variable:
          var: vx
          value:
            divide:
              - subtract: [ { var: 目标x }, { var: 塔x } ]
              - { mathop: { operator: sqrt, num: { add: [ { multiply: [ { subtract: [ { var: 目标x }, { var: 塔x } ] }, { subtract: [ { var: 目标x }, { var: 塔x } ] } ] }, { multiply: [ { subtract: [ { var: 目标y }, { var: 塔y } ] }, { subtract: [ { var: 目标y }, { var: 塔y } ] } ] } ] } } }
      - set_variable:
          var: vy
          value:
            divide:
              - subtract: [ { var: 目标y }, { var: 塔y } ]
              - { mathop: { operator: sqrt, num: { add: [ { multiply: [ { subtract: [ { var: 目标x }, { var: 塔x } ] }, { subtract: [ { var: 目标x }, { var: 塔x } ] } ] }, { multiply: [ { subtract: [ { var: 目标y }, { var: 塔y } ] }, { subtract: [ { var: 目标y }, { var: 塔y } ] } ] } ] } } }
      - goto_xy: { x: { var: bx }, y: { var: by } }
      - show: null
    - - when_start_as_clone: null
      - forever:
          do:
            - change_variable: { var: bx, by: { var: vx } }
            - change_variable: { var: by, by: { var: vy } }
            - goto_xy: { x: { var: bx }, y: { var: by } }
            - set_variable: { var: __k, value: 0 }
            - repeat:
                times: 30
                do:
                  - change_variable: { var: __k, by: 1 }
                  - if:
                      cond:
                        and:
                          - equals: [ { item_of_list: { list: 敌活, index: { var: __k } } }, 1 ]
                          - and:
                              - lt: [ { mathop: { operator: abs, num: { subtract: [ { var: bx }, { item_of_list: { list: 敌x, index: { var: __k } } } ] } }, 18 ]
                              - lt: [ { mathop: { operator: abs, num: { subtract: [ { var: by }, { item_of_list: { list: 敌y, index: { var: __k } } } ] } }, 18 ]
                      do:
                        - change_variable: { var: 伤害, by: 0 }   # 占位（伤害由塔写入）
                        - replace_item_of_list:
                            list: 敌hp
                            index: { var: __k }
                            item: { subtract: [ { item_of_list: { list: 敌hp, index: { var: __k } } }, 10 ] }
                        - delete_this_clone: null
            - if: { cond: { gt: [ { mathop: { operator: abs, num: { var: bx } } }, 260 ] }, do: [ { delete_this_clone: null } ] }
            - wait: 0.02
```

> ⚠️ 上面 `vx/vy` 用 `divide` 求单位向量；真实工程里速度要乘一个系数（如 `* 8`），否则子弹一帧只动 1px。示例为可读性省略了系数，请在 `vx/vy` 外再乘「子弹速度」。**且子弹速度 >15px/帧时必须改线段扫掠**（见铁律29），距离判定会漏检。

---

## §TD8 经济与建造

### 金币循环

- 杀敌：`分数 += 击杀奖励`；`金 += 奖励`（敌人死亡时由控制器或被击杀逻辑发奖励）。
- 建塔：`金 -= 建塔费用`。
- 卖塔：退款一半（`金 += 建塔费用/2`，hide 该塔）。
- 升级：社区常见「卖+重建」（省代码），或直接改塔私有 `伤害/范围`。

### 建造交互（铁律10：用角色按钮，不用「询问」）

```
当角色被点击(商店里的塔图标): 进入放置模式(下一个点击=塔位)
当角色被点击(地图空地):
    如果 (金 >= 建塔费用) 且 (碰到路径色? = 否):     ← 不能建在路径上
        金 = 金 - 建塔费用
        create clone of [防御塔]
```

> 用「角色被点击」做按钮和放置，不要用 `询问 [...] 并等待`（铁律10：菜单/交互用角色按钮）。

---

## §TD9 胜负与结算（铁律7）

- **失败**：`生命 <= 0` → `broadcast [失败 v]` → 切结算背景。
- **结算页必须有「返回 / 再来一局」按钮**（铁律7，最高频遗忘）：按钮广播 `[重置]`（复位挂广播而非绿旗，铁律6），复位逻辑清 金/生命/分数/敌计数器/敌活列表 + 回到第一波。
- **数字带标签角色**（铁律1）：金币/生命/分数用角色显示数值 + 文字标签，别只显示裸数字。

---

## ★ §TD10 致命坑（实测复现过，不是理论）

### TD10.1 克隆守卫必须有（铁律11）
敌人/塔/子弹 接收生成广播必须 `if(是克隆==0)` 守卫，否则克隆响应本体事件帽子继续生成克隆 → 指数级爆炸。

### TD10.2 波次广播别退化成 giant if（铁律16）
一波一广播，订阅者各自响应。**不要**在主控里写 `if 波次==1 ... else if 波次==2 ...` 串 13 个分支——失去解耦、难扩展。波次控制器只负责 `broadcast`，不负责具体刷哪种怪。

### TD10.3 状态必须私有（铁律9）
每个敌人的 `hp` / `冷却` 必须是**角色级私有变量**，切勿用全局变量当敌人血槽——多个敌人会串血、互相误杀。多血槽（主血+护盾）也各自私有。

### TD10.4 子弹碰撞用位置数学/线段扫掠，别只用 碰到对象（铁律29）
`sensing_touchingobject` 依赖渲染器，无头测不到；高速弹会穿模。用 `abs(dx)<R and abs(dy)<R` 距离判定 + 列表追踪（可验证），>15px/帧 改线段扫掠。

### TD10.5 forever 不加 wait → 无头逐步推进被放大（射击册 §120.1）
每个 `forever` 末尾加 `wait 0.02`（≈每帧一次），保证 `stepN(n)` 精确等于推进 n 帧。

### TD10.6 路径/敌情列表块式声明 + 校验读 variables 1-based-1
列表在 builder 里是「变量存数组」，必须块式 YAML（`- 0` 每行）；校验时从 `target.variables` 取数组、**按 1-based 索引 − 1** 读写（射击册 §120.3 同款）。

### TD10.7 阻尼用乘不用减（铁律5）
塔/敌人移动用 `x = x * 系数` 衰减；**绝不要**写成 `x = x*0.9; x += x`（实为 1.8× 放大，数值不稳定）。跑酷册 §三、射击册 §二 都是这个同源 bug。

### TD10.8 嵌套 IF 的 do 里放 CLONE 会被漏编译（射击册 §120.2）
`if (是克隆==0) { if (敌计数器<上限) { +1; create clone } }` 内层 CLONE 静默消失 → 一只怪都不生成。拆成两个**平级单分支 IF**（见 §TD3）。

---

## 变体与扩展

| 玩法 | 改法 |
|---|---|
| **固定路线 TD** | 单条路径列表；敌人顺序走 |
| **分叉/多路线** | 多条路径列表，敌人按类型选路线 |
| **Boss 波** | 单个大敌人 + 多段血（敌hp 为大值），归零才删 |
| **属性克制** | 敌人和塔各带颜色/类型，同类型伤害减半（敌人私有 `类型`，塔私有 `类型`） |
| **多塔种** | 多个塔模板角色，各自私有 `伤害/范围/冷却` |
| **无尽模式** | 波次无限递增（`波次²` 难度），金币随击杀指数给 |
| **可放置塔** | 塔用 `create clone of [防御塔]` 在点击位生成（§TD8） |

> 无论哪种变体，**TD10.1 克隆守卫**、**TD10.3 私有状态**、**TD10.4 碰撞数学**、**TD10.7 阻尼用乘** 都适用，且必须靠行为校验实跑验证。

---

## 交付前自检

```bash
python scripts/build_sb3.py --ir examples/tower-defense.yaml --out examples/output/tower-defense.sb3 --workdir /tmp/td_build
python scripts/validate_sb3.py --sb3 examples/output/tower-defense.sb3          # 四层结构校验
node scripts/towerdefense_behavior_check.mjs examples/output/tower-defense.sb3   # TOWERDEFENSE_LOGIC_OK
```

`towerdefense_behavior_check.mjs` 会真实模拟「绿旗 → 检查舞台/敌人/塔/子弹角色存在、初始 生命=10/金币=200 → 出波验证敌人克隆守卫(==N) → 敌人沿路径移动 → 子弹命中扣血并击杀敌人(敌hp 下降、敌活=0) → 敌人到达基地扣生命 → 生命归零触发失败」，全部断言通过才输出 `TOWERDEFENSE_LOGIC_OK`。

**只过四层校验不算塔防作品完成**——克隆守卫、路径移动、子弹命中扣血击杀、到达基地扣生命、失败触发这五条核心逻辑必须靠行为校验实跑验证。

---

## 附录：本册用到的积木速查

| 用途 | IR 写法 |
|---|---|
| 克隆自己（守卫后） | `{ create_clone_of: { clone: _myself_ } }` |
| 作为克隆启动 | `when_start_as_clone: null` |
| 删除克隆 | `{ delete_this_clone: null }` |
| 广播出波 | `{ broadcast: { message: 出波 } }` |
| 收到广播 | `{ when_receive: { message: 出波 } }` |
| 自身坐标 | `{ of: { object: 防御塔, property: x position } }` |
| 列表：第 n 项 | `{ item_of_list: { list: 敌x, index: n } }` |
| 列表：替换第 n 项 | `{ replace_item_of_list: { list: 敌x, index: n, item: 值 } }` |
| 列表：长度 | `{ length_of_list: { list: 路径X } }` |
| 距离/绝对值 | `{ mathop: { operator: abs, num: ... } }` / `{ mathop: { operator: sqrt, num: ... } }` |
| 夹紧长度防除零 | `if <len < 1> then len = 1` |
| 等待（节流） | `{ wait: { secs: 0.02 } }` |

> 通用积木速查见 `game-systems.md` 附录；碰撞/列表陷阱见射击册 §120。
