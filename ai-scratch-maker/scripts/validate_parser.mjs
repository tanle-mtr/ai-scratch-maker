// 用官方 scratch-parser 校验 .sb3 是否能被「打开」（最贴近编辑器的检查）。
//
// 为什么单独做：Scratch 编辑器打开项目时走的就是 scratch-parser 的 validate()。
// 若项目结构非法，parser 会拒绝并回退到 SB1 解析，于是报出
// "Non-ascii character in FixedAsciiString" 这种**看似无关**的错。
// 这里直接调 parser 的 validate()，能第一时间判断「编辑器能不能打开」。
//
// 用法: node validate_parser.mjs <作品.sb3>
import fs from "node:fs";
import { createRequire } from "node:module";
import { findScratchVM, findScratchParser } from "./scratch_vm_path.mjs";

const require = createRequire(import.meta.url);

const RUNTIME = findScratchVM();
const PARSER = findScratchParser(RUNTIME);

const sb3Path = process.argv[2];
if (!sb3Path) {
  console.error("用法: node validate_parser.mjs <作品.sb3>");
  process.exit(2);
}

let validate;
try {
  const parser = require(PARSER);
  // scratch-parser 的主导出就是 validate(input, isSprite, callback)
  validate = typeof parser === "function" ? parser
    : (parser.validate || (parser.default && (parser.default.validate || parser.default)));
} catch (e) {
  console.error("SKIP_PARSER 未找到 scratch-parser，跳过");
  process.exit(0);
}
if (!validate) {
  console.error("SKIP_PARSER scratch-parser 没有 validate()");
  process.exit(0);
}

const buf = fs.readFileSync(sb3Path);

validate(buf, false, (err, res) => {
  if (err) {
    console.error("PARSER_FAIL " + sb3Path);
    console.error("  " + (err.message || err));
    if (err.sb2Errors) console.error("  sb2: " + JSON.stringify(err.sb2Errors).slice(0, 300));
    if (err.sb3Errors) console.error("  sb3: " + JSON.stringify(err.sb3Errors).slice(0, 600));
    process.exit(1);
  }
  const targets = (res && res[0] && res[0].targets) || [];
  console.log("PARSER_OK " + sb3Path + "  targets=" + targets.length);
  process.exit(0);
});
