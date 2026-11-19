// 教育课件行为校验：绿旗生成 → 验证翻页/数据可视化（柱子数=数据长度、每柱高度=数据值）/随堂测验计分。
// 翻页与答题都走「广播 + 变量」，不用 ask/answer，所以无头 scratch-vm 也能真实验证。
// 用法: node edu_behavior_check.mjs <edu_demo.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_EDU")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node edu_behavior_check.mjs <edu_demo.sb3>"); process.exit(2); }

let vm = null;

const getVar = (t, name) => {
  for (const id of Object.keys(t.variables || {}))
    if (t.variables[id] && t.variables[id].name === name) return t.variables[id].value;
  return undefined;
};
const setVar = (t, name, val) => {
  for (const id of Object.keys(t.variables || {}))
    if (t.variables[id] && t.variables[id].name === name) { t.variables[id].value = val; return true; }
  return false;
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
const clonesOf = (name) =>
  vm.runtime.targets.filter((t) => t.sprite && t.sprite.name === name && !t.isOriginal);
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
  const disposeAll = (name) => { for (const t of clonesOf(name)) vm.runtime.disposeTarget(t); };

  const bad = [];
  const snap = {};

  // A. 绿旗 → 初始状态正确（绿旗脚本已广播[生成柱子]，只跑一次）
  vm.greenFlag();
  await stepN(8);
  if (num(getStageVar("页码")) !== 1) bad.push("初始页码!=1: " + getStageVar("页码"));
  if (num(getStageVar("得分")) !== 0) bad.push("初始得分!=0: " + getStageVar("得分"));
  const dataArr = getStageVar("数据");
  const dataLen = Array.isArray(dataArr) ? dataArr.length : (typeof dataArr === "string" ? dataArr.split(",").length : 0);
  snap.柱子数 = clonesOf("柱子").length;
  if (snap.柱子数 !== dataLen) bad.push("柱子克隆数=" + snap.柱子数 + "(期望" + dataLen + "，=数据长度)");

  // B. 数据可视化：每根柱子的「高度」变量必须等于 数据[编号]（柱由列表驱动）
  {
    const bars = clonesOf("柱子");
    let allMatch = true;
    for (const b of bars) {
      const no = num(getVar(b, "编号"));
      const h = num(getVar(b, "高度"));
      const dv = Array.isArray(dataArr) ? num(dataArr[no - 1]) : undefined;
      if (!(dv !== undefined && h === dv)) { allMatch = false; break; }
    }
    snap.柱高匹配 = allMatch;
    if (!allMatch) bad.push("柱子高度未正确反映数据列表（数据可视化失败）");
  }

  // C. 翻页：下一页 → 页码+1；上一页 → 页码-1
  broadcast("下一页"); await stepN(2);
  const p1 = num(getStageVar("页码"));
  snap.下一页后页码 = p1;
  if (p1 !== 2) bad.push("下一页后页码=" + p1 + "(期望2)");
  broadcast("上一页"); await stepN(2);
  const p2 = num(getStageVar("页码"));
  if (p2 !== 1) bad.push("上一页后页码=" + p2 + "(期望1)");

  // D. 随堂测验：当前答案==正确答案 才得分
  setStageVar("当前答案", 2); // 正确答案=2
  broadcast("提交"); await stepN(2);
  snap.答对后得分 = num(getStageVar("得分"));
  if (snap.答对后得分 !== 1) bad.push("答对后得分=" + snap.答对后得分 + "(期望1)");
  // 再答错一次，得分不应再涨
  setStageVar("当前答案", 1);
  broadcast("提交"); await stepN(2);
  if (num(getStageVar("得分")) !== 1) bad.push("答错后仍加分(得分=" + getStageVar("得分") + "，应仍为1)");

  const actual = {
    柱子数: snap.柱子数,
    柱高匹配: snap.柱高匹配,
    下一页后页码: snap.下一页后页码,
    答对后得分: snap.答对后得分,
  };
  console.log(JSON.stringify({ actual, bad }, null, 2));
  if (bad.length) { console.error("EDU_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("EDU_LOGIC_OK");
})().catch((e) => {
  console.error("EDU_CHECK_FAIL", e && (e.stack || e));
  process.exit(1);
});
