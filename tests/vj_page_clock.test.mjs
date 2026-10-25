// Node tests for the page grid (Lasers v2 slice S2, spec 3.2 and receipt A2): vj-core.js BeatClock's continuous beat
// position (posAt), its slew and re-anchor, the engine's grid version and bar, and the laser engine's gates driven
// through it (vj-hookup.js laserClock) on a 60 fps virtual clock. Zero dependencies, no GPU:
//   node --test tests/vj_page_clock.test.mjs
// Every number here is synthetic: nothing reads Daniel's playing.
import { test } from "node:test";
import assert from "node:assert/strict";
import { BeatClock, parseEvent, GRID_SLEW_MAX, GRID_STRETCH_MAX } from "../arsenal/web/vj-core.js";
import * as L from "../arsenal/web/vj-lasers.js";
import { laserClock } from "../arsenal/web/vj-hookup.js";

const F = 1000 / 60;
const mulberry = (s) => L.mulberry32(s);

// The engine's beats as the page receives them: beat k at times(k), each announced `ahead` ms before it, with optional
// jitter on the prediction, a grid version and a bar. Steps the BeatClock at 60 fps from `from` to `to`; onFrame(t, bc).
function feed(bc, { times, ahead = 250, jitter = 0, seed = 3, ver = () => 1, bar = () => 0, from = 0, to = 10000, onFrame = null, gap = null, bpm = null }) {
  const rnd = mulberry(seed);
  let k = 0, prev = null;
  while (times(k) < from) k++;
  for (let j = 0; ; j++) {
    const t = from + j * F;
    if (t > to) break;
    while (times(k) <= t + ahead) {
      const due = times(k) + (jitter ? (rnd() * 2 - 1) * jitter : 0);
      const silent = gap && times(k) >= gap[0] && times(k) < gap[1];
      if (!silent && due >= t - 30) {
        const ev = parseEvent({ t: "beat", due_ms: due - t, bpm: bpm || 60000 / (times(k + 1) - times(k)), conf: 0.9, n: k, on_beat: 0.8,
                                src: "track", bar: bar(k), ver: ver(k), wall_ms: 0 });
        bc.schedule(t, ev);
      }
      k++;
    }
    bc.update(t, prev === null ? F / 1000 : (t - prev) / 1000);
    prev = t;
    if (onFrame) onFrame(t, bc);
  }
}

test("S2: posAt is a continuous beat position that meets each beat (steady 150 BPM, no error, no re-anchor)", () => {
  const per = 400, bc = new BeatClock();
  assert.equal(bc.posAt(0), null, "no position before the first beat");
  let last = -Infinity, worst = 0;
  feed(bc, { times: (k) => 1000 + k * per, to: 12000, onFrame: (t) => {
    const p = bc.posAt(t);
    if (p === null) return;
    assert.ok(p >= last - 1e-9, `never backward (${p} after ${last})`);
    last = p;
  } });
  // at each beat's own time the position is a whole number, one per beat
  for (let k = 3; k < 25; k++) {
    const p = bc.posAt(1000 + k * per);
    worst = Math.max(worst, Math.abs(p - Math.round(p)));
  }
  assert.ok(worst < 1e-6, `whole beats on the beats: worst ${worst}`);
  assert.equal(bc.reanchors, 0);
});

test("S2: a beat a little off the grid slews (no jump, at most 10 % stretch); more than a quarter beat re-anchors", () => {
  const per = 400, bc = new BeatClock();
  const times = (k) => 1000 + k * per + (k >= 10 ? 60 : 0);        // from beat 10 on, every beat 60 ms (0.15 beat) late
  let last = -Infinity, maxStep = 0, prevT = null;
  feed(bc, { times, bpm: 150, to: 9000, onFrame: (t) => {
    const p = bc.posAt(t);
    if (p === null) return;
    if (prevT !== null) maxStep = Math.max(maxStep, (p - last) / ((t - prevT) / per));
    assert.ok(p >= last - 1e-9, "never backward while slewing");
    last = p; prevT = t;
  } });
  assert.equal(bc.reanchors, 0, "0.15 beat slews");
  assert.ok(bc.slews >= 2, `slews ${bc.slews}`);
  assert.ok(maxStep <= 1 + GRID_STRETCH_MAX + 1e-6, `rate at most 1.1 beats a period: ${maxStep.toFixed(4)}`);
  // after a few beats the grid sits on the late beats again
  const p = bc.posAt(times(18));
  assert.ok(Math.abs(p - Math.round(p)) < 0.02, `back on the beats: ${p.toFixed(4)}`);
  // a 0.4-beat jump with no new version: a hard re-anchor at that beat
  const bc2 = new BeatClock();
  feed(bc2, { times: (k) => 1000 + k * per + (k >= 10 ? 160 : 0), bpm: 150, to: 7000 });
  assert.ok(bc2.reanchors >= 1, `re-anchored: ${bc2.reanchors}`);
  assert.ok(GRID_SLEW_MAX === 0.25);
});

