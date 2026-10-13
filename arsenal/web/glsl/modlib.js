// arsenal/web/glsl/modlib.js -- the browser twin of arsenal/shaders/modules.py: parse, resolve and compose house GLSL
// modules in the page, so a surface (the piano, First Light, the bench, the shader lab) builds its shader from the SAME
// module files the CLI composes. tests/test_glsl_modules.py runs this file under node and requires byte-identical output
// to the Python composer: "tweak one module and have everything update" (Daniel, 2026-10-13) only holds if the two
// doors cannot disagree. Change the algorithm in both files or in neither.
//
//   import { parseModule, createLibrary, loadLibrary } from '/glsl/modlib.js';
//   const lib = await loadLibrary('/glsl/index.json');       // or createLibrary([parseModule(text, path), ...])
//   const prelude = lib.prelude(['orbit-swarm']);             // helpers a snippet needs, dependency-ordered
//   const glsl = lib.compose(['fbm', 'palette-cosine']);      // function modules and everything they need
//
// A module is a .glsl file whose leading `//!` lines are one JSON header ({name, kind, cat, order, in, out, needs,
// params, license, credits, cost, note}). Dependencies are read from the code (a call to a function another module
// defines) plus the header's `needs`. Kinds helper/function/recipe/library/const compose; every other kind is a
// statement snippet that only a chain compiler can place.

export const API = 'arsenal.glsl-module/v1';
export const FUNCTION_KINDS = new Set(['helper', 'function', 'recipe', 'library', 'const']);
const DEFAULT_ORDER = 50;

// Kept in lockstep with arsenal/shaders/modules.py.
const COMMENT_RE = /\/\/[^\n]*|\/\*[\s\S]*?\*\//g;
const DEFINITION_RE = /^[ \t]*(?:(?:highp|mediump|lowp|const)\s+)*([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)\s*\{/gm;
const CALL_RE = /\b([A-Za-z_][A-Za-z0-9_]*)\s*\(/g;
const NOT_A_TYPE = new Set(['return', 'else', 'if', 'for', 'while', 'do', 'switch', 'case']);
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

export class ModuleError extends Error {}

export function stripComments(code) { return code.replace(COMMENT_RE, ' '); }

export function normalizeBody(body) {
  return body.replace(/\r\n/g, '\n').replace(/^\n+/, '').replace(/\s+$/, '').replace(/\n{3,}/g, '\n\n');
}

function sortedUnique(xs) { return [...new Set(xs)].sort(); }

export function parseModule(text, path = '<text>') {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  let n = 0;
  while (n < lines.length && lines[n].trimStart().startsWith('//!')) n++;
  if (!n) throw new ModuleError(`${path}: no //! header on the first line`);
  let header;
  try {
    header = JSON.parse(lines.slice(0, n).map((l) => l.trimStart().slice(3)).join(' '));
  } catch (e) {
    throw new ModuleError(`${path}: the //! header is not JSON (${e.message})`);
  }
  if (!header || typeof header !== 'object' || typeof header.name !== 'string' || !header.kind) {
    throw new ModuleError(`${path}: the //! header needs a name and a kind`);
  }
  const body = lines.slice(n).join('\n');
  const code = stripComments(body);
  const provides = sortedUnique([...code.matchAll(DEFINITION_RE)].filter((m) => !NOT_A_TYPE.has(m[1])).map((m) => m[2]));
  const own = new Set(provides);
  const calls = sortedUnique([...code.matchAll(CALL_RE)].map((m) => m[1]).filter((c) => !BUILTINS.has(c) && !own.has(c)));
  const order = typeof header.order === 'number' ? header.order : DEFAULT_ORDER;
  return { name: header.name, path, header, body, provides, calls, kind: String(header.kind),
    cat: String(header.cat || 'misc'), order, composable: FUNCTION_KINDS.has(String(header.kind)) };
}

export function createLibrary(modules = []) {
  const byName = new Map();
  const providers = new Map();
  const key = (a, b) => {
    const ma = byName.get(a), mb = byName.get(b);
    return (ma.order - mb.order) || (a < b ? -1 : a > b ? 1 : 0);
  };
  const lib = {
    add(m) {
      if (byName.has(m.name)) throw new ModuleError(`two modules are named '${m.name}': ${byName.get(m.name).path} and ${m.path}`);
      for (const fn of m.provides) {
        if (providers.has(fn)) throw new ModuleError(`function '${fn}' is defined by two modules: ${providers.get(fn)} and ${m.name}`);
      }
      byName.set(m.name, m);
      for (const fn of m.provides) providers.set(fn, m.name);
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
      for (const need of m.header.needs || []) {
        if (byName.has(need)) out.add(need);
        else if (providers.has(need)) out.add(providers.get(need));
        else throw new ModuleError(`module '${name}' needs '${need}', which no module is named or defines`);
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
    emit(order) {
      const parts = [`// ${API} compose: ` + order.join(', ')];
      for (const n of order) {
        const m = byName.get(n);
        parts.push(`// --- ${n} (${m.cat}) ---\n` + normalizeBody(m.body));
      }
      return parts.join('\n\n') + '\n';
    },
    compose(names) {
      const order = lib.resolve(names);
      const snippets = order.filter((n) => !byName.get(n).composable);
      if (snippets.length) {
        throw new ModuleError('cannot compose a snippet (' + snippets.map((n) => `${n}: kind '${byName.get(n).kind}'`).join(', ') +
          '); a chain compiler places snippets -- use prelude() for the helpers they need');
      }
      return lib.emit(order);
    },
    prelude(names) { return lib.emit(lib.resolve(names).filter((n) => byName.get(n).composable)); },
    modules: byName,
  };
  for (const m of modules) lib.add(m);
  return lib;
}

// In the page: an index.json ({api, files: ["noise/fbm.glsl", ...]}) beside the modules.
export async function loadLibrary(indexUrl) {
  const res = await fetch(indexUrl);
  if (!res.ok) throw new ModuleError(`${indexUrl}: HTTP ${res.status}`);
  const index = await res.json();
  const base = new URL('.', new URL(indexUrl, globalThis.location ? globalThis.location.href : 'http://localhost/'));
  const texts = await Promise.all(index.files.map(async (f) => {
    const r = await fetch(new URL(f, base));
    if (!r.ok) throw new ModuleError(`${f}: HTTP ${r.status}`);
    return [f, await r.text()];
  }));
  return createLibrary(texts.map(([f, t]) => parseModule(t, f)));
}
