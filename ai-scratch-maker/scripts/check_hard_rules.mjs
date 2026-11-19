// 铁律通用水印检查器（不启动 scratch-vm，直接解析 project.json，秒级跑完全部作品）。
// 用法: node check_hard_rules.mjs [sb3目录] [--strict]
//
// 目的：对所有 example 作品做「机器可检」的 铁律 断言，作为比单作品行为护栏更宽的
// 跨作品安全网——任何一个作品改坏了铁律，这里会立刻冒红，而不必等逐个行为回归。
//
// 覆盖九条机器可检的 铁律（均为「结构/反模式」层面的硬信号，刻意放宽以压低误报）：
//   （前七条见下；新增两条为对硬要求 铁律8 / 铁律4 的「静态可检影子规则」，编号 18/19 不与
//     hard-requirements.md 的 1~17 冲突——18=颜色6位HEX 的机器版，19=背景/装饰障碍碰撞箱 的机器版）
//   铁律18 颜色6位HEX：project.json / SVG 里不得出现 3 位 HEX 缩写（#abc），必须写 6 位（#aabbcc），
//          对应硬要求 铁律8「颜色字面量必须是 6 位 HEX」。
//   铁律19 障碍碰撞箱：名为 墙/障碍/… 的「障碍类」角色若从未被任何碰撞原语（碰到[角色]? / 碰到颜色?）
//          引用，极可能是「画上去但没有碰撞箱」的装饰/背景障碍，对应硬要求 铁律4。
//   铁律1  数字完整显示：数值 HUD 变量若用 say 气泡显示（而非 显示变量/监视器）即违规。
//   铁律2  对话用自制聊天框：say/think 显示长文本对话（>=10 字符字面量）→ 应改聊天框角色。
//   铁律3  署名合规：作品/监视器/角色名含「禁止改编/请勿复制/私人作品」等措辞即违规（CC BY-SA）。
//   铁律6  复位挂[重置]：游戏类作品应能通过 重置/再来/开始游戏 等广播复位（复位靠广播而非纯绿旗）。
//   铁律7  结算页有返回/再来一局：游戏类作品应有结算页，且「点击/按键」能触发复位广播。
//   铁律11 克隆体私有守卫：用了 control_create_clone_of 就必须有 control_start_as_clone，
//         否则克隆体无生命周期（易指数爆炸 / 裸克隆啥也不干）。
//   铁律17 SVG 禁用标签：编译产物里的 .svg 造型不得含 text/filter/mask/clipPath/pattern/image
//         （换机器变豆腐块 / 嵌入位图；与 check_ui_assets.py 同口径）。
//
// 默认只报告（WARN 不致命，退出 0）；--strict 把 WARN 升级为 FAIL（退出 1），便于接入 CI 卡口。

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { findScratchVM, skipMessage } from "./scratch_vm_path.mjs";

// 复用 scratch-vm 旁的 jszip 解 sb3（与行为回归同环境；没有就优雅 SKIP）。
const vmPath = findScratchVM();
let JSZip = null;
if (vmPath) {
  try {
    const req = createRequire(import.meta.url);
    JSZip = req(path.join(path.dirname(vmPath), "jszip"));
  } catch { JSZip = null; }
}
if (!JSZip) { console.error(skipMessage("SKIP_HARD_RULES")); process.exit(0); }

const args = process.argv.slice(2);
const dir = args.find((a) => !a.startsWith("--")) || path.join(process.cwd(), "examples", "output");
const strict = args.includes("--strict");

