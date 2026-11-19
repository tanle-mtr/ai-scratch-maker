#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sb3 校验：结构合法性 + 编码正确性 + (可选) scratch-vm 运行时加载运行。

用法:
  python validate_sb3.py --sb3 out.sb3 [--spec references/blocks-spec.json]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

STATUS_OK = 0
STATUS_WARN = 0  # 仍算通过，但打印告警
STATUS_FAIL = 1


def md5_of(data):
    return hashlib.md5(data).hexdigest()


def _png_size(z, md5ext, height=False):
    """读 PNG 头的宽高（只解析 IHDR，不依赖 Pillow）。SVG 返回 None。"""
    if not md5ext or not md5ext.lower().endswith(".png"):
        return None
    try:
        data = z.read(md5ext)
    except KeyError:
        return None
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    # IHDR: 8 字节签名 + 4 长度 + 4 类型 + 宽(4) + 高(4)
    w = int.from_bytes(data[16:20], "big")
    h = int.from_bytes(data[20:24], "big")
    return h if height else w


def validate_structure(sb3_path, spec):
    errors = []
    warnings = []
    with zipfile.ZipFile(sb3_path) as z:
        names = z.namelist()
        if "project.json" not in names:
            errors.append("缺少 project.json")
            return errors, warnings, None
        proj = json.loads(z.read("project.json").decode("utf-8"))
        asset_names = set(n for n in names if n != "project.json")

        for key in ("targets", "monitors", "extensions", "meta"):
            if key not in proj:
                errors.append("project.json 缺少顶层键: %s" % key)

        # 资产一致性
        for t in proj.get("targets", []):
            for c in t.get("costumes", []):
                m = c.get("md5ext")
                if not m:
                    errors.append("造型缺少 md5ext: %s" % c.get("name"))
                    continue
                if m not in asset_names:
                    errors.append("资产缺失: %s" % m)
                    continue
                data = z.read(m)
                if md5_of(data) != m.split(".")[0]:
                    errors.append("资产 MD5 不匹配: %s" % m)
            for s in t.get("sounds", []):
                m = s.get("md5ext")
                if m and m not in asset_names:
                    errors.append("声音资产缺失: %s" % m)

        # 角色尺寸体检
        # 舞台 480x360。角色太大会有两个典型后果：
        #   1) 角色在屏幕中间时，别的角色一出现就「碰到」，判定条件恒成立
        #   2) 角色几乎占满屏幕，看不见别的角色
        # 只检查**会移动的角色**（含运动积木的）：聊天框、按钮这类 UI 面板
        # 本来就占地方，不算问题。
        STAGE_W, STAGE_H = 480, 360
        MAX_H_RATIO = 1.0 / 3.0     # 屏高占比上限
        MAX_W_RATIO = 1.0 / 2.0     # 屏宽占比上限
        for t in proj.get("targets", []):
            if t.get("isStage"):
                continue
            blocks = t.get("blocks") or {}
            if not any(str(b.get("opcode", "")).startswith("motion_") for b in blocks.values()):
                continue      # 不会动的角色（UI 面板）跳过检查
            size = float(t.get("size", 100)) / 100.0
            if size <= 0:
                continue
            worst_w = worst_h = 0
            for c in t.get("costumes", []):
                w = _png_size(z, c.get("md5ext"))
                h = _png_size(z, c.get("md5ext"), height=True)
                if w:
                    worst_w = max(worst_w, w * size)
                if h:
                    worst_h = max(worst_h, h * size)
            hr = worst_h / float(STAGE_H)
            wr = worst_w / float(STAGE_W)
            if hr > MAX_H_RATIO or wr > MAX_W_RATIO:
                warnings.append(
                    "角色 %r 在屏幕上约占 %d%% 屏高 / %d%% 屏宽"
                    "（上限 %d%% / %d%%）——角色太大容易「一出现就碰到」，"
                    "建议调小 size 或缩小原图"
                    % (t.get("name"), round(hr * 100), round(wr * 100),
                       round(MAX_H_RATIO * 100), round(MAX_W_RATIO * 100)))

        # opcode 合法性（对照 spec；spec 缺失时不强制）
        known = set(spec.get("blocks", {}).keys()) if spec else None
        used = set()
        for t in proj.get("targets", []):
            ids = set(t.get("blocks", {}).keys())
            for bid, b in t.get("blocks", {}).items():
                op = b.get("opcode")
                used.add(op)
                if known is not None and op not in known:
                    warnings.append("使用了 spec 未登记的 opcode: %s" % op)
                # 输入数组形态检查
                for iname, ival in (b.get("inputs", {}) or {}).items():
                    if ival is None:
                        continue
                    if not (isinstance(ival, list) and len(ival) >= 2):
                        errors.append("积木 %s 输入 %s 形态异常: %r" % (op, iname, ival))
                        continue
                    errors.extend(_check_primitive(op, iname, ival))
                # 字段形态检查
                for fname, fval in (b.get("fields", {}) or {}).items():
                    errors.extend(_check_field(op, fname, fval))
                # 注释关联检查（block.comment <-> comment.blockId 必须双向对得上）
                cid = b.get("comment")
                if cid is not None:
                    if cid not in (t.get("comments") or {}):
                        errors.append("积木 %s 的 comment 指向不存在的注释 %s" % (op, cid))
                    elif t["comments"][cid].get("blockId") != bid:
                        errors.append("积木 %s 与注释 %s 的关联不一致" % (op, cid))
            # 注释本身的检查
            for cid, c in (t.get("comments") or {}).items():
                bid = c.get("blockId")
                if bid is not None and bid not in ids:
                    errors.append("注释 %s 指向不存在的积木 %s" % (cid, bid))
                if not isinstance(c.get("text"), str):
                    errors.append("注释 %s 缺少 text" % cid)
                elif len(c["text"]) > 8000:
                    errors.append("注释 %s 的文本超过官方上限 8000 字符" % cid)
            # 影子积木必须是 topLevel=false
            # （scratch-vm 的 Blocks.createBlock 会把 topLevel=true 的积木加进 _scripts，
            #   而编辑器正是遍历 _scripts 生成画布的 —— 否则影子会变成悬在角落的孤块）
            for bid, b in t.get("blocks", {}).items():
                if b.get("shadow") and b.get("topLevel"):
                    errors.append("影子积木 %s(%s) 不应是 topLevel，否则会在画布上多出孤立积木"
                                  % (bid, b.get("opcode")))
        # 云变量检查
        cloud_n = 0
        for t in proj.get("targets", []):
            for vid, v in (t.get("variables", {}) or {}).items():
                if isinstance(v, list) and len(v) == 3 and v[2] is True:
                    cloud_n += 1
        if cloud_n > 10:
            errors.append("云变量 %d 个，超过 Scratch 3.0 上限 10 个" % cloud_n)
        elif cloud_n:
            warnings.append("包含 %d 个云变量" % cloud_n)
        return errors, warnings, proj


