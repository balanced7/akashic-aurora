// Virtual Stage v0: kinetics (arsenal/web/stage/kinetics.js). node --test tests/stage_kinetics.test.mjs
// K1: velocity, acceleration and jerk never exceed the hoist's limits; a time-priority formation lands within one frame of
// its target beat at 150 BPM; the roll limit holds in real mode.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Strand, Axis, trapezoidTime, quinticTime, quintic, fitAmplitude, formationTarget, MODES, sCurveTime, sCurvePlan, sCurveAt, sCurveFit,
         RingRig, ringAxisLimits, nearestTurn, hermite } from "../arsenal/web/stage/kinetics.js";
import { BeatGrid } from "../arsenal/web/stage/grid.js";

const FPS = 60, DT = 1 / FPS;

test("the design's arithmetic: a 6 m move at 0.4 m/s and 0.4 m/s^2 takes 16 s (10 bars at 150 BPM)", () => {
  assert.equal(trapezoidTime(6, 0.4, 0.4), 16);
  assert.equal((16 * 150) / 60 / 4, 10);
  assert.ok(Math.abs(trapezoidTime(0.2, 0.5, 0.4) - 2 * Math.sqrt(0.2 / 0.4)) < 1e-12, "a short move never reaches cruise");
  assert.ok(Math.abs(quintic(0.5) - 0.5) < 1e-12 && quintic(0) === 0 && quintic(1) === 1);
});

test("fitAmplitude keeps a sine inside every limit", () => {
  const lim = MODES.real;
  const A = fitAmplitude(3, 12.8, lim);
  const w = (2 * Math.PI) / 12.8;
  assert.ok(A * w <= lim.vmax + 1e-12 && A * w * w <= lim.amax + 1e-12 && A * w ** 3 <= lim.jmax + 1e-12);
});

// differentiate a sampled series and return the peaks
function peaks(xs, dt) {
  let v = 0, a = 0, j = 0;
  const vs = [], as = [];
  for (let i = 1; i < xs.length; i++) vs.push((xs[i] - xs[i - 1]) / dt);
  for (let i = 1; i < vs.length; i++) as.push((vs[i] - vs[i - 1]) / dt);
  for (const x of vs) v = Math.max(v, Math.abs(x));
  for (const x of as) a = Math.max(a, Math.abs(x));
  for (let i = 1; i < as.length; i++) j = Math.max(j, Math.abs((as[i] - as[i - 1]) / dt));
  return { v, a, j };
}

function simulate({ seconds, onFrame, mode = "real" }) {
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  const strand = new Strand({ rungs: 12, mode });
  const series = Array.from({ length: 24 }, () => []);
  let t = 0;
  for (let f = 0; f <= seconds * FPS; f++) {
    t = f * (1000 / FPS);
    if (onFrame) onFrame(f, t, grid, strand);
    strand.update(grid, t, DT);
    strand.axes.forEach((ax, k) => series[k].push(ax.x));
  }
  return { grid, strand, series };
}

test("K1: the travelling wave never exceeds vmax, amax or jerk on any of the 24 hoists (real mode, 60 s)", () => {
  const { series, strand } = simulate({
    seconds: 60,
    onFrame: (f, t, grid, s) => {
      if (f === 0) s.set("ceiling", { y: 20 }, grid.bpm);
      if (f === 30) s.land("wave", { centre: 17, size: 0.9, roll: 16, measure: 32 }, grid, t);
      if (f === 60 * 28) s.land("wave", { centre: 14.5, size: 0.9, roll: 16, measure: 32 }, grid, t);
    },
  });
  const lim = strand.lim;
  for (const xs of series) {
    const p = peaks(xs, DT);
    assert.ok(p.v <= lim.vmax * 1.02, `v ${p.v}`);
    assert.ok(p.a <= lim.amax * 1.03, `a ${p.a}`);
    assert.ok(p.j <= lim.jmax * 1.08, `j ${p.j}`);
  }
});

