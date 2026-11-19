#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 sb3 的脚本反编译成紧凑伪代码，用于理解大型工程（万块级）。

用法:
  python scripts/decompile_sb3.py <file.sb3> --target "角色名" [--max 200]
  python scripts/decompile_sb3.py <file.sb3> --list             # 列角色
  python scripts/decompile_sb3.py <file.sb3> --grep "里程"       # 全局搜变量/列表名出现处
  python scripts/decompile_sb3.py <file.sb3> --target X --only 里程,速度   # 只打印含关键字的行

设计要点（与 dump_scripts.py 的区别）：dump_scripts 逐层缩进打印 block 树，块多时不可读；
本工具把表达式压成一行中缀式（如 `速度 + 0.6*(限速-速度)`），语句压成一行，
并对 if/else/repeat/forever 做结构化缩进 + 显示控制流标记，便于快速还原算法。
"""
import sys, json, zipfile, argparse

# ---------- 表达式渲染 ----------
BIN = {
    "operator_add": "+", "operator_subtract": "-", "operator_multiply": "*", "operator_divide": "/",
    "operator_mod": "mod", "operator_gt": ">", "operator_lt": "<", "operator_equals": "=",
    "operator_and": "and", "operator_or": "or",
}
FMT2 = {"operator_mathop": "math", "operator_letter_of": "letter", "operator_length": "len",
        "operator_contains": "contains", "operator_join": "join"}


class Dec:
    def __init__(self, data, target):
        self.t = target
        self.blocks = target.get("blocks") or {}
        self.stage = data["targets"][0]
        # 变量/列表 id -> 名字（含角色私有 + 舞台全局）
        self.vnames = {}
        for tg in (self.stage, target):
            for k, v in (tg.get("variables") or {}).items():
                nm = v.get("name") if isinstance(v, dict) else v[0]
                self.vnames[k] = nm
            for k, v in (tg.get("lists") or {}).items():
                nm = v.get("name") if isinstance(v, dict) else v[0]
                self.vnames[k] = nm
        self.bnames = {}
        for k, v in (self.stage.get("broadcasts") or {}).items():
            self.bnames[k] = v.get("name") if isinstance(v, dict) else v

    # --- 输入取值 ---
    def _pick(self, iv):
        """返回 (blockId|None, literal|None)"""
        if not isinstance(iv, list) or len(iv) < 2:
            return None, iv
        mode, first = iv[0], iv[1]
        if isinstance(first, str) and first in self.blocks:
            return first, None
        if isinstance(first, list):
            return None, first[1] if len(first) > 1 else ""
        return None, first

    def expr(self, iv):
        bid, lit = self._pick(iv)
        if bid:
            return self.block_expr(bid)
        if lit is None:
            return "?"
        if isinstance(lit, bool):
            return "true" if lit else "false"
        s = str(lit)
        return s

    def block_expr(self, bid):
        b = self.blocks.get(bid)
        if not isinstance(b, dict):
            return "?"
        op = b.get("opcode", "")
        ins = b.get("inputs") or {}
        flds = b.get("fields") or {}

        def f(name):
            v = flds.get(name)
            if not v:
                return ""
            raw = v[0] if isinstance(v, list) else v
            if name in ("VARIABLE", "LIST"):
                return self.vnames.get(raw, str(raw))
            if name == "BROADCAST_OPTION":
                return self.bnames.get(raw, str(raw))
            return str(raw)

        if op in BIN:
            a = self.expr(ins.get("NUM1") or ins.get("OPERAND1"))
            c = self.expr(ins.get("NUM2") or ins.get("OPERAND2"))
            p = BIN[op]
            return f"({a} {p} {c})"
        if op == "operator_not":
            return f"(not {self.expr(ins.get('OPERAND'))})"
        if op == "operator_join":
            return f"join({self.expr(ins.get('STRING1'))},{self.expr(ins.get('STRING2'))})"
        if op == "operator_letter_of":
            return f"letter({self.expr(ins.get('LETTER'))},{self.expr(ins.get('STRING'))})"
        if op == "operator_length":
            return f"len({self.expr(ins.get('STRING'))})"
        if op == "operator_contains":
            return f"contains({self.expr(ins.get('STRING1'))},{self.expr(ins.get('STRING2'))})"
        if op == "operator_mathop":
            return f"{f('OPERATOR')}({self.expr(ins.get('NUM'))})"
        if op == "operator_random":
            return f"random({self.expr(ins.get('FROM'))},{self.expr(ins.get('TO'))})"
        if op == "operator_round":
            return f"round({self.expr(ins.get('NUM'))})"
        if op in ("data_variable",):
            return f()
        if op == "data_listcontents":
            return f"{f()}[]"
        if op == "data_itemoflist":
            return f"{f('LIST')}[{self.expr(ins.get('INDEX'))}]"
        if op == "data_itemnumoflist":
            return f"indexOf({f('LIST')},{self.expr(ins.get('ITEM'))})"
        if op == "data_lengthoflist":
            return f"len({f('LIST')})"
        if op == "data_listcontainsitem":
            return f"contains({f('LIST')},{self.expr(ins.get('ITEM'))})"
        if op == "sensing_touchingobject":
            return f"touching({self.expr(ins.get('TOUCHINGOBJECTMENU'))})"
        if op == "sensing_keypressed":
            return f"key({self.expr(ins.get('KEY_OPTION'))})"
        if op == "sensing_mousedown":
            return "mouseDown"
        if op == "sensing_mousex":
            return "mouseX"
        if op == "sensing_mousey":
            return "mouseY"
        if op == "sensing_timer":
            return "timer"
        if op == "sensing_of":
            return f"{f('PROPERTY')} of {self.expr(ins.get('OBJECT'))}"
        if op.endswith("_menu"):
            # 菜单块（克隆目标 / 声音 / 造型 / 对象 …）直接把字段值当字面量
            for k, v in flds.items():
                raw = v[0] if isinstance(v, list) else v
                return str(raw)
            return op.replace("_menu", "")
        if op == "motion_xposition":
            return "x"
        if op == "motion_yposition":
            return "y"
        if op == "motion_direction":
            return "dir"
        if op in ("looks_costume",):
            return f"costume#{f('COSTUME')}"
        if op in ("looks_backdrops",):
            return f"backdrop#{f('BACKDROP')}"
        if op == "looks_size":
            return "size"
        if op == "control_get_counter":
            return "counter"
        if op == "argument_reporter_string_number" or op == "argument_reporter_boolean":
            return f("VALUE")
        if op == "procedures_call":
            mut = b.get("mutation") or {}
            return dump_proccode(mut.get("proccode", ""))
        if op == "text":
            return repr(b.get("fields", {}).get("TEXT", [""])[0])
        return f"<{op}>"

    # --- 语句渲染 ---
    def sub(self, iv, ind):
        # 允许直接传 blockId（字符串）或输入数组（[2, id]）
        if isinstance(iv, str):
            bid = iv if iv in self.blocks else None
        else:
            bid, _ = self._pick(iv)
        out = []
        while bid:
            b = self.blocks.get(bid)
            if not isinstance(b, dict):
                break
            out.extend(self.stmt(b, ind))
            bid = b.get("next")
        return out

    def stmt(self, b, ind):
        pad = "  " * ind
        op = b.get("opcode", "")
        ins = b.get("inputs") or {}
        flds = b.get("fields") or {}

        def f(name):
            v = flds.get(name)
            if not v:
                return ""
            raw = v[0] if isinstance(v, list) else v
            if name in ("VARIABLE", "LIST"):
                return self.vnames.get(raw, str(raw))
            if name == "BROADCAST_OPTION":
                return self.bnames.get(raw, str(raw))
            return str(raw)

        E = lambda k: self.expr(ins.get(k))

        if op == "control_if":
            out = [f"{pad}if {E('CONDITION')}:"]
            body = self.sub(("x", ins.get("SUBSTACK")), ind + 1) if False else None
            out += self._substk(ins.get("SUBSTACK"), ind + 1)
            return out
        if op == "control_if_else":
            out = [f"{pad}if {E('CONDITION')}:"]
            out += self._substk(ins.get("SUBSTACK"), ind + 1)
            out.append(f"{pad}else:")
            out += self._substk(ins.get("SUBSTACK2"), ind + 1)
            return out
        if op == "control_repeat":
            out = [f"{pad}repeat {E('TIMES')}:"]
            out += self._substk(ins.get("SUBSTACK"), ind + 1)
            return out
        if op == "control_repeat_until":
            out = [f"{pad}repeatUntil {E('CONDITION')}:"]
            out += self._substk(ins.get("SUBSTACK"), ind + 1)
            return out
        if op == "control_forever":
            out = [f"{pad}forever:"]
            out += self._substk(ins.get("SUBSTACK"), ind + 1)
            return out
        if op == "control_wait_until":
            return [f"{pad}waitUntil {E('CONDITION')}"]
        if op == "control_wait":
            return [f"{pad}wait {E('DURATION')}"]
        if op == "control_stop":
            return [f"{pad}stop {f('STOP_OPTION')}"]
        if op == "control_create_clone_of":
            return [f"{pad}clone {self.expr_proj(ins.get('CLONE_OPTION'))}"]
        if op == "control_delete_this_clone":
            return [f"{pad}deleteClone"]
        if op == "event_broadcast":
            return [f"{pad}bcast {self.expr_proj(ins.get('BROADCAST_INPUT'))}"]
        if op == "event_broadcastandwait":
            return [f"{pad}bcastWait {self.expr_proj(ins.get('BROADCAST_INPUT'))}"]
        if op.startswith("event_when"):
            tag = {
                "event_whenflagclicked": "when Flag",
                "event_whenkeypressed": f"when key {f('KEY_OPTION')}",
                "event_whenthisspriteclicked": "when Clicked",
                "event_whenstageclicked": "when StageClicked",
                "event_whenbackdropswitchesto": f"when Backdrop {f('BACKDROP')}",
                "event_whengreaterthan": f"when {f('WHENGREATERTHANMENU')} > {E('VALUE')}",
                "event_whenbroadcastreceived": f"when {f('BROADCAST_OPTION')}",
            }.get(op, op)
            return [f"{pad}--- {tag} ---"]
        if op == "procedures_definition":
            mut = b.get("inputs", {}).get("custom_block")
            proto = None
            if mut and isinstance(mut, list) and len(mut) > 1 and isinstance(mut[1], str):
                proto = self.blocks.get(mut[1], {}).get("mutation", {})
            pc = (proto or {}).get("proccode", "?")
            args = (proto or {}).get("argumentnames", "[]")
            return [f"{pad}=== define {dump_proccode(pc)} args={args} ==="]
        if op == "procedures_call":
            mut = b.get("mutation") or {}
            ids = json.loads(mut.get("argumentids") or "[]")
            vals = [self.expr(ins.get(i)) for i in ids]
            return [f"{pad}{dump_proccode(mut.get('proccode',''))}({', '.join(vals)})"]
        if op == "data_setvariableto":
            return [f"{pad}{f('VARIABLE')} = {E('VALUE')}"]
        if op == "data_changevariableby":
            return [f"{pad}{f('VARIABLE')} += {E('VALUE')}"]
        if op == "data_addtolist":
            return [f"{pad}{f('LIST')}.add({E('ITEM')})"]
        if op == "data_deleteoflist":
            return [f"{pad}{f('LIST')}.del({E('INDEX')})"]
        if op == "data_deletealloflist":
            return [f"{pad}{f('LIST')}.clear()"]
        if op == "data_replaceitemoflist":
            return [f"{pad}{f('LIST')}[{E('INDEX')}] = {E('ITEM')}"]
        if op == "data_insertatlist":
            return [f"{pad}{f('LIST')}.insert({E('INDEX')}, {E('ITEM')})"]
        if op == "data_showvariable":
            return [f"{pad}show {f('VARIABLE')}"]
        if op == "data_hidevariable":
            return [f"{pad}hide {f('VARIABLE')}"]
        if op == "motion_gotoxy":
            return [f"{pad}goto({E('X')}, {E('Y')})"]
        if op == "motion_setx":
            return [f"{pad}x = {E('X')}"]
        if op == "motion_sety":
            return [f"{pad}y = {E('Y')}"]
        if op == "motion_changexby":
            return [f"{pad}x += {E('DX')}"]
        if op == "motion_changeyby":
            return [f"{pad}y += {E('DY')}"]
        if op == "motion_pointindirection":
            return [f"{pad}point {E('DIRECTION')}"]
        if op == "motion_turnright":
            return [f"{pad}turnRight {E('DEGREES')}"]
        if op == "motion_turnleft":
            return [f"{pad}turnLeft {E('DEGREES')}"]
        if op == "motion_setrotationstyle":
            return [f"{pad}rotationStyle {f('STYLE')}"]
        if op == "looks_switchcostumeto":
            return [f"{pad}costume {self.expr_proj(ins.get('COSTUME'))}"]
        if op == "looks_nextcostume":
            return [f"{pad}nextCostume"]
        if op == "looks_switchbackdropto":
            return [f"{pad}backdrop {self.expr_proj(ins.get('BACKDROP'))}"]
        if op == "looks_nextbackdrop":
            return [f"{pad}nextBackdrop"]
        if op == "looks_show":
            return [f"{pad}show"]
        if op == "looks_hide":
            return [f"{pad}hide"]
        if op == "looks_setsizeto":
            return [f"{pad}size = {E('SIZE')}"]
        if op == "looks_changesizeby":
            return [f"{pad}size += {E('CHANGE')}"]
        if op == "looks_changeeffectby":
            return [f"{pad}{f('EFFECT')} += {E('CHANGE')}"]
        if op == "looks_seteffectto":
            return [f"{pad}{f('EFFECT')} = {E('VALUE')}"]
        if op == "looks_cleargraphiceffects":
            return [f"{pad}clearEffects"]
        if op == "looks_gotofrontback":
            return [f"{pad}layer {f('FRONT_BACK')}"]
        if op == "looks_goforwardbackward":
            return [f"{pad}layer {f('FORWARD_BACKWARD')} {E('NUM')}"]
        if op == "looks_say":
            return [f"{pad}say {E('MESSAGE')}"]
        if op == "looks_sayforsecs":
            return [f"{pad}say {E('MESSAGE')} for {E('SECS')}"]
        if op == "sound_play":
            return [f"{pad}playSound {self.expr_proj(ins.get('SOUND_MENU'))}"]
        if op == "sound_playuntildone":
            return [f"{pad}playSoundWait {self.expr_proj(ins.get('SOUND_MENU'))}"]
        if op == "sound_stopallsounds":
            return [f"{pad}stopAllSounds"]
        if op == "sound_setvolumeto":
            return [f"{pad}volume = {E('VOLUME')}"]
        if op == "sensing_askandwait":
            return [f"{pad}ask {E('QUESTION')}"]
        if op == "sensing_answer":
            return "answer"
        if op == "sensing_resettimer":
            return [f"{pad}resetTimer"]
        if op == "sensing_setdragmode":
            return [f"{pad}dragMode {f('DRAG_MODE')}"]
        if op == "pen_clear":
            return [f"{pad}penClear"]
        if op == "pen_penDown":
            return [f"{pad}penDown"]
        if op == "pen_penUp":
            return [f"{pad}penUp"]
        if op == "pen_stamp":
            return [f"{pad}stamp"]
        if op == "pen_setPenColorToColor":
            return [f"{pad}penColor {E('COLOR')}"]
        if op == "pen_setPenSizeTo":
            return [f"{pad}penSize {E('SIZE')}"]
        if op == "pen_changePenSizeBy":
            return [f"{pad}penSize += {E('SIZE')}"]
        if op == "pen_setPenSizeToParam":
            return [f"{pad}penSetParam {f('PARAM')} {E('VALUE')}"]
        # 兜底：把输入/字段都打出来
        parts = []
        for k, v in ins.items():
            parts.append(f"{k}={self.expr(v)}")
        for k, v in flds.items():
            parts.append(f"{k}={f(k)}")
        return [f"{pad}<{op}> {' '.join(parts)}"]

    def expr_proj(self, iv):
        """菜单类输入（克隆目标/造型/声音）：可能直接是 string 或 [type, name]"""
        bid, lit = self._pick(iv)
        if bid:
            return self.block_expr(bid)
        if isinstance(lit, bool):
            return str(lit)
        return str(lit)

    def _substk(self, iv, ind):
        if not iv:
            return []
        if isinstance(iv, str):
            return self.sub(iv, ind)
        bid, _ = self._pick(iv)
        if not bid:
            return []
        return self.sub(bid, ind)

    # --- 脚本入口 ---
    def hats(self):
        """返回 [(hatBlockId, [行])]，每个顶层脚本一块（hat 无 parent）"""
        out = []
        for bid, b in self.blocks.items():
            if not isinstance(b, dict):
                continue
            op = b.get("opcode", "")
            if op.startswith("procedures_definition") or op.startswith("event_when"):
                out.append(bid)
        # 只保留真正顶层（parent 为空）
        tops = [h for h in out if not self.blocks[h].get("parent")]
        res = []
        for h in tops:
            lines = self.stmt(self.blocks[h], 0)
            nid = self.blocks[h].get("next")
            while nid:
                nb = self.blocks.get(nid)
                if not isinstance(nb, dict):
                    break
                lines += self.stmt(nb, 0)
                nid = nb.get("next")
            res.append((h, lines))
        return res


def dump_proccode(pc: str) -> str:
    """把 proccode 的 %s/%n/%b 占位替换成参数位置提示"""
    return pc.replace("%s", "⟨s⟩").replace("%n", "⟨n⟩").replace("%b", "⟨b⟩")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--target")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all", action="store_true", help="导出全部角色脚本（重定向到文件后 grep）")
    ap.add_argument("--max", type=int, default=400)
    ap.add_argument("--only", default="")
    a = ap.parse_args()

    with zipfile.ZipFile(a.file) as z:
        data = json.loads(z.read("project.json"))
    tgts = data["targets"]
    if a.list:
        for t in tgts:
            n = len(t.get("blocks") or {})
            print(f"{t['name']:<28} blocks={n}")
        return
    if a.all:
        for t in tgts:
            if not (t.get("blocks") or {}):
                continue
            d = Dec(data, t)
            print(f"\n\n#################### TARGET: {t['name']} ####################")
            for hid, lines in d.hats():
                print()
                for ln in lines:
                    print(ln)
        return
    if not a.target:
        print("需要 --target / --all / --list", file=sys.stderr); return
    t = next((x for x in tgts if x["name"] == a.target or x["name"].strip() == a.target.strip()), None)
    if not t:
        # 宽松匹配：去掉所有空白后比较（社区工程常用「68 对 标」这种字间空格）
        def sq(s):
            return "".join(s.split())
        t = next((x for x in tgts if sq(x["name"]) == sq(a.target)), None)
    if not t:
        cand = [x["name"] for x in tgts if any(ch in x["name"] for ch in a.target)][:12]
        print(f"未找到 --target={a.target!r}，候选：{cand}", file=sys.stderr); return

    d = Dec(data, t)
    only = [s for s in a.only.replace("，", ",").split(",") if s.strip()]
    n = 0
    for hid, lines in d.hats():
        print(f"\n######## {t['name']} ########")
        for ln in lines:
            if only and not any(k in ln for k in only) and ln.strip().startswith("-") is False:
                if not ln.strip().startswith("---"):
                    continue
            print(ln)
            n += 1
            if n >= a.max:
                print(f"... (截断于 {a.max} 行)")
                return


if __name__ == "__main__":
    main()
