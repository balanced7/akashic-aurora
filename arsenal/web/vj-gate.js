// VJ gate v2: arsenal/web/vj-gate.js (pure ES module: no DOM, no WebGL). Tests: tests/vj_core.test.mjs (the gate section).
//
// The final-output flash limiter. The FlashGate (vj-core.js) grants at most three full-frame flashes a second to the
// effects that ASK it (the white flash, the strobe's pulses, Invert's onset). Most of the light on the screen never asks:
// the impact pass's punch, the scene's own reaction to a hit, the overlay's rings and beams, the glitch, the look's glow.
// On 2026-10-24 an adversarial verifier counted up to 6.5 flashes a second in pad storms on a 60 fps virtual clock (the
// gate alone: at most about 3). Gate v2 judges the picture actually shown, after every layer, and is the final guarantee
// (it never loosens the FlashGate: that still decides which flashes are asked for at all).
//
// THE SECOND VERSION (2026-10-25). The round-2 verifier showed the first version held only its own 18 windows of a 4 x 4
// grid: a quarter-screen rectangle straddling that grid flashed 8 times a second while every window it watched read 0.
// Now the frame is metered in 8 x 8 cells and EVERY cell rectangle of a quarter of the screen or more is a window (311 of
// them: every size, at every offset), and the thresholds carry the worst-case overlap of an arbitrary quarter-screen
// rectangle with its best window (P_MIN, below), so a region off the grid that flashes is seen by a window that is held.
//
//   MEASURE   the final frame (scene, overlay, effects, glitch, look, invert: everything) on the GPU every frame, EVERY
//             pixel (a box reduction, any canvas size), as the relative luminance (WCAG: linear light, 0.2126 R + 0.7152 G
//             + 0.0722 B of the sRGB-decoded pixel) and the WCAG red quantity (max(0, R - G - B) x 320 over saturated red
//             pixels, R / (R + G + B) >= 0.8; stored / 320), in 8 x 8 cells; each cell keeps four sums weighted by its
//             corners' "hats" (smoothstep-bilinear), so the shown value of any window is an exact linear function of the
//             9 x 9 corner gains the apply pass interpolates.
//   WINDOWS   311 windows: every rectangle of cells covering a quarter of the screen or more (16 of the 64 cells), at every
//             offset (the standard's area: flashes over more than 25 % of the screen). Each window has two TRACKERS,
//             luminance and red. P_MIN = 0.72: any rectangle of a quarter of the screen or more, wherever it sits, has a
//             window that lies at least 72 % inside it (checked by tests/vj_core.test.mjs over 20000 random rectangles),
//             so a region that flickers by 0.1 shows a window a swing of at least 0.072.
//   COUNT     each tracker runs, online, the verifier's own flash counter (vj-gate.js transitions, the 2026-10-24
//             verifier's method): turning points with a hysteresis (0.02 luminance), a transition is a swing between
//             turning points of at least TH (0.068: the standard's 0.1 times P_MIN, less a margin), counted at its END (the
//             later turning point), in a one-second ring. The standard allows six transitions (three flashes); a window
//             is allowed N_MAX = 5, so a quarter-screen rectangle that no window matches exactly (its own turning points,
//             its own mix of cells) has a transition of slack and still counts at most six (the twin battery, 171 cases).
//   CELLS     every one of the 64 cells is a window too, with thresholds of its own (a swing of 0.15): an anti-phase
//             pattern (a checkerboard, blocks, a split off the grid) keeps every quarter window's mean level while a
//             quarter-screen rectangle cut differently sees the imbalance; its cells flicker hard and are held.
//   FREE      while a tracker has room for a whole flash (at most three transitions ended in the last second, no forced
//             rest) the frame shows as it was drawn. A transition is counted from the frame its swing reaches TH (it may
//             end there, or later), so the limit holds however the second is cut: a receipt that stops mid-swing counts it
//             at its last frame, still inside.
//   PARTIAL   with four: a flash is a rise AND a fall, so the last transition is kept for a fall. A rise is held under the
//             threshold (and under a band's top, below); a fall may start. So a window runs out of budget in its DARK
//             state, and holding it there takes light away (darkening keeps colour) instead of lifting the gaps.
//   HELD      with five (or resting), the window's shown value may only move inside a band that starts no new transition
//             (the "no-commit" interval of its own counter, the HARD limit) and is at most BAND wide (0.045), centred on
//             the shown value when the hold starts and drifting toward the drawn value (DRIFT_DOWN 0.6 a second, DRIFT 0.2
//             up) (the SOFT limit); an open transition already counted may run on. Any two frames of one held stretch then
//             differ by at most BAND + DRIFT x its length, whatever another counter's turning points, so the receipt's
//             counter (with its own windows and sampling) sees no new flash in it either.
//   SOLVE     the 81 corner gains a (darken, 0..1) and lifts k (toward white, 0..1: Y' = a Y + k (1 - Y), exact in linear
//             light) by projections onto the held windows' bands (Kaczmarz: SWEEPS sweeps on the soft limits, then
//             HARD_SWEEPS on the hard ones; each correction spread over the window's corners in proportion to their share
//             of its light, so the brightest part dims most and the field stays smooth). Free windows add no constraint:
//             with nothing held every gain is exactly 1 and the apply pass copies the frame untouched.
//   FALLBACK  a smooth field cannot always meet overlapping windows at once. Then one blend toward the previous SHOWN frame,
//             beta (0..1, the smallest that meets every hard limit; 1 shows the last frame again, which meets them all by
//             construction), finishes the job. It is rare (a frame or two of echo) and it is what makes the limit certain.
//   REST      ITU-R BT.1702: even compliant flashing for more than about five seconds may be a risk. Each transition in a
//             tracker's ring is marked once its swing reaches TH_REST (0.07: the standard's 0.1 times P_MIN); while some
//             window holds REST_COUNT (4: two flashes) such transitions in its last second, the run grows, and after RUN_S
//             (5 s) of it every tracker is held for REST_S (2 s). A set pulsing to the beat (about one flash a second at
//             most, measured under the demo's music) never rests.
//   RED       red counts like luminance (its own threshold and hysteresis), so any change to or from saturated red over a
//             quarter of the screen spends the same kind of budget; a darkening gain lowers red exactly, a lift lowers it
//             further (the model counts it as unchanged, never an underestimate of too much red).
// The GPU twin (vj-limiter.js) is generated from these constants and mirrors FlashLimiter.step line by line; the browser
// receipt (arsenal/lanes/vj_storm.mjs, its parity check) feeds both the same cell sums and compares the results. When the
// GPU decision cannot run (a program that will not link), the page runs THIS class on the cell sums it reads back (the
// limiter's "cpu" mode): the same rules, a stall per frame instead of none.

