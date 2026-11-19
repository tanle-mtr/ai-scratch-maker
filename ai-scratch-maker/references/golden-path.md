# 黄金路径（默认链路）· 端到端做一件高质量 Scratch 作品

> 本文是 `SKILL.md` 工作流程的**可复现范例**。它把「标准 6 步 + 八层校验 + 质量门禁」
> 串成一条能直接抄命令跑通的链路，并以 `examples/fruit_basket.yaml`（接水果游戏）为样例，
> 给出每一步的真实产物与校验结果。**照着跑，就能产出一件通过质量门禁的真·完整作品。**
>
> **第二范例（打地鼠）**：`examples/whack_a_mole.yaml`（21 角色 / 525 积木 / 9/9 优秀），
> 机制更偏「手感打磨」（缓动升降、命中顿帧、震屏、粒子、连击、升关），并自带深网探针
> `scripts/whack_a_mole_behavior_check.mjs`（`WHACK_LOGIC_OK`）。**创作侧方法论**（如何从零
> 想题材、凑资产、写 IR、过校验）见 `references/creation-playbook.md`——验收侧门禁齐全后，
> 创作侧才是「能做高质量作品」的真正瓶颈。

---

## 0. 一句话链路

```
设计定规格 → 写 IR → 生成素材 → 编译成 .sb3 → 八层结构校验 → 质量门禁（A+B 层）
```

- 默认链路**强制素材**：以前素材是可选项，导致 82% 的示例零音效、造型中位 2–4 个。
  现在第 1 步先定规格表、第 3 步按规格表凑够资产密度，作品才不会「能打开但不像作品」。

> **全链路一键验收**：写完作品后，一条命令跑完「全量构建 → 八层校验 → 9 条铁律检查 →
> L7 语义回归 → 全量启动冒烟 + 23 个作品行为回归 → 质量门禁」，给出统一 PASS/FAIL：
> ```bash
> bash scripts/verify_project.sh                 # 全链路（约 12+ 分钟，含行为回归）
> bash scripts/verify_project.sh --skip-regress   # 只跑前 5 阶段（不含 12 分钟行为回归）
> bash scripts/verify_project.sh --jobs 4         # 行为回归并行提速（失败自动重试甄别假红）
> ```
> 各阶段脚本：结构校验 `validate_sb3.py` / `validate_schema.mjs` / `validate_parser.mjs` /
> `validate_runtime.mjs`；铁律 `check_hard_rules.mjs`；语义 `semantic_check.py`；
> 启动冒烟 `boot_smoke_check.mjs`；行为回归 `regress_behavior.sh`；质量门禁 `quality_gate.py`。

- 所有命令都在 **skill 根目录**下执行（SKILL.md 所在目录），用相对路径 `scripts/xxx`。
  Windows 上用 `python`（不是 `python3`）；本文明示 `python3` 处请自行替换。

---

## 1. 六步工作流（与 SKILL.md 对齐）

| 步 | 动作 | 关键产物 / 命令 |
|---|---|---|
| 1 | 设计 + 定规格 | `python scripts/quality_gate.py --init --profile game --out <作品>.quality.json` |
| 2 | 写 IR（YAML） | `<作品>.yaml`，每个脚本以帽子积木开头、加 `comment:` |
| 3 | 生成素材（必选） | 查社区包 / ImageGen 出 PNG / `gen_audio.py`、`gen_sfx_kit.py`、`make_ui_assets.py` |
| 4 | 编译 | `python3 scripts/build_sb3.py --ir <作品>.yaml --out <作品>.sb3 --workdir <tmp>` |
| 5 | 结构校验 | `validate_sb3.py` + schema/parser/runtime/smoke（见 §3 八层表） |
| 6 | 质量门禁 | `python scripts/quality_gate.py --sb3 <作品>.sb3 --spec <作品>.quality.json --strict` |

> **第 3 步是默认链路的关键。** 先有规格表（要几个造型、几个音效、多大体积），
> 再去生成/查素材凑够，而不是写完 IR 才发现资产密度不够、前七层全过却不像作品。

---

