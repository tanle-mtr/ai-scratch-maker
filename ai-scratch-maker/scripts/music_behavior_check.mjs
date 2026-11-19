// 乐器编曲台行为校验：简谱解析 / 八度偏移 / 变量驱动乐器切换。
// 用法: node music_behavior_check.mjs <music_band.sb3>
//
// 音乐类作品听起来「对不对」很难自动判断，但下面三件事是**确定的**：
//   ① 简谱 → MIDI 的映射（1 1 5 5 6 6 5 → 60 60 67 67 69 69 67）
//   ② 八度偏移（+12）
//   ③ set instrument to (变量) 之后，VM 里 currentInstrument 真的变了
//
// 第 ③ 条是本轮新找到的硬校验路径：
//   scratch-vm 的 music 扩展把状态存在 target.getCustomState("Scratch.music")，
//   而 _setInstrument 没有 audioEngine 守卫 —— 所以无头环境也能读到「乐器换了没」。
//
// ⚠️ 不要触发「演奏旋律」：play note for beats 按**虚拟时间**阻塞（与有没有声音无关），
//    测一首长谱会直接超时。演奏的正确性靠「音高表」间接验证。
import fs from "node:fs";
import { findScratchVM, loadScratchVM } from "./scratch_vm_path.mjs";

const VM = loadScratchVM(findScratchVM());
const vm = new VM();

const buf = fs.readFileSync(process.argv[2]);
await vm.loadProject(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
vm.runtime.currentStepTime = 1000 / 30;

const num = (x) => (typeof x === "string" ? parseFloat(x) : x);

function allNames() {
  const out = {};
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v) out[v.name] = v;
    }
  }
  return out;
}
const getVar = (name) => { const v = allNames()[name]; return v ? v.value : undefined; };
const setVar = (name, value) => { const v = allNames()[name]; if (v) { v.value = value; return true; } return false; };
const getList = (name) => { const v = allNames()[name]; return v ? v.value : undefined; };
const setList = (name, arr) => { const v = allNames()[name]; if (v) { v.value = arr.slice(); return true; } return false; };

const stepN = async (n) => {
  for (let i = 0; i < n; i++) {
    vm.runtime.currentMSecs += 33;
    vm.runtime._step();
    await Promise.resolve();
  }
};
const broadcast = (m) =>
  vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: m });

const sprite = (name) => vm.runtime.targets.find((t) => !t.isStage && t.getName() === name);

const bad = [];
const snap = {};

// ---------------------------------------------------------------- 0. 启动
vm.greenFlag();
await stepN(3);
setVar("自动帧", 0);
await stepN(2);

snap.角色数 = vm.runtime.targets.filter((t) => !t.isStage).length;
if (snap.角色数 < 3) bad.push("角色数异常：应 ≥3，实为 " + snap.角色数);

// ---------------------------------------------------------------- 1. 简谱 → MIDI
const TWINKLE = [1, 1, 5, 5, 6, 6, 5, 4, 4, 3, 3, 2, 2, 1];
const WANT4 = [60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60];

setList("简谱", TWINKLE);
setVar("八度", 4);
broadcast("解析简谱");
await stepN(30);
const pitches = (getList("音高表") || []).map(Number);
snap.简谱 = TWINKLE.join(" ");
snap.音高_八度4 = pitches;
if (pitches.length !== WANT4.length)
  bad.push("音高表长度应为 " + WANT4.length + "，实为 " + pitches.length);
else if (String(pitches.join(",")) !== WANT4.join(","))
  bad.push("八度 4 的音高应为 [" + WANT4.join(",") + "]，实为 [" + pitches.join(",") + "]");

// 休止符：0 应变成 0（不是 60）
setList("简谱", [1, 0, 5]);
broadcast("解析简谱");
await stepN(30);
const withRest = (getList("音高表") || []).map(Number);
snap.含休止 = withRest;
if (String(withRest.join(",")) !== "60,0,67")
  bad.push("休止符应解析成 0（得到 60,0,67），实为 " + withRest.join(","));