test("time priority: the move lands on the bar line it was given, within one frame", () => {
  let plan = null, endFrame = null, errAtEnd = null;
  const { grid } = simulate({
    seconds: 30,
    onFrame: (f, t, g, s) => {
      if (f === 0) s.set("ceiling", { y: 20 }, g.bpm);
      if (f === 12) plan = s.land("low", { y: 17.5 }, g, t);
      // the frame the move completes (the reference reaches its landing): every hoist must be there, give or take 1 cm
      if (plan && endFrame === null && f > 12 && !s.move) {
        endFrame = f;
        errAtEnd = Math.max(...s.axes.map((ax) => Math.abs(ax.x - 17.5)));
      }
    },
  });
  assert.ok(plan, "a landing was planned");
  assert.equal(plan.posLand % 4, 0, "the landing is a bar line (bars on multiples of 4 here)");
  const targetFrame = (plan.posLand * grid.period) / (1000 / FPS);
  assert.ok(endFrame !== null, "it landed");
  assert.ok(Math.abs(endFrame - targetFrame) <= 1, `the move ended at frame ${endFrame}, the bar line is frame ${targetFrame}`);
  assert.ok(errAtEnd < 0.01, `every hoist within 1 cm at the ONE (worst ${errAtEnd} m)`);
  // and it was given no more than a bar beyond the time it needed
  assert.ok((plan.posLand * grid.period) / 1000 - 0.2 - plan.tMinS < (4 * grid.period) / 1000);
});

test("the roll limit holds in real mode (+-50), dream mode turns past it", () => {
  const real = new Strand({ rungs: 12, mode: "real" });
  const [hL, hR] = real.hoists(18, 80);
  const roll = (Math.asin((hR - hL) / real.L) * 180) / Math.PI;
  assert.ok(Math.abs(roll - 50) < 1e-9, `real roll ${roll}`);
  const dream = new Strand({ rungs: 12, mode: "dream" });
  const [dL, dR] = dream.hoists(18, 80);
  assert.ok((Math.asin((dR - dL) / dream.L) * 180) / Math.PI > 79.9);
  // the helix formation, clamped
  const t = formationTarget("helix", {}, 11, 12, 0);
  assert.ok(t.roll > 50, "the formation asks for more");
  const h = real.hoists(t.y, t.roll);
  assert.ok(Math.abs(h[1] - h[0]) <= real.L * Math.sin((50 * Math.PI) / 180) + 1e-9);
});

test("the star formation drops the front rungs into a mandala at 0, 30, ... 150 degrees", () => {
  const rolls = [];
  for (let i = 0; i < 6; i++) rolls.push(formationTarget("star", {}, i, 12, 0).roll);
  assert.deepEqual(rolls, [0, 30, 60, 90, 120, 150]);
  assert.equal(formationTarget("star", {}, 8, 12, 0).y, 21);
});

test("an axis follows a reference with feed-forward and never violates a limit", () => {
  const ax = new Axis({ x: 0, vmax: 0.5, amax: 0.4, jmax: 2 });
  const xs = [];
  for (let f = 0; f < 60 * 20; f++) { ax.step(f < 60 ? 0 : 5, 0, 0, DT); xs.push(ax.x); }   // a step input: the worst case
  const p = peaks(xs, DT);
  assert.ok(p.v <= 0.5 * 1.01 && p.a <= 0.4 * 1.03 && p.j <= 2 * 1.08, JSON.stringify(p));
  assert.ok(Math.abs(xs[xs.length - 1] - 5) < 0.02, "it gets there");
  assert.ok(quinticTime(5, 0.5, 0.4, 2) > 0);
});

// ------------------------------------------------------------------------------------- v2: kinetics wave A --
test("the S-curve with cruise: 2, 6 and 12 m at the real limits take 5.45, 13.45 and 25.45 s (the quintic 7.5, 22.5, 45)", () => {
  const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);
  close(sCurveTime(2, 0.5, 0.4, 2), 5.45); close(sCurveTime(6, 0.5, 0.4, 2), 13.45); close(sCurveTime(12, 0.5, 0.4, 2), 25.45);
  assert.ok(Math.abs(quinticTime(6, 0.5, 0.4, 2) - 22.5) < 1e-9, "the quintic is 67 % slower");
  // short moves never reach cruise (with and without the acceleration limit): the peak stays under vmax, the end is exact
  for (const D of [0.05, 0.5, 0.7]) {
    const p = sCurvePlan(D, 0.5, 0.4, 2);
    assert.ok(p.Tv === 0 && p.vp < 0.5);
    close(sCurveAt(p, p.T).s, D);
  }
});

