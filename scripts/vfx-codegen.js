// scripts/vfx-codegen.js -- the VFX bench's three GLSL writers, rebuilt on the shared module composer.
//
// WHY THIS FILE EXISTS. The bench (scripts/vfx.html) turns chunks into a shader in three places: the Compose chain
// (buildGLSL), the Graph card (buildGraphGLSL) and the writer behind palette tiles, the hover preview and CLI thumbs
// (thumbShaderFor). Each read the chunk library its own way, pasted its own copy of the uniform list, and put the
// helpers in order by their `order` number alone. This file is the same three writers standing on
// arsenal/web/glsl/modlib.js, the composer every other surface uses (the shader lab and the CLI today; First Light and
// the piano next): the chunks are parsed by the one parser, the helpers are put in order by the one resolver, and the
// uniform list is written once. In hardware terms: three hand-wired boards replaced by one bus, with the old boards
// left in the rack and a scope clipped across both outputs.
//
// THE HELPER ORDER IS THE LEGACY ORDER, BY LINT. The legacy writers sort helpers by `order || 50` (0 reads as 50) and
// break ties by file name, and never move a helper for a call; the resolver reads 0 as 0, breaks ties by name and puts
// a callee first. Rather than declare that as a second difference, `py -m arsenal shader lib lint` refuses a bench
// helper on which the two would disagree: order 0, two helpers of one order whose names and file names sort apart (one
// name a prefix of the other), and a helper that calls or needs a chunk the legacy writer emits later or never. For
// chunks that pass, both orders are the same list, so the legacy bytes stay the default.
//
// ZERO PIXEL CHANGE, PROVED AS ZERO BYTE CHANGE. tests/vfx_codegen_parity.test.mjs runs the page's own legacy writers
// (lifted out of vfx.html at test time) beside these, over every chunk, group, saved chain and saved graph and a few
// hundred graphs built by the page's own editing code, and requires identical text: identical text compiles to
// identical pixels, so no GPU render is needed. The page re-checks every build at run time too (vfx.html,
// codegenPick): the legacy writer still runs, and any build whose text differs ships the legacy text and says so.
//
// ONE DECLARED DIFFERENCE: the mask-port fix (census defect D1, research/in-flight/shader-school-2026-10-13/
// arc-vfx-bench.md section 6). The Graph card's "use as mask" button wires a mask's float output into a blend's colB
// port, and the legacy writer then read that mask's COLOUR (`vec3 colB = <mask>_col;`), which a mask never writes: the
// rule "a mask can never enter a colour socket" was broken in the generated code. Here a wire from a mask's `m` feeds
// the receiving block's `m` (`float m = <mask>_m;`) and colB stays unwired (`vec3(0.)`). And every block that has a
// colB, a graph block whose chunk takes colB or a blend tile, declares `m` beside it: the wired mask's, or MASK_DEFAULT
// (0.5, the even mix mix-blend uses today). So a blend that reads m compiles in a tile and in a graph with no mask wired
// (the S5 review found the planned "mix-blend reads m" would fail there), and keeps its 0.5 mix while unwired. Pixels
// do not move with the shipped chunks (colB was already black, and no shipped blend reads m yet), but the blend can now
// see its mask. graph(G, {maskFix: false}) and thumb(c, {maskFix: false}) write the legacy text, which is what the page
// compares against. A chunk never declares m itself (the writer does; the parity test refuses a chunk that would).
//
// THE SNIPPET ABI (architecture draft section 3.4). A chunk body is a block of statements that reads and writes
// `vec2 uv`, `vec3 col`, `float alpha`, `vec3 colB` and `float m`, and nothing else crosses blocks. The Graph writer
// gives every node its own block and its own copies (<id>_col, <id>_alpha, <id>_m, <id>_uv), which is why every chunk
// written for the linear chain works in a graph unchanged: the graph wraps bodies, it never rewrites them.
//
// USE (the page passes modlib in, so this file never decides where modlib lives: /glsl/modlib.js in the page, a path
// on disk in the node test):
//   import * as modlib from '/glsl/modlib.js';
//   import { createBenchCodegen } from '/vfx-codegen.js';
//   const gen = createBenchCodegen(modlib, CHUNKS);        // CHUNKS exactly as GET /vfx/chunks serves them
//   gen.chain('plasma-field', ['tanh-tonemap'])            // the Compose card: GLSL text, or null without a source
//   gen.graph(G)                                           // the Graph card: {src} or {err}
//   gen.thumb(chunk, {ref, refB})                          // a palette tile, the hover preview, a CLI thumb
//   (graph and thumb take {maskFix: false} for the legacy-equivalent text the page holds to the legacy bytes)
//
// Licence: Apache-2.0, house code written for this repository. It carries no outside shader code: the GLSL it writes is
// the bench's own scaffolding (the same lines its legacy writers emit) around chunk bodies read at run time.

