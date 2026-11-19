// MOBA 与策略游戏复刻引擎行为校验（第四十一册 §503–§526）
// 用法: node strategy_replicas_behavior_check.mjs <strategy_replicas.sb3>
//
// 覆盖四个模式（王者 / LOL / 三国杀 / 金铲铲）的纯判定逻辑：
//   模式1 王者荣耀 —— 兵线推进 / 塔索敌 / 塔攻击 / 补刀 / 破塔顺序
//   模式2 LOL       —— 塔目标优先级表 / 镀层 / 漏刀系数
//   模式3 三国杀   —— 回合阶段 / 摸牌 / 判定 / 距离 / 求桃 / 胜负
//   模式4 金铲铲   —— 收入 / 刷新 / 升星 / 羁绊 / 战斗 / 选秀
// 全部是「输入 → 输出」纯判定，用已知答案硬校验。
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
const setList = (n, a) => { const v = allNames()[n]; if (v) { v.value = a.map(String); return true; } return false; };
/** Scratch 列表是 1-based；这里按 1-based 下标写入，VM 内部是 0-based 数组。 */
const setItem = (n, idx1, val) => {
  const v = allNames()[n];
  if (!v) return false;
  v.value[idx1 - 1] = String(val);
  return true;
};
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
const near = (a, b, eps = 1e-6) => Math.abs(num(a) - num(b)) <= eps;
const G = (n) => getVar(n);
const S = (n, v) => setVar(n, v);
const has = (n, kw) => String(G(n)).includes(kw);

vm.greenFlag();
await stepN(5);
S("自动帧", 0);
await stepN(2);

// ---------------------------------------------------------------- 状态复位
// 引擎自带的「重置」广播只覆盖一部分变量，这里做**全量硬复位**，
// 保证每个用例都从已知初值出发（否则「摸牌数被就地夹紧」这类副作用会串味）。
const VAR_INIT = {
  模式: 1, 游戏秒: 0, 波次: 0, 兵线进度: 0, 兵线速度: 0.01, 遇敌: 0,
  波间隔: 30, 塔血量: 1000, 塔等级: 1, 塔减伤: 1, 塔锁定英雄: 0, 无兵线: 0,
  塔攻击次数: 0, 塔伤害: 0, 目标类型: 0, 候选数: 0, 最优优先级: 99, 最优单位: 0,
  最优距离: 99999, 当前优先级: 0, 当前距离: 0, 候选伤害标记: 0, 补刀: 0, 金币: 0,
  漏刀系数: 0.8, 全额金币: 21, 镀层: 0, 一血塔已发: 0, 主基地血: 100, 建筑序号: 1,
  破塔顺序: 0, 超级兵: 0, 结束: 0, 路: 1,
  回合角色: 1, 当前阶段: 0, 人数: 8, 体力: 4, 体力上限: 4, 手牌数: 0, 牌堆数: 10,
  弃牌堆数: 0, 摸牌数: 2, 判定区数: 0, 判定牌: 0, 判定花色: 0, 判定点数: 0,
  改判可用: 0, 改判次数: 0, 判定结果: 0, 基础距离: 0, 实际距离: 0, 攻击范围: 1,
  减一马: 0, 加一马: 0, 座位A: 1, 座位B: 2, 濒死者: 0, 自救: 0, 求桃数: 0, 桃数: 0,
  主公死: 0, 内奸存活: 0, 反贼存活: 0, 唯一存活内奸: 0, 胜负: "继续",
  金币铲: 0, 人口: 1, 经验铲: 0, 利息: 0, 连胜: 0, 连败: 0, 回合收入: 0,
  基础收入: 5, 连胜奖励: 0, 本回合胜: 0, 生命: 100, 阶段: 0, 回合: 1, 刷新费: 2,
  抽签值: 0, 概率门槛: 0, 卡池剩余: 0, 棋子费: 0, 棋子ID: 0, 同名数: 0, 星级: 1,
  棋子ID表长度: 12, 羁绊计数: 0, 羁绊阈值: 2, 羁绊激活: 0, 战力: 0, 敌战力: 0,
  存活棋子: 0, 扣血: 0, 阶段基础伤害: 2, 淘汰: 0, 选秀顺序: 0, 最低血者: 1,
  种子: 1, i: 0, j: 0, 临时: 0, 临时2: 0, 结果: "",
};
const LIST_INIT = {
  候选类型: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  候选距离: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  候选伤害英雄: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  牌堆: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  弃牌堆: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  判定区: [0, 0, 0, 0, 0, 0],
  求桃队列: [0, 0, 0, 0, 0, 0, 0, 0],
  等级概率表: [80, 20, 0, 0, 0],
  卡池: [10, 10, 8, 8, 6, 6, 4, 4, 2, 2],
  棋子ID表: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  棋子星级: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  羁绊阈值表: [2, 4, 6, 2, 4, 6, 2, 4, 6, 2, 4, 6],
  生命表: [100, 90, 80, 70, 60, 50, 40, 30],
};
function hardReset() {
  for (const [k, v] of Object.entries(VAR_INIT)) S(k, v);
  for (const [k, v] of Object.entries(LIST_INIT)) setList(k, v);
}
/** 复位 + 装载模式（走真实的「设模式」广播，不抄参数） */
async function mode(m) {
  hardReset();
  S("模式", m);
  broadcast("设模式");
  await stepN(40);
}