test("S2: a new grid version flushes the old version's queued beats and re-anchors on its first beat", () => {
  const per = 400, bc = new BeatClock();
  // ver 1 until beat 12; the engine then re-anchors half a beat later (ver 2)
  const times = (k) => 1000 + k * per + (k >= 12 ? per / 2 : 0);
  // announce ver-1 beats far ahead so some are still queued when ver 2 arrives
  feed(bc, { times, ahead: 700, ver: (k) => (k >= 12 ? 2 : 1), to: 9000 });
  assert.ok(bc.flushed >= 1, `old-version beats flushed: ${bc.flushed}`);
  assert.ok(bc.reanchors >= 1, `re-anchored: ${bc.reanchors}`);
  assert.equal(bc.ver, 2);
  const p = bc.posAt(times(18));
  assert.ok(Math.abs(p - Math.round(p)) < 1e-6, `on the new grid: ${p}`);
});

test("S2: the engine's bar puts the ONE on a multiple of 4, and barAt counts 1-4 from it", () => {
  const per = 400, bc = new BeatClock();
  // the engine's bars start at beat 6 (its first tap was the ONE): bar(k) = ((k - 6) mod 4) + 1 from there, 0 before
  const bar = (k) => (k >= 6 ? (((k - 6) % 4) + 4) % 4 + 1 : 0);
  feed(bc, { times: (k) => 1000 + k * per, bar, to: 8000 });
  for (let k = 8; k < 16; k++) {
    const t = 1000 + k * per + 5;
    assert.equal(bc.barAt(t), bar(k), `beat ${k}`);
    if (bar(k) === 1) assert.equal(Math.round(bc.posAt(1000 + k * per)) % 4, 0, `the ONE at beat ${k} is a multiple of 4`);
  }
});

// A2 through the page grid: the laser engine on vj-core's BeatClock (laserClock: posAt) at 60 fps, its pulses (lit in the
// frame whose picture -- one frame later -- lands on or just before the beat) against the TRUE grid the beats came from.
function gatesThroughThePage({ bpm, jitter = 0, ramp = null, seed = 5, gate = "triple", presses = 10, clockOf = laserClock, verJump = null }) {
  const per = 60000 / bpm;
  // true beat times: steady, a ramp from bpm to ramp.to over ramp.beats beats, or a half-beat jump (a new ver) at verJump
  const T = [];
  let t = 1000, p = per;
  for (let k = 0; k < 400; k++) {
    T.push(t + (verJump !== null && k >= verJump ? per / 2 : 0));
    if (ramp && k >= ramp.at && k < ramp.at + ramp.beats) p = 60000 / (bpm + (ramp.to - bpm) * (k - ramp.at + 1) / ramp.beats);
    t += p;
  }
  const bc = new BeatClock();
  const eng = L.createLaserEngine({ seed, clock: clockOf(bc), gateMode: gate, patternMode: "fan", bankMode: "A" });
  const pressAt = [];
  for (let i = 0; i < presses; i++) pressAt.push(T[16 + i * 6] - 20 - (i % 3) * 13);   // a little early, as a hand is
  const ons = [];
  let pi = 0;
  feed(bc, { times: (k) => T[k], jitter, seed, ver: (k) => (verJump !== null && k >= verJump ? 2 : 1),
    from: T[0], to: T[16 + presses * 6 + 4], onFrame: (tf) => {
      while (pi < pressAt.length && pressAt[pi] <= tf) { eng.hit(pressAt[pi], 0.9); eng.release(pressAt[pi] + 40); pi++; }
      const out = eng.frame(tf);
      for (const e of out.events) if (e.type === "pulse") ons.push(tf + F);
    } });
  // each pulse against the nearest quarter-beat of the true grid (the gate's 1/4 grid; beats interpolated)
  const errs = ons.map((x) => {
    let k = 0; while (k + 1 < T.length && T[k + 1] <= x) k++;
    const span = T[k + 1] - T[k], frac = (x - T[k]) / span, q = Math.round(frac * 4) / 4;
    return x - (T[k] + q * span);
  });
  return { ons, errs, per, gate: L.GATES[gate], presses };
}

