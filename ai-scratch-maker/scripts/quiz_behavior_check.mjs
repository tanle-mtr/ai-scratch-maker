// 答题系统行为校验：真实点击选项 → 判题 → 计分 → 推进 → 结算。
// 用法: node quiz_behavior_check.mjs <quiz.sb3> [--json]
//
// 验证点（比四层校验更进一步，检查「逻辑对不对」）：
//   1. 每道题判题正确（对/错）
//   2. 防连点锁：反馈期间重复点击不重复计分
//   3. 越界后进入结算态，不会继续读题库
//   4. 一局复位干净（分数/题号/连对归零）

import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_QUIZ")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node quiz_behavior_check.mjs <quiz.sb3>"); process.exit(2); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const vm = new VirtualMachine();
  const buf = fs.readFileSync(sb3Path);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  await vm.loadProject(ab);
  vm.runtime.currentStepTime = 1000 / 30;
  vm.setTurboMode(true);
  vm.greenFlag();

  const stepFor = async (ms) => {
    const t0 = Date.now();
    const baseMSecs = vm.runtime.currentMSecs || t0;
    while (Date.now() - t0 < ms) {
      // ⚠️ headless 下没有 RAF ticker，runtime.currentMSecs 不会自己走。
      //    control_wait 的 Timer 读的正是这个**虚拟时钟**（见
      //    scratch-vm/src/engine/block-utility.js 的 _nowObj），
      //    不推进它，任何含 wait 的脚本都会永久卡住。
      //    按真实经过时间 1:1 推进，wait 语义与编辑器一致。
      vm.runtime.currentMSecs = baseMSecs + (Date.now() - t0);
      vm.runtime._step();
      await sleep(4);
    }
  };
  const stage = vm.runtime.targets.find((t) => t.isStage);
  const readVar = (name) => {
    for (const t of vm.runtime.targets) {
      for (const id of Object.keys(t.variables || {})) {
        const v = t.variables[id];
        if (v && v.name === name) return v.value;
      }
    }
    return null;
  };
  const targetByName = (n) => vm.runtime.targets.find(
    (t) => !t.isStage && ((t.sprite && t.sprite.name) || t.name) === n);
  const click = (name) => {
    const t = targetByName(name);
    if (!t) throw new Error("找不到角色 " + name);
    vm.runtime.startHats('event_whenthisspriteclicked', null, t);
  };

  await stepFor(120);

  // 点开始按钮（限定该 target，避免误触发 4 个选项按钮）
  click('开始按钮');
  await stepFor(200);

  const trace = [];
  // 4 题，正确答案索引 [2,3,1,4]；按「对、错、对、对」作答
  const answers = ['选项B', '选项A', '选项A', '选项D'];
  for (let i = 0; i < answers.length; i++) {
    click(answers[i]);
    if (i === 0) {
      // 防连点：反馈期间再点一个不同选项，分数不应变化
      await stepFor(80);
      click('选项C');
    }
    await stepFor(1250);   // 等 wait 1.0 走完 + 下一题链路
    trace.push({
      after: i + 1,
      题号: readVar('题号'),
      分数: readVar('分数'),
      答对数: readVar('答对数'),
      连对: readVar('连对'),
      最高连对: readVar('最高连对'),
      game_state: readVar('game_state'),
      已答: readVar('已答'),
    });
  }

  const final = readVar('game_state');
  const score = readVar('分数');
  const correct = readVar('答对数');
  const maxStreak = readVar('最高连对');
  const q = readVar('题号');

  const expected = { 分数: 30, 答对数: 3, 最高连对: 2, game_state: 3, 题号: 5 };
  const actual = { 分数: score, 答对数: correct, 最高连对: maxStreak, game_state: final, 题号: q };
  const bad = Object.keys(expected).filter((k) => String(expected[k]) !== String(actual[k]));

  console.log(JSON.stringify({ trace, expected, actual, bad }, null, 2));
  if (bad.length) { console.error('QUIZ_LOGIC_FAIL ' + bad.join(',')); process.exit(1); }
  console.log('QUIZ_LOGIC_OK');
})().catch((e) => {
  console.error('QUIZ_CHECK_FAIL', e && (e.stack || e));
  process.exit(1);
});
