# 物理引擎进阶（第四册：§51–§58）

> 来源：Scratch Wiki《How to Make a Physics Engine》《Rope Physics》、
> Scratch 官方社区（Verlet Integration demo、Real World Rope Physics、
> Particles 2.0 fluids using grid、Spatial Grid Collision、Bouncing & Turning）、
> science-on-stage《Physics Engine》教学材料、ItsMyBot 物理游戏教程、
> hqwc.cn（矩形碰撞检测、对象管理器、AABB 引擎）、
> 真视野（Scratch 引擎化：对象池/事件总线/空间分块）、
> Scratch Discuss 克隆体性能帖（griffpatch 的物理与克隆体复用建议）等公开资料。
>
> 本册讲「怎么在 Scratch 里手搓一个物理引擎」。Scratch 没有内置物理引擎，
> 所有东西都要自己算 —— 但社区已经验证出一套可用的配方。
> 每节都给出本 skill 的 IR 写法（能直接生成 sb3 的标 ✅）。

## 速查表

| 想做什么 | 章节 |
|---|---|
| 碰撞判定不准 / 性能差，要自己算碰撞盒 | §51 AABB 包围盒碰撞 |
| 想要稳定的物理（不抖、不爆炸） | §52 Verlet 积分 |
| 做绳子、弹簧、布料、软体 | §53 绳索与布料（Verlet + 约束松弛） |
| 做太阳系、轨道、引力 | §54 万有引力与轨道 |
| 两个球要真实地交换动量 | §55 弹性碰撞与动量守恒 |
| 角色要能爬斜坡、在坡上不打滑 | §56 斜坡检测与坡面摩擦 |
| 弹幕/射击游戏掉帧 | §57 对象池（克隆体复用） |
| 实体一多碰撞检测就爆 | §58 空间分桶（broad phase） |

---

## 51. AABB 包围盒碰撞（自己算，不用「碰到」）

### 51.1 为什么不用 Scratch 自带的「碰到」

Scratch 的「碰到 [角色]?」和「碰到颜色?」在底层做的是**像素级比对**：
两个角色的造型要逐像素比较透明区域。后果有三个：

| 问题 | 后果 |
|---|---|
| **性能差** | 每次判定都比对两张图，几十个角色两两判定直接拖垮帧率 |
| **精度不稳** | 造型里有透明留白时，**视觉上没碰到但判定为碰到**（玩家体验极差） |
| **克隆体判定不稳** | 障碍物是克隆体时，「碰到」可能时灵时不灵 |

社区（hqwc.cn 的引擎化实践、TrueSight 的架构分析）的一致结论是：
**引擎级项目一律换成自己算包围盒（AABB）**。

### 51.2 AABB 判定公式

轴对齐矩形（AABB）就是「贴着角色边缘的矩形」。两个矩形相交的条件是**四条同时成立**：

```
A右边界 > B左边界
A左边界 < B右边界
A上边界 > B下边界
A下边界 < B上边界
```

```
左边界 = x - 半宽
右边界 = x + 半宽
上边界 = y + 半高
下边界 = y - 半高
```

### 51.3 IR 配方

```yaml
# 在角色的碰撞检测角色里（或用全局变量）
- set_variable: { var: 我左, value: { subtract: [ { x_position }, {var: 我半宽} ] } }
- set_variable: { var: 我右, value: { add: [ { x_position }, {var: 我半宽} ] } }
- set_variable: { var: 我上, value: { add: [ { y_position }, {var: 我半高} ] } }
- set_variable: { var: 我下, value: { subtract: [ { y_position }, {var: 我半高} ] } }

# 对方的边界（假设对方把数据写进全局列表）
- set_variable: { var: 他左, value: { item_of_list: { index: {var: 对方索引}, list: 敌左 } } }
- set_variable: { var: 他右, value: { item_of_list: { index: {var: 对方索引}, list: 敌右 } } }
- set_variable: { var: 他上, value: { item_of_list: { index: {var: 对方索引}, list: 敌上 } } }
- set_variable: { var: 他下, value: { item_of_list: { index: {var: 对方索引}, list: 敌下 } } }

- if:
    cond:
      and:
        - and:
            - greater_than: { a: {var: 我右}, b: {var: 他左} }
            - less_than:    { a: {var: 我左}, b: {var: 他右} }
        - and:
            - greater_than: { a: {var: 我上}, b: {var: 他下} }
            - less_than:    { a: {var: 我下}, b: {var: 他上} }
    do:
      - set_variable: { var: 撞到了, value: 1 }
```

