#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一入口：爬社区 -> 过滤非 Scratch 积木 -> 精通技巧。

把 xiaomawang / cocrea / scratch_official / filter_scratch_blocks / analyze 串起来。

用法：
  # 小码王：抓全部精选（716 件）元数据，并下载 sb3 到 ./sb3/xmw/
  python run_crawl.py xiaomawang --pages 36 --meta ./data/xmw_featured.json --download --out ./sb3/xmw

  # 共创世界：用一份作品 id/url 清单批量下载解密
  python run_crawl.py cocrea --ids-file ids.txt --out ./sb3/ccw

  # Scratch 官方：抓热门并下载
  python run_crawl.py scratch --limit 40 --out ./sb3/scratch

  # 过滤非 Scratch 积木（单个/批量目录）
  python run_crawl.py filter --in x.sb3 --out x_clean.sb3 --report r.json --strip-ext
  python run_crawl.py filter --dir ./sb3/xmw --out ./sb3/xmw_clean

  # 技巧分析
  python run_crawl.py analyze --in x.sb3
  python run_crawl.py analyze --dir ./sb3/xmw
"""
import sys, os, argparse, glob

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import xiaomawang, cocrea, scratch_official, filter_scratch_blocks, analyze


def cmd_xiaomawang(a):
    meta = a.meta
    os.makedirs(os.path.dirname(os.path.abspath(meta)) or ".", exist_ok=True)
    items = list(xiaomawang.iter_featured(page_size=20, max_pages=a.pages))
    import json
    json.dump({"count": len(items), "items": items}, open(meta, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"元数据 {len(items)} 件 -> {meta}")
    if a.download:
        ok = 0
        for it in items:
            try:
                xiaomawang.download_sb3(it.get("fileKey") or it["compositionId"],
                                       os.path.join(a.out, it["compositionId"] + ".sb3"))
                ok += 1
            except Exception as e:
                print(f"  [跳过] {it['compositionId']}: {e}")
        print(f"下载成功 {ok}/{len(items)} -> {a.out}")


def cmd_cocrea(a):
    ids = open(a.ids_file, encoding="utf-8").read().splitlines()
    cocrea.crawl(ids, a.out)


def cmd_scratch(a):
    items = scratch_official.explore(mode=a.mode, limit=a.limit, query=a.query)
    import json
    os.makedirs(a.out, exist_ok=True)
    ok = 0
    for it in items:
        pid = it.get("id")
        try:
            scratch_official.download_project(pid, os.path.join(a.out, f"{pid}.sb3"))
            ok += 1
        except Exception as e:
            print(f"  [失败] {pid}: {e}")
    json.dump([{"id": i.get("id"), "title": i.get("title")} for i in items],
              open(os.path.join(a.out, "_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"下载成功 {ok}/{len(items)} -> {a.out}")


def cmd_filter(a):
    if a.dir:
        for f in sorted(glob.glob(os.path.join(a.dir, "*.sb3"))):
            out = os.path.join(a.out, os.path.basename(f))
            rep = os.path.join(a.out, "_reports", os.path.basename(f) + ".json")
            filter_scratch_blocks.run(f, out, rep, a.extra_allow, a.strip_ext, a.report_only)
    else:
        filter_scratch_blocks.run(a.inp, a.out, a.report, a.extra_allow, a.strip_ext, a.report_only)


def cmd_analyze(a):
    if a.dir:
        analyze.main.__wrapped__ if False else analyze.analyze  # noop guard
        results = []
        for f in sorted(glob.glob(os.path.join(a.dir, "*.sb3"))):
            results.append(analyze.analyze(f))
        from collections import Counter
        agg = Counter()
        for r in results:
            for k in r["techniques"]:
                agg[k] += 1
        print(f"共 {len(results)} 个作品，各技巧出现作品数：")
        for k, v in agg.most_common():
            print(f"  {k:12s} {v}")
        if a.json:
            import json
            json.dump(results, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    else:
        r = analyze.analyze(a.inp)
        import json
        print(json.dumps(r, ensure_ascii=False, indent=2))
        if a.json:
            json.dump(r, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="社区爬虫·过滤·技巧 统一入口")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("xiaomawang"); p.add_argument("--pages", type=int, default=36)
    p.add_argument("--meta", default="./data/xmw_featured.json"); p.add_argument("--download", action="store_true")
    p.add_argument("--out", default="./sb3/xmw"); p.set_defaults(func=cmd_xiaomawang)
    p = sub.add_parser("cocrea"); p.add_argument("--ids-file", required=True); p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_cocrea)
    p = sub.add_parser("scratch"); p.add_argument("--limit", type=int, default=40)
    p.add_argument("--mode", default="popular"); p.add_argument("--query", default="")
    p.add_argument("--out", default="./sb3/scratch"); p.set_defaults(func=cmd_scratch)
    p = sub.add_parser("filter"); p.add_argument("--in"); p.add_argument("--dir")
    p.add_argument("--out", default="./sb3_clean"); p.add_argument("--report")
    p.add_argument("--extra-allow"); p.add_argument("--strip-ext", action="store_true")
    p.add_argument("--report-only", action="store_true"); p.set_defaults(func=cmd_filter)
    p = sub.add_parser("analyze"); p.add_argument("--in"); p.add_argument("--dir"); p.add_argument("--json")
    p.set_defaults(func=cmd_analyze)
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help(); return
    args.func(args)


if __name__ == "__main__":
    main()
