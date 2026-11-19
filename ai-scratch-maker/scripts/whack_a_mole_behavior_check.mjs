// 打地鼠 行为校验：标题态 / 开始复位 / 再来一局复位 / 结束态可达 / 回标题复位 / 关键角色。
// 用法: node whack_a_mole_behavior_check.mjs <whack_a_mole.sb3> [--json]
//
// 重点守卫「拿来当模板抄」最易回归的几处（与 cat_mouse / fruit_basket 同思路）：
//   1. 绿旗回标题态（游戏状态=0）
//   2. 开始游戏 -> 游戏态=1 + 分数/时间/关卡干净复位
//   3. 重复开始（再来一局）仍完全复位 —— 状态机复位逻辑的核心
//   4. 关键角色（地鼠 / 锤子 / 结算页 / 再来一局 / 返回首页 / 首页开始）存在
//   5. 结束态可达：广播 时间到 -> 游戏状态=2，并刷新最高分
//   6. 回标题 -> 游戏状态=0（结算页可回到首页）
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_WHACK")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node whack_a_mole_behavior_check.mjs <whack_a_mole.sb3>"); process.exit(2); }

let vm = null;
const num = (x) => (typeof x === "string" ? parseFloat(x) : x);
const getStageVar = (name) => {
  for (const t of vm.runtime.targets)
    for (const id of Object.keys(t.variables || {}))
      if (t.variables[id] && t.variables[id].name === name) return t.variables[id].value;
  return undefined;
};
const setStageVar = (name, val) => {
  for (const t of vm.runtime.targets)
    for (const id of Object.keys(t.variables || {}))
      if (t.variables[id] && t.variables[id].name === name) { t.variables[id].value = val; return true; }
  return false;
};
const spriteExists = (name) =>
  vm.runtime.targets.some((t) => t.sprite && t.sprite.name === name);

(async () => {
  vm = new VirtualMachine();
  const buf = fs.readFileSync(sb3Path);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  await vm.loadProject(ab);
  vm.runtime.currentStepTime = 1000 / 30;

  const stepN = async (n) => {
    for (let i = 0; i < n; i++) { vm.runtime.currentMSecs += 33; vm.runtime._step(); await Promise.resolve(); }
  };
  const broadcast = (msg) => vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: msg });

  const bad = [];
  const snap = {};
  const notes = [];

  // A. 绿旗 -> 回到标题态
  vm.greenFlag();
  await stepN(3);
  snap.绿旗后游戏状态 = num(getStageVar("游戏状态"));
  if (snap.绿旗后游戏状态 !== 0) bad.push("绿旗后未回标题态(游戏状态!=0): " + snap.绿旗后游戏状态);

  // B. 开始游戏 -> 进入游戏态且干净复位
  broadcast("开始游戏"); await stepN(3);
  snap.开始后游戏状态 = num(getStageVar("游戏状态"));
  snap.开始后分数 = num(getStageVar("分数"));
  snap.开始后时间 = num(getStageVar("时间"));
  snap.开始后关卡 = num(getStageVar("关卡"));
  if (snap.开始后游戏状态 !== 1) bad.push("开始后未进入游戏态: " + snap.开始后游戏状态);
  if (snap.开始后分数 !== 0) bad.push("开始后分数未复位: " + snap.开始后分数);
  if (snap.开始后时间 !== 60) bad.push("开始后时间未复位(应为60): " + snap.开始后时间);
  if (snap.开始后关卡 !== 1) bad.push("开始后关卡未复位(应为1): " + snap.开始后关卡);

  // C. 再来一局（重复开始）仍完全复位 —— 状态机复位逻辑核心守卫
  setStageVar("分数", 25); setStageVar("时间", 11); setStageVar("关卡", 4);
  broadcast("开始游戏"); await stepN(3);
  snap.重开分数 = num(getStageVar("分数"));
  snap.重开时间 = num(getStageVar("时间"));
  snap.重开关卡 = num(getStageVar("关卡"));
  snap.重开游戏状态 = num(getStageVar("游戏状态"));
  if (snap.重开分数 !== 0) bad.push("再来一局后分数未复位: " + snap.重开分数);
  if (snap.重开时间 !== 60) bad.push("再来一局后时间未复位: " + snap.重开时间);
  if (snap.重开关卡 !== 1) bad.push("再来一局后关卡未复位: " + snap.重开关卡);
  if (snap.重开游戏状态 !== 1) bad.push("再来一局后未回到游戏态: " + snap.重开游戏状态);

  // D. 关键角色存在（缺一则游戏根本跑不起来）
  for (const n of ["地鼠", "锤子", "结算页", "再来一局", "返回首页", "首页开始"])
    if (!spriteExists(n)) bad.push("缺少关键角色: " + n);

  // E. 结束态可达（直接广播 时间到 -> 游戏状态=2 并刷新最高分）；铁律7 结算态正确切换
  setStageVar("分数", 99); setStageVar("最高分", 0);
  broadcast("时间到"); await stepN(3);
  snap.结束后游戏状态 = num(getStageVar("游戏状态"));
  snap.结束后最高分 = num(getStageVar("最高分"));
  if (snap.结束后游戏状态 !== 2) bad.push("时间到后未切入结算态(游戏状态!=2): " + snap.结束后游戏状态);
  if (snap.结束后最高分 !== 99) bad.push("时间到后最高分未刷新(应为99): " + snap.结束后最高分);

  // F. 回标题 -> 游戏状态=0（结算页可回到首页，铁律7 闭环）
  broadcast("回标题"); await stepN(3);
  snap.回标题后游戏状态 = num(getStageVar("游戏状态"));
  if (snap.回标题后游戏状态 !== 0) bad.push("回标题后未回标题态(游戏状态!=0): " + snap.回标题后游戏状态);

  // 输出
  if (bad.length === 0) {
    console.log("WHACK_LOGIC_OK 状态: 标题=" + snap.绿旗后游戏状态 +
      " 开局=" + snap.开始后游戏状态 + "/分" + snap.开始后分数 + "/时" + snap.开始后时间 + "/关" + snap.开始后关卡 +
      " 重开=" + snap.重开游戏状态 + "/分" + snap.重开分数 + " 结束=" + snap.结束后游戏状态 +
      "/最高分" + snap.结束后最高分 + " 回标题=" + snap.回标题后游戏状态);
    for (const n of notes) console.log("  · note: " + n);
    process.exit(0);
  } else {
    console.log("WHACK_LOGIC_FAIL");
    for (const b of bad) console.log("  ✗ " + b);
    for (const n of notes) console.log("  · note: " + n);
    process.exit(1);
  }
})().catch((e) => { console.error("WHACK_CHECK_ERROR", e && e.message); process.exit(1); });
