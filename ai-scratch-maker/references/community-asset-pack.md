# 社区素材包与参数化模板（§C6）

> 解决「生成物只有 2–4 个几何造型、零音效，因而不像作品」的问题。
> 素材来自 11 个真实社区作品（1717 次引用 → 1410 个去重素材），配合 5 个已验证的可编译 IR 模板。
> 提炼出的模式见 `community-techniques.md` §C1–§C5，本册讲**怎么直接用**。

---

## ⚠️ 先看授权

所有素材来自小码王社区公开作品，**仅供本项目学习与内部参考**。

- `assets/community/manifest.json` 每条素材的 `sources` 都带原作品 CID、标题、**作品页 URL**、原始名与所属角色，便于回溯。
- 标注为「转载」「改编」的作品（NGwJJ66J / bkiJJ66J / JCS6J66J / hKS6J66J / fSS6J66J）**尤其需要确认原始授权链**；部分作品说明中作者明确表达了改编限制，请尊重原作者意愿。
- 对外分发、发布到社区或商用前，须自行取得原作者授权；不要把第三方素材当作本 skill 自产素材。
- 本 skill 自己产出的作品仍按铁律 3 署名 CC BY-SA，且不得写「禁止改编」。

---

## 三层结构

| 层 | 位置 | 体积 | 用途 |
|---|---|---|---|
| 轻索引 | `assets/community/manifest.json` + `INDEX.md` | ~1 MB | 随 skill 分发，检索用 |
| 样本层 | `assets/community/samples/`（63 个） | 0.76 MB | 随 skill 分发，**离线即可引用** |
| 全量库 | `<项目根>/community-crawler/data/asset_pack/library/` | 351 MB | 不进 skill 包；本机开发时用 |

全量库按内容 md5 去重（重复率 17.9%）。找不到库时设置环境变量：

```bash
export COMMUNITY_ASSET_LIBRARY=/path/to/community-crawler/data/asset_pack/library
```

重新生成资产包（在 `community-crawler/` 下）：

```bash
python extract_asset_pack.py
```

---

## 三种引用方式

**① 推荐：虚拟引用**（编译前由 `build_sb3.py` 自动展开成绝对路径）

```yaml
costumes:
  - {asset: "community:pGeJJ66J/办公室亮灯"}
  - {name: 我的名字, asset: "community:2SwJJ66J/体力果"}
```

不写 `name` 时会自动补素材原名。解析顺序：样本层 → 全量库 → 报错并提示 `fetch`。

**② 直接引用样本**（skill 单独分发时最稳）

```yaml
- {asset: "assets/community/samples/2SwJJ66J_体力果_239fea7a.svg"}
```

**③ 取到工程里**（想让产物自包含、或素材不在本机库里时）

```bash
python scripts/asset_pack.py fetch "pGeJJ66J/办公室" --to examples/assets/community
```

---

## CLI 速查

```bash
python scripts/asset_pack.py stats                              # 概览与库路径
python scripts/asset_pack.py search 办公室 --kind backdrop       # 按名字/来源/类型检索
python scripts/asset_pack.py search 数字方块 --cid NGwJJ66J
python scripts/asset_pack.py resolve "community:2SwJJ66J/体力果"  # 看解析到哪个文件
python scripts/asset_pack.py fetch <id> --to <目录>             # 复制到工程
```

`search` 会直接打印可粘贴的 `asset: community:<id>` 写法。

---

## 5 个参数化 IR 模板

模板会自动**从资产包挑真实素材**填进去，生成即可编译，不用从零画。全部已通过四层校验。

```bash
python scripts/gen_community_template.py --list
python scripts/gen_community_template.py --template numberblock_band --count 8 --out examples/band.json
python scripts/build_sb3.py --ir examples/band.json --out examples/output/band.sb3 --workdir <tmp>
```

| 模板 | 对应模式 | 骨架 | 实测产物（count=6） |
|---|---|---|---|
| `numberblock_band` | §110 广播乐队 | 指挥者 `broadcast_and_wait` 序列 + N 个方块接收帽（换造型→播音→等待→隐藏） | 166 KB / 7 targets |
| `audio_sequence_player` | §109 音频序列 | 单角色按序 换造型 + 播音 + 等待 | 3.6 MB / 2 targets |
| `backdrop_room_fsm` | §106 房间状态机 | N 个背景造型即房间 + `when_backdrop_switches_to` 钩子 + HUD 广播解耦 | 20 KB / 2 targets |
| `clone_swarm` | §107 克隆海 | 母体刷 N 克隆 + 私有 `是克隆` + 列表存实体坐标 | 7 KB / 2 targets |
| `list_maze` | §108 列表迷宫 | 一维列表存 `宽×高` 地图 + `索引 = y*宽 + x + 1` 查格 | 8 KB / 2 targets |

> 注意 `add` / `and` / `or` 只有 **2 个输入槽**，三项要嵌套成 `{add: [a, {add: [b, c]}]}`；
> 构建器的语义校验会拦下这种「能打开但算错」的写法（本次 `list_maze` 就被正确拦了一次）。

---

## 把它接进「作品规格表」

资产包只是供给侧。要真正提高成品质量，生成前应先定规格，交付前按规格验收：

| 指标 | demo 级（当前默认） | 作品级（建议门槛） | 参照 |
|---|---|---|---|
| 造型数 | 2–4 | ≥ 20 | 数字方块 Ultra100：478 |
| 音效/音乐数 | 0（82% 示例） | ≥ 8 | 双阶乘：45 |
| 角色数 | 1–3 | ≥ 8 | FNAF：29 |
| 产物体积 | ~90 KB | ≥ 2 MB | 社区典型 9–62 MB |
| 关卡/内容量 | 单场景 | ≥ 3 场景或 10 关卡 | FNAF 40 个背景 |

可用 `scripts/digest_sb3.py` / `community-crawler/analyze.py` 统计这些指标做自动门禁。
**这批数字就是「高质量」的可量化锚点**——注意逻辑积木数不需要进门槛，现有示例最多 1566 块已超过 FNAF 的 1005 块，瓶颈从来不在逻辑。

---

## 已知边界

- SVG 来自真实作品，尺寸/旋转中心各异；若要精确排布，先跑 `scripts/prep_asset.py` 归一化。
- 大 BGM（最大 20 MB 的 WAV）只在全量库里，不进 skill 包。
- 无头校验测不到 size / 克隆 / 画笔 / 音频 / 悬停，素材「好不好看」仍需人工目视。
- 模板是**骨架**，不是成品；数值、演出节奏、关卡内容仍需按具体题材设计。
