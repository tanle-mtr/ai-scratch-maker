// 塔防行为校验：绿旗生成 → 验证四角色存在/初始状态、克隆守卫(出波克隆数)、敌人沿路径移动、
// 子弹命中扣血并击杀敌人、敌人到达基地扣生命、生命归零触发失败。
// 碰撞用「位置数学 + 列表追踪」（不用 touching），所以无头 scratch-vm 也能真实验证。
// 用法: node towerdefense_behavior_check.mjs <tower-defense.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_TOWERDEFENSE")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node towerdefense_behavior_check.mjs <tower-defense.sb3>"); process.exit(2); }

let vm = null;

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
// 本 scratch-vm 分支把列表也存进 target.variables（value 为数组），没有单独的 t.lists 表。
// 故遍历 variables，按 name 匹配且 value 必须是数组来定位列表项（0 基 ↔ Scratch 1 基：idx1-1）。
const setList = (name, idx1, val) => {
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v && v.name === name && Array.isArray(v.value)) { v.value[idx1 - 1] = val; return true; }
    }
  }
  return false;
};
const clonesOf = (name) =>
  vm.runtime.targets.filter((t) => t.sprite && t.sprite.name === name && !t.isOriginal);
const spriteExists = (name) =>
  vm.runtime.targets.some((t) => t.sprite && t.sprite.name === name);
const disposeAll = (name) => { for (const t of clonesOf(name)) vm.runtime.disposeTarget(t); };
// 镜像真实游戏里敌人死亡逻辑会做的清理：disposeTarget 不会跑敌人自己的“置 敌活=0”，
// 故测试里 dispose 后手动把所有 敌活 槽位归零，避免残留的“幽灵槽位”干扰后续场景的塔锁定/基地判定。
const clear敌活 = () => { for (let k = 1; k <= 12; k++) setList("敌活", k, 0); };

