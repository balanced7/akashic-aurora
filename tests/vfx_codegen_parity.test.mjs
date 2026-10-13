// tests/vfx_codegen_parity.test.mjs -- the VFX bench's GLSL, written by the shared composer, must be the GLSL the bench
// writes today, byte for byte (slice S5 of the shader school, 2026-10-13).
//
// Why this file exists. scripts/vfx.html has three hand-written code generators: buildGLSL (the Compose chain),
// buildGraphGLSL (the Graph card) and thumbShaderFor (palette tiles, the hover preview, CLI thumbs). S5 rebuilds them on
// arsenal/web/glsl/modlib.js as scripts/vfx-codegen.js, so the bench reads its chunks through the same parser and the
// same dependency resolver as every other surface. "Zero pixel change" is proved here as "zero byte change": identical
// shader text compiles to identical pixels, so no GPU render is needed. The one exception is DECLARED below and has its
// own diff: the mask-port fix (census defect D1).
//
// The oracle is the page itself, never a copy of it: the legacy generators (and the page's own graph-editing functions,
// which build the random graphs below) are lifted out of scripts/vfx.html at test time and run in a node vm with the
// page's globals stubbed, so a later edit to the page is what gets compared. The chunks are the exact records the bench
// receives from GET /vfx/chunks (scripts/bifrost_ui.py _vfx_chunks_read), read through Python when `py` runs here and
// through a line-for-line JS twin otherwise; when both run they must agree.
//
// Run: node tests/vfx_codegen_parity.test.mjs     (zero dependencies; exits 1 on any failure)
import { readFileSync, readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import vm from 'node:vm';
import * as modlib from '../arsenal/web/glsl/modlib.js';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
const at = (p) => join(ROOT, p);
let pass = 0, fail = 0;
function check(label, ok, detail = '') {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ': ' + detail : ''}`);
}
function finish() {
  console.log(`vfx codegen parity: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
}
// Strings, null, {src} and {err} alike; objects made inside the vm compare by their JSON.
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const sortedJSON = (v) => JSON.stringify(v, (k, x) => (x && typeof x === 'object' && !Array.isArray(x)
  ? Object.fromEntries(Object.keys(x).sort().map((key) => [key, x[key]])) : x));

// One hunk per run of changed lines, two lines of context: enough to read a declared difference at a glance.
function lineDiff(a, b) {
  const x = a.split('\n'), y = b.split('\n');
  let i = 0;
  while (i < x.length && i < y.length && x[i] === y[i]) i++;
  let j = 0;
  while (j < x.length - i && j < y.length - i && x[x.length - 1 - j] === y[y.length - 1 - j]) j++;
  const out = [`@@ line ${i + 1} @@`];
  for (let k = Math.max(0, i - 2); k < i; k++) out.push('  ' + x[k]);
  for (let k = i; k < x.length - j; k++) out.push('- ' + x[k]);
  for (let k = i; k < y.length - j; k++) out.push('+ ' + y[k]);
  for (let k = x.length - j; k < Math.min(x.length, x.length - j + 2); k++) out.push('  ' + x[k]);
  return out.join('\n');
}

// ---- the module under test ------------------------------------------------------------------------------------------
let codegen;
try {
  codegen = await import(pathToFileURL(at('scripts/vfx-codegen.js')).href);
} catch (e) {
  check('scripts/vfx-codegen.js loads as an ES module', false, e.message.split('\n')[0]);
  finish();
}
check('vfx-codegen exports createBenchCodegen', typeof codegen.createBenchCodegen === 'function');
if (typeof codegen.createBenchCodegen !== 'function') finish();

