# 素材生成与使用指南

本 skill 让 agent 在生成 Scratch 作品时，拥有**生成图片（背景/角色）**与**生成音频（音效/音乐）**
的能力。素材最终通过 IR 的 `asset` 字段引用，由 `build_sb3.py` 计算 MD5 并打包进 `.sb3`。

---

## 一、图片素材（背景 / 角色）

### 1. 生成图片（**默认最高质量，不得自行降级**）

> ## 🔒 默认最高质量（用户显式要求）
>
> **除非用户明确要求更低质量 / 更快出图，一律用最高质量生图。**
> - 用户**没提**画质要求 → 按本节的最高质量默认参数走。
> - **不得**因为省时间、省积分、赶进度、图多而自行降 `quality` 或缩 `size`。
> - 只有用户明确说「随便出一张」「要快」「低质量就行」「先出个草稿」等，才允许降级；
>   降级时要在回复里说明「本次用的是低质量」。
> - 不确定用户意图时，**按最高质量执行**，不要反问要不要降级。

**默认调用模板（直接复制，别省参数）**

```
背景图：
  prompt : <场景描述> + 下方「背景提示词模板」的画质后缀
  size   : "1536x1024"
  quality: "high"

角色图：
  prompt : <角色描述> + 下方「角色提示词模板」的画质后缀
  size   : "1024x1024"
  quality: "high"
  background: "transparent"   # 尝试一下；本机实测不生效，仍需 --remove-bg
  footnote  : 不传 / 留空      # 尝试一下；实测挡不住水印，仍需后处理
```

> 生成前先告知用户：图像生成会**额外消耗积分**（约 5–10 积分/张）。
> 这是消耗告知，**不是**请求用户批准降级 —— 默认仍按最高质量出图。

用 **ImageGen** 生成 PNG。参数含义与实测结论：

| 参数 | 背景图 | 角色图 | 为什么 |
| --- | --- | --- | --- |
| `quality` | **`high`** | **`high`** | 默认档细节明显不足，缩小后更糊；**实测 high 档线条与材质提升明显** |
| `size` | `1536x1024`（横版 3:2） | `1024x1024` | 先出大图再缩，比直接出小图清晰得多 |
| `background` | `opaque` | 可尝试 `transparent` | **⚠ 实测本环境该参数不生效**，输出仍是 RGB 无 alpha → 见下方说明 |
| `footnote` | 不传 / 留空 | 不传 / 留空 | **⚠ 实测无法阻止水印**，工具会在右下角强制加标记 → 见下方说明 |

### 1.0 两个实测坑（2026-11-04 验证，别再踩）

1. **`background: transparent` 不生效**：即使传了，ImageGen 输出的仍是 RGB、
   带浅灰棋盘格底，**没有 alpha 通道**。所以角色图**照旧要跑 `--remove-bg`**。
   别把「不抠图」写进流程，否则 Scratch 里会出现灰方块底。
2. **右下角水印无法通过参数关闭**：`footnote` 留空也照盖不误。所幸有两条补救：
   - **角色图**：水印是浅灰色、与边缘浅色背景连通 → `--remove-bg` 的连通域扩散
     会把水印和背景**一起抠掉**（实测有效）。
   - **背景图**（不抠背景）：水印会保留 → 用 **`--crop-watermark`**
     裁掉右下角 14%×12% 再裁填，构图损失很小。

> `quality: high` + 大 `size` 是这两条里唯一「纯赚」的参数：**能传就一定要传**。
> 后期处理（抠图、锐化）只能补救，救不回生成时就没画出来的细节。

**背景提示词模板**（横版场景，不要人物特写）：

```
<场景描述>, wide establishing shot, children's picture-book illustration,
clean crisp line art, smooth flat color with subtle gradient shading,
soft even lighting, high detail, sharp focus, no text, no watermark, no border
```

**角色提示词模板**（`sprite-art.md` 有完整版）：

```
<角色描述>, single character, full body, centered,
simple flat vector illustration, bold clean outlines, crisp edges,
high detail, sharp focus, isolated on transparent background,
no shadow, no ground, no text, no watermark
```

**画质关键词不能省**：`crisp edges` / `sharp focus` / `high detail` / `no watermark` /
`clean line art`。少了它们，模型倾向于出柔焦、带噪点、边缘发灰的图。

> 生成后把文件保存到 IR 同级的 `assets/` 目录（例如 `assets/hero.png`）。
> **保留原始大图**（`hero_raw.png`），只把整理后的 `hero.png` 写进 IR ——
> 以后要放大显示或换尺寸时能从原图重新导出，不用二次放大糊图。