## 2. 端到端复现：接水果（fruit_basket）

下面是从零复现 `examples/fruit_basket.sb3` 的完整命令。它在 dev 副本
`ai-scratch-maker/` 下已跑通，可作为你自己作品的模板。

### 2.1 定规格（第 1 步）

```bash
cd ai-scratch-maker            # skill 根目录
python3 scripts/quality_gate.py --init --profile game \
        --out examples/fruit_basket.quality.json
```

>`game` 档默认 `bytes ≥ 1MB` 是为**栅格重美术（PNG/照片素材）**校准的。
>矢量化（SVG）+ WAV 的游戏真实素材约 600–700KB 就已是完整作品，因此本样例把
>`min_bytes` 手改为 `400000`（只动这一项，其余 game 门槛全保留），详见 §4.3。

### 2.2 写 IR（第 2 步）

成品：`examples/fruit_basket.yaml`（约 370 行）。结构要点：

- `project.title_screen`：标题页（背景 + 开始按钮），点开始广播 `开始游戏`。
- `stage`：2 个背景、7 个变量（分数/生命/关卡/过关目标/游戏状态/下落速度/音效开 + 低血告警）、
  3 个监视器、BGM 常驻循环、过关/通关/失败音效路由、低血告警。
- 角色：挡板（方向键+鼠标控制）、水果（8 造型克隆下落、接住计分、漏接扣血）、
  结算页（胜利/失败两态）、再来一局（点击+空格重开，**铁律 7**）、加分散字、过关飘字、背景装饰。

### 2.3 生成素材（第 3 步）

```bash
# 22 个音效（ui/fx/ev/amb 四层响度），进 examples/assets/sfx/，含 manifest.json
python3 scripts/gen_sfx_kit.py --out examples/assets/sfx

# UI 面板（标题背景、按钮、篮子、胜负页、重开按钮、+1、过关！）
python3 scripts/make_ui_assets.py panel --text "+1"  --out examples/assets/ui/plus1.png
python3 scripts/make_ui_assets.py panel --text "过关！" --out examples/assets/ui/levelup.png
# title_bg / btn_start / basket / win / lose / btn_restart 由同一脚本的其它子命令生成

# 社区素材：直接写 asset: "community:<id>"，构建前自动展开（见 §5 全新环境安全网）
```

> **资产解析规则**：IR 里 `asset:` 的相对路径是**相对于 IR 文件所在目录**解析的。
> 本样例 IR 在 `examples/`，所以 `assets/ui/basket.png` 实际指向
> `examples/assets/ui/basket.png`。把素材放在 IR 同级的 `assets/` 下即可自包含。

### 2.4 编译（第 4 步）

```bash
python3 scripts/build_sb3.py --ir examples/fruit_basket.yaml \
        --out examples/output/fruit_basket.sb3 --workdir /tmp/fb_work
```

构建前会做 IR 校验（积木名、帽子开头、变量/广播、造型齐备、云变量）。
本样例构建输出：`targets=9 blocks=244 extensions=[]`，产物 **674 KB**。

> **必须带 `--workdir`**：不带会在 CWD 留下 `_proj` 临时目录；显式给临时目录更干净。

### 2.5 八层结构校验（第 5 步）

```bash
SB3=examples/output/fruit_basket.sb3
# 第 2/4 层要解压后的 project.json：
python3 -c "import zipfile;zipfile.ZipFile('$SB3').extract('project.json','examples/output/_extract')"

python3 scripts/validate_sb3.py      --sb3 "$SB3"                 # L1 全部校验通过 ✅
node    scripts/validate_schema.mjs   examples/output/_extract/project.json   # L2 SCHEMA_OK
node    scripts/validate_parser.mjs   "$SB3"                       # L3 PARSER_OK
node    scripts/validate_runtime.mjs  examples/output/_extract/project.json   # L4 RUNTIME_OK
node    scripts/smoke_test.mjs        "$SB3" --seconds 3           # L5 SMOKE_OK
python3 scripts/semantic_check.py                                        # L7 SEMANTIC_OK
rm -rf examples/output/_extract
```

