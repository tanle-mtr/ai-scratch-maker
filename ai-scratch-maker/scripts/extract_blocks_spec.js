#!/usr/bin/env node
/**
 * 从 Scratch 官方源码抽取「全部积木」的机器可读规范 -> references/blocks-spec.json
 *
 * 数据来源（3 个权威源）：
 *   1. scratch-blocks/src/blocks/*.ts        —— 积木形状、输入名、字段名、下拉菜单选项
 *   2. scratch-vm/src/blocks/scratch3_*.js    —— 运行时原语；用 Cast.to*(args.X) 推断输入原始类型
 *   3. scratch-vm 的 src/extensions 下各扩展    —— 扩展积木（画笔/音乐/翻译/语音…）的 opcode 与参数类型
 *
 * 交叉校验：scratch-vm 运行时支持的全部原语必须被收录 —— 这是「不漏积木」的硬保证。
 *
 * 用法：
 *   node scripts/extract_blocks_spec.js \
 *     --scratch-blocks ../reference/scratch-sources/scratch-blocks \
 *     --scratch-vm     ../reference/scratch-sources/scratch-vm \
 *     --aliases        references/blocks-aliases.json \
 *     --out            references/blocks-spec.json
 */
'use strict';

const fs = require('fs');
const path = require('path');

/* ================================================================== *
 * 迷你 JS 字面量解析器
 * ================================================================== */
function skipWs(src, i) {
  for (;;) {
    while (i < src.length && ' \t\n\r'.indexOf(src[i]) >= 0) i++;
    if (src[i] === '/' && src[i + 1] === '/') {
      while (i < src.length && src[i] !== '\n') i++;
      continue;
    }
    if (src[i] === '/' && src[i + 1] === '*') {
      i += 2;
      while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) i++;
      i += 2;
      continue;
    }
    return i;
  }
}

function parseString(src, i) {
  const quote = src[i];
  i++;
  let out = '';
  while (i < src.length) {
    const c = src[i];
    if (c === '\\') {
      const n = src[i + 1];
      const map = { n: '\n', t: '\t', r: '\r', '\\': '\\', "'": "'", '"': '"', '`': '`', '\n': '' };
      out += map[n] !== undefined ? map[n] : n;
      i += 2;
      continue;
    }
    if (c === quote) { i++; return [out, i]; }
    out += c;
    i++;
  }
  return [out, i];
}

// 跳到同深度的 ',' / '}' / ']'（用于 `a.path + 'literal'` 这类拼接表达式）
function skipOpaque(src, i) {
  let depth = 0;
  while (i < src.length) {
    const c = src[i];
    if (c === '(' || c === '[' || c === '{') { depth++; i++; continue; }
    if (c === ')' || c === ']' || c === '}') {
      if (depth === 0) return i;
      depth--; i++; continue;
    }
    if (c === '"' || c === "'" || c === '`') { [, i] = parseString(src, i); continue; }
    if (c === '/' && src[i + 1] === '/') { while (i < src.length && src[i] !== '\n') i++; continue; }
    if (c === ',' && depth === 0) return i;
    i++;
  }
  return i;
}

const IDENT_RE = /^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*/;

function parseValue(src, i) {
  i = skipWs(src, i);
  const c = src[i];
  if (c === '{') return parseObject(src, i);
  if (c === '[') return parseArray(src, i);
  if (c === '"' || c === "'" || c === '`') return parseString(src, i);
  if (c === '-' || (c >= '0' && c <= '9')) {
    const m = /^-?\d+(\.\d+)?([eE][-+]?\d+)?/.exec(src.slice(i));
    return [Number(m[0]), i + m[0].length];
  }
  const m = IDENT_RE.exec(src.slice(i));
  if (m) {
    let j = i + m[0].length;
    const nx = skipWs(src, j);
    if (src[nx] === '(') {
      let k = skipWs(src, nx + 1);
      const args = [];
      if (src[k] !== ')') {
        for (;;) {
          let v;
          [v, k] = parseValue(src, k);
          args.push(v);
          k = skipWs(src, k);
          if (src[k] === ',') { k++; continue; }
          break;
        }
      }
      k = skipWs(src, k);
      if (src[k] === ')') k++;
      return [{ __call: m[0], args }, k];
    }
    return [{ __ident: m[0] }, j];
  }
  return [null, i + 1];
}

