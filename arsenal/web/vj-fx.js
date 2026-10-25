// VJ transitions and post look: arsenal/web/vj-fx.js (ES module, WebGL2; no DOM). The page (vj.js) owns the frame; this
// module owns two extra passes and their targets, and leaves the default framebuffer bound when it is done.
//
//   TRANSITION  mixes the live set and the cued set into one picture while a switch plays, in one of four styles
//               (vj-show.js TRANSITIONS): 0 crossfade, 1 radial wipe (an iris with a lit rim), 2 glitch cut (blocks flip
//               to the new set one by one, each exactly once, torn and colour-split while they flip), 3 zoom-through
//               (fly into the old set and out of the new one, with a radial motion blur). Every style is monotonic in
//               the picture it shows: no block or ring flips back, so a transition cannot flicker between the two sets.
//   POST        the look, over the composite: a two-level bloom (a bright pass at a quarter of the frame, a wide glow at
//               a sixteenth), a gentle vignette, film grain, and a touch of chromatic aberration on hits. All of it scales
//               with one master amount (vj-show.js lookParams). The glow's mean contribution to the frame is measured
//               every frame (the wide level's top mip IS its mean) and capped, so the look can never add a flash.
//               Grain is zero-mean (a difference of two hashes). The page skips the pass entirely when the look is off.

const VERT = `#version 300 es
precision highp float;
out vec2 v_uv;
void main() {
  vec2 pos[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
  vec2 p = pos[gl_VertexID];
  v_uv = (p + 1.0) * 0.5;
  gl_Position = vec4(p, 0.0, 1.0);
}`;

const TRANSITION_FS = `#version 300 es
precision highp float;
uniform sampler2D u_a, u_b;
uniform vec2 u_res;
uniform float u_p;        // progress 0..1
uniform int u_style;
uniform float u_seed;
uniform float u_t;        // seconds, for the glitch's tearing
uniform vec3 u_edge;      // the iris rim's colour (linear)
in vec2 v_uv;
out vec4 outColor;
const float PI = 3.14159265358979;
float h12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec2 mirrorUv(vec2 uv) { return 1.0 - abs(1.0 - mod(uv, 2.0)); }
vec3 A(vec2 uv) { return texture(u_a, mirrorUv(uv)).rgb; }
vec3 B(vec2 uv) { return texture(u_b, mirrorUv(uv)).rgb; }
vec3 toLin(vec3 c) { return pow(max(c, vec3(0.0)), vec3(2.2)); }
vec3 toDisp(vec3 c) { return pow(max(c, vec3(0.0)), vec3(1.0 / 2.2)); }
void main() {
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 uv = v_uv;
  vec2 p = (uv - 0.5) * vec2(asp, 1.0);
  float pr = clamp(u_p, 0.0, 1.0);
  float e = pr * pr * (3.0 - 2.0 * pr);
  vec3 c;
  if (u_style == 1) {
    // radial wipe: an iris opens from the centre; its edge wobbles a little while it moves and carries a thin lit rim
    float maxR = 0.5 * length(vec2(asp, 1.0)) + 0.06;
    float ang = atan(p.y, p.x + 1e-9);
    float wob = (0.020 * sin(ang * 7.0 + u_t * 2.3) + 0.012 * sin(ang * 13.0 - u_t * 3.1)) * sin(PI * e);
    float edgeR = e * (maxR + 0.06) - 0.03 + wob;
    float r = length(p);
    float m = 1.0 - smoothstep(edgeR - 0.010, edgeR + 0.010, r);
    vec3 lin = mix(toLin(A(uv)), toLin(B(uv)), m);
    float rim = exp(-pow((r - edgeR) / 0.005, 2.0)) * sin(PI * pr);
    lin += u_edge * rim * 0.45;
    c = toDisp(lin);
  } else if (u_style == 2) {
    // glitch cut: blocks (two sizes) flip from A to B, each at its own moment and only once
    vec2 cells = vec2(floor(16.0 * asp / 1.7778 + 0.5), 9.0);
    vec2 cid = floor(uv * cells);
    vec2 bid = floor(uv * cells * 0.5);
    float thr = 0.06 + 0.80 * mix(h12(cid + u_seed * 7.31), h12(bid * 1.7 + u_seed), 0.45);
    float flipped = step(thr, pr);
    float near = 1.0 - smoothstep(0.0, 0.07, abs(pr - thr));      // this block is mid-flip
    float tick = floor(u_t * 18.0);
    float row = h12(vec2(floor(uv.y * 90.0), tick + u_seed * 3.0));
    float tear = step(0.93, row) * sin(PI * pr);
    vec2 off = vec2((h12(cid * 1.3 + tick) - 0.5) * 0.07 * near + (row - 0.965) * 0.6 * tear, 0.0);
    vec2 q = uv + off;
    float split = 0.007 * max(near, tear);
    vec3 a = vec3(A(q + vec2(split, 0.0)).r, A(q).g, A(q - vec2(split, 0.0)).b);
    vec3 b = vec3(B(q + vec2(split, 0.0)).r, B(q).g, B(q - vec2(split, 0.0)).b);
    c = mix(a, b, flipped);
  } else if (u_style == 3) {
    // zoom-through: both pictures grow toward the eye; the old one rushes past, the new one arrives from the distance
    float zA = 1.0 + 3.0 * e * e;
    float zB = 1.0 + 2.0 * (1.0 - e) * (1.0 - e);
    float blur = 0.06 * sin(PI * pr);
    vec2 d = uv - 0.5;
    vec3 la = vec3(0.0), lb = vec3(0.0);
    for (int i = 0; i < 5; i++) {
      float k = 1.0 - blur * float(i) / 4.0;
      la += toLin(A(0.5 + d / zA * k));
      lb += toLin(B(0.5 + d * zB * k));
    }
    float w = smoothstep(0.30, 0.75, pr);
    c = toDisp(mix(la, lb, w) / 5.0);
  } else {
    c = mix(A(uv), B(uv), e);
  }
  outColor = vec4(clamp(c, 0.0, 1.0), 1.0);
}`;

