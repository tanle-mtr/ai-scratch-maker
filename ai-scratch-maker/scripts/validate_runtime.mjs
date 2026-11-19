// 运行时校验：用 scratch-vm 真正加载 project.json 并步进运行若干帧。
// 用法: node validate_runtime.mjs <project.json 路径>
//
// scratch-vm 定位顺序：
//   1) 环境变量 SCRATCH_VM_PATH
//   2) skill 内置 node_modules/scratch-vm（若随包分发）
//   3) 本机常见位置（~/.workbuddy/sb3_poc_runtime、./node_modules 等）
// 找不到时输出 SKIP_RUNTIME 并以 0 退出 —— 由调用方判定为「跳过」而非「失败」。
import fs from "fs";
import { createRequire } from "module";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const require = createRequire(import.meta.url);

const vmPath = findScratchVM();
if (!vmPath) {
  console.error(skipMessage("SKIP_RUNTIME"));
  process.exit(0);
}

let VirtualMachine;
try {
  VirtualMachine = loadScratchVM(vmPath);
} catch (e) {
  console.error("SKIP_RUNTIME 加载 scratch-vm 失败：" + (e && e.message));
  process.exit(0);
}

const projPath = process.argv[2];
if (!projPath) {
  console.error("usage: node validate_runtime.mjs <project.json>");
  process.exit(2);
}

const json = JSON.parse(fs.readFileSync(projPath, "utf8"));

(async () => {
  const vm = new VirtualMachine();
  // headless 校验：置空 storage，让 scratch-vm 跳过素材（声音/位图）加载，
  // 只验证「脚本能被解析、targets 能建立、绿旗可触发并步进运行不抛异常」。
  // （真实 Scratch 编辑器会注入 audioEngine / renderer / storage，此处不需要。）
  try {
    // 关键：runtime.start() 才会设置 currentStepTime，
    // 而 sequencer.stepThreads() 用它算每帧的 WORK_TIME。
    // 不设置的话 while 循环的比较是 x < NaN（恒为 false），脚本根本不会执行，
    // 「运行不抛异常」就成了假通过。
    vm.runtime.currentStepTime = 1000 / 30;
    vm.setTurboMode(true);          // 无渲染器时也能持续步进
  } catch (e) { /* ignore */ }

  try {
    await vm.loadProject(json);
  } catch (e) {
    console.error("RUNTIME_FAIL loadProject:", e && e.stack);
    process.exit(1);
  }

  try {
    vm.greenFlag();
    for (let i = 0; i < 60; i++) vm.runtime._step();
    vm.stopAll();
  } catch (e) {
    console.error("RUNTIME_FAIL run:", e && e.stack);
    process.exit(1);
  }

  const nTargets = vm.runtime && vm.runtime.targets ? vm.runtime.targets.length : 0;
  // 报告确实执行过的线程数，避免「脚本其实没跑」的假通过
  const nThreads = vm.runtime && vm.runtime.threads ? vm.runtime.threads.length : 0;
  console.log("RUNTIME_OK targets=" + nTargets + " threads=" + nThreads);
  process.exit(0);
})().catch((e) => {
  console.error("RUNTIME_FAIL unexpected:", e && e.stack);
  process.exit(1);
});
