# IR 格式说明（中间表示）

AI 只需要写这份 IR，**不要手写 project.json 或 sb3 的数组结构**。
`scripts/build_sb3.py` 会把 IR 编译成合法且能被 Scratch 打开的 `.sb3`。

IR 可以是 YAML（推荐，可读性好）或 JSON。

---

## 1. 顶层结构

```yaml
project:
  name: 我的作品            # 可选
  extensions: [pen]         # 用到扩展积木时必须声明
  stage: {...}              # 舞台（全局作用域）
  sprites: [...]            # 角色列表
```

`stage` 和 `sprites` 至少要有一个。

---

## 2. 舞台与角色

```yaml
project:
  stage:
    backdrops:               # 舞台的背景（内部映射到 Scratch 的 costumes）
      - {name: 草地, asset: assets/bg.png}
    variables: {}           # 全局变量
    lists: {}               # 全局列表
    scripts: []
  sprites:
    - name: 小猫
      x: 0
      y: 0
      size: 100              # 缩放百分比
      direction: 90          # 朝向（90 = 向右）
      visible: true
      rotationStyle: all around   # all around / left-right / don't rotate
      costumes:              # 造型
        - {name: cat1, asset: assets/cat.svg}
      sounds:                # 声音
        - {name: meow, asset: assets/meow.wav}
      variables: {}         # 该角色的局部变量
      lists: {}             # 该角色的局部列表
      procedures: []        # 自定义积木
      scripts: []
```

### 2.1 变量的作用域

- 写在 `stage.variables` / `stage.lists` 里 → **全局**，所有角色共用同一个 id。
- 写在 `sprite.variables` / `sprite.lists` 里 → **该角色专属**。
- 角色脚本里引用全局变量时，直接用变量名即可，序列化器会自动套用舞台的 id，
  不会在角色上重复创建。

### 2.2 云变量

云变量只能声明在**舞台**上：

```yaml
stage:
  variables:
    最高分:
      value: 0
      cloud: true        # ← 云变量
    普通变量: 0           # ← 普通变量
```

也支持完整写法：

```yaml
stage:
  variables:
    最高分: {value: 0, cloud: true}
```

sb3 里编码为 `["最高分", 0, true]`。

**限制**：Scratch 3.0 一个项目最多 **10 个云变量**（编译时会检查并报错）。

**云列表：Scratch 3.0 不支持**。官方 sb3 规范的 list 定义只允许 `[名字, 内容]` 两项，
scratch-vm 也只给标量变量加 `isCloud`。如果写了 `cloud: true` 的列表，
序列化器会打印明确告警并按普通列表生成。需要共享列表时，
用「全局列表 + 云变量存校验/版本号」或「云变量存 JSON 字符串」的组合。

### 2.3 角色的朝向、翻转与多造型

```yaml
sprites:
  - name: 小猫
    x: 0
    y: 0
    size: 100              # 缩放百分比
    direction: 90          # 朝向（90 = 向右；0=上 180=下 负数=左）
    visible: true
    # 旋转风格：all around（整个角色旋转）/ left-right（保持站立，朝左时整个镜像）
    #            / don't rotate（不转不翻）。做人物动物请用 left-right。
    rotationStyle: left-right
    costumes:              # 造型；costumes[0] 是默认造型
      - {name: 猫-右, asset: assets/cat.png}       # 原始
      - {name: 猫-左, asset: assets/cat_left.png}   # --flip-h 生成的镜像
```

- **角色一律用 `rotationStyle: left-right`**：默认的 `all around` 会让角色朝上走时
  整个倒过来。
- **`left-right` 的代价**：`direction < 0` 时渲染器把整个造型水平镜像，
  身上左右不对称的部分（举起的爪子、身上的字、手里的东西）会翻到另一边。
  所以要准备「原图 + 镜像图」两套造型，按朝向切换：
  ```yaml
  - if:
      cond: {less_than: {a: {direction}, b: 0}}
      do:
        - switch_costume: {costume: 猫-左}
      else:
        - switch_costume: {costume: 猫-右}
  ```
