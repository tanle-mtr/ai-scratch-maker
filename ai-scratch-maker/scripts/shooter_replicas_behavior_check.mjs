// 四款射击/摸金复刻引擎行为校验（第四十册 §479–§502）
// 用法: node shooter_replicas_behavior_check.mjs <shooter_replicas.sb3>
//
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

vm.greenFlag();
await stepN(3);
setVar("自动帧", 0);
await stepN(2);

function reset(mode = 1) {
  setVar("自动帧", 0); setVar("模式", mode);
  setVar("射线起点X", 0); setVar("射线起点Y", 0);
  setVar("射线方向X", 1); setVar("射线方向Y", 0);
  setVar("射线最大距", 2000);
  setVar("目标X", 500); setVar("目标Y", 0); setVar("目标半径", 30);
  setVar("墙体t", -1); setVar("穿墙系数", 1);
  setVar("基础伤害", 36); setVar("目标血量", 100); setVar("目标护甲", 0);
  setVar("护甲等级", 0); setVar("弹药穿透", 0); setVar("头盔", 0);
  setVar("信号值", 100); setVar("血量", 100);
  setVar("命中", 0); setVar("命中部位", 0); setVar("实际伤害", 0);
  setVar("金钱", 800); setVar("连败档", 0); setVar("回合", 1);
  setVar("回合结果", 0); setVar("击杀武器", 0); setVar("下包", 0);
  setVar("C4状态", 0); setVar("回合计时", 115); setVar("半场", 0);
  setVar("圈阶段", 0); setVar("当前半径", 1000);
  setVar("圈中心X", 0); setVar("圈中心Y", 0);
  setVar("玩家X", 0); setVar("玩家Y", 0);
  setVar("圈外倒计时", 180); setVar("淘汰", 0);
  setVar("仓库价值", 0); setVar("背包价值", 0); setVar("安全箱价值", 0);
  setVar("带入价值", 0); setVar("目标金额", 10000); setVar("已入柜价值", 0);
  setVar("撤离点开放", 0); setVar("撤离前置", 0); setVar("撤离读条", 0);
  setVar("撤离需读秒", 8); setVar("撤离成功", 0); setVar("受击打断", 0);
  setVar("负重", 0); setVar("负重上限", 100); setVar("移速系数", 1);
  setVar("危险指数", 0); setVar("局内分钟", 0); setVar("龙珠", 0);
  setVar("种子", 1); setVar("难度系数", 1); setVar("dt", 0.033);
  setVar("连发数", 0); setVar("移动速度", 0);
  setVar("蹲下", 0); setVar("开镜", 0); setVar("急停", 0);
  setVar("怪物距离", 100); setVar("怪物视距", 300);
  setVar("声波半径", 0); setVar("门开", 1);
  setVar("玩家高度", 0); setVar("怪物高度", 0); setVar("怪物状态", 0);
}
const fire = async (extra = {}) => {
  for (const [k, v] of Object.entries(extra)) setVar(k, v);
  broadcast("开火"); await stepN(150);
  return { 命中: num(getVar("命中")), 部位: num(getVar("命中部位")),
           t: num(getVar("入射t")), 伤害: num(getVar("实际伤害")),
           血: num(getVar("目标血量")), 掩体: num(getVar("掩体系数")) };
};

// ---------------------------------------------------------------- 1. 模式表（§496）
{
  const rows = [];
  for (const m of [1, 2, 3, 4]) {
    reset(m);
    broadcast("设模式"); await stepN(100);
    rows.push({ 模式: m, 金钱: num(getVar("金钱")), 信号: num(getVar("信号值")),
                目标金额: num(getVar("目标金额")), 仓库: num(getVar("仓库价值")),
                护甲等级: num(getVar("护甲等级")), 半径: num(getVar("当前半径")) });
  }
  snap.模式表 = rows;
  if (rows[0].金钱 !== 800) bad.push("CS2 起始金钱应 $800");
  if (rows[1].信号 !== 100 || rows[1].半径 !== 1000) bad.push("和平精英初始信号值/圈半径错");
  if (rows[2].护甲等级 !== 3) bad.push("三角洲初始护甲等级应为 3（示意）");
  if (rows[3].目标金额 !== 10000) bad.push("超自然浅层目标金额应 10000");
}

