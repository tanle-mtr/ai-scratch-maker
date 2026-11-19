#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小码王社区 (world.xiaomawang.com / m-world.xiaomawang.com) 爬虫。

==================== 原理（逆向结论） ====================
小码王社区是 Next.js SPA。作品列表/详情数据全部来自后端 JSON API，不经过页面 HTML：
  · API 主机： https://community-api.xiaomawang.com   （注意带横线，communityapi 不带横线会被拒）
  · 作品（composition）相关端点（均为 GET + query 参数）：
      GET /api/v1/composition/get-choice-list?page=N&pageSize=M   # 精选/编辑精选（共 716 件，total 字段给出）
      GET /api/v1/composition/get-discovery-list?tagId=T&page=N&pageSize=M  # 按分类（tagId）的发现流
      GET /api/v1/composition/get-info?compositionId=XXXX         # 单作品详情（含 fileKey=直链）
      GET /api/v1/composition/get-other-list?compositionId=XXXX   # 相关作品
  · 每条作品关键字段：
      compositionId : 7 位作品 ID（如 yvF6J66J），详情页 URL = https://m-world.xiaomawang.com/main/project/{compositionId}
      title / description / coverKey(封面) / fileKey(sb3 直链) / tags / statObject(浏览·点赞) / userObject(作者)
      createTime / publishTime / isRecommend / isTop

==================== sb3 下载 ====================
作品 sb3 直链在 fileKey 字段，形如 https://community-wscdn.xmwol.com/composition/{hash}.sb3 。
注意：该 CDN 有 WAF，非浏览器客户端（含机房 IP）常返回 403。
  → 从本机/浏览器环境运行通常正常；若遇 403，请带上浏览器 Cookie/Referer 或用浏览器手动下载。
  本模块已内置浏览器 UA + Referer，但机房 IP 仍可能被拦，属正常现象。

==================== 用法 ====================
  python xiaomawang.py featured  --pages 36 --out ./data/xmw_featured.json
  python xiaomawang.py info     --id yvF6J66J
  python xiaomawang.py download --id yvF6J66J --out ./sb3/
  python xiaomawang.py crawl    --pages 36 --out ./sb3/ --meta ./data/xmw_featured.json
"""
import sys, os, json, time, argparse

try:
    import requests
    _HAVE_REQUESTS = True
except Exception:
    _HAVE_REQUESTS = False
    import urllib.request, urllib.parse, urllib.error

API_BASE = "https://community-api.xiaomawang.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _http_get(path: str, params: dict):
    url = API_BASE + path
    if _HAVE_REQUESTS:
        r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        return r.json()
    else:
        q = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{url}?{q}", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))


def fetch_choice_list(page=1, page_size=20):
    """精选作品列表（编辑精选，total≈716）。"""
    d = _http_get("/api/v1/composition/get-choice-list",
                  {"page": page, "pageSize": page_size})
    if d.get("code") != 0:
        raise RuntimeError(f"get-choice-list 失败: {d.get('message')}")
    return d["data"]


def fetch_discovery_list(tag_id, page=1, page_size=20):
    """按 tagId 的发现流（分类浏览）。"""
    d = _http_get("/api/v1/composition/get-discovery-list",
                  {"tagId": tag_id, "page": page, "pageSize": page_size})
    if d.get("code") != 0:
        raise RuntimeError(f"get-discovery-list 失败: {d.get('message')}")
    return d["data"]


def fetch_info(composition_id):
    """单作品详情（含 fileKey 直链）。"""
    d = _http_get("/api/v1/composition/get-info",
                  {"compositionId": composition_id})
    if d.get("code") != 0:
        raise RuntimeError(f"get-info 失败: {d.get('message')}")
    return d["data"]


def iter_featured(page_size=20, max_pages=None, sleep=0.3):
    """生成器：翻页遍历全部精选作品元数据（不下载 sb3）。"""
    page = 1
    seen = 0
    while True:
        data = fetch_choice_list(page=page, page_size=page_size)
        total = data.get("total", 0)
        items = data.get("list", [])
        if not items:
            break
        for it in items:
            yield it
            seen += 1
        if max_pages and page >= max_pages:
            break
        if page * page_size >= total:
            break
        page += 1
        if sleep:
            time.sleep(sleep)


def download_sb3(file_key_or_id, out_path, referer="https://m-world.xiaomawang.com/"):
    """下载 sb3。file_key 为直链；若传 compositionId 则先取详情。"""
    if file_key_or_id.startswith("http"):
        url = file_key_or_id
    else:
        url = fetch_info(file_key_or_id).get("fileKey")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    headers = {"User-Agent": UA, "Referer": referer, "Origin": "https://m-world.xiaomawang.com"}
    if _HAVE_REQUESTS:
        r = requests.get(url, headers=headers, timeout=60)
        if r.status_code == 403:
            raise RuntimeError("CDN 返回 403（WAF 拦截非浏览器/机房 IP）。请在本机浏览器环境运行，或手动带上 Cookie 下载。")
        r.raise_for_status()
        data = r.content
    else:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path


def cmd_featured(args):
    out = args.out
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    items = list(iter_featured(page_size=args.page_size, max_pages=args.pages))
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"count": len(items), "items": items}, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(items)} 件精选作品元数据 -> {out}")


def cmd_info(args):
    info = fetch_info(args.id)
    print(json.dumps(info, ensure_ascii=False, indent=2))


def cmd_download(args):
    p = download_sb3(args.id, args.out)
    print(f"已下载 -> {p}")


def cmd_crawl(args):
    meta = args.meta
    os.makedirs(os.path.dirname(os.path.abspath(meta)) or ".", exist_ok=True)
    items = list(iter_featured(page_size=args.page_size, max_pages=args.pages))
    with open(meta, "w", encoding="utf-8") as f:
        json.dump({"count": len(items), "items": items}, f, ensure_ascii=False, indent=2)
    print(f"元数据 {len(items)} 件 -> {meta}")
    ok = 0
    for it in items:
        cid = it["compositionId"]
        try:
            download_sb3(it.get("fileKey") or cid, os.path.join(args.out, f"{cid}.sb3"))
            ok += 1
        except Exception as e:
            print(f"  [跳过] {cid} 下载失败: {e}")
    print(f"实际下载成功 {ok}/{len(items)} 件 -> {args.out}")


def main():
    ap = argparse.ArgumentParser(description="小码王社区爬虫")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("featured"); p.add_argument("--pages", type=int, default=36)
    p.add_argument("--page-size", type=int, default=20); p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_featured)
    p = sub.add_parser("info"); p.add_argument("--id", required=True); p.set_defaults(func=cmd_info)
    p = sub.add_parser("download"); p.add_argument("--id", required=True); p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_download)
    p = sub.add_parser("crawl"); p.add_argument("--pages", type=int, default=36)
    p.add_argument("--page-size", type=int, default=20); p.add_argument("--out", required=True)
    p.add_argument("--meta", required=True); p.set_defaults(func=cmd_crawl)
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help(); return
    args.func(args)


if __name__ == "__main__":
    main()
