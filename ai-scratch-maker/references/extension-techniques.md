# Scratch 自带扩展积木（第八册：§83–§92）

> 本册聚焦 **Scratch 3.0 内置的 5 个软件扩展**（画笔已在第六册，硬件扩展 Makey/ micro:bit 等不在本 skill 范围）：
>
> | 扩展 | 积木数 | 用途 | 离线可用 | 本册章节 |
> |---|---|---|---|---|
> | **音乐 music** | 9 | 合成音符 / 鼓点 / 乐器 / 速度 | ✅ 完全离线 | §83–§85 |
> | **朗读 text2speech** | 3 | 让角色念出文字 | ⚠️ 需联网（官方服务） | §86–§87 |
> | **翻译 translate** | 2 | 实时翻译 / 读浏览者语言 | ⚠️ 需联网 | §88–§89 |
> | **视频感应 videoSensing** | 4 | 摄像头动作触发 / 视频叠加 | ⚠️ 需摄像头 | §90–§91 |
> | **语音转文字 speech2text** | 3 | 听指令 / 转写语音 | ❌ 受限扩展 + 需联网麦克风 | §92 |
>
> 每节给本 skill 的 IR 写法。**✅ = 能生成 sb3 且能在无头环境跑通校验**；
> **⚠️ = 能生成 sb3（结构合法），但执行效果依赖联网/摄像头，无头环境只能做结构级校验**；
> **❌ = 无头运行时无法加载/执行（崩溃或需 Web Worker），只能在 Scratch 编辑器里目视确认**。
>
> ⚠️ **铁律**：用到任何一个扩展，IR 根**必须**写 `extensions: [music]`（id 大小写敏感：
> `videoSensing` / `text2speech` / `speech2text` 是驼峰，其余全小写），否则 Scratch 打开后
> 积木全部变黄报错。本册所有示例都已声明对应扩展。

## 速查表

| 想做什么 | 章节 | 关键积木 |
|---|---|---|
| 用数据列表驱动一段旋律（小星星等） | §83 程序化旋律 | `music_play_note_for_beats` / `music_set_instrument` / `music_set_tempo` |
| 鼓点节奏 + 休止，让音符不挤成一团 | §84 鼓点与休止 | `music_play_drum_for_beats` / `music_rest_for_beats` |
| 不同场景切换 BGM（标题/战斗/胜利） | §85 动态 BGM 状态机 | `music_set_instrument` / `music_set_tempo` + 广播 |
| 让角色开口说话（念台词） | §86 朗读说话 | `text2speech_speak_and_wait` / `set_voice` / `set_language` |
| 多语言旁白 / 本地化 | §87 多语言旁白 | `text2speech_set_language` + `speak_and_wait` |
| 实时把一句台词翻译成外语气泡 | §88 翻译气泡 | `translate_get_translate` |
| 按「浏览者语言」自动切换界面文字 | §89 浏览者语言 | `translate_get_viewer_language` |
| 开启摄像头并把画面透叠到舞台 | §90 视频叠加 | `video_sensing_video_toggle` / `set_video_transparency` |
| 挥手 / 动作超过阈值就触发事件 | §91 动作触发 | `video_sensing_when_motion_greater_than`（帽子） |
| 听玩家说出的指令词 | §92 语音指令 | `speech2text_when_i_hear_hat` / `listen_and_wait` / `get_speech` |

---

## 83. 音乐：程序化旋律（音符 / 乐器 / 速度）✅

音乐扩展是**自带扩展里唯一能完全离线跑通**的一个——它不调网络、不依赖摄像头，
靠 Scratch 内置的合成器发声。所以它是「扩展积木技巧」里最值得吃透的。

### 83.1 三个核心参数

| 积木 | 输入 | 说明 |
|---|---|---|
| `music_play_note_for_beats` | `note`（音高）、`beats`（时值） | 演奏一个音，阻塞到时值结束 |
| `music_set_instrument` | `instrument`（0–21 下拉） | 切换乐器：**0 钢琴 / 1 吉他 / 2 贝斯 / 3 大提琴 / 4 八音盒 / 5 颤音琴 / 6 马林巴 … 21 管弦乐** |
| `music_set_tempo` / `music_change_tempo` | `tempo`（BPM） | 设置 / 改变速度；`music_get_tempo` 读取当前 BPM |

