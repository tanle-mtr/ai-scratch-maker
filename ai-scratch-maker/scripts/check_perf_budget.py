#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""性能预算静态检查（Performance Budget Linter）。

不启动 VM、直接解析 project.json 的 blocks，给出「结构性性能风险」预警：
  · Long Script      ：单脚本积木数过大 → 拆广播子程序（LitterBox 臭味）
  · Busy Waiting     ：repeat/forever 内 wait 字面量 ≤ 0.03s → 空转抢占整角色
  · 克隆风暴         ：create_clone_of 总数逼近/超过 300 硬上限（铁律12）
  · 广播风暴         ：broadcast 总数过多（>60 警示耦合）
  · 单角色脚本过多   ：单角色 scripts 数过多（味道）

用法：
    python scripts/check_perf_budget.py examples/output/x.sb3
    python scripts/check_perf_budget.py examples/output/x.sb3 --strict   # 超出阈值返回 1
    python scripts/check_perf_budget.py examples/output/x.sb3 --json

默认只出报告、退出码 0；--strict 且有任意项超阈值时返回 1（可接 CI 拦交付）。
这是「软性」性能嗅觉，不与八层校验/铁律冲突；命中项是优化建议而非缺陷。
"""
import argparse
import json
import sys
import zipfile

# ---- 阈值（经验值，可按项目调）----
# 校准说明（2026-11-07 全 56 作品实测）：原 120 会把 13 个健康作品误报
# （platformer 主循环 280 块、cat_mouse 166 块都是平铺的正常主循环）。
# Scratch 单脚本几百块是常态，真正的性能风险来自「每帧重算 + 克隆风暴 + 广播风暴」，
# 故 Long Script 阈值放宽到 300，只提示「需要拆子程序」的极端长脚本。
MAX_SCRIPT_BLOCKS = 300      # Long Script：超过建议拆子程序
MAX_CLONE_CREATE = 300       # 铁律12 克隆硬上限；>250 即预警
MAX_BROADCAST = 60           # 广播风暴警示
MAX_SCRIPTS_PER_ROLE = 40    # 单角色脚本过多
BUSY_WAIT_LITERAL = 0.03     # repeat/forever 内 wait ≤ 此值视为空转


def _resolve_literal(blocks, block_id, depth=0):
    """顺着 input/next 链解析一个数值字面量（math_number 的 fields.NUM.value）。"""
    if depth > 20 or block_id not in blocks:
        return None
    b = blocks[block_id]
    op = b.get("opcode", "")
    # 数字块：字段 NUM / VALUE 内是字面量
    for fld in ("NUM", "VALUE", "DURATION", "FROM", "TO", "STEP"):
        fv = (b.get("fields") or {}).get(fld)
        if isinstance(fv, (list, tuple)) and len(fv) >= 2:
            try:
                return float(fv[1])
            except (TypeError, ValueError):
                pass
        elif isinstance(fv, dict) and "value" in fv:
            try:
                return float(fv["value"])
            except (TypeError, ValueError):
                pass
    # 否则看 inputs 里指向的数字块
    for inp in (b.get("inputs") or {}).values():
        ref = inp[1] if isinstance(inp, list) and len(inp) > 1 else None
        if isinstance(ref, str) and ref in blocks:
            v = _resolve_literal(blocks, ref, depth + 1)
            if v is not None:
                return v
    return None


def _walk(blocks, top_id, ancestors, findings):
    """DFS 一个脚本子图，收集 Busy Waiting 信号。"""
    seen = set()
    stack = [(top_id, 0)]
    while stack:
        bid, depth = stack.pop()
        if bid in seen or bid not in blocks or depth > 200:
            continue
        seen.add(bid)
        b = blocks[bid]
        op = b.get("opcode", "")
        new_anc = list(ancestors) + [op]
        in_loop = any(a in ("control_repeat", "control_forever") for a in new_anc)
        if op == "wait":
            lit = _resolve_literal(blocks, bid)
            if lit is not None and lit <= BUSY_WAIT_LITERAL and in_loop:
                findings["busy_waiting"].append(bid)
        # 入边：next + 各 input 指向的块
        nxt = b.get("next")
        if isinstance(nxt, str) and nxt in blocks:
            stack.append((nxt, depth + 1))
        for inp in (b.get("inputs") or {}).values():
            ref = inp[1] if isinstance(inp, list) and len(inp) > 1 else None
            if isinstance(ref, str) and ref in blocks:
                stack.append((ref, depth + 1))


def analyze(sb3):
    with zipfile.ZipFile(sb3) as z:
        d = json.loads(z.read("project.json"))
    blocks_total = 0
    scripts_total = 0
    max_script_blocks = 0
    max_script_role = ""
    max_scripts_role = ""
    max_scripts_count = 0
    clone_create = 0
    broadcast = 0
    busy = []
    role_script_counts = []

    for t in d.get("targets", []):
        name = t.get("name") or ("舞台" if t.get("isStage") else "?")
        blocks = t.get("blocks", {})
        # 序列化的 project.json 没有 scripts 数组；顶层脚本是 topLevel=True 的块
        scripts = [bid for bid, b in blocks.items()
                   if isinstance(b, dict) and b.get("topLevel")]
        blocks_total += len(blocks)
        scripts_total += len(scripts)
        role_script_counts.append((name, len(scripts)))
        if len(scripts) > max_scripts_count:
            max_scripts_count = len(scripts)
            max_scripts_role = name
        for op in blocks.values():
            o = op.get("opcode", "") if isinstance(op, dict) else ""
            if o == "control_create_clone_of":
                clone_create += 1
            elif o in ("event_broadcast", "event_broadcastandwait"):
                broadcast += 1
        for top in scripts:
            if not isinstance(top, str) or top not in blocks:
                continue
            seen = set()
            stack = [top]
            cnt = 0
            while stack:
                bid = stack.pop()
                if bid in seen or bid not in blocks:
                    continue
                seen.add(bid)
                cnt += 1
                b = blocks[bid]
                nxt = b.get("next")
                if isinstance(nxt, str):
                    stack.append(nxt)
                for inp in (b.get("inputs") or {}).values():
                    ref = inp[1] if isinstance(inp, list) and len(inp) > 1 else None
                    if isinstance(ref, str):
                        stack.append(ref)
            if cnt > max_script_blocks:
                max_script_blocks = cnt
                max_script_role = name
            _walk(blocks, top, [], {"busy_waiting": busy})

    return {
        "blocks_total": blocks_total,
        "scripts_total": scripts_total,
        "max_script_blocks": max_script_blocks,
        "max_script_role": max_script_role,
        "max_scripts_role": max_scripts_role,
        "max_scripts_count": max_scripts_count,
        "clone_create": clone_create,
        "broadcast": broadcast,
        "busy_waiting": len(busy),
    }


def _expand(targets):
    """把 CLI 参数展开成 .sb3 路径列表：目录 -> 目录下 *.sb3，文件原样保留。"""
    import os
    out = []
    for t in targets:
        if os.path.isdir(t):
            for n in sorted(os.listdir(t)):
                if n.lower().endswith(".sb3"):
                    out.append(os.path.join(t, n))
        else:
            out.append(t)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sb3", nargs="+", help="一个或多个 .sb3，或一个目录（批量扫描）")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    paths = _expand(args.sb3)
    batch = len(paths) > 1

    total_ok = 0
    total_warn = 0
    warn_lines = []
    for p in paths:
        try:
            r = analyze(p)
        except Exception as e:
            print(f"[check_perf_budget] 解析失败（跳过）{p}: {e}")
            continue

        fails = []
        if r["max_script_blocks"] > MAX_SCRIPT_BLOCKS:
            fails.append(f"Long Script：{r['max_script_role']} 单脚本 {r['max_script_blocks']} 块 (> {MAX_SCRIPT_BLOCKS})")
        if r["clone_create"] > 250:
            fails.append(f"克隆逼近硬上限：create_clone_of 共 {r['clone_create']} (铁律12 上限 300)")
        if r["broadcast"] > MAX_BROADCAST:
            fails.append(f"广播偏多：{r['broadcast']} 次 (> {MAX_BROADCAST})")
        if r["max_scripts_count"] > MAX_SCRIPTS_PER_ROLE:
            fails.append(f"单角色脚本过多：{r['max_scripts_role']} 共 {r['max_scripts_count']} 个")
        if r["busy_waiting"] > 0:
            fails.append(f"Busy Waiting 风险：{r['busy_waiting']} 处 repeat/forever 内 wait≤{BUSY_WAIT_LITERAL}s")

        if fails:
            total_warn += 1
        else:
            total_ok += 1

        if args.json:
            print(json.dumps({"sb3": p, "metrics": r, "fails": fails}, ensure_ascii=False, indent=2))
            continue

        if batch:
            # 批量模式：每作品一行，只列命中项，避免 56 个作品的表格淹没日志
            if fails:
                import os as _os
                warn_lines.append((_os.path.basename(p), fails))
            continue

        # 单文件模式：完整报表
        print("== 性能预算 ==")
        print(f"  积木总数      : {r['blocks_total']}")
        print(f"  脚本总数      : {r['scripts_total']}")
        print(f"  最长脚本      : {r['max_script_blocks']} 块 @ {r['max_script_role']}")
        print(f"  克隆创建      : {r['clone_create']} (硬上限 300)")
        print(f"  广播数        : {r['broadcast']}")
        print(f"  单角色脚本峰值: {r['max_scripts_count']} @ {r['max_scripts_role']}")
        print(f"  BusyWaiting   : {r['busy_waiting']} 处")
        print("--")
        if fails:
            print("  建议优化（非致命）：")
            for f in fails:
                print(f"    ! {f}")
            # 机器可读令牌：与 --strict 退出码对齐，便于编排器统计
            print(f"  PERF_BUDGET_WARN：{len(fails)} 项建议（非致命）")
        else:
            print("  PERF_BUDGET_OK：未触发性能嗅觉阈值")

    if batch and not args.json:
        print("== 性能预算（批量） ==")
        for name, fails in warn_lines:
            print(f"  · {name}: {'; '.join(fails)}")
        print(f"  合计 {len(paths)} 个：OK {total_ok} / WARN {total_warn}")
        if total_warn:
            print(f"  PERF_BUDGET_WARN：{total_warn} 个作品有建议（非致命）")
        else:
            print("  PERF_BUDGET_OK：未触发性能嗅觉阈值")

    has_warn = total_warn > 0 if batch else bool(fails)
    sys.exit(1 if (args.strict and has_warn) else 0)


if __name__ == "__main__":
    main()
