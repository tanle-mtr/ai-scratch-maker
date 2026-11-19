#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成前置脚手架 —— 从「已验收的完整作品」起手，而不是从零写 IR。

## 为什么有这个脚本

过去几十轮做的都是「事后检查」：八层校验、铁律、质量门禁、增量嗅觉……
检查发生在 AI 写完 IR 之后，只会回报「不达标」，不改变它的起点。
结果是 AI 仍然从一张白纸开始，天然倾向最省事的程序化素材 + 最小可跑逻辑，
于是产出永远是「能打开、能跑，但画面糙、玩法空、手感生硬」。

本脚本把高质量**前置到生成的第 0 步**：直接复制一份「八层 + 深网 + 门禁全过」
的完整作品作为起点（含首页 / 状态机 / 结算页返回按钮 / 复位广播 / 胜负判定 /
计分生命 / 音频四层；platformer 还含跳跃缓冲、可变跳、挤压拉伸、震屏），
AI 只需要改玩法差异和素材，不给它从零瞎写的机会。

采用**文本级复制**（不解析 YAML）是为了保留原 IR 的注释、格式与缩进——
这些 IR 都是编译通过的，复制件必定能编译通过。

## 用法（在 skill 根目录执行）

    python scripts/new_project.py --list
    python scripts/new_project.py --genre catch --name 星空拾贝
    python scripts/new_project.py --genre platformer --name 云间跳跃 --profile showcase

产出三份文件（都在 examples/ 下，与模板同目录以保证 asset 相对路径有效）：
    examples/<slug>.yaml           完整可编译 IR
    examples/<slug>.quality.json   规格表（带 require_bitmap 硬闸）
    examples/<slug>.assets.md      素材清单 + 生图提示词（必须逐项替换）

随后：
    python scripts/build_sb3.py --ir examples/<slug>.yaml --out examples/output/<slug>.sb3 --workdir <临时目录>
    python scripts/quality_gate.py --sb3 examples/output/<slug>.sb3 --spec examples/<slug>.quality.json --strict
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
PROFILES = ROOT / "references" / "quality-profiles.json"

# 模板全部来自「八层结构校验 + 深网行为断言 + 质量门禁」已通过的作品。
# 不要换成未经验证的 IR —— 脚手架的全部价值就在于「起点一定是好的」。
TEMPLATES = {
    "catch": {
        "ir": "fruit_basket.yaml",
        "label": "接物 / 收集类：计分 + 生命 + 关卡递进 + 首页 + 结算",
        "hero": "主角（接住下落物的角色）",
        "scene": "游戏主场景背景",
        "prop": "下落物 / 收集物",
    },
    "platformer": {
        "ir": "platformer.yaml",
        "label": "平台跳跃：物理积分 + 土狼时间 + 跳跃缓冲 + 可变跳 + 挤压拉伸 + 震屏 + 相机跟随",
        "hero": "玩家角色（可跳跃）",
        "scene": "横版关卡背景",
        "prop": "金币 / 收集物",
    },
    "whack": {
        "ir": "whack_a_mole.yaml",
        "label": "点击 / 打地鼠类：多点位随机出现 + 连击 + 限时 + 结算",
        "hero": "锤子 / 指针（点击工具）",
        "scene": "游戏主场景背景（含地洞排布）",
        "prop": "冒头的目标物",
    },
    "music": {
        "ir": "music_band.yaml",
        "label": "乐器编曲台：简谱转乐器演奏，点击指挥者随机换乐器并演奏，含得分 + 运势随机",
        "hero": "指挥者（可点击演奏、带指挥/演奏造型的角色）",
        "scene": "音乐舞台背景（暖色聚光）",
        "prop": "乐器 / 音符",
    },
    "story": {
        "ir": "story.yaml",
        "label": "分支叙事：点击选项推进剧情，多结局 + 得分 + 运势随机",
        "hero": "主角冒险者（带站立/行走造型）",
        "scene": "故事书森林岔路背景",
        "prop": "指引罗盘 / 选项按钮",
    },
}