**音高 = MIDI 式数字**：`60` = 中央 C（C4），每 +1 升半音、`+12` 升八度。
常用：`C=60 D=62 E=64 F=65 G=67 A=69 B=71 C5=72`。

**时值 = 拍**：1 拍的时长 = `60 / BPM` 秒。BPM=120 时 1 拍=0.5 秒；
`beats: 0.5` 就是半拍（八分音符）。

> ⚠️ **音乐积木会阻塞线程**：`play_note_for_beats` 和后面的 `等待` 一样，会卡住当前脚本
> 直到音播完。所以「边放音乐边做别的」要靠**多个角色各开一条绿旗脚本**（见 §84 复调）。

### 83.2 IR 配方：用列表驱动一段旋律（✅ 本 skill 支持）

把音符存进 `旋律` 列表，循环读出来播——这是「数据 / 逻辑分离」的标准做法，改歌只改列表：

```yaml
project:
  name: 小星星
  extensions: [music]
  stage:
    backdrops: [{name: 背景1, asset: assets/backdrop1.svg}]
    lists: { 旋律: [60,60,67,67,69,69,67, 65,65,64,64,62,62,60] }
    variables: { 序号: 0, 当前音: 0 }
    scripts:
      - - when_green_flag_clicked: null
        - music_set_tempo: { tempo: 100 }
        - music_set_instrument: { instrument: 0 }      # 钢琴
        - set_variable: { var: 序号, value: 1 }
        - repeat: { times: 14, do:
            [ { set_variable: { var: 当前音, value: { item_of_list: { index: { var: 序号 }, list: 旋律 } } } }
            , { music_play_note_for_beats: { note: { var: 当前音 }, beats: 0.5 } }
            , change_variable: { var: 序号, value: 1 } ] }
```

> ✅ **已实测**：`note` 直接填数字或填 `{var: …}` / `{item_of_list: …}` 都能生成合法 sb3，
> 无头环境能跑通运行时校验（合成器在无头里是 no-op，不报错）。

---

## 84. 音乐：鼓点节奏与休止（复调）✅

只有旋律会「干」。加鼓点 + 休止，节奏才立得住。

### 84.1 鼓与休止

| 积木 | 输入 | 说明 |
|---|---|---|
| `music_play_drum_for_beats` | `drum`（1–18 下拉）、`beats` | 敲鼓：`1 军鼓 / 2 嗵鼓 / 4 吊镲 / 5 闭合踩镲 …` |
| `music_rest_for_beats` | `beats` | **休止**：静音若干拍 |

> ⚠️ **休止不是可有可无**：音乐积木是「阻塞式」的，但同一个脚本里连续两个 `play_note`
> 会**无缝衔接**（前一个刚结束下一个立刻响），听感拥挤。`rest_for_beats` 用来「留白」，
> 把音符隔开成乐句。另外 `play_note` 与 `play_drum` 默认是**单声部**——同一时刻只在放一个音。

### 84.2 IR 配方：旋律 + 鼓点复调（✅ 本 skill 支持）

「复调」= 旋律和鼓**各占一个角色**，两条绿旗脚本同时跑，互不阻塞：

```yaml
# 舞台放旋律（同 §83）；鼓手角色放鼓点：
sprites:
  - name: 鼓手
    costumes: [{name: 点, asset: assets/dot.svg}]
    variables: { 拍: 0 }
    scripts:
      - - when_green_flag_clicked: null
        - set_variable: { var: 拍, value: 1 }
        - repeat: { times: 8, do:
            [ { music_play_drum_for_beats: { drum: 1, beats: 0.25 } }   # 军鼓
            , { music_rest_for_beats: { beats: 0.25 } }
            , { music_play_drum_for_beats: { drum: 5, beats: 0.25 } }   # 踩镲
            , { music_rest_for_beats: { beats: 0.25 } }
            , change_variable: { var: 拍, value: 1 } ] }
```

> ✅ 两个角色同时绿旗 → 两个独立线程 → 旋律与鼓重叠播放，得到「带伴奏的曲子」。

---

