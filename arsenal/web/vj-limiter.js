// VJ gate v2 on the GPU: arsenal/web/vj-limiter.js (ES module, WebGL2; no DOM). The rules and their JS twin live in
// vj-gate.js (FlashLimiter); this module runs them on the frame the viewer is about to see, every frame:
//
//   METER   the final frame -> blocks of at most 16 x 16 pixels (EVERY pixel read, at any canvas size: a block grid sized
//           from the canvas, so nothing is skipped at 1280 x 720, 1080p or 4K) -> 8 x 8 cells (cell (cx, cy), signal s at
//           texel (2 cx + s, cy): the cell's four corner-hat sums of the sRGB-decoded relative luminance and the WCAG red
//           quantity, each pixel weighted by its place in its cell)
//   BAND    one fragment per tracker (750: 375 windows x luminance and red): its mode and limits this frame (vj-gate.js
//           FlashLimiter.band) and its window's drawn value
//   SOLVE   4 x 3 fragments, each running the projections over the held trackers' bands and the fallback blend (they all
//           compute the same thing) and writing 7 of the 81 corners (four targets); UNPACK lays them out as the 9 x 9 gain
//           texture (a, k, beta, limiting). (One solve per corner, 81 of them, made a storm frame 3x slower on SwiftShader.)
//   SHOWN   one fragment per tracker: its window through the gains and the blend, the value the viewer gets
//   STATE   (750 + 1) x 5 fragments: each tracker's five texels after this frame (its counter, its held band, its ring of
//           transition ends, which of them were full size, the end that may still move), and the shared texels (the
//           flashing run, the forced rest, the frame count, beta; the held and leak counts as they stood)
//   APPLY   the frame through the gains (linear light: a Y + k (1 - Y), smoothstep-bilinear between the corners, the same hats the
//           meter used) and, when beta > 0, blended toward the previous shown frame, into the SHOWN pair (RGBA8: exactly
//           what the canvas gets), then blitted to the canvas. With nothing held, every gain is exactly 1 and beta 0: the
//           pixel is copied untouched.
// THREE WAYS TO DECIDE (2026-10-25, the round-2 verifier: a page without its limiter was not flash-safe):
//   "gpu"   all eight programs linked: no readback, no stall.
//   "cpu"   the meter and the apply pass linked but the decision has not (it is still compiling in the background, or it
//           failed: the solve shader is large and had never been compiled on a real Windows GPU): the cell sums are read back
//           (2 KB, a stall per frame) and the JS twin decides (the same rules, vj-gate.js); its state moves to the GPU the
//           frame the decision links. ?limiter=cpu forces it (receipts).
//   none    the meter or the apply pass cannot run (no float target, a program that will not link): live() is false and
//           the page refuses every pad effect (vj.js: its safe mode, flash-safe by construction).
// The state and the gains are float textures (RGBA32F with EXT_color_buffer_float, else RGBA16F).

import { LIMIT, WINDOWS, NW, NWQ, NT, NTQ, NSIG, TRACKER_FLOATS, TRACKER_ROWS, NCELL_FLOATS, NCTRL, FlashLimiter } from "./vj-gate.js";

const VERT = `#version 300 es
precision highp float;
void main() {
  vec2 pos[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
  gl_Position = vec4(pos[gl_VertexID], 0.0, 1.0);
}`;

const f = (x) => { const s = String(+x); return /[.e]/.test(s) ? s : `${s}.0`; };
const v4 = (a) => `vec4(${a.map(f).join(", ")})`;
const BLOCK = 16;                          // the meter's block side: at most 16 x 16 pixels per first-pass texel
const GX = LIMIT.GX, GY = LIMIT.GY, CX = LIMIT.CX, CY = LIMIT.CY;
const SOLVE_W = 4, SOLVE_H = 3, PER = 7;   // the solve: 12 fragments, 7 corners each (4 targets: 7 x (a, k) + beta, limiting)
if (SOLVE_W * SOLVE_H * PER < NCTRL) throw new Error("the solve's fragments do not cover every corner");

// sRGB: the canvas's values are display-referred (the composite and the look write gamma-encoded values the screen shows)
const SRGB = `
float dec1(float c) { return c <= 0.04045 ? c / 12.92 : pow((c + 0.055) / 1.055, 2.4); }
vec3 dec3(vec3 c) { return vec3(dec1(c.r), dec1(c.g), dec1(c.b)); }
float enc1(float l) { return l <= 0.0031308 ? l * 12.92 : 1.055 * pow(l, 1.0 / 2.4) - 0.055; }
vec3 enc3(vec3 l) { return vec3(enc1(l.r), enc1(l.g), enc1(l.b)); }
// cell boundaries in pixels: B_c = floor(c n / G); a pixel belongs to the cell whose [B_c, B_c+1) holds it, and its hat
// weights come from its centre's place in that cell (the meter and the apply pass share these functions)
int boundX(int c, int n) { return (c * n) / ${GX}; }
int boundY(int c, int n) { return (c * n) / ${GY}; }
// (the last c with B_c <= p, in closed form: c = floor((G p + G - 1) / n); one division instead of seven a pixel)
int cellX(int p, int n) { return min(${GX - 1}, (${GX} * p + ${GX - 1}) / n); }
int cellY(int p, int n) { return min(${GY - 1}, (${GY} * p + ${GY - 1}) / n); }
`;

