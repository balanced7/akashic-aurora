// Virtual Stage, the final-frame flash limiter: arsenal/web/stage/flash.js (pure ES module). Tests:
// tests/stage_flash.test.mjs.
//
// The house rule: at most three full-frame flashes in any second (WCAG 2.3.1), red included, judged on the picture the
// viewer actually gets, after every layer. The page's gate v2 limiter (vj-gate.js and its GPU twin vj-limiter.js) is the
// house's answer on the VJ page; this module is the Stage's own copy of the same CONTRACT, small enough for a standalone
// page. Constants follow gate v2's LIMIT table.
//
// v2 (2026-10-28, the flash toggle; Daniel on v1: "it freezes the render though, those blocks stall, can we remove or
// tweak the system?"). v1 controlled each of the 16 cells with a constant gain and a HOLD that blended the cell toward
// the last shown frame, and when its sweeps could not meet a window it held the window's cells completely (the last
// frame again): during heavy play whole tiles froze with hard edges while the rest moved. v2 keeps the measurement, the
// windows, the counters and every limit of v1, and changes only how a held window is met:
//   - the controls are SMOOTH FIELDS over the 5 x 5 corners of the cells (gate v2's approach), interpolated with
//     smoothstep-bilinear "hats" that are continuous and flat at every cell border, so an intervention reads as a soft
//     local dimming or a soft glow, never a tile with an edge;
//   - a window that would RISE too often is darkened (gain a, 0..1, taken first from the corners whose cells rose since
//     the last shown frame, in proportion to their rise);
//   - a window that would FALL too often is first given back any gain other windows took, then LIFTED: a glow in the
//     colour the region showed last frame (colour lift c), then toward white (white lift w) only if that is not enough;
//     no previous-frame detail is shown, so nothing freezes;
//   - once the limiter has had to act on a window, its budget runs out in its DARK state (gate v2's partial hold,
//     PARTIAL below): with four transitions in its second it may still fall but not rise, so a strobe that keeps
//     spending its budget dims and stays dim instead of sticking lit (a window that never needed help is held as in v1,
//     so a programmed show inside the budget is still never touched);
//   - only if the fields cannot meet every held window does one blend toward the previous SHOWN frame (beta, over the
//     whole frame: an echo with no edge, gate v2's fallback) finish the job; the smallest that meets them all.
//
//   MEASURE   the final frame in 4 x 4 cells (the meter's own: 16-pixel blocks shared out as evenly as they divide); per
//             cell and signal, the four corner-hat moments (the mean over the cell of hat_j(p) x the pixel's value), so
//             the shown value of any window is an EXACT linear function of the corner controls; plus the cell's mean
//             linear RGB (the lift's colour). Signals: relative luminance (sRGB-decoded, WCAG weights) and the WCAG red
//             quantity (max(0, R - G - B) x 320 over saturated-red pixels, R / (R + G + B) >= 0.8).
//   WINDOWS   the 18 windows of a quarter of the screen or more: the whole frame, the nine 2 x 2 blocks, the four rows,
//             the four columns. (Unchanged.)
//   COUNT     per window and signal, online: turning points with a hysteresis (0.02; red 2 on the x320 scale); a
//             transition is counted from the frame its swing reaches TH (0.07, the standard's 0.1 less a margin; red 14 of
//             20). At most N_MAX = 5 counted transitions in any 1.01 s. Why five and not six: a transition reaches TH no
//             later than it ENDS, and each one's reach comes after the previous one's end, so k ends inside any second
//             carry at least k - 1 reaches inside it; five reaches allow at most six ends: three flashes, counted the way
//             the verifier counts them (at the later turning point). (Unchanged.)
//   HOLD      HARD, v1's limit exactly: a window with no budget left (or resting) may only show values that start no new
//             transition, inside the no-commit interval of its own counter. SOFT, v2's policy, for a BUSY window (one the
//             limiter has had to act on, until it has room for a whole flash again): PARTIAL -- with one transition left a
//             rise would need two (its fall too), so only a fall may start -- and, once spent, no turning up from a
//             falling run's low (a new turning point would leave a floor a later, darker frame could not keep). A window
//             that never needed help is held exactly as v1 held it, so a show inside the budget is never touched.
//   SOLVE     SOFT sweeps: local Kaczmarz projections of the fields onto the soft intervals and a lift cap (a lift holds
//             a window just above its floor, never higher), each correction where the light rose (a cut) or fell (a lift);
//             then HARD sweeps: exact projections, in one metric so they converge, onto the hard intervals and each
//             corner's box; then the beta fallback for whatever the fields could not meet. The gradients are exact (the
//             corner moments). Free windows add no constraint: with nothing held every gain is exactly 1, every lift 0,
//             beta 0, and the apply pass copies the frame untouched.
//   APPLY     per pixel, linear light: x' = (1 - beta) (a(p) x + l(p)) + beta prev, a(p) = sum_j hat_j(p) a_j and
//             l(p) = sum_j hat_j(p) (c_j q_j + w_j), with a_j + c_j + w_j <= 1 and every q_j <= 1 (so x' <= 1: no clip the
//             model does not know). q_j carries no red quantity (r <= g + b), so a lift never adds red.
//   REST      ITU-R BT.1702: while some window holds 4 full-size (0.09) transitions in its last second for 5 s, every
//             window is held for 2 s. (Unchanged.)
// interventions counts the frames whose controls were not the identity: the receipt for a well-programmed show is ZERO.

