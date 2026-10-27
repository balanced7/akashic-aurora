// VJ air: arsenal/web/vj-fluid.js (ES module). The pure parts (constants, envelopes, the beam stirs and the CPU twin of the
// solver) are pinned in tests/vj_fluid.test.mjs; vj.js wires it in its AIR block; the page receipts are vj_storm.mjs's
// airedge and airstir storms.
//
// Daniel, 2026-10-27: "stunning laser effects through as best of a volumetric fog as we can manage", and for CO2 "combine
// it into one physics system ... a slowed down higher fidelity version" (of NVIDIA's GeForce 8 smoke, GPU Gems 3 ch. 30).
// The record: research/reviewed/keylab-liberation-2026-10-22/vj-v2-research-2026-10-27/fog-fluid.research.md and its
// check fog-fluid.check.md (the check wins where they differ); the build spec: research/in-flight/
// vj-v2-build-spec-2026-10-27.md section C, P1.
//
// WHAT. One 2D stable fluid behind the VJ page (Stam's stable fluids, with the GPU Gems 3 ch. 30 lessons): a 512 x 288 grid
// of 16-bit fields in WebGL2 fragment passes (no compute there), stepped at a fixed 60 Hz:
//   velocity  RG16F, cells per second
//   scalars   RGBA16F: haze, fog, CO2 condensate, temperature (an offset from the room's)
//   per step  the velocity rides itself (semi-Lagrangian), vorticity confinement, buoyancy (cold dense CO2 sinks, warm fog
//             lifts), the emitters, the divergence, 20 Jacobi iterations (warm-started) and the projection; then the
//             scalars ride the projected flow by MacCormack with the min/max clamp (two passes: the forward trace, then the
//             back trace fused with the combine and its clamp), each channel decaying on its own clock (haze relaxes
//             toward the hazer's level, fog hangs for seconds, CO2 condensate burns off in about a second, the cold mixes
//             away). Why the velocity is not MacCormack too: SIM.VORTICITY.
//   the light the beam layer (vj.js, linear light) is the source the air scatters: two blurred levels of it (a near halo
//             and a wide multiple-scatter fill), each through a slow exponential history so the air's light can never
//             rise faster than the FlashGate's edge, then the air pass: each CO2 jet's column drawn analytically (CO2
//             REACH_FH: the cannon the eye reads, while the grid makes the bloom), the glow of each cell in proportion to its
//             optical depth, whitening where it is intense (white-hot roots, saturated air elsewhere); the CO2 body's own
//             white light from its nozzle LEDs; a faint fog body; and the transmittance the dense bodies leave the frame
//             behind them (alpha).
// The page adds it in its composite, linear light at the screen's own place: lin = lin * mix(1, T, gain) + air * gain.
//
// SAFETY (build spec amendment 7: the air is a FLASH SOURCE). A CO2 burst and a fog push each ask the page's FlashGate at
// their onset, the same path as punch and Invert: granted, the valve opens at full strength; refused, a smaller burst
// opens slowly (REFUSED_*), which is not a flash. One onset asks once: a pad press that fires a row of jets asks for
// the row and hands each jet its answer (co2's granted), since the gate's 1/3 s gap would refuse every jet after the
// first. Everything the air shows rises no faster than the gate's edge (1/3 s,
// FlashGate.minGap): the beam light through its history (rise 10-90 % = 2.2 tau), the CO2 body through the jet's own
// travel (the twin's rise receipt), the fog body by staying under the flash line at full density. Gate v2 (vj-limiter.js)
// still judges the frame as shown, after every layer.
//
// Licence line: our own code from the published equations (Stam 1999; Fedkiw, Stam and Jensen 2001; Selle et al. 2008 and
// GPU Gems 3 ch. 30 for MacCormack with the clamp). No shader code is copied from GPU Gems, NVIDIA Flow or any WebGL demo.

export const FLUID_API = "arsenal.vj-fluid/v1";

// ------------------------------------------------------------------------------------------------- constants --
// Physics in frame heights (fh) and seconds; the passes convert to cells with the grid's height.
export const GRID = Object.freeze({
  high: Object.freeze({ W: 512, H: 288, JACOBI: 20 }),
  low: Object.freeze({ W: 256, H: 144, JACOBI: 12 }),   // ?air=low: a quarter of the cells for slow GPUs
});
export const SIM = Object.freeze({
  HZ: 60, MAX_STEPS: 2,         // a fixed tick; a slow frame drops sim time rather than spiral
  // The velocity is advected semi-Lagrangian and the confinement gives back the swirls its numerical viscosity takes
  // (Fedkiw, Stam and Jensen's own pairing); the scalars, what the eye sees, get MacCormack with the clamp. Measured on
  // the twin (2026-10-27): MacCormack on this collocated grid's velocity leaves a checkerboard divergence the projection
  // cannot see, and the fog then GAINED 25 % of its mass in the 2.5 s after a release instead of losing 30 %.
  VORTICITY: 12,                // confinement, cell units: f = eps (N x omega)
  VEL_TAU_S: 1.6,               // the air's drag
  KAPPA_CO2: 3.5,               // fh/s^2 per unit condensate: cold CO2 is ~2.3 x as dense as the room
  BETA_T: 2.0,                  // fh/s^2 per unit temperature offset (cold sinks, warm lifts)
  TAU_S: Object.freeze({ haze: 10, fog: 7, co2: 0.7, temp: 2.0 }),
  C_MAX: 2, T_MAX: 1.5,         // the scalars' clamps (condensate and fog never above 2; temperature +-1.5)
  HAZE_SCALE: 3.2,              // the hazer's texture: noise cells per frame height
  HAZE_WIND: Object.freeze([0.03, 0.008]),   // fh/s: the texture drifts
  PRESSURE_KEEP: 0.99,          // the warm start: the last step's pressure (a hair relaxed, so the Neumann constant cannot drift);
                                // at 0.9 the low modes never built up and the fog kept 10 % more mass than its clock allows
});
// Emitters. A CO2 jet: a parametric near field (cone 12 degrees, the check's "keep the near field analytic") feeding the
// grid, which carries the far field. Valve: a granted burst ramps in RAMP_S and holds HOLD_S (by strength) then closes.
export const CO2 = Object.freeze({
  U0_FH: 3.5, TAN_HALF: Math.tan(12 * Math.PI / 180), NOZZLE_FH: 0.02, NEAR_FH: 0.1, GRIP: 0.6,
  RATE: 20,                     // condensate per second at the nozzle, full valve
  COLD: -1,                     // the temperature it carries
  RAMP_S: 0.12, HOLD_S: Object.freeze([0.22, 0.6]), CLOSE_S: 0.08,
  REFUSED_SCALE: 0.4, REFUSED_RAMP_S: 0.6,   // refused by the gate: a smaller burst that opens slowly
  MAX_JETS: 4,
  // The column the eye reads as a CO2 cannon, drawn analytically in the air pass (the check: a grid cannot make a crisp
  // jet; keep the near field analytic). Its tip climbs as sqrt(t) while the valve is open (the starting jet's tip law),
  // to REACH; at the close the tail lifts off at TAIL_FH per second and the column fades in FADE_S. The grid carries
  // the bloom above it and the cold cloud that sinks.
  // RISE_S: its light comes up over this smoothstep, so the whole burst (column and bloom) rises 10-90 % in no less than
  // the gate's edge (the twin's receipt: a column over the gate's edge gave 0.25 s with the bloom, over 0.8 s 0.30 s)
  // DILUTE_FH: the width below which the column is at full density; wider, it thins as 1 / width (the flux through a
  // widening 2D cone); TIP_FH: how far its tip feathers out
  REACH_FH: 0.55, TIP_S: 0.35, TAIL_FH: 1.6, FADE_S: 0.15, COLUMN_DEPTH: 1.2, RISE_S: 1.0, DILUTE_FH: 0.035, TIP_FH: 0.15,
});
// Fog machines at the deck's two ends, aimed inward and a little up; a push is a rate while held.
export const FOG = Object.freeze({
  NOZZLES: Object.freeze([[0.03, 0.06, 20], [0.97, 0.06, 160]]),   // x01, y01, aim (degrees from +x)
  U_FH: 0.5, TAN_HALF: Math.tan(25 * Math.PI / 180), NOZZLE_FH: 0.02, NEAR_FH: 0.08, GRIP: 0.35,
  RATE: 2.5, WARM: 0.3, REFUSED_SCALE: 0.4,
});
export const MAX_EMITTERS = CO2.MAX_JETS + FOG.NOZZLES.length;
export const MAX_STIRS = 16;
export const STIR = Object.freeze({ MAX_FH: 1.2, RADIUS_FH: 0.05, GAIN: 0.35, MAX_BEAMS: 16, RATE: 8 });   // RATE: 1/s, how fast the air takes a stir's velocity
// The light. EMA_TAU_S: the air's light history (rise 10-90 % = 2.197 tau >= the gate's edge); the levels' blur; the gains.
export const LIGHT = Object.freeze({
  EMA_TAU_S: 0.18, L1: Object.freeze([256, 144]), L2: Object.freeze([128, 72]), SIGMA_TEXELS: 2.2,
  GLOW_NEAR: 4.0, GLOW_WIDE: 2.5,   // a 1-2 px beam spread over a light texel is faint: the air pass gives it back
  DEPTH: Object.freeze({ haze: 0.7, fog: 2.0, co2: 4.0 }),   // view optical depth per unit density (what scatters)
  OCCLUDE: Object.freeze({ fog: 0.8, co2: 2.5 }),           // what the dense bodies take from the frame behind them
  OCCLUDE_MIX: 0.65,
  CO2_LIGHT: 0.8,               // the CO2 body's own light (its nozzle LEDs), linear, near the deck: white
  FOG_LIGHT: 0.065,             // the fog body's room light: under the flash line at any density
  TINT: 0.3,                    // how much of the theme's LED colour the bodies take
  HOT: Object.freeze([0.35, 1.2]),   // the glow whitens between these levels (white-hot roots)
});
export const GATE_EDGE_S = 1 / 3;  // FlashGate.minGap: the fastest the air's light may rise (10-90 %)
export const FLASH_LINE = 0.1;     // WCAG 2.3.1: a change of 0.1 in relative luminance

