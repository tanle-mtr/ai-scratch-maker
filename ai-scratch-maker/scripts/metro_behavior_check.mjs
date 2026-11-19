// 地铁模拟行为校验：验证牵引/制动/限速、速度积分里程、折线插值定位、到站判定（位置+停稳）、
// 车门四态状态机、门未关禁止牵引、表针角度映射。
// 用法: node metro_behavior_check.mjs <metro.sb3> [--json]
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_METRO")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node metro_behavior_check.mjs <metro.sb3>"); process.exit(2); }

let vm = null;
const num = (x) => (typeof x === "string" ? parseFloat(x) : x);
const getVar = (name) => {
  for (const t of vm.runtime.targets)
    for (const id of Object.keys(t.variables || {}))
      if (t.variables[id] && t.variables[id].name === name) return t.variables[id].value;
  return undefined;
};
const setVar = (name, val) => {
  for (const t of vm.runtime.targets)
    for (const id of Object.keys(t.variables || {}))
      if (t.variables[id] && t.variables[id].name === name) { t.variables[id].value = val; return true; }
  return false;
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
  // 广播后推进两格：无头下 startHats 只入队，执行落在下一个 _step
  const frames = async (n = 1) => {
    for (let i = 0; i < n; i++) { broadcast("帧"); await stepN(2); }
  };
  const until = async (pred, cap = 200) => {
    let g = 0;
    while (!pred() && g < cap) { await frames(1); g++; }
    return g < cap;
  };

  const bad = [];
  const snap = {};

  // ---- 初始化
  vm.greenFlag();
  await stepN(2);
  setVar("自动帧", 0);        // 关掉自带时钟，逐帧驱动（可复现）
  setVar("使用键盘", 0);      // 档位改由变量注入
  setVar("时间倍率", 0);      // 先冻结里程，专测加减速，避免误触到站
  await stepN(3);
  snap.初始里程 = num(getVar("里程"));
  snap.初始下一站 = num(getVar("下一站"));
  if (snap.初始下一站 !== 2) bad.push("初始下一站!=2: " + snap.初始下一站);

  // ---- A. 牵引：档位 +1 → 速度上升
  setVar("档位", 1);
  await frames(10);
  snap.牵引后速度 = Math.round(num(getVar("速度")) * 100) / 100;
  if (!(snap.牵引后速度 > 3)) bad.push("牵引后速度未上升: " + snap.牵引后速度);

  // ---- B. 限速：猛拉 200 帧不能超过限速（80）
  await frames(200);
  snap.限速后速度 = Math.round(num(getVar("速度")) * 100) / 100;
  snap.限速值 = num(getVar("限速"));
  if (snap.限速后速度 > snap.限速值 + 0.01) bad.push("超过限速: " + snap.限速后速度 + " > " + snap.限速值);
  if (!(snap.限速后速度 >= snap.限速值 - 1)) bad.push("没有拉到限速: " + snap.限速后速度);

  // ---- I. 表针角度 = 速度/满量程*180 - 90
  const sc = num(getVar("速度")), full = num(getVar("表盘满量程"));
  snap.表针角 = Math.round(num(getVar("表针角")) * 100) / 100;
  const expectNeedle = Math.round((sc / full * 180 - 90) * 100) / 100;
  if (Math.abs(snap.表针角 - expectNeedle) > 0.6)
    bad.push("表针角映射错: " + snap.表针角 + " 期望 " + expectNeedle);

  // ---- D. 制动：档位 -1 → 速度下降
  setVar("档位", -1);
  await frames(20);
  snap.制动后速度 = Math.round(num(getVar("速度")) * 100) / 100;
  if (!(snap.制动后速度 < snap.限速后速度 - 10))
    bad.push("制动无效: " + snap.限速后速度 + " -> " + snap.制动后速度);

  // ---- C. 里程 → 屏幕坐标：折线插值（段1：0~800 米，x -200~0）
  setVar("档位", 0); setVar("速度", 0);
  setVar("里程", 400);
  await frames(1);
  snap.插值_t = Math.round(num(getVar("t")) * 1000) / 1000;
  snap.插值_列车x = Math.round(num(getVar("列车x")) * 100) / 100;
  snap.插值_列车y = Math.round(num(getVar("列车y")) * 100) / 100;
  if (Math.abs(snap.插值_t - 0.5) > 0.01) bad.push("插值 t 不对: " + snap.插值_t + " 期望 0.5");
  if (Math.abs(snap.插值_列车x - (-100)) > 1) bad.push("插值 x 不对: " + snap.插值_列车x + " 期望 -100");

  // ---- E. 到站判定：位置够近 + 停稳 → 开门中 + 记停车偏差
  setVar("里程", 795);          // 距 800 米停车点还差 5 米
  setVar("速度", 0);
  setVar("车门状态", 0);
  setVar("到站次数", 0);
  setVar("停车偏差", 0);
  await frames(1);
  snap.到站后车门状态 = num(getVar("车门状态"));
  snap.到站次数 = num(getVar("到站次数"));
  snap.停车偏差 = num(getVar("停车偏差"));
  if (snap.到站后车门状态 !== 1) bad.push("到站未进入开门中(状态!=1): " + snap.到站后车门状态);
  if (snap.到站次数 !== 1) bad.push("到站计数不对: " + snap.到站次数);
  if (snap.停车偏差 !== -5) bad.push("停车偏差不对: " + snap.停车偏差 + " 期望 -5");

  // ---- E2. 位置到了但没停稳 → 不应开门（§170 的核心）
  setVar("车门状态", 0); setVar("到站次数", 0);
  setVar("里程", 795); setVar("速度", 40);      // 高速通过
  await frames(1);
  snap.高速通过_车门状态 = num(getVar("车门状态"));
  snap.高速通过_到站次数 = num(getVar("到站次数"));
  if (snap.高速通过_车门状态 !== 0 || snap.高速通过_到站次数 !== 0)
    bad.push("高速通过也开门了（只判位置没判停稳）: 状态=" + snap.高速通过_车门状态);

  // ---- F. 开门推进到底 → 已开 + 停站计时装载
  setVar("里程", 795); setVar("速度", 0); setVar("车门状态", 1); setVar("门开度", 0);
  const opened = await until(() => num(getVar("车门状态")) === 2, 40);
  snap.开门完成 = opened;
  snap.门开度_全开 = num(getVar("门开度"));
  snap.停站计时 = num(getVar("停站计时"));
  if (!opened) bad.push("开门未完成(状态未到 2)");
  if (snap.门开度_全开 !== 100) bad.push("门开度未到 100: " + snap.门开度_全开);
  if (!(snap.停站计时 > 0)) bad.push("停站计时未装载: " + snap.停站计时);

  // ---- H. 门开着不许牵引
  setVar("档位", 1); setVar("速度", 0);
  await frames(5);
  snap.开门时速度 = Math.round(num(getVar("速度")) * 100) / 100;
  if (snap.开门时速度 > 0.01) bad.push("门没关就能牵引了: 速度=" + snap.开门时速度);

  // ---- G. 停站结束 → 关门到底 → 下一站推进
  setVar("档位", 0);
  const closed = await until(() => num(getVar("车门状态")) === 0, 220);
  snap.关门完成 = closed;
  snap.门开度_关 = num(getVar("门开度"));
  snap.下一站 = num(getVar("下一站"));
  snap.当前站 = num(getVar("当前站"));
  if (!closed) bad.push("关门未完成(状态未回到 0)");
  if (snap.门开度_关 !== 0) bad.push("门开度未归零: " + snap.门开度_关);
  if (snap.下一站 !== 3) bad.push("关门后下一站未推进: " + snap.下一站);
  if (snap.当前站 !== 2) bad.push("关门后当前站未推进: " + snap.当前站);

  // ---- I2. 关门后允许牵引恢复
  setVar("档位", 1);
  await frames(3);
  snap.恢复牵引速度 = Math.round(num(getVar("速度")) * 100) / 100;
  snap.允许牵引 = num(getVar("允许牵引"));
  if (snap.允许牵引 !== 1) bad.push("关门后允许牵引未恢复");
  if (!(snap.恢复牵引速度 > 0)) bad.push("关门后无法牵引: 速度=" + snap.恢复牵引速度);

  console.log(JSON.stringify({ actual: snap, bad }, null, 2));
  if (bad.length) { console.error("METRO_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("METRO_LOGIC_OK");
})().catch((e) => { console.error("METRO_CHECK_FAIL", e && (e.stack || e)); process.exit(1); });