// ---------------------------------------------------------------- 1. 模式装载（§503）
{
  const rows = [];
  for (const m of [1, 2, 3, 4]) {
    await mode(m);
    rows.push({
      模式: m,
      漏刀系数: num(G("漏刀系数")), 波间隔: num(G("波间隔")),
      塔减伤: num(G("塔减伤")), 镀层: num(G("镀层")), 一血塔已发: num(G("一血塔已发")),
      当前阶段: num(G("当前阶段")), 回合角色: num(G("回合角色")),
      牌堆数: num(G("牌堆数")), 弃牌堆数: num(G("弃牌堆数")),
      判定区数: num(G("判定区数")), 胜负: String(G("胜负")),
      金币铲: num(G("金币铲")), 人口: num(G("人口")), 生命: num(G("生命")),
      连胜: num(G("连胜")), 连败: num(G("连败")), 淘汰: num(G("淘汰")),
      结果: String(G("结果")),
    });
  }
  snap.模式装载 = rows.map((r) => ({
    模式: r.模式, 漏刀系数: r.漏刀系数, 塔减伤: r.塔减伤, 镀层: r.镀层,
    人口: r.人口, 生命: r.生命, 结果: r.结果,
  }));
  if (!(rows[0].漏刀系数 === 0.8 && rows[0].塔减伤 === 0.6 && rows[0].镀层 === 0))
    bad.push("王者装载参数错：漏刀系数/塔减伤/镀层 = " +
      rows[0].漏刀系数 + "/" + rows[0].塔减伤 + "/" + rows[0].镀层);
  if (!(rows[1].漏刀系数 === 0.4 && rows[1].塔减伤 === 1 && rows[1].镀层 === 5 &&
        rows[1].一血塔已发 === 0))
    bad.push("LOL 装载参数错：漏刀系数/塔减伤/镀层 = " +
      rows[1].漏刀系数 + "/" + rows[1].塔减伤 + "/" + rows[1].镀层);
  if (!(rows[2].当前阶段 === 0 && rows[2].回合角色 === 1 && rows[2].牌堆数 === 10 &&
        rows[2].弃牌堆数 === 0 && rows[2].判定区数 === 0 && rows[2].胜负 === "继续"))
    bad.push("三国杀装载初值错：" + JSON.stringify(rows[2]));
  if (!(rows[3].金币铲 === 0 && rows[3].人口 === 1 && rows[3].生命 === 100 &&
        rows[3].连胜 === 0 && rows[3].连败 === 0 && rows[3].淘汰 === 0))
    bad.push("金铲铲装载初值错：" + JSON.stringify(rows[3]));
  for (const r of rows)
    if (!r.结果.includes(`模式 ${r.模式} 已装载`))
      bad.push(`模式 ${r.模式} 未回报已装载，实为 "${r.结果}"`);
}

// ---------------------------------------------------------------- 2. 兵线推进（§504）
{
  await mode(1);
  broadcast("兵线推进"); await stepN(60);
  snap.兵线 = { 波次: num(G("波次")), 进度: num(G("兵线进度")) };
  if (num(G("波次")) !== 1) bad.push("波次应为 1 + round(游戏秒/波间隔) = 1，实为 " + G("波次"));
  if (!near(G("兵线进度"), 0.3)) bad.push("兵线进度应为 兵线速度×波间隔 = 0.3，实为 " + G("兵线进度"));
  if (!has("结果", "进度")) bad.push("结果应回报兵线进度，实为 " + G("结果"));

  // 进度上限 1
  S("兵线速度", 1);
  broadcast("兵线推进"); await stepN(60);
  if (!near(G("兵线进度"), 1)) bad.push("兵线进度应被夹在 1 以内，实为 " + G("兵线进度"));

  // 兵线接触 → 进度不变
  await mode(1);
  S("兵线进度", 0.4); S("遇敌", 1);
  broadcast("兵线推进"); await stepN(60);
  snap.兵线接触 = { 进度: num(G("兵线进度")), 结果: String(G("结果")) };
  if (!near(G("兵线进度"), 0.4)) bad.push("双方兵线接触时进度应不变，实为 " + G("兵线进度"));
  if (!has("结果", "兵线接触")) bad.push("结果应提示兵线接触，实为 " + G("结果"));

  // 超级兵
  await mode(1);
  S("超级兵", 1);
  broadcast("兵线推进"); await stepN(60);
  if (!has("结果", "超级兵")) bad.push("超级兵波次应被标注，实为 " + G("结果"));

  // 炮车：LOL 每 3 波一次；王者第 7 波起每次
  await mode(2);
  S("游戏秒", 60); // 波次 = 1 + round(60/30) = 3 → 3 mod 3 = 0
  broadcast("兵线推进"); await stepN(60);
  snap.炮车_LOL = { 波次: num(G("波次")), 结果: String(G("结果")) };
  if (num(G("波次")) !== 3) bad.push("波次公式错，实为 " + G("波次"));
  if (!has("结果", "炮车")) bad.push("LOL 每 3 波应有炮车，实为 " + G("结果"));

  await mode(2);
  S("游戏秒", 30); // 波次 = 2 → 2 mod 3 ≠ 0
  broadcast("兵线推进"); await stepN(60);
  if (has("结果", "炮车")) bad.push("LOL 非 3 的倍数波不应有炮车，实为 " + G("结果"));

  await mode(1);
  S("游戏秒", 180); // 波次 = 7
  broadcast("兵线推进"); await stepN(60);
  snap.炮车_王者 = { 波次: num(G("波次")), 结果: String(G("结果")) };
  if (num(G("波次")) !== 7) bad.push("王者波次公式错，实为 " + G("波次"));
  if (!has("结果", "炮车")) bad.push("王者第 7 波起应有炮车，实为 " + G("结果"));

  await mode(1);
  S("游戏秒", 150); // 波次 = 6 < 7
  broadcast("兵线推进"); await stepN(60);
  if (has("结果", "炮车")) bad.push("王者第 6 波不应有炮车，实为 " + G("结果"));
}

