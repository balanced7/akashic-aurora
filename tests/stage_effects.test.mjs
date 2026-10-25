// Virtual Stage v0: the effects engine and the beat grid (arsenal/web/stage/effects.js, grid.js).
// node --test tests/stage_effects.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { spreadValues, fromMA, fromChamSys, fromHog, waveform, governEffect, Phasor, EffectInstance, UNISON_FLOOR }
  from "../arsenal/web/stage/effects.js";
import { BeatGrid, DemoBeats, beatExtras } from "../arsenal/web/stage/grid.js";

const close = (a, b, eps, msg = "") => assert.ok(Math.abs(a - b) <= eps, `${msg} ${a} != ${b} (eps ${eps})`);
const keysOf = (n) => ({ index: Float64Array.from({ length: n }, (_, i) => i), x: Float64Array.from({ length: n }, (_, i) => -n / 2 + i) });

// ------------------------------------------------------------------------------------------------ spreads --
test("spread basics: cyclic and one-shot normalisation", () => {
  const k = keysOf(4);
  assert.deepEqual(Array.from(spreadValues(k, { from: 0, to: 360, cyclic: true }, 4)), [0, 90, 180, 270]);
  assert.deepEqual(Array.from(spreadValues(k, { from: 0, to: 360, cyclic: false }, 4)), [0, 120, 240, 360]);
  assert.deepEqual(Array.from(spreadValues(k, { from: 0, to: 90, reverse: true }, 4)), [90, 60, 30, 0]);
  assert.deepEqual(Array.from(spreadValues(k, { from: 0, to: 300, cyclic: false, shift: 1 }, 4)), [100, 200, 300, 0]);
});

test("block, repeat, wings and mirror", () => {
  const k = keysOf(8);
  // block 2: neighbours share a value
  const pairs = Array.from(spreadValues(k, { from: 0, to: 3, block: 2 }, 8));
  assert.deepEqual(pairs, Array.from({ length: 8 }, (_, i) => i >> 1));
  // repeat 2: the pattern restarts every 2
  const alternating = Array.from(spreadValues(k, { from: 0, to: 1, repeat: 2 }, 8));
  assert.deepEqual(alternating, Array.from({ length: 8 }, (_, i) => i % 2));
  // wings 2 mirrored: symmetric about the centre
  const w = Array.from(spreadValues(k, { from: 0, to: 3, wings: 2, mirror: true }, 8));
  assert.deepEqual(w, [0, 1, 2, 3, 3, 2, 1, 0]);
  // two wings 180 degrees apart (the helix's two backbones)
  const h = Array.from(spreadValues(k, { from: 0, to: 360, cyclic: true, wings: 2, wingOffset: 0.5 }, 8));
  assert.deepEqual(h, [0, 90, 180, 270, 180, 270, 360, 450]);
});

test("one Spread object covers MA MAtricks, ChamSys spread and Hog fan: identical offsets", () => {
  const k = keysOf(12);
  const base = { from: 0, to: 360, cyclic: true, wings: 2, mirror: true };
  const ma = spreadValues(k, fromMA({ ...base, block: 2, group: 3 }), 12);
  const cs = spreadValues(k, fromChamSys({ ...base, segments: 2, parts: 3 }), 12);
  const hog = spreadValues(k, fromHog({ ...base, buddying: 2, segments: 3 }), 12);
  assert.deepEqual(Array.from(ma), Array.from(cs));
  assert.deepEqual(Array.from(ma), Array.from(hog));
  // the shuffle is seeded: the same seed, the same permutation
  const s1 = spreadValues(k, { from: 0, to: 11, shuffle: 1 }, 12, 7), s2 = spreadValues(k, { from: 0, to: 11, shuffle: 1 }, 12, 7);
  assert.deepEqual(Array.from(s1), Array.from(s2));
  assert.deepEqual(Array.from(s1).sort((a, b) => a - b), Array.from({ length: 12 }, (_, i) => i));
});

