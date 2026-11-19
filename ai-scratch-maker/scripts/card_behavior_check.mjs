// 桌游判定行为校验：斗地主 / UNO / 板子 / 红狼 / 竞选 / 警徽流 / 自爆 / 屠边 / 觉醒 / 新月事件。
// 用法: node card_behavior_check.mjs <card_game.sb3>
//
// 桌游的判定逻辑是「输入 → 输出」的纯函数，最适合拿已知答案硬校验：
//   牌型识别 13 例（含 2 不能进顺子、飞机带单、王炸压炸弹）
//   比大小 7 例（同型比主值 / 炸弹通吃 / 王炸最大）
//   UNO 2 例（同色、同数字、万能都能出）
//   狼人杀 3 例（一边倒 / 平票 / 死人不能计票）
//   板子装载 1 例（逗号串拆成身份池，12人进阶场计数）
//   警长竞选 6 例（无人上警 / 唯一候选 / 得票最多 / 平票进 PK / PK 决出 / PK 再平）
//   警徽流 5 例（金水移交 / 查杀撕徽 / 接徽人已死 / 没留流 / 非警长）
//   自爆 4 例（双爆第一爆 / 恢复竞选 / 第二爆吞警徽 / 不可自爆身份 / 单爆规则）
//   屠边 5 例（开局继续 / 屠民 / 屠神 / 好人胜 / 无民板子不误判）
//   红狼 4 例（87 身份三表对齐 / 机械狼板 12 张 / 炸弹师 10 人 / 疯狂动物园 9 人）
//   觉醒 7 组（93 身份 13 觉醒 / 3 个觉醒板子 / 集合查验 / 协助者投票 8 例 /
//              狼王爪守恒与最后一狼 / 偶像死因分叉 / 梦语技能通道 / 决斗连击）
//   新月 5 组（10 张卡库 / 一局一次与种子复现 / 三类时效清理 /
//              快照栈恢复 / 结算类事件与身份实时查座位）
//
// 它抓的是「四层校验完全看不见」的错：
//   ① 牌型判定顺序错（三带二被当成三张）
//   ② 顺子把 2 算进去（数值上连续，规则上不允许）
//   ③ 炸弹没通吃
//   ④ UNO 只判同数字忘了同色
//   ⑤ 平票只取一个人
//   ⑥ 身份编码表与列表下标错位（阵营统计全错）
//   ⑦ 两个平级 IF 互相覆盖（双爆退化成单爆）
//   ⑧ 存活民恒为 0 导致无民板子开局判负
//   ⑨ 集合查验被写成两次单验、协助者不查重复、狼王爪被复制而非转移
//   ⑩ 梦语出局走夜伤通道被自己的免疫挡掉、变身早于胜负结算
//   ⑪ 事件卡撤销时把开关置默认值抹掉别的效果、永久卡被回合末清理、
//      结算类事件没在阶段末重判胜负、随机抽卡不可复现
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
const getVar = (name) => {
  const v = allNames()[name];
  return v ? v.value : undefined;
};
const setVar = (name, value) => {
  const v = allNames()[name];
  if (v) { v.value = value; return true; }
  return false;
};
const getList = (name) => {
  const v = allNames()[name];
  return v ? v.value : undefined;
};
const setList = (name, arr) => {
  const v = allNames()[name];
  if (v) { v.value = arr.slice(); return true; }
  return false;
};

const stepN = async (n) => {
  for (let i = 0; i < n; i++) {
    vm.runtime.currentMSecs += 33;
    vm.runtime._step();
    await Promise.resolve();
  }
};
const broadcast = (m) =>
  vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: m });

const bad = [];
const snap = { 牌型: [], 比大小: [], UNO: [], 狼人杀: {} };

// ---------------------------------------------------------------- 0. 启动
vm.greenFlag();
await stepN(3);
setVar("自动帧", 0);
await stepN(2);
if (vm.runtime.targets.filter((t) => !t.isStage).length < 2)
  bad.push("角色数异常");

// ---------------------------------------------------------------- 1. 斗地主牌型
const RANK = { 11: "J", 12: "Q", 13: "K", 14: "A", 15: "2", 16: "小王", 17: "大王" };
const nm = (v) => RANK[v] || String(v);
const combos = [
  { cards: [5], want: "单张", val: 5 },
  { cards: [7, 7], want: "对子", val: 7 },
  { cards: [9, 9, 9], want: "三张", val: 9 },
  { cards: [9, 9, 9, 4], want: "三带一", val: 9 },
  { cards: [9, 9, 9, 4, 4], want: "三带二", val: 9 },
  { cards: [3, 4, 5, 6, 7], want: "顺子", val: 3 },
  { cards: [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14], want: "顺子", val: 3 },
  { cards: [11, 12, 13, 14, 15], want: "不成牌型", val: 0, note: "含 2 不能成顺" },
  { cards: [3, 3, 4, 4, 5, 5], want: "连对", val: 3 },
  { cards: [9, 9, 9, 10, 10, 10], want: "飞机", val: 9 },
  { cards: [6, 6, 6, 6], want: "炸弹", val: 56 },
  { cards: [16, 17], want: "王炸", val: 100 },
  { cards: [3, 5, 7, 9], want: "不成牌型", val: 0 },
  { cards: [5, 5, 5, 8, 8, 8, 3, 4], want: "飞机带单", val: 5 },
];
for (const c of combos) {
  setList("牌组", c.cards);
  broadcast("判牌型");
  await stepN(40);
  const got = getVar("牌型");
  const gv = num(getVar("主值"));
  const label = c.cards.map(nm).join(" ");
  snap.牌型.push({ 牌: label, 判定: got, 主值: gv, 期望: c.want + "/" + c.val });
  if (got !== c.want || gv !== c.val)
    bad.push("牌型[" + label + "] 应为 " + c.want + "/" + c.val + "，实为 " + got + "/" + gv
             + (c.note ? "（" + c.note + "）" : ""));
}

// ---------------------------------------------------------------- 2. 比大小
const beats = [
  { mine: ["对子", 9], prev: ["对子", 7], want: 1 },
  { mine: ["对子", 7], prev: ["对子", 9], want: 0 },
  { mine: ["炸弹", 53], prev: ["对子", 14], want: 1 },
  { mine: ["对子", 14], prev: ["炸弹", 53], want: 0 },
  { mine: ["王炸", 100], prev: ["炸弹", 56], want: 1 },
  { mine: ["顺子", 5], prev: ["顺子", 3], want: 1 },
  { mine: ["三张", 9], prev: ["对子", 9], want: 0 },
];
for (const b of beats) {
  setVar("牌型", b.mine[0]); setVar("主值", b.mine[1]);
  setVar("上家型", b.prev[0]); setVar("上家值", b.prev[1]);
  broadcast("比大小");
  await stepN(20);
  const got = num(getVar("能压"));
  snap.比大小.push({ 我方: b.mine.join("/"), 上家: b.prev.join("/"), 能压: got });
  if (got !== b.want)
    bad.push("比大小 " + b.mine.join("/") + " vs " + b.prev.join("/") + " 应为 " + b.want + "，实为 " + got);
}

// ---------------------------------------------------------------- 3. UNO
{
  setList("手牌色", [1, 1, 2, 3, 0]);
  setList("手牌值", [5, 9, 5, 2, 13]);
  setVar("台面色", 1); setVar("台面值", 5);
  broadcast("判UNO");
  await stepN(30);
  const cnt = num(getVar("可出数"));
  const idx = (getList("可出表") || []).map(Number);
  snap.UNO.push({ 台面: "红-5", 可出数: cnt, 下标: idx });
  // 红5(同色同数) 红9(同色) 黄5(同数) 万能 → 4 张；蓝2 不能出
  if (cnt !== 4) bad.push("UNO 可出数应为 4，实为 " + cnt);
  if (String(idx.join(",")) !== "1,2,3,5")
    bad.push("UNO 可出下标应为 1,2,3,5（1-based），实为 " + idx.join(","));
}
{
  setList("手牌色", [3, 3, 2, 0]);
  setList("手牌值", [7, 1, 4, 14]);
  setVar("台面色", 1); setVar("台面值", 5);
  broadcast("判UNO");
  await stepN(30);
  const cnt = num(getVar("可出数"));
  snap.UNO.push({ 台面: "红-5", 可出数: cnt });
  if (cnt !== 1) bad.push("UNO 第二例可出数应为 1（仅万能），实为 " + cnt);
}