export const CODEGEN_API = 'arsenal.vfx-codegen/v1';

const HEAD = ['#version 300 es', 'precision highp float;', 'out vec4 outColor;'];
// The bench's uniform contract (the AgentAvatar host's), written once. The thumbnail writer adds u_thick.
export const UNIFORMS = Object.freeze([
  'uniform vec2  u_res;', 'uniform float u_time;', 'uniform float u_sub;', 'uniform float u_gap;',
  'uniform float u_spin;', 'uniform float u_pulse;', 'uniform float u_sat;', 'uniform vec3  u_tint;',
  'uniform float u_dim;', 'uniform float u_wire;', 'uniform vec3  u_id0;', 'uniform vec3  u_id1;',
  'uniform float u_round;', 'uniform float u_star;', 'uniform float u_see;',
]);
const THUMB_UNIFORMS = [...UNIFORMS, 'uniform float u_thick;'];
const FRAME = '  vec2 uv=(-u_res.xy+2.*gl_FragCoord.xy)/u_res.y;';   // the bench frame: y runs -1..1, x by aspect
const CLEAR = '  vec3 col=vec3(0.); float alpha=0.;';
// The thumbnail's before/after fade: k eases 0 -> 1 -> 0 forever, so a tile always answers "what does this change".
const FADE = '  float k = 0.5 - 0.5*cos(u_time * 3.14159265);\n';
export const THUMB_REF = 'thumb-reference';   // the calibration ramp every tile is drawn against
export const THUMB_REF_B = 'sphere-glass';    // the second input of a blend tile
// What a block with a colB reads as m when no mask is wired: the even mix mix-blend uses today, so a blend switched to
// reading m moves no pixel until a mask is wired into it.
export const MASK_DEFAULT = '0.5';

const indent = (body) => body.split('\n').map((l) => '    ' + l).join('\n');
const portsOf = (m, side) => {
  const p = m.header ? m.header[side] : null;
  return p && typeof p === 'object' ? p : {};
};

// A /vfx/chunks record back into module text: every header field but the body on one //! line, then the body.
// The server sends the header as parsed JSON and the body stripped, so this is the file as the bench sees it.
export function chunkSource(rec) {
  const header = {};
  for (const k of Object.keys(rec || {})) if (k !== 'body') header[k] = rec[k];
  return '//! ' + JSON.stringify(header) + '\n' + (rec && typeof rec.body === 'string' ? rec.body : '');
}

// The library over the bench's chunks. Lenient, as every page is: a chunk that cannot be read is quarantined into
// library.problems and the rest load (the page then sees different text for anything using it, and falls back).
export function libraryFromChunks(modlib, chunks, { strict = false } = {}) {
  if (!modlib || typeof modlib.libraryFromSources !== 'function') {
    throw new Error('vfx-codegen needs arsenal/web/glsl/modlib.js (pass its module namespace); ' +
      'without it the page keeps its legacy writers');
  }
  const records = Array.isArray(chunks) ? chunks : [];
  return modlib.libraryFromSources(records.map((c) => [`design/vfx-chunks/${c && c.name}.glsl`, chunkSource(c)]), { strict });
}