// ---- the chunks, exactly as the bench receives them -----------------------------------------------------------------
const CHUNK_DIR = at('design/vfx-chunks');
function chunksLikeBifrost() {   // a twin of scripts/bifrost_ui.py _vfx_chunks_read, line for line
  const names = readdirSync(CHUNK_DIR).filter((f) => f.endsWith('.glsl')).sort();
  return names.map((fn) => {
    try {
      // Python's text-mode open() reads \r\n and a lone \r as \n (universal newlines), and some chunks are CRLF on disk.
      const txt = readFileSync(join(CHUNK_DIR, fn), 'utf8').replace(/\r\n?/g, '\n');
      const cut = txt.indexOf('\n');
      const head = cut < 0 ? txt : txt.slice(0, cut);
      const body = cut < 0 ? '' : txt.slice(cut + 1);
      const meta = head.startsWith('//!') ? JSON.parse(head.slice(3).trim()) : {};
      meta.body = body.trim();
      if (!('name' in meta)) meta.name = fn.slice(0, -5);
      if (!('kind' in meta)) meta.kind = 'modifier';
      return meta;
    } catch (e) {
      return { name: fn.slice(0, -5), kind: 'broken', note: String(e).slice(0, 160), body: '' };
    }
  });
}
function chunksFromPython() {
  const code = 'import json, sys; sys.path.insert(0, "scripts"); import bifrost_ui as B; ' +
    'sys.stdout.write("\\n@@CHUNKS@@" + json.dumps(B._vfx_chunks_read()))';
  const r = spawnSync('py', ['-c', code], { cwd: ROOT, encoding: 'utf8', timeout: 60000 });
  if (r.error || r.status !== 0) return { error: r.error ? r.error.message : String(r.stderr || '').trim().split('\n').pop() };
  const cut = r.stdout.lastIndexOf('@@CHUNKS@@');
  if (cut < 0) return { error: 'no marker in the output' };
  try { return { chunks: JSON.parse(r.stdout.slice(cut + 10)) }; } catch (e) { return { error: 'not JSON: ' + e.message }; }
}
const twinChunks = chunksLikeBifrost();
const py = chunksFromPython();
let CHUNKS = twinChunks;
if (py.chunks) {
  check('the JS twin of _vfx_chunks_read agrees with bifrost_ui.py', sortedJSON(py.chunks) === sortedJSON(twinChunks));
  CHUNKS = py.chunks;
  console.log(`chunks: ${CHUNKS.length} records from bifrost_ui._vfx_chunks_read (cross-checked against the JS twin)`);
} else {
  console.log(`chunks: ${CHUNKS.length} records from the JS twin (py did not run: ${py.error})`);
}
check('the bench has chunks to compare', CHUNKS.length >= 20, `${CHUNKS.length}`);
const byKind = (k) => CHUNKS.filter((c) => c.kind === k).map((c) => c.name);
const SOURCES = byKind('source');
const NON_HELPERS = CHUNKS.filter((c) => c.kind !== 'helper').map((c) => c.name);
const MODIFIERS = byKind('modifier');

// ---- the page's own code, lifted out of scripts/vfx.html ------------------------------------------------------------
const PAGE = readFileSync(at('scripts/vfx.html'), 'utf8');
// A top-level function exactly as the page writes it: from `function NAME(` to the shortest prefix that parses on its
// own (a one-liner ends on its own line; a longer one at a closing brace in column 0).
function lift(name) {
  const m = new RegExp(`^(?:async )?function ${name}\\(`, 'm').exec(PAGE);
  if (!m) throw new Error(`scripts/vfx.html has no top-level function ${name}()`);
  const ends = [PAGE.indexOf('\n', m.index)];
  for (let k = PAGE.indexOf('\n}', m.index); k >= 0 && ends.length < 500; k = PAGE.indexOf('\n}', k + 1)) ends.push(k + 2);
  for (const end of ends) {
    const text = PAGE.slice(m.index, end);
    try { new vm.Script(text); return text; } catch { /* not a whole function yet */ }
  }
  throw new Error(`could not lift ${name}() out of scripts/vfx.html`);
}
// A one-line top-level `var NAME = ...;` (the page's constants and the CODEGEN record).
function liftVar(name) {
  const m = new RegExp(`^var ${name} *=[^\\n]*`, 'm').exec(PAGE);
  if (!m) throw new Error(`scripts/vfx.html has no one-line top-level var ${name}`);
  return m[0];
}
const EDITING = ['chunkBy', 'gchunk', 'portsOf', 'edgeInto', 'reaches', 'addNodeNoHist', 'linkOptions', 'applyLink', 'connect'];
const LEGACY = ['buildGLSL', 'buildGraphGLSL', 'thumbShaderFor'];
const DISPATCH = ['setCodegen', 'codegenFallback', 'loadCodegen', 'codegenGen', 'codegenPick', 'genChainGLSL',
  'genGraphGLSL', 'genThumbGLSL'];

