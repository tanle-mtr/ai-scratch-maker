# 失败模式库（Failure-Mode Library）

> 把反复踩过的 IR 坑 + 社区静态臭味（LitterBox）沉淀成「易错点 → 正确写法」速查。
> 每次写 IR 前扫一遍，能省 80% 的构建失败与返工。铁律编号见 `SKILL.md`。

---

## A · IR 语法（直接导致 `build_sb3` 失败）

| 易错点 | 症状 | 正确写法 |
|---|---|---|
| `else` 块另起一行 `- else:` | 构建报「未知积木 / 结构错」 | `else:` 必须放在 `if:` **同列表项**内：`if: {cond:..., do:[...], else:[...]}` |
| 裸 `forever` | 构建报错 / 运行空转 | 每脚本以**帽子**开头；`forever` 内要有 `wait: 0.02` 节流（无头环境用固定 `stepN`） |
| `rotationStyle` 值错 | 角色乱转或构建失败 | 取值仅 `all` / `none` / `left-right`；平台/射击类用 `none` |
| 缺素材文件 | 构建报「找不到 XXX.svg」 | IR 内联 SVG，或确认 `assets:` 路径相对 IR 目录；优先 `make_ui_assets.py` 生成 |
| 颜色写 `#rgb` 三位 | 铁律18 硬拦 | 一律 6 位 `#rrggbb` |
| `and` / `or` 多输入 | 构建只认 2 输入 | 多条件**嵌套**：`and:[{or:[a,b]},c]` |
| `not` 包 `equals` | 结构不符 | `not:` 直接包运算：`not: {equals:[x,y]}` |
| 无参积木写成 `{x: 0}` | 构建误判有参 | 无参用 `{x: null}` 或空字典 |

## B · 铁律相关（构建过但违规 / 观感废）

| 易错点 | 违反 | 正确写法 |
|---|---|---|
| 数字用 `say` 显示 | 铁律1 | 用 `digit_display` 伪积木或舞台变量显示，带文字标签 |
| 长文本用 `say` 气泡聊天 | 铁律2 | 用自制聊天框角色（多行 + 头像 + 不挡操作） |
| 障碍画在背景图里 | 铁律4 | 障碍必须是**独立角色**才有碰撞箱 |
| 克隆体私有变量漏挡本体 | 铁律11 | 用私有 `是克隆`，克隆事件帽内 `if 是克隆==1` 才执行 |
| 菜单用「询问」 | 铁律10 | 用角色按钮 + `当角色被点击` |
| 复位挂绿旗 | 铁律6 | 一切一局要复位的东西挂 `[重置]` 广播，点重试才干净 |
| 结算页缺重玩按钮 | 铁律7 | 结算页必须有「再来一局 / 返回」按钮（最高频遗忘） |
| 摩擦/阻尼用减 | 铁律5 | 一律用「乘」（减法会反向加速飞走） |
| 重力取正 | 铁律8 | y+ 朝上 → 重力取负 |
| SVG 含禁用标签 | 铁律17 | 禁 `text/filter/mask/clipPath/pattern/image/foreignObject` |
| 冷灰 / 深绿填充 | 铁律8/§198 | 冷灰（B≫R 且 R≈G）禁止；深绿 `#216E09`/深蓝绿 `#2F7365` 仅限文字 |
| 障碍角色没被任何碰撞引用 | 铁律19 | 命名为 墙/障碍/围栏/栅栏/障碍物 的角色必须被碰撞检测引用，否则只是画上去 |
| 音效互打断 / UI 用「直到结束」 | 铁律18 | 音效克隆跑；UI 音效 ≤0.25s |

## C · 性能 / 静态臭味（LitterBox 对应，新增脚本辅助）

| 臭味 | 表现 | 规避 |
|---|---|---|
| **Long Script** | 单脚本积木过多，难维护 | 拆成广播子程序（见 `ir-patterns.md` P1/P8） |
| **Busy Waiting** | `repeat` 内 `wait` ≤0.03s，抢占整角色 | 定时重复改用**计时器 / 帧计数**，不要极小 wait 空转 |
| **Missing Termination** | `repeat` 无终止条件 / `forever` 内无出口 | 循环必有退出（计数到 0 / 离屏 `delete_clone_of`） |
| **Duplicated Script** | 多角色脚本几乎一致 | 抽到「主控 + 广播」，避免复制粘贴 |
| **Call Without Definition** | 调用了未定义的广播/变量 | 构建前 grep 广播名是否都有发射点 |
| **Missing Resource** | 引用了不存在的造型/音效 | `build_sb3` 会报；用 `make_ui_assets.py` 生成避免路径错 |
| **Comparing Literals** | 用字面量比较而非变量 | 状态比较走变量（如 `游戏状态=="游戏"`），便于调试 |
| **克隆无限堆积** | 飞出屏不删 / 隐形循环克隆 | 见 `ir-patterns.md` P6：离屏即删，静默上限 300（铁律12） |

## D · 验收侧已知误报（已修，记一笔防再踩）

- **孤儿 SVG 假阳性**：构建会把共享 UI-Kit 资源作为孤儿 SVG 打进每个 .sb3；`quality_gate.py` 已改为只扫被 `project.json` 引用的 SVG（铁律17 的 `!` 同源 WARN 非致命）。若某作品仍报配色违规，先确认是「被引用 SVG」还是孤儿。
- **L2/L4 解压路径**：Git Bash 的 `/tmp` 原生 Windows python 不认；抽取 `project.json` 用 `python -c "tempfile.mkdtemp()"` 生成 Windows 绝对路径。
- **Long Script 阈值拍脑袋**：`check_perf_budget.py` 原设 120 块，全量 56 作品一跑误报 13 个（platformer 主循环 280 块、cat_mouse 166 块都是健康平铺）。已放宽到 300。**任何启发式阈值上线前先跑全量看分布**，别无脑信经验值。
- **WARN 分支漏机器令牌**：检查器只有 `XXX_OK` 令牌、没有 `XXX_WARN`，编排器 grep 不到就会把「有建议」静默当成「没结论」。凡 `--strict` 能返回 1 的脚本，WARN 分支必须同时打令牌。

## E · 已知既有欠债（不是新缺陷，改前先评估）

> 这些是历史作品里真实存在、但**已被八层+门禁放行**的软性问题（因为它们是 WARN 级）。
> 别把 `check_a11y.py` / `check_perf_budget.py --strict` 报出来的这些当成"刚刚弄坏的"。

| 作品 | 现象 | 性质 |
|---|---|---|
| `showcase_band` | 14 个「方块N」造型 SVG 含 `<text>` 写数字 | Scratch 原生 scratch-paint 导出（带 `data-paper-data`），铁律17 边界：角色上写数字 vs UI 面板禁 text。要改需重做造型，风险高 |
| `fruit_basket` | 2 个水果 SVG 含 `<text>`；红/绿系同现 | 同上；红绿是苹果+叶子的自然配色，非"信息只靠颜色" |
| `story` | 2 个按钮 SVG 含 `<text>`（btnA/btnB） | 同上 |
| `ato_train` / `board_gomoku` | 单脚本 401 / 1349 块 | 大状态机/棋盘判定，属合理长脚本，拆子程序收益有限 |

> 处理原则：新作品一律按 `ir-patterns.md` 写（不用 text、不用红绿单通道），
> 既有欠债只在"顺重重做该作品"时一并修，不为指标好看去动已验收的资产。

> 发现新坑就往这里补一行；本库与 `ir_schema.py` 的行号报错、`check_hard_rules.mjs` 的 9 条铁律互为表里。
