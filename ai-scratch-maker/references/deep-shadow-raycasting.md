# 阴影光追专项教程（2D 可见性多边形）

> 本篇是第九册 §99「视野盲区引擎」的**深入版**：把「谁能被看见」这件事做到严谨。
> 配套工程：`examples/technique_probe13.yaml`（构建产物 `examples/output/technique_probe13.sb3`）。
> 全部代码已通过 build + 四层校验 + 冒烟测试。

---

## 0. 先看结论：两种算法，别混用

| | 简化版（§99 原版） | 严谨版（本篇 / probe13） |
|---|---|---|
| 思路 | 每个墙角算「玩家→墙角夹角」，找与实体夹角最接近、且距离更近的墙角 | 对每个墙角方向投 3 条射线（±ε）取最近命中，连成**可见性多边形**；实体判定直接投一条射线 |
| 数据 | 只需要墙角点表 | 需要**墙体线段**表（A、B 两点） |
| 代价 | O(墙角数)，实现极简 | O(墙角数 × 墙数)，但结果正确 |
| 误判 | 实体在墙的「侧后方」时会误判成阴影 | 不会 |
| 适合 | 快速原型、墙体简单 | 潜行/恐怖/探索、需要精确判定 |

**§99 的简化版会误判**：实体在墙角「侧后方但没被挡」时，
它的方向角仍然最接近某个墙角角，如果那个墙角恰好更近，就会被判成阴影。
严谨版不依赖角度，直接问「这条视线有没有被墙挡住」。

---

## 1. 核心几何：射线 × 线段求交（只要叉积，不要开方）

把墙看成**线段** `A → B`，射线看成 `O + t·D`（`O` 是玩家，`D` 是单位方向向量）。

```
E  = B - A                     （线段方向）
denom = cross(D, E) = Dx*Ey - Dy*Ex
t     = cross(A-O, E) / denom  （命中点沿射线的距离）
u     = cross(A-O, D) / denom  （命中点在线段上的比例）
命中条件： t > 0 且 0 ≤ u ≤ 1
```

三个要点：

1. **不用 sqrt**：`t` 出来就是距离，因为 `D` 是单位向量。
2. **不用 atan2**：全程只有向量运算，角度问题自动消失（见 §4.1 的坑）。
3. **`u` 的意义**：`u` 把「射线打到墙所在的那条无限长的直线」和「真的打到这段墙上」区分开。
   `u` 不在 `[0,1]` 就说明射线擦着墙的延长线过去了，不算命中。

IR 配方（Scratch 无 `>=` / `<=`，用 `not` 反写）：

```yaml
- set_variable: { var: 分母, value:
    { subtract: [
        { multiply: [ { var: 方向X }, { var: EY } ] },
        { multiply: [ { var: 方向Y }, { var: EX } ] } ] } }
- if: { cond: { greater_than: [ { mathop: { op: abs, num: { var: 分母 } } }, 0.0001 ] },
    do: [
      - set_variable: { var: t, value:
          { divide: [
              { subtract: [ { multiply: [ { var: AOx }, { var: EY } ] },
                            { multiply: [ { var: AOy }, { var: EX } ] } ] },
              { var: 分母 } ] } }
      - set_variable: { var: u, value:
          { divide: [
              { subtract: [ { multiply: [ { var: AOx }, { var: 方向Y } ] },
                            { multiply: [ { var: AOy }, { var: 方向X } ] } ] },
              { var: 分母 } ] } }
      - if: { cond: { and: [ { greater_than: [ { var: t }, 0 ] },
                            { and: [ { not: { operand: { less_than: [ { var: u }, 0 ] } } },
                                    { not: { operand: { greater_than: [ { var: u }, 1 ] } } } ] } ] },
          do: [ - if: { cond: { less_than: [ { var: t }, { var: 最近距离 } ] },
                        do: [ - set_variable: { var: 最近距离, value: { var: t } } ] } ] }
    ] }
```

---

## 2. 可见性多边形：为什么每个墙角要投 3 条射线

经典算法（Inigo Quilez 的 visibility polygon）：

1. 玩家在 `O`，每个墙角在 `C`，方向 `D = normalize(C - O)`。
2. 对 `D` 做 **±ε 旋转**，得到 `D₋`、`D₊`（ε 取 0.5° 左右）。
3. 分别投 `D₋`、`D`、`D₊` 三条射线，取**三个命中距离的最小值** `d`。
4. 可见性多边形的这个顶点 = `O + D·d`。
5. 所有墙角按角度排好序，依次连成闭合多边形 = 玩家真正看得见的区域。