test("the S-curve profile honours every limit and arrives exactly; stretched (time priority) it still does", () => {
  for (const [D, T] of [[6, 0], [6, 20], [0.4, 0], [12, 40], [1.2, 9]]) {
    const p = T ? sCurveFit(D, T, 0.5, 0.4, 2) : sCurvePlan(D, 0.5, 0.4, 2);
    if (T) assert.ok(Math.abs(p.T - T) < 1e-6, `stretched to ${T}: ${p.T}`);
    const xs = [];
    for (let t = 0; t <= p.T + 1e-9; t += DT) xs.push(sCurveAt(p, t).s);
    xs.push(sCurveAt(p, p.T).s);
    const pk = peaks(xs, DT);
    assert.ok(pk.v <= 0.5 * 1.01 && pk.a <= 0.4 * 1.03 && pk.j <= 2 * 1.1, JSON.stringify({ D, T, pk }));
    assert.ok(Math.abs(xs[xs.length - 1] - D) < 1e-9 && xs.every((x, i) => i === 0 || x >= xs[i - 1] - 1e-12), "monotone, exact");
  }
});

test("a strand formation may land on the S-curve: earlier than the quintic, inside the hoists' limits, on its bar line", () => {
  const run = (params) => {
    let plan = null;
    const r = simulate({ seconds: 40, onFrame: (f, t, g, s) => {
      if (f === 0) s.set("ceiling", { y: 20 }, g.bpm);
      if (f === 12) plan = s.land("ramp", params, g, t);
    } });
    return { plan, ...r };
  };
  const q = run({ top: 21, step: 1.1 }), sc = run({ top: 21, step: 1.1, curve: "scurve" });
  assert.ok(sc.plan.posLand < q.plan.posLand, `the S-curve lands at beat ${sc.plan.posLand}, the quintic at ${q.plan.posLand}`);
  assert.equal(sc.plan.posLand % 4, 0);
  for (const xs of sc.series) {
    const pk = peaks(xs, DT);
    assert.ok(pk.v <= 0.5 * 1.02 && pk.a <= 0.4 * 1.04, JSON.stringify(pk));
  }
  for (let i = 0; i < 12; i++) assert.ok(Math.abs(sc.strand.poses[i].y - (21 - 1.1 * i)) < 0.02, `rung ${i} at ${sc.strand.poses[i].y}`);
});

test("the strand shapes: an arch cresting mid-hall, a valley, a ramp pouring toward the eye, stairs in pairs", () => {
  const ys = (name, p = {}) => Array.from({ length: 12 }, (_, i) => formationTarget(name, p, i, 12, 0).y);
  const arch = ys("arch");
  assert.ok(Math.abs(Math.max(...arch) - (9 + 12 * Math.sin(Math.PI * 5.5 / 12))) < 1e-9 && arch[5] === arch[6] && arch[0] < arch[5]);
  const valley = ys("valley");
  assert.ok(valley[0] === 20 && valley[11] === 20 && Math.min(...valley) < 11 && valley[5] === valley[6]);
  const ramp = ys("ramp");
  assert.ok(ramp[0] === 21 && Math.abs(ramp[11] - 8.9) < 1e-9 && ramp.every((y, i) => i === 0 || y < ramp[i - 1]));
  assert.deepEqual(ys("stairs"), [20, 20, 16, 16, 20, 20, 16, 16, 20, 20, 16, 16]);
  for (const y of [...arch, ...valley, ...ramp]) assert.ok(y >= 8 && y <= 22, "inside the rungs' height limits");
});

test("the honest real helix: the travelling roll sine fits to +-13.7 degrees at a 32-beat measure, +-50 only at about 104", () => {
  const s = new Strand({ rungs: 12, mode: "real" });
  const at32 = s.fit("wave", { size: 0, roll: 50, measure: 32, spread: 2.67 }, 150)._R;
  const at104 = s.fit("wave", { size: 0, roll: 50, measure: 104, spread: 2.67 }, 150)._R;
  assert.ok(Math.abs(at32 - 13.7) < 0.1, `${at32}`);
  assert.ok(at104 > 49 && at104 <= 50, `${at104}`);
});

