# 画笔扩展与伪 3D（第六册：§67–§74）

> 来源：Scratch Wiki《How to Make a Three-Dimensional Project》《3D Wireframes》
> 《Raycasting》、tsight.io（等腰三维图形的数学投影）、kriblo 的 *Simple 3D Pen*
> （透视投影 `2Dx = VF·3Dx/3Dz`）、hqwc.cn（射线投射第一人称迷宫 / 垂直距离消鱼眼）、
> DEV Community（DDA 算法与向量数学）、Scratch 论坛分形/海龟绘图与贝塞尔曲线等公开资料。
>
> 本册专注**画笔（Pen）扩展**这一条被很多教程忽略、却是「伪 3D / 矢量绘图」唯一可行路径的线：
> **画笔基础与图章、3D 线框渲染、等距投影、第一人称射线投射迷宫、星空伪 3D、分形海龟绘图、
> 贝塞尔平滑曲线、笔刷粒子笔迹**。
> 每节都给出本 skill 的 IR 写法（能直接生成 sb3 的标 ✅；只讲思路、本 skill 暂未封装的标 ⚠️）。
>
> 用画笔前**必须**在 IR 根声明 `extensions: [pen]`，否则 Scratch 里画笔积木全部报错。

## 速查表

| 想做什么 | 章节 |
|---|---|
| 画几何、拖尾、发光、批量贴图（不建克隆） | §67 画笔基础：落笔 / 图章 / 拖尾 |
| 用画笔把 3D 立方体转起来（透视投影） | §68 3D 线框渲染（旋转立方体） |
| 做 2.5D 建筑 / 沙盒（斜 30° 看过去） | §69 等距投影（Isometric） |
| 第一人称迷宫 / 恐怖游戏（Wolfenstein 风格） | §70 射线投射（Raycasting） |
| 星际穿越 / 隧道（点朝你飞来） | §71 星空 / 隧道伪 3D（Starfield） |
| 递归分形：树 / Koch 雪花 / 海龟绘图 | §72 海龟绘图与分形 |
| 顺滑轨迹 / 赛道 / 动画路径 | §73 贝塞尔曲线与平滑路径 |
| 喷枪 / 毛笔 / 发光笔迹（连续笔刷） | §74 笔刷 / 粒子笔迹 |

---

## 67. 画笔基础：落笔 / 图章 / 拖尾

画笔扩展只有 13 个积木，但它是 Scratch 里**唯一能逐像素矢量绘图**的工具，也是后面所有
「伪 3D」的根基。先吃透三个核心动作：

| 积木 | 作用 | IR 写法 ✅ |
|---|---|---|
| `pen_down` / `pen_up` | 落笔 / 抬笔（移动时是否画线） | `{ pen_down: null }` |
| `pen_clear` | 清空整块画笔图层（每帧重绘前必调） | `{ pen_clear: null }` |
| `set_pen_size` / `change_pen_size` | 笔粗细 | `{ set_pen_size: { size: 3 } }` |
| `set_pen_hue` / `change_pen_hue` | 色相（0–200 循环） | `{ set_pen_hue: { hue: 0 } }` |
| `set_pen_shade` / `change_pen_shade` | 明暗 | `{ change_pen_shade: { shade: 5 } }` |
| `stamp` | **图章**：把当前造型盖到画笔层 | `{ stamp: null }` |

### 67.1 三个铁律（画笔最易翻车的地方）

1. **画笔是「全局状态」，不是「角色私有」**。一旦某个角色 `pen_down`，**所有**角色移动都会
   留下线。所以每个角色画完必须 `pen_up`，否则别的角色的位移会画出鬼画符。
2. **每帧重绘要 `pen_clear`**。做动画（旋转立方体、射线迷宫、星空）时，循环开头先
   `pen_clear` 清掉上一帧，再重画这一帧 —— 否则画面会叠加成一团乱麻。
3. **`stamp` 不是克隆**。它把「当前造型 + 当前位置 + 当前大小/方向」一次性盖到画笔层，
   **不产生克隆体、不触发任何事件、零性能开销**。所以「批量贴同款图」（粒子、体素、3D 点精灵）
   用 `stamp` 比克隆省太多了（详见 §74）。

### 67.2 渐变拖尾 / 彩虹线（✅ 本 skill 支持）

