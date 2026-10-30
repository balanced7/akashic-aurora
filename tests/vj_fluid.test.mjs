// VJ air (arsenal/web/vj-fluid.js): the pure parts and the CPU twin of the solver. node --test tests/vj_fluid.test.mjs
//
// What is pinned: the safety numbers (the air's light rises no faster than the FlashGate's edge; a refused burst and the
// fog body stay under the flash line; CO2 at the gate's edge makes no flash train), the valve, the beam stirs, the
// hazer's noise, and the physics on the twin (the projection, the MacCormack clamp, CO2 rising, blooming, sinking and
// burning off, fog hanging after a push).
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  GRID, SIM, CO2, FOG, LIGHT, GATE_EDGE_S, FLASH_LINE, MAX_EMITTERS, co2Plan, valve, burstLength, emaK, emaRise, emaRipple,
  beamStirs, STIR, co2Emitter, fogEmitters, emitterCells, emitterWeight, hashU, valueNoise, hazeTarget, FluidTwin, bodyLight,
  jetColumn, columnDensity,
} from "../arsenal/web/vj-fluid.js";

const DT = 1 / 60;
const W = 128, H = 72;   // the twin's grid for the physics pins (a quarter of the page's in each axis)

// the 2026-10-24 verifier's counter (vj_storm.mjs, kept the same here so the twin is judged as the page is): turning
// points with a hysteresis of 0.02; a transition is a swing of 0.1 or more whose darker end is under 0.8
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
const maxIn1s = (at) => { let best = 0; for (let i = 0, j = 0; i < at.length; i++) { while (at[i] - at[j] >= 60) j++; best = Math.max(best, i - j + 1); } return best; };
// the bodies' mean light in a window of the screen (0..1 units, y up), the jets' columns added as the air pass adds them
// (cols: [{ x, col: jetColumn(...) }], nozzles on the deck at y 0.02)
function windowLight(tw, x0, y0, w, h, cols = []) {
  let s = 0, n = 0;
  for (let j = Math.floor(y0 * tw.H); j < Math.floor((y0 + h) * tw.H); j++) for (let i = Math.floor(x0 * tw.W); i < Math.floor((x0 + w) * tw.W); i++) {
    const k = j * tw.W + i, x01 = (i + 0.5) / tw.W, y01 = (j + 0.5) / tw.H;
    let jet = 0;
    for (const c of cols) jet += columnDensity(c.col, (x01 - c.x) * tw.W / tw.H, y01 - 0.02);
    s += bodyLight(tw.s[1][k], tw.s[2][k] + CO2.COLUMN_DEPTH * jet, y01); n++;
  }
  return s / n;
}
const WINDOWS = [[0, 0, 0.5, 0.5], [0.25, 0, 0.5, 0.5], [0.5, 0, 0.5, 0.5], [0, 0.5, 0.5, 0.5], [0.25, 0.25, 0.5, 0.5], [0, 0, 1, 1], [0.375, 0, 0.25, 1]];
// run a schedule of bursts and fog on the twin; returns the window series
function play(frames, sched) {
  const tw = new FluidTwin(W, H), bursts = [], fog = { level: 0 };
  const series = WINDOWS.map(() => []);
  for (let f = 0; f < frames; f++) {
    const t = f * DT;
    sched(f, t, bursts, fog);
    const em = [];
    for (const b of bursts) { const lv = valve(b.plan, t - b.t0); if (lv > 0) em.push(co2Emitter(b.x, 0.02, lv)); }
    if (fog.level > 0) em.push(...fogEmitters(fog.level));
    tw.step(DT, { emitters: em.slice(-MAX_EMITTERS), haze: 0.5 });
    const cols = bursts.slice(-CO2.MAX_JETS).map((b) => ({ x: b.x, col: jetColumn(b.plan, t + DT - b.t0) }));
    WINDOWS.forEach((w, k) => series[k].push(windowLight(tw, ...w, cols)));
  }
  return { tw, series };
}

test("the safety numbers: the light's history rises no faster than the gate's edge, the fog body stays under the line", () => {
  assert.equal(GATE_EDGE_S, 1 / 3);                       // FlashGate.minGap (vj-core.js)
  assert.ok(emaRise() >= GATE_EDGE_S, `rise ${emaRise()}`);
  // a beam gated on and off at 3 Hz or faster leaves at most a third of its light as ripple in the air
  assert.ok(emaRipple(3) < 0.45 && emaRipple(8) < 0.2, `${emaRipple(3)} ${emaRipple(8)}`);
  // one frame's step of the history at 60 Hz
  assert.ok(Math.abs(emaK(1 / 60) - (1 - Math.exp(-1 / 60 / LIGHT.EMA_TAU_S))) < 1e-12);
  // the fog body at any density cannot change a window by the flash line on its own
  assert.ok(bodyLight(SIM.C_MAX, 0, 0) < FLASH_LINE);
  // the grid the page runs (the build spec: ~512 x 288, ~20 Jacobi iterations, 16-bit fields)
  assert.deepEqual([GRID.high.W, GRID.high.H, GRID.high.JACOBI], [512, 288, 20]);
});

