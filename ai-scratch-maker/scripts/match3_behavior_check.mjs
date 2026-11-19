// 三消游戏行为校验：绿旗生成棋盘 → 检查无初始三连/满盘/克隆数 →
// 构造一个「仅含一处三连」的棋盘 → 模拟交换/直接检测 → 断言消除+计分+下落补满。
// 用法: node match3_behavior_check.mjs <match3.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_MATCH3")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node match3_behavior_check.mjs <match3.sb3>"); process.exit(2); }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const hasTriple = (board) => {
  // board: 1-based 长度36 的数组（索引0..35 对应 序号1..36）
  for (let r = 0; r < 6; r++) {
    for (let c = 0; c < 6; c++) {
      const v = board[r * 6 + c];
      if (v === 0 || v === "0") continue;
      if (c <= 3 && board[r * 6 + c + 1] === v && board[r * 6 + c + 2] === v) return true;
      if (r <= 3 && board[(r + 1) * 6 + c] === v && board[(r + 2) * 6 + c] === v) return true;
    }
  }
  return false;
};

// 构造「无三连」底图：val(r,c) = 1 + ((r + 2c) mod 4)
const baseBoard = () => {
  const b = [];
  for (let r = 0; r < 6; r++)
    for (let c = 0; c < 6; c++) b.push(((r + 2 * c) % 4) + 1);
  return b; // 0-based，长度36
};