⚠️ **Scratch 的「与」只有 2 个输入**，4 个条件必须**嵌套成 2+2**，
写成 `and: [a, b, c, d]` 会**静默丢掉 c、d**。

### 51.4 圆形碰撞（子弹打敌人）

两个圆相交的条件是**距离 < 半径之和**。
⚠️ **不要真的开平方** —— 比较**距离平方**和**半径和平方**即可：

```yaml
- set_variable:
    var: 距离平方
    value:
      add:
        - multiply:
            - subtract: [ { x_position }, { of: { object: 敌人, property: "x position" } } ]
            - subtract: [ { x_position }, { of: { object: 敌人, property: "x position" } } ]
        - multiply:
            - subtract: [ { y_position }, { of: { object: 敌人, property: "y position" } } ]
            - subtract: [ { y_position }, { of: { object: 敌人, property: "y position" } } ]
- if:
    cond:
      less_than:
        a: { var: 距离平方 }
        b: { multiply: [ { add: [ {var: 我半径}, {var: 他半径} ] }, { add: [ {var: 我半径}, {var: 他半径} ] } ] }
    do:
      - set_variable: { var: 撞到了, value: 1 }
```

### 51.5 碰撞盒要比造型小一圈（关键手感技巧）

社区反复强调的一点：**碰撞盒不必和造型等大，可以比造型小一圈**。

| 做法 | 效果 |
|---|---|
| 碰撞盒 = 造型大小 | 「明明是擦边却死了」，挫败感极强 |
| **碰撞盒比造型小一圈** | 手感立刻变好（社区通用做法） |

实现：给每个对象额外记 `碰撞宽` / `碰撞高` 两个参数（可以是美术尺寸的 0.8 倍）。

⚠️ **还要支持偏移**（hqwc.cn 的做法）：角色低头时碰撞区应该往下移，
树的树干和树冠碰撞范围也不同 → 再记一组 `偏移X` / `偏移Y`。

```yaml
- set_variable: { var: 我左, value: { add: [ { subtract: [ { x_position }, {var: 我半宽} ] }, {var: 偏移X} ] } }
```

---

## 52. Verlet 积分（稳定的物理）

### 52.1 什么是 Verlet 积分

普通欧拉积分是「位置 += 速度 × dt，速度 += 加速度 × dt」。
**Verlet 积分**换了个思路：**不存速度，只存当前位置和上一帧位置**，
速度由两者相减隐式得到。

```
新位置 = 2×当前位置 − 上一帧位置 + 加速度×dt²
上一帧位置 = 当前位置
```

（CMU《Sticky Fingers》论文的原始表述）

### 52.2 为什么 Verlet 更适合 Scratch

社区（Real World Rope Physics 作者）的原话：
**Verlet 积分比欧拉方法稳定得多**（"much more stable than some other methods"）。

具体好处：

| 特性 | 说明 |
|---|---|
| **不用存速度变量** | 只存 `当前x/当前y` 和 `上一帧x/上一帧y`，省一半变量 |
| **约束修正自动带动速度** | 把粒子拉回正确距离时，位置变化自然被下一帧的「相减」读成新速度 |
| **天然处理碰撞** | 碰撞也可以表达成「约束」，两个物体互相推开，Verlet 自动传递动量 |

### 52.3 IR 配方（单粒子）

```yaml
# 变量：px, py（当前）, ox, oy（上一帧）, ax, ay（本帧加速度）
- forever:
    do:
      # 1) 积分：算新位置
      - set_variable:
          var: nx
          value:
            add:
              - multiply: [ 2, { x_position } ]
              - multiply: [ -1, {var: ox} ]
              - multiply: [ {var: ax}, { multiply: [ {var: dt}, {var: dt} ] } ]
      - set_variable:
          var: ny
          value:
            add:
              - multiply: [ 2, { y_position } ]
              - multiply: [ -1, {var: oy} ]
              - multiply: [ {var: ay}, { multiply: [ {var: dt}, {var: dt} ] } ]
      # 2) 保存上一帧位置
      - set_variable: { var: ox, value: { x_position } }
      - set_variable: { var: oy, value: { y_position } }
      # 3) 移到新位置
      - goto_xy: { x: {var: nx}, y: {var: ny} }
```

### 52.4 三步法：Simulate → Relax → Render

