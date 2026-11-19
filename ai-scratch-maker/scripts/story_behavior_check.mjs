// 分支叙事（视觉小说）行为校验：验证打字机逐字显示、分支跳转、双结局到达、对话锁。
// 用法: node story_behavior_check.mjs <story.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_STORY")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node story_behavior_check.mjs <story.sb3>"); process.exit(2); }

let vm = null;
const num = (x) => (typeof x === "string" ? parseFloat(x) : x);
const getStageVar = (name) => {
  for (const t of vm.runtime.targets)
    for (const id of Object.keys(t.variables || {}))
      if (t.variables[id] && t.variables[id].name === name) return t.variables[id].value;
  return undefined;
};
const getSpriteX = (name) => {
  for (const t of vm.runtime.targets)
    if (t.sprite && t.sprite.name === name) return num(t.x);
  return undefined;
};

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
  // 跑到「当前文本非空 且 显示文本已追平当前文本」——即本节点打字机完成。
  // 注意：必须先 step 再判断，否则「切换节点瞬间 显示文本==当前文本(旧值)」会让循环在广播处理前就提前退出。
  const runUntilTyped = async (cap = 400) => {
    let g = 0;
    while (g < cap) {
      await stepN(1); g++;
      if (getStageVar("当前文本") !== "" && getStageVar("显示文本") === getStageVar("当前文本")) break;
    }
    return g < cap;
  };

  const bad = [];
  const snap = {};

  // A. 绿旗 → 节点1 旁白，打字机逐字显示完成，等待「推进」
  vm.greenFlag();
  const okA = await runUntilTyped();
  snap.绿旗后节点 = num(getStageVar("当前节点"));
  snap.显示文本1 = getStageVar("显示文本");
  snap.对话中1 = num(getStageVar("对话中"));
  snap.待推进1 = num(getStageVar("待推进"));
  snap.待选择1 = num(getStageVar("待选择"));
  if (!okA) bad.push("节点1 打字机未完成");
  if (snap.绿旗后节点 !== 1) bad.push("绿旗后当前节点!=1: " + snap.绿旗后节点);
  if (snap.显示文本1 !== "你醒来在神秘森林。") bad.push("节点1 文字不符: " + snap.显示文本1);
  if (snap.对话中1 !== 1) bad.push("对话中未置1(对话锁未开): " + snap.对话中1);
  if (snap.待推进1 !== 1) bad.push("节点1 未进入待推进: " + snap.待推进1);
  if (snap.待选择1 !== 0) bad.push("节点1 误入待选择: " + snap.待选择1);

  // B. 对话锁：对话中=1 时发「移动」玩家不应动
  const x0 = getSpriteX("玩家");
  broadcast("移动"); await stepN(3);
  snap.对话中移动后x = getSpriteX("玩家");
  if (snap.对话中移动后x !== x0) bad.push("对话锁失效：对话中仍被移动 (" + x0 + "→" + snap.对话中移动后x + ")");

  // C. 推进 → 节点2 选择节点（二选一）
  broadcast("推进"); await runUntilTyped();
  snap.节点2 = num(getStageVar("当前节点"));
  snap.显示文本2 = getStageVar("显示文本");
  snap.待选择2 = num(getStageVar("待选择"));
  if (snap.节点2 !== 2) bad.push("推进后未到节点2: " + snap.节点2);
  if (snap.显示文本2 !== "精灵：你要往哪走？") bad.push("节点2 文字不符: " + snap.显示文本2);
  if (snap.待选择2 !== 1) bad.push("节点2 未进入待选择: " + snap.待选择2);

  // D. 选 B（向右走）→ 节点4 旁白 → 推进 → 节点6 结局二
  broadcast("选B"); await runUntilTyped();
  snap.选B后节点 = num(getStageVar("当前节点"));
  snap.显示文本4 = getStageVar("显示文本");
  if (snap.选B后节点 !== 4) bad.push("选B后未到节点4: " + snap.选B后节点);
  if (snap.显示文本4 !== "右边有一只怪物……") bad.push("节点4 文字不符: " + snap.显示文本4);

  broadcast("推进"); await runUntilTyped();
  snap.结局节点 = num(getStageVar("当前节点"));
  snap.结局 = num(getStageVar("结局"));
  snap.结局2计数 = num(getStageVar("结局2计数"));
  snap.结局后对话中 = num(getStageVar("对话中"));
  if (snap.结局节点 !== 6) bad.push("选B路径未到结局节点6: " + snap.结局节点);
  if (snap.结局 !== 2) bad.push("选B未触发结局二(结局!=2): " + snap.结局);
  if (snap.结局2计数 !== 1) bad.push("结局二计数!=1: " + snap.结局2计数);
  if (snap.结局后对话中 !== 0) bad.push("结局后对话锁未放开(对话中!=0): " + snap.结局后对话中);

  // E. 结局后对话锁放开：此时「移动」应真正移动玩家
  const xBefore = getSpriteX("玩家");
  broadcast("移动"); await stepN(3);
  snap.结局后移动x = getSpriteX("玩家");
  if (snap.结局后移动x !== xBefore + 10) bad.push("结局后对话锁未放开：移动无效 (" + xBefore + "→" + snap.结局后移动x + ")");

  // F. 重开并走选 A 路径 → 节点3 旁白 → 推进 → 节点5 结局一
  vm.greenFlag(); await runUntilTyped();
  broadcast("推进"); await runUntilTyped();   // 节点2
  broadcast("选A"); await runUntilTyped();   // 节点3
  broadcast("推进"); await runUntilTyped();   // 节点5 结局一
  snap.选A路径节点 = num(getStageVar("当前节点"));
  snap.选A结局 = num(getStageVar("结局"));
  snap.结局1计数 = num(getStageVar("结局1计数"));
  if (snap.选A路径节点 !== 5) bad.push("选A路径未到结局节点5: " + snap.选A路径节点);
  if (snap.选A结局 !== 1) bad.push("选A未触发结局一(结局!=1): " + snap.选A结局);
  if (snap.结局1计数 !== 1) bad.push("结局一计数!=1: " + snap.结局1计数);

  const actual = {
    绿旗后节点: snap.绿旗后节点, 节点2: snap.节点2, 选B后节点: snap.选B后节点,
    结局: snap.结局, 结局2计数: snap.结局2计数, 选A结局: snap.选A结局, 结局1计数: snap.结局1计数,
  };
  console.log(JSON.stringify({ actual, bad }, null, 2));
  if (bad.length) { console.error("STORY_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("STORY_LOGIC_OK");
})().catch((e) => { console.error("STORY_CHECK_FAIL", e && (e.stack || e)); process.exit(1); });
