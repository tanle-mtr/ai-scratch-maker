#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scratch 官方社区 (scratch.mit.edu) 爬虫。

==================== 原理 ====================
Scratch 官方有干净的公开 API（无需登录）：
  · 探索/热门作品列表：
      GET https://api.scratch.mit.edu/explore/projects?limit=N&mode=popular&language=en
      mode 还可取 top_remixed / recent 等；q= 关键词搜索。
      返回 [{id, title, author:{username}, ...}]
  · 下载 sb3：官方 https://projects.scratch.mit.edu/{id}/ 偶有限流；更稳的是 TurboWarp CDN：
      https://cdn2.turbowarp.org/{id}.sb3   （TurboWarp 镜像，CORS 友好、速度快）
  · 注：scratch.mit.edu 上的作品不能直接加自定义扩展，所以「非 Scratch 积木」极少见；
       本模块主要价值是『热门作品素材库』+ 配合 filter / analyze 学技巧。

==================== 用法 ====================
  python scratch_official.py explore --limit 40 --mode popular --out ./data/scratch_popular.json
  python scratch_official.py crawl   --limit 40 --mode popular --out ./sb3/
"""
import sys, os, json, time, argparse
try:
    import requests
    _HAVE_REQUESTS = True
except Exception:
    _HAVE_REQUESTS = False
    import urllib.request, urllib.parse, urllib.error

API = "https://api.scratch.mit.edu"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _get_json(url, params=None):
    if _HAVE_REQUESTS:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        return r.json()
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    req = urllib.request.Request(url + q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def explore(mode="popular", limit=40, query=""):
    """返回热门/分类作品列表（id, title, author）。"""
    items = []
    while len(items) < limit:
        take = min(40, limit - len(items))
        params = {"limit": take, "mode": mode, "language": "en"}
        if query:
            params["q"] = query
        page = _get_json(f"{API}/explore/projects", params=params)
        if not page:
            break
        items.extend(page)
        time.sleep(0.2)
    return items[:limit]


def download_project(project_id, out_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    url = f"https://cdn2.turbowarp.org/{project_id}.sb3"
    if _HAVE_REQUESTS:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=120)
        r.raise_for_status()
        data = r.content
    else:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def cmd_explore(args):
    items = explore(mode=args.mode, limit=args.limit, query=args.query)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(items)} 件热门作品元数据 -> {args.out}")


def cmd_crawl(args):
    items = explore(mode=args.mode, limit=args.limit, query=args.query)
    os.makedirs(args.out, exist_ok=True)
    meta = []
    ok = 0
    for it in items:
        pid = it.get("id")
        title = (it.get("title") or "").replace("/", "_")
        author = it.get("author", {}).get("username", "unknown") if isinstance(it.get("author"), dict) else "unknown"
        try:
            p = download_project(pid, os.path.join(args.out, f"{pid}.sb3"))
            ok += 1
            meta.append({"id": pid, "title": title, "author": author, "file": f"{pid}.sb3"})
        except Exception as e:
            print(f"  [失败] {pid}: {e}")
    with open(os.path.join(args.out, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"下载成功 {ok}/{len(items)} 件 -> {args.out}")


def main():
    ap = argparse.ArgumentParser(description="Scratch 官方社区爬虫")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("explore"); p.add_argument("--limit", type=int, default=40)
    p.add_argument("--mode", default="popular"); p.add_argument("--query", default="")
    p.add_argument("--out", required=True); p.set_defaults(func=cmd_explore)
    p = sub.add_parser("crawl"); p.add_argument("--limit", type=int, default=40)
    p.add_argument("--mode", default="popular"); p.add_argument("--query", default="")
    p.add_argument("--out", required=True); p.set_defaults(func=cmd_crawl)
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help(); return
    args.func(args)


if __name__ == "__main__":
    main()