// ---------------------------------------------------------------- 4. 狼人杀投票
{
  setVar("玩家数", 4);
  setList("存活表", [1, 1, 1, 1]);       // 下标 k-1 = 玩家 k，1=存活
  setList("票箱", [2, 2, 4, 2]);        // A→B B→B C→D D→B
  broadcast("统计票");
  await stepN(30);
  const top = num(getVar("最高票"));
  const out = (getList("出局表") || []).map(Number);
  snap.狼人杀.一边倒 = { 最高票: top, 出局: out };
  if (top !== 3) bad.push("投票最高票应为 3，实为 " + top);
  if (String(out.join(",")) !== "2") bad.push("出局者应为 2，实为 " + out.join(","));
}
{
  setVar("玩家数", 4);
  setList("存活表", [1, 1, 1, 1]);       // 下标 k-1 = 玩家 k，1=存活
  setList("票箱", [2, 3, 2, 3]);        // A→B B→C C→B D→C  → B/C 各 2 票
  broadcast("统计票");
  await stepN(30);
  const top = num(getVar("最高票"));
  const out = (getList("出局表") || []).map(Number);
  snap.狼人杀.平票 = { 最高票: top, 出局: out };
  if (top !== 2) bad.push("平票最高票应为 2，实为 " + top);
  if (String(out.join(",")) !== "2,3") bad.push("平票候选应为 2,3，实为 " + out.join(","));
}

// ---------------------------------------------------------------- 5. 死人不能被投
{
  setVar("玩家数", 4);
  setList("存活表", [1, 0, 1, 1]);       // 2 号已出局
  setList("票箱", [2, 2, 3]);           // 两票投给已出局的 2
  broadcast("统计票");
  await stepN(30);
  const top = num(getVar("最高票"));
  const out = (getList("出局表") || []).map(Number);
  snap.狼人杀.已出局不计票 = { 最高票: top, 出局: out };
  if (top !== 1 || String(out.join(",")) !== "3")
    bad.push("已出局玩家不该计票：应最高 1 票 / 出局 3，实为 " + top + " / " + out.join(","));
}

// ---------------------------------------------------------------- 6. 狼人杀发牌（板子配置）
// 12 人标准场（预女猎白）：4 狼 + 4 民 + 预言家/女巫/猎人/白痴
{
  const POOL = [1, 1, 1, 1, 2, 2, 2, 2, 3, 4, 5, 6];
  const NAMES = { 1: "狼人", 2: "村民", 3: "预言家", 4: "女巫", 5: "猎人", 6: "白痴" };
  setList("板子池", POOL);
  broadcast("发牌");
  await stepN(50);
  const got = (getList("身份池") || []).map(Number);
  const cnt = {};
  for (const v of got) cnt[v] = (cnt[v] || 0) + 1;
  snap.发牌 = { 张数: got.length, 计数: cnt, 顺序: got };

  if (got.length !== 12) bad.push("发牌张数应为 12，实为 " + got.length);
  const want = { 1: 4, 2: 4, 3: 1, 4: 1, 5: 1, 6: 1 };
  for (const k of Object.keys(want)) {
    if ((cnt[k] || 0) !== want[k])
      bad.push("身份 " + NAMES[k] + " 应有 " + want[k] + " 张，实为 " + (cnt[k] || 0));
  }

  // 洗牌必须真的打乱：再发一次，两次顺序不该完全相同（相同概率 1/12!）
  broadcast("发牌");
  await stepN(50);
  const got2 = (getList("身份池") || []).map(Number);
  snap.发牌_第二次 = got2;
  if (String(got2.join(",")) === String(got.join(",")))
    bad.push("两次发牌顺序完全相同，洗牌可能没生效");
}

// ---------------------------------------------------------------- 7. 板子装载（逗号串 → 身份池）
// 板子表是「数据」不是「代码」（第三十三册 §320/§334）：
// 一个新板子只应该在 板子串表 里加一行，状态机一行都不用动。
//
// ⚠️ 索引约定：板子串表 / 板子名表 第 1 项是占位空串，所以「12人进阶场」= 第 6 项。
{
  setVar("当前板子", 6);                    // 6 = 12人进阶场（狼王守卫）
  broadcast("装载板子");
  await stepN(60);
  const pool = (getList("板子池") || []).map(Number);
  const cnt = {};
  for (const v of pool) cnt[v] = (cnt[v] || 0) + 1;
  snap.板子装载 = { 张数: pool.length, 计数: cnt };
  if (pool.length !== 12)
    bad.push("装载「12人进阶场」应有 12 张身份，实为 " + pool.length);
  const want = { 1: 3, 9: 1, 2: 4, 3: 1, 4: 1, 5: 1, 7: 1 };  // 3普狼+狼王+4民+预女猎守
  for (const k of Object.keys(want)) {
    if ((cnt[k] || 0) !== want[k])
      bad.push("12人进阶场 身份 " + k + " 应有 " + want[k] + " 张，实为 " + (cnt[k] || 0));
  }
}

// ---------------------------------------------------------------- 7b. 红狼（经典版）身份与板子
// 「红狼」是另一款游戏（狼人杀经典版），不是身份。见 references/werewolf-classic.md。
// 这里验证三件事：身份表总数、红狼专属身份的阵营/自爆标记、红狼板子能正确装载。
{
  const names = getList("身份名表") || [];
  const camps = (getList("阵营表") || []).map(Number);
  const boom = (getList("可自爆表") || []).map(Number);
  snap.身份表 = { 总数: names.length, 阵营表长: camps.length, 可自爆表长: boom.length };
  if (names.length !== 93)
    bad.push("身份名表应有 93 项（67 网易含 13 觉醒 + 26 红狼），实为 " + names.length);
  if (camps.length !== 93 || boom.length !== 93)
    bad.push("阵营表/可自爆表长度应与身份名表一致（93），实为 " +
             camps.length + "/" + boom.length);

  // 三张表必须逐位对齐：抽查几个关键编码
  const spot = { 1: ["狼人", 1, 1], 9: ["狼王", 1, 1], 11: ["狼美人", 1, 0],
                 20: ["厚皮狼", 3, 0], 79: ["机械狼", 1, 0], 82: ["红月使徒", 1, 1],
                 86: ["盗宝大师", 4, 0] };
  for (const k of Object.keys(spot)) {
    const [n, c, b] = spot[k];
    const got = [names[k - 1], camps[k - 1], boom[k - 1]];
    if (got[0] !== n || got[1] !== c || got[2] !== b)
      bad.push("身份 " + k + " 应为 " + n + "/" + c + "/" + b + "，实为 " + got.join("/"));
  }
  // 「红狼」不该出现在身份表里（它是游戏名）
  if (names.includes("红狼")) bad.push("身份表里不应有「红狼」——红狼是一款游戏，不是身份");
}
{
  // 红狼「机械狼」板子：4 民 + 3 狼 + 机械狼 + 通灵师/女巫/猎人/守卫
  setVar("当前板子", 13);
  broadcast("装载板子");
  await stepN(80);
  const pool = (getList("板子池") || []).map(Number);
  const cnt = {};
  for (const v of pool) cnt[v] = (cnt[v] || 0) + 1;
  snap.红狼_机械狼板 = { 张数: pool.length, 计数: cnt };
  if (pool.length !== 12) bad.push("机械狼板应有 12 张，实为 " + pool.length);
  const want = { 1: 3, 79: 1, 66: 1, 4: 1, 5: 1, 7: 1, 2: 4 };
  for (const k of Object.keys(want)) {
    if ((cnt[k] || 0) !== want[k])
      bad.push("机械狼板 身份 " + k + " 应为 " + want[k] + " 张，实为 " + (cnt[k] || 0));
  }
}
{
  // 红狼人数梯度：炸弹师 10 人 / 疯狂动物园 9 人
  for (const [idx, n, label] of [[18, 10, "炸弹师"], [19, 9, "疯狂动物园"]]) {
    setVar("当前板子", idx);
    broadcast("装载板子");
    await stepN(70);
    const len = (getList("板子池") || []).length;
    snap["红狼_" + label] = len;
    if (len !== n) bad.push(label + "板应有 " + n + " 张，实为 " + len);
  }
}