export const FLASH_API = "arsenal.stage-flash/v2";
export const LIMIT = Object.freeze({
  N_MAX: 5, WINDOW_S: 1.01, RUN_S: 5, REST_S: 2, REST_COUNT: 4,
  TH: [0.07, 14], HYST: [0.02, 2], TH_REST: [0.09, 18], MARGIN: [0.004, 0.5],
});
// how a window is met (v2): the policy, not the limit
export const SOLVE = Object.freeze({
  PARTIAL: true,          // with one transition left, only a fall may start (the budget runs out dark)
  SWEEPS: 24,             // SOFT sweeps: local projections (where the light rose or fell) onto the soft intervals
  HARD_SWEEPS: 600,       // then HARD sweeps: exact projections onto the hard intervals and each corner's box, in one
                          // metric (so they converge whenever the limits can be met; they stop once every window is)
  RELAX: 1.5,             // ... over-relaxed (measured: 1.5 needs the fewest sweeps on the storm cases)
  RISE_FLOOR: 0.05,       // a corner whose cells did not rise still takes this share of a cut (so a cut always lands)
  LIFT_FIRST: 4,          // above a window: a lift some other window asked for goes first (x this weight)
  WHITE: 0.15,            // below a window: the white lift's weight next to the colour lift's 1 (colour first)
  GAIN_BACK: 2,           // below a window: a gain another window took comes back first (x this weight)
  Q_MIN_Y: 0.25,          // the lift colour's luminance floor (deep colours are lightened toward white to reach it)
  // the projections aim this far inside a held interval (per signal: luminance, red x320), so the other windows'
  // projections cannot nudge a met window back out by a rounding's worth; a miss under half of it is no miss (both far
  // inside the counters' own margin, LIMIT.MARGIN, which stays the hard limit)
  AIM: Object.freeze([2e-4, 0.025]),
  // how far a lift may carry a window above the larger of what it showed last frame and what it wants now (slack, so the
  // projections of overlapping windows converge; per signal)
  LIFT_SLACK: Object.freeze([0.008, 1]),
});

export const GX = 4, GY = 4, CX = 5, CY = 5, NCELL = 16, NCORNER = 25;
export const WINDOWS = (() => {
  const w = [[0, 0, 3, 3]];
  for (let by = 0; by < 3; by++) for (let bx = 0; bx < 3; bx++) w.push([bx, by, bx + 1, by + 1]);
  for (let r = 0; r < 4; r++) w.push([0, r, 3, r]);
  for (let c = 0; c < 4; c++) w.push([c, 0, c, 3]);
  return w;
})();

// corner j of cell c (c = cy * 4 + cx): 0 (cx, cy), 1 (cx + 1, cy), 2 (cx, cy + 1), 3 (cx + 1, cy + 1)
export const cornerOf = (c, j) => (((c >> 2) + (j >> 1)) * CX) + (c & 3) + (j & 1);
export const smooth = (q) => q * q * (3 - 2 * q);
// the hat weights of a point (u, v) in 0..1 inside its cell, for the cell's four corners: smoothstep-bilinear, a
// partition of unity, continuous and flat across every cell border (the apply pass uses the same function)
export function hats(u, v, out = new Float64Array(4)) {
  const fx = smooth(Math.min(1, Math.max(0, u))), fy = smooth(Math.min(1, Math.max(0, v)));
  out[0] = (1 - fx) * (1 - fy); out[1] = fx * (1 - fy); out[2] = (1 - fx) * fy; out[3] = fx * fy;
  return out;
}

