// arsenal/web/glsl/modlib.js -- the browser twin of arsenal/shaders/modules.py: parse, resolve and compose house GLSL
// modules in the page, so a surface (the piano, First Light, the bench, the shader lab) builds its shader from the SAME
// module files the CLI composes. tests/test_glsl_modules.py runs this file under node and requires byte-identical output
// to the Python composer: "tweak one module and have everything update" (Daniel, 2026-10-13) only holds if the two
// doors cannot disagree. Change the algorithm in both files or in neither.
//
//   import { parseModule, createLibrary, loadLibrary } from '/glsl/modlib.js';
//   const lib = await loadLibrary('/glsl/index.json');       // lenient: a bad file is quarantined into lib.problems
//   const prelude = lib.prelude(['orbit-swarm']);             // helpers a snippet needs, dependency-ordered
//   const glsl = lib.compose(['fbm', 'palette-cosine'], 'webgl2');   // function modules and everything they need
//
// A module is a .glsl file whose leading `//!` lines are one JSON header ({name, kind, cat, order, version, in, out,
// needs, hooks, targets, params, license, credits, cost, note}). Dependencies are read from the code (a call to a
// function another module defines, or any use of a struct or top-level const another module declares) plus the
// header's `needs`. Kinds helper/function/recipe/library/const compose; every other kind is a statement snippet that
// only a chain compiler can place.
//
// The S1 extensions (shader school, 2026-10-13) are explained once, in the docstring of modules.py: structs and consts
// as providers, hooks as prototypes, strict and lenient loading, a quarantine that never composes a dangling call
// (salvaged symbols, unknown providers, bytes decoded one way in both twins, the header nesting limit), targets, the
// composed header (versions and sha256), and the index. This file mirrors them line for line.

export const API = 'arsenal.glsl-module/v1';
export const FUNCTION_KINDS = new Set(['helper', 'function', 'recipe', 'library', 'const']);
const DEFAULT_ORDER = 50;
const DEFAULT_VERSION = '0.0.0';

