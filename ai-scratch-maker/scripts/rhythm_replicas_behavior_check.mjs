// 五款代表作音游复刻引擎行为校验（第三十九册 §457–§478）
// 用法: node rhythm_replicas_behavior_check.mjs <rhythm_replicas.sb3>
//
// 纯判定函数，用已知答案硬校验。为测精确窗口边界，多数用例把「帧长ms」设为 1
// 关闭帧量化；帧量化本身单独测（第三十八册 §435）。
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
const Z = (n) => Array.from({ length: n }, () => 0);

vm.greenFlag();
await stepN(3);
setVar("自动帧", 0);
await stepN(2);

function resetBase(frameMs = 1) {
  broadcast("重置");
  setVar("自动帧", 0);
  setVar("帧长ms", frameMs);
  setVar("校准ms", 0);
  setVar("songTime", 0);
  setVar("音符数", 0);
  setVar("扫描指针", 1);
  setVar("线X", 0); setVar("线Y", 0); setVar("线角", 0);
  setVar("圈X", 0); setVar("圈Y", 0); setVar("圈半径", 100);
  setVar("全屏判定", 0); setVar("不透明度", 255);
  setVar("活跃雨丝", 0); setVar("屏上手指", 0);
  setVar("Ξ数", 0); setVar("闪电HP", 3);
  setVar("闪电Exact", 0); setVar("闪电Miss", 0);
  setVar("输入X", 0); setVar("输入Y", 0);
  setVar("输入格", 0); setVar("输入方向", 0);
  setVar("输入动作", 1); setVar("输入时刻", 0);
  setVar("连续列", 2); setVar("每行ms", 500);
  setVar("检查点", 0); setVar("完成度", 0); setVar("失败数", 0);
  setVar("半宽", 50); setVar("宽度单位", 1);
  setList("谱时刻", Z(40)); setList("谱类型", Z(40));
  setList("谱位置", Z(40)); setList("谱线号", Z(40));
  setList("谱时长", Z(40)); setList("谱方向", Z(40));
  setList("谱参数", Z(40)); setList("已判定", Z(40));
  setList("转角时刻", Z(20)); setList("已转", Z(20));
  setList("段检查点", Z(20));
  setList("行地板", Array.from({ length: 20 }, () => 1));
  setList("行障碍", Z(20)); setList("行跳板", Z(20));
  setList("行收集", Z(20)); setList("行障碍列", Z(20));
  setList("行地板列", Array.from({ length: 20 }, () => -1));
  setList("事件线", Z(12)); setList("事件型", Z(12));
  setList("事件起表", Z(12)); setList("事件止表", Z(12));
  setList("事件起值表", Z(12)); setList("事件终值表", Z(12));
  setVar("事件数", 0);
  setVar("分数", 0); setVar("裸分", 0);
  setVar("连击", 0); setVar("最大连击", 0);
  setVar("档1数", 0); setVar("档2数", 0); setVar("档3数", 0);
  setVar("档4数", 0); setVar("档5数", 0); setVar("档Miss数", 0);
}
const chart1 = (t, type = 1, pos = 0, dur = 0, dir = 0, param = 1) => {
  setList("谱时刻", [t]);
  setList("谱类型", [type]);
  setList("谱位置", [pos]);
  setList("谱时长", [dur]);
  setList("谱方向", [dir]);
  setList("谱参数", [param]);
  setList("谱线号", [1]);
  setList("已判定", [0]);
  setVar("音符数", 1);
};
const hitP = async (t, extra = {}) => {
  setVar("输入时刻", t);
  for (const [k, v] of Object.entries(extra)) setVar(k, v);
  broadcast("P判一击"); await stepN(160);
  return { 档: num(getVar("档位")), 词: getVar("档名词"), 误差: num(getVar("误差")) };
};
const hitS = async (t, extra = {}) => {
  setVar("输入时刻", t);
  for (const [k, v] of Object.entries(extra)) setVar(k, v);
  broadcast("S判一击"); await stepN(160);
  return { 档: num(getVar("档位")), 词: getVar("档名词"),
           连击: num(getVar("连击")), 生命: num(getVar("生命")) };
};
const hitM = async (t, extra = {}) => {
  setVar("输入时刻", t);
  for (const [k, v] of Object.entries(extra)) setVar(k, v);
  broadcast("M判一击"); await stepN(160);
  return { 档: num(getVar("档位")), 词: getVar("档名词"),
           Ξ: num(getVar("Ξ数")), 全屏: num(getVar("全屏判定")) };
};

