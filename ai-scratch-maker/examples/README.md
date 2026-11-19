# 示例索引

每个示例都包含 **IR 源文件** 和 **编译产物 `.sb3`**，产物已通过
「结构与编码检查 + 官方 JSON Schema + 官方 scratch-parser + scratch-vm 运行时
+ 行为冒烟测试 + 进阶技巧专项」六重校验。

重新编译全部示例：

```bash
cd ..
for f in examples/*.json examples/*.yaml; do
  base=$(basename "$f"); out="examples/output/${base%.*}.sb3"
  python3 scripts/build_sb3.py --ir "$f" --out "$out"
  python3 scripts/validate_sb3.py --sb3 "$out"
  node scripts/smoke_test.mjs "$out" --seconds 1.5
done
```

| 示例 | 演示的积木 / 能力 |
|---|---|
| `cat_chase.json` | 运动、外观、画笔、广播、变量、随机数、鼠标检测 |
| `cat_chase.yaml` | 同上，YAML 写法（推荐风格） |
| `cat_chase_ascii.json` | 纯 ASCII 变量名/消息名（跨平台与编码兼容性测试） |
| `example_lists.json` | 列表：加入、插入、删除、替换、读取、包含判断、长度 |
| `example_clones.json` | 克隆体：创建、作为克隆体启动、删除自己 |
| `example_procedures.json` | 自定义积木：定义、参数、调用 |
| `example_operators_sensing.json` | 运算（+ - × ÷ 随机 取整 比较 逻辑）与侦测（按键 鼠标 计时器） |
| `example_pen_sound.json` | 画笔全套（落笔/抬笔/盖章/改色/改粗细）+ 声音播放与音效 |
| `example_cloud.json` | **云变量**、全局变量作用域、广播 |
| `example_with_bg.json` | 带 ImageGen 生成的背景图 |
| **`cat_mouse.yaml`** | **完整小游戏：猫抓老鼠（大地图版）**——第一册 15 套技巧全用上 |
| `technique_probe.yaml` | 第一册技巧最小示教工程（克隆粒子 / 视野阴影 / 触屏命中 / 音效音量） |
| `technique_probe2.yaml` | 第二册示教①（敌人视野 AI / 平台跳跃物理 / 网格移动 / 克隆分身 / 背包商店 / 伤害飘字 / 云变量存档） |
| `technique_probe3.yaml` | 第二册示教②（网格推箱子 / 机关 / 多人云变量同步 / 命名造型动画 / 克隆子弹 / Cutscene 三段式 / 镜头关键帧） |
| `technique_probe4.yaml` | 第二册示教③（视差滚动 / Wavefront 寻路 / 塔防 / BGM 分场景 / 八方向动画 / 无尽生成 / 云变量编码） |
| `technique_probe5.yaml` | 第三册示教（回合制战斗 / 场景管理 / 菜单状态机 / 节奏判定 / 效用 AI / 射线视线 / 磁力与弹跳物理 / 成长装备） |
| `technique_probe6.yaml` | 第四册示教（AABB 碰撞 / Verlet 积分 / 绳索约束 / 万有引力 / 弹性碰撞 / 斜坡检测 / 对象池 / 空间分桶） |
| `technique_probe7.yaml` | 第五册示教（数据驱动瓦片地图 / 程序化音乐 / 平滑摄像机 / 缓动补间 / 昼夜循环 / 对话树 / 迷你地图 / 转场） |
| `technique_probe8.yaml` | 第六册示教（画笔基础 / 3D 线框 / 等距投影 / 射线投射迷宫 / 星空隧道 / 分形树 / 贝塞尔曲线 / 笔刷粒子） |
| `technique_probe9.yaml` | 第七册示教（画笔拖尾 / 克隆残影 / BGM 状态机与淡入淡出 / **多角色选项菜单** / 克隆三阶段生命周期 / 受击反馈 / 缓动登场 / 节奏判定） |
| `technique_probe10.yaml` | 第八册示教（**自带扩展积木**：音乐旋律 / 复调鼓点 / 视频摄像头叠加 / 朗读 / 翻译；除视频帽子与语音转文字外均通过无头校验） |
| `technique_probe11.yaml` | 第九册示教（**社区作品提炼**：数据驱动开关阵列 / 平台跳跃物理 / ★视野盲区 2D 可见性阴影光传 / 加载圈；已全部通过五层校验，运行时实测 阴影已算=1、实体在阴影=0、玩家落地 y=-120） |
| `technique_probe13.yaml` | **阴影光追专项示教**（`../references/deep-shadow-raycasting.md`）：射线×线段叉积求交 / ±ε 三射线可见性多边形 / 实体遮挡判定；五层校验全绿，实测 实体1、2 在阴影、实体3 可见，多边形顶点正确） |
| `technique_probe14.yaml` | **瓦片相机专项示教**（`../references/deep-tile-camera.md`）：24×16 滚动地图 / 相机跟随 / 边界钳制 / 只画相机窗口；五层校验全绿，实测 相机 (6,4)、贴边钳制 (12,7)、角落钳制 (0,0)、可见瓦片 108=12×9） |
| `ref_minecraft3d.yaml` | ★ **完整可玩参考工程**（第一人称体素光线投射）：DDA 体素射线 / 贴墙碰撞 / 画笔 48 列透视渲染；WASD 移动转向、空格挖方块、B 放方块；五层校验全绿，实测 首射线距离=13.5、碰撞测试=1、测试后px=1.7） |

