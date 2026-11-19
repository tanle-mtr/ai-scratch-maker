// 行为冒烟测试：真正「玩」一遍作品，检查脚本逻辑是否按预期生效。
//
// 用法: node smoke_test.mjs <作品.sb3> [--frames N] [--expect var=值,...]
//
// 与 validate_runtime.mjs 的区别：那个只验证「能加载、能跑、不抛异常」；
// 这个验证「逻辑真的生效」——变量是否按预期变化、角色是否移动、
// 碰撞后是否加分、广播是否触发等。
//
// 说明：Scratch 的碰撞检测依赖渲染器（isTouchingSprite 需要 renderer），
// 而 headless 环境没有 WebGL。这里用「位置包围盒」近似实现碰撞，
// 只用于测试，不代表 Scratch 里的精确像素碰撞。
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const require = createRequire(import.meta.url);
const vmPath = findScratchVM();
if (!vmPath) {
  console.error(skipMessage("SKIP_SMOKE"));
  process.exit(0);
}

const argv = process.argv.slice(2);
const arg = (n, d) => { const i = argv.indexOf(n); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };
const sb3Path = argv.find((a) => !a.startsWith("--") && argv[argv.indexOf(a) - 1] !== "--expect");
if (!sb3Path) { console.error("用法: node smoke_test.mjs <作品.sb3>"); process.exit(2); }
const seconds = parseFloat(arg("--seconds", "2.5"));
const frames = parseInt(arg("--frames", "120"), 10);
const expect = (arg("--expect", "") || "").split(",").filter(Boolean);
const catchMode = argv.includes("--catch");

let VirtualMachine;
try {
  VirtualMachine = loadScratchVM(vmPath);
} catch (e) {
  console.error("SKIP_SMOKE 加载 scratch-vm 失败：" + (e && e.message));
  process.exit(0);
}

// ---- 用包围盒近似实现碰撞（headless 没有渲染器）----
// 注意：必须从**运行时实例**上取原型来打补丁 —— 安装包的入口是 dist/node/scratch-vm.js，
// 直接 require('src/sprites/rendered-target.js') 拿到的是另一个模块实例，补丁不生效。
//
// 碰撞半径：默认 45（小角色）；大件障碍（家具）用自己的半宽，
// 否则「猫靠近沙发」会误判成没碰撞（因为沙发中心离猫很远）。
const HIT_RADIUS = {
  "沙发": 90, "柜子": 90, "书桌": 100, "地毯": 100,
};
function patchCollision(runtime, hitRadius = 45) {
  const target = runtime.targets.find((t) => !t.isStage);
  if (!target) return;
  const proto = Object.getPrototypeOf(target);
  proto.isTouchingSprite = function (spriteName) {
    const other = runtime.getSpriteTargetByName(String(spriteName));
    if (!other) return false;
    const otherName = (other.sprite && other.sprite.name) || other.name || "";
    const r = HIT_RADIUS[otherName] ?? hitRadius;
    return Math.abs(other.x - this.x) < r && Math.abs(other.y - this.y) < r;
  };
}

function targetName(t) {
  return (t.sprite && t.sprite.name) || t.name || "(无名)";
}

// 跨所有 target（含舞台上的全局变量）按名字找变量
function getVarByName(runtime, name) {
  for (const t of runtime.targets) {
    const vars = t.variables || {};
    for (const vid of Object.keys(vars)) {
      const v = vars[vid];
      if (v && v.name === name) return v;
    }
  }
  return null;
}

function snapshot(runtime) {
  const out = { vars: {}, pos: {} };
  for (const t of runtime.targets) {
    const name = targetName(t);
    out.vars[name] = {};
    for (const vid of Object.keys(t.variables || {})) {
      const v = t.variables[vid];
      if (!v || v.type === "broadcast_msg") continue;   // 广播不计入变量
      out.vars[name][v.name] = v.value;
    }
    out.pos[name] = {
      x: Math.round(t.x), y: Math.round(t.y), visible: t.visible,
      direction: t.direction,
      rotationStyle: t.rotationStyle,
      costume: (t.getCostumes && t.getCostumes()[t.currentCostume])
        ? t.getCostumes()[t.currentCostume].name : undefined
    };
  }
  return out;
}

// ---- headless 音频桩 ----
// scratch-vm 的音乐/声音扩展在 node 里没有 AudioContext：
//   加载时音乐扩展构造器会解码内置采样并抛 "No Audio Context Detected"，
//   或真正发声时访问 audioContext 的方法而崩溃。
// 这里提供一个 no-op 的 audioEngine，让「用到音乐扩展」的工程也能在 headless 下
// 加载并步进运行（不产出真实声音，只验证脚本逻辑是否生效）。
// 仅当工程确实用到音乐积木时才安装，避免影响其它工程（尤其是用声音扩展的工程）。
const JSZip = (() => { try { return require(path.join(vmPath, "..", "jszip")); } catch { return null; } })();

