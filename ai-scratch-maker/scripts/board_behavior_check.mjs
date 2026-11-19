// 五子棋行为校验：验证棋盘表示(1维列表81格)、落子写入、换手、五连珠胜负判定、结束守卫。
// 用法: node board_behavior_check.mjs <board_gomoku.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_BOARD")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node board_behavior_check.mjs <board_gomoku.sb3>"); process.exit(2); }

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
      if (t.variables[id] && t.variables[id].name === name) { t.variables[id].value = val; return; }
};
// 列表在 builder 里是「变量存数组」：直接改数组元素（Scratch 列表 1 基 → JS 数组 0 基）
const setStageListArr = (name, i0, val) => {
  for (const t of vm.runtime.targets)
    for (const id of Object.keys(t.variables || {}))
      if (t.variables[id] && t.variables[id].name === name) { t.variables[id].value[i0] = val; return true; }
  return false;
};

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

  // A. 绿旗 → 棋盘 81 格全空，回合/胜负复位
  vm.greenFlag();
  await stepN(2);
  const board = getStageVar("棋盘");
  snap.棋盘长度 = Array.isArray(board) ? board.length : (board ? board.split(",").length : -1);
  if (snap.棋盘长度 !== 81) bad.push("棋盘长度!=81: " + snap.棋盘长度);
  const allZero = Array.isArray(board) ? board.every((v) => num(v) === 0) : String(board).split(",").every((v) => num(v) === 0);
  if (!allZero) bad.push("绿旗后棋盘未清空");
  if (num(getStageVar("轮到")) !== 1) bad.push("初始轮到!=1: " + getStageVar("轮到"));
  if (num(getStageVar("胜者")) !== 0) bad.push("初始胜者!=0: " + getStageVar("胜者"));
  if (num(getStageVar("局结束")) !== 0) bad.push("初始局结束!=0: " + getStageVar("局结束"));

  // B. 落子(4,4)：写入棋盘对应格，并换手到 2
  setStageVar("行", 4); setStageVar("列", 4);
  broadcast("落子"); await stepN(1);
  const boardB = getStageVar("棋盘");
  const cell = Array.isArray(boardB) ? num(boardB[4 * 9 + 4]) : num(String(boardB).split(",")[4 * 9 + 4]);
  snap.落子值 = cell;
  snap.落子后轮到 = num(getStageVar("轮到"));
  if (snap.落子值 !== 1) bad.push("落子未写入棋盘(4,4): " + snap.落子值);
  if (snap.落子后轮到 !== 2) bad.push("落子后未换手: 轮到=" + snap.落子后轮到);

  // C. 五连珠：预置 (0,0..3)=黑，再落 (0,4) 应判黑胜
  setStageListArr("棋盘", 0, 1); setStageListArr("棋盘", 1, 1);
  setStageListArr("棋盘", 2, 1); setStageListArr("棋盘", 3, 1);
  setStageVar("轮到", 1); setStageVar("胜者", 0); setStageVar("局结束", 0);
  setStageVar("行", 0); setStageVar("列", 4);
  broadcast("落子"); await stepN(1);
  snap.胜者 = num(getStageVar("胜者"));
  snap.局结束 = num(getStageVar("局结束"));
  const boardC = getStageVar("棋盘");
  const last = Array.isArray(boardC) ? num(boardC[0 * 9 + 4]) : num(String(boardC).split(",")[0 * 9 + 4]);
  if (last !== 1) bad.push("第五子未写入(0,4): " + last);
  if (snap.胜者 !== 1) bad.push("五连珠未判黑胜: 胜者=" + snap.胜者);
  if (snap.局结束 !== 1) bad.push("五连珠未结束: 局结束=" + snap.局结束);

  // D. 结束守卫：局结束后再次落子不改变胜负
  setStageVar("行", 8); setStageVar("列", 8);
  broadcast("落子"); await stepN(1);
  snap.胜者_后 = num(getStageVar("胜者"));
  snap.局结束_后 = num(getStageVar("局结束"));
  if (snap.胜者_后 !== 1) bad.push("结束守卫失效: 胜者被改=" + snap.胜者_后);
  if (snap.局结束_后 !== 1) bad.push("结束守卫失效: 局结束被改=" + snap.局结束_后);

  const actual = { 棋盘长度: snap.棋盘长度, 落子值: snap.落子值, 胜者: snap.胜者, 局结束: snap.局结束 };
  console.log(JSON.stringify({ actual, bad }, null, 2));
  if (bad.length) { console.error("BOARD_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("BOARD_LOGIC_OK");
})().catch((e) => { console.error("BOARD_CHECK_FAIL", e && (e.stack || e)); process.exit(1); });