---

## 猫抓老鼠（大地图版 · 完整小游戏）

玩法：方向键控制猫在**比舞台大 2 倍的客厅**里追老鼠，抓住得分，30 秒后结算。

### 用到的进阶技巧（全部来自 `../references/advanced-techniques.md`）

| 技巧 | 在本作品里怎么体现 |
|---|---|
| **大地图 + 小地图**（§1） | 世界 960×720（舞台 480×360）。`camera_x/camera_y` 两变量做相机，地图精灵反向移动；右下角小地图是缩小 8 倍的底图 + 猫/鼠两个置顶圆点，**按 M 开关** |
| **平滑移动**（§2） | 猫用「速度 + 摩擦」（加速度 0.8 / 摩擦 0.85）+ 对角线归一化 ×0.707；老鼠用缓动速度（3↔8 逼近 `speed_target`）+ 单位向量逃离（`mathop sqrt` 求模长） |
| **开关设计**（§3） | `game_state` 状态机（0 首页 / 1 游戏 / 2 结束）+ 广播调度；**M 小地图 / S 音效 / F 灯光** 三个 0-1 开关，全部用「边沿检测」实现，按住不会连发 |
| **视野阴影**（§4） | 整屏黑幕 `dark_overlay.png`（中央透明洞）盖住世界，洞跟着猫走；**先切小造型设 size 250% 再切回黑幕**，绕开 Scratch 的 150% 尺寸上限；**按 F 开关** |
| **弹窗与「当关闭被点击」**（§5） | 按 H 打开帮助弹窗 = 「半透明遮罩 + 面板 + 右上角 ×」三件套。遮罩负责**拦截穿透点击**；点 × 或点遮罩都能关；面板打开时猫的操作被冻结（`面板开` 变量） |
| **防搬（合规署名）**（§6） | 首页底部有署名卡「原作与美术：AI Scratch Maker」。**没有**写「禁止改编」——Scratch 全部作品是 CC BY-SA，官方禁止在说明里写禁止改编 |
| **克隆粒子系统**（§7） | 抓到老鼠时爆一簇 10 个火花克隆：`vx/vy/是否克隆` 都是**角色级私有变量**（每个克隆各一份），渐隐 + 阻尼 + 寿命结束 `delete this clone` |
| **触屏适配**（§8） | 预留 `touching: {object: _mouse_}` + `mousedown` 的写法（见 `technique_probe.yaml`），本作用键盘但两套可并存 |
| **血条 / 进度条**（§9） | 用 `digit_display` 角色展示（分数、剩余时间各一个两位数数字精灵，**自动把间距调到不重叠/不裁切**），并各带一个 `label` 文字标签说明「分数 / 时间」；不显示监视器 |
| **关卡数据表**（§10） | 见 `technique_probe.yaml` 的列表当配置表写法 |
| **缓动与物理**（§11） | 相机用 lerp 缓动跟随；老鼠速度缓动逼近目标值 |
| **音频控制**（§12） | `音效开` 开关控制 BGM 播放；`play_sound` / `play_sound_until_done` 播追逐 BGM 与抓鼠音效 |
| **投影与遮挡层次**（§13） | 层级：地图 → 家具 → 猫/鼠 → 黑暗 → 火花 → 聊天框 → 数字 → 小地图 → 标记 → 弹窗层 |
| **性能红线**（§14） | 特效 ≤ 3 层；克隆一次 10 个、寿命 16 帧 |
| **碰撞箱与障碍物**（§15） | **4 件家具是独立角色**（沙发/柜子/书桌/地毯），各自存世界坐标、每帧渲染到 `世界 - 相机` 跟着地图滚动；猫和老鼠都用 `touching [家具]?` 检测，猫做**分轴碰撞**（先走 X 再走 Y，撞了回退该轴并清零速度 → 沿墙滑动）。大地图图片本身**不再画家具**——画在图里的家具没有碰撞箱，玩家会直接穿过去 |

