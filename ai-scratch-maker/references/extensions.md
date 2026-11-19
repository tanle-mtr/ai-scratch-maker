# 扩展积木与自制积木

本文档回答两件事：

1. **Scratch 自带哪些扩展积木**（画笔 / 音乐 / 朗读 / 翻译 / 视频感应 / 语音转文字），
   怎么在 IR 里写、有什么坑。
2. **自制积木（自定义积木 / procedure）**怎么在 IR 里声明、怎么调用、有什么坑。

---

## 一、Scratch 自带扩展积木

Scratch 3.0 内置 6 个扩展，共 34 个积木。它们都需要在 `project.json` 的
`extensions` 数组里登记扩展 id —— IR 里写 `extensions: [pen]` 即可，
序列化器会自动处理。

### 1.1 画笔（pen）—— 13 个

| opcode | 作用 | 常用友好名 |
|---|---|---|
| `pen_penDown` | 落笔（开始画线） | `pen_down` |
| `pen_penUp` | 抬笔 | `pen_up` |
| `pen_stamp` | 盖章（把角色当前造型印在舞台上） | `pen_stamp` |
| `pen_clear` | 清空所有笔迹 | `pen_clear` |
| `pen_setPenColorToColor` | 设置画笔颜色 | `set_pen_color` |
| `pen_changePenColorParamBy` | 按参数改颜色（色相/饱和/亮度） | `change_pen_color` |
| `pen_setPenHueToNumber` | 设置色相 | `set_pen_hue` |
| `pen_changePenHueBy` | 改变色相 | `change_pen_hue` |
| `pen_setPenShadeToNumber` | 设置明度 | `set_pen_shade` |
| `pen_changePenShadeBy` | 改变明度 | `change_pen_shade` |
| `pen_setPenSizeTo` | 设置笔粗 | `set_pen_size` |
| `pen_changePenSizeBy` | 改变笔粗 | `change_pen_size` |
| `pen_penDown`（旧别名） | — | — |

**注意**：官方 `pen` 扩展实际有 `pen_setPenColorParamTo` 等「按参数」版本，
运行时 `getExtensionIdForOpcode` 会把它们都算作 `pen` 扩展。

IR 写法：

```yaml
project:
  extensions: [pen]
  sprites:
    - name: 画笔人
      costumes: [{name: 笔, asset: assets/pen.svg}]
      scripts:
        - - when_green_flag_clicked: null
          - set_pen_size: {size: 4}
          - set_pen_color: {color: "#ff0000"}
          - pen_down: null
          - repeat: {times: 36, do: [{move_steps: {steps: 10}}, {turn_right: {degrees: 10}}]}
          - pen_up: null
```

### 1.2 音乐（music）—— 9 个

| opcode | 作用 | 友好名 |
|---|---|---|
| `music_playDrumForBeats` | 敲鼓若干拍 | `play_drum_for_beats` |
| `music_midiPlayDrumForBeats` | MIDI 鼓（旧版） | `midi_play_drum_for_beats` |
| `music_playNoteForBeats` | 演奏音符 | `play_note_for_beats` |
| `music_restForBeats` | 休止若干拍 | `rest_for_beats` |
| `music_setInstrument` | 设置乐器 | `set_instrument` |
| `music_midiSetInstrument` | MIDI 乐器 | `midi_set_instrument` |
| `music_setTempo` | 设置 BPM | `set_tempo` |
| `music_changeTempo` | 改变 BPM | `change_tempo` |
| `music_getTempo` | 读取 BPM | `get_tempo` |

`music_playDrumForBeats` 的鼓组和 `music_playNoteForBeats` 的音高都是**菜单下拉**，
IR 里写字符串即可（如 `drum: 1`、`note: 60`）。

### 1.3 朗读（text2speech）—— 3 个

| opcode | 作用 | 友好名 |
|---|---|---|
| `text2speech_speakAndWait` | 把文字念出来 | `speak_and_wait` |
| `text2speech_setVoice` | 设置音色 | `set_voice` |
| `text2speech_setLanguage` | 设置语言 | `set_language` |

**注意**：朗读扩展调的是 Scratch 官方在线服务，需要联网；
音色和语言也是下拉菜单。

### 1.4 翻译（translate）—— 2 个

| opcode | 作用 | 友好名 |
|---|---|---|
| `translate_getTranslate` | 把文字翻译成另一种语言 | `get_translate` |
| `translate_getViewerLanguage` | 读取浏览者语言 | `get_viewer_language` |

同样需要联网。

### 1.5 视频感应（videoSensing）—— 4 个

| opcode | 作用 | 友好名 |
|---|---|---|
| `videoSensing_whenMotionGreaterThan` | 画面运动超过阈值时启动（帽子） | `when_motion_greater_than` |
| `videoSensing_videoOn` | 开启摄像头 | `video_on` |
| `videoSensing_videoToggle` | 切换摄像头开关 | `video_toggle` |
| `videoSensing_setVideoTransparency` | 设置视频透明度 | `set_video_transparency` |

