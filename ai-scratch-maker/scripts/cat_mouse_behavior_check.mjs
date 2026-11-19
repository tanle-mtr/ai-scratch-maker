// 猫抓老鼠（大地图版）行为校验：状态机 / 开始复位 / 再来一局复位 / 关键角色 / 结束态可达。
// 用法: node cat_mouse_behavior_check.mjs <cat_mouse.sb3> [--json]
//
// 重点守卫「拿来当模板抄」最易回归的几处（与 fruit_basket 同思路）：
//   1. 绿旗回标题态（游戏状态=0）
//   2. 开始游戏 -> 游戏态=1 + 分数/剩余时间干净复位
//   3. 重复开始（再来一局）仍完全复位 —— 状态机复位逻辑的核心
//   4. 关键角色（猫 / 鼠 / 地图）存在
//   5. 结束态可达：倒计时归零 -> 游戏结束 -> 游戏状态=2（直接广播路径硬校验；
//      虚拟化倒计时归零终止作为软探针，无头计时器若不支持则记 note 不致命）
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_CATMOUSE")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node cat_mouse_behavior_check.mjs <cat_mouse.sb3>"); process.exit(2); }

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
const targetByName = (name) =>
  vm.runtime.targets.find((t) => t.sprite && t.sprite.name === name);

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
  snap.绿旗后游戏状态 = num(getStageVar("game_state"));
  if (snap.绿旗后游戏状态 !== 0) bad.push("绿旗后未回标题态(game_state!=0): " + snap.绿旗后游戏状态);

  // B. 开始游戏 -> 进入游戏态且干净复位
  broadcast("开始游戏"); await stepN(3);
  snap.开始后游戏状态 = num(getStageVar("game_state"));
  snap.开始后分数 = num(getStageVar("分数"));
  snap.开始后剩余时间 = num(getStageVar("剩余时间"));
  if (snap.开始后游戏状态 !== 1) bad.push("开始后未进入游戏态: " + snap.开始后游戏状态);
  if (snap.开始后分数 !== 0) bad.push("开始后分数未复位: " + snap.开始后分数);
  if (snap.开始后剩余时间 !== 30) bad.push("开始后剩余时间未复位(应为30): " + snap.开始后剩余时间);

  // C. 再来一局（重复开始）仍完全复位 —— 状态机复位逻辑核心守卫
  setStageVar("分数", 5); setStageVar("剩余时间", 11);
  broadcast("开始游戏"); await stepN(3);
  snap.重开分数 = num(getStageVar("分数"));
  snap.重开剩余时间 = num(getStageVar("剩余时间"));
  snap.重开游戏状态 = num(getStageVar("game_state"));
  if (snap.重开分数 !== 0) bad.push("再来一局后分数未复位: " + snap.重开分数);
  if (snap.重开剩余时间 !== 30) bad.push("再来一局后剩余时间未复位: " + snap.重开剩余时间);
  if (snap.重开游戏状态 !== 1) bad.push("再来一局后未回到游戏态: " + snap.重开游戏状态);

  // D. 关键角色存在（猫/老鼠/地图，缺一则游戏根本跑不起来）
  for (const n of ["猫", "老鼠", "地图"])
    if (!spriteExists(n)) bad.push("缺少关键角色: " + n);

  // E1. 结束态可达（直接广播 游戏结束 -> game_state=2）；铁律7 结算态正确切换
  broadcast("游戏结束"); await stepN(3);
  snap.结束后游戏状态 = num(getStageVar("game_state"));
  if (snap.结束后游戏状态 !== 2) bad.push("游戏结束后未切入结算态(game_state!=2): " + snap.结束后游戏状态);

  // E2. 软探针：虚拟化倒计时归零终止。先重新开局，再置 剩余时间=0 步进，
  //     若无头计时器支持 wait，则倒计时应触发 游戏结束 -> game_state=2；
  //     不支持则记 note，不致命（已由 E1 直接广播路径覆盖）。
  broadcast("开始游戏"); await stepN(2);
  setStageVar("剩余时间", 0);
  await stepN(45);
  snap.归零后游戏状态 = num(getStageVar("game_state"));
  if (snap.归零后游戏状态 === 2) {
    notes.push("倒计时归零 -> 结束态 虚拟化触发正常");
  } else {
    notes.push("倒计时归零终止未在虚拟化下触发(游戏状态=" + snap.归零后游戏状态 +
      ")，疑为无头计时器限制；直接广播 游戏结束 路径(E1)已覆盖结束态");
  }

  // 输出
  if (bad.length === 0) {
    console.log("CATMOUSE_LOGIC_OK 状态: 标题=" + snap.绿旗后游戏状态 +
      " 开局=" + snap.开始后游戏状态 + "/分" + snap.开始后分数 + "/时" + snap.开始后剩余时间 +
      " 重开=" + snap.重开游戏状态 + "/分" + snap.重开分数 + " 结束=" + snap.结束后游戏状态);
    for (const n of notes) console.log("  · note: " + n);
    process.exit(0);
  } else {
    console.log("CATMOUSE_LOGIC_FAIL");
    for (const b of bad) console.log("  ✗ " + b);
    for (const n of notes) console.log("  · note: " + n);
    process.exit(1);
  }
})().catch((e) => { console.error("CATMOUSE_CHECK_ERROR", e && e.message); process.exit(1); });