### 其它要素

| 要素 | 实现 |
|---|---|
| 首页 | `title_screen`（背景 + 开始按钮 + 署名卡），点开始才进正题 |
| 聊天框 | 自制聊天框角色（`chat_box` + `chat_say`），4 句台词，不用「说」气泡 |
| 音效 | `catch.wav`（`sfx pop`）、`gameover.wav`（`sfx lose`）、`hurry.wav`（`sfx swoosh`） |
| BGM | `bgm_chase.wav`（`bgm --mood chase`，4 小节无缝循环，舞台循环播放） |
| 朝向 | 两个角色都是 `rotationStyle: left-right`（不会朝上走就倒过来），按 `direction` 自动左右翻转 |
| 老鼠 AI | 随机游走；猫靠近 90px 内切换成逃离单位向量 + 加速 + 播逃跑音效 |
| 计分 | 碰撞 → 分数 +1 → 广播「抓到啦」→ 爆火花 → 老鼠躲 0.6 秒换位置出现 |
| 注释 | 每个关键积木都挂了中文注释（猫 4 条、老鼠 3 条、黑暗 2 条、弹窗 4 条…） |
| 积木整理 | 顶层脚本自动按网格排开，打开 Scratch 不会全叠在左上角 |

### 验证

```bash
node scripts/smoke_test.mjs examples/output/cat_mouse.sb3 --seconds 6 --catch
node scripts/verify_techniques.mjs examples/output/cat_mouse.sb3 /tmp/verify.txt
```

- 冒烟测试里 `分数` 会大于 0 → 「碰撞 → 计分 → 广播 → 老鼠重生」整条链路是通的；
  `地图` 的坐标恒等于 `(-camera_x, -camera_y)` → 相机与渲染链路正确。
- 专项测试输出 `ALL_NEW_TECH_OK` → 视野阴影结构与层级、帮助弹窗与「当关闭被点击」、
  克隆粒子结构与私有变量全部符合预期。

> ⚠️ 无头 scratch-vm 没有渲染器，**看不到 `size` 变化、也跑不了克隆生命周期**，
> 所以这两项只做了结构级校验；最终效果要在 Scratch 编辑器里目视确认。

---

## IR 写法速查

```yaml
project:
  name: 作品名
  extensions: [pen]                 # 用扩展时声明
  stage:
    backdrops: [{name: 草地, asset: assets/backdrop1.svg}]
    variables:                       # 全局变量
      分数: 0
      最高分: {value: 0, cloud: true}   # 云变量
    lists: {排行榜: []}               # 全局列表
    scripts:
      - - when_green_flag_clicked: null
        - broadcast: 开始
  sprites:
    - name: 小猫
      x: 0; y: 0; size: 100; direction: 90
      costumes: [{name: cat1, asset: assets/cat.svg}]
      sounds:   [{name: beep, asset: assets/beep.wav}]
      variables: {局部变量: 0}          # 该角色专属
      procedures:
        - name: 画正方形 %n
          args: [边长]
          script:
            - repeat: {times: 4, do: [{move_steps: {var: 边长}}, {turn_right: 90}]}
      scripts:
        - - when_green_flag_clicked: null
          - set_variable: {var: 分数, value: 0}
          - repeat: {times: 50, do: [{move_steps: 10}]}
```

积木的完整对照见 `../references/blocks.md`（183 个积木全覆盖）。

---

## 素材

`assets/` 里是示例用到的素材：

