# 社区 Scratch 作品爬虫 · 过滤 · 技巧精通 工具箱

把各 Scratch 社区的热门优秀作品**爬下来 → 过滤掉不是 Scratch 的积木 → 读薄成技巧清单**，
用于借鉴/教学/二次创作。本目录是一套可运行的 Python 工具。

---

## 0. 目录结构

```
community-crawler/
├── README.md                 # 本文件（原理 + 用法）
├── xiaomawang.py             # 小码王社区爬虫（已验证 API）
├── cocrea.py                 # 共创世界 CCW 爬虫 + 解密
├── ccw_crypto.py             # CCW sb3 解密（project.json 混淆 + 整文件 AES-CBC），含 --selftest
├── scratch_official.py       # Scratch 官方社区爬虫（公开 API）
├── filter_scratch_blocks.py  # 过滤非 Scratch 积木（核心复用件）
├── analyze.py                # 提取作品用到的进阶技巧
├── run_crawl.py              # 统一入口
├── data/                     # 爬到的元数据（如 xmw_featured.json = 716 件精选）
└── demo/                     # 本地作品过滤演示（filtered/ + reports/）
```

依赖：`requests`（可选，缺则回退 urllib）；CCW 整文件 AES 路径需要 `pip install pycryptodome`（常见路径无需）。

---

## 1. 小码王社区（world.xiaomawang.com）—— 原理与代码

### 1.1 原理（逆向结论）
小码王社区是 **Next.js SPA**，作品数据全部来自后端 JSON API，页面 HTML 里没有作品列表。
通过读它的 H5 前端 bundle（`communityh5/.../main.*.chunk.js`）定位到真实接口：

- **API 主机**：`https://community-api.xiaomawang.com`
  ⚠️ 注意带横线。`communityapi.xiaomawang.com`（不带横线）会被拒（`页面不存在`），必须用 `community-api`。
- **作品（composition）端点，均为 `GET` + query 参数**：
  | 端点 | 作用 |
  |---|---|
  | `/api/v1/composition/get-choice-list?page=N&pageSize=M` | **精选/编辑精选**（共 716 件，`total` 字段给出） |
  | `/api/v1/composition/get-discovery-list?tagId=T&page=N&pageSize=M` | 按分类（tagId）的发现流 |
  | `/api/v1/composition/get-info?compositionId=XXXX` | 单作品详情（含 `fileKey` 直链） |
  | `/api/v1/composition/get-other-list?compositionId=XXXX` | 相关作品 |
- **每条作品关键字段**：`compositionId`（7 位 ID，如 `yvF6J66J`；详情页 `https://m-world.xiaomawang.com/main/project/{compositionId}`）、`title`、`description`、`coverKey`（封面）、`fileKey`（**sb3 直链**）、`tags`、`statObject`（`viewCount`/`likeCount`/`commentCount`/`collectCount`）、`userObject`（作者）、`createTime`、`isRecommend`、`isTop`、`cloudVariableNum`。
- **sb3 下载直链**：`fileKey` 形如 `https://community-wscdn.xmwol.com/composition/{hash}.sb3`。
  ⚠️ 该 CDN 有 WAF，**非浏览器/机房 IP 常被拦 403**。从本机浏览器环境运行通常正常；
  若 403，请带上浏览器 Cookie/Referer，或浏览器手动另存为。脚本已内置浏览器 UA+Referer。

### 1.2 代码与运行
```bash
# 抓全部精选（716 件）元数据 -> data/xmw_featured.json
python xiaomawang.py featured --pages 36 --out ./data/xmw_featured.json

# 看单个作品详情
python xiaomawang.py info --id yvF6J66J

# 下载单个作品 sb3（需浏览器环境，否则可能 403）
python xiaomawang.py download --id yvF6J66J --out ./sb3/xmw/yvF6J66J.sb3

# 一键：抓元数据 + 批量下载
python xiaomawang.py crawl --pages 36 --meta ./data/xmw_featured.json --out ./sb3/xmw
```

---

## 2. 共创世界 CCW（cocrea.world / ccw.site）—— 原理与代码

### 2.1 原理（逆向自开源仓库 github.com/OpenCCW）
CCW 基于 **Gandi IDE**，sb3 **默认加密**。开源社区已完整逆向：

- **sb3 直链**：`https://m.ccw.site/user_projects_sb3/{userId}/{hash}.sb3`
  文件名 `{hash}.sb3` 的**前 32 个字符就是解密密钥材料**。
- **解密（见 `ccw_crypto.py`，已 `python ccw_crypto.py --selftest` 自检）**：
  1. **常见情况（占绝大多数）**：zip 头是正常 `PK`，仅 `project.json` 被混淆成一段 base64 文本。
     加密时：`s = btoa(encodeURIComponent(json))`；`n = len(s)%10`；
     `stored = s[:n] + 'bxeygiuc12'[n] + s[n+1:] + s[n]`（把第 n 个字符挪到末尾，原位塞哨兵字符）。
     解密：把末尾字符拿回第 n 位 → `atob` → `decodeURIComponent` 即得原 JSON。
  2. **少见情况（整文件加密）**：整个文件是 `base64( AES-CBC( 逗号分隔十进制字节 ) )`。
     - 密钥 = `b64decode("KzdnFCBRvq3" + 文件名前32字符)[:32]`
     - IV = 密钥前 16 字节
     - AES-CBC 解密后得到「逗号分隔的十进制字节」字符串，按逗号 split 即为真正的 zip 字节。
     （此路径需要 `pycryptodome`；脚本在命中该路径且缺库时会明确报错。）