- 详见 **`references/sprite-art.md`**。

### 2.4 列表

```yaml
stage:
  lists:
    排行榜: []            # 空列表
    预设: [10, 20, 30]     # 带初始内容
```

### 2.5 屏幕读数（monitors）

Scratch 里勾选「显示变量」会在舞台上出现一个读数。IR 里用 `monitors` 声明：

```yaml
stage:
  variables:
    分数: 0
    剩余时间: 30
  monitors:
    - {var: 分数, x: 8, y: 8}        # 屏幕左上角
    - {var: 剩余时间, x: 130, y: 8}   # 屏幕右上角
    - {list: 排行榜, x: 8, y: 40, visible: false}   # 列表读数（默认隐藏）
```

- `var` / `list` 二选一，必须是**同一个 target 上已声明**的名字，否则编译时报错。
- `x` / `y` 是舞台坐标（0~480 / 0~360），左上角为原点。
- `visible: false` 可以先生成、再在 Scratch 里手动勾上。
- 数值会**实时跟随变量变化**（运行时已验证）。

---

## 3. 脚本（scripts）

一个 target 的 `scripts` 是一个**脚本列表**，每个脚本是一个**积木的平铺列表**，
第一个必须是**帽子积木**（绿旗 / 接收广播 / 按键 / 点击 / 作为克隆体启动 …）。

> **为什么必须是帽子积木**：scratch-vm 的 `runtime.greenFlag()` 只会
> `startHats('event_whenflagclicked')`。顶层放一个裸的 `forever` **不会报错，
> 但永远不会被执行** —— 属于静默失效。本 skill 的 IR 校验会直接拦下这种情况。

```yaml
scripts:
  - - when_green_flag_clicked: null
    - move_steps: 10
    - turn_left: {degrees: 15}
  - - when_receive: 开始
    - say: {text: 出发啦！, secs: 2}
```

可用的帽子积木：

| 帽子 | 积木名 |
|---|---|
| 当绿旗被点击 | `when_green_flag_clicked` |
| 当接收到消息 | `when_receive` |
| 当按下按键 | `when_key_pressed` |
| 当舞台被点击 | `when_stage_clicked` |
| 当角色被点击 | `when_this_sprite_clicked` |
| 当背景切换到 | `when_backdrop_switches_to` |
| 当计时器 > | `when_greater_than` |
| 当作为克隆体启动 | `when_start_as_clone` |

需要「一直重复」的逻辑，就挂在绿旗帽子下面：

```yaml
- - when_green_flag_clicked: null
  - forever:
      do:
        - move_steps: 10
```

### 3.1 积木的写法

每个积木是一个**单键映射** `{ 积木名: 值 }`。积木名可以用：

- 友好名：`move_steps`、`set_variable`、`when_green_flag_clicked` …
- 原始 opcode：`motion_movesteps`、`data_setvariableto` …

完整对照表见 **`references/blocks.md`**（183 个积木全覆盖）。

**多键写法**（YAML 块状风格最自然，推荐）：

```yaml
- forever:
    do:
      - move_steps: 10
- if:
    cond: {less_than: {a: {var: 分数}, b: 10}}
    do:
      - say: {text: 还差一点！, secs: 1}
    else:
      - say: {text: 过关啦！, secs: 1}
```

第一个键是积木名，其余键（`do:` / `else:` / `cond:` …）并入积木的值。
等价于单键写法 `- forever: {do: [...]}`。

> **YAML 注意事项**：YAML 的**流式集合**（`[...]` / `{...}`）内部**不能**用
> `- 条目` 这种块状序列语法。所以要么把整个流式集合写在一行，要么像上面那样
> 改成块状写法。写成 `- repeat: {times: 10, do: [\n  - move_steps: 10\n]}` 会报
> `expected the node content, but found '-'`。

### 3.2 值的写法（按输入类型）

