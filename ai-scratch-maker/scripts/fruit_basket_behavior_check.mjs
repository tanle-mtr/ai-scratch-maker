// 水果篮子（接水果）行为校验：状态机 / 重开复位（铁律7）/ 角色存在 / 胜负分支接线。
// 用法: node fruit_basket_behavior_check.mjs <fruit_basket.sb3> [--json]
//
// 重点守卫「拿来当模板抄」最易回归的几处：
//   1. 绿旗回标题态（游戏状态=0）
//   2. 开始/再来一局 广播 -> 游戏态=1 + 分数/生命/关卡/过关目标 干净复位
//   3. 重复开始（再来一局）仍完全复位 —— 铁律7 的核心
//   4. 关键角色（挡板/水果/结算页/再来一局）与胜负画面（胜利页/失败页）存在
//   5. 软探针：把克隆体拉到屏幕底部驱动扣血，验证「生命归零 -> 游戏状态=2 -> 结算页切失败页」
//      （失败不影响总判定，只作为额外覆盖；环境不支持克隆操作时记 note 跳过）
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_FRUIT")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node fruit_basket_behavior_check.mjs <fruit_basket.sb3>"); process.exit(2); }

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
const clonesOf = (name) =>
  vm.runtime.targets.filter((t) => t.sprite && t.sprite.name === name && !t.isOriginal);
const costumeName = (t) => {
  if (!t || !t.sprite) return undefined;
  const i = t.currentCostume;
  const arr = t.sprite.costumes || [];
  return arr[i] ? arr[i].name : undefined;
};
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
  snap.绿旗后游戏状态 = num(getStageVar("游戏状态"));
  if (snap.绿旗后游戏状态 !== 0) bad.push("绿旗后未回标题态(游戏状态!=0): " + snap.绿旗后游戏状态);

  // B. 开始 -> 进入游戏态且干净复位
  broadcast("开始游戏"); await stepN(3);
  snap.开始后游戏状态 = num(getStageVar("游戏状态"));
  snap.开始后分数 = num(getStageVar("分数"));
  snap.开始后生命 = num(getStageVar("生命"));
  snap.开始后关卡 = num(getStageVar("关卡"));
  snap.开始后过关目标 = num(getStageVar("过关目标"));
  if (snap.开始后游戏状态 !== 1) bad.push("开始后未进入游戏态: " + snap.开始后游戏状态);
  if (snap.开始后分数 !== 0) bad.push("开始后分数未复位: " + snap.开始后分数);
  if (snap.开始后生命 !== 3) bad.push("开始后生命未复位: " + snap.开始后生命);
  if (snap.开始后关卡 !== 1) bad.push("开始后关卡未复位: " + snap.开始后关卡);
  if (snap.开始后过关目标 !== 10) bad.push("开始后过关目标未复位: " + snap.开始后过关目标);

  // C. 再来一局（重复开始）仍完全复位 —— 铁律7 核心守卫
  setStageVar("分数", 7); setStageVar("生命", 1); setStageVar("关卡", 3);
  broadcast("开始游戏"); await stepN(3);
  snap.重开分数 = num(getStageVar("分数"));
  snap.重开生命 = num(getStageVar("生命"));
  snap.重开关卡 = num(getStageVar("关卡"));
  snap.重开游戏状态 = num(getStageVar("游戏状态"));
  if (snap.重开分数 !== 0) bad.push("再来一局后分数未复位: " + snap.重开分数);
  if (snap.重开生命 !== 3) bad.push("再来一局后生命未复位: " + snap.重开生命);
  if (snap.重开关卡 !== 1) bad.push("再来一局后关卡未复位: " + snap.重开关卡);
  if (snap.重开游戏状态 !== 1) bad.push("再来一局后未回到游戏态: " + snap.重开游戏状态);

  // D. 关键角色与胜负画面存在（模板被破坏会直接抓出来）
  for (const n of ["挡板", "水果", "结算页", "再来一局"])
    if (!spriteExists(n)) bad.push("缺少关键角色: " + n);
  const 结算页 = targetByName("结算页");
  if (结算页) {
    const cnames = (结算页.sprite.costumes || []).map((c) => c.name);
    if (!cnames.includes("胜利页")) bad.push("结算页缺少 胜利页 造型");
    if (!cnames.includes("失败页")) bad.push("结算页缺少 失败页 造型");
    snap.结算页造型 = cnames;
  }

  // E. 软探针：直接造水果克隆（绕过生成器的 wait），把克隆体拉到底部驱动扣血
  //    -> 生命归零 -> 游戏状态=2 -> 结算页切失败页
  //    （scratch-vm 的 control_wait 走真实墙钟，无头下只推虚拟时钟不会让生成器吐克隆，
  //      故用 vm.runtime.cloneTarget() 直接克隆；失败不影响总判定，只作额外覆盖）
  try {
    if (typeof (vm.runtime.targets[0] || {}).makeClone !== "function")
      throw new Error("本版本 scratch-vm 无 makeClone");
    setStageVar("生命", 3);
    setStageVar("游戏状态", 1);
    const fruitOriginal = targetByName("水果");
    if (!fruitOriginal) throw new Error("找不到 水果 原始角色");
    for (let attempt = 0; attempt < 6; attempt++) {
      const clone = fruitOriginal.makeClone();
      if (!clone) { notes.push("软探针: makeClone 返回空，跳过失败路径验证"); break; }
      vm.runtime.addTarget(clone);
      clone.goBehindOther(fruitOriginal);
      vm.runtime.startHats("control_start_as_clone", null, clone);
      await stepN(1);          // 克隆初始化（set_y 180 等）
      clone.y = -200;          // 直接拉到屏幕底部
      await stepN(2);          // 触发 y<-185 扣血分支（并删除克隆）
      if (num(getStageVar("生命")) <= 0) break;
    }
    await stepN(3);
    snap.探针后生命 = num(getStageVar("生命"));
    snap.探针后游戏状态 = num(getStageVar("游戏状态"));
    snap.探针后结算页造型 = costumeName(结算页);
    if (snap.探针后游戏状态 === 2 && snap.探针后结算页造型 === "失败页") {
      snap.失败路径 = "OK";
    } else {
      notes.push("软探针: 失败路径未完全触发(生命=" + snap.探针后生命 +
        ", 游戏状态=" + snap.探针后游戏状态 + ", 结算页=" + snap.探针后结算页造型 + ")");
    }
  } catch (e) {
    notes.push("软探针异常，跳过: " + (e && e.message));
  }

  console.log(JSON.stringify({ snap, bad, notes }, null, 2));
  if (bad.length) { console.error("FRUIT_BASKET_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("FRUIT_BASKET_LOGIC_OK");
})().catch((e) => {
  console.error("FRUIT_BASKET_CHECK_FAIL", e && (e.stack || e));
  process.exit(1);
});
