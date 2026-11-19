// 射击游戏行为校验：绿旗生成 → 验证玩家/子弹/敌人生命周期、移动、位置碰撞计分、撞玩家扣血/结束。
// 碰撞用「位置数学 + 列表追踪」（不用 touching），所以无头 scratch-vm 也能真实验证。
// 用法: node shooter_behavior_check.mjs <shooter.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_SHOOTER")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node shooter_behavior_check.mjs <shooter.sb3>"); process.exit(2); }

let vm = null; // 在 IIFE 内赋值，供下方助手函数访问

const getVar = (t, name) => {
  for (const id of Object.keys(t.variables || {}))
    if (t.variables[id] && t.variables[id].name === name) return t.variables[id].value;
  return undefined;
};
const setVar = (t, name, val) => {
  for (const id of Object.keys(t.variables || {}))
    if (t.variables[id] && t.variables[id].name === name) { t.variables[id].value = val; return true; }
  return false;
};
const getStageVar = (name) => {
  for (const t of vm.runtime.targets)
    for (const id of Object.keys(t.variables || {}))
      if (t.variables[id] && t.variables[id].name === name) return t.variables[id].value;
  return undefined;
};
const setStageVar = (name, val) => {
  for (const t of vm.runtime.targets)
    for (const id of Object.keys(t.variables || {}))
      if (t.variables[id] && t.variables[id].name === name) { t.variables[id].value = val; return; }
};
const num = (x) => (typeof x === "string" ? parseFloat(x) : x);
// 直接写舞台列表某项（scratch-vm 内部数组为 0 基，Scratch 列表索引为 1 基，故 idx1-1）
const setList = (name, idx1, val) => {
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.lists || {})) {
      if (t.lists[id] && t.lists[id].name === name) { t.lists[id].value[idx1 - 1] = val; return true; }
    }
  }
  return false;
};
const clonesOf = (name) =>
  vm.runtime.targets.filter((t) => t.sprite && t.sprite.name === name && !t.isOriginal);
const spriteExists = (name) =>
  vm.runtime.targets.some((t) => t.sprite && t.sprite.name === name);
// 敌计数器到 60（上限）即「锁死」所有敌人生成（自动节奏 + 手动广播都受 LT(敌计数器,60) 拦截）。
const lockSpawn = () => setStageVar("敌计数器", 60);
const freeSpawn = () => setStageVar("敌计数器", 0);