test("the valve: a granted burst opens fast and full, a refused one smaller and slow, both close", () => {
  const g = co2Plan(true, 1), r = co2Plan(false, 1), soft = co2Plan(true, 0.3);
  assert.equal(g.level, 1); assert.equal(r.level, CO2.REFUSED_SCALE); assert.equal(soft.level, 0.3);
  assert.ok(r.ramp >= GATE_EDGE_S && g.ramp >= 0.1, "the attack ramp is never a cut (research: >= 100 ms)");
  assert.ok(soft.hold < g.hold);
  assert.equal(valve(g, -0.01), 0); assert.equal(valve(g, 0), 0);
  assert.equal(valve(g, g.ramp + 0.01), 1);
  assert.equal(valve(g, burstLength(g) + 0.001), 0);
  for (let t = 0; t < burstLength(g); t += 0.005) assert.ok(Math.abs(valve(g, t + 0.005) - valve(g, t)) < 0.2, "no jump");
});

test("the CO2 column: its tip climbs as sqrt(t), it lifts off at the close and fades; its light rises no faster than the gate's edge", () => {
  const g = co2Plan(true, 1);
  assert.equal(jetColumn(g, -0.1).level, 0);
  const a = jetColumn(g, CO2.TIP_S / 4), b = jetColumn(g, CO2.TIP_S), c = jetColumn(g, 2 * CO2.TIP_S);
  assert.ok(Math.abs(a.tip - CO2.REACH_FH / 2) < 1e-9 && Math.abs(b.tip - CO2.REACH_FH) < 1e-9 && c.tip === CO2.REACH_FH);
  assert.equal(a.tail, 0);
  const open = g.ramp + g.hold, after = jetColumn(g, open + 0.1);
  assert.ok(after.tail > 0.1 && after.level < jetColumn(g, open - 1e-6).level, "lifts off and fades");
  assert.ok(Math.abs(jetColumn(g, open + 1e-6).level - jetColumn(g, open - 1e-6).level) < 1e-3, "no jump at the close");
  assert.equal(jetColumn(g, open + 5 * CO2.FADE_S).level, 0);
  // its own light's 10-90 % rise to the level it reaches before the close
  const peak = jetColumn(g, open - 1e-6).level;
  let t10 = null, t90 = null;
  for (let t = 0; t < open; t += 1e-3) { const l = jetColumn(g, t).level; if (t10 === null && l >= 0.1 * peak) t10 = t; if (t90 === null && l >= 0.9 * peak) t90 = t; }
  assert.ok(t90 - t10 >= GATE_EDGE_S - 0.01, `rise ${t90 - t10}`);
  // the cone: dense on its axis near the nozzle, thinning as it widens, gone beside it and above its tip
  const full = jetColumn(g, open - 1e-6);
  assert.ok(columnDensity(full, 0, 0.05) > 0.9 * full.level);
  assert.ok(columnDensity(full, 0, 0.35) < 0.6 * columnDensity(full, 0, 0.05));
  assert.equal(columnDensity(full, 0, full.tip + 0.01), 0);
  assert.ok(columnDensity(full, 0.3, 0.3) < 1e-3);
});

test("the beams stir the air: a moving beam pushes at three points along it, a new source does not, headers are skipped", () => {
  const prev = new Float32Array(32), seg = new Float32Array(32);
  prev.set([0, -0.5, 0.1, 0.4]); seg.set([0, -0.5, 0.2, 0.4]);              // row 0: the same head, its tip moved 0.1
  prev.set([0.3, -0.5, 0.3, 0.4], 8); seg.set([-0.6, -0.5, 0.3, 0.4], 8);   // row 1: another head now (a new deal)
  prev.set([0, 0, 0.2, 1002], 16); seg.set([0, 0, 0.2, 1002], 16);         // row 2: a figure's header
  const s = beamStirs(prev, 3, seg, 3, 1 / 60, 16 / 9);
  assert.equal(s.length, 3);
  assert.ok(s.every((x) => x.vx > 0 && Math.abs(x.vy) < 1e-9 && x.r === STIR.RADIUS_FH));
  assert.ok(Math.hypot(s[2].vx, s[2].vy) <= STIR.MAX_FH * STIR.GAIN + 1e-9, "capped");
  assert.ok(s[0].vx < s[2].vx, "the tip end moves most");
  assert.ok(Math.abs(s[2].x - ((0 + 0.2 * 0.95) / (16 / 9) + 0.5)) < 1e-6 && Math.abs(s[2].y - (-0.5 + 0.9 * 0.95 + 0.5)) < 1e-6);
  assert.deepEqual(beamStirs(null, 0, seg, 3, 1 / 60, 16 / 9), []);
});