// ---------------------------------------------------------------- 3. 塔索敌优先级（§505–§506）
{
  // LOL 优先级：英雄1 < 小兵6(2) < 炮车7(3) < 超级兵4/5(4) < 近战2(5) < 远程3(6)
  await mode(2);
  setList("候选类型", [6, 7, 2]);
  setList("候选距离", [500, 100, 50]);
  setList("候选伤害英雄", [0, 0, 0]);
  S("候选数", 3);
  broadcast("塔索敌"); await stepN(60);
  snap.塔索敌_LOL = { 最优单位: num(G("最优单位")), 优先级: num(G("最优优先级")), 距离: num(G("最优距离")) };
  if (num(G("最优单位")) !== 1 || num(G("最优优先级")) !== 2 || num(G("最优距离")) !== 500)
    bad.push("LOL 塔应优先打小兵(类型6→优先级2)，实为 " + JSON.stringify(snap.塔索敌_LOL));

  // 同优先级 → 距离近者优先
  await mode(2);
  setList("候选类型", [2, 2]);
  setList("候选距离", [300, 100]);
  setList("候选伤害英雄", [0, 0]);
  S("候选数", 2);
  broadcast("塔索敌"); await stepN(60);
  snap.塔索敌_同优先级 = { 最优单位: num(G("最优单位")), 距离: num(G("最优距离")) };
  if (num(G("最优单位")) !== 2 || num(G("最优距离")) !== 100)
    bad.push("同优先级应取更近的目标，实为 " + JSON.stringify(snap.塔索敌_同优先级));

  // 英雄绝对优先
  await mode(2);
  setList("候选类型", [6, 2]);
  setList("候选距离", [10, 900]);
  setList("候选伤害英雄", [0, 1]);
  S("候选数", 2);
  broadcast("塔索敌"); await stepN(60);
  snap.塔索敌_英雄 = { 最优单位: num(G("最优单位")), 优先级: num(G("最优优先级")) };
  if (num(G("最优单位")) !== 2 || num(G("最优优先级")) !== 1)
    bad.push("塔应绝对优先补刀英雄(优先级1)，实为 " + JSON.stringify(snap.塔索敌_英雄));

  // 王者优先级：英雄1 < 其他(类型≥2)2 < 类型1 → 3
  await mode(1);
  setList("候选类型", [1, 3]);
  setList("候选距离", [10, 900]);
  setList("候选伤害英雄", [0, 0]);
  S("候选数", 2);
  broadcast("塔索敌"); await stepN(60);
  snap.塔索敌_王者 = { 最优单位: num(G("最优单位")), 优先级: num(G("最优优先级")) };
  if (num(G("最优单位")) !== 2 || num(G("最优优先级")) !== 2)
    bad.push("王者塔应先打小兵(类型3→优先级2)，实为 " + JSON.stringify(snap.塔索敌_王者));

  await mode(1);
  setList("候选类型", [1]);
  setList("候选距离", [10]);
  setList("候选伤害英雄", [0]);
  S("候选数", 1);
  broadcast("塔索敌"); await stepN(60);
  if (num(G("最优优先级")) !== 3)
    bad.push("王者塔打类型1应得优先级3，实为 " + G("最优优先级"));
}

// ---------------------------------------------------------------- 4. 塔攻击 / 镀层（§507–§508）
{
  await mode(1); // 塔减伤 0.6
  S("目标类型", 1); S("无兵线", 0);
  broadcast("塔攻击"); await stepN(60);
  snap.塔攻击_王者1 = { 伤害: num(G("塔伤害")), 塔血: num(G("塔血量")), 次数: num(G("塔攻击次数")) };
  if (!near(G("塔伤害"), 60) || !near(G("塔血量"), 940) || num(G("塔攻击次数")) !== 1)
    bad.push("王者塔首次攻击：100×1×0.6=60，剩余 940，实为 " + JSON.stringify(snap.塔攻击_王者1));

  broadcast("塔攻击"); await stepN(60);
  snap.塔攻击_王者2 = { 伤害: num(G("塔伤害")), 塔血: num(G("塔血量")) };
  if (!near(G("塔伤害"), 78) || !near(G("塔血量"), 862))
    bad.push("王者塔第 2 次：100×1.3×0.6=78，剩余 862，实为 " + JSON.stringify(snap.塔攻击_王者2));

  await mode(1);
  S("目标类型", 1); S("无兵线", 1);
  broadcast("塔攻击"); await stepN(60);
  snap.塔攻击_无兵线 = { 伤害: num(G("塔伤害")) };
  if (!near(G("塔伤害"), 15)) bad.push("无兵线时塔伤害应 ×0.25 再 ×0.6 = 15，实为 " + G("塔伤害"));

  const typeDmg = {};
  for (const [t, d] of [[2, 27], [3, 42], [4, 8.4], [5, 3]]) {
    await mode(1);
    S("目标类型", t); S("无兵线", 0);
    broadcast("塔攻击"); await stepN(60);
    typeDmg[t] = num(G("塔伤害"));
    if (!near(G("塔伤害"), d))
      bad.push(`王者塔打类型${t}伤害应为 ${d}（含塔减伤0.6），实为 ${G("塔伤害")}`);
  }
  snap.塔伤害按类型 = typeDmg;

  // LOL 镀层：8 分半前每次攻击 -1，8 分半后清零
  await mode(2); // 塔减伤 1，镀层 5
  S("目标类型", 2); S("游戏秒", 100);
  broadcast("塔攻击"); await stepN(60);
  snap.镀层_前期 = { 镀层: num(G("镀层")), 伤害: num(G("塔伤害")) };
  if (num(G("镀层")) !== 4) bad.push("LOL 8 分半前攻击应掉 1 层镀层，实为 " + G("镀层"));
  if (!near(G("塔伤害"), 45)) bad.push("LOL 塔打类型2伤害应 45（塔减伤1），实为 " + G("塔伤害"));

  S("游戏秒", 900);
  broadcast("塔攻击"); await stepN(60);
  snap.镀层_后期 = { 镀层: num(G("镀层")) };
  if (num(G("镀层")) !== 0) bad.push("LOL 8 分半后镀层应清零，实为 " + G("镀层"));
}

// ---------------------------------------------------------------- 5. 补刀与漏刀（§509）
{
  await mode(1); // 漏刀系数 0.8
  S("补刀", 1);
  broadcast("补刀结算"); await stepN(60);
  snap.补刀 = { 补刀: num(G("补刀")), 金币: num(G("金币")) };
  if (num(G("金币")) !== 21) bad.push("补刀应给全额 21 金币，实为 " + G("金币"));

  S("补刀", 0);
  broadcast("补刀结算"); await stepN(60);
  snap.漏刀 = { 金币: num(G("金币")) };
  if (num(G("金币")) !== 38) bad.push("漏刀应给 round(21×0.8)=17，合计 38，实为 " + G("金币"));

  await mode(2); // 漏刀系数 0.4
  S("补刀", 0);
  broadcast("补刀结算"); await stepN(60);
  snap.漏刀_LOL = { 金币: num(G("金币")) };
  if (num(G("金币")) !== 8) bad.push("LOL 漏刀应给 round(21×0.4)=8，实为 " + G("金币"));
}

