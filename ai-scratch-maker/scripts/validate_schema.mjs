// 用官方 sb3 JSON Schema 校验 project.json
//
// 用法：node validate_schema.mjs <project.json> [--schema <sb3_schema.json>]
// 缺省 schema 指向 reference/scratch-sources/scratch-parser/lib/sb3_schema.json
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { findScratchVM } from './scratch_vm_path.mjs'

const require = createRequire(import.meta.url)
const HERE = path.dirname(fileURLToPath(import.meta.url))

const argv = process.argv.slice(2)
const arg = (n, d) => {
  const i = argv.indexOf(n)
  return i >= 0 && argv[i + 1] ? argv[i + 1] : d
}

const projPath = argv.find((a) => !a.startsWith('--') && argv[argv.indexOf(a) - 1] !== '--schema')
if (!projPath) {
  console.error('用法: node validate_schema.mjs <project.json> [--schema <path>]')
  process.exit(2)
}

const schemaPath = arg('--schema')
const defsPath = schemaPath
  ? path.join(path.dirname(schemaPath), 'sb3_definitions.json')
  : null

// ajv 的位置：优先与 scratch-vm 同级，其次本地 node_modules，最后全局 require
const RUNTIME = findScratchVM()
const AJV_CANDIDATES = [
  RUNTIME ? path.join(path.dirname(RUNTIME), 'ajv') : null,
  path.resolve(HERE, '..', 'node_modules', 'ajv'),
  path.resolve(process.cwd(), 'node_modules', 'ajv'),
].filter(Boolean)

let Ajv
for (const dir of AJV_CANDIDATES) {
  try { Ajv = require(dir); break } catch (e) { /* try next */ }
}
if (!Ajv) {
  try {
    Ajv = require('ajv')
  } catch (e2) {
    console.error('SKIP_SCHEMA 未找到 ajv，跳过官方 schema 校验\n  已尝试：\n    ' + AJV_CANDIDATES.join('\n    '))
    process.exit(0)
  }
}
if (Ajv && Ajv.default) Ajv = Ajv.default

let schema
let defs
if (schemaPath) {
  schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'))
  defs = JSON.parse(fs.readFileSync(defsPath, 'utf8'))
} else {
  // 按优先级探测 schema 目录，保证 skill 被安装到任意位置后都能工作：
  //   1) 环境变量 SB3_SCHEMA_DIR
  //   2) skill 内置 references/sb3-schema（随 skill 分发）
  //   3) 脚本相对路径 ../references/sb3-schema
  //   4) 旧的项目内布局 ../reference/scratch-sources/scratch-parser/lib
  const here = path.dirname(fileURLToPath(import.meta.url))
  const candidates = [
    process.env.SB3_SCHEMA_DIR,
    path.resolve(here, '..', 'references', 'sb3-schema'),
    path.resolve(here, '..', 'reference', 'scratch-sources', 'scratch-parser', 'lib'),
    path.resolve(process.cwd(), '..', 'reference', 'scratch-sources', 'scratch-parser', 'lib'),
    path.resolve(process.cwd(), 'references', 'sb3-schema'),
  ].filter(Boolean)

  let base = null
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, 'sb3_schema.json'))) { base = c; break }
  }
  if (!base) {
    console.error('SCHEMA_SKIP 找不到 sb3_schema.json，已尝试：\n  ' + candidates.join('\n  '))
    console.error('  可用 --schema <path> 或设置 SB3_SCHEMA_DIR 显式指定')
    process.exit(0)
  }
  schema = JSON.parse(fs.readFileSync(path.join(base, 'sb3_schema.json'), 'utf8'))
  defs = JSON.parse(fs.readFileSync(path.join(base, 'sb3_definitions.json'), 'utf8'))
}

const ajv = new Ajv({ allErrors: true, schemaId: 'auto', unknownFormats: 'ignore' })
ajv.addSchema(defs, 'sb3_definitions.json')

const validate = ajv.compile(schema)
const project = JSON.parse(fs.readFileSync(projPath, 'utf8'))

if (validate(project)) {
  console.log('SCHEMA_OK ' + projPath)
  process.exit(0)
} else {
  console.error('SCHEMA_FAIL ' + projPath)
  for (const e of validate.errors.slice(0, 25)) {
    console.error('  ' + (e.dataPath || '/') + ' ' + e.message)
  }
  process.exit(1)
}
