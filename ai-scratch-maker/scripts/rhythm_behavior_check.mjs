// 音游判定行为校验（第三十八册 §433–§456）：BPM / 谱面 / 四档判定 / 校准 /
// 帧量化 / 去重 / 漏击扫描 / 长按 / 结算。
// 用法: node rhythm_behavior_check.mjs <rhythm_game.sb3>
//
// 判定是纯函数，最适合拿已知答案硬校验。窗口按帧长整数倍配：
//   帧长 33ms → P≤33 / G≤66 / Good≤99 / 候选剪枝与漏击阈值 132
// 谱面时刻全部取 33 的倍数，这样量化不会引入额外误差，边界可以写死。
import fs from "node:fs";
import { findScratchVM, loadScratchVM } from "./scratch_vm_path.mjs";

const VM = loadScratchVM(findScratchVM());
const vm = new VM();
const buf = fs.readFileSync(process.argv[2]);
await vm.loadProject(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
vm.runtime.currentStepTime = 1000 / 30;

const num = (x) => (typeof x === "string" ? parseFloat(x) : x);
function allNames() {
  const out = {};
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v) out[v.name] = v;
    }
  }
  return out;
}
const getVar = (n) => { const v = allNames()[n]; return v ? v.value : undefined; };
const setVar = (n, x) => { const v = allNames()[n]; if (v) { v.value = x; return true; } return false; };
const getList = (n) => { const v = allNames()[n]; return v ? v.value : undefined; };
const setList = (n, a) => { const v = allNames()[n]; if (v) { v.value = a.slice(); return true; } return false; };
const stepN = async (n) => {
  for (let i = 0; i < n; i++) {
    vm.runtime.currentMSecs += 33;
    vm.runtime._step();
    await Promise.resolve();
  }
};
const broadcast = (m) => vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: m });

const bad = [];
const snap = {};

// ---------------------------------------------------------------- 0. 启动
vm.greenFlag();
await stepN(3);
setVar("自动帧", 0);
await stepN(2);

const NOTES = [990, 990, 1320, 1650, 2640];   // 全部 33 的倍数
const LANES = [1, 2, 1, 3, 1];
function resetJudge() {
  setList("音符时刻", NOTES.slice());
  setList("音符轨道", LANES.slice());
  setList("音符类型", [1, 1, 1, 1, 1]);
  setList("音符时长", [0, 0, 0, 0, 0]);
  setList("已判定", [0, 0, 0, 0, 0]);
  setList("误差表", [0, 0, 0, 0, 0]);
  setList("判定档表", [0, 0, 0, 0, 0]);
  setVar("音符数", 5);
  setVar("扫描指针", 1);
  setVar("帧长ms", 33);
  setVar("窗口P", 33); setVar("窗口G", 66);
  setVar("窗口Good", 99); setVar("窗口Miss", 132);
  setVar("校准ms", 0);
  setVar("songTime", 0);
  setVar("分数", 0); setVar("裸分", 0);
  setVar("连击", 0); setVar("最大连击", 0); setVar("加成连击", 0);
  setVar("档P数", 0); setVar("档G数", 0);
  setVar("档Good数", 0); setVar("档Miss数", 0);
  setVar("最大连击", 0);
  setVar("准确率", 0); setVar("评级", "");
  setVar("自动帧", 0);
}
const hit = async (t, lane, calib) => {
  if (calib !== undefined) setVar("校准ms", calib);
  setVar("输入时刻", t);
  setVar("当前轨道", lane);
  broadcast("判一击");
  await stepN(150);
  return {
    档: num(getVar("判定档")), 词: getVar("判定词"),
    误差: num(getVar("误差")), 连击: num(getVar("连击")),
    分数: num(getVar("分数")), 裸分: num(getVar("裸分")),
  };
};

// ---------------------------------------------------------------- 1. BPM 数学（§437）
{
  const rows = [];
  for (const bpm of [120, 150, 180]) {
    setVar("BPM", bpm);
    broadcast("算BPM"); await stepN(60);
    rows.push({ BPM: bpm, 拍长: num(getVar("拍长ms")),
               十六分: num(getVar("十六分ms")), 三连音: num(getVar("三连音ms")) });
  }
  snap.BPM = { 表: rows, 窗口: [num(getVar("窗口P")), num(getVar("窗口G")),
                              num(getVar("窗口Good")), num(getVar("窗口Miss"))] };
  const want = [[500, 125, 167], [400, 100, 133], [333, 83, 111]];
  rows.forEach((r, k) => {
    if (r.拍长 !== want[k][0] || r.十六分 !== want[k][1] || r.三连音 !== want[k][2])
      bad.push("BPM " + r.BPM + " 数学错：" + JSON.stringify(r));
  });
  // 窗口必须全是帧长整数倍
  for (const w of snap.BPM.窗口)
    if (w % 33 !== 0) bad.push("判定窗口 " + w + "ms 不是帧长(33ms)的整数倍（§435）");
}