// ---------------------------------------------------------------- 8. 警长竞选（六种边界）
// ⚠️ 玩家编号 ↔ 数组下标：Scratch 列表从 1 开始，JS 数组从 0 开始。
//    统一约定「arr[k-1] = 玩家 k」，并用 arr() 生成，避免到处写 ±1。
const P = 12;
const arr = (n, fn) => Array.from({ length: n }, (_, i) => fn(i + 1));
const zerosOf = (n) => arr(n, () => 0);
const onesOf = (n) => arr(n, () => 1);

function resetSheriff() {
  setVar("玩家数", P);
  setList("上警表", zerosOf(P));
  setList("退水表", zerosOf(P));
  setList("存活表", onesOf(P));
  setList("竞选票箱", zerosOf(P));
  setList("竞选票箱PK", zerosOf(P));
  setList("并列表", [0]);
  setVar("候选数", 0);
  setVar("警长", 0);
  setVar("警徽状态", 0);
  setVar("竞选阶段", 0);
}
{
  // ① 无人上警 → 警徽流失（状态 7 必须显式存在，不能靠「警长=0」推断）
  resetSheriff();
  broadcast("竞选计票");
  await stepN(60);
  const st = num(getVar("警徽状态"));
  const ph = num(getVar("竞选阶段"));
  snap.竞选_无人上警 = { 警徽状态: st, 竞选阶段: ph, 候选数: num(getVar("候选数")) };
  if (st !== 2 || ph !== 7)
    bad.push("无人上警应「警徽流失(2)/阶段7」，实为 " + st + "/" + ph);
}
{
  // ② 只有 1 人上警 → 直接当选，跳过投票
  resetSheriff();
  const up = zerosOf(P); up[2] = 1;        // 玩家 3
  setList("上警表", up);
  broadcast("竞选计票");
  await stepN(60);
  const chief = num(getVar("警长"));
  snap.竞选_唯一候选 = { 警长: chief, 警徽状态: num(getVar("警徽状态")) };
  if (chief !== 3 || num(getVar("警徽状态")) !== 1)
    bad.push("唯一候选人应直接当选（警长=3/状态1），实为 " + chief + "/" + num(getVar("警徽状态")));
}
{
  // ③ 三人上警（2/5/8），得票 5:3 → 2 号当选
  resetSheriff();
  const up = zerosOf(P); up[1] = 1; up[4] = 1; up[7] = 1;   // 玩家 2/5/8
  setList("上警表", up);
  const box = zerosOf(P);
  // 投票人 1,3,4,6,7 投 2 号（上警的 2/5/8 没有票）
  box[0] = 2; box[2] = 2; box[3] = 2; box[5] = 2; box[6] = 2;
  // 投票人 9,10,11 投 5 号
  box[8] = 5; box[9] = 5; box[10] = 5;
  setList("竞选票箱", box);
  broadcast("竞选计票");
  await stepN(70);
  const chief = num(getVar("警长"));
  snap.竞选_得票最多 = { 警长: chief, 最高票: num(getVar("最高票")) };
  if (chief !== 2 || num(getVar("最高票")) !== 5)
    bad.push("得票最多者应 2 号(5票)，实为 " + chief + "(" + num(getVar("最高票")) + "票)");
}
{
  // ④ 平票 → 进入 PK（阶段 5），并列表 = 并列者
  resetSheriff();
  const up = zerosOf(P); up[1] = 1; up[4] = 1;             // 玩家 2/5
  setList("上警表", up);
  const box = zerosOf(P);
  box[0] = 2; box[2] = 2; box[3] = 2; box[5] = 2; box[6] = 2;      // 5 票给 2
  box[7] = 5; box[8] = 5; box[9] = 5; box[10] = 5; box[11] = 5;    // 5 票给 5
  setList("竞选票箱", box);
  broadcast("竞选计票");
  await stepN(80);
  const tieList = (getList("并列表") || []).map(Number).filter((x) => x > 0);
  snap.竞选_平票进PK = { 竞选阶段: num(getVar("竞选阶段")), 并列表: tieList };
  if (num(getVar("竞选阶段")) !== 5)
    bad.push("平票应进入 PK(阶段5)，实为 " + num(getVar("竞选阶段")));
  if (String(tieList.join(",")) !== "2,5")
    bad.push("PK 并列表应为 2,5，实为 " + tieList.join(","));

  // ⑤ PK 重投 4:3 → 2 号当选
  const pk = zerosOf(P);
  pk[0] = 2; pk[2] = 2; pk[3] = 2; pk[5] = 2;      // 投票人 1,3,4,6
  pk[6] = 5; pk[7] = 5; pk[8] = 5;                 // 投票人 7,8,9
  setList("竞选票箱PK", pk);
  broadcast("PK投票");
  await stepN(70);
  const chief = num(getVar("警长"));
  snap.竞选_PK结果 = { 警长: chief, 警徽状态: num(getVar("警徽状态")) };
  if (chief !== 2 || num(getVar("警徽状态")) !== 1)
    bad.push("PK 应决出警长 2 号(状态1)，实为 " + chief + "/" + num(getVar("警徽状态")));
}
{
  // ⑥ PK 再次平票 → 警徽流失（不再进行第二轮）
  resetSheriff();
  setList("上警表", arr(P, (k) => (k === 2 || k === 5 ? 1 : 0)));
  setList("并列表", [2, 5]);
  setVar("竞选阶段", 5);
  const pk = zerosOf(P);
  pk[0] = 2; pk[2] = 2; pk[3] = 2; pk[5] = 2;      // 4 票给 2
  pk[6] = 5; pk[7] = 5; pk[8] = 5; pk[9] = 5;      // 4 票给 5
  setList("竞选票箱PK", pk);
  broadcast("PK投票");
  await stepN(70);
  snap.竞选_PK再平 = { 警徽状态: num(getVar("警徽状态")), 竞选阶段: num(getVar("竞选阶段")) };
  if (num(getVar("警徽状态")) !== 2 || num(getVar("竞选阶段")) !== 7)
    bad.push("PK 再次平票应警徽流失(2/7)，实为 " +
             num(getVar("警徽状态")) + "/" + num(getVar("竞选阶段")));
}