# §198 18 色板合规提示；铁律17 禁 SVG <text>；铁律8 禁冷灰/深绿填充
_STYLE_RULES = """\
- **风格统一**：同一作品所有素材用同一种画风（儿童绘本厚涂 / 柔和水彩 / 扁平矢量三选一），
  暖色为主、柔和光照、圆润造型，避免写实照片与卡通混搭。
- **禁用配色**：冷灰（B 明显 > R 且 R≈G）、深绿 `#216E09` / 深蓝绿 `#2F7365` 做填充。
  取 §198 的 18 色 HEX 色板；颜色字面量一律 6 位 `#rrggbb`。
- **画面里不要任何文字**：Scratch 造型里写字会因字体缺失/缩放糊掉（铁律17）。
  标题、分数、按钮文案一律由独立角色或 UI 面板承担。
- **背景**：横版 4:3，主体留中央安全区，四周留出 UI 与角色活动空间，不要填满细节。
- **角色**：透明背景 PNG，角色高度约为舞台的 1/3，轮廓清晰、带描边，方便做挤压拉伸。
- **按钮/面板**：窗口圆角 + 五层体积感（投影→外描边→渐变→顶高光→底内阴），
  Scratch 无九宫格，面板请按目标尺寸直接出图。
- 生成后一律走 `scripts/prep_asset.py` 整理尺寸，再写回 IR 的 `asset:`。
"""


def _slug(name, genre):
    """中文名转成安全的文件名；纯中文时退回题材+短哈希，避免全空。"""
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", name.strip(), flags=re.UNICODE)
    s = s.strip("_")
    if not s:
        s = genre
    # 中文文件名在部分工具链上会踩编码坑，统一用 ASCII 前缀 + 题材
    if re.search(r"[\u4e00-\u9fff]", s):
        import hashlib
        h = hashlib.md5(name.encode("utf-8")).hexdigest()[:6]
        s = "%s_%s" % (genre, h)
    return s


def _collect_assets(text):
    """扫出 IR 里所有素材引用，按用途粗分类。"""
    pat = re.compile(r"(?:asset|backdrop|button_asset)\s*:\s*[\"']?([^\"'\s}\n,]+)")
    items = []
    for m in pat.finditer(text):
        v = m.group(1).strip().strip("\"'")
        if v and v not in [x[0] for x in items]:
            items.append((v, m.start()))
    bitmaps = [v for v, _ in items if v.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))]
    vectors = [v for v, _ in items if v.lower().endswith(".svg")]
    audio = [v for v, _ in items if v.lower().endswith((".wav", ".mp3", ".ogg"))]
    community = [v for v, _ in items if v.startswith("community:")]
    return {"all": [v for v, _ in items], "bitmap": bitmaps, "vector": vectors,
            "audio": audio, "community": community}


def _make_spec(genre, info, profile, slug, name, n_bitmap_required):
    base = {}
    if PROFILES.exists():
        try:
            base = json.loads(PROFILES.read_text(encoding="utf-8"))["profiles"].get(profile, {})
        except Exception:
            base = {}
    spec = {k: v for k, v in base.items() if not k.startswith("_") and k != "label"}

    # 继承模板自带的规格表覆盖值。否则脚手架一生成就在 A 层 FAIL，起点就不是「已验收」。
    # 注：min_bytes 现为统一防呆下限 150000（只拦构建空壳，不作质量指标）；
    # 旧值 1MB/8MB 是社区素材整库内嵌污染时代的虚高地板，已废止。
    tpl_spec = EXAMPLES / (Path(info["ir"]).stem + ".quality.json")
    if tpl_spec.exists():
        try:
            for k, v in json.loads(tpl_spec.read_text(encoding="utf-8")).items():
                if k.startswith("min_"):
                    spec[k] = v
        except Exception:
            pass

    spec.update({
        "label": "%s（由 new_project.py 生成，带合适素材硬闸）" % name,
        "profile": profile,
        "genre": "game",
        # ↓ D 层硬闸：quality_gate.py 只对这个字段为 true 的规格表启用
        "require_bitmap": True,
        "min_bitmap_assets": n_bitmap_required,
        "_scaffold": "new_project.py --genre %s" % genre,
        "_hint": "require_bitmap=true 时，统计被 project.json 真正引用的「合适资产」："
                 "矢量 SVG（铁律17，UI 一律矢量优先）+ 带透明通道的抠图位图；"
                 "白底未抠 / 整块不透明的位图不计入。全屏背景本就不透明，一律算合适。"
                 "不为指标好看去堆无引用的孤儿素材。",
    })
    return spec