## 85. 音乐：动态 BGM 状态机 ✅

游戏不同场景要换背景音乐（标题页轻快、战斗紧张、胜利欢快）。
配合第一册 §3 的状态机 + 广播，用 `set_instrument` + `set_tempo` 切换「曲风」：

```yaml
stage:
  variables: { 场景: "标题" }
  scripts:
    - - when_green_flag_clicked: null
      - music_set_tempo: { tempo: 90 }
      - music_set_instrument: { instrument: 4 }      # 八音盒 → 标题页
    - - when_receive: 进入战斗
      - music_set_tempo: { tempo: 150 }
      - music_set_instrument: { instrument: 8 }      # 太鼓 → 战斗
    - - when_receive: 胜利
      - music_set_tempo: { tempo: 120 }
      - music_set_instrument: { instrument: 0 }      # 钢琴 → 胜利
```

> ⚠️ **速度是全局的**：`tempo` 是舞台级属性，改一次影响**所有**音乐积木。
> 所以「同一时刻多首曲子用不同速度」做不到——只能靠「换乐器」区分场景色彩，
> 或让它们**先后**播放。需要叠混音时，还是用第七册 §76 的**声音文件 BGM** 更合适
> （声音文件之间可以叠，音乐扩展是单声部合成）。

---

## 86. 朗读：让角色开口说话 ⚠️

朗读扩展把文字念出来，比 `say` 气泡更「有戏」——适合旁白、教学、无障碍。

| 积木 | 输入 | 说明 |
|---|---|---|
| `text2speech_speak_and_wait` | `words`（文字） | 念出文字，**念完才继续**（阻塞） |
| `text2speech_set_voice` | `voice`（下拉） | 音色：`ALTO 中音 / SOPRANO 女高 / TENOR 男中 / GIANT 巨人 / KITTEN 小猫 / SQUEAK 吱吱` |
| `text2speech_set_language` | `language`（下拉） | 语言：`Chinese / English / Japanese / French / Spanish …` |

```yaml
- when_green_flag_clicked: null
  - text2speech_set_language: { language: "Chinese" }
  - text2speech_set_voice: { voice: "ALTO" }
  - text2speech_speak_and_wait: { words: "欢迎来到我的作品！" }
```

> ⚠️ **联网才出声**：朗读调的是 Scratch 官方在线语音服务，**无网络时静默失败**。
> ⚠️ **阻塞线程**：`speak_and_wait` 会等到念完，适合「一句接一句」的对白；
> 不要把它塞进 `forever` 里（会一直念）。
> ⚠️ **下拉值要写官方字符串**：`"Chinese"` / `"English"` 等，写错语言不会报错但可能念错。
> ⚠️ **无头限制**：本 skill 能生成合法 sb3，但执行时发网络请求，无头环境**只能做结构级校验**，
> 听不到声音——最终要在 Scratch 编辑器联网确认。

---

## 87. 朗读：多语言旁白与本地化 ⚠️

用 `set_language` + `speak_and_wait` 给不同语种玩家念不同的旁白。
把「台词」按语言分列表，或用 `when_receive` 分发：

```yaml
stage:
  variables: { 语言: "Chinese" }
  scripts:
    - - when_receive: 旁白_中文
      - text2speech_set_language: { language: "Chinese" }
      - text2speech_speak_and_wait: { words: "关卡开始，祝你好运。" }
    - - when_receive: 旁白_英文
      - text2speech_set_language: { language: "English" }
      - text2speech_speak_and_wait: { words: "Level start. Good luck!" }
```

> ✅ 配合 §89 的「浏览者语言」可以做到「自动选语种旁白」。

---

## 88. 翻译：实时翻译对话气泡 ⚠️

`translate_get_translate` 是个**报告积木**（返回字符串），把一段文字翻译成目标语言，
直接喂给 `say` 当气泡：

| 积木 | 输入 | 说明 |
|---|---|---|
| `translate_get_translate` | `words`、`language`（下拉） | 翻译 `words` 成 `language`（`"Chinese (Simplified)"` / `"English"` / `"Japanese"` …） |
| `translate_get_viewer_language` | 无 | 报告**当前浏览者**的浏览器语言 |