// ---------------------------------------------------------------- 1. 模式表（§473）
{
  const rows = [];
  for (const m of [1, 2, 3, 4, 5]) {
    resetBase();
    setVar("模式", m);
    broadcast("设模式"); await stepN(120);
    rows.push({ 模式: m, 窗: [1, 2, 3, 4, 5].map((k) => num(getVar("窗" + k))),
                断连: num(getVar("断连阈值")), 体: num(getVar("体类型")),
                生命: num(getVar("生命")), 候选: num(getVar("候选窗口")) });
  }
  snap.模式表 = rows;
  if (rows[0].窗[0] !== 80 || rows[0].窗[1] !== 180 || rows[0].断连 !== 3)
    bad.push("Phigros 窗口/断连阈值错：" + JSON.stringify(rows[0]));
  if (rows[1].窗[0] !== 41.7 || rows[1].窗[3] !== 125 || rows[1].生命 !== 1000)
    bad.push("PJSK 五档窗口 / Life 错：" + JSON.stringify(rows[1]));
  if (rows[2].窗.join(",") !== "35,70,105,140,155" || rows[2].断连 !== 5)
    bad.push("Milthm 六档窗口 / 断连阈值错：" + JSON.stringify(rows[2]));
  if (rows[3].体 !== 4 || rows[4].体 !== 3)
    bad.push("亚音游判定体类型错（跳舞的线=4 / 滚动的天空=3）");
}

// ---------------------------------------------------------------- 2. Phigros（§459–§463）
{
  resetBase();
  setVar("模式", 1); broadcast("设模式"); await stepN(100);
  setVar("bpm", 100); setVar("timeT", 32);
  broadcast("官谱换算"); await stepN(80);
  snap.官谱换算 = { Tms: num(getVar("Tms")), 目标: num(getVar("目标时刻")) };
  if (num(getVar("Tms")) !== 18.75 || num(getVar("目标时刻")) !== 600)
    bad.push("官谱 T 单位应为 1875/bpm=18.75ms，timeT=32 → 600ms");

  // 判定线事件：线性插值，无缓动
  setList("事件型", [3, 4]); setList("事件起表", [0, 0]);
  setList("事件止表", [1000, 1000]);
  setList("事件起值表", [0, 0]); setList("事件终值表", [90, 255]);
  setVar("事件数", 2); setVar("songTime", 250);
  broadcast("判定线求值"); await stepN(120);
  snap.判定线求值 = { 角: num(getVar("线角")), 透明度: num(getVar("不透明度")),
                      插值: num(getVar("事件插值")) };
  if (Math.abs(num(getVar("线角")) - 22.5) > 0.01)
    bad.push("事件应线性插值：250/1000 × 90 = 22.5，实为 " + getVar("线角"));
  if (num(getVar("不透明度")) <= 0)
    bad.push("隐藏判定线时只关渲染，判定仍生效");

  // 切向投影：θ=90°，法向(输入X)很远也应命中；切向(输入Y)远离则不命中
  setVar("线角", 90); setVar("线X", 0); setVar("线Y", 0);
  setVar("半宽", 50);
  chart1(1000, 1, 200);
  let r = await hitP(1000, { 输入X: 1000, 输入Y: 200 });
  snap.切向命中 = { 档: r.档, 切向: num(getVar("切向坐标")) };
  if (r.档 !== 1) bad.push("Phigros 判定区法向无限延伸：输入X=1000 也应命中");
  resetBase(); setVar("模式", 1); broadcast("设模式"); await stepN(100);
  setVar("线角", 90); setVar("半宽", 50); chart1(1000, 1, 200);
  r = await hitP(1000, { 输入X: 0, 输入Y: 9999 });
  if (r.档 !== 0) bad.push("切向坐标远离音符时不应命中（不能写成点到线距离）");

  // 四档边界（帧长=1，纯判定）
  const cases = [
    { t: 1000, want: 1 }, { t: 1081, want: 2 }, { t: 1190, want: 3 },
    { t: 1250, want: 6 }, { t: 1400, want: 0 },
  ];
  const got = [];
  for (const c of cases) {
    resetBase(); setVar("模式", 1); broadcast("设模式"); await stepN(100);
    chart1(1000, 1, 0);
    const x = await hitP(c.t, { 输入X: 0, 输入Y: 0 });
    got.push({ 偏差: c.t - 1000, 档: x.档, 词: x.词 });
    if (x.档 !== c.want) bad.push("Phigros 偏差 " + (c.t - 1000) + "ms 应档 " + c.want + "，实为 " + x.档);
  }
  snap.Phigros四档 = got;
  // Drag / Flick 只有 P/Miss；Hold 无 Bad
  for (const [type, label] of [[2, "Drag"], [4, "Flick"]]) {
    resetBase(); setVar("模式", 1); broadcast("设模式"); await stepN(100);
    chart1(1000, type, 0);
    const x = await hitP(1190, { 输入X: 0, 输入Y: 0 });
    if (x.档 !== 6) bad.push(label + " 只能出 Perfect/Miss，实为档 " + x.档);
  }
  resetBase(); setVar("模式", 1); broadcast("设模式"); await stepN(100);
  chart1(1000, 3, 0);
  const hold = await hitP(1190, { 输入X: 0, 输入Y: 0 });
  if (hold.档 !== 6) bad.push("Hold 没有 Bad 判定（应降为 Miss），实为 " + hold.档);
  snap.Phigros类型 = { DragFlick: "仅P/Miss", Hold无Bad: hold.档 };

  // 单次点击只判一个
  resetBase(); setVar("模式", 1); broadcast("设模式"); await stepN(100);
  setList("谱时刻", [1000, 1000]); setList("谱类型", [1, 1]);
  setList("谱位置", [0, 0]); setList("已判定", [0, 0]);
  setList("谱参数", [1, 1]); setVar("音符数", 2);
  await hitP(1000, { 输入X: 0, 输入Y: 0 });
  const judged = (getList("已判定") || []).map(Number);
  if (judged.filter((x) => x !== 0).length !== 1)
    bad.push("单次点击只能判定一个 Tap/Hold 音符");
}