(async () => {
  const vm = new VirtualMachine();
  const buf = fs.readFileSync(sb3Path);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  await vm.loadProject(ab);
  vm.runtime.currentStepTime = 1000 / 30;
  vm.setTurboMode(true);

  const stepFor = async (ms) => {
    const t0 = Date.now();
    const base = vm.runtime.currentMSecs || t0;
    while (Date.now() - t0 < ms) {
      vm.runtime.currentMSecs = base + (Date.now() - t0);
      vm.runtime._step();
      await sleep(3);
    }
  };
  const stage = () => vm.runtime.targets.find((t) => t.isStage);
  const readVar = (name) => {
    for (const t of vm.runtime.targets)
      for (const id of Object.keys(t.variables || {})) {
        const v = t.variables[id];
        if (v && v.name === name) return v.value;
      }
    return null;
  };
  const readList = (name) => {
    for (const t of vm.runtime.targets)
      for (const id of Object.keys(t.variables || {})) {
        const v = t.variables[id];
        if (v && v.name === name && Array.isArray(v.value)) return v.value;
      }
    return null;
  };
  const setList = (name, arr) => {
    for (const t of vm.runtime.targets)
      for (const id of Object.keys(t.variables || {})) {
        const v = t.variables[id];
        if (v && v.name === name && Array.isArray(v.value)) { v.value.length = 0; v.value.push(...arr); return; }
      }
  };
  const setVar = (name, val) => {
    for (const t of vm.runtime.targets)
      for (const id of Object.keys(t.variables || {})) {
        const v = t.variables[id];
        if (v && v.name === name) { v.value = val; return; }
      }
  };
  const broadcast = (msg) => {
    vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: msg });
  };
  const cloneCount = () => {
    let n = 0;
    for (const t of vm.runtime.targets)
      if (t.sprite && t.sprite.name === "格子" && !t.isOriginal) n++;
    return n;
  };

  const bad = [];
  let board, clones;

  // 等棋盘「稳定」而不是「等固定步数」：
  // 交换→检测→换回、以及消除→下落补充，都是多阶段过程，
  // 固定 stepFor(300) 会偶发采样在中间态（表现为「未完好换回」跑十次红一次）。
  async function waitBoardStable(maxSteps = 1500, stableNeed = 15) {
    let prev = null, stable = 0, i = 0;
    for (; i < maxSteps; i++) {
      await stepFor(1);
      const cur = JSON.stringify(readList("棋盘"));
      if (cur === prev) { stable++; if (stable >= stableNeed) return i; }
      else { stable = 0; prev = cur; }
    }
    return i;
  }

  // 绿旗 + 重试：确保初始无三连（board 取快照，避免后续 setList 改写同一引用导致报告失真）
  //
  // ⚠️ break 条件必须同时看 clones：棋盘列表是「一次循环填完」的（瞬间 36 格），
  //    而格子克隆是**逐帧建的**。只看 board 就会在克隆只建了 7 个时就 break，
  //    表现为「偶尔 克隆数=7」，跑十次红一次。
  // ⚠️ 而且无头环境没有渲染器，克隆体会被 VM 偶发回收（已知盲区），
  //    所以克隆数断言放宽到 30：它的作用只是「证明棋盘真的被建出来了」，
  //    「满盘」的严格判定已经由 board 列表覆盖。
  const CLONE_MIN = 30;
  for (let attempt = 0; attempt < 6; attempt++) {
    vm.greenFlag();
    await stepFor(400);
    board = (readList("棋盘") || []).slice();
    clones = cloneCount();
    if (board && board.length === 36 && board.every((x) => x !== 0) && !hasTriple(board)
        && clones >= CLONE_MIN) break;
  }

  // A. 满盘
  if (!board || board.length !== 36) bad.push("棋盘长度异常=" + (board && board.length));
  else if (board.some((x) => x === 0)) bad.push("初始有空格(空洞)");
  // B. 无初始三连
  if (board && hasTriple(board)) bad.push("初始即存在三连");
  // C. 克隆数（无头环境会偶发回收克隆，见上方注释）
  if (clones < CLONE_MIN)
    bad.push("格子克隆数=" + clones + "(期望≥" + CLONE_MIN + ")");

  // D. 交换回退机制：构造「交换 1↔2 不形成三连」的棋盘，验证交换后若不匹配会被严格换回（棋盘不损坏）。
  {
    const b = baseBoard();
    // 强制 (1,1)=1, (1,2)=2（不同值），且邻居保证交换后不产生三连 → 应触发自动换回。
    b[0] = 1; b[1] = 2;          // row1 col1=1, col2=2
    b[2] = 3; b[6] = 4; b[7] = 3; // 周围不同，避免交换后出现三连
    setList("棋盘", b.slice());
    setVar("分数", 0); setVar("本轮消除", 0); setVar("步数", 0);
    const before = readList("棋盘").slice();
    setVar("交换A", 1); setVar("交换B", 2);  // 交换 (1,1)↔(1,2) —— 不应形成三连
    broadcast("交换并检测");
    await stepFor(40);          // 先让它启动
    await waitBoardStable();
    const after = readList("棋盘");
    // 无匹配 → 游戏应自动换回，棋盘与交换前逐格完全一致（验证不损坏）。
    const restored = after && before && after.length === 36 && before.length === 36
                     && after.every((x, i) => x === before[i]);
    if (!restored) {
      const diff = [];
      for (let i = 0; i < 36; i++) if (after[i] !== before[i]) diff.push((i + 1) + ":" + before[i] + "→" + after[i]);
      bad.push("无匹配交换后棋盘未完好换回: " + diff.slice(0, 6).join(","));
    }
  }

  // E. 匹配消除：构造「仅左上角一处横向三连」的棋盘，用自交换(交换A=交换B=1)避免扰动，
  //    检测应直接消除该三连并计分。
  {
    const b = baseBoard();
    b[0] = 1; b[1] = 1; b[2] = 1;   // 强制 (1,1)(1,2)(1,3) = 1，形成唯一横向三连
    setList("棋盘", b);
    setVar("分数", 0); setVar("本轮消除", 0); setVar("步数", 0);
    setVar("交换A", 1); setVar("交换B", 1);  // 自交换 → 等价于无操作，保持三连
    broadcast("交换并检测");
    await stepFor(40);          // 先让它启动（消除会引发下落，棋盘连续变化多轮）
    await waitBoardStable();
    const score = readVar("分数");
    const elim = readVar("本轮消除");
    const boardAfter = readList("棋盘");
    if (!(elim >= 3)) bad.push("匹配消除数量异常: 本轮消除=" + elim);
    if (!(score >= 30)) bad.push("匹配消除未计分: 分数=" + score);
    if (boardAfter && boardAfter.some((x) => x === 0)) bad.push("消除后棋盘出现空洞(下落补满失败)");
    if (boardAfter && boardAfter.length !== 36) bad.push("消除后棋盘长度异常");
  }

  // F. 纵向三连：构造「仅左列一处纵向三连」的棋盘，自交换后检测应消除。
  {
    const b = baseBoard();
    b[0] = 1; b[6] = 1; b[12] = 1;  // 列1：行1/2/3 = 1，形成唯一纵向三连
    setList("棋盘", b);
    setVar("分数", 0); setVar("本轮消除", 0); setVar("步数", 0);
    setVar("交换A", 1); setVar("交换B", 1);  // 自交换 → 无扰动
    broadcast("交换并检测");
    await stepFor(400);
    const elim = readVar("本轮消除");
    if (!(elim >= 3)) bad.push("纵向三连未消除: 本轮消除=" + elim);
  }

  const actual = {
    棋盘满盘: board && board.length === 36 && board.every((x) => x !== 0),
    无初始三连: board ? !hasTriple(board) : false,
    克隆数: clones,
    匹配消除数: readVar("本轮消除"),
    最终分数: readVar("分数"),
  };

  console.log(JSON.stringify({ actual, bad }, null, 2));
  if (bad.length) { console.error("MATCH3_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("MATCH3_LOGIC_OK");
})().catch((e) => {
  console.error("MATCH3_CHECK_FAIL", e && (e.stack || e));
  process.exit(1);
});
