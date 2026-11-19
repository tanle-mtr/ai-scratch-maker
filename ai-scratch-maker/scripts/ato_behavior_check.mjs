// ATO 自动驾驶行为校验：跑完两站全程，验证规划层 / 执行层 / 状态机 / 安全层。
// 用法: node ato_behavior_check.mjs <ato_train.sb3>
import fs from "node:fs";
import { findScratchVM, loadScratchVM } from "./scratch_vm_path.mjs";

const VM = loadScratchVM(findScratchVM());
const vm = new VM();

const buf = fs.readFileSync(process.argv[2]);
await vm.loadProject(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
vm.runtime.currentStepTime = 1000 / 30;

const num = (x) => (typeof x === "string" ? parseFloat(x) : x);
const r2 = (x) => Math.round(x * 100) / 100;

function getVar(name) {
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v && v.name === name) return v.value;
    }
  }
  return undefined;
}
function setVar(name, value) {
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v && v.name === name) { v.value = value; return true; }
    }
  }
  return false;
}

// ★ 线路数据从产物里读，而不是写死在断言里。
//   原因：scripts/gen_ato.py 支持换线路（站名/站距/限速表是参数），
//   若断言写死「2 段 / 1500 米 / 75 限速 / 桂湾」，换线路后校验必然假红。
//   改为读 站距 / 限速表 / 站名 三个列表，断言对任意线路都成立。
function getList(name) {
  for (const t of vm.runtime.targets) {
    for (const id of Object.keys(t.variables || {})) {
      const v = t.variables[id];
      if (v && v.name === name && Array.isArray(v.value)) return v.value.map(String);
    }
  }
  return [];
}

const stepN = async (n) => {
  for (let i = 0; i < n; i++) {
    vm.runtime.currentMSecs += 33;
    vm.runtime._step();
    await Promise.resolve();
  }
};
const broadcast = (m) =>
  vm.runtime.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: m });

// ★ 教训：startHats 只入队，线程在「下一个」_step 才跑 → 一帧必须推进 2 步
const frames = async (n = 1) => {
  for (let i = 0; i < n; i++) { broadcast("帧"); await stepN(2); }
};

const bad = [];
const snap = {};
const st = () => num(getVar("状态"));

// ---------------------------------------------------------------- 0. 启动
vm.greenFlag();
await stepN(3);
setVar("自动帧", 0);            // 接管时钟，避免与舞台 forever 抢发帧
await stepN(3);

snap.初_状态 = st();
snap.初_剩余里程 = r2(num(getVar("剩余里程")));
snap.初_速度 = r2(num(getVar("速度")));
snap.初_总段数 = num(getVar("总段数"));

// 线路数据（从产物读，供断言使用）
const LINE_站名 = getList("站名");
const LINE_站距 = getList("站距").map(Number);
const LINE_限速 = getList("限速表").map(Number);
const LINE_段数 = LINE_站距.length;
snap.线路 = { 站名: LINE_站名, 站距: LINE_站距, 限速: LINE_限速 };

if (LINE_段数 < 1) bad.push("线路数据缺失：站距列表为空");
if (LINE_站名.length !== LINE_段数 + 1)
  bad.push("站名数量应等于 站距数+1，实为 " + LINE_站名.length + "/" + (LINE_段数 + 1));
if (LINE_限速.length !== LINE_段数)
  bad.push("限速表长度应等于 站距长度，实为 " + LINE_限速.length + "/" + LINE_段数);

if (snap.初_状态 !== 0) bad.push("初始状态应为 0（待发车），实为 " + snap.初_状态);
if (LINE_段数 > 0 && Math.abs(snap.初_剩余里程 - LINE_站距[0]) > 0.5)
  bad.push("初始剩余里程应为首段站距 " + LINE_站距[0] + "，实为 " + snap.初_剩余里程);
if (snap.初_总段数 !== LINE_段数)
  bad.push("总段数应为 " + LINE_段数 + "，实为 " + snap.初_总段数);