export const GATE_API = "arsenal.vj-gate/v2.1";

export const LIMIT = Object.freeze({
  GX: 8, GY: 8,               // 8 x 8 measuring cells
  CX: 9, CY: 9,               // 9 x 9 corner gains
  MIN_CELLS: 16,              // a window covers at least a quarter of the cells
  P_MIN: 0.72,                // the worst overlap of a quarter-screen rectangle with its best window (tests check it)
  N_MAX: 5,                   // transitions in any second: two and a half flashes, a transition short of the standard's
                              // three, so a quarter-screen window off the grid (its own turning points) still counts <= 6;
                              // a steady two flashes a second (four transitions) never needs holding
  WINDOW_S: 0.995,            // a transition 59 frames old shares a second with this one, one 60 frames old does not
                              // (the receipt's rule: ends j - i < 60 frames); a late end is the moving end's business
  RING: 7,                    // transition ends kept per tracker (at most N_MAX are ever younger than WINDOW_S)
  RUN_S: 5, REST_S: 2,        // the forced rest
  REST_COUNT: 4,              // full-size transitions in a window's last second that count as flashing, for the rest
  SWEEPS: 3, HARD_SWEEPS: 3,
  K_MAX: 1,
  EMPTY_AGE: 9,               // a ring slot that holds no transition
  // per signal and kind: [quarter window luminance, red quantity / 320, cell luminance, cell red / 320]
  TH: Object.freeze([0.068, 14 / 320, 0.15, 36 / 320]),
  HYST: Object.freeze([0.02, 2 / 320, 0.04, 6 / 320]),
  BAND: Object.freeze([0.045, 8 / 320, 0.08, 20 / 320]),
  DRIFT: Object.freeze([0.2, 24 / 320, 0.6, 72 / 320]),          // the held band toward a brighter drawn value, a second
  DRIFT_DOWN: Object.freeze([0.6, 72 / 320, 1.2, 144 / 320]),    // ... and toward a darker one (taking light away is cheap)
  TH_REST: Object.freeze([0.07, 14 / 320, 9, 9]),                // (cells never count toward the rest)
  EXT_NEAR: Object.freeze([0.02, 2 / 320, 0.04, 6 / 320]),       // the newest transition's end moves to now within this of its extreme
  EXT_CLOSE: Object.freeze([0.04, 4 / 320, 0.08, 12 / 320]),     // ... until the value has turned back by this much
});
export const NSIG = 2;
export const MODE = Object.freeze({ FREE: 0, HELD: 1 });