const LUT = new Float32Array(256).map((_, i) => { const s = i / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
export const srgbToLinear8 = (v) => LUT[v];
const encode1 = (l) => (l <= 0.0031308 ? l * 12.92 : 1.055 * Math.pow(l, 1 / 2.4) - 0.055);
const lumOf = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

// The cell boundaries (in pixels, n + 1 values for an n-pixel axis) the GPU meter uses: 16-pixel blocks
// (ceil(ceil(n / 4) / 4) of them) shared out four ways, block b in cell floor(4 b / blocks); the last block may be short.
export function meterBounds(n) {
  const m2 = Math.ceil(Math.ceil(n / 4) / 4);
  const out = [0, 0, 0, 0, n];
  for (let c = 1; c < 4; c++) out[c] = Math.min(n, 16 * Math.ceil((c * m2) / 4));
  return out;
}

// The meter on the CPU (tests, and the receipts' twin): RGBA8 pixels (w x h, rows bottom-up as readPixels gives them:
// the window family is symmetric, cell (cx, cy) is then counted from the bottom, as on the GPU). Returns
// { L, R (16 cell means), LM, RM (64 corner moments: cell c, corner j at c * 4 + j), rgb (48: cell mean linear RGB) }.
export function cellsFromRGBA8(px, w, h, { bx = meterBounds(w), by = meterBounds(h) } = {}) {
  const out = { L: new Float64Array(16), R: new Float64Array(16), LM: new Float64Array(64), RM: new Float64Array(64), rgb: new Float64Array(48) };
  const hx = new Float64Array(w * 2), cxOf = new Int32Array(w);
  for (let x = 0; x < w; x++) {
    let cx = 0; while (cx < 3 && x >= bx[cx + 1]) cx++;
    cxOf[x] = cx;
    const f = smooth((x + 0.5 - bx[cx]) / Math.max(1, bx[cx + 1] - bx[cx]));
    hx[x * 2] = 1 - f; hx[x * 2 + 1] = f;
  }
  const n = new Float64Array(16);
  for (let y = 0; y < h; y++) {
    let cy = 0; while (cy < 3 && y >= by[cy + 1]) cy++;
    const fy = smooth((y + 0.5 - by[cy]) / Math.max(1, by[cy + 1] - by[cy]));
    for (let x = 0; x < w; x++) {
      const c = cy * 4 + cxOf[x], i = (y * w + x) * 4, r8 = px[i], g8 = px[i + 1], b8 = px[i + 2];
      const lr = LUT[r8], lg = LUT[g8], lb = LUT[b8];
      const L = lumOf(lr, lg, lb);
      const s = r8 + g8 + b8;
      const R = s > 0 && r8 / s >= 0.8 ? Math.max(0, (lr - lg - lb) * 320) : 0;
      const h0 = hx[x * 2] * (1 - fy), h1 = hx[x * 2 + 1] * (1 - fy), h2 = hx[x * 2] * fy, h3 = hx[x * 2 + 1] * fy;
      const o = c * 4;
      out.LM[o] += h0 * L; out.LM[o + 1] += h1 * L; out.LM[o + 2] += h2 * L; out.LM[o + 3] += h3 * L;
      out.RM[o] += h0 * R; out.RM[o + 1] += h1 * R; out.RM[o + 2] += h2 * R; out.RM[o + 3] += h3 * R;
      out.rgb[c * 3] += lr; out.rgb[c * 3 + 1] += lg; out.rgb[c * 3 + 2] += lb;
      n[c]++;
    }
  }
  return finishCells(out, n);
}
// sums -> means (the GPU path reads sums back and finishes them here too)
export function finishCells(out, n) {
  for (let c = 0; c < 16; c++) {
    const k = 1 / Math.max(1, n[c]);
    let L = 0, R = 0;
    for (let j = 0; j < 4; j++) { out.LM[c * 4 + j] *= k; out.RM[c * 4 + j] *= k; L += out.LM[c * 4 + j]; R += out.RM[c * 4 + j]; }
    out.L[c] = L; out.R[c] = R;
    for (let q = 0; q < 3; q++) out.rgb[c * 3 + q] *= k;
  }
  return out;
}
// cells given only as means (v1's format): a uniform cell carries a quarter of its mean on each corner, and grey
export function normalizeCells(cells) {
  if (cells.LM && cells.RM && cells.rgb) return cells;
  const LM = cells.LM || new Float64Array(64), RM = cells.RM || new Float64Array(64), rgb = cells.rgb || new Float64Array(48);
  for (let c = 0; c < 16; c++) {
    if (!cells.LM) for (let j = 0; j < 4; j++) LM[c * 4 + j] = cells.L[c] / 4;
    if (!cells.RM) for (let j = 0; j < 4; j++) RM[c * 4 + j] = cells.R[c] / 4;
    if (!cells.rgb) { rgb[c * 3] = cells.L[c]; rgb[c * 3 + 1] = cells.L[c]; rgb[c * 3 + 2] = cells.L[c]; }
  }
  return { L: cells.L, R: cells.R, LM, RM, rgb };
}

export function windowMean(cells, w) {
  const [x0, y0, x1, y1] = WINDOWS[w];
  let s = 0;
  for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) s += cells[cy * 4 + cx];
  return s / ((x1 - x0 + 1) * (y1 - y0 + 1));
}
const cellsOfWindow = WINDOWS.map(([x0, y0, x1, y1]) => { const o = []; for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) o.push(cy * 4 + cx); return o; });
// how many of a window's cells touch each corner (the lifts' weight: a lift reaches a quarter of each such cell's mean)
const adjOfWindow = cellsOfWindow.map((cs) => { const a = new Float64Array(NCORNER); for (const c of cs) for (let j = 0; j < 4; j++) a[cornerOf(c, j)]++; return a; });

// One window's online counter for one signal. (Unchanged from v1.)
export class Tracker {
  constructor(th, hyst, thRest) {
    this.th = th; this.hyst = hyst; this.thRest = thRest;
    this.dir = 0;          // 0 unknown, +1 rising, -1 falling
    this.ext = null;       // the last turning point's value
    this.cand = null;      // the current run's extreme
    this.lo = null; this.hi = null;   // before the first turning point: the range seen
    this.counted = false;  // the current run has been counted
    this.fullMarked = false;
    this.ends = [];        // times of counted transitions (seconds)
    this.full = [];        // times of full-size transitions
    this.busy = false;     // v2: the limiter has acted on this window since it last had room for a whole flash
  }
  count(t, W = LIMIT.WINDOW_S) { while (this.ends.length && t - this.ends[0] >= W) this.ends.shift(); return this.ends.length; }
  fullCount(t, W = 1) { while (this.full.length && t - this.full[0] >= W) this.full.shift(); return this.full.length; }
  // the interval of values that would start no new counted transition now
  noCommit(margin) {
    if (this.dir === 0) {
      if (this.lo === null) return [-Infinity, Infinity];
      return [this.hi - this.th + margin, this.lo + this.th - margin];
    }
    if (this.dir > 0) return [this.cand - this.th + margin, (this.counted ? Infinity : this.ext + this.th - margin)];
    return [(this.counted ? -Infinity : this.ext - this.th + margin), this.cand + this.th - margin];
  }
  // feed a shown value at time t; returns 1 if a transition was counted this frame
  push(v, t) {
    let counted = 0;
    if (this.dir === 0) {
      if (this.lo === null) { this.lo = this.hi = v; this.loAt = this.hiAt = t; return 0; }
      if (v < this.lo) this.lo = v;
      if (v > this.hi) this.hi = v;
      if (this.hi - this.lo >= this.hyst) {
        // the first turning point: whichever extreme came first
        const rising = v >= this.hi;
        this.dir = rising ? 1 : -1;
        this.ext = rising ? this.lo : this.hi;
        this.cand = v;
        this.counted = false; this.fullMarked = false;
      }
    } else if (this.dir > 0) {
      if (v > this.cand) this.cand = v;
      else if (this.cand - v >= this.hyst) { this.ext = this.cand; this.cand = v; this.dir = -1; this.counted = false; this.fullMarked = false; }
    } else {
      if (v < this.cand) this.cand = v;
      else if (v - this.cand >= this.hyst) { this.ext = this.cand; this.cand = v; this.dir = 1; this.counted = false; this.fullMarked = false; }
    }
    if (this.dir !== 0) {
      const swing = Math.abs(this.cand - this.ext);
      if (!this.counted && swing >= this.th) { this.counted = true; this.ends.push(t); counted = 1; }
      if (!this.fullMarked && swing >= this.thRest) { this.fullMarked = true; this.full.push(t); }
    }
    return counted;
  }
}