function parseObject(src, i) {
  i++;
  const obj = {};
  for (;;) {
    i = skipWs(src, i);
    if (i >= src.length) return [obj, i];
    if (src[i] === '}') return [obj, i + 1];
    if (src[i] === ',') { i++; continue; }
    let key;
    if (src[i] === '"' || src[i] === "'") { [key, i] = parseString(src, i); }
    else {
      const m = /^[A-Za-z_$][\w$]*/.exec(src.slice(i));
      if (!m) { i = skipOpaque(src, i); continue; }
      key = m[0];
      i += m[0].length;
    }
    i = skipWs(src, i);
    if (src[i] === ':') i++;
    let val;
    [val, i] = parseValue(src, i);
    const after = skipWs(src, i);
    if (src[after] !== ',' && src[after] !== '}' && src[after] !== ']' && after < src.length) {
      i = skipOpaque(src, after);
    }
    obj[key] = val;
  }
}

function parseArray(src, i) {
  i++;
  const arr = [];
  for (;;) {
    i = skipWs(src, i);
    if (i >= src.length) return [arr, i];
    if (src[i] === ']') return [arr, i + 1];
    if (src[i] === ',') { i++; continue; }
    let val;
    [val, i] = parseValue(src, i);
    const after = skipWs(src, i);
    if (src[after] !== ',' && src[after] !== ']' && after < src.length) i = skipOpaque(src, after);
    arr.push(val);
  }
}

/* ================================================================== *
 * 辅助
 * ================================================================== */
const identText = (v) => {
  if (v && typeof v === 'object' && '__ident' in v) return v.__ident;
  if (v && typeof v === 'object' && '__call' in v) {
    const a = v.args && v.args[0];
    if (a && typeof a === 'object' && !Array.isArray(a) && 'default' in a) return a.default;
    return v.__call;
  }
  if (typeof v === 'string') return v;
  if (v === null || v === undefined) return '';
  return String(v);
};
const lastSeg = (s) => String(s).split('.').pop();
const isIdent = (v) => !!(v && typeof v === 'object' && '__ident' in v);

/* ================================================================== *
 * 1. scratch-blocks
 * ================================================================== */
const CATEGORY_BY_FILE = {
  'event.ts': 'events', 'control.ts': 'control', 'motion.ts': 'motion',
  'looks.ts': 'looks', 'sound.ts': 'sound', 'sensing.ts': 'sensing',
  'operators.ts': 'operators', 'math.ts': 'operators', 'text.ts': 'operators',
  'note.ts': 'sound', 'matrix.ts': 'operators', 'colour.ts': 'looks',
  'data.ts': 'data', 'procedures.ts': 'procedures',
};

const SHAPE_BY_EXT = {
  shape_hat: 'hat', shape_bowler_hat: 'hat', shape_statement: 'command',
  shape_reporter: 'reporter', shape_boolean: 'boolean',
  shape_boolean_modifier: 'boolean', shape_end: 'command',
  output_number: 'reporter', output_string: 'reporter', output_boolean: 'boolean',
};

// 动态下拉菜单（sb3 里存成 inputs 的裸字符串 [1,"值"]）
// 注意：event_whenkeypressed 的 KEY_OPTION 在 scratch-blocks 里是 field_dropdown，
// 会自动走「字段」分支；sensing_keypressed 的同名参数是 input_value，走本表。
const DYNAMIC_MENU_INPUTS = new Set([
  'BACKDROP', 'CLONE_OPTION', 'COSTUME', 'DISTANCETOMENU', 'KEY_OPTION',
  'OPERATOR', 'SOUND_MENU', 'TO', 'TOUCHINGOBJECTMENU', 'TOWARDS',
]);