// ------------------------------------------------------------------------------------------------ forms --
test("waveforms: the pulsing forms peak on the line", () => {
  close(waveform("sine", 0), 1, 1e-12); close(waveform("sine", 0.5), 0, 1e-12);
  close(waveform("pulse", 0, { width: 0.5 }), 1, 1e-12); assert.equal(waveform("pulse", 0.6, { width: 0.5 }), 0);
  close(waveform("triangle", 0.25), 0.5, 1e-12);
  assert.equal(waveform("square", 0.2, { width: 0.5 }), 1); assert.equal(waveform("square", 0.7, { width: 0.5 }), 0);
  close(waveform("step", 0.99, { steps: 4 }), 1, 1e-12);
  assert.equal(waveform("random", 3.2, { seed: 9 }), waveform("random", 3.9, { seed: 9 }), "one value per cycle");
});

// --------------------------------------------------------------------------------------------- the floor rule --
test("a unison dimmer pulse is a lift, not a flash: floor >= 0.6; a chase spread over 90 degrees keeps its depth", () => {
  const unison = governEffect({ attrs: ["Dimmer"], form: "pulse", size: 1, measure: 1, phase: { from: 0, to: 0 } });
  assert.ok(unison.governed && unison.floor >= UNISON_FLOOR - 1e-12);
  const g = { n: 12, keys: keysOf(12) };
  const inst = new EffectInstance("u", { attrs: ["Dimmer"], form: "pulse", size: 1, measure: 1, phase: { from: 0, to: 10 } }, g);
  let lo = 1;
  for (let i = 0; i <= 100; i++) { inst.phasor.phi = i / 100; lo = Math.min(lo, inst.apply("Dimmer", 1, 0)); }
  assert.ok(lo >= UNISON_FLOOR - 1e-9, `the trough ${lo}`);
  const chase = governEffect({ attrs: ["Dimmer"], form: "pulse", size: 1, measure: 2, phase: { from: 0, to: 360, cyclic: true } });
  assert.ok(!chase.governed && !(chase.floor > 0));
  const abs = governEffect({ attrs: ["Dimmer"], form: "sine", mode: "absolute", size: 0.5, measure: 1 });
  assert.ok(abs.floor >= UNISON_FLOOR);
  const tilt = governEffect({ attrs: ["Tilt"], form: "sine", size: 30, measure: 1 });
  assert.ok(!tilt.governed);
});

// ------------------------------------------------------------------------------------------- the beat grid --
function runDemo({ bpm = 150, ramp = null, taps = [], seconds = 20, lead = 220 } = {}) {
  const demo = new DemoBeats({ bpm, startMs: 1000, ramp, taps, leadMs: lead });
  const grid = new BeatGrid({ bpm, t0: 0 });
  const frames = [];
  for (let t = 0; t <= seconds * 1000; t += 1000 / 60) {
    demo.tick(t, (o) => grid.beat({ ...o, ...beatExtras(o) }, t));
    frames.push({ t, pos: grid.posAt(t), locked: grid.locked });
  }
  return { demo, grid, frames };
}

test("the grid locks to the engine's beats and puts each beat on a whole number", () => {
  const { demo, grid } = runDemo({ seconds: 10 });
  assert.ok(grid.locked);
  let worst = 0;
  for (let i = 4; i < 20; i++) { const p = grid.posAt(demo.timeOf(i)); worst = Math.max(worst, Math.abs(p - Math.round(p))); }
  assert.ok(worst < 0.01, `worst beat error ${worst}`);
  // the bar field anchors the ONE: beat n % 4 === 0 is bar beat 1
  const b = grid.barAt(demo.timeOf(16) + 1);
  assert.equal(b.beat, 1);
});