// ------------------------------------------------------------------------------------------------- envelopes --
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
const smooth = (x) => { const t = clamp(x, 0, 1); return t * t * (3 - 2 * t); };

// A CO2 burst's plan from the gate's answer and the pad's strength (0..1).
export function co2Plan(granted, strength) {
  const s = clamp(strength, 0, 1);
  return {
    granted: !!granted,
    level: granted ? s : s * CO2.REFUSED_SCALE,
    ramp: granted ? CO2.RAMP_S : CO2.REFUSED_RAMP_S,
    hold: CO2.HOLD_S[0] + (CO2.HOLD_S[1] - CO2.HOLD_S[0]) * s,
    close: CO2.CLOSE_S,
  };
}
// The valve's opening at `age` seconds into a burst (0..level): an eased ramp, the hold, a short close.
export function valve(plan, age) {
  if (age < 0) return 0;
  const { ramp, hold, close, level } = plan;
  if (age < ramp) return level * smooth(age / ramp);
  if (age < ramp + hold) return level;
  return level * (1 - smooth((age - ramp - hold) / close));
}
export const burstLength = (plan) => plan.ramp + plan.hold + plan.close;
// The column at `age`: { tip, tail } in frame heights above the nozzle and its level (0 when gone).
export function jetColumn(plan, age) {
  if (age < 0) return { tip: 0, tail: 0, level: 0 };
  const tip = CO2.REACH_FH * Math.min(1, Math.sqrt(age / CO2.TIP_S)), open = plan.ramp + plan.hold;
  // its light comes up over RISE_S whatever the valve does (a smoothstep's 10-90 % is 0.608 of its span)
  const rise = (a) => smooth(a / CO2.RISE_S);
  if (age < open) return { tip, tail: 0, level: valve(plan, age) * rise(age) };
  const tc = age - open;
  return { tip, tail: Math.min(tip, CO2.TAIL_FH * tc), level: tc > 4 * CO2.FADE_S ? 0 : plan.level * rise(open) * Math.exp(-tc / CO2.FADE_S) };
}
// The column's density at (dx, dy) frame heights from its nozzle (dy up): a cone of the jet's half-angle, soft at its
// tail and tip. The air pass computes the same.
export function columnDensity(col, dx, dy) {
  if (col.level <= 0 || dy < col.tail - 0.03 || dy > col.tip) return 0;
  const half = CO2.NOZZLE_FH + Math.max(0, dy) * CO2.TAN_HALF, a = dx / half;
  return col.level * Math.min(1, CO2.DILUTE_FH / half) * Math.exp(-a * a) * smooth((dy - col.tail + 0.03) / 0.03) *
         (1 - smooth((dy - col.tip + CO2.TIP_FH) / CO2.TIP_FH));
}

// The air's light history: k for one frame of dt, and the 10-90 % rise time of a step through it.
export const emaK = (dt, tau = LIGHT.EMA_TAU_S) => 1 - Math.exp(-Math.max(0, dt) / tau);
export const emaRise = (tau = LIGHT.EMA_TAU_S) => tau * Math.log(9);
// The ripple a square wave of `hz` (full on / off) leaves through the history, as a fraction of its amplitude.
export const emaRipple = (hz, tau = LIGHT.EMA_TAU_S) => Math.tanh(1 / (4 * hz * tau));

// The beams' motion as stirs: for each beam drawn now and last frame (the same row, the same source within 1 % of the
// frame height: the laser engine keeps a head's rows in order), its tip's travel pushes the air at three points along it.
// seg: vj-lasers.js records (texel 0 = x0, y0, x1, y1 in centred units: frame heights about the centre); asp: width /
// height. Returns stirs in screen 0..1 with velocities in fh/s, capped (STIR.MAX_FH), at most STIR.MAX_BEAMS beams.
export function beamStirs(prev, prevN, seg, n, dt, asp, floats = 8, groupMark = 1000) {
  const out = [];
  if (!prev || !seg || dt <= 0) return out;
  const rows = Math.min(n, prevN);
  for (let i = 0; i < rows && out.length < STIR.MAX_BEAMS * 3; i++) {
    const o = i * floats;
    if (seg[o + 3] >= groupMark - 0.5 || prev[o + 3] >= groupMark - 0.5) continue;   // a figure's header
    const same = Math.abs(seg[o] - prev[o]) < 0.01 && Math.abs(seg[o + 1] - prev[o + 1]) < 0.01;
    if (!same) continue;
    let vx = (seg[o + 2] - prev[o + 2]) / dt, vy = (seg[o + 3] - prev[o + 3]) / dt;
    const sp = Math.hypot(vx, vy);
    if (sp < 1e-4) continue;
    const cap = Math.min(1, STIR.MAX_FH / sp) * STIR.GAIN;
    vx *= cap; vy *= cap;
    for (const u of [0.35, 0.65, 0.95]) {
      const x = seg[o] + (seg[o + 2] - seg[o]) * u, y = seg[o + 1] + (seg[o + 3] - seg[o + 1]) * u;
      out.push({ x: x / asp + 0.5, y: y + 0.5, vx: vx * u, vy: vy * u, r: STIR.RADIUS_FH });
    }
  }
  return out;
}

// --------------------------------------------------------------------------------------------- the emitters --
// The emitters of one step, in cells: { x, y, dx, dy, level, u0, tan, r0, near, grip, rate, channel (1 fog, 2 CO2), temp }.
export function emitterCells(list, W, H) {
  return list.map((e) => ({ ...e, x: e.x01 * W, y: e.y01 * H, u0: e.u0Fh * H, r0: e.r0Fh * H, near: e.nearFh * H }));
}
export function co2Emitter(x01, y01, level) {
  return { x01, y01, dx: 0, dy: 1, level, u0Fh: CO2.U0_FH, tan: CO2.TAN_HALF, r0Fh: CO2.NOZZLE_FH, nearFh: CO2.NEAR_FH,
           grip: CO2.GRIP, rate: CO2.RATE, channel: 2, temp: CO2.COLD };
}
export function fogEmitters(level) {
  return FOG.NOZZLES.map(([x01, y01, deg]) => ({ x01, y01, dx: Math.cos(deg * Math.PI / 180), dy: Math.sin(deg * Math.PI / 180),
    level, u0Fh: FOG.U_FH, tan: FOG.TAN_HALF, r0Fh: FOG.NOZZLE_FH, nearFh: FOG.NEAR_FH, grip: FOG.GRIP, rate: FOG.RATE,
    channel: 1, temp: FOG.WARM }));
}
// The near field's weight at a cell (cell units): a cone from the nozzle along (dx, dy), soft at its ends.
export function emitterWeight(e, px, py) {
  const rx = px - e.x, ry = py - e.y;
  const along = rx * e.dx + ry * e.dy;
  const ax = rx - along * e.dx, ay = ry - along * e.dy;
  const half = e.r0 + Math.max(0, along) * e.tan;
  const across = Math.hypot(ax, ay) / Math.max(half, 1e-3);
  const ends = smooth((along + e.r0) / e.r0) * (1 - smooth((along - 0.7 * e.near) / (0.3 * e.near)));
  return e.level * Math.exp(-across * across) * ends;
}