// ---------------------------------------------------------------- 3. PJSK（§464–§465）
{
  const cases = [
    { t: 1000, want: 1 }, { t: 1050, want: 2 }, { t: 1100, want: 3 },
    { t: 1115, want: 4 }, { t: 1150, want: 6 },
  ];
  const got = [];
  for (const c of cases) {
    resetBase(); setVar("模式", 2); broadcast("设模式"); await stepN(100);
    chart1(1000, 1, 0, 0, 0, 2);
    const x = await hitS(c.t, { 输入格: 0 });
    got.push({ 偏差: c.t - 1000, 档: x.档, 词: x.词, 生命: x.生命 });
    if (x.档 !== c.want) bad.push("PJSK 偏差 " + (c.t - 1000) + "ms 应档 " + c.want + "，实为 " + x.档);
  }
  snap.PJSK五档 = got;
  if (num(got[3].生命) !== 950) bad.push("BAD 应扣 50 Life，实为 " + got[3].生命);
  if (num(got[4].生命) !== 920) bad.push("MISS 应扣 80 Life，实为 " + got[4].生命);

  // GOOD 断连击
  resetBase(); setVar("模式", 2); broadcast("设模式"); await stepN(100);
  chart1(1000, 1, 0, 0, 0, 2);
  await hitS(1000, { 输入格: 0 });
  const c1 = num(getVar("连击"));
  chart1(1000, 1, 0, 0, 0, 2);   // ★ 目标仍是 1000，只是重新置未判定
  await hitS(1100, { 输入格: 0 }); // 晚按 100ms → GOOD
  snap.PJSK_GOOD断连 = { 打P后: c1, 打GOOD后: num(getVar("连击")) };
  if (c1 !== 1 || num(getVar("连击")) !== 0)
    bad.push("PJSK 的 GOOD 必须断连击");

  // 12 格区间匹配
  resetBase(); setVar("模式", 2); broadcast("设模式"); await stepN(100);
  chart1(1000, 1, 4, 0, 0, 3);        // 起始格 4、宽 3（4/5/6）
  let r = await hitS(1000, { 输入格: 6 });
  if (r.档 !== 1) bad.push("宽音符应做格区间匹配（格6 属于 4..6）");
  resetBase(); setVar("模式", 2); broadcast("设模式"); await stepN(100);
  chart1(1000, 1, 4, 0, 0, 3);
  r = await hitS(1000, { 输入格: 7 });
  if (r.档 !== 0) bad.push("格 7 不在宽音符区间内，应空击");

  // Flick 方向 / Trace 只 P/Miss
  resetBase(); setVar("模式", 2); broadcast("设模式"); await stepN(100);
  chart1(1000, 3, 0, 0, 1, 2);       // Flick 要求方向 1
  r = await hitS(1000, { 输入格: 0, 输入方向: 2 });
  if (r.档 !== 6) bad.push("Flick 方向不符应判 MISS，实为 " + r.档);
  resetBase(); setVar("模式", 2); broadcast("设模式"); await stepN(100);
  chart1(1000, 4, 0, 0, 0, 2);       // Trace
  r = await hitS(1100, { 输入格: 0 });
  if (r.档 !== 1) bad.push("Trace 只出 PERFECT/MISS，任何接触即通过");

  // Hold 头尾两次判定
  resetBase(); setVar("模式", 2); broadcast("设模式"); await stepN(100);
  chart1(1000, 2, 0, 500, 0, 2);
  await hitS(1000, { 输入格: 0 });
  const head = (getList("已判定") || []).map(Number)[0];
  setVar("输入时刻", 1500);
  broadcast("S尾判"); await stepN(160);
  snap.PJSK_Hold = { 头状态: head, 尾档: num(getVar("档位")) };
  if (head !== 5 || num(getVar("档位")) !== 1)
    bad.push("Hold 必须有独立的头判与尾判");
}

