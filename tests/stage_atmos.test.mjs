// Virtual Stage, the medium contract (arsenal/web/stage/atmos.js, VJ V2 P0): two channels, two caps, and the white-out
// receipts against the guards that exist -- the final-frame limiter (flash.js) and the FlashGate (programmer.js).
// node --test tests/stage_atmos.test.mjs
//
// The check (vj-v2-research-2026-10-27/fog-fluid.check.md): lifting the plume cap is only as safe as receipts against
// flash.js and the FlashGate, because the predictive governor the research leaned on is unbuilt. So: a CO2 white-out is
// modelled on the limiter's own 4 x 4 cells (the plume's optical depth over its path, Beer-Lambert, in front of a dark
// stage), asked for every beat at 150 and 180 BPM and granted by the Stage's FlashGate, and the frames go through
// FrameLimiter. Receipt: the limiter never has to act, and the verifier's counter (vj_storm.mjs) sees at most three
// flashes in any second in any window. And the backstop: a white-out that bypassed the gate and cleared fast (a fan
// blowing it away) is held by the limiter to three flashes a second on the frames shown.
import { test } from "node:test";
import assert from "node:assert/strict";
import { HAZE_CAP, PLUME_CAP, SIGMA_CAP, clampSigma, clampPlume, plumeTransmittance, Atmosphere, airTint } from "../arsenal/web/stage/atmos.js";
import { readFileSync } from "node:fs";
import { hexToLinear } from "../arsenal/web/stage/lasers.js";
import { FrameLimiter, WINDOWS, windowMean } from "../arsenal/web/stage/flash.js";
import { FlashGate } from "../arsenal/web/stage/programmer.js";

// the verifier's counter (vj_storm.mjs transitions): hysteresis 0.02, a swing of 0.1 or more whose darker end is under 0.8
function transitions(L, hyst = 0.02, thr = 0.1, dark = 0.8) {
  const ext = []; let dir = 0, hi = { i: 0, v: L[0] }, lo = { i: 0, v: L[0] }, cand = null;
  for (let i = 1; i < L.length; i++) {
    const v = L[i];
    if (dir === 0) {
      if (v > hi.v) hi = { i, v };
      if (v < lo.v) lo = { i, v };
      if (hi.v - lo.v >= hyst) { if (hi.i > lo.i) { ext.push(lo); dir = 1; cand = hi; } else { ext.push(hi); dir = -1; cand = lo; } }
    } else if (dir === 1) { if (v > cand.v) cand = { i, v }; else if (cand.v - v >= hyst) { ext.push(cand); dir = -1; cand = { i, v }; } }
    else if (v < cand.v) cand = { i, v }; else if (v - cand.v >= hyst) { ext.push(cand); dir = 1; cand = { i, v }; }
  }
  if (cand) ext.push(cand);
  const out = [];
  for (let k = 1; k < ext.length; k++) { const a = ext[k - 1], b = ext[k]; if (Math.abs(b.v - a.v) >= thr && Math.min(a.v, b.v) < dark) out.push(b.i); }
  return out;
}
const maxIn1s = (at, fps) => { let best = 0; for (let i = 0, j = 0; i < at.length; i++) { while (at[i] - at[j] >= fps) j++; best = Math.max(best, i - j + 1); } return best; };

// A CO2 burst on the plume channel: the valve ramps (>= 100 ms, one flash), holds, closes; the condensate burns off.
const CO2 = { ramp: 0.12, hold: 1.0, tau: 1.5, path: 0.6, refusedScale: 0.25, refusedRamp: 0.6 };
function plumeSigma(bursts, t, tau = CO2.tau, hold = CO2.hold) {
  let s = 0;
  for (const b of bursts) {
    const age = t - b.t0;
    if (age < 0) continue;
    const open = age < b.ramp ? age / b.ramp : 1;
    s += b.peak * (age < b.ramp + hold ? open : Math.exp(-(age - b.ramp - hold) / tau));
  }
  return clampPlume(s);
}
// The frame on the limiter's cells: a dark stage (0.03 linear), the plume (lit white, 0.6) over the cells it covers.
function cellsAt(sigma, covered, bg = 0.03, lit = 0.6) {
  const T = plumeTransmittance(sigma, CO2.path);
  const L = new Float64Array(16).fill(bg), R = new Float64Array(16);
  for (const c of covered) L[c] = bg * T + lit * (1 - T);
  return { L, R };
}
const QUARTER = [5, 6, 9, 10], FULL = [...Array(16).keys()];
// play `seconds` at 60 fps: CO2 asked on every beat (the gate decides), through FrameLimiter; returns what was shown
function play({ bpm, covered, seconds = 20, gated = true, tau = CO2.tau, hold = CO2.hold }) {
  const fps = 60, gate = new FlashGate(), lim = new FrameLimiter(), bursts = [];
  const shown = WINDOWS.map(() => []);
  let lastBeat = -1;
  for (let f = 0; f < seconds * fps; f++) {
    const t = f / fps, beat = Math.floor(t * bpm / 60);
    if (beat !== lastBeat) {
      lastBeat = beat;
      const granted = !gated || gate.request(beat);
      bursts.push(granted ? { t0: t, peak: PLUME_CAP, ramp: CO2.ramp } : { t0: t, peak: PLUME_CAP * CO2.refusedScale, ramp: CO2.refusedRamp });
      if (bursts.length > 16) bursts.shift();
    }
    lim.step(cellsAt(plumeSigma(bursts, t, tau, hold), covered), t, 1 / fps);
    WINDOWS.forEach((_, w) => shown[w].push(windowMean(lim.prevCells[0], w)));
  }
  const worst = Math.max(...shown.map((s) => maxIn1s(transitions(s), fps)));
  return { interventions: lim.interventions, worstTransitionsIn1s: worst, grants: gate.grants.length };
}

