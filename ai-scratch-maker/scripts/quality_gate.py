#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""作品质量门禁：把「高质量」变成可验收的数字。

诊断背景：现有示例积木数最多 1566 块（超过 FNAF 的 1005 块），但 82% 零音效、
造型中位 2–4 个、产物中位 ~90 KB。瓶颈是**资产密度**，不是逻辑复杂度。

本门禁分四层：
  A. 资产密度（6 项计数）：造型/音效/角色/体积/场景/积木 —— 保证「看得见的东西够多」。
     【2026-11-09】体积(min_bytes)只作防构建空壳下限，统一 150000 字节；不再是质量指标
     （旧值 1MB/8MB 来自社区素材整库内嵌污染，与「矢量优先」口径冲突）。
  B. 玩法完整度（3 项启发式，仅 game 品类强制）：玩家可操控 / 胜负条件 / 重玩价值
     —— 保证「像个能玩的完整作品」，而非零交互幻灯片或不能操控的展示。
  C. 观感质量（启发式评分 + 明确违规 WARN，所有品类都分析，默认不硬拦）：
     渐变体积感 / 窗口圆角 / 缓动过渡 / 配色合规（冷灰、深绿填充、调色板合规率，§198）。
  D. 生图素材硬闸（仅规格表 require_bitmap=true 时启用，由 new_project.py 写入）：
     统计**被 project.json 真正引用**的「合适资产」数：矢量 SVG 与带透明通道的
     位图都算；白底未抠（无 alpha）的位图记为不合适、不计入；舞台背景以及
     尺寸恰为 480x360 整数倍的全屏铺底图与背景同理免抠。治的是「只数数量
     不看质感」——过去塞一堆白底 AI 图也能 5/5，但缩进 Scratch 后观感依旧糙。
  E. 动画完备性（game/showcase **硬拦**）：至少 1 个角色在播放帧动画（多造型 且 脚本切造型）。
     零在播动画 = 静止单造型，观感死板（铁律15/手感「会动」；ir-patterns.md P9）。
  F. 音效密度（软提示）：总音效 / 角色数 比；比过低说明反馈稀疏、手感偏干（铁律18 四层）。
     不硬拦——已验收旗舰 platformer 本就零音效，硬拦会误杀基线。

用法（skill 根目录）：
    # 设计阶段：先生成一份规格表（genre 默认 game；音乐/动画改成 "music" / "animation"）
    python scripts/quality_gate.py --init --profile game --out examples/mywork.quality.json

    # 交付阶段：按规格表验收（game 品类会强制玩法完整度）
    python scripts/quality_gate.py --sb3 examples/output/mywork.sb3 \
        --spec examples/mywork.quality.json --strict

    # 不给 spec 时用内置档位
    python scripts/quality_gate.py --sb3 x.sb3 --profile mini
    python scripts/quality_gate.py --list