// ---------------------------------------------------------------- 9. 警徽流（§337/§338）
// 核心语义：警徽交给谁 = 向全场宣布「那个人是金水」（预言家不会把 1.5 票送给查杀）。
function resetBadge() {
  setVar("玩家数", P);
  setList("存活表", onesOf(P));
  setVar("警长", 3);
  setVar("警徽状态", 1);
  setVar("流指针", 1);
  setVar("新警长", 0);
  setList("警徽流_验", [3, 7]);      // 第 1 顺位验 3 号，第 2 顺位验 7 号（按顺位排，不是玩家号索引）
  setList("警徽流_金", [7, 9]);      // 3 号金水 → 给 7；7 号金水 → 给 9
  setList("警徽流_杀", [0, 0]);      // 查杀 → 撕警徽
  setList("查验结果", zerosOf(P));   // 玩家号索引：1 金水 / 2 查杀 / 0 未查
}
{
  // 金水 → 警徽交给 7 号，流指针前进
  resetBadge();
  const chk = zerosOf(P); chk[2] = 1;   // 玩家 3 是金水
  setList("查验结果", chk);
  setVar("死者", 3);
  broadcast("警长死亡");
  await stepN(60);
  snap.警徽流_金水 = { 警长: num(getVar("警长")), 流指针: num(getVar("流指针")),
                       警徽状态: num(getVar("警徽状态")) };
  if (num(getVar("警长")) !== 7 || num(getVar("警徽状态")) !== 1)
    bad.push("金水应把警徽交给 7 号，实为 " + num(getVar("警长")));
  if (num(getVar("流指针")) !== 2)
    bad.push("警徽移交后流指针应前进到 2，实为 " + num(getVar("流指针")));
}
{
  // 查杀 → 去向 0 = 撕警徽（状态 3）
  resetBadge();
  const chk = zerosOf(P); chk[2] = 2;   // 玩家 3 是查杀
  setList("查验结果", chk);
  setVar("死者", 3);
  broadcast("警长死亡");
  await stepN(60);
  snap.警徽流_撕警徽 = { 警徽状态: num(getVar("警徽状态")), 结果: getVar("结果") };
  if (num(getVar("警徽状态")) !== 3)
    bad.push("查杀且去向为 0 应撕警徽(状态3)，实为 " + num(getVar("警徽状态")));
}
{
  // 接徽人已死 → 警徽流失（不能随机挑一个，玩家会发现警徽飞到陌生人手里）
  resetBadge();
  const chk = zerosOf(P); chk[2] = 1;
  setList("查验结果", chk);
  const alive = onesOf(P); alive[6] = 0;   // 玩家 7 已出局
  setList("存活表", alive);
  setVar("死者", 3);
  broadcast("警长死亡");
  await stepN(60);
  snap.警徽流_接徽人已死 = { 警徽状态: num(getVar("警徽状态")), 警长: num(getVar("警长")) };
  if (num(getVar("警徽状态")) !== 2 || num(getVar("警长")) !== 3)
    bad.push("接徽人已出局应警徽流失(2)且警长不变，实为 " +
             num(getVar("警徽状态")) + "/" + num(getVar("警长")));
}
{
  // 没留警徽流 → 信息随人消失
  resetBadge();
  setVar("流指针", 3);                 // 越界 = 没有更多顺位
  setVar("死者", 3);
  broadcast("警长死亡");
  await stepN(60);
  snap.警徽流_没留流 = { 警徽状态: num(getVar("警徽状态")), 结果: getVar("结果") };
  if (num(getVar("警徽状态")) !== 2)
    bad.push("没留警徽流应流失(2)，实为 " + num(getVar("警徽状态")));
}
{
  // 死者不是警长 → 不处理
  resetBadge();
  setVar("死者", 5);
  broadcast("警长死亡");
  await stepN(50);
  snap.警徽流_非警长 = { 警长: num(getVar("警长")), 警徽状态: num(getVar("警徽状态")) };
  if (num(getVar("警长")) !== 3 || num(getVar("警徽状态")) !== 1)
    bad.push("非警长死亡不应处理警徽，实为 " + num(getVar("警长")) + "/" + num(getVar("警徽状态")));
}

// ---------------------------------------------------------------- 10. 自爆与吞警徽（§339/§340）
function resetBoom(ids) {
  setVar("玩家数", P);
  setList("存活表", onesOf(P));
  setList("身份池", ids);
  setVar("竞选阶段", 4);
  setVar("竞选暂停次数", 0);
  setVar("双爆开关", 1);
  setVar("自爆数", 0);
  setVar("警徽状态", 1);
  setVar("警长", 0);
  setVar("昼夜", 0);
  setVar("白天阶段", 1);
  setVar("自爆者", 0);
}
const WOLVES = [1, 1, 1, 1, 2, 2, 2, 2, 3, 4, 5, 6];   // 1~4 号是狼
{
  // 双爆第一爆 → 竞选暂停（阶段 8），直接入夜
  resetBoom(WOLVES);
  setVar("自爆者", 1);
  broadcast("自爆");
  await stepN(60);
  const alive1 = (getList("存活表") || [])[0];
  snap.自爆_第一爆 = { 存活: num(alive1), 自爆数: num(getVar("自爆数")),
                       竞选阶段: num(getVar("竞选阶段")), 昼夜: num(getVar("昼夜")),
                       白天阶段: num(getVar("白天阶段")) };
  if (num(alive1) !== 0) bad.push("自爆者应出局，实为存活 " + num(alive1));
  if (num(getVar("竞选阶段")) !== 8)
    bad.push("双爆规则第一爆应暂停竞选(阶段8)，实为 " + num(getVar("竞选阶段")));
  if (num(getVar("昼夜")) !== 1 || num(getVar("白天阶段")) !== 0)
    bad.push("自爆后应直接入夜且中止白天，实为 昼夜=" + num(getVar("昼夜")) +
             " 白天阶段=" + num(getVar("白天阶段")));

  // 次日恢复竞选（阶段 8 → 4），第二爆才会被判定成「竞选期间」
  broadcast("恢复竞选");
  await stepN(40);
  snap.自爆_恢复竞选 = { 竞选阶段: num(getVar("竞选阶段")) };
  if (num(getVar("竞选阶段")) !== 4)
    bad.push("恢复竞选后阶段应回到 4，实为 " + num(getVar("竞选阶段")));

  // 第二爆 → 警徽流失
  setVar("自爆者", 2);
  broadcast("自爆");
  await stepN(60);
  snap.自爆_第二爆 = { 竞选阶段: num(getVar("竞选阶段")), 警徽状态: num(getVar("警徽状态")) };
  if (num(getVar("竞选阶段")) !== 7 || num(getVar("警徽状态")) !== 2)
    bad.push("双爆第二爆应警徽流失(阶段7/状态2)，实为 " +
             num(getVar("竞选阶段")) + "/" + num(getVar("警徽状态")));
}
{
  // 不可自爆的身份（狼美人=11）→ 拒绝，且人还活着
  resetBoom([1, 11, 1, 1, 2, 2, 2, 2, 3, 4, 5, 6]);   // 2 号是狼美人
  setVar("自爆者", 2);
  broadcast("自爆");
  await stepN(60);
  const alive2 = (getList("存活表") || [])[1];
  snap.自爆_不可自爆 = { 存活: num(alive2), 结果: getVar("结果") };
  if (num(alive2) !== 1) bad.push("狼美人不能自爆，却出局了");
  if (!String(getVar("结果")).includes("不能自爆"))
    bad.push("狼美人自爆应被拒绝，实为：" + getVar("结果"));
}
{
  // 单爆规则 → 第一次就吞掉警徽
  resetBoom(WOLVES);
  setVar("双爆开关", 0);
  setVar("自爆者", 3);
  broadcast("自爆");
  await stepN(60);
  snap.自爆_单爆规则 = { 竞选阶段: num(getVar("竞选阶段")), 警徽状态: num(getVar("警徽状态")) };
  if (num(getVar("竞选阶段")) !== 7 || num(getVar("警徽状态")) !== 2)
    bad.push("单爆规则应直接吞警徽(7/2)，实为 " +
             num(getVar("竞选阶段")) + "/" + num(getVar("警徽状态")));
}

