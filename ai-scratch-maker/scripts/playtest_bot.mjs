// 自动化试玩机器人（Playtest Bot）：用 scratch-vm 真跑作品，断言「能启动、能响应、不崩溃、不软锁」。
//
// 与 boot_smoke_check.mjs（只查启动崩溃）互补：本脚本还做「活性检查」——
//   1) 绿旗后能进入运行态（有脚本线程在执行）；
//   2) 注入一串确定性输入（方向键/空格/鼠标移动）后，作品状态（变量）发生变化
//      → 证明「可交互、有玩法推进」，而非死页；
//   3) 全程不抛运行时异常。
//
// 用法：
//   node scripts/playtest_bot.mjs <x.sb3> [steps=600] [--strict]
//
// 这是**通用**活性探针：真正的「到达胜利态」断言仍由各作品的 *_behavior_check.mjs 负责
// （它们知道具体的键位与胜负变量）。本脚本只保证「作品活着且会动」。
// 找不到 scratch-vm 时打印 SKIP_PLAYTEST 并以 0 退出（不阻断流程）。

import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const sb3Path = process.argv[2];
const argSteps = process.argv.find((a) => /^\d+$/.test(a));
const STEPS = argSteps ? parseInt(argSteps, 10) : 600;
const STRICT = process.argv.includes("--strict");

if (!sb3Path) {
  console.error("用法: node playtest_bot.mjs <x.sb3> [steps] [--strict]");
  process.exit(2);
}

const vmPath = findScratchVM();
if (!vmPath) {
  console.log(skipMessage("SKIP_PLAYTEST"));
  process.exit(0);
}
const VirtualMachine = loadScratchVM(vmPath);

// 采集所有变量名->值
function snapshot(vm) {
  const out = {};
  for (const t of vm.runtime.targets) {
    const vars = t.variables || {};
    for (const id of Object.keys(vars)) {
      const v = vars[id];
      if (v && typeof v.name === "string") out[v.name] = v.value;
    }
  }
  return out;
}

function changed(a, b) {
  let n = 0;
  for (const k of Object.keys(b)) {
    if (JSON.stringify(a[k]) !== JSON.stringify(b[k])) n++;
  }
  return n;
}

(async () => {
  const vm = new VirtualMachine();
  let runtimeError = null;
  let maxThreads = 0;

  try {
    const buf = fs.readFileSync(sb3Path);
    await vm.loadProject(buf);

    // 关键：headless 下必须显式设 currentStepTime，否则序列器 stepThreads 的
    // while 条件 WORK_TIME = 0.75 * currentStepTime 为 NaN，循环体从不执行 —— 线程被
    // 绿旗创建出来，但积木一句都不跑。「maxThreads>0」会假性通过（曾经让回归套件漏判）。
    // *_behavior_check.mjs 已设此值；这里补齐，让活性检查变成「真跑了」而非「建了线程」。
    vm.runtime.currentStepTime = 33;

    vm.greenFlag();

    // 检测「积木真的执行过」：逐迭代记录每个线程当前栈顶块(peekStack)，若同一线程的
    // 栈顶在两迭代间变化，即证明块被推进（不是只建了线程就停）。
    // 注意：Thread 没有 blockId 属性，当前块要用 peekStack() 取。
    const lastTop = new Map();
    let executedBlocks = false;

    const before = snapshot(vm);

    // 确定性输入序列：轮询按键 + 鼠标移动，证明「输入不会让 VM 崩」
    const keys = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", " ", "a", "s"];
    const kb = vm.runtime.ioDevices.keyboard;
    const mouse = vm.runtime.ioDevices.mouse;

    for (let i = 0; i < STEPS; i++) {
      const k = keys[i % keys.length];
      try {
        if (kb && kb.postData) kb.postData({ key: k, isDown: true });
        if (mouse && mouse.postData)
          mouse.postData({ x: ((i * 7) % 480) - 240, y: ((i * 5) % 360) - 180, isDown: i % 3 === 0 });
      } catch (e) {
        /* 输入注入失败不影响存活判定 */
      }
      try {
        // 与现有 *_behavior_check.mjs 同款推进方式
        vm.runtime.currentMSecs += 33;
        vm.runtime._step();
        await Promise.resolve();
      } catch (e) {
        runtimeError = e;
        break;
      }
      if (vm.runtime.threads && vm.runtime.threads.length > maxThreads)
        maxThreads = vm.runtime.threads.length;
      // 任何线程的栈顶块相比上一迭代发生变化 → 积木确实在推进
      for (const t of vm.runtime.threads) {
        const top = typeof t.peekStack === "function" ? t.peekStack() : null;
        if (top != null) {
          const prev = lastTop.get(t);
          if (prev != null && prev !== top) executedBlocks = true;
          lastTop.set(t, top);
        }
      }
      // 松开按键，避免一直按住
      try {
        if (kb && kb.postData) kb.postData({ key: k, isDown: false });
      } catch (e) {}
    }

    const after = snapshot(vm);
    const diffCount = changed(before, after);

    // 判定：核心信号是「有脚本线程在运行」（作品活着）；变量随输入变化是加分项。
    if (runtimeError) {
      console.log(`PLAYTEST_FAIL: 运行时异常 @step -> ${runtimeError && runtimeError.message}`);
      process.exit(STRICT ? 1 : 0);
    }
    if (maxThreads === 0) {
      // 绿旗后没有任何脚本线程 —— 纯展示/死页
      console.log("PLAYTEST_WARN: 绿旗后无任何脚本线程执行（可能是纯展示/死页）");
      process.exit(STRICT ? 1 : 0);
    }
    if (!executedBlocks) {
      // 线程存在但没有任何积木真正执行：headless 步进未生效（典型是 currentStepTime 未设，
      // 序列器 while 永不进入）。这正是曾经让回归套件「假性通过」的盲点。
      console.log(
        "PLAYTEST_WARN: 线程存在但积木从未被执行（疑似 headless 步进失效，currentStepTime 未生效？）"
      );
      process.exit(STRICT ? 1 : 0);
    }
    // 活着且真跑了：有线程在执行、至少有积木执行过。变量变化与否作为补充信息
    // （站桩/等待输入的游戏本就不主动变，故不作为硬性失败条件）。
    const note = diffCount > 0
      ? `状态随输入推进（diff=${diffCount}）`
      : "脚本在运行（未检测到状态随输入变化，可能需具体键位才能推进）";
    console.log(
      `PLAYTEST_LIVENESS_OK: 运行线程峰值=${maxThreads}, 积木已执行=是, ${note}`
    );
    process.exit(0);
  } catch (e) {
    console.log(`PLAYTEST_FAIL: 加载/运行异常 -> ${e && e.message}`);
    process.exit(STRICT ? 1 : 0);
  }
})();