// 编辑器内部积木，不属于 Scratch 积木集
const HELPER_BLOCKS = new Set([
  'argument_editor_boolean', 'argument_editor_string_number',
  'colour_picker', 'matrix', 'note', 'text',
  'data_listindexall', 'data_listindexrandom',
  'sensing_keyoptions', 'sensing_online', 'sensing_userid',
  'looks_hideallsprites', 'looks_changestretchby', 'looks_setstretchto',
  'math_angle', 'math_integer', 'math_number', 'math_positive_number', 'math_whole_number',
  'motion_align_scene', 'motion_scroll_right', 'motion_scroll_up', 'motion_xscroll', 'motion_yscroll',
]);

// 下拉菜单「影子积木」：sb3 里作为 shadow 存在，需要登记
const MENU_SOURCE_BLOCKS = {
  event_broadcast_menu: { field: 'BROADCAST_OPTION' },
  event_touchingobjectmenu: { field: 'TOUCHINGOBJECTMENU' },
  motion_goto_menu: { field: 'TO' },
  motion_pointtowards_menu: { field: 'TOWARDS' },
  motion_glideto_menu: { field: 'TO' },
  sensing_touchingobjectmenu: { field: 'TOUCHINGOBJECTMENU' },
  sensing_distancetomenu: { field: 'DISTANCETOMENU' },
  sensing_of_object_menu: { field: 'OBJECT' },
  control_create_clone_of_menu: { field: 'CLONE_OPTION' },
  sound_sounds_menu: { field: 'SOUND_MENU' },
  sound_beats_menu: { field: 'BEATS' },
  sound_effects_menu: { field: 'EFFECT' },
  looks_costume: { field: 'COSTUME' },
  looks_backdrops: { field: 'BACKDROP' },
};

// 「动态下拉」输入在 sb3 里必须指向一个 shadow 积木（而不是裸字符串）。
// 运行时反序列化时，字符串会被当成「块 id」去找，找不到就是 null，
// 脚本一执行就崩。所以这里记录 每个积木的哪个输入 用哪个影子积木。
const MENU_INPUT_REFS = {
  'motion_goto': { TO: 'motion_goto_menu' },
  'motion_glideto': { TO: 'motion_glideto_menu' },
  'motion_pointtowards': { TOWARDS: 'motion_pointtowards_menu' },
  'looks_switchcostumeto': { COSTUME: 'looks_costume' },
  'looks_switchbackdropto': { BACKDROP: 'looks_backdrops' },
  'looks_switchbackdroptoandwait': { BACKDROP: 'looks_backdrops' },
  'sound_play': { SOUND_MENU: 'sound_sounds_menu' },
  'sound_playuntildone': { SOUND_MENU: 'sound_sounds_menu' },
  'sound_soundsuntil': { SOUND_MENU: 'sound_sounds_menu' },
  'sensing_touchingobject': { TOUCHINGOBJECTMENU: 'sensing_touchingobjectmenu' },
  'sensing_distanceto': { DISTANCETOMENU: 'sensing_distancetomenu' },
  'control_create_clone_of': { CLONE_OPTION: 'control_create_clone_of_menu' },
  'control_start_as_clone': { CLONE_OPTION: 'control_create_clone_of_menu' },
  'sensing_of': { OBJECT: 'sensing_of_object_menu' },
};

// 手工补齐：由 scratch-gui 动态生成、scratch-blocks 里只有空壳的积木
const MANUAL_BLOCKS = {
  event_whenbackdropswitchesto: {
    category: 'events', shape: 'hat',
    inputs: {}, fields: { BACKDROP: { type: 'menu' } },
  },
  control_start_as_clone: {
    category: 'control', shape: 'hat',
    inputs: { CLONE_OPTION: { type: 'menu' } }, fields: {},
  },
  sensing_of: {
    category: 'sensing', shape: 'reporter',
    inputs: { OBJECT: { type: 'menu' }, PROPERTY: { type: 'value' } }, fields: {},
  },
  control_stop: {
    category: 'control', shape: 'command',
    inputs: {},
    fields: {
      STOP_OPTION: {
        type: 'menu',
        options: [['全部脚本', 'all'], ['这个脚本', 'this script'], ['其他脚本', 'other scripts in sprite']],
      },
    },
  },
};