test("the hazer's noise: deterministic, in range, textured; the haze target follows the level", () => {
  assert.equal(hashU(3, 7), hashU(3, 7));
  assert.notEqual(hashU(3, 7), hashU(7, 3));
  assert.equal(hashU(-1, 0), hashU(0xffffffff, 0));         // negative cells wrap as the GLSL's uvec2(ivec2) does
  let lo = 1, hi = 0;
  for (let i = 0; i < 400; i++) { const v = valueNoise(i * 0.37, i * 0.11); lo = Math.min(lo, v); hi = Math.max(hi, v); }
  assert.ok(lo >= 0 && hi <= 1 && hi - lo > 0.5);
  assert.equal(hazeTarget(0, 0.3, 0.2, 5), 0);
  const h = hazeTarget(0.5, 0.3, 0.2, 5);
  assert.ok(h >= 0.5 * 0.55 - 1e-9 && h <= 0.5 * 1.45 + 1e-9);
});

test("the emitters: a cone along the aim, soft at both ends, zero behind the nozzle; fog from the deck's two ends", () => {
  const [e] = emitterCells([co2Emitter(0.5, 0.02, 1)], 512, 288);
  assert.ok(Math.abs(e.u0 - CO2.U0_FH * 288) < 1e-9);
  const at = (dx, dy) => emitterWeight(e, e.x + dx, e.y + dy);
  assert.ok(at(0, e.near * 0.3) > 0.9);
  assert.ok(at(0, -2 * e.r0) < 1e-6 && at(0, 1.2 * e.near) < 1e-6);
  assert.ok(at(e.r0 * 2.5, e.near * 0.2) < 0.2 * at(0, e.near * 0.2), "narrow across");
  const f = fogEmitters(1);
  assert.equal(f.length, FOG.NOZZLES.length);
  assert.ok(f[0].dx > 0 && f[1].dx < 0 && f.every((x) => x.dy > 0 && x.channel === 1));
});

test("the twin: the projection takes most of the divergence; what it leaves is the grid's, not the iteration count's", () => {
  const div = (jacobi) => {
    const tw = new FluidTwin(64, 36, { jacobi });
    for (let f = 0; f < 10; f++) tw.step(DT, { emitters: [co2Emitter(0.5, 0.02, 1)], stirs: [{ x: 0.3, y: 0.5, vx: 1, vy: 0.4, r: 0.08 }] });
    let rms = 0;
    for (let j = 1; j < 35; j++) for (let i = 1; i < 63; i++) {
      const r = tw.velAt(i + 1, j), l = tw.velAt(i - 1, j), t = tw.velAt(i, j + 1), b = tw.velAt(i, j - 1);
      rms += (0.5 * ((r[0] - l[0]) + (t[1] - b[1]))) ** 2;
    }
    return { max: tw.maxDiv(), rms: Math.sqrt(rms / (62 * 34)) };
  };
  const d0 = div(0), d20 = div(20), d200 = div(200);
  assert.ok(d20.max < 0.3 * d0.max && d20.rms < 0.45 * d0.rms, JSON.stringify([d0, d20]));
  // the collocated grid's checkerboard: the compact Laplacian cannot see it, so 200 iterations leave about what 20 do
  assert.ok(d200.rms < 1.25 * d20.rms, JSON.stringify([d20, d200]));
});

test("the twin: MacCormack with the clamp makes no new extremes (each value inside its four nodes)", () => {
  const tw = new FluidTwin(48, 27);
  let a = 1;
  const r = () => { a = (a * 1664525 + 1013904223) >>> 0; return a / 4294967296; };
  for (let k = 0; k < tw.u.length; k++) { tw.u[k] = (r() - 0.5) * 900; tw.v[k] = (r() - 0.5) * 900; tw.s[2][k] = r(); }
  const out = new Float32Array(tw.u.length), hat = new Float32Array(tw.u.length);
  tw.advect([tw.s[2]], [hat], [out], DT);
  let lo = Infinity, hi = -Infinity;
  for (const v of tw.s[2]) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  for (let j = 0; j < 27; j++) for (let i = 0; i < 48; i++) {
    const k = j * 48 + i, [bl, bh] = tw.bounds(tw.s[2], i + 0.5 - DT * tw.u[k], j + 0.5 - DT * tw.v[k]);
    assert.ok(out[k] >= bl - 1e-6 && out[k] <= bh + 1e-6 && out[k] >= lo && out[k] <= hi);
  }
});

