#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把社区作品提炼的 5 个模式（§C1–§C5）生成成可编译的 IR。

模板会自动从社区资产包挑选真实素材，写 `asset: community:<id>`，
所以生成出来的工程直接带真实美术/音效，不用从零画。

用法（skill 根目录）：
    python scripts/gen_community_template.py --list
    python scripts/gen_community_template.py --template numberblock_band --count 8 --out examples/band.yaml
    python scripts/gen_community_template.py --template backdrop_room_fsm --count 6 --out examples/rooms.yaml
    python scripts/gen_community_template.py --template audio_sequence_player --count 6 --out examples/seq.yaml
    python scripts/gen_community_template.py --template clone_swarm --count 12 --out examples/swarm.yaml
    python scripts/gen_community_template.py --template list_maze --width 8 --height 6 --out examples/maze.yaml

生成后再按常规流程编译：
    python scripts/build_sb3.py --ir examples/band.yaml --out examples/output/band.sb3 --workdir <tmp>
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asset_pack import load_manifest  # noqa: E402

TEMPLATES = {
    "numberblock_band": "§C5 广播编排的数字方块乐队（指挥者广播 + 每方块接收帽）",
    "audio_sequence_player": "§C4 极简音频序列播放器（单角色 换造型+播音+等待）",
    "backdrop_room_fsm": "§C1 背景驱动的房间状态机（背景造型即房间 + 切换钩子）",
    "clone_swarm": "§C2 克隆海生存骨架（克隆当实体 + 列表当世界）",
    "list_maze": "§C3 列表即迷宫网格（一维列表存二维地图 + 索引换算）",
}


def pick(manifest, kind, cid=None, n=1, max_bytes=200 * 1024):
    rows = [a for a in manifest["assets"]
            if a["kind"] == kind and a["bytes"] <= max_bytes
            and (cid is None or any(s["cid"] == cid for s in a["sources"]))]
    rows.sort(key=lambda a: (not bool(a.get("sample_file")), a["bytes"]))
    if len(rows) < n:
        rows = [a for a in manifest["assets"] if a["kind"] == kind and a["bytes"] <= max_bytes]
        rows.sort(key=lambda a: (not bool(a.get("sample_file")), a["bytes"]))
    return rows[:n]


def entry(a, name=None):
    d = {"asset": a["ir_asset"]}
    if name:
        d["name"] = name
    return d


def base(name, backdrop):
    return {"project": {
        "name": name,
        "stage": {"backdrops": [backdrop], "scripts": []},
        "sprites": [],
    }}


def t_numberblock_band(m, args):
    cos = pick(m, "costume", args.cid or "NGwJJ66J", args.count)
    snd = pick(m, "sound", args.cid or "NGwJJ66J", args.count)
    bd = pick(m, "backdrop", args.cid or "NGwJJ66J", 1)[0]
    ir = base("数字方块乐队（{} 声部）".format(len(cos)), entry(bd))
    stage = ir["project"]["stage"]
    notes = ["音符{}".format(i + 1) for i in range(len(cos))]
    stage["scripts"] = [[{"when_green_flag_clicked": None}] +
                        [{"broadcast_and_wait": {"message": nt}} for nt in notes]]
    for i, a in enumerate(cos):
        cs = entry(a, "方块{}".format(i + 1))
        sounds = [entry(snd[i], "声{}".format(i + 1))] if i < len(snd) else []
        script = [
            {"when_receive": {"message": notes[i]}},
            {"show": None},
            {"switch_costume": {"costume": "方块{}".format(i + 1)}},
        ]
        if sounds:
            script.append({"play_sound": {"sound": "声{}".format(i + 1)}})
        script += [{"wait": {"secs": args.beat}}, {"hide": None}]
        ir["project"]["sprites"].append({
            "name": "方块{}".format(i + 1), "x": -180 + i * 40, "y": 0,
            "costumes": [cs], "sounds": sounds, "scripts": [script],
        })
    return ir


def t_audio_sequence_player(m, args):
    cos = pick(m, "costume", args.cid or "3AwJJ66J", args.count)
    snd = pick(m, "sound", args.cid or "3AwJJ66J", args.count, max_bytes=2 * 1024 * 1024)
    bd = pick(m, "backdrop", None, 1)[0]
    ir = base("音频序列播放器（{} 段）".format(len(cos)), entry(bd))
    script = [{"when_green_flag_clicked": None}]
    for i in range(len(cos)):
        script.append({"switch_costume": {"costume": "画面{}".format(i + 1)}})
        if i < len(snd):
            script.append({"play_sound": {"sound": "片段{}".format(i + 1)}})
        script.append({"wait": {"secs": args.beat}})
    ir["project"]["sprites"] = [{
        "name": "播放器", "x": 0, "y": 0,
        "costumes": [entry(cos[i], "画面{}".format(i + 1)) for i in range(len(cos))],
        "sounds": [entry(snd[i], "片段{}".format(i + 1)) for i in range(len(snd))],
        "scripts": [script],
    }]
    return ir