// ---------------------------------------------------------------- 6. 破塔顺序（§510）
{
  await mode(1);
  S("建筑序号", 1);
  broadcast("破塔"); await stepN(60);
  snap.破塔1 = { 顺序: num(G("破塔顺序")), 超级兵: num(G("超级兵")), 一血塔: num(G("一血塔已发")), 金币: num(G("金币")) };
  if (!(num(G("破塔顺序")) === 1 && num(G("超级兵")) === 0 &&
        num(G("一血塔已发")) === 1 && num(G("金币")) === 300))
    bad.push("破第 1 塔：顺序1/无超级兵/发一血塔奖励300金，实为 " + JSON.stringify(snap.破塔1));

  S("建筑序号", 3);
  broadcast("破塔"); await stepN(60);
  if (num(G("破塔顺序")) !== 2 || num(G("超级兵")) !== 0)
    bad.push("破第 3 塔：顺序2/仍无超级兵，实为 " + G("破塔顺序") + "/" + G("超级兵"));

  S("建筑序号", 4);
  broadcast("破塔"); await stepN(60);
  if (num(G("破塔顺序")) !== 3 || num(G("超级兵")) !== 1)
    bad.push("破第 4 塔应出超级兵，实为 " + G("超级兵"));

  // 乱序破塔必须被拒
  await mode(1);
  S("破塔顺序", 3); S("建筑序号", 2);
  broadcast("破塔"); await stepN(60);
  snap.乱序破塔 = { 顺序: num(G("破塔顺序")), 结果: String(G("结果")) };
  if (num(G("破塔顺序")) !== 3) bad.push("乱序破塔不应推进顺序，实为 " + G("破塔顺序"));
  if (!has("结果", "必须按顺序破塔")) bad.push("乱序破塔应被拒绝并提示，实为 " + G("结果"));

  // 破满 6 塔 → 主基地推倒
  await mode(1);
  for (let k = 1; k <= 6; k++) { S("建筑序号", k); broadcast("破塔"); await stepN(40); }
  snap.破塔结束 = { 顺序: num(G("破塔顺序")), 结束: num(G("结束")), 基地血: num(G("主基地血")) };
  if (!(num(G("破塔顺序")) === 6 && num(G("结束")) === 1 && num(G("主基地血")) === 0))
    bad.push("破满 6 塔应结束对局并推倒主基地，实为 " + JSON.stringify(snap.破塔结束));
}

// ---------------------------------------------------------------- 7. 三国杀回合与阶段（§511–§512）
{
  await mode(3);
  // 三国杀一轮 = 一个角色的 6 个阶段；**角色只在阶段回卷时推进**（不是每阶段都推进）。
  const seen = [];
  for (let k = 0; k < 13; k++) {
    broadcast("SG回合推进"); await stepN(40);
    seen.push({ 阶段: num(G("当前阶段")), 角色: num(G("回合角色")) });
  }
  snap.SG回合 = seen;
  const phases = seen.map((x) => x.阶段).join(",");
  if (phases !== "1,2,3,4,5,6,1,2,3,4,5,6,1")
    bad.push("阶段应 1..6 循环，实为 " + phases);
  const roles = seen.map((x) => x.角色).join(",");
  if (roles !== "1,1,1,1,1,1,2,2,2,2,2,2,3")
    bad.push("回合角色应在每个角色的 6 个阶段走完后推进，实为 " + roles);
  // 第 3 阶段自动摸牌（13 次推进触发 2 次）
  snap.SG摸牌联动 = { 手牌: num(G("手牌数")), 牌堆: num(G("牌堆数")) };
  if (num(G("手牌数")) !== 4 || num(G("牌堆数")) !== 6)
    bad.push("第 3 阶段应自动摸牌（13 步触发 2 次 → 手牌4/牌堆6），实为 " + JSON.stringify(snap.SG摸牌联动));

  await mode(3);
  broadcast("SG回合推进"); await stepN(40);
  broadcast("SG回合推进"); await stepN(40);
  broadcast("SG回合推进"); await stepN(60);
  snap.SG摸牌联动_单轮 = { 手牌: num(G("手牌数")), 牌堆: num(G("牌堆数")) };
  if (num(G("手牌数")) !== 2 || num(G("牌堆数")) !== 8)
    bad.push("第 3 阶段应自动摸 2 张（手牌2/牌堆8），实为 " + JSON.stringify(snap.SG摸牌联动_单轮));
}

// ---------------------------------------------------------------- 8. 三国杀摸牌 / 洗牌（§513）
{
  await mode(3);
  S("牌堆数", 10); S("弃牌堆数", 0); S("摸牌数", 2); S("手牌数", 0);
  broadcast("SG摸牌"); await stepN(60);
  snap.SG摸牌 = { 手牌: num(G("手牌数")), 牌堆: num(G("牌堆数")) };
  if (num(G("手牌数")) !== 2 || num(G("牌堆数")) !== 8)
    bad.push("摸 2 张后手牌 2 / 牌堆 8，实为 " + JSON.stringify(snap.SG摸牌));

  // 牌堆不足 → 摸牌数被夹到牌堆数
  S("牌堆数", 1); S("摸牌数", 2);
  broadcast("SG摸牌"); await stepN(60);
  snap.SG摸牌_不足 = { 手牌: num(G("手牌数")), 牌堆: num(G("牌堆数")) };
  if (num(G("手牌数")) !== 3 || num(G("牌堆数")) !== 0)
    bad.push("牌堆只剩 1 张时只应摸 1 张（手牌3/牌堆0），实为 " + JSON.stringify(snap.SG摸牌_不足));

  // 牌堆空 → 弃牌堆洗混成新牌堆
  S("牌堆数", 0); S("弃牌堆数", 5); S("摸牌数", 2);
  broadcast("SG摸牌"); await stepN(60);
  snap.SG洗牌 = { 牌堆: num(G("牌堆数")), 弃牌堆: num(G("弃牌堆数")), 手牌: num(G("手牌数")), 结果: String(G("结果")) };
  if (!(num(G("牌堆数")) === 3 && num(G("弃牌堆数")) === 0 && num(G("手牌数")) === 5))
    bad.push("弃牌堆洗混后应再抽 2 张（手牌5/牌堆3/弃牌0），实为 " + JSON.stringify(snap.SG洗牌));
  if (!has("结果", "弃牌堆洗混")) bad.push("洗牌应有提示，实为 " + G("结果"));
}