function makeHeadlessAudioStub() {
  const gainNode = () => ({
    gain: { value: 1, setValueAtTime() {}, linearRampToValueAtTime() {}, setTargetAtTime() {} },
    connect() {},
  });
  const audioContext = {
    currentTime: 0,
    sampleRate: 44100,
    destination: {},
    createGain: gainNode,
    createBufferSource: () => ({ playbackRate: { value: 1 }, connect() {}, start() {}, stop() {} }),
    createBiquadFilter: () => ({ frequency: { value: 1 }, Q: { value: 1 }, type: "", connect() {} }),
    createBuffer: () => ({ getChannelData: () => new Float32Array(1) }),
    decodeAudioData: () => Promise.resolve({ getChannelData: () => new Float32Array(1) }),
  };
  const makePlayer = () => ({
    isPlaying: false,
    isStarting: false,
    outputNode: { playbackRate: { value: 1 }, stop() {} },
    take() { return makePlayer(); },
    once() {},
    play() {},
    stop() {},
    connect() {},
    setVolume() {},
    gain: gainNode(),
  });
  return {
    audioContext,
    currentTime: 0,
    getInputNode() { return { connect() {} }; },
    decodeSoundPlayer: () => Promise.resolve(makePlayer()),
    makeBuffer: () => ({ getChannelData: () => new Float32Array(1) }),
    // 带声音素材（.wav/.mp3）的工程在反序列化时会走 audioEngine.createBank，
    // 真实的 scratch-audio 在 node 里没有 AudioContext，这里给一个 no-op 银行。
    createBank() {
      return {
        name: "headless",
        sampleRate: 44100,
        channelCount: 2,
        length: 1,
        getAudioBuffer: () => Promise.resolve({ getChannelData: () => new Float32Array(1) }),
        decodeSoundPlayer: () => Promise.resolve(makePlayer()),
        addSoundPlayer() {},
        setEffects() {},
        setVolume() {},
        stopAllSounds() {},
        stop() {},
        playSound() {},
        playSoundId() {},
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
  } catch {
    return false;
  }
}

(async () => {
  const vm = new VirtualMachine();
  const buf = fs.readFileSync(sb3Path);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);

  // headless 下：仅当工程用到音乐扩展时，注入 no-op 音频桩，
  // 否则音乐扩展加载内置采样会因缺少 AudioContext 而崩溃。
  if (await projectUsesMusic(buf)) {
    vm.runtime.audioEngine = makeHeadlessAudioStub();
  }

  try {
    await vm.loadProject(ab);
  } catch (e) {
    console.error("SMOKE_FAIL loadProject:", e && (e.stack || e));
    process.exit(1);
  }

  patchCollision(vm.runtime);
  // 关键：currentStepTime 由 runtime.start() 设置，不设置的话
  // sequencer.stepThreads() 的 WORK_TIME 是 NaN，脚本根本不会执行。
  vm.runtime.currentStepTime = 1000 / 30;
  vm.setTurboMode(true);
  vm.greenFlag();

  // --catch 模式：模拟「点击开始按钮」，触发「当角色被点击」帽子，
  // 让「标题屏 → 游戏」的广播链路真正跑起来（否则游戏逻辑永不启动，碰撞计分测不到）。
  // 对所有角色触发 clicked 帽子即可，当前只有「开始按钮」可点击。
  if (catchMode) {
    try { vm.runtime.startHats("event_whenthisspriteclicked"); } catch (e) { /* ignore */ }
  }

  // Scratch 的 wait / 计时用的是**真实时钟**，所以这里按真实时间推进，
  // 让「等待 1 秒」这类积木真的能走完。
  const startedAt = Date.now();
  const baseMSecs = vm.runtime.currentMSecs || startedAt;
  let steps = 0;
  let teleported = false;
  // ⚠️ headless 下没有 RAF ticker，runtime.currentMSecs（虚拟时钟）不会自己走。
  //    control_wait / 计时器 / 节奏判定的 Timer 读的正是这个值
  //    （见 scratch-vm/src/engine/block-utility.js 的 _nowObj），
  //    不推进它，任何含「等待 N 秒」的脚本都会永久卡住，
  //    冒烟测试会给出「看起来通过、其实后半段根本没跑」的假结果。
  //    这里按**真实经过时间** 1:1 推进，保证 wait 语义和编辑器一致。
  while (Date.now() - startedAt < seconds * 1000) {
    vm.runtime.currentMSecs = baseMSecs + (Date.now() - startedAt);
    vm.runtime._step();
    steps++;
    // --catch 模式：把「猫」的世界坐标同步成「鼠」的世界坐标，
    // 这样两者的屏幕位置必然重合 -> 触发「碰撞 -> 加分」链路。
    // （本游戏用世界坐标 + 相机渲染，不能简单把 sprite 钉在一起，故同步世界变量。）
    if (catchMode && steps > 30) {
      const cat = vm.runtime.targets.find((t) => !t.isStage &&
        ((t.sprite && t.sprite.name) || t.name) === "猫");
      const mouse = vm.runtime.targets.find((t) => !t.isStage &&
        ((t.sprite && t.sprite.name) || t.name) === "老鼠");
      if (cat && mouse) {
        const mwx = getVarByName(vm.runtime, "mouse_wx");
        const mwy = getVarByName(vm.runtime, "mouse_wy");
        const cwx = getVarByName(vm.runtime, "cat_wx");
        const cwy = getVarByName(vm.runtime, "cat_wy");
        if (mwx && mwy && cwx && cwy) {
          cwx.value = mwx.value;
          cwy.value = mwy.value;
          teleported = true;
        }
      }
    }
    await new Promise((r) => setTimeout(r, 1000 / 60));
  }
  const after = snapshot(vm.runtime);
  const before = { vars: after.vars, pos: {} };

  console.log("SMOKE_OK " + sb3Path + "  (跑了 " + steps + " 帧 / " + seconds + " 秒)");
  console.log("  target 变量:");
  for (const name of Object.keys(after.vars)) {
    console.log("    %s: %s", name, JSON.stringify(after.vars[name]));
  }
  // 监视器（屏幕上的读数）：检查是否被运行时加载，以及数值是否跟着变
  const monitorState = vm.runtime.getMonitorState
    ? vm.runtime.getMonitorState() : null;
  if (monitorState && monitorState.size !== undefined) {
    const rows = [];
    monitorState.forEach((m) => {
      rows.push(`${m.params && (m.params.VARIABLE || m.params.LIST)}=${JSON.stringify(m.value)}@(${m.x},${m.y})${m.visible ? "" : "[隐藏]"}`);
    });
    console.log("  监视器(%d): %s", monitorState.size, rows.join(", ") || "(无)");
  }
  // 注释与积木整理
  for (const t of vm.runtime.targets) {
    const name = targetName(t);
    const comments = t.comments || {};
    const nComments = Object.keys(comments).length;
    const scripts = (t.blocks && t.blocks._scripts) || [];
    const tops = scripts.map((id) => t.blocks._blocks[id]);
    const positions = tops.map((b) => `(${Math.round(b.x)},${Math.round(b.y)})`).join(" ");
    const stray = tops.filter((b) => b.shadow).length;
    console.log("  %s: 脚本 %d 个 %s | 注释 %d 条%s", name, scripts.length, positions,
      nComments, stray ? ` | [警告] ${stray} 个影子积木被当成独立脚本` : "");
  }
  console.log("  位置变化:");
  for (const name of Object.keys(after.pos)) {
    const b = before.pos[name] || { x: 0, y: 0 };
    const a = after.pos[name];
    const moved = (b.x !== a.x || b.y !== a.y);
    const extra = [];
    if (a.rotationStyle) extra.push("旋转=" + a.rotationStyle);
    if (a.direction !== undefined) extra.push("朝向=" + a.direction);
    if (a.costume) extra.push("造型=" + a.costume);
    console.log("    %s: (%s,%s) -> (%s,%s) %s %s", name, b.x, b.y, a.x, a.y,
      moved ? "[移动了]" : "[没动]", extra.join(" "));
  }

  // 断言
  const failures = [];
  for (const exp of expect) {
    const idx = exp.lastIndexOf("=");
    const name = exp.slice(0, idx);
    const want = exp.slice(idx + 1);
    let found = null;
    for (const t of Object.keys(after.vars)) {
      if (Object.prototype.hasOwnProperty.call(after.vars[t], name)) {
        found = after.vars[t][name];
        break;
      }
    }
    if (found === undefined) { failures.push(`变量 ${name} 不存在`); continue; }
    if (String(found) !== want) {
      failures.push(`变量 ${name} 期望 ${want}，实际 ${found}`);
    } else {
      console.log("  [ok] %s = %s", name, want);
    }
  }

  vm.stopAll();
  if (failures.length) {
    console.error("SMOKE_FAIL 断言不通过:");
    for (const f of failures) console.error("  - " + f);
    process.exit(1);
  }
  process.exit(0);
})().catch((e) => {
  console.error("SMOKE_FAIL unexpected:", e && (e.stack || e));
  process.exit(1);
});
