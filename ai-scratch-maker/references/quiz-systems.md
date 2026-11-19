# 第十册：答题 / 测验系统（§106–§110）

> 面向「选择题、判断题、测验、闯关答题」类作品的一整套可照抄范式。
> 配套可运行工程：`examples/quiz.yaml`（4 题选择题）、
> 行为校验 `scripts/quiz_behavior_check.mjs`、生成器 `deploy-tools/gen_quiz.py`。
>
> **本册所有结论都经过 scratch-vm 实跑验证**（`QUIZ_LOGIC_OK`），
> 不是纸上推演。§109 的三个坑是会真实让游戏卡死/算错的，务必先看。

---

## 106. 状态机总览：一局答题只有 4 个状态

```
game_state: 0 首页  →  1 答题中  →  2 反馈中  →  3 结算
                          ↑            │
                          └── 下一题 ──┘
```

配套变量（全部放 **stage 全局**，跨角色读写）：

| 变量 | 作用 |
| --- | --- |
| `game_state` | 状态机，所有输入都按它过滤 |
| `题号` | 当前题，**从 1 开始**（Scratch 列表是 1-based） |
| `题目总数` | 用于越界判断 |
| `当前选项` | 玩家刚点的选项序号 1..4，由按钮角色写入 |
| `已答` | **防连点锁**，0=可答 / 1=已提交 |
| `分数` / `答对数` / `连对` / `最高连对` | 统计 |

### 广播链路（全部集中在舞台判题，按钮只发号）

```
当收到 [开始答题]        → broadcast [重置]
当收到 [重置]            → 复位所有变量 + broadcast [出题]
当收到 [出题]            → game_state=1, 已答=0, 当前选项=0   （题板角色同时换造型）
选项按钮被点击           → 若 已答=0 且 game_state=1：设 当前选项=N + broadcast [提交答案]
当收到 [提交答案]        → 上锁 → 判题 → 反馈 → wait → broadcast [下一题]
当收到 [下一题]          → 题号+1 → 越界则 broadcast [结算]，否则 broadcast [出题]
当收到 [结算]            → game_state=3，显示结算牌
```

> **复位必须挂「当收到 [重置]」，不能挂绿旗**（见第三册 §45.3）。
> 绿旗只在启动时触发一次；玩家想「再玩一次」必须能重新复位。

---

## 107. 题库：平行列表 + 造型名列表，加题不改脚本

Scratch 没有「结构体」，用**平行列表**（同一索引代表同一题）：

```yaml
stage:
  lists:
    正确答案: [2, 3, 1, 4]            # 每题正确选项的序号 1..4
    题板名:   [题1, 题2, 题3, 题4]    # 题板角色的造型名
```

题目文本**画进造型图**（Scratch 没有「设置文字」积木）：
用 `scripts/make_ui_assets.py panel` 或 `chatlines` 生成 `q1.png … qN.png`，
一行题干 + 一行四个选项，题板角色挂 N 套造型。

出题时按题号取造型名：

```yaml
- when_receive: { message: 出题 }
- switch_costume:
    costume: { item_of_list: { index: { var: 题号 }, list: 题板名 } }
- show: null
```

**加一道题** = 加 1 张图 + 2 行列表数据，**脚本一行都不用改**。

四个选项按钮是固定角色 A/B/C/D（各一张字母图），不是每题一套。

---

## 108. 判题与计分：索引比较，绝不比文本

```yaml
- when_receive: { message: 提交答案 }
- if:
    cond: { and: [ { equals: [ { var: 已答 }, 0 ] },
                   { equals: [ { var: game_state }, 1 ] } ] }
    do:
      - set_variable: { var: 已答, value: 1 }        # 先上锁，再做任何事
      - set_variable: { var: game_state, value: 2 }
      - if_else:
          cond:
            equals:
              - { var: 当前选项 }
              - { item_of_list: { index: { var: 题号 }, list: 正确答案 } }
          do:
            - change_variable: { var: 分数, by: 10 }
            - change_variable: { var: 答对数, by: 1 }
            - change_variable: { var: 连对, by: 1 }
            - if:
                cond: { gt: [ { var: 连对 }, { var: 最高连对 } ] }
                do: [ { set_variable: { var: 最高连对, value: { var: 连对 } } } ]
            - broadcast: { message: 答对了 }
          else:
            - set_variable: { var: 连对, value: 0 }
            - broadcast: { message: 答错了 }
      - wait: 1.0                                  # 反馈停留
      - broadcast: { message: 下一题 }
```

**为什么用索引不比文本**：玩家点的是按钮，天然得到序号；
比文本要处理大小写、全半角、首尾空格、数字 `2` 与字符串 `"2"`，
每一条都是静默算错的机会。

**越界检查必须在读列表之前**：

```yaml
- when_receive: { message: 下一题 }
- change_variable: { var: 题号, by: 1 }
- if_else:
    cond: { gt: [ { var: 题号 }, { var: 题目总数 } ] }
    do:   [ { set_variable: { var: game_state, value: 3 } },
            { broadcast: { message: 结算 } } ]
    else: [ { broadcast: { message: 出题 } } ]
```