// The hazer's texture: our own value noise on a 32-bit integer hash, written so the GLSL below computes the same numbers.
export function hashU(x, y) {
  let h = (Math.imul(x >>> 0, 0x8da6b343) ^ Math.imul(y >>> 0, 0xd8163841)) >>> 0;
  h = Math.imul(h ^ (h >>> 15), 0x2c1b3c6d) >>> 0;
  h = Math.imul(h ^ (h >>> 12), 0x297a2d39) >>> 0;
  return (h ^ (h >>> 15)) >>> 0;
}
export function valueNoise(x, y) {
  const ix = Math.floor(x), iy = Math.floor(y);
  let fx = x - ix, fy = y - iy;
  fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
  const h = (i, j) => hashU(ix + i, iy + j) / 4294967295;
  const a = h(0, 0) + (h(1, 0) - h(0, 0)) * fx, b = h(0, 1) + (h(1, 1) - h(0, 1)) * fx;
  return a + (b - a) * fy;
}
// The haze the hazers hold a cell at (level 0..1): the room's level, textured, drifting with the wind.
export function hazeTarget(level, xFh, yFh, t) {
  const n = valueNoise(xFh * SIM.HAZE_SCALE + SIM.HAZE_WIND[0] * t * SIM.HAZE_SCALE, yFh * SIM.HAZE_SCALE + SIM.HAZE_WIND[1] * t * SIM.HAZE_SCALE);
  return level * (0.55 + 0.9 * n);
}

// ------------------------------------------------------------------------------------------------ the twin --
// The scalars the room outside the box does not carry (haze, fog, CO2, temperature): the haze relaxes to its level anyway.
export const OPEN = Object.freeze([0, 1, 1, 1]);
// The CPU twin of the GPU step, pass for pass (the same traces, clamps, ghosts and constants), on a small grid: the
// physics receipts run on it (projection, the clamp's bounds, CO2 rising then sinking and burning off, fog hanging).
export class FluidTwin {
  constructor(W, H, { jacobi = GRID.high.JACOBI, keep = SIM.PRESSURE_KEEP } = {}) {
    this.W = W; this.H = H; this.jacobi = jacobi; this.keep = keep;
    const n = W * H, f = () => new Float32Array(n);
    this.u = f(); this.v = f(); this.u2 = f(); this.v2 = f();
    this.s = [f(), f(), f(), f()]; this.sT = [f(), f(), f(), f()]; this.s2 = [f(), f(), f(), f()];
    this.p = f(); this.p2 = f(); this.div = f(); this.curl = f();
    this.t = 0; this.haze = 0;
  }
  idx(i, j) { return j * this.W + i; }
  // bilinear at cell coordinates (centres at i + 0.5), clamped to the edge as CLAMP_TO_EDGE does
  sample(F, x, y) {
    const W = this.W, H = this.H;
    x = clamp(x, 0.5, W - 0.5) - 0.5; y = clamp(y, 0.5, H - 0.5) - 0.5;
    const i0 = Math.floor(x), j0 = Math.floor(y), i1 = Math.min(i0 + 1, W - 1), j1 = Math.min(j0 + 1, H - 1);
    const tx = x - i0, ty = y - j0;
    const a = F[j0 * W + i0] + (F[j0 * W + i1] - F[j0 * W + i0]) * tx;
    const b = F[j1 * W + i0] + (F[j1 * W + i1] - F[j1 * W + i0]) * tx;
    return a + (b - a) * ty;
  }
  // the 4 nodes about a trace point: [min, max] of F there
  bounds(F, x, y) {
    const W = this.W, H = this.H;
    x = clamp(x, 0.5, W - 0.5); y = clamp(y, 0.5, H - 0.5);
    const i0 = Math.floor(x - 0.5), j0 = Math.floor(y - 0.5), i1 = Math.min(i0 + 1, W - 1), j1 = Math.min(j0 + 1, H - 1);
    const a = F[j0 * W + i0], b = F[j0 * W + i1], c = F[j1 * W + i0], d = F[j1 * W + i1];
    return [Math.min(a, b, c, d), Math.max(a, b, c, d)];
  }
  // velocity at a cell with the walls' free-slip ghosts (the normal component mirrored)
  velAt(i, j) {
    const W = this.W, H = this.H, k = clamp(j, 0, H - 1) * W + clamp(i, 0, W - 1);
    let u = this.u[k], v = this.v[k];
    if (i < 0 || i > W - 1) u = -u;
    if (j < 0 || j > H - 1) v = -v;
    return [u, v];
  }
  // MacCormack, fused: pass 1 traced every field forward into `hat`; pass 2 traces back, combines and clamps. `open`
  // marks the fields the room outside the box does not carry (fog, CO2, the temperature offset): a trace that starts
  // outside brings clean air, where clamping to the edge would copy the wall's cell inward and make mass from nothing.
  advect(fields, hats, outs, dt, vel = [this.u, this.v], open = null) {
    const W = this.W, H = this.H, [U, V] = vel;
    const inside = (x, y) => (x >= 0 && x <= W && y >= 0 && y <= H ? 1 : 0);
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, px = i + 0.5, py = j + 0.5, qx = px - dt * U[k], qy = py - dt * V[k], o = inside(qx, qy);
      for (let f = 0; f < fields.length; f++) hats[f][k] = this.sample(fields[f], qx, qy) * (open && open[f] ? o : 1);
    }
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, px = i + 0.5, py = j + 0.5, qx = px - dt * U[k], qy = py - dt * V[k], o = inside(qx, qy);
      for (let f = 0; f < fields.length; f++) {
        const back = this.sample(hats[f], px + dt * U[k], py + dt * V[k]);
        const r = hats[f][k] + 0.5 * (fields[f][k] - back);
        const [lo, hi] = this.bounds(fields[f], qx, qy);
        outs[f][k] = clamp(r, lo, hi) * (open && open[f] ? o : 1);
      }
    }
  }
  step(dt, { emitters = [], stirs = [], haze = this.haze } = {}) {
    const W = this.W, H = this.H, n = W * H;
    this.haze = haze;
    const em = emitterCells(emitters, W, H);
    // 1. the velocity rides itself, semi-Lagrangian (see SIM.VORTICITY for why not MacCormack)
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, qx = i + 0.5 - dt * this.u[k], qy = j + 0.5 - dt * this.v[k];
      this.u2[k] = this.sample(this.u, qx, qy); this.v2[k] = this.sample(this.v, qx, qy);
    }
    this.u.set(this.u2); this.v.set(this.v2);
    // 2. the curl, then the forces: confinement, buoyancy, stirs, drag, the emitters' grip
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const r = this.velAt(i + 1, j), l = this.velAt(i - 1, j), t = this.velAt(i, j + 1), b = this.velAt(i, j - 1);
      this.curl[j * W + i] = 0.5 * ((r[1] - l[1]) - (t[0] - b[0]));
    }
    const C = (i, j) => Math.abs(this.curl[clamp(j, 0, H - 1) * W + clamp(i, 0, W - 1)]);
    const drag = Math.exp(-dt / SIM.VEL_TAU_S);
    const kappa = SIM.KAPPA_CO2 * H, beta = SIM.BETA_T * H;
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, px = i + 0.5, py = j + 0.5, w = this.curl[k];
      let ex = 0.5 * (C(i + 1, j) - C(i - 1, j)), ey = 0.5 * (C(i, j + 1) - C(i, j - 1));
      const el = Math.hypot(ex, ey) + 1e-5; ex /= el; ey /= el;
      let u = this.u[k] + dt * SIM.VORTICITY * ey * w;
      let v = this.v[k] + dt * (-SIM.VORTICITY * ex * w - kappa * this.s[2][k] + beta * this.s[3][k]);
      for (const s of stirs) {
        const dx = px - s.x * W, dy = py - s.y * H, rr = s.r * H, g = Math.exp(-(dx * dx + dy * dy) / (rr * rr));
        u += s.vx * H * g * dt * STIR.RATE; v += s.vy * H * g * dt * STIR.RATE;
      }
      u *= drag; v *= drag;
      for (const e of em) {
        const g = clamp(emitterWeight(e, px, py) * e.grip, 0, 1);
        u += (e.u0 * e.dx - u) * g; v += (e.u0 * e.dy - v) * g;
      }
      this.u2[k] = u; this.v2[k] = v;
    }
    this.u.set(this.u2); this.v.set(this.v2);
    // 3. the divergence, the pressure (warm-started Jacobi, Neumann walls), the projection and the walls
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const r = this.velAt(i + 1, j), l = this.velAt(i - 1, j), t = this.velAt(i, j + 1), b = this.velAt(i, j - 1);
      this.div[j * W + i] = 0.5 * ((r[0] - l[0]) + (t[1] - b[1]));
    }
    for (let k = 0; k < n; k++) this.p[k] *= this.keep;
    for (let it = 0; it < this.jacobi; it++) {
      const P = this.p, Q = this.p2;
      for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
        const at = (a, b) => P[clamp(b, 0, H - 1) * W + clamp(a, 0, W - 1)];
        Q[j * W + i] = 0.25 * (at(i - 1, j) + at(i + 1, j) + at(i, j - 1) + at(i, j + 1) - this.div[j * W + i]);
      }
      this.p = Q; this.p2 = P;
    }
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const at = (a, b) => this.p[clamp(b, 0, H - 1) * W + clamp(a, 0, W - 1)], k = j * W + i;
      let u = this.u[k] - 0.5 * (at(i + 1, j) - at(i - 1, j)), v = this.v[k] - 0.5 * (at(i, j + 1) - at(i, j - 1));
      if (i === 0) u = Math.max(u, 0); if (i === W - 1) u = Math.min(u, 0);
      if (j === 0) v = Math.max(v, 0); if (j === H - 1) v = Math.min(v, 0);
      this.u2[k] = u; this.v2[k] = v;
    }
    this.u.set(this.u2); this.v.set(this.v2);
    // 4. the scalars ride the projected flow, decay on their own clocks, and take the emitters
    this.advect(this.s, this.sT, this.s2, dt, [this.u, this.v], OPEN);
    const dh = 1 - Math.exp(-dt / SIM.TAU_S.haze), df = Math.exp(-dt / SIM.TAU_S.fog), dc = Math.exp(-dt / SIM.TAU_S.co2),
          dT = Math.exp(-dt / SIM.TAU_S.temp);
    const tNow = this.t + dt;
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i, px = i + 0.5, py = j + 0.5;
      let h = this.s2[0][k], f = this.s2[1][k] * df, c = this.s2[2][k] * dc, T = this.s2[3][k] * dT;
      h += (hazeTarget(haze, px / H, py / H, tNow) - h) * dh;
      for (const e of em) {
        const w = emitterWeight(e, px, py);
        if (e.channel === 1) f += dt * e.rate * w; else c += dt * e.rate * w;
        T += (e.temp - T) * clamp(w * e.grip, 0, 1);
      }
      this.s[0][k] = clamp(h, 0, SIM.C_MAX); this.s[1][k] = clamp(f, 0, SIM.C_MAX);
      this.s[2][k] = clamp(c, 0, SIM.C_MAX); this.s[3][k] = clamp(T, -SIM.T_MAX, SIM.T_MAX);
    }
    this.t = tNow;
  }
  total(ch) { let s = 0; for (const x of this.s[ch]) s += x; return s; }
  // the centre of mass of a channel, in frame heights from the floor (null when empty)
  heightOf(ch) { let m = 0, my = 0; const F = this.s[ch], W = this.W, H = this.H; for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) { m += F[j * W + i]; my += F[j * W + i] * (j + 0.5); } return m > 1e-9 ? my / m / H : null; }
  maxDiv() { let m = 0; for (let j = 0; j < this.H; j++) for (let i = 0; i < this.W; i++) { const r = this.velAt(i + 1, j), l = this.velAt(i - 1, j), t = this.velAt(i, j + 1), b = this.velAt(i, j - 1); m = Math.max(m, Math.abs(0.5 * ((r[0] - l[0]) + (t[1] - b[1])))); } return m; }
}