Real World Rope Physics 作者把物理引擎拆成三步，这是**最值得抄的架构**：

| 步骤 | 做什么 | 频率 |
|---|---|---|
| **Simulate（模拟）** | 施加重力等外力，用 Verlet 算新位置 | 每帧 1 次 |
| **Relax（松弛）** | 把粒子拉回满足约束的距离（拉直绳子） | 每帧**多次**（15~200 次） |
| **Render（渲染）** | 沿粒子画线 | 每帧 1 次 |

⚠️ **Relax 的次数（ACCURACY）决定质量与性能的平衡**：
- Scratch 上限约 **15 次/帧**（再多就卡）；
- TurboWarp 上可以开到 **1000**（200 次就够准）；
- 次数太少 → 绳子「拉长」（因为每个粒子都在覆盖前一个的修正）；
- 作者原话：「理论上要松弛无穷多次才能完全满足约束」。

---

## 53. 绳索与布料（Verlet + 约束松弛）

### 53.1 两种绳索做法

| 做法 | 原理 | 特点 |
|---|---|---|
| **弹簧法** | 每个关节算「力」（胡克定律），累加到速度 | 物理准确，能摆动 |
| **位置约束法**（Verlet + Relax） | 直接把两个粒子**移到正确距离**，反复松弛 | 实现简单、稳定，是社区主流 |

### 53.2 弹簧法的公式（Scratch Wiki《Rope Physics》）

```
力X = (x2 − x1) × 刚度 ÷ 质量
力Y = (y2 − y1) × 刚度 ÷ 质量
新速度X = (旧速度X + 力X) × 阻尼
新速度Y = (旧速度Y + 力Y) × 阻尼
```

其中 `x1,y1` 是上端，`x2,y2` 是下端。
**刚度**让绳子更短更硬，**阻尼**让力传播得更慢。

### 53.3 位置约束法的公式（CMU《Sticky Fingers》）

两个粒子 `x1, x2`，静止距离 `r`，则每个粒子的修正量：

```
Δx1 = ½ × (|x2 − x1| − r) × (x2 − x1)/|x2 − x1|
Δx2 = −Δx1
```

（质量相等时各分一半；若只有一个粒子被固定，就全给另一个。）

⚠️ **约束不能超过静止长度的 10%**（CS 184 的 Provot 论文做法）：
超过就把位置修正回 `1.1 × 静止长度`。

### 53.4 绳索关节的数据结构

Scratch Wiki 给的三种关节类型（存进列表）：

| 类型 | 含义 |
|---|---|
| `1` | 上下都有绳索关节 |
| `0` | 固定在某个物体上（如玩家） |
| `-1` | 只连接一个其他关节（绳子的末端） |

一条 4 段绳子的类型序列是 `1, 1, 1, 0`。

**列表用「每个关节 3 项」** 布局：`x坐标, y坐标, 类型` 依次排列。

### 53.5 IR 配方（单关节的约束松弛）

```yaml
# 变量：上一关节x, 上一关节y, 本关节x, 本关节y, 静止长度
# 列表：关节X, 关节Y, 关节类型
- - when_start_as_clone: { clone: _myself_ }
  - forever:
      do:
        # 取出本关节和上一关节
        - set_variable: { var: 本x, value: { item_of_list: { index: {var: 我的ID}, list: 关节X } } }
        - set_variable: { var: 本y, value: { item_of_list: { index: {var: 我的ID}, list: 关节Y } } }
        - set_variable: { var: 上x, value: { item_of_list: { index: { subtract: [ {var: 我的ID}, 1 ] }, list: 关节X } } }
        - set_variable: { var: 上y, value: { item_of_list: { index: { subtract: [ {var: 我的ID}, 1 ] }, list: 关节Y } } }
        # 距离平方（不开根号，省性能）
        - set_variable:
            var: 距平方
            value:
              add:
                - multiply: [ { subtract: [ {var: 本x}, {var: 上x} ] }, { subtract: [ {var: 本x}, {var: 上x} ] } ]
                - multiply: [ { subtract: [ {var: 本y}, {var: 上y} ] }, { subtract: [ {var: 本y}, {var: 上y} ] } ]
        # 约束松弛：把本关节往上一关节拉（只拉一半）
        - if:
            cond: { greater_than: { a: {var: 距平方}, b: { multiply: [ {var: 静止长度}, {var: 静止长度} ] } } }
            do:
              - set_variable:
                  var: 距
                  value: { mathop: { operator: sqrt, num: {var: 距平方} } }
              - set_variable:
                  var: 修正比例
                  value: { divide: [ { subtract: [ {var: 距}, {var: 静止长度} ] }, {var: 距} ] }
              - set_variable:
                  var: 新x
                  value: { add: [ {var: 本x}, { multiply: [ {var: 修正比例}, { multiply: [ 0.5, { subtract: [ {var: 本x}, {var: 上x} ] } ] } ] } ] }
              - set_variable:
                  var: 新y
                  value: { add: [ {var: 本y}, { multiply: [ {var: 修正比例}, { multiply: [ 0.5, { subtract: [ {var: 本y}, {var: 上y} ] } ] } ] } ] }
              - replace_item_of_list: { item: {var: 新x}, index: {var: 我的ID}, list: 关节X }
              - replace_item_of_list: { item: {var: 新y}, index: {var: 我的ID}, list: 关节Y }
```

