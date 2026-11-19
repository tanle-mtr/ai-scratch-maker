#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""社区素材扩充：把更多社区作品素材并入素材包 manifest。

现状（详见 MEMORY.md「小码王下载」与社区补编 §C6）：
  · 当前素材包 63 个样本 + manifest；全量库 1410 个在 community-crawler/data 下（不进 skill）。
  · 直接联网爬取被墙：scratch.mit.edu 不可达、小码王 CDN 直链 403、javascript 注入被屏蔽、
    Edge dom_cua 会 Blocked/timeout。**不要再用这三条**。
  · 唯一可行的在线取数＝小码王「保存到电脑」人工流程（见 MEMORY），无法脚本化。

所以本脚本提供**离线可跑**的两条真路径 + 一条**明确标注待联网**的爬取入口：

  1. --status            报告当前 manifest 规模（样本数 / 唯一数 / 按类型 / 库根提示）。
  2. --merge <dir>       并入已下载素材：<dir> 里放素材文件 + 一份 manifest 片段
                         （同 schema 的 assets 列表），本脚本去重并入、拷贝样本进
                         assets/community/samples/、重算 samples/sample_bytes/unique_assets，
                         写回 manifest（先备份）。这是「人工下载 → 脚本并入」的落地命令。
  3. --crawl             【待联网】列出候选来源与小码王「保存到电脑」人工流程；
                         真正爬取只在网络可达时尝试，否则明确报「网络受限，待执行」。

用法：
    python scripts/expand_community_assets.py --status
    python scripts/expand_community_assets.py --merge ./new_assets --fragment frag.json
    python scripts/expand_community_assets.py --crawl
"""
import argparse
import json
import os
import shutil
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
MANIFEST = os.path.join(SKILL_ROOT, "assets", "community", "manifest.json")
SAMPLES_DIR = os.path.join(SKILL_ROOT, "assets", "community", "samples")


def load_manifest():
    if not os.path.exists(MANIFEST):
        print("找不到 %s" % MANIFEST, file=sys.stderr)
        sys.exit(2)
    return json.load(open(MANIFEST, encoding="utf-8"))


def save_manifest(m):
    bak = MANIFEST + ".bak_" + datetime.date.today().isoformat()
    if not os.path.exists(bak):
        shutil.copyfile(MANIFEST, bak)
    json.dump(m, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("manifest 已写回（备份 %s）" % bak)


def cmd_status(m):
    assets = m.get("assets", [])
    by_kind = {}
    samples = 0
    bytes_ = 0
    for a in assets:
        by_kind[a.get("kind", "?")] = by_kind.get(a.get("kind", "?"), 0) + 1
        if a.get("sample_file"):
            samples += 1
            bytes_ += a.get("bytes", 0)
    ids = set(a.get("id") for a in assets)
    print("=" * 56)
    print("社区素材包状态")
    print("=" * 56)
    print("  唯一素材 id : %d" % len(ids))
    print("  条目总数   : %d" % len(assets))
    print("  有样本文件 : %d（%.2f MB）" % (samples, bytes_ / 1024 / 1024))
    print("  库根提示   : %s" % m.get("library_root_hint", "?"))
    print("  按类型     : %s" % ", ".join("%s=%d" % (k, v) for k, v in sorted(by_kind.items())))
    print("STATUS_OK")
    return 0


def cmd_merge(m, src_dir, fragment):
    if not os.path.isdir(src_dir):
        print("合并源目录不存在: %s" % src_dir, file=sys.stderr)
        return 2
    frag = []
    if fragment:
        frag = json.load(open(fragment, encoding="utf-8"))
        if isinstance(frag, dict):
            frag = frag.get("assets", [])
    # 片段里可以直接带 file（本地绝对/相对路径）字段指向素材本体
    existing = {a["id"]: a for a in m.get("assets", []) if "id" in a}
    added = 0
    for e in frag:
        eid = e.get("id")
        if not eid:
            continue
        fpath = e.get("file")
        if fpath and os.path.exists(fpath):
            base = os.path.basename(fpath)
            dest = os.path.join(SAMPLES_DIR, base)
            os.makedirs(SAMPLES_DIR, exist_ok=True)
            shutil.copyfile(fpath, dest)
            e["sample_file"] = os.path.relpath(dest, SKILL_ROOT).replace("\\", "/")
            e.setdefault("sample_bytes", os.path.getsize(fpath))
        if eid in existing:
            # 已有：仅补充缺失的样本文件指针
            if e.get("sample_file") and not existing[eid].get("sample_file"):
                existing[eid]["sample_file"] = e["sample_file"]
            continue
        m.setdefault("assets", []).append(e)
        existing[eid] = e
        added += 1
    # 重算计数
    samples, bytes_ = 0, 0
    ids = set()
    for a in m["assets"]:
        ids.add(a.get("id"))
        if a.get("sample_file"):
            samples += 1
            bytes_ += a.get("bytes", 0)
    m["unique_assets"] = len(ids)
    m["samples"] = samples
    m["sample_bytes"] = bytes_
    m["total_asset_refs"] = len(m["assets"])
    save_manifest(m)
    print("MERGE_OK  新增 %d 个素材条目；现在唯一 %d / 样本 %d（%.2f MB）"
          % (added, len(ids), samples, bytes_ / 1024 / 1024))
    return 0


def cmd_crawl():
    print("=" * 56)
    print("社区素材爬取【待联网】")
    print("=" * 56)
    print("  当前环境：scratch.mit.edu 不可达、小码王 CDN 直链 403、")
    print("  javascript 注入被屏蔽、Edge dom_cua 会 Blocked/timeout。")
    print("  不要再用这三条自动路径。")
    print("  唯一可行在线取数 = 小码王「保存到电脑」人工流程：")
    print("    1) Edge 打开 world.xiaomawang.com/community/main/compose/{CID}")
    print("    2) 滚到动作栏，点「改编作品」（cua 坐标=截图 x+62，常需连点两次）")
    print("    3) 编辑器「文件」(183,27) → 「保存到电脑」(275,136)")
    print("    4) 静默下载到 Downloads/{标题}.sb3（大型作品可达 5–10 分钟）")
    print("  下载后用 --merge 把素材并入 manifest。")
    print("CRAWL_PENDING_NETWORK")
    return 0


def main():
    ap = argparse.ArgumentParser(description="社区素材扩充（离线 merge / 状态 / 待联网爬取）")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--merge", metavar="DIR", help="并入已下载素材目录")
    ap.add_argument("--fragment", help="manifest 片段 JSON（assets 列表，条目可带 file 字段）")
    ap.add_argument("--crawl", action="store_true", help="【待联网】列出爬取流程")
    args = ap.parse_args()
    m = load_manifest()
    if args.crawl:
        return cmd_crawl()
    if args.merge:
        return cmd_merge(m, args.merge, args.fragment)
    return cmd_status(m)


if __name__ == "__main__":
    sys.exit(main())
