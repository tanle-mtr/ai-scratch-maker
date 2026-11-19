// 行为验证：新技巧是否真的生效
//  0) 绿旗阶段：署名卡可见、黑暗已放大到 250%、火花本体隐藏
//  1) 视野阴影：黑暗角色与猫同屏，且层级在猫之上
//  2) 帮助弹窗：广播「打开帮助」-> 面板/遮罩/× 显示，面板开=1
//  3) 当关闭被点击：点 × -> 全部隐藏，面板开=0
//  4) 克隆粒子：广播「抓到啦」-> 火花产生克隆体，且各克隆速度独立
import fs from "node:fs";
import { createRequire } from "node:module";
import { findScratchVM, loadScratchVM, skipMessage } from "./scratch_vm_path.mjs";
const require = createRequire(import.meta.url);
const vmPath = findScratchVM();
if (!vmPath) {
  console.error(skipMessage("SKIP_VERIFY"));
  process.exit(0);
}
let VirtualMachine;
try {
  VirtualMachine = loadScratchVM(vmPath);
} catch (e) {
  console.error("SKIP_VERIFY 加载 scratch-vm 失败：" + (e && e.message));
  process.exit(0);
}
const sb3Path = process.argv[2];

const nm = (t) => (t.sprite && t.sprite.name) || t.name || "?";
const getVar = (rt, n) => {
  for (const t of rt.targets) for (const id of Object.keys(t.variables || {})) {
    const v = t.variables[id]; if (v && v.name === n) return v;
  } return null;
};
const find = (rt, n) => rt.targets.find((t) => !t.isStage && nm(t) === n);

// 把某个角色的积木链拍平成 [{opcode, field, num}]，用于结构级断言
// 运行时里 inputs 是 {name, block, shadow}，字面量/下拉值都在影子积木上，
// 所以要顺着 shadow 找 math_number 的 NUM / 菜单积木的字段。
function blocksOf(target) {
  const seq = [];
  if (!target || !target.blocks) return { seq };
  const bl = target.blocks._blocks || {};

  const fieldOf = (id) => {
    const b = bl[id];
    if (!b) return null;
    for (const k of Object.keys(b.fields || {})) {
      const fv = b.fields[k];
      const v = (fv && fv.value != null) ? fv.value : (Array.isArray(fv) ? fv[0] : null);
      if (v != null) return v;
    }
    return null;
  };
  const numOf = (id) => {
    const b = bl[id];
    if (!b) return null;
    const v = fieldOf(id);
    return v == null ? null : Number(v);
  };

  const walk = (id) => {
    let cur = id;
    while (cur && bl[cur]) {
      const b = bl[cur];
      const inp = b.inputs || {};
      let field = null, num = null;
      for (const k of Object.keys(inp)) {
        const spec = inp[k];
        const sh = spec && spec.shadow;
        if (!sh) continue;
        const shBlock = bl[sh];
        if (!shBlock) continue;
        if (shBlock.opcode === "math_number") { if (num == null) num = numOf(sh); }
        else if (!/^math_/.test(shBlock.opcode)) { if (field == null) field = fieldOf(sh); }
      }
      seq.push({ opcode: b.opcode, field, num });
      // 递归子栈
      for (const k of Object.keys(inp)) {
        if (/substack/i.test(k) && inp[k] && inp[k].block) walk(inp[k].block);
      }
      cur = b.next;
    }
  };
  for (const id of target.blocks._scripts || []) walk(id);
  return { seq };
}

// 层级：runtime.targets 的下标越大越靠前
const layerOf = (rt, n) => rt.targets.findIndex((t) => !t.isStage && nm(t) === n);