**为什么不能只投 1 条**？因为墙角是一个「角」，射线正对着角点时，
可能刚好从墙的**内侧**或**外侧**擦过去，单条射线会给出偏大的距离，
多边形会「鼓包」或「缺角」。投 3 条取最小值，等于取「墙角两侧都能看到的那个更近的点」。

旋转用**旋转矩阵**（不需要 atan / atan2）：

```
D'₋ = ( Dx·cos ε + Dy·sin ε ,  Dy·cos ε - Dx·sin ε )     （转 -ε）
D'₊ = ( Dx·cos ε - Dy·sin ε ,  Dx·sin ε + Dy·cos ε )     （转 +ε）
```

IR 配方（`算顶点 %n %n` 自定义积木）：

```yaml
- set_variable: { var: dx, value: { subtract: [ { var: 点X }, { var: 玩家X } ] } }
- set_variable: { var: dy, value: { subtract: [ { var: 点Y }, { var: 玩家Y } ] } }
- set_variable: { var: len, value: { mathop: { op: sqrt, num:
    { add: [ { multiply: [ { var: dx }, { var: dx } ] },
             { multiply: [ { var: dy }, { var: dy } ] } ] } } } }
- set_variable: { var: ux, value: { divide: [ { var: dx }, { var: len } ] } }
- set_variable: { var: uy, value: { divide: [ { var: dy }, { var: len } ] } }
- set_variable: { var: c, value: { mathop: { op: cos, num: 0.5 } } }
- set_variable: { var: s, value: { mathop: { op: sin, num: 0.5 } } }
# 方向 -ε
- set_variable: { var: rx, value: { add: [ { multiply: [ { var: ux }, { var: c } ] },
                                       { multiply: [ { var: uy }, { var: s } ] } ] } }
- set_variable: { var: ry, value: { add: [ { multiply: [ { var: uy }, { var: c } ] },
                                       { multiply: [ { multiply: [ { var: ux }, { var: s } ] }, -1 ] } ] } }
```

---

## 3. 实体是否在阴影里

最直接：**朝实体投一条射线**，比较命中距离和实体距离。

```
实体距 = |实体 - 玩家|
如果 最近命中距离 < 实体距  ->  实体在阴影里
```

注意「命中距离 < 实体距」而不是「有命中就是阴影」：
实体站在墙**前面**时，射线会先打到实体身后的墙，但命中距离 > 实体距 → 可见 ✓。

---

## 4. 五个必踩的坑（都在真实项目里踩过）

### 4.1 ⚠️ Scratch 3 **没有 atan2 积木**

scratch-vm 只实现了这些运算积木：

```
add / subtract / multiply / divide / lt / equals / gt / and / or / not /
random / join / letter_of / length_of / contains / mod / round / mathop
```

**没有 `operator_atan2`**。如果 IR 里写了 `atan2`，构建器如果照单全收就会生成
一个 VM 不认识的活动积木 → **运行时静默返回 0**，整个算法看起来「跑通了」但结果全错。
（本 skill 已在规范里删掉这条伪积木，并给了自动拒绝。）

想算角度只有两条路：

- **路线 A（推荐）**：干脆不用角度 —— 全文向量 + 叉积（本篇做法）。
- **路线 B**：用 `mathop` 的 `atan`（**单位是度**）自己拼 atan2：

  ```
  x > 0            ->  atan(y/x)
  x < 0 且 y >= 0  ->  atan(y/x) + 180
  x < 0 且 y < 0   ->  atan(y/x) - 180
  x = 0 且 y > 0   ->  90      x = 0 且 y < 0 -> -90      x = 0, y = 0 -> 0
  ```

  Scratch 没有「值的三目运算」（没有 reporter 级 if/else），
  所以必须包成一个**自定义积木**（用全局变量把结果带出来），例：

  ```yaml
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
                - set_variable: { var: 角度, value: { add: [ { var: 角度 }, 180 ] } } } ] } ] }
  ```

> `mathop` 的 `sin / cos / tan / asin / acos / atan` 在**官方编辑器下拉菜单里看不到**
> （菜单只有 abs/floor/ceiling/sqrt/ln/log/e^/10^），但 scratch-vm 实现了它们，
> 运行时能正常算。TurboWarp 等编辑器里能直接选到。给使用者交付时要说明这一点。

### 4.2 ⚠️ `if` 带 `else` 必须用 `if_else`

