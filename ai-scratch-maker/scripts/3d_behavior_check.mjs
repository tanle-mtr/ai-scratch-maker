// 伪3D透视投影行为校验：验证「屏幕坐标=世界/深度*K」「尺寸∝1/深度」「飞过摄像机重置」。
// 用法: node 3d_behavior_check.mjs <3d_demo.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_3D")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node 3d_behavior_check.mjs <3d_demo.sb3>"); process.exit(2); }

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

  const bad = [];
  const snap = {};

  // A. 绿旗 + 几步：深度应小于初始 200，且屏幕坐标/尺寸为正
  vm.greenFlag();
  await stepN(3);
  snap.z0 = num(getStageVar("obj_z"));
  snap.sx0 = num(getStageVar("obj_sx"));
  snap.ss0 = num(getStageVar("obj_ssize"));
  if (!(snap.z0 < 200 && snap.z0 > 0)) bad.push("深度未正常逼近: z0=" + snap.z0);
  if (!(snap.sx0 > 0)) bad.push("屏幕x<=0: " + snap.sx0);
  if (!(snap.ss0 > 0)) bad.push("尺寸<=0: " + snap.ss0);

  // B. 继续推进：深度单调减小，尺寸随逼近而增大（透视除法核心）
  await stepN(5);
  snap.z1 = num(getStageVar("obj_z"));
  snap.sx1 = num(getStageVar("obj_sx"));
  snap.ss1 = num(getStageVar("obj_ssize"));
  if (!(snap.z1 < snap.z0)) bad.push("深度未单调减小: " + snap.z0 + "->" + snap.z1);
  if (!(snap.ss1 > snap.ss0)) bad.push("尺寸未随逼近增大: " + snap.ss0 + "->" + snap.ss1);
  if (!(snap.sx1 > snap.sx0)) bad.push("屏幕x未随投影变化: " + snap.sx0 + "->" + snap.sx1);

  // C. 飞过摄像机后应重置（passed 标记），且深度回到合理范围。
  // 无头下 FOREVER 受 wait 节流，迭代速率约 0.4 次/步，故持续步进直到触发（封顶防呆）。
  let guard = 0;
  while (num(getStageVar("passed")) !== 1 && guard < 300) { await stepN(5); guard++; }
  snap.passed = num(getStageVar("passed"));
  snap.z2 = num(getStageVar("obj_z"));
  if (snap.passed !== 1) bad.push("未触发飞过摄像机的重置(passed!=1): " + snap.passed);
  if (!(snap.z2 > 20 && snap.z2 <= 200)) bad.push("重置后深度越界: " + snap.z2);

  const actual = { z0: snap.z0, z1: snap.z1, ss0: snap.ss0, ss1: snap.ss1, passed: snap.passed };
  console.log(JSON.stringify({ actual, bad }, null, 2));
  if (bad.length) { console.error("D3_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("D3_LOGIC_OK");
})().catch((e) => { console.error("D3_CHECK_FAIL", e && (e.stack || e)); process.exit(1); });
