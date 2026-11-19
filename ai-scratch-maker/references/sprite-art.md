# 角色美术规范（造型 / 背景 / 翻转）

本文件讲**角色（sprite）在 Scratch 里怎么摆才不难看**。三个高频坑：

1. **背景不干净** —— 角色四周有个灰方块底。
2. **整个角色倒过来** —— 角色朝上走时头朝下；或者朝左时整张图被镜像，
   举起的爪子、身上的字、拿的东西全翻到了另一边。
3. **只有一个造型** —— 需要多套造型（走路、受伤、变装、朝左/朝右）时没有得用。

---

## 1. 角色背景：必须真透明

Scratch 的造型是**整张 PNG**，不是「主体 + 抠图」。
只要 PNG 里有任何不透明像素，Scratch 就会照原样画出来 —— 角色背后会浮一个方块。

AI 生成的图尤其容易踩：模型常把「透明背景」画成**浅灰棋盘格**，
PNG 里**根本没有 alpha 通道**，肉眼看是透明的，导入 Scratch 却是灰格子。

### 1.1 生成时的提示词

> 🔒 **默认最高质量**：除非用户明确要求更低质量 / 更快出图，
> 角色图一律 `quality: high` + `size: 1024x1024`，不得自行降级。
> 完整默认模板与例外条件见 `asset-guide.md` §一.1。

先用 **ImageGen 参数**把画质底子打好（这比事后锐化有效得多）：

| 参数 | 值 | 说明 |
| --- | --- | --- |
| `quality` | **`high`**（默认，不可省略） | **实测有效**：默认档线条发虚、缩小后更糊 |
| `size` | **`1024x1024`**（默认，不可省略） | 先出大图，再缩到 Scratch 需要的尺寸 |
| `background` | 可尝试 `transparent` | **⚠ 本机实测不生效**，输出仍是 RGB 无 alpha |
| `footnote` | 留空 | **⚠ 挡不住右下角强制水印**，靠后处理去掉 |

```
<角色描述>, single character, full body, centered,
simple flat vector illustration style, bold clean outlines, crisp edges,
high detail, sharp focus, clean line art, no grain, no watermark,
isolated on transparent background, no shadow, no ground, no text
```

关键三句：`isolated on transparent background`、`no ground`、`no shadow`。
画质四句：`crisp edges`、`sharp focus`、`clean line art`、`no grain`。

### 1.0 别指望「真透明」参数，抠图仍是必需步骤

实测（2026-11-04）：传 `background: transparent` 后，ImageGen 输出的**仍是 RGB 图，
没有 alpha 通道**，背景是浅灰棋盘格。所以角色图**必须跑 `--remove-bg`**，
否则 Scratch 里会出现灰方块底。

好消息是：工具在右下角强制盖的浅灰水印，与边缘浅色背景连通，
`--remove-bg` 的连通域扩散会把**水印和背景一起抠掉**（实测有效，见 `asset-guide.md` §一.0）。
背景图不抠背景，水印需另用 `--crop-watermark` 裁掉。

`--remove-bg` 是「亮且低饱和 + 连通域」的二值判定，会把边缘像素硬切成
全透明/全不透明，缩小后容易出现白边、锯齿和灰晕 —— 所以抠完要接
`--trim --hq`（`--hq` 内的 `--defringe` 专治白边），再跑 `--check-alpha` 自检。

### 1.2 处理与自检

```bash
# 抠掉浅色背景 + 裁掉透明边 + 自检背景是否干净
python3 scripts/prep_asset.py --in assets/cat_raw.png --out assets/cat.png \
    --mode sprite --max 300 --remove-bg --trim --check-alpha
```

`--check-alpha` 会打印并判定：

```
[cat.png] 尺寸=268x300 不透明像素=57.3% 边缘不透明=0/1136
[ok] 背景干净（四边全透明）
```

如果报 `[!] 角色四周仍有不透明像素`，说明抠图没成功：

- 背景不是浅色 → 调大 `--bg-brightness`（默认 175）会让更多像素被判为背景，
  调**小**它反而更保守；两个参数一起试。
- 背景是渐变/复杂场景 → `--remove-bg` 不适用，改用「重新生成时要求纯色底」，
  或者让 ImageGen 出一张「纯白底」的图再抠。