// the bright pass, at a quarter of the frame: four bilinear taps cover a 4x4 block; display values to linear light
const PREFILTER_FS = `#version 300 es
precision highp float;
uniform sampler2D u_src;
uniform vec2 u_srcTexel;
in vec2 v_uv;
out vec4 outColor;
void main() {
  vec3 s = vec3(0.0);
  s += texture(u_src, v_uv + u_srcTexel * vec2(-1.0, -1.0)).rgb;
  s += texture(u_src, v_uv + u_srcTexel * vec2(1.0, -1.0)).rgb;
  s += texture(u_src, v_uv + u_srcTexel * vec2(-1.0, 1.0)).rgb;
  s += texture(u_src, v_uv + u_srcTexel * vec2(1.0, 1.0)).rgb;
  vec3 lin = pow(max(s * 0.25, vec3(0.0)), vec3(2.2));
  float l = dot(lin, vec3(0.2126, 0.7152, 0.0722));
  outColor = vec4(lin * smoothstep(0.12, 0.55, l), 1.0);
}`;

// a separable gaussian (nine taps through five bilinear reads)
const BLUR_FS = `#version 300 es
precision highp float;
uniform sampler2D u_src;
uniform vec2 u_dir;       // one texel along the blur, times the spread
in vec2 v_uv;
out vec4 outColor;
void main() {
  vec3 s = texture(u_src, v_uv).rgb * 0.2270270270;
  s += texture(u_src, v_uv + u_dir * 1.3846153846).rgb * 0.3162162162;
  s += texture(u_src, v_uv - u_dir * 1.3846153846).rgb * 0.3162162162;
  s += texture(u_src, v_uv + u_dir * 3.2307692308).rgb * 0.0702702703;
  s += texture(u_src, v_uv - u_dir * 3.2307692308).rgb * 0.0702702703;
  outColor = vec4(s, 1.0);
}`;