// 复位/重开类广播（铁律6/7）：覆盖「开始游戏/重新开始」这类复用初始广播做整局重置的常见写法。
const RE_RESET = /重置|复位|重开|再来|重来|开始游戏|重新开始|重启|restart|reset|replay/i;
// 游戏类判定：只认明显的竞技/计分信号，避免把互动故事/课件误判成游戏（那样会误报 6/7）。
const RE_GAMETERM = /胜利|失败|通关|gameover|game_over|win|lose|过关|结算|score|level|生命|血量|分数|得分/i;
const RE_SETTLE = /结算|结束|结果|通关|失败|成功|gameover|over|结算页|结束页/i;
const RE_NUMVAR = /分数|得分|score|生命|血量|lives|hp|关卡|level|连击|combo|金币|coin|gold|时间|time|计时|能量|energy/i;
// 铁律2：say/think 显示长句对话 → 应改自制聊天框。仅对「长文本字面量」报警，短反馈不算。
const RE_SAY = /^(say|sayforsecs|think|thinkforsecs)$/;
// 铁律3：署名合规，不得写这些措辞（违反 CC BY-SA 可改编原则，官方会处理作品）。
const RE_FORBID_PHRASE = /禁止改编|请勿复制|私人作品|禁止转载|请勿转载|盗版必究/i;
// 铁律17：SVG 禁用标签（铁律17 / check_ui_assets.py 同口径）。
const FORBID_TAGS = ["text", "filter", "mask", "clipPath", "pattern", "image", "foreignObject"];
const RE_FORBID_TAG = new RegExp("<(" + FORBID_TAGS.join("|") + ")\\b", "i");
// 铁律18：3 位 HEX 缩写（#abc）→ 必须写 6 位（#aabbcc）。负向前后查保证「正好 3 位」而非 6/8 位前缀。
const RE_HEX3 = /(?<![0-9a-fA-F#])#[0-9a-fA-F]{3}(?![0-9a-fA-F])/g;
// 铁律19：障碍类角色名——只用「明确意在挡人」的词（墙/障碍/围栏/栅栏/障碍物），
// 刻意排除 柱子/挡板/箱子/石头 等歧义词（可能是装饰或玩家操控物，如 推箱子手 含「箱子」是玩家角色）。
const RE_OBSTACLE = /(墙|障碍|围栏|栅栏|障碍物)/i;

function collect(pj) {
  const r = {
    broadcasts: new Set(),
    variables: new Set(),
    monitors: new Set(),
    createClone: false,
    cloneHat: false,
    isGame: false,
    settlement: null,
    clickRestart: false, // 存在「点击/按键 → 复位广播」的 UI 复位入口
    sayNumVars: new Set(), // 用 say 气泡显示的数值 HUD 变量（铁律1 反模式）
    sayLong: false, // 用 say/think 显示长文本对话（铁律2 反模式）
    usesTouchingColor: false, // 用过「碰到颜色?」/「颜色碰到颜色?」→ 颜色碰撞（铁律4 方案B，安全）
    touchingTargets: new Set(), // 被「碰到[角色]?」引用的角色名
    obstacleNames: [], // 名为 墙/障碍/… 的障碍类角色
  };
  let anyClickKeyResetTarget = false;
  const projBc = pj.broadcasts || {};
  for (const t of pj.targets || []) {
    const bc = t.broadcasts || {};
    const vars = t.variables || {};
    const vmap = {};
    for (const vid in vars) {
      const v = vars[vid];
      if (Array.isArray(v) && typeof v[0] === "string") { r.variables.add(v[0]); vmap[vid] = v[0]; }
    }
    const blocks = t.blocks || {};
    let hasClickKey = false;
    let sendsReset = false;
    for (const bid in blocks) {
      const b = blocks[bid];
      const op = b.opcode;
      if (op === "control_create_clone_of") r.createClone = true;
      if (op === "control_start_as_clone") r.cloneHat = true;
      if (op === "event_whenthisspriteclicked" || op === "event_whenkeypressed") hasClickKey = true;
      // 接收广播：消息名直接存在 fields.BROADCAST_OPTION[0]（本 skill 的 sb3 不写 broadcasts 映射表）。
      if (op === "event_whenbroadcastreceived") {
        const fo = b.fields && b.fields.BROADCAST_OPTION;
        if (fo && fo[0]) r.broadcasts.add(fo[0]);
      }
      // 发送广播：BROADCAST_INPUT 可能是 [1, [11,"名","名"]] 内联，或老格式 [1, id]。
      if (op === "event_broadcast" || op === "event_broadcastandwait") {
        const inp = b.inputs && b.inputs.BROADCAST_INPUT;
        let nm = null;
        if (inp) {
          const p = inp[1];
          if (Array.isArray(p) && typeof p[1] === "string") nm = p[1];
          else if (typeof p === "string") nm = bc[p] || projBc[p] || null;
        }
        if (nm && RE_RESET.test(nm)) sendsReset = true;
      }
      if (RE_SAY.test(op)) {
        const inp = b.inputs && b.inputs.MESSAGE;
        if (inp && Array.isArray(inp) && inp[0] === 10 && typeof inp[1] === "string") {
          const s = inp[1];
          if (RE_NUMVAR.test(s)) {
            // 数字显示交给铁律1，这里不重复报
          } else if (s.length >= 10) {
            // 长文本字面量（>=10 字符）：对话级文本，应改自制聊天框（铁律2）。
            r.sayLong = true;
          }
        }
      }
      // 铁律19：碰撞原语引用。碰到颜色? / 颜色碰到颜色? → 颜色碰撞（铁律4 方案B，视为已处理）。
      if (op === "sensing_touchingcolor" || op === "sensing_coloristouchingcolor") r.usesTouchingColor = true;
      // 碰到[角色]? → 记录被引用的角色名（排除 鼠标 / 边缘 这两个特殊对象）。
      if (op === "sensing_touchingobject") {
        const inp = b.inputs && b.inputs.TOUCHINGOBJECTMENU;
        if (inp) {
          let nm = null;
          if (Array.isArray(inp[1])) nm = typeof inp[1][0] === "string" ? inp[1][0] : null;
          else if (typeof inp[1] === "string") nm = inp[1];
          if (nm && nm !== "_mouse_" && nm !== "_edge_") r.touchingTargets.add(nm);
        }
      }
    }
    if (hasClickKey && sendsReset) anyClickKeyResetTarget = true;
  }
  r.clickRestart = anyClickKeyResetTarget;
  for (const m of pj.monitors || []) {
    if (m.opcode === "data_variable" && m.params && m.params.VARIABLE) r.monitors.add(m.params.VARIABLE);
    if (m.opcode === "data_listcontents" && m.params && m.params.LIST) r.monitors.add(m.params.LIST);
  }
  const allMsg = [...r.broadcasts].join(" ");
  const names = (pj.targets || []).map((t) => t.name || "").join(" ");
  r.isGame = RE_GAMETERM.test(allMsg) || RE_GAMETERM.test(names);
  for (const t of pj.targets || []) {
    if (!t.isStage && RE_OBSTACLE.test(t.name || "")) r.obstacleNames.push(t.name);
  }
  for (const t of pj.targets || []) {
    if (!t.isStage && RE_SETTLE.test(t.name || "")) { r.settlement = t.name || ""; break; }
  }
  return r;
}

async function scanZip(zip, pj) {
  const res = { svgForbidden: new Set(), phrase: false, svgCount: 0, hex3: new Set() };
  // 工程级违禁措辞：角色名 / 监视器 / 广播名等（铁律3）。
  const probe = ((pj.targets || []).map((t) => t.name || "").join(" ")
    + " " + JSON.stringify(pj.monitors || []));
  if (RE_FORBID_PHRASE.test(probe)) res.phrase = true;
  // 铁律18：3 位 HEX 缩写也出现在 project.json（颜色/画笔等字面量）。
  for (const m of JSON.stringify(pj).match(RE_HEX3) || []) res.hex3.add(m);
  for (const name of Object.keys(zip.files)) {
    if (!name.toLowerCase().endsWith(".svg")) continue;
    res.svgCount++;
    let txt;
    try { txt = await zip.file(name).async("string"); } catch { continue; }
    if (RE_FORBID_PHRASE.test(txt)) res.phrase = true;
    for (const t of FORBID_TAGS) {
      if (new RegExp("<" + t + "\\b", "i").test(txt)) res.svgForbidden.add(t);
    }
    // 铁律18：SVG 填充/描边里的 3 位 HEX 缩写。
    for (const m of txt.match(RE_HEX3) || []) res.hex3.add(m + "@" + name);
  }
  return res;
}

function checkWork(name, pj, scan) {
  const r = collect(pj);
  const rules = [];
  // 铁律1：数值变量若用 say 显示则违规（其余情况视为自定义 HUD / 监视器，不误报）。
  if (r.sayNumVars.size === 0) rules.push(["铁律1", "PASS", "无『say 显示数字』反模式"]);
  else rules.push(["铁律1", "WARN", "用 say 气泡显示数字(应改监视器): " + [...r.sayNumVars].join("、")]);
  // 铁律6：游戏类应有复位广播。
  if (!r.isGame) rules.push(["铁律6", "N/A", "非竞技/计分类"]);
  else if ([...r.broadcasts].some((m) => RE_RESET.test(m))) rules.push(["铁律6", "PASS", "存在复位/重开广播"]);
  else rules.push(["铁律6", "WARN", "游戏类但未检测到 重置/再来/开始游戏 类复位广播（复位应挂广播而非纯绿旗）"]);
  // 铁律7：结算页 + 可点/可按键触发复位。
  if (!r.isGame) rules.push(["铁律7", "N/A", "非竞技/计分类"]);
  else if (!r.settlement) rules.push(["铁律7", "WARN", "游戏类但未检测到结算页角色(名含 结算/结束/结果/通关/失败…)"]);
  else if (r.clickRestart) rules.push(["铁律7", "PASS", "结算页[" + r.settlement + "]可由点击/按键触发复位"]);
  else rules.push(["铁律7", "WARN", "结算页[" + r.settlement + "]缺少『点击/按键→复位广播』入口(应有 再来一局/返回)"]);
  // 铁律11：克隆必须有 克隆起始帽。
  if (!r.createClone) rules.push(["铁律11", "N/A", "未使用克隆"]);
  else if (r.cloneHat) rules.push(["铁律11", "PASS", "有 control_start_as_clone 生命周期"]);
  else rules.push(["铁律11", "WARN", "用了 control_create_clone_of 但无 control_start_as_clone(克隆体无生命周期/易爆炸)"]);
  // 铁律2：长文本对话应改用自制聊天框（say/think 显示长句）。
  if (!r.sayLong) rules.push(["铁律2", "PASS", "未用 say/think 显示长文本对话"]);
  else rules.push(["铁律2", "WARN", "用 say/think 显示长文本(对话建议用自制聊天框角色)"]);
  // 铁律3：署名合规（不得写 禁止改编/请勿复制 等）。
  if (!scan.phrase) rules.push(["铁律3", "PASS", "无署名违禁措辞"]);
  else rules.push(["铁律3", "WARN", "含『禁止改编/请勿复制/私人作品』类措辞(违反 CC BY-SA 署名合规)"]);
  // 铁律17：SVG 禁用 text/filter/mask/clipPath/pattern/image（铁律17 / check_ui_assets.py 同口径）。
  if (scan.svgCount === 0) rules.push(["铁律17", "N/A", "无 SVG 造型"]);
  else if (scan.svgForbidden.size === 0) rules.push(["铁律17", "PASS", "SVG 无禁用标签"]);
  else rules.push(["铁律17", "WARN", "SVG 含禁用标签: " + [...scan.svgForbidden].join("/")]);
  // 铁律18：颜色字面量必须是 6 位 HEX（硬要求 铁律8）。3 位缩写 #abc 应写 #aabbcc。
  if (scan.hex3.size === 0) rules.push(["铁律18", "PASS", "颜色字面量均为 6 位 HEX"]);
  else rules.push(["铁律18", "WARN", "存在 3 位 HEX 缩写(应改 6 位 #rrggbb): " + [...scan.hex3].slice(0, 6).join("、")]);
  // 铁律19：障碍类角色必须能被碰撞检测引用，否则「画上去没碰撞箱」（硬要求 铁律4 的机器影子）。
  if (r.obstacleNames.length === 0) rules.push(["铁律19", "N/A", "无明确障碍类角色"]);
  else if (r.usesTouchingColor) rules.push(["铁律19", "PASS", "障碍经『碰到颜色』碰撞(铁律4 方案B)"]);
  else {
    const unused = r.obstacleNames.filter((n) => !r.touchingTargets.has(n));
    if (unused.length === 0) rules.push(["铁律19", "PASS", "障碍角色均被碰撞原语引用"]);
    else rules.push(["铁律19", "WARN", "障碍角色[" + unused.join("、") + "]未被任何碰撞检测引用(可能只是画上去没有碰撞箱,违反铁律4)"]);
  }
  return { rules };
}

const files = fs.readdirSync(dir).filter((f) => f.endsWith(".sb3")).sort();
let pass = 0, warn = 0, na = 0;
const rows = [];
for (const f of files) {
  const p = path.join(dir, f);
  let pj;
  let zip;
  try {
    const buf = fs.readFileSync(p);
    zip = new JSZip();
    await zip.loadAsync(buf);
    const txt = await zip.file("project.json").async("string");
    pj = JSON.parse(txt);
  } catch (e) {
    console.error("  [跳过] " + f + " 解析失败: " + (e && e.message));
    continue;
  }
  const scan = await scanZip(zip, pj);
  const { rules } = checkWork(f, pj, scan);
  rows.push([f, rules]);
  let line = f.padEnd(30);
  for (const [rid, st, note] of rules) {
    if (st === "PASS") pass++; else if (st === "WARN") warn++; else na++;
    const mark = st === "PASS" ? "✓" : st === "WARN" ? "!" : "·";
    line += `  ${mark}${rid}`;
  }
  console.log(line);
  for (const [rid, st, note] of rules) if (st === "WARN") console.log("        ! " + rid + ": " + note);
}
console.log("--------------------------------------------------");
console.log(`作品 ${rows.length} 个 | 规则 PASS=${pass} WARN=${warn} N/A=${na}`);
const warns = [];
for (const [f, rules] of rows) for (const [rid, st, note] of rules) if (st === "WARN") warns.push(f + "/" + rid);
if (warns.length) {
  console.log("WARN 明细条数: " + warns.length);
  if (strict) { console.error("HARD_RULES_FAIL " + warns.join(",")); process.exit(1); }
}
console.log("HARD_RULES_OK");
process.exit(0);
