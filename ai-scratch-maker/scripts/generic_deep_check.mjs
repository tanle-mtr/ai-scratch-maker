// 通用「深网」行为校验：覆盖所有**非标杆**作品（technique_probe* / community_tpl_* /
// example_* / cat_chase* / ref_* / semantic_check / showcase_band / community_asset_smoke 等），
// 它们此前只有「启动冒烟」（只断言能加载不崩），没有 VM 驱动的运行时深度验证。
//
// 与启动冒烟的区别（更深）：
//   · 冒烟：绿旗 + 「开始游戏」广播，各步进 60 帧 —— 浅，只抓加载即崩。
//   · 本脚本：绿旗后步进更久（CORE_STEPS=180），并**模拟多类交互**（多个常见广播 +
//     方向键/空格按键事件），每类交互后再步进，触发更多帽子与广播处理器；
//     期间收集运行时错误。交互触发的崩溃（如某广播处理器抛错）能被抓到。
//
// 三类断言（任意失败 → XXX_DEEP_FAIL）：
//   1. 运行时零错误：RUNTIME_ERROR 事件 + 加载/步进/交互全程未抛异常。
//   2. 结构完整性（project.json，总是可得）：存在舞台；总积木数 >= 1
//      （空构建 / 脚本整段丢失会触发）。
//   3. IR↔产物角色一致性：调用 ir_role_names.py 取 IR 声明的 sprite 名，断言每个都存在于
//      构建产物的 targets（最易回归的构建 bug：构建把某 sprite 弄丢了）。该层用规范解析器，
//      不靠正则会误抓自制积木名/背景名。
//
// 用法: node generic_deep_check.mjs <xxx.sb3>
// 退出码: 0 = 通过；1 = 失败；2 = 参数错误；0(打印 SKIP_*) = 未找到 scratch-vm，跳过。
// 输出标记: <STEM大写_DEEP_OK> / <STEM大写_DEEP_FAIL>
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_GENERIC_DEEP")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node generic_deep_check.mjs <xxx.sb3>"); process.exit(2); }
const STEM = path.basename(sb3Path).replace(/\.sb3$/i, "");
const MARK = STEM.toUpperCase().replace(/[^A-Z0-9]/g, "_") + "_DEEP_OK";

const require = createRequire(import.meta.url);
const JSZip = (() => {
  try { return require(path.join(path.dirname(vmPath), "jszip")); }
  catch { return null; }
})();
const SKILL_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const HELPER = path.join(SKILL_ROOT, "scripts", "ir_role_names.py");

// ---- headless 音频桩（与 boot_smoke_check.mjs 同源）----
function makeHeadlessAudioStub() {
  const gainNode = () => ({
    gain: { value: 1, setValueAtTime() {}, linearRampToValueAtTime() {}, setTargetAtTime() {} },
    connect() {},
  });
  const audioContext = {
    currentTime: 0, sampleRate: 44100, destination: {},
    createGain: gainNode,
    createBufferSource: () => ({ playbackRate: { value: 1 }, connect() {}, start() {}, stop() {} }),
    createBiquadFilter: () => ({ frequency: { value: 1 }, Q: { value: 1 }, type: "", connect() {} }),
    createBuffer: () => ({ getChannelData: () => new Float32Array(1) }),
    decodeAudioData: () => Promise.resolve({ getChannelData: () => new Float32Array(1) }),
  };
  const makePlayer = () => ({
    isPlaying: false, isStarting: false,
    outputNode: { playbackRate: { value: 1 }, stop() {} },
    once() {}, play() {}, stop() {}, connect() {}, setVolume() {}, gain: gainNode(),
    take() { return makePlayer(); },
  });
  return {
    audioContext, currentTime: 0, getInputNode() { return { connect() {} }; },
    decodeSoundPlayer: () => Promise.resolve(makePlayer()),
    makeBuffer: () => ({ getChannelData: () => new Float32Array(1) }),
    createBank() {
      return {
        name: "headless", sampleRate: 44100, channelCount: 2, length: 1,
        getAudioBuffer: () => Promise.resolve({ getChannelData: () => new Float32Array(1) }),
        decodeSoundPlayer: () => Promise.resolve(makePlayer()),
        addSoundPlayer() {}, setEffects() {}, setVolume() {}, stopAllSounds() {},
        stop() {}, playSound() {}, playSoundId() {},
      };
    },
  };
}

async function projectUsesMusic(buf) {
  if (!JSZip) return false;
  try {
    const zip = new JSZip();
    const data = await zip.loadAsync(buf);
    const pjName = Object.keys(data.files).find((n) => n.endsWith("project.json"));
    if (!pjName) return false;
    const pj = await data.files[pjName].async("string");
    return /music_playNoteForBeats|music_setTempo|music_playDrumForBeats|music_setInstrument|music_restForBeats/.test(pj);
  } catch { return false; }
}