// the rings: R0 to R3 (radius 14, 10, 6.5, 3), home tilts 55 / 40 / 25 / 10 at 14 m
const RINGS = [14, 10, 6.5, 3].map((r, k) => ({ radius: r, home: { y: 14, tilt: [55, 40, 25, 10][k] }, limits: { y: [14, 18.5], tilt: [0, 90] } }));
function ringRun({ seconds, onFrame, rings = RINGS }) {
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  const rr = new RingRig({ rings });
  const series = rings.map(() => ({ y: [], tilt: [], yaw: [], spin: [], axial: [] }));
  for (let f = 0; f <= seconds * FPS; f++) {
    const t = f * (1000 / FPS);
    if (onFrame) onFrame(f, t, grid, rr);
    rr.update(grid, t, DT);
    rr.poses.forEach((p, k) => { for (const d of ["y", "tilt", "yaw", "spin", "axial"]) series[k][d].push(p[d]); });
  }
  return { grid, rr, series };
}

test("the ring tilt rate is the hoist's speed over the pickup radius: R0 2.0 deg/s, R3 9.5 deg/s; dream x3", () => {
  const r0 = ringAxisLimits(null, 14, "real"), r3 = ringAxisLimits(null, 3, "real"), d0 = ringAxisLimits(null, 14, "dream");
  assert.ok(Math.abs(r0.tilt.vmax - (0.5 / 14) * 180 / Math.PI) < 1e-9 && Math.abs(r0.tilt.vmax - 2.046) < 0.001);
  assert.ok(Math.abs(r3.tilt.vmax - 9.549) < 0.001);
  assert.ok(Math.abs(d0.tilt.vmax - 3 * r0.tilt.vmax) < 1e-9 && r0.rot === null && d0.rot.vmax > 0, "the rotators are dream-only");
  // a real 35-degree tilt of R0 takes about 17 s (11 bars at 150 BPM), not the 3.6 bars a 6 deg/s guess gave
  const T = sCurveTime(35, r0.tilt.vmax, r0.tilt.amax, r0.tilt.jmax);
  assert.ok(T > 17 && T < 19, `${T}`);
});

test("RingRig real: lift before tilt, the lowering after it; every axis inside its real limits; lands on a bar line", () => {
  const up = { rings: [{ tilt: 30, lift: 4 }, { tilt: 40, lift: 4 }, { tilt: 25, lift: 4 }, { tilt: 10, lift: 4 }] };
  let plan = null, plan2 = null;
  const { series, rr, grid } = ringRun({ seconds: 140, onFrame: (f, t, g, r) => {
    if (f === 6) plan = r.land("up", up, g, t);
    if (plan && !plan2 && !r.move && f > 6) plan2 = r.land("home", { rings: RINGS.map((x) => ({ tilt: x.home.tilt })) }, g, t);
  } });
  assert.ok(plan && plan2, "both moves planned");
  const m = plan.rings[0];
  assert.ok(m.rise && m.split > m.start && m.land % 4 === 0, JSON.stringify(m));
  const fOf = (pos) => Math.round((pos * grid.period) / (1000 / FPS));
  const S = series[0];
  assert.ok(Math.abs(S.tilt[fOf(m.split) - 2] - 55) < 0.05, `the tilt holds while R0 lifts: ${S.tilt[fOf(m.split) - 2]}`);
  assert.ok(Math.abs(S.y[fOf(m.split) + 2] - 18) < 0.05, `the height holds while R0 tilts: ${S.y[fOf(m.split) + 2]}`);
  const m2 = plan2.rings[0];
  assert.ok(m2.lower && Math.abs(S.y[fOf(m2.split) - 2] - 18) < 0.05, "the lowering waits for the tilt");
  const L = ringAxisLimits(null, 14, "real");
  const pkT = peaks(S.tilt, DT), pkY = peaks(S.y, DT);
  assert.ok(pkT.v <= L.tilt.vmax * 1.02 && pkY.v <= 0.5 * 1.02 && pkY.a <= 0.4 * 1.04, JSON.stringify({ pkT, pkY }));
  assert.ok(Math.abs(rr.poses[0].tilt - 55) < 0.02 && Math.abs(rr.poses[0].y - 14) < 0.02, "home again");
});