// The windows, as cell rectangles [x0, y0, x1, y1] (inclusive): every rectangle of at least MIN_CELLS cells, the whole
// frame first, then by area (largest first) and position.
export const WINDOWS = (() => {
  const w = [];
  for (let h = LIMIT.GY; h >= 1; h--) for (let wd = LIMIT.GX; wd >= 1; wd--) {
    if (wd * h < LIMIT.MIN_CELLS) continue;
    for (let y = 0; y + h <= LIMIT.GY; y++) for (let x = 0; x + wd <= LIMIT.GX; x++) w.push([x, y, x + wd - 1, y + h - 1]);
  }
  w.sort((p, q) => ((q[2] - q[0] + 1) * (q[3] - q[1] + 1)) - ((p[2] - p[0] + 1) * (p[3] - p[1] + 1)) || p[1] - q[1] || p[0] - q[0] || (p[2] - q[2]));
  // then every single cell, its own window with its own (much higher) thresholds: a pattern flickering in anti-phase
  // (a checkerboard, blocks, a split off the grid) keeps every quarter window's mean nearly level while a quarter window
  // off the grid, cut differently, sees the imbalance; its cells flicker hard, and holding them takes the pattern down
  for (let y = 0; y < LIMIT.GY; y++) for (let x = 0; x < LIMIT.GX; x++) w.push([x, y, x, y]);
  return Object.freeze(w.map((x) => Object.freeze(x)));
})();
export const NW = WINDOWS.length;          // 375
export const NWQ = NW - LIMIT.GX * LIMIT.GY;   // 311 quarter windows (then the 64 cells)
export const NT = NW * NSIG;               // 750 trackers: tracker t = window (t >> 1), signal (t & 1)
export const NTQ = NWQ * NSIG;             // the quarter windows' trackers come first
// the constants' index for tracker t: its signal, plus 2 for a cell
export const kindOf = (t) => (t & 1) + ((t >> 1) >= NWQ ? 2 : 0);
// per tracker (five RGBA texels on the GPU): [dir, X, C, sPrev | open, held level (0 free, 1 partial, 2 full), pin, ext |
// ring 0-3 | ring 4-6, leaks |
// full-size mask (bit r: ring slot r's swing reached TH_REST), ext extreme, ext direction, -]
// (ext: the ring slot of the newest transition whose end may still move, -1 none)
export const TRACKER_FLOATS = 20;
export const TRACKER_ROWS = TRACKER_FLOATS / 4;
export const NCELLS = LIMIT.GX * LIMIT.GY;
export const NCTRL = LIMIT.CX * LIMIT.CY;
export const NCELL_FLOATS = NCELLS * NSIG * 4;   // 512: cell (cy * GX + cx), signal s, corner j
export const cellIndex = (cx, cy, s, j) => (((cy * LIMIT.GX + cx) * NSIG + s) << 2) + j;
// corner j of cell (cx, cy): 0 (cx, cy), 1 (cx + 1, cy), 2 (cx, cy + 1), 3 (cx + 1, cy + 1); the control there
export const ctrlIndex = (cx, cy, j) => (cy + (j >> 1)) * LIMIT.CX + cx + (j & 1);

// The hat weights of a point (u, v) in 0..1 (the frame) for its cell's four corners, as the apply pass uses them:
// out = [cx, cy, w0, w1, w2, w3].
export function hats(u, v, out) {
  const x = Math.min(LIMIT.GX - 1e-6, Math.max(0, u * LIMIT.GX)), y = Math.min(LIMIT.GY - 1e-6, Math.max(0, v * LIMIT.GY));
  const cx = Math.floor(x), cy = Math.floor(y);
  // smoothstep-weighted bilinear: still a partition of unity (so a window's value stays linear in the gains), and smooth
  // across cells, so a held region dims as a soft round patch rather than a pyramid
  const ss = (q) => q * q * (3 - 2 * q), fx = ss(x - cx), fy = ss(y - cy);
  out[0] = cx; out[1] = cy;
  out[2] = (1 - fx) * (1 - fy); out[3] = fx * (1 - fy); out[4] = (1 - fx) * fy; out[5] = fx * fy;
  return out;
}

// Cell sums from a picture: lum(u, v) and red(u, v) give the two signals at a point; the picture is sampled on an n x m
// grid of points (cell-aligned when n and m are multiples of 8). A cell's four corner sums add up to its mean. The GPU
// meter does the same on the frame, every pixel.
export function cellSums(lum, red, n = 64, m = 64, out = new Float32Array(NCELL_FLOATS)) {
  out.fill(0);
  const h = new Float64Array(6), count = new Float64Array(NCELLS);
  for (let iy = 0; iy < m; iy++) for (let ix = 0; ix < n; ix++) {
    const u = (ix + 0.5) / n, v = (iy + 0.5) / m;
    hats(u, v, h);
    const c = h[1] * LIMIT.GX + h[0];
    count[c]++;
    const L = lum(u, v), R = red(u, v);
    for (let j = 0; j < 4; j++) { out[cellIndex(h[0], h[1], 0, j)] += h[2 + j] * L; out[cellIndex(h[0], h[1], 1, j)] += h[2 + j] * R; }
  }
  for (let c = 0; c < NCELLS; c++) for (let k = 0; k < 8; k++) out[(c << 3) + k] /= Math.max(count[c], 1);
  return out;
}