### 53.6 布料 = 网格 + 三类约束

CMU 论文的布料模型：规则的粒子网格，相邻粒子之间连三类约束。

| 约束 | 连接 | 作用 |
|---|---|---|
| **Stretch（拉伸）** | 正交相邻 | 防止布被拉太开 |
| **Shear（剪切）** | 对角相邻 | 防止布被剪歪 |
| **Bend（弯曲）** | 隔一个的正交 | 控制布的柔软度（刚度最小） |

⚠️ **不要用「弹簧-阻尼力」做布料**（CMU 论文明确指出）：
那种做法会产生「super-elastic cloth」（过度弹性的布），看起来很不真实。
要用**位置约束**（直接修正位置）才能得到又硬又不拉伸的布。

### 53.7 ⚠️ 渲染绳索要用画笔，且角色要「不旋转」

Scratch Discuss 的性能建议：
用画笔画线时，如果一边改 `direction` 一边 `move`，
Scratch **每次都要旋转并重绘造型**，非常慢。

**解决办法**：
- 把画笔角色的 `rotationStyle` 设成 **`don't rotate`**；
- 或者用**空白矢量造型**（空白造型旋转起来极快）。

⚠️ **画笔扩展的图章（stamp）会留在舞台上**，切场景时要 `pen_clear`。

---

## 54. 万有引力与轨道

### 54.1 引力公式

```
F = G × m1 × m2 / r²
a = F / m            （加速度）
```

简化后（把常量吸进 `G`）：

```
ax = G × 中心x / r³
ay = G × 中心y / r³
```

（r³ = r² × r，方向直接用「指向中心的向量」乘以系数，
省掉一次开方和方向计算 —— 这是国内教学材料（码丁实验室）的做法。）

### 54.2 轨道运动的两条路

| 做法 | 原理 | 优点 | 缺点 |
|---|---|---|---|
| **参数化圆轨道** | `x = 中心x + R×cos(θ)`，`y = 中心y + R×sin(θ)`，θ 每帧递增 | 稳定、完美椭圆/圆、不会飞走 | 不是真的物理，是「画」出来的 |
| **真引力模拟** | 每帧算引力加速度并积分 | 真实、可以发射彗星、可以双星系统 | 参数不当会飞走/坠落 |

**教程类作品（太阳系）几乎都用参数化**（Harvard ScratchEd 的教材就是这么教的）：

```yaml
- forever:
    do:
      - change_variable: { var: 角度, by: 1 }
      - goto_xy:
          x: { add: [ {var: 中心x}, { multiply: [ {var: 半径}, { mathop: { operator: cos, num: {var: 角度} } } ] } ] }
          y: { add: [ {var: 中心y}, { multiply: [ {var: 半径}, { mathop: { operator: sin, num: {var: 角度} } } ] } ] }
```

### 54.3 参考系嵌套（月球绕地球，地球绕太阳）

GitHub 的 scratch-solar 教程给了公式：

```
月球x = 地球的x + 月球半径 × cos(月球角度)
月球y = 地球的y + 月球半径 × sin(月球角度)
```

⚠️ **角度要按「度」算**（Scratch 的 sin/cos 用度不用弧度），
且**每个天体的自转角与公转角要分开**（自转 = 造型旋转，公转 = 位置）。

### 54.4 「时间尺度压缩」是科学建模的关键

