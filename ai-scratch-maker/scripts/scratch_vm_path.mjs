// 统一的 scratch-vm / scratch-parser 定位器（供各校验脚本复用）。
//
// 定位顺序：
//   1) 环境变量 SCRATCH_VM_PATH / SCRATCH_PARSER_PATH（显式指定优先）
//   2) skill 内置 node_modules（若随包分发）
//   3) 当前工作目录 node_modules
//   4) 本机常见位置（~/.workbuddy/sb3_poc_runtime 等）
//
// 设计要点：**不写死任何绝对路径**。找不到时返回 null，由调用方
// 打印 SKIP_* 提示并以 0 退出（跳过），而不是抛 Node 堆栈把流程打断。
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(HERE, "..");

export function candidates() {
  return [
    process.env.SCRATCH_VM_PATH,
    path.join(SKILL_ROOT, "node_modules", "scratch-vm"),
    path.resolve(process.cwd(), "node_modules", "scratch-vm"),
    path.join(os.homedir(), ".workbuddy", "sb3_poc_runtime", "node_modules", "scratch-vm"),
    path.join(os.homedir(), "sb3_poc_runtime", "node_modules", "scratch-vm"),
  ].filter(Boolean);
}

export function findScratchVM() {
  for (const c of candidates()) {
    try { if (fs.existsSync(c)) return c; } catch { /* ignore */ }
  }
  return null;
}

/** scratch-parser 通常与 scratch-vm 同级安装。 */
export function findScratchParser(vmPath) {
  if (process.env.SCRATCH_PARSER_PATH) return process.env.SCRATCH_PARSER_PATH;
  if (!vmPath) return null;
  const p = path.join(path.dirname(vmPath), "scratch-parser");
  try { if (fs.existsSync(p)) return p; } catch { /* ignore */ }
  return null;
}

export function loadScratchVM(vmPath) {
  const mod = require(vmPath);
  return mod.VirtualMachine || mod.default || mod;
}

export function skipMessage(tag, hint) {
  return (
    `${tag} 未找到 scratch-vm，跳过相关校验。\n` +
    `  已尝试：\n    ${candidates().join("\n    ")}\n` +
    `  ${hint || "安装：npm i scratch-vm，或用 SCRATCH_VM_PATH 指向已有安装。"}`
  );
}