| 文件 | 说明 |
|---|---|
| `backdrop1.svg` | 纯 SVG 背景（草地） |
| `cat.svg` | 纯 SVG 角色（猫） |
| `beep.wav` | `gen_audio.py` 合成的提示音 |
| `sample_bg.png` | ImageGen 生成的背景原图（800×600） |
| `sample_bg_stage.png` | `prep_asset.py` 整理后的舞台背景（480×360） |
| `sample_bg_sprite.png` | `prep_asset.py` 整理后的角色图（200×150） |
| `cat_mouse/room.png` | 猫抓老鼠的背景（ImageGen → `prep_asset.py --mode stage --fill`） |
| `cat_mouse/cat.png` | 猫（ImageGen → `--remove-bg --trim --max 300`） |
| `cat_mouse/cat_left.png` | 猫的镜像造型（`--flip-h`） |
| `cat_mouse/mouse.png` | 老鼠（ImageGen → `--remove-bg --trim --max 240`） |
| `cat_mouse/mouse_left.png` | 老鼠的镜像造型（`--flip-h`） |
| `cat_mouse/bigmap.png` | 大地图（960×720，`make_ui_assets.py world`，**不含家具**） |
| `cat_mouse/沙发.png` `柜子.png` `书桌.png` `地毯.png` | **家具 = 独立障碍角色**（`make_ui_assets.py furniture`，像素尺寸 = 世界尺寸 1:1） |
| `cat_mouse/mini_map.png` | 小地图底图（120×90，`make_ui_assets.py minimap`） |
| `cat_mouse/cat_dot.png` / `mouse_dot.png` | 小地图上的猫/鼠标记点 |
| `cat_mouse/dark_overlay.png` | **视野阴影遮罩**（480×360 黑幕 + 中央透明洞，`make_ui_assets.py darkness`） |
| `cat_mouse/ui_mask.png` | **UI 遮罩**（半透明黑板，拦截穿透点击，`make_ui_assets.py mask`） |
| `cat_mouse/btn_close.png` | **关闭按钮 ×**（`make_ui_assets.py closebtn`） |
| `cat_mouse/help_panel.png` | 帮助面板（`make_ui_assets.py panel`） |
| `cat_mouse/byline.png` | 署名卡（防搬 · 合规署名，`make_ui_assets.py panel`） |
| `cat_mouse/catch.wav` | 抓到老鼠的音效（`gen_audio.py sfx --name pop`） |
| `cat_mouse/gameover.wav` | 游戏结束音效（`gen_audio.py sfx --name lose`） |
| `cat_mouse/hurry.wav` | 老鼠逃跑音效（`gen_audio.py sfx --name swoosh`） |
| `cat_mouse/bgm_chase.wav` | 追逐 BGM（`gen_audio.py bgm --mood chase --bars 4`，无缝循环） |

---

## 第二册：游戏系统与 AI（`technique_probe2.yaml`）

`technique_probe2.yaml` 是第二册技巧的最小可运行示教工程，
把「敌人视野 AI / 平台跳跃物理 / 网格移动 / 克隆分身 / 背包商店 / 伤害飘字 / 云变量存档」
集中在一个小工程里，方便对照 `../references/game-systems.md` 的 IR 配方。

| 角色 | 演示的技巧 |
|---|---|
| `守卫` | 敌人 AI：借朝向算角度差 + 归一化到 ±180° + 距离判定 → 视野锥；巡逻点用列表；每 0.1 秒检测一次 |
| `玩家` | 平台跳跃物理：水平/重力/地面/跳跃**四个独立循环** + 郊狼时间 + 跳跃缓冲；网格移动只在格点转向 |
| `地面` | 平台（`touching` 检测用） |
| `方块` | 克隆分身：本体自增编号再克隆，每个克隆用私有 ID 走不同分支 |
| `苹果` | 磁性吸附拾取 + 写入背包列表（名称映射表 `item num of ... in ...`） |
| `飘字` | 伤害飘字：克隆 + 私有变量 + 渐隐 + 到期删除 |
| 舞台 | 列表当数据表（背包/巡逻点）、云变量存最高分与关卡、连击与音量脉冲 |

验证：

```bash
node scripts/smoke_test.mjs examples/output/technique_probe2.sb3 --seconds 2
```

---

## 第三册示教：`technique_probe3.yaml`