// 输入类型的手工修正（Cast 推断无法覆盖的语义）
const TYPE_OVERRIDES = {
  'looks_sayforsecs': { MESSAGE: 'text' },
  'looks_say': { MESSAGE: 'text' },
  'looks_think': { MESSAGE: 'text' },
  'looks_thinkforsecs': { MESSAGE: 'text' },
  'sensing_askandwait': { QUESTION: 'text' },
  'operator_join': { STRING1: 'text', STRING2: 'text' },
  'operator_letter_of': { LETTER: 'text' },
  'operator_contains': { STRING1: 'text', STRING2: 'text' },
  'data_addtolist': { ITEM: 'text' },
  'data_insertatlist': { ITEM: 'text' },
  'data_replaceitemoflist': { ITEM: 'text' },
  'data_listcontainsitem': { ITEM: 'text' },
  'data_deleteoflist': { INDEX: 'number' },
  'data_insertatlist': { INDEX: 'number' },
  'data_replaceitemoflist': { INDEX: 'number' },
  'data_itemoflist': { INDEX: 'number' },
  'motion_gotoxy': { X: 'number', Y: 'number' },
  'motion_glidesecstoxy': { SECS: 'number', X: 'number', Y: 'number' },
  'motion_glideto': { SECS: 'number' },
  'motion_setx': { X: 'number' },
  'motion_sety': { Y: 'number' },
  'motion_changexby': { DX: 'number' },
  'motion_changeyby': { DY: 'number' },
  'motion_turnright': { DEGREES: 'number' },
  'motion_turnleft': { DEGREES: 'number' },
  'motion_pointindirection': { DIRECTION: 'angle' },
  'looks_changesizeby': { CHANGE: 'number' },
  'looks_setsizeto': { SIZE: 'number' },
  'looks_changeeffectby': { CHANGE: 'number' },
  'looks_seteffectto': { VALUE: 'number' },
  'control_wait': { DURATION: 'number' },
  'control_repeat': { TIMES: 'number' },
  'control_if_else': { CONDITION: 'boolean' },
  'control_if': { CONDITION: 'boolean' },
  'control_repeat_until': { CONDITION: 'boolean' },
  'control_while': { CONDITION: 'boolean' },
  'control_wait_until': { CONDITION: 'boolean' },
  'sound_changevolumeby': { VOLUME: 'number' },
  'sound_setvolumeto': { VOLUME: 'number' },
  'sound_playuntildone': { SECS: 'number' },
  'looks_sayforsecs': { SECS: 'number' },
  'looks_thinkforsecs': { SECS: 'number' },
  'operator_random': { FROM: 'number', TO: 'number' },
  'operator_letter_of': { LETTER: 'text' },
  // 比较类运算的操作数接受任意值（scratch-vm 用 Cast.compare，不做布尔转换）
  'operator_gt': { OPERAND1: 'value', OPERAND2: 'value' },
  'operator_lt': { OPERAND1: 'value', OPERAND2: 'value' },
  'operator_equals': { OPERAND1: 'value', OPERAND2: 'value' },
  'sensing_of': { PROPERTY: 'value', OBJECT: 'menu' },
  // 广播：sb3 里是 [1,[11,名字,id]] 广播基元
  'event_broadcast': { BROADCAST_INPUT: 'broadcast' },
  'event_broadcastandwait': { BROADCAST_INPUT: 'broadcast' },
  // 列表字段修正
  'data_listcontents': { LIST: 'listfield' },
  'data_deletealloflist': { LIST: 'listfield' },
  'data_showlist': { LIST: 'listfield' },
  'data_hidelist': { LIST: 'listfield' },
  // 扩展积木的下拉
  'music_playDrumForBeats': { DRUM: 'menu' },
  'music_midiPlayDrumForBeats': { DRUM: 'menu' },
  'music_playNoteForBeats': { NOTE: 'menu' },
  'music_setInstrument': { INSTRUMENT: 'menu' },
  'music_midiSetInstrument': { INSTRUMENT: 'menu' },
  'text2speech_setVoice': { VOICE: 'menu' },
  'text2speech_setLanguage': { LANGUAGE: 'menu' },
  'translate_getTranslate': { LANGUAGE: 'menu' },
  'videoSensing_videoOn': { ATTRIBUTE: 'menu', SUBJECT: 'menu' },
  'videoSensing_setVideoTransparency': { ATTRIBUTE: 'menu', SUBJECT: 'menu' },
  'videoSensing_videoToggle': { ATTRIBUTE: 'menu', SUBJECT: 'menu' },
};