def _make_asset_brief(name, genre, info, assets, spec, slug):
    lines = [
        "# %s · 素材清单与生图提示词" % name,
        "",
        "> 由 `new_project.py --genre %s --name %s` 生成。" % (genre, name),
        "> **这一步不是可选的**：模板 IR 里的素材是占位/示例，直接交付就是「画面糙」的旧样子。",
        "> 逐项用 ImageGen 生成后经 `prep_asset.py` 整理，再写回 IR 的 `asset:`。",
        "",
        "## 必须替换的位图（门禁 D 层会查）",
        "",
        "规格表要求至少 **%d 个被真正引用的位图造型**。" % spec["min_bitmap_assets"],
        "「被引用」指写进 costumes/backdrops 且被 project.json 记录，孤儿素材不算。",
        "",
        "| 用途 | 提示词要点 |",
        "|---|---|",
        "| %s | 主视觉，横版 4:3，暖色儿童绘本风，中央留活动区，无文字 |" % info["scene"],
        "| %s | 透明背景 PNG，圆润带描边，高度≤舞台 1/3，四方向可辨识，无文字 |" % info["hero"],
        "| %s | 透明背景 PNG，同上画风，轮廓与主角明显区分，无文字 |" % info["prop"],
        "| 首页背景 | 与 %s 同场景，中央大面积留白给标题，无文字 |" % info["scene"],
        "| 开始按钮 | 圆角窗口 + 五层体积感，单独 PNG，无文字（文案用角色） |" % (),
        "| 结算页 | 与首页同系列，留出「再来一局 / 返回」按钮位置，无文字 |" % (),
        "",
        "### 统一画风约束（每张图都要遵守）",
        "",
        _STYLE_RULES,
        "## 模板 IR 当前引用的素材",
        "",
        "- 位图 %d 个、矢量 %d 个、音频 %d 个、社区素材 %d 个。" % (
            len(assets["bitmap"]), len(assets["vector"]),
            len(assets["audio"]), len(assets["community"])),
        "",
        "```",
    ]
    for v in assets["all"]:
        lines.append("  " + v)
    lines += [
        "```",
        "",
        "## 音效（四层响度，铁律18）",
        "",
        "ui 点击 ≤0.25s / fx 反馈 -9dBFS / ev 胜负 -3dBFS / amb 背景 -15dBFS；",
        "首尾归零、DC<0.01、UI 音禁用「播放声音直到结束」。",
        "可直接复用 `scripts/gen_sfx_kit.py` 的 22 个预设，但**至少替换 1~2 个为主题专属音**。",
        "",
        "## 替换后的验收命令",
        "",
        "```bash",
        "python scripts/build_sb3.py --ir examples/%s.yaml --out examples/output/%s.sb3 --workdir <临时目录>" % (
            "%s", "%s"),
        "python scripts/quality_gate.py --sb3 examples/output/%s.sb3 --spec examples/%s.quality.json --strict" % (
            "%s", "%s"),
        "bash scripts/verify_project.sh --only-advisory   # 秒级看性能/可访问性建议",
        "```",
        "",
        "> 交付前还要逐条过 `references/self-review.md` 的 9 类软性自查，",
        "> 以及 `scripts/verify_project.sh` 全量回归。",
        "",
    ]
    # 把命令示例里的 %s 占位换成**真实文件名**，用户可直接复制执行，不用猜 <slug> 填什么。
    return ("\n".join(lines)
            .replace("examples/%s.yaml", "examples/%s.yaml" % slug)
            .replace("examples/output/%s.sb3", "examples/output/%s.sb3" % slug)
            .replace("examples/%s.quality.json", "examples/%s.quality.json" % slug))