| 角色 | 演示的技巧 |
|---|---|
| `推箱子手` | 网格解谜：整张地图存一条列表，`index = (y-1)*列数 + x`；推箱子要看「右边第二格」 |
| `子弹` | 投射物：克隆 + 发射瞬间 `point towards` 瞄准 + `repeat until` 碰到或出界 + `delete this clone` |
| `准星` | 跟随鼠标（`mouse_x` / `mouse_y`） |
| `演员` | Cutscene 三段式：`开始游戏`（重置数据）/ `游戏进行`（正常逻辑）/ `演出`（开头 `stop other scripts in this sprite`，结尾广播回「游戏进行」） |
| `打字机` | 打字机效果：`join` + `letter of` 逐字拼接 |
| `走路的` | 角色动画：命名造型走路循环（比 `next costume` 稳）+ 待机呼吸（size 振荡） |
| 舞台 | 镜头关键帧：4 条列表 + **计时器做全局节拍**（叠加 `wait` 会累积误差）；多人位置同步（云变量，每 0.2 秒写一次） |

验证：

```bash
node scripts/smoke_test.mjs examples/output/technique_probe3.sb3 --seconds 2
```

---

## 第四册示教：`technique_probe5.yaml`（第三册《玩法设计》）

`technique_probe5.yaml` 是第三册技巧的最小可运行示教工程（11 个角色 / 357 块）。

| 角色 | 演示的技巧 |
|---|---|
| `开始按钮` | 菜单铁律：点开始 = 广播「重置」，**不自己复位**（复位逻辑统一挂在广播上） |
| `战斗角色` / `敌人` | 回合制战斗：`C_`/`E_` 前缀属性、伤害保底、属性克制（独立 if）、`battle_state` 回合流程 |
| `传送门` | 场景管理：`当背景切换到` 钩子 + 切背景后重新定位 + 跨场景带数据（`来自场景`） |
| `玩家` | 菜单四态（标题/游戏/暂停/结算）、战斗输入锁定、经验曲线 |
| `判定点` | 节奏游戏：按**距离分段**判 Perfect/Great/Good（不除以距离，避免除零）+ 连击 |
| `敌人` | 效用 AI：追击分/攻击分/逃跑分，基准分先设成巡逻分 |
| `视线探针` | 射线与视线：步进 + 碰到颜色判遮挡；探针 `ghost 100` + 置后 |
| `磁铁` | 吸引力：距离衰减的磁力吸取，**力度夹紧防除零** |
| `弹球` | 物理：重力（速度累加）+ **乘性阻尼**（减法阻尼会让球反向加速飞走）+ 反弹贴回边界 |
| `选关按钮` | 选关界面：一个角色多造型，造型号 = 关卡号（`costume_number_name`） |

验证：

```bash
node scripts/smoke_test.mjs examples/output/technique_probe5.sb3 --seconds 3
```

---

## 第五册示教：`technique_probe6.yaml`（第四册《物理引擎》）

`technique_probe6.yaml` 是第四册技巧的最小可运行示教工程（10 个角色 / 451 块，含画笔扩展）。

| 角色 | 演示的技巧 |
|---|---|
| `碰撞体` | §51 AABB 包围盒：算 4 条边界 + 4 条比较；⚠️ 「与」只有 2 个输入 → 4 个条件必须嵌套成 2+2；圆形碰撞比较**距离平方**（不开方） |
| `粒子` | §52 Verlet 积分：新位置 = 2×当前 − 上一帧 + a×dt²；⚠️ Scratch 的 y+ 朝**上**，重力取负值；反弹要改「上一帧位置」而不是速度 |
| `绳` | §53 绳索：位置约束松弛（距离超了就把关节往回拉一半）+ 画笔渲染；角色必须 `don't rotate` |
| `恒星` | §54 参数化圆轨道：`x = 中心x + R·cos(θ)`（教学首选，稳定不飞走） |
| `行星` | §54 真引力：`a = G/r²`，⚠️ **方向必须指向中心（取负号）**；圆轨道初速度 `v = sqrt(G/r)`；用自己的私有 Verlet 状态 |
| `斜坡体` + `地面` | §56 斜坡检测：水平移动后尝试向上爬 8 像素，爬满仍在地面 = 坡太陡 → 退回原位 |
| `子弹` | §57 对象池：预建克隆体 + 状态列表（0 空闲/1 在用），用完归还而不是删除；广播不能带参数 → 用全局变量传索引 |
| `分桶体` | §58 空间分桶：格子号 = floor((坐标 + 舞台半宽) / 格宽)；走出边界要**水平垂直都回绕** |