// ---------------------------------------------------------------- 2. 谱面生成（§438）
{
  setVar("BPM", 120);
  broadcast("算BPM"); await stepN(60);
  setVar("小节数", 2);
  setVar("谱面偏移ms", 500);
  broadcast("生成谱面"); await stepN(400);
  const times = (getList("音符时刻") || []).map(Number);
  const lanes = (getList("音符轨道") || []).map(Number);
  const done = (getList("已判定") || []).map(Number);
  snap.谱面 = { 音符数: num(getVar("音符数")), 前四个时刻: times.slice(0, 4),
                轨道: lanes.slice(0, 4) };
  if (num(getVar("音符数")) !== 16 || times.length !== 16)
    bad.push("2 小节 × 8 个非空格应生成 16 个音符，实为 " + num(getVar("音符数")));
  if (times[0] !== 500 || times[1] !== 750)
    bad.push("谱面偏移与 16 分网格错：前两音符应 500/750，实为 " + times.slice(0, 2));
  for (let k = 1; k < times.length; k++)
    if (times[k] < times[k - 1]) bad.push("谱面必须按时刻升序，第 " + k + " 项倒序");
  if (lanes.some((x) => x < 1 || x > 4)) bad.push("轨道号越界");
  if (done.some((x) => x !== 0)) bad.push("新生成谱面的「已判定」应全为 0");
}

// ---------------------------------------------------------------- 3. 四档判定边界（§441）
{
  const cases = [
    { t: 990, want: 1, label: "0帧" },
    { t: 1023, want: 1, label: "晚1帧(=33ms)" },
    { t: 1056, want: 2, label: "晚2帧(=66ms)" },
    { t: 1089, want: 3, label: "晚3帧(=99ms)" },
    { t: 1122, want: 4, label: "晚4帧(=132ms)" },
    { t: 924, want: 2, label: "早2帧(-66ms)" },
  ];
  const got = [];
  for (const c of cases) {
    resetJudge();
    const r = await hit(c.t, 1);
    got.push({ 情形: c.label, 档: r.档, 误差: r.误差 });
    if (r.档 !== c.want)
      bad.push(c.label + " 应判档 " + c.want + "，实为 " + r.档 + " (误差 " + r.误差 + ")");
  }
  snap.四档边界 = got;
  // abs 对称：早 66 与晚 66 同档
  if (got[2].档 !== got[5].档) bad.push("判定必须用 abs：早按与晚按应同档");

  // 超出候选剪枝窗口 → 空击，不判 Miss
  resetJudge();
  const far = await hit(1155, 1);      // 误差 165 > 窗口Miss 132
  snap.剪枝 = { 档: far.档, 词: far.词, Miss数: num(getVar("档Miss数")) };
  if (far.档 !== 0 || num(getVar("档Miss数")) !== 0)
    bad.push("超出候选窗口应为空击、不计 Miss，实为 档=" + far.档);
}

// ---------------------------------------------------------------- 4. 找最近 / 去重 / 空击 / 轨道隔离（§442）
{
  resetJudge();
  let r = await hit(1320, 1);
  snap.找最近 = { 档: r.档, 误差: r.误差, 已判定: (getList("已判定") || []).map(Number) };
  if (r.档 !== 1 || r.误差 !== 0 || num((getList("已判定") || [])[2]) !== 1)
    bad.push("应命中同轨最近的 1320 音符，而不是更早的 990");

  resetJudge();
  r = await hit(990, 1);
  const score1 = num(getVar("分数"));
  const r2 = await hit(990, 1);
  snap.去重 = { 首次档: r.档, 二次档: r2.档, 分数: num(getVar("分数")) };
  if (r2.档 !== 0 || num(getVar("分数")) !== score1)
    bad.push("已判定音符不得二次计分（按下沿 + 已判定表双层去重）");

  resetJudge();
  const empty = await hit(990, 4);   // 轨道 4 没有音符
  snap.空击 = { 档: empty.档, 连击: empty.连击, Miss数: num(getVar("档Miss数")) };
  if (empty.档 !== 0 || empty.连击 !== 0 || num(getVar("档Miss数")) !== 0)
    bad.push("空击不能判 Miss、不能断连击");

  resetJudge();
  await hit(990, 2);
  const judged = (getList("已判定") || []).map(Number);
  snap.轨道隔离 = judged;
  if (num(judged[1]) !== 1 || num(judged[0]) !== 0)
    bad.push("按 2 轨只能命中 2 轨的音符（同刻 1 轨不受影响）");
}