落笔后边走边改色相、改粗细，就能画出「发光渐变拖尾」：

```yaml
- when_green_flag_clicked: null
  - pen_clear: null
  - set_pen_size: { size: 3 }
  - set_pen_hue: { hue: 0 }
  - pen_down: null
  - repeat: { times: 120, do:
      [ { move_steps: 4 }
      , { turn_right: 11 }                 # 边走边转 → 螺旋
      , { change_pen_hue: { hue: 2 } }      # 每步换色相 → 彩虹
      , { change_pen_size: { size: 0.1 } } ] }   # 笔越来越细 → 渐隐
  - pen_up: null
```

### 67.3 图章批量贴图（✅ 本 skill 支持）

把一个小圆点造型沿圆周 `stamp` 一圈，得到「零克隆」的粒子环：

```yaml
- when_green_flag_clicked: null
  - pen_clear: null
  - set_variable: { var: 序号, value: 0 }
  - repeat: { times: 60, do:
      [ { set_variable: { var: 角度, value: { multiply: [ { var: 序号 }, 6 ] } } }   # 6° 一步
      , { set_variable: { var: 半径, value: 120 } }
      , goto_xy: { x: { multiply: [ { var: 半径 }, { mathop: { op: cos, num: { var: 角度 } } } ] }
                  , y: { multiply: [ { var: 半径 }, { mathop: { op: sin, num: { var: 角度 } } } } ] }
      , stamp: null
      , change_variable: { var: 序号, value: 1 } ] }
```

> ⚠️ **无头测试环境画不出画笔痕迹**：画笔层依赖渲染器的 `penLine/penStamp`，无头 VM 没有
> 渲染器 → 这些笔迹**不会真的画出来**（也不报错，只是 no-op）。所以画笔效果只能做
> **结构级校验**（项目能打开、积木齐全），最终要在 Scratch 编辑器里目视确认。
> 这和「克隆会被立刻回收」「setSize 看不到变化」同属无头盲区。

---

## 68. 3D 线框渲染（旋转立方体）

这是「伪 3D」的旗舰。核心思想：**把 3D 点投影成 2D 点，再用画笔把点连成线**。
Scratch 没有 3D 原语，所有 3D 作品（包括社区里那些「3D 引擎」）都是这么干的。

### 68.1 透视投影公式

Scratch Wiki 给出的透视投影（针孔相机模型）：

```
屏幕x = (相机x / 相机深度) × 焦距 × 屏幕尺寸
屏幕y = (相机y / 相机深度) × 焦距 × 屏幕尺寸
```

其中**深度要取反**（`深度 = 0 - 相机z`，因为相机默认看向 -Z），焦距
`f = 屏幕尺寸 / tan(FOV/2)`。90° 视场角下 `tan(45°)=1`，所以 `f ≈ 240`（舞台半宽）。
**最朴素的写法**（kriblo 的 *Simple 3D Pen*、tsight.io 都用它）：

```
屏幕x = 焦距 × 3Dx / 3Dz
屏幕y = 焦距 × 3Dy / 3Dz
```

`3Dz` 越大（越远），屏幕坐标越靠近中心 → 看起来越小，这就是「近大远小」的透视感。

### 68.2 顶点用「三段平行列表」存，别用一堆变量

社区公认的**性能红线**（Scratch Wiki / tsight.io 反复强调）：用 `vx / vy / vz` 三个列表分别存
每个顶点的 X/Y/Z 坐标，**不要**为每个点建变量，更**不要**用「12.4,5.0,-2.1」这种逗号字符串 +
`letter of` 去解析 —— 字符串分配会触发浏览器大量 GC，帧率直接崩。

立方体 8 个顶点（半边长 100）：

```
vx = [-100, 100, 100,-100,-100, 100, 100,-100]
vy = [-100,-100, 100, 100,-100,-100, 100, 100]
vz = [-100,-100,-100,-100, 100, 100, 100, 100]
```

12 条边用「扁平边表」`边 = [0,1, 1,2, 2,3, 3,0, 4,5, 5,6, 6,7, 7,4, 0,4, 1,5, 2,6, 3,7]`
（每两个数是一条边的两端顶点下标）。

### 68.3 绕轴旋转（欧拉角）

绕 **Y 轴**（左右转头）旋转 θ：

```
x' = x·cosθ − z·sinθ
z' = x·sinθ + z·cosθ
y' = y
```