### 1.3 舞台背景是另一回事

舞台的 `backdrops` 本来就是**不透明**的整幅画（480×360），**不要**抠背景：

```bash
python3 scripts/prep_asset.py --in assets/bg_raw.png --out assets/bg.png --mode stage --fill
```

---

## 2. 「倒过来」：三种旋转风格

scratch-vm 的 `RenderedTarget._getRenderedDirectionAndScale()` 决定了实际怎么画：

| `rotationStyle` | 行为 | 适合 |
|---|---|---|
| `all around`（Scratch 默认） | 角色**整个旋转**：朝上走就是头朝下 | 球、纸片、旋转物体 |
| `left-right` | 渲染方向强制为 90（**始终站立**），但 `direction < 0` 时**整个造型水平镜像** | **人物、动物** |
| `don't rotate` | 不转也不翻 | 按钮、图标、UI |

### 2.1 人物/动物一律用 `left-right`

`all around` 下，一只猫朝上走会变成「倒着爬」—— 这是最常见的「角色看起来坏了」的原因。

```yaml
sprites:
  - name: 猫
    rotationStyle: left-right
```

IR 里不写 `rotationStyle` 时默认是 `all around`（与 Scratch 一致），
**做角色时请显式写上 `left-right`**。

### 2.2 `left-right` 的副作用：整个造型被镜像

`direction < 0` 时渲染器把整个 drawable 的 `scale.x` 取 `-1`，
于是**造型里所有左右不对称的东西都被翻到另一边**：

- 举起的左手爪 → 变成举起的右手爪
- 身上的文字 → 变成镜像的乱码
- 手里拿的球 / 背包 → 换到另一边

### 2.3 标准解法：两套造型 + 按朝向切换

准备「原图」和「原图的水平镜像」两套造型，朝左时切到镜像那套。
这样朝向由美术决定，不会出现镜像乱码或左右颠倒的肢体。

**生成镜像造型**：

```bash
python3 scripts/prep_asset.py --in assets/cat.png --out assets/cat_left.png \
    --mode sprite --flip-h
```

镜像不会改变图片尺寸，旋转中心仍是 `(宽/2, 高/2)`，所以两套造型的站位一致。

**IR 里登记两套造型**：

```yaml
sprites:
  - name: 猫
    rotationStyle: left-right
    costumes:
      - {name: 猫-右, asset: assets/cat.png}        # 原始
      - {name: 猫-左, asset: assets/cat_left.png}    # 水平镜像
```

**按朝向切换**（每帧检查一次方向）：

```yaml
- if:
    cond: {less_than: {a: {direction}, b: 0}}   # direction < 0 即朝左
    do:
      - switch_costume: {costume: 猫-左}
    else:
      - switch_costume: {costume: 猫-右}
```

> `motion_direction`（友好名 `direction`）返回角色当前的朝向值：
> 0=上、90=右、180=下、-90/-104…=左（Scratch 把 -179~180 之间都算「朝左」）。

### 2.4 什么时候**不用**两套造型

- 角色左右对称（正面站姿的吉祥物、大部分 Q 版角色）→ 单造型 + `left-right` 即可。
- 角色本来就该整体旋转（纸飞机、齿轮）→ 用 `all around`，不需要镜像造型。

---

## 3. 生成造型（多造型）

### 3.1 IR 里一个角色可以有多个造型

```yaml
sprites:
  - name: 猫
    rotationStyle: left-right
    costumes:
      - {name: 猫-右,   asset: assets/cat.png}
      - {name: 猫-左,   asset: assets/cat_left.png}   # 镜像
      - {name: 猫-抓,  asset: assets/cat_catch.png}   # 抓到时的表情
    scripts:
      - - when_green_flag_clicked: null
        - switch_costume: {costume: 猫-右}
```

- `costumes[0]` 是**默认造型**（游戏开始时的样子）。
- `currentCostume` 默认是 0，所以第一个造型要放默认状态。
- 切换用 `looks_switchcostumeto`（友好名 `switch_costume`），
  它的 `COSTUME` 是**动态下拉菜单**，写造型名字即可。

### 3.2 常用造型组合