| 输入类型 | 写法 | 例子 |
|---|---|---|
| 无输入 | `null` 或省略 | `{pen_down: null}` |
| 单个输入 | 直接写值 | `{move_steps: 10}` |
| 多个输入 | 字典，键为输入别名 | `{say: {text: 你好, secs: 2}}` |
| 子栈 | `do:`（否则分支 `else:`） | `{repeat: {times: 10, do: [...]}}` |
| 布尔条件 | `cond:` | `{if: {cond: {touching: {object: _mouse_}}, do: [...]}}` |
| 变量读取 | `{var: 名字}` | `{set_variable: {var: 分数, value: {var: 分数}}}` |
| 列表读取 | `{list: 名字}` | `{say: {text: {list: 排行榜}}}` |
| 嵌套表达式 | 递归 | `{turn_left: {degrees: {random: [-15, 15]}}}` |
| 动态下拉菜单 | 字符串 | `{goto: {to: _mouse_}}`、`{switch_costume: {costume: cat1}}` |
| 静态下拉菜单 | 字符串 | `{set_effect: {effect: COLOR, value: 25}}` |
| 广播 | 字符串 | `{broadcast: 开始}`、`{when_receive: 开始}` |
| 自定义积木调用 | `{call: {proc: 名字, args: [...]}}` | |

**输入别名**：`references/blocks-spec.json` 的 `input_aliases` 里为每个积木定义了
更短的键名，例如

- `motion_movesteps`：`steps`
- `looks_sayforsecs`：`text` / `secs`
- `operator_add`：`a` / `b`
- `data_setvariableto`：`value`（也可用 `to`）
- `data_changevariableby`：`value`（也可用 `by`）

同一个输入可能登记了多个别名，**写哪个都行**，序列化器会依次尝试。

查一个积木有哪些输入别名：看 `references/blocks.md` 的「输入」表。

### 3.3 下拉菜单（动态菜单）

「移到 鼠标指针」「碰到 老鼠」「播放 喵」这类下拉，直接写字符串值：

```yaml
- goto: {to: _mouse_}
- point_towards: {towards: _random_}
- touching: {object: 老鼠}
- play_sound: {sound: 喵}
- create_clone_of: {clone: _myself_}
```

序列化器会自动为它们生成 sb3 需要的「影子积木」，
你不需要（也不应该）自己写。

特殊取值：

| 值 | 含义 | 用在 |
|---|---|---|
| `_mouse_` | 鼠标指针 | goto / point_towards / touching |
| `_random_` | 随机位置/方向 | goto / point_towards |
| `_myself_` | 自己 | create_clone_of |
| `_edge_` | 舞台边缘 | touching |
| 角色名 | 某个角色 | touching / goto / play_sound |
| 造型名 | 某个造型 | switch_costume |
| 声音名 | 某个声音 | play_sound |
| 消息名 | 某个广播 | broadcast / when_receive |

**静态下拉**（特效类型、前后方向、音符等）同样写字符串：

```yaml
- set_effect: {effect: COLOR, value: 25}
- goto_front_back: {front_back: front}
```

### 3.4 变量 / 列表积木的特殊写法

变量和列表在 Scratch 里是**下拉字段**而不是普通输入，所以它们的「名字」
要单独给出来：

```yaml
- set_variable: {var: 分数, value: 100}          # ✅
- change_variable: {var: 分数, by: 1}             # ✅
- add_to_list: {list: 排行榜, item: 90}           # ✅
- item_of_list: {list: 排行榜, index: 1}          # ✅
- set_variable: {variable: 分数, value: 100}      # ✅ 也可以用 variable
```

读取变量 / 列表则用 `{var: ...}` / `{list: ...}`：

```yaml
- say: {text: {var: 分数}, secs: 2}
- say: {text: {list: 排行榜}, secs: 2}
```

### 3.5 条件表达式

布尔积木可以直接写在 `cond:` 里，也可以作为普通输入：

```yaml
- if:
    cond: {less_than: {a: {var: 分数}, b: 10}}
    do:
      - say: {text: 还差一点！, secs: 1}
    else:
      - say: {text: 过关啦！, secs: 1}
```