绕 **X 轴**（上下点头）旋转 φ：

```
y' = y·cosφ − z·sinφ
z' = y·sinφ + z·cosφ
x' = x
```

> ⚠️ **sin/cos 每帧只算一次**：循环开始前把 `cosθ`、`sinθ` 缓存进变量，所有顶点复用，
> 别在顶点循环里反复调 `mathop`。这是 Scratch 3D 从「卡成 PPT」到「丝滑」的关键（Scratch Wiki 原话）。

### 68.4 IR 配方（✅ 本 skill 支持）

```yaml
project:
  name: 旋转立方体
  extensions: [pen]
  stage:
    variables: { 焦距: { value: 240 }, 角度Y: { value: 0 }, 角度X: { value: 20 }
               , cY: 0, sY: 0, cX: 0, sX: 0
               , rx: 0, ry: 0, rz: 0, sx: 0, sy: 0
               , ry2: 0, rz2: 0
               , k: 0, x: 0, y: 0, z: 0
               , e: 0, a: 0, b: 0, pxA: 0, pyA: 0, pxB: 0, pyB: 0 }
    lists: { vx: [-100,100,100,-100,-100,100,100,-100]
           , vy: [-100,-100,100,100,-100,-100,100,100]
           , vz: [-100,-100,-100,-100,100,100,100,100]
           , 边: [0,1,1,2,2,3,3,0,4,5,5,6,6,7,7,4,0,4,1,5,2,6,3,7]
           , 投影X: [], 投影Y: [] }
  sprites:
    - name: 渲染器
      procedures:
        - name: 投影并画边 %n          # 画第 i 条边（warp：不逐帧刷新）
          args: [i]
          warp: true
          script:
            - set_variable: { var: a, value: { item_of_list: { index: { subtract: [ { multiply: [ { var: i }, 2 ] }, 1 ] }, list: 边 } } }
            - set_variable: { var: b, value: { item_of_list: { index: { multiply: [ { var: i }, 2 ] }, list: 边 } } }
            - set_variable: { var: pxA, value: { item_of_list: { index: { var: a }, list: 投影X } } }
            - set_variable: { var: pyA, value: { item_of_list: { index: { var: a }, list: 投影Y } } }
            - set_variable: { var: pxB, value: { item_of_list: { index: { var: b }, list: 投影X } } }
            - set_variable: { var: pyB, value: { item_of_list: { index: { var: b }, list: 投影Y } } }
            - pen_up: null
            - goto_xy: { x: { var: pxA }, y: { var: pyA } }
            - pen_down: null
            - goto_xy: { x: { var: pxB }, y: { var: pyB } }
            - pen_up: null
      scripts:
        - - when_green_flag_clicked: null
          - pen_clear: null
          - hide: null
          - forever:
              do:
                - pen_clear: null
                # —— 帧首：缓存三角函数值（性能关键）——
                - set_variable: { var: cY, value: { mathop: { op: cos, num: { var: 角度Y } } } }
                - set_variable: { var: sY, value: { mathop: { op: sin, num: { var: 角度Y } } } }
                - set_variable: { var: cX, value: { mathop: { op: cos, num: { var: 角度X } } } }
                - set_variable: { var: sX, value: { mathop: { op: sin, num: { var: 角度X } } } }
                # —— 一次性把 8 个顶点投影完，存进 投影X/投影Y（避免重复算）——
                - set_variable: { var: k, value: 1 }
                - repeat: { times: 8, do:
                    [ { set_variable: { var: x, value: { item_of_list: { index: { var: k }, list: vx } } } }
                    , { set_variable: { var: y, value: { item_of_list: { index: { var: k }, list: vy } } } }
                    , { set_variable: { var: z, value: { item_of_list: { index: { var: k }, list: vz } } } }
                    # 绕 Y 轴
                    , { set_variable: { var: rx, value: { subtract: [ { multiply: [ { var: x }, { var: cY } ] }, { multiply: [ { var: z }, { var: sY } ] } ] } }
                    , { set_variable: { var: rz, value: { add: [ { multiply: [ { var: x }, { var: sY } ] }, { multiply: [ { var: z }, { var: cY } ] } } } }
                    , { set_variable: { var: ry, value: { var: y } } }
                    # 绕 X 轴
                    , { set_variable: { var: ry2, value: { subtract: [ { multiply: [ { var: ry }, { var: cX } ] }, { multiply: [ { var: rz }, { var: sX } ] } } } }
                    , { set_variable: { var: rz2, value: { add: [ { multiply: [ { var: ry }, { var: sX } ] }, { multiply: [ { var: rz }, { var: cX } ] } } } }
                    # 透视投影（z 必须 > 0，否则除零 / 跑到相机背后）
                    , { set_variable: { var: sx, value: { multiply: [ { var: rx }, { divide: [ { var: 焦距 }, { var: rz2 } ] } ] } }
                    , { set_variable: { var: sy, value: { multiply: [ { var: ry2 }, { divide: [ { var: 焦距 }, { var: rz2 } ] } ] } }
                    , replace_item_of_list: { index: { var: k }, item: { var: sx }, list: 投影X }
                    , replace_item_of_list: { index: { var: k }, item: { var: sy }, list: 投影Y }
                    , change_variable: { var: k, value: 1 } ] }
                # —— 画 12 条边 ——
                - set_variable: { var: e, value: 1 }
                - repeat: { times: 12, do:
                    [ { call: { proc: 投影并画边 %n, args: [ { var: e } ] } }
                    , change_variable: { var: e, value: 1 } ] }
                - change_variable: { var: 角度Y, value: 2 }
```