// A fresh copy of the page's globals and functions. el() hands back one fake element per id.
function pageSandbox(chunks, { dispatch = false } = {}) {
  const els = {};
  const warnings = [];
  const ctx = {
    CHUNKS: chunks, chain: [], G: { nodes: [], edges: [], seq: 1 },
    histPush() {}, renderGraph() {}, drawWires() {}, gmsg() {},
    console: { log() {}, warn(...a) { warnings.push(a); }, error() {} },
    location: { search: '' }, URLSearchParams, warnings,
  };
  ctx.el = (id) => (els[id] = els[id] || { id, value: '', textContent: '', className: '' });
  vm.createContext(ctx);
  const names = [...EDITING, ...LEGACY, ...(dispatch ? DISPATCH : [])];
  const vars = ['THUMB_REF', 'THUMB_REF_B', ...(dispatch ? ['CODEGEN'] : [])];
  vm.runInContext(names.map(lift).join('\n') + '\n' + vars.map(liftVar).join('\n'), ctx);
  return ctx;
}
let page;
try {
  page = pageSandbox(CHUNKS);
} catch (e) {
  check('the legacy generators lift out of scripts/vfx.html', false, e.message);
  finish();
}
const legacyChain = (source, items) => { page.el('csource').value = source; page.chain = items.slice(); return page.buildGLSL(); };
const legacyGraph = (G) => { page.G = JSON.parse(JSON.stringify(G)); return page.buildGraphGLSL(); };
const legacyThumb = (c) => page.thumbShaderFor(c);

// ---- the shared codegen -----------------------------------------------------------------------------------------------
let gen;
try {
  gen = codegen.createBenchCodegen(modlib, CHUNKS);
} catch (e) {
  check('createBenchCodegen builds over the repo chunks', false, e.message);
  finish();
}
check('the composer quarantined none of the repo chunks', gen.problems.length === 0, JSON.stringify(gen.problems));
let refused = null;
try { codegen.createBenchCodegen(null, CHUNKS); } catch (e) { refused = e.message; }
check('without modlib the codegen refuses by name (the page then keeps its legacy writers)',
  refused !== null && /modlib/.test(refused), String(refused));

// Reading a chunk through the bench's record (header JSON + stripped body) is lossless: modlib sees the same module it
// sees when it reads the file itself.
for (const c of CHUNKS) {
  const m = gen.library.modules.get(c.name);
  let fileModule = null;
  try { fileModule = modlib.parseModule(readFileSync(join(CHUNK_DIR, c.name + '.glsl'), 'utf8'), c.name); } catch { /* named below */ }
  check(`chunk ${c.name}: modlib reads the bench record as it reads the file`, !!m && !!fileModule &&
    same(m.provides, fileModule.provides) && same(m.calls, fileModule.calls) && m.kind === fileModule.kind &&
    m.body === c.body, m ? '' : 'missing from the library');
}

// ---- 1. thumbnails: every chunk ---------------------------------------------------------------------------------------
let n = 0;
for (const c of CHUNKS) {
  const want = legacyThumb(c);
  let got;
  try { got = gen.thumb(c, { ref: page.THUMB_REF, refB: page.THUMB_REF_B }); } catch (e) { got = 'threw: ' + e.message; }
  check(`thumb ${c.name} (${c.kind}) is byte-identical`, want === got, typeof got === 'string' ? lineDiff(want, got) : '');
  n++;
}
// With the calibration ramp missing, both writers refuse (the page's own tile code catches it and lists the chunk).
{
  const bare = CHUNKS.filter((c) => c.name !== page.THUMB_REF);
  const p2 = pageSandbox(bare), g2 = codegen.createBenchCodegen(modlib, bare);
  const mod = bare.find((c) => c.kind === 'modifier');
  let a = null, b = null;
  try { p2.thumbShaderFor(mod); } catch (e) { a = e; }
  try { g2.thumb(mod, { ref: p2.THUMB_REF, refB: p2.THUMB_REF_B }); } catch (e) { b = e; }
  check('thumb without its reference chunk: both writers throw', a !== null && b !== null, `legacy ${a} / modlib ${b}`);
}