Scratch 读越界列表项**不报错，返回空串** —— 不先判断就会拿空串去比，静默算成「答错」。

---

## 109. ★ 三个致命坑（实测复现过，不是理论）

### 109.1 广播会重启同名帽子线程 → 反馈期间的重复点击会**卡死整局**

这是答题系统最隐蔽的坑。**Scratch 的 `broadcast` 启动帽子时，若同一帽子已有线程在跑，
会先杀掉旧线程再新建。** 判题脚本里含 `wait 1.0`，正处在 yield 状态：
玩家在反馈期间再点一次选项 → 又广播 `[提交答案]` → **正在 wait 的判题线程被杀掉** →
`broadcast [下一题]` 永远不执行 → 游戏停在 `game_state=2` 不动了。

❌ 错误做法：把「已答」锁只放在舞台判题脚本里（来不及，广播已经发出）。

✅ 正确做法：**把锁前移到按钮侧，锁住时连广播都不发**：

```yaml
- when_this_sprite_clicked: null
- if:
    cond: { and: [ { equals: [ { var: 已答 }, 0 ] },
                   { equals: [ { var: game_state }, 1 ] } ] }
    do:
      - set_variable: { var: 当前选项, value: 2 }   # B 按钮固定写 2
      - broadcast: { message: 提交答案 }
```

舞台判题脚本里**仍保留同一把锁**（双保险），但关键是按钮侧这道。

> 通用规律：**凡是在「带 wait 的脚本」里等消息，就要防止该消息被重复广播**。
> 更彻底的做法是把「提交」和「推进」拆成不同消息，或用 `broadcast_and_wait`。

### 109.2 无头校验不会推进虚拟时钟 → 含 `wait` 的作品验证是「假通过」

`control_wait` 的 Timer 读的是 `runtime.currentMSecs`（**虚拟时钟**，见
scratch-vm `src/engine/block-utility.js` 的 `_nowObj`），不是 `Date.now()`。
无头环境没有 RAF ticker，只调 `runtime._step()` 时这个值永远不动 →
`wait` 永不结束，脚本后半段根本没跑，但校验照样报「通过」。

`scripts/smoke_test.mjs` 与 `scripts/quiz_behavior_check.mjs` **已修**，
按真实经过时间 1:1 推进：

```js
const baseMSecs = vm.runtime.currentMSecs || Date.now();
vm.runtime.currentMSecs = baseMSecs + (Date.now() - startedAt);
```

改别的无头校验脚本时，别忘了这一句。

### 109.3 复位挂绿旗、日志靠变量监视器

- 复位挂绿旗 → 玩家点「再来一局」时分数/题号不会清零。**挂 `[重置]` 广播**。
- 分数用变量监视器 → 舞台角落一个小框，做进 UI 很难看。用 `digit_display`
  声明式配置（见 SKILL.md §五）。

### 109.4 其它易踩点

| 坑 | 后果 | 解法 |
| --- | --- | --- |
| 用 `ask` / `answer` 做输入 | 阻塞脚本；无头/嵌入环境不可用；字符串比较一堆坑 | 点击选项按钮 + 广播（§77 架构） |
| `if` 里写 `else` | else 分支静默丢弃 | 用 `if_else` + `do` / `else` |
| 算术/逻辑写 3 个操作数 | 第 3 项起静默丢弃 | 嵌套成两层两输入 |
| 题号从 0 开始 | 取到第 0 项（空） | Scratch 列表是 **1-based** |
| 结算后按钮仍可点 | 越界后继续判题 | `game_state=3` 后隐藏按钮（按钮侧锁也会拦） |

---

## 110. 变体与扩展

| 玩法 | 改法 |
| --- | --- |
| **判断题** | 只要 2 个按钮（对/错），`正确答案` 存 1/2 |
| **多选题** | 每点一个选项就切换该选项的选中位图；「提交」按钮才触发判题；答案用位掩码或列表比较 |
| **限时答题** | 每题 `reset_timer` + `forever` 检查 `timer > 限时` → 广播 `[超时]`；**超时与提交共用同一把 `已答` 锁** |
| **乱序出题** | 建 `题序` 列表存打乱后的题号，用 `item(题序, 当前第几题)` 索引题库 |
| **错题重做** | 答错时把 `题号` 追加进 `错题本` 列表，结算后重放 |
| **难度分级** | 题库按难度分多个平行列表组，`难度` 变量决定取哪组 |

> 无论哪种变体，**§109.1 的按钮侧锁**和 **§109.2 的时钟推进**都适用。

---

## 交付前自检

```bash
python scripts/build_sb3.py --ir examples/quiz.yaml --out examples/output/quiz.sb3
python scripts/validate_sb3.py --sb3 examples/output/quiz.sb3      # 四层
node scripts/quiz_behavior_check.mjs examples/output/quiz.sb3        # QUIZ_LOGIC_OK
```

`quiz_behavior_check.mjs` 会真实模拟「点开始 → 逐题点击 → 反馈期重复点击 → 结算」，
断言分数、答对数、最高连对、`game_state`、题号。**只过四层校验不算答题作品完成。**