// ---------------------------------------------------------------- 2. 射线 / 命中（§481）
{
  reset(1);
  let r = await fire();
  snap.射线命中 = r;
  if (r.命中 !== 1 || Math.abs(r.t - 470) > 0.01)
    bad.push("hitscan 应从 0 沿 +x 命中 (500,0,r30)，入射 t=470，实为 " + JSON.stringify(r));
  if (r.部位 !== 3) bad.push("命中点居中应判胸部(部位3)，实为 " + r.部位);

  reset(1);
  r = await fire({ 目标Y: 200 });
  if (r.命中 !== 0) bad.push("垂距超出半径应未命中");

  reset(1);
  r = await fire({ 墙体t: 100, 穿墙系数: 0.4 });
  snap.掩体 = r;
  if (r.掩体 !== 0.4) bad.push("墙的 t 更小应命中墙并衰减，实为 " + r.掩体);
  if (r.伤害 <= 0) bad.push("穿墙后仍应计算衰减伤害");

  // 部位：把射线抬高 20 命中头部
  reset(1);
  r = await fire({ 射线起点Y: 20 });
  const head = r;
  reset(1);
  const chest = await fire();
  snap.部位倍率 = { 头: head.伤害, 胸: chest.伤害 };
  if (head.部位 !== 4) bad.push("命中点高于中心 15 应判头部(4)，实为 " + head.部位);
  if (head.伤害 !== chest.伤害 * 4)
    bad.push("爆头倍率应 4×，实为 " + head.伤害 + " / " + chest.伤害);

  // 距离衰减
  reset(1);
  r = await fire({ 目标X: 1600 });
  snap.距离衰减 = { 距离: num(getVar("距离")), 衰减: num(getVar("距离衰减")) };
  if (num(getVar("距离衰减")) >= 1)
    bad.push("距离 >1000 应触发衰减，实为 " + getVar("距离衰减"));

  // 高速弹丸不穿模：由「上一帧到本帧的线段扫掠」保证（结构断言：射线最大距覆盖整段）
  reset(1);
  setVar("射线最大距", 3000);
  r = await fire({ 目标X: 2000 });
  if (r.命中 !== 1) bad.push("扫掠射线应能命中远距离目标（不能只测本帧点）");
}

// ---------------------------------------------------------------- 3. 伤害管线（§482）
{
  // 三角洲：穿透是门槛，不是加伤 buff
  const pen = [];
  for (const p of [2, 3, 5]) {
    reset(3);
    broadcast("设模式"); await stepN(80);
    const r = await fire({ 弹药穿透: p, 护甲等级: 3, 基础伤害: 40 });
    pen.push({ 穿透: p, 系数: num(getVar("护甲系数")), 伤害: r.伤害 });
  }
  snap.穿透门槛 = pen;
  if (Math.abs(pen[0].系数 - 0.15) > 0.001 || Math.abs(pen[1].系数 - 0.75) > 0.001 ||
      Math.abs(pen[2].系数 - 1) > 0.001)
    bad.push("穿透<甲=0.15 / =甲=0.75 / >甲=1.0，实为 " + JSON.stringify(pen));

  // CS：护甲数值与头盔
  reset(1);
  let r = await fire({ 目标护甲: 100 });
  const armored = r.伤害;
  reset(1);
  r = await fire({ 目标护甲: 100, 头盔: 1, 射线起点Y: 20 });
  snap.CS护甲 = { 有甲胸: armored, 有甲带头爆头: r.伤害 };
  if (num(getVar("护甲系数")) >= 0.5)
    bad.push("CS 有甲应减伤且头盔进一步减免爆头");

  // 和平精英：信号值只放大受击伤害，不扣血
  const sig = [];
  for (const v of [100, 60, 40, 10]) {
    reset(2);
    const r = await fire({ 信号值: v });
    sig.push({ 信号值: v, 伤害: r.伤害, 血量: num(getVar("血量")) });
  }
  snap.信号受伤加成 = sig;
  if (!(sig[1].伤害 > sig[0].伤害 && sig[2].伤害 > sig[1].伤害 && sig[3].伤害 > sig[2].伤害))
    bad.push("信号值 <75% 后每降 25% 受击伤害应上一阶");
  if (sig.some((x) => x.血量 !== 100))
    bad.push("★ 信号值不是血条，开火判定不得改玩家血量");
}

