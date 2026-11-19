// 平台跳跃行为校验：验证重力落地、可变跳跃、水平移动、撞墙不穿透、金币拾取、镜头钳制。
// 用法: node platformer_behavior_check.mjs <platformer.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_PLATFORMER")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node platformer_behavior_check.mjs <platformer.sb3>"); process.exit(2); }

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
  // 一帧 = 广播 + 推进两格：无头下 startHats 只是把线程入队，
  // 真正执行落在下一个 _step，所以「广播 + stepN(2)」才等于一个完整物理帧。
  // （用 stepN(1) 会让物理隔帧才推进一次，跳跃高度与落地时机全部对不上）
  const frames = async (n = 1) => {
    for (let i = 0; i < n; i++) { broadcast("帧"); await stepN(2); }
  };
  const untilGrounded = async (cap = 90) => {
    let g = 0;
    while (num(getStageVar("在地面")) !== 1 && g < cap) { await frames(1); g++; }
    return g < cap;
  };

  const bad = [];
  const snap = {};

  // ---- A. 绿旗：初始化 + 自由落体后正好停在地面顶面（y = -120 + 20 + 18 = -102）
  vm.greenFlag();
  await stepN(2);
  setStageVar("自动帧", 0);          // 关掉自带时钟，改由本脚本逐帧驱动（可复现）
  setStageVar("使用键盘", 0);        // 输入改由变量注入，不依赖键盘
  await stepN(1);
  const grounded = await untilGrounded(90);
  snap.落地成功 = grounded;
  snap.落地y = Math.round(num(getStageVar("玩家y")) * 100) / 100;
  snap.在地面 = num(getStageVar("在地面"));
  if (!grounded) bad.push("自由落体后没有落地(在地面!=1)");
  if (Math.abs(snap.落地y - (-102)) > 1.5) bad.push("落地高度不对 y=" + snap.落地y + " 期望 -102");

  // ---- F1. 镜头左端钳制：玩家 x=-200 时 镜头x = max(-260, -200-160) = -260
  snap.镜头x_起点 = Math.round(num(getStageVar("镜头x")) * 100) / 100;
  if (Math.abs(snap.镜头x_起点 - (-260)) > 0.5) bad.push("镜头左端未钳制: " + snap.镜头x_起点);

  // ---- B. 跳跃：置跳跃键 → 速度转正、离地、y 上升
  setStageVar("输入_跳", 1);
  await frames(2);
  snap.跳跃后vy = Math.round(num(getStageVar("vy")) * 100) / 100;
  snap.跳跃后在地面 = num(getStageVar("在地面"));
  const yJump = num(getStageVar("玩家y"));
  snap.跳跃后y = Math.round(yJump * 100) / 100;
  if (snap.跳跃后vy <= 0) bad.push("按跳后 vy 未转正: " + snap.跳跃后vy);
  if (snap.跳跃后在地面 !== 0) bad.push("按跳后仍在地面");
  if (yJump <= -102) bad.push("按跳后 y 未上升: " + snap.跳跃后y);
  // 松开跳跃键 → 应回落到地面
  setStageVar("输入_跳", 0);
  const grounded2 = await untilGrounded(90);
  snap.落地回位 = grounded2;
  snap.回落y = Math.round(num(getStageVar("玩家y")) * 100) / 100;
  if (!grounded2) bad.push("跳跃后没有重新落地");
  if (Math.abs(snap.回落y - (-102)) > 1.5) bad.push("跳后落地高度不对 y=" + snap.回落y);

  // ---- C/D/E. 一直右移 100 帧：x 必须前进、被矮墙挡住、并吃到路上那枚金币
  setStageVar("输入_右", 1);
  const x0 = num(getStageVar("玩家x"));
  await frames(100);
  setStageVar("输入_右", 0);
  const x1 = num(getStageVar("玩家x"));
  snap.起始x = Math.round(x0);
  snap.最终x = Math.round(x1 * 10) / 10;
  snap.金币数 = num(getStageVar("金币数"));
  snap.得分 = num(getStageVar("得分"));
  if (!(x1 > x0 + 50)) bad.push("右移无效: x " + x0 + " -> " + x1);
  // 矮墙左边界 x=-40，玩家半宽 14 → 最多到 -54（本实现停在 -56）
  if (!(x1 < 0)) bad.push("穿墙了：x 越过矮墙到 " + snap.最终x);
  if (!(x1 > -70 && x1 < -40)) bad.push("撞墙停位异常 x=" + snap.最终x + " 期望 -56 附近");
  if (snap.金币数 !== 1) bad.push("金币计数不对: " + snap.金币数 + "（期望 1）");
  if (snap.得分 !== 10) bad.push("得分不对: " + snap.得分 + "（期望 10）");

  // ---- F2. 镜头跟随：镜头x = 玩家x - 160
  snap.镜头x_终点 = Math.round(num(getStageVar("镜头x")) * 100) / 100;
  const expectCam = Math.round((x1 - 160) * 100) / 100;
  if (Math.abs(snap.镜头x_终点 - expectCam) > 0.6)
    bad.push("镜头未跟随: " + snap.镜头x_终点 + " 期望 " + expectCam);

  // ---- G. 重置：回到出生点、金币复活
  broadcast("重置"); await stepN(2);
  snap.重置后x = Math.round(num(getStageVar("玩家x")));
  snap.重置后金币数 = num(getStageVar("金币数"));
  const coinAlive = getStageVar("金币活");
  snap.重置后金币活 = Array.isArray(coinAlive) ? coinAlive.map((v) => num(v)) : String(coinAlive);
  if (snap.重置后x !== -200) bad.push("重置未回出生点: x=" + snap.重置后x);
  if (!Array.isArray(coinAlive) || coinAlive.some((v) => num(v) !== 1))
    bad.push("重置后金币未复活: " + JSON.stringify(snap.重置后金币活));

  console.log(JSON.stringify({ actual: snap, bad }, null, 2));
  if (bad.length) { console.error("PLATFORMER_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("PLATFORMER_LOGIC_OK");
})().catch((e) => { console.error("PLATFORMER_CHECK_FAIL", e && (e.stack || e)); process.exit(1); });
