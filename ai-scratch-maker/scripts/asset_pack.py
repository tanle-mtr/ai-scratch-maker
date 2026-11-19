#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""社区素材包：检索、取用，以及 IR 里 `asset: community:<id>` 的解析。

CLI（在 skill 根目录执行）：
    python scripts/asset_pack.py stats
    python scripts/asset_pack.py search 办公室 --kind backdrop --limit 10
    python scripts/asset_pack.py search 数字方块 --cid NGwJJ66J
    python scripts/asset_pack.py fetch "pGeJJ66J/办公室亮灯" --to examples/assets/community
    python scripts/asset_pack.py resolve "community:2SwJJ66J/体力果"

IR 用法：
    costumes:
      - {asset: "community:2SwJJ66J/体力果"}        # 名称自动取素材原名
      - {name: 我的名字, asset: "community:<id>"}   # 也可覆盖名称
build_sb3.py 会在编译前把 community: 引用展开成实际文件路径。

授权：素材来自小码王社区公开作品，仅供学习参考；对外分发/商用前须回溯原作者授权。
"""
import argparse
import json
import os
import shutil
import struct
import sys
import wave

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GENERATED_DIR = os.path.join(SKILL_ROOT, "assets", "community", "generated")

MANIFEST = os.path.join(SKILL_ROOT, "assets", "community", "manifest.json")
PREFIX = "community:"


def load_manifest():
    if not os.path.exists(MANIFEST):
        raise FileNotFoundError(
            "找不到 assets/community/manifest.json；请先运行 "
            "community-crawler/extract_asset_pack.py 生成资产包")
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def library_root():
    """按优先级找全量素材库；找不到返回 None（此时仍可用 skill 内样本）。"""
    env = os.environ.get("COMMUNITY_ASSET_LIBRARY")
    candidates = [env] if env else []
    candidates += [
        os.path.normpath(os.path.join(SKILL_ROOT, "..", "community-crawler",
                                      "data", "asset_pack", "library")),
        os.path.join(SKILL_ROOT, "assets", "community", "library"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return None


def find_asset(asset_id, manifest=None):
    m = manifest or load_manifest()
    exact = [a for a in m["assets"] if a["id"] == asset_id]
    if exact:
        return exact[0]
    low = asset_id.lower()
    fuzzy = [a for a in m["assets"] if low in a["id"].lower()
             or any(low in (s.get("original_name") or "").lower() for s in a["sources"])]
    if not fuzzy:
        return None
    if len(fuzzy) > 1:
        sys.stderr.write("[提示] '{}' 匹配到 {} 个素材，取第一个；用完整 id 可精确指定\n".format(
            asset_id, len(fuzzy)))
    return fuzzy[0]


def resolve_community_asset(asset_id, manifest=None):
    """把 community:<id> 解析成可读取的绝对文件路径。"""
    a = find_asset(asset_id, manifest)
    if a is None:
        raise FileNotFoundError(
            "资产包里找不到 '{}'；用 `python scripts/asset_pack.py search <关键词>` 查可用 id".format(asset_id))
    if a.get("sample_file"):
        p = os.path.join(SKILL_ROOT, a["sample_file"])
        if os.path.exists(p):
            return p
    root = library_root()
    if root:
        p = os.path.join(root, a["library_file"])
        if os.path.exists(p):
            return p
    # 全新环境降级：样本层与全量库都没有时，生成程序化占位素材，保证构建永不硬崩。
    warn = (
        "[社区素材] 占位降级：'{}' 既不在样本层、也找不到全量素材库，"
        "已生成占位素材（画面/音效为替代内容）。\n".format(asset_id) +
        "  要换上真实素材：① 设置环境变量 COMMUNITY_ASSET_LIBRARY 指向 "
        "community-crawler/data/asset_pack/library；\n"
        "  ② 或把 351MB 全量库解压到 assets/community/library/；"
        "③ 或 python scripts/asset_pack.py fetch '{}' --to examples/assets/community".format(asset_id))
    sys.stderr.write(warn + "\n")
    return generate_placeholder(asset_id, a.get("kind", "costume"),
                                original_name(asset_id, manifest) or asset_id)


def original_name(asset_id, manifest=None):
    a = find_asset(asset_id, manifest)
    if not a:
        return None
    return (a["sources"][0].get("original_name") or os.path.splitext(
        os.path.basename(a["library_file"]))[0])


def _safe_slug(s):
    """把素材 id / 原名压成文件名安全的 slug。"""
    keep = []
    for ch in str(s):
        if ch.isalnum() or ch in "-_":
            keep.append(ch)
        else:
            keep.append("_")
    slug = "".join(keep)
    return slug[:80]


def generate_placeholder(asset_id, kind, label):
    """样本层与全量库都缺失时，生成程序化占位素材，保证构建不中断。

    - costume / backdrop -> 一个带标签的 SVG（合法、能被 Scratch 打开）
    - sound              -> 一段 0.2s 的 440Hz 正弦 WAV
    结果缓存在 assets/community/generated/，按 slug 复用，不重复生成。
    """
    os.makedirs(GENERATED_DIR, exist_ok=True)
    slug = _safe_slug(asset_id)
    if kind == "sound":
        path = os.path.join(GENERATED_DIR, slug + ".wav")
        if not os.path.exists(path):
            _write_sine_wav(path, freq=440, dur=0.2, amp=0.25)
        return path
    # 造型 / 背景：SVG
    path = os.path.join(GENERATED_DIR, slug + ".svg")
    if not os.path.exists(path):
        _write_label_svg(path, label, is_backdrop=(kind == "backdrop"))
    return path


def _write_label_svg(path, label, is_backdrop=False):
    w, h = (480, 360) if is_backdrop else (80, 80)
    fill = "#2b6cb0" if is_backdrop else "#dd6b20"
    txt = (label or "占位")[:18]
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        'viewBox="0 0 {w} {h}">\n'
        '  <rect width="{w}" height="{h}" fill="{fill}"/>\n'
        '  <rect x="4" y="4" width="{w2}" height="{h2}" fill="none" '
        'stroke="#ffffff" stroke-width="3"/>\n'
        '  <text x="{cx}" y="{cy}" font-size="{fs}" fill="#ffffff" '
        'text-anchor="middle" font-family="sans-serif">{txt}</text>\n'
        '</svg>\n'
    ).format(w=w, h=h, w2=w - 8, h2=h - 8, fill=fill,
             cx=w / 2, cy=h / 2 + 6, fs=(28 if is_backdrop else 16), txt=_xml_escape(txt))
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


def _xml_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _write_sine_wav(path, freq=440, dur=0.2, amp=0.25, sr=44100):
    n = int(sr * dur)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            v = int(amp * 32767 * __import__("math").sin(2 * __import__("math").pi * freq * i / sr))
            frames += struct.pack("<h", v)
        wf.writeframes(bytes(frames))


def expand_community_assets(ir, manifest=None):
    """递归把 IR 中所有 asset: community:<id> 展开成绝对路径，并补默认名称。"""
    m = manifest or load_manifest()
    seen = {}

    def conv(v):
        if isinstance(v, dict):
            out = {}
            for k, val in v.items():
                if k == "asset" and isinstance(val, str) and val.startswith(PREFIX):
                    aid = val[len(PREFIX):]
                    path = resolve_community_asset(aid, m)
                    seen[aid] = path
                    out[k] = path
                    if "name" not in v:
                        nm = original_name(aid, m)
                        if nm:
                            out["name"] = nm
                else:
                    out[k] = conv(val)
            return out
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v

    result = conv(ir)
    if seen:
        sys.stderr.write("[社区素材] 展开 {} 个引用\n".format(len(seen)))
    return result


def cmd_stats(m, args):
    print("来源作品 {} 个 / 唯一素材 {} 个（原始引用 {} 次）".format(
        m["source_works"], m["unique_assets"], m["total_asset_refs"]))
    print("skill 内样本 {} 个（{} MB）；全量库 {} 个（{} MB）".format(
        m["samples"], round(m["sample_bytes"] / 1024 / 1024, 2),
        m["unique_assets"] - m["samples"],
        round((sum(a["bytes"] for a in m["assets"]) - m["sample_bytes"]) / 1024 / 1024, 1)))
    root = library_root()
    print("全量素材库：{}".format(root or "未找到（可设置 COMMUNITY_ASSET_LIBRARY）"))


def cmd_search(m, args):
    q = (args.query or "").lower()
    rows = []
    for a in m["assets"]:
        hay = " ".join([a["id"], a["kind"], a["format"]] +
                       [s.get("original_name", "") + " " + s.get("title", "") + " " +
                        s.get("sprite", "") + " " + s.get("cid", "") for s in a["sources"]]).lower()
        if q and q not in hay:
            continue
        if args.kind and a["kind"] != args.kind:
            continue
        if args.cid and not any(s["cid"] == args.cid for s in a["sources"]):
            continue
        rows.append(a)
    print("命中 {} 个{}".format(len(rows), "（显示前 {} 个）".format(args.limit) if len(rows) > args.limit else ""))
    print("id".ljust(46), "类型".ljust(10), "格式".ljust(6), "KB".rjust(8), " 样本", " 来源")
    for a in rows[:args.limit]:
        src = a["sources"][0]
        print(a["id"][:44].ljust(46), a["kind"].ljust(10), a["format"].ljust(6),
              str(round(a["bytes"] / 1024, 1)).rjust(8),
              ("  Y" if a.get("sample_file") else "  -"), " ",
              "{} {}".format(src["cid"], src.get("label") or ""))
    if rows:
        print("\n引用写法（任选一条）：")
        print('  - {asset: "community:' + rows[0]["id"] + '"}')


def cmd_fetch(m, args):
    a = find_asset(args.asset_id)
    if a is None:
        print("找不到素材：{}".format(args.asset_id), file=sys.stderr)
        sys.exit(2)
    root = library_root()
    if not root:
        print("找不到全量素材库；设置 COMMUNITY_ASSET_LIBRARY 后重试", file=sys.stderr)
        sys.exit(2)
    src = os.path.join(root, a["library_file"])
    if not os.path.exists(src):
        print("库内文件缺失：{}".format(src), file=sys.stderr)
        sys.exit(2)
    os.makedirs(args.to, exist_ok=True)
    dst = os.path.join(args.to, os.path.basename(a["library_file"]))
    shutil.copyfile(src, dst)
    print("已取用 -> {}".format(dst))
    print("来源：{} {} {}".format(a["sources"][0]["cid"], a["sources"][0]["title"],
                                a["sources"][0]["url"]))
    print("IR 写法：")
    print('  - {{name: {}, asset: "{}"}}'.format(
        args.name or a["sources"][0].get("original_name") or a["id"].split("/")[-1],
        dst.replace("\\", "/")))


def cmd_resolve(m, args):
    aid = args.asset_id
    if aid.startswith(PREFIX):
        aid = aid[len(PREFIX):]
    print(resolve_community_asset(aid, m))


def main():
    ap = argparse.ArgumentParser(description="社区素材包检索与取用")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("stats", help="资产包概览")
    p = sub.add_parser("search", help="检索素材")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--kind", choices=["backdrop", "costume", "sound"])
    p.add_argument("--cid")
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("fetch", help="从全量库取一个素材到目标目录")
    p.add_argument("asset_id")
    p.add_argument("--to", default="examples/assets/community")
    p.add_argument("--name", help="覆盖 IR 里的默认名称")
    p = sub.add_parser("resolve", help="解析 community:<id> 为实际路径")
    p.add_argument("asset_id")
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return
    m = load_manifest()
    {"stats": cmd_stats, "search": cmd_search, "fetch": cmd_fetch,
     "resolve": cmd_resolve}[args.cmd](m, args)


if __name__ == "__main__":
    main()