function readProjectJSON(buf) {
  if (!JSZip) return null;
  const zip = new JSZip();
  return zip.loadAsync(buf).then((data) => {
    const pjName = Object.keys(data.files).find((n) => n.endsWith("project.json"));
    if (!pjName) return null;
    return data.files[pjName].async("string").then((s) => JSON.parse(s));
  });
}

function declaredSpriteNames() {
  for (const py of ["python", "python3"]) {
    try {
      const out = execFileSync(py, [HELPER, STEM], { cwd: SKILL_ROOT, encoding: "utf-8" });
      const names = out.split("\n").map((s) => s.trim()).filter(Boolean);
      return { names, used: py };
    } catch { /* 试下一个解释器 */ }
  }
  return { names: [], used: null };
}

const CORE_STEPS = 180;
const INTERACT_STEPS = 24;
const BROADCASTS = ["开始游戏", "开始", "reset", "重置", "重开", "下一关", "next"];
const KEYS = ["space", "right arrow", "left arrow", "up arrow", "down arrow"];

(async () => {
  const buf = fs.readFileSync(sb3Path);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);

  const vm = new VirtualMachine();
  vm.runtime.currentStepTime = 1000 / 30;
  const errs = [];
  try { vm.runtime.on("RUNTIME_ERROR", (e) => errs.push(e && (e.message || String(e)))); } catch { /* 无事件则忽略 */ }

  if (await projectUsesMusic(buf)) vm.runtime.audioEngine = makeHeadlessAudioStub();
  await vm.loadProject(ab);

  const stepN = (n) => { for (let i = 0; i < n; i++) { vm.runtime.currentMSecs += 33; vm.runtime._step(); } };
  const tryHats = (op, opts) => { try { vm.runtime.startHats(op, opts); } catch { /* 无对应帽子=空操作 */ } };

  let maxThreads = 0;
  vm.greenFlag();
  maxThreads = Math.max(maxThreads, vm.runtime.threads.length); // 帽子线程创建即入队，立即采样
  stepN(CORE_STEPS);

  // 模拟交互：广播 + 按键，每类后再步进，触发更多处理器
  for (const msg of BROADCASTS) { tryHats("event_whenbroadcastreceived", { BROADCAST_OPTION: msg }); maxThreads = Math.max(maxThreads, vm.runtime.threads.length); stepN(INTERACT_STEPS); }
  for (const k of KEYS) { tryHats("event_whenkeypressed", { KEY_OPTION: k }); maxThreads = Math.max(maxThreads, vm.runtime.threads.length); stepN(INTERACT_STEPS); }
  // 舞台被点击也常作为开始触发器
  tryHats("event_whenstageclicked"); maxThreads = Math.max(maxThreads, vm.runtime.threads.length); stepN(INTERACT_STEPS);

  // ---- 断言 1：运行时零错误 ----
  const bad = [];
  if (errs.length) bad.push("运行时错误 " + errs.length + " 处: " + errs.slice(0, 3).join("; "));

  // ---- 断言 2：结构完整性（project.json）----
  const pj = await readProjectJSON(buf);
  if (!pj) {
    bad.push("无法解析 project.json（产物结构损坏）");
  } else {
    const targets = pj.targets || [];
    const stage = targets.find((t) => t.isStage);
    if (!stage) bad.push("缺少舞台角色");
    const totalBlocks = targets.reduce((acc, t) => acc + (t.blocks ? Object.keys(t.blocks).length : 0), 0);
    if (totalBlocks < 1) bad.push("总积木数为 0（构建疑似空/脚本整段丢失）");
  }

  // ---- 断言 3：IR↔产物角色一致性 ----
  const { names: declared } = declaredSpriteNames();
  if (pj && declared.length) {
    const built = new Set((pj.targets || []).filter((t) => !t.isStage).map((t) => t.name));
    const missing = declared.filter((n) => !built.has(n));
    if (missing.length) bad.push("IR 声明但构建产物缺失的角色: " + missing.join(" / "));
  }

  const notes = [];
  if (maxThreads === 0) notes.push("绿旗后无任何脚本线程启动（交互前），可能是纯广播触发型作品或脚本未编译");

  if (bad.length === 0) {
    console.log(MARK + " 帧=" + (CORE_STEPS + (BROADCASTS.length + KEYS.length + 1) * INTERACT_STEPS) +
      " 交互=" + (BROADCASTS.length + KEYS.length + 1) + " 声明角色=" + declared.length);
    for (const n of notes) console.log("  · note: " + n);
    process.exit(0);
  } else {
    console.log(MARK.replace("_DEEP_OK", "_DEEP_FAIL"));
    for (const b of bad) console.log("  ✗ " + b);
    for (const n of notes) console.log("  · note: " + n);
    process.exit(1);
  }
})().catch((e) => { console.error(STEM.toUpperCase() + "_DEEP_ERROR", e && e.message); process.exit(1); });