// ---- 2. chains: every source alone, every source with every chunk, every group, every saved chain ---------------------
const GROUPS = JSON.parse(readFileSync(at('design/vfx-groups.json'), 'utf8'));
const COMPOS = JSON.parse(readFileSync(at('design/vfx-compositions.json'), 'utf8'));
const chains = [['(no source)', '', []], ['(unknown source)', 'no-such-chunk', ['tanh-tonemap']]];
for (const s of SOURCES) {
  chains.push([`${s} alone`, s, []]);
  chains.push([`${s} + every modifier`, s, MODIFIERS]);
  chains.push([`${s} + an unknown name`, s, ['tanh-tonemap', 'no-such-chunk', 'vignette-cubic']]);
  for (const c of NON_HELPERS) chains.push([`${s} + ${c}`, s, [c]]);
  for (const [g, items] of Object.entries(GROUPS)) chains.push([`${s} + group "${g}"`, s, items]);
}
for (const [k, v] of Object.entries(COMPOS)) chains.push([`saved chain "${k}"`, v.source || '', v.chain || []]);
for (const [label, s, items] of chains) {
  const want = legacyChain(s, items);
  let got;
  try { got = gen.chain(s, items); } catch (e) { got = 'threw: ' + e.message; }
  check(`chain ${label} is byte-identical`, same(want, got), typeof want === 'string' && typeof got === 'string' ? lineDiff(want, got) : `${want} / ${got}`);
}
check('every saved chain and group was compared', Object.keys(COMPOS).length >= 1 && Object.keys(GROUPS).length >= 1);

// ---- 3. graphs: every saved graph, one node per chunk, and graphs built by the page's own editing code -----------------
// THE DECLARED DIFFERENCES. Anything else that differs between the writers is a failure.
const DECLARED = [{
  id: 'mask-port',
  defect: 'census D1 (research/in-flight/shader-school-2026-10-13/arc-vfx-bench.md, section 6)',
  rule: "a wire from a mask's m output feeds the receiving block's m, never its colour: colB stays unwired " +
    '(vec3(0.)) and the block declares float m = <mask>_m',
  pixels: 'none with the shipped chunks: a mask block never writes col, so the legacy colB = <mask>_col was already ' +
    'vec3(0.); the blend now SEES the mask, and no shipped blend reads m yet (mix-blend still mixes at 0.5)',
}];
// The declared rewrite, applied to the legacy text: in the block of every node whose colB port is fed from a mask's m,
// `vec3 colB = <A>_col;` becomes `vec3 colB = vec3(0.);` and the block's m is the mask's.
function declaredRewrite(legacy, G) {
  if (!legacy || legacy.err) return legacy;
  const lines = legacy.src.split('\n');
  for (const node of G.nodes) {
    const eB = G.edges.filter((e) => e.to === node.id && e.toPort === 'colB')[0];
    const c = CHUNKS.find((x) => x.name === node.chunk);
    if (!eB || eB.fromPort !== 'm' || !c || !(c.in && c.in.colB)) continue;
    const head = lines.indexOf(`  // ---- ${c.name} (${node.id}) ----`);
    if (head < 0) continue;   // not reached from OUTPUT: no block was written
    const k = lines.indexOf(`    vec3 colB = ${eB.from}_col;`, head);
    lines[k] = '    vec3 colB = vec3(0.);';
    if (lines[k + 1] === '    float m = 0.;') lines[k + 1] = `    float m = ${eB.from}_m;`;
    else lines.splice(k + 1, 0, `    float m = ${eB.from}_m;`);
  }
  return { src: lines.join('\n') };
}
const maskWired = (G) => G.edges.some((e) => e.toPort === 'colB' && e.fromPort === 'm');
function compareGraph(label, G) {
  const want = legacyGraph(G);
  let twin, shipped;
  try { twin = gen.graph(G, { maskFix: false }); } catch (e) { twin = { threw: e.message }; }
  try { shipped = gen.graph(G); } catch (e) { shipped = { threw: e.message }; }
  const diff = (a, b) => (a && b && a.src && b.src ? lineDiff(a.src, b.src) : `${JSON.stringify(a).slice(0, 200)} / ${JSON.stringify(b).slice(0, 200)}`);
  check(`graph ${label}: maskFix off is byte-identical to legacy`, same(want, twin), diff(want, twin));
  const expect = declaredRewrite(want, G);
  check(`graph ${label}: shipped output = legacy + the declared mask-port fix only`, same(expect, shipped), diff(expect, shipped));
  return { want, shipped };
}