// One window's value under gains a and lifts k: the mean over its cells of sum_j (a_j S_j + k_j (1/4 - S_j)) for
// luminance; sum_j a_j S_j for red (a lift only lowers red).
export function windowValue(cells, a, k, w, s) {
  const [x0, y0, x1, y1] = WINDOWS[w];
  let sum = 0;
  for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) {
    for (let j = 0; j < 4; j++) {
      const S = cells[cellIndex(cx, cy, s, j)], i = ctrlIndex(cx, cy, j);
      sum += a[i] * S + (s === 0 ? k[i] * (0.25 - S) : 0);
    }
  }
  return sum / ((x1 - x0 + 1) * (y1 - y0 + 1));
}
// The window's value as drawn (every gain 1, no lift).
export function windowWant(cells, w, s) {
  const [x0, y0, x1, y1] = WINDOWS[w];
  let sum = 0;
  for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) for (let j = 0; j < 4; j++) sum += cells[cellIndex(cx, cy, s, j)];
  return sum / ((x1 - x0 + 1) * (y1 - y0 + 1));
}

// The worst overlap, over n random rectangles of a quarter of the screen or more (any aspect from 1:4 to 4:1, anywhere),
// of the rectangle with its best window: the share of the best window's area that lies inside the rectangle. A region
// that flickers uniformly by s shows that window at least s times this.
export function worstOverlap(n = 20000, seed = 1) {
  let s = seed >>> 0;
  const R = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  let worst = 1, at = null;
  const W = WINDOWS.slice(0, NWQ).map(([x0, y0, x1, y1]) => [x0 / LIMIT.GX, y0 / LIMIT.GY, (x1 + 1) / LIMIT.GX, (y1 + 1) / LIMIT.GY]);
  for (let i = 0; i < n; i++) {
    const area = R() < 0.5 ? 0.25 : 0.25 * (1 + 0.6 * R());
    const ar = Math.exp(Math.log(0.25) + R() * (Math.log(4) - Math.log(0.25)));
    const w = Math.sqrt(area * ar), h = area / w;
    if (w > 1 || h > 1) continue;
    const x = R() * (1 - w), y = R() * (1 - h);
    let best = 0;
    for (const [mx0, my0, mx1, my1] of W) {
      const ix = Math.max(0, Math.min(x + w, mx1) - Math.max(x, mx0)), iy = Math.max(0, Math.min(y + h, my1) - Math.max(y, my0));
      const p = (ix * iy) / ((mx1 - mx0) * (my1 - my0));
      if (p > best) best = p;
    }
    if (best < worst) { worst = best; at = [x, y, x + w, y + h]; }
  }
  return { worst, at };
}