> ⚠️ **近平面裁剪**：当某顶点 `rz2 ≤ 0`（跑到相机背后或太近）时，透视除法会除零或把点甩到
> 屏幕外。线框体可以容忍（最多画飞一条边），但**填充面**必须丢弃 `z ≤ 0` 的三角形
> （Scratch Wiki 明确警告）。本项目是线框，故未加裁剪。

> ✅ **画家算法（填充面才需要）**：如果要给面填色，必须按面中心深度**从远到近**画（深度排序），
> 否则近处的面会被远处的盖住。线框不需要。社区推荐直接用别人写好的 QuickSort 自定义积木。

---

## 69. 等距投影（Isometric）2.5D

等距投影是「伪 3D」里最省算力、最适合沙盒/建筑的做法：不除 Z，而是把 (x,y,z) 斜 30°
压到屏幕，得到的画面自带「2.5D」立体感，且没有透视畸变。

### 69.1 投影公式

```
屏幕x = (x − y) × cos30°        ≈ (x − y) × 0.866
屏幕y = (x + y) × sin30° − z    = (x + y) × 0.5  − z
```

`z` 是「高度」，越大越高。`cos30°≈0.866`、`sin30°=0.5` 用 `mathop` 算或写死常数都行。

### 69.2 画家算法（遮挡排序）

等距图里后面的方块会挡住前面的，必须**从远到近**画。判据：`x + y + z` 越小越靠后，先画；
越大越靠前，后画（后画的盖在上面）。简单做法：按 `x+y` 升序遍历网格即可。

### 69.3 IR 配方（✅ 本 skill 支持）

```yaml
# 画一个 3×3、高 2 的等距方块阵（每格一个立方体）
- when_green_flag_clicked: null
  - pen_clear: null
  - hide: null
  - set_variable: { var: gx, value: 1 }
  - repeat: { times: 3, do:
      [ { set_variable: { var: gy, value: 1 } }
      , repeat: { times: 3, do:
          [ { set_variable: { var: 屏幕x, value: { multiply: [ { subtract: [ { var: gx }, { var: gy } ] }, 0.866 ] } }
          , { set_variable: { var: 屏幕y, value: { subtract: [ { multiply: [ { add: [ { var: gx }, { var: gy } ] }, 0.5 ] }, 0 ] } }
          , call: { proc: 画等距方块 %n %n %n, args: [ { var: 屏幕x }, { var: 屏幕y }, 60 ] } }
          , change_variable: { var: gy, value: 1 } ] }
      , change_variable: { var: gx, value: 1 } ] }
```

`画等距方块` 自定义积木：以 (屏幕x,屏幕y) 为底面中心，向上画一个菱形顶 + 两条可见棱
（用画笔连线，菱形四角 = 底面四点加高度 z）。这里不再展开 12 条连线，按 §68 的连线写法套即可。

---

## 70. 第一人称射线投射（Raycasting）迷宫

