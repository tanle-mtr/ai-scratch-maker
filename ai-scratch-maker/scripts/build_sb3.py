#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IR -> 合法 Scratch 3.0 .sb3 的序列化器。

设计要点
--------
- AI 只写一份清晰的中间表示（IR, YAML/JSON）；本脚本把易错的 sb3 结构全部收敛到
  被测试覆盖的代码里。
- 积木的输入/字段结构来自 references/blocks-spec.json（由 scripts/extract_blocks_spec.js
  从 Scratch 官方源码抽取），因此不会漏积木、也不会写错 opcode。
- 关键编码规则（见 references/blocks-spec.md）：
    inputs : [status, ...]  status 1=影子值 2=仅积木 3=影子+积木
    fields : {名字: [值, id]}   普通下拉 id 为 null；变量/列表下拉带 id
    菜单(动态下拉) 输入编码为 [1, "裸字符串"]
    广播   输入编码为 [1, [11, 名字, id]]
- 支持云变量（isCloud）；Scratch 3.0 不支持云列表，会给出明确告警并退化为普通列表。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import uuid
import wave
import zipfile

import yaml

# 仓库根目录（scripts/ 的上级），用于定位 references/ 与默认缓存目录。
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)

# 生成「文字标签」需要中文字体，复用 make_ui_assets 的字体候选与测量函数
try:
    from make_ui_assets import (
        FONT_CANDIDATES as _FONT_CANDIDATES,
        load_font as _mu_load_font,
        _text_size as _mu_text_size,
    )
except Exception:
    _FONT_CANDIDATES, _mu_load_font, _mu_text_size = [], None, None

# primitive 类型码（见 scratch-vm 序列化规范）
PRIM = {
    "number": 4,     # MATH_NUM_PRIMITIVE
    "angle": 8,      # ANGLE_NUM_PRIMITIVE
    "color": 9,      # COLOR_PICKER_PRIMITIVE
    "text": 10,      # TEXT_PRIMITIVE
    "broadcast": 11, # BROADCAST_PRIMITIVE
    "variable": 12,  # VAR_PRIMITIVE
    "list": 13,      # LIST_PRIMITIVE
}

CLOUD_LIMIT = 10   # scratch-vm: 单个项目最多 10 个云变量


# ------------------------------------------------------------------ #
# 文本/数字素材的辅助函数（生成「文字标签」、量数字图尺寸）
# ------------------------------------------------------------------ #
_LABEL_TMP = None


def _label_tmp_dir():
    """标签 PNG 的生成目录（进程内复用，构建时由 add_asset 读走）。"""
    global _LABEL_TMP
    if _LABEL_TMP is None:
        _LABEL_TMP = tempfile.mkdtemp(prefix="sb3labels_")
    return _LABEL_TMP


def _png_size_file(path):
    """读 PNG 的天然宽高（解析 IHDR，不依赖 Pillow）。失败返回兜底尺寸。"""
    try:
        with open(path, "rb") as f:
            head = f.read(33)
    except Exception:
        return 40, 48
    if len(head) >= 24 and head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
        w, h = struct.unpack(">II", head[16:24])
        return w, h
    return 40, 48


def _digit_natural_size(assets_dir, assets_src):
    """读数字图 d0.png 的天然尺寸，用于自动计算相邻数字的 gap。"""
    if assets_dir:
        p = os.path.join(assets_src or ".", assets_dir, "d0.png")
        w, h = _png_size_file(p)
        if w > 0:
            return w, h
    return 32, 46  # 兜底：约等于 make_digits 默认 cell_h=40 的产物