const SAVED = JSON.parse(readFileSync(at('design/vfx-graphs.json'), 'utf8'));
for (const [k, G] of Object.entries(SAVED)) {
  const { want, shipped } = compareGraph(`saved "${k}"`, G);
  if (!maskWired(G)) check(`saved graph "${k}" is untouched by the declared fix`, same(want, shipped));
}
check('every saved graph was compared', Object.keys(SAVED).length >= 1);

// One node per chunk: a source straight into OUTPUT; a modifier, domain or blend fed by a source; a mask alone.
const OUT = { id: 'n1', chunk: '__out', x: 420, y: 140 };
for (const c of CHUNKS.filter((x) => x.kind !== 'helper')) {
  const nodes = [OUT, { id: 'n2', chunk: c.name, x: 20, y: 20 }, { id: 'n3', chunk: SOURCES[0], x: 20, y: 140 },
    { id: 'n4', chunk: SOURCES[1] || SOURCES[0], x: 20, y: 250 }];
  const edges = [{ from: 'n2', fromPort: 'col', to: 'n1', toPort: 'col', type: 'vec3' }];
  if (c.in && c.in.col) edges.push({ from: 'n3', fromPort: 'col', to: 'n2', toPort: 'col', type: 'vec3' });
  if (c.in && c.in.colB) edges.push({ from: 'n4', fromPort: 'col', to: 'n2', toPort: 'colB', type: 'vec3' });
  if (c.kind === 'domain') edges.push({ from: 'n2', fromPort: 'uv', to: 'n3', toPort: 'uv', type: 'vec2' });
  compareGraph(`one ${c.kind} node ${c.name}`, { nodes, edges, seq: 5 });
}
compareGraph('no output node', { nodes: [{ id: 'n2', chunk: SOURCES[0] }], edges: [], seq: 3 });
compareGraph('nothing wired into OUTPUT', { nodes: [OUT, { id: 'n2', chunk: SOURCES[0] }], edges: [], seq: 3 });

// THE DECLARED FIXTURE: the saved blend-demo, then "use as mask" pressed from its unwired radial-mask onto the sphere,
// through the page's own applyLink (so the edge is exactly the one the HUD writes).
function pressUseAsMask(G, maskId, targetId) {
  page.G = JSON.parse(JSON.stringify(G));
  const A = page.G.nodes.find((x) => x.id === maskId), B = page.G.nodes.find((x) => x.id === targetId);
  const opt = page.linkOptions(A, B).find((o) => o.mask);
  if (!opt) return null;
  page.applyLink(A, B, opt);
  return JSON.parse(JSON.stringify(page.G));
}
const demo = SAVED['blend-demo'];
const maskId = demo && (demo.nodes.find((x) => x.chunk === 'radial-mask') || {}).id;
const sphereId = demo && (demo.nodes.find((x) => x.chunk === 'sphere-glass') || {}).id;
const fixture = demo && maskId && sphereId ? pressUseAsMask(demo, maskId, sphereId) : null;
check('the declared fixture builds through the page\'s "use as mask" button', !!fixture && maskWired(fixture));
if (fixture) {
  const { want, shipped } = compareGraph('declared fixture "blend-demo + use as mask"', fixture);
  check('the declared mask-port difference is real (the fixture differs from legacy)', !same(want, shipped));
  if (want.src && shipped.src) {
    console.log(`\nDECLARED DIFFERENCE ${DECLARED[0].id} -- ${DECLARED[0].defect}`);
    console.log(`  rule:   ${DECLARED[0].rule}`);
    console.log(`  pixels: ${DECLARED[0].pixels}`);
    console.log(lineDiff(want.src, shipped.src).split('\n').map((l) => '    ' + l).join('\n') + '\n');
  }
}