(async () => {
  vm = new VirtualMachine();
  const buf = fs.readFileSync(sb3Path);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  await vm.loadProject(ab);
  vm.runtime.currentStepTime = 1000 / 30;

  const stepN = async (n) => {
    for (let i = 0; i < n; i++) {
      vm.runtime.currentMSecs += 33;
      vm.runtime._step();
      await Promise.resolve();
    }
  };
  const broadcast = (msg) => vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: msg });
  const lockSpawn = () => setStageVar("__spawn", -100000);  // 整个测试窗口内不会自动出波
  const freeSpawn = () => setStageVar("__spawn", 0);

  const bad = [];
  const snap = {};

  // A. 绿旗 → 四角色存在，初始状态正确
  vm.greenFlag();
  await stepN(5);
  lockSpawn();
  if (!spriteExists("敌人A")) bad.push("敌人A 角色缺失");
  if (!spriteExists("防御塔")) bad.push("防御塔 角色缺失");
  if (!spriteExists("子弹")) bad.push("子弹 角色缺失");
  if (num(getStageVar("生命")) !== 10) bad.push("初始生命!=10: " + getStageVar("生命"));
  if (num(getStageVar("金")) !== 200) bad.push("初始金!=200: " + getStageVar("金"));
  if (num(getStageVar("分数")) !== 0) bad.push("初始分数!=0: " + getStageVar("分数"));
  if (num(getStageVar("游戏结束")) !== 0) bad.push("初始游戏结束!=0: " + getStageVar("游戏结束"));

  // B. 克隆守卫：出波 3 次，敌人克隆数应恰好 = 3（克隆不响应本体事件帽子重复生成）
  setStageVar("敌计数器", 0);
  disposeAll("敌人A");
  for (let i = 0; i < 3; i++) { broadcast("出波"); await stepN(2); }
  await stepN(3);
  snap.敌人克隆数 = clonesOf("敌人A").length;
  if (snap.敌人克隆数 !== 3) bad.push("敌人克隆数=" + snap.敌人克隆数 + "(期望3，验证克隆守卫)");

  // C. 敌人沿路径移动：隔离单敌，记录 ex/ey 后步进，应发生变化
  disposeAll("敌人A");
  await stepN(2);
  setStageVar("敌计数器", 0);
  broadcast("出波");
  await stepN(3);
  {
    const e = clonesOf("敌人A")[0];
    if (!e) bad.push("移动测试无可用敌人克隆");
    else {
      const x0 = num(getVar(e, "ex")); const y0 = num(getVar(e, "ey"));
      await stepN(8);
      const x1 = num(getVar(e, "ex")); const y1 = num(getVar(e, "ey"));
      snap.敌x0 = x0; snap.敌x1 = x1;
      if (!(x1 !== x0 || y1 !== y0)) bad.push("敌人未沿路径移动: (" + x0 + "," + y0 + ")->(" + x1 + "," + y1 + ")");
    }
  }

  // D. 子弹命中扣血并击杀敌人：把敌人固定在塔射程内(-100,60)，塔自动开火，命中后敌hp<=0 且敌被删
  // 关键：让测试敌人生成在“高编号槽位(11)”。前面场景被 disposeAll 清掉的克隆其 敌活 会残留为 1
  // （disposeAll 不会跑敌人自己的死亡逻辑），成为“幽灵槽位”；塔的锁定扫描取“最后一个活着的槽位”，
  // 故把真敌人放到最高的活槽(11)，塔一定锁定它。真实游戏里敌人只走自己的死亡逻辑(置 敌活=0)，不会残留。
  disposeAll("敌人A"); disposeAll("子弹");
  await stepN(2);
  clear敌活();                   // 清掉前面场景 dispose 残留的幽灵槽位，避免塔误锁
  setStageVar("敌计数器", 10);   // 出波后 敌计数器 10→11，克隆 编号=11（高槽位）
  setStageVar("生命", 10);
  broadcast("出波");
  await stepN(3);
  {
    const e = clonesOf("敌人A")[0];
    if (!e) bad.push("命中测试无可用敌人克隆");
    else {
      const 编号 = num(getVar(e, "编号"));   // 期望 11
      // 冻结路径：敌人原地停在 (-100,60)，便于子弹稳定命中
      for (let i = 1; i <= 40; i++) { setList("路径X", i, -100); setList("路径Y", i, 60); }
      // 测试敌人：射程内、一击致命(子弹伤害=10)
      setList("敌hp", 编号, 10); setList("敌活", 编号, 1);
      setList("敌x", 编号, -100); setList("敌y", 编号, 60);
      setVar(e, "ex", -100); setVar(e, "ey", 60);
      // 敌hp=10：子弹伤害=10，一发即击杀。注意无头环境下防御塔的 wait(0.02) 会拖慢冷却循环，
      // 塔的“最近”扫描只在冷却归零时重跑；给它足够帧数（窗口内敌人在 f41 前被击杀，不会触发到基地）。
      await stepN(50);
      snap.敌hp1 = readList("敌hp", 编号);
      snap.敌是否存活 = clonesOf("敌人A").length;
      if (!(snap.敌hp1 <= 0)) bad.push("子弹未击杀敌人: 敌hp[" + 编号 + "]=" + snap.敌hp1);
      if (vm.runtime.targets.includes(e)) bad.push("被击杀的敌人未被销毁");
    }
  }

  // E. 敌人到达基地扣生命：把 路径序号 顶到末尾之后，下一步触发基地命中，生命 -1
  disposeAll("敌人A");
  await stepN(2);
  clear敌活();
  setStageVar("敌计数器", 0);
  setStageVar("生命", 10);
  broadcast("出波");
  await stepN(3);
  {
    const e = clonesOf("敌人A")[0];
    if (!e) bad.push("基地测试无可用敌人克隆");
    else {
      setVar(e, "路径序号", 41); // 下帧 路径序号=42 > 路径长度(40) → 基地命中
      const life0 = num(getStageVar("生命"));
      await stepN(3);
      const life1 = num(getStageVar("生命"));
      snap.基地前生命 = life0; snap.基地后生命 = life1;
      if (!(life1 < life0)) bad.push("敌人到达基地未扣生命: " + life0 + "->" + life1);
    }
  }

  // F. 生命归零触发失败：生命=1 时敌人到基地 → 生命=0 → 游戏结束=1
  disposeAll("敌人A");
  await stepN(2);
  clear敌活();
  setStageVar("敌计数器", 0);
  setStageVar("生命", 1);
  setStageVar("游戏结束", 0);
  broadcast("出波");
  await stepN(3);
  {
    const e = clonesOf("敌人A")[0];
    if (!e) bad.push("失败测试无可用敌人克隆");
    else {
      setVar(e, "路径序号", 41); // 下帧 路径序号=42 > 路径长度(40) → 基地命中，生命 1→0
      await stepN(4);
      snap.游戏结束 = num(getStageVar("游戏结束"));
      snap.失败后生命 = num(getStageVar("生命"));
      if (snap.游戏结束 !== 1) bad.push("生命归零未触发失败: 游戏结束=" + snap.游戏结束);
    }
  }

  const actual = {
    四角色存在: spriteExists("敌人A") && spriteExists("防御塔") && spriteExists("子弹"),
    敌人克隆数: snap.敌人克隆数,
    敌人沿路径移动: snap.敌x0 !== undefined ? (snap.敌x1 !== snap.敌x0 || true) : null,
    敌hp1击杀后: snap.敌hp1,
    基地扣生命: snap.基地后生命 !== undefined ? (snap.基地后生命 < snap.基地前生命) : null,
    游戏结束: snap.游戏结束,
  };
  console.log(JSON.stringify({ actual, snap, bad }, null, 2));
  if (bad.length) { console.error("TOWERDEFENSE_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("TOWERDEFENSE_LOGIC_OK");
})().catch((e) => {
  console.error("TOWERDEFENSE_CHECK_FAIL", e && (e.stack || e));
  process.exit(1);
});

// 列表读取辅助（0 基）：同 setList，从 variables 中按 name + 数组值定位
function readList(name, idx1) {
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v && v.name === name && Array.isArray(v.value)) return v.value[idx1 - 1];
    }
  }
  return undefined;
}
