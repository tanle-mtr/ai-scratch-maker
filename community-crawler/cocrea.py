#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共创世界 (CCW / cocrea.world / ccw.site) 爬虫 + 解密。

==================== 原理（逆向结论） ====================
CCW 基于 Gandi IDE，sb3 默认【加密】。开源仓库 https://github.com/OpenCCW 逆向出了全部细节：

  1) sb3 下载直链形如：
        https://m.ccw.site/user_projects_sb3/{userId}/{hash}.sb3
     文件名 {hash}.sb3 的前 32 个字符就是解密密钥材料（见 ccw_crypto.py）。

  2) 解密（见 ccw_crypto.py，已带 --selftest 自检）：
        · 常见情况：zip 头是正常 PK，仅 project.json 被混淆成一段 base64 文本
          （btoa(encodeURIComponent(json)) 后把第 n 个字符挪到末尾、原位置塞哨兵 'bxeygiuc12'[n]）。
          还原：把末尾字符拿回第 n 位 -> atob -> decodeURIComponent。
        · 少见情况：整文件是 base64(AES-CBC(逗号分隔字节))。
          密钥 = b64decode("KzdnFCBRvq3"+文件名前32字符)[:32]，IV = 密钥前16字节。

  3) 作品列表/详情 API（api.cocrea.world / api.ccw.site）【需要登录】，本机浏览器外常返回
     "User not logged in"。因此「热门作品列表」需以下任一方式获取：
        (a) 用户先在浏览器登录 CCW，从网络面板复制作品详情/探索接口，或
        (b) 直接拿一批作品详情页 URL（https://www.ccw.site/detail/{id}）喂给本脚本，或
        (c) discover_explore() 尽力从 ccw.site 页面抓取 detail/{id} 链接（SPA 可能需登录态）。

本模块提供：
  · download_and_decrypt(sb3_url, out_path)        下载并解密单个作品（核心，已验证算法）
  · fetch_detail(project_id)                       尽力取详情（含 userId/hash），可能需要登录态
  · discover_explore()                              尽力从探索页抓作品 id（best-effort）
  · crawl(ids_or_urls, out_dir)                    批量下载+解密+落盘

==================== 用法 ====================
  python cocrea.py decrypt --url "https://m.ccw.site/user_projects_sb3/123/abc...def.sb3" --out ./sb3/abc.sb3
  python cocrea.py crawl  --ids-file ids.txt --out ./sb3/
  python cocrea.py explore --out ids.txt
"""
import sys, os, json, re, time, argparse
try:
    import requests
    _HAVE_REQUESTS = True
except Exception:
    _HAVE_REQUESTS = False
    import urllib.request, urllib.parse, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccw_crypto import decrypt_sb3

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _http_json(url, params=None, headers=None):
    headers = headers or {"User-Agent": UA}
    if _HAVE_REQUESTS:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        return r.status_code, r.text
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    req = urllib.request.Request(url + q, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def download_and_decrypt(sb3_url, out_path):
    """下载加密 sb3 并解密为标准 sb3。"""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    if _HAVE_REQUESTS:
        r = requests.get(sb3_url, headers={"User-Agent": UA}, timeout=120)
        r.raise_for_status()
        data = r.content
    else:
        req = urllib.request.Request(sb3_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    fname = os.path.basename(sb3_url).split("?")[0]
    dec = decrypt_sb3(data, fname)
    with open(out_path, "wb") as f:
        f.write(dec)
    return out_path


def fetch_detail(project_id):
    """尽力取作品详情（可能需登录态，返回 dict 或 None）。"""
    url = f"https://www.ccw.site/detail/{project_id}"
    code, html = _http_json(url, headers={"User-Agent": UA})
    if code != 200:
        # 尝试 api（可能需登录）
        for api in ("https://api.ccw.site/api/project/detail",
                    "https://api.cocrea.world/api/project/detail"):
            c2, txt = _http_json(api, params={"id": project_id})
            if c2 == 200:
                try:
                    return json.loads(txt)
                except Exception:
                    pass
        return None
    # 从页面里尝试抠 sb3 直链 / userId+hash
    m = re.search(r"user_projects_sb3/(\d+)/([0-9a-f]+)\.sb3", html)
    if m:
        return {"userId": m.group(1), "hash": m.group(2),
                "sb3Url": f"https://m.ccw.site/user_projects_sb3/{m.group(1)}/{m.group(2)}.sb3"}
    return None


def discover_explore(max_pages=5, sleep=0.5):
    """尽力从 CCW 探索页抓取作品 id（best-effort，SPA 可能需登录态）。"""
    ids = []
    for pg in range(1, max_pages + 1):
        code, html = _http_json(f"https://www.ccw.site/explore?page={pg}",
                               headers={"User-Agent": UA})
        found = re.findall(r"/detail/(\d+)", html)
        ids.extend(found)
        if code != 200 or not found:
            break
        time.sleep(sleep)
    # 去重
    seen, uniq = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i); uniq.append(i)
    return uniq


def crawl(ids_or_urls, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    ok = 0
    for item in ids_or_urls:
        item = item.strip()
        if not item:
            continue
        # 直接是 sb3 直链
        if item.startswith("http") and item.endswith(".sb3"):
            out = os.path.join(out_dir, os.path.basename(item).split("?")[0])
            try:
                download_and_decrypt(item, out); ok += 1
                print(f"  [OK] {out}")
            except Exception as e:
                print(f"  [失败] {item}: {e}")
            continue
        # 作品 id -> 取详情 -> 下载
        pid = item.split("/detail/")[-1].split("?")[0]
        try:
            det = fetch_detail(pid)
            if not det or not det.get("sb3Url"):
                print(f"  [跳过] {pid}: 无法取得 sb3 直链（可能需要登录态）")
                continue
            out = os.path.join(out_dir, det["hash"] + ".sb3")
            download_and_decrypt(det["sb3Url"], out); ok += 1
            print(f"  [OK] {pid} -> {out}")
        except Exception as e:
            print(f"  [失败] {pid}: {e}")
    print(f"下载解密成功 {ok}/{len(ids_or_urls)} 件 -> {out_dir}")
    return ok


def main():
    ap = argparse.ArgumentParser(description="共创世界 CCW 爬虫+解密")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("decrypt"); p.add_argument("--url", required=True)
    p.add_argument("--out", required=True); p.set_defaults(func=lambda a: print("->", download_and_decrypt(a.url, a.out)))
    p = sub.add_parser("explore"); p.add_argument("--out", required=True)
    p.add_argument("--pages", type=int, default=5)
    p.set_defaults(func=lambda a: open(a.out, "w").write("\n".join(discover_explore(a.pages))))
    p = sub.add_parser("crawl"); p.add_argument("--ids-file", required=True); p.add_argument("--out", required=True)
    p.set_defaults(func=lambda a: crawl(open(a.ids_file, encoding="utf-8").read().splitlines(), a.out))
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help(); return
    args.func(args)


if __name__ == "__main__":
    main()
