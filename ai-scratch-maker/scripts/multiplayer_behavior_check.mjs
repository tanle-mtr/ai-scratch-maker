// 联机回合示例行为校验：验证「云变量是唯一的共享通道」+ 回合守卫（非己方回合忽略）。
// 用法: node multiplayer_behavior_check.mjs <multiplayer.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_MULTIPLAYER")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node multiplayer_behavior_check.mjs <multiplayer.sb3>"); process.exit(2); }

let vm = null;
const getVar = (t, name) => {
  for (const id of Object.keys(t.variables || {}))
    if (t.variables[id] && t.variables[id].name === name) return t.variables[id].value;
  return undefined;
};
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
const num = (x) => (typeof x === "string" ? parseFloat(x) : x);

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

  // A. 绿旗 → 初始状态正确
  vm.greenFlag();
  await stepN(3);
  if (num(getStageVar("本机玩家")) !== 1) bad.push("本机玩家!=1: " + getStageVar("本机玩家"));
  if (num(getStageVar("云_回合")) !== 1) bad.push("初始云_回合!=1: " + getStageVar("云_回合"));
  if (num(getStageVar("云_进度")) !== 0) bad.push("初始云_进度!=0: " + getStageVar("云_进度"));
  if (num(getStageVar("局结束")) !== 0) bad.push("初始局结束!=0: " + getStageVar("局结束"));

  // B. 轮到自己：写入共享通道（云_进度+1）并交换回合
  setStageVar("本机玩家", 1); setStageVar("云_回合", 1);
  broadcast("我的回合行动"); await stepN(1);
  snap.进度_己方 = num(getStageVar("云_进度"));
  snap.回合_己方 = num(getStageVar("云_回合"));
  if (snap.进度_己方 !== 1) bad.push("己方行动未写入云_进度: " + snap.进度_己方);
  if (snap.回合_己方 !== 2) bad.push("己方行动后未交换回合: " + snap.回合_己方);

  // C. 非己方回合：输入被忽略（云_进度/回合不变）
  setStageVar("本机玩家", 1); setStageVar("云_回合", 2);
  broadcast("我的回合行动"); await stepN(1);
  snap.进度_非己方 = num(getStageVar("云_进度"));
  snap.回合_非己方 = num(getStageVar("云_回合"));
  if (snap.进度_非己方 !== 1) bad.push("非己方回合仍写入了云_进度: " + snap.进度_非己方);
  if (snap.回合_非己方 !== 2) bad.push("非己方回合仍交换了回合: " + snap.回合_非己方);

  // D. 进度到 5 触发结束（每次都轮到自己）
  for (let i = 0; i < 5; i++) { setStageVar("云_回合", 1); broadcast("我的回合行动"); await stepN(1); }
  snap.结束 = num(getStageVar("局结束"));
  snap.最终进度 = num(getStageVar("云_进度"));
  if (snap.结束 !== 1) bad.push("进度到 5 未结束: 进度=" + snap.最终进度 + " 结束=" + snap.结束);

  const actual = { 进度_己方: snap.进度_己方, 回合_己方: snap.回合_己方, 进度_非己方: snap.进度_非己方, 结束: snap.结束 };
  console.log(JSON.stringify({ actual, bad }, null, 2));
  if (bad.length) { console.error("MULTIPLAYER_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("MULTIPLAYER_LOGIC_OK");
})().catch((e) => { console.error("MULTIPLAYER_CHECK_FAIL", e && (e.stack || e)); process.exit(1); });