验证：

```bash
node scripts/smoke_test.mjs examples/output/technique_probe6.sb3 --seconds 3
```

---

## 第六册示教：`technique_probe8.yaml`（第六册《画笔扩展与伪 3D》）

`technique_probe8.yaml` 是画笔扩展与伪 3D 的最小可运行示教工程（7 个角色 / 527 块，**必须**声明 `extensions: [pen]`）。

| 角色 | 演示的技巧 |
|---|---|
| `画笔基础` | §67 落笔 / 抬笔 / 图章 / 彩虹螺旋；画笔笔迹留在画笔图层，要每帧重画就得 `pen_clear` |
| `三维立方体` | §68 3D 线框：顶点用 vx/vy/vz 三段平行列表 + 12 条边的扁平边表，绕 Y/X 轴旋转后透视投影（`屏幕x = 焦距·3Dx/3Dz`） |
| `等距方块` | §69 等距投影：`(x−y)·0.866, (x+y)·0.5 − z` |
| `星空` | §71 星点朝你飞来（`stamp` 图章，不产生克隆体） |
| `分形树` | §72 递归自定义积木画分形树；⚠️ 递归**必须有长度阈值熔断**，否则栈溢出 |
| `贝塞尔` | §73 三次贝塞尔；⚠️ **Scratch 没有 `pow`**，幂要靠乘法展开 |
| `射线迷宫` | §70 第一人称射线投射：地图存列表，逐列发射线撞墙后画竖线；⚠️ **必须用垂直距离**（消鱼眼）；⚠️ 列表**初值必须写进 IR**（否则 sb3 里是空列表） |

验证：

```bash
node scripts/smoke_test.mjs examples/output/technique_probe8.sb3 --seconds 3
```

---

## 第七册示教：`technique_probe9.yaml`（第七册《游戏手感与交互》）

`technique_probe9.yaml` 是「让作品从作业变成作品」的四件套示教工程
（10 个角色 + 舞台 12 段脚本 / 267 块，含画笔与音乐扩展）。
> ⚠️ 本文件由 `scripts/gen_probe9.py` 生成（用 `yaml.dump` 保证 YAML 语法 100% 正确），
> 改逻辑请改生成器再重新生成。

| 角色 | 演示的技巧 |
|---|---|
| `彩带主角` | §75 **画笔拖尾**（不产生任何克隆体）；用 `sensing_of` 读 x 坐标做回环，不要依赖隐式 `x` 变量 |
| `残影主角` | §75 + §78 **克隆残影**三阶段生命周期（本体生产 → 克隆出生 → 克隆消亡）；⚠️ `是克隆` 私有标志位挡住"本体事件帽子被克隆体触发" |
| `克隆监控` | §78 **克隆预算**：计数 + 超 200 预警；⚠️ 超过 300 时 Scratch 会**静默丢弃**新克隆 |
| `音乐控制` | §76 **BGM 状态机** + **淡入淡出**（一个 `forever` 同时管两个方向）+ §76.4 **程序化旋律**（音乐扩展，零素材） |
| `按钮一/二/三` | §77 **多角色选项菜单**：**全程不用「询问」积木**；每个选项一个角色按钮，按钮只广播意图 |
| `登场角色` | §80 **缓动滑入**：`divide` 指数逼近，⚠️ 必须加停止条件（`stop` 的选项值是英文 `this script`） |
| `受击目标` | §79 **受击反馈**：闪白（`change_effect`）+ 击退 + 死亡广播 |
| `顿帧角色` | §79.3 **顿帧**：全局 `顿帧` 标记，所有会动的角色一起停 |
| 舞台（12 段） | §77 菜单状态机 + §79 顿帧广播 + §81 节奏判定（Perfect/Good/Miss）+ §81.3 连击 + §82 广播解耦 |

关键 IR 写法（已全部实测通过）：

```yaml
# 克隆体：注意键名是 clone，不是 target
- create_clone_of: { clone: _myself_ }
- when_start_as_clone: null
- delete_this_clone: null

# 外观特效：effect 值是大写英文
- change_effect: { effect: GHOST, value: 5 }
- change_effect: { effect: COLOR, value: 50 }
- change_size: { value: 5 }

# 碰到鼠标指针：下拉值必须是 _mouse_
- if: { cond: { touching_mouse_pointer: { object: _mouse_ } }, do: [ ... ] }
- if: { cond: { not: { operand: { touching_mouse_pointer: { object: _mouse_ } } } }, do: [ ... ] }

# 停止脚本：选项值是英文
- stop: { option: this script }
```