// The final-output limiter, the JS twin of the GPU passes (vj-limiter.js). step(cells, dt) takes this frame's cell sums
// and the time since the last frame, and returns what the apply pass does: { a, k } (Float32Array(81) each, control
// y * 9 + x) and beta (the blend toward the previous shown frame).
export class FlashLimiter {
  constructor() {
    this.state = new Float32Array(NT * TRACKER_FLOATS);
    this.glob = new Float32Array(8);           // [flashing run, rest left, frames, beta | held, leaks, worst soft miss, -]
    this.a = new Float32Array(NCTRL); this.k = new Float32Array(NCTRL); this.beta = 0;
    this.lo = new Float64Array(NT); this.hi = new Float64Array(NT);        // soft limits (free: -inf, inf)
    this.hlo = new Float64Array(NT); this.hhi = new Float64Array(NT);      // hard limits
    this.want = new Float64Array(NT); this.shown = new Float64Array(NT);
    this.mode = new Uint8Array(NT); this.level = new Uint8Array(NT); this.pinNow = new Float64Array(NT);
    this._ga = new Float64Array(NCTRL); this._gk = new Float64Array(NCTRL);
    this.commits = 0;                          // transitions counted, all trackers (receipts)
    this.leaks = 0;                            // transitions started while held (the limit failed; never expected)
    this.projections = 0;                      // projections that moved the field (the cost receipt)
    this.reset();
  }
  reset() {
    this.state.fill(0);
    for (let t = 0; t < NT; t++) {
      const o = t * TRACKER_FLOATS;
      for (let r = 0; r < LIMIT.RING; r++) this.state[o + 8 + r] = LIMIT.EMPTY_AGE;
      this.state[o + 4] = -1;
      this.state[o + 7] = -1;
    }
    this.glob.fill(0);
    this.a.fill(1); this.k.fill(0); this.beta = 0;
    this.commits = 0; this.leaks = 0; this.projections = 0;
  }
  // transitions ended within the window once this frame's dt has passed (the ring ages before this frame's update);
  // fullSize: only those whose swing reached TH_REST
  count(t, dt, fullSize = false) {
    const o = t * TRACKER_FLOATS + 8, mask = this.state[t * TRACKER_FLOATS + 16];
    let n = 0;
    for (let r = 0; r < LIMIT.RING; r++) if (this.state[o + r] + dt < LIMIT.WINDOW_S && (!fullSize || (mask >> r) & 1)) n++;
    return n;
  }
  // This frame's mode and limits for tracker t.
  band(t, cells, dt) {
    const S = this.state, o = t * TRACKER_FLOATS, s = t & 1, w = t >> 1, q = kindOf(t);
    const TH = LIMIT.TH[q], BAND = LIMIT.BAND[q];
    const want = windowWant(cells, w, s);
    this.want[t] = want;
    const dir = S[o], X = S[o + 1], C = S[o + 2], sPrev = S[o + 3], open = S[o + 4], level = S[o + 5];
    this.mode[t] = MODE.FREE; this.level[t] = 0; this.pinNow[t] = S[o + 6];
    this.lo[t] = this.hlo[t] = -Infinity;
    this.hi[t] = this.hhi[t] = Infinity;
    if (dir === 0) return;
    const eps = s === 0 ? 1e-4 : 2e-5;
    // A transition counts from the frame it crosses TH: its end (where the receipt counts it) is that frame or later, so
    // the transitions already in the last second are what a new one would join. A flash is a rise AND a fall: a rise may
    // start only with room left for its fall (n + 2 <= budget), a fall with room for itself (n + 1 <= budget). So a window
    // that runs out of budget does so in its dark state, and holding it there only ever takes light away (darkening keeps
    // colour; lifting toward white, the other way, is left for what the content forces).
    const n = this.count(t, dt), budget = this.glob[1] > 0 ? 0 : LIMIT.N_MAX;
    if (n + 2 <= budget) return;
    const fallOK = n + 1 <= budget;
    // the no-commit interval of its own counter: what would start a rise (above) and a fall (below)
    let ncLo, ncHi;
    if (dir > 0) { ncLo = C - TH; ncHi = open >= 0 ? Infinity : X + TH; }
    else { ncLo = open >= 0 ? -Infinity : X - TH; ncHi = C + TH; }
    // The pinned band (at most BAND wide): centred on the shown value when a hold starts or deepens (or when an allowed
    // transition carries the value out of it), then drifting toward the drawn value at DRIFT. Any two frames of a held
    // stretch then differ by at most BAND + DRIFT x its length, whatever another counter's turning points.
    this.mode[t] = MODE.HELD;
    const lv = fallOK ? 1 : 2;
    this.level[t] = lv;
    let pin = S[o + 6];
    // (a value within 1e-5 of the band counts as in it: the GPU twin, in float32, must take the same branch)
    if (level < lv - 0.5 || sPrev < pin - 1e-5 || sPrev > pin + BAND + 1e-5) pin = sPrev - 0.5 * BAND;
    const top = pin + BAND, step = LIMIT.DRIFT[q] * dt;
    if (want > top) pin += Math.min(step, want - top);
    else if (want < pin) pin -= Math.min(LIMIT.DRIFT_DOWN[q] * dt, pin - want);
    const runOnDown = dir < 0 && open >= 0, runOnUp = dir > 0 && open >= 0;
    if (fallOK) {
      // PARTIAL: one transition left, kept for a fall: below, anything (a fall may start, or run on); above, nothing that
      // would start a rise, and the band's top
      if (pin + BAND > ncHi) pin = ncHi - BAND;
      this.pinNow[t] = pin;
      this.hhi[t] = ncHi - eps;
      this.hi[t] = runOnUp ? this.hhi[t] : Math.min(pin + BAND, this.hhi[t]);
      return;
    }
    // FULL: nothing may start; an open committed transition may still run on (it is one transition, however far it goes)
    if (pin < ncLo) pin = ncLo;
    if (pin + BAND > ncHi) pin = ncHi - BAND;
    this.pinNow[t] = pin;
    this.hlo[t] = ncLo + eps;
    this.hhi[t] = ncHi - eps;
    this.lo[t] = runOnDown ? this.hlo[t] : Math.max(pin, this.hlo[t]);
    this.hi[t] = runOnUp ? this.hhi[t] : Math.min(pin + BAND, this.hhi[t]);
    if (this.lo[t] > this.hi[t]) { const v = Math.min(Math.max(sPrev, this.hlo[t]), this.hhi[t]); this.lo[t] = v; this.hi[t] = v; }
  }
  // One projection of the field onto [lo, hi] for tracker t: the correction goes to the window's corners in proportion to
  // their share of its light (the gradient of its value), so the brightest part of the window dims most.
  project(cells, t, lo, hi) {
    const a = this.a, k = this.k, s = t & 1, w = t >> 1;
    const v = windowValue(cells, a, k, w, s);
    // (a miss under 1e-6 is no miss: the float32 twin must decide the same way at a tie)
    if (v <= hi + 1e-6 && v >= lo - 1e-6) return;
    const down = v > hi;
    const margin = Math.min(s === 0 ? 0.002 : 0.0006, 0.1 * (hi - lo));
    const target = down ? hi - margin : lo + margin;
    const ga = this._ga, gk = this._gk;
    const [x0, y0, x1, y1] = WINDOWS[w];
    const inv = 1 / ((x1 - x0 + 1) * (y1 - y0 + 1));
    // the gradient at each corner of the window: its share of the light of the window's cells around it (accumulated cell
    // by cell, as the GPU twin does)
    for (let Y = y0; Y <= y1 + 1; Y++) for (let X = x0; X <= x1 + 1; X++) { ga[Y * LIMIT.CX + X] = 0; gk[Y * LIMIT.CX + X] = 0; }
    for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) for (let j = 0; j < 4; j++) {
      const Sv = cells[cellIndex(cx, cy, s, j)], i = ctrlIndex(cx, cy, j);
      ga[i] += Sv * inv;
      if (s === 0) gk[i] += (0.25 - Sv) * inv;
    }
    let norm = 0;
    for (let Y = y0; Y <= y1 + 1; Y++) for (let X = x0; X <= x1 + 1; X++) {
      const i = Y * LIMIT.CX + X;
      if (down ? a[i] <= 0 : a[i] >= 1) ga[i] = 0;
      if (s !== 0 || (down ? k[i] <= 0 : k[i] >= LIMIT.K_MAX)) gk[i] = 0;
      norm += ga[i] * ga[i] + gk[i] * gk[i];
    }
    if (norm < 1e-12) return;
    const d = (target - v) / norm;
    for (let Y = y0; Y <= y1 + 1; Y++) for (let X = x0; X <= x1 + 1; X++) {
      const i = Y * LIMIT.CX + X;
      a[i] = Math.min(1, Math.max(0, a[i] + d * ga[i]));
      k[i] = Math.min(LIMIT.K_MAX, Math.max(0, k[i] + d * gk[i]));
    }
    this.projections++;
  }
  // (The order is the windows' own, the whole frame first: run from the smallest window up, the twin battery lifted the
  // gaps of a storm toward white and let halves split off the grid flash 4.5 times a second.)
  solve(cells) {
    this.a.fill(1); this.k.fill(0);
    for (let sweep = 0; sweep < LIMIT.SWEEPS; sweep++) {
      for (let t = 0; t < NT; t++) if (this.mode[t] !== MODE.FREE) this.project(cells, t, this.lo[t], this.hi[t]);
    }
    for (let sweep = 0; sweep < LIMIT.HARD_SWEEPS; sweep++) {
      for (let t = 0; t < NT; t++) if (this.mode[t] !== MODE.FREE) this.project(cells, t, this.hlo[t], this.hhi[t]);
    }
    // the fallback: the smallest blend toward the previous shown frame that meets every hard limit
    let beta = 0;
    for (let t = 0; t < NT; t++) {
      if (this.mode[t] === MODE.FREE) continue;
      const v = windowValue(cells, this.a, this.k, t >> 1, t & 1), p = this.state[t * TRACKER_FLOATS + 3];
      const lo = this.hlo[t], hi = this.hhi[t];
      if (v > hi + 1e-6 && p < v) beta = Math.max(beta, (v - hi) / (v - p));
      else if (v < lo - 1e-6 && p > v) beta = Math.max(beta, (lo - v) / (p - v));
    }
    this.beta = Math.min(1, beta);
  }
  // The counter, one tracker, one shown value (the ring has already aged by dt).
  update(t, v, dt) {
    const S = this.state, o = t * TRACKER_FLOATS, q = kindOf(t);
    const TH = LIMIT.TH[q], H = LIMIT.HYST[q];
    S[o + 3] = v;
    if (S[o] === 0) { S[o] = 1; S[o + 1] = v; S[o + 2] = v; S[o + 4] = -1; return; }
    let committed = false;
    const commit = (rise) => {
      committed = true;
      let idx = 0, oldest = -1;
      for (let r = 0; r < LIMIT.RING; r++) if (S[o + 8 + r] > oldest) { oldest = S[o + 8 + r]; idx = r; }
      S[o + 8 + idx] = 0;
      S[o + 4] = idx;
      S[o + 16] = S[o + 16] & ~(1 << idx);                  // a new transition in that slot: not full size (yet)
      this.commits++;
      // a leak: a transition the hold did not allow (any while full; a rise while one is kept for a fall)
      if (this.level[t] === 2 || (this.level[t] === 1 && rise)) { this.leaks++; S[o + 15]++; }
    };
    // A frame within NEAR of the turning value also moves the open transition's end to now: on a plateau the receipt's
    // counter (its own sampling: values a hair apart) may put the turning point on any of its frames, so ours is the last.
    const dir = S[o], X = S[o + 1], C = S[o + 2], NEAR = 0.5 * H;
    if (dir > 0) {
      if (v > C) {
        S[o + 2] = v;
        if (S[o + 4] >= 0) S[o + 8 + S[o + 4]] = 0;            // the open transition's end moves to now
        else if (v - X >= TH) commit(true);
      } else if (C - v >= H) {
        S[o] = -1; S[o + 1] = C; S[o + 2] = v; S[o + 4] = -1;
        if (C - v >= TH) commit(false);
      } else if (C - v <= NEAR && S[o + 4] >= 0) S[o + 8 + S[o + 4]] = 0;
    } else if (v < C) {
      S[o + 2] = v;
      if (S[o + 4] >= 0) S[o + 8 + S[o + 4]] = 0;
      else if (X - v >= TH) commit(false);
    } else if (v - C >= H) {
      S[o] = 1; S[o + 1] = C; S[o + 2] = v; S[o + 4] = -1;
      if (v - C >= TH) commit(true);
    } else if (v - C <= NEAR && S[o + 4] >= 0) S[o + 8 + S[o + 4]] = 0;
    // the open transition's swing reaching full size (TH_REST) marks its slot, for the rest
    if (S[o + 4] >= 0 && Math.abs(S[o + 2] - S[o + 1]) >= LIMIT.TH_REST[q]) S[o + 16] = S[o + 16] | (1 << S[o + 4]);
    // THE END THAT MAY STILL MOVE. Another window (the receipt's, off our grid) sees nearly our value but its own turning
    // points: where ours turned back by a hair more than the hysteresis, its swing may run on, and its transition ends
    // (and is counted) later. So the newest transition's end keeps moving to now while the value stays within EXT_NEAR
    // of its extreme, until the value has turned back by EXT_CLOSE (more than any such window's hysteresis plus the
    // difference between the two windows' values).
    if (committed) { S[o + 7] = S[o + 4]; S[o + 17] = v; S[o + 18] = S[o]; }
    else if (S[o + 7] >= 0) {
      const ext = S[o + 7], up = S[o + 18] > 0, NEAR2 = LIMIT.EXT_NEAR[q];
      if (up ? v > S[o + 17] : v < S[o + 17]) S[o + 17] = v;
      const back = up ? S[o + 17] - v : v - S[o + 17];
      if (back <= NEAR2) S[o + 8 + ext] = 0;
      else if (back >= LIMIT.EXT_CLOSE[q]) S[o + 7] = -1;
    }
  }
  step(cells, dt) {
    dt = Math.max(0, Math.min(0.25, dt));
    const g = this.glob;
    // the forced rest, from the counters as they stood before this frame
    let flashing = false;
    for (let t = 0; t < NTQ; t++) if (this.count(t, dt, true) >= LIMIT.REST_COUNT) { flashing = true; break; }
    for (let t = 0; t < NT; t++) this.band(t, cells, dt);
    this.solve(cells);
    let miss = 0, held = 0;
    for (let t = 0; t < NT; t++) {
      const o = t * TRACKER_FLOATS;
      for (let r = 0; r < LIMIT.RING; r++) this.state[o + 8 + r] = Math.min(LIMIT.EMPTY_AGE, this.state[o + 8 + r] + dt);
      const vf = windowValue(cells, this.a, this.k, t >> 1, t & 1);
      const v = vf + this.beta * (this.state[o + 3] - vf);
      this.shown[t] = v;
      if (this.mode[t] === MODE.HELD) { held++; miss = Math.max(miss, this.lo[t] - v, v - this.hi[t]); }
      this.state[o + 5] = this.level[t];
      this.state[o + 6] = this.pinNow[t];
      this.update(t, v, dt);
    }
    if (g[1] > 0) { g[1] = g[1] - dt > 0 ? g[1] - dt : 0; if (g[1] === 0) g[0] = 0; }
    else { g[0] = flashing ? g[0] + dt : Math.max(0, g[0] - dt); if (g[0] >= LIMIT.RUN_S) { g[1] = LIMIT.REST_S; g[0] = 0; } }
    g[2]++;
    g[3] = this.beta; g[4] = held; g[5] = this.leaks; g[6] = miss;
    return { a: this.a, k: this.k, beta: this.beta };
  }
  held() { let n = 0; for (let t = 0; t < NT; t++) n += this.mode[t] === MODE.HELD ? 1 : 0; return n; }
}