// ---------------------------------------------------------------- 9. 三国杀判定（§514）
{
  await mode(3);
  S("判定区数", 0);
  broadcast("SG判定"); await stepN(60);
  if (!has("结果", "判定区为空")) bad.push("判定区为空应提示，实为 " + G("结果"));

  // 花色 = mod(牌,4)；点数 = mod(牌,13)+1
  setItem("判定区", 2, 4);
  S("判定区数", 2);
  broadcast("SG判定"); await stepN(60);
  snap.SG判定_黑桃 = { 牌: num(G("判定牌")), 花色: num(G("判定花色")), 点数: num(G("判定点数")), 结果: num(G("判定结果")) };
  if (!(num(G("判定牌")) === 4 && num(G("判定花色")) === 0 && num(G("判定点数")) === 5))
    bad.push("判定牌4 应得花色0/点数5，实为 " + JSON.stringify(snap.SG判定_黑桃));
  if (num(G("判定结果")) !== 3)
    bad.push("花色0 且点数 2..9 应判成 3（可横置），实为 " + G("判定结果"));
  if (num(G("判定区数")) !== 1) bad.push("判定后判定区数应减 1，实为 " + G("判定区数"));

  // 红桃（花色1）→ 判定成功 0
  setItem("判定区", 1, 1);
  S("判定区数", 1);
  broadcast("SG判定"); await stepN(60);
  snap.SG判定_红桃 = { 花色: num(G("判定花色")), 点数: num(G("判定点数")), 结果: num(G("判定结果")) };
  if (!(num(G("判定花色")) === 1 && num(G("判定点数")) === 2 && num(G("判定结果")) === 0))
    bad.push("红桃判定应成功(0)，实为 " + JSON.stringify(snap.SG判定_红桃));

  // 方块/梅花 → 判定失败 1
  setItem("判定区", 1, 2);
  S("判定区数", 1);
  broadcast("SG判定"); await stepN(60);
  if (num(G("判定结果")) !== 1) bad.push("非红桃非黑桃应判失败(1)，实为 " + G("判定结果"));

  // 改判：改判后按「红桃 A」重判
  setItem("判定区", 1, 13);
  S("判定区数", 1); S("改判可用", 1);
  broadcast("SG判定"); await stepN(60);
  snap.SG判定_改判 = { 牌: num(G("判定牌")), 花色: num(G("判定花色")), 点数: num(G("判定点数")), 改判: num(G("改判次数")), 结果: num(G("判定结果")) };
  if (!(num(G("判定牌")) === 99 && num(G("判定花色")) === 1 && num(G("判定点数")) === 1 &&
        num(G("改判次数")) === 1 && num(G("判定结果")) === 0))
    bad.push("改判应重判为红桃A且改判次数=1，实为 " + JSON.stringify(snap.SG判定_改判));
}

// ---------------------------------------------------------------- 10. 三国杀距离（§515）
{
  await mode(3);
  S("人数", 8); S("攻击范围", 1); S("座位A", 1); S("座位B", 5);
  broadcast("SG距离"); await stepN(60);
  snap.SG距离_直线 = { 基础: num(G("基础距离")), 实际: num(G("实际距离")), 合法: num(G("临时")) };
  if (!(num(G("基础距离")) === 4 && num(G("实际距离")) === 4))
    bad.push("座位1↔5 基础距离应为 4，实为 " + JSON.stringify(snap.SG距离_直线));
  if (num(G("临时")) !== 0) bad.push("距离4 > 范围1 应判不合法，实为 " + G("临时"));

  // 环形距离：1 ↔ 8 只有 1 步
  S("座位B", 8);
  broadcast("SG距离"); await stepN(60);
  snap.SG距离_环形 = { 基础: num(G("基础距离")), 合法: num(G("临时")) };
  if (num(G("基础距离")) !== 1) bad.push("座位1↔8 环形距离应为 1，实为 " + G("基础距离"));
  if (num(G("临时")) !== 1) bad.push("距离1 ≤ 范围1 应判合法，实为 " + G("临时"));

  // +1 马 / -1 马
  S("座位B", 5); S("加一马", 1); S("攻击范围", 5);
  broadcast("SG距离"); await stepN(60);
  if (num(G("实际距离")) !== 5) bad.push("加一马后实际距离应为 5，实为 " + G("实际距离"));

  S("加一马", 0); S("减一马", 3);
  broadcast("SG距离"); await stepN(60);
  if (num(G("实际距离")) !== 1) bad.push("减一马后实际距离应为 1，实为 " + G("实际距离"));

  // 距离下限夹到 1
  S("减一马", 5);
  broadcast("SG距离"); await stepN(60);
  if (num(G("实际距离")) !== 1) bad.push("实际距离下限应夹到 1，实为 " + G("实际距离"));
}

