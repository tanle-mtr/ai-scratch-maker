// 第一人称迷宫行为校验：验证「射线探测正前方墙/越界」+「撞墙不移动、空地才移动」+「转向」。
// 用法: node firstperson_behavior_check.mjs <firstperson.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_FP")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node firstperson_behavior_check.mjs <firstperson.sb3>"); process.exit(2); }

let vm = null;
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

  vm.greenFlag();
  await stepN(2);
  if (num(getStageVar("px")) !== 1 || num(getStageVar("py")) !== 1) bad.push("起点不对: " + getStageVar("px") + "," + getStageVar("py"));
  if (num(getStageVar("pdir")) !== 0) bad.push("初始朝向不对: " + getStageVar("pdir"));

  // B. 朝西(pdir=180)：正前方(0,1)是边界墙 → 前方墙=1
  setStageVar("pdir", 180);
  broadcast("探测"); await stepN(1);
  snap.墙_西 = num(getStageVar("前方墙"));
  if (snap.墙_西 !== 1) bad.push("朝西未探测到边界墙: 前方墙=" + snap.墙_西);

  // C. 朝东(pdir=0)：正前方(2,1)是地板 → 前方墙=0
  setStageVar("pdir", 0);
  broadcast("探测"); await stepN(1);
  snap.墙_东 = num(getStageVar("前方墙"));
  if (snap.墙_东 !== 0) bad.push("朝东误判为墙: 前方墙=" + snap.墙_东);

  // D. 撞墙不移动：朝西(墙)前进 → px 不变
  setStageVar("pdir", 180); setStageVar("px", 1);
  broadcast("探测"); await stepN(1);
  broadcast("前进"); await stepN(1);
  snap.px_撞墙 = num(getStageVar("px"));
  if (snap.px_撞墙 !== 1) bad.push("撞墙仍移动了: px=" + snap.px_撞墙);

  // E. 空地才移动：朝东(地板)前进 → px 变 2
  setStageVar("pdir", 0); setStageVar("px", 1);
  broadcast("探测"); await stepN(1);
  broadcast("前进"); await stepN(1);
  snap.px_空地 = num(getStageVar("px"));
  if (snap.px_空地 !== 2) bad.push("空地前进未移动: px=" + snap.px_空地);

  // F. 转向：左转 90°（0→90）
  setStageVar("pdir", 0);
  broadcast("左转"); await stepN(1);
  snap.pdir_左转 = num(getStageVar("pdir"));
  if (snap.pdir_左转 !== 90) bad.push("左转未生效: pdir=" + snap.pdir_左转);

  const actual = { 墙_西: snap.墙_西, 墙_东: snap.墙_东, px_撞墙: snap.px_撞墙, px_空地: snap.px_空地, pdir_左转: snap.pdir_左转 };
  console.log(JSON.stringify({ actual, bad }, null, 2));
  if (bad.length) { console.error("FP_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("FP_LOGIC_OK");
})().catch((e) => { console.error("FP_CHECK_FAIL", e && (e.stack || e)); process.exit(1); });