test("A2 (page): steady 150 and 180 BPM through the page grid -- every pulse on the grid, never late, at most a frame early", () => {
  for (const bpm of [150, 180]) for (const gate of ["single", "onetwo", "triple"]) {
    const r = gatesThroughThePage({ bpm, gate });
    assert.equal(r.ons.length, r.presses * r.gate.pulses.length, `${gate} ${bpm}: every pulse fired once`);
    for (const e of r.errs) assert.ok(e <= 0.5 && e >= -F - 0.5, `${gate} at ${bpm}: ${e.toFixed(2)} ms from the grid`);
  }
});

test("A2 (page): +-8 ms of jitter on the predictions stays within 17 ms of the true grid; a 150 -> 156 ramp within 12 ms", () => {
  let worstJ = 0, worstR = 0;
  for (const seed of [1, 2, 3, 4]) {
    const r = gatesThroughThePage({ bpm: 150, jitter: 8, seed });
    assert.equal(r.ons.length, r.presses * 3, "no missing or doubled pulse with jitter");
    for (const e of r.errs) { worstJ = Math.max(worstJ, Math.abs(e + F / 2) - F / 2); assert.ok(e <= 17 && e >= -F - 17, `jitter: ${e.toFixed(2)} ms`); }
  }
  const ramp = gatesThroughThePage({ bpm: 150, ramp: { at: 12, beats: 16, to: 156 }, gate: "triple", presses: 12 });
  assert.equal(ramp.ons.length, 36, "no missing or doubled pulse on the ramp");
  for (const e of ramp.errs) { worstR = Math.max(worstR, Math.abs(e + F / 2) - F / 2); assert.ok(e <= 12 && e >= -F - 12, `ramp: ${e.toFixed(2)} ms`); }
  console.log(`  A2 page grid: jitter worst ${worstJ.toFixed(2)} ms past the early window, ramp ${worstR.toFixed(2)} ms`);
});

test("A2 (page): after the engine's half-beat re-anchor (a new ver) no pulse fires twice and the next lands on the new grid", () => {
  const r = gatesThroughThePage({ bpm: 150, gate: "triple", presses: 8, verJump: 30 });
  assert.equal(r.ons.length, 24, `no doubled or missing pulse: ${r.ons.length}`);
  const after = r.errs.filter((_, i) => r.ons[i] > 1000 + 31 * 400);
  assert.ok(after.length >= 6);
  for (const e of after) assert.ok(e <= 0.5 && e >= -F - 0.5, `on the new grid: ${e.toFixed(2)} ms`);
});

test("A2 (page): the page grid is at least as tight as the phase-unwrapped clock it replaces", () => {
  const phaseOnly = (bc) => L.clockFromBeatClock(bc);       // the engine's own adapter: no posAt
  for (const seed of [7, 8]) {
    const a = gatesThroughThePage({ bpm: 150, jitter: 8, seed });
    const b = gatesThroughThePage({ bpm: 150, jitter: 8, seed, clockOf: phaseOnly });
    const rms = (xs) => Math.sqrt(xs.reduce((s, x) => s + (x + F / 2) ** 2, 0) / xs.length);
    assert.ok(rms(a.errs) <= rms(b.errs) + 0.5, `page grid rms ${rms(a.errs).toFixed(2)} vs phase ${rms(b.errs).toFixed(2)} ms`);
  }
});
