#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sb3 工程解剖：把任意 sb3 压成一份高信号摘要，便于快速理解架构。

用法:
    python scripts/digest_sb3.py <file.sb3> [--top 40] [--sprite 角色名] [--full]

输出（默认紧凑）:
    §1 规模概览   §2 角色清单与职责   §3 全局变量/列表   §4 广播消息表
    §5 自制积木表 §6 opcode 直方图    §7 作者注释        §8 绿旗入口摘要

设计意图：读别人的大工程时，**广播表 + 自制积木表 + 注释**最能还原作者的架构思路，
比逐块反编译快两个数量级。变量/列表的规模能看出数据驱动程度。
"""
import sys, os, json, zipfile
from collections import Counter, defaultdict

# ---------------------------------------------------------------- opcode 中文注记
OPHINT = {
    "event_whenflagclicked": "当绿旗",
    "event_whenbroadcastreceived": "当收到广播",
    "event_broadcast": "广播(不等)",
    "event_broadcastandwait": "广播并等待",
    "event_whenkeypressed": "当按下键",
    "event_whenthisspriteclicked": "当角色被点击",
    "event_whenstageclicked": "当舞台被点击",
    "event_whenbackdropswitchesto": "当背景切换",
    "event_whengreaterthan": "当计时/响度",
    "control_forever": "重复执行(无限)",
    "control_repeat": "重复N次",
    "control_repeat_until": "重复直到",
    "control_while": "当条件成立重复",
    "control_if": "如果",
    "control_if_else": "如果否则",
    "control_wait": "等待秒",
    "control_wait_until": "等待直到",
    "control_stop": "停止",
    "control_create_clone_of": "克隆自己/某角色",
    "control_start_as_clone": "当作为克隆体启动",
    "control_delete_this_clone": "删除此克隆体",
    "motion_gotoxy": "移到xy",
    "motion_setx": "x设为",
    "motion_sety": "y设为",
    "motion_changexby": "x增加",
    "motion_changeyby": "y增加",
    "motion_pointindirection": "面向方向",
    "motion_turnright": "右转",
    "motion_turnleft": "左转",
    "motion_movesteps": "移动步",
    "motion_glidesecstoxy": "滑行到xy",
    "motion_ifonedgebounce": "碰到边缘反弹",
    "motion_setrotationstyle": "旋转方式",
    "looks_switchcostumeto": "换成造型",
    "looks_nextcostume": "下一个造型",
    "looks_switchbackdropto": "换成背景",
    "looks_nextbackdrop": "下一个背景",
    "looks_sayforsecs": "说N秒",
    "looks_say": "说",
    "looks_think": "思考",
    "looks_changesizeby": "大小增加",
    "looks_setsizeto": "大小设为",
    "looks_changeeffectby": "特效增加",
    "looks_seteffectto": "特效设为",
    "looks_cleargraphiceffects": "清除特效",
    "looks_show": "显示",
    "looks_hide": "隐藏",
    "looks_gotofrontback": "移到最前/后",
    "looks_goforwardbackward": "前移/后移层",
    "looks_showlist": "显示列表",
    "looks_hidelist": "隐藏列表",
    "sound_play": "播放声音",
    "sound_playuntildone": "播放声音等完",
    "sound_stopallsounds": "停止所有声音",
    "sound_setvolumeto": "音量设为",
    "data_setvariableto": "变量设为",
    "data_changevariableby": "变量增加",
    "data_showvariable": "显示变量",
    "data_hidevariable": "隐藏变量",
    "data_addtolist": "列表加入",
    "data_deleteoflist": "列表删除",
    "data_deletealloflist": "列表清空",
    "data_insertatlist": "列表插入",
    "data_replaceitemoflist": "列表替换",
    "data_itemoflist": "列表第N项",
    "data_itemnumoflist": "列表项位置",
    "data_lengthoflist": "列表长度",
    "data_listcontainsitem": "列表包含",
    "operator_add": "加",
    "operator_subtract": "减",
    "operator_multiply": "乘",
    "operator_divide": "除",
    "operator_random": "随机数",
    "operator_gt": "大于",
    "operator_lt": "小于",
    "operator_equals": "等于",
    "operator_and": "与",
    "operator_or": "或",
    "operator_not": "非",
    "operator_join": "连接文本",
    "operator_letter_of": "第N个字符",
    "operator_length": "文本长度",
    "operator_contains": "包含文本",
    "operator_mod": "取余",
    "operator_round": "四舍五入",
    "operator_mathop": "数学函数",
    "sensing_touchingobject": "碰到",
    "sensing_touchingcolor": "碰到颜色",
    "sensing_coloristouchingcolor": "颜色碰到颜色",
    "sensing_distanceto": "到某角色距离",
    "sensing_keypressed": "按键按下",
    "sensing_mousedown": "鼠标按下",
    "sensing_mousex": "鼠标x",
    "sensing_mousey": "鼠标y",
    "sensing_timer": "计时器",
    "sensing_resettimer": "重置计时器",
    "sensing_of": "某角色的属性",
    "sensing_current": "当前年月日",
    "sensing_dayssince2000": "2000年至今",
    "pen_clear": "画笔清空",
    "pen_stamp": "图章",
    "pen_penDown": "落笔",
    "pen_penUp": "抬笔",
    "pen_setPenColorToColor": "笔色设为",
    "pen_changePenSizeBy": "笔粗增加",
    "pen_setPenSizeTo": "笔粗设为",
    "pen_setPenColorParamTo": "笔参设为",
    "pen_changePenColorParamBy": "笔参增加",
    "procedures_definition": "定义自制积木",
    "procedures_call": "调用自制积木",
    "argument_reporter_string_number": "参数(字符/数字)",
    "argument_reporter_boolean": "参数(布尔)",
    "videoSensing_videoOn": "视频侦测",
    "text2speech_speakAndWait": "朗读文本",
    "translate_getTranslate": "翻译",
    "music_playNoteForBeats": "演奏音符",
    "music_setInstrument": "设乐器",
    "music_restForBeats": "休止",
}


def s(x, limit=60):
    """安全字符串化 + 截断。"""
    if x is None:
        return ""
    t = str(x)
    return t if len(t) <= limit else t[:limit] + "…"


def load(path):
    z = zipfile.ZipFile(path)
    return json.loads(z.read("project.json"))


def blocks_of(t):
    b = t.get("blocks", {})
    if isinstance(b, dict):
        return b
    return {}


def name_of_var(v):
    return v[0] if isinstance(v, list) and v else str(v)


def collect_varrefs(blocks):
    """扫描 data_* 的 VARIABLE / LIST field，统计每个变量被读/写次数。"""
    reads, writes = Counter(), Counter()
    for bid, b in blocks.items():
        if not isinstance(b, dict):
            continue
        op = b.get("opcode", "")
        f = b.get("fields", {})
        if "VARIABLE" in f:
            nm = f["VARIABLE"][0]
            if op.startswith("data_set") or op.startswith("data_change"):
                writes[nm] += 1
            else:
                reads[nm] += 1
        if "LIST" in f:
            nm = f["LIST"][0]
            if op in ("data_addtolist", "data_deleteoflist", "data_insertatlist",
                      "data_replaceitemoflist", "data_deletealloflist"):
                writes[nm] += 1
            else:
                reads[nm] += 1
        # 嵌套在 inputs 里的变量当作读
        for k, v in b.get("inputs", {}).items():
            if isinstance(v, list) and len(v) > 2 and isinstance(v[2], list) and v[2]:
                nm = name_of_var(v[2])
                if nm:
                    reads[nm] += 1
    return reads, writes


def digest(path, top=40, only_sprite=None, full=False):
    d = load(path)
    tg = d["targets"]
    stage = tg[0]
    all_blocks = sum(len(blocks_of(t)) for t in tg)

    print("=" * 78)
    print(f"# 工程: {os.path.basename(path)}")
    print("=" * 78)

    # ---------------- §1 规模
    print("\n## §1 规模概览")
    clones = sum(1 for t in tg if t.get("isStage") is False and
                 any(isinstance(b, dict) and b.get("opcode") == "control_start_as_clone"
                     for b in blocks_of(t).values()))
    print(f"  角色数(含舞台) = {len(tg)}   块总数 = {all_blocks}   "
          f"克隆体类角色 = {clones}")
    print(f"  造型总数 = {sum(len(t.get('costumes', [])) for t in tg)}   "
          f"声音总数 = {sum(len(t.get('sounds', [])) for t in tg)}")
    opc = Counter()
    for t in tg:
        for b in blocks_of(t).values():
            if isinstance(b, dict):
                opc[b.get("opcode", "?")] += 1
    print(f"  不同 opcode 种类 = {len(opc)}")

    # ---------------- §2 角色清单
    print("\n## §2 角色清单（块数降序）")
    rows = []
    for t in tg:
        if t.get("isStage"):
            continue
        bl = blocks_of(t)
        rows.append((len(bl), t))
    rows.sort(reverse=True, key=lambda x: x[0])
    for n, t in rows:
        if only_sprite and t["name"] != only_sprite:
            continue
        hats = Counter()
        for b in blocks_of(t).values():
            if isinstance(b, dict):
                op = b.get("opcode", "")
                if op.startswith("event_when") or op in ("control_start_as_clone", "procedures_definition"):
                    hats[op] += 1
        # 角色私有变量
        pv = list(t.get("variables", {}).values())
        pvn = [name_of_var(v) for v in pv][:8]
        # 角色私有列表
        pl = list(t.get("lists", {}).values())
        pln = [name_of_var(v) for v in pl][:8]
        hatstr = ", ".join(f"{k.replace('event_when','').replace('control_start_as_clone','克隆体')}×{v}"
                           for k, v in hats.most_common(6))
        extras = []
        if pvn:
            extras.append("私有变量:" + "/".join(pvn))
        if pln:
            extras.append("私有列表:" + "/".join(pln))
        print(f"  - {t['name']:<22} 块{n:<6} 造型{len(t.get('costumes', [])):<4} "
              f"{'| ' + hatstr if hatstr else ''}")
        if extras:
            print(f"      {' ; '.join(extras)}")

    # ---------------- §3 全局变量/列表
    print("\n## §3 舞台全局数据（数据驱动程度）")
    gv = list(stage.get("variables", {}).values())
    gl = list(stage.get("lists", {}).values())
    print(f"  全局变量 {len(gv)} 个 / 全局列表 {len(gl)} 个")
    reads, writes = collect_varrefs(blocks_of(stage))
    # 把各角色的变量读写也并进来（同名合并）
    for t in tg[1:]:
        r2, w2 = collect_varrefs(blocks_of(t))
        reads.update(r2)
        writes.update(w2)

    if gl:
        print("  列表（名字 / 长度 / 前几项）:")
        for v in gl[:24]:
            nm, val = name_of_var(v), v[1]
            n = len(val) if isinstance(val, list) else 0
            head = ""
            if isinstance(val, list) and val:
                head = " | ".join(s(x, 18) for x in val[:5])
            print(f"    · {nm:<20} len={n:<5} {head}")
    if gv:
        print("  变量（名字 / 初值 / 写次数）:")
        for v in gv[:40]:
            nm, val = name_of_var(v), v[1]
            print(f"    · {nm:<20} = {s(val, 26):<28} w={writes.get(nm, 0)}")

    # ---------------- §4 广播表
    print("\n## §4 广播消息表（架构骨架）")
    # 广播名可能来自 stage.broadcasts
    bcast_names = {}
    for bid, b in (stage.get("broadcasts") or {}).items():
        bcast_names[bid] = b if isinstance(b, str) else (b[0] if isinstance(b, list) else str(b))
    recv = Counter()
    send = Counter()
    for t in tg:
        for b in blocks_of(t).values():
            if not isinstance(b, dict):
                continue
            op = b.get("opcode", "")
            if op == "event_whenbroadcastreceived":
                nm = b.get("fields", {}).get("BROADCAST_OPTION", ["?"])[0]
                recv[nm] += 1
            elif op in ("event_broadcast", "event_broadcastandwait"):
                inp = b.get("inputs", {}).get("BROADCAST_INPUT")
                nm = None
                if isinstance(inp, list) and len(inp) > 2 and isinstance(inp[2], list) and inp[2]:
                    nm = inp[2][1] if len(inp[2]) > 1 else None
                    if isinstance(nm, str) and nm in bcast_names:
                        nm = bcast_names[nm]
                elif isinstance(inp, list) and len(inp) > 1 and isinstance(inp[1], str):
                    nm = bcast_names.get(inp[1], inp[1])
                if nm:
                    send[nm] += 1
    if recv or send:
        print(f"  {'消息名':<24} {'接收者数':>6} {'发送次数':>8}")
        allnames = sorted(set(recv) | set(send), key=lambda n: -recv.get(n, 0))
        for nm in allnames:
            print(f"  {s(nm, 24):<24} {recv.get(nm, 0):>6} {send.get(nm, 0):>8}")
    else:
        print("  （无广播——纯轮询架构）")

    # ---------------- §5 自制积木
    print("\n## §5 自制积木表（复用与抽象度）")
    procs = defaultdict(list)
    for t in tg:
        for b in blocks_of(t).values():
            if not isinstance(b, dict):
                continue
            if b.get("opcode") != "procedures_prototype":
                continue
            mu = b.get("mutation", {})
            pc = mu.get("proccode", "?")
            warp = mu.get("warp", "false")
            args = mu.get("argumentnames", "[]")
            try:
                args = json.loads(args)
            except Exception:
                args = []
            procs[(pc, warp, tuple(args))].append(t["name"])
    if procs:
        for (pc, warp, args), owners in sorted(procs.items(), key=lambda kv: kv[0][0]):
            w = "  [立即刷新]" if str(warp).lower() == "true" else ""
            a = f" ({', '.join(args)})" if args else ""
            print(f"  · {pc}{a}{w}   —在 {', '.join(owners)}")
    else:
        print("  （无自制积木——全平铺，可维护性差）")

    # ---------------- §6 opcode 直方图
    print(f"\n## §6 opcode 直方图 top{top}")
    for op, n in opc.most_common(top):
        print(f"  {n:>6}  {op:<34} {OPHINT.get(op, '')}")

    # ---------------- §7 注释
    print("\n## §7 作者注释")
    cnt = 0
    for t in tg:
        for cid, c in (t.get("comments") or {}).items():
            txt = (c.get("text") or "").strip()
            if not txt:
                continue
            cnt += 1
            if cnt > 60 and not full:
                print("  …（截断，用 --full 看全部）")
                break
            first = txt.replace("\n", " ⏎ ")
            print(f"  [{t['name']}] {s(first, 150)}")
        if cnt > 60 and not full:
            break
    if cnt == 0:
        print("  （无注释）")

    # ---------------- §8 绿旗入口
    print("\n## §8 绿旗入口脚本（每个角色第一条链的开头 6 块）")
    for t in tg:
        bl = blocks_of(t)
        for bid, b in bl.items():
            if not isinstance(b, dict) or b.get("opcode") != "event_whenflagclicked":
                continue
            chain = []
            nid = b.get("next")
            seen = 0
            while nid and seen < 6:
                nb = bl.get(nid)
                if not isinstance(nb, dict):
                    break
                op = nb.get("opcode", "")
                label = OPHINT.get(op, op)
                # 附带关键 field
                fld = ""
                f = nb.get("fields", {})
                if "VARIABLE" in f:
                    fld = f" [{f['VARIABLE'][0]}]"
                elif "BROADCAST_OPTION" in f:
                    fld = f" [{f['BROADCAST_OPTION'][0]}]"
                chain.append(label + fld)
                nid = nb.get("next")
                seen += 1
            print(f"  [{t['name']}] " + " → ".join(chain))
            break


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return
    path = args[0]
    top, only, full = 40, None, False
    i = 1
    while i < len(args):
        if args[i] == "--top":
            top = int(args[i + 1]); i += 2
        elif args[i] == "--sprite":
            only = args[i + 1]; i += 2
        elif args[i] == "--full":
            full = True; i += 1
        else:
            i += 1
    digest(path, top=top, only_sprite=only, full=full)


if __name__ == "__main__":
    main()