// METER 1: one texel per block; the block grid is SX x SY blocks per cell (uniform u_sub), so every pixel of the frame
// belongs to exactly one block, whatever the canvas size
const METER1_FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_src;
uniform ivec2 u_size;          // the frame, pixels
uniform ivec2 u_sub;           // blocks per cell, x and y
layout(location = 0) out vec4 o_lum;
layout(location = 1) out vec4 o_red;
${SRGB}
void main() {
  ivec2 t = ivec2(gl_FragCoord.xy);
  int cx = t.x / u_sub.x, cy = t.y / u_sub.y, lx = t.x - cx * u_sub.x, ly = t.y - cy * u_sub.y;
  int bx0 = boundX(cx, u_size.x), bx1 = boundX(cx + 1, u_size.x), by0 = boundY(cy, u_size.y), by1 = boundY(cy + 1, u_size.y);
  int cw = max(bx1 - bx0, 1), ch = max(by1 - by0, 1);
  int x0 = bx0 + (lx * cw) / u_sub.x, x1 = bx0 + ((lx + 1) * cw) / u_sub.x;
  int y0 = by0 + (ly * ch) / u_sub.y, y1 = by0 + ((ly + 1) * ch) / u_sub.y;
  vec4 L = vec4(0.0), R = vec4(0.0);
  for (int y = y0; y < y1; y++) for (int x = x0; x < x1; x++) {
    vec3 d = clamp(texelFetch(u_src, ivec2(x, y), 0).rgb, 0.0, 1.0);
    vec3 lin = dec3(d);
    float l = dot(lin, vec3(0.2126, 0.7152, 0.0722));
    float sum = d.r + d.g + d.b;
    // WCAG red: a saturated red pixel (R / (R + G + B) >= 0.8, display values), its quantity (R - G - B) x 320 in linear
    // light (stored / 320)
    float red = (sum > 0.0 && d.r >= 0.8 * sum) ? max(0.0, lin.r - lin.g - lin.b) : 0.0;
    float fx = (float(x - bx0) + 0.5) / float(cw), fy = (float(y - by0) + 0.5) / float(ch);
    // the corners' hats: smoothstep-weighted bilinear (a partition of unity, so still linear in the 81 gains, and smooth
    // across cells: a held region dims as a soft round patch, never a pyramid)
    float sx = fx * fx * (3.0 - 2.0 * fx), sy = fy * fy * (3.0 - 2.0 * fy);
    vec4 h = vec4((1.0 - sx) * (1.0 - sy), sx * (1.0 - sy), (1.0 - sx) * sy, sx * sy);
    L += h * l; R += h * red;
  }
  // this block's share of its cell's mean
  float inv = 1.0 / float(cw * ch);
  o_lum = L * inv; o_red = R * inv;
}`;

const METER2_FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_lum, u_red;
uniform ivec2 u_sub;           // blocks per cell
out vec4 outColor;
void main() {
  ivec2 p = ivec2(gl_FragCoord.xy);
  int cx = p.x >> 1, s = p.x & 1, cy = p.y;
  vec4 acc = vec4(0.0);
  for (int j = 0; j < u_sub.y; j++) for (int i = 0; i < u_sub.x; i++) {
    ivec2 q = ivec2(cx * u_sub.x + i, cy * u_sub.y + j);
    acc += s == 0 ? texelFetch(u_lum, q, 0) : texelFetch(u_red, q, 0);
  }
  outColor = acc;
}`;

// Shared by BAND, SOLVE and STATE: the constants, the window table (a texture: 375 rectangles), the window values.
const COMMON = `
const int NT = ${NT};
const int NTQ = ${NTQ};
const int NWQ = ${NWQ};
const int RING = ${LIMIT.RING};
const float NMAX = ${f(LIMIT.N_MAX)};
const float WINDOW_S = ${f(LIMIT.WINDOW_S)};
const float EMPTY_AGE = ${f(LIMIT.EMPTY_AGE)};
const float RUN_S = ${f(LIMIT.RUN_S)};
const float REST_S = ${f(LIMIT.REST_S)};
const int REST_COUNT = ${LIMIT.REST_COUNT};
const float K_MAX = ${f(LIMIT.K_MAX)};
// per kind q = signal + 2 x (a cell): quarter-window luminance, red, cell luminance, red
const vec4 TH4 = ${v4(LIMIT.TH)};
const vec4 HY4 = ${v4(LIMIT.HYST)};
const vec4 BAND4 = ${v4(LIMIT.BAND)};
const vec4 DRIFT4 = ${v4(LIMIT.DRIFT)};
const vec4 DRIFTD4 = ${v4(LIMIT.DRIFT_DOWN)};
const vec4 THREST4 = ${v4(LIMIT.TH_REST)};
const vec4 EXTN4 = ${v4(LIMIT.EXT_NEAR)};
const vec4 EXTC4 = ${v4(LIMIT.EXT_CLOSE)};
const float BIG = 1.0e9;
uniform highp usampler2D u_win;
uniform sampler2D u_cells, u_state;
uniform float u_dt;
// loop counts as uniforms (trackers, sweeps): a shader compiler that unrolls loops of constant length (Direct3D's fxc,
// behind ANGLE on Windows) keeps these as loops instead of pasting the solve out thousands of times
uniform int u_nt, u_ntq;
ivec4 win(int w) { return ivec4(texelFetch(u_win, ivec2(w, 0), 0)); }
int kindOf(int t) { return (t & 1) + ((t >> 1) >= NWQ ? 2 : 0); }
float pick(vec4 v, int q) { return q == 0 ? v.x : q == 1 ? v.y : q == 2 ? v.z : v.w; }
float pickJ(vec4 v, int j) { return j == 0 ? v.x : j == 1 ? v.y : j == 2 ? v.z : v.w; }
vec4 cellAt(int cx, int cy, int s) { return texelFetch(u_cells, ivec2(cx * ${NSIG} + s, cy), 0); }
float winWant(ivec4 r, int s) {
  float sum = 0.0;
  for (int cy = r.y; cy <= r.w; cy++) for (int cx = r.x; cx <= r.z; cx++) { vec4 S = cellAt(cx, cy, s); sum += S.x + S.y + S.z + S.w; }
  return sum / float((r.z - r.x + 1) * (r.w - r.y + 1));
}
float countRing(vec4 r2, vec4 r3) {
  float n = 0.0;
  n += r2.x + u_dt < WINDOW_S ? 1.0 : 0.0; n += r2.y + u_dt < WINDOW_S ? 1.0 : 0.0;
  n += r2.z + u_dt < WINDOW_S ? 1.0 : 0.0; n += r2.w + u_dt < WINDOW_S ? 1.0 : 0.0;
  n += r3.x + u_dt < WINDOW_S ? 1.0 : 0.0; n += r3.y + u_dt < WINDOW_S ? 1.0 : 0.0;
  n += r3.z + u_dt < WINDOW_S ? 1.0 : 0.0;
  return n;
}
`;

