# 第三方素材与许可声明

本仓库（ai-scratch-maker）自身的代码、文档与**自产素材**以
[CC BY-SA 4.0](LICENSE) 授权。

但仓库中有些内容**没有**随仓库分发，原因与出处如下。

---

## 1. 社区素材包（`assets/community/`）— 未分发

**来源**：由 `community-crawler/extract_asset_pack.py` 从 11 个第三方 Scratch 社区
（小码王等）的公开作品抽取，共 1410 个素材。

**为什么不分发**：素材索引 `manifest.json` 里记录的原始授权声明写得很明确——

> 素材来自小码王社区公开作品，仅供本项目学习与参考。每条记录的 sources 含原作品
> CID/标题/作品页 URL；**对外分发或商用前须回溯原作者授权**。标注为「转载」「改编」
> 的作品尤其需确认原始授权链，部分作品说明中作者明确表达了改编限制，
> 请尊重原作者意愿。

既然部分原作明确声明了改编限制，就不能把它们的素材当作可再分发的自有内容发布。
因此仓库只保留**工具与索引**，素材本体由使用者在本机自行获取：

```bash
python community-crawler/extract_asset_pack.py      # 需要网络
export COMMUNITY_ASSET_LIBRARY=/abs/path/to/library
python ai-scratch-maker/scripts/asset_pack.py stats  # 确认已接上
```

没有素材库时，构建器会生成带标签的**程序化占位素材**并在 stderr 打印
`[社区素材] 占位降级` 告警，**不会中断构建**。这是设计好的降级路径，
不是缺陷。

**如何使用这些素材**：请遵循原作者的授权条款（通常要求署名 CC BY-SA，
并保留原始作品链接）。素材索引里的 `sources` 字段提供了完整回溯信息。

---

## 2. 社区爬取的原始作品（`community-crawler/data/`、`community-crawler/demo/`）— 未分发

这两个目录（约 1GB）存放的是从第三方社区抓取的**他人作品**（.sb3）、反编译产物与
分析报告。它们是**调研素材**，不属于本项目自产内容，不得公开转发。

仓库只保留爬虫与解析工具的**代码**（`community-crawler/*.py`）。使用者如需调研，
请自行抓取，并遵守目标社区的服务条款与著作权。

---

## 3. GitHub 参考作品（`references/gh_reference_works/`）— 部分分发

该目录的 16 个 .sb3 来自两个上游 GitHub 仓库，许可不同：

| 上游仓库 | 许可 | 是否随仓库分发 |
|---|---|---|
| `learning-game-development/learning-scratch-game-development` | Unlicense（公有领域奉献） | ✅ 8 个英文名作品（`Platformer` / `Brick-Breaker` / `Fruit_Slicer` / `Asteroid-Breaker` / `Basketball` / `Maze-Runner` / `Snaaaaaake` / `Rainbow-Lines`） |
| `SilkRoad/Scratch` | **无许可证**（GitHub API `license=NONE`） | ❌ 8 个编号作品（`001`–`007`） |

无许可证即未授予复制与再分发权，故编号系列不随仓库分发；需要时自行从上游获取。

---

## 4. Scratch 官方源码（`reference/scratch-sources/`）— 未分发

`scratch-vm` / `scratch-blocks` / `scratch-parser` 的源码副本（约 74MB）用于
提取官方积木规范与官方 JSON Schema。它们是第三方作品，遵循各自上游的许可证
（Scratch 官方仓库为 MIT / LGPL 等），故不随本仓库分发。

按需自行获取：

```bash
git clone https://github.com/scratchfoundation/scratch-vm.git reference/scratch-sources/scratch-vm
git clone https://github.com/scratchfoundation/scratch-blocks.git reference/scratch-sources/scratch-blocks
git clone https://github.com/scratchfoundation/scratch-parser.git reference/scratch-sources/scratch-parser
```

官方 JSON Schema 亦可从 `scratch-vm/src/../scratch-parser` 相关目录获取；
`scripts/validate_schema.mjs` 在缺失时会有明确提示。

---

## 5. 运行时依赖

| 依赖 | 许可证 | 用途 |
|---|---|---|
| Python ≥ 3.8 + PyYAML | MIT / PSF | IR 解析、构建器与门禁脚本 |
| Node.js ≥ 18 | MIT | schema / parser / runtime 校验器 |
| [ajv](https://github.com/ajv-validator/ajv) v6 | MIT | 官方 project.json Schema 校验 |
| fast-deep-equal | MIT | 深度比较 |
| fast-json-stable-stringify | MIT | 稳定 JSON 序列化 |
| json-schema-traverse | MIT | Schema 遍历 |
| uri-js | MIT | URI 处理 |
| Pillow | MIT-CMU | 位图 alpha 检测（素材合适性判定） |

第三方依赖通过 `ai-scratch-maker/package.json` 声明，执行 `npm install` 安装，
**不**提交 `node_modules/`。

---

## 6. 自产素材

以下素材由本项目生成，适用本仓库的 CC BY-SA 4.0 授权：

- `ai-scratch-maker/examples/assets/**` —— 矢量素材（SVG）、生图素材（PNG）与音效（WAV），
  由 `scripts/gen_ui_kit.py`、`scripts/gen_fruit_art.py`、`scripts/gen_sfx_kit.py`、
  `scripts/gen_audio.py` 等生成器产出；
- `ai-scratch-maker/assets/td/`、`ai-scratch-maker/assets/templates/` —— 模板素材；
- `ai-scratch-maker/raw_assets/` —— `generate_staged --raw-assets` 的输入样本。

**署名要求**：使用本项目生成的素材或产出的 .sb3 作品时，请署名
「ai-scratch-maker」并附上本仓库链接，且**不得附加「禁止改编」类限制**
（这既是本项目的铁律 3，也是 CC BY-SA 的要求）。

---

## 7. 随仓库分发的成品作品

仓库根目录的 `猫抓老鼠.sb3` 是本项目自产的示例作品，适用 CC BY-SA 4.0。
它是《猫抓老鼠》教学示例的成品，作者允许自由改编与再分发。