export class FrameLimiter {
  constructor() {
    this.trackers = WINDOWS.map(() => [new Tracker(LIMIT.TH[0], LIMIT.HYST[0], LIMIT.TH_REST[0]),
                                       new Tracker(LIMIT.TH[1], LIMIT.HYST[1], LIMIT.TH_REST[1])]);
    this.prevWin = null;           // [lum, red] window values of the last SHOWN frame (exact: what the trackers were fed)
    this.prevCell = null;          // [lum, red, rgb] cell means of the last shown frame (the model: rise/fall, lift colour)
    this.run = 0; this.restUntil = -Infinity;
    this.frames = 0; this.interventions = 0; this.betaFrames = 0; this.restFrames = 0;
    this.dimFrames = 0; this.liftFrames = 0; this.echoFrames = 0;
    this.A = new Float64Array(NCORNER).fill(1);      // gain (darken), per corner
    this.C = new Float64Array(NCORNER);              // colour lift amount, per corner
    this.Wl = new Float64Array(NCORNER);             // white lift amount, per corner
    this.Q = new Float64Array(NCORNER * 3);          // the colour lift's colour (linear RGB, each <= 1), per corner
    this.beta = 0;
    this.cornerA = new Float32Array(NCORNER).fill(1);
    this.cornerL = new Float32Array(NCORNER * 3);    // the lift, per corner (linear RGB): c q + w
    this.gains = { a: 1, b: 0, beta: 0, lift: 0, cornerA: this.cornerA, cornerL: this.cornerL, identity: true };
    this.log = [];
  }
  // cells: {L, R (16 means), LM, RM (64 corner moments), rgb (48)} of the frame as drawn (v1's {L, R} alone are taken as
  // uniform cells); t in seconds. Returns the gains for the apply pass: {cornerA (25), cornerL (25 x RGB), beta,
  // identity}, and for the log a (the smallest gain), b (the largest share of a point not drawn now: beta or a lift).
  step(cellsIn, t, dt = 1 / 60) {
    this.frames++;
    const cells = normalizeCells(cellsIn);
    const nW = WINDOWS.length;
    const resting = t < this.restUntil;
    const M = [cells.LM, cells.RM], D = [cells.L, cells.R];
    // the drawn frame's window values (the identity's), and the last shown ones (the first frame: itself)
    const want = [new Float64Array(nW), new Float64Array(nW)];
    for (let w = 0; w < nW; w++) { want[0][w] = windowMean(cells.L, w); want[1][w] = windowMean(cells.R, w); }
    const P = this.prevWin || [Float64Array.from(want[0]), Float64Array.from(want[1])];
    const PC = this.prevCell || [Float64Array.from(cells.L), Float64Array.from(cells.R), Float64Array.from(cells.rgb)];
    // which windows are held, and the interval each must stay in: HARD, v1's exactly (no budget left, or resting: the
    // no-commit interval of its own counter), and SOFT (inside it), the v2 policy for a BUSY window -- PARTIAL (with one
    // transition left only a fall may start) and, when spent, no new turning point up from a falling run's low
    const held = [];
    for (let w = 0; w < nW; w++) {
      for (let s = 0; s < 2; s++) {
        const tr = this.trackers[w][s];
        const n = resting ? LIMIT.N_MAX : tr.count(t);
        // BUSY: a window the limiter has had to act on stays busy until it has room for a whole flash again (a rise and
        // its fall); a window that never needed help is held exactly as v1 held it (so a show that stays inside the
        // budget is never touched: the receipts' zero interventions)
        if (tr.busy && !resting && n + 2 <= LIMIT.N_MAX) tr.busy = false;
        const spent = resting || n + 1 > LIMIT.N_MAX;
        const partial = SOLVE.PARTIAL && tr.busy && !spent && n + 2 > LIMIT.N_MAX;
        if (!spent && !partial) continue;
        const [ncLo, ncHi] = tr.noCommit(LIMIT.MARGIN[s]);
        const lo = spent ? ncLo : -Infinity, hi = spent ? ncHi : Infinity;
        let slo = lo, shi = partial ? ncHi : hi;
        if (spent && tr.busy && tr.dir < 0) shi = Math.min(shi, tr.cand + tr.hyst - LIMIT.MARGIN[s]);
        if (lo === -Infinity && hi === Infinity && slo === -Infinity && shi === Infinity) continue;
        held.push([w, s, lo, hi, slo, shi]);
        // the drawn frame would leave the hard interval: the limiter acts on this window, which is busy from now on
        if (want[s][w] > hi + 1e-9 || want[s][w] < lo - 1e-9) tr.busy = true;
      }
    }
    const A = this.A, C = this.C, Wl = this.Wl, Q = this.Q;
    A.fill(1); C.fill(0); Wl.fill(0);
    let beta = 0;
    if (held.length) {
      // the lift's colour at each corner: what the cells around it showed last frame, at its brightest (max channel 1),
      // with no red quantity (r <= g + b) and lightened toward white to a luminance of at least Q_MIN_Y
      for (let k = 0; k < NCORNER; k++) {
        const kx = k % CX, ky = (k / CX) | 0;
        let r = 0, g = 0, b = 0, m = 0;
        for (let dy = -1; dy <= 0; dy++) for (let dx = -1; dx <= 0; dx++) {
          const cx = kx + dx, cy = ky + dy;
          if (cx < 0 || cy < 0 || cx > 3 || cy > 3) continue;
          const c = cy * 4 + cx;
          r += PC[2][c * 3]; g += PC[2][c * 3 + 1]; b += PC[2][c * 3 + 2]; m++;
        }
        r /= m; g /= m; b /= m;
        if (r > g + b) r = g + b;
        const mx = Math.max(r, g, b);
        if (mx > 1e-6) { r /= mx; g /= mx; b /= mx; } else { r = g = b = 1; }
        const y = lumOf(r, g, b);
        if (y < SOLVE.Q_MIN_Y) { const f = (SOLVE.Q_MIN_Y - y) / (1 - y); r += (1 - r) * f; g += (1 - g) * f; b += (1 - b) * f; }
        Q[k * 3] = r; Q[k * 3 + 1] = g; Q[k * 3 + 2] = b;
      }
      // per held window: its exact gradients (gain: the corner moments; lifts: a quarter of each adjacent cell)
      const grads = held.map(([w, s]) => {
        const gA = new Float64Array(NCORNER), gC = new Float64Array(NCORNER), gW = new Float64Array(NCORNER);
        const cs = cellsOfWindow[w], inv = 1 / cs.length;
        for (const c of cs) for (let j = 0; j < 4; j++) gA[cornerOf(c, j)] += M[s][c * 4 + j] * inv;
        if (s === 0) {
          const adj = adjOfWindow[w];
          for (let k = 0; k < NCORNER; k++) if (adj[k]) { gW[k] = adj[k] * 0.25 * inv; gC[k] = gW[k] * lumOf(Q[k * 3], Q[k * 3 + 1], Q[k * 3 + 2]); }
        }
        // where the light rose, and where it fell, since the last shown frame (cells, then their corners)
        const rise = new Float64Array(NCORNER), fall = new Float64Array(NCORNER);
        for (const c of cs) {
          const d = D[s][c] - PC[s][c];
          for (let j = 0; j < 4; j++) { const k = cornerOf(c, j); if (d > 0) rise[k] += d; else fall[k] -= d; }
        }
        let mr = 0, mf = 0;
        for (let k = 0; k < NCORNER; k++) { mr = Math.max(mr, rise[k]); mf = Math.max(mf, fall[k]); }
        // the shares (0..1); the floor, for a cut or a lift the risers (fallers) alone cannot carry, is added below
        for (let k = 0; k < NCORNER; k++) { rise[k] = mr > 0 ? rise[k] / mr : 0; fall[k] = mf > 0 ? fall[k] / mf : 0; }
        return { gA, gC, gW, rise, fall };
      });
      const value = (i) => { const { gA, gC, gW } = grads[i]; let v = 0; for (let k = 0; k < NCORNER; k++) v += gA[k] * A[k] + gC[k] * C[k] + gW[k] * Wl[k]; return v; };
      const dA = new Float64Array(NCORNER), dC = new Float64Array(NCORNER), dW = new Float64Array(NCORNER);
      // THE LIFT CAP (soft): a lift holds a window just above its floor (or at what it wants, if more), never above it --
      // lifts from overlapping windows add up, and a window carried above its floor would raise its peak and with it the
      // floor of the next frame; held there, a spent lit region settles a hair under the threshold below its peak
      const liftCap = held.map(([w, s, , , slo]) => (slo > -Infinity ? Math.max(slo + 4 * SOLVE.AIM[s], want[s][w]) + SOLVE.LIFT_SLACK[s] : Infinity));
      for (let sweep = 0; sweep < SOLVE.SWEEPS; sweep++) {
        let moved = false;
        for (let i = 0; i < held.length; i++) {
          const sg = held[i][1], lo = held[i][4], hi = held[i][5];
          const v = value(i), aim = SOLVE.AIM[sg];
          const { gA, gC, gW, rise, fall } = grads[i];
          if (v > liftCap[i] + 1e-9 && v <= hi + 0.5 * aim) {
            // too much lift here (from other windows): take lift back, lift only, never below the cap
            let den = 0;
            for (let k = 0; k < NCORNER; k++) { dC[k] = C[k] > 0 ? gC[k] : 0; dW[k] = Wl[k] > 0 ? gW[k] : 0; den += gC[k] * dC[k] + gW[k] * dW[k]; }
            if (den > 1e-15) {
              const lam = (v - liftCap[i]) / den;
              for (let k = 0; k < NCORNER; k++) { if (dC[k]) C[k] = Math.max(0, C[k] - lam * dC[k]); if (dW[k]) Wl[k] = Math.max(0, Wl[k] - lam * dW[k]); }
              moved = true;
            }
          } else if (v > hi + 0.5 * aim) {
            // take light back: a lift another window asked for first, then gain from the corners whose cells rose (in
            // proportion to their rise); from every corner (in proportion to its light) only when the risers cannot
            const target = hi - aim;
            let have = 0;
            for (let k = 0; k < NCORNER; k++) have += gC[k] * C[k] + gW[k] * Wl[k] + (rise[k] > 0 ? gA[k] * A[k] : 0);
            const floor = have >= (v - target) * 1.0001 ? 0 : SOLVE.RISE_FLOOR;
            let den = 0;
            for (let k = 0; k < NCORNER; k++) {
              dC[k] = C[k] > 0 ? gC[k] * SOLVE.LIFT_FIRST : 0;
              dW[k] = Wl[k] > 0 ? gW[k] * SOLVE.LIFT_FIRST : 0;
              dA[k] = A[k] > 0 ? gA[k] * (rise[k] + floor) : 0;
              den += gA[k] * dA[k] + gC[k] * dC[k] + gW[k] * dW[k];
            }
            if (den <= 1e-15) continue;
            const lam = (v - target) / den;
            for (let k = 0; k < NCORNER; k++) {
              if (dA[k]) A[k] = Math.max(0, A[k] - lam * dA[k]);
              if (dC[k]) C[k] = Math.max(0, C[k] - lam * dC[k]);
              if (dW[k]) Wl[k] = Math.max(0, Wl[k] - lam * dW[k]);
            }
            moved = true;
          } else if (v < lo - 0.5 * aim) {
            // give light back where it fell: gain another window took first; then a glow in the region's own colour,
            // then white; where there is no room left under a + c + w = 1, the glow takes the gain's place (only where
            // it is the brighter of the two: the content keeps moving under it, dimmer)
            const target = lo + aim;
            let have = 0;
            for (let k = 0; k < NCORNER; k++) if (fall[k] > 0) have += Math.max(gA[k], gC[k], gW[k]) - (gA[k] * A[k] + gC[k] * C[k] + gW[k] * Wl[k]);
            const floor = have >= (target - v) * 1.0001 ? 0 : SOLVE.RISE_FLOOR;
            let den = 0;
            for (let k = 0; k < NCORNER; k++) {
              const wk = fall[k] + floor, room = 1 - A[k] - C[k] - Wl[k];
              if (room > 1e-12) {
                dA[k] = gA[k] * wk * SOLVE.GAIN_BACK;
                dC[k] = gC[k] * wk;
                dW[k] = gW[k] * wk * SOLVE.WHITE;
              } else {
                dC[k] = gC[k] > gA[k] && A[k] > 0 ? (gC[k] - gA[k]) * wk : 0;
                dW[k] = gW[k] > gA[k] && A[k] > 0 ? (gW[k] - gA[k]) * wk * SOLVE.WHITE : 0;
                dA[k] = -(dC[k] + dW[k]);
              }
              den += gA[k] * dA[k] + gC[k] * dC[k] + gW[k] * dW[k];
            }
            if (den <= 1e-15) continue;
            const lam = (target - v) / den;
            for (let k = 0; k < NCORNER; k++) {
              if (dA[k]) A[k] = Math.min(1, Math.max(0, A[k] + lam * dA[k]));
              if (dC[k]) C[k] = Math.max(0, C[k] + lam * dC[k]);
              if (dW[k]) Wl[k] = Math.max(0, Wl[k] + lam * dW[k]);
              // a + c + w <= 1 (no clip): the white lift gives way first, then the gain, then the colour lift
              let ex = A[k] + C[k] + Wl[k] - 1;
              if (ex > 0) { const d = Math.min(Wl[k], ex); Wl[k] -= d; ex -= d; }
              if (ex > 0) { const d = Math.min(A[k], ex); A[k] -= d; ex -= d; }
              if (ex > 0) C[k] -= ex;
            }
            moved = true;
          }
        }
        if (!moved) break;
      }
      // THE HARD PHASE: from where the soft phase left the fields, exact projections (in one metric, so they converge)
      // onto every held window's hard interval (aiming a hair inside) and every corner's box (0 <= a <= 1, c, w >= 0,
      // a + c + w <= 1), moving the fields only as far as the hard limits need.
      this._hard(held, grads);
      // the fallback: the smallest blend toward the previous shown frame that meets every held window
      for (let i = 0; i < held.length; i++) {
        const [w, s, lo, hi] = held[i];
        const v = value(i), p = P[s][w];
        const tol = 0.5 * SOLVE.AIM[s];
        if (v > hi + tol && p < v) beta = Math.max(beta, (v - hi) / (v - p));
        else if (v < lo - tol && p > v) beta = Math.max(beta, (lo - v) / (p - v));
      }
      beta = Math.min(1, beta);
    }
    this.beta = beta;
    // the shown frame (the model): windows exactly, cells for the next frame's rise/fall and lift colour
    const shownWin = [new Float64Array(nW), new Float64Array(nW)];
    const cellVal = (c, s) => {
      let v = 0;
      for (let j = 0; j < 4; j++) {
        const k = cornerOf(c, j);
        v += A[k] * M[s][c * 4 + j];
        if (s === 0) v += 0.25 * (C[k] * lumOf(Q[k * 3], Q[k * 3 + 1], Q[k * 3 + 2]) + Wl[k]);
      }
      return v;
    };
    const next = [new Float64Array(16), new Float64Array(16), new Float64Array(48)];
    for (let c = 0; c < 16; c++) {
      for (let s = 0; s < 2; s++) next[s][c] = (1 - beta) * cellVal(c, s) + beta * PC[s][c];
      // the colour (only the lift's colour reads it): the cell's gain as its corners average it, its lift as they add it
      let ga = 0; const lr = [0, 0, 0];
      for (let j = 0; j < 4; j++) { const k = cornerOf(c, j); ga += 0.25 * A[k]; for (let q = 0; q < 3; q++) lr[q] += 0.25 * (C[k] * Q[k * 3 + q] + Wl[k]); }
      for (let q = 0; q < 3; q++) next[2][c * 3 + q] = (1 - beta) * (ga * cells.rgb[c * 3 + q] + lr[q]) + beta * PC[2][c * 3 + q];
    }
    for (let w = 0; w < nW; w++) for (let s = 0; s < 2; s++) shownWin[s][w] = windowMean(next[s], w);
    // the identity, the log, the counters
    let a = 1, lift = 0, dim = false, lifted = false;
    for (let k = 0; k < NCORNER; k++) {
      a = Math.min(a, A[k]); lift = Math.max(lift, C[k] + Wl[k]);
      if (A[k] !== 1) dim = true;
      if (C[k] !== 0 || Wl[k] !== 0) lifted = true;
    }
    const identity = !dim && !lifted && beta === 0;
    if (!identity) {
      this.interventions++;
      if (dim) this.dimFrames++;
      if (lifted) this.liftFrames++;
      if (beta > 0) this.echoFrames++;
      if (beta >= 0.999) this.betaFrames++;
      if (this.log.length < 256) this.log.push({ t: +t.toFixed(3), a: +a.toFixed(4), lift: +lift.toFixed(4), beta: +beta.toFixed(4), held: held.length });
    }
    if (resting) this.restFrames++;
    // feed the trackers what is SHOWN, and keep it for the next frame
    let maxFull = 0;
    for (let w = 0; w < nW; w++) {
      this.trackers[w][0].push(shownWin[0][w], t);
      this.trackers[w][1].push(shownWin[1][w], t);
      maxFull = Math.max(maxFull, this.trackers[w][0].fullCount(t), this.trackers[w][1].fullCount(t));
    }
    this.prevWin = shownWin;
    this.prevCell = next;
    // the forced rest after five seconds of flashing
    if (!resting) {
      this.run = maxFull >= LIMIT.REST_COUNT ? this.run + dt : 0;
      if (this.run >= LIMIT.RUN_S) { this.restUntil = t + LIMIT.REST_S; this.run = 0; }
    }
    for (let k = 0; k < NCORNER; k++) {
      this.cornerA[k] = A[k];
      for (let q = 0; q < 3; q++) this.cornerL[k * 3 + q] = C[k] * Q[k * 3 + q] + Wl[k];
    }
    const g = this.gains;
    g.a = a; g.b = Math.max(beta, lift); g.beta = beta; g.lift = lift; g.identity = identity;
    return g;
  }
  // v1's name for the last shown frame's cell means ([luminance, red]), read by tests/stage_atmos.test.mjs
  get prevCells() { return this.prevCell ? [this.prevCell[0], this.prevCell[1]] : null; }
  // The hard phase (see step). held: [w, s, lo, hi, ...]; grads: per held row {gA, gC, gW, rise, fall}.
  _hard(held, grads) {
    const A = this.A, C = this.C, Wl = this.Wl, NV = NCORNER * 3;
    const m = held.length;
    // the metric (fixed for the frame, so the steps stay exact): a corner where some held window's light rose or fell
    // moves up to twenty times more readily than one where nothing changed, so the hard phase stays local too
    const D = new Float64Array(NV);
    for (let k = 0; k < NCORNER; k++) {
      let wk = SOLVE.RISE_FLOOR;
      for (const g of grads) wk = Math.max(wk, g.rise[k], g.fall[k]);
      D[k] = D[NCORNER + k] = D[2 * NCORNER + k] = wk;
    }
    const G = held.map((_, i) => { const g = new Float64Array(NV), { gA, gC, gW } = grads[i]; g.set(gA, 0); g.set(gC, NCORNER); g.set(gW, 2 * NCORNER); return g; });
    const x = new Float64Array(NV);
    x.set(A, 0); x.set(C, NCORNER); x.set(Wl, 2 * NCORNER);
    // the exact projection of corner k's (a, c, w) onto its box: clipped at 0 (and a at 1); if that leaves
    // a + c + w > 1, onto the face a + c + w = 1 instead (the simplex projection, three values sorted by hand)
    const box = (v, k) => {
      const y0 = v[k], y1 = v[NCORNER + k], y2 = v[2 * NCORNER + k];
      let a = Math.min(1, Math.max(0, y0)), c = Math.max(0, y1), w = Math.max(0, y2);
      if (a + c + w > 1) {
        let u0 = y0, u1 = y1, u2 = y2, t;
        if (u0 < u1) { t = u0; u0 = u1; u1 = t; }
        if (u1 < u2) { t = u1; u1 = u2; u2 = t; }
        if (u0 < u1) { t = u0; u0 = u1; u1 = t; }
        let th = u0 - 1;
        if (u1 - (u0 + u1 - 1) / 2 > 0) th = (u0 + u1 - 1) / 2;
        if (u2 - (u0 + u1 + u2 - 1) / 3 > 0) th = (u0 + u1 + u2 - 1) / 3;
        a = Math.max(0, y0 - th); c = Math.max(0, y1 - th); w = Math.max(0, y2 - th);
      }
      v[k] = a; v[NCORNER + k] = c; v[2 * NCORNER + k] = w;
    };
    // the corners each row touches (its gradient is zero elsewhere)
    const touch = G.map((g) => { const o = []; for (let k = 0; k < NCORNER; k++) if (g[k] || g[NCORNER + k] || g[2 * NCORNER + k]) o.push(k); return o; });
    const dot = (g, v) => { let t = 0; for (let j = 0; j < NV; j++) t += g[j] * v[j]; return t; };
    const dotD = (g, v) => { let t = 0; for (let j = 0; j < NV; j++) t += g[j] * D[j] * v[j]; return t; };
    // exact projections, over-relaxed, the rows in turn and back (a symmetric sweep), each followed by the boxes
    for (let sweep = 0; sweep < SOLVE.HARD_SWEEPS; sweep++) {
      let miss = false;
      for (let ii = 0; ii < m; ii++) {
        const i = sweep & 1 ? m - 1 - ii : ii;
        const sg = held[i][1], lo = held[i][2], hi = held[i][3], aim = SOLVE.AIM[sg], v = dot(G[i], x);
        let dd = 0;
        if (v > hi + 0.5 * aim) dd = hi - aim - v; else if (v < lo - 0.5 * aim) dd = lo + aim - v; else continue;
        miss = true;
        const g = G[i], gg = dotD(g, g);
        if (gg <= 1e-15) continue;
        const lam = SOLVE.RELAX * dd / gg;
        for (const k of touch[i]) {
          x[k] += lam * D[k] * g[k]; x[NCORNER + k] += lam * D[NCORNER + k] * g[NCORNER + k]; x[2 * NCORNER + k] += lam * D[2 * NCORNER + k] * g[2 * NCORNER + k];
          box(x, k);
        }
      }
      if (!miss) break;
    }
    for (let k = 0; k < NCORNER; k++) { A[k] = x[k]; C[k] = x[NCORNER + k]; Wl[k] = x[2 * NCORNER + k]; }
  }
  // The frozen-tile measure for the receipts (stage_verify's hd, sm, he): hd, the largest share of any point of the
  // shown frame that is the previous shown frame (beta: the fields never show the previous frame); sm, the largest step
  // of the controls (gain, lift, hold) between the two pixels either side of any cell border, the fields evaluated as
  // the apply pass evaluates them (continuous, so a numerical zero); he, a hold of 0.9 or more beside a step of 0.1.
  holdMetrics() {
    const h1 = new Float64Array(4), h2 = new Float64Array(4);
    const ctl = (c, u, v, hh) => {
      hats(u, v, hh);
      let a = 0, l = 0;
      for (let j = 0; j < 4; j++) { const k = cornerOf(c, j); a += hh[j] * this.A[k]; l += hh[j] * (this.C[k] + this.Wl[k]); }
      return [a, l];
    };
    let sm = 0;
    const e = 1e-4;
    for (let cy = 0; cy < 4; cy++) for (let cx = 0; cx < 4; cx++) {
      const c = cy * 4 + cx;
      for (const v of [0.05, 0.5, 0.95]) {
        if (cx < 3) { const p = ctl(c, 1 - e, v, h1), q = ctl(c + 1, e, v, h2); sm = Math.max(sm, Math.abs(p[0] - q[0]), Math.abs(p[1] - q[1])); }
        if (cy < 3) { const p = ctl(c, v, 1 - e, h1), q = ctl(c + 4, v, e, h2); sm = Math.max(sm, Math.abs(p[0] - q[0]), Math.abs(p[1] - q[1])); }
      }
    }
    const hd = this.beta;
    return { hd, sm, he: hd >= 0.9 && sm >= 0.1 ? 1 : 0 };
  }
  stats() {
    let worst = 0;
    for (const pair of this.trackers) for (const tr of pair) worst = Math.max(worst, tr.ends.length);
    return { frames: this.frames, interventions: this.interventions, full_hold_frames: this.betaFrames, rest_frames: this.restFrames,
             dim_frames: this.dimFrames, lift_frames: this.liftFrames, echo_frames: this.echoFrames,
             worst_window_transitions_now: worst, log: this.log.slice(-16) };
  }
}