// Random graphs, built only by what the page lets a hand do: add a node, drag a wire between sockets of one type
// (connect), drop a node on a node and press a HUD button (linkOptions + applyLink, the mask button included), grab a
// wire and let go of it, delete a node. A seeded generator, so a failure names a seed that reproduces it.
function mulberry32(a) {
  return () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const sock = (node, dir, port, type) => ({ dataset: { node, dir, port, type } });
const MASKS = byKind('mask');
function randomGraph(seed) {
  const rnd = mulberry32(seed);
  const pick = (xs) => xs[Math.floor(rnd() * xs.length)];
  page.G = { nodes: [{ id: 'n1', chunk: '__out', x: 420, y: 140 }], edges: [], seq: 2 };
  const steps = 4 + Math.floor(rnd() * 14);
  for (let s = 0; s < steps; s++) {
    const r = rnd(), G = page.G;
    if (r < 0.3 || G.nodes.length < 3) { page.addNodeNoHist(rnd() < 0.15 ? pick(MASKS) : pick(NON_HELPERS), 0, 0); continue; }
    const A = pick(G.nodes), B = pick(G.nodes);
    if (A === B) continue;
    if (r < 0.65) {
      const po = page.portsOf(A).out, pi = page.portsOf(B).in, pairs = [];
      for (const p of Object.keys(po)) for (const q of Object.keys(pi)) if (po[p] === pi[q]) pairs.push([p, q, po[p]]);
      if (pairs.length) { const [p, q, t] = pick(pairs); page.connect(sock(A.id, 'out', p, t), sock(B.id, 'in', q, t)); }
    } else if (r < 0.88) {
      const opts = page.linkOptions(A, B);
      if (opts.length) page.applyLink(A, B, pick(opts));
    } else if (r < 0.94) {
      if (G.edges.length) G.edges.splice(Math.floor(rnd() * G.edges.length), 1);
    } else if (A.chunk !== '__out') {
      G.nodes = G.nodes.filter((m) => m !== A);
      G.edges = G.edges.filter((e) => e.from !== A.id && e.to !== A.id);
    }
  }
  return JSON.parse(JSON.stringify(page.G));
}
let graphs = 0, masked = 0, built = 0;
for (let seed = 1; seed <= 600; seed++) {
  const G = randomGraph(seed);
  const { want } = compareGraph(`random seed ${seed}`, G);
  graphs++;
  if (maskWired(G)) masked++;
  if (want && want.src) built++;
}
check('the random graphs exercise the mask button often enough to mean something', masked >= 25, `${masked} of ${graphs}`);
check('most random graphs reach OUTPUT and compile to text', built >= 150, `${built} of ${graphs}`);
console.log(`graphs: ${graphs} random (${masked} with a mask wire, ${built} wired to OUTPUT), ${Object.keys(SAVED).length} saved, ` +
  `${CHUNKS.length - byKind('helper').length} one-node; chains: ${chains.length}; thumbs: ${n}`);

// ---- 4. the page: dispatch, fallback and the status line ------------------------------------------------------------
// Every build goes through one dispatcher per writer; nothing calls a legacy writer directly any more.
for (const [legacy, dispatcher] of [['buildGLSL', 'genChainGLSL'], ['buildGraphGLSL', 'genGraphGLSL'], ['thumbShaderFor', 'genThumbGLSL']]) {
  const calls = (PAGE.match(new RegExp(`\\b${legacy}\\(`, 'g')) || []).length;
  let inside = 0;
  try { inside = (lift(dispatcher).match(new RegExp(`\\b${legacy}\\(`, 'g')) || []).length; } catch { /* named below */ }
  check(`${legacy}() is called only from ${dispatcher}()`, calls === 2 && inside === 1, `${calls - 1} call(s), ${inside} inside the dispatcher`);
}
check('the page has a codegen status line', /id="codegenline"/.test(PAGE));
check('the page boots the codegen loader', /\bloadCodegen\(\)/.test(PAGE));

let dp;
try { dp = pageSandbox(CHUNKS, { dispatch: true }); } catch (e) { check('the dispatchers lift out of scripts/vfx.html', false, e.message); finish(); }
const status = () => dp.el('codegenline').textContent;
const realImport = (u) => (u === '/vfx-codegen.js' ? import(pathToFileURL(at('scripts/vfx-codegen.js')).href)
  : u === '/glsl/modlib.js' ? import(pathToFileURL(at('arsenal/web/glsl/modlib.js')).href)
  : Promise.reject(new Error(`${u}: HTTP 404`)));
const compo = Object.values(COMPOS)[0];
dp.el('csource').value = compo.source; dp.chain = compo.chain.slice();
check('before the loader runs the page writes legacy GLSL', dp.genChainGLSL() === dp.buildGLSL());

// ?codegen=legacy: forced, and the composer is never even fetched.
dp.location.search = '?codegen=legacy';
let fetched = 0;
const forced = await dp.loadCodegen((u) => { fetched++; return realImport(u); });
check('?codegen=legacy forces the legacy writers without fetching the composer', forced === false && fetched === 0 &&
  dp.CODEGEN.mode === 'legacy' && /legacy/.test(status()) && /forced/.test(status()), status());

// The bench at 8787 today: bifrost_ui.py has no /glsl/ route, so modlib 404s; the page keeps legacy and says why.
dp.location.search = '';
const at8787 = await dp.loadCodegen((u) => (u === '/glsl/modlib.js' ? Promise.reject(new Error('HTTP 404')) : realImport(u)));
check('when modlib cannot load, the page stays on legacy and the status line says so', at8787 === false &&
  dp.CODEGEN.mode === 'legacy' && /legacy/.test(status()) && /\/glsl\//.test(status()), status());
check('...and its builds are the legacy text', dp.genChainGLSL() === dp.buildGLSL());

// With the routes mounted: modlib by default, byte-identical, the declared fix live on the graph card.
const loaded = await dp.loadCodegen(realImport);
check('with modlib served, the page selects the shared composer by default', loaded === true && dp.CODEGEN.mode === 'modlib' &&
  /modlib/.test(status()), status());
check('the Compose card writes the legacy bytes through the composer', dp.genChainGLSL() === dp.buildGLSL());
for (const c of CHUNKS.slice(0, 8)) check(`the thumb writer agrees for ${c.name}`, dp.genThumbGLSL(c) === dp.thumbShaderFor(c));
if (fixture) {
  dp.G = JSON.parse(JSON.stringify(fixture));
  const shippedPage = dp.genGraphGLSL();
  check('the Graph card ships the declared mask-port fix', same(shippedPage, gen.graph(fixture)) &&
    !same(shippedPage, dp.buildGraphGLSL()));
  dp.G = JSON.parse(JSON.stringify(demo));
  check('...and an unmasked saved graph is byte-identical', same(dp.genGraphGLSL(), dp.buildGraphGLSL()));
}
check('no fallback happened on honest data', dp.warnings.length === 0, JSON.stringify(dp.warnings).slice(0, 300));

// A composer that drifts is caught on the build it drifts on: the page uses legacy for that build and says so in red.
dp.CODEGEN.gen = { chain: () => 'drifted', graph: () => ({ src: 'drifted' }), thumb: () => 'drifted' };
dp.CODEGEN.genOf = dp.CHUNKS;
check('a drifting composer is caught: the build falls back to the legacy bytes', dp.genChainGLSL() === dp.buildGLSL());
check('...the status line names the fallback', /legacy for this chain/.test(status()) && /err/.test(dp.el('codegenline').className), status());
check('...and the console carries both texts', dp.warnings.length === 1);
dp.CODEGEN.gen = { chain() { throw new Error('boom'); } };
check('a composer that throws is caught too', dp.genChainGLSL() === dp.buildGLSL() && /boom/.test(status()), status());

finish();
