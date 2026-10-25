// VJ gate v2 on the GPU: arsenal/web/vj-limiter.js (ES module, WebGL2; no DOM). The rules and their JS twin live in
// vj-gate.js (FlashLimiter); this module runs them on the frame the viewer is about to see, every frame, without ever
// reading a pixel back to the CPU (no stall):
//
//   METER   the final frame -> 64 x 36 texels (two targets: luminance and red, each texel four hat-weighted sums of the
//           sRGB-decoded pixels of its block; every pixel is read up to 10 x 10 a texel, i.e. every pixel at 640 x 360)
//           -> 8 x 4 "cells" (cell (cx, cy), signal s at texel (2 cx + s, cy): the cell's four corner sums)
//   SOLVE   5 x 5 fragments, one per corner gain, each running the whole decision (the bands of the 36 trackers from the
//           state, the projections, the fallback blend): out (a, k, beta, 1). Every fragment computes the same thing, so
//           the 25 gains agree exactly.
//   STATE   (36 + 1) x 5 fragments: each tracker's five texels after this frame (its counter, its held band, its ring of
//           transition ends and which of them were full size), and the shared texels (the flashing run, the forced rest,
//           the frame count, beta; the held and leak counts as they stood)
//   APPLY   the frame through the gains (linear light: a Y + k (1 - Y), bilinear between the corners, the same hats the
//           meter used) and, when beta > 0, blended toward the previous shown frame, into the SHOWN pair (RGBA8: exactly
//           what the canvas gets), then blitted to the canvas. With nothing held, every gain is exactly 1 and beta 0: the
//           pixel is copied untouched.
// The state and the gains are float textures (RGBA32F with EXT_color_buffer_float, else RGBA16F). No float target at all:
// createLimiter throws and the page runs its safe mode (vj.js: no punch, no dip, no set reactions).

import { LIMIT, WINDOWS, NT, NSIG, TRACKER_FLOATS, TRACKER_ROWS, NCELL_FLOATS, FlashLimiter } from "./vj-gate.js";

const VERT = `#version 300 es
precision highp float;
void main() {
  vec2 pos[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
  gl_Position = vec4(pos[gl_VertexID], 0.0, 1.0);
}`;

const f = (x) => { const s = String(+x); return /[.e]/.test(s) ? s : `${s}.0`; };
const MSUB_X = 16, MSUB_Y = 9;             // meter texels per cell
const MW = LIMIT.GRID * MSUB_X, MH = LIMIT.GRID * MSUB_Y;   // 64 x 36
const MAX_SIDE = 10;                       // pixels read per texel side before the meter strides

// sRGB: the canvas's values are display-referred (the composite and the look write gamma-encoded values the screen shows)
const SRGB = `
float dec1(float c) { return c <= 0.04045 ? c / 12.92 : pow((c + 0.055) / 1.055, 2.4); }
vec3 dec3(vec3 c) { return vec3(dec1(c.r), dec1(c.g), dec1(c.b)); }
float enc1(float l) { return l <= 0.0031308 ? l * 12.92 : 1.055 * pow(l, 1.0 / 2.4) - 0.055; }
vec3 enc3(vec3 l) { return vec3(enc1(l.r), enc1(l.g), enc1(l.b)); }
// cell boundaries in pixels: B_c = floor(c n / 4); a pixel belongs to the cell whose [B_c, B_c+1) holds it, and its hat
// weights come from its centre's place in that cell (the meter and the apply pass share these two functions)
int bound(int c, int n) { return (c * n) / ${LIMIT.GRID}; }
int cellOf(int p, int n) { int c = 0; for (int k = 1; k < ${LIMIT.GRID}; k++) if (p >= bound(k, n)) c = k; return c; }
`;