// ---------------------------------------------------------------- 11. 屠边胜负（§344）
function judge(board, killed) {
  const n = board.length;
  setVar("人数", n);
  setList("身份池", board);                 // item k = 玩家 k 的身份
  const alive = onesOf(n);
  for (const k of killed || []) alive[k - 1] = 0;
  setList("存活表", alive);
  setVar("屠城开关", 0);
  broadcast("判胜负");
}
{
  const std = [1, 1, 1, 1, 2, 2, 2, 2, 3, 4, 5, 6];   // 12人标准场：4狼4民4神
  const kill = (pred) => std.map((v, i) => (pred(v) ? i + 1 : 0)).filter((x) => x > 0);

  await judge(std); await stepN(60);
  snap.胜负_开局 = { 胜负: getVar("胜负"), 存活狼: num(getVar("存活狼")),
                     存活神: num(getVar("存活神")), 存活民: num(getVar("存活民")) };
  if (getVar("胜负") !== "继续")
    bad.push("12人标准场开局应「继续」，实为 " + getVar("胜负"));

  await judge(std, kill((v) => v === 2)); await stepN(60);
  snap.胜负_屠民 = getVar("胜负");
  if (!String(getVar("胜负")).includes("屠民"))
    bad.push("杀光平民应「狼人胜·屠民」，实为 " + getVar("胜负"));

  await judge(std, kill((v) => v >= 3)); await stepN(60);
  snap.胜负_屠神 = getVar("胜负");
  if (!String(getVar("胜负")).includes("屠神"))
    bad.push("杀光神职应「狼人胜·屠神」，实为 " + getVar("胜负"));

  await judge(std, kill((v) => v === 1)); await stepN(60);
  snap.胜负_好人 = getVar("胜负");
  if (getVar("胜负") !== "好人胜")
    bad.push("杀光狼人应「好人胜」，实为 " + getVar("胜负"));
}
{
  // ⚠️ 无民板子（诸神黄昏：狼王+白狼王+恶灵骑士 + 5 神 + 0 民）
  //    存活民恒为 0，若没有「总民 > 0」守卫会开局就判狼人胜。
  const gods = [9, 10, 14, 3, 7, 4, 5, 6];
  await judge(gods); await stepN(60);
  snap.胜负_无民板子 = { 胜负: getVar("胜负"), 总民: num(getVar("总民")),
                         存活民: num(getVar("存活民")), 总神: num(getVar("总神")) };
  if (getVar("胜负") !== "继续")
    bad.push("无民板子开局应「继续」（屠民退化为屠城），实为 " + getVar("胜负"));
  if (num(getVar("总民")) !== 0)
    bad.push("无民板子的总民应为 0，实为 " + num(getVar("总民")));
}


// ---------------------------------------------------------------- 12. 觉醒体系：身份表与板子（第三十六册）
// ⚠️ 下标约定沿用前文：arr[k-1] = 玩家 k；身份编码 = names.indexOf(名字)+1。
{
  const names = getList("身份名表") || [];
  const camps = (getList("阵营表") || []).map(Number);
  const booms = (getList("可自爆表") || []).map(Number);
  const awakened = names.filter((x) => String(x).startsWith("觉醒"));
  snap.觉醒_身份表 = { 身份数: names.length, 觉醒角色: awakened };
  if (names.length !== 93)
    bad.push("身份表应为 93 个（含 13 觉醒），实为 " + names.length);
  if (camps.length !== names.length || booms.length !== names.length)
    bad.push("身份三表长度不一致：" + names.length + "/" + camps.length + "/" + booms.length);
  if (awakened.length !== 13)
    bad.push("官方觉醒系列应为 13 个，实为 " + awakened.length + " → " + awakened.join(","));
  // 逐位对齐抽检：觉醒骑士=好人神职(2)不可自爆，觉醒白狼王=狼(1)可自爆
  const iK = names.indexOf("觉醒骑士");
  const iW = names.indexOf("觉醒白狼王");
  if (iK < 0 || camps[iK] !== 2 || booms[iK] !== 0)
    bad.push("觉醒骑士的阵营/可自爆位表错位");
  if (iW < 0 || camps[iW] !== 1 || booms[iW] !== 1)
    bad.push("觉醒白狼王的阵营/可自爆位表错位");
}
{
  // 板子 29 = 12 人月坠光渊（Scratch 1-based；JS 数组下标 28）
  setVar("当前板子", 29);
  broadcast("装载板子"); await stepN(80);
  const pool = (getList("板子池") || []).map(Number);
  snap.觉醒_月坠光渊 = { 张数: pool.length, 身份: pool };
  if (pool.length !== 12) bad.push("月坠光渊12 应 12 张，实为 " + pool.length);
  if (!pool.includes(60) || !pool.includes(56))
    bad.push("月坠光渊12 必须同时含觉醒白狼王(60)与觉醒守卫(56)");
}
{
  // 板子 32 = 云端追踪12：无民板子（Scratch 1-based）
  setVar("当前板子", 32);
  broadcast("装载板子"); await stepN(80);
  const pool = (getList("板子池") || []).map(Number);
  const nMin = (getList("阵营表") || []).length
    ? pool.filter((v) => Number((getList("阵营表") || [])[v - 1]) === 3).length : -1;
  snap.觉醒_云端追踪 = { 张数: pool.length, 民数: nMin };
  if (pool.length !== 12) bad.push("云端追踪12 应 12 张，实为 " + pool.length);
  if (nMin !== 0) bad.push("云端追踪12 是无民板子，民数应为 0，实为 " + nMin);
  // 无民板子开局不能误判狼人胜
  setVar("人数", 12);
  setList("身份池", pool);
  setList("存活表", Array.from({ length: 12 }, () => 1));
  setVar("屠城开关", 0);
  broadcast("判胜负"); await stepN(80);
  if (getVar("胜负") !== "继续")
    bad.push("无民觉醒板子开局应「继续」，实为 " + getVar("胜负"));
}
{
  // 板子 35 = 月坠光渊10（同一板子按人数分档，女巫自救档不同）
  setVar("当前板子", 35);
  broadcast("装载板子"); await stepN(80);
  const pool = (getList("板子池") || []).map(Number);
  snap.觉醒_月坠光渊10 = { 张数: pool.length };
  if (pool.length !== 10) bad.push("月坠光渊10 应 10 张，实为 " + pool.length);
}

// ---------------------------------------------------------------- 13. 集合查验（§396）
const AW_N = 12;
const AW_A = (n, fn) => Array.from({ length: n }, (_, i) => fn(i + 1));
const AW_Z = (n) => AW_A(n, () => 0);
function resetAwaken() {
  setVar("人数", AW_N);
  setVar("自动帧", 0);
  setList("存活表", AW_A(AW_N, () => 1));
  setList("现阵营表", AW_Z(AW_N));
  setList("身份池", AW_Z(AW_N));
  setList("狼王爪持有", AW_Z(AW_N));
  setList("协助过表", AW_Z(AW_N));
  setList("决斗已用", AW_Z(AW_N));
  setList("免疫夜伤", AW_Z(AW_N));
}
{
  resetAwaken();
  const camp = AW_Z(AW_N); camp[0] = 1; camp[1] = 1; camp[2] = 1;  // 玩家 1/2/3 是狼
  setList("现阵营表", camp);
  const check = async (a, b) => {
    setVar("验A", a); setVar("验B", b);
    broadcast("觉醒查验"); await stepN(50);
    return num(getVar("集合验果"));
  };
  const r1 = await check(4, 5);   // 两个好人
  const r2 = await check(2, 6);   // 一狼一好人
  const r3 = await check(3, 3);   // 同一个人
  snap.觉醒_集合查验 = { 好好: r1, 狼好: r2, 同一人: r3 };
  if (r1 !== 0) bad.push("两个好人应返回 0（无狼），实为 " + r1);
  if (r2 !== 1) bad.push("含一狼应返回 1（有狼），实为 " + r2);
  if (r3 !== -1) bad.push("同一目标应判非法(-1)，实为 " + r3);
}