常用比较：`greater_than`、`less_than`、`equals`、`and`、`or`、`not`。
常用侦测布尔：`touching`、`touching_color`、`key_pressed`、`mousedown`。
`touching` / `key_pressed` 等带下拉的侦测积木，参数写成 `{object: ...}` / `{key: ...}`。

---

## 4. 注释与积木整理

### 4.1 注释（comments）

Scratch 的注释是**附在积木上的便签**（不是 YAML 注释）。两种写法：

**① 附着到某个积木**（推荐）—— 在积木的值里加一个 `comment:` 键：

```yaml
scripts:
  - - when_green_flag_clicked:
        comment: 绿旗：重置分数与倒计时，然后广播开始
    - set_variable: {var: 分数, value: 0}
```

> **YAML 写法要注意**：块名后面**不要**带行内值，否则同一层再写 `comment:` 会被 YAML
> 解析成兄弟键（虽然本 skill 也能处理，但可读性差）。推荐写成块状形式：
> 块名单独占一行，缩进一层写 `comment:` 和各个输入。

**② 悬空在画布上**（说明性文字、操作指引）—— 用 target 的 `comments` 列表：

```yaml
stage:
  comments:
    - text: |
        猫抓老鼠 —— 操作说明
        1) 方向键控制猫移动
        2) 每抓住一只 +1 分
      x: 24
      y: 24
      width: 260
      height: 140
```

- `text` 必填（官方上限 8000 字符），支持多行。
- 附着式注释会自动挂到该积木上；悬空注释用 `x`/`y` 指定在画布上的位置。

### 4.2 整理积木（layout）

sb3 里**只有顶层积木带 x/y**（见 scratch-vm `serializeBlock`：只有 `block.topLevel`
才写 x/y），其余积木由编辑器按积木树自动排布。所以「整理积木」就是给顶层脚本
分配互不重叠的位置。

默认行为：序列化器会**自动**把顶层脚本按网格排开（列宽 300px、单列高 620px），
避免在 Scratch 里全部叠在左上角。

```yaml
stage:
  layout:
    mode: tidy            # 默认值
    start_x: 40
    start_y: 40
    col_width: 300
    col_height: 620
```

想自己指定位置就写 `mode: manual`，然后在每个脚本上给 `x` / `y`（IR 暂未支持
逐脚本指定，用 `manual` 意味着你接受默认网格）。

---

## 5. 自定义积木（procedures）
```yaml
procedures:
  - name: 画正方形 %n       # %n 表示数值参数
    args: [边长]
    defaults: [100]
    warp: false             # true = 在 Turbo 模式运行
    script:
      - repeat: {times: 4, do: [
          {move_steps: {var: 边长}},
          {turn_right: 90}
      ]}
```

调用：

```yaml
- call: {proc: 画正方形 %n, args: [100]}
```

规则：

- `args` 里的参数名就是过程体内的变量名，用 `{var: 边长}` 引用。
  （构建器会自动把它编译成 Scratch 的**参数报告器** `argument_reporter_*`——
  Scratch 的过程参数走线程参数栈，只有参数报告器才读得到值，用普通变量读会永远是初值。）
- `name` 里的 `%n` / `%s` / `%b` 依次对应 `args` 的第 1、2、3 个参数。
- ⚠️ **自定义积木是「每个角色一份」**：舞台上定义的过程，别的角色**调用不到**。
  要跨角色共享，把过程建在真正调用它的那个角色上，别的角色用广播请求它算。
- ⚠️ **过程共享全局变量**：过程内部的循环变量**不要与调用方重名**，
  否则会把调用方的索引冲掉（表现为「只写进第 N 格」「循环索引错乱」）。
  给每个过程起专属变量名：`墙序号` / `tile序号` / `clone序号` …

---

## 5.1 三条「静默失效」的硬规则

这三种写法**不报错、构建器也不拦**（除 `if+else` 现在会警告并自动升级），
但运行结果是错的 —— 本 skill 已在构建器里加了防护，但请直接写对。