function extractFromScratchBlocks(sbRoot) {
  const blocksDir = path.join(sbRoot, 'src', 'blocks');
  const out = {};

  // 英文消息表：Blockly.Msg.KEY -> "move %1 steps"
  let msgTable = {};
  const msgPath = path.join(sbRoot, 'msg', 'json', 'en.json');
  if (fs.existsSync(msgPath)) {
    try { msgTable = JSON.parse(fs.readFileSync(msgPath, 'utf8')); } catch (e) { msgTable = {}; }
  }

  for (const file of fs.readdirSync(blocksDir)) {
    if (!file.endsWith('.ts')) continue;
    const src = fs.readFileSync(path.join(blocksDir, file), 'utf8');
    const category = CATEGORY_BY_FILE[file] || 'other';

    const re = /Blockly\.Blocks\.([A-Za-z0-9_]+)\s*=/g;
    let m;
    while ((m = re.exec(src)) !== null) {
      const opcode = m[1];
      if (HELPER_BLOCKS.has(opcode)) continue;
      const ji = src.indexOf('this.jsonInit(', m.index);
      if (ji < 0) continue;
      const nextDef = src.indexOf('Blockly.Blocks.', m.index + 10);
      if (nextDef >= 0 && ji > nextDef) continue;

      let init;
      try { [init] = parseObject(src, src.indexOf('{', ji)); } catch (e) { continue; }
      if (!init) continue;

      const exts = (init.extensions || []).map(identText);
      let shape = 'command';
      for (const e of exts) { if (SHAPE_BY_EXT[e]) { shape = SHAPE_BY_EXT[e]; break; } }

      // 积木显示文本（英文原文，来自官方消息表）
      let text = '';
      const m0 = init.message0;
      if (isIdent(m0)) {
        const key = lastSeg(identText(m0));
        if (msgTable[key]) text = msgTable[key];
      }

      const argList = [];
      for (const k of Object.keys(init)) {
        if (/^args\d+$/.test(k) && Array.isArray(init[k])) argList.push(...init[k]);
      }

      const inputs = {};
      const fields = {};
      for (const a of argList) {
        const atype = identText(a.type);
        const aname = identText(a.name);
        if (!aname) continue;

        if (atype === 'input_statement') { inputs[aname] = { type: 'substack' }; continue; }
        if (atype === 'field_label' || atype === 'field_image') continue;

        if (atype === 'field_dropdown') {
          const opts = [];
          for (const o of a.options || []) {
            if (Array.isArray(o) && o.length >= 2) opts.push([lastSeg(identText(o[0])), identText(o[1])]);
          }
          fields[aname] = { type: 'menu', options: opts };
          continue;
        }
        if (atype === 'field_numberdropdown') {
          const opts = [];
          for (const o of a.options || []) {
            if (Array.isArray(o) && o.length >= 2) opts.push([lastSeg(identText(o[0])), identText(o[1])]);
          }
          fields[aname] = { type: 'menu', options: opts };
          continue;
        }
        if (atype === 'field_variable' || atype === 'field_variable_getter') {
          // 广播 / 列表 / 标量 三种变量下拉要区分开
          const vtypes = (a.variableTypes || []).map(identText);
          const dtype = identText(a.defaultType);
          const avtype = identText(a.allowedVariableType);
          const kinds = vtypes.concat([dtype, avtype]).filter(Boolean);
          const isBroadcast = kinds.some((t) => /broadcast/i.test(t));
          const isList = kinds.some((t) => /list/i.test(t));
          if (isBroadcast) fields[aname] = { type: 'broadcast' };
          else if (isList) fields[aname] = { type: 'listfield' };
          else fields[aname] = { type: 'varfield' };
          continue;
        }
        if (atype === 'field_list') { fields[aname] = { type: 'listfield' }; continue; }
        if (atype === 'field_number') { inputs[aname] = { type: 'number' }; continue; }
        if (atype === 'field_angle') { inputs[aname] = { type: 'angle' }; continue; }
        if (atype === 'field_input' || atype === 'field_multiline') { inputs[aname] = { type: 'text' }; continue; }
        if (atype === 'input_value') {
          if (DYNAMIC_MENU_INPUTS.has(aname)) inputs[aname] = { type: 'menu' };
          else inputs[aname] = { type: 'value' };
          continue;
        }
      }

      out[opcode] = {
        opcode, category, shape, extension: null, inputs, fields,
        text,
        menu_inputs: MENU_INPUT_REFS[opcode] || undefined,
        source: 'scratch-blocks/src/blocks/' + file,
      };
    }
  }
  return out;
}