// ---------------------------------------------------------------- 14. 觉醒女巫协助者投票（§396）
{
  const rp = () => {
    resetAwaken();
    setVar("毒药次数", 0);
    setVar("毒目标", 9);
    setList("协助者表", []);
    setList("协助票箱", []);
  };
  const vote = async (helpers, votes) => {
    setList("协助者表", helpers);
    setList("协助票箱", votes);
    broadcast("毒药调配"); await stepN(140);
    return { ok: num(getVar("协助生效")), times: num(getVar("毒药次数")) };
  };

  rp();
  let v = await vote([3], [1]);                       // 第 1 次需 1 人，全票
  snap.觉醒_毒药_首次 = v;
  if (v.ok !== 1 || v.times !== 1)
    bad.push("第 1 次毒药 1 名协助者全票应生效且次数=1，实为 " + JSON.stringify(v));
  if (num((getList("协助过表") || [])[2]) !== 1)
    bad.push("协助者 3 号应被标记「已协助」");

  v = await vote([3, 4], [1, 1]);                    // 3 号已协助过 → 拒绝
  snap.觉醒_毒药_重复协助 = v;
  if (v.ok !== 0 || v.times !== 1)
    bad.push("已协助过的玩家不得再协助，实为 " + JSON.stringify(v));

  v = await vote([4], [1]);                          // 第 2 次需 2 人，人数不足 → -2
  snap.觉醒_毒药_人数不符 = v;
  if (v.ok !== -2) bad.push("第 2 次毒药需 2 名协助者，实为 " + JSON.stringify(v));

  v = await vote([4, 5], [1, 0]);                    // 有反对票 → 不生效，次数不增
  snap.觉醒_毒药_反对票 = v;
  if (v.ok !== 0 || v.times !== 1)
    bad.push("有 1 张反对票应不生效且次数不增加，实为 " + JSON.stringify(v));

  v = await vote([4, 5], [1, 1]);                    // 全票 → 第 2 次生效
  if (v.ok !== 1 || v.times !== 2)
    bad.push("第 2 次毒药全票应生效且次数=2，实为 " + JSON.stringify(v));

  v = await vote([6, 6, 8], [1, 1, 1]);              // 第 3 次需 3 人，有重复 → 拒绝
  snap.觉醒_毒药_协助者重复 = v;
  if (v.ok !== 0 || v.times !== 2)
    bad.push("协助者重复应被拒绝且不增加次数，实为 " + JSON.stringify(v));

  v = await vote([9, 7, 8], [1, 1, 1]);              // 协助者是毒目标本人 → 拒绝
  snap.觉醒_毒药_目标本人 = v;
  if (v.ok !== 0) bad.push("毒目标本人不能当协助者，实为 " + JSON.stringify(v));

  v = await vote([6, 7, 8], [1, 1, 1]);              // 合法第 3 次
  if (v.ok !== 1 || v.times !== 3)
    bad.push("第 3 次毒药 3 名协助者全票应生效，实为 " + JSON.stringify(v));

  v = await vote([1, 2, 3, 4], [1, 1, 1, 1]);        // 第 4 次 → -1
  snap.觉醒_毒药_超次 = v;
  if (v.ok !== -1) bad.push("毒药一局最多 3 次，第 4 次应返回 -1，实为 " + JSON.stringify(v));
}

// ---------------------------------------------------------------- 15. 狼王爪：转移 + 守恒 + 最后一狼禁用（§400）
{
  resetAwaken();
  const claws = AW_Z(AW_N); claws[0] = 2;            // 玩家 1 持 2 爪
  setList("狼王爪持有", claws);
  const camp = AW_Z(AW_N); camp[0] = 1; camp[1] = 1; camp[2] = 1;
  setList("现阵营表", camp);
  setVar("亲传者", 1); setVar("接爪者", 2); setVar("亲传已用", 0);
  broadcast("亲传"); await stepN(90);
  const c2 = (getList("狼王爪持有") || []).map(Number);
  snap.觉醒_亲传 = { 原持有: num(c2[0]), 接爪者: num(c2[1]),
                     守恒: num(getVar("爪守恒")), 结果: getVar("亲传结果") };
  if (num(c2[0]) !== 1 || num(c2[1]) !== 1)
    bad.push("亲传是转移不是复制：应 1/1，实为 " + c2[0] + "/" + c2[1]);
  if (num(getVar("爪守恒")) !== 2)
    bad.push("狼王爪全局守恒应恒为 2，实为 " + getVar("爪守恒"));

  // 第二次亲传 → 被拒（亲传已用）
  setVar("接爪者", 3);
  broadcast("亲传"); await stepN(90);
  if (String(getVar("亲传结果")).includes("已亲传"))
    bad.push("一局只能亲传一次，第二次应被拒绝");

  // 传给非狼 → 被拒
  setVar("亲传已用", 0); setVar("接爪者", 5);   // 玩家 5 现阵营=0（好人侧）
  broadcast("亲传"); await stepN(90);
  if (String(getVar("亲传结果")).includes("已亲传"))
    bad.push("狼王爪不能亲传给非狼人");

  // 最后一狼 → 不能发动
  setVar("爪出局者", 1); setVar("存活狼", 1);
  broadcast("爪结算"); await stepN(50);
  snap.觉醒_爪_最后一狼 = num(getVar("可发动爪"));
  if (num(getVar("可发动爪")) !== 0)
    bad.push("最后一狼出局不能发动狼王爪，实为可发动 " + getVar("可发动爪"));

  // 还有别的狼 → 可发动 1 次
  setVar("存活狼", 2);
  broadcast("爪结算"); await stepN(50);
  snap.觉醒_爪_正常发动 = num(getVar("可发动爪"));
  if (num(getVar("可发动爪")) !== 1)
    bad.push("玩家 1 持 1 爪且仍有别的狼 → 应发动 1 次，实为 " + getVar("可发动爪"));
}

// ---------------------------------------------------------------- 16. 觉醒孤独少女：死因分叉 + 结算优先（§403）
{
  // 构造「无狼」局面，先跑完胜负结算，再让偶像出局
  resetAwaken();
  const ids = AW_A(AW_N, () => 2); ids[0] = 91; ids[1] = 3;   // 1=觉醒孤独少女 2=偶像(预言家)
  setList("身份池", ids);
  const camp = AW_Z(AW_N); camp[0] = 4; camp[1] = 2;
  setList("现阵营表", camp);
  setVar("人数", AW_N);
  setVar("屠城开关", 0);
  broadcast("判胜负"); await stepN(90);
  const before = getVar("胜负");
  setVar("觉醒者", 1); setVar("偶像", 2); setVar("偶像死因", 2);  // 放逐
  broadcast("偶像出局"); await stepN(60);
  const st1 = num(getVar("变身状态"));
  const campAfter = (getList("现阵营表") || []).map(Number);
  const idAfter = (getList("身份池") || []).map(Number);
  snap.觉醒_偶像被放逐 = { 变身前胜负: before, 快照: getVar("变身前胜负"),
                           状态: st1, 现阵营: num(campAfter[0]), 身份: num(idAfter[0]) };
  if (getVar("变身前胜负") !== before)
    bad.push("结算优先于变身：变身前胜负快照应 = 判胜负结果 " + before +
             "，实为 " + getVar("变身前胜负"));
  if (st1 !== 1 || num(campAfter[0]) !== 1)
    bad.push("偶像被放逐应变身为狼（状态1/现阵营1），实为 " + st1 + "/" + campAfter[0]);
  if (num(idAfter[0]) !== 91)
    bad.push("变狼不应改写身份池（仍是觉醒孤独少女），实为 " + idAfter[0]);

  // 非放逐死因 → 继承偶像身份与阵营
  resetAwaken();
  setList("身份池", ids);
  setList("现阵营表", camp);
  setVar("觉醒者", 1); setVar("偶像", 2); setVar("偶像死因", 3);  // 毒
  broadcast("偶像出局"); await stepN(60);
  const id2 = (getList("身份池") || []).map(Number);
  const camp2 = (getList("现阵营表") || []).map(Number);
  snap.觉醒_偶像被毒 = { 状态: num(getVar("变身状态")),
                         继承身份: num(getVar("继承身份")), 身份池: num(id2[0]), 现阵营: num(camp2[0]) };
  if (num(getVar("变身状态")) !== 2 || num(id2[0]) !== 3 || num(camp2[0]) !== 2)
    bad.push("偶像非放逐出局应继承预言家(3/阵营2)，实为 " +
             getVar("变身状态") + "/" + id2[0] + "/" + camp2[0]);
}