### 2. 整理为标准尺寸（强烈推荐）
Scratch 舞台是 **480×360**。直接用任意尺寸图片做背景会出现黑边或错位；角色图片过大
也会拖慢编辑器。用 `scripts/prep_asset.py` 统一处理：

```bash
# 背景：裁剪填充到 480×360（铺满，多余部分裁掉）
python3 scripts/prep_asset.py --in assets/hero_raw.png --out assets/hero.png --mode stage

# 背景：等比缩放并居中留白到 480×360（不裁剪，留透明边）
python3 scripts/prep_asset.py --in assets/hero_raw.png --out assets/hero.png --mode stage --no-fill

# 角色：保持比例，最长边限制在 480（默认不缩放，仅当超过时缩小）
python3 scripts/prep_asset.py --in assets/cat_raw.png --out assets/cat.png --mode sprite --max 480

# 自定义尺寸
python3 scripts/prep_asset.py --in a.png --out b.png --width 200 --height 200 --fill
```

参数说明：
- `--mode stage`：目标 480×360（可用 `--width/--height` 覆盖）。
- `--mode sprite`：保持原始比例；`--max N` 限制最长边。
- `--fill`：裁剪填充（铺满目标框）；不加则等比留白。
- `--remove-bg`：抠掉浅色背景（见下）。
- `--trim`：抠完后裁掉四周透明区域。
- `--flip-h`：**水平镜像**，用于生成「朝左」那套造型（见 `sprite-art.md`）。
- `--check-alpha`：检查背景是否真透明并打印结论。
- **`--hq`**：画质组合（= `--defringe --sharpen`），**AI 生成图建议常开**。
  - `--defringe`：缩放前腐蚀 alpha 1px，去掉抠图残留的白边/灰晕；
    后续 LANCZOS 会重建平滑抗锯齿，不会变锯齿。
  - `--sharpen`：缩放后做轻微 UnsharpMask，补回大图缩小时损失的高频细节。
  - 实测：同一张 1024×1024 猫图缩到 268×300，边缘偏白的脏像素从 66 个降到 2 个。
- **`--crop-watermark`**：裁掉右下角水印区（右侧 14% / 底部 12%）。
  仅用于**不抠背景的背景图**；角色图靠 `--remove-bg` 就能顺带去掉水印。
- 依赖 Pillow：`python3 -m pip install -i https://pypi.org/simple Pillow`。

### 2.1 抠掉 AI 生成图的「棋盘格底」（重要）

很多 AI 生成的图片**没有真正的 alpha 通道**，而是画了一层浅灰棋盘格。
直接塞进 Scratch，角色周围会出现一个明显的灰色方块。

`prep_asset.py` 的 `--remove-bg` 会把「亮且低饱和」且**与图片边缘连通**的像素抠成透明，
因此角色身上的白色肚子、白爪子不会被误删：

```bash
python3 scripts/prep_asset.py --in assets/cat_raw.png --out assets/cat.png \
    --mode sprite --max 300 --remove-bg --trim
```

- `--remove-bg`：抠背景（连通域扩散，只抠与边缘相连的浅色区域）。
- `--trim`：抠完后裁掉四周透明区域，让角色填满造型框（Scratch 的旋转中心取图片中心）。
- `--bg-brightness` / `--bg-saturation`：背景判定阈值（默认 175 / 30），
  背景不是浅色时调大 `--bg-brightness` 会更容易误抠，必要时手工调。
- `--check-alpha`：自检。会打印不透明像素占比与边缘是否透明，
  若报「边缘仍有不透明像素」说明抠图没成功（Scratch 里会看到灰方块底）。

### 2.2 角色的朝向与镜像造型

角色在 Scratch 里默认「整个旋转」（朝上走会头朝下），
改成 `rotationStyle: left-right` 才能保持站立 —— 但那样朝左时**整个造型会被镜像**。
完整解法（两套造型 + 按朝向切换）见 **`references/sprite-art.md`**。

生成镜像造型：

```bash
python3 scripts/prep_asset.py --in assets/cat.png --out assets/cat_left.png \
    --mode sprite --flip-h
```

