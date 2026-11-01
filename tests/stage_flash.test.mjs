// Virtual Stage: the final-frame flash limiter (arsenal/web/stage/flash.js, v2). node --test tests/stage_flash.test.mjs
// Judged with an independent counter written here from the 2026-10-24 verifier's rule (turning points with a hysteresis
// of 0.02, a transition is a swing of 0.1 or more whose darker end is under 0.8, counted at its later turning point;
// flashes in a second = transitions / 2), never with the limiter's own trackers. The shown values are computed here from
// the gains the limiter returns (the apply pass's model, written out again), or, end to end, by applying the gains to
// pixels and metering the result with a meter written here (the verifier's quarters).
import { test } from "node:test";
import assert from "node:assert/strict";
import { WINDOWS, FrameLimiter, cellsFromRGBA8, applyRGBA8, windowMean, LIMIT, SOLVE, cornerOf, presentGains } from "../arsenal/web/stage/flash.js";

function transitions(L, hyst = 0.02, thr = 0.1) {
  const ext = []; let dir = 0, hi = { i: 0, v: L[0] }, lo = { i: 0, v: L[0] }, cand = null;
  for (let i = 1; i < L.length; i++) {
    const v = L[i];
    if (dir === 0) {
      if (v > hi.v) hi = { i, v };
      if (v < lo.v) lo = { i, v };
      if (hi.v - lo.v >= hyst) { if (hi.i > lo.i) { ext.push(lo); dir = 1; cand = hi; } else { ext.push(hi); dir = -1; cand = lo; } }
    } else if (dir === 1) { if (v > cand.v) cand = { i, v }; else if (cand.v - v >= hyst) { ext.push(cand); dir = -1; cand = { i, v }; } }
    else { if (v < cand.v) cand = { i, v }; else if (v - cand.v >= hyst) { ext.push(cand); dir = 1; cand = { i, v }; } }
  }
  if (cand) ext.push(cand);
  const tr = [];
  for (let k = 1; k < ext.length; k++) { const a = ext[k - 1], b = ext[k]; if (Math.abs(b.v - a.v) >= thr && Math.min(a.v, b.v) < 0.8) tr.push(b.i); }
  return tr;
}
function maxFlashesPerSecond(series, fps = 60, hyst = 0.02, thr = 0.1) {
  const t = transitions(series, hyst, thr).map((i) => i / fps);
  let best = 0;
  for (let i = 0; i < t.length; i++) { let n = 0; for (let j = i; j < t.length && t[j] - t[i] < 1; j++) n++; best = Math.max(best, n); }
  return best / 2;
}
const LUM = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
// the apply pass's model, cell by cell: shown = (1 - beta) (sum_j a_k M_cj + 1/4 sum_j Y(l_k)) + beta prev
function shownCells(c, g, prev) {
  const L = new Float64Array(16), R = new Float64Array(16);
  for (let i = 0; i < 16; i++) {
    let l = 0, r = 0;
    for (let j = 0; j < 4; j++) {
      const k = cornerOf(i, j);
      const lm = c.LM ? c.LM[i * 4 + j] : c.L[i] / 4, rm = c.RM ? c.RM[i * 4 + j] : c.R[i] / 4;
      l += g.cornerA[k] * lm + 0.25 * LUM(g.cornerL[k * 3], g.cornerL[k * 3 + 1], g.cornerL[k * 3 + 2]);
      r += g.cornerA[k] * rm;
    }
    const b = g.beta || 0;
    L[i] = (1 - b) * l + b * (prev ? prev.L[i] : c.L[i]);
    R[i] = (1 - b) * r + b * (prev ? prev.R[i] : c.R[i]);
  }
  return { L, R };
}
// drive the limiter with a per-frame cell function; return the SHOWN window series and the limiter
function drive(cellsAt, frames, fps = 60, each = null) {
  const lim = new FrameLimiter();
  const shown = WINDOWS.map(() => []), shownR = WINDOWS.map(() => []);
  let prev = null;
  for (let f = 0; f < frames; f++) {
    const c = cellsAt(f);
    const g = lim.step(c, f / fps, 1 / fps);
    const s = shownCells(c, g, prev);
    prev = s;
    WINDOWS.forEach((_, w) => { shown[w].push(windowMean(s.L, w)); shownR[w].push(windowMean(s.R, w)); });
    if (each) each(f, lim, g);
  }
  return { lim, shown, shownR };
}
const uniform = (l, r = 0) => ({ L: new Float64Array(16).fill(l), R: new Float64Array(16).fill(r) });