fruit_basket 实测结果（见 §3 表）。**L6 `verify_techniques.mjs` 是猫抓老鼠专属**，
只对该作品跑；通用作品跳过 L6，进阶技巧由 `technique_probe*.sb3` 与对应模板覆盖。

### 2.6 质量门禁（第 6 步）

```bash
python3 scripts/quality_gate.py --sb3 examples/output/fruit_basket.sb3 \
        --spec examples/fruit_basket.quality.json --strict
```

输出：`达标 9/9 · 评级：优秀` → 打印 `QUALITY_GATE_OK`，`--strict` 退出码 0，可交付。

---

## 3. 八层校验总表（对齐 SKILL.md）

| # | 命令 | 通过标志 | fruit_basket 实测 |
|---|---|---|---|
| 1 | `validate_sb3.py --sb3 <x.sb3>` | `全部校验通过 ✅` | ✅ |
| 2 | `validate_schema.mjs <project.json>` | `SCHEMA_OK` | ✅ |
| 3 | `validate_parser.mjs <x.sb3>` | `PARSER_OK` | ✅ |
| 4 | `validate_runtime.mjs <project.json>` | `RUNTIME_OK` | ✅ |
| 5 | `smoke_test.mjs <x.sb3> --seconds 3` | `SMOKE_OK` + 变量符合预期 | ✅ |
| 6 | `verify_techniques.mjs <x.sb3> <out>` | `ALL_NEW_TECH_OK` | ⛔ 猫抓老鼠专属，本作跳过 |
| 7 | `semantic_check.py` | `SEMANTIC_OK` | ✅（27/27 探针） |
| 8 | `quality_gate.py --sb3 <x.sb3> --spec <s>.json --strict` | `QUALITY_GATE_OK` | ✅（9/9） |

> 前七层保证「能打开、逻辑对」；**第 8 层才保证「像作品」**。
> 不做质量门禁，一个零音效、2 个几何造型的 demo 能全过前七层被交付。

- 第 2/4 层要解压后的 `project.json`（sb3 是 zip），见 §2.5 一行解压命令。
- 第 5 层可选 `--catch`（猫抓老鼠用，模拟点开始+同步猫鼠坐标触发碰撞计分）。
- 第 7 层是**积木语义回归**：前六层只保证「能打开不崩」，这一层保证「1+2 真的等于 3」。
  改动构建器、别名表、输入映射后必跑。
- **答题/测验类额外必跑** `node scripts/quiz_behavior_check.mjs <x.sb3>` → `QUIZ_LOGIC_OK`。

---

## 4. 质量门禁（第 8 层）详解

### 4.1 两层结构

- **A. 资产密度（6 项计数，所有品类都查）**：造型 / 音效 / 角色 / 体积 / 场景 / 积木。
- **B. 玩法完整度（3 项启发式，仅 `genre=game` 强制）**：玩家可操控 / 胜负条件 / 重玩价值。

### 4.2 fruit_basket 的规格表实测（按 `game` 档，仅 bytes 下调）

| 指标 | 实测 | 门槛 | 结果 |
|---|---|---|---|
| 造型数 | 21 | 20 | OK |
| 音效/音乐数 | 9 | 8 | OK |
| 角色数 | 8 | 4 | OK |
| 产物体积 | 674 KB | 400000 | OK（默认 game 为 1MB，已下调） |
| 场景/背景数 | 2 | 2 | OK |
| 积木数 | 244 | 150 | OK |
| 玩家可操控 | 有 | 必有 | OK |
| 胜负/目标条件 | 有 | 必有 | OK |
| 重玩价值 | 有 | 必有 | OK |

### 4.3 为什么下调 `bytes`

`game` 档默认 `min_bytes=1000000` 是参照社区**栅格重美术**作品（照片/PNG 素材）定的。
本作是**矢量 SVG + WAV 音效**游戏：21 个 SVG 造型、8 个真实音效、1 段 BGM，
真实素材已约 674KB，是完整可玩的作品。硬塞 1MB 只会逼人拿环境音循环 padding，
正好违背门禁「不要靠堆积木/堆素材凑指标」的初衷。