// ---- 无头环境没有渲染器，isTouchingSprite 会抛错 → 用包围盒近似打补丁 ----
// 家具是大件，用各自的半宽当半径，否则「猫靠近沙发」会被误判成没碰撞。
const HIT_RADIUS = { "沙发": 90, "柜子": 90, "书桌": 100, "地毯": 100 };
function patchCollision(runtime, hitRadius = 45) {
  const target = runtime.targets.find((t) => !t.isStage);
  if (!target) return;
  const proto = Object.getPrototypeOf(target);
  proto.isTouchingSprite = function (spriteName) {
    const other = runtime.getSpriteTargetByName(String(spriteName));
    if (!other) return false;
    const otherName = (other.sprite && other.sprite.name) || other.name || "";
    const r = HIT_RADIUS[otherName] ?? hitRadius;
    return Math.abs(other.x - this.x) < r && Math.abs(other.y - this.y) < r;
  };
}

const log = [];
let failures = 0;
const check = (label, ok, extra) => {
  log.push((ok ? "  [ok] " : "  [FAIL] ") + label + (extra ? "  -> " + extra : ""));
  if (!ok) failures++;
};

(async () => {
  const vm = new VirtualMachine();
  const buf = fs.readFileSync(sb3Path);
  await vm.loadProject(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  const rt = vm.runtime;
  vm.runtime.currentStepTime = 1000 / 30;
  vm.setTurboMode(true);
  patchCollision(rt);
  // 本脚本是「猫抓老鼠」专属技巧验证（署名/黑暗/火花/猫/家具等角色硬编码）。
  // 若目标作品不是猫抓老鼠（缺少签名角色），直接跳过，避免对非本作品误报甚至崩溃
  //（例如 getVar(rt,"game_state").value 在其它作品里会因变量不存在而 null.value 抛错）。
  if (!(find(rt, "猫") && find(rt, "黑暗") && find(rt, "火花"))) {
    console.error(skipMessage("SKIP_VERIFY"));
    process.exit(0);
  }
  const step = async (n) => { for (let i = 0; i < n; i++) { rt._step(); await new Promise((r) => setTimeout(r, 1000 / 120)); } };
  const clickSprite = (name) => {
    const t = find(rt, name);
    if (t) rt.startHats("event_whenthisspriteclicked", {}, t);
    return !!t;
  };
  const broadcast = (msg) => rt.startHats("event_whenbroadcastreceived", { BROADCAST_OPTION: msg });

  // ---- 0. 绿旗阶段 ----
  log.push("== 0. 绿旗阶段（首页）==");
  vm.greenFlag();
  await step(20);
  const byline = find(rt, "署名");
  const dark = find(rt, "黑暗");
  const spark = find(rt, "火花");
  const cat = find(rt, "猫");
  check("署名卡在首页可见（防搬署名）", byline && byline.visible);
  // ⚠️ 无头 VM 没有渲染器，RenderedTarget.setSize 的赋值在 if(this.renderer) 里，
  //    所以无头环境**看不到** size 变化（编辑器里会按「当前造型」正常夹紧）。
  //    这里改为校验「先切小造型再设 size」的积木结构是否正确。
  const darkBlocks = blocksOf(dark);
  check("黑幕结构：先切「点」→ 设 size 250 → 再切回「暗」（绕 150% 上限）",
    darkBlocks.seq.some((o) => o.opcode === "looks_switchcostumeto" && o.field === "点") &&
    darkBlocks.seq.some((o) => o.opcode === "looks_setsizeto" && o.num === 250) &&
    darkBlocks.seq.some((o) => o.opcode === "looks_switchcostumeto" && o.field === "暗"),
    JSON.stringify(darkBlocks.seq.filter((o) => o.opcode.startsWith("looks_"))));
  check("黑幕当前造型是「暗」", dark && dark.getCostumes()[dark.currentCostume].name === "暗",
    dark && dark.getCostumes()[dark.currentCostume].name);
  check("火花本体隐藏（只当粒子工厂）", spark && spark.visible === false);
  check("首页时猫是隐藏的", cat && cat.visible === false);

  // ---- 1. 进入游戏 ----
  log.push("== 1. 点击开始按钮进入游戏 ==");
  check("找到开始按钮", clickSprite("开始按钮"));
  await step(30);
  check("game_state=1（游戏中）", getVar(rt, "game_state").value == 1, "=" + getVar(rt, "game_state").value);
  check("猫显示出来了", cat && cat.visible === true);
  check("黑幕覆盖在猫之上（层级更高）", layerOf(rt, "黑暗") > layerOf(rt, "猫"),
    "黑暗层=" + layerOf(rt, "黑暗") + " 猫层=" + layerOf(rt, "猫"));
  check("透明洞跟着猫走（同屏）", dark && cat && Math.abs(dark.x - cat.x) < 12 && Math.abs(dark.y - cat.y) < 12,
    "dark=(" + Math.round(dark.x) + "," + Math.round(dark.y) + ") cat=(" + Math.round(cat.x) + "," + Math.round(cat.y) + ")");
  check("小地图在黑幕之上（UI 不被盖黑）", layerOf(rt, "小地图") > layerOf(rt, "黑暗"),
    "小地图层=" + layerOf(rt, "小地图") + " 黑暗层=" + layerOf(rt, "黑暗"));
  check("署名卡在游戏中隐藏", byline && byline.visible === false);

  // ---- 2. 帮助弹窗 ----
  log.push("== 2. 帮助弹窗（遮罩 + 面板 + 关闭按钮）==");
  const panel = find(rt, "帮助面板"), mask = find(rt, "弹窗遮罩"), xbtn = find(rt, "关闭按钮");
  check("面板/遮罩/× 三个角色都存在", !!(panel && mask && xbtn));
  broadcast("打开帮助");
  await step(12);
  check("打开后：面板显示", panel.visible);
  check("打开后：遮罩显示（拦截穿透点击）", mask.visible);
  check("打开后：× 显示", xbtn.visible);
  check("打开后：面板开=1", getVar(rt, "面板开").value == 1, "面板开=" + getVar(rt, "面板开").value);

  // ---- 3. 当关闭被点击 ----
  log.push("== 3. 当关闭被点击（点右上角 ×）==");
  check("找到关闭按钮并触发点击", clickSprite("关闭按钮"));
  await step(12);
  check("点 × 后：面板隐藏", !panel.visible);
  check("点 × 后：遮罩隐藏", !mask.visible);
  check("点 × 后：× 隐藏", !xbtn.visible);
  check("点 × 后：面板开=0", getVar(rt, "面板开").value == 0, "面板开=" + getVar(rt, "面板开").value);

  // ---- 4. 家具碰撞箱 ----
  log.push("== 4. 家具碰撞箱（背景图里的家具挡不住人，必须做成独立角色）==");
  const FURN = ["沙发", "柜子", "书桌", "地毯"];
  const furnTargets = FURN.map((n) => find(rt, n));
  check("4 件家具都是独立角色", furnTargets.every(Boolean),
    "缺=" + FURN.filter((n, i) => !furnTargets[i]).join(",") || "无");
  check("游戏中家具可见", furnTargets.every((t) => t && t.visible));
  // 家具要跟着相机滚动：屏幕位置 = 世界坐标 - 相机
  const camX = getVar(rt, "camera_x").value, camY = getVar(rt, "camera_y").value;
  const sofa = furnTargets[0];
  const sofaWorldX = -270, sofaWorldY = 190;
  check("家具跟着相机滚动（屏幕位置 = 世界 - 相机）",
    Math.abs(sofa.x - (sofaWorldX - camX)) < 2 && Math.abs(sofa.y - (sofaWorldY - camY)) < 2,
    "沙发屏幕=(" + Math.round(sofa.x) + "," + Math.round(sofa.y) + ") 期望=(" +
    Math.round(sofaWorldX - camX) + "," + Math.round(sofaWorldY - camY) + ")");
  // 猫撞上沙发时应该被挡住（位置退回、速度清零）
  const catW = getVar(rt, "cat_wx"), catH = getVar(rt, "cat_wy");
  const catV = find(rt, "猫");
  catW.value = sofaWorldX; catH.value = sofaWorldY;   // 把猫放到沙发正中心
  const vxVar = Object.values(catV.variables || {}).find((v) => v && v.name === "cat_vx");
  if (vxVar) vxVar.value = 12;                       // 给一个向右的速度
  await step(6);
  check("猫撞到家具后被挡住（退回原位）",
    Math.abs(catW.value - sofaWorldX) < 1.5 && Math.abs(catH.value - sofaWorldY) < 1.5,
    "cat_w=(" + catW.value.toFixed(1) + "," + catH.value.toFixed(1) + ") 沙发=(" + sofaWorldX + "," + sofaWorldY + ")");
  check("撞墙后水平速度被清零（不会贴着墙持续加速）", vxVar && Math.abs(vxVar.value) < 0.01,
    "cat_vx=" + (vxVar && vxVar.value));
  // 远离家具时应该能正常移动
  catW.value = 0; catH.value = 0;
  if (vxVar) vxVar.value = 12;
  await step(6);
  check("空旷处能正常移动（碰撞不会误挡）", catW.value > 1, "cat_wx=" + catW.value.toFixed(1));

  // ---- 5. 克隆粒子 ----
  log.push("== 4. 克隆粒子系统（结构级 + 触发级）==");
  const sb = blocksOf(spark);
  check("有「当作为克隆体启动」帽子", sb.seq.some((o) => o.opcode === "control_start_as_clone"));
  check("有「创建克隆体」积木", sb.seq.some((o) => o.opcode === "control_create_clone_of"));
  check("有「删除此克隆体」积木", sb.seq.some((o) => o.opcode === "control_delete_this_clone"));
  check("粒子循环次数正确（不是 0）", sb.seq.some((o) => o.opcode === "control_repeat" && o.num === 16),
    "repeat TIMES=" + sb.seq.filter((o) => o.opcode === "control_repeat").map((o) => o.num).join(","));
  check("生成数量正确（10 个）", sb.seq.some((o) => o.opcode === "control_repeat" && o.num === 10),
    "repeat TIMES=" + sb.seq.filter((o) => o.opcode === "control_repeat").map((o) => o.num).join(","));
  // 私有变量必须是角色级（sprite 级）才每个克隆各一份
  const sparkVars = Object.values(spark.variables || {}).filter((v) => v && v.type !== "broadcast_msg");
  const localNames = sparkVars.map((v) => v.name);
  check("vx/vy 是角色级私有变量（每个克隆各一份）",
    localNames.includes("vx") && localNames.includes("vy"), "变量=" + localNames.join(","));
  // 行为级：广播后脚本确实被触发（火花会跳到老鼠当时所在的位置）
  const mouse = find(rt, "老鼠");
  const mouseAt = { x: mouse.x, y: mouse.y };      // 先记下广播瞬间的位置（老鼠之后还会继续跑）
  const before = { x: spark.x, y: spark.y };
  broadcast("抓到啦");
  await step(20);
  check("广播「抓到啦」后脚本被触发（火花移到老鼠处）",
    Math.abs(spark.x - mouseAt.x) < 3 && Math.abs(spark.y - mouseAt.y) < 3,
    "火花=(" + Math.round(spark.x) + "," + Math.round(spark.y) + ") 老鼠当时=(" +
    Math.round(mouseAt.x) + "," + Math.round(mouseAt.y) + ") 之前=(" + Math.round(before.x) + "," + Math.round(before.y) + ")");

  log.push("");
  log.push(failures === 0 ? "ALL_NEW_TECH_OK" : "NEW_TECH_FAIL " + failures);
  fs.writeFileSync(process.argv[3], log.join("\n"), "utf8");
  vm.stopAll();
  process.exit(failures === 0 ? 0 : 1);
})().catch((e) => {
  fs.writeFileSync(process.argv[3], "DIAG_ERROR " + (e && (e.stack || e)), "utf8");
  process.exit(1);
});