test("RingRig clamps a tilt into the ring's legal window at its height, and says so", () => {
  const rings = RINGS.map((r, k) => ({ ...r, window: k === 0 ? (y) => (y < 18 ? [47.5, 63] : [0, 63]) : null }));
  const rr = new RingRig({ rings });
  const t = rr.target({ rings: [{ tilt: 0 }, {}, {}, {}] }, 0, 0, undefined, true);
  assert.equal(t.tilt, 47.5);
  assert.equal(rr.clamped.at(-1).asked, 0);
  assert.equal(rr.target({ rings: [{ tilt: 0, lift: 4.5 }, {}, {}, {}] }, 0, 0).tilt, 0, "lifted, it may stand upright");
});

test("dream rotators: unwrapped continuous turns at prime rates (never the two-pickup roll, which aliases past 90)", () => {
  const orrery = { dream: true, rings: [{ tilt: 55, spin_beats: 113 }, { tilt: 80, yaw_beats: 89 }, { tilt: 60, yaw_beats: -67 }, { tilt: 30, yaw_beats: 37 }],
                   reveal: { order: [3, 2, 1, 0], stagger_beats: 4 } };
  let plan = null;
  const { series, rr, grid } = ringRun({ seconds: 150, onFrame: (f, t, g, r) => { if (f === 6) plan = r.land("orrery", orrery, g, t); } });
  // the reveal in depth order: R3 starts first, each ring a stagger later; the formation lands when its last ring does
  const starts = plan.rings.map((x) => x.start);
  assert.ok(starts[3] < starts[2] && starts[2] < starts[1] && starts[1] < starts[0]);
  assert.equal(plan.posLand, Math.max(...plan.rings.map((x) => x.land)));
  // landed, R1 turns at 360 / 89 degrees a beat, R2 at -360 / 67, R3 at 360 / 37, R0 spins at 360 / 113 (the last 40 beats)
  const n = series[1].yaw.length, span = Math.round((40 * grid.period) / (1000 / FPS));
  const rate = (k, d = "yaw") => (series[k][d][n - 1] - series[k][d][n - 1 - span]) / 40;
  assert.ok(Math.abs(rate(1) - 360 / 89) < 0.02 && Math.abs(rate(2) + 360 / 67) < 0.02 && Math.abs(rate(3) - 360 / 37) < 0.02, `${rate(1)} ${rate(2)} ${rate(3)}`);
  assert.ok(Math.abs(rate(0, "spin") - 360 / 113) < 0.02);
  assert.ok(series[3].yaw[n - 1] > 720, "unwrapped: past two whole turns, with no wrap and no alias");
  for (const k of [1, 2, 3]) for (let i = 1; i < n; i++) assert.ok(Math.abs(series[k].yaw[i] - series[k].yaw[i - 1]) < 1.5, "continuous on every frame");
  // the periods are pairwise coprime: the set repeats only after their product
  const gcd = (a, b) => (b ? gcd(b, a % b) : a);
  const P = [113, 89, 67, 37];
  for (let a = 0; a < 4; a++) for (let b = a + 1; b < 4; b++) assert.equal(gcd(P[a], P[b]), 1);
  assert.ok(P.reduce((x, y) => x * y, 1) > 24e6);
  assert.ok(Math.abs(rr.poses[1].tilt - 80) < 0.05);
});

test("a Hermite spin-up arrives at the angle and the speed it was asked for", () => {
  const h = hermite(10, 0, 370, 90, 1);
  assert.ok(Math.abs(h.x - 370) < 1e-9 && Math.abs(h.v - 90) < 1e-9);
  const h0 = hermite(10, 0, 370, 90, 0);
  assert.ok(Math.abs(h0.x - 10) < 1e-9 && Math.abs(h0.v) < 1e-9);
  assert.equal(nearestTurn(5, 725), 725);
});
