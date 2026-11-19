"""IR 加载与校验（AI 生成的中间表示 -> Python dict）。

在编译成 .sb3 之前就把「积木名写错」「云变量超限」「脚本没有帽子积木」这类问题
报出来，避免浪费一次编译+运行时的往返。
"""
import json
import os

import yaml

# 帽子积木（脚本的起始块）
HAT_OPCODES = {
    "event_whenflagclicked", "event_whenbroadcastreceived", "event_whenkeypressed",
    "event_whenstageclicked", "event_whenthisspriteclicked",
    "event_whenbackdropswitchesto", "event_whengreaterthan",
    "control_start_as_clone", "procedures_definition",
    "videoSensing_whenMotionGreaterThan", "speech2text_whenIHearHat",
}

CLOUD_LIMIT = 10


def load_spec(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_ir(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_ir_marked(path):
    """加载 IR 并同时记录每个 dict/list 节点在源文件里的行号。

    返回 (ir, marks)，marks 是 {id(obj): line}。validate_ir 用 marks
    把报错定位到具体行号，而不只是 'sprites[3].scripts[0]' 这种路径。
    （dict/list 是独立对象、id 稳定；标量不记——标量也不需要行号。）
    """
    marks = {}

    class _LineLoader(yaml.SafeLoader):
        pass

    def _co(self, node, deep=False):
        # construct_object 是所有节点（mapping / sequence / scalar）的统一入口，
        # 在这里标记 dict/list 的起始行，能覆盖脚本里「第二个及以后的积木」等
        # 会被 construct_sequence 内部以其它路径构造的节点。
        obj = yaml.SafeLoader.construct_object(self, node, deep=deep)
        if isinstance(obj, (dict, list)):
            marks[id(obj)] = node.start_mark.line + 1
        return obj

    _LineLoader.construct_object = _co
    with open(path, encoding="utf-8") as f:
        ir = yaml.load(f, Loader=_LineLoader)
    return ir, marks


def _lev(a, b):
    """Levenshtein 编辑距离（用于「你是不是想写 X」近似建议）。"""
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]


def _suggest(name, known, maxd=4, topn=3):
    """从已知积木名里挑最接近 name 的几个（编辑距离 ≤ maxd）。"""
    if not known:
        return []
    scored = sorted((_lev(name, k), k) for k in known)
    out = []
    for d, k in scored:
        if d == 0 or d > maxd:
            continue
        out.append(k)
        if len(out) >= topn:
            break
    return out


def _resolve(name, spec):
    blocks = spec.get("blocks") or {}
    if name in blocks:
        return name
    aliases = spec.get("aliases") or {}
    if name in aliases:
        return aliases[name]
    # 编译期展开的伪积木（chat_say/safe_spawn）：build 的 expand_display_scripts 会改写成
    # 真实积木，校验阶段必须放行，否则含这些写法的作品（如 cat_mouse）会被误判未知积木。
    if name in PSEUDO_BLOCKS:
        return name
    return None


def _split_block(blk):
    """拆出 (积木名, 值)。支持多键写法 {forever: null, do: [...]}。"""
    if not isinstance(blk, dict) or not blk:
        return None, None
    keys = list(blk.keys())
    name = keys[0]
    if len(keys) == 1:
        return name, blk[name]
    merged = {}
    base = blk[name]
    if isinstance(base, dict):
        merged.update(base)
    for k in keys[1:]:
        merged[k] = blk[k]
    return name, merged


def _walk_blocks(items, spec, path, errs, require_hat=False, marks=None, known=None):
    """遍历脚本中的积木，校验名字；顶层脚本要求以帽子积木开头。"""
    if not isinstance(items, list):
        return
    for i, blk in enumerate(items):
        ln = marks.get(id(blk)) if marks else None
        pre = ("第%d行 " % ln) if ln else ""
        name, val = _split_block(blk)
        if name is None:
            errs.append("%s%s[%d]: 每个积木必须写成 {积木名: 值}，实际是 %r" % (pre, path, i, blk))
            continue
        opcode = _resolve(name, spec)
        if opcode is None:
            sug = _suggest(name, known) if known else []
            extra = ("；你是不是想写：" + " / ".join(sug)) if sug else ""
            errs.append("%s%s[%d]: 未知积木名 %r（查 references/blocks.md）%s"
                        % (pre, path, i, name, extra))
            continue
        if require_hat and i == 0:
            # 只有「帽子积木」会在绿旗/广播/按键时启动脚本。
            # scratch-vm 的 runtime.greenFlag() 只 startHats('event_whenflagclicked')，
            # 顶层放一个裸的 forever 不会报错，但**永远不会被执行** —— 静默失效。
            if opcode not in HAT_OPCODES:
                errs.append(
                    "%s%s[0]: 脚本必须以帽子积木开头，%r 不是帽子积木"
                    "（顶层裸积木不会被绿旗启动）。可选帽子：%s"
                    % (pre, path, name, "、".join(sorted(HAT_OPCODES))))
        if opcode in ("procedures_definition", "procedures_prototype"):
            errs.append("%s%s[%d]: 请改用 target.procedures 声明自定义积木" % (pre, path, i))
            continue
        # 递归子栈（子栈里的块不需要是帽子积木）
        if isinstance(val, dict):
            for key in ("do", "else"):
                if key in val:
                    _walk_blocks(val[key], spec, "%s[%d].%s" % (path, i, key),
                                 errs, False, marks, known)
            for k, v in val.items():
                if k in ("do", "else"):
                    continue
                _walk_expr(v, spec, "%s[%d].%s" % (path, i, k), errs, marks, known)


def _looks_like_block(node, spec):
    """判断一个 dict/list 是否「看起来像一个嵌套积木」（而非输入名→字面量的映射）。

    IR 里输入名 a/b/operand 等的值是字面量（{a: 1}）或变量引用，若把它们当成积木
    遍历会把输入名误判成积木名——典型坑：not:{equals:{a:1,b:2}} 会把 'a' 当积木。
    只有「首键能解析成已知积木名」的 dict（如 {equals:{a:1,b:2}}、{add:[..]}）才下钻。
    """
    if isinstance(node, dict):
        if "var" in node or "list" in node:
            return False
        name, _ = _split_block(node)
        return name is not None and _resolve(name, spec) is not None
    if isinstance(node, list):
        return any(_looks_like_block(item, spec) for item in node)
    return False


def _walk_expr(node, spec, path, errs, marks=None, known=None):
    """遍历表达式（嵌套积木）。"""
    if isinstance(node, dict):
        if "var" in node or "list" in node:
            return
        name, val = _split_block(node)
        if name is None:
            return
        if _resolve(name, spec) is None:
            ln = marks.get(id(node)) if marks else None
            pre = ("第%d行 " % ln) if ln else ""
            sug = _suggest(name, known) if known else []
            extra = ("；你是不是想写：" + " / ".join(sug)) if sug else ""
            errs.append("%s%s: 未知积木名 %r%s" % (pre, path, name, extra))
            return
        if isinstance(val, dict):
            for k, v in val.items():
                if _looks_like_block(v, spec):
                    _walk_expr(v, spec, "%s.%s" % (path, k), errs, marks, known)
        elif isinstance(val, list):
            for j, v in enumerate(val):
                if _looks_like_block(v, spec):
                    _walk_expr(v, spec, "%s[%d]" % (path, j), errs, marks, known)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if _looks_like_block(v, spec):
                _walk_expr(v, spec, "%s[%d]" % (path, i), errs, marks, known)


def _check_target(tdef, spec, label, errs, marks=None, known=None):
    variables = tdef.get("variables") or {}
    lists = tdef.get("lists") or {}
    tln = marks.get(id(tdef)) if marks else None
    tpre = ("第%d行 " % tln) if tln else ""
    # 官方 sb3 规范：每个 target 至少要有一个 costume
    # digit_display / chat_box / list_display 会自动补齐造型，所以也算有造型
    auto_costumes = (tdef.get("digit_display") or tdef.get("chat_box")
                     or tdef.get("list_display"))
    if not (tdef.get("costumes") or tdef.get("backdrops") or auto_costumes):
        errs.append("%s%s: 至少要有一个造型（舞台用 backdrops，角色用 costumes）" % (tpre, label))
    # chat_box 必须写明台词数
    ccfg = tdef.get("chat_box")
    if ccfg is not None:
        if not isinstance(ccfg, dict) or not ccfg.get("lines"):
            errs.append("%s%s.chat_box: 必须写明 lines（共有几句台词）" % (tpre, label))
    # list_display 必须写明列表和取哪一项
    lcfg = tdef.get("list_display")
    if lcfg is not None:
        if not isinstance(lcfg, dict) or not lcfg.get("list"):
            errs.append("%s%s.list_display: 必须写明 list（哪个列表）" % (tpre, label))
        elif not (lcfg.get("list_index") or lcfg.get("list_length")):
            errs.append("%s%s.list_display: 必须写明 list_index（第几项）或 list_length（长度）"
                        % (tpre, label))
    # 监视器（屏幕读数）引用的变量必须存在
    for i, m in enumerate(tdef.get("monitors") or []):
        mln = marks.get(id(m)) if marks else None
        mpre = ("第%d行 " % mln) if mln else ""
        if not isinstance(m, dict):
            errs.append("%s%s.monitors[%d]: 必须是 {var: 名字, x: N, y: N} 这样的对象"
                        % (mpre, label, i))
            continue
        if "var" in m:
            if str(m["var"]) not in variables:
                errs.append("%s%s.monitors[%d]: 变量 %r 不存在（应在 stage.variables 里声明）"
                            % (mpre, label, i, m["var"]))
        elif "list" in m:
            if str(m["list"]) not in lists:
                errs.append("%s%s.monitors[%d]: 列表 %r 不存在（应在 stage.lists 里声明）"
                            % (mpre, label, i, m["list"]))
        else:
            errs.append("%s%s.monitors[%d]: 缺少 var 或 list 键" % (mpre, label, i))
    cloud = 0
    for vname, vraw in variables.items():
        if isinstance(vraw, dict) and (vraw.get("cloud") or vraw.get("isCloud")):
            cloud += 1
    for lname, lraw in lists.items():
        if isinstance(lraw, dict) and (lraw.get("cloud") or lraw.get("isCloud")):
            errs.append(
                "%s%s.lists.%s: Scratch 3.0 不支持云列表（官方 sb3 规范的 list 只允许 [名字, 内容]），"
                "请改用普通列表。" % (tpre, label, lname))
    if cloud > CLOUD_LIMIT:
        errs.append("%s%s: 云变量 %d 个，超过 Scratch 3.0 上限 %d 个"
                    % (tpre, label, cloud, CLOUD_LIMIT))
    for i, script in enumerate(tdef.get("scripts") or []):
        # 行号由 _walk_blocks 在每个积木自身上加（避免重复前缀）；这里只传路径。
        _walk_blocks(script, spec, "%s.scripts[%d]" % (label, i),
                     errs, require_hat=True, marks=marks, known=known)
    for i, pdef in enumerate(tdef.get("procedures") or []):
        pln = marks.get(id(pdef)) if marks else None
        ppre = ("第%d行 " % pln) if pln else ""
        if not pdef.get("name"):
            errs.append("%s%s.procedures[%d]: 缺少 name" % (ppre, label, i))
        _walk_blocks(pdef.get("script") or [], spec,
                     "%s%s.procedures[%d].script" % (ppre, label, i),
                     errs, marks=marks, known=known)


# 编译期展开的伪积木：build 的 expand_display_scripts 会改写成真实积木，
# 校验阶段必须放行，否则含这些写法的作品（如 cat_mouse 的 chat_say）会被误判未知积木。
PSEUDO_BLOCKS = ("chat_say", "safe_spawn")


def validate_ir(ir, spec=None, marks=None):
    """结构校验，返回错误列表（空列表 = 通过）。

    marks 来自 load_ir_marked()，用于在报错里带上源文件行号；不传则只给路径。
    """
    errs = []
    if not isinstance(ir, dict) or "project" not in ir:
        return ["IR 顶层必须包含 project 键"]
    p = ir["project"]
    if not isinstance(p, dict):
        return ["project 必须是对象"]
    if "stage" not in p and "sprites" not in p:
        errs.append("project 至少需要 stage 或 sprites 之一")

    if spec is None:
        here = os.path.dirname(os.path.abspath(__file__))
        spec_path = os.path.join(here, "..", "references", "blocks-spec.json")
        if os.path.exists(spec_path):
            spec = load_spec(spec_path)

    known = set()
    if spec:
        known.update((spec.get("blocks") or {}).keys())
        known.update((spec.get("aliases") or {}).keys())
    # 编译期展开的伪积木：build 的 expand_display_scripts 会改写成真实积木，
    # 校验阶段不应当「未知积木」拦截（否则旗舰 cat_mouse 等含 chat_say 的作品无法构建）。
    known.update(PSEUDO_BLOCKS)

    if spec:
        stage = p.get("stage")
        if stage is not None:
            _check_target(stage, spec, "舞台", errs, marks, known)
        for i, sp in enumerate(p.get("sprites") or []):
            sname = sp.get("name") if isinstance(sp, dict) else None
            label = ("角色[%s]" % sname) if sname else ("sprites[%d]" % i)
            _check_target(sp, spec, label, errs, marks, known)
    return errs