### 3. 在 IR 中引用
```yaml
stage:
  backdrops: [ { name: 海底, asset: assets/hero.png } ]
sprites:
  - name: 小猫
    costumes: [ { name: cat1, asset: assets/cat.png } ]
```
`asset` 路径相对于 **IR 文件所在目录**（默认 `assets-src`）。序列化器会读取文件、算 MD5、
写入 `assets/<md5>.<ext>` 并填好 `md5ext` 与 `rotationCenter`。

### 4. SVG 角色（可选）
角色也可以用 SVG（矢量）。直接把 `.svg` 作为 `asset` 即可；序列化器会从 `viewBox`/宽高
读尺寸并设旋转中心。适合需要清晰缩放的几何形象。

---

## 二、音频素材（音效 / 音乐）

> **路线已定：音频全部由 agent 本地生成，不接入任何外部 TTS / 音乐 API。**
> `scripts/gen_audio.py` 用 Python 标准库离线合成，无第三方依赖、无网络调用、
> 无密钥管理，产物是 Scratch 可直接使用的合法 WAV。

### 1. 命令一览

```bash
python3 scripts/gen_audio.py list                     # 列出全部预设

# 音效预设（游戏里最常用的一批）
python3 scripts/gen_audio.py sfx --name coin    --out assets/coin.wav
python3 scripts/gen_audio.py sfx --name pop     --out assets/pop.wav
python3 scripts/gen_audio.py sfx --name hit     --out assets/hit.wav
python3 scripts/gen_audio.py sfx --name jump    --out assets/jump.wav
python3 scripts/gen_audio.py sfx --name swoosh  --out assets/swoosh.wav
python3 scripts/gen_audio.py sfx --name laser   --out assets/laser.wav
python3 scripts/gen_audio.py sfx --name powerup --out assets/powerup.wav
python3 scripts/gen_audio.py sfx --name explosion --out assets/boom.wav
python3 scripts/gen_audio.py sfx --name win     --out assets/win.wav
python3 scripts/gen_audio.py sfx --name lose    --out assets/lose.wav

# 程序化背景音乐（无缝循环）
python3 scripts/gen_audio.py bgm --mood chase  --bars 4 --out assets/bgm.wav
python3 scripts/gen_audio.py bgm --mood happy  --bars 2 --out assets/happy.wav
python3 scripts/gen_audio.py bgm --mood spooky --bars 2 --out assets/spooky.wav

# 自由组合
python3 scripts/gen_audio.py tone   --freq 440 --dur 0.2 --wave square --out assets/beep.wav
python3 scripts/gen_audio.py sweep  --from-freq 900 --to-freq 300 --dur 0.15 --out assets/whoosh.wav
python3 scripts/gen_audio.py melody --notes "C4:1 E4:1 G4:2" --dur 0.2 --out assets/jingle.wav
python3 scripts/gen_audio.py noise  --dur 0.12 --out assets/hit.wav
```

### 2. 音效预设（17 个）

| 类别 | 预设 | 说明 |
|---|---|---|
| 反馈 | `pop` `click` `blip` `error` | 短促提示音、报错音 |
| 收集 | `coin` `powerup` `sparkle` | 得分、升级、闪光 |
| 动作 | `jump` `boing` `footstep` `swoosh` `whoosh` | 移动类 |
| 战斗 | `hit` `laser` `explosion` | 打击、射击、爆炸 |
| 结算 | `win` `lose` | 胜负面 |

### 3. BGM 情绪（7 种）

`happy`（轻快）、`chase`（追逐）、`spooky`（诡异）、`calm`（舒缓）、
`victory`（胜利）、`defeat`（失败）、`explore`（探索）。

BGM 是**程序化生成**的（旋律音型 + 低音音型），并且做了**无缝循环处理**
（首尾交叉淡化），在 Scratch 里用「播放 声音直到播放完毕」放进 `forever` 即可无缝衔接。

### 4. 音名与波形

- 音名支持升降号：`C4` `D#4` `Eb4` `A#3` `G#4` …
- 波形：`sine` `square` `saw` `tri`（`triangle` 是 `tri` 的别名）
- `melody` 的音符串用逗号**或空格**分隔，冒号后跟拍数：`"C4:1 E4:1 G4:2"`

### 5. 在 IR 中引用

```yaml
sprites:
  - name: 小猫
    sounds:
      - {name: coin, asset: assets/coin.wav}
    scripts:
      - - when_green_flag_clicked: null
        - play_sound: {sound: coin}

stage:
  sounds:
    - {name: 追逐, asset: assets/bgm.wav}
  scripts:
    - - when_green_flag_clicked: null
      - forever:
          do:
            - play_sound_until_done: {sound: 追逐}
```