/* ================================================================== *
 * 2. scratch-vm 扩展积木
 * ================================================================== */
const EXT_ID_BY_DIR = {
  scratch3_pen: 'pen', scratch3_music: 'music', scratch3_text2speech: 'text2speech',
  scratch3_translate: 'translate', scratch3_video_sensing: 'videoSensing',
  scratch3_speech2text: 'speech2text',
};
const BLOCKTYPE_TO_SHAPE = {
  COMMAND: 'command', REPORTER: 'reporter', BOOLEAN: 'boolean',
  BUTTON: 'command', CONDITIONAL: 'boolean',
};
const ARG_TYPE_MAP = {
  ANGLE: 'angle', BOOLEAN: 'boolean', COLOR: 'color', NUMBER: 'number',
  STRING: 'text', MATRIX: 'text', COSTUME: 'menu', SOUND: 'menu',
  VARIABLE: 'varfield', LIST: 'listfield', BLOCK: 'value',
};

function extractFromExtensions(vmRoot) {
  const extDir = path.join(vmRoot, 'src', 'extensions');
  const out = {};
  for (const dir of fs.readdirSync(extDir)) {
    const extId = EXT_ID_BY_DIR[dir];
    if (!extId) continue;
    const file = path.join(extDir, dir, 'index.js');
    if (!fs.existsSync(file)) continue;
    const src = fs.readFileSync(file, 'utf8');
    const gi = src.indexOf('getInfo');
    if (gi < 0) continue;
    const bi = src.indexOf('blocks: [', gi);
    if (bi < 0) continue;
    let blocks;
    try { [blocks] = parseArray(src, src.indexOf('[', bi)); } catch (e) { continue; }
    if (!Array.isArray(blocks)) continue;

    for (const b of blocks) {
      if (!b || !b.opcode) continue;
      const opcode = extId + '_' + identText(b.opcode);
      const shape = BLOCKTYPE_TO_SHAPE[identText(b.blockType) || 'COMMAND'] || 'command';
      const inputs = {};
      const fields = {};
      for (const a of Object.keys(b.arguments || {})) {
        const adef = b.arguments[a];
        let kind = ARG_TYPE_MAP[identText(adef.type)] || 'text';
        // 带 menu 属性的参数在编辑器里是下拉菜单
        if (adef.menu) kind = 'menu';
        if (kind === 'varfield' || kind === 'listfield') fields[a] = { type: kind };
        else if (kind === 'menu') inputs[a] = { type: 'menu' };
        else if (kind === 'boolean') inputs[a] = { type: 'boolean' };
        else inputs[a] = { type: kind };
      }
      out[opcode] = {
        opcode, category: extId, shape, extension: extId, inputs, fields,
        text: identText(b.text),
        source: 'scratch-vm/src/extensions/' + dir + '/index.js',
      };
    }
  }
  return out;
}