def main():
    ap = argparse.ArgumentParser(description="从已验收作品生成新项目骨架")
    ap.add_argument("--genre", choices=sorted(TEMPLATES), default="catch")
    ap.add_argument("--name", default="我的新作品")
    ap.add_argument("--slug", help="输出文件名（不含扩展名），默认由 --name 自动生成")
    ap.add_argument("--profile", choices=["demo", "mini", "game", "showcase"], default="game")
    ap.add_argument("--min-bitmap", type=int, default=3,
                    help="门禁 D 层要求的最少被引用位图造型数（默认 3：背景+主角+道具）")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的同名文件")
    ap.add_argument("--list", action="store_true", help="列出可用骨架模板并退出")
    args = ap.parse_args()

    if args.list:
        print("可用骨架模板（全部已通过八层 + 深网 + 质量门禁）：")
        for k, v in TEMPLATES.items():
            p = EXAMPLES / v["ir"]
            print("  %-12s %-6s %s" % (k, "OK" if p.exists() else "缺失", v["label"]))
            print("  %-12s        源: examples/%s" % ("", v["ir"]))
        return 0

    info = TEMPLATES[args.genre]
    src = EXAMPLES / info["ir"]
    if not src.exists():
        print("[new_project] 模板不存在: %s" % src, file=sys.stderr)
        return 2

    slug = args.slug or _slug(args.name, args.genre)
    ir_out = EXAMPLES / (slug + ".yaml")
    spec_out = EXAMPLES / (slug + ".quality.json")
    brief_out = EXAMPLES / (slug + ".assets.md")
    if not args.force:
        for p in (ir_out, spec_out, brief_out):
            if p.exists():
                print("[new_project] 已存在: %s（加 --force 覆盖）" % p, file=sys.stderr)
                return 3

    text = src.read_text(encoding="utf-8")

    # 只改 project.name，绝不改变量名/广播名/积木名 —— 它们是深网断言的依据。
    new_text, n = re.subn(r"(?m)^(  name:\s*).+$", lambda m: m.group(1) + args.name, text, count=1)
    if n == 0:
        print("[new_project] 警告：未找到 project.name 行，IR 保持原名", file=sys.stderr)
        new_text = text

    # 顶部插入「由脚手架生成」的溯源注释（纯注释，不影响 YAML 结构）
    banner = (
        "# 由 scripts/new_project.py --genre %s 生成，骨架源: examples/%s\n"
        "# 该骨架已通过八层结构校验 / 深网行为断言 / 质量门禁；请只改玩法差异与素材。\n"
        "# 素材替换清单见 examples/%s.assets.md；规格表见 examples/%s.quality.json\n"
        "# 配色遵守 §198 18 色板，所有颜色字面量 6 位 HEX（铁律8/13）。\n"
    ) % (args.genre, info["ir"], slug, slug)
    new_text = banner + new_text

    assets = _collect_assets(new_text)
    spec = _make_spec(args.genre, info, args.profile, slug, args.name, args.min_bitmap)

    ir_out.write_text(new_text, encoding="utf-8")
    spec_out.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    brief_out.write_text(_make_asset_brief(args.name, args.genre, info, assets, spec, slug), encoding="utf-8")

    print("NEW_PROJECT_OK")
    print("  骨架源  : examples/%s  (%s)" % (info["ir"], info["label"]))
    print("  IR      : examples/%s.yaml  (%d 行，可直接编译)" % (slug, len(new_text.splitlines())))
    print("  规格表  : examples/%s.quality.json  (require_bitmap=true, min=%d)" % (slug, args.min_bitmap))
    print("  素材清单: examples/%s.assets.md" % slug)
    print("  现有引用: 位图 %d / 矢量 %d / 音频 %d / 社区 %d" % (
        len(assets["bitmap"]), len(assets["vector"]), len(assets["audio"]), len(assets["community"])))
    print("")
    print("下一步：按 assets.md 生图并替换 → build_sb3.py → quality_gate.py --strict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