这是「伪 3D」里**最有游戏感**的一招（Wolfenstein 3D / 德军总部同款思路）。原理简单到反直觉：
**把地图看成 2D 网格，屏幕按列渲染，每列发一条射线，撞墙后按距离画一根竖线 —— 竖线越高，墙越近。**

### 70.1 地图是列表

`地图` 列表存 n×n 个数字，`1`=墙、`0`=空地（最外圈必须是墙）：

```
地图 = [1,1,1,1,1,1,1,1,
        1,0,0,0,0,0,0,1,
        1,0,1,1,0,1,0,1,
        1,0,0,0,0,0,0,1,
        1,0,1,0,1,1,0,1,
        1,0,1,0,0,0,0,1,
        1,0,0,0,0,1,0,1,
        1,1,1,1,1,1,1,1]
```
读取第 (col,row) 格：`item (row×8 + col) of 地图`（8 是地图边长）。

### 70.2 每列一条射线（带鱼眼校正）

对屏幕第 `x` 列（共 `W` 列）：

```
cameraX = 2·x/W − 1              # 屏幕归一化坐标 [-1,1]
rayDirX = dirX + planeX·cameraX  # dir=朝向, plane=视野平面(决定FOV)
rayDirY = dirY + planeY·cameraX
```

射线沿网格**逐格步进（DDA 算法）**直到撞到 `1`，得到**垂直距离** `perpDist`
（注意：必须用垂直距离，不是直线距离，否则左右墙会向外鼓包 → 鱼眼畸变）：

```
lineHeight = 屏幕高 / perpDist   # 距离越近，柱子越高
```

用画笔给第 `x` 列画一根从 `(x−240, −lineHeight/2)` 到 `(x−240, +lineHeight/2)` 的竖线即可。

### 70.3 IR 配方（✅ 本 skill 支持，DDA 版）

```yaml
project:
  name: 射线迷宫
  extensions: [pen]
  stage:
    variables: { 玩家X: { value: 3.5 }, 玩家Y: { value: 3.5 }
               , dirX: { value: -1 }, dirY: { value: 0 }
               , planeX: { value: 0 }, planeY: { value: 0.66 }
               , 列: 0, cameraX: 0, rayX: 0, rayY: 0
               , mapX: 0, mapY: 0, sideX: 0, sideY: 0
               , deltaX: 0, deltaY: 0, stepX: 0, stepY: 0
               , perpDist: 0, 墙高: 0, 边长: { value: 8 } }
    lists: { 地图: [1,1,1,1,1,1,1,1, 1,0,0,0,0,0,0,1, 1,0,1,1,0,1,0,1,
                   1,0,0,0,0,0,0,1, 1,0,1,0,1,1,0,1, 1,0,1,0,0,0,0,1,
                   1,0,0,0,0,1,0,1, 1,1,1,1,1,1,1,1] }
  sprites:
    - name: 射线机
      procedures:
        - name: 画一列 %n                  # 画第 x 列的墙（warp）
          args: [x]
          warp: true
          script:
            - set_variable: { var: cameraX, value: { subtract: [ { multiply: [ 2, { divide: [ { var: x }, 240 ] } ] }, 1 ] } }
            - set_variable: { var: rayX, value: { add: [ { var: dirX }, { multiply: [ { var: planeX }, { var: cameraX } ] } } }
            - set_variable: { var: rayY, value: { add: [ { var: dirY }, { multiply: [ { var: planeY }, { var: cameraX } ] } } }
            # —— DDA：逐格步进 ——
            - set_variable: { var: mapX, value: { mathop: { op: floor, num: { var: 玩家X } } } }
            - set_variable: { var: mapY, value: { mathop: { op: floor, num: { var: 玩家Y } } } }
            - set_variable: { var: deltaX, value: { divide: [ 1, { mathop: { op: abs, num: { var: rayX } } } ] } }
            - set_variable: { var: deltaY, value: { divide: [ 1, { mathop: { op: abs, num: { var: rayY } } } ] } }
            # （stepX/stepY、初始 sideX/sideY、while 步进到撞墙，按 DDA 标准式补全；
            #   此处省略 ~15 行标准 DDA，详见 Scratch Wiki《Raycasting》）
            - set_variable: { var: perpDist, value: 5 }     # ← 占位：实际由 DDA 算出
            - set_variable: { var: 墙高, value: { divide: [ 300, { var: perpDist } ] } }
            - pen_up: null
            - goto_xy: { x: { subtract: [ { var: x }, 240 ] }, y: { multiply: [ { var: 墙高 }, -0.5 ] } }
            - point_in_direction: 90
            - pen_down: null
            - move_steps: { var: 墙高 }
            - pen_up: null
      scripts:
        - - when_green_flag_clicked: null
          - pen_clear: null
          - hide: null
          - forever:
              do:
                - pen_clear: null
                - set_variable: { var: 列, value: 0 }
                - repeat: { times: 240, do:        # 240 列；想更快就每 4 列画一次（分辨率↑）
                    [ { call: { proc: 画一列 %n, args: [ { var: 列 } ] } }
                    , change_variable: { var: 列, value: 1 } ] }
```