test("18 windows, each at least a quarter of the screen", () => {
  assert.equal(WINDOWS.length, 18);
  for (const [x0, y0, x1, y1] of WINDOWS) assert.ok((x1 - x0 + 1) * (y1 - y0 + 1) >= 4);
});

test("the limits are v1's, unchanged", () => {
  assert.deepEqual({ ...LIMIT, TH: [...LIMIT.TH], HYST: [...LIMIT.HYST], TH_REST: [...LIMIT.TH_REST], MARGIN: [...LIMIT.MARGIN] },
    { N_MAX: 5, WINDOW_S: 1.01, RUN_S: 5, REST_S: 2, REST_COUNT: 4, TH: [0.07, 14], HYST: [0.02, 2], TH_REST: [0.09, 18], MARGIN: [0.004, 0.5] });
});

test("a calm, beat-locked show passes untouched: zero interventions", () => {
  // a 60 -> 100 % lift on every beat at 150 BPM over the whole frame at a modest level, plus a slow drift
  const { lim } = drive((f) => {
    const beat = (f / 60) * 2.5, x = beat - Math.floor(beat);
    return uniform(0.12 * (0.6 + 0.4 * Math.exp(-x * 5)) + 0.02 * Math.sin(f / 90));
  }, 60 * 20);
  assert.equal(lim.stats().interventions, 0);
});

test("a 10 Hz full-frame strobe is held to at most 3 flashes a second in every window, never by an echo of the last frame", () => {
  const { lim, shown } = drive((f) => uniform(Math.floor(f / 3) % 2 ? 0.6 : 0.03), 60 * 6);
  for (let w = 0; w < WINDOWS.length; w++) assert.ok(maxFlashesPerSecond(shown[w]) <= 3, `window ${w}: ${maxFlashesPerSecond(shown[w])}`);
  const st = lim.stats();
  assert.ok(st.interventions > 0, "it had to act");
  // dimmed while it waits (and, the first time its budget runs out lit, held up by a glow): never a frame echoed
  assert.ok(st.dim_frames > 0);
  assert.equal(st.echo_frames, 0, "no echo of the previous frame");
  assert.equal(st.full_hold_frames, 0, "no full hold");
});

test("a strobe in one quadrant is held there; the opposite quadrant moving slowly is left alone", () => {
  let keep = 1;
  const { shown, lim } = drive((f) => {
    const c = uniform(0.1);
    const on = Math.floor(f / 4) % 2 ? 0.7 : 0.05;
    for (const i of [0, 1, 4, 5]) c.L[i] = on;
    for (const i of [10, 11, 14, 15]) c.L[i] = 0.1 + 0.05 * Math.sin(f / 40);
    return c;
  }, 60 * 6, 60, (f, l, g) => {
    // the far quadrant's own corners (x, y >= 3: they touch only cells 10, 11, 14, 15, which only drift) move little: a
    // cut is taken where the light rose and a lift given where it fell; only when the strobe's own corners are pinned by
    // the windows around them does the whole frame's balance reach this far (measured over 6 s: gain >= 0.85, lift <= 0.16)
    for (const k of [18, 19, 23, 24]) { assert.ok(g.cornerA[k] >= 0.8, `corner ${k} frame ${f}: ${g.cornerA[k]}`); assert.ok(g.cornerL[k * 3] <= 0.2, `lift at corner ${k}: ${g.cornerL[k * 3]}`); }
  });
  // the far block (window 9) as drawn and as shown: the smooth field reaches into it only through the screen's centre
  // corner, which it shares with the strobe (v1's cells left it exactly alone, with a hard edge at the centre instead)
  const drawn9 = (f) => 0.1 + 0.05 * Math.sin(f / 40);
  for (let f = 0; f < shown[9].length; f++) keep = Math.min(keep, shown[9][f] / drawn9(f));
  for (let w = 0; w < WINDOWS.length; w++) assert.ok(maxFlashesPerSecond(shown[w]) <= 3, `window ${w}: ${maxFlashesPerSecond(shown[w])}`);
  assert.ok(keep >= 0.9, `the far block keeps ${keep} of its light`);
  assert.ok(maxFlashesPerSecond(shown[9]) <= 0.5, "the far block never flashes (its own drift swings 0.0999)");
  assert.ok(lim.stats().interventions > 0);
});

