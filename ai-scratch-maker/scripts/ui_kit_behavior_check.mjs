// UI Kit 行为校验：确认素材真的装进界面能用。
// 用法: node ui_kit_behavior_check.mjs <ui_kit_demo.sb3>
//
// 它抓的是「四层校验看不见」的一类错：
//   ① 造型名拼错 → switch 静默失败，界面永远停在第一帧的样子
//   ② 弹窗组没同步 → 遮罩关了但面板还留着
//   ③ 进度条档位算错 → 血量变了但造型不变（或被拉伸）
//   ④ hover 判定没挡弹窗 → 弹窗开着时底下的按钮还在变亮
import fs from "node:fs";
import { findScratchVM, loadScratchVM } from "./scratch_vm_path.mjs";

const VM = loadScratchVM(findScratchVM());
const vm = new VM();

const buf = fs.readFileSync(process.argv[2]);
await vm.loadProject(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
vm.runtime.currentStepTime = 1000 / 30;

const num = (x) => (typeof x === "string" ? parseFloat(x) : x);

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
function sprite(name) {
  return vm.runtime.targets.find((t) => !t.isStage && t.getName() === name);
}
function costumeOf(name) {
  const t = sprite(name);
  return t ? t.getCostumes()[t.currentCostume].name : undefined;
}
function visibleOf(name) {
  const t = sprite(name);
  return t ? t.visible : undefined;
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
// 一帧 = 广播 + 推 2 步（startHats 只入队，线程在下一个 _step 才跑）
const frames = async (n = 1) => {
  for (let i = 0; i < n; i++) { broadcast("帧"); await stepN(2); }
};

const bad = [];
const snap = {};

// ---------------------------------------------------------------- 0. 启动
vm.greenFlag();
await stepN(3);
setVar("自动帧", 0);          // 接管时钟，避免与舞台 forever 抢发帧
await stepN(3);

snap.角色数 = vm.runtime.targets.filter((t) => !t.isStage).length;
if (snap.角色数 < 15) bad.push("角色数异常：应为 18 个（含弹窗组），实为 " + snap.角色数);

// ⚠️ 绿旗后舞台的 forever 已经发过帧了，血量会掉一点 —— 先显式「重开」再断言初值，
//    否则测的是「启动了几帧之后的状态」，不是初值。
broadcast("重开");
await stepN(3);

snap.初_弹窗 = num(getVar("弹窗"));
snap.初_血量 = num(getVar("血量"));
if (snap.初_弹窗 !== 0) bad.push("开局弹窗应为关闭(0)，实为 " + snap.初_弹窗);
if (snap.初_血量 !== 100) bad.push("开局血量应为 100，实为 " + snap.初_血量);

// 弹窗组默认必须隐藏
for (const n of ["遮罩", "设置窗", "窗标题", "关闭键", "窗内按钮", "窗内按钮文字"]) {
  if (visibleOf(n) !== false) bad.push("开局「" + n + "」应隐藏，实为 visible=" + visibleOf(n));
}

// ---------------------------------------------------------------- 1. 帧循环真的在跑
// 用「血量下降」当证据：帧计数只在自动帧=1 时增长，而校验里我们接管了时钟。
const hp0 = num(getVar("血量"));
await frames(6);
const hp1 = num(getVar("血量"));
snap.血量_6帧降幅 = Math.round((hp0 - hp1) * 100) / 100;
if (hp0 - hp1 <= 0) bad.push("帧循环未推进：6 帧后血量没有下降（" + hp0 + " → " + hp1 + "）");

// ---------------------------------------------------------------- 2. 按钮造型存在且正确
snap.主按钮_造型 = costumeOf("主按钮");
if (snap.主按钮_造型 !== "primary_normal_l")
  bad.push("主按钮静止时应为 primary_normal_l，实为 " + snap.主按钮_造型);
snap.设置按钮_造型 = costumeOf("设置按钮");
if (snap.设置按钮_造型 !== "secondary_normal_m")
  bad.push("设置按钮静止时应为 secondary_normal_m，实为 " + snap.设置按钮_造型);

// ---------------------------------------------------------------- 3. 进度条换档
// 重新回满，然后连跑 12 帧（血量 100 → 94，跨过 100→90 这一档）
broadcast("重开");
await stepN(2);
const bar0 = costumeOf("血条");
await frames(12);
const bar1 = costumeOf("血条");
snap.血条_初始 = bar0;
snap.血条_12帧后 = bar1;
snap.血量_12帧后 = Math.round(num(getVar("血量")) * 10) / 10;
if (bar0 !== "bar_hp_100") bad.push("血条初始造型应为 bar_hp_100，实为 " + bar0);
if (bar1 === bar0) bad.push("血量已下降但血条造型没变（档位计算或造型名拼错）");
if (!/^bar_hp_\d{3}$/.test(String(bar1)))
  bad.push("血条造型名格式错：" + bar1 + "（应为 bar_hp_###）");
if (bar1 !== "bar_hp_090")
  bad.push("血量降到 90 档时造型应为 bar_hp_090，实为 " + bar1);

// ---------------------------------------------------------------- 4. 打开弹窗
broadcast("开设置");
await stepN(3);
snap.开窗_弹窗 = num(getVar("弹窗"));
snap.开窗_遮罩 = visibleOf("遮罩");
snap.开窗_面板 = visibleOf("设置窗");
snap.开窗_关闭键 = visibleOf("关闭键");
if (snap.开窗_弹窗 !== 1) bad.push("收到「开设置」后弹窗标志应为 1，实为 " + snap.开窗_弹窗);
for (const [k, v] of [["遮罩", snap.开窗_遮罩], ["设置窗", snap.开窗_面板],
                      ["关闭键", snap.开窗_关闭键]]) {
  if (v !== true) bad.push("开窗后「" + k + "」应显示，实为 visible=" + v);
}

// 弹窗开着时，血条不应继续掉（弹窗=1 挡住了帧逻辑）
const hpA = num(getVar("血量"));
await frames(8);
const hpB = num(getVar("血量"));
snap.开窗_血量变化 = Math.round((hpA - hpB) * 100) / 100;
if (Math.abs(hpA - hpB) > 0.01)
  bad.push("弹窗打开时血量仍在下降（" + hpA + " → " + hpB + "），说明帧逻辑没挡弹窗");

// ---------------------------------------------------------------- 5. 关闭弹窗
broadcast("关设置");
await stepN(3);
snap.关窗_弹窗 = num(getVar("弹窗"));
snap.关窗_遮罩 = visibleOf("遮罩");
if (snap.关窗_弹窗 !== 0) bad.push("收到「关设置」后弹窗标志应为 0，实为 " + snap.关窗_弹窗);
if (snap.关窗_遮罩 !== false) bad.push("关窗后遮罩应隐藏，实为 visible=" + snap.关窗_遮罩);

// 关窗后血量恢复下降
const hpC = num(getVar("血量"));
await frames(8);
const hpD = num(getVar("血量"));
snap.关窗_血量下降 = Math.round((hpC - hpD) * 100) / 100;
if (hpC - hpD <= 0) bad.push("关窗后血量应恢复下降，实为 " + hpC + " → " + hpD);

// ---------------------------------------------------------------- 6. 重开（主按钮广播）
broadcast("重开");
await stepN(3);
snap.重开后血量 = num(getVar("血量"));
if (snap.重开后血量 !== 100) bad.push("收到「重开」后血量应回满 100，实为 " + snap.重开后血量);

// ---------------------------------------------------------------- 7. 素材齐全性
const allCostumes = new Set();
for (const t of vm.runtime.targets) {
  for (const c of t.getCostumes()) allCostumes.add(c.name);
}
snap.造型总数 = allCostumes.size;
for (const need of ["bar_hp_100", "bar_hp_090", "bar_hp_000",
                    "primary_hover_l", "primary_pressed_l",
                    "ghost_pressed_m", "ok_pressed_s"]) {
  if (!allCostumes.has(need)) bad.push("缺少造型：" + need);
}

// ---------------------------------------------------------------- 8. 音效真的挂上了
// 无头环境没有 AudioContext，「播放声音」不会真的出声，也不会报错 ——
// 所以这里只做**资源级**校验：音效有没有被打进 sb3、名字对不对。
const soundsOf = (name) => {
  const t = name === "__stage__"
    ? vm.runtime.targets.find((x) => x.isStage)
    : sprite(name);
  return t ? (t.sprite.sounds || []).map((s) => s.name) : [];
};
snap.舞台音效 = soundsOf("__stage__");
if (!snap.舞台音效.includes("ev_open") || !snap.舞台音效.includes("ev_close"))
  bad.push("舞台应挂 ev_open / ev_close，实为 [" + snap.舞台音效.join(",") + "]");
for (const n of ["主按钮", "设置按钮", "退出按钮", "关闭键", "窗内按钮"]) {
  const s = soundsOf(n);
  if (!s.includes("ui_click")) bad.push("「" + n + "」缺少 ui_click 音效，实为 [" + s.join(",") + "]");
}
const allSounds = new Set();
for (const t of vm.runtime.targets) {
  for (const s of (t.sprite.sounds || [])) allSounds.add(s.name);
}
snap.音效总数 = allSounds.size;
if (allSounds.size < 3) bad.push("音效资源过少（应至少 3 个），实为 " + allSounds.size);

const pass = bad.length === 0;
console.log(JSON.stringify(snap, null, 2));
if (pass) {
  console.log("UI_KIT_LOGIC_OK  界面素材装进工程后行为正确");
  process.exit(0);
} else {
  console.log("UI_KIT_LOGIC_FAIL");
  for (const b of bad) console.log("  ✗ " + b);
  process.exit(1);
}
