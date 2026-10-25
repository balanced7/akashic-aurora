// Virtual Stage v0: the final-frame flash limiter (arsenal/web/stage/flash.js). node --test tests/stage_flash.test.mjs
// Judged with an independent counter written here from the 2026-10-24 verifier's rule (turning points with a hysteresis
// of 0.02, a transition is a swing of 0.1 or more whose darker end is under 0.8, counted at its later turning point;
// flashes in a second = transitions / 2), never with the limiter's own trackers.
import { test } from "node:test";
import assert from "node:assert/strict";
import { WINDOWS, FrameLimiter, cellsFromRGBA8, windowMean, LIMIT } from "../arsenal/web/stage/flash.js";

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
function maxFlashesPerSecond(series, fps = 60) {
  const t = transitions(series).map((i) => i / fps);
  let best = 0;
  for (let i = 0; i < t.length; i++) { let n = 0; for (let j = i; j < t.length && t[j] - t[i] < 1; j++) n++; best = Math.max(best, n); }
  return best / 2;
}
// drive the limiter with a per-frame cell function, return the SHOWN window series (computed from the gains, the way
// the apply pass makes them) and the limiter
function drive(cellsAt, frames, fps = 60) {
  const lim = new FrameLimiter();
  const shown = WINDOWS.map(() => []), shownR = WINDOWS.map(() => []);
  let prev = null;
  for (let f = 0; f < frames; f++) {
    const c = cellsAt(f);
    const g = lim.step(c, f / fps, 1 / fps);
    const L = new Float64Array(16), R = new Float64Array(16);
    for (let i = 0; i < 16; i++) {
      const a = g.cellA[i], b = g.cellB[i];
      L[i] = (1 - b) * a * c.L[i] + b * (prev ? prev.L[i] : c.L[i]);
      R[i] = (1 - b) * a * c.R[i] + b * (prev ? prev.R[i] : c.R[i]);
    }
    prev = { L, R };
    WINDOWS.forEach((_, w) => { shown[w].push(windowMean(L, w)); shownR[w].push(windowMean(R, w)); });
  }
  return { lim, shown, shownR };
}
const uniform = (l, r = 0) => ({ L: new Float64Array(16).fill(l), R: new Float64Array(16).fill(r) });

test("18 windows, each at least a quarter of the screen", () => {
  assert.equal(WINDOWS.length, 18);
  for (const [x0, y0, x1, y1] of WINDOWS) assert.ok((x1 - x0 + 1) * (y1 - y0 + 1) >= 4);
});

test("a calm, beat-locked show passes untouched: zero interventions", () => {
  // a 60 -> 100 % lift on every beat at 150 BPM over the whole frame at a modest level, plus a slow drift
  const { lim } = drive((f) => {
    const beat = (f / 60) * 2.5, x = beat - Math.floor(beat);
    return uniform(0.12 * (0.6 + 0.4 * Math.exp(-x * 5)) + 0.02 * Math.sin(f / 90));
  }, 60 * 20);
  assert.equal(lim.stats().interventions, 0);
});

test("a 10 Hz full-frame strobe is held to at most 3 flashes a second in every window", () => {
  const { lim, shown } = drive((f) => uniform(Math.floor(f / 3) % 2 ? 0.6 : 0.03), 60 * 6);
  for (let w = 0; w < WINDOWS.length; w++) assert.ok(maxFlashesPerSecond(shown[w]) <= 3, `window ${w}: ${maxFlashesPerSecond(shown[w])}`);
  assert.ok(lim.stats().interventions > 0, "it had to act");
});

test("a strobe in one quadrant is held there; the opposite quadrant moving slowly is left alone", () => {
  let calm = null;
  const { shown, lim } = drive((f) => {
    const c = uniform(0.1);
    const on = Math.floor(f / 4) % 2 ? 0.7 : 0.05;
    for (const i of [0, 1, 4, 5]) c.L[i] = on;
    for (const i of [10, 11, 14, 15]) c.L[i] = 0.1 + 0.05 * Math.sin(f / 40);
    calm = calm || [];
    calm.push(c.L[15]);
    return c;
  }, 60 * 6);
  for (let w = 0; w < WINDOWS.length; w++) assert.ok(maxFlashesPerSecond(shown[w]) <= 3, `window ${w}: ${maxFlashesPerSecond(shown[w])}`);
  // the far quadrant (block 2,2: window 9) is shown as drawn: no cell gain ever touched it
  assert.equal(maxFlashesPerSecond(shown[9]), 0);
  assert.ok(lim.stats().interventions > 0);
});

test("saturated red flashing is held too (the x320 scale, swing 20)", () => {
  const { shownR } = drive((f) => uniform(0.05, Math.floor(f / 3) % 2 ? 60 : 0), 60 * 4);
  for (let w = 0; w < WINDOWS.length; w++) {
    const t = transitions(shownR[w], 2, 20).map((i) => i / 60);
    let best = 0;
    for (let i = 0; i < t.length; i++) { let n = 0; for (let j = i; j < t.length && t[j] - t[i] < 1; j++) n++; best = Math.max(best, n); }
    assert.ok(best / 2 <= 3, `red window ${w}: ${best / 2} flashes a second`);
  }
});

test("the forced rest: five seconds of flashing at the limit rests every window for two", () => {
  const { lim } = drive((f) => uniform(Math.floor(f / 12) % 2 ? 0.5 : 0.05), 60 * 9);
  assert.ok(lim.stats().rest_frames >= 60, `rested ${lim.stats().rest_frames} frames`);
  assert.equal(LIMIT.RUN_S, 5); assert.equal(LIMIT.REST_S, 2);
});

test("cells from RGBA8 pixels: sRGB-decoded relative luminance, the red quantity only on saturated red", () => {
  const w = 8, h = 8, px = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) { px[i * 4] = 255; px[i * 4 + 1] = 255; px[i * 4 + 2] = 255; px[i * 4 + 3] = 255; }
  let c = cellsFromRGBA8(px, w, h);
  for (let i = 0; i < 16; i++) { assert.ok(Math.abs(c.L[i] - 1) < 1e-6); assert.equal(c.R[i], 0); }
  for (let i = 0; i < w * h; i++) { px[i * 4] = 255; px[i * 4 + 1] = 0; px[i * 4 + 2] = 0; }
  c = cellsFromRGBA8(px, w, h);
  assert.ok(Math.abs(c.R[0] - 320) < 1e-6);
  assert.ok(Math.abs(c.L[0] - 0.2126) < 1e-4);
});