test("two channels, two caps: haze and fog stay at 0.26 /m, a plume may reach 15 /m", () => {
  assert.equal(HAZE_CAP, 0.26); assert.equal(SIGMA_CAP, HAZE_CAP); assert.equal(PLUME_CAP, 15);
  assert.equal(clampSigma(9), HAZE_CAP); assert.equal(clampPlume(99), PLUME_CAP); assert.equal(clampPlume(-1), 0);
  // the check's numbers: at the haze cap a 0.6 m plume is at most 14 % opaque; at full burst its core passes <= 10 %
  assert.ok(Math.abs(1 - Math.exp(-HAZE_CAP * 0.6) - 0.144) < 0.001);
  assert.ok(plumeTransmittance(PLUME_CAP, 0.6) <= 0.1);
  // the medium: each channel under its own cap at the same point (a broken hazer cannot borrow the plume's headroom)
  const a = new Atmosphere({ hazers: [{ pos: [0, 2, 0] }], preHaze: 1 });
  a.hazers[0].output = 50;
  a.update(1 / 60);
  assert.ok(a.densityAt([0, 3.5, 0], 1) <= HAZE_CAP + 1e-12);
  assert.ok(Math.abs(a.densityAt([0, 3.5, 0], 1, 40) - (a.densityAt([0, 3.5, 0], 1) + PLUME_CAP)) < 1e-12);
});

test("white-out receipt: CO2 asked every beat, granted by the FlashGate, never makes the limiter act", () => {
  for (const bpm of [150, 180]) for (const covered of [QUARTER, FULL]) {
    const r = play({ bpm, covered });
    assert.ok(r.grants >= Math.floor(20 * bpm / 60 / 4) - 1, `${bpm}: grants ${r.grants}`);
    assert.equal(r.interventions, 0, `${bpm} BPM, ${covered.length} cells: the limiter acted`);
    assert.ok(r.worstTransitionsIn1s <= 6, `${bpm} BPM: ${r.worstTransitionsIn1s} transitions in a second`);
  }
});

test("white-out backstop: a plume that bypassed the gate and clears fast is held to three flashes a second", () => {
  // short puffs on every beat at 240 BPM (4 a second), blown away in 40 ms: the plume itself would flash at 4 Hz
  const raw = play({ bpm: 240, covered: QUARTER, gated: false, tau: 0.04, hold: 0.05 });
  assert.ok(raw.interventions > 0, "the limiter had to act (the case is real)");
  assert.ok(raw.worstTransitionsIn1s <= 6, `shown: ${raw.worstTransitionsIn1s} transitions in a second`);
});

test("the air's colour: a theme's air_tint moves the haze veil's hue toward its ambient and never its luminance", () => {
  const Y = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  // fix round 2: the Stage's Dreaming City air measured a neutral blue-grey (the rings' white LEDs light the veil), every
  // still of Daniel's measures plum (R about 18 over G)
  const scene = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
  const dc = scene.themes["dreaming-city"], amb = hexToLinear(dc.ambient);
  assert.ok(dc.air_tint > 0 && dc.air_tint <= 1);
  const veil = [0.0093, 0.0086, 0.0144];                       // the measured air, linear (sRGB 24, 23, 32)
  const out = airTint(veil, amb, dc.air_tint);
  assert.ok(Math.abs(Y(out) - Y(veil)) < 1e-12, "the luminance the flash limiter counts does not move");
  const srgb = (l) => 255 * (l <= 0.0031308 ? 12.92 * l : 1.055 * l ** (1 / 2.4) - 0.055);
  assert.ok(srgb(out[0]) - srgb(out[1]) >= 12 && srgb(out[2]) - srgb(out[1]) >= 12, `plum: ${out.map(srgb).map(Math.round)}`);
  // t = 0 (every other theme), a black veil and a black ambient leave it as it was; t clamps to 0..1
  assert.deepEqual(airTint(veil, amb, 0), veil);
  assert.deepEqual(airTint([0, 0, 0], amb, 1), [0, 0, 0]);
  assert.deepEqual(airTint(veil, [0, 0, 0], 1), veil);
  assert.deepEqual(airTint(veil, amb, 5), airTint(veil, amb, 1));
  const full = airTint(veil, amb, 1);
  for (let i = 1; i < 3; i++) assert.ok(Math.abs(full[i] / full[0] - amb[i] / amb[0]) < 1e-9, "t = 1: the ambient's own hue");
  // in place (the renderer reuses one buffer a frame)
  const v = veil.slice(); assert.equal(airTint(v, amb, 0.5, v), v);
  for (const [id, t] of Object.entries(scene.themes)) if (t.air_tint !== undefined) assert.ok(t.air_tint >= 0 && t.air_tint <= 1, id);
});