// ---------------------------------------------------------------- 1. 自动起步
let g = 0;
while (st() === 0 && g < 80) { await frames(1); g++; }
snap.起步_帧数 = g;
snap.起步_状态 = st();
if (snap.起步_状态 !== 1) bad.push("起步延时到期后应进入运行(1)，实为 " + snap.起步_状态);
if (g === 0) bad.push("起步延时未生效（第一帧就发车）");

// ---------------------------------------------------------------- 2. 牵引加速
await frames(20);
const v20 = num(getVar("速度"));
snap.加速_20帧速度 = r2(v20);
if (v20 <= 1) bad.push("牵引 20 帧速度应明显上升，实为 " + v20);

// ---------------------------------------------------------------- 3. 巡航封顶（不超区间限速）
let vmax = 0, gmax = 0;
while (st() === 1 && gmax < 900 && num(getVar("剩余里程")) > 260) {
  await frames(1); gmax++;
  vmax = Math.max(vmax, num(getVar("速度")));
}
snap.巡航_最高速 = r2(vmax);
snap.巡航_区间限速 = num(getVar("区间限速"));
if (vmax > num(getVar("区间限速")) + 0.01)
  bad.push("超速: 最高 " + vmax + " > 限速 " + num(getVar("区间限速")));

// ---------------------------------------------------------------- 4. 进站制动（包络生效）
const vNear = num(getVar("速度"));
snap.进站_260m速度 = r2(vNear);
if (vNear > 70) bad.push("距停车标 260m 时速度仍 " + vNear + "，制动曲线未生效");

// ---------------------------------------------------------------- 5. 精确停车
g = 0;
while (st() === 1 && g < 1200) { await frames(1); g++; }
snap.第一段_总帧 = gmax + g + 21;
snap.停车1_状态 = st();
snap.停车1_误差 = r2(num(getVar("对标误差")));
snap.停车1_结果 = getVar("停车结果");
snap.停车1_速度 = r2(num(getVar("速度")));
if (st() !== 2 && st() !== 3 && st() !== 4)
  bad.push("第一段应停稳(2)或已进入开门流程，实为 " + st());
if (Math.abs(snap.停车1_误差) > 5)
  bad.push("第一段对标误差 " + snap.停车1_误差 + " 超出 ±5 米窗口");
if (Math.abs(snap.停车1_速度) > 0.01)
  bad.push("停车判定时速度未归零: " + snap.停车1_速度);

// ---------------------------------------------------------------- 6. 开门 → 保持 → 关门
g = 0;
while (st() !== 4 && g < 120) { await frames(1); g++; }
snap.开门_帧数 = g;
snap.开门_门位 = num(getVar("门位"));
snap.开门_车门 = num(getVar("车门"));
if (snap.开门_门位 !== 100) bad.push("开门后门位应到 100，实为 " + snap.开门_门位);
if (snap.开门_车门 !== 1) bad.push("开门后车门标志应为 1");
if (g < 10) bad.push("开门动画过快（应逐帧推进，不是瞬间到 100）");

g = 0;
while (st() === 4 && g < 200) { await frames(1); g++; }
snap.dwell_帧数 = g;
if (g < 30) bad.push("停站保持过短: " + g + " 帧");

// ---------------------------------------------------------------- 7. 关门 + 站点推进（握手）
g = 0;
while (st() === 5 && g < 120) { await frames(1); g++; }
snap.站点2_状态 = st();
snap.站点2_站点 = num(getVar("站点"));
snap.站点2_剩余里程 = r2(num(getVar("剩余里程")));
snap.站点2_限速 = num(getVar("区间限速"));
snap.站点2_当前站 = getVar("当前站");
snap.站点2_下一站 = getVar("下一站");
if (snap.站点2_站点 !== 2) bad.push("关门后站点应推进到 2，实为 " + snap.站点2_站点);
if (LINE_段数 > 1) {
  if (Math.abs(snap.站点2_剩余里程 - LINE_站距[1]) > 0.5)
    bad.push("站点推进后剩余里程应重置为第 2 段站距 " + LINE_站距[1] + "，实为 " + snap.站点2_剩余里程);
  if (snap.站点2_限速 !== LINE_限速[1])
    bad.push("第二段限速应切到 " + LINE_限速[1] + "，实为 " + snap.站点2_限速);
  if (snap.站点2_当前站 !== LINE_站名[1])
    bad.push("当前站应更新为 " + LINE_站名[1] + "，实为 " + snap.站点2_当前站);
}
if (num(getVar("门位")) !== 0) bad.push("关门后门位应归零");

