# 社区素材管线示例（需本地素材库，未随仓库分发）

本目录下的 IR 是**社区素材包（§C6）** 的用法示范：它们通过 `asset: "community:<id>"`
引用社区素材库里的造型与音效。

> ⚠️ **这些素材不随本仓库分发。**
> 素材来自第三方 Scratch 社区的公开作品，其授权声明明确写着：
> 「对外分发或商用前须回溯原作者授权」，且部分原作标注了改编限制。
> 因此仓库只保留**索引与工具**，素材本体由使用者在本机自行获取。

## 本目录内容

| 文件 | 说明 |
|---|---|
| `showcase_band.json` | 《数字方块乐队（20 声部）》—— 社区素材的完整 showcase 工程 |
| `showcase_band.quality.json` | 上述工程的质量门禁规格表 |
| `community_tpl_numberblock_band.json` | 数字方块乐队（6 声部）骨架模板 |
| `community_tpl_backdrop_room_fsm.json` | 背景房间状态机（6 房间）骨架模板 |
| `community_tpl_audio_sequence_player.json` | 音频序列播放器（6 段）骨架模板 |
| `community_tpl_clone_swarm.json` | 克隆海生存骨架（6 实体）模板 |
| `community_tpl_list_maze.json` | 列表迷宫 8×6 模板 |
| `community_asset_smoke.json` | 社区素材包冒烟测试（校验 `community:<id>` 能否展开） |

## 为什么放在子目录

`scripts/build_all.py` 只扫描 `examples/*.{yaml,json}`（**非递归**），
所以本目录的示例**不会**被批量构建，也不会进入 `quality_gate` 的门禁清单。

这一点是刻意的：没有本地素材库时，引用会降级成「程序化占位素材」，
构建虽不报错，但产出的画面与原设计相去甚远——与其生成一份名不副实的产物，
不如让它显式地「不在默认构建范围内」，并在此处说明如何获得真实素材。

## 如何获得素材库（可选）

```bash
# 1) 抓取社区作品并抽取素材包（需要网络；详见 community-crawler/README.md）
python ../community-crawler/extract_asset_pack.py

# 2) 指定素材库位置（环境变量优先，其次是默认相对路径）
export COMMUNITY_ASSET_LIBRARY=/abs/path/to/asset_pack/library

# 3) 确认已接上
python ../scripts/asset_pack.py stats
```

接上之后，本目录的 IR 可以单独构建：

```bash
python ../scripts/build_sb3.py --ir examples/community/community_asset_smoke.json \
    --out /tmp/smoke.sb3 --workdir /tmp/wd
```

没有素材库时，`build_sb3.py` 会自动生成带标签的占位素材并在 stderr 打印
`[社区素材] 占位降级` 告警，**不会硬崩**——这正是设计意图。

## 素材索引

`ai-scratch-maker/assets/community/manifest.json` 记录了每个素材的
原始作品 CID、标题、作品页 URL、原始名与所属角色，可据此回溯原作者。