export function createBenchCodegen(modlib, chunks, { strict = false } = {}) {
  const lib = libraryFromChunks(modlib, chunks, { strict });
  const mod = (name) => (typeof name === 'string' && lib.modules.has(name) ? lib.modules.get(name) : null);
  const need = (name, why) => {
    const m = mod(name);
    if (!m) throw new Error(`vfx-codegen: ${why} '${name}' is not in the chunk library`);
    return m;
  };

  // Every helper, as the legacy writers include them (cheap, and it removes a whole class of "forgot a dependency"
  // failures), in the resolver's order: what a helper calls comes first, then the header's `order`, then the name. For
  // chunks the bench lint passes this is exactly the legacy order (see the header).
  const helperOrder = lib.resolve([...lib.modules.values()].filter((m) => m.kind === 'helper').map((m) => m.name))
    .filter((name) => lib.modules.get(name).composable);
  const helpers = helperOrder.map((name) => lib.modules.get(name).body).join('\n');

  // The Compose card: one source, then the chain of chunks in order, all in main's own scope.
  function chain(sourceName, items) {
    const src = mod(sourceName);
    if (!src) return null;
    const steps = (items || []).map((name) => {
      const c = mod(name);
      return c ? '  // ---- ' + c.name + ' ----\n' + c.body : '';   // an unknown name leaves an empty line, as before
    });
    return [...HEAD, ...UNIFORMS, '', '// ---- helpers ----', helpers, '',
      'void main(){', FRAME, CLEAR,
      '  // ---- source: ' + src.name + ' ----', src.body, steps.join('\n'),
      '  col*=u_dim;',
      '  outColor=vec4(max(col,0.),clamp(alpha,0.,1.));',
      '}'].join('\n');
  }

  // The Graph card: a depth-first walk upstream from OUTPUT, each node one block with its own copies of the ABI
  // variables. A cycle (the HUD's insert-a-blend button can close one) is skipped where it closes, never followed.
  function graph(G, { maskFix = true } = {}) {
    const out = G.nodes.filter((nd) => nd.chunk === '__out')[0];
    if (!out) return { err: 'no output node' };
    const order = [], mark = {};
    function visit(id) {
      if (mark[id] === 'done') return true;
      if (mark[id] === 'open') return false;
      mark[id] = 'open';
      G.edges.filter((e) => e.to === id).forEach((e) => { visit(e.from); });
      mark[id] = 'done'; order.push(id); return true;
    }
    if (!visit(out.id)) return { err: 'cycle' };
    const byId = {};
    G.nodes.forEach((nd) => { byId[nd.id] = nd; });
    const into = (id, port) => G.edges.filter((e) => e.to === id && e.toPort === port)[0];

    const body = [];
    order.forEach((id) => {
      const nd = byId[id];
      if (!nd || nd.chunk === '__out') return;
      const c = mod(nd.chunk);
      if (!c) return;
      const ins = portsOf(c, 'in'), outs = portsOf(c, 'out');
      const eCol = into(id, 'col'), eB = into(id, 'colB'), eUV = into(id, 'uv');
      // The declared fix: a wire from a mask's m output feeds this block's m, never its colour; with no mask wired, a
      // block that takes colB still declares m (MASK_DEFAULT), so a blend that reads m always compiles.
      const maskIn = maskFix && ins.colB && eB && eB.fromPort === 'm';
      body.push('  // ---- ' + c.name + ' (' + id + ') ----');
      body.push('  vec3 ' + id + '_col = vec3(0.); float ' + id + '_alpha = 0.; float ' + id + '_m = 0.;');
      body.push('  vec2 ' + id + '_uv = uv;');
      body.push('  {');
      body.push('    vec2 uv = ' + (eUV ? eUV.from + '_uv' : 'uv') + ';');
      body.push('    vec3 col = ' + (eCol ? eCol.from + '_col' : 'vec3(0.)') + ';');
      body.push('    float alpha = ' + (eCol ? eCol.from + '_alpha' : '0.') + ';');
      if (ins.colB) body.push('    vec3 colB = ' + (eB && !maskIn ? eB.from + '_col' : 'vec3(0.)') + ';');
      if (maskIn) body.push('    float m = ' + eB.from + '_m;');
      else if (maskFix && ins.colB) body.push('    float m = ' + MASK_DEFAULT + ';');
      else if (outs.m) body.push('    float m = 0.;');
      body.push(indent(c.body));
      body.push('    ' + id + '_col = col; ' + id + '_alpha = alpha; ' + id + '_uv = uv;');
      if (outs.m) body.push('    ' + id + '_m = m;');
      body.push('  }');
    });
    const last = into(out.id, 'col');
    if (!last) return { err: 'nothing is wired into OUTPUT' };
    return { src: [...HEAD, ...UNIFORMS, '', helpers, '',
      'void main(){', FRAME, body.join('\n'),
      '  outColor = vec4(max(' + last.from + '_col,0.)*u_dim, clamp(' + last.from + '_alpha,0.,1.));',
      '}'].join('\n') };
  }

  // A tile: the chunk doing its job against the calibration ramp, as a before/after (see vfx.html's THUMBNAILS notes).
  // maskFix (the declared difference) gives a blend tile's block its default m; false writes the legacy text.
  function thumb(chunk, { ref = THUMB_REF, refB = THUMB_REF_B, maskFix = true } = {}) {
    const c = need(chunk && chunk.name, 'chunk');
    let body;
    if (c.kind === 'source') {
      body = c.body;
    } else if (c.kind === 'domain') {
      // The warp runs BEFORE the reference samples the space, and the fade is in the coordinate, not the image.
      body = FADE + '  vec2 _w = uv;\n  {\n    vec2 uv = _w;\n' + indent(c.body) +
        '\n    _w = uv;\n  }\n  { vec2 uv = mix(uv, _w, k);\n' + need(ref, 'reference').body + '\n  }';
    } else if (c.kind === 'mask') {
      // A mask is a float, so it is drawn as one: greyscale, no fade.
      body = '  float m=0.;\n' + c.body + '\n  col=vec3(m); alpha=m;';
    } else if (c.kind === 'blend') {
      // The second input is computed in its own scope, then the blend sees the ramp as col and refB as colB.
      body = FADE +
        '  vec3 _b=vec3(0.), _raw=vec3(0.);\n' +
        '  { vec3 col=vec3(0.); float alpha=0.;\n' + need(refB, 'second reference').body + '\n    _b=col; }\n' +
        '  { vec3 col=vec3(0.); float alpha=0.;\n' + need(ref, 'reference').body + '\n    _raw=col; }\n' +
        '  { vec3 col=_raw; vec3 colB=_b; float alpha=1.;' + (maskFix ? ' float m=' + MASK_DEFAULT + ';' : '') + '\n' +
        c.body + '\n    _b=col; }\n' +
        '  col = mix(_raw, _b, k); alpha = 1.0;';
    } else {
      // A modifier (or anything else): run the ramp, keep it, run the effect on a copy, cross-fade between them.
      body = FADE +
        '  vec3 _raw=vec3(0.);\n' +
        '  { vec3 col=vec3(0.); float alpha=0.;\n' + need(ref, 'reference').body + '\n    _raw=col; }\n' +
        '  { vec3 col=_raw; float alpha=1.;\n' + c.body + '\n    _raw = mix(_raw, col, k); }\n' +
        '  col = _raw; alpha = 1.0;';
    }
    return [...HEAD, ...THUMB_UNIFORMS, '', helpers, '',
      'void main(){', FRAME, CLEAR, body,
      '  outColor=vec4(max(col,0.), clamp(max(alpha,dot(col,vec3(.4))),0.,1.));',
      '}'].join('\n');
  }

  return { api: CODEGEN_API, library: lib, problems: lib.problems, helpers: helperOrder.slice(), chain, graph, thumb };
}
