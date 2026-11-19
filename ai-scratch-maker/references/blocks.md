# Scratch 3.0 全部积木速查表

> 本文件由 `scripts/make_blocks_doc.py` 从 `references/blocks-spec.json` 自动生成，
> 而 `blocks-spec.json` 又由 `scripts/extract_blocks_spec.js` 直接从 **Scratch 官方源码** 抽取：
>
> - 积木形状、输入名、字段名、下拉选项 ← `scratch-blocks/src/blocks/*.ts`
> - 运行时原语清单（保证不漏积木）、输入原始类型 ← `scratch-vm/src/blocks/scratch3_*.js`
> - 扩展积木 ← `scratch-vm/src/extensions/*/index.js`

共 **188** 个积木（含 14 个下拉影子积木），覆盖 9 大类别 + 画笔/音乐/朗读/翻译/视频感应/语音转文字扩展。

## 阅读方式

- **opcode**：Scratch 内部的积木唯一标识，IR 里写它最保险。
- **友好名**：语义化的英文别名（如 `move_steps`），IR 里写它更易读。
- **输入（inputs）**：会出现在 sb3 的 `inputs` 字典里，值是 `[状态, ...]`。
- **字段（fields）**：下拉选择类的输入（变量名、造型名、特效类型…），
  在 sb3 里写在 `fields` 字典里，值是 `[值, id]`。

### sb3 编码速查

| 概念 | sb3 写法 |
|---|---|
| 输入里的影子值 | `[1, [4,"10"]]` — 状态 1 + 基元 |
| 输入里嵌套了积木 | `[2, "块id"]` — 状态 2（只有积木） |
| 变量/列表引用 | `[3, [12,"分数","变量id"]]` — 状态 3 |
| 动态下拉菜单 | `[1, "_mouse_"]` — 裸字符串 |
| 广播 | `[1, [11,"开始","开始"]]` |
| 变量字段 | `fields.VARIABLE = ["分数","变量id"]` |
| 普通下拉字段 | `fields.EFFECT = ["COLOR", null]` |
| 静态下拉 id | `null` |

基元类型码：`4`=数字、`8`=角度、`9`=颜色、`10`=文本、`11`=广播、`12`=变量、`13`=列表。

---

## 事件 (Events)（12 个）