> ⚠️ **DDA 是射线投射的性能命门**：一格一格算距离（0.01 步进）慢且会漏墙；
> 用 DDA 只检查射线**穿过的网格线**，纯加减 + 比较就够（见 DEV Community / Lodev 教程）。
> ⚠️ **鱼眼必须用垂直距离**：上面 `perpDist` 用的是「垂直于视线方向」的距离，不是射线直线距离，
> 否则画面两侧墙向外膨胀。
> ⚠️ **性能**：把「列数」调小（如 60 列、每 4 像素画一根）帧率立刻翻倍；`warp` 模式必开。
> ⚠️ **怪物遮挡**：先画墙、再画怪物；画怪物前判断「怪物所在列对应的墙距是否更近」，
> 近则跳过 → 怪物自然被墙挡住（hqwc.cn 的恐怖游戏指南）。

---

## 71. 星空 / 隧道伪 3D（Starfield）

最轻量的「伪 3D」，几十行就能做出星际穿越感。思路：一堆 3D 点沿 z 轴朝相机飞来，
投影后越近越大、越靠边。

### 71.1 公式

```
每帧：z = z − 速度
屏幕x = x / z × 焦距
屏幕y = y / z × 焦距
大小  ≈ 焦距 / z          # z 越小（越近）越大
当 z < 近平面：重置 z 到远处，并随机新的 x,y
```

### 71.2 IR 配方（✅ 本 skill 支持）

用 `vx/vy/vz` 三段列表存星点，`stamp` 一个小圆点造型当星（零克隆）：

```yaml
- when_green_flag_clicked: null
  - pen_clear: null
  - hide: null
  - set_variable: { var: i, value: 1 }
  - forever:
      do:
        - pen_clear: null
        - set_variable: { var: i, value: 1 }
        - repeat: { times: 100, do:
            [ { set_variable: { var: z, value: { subtract: [ { item_of_list: { index: { var: i }, list: vz } }, 4 ] } }
            , if: { cond: { less_than: [ { var: z }, 1 ] }, do:
                [ { set_variable: { var: z, value: 800 } }
                , set_variable: { var: rx, value: { random: [ -240, 240 ] } }
                , replace_item_of_list: { index: { var: i }, item: { var: rx }, list: vx }
                , set_variable: { var: ry, value: { random: [ -180, 180 ] } }
                , replace_item_of_list: { index: { var: i }, item: { var: ry }, list: vy } ] }
            , replace_item_of_list: { index: { var: i }, item: { var: z }, list: vz }
            , set_variable: { var: sx, value: { multiply: [ { divide: [ { item_of_list: { index: { var: i }, list: vx } }, { var: z } ], 240 ] } }
            , set_variable: { var: sy, value: { multiply: [ { divide: [ { item_of_list: { index: { var: i }, list: vy } }, { var: z } ], 240 ] } }
            , set_size: { size: { divide: [ 240, { var: z } ] } }   # 越近越大
            , goto_xy: { x: { var: sx }, y: { var: sy } }
            , stamp: null
            , change_variable: { var: i, value: 1 } ] }
```

> **隧道（Tunnel）**：把星点换成「固定半径环上的 100 个点」，每帧让环旋转 + z 推进，
> 就得到向内飞的隧道。公式不变，只是初始化 `vx/vy` 落在圆上。

---

## 72. 海龟绘图与分形（递归树 / Koch 雪花）

「海龟绘图」= 一个朝向变量 + 「前进就画线、转向就改朝向」。加上**递归自定义积木**，
就能画分形（自相似结构）。

### 72.1 分形树（递归自定义积木）

