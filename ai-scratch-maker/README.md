# AI Scratch Maker

让 AI 生成 **Scratch 3.0 作品（.sb3 文件）** 的 WorkBuddy Skill。

AI 不直接写 `.sb3` 的 JSON 数组（极易出错），而是写一份人类可读的 **中间表示（IR）**，
由序列化器编译成合法且能被 Scratch 打开/运行的 `project.json` + 素材。

---

## 快速上手

```bash
# 1. 写一份 IR（YAML 或 JSON）
# 2. 编译成 .sb3
python3 scripts/build_sb3.py --ir examples/cat_chase.yaml --out 作品.sb3

# 3. 三重校验（结构 / 官方 Schema / scratch-vm 运行时）
python3 scripts/validate_sb3.py --sb3 作品.sb3
```

输出：

```
结构校验通过: 作品.sb3
  targets=2 blocks=25 extensions=['pen']
  [ok] 官方 schema 校验: SCHEMA_OK
  [ok] 运行时校验: RUNTIME_OK targets=2
全部校验通过 ✅
```

---

## 这个 Skill 解决什么问题

| 手写 sb3 的坑 | 本 Skill 怎么避免 |
|---|---|
| 菜单下拉写成数组而不是裸字符串 | 序列化器统一编码成 `[1, "值"]` |
| 变量该放 `fields` 却放进了 `inputs` | 积木规范来自 Scratch 官方源码，位置天然正确 |
| opcode 拼错（`looks_seteffect` ≠ `looks_seteffectto`） | 规范自动抽取 + 运行时原语交叉校验 |
| 变量名被二次编码成字符串 | 校验器专门检查这种畸形 |
| 自定义积木缺 `tagName`/`children` | 序列化器自动生成完整 mutation |
| 云变量作用域搞错 | 舞台变量自动全局共享，角色不重复创建 |
| 漏掉某个积木 | 抽取脚本保证「运行时原语 100% 收录」 |

---

## 素材：图片与音频都由 agent 本地生成

**图片**：用 **ImageGen** 生成背景/角色 → `scripts/prep_asset.py` 整理
（舞台裁填 480×360、角色等比缩放、`--remove-bg` 抠掉 AI 常见的浅灰棋盘格底、
`--check-alpha` 自检背景、`--flip-h` 生成镜像造型）。

> 🔒 **默认最高质量**：除非用户明确要求降级，一律 `quality: high` + 大 `size`
> （背景 `1536x1024`、角色 `1024x1024`），不得因省时间/省积分自行降级。
> AI 图建议再跑 `--hq`（去白边+锐化），背景图加 `--crop-watermark` 去右下角水印。
> 完整参数模板与实测结论见 `references/asset-guide.md` §一。

**角色的朝向**：Scratch 默认的 `all around` 会让角色朝上走时整个倒过来；
人物动物要用 `rotationStyle: left-right`。但那样朝左时**整个造型会被镜像**，
所以要准备「原图 + 镜像图」两套造型、按 `direction` 切换 —— 详见 `references/sprite-art.md`。

**音频**：**不接任何外部 TTS / 音乐 API**，由 `scripts/gen_audio.py` 离线合成
（纯 Python 标准库，零第三方依赖）：

```bash
python3 scripts/gen_audio.py list                        # 17 音效预设 + 7 程序化 BGM
python3 scripts/gen_audio.py sfx --name coin   --out assets/coin.wav
python3 scripts/gen_audio.py bgm --mood chase --bars 4 --out assets/bgm.wav
```

BGM 是程序化生成的并做了**无缝循环**，在 Scratch 里放舞台上、
用「播放 声音直到播放完毕」+ `forever` 即可无缝衔接。

---

## 积木规范来自官方源码

`references/blocks-spec.json` 不是手写的，而是从 Scratch 官方仓库直接抽取：

| 来源 | 提供什么 |
|---|---|
| `scratch-blocks/src/blocks/*.ts` | 积木形状、输入名、字段名、下拉选项、英文原文 |
| `scratch-vm/src/blocks/scratch3_*.js` | 运行时原语清单（保证不漏）、输入原始类型 |
| `scratch-vm/src/extensions/*/index.js` | 画笔/音乐/朗读/翻译/视频感应/语音转文字扩展 |

抽取脚本会做 **交叉校验**：scratch-vm 运行时支持的每一个原语都必须出现在规范里，
否则以非零退出码报警。

> 已验证：Scratch 3.0 发布时（2019）与当前版本的 opcode 集合 **完全一致**，
> 所以规范对 Scratch 3.0 有效。

---

## 目录

```
ai-scratch-maker/
├── SKILL.md                 # Skill 说明书（agent 读这个）
├── README.md                # 本文件
├── agents/openai.yaml       # agent 界面定义
├── references/
│   ├── blocks.md            # ★ 全部 188 个积木的速查表（先看这个）
│   ├── blocks-spec.json     # 机器可读规范
│   ├── blocks-spec.md       # sb3 编码规则详解
│   ├── ir-format.md         # IR 格式说明
│   ├── sprite-art.md        # ★ 角色美术规范（透明背景 / 左右翻转 / 多造型）
│   └── asset-guide.md       # 素材生成指南
├── scripts/                 # 全部工具脚本
└── examples/                # 34 个可运行示例（IR + 产物 .sb3）
```

---

## 环境依赖

| 依赖 | 用途 | 必需？ |
|---|---|---|
| Python 3 + PyYAML | 编译与校验 | 必需 |
| Pillow | `prep_asset.py` 图片整理 | 生成图片素材时需要 |
| Node.js | Schema 校验 + scratch-vm 运行时校验 | 强烈建议 |
| scratch-vm | 运行时校验 | 由 `SCRATCH_VM_PATH` 指定，默认路径已内置 |

安装：

```bash
python3 -m pip install pyyaml pillow
npm install scratch-vm
```

---

## 重新抽取积木规范

```bash
git clone --depth 1 https://github.com/scratchfoundation/scratch-vm.git
git clone --depth 1 --filter=blob:none --sparse https://github.com/scratchfoundation/scratch-blocks.git
cd scratch-blocks && git sparse-checkout set src msg

node scripts/extract_blocks_spec.js \
  --scratch-blocks ../reference/scratch-sources/scratch-blocks \
  --scratch-vm     ../reference/scratch-sources/scratch-vm \
  --aliases        references/blocks-aliases.json \
  --out            references/blocks-spec.json

python3 scripts/make_aliases.py     # 友好名对照表
python3 scripts/make_blocks_doc.py  # 生成 blocks.md
```
