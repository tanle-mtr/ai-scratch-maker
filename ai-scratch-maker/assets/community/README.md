# 社区素材包 · 轻索引与样本层

由 `community-crawler/extract_asset_pack.py` 从 11 个小码王社区公开作品生成。
完整使用说明见 `references/community-asset-pack.md`（§C6）。

| 文件 | 说明 |
|---|---|
| `manifest.json` | 1410 个去重素材的完整索引（id / 类型 / 格式 / 大小 / 来源 CID / 原始名 / 作品页 URL） |
| `INDEX.md` | 自动生成的速查统计 |
| `samples/` | 63 个精选样本（0.76 MB），随 skill 分发，可直接写进 IR |

全量素材（351 MB）不在本目录，位于
`<项目根>/community-crawler/data/asset_pack/library/`，
或由环境变量 `COMMUNITY_ASSET_LIBRARY` 指定。

```bash
python scripts/asset_pack.py stats
python scripts/asset_pack.py search 办公室 --kind backdrop
```

IR 引用：`asset: "community:<id>"`（`build_sb3.py` 编译前自动展开）。

---

## 全新环境（只装了 skill 包、没有 351MB 全量库）怎么办？

skill 分发包 **只带 63 个样本**（`samples/`，0.76 MB）。如果 IR 里引用了
**不在样本层**的 `community:<id>`，构建时按以下顺序兜底，**永不硬崩**：

1. 先找样本层 `samples/`（命中即用，画质与原始一致）；
2. 再找全量库：环境变量 `COMMUNITY_ASSET_LIBRARY` →
   `community-crawler/data/asset_pack/library/` → `assets/community/library/`；
3. 两者都没有 → **自动生成程序化占位素材**（造型/背景换成带标签的 SVG、
   音效换成 440Hz 短音），并在 stderr 打印 `[社区素材] 占位降级` 告警，
   构建照常完成。换上真实素材的三种方式见上面的告警提示。

> 想让默认体验直接用真实素材：把 351MB 全量库解压到 `assets/community/library/`
> （或设 `COMMUNITY_ASSET_LIBRARY`），`python scripts/asset_pack.py stats` 会显示
> 「全量素材库：<路径>」即代表已接上。
>
> 占位素材缓存在 `assets/community/generated/`，属运行时生成物，**不进分发包**
> （打包时已排除，见 `deploy-tools/pack_skill.py`）。

---

## ⚠️ 授权与署名

素材来自小码王社区公开作品，**仅供本项目学习与内部参考**，不是本 skill 自产素材。

- `manifest.json` 每条记录的 `sources` 含原作品 CID、标题、**作品页 URL**、原始名与所属角色，便于回溯。
- 标注「转载」「改编」的作品（NGwJJ66J / bkiJJ66J / JCS6J66J / hKS6J66J / fSS6J66J）需确认原始授权链；部分作品说明中作者明确表达了改编限制，请尊重原作者意愿。
- **对外分发、发布到社区或商用前，须自行取得原作者授权。**
- 本 skill 自己产出的作品仍按铁律 3 署名 CC BY-SA，且不得写「禁止改编」。