// ---------------------------------------------------------------- 4. 后坐力 / 散布（§483）
{
  reset(1);
  broadcast("后坐力"); await stepN(100);
  const first = { 垂直: num(getVar("后坐垂直")), 水平: num(getVar("后坐水平")),
                  散布: num(getVar("散布")) };
  for (let k = 1; k < 6; k++) { broadcast("后坐力"); await stepN(80); }
  const sixth = { 连发: num(getVar("连发数")), 水平: num(getVar("后坐水平")) };
  snap.后坐力 = { 首发: first, 第六发: sixth };
  if (first.垂直 !== 1.2 || first.水平 !== 0.6)
    bad.push("后坐力图案应可复现（首发 1.2/0.6）");
  if (sixth.连发 !== 6 || sixth.水平 >= 0)
    bad.push("第 6 发应进入反向水平图案，实为 " + JSON.stringify(sixth));
  reset(1);
  setVar("移动速度", 10); setVar("蹲下", 1);
  broadcast("后坐力"); await stepN(100);
  const crouch = num(getVar("散布"));
  reset(1);
  setVar("移动速度", 10);
  broadcast("后坐力"); await stepN(100);
  const stand = num(getVar("散布"));
  snap.散布 = { 站立: stand, 蹲下: crouch, 急停: null };
  if (!(crouch < stand)) bad.push("蹲下应减小散布");
  reset(1);
  setVar("移动速度", 10); setVar("急停", 1);
  broadcast("后坐力"); await stepN(100);
  snap.散布.急停 = num(getVar("散布"));
  if (num(getVar("散布")) !== 1) bad.push("急停应把散布恢复到基础值");
}

// ---------------------------------------------------------------- 5. CS2 经济（§484–§486）
{
  const eco = async (res, extra = {}) => {
    reset(1);
    for (const [k, v] of Object.entries(extra)) setVar(k, v);
    setVar("回合结果", res);
    broadcast("回合结算"); await stepN(140);
    return { 收入: num(getVar("本回合收入")), 金钱: num(getVar("金钱")),
             连败档: num(getVar("连败档")), 回合: num(getVar("回合")),
             回合计时: num(getVar("回合计时")) };
  };
  const win = await eco(1);
  const bomb = await eco(2);
  snap.CS胜负奖励 = { 歼灭胜: win.收入, 炸弹胜: bomb.收入 };
  if (win.收入 !== 3250 || bomb.收入 !== 3500)
    bad.push("CS 歼灭胜 $3250 / 炸弹胜 $3500，实为 " + win.收入 + "/" + bomb.收入);

  const ladder = [];
  for (let k = 0; k < 6; k++) {
    // 连续 6 次失败（每次都重置金钱但不重置连败档由脚本自己维护 → 这里单独累计）
    reset(1);
    setVar("连败档", k);
    setVar("回合结果", 3);
    broadcast("回合结算"); await stepN(140);
    ladder.push(num(getVar("本回合收入")));
  }
  snap.连败阶梯 = ladder;
  const want = [1400, 1900, 2400, 2900, 3400, 3400];
  if (ladder.join(",") !== want.join(","))
    bad.push("连败阶梯 +$500 且 5+ 封顶 3400，实为 " + ladder.join(","));

  // 赢一回合只降一级
  reset(1);
  setVar("连败档", 4); setVar("回合结果", 1);
  broadcast("回合结算"); await stepN(140);
  snap.赢后连败档 = num(getVar("连败档"));
  if (num(getVar("连败档")) !== 3)
    bad.push("CS2 赢一回合应把连败档降一级（4→3），实为 " + getVar("连败档"));

  // 下包但输
  reset(1);
  setVar("回合结果", 3); setVar("下包", 1);
  broadcast("回合结算"); await stepN(140);
  if (num(getVar("本回合收入")) !== 2200)
    bad.push("下包但输应 1400+800=2200，实为 " + getVar("本回合收入"));

  // 击杀奖励按武器
  const rewards = [];
  for (const w of [1, 2, 3, 4, 5]) {
    reset(1);
    setVar("回合结果", 1); setVar("击杀武器", w);
    broadcast("回合结算"); await stepN(140);
    rewards.push(num(getVar("本回合收入")) - 3250);
  }
  snap.击杀奖励 = rewards;
  if (rewards.join(",") !== "300,100,600,900,1500")
    bad.push("击杀奖励 步枪300/AWP100/SMG600/霰弹900/刀1500，实为 " + rewards.join(","));

  // 金钱上限 / 半场 / C4 计时
  reset(1);
  setVar("金钱", 15900); setVar("回合结果", 1);
  broadcast("回合结算"); await stepN(140);
  if (num(getVar("金钱")) !== 16000) bad.push("金钱上限应 $16000");
  reset(1);
  setVar("回合", 12); setVar("金钱", 9000); setVar("回合结果", 1);
  broadcast("回合结算"); await stepN(140);
  if (num(getVar("金钱")) !== 800 || num(getVar("半场")) !== 1)
    bad.push("12 回合后应换边并把金钱重置 $800");
  reset(1);
  setVar("C4状态", 1); setVar("回合结果", 1);
  broadcast("回合结算"); await stepN(140);
  if (num(getVar("回合计时")) !== 40)
    bad.push("★ C4 已下应把回合计时切到 40s，实为 " + getVar("回合计时"));
}