### ① 带 `else` 的分支必须用 `if_else`

```yaml
# ❌ else 会被静默丢弃：control_if 只有 SUBSTACK 一个子栈槽位
- if: {cond: C, do: [A], else: [B]}

# ✅
- if_else: {cond: C, do: [A], else: [B]}
```

### ② Scratch 3 没有 `atan2`，也没有 `>=` / `<=`、没有 reporter 级 if/else

scratch-vm 只实现了这些运算积木：
`add / subtract / multiply / divide / lt / equals / gt / and / or / not / random /
join / letter_of / length_of / contains / mod / round / mathop`。

- **没有 `operator_atan2`**：写了会**静默返回 0**。角度只能用 `mathop` 的 `atan`
  （**单位是度**）自己拼，或改用**向量 + 叉积**（见 `deep-shadow-raycasting.md`）。
- `mathop` 的 `sin / cos / tan / asin / acos / atan` VM **实现了**，
  但官方编辑器的下拉菜单里只有 `abs / floor / ceiling / sqrt / ln / log / e^ / 10^`。
- `>=` / `<=` 要写成 `not(<)` / `not(>)`。
- 值级的三目必须包成**自定义积木**（过程体里用语句 + 全局变量把结果带出来）。

### ③ 列表是 1 基的

`item_of_list` / `replace_item_of_list` 的 `index` 从 **1** 开始；
扁平地图的索引公式是 `行 × 宽 + 列 + 1`。
- 过程体是积木的平铺列表，**不需要**帽子积木。

---

## 6. 素材引用

```yaml
costumes:
  - {name: cat1, asset: assets/cat.svg}
sounds:
  - {name: meow, asset: assets/meow.wav}
```

- `asset` 是相对路径，相对基准是 **IR 文件所在目录**
  （可用 `--assets-src` 覆盖）。
- 扩展名决定类型：`.svg` / `.png` / `.jpg` 是造型，`.wav` / `.mp3` 是声音。
- 图片建议先跑一遍 `scripts/prep_asset.py` 整理尺寸（舞台 480×360）。

---

## 7. 完整示例

见 `examples/` 目录：

| 文件 | 演示内容 |
|---|---|
| `cat_chase.json` | 运动、外观、画笔、广播、变量 |
| `cat_chase.yaml` | 同上，YAML 写法 |
| `cat_chase_ascii.json` | 纯 ASCII 变量名（兼容性测试） |
| `example_lists.json` | 列表的增删查改 |
| `example_clones.json` | 克隆体 |
| `example_procedures.json` | 自定义积木 |
| `example_operators_sensing.json` | 运算与侦测 |
| `example_pen_sound.json` | 画笔 + 声音 |
| `example_cloud.json` | **云变量** + 全局变量作用域 |
| `example_with_bg.json` | 带生成背景图的作品 |

---

## 8. 校验

编译前会做 IR 结构校验（积木名是否存在、脚本是否以帽子积木开头、
云变量是否超限、是否缺少造型），编译后：

```bash
python3 scripts/validate_sb3.py --sb3 作品.sb3
```

依次执行：

1. **结构与编码检查** —— ZIP/project.json/资产 MD5、积木 opcode 合法性、
   输入数组形态、变量是否被二次编码、字段是否放对位置、云变量数量。
2. **官方 JSON Schema 校验** —— 用 `scratch-parser` 的 `sb3_schema.json` 校验。
3. **scratch-vm 运行时校验** —— 真正加载项目、绿旗启动、步进 60 帧、停止。
   无异常才算通过。

还可以做**行为冒烟测试**（脚本真的跑起来，检查变量/位置是否按预期变化）：

```bash
node scripts/smoke_test.mjs 作品.sb3 --seconds 3
node scripts/smoke_test.mjs 作品.sb3 --seconds 4 --catch   # 额外模拟「碰撞」
```

> 注意：Scratch 的 `等待` 积木用的是**真实时钟**，所以冒烟测试按真实时间推进
> （`--seconds`），不是按帧数。