// Kept in lockstep with arsenal/shaders/modules.py. Every pattern is ASCII by construction: whitespace is spelled
// [ \t\r\n\f\v] (the two languages' \s disagree outside ASCII), and a definition starts a line by the lookbehind
// (?<![^\n]) instead of ^ with the m flag (which here would also start a line after \r, U+2028 and U+2029).
const COMMENT_RE = /\/\/[^\n]*|\/\*[\s\S]*?\*\//g;
const DEFINITION_RE = /(?<![^\n])[ \t]*(?:(?:highp|mediump|lowp|const)[ \t\r\n\f\v]+)*([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]+([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*\(([^()]*)\)[ \t\r\n\f\v]*\{/g;
const CALL_RE = /\b([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*\(/g;
const NOT_A_TYPE = new Set(['return', 'else', 'if', 'for', 'while', 'do', 'switch', 'case']);
const ENTRY_POINTS = new Set(['main', 'mainImage', 'mainCubemap', 'mainSound', 'mainVR']);   // placed by a runtime
const IDENT_RE = /\b[A-Za-z_][A-Za-z0-9_]*/g;
const STRUCT_RE = /\bstruct[ \t\r\n\f\v]+([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*\{/g;
const CONST_RE = /\bconst[ \t\r\n\f\v]+(?:(?:highp|mediump|lowp)[ \t\r\n\f\v]+)?[A-Za-z_][A-Za-z0-9_]*[ \t\r\n\f\v]*(?:\[[^\]]*\][ \t\r\n\f\v]*)?([^;]*);/g;
const DECLARATOR_RE = /^[ \t\r\n\f\v]*([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*(?:\[[^\]]*\][ \t\r\n\f\v]*)?=/;
const HOOK_RE = /^(?:(?:highp|mediump|lowp) )?[A-Za-z_][A-Za-z0-9_]* ([A-Za-z_][A-Za-z0-9_]*)\([^()]*\)$/;
const PARAM_TOKEN_RE = /^[A-Za-z_][A-Za-z0-9_]*(?:\[[A-Za-z0-9_]*\])?$/;
const PARAM_DIRECTIONS = { in: '', out: 'out ', inout: 'inout ' };   // `in` is the default, so it never counts
const PARAM_IGNORED = new Set(['const', 'highp', 'mediump', 'lowp']);
// A name the module declares itself (a parameter, a local, a field), so a use of it is not a use of a quarantined
// file's const of the same name; the kind of a file whose header is not JSON, read for salvage only (as modules.py).
const DECLARED_RE = /\b([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]+([A-Za-z_][A-Za-z0-9_]*)[ \t\r\n\f\v]*(?=[=;,)\[])/g;
const KIND_RE = /"kind"[ \t\r\n]*:[ \t\r\n]*"([^"\\]*)"/;
export const MAX_HEADER_DEPTH = 32;   // brackets and braces outside strings; a real header nests four deep
// Header values that reach the composed header or the sort order (same rules and words as modules.py).
const NAME_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]*$/;
const VERSION_RE = /^[0-9A-Za-z][0-9A-Za-z.+-]*$/;
const CONTROL_RE = /[\x00-\x1f\x7f-\x9f\u2028\u2029\ud800-\udfff]/u;   // with u, the surrogate range is lone surrogates only
const BUILTINS = new Set(`
radians degrees sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh pow exp log exp2 log2 sqrt inversesqrt
abs sign floor trunc round roundEven ceil fract mod modf min max clamp mix step smoothstep isnan isinf
floatBitsToInt floatBitsToUint intBitsToFloat uintBitsToFloat packSnorm2x16 unpackSnorm2x16 packUnorm2x16
unpackUnorm2x16 packHalf2x16 unpackHalf2x16 length distance dot cross normalize faceforward reflect refract
matrixCompMult outerProduct transpose determinant inverse lessThan lessThanEqual greaterThan greaterThanEqual equal
notEqual any all not textureSize texture textureProj textureLod textureOffset texelFetch texelFetchOffset
textureProjOffset textureLodOffset textureProjLod textureProjLodOffset textureGrad textureGradOffset textureProjGrad
textureProjGradOffset dFdx dFdy fwidth
float int uint bool vec2 vec3 vec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4 bvec2 bvec3 bvec4 mat2 mat3 mat4
mat2x2 mat2x3 mat2x4 mat3x2 mat3x3 mat3x4 mat4x2 mat4x3 mat4x4
if for while return switch do else main mainImage mainCubemap mainSound mainVR
`.split(/\s+/).filter(Boolean));

// What each target cannot do, in the words the refusal uses (same tables as modules.py, which explains them).
const ES1_LACKS = {
  uint: 'GLSL ES 1.00 has no unsigned integers',
  texelFetch: 'GLSL ES 1.00 has no texelFetch',
  derivatives: 'GLSL ES 1.00 has dFdx, dFdy and fwidth only through the OES_standard_derivatives extension',
};
export const TARGET_LACKS = {
  webgl2: {},
  toy: {},
  'three-r186': {},
  'three-r186-glsl1': { ...ES1_LACKS },
  webgl1: { ...ES1_LACKS, 'float-targets': 'WebGL1 renders to float textures only through extensions' },
};
export const TARGET_ES1_ONLY = {
  'three-r186-glsl1': 'a three.js RawShaderMaterial without glslVersion: THREE.GLSL3 is compiled as GLSL ES 1.00',
  webgl1: 'WebGL1 compiles GLSL ES 1.00 only',
};
const ONE_PASS = 'a three.js material is one pass; a pass needs the multipass runtime';
export const TARGET_REFUSES_KINDS = {
  'three-r186': { pass: ONE_PASS },
  'three-r186-glsl1': { pass: ONE_PASS },
};
const has = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);

export class ModuleError extends Error {}

export function stripComments(code) { return code.replace(COMMENT_RE, ' '); }

export function normalizeBody(body) {
  return body.replace(/\r\n/g, '\n').replace(/^\n+/, '').replace(/[ \t\r\n\f\v]+$/, '').replace(/\n{3,}/g, '\n\n');
}

// Everything inside ( ) and { } blanked, the outermost brackets kept: what GLSL sees at file scope. Iterates by code
// point, as Python does, so a stray closer behaves the same in both twins.
export function topLevel(code) {
  let depth = 0;
  let out = '';
  for (const ch of code) {
    if (ch === '(' || ch === '{') { depth++; out += depth === 1 ? ch : ' '; }
    else if (ch === ')' || ch === '}') { out += depth <= 1 ? ch : ' '; depth = Math.max(0, depth - 1); }
    else out += depth === 0 ? ch : ' ';
  }
  return out;
}

// "float  mapScene( vec3 p );" -> "float mapScene(vec3 p)": one spelling per prototype, so a shared hook prints once.
export function canonicalPrototype(text) {
  return text.replace(/[ \t\r\n\f\v]+/g, ' ').replace(/ ?([(),;]) ?/g, '$1')
    .replace(/ ?\[ ?/g, '[').replace(/ ?\]/g, ']')   // "float w [ 4 ]" -> "float w[4]"; the space after "]" stays
    .replace(/;+$/, '').replace(/^ +| +$/g, '').replace(/,/g, ', ');
}

// [name, base, full] of a canonical prototype (see hook_signature in modules.py), or null when malformed.
export function hookSignature(proto) {
  if (!HOOK_RE.test(proto)) return null;
  const open = proto.indexOf('(');
  const head = proto.slice(0, open).split(' ');
  const inner = proto.slice(open + 1, -1);
  const ret = head[head.length - 2];
  const name = head[head.length - 1];
  const types = [];
  const full = [];
  for (const param of (inner === '' || inner === 'void' ? [] : inner.split(', '))) {
    let direction = null;
    const rest = [];
    for (const tok of param.split(' ')) {
      if (has(PARAM_DIRECTIONS, tok)) {
        if (direction !== null) return null;
        direction = PARAM_DIRECTIONS[tok];
      } else if (!PARAM_IGNORED.has(tok)) rest.push(tok);
    }
    if (rest.length < 1 || rest.length > 2 || !rest.every((t) => PARAM_TOKEN_RE.test(t))) return null;
    let kind = rest[0];
    if (rest.length === 2 && rest[1].includes('[')) {
      if (kind.includes('[')) return null;   // an array of arrays is not GLSL ES
      kind += rest[1].slice(rest[1].indexOf('['));
    }
    types.push(kind);
    full.push((direction || '') + kind);
  }
  return [name, `${name}(${types.join(',')})`, `${ret} ${name}(${full.join(',')})`];
}

// [prototypes, names, [base, full] keys]. ownData maps each struct and const this module declares to its kind: a hook
// may not name one, because the hooks block is written before the module body.
function parseHooks(header, path, ownData) {
  const raw = header.hooks;
  if (raw === undefined || raw === null) return [[], [], []];
  if (!Array.isArray(raw) || !raw.every((h) => typeof h === 'string')) {
    throw new ModuleError(`${path}: hooks must be a list of GLSL prototypes such as "float mapScene(vec3 p)"`);
  }
  const hooks = [];
  const names = [];
  const keys = [];
  const seen = new Map();
  for (const h of raw) {
    const proto = canonicalPrototype(h);
    const sig = hookSignature(proto);
    if (!sig) throw new ModuleError(`${path}: hook '${h}' is not a GLSL prototype (want "float mapScene(vec3 p)")`);
    const [name, base, full] = sig;
    const own = sortedUnique(full.match(IDENT_RE) || []).filter((i) => i !== name && i !== 'out' && i !== 'inout' && ownData.has(i));
    if (own.length) {
      const what = ownData.get(own[0]);
      throw new ModuleError(`${path}: hook '${h}' names ${what} '${own[0]}', which this module declares; the hooks block ` +
        `is written before the module body, so move the ${what} to its own module`);
    }
    if (seen.has(base)) {
      if (seen.get(base)[0] !== full) throw new ModuleError(`${path}: hooks '${seen.get(base)[1]}' and '${proto}' declare ${name}() differently`);
      continue;
    }
    seen.set(base, [full, proto]);
    hooks.push(proto);
    keys.push([base, full]);
    if (!names.includes(name)) names.push(name);
  }
  return [hooks, names, keys];
}

function targetNeedsOf(header) {
  const t = header.targets;
  const needs = t && typeof t === 'object' && !Array.isArray(t) ? t.needs : undefined;
  return Array.isArray(needs) ? needs.filter((n) => typeof n === 'string') : [];
}

function targetGlslOf(header) {
  const t = header.targets;
  return t && typeof t === 'object' && !Array.isArray(t) && t.glsl === '100' ? '100' : '300es';
}

// Code-point order, as Python's sorted(): identifiers and module names are ASCII, so the default sort agrees.
function sortedUnique(xs) { return [...new Set(xs)].sort(); }

// One leading BOM dropped, and \r\n and a lone \r both read as a line break (as in modules.py).
function sourceLines(text) {
  return (text.startsWith('\ufeff') ? text.slice(1) : text).replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
}

// Leading `//!` lines; only spaces and tabs may precede the marker (trimStart() and lstrip() disagree on the rest).
function headerLineCount(lines) {
  let n = 0;
  while (n < lines.length && lines[n].replace(/^[ \t]+/, '').startsWith('//!')) n++;
  return n;
}

function scan(code, composable) {
  const functions = sortedUnique([...code.matchAll(DEFINITION_RE)]
    .filter((m) => !NOT_A_TYPE.has(m[1]) && !ENTRY_POINTS.has(m[2])).map((m) => m[2]));
  let structs = [];
  const consts = [];
  if (composable) {   // a snippet's consts live in a block of the chain compiler's main
    const scope = topLevel(code);
    structs = sortedUnique([...scope.matchAll(STRUCT_RE)].map((m) => m[1]));
    for (const m of scope.matchAll(CONST_RE)) {
      for (const part of m[1].split(',')) {
        const d = DECLARATOR_RE.exec(part);
        if (d) consts.push(d[1]);
      }
    }
  }
  return [functions, structs, sortedUnique(consts)];
}

const isText = (v) => typeof v === 'string' && !CONTROL_RE.test(v);

// The first header value that would corrupt the composed header, the sort order or a refusal (words as modules.py).
function headerProblem(header) {
  if (!NAME_RE.test(header.name)) return "the //! header's name must be letters, digits, '.', '_' or '-' (kebab-case for a library module)";
  const absent = (v) => v === undefined || v === null;
  if (!isText(header.kind)) return "the //! header's kind must be a string without control characters";
  if (!absent(header.cat) && !isText(header.cat)) return "the //! header's cat must be a string without control characters";
  if (!absent(header.version) && !(typeof header.version === 'string' && VERSION_RE.test(header.version))) {
    return "the //! header's version must be letters, digits, '.', '+' or '-' (a semantic version such as \"1.2.0\")";
  }
  if (!absent(header.order) && !(typeof header.order === 'number' && Number.isFinite(header.order))) {
    return "the //! header's order must be a finite number (not a boolean or a string)";
  }
  if (!absent(header.needs) && !(Array.isArray(header.needs) && header.needs.every((n) => typeof n === 'string'))) {
    return "the //! header's needs must be a list of module or function names";
  }
  return null;
}

function headerText(lines, n) {
  return lines.slice(0, n).map((l) => l.replace(/^[ \t]+/, '').slice(3)).join(' ');
}

// How deep brackets and braces nest outside JSON strings: a count both twins share (Python's json recursed out on a
// header V8's JSON.parse read). Only ASCII characters matter, so code units and code points count alike.
function jsonDepth(text) {
  let depth = 0;
  let deepest = 0;
  let inString = false;
  let escaped = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === '"') inString = false;
    } else if (ch === '"') inString = true;
    else if (ch === '[' || ch === '{') { depth++; deepest = Math.max(deepest, depth); }
    else if (ch === ']' || ch === '}') depth--;
  }
  return deepest;
}

function parseHeaderJson(text, path) {
  if (jsonDepth(text) > MAX_HEADER_DEPTH) throw new ModuleError(`${path}: the //! header nests deeper than ${MAX_HEADER_DEPTH} levels`);
  try {
    return JSON.parse(text);
  } catch (e) {
    throw new ModuleError(`${path}: the //! header is not JSON (${e.message})`);
  }
}

export function parseModule(text, path = '<text>') {
  const lines = sourceLines(text);
  const n = headerLineCount(lines);
  if (!n) throw new ModuleError(`${path}: no //! header on the first line`);
  const header = parseHeaderJson(headerText(lines, n), path);
  if (!header || typeof header !== 'object' || Array.isArray(header) || typeof header.name !== 'string' ||
      header.kind === undefined || header.kind === null || header.kind === '') {
    throw new ModuleError(`${path}: the //! header needs a name and a kind`);
  }
  const problem = headerProblem(header);
  if (problem) throw new ModuleError(`${path}: ${problem}`);
  const body = lines.slice(n).join('\n');
  const code = stripComments(body);
  const kind = header.kind;
  const composable = FUNCTION_KINDS.has(kind);
  const [functions, structs, consts] = scan(code, composable);
  const ownData = new Map([...consts.map((c) => [c, 'const']), ...structs.map((s) => [s, 'struct'])]);
  const [hooks, hookNames, hookKeys] = parseHooks(header, path, ownData);
  const own = new Set([...functions, ...structs, ...consts]);
  const provides = sortedUnique([...own]);
  const calls = sortedUnique([...code.matchAll(CALL_RE)].map((m) => m[1]).filter((c) => !BUILTINS.has(c) && !own.has(c)));
  const scope = code + '\n' + hooks.join('\n');
  const uses = sortedUnique(scope.match(IDENT_RE) || []).filter((u) => !BUILTINS.has(u) && !own.has(u));
  const declared = sortedUnique([...scope.matchAll(DECLARED_RE)].filter((d) => !NOT_A_TYPE.has(d[1])).map((d) => d[2]));
  const order = header.order === undefined || header.order === null ? DEFAULT_ORDER : header.order;
  const version = typeof header.version === 'string' && header.version ? header.version : DEFAULT_VERSION;
  return { name: header.name, path, header, body, provides, calls, functions, structs, consts,
    uses, declared, hooks, hookNames, hookKeys, targetNeeds: targetNeedsOf(header), glsl: targetGlslOf(header), version,
    kind, cat: String(header.cat || 'misc'), order, composable };
}

// The offset of the first byte that does not begin a well-formed UTF-8 sequence, or -1: the WHATWG decoder's rule
// (overlong forms, surrogates and anything past U+10FFFF are malformed), which is Python's exc.start.
function firstBadUtf8Byte(bytes) {
  for (let i = 0; i < bytes.length;) {
    const b = bytes[i];
    if (b < 0x80) { i++; continue; }
    let need;
    let lower = 0x80;
    let upper = 0xbf;
    if (b >= 0xc2 && b <= 0xdf) need = 1;
    else if (b >= 0xe0 && b <= 0xef) { need = 2; if (b === 0xe0) lower = 0xa0; if (b === 0xed) upper = 0x9f; }
    else if (b >= 0xf0 && b <= 0xf4) { need = 3; if (b === 0xf0) lower = 0x90; if (b === 0xf4) upper = 0x8f; }
    else return i;
    for (let k = 1; k <= need; k++) {
      const c = bytes[i + k];
      if (c === undefined || c < lower || c > upper) return i;
      lower = 0x80;
      upper = 0xbf;
    }
    i += need + 1;
  }
  return -1;
}

const UTF8 = new TextDecoder('utf-8', { ignoreBOM: true });   // keep a BOM: sourceLines drops exactly one, as Python

// [text, problem]: bytes decoded as UTF-8, each malformed sequence one U+FFFD and a leading BOM kept, and null or why
// the file is not UTF-8, naming its first bad byte (decode_source in modules.py; the parity plan compares the two).
export function decodeSource(bytes, path = '<bytes>') {
  const u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  const bad = firstBadUtf8Byte(u8);
  return [UTF8.decode(u8), bad < 0 ? null : `${path}: is not UTF-8 text (byte ${bad} cannot be decoded)`];
}

// The kind a broken file declares, if it can be read: from the header when it parses, else from a "kind" string.
function salvageKind(text) {
  let header;
  try {
    header = parseHeaderJson(text, '');
  } catch {
    const found = KIND_RE.exec(text);
    return found ? found[1] : null;
  }
  return header && typeof header === 'object' && !Array.isArray(header) && typeof header.kind === 'string' ? header.kind : null;
}

// [functions, structs and consts, known] a quarantined file would have provided (see _salvage_symbols in
// modules.py): data symbols unless the kind is readable and not composable; known is false when the salvage failed or
// a replacement from decoding sits in the code. Never throws.
function salvageSymbols(text, replaced = false) {
  try {
    const lines = sourceLines(text);
    const n = headerLineCount(lines);
    const kind = salvageKind(headerText(lines, n));
    const code = stripComments(lines.slice(n).join('\n'));
    const [functions, structs, consts] = scan(code, kind === null || FUNCTION_KINDS.has(kind));
    return [functions, sortedUnique([...structs, ...consts]), !(replaced && code.includes('\ufffd'))];
  } catch {
    return [[], [], false];
  }
}

function symbolKind(m, sym) {
  return m.functions.includes(sym) ? 'function' : m.structs.includes(sym) ? 'struct' : 'const';
}

// createLibrary(modules, {strict}): strict (the default, as load_library in Python) throws on a name or symbol clash;
// lenient quarantines the later module into lib.problems ({path, name, problem}) and keeps the rest.
export function createLibrary(modules = [], { strict = true } = {}) {
  const byName = new Map();
  const providers = new Map();   // symbol -> module name
  const data = new Map();        // struct and const symbols only (used, not called)
  const problems = [];
  const lost = new Map();        // symbol a quarantined file had -> [path, isData] (the first quarantined file wins)
  const lostModules = new Map(); // name of a quarantined module -> its path
  const unknown = [];            // quarantined files whose text could not be read in full
  const unknownNote = () => `a quarantined file the library could not read in full may: ${unknown.join(', ')}`;
  const key = (a, b) => {
    const ma = byName.get(a), mb = byName.get(b);
    return (ma.order - mb.order) || (a < b ? -1 : a > b ? 1 : 0);
  };
  const lib = {
    // Record a refused file and remember its symbols, so a module calling one is refused at compose time naming it.
    // An unknown file may have held anything: while one is recorded, every unresolved call is refused, naming it.
    quarantine(path, name, problem, functions = [], dataSymbols = [], isUnknown = false) {
      problems.push({ path, name, problem });
      for (const sym of functions) if (!lost.has(sym)) lost.set(sym, [path, false]);
      for (const sym of dataSymbols) if (!lost.has(sym)) lost.set(sym, [path, true]);
      if (name !== null && name !== undefined && !lostModules.has(name)) lostModules.set(name, path);
      if (isUnknown) unknown.push(path);
    },
    add(m) {
      let problem = null;
      if (byName.has(m.name)) {
        problem = `two modules are named '${m.name}': ${byName.get(m.name).path} and ${m.path}`;
      } else {
        for (const sym of m.provides) {
          if (providers.has(sym)) {
            const other = providers.get(sym);
            problem = `${symbolKind(m, sym)} '${sym}' is provided by two modules: ${other} (${byName.get(other).path}) and ${m.name} (${m.path})`;
            break;
          }
        }
      }
      if (problem) {
        if (strict) throw new ModuleError(problem);
        lib.quarantine(m.path, m.name, problem, m.functions, [...m.structs, ...m.consts]);
        return false;
      }
      byName.set(m.name, m);
      for (const sym of m.provides) providers.set(sym, m.name);
      for (const sym of [...m.structs, ...m.consts]) data.set(sym, m.name);
      return true;
    },
    names() { return [...byName.keys()].sort(); },
    get(name) {
      if (!byName.has(name)) throw new ModuleError(`no module named '${name}'`);
      return byName.get(name);
    },
    deps(name) {
      const m = lib.get(name);
      const out = new Set();
      for (const c of m.calls) if (providers.has(c) && providers.get(c) !== name) out.add(providers.get(c));
      for (const u of m.uses) if (data.has(u)) out.add(data.get(u));
      for (const need of m.header.needs || []) {
        if (byName.has(need)) out.add(need);
        else if (providers.has(need)) out.add(providers.get(need));
        else {
          const where = lostModules.get(need) || (lost.has(need) ? lost.get(need)[0] : null);
          throw new ModuleError(`module '${name}' needs '${need}', which no module is named or defines` +
            (where ? ` (only the quarantined file ${where} did; see library.problems)`
              : unknown.length ? ` (${unknownNote()}; see library.problems)` : ''));
        }
      }
      out.delete(name);
      return [...out].sort(key);
    },
    resolve(names) {
      const closure = new Set();
      const stack = [...names];
      while (stack.length) {
        const n = stack.pop();
        if (closure.has(n)) continue;
        lib.get(n);
        closure.add(n);
        stack.push(...lib.deps(n));
      }
      const pending = new Map([...closure].map((n) => [n, new Set(lib.deps(n))]));
      const out = [];
      while (pending.size) {
        const ready = [...pending].filter(([, d]) => d.size === 0).map(([n]) => n).sort(key);
        if (!ready.length) throw new ModuleError('dependency cycle among: ' + [...pending.keys()].sort().join(', '));
        const nxt = ready[0];
        out.push(nxt);
        pending.delete(nxt);
        for (const d of pending.values()) d.delete(nxt);
      }
      return out;
    },
    // Calls no module provides and no hook in the module's reach (its own, its dependencies') declares.
    unresolved(name) {
      const m = lib.get(name);
      const hooks = new Set(lib.resolve([name]).flatMap((n) => byName.get(n).hookNames));
      return m.calls.filter((c) => !providers.has(c) && !hooks.has(c));
    },
    checkTarget(order, target) {
      if (target === null || target === undefined) return;
      if (!Object.prototype.hasOwnProperty.call(TARGET_LACKS, target)) {
        throw new ModuleError(`unknown target '${target}' (known: ${Object.keys(TARGET_LACKS).sort().join(', ')})`);
      }
      const lacks = TARGET_LACKS[target];
      const kinds = TARGET_REFUSES_KINDS[target] || {};
      const es1Only = has(TARGET_ES1_ONLY, target) ? TARGET_ES1_ONLY[target] : null;
      const refusals = [];
      for (const n of order) {
        const m = byName.get(n);
        if (has(kinds, m.kind)) refusals.push(`module '${n}' is kind '${m.kind}' (${kinds[m.kind]})`);
        if (es1Only && m.glsl !== '100') {
          refusals.push(`module '${n}' is GLSL ES 3.00 (${es1Only}; a module written for both declares targets.glsl "100")`);
        }
        for (const need of m.targetNeeds) {
          if (has(lacks, need)) refusals.push(`module '${n}' needs ${need} (${lacks[need]})`);
        }
      }
      if (refusals.length) throw new ModuleError(`target '${target}' cannot take this composition: ` + refusals.join('; '));
    },
    // A module that calls, or uses as a type or constant, a symbol only a quarantined file provides is refused: lenient
    // loading must never hand a page a dangling call. While an unknown file is quarantined, every unresolved call is
    // refused too, naming the unknown files. A hook in the module's reach still covers a call; a use of a lost struct
    // or const does not count where the module declares that name itself.
    checkQuarantine(order) {
      if (!lost.size && !unknown.length) return;
      const refusals = [];
      for (const n of order) {
        const m = byName.get(n);
        const called = [];
        for (const c of lib.unresolved(n)) {
          if (lost.has(c)) {
            called.push(c);
            refusals.push(`module '${n}' calls ${c}() (only the quarantined file ${lost.get(c)[0]} provides it)`);
          } else if (unknown.length) {
            refusals.push(`module '${n}' calls ${c}(), which no loaded module provides (${unknownNote()})`);
          }
        }
        for (const u of m.uses) {
          if (lost.has(u) && lost.get(u)[1] && !providers.has(u) && !called.includes(u) && !m.declared.includes(u)) {
            refusals.push(`module '${n}' uses ${u} (only the quarantined file ${lost.get(u)[0]} provides it)`);
          }
        }
      }
      if (refusals.length) {
        throw new ModuleError('cannot compose: part of it was quarantined at load (see library.problems): ' + refusals.join('; '));
      }
    },
    emit(order) {
      const parts = [];
      const emitted = new Map();   // base signature -> [full, module, prototype]
      for (const n of order) {
        const m = byName.get(n);
        const fresh = [];
        m.hooks.forEach((h, i) => {
          const [base, full] = m.hookKeys[i];
          if (emitted.has(base)) {
            const [firstFull, firstModule, firstHook] = emitted.get(base);
            if (firstFull !== full) {
              throw new ModuleError(`modules '${firstModule}' and '${n}' declare the hook ${base.slice(0, base.indexOf('('))}() differently: '${firstHook}' and '${h}'`);
            }
            return;
          }
          emitted.set(base, [full, n, h]);
          fresh.push(h);
        });
        if (fresh.length) parts.push('// hooks\n' + fresh.map((h) => h + ';').join('\n'));
        parts.push(`// --- ${n} (${m.cat}) ---\n` + normalizeBody(m.body));
      }
      const text = parts.length ? '\n' + parts.join('\n\n') + '\n' : '';
      const head = [`// ${API} compose: ` + order.join(', '),
        '// modules:' + order.map((n) => ` ${n}@${byName.get(n).version}`).join(''),
        '// sha256: ' + sha256(text)];
      return head.join('\n') + '\n' + text;
    },
    compose(names, target = null) {
      const order = lib.resolve(names);
      lib.checkTarget(order, target);
      lib.checkQuarantine(order);
      const snippets = order.filter((n) => !byName.get(n).composable);
      if (snippets.length) {
        throw new ModuleError('cannot compose a snippet (' + snippets.map((n) => `${n}: kind '${byName.get(n).kind}'`).join(', ') +
          '); a chain compiler places snippets -- use prelude() for the helpers they need');
      }
      return lib.emit(order);
    },
    prelude(names, target = null) {
      const order = lib.resolve(names);
      lib.checkTarget(order, target);
      lib.checkQuarantine(order);
      return lib.emit(order.filter((n) => byName.get(n).composable));
    },
    modules: byName,
    problems,
    unknown,
    strict,
  };
  for (const m of modules) lib.add(m);
  return lib;
}

// Parse one file into the library. Strict lets any failure throw; lenient quarantines whatever went wrong (a
// ModuleError or a bug alike: a page must not blank over one file) with what the file would have provided.
function addSource(lib, path, text) {
  let m;
  try {
    m = parseModule(text, path);
  } catch (e) {
    if (lib.strict) throw e;
    const problem = e instanceof ModuleError ? e.message : `${path}: ${e && e.name}: ${e && e.message}`;
    const [functions, data, known] = salvageSymbols(text);
    lib.quarantine(path, null, problem, functions, data, !known);
    return;
  }
  lib.add(m);
}

// Decode one file's bytes (as decodeSource) and parse it: bytes that are not UTF-8 quarantine the file (strict throws)
// with what its replaced text still shows it provided, and make it unknown too if a replacement sits in its code.
function addBytes(lib, path, bytes) {
  const [text, problem] = decodeSource(bytes, path);
  if (problem === null) { addSource(lib, path, text); return; }
  if (lib.strict) throw new ModuleError(problem);
  const [functions, data, known] = salvageSymbols(text, true);
  lib.quarantine(path, null, problem, functions, data, !known);
}

// A file named but not read (a failed fetch; in the CLI, an OSError): strict throws, lenient records it unknown.
function addUnread(lib, path, problem) {
  const reason = problem || `${path}: could not be read`;
  if (lib.strict) throw new ModuleError(reason);
  lib.quarantine(path, null, reason, [], [], true);
}

// A library from sources in load order: [path, text], [path, bytes] (a Uint8Array or ArrayBuffer, decoded as
// decodeSource does), or [path, null, problem] for a file that could not be read -- the shapes library_from_sources
// takes in modules.py. Lenient quarantines a bad file of any shape and loads the rest; strict throws the first.
export function libraryFromSources(sources, { strict = true } = {}) {
  const lib = createLibrary([], { strict });
  for (const [path, content, problem] of sources) {
    if (content === null || content === undefined) addUnread(lib, path, problem);
    else if (typeof content === 'string') addSource(lib, path, content);
    else addBytes(lib, path, content);
  }
  return lib;
}

// In the page: arsenal/web/glsl/index.json beside the modules, written by `py -m arsenal shader lib index --write`.
// Both shapes load: {files: [{path, sha256}]} (S1) and the older {files: ["noise/fbm.glsl", ...]}. A page is lenient
// by default: a file it cannot fetch (a 404 from a stale index, a dropped connection, an entry with no path) is
// quarantined as an UNKNOWN provider, and one it cannot decode or parse is quarantined with what it would have
// provided, into lib.problems in index order; the rest load. Strict throws the first failure in index order. Only the
// index itself failing is fatal, because without it there is no library at all. The files are read as bytes
// (arrayBuffer, not text(): text() drops a BOM and hides bytes that are not UTF-8, so the CLI and the page disagreed).
export async function loadLibrary(indexUrl, { strict = false } = {}) {
  const res = await fetch(indexUrl);
  if (!res.ok) throw new ModuleError(`${indexUrl}: HTTP ${res.status}`);
  const index = await res.json();
  if (!index || !Array.isArray(index.files)) throw new ModuleError(`${indexUrl}: not a module index (want {"files": [...]})`);
  const base = new URL('.', new URL(indexUrl, globalThis.location ? globalThis.location.href : 'http://localhost/'));
  const sources = await Promise.all(index.files.map(async (f, i) => {
    const path = typeof f === 'string' ? f : f && typeof f.path === 'string' ? f.path : null;
    if (path === null) return [`index.files[${i}]`, null, `${indexUrl}: index.files[${i}] names no path`];
    try {
      const r = await fetch(new URL(path, base));
      if (!r.ok) return [path, null, `${path}: HTTP ${r.status}`];
      // Bytes, so the decoding is decodeSource's. A fetch shim with no arrayBuffer() (a test double) gets text(),
      // which is already decoded (a BOM dropped, bad bytes replaced): only a real Response matches the CLI exactly.
      return [path, typeof r.arrayBuffer === 'function' ? new Uint8Array(await r.arrayBuffer()) : await r.text()];
    } catch (e) {
      return [path, null, `${path}: could not be fetched (${e && e.message})`];
    }
  }));
  return libraryFromSources(sources, { strict });
}

// SHA-256 of a string's UTF-8 bytes, synchronous so compose() stays synchronous in the page (SubtleCrypto is async).
// The constants are the standard ones (FIPS 180-4); the parity pin checks this against Python's hashlib.
const SHA_K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);
const SHA_H0 = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];

export function sha256(text) {
  const bytes = new TextEncoder().encode(text);
  const total = Math.ceil((bytes.length + 9) / 64) * 64;
  const buf = new Uint8Array(total);
  buf.set(bytes);
  buf[bytes.length] = 0x80;
  const view = new DataView(buf.buffer);
  const bits = bytes.length * 8;
  view.setUint32(total - 8, Math.floor(bits / 0x100000000));
  view.setUint32(total - 4, bits >>> 0);
  const H = Uint32Array.from(SHA_H0);
  const W = new Uint32Array(64);
  const ror = (x, n) => (x >>> n) | (x << (32 - n));
  for (let off = 0; off < total; off += 64) {
    for (let i = 0; i < 16; i++) W[i] = view.getUint32(off + 4 * i);
    for (let i = 16; i < 64; i++) {
      const a = W[i - 15], b = W[i - 2];
      W[i] = W[i - 16] + (ror(a, 7) ^ ror(a, 18) ^ (a >>> 3)) + W[i - 7] + (ror(b, 17) ^ ror(b, 19) ^ (b >>> 10));
    }
    let a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];   // FIPS 180-4 working variables
    for (let t = 0; t < 64; t++) {   // the round index is t in FIPS 180-4
      const t1 = (h + (ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)) + ((e & f) ^ (~e & g)) + SHA_K[t] + W[t]) >>> 0;
      const t2 = ((ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    H[0] += a; H[1] += b; H[2] += c; H[3] += d; H[4] += e; H[5] += f; H[6] += g; H[7] += h;
  }
  return [...H].map((x) => x.toString(16).padStart(8, '0')).join('');
}
