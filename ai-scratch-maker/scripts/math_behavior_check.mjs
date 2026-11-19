// 数学实验室行为校验：用**已知正确答案**当断言。
// 用法: node math_behavior_check.mjs <math_lab.sb3>
//
// 数学类作品最好验证 —— 答案唯一，不靠「看起来对不对」：
//   N 皇后解数：4→2, 5→10, 6→4, 7→40, 8→92（OEIS A000170）
//   1/2+1/3=5/6，3/4-1/6=7/12
//   1..100 质数 25 个，第 25 个是 97
//
// 它抓的是「四层校验完全看不见」的错：
//   ① 回溯时多做/少做一次推进 → 解数少一半（14 vs 92）
//   ② 除法没取整 → 分子出现 5.000000001
//   ③ gcd 循环边界错 → 化简不彻底
//   ④ 筛法没从 i*i 开始 → 质数个数偏多
import fs from "node:fs";
import { findScratchVM, loadScratchVM } from "./scratch_vm_path.mjs";

const VM = loadScratchVM(findScratchVM());
const vm = new VM();

const buf = fs.readFileSync(process.argv[2]);
await vm.loadProject(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
vm.runtime.currentStepTime = 1000 / 30;

const num = (x) => (typeof x === "string" ? parseFloat(x) : x);
const r2 = (x) => Math.round(x * 100) / 100;

function getVar(name) {
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v && v.name === name) return v.value;
    }
  }
  return undefined;
}
function setVar(name, value) {
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v && v.name === name) { v.value = value; return true; }
    }
  }
  return false;
}
function getList(name) {
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v && v.name === name) return v.value;
    }
  }
  return undefined;
}

const stepN = async (n) => {
  for (let i = 0; i < n; i++) {
    vm.runtime.currentMSecs += 33;
    vm.runtime._step();
    await Promise.resolve();
  }
};
const broadcast = (m) =>
  vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: m });

// 广播一个「会跑完」的脚本，一直推进到线程清空（舞台 forever 常驻，基线算 1）
async function runToEnd(msg, label, maxSteps = 60000) {
  const base = vm.runtime.threads.length;
  broadcast(msg);
  await stepN(2);
  let i = 2;
  while (vm.runtime.threads.length > base && i < maxSteps) {
    await stepN(1);
    i++;
  }
  if (i >= maxSteps) return { steps: i, timeout: true };
  return { steps: i, timeout: false };
}

const bad = [];
const snap = {};

// ---------------------------------------------------------------- 0. 启动
vm.greenFlag();
await stepN(3);
setVar("自动帧", 0);          // 接管时钟（此工程没有「帧」驱动，保险）
await stepN(2);

snap.角色数 = vm.runtime.targets.filter((t) => !t.isStage).length;
if (snap.角色数 < 3) bad.push("角色数异常：应 ≥3，实为 " + snap.角色数);

// ---------------------------------------------------------------- 1. N 皇后
const queenCases = [
  { n: 4, want: 2 },
  { n: 5, want: 10 },
  { n: 6, want: 4 },
  { n: 8, want: 92 },
];
snap.皇后 = [];
for (const c of queenCases) {
  setVar("n", c.n);
  setVar("解上限", 100000);
  const r = await runToEnd("跑皇后", "n=" + c.n);
  const got = num(getVar("解数"));
  const nodes = num(getVar("节点数"));
  snap.皇后.push({ n: c.n, 解数: got, 期望: c.want, 节点: nodes, steps: r.steps,
                   timeout: r.timeout });
  if (r.timeout) bad.push("N=" + c.n + " 回溯超时（可能死循环）");
  if (got !== c.want) bad.push("N=" + c.n + " 解数应为 " + c.want + "，实为 " + got);
  // 列表长度必须等于 n（回退时若多塞了一项，这里会露出来）
  const listLen = (getList("皇后列") || []).length;
  if (listLen !== c.n)
    bad.push("N=" + c.n + " 时「皇后列」长度应为 " + c.n + "，实为 " + listLen);
}

// ---------------------------------------------------------------- 2. 分数
const fracCases = [
  { fa: 1, fb: 2, fc: 1, fd: 3, p: 5, q: 6, label: "1/2+1/3" },
  { fa: 3, fb: 4, fc: -1, fd: 6, p: 7, q: 12, label: "3/4-1/6" },
  { fa: 1, fb: 3, fc: 2, fd: 3, p: 1, q: 1, label: "1/3+2/3（须约成 1/1）" },
  { fa: 2, fb: 6, fc: 1, fd: 6, p: 1, q: 2, label: "2/6+1/6（须约成 1/2）" },
];
snap.分数 = [];
for (const c of fracCases) {
  setVar("fa", c.fa); setVar("fb", c.fb);
  setVar("fc", c.fc); setVar("fd", c.fd);
  await runToEnd("跑分数", c.label, 4000);
  const p = num(getVar("分子"));
  const q = num(getVar("分母"));
  snap.分数.push({ 用例: c.label, 结果: p + "/" + q, 期望: c.p + "/" + c.q });
  if (p !== c.p || q !== c.q)
    bad.push(c.label + " 应为 " + c.p + "/" + c.q + "，实为 " + p + "/" + q);
  if (Math.abs(p - Math.round(p)) > 1e-9)
    bad.push(c.label + " 分子不是整数（" + p + "），说明化简时没取整");
}

// ---------------------------------------------------------------- 3. 质数筛
setVar("上限", 100);
await runToEnd("跑质数", "100", 4000);
const cnt = num(getVar("质数个数"));
const plist = getList("质数表") || [];
snap.质数_个数 = cnt;
snap.质数_前5 = plist.slice(0, 5).map(Number);
snap.质数_第25个 = Number(plist[24]);
if (cnt !== 25) bad.push("1~100 质数应为 25 个，实为 " + cnt);
if (String(snap.质数_前5.join(",")) !== "2,3,5,7,11")
  bad.push("前 5 个质数应为 2,3,5,7,11，实为 " + snap.质数_前5.join(","));
if (snap.质数_第25个 !== 97)
  bad.push("第 25 个质数应为 97，实为 " + snap.质数_第25个);
if (plist.length !== 25) bad.push("质数表长度应为 25，实为 " + plist.length);

// ---------------------------------------------------------------- 结果
const pass = bad.length === 0;
console.log(JSON.stringify(snap, null, 2));
if (pass) {
  console.log("MATH_LOGIC_OK  数学结果全部正确（回溯/分数/筛法）");
  process.exit(0);
} else {
  console.log("MATH_LOGIC_FAIL");
  for (const b of bad) console.log("  ✗ " + b);
  process.exit(1);
}