// ---------------------------------------------------------------- 6. 和平精英圈（§487）
{
  reset(2);
  let before = { 信号: num(getVar("信号值")), 血: num(getVar("血量")) };
  broadcast("圈推进"); await stepN(140);
  snap.圈内 = { 信号: num(getVar("信号值")), 血: num(getVar("血量")),
                倒计时: num(getVar("圈外倒计时")) };
  if (num(getVar("信号值")) !== 100 || num(getVar("血量")) !== 100)
    bad.push("圈内信号值不减、血量不变");

  reset(2);
  setVar("玩家X", 2000);
  broadcast("圈推进"); await stepN(140);
  snap.圈外_首阶段 = { 信号: num(getVar("信号值")), 血: num(getVar("血量")),
                        倒计时: num(getVar("圈外倒计时")) };
  if (num(getVar("信号值")) !== 99) bad.push("首阶段圈外应扣 1 点信号值");
  if (num(getVar("血量")) !== 100) bad.push("★ 信号值不掉血");

  reset(2);
  setVar("玩家X", 2000); setVar("圈阶段", 7);
  broadcast("圈推进"); await stepN(140);
  snap.圈外_后期 = { 信号: num(getVar("信号值")), 衰减: num(getVar("阶段衰减")) };
  if (num(getVar("阶段衰减")) <= 1)
    bad.push("圈衰减速率应逐阶段递增，后期实为 " + getVar("阶段衰减"));

  reset(2);
  setVar("玩家X", 2000); setVar("圈外倒计时", 1);
  broadcast("圈推进"); await stepN(140);
  if (num(getVar("淘汰")) !== 1)
    bad.push("圈外淘汰倒计时结束应直接淘汰（无视血量/信号值）");
}

// ---------------------------------------------------------------- 7. 摸金（§489–§495）
{
  // 搜刮：同种子可复现；难度只改权重
  reset(3);
  broadcast("搜刮"); await stepN(150);
  const a = { 物品: num(getVar("抽到物品")), 价值: num(getVar("抽到价值")),
              背包: num(getVar("背包价值")), 负重: num(getVar("负重")),
              移速: num(getVar("移速系数")) };
  reset(3);
  broadcast("搜刮"); await stepN(150);
  const b = num(getVar("抽到物品"));
  snap.搜刮 = { 首次: a, 复现: b };
  if (a.物品 !== b) bad.push("战利品抽取必须用可控种子可复现");
  if (!(a.负重 > 0 && a.移速 < 1))
    bad.push("负重应降低移速系数，实为 " + JSON.stringify(a));

  // 撤离条件 + 读条 + 打断
  reset(3);
  setVar("背包价值", 50000);
  broadcast("撤离"); await stepN(120);
  if (num(getVar("撤离成功")) !== 0) bad.push("撤离点未开放/前置未完成时应拒绝");
  reset(3);
  setVar("背包价值", 50000); setVar("撤离点开放", 1); setVar("撤离前置", 1);
  setVar("撤离读条", 7.99);
  broadcast("撤离"); await stepN(140);
  snap.撤离成功 = { 成功: num(getVar("撤离成功")), 仓库: num(getVar("仓库价值")),
                    背包: num(getVar("背包价值")) };
  if (num(getVar("撤离成功")) !== 1 || num(getVar("仓库价值")) !== 50000 ||
      num(getVar("背包价值")) !== 0)
    bad.push("撤离成功应把背包价值入仓库并清空背包");
  reset(3);
  setVar("撤离点开放", 1); setVar("撤离前置", 1);
  setVar("撤离读条", 6); setVar("受击打断", 1);
  broadcast("撤离"); await stepN(120);
  if (num(getVar("撤离读条")) !== 0 || num(getVar("撤离成功")) !== 0)
    bad.push("读条期间受击应打断且归零");

  // 阵亡：全丢，安全箱保留
  reset(3);
  setVar("背包价值", 80000); setVar("带入价值", 20000); setVar("安全箱价值", 30000);
  broadcast("阵亡"); await stepN(100);
  snap.阵亡 = { 背包: num(getVar("背包价值")), 带入: num(getVar("带入价值")),
                安全箱: num(getVar("安全箱价值")) };
  if (num(getVar("背包价值")) !== 0 || num(getVar("带入价值")) !== 0 ||
      num(getVar("安全箱价值")) !== 30000)
    bad.push("阵亡应清空背包与带入装备，仅安全箱保留");

  // 超自然：只有放回收纳柜才计数；金额未达标不能撤
  reset(4);
  broadcast("设模式"); await stepN(80);
  setVar("背包价值", 12000);
  broadcast("撤离"); await stepN(100);
  if (num(getVar("撤离成功")) !== 0 || !String(getVar("结果")).includes("条件不满足"))
    bad.push("未放回收纳柜且撤离未开放时应拒绝");
  setVar("撤离点开放", 1); setVar("撤离前置", 1); setVar("撤离读条", 7.99);
  broadcast("撤离"); await stepN(140);
  if (num(getVar("撤离成功")) !== 0)
    bad.push("★ 身上有钱但没入柜 → 目标金额未达标，不能撤离");
  broadcast("放入收纳柜"); await stepN(100);
  snap.收纳柜 = { 已入柜: num(getVar("已入柜价值")), 背包: num(getVar("背包价值")) };
  if (num(getVar("已入柜价值")) !== 12000 || num(getVar("背包价值")) !== 0)
    bad.push("放入收纳柜应把背包价值转入已入柜价值");
  setVar("撤离读条", 7.99);
  broadcast("撤离"); await stepN(140);
  if (num(getVar("撤离成功")) !== 1)
    bad.push("入柜达标后应可撤离");
}