// BAND: a line-by-line port of vj-gate.js FlashLimiter.band, one fragment per tracker, two targets: (lo, hi, hlo, hhi)
// and (pin, level, held, want).
const BAND_FS = `#version 300 es
precision highp float;
precision highp int;
layout(location = 0) out vec4 o_lim;
layout(location = 1) out vec4 o_pin;
${COMMON}
void main() {
  int t = int(gl_FragCoord.x), s = t & 1, w = t >> 1, q = kindOf(t);
  vec4 r0 = texelFetch(u_state, ivec2(t, 0), 0), r1 = texelFetch(u_state, ivec2(t, 1), 0);
  vec4 r2 = texelFetch(u_state, ivec2(t, 2), 0), r3 = texelFetch(u_state, ivec2(t, 3), 0);
  float th = pick(TH4, q), bw = pick(BAND4, q), dr = pick(DRIFT4, q), drd = pick(DRIFTD4, q);
  float want = winWant(win(w), s);
  float dir = r0.x, X = r0.y, C = r0.z, sPrev = r0.w, open = r1.x, level = r1.y;
  float lo = -BIG, hi = BIG, hlo = -BIG, hhi = BIG, pin = r1.z, lv = 0.0;
  bool held = false;
  if (dir != 0.0) {
    float eps = s == 0 ? 1.0e-4 : 2.0e-5;
    float rest = texelFetch(u_state, ivec2(NT, 0), 0).y;
    float budget = rest > 0.0 ? 0.0 : NMAX;
    float n = countRing(r2, r3);
    if (n + 2.0 > budget) {                  // no room for a rise and its fall: held
      bool fallOK = n + 1.0 <= budget;
      float ncLo, ncHi;
      if (dir > 0.0) { ncLo = C - th; ncHi = open >= 0.0 ? BIG : X + th; }
      else { ncLo = open >= 0.0 ? -BIG : X - th; ncHi = C + th; }
      held = true;
      lv = fallOK ? 1.0 : 2.0;
      if (level < lv - 0.5 || sPrev < pin - 1.0e-5 || sPrev > pin + bw + 1.0e-5) pin = sPrev - 0.5 * bw;
      float top = pin + bw;
      if (want > top) pin += min(dr * u_dt, want - top);
      else if (want < pin) pin -= min(drd * u_dt, pin - want);
      bool runOnDown = dir < 0.0 && open >= 0.0, runOnUp = dir > 0.0 && open >= 0.0;
      if (fallOK) {                          // PARTIAL: one transition left, kept for a fall
        if (pin + bw > ncHi) pin = ncHi - bw;
        hhi = ncHi - eps;
        hi = runOnUp ? hhi : min(pin + bw, hhi);
      } else {                               // FULL: nothing may start; an open committed transition may run on
        if (pin < ncLo) pin = ncLo;
        if (pin + bw > ncHi) pin = ncHi - bw;
        hlo = ncLo + eps; hhi = ncHi - eps;
        lo = runOnDown ? hlo : max(pin, hlo);
        hi = runOnUp ? hhi : min(pin + bw, hhi);
        if (lo > hi) { float v = min(max(sPrev, hlo), hhi); lo = v; hi = v; }
      }
    }
  }
  o_lim = vec4(lo, hi, hlo, hhi);
  o_pin = vec4(pin, lv, held ? 1.0 : 0.0, want);
}`;

// SOLVE: FlashLimiter.project / solve. SOLVE_W x SOLVE_H fragments, each running the whole solve (they agree exactly)
// and writing PER corners' (a, k) and, last, (beta, limiting) into four targets; UNPACK lays them out as the 9 x 9 gain
// texture. (Twelve solves where one per corner took 81: on SwiftShader the solve is most of the limiter's cost.)
const SOLVE_FS = `#version 300 es
precision highp float;
precision highp int;
layout(location = 0) out vec4 o_0;
layout(location = 1) out vec4 o_1;
layout(location = 2) out vec4 o_2;
layout(location = 3) out vec4 o_3;
${COMMON}
uniform sampler2D u_lim, u_pin;
uniform int u_sweeps, u_hard, u_nc;
float CELL[${NCELL_FLOATS}];
float A[${NCTRL}];
float K[${NCTRL}];
float GA[${NCTRL}];
float GK[${NCTRL}];
int HELD[${NT}];
float winVal(ivec4 r, int s) {
  float sum = 0.0;
  for (int cy = r.y; cy <= r.w; cy++) for (int cx = r.x; cx <= r.z; cx++) {
    int b = ((cy * ${GX} + cx) * ${NSIG} + s) * 4, i0 = cy * ${CX} + cx;
    float S0 = CELL[b], S1 = CELL[b + 1], S2 = CELL[b + 2], S3 = CELL[b + 3];
    sum += A[i0] * S0 + A[i0 + 1] * S1 + A[i0 + ${CX}] * S2 + A[i0 + ${CX + 1}] * S3;
    if (s == 0) sum += K[i0] * (0.25 - S0) + K[i0 + 1] * (0.25 - S1) + K[i0 + ${CX}] * (0.25 - S2) + K[i0 + ${CX + 1}] * (0.25 - S3);
  }
  return sum / float((r.z - r.x + 1) * (r.w - r.y + 1));
}
void project(int t, float lo, float hi) {
  int s = t & 1;
  ivec4 r = win(t >> 1);
  float v = winVal(r, s);
  if (v <= hi + 1.0e-6 && v >= lo - 1.0e-6) return;
  bool down = v > hi;
  float margin = min(s == 0 ? 0.002 : 0.0006, 0.1 * (hi - lo));
  float target = down ? hi - margin : lo + margin;
  float inv = 1.0 / float((r.z - r.x + 1) * (r.w - r.y + 1));
  for (int Y = r.y; Y <= r.w + 1; Y++) for (int X = r.x; X <= r.z + 1; X++) { GA[Y * ${CX} + X] = 0.0; GK[Y * ${CX} + X] = 0.0; }
  for (int cy = r.y; cy <= r.w; cy++) for (int cx = r.x; cx <= r.z; cx++) {
    int b = ((cy * ${GX} + cx) * ${NSIG} + s) * 4;
    for (int j = 0; j < 4; j++) {
      float Sv = CELL[b + j];
      int i = (cy + (j >> 1)) * ${CX} + cx + (j & 1);
      GA[i] += Sv * inv;
      if (s == 0) GK[i] += (0.25 - Sv) * inv;
    }
  }
  float norm = 0.0;
  for (int Y = r.y; Y <= r.w + 1; Y++) for (int X = r.x; X <= r.z + 1; X++) {
    int i = Y * ${CX} + X;
    if (down ? A[i] <= 0.0 : A[i] >= 1.0) GA[i] = 0.0;
    if (s != 0 || (down ? K[i] <= 0.0 : K[i] >= K_MAX)) GK[i] = 0.0;
    norm += GA[i] * GA[i] + GK[i] * GK[i];
  }
  if (norm < 1.0e-12) return;
  float d = (target - v) / norm;
  for (int Y = r.y; Y <= r.w + 1; Y++) for (int X = r.x; X <= r.z + 1; X++) {
    int i = Y * ${CX} + X;
    A[i] = clamp(A[i] + d * GA[i], 0.0, 1.0);
    K[i] = clamp(K[i] + d * GK[i], 0.0, K_MAX);
  }
}
void main() {
  ivec2 p = ivec2(gl_FragCoord.xy);
  for (int cy = 0; cy < ${GY}; cy++) for (int cx = 0; cx < ${GX * NSIG}; cx++) {
    vec4 v = texelFetch(u_cells, ivec2(cx, cy), 0);
    int b = (cy * ${GX * NSIG} + cx) * 4;
    CELL[b] = v.x; CELL[b + 1] = v.y; CELL[b + 2] = v.z; CELL[b + 3] = v.w;
  }
  int nh = 0;
  for (int t = 0; t < u_nt; t++) if (texelFetch(u_pin, ivec2(t, 0), 0).z > 0.5) { HELD[nh] = t; nh++; }
  for (int i = 0; i < u_nc; i++) { A[i] = 1.0; K[i] = 0.0; }
  for (int sweep = 0; sweep < u_sweeps; sweep++) for (int h = 0; h < nh; h++) {
    vec4 b = texelFetch(u_lim, ivec2(HELD[h], 0), 0);
    project(HELD[h], b.x, b.y);
  }
  for (int sweep = 0; sweep < u_hard; sweep++) for (int h = 0; h < nh; h++) {
    vec4 b = texelFetch(u_lim, ivec2(HELD[h], 0), 0);
    project(HELD[h], b.z, b.w);
  }
  // the fallback: the smallest blend toward the previous shown frame that meets every hard limit
  float beta = 0.0;
  for (int h = 0; h < nh; h++) {
    int t = HELD[h];
    vec4 b = texelFetch(u_lim, ivec2(t, 0), 0);
    float v = winVal(win(t >> 1), t & 1), pv = texelFetch(u_state, ivec2(t, 0), 0).w;
    if (v > b.w + 1.0e-6 && pv < v) beta = max(beta, (v - b.w) / (v - pv));
    else if (v < b.z - 1.0e-6 && pv > v) beta = max(beta, (b.z - v) / (pv - v));
  }
  beta = min(1.0, beta);
  // whether anything is limited this frame (any gain under 1, any lift, a blend): the apply pass copies the frame
  // untouched when not, after reading one texel
  bool limiting = beta > 0.0;   // (not "active": a reserved word in GLSL ES)
  for (int i = 0; i < u_nc; i++) if (A[i] < 1.0 || K[i] > 0.0) limiting = true;
  int c0 = (p.y * ${SOLVE_W} + p.x) * ${PER};
  float ov[${2 * PER}];
  for (int j = 0; j < ${PER}; j++) { int i = min(c0 + j, ${NCTRL - 1}); ov[2 * j] = A[i]; ov[2 * j + 1] = K[i]; }
  o_0 = vec4(ov[0], ov[1], ov[2], ov[3]);
  o_1 = vec4(ov[4], ov[5], ov[6], ov[7]);
  o_2 = vec4(ov[8], ov[9], ov[10], ov[11]);
  o_3 = vec4(ov[12], ov[13], beta, limiting ? 1.0 : 0.0);
}`;

