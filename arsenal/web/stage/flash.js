// Virtual Stage v0, the final-frame flash limiter: arsenal/web/stage/flash.js (pure ES module). Tests:
// tests/stage_flash.test.mjs.
//
// The house rule: at most three full-frame flashes in any second (WCAG 2.3.1), red included, judged on the picture the
// viewer actually gets, after every layer. The page's gate v2 limiter (vj-gate.js and its GPU twin vj-limiter.js, built
// on its own lane and not on master when this was written) is the house's answer; this module is the stage's own copy of
// the same CONTRACT, small enough for a standalone page, until the stage becomes a set inside vj.html (v1) and runs
// behind gate v2 itself. Constants follow gate v2's LIMIT table.
//
//   MEASURE   the final frame in 4 x 4 cells: the mean relative luminance (sRGB-decoded, WCAG weights) and the mean WCAG
//             red quantity (max(0, R - G - B) x 320 over saturated-red pixels, R / (R + G + B) >= 0.8), as the page's
//             meter reads them from a small reduction of the frame.
//   WINDOWS   the 18 windows of a quarter of the screen or more: the whole frame, the nine 2 x 2 blocks, the four rows,
//             the four columns.
//   COUNT     per window and signal, online: turning points with a hysteresis (0.02; red 2 on the x320 scale); a
//             transition is counted from the frame its swing reaches TH (0.07, the standard's 0.1 less a margin; red 14 of
//             20). At most N_MAX = 5 counted transitions in any 1.01 s. Why five and not six: a transition reaches TH no
//             later than it ENDS, and each one's reach comes after the previous one's end, so k ends inside any second
//             carry at least k - 1 reaches inside it; five reaches allow at most six ends: three flashes, counted the way
//             the verifier counts them (at the later turning point).
//   HOLD      a window with no budget left may only show values that start no new transition: inside the no-commit
//             interval of its own counter (the swing from its last turning point, and the reversal from the current
//             extreme, both stay under TH).
//   SOLVE     per CELL (4 x 4) two controls, found by projections onto the held windows (a few Kaczmarz sweeps): a gain
//             a (0..1) that darkens the cell, and a hold b (0..1) that blends it toward the cell as it was last SHOWN
//             (x' = (1 - b) a x + b prev, exact in linear light). A window above its interval takes the light back from
//             the cells that rose since the last shown frame, in proportion to their rise (then evenly); a window below
//             its interval holds the cells that fell, in proportion to their fall. So a flash in one quadrant is held
//             there and a calm quadrant elsewhere is left alone, and nothing is ever lifted toward grey. If the sweeps
//             cannot meet a held window, its cells are held completely (b = 1: the last shown frame again, which starts no
//             transition by construction). The cells are the meter's own (16-pixel blocks shared out as evenly as they
//             divide), so the apply pass and the meter agree exactly. Gate v2 solves a smooth 5 x 5 field of corner gains
//             instead of piecewise-constant cells (no seam where a held cell meets a free one): that is the v1 upgrade.
//   REST      ITU-R BT.1702: while some window holds 4 full-size (0.09) transitions in its last second for 5 s, every
//             window is held for 2 s.
// interventions counts the frames whose gains were not the identity: the receipt for a well-programmed show is ZERO.

export const FLASH_API = "arsenal.stage-flash/v1";
export const LIMIT = Object.freeze({
  N_MAX: 5, WINDOW_S: 1.01, RUN_S: 5, REST_S: 2, REST_COUNT: 4,
  TH: [0.07, 14], HYST: [0.02, 2], TH_REST: [0.09, 18], MARGIN: [0.004, 0.5],
});

export const WINDOWS = (() => {
  const w = [[0, 0, 3, 3]];
  for (let by = 0; by < 3; by++) for (let bx = 0; bx < 3; bx++) w.push([bx, by, bx + 1, by + 1]);
  for (let r = 0; r < 4; r++) w.push([0, r, 3, r]);
  for (let c = 0; c < 4; c++) w.push([c, 0, c, 3]);
  return w;
})();