// ---------------------------------------------------------------- 11. 三国杀求桃 / 胜负（§516–§517）
{
  await mode(3);
  S("自救", 0); S("桃数", 0); S("体力", 0);
  broadcast("SG求桃"); await stepN(60);
  snap.SG求桃_无人 = { 体力: num(G("体力")), 结果: String(G("结果")) };
  if (num(G("体力")) !== 0) bad.push("无人出桃应体力归零，实为 " + G("体力"));
  if (!has("结果", "全员无桃")) bad.push("无人出桃应进入死亡结算，实为 " + G("结果"));

  setItem("求桃队列", 3, 1);
  broadcast("SG求桃"); await stepN(60);
  snap.SG求桃_有人 = { 体力: num(G("体力")), 结果: String(G("结果")) };
  if (num(G("体力")) !== 1) bad.push("有人出桃应救回体力 1，实为 " + G("体力"));
  if (!has("结果", "角色 3 出桃救人")) bad.push("应报出桃者座位 3，实为 " + G("结果"));

  S("自救", 1); S("桃数", 1);
  broadcast("SG求桃"); await stepN(60);
  snap.SG求桃_自救 = { 体力: num(G("体力")), 结果: String(G("结果")) };
  if (num(G("体力")) !== 1) bad.push("自救应恢复体力 1，实为 " + G("体力"));
  if (!has("结果", "自救成功")) bad.push("自救应优先，实为 " + G("结果"));

  // 胜负
  const wins = [];
  for (const [k, want] of [
    [{ 主公死: 1, 唯一存活内奸: 0 }, "反贼胜"],
    [{ 主公死: 1, 唯一存活内奸: 1 }, "内奸胜"],
    [{ 主公死: 0, 反贼存活: 0, 内奸存活: 0 }, "主忠胜"],
    [{ 主公死: 0, 反贼存活: 1, 内奸存活: 0 }, "继续"],
  ]) {
    await mode(3);
    for (const [kk, vv] of Object.entries(k)) S(kk, vv);
    broadcast("SG胜负"); await stepN(60);
    wins.push({ 输入: k, 胜负: String(G("胜负")) });
    if (String(G("胜负")) !== want)
      bad.push(`胜负判定 ${JSON.stringify(k)} 应为 ${want}，实为 ${G("胜负")}`);
  }
  snap.SG胜负 = wins;
}

// ---------------------------------------------------------------- 12. 金铲铲收入（§518）
{
  await mode(4);
  S("基础收入", 5); S("金币铲", 0); S("本回合胜", 0);
  broadcast("JCC收入"); await stepN(60);
  snap.JCC收入1 = { 收入: num(G("回合收入")), 金币: num(G("金币铲")), 连败: num(G("连败")) };
  if (!(num(G("回合收入")) === 5 && num(G("金币铲")) === 5 && num(G("连败")) === 1))
    bad.push("首回合收入应为 基础5+利息0+连胜0+胜利0=5，实为 " + JSON.stringify(snap.JCC收入1));

  broadcast("JCC收入"); await stepN(60);
  snap.JCC收入2 = { 收入: num(G("回合收入")), 金币: num(G("金币铲")), 连败: num(G("连败")) };
  if (!(num(G("回合收入")) === 6 && num(G("金币铲")) === 11 && num(G("连败")) === 2))
    bad.push("次回合利息 round(5/10)=1 → 收入6、金币11，实为 " + JSON.stringify(snap.JCC收入2));

  // 连胜奖励
  await mode(4);
  S("金币铲", 0); S("连胜", 2); S("连败", 0); S("本回合胜", 1);
  broadcast("JCC收入"); await stepN(60);
  snap.JCC连胜2 = { 奖励: num(G("连胜奖励")), 收入: num(G("回合收入")), 连胜: num(G("连胜")) };
  if (!(num(G("连胜奖励")) === 1 && num(G("回合收入")) === 7 && num(G("连胜")) === 3))
    bad.push("连胜2 应奖励1 → 收入7、连胜3，实为 " + JSON.stringify(snap.JCC连胜2));

  await mode(4);
  S("金币铲", 0); S("连胜", 4); S("连败", 0); S("本回合胜", 1);
  broadcast("JCC收入"); await stepN(60);
  snap.JCC连胜4 = { 奖励: num(G("连胜奖励")), 收入: num(G("回合收入")) };
  if (!(num(G("连胜奖励")) === 2 && num(G("回合收入")) === 8))
    bad.push("连胜4 应奖励2 → 收入8，实为 " + JSON.stringify(snap.JCC连胜4));

  // 利息上限 5
  await mode(4);
  S("金币铲", 100); S("基础收入", 0); S("连胜", 0); S("连败", 0); S("本回合胜", 0);
  broadcast("JCC收入"); await stepN(60);
  snap.JCC利息上限 = { 利息: num(G("利息")) };
  if (num(G("利息")) !== 5) bad.push("利息上限应为 5，实为 " + G("利息"));
}