const METER1_FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_src;
uniform ivec2 u_size;
layout(location = 0) out vec4 o_lum;
layout(location = 1) out vec4 o_red;
${SRGB}
void main() {
  ivec2 t = ivec2(gl_FragCoord.xy);
  int cx = t.x / ${MSUB_X}, cy = t.y / ${MSUB_Y}, lx = t.x - cx * ${MSUB_X}, ly = t.y - cy * ${MSUB_Y};
  int bx0 = bound(cx, u_size.x), bx1 = bound(cx + 1, u_size.x), by0 = bound(cy, u_size.y), by1 = bound(cy + 1, u_size.y);
  int cw = max(bx1 - bx0, 1), ch = max(by1 - by0, 1);
  int x0 = bx0 + (lx * cw) / ${MSUB_X}, x1 = bx0 + ((lx + 1) * cw) / ${MSUB_X};
  int y0 = by0 + (ly * ch) / ${MSUB_Y}, y1 = by0 + ((ly + 1) * ch) / ${MSUB_Y};
  int nx = x1 - x0, ny = y1 - y0;
  int sx = max(1, (nx + ${MAX_SIDE - 1}) / ${MAX_SIDE}), sy = max(1, (ny + ${MAX_SIDE - 1}) / ${MAX_SIDE});
  vec4 L = vec4(0.0), R = vec4(0.0);
  float n = 0.0;
  for (int y = y0; y < y1; y += sy) for (int x = x0; x < x1; x += sx) {
    vec3 d = clamp(texelFetch(u_src, ivec2(x, y), 0).rgb, 0.0, 1.0);
    vec3 lin = dec3(d);
    float l = dot(lin, vec3(0.2126, 0.7152, 0.0722));
    float sum = d.r + d.g + d.b;
    // WCAG red: a saturated red pixel (R / (R + G + B) >= 0.8, display values), its quantity (R - G - B) x 320 in linear
    // light (stored / 320)
    float red = (sum > 0.0 && d.r >= 0.8 * sum) ? max(0.0, lin.r - lin.g - lin.b) : 0.0;
    float fx = (float(x - bx0) + 0.5) / float(cw), fy = (float(y - by0) + 0.5) / float(ch);
    vec4 h = vec4((1.0 - fx) * (1.0 - fy), fx * (1.0 - fy), (1.0 - fx) * fy, fx * fy);
    L += h * l; R += h * red; n += 1.0;
  }
  // this block's share of its cell's mean (each read pixel stands for nx * ny / n of the block's pixels)
  float wgt = n > 0.0 ? float(nx * ny) / (n * float(cw * ch)) : 0.0;
  o_lum = L * wgt; o_red = R * wgt;
}`;

const METER2_FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_lum, u_red;
uniform ivec2 u_sub;           // meter texels per cell (16 x 9), a uniform for the same reason as the decision's loops
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

// The decision, shared by SOLVE and STATE: a line-by-line port of vj-gate.js FlashLimiter (band, project, solve, update).
function decisionGlsl(withSolve) {
  const W = WINDOWS.map((w) => `ivec4(${w.join(", ")})`).join(", ");
  return `