// ---------------------------------------------------------------- 17. 梦语出局走技能通道（§399）
{
  resetAwaken();
  const imm = AW_Z(AW_N); imm[3] = 1;      // 玩家 4 免疫夜间伤害
  setList("免疫夜伤", imm);
  setVar("夜数", 2); setVar("梦语者", 4); setVar("上夜梦语者", 0); setVar("梦语指令", 1);
  broadcast("梦语结算"); await stepN(50);
  const alive4 = num((getList("存活表") || [])[3]);
  snap.觉醒_梦语生效 = { 存活: alive4, 结果: getVar("结果") };
  if (alive4 !== 0)
    bad.push("梦语出局是技能通道，不能被自己的「免疫夜伤」挡掉");
  if (!String(getVar("结果")).includes("梦语出局生效"))
    bad.push("梦语结算结果异常：" + getVar("结果"));

  resetAwaken();
  setVar("夜数", 3); setVar("梦语者", 4); setVar("上夜梦语者", 4); setVar("梦语指令", 1);
  broadcast("梦语结算"); await stepN(50);
  snap.觉醒_梦语连选 = { 存活: num((getList("存活表") || [])[3]), 结果: getVar("结果") };
  if (!String(getVar("结果")).includes("非法") ||
      num((getList("存活表") || [])[3]) !== 1)
    bad.push("连续两晚梦语同一目标应判非法且不出局");

  setVar("夜数", 1); setVar("上夜梦语者", 0);
  broadcast("梦语结算"); await stepN(50);
  if (String(getVar("结果")).includes("梦语出局生效"))
    bad.push("首夜不能主动梦语出局（官方：从第二夜开始）");
}

// ---------------------------------------------------------------- 18. 觉醒骑士决斗（§398）
{
  resetAwaken();
  const camp = AW_Z(AW_N); camp[0] = 1; camp[5] = 2;   // 玩家1=狼，玩家6=好人
  setList("现阵营表", camp);
  setVar("决斗者", 5);

  setVar("决斗目标", 1);
  broadcast("决斗"); await stepN(60);
  const a1 = (getList("存活表") || []).map(Number);
  snap.觉醒_决斗到狼 = { 狼存活: num(a1[0]), 骑士存活: num(a1[4]),
                         继续白天: num(getVar("白天继续")), 结果: getVar("决斗结果") };
  if (num(a1[0]) !== 0 || num(a1[4]) !== 1 || num(getVar("白天继续")) !== 0)
    bad.push("决斗到狼：狼出局、骑士存活、应可连击（白天继续=0）");

  broadcast("决斗"); await stepN(60);
  if (!String(getVar("决斗结果")).includes("只能被决斗一次"))
    bad.push("每名玩家只能被决斗一次，重复决斗应被拒绝");

  setVar("决斗目标", 6);
  broadcast("决斗"); await stepN(60);
  const a2 = (getList("存活表") || []).map(Number);
  snap.觉醒_决斗到好人 = { 目标存活: num(a2[5]), 骑士存活: num(a2[4]),
                           继续白天: num(getVar("白天继续")) };
  if (num(a2[5]) !== 0 || num(a2[4]) !== 0)
    bad.push("决斗到好人：双方应同时出局");
  if (num(getVar("白天继续")) !== 1)
    bad.push("决斗到好人应继续原本白天发言流程，不是入夜");
}


// ---------------------------------------------------------------- 19. 新月事件卡：卡库与板子（第三十七册）
{
  const names = getList("事件名表") || [];
  const times = (getList("事件时效表") || []).map(Number);
  const types = (getList("事件类型表") || []).map(Number);
  const votes = (getList("事件票权表") || []).map(Number);
  snap.新月_卡库 = { 张数: names.length, 卡名: names,
                     满月: times.filter((x) => x === 1).length,
                     条件: times.filter((x) => x === 2).length,
                     永久: times.filter((x) => x === 3).length };
  if (names.length !== 10)
    bad.push("示教卡库应 10 张，实为 " + names.length);
  if (times.length !== 10 || types.length !== 10 || votes.length !== 10)
    bad.push("卡库四张表长度不一致");
  // ★ 卡库无前导占位：Scratch item 1 就应该是「奇迹」
  if (names[0] !== "奇迹")
    bad.push("卡库第 1 项应为「奇迹」（无占位），实为 " + names[0]);
}
{
  // 板子 37 = 12 人新月降临（Scratch 1-based，JS 数组下标 36）
  setVar("当前板子", 37);
  broadcast("装载板子"); await stepN(80);
  const pool = (getList("板子池") || []).map(Number);
  const cnt = {};
  for (const v of pool) cnt[v] = (cnt[v] || 0) + 1;
  snap.新月_板子 = { 张数: pool.length, 计数: cnt };
  if (pool.length !== 12) bad.push("12人新月降临应 12 张，实为 " + pool.length);
  const want = { 1: 4, 2: 4, 3: 1, 4: 1, 5: 1, 6: 1 };  // 4狼4民 预女猎愚
  for (const k of Object.keys(want))
    if ((cnt[k] || 0) !== want[k])
      bad.push("12人新月降临 身份 " + k + " 应 " + want[k] + " 张，实为 " + (cnt[k] || 0));
}

// ---------------------------------------------------------------- 20. 抽卡：一局一次 + 种子可复现
const MOON_IDS = [1, 1, 1, 1, 3, 4, 5, 6, 2, 2, 2, 2];  // 12人新月降临
const resetMoon = async (seed) => {
  broadcast("新局初始化"); await stepN(160);
  setVar("种子", seed === undefined ? 1 : seed);
  setVar("人数", 12);
  setList("身份池", MOON_IDS.slice());
  setList("存活表", Array.from({ length: 12 }, () => 1));
  setVar("存活好人", 8);
};
{
  await resetMoon(1);
  broadcast("抽新月卡"); await stepN(100);
  const ev1 = num(getVar("当前事件"));
  const d1 = num(getVar("栈深"));
  snap.新月_首次抽卡 = { 事件: ev1, 卡名: (getList("事件名表") || [])[ev1 - 1],
                         栈深: d1, 结果: getVar("抽卡结果") };
  if (ev1 < 1 || ev1 > 10) bad.push("抽到的事件 ID 越界：" + ev1);
  if (d1 !== 1) bad.push("抽卡后活动栈应有 1 条，实为 " + d1);

  // 一局仅一次：第二次抽卡必须被拒，栈深不变
  broadcast("抽新月卡"); await stepN(80);
  snap.新月_重复抽卡 = { 结果: getVar("抽卡结果"), 栈深: num(getVar("栈深")) };
  if (!String(getVar("抽卡结果")).includes("一局仅一次") || num(getVar("栈深")) !== 1)
    bad.push("新月降临一局只能抽 1 次，重复抽卡应被拒绝且栈深不变");

  // 白天的「重置」不能清掉整局事件状态
  broadcast("重置"); await stepN(30);
  broadcast("抽新月卡"); await stepN(60);
  if (!String(getVar("抽卡结果")).includes("一局仅一次"))
    bad.push("白天流程重置不得清空「事件已触发」（否则第二天会再抽一张）");

  // 固定种子可复现；换种子能抽到不同卡
  await resetMoon(1);
  broadcast("抽新月卡"); await stepN(100);
  const evA = num(getVar("当前事件"));
  await resetMoon(1);
  broadcast("抽新月卡"); await stepN(100);
  const evB = num(getVar("当前事件"));
  await resetMoon(7);
  broadcast("抽新月卡"); await stepN(100);
  const evC = num(getVar("当前事件"));
  snap.新月_种子 = { 种子1复现: evA + "/" + evB, 种子7: evC, 事件1: ev1 };
  if (evA !== evB) bad.push("同一种子应抽到同一张卡（不可复现会让校验假红）");
  if (ev1 !== evA) bad.push("初始种子 1 的抽卡结果不一致");
  if (evC === evA) bad.push("不同种子应能抽到不同事件");
}