验证：

```bash
node scripts/smoke_test.mjs examples/output/technique_probe9.sb3 --seconds 3
```

> ⚠️ **无头测试盲区**：克隆体在 headless VM 里会被立刻回收，
> 所以残影 / 克隆菜单 / 悬停高亮 / 音频只能做**结构级校验**，
> 最终效果必须在 Scratch 编辑器里目视确认。

---

## 第八册示教：`technique_probe10.yaml`（第八册《Scratch 自带扩展积木》）

`technique_probe10.yaml` 是 5 个自带软件扩展（音乐 / 朗读 / 翻译 / 视频感应 / 语音转文字）
的最小可运行示教工程（舞台 3 段脚本 + `鼓手` 角色 1 段 / 33 块，
`extensions: [music, text2speech, translate, videoSensing]`）。

| 角色 / 舞台脚本 | 演示的技巧 | 无头可行性 |
|---|---|---|
| 舞台·绿旗 | §83 **程序化旋律**（用 `旋律` 列表驱动 `music_play_note_for_beats`）+ §85 加速 + §90 **视频摄像头叠加**（`video_sensing_video_toggle` / `set_video_transparency`） | ✅ 跑通校验 |
| `鼓手`·绿旗 | §84 **复调鼓点**：军鼓 + 踩镲 + 休止循环，与旋律**两条线程同时跑**（单角色是单声部） | ✅ 跑通校验 |
| 舞台·`when_receive: 旁白` | §86 **朗读说话**（`text2speech_speak_and_wait` + `set_voice` + `set_language`） | ⚠️ 联网才出声，未在无头执行 |
| 舞台·`when_receive: 翻译` | §88 **翻译气泡**（`translate_get_translate`）+ §89 浏览者语言（`get_viewer_language`） | ⚠️ 联网才翻译，未在无头执行 |

关键 IR 写法（已全部实测通过）：

```yaml
# 音乐：音高是 MIDI 式数字（60=中央 C）；旋律从列表读
- music_set_tempo: { tempo: 100 }
- music_set_instrument: { instrument: 0 }          # 0 钢琴 … 21 管弦乐
- music_play_note_for_beats: { note: { var: 当前音 }, beats: 0.5 }
- music_play_drum_for_beats: { drum: 1, beats: 0.25 }   # 1 军鼓 / 5 踩镲
- music_rest_for_beats: { beats: 0.25 }

# 视频感应：开摄像头 + 调透明度（命令积木，无头不崩）
- video_sensing_video_toggle: { video_state: "on" }
- video_sensing_set_video_transparency: { transparency: 50 }

# 朗读 / 翻译（报告积木直接喂给 say；联网才生效）
- text2speech_speak_and_wait: { words: "欢迎" }
- translate_get_translate: { words: "Hello", language: "Chinese (Simplified)" }
```

验证：

```bash
python3 scripts/build_sb3.py --ir examples/technique_probe10.yaml \
  --out examples/output/technique_probe10.sb3 --workdir /tmp/probe10
python3 scripts/validate_sb3.py --sb3 examples/output/technique_probe10.sb3
node scripts/smoke_test.mjs examples/output/technique_probe10.sb3 --seconds 4
```

> ⚠️ **扩展积木无头盲区**：本示教里**音乐 + 视频命令积木**能端到端跑通无头校验；
> 朗读 / 翻译需联网、无头只能结构级校验；**视频感应帽子**（`when_motion_greater_than`，
> 无渲染器会崩溃）和**语音转文字**（需 Web Worker，无头无法加载）仅在手册里讲解、未放进本示教，
> 真实效果都必须在 Scratch 编辑器 + 摄像头 / 麦克风 / 联网环境下目视确认。

---

## 完整可玩参考工程：`ref_minecraft3d.yaml`（第一人称体素光线投射）

> 教程：见本册手册的「完整可玩参考工程」一节；技术来源见 `../references/community-techniques.md` §98。
> 这不是「示教片段」，而是一个**能玩的完整游戏**。

### 玩法