// THE HAZE FADER (2026-10-29, atmos.js header). Daniel: "It looks like the haze knob doesn't quite fully control the haze"
// (his HUD: haze "96 % -> 100 % ... 8 hazers", F5 not at the top). The room had a floor (0.003 /m at F5 = 0), the hazers'
// plumes ran at 40 % whatever the fader, the room followed the fader over a 30 s lag, and a fader event the hub filed as
// relative was dropped by the page. F5 at 0 is now no haze anywhere, the top is full, smoothly, and any fader event moves it.
test("the haze fader is ALL the haze: F5 at 0 leaves no haze anywhere (room, noise, the eight hazers' plumes), the top is full, in between it is the fader's share, and it follows smoothly in seconds", async () => {
  const { expandScene } = await import("../arsenal/web/stage/rig.js");
  const { SIGMA_MAX } = await import("../arsenal/web/stage/atmos.js");
  const scene = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
  const rig = expandScene(scene);
  assert.equal(rig.hazers.length, 8);
  const a = new Atmosphere({ hazers: rig.hazers, tau: rig.atmos.tau_s, preHaze: rig.atmos.pre_haze });
  const run = (s) => { for (let i = 0; i < s * 60; i++) a.update(1 / 60); };
  const probes = [...rig.hazers.map((h) => [h.pos[0], h.pos[1] + 1.5, h.pos[2]]), [0, 10, 20], [0, 2, 40], [-12, 20, 10]];
  const densest = () => Math.max(...probes.map((p) => Math.max(a.densityAt(p, 1), a.densityAt(p, 0), a.densityAt(p, -1))));
  // F5 at 0: none
  a.setTarget(0); run(15);
  assert.equal(a.H, 0); assert.equal(a.uniform.sigma0, 0);
  assert.ok(Array.from(a.uniform.hazerSigma).every((x) => x === 0), `the hazers at F5 = 0: ${Array.from(a.uniform.hazerSigma)}`);
  assert.equal(densest(), 0, "no haze at any probe, the hazers' nozzles included");
  // the top: full
  a.setTarget(1); run(15);
  assert.equal(a.H, 1); assert.equal(a.uniform.sigma0, SIGMA_MAX);
  assert.ok(Array.from(a.uniform.hazerSigma).slice(0, 8).every((x) => Math.abs(x - 0.012) < 1e-8));   // (Float32)
  // in between: the fader's share, the room and the plumes alike
  for (const f of [0.25, 0.5, 0.75]) {
    a.setTarget(f); run(15);
    assert.ok(Math.abs(a.uniform.sigma0 - SIGMA_MAX * f) < 1e-9, `F5 ${f}: sigma0 ${a.uniform.sigma0}`);
    assert.ok(Math.abs(a.uniform.hazerSigma[0] - 0.012 * f) < 1e-8);
  }
  // smoothly: a full throw of the fader is 90 % there in 3.5 s, never a step bigger than a frame's share, monotone
  a.setTarget(0); run(15);
  a.setTarget(1);
  let prev = a.uniform.sigma0, t90 = null, biggest = 0, back = 0;
  for (let i = 1; i <= 10 * 60; i++) {
    a.update(1 / 60);
    const s = a.uniform.sigma0;
    biggest = Math.max(biggest, s - prev); if (s < prev - 1e-15) back++;
    if (t90 === null && a.H >= 0.9) t90 = i / 60;
    prev = s;
  }
  assert.ok(t90 !== null && t90 <= 3.5 && t90 >= 2, `90 % of a full throw in ${t90} s`);
  assert.ok(biggest <= SIGMA_MAX * (1 / 60) / rig.atmos.tau_s + 1e-12, `the largest step in a frame: ${biggest}`);
  assert.equal(back, 0, "monotone");
});

test("a fader moves its target whatever kind the hub filed it as: absolute, or a CC it learned as relative (its raw value rides in delta)", async () => {
  const { faderValue } = await import("../arsenal/web/stage/show.js");
  assert.equal(faderValue({ t: "ctl", id: "cc109", kind: "abs", value: 0.5, delta: 3 }), 0.5);
  assert.equal(faderValue({ t: "ctl", id: "cc109", kind: "rel", value: 0.73, delta: 127 - 64 }), 1);
  assert.equal(faderValue({ t: "ctl", id: "cc109", kind: "rel", value: 0.73, delta: 0 - 64 }), 0);
  assert.ok(Math.abs(faderValue({ t: "ctl", id: "cc109", kind: "rel", value: 0.9, delta: 40 - 64 }) - 40 / 127) < 1e-12);
  assert.equal(faderValue({ kind: "abs", value: "x" }), null);
  assert.equal(faderValue(null), null);
});
