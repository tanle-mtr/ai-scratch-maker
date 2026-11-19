# sb3 编码规则详解

本文件解释 Scratch 3.0 `.sb3` 的内部结构。**AI 写 IR 时不需要直接用这些结构**——
序列化器 `scripts/build_sb3.py` 会自动处理；本文件用于调试和深入理解。

所有规则都来自 **Scratch 官方源码与官方 JSON Schema**：

- `scratch-parser/lib/sb3_schema.json` + `sb3_definitions.json`（官方 sb3 规范）
- `scratch-vm/src/serialization/sb3.js`（官方序列化/反序列化实现）
- `scratch-vm/src/engine/runtime.js`（运行时语义）

---

## 1. 文件结构

`.sb3` 是一个 **ZIP**（官方规范不压缩，用 ZIP_STORED 即可）：

```
项目.sb3
├── project.json          # 项目本体（UTF-8，官方要求 ASCII 转义）
└── assets/
    ├── <md5>.svg         # 造型
    ├── <md5>.png
    └── <md5>.wav         # 声音
```

资产文件名 = 文件内容的 MD5 + 原扩展名，`project.json` 里通过 `md5ext` 字段引用。

`project.json` 顶层结构：

```json
{
  "targets": [ /* 舞台 + 所有角色 */ ],
  "monitors": [],
  "extensions": ["pen"],
  "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "..."}
}
```

---

## 2. target（舞台 / 角色）

每个 target 是一个字典：

| 字段 | 说明 |
|---|---|
| `isStage` | `true` = 舞台（全局作用域），`false` = 角色 |
| `name` | 名字（舞台固定为 `"Stage"`） |
| `variables` | `{变量id: [名字, 初值]}`，云变量为 `[名字, 初值, true]` |
| `lists` | `{列表id: [名字, [内容...]]}` |
| `broadcasts` | `{广播id: 广播消息}` |
| `blocks` | `{块id: 积木对象}` |
| `costumes` | 造型数组（舞台的背景也叫 costumes） |
| `sounds` | 声音数组 |
| `currentCostume` / `volume` / `layerOrder` | 当前造型 / 音量 / 图层顺序 |
| `x` `y` `size` `direction` `visible` `rotationStyle` | 仅角色有 |

### 2.1 变量作用域（很重要）

- 声明在 **舞台** 上的变量 = **全局变量**，所有角色共用同一个变量 id。
- 声明在 **角色** 上的变量 = **局部变量**，只有该角色能用。
- 角色脚本里引用一个全局变量时，**用舞台那个变量的 id**，角色自己的 `variables`
  里 **不会出现** 它。

序列化器已自动处理：先构建舞台并登记全局变量 id，之后角色遇到同名变量直接复用。

### 2.2 云变量（Cloud Variables）

官方 `scalar_variable` 定义：

```json
{ "type": "array", "items": ["名字", 初值], "additionalItems": { "const": true }, "maxItems": 3 }
```

也就是说云变量的写法是：

```json
"variables": {
  "变量id": ["最高分", 0, true]
}
```

**限制**：`scratch-vm` 的 `cloudDataManager` 里 `const limit = 10` ——
一个项目最多 **10 个云变量**。

云变量必须声明在 **舞台** 上才能真正全局共享。

### 2.3 云列表：Scratch 3.0 不支持

官方 `list` 定义的 `items` 恰好两项且 `additionalItems: false`：

```json
{ "type": "array", "items": ["名字", [内容...]], "additionalItems": false }
```

`scratch-vm` 的 `serializeVariables` 也只给标量变量追加 `isCloud`：

```js
// otherwise should be a scalar type
obj.variables[varId] = [v.name, v.value];
// only scalar vars have the potential to be cloud vars
if (v.isCloud) obj.variables[varId].push(true);
```

**结论**：Scratch 3.0 的编辑器里没有「云列表」这个东西。
需要在多人之间共享一份列表时，用 **全局列表 + 云变量存版本/校验和**，
或者用一个云变量存 JSON 字符串。本 skill 在 IR 里如果写了 `cloud: true` 的列表，
会给出明确告警并按普通列表生成。

---

## 3. 积木对象（block）

```json
{
  "opcode": "motion_movesteps",
  "next": null,                 // 下一个积木的 id
  "parent": null,               // 父积木 id（子栈里的积木指向 C 型积木）
  "inputs": { "STEPS": [1, [4, "10"]] },
  "fields": {},
  "topLevel": true,             // 是否是脚本/子栈的第一块
  "x": 0, "y": 0
}
```

### 3.1 inputs（值输入）

值是 `[状态, ...]`：

| 状态 | 含义 | 后续内容 |
|---|---|---|
| `1` | 只有影子值 | 一个基元，或一个影子积木的 id |
| `2` | 只有积木 | 积木 id（字符串） |
| `3` | 影子被积木遮住 | 积木 id（字符串），或基元 + 积木 id |

