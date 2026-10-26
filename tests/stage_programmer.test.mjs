// Virtual Stage v0: the programmer, the show runner and the atmosphere (arsenal/web/stage/programmer.js, show.js,
// atmos.js). node --test tests/stage_programmer.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { Programmer, Slew, slewFor, resolveTheme, nearestSlot, H, HEAD_FLOATS } from "../arsenal/web/stage/programmer.js";
import { Show, speedFromFader } from "../arsenal/web/stage/show.js";
import { BeatGrid, DemoBeats, beatExtras } from "../arsenal/web/stage/grid.js";
import { Atmosphere, SIGMA_CAP, visibility, phaseHG, hazeNoise3D, clampSigma } from "../arsenal/web/stage/atmos.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v0.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const THEME = { name: "source-violet", ...SCENE.themes["source-violet"] };
const FPS = 60, DT = 1 / FPS;

function locked(bpm = 150) {
  const g = new BeatGrid({ bpm, t0: 0 });
  g.beat({ due_ms: 0, bpm, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
  return g;
}

test("physics: a pan never moves faster than its motor (540 deg in 2.2 s) nor accelerates past it", () => {
  const s = slewFor({ min: -270, max: 270, real_fade: 2.2, real_accel: 0.2 });
  const xs = [];
  for (let f = 0; f < FPS * 4; f++) xs.push(s.step(270, DT));
  let vmax = 0, amax = 0, prevV = 0;
  for (let i = 1; i < xs.length; i++) {
    const v = (xs[i] - xs[i - 1]) / DT;
    vmax = Math.max(vmax, Math.abs(v));
    if (i > 1) amax = Math.max(amax, Math.abs(v - prevV) / DT);
    prevV = v;
  }
  assert.ok(vmax <= (540 / 2.2) * 1.0001, `v ${vmax}`);
  assert.ok(amax <= (540 / 2.2 / 0.2) * 1.0001, `a ${amax}`);
  assert.equal(xs.at(-1), 270, "it lands on the target");
  // a real move takes at least its range over the speed
  const t = xs.findIndex((x) => x === 270) / FPS;
  assert.ok(t >= 270 / (540 / 2.2), `got there in ${t} s`);
  assert.ok(new Slew(0, 1, 10).step(0.5, 0) === 0);
});

test("themes refuse saturated red roles; the wheel snaps to its nearest slot", () => {
  assert.throws(() => resolveTheme({ name: "bad", A: "#ff0000", B: "#0000ff", W: "#ffffff", beamA: "#ffffff", beamB: "#ffffff", warm: "#ffaa55" }));
  const wheel = SCENE.types["beam-7r"].attrs.Color1.colours;
  const lin = (h) => { const v = parseInt(h.slice(1), 16); return [(v >> 16 & 255) / 255, (v >> 8 & 255) / 255, (v & 255) / 255]; };
  assert.equal(nearestSlot(wheel.map(lin), [1, 1, 1]), 0);
  assert.equal(nearestSlot(wheel.map(lin), lin("#19ff4a")), 5);
});

test("looks: every level stays in 0..1, the unison pulse on the strand never dips below 60 % of its base", () => {
  const g = locked();
  const p = new Programmer(RIG, { theme: THEME });
  p.setLook("drop", 0);
  let lo = Infinity;
  for (let f = 0; f < FPS * 8; f++) {
    const t = f * (1000 / FPS);
    p.tick(g, t, DT);
    for (let i = 0; i < p.nH; i++) {
      const d = p.heads[i * HEAD_FLOATS + H.DIM];
      assert.ok(d >= 0 && d <= 1);
      if (p.strandHead[i] && f > FPS) lo = Math.min(lo, d);
    }
    for (let c = 0; c < p.nC; c++) assert.ok(p.pixels[c * 4 + 3] >= 0 && p.pixels[c * 4 + 3] <= 1);
  }
  assert.ok(lo >= 0.6 - 1e-6, `the strand's trough ${lo}`);
});

test("KICK lands on the beat: a press up to half a beat early waits for the line; the lift peaks on the beat frame, +-1, over 64 beats", () => {
  const g = locked();
  const p = new Programmer(RIG, { theme: THEME });
  p.setLook("break", 0);
  const cubeCell = RIG.cells.kind.indexOf(2);
  const lv = [];
  let next = 4;
  for (let f = 0; f < FPS * 30; f++) {
    const t = f * (1000 / FPS), pos = g.posAt(t);
    if (next <= 67 && pos >= next - 0.15) { p.pad("kick", 1, pos); next += 1; }   // an early press, as a player anticipates
    p.tick(g, t, DT);
    lv.push(p.pixels[cubeCell * 4 + 3]);
  }
  let checked = 0;
  for (let k = 4; k <= 67; k++) {
    const beatFrame = Math.round((k * 400) / (1000 / FPS));
    // the frame of the highest level within half a beat of the line
    let best = -1, bf = -1;
    for (let f = beatFrame - 12; f <= beatFrame + 12; f++) if (lv[f] > best) { best = lv[f]; bf = f; }
    assert.ok(Math.abs(bf - beatFrame) <= 1, `beat ${k}: the lift peaked at frame ${bf}, the beat is frame ${beatFrame}`);
    assert.ok(best > 0.99, `beat ${k}: the lift reached ${best}`);
    checked++;
  }
  assert.equal(checked, 64);
  assert.equal(p.stats.kicks.length, 64);
});

test("the show: sections change on bar lines in the demo plan, and DROP NOW drops on the next downbeat", () => {
  const demo = new DemoBeats({ bpm: 150, startMs: 0 });
  const g = new BeatGrid({ bpm: 150, t0: 0 });
  const show = new Show(RIG, { demo: true });
  const seen = [], pads = [];
  for (let f = 0; f < FPS * 70; f++) {
    const t = f * (1000 / FPS);
    demo.tick(t, (o) => g.beat({ ...o, ...beatExtras(o) }, t));
    if (!g.locked) continue;
    for (const ev of show.update(g, g.posAt(t))) {
      if (ev.type === "section") seen.push([ev.name, ev.pos]);
      if (ev.type === "pad" && ev.on) pads.push([ev.pad, ev.pos, show.section.name]);
    }
  }
  const names = seen.map((s) => s[0]);
  assert.deepEqual(names.slice(0, 5), ["intro", "build", "drop", "break", "intro"]);
  for (const [, pos] of seen) assert.equal(((pos - g.barAnchor) % 4 + 4) % 4, 0, `a section began off the bar line at ${pos}`);
  assert.equal(seen[1][1] - seen[0][1], 32); assert.equal(seen[2][1] - seen[1][1], 32); assert.equal(seen[3][1] - seen[2][1], 64);
  // the demo's pads: KICK on every drop downbeat, DROP NOW in the build's last bar, a held laser gate into the drop
  const kicks = pads.filter((p) => p[0] === 1);
  assert.equal(kicks.length, 16);
  assert.ok(pads.some((p) => p[0] === 10 && p[2] === "build"));
  // DROP NOW in engine mode
  const g2 = locked();
  const live = new Show(RIG, { demo: false });
  live.update(g2, 0.1);
  const at = live.dropNow(g2, 5.3);
  assert.equal(at, 8);
  let dropped = null;
  for (let pos = 5.3; pos < 9; pos += 0.05) for (const ev of live.update(g2, pos)) if (ev.type === "section" && ev.name === "drop") dropped = ev.pos;
  assert.equal(dropped, 8);
  assert.equal(speedFromFader(0.5), 1); assert.equal(speedFromFader(1), 4); assert.equal(speedFromFader(0), 0.25);
});

test("the atmosphere: never denser than 0.26 /m (whiteout guard), the lag of the machines, the physics constants", () => {
  const a = new Atmosphere({ hazers: RIG.hazers, tau: 30, preHaze: 0.1 });
  a.setTarget(1);
  for (let i = 0; i < 30 * 60; i++) a.update(1 / 60);
  // after one time constant the room has made 63 % of the step
  assert.ok(Math.abs((a.H - 0.1) / 0.9 - (1 - Math.exp(-1))) < 0.01, `H ${a.H}`);
  for (const h of a.hazers) h.output = 50;          // a broken machine at fifty times full
  a.update(1 / 60);
  for (const h of RIG.hazers) assert.ok(a.densityAt(h.pos, 1) <= SIGMA_CAP + 1e-12);
  assert.equal(clampSigma(9), SIGMA_CAP);
  // Koschmieder: 0.26 /m is 15 m of visibility, 0.02 about 200 m, 0.003 about 1,300 m
  assert.ok(Math.abs(visibility(0.26) - 15.05) < 0.1 && Math.abs(visibility(0.02) - 195.6) < 0.1 && Math.abs(visibility(0.003) - 1304) < 1);
  // Henyey-Greenstein at g = 0.75: 30 degrees off the axis is 14.4 times side-on, head-on 125 times
  assert.ok(Math.abs(phaseHG(Math.cos(Math.PI / 6), 0.75) / phaseHG(0, 0.75) - 14.44) < 0.01);
  assert.ok(Math.abs(phaseHG(1, 0.75) / phaseHG(0, 0.75) - 125) < 0.01);
  // the noise texture: 32^3 bytes, and it uses its range
  const n = hazeNoise3D(32, 1);
  assert.equal(n.length, 32 ** 3);
  let lo = 255, hi = 0; for (const v of n) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  assert.ok(hi - lo > 100);
});
