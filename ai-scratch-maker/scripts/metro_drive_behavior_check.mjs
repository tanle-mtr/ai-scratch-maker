// 地铁驾驶模拟（进阶）行为校验：验证第二十五册 §207–§221 的核心机制。
// 覆盖：剩余里程初始化 / 牵引加速 / 限速封顶 / 里程积分（速度÷里程系数）/
//       制动到零不回退 / 推荐速度闭式曲线（制动距离 v²=2ad）/ 超速自动干预 /
//       到站握手（停稳 + |d|≤5）/ 开门重置里程 + 站点推进 / 冲标（d<-5）/ 退回重对标 /
//       三显示移动闭塞阈值（9000 / 5000）/ 前车推进 + 间距扣车长 / 终点结算
// 用法: node metro_drive_behavior_check.mjs <metro_drive.sb3>
import fs from "node:fs";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";

const vmPath = findScratchVM();
if (!vmPath) { console.error(skipMessage("SKIP_METRO_DRIVE")); process.exit(0); }
const VirtualMachine = loadScratchVM(vmPath);

const sb3Path = process.argv[2];
if (!sb3Path) { console.error("用法: node metro_drive_behavior_check.mjs <metro_drive.sb3>"); process.exit(2); }

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
const r2 = (x) => Math.round(num(x) * 100) / 100;

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
  // 无头下 startHats 只入队，执行落在下一个 _step（§156 的坑），故推进两格
  const frames = async (n = 1) => {
    for (let i = 0; i < n; i++) { broadcast("帧"); await stepN(2); }
  };

  const bad = [];
  const snap = {};

  vm.greenFlag();
  await stepN(3);
  setVar("自动帧", 0);      // 关掉自带时钟，逐帧驱动（可复现）
  setVar("使用键盘", 0);    // 档位/车门改为直接注入
  setVar("前车速度", 0);    // 前车先冻住，避免干扰单测
  setVar("前车里程", 20000);
  await stepN(2);

  // ---- ① 初始化：剩余里程 = 站距[1]，站点 1，状态 0
  snap.初始_剩余里程 = r2(getVar("剩余里程"));
  snap.初始_站点 = num(getVar("站点"));
  snap.初始_总段数 = num(getVar("总段数"));
  snap.初始_当前站 = getVar("当前站");
  snap.初始_下一站 = getVar("下一站");
  snap.初始_运行状态 = num(getVar("运行状态"));
  if (snap.初始_剩余里程 !== 5090) bad.push("初始剩余里程应为站距[1]=5090: " + snap.初始_剩余里程);
  if (snap.初始_站点 !== 1) bad.push("初始站点应为 1: " + snap.初始_站点);
  if (snap.初始_总段数 !== 5) bad.push("总段数应为 5: " + snap.初始_总段数);
  if (snap.初始_当前站 !== "前海湾" || snap.初始_下一站 !== "桂湾")
    bad.push("站名取错: " + snap.初始_当前站 + "→" + snap.初始_下一站);
  if (snap.初始_运行状态 !== 0) bad.push("初始运行状态应为 0: " + snap.初始_运行状态);

  // ---- ② 牵引：档位 1，10 帧 × 1.2 = 12
  setVar("档位", 1); setVar("速度", 0); setVar("剩余里程", 5090);
  await frames(10);
  snap.牵引10帧_速度 = r2(getVar("速度"));
  if (Math.abs(snap.牵引10帧_速度 - 12) > 0.6) bad.push("牵引 10 帧应≈12: " + snap.牵引10帧_速度);

  // ---- ③ 限速封顶：一直牵引不能超过区间限速 80
  setVar("剩余里程", 5090);
  await frames(120);
  snap.封顶_速度 = r2(getVar("速度"));
  snap.封顶_区间限速 = num(getVar("区间限速"));
  if (snap.封顶_速度 > snap.封顶_区间限速 + 0.01)
    bad.push("超过区间限速: " + snap.封顶_速度 + " > " + snap.封顶_区间限速);
  if (snap.封顶_速度 < snap.封顶_区间限速 - 0.01)
    bad.push("没有拉到区间限速: " + snap.封顶_速度);

  // ---- ④ 里程积分：Δd = 速度/里程系数 × 帧数
  const coeff = num(getVar("里程系数"));
  setVar("档位", 0); setVar("速度", 80); setVar("剩余里程", 5000);
  const d0 = num(getVar("剩余里程"));
  await frames(10);
  const d1 = num(getVar("剩余里程"));
  snap.积分_系数 = coeff;
  snap.积分_10帧Δ = r2(d0 - d1);
  const expectDelta = (80 / coeff) * 10;
  if (Math.abs(snap.积分_10帧Δ - expectDelta) > 2)
    bad.push("里程积分错: Δ=" + snap.积分_10帧Δ + " 期望≈" + expectDelta.toFixed(2));

  // ---- ⑤ 制动：档位 3 降到 0 且不回退为负（§215 过零夹紧）
  setVar("档位", 3); setVar("速度", 80); setVar("剩余里程", 4000);
  await frames(80);
  snap.制动_速度 = r2(getVar("速度"));
  if (snap.制动_速度 !== 0) bad.push("制动后速度应夹到 0（不许为负）: " + snap.制动_速度);

  // ---- ⑥ 推荐速度闭式：v = 3.6·√(2·a·(d-5))
  setVar("档位", 0); setVar("速度", 0); setVar("剩余里程", 400);
  await frames(1);
  snap.推荐_d400 = r2(getVar("推荐速度"));
  const a = num(getVar("制动率"));
  const expect400 = 3.6 * Math.sqrt(2 * a * (400 - 5));
  if (Math.abs(snap.推荐_d400 - expect400) > 2)
    bad.push("d=400 推荐速度错: " + snap.推荐_d400 + " 期望≈" + expect400.toFixed(1));

  setVar("剩余里程", 100); await frames(1);
  snap.推荐_d100 = r2(getVar("推荐速度"));
  if (!(snap.推荐_d100 > 25 && snap.推荐_d100 < 45))
    bad.push("d=100 推荐速度应在 25~45: " + snap.推荐_d100);

  // 远距离应被区间限速钳住（而不是被曲线钳住）
  setVar("剩余里程", 3000); await frames(1);
  snap.推荐_d3000 = r2(getVar("推荐速度"));
  if (Math.abs(snap.推荐_d3000 - num(getVar("区间限速"))) > 0.5)
    bad.push("远距离推荐速度应等于区间限速: " + snap.推荐_d3000);

  // ---- ⑦ 超速自动干预：速度 > 推荐+3 → 每帧扣紧急减
  setVar("剩余里程", 100); setVar("速度", 60); setVar("档位", 0);
  await frames(1);
  const vAfter1 = num(getVar("速度"));
  snap.超速_1帧后 = r2(vAfter1);
  if (!(vAfter1 < 60 - 3)) bad.push("超速未触发紧急制动: " + vAfter1);
  await frames(20);
  snap.超速_21帧后 = r2(getVar("速度"));
  if (!(snap.超速_21帧后 < 42))
    bad.push("超速干预没把速度拉回推荐附近: " + snap.超速_21帧后);

  // ---- ⑧ 到站握手：停稳 + |d|≤5 → 状态 1 + 完美对标 +100
  setVar("速度", 0); setVar("档位", 0); setVar("运行状态", 0);
  setVar("站点", 1); setVar("剩余里程", 1); setVar("分值", 0); setVar("停车结果", "—");
  await frames(2);
  snap.到站_运行状态 = num(getVar("运行状态"));
  snap.到站_对标误差 = num(getVar("对标误差"));
  snap.到站_停车结果 = getVar("停车结果");
  snap.到站_分值 = num(getVar("分值"));
  if (snap.到站_运行状态 !== 1) bad.push("到站后状态应为 1（停站）: " + snap.到站_运行状态);
  if (snap.到站_停车结果 !== "完美对标") bad.push("|d|=1 应为完美对标: " + snap.到站_停车结果);
  if (snap.到站_分值 !== 100) bad.push("完美对标应 +100: " + snap.到站_分值);

  // 停车中速度锁死（门没关也不许动）
  setVar("档位", 1); await frames(3);
  snap.停站_牵引速度 = r2(getVar("速度"));
  if (snap.停站_牵引速度 !== 0) bad.push("停站中不应能动: " + snap.停站_牵引速度);

  // ---- ⑨ 开门 → 关门：重置里程 = 站距[新站点]，站点 +1
  setVar("档位", 0);
  broadcast("开门"); await stepN(2);
  snap.开门后_车门 = num(getVar("车门"));
  if (snap.开门后_车门 !== 1) bad.push("开门未生效: " + snap.开门后_车门);

  broadcast("关门"); await stepN(2);
  snap.关门后_车门 = num(getVar("车门"));
  snap.关门后_站点 = num(getVar("站点"));
  snap.关门后_剩余里程 = r2(getVar("剩余里程"));
  snap.关门后_完成数 = num(getVar("完成数"));
  snap.关门后_运行状态 = num(getVar("运行状态"));
  snap.关门后_当前站 = getVar("当前站");
  if (snap.关门后_车门 !== 0) bad.push("关门未生效: " + snap.关门后_车门);
  if (snap.关门后_站点 !== 2) bad.push("站点未推进: " + snap.关门后_站点);
  if (snap.关门后_剩余里程 !== 12500) bad.push("里程未重置为新段全长 12500: " + snap.关门后_剩余里程);
  if (snap.关门后_完成数 !== 1) bad.push("完成数应为 1: " + snap.关门后_完成数);
  if (snap.关门后_运行状态 !== 0) bad.push("关门后应回到驾驶状态 0: " + snap.关门后_运行状态);
  if (snap.关门后_当前站 !== "桂湾") bad.push("当前站应为桂湾: " + snap.关门后_当前站);

  // ---- ⑩ 冲标：d < -5 且停稳 → 状态 2 + 扣 50
  setVar("运行状态", 0); setVar("速度", 0); setVar("档位", 0);
  setVar("剩余里程", -18); setVar("分值", 0); setVar("停车结果", "—");
  await frames(2);
  snap.冲标_运行状态 = num(getVar("运行状态"));
  snap.冲标_停车结果 = getVar("停车结果");
  snap.冲标_分值 = num(getVar("分值"));
  if (snap.冲标_运行状态 !== 2) bad.push("冲标应进入状态 2: " + snap.冲标_运行状态);
  if (snap.冲标_停车结果 !== "冲标") bad.push("冲标结果标记错: " + snap.冲标_停车结果);
  if (snap.冲标_分值 !== -50) bad.push("冲标应 -50: " + snap.冲标_分值);

  // ---- ⑪ 退回：一次不够（-18+12=-6 仍 < -5），两次才进窗口
  broadcast("退回"); await frames(1);
  snap.退回1_剩余里程 = r2(getVar("剩余里程"));
  snap.退回1_运行状态 = num(getVar("运行状态"));
  if (snap.退回1_剩余里程 !== -6) bad.push("退回一次应到 -6: " + snap.退回1_剩余里程);
  if (snap.退回1_运行状态 !== 2) bad.push("仍冲标却已离开状态 2: " + snap.退回1_运行状态);

  broadcast("退回"); await frames(1);
  snap.退回2_剩余里程 = r2(getVar("剩余里程"));
  snap.退回2_运行状态 = num(getVar("运行状态"));
  snap.退回2_停车结果 = getVar("停车结果");
  if (snap.退回2_运行状态 !== 1) bad.push("退回窗口后应进入停站状态 1: " + snap.退回2_运行状态);
  if (snap.退回2_停车结果 !== "退回对标") bad.push("退回对标标记错: " + snap.退回2_停车结果);

  // ---- ⑫ 三显示移动闭塞阈值（必须扣车长 1400）
  const sigOf = async (leadMile) => {
    setVar("本车里程", 0); setVar("前车里程", leadMile);
    setVar("前车速度", 0); setVar("速度", 0); setVar("档位", 0);
    await frames(1);
    return { sig: num(getVar("信号")), gap: num(getVar("间距")) };
  };
  const g1 = await sigOf(0 + 1400 + 10000);   // 净空 10000 → 绿
  const g2 = await sigOf(0 + 1400 + 6000);    // 净空 6000  → 黄
  const g3 = await sigOf(0 + 1400 + 3000);    // 净空 3000  → 红
  const g4 = await sigOf(0 + 1400 + 5000);    // 净空 5000（边界）→ 红（条件是 >5000）
  snap.信号_净空10000 = g1.sig;
  snap.信号_净空6000 = g2.sig;
  snap.信号_边界5000 = g4.sig;
  snap.信号_净空3000 = g3.sig;
  snap.间距_扣车长 = r2(g1.gap);
  if (g1.sig !== 3) bad.push("净空 10000 应为绿灯: " + g1.sig);
  if (g2.sig !== 2) bad.push("净空 6000 应为黄灯: " + g2.sig);
  if (g4.sig !== 1) bad.push("净空 5000 边界应为红灯: " + g4.sig);
  if (g3.sig !== 1) bad.push("净空 3000 应为红灯: " + g3.sig);
  if (Math.abs(snap.间距_扣车长 - 10000) > 1)
    bad.push("间距未扣车长: " + snap.间距_扣车长 + " 期望 10000");

  // ---- ⑬ 前车推进：前车里程 += 前车速度/系数，间距随之收缩
  setVar("本车里程", 0); setVar("前车里程", 20000);
  setVar("前车速度", 80); setVar("速度", 0); setVar("档位", 0);
  await frames(10);
  snap.前车_10帧后里程 = r2(getVar("前车里程"));
  snap.前车_间距 = r2(getVar("间距"));
  const expectLead = 20000 + (80 / coeff) * 10;
  if (Math.abs(snap.前车_10帧后里程 - expectLead) > 2)
    bad.push("前车里程推进错: " + snap.前车_10帧后里程 + " 期望≈" + expectLead.toFixed(1));
  // 间距在本帧「积分之前」算，天然比快照晚一帧（控制用上一帧状态，属正确设计），
  // 容差放宽到一帧的前车位移（80/12 ≈ 6.7 米）。
  if (Math.abs(snap.前车_间距 - (expectLead - 1400)) > 8)
    bad.push("间距计算错: " + snap.前车_间距 + " 期望≈" + (expectLead - 1400).toFixed(1));

  // ---- ⑭ 终点：最后一段开门关门 → 状态 3 结算（铁律 13 靠 结算面板 的按钮回到「重置」）
  setVar("站点", 5); setVar("完成数", 4); setVar("运行状态", 0);
  setVar("速度", 0); setVar("档位", 0); setVar("车门", 0); setVar("剩余里程", 2);
  await frames(2);
  if (num(getVar("运行状态")) !== 1) bad.push("末站未进入停站状态: " + getVar("运行状态"));
  broadcast("开门"); await stepN(2);
  broadcast("关门"); await stepN(2);
  snap.终点_运行状态 = num(getVar("运行状态"));
  snap.终点_完成数 = num(getVar("完成数"));
  if (snap.终点_运行状态 !== 3) bad.push("末站关门后应进入结算状态 3: " + snap.终点_运行状态);
  if (snap.终点_完成数 !== 5) bad.push("完成数应为 5: " + snap.终点_完成数);

  console.log(JSON.stringify({ actual: snap, bad }, null, 2));
  if (bad.length) { console.error("METRO_DRIVE_LOGIC_FAIL " + bad.join("; ")); process.exit(1); }
  console.log("METRO_DRIVE_LOGIC_OK");
})().catch((e) => { console.error("METRO_DRIVE_CHECK_FAIL", e && (e.stack || e)); process.exit(1); });