基元（primitive）是一个数组，**首元素是类型码**：

| 类型码 | 含义 | 形状 |
|---|---|---|
| `4` | 数字 | `[4, "10"]` |
| `8` | 角度 | `[8, "90"]` |
| `9` | 颜色 | `[9, "#ff0000"]` |
| `10` | 文本 | `[10, "你好"]` |
| `11` | 广播 | `[11, "消息名", "消息id"]` |
| `12` | 变量 | `[12, "变量名", "变量id"]` |
| `13` | 列表 | `[13, "列表名", "列表id"]` |

> **注意 1**：菜单（下拉选择）**不是基元**。
> 「动态下拉」（如「移到 鼠标指针」「碰到 老鼠」）在 sb3 里是一个**独立的影子积木**，
> 父积木的输入引用它的 id：
>
> ```json
> "motion_goto": { "inputs": { "TO": [1, "影子积木id"] }, "fields": {} },
> "影子积木id": {
>   "opcode": "motion_goto_menu",
>   "fields": { "TO": ["_mouse_", null] },
>   "shadow": true, "topLevel": true, "inputs": {}, "next": null, "parent": null
> }
> ```
>
> 直接写裸字符串 `[1, "_mouse_"]` 是**错的**：运行时反序列化时字符串会被当成
> 「块 id」去查找，找不到就是 `null`，脚本一执行就崩
> （`Cannot read properties of null (reading '_isHat')`）。

> **注意 2**：`event_broadcast` 的广播输入用的是**广播基元** `[11, 名字, id]`，
> 它会被反序列化成 `event_broadcast_menu` 影子积木（带 `fields.BROADCAST_OPTION`）。

各积木的动态下拉对应哪个影子积木，见 `references/blocks-spec.json` 里
每个积木的 `menu_inputs` 字段。

### 3.2 fields（下拉字段）

| 字段 | 写法 | 例子 |
|---|---|---|
| 变量下拉 | `["变量名", "变量id"]` | `{"VARIABLE": ["分数", "a1b2"]}` |
| 列表下拉 | `["列表名", "列表id"]` | `{"LIST": ["排行榜", "c3d4"]}` |
| 静态下拉 | `["选项值", null]` | `{"EFFECT": ["COLOR", null]}` |
| 广播（自定义积木） | mutation 对象 | `{"PROCEDURE_DEFINITION": {...}}` |

**关键区别**：

- `looks_seteffectto` 的 `EFFECT`（选哪种特效）→ **field**，
  `VALUE`（特效数值）→ **input**。
- `motion_goto` 的 `TO`（去鼠标/随机位置/角色）→ **input**，
  但值在**影子积木**里（见 3.1 的说明）。
- `data_setvariableto` 的 `VARIABLE`（改哪个变量）→ **field**，
  `VALUE`（改成什么）→ **input**。
- `event_whenbroadcastreceived` 的 `BROADCAST_OPTION` → **field**，
  写成 `[消息名, 消息id]`。帽子的匹配逻辑读的是 `fields`。

写错位置（该在 field 的写到 input，或反之）不会报错，但积木在 Scratch 里会
表现为「丢了参数」的样子。`scripts/validate_sb3.py` 会检查这一点。

---

## 4. 子栈与连线

C 型积木（repeat / if / if_else / forever / while …）的子栈积木：

```json
"control_repeat": {
  "inputs": {
    "TIMES": [1, [4, "10"]],
    "SUBSTACK": [2, "第一个子积木的id"]
  }
}
```

子栈里的积木通过 `parent` 指回 C 型积木，`next` 串成链；
`SUBSTACK2`（if_else 的否则分支）同理。

---

## 5. 自定义积木（Procedures）

一个自定义积木由三块组成：

1. `procedures_definition`（帽子积木）
2. `procedures_prototype`（原型，输入 = definition 的 `custom_block`）
3. `procedures_call`（调用）

`mutation` 对象必须包含 `tagName: "mutation"` 和 `children: []`，
否则 `mutationToXML` 会抛 `Cannot read properties of undefined (reading 'length')`。

```json
{
  "tagName": "mutation",
  "proccode": "画正方形 %n",
  "argumentids": "[\"arg1\"]",
  "argumentnames": "[\"side\"]",
  "argumentdefaults": "[\"\"]",
  "warp": "false",
  "children": []
}
```

**过程参数在 sb3 里是「以参数 id 为变量 id 的变量」**：
`argumentids` 里的 `arg1` 同时会出现在该 target 的 `variables` 里：

```json
"variables": { "arg1": ["side", ""] }
```

---

## 6. 扩展（Extensions）

| 扩展 | id | 积木前缀 |
|---|---|---|
| 画笔 | `pen` | `pen_` |
| 音乐 | `music` | `music_` |
| 朗读 | `text2speech` | `text2speech_` |
| 翻译 | `translate` | `translate_` |
| 视频感应 | `videoSensing` | `videoSensing_` |
| 语音转文字 | `speech2text` | `speech2text_` |