教学材料（太阳系课件）反复强调的一点：
**现实里地球公转一圈 365 天，程序里可能设成 60 秒一圈**。
学生要理解「程序中的 1 秒 ≠ 现实 1 秒」，
并通过调整「角度增量」或「等待时间」来调节公转速度，
建立「参数调控 → 行为响应」的因果认知。

⚠️ **调参时常见错误：把角度单位误用成弧度**（教学材料明确点名这个坑），
以及「行星飞出屏幕 → 要检查坐标范围」。

### 54.5 开普勒第三定律（教学点）

`火星公转周期是地球的 1.88 倍` → 半径按 `1.524` 倍 →
周期按 `1.524^1.5 ≈ 1.88` 倍。
把这个换算写进作品注释，学生就能理解「变量 = 现实量的数字化映射」。

---

## 55. 弹性碰撞与动量守恒

### 55.1 一维（正面碰撞）的简单解

science-on-stage 的物理引擎教学材料给了最简版本：
**等质量的两球正面碰撞 = 交换速度**。

```
球1：v1' = v2
球2：v2' = v1
```

不等质量时（Science on Stage 的公式）：

```
v1' = ((m1−m2)/m1+m2) × v1 + (2×m2/(m1+m2)) × v2
v2' = (2×m1/(m1+m2)) × v1 + ((m2−m1)/m1+m2) × v2
```

### 55.2 二维（斜着撞）的正确做法

Scratch Discuss 的高赞回答（dem_bot）：
**不能只翻转速度** —— 那样只对「垂直撞墙」成立。

正确做法是**把速度向量旋转到「法线 / 切线」坐标系，交换法线分量，再旋回**：

1. 求碰撞面的**法线向量**（指向表面外侧）；
2. 把两个球的速度向量分解成法线分量与切线分量；
3. **只交换法线分量**（切线分量保持）；
4. 把结果旋回原坐标系。

⚠️ **质量不同时要先乘质量再交换、之后又除回去**（交换的是动量不是速度）。

### 55.3 圆对圆的正确反弹（含「谁撞谁」）

Scratch Discuss 的完整解法（球撞移动中的玩家）：

```
1. 假设玩家静止：先算出法线向量
2. 取球速度在法线方向上的分量（点积）：
   dot = normalize(法线) · 球速度
3. 反射：球速度 = 球速度 − 2×dot×法线
4. 因为玩家也在动：把世界坐标系平移，让玩家静止
   球速度 −= 玩家速度
5. 做反弹
6. 再平移回去
   球速度 += 玩家速度
```

⚠️ **「踢」的方向控制**：纯物理反弹不好控制球往哪飞，
社区做法是**把法线向量偏向玩家移动方向再归一化**。

⚠️ **「球卡在玩家身上」的 bug**：因为「踢球力」是加在法线方向上的，
玩家往后退时额外的力会把球**推向玩家**。
解法：**只在球位于玩家「前方」时才施加踢球力**（再用一次点积判断）。

### 55.4 简单场景的实用折中

如果不做真弹性碰撞（比如弹球游戏），社区的实用折中是：

```yaml
- change_x: { dx: {var: vx} }
- if: { cond: { touching: { object: 障碍 } }, do: [ { set_variable: { var: vx, value: { multiply: [ {var: vx}, -1 ] } } } ] }
```

⚠️ **这只是「翻转速度」，只对垂直撞墙正确**；
而且**只翻转速度、不分离位置** → 球会卡在墙里。
必须配合「退回位置」：

```yaml
- if:
    cond: { touching: { object: 障碍 } }
    do:
      - set_variable: { var: vx, value: { multiply: [ {var: vx}, -1 ] } }
      - change_x: { dx: { multiply: [ {var: vx}, -1 ] } }   # 退回原位
```

---

## 56. 斜坡检测与坡面摩擦

### 56.1 斜坡检测的标准做法

Scratch Wiki《How to Make a Physics Engine》与
shie-li-yi 的《平台游戏》教程给的是同一套算法：
**水平移动后，尝试向上爬，记录爬了多高**。

```yaml
- set_variable: { var: 斜坡, value: 0 }
- repeat: 8                    # 最多能爬 8 像素
  - change_y: { dy: 1 }
  - change_variable: { var: 斜坡, by: 1 }
  - if: { cond: { not: { operand: { touching: { object: 地面 } } } }, do: [ { stop: { stop_option: this script } } ] }
# 如果爬满了 8 像素还在地面 → 坡太陡，退回原位
- if: { cond: { equals: { a: {var: 斜坡}, b: 8 } }, do: [ { change_y: { dy: { multiply: [ {var: 斜坡}, -1 ] } } } ] }
```