test("the twin: a CO2 jet shoots up, blooms, then sinks and burns off within about two seconds", () => {
  const tw = new FluidTwin(W, H), plan = co2Plan(true, 1);
  const com = [], mass = [], wide = [];
  for (let f = 0; f <= 180; f++) {
    const lv = valve(plan, f * DT);
    tw.step(DT, { emitters: lv > 0 ? [co2Emitter(0.5, 0.02, lv)] : [], haze: 0.5 });
    com.push(tw.heightOf(2) ?? 0); mass.push(tw.total(2));
    let cols = 0;
    for (let i = 0; i < W; i++) { let any = false; for (let j = 0; j < H; j++) if (tw.s[2][j * W + i] > 0.08) { any = true; break; } if (any) cols++; }
    wide.push(cols / W * (W / H));                                    // the plume's width in frame heights
  }
  const top = Math.max(...com), topAt = com.indexOf(top), peak = Math.max(...mass);
  assert.ok(top > 0.35, `the cloud rises to ${top}`);
  assert.ok(topAt * DT > 0.6 && topAt * DT < 1.6, `it turns at ${topAt * DT} s`);
  assert.ok(com[180] < top - 0.15, `then sinks (${com[180]})`);
  assert.ok(Math.max(...wide) > 0.3, `it blooms (${Math.max(...wide)} fh wide)`);
  assert.ok(mass[180] < 0.2 * peak, `and burns off (${mass[180] / peak} of its peak at 3 s)`);
});

test("the twin: CO2 light rises no faster than the gate's edge; at the gate's edge it makes no flash train", () => {
  // one granted burst: its rise in the quarter above the nozzle
  const one = play(120, (f, t, bursts) => { if (f === 0) bursts.push({ t0: 0, x: 0.5, plan: co2Plan(true, 1) }); });
  const L = one.series[1], pk = Math.max(...L);
  const rise = (L.findIndex((v) => v >= 0.9 * pk) - L.findIndex((v) => v >= 0.1 * pk)) * DT;
  assert.ok(rise >= GATE_EDGE_S, `rise ${rise} s`);
  // granted every 20 frames (the gate's own edge) on three nozzles, with fog pushed and released in the second half
  const edge = play(360, (f, t, bursts, fog) => {
    if (f % 20 === 0) bursts.push({ t0: t, x: [0.2, 0.5, 0.8][(f / 20) % 3], plan: co2Plan(true, 1) });
    fog.level = f < 180 ? 1 : Math.floor(f / 12) % 2;
  });
  // the house line is 3 flashes (6 transitions) a second; each column's on and off is the flash its granted slot paid
  // for, and the strip over a nozzle sees at most 1.5 a second (measured 3 transitions): pinned with that margin
  for (const s of edge.series) assert.ok(maxIn1s(transitions(s)) <= 4, "at most two flashes a second in any window");
  // refused bursts hammered every 3 frames never reach the flash line
  const refused = play(240, (f, t, bursts) => { if (f % 3 === 0) bursts.push({ t0: t, x: [0.2, 0.5, 0.8][(f / 3) % 3], plan: co2Plan(false, 1) }); if (bursts.length > 8) bursts.shift(); });
  for (const s of refused.series) assert.equal(transitions(s).length, 0);
});

test("the twin: a fog push builds while held and hangs after release, decaying on its own clock", () => {
  const tw = new FluidTwin(W, H);
  const mass = [];
  for (let f = 0; f < 60 * 4; f++) { tw.step(DT, { emitters: f < 90 ? fogEmitters(1) : [], haze: 0.5 }); mass.push(tw.total(1)); }
  assert.ok(mass[89] > mass[30] && mass[30] > 0, "builds while held");
  // after the release it only falls (MacCormack is not conservative: it may keep a little more than the clock alone)
  for (let f = 120; f < 240; f += 15) assert.ok(mass[f + 15 - 1] <= mass[f] * 1.005, `falls from ${f}`);
  const after = mass[90 + 120] / mass[90];
  assert.ok(after < 0.92 && after > Math.exp(-2 / SIM.TAU_S.fog) - 0.05, `two seconds on: ${after}`);
  assert.ok((tw.heightOf(1) ?? 0) > 0.06, "warm fog lifts off the deck");
});
