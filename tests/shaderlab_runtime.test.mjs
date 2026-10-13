// tests/shaderlab_runtime.test.mjs -- the shaderlab runtime (arsenal/web/shaderlab/toy-runtime.js) without a GPU.
//
// Two halves. The pure helpers are pinned directly: header text per pass type and input kind, Common assembly,
// error-line mapping, pass order with buffers reading each other and themselves, sampler mapping, the .bin volume
// header, the keyboard and audio textures, the frame schedule. The GL path is driven against FakeGL, a recording
// WebGL2 stand-in that enforces what a real context refuses a draw for (a texture bound for reading while it is the
// render target, a sampler uniform pointing at the wrong unit, a uniform set on a program that is not bound,
// #version not on line 1). Real pixels are the headless SwiftShader harness's job; this proves the plumbing.
//
// Every shader here is synthetic and ours.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../arsenal/web/shaderlab/toy-runtime.js';
import { parseParams, mediaResolver, shaderFromBody, DATE_BASE } from '../arsenal/web/shaderlab/render.js';

const { GL } = R;
const ID = { A: '4dXGR8', B: 'XsXGR8', C: '4sXGR8', D: 'XdfGR8', cube: '4dX3Rr', image: '4dfGRr', sound: 'XsfGRr' };
const PREVIZ = { A: '/media/previz/buffer00.png', B: '/media/previz/buffer01.png', C: '/media/previz/buffer02.png', D: '/media/previz/buffer03.png' };
const S = (filter = 'linear', wrap = 'clamp', vflip = 'true', srgb = 'false') => ({ filter, wrap, vflip, srgb, internal: 'byte' });
const bufIn = (ch, key, sampler = S()) => ({ channel: ch, type: 'buffer', id: ID[key], filepath: PREVIZ[key], sampler });
const pass = (name, type, code, inputs = [], outId = null) => ({
  name, type, code, inputs, outputs: outId ? [{ id: outId, channel: 0 }] : [],
});
const img = (code, inputs = []) => pass('Image', 'image', code, inputs, ID.image);
const MAIN = (tag, body = 'o = vec4(u * 0.01, 0.25, 1.0);') => `// PASS ${tag} of this test\nvoid mainImage(out vec4 o, in vec2 u) {\n  ${body}\n}\n`;

// ---------------------------------------------------------------------------------------------------------------
// FakeGL: records and enforces
// ---------------------------------------------------------------------------------------------------------------
const TEX_TARGETS = [GL.TEXTURE_2D, GL.TEXTURE_CUBE_MAP, GL.TEXTURE_3D];
const baseTarget = (t) => (t >= GL.TEXTURE_CUBE_MAP_POSITIVE_X && t < GL.TEXTURE_CUBE_MAP_POSITIVE_X + 6 ? GL.TEXTURE_CUBE_MAP : t);
const SAMPLER_TARGET = { sampler2D: GL.TEXTURE_2D, samplerCube: GL.TEXTURE_CUBE_MAP, sampler3D: GL.TEXTURE_3D };

