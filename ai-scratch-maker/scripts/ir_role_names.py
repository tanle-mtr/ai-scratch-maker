#!/usr/bin/env python3
# 给定作品 stem，用规范 IR 解析器提取「IR 声明的 sprite 角色名」，每行一个打印到 stdout。
# 用途：供 generic_deep_check.mjs 做「IR 声明角色 ↔ 构建产物角色」一致性断言
#       （最易回归的构建 bug：构建把某个 sprite 弄丢了）。
#
# 设计要点：
#   · 路径从本脚本自身定位 skill 根（scripts/ 的父目录），不依赖调用方 cwd。
#   · 优先 yaml 源、其次 json 源；无源或解析失败 → 静默退出 0（打印空），
#     绝不因「提取不到」而让上层校验判定失败（提取是辅助层，缺失即跳过）。
#   · 只提取 sprites（角色），不含舞台 / 背景 / 自制积木 —— 这些是 IR 里独立的键，
#     用 ir_schema 规范解析可精确区分，避免正则误把「自制积木名 / 背景名」当 sprite。
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

STEM = sys.argv[1] if len(sys.argv) > 1 else ""


def main():
    if not STEM:
        return
    y = os.path.join(SKILL_ROOT, "examples", STEM + ".yaml")
    j = os.path.join(SKILL_ROOT, "examples", STEM + ".json")
    src = y if os.path.exists(y) else (j if os.path.exists(j) else None)
    if not src:
        return  # 无 IR 源：交验层直接跳过角色一致性
    try:
        import ir_schema as I
        ir, _ = I.load_ir_marked(src)
    except Exception:
        return  # 解析失败：跳过，不让提取问题影响结论
    proj = ir.get("project", ir) if isinstance(ir, dict) else {}
    sprites = proj.get("sprites") or []
    for s in sprites:
        if isinstance(s, dict) and s.get("name"):
            print(s["name"])


if __name__ == "__main__":
    main()