// ---------------------------------------------------------------- 4. Milthm（§466–§468）
{
  const cases = [
    { t: 1000, want: 1 }, { t: 1050, want: 2 }, { t: 1090, want: 3 },
    { t: 1120, want: 4 }, { t: 1148, want: 5 }, { t: 1180, want: 6 },
  ];
  const got = [];
  for (const c of cases) {
    resetBase(); setVar("模式", 3); broadcast("设模式"); await stepN(100);
    chart1(1000, 1, 0);
    const x = await hitM(c.t, { 输入X: 0, 输入Y: 0 });
    got.push({ 偏差: c.t - 1000, 档: x.档, 词: x.词 });
    if (x.档 !== c.want) bad.push("Milthm 偏差 " + (c.t - 1000) + "ms 应档 " + c.want + "，实为 " + x.档);
  }
  snap.Milthm六档 = got;

  // 圆命中 / 圈外
  resetBase(); setVar("模式", 3); broadcast("设模式"); await stepN(100);
  chart1(1000, 1, 0);
  let r = await hitM(1000, { 输入X: 200, 输入Y: 0 });
  if (r.档 !== 0) bad.push("判定圈外应空击");
  // 全屏判定（水面反射）时圈外也命中
  resetBase(); setVar("模式", 3); broadcast("设模式"); await stepN(100);
  setVar("全屏判定", 1); chart1(1000, 1, 0);
  r = await hitM(1000, { 输入X: 200, 输入Y: 0 });
  if (r.档 !== 1) bad.push("水面反射后判定范围扩展到全屏，圈外也应命中");

  // 雨丝：命中后开启全屏、活跃+1、Ξ+1
  resetBase(); setVar("模式", 3); broadcast("设模式"); await stepN(100);
  chart1(1000, 2, 0);   // 2 = 雨丝
  r = await hitM(1000, { 输入X: 0, 输入Y: 0 });
  snap.雨丝 = { 档: r.档, 全屏: num(getVar("全屏判定")),
                活跃: num(getVar("活跃雨丝")), 手指: num(getVar("屏上手指")), Ξ: num(getVar("Ξ数")) };
  if (num(getVar("全屏判定")) !== 1 || num(getVar("活跃雨丝")) !== 1 || num(getVar("Ξ数")) !== 1)
    bad.push("雨丝命中应触发水面反射并进入普通序列 Ξ");

  // 水面反射：有雨丝无手指 → Miss；无雨丝 → 不惩罚
  setVar("屏上手指", 0);
  broadcast("水面反射"); await stepN(120);
  if (num(getVar("档Miss数")) === 0 || num(getVar("连击")) !== 0)
    bad.push("有雨丝接触判定圈却没有手指 → 应判 Miss 并断连击");
  setVar("活跃雨丝", 0); setVar("屏上手指", 1);
  broadcast("水面反射"); await stepN(120);
  if (num(getVar("全屏判定")) !== 1) { /* 无活跃雨丝时应清全屏 */ }
  snap.水面反射 = { 全屏: num(getVar("全屏判定")), 结果: getVar("结果") };
  if (num(getVar("全屏判定")) !== 0)
    bad.push("无活跃雨丝应关闭全屏判定，继续按住不产生判定也不惩罚");

  // 闪电最后判 + 独立序列 Φ
  resetBase(); setVar("模式", 3); broadcast("设模式"); await stepN(100);
  chart1(1000, 4, 0);   // 4 = 闪电
  r = await hitM(1000, { 输入X: 0, 输入Y: 0 });
  snap.闪电待后判 = { 词: r.词, Ξ: num(getVar("Ξ数")) };
  if (num(getVar("Ξ数")) !== 0) bad.push("闪电不得进入普通判定序列 Ξ");
  setVar("目标时刻", 1000); setVar("输入时刻", 1000);
  broadcast("M闪电"); await stepN(120);
  if (num(getVar("闪电Exact")) !== 1 || num(getVar("Ξ数")) !== 0)
    bad.push("Lightning Exact 应只累加 Φ，不进 Ξ");
  setVar("输入时刻", 1200);
  broadcast("M闪电"); await stepN(120);
  snap.闪电 = { Exact: num(getVar("闪电Exact")), Miss: num(getVar("闪电Miss")),
                HP: num(getVar("闪电HP")), Ξ: num(getVar("Ξ数")) };
  if (num(getVar("闪电Miss")) !== 1 || num(getVar("闪电HP")) !== 2 || num(getVar("Ξ数")) !== 0)
    bad.push("闪电 Miss 消耗闪电 HP、独立统计，不计普通物量");
}