退出码：默认总为 0（只出报告）；--strict 且有未达标项时返回 1，可用于阻止交付。
"""

import argparse
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_PATH = os.path.join(ROOT, "references", "quality-profiles.json")

# A. 资产密度（计数型，所有品类都查）
METRICS = [
    ("costumes", "造型数", "min_costumes",
     "asset_pack.py search \"\" --kind costume；或 gen_community_template.py --template numberblock_band"),
    ("sounds", "音效/音乐数", "min_sounds",
     "asset_pack.py search \"\" --kind sound；或 python scripts/gen_audio.py <mood>"),
    ("sprites", "角色数", "min_sprites",
     "用 gen_community_template.py 的骨架扩角色，或把静态元素拆成独立角色"),
    ("bytes", "产物体积", "min_bytes",
     "防构建空壳下限（非质量指标）：先查资产是否丢失、是否误用 build_all 整库内嵌；"
     "素材是否合适由 D 层 suitable_assets 判定，别靠堆体积凑数"),
    ("scenes", "场景/背景数", "min_scenes",
     "gen_community_template.py --template backdrop_room_fsm 做多房间背景"),
    ("blocks", "积木数", "min_blocks",
     "补玩法逻辑与演出脚本；注意这项通常不是瓶颈"),
]

# B. 玩法完整度（布尔型，仅 genre=game 强制；其余品类跳过）
# 每项：key, 显示名, 补齐建议
COMPLETENESS = [
    ("player_control", "玩家可操控",
     "至少有一个角色用「当按下[方向键/空格]」「当角色被点击」等输入帽，且帽下挂运动/交互逻辑；"
     "不要只有绿旗+广播、玩家插不上手"),
    ("win_lose", "胜负/目标条件",
     "要有明确结局：广播名含 胜利/失败/通关/过关、变量含 生命/血量/得分/分数/关卡、或用「停止全部」收尾；"
     "让玩家知道赢没赢"),
    ("replay_value", "重玩价值",
     "至少满足 2 条：有「随机数」让每局不同、有 分数/得分 系统、有 关卡/难度 递进；"
     "否则通关即弃、无复玩动力"),
]

# 胜负信号关键词（广播名 / 变量名）
_WIN_BROADCAST = ["胜利", "失败", "通关", "过关", "赢", "输", "gameover", "win", "lose", "clear"]
_WIN_VAR = ["生命", "血量", "得分", "分数", "lives", "hp", "score", "health", "level"]
# 交互逻辑代理积木（输入帽下常见的「动了点什么」）
_INTERACTIVE_OPS = (
    "motion_", "sensing_mousedown", "sensing_touchingobject",
    "data_setvariableto", "data_changevariableby", "control_stop",
)

# §198 调色板（18 色，参考用）。冷灰（B 明显大于 R 且 R≈G）一律禁止；
# 深绿 #216E09 / 深蓝绿 #2F7365 明确「仅限文字，不得做填充」。
PALETTE_18 = {
    "#ffcf4d", "#ffedb3", "#faf19b", "#4f4a47", "#876c26",
    "#32af00", "#5fd100", "#8ce243", "#c6ff2a", "#216e09",
    "#3a8e7d", "#5cd9ba", "#c4ffe3", "#67f6d5", "#2f7365",
    "#767171", "#675d5d", "#7f7f7f",
}
FORBIDDEN_FILL_GREENS = {"#216e09", "#2f7365"}


def analyze_appearance(sb3):
    """扫描 SVG 与 project.json，启发式评估「观感质量」。

    对应铁律 8/9/11 里**可静态检**的部分：
      · 渐变体积感（铁律 11：UI 应有 linearGradient/radialGradient）
      · 窗口圆角（铁律 8/§200：窗口用圆角 rect 而非普通矩形）
      · 缓动/过渡（铁律 9：glide / GHOST 渐显 / 阻尼 multiply / 缓动关键词）
      · 配色合规（铁律 8/§198：冷灰禁止、深绿不得做填充）
    返回评分 0–100 与明细；冷灰/深绿为明确违规（低误杀）。
    """
    with zipfile.ZipFile(sb3) as z:
        names = z.namelist()
        try:
            d = json.loads(z.read("project.json"))
        except Exception:
            d = {"targets": []}
        # 只检查被角色/背景实际引用的 SVG（孤立文件是构建残留 / 共享 UI-Kit 资源，
        # 并不作为作品本身的画面呈现，误计入会假阳性判配色违规）
        ref_md5 = set()
        for t in d.get("targets", []):
            for c in t.get("costumes", []) + t.get("backdrops", []):
                a = c.get("assetId") or c.get("md5ext", "")
                ref_md5.add(str(a).split(".")[0].lower())
        svgs = [n for n in names if n.lower().endswith(".svg")
                and n[:-4].lower().split("/")[-1] in ref_md5]
        gradient_svgs = 0
        rect_total = 0
        rect_rounded = 0
        hex_colors = set()
        green_fill = 0  # 深绿/深蓝绿被用作填充（§198：仅限文字，不得做填充）
        for n in svgs:
            try:
                txt = z.read(n).decode("utf-8", "ignore")
            except Exception:
                continue
            if "linearGradient" in txt or "radialGradient" in txt:
                gradient_svgs += 1
            for m in re.finditer(r"<rect\b[^>]*>", txt):
                tag = m.group(0)
                rect_total += 1
                if re.search(r"\brx\s*=", tag):
                    rect_rounded += 1
            for h in re.findall(r"#[0-9a-fA-F]{6}\b", txt):
                hex_colors.add(h.lower())
            # 绿仅作「填充」才算 §198 违规；渐变 stop-color / 描边 / 文字都合法
            for fg in FORBIDDEN_FILL_GREENS:
                green_fill += len(re.findall(r'fill=["\']' + re.escape(fg) + r'["\']', txt, re.I))
    targets = d.get("targets", [])

    opcodes = set()
    var_names = set()
    ghost_fades = 0
    multiply_cnt = 0
    for t in targets:
        for v in t.get("variables", {}).values():
            if isinstance(v, list) and v:
                var_names.add(str(v[0]))
        for b in t.get("blocks", {}).values():
            if not isinstance(b, dict):
                continue
            op = b.get("opcode", "")
            if op:
                opcodes.add(op)
            if op == "looks_changeeffect":
                inp = b.get("inputs", {})
                val = inp.get("EFFECT", [None, None])
                if isinstance(val, list) and isinstance(val[1], str) and val[1].upper() == "GHOST":
                    ghost_fades += 1
            if op == "operator_multiply":
                multiply_cnt += 1
    glide = any("glide" in op for op in opcodes)
    keyword = any(re.search(r"缓动|lerp|ease|阻尼|平滑|目标|speed|速度", v) for v in var_names)
    ease_signals = int(glide) + int(ghost_fades > 0) + int(multiply_cnt >= 2) + int(keyword)

    cold_gray = 0
    deep_green = green_fill
    for h in hex_colors:
        try:
            r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        except ValueError:
            continue
        # 真灰：三通道接近（低饱和），且蓝通道偏高（冷调）。纯蓝/饱和色不算灰。
        lo, hi = min(r, g, b), max(r, g, b)
        if (hi - lo) <= 20 and b > r + 12 and b >= g:
            cold_gray += 1

    # 调色板合规率：只统计「有彩度的真实颜色」（排除纯白/纯黑/近白/近黑这些中性色，
    # 它们用于高光/阴影/描边，本就允许），看这些颜色有多少落在 §198 的 18 色板
    # 或与之极近（每通道 ≤24）。合规率低说明用了大量非标颜色，观感会脱离统一画风。
    real_colors = []
    for h in hex_colors:
        try:
            r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        except ValueError:
            continue
        mx, mn = max(r, g, b), min(r, g, b)
        if mx >= 245 or mn <= 16:        # 近白/近黑中性色，豁免
            continue
        real_colors.append((h, r, g, b))
    pal_rgb = []
    for p in PALETTE_18:
        try:
            pal_rgb.append((int(p[1:3], 16), int(p[3:5], 16), int(p[5:7], 16)))
        except ValueError:
            continue
    near = 0
    for h, r, g, b in real_colors:
        if h in PALETTE_18:
            near += 1
            continue
        for pr, pg, pb in pal_rgb:
            if abs(r - pr) <= 24 and abs(g - pg) <= 24 and abs(b - pb) <= 24:
                near += 1
                break
    palette_compliance = round(100.0 * near / len(real_colors)) if real_colors else 100

    svg_total = len(svgs)
    sub_gradient = 100 if gradient_svgs > 0 else (70 if svg_total < 5 else 40)
    # 无 rect（用 path 画圆角）的作品不罚；有 rect 则看圆角比例
    sub_round = (rect_rounded / rect_total * 100) if rect_total > 0 else 100
    sub_ease = 100 if ease_signals >= 2 else (50 if ease_signals == 1 else 0)
    sub_color = 0 if (cold_gray + deep_green) > 0 else 100
    score = round(0.35 * sub_gradient + 0.15 * sub_round + 0.35 * sub_ease + 0.15 * sub_color)

    return {
        "svg_total": svg_total,
        "gradient_svgs": gradient_svgs,
        "rect_total": rect_total,
        "rect_rounded": rect_rounded,
        "ease_signals": ease_signals,
        "cold_gray": cold_gray,
        "deep_green": deep_green,
        "palette_compliance": palette_compliance,
        "score": score,
        "_detail": {
            "glide": glide, "ghost_fades": ghost_fades,
            "multiply_cnt": multiply_cnt, "keyword": keyword,
            "sub_gradient": sub_gradient, "sub_round": round(sub_round),
            "sub_ease": sub_ease, "sub_color": sub_color,
        },
    }


def analyze_bitmap_usage(sb3):
    """D 层素材硬闸：统计**被 project.json 真正引用**的「合适资产」数量。

    为什么要单独做这一层：早期门禁只数「造型数/音效数/角色数」，导致作品可以
    全用程序化纯色 SVG 堆够数量、观感分照样 90+ 放行 —— 这正是「画面糙」的根因。
    另外构建会把共享 UI-Kit 资源作为**孤儿素材**打进每个 .sb3，所以绝不能只数
    zip 里的 .png（那样 50/56 作品都"含位图"，全是假象），必须走引用交集。

    【2026-11-08 修订：认「合适资产」而非「只数位图」】
    用户反馈「AI 生成的位图很多不适合做 Scratch 素材」——典型是白底未抠（无透明
    通道）的位图，缩进 480x360 后糊成一团、还带白方块。这类位图不该算数。
    新口径：
      · 矢量 SVG 造型：Scratch 原生、铁律17 合规（UI 矢量+五层体积），一律算合适；
      · 位图：带透明通道（已抠图 / 本身是透明）才算合适；白底未抠（无 alpha）
        记为 unsuitable，不计入达标数，并在报告里点名，便于人工复核；
      · 舞台背景、以及「尺寸恰为舞台 480x360 整数倍」的全屏铺底素材
        （960x720 大地图 / 480x360 遮罩）：与背景同理，本来就该不透明，一律算合适。
        该几何判据不会误伤 1024x1024 / 480x480 这类角色精灵（不满足整除）。
    这样评分/门禁才与「画面是否真合适」一致，而不是「塞了多少张图」。
    """
    import io
    import zipfile
    try:
        from PIL import Image
        _HAVE_PIL = True
    except Exception:
        _HAVE_PIL = False
    BITMAP_EXT = ("png", "jpg", "jpeg", "webp", "bmp")
    with zipfile.ZipFile(sb3) as z:
        names = z.namelist()
        d = json.loads(z.read("project.json"))
        # zip 内实际资产名（去掉扩展名）-> 完整名（用于读像素判 alpha）
        full_of = {}
        for n in names:
            base = n.split("/")[-1].lower()
            if "." in base:
                stem, _ = base.rsplit(".", 1)
                full_of[stem] = n
        referenced = []  # (ext, full_name_or_None)
        for t in d.get("targets", []):
            is_stage = bool(t.get("isStage"))
            items = t.get("backdrops", []) if is_stage else t.get("costumes", [])
            for c in items:
                # 优先 md5ext（带扩展名），assetId 常常是纯 md5
                md5 = str(c.get("md5ext") or c.get("assetId") or "")
                stem = md5.rsplit(".", 1)[0].lower() if "." in md5 else md5.lower()
                ext = None
                if stem in full_of and "." in full_of[stem]:
                    ext = full_of[stem].rsplit(".", 1)[-1].lower()
                elif "." in md5:
                    ext = md5.rsplit(".", 1)[-1].lower()
                referenced.append((ext or "?", full_of.get(stem), is_stage))
        vector_count = sum(1 for e, _, _ in referenced if e == "svg")
        suitable_bitmap = 0
        unsuitable_bitmap = 0
        STAGE_W, STAGE_H = 480, 360
        for e, full, is_stage in referenced:
            if e not in BITMAP_EXT:
                continue
            if is_stage:
                # 舞台背景本来就该不透明，一律算合适
                suitable_bitmap += 1
                continue
            if not _HAVE_PIL or full is None:
                # 无法判 alpha：保守算作合适（不误杀），但标记未知
                suitable_bitmap += 1
                continue
            try:
                img = Image.open(io.BytesIO(z.read(full)))
                # 全屏铺底素材（尺寸恰为舞台整数倍，如 960x720 大地图 / 480x360
                # 遮罩）与舞台背景同理，本就该不透明，不要求透明通道。
                w, h = img.size
                if w % STAGE_W == 0 and h % STAGE_H == 0:
                    suitable_bitmap += 1
                    continue
                has_alpha = False
                if img.mode in ("RGBA", "LA", "RGBa"):
                    # 末带是 alpha；最小值 < 250 说明存在透明/半透像素
                    extrema = img.getextrema()
                    ab = extrema[-1]
                    if isinstance(ab, tuple) and ab[0] < 250:
                        has_alpha = True
                elif img.mode == "P" and "transparency" in img.info:
                    has_alpha = True
            except Exception:
                suitable_bitmap += 1
                continue
            if has_alpha:
                suitable_bitmap += 1
            else:
                unsuitable_bitmap += 1
        bitmap_count = suitable_bitmap + unsuitable_bitmap
        suitable_assets = vector_count + suitable_bitmap
        return {
            "referenced_total": len(referenced),
            "bitmap_count": bitmap_count,          # 兼容旧字段（原始位图总数）
            "suitable_bitmap": suitable_bitmap,
            "unsuitable_bitmap": unsuitable_bitmap,
            "vector_count": vector_count,
            "suitable_assets": suitable_assets,   # 新：达标口径（矢量 + 透明位图）
        }


def analyze_animation(sb3):
    """E 层·动画完备性：游戏/展示类作品应当「看起来是活的」。

    判断依据（纯静态，无头可检）：
      · 多造型角色数（≥2 个 costume 的角色）——只有 1 个造型的角色是「死的」；
      · 真正在播放动画的角色数（多造型 且 脚本里用了 切换造型/下一个造型 积木）。
    经验：griffpatch 等顶级作品的「活」来自帧动画（见 ir-patterns.md P9）。
    本层不查「动作是否自然」，只查「有没有在动」这一最低门槛。
    """
    with zipfile.ZipFile(sb3) as z:
        d = json.loads(z.read("project.json"))
    targets = [t for t in d.get("targets", []) if not t.get("isStage")]
    multicostume = 0
    animated = 0
    for t in targets:
        cs = t.get("costumes", [])
        if len(cs) >= 2:
            multicostume += 1
            ops = set()
            for b in t.get("blocks", {}).values():
                if isinstance(b, dict) and b.get("opcode"):
                    ops.add(b["opcode"])
            if "looks_switchcostumeto" in ops or "looks_nextcostume" in ops \
               or "looks_switchcostumeto_backdrop" in ops:
                animated += 1
    total = len(targets)
    return {
        "total_sprites": total,
        "multicostume_sprites": multicostume,
        "animated_sprites": animated,
        "avg_costumes": round(sum(len(t.get("costumes", [])) for t in targets) / total, 2) if total else 0,
    }


def analyze_sfx_density(sb3):
    """F 层·音效密度：声音资产是否「铺得够开」。

    判断：总音效数 / 角色数；以及「完全无声的角色」数量（零音效的角色）。
    纯 UI 文字角色无声是合理的，所以本层只做**密度提示**，不硬性要求每个角色都有声；
    但游戏类若音效/角色比过低（< 0.5），说明反馈稀疏、手感偏干，应补 UI/FX 反馈音。
    """
    with zipfile.ZipFile(sb3) as z:
        d = json.loads(z.read("project.json"))
    all_targets = d.get("targets", [])
    targets = [t for t in all_targets if not t.get("isStage")]
    # 分子统计**全部**音效（含舞台）：BGM 与全局事件音（胜/负/升级）常挂在舞台角色上，
    # 不应因此被算作「无音效」。原实现只数非舞台角色的音效，导致所有规范作品误判 1/5。
    total_sounds = sum(len(t.get("sounds", [])) for t in all_targets)
    # silent_sprites 仍只数非舞台角色——用于提示「哪些交互角色缺少自带反馈音」。
    silent = sum(1 for t in targets if len(t.get("sounds", [])) == 0)
    total = len(targets)
    ratio = round(total_sounds / total, 2) if total else 0
    return {
        "total_sounds": total_sounds,
        "silent_sprites": silent,
        "total_sprites": total,
        "sound_per_sprite": ratio,
    }


def load_profiles():
    with open(PROFILES_PATH, encoding="utf-8") as f:
        return json.load(f)["profiles"]


def _broadcast_name(block, stage_broadcasts):
    inp = block.get("inputs", {}).get("BROADCAST_INPUT")
    if not inp or len(inp) < 2:
        return None
    val = inp[1]
    if isinstance(val, list):          # [name, variableId]
        return val[0]
    if isinstance(val, str):           # 直接引用 stage.broadcasts 的 id
        return stage_broadcasts.get(val) or val
    return None


def analyze_completeness(sb3):
    """扫描 project.json，启发式判定三项玩法完整度。"""
    with zipfile.ZipFile(sb3) as z:
        d = json.loads(z.read("project.json"))
    targets = d.get("targets", [])
    stage = [t for t in targets if t.get("isStage")]
    stage_broadcasts = stage[0].get("broadcasts", {}) if stage else {}

    opcodes = set()
    broadcast_names = set(str(x) for x in stage_broadcasts.values())
    var_names = set()
    input_hats = 0
    has_stop_all = False
    has_random = False
    has_motion = False
    has_poll_input = False

    for t in targets:
        for v in t.get("variables", {}).values():
            if isinstance(v, list) and v:
                var_names.add(str(v[0]))
        for b in t.get("blocks", {}).values():
            if not isinstance(b, dict):
                continue
            op = b.get("opcode", "")
            if not op:
                continue
            opcodes.add(op)
            if op in ("event_whenkeypressed", "event_whenthisspriteclicked",
                      "event_whenstageclicked"):
                input_hats += 1
            if op in ("sensing_keyoptions", "sensing_keypressed", "sensing_mousedown"):
                has_poll_input = True
            if op == "control_stop":
                has_stop_all = True
            if op in ("operator_random", "sensing_random", "math_random",
                      "operator_random_int"):
                has_random = True
            if op.startswith("motion_"):
                has_motion = True
            bn = _broadcast_name(b, stage_broadcasts)
            if bn:
                broadcast_names.add(str(bn))

    # 1b) 自研随机（Park-Miller LCG 等）：不依赖 operator_random 积木，
    #     而是「种子变量 + mod/乘 运算」组合出伪随机序列。
    #     2026-11-19 修正：strategy_replicas 用自研 RNG（种子=mod(种子*16807, 2^31-1)）
    #     实现四模式可复现抽卡，原判据完全漏检 -> 误判「无重玩价值」。
    #     判据：存在名为「种子/随机种子/random_seed/seed」的变量，
    #     且存在 operator_mod 积木（LCG 的必要组成部分）。
    seed_vars = {vn for vn in var_names
                 if any(k in vn.lower() for k in ("种子", "seed", "随机"))}
    has_own_rng = bool(seed_vars) and "operator_mod" in opcodes
    if has_own_rng:
        has_random = True

    # 1) 玩家可操控：有输入（帽子式 或 轮询式「键/鼠标被按下?」）+ 有交互/运动逻辑
    has_input = input_hats > 0 or has_poll_input
    player_control = has_input and (
        has_motion or has_stop_all or has_random
        or any(op.startswith("sensing_") or op.startswith("data_") for op in opcodes)
    )

    # 2) 胜负/目标条件：强信号广播/变量 + 收尾
    win_b = any(k.lower() in str(bn).lower() for bn in broadcast_names for k in _WIN_BROADCAST)
    win_v = any(any(k.lower() in str(vn).lower() for k in _WIN_VAR) for vn in var_names)
    win_lose = win_b or win_v or has_stop_all

    # 3) 重玩价值：随机数 / 计分 / 关卡递进 至少 2 条
    #    2026-11-19 修正：关卡关键词补「波次 / 回合 / 局 / 难度」——
    #    MOBA 走「波次」（兵线波次递增），策略游戏走「回合」（金铲铲回合经济），
    #    这两者与「关卡」同属「难度/进度递进」语义，原关键词表漏检。
    rep = 0
    if has_random:
        rep += 1
    if any(any(k.lower() in vn.lower() for k in ("分数", "得分", "score")) for vn in var_names):
        rep += 1
    if any(any(k.lower() in vn.lower()
               for k in ("关卡", "难度", "level", "stage", "波次", "回合", "局数"))
               for vn in var_names):
        rep += 1
    replay_value = rep >= 2

    return {
        "player_control": player_control,
        "win_lose": win_lose,
        "replay_value": replay_value,
        "_detail": {
            "input_hats": input_hats, "has_motion": has_motion,
            "has_random": has_random, "has_stop_all": has_stop_all,
            "broadcasts": sorted(broadcast_names)[:12],
            "vars": sorted(var_names)[:12],
        },
    }


def measure(sb3):
    with zipfile.ZipFile(sb3) as z:
        d = json.loads(z.read("project.json"))
    targets = d.get("targets", [])
    stage = [t for t in targets if t.get("isStage")]
    sprites = [t for t in targets if not t.get("isStage")]
    stagecost = stage[0].get("costumes", []) if stage else []
    return {
        "costumes": sum(len(t.get("costumes", [])) for t in targets),
        "sounds": sum(len(t.get("sounds", [])) for t in targets),
        "sprites": len(sprites),
        "bytes": os.path.getsize(sb3),
        "scenes": len(stagecost),
        "blocks": sum(len(t.get("blocks", {})) for t in targets),
    }


def fmt(v, key):
    if key == "bytes":
        return "{:.2f} MB".format(v / 1024 / 1024) if v >= 1024 * 1024 else "{} KB".format(round(v / 1024))
    return str(v)


def load_spec(path, profiles, default_profile):
    if path:
        with open(path, encoding="utf-8") as f:
            s = json.load(f)
        base = dict(profiles.get(s.get("profile", default_profile), profiles[default_profile]))
        for k, v in s.items():
            # min_* 是门槛覆盖；require_bitmap 是 D 层硬闸开关（new_project.py 写入）。
            # 早期这里只收 min_*，导致自定义布尔开关被静默丢弃 —— 硬闸形同虚设。
            if k.startswith("min_") or k == "require_bitmap":
                base[k] = v
        base["label"] = s.get("label", base.get("label", ""))
        base["genre"] = s.get("genre", base.get("genre", "game"))
        return base
    p = dict(profiles[default_profile])
    p["genre"] = p.get("genre", "game")
    return p


def cmd_init(args, profiles):
    p = dict(profiles[args.profile])
    p["profile"] = args.profile
    p["genre"] = "game"
    p["_hint"] = ("genre=game 时强制查「玩家可操控/胜负条件/重玩价值」；"
                  "音乐/动画/剧情类请改 genre 为 music/animation/story，三项自动跳过。"
                  "可手改任意 min_* 与 genre，交付时 --spec 指向本文件。")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)
    print("[完成] 规格表 -> {}".format(args.out))
    print("       档位 {}：{}".format(args.profile, p["label"]))
    print("       品类 {}（game 会强制玩法完整度）".format(p["genre"]))
    print("       可手改任意 min_* / genre 字段，交付时：")
    print("       python scripts/quality_gate.py --sb3 <产物>.sb3 --spec {} --strict".format(args.out))


def main():
    ap = argparse.ArgumentParser(description="作品质量门禁（资产密度 + 玩法完整度验收）")
    ap.add_argument("--sb3", help="待验收的 .sb3")
    ap.add_argument("--profile", default="game", help="内置档位 demo/mini/game/showcase")
    ap.add_argument("--spec", help="规格表 JSON（优先于 --profile）")
    ap.add_argument("--init", action="store_true", help="生成规格表模板")
    ap.add_argument("--out", help="--init 的输出路径 / --json 的报告路径由 --json 单独指定")
    ap.add_argument("--strict", action="store_true", help="有未达标项时返回非零退出码")
    ap.add_argument("--json", dest="json_out", help="把报告写成 JSON")
    ap.add_argument("--list", action="store_true", help="列出内置档位")
    args = ap.parse_args()

    profiles = load_profiles()
    if args.list:
        for k, v in profiles.items():
            print("{:10s} {}".format(k, v["label"]))
            print("           造型≥{} 音效≥{} 角色≥{} 体积≥{} 场景≥{} 积木≥{}".format(
                v["min_costumes"], v["min_sounds"], v["min_sprites"],
                fmt(v["min_bytes"], "bytes"), v["min_scenes"], v["min_blocks"]))
        return
    if args.init:
        if not args.out:
            ap.error("--init 需要 --out")
        cmd_init(args, profiles)
        return
    if not args.sb3:
        ap.error("需要 --sb3（或 --init / --list）")
    if not os.path.exists(args.sb3):
        print("找不到产物：{}".format(args.sb3), file=sys.stderr)
        sys.exit(2)

    spec = load_spec(args.spec, profiles, args.profile)
    genre = spec.get("genre", "game")
    actual = measure(args.sb3)
    results = []
    for key, label, skey, advice in METRICS:
        limit = spec[skey]
        val = actual[key]
        results.append({
            "metric": key, "label": label, "actual": val,
            "limit": limit, "pass": val >= limit, "advice": advice,
            "kind": "count",
        })

    # B. 玩法完整度（仅 game 品类强制）
    comp = analyze_completeness(args.sb3)
    if genre == "game":
        for key, label, advice in COMPLETENESS:
            val = comp[key]
            results.append({
                "metric": key, "label": label, "actual": "有" if val else "无",
                "limit": "必有", "pass": val, "advice": advice, "kind": "bool",
            })
    else:
        print("[提示] 品类 {}：玩法完整度（玩家可操控/胜负/重玩）不适用，已跳过。".format(genre))

    # C. 观感质量（所有品类都分析，软评分 + 明确违规 WARN）
    appr = analyze_appearance(args.sb3)
    print("\n--- C. 观感质量（铁律 8/9/11 可静态检部分）---")
    print("  渐变体积感 : {} 个 SVG 含渐变 / 共 {} 个".format(appr["gradient_svgs"], appr["svg_total"]))
    print("  窗口圆角   : {} 个圆角 rect / 共 {} 个 rect".format(appr["rect_rounded"], appr["rect_total"]))
    print("  缓动/过渡  : {} 个信号 (glide/ghost/阻尼/关键词)".format(appr["ease_signals"]))
    print("  配色合规   : 冷灰 {} 处 / 深绿填充 {} 处 / 调色板合规率 {}%".format(
        appr["cold_gray"], appr["deep_green"], appr["palette_compliance"]))
    print("  观感质量分 : {} / 100".format(appr["score"]))
    if appr["cold_gray"] or appr["deep_green"]:
        print("  [违规] 出现冷灰或深绿填充（§198 禁止），必须改回 §198 调色板")
    if appr["palette_compliance"] < 70:
        print("  [建议] 调色板合规率 < 70%，大量非标颜色会破坏统一画风（铁律13/§198）")
    if appr["score"] < 60:
        print("  [建议] 观感质量分 < 60，回看 references/quality-checklist.md 模块三/四")

    # E. 动画完备性（game/showcase 强制：至少 1 个角色在播放帧动画）
    anim = analyze_animation(args.sb3)
    print("\n--- E. 动画完备性（铁律观感/手感：作品要「会动」）---")
    print("  角色总数   : {}".format(anim["total_sprites"]))
    print("  多造型角色 : {} 个（≥2 造型）".format(anim["multicostume_sprites"]))
    print("  在播动画   : {} 个（多造型且脚本里切造型）".format(anim["animated_sprites"]))
    print("  平均造型数 : {} / 角色".format(anim["avg_costumes"]))
    if genre in ("game", "showcase") and anim["animated_sprites"] == 0:
        print("  [违规] 游戏/展示类零在播动画——全是静止单造型，观感死板（见 ir-patterns.md P9 帧动画）")

    # F. 音效密度（软提示：声音铺得够不够开）
    sfx = analyze_sfx_density(args.sb3)
    print("\n--- F. 音效密度（手感反馈是否铺开）---")
    print("  总音效     : {}".format(sfx["total_sounds"]))
    print("  无声角色   : {} 个（零音效）".format(sfx["silent_sprites"]))
    print("  音效/角色  : {} : 1".format(sfx["sound_per_sprite"]))
    if genre in ("game", "showcase") and sfx["sound_per_sprite"] < 0.5:
        print("  [建议] 音效/角色比 < 0.5，反馈稀疏、手感偏干，补 UI/FX 反馈音（铁律18 四层）")

    # D. 生图素材硬闸（仅规格表显式 require_bitmap=true 时启用）
    # 由 new_project.py 生成的规格表带上此字段；既有纯 SVG 技术探针不受影响。
    if spec.get("require_bitmap"):
        bm = analyze_bitmap_usage(args.sb3)
        need = int(spec.get("min_bitmap_assets", 3))
        print("\n--- D. 生图素材硬闸（require_bitmap）---")
        print("  被引用合适资产: {} 个（矢量 {} / 透明位图 {}）".format(
            bm["suitable_assets"], bm["vector_count"], bm["suitable_bitmap"]))
        print("  不合适位图    : {} 个（白底未抠/无透明通道，不计入达标）".format(
            bm["unsuitable_bitmap"]))
        print("  门槛           : 合适资产 >= {} 个".format(need))
        print("  [说明] 矢量 SVG 与带透明通道的位图都算合适；白底位图不算。zip 孤儿素材不计。")
        results.append({
            "metric": "bitmap_assets", "label": "生图素材", "actual": bm["suitable_assets"],
            "limit": need, "pass": bm["suitable_assets"] >= need,
            "advice": "素材优先用矢量 SVG（enhance_svg 加五层体积，铁律17 合规）；位图须带透明通道（prep_asset.py --remove-bg 抠图），白底未抠不达标。",
            "kind": "count",
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    grade = "优秀" if passed == total else ("作品级" if passed >= total - 2 else "DEMO 级")

    print("=" * 68)
    print("作品质量门禁 · {}".format(os.path.basename(args.sb3)))
    print("档位 {} / {} · 品类 {}".format(args.spec or args.profile, spec.get("label", ""), genre))
    print("=" * 68)
    print("{:<14}{:>12}{:>12}  {}".format("指标", "实测", "门槛", "结果"))
    print("-" * 68)
    for r in results:
        print("{:<14}{:>12}{:>12}  {}".format(
            r["label"], r["actual"] if r["kind"] == "bool" else fmt(r["actual"], r["metric"]),
            r["limit"], "OK" if r["pass"] else "不足"))
    print("-" * 68)
    print("达标 {}/{} · 评级：{}".format(passed, total, grade))

    failed = [r for r in results if not r["pass"]]
    # C 层「明确违规」（冷灰 / 深绿填充）才阻断交付；观感分仅作建议，避免误杀旗舰。
    # game / showcase 品类在 --strict 下拦截真违规（§198 配色铁律）。
    if genre in ("game", "showcase") and (appr["cold_gray"] or appr["deep_green"]):
        failed.append({
            "metric": "appearance", "label": "观感质量(配色)",
            "actual": "冷灰{}处/深绿填充{}处".format(appr["cold_gray"], appr["deep_green"]),
            "limit": "达标", "pass": False,
            "advice": "回看 references/quality-checklist.md 模块三/四（§198 配色）", "kind": "bool",
        })
    # E 层：游戏/展示类零在播动画 -> 硬拦（静止单造型观感死板，铁律15/手感要求「会动」）
    if genre in ("game", "showcase") and anim["animated_sprites"] == 0:
        failed.append({
            "metric": "animation", "label": "动画完备性",
            "actual": "在播动画 0 个", "limit": "≥1", "pass": False,
            "advice": "给主角/敌人加帧动画（ir-patterns.md P9）：声明 animations: 驱动变量+状态->造型序列",
            "kind": "bool",
        })
    # C 层·调色板合规率：软提示（不硬拦）。已验收旗舰 fruit_basket/star_catch 也仅 13~23%，
    # 因为真实美术会用到 18 色板外的过渡色；硬拦会误杀已验收作品。硬 §198 违规仍走
    # 冷灰/深绿填充那条。合规率只作「收敛趋势」提示。
    if failed:
        print("\n补齐建议（按差距排序）：")
        # 计数项按差距比例，布尔项置顶
        def gap(r):
            if r["kind"] == "bool":
                return 0
            lim = max(r["limit"], 1)
            return 1 - min(r["actual"] / lim, 1)
        for r in sorted(failed, key=gap):
            print("  · {} {} < {}：{}".format(
                r["label"],
                r["actual"] if r["kind"] == "bool" else fmt(r["actual"], r["metric"]),
                r["limit"], r["advice"]))
    print("\n人工检查项（无头校验测不到，仍需目视）：")
    print("  · 首页/标题页是否齐全；结算页是否有返回/再来一局按钮（铁律 7）")
    print("  · 素材尺寸与旋转中心、中文排版、质感曲线、音效响度层级")

    report = {
        "sb3": args.sb3, "profile": args.spec or args.profile, "genre": genre,
        "grade": grade, "passed": passed, "total": total,
        "actual": actual, "limits": {k: spec[k] for _, _, k, _ in METRICS},
        "completeness": {k: comp[k] for k in ("player_control", "win_lose", "replay_value")},
        "animation": anim,
        "sfx_density": sfx,
        "appearance": {k: appr[k] for k in ("score", "cold_gray", "deep_green", "palette_compliance")},
        "results": results,
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("\n报告 -> {}".format(args.json_out))

    if failed and args.strict:
        print("\n[FAIL] --strict：{} 项未达标，交付被阻止".format(len(failed)))
        sys.exit(1)
    if failed:
        print("\n[WARN] {} 项未达标（未启用 --strict，仅警告）".format(len(failed)))
    else:
        print("\n[PASS] 全部达标")
    print("QUALITY_GATE_{}".format("OK" if not failed else "WARN"))


if __name__ == "__main__":
    main()