// ---------------------------------------------------------------- 8. 动态难度 / 怪物 AI（§492–§493）
{
  reset(4);
  broadcast("推进时间"); await stepN(100);
  const d1 = num(getVar("危险指数"));
  reset(4);
  setVar("龙珠", 1);
  broadcast("推进时间"); await stepN(100);
  const d2 = num(getVar("危险指数"));
  snap.动态难度 = { 无龙珠: d1, 有龙珠: d2 };
  if (!(d2 > d1 + 2.9)) bad.push("拿到龙珠应让危险指数跃升 +3");
  reset(4);
  setVar("局内分钟", 23);
  broadcast("推进时间"); await stepN(100);
  if (num(getVar("淘汰")) !== 1) bad.push("局内 24 点超时应失败");

  reset(4);
  setVar("门开", 0); setVar("怪物距离", 100);
  broadcast("怪物AI"); await stepN(100);
  const patrol = getVar("AI结果");
  reset(4);
  setVar("门开", 1); setVar("怪物距离", 100);
  broadcast("怪物AI"); await stepN(100);
  const chase = getVar("AI结果");
  reset(4);
  setVar("门开", 0); setVar("怪物距离", 100); setVar("声波半径", 200);
  broadcast("怪物AI"); await stepN(100);
  const heard = getVar("AI结果");
  reset(4);
  setVar("门开", 1); setVar("怪物距离", 100);
  setVar("玩家高度", 2); setVar("怪物高度", 0);
  broadcast("怪物AI"); await stepN(100);
  const high = getVar("AI结果");
  snap.怪物AI = { 关门: patrol, 开门: chase, 听声: heard, 高低差: high };
  if (!String(patrol).includes("巡逻")) bad.push("关门应隔离怪物（未感知）");
  if (!String(chase).includes("追击")) bad.push("开门且在视距内应追击");
  if (!String(heard).includes("追击")) bad.push("声波事件应让怪物感知（即使门关）");
  if (!String(high).includes("够不到")) bad.push("高低差应让近战怪打不到");
}

// ---------------------------------------------------------------- 结果
const pass = bad.length === 0;
console.log(JSON.stringify(snap, null, 2));
if (pass) {
  console.log("SHOOTER_REPLICAS_LOGIC_OK  四款射击/摸金复刻判定全部正确（CS2/和平精英/三角洲/超自然行动组）");
  process.exit(0);
} else {
  console.log("SHOOTER_REPLICAS_LOGIC_FAIL");
  for (const b of bad) console.log("  ✗ " + b);
  process.exit(1);
}