**注意**：这个扩展需要摄像头权限，且 `videoSensing_whenMotionGreaterThan`
是**帽子积木**（写成 `when_motion_greater_than: 20`）。

### 1.6 语音转文字（speech2text）—— 3 个

| opcode | 作用 | 友好名 |
|---|---|---|
| `speech2text_whenIHearHat` | 听到语音时启动（帽子） | `when_i_hear` |
| `speech2text_listenAndWait` | 听取语音并等待 | `listen_and_wait` |
| `speech2text_getSpeech` | 读取听到的语音文本 | `get_speech` |

**注意**：`speech2text` 在 Scratch 3.0 里是**受限扩展**，
需要在项目设置里手动勾选才能用；用官方 parser 校验时不受影响。

### 1.7 扩展积木的坑

| 坑 | 说明 |
|---|---|
| **必须登记 extensions** | 只写积木不写 `extensions: [pen]`，Scratch 打开后会积木变黄/报错 |
| **扩展 id 大小写敏感** | `videoSensing`、`text2speech`、`speech2text` 都是**驼峰**，其余全小写 |
| **帽子积木要放最前** | `videoSensing_whenMotionGreaterThan`、`speech2text_whenIHearHat` 是帽子，必须是脚本的第一个积木 |
| **画笔是全局的** | 笔迹画在**舞台**上，不属于任何角色；多个角色同时用画笔会互相干扰 |
| **音乐/朗读/翻译要联网** | 无网络时会静默失败或报错 |
| **扩展积木也能用原始 opcode** | IR 里写 `pen_penDown` 和写 `pen_down` 等价 |

---

## 二、自制积木（自定义积木 / Procedure）

Scratch 的「自制积木」在 sb3 里由**三个积木**组成：

1. `procedures_definition` —— 定义（帽子）
2. `procedures_prototype` —— 原型（带参数声明）
3. `procedures_call` —— 调用

**不要手写这三个 opcode**，IR 里用 `target.procedures` 声明。

### 2.1 声明

```yaml
sprites:
  - name: 猫
    procedures:
      - name: 画正方形 %n
        args: [side]           # 参数名
        defaults: [50]         # 参数默认值（可省）
        warp: false            # true = 不逐帧执行（环绕执行）
        script:
          - repeat: {times: 4, do: [
              - move_steps: {var: side}
              - turn_right: {degrees: 90}
          ]}
    scripts:
      - - when_green_flag_clicked: null
        - call: {proc: 画正方形 %n, args: [60]}
```

### 2.2 关键规则

| 规则 | 说明 |
|---|---|
| **名字里 `%n` 必写** | Scratch 用 `%n` 标记「这是个带参数的积木」；`%s` 表示字符串参数 |
| **参数在脚本里当变量用** | `{var: side}` 就是读参数 `side`，不需要先声明变量 |
| **`warp: true`** | 「不逐帧执行」——循环多的自制积木建议开，否则会卡住整个脚本 |
| **调用要传够参数** | 参数个数必须与定义一致 |
| **自定义积木不能递归过深** | 运行时深度有限，递归自制积木容易栈溢出 |
| **自制积木属于某个角色** | 定义在哪个 sprite 上，就只能在那个 sprite 里调用（除非用克隆体） |

### 2.3 运行时编码（了解即可）

sb3 里：

- `procedures_prototype` 的 `fields.PROCEDURE_DEFINITION` 存着 `mutation` 对象：
  `proccode`（积木名）、`argumentids`（形如 `["arg1"]` 的 JSON 数组）、
  `argumentnames`（参数名 JSON 数组）、`argumentdefaults`、`warp`
- 参数在运行时被当作**变量**处理，`argumentids` 就是它们的变量 id
- `procedures_call` 的输入 `custom_block` 指向 prototype 的 id

序列化器已经处理好了这些，手写 IR 时不用管。

### 2.4 与扩展积木的区别

| | 自制积木 | 扩展积木 |
|---|---|---|
| 来源 | 你自己写（IR 声明） | Scratch 官方内置 |
| sb3 表现 | `procedures_*` 三个 opcode | 各扩展自己的 opcode 前缀 |
| 需要登记 | 不需要 | 需要 `extensions` |
| 编辑器里显示 | 「我的积木」分类 | 对应扩展分类 |
| 能被其它项目复用 | 能（导出积木） | 不能 |

---

## 三、两者一起用：给 agent 的建议

1. **先查积木全表**：`references/blocks.md` 里有全部 183 个积木（含 34 个扩展积木）
   的 opcode、形状、输入参数和 sb3 编码示例。
2. **扩展积木优先用官方实现**：不要试图用自制积木模拟画笔 —— 官方画笔能盖章、
   能改笔迹，而自制积木做不到。
3. **重复逻辑抽成自制积木**：像「移动到安全位置」「重置角色状态」这类
   在多处重复的逻辑，抽成 `procedures` 能让 IR 更短、更好维护。
4. **扩展 + 自制积木组合**：比如「用画笔画一个正方形」可以做成自制积木，
   内部调用画笔扩展的积木 —— 两级都是原生机制，Scratch 里完全正常。