// ---------------------------------------------------------------- 21. 三类时效：阶段末清理
{
  const Z12 = () => Array.from({ length: 12 }, () => 0);
  const setup = (expires, day) => {
    const stack = Z12(), tm = Z12(), due = Z12(), st = Z12();
    stack[0] = 1; stack[1] = 2; stack[2] = 3;              // 奇迹/群情激奋/葬礼
    tm[0] = 1; tm[1] = 2; tm[2] = 3;                       // 满月/新月/暗月
    due[0] = expires; due[1] = expires; due[2] = 0;
    st[0] = 1; st[1] = 1; st[2] = 1;
    setList("活动栈", stack); setList("栈时效", tm);
    setList("栈到期", due); setList("栈状态", st);
    setVar("栈深", 3); setVar("天数", day);
  };
  setup(1, 2);
  broadcast("事件推进"); await stepN(120);
  let st = (getList("栈状态") || []).map(Number);
  snap.新月_时效清理 = { 满月: st[0], 条件卡超时: st[1], 永久: st[2] };
  if (num(st[0]) !== 3) bad.push("满月卡应在当回合末被卸载");
  if (num(st[1]) !== 3) bad.push("条件触发卡超时后应作废（防栈泄漏）");
  if (num(st[2]) !== 1) bad.push("★ 暗月/永久卡绝不能被回合末清理，实为 " + st[2]);

  setup(5, 2);
  broadcast("事件推进"); await stepN(120);
  st = (getList("栈状态") || []).map(Number);
  snap.新月_条件未超时 = { 满月: st[0], 条件卡: st[1], 永久: st[2] };
  if (num(st[1]) !== 1) bad.push("条件卡未超时不应被清除");
}

// ---------------------------------------------------------------- 22. 快照栈：先撤销者不抹掉后者的效果（§428）
{
  await resetMoon(1);
  const Z12 = () => Array.from({ length: 12 }, () => 0);
  const stack = Z12(), snapv = Z12(), st = Z12();
  stack[0] = 6; stack[1] = 10;          // 快乐星球(票权2) → 惊人的不信任(票权3)
  snapv[0] = 1; snapv[1] = 2;           // 各自挂载前的票权原值
  st[0] = 1; st[1] = 1;
  setList("活动栈", stack); setList("栈快照", snapv); setList("栈状态", st);
  setVar("栈深", 2); setVar("票权开关", 3); setVar("快照顶", 2);

  // 先撤销 A（非栈顶）→ 只打标记，票权不能被抹掉
  setVar("撤销槽", 1);
  broadcast("事件撤销"); await stepN(120);
  snap.新月_非栈顶撤销 = { 票权: num(getVar("票权开关")),
                           快照顶: num(getVar("快照顶")), 结果: getVar("撤销结果") };
  if (num(getVar("票权开关")) !== 3)
    bad.push("非栈顶事件撤销不得改动开关（否则抹掉后挂载事件的效果）");
  if (num(getVar("快照顶")) !== 2)
    bad.push("非栈顶撤销后快照顶应仍是 2，实为 " + getVar("快照顶"));

  // 再撤销 B（栈顶）→ 恢复 B 的快照 = 2，而不是默认值 1
  setVar("撤销槽", 2);
  broadcast("事件撤销"); await stepN(120);
  snap.新月_栈顶撤销 = { 票权: num(getVar("票权开关")),
                         快照顶: num(getVar("快照顶")), 结果: getVar("撤销结果") };
  if (num(getVar("票权开关")) !== 2)
    bad.push("栈顶撤销应按快照恢复为 2（不是默认值 1），实为 " + getVar("票权开关"));
  if (num(getVar("快照顶")) !== 0)
    bad.push("全部生效事件撤销后快照顶应归 0，实为 " + getVar("快照顶"));

  setVar("撤销槽", 2);
  broadcast("事件撤销"); await stepN(80);
  if (!String(getVar("撤销结果")).includes("已撤销"))
    bad.push("重复撤销同一槽位应被拒绝");
}

// ---------------------------------------------------------------- 23. 结算类事件：额外胜负条件（§423）
{
  // 种子 42 → 事件 5「到点下班」（条件触发，第 3 天末）
  await resetMoon(42);
  broadcast("抽新月卡"); await stepN(100);
  const ev = num(getVar("当前事件"));
  snap.新月_到点下班事件 = { ID: ev, 卡名: (getList("事件名表") || [])[ev - 1] };
  if (ev !== 5) bad.push("种子 42 应抽到事件 5「到点下班」，实为 " + ev);

  setVar("天数", 2);
  broadcast("事件判胜负"); await stepN(140);
  if (getVar("事件胜负") !== "无")
    bad.push("第 2 天不应触发到点下班，实为 " + getVar("事件胜负"));

  setVar("天数", 3);
  broadcast("事件判胜负"); await stepN(140);
  snap.新月_到点下班 = { 天数: num(getVar("天数")), 胜负: getVar("事件胜负") };
  if (getVar("事件胜负") !== "好人胜·到点下班")
    bad.push("第 3 天结束且有好人存活应「好人胜·到点下班」，实为 " + getVar("事件胜负"));

  setVar("存活好人", 0);
  broadcast("事件判胜负"); await stepN(140);
  if (getVar("事件胜负") !== "无")
    bad.push("好人全部出局时到点下班不应触发");
}
{
  // 种子 9 → 事件 4「盲目之眼」：预言家出局则狼人直接获胜
  await resetMoon(9);
  broadcast("抽新月卡"); await stepN(100);
  const ev = num(getVar("当前事件"));
  if (ev !== 4) bad.push("种子 9 应抽到事件 4「盲目之眼」，实为 " + ev);

  broadcast("事件判胜负"); await stepN(140);
  snap.新月_盲目之眼_预存活 = { 预言家座位: num(getVar("预言家座位")),
                                胜负: getVar("事件胜负") };
  if (getVar("事件胜负") !== "无")
    bad.push("预言家存活时不应触发盲目之眼，实为 " + getVar("事件胜负"));
  if (num(getVar("预言家座位")) !== 5)
    bad.push("预言家应按身份池实时查座位（应为 5），实为 " + getVar("预言家座位"));

  const alive = Array.from({ length: 12 }, () => 1); alive[4] = 0;
  setList("存活表", alive);
  broadcast("事件判胜负"); await stepN(140);
  snap.新月_盲目之眼 = { 胜负: getVar("事件胜负") };
  if (getVar("事件胜负") !== "狼人胜·盲目之眼")
    bad.push("预言家出局应「狼人胜·盲目之眼」，实为 " + getVar("事件胜负"));

  // 星体转移：把预言家身份挪到 8 号，8 号出局仍应判狼人胜（不能写死座位）
  const moved = MOON_IDS.slice();
  moved[4] = 2; moved[7] = 3;                  // 5 号变民，8 号变预言家
  setList("身份池", moved);
  const alive2 = Array.from({ length: 12 }, () => 1); alive2[7] = 0;
  setList("存活表", alive2);
  broadcast("事件判胜负"); await stepN(140);
  snap.新月_星体转移 = { 预言家座位: num(getVar("预言家座位")), 胜负: getVar("事件胜负") };
  if (num(getVar("预言家座位")) !== 8 || getVar("事件胜负") !== "狼人胜·盲目之眼")
    bad.push("身份互换后应按新座位查预言家，实为 座位=" +
             getVar("预言家座位") + " / " + getVar("事件胜负"));

  // 事件胜负是「额外条件」，不能吞掉原有屠边判定
  setVar("人数", 12);
  setList("身份池", MOON_IDS.slice());
  setList("存活表", Array.from({ length: 12 }, () => 1));
  setVar("屠城开关", 0);
  broadcast("判胜负"); await stepN(100);
  if (getVar("胜负") !== "继续")
    bad.push("结算类事件不应影响通用屠边引擎，实为 " + getVar("胜负"));
}

// ---------------------------------------------------------------- 结果
const pass = bad.length === 0;
console.log(JSON.stringify(snap, null, 2));
if (pass) {
  console.log("CARD_LOGIC_OK  桌游判定全部正确（牌型/UNO/板子/红狼/竞选/警徽流/自爆/屠边/觉醒/新月）");
  process.exit(0);
} else {
  console.log("CARD_LOGIC_FAIL");
  for (const b of bad) console.log("  ✗ " + b);
  process.exit(1);
}