⚠️ **`stop this script` 只能停当前脚本，不能只跳出 repeat** ——
所以要把「爬坡」抽成**自定义积木**（Scratch Wiki 的标准做法）。

⚠️ **退回时要退回 X 和 Y 两个轴**：
水平移动了 `vx` 就退回 `-vx`，爬了 `斜坡` 就退回 `-斜坡`。

### 56.2 斜坡上的朝向与摩擦（Wiki 的 Turn 积木）

爬坡时角色应该**转过来贴着坡面**，Wiki 的 `Turn` 积木做法是：
向右试探 10 像素 → 如果离开了地面就转一点并往回退 → 逐步加大转角，
直到找到能站住的角度。

⚠️ **Wiki 的 Turn 积木用的是「逐步加大转角」的试错法**，
逻辑复杂但效果好。简单项目可以只做「贴着坡不穿模」，
不做「精确贴坡」。

### 56.3 坡面摩擦

Wiki 的 `Physics` 积木里，落地时：

```
X速度 = X速度 × 摩擦系数      （摩擦系数 < 1，如 0.95）
方向 = 方向 × 刚度
```

⚠️ **「方向 × 刚度」是斜坡滑动的关键**：
刚度 < 1 → 角色在坡上会缓慢「转向水平」，模拟重力把它拉平。

### 56.4 「地板检测」要用「脚下感应点」

这是 §17 已经强调过的，但在斜坡场景更关键：
**用整个造型做地面检测** → 角色的头发像素也算「碰到地面」→ 角色浮着或爬坡失败。

社区做法：单独做一个小「感应点」角色贴在角色脚下，
只检测这个感应点是否碰到地面。

---

## 57. 对象池（克隆体复用）

### 57.1 为什么不能老建老删克隆体

Scratch Discuss 的权威回答（griffpatch 参与讨论）拆解了瓶颈：

> 克隆体**存在**本身不卡，**创建和销毁**才卡。
> 真正的创建/销毁开销是 DOM 操作。

实测数据（多篇独立来源）：

| 方案 | 场景 | 帧率 |
|---|---|---|
| 原生克隆（每发子弹建一个） | 150 颗子弹同时存在 | **约 20 FPS** |
| 原生克隆 | 300 颗子弹 | 22 FPS |
| **对象池** | 200 颗子弹 | **稳定 30 FPS** |
| 对象池 | 30 个敌人互撞 | 40 → **60 FPS** |

### 57.2 对象池的三种实现

| 实现 | 做法 | 特点 |
|---|---|---|
| **A. 状态列表法**（推荐） | 预建 N 个克隆体，列表 `Bullet_Status` 记状态（0空闲/1飞行），射击时找第一个 0 的索引激活 | 最清晰，性能极佳 |
| **B. 自由链表法** | 空闲索引存进 `pool_free` 列表，取用时从表头取，回收时放回表头 | 取用更快，但状态分散 |
| **C. 惰性回收法** | 克隆体不删除，只 `hide` + 停脚本，用广播「唤醒」 | 最简单，但要靠全局变量协调 |

### 57.3 状态列表法（IR 配方）

```yaml
# 初始化：预建 100 个子弹克隆体，全部隐藏，状态全设为 0
- - when_green_flag_clicked:
  - delete_all_of_list: { list: 子弹状态 }
  - delete_all_of_list: { list: 子弹X }
  - delete_all_of_list: { list: 子弹Y }
  - repeat: 100
    - create_clone_of: { clone: 子弹 }
    - add_to_list: { item: 0, list: 子弹状态 }
    - add_to_list: { item: 0, list: 子弹X }
    - add_to_list: { item: 0, list: 子弹Y }

# 射击：找第一个状态为 0 的索引
- - when_receive:
    message: 开火
  - set_variable: { var: 目标索引, value: 0 }
  - set_variable: { var: 找过了, value: 0 }
  - repeat_until:
      cond: { greater_than: { a: {var: 找过了}, b: { length_of_list: { list: 子弹状态 } } } }
      do:
        - change_variable: { var: 找过了, by: 1 }
        - if:
            cond: { equals: { a: { item_of_list: { index: {var: 找过了}, list: 子弹状态 } }, b: 0 } }
            do:
              - set_variable: { var: 目标索引, value: {var: 找过了} }
              - set_variable: { var: 找过了, value: 999 }    # 找到就跳出
  # 激活它
  - if:
      cond: { less_than: { a: {var: 目标索引}, b: { length_of_list: { list: 子弹状态 } } } }
      do:
        - replace_item_of_list: { item: 1, index: {var: 目标索引}, list: 子弹状态 }
        - broadcast: { message: 激活子弹, 参数: {var: 目标索引} }
```