`control_if` 只有 **一个** 子栈槽位（SUBSTACK），没有 SUBSTACK2。
把 `else` 写进 `if` 里 → **else 分支被静默丢弃**，不报错、不警告，
结果是「条件成立时执行了 A，条件不成立时什么都不做」。
本 skill 的构建器现在会**自动升级**成 `control_if_else` 并打印警告，但建议直接写 `if_else`。

```yaml
- if_else: { cond: { less_than: [ { var: 最近墙距 }, { var: 实体距 } ] },
    do:  [ - set_variable: { var: 实体在阴影, value: 1 } ]
    else: [ - set_variable: { var: 实体在阴影, value: 0 } ] }
```

### 4.3 ⚠️ 自定义积木的参数**不是变量**

Scratch 的自定义积木参数走的是**线程参数栈**：
调用时按「参数名」压栈，过程体里用 `argument_reporter_*`（参数报告器）读取。
如果过程体里用普通「变量」积木读同名变量，拿到的永远是初值。

IR 里过程体的参数引用写法与普通变量**完全一样**（`{ var: 名字 }`），
由构建器自动区分：过程内声明过的参数名 → `argument_reporter`；否则 → 普通变量。

### 4.4 ⚠️ 过程内部的循环变量不能与调用方重名

Scratch 的过程**共享全局变量**。若过程内部用 `序号` 做自己的循环计数，
它会把调用方的 `序号` 冲掉，调用方的循环索引当场错乱
（表现为「只有第 N 个结果是对的」「列表里只有一格有值」）。

**规矩**：每个过程用**自己专属**的循环变量（`墙序号` / `tile序号` / `clone序号`…）。

### 4.5 ⚠️ 角度环绕

`-170°` 与 `170°` 的实际夹角是 `20°`，不是 `340°`。
算夹差后要归一：

```yaml
- if: { cond: { greater_than: [ { var: 角差 }, 180 ] }, do: [
    - set_variable: { var: 角差, value: { subtract: [ 360, { var: 角差 } ] } } ] }
```

（用向量法算夹角可以完全绕开这个问题：直接用点积 `dot(a,b)`，再 `acos` 求角。）

---

## 5. probe13 工程结构

```
舞台（全局变量 + 数据表）
  ├ 墙AX / 墙AY / 墙BX / 墙BY   三条墙体线段（各 3 个）
  ├ 角点X / 角点Y               6 个墙角，按角度逆时针排好
  └ 顶点X / 顶点Y               算出来的可见性多边形顶点
光追（角色，开了画笔）
  ├ 过程 投射方向 %n %n  → 最近距离      （叉积求交，取所有墙里最近的一个）
  ├ 过程 算顶点   %n %n  → 可见点X/可见点Y（±ε 三射线取最近）
  └ 过程 实体判定 %n %n  → 实体在阴影
```

绿旗 → 广播「开始」→ 光追角色依次：
算 6 个可见点 → 画多边形 → 画墙 → 判定 3 个实体并画连线（红=阴影 / 绿=可见）。

**运行时自检值**（冒烟测试实测）：

| 变量 | 实测 | 含义 |
|---|---|---|
| 实体1在阴影 | `1` | (170,0) 被右侧竖墙挡住 ✓ |
| 实体2在阴影 | `1` | (0,200) 被上方横墙挡住 ✓ |
| 实体3在阴影 | `0` | (150,170) 在两面墙的夹缝里，可见 ✓ |
| 顶点X/顶点Y | `[-99.5, 99.5, 99.5, -39.9, 39.9, -99.5]` 等 | 多边形顶点（比墙角略靠内，正是 ±ε 取最近的效果） |

---

## 6. 性能与扩展

- **墙很多时**：`投射方向` 是 O(墙数)。100 段墙 × 6 墙角 = 600 次求交/帧，
  Scratch 里建议：① 过程开 `warp`（Turbo 模式）；② 只对**可见范围内**的墙求交；
  ③ 玩家移动时才重算多边形，别每帧都算。
- **想画阴影扇形**：多边形画完后，把「玩家 → 某实体」这条线按是否在阴影涂色即可
  （probe13 就是这么做的：红=阴影，绿=可见）。
- **想贴图**：把多边形顶点存进列表，用 `图章` 或克隆贴图做「暗区遮罩」。

---

## 7. 和 §99 原版的关系

- §99（第九册）给的是**快速原型**思路：墙角夹角 + 最近角遮挡，代码量小、够用。
- 本篇给的是**严谨版**：线段求交 + 可见性多边形，能精确回答「看得见 / 看不见」。
- 两者共用一套前提：墙体用**数据表**（列表）描述，而不是一堆角色。
  这也是 §93「数据驱动」思想在光影上的延伸。