// ---------------------------------------------------------------- 5. 跳舞的线（§469）
{
  resetBase(); setVar("模式", 4); broadcast("设模式"); await stepN(100);
  setList("转角时刻", [1000, 1500, 2000]);
  setList("已转", [0, 0, 0]);
  setList("段检查点", [0, 1, 0]);
  setVar("转向窗口", 100);
  setVar("输入时刻", 1000);
  broadcast("D一步"); await stepN(120);
  snap.跳舞的线_成功 = { 档: num(getVar("档位")), 指针: num(getVar("扫描指针")),
                          完成度: num(getVar("完成度")) };
  if (num(getVar("档位")) !== 1 || num(getVar("扫描指针")) !== 2 || num(getVar("完成度")) !== 1)
    bad.push("转角窗口内点击应转向成功且只消费一个转角");
  setVar("输入时刻", 1600);   // 第 2 个转角 +100（边界）
  broadcast("D一步"); await stepN(120);
  if (num(getVar("扫描指针")) !== 3 || num(getVar("检查点")) !== 2)
    bad.push("连点窗口重叠时按扫描指针逐个消费；检查点应更新");
  setVar("输入时刻", 2500);   // 第 3 个转角 +500 → 失败
  broadcast("D一步"); await stepN(120);
  snap.跳舞的线_失败 = { 档: num(getVar("档位")), 指针: num(getVar("扫描指针")),
                          失败数: num(getVar("失败数")) };
  if (num(getVar("档位")) !== 6 || num(getVar("扫描指针")) !== 3)
    bad.push("失败应回到最近检查点（段2 → 指针3），不是回开头");
}

// ---------------------------------------------------------------- 6. 滚动的天空（§470）
{
  resetBase(); setVar("模式", 5); broadcast("设模式"); await stepN(100);
  setVar("每行ms", 500); setVar("连续列", 2.4);   // 拖动连续量 → 取整 2
  // 行1 全地板无障碍；行2 有障碍在列2；行3 障碍但无地板支撑；行4 列2 无地板；行5 跳板；行6 收集
  setList("行地板", [1, 1, 0, 0, 1, 1]);
  setList("行障碍", [0, 1, 1, 0, 0, 0]);
  setList("行障碍列", [0, 2, 2, 0, 0, 0]);
  setList("行地板列", [-1, -1, -1, 2, -1, -1]);
  setList("行跳板", [0, 0, 0, 0, 1, 0]);
  setList("行收集", [0, 0, 0, 0, 0, 1]);
  const rows = [];
  for (const row of [1, 2, 3, 4, 5, 6]) {
    setVar("songTime", (row - 1) * 500);
    broadcast("R一步"); await stepN(140);
    rows.push({ 行: row, 列: num(getVar("当前列")), 档: num(getVar("档位")),
                完成度: num(getVar("完成度")) });
  }
  snap.滚动的天空 = rows;
  if (rows[0].列 !== 2 || rows[0].档 !== 1)
    bad.push("连续列 2.4 应取整为 2；无障碍行应通过");
  if (rows[1].档 !== 6) bad.push("列 2 撞障碍应失败");
  if (rows[2].档 !== 1) bad.push("★ 障碍无地板支撑时无伤害判定，应通过");
  if (rows[3].档 !== 6) bad.push("列 2 无地板应坠落失败");
  if (num(getVar("跳高")) !== 3 || num(getVar("跳远")) !== 4)
    bad.push("普通跳板应 3 格高 / 4 格远");
  if (num(getVar("行收集数")) !== 1) bad.push("收集品应计数");
}

// ---------------------------------------------------------------- 结果
const pass = bad.length === 0;
console.log(JSON.stringify(snap, null, 2));
if (pass) {
  console.log("REPLICAS_LOGIC_OK  五款代表作复刻判定全部正确（Phigros/PJSK/Milthm/跳舞的线/滚动的天空）");
  process.exit(0);
} else {
  console.log("REPLICAS_LOGIC_FAIL");
  for (const b of bad) console.log("  ✗ " + b);
  process.exit(1);
}