test("saturated red flashing is held too (the x320 scale, swing 20)", () => {
  const { shownR } = drive((f) => uniform(0.05, Math.floor(f / 3) % 2 ? 60 : 0), 60 * 4);
  for (let w = 0; w < WINDOWS.length; w++) assert.ok(maxFlashesPerSecond(shownR[w], 60, 2, 20) <= 3, `red window ${w}`);
});

test("the forced rest: five seconds of flashing at the limit rests every window for two, without a full hold", () => {
  // two quadrants flashing in alternation, each just under two flashes a second: some window always holds four
  // full-size transitions of its last second (one quadrant's own flashing never does, under PARTIAL)
  const { lim, shown } = drive((f) => {
    const c = uniform(0.05);
    for (const i of [0, 1, 4, 5]) c.L[i] = Math.floor(f / 16) % 2 ? 0.6 : 0.05;
    for (const i of [10, 11, 14, 15]) c.L[i] = Math.floor((f + 8) / 16) % 2 ? 0.6 : 0.05;
    return c;
  }, 60 * 9);
  const st = lim.stats();
  assert.ok(st.rest_frames >= 60, `rested ${st.rest_frames} frames`);
  assert.equal(LIMIT.RUN_S, 5); assert.equal(LIMIT.REST_S, 2);
  for (let w = 0; w < WINDOWS.length; w++) assert.ok(maxFlashesPerSecond(shown[w]) <= 3, `window ${w}`);
  assert.equal(st.full_hold_frames, 0, "the rest is met by the fields, never the last frame again");
});

test("cells from RGBA8 pixels: sRGB-decoded relative luminance, the red quantity only on saturated red; corner moments add up to the mean", () => {
  const w = 8, h = 8, px = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) { px[i * 4] = 255; px[i * 4 + 1] = 255; px[i * 4 + 2] = 255; px[i * 4 + 3] = 255; }
  let c = cellsFromRGBA8(px, w, h, { bx: [0, 2, 4, 6, 8], by: [0, 2, 4, 6, 8] });
  for (let i = 0; i < 16; i++) {
    assert.ok(Math.abs(c.L[i] - 1) < 1e-6); assert.equal(c.R[i], 0);
    for (let j = 0; j < 4; j++) assert.ok(Math.abs(c.LM[i * 4 + j] - 0.25) < 1e-9, "a uniform cell: a quarter on each corner");
  }
  for (let i = 0; i < w * h; i++) { px[i * 4] = 255; px[i * 4 + 1] = 0; px[i * 4 + 2] = 0; }
  c = cellsFromRGBA8(px, w, h, { bx: [0, 2, 4, 6, 8], by: [0, 2, 4, 6, 8] });
  assert.ok(Math.abs(c.R[0] - 320) < 1e-6);
  assert.ok(Math.abs(c.L[0] - 0.2126) < 1e-4);
});