> 舞台也可以有声音（舞台同样有声音库），把 BGM 放舞台上循环播放最省事。

### 6. 局限（诚实说明）

离线合成只能产出**程序化音效与旋律**，做不到：
- 语音旁白（需要真人录音或 TTS）
- 写实的环境音/乐器音色（真实吉他、钢琴采样）
- 精确复刻某首曲子

如果作品强依赖这些，请告知用户并建议其自行提供音频文件，
放到 `assets/` 后按同样的 `asset:` 字段引用即可。

---

## 三、素材校验要点

- 背景/角色图片必须是可读的 PNG/JPG/SVG；损坏文件会导致打包失败。
- 音频必须是 WAV（或目标环境支持的格式）；`gen_audio.py` 产出标准 WAV。
- 引用路径务必与文件实际位置一致；校验脚本会核对 `assets/` 内 MD5 是否匹配。
- 生成并校验通过（`validate_sb3.py` 全部通过）后，`.sb3` 即可在 Scratch 中正常显示素材。
- **每个 target 至少要有一个造型**：官方 sb3 规范要求 `costumes` 至少 1 项，
  舞台算 1 个 backdrop。没有造型会在加载时被 Schema 拒绝。
- 角色图片建议带真透明通道；拿不到真透明时才用 `--remove-bg --trim --hq` 补救。

---

## 四、画质诊断清单（「AI 图好糊」按这个顺序排查）

| 现象 | 最可能的原因 | 解法 |
| --- | --- | --- |
| 整体发虚、细节糊 | ImageGen 没传 `quality: high`，用了默认档 | 重出图，`quality: high` + `size: 1536x1024` |
| 边缘一圈白/灰光晕 | 抠图二值判定留下的脏边 | `--hq`（内含 `--defringe`） |
| 缩小后线条变软 | 大图→小图的 LANCZOS 高频损失 | `--hq`（内含 `--sharpen`） |
| 右下角有「AI 生成」水印 | 工具强制加，`footnote` 留空也挡不住 | 角色图 `--remove-bg`；背景图 `--crop-watermark` |
| 角色背后有灰白格子方块 | 模型把「透明」画成棋盘格（本机 `background:transparent` 无效） | `--remove-bg --trim --hq` |
| 图放大显示后糊 | 造型实际像素小于 Scratch 里的显示尺寸 | **保留原始大图**，按目标显示尺寸重新导出，不要用小图放大 |
| 画面看着廉价、像占位图 | 用了 `make_ui_assets.py` 的程序化纯色块（1~5KB 的纯色矩形/网格） | 这些是**功能性占位素材**，不是成品美术；正式作品应换成 AI 生成的插画 |

### 硬规则

0. **默认最高质量，不得自行降级**（用户显式要求）：除非用户明确说「要快 / 随便出一张 /
   低质量就行」，否则一律 `quality: high` + 大 `size`。**不得因为省积分、图多、赶进度降级**；
   不确定就按最高质量执行，不要反问要不要降级。降级时需在回复中说明。
1. **`quality: high` + 大 `size` 优先于一切后期**：比任何锐化都有效。
   后期处理只能补救，救不回生成时就没画出来的细节。
2. **永远保留原图**（`*_raw.png`）。Scratch 舞台只有 480×360，但角色可能要放大、
   或者以后换高清舞台，从 1024/1536 原图重导才有余量。
3. **缩小一次就好**。原图 → 目标尺寸，一步到位；反复「缩小→放大→再缩小」会累积糊化。
4. **换首页背景时别忘了标题文字**。`title_screen` 只提供 `backdrop` + `button`，
   **没有单独的标题角色** —— 旧版 `make_ui_assets.py` 的首页图把「猫抓老鼠」和
   操作提示**烧在背景里**。换成 AI 插画后这些文字会整体消失。
   换图后必须用 PIL 在背景上叠回标题（半透明底板 + 深色字 + 白色描边，
   按钮区域 `y≈265~315` 保持留空）。`deploy-tools/regen_assets.py` 的
   `overlay_title()` 是可复用的实现。

> 关于「程序化 UI 素材」：`make_ui_assets.py` 输出的数字牌、按钮、聊天框、
> 大地图网格是为**示教与校验**服务的，刻意做成简洁纯色块。
> 它们不该被当成成品美术 —— 用户要「好看的作品」时，
> 背景、角色、主要 UI 都应走 ImageGen + `prep_asset.py --hq` 这条链路。