const int NT = ${NT};
const int NW = ${WINDOWS.length};
const int RING = ${LIMIT.RING};
const float NMAX = ${f(LIMIT.N_MAX)};
const float WINDOW_S = ${f(LIMIT.WINDOW_S)};
const float EMPTY_AGE = ${f(LIMIT.EMPTY_AGE)};
const float BASE_TAU = ${f(LIMIT.BASE_TAU)};
const float RUN_S = ${f(LIMIT.RUN_S)};
const float REST_S = ${f(LIMIT.REST_S)};
const int REST_COUNT = ${LIMIT.REST_COUNT};
const vec2 THREST = vec2(${f(LIMIT.TH_REST[0])}, ${f(LIMIT.TH_REST[1])});
const int SWEEPS = ${LIMIT.SWEEPS};
const int HARD_SWEEPS = ${LIMIT.HARD_SWEEPS};
const float K_MAX = ${f(LIMIT.K_MAX)};
const vec2 THV = vec2(${f(LIMIT.TH[0])}, ${f(LIMIT.TH[1])});
const vec2 HYV = vec2(${f(LIMIT.HYST[0])}, ${f(LIMIT.HYST[1])});
const vec2 BANDV = vec2(${f(LIMIT.BAND[0])}, ${f(LIMIT.BAND[1])});
const vec2 DRIFTV = vec2(${f(LIMIT.DRIFT[0])}, ${f(LIMIT.DRIFT[1])});
const float BIG = 1.0e9;
const ivec4 WIN[${WINDOWS.length}] = ivec4[${WINDOWS.length}](${W});
uniform sampler2D u_cells, u_state;
uniform float u_dt;
// loop counts as uniforms (NT, SWEEPS, HARD_SWEEPS, 25 corners): a shader compiler that unrolls loops of constant length
// (Direct3D's fxc, behind ANGLE on Windows) keeps these as loops instead of pasting the solve out thousands of times
uniform int u_nt, u_sweeps, u_hard, u_nc;
float CELL[${NCELL_FLOATS}];
float A[25];
float K[25];
void loadCells() {
  for (int cy = 0; cy < ${LIMIT.GRID}; cy++) for (int cx = 0; cx < ${LIMIT.GRID}; cx++) for (int s = 0; s < ${NSIG}; s++) {
    vec4 v = texelFetch(u_cells, ivec2(cx * ${NSIG} + s, cy), 0);
    int b = ((cy * ${LIMIT.GRID} + cx) * ${NSIG} + s) * 4;
    CELL[b] = v.x; CELL[b + 1] = v.y; CELL[b + 2] = v.z; CELL[b + 3] = v.w;
  }
}
int cellIdx(int cx, int cy, int s, int j) { return ((cy * ${LIMIT.GRID} + cx) * ${NSIG} + s) * 4 + j; }
int ctrlIdx(int cx, int cy, int j) { return (cy + (j >> 1)) * ${LIMIT.CTRL} + cx + (j & 1); }
float winVal(int w, int s) {
  ivec4 r = WIN[w];
  float sum = 0.0;
  for (int cy = r.y; cy <= r.w; cy++) for (int cx = r.x; cx <= r.z; cx++) for (int j = 0; j < 4; j++) {
    float S = CELL[cellIdx(cx, cy, s, j)];
    int i = ctrlIdx(cx, cy, j);
    sum += A[i] * S + (s == 0 ? K[i] * (0.25 - S) : 0.0);
  }
  return sum / float((r.z - r.x + 1) * (r.w - r.y + 1));
}
float winWant(int w, int s) {
  ivec4 r = WIN[w];
  float sum = 0.0;
  for (int cy = r.y; cy <= r.w; cy++) for (int cx = r.x; cx <= r.z; cx++) for (int j = 0; j < 4; j++) sum += CELL[cellIdx(cx, cy, s, j)];
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
struct Band { float lo; float hi; float hlo; float hhi; float pin; float base; float want; bool held; };
Band band(int t) {
  Band b;
  int s = t & 1, w = t >> 1;
  vec4 r0 = texelFetch(u_state, ivec2(t, 0), 0), r1 = texelFetch(u_state, ivec2(t, 1), 0);
  vec4 r2 = texelFetch(u_state, ivec2(t, 2), 0), r3 = texelFetch(u_state, ivec2(t, 3), 0);
  float th = s == 0 ? THV.x : THV.y, bw = s == 0 ? BANDV.x : BANDV.y, dr = s == 0 ? DRIFTV.x : DRIFTV.y;
  b.want = winWant(w, s);
  float dir = r0.x, X = r0.y, C = r0.z, sPrev = r0.w, open = r1.x, held = r1.y;
  b.base = dir == 0.0 ? b.want : r1.w + (b.want - r1.w) * (1.0 - exp(-u_dt / BASE_TAU));
  b.held = false; b.pin = r1.z;
  b.lo = -BIG; b.hlo = -BIG; b.hi = BIG; b.hhi = BIG;
  if (dir == 0.0) return b;
  float eps = s == 0 ? 1.0e-4 : 2.0e-5;
  float rest = texelFetch(u_state, ivec2(NT, 0), 0).y;
  float budget = rest > 0.0 ? 0.0 : NMAX;
  if (countRing(r2, r3) < budget) return b;
  float ncLo, ncHi;
  if (dir > 0.0) { ncLo = C - th; ncHi = open >= 0.0 ? BIG : X + th; }
  else { ncLo = open >= 0.0 ? -BIG : X - th; ncHi = C + th; }
  float pin;
  if (held > 0.5) {
    pin = r1.z;
    float top = pin + bw, st = dr * u_dt;
    if (b.want > top) pin += min(st, b.want - top);
    else if (b.want < pin) pin -= min(st, pin - b.want);
  } else pin = b.base - 0.5 * bw;
  if (pin < ncLo) pin = ncLo;
  if (pin + bw > ncHi) pin = ncHi - bw;
  b.held = true; b.pin = pin;
  b.hlo = ncLo + eps; b.hhi = ncHi - eps;
  b.lo = max(pin, b.hlo); b.hi = min(pin + bw, b.hhi);
  if (b.lo > b.hi) { float v = min(max(sPrev, b.hlo), b.hhi); b.lo = v; b.hi = v; }
  return b;
}
${withSolve ? SOLVE_GLSL : ""}`;
}
const SOLVE_GLSL = `
void project(int t, float lo, float hi) {
  int s = t & 1, w = t >> 1;
  float v = winVal(w, s);
  if (v <= hi && v >= lo) return;
  bool down = v > hi;
  float margin = min(s == 0 ? 0.002 : 0.0006, 0.1 * (hi - lo));
  float target = down ? hi - margin : lo + margin;
  float ga[25], gk[25];
  for (int i = 0; i < u_nc; i++) { ga[i] = 0.0; gk[i] = 0.0; }
  ivec4 r = WIN[w];
  float inv = 1.0 / float((r.z - r.x + 1) * (r.w - r.y + 1));
  for (int cy = r.y; cy <= r.w; cy++) for (int cx = r.x; cx <= r.z; cx++) for (int j = 0; j < 4; j++) {
    float Sv = CELL[cellIdx(cx, cy, s, j)];
    int i = ctrlIdx(cx, cy, j);
    ga[i] += Sv * inv;
    if (s == 0) gk[i] += (0.25 - Sv) * inv;
  }
  float norm = 0.0;
  for (int i = 0; i < u_nc; i++) {
    if (down ? A[i] <= 0.0 : A[i] >= 1.0) ga[i] = 0.0;
    if (s != 0 || (down ? K[i] <= 0.0 : K[i] >= K_MAX)) gk[i] = 0.0;
    norm += ga[i] * ga[i] + gk[i] * gk[i];
  }
  if (norm < 1.0e-12) return;
  float d = (target - v) / norm;
  for (int i = 0; i < u_nc; i++) {
    A[i] = clamp(A[i] + d * ga[i], 0.0, 1.0);
    K[i] = clamp(K[i] + d * gk[i], 0.0, K_MAX);
  }
}
Band BANDS[NT];
float solve() {
  for (int t = 0; t < u_nt; t++) BANDS[t] = band(t);
  for (int i = 0; i < u_nc; i++) { A[i] = 1.0; K[i] = 0.0; }
  for (int sweep = 0; sweep < u_sweeps; sweep++) for (int t = 0; t < u_nt; t++) if (BANDS[t].held) project(t, BANDS[t].lo, BANDS[t].hi);
  for (int sweep = 0; sweep < u_hard; sweep++) for (int t = 0; t < u_nt; t++) if (BANDS[t].held) project(t, BANDS[t].hlo, BANDS[t].hhi);
  float beta = 0.0;
  for (int t = 0; t < u_nt; t++) {
    if (!BANDS[t].held) continue;
    float v = winVal(t >> 1, t & 1), p = texelFetch(u_state, ivec2(t, 0), 0).w;
    float lo = BANDS[t].hlo, hi = BANDS[t].hhi;
    if (v > hi && p < v) beta = max(beta, (v - hi) / (v - p));
    else if (v < lo && p > v) beta = max(beta, (lo - v) / (p - v));
  }
  return min(1.0, beta);
}
`;

const SOLVE_FS = () => `#version 300 es
precision highp float;
precision highp int;
out vec4 outColor;
${decisionGlsl(true)}
void main() {
  ivec2 p = ivec2(gl_FragCoord.xy);
  loadCells();
  float beta = solve();
  int ci = p.y * ${LIMIT.CTRL} + p.x;
  // w: whether anything is limited this frame (any gain under 1, any lift, a blend): the apply pass copies the frame
  // untouched when not, after reading this one texel
  bool limiting = beta > 0.0;   // (not "active": a reserved word in GLSL ES)
  for (int i = 0; i < u_nc; i++) if (A[i] < 1.0 || K[i] > 0.0) limiting = true;
  outColor = vec4(A[ci], K[ci], beta, limiting ? 1.0 : 0.0);
}`;

const STATE_FS = () => `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_gain;
out vec4 outColor;
${decisionGlsl(false)}
void main() {
  ivec2 p = ivec2(gl_FragCoord.xy);
  int t = p.x, row = p.y;
  if (t >= NT) {                       // the shared texel: the forced rest, from the counters as they stood before
    vec4 g = texelFetch(u_state, ivec2(NT, 0), 0), g1 = texelFetch(u_state, ivec2(NT, 1), 0);
    if (row == 0) {
      bool flashing = false;
      for (int k = 0; k < u_nt; k++) {
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
      float held = 0.0, leaks = 0.0;
      for (int k = 0; k < u_nt; k++) { held += texelFetch(u_state, ivec2(k, 1), 0).y; leaks += texelFetch(u_state, ivec2(k, 3), 0).w; }
      outColor = vec4(held, leaks, 0.0, 0.0);      // as they stood before this frame (receipts)
    } else outColor = vec4(0.0);
    return;
  }
  loadCells();
  for (int i = 0; i < u_nc; i++) { vec4 gv = texelFetch(u_gain, ivec2(i - (i / ${LIMIT.CTRL}) * ${LIMIT.CTRL}, i / ${LIMIT.CTRL}), 0); A[i] = gv.x; K[i] = gv.y; }
  float beta = texelFetch(u_gain, ivec2(0, 0), 0).z;
  Band b = band(t);
  int s = t & 1, w = t >> 1;
  vec4 r0 = texelFetch(u_state, ivec2(t, 0), 0), r1 = texelFetch(u_state, ivec2(t, 1), 0);
  vec4 r2 = texelFetch(u_state, ivec2(t, 2), 0), r3 = texelFetch(u_state, ivec2(t, 3), 0);
  float ring[${LIMIT.RING}];
  ring[0] = r2.x; ring[1] = r2.y; ring[2] = r2.z; ring[3] = r2.w; ring[4] = r3.x; ring[5] = r3.y; ring[6] = r3.z;
  for (int r = 0; r < RING; r++) ring[r] = min(EMPTY_AGE, ring[r] + u_dt);
  float leaks = r3.w;
  int mask = int(texelFetch(u_state, ivec2(t, 4), 0).x + 0.5);
  float vf = winVal(w, s);
  float v = vf + beta * (r0.w - vf);
  float dir = r0.x, X = r0.y, C = r0.z, open = r1.x;
  float th = s == 0 ? THV.x : THV.y, H = s == 0 ? HYV.x : HYV.y, NEAR = 0.5 * H;
  bool doCommit = false;
  if (dir == 0.0) { dir = 1.0; X = v; C = v; open = -1.0; }
  else if (dir > 0.0) {
    if (v > C) { C = v; if (open >= 0.0) ring[int(open)] = 0.0; else if (v - X >= th) doCommit = true; }
    else if (C - v >= H) { dir = -1.0; X = C; C = v; open = -1.0; if (X - v >= th) doCommit = true; }
    else if (C - v <= NEAR && open >= 0.0) ring[int(open)] = 0.0;
  } else {
    if (v < C) { C = v; if (open >= 0.0) ring[int(open)] = 0.0; else if (X - v >= th) doCommit = true; }
    else if (v - C >= H) { dir = 1.0; X = C; C = v; open = -1.0; if (v - X >= th) doCommit = true; }
    else if (v - C <= NEAR && open >= 0.0) ring[int(open)] = 0.0;
  }
  if (doCommit) {
    int idx = 0; float oldest = -1.0;
    for (int r = 0; r < RING; r++) if (ring[r] > oldest) { oldest = ring[r]; idx = r; }
    ring[idx] = 0.0;
    open = float(idx);
    mask = mask & ~(1 << idx);
    if (b.held) leaks += 1.0;
  }
  if (open >= 0.0 && abs(C - X) >= (s == 0 ? THREST.x : THREST.y)) mask = mask | (1 << int(open));
  if (row == 0) outColor = vec4(dir, X, C, v);
  else if (row == 1) outColor = vec4(open, b.held ? 1.0 : 0.0, b.pin, b.base);
  else if (row == 2) outColor = vec4(ring[0], ring[1], ring[2], ring[3]);
  else if (row == 3) outColor = vec4(ring[4], ring[5], ring[6], leaks);
  else outColor = vec4(float(mask), 0.0, 0.0, 0.0);
}`;

const APPLY_FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_src, u_gain, u_prev;
uniform ivec4 u_bx, u_by;      // the cell boundaries B_0..B_3 in pixels (B_c = floor(c n / 4)), x and y
uniform vec4 u_ix, u_iy;       // 1 / (B_c+1 - B_c): the cells' widths and heights, inverted
out vec4 outColor;
${SRGB}
void main() {
  ivec2 px = ivec2(gl_FragCoord.xy);
  vec3 d = clamp(texelFetch(u_src, px, 0).rgb, 0.0, 1.0);
  vec4 g00 = texelFetch(u_gain, ivec2(0, 0), 0);
  if (g00.w < 0.5) { outColor = vec4(d, 1.0); return; }        // nothing limited this frame: the frame, untouched
  int cx = px.x >= u_bx.w ? 3 : px.x >= u_bx.z ? 2 : px.x >= u_bx.y ? 1 : 0;
  int cy = px.y >= u_by.w ? 3 : px.y >= u_by.z ? 2 : px.y >= u_by.y ? 1 : 0;
  float fx = (float(px.x - u_bx[cx]) + 0.5) * u_ix[cx], fy = (float(px.y - u_by[cy]) + 0.5) * u_iy[cy];
  g00 = texelFetch(u_gain, ivec2(cx, cy), 0);
  vec4 g10 = texelFetch(u_gain, ivec2(cx + 1, cy), 0);
  vec4 g01 = texelFetch(u_gain, ivec2(cx, cy + 1), 0), g11 = texelFetch(u_gain, ivec2(cx + 1, cy + 1), 0);
  vec2 g = g00.xy * ((1.0 - fx) * (1.0 - fy)) + g10.xy * (fx * (1.0 - fy)) + g01.xy * ((1.0 - fx) * fy) + g11.xy * (fx * fy);
  float beta = g00.z;
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
  return { prog, v, fr, names, u: null };
}
function finish(gl, p) {
  if (p.u) return;
  const ok = gl.getProgramParameter(p.prog, gl.LINK_STATUS);
  const log = ok ? "" : ((!gl.getShaderParameter(p.fr, gl.COMPILE_STATUS) ? gl.getShaderInfoLog(p.fr) : gl.getProgramInfoLog(p.prog)) || "link error");
  gl.deleteShader(p.v); gl.deleteShader(p.fr);
  if (!ok) throw new Error(log);
  p.u = {};
  for (const n of p.names) p.u[n] = gl.getUniformLocation(p.prog, n);
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

// The initial state texture: the JS twin's reset state (every ring slot empty, no counter started).
function initialState() {
  const m = new FlashLimiter();
  const out = new Float32Array((NT + 1) * TRACKER_ROWS * 4);
  for (let t = 0; t < NT; t++) for (let row = 0; row < TRACKER_ROWS; row++) for (let c = 0; c < 4; c++) {
    out[(row * (NT + 1) + t) * 4 + c] = m.state[t * TRACKER_FLOATS + row * 4 + c];
  }
  return out;
}

// createLimiter(gl, { preInternal, preType }): the page's frame format for the pre-limit target (the look draws into it).
// Throws when no float target can be rendered. Its programs compile in the background (KHR_parallel_shader_compile, when
// the browser has it): ready() is false until all five have linked, and run() refuses until then (the page keeps its safe
// mode meanwhile); a program that fails to link makes error() say why, for good.
const DECISION_UNIFORMS = ["u_cells", "u_state", "u_dt", "u_nt", "u_sweeps", "u_hard", "u_nc"];
// The five fragment shaders' sources (tests/vj_core.test.mjs reads them for words GLSL ES reserves: a shader that does
// not compile leaves the page in its safe mode, which a browser receipt notices only when it runs).
export function limiterShaderSources() {
  return { meter1: METER1_FS, meter2: METER2_FS, solve: SOLVE_FS(), state: STATE_FS(), apply: APPLY_FS };
}
export function createLimiter(gl, { preInternal = gl.RGBA8, preType = gl.UNSIGNED_BYTE } = {}) {
  const full = !!gl.getExtension("EXT_color_buffer_float");
  const half = full || !!gl.getExtension("EXT_color_buffer_half_float");
  if (!half) throw new Error("no float render target (EXT_color_buffer_float / _half_float): the limiter cannot keep its state");
  const SF = full ? gl.RGBA32F : gl.RGBA16F;            // state, gains, cells
  const SFT = gl.FLOAT;
  const MF = gl.RGBA16F;                                 // meter blocks (half is plenty for a block's share of a mean)
  const par = gl.getExtension("KHR_parallel_shader_compile");
  const meter1 = startLink(gl, METER1_FS, ["u_src", "u_size"]);
  const meter2 = startLink(gl, METER2_FS, ["u_lum", "u_red", "u_sub"]);
  const solve = startLink(gl, SOLVE_FS(), DECISION_UNIFORMS);
  const state = startLink(gl, STATE_FS(), [...DECISION_UNIFORMS, "u_gain"]);
  const apply = startLink(gl, APPLY_FS, ["u_src", "u_gain", "u_prev", "u_bx", "u_by", "u_ix", "u_iy"]);
  const programs = [meter1, meter2, solve, state, apply];
  let ready = false, error = "";
  const t0 = performance.now();
  let compileMs = null;
  function poll() {
    if (ready || error) return ready;
    if (par && programs.some((p) => !gl.getProgramParameter(p.prog, par.COMPLETION_STATUS_KHR))) return false;
    try { for (const p of programs) finish(gl, p); } catch (err) { error = String(err.message || err); return false; }
    ready = true;
    compileMs = Math.round(performance.now() - t0);
    return true;
  }
  const T = {
    mLum: texture(gl, MW, MH, MF, gl.RGBA, gl.HALF_FLOAT), mRed: texture(gl, MW, MH, MF, gl.RGBA, gl.HALF_FLOAT),
    cells: texture(gl, LIMIT.GRID * NSIG, LIMIT.GRID, SF, gl.RGBA, SFT),
    gain: texture(gl, LIMIT.CTRL, LIMIT.CTRL, SF, gl.RGBA, SFT),
    state: [texture(gl, NT + 1, TRACKER_ROWS, SF, gl.RGBA, SFT, initialState()), texture(gl, NT + 1, TRACKER_ROWS, SF, gl.RGBA, SFT, initialState())],
  };
  const F = { m1: fbo(gl, [T.mLum, T.mRed]), m2: fbo(gl, [T.cells]), gain: fbo(gl, [T.gain]), state: [fbo(gl, [T.state[0]]), fbo(gl, [T.state[1]])] };
  let cur = 0;                                           // the state texture holding the latest state
  const S = { w: 0, h: 0, pre: null, preFb: null, shown: [null, null], shownFb: [null, null], read: 0 };
  let frames = 0;
  function ensure(w, h) {
    if (S.w === w && S.h === h && S.pre) return;
    for (const t of [S.pre, ...S.shown]) if (t) gl.deleteTexture(t);
    for (const fb of [S.preFb, ...S.shownFb]) if (fb) gl.deleteFramebuffer(fb);
    S.w = w; S.h = h;
    S.pre = texture(gl, w, h, preInternal, gl.RGBA, preType);
    S.preFb = fbo(gl, [S.pre]);
    S.shown = [texture(gl, w, h, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE), texture(gl, w, h, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE)];
    S.shownFb = [fbo(gl, [S.shown[0]]), fbo(gl, [S.shown[1]])];
    for (const fb of S.shownFb) { gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT); }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }
  function bind(unit, tex) { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex); }
  function draw(fb, w, h) { gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.viewport(0, 0, w, h); gl.drawArrays(gl.TRIANGLES, 0, 3); }
  // the decision: SOLVE then STATE, from the cells texture
  function counts(u) { gl.uniform1i(u.u_nt, NT); gl.uniform1i(u.u_sweeps, LIMIT.SWEEPS); gl.uniform1i(u.u_hard, LIMIT.HARD_SWEEPS); gl.uniform1i(u.u_nc, LIMIT.CTRL * LIMIT.CTRL); }
  function decide(dt) {
    gl.useProgram(solve.prog);
    bind(0, T.cells); bind(1, T.state[cur]);
    gl.uniform1i(solve.u.u_cells, 0); gl.uniform1i(solve.u.u_state, 1); gl.uniform1f(solve.u.u_dt, dt); counts(solve.u);
    draw(F.gain, LIMIT.CTRL, LIMIT.CTRL);
    gl.useProgram(state.prog);
    bind(0, T.cells); bind(1, T.state[cur]); bind(2, T.gain);
    gl.uniform1i(state.u.u_cells, 0); gl.uniform1i(state.u.u_state, 1); gl.uniform1i(state.u.u_gain, 2); gl.uniform1f(state.u.u_dt, dt);
    counts(state.u);
    draw(F.state[1 - cur], NT + 1, TRACKER_ROWS);
    cur = 1 - cur;
  }
  return {
    full, format: full ? "RGBA32F" : "RGBA16F", parallel: !!par,
    ready: () => poll(), error: () => error, compileMs: () => compileMs,
    // the target the look draws into, and its texture
    preTarget(w, h) { ensure(w, h); return S.preFb; },
    preTexture() { return S.pre; },
    // Meter, decide and apply `src` (w x h, display values) for a frame dt seconds after the last; the result lands on
    // the canvas (the default framebuffer). False (and nothing drawn) while the programs are still compiling. mark(stage),
    // when given (the cost receipt), is called after each stage: "meter", "decide", "apply", "blit".
    run(src, w, h, dt, mark = null) {
      if (!poll()) return false;
      ensure(w, h);
      const d = Math.max(0, Math.min(0.25, Number.isFinite(dt) ? dt : 0));
      gl.useProgram(meter1.prog);
      bind(0, src);
      gl.uniform1i(meter1.u.u_src, 0); gl.uniform2i(meter1.u.u_size, w, h);
      draw(F.m1, MW, MH);
      gl.useProgram(meter2.prog);
      bind(0, T.mLum); bind(1, T.mRed);
      gl.uniform1i(meter2.u.u_lum, 0); gl.uniform1i(meter2.u.u_red, 1); gl.uniform2i(meter2.u.u_sub, MSUB_X, MSUB_Y);
      draw(F.m2, LIMIT.GRID * NSIG, LIMIT.GRID);
      if (mark) mark("meter");
      decide(d);
      if (mark) mark("decide");
      const write = 1 - S.read;
      gl.useProgram(apply.prog);
      bind(0, src); bind(1, T.gain); bind(2, S.shown[S.read]);
      gl.uniform1i(apply.u.u_src, 0); gl.uniform1i(apply.u.u_gain, 1); gl.uniform1i(apply.u.u_prev, 2);
      // the cell boundaries, as the meter computes them (B_c = floor(c n / 4)), and their inverse sizes
      const B = (n) => [0, 1, 2, 3, 4].map((c) => Math.floor((c * n) / LIMIT.GRID));
      const bx = B(w), by = B(h);
      gl.uniform4i(apply.u.u_bx, bx[0], bx[1], bx[2], bx[3]); gl.uniform4i(apply.u.u_by, by[0], by[1], by[2], by[3]);
      gl.uniform4f(apply.u.u_ix, ...[0, 1, 2, 3].map((c) => 1 / Math.max(1, bx[c + 1] - bx[c])));
      gl.uniform4f(apply.u.u_iy, ...[0, 1, 2, 3].map((c) => 1 / Math.max(1, by[c + 1] - by[c])));
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
    // Receipts: the decision alone on given cell sums (a Float32Array laid out as vj-gate.js cellIndex), as the JS twin
    // takes them. Returns what read() returns.
    decideCells(cells, dt) {
      if (!poll()) return null;
      gl.bindTexture(gl.TEXTURE_2D, T.cells);
      gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, LIMIT.GRID * NSIG, LIMIT.GRID, gl.RGBA, gl.FLOAT, cells);
      decide(Math.max(0, Math.min(0.25, dt)));
      return this.read();
    },
    // Receipts and the HUD: the state, the gains and the cells, read back (a stall: never per frame in a show).
    read() {
      if (!poll()) return { ready: false, error };
      const st = new Float32Array((NT + 1) * TRACKER_ROWS * 4), gn = new Float32Array(LIMIT.CTRL * LIMIT.CTRL * 4), ce = new Float32Array(NCELL_FLOATS);
      gl.bindFramebuffer(gl.FRAMEBUFFER, F.state[cur]); gl.readPixels(0, 0, NT + 1, TRACKER_ROWS, gl.RGBA, gl.FLOAT, st);
      gl.bindFramebuffer(gl.FRAMEBUFFER, F.gain); gl.readPixels(0, 0, LIMIT.CTRL, LIMIT.CTRL, gl.RGBA, gl.FLOAT, gn);
      gl.bindFramebuffer(gl.FRAMEBUFFER, F.m2); gl.readPixels(0, 0, LIMIT.GRID * NSIG, LIMIT.GRID, gl.RGBA, gl.FLOAT, ce);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      const tracker = (t) => { const o = []; for (let row = 0; row < TRACKER_ROWS; row++) for (let c = 0; c < 4; c++) o.push(st[(row * (NT + 1) + t) * 4 + c]); return o; };
      const trackers = []; for (let t = 0; t < NT; t++) trackers.push(tracker(t));
      const g0 = tracker(NT);
      return { ready: true, compile_ms: compileMs, trackers, run: g0[0], rest: g0[1], frames: g0[2], beta: g0[3], held: g0[4], leaks: g0[5],
               a: Array.from({ length: 25 }, (_, i) => gn[i * 4]), k: Array.from({ length: 25 }, (_, i) => gn[i * 4 + 1]),
               betaNow: gn[2], cells: Array.from(ce) };
    },
    reset() {
      for (const t of T.state) { gl.bindTexture(gl.TEXTURE_2D, t); gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, NT + 1, TRACKER_ROWS, gl.RGBA, gl.FLOAT, initialState()); }
      cur = 0;
    },
    frames: () => frames,
    dispose() {
      for (const p of [meter1, meter2, solve, state, apply]) gl.deleteProgram(p.prog);
      for (const t of [T.mLum, T.mRed, T.cells, T.gain, ...T.state, S.pre, ...S.shown]) if (t) gl.deleteTexture(t);
      for (const fb of [F.m1, F.m2, F.gain, ...F.state, S.preFb, ...S.shownFb]) if (fb) gl.deleteFramebuffer(fb);
    },
  };
}