| 需求 | 做法 |
|---|---|
| 朝左/朝右 | 原图 + `--flip-h` 镜像，按 `direction` 切换 |
| 走路/站立 | 2~4 张循环图，用 `wait` + `switch_costume` 循环 |
| 受伤/正常 | 两套图，受伤时切过去并加特效 |
| 大小变化 | 用 `change size` 而不是换图（更省资产） |
| 变身 | 换整套装扮（每个装扮一套造型组） |

### 3.3 造型切换的常见坑

- **别每帧都切**：Scratch 里频繁 `switch costume` 会打断脚本（造型切换会重启脚本栈）。
  只在**状态真的变了**时切（例如方向改变时）。
- **造型名要唯一**：同名造型在 Scratch 里会混淆，镜像造型建议加 `-左`/`-右` 后缀。
- **镜像造型的旋转中心要一致**：`--flip-h` 天然保持一致；
  手工做镜像时务必保持同样的宽高。

---

## 4. 一份可复用的角色制作流程

```bash
# 1) 生成（提示词里强调 transparent background / no ground）
#    ImageGen -> assets/cat_raw.png

# 2) 抠背景 + 裁边 + 自检
python3 scripts/prep_asset.py --in assets/cat_raw.png --out assets/cat.png \
    --mode sprite --max 300 --remove-bg --trim --check-alpha

# 3) 出镜像造型（左右翻转用）
python3 scripts/prep_asset.py --in assets/cat.png --out assets/cat_left.png \
    --mode sprite --flip-h

# 4) IR 里：rotationStyle: left-right + 两套造型 + 按 direction 切换

# 5) 编译 + 校验
python3 scripts/build_sb3.py --ir examples/cat_mouse.yaml --out 作品.sb3
python3 scripts/validate_sb3.py --sb3 作品.sb3
```

---

## 5. 角色尺寸：必须算清楚

舞台只有 **480×360**。角色太大有两个典型后果：

1. **判定条件恒成立** —— 角色在屏幕中间时，别的角色一出现就「碰到」。
   表现出来就是「猫在屏幕中间一直加分」���— 因为猫的碰撞体把周围全罩住了。
2. 角色几乎占满屏幕，看不见别的角色，也没法走位。

### 换算公式

角色在屏幕上的实际像素 = **原图像素 × size%**。常用角色建议：

| 角色类型 | 原图尺寸 | 建议 size | 屏幕上实际 | 占屏高 |
|---|---|---|---|---|
| 主角（人/动物） | 268×300 | **30~35%** | 80×90 ~ 94×105 | 22~29% |
| 敌对小角色 | 240×240 | **20~25%** | 48×48 ~ 60×60 | 13~17% |
| 收集物/子弹 | 64×64 | 100% | 64×64 | 18% |
| UI 面板 | 300×60 | 100% | 300×60 | 17% |

**经验值：可移动角色在屏幕上占屏高不超过 1/3（约 120px）。**

### 校验器会自动检查

`validate_sb3.py` 会读造型图片的实际像素宽高，换算屏幕占用，
超过 1/3 屏高就给出警告：

```
[warn] 角色 '猫' 在屏幕上约占 46% 屏高（上限 33%）——
       角色太大容易「一出现就碰到」，建议调小 size 或缩小原图
```

### 配套：安全生成点

角色重新出现时，如果落点离玩家太近，会「刚出现就判定被抓」。
用 `safe_spawn` 伪积木保证落点距离：

```yaml
- - when_receive: { message: 重新出现 }
  - safe_spawn: { avoid: 猫, min_distance: 150 }
```

展开成「反复随机落点，直到离 `猫` 的距离 > 150」。

---

## 6. 自查清单

| 检查项 | 怎么看 |
|---|---|
| 背景透明 | `prep_asset.py --check-alpha` 报「四边全透明」 |
| 角色不会倒过来 | IR 里 `rotationStyle: left-right` |
| 左右朝向正确 | 两套造型 + `direction < 0` 切换；冒烟测试会打印「造型=…」 |
| 角色尺寸合理 | 校验器不报「占屏高超过 33%」 |
| 造型齐备 | `costumes` 列表里第一项是默认状态 |
| 运行时没报错 | `validate_sb3.py` 的运行时校验通过 |