const DOWN_FS = `#version 300 es
precision highp float;
uniform sampler2D u_src;
uniform vec2 u_srcTexel;
in vec2 v_uv;
out vec4 outColor;
void main() {
  vec3 s = texture(u_src, v_uv + u_srcTexel * vec2(-1.0, -1.0)).rgb + texture(u_src, v_uv + u_srcTexel * vec2(1.0, -1.0)).rgb +
           texture(u_src, v_uv + u_srcTexel * vec2(-1.0, 1.0)).rgb + texture(u_src, v_uv + u_srcTexel * vec2(1.0, 1.0)).rgb;
  outColor = vec4(s * 0.25, 1.0);
}`;

const POST_FS = `#version 300 es
precision highp float;
uniform sampler2D u_src;      // the composite (display values)
uniform sampler2D u_b1;       // the tight glow (linear)
uniform sampler2D u_b2;       // the wide glow (linear), mipmapped: its top level is its mean
uniform vec2 u_res;
uniform float u_bloom, u_bloomCap, u_vignette, u_grain, u_ca;
uniform float u_seed;
in vec2 v_uv;
out vec4 outColor;
float h12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
void main() {
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 uv = v_uv;
  vec2 d = uv - 0.5;
  // chromatic aberration: red pulled in, blue pushed out, growing toward the corners
  vec3 c;
  if (u_ca > 1e-5) {
    vec2 o = d * u_ca * 2.0;
    c = vec3(texture(u_src, uv - o).r, texture(u_src, uv).g, texture(u_src, uv + o).b);
  } else c = texture(u_src, uv).rgb;
  vec3 lin = pow(max(c, vec3(0.0)), vec3(2.2));
  // the glow, its mean contribution capped
  vec3 glow = textureLod(u_b1, uv, 0.0).rgb * 0.55 + textureLod(u_b2, uv, 0.0).rgb * 0.45;
  vec3 mean = textureLod(u_b2, vec2(0.5), 16.0).rgb;
  float added = dot(mean, vec3(0.2126, 0.7152, 0.0722)) * u_bloom;
  float k = added > u_bloomCap ? u_bloomCap / added : 1.0;
  lin += glow * u_bloom * k;
  // the vignette: an ellipse fitted to the frame (1 at the corners), darkening only the outer part
  float rr = length(d) * 1.41421;
  lin *= 1.0 - u_vignette * smoothstep(0.45, 1.05, rr);
  c = pow(max(lin, vec3(0.0)), vec3(1.0 / 2.2));
  // grain: zero-mean (a difference of two hashes), strongest in the mid-tones, new every frame
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  float n = h12(gl_FragCoord.xy + u_seed) - h12(gl_FragCoord.xy * 1.37 + u_seed * 1.91 + 17.0);
  c += n * u_grain * (0.3 + 2.8 * l * (1.0 - l));
  c += (h12(gl_FragCoord.xy * 0.731 + u_seed * 0.37) - 0.5) / 255.0;   // a dither at the 8-bit step
  if (any(isnan(c)) || any(isinf(c))) c = vec3(0.0);
  outColor = vec4(clamp(c, 0.0, 1.0), 1.0);
}`;

function compile(gl, type, src) {
  const sh = gl.createShader(type);
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(sh) || "compile error";
    gl.deleteShader(sh);
    throw new Error(log);
  }
  return sh;
}
function link(gl, fs, names) {
  const v = compile(gl, gl.VERTEX_SHADER, VERT);
  let f;
  try { f = compile(gl, gl.FRAGMENT_SHADER, fs); } catch (err) { gl.deleteShader(v); throw err; }
  const prog = gl.createProgram();
  gl.attachShader(prog, v); gl.attachShader(prog, f);
  gl.linkProgram(prog);
  gl.deleteShader(v); gl.deleteShader(f);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(prog) || "link error";
    gl.deleteProgram(prog);
    throw new Error(log);
  }
  const u = {};
  for (const n of names) u[n] = gl.getUniformLocation(prog, n);
  return { prog, u };
}