def _render_label_png(text, font_size=32, color="#ffffff", bold=True):
    """把一行文字渲染成透明 PNG，返回绝对路径（costume 可直接引用）。

    用于「用角色展示文字标签」，告诉玩家数字代表什么变量。
    """
    from PIL import Image, ImageDraw, ImageFont
    out_dir = _label_tmp_dir()
    digest = hashlib.md5(
        ("label|%s|%d|%s" % (text, font_size, color)).encode("utf-8")
    ).hexdigest()[:12]
    path = os.path.join(out_dir, "label_%s.png" % digest)
    if os.path.exists(path):
        return path
    font = None
    for fp, idx in _FONT_CANDIDATES:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size, index=idx)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()
    probe = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    pd = ImageDraw.Draw(probe)
    if _mu_text_size is not None:
        tw, th = _mu_text_size(pd, text, font)
    else:
        bb = pd.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = max(4, font_size // 8)
    w = int(tw + pad * 2)
    h = int(th + pad * 2)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    # 深底描边，提升在彩色背景上的可读性
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if dx * dx + dy * dy <= 4:
                dr.text((pad + dx, pad + dy), text, font=font,
                        fill=(18, 20, 36, 255))
    dr.text((pad, pad), text, font=font, fill=color)
    img.save(path)
    return path


def gen_id(n=16):
    return "".join(uuid.uuid4().hex[:n])


class Builder(object):
    _ctr = 0

    def __init__(self, spec, assets_src):
        self.spec = spec
        self.assets_src = assets_src
        self.extensions = set()
        self.broadcasts_used = {}   # 广播名字 -> id
        self.warnings = []
        # 会静默改变程序逻辑的问题：默认**阻止交付**（--lenient 可放宽）。
        # 这类问题过去只发 [警告] 却照样打印 "OK 生成"，导致作品能打开、
        # 四层校验全过，但行为与 IR 意图不符 —— 是「生成的代码逻辑不对」的主因。
        self.semantic_errors = []
        self.cloud_count = 0
        # 舞台上的全局变量/列表：所有精灵共用同一个 id（Scratch 的作用域规则）
        self.global_vars = {}
        self.global_lists = {}
        self._pending_comments = []   # [(block_id, 注释文本)]
        # 自定义积木参数 id 必须在整个工程内唯一：
        # Scratch 的参数在 sb3 中表现为「以 argumentid 为变量 id 的变量引用」，
        # 若不同过程都用 arg1/arg2，两个过程的第一个参数会共用同一个变量槽位。
        self._proc_seq = 0

    # ------------------------------------------------------------------ #
    # 基础工具
    # ------------------------------------------------------------------ #
    def _next_id(self):
        Builder._ctr += 1
        return "b%08d" % Builder._ctr

    def resolve_opcode(self, name):
        if name in self.spec["blocks"]:
            return name
        aliases = self.spec.get("aliases") or {}
        if name in aliases:
            return aliases[name]
        raise ValueError(
            "未知积木名 %r。请查 references/blocks.md 的友好名表，或 references/blocks-spec.json 的 blocks 键。"
            % name)

    def _input_aliases(self, opcode):
        return (self.spec.get("input_aliases") or {}).get(opcode) or {}

    def _alias_rev(self, opcode, block_spec):
        """spec 输入名 -> 友好别名列表（IR 里可用短键名）。

        同一个输入可能登记了多个别名（例如 VALUE -> value / by，
        MESSAGE -> text / message）。这里全部保留，取值时逐个尝试。
        """
        rev = {}
        for friendly, specname in self._input_aliases(opcode).items():
            rev.setdefault(specname, []).append(friendly)
        return rev

    # ------------------------------------------------------------------ #
    # 取值
    # ------------------------------------------------------------------ #
    # 通用兜底键：当积木只有一个非子栈输入时，IR 里写成 value / by / 数字
    # 都能对上（Scratch 里大量积木的输入名是 DX / DY / VALUE 这类内部名，
    # 但用户/模型习惯写 value）。
    UNIVERSAL_KEYS = ("value", "by", "val")

    def _get_raw(self, value, input_name, opcode, block_spec, allow_universal=True):
        rev = self._alias_rev(opcode, block_spec)
        if isinstance(value, dict):
            keys = [input_name, input_name.lower()] + list(rev.get(input_name) or [])
            for key in keys:
                if key and key in value:
                    return value[key]
            # 兜底：只有一个非子栈输入时，value/by 都能对上。
            # ⚠️ 字段（varfield/listfield/broadcast）不能走这条兜底 ——
            #    否则 {var: 分数, by: 1} 里的变量名会被错填成 by 的值。
            order = [k for k, v in block_spec["inputs"].items()
                     if v["type"] not in ("substack", "substack2")]
            if allow_universal and len(order) == 1:
                for uk in self.UNIVERSAL_KEYS:
                    if uk in value:
                        self.warnings.append(
                            "积木 %s 的输入 %s 没有别名 %r，已用通用键 %r 代填"
                            % (opcode, input_name, uk, uk))
                        return value[uk]
            return None
        if isinstance(value, list):
            order = [k for k, v in block_spec["inputs"].items()
                     if v["type"] not in ("substack", "substack2")]
            # ⚠️ 列表形式按输入槽顺序取值，**超出槽位的项会被静默丢弃**。
            #    例如 {add: [a, b, c]} 编译成「a+b」，c 直接消失 —— 不报错但结果不对。
            if len(value) > len(order):
                self.semantic_errors.append(
                    "积木 %s 只有 %d 个输入槽，列表却给了 %d 项；"
                    "多出的 %r 会被丢弃，结果必然算错。"
                    "请嵌套成两层两输入积木，例如 {add: [a, {add: [b, c]}]}"
                    % (opcode, len(order), len(value), value[len(order):]))
            try:
                idx = order.index(input_name)
                return value[idx] if idx < len(value) else None
            except ValueError:
                return None
        order = [k for k, v in block_spec["inputs"].items()
                 if v["type"] not in ("substack", "substack2")]
        if len(order) == 1:
            return value
        return None

    def _field_name(self, value, fname, opcode, block_spec):
        fv = self._get_raw(value, fname, opcode, block_spec, allow_universal=False)
        if fv is None and isinstance(value, str):
            return value
        return fv

    def _var_field_name(self, value, fname, opcode, block_spec, kind):
        """取变量/列表字段的名字。

        支持几种写法：
            {VARIABLE: "分数"}   {variable: "分数"}   {var: "分数"}
            {LIST: "排行榜"}      {list: "排行榜"}
            {var: {var: "分数"}}  （嵌套写法也兼容）
        """
        raw = self._field_name(value, fname, opcode, block_spec)
        if raw is None and isinstance(value, dict):
            keys = ("var", "variable", "name") if kind == "varfield" else ("list", "name")
            for k in keys:
                if k in value:
                    raw = value[k]
                    break
        if isinstance(raw, dict):
            if kind == "varfield":
                raw = self._var_name(raw)
            else:
                raw = self._list_name(raw)
        return raw

    # ------------------------------------------------------------------ #
    # 输入编码
    # ------------------------------------------------------------------ #
    def encode_literal(self, itype, raw):
        if itype in ("number", "angle"):
            return [1, [PRIM[itype], str(raw)]]
        if itype == "color":
            # Scratch 的颜色字面量必须是 #rrggbb 六位十六进制（不带 alpha）。
            # 写成 8 位（#rrggbbaa）会让官方 schema 校验直接失败。
            c = str(raw).strip().lstrip("#")
            if len(c) == 8:
                c = c[:6]
            if len(c) == 3:
                c = "".join(ch * 2 for ch in c)
            if not re.fullmatch(r"[0-9a-fA-F]{6}", c):
                raise ValueError(
                    "颜色 %r 不是合法的 #rrggbb 形式（Scratch 的颜色不能带 alpha 通道）"
                    % (raw,))
            return [1, [PRIM["color"], "#" + c.lower()]]
        if itype == "text":
            return [1, [PRIM["text"], str(raw)]]
        if itype == "any" or itype == "value":
            if isinstance(raw, bool):
                return [1, [PRIM["number"], "1" if raw else "0"]]
            if isinstance(raw, (int, float)):
                return [1, [PRIM["number"], str(raw)]]
            return [1, [PRIM["text"], str(raw)]]
        if itype == "broadcast":
            name = str(raw)
            self.broadcasts_used.setdefault(name, name)
            return [1, [PRIM["broadcast"], name, name]]
        if itype == "variable":
            return self._var_ref(raw)
        if itype == "list":
            return self._list_ref(raw)
        if itype == "menu":
            # 动态下拉菜单：sb3 里存成裸字符串
            return [1, str(raw)]
        return [1, [PRIM["text"], str(raw)]]

    def _var_name(self, raw):
        if isinstance(raw, dict):
            if "var" in raw:
                return str(raw["var"])
            if "name" in raw:
                return str(raw["name"])
        return str(raw)

    def _list_name(self, raw):
        if isinstance(raw, dict):
            if "list" in raw:
                return str(raw["list"])
            if "name" in raw:
                return str(raw["name"])
        return str(raw)

    def _var_ref(self, raw, tctx=None):
        name = self._var_name(raw)
        tctx = tctx or self._tmp
        vid = self._resolve_var_id(name, tctx)
        return [3, [PRIM["variable"], name, vid]]

    @staticmethod
    def _looks_like_number(s):
        try:
            float(s)
            return True
        except (TypeError, ValueError):
            return False

    def _list_ref(self, raw, tctx=None):
        name = self._list_name(raw)
        tctx = tctx or self._tmp
        lid = self._resolve_list_id(name, tctx)
        return [3, [PRIM["list"], name, lid]]

    def _resolve_var_id(self, name, tctx):
        """变量 id 解析：优先本 target 声明的，其次舞台全局的，都没有则就地建为局部变量。"""
        if name in tctx.var_ids:
            return tctx.var_ids[name]
        if name in self.global_vars:
            return self.global_vars[name]
        vid = gen_id()
        tctx.var_ids[name] = vid
        tctx.var_initials.setdefault(name, 0)
        tctx.var_cloud.setdefault(name, False)
        self.warnings.append(
            "变量 %r 未在任何 target 声明，已在 %s 上自动创建为局部变量"
            "（若希望所有角色共用，请在 stage.variables 中声明）" % (name, tctx.label))
        return vid

    def _resolve_list_id(self, name, tctx):
        """列表 id 解析，规则同变量。"""
        if name in tctx.list_ids:
            return tctx.list_ids[name]
        if name in self.global_lists:
            return self.global_lists[name]
        lid = gen_id()
        tctx.list_ids[name] = lid
        self.warnings.append(
            "列表 %r 未在任何 target 声明，已在 %s 上自动创建为局部列表"
            "（若希望所有角色共用，请在 stage.lists 中声明）" % (name, tctx.label))
        return lid

    def build_expr(self, raw, tctx, parent_id=None):
        """把 reporter/boolean 表达式编译成积木，返回 block id。"""
        if not isinstance(raw, dict):
            raise ValueError("无法把 %r 当作表达式编译" % (raw,))
        if "var" in raw:
            # 变量读取器：sb3 里变量名放在 fields.VARIABLE
            name = str(raw["var"])
            # ⚠️ 自定义积木的参数**不是变量**：scratch-vm 通过线程参数栈传参，
            # 只有 argument_reporter_*（按参数名读取）才拿得到值。
            # 若这里发成 data_variable，参数会永远是初值（0/""）。
            arg_type = (tctx.arg_types or {}).get(name)
            if arg_type is not None:
                opcode = ("argument_reporter_boolean" if arg_type == "boolean"
                          else "argument_reporter_string_number")
                return self.make_block(opcode, {"VALUE": name}, tctx,
                                       x=0, y=0, parent_id=parent_id)
            self._resolve_var_id(name, tctx)
            return self.make_block("data_variable", {"VARIABLE": name}, tctx,
                                   x=0, y=0, parent_id=parent_id)
        if "list" in raw:
            name = str(raw["list"])
            self._resolve_list_id(name, tctx)
            return self.make_block("data_listcontents", {"LIST": name}, tctx,
                                   x=0, y=0, parent_id=parent_id)
        if len(raw) == 1:
            (fname, val), = raw.items()
        else:
            fname, val = self._split_block(raw)

        # --- 逻辑运算归一化（and/or N 元自动嵌套；not 支持裸表达式） ---
        # 开发实战坑：and/or 在 Scratch 里只有 2 个输入槽，写 3+ 个条件必须
        # 手写嵌套，否则 _get_raw 会报「超出槽位」并静默丢弃多出的项，结果算错。
        # 这里在编译期把 N 元列表自动两两嵌套，用户可以直接写
        #   and: [a, b, c, d]  →  and(and(a,b), and(c,d))
        # 不再需要手搓嵌套。
        if fname in ("and", "or") and isinstance(val, list) and len(val) > 2:
            reduced = val[0]
            for nxt in val[1:]:
                reduced = {fname: [reduced, nxt]}
            return self.build_expr(reduced, tctx, parent_id)
        # not 只有 1 个 operand 输入；用户常顺手写 {not: {equals: ...}} 直接失败。
        # 这里把裸表达式（非 {operand:..} 包裹的 dict/list）自动包成
        #   {not: {operand: <expr>}}，避免又一处「不报错但失效」的坑。
        if (fname == "not" and isinstance(val, (dict, list))
                and not (isinstance(val, dict) and "operand" in val)):
            return self.build_expr({"not": {"operand": val}}, tctx, parent_id)

        op = self.resolve_opcode(fname)
        return self.make_block(op, val, tctx, x=0, y=0, parent_id=parent_id)

    # ------------------------------------------------------------------ #
    # 未知键检查（防止静默失效）
    # ------------------------------------------------------------------ #
    def _warn_unknown_keys(self, opcode, spec, value):
        """积木的字典里出现无法识别的键时给出警告。

        这类错误最危险的地方在于「不报错但也不生效」：
        积木照常生成，只是那个值被丢掉了，运行起来完全不像写的那么回事。
        例如 `{change_x: {value: 10}}` —— change_x 的输入名其实是 DX，
        `value` 不是它的别名，于是 DX 被填成 0，角色**一动不动**。
        """
        if not isinstance(value, dict):
            return
        accepted = set()
        rev = self._alias_rev(opcode, spec)
        for iname in spec.get("inputs", {}):
            accepted.add(iname)
            accepted.add(iname.lower())
            accepted.update(rev.get(iname) or [])
        for fname, fdef in spec.get("fields", {}).items():
            accepted.add(fname)
            accepted.add(fname.lower())
            accepted.update(rev.get(fname) or [])
            # 变量/列表字段用 var/variable/name、list/name 取名
            if fdef.get("type") == "varfield":
                accepted.update({"var", "variable", "name"})
            elif fdef.get("type") == "listfield":
                accepted.update({"list", "name"})
        # 子栈与常见约定键
        accepted.update({"do", "else", "cond", "condition", "comment"})
        # {var: 变量名} 作为数值输入的便捷写法（见 make_block 里的处理）
        has_varfield = any(f.get("type") == "varfield"
                           for f in spec.get("fields", {}).values())
        if not has_varfield:
            accepted.add("var")
        # 只有一个非子栈输入时，通用键也能对上（见 _get_raw 的兜底）
        order = [k for k, v in spec.get("inputs", {}).items()
                 if v["type"] not in ("substack", "substack2")]
        if len(order) == 1:
            accepted.update(self.UNIVERSAL_KEYS)
        unknown = [k for k in value.keys() if k not in accepted]
        if unknown:
            self.semantic_errors.append(
                "积木 %s 里的键 %s 无法识别，值不会生效（分支/参数会被整个丢掉）。"
                " 常见误写：if_else 的分支键应是 do/else，不是 then；"
                " 请查 references/blocks-spec.json 的 inputs/fields"
                % (opcode, "、".join(repr(k) for k in unknown)))

    # ------------------------------------------------------------------ #
    # 积木构建
    # ------------------------------------------------------------------ #
    def make_block(self, opcode, value, tctx, x=0, y=0, parent_id=None):
        # ⚠️ control_if 只有 SUBSTACK 一个子栈槽位，写了 else 会被**静默丢弃**。
        #    这里自动升级成 control_if_else（SUBSTACK + SUBSTACK2），并给出提示。
        if (opcode == "control_if" and isinstance(value, dict)
                and value.get("else") is not None):
            self.warnings.append(
                "积木 if 带了 else 分支，已自动升级为 if/else（control_if 无 else 槽位）")
            opcode = "control_if_else"
        if opcode == "procedures_call":
            return self._make_call(value, tctx, x, y, parent_id)
        if opcode in ("procedures_definition", "procedures_prototype"):
            raise ValueError(
                "自定义积木请用 target.procedures 声明，不要直接写 %s" % opcode)

        spec = self.spec["blocks"][opcode]
        if spec.get("extension"):
            self.extensions.add(spec["extension"])
        self._warn_unknown_keys(opcode, spec, value)
        bid = self._next_id()
        block = {
            "opcode": opcode,
            "next": None,
            "parent": parent_id,
            "inputs": {},
            "fields": {},
            "topLevel": parent_id is None,
            "x": x,
            "y": y,
        }

        # --- 子栈 ---
        for iname, idef in spec["inputs"].items():
            if idef["type"] not in ("substack", "substack2"):
                continue
            # SUBSTACK -> do:；SUBSTACK2 -> else:
            key = "else" if iname.upper().endswith("2") else "do"
            sub_items = None
            if isinstance(value, dict):
                sub_items = value.get(key)
                if sub_items is None:
                    sub_items = value.get(iname.lower())
                if sub_items is None:
                    sub_items = value.get(key + "_")
            if sub_items:
                first = self._chain(sub_items, tctx, x=x + 30, y=y + 40, parent_id=bid)
                block["inputs"][iname] = [2, first]
            else:
                # 空子栈与「非空 = [2, firstBlockId]」对齐，写成 [2, null]
                block["inputs"][iname] = [2, None]

        # --- 普通输入 ---
        for iname, idef in spec["inputs"].items():
            if idef["type"] in ("substack", "substack2"):
                continue
            itype = idef["type"]
            raw = self._get_raw(value, iname, opcode, spec)

            if itype == "menu":
                # 动态下拉菜单：默认指向一个「影子积木」（shadow block）。
                # 直接写裸字符串的话，运行时反序列化会把它当成块 id 去查找，
                # 找不到就是 null，脚本一执行就崩。
                if raw is None and isinstance(value, str):
                    raw = value
                menu_ref = (spec.get("menu_inputs") or {}).get(iname)
                # 关键：如果给的是一个**表达式**（字典），就把真实积木放进槽位，
                # 而不是菜单影子。这样「换成 X 造型」就能用计算值动态切换。
                # 运行时 scratch3_looks._setCostume 同时支持
                #   · 字符串 → 按造型名匹配
                #   · 数字   → 按造型序号（1 起）
                # 所以「用角色显示变量」的实现方式就是：
                #   造 0..9 十套造型 → 用 (值 mod 10) 之类的计算值切造型。
                if isinstance(raw, dict):
                    child = self.build_expr(raw, tctx, parent_id=bid)
                    block["inputs"][iname] = [2, child]
                elif menu_ref:
                    shadow_id = self._make_menu_shadow(menu_ref, iname, raw, tctx)
                    block["inputs"][iname] = [1, shadow_id]
                else:
                    # 没有对应影子积木时，退化成文本影子（运行时按字符串处理）
                    if raw in (None, ""):
                        self.warnings.append(
                            "积木 %s 的 %s 下拉菜单没有指定值，已填空串（该判断恒为假）"
                            % (opcode, iname))
                    block["inputs"][iname] = self.encode_literal("text", raw if raw is not None else "")
                continue

            if itype in ("boolean", "number_reporter"):
                if raw is None and isinstance(value, dict):
                    for alt in ("cond", "condition"):
                        if alt in value:
                            raw = value[alt]
                            break
                if isinstance(raw, dict):
                    child = self.build_expr(raw, tctx, parent_id=bid)
                    block["inputs"][iname] = [2, child]
                elif raw is None:
                    block["inputs"][iname] = None
                else:
                    block["inputs"][iname] = self.encode_literal("any", raw)
                continue

            if itype == "variable":
                if raw is None and isinstance(value, str):
                    raw = value
                block["inputs"][iname] = self._var_ref(raw, tctx)
                continue

            if itype == "list":
                block["inputs"][iname] = self._list_ref(raw, tctx)
                continue

            if itype == "broadcast":
                if raw is None and isinstance(value, str):
                    raw = value
                block["inputs"][iname] = self.encode_literal("broadcast", raw)
                continue

            # 便捷写法：{move_steps: {var: 力度}} —— 把变量的值塞进数值输入。
            # 这个积木本身没有变量字段，所以 "var" 不会被当成字段名。
            if raw is None and isinstance(value, dict) and "var" in value:
                raw = {"var": value["var"]}

            # 字面量
            if raw is None:
                raw = 0 if itype in ("number", "angle") else ""
            if isinstance(raw, dict):
                child = self.build_expr(raw, tctx, parent_id=bid)
                block["inputs"][iname] = [2, child]
            elif (isinstance(raw, str) and itype in ("number", "number_reporter", "angle")
                  and not self._looks_like_number(raw)
                  and (raw in tctx.var_ids or raw in self.global_vars
                       or raw in getattr(tctx, "arg_names", {}))):
                # 数值/算术输入里出现「裸变量名字符串」（如 "r1"）时，当成变量引用。
                # 否则会被当成字面量字符串 "r1" 写进积木，运行时读不到变量值
                # （表现为 item_of_list / 运算 拿到空值）。详见 match3.idx 的坑。
                block["inputs"][iname] = self._var_ref(raw, tctx)
            else:
                block["inputs"][iname] = self.encode_literal(itype, raw)

        # --- 字段 ---
        for fname, fdef in spec.get("fields", {}).items():
            ftype = fdef.get("type")
            if ftype == "varfield":
                name = self._var_field_name(value, fname, opcode, spec, "varfield")
                if name is None:
                    raise ValueError(
                        "积木 %s 的 %s 字段必须指明是哪个变量"
                        "（写成 {var: 名字} 或 {variable: 名字}）。" % (opcode, fname))
                vid = self._resolve_var_id(str(name), tctx)
                block["fields"][fname] = [str(name), vid]
            elif ftype == "listfield":
                name = self._var_field_name(value, fname, opcode, spec, "listfield")
                if name is None:
                    raise ValueError(
                        "积木 %s 的 %s 字段必须指明是哪个列表"
                        "（写成 {list: 名字}）。" % (opcode, fname))
                lid = self._resolve_list_id(str(name), tctx)
                block["fields"][fname] = [str(name), lid]
            elif ftype == "broadcast":
                fv = self._field_name(value, fname, opcode, spec)
                if fv is None:
                    raise ValueError(
                        "积木 %s 的 %s 字段必须指明是哪个广播消息"
                        "（写成 {message: 消息名}）。" % (opcode, fname))
                name = str(fv)
                self.broadcasts_used.setdefault(name, name)
                # 广播字段写作 [消息名, 消息id]
                block["fields"][fname] = [name, self.broadcasts_used[name]]
            elif ftype == "argument":
                # 自定义积木参数：官方 sb3 写作 ["参数名"]（单元素）
                fv = self._field_name(value, fname, opcode, spec)
                if fv is None:
                    raise ValueError(
                        "积木 %s 的 %s 字段必须指明是哪个参数"
                        "（写成 {VALUE: 参数名}）。" % (opcode, fname))
                block["fields"][fname] = [str(fv)]
            else:
                # 静态下拉菜单：fields 里存 [值, null]
                fv = self._field_name(value, fname, opcode, spec)
                if fv is None:
                    opts = fdef.get("options") or []
                    if opts:
                        fv = opts[0][1]
                if fv is not None:
                    block["fields"][fname] = [str(fv), None]

        self.blocks[bid] = block
        # 内联注释：积木值里的 comment 键（留给 target 构建阶段统一处理）
        if isinstance(value, dict):
            ctext = value.get("comment")
            if isinstance(ctext, str) and ctext.strip():
                self._pending_comments.append((bid, ctext.strip()))
        return bid

    # ------------------------------------------------------------------ #
    # 整理积木（Clean Up Blocks）
    # ------------------------------------------------------------------ #
    def _script_extent(self, top_id):
        """估算一个脚本的画布占用高度（px）。

        Scratch 里只有**顶层积木**带 x/y（见 scratch-vm serializeBlock：
        只有 block.topLevel 才写 x/y），其余积木由编辑器按积木树自己排。
        所以「整理积木」只需要给顶层脚本排位置。
        """
        spec_of = self.spec["blocks"]
        h = 0
        cur = top_id
        while cur and cur in self.blocks:
            b = self.blocks[cur]
            h += 76
            op = b.get("opcode")
            inputs = (spec_of.get(op) or {}).get("inputs") or {}
            for iname, idef in inputs.items():
                if idef.get("type") != "substack":
                    continue
                sub = (b.get("inputs") or {}).get(iname)
                if isinstance(sub, list) and len(sub) > 1 and isinstance(sub[1], str):
                    h += self._script_extent(sub[1]) - 76 + 24
            cur = b.get("next")
        return max(h, 76)

    def _tidy_scripts(self, tops, layout=None):
        """把顶层脚本按网格排开，避免在 Scratch 里全部叠在左上角。

        layout 可选：
            {mode: "tidy", start_x: 40, start_y: 40, col_width: 300, col_height: 600}
            {mode: "manual"}   -> 保持 IR 里给的位置
        """
        layout = layout or {}
        if layout.get("mode") == "manual":
            return
        start_x = layout.get("start_x", 40)
        start_y = layout.get("start_y", 40)
        col_width = layout.get("col_width", 300)
        col_height = layout.get("col_height", 620)

        col = 0
        y = start_y
        used = 0
        for top in tops:
            h = self._script_extent(top)
            if used > 0 and used + h > col_height:
                col += 1
                y = start_y
                used = 0
            b = self.blocks[top]
            b["x"] = start_x + col * col_width
            b["y"] = y
            b["topLevel"] = True
            y += h + 24
            used += h + 24

    # ------------------------------------------------------------------ #
    # 下拉菜单影子积木
    # ------------------------------------------------------------------ #
    def _make_menu_shadow(self, menu_opcode, field_name, value, tctx):
        """创建一个下拉菜单的影子积木，返回它的 id。

        sb3 里的下拉菜单是一个独立的 shadow block：
            "<id>": {"opcode": "motion_goto_menu",
                     "fields": {"TO": ["_mouse_", null]},
                     "shadow": true, "topLevel": false, ...}
        父积木的输入再引用这个 id：  "TO": [1, "<id>"]

        注意 topLevel 必须是 **false**：
        scratch-vm 的 Blocks.createBlock 会把 topLevel=true 的积木加进 _scripts，
        而编辑器的 toXML() 正是遍历 _scripts 生成画布的 —— 于是这个影子积木会
        变成一个孤零零悬在左上角的小下拉框。影子积木是父积木的输入，不是独立脚本。
        """
        bid = self._next_id()
        self.blocks[bid] = {
            "opcode": menu_opcode,
            "next": None, "parent": None,
            "inputs": {},
            "fields": {field_name: [str(value if value is not None else ""), None]},
            "shadow": True,
            "topLevel": False,
        }
        return bid

    # ------------------------------------------------------------------ #
    # 过程调用
    # ------------------------------------------------------------------ #
    def _make_call(self, value, tctx, x, y, parent_id):
        proc = value.get("proc") if isinstance(value, dict) else str(value)
        args = value.get("args", []) if isinstance(value, dict) else []
        reg = tctx.procs.get(proc)
        if reg is None:
            raise ValueError("调用了未定义的过程 %r（请先在 target.procedures 中定义）" % proc)
        ids = reg["ids"]
        bid = self._next_id()
        inputs = {}
        for i, a in enumerate(args):
            key = ids[i] if i < len(ids) else "arg%d" % (i + 1)
            if isinstance(a, dict):
                child = self.build_expr(a, tctx, parent_id=bid)
                inputs[key] = [2, child]
            else:
                inputs[key] = self.encode_literal("any", a)
        block = {
            "opcode": "procedures_call",
            "next": None, "parent": parent_id,
            "inputs": inputs,
            "fields": {"PROCEDURE_DEFINITION": reg["mutation"]},
            "mutation": reg["mutation"],
            "topLevel": parent_id is None,
            "x": x, "y": y,
        }
        self.blocks[bid] = block
        return bid

    # ------------------------------------------------------------------ #
    # 过程定义
    # ------------------------------------------------------------------ #
    def _build_procedure(self, pdef, tctx, x, y):
        name = pdef["name"]
        raw_args = pdef.get("args") or []
        # 参数可以是 "名字" 或 {"name": "名字", "type": "boolean"}
        arg_names, arg_kinds = [], []
        for a in raw_args:
            if isinstance(a, dict):
                arg_names.append(str(a.get("name", "")))
                arg_kinds.append("boolean" if a.get("type") == "boolean" else "number")
            else:
                arg_names.append(str(a))
                arg_kinds.append("number")
        args = raw_args
        # 参数 id 全局唯一：不同过程不能共用 arg1/arg2，否则参数会串味
        self._proc_seq += 1
        ids = ["arg%d_%d" % (self._proc_seq, i + 1) for i in range(len(args))]
        names = arg_names
        defaults = [str(d) for d in (pdef.get("defaults") or [])]
        while len(defaults) < len(names):
            defaults.append("")
        warp = "true" if pdef.get("warp") else "false"
        mutation = {
            "tagName": "mutation",
            "proccode": name,
            "argumentids": json.dumps(ids),
            "argumentnames": json.dumps(names),
            "argumentdefaults": json.dumps(defaults),
            "warp": warp,
            "children": [],
        }
        # 过程参数在 sb3 中**不是变量**，而是原型 mutation 里的 argumentids；
        # 过程体里用 argument_reporter_*（按参数名）读取。
        # 这里登记成 tctx.arg_names，供 build_expr 区分「参数」与「普通变量」。
        for i, nm in enumerate(names):
            tctx.arg_names[nm] = ids[i]
            tctx.arg_types[nm] = arg_kinds[i]
        # 先登记过程，再拼接过程体：支持过程内的递归调用与前向引用
        tctx.procs[name] = {"ids": ids, "mutation": mutation}
        def_id = self._next_id()
        proto_id = self._next_id()
        def_block = {
            "opcode": "procedures_definition",
            "next": None, "parent": None,
            "inputs": {"custom_block": [1, proto_id]},
            "fields": {}, "topLevel": True,
            "x": x, "y": y,
        }
        proto_block = {
            "opcode": "procedures_prototype",
            "next": None, "parent": def_id,
            "inputs": {}, "fields": {"PROCEDURE_DEFINITION": mutation},
            "mutation": mutation,
            "topLevel": False, "x": x, "y": y,
        }
        self.blocks[def_id] = def_block
        self.blocks[proto_id] = proto_block
        first = self._chain(pdef.get("script") or [], tctx, x, y + 80, parent_id=def_id)
        def_block["next"] = first

    # ------------------------------------------------------------------ #
    # 链式堆叠
    # ------------------------------------------------------------------ #
    def _chain(self, items, tctx, x=0, y=0, parent_id=None):
        prev = None
        first = None
        cy = y
        for blk in items:
            fname, val = self._split_block(blk)
            op = self.resolve_opcode(fname)
            bid = self.make_block(op, val, tctx, x=x, y=cy,
                                  parent_id=(parent_id if prev is None else prev))
            if first is None:
                first = bid
            if prev is not None:
                self.blocks[prev]["next"] = bid
            prev = bid
            cy += 80
        return first

    def _split_block(self, blk):
        """把一个积木写法拆成 (积木名, 值)。

        支持多种写法：
            {move_steps: 10}                 单键
            {forever: null, do: [...]}       多键：第一个键是积木名，其余并入值
            {if: null, cond: ..., do: ...}   同上（YAML 块状写法最自然）
        """
        if not isinstance(blk, dict) or not blk:
            raise ValueError("积木必须写成 {积木名: 值}：%r" % (blk,))
        keys = list(blk.keys())
        name = keys[0]
        if len(keys) == 1:
            return name, blk[name]
        return name, self._merge_block_value(name, blk[name], {k: blk[k] for k in keys[1:]})

    def _merge_block_value(self, opcode, base, extra):
        """把多键写法里「积木名之外的键」并进积木的值。

        base 是字典 -> 直接合并；
        base 是标量（例如 when_receive: 出发）-> 把标量放进该积木唯一的那个输入，
        再并入其余键（这样 {when_receive: 出发, comment: "..."} 不会把消息名丢掉）。

        ⚠️ 两个必须注意的坑（这里都做了处理）：
        1) **友好名要解析成规范 opcode**：blocks 表的键是 control_repeat / control_wait，
           而 IR 里写的是 repeat / wait。不解析就会查不到规格，
           标量被丢掉 -> 例如 `- repeat: 16` + `do:` 会编译成「重复 0 次」（静默失效）。
        2) **选输入槽时必须跳过 SUBSTACK**：带子栈的积木第一个输入往往不是值输入，
           写错了值会被子栈覆盖。
        """
        if isinstance(base, dict):
            merged = dict(base)
            merged.update(extra)
            return merged
        merged = {}
        if base is not None:
            spec_name = opcode
            if spec_name not in (self.spec.get("blocks") or {}):
                spec_name = (self.spec.get("aliases") or {}).get(opcode, opcode)
            spec = (self.spec.get("blocks") or {}).get(spec_name) or {}
            inputs = spec.get("inputs") or {}
            # 子栈输入（SUBSTACK）不是「值」输入，不能拿来放标量
            slots = [k for k, v in inputs.items()
                     if (v or {}).get("type") not in ("substack", "substack2")]
            if slots:
                merged[slots[0]] = base
                if len(slots) > 1:
                    self.warnings.append(
                        "积木 %s 有多个输入，标量值 %r 已放进第一个输入 %s，请确认是否正确"
                        % (opcode, base, slots[0]))
            else:
                merged = {}
        merged.update(extra)
        return merged

    # ------------------------------------------------------------------ #
    # 资产
    # ------------------------------------------------------------------ #
    def _read_file(self, rel):
        p = rel if os.path.isabs(rel) else os.path.join(self.assets_src or ".", rel)
        with open(p, "rb") as f:
            return f.read()

    def add_asset(self, rel, assets_dir):
        data = self._read_file(rel)
        ext = os.path.splitext(rel)[1].lstrip(".").lower()
        md5 = hashlib.md5(data).hexdigest()
        md5ext = "%s.%s" % (md5, ext)
        with open(os.path.join(assets_dir, md5ext), "wb") as f:
            f.write(data)
        return md5, md5ext, ext, data

    def costume_entry(self, c, assets_dir):
        md5, md5ext, ext, data = self.add_asset(c["asset"], assets_dir)
        name = c.get("name", os.path.splitext(os.path.basename(c["asset"]))[0])
        if ext == "svg":
            w, h = self._svg_size(data)
            return {
                "assetId": md5, "name": name, "md5ext": md5ext, "dataFormat": "svg",
                "rotationCenterX": w // 2, "rotationCenterY": h // 2,
            }
        w, h = self._png_size(data) if ext == "png" else (480, 360)
        return {
            "assetId": md5, "name": name, "md5ext": md5ext, "dataFormat": ext,
            "bitmapResolution": 1, "rotationCenterX": w // 2, "rotationCenterY": h // 2,
        }

    def sound_entry(self, s, assets_dir):
        md5, md5ext, ext, data = self.add_asset(s["asset"], assets_dir)
        name = s.get("name", os.path.splitext(os.path.basename(s["asset"]))[0])
        rate, sample_count = 44100, 0
        if ext == "wav":
            try:
                with wave.open(os.path.join(self.assets_src, s["asset"]), "rb") as wf:
                    rate = wf.getframerate()
                    sample_count = wf.getnframes()
            except Exception:
                pass
        return {
            "assetId": md5, "name": name, "dataFormat": ext,
            "format": "", "rate": rate, "sampleCount": sample_count, "md5ext": md5ext,
        }

    @staticmethod
    def _svg_size(data):
        txt = data.decode("utf-8", "ignore")
        m = re.search(r'viewBox\s*=\s*["\']\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)', txt)
        if m:
            return int(float(m.group(1))), int(float(m.group(2)))
        m = re.search(r'width\s*=\s*["\']?([\d.]+)', txt)
        mh = re.search(r'height\s*=\s*["\']?([\d.]+)', txt)
        if m and mh:
            return int(float(m.group(1))), int(float(m.group(1)))
        return 480, 360

    @staticmethod
    def _png_size(data):
        try:
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", data[16:24])
                return w, h
        except Exception:
            pass
        return 480, 360

    # ------------------------------------------------------------------ #
    # 变量 / 列表（含云变量）
    # ------------------------------------------------------------------ #
    @staticmethod
    def _var_decl(raw):
        """返回 (初始值, is_cloud)。支持三种写法：
             名字: 0                       普通变量
             名字: {value: 0}             普通变量
             名字: {value: 0, cloud: true} 云变量
        """
        if isinstance(raw, dict):
            val = raw.get("value", raw.get("initial", 0))
            cloud = bool(raw.get("cloud") or raw.get("isCloud"))
            return val, cloud
        return raw, False

    # ------------------------------------------------------------------ #
    # 变量监视器（屏幕上的读数）
    # ------------------------------------------------------------------ #
    @staticmethod
    def _find_var_id(target, name):
        for vid, entry in (target.get("variables") or {}).items():
            if isinstance(entry, list) and entry and entry[0] == name:
                return vid
        return None

    @staticmethod
    def _find_list_id(target, name):
        for lid, entry in (target.get("lists") or {}).items():
            if isinstance(entry, list) and entry and entry[0] == name:
                return lid
        return None

    def _make_monitor(self, m, stage_target):
        """生成一个监视器（Scratch 里的「变量显示」）。

        sb3 的 monitors 数组里每一项形如：
            {"id": "<变量id>", "mode": "default", "opcode": "data_variable",
             "params": {"VARIABLE": "分数"}, "spriteName": null,
             "value": 0, "width": 0, "height": 0, "x": 5, "y": 5, "visible": true,
             "sliderMin": 0, "sliderMax": 100, "isDiscrete": true}
        列表监视器用 mode "list" + opcode "data_listcontents"，且不带 slider 三个字段。
        """
        if not isinstance(m, dict):
            return None
        is_list = "list" in m
        name = str(m.get("list") if is_list else m.get("var"))
        if is_list:
            mid = self._find_list_id(stage_target, name)
            opcode, params, mode = "data_listcontents", {"LIST": name}, "list"
            value = []
        else:
            mid = self._find_var_id(stage_target, name)
            opcode, params, mode = "data_variable", {"VARIABLE": name}, "default"
            value = 0
        if mid is None:
            self.warnings.append(
                "监视器引用了不存在的%s %r，已跳过（请在 stage.variables / stage.lists 中声明）"
                % ("列表" if is_list else "变量", name))
            return None
        mon = {
            "id": mid,
            "mode": m.get("mode", mode),
            "opcode": opcode,
            "params": params,
            "spriteName": m.get("sprite"),   # null = 全局（舞台上的变量）
            "value": value,
            "width": 0, "height": 0,
            "x": m.get("x", 5), "y": m.get("y", 5),
            "visible": m.get("visible", True),
        }
        if mode != "list":
            mon["sliderMin"] = 0
            mon["sliderMax"] = 100
            mon["isDiscrete"] = True
        return mon

    # ------------------------------------------------------------------ #
    # 用角色显示变量（数字精灵）
    # ------------------------------------------------------------------ #
    def _build_digit_display(self, tdef, costume_src, tmpdir, costumes):
        """为「数字精灵」角色补齐 0~9 造型。

        Scratch 3.0 的变量默认显示成舞台角落的监视器（monitor），
        很多游戏希望分数/时间显示成角色的一部分。这里用一个小技巧：

          角色准备 0~9 共 10 套造型（图片就是数字 0~9）
          脚本里不断「换成 (计算值) 造型」

        运行时 scratch3_looks._setCostume 对**数字**按造型序号处理（1 起算），
        对**字符串**按造型名匹配。数字精灵的造型就叫 "0".."9"，
        所以传 (值 mod 10) + 1 即可命中第 (值 mod 10) + 1 套造型。

        list_display（列表显示）走同一条路：把「第几项」或「列表长度」
        的个位显示出来。
        """
        cfg = tdef.get("digit_display") or {}
        var = cfg.get("variable")
        if not var:
            raise ValueError(
                "角色 %r 的 digit_display 必须写明 variable（要显示哪个变量）"
                % tdef.get("name"))
        digit_dir = (cfg.get("assets") or "assets/ui").rstrip("/")
        new_costumes = []
        for i in range(10):
            rel = "%s/d%d.png" % (digit_dir, i)
            new_costumes.append(self.costume_entry(
                {"name": str(i), "asset": rel}, tmpdir))
        # digit_display 只负责补齐数字造型，调用方自己的造型排在后面
        return new_costumes + costumes

    # ------------------------------------------------------------------ #
    # 聊天框角色
    # ------------------------------------------------------------------ #
    def _build_chat_box(self, tdef, tmpdir, costumes):
        """为「聊天框」角色补齐台词造型。

        Scratch 内置的「说/想」气泡是画在角色头顶的固定造型，
        没法排版中文、没法换背景、在正式作品里很违和。
        自制聊天框的做法：

          · 角色准备 N+1 套造型：第 0 套是空白底板，1..N 是各句台词
            （台词图片由 scripts/make_ui_assets.py chatlines 预渲染）
          · 脚本用「换成 (计算值) 造型」按台词序号切换
            —— 运行时 _setCostume 对数字按序号处理（1 起算）

        这样聊天框就是一个普通角色：可以移动、缩放、盖在画面上层，
        台词图片也由我们自己排版，中文完全可控。
        """
        cfg = tdef.get("chat_box") or {}
        lines_dir = (cfg.get("assets") or "assets/ui/chat").rstrip("/")
        count = int(cfg.get("lines", 0))
        if count <= 0:
            raise ValueError(
                "角色 %r 的 chat_box 必须写明 lines（共有几句台词）"
                % tdef.get("name"))
        new_costumes = []
        # 造型 0 = 空底板；1..N = 各句台词
        blank = cfg.get("blank") or ("%s/chat_blank.png" % lines_dir)
        new_costumes.append(self.costume_entry(
            {"name": "空白", "asset": blank}, tmpdir))
        for i in range(1, count + 1):
            new_costumes.append(self.costume_entry(
                {"name": "台词%d" % i,
                 "asset": "%s/chat_%02d.png" % (lines_dir, i)}, tmpdir))
        return new_costumes + costumes

    # ------------------------------------------------------------------ #
    # 列表显示角色
    # ------------------------------------------------------------------ #
    def _build_list_display(self, tdef, tmpdir, costumes):
        """为「列表显示」角色补齐 0~9 造型。

        列表比变量复杂：Scratch 没有「列表监视器」以外的显示方式，
        而监视器是舞台角落的小框，做进游戏 UI 里很难看。

        这里用数字精灵的同一套机制，但显示的是**列表的某一项**：
          · list_index: 显示列表第几项（1 起）
          · list_length: 显示列表长度
        两者都取个位显示（列表长度 < 10 才有意义）。
        要显示完整数字，就把 N 个数字精灵并排放在舞台上。
        """
        cfg = tdef.get("list_display") or {}
        if not (cfg.get("list") and (cfg.get("list_index") or cfg.get("list_length"))):
            raise ValueError(
                "角色 %r 的 list_display 必须写明 list（哪个列表）"
                "以及 list_index（第几项）或 list_length（长度）"
                % tdef.get("name"))
        digit_dir = (cfg.get("assets") or "assets/ui").rstrip("/")
        new_costumes = []
        for i in range(10):
            rel = "%s/d%d.png" % (digit_dir, i)
            new_costumes.append(self.costume_entry(
                {"name": str(i), "asset": rel}, tmpdir))
        return new_costumes + costumes

    # ------------------------------------------------------------------ #
    # target 构建
    # ------------------------------------------------------------------ #
    # ------------------------------------------------------------------ #
    # 目标构建
    # ------------------------------------------------------------------ #
    def build_target(self, tdef, is_stage, layer_order):
        self.blocks = {}
        self._pending_comments = []
        label = "Stage" if is_stage else tdef.get("name", "Sprite")
        self._tmp = type("T", (), {
            "var_ids": {}, "list_ids": {}, "var_initials": {}, "list_initials": {},
            "var_cloud": {}, "list_cloud": {}, "procs": {}, "label": label,
            # 自定义积木参数：名字 -> id（不是普通变量！）
            "arg_names": {}, "arg_types": {},
        })()
        tctx = self._tmp

        for vname, vraw in (tdef.get("variables") or {}).items():
            init, cloud = self._var_decl(vraw)
            tctx.var_ids[vname] = gen_id()
            tctx.var_initials[vname] = init
            tctx.var_cloud[vname] = cloud
            if cloud:
                self.cloud_count += 1
                if self.cloud_count > CLOUD_LIMIT:
                    raise ValueError(
                        "云变量超过上限 %d 个（Scratch 3.0 限制）" % CLOUD_LIMIT)
        for lname, lraw in (tdef.get("lists") or {}).items():
            init, cloud = self._var_decl(lraw) if isinstance(lraw, dict) else (lraw, False)
            tctx.list_ids[lname] = gen_id()
            # 列表初值：可以是 [1,2,3] 这样的数组，也可以是 {value: [...]} 形式
            if isinstance(init, (list, tuple)):
                tctx.list_initials[lname] = [str(v) for v in init]
            elif init is None or init == "":
                tctx.list_initials[lname] = []
            else:
                tctx.list_initials[lname] = [str(init)]
            if cloud:
                self.warnings.append(
                    "Scratch 3.0 不支持云列表（官方 sb3 规范的 list 定义只允许 [名字, 内容] 两项），"
                    "列表 %r 已按普通列表生成。" % lname)

        tmpdir = tempfile.mkdtemp(prefix="sb3assets_")
        costume_src = tdef.get("costumes") or tdef.get("backdrops") or []
        digit_cfg = tdef.get("digit_display")
        chat_cfg = tdef.get("chat_box")
        list_cfg = tdef.get("list_display")
        if not costume_src and not (digit_cfg or chat_cfg or list_cfg):
            raise ValueError(
                "%s 没有任何造型：官方 sb3 规范要求每个 target 至少 1 个 costume"
                "（舞台用 stage.backdrops，角色用 costumes）。" % label)
        costumes = [self.costume_entry(c, tmpdir) for c in costume_src]
        sounds = [self.sound_entry(s, tmpdir) for s in (tdef.get("sounds") or [])]

        # 「用角色显示变量/列表/台词」：自动补齐所需的造型
        if digit_cfg:
            costumes = self._build_digit_display(tdef, costume_src, tmpdir, costumes)
        if chat_cfg:
            costumes = self._build_chat_box(tdef, tmpdir, costumes)
        if list_cfg:
            costumes = self._build_list_display(tdef, tmpdir, costumes)

        for pdef in (tdef.get("procedures") or []):
            self._build_procedure(pdef, tctx, x=300, y=200)

        # 每个顶层脚本记住入口块，整理积木时要给它们排位置
        script_tops = []
        for script in (tdef.get("scripts") or []):
            top = self._chain(script, tctx, x=100, y=100)
            if top:
                script_tops.append(top)

        # 整理积木：把顶层脚本按网格排开（否则在 Scratch 里全叠在左上角）
        self._tidy_scripts(script_tops, tdef.get("layout"))

        # 注释：附着到积木的（内联 comment:）+ 悬空在画布上的
        comments = {}
        for bid, ctext in self._pending_comments:
            cid = gen_id()
            b = self.blocks[bid]
            comments[cid] = {
                "blockId": bid,
                "text": ctext,
                "minimized": False,
                "x": b.get("x", 0) + 180,
                "y": b.get("y", 0),
                "width": 200,
                "height": 200,
            }
            b["comment"] = cid
        for c in (tdef.get("comments") or []):
            if not isinstance(c, dict) or not c.get("text"):
                continue
            cid = gen_id()
            comments[cid] = {
                "blockId": c.get("block"),
                "text": str(c["text"]),
                "minimized": bool(c.get("minimized", False)),
                "x": c.get("x", 20),
                "y": c.get("y", 20),
                "width": c.get("width", 200),
                "height": c.get("height", 200),
            }

        # 变量：[名字, 初值] 或 [名字, 初值, true]（云变量）
        variables = {}
        for name, vid in tctx.var_ids.items():
            entry = [name, tctx.var_initials.get(name, 0)]
            if tctx.var_cloud.get(name):
                entry.append(True)
            variables[vid] = entry
        lists = {lid: [name, list(tctx.list_initials.get(name, []))]
                 for name, lid in tctx.list_ids.items()}

        target = {
            "isStage": is_stage,
            "name": "Stage" if is_stage else tdef.get("name", "Sprite"),
            "variables": variables,
            "lists": lists,
            "broadcasts": {},
            "blocks": self.blocks,
            "comments": comments,
            "currentCostume": 0,
            "costumes": costumes,
            "sounds": sounds,
            "volume": 100,
            "layerOrder": layer_order,
        }
        if is_stage:
            target.update({"tempo": 60, "videoTransparency": 50,
                           "videoState": "on", "textToSpeechLanguage": None})
            # 舞台上的变量/列表是全局的：所有角色共用同一个 id
            self.global_vars.update(tctx.var_ids)
            self.global_lists.update(tctx.list_ids)
        else:
            rs = tdef.get("rotationStyle", "all around")
            # Scratch 官方 project.json schema 只接受这三个字符串。作者若写
            # none / fixed / 不旋转，产物在编辑器里能打开，但 L2 schema 校验必 FAIL
            # （完整 verify 才发现，门禁查不到）。这里统一归一化并告警。
            if rs not in ("all around", "left-right", "don't rotate"):
                fixed = {"none": "don't rotate", "fixed": "don't rotate",
                         "不旋转": "don't rotate"}.get(
                             str(rs).strip().lower(), "don't rotate")
                self.warnings.append(
                    "角色 %r 的 rotationStyle=%r 非法，已归一化为 %r"
                    "（合法值：all around / left-right / don't rotate）"
                    % (tdef.get("name"), rs, fixed))
                rs = fixed
            target.update({
                "visible": tdef.get("visible", True),
                "x": tdef.get("x", 0), "y": tdef.get("y", 0),
                "size": tdef.get("size", 100), "direction": tdef.get("direction", 90),
                "draggable": False, "rotationStyle": rs,
            })
        return target, tmpdir

    # ------------------------------------------------------------------ #
    # 顶层
    # ------------------------------------------------------------------ #
    def build(self, ir, out_sb3, workdir):
        p = ir["project"]
        for ext in (p.get("extensions") or []):
            self.extensions.add(ext)

        targets_tmp = []
        stage = p.get("stage")
        if stage is None:
            stage = {"costumes": [], "scripts": []}
        stage_target, td = self.build_target(stage, True, 0)
        targets_tmp.append((stage_target, td))

        layer = 1
        for sp in (p.get("sprites") or []):
            st, td = self.build_target(sp, False, layer)
            layer += 1
            targets_tmp.append((st, td))

        stage_target["broadcasts"] = {n: n for n in self.broadcasts_used}

        # 屏幕上的读数（变量/列表监视器）
        monitors = []
        for m in (stage.get("monitors") or []):
            mon = self._make_monitor(m, stage_target)
            if mon:
                monitors.append(mon)

        project = {
            "targets": [t for t, _ in targets_tmp],
            "monitors": monitors,
            "extensions": sorted(self.extensions),
            "meta": {"semver": "3.0.0", "vm": "0.2.0-prerelease",
                     "agent": "ai-scratch-maker/0.2"},
        }
        os.makedirs(workdir, exist_ok=True)
        with open(os.path.join(workdir, "project.json"), "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=True)
        # 只记录【本次构建实际引用】的资产名。早期这里打包 os.listdir(workdir) 全量，
        # 而 build_all 共用一个临时目录：前一个作品留下的资产会被后一个作品打包进去，
        # 孤儿素材越攒越多（体积虚高到 7~12MB，正是 #228 min_bytes 污染值的来源）。
        # 单文件构建行为不变（emitted 就是全部），批量构建也不会再串味。
        emitted = set()
        for _, td in targets_tmp:
            for fn in os.listdir(td):
                with open(os.path.join(td, fn), "rb") as sf:
                    with open(os.path.join(workdir, fn), "wb") as df:
                        df.write(sf.read())
                if fn != "project.json":
                    emitted.add(fn)
        if os.path.exists(out_sb3):
            os.remove(out_sb3)
        with zipfile.ZipFile(out_sb3, "w", zipfile.ZIP_STORED) as z:
            z.write(os.path.join(workdir, "project.json"), "project.json")
            for fn in sorted(emitted):
                z.write(os.path.join(workdir, fn), fn)
        return project


def expand_display_scripts(ir, assets_src=None):
    """把声明式的「显示」配置展开成真实的脚本。

    这样写 IR 的人不需要自己算「造型序号 = 值 mod 10 + 1」这种
    运行时细节（数字按 1 起算、字符串按名字匹配），
    只要声明想显示什么，展开器负责生成正确的积木。

    目前支持三类：
      digit_display  —— 显示变量的个位
      list_display   —— 显示列表某一项 / 列表长度的个位
      chat_say       —— 聊天框角色显示第 N 句台词
    """
    project = ir.get("project") or {}

    def _rewrite_chat(items):
        """把 chat_say / safe_spawn 伪积木改写成真实积木。"""
        out = []
        for blk in items:
            if not isinstance(blk, dict):
                out.append(blk)
                continue
            keys = list(blk.keys())
            if len(keys) == 1 and keys[0] == "chat_say":
                cfg = blk["chat_say"] or {}
                line = int(cfg.get("line", 1))
                secs = cfg.get("secs")
                # 造型序号按 1 起算：第 N 句 -> 造型序号 N + 1
                out.append({"switch_costume": {"costume": {"add": [line, 1]}}})
                out.append({"show": None})
                if secs is not None:
                    out.append({"wait": secs})
                    out.append({"hide": None})
                continue
            if len(keys) == 1 and keys[0] == "safe_spawn":
                cfg = blk["safe_spawn"] or {}
                avoid = cfg.get("avoid")
                mind = cfg.get("min_distance", 120)
                if not avoid:
                    raise ValueError(
                        "safe_spawn 必须写明 avoid（要避开哪个角色）")
                # 反复随机落点，直到离目标角色足够远
                out.append({
                    "repeat_until": {
                        "cond": {"greater_than": {
                            "a": {"distance_to": {"object": avoid}},
                            "b": mind}},
                        "do": [{"goto": "_random_"}],
                    }
                })
                continue
            if len(keys) > 1:
                name, val = keys[0], blk[keys[0]]
                rest = {k: blk[k] for k in keys[1:]}
                out.append({name: val, **rest})
                continue
            (name, val), = blk.items()
            if isinstance(val, dict) and ("do" in val or "else" in val):
                newval = dict(val)
                if "do" in newval:
                    newval["do"] = _rewrite_chat(newval["do"])
                if "else" in newval:
                    newval["else"] = _rewrite_chat(newval["else"])
                out.append({name: newval})
            else:
                out.append({name: val})
        return out

    for target in [project.get("stage") or {}] + list(project.get("sprites") or []):
        cfg = target.get("digit_display")
        lcfg = target.get("list_display")
        if not (cfg or lcfg):
            # 没有声明式显示配置，但可能有 chat_say 要改写
            if target.get("scripts"):
                target["scripts"] = [_rewrite_chat(s) for s in target["scripts"]]
            continue
        scripts = target.setdefault("scripts", [])
        if cfg and cfg.get("auto_script", True):
            var = cfg.get("variable")
            if not var:
                raise ValueError("digit_display 必须写明 variable")
            digits = int(cfg.get("digits", 1))
            if digits < 1:
                digits = 1
            assets = cfg.get("assets")
            sz = int(target.get("size", 100))
            # 量出数字图的真实尺寸，自动把 gap 调到 ≥ 数字在屏幕上的宽度，
            # 否则相邻数字会重叠 / 被裁切——这就是「数字显示不全」最常见的根因。
            dwd, dht = _digit_natural_size(assets, assets_src)
            on_screen_digit_w = dwd * sz / 100.0
            gap = max(int(cfg.get("gap", 30)), int(on_screen_digit_w) + 6)
            # 首页背景存在时，数字精灵首页隐藏、点「开始」后才显示
            start_msg = (project.get("title_screen") or {}).get("broadcast")
            top_idx = digits - 1

            def _digit_costume(idx):
                # 第 idx 位的数值：反复「减去个位再除以 10」，避开对 floor 的依赖
                e = {"var": var}
                for _ in range(idx):
                    e = {"divide": {"a": {"subtract": {"a": e,
                        "b": {"mod": {"a": e, "b": 10}}}}, "b": 10}}
                return {"add": [{"mod": {"a": e, "b": 10}}, 1]}

            def _digit_scripts(idx):
                costume = _digit_costume(idx)
                if start_msg:
                    return [
                        [{"when_green_flag_clicked": None}, {"hide": None}],
                        [{"when_receive": {"message": start_msg}},
                         {"show": None},
                         {"forever": {"do": [
                             {"switch_costume": {"costume": costume}}]}}],
                    ]
                return [[{"when_green_flag_clicked": None},
                         {"forever": {"do": [
                             {"switch_costume": {"costume": costume}}]}}]]

            # 主角色（当前 target）显示最高位
            scripts.extend(_digit_scripts(top_idx))
            # 多位时，为低位各生成一个独立数字精灵角色（次高→个位，依次右移 gap）
            sprites = project.setdefault("sprites", [])
            base = target.get("name", "数字")
            x0 = int(target.get("x", 0))
            y0 = int(target.get("y", 0))
            if digits > 1:
                for k in range(1, digits):
                    idx = top_idx - k
                    dd = {"variable": var}
                    if assets:
                        dd["assets"] = assets
                    sprites.append({
                        "name": "%s_位%d" % (base, k),
                        "x": x0 + k * gap, "y": y0, "size": sz,
                        "digit_display": dd,
                        "scripts": _digit_scripts(idx),
                    })

            # ---- 文字标签：用角色展示「这是什么变量」，避免只摆数字看不懂 ----
            label_text = cfg.get("label")
            if label_text:
                lsz = int(cfg.get("label_size", 100))
                lpath = _render_label_png(
                    str(label_text),
                    font_size=int(cfg.get("label_font", 32)),
                    color=cfg.get("label_color", "#ffffff"))
                lw, lh = _png_size_file(lpath)
                on_screen_label_w = lw * lsz / 100.0
                on_screen_label_h = lh * lsz / 100.0
                on_screen_digit_h = dht * sz / 100.0
                side = cfg.get("label_side", "left")
                if side == "right":
                    lx = (x0 + (digits - 1) * gap + on_screen_digit_w / 2
                          + on_screen_label_w / 2 + 6)
                    ly = y0
                elif side == "top":
                    lx = x0 + (digits - 1) * gap / 2.0
                    ly = y0 + on_screen_digit_h / 2 + on_screen_label_h / 2 + 6
                else:  # left（默认）
                    lx = (x0 - on_screen_digit_w / 2
                          - on_screen_label_w / 2 - 6)
                    ly = y0
                lx = max(-225, min(225, lx))
                ly = max(-165, min(165, ly))
                label_scripts = [
                    [{"when_green_flag_clicked": None}, {"hide": None}],
                    [{"when_receive": {"message": start_msg}},
                     {"show": None}],
                ] if start_msg else [
                    [{"when_green_flag_clicked": None}, {"show": None}],
                ]
                sprites.append({
                    "name": "%s_标签" % base,
                    "x": round(lx), "y": round(ly), "size": lsz,
                    "rotationStyle": "don't rotate",
                    "costumes": [{"name": "文字", "asset": lpath}],
                    "scripts": label_scripts,
                })

        if lcfg and lcfg.get("auto_script", True):
            lst = lcfg.get("list")
            if lcfg.get("list_index"):
                src = {"item_of_list": {"list": lst, "index": lcfg["list_index"]}}
            else:
                src = {"length_of_list": {"list": lst}}
            scripts.append([
                {"when_green_flag_clicked": None},
                {"forever": {"do": [
                    {"switch_costume": {"costume": {
                        "add": [{"mod": {"a": src, "b": 10}}, 1]}}},
                ]}},
            ])

        # 聊天框：chat_say -> 换造型 + 显示
        target["scripts"] = [_rewrite_chat(s) for s in scripts]
    return ir


def expand_juice(ir):
    """把声明式 juice: 块展开成真实手感脚本（挤压拉伸 / 命中闪光 / 震屏）。

    这是「质量焊死在编译期」的核心：只要作品骨架带 juice:，AI 生成的每个
    作品都自带游戏手感，无法跳过——不依赖 AI 自觉写效果积木。

    IR 写法（顶层 juice: 列表）：
      juice:
        - sprite: 挡板        # 受影响的角色（必须已存在）
          trigger: 加分       # 触发广播（注意：键名用 trigger，别用 on——YAML 1.1 把 on 当布尔）
          squash: 22          # 挤压拉伸幅度(%)，快速放大回弹
          flash: 40           # 白闪幅度(BRIGHTNESS)，短暂提亮再还原
          shake: 5            # 震屏幅度(px)，短暂随机抖动
    """
    juice = ir.get("juice")
    if not juice:
        return ir
    if not isinstance(juice, list):
        print("[警告] juice 必须是列表，已跳过", file=sys.stderr)
        return ir
    project = ir.get("project") or {}
    sprites = project.get("sprites") or []
    by_name = {}
    for s in sprites:
        if isinstance(s, dict) and s.get("name"):
            by_name[s["name"]] = s
    for entry in juice:
        if not isinstance(entry, dict):
            continue
        sname = entry.get("sprite")
        # 兼容 YAML 1.1 把未加引号的 on 当布尔 True 的写法
        trig = entry.get("trigger")
        if trig is None and True in entry:
            trig = entry[True]
        if not sname or not trig:
            print("[警告] juice 条目缺 sprite/trigger，跳过", file=sys.stderr)
            continue
        tgt = by_name.get(sname)
        if tgt is None:
            print("[警告] juice 指向不存在的角色 %r，跳过" % sname, file=sys.stderr)
            continue
        base = int(tgt.get("size", 100))
        blocks = []
        # —— 挤压拉伸：快速放大再回弹，制造「打击感」 ——
        if entry.get("squash") is not None:
            a = float(entry["squash"])
            blocks += [
                {"set_size": {"value": base}},
                {"change_size": {"size": a}},
                {"wait": 0.03},
                {"change_size": {"size": -a * 0.5}},
                {"wait": 0.03},
                {"set_size": {"value": base}},
            ]
        # —— 命中白闪：短暂提亮再还原 ——
        if entry.get("flash") is not None:
            f = float(entry["flash"])
            blocks += [
                {"set_effect": {"effect": "BRIGHTNESS", "value": f}},
                {"wait": 0.05},
                {"set_effect": {"effect": "BRIGHTNESS", "value": 0}},
            ]
        # —— 震屏：短暂随机抖动（持续被重定位的角色会自行归位） ——
        if entry.get("shake") is not None:
            s = float(entry["shake"])
            for _ in range(3):
                blocks += [
                    {"change_x": {"dx": {"random": [-s, s]}}},
                    {"change_y": {"dy": {"random": [-s, s]}}},
                    {"wait": 0.02},
                ]
        if not blocks:
            continue
        scripts = tgt.setdefault("scripts", [])
        scripts.append([{"when_receive": {"message": trig}}] + blocks)
    return ir


def expand_animations(ir):
    """把声明式 animations: 帧动画展开成真实切换造型脚本。

    设计目标：让「会动」成为编译期能力——只要角色的 IR 写了 animations:，
    生成的作品就自带多帧循环动画，无需作者手写翻帧逻辑（这是 Platformer 类
    作品和 griffpatch 顶级作品共有的「看起来活」的关键，也是本次对照 GitHub
    标杆作品后补上的最大短板）。

    IR 写法（在某个 sprite 下声明 animations: 字典）：
      - name: 玩家
        costumes:
          - {name: idle,  asset: assets/player/idle.svg}
          - {name: walk1, asset: assets/player/walk1.svg}
          - {name: walk2, asset: assets/player/walk2.svg}
          - {name: jump,  asset: assets/player/jump.svg}
        variables:
          状态: 待机            # 驱动变量：字符串，作者的脚本去改它
        animations:
          var: 状态             # 指向上面的驱动变量
          fps: 12               # 每秒帧数（默认 12）
          states:               # 状态名 -> 该状态的造型名列表（按顺序循环）
            待机: [idle]
            走:   [walk1, walk2]
            跳:   [jump]
        scripts:
          ... 作者自己的逻辑里 set_variable 状态 为 待机/走/跳 ...

    展开器会：
      1) 校验每个状态引用的造型名都真实存在于该角色 costumes，否则告警并跳过该状态；
      2) 注入 3 个私有变量：动画帧 / 动画上一状态 / 动画序列（动画序列为列表，存当前
         状态的造型名）；
      3) 注入两段脚本：
         · 状态机：当状态变量变化时，重建「动画序列」列表（只重建一次，不每帧重建）；
         · 翻帧器：每 1/fps 秒推进一帧，按 (帧 mod 序列长)+1 取造型名并切换造型。
    """
    project = ir.get("project") or {}
    sprites = project.get("sprites") or []
    for sp in sprites:
        if not isinstance(sp, dict):
            continue
        anim = sp.get("animations")
        if not anim or not isinstance(anim, dict):
            continue
        sname = sp.get("name", "<匿名角色>")
        costumes = sp.get("costumes") or []
        costume_names = [c.get("name") for c in costumes if isinstance(c, dict)]
        driver = anim.get("var")
        states = anim.get("states") or {}
        if not driver:
            print("[警告] %s 的 animations 缺 var（驱动变量），跳过帧动画" % sname, file=sys.stderr)
            continue
        if not isinstance(states, dict) or not states:
            print("[警告] %s 的 animations.states 为空或格式不对，跳过帧动画" % sname, file=sys.stderr)
            continue
        # —— 校验造型名（引用不存在的造型是「画了却动不起来」的最常见原因）——
        valid_states = {}
        for st_name, cnames in states.items():
            if not isinstance(cnames, list):
                cnames = [cnames]
            cnames = [c for c in cnames if c is not None]
            bad = [c for c in cnames if c not in costume_names]
            if bad:
                print("[警告] %s 状态 %r 引用了不存在的造型 %r（该角色造型：%s），已跳过该状态"
                      % (sname, st_name, bad, costume_names), file=sys.stderr)
                continue
            if not cnames:
                continue
            valid_states[st_name] = cnames
        if not valid_states:
            print("[警告] %s 的 animations 没有可用状态（造型全部缺失），跳过帧动画" % sname, file=sys.stderr)
            continue

        # —— 注入私有变量 / 列表（变量按角色隔离，前缀避免与作者变量撞名）——
        vars_ = sp.setdefault("variables", {})
        lists_ = sp.setdefault("lists", {})
        FRAME = "动画帧"
        PREV = "动画上一状态"
        SEQ = "动画序列"
        if FRAME not in vars_:
            vars_[FRAME] = 0
        if PREV not in vars_:
            vars_[PREV] = ""
        if SEQ not in lists_:
            lists_[SEQ] = []
        # 驱动变量若未声明，自动补一个，初值取第一个状态（避免空状态机）
        if driver not in vars_:
            init_state = next(iter(valid_states))
            print("[警告] %s 的 animations.var=%r 未在 variables 声明，已自动补建（初值=%r）"
                  % (sname, driver, init_state), file=sys.stderr)
            vars_[driver] = init_state

        fps = float(anim.get("fps", 12)) or 12.0
        wait_secs = round(1.0 / fps, 4)

        # —— 脚本 A：状态机（状态变化时重建动画序列）——
        rebuild_inner = [{"delete_all_of_list": {"list": SEQ}}]
        for st_name, cnames in valid_states.items():
            adds = [{"add_to_list": {"list": SEQ, "item": c}} for c in cnames]
            rebuild_inner.append({
                "if": {"cond": {"equals": {"a": {"var": driver}, "b": st_name}},
                       "do": adds}})
        rebuild_inner.append({"set_variable": {"var": PREV, "value": {"var": driver}}})
        state_machine = [
            {"when_green_flag_clicked": None},
            {"set_variable": {"var": PREV, "value": ""}},
            {"forever": {"do": [
                {"if": {"cond": {"not": {"operand": {"equals": {"a": {"var": driver}, "b": {"var": PREV}}}}},
                        "do": rebuild_inner}}
            ]}},
        ]

        # —— 脚本 B：翻帧器（按帧率推进并切换造型）——
        frame_index_expr = {
            "add": [
                {"mod": {"a": {"var": FRAME}, "b": {"length_of_list": {"list": SEQ}}}},
                1,
            ]
        }
        flipper = [
            {"when_green_flag_clicked": None},
            {"forever": {"do": [
                {"wait": wait_secs},
                {"change_variable": {"var": FRAME, "value": 1}},
                {"if": {"cond": {"greater_than": {"a": {"length_of_list": {"list": SEQ}}, "b": 0}},
                        "do": [
                            {"switch_costume": {"costume": {
                                "item_of_list": {"list": SEQ, "index": frame_index_expr}}}}]}},
            ]}},
        ]
        scripts = sp.setdefault("scripts", [])
        scripts.append(state_machine)
        scripts.append(flipper)
    return ir


def expand_tween(ir):
    """把声明式 tweens: 块展开成真实补间脚本（指数平滑逼近，铁律9 缓动）。

    让「平滑过渡」成为编译期能力——只要 IR 顶层写了 tweens:，指定角色的某个变量
    就会在被广播触发时，从当前值指数平滑逼近目标值（菜单滑入、UI 淡入位移、镜头推拉
    都用它）。不依赖 AI 自觉写 lerp 积木。

    IR 写法（顶层 tweens: 列表）：
      tweens:
        - sprite: 面板
          trigger: 打开菜单          # 触发广播
          var: 面板x                # 要补间的变量（必须已在角色 variables 声明）
          to: -200                 # 目标值（数字，或 {var: 玩家x} 跟随另一变量）
          frames: 18               # 补间帧数（默认 18，决定时长 ≈ frames/30 秒）
          easing: easeOut          # easeOut（默认）/ linear / easeIn（平滑系数）
    """
    tweens = ir.get("tweens")
    if not tweens:
        return ir
    if not isinstance(tweens, list):
        print("[警告] tweens 必须是列表，已跳过", file=sys.stderr)
        return ir
    project = ir.get("project") or {}
    sprites = project.get("sprites") or []
    by_name = {}
    for s in sprites:
        if isinstance(s, dict) and s.get("name"):
            by_name[s["name"]] = s
    for tw in tweens:
        if not isinstance(tw, dict):
            continue
        sname = tw.get("sprite")
        trig = tw.get("trigger")
        var = tw.get("var")
        tgt = tw.get("to")
        frames = int(tw.get("frames", 18)) or 18
        easing = (tw.get("easing") or "easeOut").lower()
        if not sname or not trig or not var:
            print("[警告] tween 缺 sprite/trigger/var，跳过", file=sys.stderr)
            continue
        tgt_sp = by_name.get(sname)
        if tgt_sp is None:
            print("[警告] tween 指向不存在角色 %r，跳过" % sname, file=sys.stderr)
            continue
        vars_ = tgt_sp.setdefault("variables", {})
        if var not in vars_:
            print("[警告] tween.var=%r 不在角色 %r 的 variables，跳过" % (var, sname), file=sys.stderr)
            continue
        if isinstance(tgt, dict) and "var" in tgt:
            target_expr = {"var": tgt["var"]}
        else:
            target_expr = tgt
        if easing == "linear":
            k = 1.0 / frames
        elif easing == "easein":
            k = 0.08
        else:  # easeOut：指数平滑，帧数只影响何时停止循环，逼近速度恒定
            k = 0.15
        fps = 30.0
        wait_s = round(1.0 / fps, 4)
        loop_body = [
            {"set_variable": {"var": var, "value": {"add": [
                {"var": var},
                {"multiply": [{"subtract": [target_expr, {"var": var}]}, k]}
            ]}}},
            {"wait": wait_s},
        ]
        scripts = tgt_sp.setdefault("scripts", [])
        scripts.append([
            {"when_receive": {"message": trig}},
            {"repeat": {"times": frames, "do": loop_body}},
        ])
    return ir


def expand_camera(ir):
    """把声明式 camera: 块展开成相机跟随脚本（只动绘制坐标，不碰状态量，见 ir-patterns.md P5）。

    横版/大场景作品需要相机：相机变量 镜头x 由本展开器在舞台（或指定角色）上维护，
    每帧向「目标 - 偏移」做 lerp 逼近；其他角色按 P5 模式用 (自身x - 镜头x) 作为绘制坐标，
    从而自动获得平滑跟随 + 视差基础。纯编译期注入，不依赖 AI 自觉写相机逻辑。

    IR 写法（顶层 camera: 字典）：
      camera:
        var: 镜头x                 # 相机会维护的变量名（自动在 owner 上声明）
        owner: 舞台                # 维护者：舞台（默认）或某角色名
        follow:
          var: 玩家x              # 跟随的变量（角色的真实世界坐标）
          offset: 160             # 让角色停在屏幕偏左 160 处
          lerp: 0.1               # 平滑系数（每帧逼近比例，0.1 顺滑）
    """
    cam = ir.get("camera")
    if not cam or not isinstance(cam, dict):
        return ir
    project = ir.get("project") or {}
    var = cam.get("var")
    owner_name = cam.get("owner", "舞台")
    follow = cam.get("follow") or {}
    fvar = follow.get("var")
    offset = follow.get("offset", 0)
    lerp = follow.get("lerp", 0.1)
    if not var or not fvar:
        print("[警告] camera 缺 var 或 follow.var，跳过", file=sys.stderr)
        return ir
    owner = None
    if owner_name in ("舞台", "stage", None):
        owner = project.get("stage")
    else:
        for s in project.get("sprites") or []:
            if isinstance(s, dict) and s.get("name") == owner_name:
                owner = s
                break
    if owner is None:
        print("[警告] camera.owner=%r 不存在，跳过" % owner_name, file=sys.stderr)
        return ir
    ov = owner.setdefault("variables", {})
    if var not in ov:
        ov[var] = 0
    # 初始对齐 + 每帧 lerp（指数平滑，铁律16 控制分层里的「规划/执行」雏形）
    init = {"set_variable": {"var": var, "value": {"subtract": [{"var": fvar}, offset]}}}
    perframe = {"set_variable": {"var": var, "value": {"add": [
        {"var": var},
        {"multiply": [{"subtract": [{"subtract": [{"var": fvar}, offset]}, {"var": var}]}, lerp]}
    ]}}}
    scripts = owner.setdefault("scripts", [])
    scripts.append([{"when_green_flag_clicked": None}, init])
    scripts.append([
        {"when_green_flag_clicked": None},
        {"forever": {"do": [perframe, {"wait": 0.02}]}},
    ])
    return ir


def build_title_screen(ir):
    """生成「首页（标题页）」。

    游戏类作品应该先有一个首页，点「开始游戏」才进入正题。
    机制（全部用 Scratch 原生积木，不做私有扩展）：

      · 舞台的第一个背景是首页，往后是各个游戏场景
      · 一个「开始按钮」角色，被点击后广播「开始游戏」
      · 舞台收到「开始游戏」后切到游戏场景背景
      · 游戏角色在首页时隐藏，收到「开始游戏」后出现

    IR 写法：
        project:
          title_screen:
            backdrop: assets/ui/title_bg.png     # 首页背景（整屏 480x360）
            button:
              asset: assets/ui/btn_start.png
              x: 0
              y: -110
            game_backdrop: 游戏场景              # 点开始后切到哪个背景
            broadcast: 开始游戏
    """
    project = ir.get("project") or {}
    ts = project.get("title_screen")
    if not ts:
        return ir
    stage = project.get("stage")
    if stage is None:
        raise ValueError("title_screen 需要 stage（首页背景挂在舞台上）")

    backdrop_asset = ts.get("backdrop")
    if not backdrop_asset:
        raise ValueError("title_screen 必须写明 backdrop（首页背景图片）")
    title_name = ts.get("title_name", "首页")
    backdrops = stage.setdefault("backdrops", [])
    if not any(b.get("name") == title_name for b in backdrops):
        backdrops.insert(0, {"name": title_name, "asset": backdrop_asset})
    game_backdrop = ts.get("game_backdrop")
    if not game_backdrop:
        raise ValueError("title_screen 必须写明 game_backdrop（点开始后进入哪个背景）")
    if not any(b.get("name") == game_backdrop for b in backdrops):
        raise ValueError(
            "title_screen 的 game_backdrop %r 不在 stage.backdrops 里" % game_backdrop)
    broadcast = ts.get("broadcast", "开始游戏")

    # 舞台脚本：绿旗 -> 切到首页；收到开始游戏 -> 切到游戏场景
    stage_scripts = stage.setdefault("scripts", [])
    stage_scripts.append([
        {"when_green_flag_clicked": None},
        {"switch_backdrop": {"backdrop": title_name}},
    ])
    stage_scripts.append([
        {"when_receive": {"message": broadcast}},
        {"switch_backdrop": {"backdrop": game_backdrop}},
    ])

    # 开始按钮角色
    btn = ts.get("button") or {}
    if btn.get("asset"):
        project.setdefault("sprites", []).append({
            "name": btn.get("name", "开始按钮"),
            "x": btn.get("x", 0),
            "y": btn.get("y", -110),
            "size": btn.get("size", 100),
            "costumes": [{"name": "按钮", "asset": btn["asset"]}],
            "scripts": [
                [{"when_green_flag_clicked": None}, {"show": None}],
                [{"when_this_sprite_clicked": None},
                 {"hide": None},
                 {"broadcast": broadcast}],
            ],
        })
    else:
        project.setdefault("sprites", []).append({
            "name": "开始按钮",
            "x": 0, "y": -110,
            "costumes": [{"name": "按钮", "asset": backdrop_asset}],
            "scripts": [
                [{"when_green_flag_clicked": None}, {"show": None}],
                [{"when_this_sprite_clicked": None},
                 {"hide": None},
                 {"broadcast": broadcast}],
            ],
        })
    return ir


def load_spec_file(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ #
# 产物缓存：内容哈希命中则跳过整段构建（只拷贝已存的 .sb3）。
# key 由「IR 内容 + 构建脚本 + 被引用资产内容」共同决定，确保任何输入变化都失效。
# ------------------------------------------------------------------ #
_CACHE_EXTS = (".png", ".svg", ".wav", ".jpg", ".jpeg", ".mp3", ".gif")


def _collect_asset_paths(ir, assets_src, ir_path):
    """收集 IR 里引用到的、且磁盘上真实存在的素材文件绝对路径。"""
    found = set()
    candidates = [
        assets_src,
        os.path.dirname(os.path.abspath(ir_path)) if ir_path else None,
        ".",
    ]

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                if isinstance(v, str):
                    s = v.strip()
                    if s.lower().endswith(_CACHE_EXTS):
                        for c in candidates:
                            if not c:
                                continue
                            p = s if os.path.isabs(s) else os.path.join(c, s)
                            if os.path.exists(p):
                                found.add(os.path.abspath(p))
                                break
                walk(v)
        elif isinstance(node, list):
            for it in node:
                walk(it)

    walk(ir)
    return found


def compute_cache_key(ir, assets_src, ir_path, here):
    """内容哈希缓存键。

    采用「IR 内容 + 各输入文件 mtime/size」而非整文件哈希：
      - 输入文件（构建脚本、spec、被引用素材）任一被编辑都会改 mtime → 必然失效；
      - 只 stat 不读内容，开销极低，避免「哈希资产」反而比构建更慢；
      - 同一次不改动的重构建，IR 与文件 mtime 不变 → 命中缓存、跳过整段构建。
    这是与 Make/ninja 同思路的 staleness 判定，足够安全（编辑即失效）。
    """
    h = hashlib.sha256()
    h.update(yaml.safe_dump(ir, allow_unicode=True, sort_keys=True).encode("utf-8"))
    files = [os.path.abspath(os.path.join(here, frel)) for frel in (
        "build_sb3.py",
        os.path.join("..", "references", "blocks-spec.json"),
        "make_ui_assets.py",
    )]
    files += sorted(_collect_asset_paths(ir, assets_src, ir_path))
    for p in files:
        try:
            st = os.stat(p)
            h.update(("%s|%d|%d" % (p, st.st_mtime_ns, st.st_size)).encode("utf-8"))
        except OSError:
            h.update(p.encode("utf-8"))
    return h.hexdigest()


def _sb3_counts(sb3_path):
    try:
        with zipfile.ZipFile(sb3_path) as z:
            pj = json.loads(z.read("project.json"))
        return (len(pj.get("targets", [])),
                sum(len(t.get("blocks", {})) for t in pj.get("targets", [])))
    except Exception:
        return 0, 0


def _sb3_meta(sb3_path):
    try:
        with zipfile.ZipFile(sb3_path) as z:
            pj = json.loads(z.read("project.json"))
        return (len(pj.get("targets", [])),
                sum(len(t.get("blocks", {})) for t in pj.get("targets", [])),
                pj.get("extensions", []))
    except Exception:
        return 0, 0, []


def build_one(ir_path, out_path, spec_path=None, assets_src=None, workdir=None,
              lenient=False, no_cache=False, cache_dir=None):
    """单文件构建 IR -> sb3，供 CLI 与 build_all 复用。

    返回 (ok: bool, message: str, code: int)：
      code 0  = 成功（含缓存命中）
      code 2  = 输入/读取/spec/变换/构建异常（含 IR 结构校验失败）
      code 3  = IR 语义错误（默认阻止交付，已删除半成品产物）
    非致命的 [警告] 仍打印到 stderr，单文件与批量模式都可见。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    spec_path = spec_path or os.path.join(here, "..", "references", "blocks-spec.json")
    # 产物目录可能不存在：全新 clone 时 examples/output/ 是 .gitignore 掉的空目录。
    # 不建目录就直接写会报 FileNotFoundError，用户会以为是构建器坏了。
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir and not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            return False, "无法创建产物目录 %s: %s" % (out_dir, e), 2
    try:
        spec = load_spec_file(spec_path)
    except Exception as e:
        return False, "无法读取 spec %s: %s" % (spec_path, e), 2
    try:
        if ir_path.lower().endswith(".json"):
            with open(ir_path, encoding="utf-8") as f:
                ir = json.load(f)
            ir_marks = None
        else:
            sys.path.insert(0, here)
            from ir_schema import load_ir_marked
            ir, ir_marks = load_ir_marked(ir_path)
    except Exception as e:
        return False, "无法读取 IR %s: %s" % (ir_path, e), 2
    sys.path.insert(0, here)
    from ir_schema import validate_ir
    if "community:" in str(ir):
        try:
            from asset_pack import expand_community_assets
            ir = expand_community_assets(ir)
        except Exception as e:
            return False, "社区素材展开失败: %s" % e, 2
    # 结构校验：先校验「作者原始 IR」，让报错行号精确指向源文件。
    # build_title_screen / expand_display_scripts 会改写 IR（丢失对象身份），若放到那之后，
    # 行号就对不上了。最终产物的结构正确性仍由 L2~L5 八层校验兜底。
    errs = validate_ir(ir, spec, marks=ir_marks)
    if errs:
        return False, "IR 校验失败: " + "; ".join(str(x) for x in errs), 2
    # asset 目录要先确定（expand_display_scripts 需要它来量数字图尺寸、生成标签）
    assets_src = assets_src or os.path.dirname(os.path.abspath(ir_path))
    # 产物缓存：内容哈希命中则跳过整段构建（IR / 构建脚本 / 被引用素材任一变化都会失效）。
    # key 在 transforms 之前算好，命中时连 transforms（含标签渲染等开销）一并跳过。
    do_cache = not no_cache
    cache_dir = cache_dir or os.path.join(REPO_ROOT, ".build_cache")
    cached = None
    if do_cache:
        try:
            key = compute_cache_key(ir, assets_src, ir_path, here)
            cached = os.path.join(cache_dir, key + ".sb3")
            if os.path.exists(cached):
                shutil.copyfile(cached, out_path)
                nt, nb, exts = _sb3_meta(cached)
                return True, "targets=%d blocks=%d extensions=%s | CACHE_HIT" % (nt, nb, exts), 0
        except Exception:
            cached = None
    try:
        # 首页（标题页）：生成背景、按钮角色与切换脚本
        ir = build_title_screen(ir)
        # 声明式配置 -> 真实脚本（数值显示、聊天框台词等）
        ir = expand_display_scripts(ir, assets_src)
        # 声明式手感 -> 真实脚本（挤压拉伸 / 白闪 / 震屏）；质量焊死在编译期
        ir = expand_juice(ir)
        # 声明式帧动画 -> 真实切换造型脚本（让「会动」成为编译期能力）
        ir = expand_animations(ir)
        # 声明式补间 -> 真实平滑逼近脚本（菜单滑入 / UI 过渡 / 镜头推拉，铁律9 缓动）
        ir = expand_tween(ir)
        # 声明式相机 -> 舞台维护 镜头x 跟随（横版大场景平滑跟随，ir-patterns.md P5）
        ir = expand_camera(ir)
    except Exception as e:
        return False, "IR 变换失败: %s" % e, 2
    workdir = workdir or tempfile.mkdtemp(prefix="sb3build_")
    try:
        b = Builder(spec, assets_src)
        project = b.build(ir, out_path, workdir)
    except Exception as e:
        return False, "构建异常: %s" % e, 2
    for w in b.warnings:
        print("[警告]", w, file=sys.stderr)
    # 语义致命错误：默认不交付。作品能打开、能过四层校验，但逻辑和 IR 意图不符，
    # 这类问题最难发现，必须在构建阶段就挡住。
    if b.semantic_errors:
        if lenient:
            for e in b.semantic_errors:
                print("[警告]（lenient 已放行）", e, file=sys.stderr)
        else:
            # build() 已经写出产物，这里删掉，避免留下一个「看似成功」的坏作品
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except OSError:
                pass
            return False, "IR 语义错误(%d 处，未生成): %s" % (
                len(b.semantic_errors),
                "; ".join(str(x) for x in b.semantic_errors)), 3
    n_targets = len(project["targets"])
    n_blocks = sum(len(t["blocks"]) for t in project["targets"])
    # 缓存写入（仅成功构建、且缓存启用、且该 key 尚未落盘；lenient 放行的语义问题不缓存）
    if do_cache and cached and not b.semantic_errors and not os.path.exists(cached):
        try:
            os.makedirs(cache_dir, exist_ok=True)
            shutil.copyfile(out_path, cached)
        except OSError:
            pass
    tag = " CACHE_MISS" if (do_cache and cached) else ""
    return True, "targets=%d blocks=%d extensions=%s%s" % (
        n_targets, n_blocks, project["extensions"], tag), 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spec", default=None, help="blocks-spec.json 路径")
    ap.add_argument("--assets-src", default=None, help="IR 中 asset 文件所在目录")
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--lenient", action="store_true",
                    help="放宽语义检查：静默丢弃操作数/未知键时只警告、仍生成 sb3（默认会阻止交付）")
    ap.add_argument("--no-cache", action="store_true",
                    help="禁用产物缓存（默认按内容哈希复用已构建的 .sb3，跳过重复构建）")
    ap.add_argument("--cache-dir", default=None,
                    help="缓存目录（默认 <仓库>/.build_cache）")
    args = ap.parse_args()
    ok, msg, code = build_one(
        args.ir, args.out, args.spec, args.assets_src, args.workdir,
        args.lenient, args.no_cache, args.cache_dir)
    if ok:
        print("OK 生成 %s | %s" % (args.out, msg))
        sys.exit(0)
    print(msg, file=sys.stderr)
    sys.exit(code)


if __name__ == "__main__":
    main()