const LUT = new Float32Array(256).map((_, i) => { const s = i / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
export const srgbToLinear8 = (v) => LUT[v];

// 4 x 4 cell means from RGBA8 pixels (w x h, rows bottom-up as readPixels gives them: the row order does not change the
// window family, which is symmetric, but cell (cx, cy) is then counted from the bottom).
export function cellsFromRGBA8(px, w, h, out = { L: new Float64Array(16), R: new Float64Array(16) }) {
  out.L.fill(0); out.R.fill(0);
  const n = new Float64Array(16);
  for (let y = 0; y < h; y++) {
    const cy = Math.min(3, Math.floor((y * 4) / h));
    for (let x = 0; x < w; x++) {
      const cx = Math.min(3, Math.floor((x * 4) / w));
      const i = (y * w + x) * 4, r8 = px[i], g8 = px[i + 1], b8 = px[i + 2];
      const lr = LUT[r8], lg = LUT[g8], lb = LUT[b8];
      const c = cy * 4 + cx;
      out.L[c] += 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
      const s = r8 + g8 + b8;
      if (s > 0 && r8 / s >= 0.8) out.R[c] += Math.max(0, (lr - lg - lb) * 320);
      n[c]++;
    }
  }
  for (let c = 0; c < 16; c++) { out.L[c] /= Math.max(1, n[c]); out.R[c] /= Math.max(1, n[c]); }
  return out;
}

export function windowMean(cells, w) {
  const [x0, y0, x1, y1] = WINDOWS[w];
  let s = 0;
  for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) s += cells[cy * 4 + cx];
  return s / ((x1 - x0 + 1) * (y1 - y0 + 1));
}

// One window's online counter for one signal.
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
    this.prevCells = null;       // [lum cell means, red cell means] of the last shown frame
    this.run = 0; this.restUntil = -Infinity;
    this.frames = 0; this.interventions = 0; this.betaFrames = 0; this.restFrames = 0;
    this.cellA = new Float64Array(16).fill(1); this.cellB = new Float64Array(16);
    this.gains = { a: 1, b: 0, cellA: this.cellA, cellB: this.cellB };
    this.log = [];
  }
  // cells: {L: 16 means, R: 16 means (x320 scale)} of the frame as drawn; t in seconds. Returns {cellA, cellB} (and a:
  // the smallest gain, b: the largest hold, for the log): the apply pass shows, in cell c,
  // x' = (1 - cellB[c]) cellA[c] x + cellB[c] prev, per channel in linear light, prev = the last shown frame.
  step(cells, t, dt = 1 / 60) {
    this.frames++;
    const nW = WINDOWS.length;
    const resting = t < this.restUntil;
    const Y = cells.L, Rr = cells.R;
    const P = this.prevCells || [Float64Array.from(Y), Float64Array.from(Rr)];   // the first frame holds to itself
    // which windows are held, and the interval each must stay in
    const held = [];
    for (let w = 0; w < nW; w++) {
      for (let s = 0; s < 2; s++) {
        const tr = this.trackers[w][s];
        const budget = resting ? 0 : LIMIT.N_MAX - tr.count(t);
        if (budget > 0) continue;
        const [lo, hi] = tr.noCommit(LIMIT.MARGIN[s]);
        held.push([w, s, lo, hi]);
      }
    }
    const A = this.cellA, B = this.cellB;
    A.fill(1); B.fill(0);
    const cur = (c, s) => (1 - B[c]) * A[c] * (s === 0 ? Y[c] : Rr[c]) + B[c] * P[s][c];
    const winVal = (w, s) => {
      const [x0, y0, x1, y1] = WINDOWS[w];
      let sum = 0, n = 0;
      for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) { sum += cur(cy * 4 + cx, s); n++; }
      return sum / n;
    };
    const cellsOf = (w) => { const [x0, y0, x1, y1] = WINDOWS[w]; const out = []; for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) out.push(cy * 4 + cx); return out; };
    if (held.length) {
      for (let sweep = 0; sweep < 10; sweep++) {
        let moved = false;
        for (const [w, s, lo, hi] of held) {
          const v = winVal(w, s);
          const cs = cellsOf(w), n = cs.length;
          if (v > hi + 1e-12) {
            // take light back: from the cells that rose (darken them), then evenly
            const E = (v - hi) * n;
            let rise = 0;
            for (const c of cs) rise += Math.max(0, cur(c, s) - P[s][c]);
            const fromRisers = Math.min(E, rise), rest = E - fromRisers;
            for (const c of cs) {
              const x = cur(c, s);
              if (x <= 0) continue;
              let cut = rise > 0 ? Math.max(0, x - P[s][c]) * (fromRisers / rise) : 0;
              if (rest > 0) cut += rest * (x / Math.max(1e-12, v * n));
              // x = (1 - b) a X + b p: lowering a by f lowers x by (1 - b) a X (1 - f)
              const base = (1 - B[c]) * A[c] * (s === 0 ? Y[c] : Rr[c]);
              if (base <= 1e-12) continue;
              A[c] *= Math.max(0, 1 - Math.min(cut, base) / base);
            }
            moved = true;
          } else if (v < lo - 1e-12) {
            // hold the cells that fell (toward what they showed), in proportion to their fall
            const D = (lo - v) * n;
            let fall = 0;
            for (const c of cs) fall += Math.max(0, P[s][c] - cur(c, s));
            if (fall <= 1e-12) continue;
            const k = Math.min(1, D / fall);
            for (const c of cs) {
              const x = cur(c, s), p = P[s][c];
              if (p <= x) continue;
              // raise x by k (p - x): b' with (1 - b') base + b' p = x + k (p - x)
              const base = (1 - B[c]) > 1e-12 ? (x - B[c] * p) / (1 - B[c]) : p;
              const target = x + k * (p - x);
              B[c] = Math.min(1, p - base > 1e-12 ? (target - base) / (p - base) : 1);
            }
            moved = true;
          }
        }
        if (!moved) break;
      }
      // whatever is still outside its interval: hold its cells completely
      for (const [w, s, lo, hi] of held) {
        const v = winVal(w, s);
        if (v < lo - 1e-6 || v > hi + 1e-6) { for (const c of cellsOf(w)) { B[c] = 1; } this.betaFrames++; }
      }
    }
    let a = 1, b = 0;
    for (let c = 0; c < 16; c++) { a = Math.min(a, A[c]); b = Math.max(b, B[c]); }
    const identity = a === 1 && b === 0;
    if (!identity) {
      this.interventions++;
      if (this.log.length < 256) this.log.push({ t: +t.toFixed(3), a: +a.toFixed(4), b: +b.toFixed(4), held: held.length });
    }
    if (resting) this.restFrames++;
    // feed the trackers what is SHOWN, and keep the shown cells for the next frame
    let maxFull = 0;
    for (let w = 0; w < nW; w++) {
      this.trackers[w][0].push(winVal(w, 0), t);
      this.trackers[w][1].push(winVal(w, 1), t);
      maxFull = Math.max(maxFull, this.trackers[w][0].fullCount(t), this.trackers[w][1].fullCount(t));
    }
    const next = [new Float64Array(16), new Float64Array(16)];
    for (let c = 0; c < 16; c++) { next[0][c] = cur(c, 0); next[1][c] = cur(c, 1); }
    this.prevCells = next;
    // the forced rest after five seconds of flashing
    if (!resting) {
      this.run = maxFull >= LIMIT.REST_COUNT ? this.run + dt : 0;
      if (this.run >= LIMIT.RUN_S) { this.restUntil = t + LIMIT.REST_S; this.run = 0; }
    }
    this.gains.a = a; this.gains.b = b; this.gains.cellA = A; this.gains.cellB = B;
    return this.gains;
  }
  stats() {
    let worst = 0;
    for (const pair of this.trackers) for (const tr of pair) worst = Math.max(worst, tr.ends.length);
    return { frames: this.frames, interventions: this.interventions, full_hold_frames: this.betaFrames, rest_frames: this.restFrames,
             worst_window_transitions_now: worst, log: this.log.slice(-16) };
  }
}