def _check_primitive(opcode, iname, ival):
    """校验输入里的基元结构，重点抓「变量名被二次编码」这类错误。"""
    errs = []
    if len(ival) < 2:
        return errs
    prim = ival[1]
    if isinstance(prim, list) and len(prim) >= 1:
        code = prim[0]
        if code in (12, 13):     # variable / list primitive
            name = prim[1] if len(prim) > 1 else ""
            if not isinstance(name, str):
                errs.append("积木 %s 输入 %s 的变量名不是字符串: %r" % (opcode, iname, name))
            elif name.startswith("[") or name.startswith("{"):
                errs.append("积木 %s 输入 %s 的变量名疑似被二次编码: %r" % (opcode, iname, name))
        elif code == 11:        # broadcast primitive
            if len(prim) < 3 or not isinstance(prim[2], str):
                errs.append("积木 %s 输入 %s 的广播基元缺少 id: %r" % (opcode, iname, prim))
    return errs


def _check_field(opcode, fname, fval):
    """字段值应为 [值, id]；变量/列表字段必须带合法 id。
    例外 1：自定义积木的 PROCEDURE_DEFINITION 字段存放 mutation 对象（sb3 规范如此）。
    例外 2：自定义积木参数的 VALUE 字段（argument_reporter_*）在官方 sb3 里
            写作 ["参数名"]（单元素，无 id）——与官方编辑器产物一致，不判错。"""
    errs = []
    if fname == "PROCEDURE_DEFINITION":
        if not isinstance(fval, dict):
            errs.append("积木 %s 的 PROCEDURE_DEFINITION 应为 mutation 对象: %r" % (opcode, fval))
        return errs
    if opcode in ("argument_reporter_string_number", "argument_reporter_boolean"):
        if not (isinstance(fval, list) and fval and isinstance(fval[0], str)):
            errs.append("积木 %s 字段 %s 应为 [参数名]: %r" % (opcode, fname, fval))
        return errs
    if isinstance(fval, list):
        if len(fval) != 2:
            errs.append("积木 %s 字段 %s 形态异常(应为 [值, id]): %r" % (opcode, fname, fval))
        elif fval[1] is not None and not isinstance(fval[1], str):
            errs.append("积木 %s 字段 %s 的 id 不是字符串: %r" % (opcode, fname, fval))
    elif isinstance(fval, str):
        # 广播字段允许是裸字符串
        pass
    else:
        errs.append("积木 %s 字段 %s 形态异常: %r" % (opcode, fname, fval))
    return errs