// The bodies' own light at a cell (linear, the luminance the air pass draws without beams): the twin of the air pass's
// body term, for the flash receipts. y01: the cell's height on the screen (the LEDs sit at the deck).
export function bodyLight(fog, co2, y01) {
  const aC = 1 - Math.exp(-LIGHT.DEPTH.co2 * co2), aF = 1 - Math.exp(-LIGHT.DEPTH.fog * fog);
  return aC * LIGHT.CO2_LIGHT * (1 - 0.55 * clamp(y01, 0, 1)) + aF * LIGHT.FOG_LIGHT;
}

// ------------------------------------------------------------------------------------------------- the GLSL --
const VS = `#version 300 es
precision highp float;
out vec2 v_uv;
void main() {
  vec2 pos[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
  vec2 p = pos[gl_VertexID];
  v_uv = (p + 1.0) * 0.5;
  gl_Position = vec4(p, 0.0, 1.0);
}`;
const f1 = (x) => (Number.isInteger(x) ? `${x}.0` : String(x));
const HEAD = `#version 300 es
precision highp float;
precision highp int;
uniform vec2 u_grid;
uniform float u_dt;
out vec4 outColor;
// bilinear at cell coordinates (centres at i + 0.5), clamped to the edge (the twin's sample)
vec4 sampleF(sampler2D t, vec2 pc) { return texture(t, clamp(pc, vec2(0.5), u_grid - 0.5) / u_grid); }
ivec2 cellOf() { return ivec2(gl_FragCoord.xy); }
ivec2 clampCell(ivec2 c) { return clamp(c, ivec2(0), ivec2(u_grid) - 1); }
`;
// velocity with the walls' free-slip ghosts (the twin's velAt)
const VEL_AT = `
uniform sampler2D u_vel;
vec2 velAt(ivec2 c) {
  ivec2 mx = ivec2(u_grid) - 1;
  vec2 v = texelFetch(u_vel, clamp(c, ivec2(0), mx), 0).xy;
  if (c.x < 0 || c.x > mx.x) v.x = -v.x;
  if (c.y < 0 || c.y > mx.y) v.y = -v.y;
  return v;
}`;
// pass 1: the forward semi-Lagrangian trace of any field
const OPEN_AT = `
uniform vec4 u_open;     // the channels the room outside the box does not carry (the twin's OPEN)
vec4 openAt(vec2 q) { float o = (q.x >= 0.0 && q.x <= u_grid.x && q.y >= 0.0 && q.y <= u_grid.y) ? 1.0 : 0.0; return mix(vec4(1.0), vec4(o), u_open); }`;
const ADVECT1_FS = `${HEAD}
uniform sampler2D u_vel, u_src;
${OPEN_AT}
void main() {
  vec2 p = gl_FragCoord.xy;
  vec2 q = p - u_dt * texelFetch(u_vel, cellOf(), 0).xy;
  outColor = sampleF(u_src, q) * openAt(q);
}`;
// pass 2: the back trace, the combine and the clamp to the four nodes about the forward trace point
const MACCORMACK = `
vec4 macCormack(sampler2D phi, sampler2D hat, vec2 vel) {
  vec2 p = gl_FragCoord.xy;
  vec2 q = clamp(p - u_dt * vel, vec2(0.5), u_grid - 0.5);
  vec4 r = texelFetch(hat, cellOf(), 0) + 0.5 * (texelFetch(phi, cellOf(), 0) - sampleF(hat, p + u_dt * vel));
  ivec2 b = ivec2(floor(q - 0.5));
  vec4 a = texelFetch(phi, clampCell(b), 0), c = texelFetch(phi, clampCell(b + ivec2(1, 0)), 0);
  vec4 d = texelFetch(phi, clampCell(b + ivec2(0, 1)), 0), e = texelFetch(phi, clampCell(b + ivec2(1, 1)), 0);
  return clamp(r, min(min(a, c), min(d, e)), max(max(a, c), max(d, e)));
}`;