#### `event_broadcast`  —  broadcast %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`broadcast`、`event_broadcast`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `BROADCAST_INPUT` | broadcast | 广播消息 | `[1, [11, "开始", "开始"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "event_broadcast",
  "next": null,
  "parent": null,
  "inputs": {
    "BROADCAST_INPUT": [1, [11, "开始", "开始"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_broadcast_menu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `BROADCAST_OPTION` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "event_broadcast_menu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "BROADCAST_OPTION": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_broadcastandwait`  —  broadcast %1 and wait

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`broadcastandwait`、`broadcast_and_wait`、`event_broadcastandwait`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `BROADCAST_INPUT` | broadcast | 广播消息 | `[1, [11, "开始", "开始"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "event_broadcastandwait",
  "next": null,
  "parent": null,
  "inputs": {
    "BROADCAST_INPUT": [1, [11, "开始", "开始"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_touchingobjectmenu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `TOUCHINGOBJECTMENU` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "event_touchingobjectmenu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "TOUCHINGOBJECTMENU": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_whenbackdropswitchesto`

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`whenbackdropswitchesto`、`when_backdrop_switches_to`、`event_whenbackdropswitchesto`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `BACKDROP` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "event_whenbackdropswitchesto",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "BACKDROP": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_whenbroadcastreceived`  —  when I receive %1

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`when_receive`、`whenbroadcastreceived`、`event_whenbroadcastreceived`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `BROADCAST_OPTION` | broadcast | broadcast | `"-"` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "event_whenbroadcastreceived",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "BROADCAST_OPTION": ["值", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_whenflagclicked`  —  when %1 clicked

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`whenflagclicked`、`when_green_flag_clicked`、`event_whenflagclicked`

**生成出的 sb3 积木**

```json
{
  "opcode": "event_whenflagclicked",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_whengreaterthan`  —  when %1 > %2

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`whengreaterthan`、`when_greater_than`、`event_whengreaterthan`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VALUE` | number | 数字 | `[1, [4, "10"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `WHENGREATERTHANMENU` | menu | 静态下拉菜单 | `["COLOR", null]` | `LOUDNESS`、`TIMER` |

**生成出的 sb3 积木**

```json
{
  "opcode": "event_whengreaterthan",
  "next": null,
  "parent": null,
  "inputs": {
    "VALUE": [1, [4, "10"]]
  },
  "fields": {
    "WHENGREATERTHANMENU": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_whenkeypressed`  —  when %1 key pressed

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`whenkeypressed`、`when_key_pressed`、`event_whenkeypressed`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `KEY_OPTION` | menu | 静态下拉菜单 | `["COLOR", null]` | `space`、`up arrow`、`down arrow`、`right arrow`、`left arrow`、`any`、`a`、`b`、`c`、`d`、`e`、`f`、`g`、`h` …（共 42 项） |

**生成出的 sb3 积木**

```json
{
  "opcode": "event_whenkeypressed",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "KEY_OPTION": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_whenstageclicked`  —  when stage clicked

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`whenstageclicked`、`when_stage_clicked`、`event_whenstageclicked`

**生成出的 sb3 积木**

```json
{
  "opcode": "event_whenstageclicked",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_whenthisspriteclicked`  —  when this sprite clicked

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`when_this_clicked`、`whenthisspriteclicked`、`when_this_sprite_clicked`、`event_whenthisspriteclicked`

**生成出的 sb3 积木**

```json
{
  "opcode": "event_whenthisspriteclicked",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `event_whentouchingobject`  —  when this sprite touches %1

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`whentouchingobject`、`event_whentouchingobject`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `TOUCHINGOBJECTMENU` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "event_whentouchingobject",
  "next": null,
  "parent": null,
  "inputs": {
    "TOUCHINGOBJECTMENU": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 控制 (Control)（18 个）

#### `control_all_at_once`  —  all at once

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`all_at_once`、`control_all_at_once`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SUBSTACK` | substack | 子栈（积木堆） | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_all_at_once",
  "next": null,
  "parent": null,
  "inputs": {
    "SUBSTACK": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_clear_counter`  —  clear counter

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`clear_counter`、`control_clear_counter`

**生成出的 sb3 积木**

```json
{
  "opcode": "control_clear_counter",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_create_clone_of`  —  create clone of %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`create_clone`、`create_clone_of`、`control_create_clone_of`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `CLONE_OPTION` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_create_clone_of",
  "next": null,
  "parent": null,
  "inputs": {
    "CLONE_OPTION": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_delete_this_clone`  —  delete this clone

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`delete_this_clone`、`control_delete_this_clone`

**生成出的 sb3 积木**

```json
{
  "opcode": "control_delete_this_clone",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_for_each`  —  for each %1 in %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`for_each`、`control_for_each`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VALUE` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |
| `SUBSTACK` | substack | 子栈（积木堆） | `[2, "子积木id"]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `VARIABLE` | varfield | 变量下拉 | `["分数", "变量id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_for_each",
  "next": null,
  "parent": null,
  "inputs": {
    "VALUE": [1, [10, "值"]],
    "SUBSTACK": [2, "子积木id"]
  },
  "fields": {
    "VARIABLE": ["分数", "变量id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_forever`  —  forever

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`forever`、`control_forever`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SUBSTACK` | substack | 子栈（积木堆） | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_forever",
  "next": null,
  "parent": null,
  "inputs": {
    "SUBSTACK": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_get_counter`  —  counter

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`get_counter`、`control_get_counter`

**生成出的 sb3 积木**

```json
{
  "opcode": "control_get_counter",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_if`  —  if %1 then

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`if`、`control_if`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `CONDITION` | boolean | 布尔积木 | `[2, "子积木id"]` |
| `SUBSTACK` | substack | 子栈（积木堆） | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_if",
  "next": null,
  "parent": null,
  "inputs": {
    "CONDITION": [2, "子积木id"],
    "SUBSTACK": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_if_else`  —  if %1 then

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`if_else`、`control_if_else`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `CONDITION` | boolean | 布尔积木 | `[2, "子积木id"]` |
| `SUBSTACK` | substack | 子栈（积木堆） | `[2, "子积木id"]` |
| `SUBSTACK2` | substack | 子栈（积木堆） | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_if_else",
  "next": null,
  "parent": null,
  "inputs": {
    "CONDITION": [2, "子积木id"],
    "SUBSTACK": [2, "子积木id"],
    "SUBSTACK2": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_incr_counter`  —  increment counter

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`incr_counter`、`control_incr_counter`

**生成出的 sb3 积木**

```json
{
  "opcode": "control_incr_counter",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_repeat`  —  repeat %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`repeat`、`control_repeat`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `TIMES` | number | 数字 | `[1, [4, "10"]]` |
| `SUBSTACK` | substack | 子栈（积木堆） | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_repeat",
  "next": null,
  "parent": null,
  "inputs": {
    "TIMES": [1, [4, "10"]],
    "SUBSTACK": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_repeat_until`  —  repeat until %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`repeat_until`、`control_repeat_until`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `CONDITION` | boolean | 布尔积木 | `[2, "子积木id"]` |
| `SUBSTACK` | substack | 子栈（积木堆） | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_repeat_until",
  "next": null,
  "parent": null,
  "inputs": {
    "CONDITION": [2, "子积木id"],
    "SUBSTACK": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_resettimer`  —  reset timer

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`control_resettimer`

**生成出的 sb3 积木**

```json
{
  "opcode": "control_resettimer",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_start_as_clone`

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`start_as_clone`、`when_start_as_clone`、`control_start_as_clone`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `CLONE_OPTION` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_start_as_clone",
  "next": null,
  "parent": null,
  "inputs": {
    "CLONE_OPTION": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_stop`

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`stop`、`control_stop`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `STOP_OPTION` | menu | 静态下拉菜单 | `["COLOR", null]` | `all`、`this script`、`other scripts in sprite` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_stop",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "STOP_OPTION": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_wait`  —  wait %1 seconds

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`wait`、`control_wait`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `DURATION` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_wait",
  "next": null,
  "parent": null,
  "inputs": {
    "DURATION": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_wait_until`  —  wait until %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`wait_until`、`control_wait_until`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `CONDITION` | boolean | 布尔积木 | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_wait_until",
  "next": null,
  "parent": null,
  "inputs": {
    "CONDITION": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `control_while`  —  while %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`while`、`control_while`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `CONDITION` | boolean | 布尔积木 | `[2, "子积木id"]` |
| `SUBSTACK` | substack | 子栈（积木堆） | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_while",
  "next": null,
  "parent": null,
  "inputs": {
    "CONDITION": [2, "子积木id"],
    "SUBSTACK": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 运动 (Motion)（18 个）

#### `motion_changexby`  —  change x by %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`change_x`、`changexby`、`motion_changexby`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `DX` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_changexby",
  "next": null,
  "parent": null,
  "inputs": {
    "DX": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_changeyby`  —  change y by %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`change_y`、`changeyby`、`motion_changeyby`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `DY` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_changeyby",
  "next": null,
  "parent": null,
  "inputs": {
    "DY": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_direction`  —  direction

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`direction`、`motion_direction`

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_direction",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_glidesecstoxy`  —  glide %1 secs to x: %2 y: %3

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`glide_xy`、`glidesecstoxy`、`motion_glidesecstoxy`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SECS` | number | 数字 | `[1, [4, "10"]]` |
| `X` | number | 数字 | `[1, [4, "10"]]` |
| `Y` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_glidesecstoxy",
  "next": null,
  "parent": null,
  "inputs": {
    "SECS": [1, [4, "10"]],
    "X": [1, [4, "10"]],
    "Y": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_glideto`  —  glide %1 secs to %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`glideto`、`glide_to`、`motion_glideto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SECS` | number | 数字 | `[1, [4, "10"]]` |
| `TO` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_glideto",
  "next": null,
  "parent": null,
  "inputs": {
    "SECS": [1, [4, "10"]],
    "TO": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_goto`  —  go to %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`goto`、`motion_goto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `TO` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_goto",
  "next": null,
  "parent": null,
  "inputs": {
    "TO": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_gotoxy`  —  go to x: %1 y: %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`gotoxy`、`goto_xy`、`motion_gotoxy`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `X` | number | 数字 | `[1, [4, "10"]]` |
| `Y` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_gotoxy",
  "next": null,
  "parent": null,
  "inputs": {
    "X": [1, [4, "10"]],
    "Y": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_ifonedgebounce`  —  if on edge, bounce

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`ifonedgebounce`、`if_on_edge_bounce`、`motion_ifonedgebounce`

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_ifonedgebounce",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_movesteps`  —  move %1 steps

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`movesteps`、`move_steps`、`motion_movesteps`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `STEPS` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_movesteps",
  "next": null,
  "parent": null,
  "inputs": {
    "STEPS": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_pointindirection`  —  point in direction %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`pointindirection`、`point_in_direction`、`motion_pointindirection`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `DIRECTION` | angle | 角度 | `[1, [8, "90"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_pointindirection",
  "next": null,
  "parent": null,
  "inputs": {
    "DIRECTION": [1, [8, "90"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_pointtowards`  —  point towards %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`pointtowards`、`point_towards`、`motion_pointtowards`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `TOWARDS` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_pointtowards",
  "next": null,
  "parent": null,
  "inputs": {
    "TOWARDS": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_setrotationstyle`  —  set rotation style %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`setrotationstyle`、`set_rotation_style`、`motion_setrotationstyle`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `STYLE` | menu | 静态下拉菜单 | `["COLOR", null]` | `left-right`、`don't rotate`、`all around` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_setrotationstyle",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "STYLE": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_setx`  —  set x to %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`setx`、`set_x`、`motion_setx`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `X` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_setx",
  "next": null,
  "parent": null,
  "inputs": {
    "X": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_sety`  —  set y to %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`sety`、`set_y`、`motion_sety`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `Y` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_sety",
  "next": null,
  "parent": null,
  "inputs": {
    "Y": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_turnleft`  —  turn %1 %2 degrees

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`turnleft`、`turn_left`、`motion_turnleft`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `DEGREES` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_turnleft",
  "next": null,
  "parent": null,
  "inputs": {
    "DEGREES": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_turnright`  —  turn %1 %2 degrees

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`turnright`、`turn_right`、`motion_turnright`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `DEGREES` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_turnright",
  "next": null,
  "parent": null,
  "inputs": {
    "DEGREES": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_xposition`  —  x position

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`xposition`、`x_position`、`motion_xposition`

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_xposition",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_yposition`  —  y position

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`yposition`、`y_position`、`motion_yposition`

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_yposition",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 外观 (Looks)（22 个）

#### `looks_backdropnumbername`  —  backdrop %1

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`backdropnumbername`、`backdrop_number_name`、`looks_backdropnumbername`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `NUMBER_NAME` | menu | 静态下拉菜单 | `["COLOR", null]` | `number`、`name` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_backdropnumbername",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "NUMBER_NAME": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_changeeffectby`  —  change %1 effect by %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`change_effect`、`changeeffectby`、`change_ghost_effect`、`looks_changeeffectby`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `CHANGE` | number | 数字 | `[1, [4, "10"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `EFFECT` | menu | 静态下拉菜单 | `["COLOR", null]` | `COLOR`、`FISHEYE`、`WHIRL`、`PIXELATE`、`MOSAIC`、`BRIGHTNESS`、`GHOST` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_changeeffectby",
  "next": null,
  "parent": null,
  "inputs": {
    "CHANGE": [1, [4, "10"]]
  },
  "fields": {
    "EFFECT": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_changesizeby`  —  change size by %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`change_size`、`changesizeby`、`change_size_effect`、`looks_changesizeby`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `CHANGE` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_changesizeby",
  "next": null,
  "parent": null,
  "inputs": {
    "CHANGE": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_cleargraphiceffects`  —  clear graphic effects

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`clear_effects`、`cleargraphiceffects`、`looks_cleargraphiceffects`

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_cleargraphiceffects",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_costumenumbername`  —  costume %1

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`costumenumbername`、`costume_number_name`、`looks_costumenumbername`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `NUMBER_NAME` | menu | 静态下拉菜单 | `["COLOR", null]` | `number`、`name` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_costumenumbername",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "NUMBER_NAME": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_goforwardbackwardlayers`  —  go %1 %2 layers

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`go_back_layers`、`looks_gobacklayers`、`goforwardbackwardlayers`、`looks_goforwardbackwardlayers`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `NUM` | number | 数字 | `[1, [4, "10"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `FORWARD_BACKWARD` | menu | 静态下拉菜单 | `["COLOR", null]` | `forward`、`backward` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_goforwardbackwardlayers",
  "next": null,
  "parent": null,
  "inputs": {
    "NUM": [1, [4, "10"]]
  },
  "fields": {
    "FORWARD_BACKWARD": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_gotofrontback`  —  go to %1 layer

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`go_to_back`、`goto_front`、`go_to_front`、`gotofrontback`、`go_to_front_back`、`go_to_front_layer`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `FRONT_BACK` | menu | 静态下拉菜单 | `["COLOR", null]` | `front`、`back` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_gotofrontback",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "FRONT_BACK": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_hide`  —  hide

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`hide`、`looks_hide`

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_hide",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_nextbackdrop`  —  next backdrop

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`nextbackdrop`、`next_backdrop`、`looks_nextbackdrop`

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_nextbackdrop",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_nextcostume`  —  next costume

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`nextcostume`、`next_costume`、`looks_nextcostume`

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_nextcostume",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_say`  —  say %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`say_no_wait`、`looks_say`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `MESSAGE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_say",
  "next": null,
  "parent": null,
  "inputs": {
    "MESSAGE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_sayforsecs`  —  say %1 for %2 seconds

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`say`、`sayforsecs`、`looks_sayforsecs`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `MESSAGE` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |
| `SECS` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_sayforsecs",
  "next": null,
  "parent": null,
  "inputs": {
    "MESSAGE": [1, [10, "值"]],
    "SECS": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_seteffectto`  —  set %1 effect to %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`set_effect`、`seteffectto`、`looks_seteffect`、`looks_seteffectto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VALUE` | number | 数字 | `[1, [4, "10"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `EFFECT` | menu | 静态下拉菜单 | `["COLOR", null]` | `COLOR`、`FISHEYE`、`WHIRL`、`PIXELATE`、`MOSAIC`、`BRIGHTNESS`、`GHOST` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_seteffectto",
  "next": null,
  "parent": null,
  "inputs": {
    "VALUE": [1, [4, "10"]]
  },
  "fields": {
    "EFFECT": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_setghostto`  —  set ghost effect to (1) %

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`set_ghost`、`setghostto`、`looks_setghostto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `GHOST` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_setghostto",
  "next": null,
  "parent": null,
  "inputs": {
    "GHOST": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_setsizeto`  —  set size to %1 %

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`set_size`、`setsizeto`、`looks_setsize`、`looks_setsizeto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SIZE` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_setsizeto",
  "next": null,
  "parent": null,
  "inputs": {
    "SIZE": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_show`  —  show

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`show`、`looks_show`

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_show",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_size`  —  size

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`size`、`looks_size`

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_size",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_switchbackdropto`  —  switch backdrop to %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`switch_backdrop`、`switchbackdropto`、`looks_switchbackdropto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `BACKDROP` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_switchbackdropto",
  "next": null,
  "parent": null,
  "inputs": {
    "BACKDROP": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_switchbackdroptoandwait`  —  switch backdrop to %1 and wait

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`switchbackdroptoandwait`、`looks_switchbackdroptoandwait`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `BACKDROP` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_switchbackdroptoandwait",
  "next": null,
  "parent": null,
  "inputs": {
    "BACKDROP": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_switchcostumeto`  —  switch costume to %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`switch_costume`、`switchcostumeto`、`looks_switchcostumeto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `COSTUME` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_switchcostumeto",
  "next": null,
  "parent": null,
  "inputs": {
    "COSTUME": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_think`  —  think %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`think_no_wait`、`looks_think`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `MESSAGE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_think",
  "next": null,
  "parent": null,
  "inputs": {
    "MESSAGE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_thinkforsecs`  —  think %1 for %2 seconds

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`think`、`thinkforsecs`、`looks_thinkforsecs`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `MESSAGE` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |
| `SECS` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_thinkforsecs",
  "next": null,
  "parent": null,
  "inputs": {
    "MESSAGE": [1, [10, "值"]],
    "SECS": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 声音 (Sound)（9 个）

#### `sound_changeeffectby`  —  change %1 effect by %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`change_sound_effect`、`sound_changeeffectby`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VALUE` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `EFFECT` | menu | 静态下拉菜单 | `["COLOR", null]` | `PITCH`、`PAN` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_changeeffectby",
  "next": null,
  "parent": null,
  "inputs": {
    "VALUE": [1, [10, "值"]]
  },
  "fields": {
    "EFFECT": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_changevolumeby`  —  change volume by %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`change_volume`、`changevolumeby`、`sound_changevolumeby`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VOLUME` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_changevolumeby",
  "next": null,
  "parent": null,
  "inputs": {
    "VOLUME": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_cleareffects`  —  clear sound effects

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`cleareffects`、`clear_sound_effects`、`sound_cleareffects`

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_cleareffects",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_play`  —  start sound %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`play`、`play_sound`、`start_sound`、`sound_play`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SOUND_MENU` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_play",
  "next": null,
  "parent": null,
  "inputs": {
    "SOUND_MENU": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_playuntildone`  —  play sound %1 until done

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`playuntildone`、`play_sound_until_done`、`sound_playuntildone`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SOUND_MENU` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_playuntildone",
  "next": null,
  "parent": null,
  "inputs": {
    "SOUND_MENU": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_seteffectto`  —  set %1 effect to %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`sound_seteffect`、`set_sound_effect`、`sound_seteffectto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VALUE` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `EFFECT` | menu | 静态下拉菜单 | `["COLOR", null]` | `PITCH`、`PAN` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_seteffectto",
  "next": null,
  "parent": null,
  "inputs": {
    "VALUE": [1, [10, "值"]]
  },
  "fields": {
    "EFFECT": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_setvolumeto`  —  set volume to %1%

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`set_volume`、`setvolumeto`、`sound_setvolume`、`sound_setvolumeto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VOLUME` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_setvolumeto",
  "next": null,
  "parent": null,
  "inputs": {
    "VOLUME": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_stopallsounds`  —  stop all sounds

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`stopallsounds`、`stop_all_sounds`、`sound_stopallsounds`

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_stopallsounds",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_volume`  —  volume

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`volume`、`sound_volume`

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_volume",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 侦测 (Sensing)（22 个）

#### `sensing_answer`  —  answer

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`answer`、`sensing_answer`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_answer",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_askandwait`  —  ask %1 and wait

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`ask`、`askandwait`、`ask_and_wait`、`sensing_askandwait`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `QUESTION` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_askandwait",
  "next": null,
  "parent": null,
  "inputs": {
    "QUESTION": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_backdropname`  —  backdrop name

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`backdropname`、`backdrop_name`、`sensing_backdropname`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_backdropname",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_backdrops`  —  backdrop #

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`backdrops`、`backdrop_num`、`sensing_backdrops`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_backdrops",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_coloristouchingcolor`  —  color %1 is touching %2?

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`color_touching_color`、`coloristouchingcolor`、`sensing_coloristouchingcolor`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `COLOR` | color | 颜色 | `[1, [9, "#ff0000"]]` |
| `COLOR2` | color | 颜色 | `[1, [9, "#ff0000"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_coloristouchingcolor",
  "next": null,
  "parent": null,
  "inputs": {
    "COLOR": [1, [9, "#ff0000"]],
    "COLOR2": [1, [9, "#ff0000"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_current`  —  current %1

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`current`、`sensing_current`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `CURRENTMENU` | menu | 静态下拉菜单 | `["COLOR", null]` | `YEAR`、`MONTH`、`DATE`、`DAYOFWEEK`、`HOUR`、`MINUTE`、`SECOND` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_current",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "CURRENTMENU": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_dayssince2000`  —  days since 2000

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`dayssince2000`、`days_since_2000`、`sensing_dayssince2000`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_dayssince2000",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_distanceto`  —  distance to %1

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`distance`、`distanceto`、`distance_to`、`sensing_distanceto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `DISTANCETOMENU` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_distanceto",
  "next": null,
  "parent": null,
  "inputs": {
    "DISTANCETOMENU": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_keypressed`  —  key %1 pressed?

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`keypressed`、`key_pressed`、`sensing_keypressed`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `KEY_OPTION` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_keypressed",
  "next": null,
  "parent": null,
  "inputs": {
    "KEY_OPTION": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_loud`  —  loud?

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`loud`、`sensing_loud`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_loud",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_loudness`  —  loudness

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`loudness`、`sensing_loudness`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_loudness",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_mousedown`  —  mouse down?

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`mousedown`、`sensing_mousedown`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_mousedown",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_mousex`  —  mouse x

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`mousex`、`mouse_x`、`sensing_mousex`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_mousex",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_mousey`  —  mouse y

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`mousey`、`mouse_y`、`sensing_mousey`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_mousey",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_of`

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`of`、`sensing_of`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `OBJECT` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |
| `PROPERTY` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_of",
  "next": null,
  "parent": null,
  "inputs": {
    "OBJECT": [1, "_mouse_"],
    "PROPERTY": [1, [10, "值"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_resettimer`  —  reset timer

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`resettimer`、`reset_timer`、`sensing_resettimer`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_resettimer",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_setdragmode`  —  set drag mode %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`setdragmode`、`set_drag_mode`、`sensing_setdragmode`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `DRAG_MODE` | menu | 静态下拉菜单 | `["COLOR", null]` | `draggable`、`not draggable` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_setdragmode",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "DRAG_MODE": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_timer`  —  timer

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`timer`、`sensing_timer`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_timer",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_touchingcolor`  —  touching color %1?

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`touchingcolor`、`touching_color`、`sensing_touchingcolor`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `COLOR` | color | 颜色 | `[1, [9, "#ff0000"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_touchingcolor",
  "next": null,
  "parent": null,
  "inputs": {
    "COLOR": [1, [9, "#ff0000"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_touchingobject`  —  touching %1?

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`touching`、`touchingobject`、`touching_mouse_pointer`、`sensing_touchingobject`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `TOUCHINGOBJECTMENU` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_touchingobject",
  "next": null,
  "parent": null,
  "inputs": {
    "TOUCHINGOBJECTMENU": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_userid`  —  user id

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`userid`、`user_id`、`sensing_userid`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_userid",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_username`  —  username

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`username`、`sensing_username`

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_username",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 运算 (Operators)（18 个）

#### `operator_add`  —  %1 + %2

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`add`、`operator_add`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `NUM1` | number | 数字 | `[1, [4, "10"]]` |
| `NUM2` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_add",
  "next": null,
  "parent": null,
  "inputs": {
    "NUM1": [1, [4, "10"]],
    "NUM2": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_and`  —  %1 and %2

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`and`、`operator_and`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `OPERAND1` | boolean | 布尔积木 | `[2, "子积木id"]` |
| `OPERAND2` | boolean | 布尔积木 | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_and",
  "next": null,
  "parent": null,
  "inputs": {
    "OPERAND1": [2, "子积木id"],
    "OPERAND2": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_contains`  —  %1 contains %2?

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`contains`、`operator_contains`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `STRING1` | text | 文本 | `[1, [10, "你好"]]` |
| `STRING2` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_contains",
  "next": null,
  "parent": null,
  "inputs": {
    "STRING1": [1, [10, "你好"]],
    "STRING2": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_divide`  —  %1 / %2

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`divide`、`operator_divide`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `NUM1` | number | 数字 | `[1, [4, "10"]]` |
| `NUM2` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_divide",
  "next": null,
  "parent": null,
  "inputs": {
    "NUM1": [1, [4, "10"]],
    "NUM2": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_equals`  —  %1 = %2

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`equals`、`operator_equals`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `OPERAND1` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |
| `OPERAND2` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_equals",
  "next": null,
  "parent": null,
  "inputs": {
    "OPERAND1": [1, [10, "值"]],
    "OPERAND2": [1, [10, "值"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_gt`  —  %1 > %2

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`gt`、`greater_than`、`operator_gt`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `OPERAND1` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |
| `OPERAND2` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_gt",
  "next": null,
  "parent": null,
  "inputs": {
    "OPERAND1": [1, [10, "值"]],
    "OPERAND2": [1, [10, "值"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_join`  —  join %1 %2

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`join`、`operator_join`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `STRING1` | text | 文本 | `[1, [10, "你好"]]` |
| `STRING2` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_join",
  "next": null,
  "parent": null,
  "inputs": {
    "STRING1": [1, [10, "你好"]],
    "STRING2": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_length`  —  length of %1

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`length`、`length_of`、`operator_length`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `STRING` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_length",
  "next": null,
  "parent": null,
  "inputs": {
    "STRING": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_letter_of`  —  letter %1 of %2

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`letter_of`、`operator_letter_of`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `LETTER` | text | 文本 | `[1, [10, "你好"]]` |
| `STRING` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_letter_of",
  "next": null,
  "parent": null,
  "inputs": {
    "LETTER": [1, [10, "你好"]],
    "STRING": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_lt`  —  %1 < %2

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`lt`、`less_than`、`operator_lt`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `OPERAND1` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |
| `OPERAND2` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_lt",
  "next": null,
  "parent": null,
  "inputs": {
    "OPERAND1": [1, [10, "值"]],
    "OPERAND2": [1, [10, "值"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_mathop`  —  %1 of %2

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`mathop`、`operator_mathop`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `NUM` | number | 数字 | `[1, [4, "10"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `OPERATOR` | menu | 静态下拉菜单 | `["COLOR", null]` | `abs`、`floor`、`ceiling`、`sqrt`、`sin`、`cos`、`tan`、`asin`、`acos`、`atan`、`ln`、`log`、`e ^`、`10 ^` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_mathop",
  "next": null,
  "parent": null,
  "inputs": {
    "NUM": [1, [4, "10"]]
  },
  "fields": {
    "OPERATOR": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_mod`  —  %1 mod %2

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`mod`、`operator_mod`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `NUM1` | number | 数字 | `[1, [4, "10"]]` |
| `NUM2` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_mod",
  "next": null,
  "parent": null,
  "inputs": {
    "NUM1": [1, [4, "10"]],
    "NUM2": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_multiply`  —  %1 * %2

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`multiply`、`operator_multiply`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `NUM1` | number | 数字 | `[1, [4, "10"]]` |
| `NUM2` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_multiply",
  "next": null,
  "parent": null,
  "inputs": {
    "NUM1": [1, [4, "10"]],
    "NUM2": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_not`  —  not %1

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`not`、`operator_not`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `OPERAND` | boolean | 布尔积木 | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_not",
  "next": null,
  "parent": null,
  "inputs": {
    "OPERAND": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_or`  —  %1 or %2

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`or`、`operator_or`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `OPERAND1` | boolean | 布尔积木 | `[2, "子积木id"]` |
| `OPERAND2` | boolean | 布尔积木 | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_or",
  "next": null,
  "parent": null,
  "inputs": {
    "OPERAND1": [2, "子积木id"],
    "OPERAND2": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_random`  —  pick random %1 to %2

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`random`、`operator_random`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `FROM` | number | 数字 | `[1, [4, "10"]]` |
| `TO` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_random",
  "next": null,
  "parent": null,
  "inputs": {
    "FROM": [1, [4, "10"]],
    "TO": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_round`  —  round %1

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`round`、`operator_round`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `NUM` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_round",
  "next": null,
  "parent": null,
  "inputs": {
    "NUM": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `operator_subtract`  —  %1 - %2

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`subtract`、`operator_subtract`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `NUM1` | number | 数字 | `[1, [4, "10"]]` |
| `NUM2` | number | 数字 | `[1, [4, "10"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "operator_subtract",
  "next": null,
  "parent": null,
  "inputs": {
    "NUM1": [1, [4, "10"]],
    "NUM2": [1, [4, "10"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 变量与列表 (Data)（17 个）

#### `data_addtolist`  —  add %1 to %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`addtolist`、`add_to_list`、`data_addtolist`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `ITEM` | text | 文本 | `[1, [10, "你好"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_addtolist",
  "next": null,
  "parent": null,
  "inputs": {
    "ITEM": [1, [10, "你好"]]
  },
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_changevariableby`  —  change %1 by %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`change_variable`、`changevariableby`、`data_changevariableby`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VALUE` | number | 数字 | `[1, [4, "10"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `VARIABLE` | varfield | 变量下拉 | `["分数", "变量id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_changevariableby",
  "next": null,
  "parent": null,
  "inputs": {
    "VALUE": [1, [4, "10"]]
  },
  "fields": {
    "VARIABLE": ["分数", "变量id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_deletealloflist`  —  delete all of %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`deletealloflist`、`delete_all_of_list`、`data_deletealloflist`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_deletealloflist",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_deleteoflist`  —  delete %1 of %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`deleteoflist`、`delete_of_list`、`data_deleteoflist`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `INDEX` | number | 数字 | `[1, [4, "10"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_deleteoflist",
  "next": null,
  "parent": null,
  "inputs": {
    "INDEX": [1, [4, "10"]]
  },
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_hidelist`  —  hide list %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`hidelist`、`hide_list`、`data_hidelist`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_hidelist",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_hidevariable`  —  hide variable %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`hidevariable`、`hide_variable`、`data_hidevariable`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `VARIABLE` | varfield | 变量下拉 | `["分数", "变量id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_hidevariable",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "VARIABLE": ["分数", "变量id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_insertatlist`  —  insert %1 at %2 of %3

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`insertatlist`、`insert_at_list`、`data_insertatlist`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `ITEM` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |
| `INDEX` | number | 数字 | `[1, [4, "10"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_insertatlist",
  "next": null,
  "parent": null,
  "inputs": {
    "ITEM": [1, [10, "值"]],
    "INDEX": [1, [4, "10"]]
  },
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_itemnumoflist`  —  item # of %1 in %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`itemnumoflist`、`item_num_of_list`、`data_itemnumoflist`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `ITEM` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_itemnumoflist",
  "next": null,
  "parent": null,
  "inputs": {
    "ITEM": [1, [10, "值"]]
  },
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_itemoflist`  —  item %1 of %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`itemoflist`、`item_of_list`、`data_itemoflist`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `INDEX` | number | 数字 | `[1, [4, "10"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_itemoflist",
  "next": null,
  "parent": null,
  "inputs": {
    "INDEX": [1, [4, "10"]]
  },
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_lengthoflist`  —  length of %1

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`lengthoflist`、`length_of_list`、`data_lengthoflist`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_lengthoflist",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_listcontainsitem`  —  %1 contains %2?

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`list_contains`、`listcontainsitem`、`data_listcontainsitem`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `ITEM` | text | 文本 | `[1, [10, "你好"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_listcontainsitem",
  "next": null,
  "parent": null,
  "inputs": {
    "ITEM": [1, [10, "你好"]]
  },
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_listcontents`

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`list`、`listcontents`、`data_listcontents`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_listcontents",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_replaceitemoflist`  —  replace item %1 of %2 with %3

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`replaceitemoflist`、`replace_item_of_list`、`data_replaceitemoflist`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `INDEX` | number | 数字 | `[1, [4, "10"]]` |
| `ITEM` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_replaceitemoflist",
  "next": null,
  "parent": null,
  "inputs": {
    "INDEX": [1, [4, "10"]],
    "ITEM": [1, [10, "值"]]
  },
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_setvariableto`  —  set %1 to %2

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`set_variable`、`setvariableto`、`data_setvariableto`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VALUE` | value | 任意值（文本/数字） | `[1, [10, "值"]]` |

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `VARIABLE` | varfield | 变量下拉 | `["分数", "变量id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_setvariableto",
  "next": null,
  "parent": null,
  "inputs": {
    "VALUE": [1, [10, "值"]]
  },
  "fields": {
    "VARIABLE": ["分数", "变量id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_showlist`  —  show list %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`showlist`、`show_list`、`data_showlist`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `LIST` | listfield | 列表下拉 | `["排行榜", "列表id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_showlist",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "LIST": ["排行榜", "列表id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_showvariable`  —  show variable %1

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`showvariable`、`show_variable`、`data_showvariable`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `VARIABLE` | varfield | 变量下拉 | `["分数", "变量id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_showvariable",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "VARIABLE": ["分数", "变量id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `data_variable`

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`var`、`variable`、`data_variable`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `VARIABLE` | varfield | 变量下拉 | `["分数", "变量id"]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "data_variable",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "VARIABLE": ["分数", "变量id"]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 自定义积木 (Procedures)（6 个）

#### `argument_reporter_boolean`

- 形状：**布尔积木（六边形）**
- 友好名（IR 里可直接用）：`argument_reporter_boolean`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `VALUE` | argument | argument | `"-"` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "argument_reporter_boolean",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "VALUE": ["值", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `argument_reporter_string_number`

- 形状：**上报积木（圆角）**
- 友好名（IR 里可直接用）：`argument_reporter_string_number`

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `VALUE` | argument | argument | `"-"` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "argument_reporter_string_number",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "VALUE": ["值", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `procedures_call`

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`call`、`call_proc`、`procedures_call`

**生成出的 sb3 积木**

```json
{
  "opcode": "procedures_call",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `procedures_declaration`

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`procedures_declaration`

**生成出的 sb3 积木**

```json
{
  "opcode": "procedures_declaration",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `procedures_definition`  —  define %1

- 形状：**帽子积木（脚本起点）**
- 友好名（IR 里可直接用）：`procedures_definition`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `custom_block` | substack | 子栈（积木堆） | `[2, "子积木id"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "procedures_definition",
  "next": null,
  "parent": null,
  "inputs": {
    "custom_block": [2, "子积木id"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `procedures_prototype`

- 形状：**命令积木**
- 友好名（IR 里可直接用）：`procedures_prototype`

**生成出的 sb3 积木**

```json
{
  "opcode": "procedures_prototype",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 画笔扩展 (Pen)（13 个）

> 使用画笔积木时，必须在 IR 根节点声明 `extensions: [pen]`。

#### `pen_changePenColorParamBy`  —  change pen [COLOR_PARAM] by [VALUE]

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`changePenColorParamBy`、`pen_change_pen_color_param_by`、`pen_changePenColorParamBy`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `COLOR_PARAM` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |
| `VALUE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_changePenColorParamBy",
  "next": null,
  "parent": null,
  "inputs": {
    "COLOR_PARAM": [1, "_mouse_"],
    "VALUE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_changePenHueBy`  —  change pen color by [HUE]

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`changePenHueBy`、`change_pen_hue`、`pen_change_pen_hue_by`、`pen_changePenHueBy`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `HUE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_changePenHueBy",
  "next": null,
  "parent": null,
  "inputs": {
    "HUE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_changePenShadeBy`  —  change pen shade by [SHADE]

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`changePenShadeBy`、`change_pen_shade`、`pen_change_pen_shade_by`、`pen_changePenShadeBy`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SHADE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_changePenShadeBy",
  "next": null,
  "parent": null,
  "inputs": {
    "SHADE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_changePenSizeBy`  —  change pen size by [SIZE]

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`changePenSizeBy`、`change_pen_size`、`pen_change_pen_size_by`、`pen_changePenSizeBy`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SIZE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_changePenSizeBy",
  "next": null,
  "parent": null,
  "inputs": {
    "SIZE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_clear`  —  erase all

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`clear`、`pen_clear`

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_clear",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_penDown`  —  pen down

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`penDown`、`pendown`、`pen_down`、`pen_pen_down`、`pen_penDown`

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_penDown",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_penUp`  —  pen up

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`penUp`、`penup`、`pen_up`、`pen_pen_up`、`pen_penUp`

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_penUp",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_setPenColorParamTo`  —  set pen [COLOR_PARAM] to [VALUE]

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`setPenColorParamTo`、`pen_set_pen_color_param_to`、`pen_setPenColorParamTo`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `COLOR_PARAM` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |
| `VALUE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_setPenColorParamTo",
  "next": null,
  "parent": null,
  "inputs": {
    "COLOR_PARAM": [1, "_mouse_"],
    "VALUE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_setPenColorToColor`  —  set pen color to [COLOR]

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`set_pen_color`、`setPenColorToColor`、`pen_set_pen_color_to_color`、`pen_setPenColorToColor`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `COLOR` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_setPenColorToColor",
  "next": null,
  "parent": null,
  "inputs": {
    "COLOR": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_setPenHueToNumber`  —  set pen color to [HUE]

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`set_pen_hue`、`setPenHueToNumber`、`pen_set_pen_hue_to_number`、`pen_setPenHueToNumber`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `HUE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_setPenHueToNumber",
  "next": null,
  "parent": null,
  "inputs": {
    "HUE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_setPenShadeToNumber`  —  set pen shade to [SHADE]

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`set_pen_shade`、`setPenShadeToNumber`、`pen_set_pen_shade_to_number`、`pen_setPenShadeToNumber`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SHADE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_setPenShadeToNumber",
  "next": null,
  "parent": null,
  "inputs": {
    "SHADE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_setPenSizeTo`  —  set pen size to [SIZE]

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`setPenSizeTo`、`set_pen_size`、`pen_set_pen_size_to`、`pen_setPenSizeTo`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `SIZE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_setPenSizeTo",
  "next": null,
  "parent": null,
  "inputs": {
    "SIZE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `pen_stamp`  —  stamp

- 形状：**命令积木**
- 扩展：`pen`
- 友好名（IR 里可直接用）：`stamp`、`pen_stamp`

**生成出的 sb3 积木**

```json
{
  "opcode": "pen_stamp",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 音乐扩展 (Music)（9 个）

#### `music_changeTempo`  —  change tempo by [TEMPO]

- 形状：**命令积木**
- 扩展：`music`
- 友好名（IR 里可直接用）：`changeTempo`、`music_change_tempo`、`music_changeTempo`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `TEMPO` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "music_changeTempo",
  "next": null,
  "parent": null,
  "inputs": {
    "TEMPO": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `music_getTempo`  —  tempo

- 形状：**命令积木**
- 扩展：`music`
- 友好名（IR 里可直接用）：`getTempo`、`music_get_tempo`、`music_getTempo`

**生成出的 sb3 积木**

```json
{
  "opcode": "music_getTempo",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `music_midiPlayDrumForBeats`  —  play drum [DRUM] for [BEATS] beats

- 形状：**命令积木**
- 扩展：`music`
- 友好名（IR 里可直接用）：`midiPlayDrumForBeats`、`music_midi_play_drum_for_beats`、`music_midiPlayDrumForBeats`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `DRUM` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |
| `BEATS` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "music_midiPlayDrumForBeats",
  "next": null,
  "parent": null,
  "inputs": {
    "DRUM": [1, "_mouse_"],
    "BEATS": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `music_midiSetInstrument`  —  set instrument to [INSTRUMENT]

- 形状：**命令积木**
- 扩展：`music`
- 友好名（IR 里可直接用）：`midiSetInstrument`、`music_midi_set_instrument`、`music_midiSetInstrument`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `INSTRUMENT` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "music_midiSetInstrument",
  "next": null,
  "parent": null,
  "inputs": {
    "INSTRUMENT": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `music_playDrumForBeats`  —  play drum [DRUM] for [BEATS] beats

- 形状：**命令积木**
- 扩展：`music`
- 友好名（IR 里可直接用）：`play_drum`、`playDrumForBeats`、`music_play_drum_for_beats`、`music_playDrumForBeats`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `DRUM` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |
| `BEATS` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "music_playDrumForBeats",
  "next": null,
  "parent": null,
  "inputs": {
    "DRUM": [1, "_mouse_"],
    "BEATS": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `music_playNoteForBeats`  —  play note [NOTE] for [BEATS] beats

- 形状：**命令积木**
- 扩展：`music`
- 友好名（IR 里可直接用）：`play_note`、`playNoteForBeats`、`music_play_note_for_beats`、`music_playNoteForBeats`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `NOTE` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |
| `BEATS` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "music_playNoteForBeats",
  "next": null,
  "parent": null,
  "inputs": {
    "NOTE": [1, "_mouse_"],
    "BEATS": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `music_restForBeats`  —  rest for [BEATS] beats

- 形状：**命令积木**
- 扩展：`music`
- 友好名（IR 里可直接用）：`rest`、`restForBeats`、`music_rest_for_beats`、`music_restForBeats`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `BEATS` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "music_restForBeats",
  "next": null,
  "parent": null,
  "inputs": {
    "BEATS": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `music_setInstrument`  —  set instrument to [INSTRUMENT]

- 形状：**命令积木**
- 扩展：`music`
- 友好名（IR 里可直接用）：`setInstrument`、`set_instrument`、`music_set_instrument`、`music_setInstrument`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `INSTRUMENT` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "music_setInstrument",
  "next": null,
  "parent": null,
  "inputs": {
    "INSTRUMENT": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `music_setTempo`  —  set tempo to [TEMPO]

- 形状：**命令积木**
- 扩展：`music`
- 友好名（IR 里可直接用）：`setTempo`、`set_tempo`、`music_set_tempo`、`music_setTempo`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `TEMPO` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "music_setTempo",
  "next": null,
  "parent": null,
  "inputs": {
    "TEMPO": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 朗读扩展 (Text to Speech)（3 个）

#### `text2speech_setLanguage`  —  set language to [LANGUAGE]

- 形状：**命令积木**
- 扩展：`text2speech`
- 友好名（IR 里可直接用）：`setLanguage`、`text2speech_set_language`、`text2speech_setLanguage`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `LANGUAGE` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "text2speech_setLanguage",
  "next": null,
  "parent": null,
  "inputs": {
    "LANGUAGE": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `text2speech_setVoice`  —  set voice to [VOICE]

- 形状：**命令积木**
- 扩展：`text2speech`
- 友好名（IR 里可直接用）：`setVoice`、`text2speech_set_voice`、`text2speech_setVoice`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VOICE` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "text2speech_setVoice",
  "next": null,
  "parent": null,
  "inputs": {
    "VOICE": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `text2speech_speakAndWait`  —  speak [WORDS]

- 形状：**命令积木**
- 扩展：`text2speech`
- 友好名（IR 里可直接用）：`speakAndWait`、`text2speech_speak_and_wait`、`text2speech_speakAndWait`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `WORDS` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "text2speech_speakAndWait",
  "next": null,
  "parent": null,
  "inputs": {
    "WORDS": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 翻译扩展 (Translate)（2 个）

#### `translate_getTranslate`  —  translate [WORDS] to [LANGUAGE]

- 形状：**命令积木**
- 扩展：`translate`
- 友好名（IR 里可直接用）：`getTranslate`、`translate_get_translate`、`translate_getTranslate`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `WORDS` | text | 文本 | `[1, [10, "你好"]]` |
| `LANGUAGE` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "translate_getTranslate",
  "next": null,
  "parent": null,
  "inputs": {
    "WORDS": [1, [10, "你好"]],
    "LANGUAGE": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `translate_getViewerLanguage`  —  language

- 形状：**命令积木**
- 扩展：`translate`
- 友好名（IR 里可直接用）：`getViewerLanguage`、`translate_get_viewer_language`、`translate_getViewerLanguage`

**生成出的 sb3 积木**

```json
{
  "opcode": "translate_getViewerLanguage",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 视频感应扩展 (Video Sensing)（4 个）

#### `videoSensing_setVideoTransparency`  —  set video transparency to [TRANSPARENCY]

- 形状：**命令积木**
- 扩展：`videoSensing`
- 友好名（IR 里可直接用）：`setVideoTransparency`、`video_sensing_set_video_transparency`、`videoSensing_setVideoTransparency`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `TRANSPARENCY` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "videoSensing_setVideoTransparency",
  "next": null,
  "parent": null,
  "inputs": {
    "TRANSPARENCY": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `videoSensing_videoOn`  —  video [ATTRIBUTE] on [SUBJECT]

- 形状：**命令积木**
- 扩展：`videoSensing`
- 友好名（IR 里可直接用）：`videoOn`、`video_sensing_video_on`、`videoSensing_videoOn`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `ATTRIBUTE` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |
| `SUBJECT` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "videoSensing_videoOn",
  "next": null,
  "parent": null,
  "inputs": {
    "ATTRIBUTE": [1, "_mouse_"],
    "SUBJECT": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `videoSensing_videoToggle`  —  turn video [VIDEO_STATE]

- 形状：**命令积木**
- 扩展：`videoSensing`
- 友好名（IR 里可直接用）：`videoToggle`、`video_sensing_video_toggle`、`videoSensing_videoToggle`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `VIDEO_STATE` | menu | 动态下拉菜单 | `[1, "_mouse_"]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "videoSensing_videoToggle",
  "next": null,
  "parent": null,
  "inputs": {
    "VIDEO_STATE": [1, "_mouse_"]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `videoSensing_whenMotionGreaterThan`  —  when video motion > [REFERENCE]

- 形状：**命令积木**
- 扩展：`videoSensing`
- 友好名（IR 里可直接用）：`whenMotionGreaterThan`、`video_sensing_when_motion_greater_than`、`videoSensing_whenMotionGreaterThan`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `REFERENCE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "videoSensing_whenMotionGreaterThan",
  "next": null,
  "parent": null,
  "inputs": {
    "REFERENCE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 语音转文字扩展 (Speech to Text)（3 个）

#### `speech2text_getSpeech`  —  speech

- 形状：**命令积木**
- 扩展：`speech2text`
- 友好名（IR 里可直接用）：`speech2text_get_speech`、`speech2text_getSpeech`

**生成出的 sb3 积木**

```json
{
  "opcode": "speech2text_getSpeech",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `speech2text_listenAndWait`  —  listen and wait

- 形状：**命令积木**
- 扩展：`speech2text`
- 友好名（IR 里可直接用）：`speech2text_listen_and_wait`、`speech2text_listenAndWait`

**生成出的 sb3 积木**

```json
{
  "opcode": "speech2text_listenAndWait",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `speech2text_whenIHearHat`  —  when I hear [PHRASE]

- 形状：**命令积木**
- 扩展：`speech2text`
- 友好名（IR 里可直接用）：`speech2text_when_i_hear_hat`、`speech2text_whenIHearHat`

**输入（写在 sb3 的 `inputs`）**

| 名称 | 类型 | 说明 | sb3 编码示例 |
|---|---|---|---|
| `PHRASE` | text | 文本 | `[1, [10, "你好"]]` |

**生成出的 sb3 积木**

```json
{
  "opcode": "speech2text_whenIHearHat",
  "next": null,
  "parent": null,
  "inputs": {
    "PHRASE": [1, [10, "你好"]]
  },
  "fields": {},
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

## 其它（12 个）

#### `control_create_clone_of_menu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `CLONE_OPTION` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "control_create_clone_of_menu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "CLONE_OPTION": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_backdrops`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `BACKDROP` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_backdrops",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "BACKDROP": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `looks_costume`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `COSTUME` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "looks_costume",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "COSTUME": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_glideto_menu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `TO` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_glideto_menu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "TO": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_goto_menu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `TO` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_goto_menu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "TO": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `motion_pointtowards_menu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `TOWARDS` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "motion_pointtowards_menu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "TOWARDS": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_distancetomenu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `DISTANCETOMENU` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_distancetomenu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "DISTANCETOMENU": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_of_object_menu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `OBJECT` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_of_object_menu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "OBJECT": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sensing_touchingobjectmenu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `TOUCHINGOBJECTMENU` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "sensing_touchingobjectmenu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "TOUCHINGOBJECTMENU": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_beats_menu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `BEATS` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_beats_menu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "BEATS": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_effects_menu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `EFFECT` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_effects_menu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "EFFECT": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```

#### `sound_sounds_menu`

- 形状：**下拉菜单影子积木**

**字段（写在 sb3 的 `fields`）**

| 名称 | 类型 | 说明 | sb3 编码示例 | 可选值 |
|---|---|---|---|---|
| `SOUND_MENU` | menu | 静态下拉菜单 | `["COLOR", null]` | （运行时填充，如角色名/造型名） |

**生成出的 sb3 积木**

```json
{
  "opcode": "sound_sounds_menu",
  "next": null,
  "parent": null,
  "inputs": {},
  "fields": {
    "SOUND_MENU": ["COLOR", null]
  },
  "topLevel": true,
  "x": 0,
  "y": 0
}
```