```yaml
- when_green_flag_clicked: null
  - say: { text: { translate_get_translate: { words: "Hello", language: "Chinese (Simplified)" } }, secs: 2 }
```

> ⚠️ **联网才翻译**：无网络时返回空或原文，不报错。
> ⚠️ **语言下拉字符串**要写全，例如 `"Chinese (Simplified)"`（含括号与空格），写错不翻译。
> ⚠️ **无头限制**：同 §86，只能结构级校验。

---

## 89. 翻译：按浏览者语言自动切换文字 ⚠️

`translate_get_viewer_language` 读出玩家浏览器语言，据此切换界面 / 台词，做「零配置本地化」：

```yaml
stage:
  variables: { 我的语言: 0 }
  scripts:
    - - when_green_flag_clicked: null
      - set_variable: { var: 我的语言, value: { translate_get_viewer_language: null } }
      - if: { cond: { equals: [ { var: 我的语言 }, "zh" ] }, do:
          [ { broadcast: 显示中文 } ], else: [ { broadcast: 显示英文 } ] }
    - - when_receive: 显示中文
      - say: { text: "你好，世界", secs: 2 }
    - - when_receive: 显示英文
      - say: { text: "Hello, world", secs: 2 }
```

> ✅ 也可以直接 `translate_get_translate` 把固定文案翻成玩家语言，省去多套硬编码文案。

---

## 90. 视频感应：开启摄像头与透明叠加 ✅（结构）/ ⚠️（效果需摄像头）

视频感应让你把**摄像头画面**透叠到舞台上，或读取「画面里的运动 / 视频」数值。
先开摄像头、调透明度，画面才会显示：

| 积木 | 输入 | 说明 |
|---|---|---|
| `video_sensing_video_toggle` | `video_state`（下拉 `on`/`off`） | 开 / 关摄像头 |
| `video_sensing_set_video_transparency` | `transparency`（0–100） | 视频透明度：**0 = 画面完全可见，100 = 完全透明** |
| `video_sensing_video_on` | `attribute`（motion/video）、`subject`（stage/sprite） | 报告「视频/运动」当前是否开启（布尔） |

```yaml
- when_green_flag_clicked: null
  - video_sensing_video_toggle: { video_state: "on" }
  - video_sensing_set_video_transparency: { transparency: 50 }   # 半透明叠加
  - if: { cond: { video_sensing_video_on: { attribute: "video", subject: "stage" } }, do:
          [ { say: { text: "摄像头已开启", secs: 1 } } ] }
```

> ✅ **命令积木（toggle / set_transparency / video_on 报告）本 skill 能生成并跑通无头校验**——
> 它们不访问摄像头渲染器，无头里是 no-op，不崩溃。
> ⚠️ **真实效果需摄像头权限**：在 Scratch 编辑器里首次会弹「允许摄像头」。透明度调到 0
> 画面最清楚，调到 100 画面消失（只剩角色）。

---

## 91. 视频感应：挥手 / 动作触发 ❌（无头无法校验）

`video_sensing_when_motion_greater_than` 是**帽子积木**：画面里运动超过阈值就触发，
做「隔空挥手控制」「体感游戏」的神器：

```yaml
sprites:
  - name: 感应区
    costumes: [{name: 点, asset: assets/dot.svg}]
    scripts:
      - - video_sensing_when_motion_greater_than: { reference: 20 }
        - broadcast: 挥手触发
        - say: { text: "我看到你动啦！", secs: 1 }
```

| 输入 | 说明 |
|---|---|
| `reference`（阈值，0–100） | 运动强度超过它才触发；安静环境设 10–20，热闹环境设 30–50 |

> ❌ **无头硬限制**：这个帽子积木每帧调用 `_analyzeLocalMotion`，要读渲染器的
> `_allDrawables`——无头 VM 没有渲染器 → **直接崩溃**，无法在本地跑通运行时校验。
> 所以本册它在无头只能**结构级校验**（能生成合法 sb3），真实触发效果**必须到
> Scratch 编辑器 + 摄像头**里目视确认。
> ⚠️ **帽子必须放脚本最前**（和其它帽子一样）。阈值要现场调：太灵敏会乱触发，太钝没反应。