class FakeGL {
  constructor({ ext = ['EXT_color_buffer_float', 'OES_texture_float_linear', 'WEBGL_debug_renderer_info', 'WEBGL_lose_context'],
    renderer = 'ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)), SwiftShader driver)', unrenderable = [],
    rejects = null } = {}) {
    this.rejects = rejects;
    this.exts = new Set(ext);
    this.rendererString = renderer;
    this.unrenderable = new Set(unrenderable);
    this.id = 1;
    this.unit = 0;
    this.units = Array.from({ length: 16 }, () => ({ [GL.TEXTURE_2D]: null, [GL.TEXTURE_CUBE_MAP]: null, [GL.TEXTURE_3D]: null }));
    this.samplerUnits = new Array(16).fill(null);
    this.fbo = null;
    this.program = null;
    this.vao = null;
    this.store = {};
    this.draws = [];
    this.uploads = [];
    this.clears = [];
    this.violations = [];
    this.textures = [];
    this.lost = false;
    this.readFbo = null;
    this.blits = [];
    this.sources = [];
  }
  violate(msg) { this.violations.push(msg); }
  get drawingBufferWidth() { return this.canvas.width; }
  get drawingBufferHeight() { return this.canvas.height; }
  isContextLost() { return this.lost; }
  getExtension(name) {
    if (!this.exts.has(name)) return null;
    if (name === 'WEBGL_debug_renderer_info') return { UNMASKED_VENDOR_WEBGL: GL.UNMASKED_VENDOR_WEBGL, UNMASKED_RENDERER_WEBGL: GL.UNMASKED_RENDERER_WEBGL };
    if (name === 'WEBGL_lose_context') return { loseContext: () => { this.lost = true; } };
    return {};
  }
  getParameter(p) {
    return ({ [GL.UNMASKED_RENDERER_WEBGL]: this.rendererString, [GL.UNMASKED_VENDOR_WEBGL]: 'Google Inc. (Google)',
      [GL.RENDERER]: 'WebKit WebGL', [GL.VENDOR]: 'WebKit', [GL.VERSION]: 'WebGL 2.0', [GL.SHADING_LANGUAGE_VERSION]: 'WebGL GLSL ES 3.00' })[p];
  }
  getError() { return GL.NO_ERROR; }
  enable() {} disable() {}
  pixelStorei(p, v) { this.store[p] = v; }
  createVertexArray() { return { id: this.id++ }; }
  bindVertexArray(v) { this.vao = v; }
  deleteVertexArray() {}
  // textures
  createTexture() { const t = { id: this.id++, target: null, internal: null, w: 0, h: 0, d: 0, mips: 0 }; this.textures.push(t); return t; }
  deleteTexture(t) { if (t) t.deleted = true; }
  activeTexture(u) { this.unit = u - GL.TEXTURE0; }
  bindTexture(target, t) {
    if (t) {
      if (t.deleted) this.violate(`bind of deleted texture ${t.id}`);
      if (t.target && t.target !== target) this.violate(`texture ${t.id} bound to a second target`);
      t.target = target;
    }
    this.units[this.unit][target] = t;
  }
  bound(target) { return this.units[this.unit][baseTarget(target)]; }
  texImage2D(target, level, internal, ...rest) {
    const t = this.bound(target);
    if (!t) { this.violate('texImage2D with no texture bound'); return; }
    let w, h, source = null;
    if (rest.length === 3) { source = rest[2]; w = source.naturalWidth || source.width; h = source.naturalHeight || source.height; }
    else { [w, h] = rest; source = rest[5]; }
    if (level === 0) Object.assign(t, { internal, w, h, d: 1 });
    this.uploads.push({ fn: 'texImage2D', tex: t.id, target, internal, w, h, source, image: rest.length === 3,
      flipY: !!this.store[GL.UNPACK_FLIP_Y_WEBGL] });
  }
  texSubImage2D(target, level, x, y, w, h, format, type, data) {
    const t = this.bound(target);
    this.uploads.push({ fn: 'texSubImage2D', tex: t && t.id, w, h, data: Uint8Array.from(data) });
  }
  texImage3D(target, level, internal, w, h, d, border, format, type, data) {
    const t = this.bound(target);
    Object.assign(t, { internal, w, h, d });
    this.uploads.push({ fn: 'texImage3D', tex: t.id, internal, w, h, d, format, type, bytes: data ? data.byteLength : 0 });
  }
  texParameteri() {}
  generateMipmap(target) { const t = this.bound(target); if (t) t.mips++; else this.violate('generateMipmap with nothing bound'); }
  // samplers
  createSampler() { return { id: this.id++, params: {} }; }
  samplerParameteri(s, p, v) { s.params[p] = v; }
  bindSampler(unit, s) { this.samplerUnits[unit] = s; }
  deleteSampler() {}
  // framebuffers
  createFramebuffer() { return { id: this.id++, attach: null }; }
  deleteFramebuffer() {}
  // READ_ / DRAW_FRAMEBUFFER bind one side; FRAMEBUFFER binds both (the WebGL2 rule). this.fbo is the draw side.
  bindFramebuffer(target, f) {
    if (target === 0x8CA8) this.readFbo = f;                 // READ_FRAMEBUFFER
    else if (target === 0x8CA9) this.fbo = f;                // DRAW_FRAMEBUFFER
    else { this.fbo = f; this.readFbo = f; }
  }
  framebufferTexture2D(target, att, texTarget, t) { this.fbo.attach = { tex: t, texTarget }; }
  checkFramebufferStatus() { return this.fbo && this.fbo.attach && !this.unrenderable.has(this.fbo.attach.tex.internal) ? GL.FRAMEBUFFER_COMPLETE : 0; }
  clearColor() {}
  // Each texture carries a content label so a test can follow pixels: a clear writes 'clear', a draw writes
  // '<pass tag>@<iFrame>', a blit copies the label.
  clear() {
    if (this.fbo && this.fbo.attach) this.fbo.attach.tex.content = 'clear';
    this.clears.push(this.fbo && this.fbo.attach ? this.fbo.attach.tex.id : 'canvas');
  }
  blitFramebuffer(sx0, sy0, sx1, sy1, dx0, dy0, dx1, dy1, mask, filter) {
    const from = this.readFbo && this.readFbo.attach ? this.readFbo.attach.tex : null;
    const to = this.fbo && this.fbo.attach ? this.fbo.attach.tex : null;
    if (!from || !to) { this.violate('blit without a read and a draw framebuffer'); return; }
    if (from === to) this.violate(`blit of texture ${from.id} onto itself`);
    if (filter !== GL.NEAREST) this.violate('blit of a float target with a filter other than NEAREST');
    this.blits.push({ from: from.id, to: to.id, src: [sx0, sy0, sx1, sy1], dst: [dx0, dy0, dx1, dy1], mask, filter });
    to.content = from.content;
  }
  viewport(x, y, w, h) { this.vp = [w, h]; }
  // shaders and programs
  createShader(type) { return { id: this.id++, type, source: '', ok: false, log: '' }; }
  shaderSource(s, src) { s.source = src; }
  compileShader(s) {
    this.sources.push({ type: s.type, source: s.source });
    const lines = s.source.split('\n');
    const errs = [];
    if (this.rejects) errs.push(...this.rejects(s.source, lines));   // a test's own compiler rule
    if (lines[0] !== '#version 300 es') errs.push(`ERROR: 0:1: '' : #version must be on line 1`);
    if (s.type === GL.FRAGMENT_SHADER && !/precision highp float;/.test(s.source)) errs.push(`ERROR: 0:2: '' : no float precision`);
    lines.forEach((l, i) => { if (l.includes('SYNTAX_ERROR_HERE')) errs.push(`ERROR: 0:${i + 1}: 'SYNTAX_ERROR_HERE' : syntax error`); });
    // An entry point the footer calls but the code never defines: the error lands on the footer's line.
    for (const [call, def] of [['mainImage(shaderlab_color', /void\s+mainImage\s*\(/], ['mainCubemap(shaderlab_color', /void\s+mainCubemap\s*\(/]]) {
      const at = lines.findIndex((l) => l.includes(call));
      if (at >= 0 && !def.test(s.source)) errs.push(`ERROR: 0:${at + 1}: 'mainImage' : no matching overloaded function found`);
    }
    s.ok = errs.length === 0;
    s.log = errs.join('\n') + (errs.length ? '\n' : '');
  }
  getShaderParameter(s) { return s.ok; }
  getShaderInfoLog(s) { return s.log; }
  deleteShader() {}
  createProgram() { return { id: this.id++, shaders: [], linked: false, frag: '', values: {} }; }
  attachShader(p, s) { p.shaders.push(s); if (s.type === GL.FRAGMENT_SHADER) p.frag = s.source; }
  detachShader(p, s) { p.shaders = p.shaders.filter((x) => x !== s); }
  linkProgram(p) { p.linked = p.shaders.length === 2 && p.shaders.every((s) => s.ok); }
  getProgramParameter(p) { return p.linked; }
  getProgramInfoLog() { return ''; }
  deleteProgram(p) { if (p) p.deleted = true; }
  useProgram(p) { this.program = p; }
  getUniformLocation(p, name) { return new RegExp(`\\b${name}\\b`).test(p.frag) ? { name, prog: p } : null; }
  setU(loc, v) {
    if (!loc) return;
    if (loc.prog !== this.program) this.violate(`uniform ${loc.name} set while another program is bound`);
    loc.prog.values[loc.name] = v;
  }
  uniform1i(l, v) { this.setU(l, v); } uniform1f(l, v) { this.setU(l, v); }
  uniform3f(l, a, b, c) { this.setU(l, [a, b, c]); }
  uniform1fv(l, v) { this.setU(l, Array.from(v)); } uniform3fv(l, v) { this.setU(l, Array.from(v)); } uniform4fv(l, v) { this.setU(l, Array.from(v)); }
  drawArrays(mode, first, count) {
    const p = this.program;
    if (!p || !p.linked || p.deleted) { this.violate('draw without a linked program'); return; }
    if (!this.vao) this.violate('draw without a vertex array bound');
    const target = this.fbo && this.fbo.attach ? this.fbo.attach.tex : null;
    const decls = [...p.frag.matchAll(/uniform (sampler2D|samplerCube|sampler3D) iChannel(\d);/g)];
    if (decls.length !== 4) this.violate(`program declares ${decls.length} channels`);
    const reads = [];
    const readContent = [];
    for (const [, type, chs] of decls) {
      const c = Number(chs);
      if (p.values[`iChannel${c}`] !== c) this.violate(`iChannel${c} points at unit ${p.values[`iChannel${c}`]}`);
      const t = this.units[c][SAMPLER_TARGET[type]];
      if (!t) this.violate(`iChannel${c} (${type}) has nothing bound on its target`);
      reads[c] = t ? t.id : null;
      readContent[c] = t ? t.content : null;
    }
    for (let u = 0; u < 4; u++) {
      for (const tt of TEX_TARGETS) if (target && this.units[u][tt] === target) this.violate(`feedback loop: texture ${target.id} is the target and bound on unit ${u}`);
    }
    const tag = (/\/\/ PASS (\S+)/.exec(p.frag) || [])[1] || '?';
    const face = this.fbo && this.fbo.attach ? this.fbo.attach.texTarget - GL.TEXTURE_CUBE_MAP_POSITIVE_X : null;
    this.draws.push({ tag, write: target ? target.id : 'canvas', face: face >= 0 && face < 6 ? face : null, reads,
      readContent, frame: p.values.iFrame, time: p.values.iTime, timeDelta: p.values.iTimeDelta,
      frameRate: p.values.iFrameRate, mouse: p.values.iMouse, chtime: p.values.iChannelTime,
      res: p.values.iResolution, chres: p.values.iChannelResolution, date: p.values.iDate, vp: this.vp });
    if (target) target.content = `${tag}@${p.values.iFrame}`;
  }
}
function fakeCanvas(gl, w = 64, h = 36) {
  const canvas = { width: w, height: h, attrs: null, getContext(type, attrs) { this.attrs = attrs; return type === 'webgl2' ? gl : null; }, addEventListener() {} };
  gl.canvas = canvas;
  return canvas;
}
function makeToy(shader, opts = {}, glOpts = {}) {
  const gl = new FakeGL(glOpts);
  const canvas = fakeCanvas(gl);
  const toy = R.createToy(canvas, shader, opts);
  return { gl, canvas, toy };
}
const shaderOf = (...passes) => ({ info: { id: 'synth1', name: 'synthetic' }, renderpass: passes });

// A five-pass graph of our own: A reads itself and D, B reads A, C reads B and D, D reads C, Image reads A.
// Saved in a shuffled order with mixed names, as real saves are.
function graphShader() {
  return shaderOf(
    img(MAIN('image', 'o = texture(iChannel0, u / iResolution.xy);'), [bufIn(0, 'A')]),
    pass('Buf A', 'buffer', MAIN('A', 'o = texture(iChannel1, u / iResolution.xy) + texture(iChannel0, u / iResolution.xy);'), [bufIn(1, 'A'), bufIn(0, 'D')], ID.A),
    pass('Buffer B', 'buffer', MAIN('B'), [bufIn(0, 'A')], ID.B),
    pass('Common', 'common', 'float shared_k() { return 1.0; }\n'),
    pass('Buffer C', 'buffer', MAIN('C'), [bufIn(0, 'B'), bufIn(1, 'D')], ID.C),
    pass('Buffer D', 'buffer', MAIN('D'), [bufIn(0, 'C', S('mipmap', 'repeat'))], ID.D),
  );
}

// ---------------------------------------------------------------------------------------------------------------
// Header and assembly
// ---------------------------------------------------------------------------------------------------------------
test('header: #version on line 1, precision, every uniform of the interface, four sampler2D channels by default', () => {
  const h = R.buildHeader('image', []);
  const lines = h.split('\n');
  assert.equal(lines[0], '#version 300 es');
  assert.equal(h.match(/#version/g).length, 1);
  assert.ok(h.endsWith('\n'));
  for (const decl of ['precision highp float;', 'precision highp int;', 'precision highp sampler3D;', '#define HW_PERFORMANCE 1',
    'uniform vec3 iResolution;', 'uniform float iTime;', 'uniform float iTimeDelta;', 'uniform float iFrameRate;',
    'uniform int iFrame;', 'uniform float iChannelTime[4];', 'uniform vec3 iChannelResolution[4];', 'uniform vec4 iMouse;',
    'uniform vec4 iDate;', 'uniform float iSampleRate;']) assert.ok(lines.includes(decl), decl);
  for (let c = 0; c < 4; c++) assert.ok(lines.includes(`uniform sampler2D iChannel${c};`));
  assert.ok(!h.includes('iBlockOffset'));
  assert.ok(!h.includes('shaderlab_face'));
  assert.ok(R.buildHeader('image', [], { hwPerformance: 0 }).includes('#define HW_PERFORMANCE 0'));
});

test('header: each input kind declares its channel with the right sampler type', () => {
  const inputs = [
    { channel: 0, type: 'cubemap', id: 'XsX3zn', filepath: '/media/a/aa.png' },
    { channel: 1, type: 'volume', id: '4sfGRr', filepath: '/media/a/bb.bin' },
    { channel: 2, type: 'cubemap', id: ID.cube, filepath: '/media/a//media/previz/cubemap00.png' },
    { channel: 3, type: 'keyboard', id: '4dXGRr', filepath: '/presets/tex00.jpg' },
  ];
  const h = R.buildHeader('buffer', inputs);
  assert.ok(h.includes('uniform samplerCube iChannel0;'));
  assert.ok(h.includes('uniform sampler3D iChannel1;'));
  assert.ok(h.includes('uniform samplerCube iChannel2;'));
  assert.ok(h.includes('uniform sampler2D iChannel3;'));
  for (const type of ['buffer', 'texture', 'keyboard', 'music', 'musicstream', 'mic', 'video', 'webcam']) {
    assert.equal(R.samplerTypeFor({ type }), 'sampler2D', type);
  }
  assert.equal(R.samplerTypeFor({ type: 'cubemap' }), 'samplerCube');
  assert.equal(R.samplerTypeFor({ type: 'volume' }), 'sampler3D');
  assert.ok(R.buildHeader('sound', []).includes('uniform float iBlockOffset;'));
  const cubeHeader = R.buildHeader('cubemap', []);
  for (const u of ['shaderlab_faceCenter', 'shaderlab_faceRight', 'shaderlab_faceUp']) assert.ok(cubeHeader.includes(`uniform vec3 ${u};`));
});

test('assembly: Common is prepended to every pass, and the counts locate each line exactly', () => {
  const common = 'float k1() { return 1.0; }\r\nfloat k2() { return 2.0; }';   // CRLF and no final newline
  const code = '// PASS A\nvoid mainImage(out vec4 o, in vec2 u) {\n  o = vec4(k1());\n}';
  for (const type of ['image', 'buffer', 'cubemap', 'sound']) {
    const p = { name: 'P', type, code: type === 'sound' ? 'vec2 mainSound(int s, float t) { return vec2(0.0); }' : code, inputs: [] };
    const a = R.assembleSource(p, common);
    const lines = a.source.split('\n');
    assert.equal(lines[0], '#version 300 es', type);
    assert.equal(a.headerLines, R.buildHeader(type, []).split('\n').length - 1);
    assert.equal(a.commonLines, 2);
    assert.equal(lines[a.headerLines], 'float k1() { return 1.0; }');
    assert.equal(lines[a.headerLines + 1], 'float k2() { return 2.0; }');
    const own = R.sanitizeGlsl(p.code).split('\n');
    for (let k = 0; k < a.passLines; k++) assert.equal(lines[a.headerLines + a.commonLines + k], own[k]);
    assert.ok(!a.source.includes('\r'));
    assert.equal(a.source.match(/void main\(\)/g).length, 1);
  }
  const empty = R.assembleSource({ type: 'image', code }, '');
  assert.equal(empty.commonLines, 0);
});

test('assembly: the footer calls the right entry point, and Image is opaque while a buffer keeps alpha', () => {
  const imgSrc = R.assembleSource({ type: 'image', code: 'void mainImage(out vec4 o, in vec2 u) { o = vec4(0.5); }' }).source;
  assert.ok(imgSrc.includes('mainImage(shaderlab_color, gl_FragCoord.xy);'));
  assert.ok(imgSrc.includes('shaderlab_out = vec4(shaderlab_color.rgb, 1.0);'));
  const bufSrc = R.assembleSource({ type: 'buffer', code: 'void mainImage(out vec4 o, in vec2 u) { o = vec4(0.5); }' }).source;
  assert.ok(bufSrc.includes('shaderlab_out = shaderlab_color;'));
  const cube = R.assembleSource({ type: 'cubemap', code: 'void mainCubemap(out vec4 o, in vec2 f, in vec3 ro, in vec3 rd) { o = vec4(rd, 1.0); }' });
  assert.equal(cube.entry, 'mainCubemap');
  assert.ok(cube.source.includes('mainCubemap(shaderlab_color, gl_FragCoord.xy, vec3(0.0), shaderlab_dir);'));
  const newSound = R.assembleSource({ type: 'sound', code: 'vec2 mainSound( int samp, float time ) { return vec2(0.0); }' }).source;
  assert.ok(newSound.includes('mainSound(shaderlab_sample, shaderlab_t)'));
  const oldSound = R.assembleSource({ type: 'sound', code: 'vec2 mainSound(float time) { return vec2(0.0); }' }).source;
  assert.ok(oldSound.includes('mainSound(shaderlab_t)') && !oldSound.includes('mainSound(shaderlab_sample'));
});

test('sanitize: non-ASCII becomes a space, CRLF becomes LF, BOM goes, no line moves', () => {
  const src = '\ufeff// \u00a9 2020 J\u00f6rg\r\nfloat x;\u00a0// tab\there\n';
  const out = R.sanitizeGlsl(src);
  assert.equal(out, '//   2020 J rg\nfloat x; // tab\there\n');
  assert.equal(R.sanitizeGlsl(''), '');
  assert.equal(R.sanitizeGlsl('a'), 'a\n');
});

// ---------------------------------------------------------------------------------------------------------------
// Error mapping
// ---------------------------------------------------------------------------------------------------------------
test('error mapping: a compiler line lands on the pass, on Common, or on our header/footer', () => {
  const H = 22, C = 5, P = 30;
  const log = [
    `ERROR: 0:${H + C + 4}: 'x' : undeclared identifier`,
    `ERROR: 0:${H + 2}: 'k' : syntax error`,
    `WARNING: 0:${H + C + 1}: 'y' : unused`,
    `ERROR: 0:3: '' : header trouble`,
    `ERROR: 0:${H + C + P + 2}: 'mainImage' : no matching overloaded function found`,
    'ERROR: 5 compilation errors.  No code generated.',
  ].join('\n');
  const mapped = R.mapErrorLog(log, H, { commonLines: C, passLines: P, passName: 'Buffer A' }).split('\n');
  assert.equal(mapped[0], "ERROR: Buffer A:4: 'x' : undeclared identifier");
  assert.equal(mapped[1], "ERROR: Common:2: 'k' : syntax error");
  assert.equal(mapped[2], "WARNING: Buffer A:1: 'y' : unused");
  assert.equal(mapped[3], "ERROR: header:3: '' : header trouble");
  assert.equal(mapped[4], "ERROR: footer:2: 'mainImage' : no matching overloaded function found");
  assert.equal(mapped[5], 'ERROR: 5 compilation errors.  No code generated.');
  // The two-argument form: everything past the header is the pass.
  assert.equal(R.mapErrorLog('ERROR: 0:30: bad', 20), 'ERROR: pass:10: bad');
  const rows = R.parseErrorLog(mapped.join('\n'));
  assert.deepEqual(rows[0], { severity: 'ERROR', section: 'Buffer A', line: 4, message: "'x' : undeclared identifier" });
  assert.equal(rows.length, 5);
  assert.deepEqual(R.locateLine(10, 8, 0, 5), { section: 'pass', line: 2 });
});

test('error mapping round trip: the mapped line is the line of the pass that holds the fault', () => {
  const code = 'float a;\nfloat b;\nfloat c = SYNTAX_ERROR_HERE;\nvoid mainImage(out vec4 o, in vec2 u) { o = vec4(1.0); }';
  const asm = R.assembleSource({ type: 'image', code }, 'float common1;\nfloat common2;');
  const absolute = asm.source.split('\n').findIndex((l) => l.includes('SYNTAX_ERROR_HERE')) + 1;
  const mapped = R.mapErrorLog(`ERROR: 0:${absolute}: 'SYNTAX_ERROR_HERE' : syntax error`, asm.headerLines,
    { commonLines: asm.commonLines, passLines: asm.passLines, passName: 'Image' });
  assert.equal(mapped, "ERROR: Image:3: 'SYNTAX_ERROR_HERE' : syntax error");
  assert.ok(code.split('\n')[2].includes('SYNTAX_ERROR_HERE'));
});

// ---------------------------------------------------------------------------------------------------------------
// Pass order
// ---------------------------------------------------------------------------------------------------------------
test('pass order: buffers saved A, B, C, D run so, Image saved first runs last, names vary; reads say which frame they see', () => {
  const order = R.passOrder(graphShader().renderpass);
  assert.deepEqual(order.map((e) => e.key), ['A', 'B', 'C', 'D', 'image']);
  assert.deepEqual(order.map((e) => e.name), ['Buf A', 'Buffer B', 'Buffer C', 'Buffer D', 'Image']);
  const reads = Object.fromEntries(order.map((e) => [e.key, e.reads]));
  assert.deepEqual(reads.A, [{ channel: 1, key: 'A', sees: 'previous-frame' }, { channel: 0, key: 'D', sees: 'previous-frame' }]);
  assert.deepEqual(reads.B, [{ channel: 0, key: 'A', sees: 'this-frame' }]);
  assert.deepEqual(reads.C, [{ channel: 0, key: 'B', sees: 'this-frame' }, { channel: 1, key: 'D', sees: 'previous-frame' }]);
  assert.deepEqual(reads.D, [{ channel: 0, key: 'C', sees: 'this-frame' }]);
  assert.deepEqual(reads.image, [{ channel: 0, key: 'A', sees: 'this-frame' }]);
});

test('pass order: Cube A runs after the buffers and before Image; Common and Sound are not drawn', () => {
  const rp = [
    pass('Sound', 'sound', 'vec2 mainSound(int s, float t) { return vec2(0.0); }', [], ID.sound),
    img(MAIN('image'), [{ channel: 0, type: 'cubemap', id: ID.cube, filepath: '/media/a//media/previz/cubemap00.png', sampler: S() }]),
    pass('Cube A', 'cubemap', 'void mainCubemap(out vec4 o, in vec2 f, in vec3 ro, in vec3 rd) { o = vec4(1.0); }',
      [{ channel: 0, type: 'cubemap', id: ID.cube, filepath: '/media/a//media/previz/cubemap00.png', sampler: S() }, bufIn(1, 'A')], ID.cube),
    pass('Common', 'common', ''),
    pass('Buffer A', 'buffer', MAIN('A'), [{ channel: 0, type: 'cubemap', id: ID.cube, filepath: '/media/a//media/previz/cubemap00.png', sampler: S() }], ID.A),
  ];
  const order = R.passOrder(rp);
  assert.deepEqual(order.map((e) => e.key), ['A', 'cube', 'image']);
  assert.deepEqual(order[0].reads, [{ channel: 0, key: 'cube', sees: 'previous-frame' }]);
  assert.deepEqual(order[1].reads, [{ channel: 0, key: 'cube', sees: 'previous-frame' }, { channel: 1, key: 'A', sees: 'this-frame' }]);
  assert.deepEqual(order[2].reads, [{ channel: 0, key: 'cube', sees: 'this-frame' }]);
});

test('pass order: ids win over names, previz paths name buffers in old saves, missing producers are marked', () => {
  assert.equal(R.passKey({ type: 'buffer', name: 'whatever', outputs: [{ id: ID.C }] }), 'C');
  assert.equal(R.passKey({ type: 'buffer', name: 'Buf D', outputs: [] }), 'D');
  assert.equal(R.passKey({ type: 'buffer', name: 'Buffer b' }), 'B');
  assert.equal(R.passKey({ type: 'buffer', name: 'mystery' }), null);
  assert.equal(R.passKey({ type: 'image', name: '' }), 'image');
  assert.equal(R.passDisplayName({ type: 'image', name: '' }), 'Image');
  assert.equal(R.bufferKeyForInput({ type: 'buffer', id: 'zzzzzz', filepath: '/media/previz/buffer02.png' }), 'C');
  assert.equal(R.bufferKeyForInput({ type: 'buffer', id: 'zzzzzz', filepath: '' }), null);
  const order = R.passOrder([img(MAIN('i'), [bufIn(0, 'B')]), pass('Buffer A', 'buffer', MAIN('A'), [], ID.A),
    pass('Buffer A again', 'buffer', MAIN('A2'), [], ID.A)]);
  assert.deepEqual(order.map((e) => e.key), ['A', 'image']);
  assert.deepEqual(order[1].reads, [{ channel: 0, key: 'B', sees: 'missing' }]);
  assert.equal(order.duplicates.length, 1);
});

// ---------------------------------------------------------------------------------------------------------------
// Samplers
// ---------------------------------------------------------------------------------------------------------------
test('samplers: every filter x wrap x vflip x srgb combination, for an uploaded texture', () => {
  const F = { nearest: [GL.NEAREST, GL.NEAREST, false], linear: [GL.LINEAR, GL.LINEAR, false], mipmap: [GL.LINEAR_MIPMAP_LINEAR, GL.LINEAR, true] };
  const W = { clamp: GL.CLAMP_TO_EDGE, repeat: GL.REPEAT, mirror: GL.MIRRORED_REPEAT };
  for (const filter of Object.keys(F)) for (const wrap of Object.keys(W)) for (const vflip of ['true', 'false', true, false]) for (const srgb of ['true', 'false']) {
    const s = R.samplerFor({ type: 'texture', sampler: { filter, wrap, vflip, srgb } });
    const want = F[filter];
    assert.equal(s.filter, filter); assert.equal(s.wrap, wrap);
    assert.equal(s.minFilter, want[0]); assert.equal(s.magFilter, want[1]); assert.equal(s.mipmaps, want[2]);
    assert.equal(s.wrapS, W[wrap]); assert.equal(s.wrapT, W[wrap]); assert.equal(s.wrapR, W[wrap]);
    assert.equal(s.flipY, vflip === true || vflip === 'true');
    assert.equal(s.internalFormat, srgb === 'true' ? GL.SRGB8_ALPHA8 : GL.RGBA8);
  }
});

test('samplers: buffers, data textures and volumes are never flipped or sRGB-decoded; defaults per kind', () => {
  for (const type of ['buffer', 'keyboard', 'music', 'musicstream', 'volume']) {
    const s = R.samplerFor({ type, sampler: S('linear', 'clamp', 'true', 'true') });
    assert.equal(s.flipY, false, type); assert.equal(s.internalFormat, GL.RGBA8, type);
  }
  const cube = R.samplerFor({ type: 'cubemap', id: 'XsX3zn', sampler: S('mipmap', 'clamp', 'true', 'true') });
  assert.equal(cube.flipY, true); assert.equal(cube.internalFormat, GL.SRGB8_ALPHA8);
  assert.equal(R.samplerFor({ type: 'video', sampler: S('linear', 'clamp', 'true') }).flipY, true);
  // Nothing saved: the kind's default.
  assert.deepEqual([R.samplerFor({ type: 'buffer' }).filter, R.samplerFor({ type: 'buffer' }).wrap], ['linear', 'clamp']);
  assert.deepEqual([R.samplerFor({ type: 'texture' }).filter, R.samplerFor({ type: 'texture' }).wrap], ['mipmap', 'repeat']);
  assert.equal(R.samplerFor({ type: 'texture', sampler: { filter: 'bogus' } }).filter, 'mipmap');
});

test('input kinds: every ctype the corpus uses, and Cube A told apart from a cubemap image', () => {
  const kinds = { buffer: 'buffer', texture: 'texture', keyboard: 'keyboard', volume: 'volume', music: 'audio',
    musicstream: 'audio', mic: 'audio', video: 'video', webcam: 'webcam', nonsense: 'unknown' };
  for (const [type, kind] of Object.entries(kinds)) assert.equal(R.inputKind({ type }), kind, type);
  assert.equal(R.inputKind({ ctype: 'texture' }), 'texture');
  assert.equal(R.inputKind({ type: 'cubemap', id: 'XsX3zn', filepath: '/media/a/x.png' }), 'cubemap');
  assert.equal(R.inputKind({ type: 'cubemap', id: ID.cube }), 'cubebuffer');
  assert.equal(R.inputKind({ type: 'cubemap', id: '??', filepath: '/media/a//media/previz/cubemap00.png' }), 'cubebuffer');
});

// ---------------------------------------------------------------------------------------------------------------
// Data textures, media and time
// ---------------------------------------------------------------------------------------------------------------
function volumeBin({ sig = 'BIN\0', w = 4, h = 3, d = 2, ch = 1, layout = 0, fmt = 0, extra = 0, fill = (i) => i & 255 } = {}) {
  const bpc = fmt === 10 ? 4 : 1;
  const n = w * h * d * ch;
  const ab = new ArrayBuffer(20 + n * bpc + extra);
  const v = new DataView(ab);
  for (let i = 0; i < 4; i++) v.setUint8(i, sig.charCodeAt(i) || 0);
  v.setUint32(4, w, true); v.setUint32(8, h, true); v.setUint32(12, d, true);
  v.setUint8(16, ch); v.setUint8(17, layout); v.setUint16(18, fmt, true);
  for (let i = 0; i < n; i += 1) { if (fmt === 10) v.setFloat32(20 + i * 4, fill(i) / 7, true); else v.setUint8(20 + i, fill(i)); }
  return ab;
}

test('volume .bin: header fields, texel views and the GL formats they need', () => {
  const a = R.parseVolumeBin(volumeBin());
  assert.deepEqual([a.signature, a.width, a.height, a.depth, a.channels, a.format, a.dataOffset], ['BIN', 4, 3, 2, 1, 'u8', 20]);
  assert.ok(a.data instanceof Uint8Array); assert.equal(a.data.length, 24); assert.equal(a.data[5], 5);
  assert.deepEqual([a.glInternal, a.glFormat, a.glType], [GL.R8, GL.RED, GL.UNSIGNED_BYTE]);
  const b = R.parseVolumeBin(new Uint8Array(volumeBin({ w: 2, h: 2, d: 2, ch: 4, extra: 3 })));
  assert.deepEqual([b.channels, b.glInternal, b.glFormat, b.trailingBytes], [4, GL.RGBA8, GL.RGBA, 3]);
  const c = R.parseVolumeBin(volumeBin({ w: 2, h: 1, d: 1, ch: 2, fmt: 10 }));
  assert.ok(c.data instanceof Float32Array); assert.equal(c.data.length, 4);
  assert.ok(Math.abs(c.data[3] - 3 / 7) < 1e-6);
  assert.deepEqual([c.format, c.glInternal, c.glFormat, c.glType], ['f32', GL.RG32F, GL.RG, GL.FLOAT]);
  assert.equal(R.parseVolumeBin(volumeBin({ ch: 3 })).glInternal, GL.RGB8);
});

test('volume .bin: short, truncated, unknown-format and empty files are refused with a reason', () => {
  assert.throws(() => R.parseVolumeBin(new ArrayBuffer(10)), /shorter than the 20-byte header/);
  assert.throws(() => R.parseVolumeBin(volumeBin().slice(0, 30)), /file holds 10/);
  assert.throws(() => R.parseVolumeBin(volumeBin({ fmt: 3 })), /unknown texel format 3/);
  assert.throws(() => R.parseVolumeBin(volumeBin({ ch: 0 })), /0 channels/);
  assert.throws(() => R.parseVolumeBin(volumeBin({ w: 0 })), /empty size/);
});

test('keyboard texture: 256 x 3, down / pressed-this-frame / toggle rows, and their texel centres', () => {
  const L = R.keyboardTextureLayout();
  assert.deepEqual([L.width, L.height, L.bytes, L.internalFormat, L.format], [256, 3, 768, GL.R8, GL.RED]);
  assert.deepEqual(L.rows, { down: 0, pressed: 1, toggle: 2 });
  assert.equal(L.index(65, 0), 65); assert.equal(L.index(65, 1), 321); assert.equal(L.index(65, 2), 577);
  assert.ok(Math.abs(L.rowV(0) - 1 / 6) < 1e-12 && Math.abs(L.rowV(2) - 5 / 6) < 1e-12);
  const k = R.createKeyboardState();
  k.markClean();
  k.set(65, true);
  assert.ok(k.dirty);
  assert.deepEqual([k.bytes[65], k.bytes[321], k.bytes[577]], [255, 255, 255]);
  k.markClean(); k.set(65, true);   // auto-repeat while held changes nothing
  assert.ok(!k.dirty); assert.equal(k.bytes[577], 255);
  k.endFrame();
  assert.deepEqual([k.bytes[65], k.bytes[321], k.bytes[577]], [255, 0, 255]);
  k.set(65, false);
  assert.deepEqual([k.bytes[65], k.bytes[577]], [0, 255]);
  k.set(65, true); k.endFrame();
  assert.deepEqual([k.bytes[65], k.bytes[321], k.bytes[577]], [255, 0, 0]);
  k.clear();
  assert.ok(k.bytes.every((b) => b === 0));
});

test('audio texture: 512 x 2 bytes, spectrum row then waveform row, resampled and clamped', () => {
  const silent = R.packAudioTexture(null, null);
  assert.equal(silent.length, 1024);
  assert.ok(silent.subarray(0, 512).every((b) => b === 0));
  assert.ok(silent.subarray(512).every((b) => b === 128));
  const fft = new Float32Array(512).map((_, i) => i / 511);
  const wave = new Float32Array(512).map((_, i) => (i / 511) * 2 - 1);
  const t = R.packAudioTexture(fft, wave);
  assert.deepEqual([t[0], t[511], t[256]], [0, 255, Math.round((256 / 511) * 255)]);
  assert.deepEqual([t[512], t[1023]], [0, 255]);
  const mid = R.packAudioTexture(null, [0, 0, 0]);
  assert.equal(mid[512 + 100], 128);
  // 1024 bins resample across the whole range; out-of-range and NaN clamp.
  const long = R.packAudioTexture(new Float32Array(1024).map((_, i) => i / 1023), [-5, 5, NaN]);
  assert.equal(long[0], 0); assert.equal(long[511], 255);
  assert.equal(long[512], 0); assert.equal(long[767], 255);
  assert.equal(R.packAudioTexture([2, -1])[0], 255);
  assert.equal(R.packAudioTexture([NaN])[3], 0);
  const out = new Uint8Array(1024);
  assert.equal(R.packAudioTexture([1], [1], out), out);
  assert.deepEqual([R.AUDIO.width, R.AUDIO.height], [512, 2]);
});

test('cubemap faces: the saved name is +X and _1.._5 follow, keeping the extension', () => {
  assert.deepEqual(R.cubemapFacePaths('/media/a/abc.png'),
    ['/media/a/abc.png', '/media/a/abc_1.png', '/media/a/abc_2.png', '/media/a/abc_3.png', '/media/a/abc_4.png', '/media/a/abc_5.png']);
  assert.equal(R.cubemapFacePaths('/media/a/d.e/f.jpg')[3], '/media/a/d.e/f_3.jpg');
  assert.equal(R.cubemapFacePaths('/media/a/noext')[1], '/media/a/noext_1');
});

test('cube face basis: a direction rendered on face f at (sc, tc) is read back from face f at (sc, tc)', () => {
  // The GL cube-map selection table, written out: major axis -> face, sc, tc.
  const select = ([x, y, z]) => {
    const ax = Math.abs(x), ay = Math.abs(y), az = Math.abs(z);
    if (ax >= ay && ax >= az) return x > 0 ? [0, -z / ax, -y / ax] : [1, z / ax, -y / ax];
    if (ay >= az) return y > 0 ? [2, x / ay, z / ay] : [3, x / ay, -z / ay];
    return z > 0 ? [4, x / az, -y / az] : [5, -x / az, -y / az];
  };
  for (let f = 0; f < 6; f++) {
    const B = R.cubeFaceBasis(f);
    for (const sc of [-0.9, -0.3, 0, 0.45, 0.95]) for (const tc of [-0.8, 0, 0.2, 0.9]) {
      const d = [0, 1, 2].map((i) => B.center[i] + sc * B.right[i] + tc * B.up[i]);
      const [face, s2, t2] = select(d);
      assert.equal(face, f, `face ${B.name} at ${sc},${tc}`);
      assert.ok(Math.abs(s2 - sc) < 1e-12 && Math.abs(t2 - tc) < 1e-12, `${B.name} ${sc},${tc} -> ${s2},${t2}`);
    }
  }
  assert.deepEqual(R.CUBE_FACES.map((f) => f.name), ['+X', '-X', '+Y', '-Y', '+Z', '-Z']);
});

test('frame schedule: fixed dt from a reset, ending exactly on t', () => {
  const s = R.advanceSchedule(0, null, 1.5, 30);
  assert.equal(s.length, 46);
  assert.deepEqual(s.map((x) => x.frame), [...Array(46).keys()]);
  assert.equal(s[0].time, 0); assert.equal(s[0].timeDelta, 1 / 30);
  assert.equal(s[45].time, 1.5); assert.ok(s[45].final);
  assert.ok(s.slice(1).every((x, i) => Math.abs(x.timeDelta - 1 / 30) < 1e-12 && x.time === x.frame / 30 || x.final));
  const off = R.advanceSchedule(0, null, 1.55, 30);
  assert.equal(off.length, 48);
  assert.equal(off[46].time, 46 / 30); assert.equal(off[47].time, 1.55); assert.ok(off[47].final);
  assert.ok(Math.abs(off[47].timeDelta - (1.55 - 46 / 30)) < 1e-12);
  const zero = R.advanceSchedule(0, null, 0, 30);
  assert.deepEqual(zero, [{ frame: 0, time: 0, timeDelta: 1 / 30, final: true }]);
  assert.deepEqual(R.advanceSchedule(46, 1.5, 1.5, 30), []);
  assert.deepEqual(R.advanceSchedule(46, 1.5, 1.0, 30), []);
});

test('frame schedule: continuing from an on-grid t equals a fresh run; chunked walks join to the whole', () => {
  const fresh = R.advanceSchedule(0, null, 4, 30);
  const first = R.advanceSchedule(0, null, 1.5, 30);
  const last = first[first.length - 1];
  const rest = R.advanceSchedule(last.frame + 1, last.time, 4, 30);
  assert.deepEqual([...first, ...rest].map(({ final, ...x }) => x), fresh.map(({ final, ...x }) => x));
  // The same is NOT true after an off-grid stop, which is why render.js resets then.
  const offFirst = R.advanceSchedule(0, null, 1.55, 30);
  const o = offFirst[offFirst.length - 1];
  const offRest = R.advanceSchedule(o.frame + 1, o.time, 4, 30);
  assert.notDeepEqual([...offFirst, ...offRest].map((x) => x.time), fresh.map((x) => x.time));
  // Chunks of 7 rebuild the uncut list.
  const pieces = [];
  let frame = 0, lastTime = null;
  for (;;) {
    const part = R.advanceSchedule(frame, lastTime, 2.0, 24, 7);
    if (!part.length) break;
    pieces.push(...part);
    frame = part[part.length - 1].frame + 1; lastTime = part[part.length - 1].time;
  }
  assert.deepEqual(pieces, R.advanceSchedule(0, null, 2.0, 24));
  assert.ok(R.onFrameGrid(1.5, 30) && R.onFrameGrid(0, 30) && R.onFrameGrid(2, 24));
  assert.ok(!R.onFrameGrid(1.55, 30) && !R.onFrameGrid(0.01, 30));
});

test('iDate: year, 0-based month, day, seconds since midnight; a ready vec4 passes through', () => {
  const d = R.dateUniform(new Date(2026, 9, 13, 1, 2, 3, 500));
  assert.deepEqual(d, [2026, 9, 13, 3723.5]);
  assert.deepEqual(R.dateUniform([2026, 0, 1, 43200]), [2026, 0, 1, 43200]);
  assert.deepEqual(DATE_BASE, [2026, 0, 1, 43200]);
});

test('buffer formats: RGBA32F only with float linear filtering, then RGBA16F, then RGBA8', () => {
  const names = (caps) => R.bufferFormatCandidates(caps).map((f) => f.name);
  assert.deepEqual(names({ colorBufferFloat: true, floatLinear: true }), ['RGBA32F', 'RGBA16F', 'RGBA8']);
  assert.deepEqual(names({ colorBufferFloat: true }), ['RGBA16F', 'RGBA8']);
  assert.deepEqual(names({ colorBufferHalfFloat: true }), ['RGBA16F', 'RGBA8']);
  assert.deepEqual(names({}), ['RGBA8']);
  assert.equal(R.chooseBufferFormat({ colorBufferFloat: true, floatLinear: true }).internal, GL.RGBA32F);
  assert.equal(R.BUFFER_FORMATS.RGBA16F.type, GL.HALF_FLOAT);
});

test('stand-ins: seeded, repeatable, distinct per source, with the paired-channel noise layout', () => {
  const a = R.proceduralTexture('/media/a/x.png', 64, 32);
  assert.equal(a.length, 64 * 32 * 4);
  assert.deepEqual(a, R.proceduralTexture('/media/a/x.png', 64, 32));
  assert.notDeepEqual(a, R.proceduralTexture('/media/a/y.png', 64, 32));
  const at = (x, y, c) => a[(y * 64 + x) * 4 + c];
  for (const [x, y] of [[0, 0], [40, 20], [63, 31], [37, 17], [5, 30]]) {
    const sx = (((x - 37) % 64) + 64) % 64, sy = (((y - 17) % 32) + 32) % 32;
    assert.equal(at(x, y, 1), at(sx, sy, 0));
    assert.equal(at(x, y, 3), at(sx, sy, 2));
  }
  const mean = a.reduce((s, v) => s + v, 0) / a.length;
  assert.ok(mean > 110 && mean < 145, `noise mean ${mean}`);
  const v = R.proceduralVolume('/media/a/v.bin', 8);
  assert.equal(v.length, 8 * 8 * 8 * 4);
  assert.deepEqual(v, R.proceduralVolume('/media/a/v.bin', 8));
  assert.equal(R.hashString('abc'), R.hashString('abc'));
  assert.notEqual(R.hashString('abc'), R.hashString('abd'));
});

test('shader JSON shapes: the saved form, the API envelope, a list, and a bare .frag', () => {
  const s = shaderOf(img(MAIN('i')));
  assert.equal(R.normalizeShader(s), s);
  assert.equal(R.normalizeShader({ Shader: s }), s);
  assert.equal(R.normalizeShader([s]), s);
  assert.throws(() => R.normalizeShader({ info: {} }), /no renderpass/);
  const g = R.shaderFromGlsl('void mainImage(out vec4 o, in vec2 u) { o = vec4(1.0); }', { name: 'x.frag' });
  assert.equal(g.renderpass.length, 1);
  assert.equal(R.passKey(g.renderpass[0]), 'image');
  assert.equal(g.info.name, 'x.frag');
});

// ---------------------------------------------------------------------------------------------------------------
// render.js helpers
// ---------------------------------------------------------------------------------------------------------------
test('render page params: defaults, limits, and errors that name the bad value', () => {
  const p = parseParams('?src=/corpus/abc123/shader.json&t=0,1.5,4&w=480&h=270&fps=30&media=/corpus/media/', '/lab/render.html');
  assert.deepEqual([p.src, p.times, p.w, p.h, p.fps, p.media, p.budgetMs, p.cube, p.hw, p.errors],
    ['/corpus/abc123/shader.json', [0, 1.5, 4], 480, 270, 30, '/corpus/media/', 120000, 1024, 1, []]);
  assert.equal(parseParams('?src=x', '/lab/render.html').media, '/corpus/media/');
  assert.equal(parseParams('?src=x', '/elsewhere/render.html').media, null);
  assert.equal(parseParams('?src=x&media=', '/lab/render.html').media, null);
  assert.deepEqual(parseParams('?src=x&w=99999').w, 4096);
  assert.match(parseParams('').errors[0], /missing \?src=/);
  assert.match(parseParams('?src=x&t=1,abc').errors[0], /bad t list/);
  assert.match(parseParams('?src=x&t=-1').errors[0], /bad t list/);
  assert.match(parseParams('?src=x&fps=fast').errors[0], /bad fps=fast/);
});

test('render page media urls: /media/a/<file> maps under the prefix; nothing else has a url', () => {
  const m = mediaResolver('/corpus/media');
  assert.equal(m('/media/a/abc.png'), '/corpus/media/abc.png');
  assert.equal(m('/media/a/abc_3.jpg'), '/corpus/media/abc_3.jpg');
  assert.equal(m('/presets/tex00.jpg'), null);
  assert.equal(m('https://soundcloud.com/x/y'), null);
  assert.equal(m('/media/a/'), null);
  assert.equal(mediaResolver(null)('/media/a/abc.png'), null);
});

test('render page bodies: JSON shapes and bare GLSL both become a shader', () => {
  const s = shaderOf(img(MAIN('i')));
  assert.deepEqual(shaderFromBody(JSON.stringify(s), '/corpus/x/shader.json'), s);
  assert.equal(shaderFromBody('void mainImage(out vec4 o, in vec2 u) { o = vec4(1.0); }', '/jobs/sketch.frag').info.name, 'sketch.frag');
  assert.equal(shaderFromBody('void mainImage(out vec4 o, in vec2 u) {}', '/jobs/x.json').renderpass.length, 1);
  assert.throws(() => shaderFromBody('<html>', '/x.json'), /neither JSON nor GLSL/);
});

// ---------------------------------------------------------------------------------------------------------------
// The GL path, against FakeGL
// ---------------------------------------------------------------------------------------------------------------
test('runtime: context attributes are the CPU-still ones, and the renderer string is read unmasked', () => {
  const { gl, canvas, toy } = makeToy(shaderOf(img(MAIN('i'))));
  assert.equal(canvas.attrs.preserveDrawingBuffer, true);
  assert.equal(canvas.attrs.failIfMajorPerformanceCaveat, false);
  assert.equal(canvas.attrs.antialias, false);
  assert.ok(toy.info().swiftshader);
  assert.ok(R.rendererInfo(gl).unmasked);
  const amd = new FakeGL({ renderer: 'ANGLE (AMD, AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0, D3D11)' });
  assert.equal(R.rendererInfo(amd).swiftshader, false);
});

test('runtime: compiles every pass with #version on line 1 and draws A, B, C, D, Image each frame', () => {
  const { gl, toy } = makeToy(graphShader());
  const c = toy.compile();
  assert.ok(c.ok && c.drawable, JSON.stringify(c.passes.map((p) => p.mappedLog)));
  assert.deepEqual(c.passes.map((p) => p.key).sort(), ['A', 'B', 'C', 'D', 'image']);
  toy.render({ time: 0, frame: 0 });
  assert.deepEqual(gl.draws.map((d) => d.tag), ['A', 'B', 'C', 'D', 'image']);
  assert.deepEqual(gl.violations, []);
  assert.equal(toy.stats().bufferFormat, 'RGBA32F');
  assert.deepEqual(toy.stats().order, ['A', 'B', 'C', 'D', 'image']);
});

test('runtime: ping-pong gives a self-read last frame, a read of a later pass last frame, an earlier pass this frame', () => {
  const { gl, toy } = makeToy(graphShader());
  toy.compile();
  const FRAMES = 4;
  for (let f = 0; f < FRAMES; f++) toy.render({ time: f / 60, frame: f });
  assert.deepEqual(gl.violations, []);
  const frames = [];
  for (let f = 0; f < FRAMES; f++) frames.push(Object.fromEntries(gl.draws.slice(f * 5, f * 5 + 5).map((d) => [d.tag, d])));
  for (let f = 1; f < FRAMES; f++) {
    const now = frames[f], prev = frames[f - 1];
    assert.equal(now.A.reads[1], prev.A.write, 'A reads itself: previous frame');
    assert.equal(now.A.reads[0], prev.D.write, 'A reads D (later in the order): previous frame');
    assert.equal(now.B.reads[0], now.A.write, 'B reads A: this frame');
    assert.equal(now.C.reads[0], now.B.write, 'C reads B: this frame');
    assert.equal(now.C.reads[1], prev.D.write, 'C reads D: previous frame');
    assert.equal(now.D.reads[0], now.C.write, 'D reads C: this frame');
    assert.equal(now.image.reads[0], now.A.write, 'Image reads A: this frame');
    assert.notEqual(now.A.write, prev.A.write, 'A alternates targets');
    if (f >= 2) assert.equal(now.A.write, frames[f - 2].A.write);
  }
  assert.notEqual(frames[0].A.reads[1], frames[0].A.write);
  assert.equal(frames[0].image.write, 'canvas');
  assert.deepEqual(frames[2].A.res, [64, 36, 1]);
  assert.deepEqual(frames[2].image.chres.slice(0, 3), [64, 36, 1]);
  assert.deepEqual(frames[2].image.chres.slice(3), [0, 0, 0, 0, 0, 0, 0, 0, 0]);
  // Buffer D is sampled with mipmaps by C... no: D is read by C with linear, and C's read of D is plain; D's own
  // input (C) asked for mipmaps, so C gets a mip chain after each frame.
  const cWrite = gl.textures.find((t) => t.id === frames[3].C.write);
  assert.ok(cWrite.mips > 0, 'a buffer read with the mipmap filter gets mipmaps');
});

test('runtime: advance steps a fixed dt, is reproducible from a reset, and continues exactly', () => {
  const { gl, toy } = makeToy(graphShader(), { dateBase: [2026, 0, 1, 100] });
  toy.compile();
  let r = toy.advance(1.5, { fps: 30 });
  assert.deepEqual([r.frames, r.frame, r.time, r.reached, r.behind], [46, 46, 1.5, true, false]);
  assert.equal(gl.draws.length, 46 * 5);
  const lastImage = gl.draws[gl.draws.length - 1];
  assert.deepEqual([lastImage.frame, lastImage.time], [45, 1.5]);
  assert.deepEqual(lastImage.date, [2026, 0, 1, 101.5]);
  r = toy.advance(1.5, { fps: 30 });
  assert.deepEqual([r.frames, r.reached], [0, true]);
  r = toy.advance(1.55, { fps: 30 });
  assert.equal(r.frames, 2);
  const firstRun = gl.draws.slice(0, 46 * 5).map((d) => [d.tag, d.frame, d.time, d.reads.join(), d.write]);
  toy.reset();
  assert.equal(toy.stats().frame, 0);
  const before = gl.draws.length;
  r = toy.advance(1.5, { fps: 30, maxFrames: 10 });
  assert.deepEqual([r.frames, r.reached], [10, false]);
  while (!r.reached) r = toy.advance(1.5, { fps: 30, maxFrames: 10 });
  const secondRun = gl.draws.slice(before).map((d) => [d.tag, d.frame, d.time, d.reads.join(), d.write]);
  assert.deepEqual(secondRun, firstRun, 'same frames, same textures, same order after a reset');
  r = toy.advance(1.0, { fps: 30 });
  assert.deepEqual([r.frames, r.behind], [0, true]);
  assert.deepEqual(gl.violations, []);
});

test('runtime: reset clears both halves of every buffer', () => {
  const { gl, toy } = makeToy(graphShader());
  toy.compile();
  toy.advance(0.1, { fps: 30 });
  gl.clears.length = 0;
  const cTargets = [...new Set(gl.draws.filter((d) => d.tag === 'C').map((d) => d.write))].map((id) => gl.textures.find((t) => t.id === id));
  assert.equal(cTargets.length, 2);
  assert.ok(cTargets.every((t) => t.mips >= 2), 'a mipmap-read buffer has mips from allocation on, before its first render');
  const mipsBefore = cTargets.map((t) => t.mips);
  toy.reset();
  const bufferTexIds = new Set(gl.draws.filter((d) => d.write !== 'canvas').map((d) => d.write));
  assert.equal(bufferTexIds.size, 8);
  for (const id of bufferTexIds) assert.ok(gl.clears.includes(id), `texture ${id} cleared`);
  // The cleared level 0 is pushed down the mip chain, so no level keeps the previous run's pixels.
  assert.deepEqual(cTargets.map((t) => t.mips), mipsBefore.map((m) => m + 1));
});

test('runtime: a compile error names the pass and its own line; an error in Common names Common', () => {
  const common = 'float c1;\nfloat c2;\nfloat c3;';
  const bad = shaderOf(
    img(MAIN('image'), [bufIn(0, 'A')]),
    pass('Common', 'common', common),
    pass('Buffer A', 'buffer', '// PASS A\nfloat a;\nfloat b;\nfloat z = SYNTAX_ERROR_HERE;\nvoid mainImage(out vec4 o, in vec2 u) { o = vec4(0.0); }', [], ID.A),
  );
  const { toy } = makeToy(bad);
  const c = toy.compile();
  assert.equal(c.ok, false); assert.equal(c.drawable, false);
  const a = c.passes.find((p) => p.key === 'A');
  assert.equal(a.ok, false);
  assert.match(a.mappedLog, /^ERROR: Buffer A:4: 'SYNTAX_ERROR_HERE' : syntax error/m);
  assert.equal(a.firstError, "Buffer A:4: 'SYNTAX_ERROR_HERE' : syntax error");
  assert.ok(c.passes.find((p) => p.key === 'image').ok);

  const badCommon = shaderOf(img(MAIN('image')), pass('Common', 'common', 'float c1;\nfloat c2 = SYNTAX_ERROR_HERE;'));
  const c2 = makeToy(badCommon).toy.compile();
  assert.match(c2.passes[0].mappedLog, /^ERROR: Common:2: /m);

  const noEntry = makeToy(shaderOf(img('// PASS image\nfloat nothing;'))).toy.compile();
  assert.match(noEntry.passes[0].firstError, /^footer:\d+: 'mainImage'/);
});

test('runtime: a pass that fails to recompile keeps its old program (scratch compile links before replacing)', () => {
  const s = shaderOf(img(MAIN('image')));
  const { gl, toy } = makeToy(s);
  assert.ok(toy.compile().ok);
  s.renderpass[0].code = 'SYNTAX_ERROR_HERE';
  assert.equal(toy.compile().ok, false);
  toy.render({ time: 0 });
  assert.deepEqual(gl.draws.map((d) => d.tag), ['image']);
  assert.deepEqual(gl.violations, []);
});

test('runtime: Cube A renders six faces into one half, Image samples the finished cube as a samplerCube', () => {
  const cubeIn = { channel: 0, type: 'cubemap', id: ID.cube, filepath: '/media/a//media/previz/cubemap00.png', sampler: S() };
  const s = shaderOf(
    img(MAIN('image', 'o = texture(iChannel0, vec3(1.0, 0.0, 0.0));'), [cubeIn]),
    pass('Cube A', 'cubemap', '// PASS cube\nvoid mainCubemap(out vec4 o, in vec2 f, in vec3 ro, in vec3 rd) { o = texture(iChannel0, rd); }', [cubeIn], ID.cube),
  );
  const { gl, toy } = makeToy(s, { cubeSize: 16 });
  assert.ok(toy.compile().drawable);
  toy.render({ time: 0, frame: 0 });
  toy.render({ time: 1 / 60, frame: 1 });
  assert.deepEqual(gl.violations, []);
  const f0 = gl.draws.slice(0, 7), f1 = gl.draws.slice(7, 14);
  assert.deepEqual(f0.map((d) => d.tag), ['cube', 'cube', 'cube', 'cube', 'cube', 'cube', 'image']);
  assert.deepEqual(f0.slice(0, 6).map((d) => d.face), [0, 1, 2, 3, 4, 5]);
  assert.ok(f0.slice(0, 6).every((d) => d.write === f0[0].write));
  assert.deepEqual(f0[0].vp, [16, 16]);
  assert.deepEqual(f0[0].res, [16, 16, 1]);
  assert.equal(f0[6].reads[0], f0[0].write, 'Image reads this frame\'s cube');
  assert.equal(f1[0].reads[0], f0[0].write, 'the cube reads its own previous frame');
  assert.notEqual(f1[0].write, f0[0].write);
  assert.equal(toy.stats().cubeSize, 16);
});

test('runtime: buffer format falls back when float targets are missing or incomplete, and says so', () => {
  const s = graphShader();
  const noFloat = makeToy(s, {}, { ext: ['WEBGL_debug_renderer_info'] }).toy;
  assert.equal(noFloat.stats().bufferFormat, 'RGBA8');
  assert.ok(noFloat.stats().warnings.some((w) => /8-bit/.test(w)));
  const no32 = makeToy(s, {}, { unrenderable: [GL.RGBA32F] }).toy;
  assert.equal(no32.stats().bufferFormat, 'RGBA16F');
  const forced = makeToy(s, { bufferFormat: 'RGBA16F' }).toy;
  assert.equal(forced.stats().bufferFormat, 'RGBA16F');
  const imageOnly = makeToy(shaderOf(img(MAIN('i')))).toy;
  assert.equal(imageOnly.stats().bufferFormat, null);
});

test('runtime: missing media become seeded stand-ins and are listed; sound, unknown inputs and passes are listed', () => {
  const s = shaderOf(
    img(MAIN('image'), [
      { channel: 0, type: 'texture', id: 'Xsf3zn', filepath: '/media/a/noise.png', sampler: S('mipmap', 'repeat') },
      { channel: 1, type: 'video', id: 'Xdf3Rn', filepath: '/media/a/clip.webm', sampler: S() },
      { channel: 2, type: 'hologram', id: 'zzzzzz', filepath: '', sampler: S() },
      { channel: 3, type: 'buffer', id: ID.B, filepath: PREVIZ.B, sampler: S() },
    ]),
    pass('Sound', 'sound', 'vec2 mainSound(int s, float t) { return vec2(0.0); }', [], ID.sound),
    pass('Mystery', 'buffer', MAIN('m')),
  );
  const { gl, toy } = makeToy(s);
  const c = toy.compile();
  assert.ok(c.drawable);
  assert.ok(c.passes.find((p) => p.key === 'sound').ok, 'the Sound pass compiles');
  toy.render({ time: 0 });
  assert.deepEqual(gl.violations, []);
  const st = toy.stats();
  const reasons = Object.fromEntries(st.substituted.map((x) => [x.src, x.reason]));
  assert.match(reasons['/media/a/noise.png'], /no media url: procedural stand-in/);
  assert.match(reasons['/media/a/clip.webm'], /video playback is not supported/);
  assert.match(reasons[PREVIZ.B], /reads Buffer B that this shader lacks: black/);
  assert.ok(st.unsupported.some((u) => u.what === 'sound playback'));
  assert.ok(st.unsupported.some((u) => u.what === 'input' && u.type === 'hologram'));
  assert.ok(st.unsupported.some((u) => u.what === 'pass' && u.name === 'Mystery'));
  assert.deepEqual(gl.draws[0].chres.slice(0, 3), [256, 256, 1]);
});

class FakeImage {
  static calls = [];
  static sizes = new Map();
  constructor() { this.crossOrigin = null; this.onload = null; this.onerror = null; }
  get src() { return this._src; }
  set src(url) {
    this._src = url;
    FakeImage.calls.push(url);
    setTimeout(() => {
      if (/missing/.test(url)) { this.onerror && this.onerror(new Error('404')); return; }
      const [w, h] = FakeImage.sizes.get(url) || [64, 32];
      this.naturalWidth = this.width = w; this.naturalHeight = this.height = h;
      this.onload && this.onload();
    }, 1);
  }
}

test('runtime: media load through mediaUrl with flip and sRGB honoured; a failed load is listed', async () => {
  const saved = globalThis.Image;
  globalThis.Image = FakeImage;
  FakeImage.calls = [];
  try {
    const s = shaderOf(img(MAIN('image'), [
      { channel: 0, type: 'texture', id: 'a', filepath: '/media/a/good.png', sampler: S('mipmap', 'repeat', 'true', 'true') },
      { channel: 1, type: 'texture', id: 'b', filepath: '/media/a/missing.png', sampler: S('linear', 'repeat', 'false') },
      { channel: 2, type: 'cubemap', id: 'c', filepath: '/media/a/sky.jpg', sampler: S('mipmap', 'clamp', 'false') },
    ]));
    const { gl, toy } = makeToy(s, { mediaUrl: (src) => `http://127.0.0.1:8797/corpus/media/${src.split('/').pop()}` });
    assert.equal(toy.stats().loading, 3);
    await toy.ready;
    assert.equal(toy.stats().loading, 0);
    assert.equal(FakeImage.calls.length, 1 + 1 + 6);
    assert.ok(FakeImage.calls.includes('http://127.0.0.1:8797/corpus/media/sky_5.jpg'));
    const good = gl.uploads.find((u) => u.image && u.w === 64 && u.internal === GL.SRGB8_ALPHA8);
    assert.ok(good, 'the sRGB texture uploads as SRGB8_ALPHA8');
    assert.equal(good.flipY, true);
    const faces = gl.uploads.filter((u) => u.image && u.target >= GL.TEXTURE_CUBE_MAP_POSITIVE_X && u.target < GL.TEXTURE_CUBE_MAP_POSITIVE_X + 6);
    assert.equal(faces.length, 0, 'a 64x32 face set is not square: refused');
    const st = toy.stats();
    assert.ok(st.substituted.some((x) => x.src === '/media/a/missing.png' && /load failed/.test(x.reason)));
    assert.ok(st.substituted.some((x) => x.src === '/media/a/sky.jpg' && /not one square size/.test(x.reason)));
    assert.ok(!st.substituted.some((x) => x.src === '/media/a/good.png'));
    toy.compile();
    toy.render({ time: 0 });
    assert.deepEqual(gl.draws[0].chres.slice(0, 3), [64, 32, 1]);
    assert.deepEqual(gl.violations, []);

    // Square faces load, in GL face order, with the saved flip.
    FakeImage.calls = [];
    for (const f of R.cubemapFacePaths('/sq/box.png')) FakeImage.sizes.set(`u:${f}`, [16, 16]);
    const s2 = shaderOf(img(MAIN('image'), [{ channel: 0, type: 'cubemap', id: 'c', filepath: '/sq/box.png', sampler: S('linear', 'clamp', 'false') }]));
    const t2 = makeToy(s2, { mediaUrl: (src) => `u:${src}` });
    await t2.toy.ready;
    const faces2 = t2.gl.uploads.filter((u) => u.image && u.target >= GL.TEXTURE_CUBE_MAP_POSITIVE_X && u.target < GL.TEXTURE_CUBE_MAP_POSITIVE_X + 6);
    assert.deepEqual(faces2.map((u) => u.target - GL.TEXTURE_CUBE_MAP_POSITIVE_X), [0, 1, 2, 3, 4, 5]);
    assert.ok(faces2.every((u) => u.flipY === false));
    assert.deepEqual(FakeImage.calls, R.cubemapFacePaths('/sq/box.png').map((p) => `u:${p}`));
    assert.equal(t2.toy.stats().substituted.length, 0);
  } finally {
    globalThis.Image = saved;
  }
});

test('runtime: a .bin volume loads as a 3D texture through fetch', async () => {
  const savedFetch = globalThis.fetch;
  globalThis.fetch = async (url) => (/broken/.test(url)
    ? { ok: false, status: 404 }
    : { ok: true, status: 200, arrayBuffer: async () => volumeBin({ w: 8, h: 8, d: 8, ch: 1 }) });
  try {
    const s = shaderOf(img(MAIN('image'), [
      { channel: 0, type: 'volume', id: 'v', filepath: '/media/a/grey.bin', sampler: S('mipmap', 'repeat') },
      { channel: 1, type: 'volume', id: 'w', filepath: '/media/a/broken.bin', sampler: S('linear', 'repeat') },
    ]));
    const { gl, toy } = makeToy(s, { mediaUrl: (src) => `x:${src}` });
    await toy.ready;
    const vol = gl.uploads.find((u) => u.fn === 'texImage3D' && u.w === 8);
    assert.deepEqual([vol.internal, vol.d, vol.bytes], [GL.R8, 8, 512]);
    assert.ok(toy.stats().substituted.some((x) => x.src === '/media/a/broken.bin' && /HTTP 404/.test(x.reason)));
    toy.compile();
    toy.render({ time: 0 });
    assert.deepEqual(gl.draws[0].chres.slice(0, 6), [8, 8, 8, 32, 32, 32]);
    assert.match(gl.draws[0].reads.join(), /\d+,\d+/);
    assert.deepEqual(gl.violations, []);
  } finally {
    globalThis.fetch = savedFetch;
  }
});

test('runtime: setAudio feeds the audio texture and clears the silence notice; keyboard rows upload per frame', () => {
  const s = shaderOf(img(MAIN('image'), [
    { channel: 0, type: 'musicstream', id: 'm', filepath: 'https://soundcloud.com/someone/something', sampler: S() },
    { channel: 1, type: 'keyboard', id: 'k', filepath: '/presets/tex00.jpg', sampler: S('nearest') },
  ]));
  const { gl, toy } = makeToy(s);
  toy.compile();
  assert.ok(toy.stats().substituted.some((x) => x.kind === 'audio' && /silence/.test(x.reason)));
  toy.setAudio({ fft: new Float32Array(512).fill(1), wave: new Float32Array(512).fill(-1) });
  toy.setKeyboard(32, true);
  toy.render({ time: 0 });
  const audioUp = gl.uploads.filter((u) => u.fn === 'texSubImage2D' && u.w === 512).pop();
  assert.deepEqual([audioUp.data[0], audioUp.data[511], audioUp.data[512], audioUp.data[1023]], [255, 255, 0, 0]);
  const keyUp = gl.uploads.filter((u) => u.fn === 'texSubImage2D' && u.w === 256).pop();
  assert.deepEqual([keyUp.data[32], keyUp.data[256 + 32], keyUp.data[512 + 32]], [255, 255, 255]);
  assert.ok(!toy.stats().substituted.some((x) => x.kind === 'audio'));
  toy.render({ time: 1 / 60 });
  const keyUp2 = gl.uploads.filter((u) => u.fn === 'texSubImage2D' && u.w === 256).pop();
  assert.deepEqual([keyUp2.data[32], keyUp2.data[256 + 32], keyUp2.data[512 + 32]], [255, 0, 255], 'pressed clears after a frame');
  assert.deepEqual(gl.draws[0].chres.slice(0, 6), [512, 2, 1, 256, 3, 1]);
  toy.setAudio(null);
  assert.ok(toy.stats().substituted.some((x) => x.kind === 'audio'));
  assert.deepEqual(gl.violations, []);
});

test('runtime: resize reallocates the buffers at the new size; destroy frees and refuses further use', () => {
  const { gl, canvas, toy } = makeToy(graphShader(), { pixelRatio: 2 });
  toy.compile();
  toy.resize(40, 20);
  assert.deepEqual([canvas.width, canvas.height], [80, 40]);
  toy.render({ time: 0 });
  assert.deepEqual(gl.draws[0].res, [80, 40, 1]);
  assert.deepEqual(gl.draws[0].vp, [80, 40]);
  toy.destroy();
  assert.ok(gl.lost);
  assert.throws(() => toy.render({ time: 0 }), /destroyed/);
});

// ---------------------------------------------------------------------------------------------------------------
// Integration round 1: GPU-parity shims, history-free stills (jump), styled stand-ins
// ---------------------------------------------------------------------------------------------------------------
test('parity shims: tanh and min/max replacements come before their macros; shims: [] leaves the header bare', () => {
  const h = R.buildHeader('image', []).split('\n');
  for (const fn of ['tanh', 'min', 'max']) {
    const macro = h.indexOf(`#define ${fn} shaderlab_${fn}`);
    assert.ok(macro > 0, `${fn} macro`);
    const bodies = h.map((l, i) => [l, i]).filter(([l]) => l.includes(` shaderlab_${fn}(`) && !l.startsWith('#'));
    assert.ok(bodies.length >= 4, `${fn} overloads`);
    assert.ok(bodies.every(([, i]) => i < macro), `${fn}: every body precedes the macro, so its own call is the built-in`);
  }
  // Every built-in signature of min/max has a twin: float and vecN (with a float second operand), int, uint families.
  for (const fn of ['min', 'max']) {
    for (const sig of ['float a, float b', 'vec3 a, vec3 b', 'vec3 a, float b', 'int a, int b', 'ivec2 a, int b', 'uvec4 a, uvec4 b', 'uvec2 a, uint b']) {
      assert.ok(h.some((l) => l.includes(`shaderlab_${fn}(${sig})`)), `${fn}(${sig})`);
    }
  }
  assert.ok(h.some((l) => l.includes(`clamp(x, -${R.TANH_CLAMP}.0, ${R.TANH_CLAMP}.0)`)));
  const bare = R.buildHeader('image', [], { shims: [] });
  assert.ok(!bare.includes('shaderlab_tanh') && !bare.includes('shaderlab_min'));
  const tanhOnly = R.buildHeader('buffer', [], { shims: ['tanh'] });
  assert.ok(tanhOnly.includes('#define tanh shaderlab_tanh') && !tanhOnly.includes('shaderlab_max'));
  assert.deepEqual(R.PARITY_LEVELS.map((l) => l.name), ['full', 'tanh-only', 'minmax-only', 'none']);
});

// A rule of the real compiler, in miniature: a call to a user function is not a constant expression.
const CONST_RULE = (src, lines) => {
  if (!src.includes('#define max shaderlab_max')) return [];
  const at = lines.findIndex((l) => /^\s*const\s+int\s+\w+\s*=\s*max\(/.test(l));
  return at >= 0 ? [`ERROR: 0:${at + 1}: 'k' : global const initializers must be constant`] : [];
};

test('parity: a pass the min/max shim breaks compiles one level down, and says so; parity false compiles bare', () => {
  const s = shaderOf(img('// PASS image\nconst int k = max(3, 1);\nvoid mainImage(out vec4 o, in vec2 u) { o = vec4(float(k)); }\n'));
  const { gl, toy } = makeToy(s, {}, { rejects: CONST_RULE });
  const c = toy.compile();
  assert.ok(c.ok && c.drawable, JSON.stringify(c.passes));
  assert.equal(c.passes[0].parity, 'tanh-only');
  assert.ok(c.warnings.some((w) => /parity level "tanh-only"/.test(w)));
  toy.render({ time: 0 });
  assert.deepEqual(gl.violations, []);
  assert.equal(gl.draws.length, 1);
  assert.ok(gl.program.frag.includes('#define tanh shaderlab_tanh') && !gl.program.frag.includes('shaderlab_max'));

  const plain = makeToy(shaderOf(img(MAIN('image'))), {}, { rejects: CONST_RULE }).toy.compile();
  assert.equal(plain.passes[0].parity, 'full');
  assert.ok(!plain.warnings.some((w) => /parity level/.test(w)));

  const off = makeToy(s, { parity: false }, { rejects: CONST_RULE });
  const c3 = off.toy.compile();
  assert.equal(c3.passes[0].parity, 'none');
  off.toy.render({ time: 0 });
  assert.ok(!off.gl.program.frag.includes('shaderlab_tanh') && !off.gl.program.frag.includes('shaderlab_max'));
  assert.ok(!c3.warnings.some((w) => /parity level/.test(w)), 'no warning when bare was asked for');

  // A real error fails every level, and the log maps against the last (bare) header.
  const bad = makeToy(shaderOf(img('// PASS image\nfloat z = SYNTAX_ERROR_HERE;\nvoid mainImage(out vec4 o, in vec2 u) { o = vec4(0.0); }')));
  const cb = bad.toy.compile();
  assert.equal(cb.passes[0].parity, null);
  assert.equal(cb.passes[0].firstError, "Image:2: 'SYNTAX_ERROR_HERE' : syntax error");
});

test('jumpStep is the last frame of the walk from a reset, for every t and rate', () => {
  for (const fps of [24, 30, 60, 7]) {
    for (const t of [0, 0.01, 1 / 30, 0.5, 1, 1.5, 1.55, 2, 3.999, 4, 7.25, 12.3456]) {
      const walk = R.advanceSchedule(0, null, t, fps);
      assert.deepEqual(R.jumpStep(t, fps), walk[walk.length - 1], `t=${t} fps=${fps}`);
    }
  }
  assert.equal(R.jumpStep(NaN, 30), null);
});

test('needsHistory: only a read of an earlier frame (a self-read or a later pass) makes a shader need its walk', () => {
  assert.equal(R.needsHistory(graphShader().renderpass), true);
  const feedForward = shaderOf(img(MAIN('image'), [bufIn(0, 'A')]), pass('Buffer A', 'buffer', MAIN('A'), [], ID.A));
  assert.equal(R.needsHistory(feedForward.renderpass), false);
  assert.equal(R.needsHistory(shaderOf(img(MAIN('image'))).renderpass), false);
  const selfRead = shaderOf(img(MAIN('image'), [bufIn(0, 'A')]), pass('Buffer A', 'buffer', MAIN('A'), [bufIn(0, 'A')], ID.A));
  assert.equal(R.needsHistory(selfRead.renderpass), true);
});

test('runtime: jump draws one frame, the walk\'s last; a feedback shader refuses to jump', () => {
  const feedForward = shaderOf(img(MAIN('image'), [bufIn(0, 'A')]), pass('Buffer A', 'buffer', MAIN('A'), [], ID.A));
  const { gl, toy } = makeToy(feedForward, { dateBase: [2026, 0, 1, 0] });
  assert.equal(toy.history, false);
  toy.compile();
  const j = toy.jump(4, { fps: 30 });
  assert.deepEqual([j.frames, j.frame, j.time], [1, 120, 4]);
  assert.deepEqual(gl.draws.map((d) => [d.tag, d.frame, d.time]), [['A', 120, 4], ['image', 120, 4]]);
  const walked = makeToy(feedForward, { dateBase: [2026, 0, 1, 0] });
  walked.toy.compile();
  walked.toy.advance(4, { fps: 30 });
  const last = walked.gl.draws.slice(-2).map((d) => [d.tag, d.frame, d.time, d.date]);
  assert.deepEqual(gl.draws.map((d) => [d.tag, d.frame, d.time, d.date]), last);
  assert.deepEqual(gl.violations, []);
  const fb = makeToy(graphShader()).toy;
  assert.equal(fb.history, true);
  assert.equal(fb.stats().history, true);
  fb.compile();
  assert.throws(() => fb.jump(1, { fps: 30 }), /reads earlier frames/);
});

test('stand-ins by style: .png noise, .jpg photo-like, cubemap environment; each listed with its style', () => {
  assert.equal(R.standinStyle('texture', '/media/a/x.png'), 'noise');
  assert.equal(R.standinStyle('texture', '/media/a/x.JPG'), 'photo');
  assert.equal(R.standinStyle('texture', '/media/a/x.jpeg?v=1'), 'photo');
  assert.equal(R.standinStyle('cubemap', '/media/a/x.png'), 'environment');
  assert.equal(R.standinStyle('video', '/media/a/x.webm'), 'photo');
  // A photo stand-in: seeded, opaque, smooth (neighbours close, unlike per-texel noise), seamless when tiled.
  const W = 64;
  const p = R.proceduralPhoto('/media/a/p.jpg', W, W);
  assert.deepEqual(p, R.proceduralPhoto('/media/a/p.jpg', W, W));
  assert.notDeepEqual(p, R.proceduralPhoto('/media/a/q.jpg', W, W));
  const at = (im, x, y, c) => im[(y * W + x) * 4 + c];
  let step = 0, n = 0, alphaOk = true;
  for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
    if (at(p, x, y, 3) !== 255) alphaOk = false;
    step += Math.abs(at(p, x, y, 0) - at(p, (x + 1) % W, y, 0)); n++;   // the wrap-around step counts too
  }
  assert.ok(alphaOk);
  const noise = R.proceduralTexture('/media/a/p.png', W, W);
  let noiseStep = 0;
  for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) noiseStep += Math.abs(at(noise, x, y, 0) - at(noise, (x + 1) % W, y, 0));
  assert.ok(step / n < noiseStep / n / 4, `photo steps ${step / n} vs noise ${noiseStep / n}`);
  const mean = [0, 1, 2].map((c) => { let s = 0; for (let i = c; i < p.length; i += 4) s += p[i]; return s / (W * W); });
  assert.ok(mean.every((m) => m > 50 && m < 200), `photo mean ${mean}`);
  // The environment: six faces; looking up (+Y) is a bluer, brighter sky than looking down (-Y).
  const N = 8;
  const env = R.proceduralEnvironment('/media/a/e.png', N);
  assert.equal(env.length, 6);
  assert.ok(env.every((f) => f.length === N * N * 4));
  assert.deepEqual(env, R.proceduralEnvironment('/media/a/e.png', N));
  const centre = (f) => { const o = ((N / 2) * N + N / 2) * 4; return [f[o], f[o + 1], f[o + 2]]; };
  const up = centre(env[2]), down = centre(env[3]);
  assert.ok(up[2] > down[2] && up[0] + up[1] + up[2] > down[0] + down[1] + down[2], `up ${up} down ${down}`);
  // Through the runtime: listed with the style it drew.
  const s = shaderOf(img(MAIN('image'), [
    { channel: 0, type: 'texture', id: 't', filepath: '/media/a/wood.jpg', sampler: S('mipmap', 'repeat') },
    { channel: 1, type: 'cubemap', id: 'c', filepath: '/media/a/sky.png', sampler: S('mipmap', 'clamp') },
    { channel: 2, type: 'texture', id: 'n', filepath: '/media/a/noise.png', sampler: S('mipmap', 'repeat') },
  ]));
  const st = makeToy(s).toy.stats();
  const style = Object.fromEntries(st.substituted.map((x) => [x.src, x.style]));
  assert.deepEqual(style, { '/media/a/wood.jpg': 'photo', '/media/a/sky.png': 'environment', '/media/a/noise.png': 'noise' });
});

test('stand-ins the corpus pins down: KNOWN_MEDIA sizes and kinds reach the texture the shader reads', () => {
  const blue = '/media/a/cb49c003b454385aa9975733aff4571c62182ccdda480aaba9a8d250014f00ec.png';
  const small = '/media/a/3083c722c0c738cad0f468383167a0d246f91af2bfa373e9c5c094fb8c8413e0.png';
  const smooth = '/media/a/ad56fba948dfba9ae698198c109e71f118a54d209c0ea50d77ea546abad89c57.png';
  assert.deepEqual([R.standinSize('texture', blue), R.standinSize('texture', small), R.standinSize('texture', '/media/a/x.png')],
    [1024, 64, R.STANDIN_SIZE]);
  assert.equal(R.standinStyle('texture', smooth), 'photo');
  assert.equal(R.standinPixels('texture', small).length, 64 * 64 * 4);
  const s = shaderOf(img(MAIN('image'), [
    { channel: 0, type: 'texture', id: 'b', filepath: blue, sampler: S('nearest', 'repeat') },
    { channel: 1, type: 'texture', id: 's', filepath: small, sampler: S('mipmap', 'repeat') },
  ]));
  const { gl, toy } = makeToy(s);
  toy.compile();
  toy.render({ time: 0 });
  assert.deepEqual(gl.draws[0].chres.slice(0, 6), [1024, 1024, 1, 64, 64, 1]);
  assert.deepEqual(gl.violations, []);
});

test('sound pass: its header has the sound uniforms only, so a sound pass may declare its own iResolution and iMouse', () => {
  const h = R.buildHeader('sound', []).split('\n');
  for (const gone of ['uniform vec3 iResolution;', 'uniform float iTime;', 'uniform float iTimeDelta;', 'uniform float iFrameRate;',
    'uniform int iFrame;', 'uniform vec4 iMouse;']) assert.ok(!h.includes(gone), gone);
  for (const kept of ['uniform float iChannelTime[4];', 'uniform vec3 iChannelResolution[4];', 'uniform vec4 iDate;',
    'uniform float iSampleRate;', 'uniform float iBlockOffset;']) assert.ok(h.includes(kept), kept);
  assert.ok(R.buildHeader('image', []).includes('uniform vec3 iResolution;'));
  // The real compiler refuses a global that redeclares a uniform; ours, in miniature.
  const REDECL = (src) => (/uniform vec3 iResolution;/.test(src) && /^\w+(\s+\w+)?\s+iResolution\s*=/m.test(src)
    ? ["ERROR: 0:1: 'iResolution' : redefinition"] : []);
  const s = shaderOf(img(MAIN('image')),
    pass('Sound', 'sound', 'const float iResolution = 2.0;\nfloat iMouse = 0.25;\nvec2 mainSound(in int sampleIndex, in float when) { return vec2(iResolution * iMouse); }', [], ID.sound));
  const c = makeToy(s, {}, { rejects: REDECL }).toy.compile();
  assert.ok(c.ok, JSON.stringify(c.passes.map((x) => x.firstError)));
  const src = R.assembleSource(s.renderpass[1]).source;
  assert.ok(/int\(shaderlab_blockSize\.x\)/.test(src) && !/int\(iResolution\.x\)/.test(src));
});

// ---------------------------------------------------------------------------------------------------------------
// Review round (2026-10-13): fidelity against Shadertoy's own client behaviour, and the page's renderer rule.
// Shadertoy's behaviour was read from its client code (effect.js, piLibs.js and the page script, in public mirrors):
// buffers paint in the saved renderpass order, then Cube A, then Image; a resize copies each buffer's old contents;
// iMouse signs its click; iChannelTime is each channel's media clock; a flipped cubemap swaps its +Y and -Y images.
// ---------------------------------------------------------------------------------------------------------------
test('defaults: stills step at 60 fps (Shadertoy runs at about 60), in the runtime and on the render page', () => {
  assert.equal(R.DEFAULT_FPS, 60);
  assert.equal(parseParams('?src=x').fps, 60);
  // A history-free t=4 still is frame 240, as Shadertoy would number it, not 120.
  assert.equal(R.jumpStep(4, parseParams('?src=x').fps).frame, 240);
});

// The shape of WdyGzy (a love_top Lattice Boltzmann shader): buffers saved A, D, B, C, and B reads D.
function savedOrderShader() {
  return shaderOf(
    pass('Buffer A', 'buffer', MAIN('A'), [bufIn(0, 'A')], ID.A),
    pass('Buffer D', 'buffer', MAIN('D'), [bufIn(0, 'A')], ID.D),
    pass('Buffer B', 'buffer', MAIN('B'), [bufIn(0, 'D')], ID.B),
    pass('Buffer C', 'buffer', MAIN('C'), [bufIn(0, 'B'), bufIn(1, 'C')], ID.C),
    img(MAIN('image'), [bufIn(0, 'C')]),
  );
}

test('pass order: buffers run in the order the shader saved them (not by letter), then Cube A, then Image', () => {
  const order = R.passOrder(savedOrderShader().renderpass);
  assert.deepEqual(order.map((e) => e.key), ['A', 'D', 'B', 'C', 'image']);
  const reads = Object.fromEntries(order.map((e) => [e.key, e.reads]));
  assert.deepEqual(reads.B, [{ channel: 0, key: 'D', sees: 'this-frame' }], 'B reads D, saved before it: this frame');
  assert.deepEqual(reads.D, [{ channel: 0, key: 'A', sees: 'this-frame' }]);
  assert.deepEqual(reads.C, [{ channel: 0, key: 'B', sees: 'this-frame' }, { channel: 1, key: 'C', sees: 'previous-frame' }]);
  // Image and Cube A saved first still run last; the buffers keep their saved order among themselves.
  const cubeIn = { channel: 0, type: 'cubemap', id: ID.cube, filepath: '/media/a//media/previz/cubemap00.png', sampler: S() };
  const mixed = R.passOrder([
    img(MAIN('image'), [cubeIn]),
    pass('Cube A', 'cubemap', 'void mainCubemap(out vec4 o, in vec2 f, in vec3 ro, in vec3 rd) { o = vec4(1.0); }', [bufIn(0, 'A')], ID.cube),
    pass('Buffer B', 'buffer', MAIN('B'), [bufIn(0, 'A')], ID.B),
    pass('Common', 'common', ''),
    pass('Buffer A', 'buffer', MAIN('A'), [], ID.A),
  ]);
  assert.deepEqual(mixed.map((e) => e.key), ['B', 'A', 'cube', 'image']);
  assert.deepEqual(mixed[0].reads, [{ channel: 0, key: 'A', sees: 'previous-frame' }], 'B saved before A sees A\'s last frame');
});

test('runtime: the saved buffer order is the draw order, and a read of an earlier-saved buffer sees this frame', () => {
  const { gl, toy } = makeToy(savedOrderShader());
  toy.compile();
  for (let f = 0; f < 3; f++) toy.render({ time: f / 60, frame: f });
  assert.deepEqual(gl.violations, []);
  assert.deepEqual(toy.stats().order, ['A', 'D', 'B', 'C', 'image']);
  assert.deepEqual(gl.draws.slice(0, 5).map((d) => d.tag), ['A', 'D', 'B', 'C', 'image']);
  const f2 = Object.fromEntries(gl.draws.slice(10, 15).map((d) => [d.tag, d]));
  assert.equal(f2.B.readContent[0], 'D@2', 'B reads the D drawn earlier in this frame');
  assert.equal(f2.C.readContent[1], 'C@1', 'C reads its own previous frame');
  assert.equal(f2.image.readContent[0], 'C@2');
});

// The float overloads of a min/max shim, evaluated in JS: GLSL mix(x, y, bool) picks y when the bool is true.
function shimBody(fn) {
  const line = R.buildHeader('image', []).split('\n').find((l) => l.startsWith(`float shaderlab_${fn}(float a, float b)`));
  return /return (.*); }$/.exec(line)[1];
}
test('parity: the min/max shim returns the operand that is not NaN whichever operand the built-in favours', () => {
  const mix = (x, y, c) => (c ? y : x);
  const isnan = Number.isNaN;
  // The two rules a built-in may follow when an operand is NaN: SwiftShader's measured one returns the second
  // operand; SPIR-V leaves it undefined, so an optimizer that swaps the operands returns the first.
  const rules = {
    second: (f) => (a, b) => (Number.isNaN(a) || Number.isNaN(b) ? b : f(a, b)),
    first: (f) => (a, b) => (Number.isNaN(a) || Number.isNaN(b) ? a : f(a, b)),
  };
  for (const fn of ['min', 'max']) {
    const body = shimBody(fn);
    for (const [rule, wrap] of Object.entries(rules)) {
      const builtin = wrap(Math[fn]);
      const shim = new Function('a', 'b', 'mix', 'isnan', fn, `return ${body};`);
      const run = (a, b) => shim(a, b, mix, isnan, builtin);
      assert.equal(run(0.5, NaN), 0.5, `${fn}(0.5, NaN) under the ${rule}-operand rule`);
      assert.equal(run(NaN, 0.5), 0.5, `${fn}(NaN, 0.5) under the ${rule}-operand rule`);
      assert.equal(run(0.25, 0.5), Math[fn](0.25, 0.5));
      assert.ok(Number.isNaN(run(NaN, NaN)));
    }
  }
  // Every float-family overload tests both operands.
  for (const l of R.PARITY_SHIMS.minmax.filter((x) => /^(float|vec\d) shaderlab_/.test(x))) {
    assert.ok(/isnan\(a\)/.test(l) && /isnan\(b\)/.test(l), l);
  }
});

// A rule of the real compiler, in miniature: tanh in a const initializer fails once tanh is a user function.
const TANH_CONST_RULE = (src, lines) => {
  if (!src.includes('#define tanh shaderlab_tanh')) return [];
  const at = lines.findIndex((l) => /^\s*const\s+float\s+\w+\s*=\s*tanh\(/.test(l));
  return at >= 0 ? [`ERROR: 0:${at + 1}: 'k' : global const initializers must be constant`] : [];
};
test('parity: a pass that only the tanh shim breaks keeps the min/max shim (level "minmax-only")', () => {
  assert.deepEqual(R.PARITY_LEVELS.map((l) => l.name), ['full', 'tanh-only', 'minmax-only', 'none']);
  const s = shaderOf(img('// PASS image\nconst float k = tanh(1.0);\nvoid mainImage(out vec4 o, in vec2 u) { o = vec4(k); }\n'));
  const { gl, toy } = makeToy(s, {}, { rejects: TANH_CONST_RULE });
  const c = toy.compile();
  assert.ok(c.ok && c.drawable, JSON.stringify(c.passes));
  assert.equal(c.passes[0].parity, 'minmax-only');
  assert.ok(c.warnings.some((w) => /parity level "minmax-only"/.test(w)));
  toy.render({ time: 0 });
  assert.ok(gl.program.frag.includes('#define min shaderlab_min') && !gl.program.frag.includes('shaderlab_tanh'));
});

test('iChannelTime: each channel\'s media clock -- iTime for music and video, 0 for everything else', () => {
  const inputs = [
    { channel: 0, type: 'musicstream', id: 'm', filepath: 'https://soundcloud.com/a/b', sampler: S() },
    { channel: 1, type: 'texture', id: 't', filepath: '/media/a/t.png', sampler: S() },
    { channel: 2, type: 'video', id: 'v', filepath: '/media/a/v.webm', sampler: S() },
    bufIn(3, 'A'),
  ];
  assert.deepEqual(R.channelTimes(inputs, 2.5), [2.5, 0, 2.5, 0]);
  assert.deepEqual(R.channelTimes([{ channel: 1, type: 'music' }, { channel: 2, type: 'mic' }, { channel: 3, type: 'keyboard' }], 7),
    [0, 7, 0, 0]);
  assert.deepEqual(R.channelTimes([], 3), [0, 0, 0, 0]);
  const s = shaderOf(img(MAIN('image'), inputs), pass('Buffer A', 'buffer', MAIN('A'), [], ID.A));
  const { gl, toy } = makeToy(s);
  toy.compile();
  toy.render({ time: 2.5, frame: 150 });
  const by = Object.fromEntries(gl.draws.map((d) => [d.tag, d]));
  assert.deepEqual(by.image.chtime, [2.5, 0, 2.5, 0]);
  assert.deepEqual(by.A.chtime, [0, 0, 0, 0]);
  assert.deepEqual(gl.violations, []);
});

test('iMouse: mouseUniform signs z by the button and w by the click frame, as Shadertoy\'s page does', () => {
  const same = (a, b) => assert.ok(a.length === b.length && a.every((v, i) => Object.is(v, b[i])), `${a} vs ${b}`);
  same(R.mouseUniform({}), [0, 0, 0, 0]);                         // never clicked: zeros (no -0)
  same(R.mouseUniform(), [0, 0, 0, 0]);
  const at = { x: 30, y: 40, clickX: 10, clickY: 20 };
  same(R.mouseUniform({ ...at, down: true, clicked: true }), [30, 40, 10, 20]);    // the frame of the click
  same(R.mouseUniform({ ...at, down: true, clicked: false }), [30, 40, 10, -20]);  // held
  same(R.mouseUniform({ ...at, down: false, clicked: false }), [30, 40, -10, -20]); // released
  same(R.mouseUniform({ ...at, clickX: -10, clickY: -20, down: true }), [30, 40, 10, -20]);   // magnitudes in, signs from the flags
  // The click lasts one frame.
  same(R.mouseAfterFrame([30, 40, 10, 20]), [30, 40, 10, -20]);
  same(R.mouseAfterFrame([30, 40, -10, -20]), [30, 40, -10, -20]);
  same(R.mouseAfterFrame([0, 0, 0, 0]), [0, 0, 0, 0]);
});

test('runtime: a click reaches one frame -- render continues with w < 0; advance clicks the first walked frame only', () => {
  const click = { x: 30, y: 40, clickX: 10, clickY: 20, down: true, clicked: true };
  const { gl, toy } = makeToy(shaderOf(img(MAIN('image'))));
  toy.compile();
  toy.render({ time: 0, frame: 0, mouse: click });
  toy.render({});
  assert.deepEqual(gl.draws.map((d) => d.mouse), [[30, 40, 10, 20], [30, 40, 10, -20]]);
  toy.render({ mouse: [1, 2, 3, 4] });   // a raw vec4 is used as given, once
  toy.render({});
  assert.deepEqual(gl.draws.slice(2).map((d) => d.mouse), [[1, 2, 3, 4], [1, 2, 3, -4]]);

  const walk = makeToy(shaderOf(img(MAIN('image'))));
  walk.toy.compile();
  walk.toy.advance(0.1, { fps: 30, mouse: click });
  const ws = walk.gl.draws.map((d) => d.mouse);
  assert.equal(ws.length, 4);
  assert.deepEqual(ws[0], [30, 40, 10, 20]);
  assert.ok(ws.slice(1).every((m) => m[2] === 10 && m[3] === -20), JSON.stringify(ws));
  // A jump is the walk's last frame, so its click is gone unless the walk is one frame long.
  const j = makeToy(shaderOf(img(MAIN('image'))));
  j.toy.compile();
  j.toy.jump(0.1, { fps: 30, mouse: click });
  j.toy.jump(0, { fps: 30, mouse: click });
  assert.deepEqual(j.gl.draws.map((d) => d.mouse), [ws[3], [30, 40, 10, 20]]);
  walk.toy.reset();
  walk.toy.render({});
  assert.deepEqual(walk.gl.draws.pop().mouse, [0, 0, 0, 0], 'reset forgets the mouse');
});

test('iFrameRate: a walk and a jump report their nominal rate, also on a final partial step', () => {
  const { gl, toy } = makeToy(shaderOf(img(MAIN('image'))));
  toy.compile();
  toy.advance(1.55, { fps: 30 });
  assert.ok(gl.draws.every((d) => d.frameRate === 30), JSON.stringify([...new Set(gl.draws.map((d) => d.frameRate))]));
  const last = gl.draws[gl.draws.length - 1];
  assert.ok(Math.abs(last.timeDelta - (1.55 - 46 / 30)) < 1e-6, 'the partial step keeps its own iTimeDelta');
  const j = makeToy(shaderOf(img(MAIN('image'))));
  j.toy.compile();
  j.toy.jump(1.55, { fps: 30 });
  assert.equal(j.gl.draws[0].frameRate, 30);
});

test('runtime: resize keeps each buffer\'s contents (copied texel for texel, both halves) and resets its ping-pong index', () => {
  const { gl, toy } = makeToy(graphShader());
  toy.compile();
  for (let f = 0; f < 3; f++) toy.render({ time: f / 60, frame: f });
  const aWrites = gl.draws.filter((d) => d.tag === 'A').map((d) => d.write);
  const [half0, half1] = [aWrites[1], aWrites[0]];   // frame 0 writes half 1, frame 1 half 0, frame 2 half 1 again
  assert.equal(aWrites[2], half1);
  const tex = (id) => gl.textures.find((t) => t.id === id);
  assert.deepEqual([tex(half0).content, tex(half1).content], ['A@1', 'A@2']);
  gl.blits.length = 0;
  toy.resize(40, 20);   // smaller than 64 x 36
  assert.deepEqual(gl.violations, []);
  const aBlits = gl.blits.filter((b) => b.from === half0 || b.from === half1);
  assert.equal(aBlits.length, 2, 'both halves of Buffer A are copied');
  assert.ok(aBlits.every((b) => b.src.join() === '0,0,40,20' && b.dst.join() === '0,0,40,20'), JSON.stringify(aBlits));
  assert.equal(gl.blits.length, 8, 'four buffers, two halves each');
  toy.render({ time: 3 / 60, frame: 3 });
  const f3 = Object.fromEntries(gl.draws.slice(-5).map((d) => [d.tag, d]));
  // Shadertoy resets the index to half 0 after a resize, so the next frame reads the copy of the OLD half 0.
  assert.equal(f3.A.readContent[1], 'A@1', 'A reads the copy of its old half 0');
  assert.deepEqual(f3.A.res, [40, 20, 1]);
  assert.ok(tex(half0).deleted && tex(half1).deleted, 'the old targets are freed');
  // Growing copies only the old size; the rest of the new target starts clear.
  gl.blits.length = 0;
  toy.resize(100, 50);
  assert.equal(gl.blits.length, 8);
  assert.ok(gl.blits.every((b) => b.src.join() === '0,0,40,20'));
  // The same size again changes nothing: no new targets, no copies, the index kept.
  toy.render({ time: 4 / 60, frame: 4 });   // reads the copied half 0, writes half 1
  const n = gl.textures.length;
  gl.blits.length = 0;
  toy.resize(100, 50);
  assert.equal(gl.textures.length, n);
  assert.equal(gl.blits.length, 0);
  toy.render({ time: 5 / 60, frame: 5 });
  assert.equal(gl.draws.filter((d) => d.tag === 'A').pop().readContent[1], 'A@4');
  assert.deepEqual(gl.violations, []);
});

test('cubemap media: a flipped cubemap uploads its _3 image as +Y and its _2 image as -Y (Shadertoy\'s rule)', async () => {
  assert.deepEqual(R.cubemapUploadOrder(false), [0, 1, 2, 3, 4, 5]);
  assert.deepEqual(R.cubemapUploadOrder(true), [0, 1, 3, 2, 4, 5]);
  const saved = globalThis.Image;
  globalThis.Image = FakeImage;
  try {
    for (const f of R.cubemapFacePaths('/fl/box.png')) FakeImage.sizes.set(`u:${f}`, [16, 16]);
    const s = shaderOf(img(MAIN('image'), [{ channel: 0, type: 'cubemap', id: 'c', filepath: '/fl/box.png', sampler: S('linear', 'clamp', 'true') }]));
    const { gl, toy } = makeToy(s, { mediaUrl: (src) => `u:${src}` });
    await toy.ready;
    const faces = gl.uploads.filter((u) => u.image && u.target >= GL.TEXTURE_CUBE_MAP_POSITIVE_X && u.target < GL.TEXTURE_CUBE_MAP_POSITIVE_X + 6);
    const byFace = Object.fromEntries(faces.map((u) => [u.target - GL.TEXTURE_CUBE_MAP_POSITIVE_X, u.source.src]));
    assert.equal(byFace[2], 'u:/fl/box_3.png', '+Y');
    assert.equal(byFace[3], 'u:/fl/box_2.png', '-Y');
    assert.equal(byFace[0], 'u:/fl/box.png');
    assert.ok(faces.length === 6 && faces.every((u) => u.flipY === true));
  } finally {
    globalThis.Image = saved;
  }
});

test('volume media: a loaded volume always gets its mip chain, whichever input reads it first', async () => {
  const savedFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true, status: 200, arrayBuffer: async () => volumeBin({ w: 8, h: 8, d: 8, ch: 1 }) });
  try {
    const s = shaderOf(img(MAIN('image'), [
      { channel: 0, type: 'volume', id: 'v', filepath: '/media/a/grey.bin', sampler: S('linear', 'repeat') },
      { channel: 1, type: 'volume', id: 'v', filepath: '/media/a/grey.bin', sampler: S('mipmap', 'repeat') },
    ]));
    const { gl, toy } = makeToy(s, { mediaUrl: (src) => `x:${src}` });
    await toy.ready;
    const up = gl.uploads.find((u) => u.fn === 'texImage3D' && u.w === 8);
    assert.ok(gl.textures.find((t) => t.id === up.tex).mips >= 1, 'the loaded volume has mipmaps');
    toy.compile();
    toy.render({ time: 0 });
    assert.deepEqual(gl.violations, []);
  } finally {
    globalThis.fetch = savedFetch;
  }
});

test('two inputs on one channel: the header and the binding both take the last one', () => {
  const inputs = [
    { channel: 0, type: 'texture', id: 't', filepath: '/media/a/t.png', sampler: S() },
    { channel: 0, type: 'cubemap', id: 'c', filepath: '/media/a/c.png', sampler: S() },
  ];
  assert.ok(R.buildHeader('image', inputs).includes('uniform samplerCube iChannel0;'));
  const { gl, toy } = makeToy(shaderOf(img(MAIN('image'), inputs)));
  const c = toy.compile();
  assert.ok(c.warnings.some((w) => /two inputs on channel 0; the last one wins/.test(w)));
  toy.render({ time: 0 });
  assert.deepEqual(gl.violations, []);
});

test('renderer rule: the page judges the renderer string exactly as the headless driver does', async () => {
  const H = await import('../arsenal/shaders/headless.mjs');
  const strings = [
    'ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)',
    'ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (LLVM 10.0.0) (0x0000C0DE)), SwiftShader driver)',
    'Google SwiftShader',
    'ANGLE (AMD, AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)',
    'SwiftShader, but on an AMD Radeon', 'ANGLE (Google, SwiftShader via Direct3D11)', 'WebKit WebGL', '', '   ', null,
  ];
  for (const s of strings) assert.deepEqual(R.judgeRenderer(s), H.judgeRenderer(s), String(s));
  assert.equal(R.HARDWARE_HINT.source, H.HARDWARE_HINT.source);
  const mixed = new FakeGL({ renderer: 'ANGLE (Google, SwiftShader via Direct3D11)' });
  const info = R.rendererInfo(mixed);
  assert.equal(info.swiftshader, false, 'a string that names hardware is not the CPU rasteriser');
  assert.match(info.judged.reason, /names hardware/);
  assert.equal(R.rendererInfo(new FakeGL()).swiftshader, true);
});

test('vertex shader: precision highp float is declared (the floor says always)', () => {
  const { gl, toy } = makeToy(shaderOf(img(MAIN('image'))));
  toy.compile();
  const vs = gl.sources.find((x) => x.type === GL.VERTEX_SHADER);
  assert.equal(vs.source.split('\n')[0], '#version 300 es');
  assert.ok(vs.source.includes('precision highp float;'));
});

test('compile is all or nothing: a failed recompile of one pass leaves every pass on its old program', () => {
  const s = shaderOf(img(MAIN('image'), [bufIn(0, 'A')]), pass('Buffer A', 'buffer', MAIN('A'), [], ID.A));
  const { gl, toy } = makeToy(s);
  assert.ok(toy.compile().ok);
  s.renderpass[1].code = MAIN('A2');                            // Buffer A would link
  s.renderpass[0].code = '// PASS image2\nSYNTAX_ERROR_HERE';   // Image would not
  const c = toy.compile();
  assert.equal(c.drawable, false);
  toy.render({ time: 0 });
  assert.deepEqual(gl.draws.map((d) => d.tag), ['A', 'image'], 'no mix of a new Buffer A with the old Image');
  assert.deepEqual(gl.violations, []);
  s.renderpass[0].code = MAIN('image2');
  assert.ok(toy.compile().ok);
  toy.render({});
  assert.deepEqual(gl.draws.slice(-2).map((d) => d.tag), ['A2', 'image2']);
});