| 操作 | 作用 |
|---|---|
| `W` / `↑` | 前进（贴墙会被挡住） |
| `S` / `↓` | 后退 |
| `A` / `←` | 左转 |
| `D` / `→` | 右转 |
| `空格` | 挖掉正前方的方块 |
| `B` | 在命中处放一个方块 |

地图是 16×16 的体素空间（外墙 + 内部柱子），用画笔实时画出 48 条视线列，
墙高 ∝ 1/距离，灰度按距离衰减 —— 就是经典的第一人称迷宫射线投射。

### 三个自定义积木

| 积木 | 作用 | 对标原作 |
|---|---|---|
| `查格 %n %n` | 取某格的方块值（0 空 / 1 墙），越界当墙 | — |
| `投射射线 %n` | 从玩家沿指定角度投一条 DDA 射线，返回 `命中距离` + `命中格X/Y` | `TestRay` |
| `渲染` | 48 条视线逐列画墙体 | `NorthEast` |

### 运行时自检值（冒烟实测）

| 变量 | 实测 | 含义 |
|---|---|---|
| 首射线距离 | `13.5` | 玩家 (1.5,1.5) 朝东，命中 x=15 的外墙 → 15−1.5 = 13.5 ✓ |
| 碰撞测试 | `1` | 西侧 (0,1) 是外墙 → 阻挡成立 ✓ |
| 测试后px | `1.7` | 向前一步成功（1.5 → 1.7）✓ |

验证：

```bash
python3 scripts/build_sb3.py --ir examples/ref_minecraft3d.yaml \
  --out examples/output/ref_minecraft3d.sb3 --workdir /tmp/refmc
python3 scripts/validate_sb3.py --sb3 examples/output/ref_minecraft3d.sb3
node scripts/smoke_test.mjs examples/output/ref_minecraft3d.sb3 --seconds 5
```

> ⚠️ 画笔渲染的画面在无头环境看不到，最终观感（透视、灰度、挖掘手感）
> 必须在 Scratch 编辑器里目视确认。

---

## 阴影光追专项：`technique_probe13.yaml`

> 教程：`../references/deep-shadow-raycasting.md`

- 舞台存 3 条**墙体线段**（`墙AX/AY/BX/BY`）与 6 个**墙角点**；
- 角色 `光追` 持有三个自定义积木：`投射方向 %n %n`（叉积求交）、`算顶点 %n %n`（±ε 三射线）、`实体判定 %n %n`；
- 绿旗后依次：算 6 个可见点 → 画可见性多边形 → 画墙 → 判定 3 个实体并画连线（红=阴影 / 绿=可见）。

**运行时自检值（冒烟实测）**：

| 变量 | 实测 | 含义 |
|---|---|---|
| 实体1在阴影 | `1` | (170,0) 被右侧竖墙挡住 ✓ |
| 实体2在阴影 | `1` | (0,200) 被上方横墙挡住 ✓ |
| 实体3在阴影 | `0` | (150,170) 在两面墙的夹缝里，可见 ✓ |
| 顶点X / 顶点Y | `[-99.5, 99.5, 99.5, -39.9, 39.9, -99.5]` 等 | 多边形顶点比墙角略靠内，正是 ±ε 取最近的效果 ✓ |

---

## 瓦片相机专项：`technique_probe14.yaml`

> 教程：`../references/deep-tile-camera.md`

- 舞台存 24×16 = 384 格的**扁平列表**地图；相机视野 12×9 格，每格 40 像素；
- 角色 `玩家` 持有 `更新相机` 过程（跟随 + **边界钳制**），并广播 `刷新`；
- 角色 `渲染` 收到 `刷新` 后只画**相机窗口内**的格子（滚动地图跑得动的关键）。

**运行时自检值（冒烟实测）**：

| 变量 | 实测 | 含义 |
|---|---|---|
| 相机X / 相机Y | `6` / `4` | 玩家 (12,8) → 相机 = 玩家 − 半视野 ✓ |
| 相机X测试 / 相机Y测试 | `12` / `7` | 玩家贴到 (23,15) → 钳制在 `地图宽−视野宽` / `地图高−视野高` ✓ |
| 相机X测试2 / 相机Y测试2 | `0` / `0` | 玩家走到 (0,0) → 钳制为 0 ✓ |
| 可见瓦片数 | `108` | = 12 × 9，恰好一屏 ✓ |