---

## 92. 语音转文字：听见指令 ❌（无头无法加载）

语音转文字是**受限扩展**（项目设置里要手动勾选才能用），让作品「听懂」玩家说的话：

| 积木 | 输入 | 说明 |
|---|---|---|
| `speech2text_when_i_hear_hat` | `phrase`（词/句） | 帽子：听到 `phrase` 就触发 |
| `speech2text_listen_and_wait` | 无 | 录音并等待，把听到的内容存起来 |
| `speech2text_get_speech` | 无 | 报告最近一次听到的文字（字符串） |

```yaml
stage:
  scripts:
    - - speech2text_when_i_hear_hat: { phrase: "开始" }
      - broadcast: 游戏开始
    - - when_green_flag_clicked: null
      - speech2text_listen_and_wait: null
      - say: { text: { speech2text_get_speech: null }, secs: 2 }
```

> ❌ **无头硬限制**：语音转文字扩展用 **Web Worker** 加载，本地的 Node 无头 VM
> 没有 `Worker` → `loadProject` 直接 `ReferenceError`。所以它**连运行时加载都过不了**，
> 只能在 Scratch 编辑器（联网 + 麦克风）里用。
> ⚠️ **受限扩展**：scratch-vm 默认不挂它，需要在项目里开启；用官方 parser 校验不受影响。
> ⚠️ **联网 + 麦克风**：识别走官方服务，离线/无麦不可用。

---

## 附录：第八册积木支持对照

| 技巧 | 关键积木 | 本 skill 支持 | 无头运行 |
|---|---|---|---|
| §83 程序化旋律 | `music_play_note_for_beats` / `music_set_instrument` / `music_set_tempo` | ✅ | ✅ 可跑通 |
| §84 鼓点与休止 | `music_play_drum_for_beats` / `music_rest_for_beats` / 复调 | ✅ | ✅ 可跑通 |
| §85 动态 BGM | `music_set_instrument` / `music_set_tempo` + 广播 | ✅ | ✅ 可跑通 |
| §86 朗读说话 | `text2speech_speak_and_wait` / `set_voice` / `set_language` | ✅ 生成 | ⚠️ 联网才出声 |
| §87 多语言旁白 | `text2speech_set_language` + `speak_and_wait` | ✅ 生成 | ⚠️ 联网 |
| §88 翻译气泡 | `translate_get_translate` | ✅ 生成 | ⚠️ 联网 |
| §89 浏览者语言 | `translate_get_viewer_language` | ✅ 生成 | ⚠️ 联网 |
| §90 视频叠加 | `video_sensing_video_toggle` / `set_video_transparency` / `video_on` | ✅ 生成 | ✅ 命令积木不崩 |
| §91 动作触发 | `video_sensing_when_motion_greater_than`（帽子） | ✅ 生成 | ❌ 无渲染器崩溃 |
| §92 语音指令 | `speech2text_when_i_hear_hat` / `listen_and_wait` / `get_speech` | ✅ 生成 | ❌ 需 Web Worker |

> **扩展积木通用铁律（务必先看）**
> 1. **必须登记 `extensions`**：用了哪个扩展就在 IR 根写 `extensions: [music]` 等；
>    漏写 → Scratch 打开后积木全黄报错。
> 2. **扩展 id 大小写敏感**：`videoSensing` / `text2speech` / `speech2text` 是**驼峰**，
>    其余（pen / music / translate）全小写。
> 3. **帽子积木放最前**：`video_sensing_when_motion_greater_than`、
>    `speech2text_when_i_hear_hat` 是帽子，必须是脚本第一个积木。
> 4. **音乐是单声部合成**：同角色同时刻只放一个音；多声部靠「多角色各开绿旗脚本」。
> 5. **联网 / 摄像头 / 麦克风依赖**：朗读、翻译要联网；视频感应要摄像头；语音转文字
>    要麦克风 + 联网且是受限扩展。无头环境只对**音乐 + 视频命令积木**能端到端跑通校验。
> 6. **下拉菜单写官方字符串**：乐器/鼓/语言/音色/视频状态的下拉值都是固定字符串，
>    错拼不会报错但功能异常（如语言翻不出、音色不变）。