def run_runtime_check(proj_json_bytes, spec_path):
    tmp = tempfile.mkdtemp(prefix="sb3rt_")
    pj = os.path.join(tmp, "project.json")
    with open(pj, "wb") as f:
        f.write(proj_json_bytes)
    node = shutil.which("node")
    if not node:
        return None, "未找到 node，跳过运行时校验"
    env = dict(os.environ)
    # 不再写死本机路径：validate_runtime.mjs 内部会按
    # SCRATCH_VM_PATH → skill 内置 node_modules → cwd/node_modules → 本机常见位置 探测
    here = os.path.dirname(os.path.abspath(__file__))
    rt = os.path.join(here, "validate_runtime.mjs")
    try:
        r = subprocess.run([node, rt, pj], capture_output=True, text=True,
                           env=env, timeout=120)
    except Exception as e:
        return None, "运行时校验异常: %s" % e
    out = (r.stdout + r.stderr).strip()
    # 缺 scratch-vm 时脚本会输出 SKIP_RUNTIME 并以 0 退出 —— 判定为「跳过」而非「失败」
    if out.startswith("SKIP_RUNTIME"):
        return None, out
    return r.returncode == 0, out


def run_schema_check(proj_json_bytes):
    """用官方 sb3 JSON Schema 校验 project.json（scratch-parser 官方规范）。"""
    tmp = tempfile.mkdtemp(prefix="sb3schema_")
    pj = os.path.join(tmp, "project.json")
    with open(pj, "wb") as f:
        f.write(proj_json_bytes)
    node = shutil.which("node")
    if not node:
        return None, "未找到 node，跳过官方 schema 校验"
    here = os.path.dirname(os.path.abspath(__file__))
    sc = os.path.join(here, "validate_schema.mjs")
    if not os.path.exists(sc):
        return None, "未找到 validate_schema.mjs，跳过官方 schema 校验"
    try:
        r = subprocess.run([node, sc, pj], capture_output=True, text=True, timeout=120)
    except Exception as e:
        return None, "官方 schema 校验异常: %s" % e
    out = (r.stdout + r.stderr).strip()
    if out.startswith("SKIP_SCHEMA"):
        return None, out
    return r.returncode == 0, out


def run_parser_check(sb3_path):
    """用官方 scratch-parser 校验「编辑器能不能打开这个 sb3」。

    Scratch 编辑器打开项目走的就是 scratch-parser 的 validate()。
    结构非法时 parser 会拒绝并回退到 SB1 解析，报出
    "Non-ascii character in FixedAsciiString" 这种看似无关的错。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    sc = os.path.join(here, "validate_parser.mjs")
    if not os.path.exists(sc):
        return None, "未找到 validate_parser.mjs，跳过"
    node = shutil.which("node")
    if not node:
        return None, "未找到 node，跳过 scratch-parser 校验"
    try:
        r = subprocess.run([node, sc, sb3_path], capture_output=True, text=True, timeout=120)
    except Exception as e:
        return None, "scratch-parser 校验异常: %s" % e
    out = (r.stdout + r.stderr).strip()
    if out.startswith("SKIP_PARSER"):
        return None, out
    return r.returncode == 0, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sb3", required=True)
    ap.add_argument("--spec", default=None)
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    spec_path = args.spec or os.path.join(here, "..", "references", "blocks-spec.json")
    spec = None
    if os.path.exists(spec_path):
        with open(spec_path, encoding="utf-8") as f:
            spec = json.load(f)

    errors, warnings, proj = validate_structure(args.sb3, spec)
    for w in warnings:
        print("  [warn]", w)
    if errors:
        for e in errors:
            print("  [fail]", e)
        print("校验未通过")
        sys.exit(STATUS_FAIL)

    print("结构校验通过: %s" % args.sb3)
    n_blocks = sum(len(t.get("blocks", {})) for t in proj.get("targets", []))
    print("  targets=%d blocks=%d extensions=%s" % (
        len(proj.get("targets", [])), n_blocks, proj.get("extensions")))

    # 官方 JSON Schema 校验
    with zipfile.ZipFile(args.sb3) as z:
        pj = z.read("project.json")
    ok, info = run_schema_check(pj)
    if ok is None:
        print("  [skip] 官方 schema 校验: %s" % info)
    elif ok:
        print("  [ok] 官方 schema 校验: %s" % info)
    else:
        print("  [fail] 官方 schema 校验: %s" % info)
        sys.exit(STATUS_FAIL)

    # 官方 scratch-parser 校验（编辑器能不能打开）
    ok, info = run_parser_check(args.sb3)
    if ok is None:
        print("  [skip] scratch-parser 校验: %s" % info)
    elif ok:
        print("  [ok] scratch-parser 校验: %s" % info)
    else:
        print("  [fail] scratch-parser 校验: %s" % info)
        sys.exit(STATUS_FAIL)

    # 运行时校验
    ok, info = run_runtime_check(pj, spec_path)
    if ok is None:
        print("  [skip] 运行时校验: %s" % info)
    elif ok:
        print("  [ok] 运行时校验: %s" % info)
    else:
        print("  [fail] 运行时校验: %s" % info)
        sys.exit(STATUS_FAIL)
    print("全部校验通过 ✅")


if __name__ == "__main__":
    main()