// ---------------------------------------------------------------- 5. 校准与帧量化（§435/§446）
{
  resetJudge();
  const cal = await hit(1056, 1, 66);   // 晚 66ms，校准 +66 → 修正为 0
  snap.校准 = { 档: cal.档, 误差: cal.误差, 目标时刻: num((getList("音符时刻") || [])[0]) };
  if (cal.档 !== 1 || cal.误差 !== 0)
    bad.push("校准 +66ms 应把「晚 66ms」修正成 Perfect，实为 " + JSON.stringify(cal));
  if (num((getList("音符时刻") || [])[0]) !== 990)
    bad.push("★ 校准只减在输入侧，绝不能改动目标时刻表");

  const quant = [];
  for (const t of [995, 1005]) {
    resetJudge();
    const r = await hit(t, 1);
    quant.push({ 原始: t, 档: r.档, 误差: r.误差 });
    if (r.档 !== 1) bad.push("原始时刻 " + t + " 应量化到同一帧并判 P");
  }
  snap.帧量化 = quant;
  if (quant[0].误差 !== quant[1].误差)
    bad.push("同一帧内的不同原始时刻必须量化成同一个误差（§435）");
}

// ---------------------------------------------------------------- 6. 漏击扫描（§443）
{
  resetJudge();
  setVar("songTime", 1123);           // > 990 + 132 = 1122
  broadcast("推进"); await stepN(180);
  const judged = (getList("已判定") || []).map(Number);
  snap.漏击 = { 判定: judged, Miss数: num(getVar("档Miss数")),
                连击: num(getVar("连击")), 指针: num(getVar("扫描指针")) };
  if (num(judged[0]) !== 4 || num(judged[1]) !== 4 || num(judged[2]) !== 0)
    bad.push("漏击扫描应把两个 990 音符判 Miss，1320 不动");
  if (num(getVar("档Miss数")) !== 2 || num(getVar("连击")) !== 0)
    bad.push("漏击应累计 2 次 Miss 并把连击清零");
  if (num(getVar("扫描指针")) !== 3)
    bad.push("扫描指针只前进，应停在 3，实为 " + getVar("扫描指针"));
}

// ---------------------------------------------------------------- 7. 长按头尾两次判定（§444）
{
  resetJudge();
  setList("音符类型", [2, 1, 1, 1, 1]);
  setList("音符时长", [660, 0, 0, 0, 0]);
  const head = await hit(990, 1);
  const afterHead = num(getVar("裸分"));
  setVar("长按索引", 1);
  setVar("抬手时刻", 1650);           // 990 + 660 = 尾时刻
  broadcast("长按抬手"); await stepN(150);
  snap.长按成功 = { 头档: head.档, 头后裸分: afterHead, 结果: getVar("长按结果"),
                    裸分: num(getVar("裸分")), 判定: num((getList("已判定") || [])[0]) };
  if (head.档 !== 5 || afterHead !== 0)
    bad.push("长按头只接住、不结算分数（点一下就满分是最常见的 bug）");
  if (!String(getVar("长按结果")).includes("成功") || num(getVar("裸分")) !== 300)
    bad.push("准时抬手应长按成功并结算 300 裸分");

  resetJudge();
  setList("音符类型", [2, 1, 1, 1, 1]);
  setList("音符时长", [660, 0, 0, 0, 0]);
  await hit(990, 1);
  setVar("长按索引", 1);
  setVar("抬手时刻", 990);            // 太早松手
  broadcast("长按抬手"); await stepN(150);
  snap.长按失败 = { 结果: getVar("长按结果"), Miss数: num(getVar("档Miss数")) };
  if (!String(getVar("长按结果")).includes("失败") || num(getVar("档Miss数")) !== 1)
    bad.push("过早松手应判长按失败");
}

// ---------------------------------------------------------------- 8. 分数 / 准确率 / 评级（§447）
{
  resetJudge();
  const first = await hit(990, 1);
  snap.连击加成 = { 分数: first.分数, 裸分: first.裸分, 连击: first.连击 };
  if (first.裸分 !== 300) bad.push("裸分应为 300（不含连击加成）");
  if (first.分数 <= first.裸分) bad.push("分数应含连击加成，大于裸分");
  if (first.连击 !== 1) bad.push("Perfect 应续连击");

  const check = async (raw, miss, label, wantAcc, wantRank) => {
    resetJudge();
    setVar("裸分", raw);
    setVar("档Miss数", miss);
    broadcast("结算"); await stepN(120);
    const acc = num(getVar("准确率")), rank = getVar("评级");
    snap[label] = { 准确率: acc, 评级: rank };
    if (acc !== wantAcc || rank !== wantRank)
      bad.push(label + " 应 " + wantAcc + "%/" + wantRank + "，实为 " + acc + "%/" + rank);
  };
  await check(1500, 0, "全Perfect", 100, "S");
  await check(500, 0, "全Good", 33, "D");
  await check(1350, 0, "九成", 90, "A");
  await check(0, 0, "空谱面", 0, "D");
}

// ---------------------------------------------------------------- 结果
const pass = bad.length === 0;
console.log(JSON.stringify(snap, null, 2));
if (pass) {
  console.log("RHYTHM_LOGIC_OK  音游判定全部正确（BPM/谱面/四档/校准/量化/去重/漏击/长按/结算）");
  process.exit(0);
} else {
  console.log("RHYTHM_LOGIC_FAIL");
  for (const b of bad) console.log("  ✗ " + b);
  process.exit(1);
}