// ---------------------------------------------------------------- 13. 金铲铲刷新 / 抽卡（§519）
{
  await mode(4);
  S("金币铲", 10); S("刷新费", 2); S("种子", 1); S("人口", 1);
  broadcast("JCC刷新"); await stepN(60);
  snap.JCC刷新1 = {
    金币: num(G("金币铲")), 种子: num(G("种子")), 抽签: num(G("抽签值")),
    门槛: num(G("概率门槛")), 费用: num(G("棋子费")), 棋子: num(G("棋子ID")),
    卡池剩: num(getList("卡池")[9]),
  };
  if (num(G("金币铲")) !== 8) bad.push("刷新应扣 2 金，实为 " + G("金币铲"));
  if (num(G("种子")) !== 282475249) bad.push("Park-Miller 种子序列应到 282475249，实为 " + G("种子"));
  if (num(G("抽签值")) !== 7) bad.push("抽签值应为 mod(16807,100)=7，实为 " + G("抽签值"));
  if (num(G("概率门槛")) !== 80) bad.push("人口1 的概率门槛应为 80，实为 " + G("概率门槛"));
  if (num(G("棋子费")) !== 1) bad.push("人口1 抽签 7 ≤ 80 应出 1 费棋，实为 " + G("棋子费"));
  if (num(G("棋子ID")) !== 10) bad.push("棋子ID 应为 mod(282475249,10)+1=10，实为 " + G("棋子ID"));
  if (num(getList("卡池")[9]) !== 1) bad.push("卡池[10] 应由 2 减到 1，实为 " + getList("卡池")[9]);

  broadcast("JCC刷新"); await stepN(60);
  snap.JCC刷新2 = { 种子: num(G("种子")), 棋子: num(G("棋子ID")), 费用: num(G("棋子费")) };
  if (num(G("种子")) !== 984943658) bad.push("第二次刷新种子应到 984943658，实为 " + G("种子"));
  if (num(G("棋子ID")) !== 9) bad.push("第二次刷新棋子应为 9，实为 " + G("棋子ID"));

  // 人口上到 4 → 门槛 0 → 抽签 7 落在 (0,15] → 2 费棋
  await mode(4);
  S("金币铲", 10); S("刷新费", 0); S("种子", 1); S("人口", 4);
  broadcast("JCC刷新"); await stepN(60);
  snap.JCC刷新_人口4 = { 门槛: num(G("概率门槛")), 抽签: num(G("抽签值")), 费用: num(G("棋子费")) };
  if (!(num(G("概率门槛")) === 0 && num(G("棋子费")) === 2))
    bad.push("人口4 门槛0、抽签7 应出 2 费棋，实为 " + JSON.stringify(snap.JCC刷新_人口4));

  // 共享卡池抽空 → 不可购买
  await mode(4);
  setList("卡池", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
  S("金币铲", 10); S("刷新费", 2); S("种子", 1);
  broadcast("JCC刷新"); await stepN(60);
  snap.JCC卡池抽空 = { 结果: String(G("结果")) };
  if (!has("结果", "抽空")) bad.push("卡池抽空应提示不可购买，实为 " + G("结果"));
}

// ---------------------------------------------------------------- 14. 金铲铲升星 / 羁绊（§520–§521）
{
  await mode(4);
  setList("棋子ID表", [5, 5, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
  setList("棋子星级", [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
  S("棋子ID", 5); S("星级", 1);
  broadcast("JCC升星"); await stepN(60);
  snap.JCC升星 = { 同名数: num(G("同名数")), 星级: num(G("星级")), 结果: String(G("结果")) };
  if (!(num(G("同名数")) === 3 && num(G("星级")) === 2))
    bad.push("3 个同名同星应合成升到 2 星，实为 " + JSON.stringify(snap.JCC升星));

  await mode(4);
  setList("棋子ID表", [5, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
  setList("棋子星级", [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
  S("棋子ID", 5); S("星级", 1);
  broadcast("JCC升星"); await stepN(60);
  snap.JCC不升星 = { 同名数: num(G("同名数")), 星级: num(G("星级")) };
  if (!(num(G("同名数")) === 2 && num(G("星级")) === 1))
    bad.push("只有 2 个同名不应升星，实为 " + JSON.stringify(snap.JCC不升星));

  // 羁绊：计数 = 非空棋子数；达到阈值 → 激活；再达人口档 → 再 +1
  await mode(4);
  setList("棋子ID表", [1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
  S("羁绊阈值", 2); S("人口", 1);
  broadcast("JCC羁绊"); await stepN(60);
  snap.JCC羁绊_满 = { 计数: num(G("羁绊计数")), 激活: num(G("羁绊激活")) };
  if (!(num(G("羁绊计数")) === 2 && num(G("羁绊激活")) === 2))
    bad.push("2 个不重复棋子 + 人口1档阈值2 → 激活层级 2，实为 " + JSON.stringify(snap.JCC羁绊_满));

  await mode(4);
  setList("棋子ID表", [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
  S("羁绊阈值", 2); S("人口", 1);
  broadcast("JCC羁绊"); await stepN(60);
  snap.JCC羁绊_未满 = { 计数: num(G("羁绊计数")), 激活: num(G("羁绊激活")) };
  if (!(num(G("羁绊计数")) === 1 && num(G("羁绊激活")) === 0))
    bad.push("1 个棋子不该激活羁绊，实为 " + JSON.stringify(snap.JCC羁绊_未满));
}

// ---------------------------------------------------------------- 15. 金铲铲战斗 / 选秀（§522–§523）
{
  await mode(4);
  S("战力", 10); S("敌战力", 5); S("生命", 100); S("阶段基础伤害", 2); S("存活棋子", 3);
  broadcast("JCC战斗"); await stepN(60);
  snap.JCC战斗_胜 = { 胜: num(G("本回合胜")), 扣血: num(G("扣血")), 生命: num(G("生命")), 结果: String(G("结果")) };
  if (!(num(G("本回合胜")) === 1 && num(G("扣血")) === 0 && num(G("生命")) === 100))
    bad.push("战力更高应零扣血获胜，实为 " + JSON.stringify(snap.JCC战斗_胜));
  if (!has("结果", "战斗胜利")) bad.push("应回报战斗胜利，实为 " + G("结果"));

  await mode(4);
  S("战力", 3); S("敌战力", 8); S("生命", 100); S("阶段基础伤害", 2); S("存活棋子", 3);
  broadcast("JCC战斗"); await stepN(60);
  snap.JCC战斗_败 = { 胜: num(G("本回合胜")), 扣血: num(G("扣血")), 生命: num(G("生命")) };
  if (!(num(G("本回合胜")) === 0 && num(G("扣血")) === 5 && num(G("生命")) === 95))
    bad.push("战败应扣 阶段伤害2+存活棋子3=5，实为 " + JSON.stringify(snap.JCC战斗_败));

  await mode(4);
  S("战力", 3); S("敌战力", 8); S("生命", 5); S("阶段基础伤害", 2); S("存活棋子", 3);
  broadcast("JCC战斗"); await stepN(60);
  snap.JCC淘汰 = { 生命: num(G("生命")), 淘汰: num(G("淘汰")) };
  if (!(num(G("生命")) === 0 && num(G("淘汰")) === 1))
    bad.push("生命归零应被淘汰，实为 " + JSON.stringify(snap.JCC淘汰));

  // 选秀：生命最低者先选
  await mode(4);
  setList("生命表", [50, 80, 30, 90, 70, 60, 10, 20]);
  broadcast("JCC选秀"); await stepN(60);
  snap.JCC选秀 = { 最低: num(G("最低血者")), 顺序: num(G("选秀顺序")) };
  if (!(num(G("最低血者")) === 7 && num(G("选秀顺序")) === 7))
    bad.push("选秀应由生命最低的第 7 位先选，实为 " + JSON.stringify(snap.JCC选秀));
}

// ---------------------------------------------------------------- 16. 结算页与复位入口（§525 铁律7）
{
  const targetByName = (n) => vm.runtime.targets.find(
    (t) => !t.isStage && ((t.sprite && t.sprite.name) || t.name) === n);

  // ⚠️ 帧广播挂在舞台 forever 的「自动帧=1」分支里：
  //    结算页靠「帧」驱动，所以这一段必须把 自动帧 打开（纯逻辑段则关掉，保证确定性）。
  S("自动帧", 1);

  // 三种结束信号都要能把结算页点亮
  await mode(1);
  for (let k = 1; k <= 6; k++) { S("建筑序号", k); broadcast("破塔"); await stepN(40); }
  await stepN(120);
  let panel = targetByName("结算板");
  let again = targetByName("再来一局");
  snap.结算页 = { 结算板存在: !!panel, 再来一局存在: !!again };
  if (!panel || !again) bad.push("缺少结算板 / 再来一局 角色（铁律7）");
  else {
    snap.结算页.结束信号 = { 结束: num(G("结束")), 结算板可见: panel.visible, 按钮可见: again.visible };
    if (num(G("结束")) !== 1) bad.push("破满 6 塔后 结束 应为 1，实为 " + G("结束"));
    if (!panel.visible) bad.push("结束信号触发后结算板应显示");
    if (!again.visible) bad.push("结束信号触发后「再来一局」按钮应显示");
  }

  // 三国杀结束信号：胜负 ≠ 继续
  await mode(3);
  S("主公死", 1); S("唯一存活内奸", 0);
  broadcast("SG胜负"); await stepN(120);
  panel = targetByName("结算板");
  snap.结算页.三国杀 = { 胜负: String(G("胜负")), 结算板可见: panel ? panel.visible : null };
  if (!panel || !panel.visible) bad.push("三国杀胜负落定后结算板应显示");

  // 金铲铲结束信号：淘汰 = 1
  await mode(4);
  S("战力", 1); S("敌战力", 9); S("生命", 3); S("阶段基础伤害", 2); S("存活棋子", 3);
  broadcast("JCC战斗"); await stepN(120);
  panel = targetByName("结算板");
  snap.结算页.金铲铲 = { 淘汰: num(G("淘汰")), 结算板可见: panel ? panel.visible : null };
  if (!panel || !panel.visible) bad.push("金铲铲被淘汰后结算板应显示");

  // 点「再来一局」→ 复位广播把结算信号清零
  again = targetByName("再来一局");
  if (again) {
    vm.runtime.startHats("event_whenthisspriteclicked", null, again);
    await stepN(120);
    snap.结算页.复位后 = { 结束: num(G("结束")), 淘汰: num(G("淘汰")), 胜负: String(G("胜负")) };
    if (num(G("结束")) !== 0 || num(G("淘汰")) !== 0 || String(G("胜负")) !== "继续")
      bad.push("点「再来一局」应广播重置并清空结算信号，实为 " + JSON.stringify(snap.结算页.复位后));
  }

  // 结算页不出现时也必须是不显示（自动帧打开也不该误亮）
  await mode(1);
  await stepN(120);
  panel = targetByName("结算板");
  snap.结算页.未结束 = { 结算板可见: panel ? panel.visible : null };
  if (panel && panel.visible) bad.push("对局未结束结算板不应显示");

  S("自动帧", 0);
}

// ---------------------------------------------------------------- 17. 跨模式隔离（§524）
{
  // 模式 3/4 不应改动 MOBA 变量；模式 1/2 不应改动 SG/JCC 变量
  await mode(3);
  const mobaBefore = [num(G("漏刀系数")), num(G("塔减伤")), num(G("镀层"))];
  broadcast("SG回合推进"); await stepN(60);
  broadcast("SG胜负"); await stepN(60);
  const mobaAfter = [num(G("漏刀系数")), num(G("塔减伤")), num(G("镀层"))];
  if (mobaBefore.join(",") !== mobaAfter.join(","))
    bad.push("三国杀模式不应改动 MOBA 参数，实为 " + mobaAfter.join(","));

  await mode(4);
  const sgBefore = [num(G("牌堆数")), num(G("判定区数")), String(G("胜负"))];
  broadcast("JCC收入"); await stepN(60);
  broadcast("JCC战斗"); await stepN(60);
  const sgAfter = [num(G("牌堆数")), num(G("判定区数")), String(G("胜负"))];
  if (sgBefore.join(",") !== sgAfter.join(","))
    bad.push("金铲铲模式不应改动三国杀状态，实为 " + sgAfter.join(","));

  // 种子可复现：同种子两次刷新得到同一棋子
  const draw = async () => {
    await mode(4);
    S("金币铲", 10); S("刷新费", 2); S("种子", 1);
    broadcast("JCC刷新"); await stepN(60);
    return `${num(G("种子"))}/${num(G("棋子ID"))}/${num(G("棋子费"))}`;
  };
  const d1 = await draw();
  const d2 = await draw();
  snap.可复现抽卡 = { 第一次: d1, 第二次: d2 };
  if (d1 !== d2) bad.push("同种子刷新必须得到同一结果，实为 " + d1 + " vs " + d2);
}

// ---------------------------------------------------------------- 结果
const pass = bad.length === 0;
console.log(JSON.stringify(snap, null, 2));
if (pass) {
  console.log("STRATEGY_REPLICAS_LOGIC_OK  四模式复刻引擎判定全部正确（王者 / LOL / 三国杀 / 金铲铲）");
  process.exit(0);
} else {
  console.log("STRATEGY_REPLICAS_LOGIC_FAIL");
  for (const b of bad) console.log("  ✗ " + b);
  process.exit(1);
}
