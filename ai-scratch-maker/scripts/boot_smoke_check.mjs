// 全量启动冒烟检查：把 examples/output 下**每一个** .sb3 加载进 scratch-vm，
// 绿旗启动 + 推若干虚拟步（再尝试触发「开始游戏」广播），断言「不抛异常 / 不崩」。
//
// 目的：补上回归的最大缺口——54 个作品里只有 ~21 个有逐作品行为校验，
// 其余（含旗舰 cat_mouse、所有 technique_probe*、community_tpl_*、example_*）
// 只过结构校验，没有 VM 驱动的运行时验证。结构校验抓不到「加载即崩 / 初始化抛错」，
// 本脚本在**一个 node 进程**里轮询全部作品，专门抓这类运行时崩溃。
//
// 与逐作品行为校验（*_behavior_check.mjs）的区别：
//   · 行为校验：针对单个作品硬编码状态机断言，深度高、覆盖少（21 个）。
//   · 启动冒烟：覆盖全部作品、只断言「能启动不崩」，深度浅、覆盖全（54 个）。
//   两者互补——冒烟是宽网（不漏崩溃），行为校验是深网（逻辑正确）。
//
// 用法：node boot_smoke_check.mjs [sb3目录]   （默认 examples/output）
// 退出码：0 = 全部启动正常；1 = 至少一个崩溃。
// 环境变量 BOOT_STEPS 控制每阶段的虚拟步数（默认 60，约 2s 仿真@30fps，足以触发初始化）。

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_BOOT_SMOKE")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

// ---- headless 音频桩（与 smoke_test.mjs 同源）----
// 含 music 扩展的工程在 loadProject 时，扩展构造器会解码内置采样并抛
// "No Audio Context Detected"。提供 no-op 音频桩，让音乐工程也能在 headless 下加载。
const require = createRequire(import.meta.url);
const JSZip = (() => {
  try { return require(path.join(path.dirname(vmPath), "jszip")); }
  catch { return null; }
})();

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

const args = process.argv.slice(2);
const dir = args.find((a) => !a.startsWith("--")) ||
  path.join(process.cwd(), "examples", "output");
const STEPS = parseInt(process.env.BOOT_STEPS || "60", 10);

function stepN(vm, n) {
  for (let i = 0; i < n; i++) {
    vm.runtime.currentMSecs += 33;
    vm.runtime._step();
  }
}

const files = fs.readdirSync(dir).filter((f) => f.endsWith(".sb3")).sort();
let pass = 0, fail = 0;
const fails = [];
for (const f of files) {
  const p = path.join(dir, f);
  let ok = true, why = "";
  try {
    const vm = new VirtualMachine();
    vm.runtime.currentStepTime = 1000 / 30;
    // 防御：若本版本 scratch-vm 支持 RUNTIME_ERROR 事件则捕获软错误；
    // 不支持时 on() 是 EventEmitter 空操作，无副作用。
    const errs = [];
    try { vm.runtime.on("RUNTIME_ERROR", (e) => errs.push(e && (e.message || String(e)))); }
    catch { /* ignore */ }

    const buf = fs.readFileSync(p);
    const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
    // 含 music 扩展的工程在 loadProject 时需 AudioContext；headless 注入 no-op 桩。
    if (await projectUsesMusic(buf)) vm.runtime.audioEngine = makeHeadlessAudioStub();
    await vm.loadProject(ab);

    vm.greenFlag();
    stepN(vm, STEPS);

    // 多数游戏只在「开始游戏」广播后才跑主逻辑；触发它可覆盖更多初始化路径。
    // 没有对应帽子时 startHats 是空操作，安全。
    try {
      vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: "开始游戏" });
      stepN(vm, STEPS);
    } catch { /* 该作品无此广播，忽略 */ }

    if (errs.length) { ok = false; why = "运行时错误 " + errs.length + " 处: " + errs.slice(0, 2).join("; "); }
  } catch (e) {
    ok = false;
    why = (e && (e.stack || e.message)) || String(e);
  }
  if (ok) { pass++; console.log("PASS " + f.padEnd(34)); }
  else { fail++; fails.push([f, why]); console.log("FAIL " + f.padEnd(34) + why.split("\n")[0]); }
}

console.log("--------------------------------------------------");
console.log(`启动冒烟 ${files.length} 个 | PASS=${pass} FAIL=${fail}`);
if (fail) {
  console.error("BOOT_SMOKE_FAIL " + fails.map((x) => x[0]).join(","));
  process.exit(1);
}
console.log("BOOT_SMOKE_OK");
process.exit(0);
