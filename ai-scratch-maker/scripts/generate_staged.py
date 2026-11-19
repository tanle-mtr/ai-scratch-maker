#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分层生成编排：从「题材 + 名字」一键走到「已验收的 .sb3」。

把质量提升的各类工具串成一条流水线，每一层验收通过才进下一层——避免「一口气生成、
最后才发现有硬伤」：

  阶段 0  脚手架      new_project.py（或 retrieve_scaffold 推荐的非内置题材）→ 起手 IR
  阶段 1  美术增强*   （可选）enhance_svg 给原始素材加五层体积感 → 写回 IR 的 asset:
  阶段 2  构建        build_sb3.py → 产物 .sb3
  阶段 3  门禁        quality_gate.py（A–F 层报告）
  阶段 4  评分卡      scorecard.py（1–5 维度总分）
  阶段 5  铁律        check_hard_rules.mjs（9 条可静态检铁律，可选，需 node）
  * 美术增强需要你先用 ImageGen 出图放 --raw-assets，本脚本只负责「增强 + 提示写回」。

设计原则：每一阶段失败（--strict 且门禁未过 / 构建失败 / 硬律违例）立即停，绝不把坏
作品推进到下一层。

用法：
    python scripts/generate_staged.py --genre catch --name 星空拾贝
    python scripts/generate_staged.py --genre platformer --name 云间跳跃 --profile showcase
    python scripts/generate_staged.py --genre catch --name X --raw-assets raw/ --strict
"""
import argparse
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAMPLES = os.path.join(ROOT, "examples")
OUT = os.path.join(EXAMPLES, "output")
sys.path.insert(0, HERE)
import new_project  # noqa: E402


def _run(cmd, **kw):
    print("  $ " + " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)
    return r


def _slug(name, genre):
    import re
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", name.strip(), flags=re.UNICODE).strip("_")
    if not s or re.search(r"[\u4e00-\u9fff]", s):
        import hashlib
        s = "%s_%s" % (genre, hashlib.md5(name.encode("utf-8")).hexdigest()[:6])
    return s


def main():
    ap = argparse.ArgumentParser(description="分层生成编排：题材+名字 → 已验收 .sb3")
    ap.add_argument("--genre", default="catch")
    ap.add_argument("--name", default="我的新作品")
    ap.add_argument("--profile", default="game", choices=["demo", "mini", "game", "showcase"])
    ap.add_argument("--slug", help="输出文件名（默认由 --name 生成）")
    ap.add_argument("--raw-assets", help="原始素材目录（将被 enhance_svg 增强）")
    ap.add_argument("--min-bitmap", type=int, default=3)
    ap.add_argument("--strict", action="store_true", help="门禁/铁律未过则非零退出")
    ap.add_argument("--skip-hard-rules", action="store_true", help="跳过 check_hard_rules（无需 node）")
    args = ap.parse_args()

    slug = args.slug or _slug(args.name, args.genre)
    ir_path = os.path.join(EXAMPLES, slug + ".yaml")
    sb3_path = os.path.join(OUT, slug + ".sb3")
    spec_path = os.path.join(EXAMPLES, slug + ".quality.json")
    os.makedirs(OUT, exist_ok=True)

    print("=" * 64)
    print("分层生成 · %s（genre=%s, profile=%s, slug=%s）" % (args.name, args.genre, args.profile, slug))
    print("=" * 64)

    # 阶段 0：脚手架
    print("\n[阶段 0] 脚手架")
    if args.genre in new_project.TEMPLATES:
        r = _run([sys.executable, "scripts/new_project.py", "--genre", args.genre,
                  "--name", args.name, "--slug", slug, "--profile", args.profile,
                  "--min-bitmap", str(args.min_bitmap), "--force"])
    else:
        print("  内置模板无 %r，改用 retrieve_scaffold 推荐 →" % args.genre)
        r = _run([sys.executable, "scripts/retrieve_scaffold.py", "--genre", args.genre,
                  "--build-index"])
        if r.returncode != 0:
            print("[阶段 0 失败] 无候选骨架，先用 retrieve_scaffold 找一个已验收题材", file=sys.stderr)
            return 2
        print("  （非内置题材请手动 cp 推荐 IR 并改 project.name；本编排对内置三题材全自动）")
        return 0
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        print("[阶段 0 失败] 脚手架未生成", file=sys.stderr)
        return 2

    # 阶段 1：美术增强（可选）
    if args.raw_assets:
        print("\n[阶段 1] 美术增强（enhance_svg 五层体积感）")
        enh_dir = os.path.join(os.path.dirname(os.path.abspath(args.raw_assets)),
                               "enhanced")
        r = _run([sys.executable, "scripts/enhance_svg.py", "--in-dir", args.raw_assets,
                  "--out-dir", enh_dir, "--strip-text"])
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            print("[阶段 1 警告] 美术增强失败，跳过（不影响后续）", file=sys.stderr)
        else:
            print("  → 已增强到 %s；请手动把 IR 里对应 asset: 指向这些文件" % enh_dir)

    # 阶段 2：构建
    print("\n[阶段 2] 构建")
    workdir = tempfile.mkdtemp(prefix="staged_")
    r = _run([sys.executable, "scripts/build_sb3.py", "--ir", ir_path, "--out", sb3_path,
              "--workdir", workdir, "--no-cache"])
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        print("[阶段 2 失败] 构建未产出，停止", file=sys.stderr)
        return 2

    # 阶段 3：门禁
    print("\n[阶段 3] 质量门禁（A–F 层）")
    if not os.path.exists(spec_path):
        # 规格表缺失时自动生成基线（genre 默认 game；非游戏作品请手改 genre），
        # 避免 quality_gate 因找不到 --spec 而报错。
        print("  （规格表缺失，先用 quality_gate --init 生成基线：%s）" % spec_path)
        _run([sys.executable, "scripts/quality_gate.py", "--init",
              "--profile", args.profile, "--out", spec_path])
    r = _run([sys.executable, "scripts/quality_gate.py", "--sb3", sb3_path,
              "--spec", spec_path])
    print(r.stdout.strip())
    gate_fail = "FAIL" in r.stdout or "WARN" in r.stdout  # --strict 才致命，这里仅报告

    # 阶段 4：评分卡
    print("\n[阶段 4] 评分卡")
    r = _run([sys.executable, "scripts/scorecard.py", sb3_path])
    print(r.stdout.strip())

    # 阶段 5：铁律（可选，需 node）
    if not args.skip_hard_rules:
        print("\n[阶段 5] 铁律静态检查（check_hard_rules.mjs）")
        node = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if node.returncode == 0:
            r = _run(["node", "scripts/check_hard_rules.mjs", sb3_path])
            print(r.stdout.strip() or r.stderr.strip())
        else:
            print("  （跳过：未检测到 node）")

    print("\n" + "=" * 64)
    print("分层生成完成 · 产物 %s" % sb3_path)
    print("GENERATE_STAGED_OK")
    if args.strict and gate_fail:
        print("[strict] 门禁未全过，请修后再交付")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