// The apply pass on the CPU (the GPU's PRESENT_FRAGMENT, line for line; tests and receipts): RGBA8 in, RGBA8 out.
// prev: the last shown frame (RGBA8, same size) or null; gains: what step() returned (identity: a copy).
export function applyRGBA8(px, prev, w, h, gains, { bx = meterBounds(w), by = meterBounds(h) } = {}, out = new Uint8ClampedArray(px.length)) {
  if (!gains || gains.identity) { out.set(px); return out; }
  const A = gains.cornerA, Lf = gains.cornerL, beta = gains.beta || 0;
  const hh = new Float64Array(4);
  for (let y = 0; y < h; y++) {
    let cy = 0; while (cy < 3 && y >= by[cy + 1]) cy++;
    const v = (y + 0.5 - by[cy]) / Math.max(1, by[cy + 1] - by[cy]);
    for (let x = 0; x < w; x++) {
      let cx = 0; while (cx < 3 && x >= bx[cx + 1]) cx++;
      const u = (x + 0.5 - bx[cx]) / Math.max(1, bx[cx + 1] - bx[cx]);
      hats(u, v, hh);
      const c = cy * 4 + cx;
      let a = 0, lr = 0, lg = 0, lb = 0;
      for (let j = 0; j < 4; j++) { const k = cornerOf(c, j); a += hh[j] * A[k]; lr += hh[j] * Lf[k * 3]; lg += hh[j] * Lf[k * 3 + 1]; lb += hh[j] * Lf[k * 3 + 2]; }
      const i = (y * w + x) * 4;
      let r = a * LUT[px[i]] + lr, g = a * LUT[px[i + 1]] + lg, b = a * LUT[px[i + 2]] + lb;
      if (beta > 0 && prev) { r += beta * (LUT[prev[i]] - r); g += beta * (LUT[prev[i + 1]] - g); b += beta * (LUT[prev[i + 2]] - b); }
      out[i] = Math.round(255 * encode1(Math.min(1, Math.max(0, r))));
      out[i + 1] = Math.round(255 * encode1(Math.min(1, Math.max(0, g))));
      out[i + 2] = Math.round(255 * encode1(Math.min(1, Math.max(0, b))));
      out[i + 3] = 255;
    }
  }
  return out;
}

// The page's choice (flash protection, lib/flash-consent.js): on, the limiter decides; off, it is not asked at all and the
// apply pass is the identity (null gains: the frame reaches the canvas as drawn).
export function presentGains(limiter, protect, cells, t, dt) { return protect ? limiter.step(cells, t, dt) : null; }