/* ================================================================== *
 * 3. 运行时原语 + 输入类型推断
 * ================================================================== */
function extractRuntimeInfo(vmRoot) {
  const prims = new Set();
  const typeHints = {};
  const files = [];
  const bdir = path.join(vmRoot, 'src', 'blocks');
  for (const f of fs.readdirSync(bdir)) if (f.endsWith('.js')) files.push(path.join(bdir, f));

  for (const f of files) {
    const src = fs.readFileSync(f, 'utf8');
    const gp = src.indexOf('getPrimitives');
    if (gp < 0) continue;
    const region = src.slice(gp, gp + 20000);
    const re = /^[ \t]+([a-z][a-z0-9_]*)[ \t]*:[ \t]*this\.([A-Za-z0-9_]+)/gm;
    let m;
    while ((m = re.exec(region)) !== null) {
      const opcode = m[1];
      prims.add(opcode);
      const method = m[2];
      const mi = src.indexOf('\n    ' + method + ' (');
      if (mi < 0) continue;
      // 方法体边界：截到下一个同缩进的方法定义为止，避免把后一个方法的
      // Cast.to*(args.X) 误算到当前积木头上
      let end = mi + 4000;
      const nextMethod = /\n    [A-Za-z0-9_]+ \(/g;
      nextMethod.lastIndex = mi + 10;
      const nm = nextMethod.exec(src);
      if (nm && nm.index < end) end = nm.index;
      const body = src.slice(mi, end);
      const cre = /Cast\.(toNumber|toAngle|toBoolean|toString)\s*\(\s*args\.([A-Z0-9_]+)\s*\)/g;
      let c;
      while ((c = cre.exec(body)) !== null) {
        const kind = { toNumber: 'number', toAngle: 'angle', toBoolean: 'boolean', toString: 'text' }[c[1]];
        typeHints[opcode] = typeHints[opcode] || {};
        if (!typeHints[opcode][c[2]] || kind !== 'text') typeHints[opcode][c[2]] = kind;
      }
    }
    // 帽子积木（getHats）
    const gh = src.indexOf('getHats');
    if (gh >= 0) {
      const hreg = src.slice(gh, gh + 4000);
      const hre = /^[ \t]+([a-z][a-z0-9_]*)[ \t]*:[ \t]*\{/gm;
      let h;
      while ((h = hre.exec(hreg)) !== null) prims.add(h[1]);
    }
  }
  return { prims, typeHints };
}

/* ================================================================== *
 * 主流程
 * ================================================================== */
function main() {
  const argv = process.argv.slice(2);
  const arg = (n, d) => { const i = argv.indexOf(n); return i >= 0 && argv[i + 1] ? argv[i + 1] : d; };

  // 解析 scratch 源码目录：兼容「项目内布局」与「skill 独立安装」两种形态。
  const scriptDir = path.dirname(__filename);
  const skillRoot = path.resolve(scriptDir, '..');
  const resolveSrc = (which) => {
    const cands = [
      path.resolve(skillRoot, '..', 'reference', 'scratch-sources', which),
      path.resolve(skillRoot, 'reference', 'scratch-sources', which),
      path.resolve(process.cwd(), '..', 'reference', 'scratch-sources', which),
      path.resolve(process.cwd(), 'reference', 'scratch-sources', which),
    ];
    for (const c of cands) if (fs.existsSync(c)) return c;
    console.error('找不到 scratch 源码目录: ' + which + '\n已尝试:\n  ' + cands.join('\n  '));
    console.error('请用 --scratch-blocks / --scratch-vm 显式指定路径');
    process.exit(2);
  };

  const sbRoot = arg('--scratch-blocks', null) || resolveSrc('scratch-blocks');
  const vmRoot = arg('--scratch-vm', null) || resolveSrc('scratch-vm');
  const aliasPath = arg('--aliases', path.join(skillRoot, 'references', 'blocks-aliases.json'));
  const outPath = arg('--out', path.join(skillRoot, 'references', 'blocks-spec.json'));

  const core = extractFromScratchBlocks(sbRoot);
  const exts = extractFromExtensions(vmRoot);
  const { prims, typeHints } = extractRuntimeInfo(vmRoot);

  const blocks = Object.assign({}, core, exts);

  // 手工补齐动态生成的积木
  for (const [opcode, def] of Object.entries(MANUAL_BLOCKS)) {
    blocks[opcode] = Object.assign(
      { opcode, extension: null, inputs: {}, fields: {}, source: 'manual (scratch-gui 动态生成)' },
      def
    );
    if (MENU_INPUT_REFS[opcode]) blocks[opcode].menu_inputs = MENU_INPUT_REFS[opcode];
  }
  // 下拉影子积木
  for (const [opcode, def] of Object.entries(MENU_SOURCE_BLOCKS)) {
    blocks[opcode] = {
      opcode, category: (core[opcode] && core[opcode].category) || 'other',
      shape: 'menu-source', extension: null,
      inputs: {}, fields: { [def.field]: { type: 'menu', options: [] } },
      source: 'scratch-blocks (下拉影子积木)',
    };
  }

  // 类型推断 + 修正
  for (const opcode of Object.keys(blocks)) {
    const b = blocks[opcode];
    const hints = typeHints[opcode] || {};
    for (const iname of Object.keys(b.inputs)) {
      const cur = b.inputs[iname];
      if (cur.type === 'value' && hints[iname]) cur.type = hints[iname];
    }
    const ov = TYPE_OVERRIDES[opcode] || {};
    for (const [iname, t] of Object.entries(ov)) {
      if (b.inputs[iname]) b.inputs[iname].type = t;
    }
  }

  // 别名表
  let aliases = {};
  let inputAliases = {};
  if (fs.existsSync(aliasPath)) {
    const a = JSON.parse(fs.readFileSync(aliasPath, 'utf8'));
    aliases = a.aliases || {};
    inputAliases = a.input_aliases || {};
  }
  // 校验别名目标必须存在
  const badAliases = Object.entries(aliases).filter(([, op]) => !blocks[op]);
  if (badAliases.length) {
    console.error('[错误] 别名指向不存在的 opcode:');
    for (const [k, op] of badAliases) console.error('   %s -> %s', k, op);
    process.exit(1);
  }

  const spec = {
    meta: {
      generated: new Date().toISOString().slice(0, 10),
      scratchVmVersion: (() => {
        try { return JSON.parse(fs.readFileSync(path.join(vmRoot, 'package.json'), 'utf8')).version; }
        catch (e) { return 'unknown'; }
      })(),
      sources: [
        'scratch-blocks/src/blocks/*.ts (形状/输入/字段/菜单)',
        'scratch-vm/src/blocks/scratch3_*.js (运行时原语 + 输入类型)',
        'scratch-vm/src/extensions/*/index.js (扩展积木)',
      ],
      count: Object.keys(blocks).length,
    },
    aliases,
    input_aliases: inputAliases,
    blocks,
  };

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(spec, null, 2), 'utf8');

  const byCat = {};
  for (const b of Object.values(blocks)) byCat[b.category] = (byCat[b.category] || 0) + 1;
  const missing = [...prims].filter((p) => !blocks[p]).sort();
  const real = Object.keys(blocks).filter((b) => blocks[b].shape !== 'menu-source');

  console.log('写入 %s', outPath);
  console.log('  积木 %d 个（可写 %d + 下拉影子 %d），运行时原语 %d，别名 %d',
    Object.keys(blocks).length, real.length, Object.keys(blocks).length - real.length,
    prims.size, Object.keys(aliases).length);
  console.log('  分类: %s', Object.entries(byCat).map(([k, v]) => k + '=' + v).join(', '));
  if (missing.length) {
    console.log('  [缺失] %d: %s', missing.length, missing.join(', '));
    process.exitCode = 2;
  } else {
    console.log('  [OK] 交叉校验通过：运行时原语 100%% 收录');
  }
}

main();