// UNPACK: the solve's targets as the 9 x 9 gain texture, one texel per corner: (a, k, beta, limiting).
const UNPACK_FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_s0, u_s1, u_s2, u_s3;
out vec4 outColor;
void main() {
  ivec2 p = ivec2(gl_FragCoord.xy);
  int i = p.y * ${CX} + p.x, n = i / ${PER}, j = i - n * ${PER};
  ivec2 at = ivec2(n - (n / ${SOLVE_W}) * ${SOLVE_W}, n / ${SOLVE_W});
  vec4 t0 = texelFetch(u_s0, at, 0), t1 = texelFetch(u_s1, at, 0), t2 = texelFetch(u_s2, at, 0), t3 = texelFetch(u_s3, at, 0);
  vec2 ak = j == 0 ? t0.xy : j == 1 ? t0.zw : j == 2 ? t1.xy : j == 3 ? t1.zw : j == 4 ? t2.xy : j == 5 ? t2.zw : t3.xy;
  outColor = vec4(ak, t3.z, t3.w);
}`;

// SHOWN: each tracker's window through the gains, then the blend: the value the viewer gets (one fragment per tracker,
// so STATE's five rows read it instead of computing it five times).
const SHOWN_FS = `#version 300 es
precision highp float;
precision highp int;
out vec4 outColor;
${COMMON}
uniform sampler2D u_gain;
void main() {
  int t = int(gl_FragCoord.x), s = t & 1;
  ivec4 r = win(t >> 1);
  float sum = 0.0;
  for (int cy = r.y; cy <= r.w; cy++) for (int cx = r.x; cx <= r.z; cx++) {
    vec4 S = cellAt(cx, cy, s);
    vec4 g00 = texelFetch(u_gain, ivec2(cx, cy), 0), g10 = texelFetch(u_gain, ivec2(cx + 1, cy), 0);
    vec4 g01 = texelFetch(u_gain, ivec2(cx, cy + 1), 0), g11 = texelFetch(u_gain, ivec2(cx + 1, cy + 1), 0);
    sum += g00.x * S.x + g10.x * S.y + g01.x * S.z + g11.x * S.w;
    if (s == 0) sum += g00.y * (0.25 - S.x) + g10.y * (0.25 - S.y) + g01.y * (0.25 - S.z) + g11.y * (0.25 - S.w);
  }
  float vf = sum / float((r.z - r.x + 1) * (r.w - r.y + 1));
  float beta = texelFetch(u_gain, ivec2(0, 0), 0).z;
  float sPrev = texelFetch(u_state, ivec2(t, 0), 0).w;
  outColor = vec4(vf + beta * (sPrev - vf), vf, 0.0, 0.0);
}`;

// STATE: FlashLimiter.update (and the shared texels).
const STATE_FS = `#version 300 es
precision highp float;
precision highp int;
out vec4 outColor;
${COMMON}
uniform sampler2D u_pin, u_gain, u_shown;
void main() {
  ivec2 p = ivec2(gl_FragCoord.xy);
  int t = p.x, row = p.y;
  if (t >= NT) {                       // the shared texel: the forced rest, from the counters as they stood before
    vec4 g = texelFetch(u_state, ivec2(NT, 0), 0);
    if (row == 0) {
      bool flashing = false;
      for (int k = 0; k < u_ntq; k++) {
        vec4 a2 = texelFetch(u_state, ivec2(k, 2), 0), a3 = texelFetch(u_state, ivec2(k, 3), 0);
        int mask = int(texelFetch(u_state, ivec2(k, 4), 0).x + 0.5);
        float ag[7]; ag[0] = a2.x; ag[1] = a2.y; ag[2] = a2.z; ag[3] = a2.w; ag[4] = a3.x; ag[5] = a3.y; ag[6] = a3.z;
        int n = 0;
        for (int r = 0; r < RING; r++) if (ag[r] + u_dt < WINDOW_S && ((mask >> r) & 1) == 1) n++;
        if (n >= REST_COUNT) { flashing = true; break; }
      }
      float run = g.x, rest = g.y;
      if (rest > 0.0) { rest = rest - u_dt > 0.0 ? rest - u_dt : 0.0; if (rest == 0.0) run = 0.0; }
      else { run = flashing ? run + u_dt : max(0.0, run - u_dt); if (run >= RUN_S) { rest = REST_S; run = 0.0; } }
      outColor = vec4(run, rest, g.z + 1.0, texelFetch(u_gain, ivec2(0, 0), 0).z);
    } else if (row == 1) {
      float held = 0.0, partial = 0.0, leaks = 0.0;
      for (int k = 0; k < u_nt; k++) { float lvk = texelFetch(u_state, ivec2(k, 1), 0).y; held += lvk > 1.5 ? 1.0 : 0.0; partial += lvk > 0.5 && lvk < 1.5 ? 1.0 : 0.0; leaks += texelFetch(u_state, ivec2(k, 3), 0).w; }
      outColor = vec4(held, leaks, partial, 0.0);  // as they stood before this frame (receipts): fully held, partial
    } else outColor = vec4(0.0);
    return;
  }
  int q = kindOf(t);
  vec4 pn = texelFetch(u_pin, ivec2(t, 0), 0);
  float level = pn.y;
  vec4 r0 = texelFetch(u_state, ivec2(t, 0), 0), r1 = texelFetch(u_state, ivec2(t, 1), 0);
  vec4 r2 = texelFetch(u_state, ivec2(t, 2), 0), r3 = texelFetch(u_state, ivec2(t, 3), 0);
  vec4 r4 = texelFetch(u_state, ivec2(t, 4), 0);
  float ring[${LIMIT.RING}];
  ring[0] = r2.x; ring[1] = r2.y; ring[2] = r2.z; ring[3] = r2.w; ring[4] = r3.x; ring[5] = r3.y; ring[6] = r3.z;
  for (int k = 0; k < RING; k++) ring[k] = min(EMPTY_AGE, ring[k] + u_dt);
  float leaks = r3.w;
  int mask = int(r4.x + 0.5);
  float v = texelFetch(u_shown, ivec2(t, 0), 0).x;
  float dir = r0.x, X = r0.y, C = r0.z, open = r1.x;
  float ext = r1.w, extV = r4.y, extDir = r4.z;
  float th = pick(TH4, q), H = pick(HY4, q), NEAR = 0.5 * H;
  bool doCommit = false, rise = false;
  if (dir == 0.0) { dir = 1.0; X = v; C = v; open = -1.0; }
  else {
    if (dir > 0.0) {
      if (v > C) { C = v; if (open >= 0.0) ring[int(open)] = 0.0; else if (v - X >= th) { doCommit = true; rise = true; } }
      else if (C - v >= H) { dir = -1.0; X = C; C = v; open = -1.0; if (X - v >= th) doCommit = true; }
      else if (C - v <= NEAR && open >= 0.0) ring[int(open)] = 0.0;
    } else {
      if (v < C) { C = v; if (open >= 0.0) ring[int(open)] = 0.0; else if (X - v >= th) doCommit = true; }
      else if (v - C >= H) { dir = 1.0; X = C; C = v; open = -1.0; if (v - X >= th) { doCommit = true; rise = true; } }
      else if (v - C <= NEAR && open >= 0.0) ring[int(open)] = 0.0;
    }
    if (doCommit) {
      int idx = 0; float oldest = -1.0;
      for (int k = 0; k < RING; k++) if (ring[k] > oldest) { oldest = ring[k]; idx = k; }
      ring[idx] = 0.0;
      open = float(idx);
      mask = mask & ~(1 << idx);
      if (level > 1.5 || (level > 0.5 && rise)) leaks += 1.0;   // a transition the hold did not allow
    }
    if (open >= 0.0 && abs(C - X) >= pick(THREST4, q)) mask = mask | (1 << int(open));
    // the end that may still move (vj-gate.js FlashLimiter.update)
    if (doCommit) { ext = open; extV = v; extDir = dir; }
    else if (ext >= 0.0) {
      bool up = extDir > 0.0;
      if (up ? v > extV : v < extV) extV = v;
      float back = up ? extV - v : v - extV;
      if (back <= pick(EXTN4, q)) ring[int(ext)] = 0.0;
      else if (back >= pick(EXTC4, q)) ext = -1.0;
    }
  }
  if (row == 0) outColor = vec4(dir, X, C, v);
  else if (row == 1) outColor = vec4(open, level, pn.x, ext);
  else if (row == 2) outColor = vec4(ring[0], ring[1], ring[2], ring[3]);
  else if (row == 3) outColor = vec4(ring[4], ring[5], ring[6], leaks);
  else outColor = vec4(float(mask), extV, extDir, 0.0);
}`;

const APPLY_FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_src, u_gain, u_prev;
uniform ivec2 u_size;
out vec4 outColor;
${SRGB}
void main() {
  ivec2 px = ivec2(gl_FragCoord.xy);
  vec3 d = clamp(texelFetch(u_src, px, 0).rgb, 0.0, 1.0);
  vec4 g00 = texelFetch(u_gain, ivec2(0, 0), 0);
  if (g00.w < 0.5) { outColor = vec4(d, 1.0); return; }        // nothing limited this frame: the frame, untouched
  int cx = cellX(px.x, u_size.x), cy = cellY(px.y, u_size.y);
  int bx0 = boundX(cx, u_size.x), bx1 = boundX(cx + 1, u_size.x), by0 = boundY(cy, u_size.y), by1 = boundY(cy + 1, u_size.y);
  float fx = (float(px.x - bx0) + 0.5) / float(max(bx1 - bx0, 1)), fy = (float(px.y - by0) + 0.5) / float(max(by1 - by0, 1));
  fx = fx * fx * (3.0 - 2.0 * fx); fy = fy * fy * (3.0 - 2.0 * fy);   // the meter's smoothstep hats
  float beta = g00.z;
  g00 = texelFetch(u_gain, ivec2(cx, cy), 0);
  vec4 g10 = texelFetch(u_gain, ivec2(cx + 1, cy), 0);
  vec4 g01 = texelFetch(u_gain, ivec2(cx, cy + 1), 0), g11 = texelFetch(u_gain, ivec2(cx + 1, cy + 1), 0);
  vec2 g = g00.xy * ((1.0 - fx) * (1.0 - fy)) + g10.xy * (fx * (1.0 - fy)) + g01.xy * ((1.0 - fx) * fy) + g11.xy * (fx * fy);
  if (g.x >= 0.99999 && g.y <= 1.0e-5 && beta <= 1.0e-5) { outColor = vec4(d, 1.0); return; }
  vec3 lin = dec3(d);
  vec3 o = lin * g.x + (1.0 - lin) * g.y;
  if (beta > 1.0e-5) o = mix(o, dec3(texelFetch(u_prev, px, 0).rgb), beta);
  outColor = vec4(enc3(clamp(o, 0.0, 1.0)), 1.0);
}`;

