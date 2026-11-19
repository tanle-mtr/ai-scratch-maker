#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从已下载的社区 .sb3 提取可复用素材，生成带来源署名的资产包。

用法（在 community-crawler/ 下执行）：
    python extract_asset_pack.py

产物分三处：
- data/asset_pack/library/             全量素材库（md5 去重，不进 skill 分发包）
- ../ai-scratch-maker/assets/community/manifest.json   轻索引（进 skill）
- ../ai-scratch-maker/assets/community/samples/       精选样本（进 skill，可离线直接引用）

IR 引用统一写 `asset: community:<id>`，由 build_sb3.py 解析；
也可写 `asset: assets/community/samples/<文件名>` 直接引用样本。

每条素材都带来源 CID / 作品名 / 原始名 / 角色 / 作品页 URL，便于回溯授权。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import zipfile
from collections import defaultdict

WORKS = [
    ("2SwJJ66J", "迷宫寻宝", "2SwJJ66J_迷宫寻宝.sb3"),
    ("WbwJJ66J", "深圳地铁12号线吹牛失败", "WbwJJ66J_深圳地铁12号线.sb3"),
    ("pGeJJ66J", "FNAF Never Along(0.24)", "pGeJJ66J_FNAF Never Along.sb3"),
    ("jmIo666J", "小猫生存1.0.3", "jmIo666J_小猫生存1.0.3.sb3"),
    ("rMwJJ66J", "Number blocks Band 51-60", "rMwJJ66J_Number blocks Band 51-60.sb3"),
    ("3AwJJ66J", "双阶乘简版素材+0!!-37!!音乐", "3AwJJ66J_双阶乘简版素材.sb3"),
    ("NGwJJ66J", "数字方块 Ultra Omega Giga 不同 100", "NGwJJ66J_数字方块UltraOmegaGiga不同100.sb3"),
    ("bkiJJ66J", "数字方块Ultra Omega Giga不同41", "bkiJJ66J_数字方块UltraOmegaGiga不同41.sb3"),
    ("JCS6J66J", "数字方块恐怖扭曲1-10", "JCS6J66J_数字方块恐怖扭曲1-10.sb3"),
    ("hKS6J66J", "数字方块恐怖扭曲11-20", "hKS6J66J_数字方块恐怖扭曲11-20.sb3"),
    ("fSS6J66J", "数字方块恐怖扭曲21-30", "fSS6J66J_数字方块恐怖扭曲21-30.sb3"),
]

# 仅在有确证时填写；不确定的留 null，避免编造。以作品页标签为准。
KNOWN_LABEL = {
    "WbwJJ66J": "原创",
    "NGwJJ66J": "转载",
    "bkiJJ66J": "转载",
    "JCS6J66J": "改编",
    "hKS6J66J": "改编",
    "fSS6J66J": "改编",
}

ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
SOURCE_URL = "https://world.xiaomawang.com/community/main/compose/{cid}"


def safe_name(s):
    s = ILLEGAL.sub("_", (s or "unnamed").strip())
    return s[:80] if s else "unnamed"