**正确做法（门禁本身支持）**：`--init` 生成规格表后，手改 `min_bytes` 到题材合理值，
其余 game 门槛原样保留，并在 `_note` 字段写明理由。这样 B 层玩法完整度（真正的「像作品」信号）
一字未动，依然强制。

> 音乐 / 动画 / 剧情类：在规格表设 `genre=music/animation/story` 自动跳过 B 层；
> 纯技术验证用 `--profile demo` 显式豁免，并在交付说明注明档位。

---

## 5. 全新环境安全网（社区素材占位降级）

`examples/fruit_basket.yaml` 里 15 处引用 `asset: "community:<id>"`。
部署分发包**只带 63 个样本素材**（351MB 全量库不进包）。

- **装了全量库**（环境变量 `COMMUNITY_ASSET_LIBRARY` 指向库目录）：正常展开。
- **只有样本层**：样本命中的正常展开，未命中的自动去全量库查。
- **两者都没有（全新环境只装了 skill 包）**：`scripts/asset_pack.py` 不再 `FileNotFoundError`
  硬崩，而是**程序化生成占位素材**——造型/背景换成带标签的 SVG、音效换成 440Hz 短音，
  并在 stderr 打印 `[社区素材] 占位降级` 告警。作品照常编译、八层照常过，
  只是那几个素材是占位图，**提醒你补真实素材**。

> 占位缓存在 `assets/community/generated/`，属运行时生成物，**不进分发包**
>（`deploy-tools/pack_skill.py` 已排除）。详见 `assets/community/README.md`。

---

## 6. IR 写法避坑（本次实战踩过的）

1. **帽子必须块式**：`when_receive: {message: 开始游戏}`，**不能**写 `when_receive: 开始游戏`
   （会被 YAML 当成内联标量，后面跟 `comment:` 直接 `ScannerError`）。
2. **无参积木写成 `{hide: null}` / `{show: null}` / `{next_costume: null}` / `{delete_this_clone: null}`**，
   不能裸写 `hide:`（校验报「每个积木必须写成 {积木名: 值}」）。
3. **运动用 `change_x:{dx:}` / `set_x:{x:}` / `change_y:{dy:}`**；
   读坐标用报告符 `x_position` / `y_position`，**不是** `x` / `y`。
4. **比较用 `equals` / `greater_than` / `less_than`，参数 `{a:, b:}`**；
   `if_else` 的 `else:` 与 `if:` 同级、**不要**包在 `do:` 里（构建会自动把 `if+else` 升级）。
5. **不要**用 `not:` 包 `equals`（parser 不认，报「未知积木名 'a'」）；
   要取反就换比较方向，或引入变量做等价判断。
6. **`and` / `or` 只有 2 个输入位**：3 个以上条件要**嵌套两层**，如
   `{and:[A, {and:[B, C]}]}`，否则多出的条件被丢弃、逻辑算错。
7. **资产路径相对 IR 目录**：把素材放 IR 同级的 `assets/` 下，保证自包含。
8. **编译必带 `--workdir`**，避免 CWD 残留 `_proj`。
9. 无头校验测不到 size/克隆/画笔/音频/悬停/中文排版/手感，**仍需人工目视**。

---

## 7. 交付物清单（fruit_basket 样例）

| 文件 | 说明 |
|---|---|
| `examples/fruit_basket.yaml` | 端到端 IR 源（可当模板抄） |
| `examples/fruit_basket.sb3` | 编译产物，**9 角色 / 244 积木 / 674 KB**，八层 + 门禁全过 |
| `examples/fruit_basket.quality.json` | 规格表（game 档，bytes 已下调并注明） |
| `examples/assets/ui/*.png` | UI 素材（标题/按钮/篮子/胜负页/重开/+1/过关！） |
| `examples/assets/sfx/*.wav` | 22 个音效 + manifest.json |

> 照这套跑通，你就拥有了一件「能打开、逻辑对、像作品、可重玩」的真·完整作品，
> 以及一套可复用的端到端命令模板。