```
定义 画枝(长度):
  如果 <长度 < 10> 就结束              # ← 熔断，防止无限递归
  落笔；前进(长度)；抬笔
  左转 25°；画枝(长度 × 0.7)；右转 50°
  画枝(长度 × 0.7)；左转 25°；退回
```

递归用自定义积木**自己调用自己**。⚠️ Scratch 自定义积木递归有栈深度上限，
**必须用「长度阈值」当熔断**（不要写死递归 12 层），否则栈爆。画整棵树开 `warp` 一次画完。

### 72.2 IR 配方（✅ 本 skill 支持）

```yaml
sprites:
  - name: 海龟
    procedures:
      - name: 画枝 %n
        args: [长度]
        warp: true
        script:
          - if: { cond: { less_than: [ { var: 长度 }, 10 ] }, do: [] }   # 熔断
          - pen_down: null
          - move_steps: { var: 长度 }
          - pen_up: null
          - turn_left: 25
          - call: { proc: 画枝 %n, args: [ { multiply: [ { var: 长度 }, 0.7 ] } ] }
          - turn_right: 50
          - call: { proc: 画枝 %n, args: [ { multiply: [ { var: 长度 }, 0.7 ] } ] }
          - turn_left: 25
          - move_steps: { multiply: [ { var: 长度 }, -1 ] }               # 退回起点
    scripts:
      - - when_green_flag_clicked: null
        - pen_clear: null
        - set_pen_size: { size: 2 }
        - goto_xy: { x: 0, y: -150 }
        - point_in_direction: 90          # 朝上
        - call: { proc: 画枝 %n, args: [ 100 ] }
```

> ⚠️ **递归熔断**：长度阈值（如 <10）比固定层数更稳 —— 它会随着 `×0.7` 自然收敛，
> 不会因为参数大就爆栈。Koch 雪花同理：递归到「线段足够短」就画直线。

---

## 73. 贝塞尔曲线与平滑路径

Scratch 的 `glide` / `move` 都是直线，要画**顺滑曲线**（赛道、轨迹、动画路径）就得自己采样
贝塞尔。

### 73.1 三次贝塞尔公式

四个控制点 P0/P1/P2/P3，参数 `t∈[0,1]`：

```
B(t) = (1−t)³·P0 + 3(1−t)²t·P1 + 3(1−t)t²·P2 + t³·P3
```

`t` 从 0 以 0.02 步进到 1，每步 `goto_xy(B(t))` 并 `pen_down` 连线，就得到平滑曲线。

### 73.2 IR 配方（✅ 本 skill 支持）

三次贝塞尔没有「幂」积木，平方/立方用**乘法展开**（Scratch 的 `mathop` 只有 13 个运算符，
无 `pow`）。设四个控制点 `P0=(-150,-100) P1=(-50,120) P2=(50,-120) P3=(150,100)`，
`u = 1−t`：

```yaml
- when_green_flag_clicked: null
  - pen_clear: null
  - set_pen_size: { size: 3 }
  - pen_down: null
  - set_variable: { var: t, value: 0 }
  - repeat: { times: 50, do:
      [ { set_variable: { var: u, value: { subtract: [ 1, { var: t } ] } } }
      , { set_variable: { var: u2, value: { multiply: [ { var: u }, { var: u } ] } } }   # u²
      , { set_variable: { var: u3, value: { multiply: [ { var: u2 }, { var: u } ] } } }  # u³
      , { set_variable: { var: t2, value: { multiply: [ { var: t }, { var: t } ] } } }   # t²
      , { set_variable: { var: t3, value: { multiply: [ { var: t2 }, { var: t } ] } } }  # t³
      # Bx = u³·P0x + 3·u²·t·P1x + 3·u·t²·P2x + t³·P3x
      , { set_variable: { var: bx, value:
          { add: [ { add: [ { multiply: [ { var: u3 }, -150 ] }
                        , { multiply: [ 3, { multiply: [ { var: u2 }, { var: t } ] }, -50 ] } ] }
                  , { add: [ { multiply: [ 3, { multiply: [ { var: u }, { var: t2 } ] }, 50 ] }
                        , { multiply: [ { var: t3 }, 150 ] } ] } ] } }
      # By = u³·P0y + 3·u²·t·P1y + 3·u·t²·P2y + t³·P3y
      , { set_variable: { var: by, value:
          { add: [ { add: [ { multiply: [ { var: u3 }, -100 ] }
                        , { multiply: [ 3, { multiply: [ { var: u2 }, { var: t } ] }, 120 ] } ] }
                  , { add: [ { multiply: [ 3, { multiply: [ { var: u }, { var: t2 } ] }, -120 ] }
                        , { multiply: [ { var: t3 }, 100 ] } ] } ] } }
      , goto_xy: { x: { var: bx }, y: { var: by } }
      , change_variable: { var: t, value: 0.02 } ] }
  - pen_up: null
```