def main():
    ap = argparse.ArgumentParser(description="从社区 sb3 提取可复用素材包")
    ap.add_argument("--raw", default="data/raw", help="原始 sb3 目录")
    ap.add_argument("--library", default="data/asset_pack/library", help="全量素材库目录")
    ap.add_argument("--skill-assets", default="../ai-scratch-maker/assets/community",
                    help="skill 内轻索引与样本目录")
    ap.add_argument("--samples-max-bytes", type=int, default=120 * 1024,
                    help="样本单文件上限")
    ap.add_argument("--samples-per-work", type=int, default=6,
                    help="每个来源作品最多挑几个样本")
    args = ap.parse_args()

    lib_root = args.library
    skill_root = args.skill_assets
    sample_root = os.path.join(skill_root, "samples")
    for sub in ("backdrops", "costumes", "audio"):
        os.makedirs(os.path.join(lib_root, sub), exist_ok=True)
    os.makedirs(sample_root, exist_ok=True)

    assets = {}
    missing = []
    total_refs = 0
    used_ids = defaultdict(int)

    for cid, title, fname in WORKS:
        path = os.path.join(args.raw, fname)
        if not os.path.exists(path):
            missing.append(fname)
            continue
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            project = json.loads(z.read("project.json"))
            for target in project["targets"]:
                is_stage = target.get("isStage", False)
                sprite = target["name"]
                for slot, is_costume in (("costumes", True), ("sounds", False)):
                    for c in target.get(slot, []):
                        md5ext = c.get("md5ext", "")
                        if md5ext not in names:
                            continue
                        blob = z.read(md5ext)
                        h = hashlib.md5(blob).hexdigest()
                        total_refs += 1
                        ext = os.path.splitext(md5ext)[1].lower().lstrip(".")
                        source = {
                            "cid": cid, "title": title, "label": KNOWN_LABEL.get(cid),
                            "url": SOURCE_URL.format(cid=cid),
                            "original_name": c.get("name", ""), "sprite": sprite,
                        }
                        if h in assets:
                            if source not in assets[h]["sources"]:
                                assets[h]["sources"].append(source)
                            continue

                        if not is_costume:
                            kind = "sound"
                        else:
                            kind = "backdrop" if is_stage else "costume"
                        sub = {"backdrop": "backdrops", "costume": "costumes", "sound": "audio"}[kind]
                        base = safe_name(c.get("name", "")) or "unnamed"
                        filename = "{}_{}_{}.{}".format(cid, base, h[:8], ext)
                        lib_rel = "{}/{}".format(sub, filename)
                        with open(os.path.join(lib_root, lib_rel), "wb") as f:
                            f.write(blob)

                        stem = "{}/{}".format(cid, base)
                        used_ids[stem] += 1
                        aid = stem if used_ids[stem] == 1 else "{}#{}".format(stem, used_ids[stem])
                        assets[h] = {
                            "id": aid,
                            "ir_asset": "community:" + aid,
                            "library_file": lib_rel,
                            "sample_file": None,
                            "kind": kind,
                            "format": ext,
                            "bytes": len(blob),
                            "md5": h,
                            "sources": [source],
                        }

    # 精选样本：每个来源作品按 kind 覆盖，优先小体积、名字带语义
    by_work = defaultdict(list)
    for r in assets.values():
        by_work[r["sources"][0]["cid"]].append(r)
    for cid, recs in by_work.items():
        cand = [r for r in recs if r["bytes"] <= args.samples_max_bytes]
        cand.sort(key=lambda r: (
            0 if r["kind"] == "backdrop" else (1 if r["kind"] == "costume" else 2),
            not bool(re.search(r"[\u4e00-\u9fff]", r["sources"][0]["original_name"])),
            r["bytes"],
        ))
        picked, kinds = [], set()
        for r in cand:
            if r["kind"] not in kinds:
                picked.append(r); kinds.add(r["kind"])
        for r in cand:
            if len(picked) >= args.samples_per_work:
                break
            if r not in picked:
                picked.append(r)
        for r in picked:
            src = os.path.join(lib_root, r["library_file"])
            dst = os.path.join(sample_root, os.path.basename(r["library_file"]))
            shutil.copyfile(src, dst)
            r["sample_file"] = "assets/community/samples/" + os.path.basename(r["library_file"])

    records = sorted(assets.values(), key=lambda r: (r["sources"][0]["cid"], r["kind"], r["id"]))
    sample_count = sum(1 for r in records if r["sample_file"])
    sample_bytes = sum(r["bytes"] for r in records if r["sample_file"])

    manifest = {
        "schema": "ai-scratch-maker/community-asset-pack v1",
        "generated_by": "community-crawler/extract_asset_pack.py",
        "source_works": len(WORKS) - len(missing),
        "total_asset_refs": total_refs,
        "unique_assets": len(records),
        "samples": sample_count,
        "sample_bytes": sample_bytes,
        "library_root": "data/asset_pack/library",
        "library_root_hint": "相对 community-crawler/；skill 单独分发时可用环境变量 COMMUNITY_ASSET_LIBRARY 指定，或只用样本层。",
        "license_notice": (
            "素材来自小码王社区公开作品，仅供本项目学习与参考。每条记录的 sources 含原作品 CID/标题/作品页 URL；"
            "对外分发或商用前须回溯原作者授权。标注为『转载』『改编』的作品尤其需确认原始授权链，"
            "部分作品说明中作者明确表达了改编限制，请尊重原作者意愿。"
        ),
        "assets": records,
    }
    with open(os.path.join(skill_root, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    lines = ["# 社区资产包速查", "",
             "- 唯一素材 **{}** 个（去重前引用 {} 次）；全量库 {} MB".format(
                 len(records), total_refs,
                 round(sum(r["bytes"] for r in records) / 1024 / 1024, 1)),
             "- skill 内附 **{}** 个精选样本（{} MB），可直接写 `asset: assets/community/samples/<文件名>`".format(
                 sample_count, round(sample_bytes / 1024 / 1024, 2)),
             "- 全量素材写 `asset: community:<id>`，由 `build_sb3.py` 自动解析；检索用 `scripts/asset_pack.py search <关键词>`。",
             "- ⚠️ 素材均来自社区公开作品，`manifest.json` 每条带来源与作品页 URL；对外分发/商用前须回溯原作者授权。", "",
             "## 按来源统计", "", "| 来源 | 唯一素材 | 样本 |", "|---|---|---|"]
    by_src = defaultdict(lambda: [0, 0])
    for r in records:
        s = r["sources"][0]
        k = "{} {}".format(s["cid"], s["label"] or "未标注")
        by_src[k][0] += 1
        by_src[k][1] += 1 if r["sample_file"] else 0
    for k in sorted(by_src):
        lines.append("| {} | {} | {} |".format(k, by_src[k][0], by_src[k][1]))
    lines += ["", "## 按类型统计", "", "| 类型 | 数量 |", "|---|---|"]
    by_kind = defaultdict(int)
    for r in records:
        by_kind[r["kind"]] += 1
    for k in sorted(by_kind):
        lines.append("| {} | {} |".format(k, by_kind[k]))
    with open(os.path.join(skill_root, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("[完成] 引用 {} 次 -> 唯一 {} 个；全量库 {} MB".format(
        total_refs, len(records), round(sum(r["bytes"] for r in records) / 1024 / 1024, 1)))
    print("        skill 样本 {} 个 / {} MB；manifest -> {}".format(
        sample_count, round(sample_bytes / 1024 / 1024, 2), os.path.join(skill_root, "manifest.json")))
    if missing:
        print("[警告] 缺失源作品: {}".format(", ".join(missing)))


if __name__ == "__main__":
    main()