用了扩展的积木，必须在 `project.json` 的 `extensions` 数组里登记扩展 id
（IR 里写 `extensions: [pen]` 即可，序列化器自动处理）。

---

## 7. 监视器（屏幕上的读数）

Scratch 里勾选「显示变量」会在舞台上出现一个读数，对应 `project.json` 顶层
`monitors` 数组：

```json
{
  "id": "变量id",
  "mode": "default",
  "opcode": "data_variable",
  "params": { "VARIABLE": "分数" },
  "spriteName": null,
  "value": 0,
  "width": 0, "height": 0,
  "x": 8, "y": 8,
  "visible": true,
  "sliderMin": 0, "sliderMax": 100, "isDiscrete": true
}
```

- `id` 必须是**变量 id**（与 `targets[].variables` 的键一致），运行时靠它关联。
- `spriteName` 为 `null` 表示全局（舞台上的变量）；角色专属变量要填角色名。
- 列表监视器：`mode` 为 `"list"`、`opcode` 为 `"data_listcontents"`、
  `params` 为 `{"LIST": 名字}`，且**不带** `sliderMin/sliderMax/isDiscrete`
  （官方序列化器就是这么区分的）。
- `x` / `y` 是舞台坐标（0~480 / 0~360），左上角为原点。

官方 `sb3_schema.json` 并没有约束 `monitors`，但运行时按上面的字段读取，
格式错了监视器就不显示。

---

## 8. 注释（comments）

Scratch 的注释是**附在积木上的便签**，写在每个 target 的 `comments` 字典里：

```json
"comments": {
  "<注释id>": {
    "blockId": "<积木id>",
    "text": "这是一条注释",
    "minimized": false,
    "x": 180, "y": 40,
    "width": 200, "height": 200
  }
}
```

- 关联是**双向**的：注释的 `blockId` 指向积木，积木也有一个 `comment` 字段指向注释 id。
  少一边，编辑器里就看不到注释。
- `blockId` 为 `null`（或缺省）表示**悬空注释**，贴在画布空白处。
- `text` 必填，官方上限 8000 字符。
- `x`/`y` 是画布坐标；官方 Schema 里它们是 `optionalNumber`（可为 null，
  由编辑器根据积木位置自己算）。

---

## 9. 积木的位置（整理积木）

sb3 里**只有顶层积木带 x/y**：

```js
// scratch-vm serializeBlock
obj.shadow = block.shadow;
if (block.topLevel) {
    obj.topLevel = true;
    obj.x = block.x ? Math.round(block.x) : 0;
    obj.y = block.y ? Math.round(block.y) : 0;
} else {
    obj.topLevel = false;
}
```

所以「整理积木」（Scratch 编辑器里的 Clean Up Blocks）= **给顶层脚本分配互不重叠的
x/y**。其余积木由编辑器按积木树自动排布，不用管。

### 一个容易踩的坑：影子积木不能是 topLevel

下拉菜单的影子积木（`motion_goto_menu` 等）是**父积木的输入**，不是独立脚本。
它必须写 `"topLevel": false`：

```js
// scratch-vm Blocks.createBlock
if (block.topLevel) {
    this._addScript(block.id);   // 加进 _scripts
}
```

而编辑器正是遍历 `_scripts` 生成画布 XML 的：

```js
// scratch-vm Blocks.toXML
return this._scripts.map(script => this.blockToXML(script, comments)).join();
```

所以一旦影子积木写成 `topLevel: true`，它就会被当成独立脚本，
在画布左上角多出一个**孤零零的小下拉框**。

---

## 10. 排查清单

| 现象 | 原因 | 处理 |
|---|---|---|
| `Non-ascii character in FixedAsciiString` | project.json 没通过 scratch-parser 校验，回退到 SB1 解析 | 这是**假象**，真正原因是结构非法；用官方 schema 校验定位 |
| 积木在 Scratch 里缺参数 | 该在 `fields` 的写进了 `inputs`（或反之） | 对照 `references/blocks.md` |
| 变量积木显示异常 | 变量名被二次编码成字符串 | 变量必须走 `fields.VARIABLE` |
| 打开项目就报错 | 菜单值写成了数组而不是裸字符串 | `[1, "值"]` |
| 积木完全不执行 | opcode 拼错（如 `looks_seteffect` 应为 `looks_seteffectto`） | 用 `references/blocks.md` 核对 |
| 自定义积木打不开 | mutation 缺 `tagName` 或 `children` | 见上文第 5 节 |

自检命令：

```bash
python3 scripts/validate_sb3.py --sb3 你的作品.sb3
```

会依次做：结构与编码检查 → 官方 JSON Schema 校验 → scratch-vm 真实加载运行。