- **作品列表/详情 API**：`api.cocrea.world` / `api.ccw.site` **需要登录**，非登录态返回
  `"User not logged in"`。因此「热门作品列表」需以下任一方式获取（见 `cocrea.py` 注释）：
  (a) 浏览器登录后从网络面板复制接口/数据；或
  (b) 直接拿一批作品详情页 URL（`https://www.ccw.site/detail/{id}`）喂给脚本；或
  (c) `python cocrea.py explore --out ids.txt` 尽力从探索页抓 `detail/{id}`（SPA，可能需登录态）。

### 2.2 代码与运行
```bash
python ccw_crypto.py --selftest     # 先验证解密算法无误

# 下载并解密单个作品
python cocrea.py decrypt --url "https://m.ccw.site/user_projects_sb3/123/abc123....def.sb3" --out ./sb3/ccw/abc.sb3

# 批量：ids.txt 每行一个 作品id 或 直链
python cocrea.py crawl --ids-file ids.txt --out ./sb3/ccw

# 尽力抓取探索页作品 id
python cocrea.py explore --out ids.txt
```

---

## 3. Scratch 官方社区（scratch.mit.edu）—— 原理与代码

Scratch 官方有干净公开 API（无需登录）：
- **热门/分类列表**：`GET https://api.scratch.mit.edu/explore/projects?limit=N&mode=popular&language=en`
  （`mode` 还可取 `top_remixed`/`recent`；`q=` 关键词搜索）。返回 `[{id,title,author:{username},...}]`。
- **下载 sb3**：官方 `https://projects.scratch.mit.edu/{id}/` 偶有限流；更稳用 **TurboWarp CDN**
  `https://cdn2.turbowarp.org/{id}.sb3`（CORS 友好、快）。
- 注：scratch.mit.edu 作品不能加自定义扩展，「非 Scratch 积木」极少见；本模块主要做热门素材库 + 配合 analyze 学技巧。

```bash
python scratch_official.py explore --limit 40 --mode popular --out ./data/scratch_popular.json
python scratch_official.py crawl   --limit 40 --mode popular --out ./sb3/scratch
```

---

## 4. 过滤「不是 Scratch 的积木」（filter_scratch_blocks.py）

### 4.1 原理
Scratch 3 的 `project.json` 里，每个积木有 `opcode = <namespace>_<blockName>`：
- **核心分类**：`motion / looks / sound / event / control / sensing / operator / data / procedures / argument`
- **官方内置扩展**（scratch.mit.edu 自带）：`pen / wedo2 / music / text2speech / translate / makeymakey / microbit(mbit) / ev3 / boost / videoSensing`

`namespace` 在白名单内 → 保留；否则即「不是 Scratch 的积木」（如小码王的云变量扩展 `xiaoma`、
CCW/Gandi 的 MMO/物理/云库等自定义扩展、`enhance`、`note`、`skyhigh173JSON` 等）→ **删除**。

删除时做「积木图手术」避免工程崩坏：
1. 把被删积木的 `next` 指针交给它的前驱（`prev.next = deleted.next`）；
2. 以被删积木为 `parent` 的子积木重挂到祖父（`parent = deleted.parent`，祖父为空则置为顶层并继承坐标）；
3. 清掉其它积木 `inputs/fields/mutations` 里对被删积木的引用；
4. 解除指向被删积木的评论；
5. `--strip-ext` 时把 `project.extensions` 里非白名单条目一并删掉。

### 4.2 运行
```bash
# 过滤单个文件，输出清洗后 sb3 + 报告
python filter_scratch_blocks.py in.sb3 --out out.sb3 --report r.json --strip-ext

# 只出报告不落盘
python filter_scratch_blocks.py in.sb3 --report-only --report r.json

# 想额外保留某些 mod 扩展（如 TurboWarp 常见扩展）
python filter_scratch_blocks.py in.sb3 --extra-allow mqtt,makeymakey --out out.sb3
```

> 实测：本地 41 个作品里 8 个含真正的非 Scratch 积木，命名空间为 `xiaoma`/`enhance`/`note`/`skyhigh173JSON`；
> 过滤后输出仍是合法 sb3，且这些命名空间清零。`demo/filtered/` 已附两个示例（韵律·音轨、2D联机枪战）。

---

## 5. 技巧精通（analyze.py）

把作品「读薄」：统计角色数、积木数、变量/列表、广播种类，并标出用到的进阶技巧
（克隆、广播解耦、自制积木、画笔、音乐、列表即数据结构、云变量、物理/数学运算、键鼠交互等）。

```bash
python analyze.py "E:/编程作品/作品/素材/Minecraft 3D v0.6.sb3"
# -> sprites=18, blocks=41700, variables=885, lists=422, customBlocks=4371, 列表即数据结构=2625 ...

python analyze.py ./sb3/xmw/          # 批量目录汇总各技巧出现频次
```

---

## 6. 统一入口（run_crawl.py）

```bash
python run_crawl.py xiaomawang --pages 36 --meta ./data/xmw_featured.json --download --out ./sb3/xmw
python run_crawl.py cocrea     --ids-file ids.txt --out ./sb3/ccw
python run_crawl.py scratch    --limit 40 --out ./sb3/scratch
python run_crawl.py filter     --dir ./sb3/xmw --out ./sb3/xmw_clean --strip-ext
python run_crawl.py analyze     --dir ./sb3/xmw
```

---

## 7. 注意事项（合规）
- 爬取仅供**个人学习/借鉴技巧**，请遵守各社区《用户协议》，控制频率（脚本已内置 0.2~0.5s 间隔），
  不要对服务器施压，不要用于商业转售/搬运。
- 小码王 CDN、CCW 列表接口均有访问限制/登录门槛，属正常防护；请在自己浏览器环境运行或依规登录。
- 解密 CCW sb3 仅用于**离线学习其实现技巧**，请尊重原作者著作权。