⚠️ **Scratch 的广播不支持带参数** —— 参数要靠**全局变量**传：
广播前把参数写进一个全局变量，接收方读完再改。
这是社区统一的「参数传递」做法。

### 57.4 克隆体怎么知道自己是被激活的那个

**关键技巧**：每个克隆体在启动时记下自己的「池索引」，
之后所有操作都通过这个索引读写列表数据。

```yaml
# 克隆体启动：记下自己的索引（靠全局的「下一个索引」分配）
- - when_start_as_clone: { clone: _myself_ }
  - set_variable: { var: 我的索引, value: {var: 下一个索引} }
  - change_variable: { var: 下一个索引, by: 1 }
  - hide: null
```

⚠️ **`change_variable` 在克隆体里改的是克隆体的私有副本**，
所以「下一个索引」要放在**舞台全局变量**里才能被所有克隆体共享。

### 57.5 ⚠️ 三个必踩的坑

**① 广播给会生克隆体的角色 → 克隆爆炸**

Scratch Discuss 的明确警告：
如果一个角色的广播接收脚本会 `create clone of [自己]`，
那么**广播时所有克隆体也会收到** → 每个克隆体又生一个 → 指数爆炸。

**解法**：用「是否克隆」私有标志排除克隆体（§7 已讲过）。

**② 「不刷新屏幕」的自定义积木里不能有这些**

Scratch Discuss 的原话：在「运行时不刷新屏幕」的自定义积木里，
**只有这段时间内不允许跑其他脚本**（除非超过半秒才会让出），
所以积木里**绝对不能**用：
- `broadcast and wait`（会永远卡住）
- `ask and wait`
- `wait until`
- `wait N secs`

这些都会造成**严重卡顿**。

**③ 特效在老设备上很卡**

`ghost` 和 `brightness` 之外的任何特效（color/fisheye/whirl/pixelate/mosaic）
会让 Scratch 尝试切到 Stage3D 模式；
**如果设备/浏览器不支持 Stage3D，Scratch 会用 CPU 慢慢算** → 巨卡。

**解法**：给玩家一个「关闭特效」选项，或自动检测。

**④ 画笔画线时角色不要旋转**

见 §53.7。

---

## 58. 空间分桶（broad phase 碰撞优化）

### 58.1 问题：两两判定是 O(n²)

50 个实体两两配对 = 1225 次判定。Scratch 的积木解释器扛不住。
实测（TrueSight 的架构分析）：30 个 AI 敌人互撞，
全遍历版帧率跌到 40 帧，分桶后稳定 60 帧。

### 58.2 解法：把舞台切成格子

把舞台分成若干固定大小的格子（Scratch 舞台 480×360，
常用格子 **120×90**，即 4×4 = 16 个格子）。
每个实体只和**同格 + 相邻 8 格**的实体判定。

### 58.3 ⚠️ 格子边长必须大于最大实体尺寸

Scratch Discuss 的 Spatial Grid Collision 项目下有人直接问：
**「对象可以比格子还大吗？」** —— 如果可以，跨格检测就漏了。

**规则：格子边长 ≥ 最大实体的对角线**，否则要额外处理跨格情况。

### 58.4 数据结构（Particles 2.0 项目的做法）

这个项目（Scratch 上的流体模拟）把分桶做得很完整，值得抄：

| 列表 | 作用 |
|---|---|
| `pcell` | 每个粒子所在格子号（**每步都要排序**） |
| `pid` | 粒子标识（与 pcell **同步排序**） |
| `cstart` | 每个格子的起始位置（在 pcell 中的下标） |
| `cend` | 每个格子的结束位置 |
| `xpos/ypos/state/xvel/yvel/fx/fy` | 粒子数据（**不跟着排序**，靠 pid 索引） |

**关键设计**：
`pcell` 排好序后，`cstart`/`cend` 就能直接给出「某格里有哪几个粒子」，
**不用遍历所有粒子**。

