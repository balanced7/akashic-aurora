// Virtual Stage v0: kinetics (arsenal/web/stage/kinetics.js). node --test tests/stage_kinetics.test.mjs
// K1: velocity, acceleration and jerk never exceed the hoist's limits; a time-priority formation lands within one frame of
// its target beat at 150 BPM; the roll limit holds in real mode.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Strand, Axis, trapezoidTime, quinticTime, quintic, fitAmplitude, formationTarget, MODES } from "../arsenal/web/stage/kinetics.js";
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
