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
import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
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
// Every changed run as its own hunk (a longest-common-subsequence walk over lines), two lines of context each: the
// printed record of the declared difference, which touches a few lines spread through a long text.
function hunks(a, b) {
  const x = a.split('\n'), y = b.split('\n');
  const L = Array.from({ length: x.length + 1 }, () => new Int32Array(y.length + 1));
  for (let i = x.length - 1; i >= 0; i--) {
    for (let j = y.length - 1; j >= 0; j--) L[i][j] = x[i] === y[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  }
  const ops = [];
  for (let i = 0, j = 0; i < x.length || j < y.length;) {
    if (i < x.length && j < y.length && x[i] === y[j]) { ops.push(['  ', x[i++]]); j++; }
    else if (i < x.length && (j === y.length || L[i + 1][j] >= L[i][j + 1])) ops.push(['- ', x[i++]]);
    else ops.push(['+ ', y[j++]]);
  }
  const keep = new Set();
  ops.forEach((o, k) => { if (o[0] !== '  ') for (let d = -2; d <= 2; d++) keep.add(k + d); });
  const out = [];
  let last = -2;
  ops.forEach((o, k) => {
    if (!keep.has(k)) return;
    if (k !== last + 1) out.push('@@');
    out.push(o[0] + o[1]);
    last = k;
  });
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

// ---- the declared differences --------------------------------------------------------------------------------------
// THE DECLARED DIFFERENCES. Anything else that differs between the writers is a failure.
const DECLARED = [{
  id: 'mask-port',
  defect: 'census D1 (research/in-flight/shader-school-2026-10-13/arc-vfx-bench.md, section 6), and the S5 review ' +
    '(item 3: every block that has a colB gets a default m, so a blend that reads m compiles everywhere)',
  rule: "a wire from a mask's m output feeds the receiving block's m, never its colour: colB stays unwired " +
    '(vec3(0.)) and the block declares float m = <mask>_m. Every other block with a colB input (graph) and every ' +
    'blend tile declares float m = 0.5, the even mix mix-blend uses today',
  pixels: 'none with the shipped chunks: a mask block never writes col, so the legacy colB = <mask>_col was already ' +
    'vec3(0.), and no shipped blend reads m yet (mix-blend still mixes at a constant 0.5). When mix-blend reads m, an ' +
    'unwired blend keeps its 0.5 mix and a wired one follows the mask',
}];
// The bench's unwired mask value: the 0.5 mix-blend mixes at today, so "mix-blend reads m" moves no unwired pixel.
const M_DEFAULT = '0.5';
// The declared rewrite, applied to the legacy text: in the block of every node with a colB input, a `float m` follows
// the colB line (replacing the `float m = 0.;` an m-output block already declares there). When the colB port is fed
// from a mask's m, `vec3 colB = <A>_col;` becomes `vec3 colB = vec3(0.);` and the block's m is the mask's; otherwise
// m is the default.
function declaredRewrite(legacy, G) {
  if (!legacy || legacy.err) return legacy;
  const lines = legacy.src.split('\n');
  for (const node of G.nodes) {
    const c = CHUNKS.find((x) => x.name === node.chunk);
    if (!c || !(c.in && c.in.colB)) continue;
    const head = lines.indexOf(`  // ---- ${c.name} (${node.id}) ----`);
    if (head < 0) continue;   // not reached from OUTPUT: no block was written
    const eB = G.edges.filter((e) => e.to === node.id && e.toPort === 'colB')[0];
    const fromMask = !!eB && eB.fromPort === 'm';
    const k = lines.findIndex((l, i) => i > head && l.startsWith('    vec3 colB = '));
    if (fromMask) lines[k] = '    vec3 colB = vec3(0.);';
    const m = fromMask ? `    float m = ${eB.from}_m;` : `    float m = ${M_DEFAULT};`;
    if (lines[k + 1] === '    float m = 0.;') lines[k + 1] = m;
    else lines.splice(k + 1, 0, m);
  }
  return { src: lines.join('\n') };
}
// The same declared difference on a tile: a blend tile's block declares the default m beside its colB.
const BLEND_TILE_BLOCK = '  { vec3 col=_raw; vec3 colB=_b; float alpha=1.;\n';
function declaredThumbRewrite(legacy, c) {
  if (typeof legacy !== 'string' || !c || c.kind !== 'blend') return legacy;
  return legacy.replace(BLEND_TILE_BLOCK, `  { vec3 col=_raw; vec3 colB=_b; float alpha=1.; float m=${M_DEFAULT};\n`);
}
// The legacy text again from a shipped one: drop exactly the default-m lines the declared difference adds.
const withoutDefaultM = (r) => (r && r.src ? { src: r.src.split('\n').filter((l) => l !== `    float m = ${M_DEFAULT};`).join('\n') } : r);

// ---- 1. thumbnails: every chunk ---------------------------------------------------------------------------------------
let n = 0;
for (const c of CHUNKS) {
  const want = legacyThumb(c);
  let twin, got;
  try { twin = gen.thumb(c, { ref: page.THUMB_REF, refB: page.THUMB_REF_B, maskFix: false }); } catch (e) { twin = 'threw: ' + e.message; }
  try { got = gen.thumb(c, { ref: page.THUMB_REF, refB: page.THUMB_REF_B }); } catch (e) { got = 'threw: ' + e.message; }
  check(`thumb ${c.name} (${c.kind}): maskFix off is byte-identical`, want === twin, typeof twin === 'string' ? lineDiff(want, twin) : '');
  const expect = declaredThumbRewrite(want, c);
  check(`thumb ${c.name} (${c.kind}): shipped = legacy + the declared default m only`, expect === got,
    typeof got === 'string' ? lineDiff(expect, got) : '');
  if (c.kind === 'blend') check(`thumb ${c.name}: the declared default m is really there`, expect !== want);
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
  if (!maskWired(G)) check(`saved graph "${k}" differs from legacy only by the default m lines`, same(want, withoutDefaultM(shipped)));
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
    console.log(hunks(want.src, shipped.src).split('\n').map((l) => '    ' + l).join('\n') + '\n');
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
for (const c of CHUNKS.slice(0, 8)) {
  check(`the thumb writer ships legacy + the declared default m for ${c.name}`,
    dp.genThumbGLSL(c) === declaredThumbRewrite(dp.thumbShaderFor(c), c));
}
check('...a blend tile among them (add-blend), so the default m is shipped by the page',
  CHUNKS.slice(0, 8).some((c) => c.kind === 'blend'));
if (fixture) {
  dp.G = JSON.parse(JSON.stringify(fixture));
  const shippedPage = dp.genGraphGLSL();
  check('the Graph card ships the declared mask-port fix', same(shippedPage, gen.graph(fixture)) &&
    !same(shippedPage, dp.buildGraphGLSL()));
  dp.G = JSON.parse(JSON.stringify(demo));
  check('...and an unmasked saved graph ships legacy + the default m only',
    same(dp.genGraphGLSL(), declaredRewrite(dp.buildGraphGLSL(), demo)));
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

// The red line reports one build, not the session: the next build that matches the legacy bytes clears it (S5 review
// item 2; before, one fallback left "legacy for this chain" up for good, over builds that were shipping modlib text).
const isRed = () => /err/.test(dp.el('codegenline').className);
dp.CODEGEN.gen = null;                       // the honest composer again: codegenGen rebuilds it over CHUNKS
const cleared = dp.genChainGLSL();
check('the next byte-identical build clears the red status line', cleared === dp.buildGLSL() && !isRed() &&
  dp.CODEGEN.mode === 'modlib' && /^codegen: modlib/.test(status()) && !/legacy for this/.test(status()), status());
dp.CODEGEN.gen = { graph: () => ({ src: 'drifted' }) };
dp.CODEGEN.genOf = dp.CHUNKS;
dp.G = JSON.parse(JSON.stringify(demo));
dp.genGraphGLSL();
const wentRed = isRed();
dp.CODEGEN.gen = null;
const back = dp.genGraphGLSL();
check('...and so does a graph build, whose shipped text carries the declared difference', wentRed && !isRed() &&
  same(back, gen.graph(demo)) && /^codegen: modlib/.test(status()), status());

// ---- 5. the snippet ABI: m is declared by the writer, never by a chunk -------------------------------------------------
// S5 review item 3. The planned "mix-blend reads m" change must compile in a blend tile and in a graph with no mask
// wired, and a chunk that declared its own `float m` would collide with the writer's on the shipped path only (the page
// compares the mask-fix-off text, which has no m), so it is refused here instead.
const declaresM = (body) => /\bfloat[ \t\r\n]+m\b/.test(body.replace(/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, ' '));
for (const c of CHUNKS) check(`chunk ${c.name} does not declare m itself (the writer declares it)`, !declaresM(c.body || ''));
{
  const READS_M = 'col = mix(col, colB, m);';
  const chunksM = CHUNKS.map((c) => (c.name === 'mix-blend' ? { ...c, body: READS_M } : c));
  const genM = codegen.createBenchCodegen(modlib, chunksM);
  const mixB = chunksM.find((c) => c.name === 'mix-blend');
  // Is `float m` declared in the body's own block, above the body? Walk up from the body line to the block's opening.
  const mDeclaredAbove = (src, bodyLine) => {
    const lines = src.split('\n');
    let k = lines.findIndex((l) => l.trim() === bodyLine);
    if (k < 0) return false;
    for (let depth = 0; --k >= 0;) {
      const l = lines[k];
      if (depth === 0 && /\bfloat m ?=/.test(l)) return true;
      depth += (l.match(/}/g) || []).length - (l.match(/{/g) || []).length;
      if (depth < 0) return false;          // left the block without meeting a declaration
    }
    return false;
  };
  const tile = genM.thumb(mixB, { ref: page.THUMB_REF, refB: page.THUMB_REF_B });
  check('a blend tile that reads m declares it (the default) in the blend\'s block', mDeclaredAbove(tile, READS_M), tile.slice(-600));
  const one = { nodes: [OUT, { id: 'n2', chunk: 'mix-blend' }, { id: 'n3', chunk: SOURCES[0] }, { id: 'n4', chunk: SOURCES[1] }],
    edges: [{ from: 'n2', fromPort: 'col', to: 'n1', toPort: 'col', type: 'vec3' },
      { from: 'n3', fromPort: 'col', to: 'n2', toPort: 'col', type: 'vec3' },
      { from: 'n4', fromPort: 'col', to: 'n2', toPort: 'colB', type: 'vec3' }], seq: 5 };
  const unwired = genM.graph(one);
  check('a graph blend that reads m with no mask wired declares the default', !!unwired.src &&
    mDeclaredAbove(unwired.src, READS_M) && unwired.src.includes(`    float m = ${M_DEFAULT};`), JSON.stringify(unwired).slice(0, 300));
  const bare = { nodes: [OUT, { id: 'n2', chunk: 'mix-blend' }], edges: [{ from: 'n2', fromPort: 'col', to: 'n1', toPort: 'col', type: 'vec3' }], seq: 3 };
  check('...and so does one with nothing wired into it at all', mDeclaredAbove(genM.graph(bare).src || '', READS_M));
  if (fixture) {
    const wired = genM.graph(fixture);
    const maskEdge = fixture.edges.find((e) => e.toPort === 'colB' && e.fromPort === 'm');
    check('a graph blend fed by a mask declares m from the mask', !!wired.src && mDeclaredAbove(wired.src, READS_M) &&
      wired.src.includes(`    float m = ${maskEdge.from}_m;`));
  }
  check('the legacy-equivalent twin declares no m (it must stay the legacy bytes)',
    !mDeclaredAbove(genM.graph(one, { maskFix: false }).src, READS_M) &&
    !mDeclaredAbove(genM.thumb(mixB, { ref: page.THUMB_REF, refB: page.THUMB_REF_B, maskFix: false }), READS_M));
}

// ---- 6. the route snippet for bifrost_ui.py ---------------------------------------------------------------------------
// S5 review item 4: os.path.commonpath raises ValueError when a link inside the folder resolves onto another drive,
// which made the route a 500 instead of a 404. The snippet's own code is run here, exactly as Heimdall would paste it.
{
  const md = readFileSync(at('research/in-flight/shader-school-2026-10-13/snippet-bifrost-glsl-route.md'), 'utf8');
  const blocks = [...md.matchAll(/```python\n([\s\S]*?)```/g)].map((m) => m[1]);
  const route = blocks.find((b) => b.includes('def _glsl_route('));
  check('the snippet carries the _glsl_route function', !!route);
  const prog = [
    'import json, os, sys',
    'REPO = sys.argv[1]',
    'exec(sys.stdin.read())',
    'out = {"modlib": _glsl_route("/glsl/modlib.js"), "up": _glsl_route("/glsl/../scripts/bifrost_ui.py")}',
    'def other_drive(paths):',
    '    raise ValueError("Paths don\'t have the same drive")',
    'os.path.commonpath = other_drive',
    'try:',
    '    out["other_drive"] = _glsl_route("/glsl/modlib.js")',
    'except Exception as exc:',
    '    out["other_drive"] = "raised " + type(exc).__name__',
    'sys.stdout.write("@@ROUTE@@" + json.dumps(out))',
  ].join('\n');
  const r = route ? spawnSync('py', ['-c', prog, ROOT], { input: route, encoding: 'utf8', timeout: 60000 }) : null;
  if (r && !r.error && r.status === 0 && r.stdout.includes('@@ROUTE@@')) {
    const out = JSON.parse(r.stdout.slice(r.stdout.lastIndexOf('@@ROUTE@@') + 9));
    check('the snippet serves modlib.js', same(out.modlib, ['arsenal/web/glsl/modlib.js', 'application/javascript']), JSON.stringify(out));
    check('the snippet refuses a traversal', out.up === null, JSON.stringify(out));
    check('the snippet answers a link onto another drive with None (a 404), not a ValueError (a 500)',
      out.other_drive === null, JSON.stringify(out.other_drive));
  } else if (route) {
    console.log(`snippet: not run (py did not run: ${r && (r.error ? r.error.message : String(r.stderr).trim().split('\n').pop())})`);
  }
}

// ---- 7. the order lint keeps the two helper orders in step ------------------------------------------------------------
// S5 review item 1: the writers order helper chunks by different rules (legacy: `order || 50`, ties by file name, no
// reordering for a call; the composer: order as written, ties by name, a callee first). Each shape below makes the two
// texts differ, which would quietly pin the bench to legacy; `py -m arsenal shader lib lint` must refuse every one, and
// passes the shipped chunks. The second declared difference the reviewer offered instead is not taken: legacy stays
// the default.
{
  const ORDER_CASES = [
    ['order 0', [{ name: 'zz-first', kind: 'helper', cat: 'math', order: 0, body: 'float zzFirst(float x){ return x * 0.625; }' }],
      /zz-first: .*order 0/],
    ['an equal-order prefix tie', [
      { name: 'tw', kind: 'helper', cat: 'math', order: 30, body: 'float twA(float x){ return x * 0.375; }' },
      { name: 'tw-b', kind: 'helper', cat: 'math', order: 30, body: 'float twB(float x){ return x * 0.125; }' }],
    /tw-b: .*prefix/],
    ['a helper calling a later helper', [
      { name: 'aa-early', kind: 'helper', cat: 'math', order: 5, body: 'float aaEarly(vec3 p){ return h31(p.zyx) * 0.5; }' }],
    /aa-early: .*h31\(\)/],
  ];
  const lintDir = (records) => {
    const dir = mkdtempSync(join(tmpdir(), 'vfx-order-'));
    try {
      for (const rec of records) writeFileSync(join(dir, `${rec.name}.glsl`), codegen.chunkSource(rec), 'utf8');
      const r = spawnSync('py', ['-m', 'arsenal', 'shader', 'lib', 'lint', '--dir', dir, '--json'],
        { cwd: ROOT, encoding: 'utf8', timeout: 120000 });
      if (r.error) return { skipped: r.error.message };
      try { return { status: r.status, problems: JSON.parse(r.stdout).problems }; } catch { return { status: r.status, problems: [String(r.stderr)] }; }
    } finally { rmSync(dir, { recursive: true, force: true }); }
  };
  const clean = lintDir(CHUNKS);
  if (clean.skipped) {
    console.log(`order lint: not run (py did not run: ${clean.skipped})`);
  } else {
    check('the order lint passes the shipped chunks', clean.status === 0 && clean.problems.length === 0, JSON.stringify(clean));
    for (const [label, extra, want] of ORDER_CASES) {
      // the bench reads chunk files in sorted file-name order (bifrost_ui._vfx_chunks_read)
      const chunks = [...CHUNKS, ...extra].sort((a, b) => (`${a.name}.glsl` < `${b.name}.glsl` ? -1 : 1));
      const p = pageSandbox(chunks), g = codegen.createBenchCodegen(modlib, chunks);
      p.el('csource').value = SOURCES[0]; p.chain = [];
      check(`order case "${label}": the two writers really differ`, p.buildGLSL() !== g.chain(SOURCES[0], []));
      const r = lintDir(chunks);
      check(`order case "${label}": lint refuses it`, r.status === 1 && r.problems.length === 1 && want.test(r.problems[0]),
        JSON.stringify(r));
    }
  }
}

finish();