// ------------------------------------------------------------------------------------- end to end, on pixels --
// A 96 x 54 frame: a dark room with a moving bar, and a white strobe over the top-left quarter at 10 Hz (the kick's
// held strobe at its worst). Metered, limited, applied to pixels, then judged with a meter written here (the verifier's
// exact quarters, not the limiter's cells).
const FW = 96, FH = 54;
function frameAt(f) {
  const px = new Uint8Array(FW * FH * 4);
  const lit = Math.floor(f / 3) % 2 === 1;
  const bar = (f * 2) % FW;
  for (let y = 0; y < FH; y++) for (let x = 0; x < FW; x++) {
    const i = (y * FW + x) * 4;
    let r = 18, g = 14, b = 40;
    if (Math.abs(x - bar) < 4) { r = 60; g = 200; b = 230; }
    if (lit && x < FW / 2 + 6 && y >= FH / 2 - 6) { r = 250; g = 245; b = 255; }
    px[i] = r; px[i + 1] = g; px[i + 2] = b; px[i + 3] = 255;
  }
  return px;
}
const LIN = new Float64Array(256).map((_, i) => { const s = i / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
function quarters(px, w, h) {
  const bx = [0, 1, 2, 3, 4].map((c) => Math.floor(c * w / 4)), by = [0, 1, 2, 3, 4].map((c) => Math.floor(c * h / 4));
  const L = new Float64Array(16), N = new Float64Array(16);
  for (let y = 0; y < h; y++) {
    const cy = y >= by[3] ? 3 : y >= by[2] ? 2 : y >= by[1] ? 1 : 0;
    for (let x = 0; x < w; x++) {
      const cx = x >= bx[3] ? 3 : x >= bx[2] ? 2 : x >= bx[1] ? 1 : 0, i = (y * w + x) * 4;
      L[cy * 4 + cx] += LUM(LIN[px[i]], LIN[px[i + 1]], LIN[px[i + 2]]); N[cy * 4 + cx]++;
    }
  }
  return { L, N };
}
function windowOf(q, [x0, y0, x1, y1]) { let l = 0, n = 0; for (let cy = y0; cy <= y1; cy++) for (let cx = x0; cx <= x1; cx++) { l += q.L[cy * 4 + cx]; n += q.N[cy * 4 + cx]; } return l / n; }

// (the meter's cells are the verifier's quarters here: at 96 x 54 the GPU's 16-pixel blocks would make cells of 32, 16, 32
// and 16 pixels; at the receipts' sizes they sit within a few blocks of the quarters, as in v1)
const QB = { bx: [0, 1, 2, 3, 4].map((c) => Math.floor(c * FW / 4)), by: [0, 1, 2, 3, 4].map((c) => Math.floor(c * FH / 4)) };
test("end to end on pixels: a 10 Hz white strobe over a quarter is held to 3 flashes a second, the model matches the pixels, and there is no edge", () => {
  const lim = new FrameLimiter();
  const series = WINDOWS.map(() => []);
  let prev = null, worstModel = 0, worstSeam = 0, held90 = 0, hardEdged = 0;
  for (let f = 0; f < 360; f++) {
    const px = frameAt(f);
    const cells = cellsFromRGBA8(px, FW, FH, QB);
    const g = lim.step(cells, f / 60, 1 / 60);
    const out = applyRGBA8(px, prev, FW, FH, g, QB);
    // the limiter's model of the shown frame equals the shown pixels, metered the same way (8-bit rounding apart)
    const back = cellsFromRGBA8(out, FW, FH, QB);
    for (let w = 0; w < WINDOWS.length; w++) worstModel = Math.max(worstModel, Math.abs(windowMean(back.L, w) - lim.prevWin[0][w]));
    const q = quarters(out, FW, FH);
    WINDOWS.forEach((r, w) => series[w].push(windowOf(q, r)));
    const hm = lim.holdMetrics();
    worstSeam = Math.max(worstSeam, hm.sm); if (hm.hd >= 0.9) held90++; hardEdged += hm.he;
    prev = out;
  }
  for (let w = 0; w < WINDOWS.length; w++) assert.ok(maxFlashesPerSecond(series[w]) <= 3, `window ${w}: ${maxFlashesPerSecond(series[w])}`);
  assert.ok(lim.stats().interventions > 0, "it had to act");
  assert.ok(worstModel < 3e-3, `model vs pixels ${worstModel}`);
  assert.ok(worstSeam < 1e-3, `a step across a cell border: ${worstSeam}`);
  assert.equal(hardEdged, 0, "no hard-edged hold");
  // the one fallback, a blend of the whole frame toward the last one (no edge), on at most 1 % of this storm's frames
  // (measured 2 of 360 at 0.9 or more: a 93 %-white strobe at 10 Hz over a quarter, the hardest case here)
  assert.ok(held90 <= 4, `frames showing 90 % or more of the last frame: ${held90}`);
});

test("protection off: the apply pass is the identity -- the shown frame is the drawn frame, bit for bit, on every frame of a storm", () => {
  const on = new FrameLimiter(), off = new FrameLimiter();
  let prevOn = null, prevOff = null, differOn = 0;
  for (let f = 0; f < 240; f++) {
    const px = frameAt(f);
    const cells = cellsFromRGBA8(px, FW, FH);
    const gOff = presentGains(off, false, cells, f / 60, 1 / 60);
    const outOff = applyRGBA8(px, prevOff, FW, FH, gOff);
    assert.equal(gOff, null, "no gains: the limiter is not asked");
    assert.ok(Buffer.from(outOff).equals(Buffer.from(px)), `frame ${f} changed with protection off`);
    const gOn = presentGains(on, true, cells, f / 60, 1 / 60);
    const outOn = applyRGBA8(px, prevOn, FW, FH, gOn);
    if (!Buffer.from(outOn).equals(Buffer.from(px))) differOn++;
    prevOn = outOn; prevOff = outOff;
  }
  assert.equal(off.stats().frames, 0, "the limiter never ran");
  assert.ok(differOn > 0, "the control: with protection on, the same storm is limited");
});