test("pos never runs backward, through a 150 -> 160 BPM ramp and a tap that moves the beat", () => {
  const { frames, grid, demo } = runDemo({ ramp: { fromBeat: 16, toBeat: 32, toBpm: 160 }, taps: [{ beat: 40, shiftMs: 90 }], seconds: 24 });
  for (let i = 1; i < frames.length; i++) assert.ok(frames[i].pos >= frames[i - 1].pos - 1e-9, `pos ran backward at ${frames[i].t}`);
  assert.ok(grid.stats.vers >= 1, "the tap's ver bump was seen");
  // after the ramp and the tap, the beats sit on whole numbers again
  let worst = 0;
  for (let i = 46; i < 54; i++) { const p = grid.posAt(demo.timeOf(i)); worst = Math.max(worst, Math.abs(p - Math.round(p))); }
  assert.ok(worst < 0.02, `worst beat error after the tap ${worst}`);
  close(grid.bpm, 160, 1e-9);
});

test("a slew never stretches a beat by more than 10 %", () => {
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  grid.beat({ due_ms: 200, bpm: 150, n: 0, conf: 1 }, 0);
  // a prediction 0.2 beat late (inside the slew band)
  const r = grid.beat({ due_ms: 200 + 400 + 80, bpm: 150, n: 1, conf: 1 }, 0);
  assert.ok(Math.abs(r.err) <= 0.25);
  assert.ok(grid.rate <= 1.1 / 400 + 1e-12 && grid.rate >= 0.9 / 400 - 1e-12);
});

// -------------------------------------------------------------------------------------- the phase, beat-locked --
test("the effect phase is continuous through a 150 -> 160 BPM ramp (no jumps, never backward)", () => {
  const { frames } = runDemo({ ramp: { fromBeat: 8, toBeat: 24, toBpm: 160 }, seconds: 14 });
  const ph = new Phasor({ measure: 4, scale: 1 });
  let prev = null, maxStep = 0;
  for (const f of frames.filter((x) => x.locked)) {        // from the lock on (the first beat may jump pos forward once)
    const phi = ph.tick(f.pos, 0);
    if (prev !== null) {
      let d = phi - prev; if (d < -0.5) d += 1;
      assert.ok(d >= -1e-9, "the phase ran backward");
      maxStep = Math.max(maxStep, d);
    }
    prev = phi;
  }
  // at 160 BPM and 60 fps one frame is 0.0444 beat = 0.0111 of a 4-beat cycle (a slew adds at most 10 %)
  assert.ok(maxStep < 0.0111 * 1.15, `largest step ${maxStep}`);
});

test("a x2 speed change lands on the next beat line with the phase continuous; x4 waits for the bar line", () => {
  const ph = new Phasor({ measure: 4, scale: 1 });
  let pos = 0;
  ph.tick(pos, 0);
  for (; pos < 5.3; pos += 0.05) ph.tick(pos, 0);
  ph.setScale(2, pos);                      // asked at beat ~5.3
  assert.equal(ph.pending.at, 6);
  let before = ph.phi, crossed = false;
  for (; pos < 7.5; pos += 0.05) {
    const p0 = ph.phi;
    ph.tick(pos, 0);
    let d = ph.phi - p0; if (d < -0.5) d += 1;
    assert.ok(d >= 0 && d < 0.05 * 2 / 4 + 1e-9, `step ${d} at ${pos}`);
    if (!crossed && ph.scale === 2) { crossed = true; assert.ok(pos >= 6 - 1e-9 && pos < 6.05 + 1e-9, `the change landed at ${pos}`); }
  }
  assert.ok(crossed);
  ph.setScale(8, pos, 0);                   // x4: the next bar line (bars start on multiples of 4 here)
  assert.equal(ph.pending.at, 8);
  void before;
});

test("a tap (ver re-anchor) snaps the phase back onto the grid", () => {
  const ph = new Phasor({ measure: 4, scale: 1, offset: 0 });
  ph.tick(10, 0);
  ph.phi = 0.37;                            // drifted (e.g. after many speed changes)
  ph.tick(10.5, 1);                         // ver 0 -> 1
  close(ph.phi, (10.5 / 4) % 1, 1e-12);
});