⚠️ **用了插入排序而不是快速排序** —— 因为 `pcell` 每步只小幅变动，
近乎有序的列表上插入排序反而更快。

⚠️ **格子编号要「从下到上、从左到右」**，
这样下落粒子的同格粒子在列表里是连续的。

### 58.5 简化版：只做「同格 + 上下左右 4 格」

如果只做弹幕/简单碰撞，可以更省：

```yaml
- set_variable: { var: 我的格X, value: { floor: { divide: [ { add: [ { x_position }, 240 ] }, {var: 格宽} ] } } }
- set_variable: { var: 我的格Y, value: { floor: { divide: [ { add: [ { y_position }, 180 ] }, {var: 格高} ] } } }
```

然后只检测 `我的格X + dx`、`我的格Y + dy`（dx,dy ∈ {-1,0,1}）这 9 个格子里的实体。

⚠️ **格子编号 → 实体列表的映射**，
最简单的做法是「每格一个列表」（16 条列表），
把实体索引塞进对应格子的列表里。

### 58.6 三种碰撞方案怎么选

| 方案 | 原理 | 优点 | 缺点 |
|---|---|---|---|
| **颜色检测** | 像素点颜色 | 实现极简 | 极易受背景纹理干扰 |
| **距离检测** | `√(Δx²+Δy²) < R` | 精度极高 | 开方开销大；实体数多时 O(n²) |
| **包围盒 AABB** | 坐标区间重叠 | **性能最优** | 对旋转物体精度较低 |

**推荐的分层做法**（TrueSight 的建议）：
**先用 AABB 做粗筛**，只有包围盒重叠时**再做精确的距离检测**。

### 58.7 数据驱动渲染（减少克隆体自身逻辑）

TrueSight 与「游戏引擎化」系列文章的共同建议：
**尽量减少克隆体自身的逻辑** —— 把实体坐标、血量等存进**列表**，
由一个「渲染器」克隆体统一根据列表数据刷新位置。

这样克隆体几乎不做事，帧率大幅提升。

---

## 附录：本册用到的积木速查

| 用途 | IR 写法 |
|---|---|
| 面向某角色 | `{ point_towards: { TOWARDS: 角色名 } }` |
| 移动 | `{ move_steps: { steps: n } }` |
| 改变 x / y | `{ change_x: { dx: 值 } }` / `{ change_y: { dy: 值 } }` |
| 位置 | `{ goto_xy: { x: 值, y: 值 } }` |
| 角度 | `{ turn_right: { degrees: n } }` / `{ turn_left: { degrees: n } }` |
| 三角函数 | `{ mathop: { operator: cos\|sin\|sqrt\|abs\|atan, num: 值 } }` |
| 取整 | `{ round: 值 }`（Scratch 自带「四舍五入」） |
| 距离 | `{ distance_to: { object: 角色名 } }` |
| 某角色属性 | `{ of: { object: 角色名, property: "x position" } }` |
| 造型编号 | `{ costume_number_name: null }` |
| 虚像 | `{ set_ghost: { value: 100 } }` |
| 列表：加入 | `{ add_to_list: { item: 值, list: 列表名 } }` |
| 列表：替换第 n 项 | `{ replace_item_of_list: { item: 值, index: n, list: 列表名 } }` |
| 列表：读第 n 项 | `{ item_of_list: { index: n, list: 列表名 } }` |
| 列表：长度 | `{ length_of_list: { list: 列表名 } }` |
| 列表：某值在第几项 | `{ item_num_of_list: { item: 值, list: 列表名 } }` |
| 画笔 | `{ pen_clear: null }` / `{ pen_down: null }` / `{ pen_up: null }` / `{ pen_stamp: null }` |
| 克隆 | `{ create_clone_of: { clone: 角色名 } }` / `{ when_start_as_clone: { clone: _myself_ } }` |
| 停止 | `{ stop: { stop_option: this script } }`（只停当前脚本） |

> ⚠️ **Scratch 3 的自定义积木没有返回值**：
> 需要「函数返回值」时，用「全局变量 + 自定义积木」组合。

> ⚠️ **「与/或」只有 2 个输入**：4 个条件必须嵌套成 `and: [and[a b] and[c d]]`，
> 多余的会被**静默丢弃**。

> ⚠️ **`stop this script` 会停掉整个当前脚本**：
> 想「只跳出循环」必须把循环体抽成自定义积木。