// Start a program's compile and link without waiting (with KHR_parallel_shader_compile the driver works in the background);
// finish() later checks it and reads its uniforms.
function startLink(gl, fs, names) {
  const v = gl.createShader(gl.VERTEX_SHADER), fr = gl.createShader(gl.FRAGMENT_SHADER);
  gl.shaderSource(v, VERT); gl.compileShader(v);
  gl.shaderSource(fr, fs); gl.compileShader(fr);
  const prog = gl.createProgram();
  gl.attachShader(prog, v); gl.attachShader(prog, fr);
  gl.linkProgram(prog);
  return { prog, v, fr, names, u: null, error: "" };
}
function finish(gl, p) {
  if (p.u || p.error) return !!p.u;
  const ok = gl.getProgramParameter(p.prog, gl.LINK_STATUS);
  const log = ok ? "" : ((!gl.getShaderParameter(p.fr, gl.COMPILE_STATUS) ? gl.getShaderInfoLog(p.fr) : gl.getProgramInfoLog(p.prog)) || "link error");
  gl.deleteShader(p.v); gl.deleteShader(p.fr);
  if (!ok) { p.error = log; return false; }
  p.u = {};
  for (const n of p.names) p.u[n] = gl.getUniformLocation(p.prog, n);
  return true;
}
function texture(gl, w, h, internal, format, type, data = null) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  for (const [k, v] of [[gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE],
                        [gl.TEXTURE_MIN_FILTER, gl.NEAREST], [gl.TEXTURE_MAG_FILTER, gl.NEAREST]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
  gl.texImage2D(gl.TEXTURE_2D, 0, internal, w, h, 0, format, type, data);
  return tex;
}
function fbo(gl, texs) {
  const fb = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  texs.forEach((t, i) => gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0 + i, gl.TEXTURE_2D, t, 0));
  if (texs.length > 1) gl.drawBuffers(texs.map((_, i) => gl.COLOR_ATTACHMENT0 + i));
  const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  if (!ok) { gl.deleteFramebuffer(fb); throw new Error("limiter framebuffer incomplete"); }
  return fb;
}

