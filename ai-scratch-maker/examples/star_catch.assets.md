# 星空拾贝 · 素材清单与生图提示词

> 由 `new_project.py --genre catch --name 星空拾贝` 生成。
> **这一步不是可选的**：模板 IR 里的素材是占位/示例，直接交付就是「画面糙」的旧样子。
> 逐项用 ImageGen 生成后经 `prep_asset.py` 整理，再写回 IR 的 `asset:`。

## 必须替换的位图（门禁 D 层会查）

规格表要求至少 **3 个被真正引用的位图造型**。
「被引用」指写进 costumes/backdrops 且被 project.json 记录，孤儿素材不算。

| 用途 | 提示词要点 |
|---|---|
| 游戏主场景背景 | 主视觉，横版 4:3，暖色儿童绘本风，中央留活动区，无文字 |
| 主角（接住下落物的角色） | 透明背景 PNG，圆润带描边，高度≤舞台 1/3，四方向可辨识，无文字 |
| 下落物 / 收集物 | 透明背景 PNG，同上画风，轮廓与主角明显区分，无文字 |
| 首页背景 | 与 游戏主场景背景 同场景，中央大面积留白给标题，无文字 |
| 开始按钮 | 圆角窗口 + 五层体积感，单独 PNG，无文字（文案用角色） |
| 结算页 | 与首页同系列，留出「再来一局 / 返回」按钮位置，无文字 |

### 统一画风约束（每张图都要遵守）

- **风格统一**：同一作品所有素材用同一种画风（儿童绘本厚涂 / 柔和水彩 / 扁平矢量三选一），
  暖色为主、柔和光照、圆润造型，避免写实照片与卡通混搭。
- **禁用配色**：冷灰（B 明显 > R 且 R≈G）、深绿 `#216E09` / 深蓝绿 `#2F7365` 做填充。
  取 §198 的 18 色 HEX 色板；颜色字面量一律 6 位 `#rrggbb`。
- **画面里不要任何文字**：Scratch 造型里写字会因字体缺失/缩放糊掉（铁律17）。
  标题、分数、按钮文案一律由独立角色或 UI 面板承担。
- **背景**：横版 4:3，主体留中央安全区，四周留出 UI 与角色活动空间，不要填满细节。
- **角色**：透明背景 PNG，角色高度约为舞台的 1/3，轮廓清晰、带描边，方便做挤压拉伸。
- **按钮/面板**：窗口圆角 + 五层体积感（投影→外描边→渐变→顶高光→底内阴），
  Scratch 无九宫格，面板请按目标尺寸直接出图。
- 生成后一律走 `scripts/prep_asset.py` 整理尺寸，再写回 IR 的 `asset:`。

## 模板 IR 当前引用的素材

- 位图 8 个、矢量 0 个、音频 6 个、社区素材 15 个。

```
  assets/ui/title_bg.png
  assets/ui/btn_start.png
  游戏场景
  community:fSS6J66J/backdrop1
  community:2SwJJ66J/金钥匙#2
  community:NGwJJ66J/pop#2
  assets/sfx/ev_levelup.wav
  assets/sfx/ev_win.wav
  assets/sfx/ev_lose.wav
  assets/sfx/ev_alarm.wav
  assets/sfx/ui_click.wav
  assets/sfx/fx_hit.wav
  assets/ui/basket.png
  community:2SwJJ66J/体力果
  community:2SwJJ66J/金钥匙
  community:bkiJJ66J/costume2
  community:2SwJJ66J/魔法汤
  community:fSS6J66J/造型1
  community:fSS6J66J/造型2
  community:hKS6J66J/造型1
  community:bkiJJ66J/costume3
  assets/ui/win.png
  assets/ui/lose.png
  assets/ui/btn_restart.png
  assets/ui/plus1.png
  assets/ui/levelup.png
  community:3AwJJ66J/0!!
  community:3AwJJ66J/1!!
  community:3AwJJ66J/9!!
  community:3AwJJ66J/4!!
```

## 音效（四层响度，铁律18）

ui 点击 ≤0.25s / fx 反馈 -9dBFS / ev 胜负 -3dBFS / amb 背景 -15dBFS；
首尾归零、DC<0.01、UI 音禁用「播放声音直到结束」。
可直接复用 `scripts/gen_sfx_kit.py` 的 22 个预设，但**至少替换 1~2 个为主题专属音**。

## 替换后的验收命令

```bash
python scripts/build_sb3.py --ir examples/star_catch.yaml --out examples/output/star_catch.sb3 --workdir <临时目录>
python scripts/quality_gate.py --sb3 examples/output/star_catch.sb3 --spec examples/star_catch.quality.json --strict
bash scripts/verify_project.sh --only-advisory   # 秒级看性能/可访问性建议
```

> 交付前还要逐条过 `references/self-review.md` 的 9 类软性自查，
> 以及 `scripts/verify_project.sh` 全量回归。