// ------------------------------------------------------------------------------------------ the flash counter --
// The verifier's method (2026-10-24): turning points of a per-frame series with a hysteresis, transitions between
// successive turning points of at least `thr` (with the darker end under `dark`, 0.8 for luminance), counted at the later
// turning point; flashes in a window = transitions / 2.
export function transitions(L, hyst = 0.02, thr = 0.1, dark = 0.8) {
  if (!L.length) return [];
  const ext = []; let dir = 0; let hi = { i: 0, v: L[0] }, lo = { i: 0, v: L[0] }, cand = null;
  for (let i = 1; i < L.length; i++) {
    const v = L[i];
    if (dir === 0) {
      if (v > hi.v) hi = { i, v };
      if (v < lo.v) lo = { i, v };
      if (hi.v - lo.v >= hyst) { if (hi.i > lo.i) { ext.push(lo); dir = 1; cand = hi; } else { ext.push(hi); dir = -1; cand = lo; } }
    } else if (dir === 1) {
      if (v > cand.v) cand = { i, v }; else if (cand.v - v >= hyst) { ext.push(cand); dir = -1; cand = { i, v }; }
    } else if (v < cand.v) cand = { i, v }; else if (v - cand.v >= hyst) { ext.push(cand); dir = 1; cand = { i, v }; }
  }
  if (cand) ext.push(cand);
  const tr = [];
  for (let k = 1; k < ext.length; k++) {
    const a = ext[k - 1], b = ext[k], d = b.v - a.v;
    if (Math.abs(d) >= thr && Math.min(a.v, b.v) < dark) tr.push({ from: a.i, at: b.i, d: +d.toFixed(4) });
  }
  return tr;
}
// The most of `times` (ascending) inside any window of `win` (same units): t_j and t_i share a window when t_i - t_j < win.
export function maxInWindow(times, win) {
  let best = 0;
  for (let i = 0, j = 0; i < times.length; i++) { while (times[i] - times[j] >= win) j++; best = Math.max(best, i - j + 1); }
  return best;
}
// Strict flashes: pairs of OPPOSING transitions (a rise and a fall, either order), paired greedily in time order, the most
// inside any window of `win` frames (the round-1 verifier's count).
export function maxPairsInWindow(tr, win = 60) {
  let best = 0;
  for (let j = 0; j < tr.length; j++) {
    let pend = 0, n = 0;
    for (let i = j; i < tr.length && tr[i].at - tr[j].at < win; i++) {
      const sg = Math.sign(tr[i].d);
      if (pend === 0) pend = sg; else if (sg !== pend) { n++; pend = 0; } else pend = sg;
    }
    best = Math.max(best, n);
  }
  return best;
}
// Flashes in a per-frame series at `fps`: the transitions, the most in any second, the strict pairs, and the longest
// "flashing run" (the longest stretch in which every frame's trailing second held at least two flashes, i.e. four
// transitions: gate v2's notion of "flashing" for its forced rest), in seconds.
export function flashReport(L, { fps = 60, hyst = 0.02, thr = 0.1, dark = 0.8 } = {}) {
  const tr = transitions(L, hyst, thr, dark);
  const times = tr.map((t) => t.at / fps);
  const maxTr = maxInWindow(times, 1);
  let run = 0, best = 0, j = 0;
  for (let f = 0; f < L.length; f++) {
    const now = f / fps;
    while (j < times.length && times[j] <= now) j++;
    let n = 0;
    for (let q = j - 1; q >= 0 && now - times[q] < 1; q--) n++;
    run = n >= 4 ? run + 1 / fps : 0;
    best = Math.max(best, run);
  }
  return { transitions: tr.length, max_transitions_in_1s: maxTr, max_flashes_in_1s: maxTr / 2,
           max_pairs_in_1s: maxPairsInWindow(tr, fps), longest_run_s: +best.toFixed(3), list: tr };
}