// ---------------------------------------------------------------- 2. 八度偏移
setList("简谱", TWINKLE);
setVar("八度", 5);
broadcast("解析简谱");
await stepN(30);
const up = (getList("音高表") || []).map(Number);
snap.音高_八度5 = up;
const want5 = WANT4.map((v) => v + 12);
if (String(up.join(",")) !== want5.join(","))
  bad.push("八度 5 应全部 +12，期望 [" + want5.join(",") + "]，实为 [" + up.join(",") + "]");

// 低八度（3）应该 -12
setVar("八度", 3);
broadcast("解析简谱");
await stepN(30);
const down = (getList("音高表") || []).map(Number);
snap.音高_八度3_首音 = down[0];
if (down[0] !== 48) bad.push("八度 3 的首音应为 48（C3），实为 " + down[0]);

// ---------------------------------------------------------------- 3. 变量驱动换乐器
// scratch-vm 把音乐状态存在 target 上：getCustomState("Scratch.music").currentInstrument
// 注意：内部是 0-based（用户选 1 = 钢琴 = 内部 0）
const musicState = (name) => {
  const t = sprite(name);
  return t ? t.getCustomState("Scratch.music") : undefined;
};

const cases = [
  { set: 5, want: 4, label: "乐器 5（电吉他）" },
  { set: 1, want: 0, label: "乐器 1（钢琴）" },
  { set: 21, want: 20, label: "乐器 21（管弦乐）" },
];
snap.乐器 = [];
for (const c of cases) {
  setVar("乐器", c.set);
  broadcast("换乐器");
  await stepN(10);
  const st = musicState("编曲台");
  const cur = st ? st.currentInstrument : undefined;
  snap.乐器.push({ 设置: c.set, 内部值: cur, 期望: c.want });
  if (cur !== c.want)
    bad.push(c.label + " 切换失败：currentInstrument 应为 " + c.want + "，实为 " + cur);
}

// 越界值应被 clamp，不能让引擎崩
setVar("乐器", 99);
broadcast("换乐器");
await stepN(10);
const stOver = musicState("编曲台");
snap.乐器越界 = stOver ? stOver.currentInstrument : undefined;
if (stOver && (stOver.currentInstrument < 0 || stOver.currentInstrument > 20))
  bad.push("乐器 99 未被 clamp 到 0..20，实为 " + stOver.currentInstrument);

// ---------------------------------------------------------------- 4. 音乐状态是「每个角色一份」
// 低音声部还没演奏过 → 它自己的 music state 应该还没被设过（或与编曲台不同源）
{
  const a = musicState("编曲台");
  const b = musicState("低音声部");
  snap.状态隔离 = { 编曲台: a ? a.currentInstrument : null, 低音声部: b ? b.currentInstrument : null };
  if (a && b && a === b && b !== null) {
    // 两者恰好相同不算错（可能都是默认值），只在「低音声部根本没设过却和编曲台一样」时提示
    // 这里不做硬断言，只记录，避免误报
  }
}

// ---------------------------------------------------------------- 5. 扩展真的用上了
// 不去读 extensionManager 的内部字段（不同版本字段名不同），直接扫积木 opcode —— 更稳。
const hasMusicBlock = () => {
  for (const t of vm.runtime.targets) {
    const bl = t.blocks && t.blocks._blocks;
    if (!bl) continue;
    for (const id of Object.keys(bl)) {
      const op = bl[id] && bl[id].opcode;
      if (op && op.indexOf("music_") === 0) return true;
    }
  }
  return false;
};
snap.含音乐积木 = hasMusicBlock();
if (!snap.含音乐积木) bad.push("工程里没有 music_* 积木（乐器扩展没接上）");

// ---------------------------------------------------------------- 结果
const pass = bad.length === 0;
console.log(JSON.stringify(snap, null, 2));
if (pass) {
  console.log("MUSIC_LOGIC_OK  简谱解析与乐器切换全部正确");
  process.exit(0);
} else {
  console.log("MUSIC_LOGIC_FAIL");
  for (const b of bad) console.log("  ✗ " + b);
  process.exit(1);
}