// ---------------------------------------------------------------- 8. 第二段自动发车
g = 0;
while (st() === 0 && g < 80) { await frames(1); g++; }
snap.第二段_发车帧 = g;
if (st() !== 1 && st() !== 6) bad.push("第二段应自动发车，实为状态 " + st());

// ---------------------------------------------------------------- 9. 跑完全程
g = 0;
while (st() !== 6 && g < 2500) { await frames(1); g++; }
snap.全程_第二段帧 = g;
snap.终点_状态 = st();
snap.终点_完成数 = num(getVar("完成数"));
snap.终点_分值 = num(getVar("分值"));
snap.终点_能耗率 = num(getVar("能耗率"));
snap.终点_完美数 = num(getVar("完美数"));
if (st() !== 6) bad.push("全程未跑完，状态 " + st() + "（可能半路停死）");
if (snap.终点_完成数 !== LINE_段数)
  bad.push("完成段数应为 " + LINE_段数 + "，实为 " + snap.终点_完成数);
if (snap.终点_分值 <= 0) bad.push("完成全程分值应 > 0，实为 " + snap.终点_分值);
if (snap.终点_能耗率 <= 0 || snap.终点_能耗率 >= 100)
  bad.push("牵引能耗占比异常: " + snap.终点_能耗率 + "%（应在 0~100 之间）");

// ---------------------------------------------------------------- 10. 红灯降级（安全层）
broadcast("重置"); await stepN(3);
setVar("自动帧", 0); await stepN(2);
await frames(40);                      // 跑起来
const vRun = num(getVar("速度"));
if (vRun <= 0) bad.push("重置后未重新起步，无法测红灯降级");
setVar("信号", 1);                      // 红灯
await frames(30);
snap.红灯_推荐速度 = r2(num(getVar("推荐速度")));
snap.红灯_速度 = r2(num(getVar("速度")));
snap.红灯_信号名 = getVar("信号名");
if (snap.红灯_推荐速度 > 0.01) bad.push("红灯后推荐速度应归零，实为 " + snap.红灯_推荐速度);
if (snap.红灯_速度 > 1) bad.push("红灯后应制动到停，实为 " + snap.红灯_速度 + " km/h");
if (snap.红灯_信号名 !== "红") bad.push("信号名应为红，实为 " + snap.红灯_信号名);

// ---------------------------------------------------------------- 11. 二次对标（欠标自动爬行）
setVar("信号", 3); setVar("状态名", "运行");
setVar("状态", 1);
setVar("剩余里程", 9); setVar("速度", 0); setVar("目标速度", 0);
await frames(1);
snap.欠标_目标速度 = r2(num(getVar("目标速度")));
if (snap.欠标_目标速度 < 1)
  bad.push("欠标 9m 且已停稳时，目标速度应为爬行值(>1)，实为 " + snap.欠标_目标速度);
g = 0;
while (st() === 1 && g < 400) { await frames(1); g++; }
snap.欠标_收敛帧 = g;
snap.欠标_最终误差 = r2(num(getVar("对标误差")));
if (st() !== 2) bad.push("二次对标后应停稳，实为状态 " + st());
if (Math.abs(snap.欠标_最终误差) > 5)
  bad.push("二次对标误差 " + snap.欠标_最终误差 + " 仍超 ±5");

// ---------------------------------------------------------------- 结果
const pass = bad.length === 0;
console.log(JSON.stringify(snap, null, 2));
if (pass) {
  console.log("ATO_LOGIC_OK  全部断言通过");
  process.exit(0);
} else {
  console.log("ATO_LOGIC_FAIL");
  for (const b of bad) console.log("  ✗ " + b);
  process.exit(1);
}