def t_backdrop_room_fsm(m, args):
    bds = pick(m, "backdrop", args.cid or "pGeJJ66J", args.count)
    ir = base("背景房间状态机（{} 房间）".format(len(bds)), entry(bds[0], "房间1"))
    stage = ir["project"]["stage"]
    stage["backdrops"] = [entry(bds[i], "房间{}".format(i + 1)) for i in range(len(bds))]
    stage["scripts"] = [
        [{"when_green_flag_clicked": None},
         {"switch_backdrop": {"backdrop": "房间1"}}],
    ]
    for i in range(len(bds)):
        stage["scripts"].append([
            {"when_backdrop_switches_to": {"backdrop": "房间{}".format(i + 1)}},
            {"broadcast": "进入房间{}".format(i + 1)},
        ])
        stage["scripts"].append([
            {"when_receive": {"message": "去房间{}".format(i + 1)}},
            {"switch_backdrop": {"backdrop": "房间{}".format(i + 1)}},
        ])
    ir["project"]["sprites"] = [{
        "name": "HUD", "x": 0, "y": 0,
        "costumes": [entry(pick(m, "costume", None, 1)[0], "默认")],
        "scripts": [[
            {"when_receive": {"message": "进入房间{}".format(i + 1)}},
            {"say": {"text": "已进入房间{}".format(i + 1), "secs": 1}},
        ] for i in range(len(bds))],
    }]
    return ir


def t_clone_swarm(m, args):
    bd = pick(m, "backdrop", None, 1)[0]
    cos = pick(m, "costume", args.cid or "jmIo666J", 1)
    ir = base("克隆海生存骨架（{} 实体）".format(args.count), entry(bd))
    stage = ir["project"]["stage"]
    stage["lists"] = {"实体X": [0] * args.count, "实体Y": [0] * args.count}
    stage["scripts"] = [[{"when_green_flag_clicked": None}] +
                        [{"create_clone_of": {"clone": "_myself_"}} for _ in range(args.count)]]
    clone_script = [
        {"when_start_as_clone": None},
        {"set_variable": {"var": "是克隆", "value": 1}},
        {"goto_xy": {"x": 0, "y": 0}},
        {"show": None},
        {"forever": {"do": [{"change_x": {"dx": 1}}, {"wait": {"secs": 0.05}}]}},
    ]
    ir["project"]["sprites"] = [{
        "name": "实体母体", "x": 0, "y": 0,
        "variables": {"是克隆": 0},
        "costumes": [entry(cos[0], "实体")],
        "scripts": [clone_script],
    }]
    return ir


def t_list_maze(m, args):
    w, h = args.width, args.height
    cells = [1 if (i % w) not in (0, w - 1) else 0 for i in range(w * h)]
    cells[0], cells[-1] = 1, 2
    bd = pick(m, "backdrop", "2SwJJ66J", 1)[0]
    cos = pick(m, "costume", "2SwJJ66J", 1)
    ir = base("列表迷宫 {}x{}".format(w, h), entry(bd))
    stage = ir["project"]["stage"]
    stage["lists"] = {"迷宫": cells}
    stage["variables"] = {"玩家X": 1, "玩家Y": 1, "索引": 0}
    stage["scripts"] = [[
        {"when_green_flag_clicked": None},
        {"set_variable": {"var": "玩家X", "value": 1}},
        {"set_variable": {"var": "玩家Y", "value": 1}},
        {"broadcast": "刷新格子"},
    ]]
    query = [
        {"when_receive": {"message": "刷新格子"}},
        {"set_variable": {"var": "索引", "value": {
            "add": [{"multiply": [{"var": "玩家Y"}, w]},
                    {"add": [{"var": "玩家X"}, 1]}]}}},
        {"say": {"text": {"item_of_list": {"list": "迷宫", "index": {"var": "索引"}}}, "secs": 1}},
    ]
    ir["project"]["sprites"] = [{
        "name": "玩家", "x": 0, "y": 0,
        "costumes": [entry(cos[0], "玩家")],
        "scripts": [query],
    }]
    return ir


BUILDERS = {
    "numberblock_band": t_numberblock_band,
    "audio_sequence_player": t_audio_sequence_player,
    "backdrop_room_fsm": t_backdrop_room_fsm,
    "clone_swarm": t_clone_swarm,
    "list_maze": t_list_maze,
}


def main():
    ap = argparse.ArgumentParser(description="生成社区模式 IR 模板")
    ap.add_argument("--list", action="store_true", help="列出模板")
    ap.add_argument("--template", choices=list(BUILDERS))
    ap.add_argument("--out", help="输出 IR 文件（.json 或 .yaml）")
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--beat", type=float, default=0.5)
    ap.add_argument("--width", type=int, default=8)
    ap.add_argument("--height", type=int, default=6)
    ap.add_argument("--cid", help="限定素材来源 CID")
    args = ap.parse_args()
    if args.list or not args.template:
        for k, v in TEMPLATES.items():
            print("{:24s} {}".format(k, v))
        return
    ir = BUILDERS[args.template](load_manifest(), args)
    text = json.dumps(ir, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        sprites = len(ir["project"]["sprites"])
        print("[完成] {} -> {}（{} 个角色）".format(args.template, args.out, sprites))
    else:
        print(text)


if __name__ == "__main__":
    main()
