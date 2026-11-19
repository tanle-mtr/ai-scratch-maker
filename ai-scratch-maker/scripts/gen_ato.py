#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 examples/ato_train.yaml —— 第二十七册《ATO 自动驾驶》配套工程。

用法:
    python scripts/gen_ato.py                          # 用默认线路生成 examples/ato_train.yaml
    python scripts/gen_ato.py --line my_line.yaml      # 用自定义线路配置生成
    python scripts/gen_ato.py --out examples/myline.yaml
    python scripts/gen_ato.py --list-lines             # 列出内置线路
    python scripts/gen_ato.py --dry-run                # 只打印线路摘要，不写文件

设计要点（为什么是「数据驱动」而不是「从零重写逻辑」）:
    ATO 的**控制逻辑**（牵引/制动死区、限速钳制、对标停车、开门时序、评分）
    与**具体线路**（站名/站距/区间限速）是两件事。逻辑通用、线路易变，
    所以：
      · 逻辑从模板 IR 复用 —— 保证换线路不会引入逻辑漂移；
      · 线路数据（站名 / 站距 / 限速表）是唯一需要参数化的部分。

    自定义线路配置格式（YAML）:
        name: 深圳地铁 5 号线（ATO 段）
        stations:            # 站名，第 1 站是始发站
          - 前海湾
          - 桂湾
          - 前湾
        distances:           # 相邻站间距（米），长度 = len(stations) - 1
          - 1200
          - 1500
        speeds:              # 每个区间的限速（km/h），长度 = len(distances)
          - 80
          - 75

    校验（缺一即报错，不静默降级）:
      · len(distances) == len(stations) - 1
      · len(speeds)    == len(distances)
      · stations 至少 2 站

    主题一致性：站内停车对标用「剩余里程 vs 区间里程」，区间里程取自 站距 列表，
    因此换线路不需要动任何控制参数。
"""
import argparse
import io
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAMPLES = os.path.join(ROOT, "examples")
TEMPLATE = os.path.join(EXAMPLES, "ato_train.yaml")

# ---------------- 内置线路 ----------------
BUILTIN_LINES = {
    "深铁5号线": {
        "name": "ATO 自动驾驶（多站全自动）",
        "stations": ["前海湾", "桂湾", "前湾"],
        "distances": [1200, 1500],
        "speeds": [80, 75],
    },
    "环线三站": {
        "name": "ATO 自动驾驶（环线三站）",
        "stations": ["西站", "中站", "东站"],
        "distances": [900, 900],
        "speeds": [70, 70],
    },
    "单区间快线": {
        "name": "ATO 自动驾驶（单区间快线）",
        "stations": ["起点站", "终点站"],
        "distances": [2000],
        "speeds": [100],
    },
}


def load_line(path):
    with io.open(path, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    if not isinstance(d, dict):
        raise SystemExit("[gen_ato] 线路配置必须是 YAML 映射: %s" % path)
    return d


def validate_line(line, where="线路"):
    stations = line.get("stations") or []
    distances = line.get("distances") or []
    speeds = line.get("speeds") or []
    if len(stations) < 2:
        raise SystemExit("[gen_ato] %s：至少需要 2 个站名（当前 %d 个）" % (where, len(stations)))
    if len(distances) != len(stations) - 1:
        raise SystemExit("[gen_ato] %s：distances 长度应为 站数-1 = %d，实际 %d"
                         % (where, len(stations) - 1, len(distances)))
    if len(speeds) != len(distances):
        raise SystemExit("[gen_ato] %s：speeds 长度应等于 distances 长度 = %d，实际 %d"
                         % (where, len(distances), len(speeds)))
    for d in distances:
        if not isinstance(d, (int, float)) or d <= 0:
            raise SystemExit("[gen_ato] %s：站距必须为正数，遇到 %r" % (where, d))
    for s in speeds:
        if not isinstance(s, (int, float)) or s <= 0:
            raise SystemExit("[gen_ato] %s：限速必须为正数，遇到 %r" % (where, s))


def apply_line(ir, line):
    """把线路数据写进 IR 模板。

    只动三类数据：舞台列表 站名/站距/限速表，以及两个「首站/次站」初始变量。
    其余逻辑（牵引/制动/停车/开门/评分）原样保留。
    """
    stations = list(line["stations"])
    distances = list(line["distances"])
    speeds = list(line["speeds"])

    stage = ir["project"]["stage"]
    lists = stage.setdefault("lists", {})
    lists["站名"] = stations
    lists["站距"] = distances
    lists["限速表"] = speeds

    # 首站 / 次站 的初始值随线路走。
    # ⚠️ 模板 IR 的绿旗脚本已改成「自己读列表首项」（item_of_list），
    #    所以这里只需保证**舞台变量的声明初值**与线路一致（供监视器/首帧显示），
    #    真正的运行期初值由绿旗脚本从 站名/站距/限速表 取，无需在此覆盖。
    vars_ = stage.setdefault("variables", {})
    vars_["当前站"] = stations[0]
    vars_["下一站"] = stations[1]
    vars_["区间限速"] = speeds[0]
    vars_["推荐速度"] = speeds[0]
    vars_["剩余里程"] = distances[0]
    # ⚠️ 只替换「线路数据」，不动任何控制调校参数（牵引加/制动减/制动率/死区…）。
    #    那些是**与线路无关的工程调校值**，由人工标定；生成器擅自按限速推算
    #    会悄悄改变作品行为（实测：制动率 0.6 被算成 0.8），属于越权。

    ir["project"]["name"] = line.get("name") or ir["project"].get("name")
    return ir


def dump_yaml(ir):
    """输出 YAML，风格与仓库内示例一致：中文不转义、列表用块样式。"""
    text = yaml.safe_dump(
        ir, allow_unicode=True, sort_keys=False, default_flow_style=False, width=100)
    return text


def main():
    ap = argparse.ArgumentParser(description="生成 ATO 自动驾驶示例工程")
    ap.add_argument("--line", help="自定义线路配置 YAML 路径")
    ap.add_argument("--out", default=os.path.join(EXAMPLES, "ato_train.yaml"),
                    help="输出 IR 路径")
    ap.add_argument("--list-lines", action="store_true", help="列出内置线路")
    ap.add_argument("--dry-run", action="store_true", help="只打印线路摘要，不写文件")
    args = ap.parse_args()

    if args.list_lines:
        print("[gen_ato] 内置线路：")
        for k, v in BUILTIN_LINES.items():
            print("  %-12s %s | 站距 %s | 限速 %s"
                  % (k, " → ".join(v["stations"]), v["distances"], v["speeds"]))
        return 0

    if args.line:
        line = load_line(args.line)
        where = os.path.basename(args.line)
    else:
        line = dict(BUILTIN_LINES["深铁5号线"])
        where = "内置线路"

    validate_line(line, where)

    print("[gen_ato] 线路：%s" % " → ".join(line["stations"]))
    print("         站距 %s / 限速 %s" % (line["distances"], line["speeds"]))

    if args.dry_run:
        print("[gen_ato] --dry-run，未写文件")
        return 0

    if not os.path.isfile(TEMPLATE):
        raise SystemExit("[gen_ato] 模板缺失: %s" % TEMPLATE)
    with io.open(TEMPLATE, "r", encoding="utf-8") as f:
        ir = yaml.safe_load(f)

    apply_line(ir, line)
    out = dump_yaml(ir)
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print("[gen_ato] 已生成 %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