// One render target: a texture and its framebuffer. mip: allocate a mip chain (generateMipmap after each render).
function target(gl, w, h, internal, type, mip = false) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mip ? gl.LINEAR_MIPMAP_LINEAR : gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texImage2D(gl.TEXTURE_2D, 0, internal, w, h, 0, gl.RGBA, type, null);
  if (mip) gl.generateMipmap(gl.TEXTURE_2D);
  const fbo = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  return { tex, fbo, w, h, ok, mip };
}
function drop(gl, t) { if (t) { gl.deleteTexture(t.tex); gl.deleteFramebuffer(t.fbo); } }

// createVjFx(gl, { internalFormat, type }): the page's framebuffer format (RGBA16F/HALF_FLOAT, or RGBA8/UNSIGNED_BYTE).
// Throws when a shader does not compile (the page then keeps its plain crossfade and no look).
export function createVjFx(gl, { internalFormat, type }) {
  const tr = link(gl, TRANSITION_FS, ["u_a", "u_b", "u_res", "u_p", "u_style", "u_seed", "u_t", "u_edge"]);
  const pre = link(gl, PREFILTER_FS, ["u_src", "u_srcTexel"]);
  const blur = link(gl, BLUR_FS, ["u_src", "u_dir"]);
  const down = link(gl, DOWN_FS, ["u_src", "u_srcTexel"]);
  const post = link(gl, POST_FS, ["u_src", "u_b1", "u_b2", "u_res", "u_bloom", "u_bloomCap", "u_vignette", "u_grain", "u_ca", "u_seed"]);
  const T = { w: 0, h: 0, mixT: null, comp: null, b1: null, b1b: null, b2: null, b2b: null, b2m: null };
  let frame = 0;

  function ensure(w, h) {
    if (T.w === w && T.h === h && T.mixT) return;
    for (const k of ["mixT", "comp", "b1", "b1b", "b2", "b2b", "b2m"]) { drop(gl, T[k]); T[k] = null; }
    T.w = w; T.h = h;
    T.mixT = target(gl, w, h, internalFormat, type);
    T.comp = target(gl, w, h, internalFormat, type);
    const w1 = Math.max(1, Math.ceil(w / 4)), h1 = Math.max(1, Math.ceil(h / 4));
    const w2 = Math.max(1, Math.ceil(w / 16)), h2 = Math.max(1, Math.ceil(h / 16));
    T.b1 = target(gl, w1, h1, internalFormat, type);
    T.b1b = target(gl, w1, h1, internalFormat, type);
    T.b2 = target(gl, w2, h2, internalFormat, type);
    T.b2b = target(gl, w2, h2, internalFormat, type);
    T.b2m = target(gl, w2, h2, internalFormat, type, true);
  }
  function draw(t) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, t ? t.fbo : null);
    gl.viewport(0, 0, t ? t.w : T.w, t ? t.h : T.h);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  function bind(unit, tex) { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex); }

  return {
    // Mix texA and texB into this module's target and return its texture. opts: { code, progress, seed, t, edge: [r,g,b] }
    transition(w, h, texA, texB, opts) {
      ensure(w, h);
      gl.useProgram(tr.prog);
      bind(0, texA); bind(1, texB);
      gl.uniform1i(tr.u.u_a, 0); gl.uniform1i(tr.u.u_b, 1);
      gl.uniform2f(tr.u.u_res, w, h);
      gl.uniform1f(tr.u.u_p, opts.progress);
      gl.uniform1i(tr.u.u_style, opts.code | 0);
      gl.uniform1f(tr.u.u_seed, opts.seed || 0);
      gl.uniform1f(tr.u.u_t, opts.t || 0);
      const e = opts.edge || [1, 1, 1];
      gl.uniform3f(tr.u.u_edge, e[0], e[1], e[2]);
      draw(T.mixT);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      return T.mixT.tex;
    },
    // The framebuffer the composite should draw into while the look is on.
    target(w, h) { ensure(w, h); return T.comp.fbo; },
    // The look: from the composite (`src`, or this module's composite target) to the screen, or into the framebuffer
    // `dst` (the flash limiter's input). p = vj-show.js lookParams(amount); hit 0..1.
    post(w, h, p, hit, src = null, dst = null) {
      ensure(w, h);
      const srcTex = src || T.comp.tex;
      frame = (frame + 1) % 65536;
      // the bright pass and the two glow levels
      gl.useProgram(pre.prog);
      bind(0, srcTex);
      gl.uniform1i(pre.u.u_src, 0);
      gl.uniform2f(pre.u.u_srcTexel, 1 / w, 1 / h);
      draw(T.b1);
      gl.useProgram(blur.prog);
      gl.uniform1i(blur.u.u_src, 0);
      bind(0, T.b1.tex); gl.uniform2f(blur.u.u_dir, 1.5 / T.b1.w, 0); draw(T.b1b);
      bind(0, T.b1b.tex); gl.uniform2f(blur.u.u_dir, 0, 1.5 / T.b1.h); draw(T.b1);
      gl.useProgram(down.prog);
      bind(0, T.b1.tex);
      gl.uniform1i(down.u.u_src, 0);
      gl.uniform2f(down.u.u_srcTexel, 1 / T.b1.w, 1 / T.b1.h);
      draw(T.b2);
      gl.useProgram(blur.prog);
      bind(0, T.b2.tex); gl.uniform2f(blur.u.u_dir, 1.5 / T.b2.w, 0); draw(T.b2b);
      bind(0, T.b2b.tex); gl.uniform2f(blur.u.u_dir, 0, 1.5 / T.b2.h); draw(T.b2m);
      bind(0, T.b2m.tex);
      gl.generateMipmap(gl.TEXTURE_2D);
      // the final pass, to the screen
      gl.useProgram(post.prog);
      bind(0, srcTex); bind(1, T.b1.tex); bind(2, T.b2m.tex);
      gl.uniform1i(post.u.u_src, 0); gl.uniform1i(post.u.u_b1, 1); gl.uniform1i(post.u.u_b2, 2);
      gl.uniform2f(post.u.u_res, w, h);
      gl.uniform1f(post.u.u_bloom, p.bloom);
      gl.uniform1f(post.u.u_bloomCap, p.bloomCap);
      gl.uniform1f(post.u.u_vignette, p.vignette);
      gl.uniform1f(post.u.u_grain, p.grain);
      gl.uniform1f(post.u.u_ca, p.aberration * Math.min(1, Math.max(0, hit)));
      gl.uniform1f(post.u.u_seed, (frame * 7.13) % 1024);
      gl.bindFramebuffer(gl.FRAMEBUFFER, dst);
      gl.viewport(0, 0, w, h);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.activeTexture(gl.TEXTURE0);
    },
    dispose() {
      for (const k of ["mixT", "comp", "b1", "b1b", "b2", "b2b", "b2m"]) { drop(gl, T[k]); T[k] = null; }
      for (const pr of [tr, pre, blur, down, post]) gl.deleteProgram(pr.prog);
      T.w = T.h = 0;
    },
    sizes() { return { w: T.w, h: T.h, b1: T.b1 && [T.b1.w, T.b1.h], b2: T.b2 && [T.b2.w, T.b2.h],
                       complete: !!(T.mixT && T.mixT.ok && T.comp.ok && T.b1.ok && T.b2m.ok) }; },
  };
}