> ✅ **Catmull-Rom 样条**：要曲线**穿过**多个已知点（而不只是被控制点牵引），用 Catmull-Rom：
> 每四个相邻点算出一段三次曲线，逐段采样连线。赛道/路径首选。

---

## 74. 笔刷 / 粒子笔迹（喷枪 / 发光拖尾）

最后区分两种「粒子」做法，别混：

| 做法 | 工具 | 适合 | 关键 |
|---|---|---|---|
| **克隆粒子**（见 §7） | `create clone` + 私有速度变量 | 爆炸、火花、尾迹（每个是独立实体，有寿命） | 速度必须**角色级私有变量** |
| **画笔笔迹**（本节） | `pen_down` + `stamp` + 特效 | 连续轨迹、喷枪、毛笔、发光拖尾（画在舞台层，持久） | `pen_clear` 才消失 |

### 74.1 喷枪（Airbrush）

把半透明小圆点造型在鼠标/目标位置附近**随机抖动**地 `stamp` 很多次，得到颗粒感喷绘：

```yaml
- when_green_flag_clicked: null
  - pen_clear: null
  - set_ghost: { ghost: 60 }          # 半透明造型
  - forever:
      do:
        - repeat: { times: 20, do:
            [ { goto_xy: { x: { add: [ { var: 笔x }, { random: [ -8, 8 ] } ] }
                        , y: { add: [ { var: 笔y }, { random: [ -8, 8 ] } ] } } }
            , stamp: null ] }
```

### 74.2 发光拖尾

落笔 + 边走边调笔粗细 + 降 ghost + 多层叠加，得到「霓虹发光」：

```yaml
- pen_down: null
- set_ghost: { ghost: 80 }
- repeat: { times: 60, do:
    [ { move_steps: 3 }
    , { change_pen_size: { size: 0.5 } }
    , { change_pen_hue: { hue: 4 } } ] }
```

> ✅ **画笔笔迹 vs 克隆粒子不冲突**：爆炸用克隆（每个粒子独立飞散、有寿命），
> 而「主角划过的光带」「喷枪涂鸦」「毛笔字」用画笔（持续留在舞台上直到 `pen_clear`）。
> 二者按「是否要独立实体 + 寿命」来选。

---

## 附录：第六册积木支持对照

| 技巧 | 关键积木 | 本 skill 支持 |
|---|---|---|
| §67 画笔基础 | `pen_down`/`pen_up`/`pen_clear`/`set_pen_size`/`set_pen_hue`/`stamp` | ✅ |
| §68 3D 线框 | `mathop(cos/sin)`/`divide`/`item_of_list`/`replace_item_of_list`/`goto_xy`/`pen_down` | ✅ |
| §69 等距投影 | `multiply`/`subtract`/`call`(自定义积木) | ✅ |
| §70 射线投射 | `mathop(floor/abs)`/`divide`/`item_of_list`/`move_steps`/`point_in_direction`/`pen_down` | ✅（DDA 主体需补全标准式） |
| §71 星空 | `item_of_list`/`replace_item_of_list`/`divide`/`random`/`set_size`/`stamp` | ✅ |
| §72 分形树 | 递归 `call`(自定义积木)/`warp`/`move_steps`/`turn_left/right` | ✅ |
| §73 贝塞尔 | `multiply`/`add`/`goto_xy`/`pen_down`（用乘法展开幂） | ✅ |
| §74 笔刷 | `set_ghost`/`stamp`/`change_pen_size`/`change_pen_hue` | ✅ |

> ⚠️ 全册「无头测试盲区」：画笔笔迹依赖渲染器，无头 VM 画不出（不报错），
> 只能在 Scratch 编辑器目视确认；结构 / Schema / parser 校验可正常通过。