(async () => {
  vm = new VirtualMachine();
  const buf = fs.readFileSync(sb3Path);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  await vm.loadProject(ab);
  vm.runtime.currentStepTime = 1000 / 30;
  // 不用 turbo：每个 forever 内已加 wait，保证无头逐步推进时每步恰好跑一次身体（确定性）。

  // 固定步数推进，避免「按真实时间」导致每帧被 sleep 循环放大、子弹瞬间飞出屏幕。
  const stepN = async (n) => {
    for (let i = 0; i < n; i++) {
      vm.runtime.currentMSecs += 33;
      vm.runtime._step();
      await Promise.resolve();
    }
  };
  const broadcast = (msg) => vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: msg });
  const disposeAll = (name) => { for (const t of clonesOf(name)) vm.runtime.disposeTarget(t); };

  const bad = [];
  const snap = {};

  // A. 绿旗 → 玩家存在，初始状态正确（VM 变量存字符串，比较用 num 强转）
  vm.greenFlag();
  await stepN(5);
  lockSpawn(); // 关掉自动节奏，全程手动控制敌人数量，避免累加
  setStageVar("__spawn", -100000); // 节律计数器设为负数：整个测试窗口内都不会越过 20，彻底静音自动生成
  if (!spriteExists("玩家")) bad.push("玩家角色缺失");
  if (num(getStageVar("分数")) !== 0) bad.push("初始分数!=0: " + getStageVar("分数"));
  if (num(getStageVar("血量")) !== 3) bad.push("初始血量!=3: " + getStageVar("血量"));
  if (num(getStageVar("游戏结束")) !== 0) bad.push("初始游戏结束!=0: " + getStageVar("游戏结束"));

  // B. 开火守卫：连发 3 次，子弹克隆数应恰好 = 3（克隆不能响应本体事件帽子重复生成）。
  //    此时没有敌人，子弹不会因碰撞消失；每发只产生 1 个克隆，故数确定为 3。
  setStageVar("分数", 0);
  disposeAll("子弹");
  for (let i = 0; i < 3; i++) { broadcast("发射"); await stepN(2); }
  await stepN(3);
  snap.子弹克隆数 = clonesOf("子弹").length;
  if (snap.子弹克隆数 !== 3) bad.push("子弹克隆数=" + snap.子弹克隆数 + "(期望3，验证克隆守卫)");

  // C. 敌人生成：开锁后显式生成 2 个，应恰好 = 2（克隆守卫同样防止指数爆炸）。
  freeSpawn();
  disposeAll("敌人");
  for (let i = 0; i < 2; i++) { broadcast("生成敌人"); await stepN(2); }
  await stepN(3);
  snap.敌人克隆数 = clonesOf("敌人").length;
  lockSpawn();
  if (snap.敌人克隆数 !== 2) bad.push("敌人克隆数=" + snap.敌人克隆数 + "(期望2)");

  // D. 移动：隔离场景——单独 1 子弹 + 1 敌人，放在远离彼此处，避免碰撞干扰。
  //    子弹向上(by 增大)、敌人向下(ey 减小)。
  disposeAll("子弹"); disposeAll("敌人");
  await stepN(2);
  freeSpawn();
  broadcast("发射"); broadcast("生成敌人");
  await stepN(3);
  lockSpawn();
  {
    const b = clonesOf("子弹")[0];
    const e = clonesOf("敌人")[0];
    if (b) { setVar(b, "bx", -150); setVar(b, "by", 0); }
    if (e) { setVar(e, "ex", 150); setVar(e, "ey", 0); } // 远离子弹，不触发碰撞
    const b0 = b ? num(getVar(b, "by")) : null;
    const e0 = e ? num(getVar(e, "ey")) : null;
    await stepN(10);
    const b1 = b ? num(getVar(b, "by")) : null;
    const e1 = e ? num(getVar(e, "ey")) : null;
    if (b && b0 !== null && b1 !== null && !(b1 > b0)) bad.push("子弹未向上移动: " + b0 + "->" + b1);
    if (e && e0 !== null && e1 !== null && !(e1 < e0)) bad.push("敌人未向下移动: " + e0 + "->" + e1);
    if (!b && !e) bad.push("移动测试无可用克隆");
  }

  // E. 位置碰撞计分：放 1 子弹 + 1 敌人于接近同点，应命中 + 敌人被销毁（敌死标记触发删自己）。
  //    列表由游戏自身每步写回，这里只设精灵坐标并把 敌计数器 设为 1（子弹只扫槽位 1，避免误判空槽）。
  disposeAll("子弹"); disposeAll("敌人");
  await stepN(2);
  setStageVar("分数", 0);
  freeSpawn();
  broadcast("发射"); broadcast("生成敌人");
  await stepN(3);
  lockSpawn();
  {
    const b = clonesOf("子弹")[0];
    const e = clonesOf("敌人")[0];
    if (!b) bad.push("碰撞测试无可用的子弹克隆");
    if (!e) bad.push("碰撞测试无可用的敌人克隆");
    if (b && e) {
      setStageVar("敌计数器", 1); // 让子弹只扫描槽位 1
      setVar(b, "bx", 0); setVar(b, "by", -5);    // 略低于敌人，纵向差在命中半径内
      setVar(e, "ex", 0); setVar(e, "ey", 0);
      await stepN(12);
      const score = num(getStageVar("分数"));
      snap.碰撞得分 = score;
      if (!(score >= 1)) bad.push("位置碰撞未计分: 分数=" + score);
      if (vm.runtime.targets.includes(e)) bad.push("被命中的敌人未被销毁(敌死标记未生效)");
    }
  }

  // F. 撞玩家扣血 / 游戏结束：血量=1 时敌人撞玩家 → 结束。
  disposeAll("敌人");
  await stepN(2);
  setStageVar("血量", 1);
  setStageVar("游戏结束", 0);
  freeSpawn();
  broadcast("生成敌人");
  await stepN(3);
  lockSpawn();
  {
    const e = clonesOf("敌人")[0];
    if (!e) bad.push("扣血测试无可用的敌人克隆");
    else {
      setVar(e, "ex", num(getStageVar("玩家x")));
      setVar(e, "ey", num(getStageVar("玩家y"))); // 玩家固定在 (玩家x, -150)
      await stepN(15);
      snap.游戏结束 = num(getStageVar("游戏结束"));
      if (snap.游戏结束 !== 1)
        bad.push("敌人撞玩家未触发结束: 血量=" + getStageVar("血量") + " 游戏结束=" + getStageVar("游戏结束"));
    }
  }

  const actual = {
    玩家存在: spriteExists("玩家"),
    子弹克隆数: snap.子弹克隆数,
    敌人克隆数: snap.敌人克隆数,
    碰撞得分: snap.碰撞得分,
    游戏结束: snap.游戏结束,
  };
  console.log(JSON.stringify({ actual, bad }, null, 2));
  if (bad.length) { console.error("SHOOTER_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("SHOOTER_LOGIC_OK");
})().catch((e) => {
  console.error("SHOOTER_CHECK_FAIL", e && (e.stack || e));
  process.exit(1);
});