// the emitters (the twin's emitterWeight): u_em = (x, y, dx, dy) cells; u_emA = (level, u0, tan, r0); u_emB = (near,
// grip, rate, channel); u_emT = temperature
const EMITTERS = `
uniform vec4 u_em[${MAX_EMITTERS}];
uniform vec4 u_emA[${MAX_EMITTERS}];
uniform vec4 u_emB[${MAX_EMITTERS}];
uniform float u_emT[${MAX_EMITTERS}];
float sm(float x) { float t = clamp(x, 0.0, 1.0); return t * t * (3.0 - 2.0 * t); }
float emitterWeight(int k, vec2 p) {
  vec4 e = u_em[k], a = u_emA[k];
  vec2 rel = p - e.xy;
  float along = dot(rel, e.zw);
  vec2 ax = rel - along * e.zw;
  float half_ = a.w + max(0.0, along) * a.z;
  float across = length(ax) / max(half_, 1e-3);
  float near = u_emB[k].x;
  float ends = sm((along + a.w) / a.w) * (1.0 - sm((along - 0.7 * near) / (0.3 * near)));
  return a.x * exp(-across * across) * ends;
}`;
const CURL_FS = `${HEAD}
${VEL_AT}
void main() {
  ivec2 c = cellOf();
  float w = 0.5 * ((velAt(c + ivec2(1, 0)).y - velAt(c - ivec2(1, 0)).y) - (velAt(c + ivec2(0, 1)).x - velAt(c - ivec2(0, 1)).x));
  outColor = vec4(w, 0.0, 0.0, 1.0);
}`;
const FORCE_FS = `${HEAD}
${VEL_AT}
${EMITTERS}
uniform sampler2D u_curl, u_scal;
uniform vec4 u_stir[${MAX_STIRS}];     // x, y (cells), vx, vy (cells/s)
uniform float u_stirR[${MAX_STIRS}];   // radius (cells); 0 = none
uniform float u_drag, u_kappa, u_beta;
float C(ivec2 c) { return abs(texelFetch(u_curl, clampCell(c), 0).r); }
void main() {
  ivec2 c = cellOf();
  vec2 p = gl_FragCoord.xy;
  float w = texelFetch(u_curl, c, 0).r;
  vec2 eta = 0.5 * vec2(C(c + ivec2(1, 0)) - C(c - ivec2(1, 0)), C(c + ivec2(0, 1)) - C(c - ivec2(0, 1)));
  eta /= length(eta) + 1e-5;
  vec4 s = texelFetch(u_scal, c, 0);
  vec2 v = texelFetch(u_vel, c, 0).xy;
  v += u_dt * vec2(${f1(SIM.VORTICITY)} * eta.y * w, -${f1(SIM.VORTICITY)} * eta.x * w - u_kappa * s.b + u_beta * s.a);
  for (int k = 0; k < ${MAX_STIRS}; k++) {
    float rr = u_stirR[k];
    if (rr <= 0.0) continue;
    vec2 d = p - u_stir[k].xy;
    v += u_stir[k].zw * exp(-dot(d, d) / (rr * rr)) * u_dt * ${f1(STIR.RATE)};
  }
  v *= u_drag;
  for (int k = 0; k < ${MAX_EMITTERS}; k++) {
    if (u_emA[k].x <= 0.0) continue;
    float g = clamp(emitterWeight(k, p) * u_emB[k].y, 0.0, 1.0);
    v += (u_emA[k].y * u_em[k].zw - v) * g;
  }
  outColor = vec4(v, 0.0, 1.0);
}`;
const DIV_FS = `${HEAD}
${VEL_AT}
void main() {
  ivec2 c = cellOf();
  outColor = vec4(0.5 * ((velAt(c + ivec2(1, 0)).x - velAt(c - ivec2(1, 0)).x) + (velAt(c + ivec2(0, 1)).y - velAt(c - ivec2(0, 1)).y)), 0.0, 0.0, 1.0);
}`;
const JACOBI_FS = `${HEAD}
uniform sampler2D u_p, u_div;
uniform float u_keep;   // the warm start's relaxation (first iteration only; 1 after)
float P(ivec2 c) { return texelFetch(u_p, clampCell(c), 0).r; }
void main() {
  ivec2 c = cellOf();
  float s = P(c + ivec2(-1, 0)) + P(c + ivec2(1, 0)) + P(c + ivec2(0, -1)) + P(c + ivec2(0, 1));
  outColor = vec4(0.25 * (u_keep * s - texelFetch(u_div, c, 0).r), 0.0, 0.0, 1.0);
}`;
const PROJECT_FS = `${HEAD}
uniform sampler2D u_vel, u_p;
float P(ivec2 c) { return texelFetch(u_p, clampCell(c), 0).r; }
void main() {
  ivec2 c = cellOf(), mx = ivec2(u_grid) - 1;
  vec2 v = texelFetch(u_vel, c, 0).xy - 0.5 * vec2(P(c + ivec2(1, 0)) - P(c - ivec2(1, 0)), P(c + ivec2(0, 1)) - P(c - ivec2(0, 1)));
  if (c.x == 0) v.x = max(v.x, 0.0);
  if (c.x == mx.x) v.x = min(v.x, 0.0);
  if (c.y == 0) v.y = max(v.y, 0.0);
  if (c.y == mx.y) v.y = min(v.y, 0.0);
  outColor = vec4(v, 0.0, 1.0);
}`;
// the hazer's texture (the twin's hashU / valueNoise / hazeTarget)
const NOISE = `
uint hashU(uvec2 q) {
  uint h = (q.x * 0x8da6b343u) ^ (q.y * 0xd8163841u);
  h = (h ^ (h >> 15)) * 0x2c1b3c6du;
  h = (h ^ (h >> 12)) * 0x297a2d39u;
  return h ^ (h >> 15);
}
float h01(ivec2 c) { return float(hashU(uvec2(c))) / 4294967295.0; }
float valueNoise(vec2 x) {
  ivec2 i = ivec2(floor(x));
  vec2 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  float a = mix(h01(i), h01(i + ivec2(1, 0)), f.x), b = mix(h01(i + ivec2(0, 1)), h01(i + ivec2(1, 1)), f.x);
  return mix(a, b, f.y);
}`;
const ADVECT2_SCAL_FS = `${HEAD}
uniform sampler2D u_vel, u_scal, u_hat;
uniform vec4 u_decay;    // haze relax k, fog, CO2 and temperature keep factors
uniform float u_haze, u_time;
${MACCORMACK}
${EMITTERS}
${NOISE}
${OPEN_AT}
void main() {
  vec2 p = gl_FragCoord.xy;
  vec2 vel = texelFetch(u_vel, cellOf(), 0).xy;
  vec4 s = macCormack(u_scal, u_hat, vel) * openAt(p - u_dt * vel);
  s.gba *= u_decay.yzw;
  vec2 fh = p / u_grid.y;
  vec2 drift = vec2(${f1(SIM.HAZE_WIND[0])}, ${f1(SIM.HAZE_WIND[1])}) * u_time;
  float target = u_haze * (0.55 + 0.9 * valueNoise((fh + drift) * ${f1(SIM.HAZE_SCALE)}));
  s.r += (target - s.r) * u_decay.x;
  for (int k = 0; k < ${MAX_EMITTERS}; k++) {
    if (u_emA[k].x <= 0.0) continue;
    float w = emitterWeight(k, p);
    if (u_emB[k].w < 1.5) s.g += u_dt * u_emB[k].z * w; else s.b += u_dt * u_emB[k].z * w;
    s.a += (u_emT[k] - s.a) * clamp(w * u_emB[k].y, 0.0, 1.0);
  }
  outColor = vec4(clamp(s.rgb, 0.0, ${f1(SIM.C_MAX)}), clamp(s.a, -${f1(SIM.T_MAX)}, ${f1(SIM.T_MAX)}));
}`;
// The light. Down: the beam layer to the first level (16 bilinear taps over each output texel's footprint); the second
// level from the first (4 taps).
const DOWN_FS = (taps) => `#version 300 es
precision highp float;
uniform sampler2D u_src;
uniform vec2 u_out;
uniform float u_gain;
out vec4 outColor;
void main() {
  vec2 base = (floor(gl_FragCoord.xy) + 0.5) / u_out;
  vec3 s = vec3(0.0);
  for (int j = 0; j < ${taps}; j++) for (int i = 0; i < ${taps}; i++) {
    vec2 o = (vec2(float(i), float(j)) + 0.5) / ${f1(taps)} - 0.5;
    s += texture(u_src, base + o / u_out).rgb;
  }
  outColor = vec4(s * (u_gain / ${f1(taps * taps)}), 1.0);
}`;
// a 9-tap Gaussian, one axis; the vertical pass also runs the history: out = mix(prev, blurred, k)
const gauss = (() => { const w = []; let sum = 0; for (let k = -4; k <= 4; k++) { const x = Math.exp(-(k * k) / (2 * LIGHT.SIGMA_TEXELS ** 2)); w.push(x); sum += x; } return w.map((x) => x / sum); })();
const BLUR_FS = (ema) => `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_src${ema ? ", u_prev" : ""};
uniform ivec2 u_axis;
${ema ? "uniform float u_k;" : ""}
out vec4 outColor;
const float W[9] = float[9](${gauss.map((x) => x.toFixed(6)).join(", ")});
void main() {
  ivec2 c = ivec2(gl_FragCoord.xy), mx = textureSize(u_src, 0) - 1;
  vec3 s = vec3(0.0);
  for (int k = 0; k < 9; k++) s += W[k] * texelFetch(u_src, clamp(c + u_axis * (k - 4), ivec2(0), mx), 0).rgb;
  ${ema ? "s = mix(texelFetch(u_prev, c, 0).rgb, s, u_k);" : ""}
  outColor = vec4(s, 1.0);
}`;
// The air: glow from the light levels in proportion to each cell's optical depth (whitening where it is intense), the
// bodies' own light, and the transmittance they leave the frame behind them (alpha).
const AIR_FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_scal, u_l1, u_l2;
uniform vec3 u_tint;
uniform vec4 u_col[${CO2.MAX_JETS}];   // the CO2 columns (the twin's jetColumn): nozzle x01, y01, tip, tail (fh)
uniform float u_colL[${CO2.MAX_JETS}]; // their levels (0 = none)
uniform float u_asp;                   // the grid's width over its height
in vec2 v_uv;
out vec4 outColor;
float sm(float x) { float t = clamp(x, 0.0, 1.0); return t * t * (3.0 - 2.0 * t); }
// the twin's columnDensity
float column(int k) {
  vec4 c = u_col[k];
  float dx = (v_uv.x - c.x) * u_asp, dy = v_uv.y - c.y;
  if (dy < c.w - 0.03 || dy > c.z) return 0.0;
  float half_ = ${f1(CO2.NOZZLE_FH)} + max(0.0, dy) * ${CO2.TAN_HALF.toFixed(6)}, a = dx / half_;
  return u_colL[k] * min(1.0, ${f1(CO2.DILUTE_FH)} / half_) * exp(-a * a) * sm((dy - c.w + 0.03) / 0.03) *
         (1.0 - sm((dy - c.z + ${f1(CO2.TIP_FH)}) / ${f1(CO2.TIP_FH)}));
}
void main() {
  vec4 s = texelFetch(u_scal, ivec2(gl_FragCoord.xy), 0);
  float jet = 0.0;
  for (int k = 0; k < ${CO2.MAX_JETS}; k++) if (u_colL[k] > 0.0) jet += column(k);
  s.b += ${f1(CO2.COLUMN_DEPTH)} * jet;
  float tau = ${f1(LIGHT.DEPTH.haze)} * s.r + ${f1(LIGHT.DEPTH.fog)} * s.g + ${f1(LIGHT.DEPTH.co2)} * s.b;
  vec3 E = ${f1(LIGHT.GLOW_NEAR)} * texture(u_l1, v_uv).rgb + ${f1(LIGHT.GLOW_WIDE)} * texture(u_l2, v_uv).rgb;
  vec3 glow = (1.0 - exp(-tau)) * E;
  float pk = max(glow.r, max(glow.g, glow.b));
  glow = mix(glow, vec3(pk), 0.6 * smoothstep(${f1(LIGHT.HOT[0])}, ${f1(LIGHT.HOT[1])}, pk));
  vec3 led = mix(vec3(1.0), u_tint / max(max(u_tint.r, max(u_tint.g, u_tint.b)), 1e-3), ${f1(LIGHT.TINT)});
  float aC = 1.0 - exp(-${f1(LIGHT.DEPTH.co2)} * s.b), aF = 1.0 - exp(-${f1(LIGHT.DEPTH.fog)} * s.g);
  vec3 body = led * (aC * ${f1(LIGHT.CO2_LIGHT)} * (1.0 - 0.55 * v_uv.y) + aF * ${f1(LIGHT.FOG_LIGHT)});
  float T = exp(-(${f1(LIGHT.OCCLUDE.co2)} * s.b + ${f1(LIGHT.OCCLUDE.fog)} * s.g));
  outColor = vec4(glow + body, mix(1.0, T, ${f1(LIGHT.OCCLUDE_MIX)}));
}`;

// ------------------------------------------------------------------------------------------------ the GL side --
function compile(gl, type, src) {
  const sh = gl.createShader(type);
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) { const log = gl.getShaderInfoLog(sh); gl.deleteShader(sh); throw new Error(`vj-fluid shader: ${log}`); }
  return sh;
}
function program(gl, vs, fsSrc, names) {
  const fs = compile(gl, gl.FRAGMENT_SHADER, fsSrc);
  const p = gl.createProgram();
  gl.attachShader(p, vs); gl.attachShader(p, fs); gl.linkProgram(p);
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(`vj-fluid link: ${gl.getProgramInfoLog(p)}`);
  const u = {};
  for (const n of names) u[n] = gl.getUniformLocation(p, n);
  return { p, u };
}

// Attach the air to the page's WebGL2 context. ctx: { gl, gate (the page's FlashGate), live () => bool (gate v2 running:
// in the safe mode every onset is refused), now () => seconds, quality "high" | "low", haze 0..1 (the room's level at
// the start) }. Throws when the context cannot render 16-bit float targets (the page then runs without air and says so).
export function attachFluid(ctx) {
  const gl = ctx.gl;
  if (!gl.getExtension("EXT_color_buffer_float")) throw new Error("vj-fluid: EXT_color_buffer_float unavailable (16-bit float targets)");
  const Q = GRID[ctx.quality === "low" ? "low" : "high"];
  const W = Q.W, H = Q.H;
  const vs = compile(gl, gl.VERTEX_SHADER, VS);
  const EM = ["u_em", "u_emA", "u_emB", "u_emT"];
  const P = {
    adv1: program(gl, vs, ADVECT1_FS, ["u_grid", "u_dt", "u_vel", "u_src", "u_open"]),
    adv2s: program(gl, vs, ADVECT2_SCAL_FS, ["u_grid", "u_dt", "u_vel", "u_scal", "u_hat", "u_decay", "u_haze", "u_time", "u_open", ...EM]),
    curl: program(gl, vs, CURL_FS, ["u_grid", "u_dt", "u_vel"]),
    force: program(gl, vs, FORCE_FS, ["u_grid", "u_dt", "u_vel", "u_curl", "u_scal", "u_stir", "u_stirR", "u_drag", "u_kappa", "u_beta", ...EM]),
    div: program(gl, vs, DIV_FS, ["u_grid", "u_dt", "u_vel"]),
    jac: program(gl, vs, JACOBI_FS, ["u_grid", "u_dt", "u_p", "u_div", "u_keep"]),
    proj: program(gl, vs, PROJECT_FS, ["u_grid", "u_dt", "u_vel", "u_p"]),
    down16: program(gl, vs, DOWN_FS(4), ["u_src", "u_out", "u_gain"]),
    down4: program(gl, vs, DOWN_FS(2), ["u_src", "u_out", "u_gain"]),
    blur: program(gl, vs, BLUR_FS(false), ["u_src", "u_axis"]),
    blurEma: program(gl, vs, BLUR_FS(true), ["u_src", "u_prev", "u_axis", "u_k"]),
    air: program(gl, vs, AIR_FS, ["u_scal", "u_l1", "u_l2", "u_tint", "u_col", "u_colL", "u_asp"]),
  };
  gl.deleteShader(vs);
  const targets = [];
  function target(w, h, internal, format, filter) {
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, internal, w, h, 0, format, gl.HALF_FLOAT, null);
    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
    gl.clearColor(0, 0, 0, 0);
    gl.viewport(0, 0, w, h);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    const t = { tex, fb, w, h };
    targets.push(t);
    if (!ok) { dispose(); throw new Error(`vj-fluid: a ${w}x${h} 16-bit target is incomplete`); }
    return t;
  }
  const L = gl.LINEAR, N = gl.NEAREST;
  const T = {
    vel: [target(W, H, gl.RG16F, gl.RG, L), target(W, H, gl.RG16F, gl.RG, L)],
    scal: [target(W, H, gl.RGBA16F, gl.RGBA, L), target(W, H, gl.RGBA16F, gl.RGBA, L)], scalHat: target(W, H, gl.RGBA16F, gl.RGBA, L),
    p: [target(W, H, gl.R16F, gl.RED, N), target(W, H, gl.R16F, gl.RED, N)],
    div: target(W, H, gl.R16F, gl.RED, N), curl: target(W, H, gl.R16F, gl.RED, N),
    l1: [target(...LIGHT.L1, gl.RGBA16F, gl.RGBA, L), target(...LIGHT.L1, gl.RGBA16F, gl.RGBA, L)], l1a: target(...LIGHT.L1, gl.RGBA16F, gl.RGBA, L), l1b: target(...LIGHT.L1, gl.RGBA16F, gl.RGBA, L),
    l2: [target(...LIGHT.L2, gl.RGBA16F, gl.RGBA, L), target(...LIGHT.L2, gl.RGBA16F, gl.RGBA, L)], l2a: target(...LIGHT.L2, gl.RGBA16F, gl.RGBA, L), l2b: target(...LIGHT.L2, gl.RGBA16F, gl.RGBA, L),
    air: target(W, H, gl.RGBA16F, gl.RGBA, L),
  };
  const st = {
    vel: 0, scal: 0, p: 0, l1: 0, l2: 0, acc: 0, t: 0, steps: 0, frames: 0, haze: clamp(ctx.haze ?? 0.5, 0, 1), tint: [1, 1, 1],
    light: null, lightGain: 0, bursts: [], fog: null, stirs: [], prevSeg: null, prevN: 0, segFloats: 8,
    granted: 0, refused: 0, safeRefused: 0, co2: 0, fogPushes: 0,
  };
  // scratch for the uniform arrays (no allocation per step)
  const emPos = new Float32Array(MAX_EMITTERS * 4), emA = new Float32Array(MAX_EMITTERS * 4), emB = new Float32Array(MAX_EMITTERS * 4),
        emT = new Float32Array(MAX_EMITTERS), stirA = new Float32Array(MAX_STIRS * 4), stirR = new Float32Array(MAX_STIRS),
        colA = new Float32Array(CO2.MAX_JETS * 4), colL = new Float32Array(CO2.MAX_JETS);
  // the haze starts at its texture (a room hazed before doors), the rest at rest
  seedHaze();

  function seedHaze() {
    const px = new Uint16Array(W * H * 4);
    const toHalf = halfConverter();
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) px[(j * W + i) * 4] = toHalf(hazeTarget(st.haze, (i + 0.5) / H, (j + 0.5) / H, 0));
    gl.bindTexture(gl.TEXTURE_2D, T.scal[st.scal].tex);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, W, H, gl.RGBA, gl.HALF_FLOAT, px);
    gl.bindTexture(gl.TEXTURE_2D, null);
  }
  function bind(unit, tex) { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex); }
  function draw(t) { gl.bindFramebuffer(gl.FRAMEBUFFER, t.fb); gl.viewport(0, 0, t.w, t.h); gl.drawArrays(gl.TRIANGLES, 0, 3); }
  function use(prog) { gl.useProgram(prog.p); if (prog.u.u_grid) gl.uniform2f(prog.u.u_grid, W, H); return prog.u; }

  // the emitters live now, into the uniform arrays (cells)
  function emitters() {
    const list = [];
    st.bursts = st.bursts.filter((b) => st.t - b.t0 < b.plan.ramp + b.plan.hold + 4 * CO2.FADE_S);
    for (const b of st.bursts.slice(-CO2.MAX_JETS)) { const lv = valve(b.plan, st.t - b.t0); if (lv > 0) list.push(co2Emitter(b.x01, b.y01, lv)); }
    if (st.fog && st.fog.level > 0) list.push(...fogEmitters(st.fog.level));
    emPos.fill(0); emA.fill(0); emB.fill(0); emT.fill(0);
    emitterCells(list, W, H).forEach((e, k) => {
      if (k >= MAX_EMITTERS) return;
      emPos.set([e.x, e.y, e.dx, e.dy], k * 4); emA.set([e.level, e.u0, e.tan, e.r0], k * 4); emB.set([e.near, e.grip, e.rate, e.channel], k * 4);
      emT[k] = e.temp;
    });
  }
  function setEmitters(u) { gl.uniform4fv(u.u_em, emPos); gl.uniform4fv(u.u_emA, emA); gl.uniform4fv(u.u_emB, emB); gl.uniform1fv(u.u_emT, emT); }

  function simStep(dt) {
    emitters();
    let u;
    // the velocity rides itself (semi-Lagrangian: SIM.VORTICITY)
    u = use(P.adv1); gl.uniform1f(u.u_dt, dt); gl.uniform1i(u.u_vel, 0); gl.uniform1i(u.u_src, 1); gl.uniform4f(u.u_open, 0, 0, 0, 0);
    bind(0, T.vel[st.vel].tex); bind(1, T.vel[st.vel].tex); draw(T.vel[1 - st.vel]); st.vel = 1 - st.vel;
    // the curl, then the forces and the emitters' grip
    u = use(P.curl); gl.uniform1i(u.u_vel, 0); bind(0, T.vel[st.vel].tex); draw(T.curl);
    u = use(P.force); gl.uniform1f(u.u_dt, dt); gl.uniform1i(u.u_vel, 0); gl.uniform1i(u.u_curl, 1); gl.uniform1i(u.u_scal, 2);
    gl.uniform1f(u.u_drag, Math.exp(-dt / SIM.VEL_TAU_S)); gl.uniform1f(u.u_kappa, SIM.KAPPA_CO2 * H); gl.uniform1f(u.u_beta, SIM.BETA_T * H);
    stirA.fill(0); stirR.fill(0);
    st.stirs.slice(0, MAX_STIRS).forEach((s, k) => { stirA.set([s.x * W, s.y * H, s.vx * H, s.vy * H], k * 4); stirR[k] = s.r * H; });
    gl.uniform4fv(u.u_stir, stirA); gl.uniform1fv(u.u_stirR, stirR);
    setEmitters(u);
    bind(0, T.vel[st.vel].tex); bind(1, T.curl.tex); bind(2, T.scal[st.scal].tex); draw(T.vel[1 - st.vel]); st.vel = 1 - st.vel;
    // the pressure: divergence, warm-started Jacobi, projection
    u = use(P.div); gl.uniform1i(u.u_vel, 0); bind(0, T.vel[st.vel].tex); draw(T.div);
    u = use(P.jac); gl.uniform1i(u.u_p, 0); gl.uniform1i(u.u_div, 1); bind(1, T.div.tex);
    for (let it = 0; it < Q.JACOBI; it++) {
      gl.uniform1f(u.u_keep, it === 0 ? SIM.PRESSURE_KEEP : 1);
      bind(0, T.p[st.p].tex); draw(T.p[1 - st.p]); st.p = 1 - st.p;
    }
    u = use(P.proj); gl.uniform1i(u.u_vel, 0); gl.uniform1i(u.u_p, 1);
    bind(0, T.vel[st.vel].tex); bind(1, T.p[st.p].tex); draw(T.vel[1 - st.vel]); st.vel = 1 - st.vel;
    // the scalars on the projected flow, their clocks and the emitters
    u = use(P.adv1); gl.uniform1f(u.u_dt, dt); gl.uniform1i(u.u_vel, 0); gl.uniform1i(u.u_src, 1); gl.uniform4f(u.u_open, ...OPEN);
    bind(0, T.vel[st.vel].tex); bind(1, T.scal[st.scal].tex); draw(T.scalHat);
    u = use(P.adv2s); gl.uniform1f(u.u_dt, dt); gl.uniform1i(u.u_vel, 0); gl.uniform1i(u.u_scal, 1); gl.uniform1i(u.u_hat, 2);
    gl.uniform4f(u.u_decay, 1 - Math.exp(-dt / SIM.TAU_S.haze), Math.exp(-dt / SIM.TAU_S.fog), Math.exp(-dt / SIM.TAU_S.co2), Math.exp(-dt / SIM.TAU_S.temp));
    gl.uniform1f(u.u_haze, st.haze); gl.uniform1f(u.u_time, st.t + dt); gl.uniform4f(u.u_open, ...OPEN);
    setEmitters(u);
    bind(0, T.vel[st.vel].tex); bind(1, T.scal[st.scal].tex); bind(2, T.scalHat.tex); draw(T.scal[1 - st.scal]); st.scal = 1 - st.scal;
    st.t += dt; st.steps++;
    st.stirs = [];
  }
  // the light: the source down to the two levels, blurred, each through its history; then the air
  function light(dt) {
    const k = emaK(dt);
    let u;
    const src = st.light && st.lightGain > 0 ? st.light : null;
    if (src) {
      u = use(P.down16); gl.uniform1i(u.u_src, 0); gl.uniform2f(u.u_out, ...LIGHT.L1); gl.uniform1f(u.u_gain, st.lightGain); bind(0, src); draw(T.l1a);
    } else { gl.bindFramebuffer(gl.FRAMEBUFFER, T.l1a.fb); gl.viewport(0, 0, ...LIGHT.L1); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT); }
    blurLevel(T.l1a, T.l1b, T.l1, "l1", k);
    u = use(P.down4); gl.uniform1i(u.u_src, 0); gl.uniform2f(u.u_out, ...LIGHT.L2); gl.uniform1f(u.u_gain, 1); bind(0, T.l1[st.l1].tex); draw(T.l2a);
    blurLevel(T.l2a, T.l2b, T.l2, "l2", k);
    u = use(P.air); gl.uniform1i(u.u_scal, 0); gl.uniform1i(u.u_l1, 1); gl.uniform1i(u.u_l2, 2); gl.uniform3f(u.u_tint, ...st.tint);
    colA.fill(0); colL.fill(0);
    st.bursts.slice(-CO2.MAX_JETS).forEach((b, k) => { const c = jetColumn(b.plan, st.t - b.t0); colA.set([b.x01, b.y01, c.tip, c.tail], k * 4); colL[k] = c.level; });
    gl.uniform4fv(u.u_col, colA); gl.uniform1fv(u.u_colL, colL); gl.uniform1f(u.u_asp, W / H);
    bind(0, T.scal[st.scal].tex); bind(1, T.l1[st.l1].tex); bind(2, T.l2[st.l2].tex); draw(T.air);
  }
  // one level: across, then down with the history (no source this frame: the down pass drew black, so the history falls
  // at its own rate, never cut)
  function blurLevel(a, b, pair, key, k) {
    let u = use(P.blur); gl.uniform1i(u.u_src, 0); gl.uniform2i(u.u_axis, 1, 0); bind(0, a.tex); draw(b);
    u = use(P.blurEma); gl.uniform1i(u.u_src, 0); gl.uniform1i(u.u_prev, 1); gl.uniform2i(u.u_axis, 0, 1); gl.uniform1f(u.u_k, k);
    bind(0, b.tex); bind(1, pair[st[key]].tex); draw(pair[1 - st[key]]); st[key] = 1 - st[key];
  }

  // asked: the caller's answer for this onset (a boolean), or left out to ask the gate here
  function onset(scale, asked) {
    const live = ctx.live ? ctx.live() : true;
    if (!live) { st.safeRefused++; return null; }
    const granted = typeof asked === "boolean" ? asked : ctx.gate ? ctx.gate.request(ctx.now ? ctx.now() : st.t) : false;
    if (granted) st.granted++; else st.refused++;
    return { granted, scale: granted ? 1 : scale };
  }
  function dispose() {
    for (const t of targets) { gl.deleteTexture(t.tex); gl.deleteFramebuffer(t.fb); }
    targets.length = 0;
    for (const k of Object.keys(P || {})) if (P[k]) gl.deleteProgram(P[k].p);
  }

  return {
    api: FLUID_API, grid: [W, H], quality: ctx.quality === "low" ? "low" : "high",
    // advance: the sim on its fixed tick (at most MAX_STEPS a frame), then the light and the air every frame
    step(dt) {
      if (!(dt > 0)) return;
      st.acc = Math.min(st.acc + dt, SIM.MAX_STEPS / SIM.HZ);
      while (st.acc >= 1 / SIM.HZ - 1e-9) { simStep(1 / SIM.HZ); st.acc -= 1 / SIM.HZ; }
      light(dt);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.activeTexture(gl.TEXTURE0);
      st.frames++;
    },
    // a CO2 jet from (x01, y01) on the screen (0..1, y up), upward; asks the gate (granted: full; refused: smaller, slow)
    // unless the caller already asked for this onset and passes the answer as granted
    co2(x01, y01 = 0.02, strength01 = 1, granted) {
      const o = onset(CO2.REFUSED_SCALE, granted);
      if (!o) return null;
      const plan = co2Plan(o.granted, strength01);
      st.bursts.push({ t0: st.t, x01: clamp(x01, 0.02, 0.98), y01: clamp(y01, 0, 0.9), plan });
      if (st.bursts.length > CO2.MAX_JETS * 2) st.bursts.shift();
      st.co2++;
      return { granted: o.granted, level: plan.level };
    },
    // the fog machines while the pad is held (level 0..1); the fog then hangs and decays by its own physics
    fogPush(level01 = 1) {
      if (st.fog) { st.fog.level = clamp(level01, 0, 1) * st.fog.scale; return { granted: st.fog.granted }; }
      const o = onset(FOG.REFUSED_SCALE);
      if (!o) return null;
      st.fog = { level: clamp(level01, 0, 1) * o.scale, scale: o.scale, granted: o.granted };
      st.fogPushes++;
      return { granted: o.granted };
    },
    fogRelease() { st.fog = null; },
    // this frame's light source: a linear-light texture of the page's size (the beam layer) and its gain
    inscatter(tex, gain = 1) { st.light = tex; st.lightGain = tex ? Math.max(0, gain) : 0; },
    // stirs for the next step: [{ x, y (0..1), vx, vy (fh/s), r (fh) }]
    stir(list) { for (const s of list) if (st.stirs.length < MAX_STIRS) st.stirs.push(s); },
    // the beams' own motion as stirs (vj-lasers.js records; asp = width / height; dt = this frame's)
    stirFromBeams(seg, n, asp, dt) {
      if (seg && n > 0 && st.prevSeg && dt > 0) this.stir(beamStirs(st.prevSeg, st.prevN, seg, n, dt, asp, st.segFloats));
      if (seg && n > 0) { if (!st.prevSeg || st.prevSeg.length < n * st.segFloats) st.prevSeg = new Float32Array(Math.max(n, 64) * st.segFloats); st.prevSeg.set(seg.subarray(0, n * st.segFloats)); st.prevN = n; }
      else st.prevN = 0;
    },
    haze(level01) { st.haze = clamp(level01, 0, 1); },
    tint(r, g, b) { st.tint[0] = r; st.tint[1] = g; st.tint[2] = b; },
    texture() { return T.air.tex; },
    stats() {
      return { grid: [W, H], jacobi: Q.JACOBI, steps: st.steps, frames: st.frames, t: +st.t.toFixed(3), haze: st.haze,
               co2: st.co2, fogPushes: st.fogPushes, fogOn: !!st.fog, granted: st.granted, refused: st.refused,
               safeRefused: st.safeRefused, jets: st.bursts.length, lightGain: st.lightGain };
    },
    dispose,
  };
}

// Float to IEEE half (for the haze's first texture: no float upload path is needed for the rest).
function halfConverter() {
  const f = new Float32Array(1), i = new Uint32Array(f.buffer);
  return (v) => {
    f[0] = v;
    const x = i[0], sign = (x >>> 16) & 0x8000, e = ((x >>> 23) & 0xff) - 127 + 15, m = x & 0x7fffff;
    if (e <= 0) return sign;
    if (e >= 31) return sign | 0x7c00;
    return sign | (e << 10) | (m >>> 13);
  };
}