// A twin's tracker state in the texture layout ((NT + 1) x 5 texels; texel (t, row) = floats row * 4 .. row * 4 + 3), the
// shared texel from its glob.
function stateTexels(m) {
  const out = new Float32Array((NT + 1) * TRACKER_ROWS * 4);
  for (let t = 0; t < NT; t++) for (let row = 0; row < TRACKER_ROWS; row++) for (let c = 0; c < 4; c++) {
    out[(row * (NT + 1) + t) * 4 + c] = m.state[t * TRACKER_FLOATS + row * 4 + c];
  }
  if (m.glob) { const g = (row, c) => (row * (NT + 1) + NT) * 4 + c; out[g(0, 0)] = m.glob[0]; out[g(0, 1)] = m.glob[1]; out[g(0, 2)] = m.glob[2]; out[g(0, 3)] = m.glob[3]; }
  return out;
}
// The window table: one RGBA8UI texel per window (x0, y0, x1, y1).
function windowTexels() {
  const out = new Uint8Array(NW * 4);
  WINDOWS.forEach((w, i) => { out.set(w, i * 4); });
  return out;
}

// createLimiter(gl, { preInternal, preType, decide }): the page's frame format for the pre-limit target (the look draws
// into it); decide "auto" (the GPU decision once it links, the JS twin until then or for good if it fails) or "cpu" (the
// JS twin always: receipts). Throws when no float target can be rendered. Programs compile in the background
// (KHR_parallel_shader_compile, when the browser has it): live() is false until the meter and the apply pass have linked,
// mode() says how the frame is decided ("gpu", "cpu" or "" while not live), error() why the decision (or, fatally, the
// meter) did not link.
const DECISION_UNIFORMS = ["u_win", "u_cells", "u_state", "u_dt", "u_nt", "u_ntq"];
// The fragment shaders' sources (tests/vj_core.test.mjs reads them for words GLSL ES reserves: a shader that does not
// compile leaves the page deciding on the CPU, or in its safe mode, which a browser receipt notices only when it runs).
export function limiterShaderSources() {
  return { meter1: METER1_FS, meter2: METER2_FS, band: BAND_FS, solve: SOLVE_FS, unpack: UNPACK_FS, shown: SHOWN_FS, state: STATE_FS, apply: APPLY_FS };
}
// The meter's block grid for a frame: blocks per cell (x, y) so that no block is wider or taller than BLOCK pixels.
export function meterGrid(w, h) {
  let cw = 0, ch = 0;
  for (let c = 0; c < GX; c++) cw = Math.max(cw, Math.floor(((c + 1) * w) / GX) - Math.floor((c * w) / GX));
  for (let c = 0; c < GY; c++) ch = Math.max(ch, Math.floor(((c + 1) * h) / GY) - Math.floor((c * h) / GY));
  const sx = Math.max(1, Math.ceil(cw / BLOCK)), sy = Math.max(1, Math.ceil(ch / BLOCK));
  return { sx, sy, width: GX * sx, height: GY * sy, cellW: cw, cellH: ch };
}
export function createLimiter(gl, { preInternal = gl.RGBA8, preType = gl.UNSIGNED_BYTE, decide = "auto", lateFrames = 0 } = {}) {
  const full = !!gl.getExtension("EXT_color_buffer_float");
  const half = full || !!gl.getExtension("EXT_color_buffer_half_float");
  if (!half) throw new Error("no float render target (EXT_color_buffer_float / _half_float): the limiter cannot meter");
  const SF = full ? gl.RGBA32F : gl.RGBA16F;            // state, gains, cells, bands, meter blocks
  const SFT = gl.FLOAT;
  const par = gl.getExtension("KHR_parallel_shader_compile");
  const meter1 = startLink(gl, METER1_FS, ["u_src", "u_size", "u_sub"]);
  const meter2 = startLink(gl, METER2_FS, ["u_lum", "u_red", "u_sub"]);
  const apply = startLink(gl, APPLY_FS, ["u_src", "u_gain", "u_prev", "u_size"]);
  const forceCpu = decide === "cpu";
  const band = forceCpu ? null : startLink(gl, BAND_FS, DECISION_UNIFORMS);
  const solve = forceCpu ? null : startLink(gl, SOLVE_FS, [...DECISION_UNIFORMS, "u_lim", "u_pin", "u_sweeps", "u_hard", "u_nc"]);
  const unpack = forceCpu ? null : startLink(gl, UNPACK_FS, ["u_s0", "u_s1", "u_s2", "u_s3"]);
  const shown = forceCpu ? null : startLink(gl, SHOWN_FS, [...DECISION_UNIFORMS, "u_gain"]);
  const state = forceCpu ? null : startLink(gl, STATE_FS, [...DECISION_UNIFORMS, "u_pin", "u_gain", "u_shown"]);
  const basic = [meter1, meter2, apply], decision = [band, solve, unpack, shown, state].filter(Boolean);
  let live = false, gpu = false, error = "", fatal = false, gpuFailed = forceCpu;
  const t0 = performance.now();
  let liveMs = null, gpuMs = null;
  const twin = new FlashLimiter();
  let twinUsed = false;                                  // the twin decided at least one frame (its state is the truth)
  function linked(p) { return !par || gl.getProgramParameter(p.prog, par.COMPLETION_STATUS_KHR); }
  function poll() {
    if (fatal) return false;
    if (!live && basic.every(linked)) {
      for (const p of basic) if (!finish(gl, p)) { fatal = true; error = `meter/apply: ${p.error}`; return false; }
      live = true; liveMs = Math.round(performance.now() - t0);
    }
    // (lateFrames: the GPU decision takes over no earlier than that many frames in, as a slow compile on a real GPU would
    // have it: receipts, ?limiter=late)
    if (live && !gpu && !gpuFailed && frames >= lateFrames && decision.every(linked)) {
      for (const p of decision) if (!finish(gl, p)) { gpuFailed = true; error = `decision (deciding on the CPU instead): ${p.error}`; }
      if (!gpuFailed) {
        gpu = true; gpuMs = Math.round(performance.now() - t0);
        // the twin's state moves to the GPU, so the counters run on without a break
        if (twinUsed) uploadState(stateTexels(twin));
      }
    }
    return live;
  }
  const T = {
    cells: texture(gl, GX * NSIG, GY, SF, gl.RGBA, SFT),
    gain: texture(gl, CX, CY, SF, gl.RGBA, SFT, (() => { const g = new Float32Array(NCTRL * 4); for (let i = 0; i < NCTRL; i++) g[i * 4] = 1; return g; })()),
    lim: texture(gl, NT, 1, SF, gl.RGBA, SFT), pin: texture(gl, NT, 1, SF, gl.RGBA, SFT),
    sol: [0, 1, 2, 3].map(() => texture(gl, SOLVE_W, SOLVE_H, SF, gl.RGBA, SFT)),
    shown: texture(gl, NT, 1, SF, gl.RGBA, SFT),
    win: texture(gl, NW, 1, gl.RGBA8UI, gl.RGBA_INTEGER, gl.UNSIGNED_BYTE, windowTexels()),
    state: [texture(gl, NT + 1, TRACKER_ROWS, SF, gl.RGBA, SFT, stateTexels(new FlashLimiter())), texture(gl, NT + 1, TRACKER_ROWS, SF, gl.RGBA, SFT, stateTexels(new FlashLimiter()))],
  };
  const F = { m2: fbo(gl, [T.cells]), gain: fbo(gl, [T.gain]), band: fbo(gl, [T.lim, T.pin]), sol: fbo(gl, T.sol), shown: fbo(gl, [T.shown]),
              state: [fbo(gl, [T.state[0]]), fbo(gl, [T.state[1]])] };
  let cur = 0;                                           // the state texture holding the latest state
  const S = { w: 0, h: 0, pre: null, preFb: null, shown: [null, null], shownFb: [null, null], read: 0, grid: null, mLum: null, mRed: null, m1: null };
  let frames = 0;
  const cellBuf = new Float32Array(NCELL_FLOATS), gainBuf = new Float32Array(NCTRL * 4);
  // (poll() may run outside a frame, from the page's HUD: the texture binding it borrows is put back)
  function uploadState(texels) {
    const was = gl.getParameter(gl.TEXTURE_BINDING_2D);
    for (const t of T.state) { gl.bindTexture(gl.TEXTURE_2D, t); gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, NT + 1, TRACKER_ROWS, gl.RGBA, gl.FLOAT, texels); }
    gl.bindTexture(gl.TEXTURE_2D, was);
    cur = 0;
  }
  function ensure(w, h) {
    if (S.w === w && S.h === h && S.pre) return;
    for (const t of [S.pre, ...S.shown, S.mLum, S.mRed]) if (t) gl.deleteTexture(t);
    for (const fb of [S.preFb, ...S.shownFb, S.m1]) if (fb) gl.deleteFramebuffer(fb);
    S.w = w; S.h = h;
    S.pre = texture(gl, w, h, preInternal, gl.RGBA, preType);
    S.preFb = fbo(gl, [S.pre]);
    S.shown = [texture(gl, w, h, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE), texture(gl, w, h, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE)];
    S.shownFb = [fbo(gl, [S.shown[0]]), fbo(gl, [S.shown[1]])];
    for (const fb of S.shownFb) { gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT); }
    S.grid = meterGrid(w, h);
    S.mLum = texture(gl, S.grid.width, S.grid.height, SF, gl.RGBA, SFT);
    S.mRed = texture(gl, S.grid.width, S.grid.height, SF, gl.RGBA, SFT);
    S.m1 = fbo(gl, [S.mLum, S.mRed]);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }
  function bind(unit, tex) { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex); }
  function draw(fb, w, h) { gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.viewport(0, 0, w, h); gl.drawArrays(gl.TRIANGLES, 0, 3); }
  function meter(src, w, h) {
    gl.useProgram(meter1.prog);
    bind(0, src);
    gl.uniform1i(meter1.u.u_src, 0); gl.uniform2i(meter1.u.u_size, w, h); gl.uniform2i(meter1.u.u_sub, S.grid.sx, S.grid.sy);
    draw(S.m1, S.grid.width, S.grid.height);
    gl.useProgram(meter2.prog);
    bind(0, S.mLum); bind(1, S.mRed);
    gl.uniform1i(meter2.u.u_lum, 0); gl.uniform1i(meter2.u.u_red, 1); gl.uniform2i(meter2.u.u_sub, S.grid.sx, S.grid.sy);
    draw(F.m2, GX * NSIG, GY);
  }
  // the GPU decision: BAND, SOLVE, UNPACK, SHOWN, STATE from the cells texture
  function common(p, dt) {
    gl.useProgram(p.prog);
    bind(0, T.win); bind(1, T.cells); bind(2, T.state[cur]);
    gl.uniform1i(p.u.u_win, 0); gl.uniform1i(p.u.u_cells, 1); gl.uniform1i(p.u.u_state, 2); gl.uniform1f(p.u.u_dt, dt);
    gl.uniform1i(p.u.u_nt, NT); gl.uniform1i(p.u.u_ntq, NTQ);
  }
  function decideGpu(dt) {
    common(band, dt);
    draw(F.band, NT, 1);
    common(solve, dt);
    bind(3, T.lim); bind(4, T.pin); gl.uniform1i(solve.u.u_lim, 3); gl.uniform1i(solve.u.u_pin, 4);
    gl.uniform1i(solve.u.u_sweeps, LIMIT.SWEEPS); gl.uniform1i(solve.u.u_hard, LIMIT.HARD_SWEEPS); gl.uniform1i(solve.u.u_nc, NCTRL);
    draw(F.sol, SOLVE_W, SOLVE_H);
    gl.useProgram(unpack.prog);
    T.sol.forEach((t, i) => { bind(i, t); gl.uniform1i(unpack.u[`u_s${i}`], i); });
    draw(F.gain, CX, CY);
    common(shown, dt);
    bind(3, T.gain); gl.uniform1i(shown.u.u_gain, 3);
    draw(F.shown, NT, 1);
    common(state, dt);
    bind(3, T.pin); bind(4, T.gain); bind(5, T.shown); gl.uniform1i(state.u.u_pin, 3); gl.uniform1i(state.u.u_gain, 4); gl.uniform1i(state.u.u_shown, 5);
    draw(F.state[1 - cur], NT + 1, TRACKER_ROWS);
    cur = 1 - cur;
  }
  // the CPU decision: the cell sums read back, the twin decides, the gains go up
  function decideCpu(dt) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, F.m2);
    gl.readPixels(0, 0, GX * NSIG, GY, gl.RGBA, gl.FLOAT, cellBuf);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    const r = twin.step(cellBuf, dt);
    twinUsed = true;
    let limiting = r.beta > 0;
    for (let i = 0; i < NCTRL; i++) { gainBuf[i * 4] = r.a[i]; gainBuf[i * 4 + 1] = r.k[i]; gainBuf[i * 4 + 2] = r.beta; if (r.a[i] < 1 || r.k[i] > 0) limiting = true; }
    for (let i = 0; i < NCTRL; i++) gainBuf[i * 4 + 3] = limiting ? 1 : 0;
    gl.bindTexture(gl.TEXTURE_2D, T.gain);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, CX, CY, gl.RGBA, gl.FLOAT, gainBuf);
  }
  function readTwin() {
    const g = twin.glob;
    let partial = 0, heldFull = 0;
    for (let t = 0; t < NT; t++) { const lv = twin.state[t * TRACKER_FLOATS + 5]; heldFull += lv > 1.5 ? 1 : 0; partial += lv > 0.5 && lv < 1.5 ? 1 : 0; }
    const trackers = []; for (let t = 0; t < NT; t++) trackers.push(Array.from(twin.state.slice(t * TRACKER_FLOATS, (t + 1) * TRACKER_FLOATS)));
    return { ready: true, mode: "cpu", trackers, run: g[0], rest: g[1], frames: g[2], beta: g[3], held: heldFull, leaks: twin.leaks, partial,
             a: Array.from(twin.a), k: Array.from(twin.k), betaNow: twin.beta, cells: Array.from(cellBuf) };
  }
  return {
    full, format: full ? "RGBA32F" : "RGBA16F", parallel: !!par,
    live: () => poll(), ready: () => poll(), mode: () => (poll() ? (gpu ? "gpu" : "cpu") : ""),
    error: () => error, fatal: () => fatal, compileMs: () => liveMs, gpuMs: () => gpuMs,
    // the target the look draws into, and its texture
    preTarget(w, h) { ensure(w, h); return S.preFb; },
    preTexture() { return S.pre; },
    // Meter, decide and apply `src` (w x h, display values) for a frame dt seconds after the last; the result lands on
    // the canvas (the default framebuffer). False (and nothing drawn) while the meter and apply programs are compiling.
    // mark(stage), when given (the cost receipt), is called after each stage: "meter", "decide", "apply", "blit".
    run(src, w, h, dt, mark = null) {
      if (!poll()) return false;
      ensure(w, h);
      const d = Math.max(0, Math.min(0.25, Number.isFinite(dt) ? dt : 0));
      meter(src, w, h);
      if (mark) mark("meter");
      if (gpu) decideGpu(d); else decideCpu(d);
      if (mark) mark("decide");
      const write = 1 - S.read;
      gl.useProgram(apply.prog);
      bind(0, src); bind(1, T.gain); bind(2, S.shown[S.read]);
      gl.uniform1i(apply.u.u_src, 0); gl.uniform1i(apply.u.u_gain, 1); gl.uniform1i(apply.u.u_prev, 2); gl.uniform2i(apply.u.u_size, w, h);
      draw(S.shownFb[write], w, h);
      if (mark) mark("apply");
      S.read = write;
      gl.bindFramebuffer(gl.READ_FRAMEBUFFER, S.shownFb[write]);
      gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, null);
      gl.blitFramebuffer(0, 0, w, h, 0, 0, w, h, gl.COLOR_BUFFER_BIT, gl.NEAREST);
      gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.activeTexture(gl.TEXTURE0);
      if (mark) mark("blit");
      frames++;
      return true;
    },
    // Receipts: the GPU decision alone on given cell sums (a Float32Array laid out as vj-gate.js cellIndex), as the JS
    // twin takes them. Returns what read() returns (null unless the GPU decision runs).
    decideCells(cells, dt) {
      if (!poll() || !gpu) return null;
      gl.bindTexture(gl.TEXTURE_2D, T.cells);
      gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, GX * NSIG, GY, gl.RGBA, gl.FLOAT, cells);
      decideGpu(Math.max(0, Math.min(0.25, dt)));
      return this.read();
    },
    // Receipts and the HUD: the state, the gains and the cells, read back (a stall: never per frame in a show).
    read() {
      if (!poll()) return { ready: false, error };
      if (!gpu) return readTwin();
      const st = new Float32Array((NT + 1) * TRACKER_ROWS * 4), gn = new Float32Array(NCTRL * 4), ce = new Float32Array(NCELL_FLOATS);
      gl.bindFramebuffer(gl.FRAMEBUFFER, F.state[cur]); gl.readPixels(0, 0, NT + 1, TRACKER_ROWS, gl.RGBA, gl.FLOAT, st);
      gl.bindFramebuffer(gl.FRAMEBUFFER, F.gain); gl.readPixels(0, 0, CX, CY, gl.RGBA, gl.FLOAT, gn);
      gl.bindFramebuffer(gl.FRAMEBUFFER, F.m2); gl.readPixels(0, 0, GX * NSIG, GY, gl.RGBA, gl.FLOAT, ce);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      const tracker = (t) => { const o = []; for (let row = 0; row < TRACKER_ROWS; row++) for (let c = 0; c < 4; c++) o.push(st[(row * (NT + 1) + t) * 4 + c]); return o; };
      const trackers = []; for (let t = 0; t < NT; t++) trackers.push(tracker(t));
      const g0 = tracker(NT);
      return { ready: true, mode: "gpu", compile_ms: liveMs, gpu_ms: gpuMs, trackers, run: g0[0], rest: g0[1], frames: g0[2], beta: g0[3], held: g0[4], leaks: g0[5], partial: g0[6],
               a: Array.from({ length: NCTRL }, (_, i) => gn[i * 4]), k: Array.from({ length: NCTRL }, (_, i) => gn[i * 4 + 1]),
               betaNow: gn[2], cells: Array.from(ce) };
    },
    reset() {
      twin.reset(); twinUsed = false;
      uploadState(stateTexels(new FlashLimiter()));
    },
    frames: () => frames,
    grid: () => S.grid,
    dispose() {
      for (const p of [meter1, meter2, apply, band, solve, unpack, shown, state]) if (p) gl.deleteProgram(p.prog);
      for (const t of [T.cells, T.gain, T.lim, T.pin, ...T.sol, T.shown, T.win, ...T.state, S.pre, ...S.shown, S.mLum, S.mRed]) if (t) gl.deleteTexture(t);
      for (const fb of [F.m2, F.gain, F.band, F.sol, F.shown, ...F.state, S.preFb, ...S.shownFb, S.m1]) if (fb) gl.deleteFramebuffer(fb);
    },
  };
}
