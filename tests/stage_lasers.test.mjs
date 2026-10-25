// Virtual Stage v0: the laser brain and its 3D adapter (arsenal/web/stage/lasers.js, lasers3d.js).
// node --test tests/stage_lasers.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { HEADS, SEG, SEG_FLOATS, LaserEngine, laserPalette, isSaturatedRed, BANK_A, BANK_B, HERO, GATE_FLOOR } from "../arsenal/web/stage/lasers.js";
import { Lasers3D, L3, L3_FLOATS, projectorBasis, roomHit } from "../arsenal/web/stage/lasers3d.js";
import { expandScene } from "../arsenal/web/stage/rig.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v0.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const clock150 = { bpm: 150, posAt: (t) => t / 400, phaseAt: (t) => (t / 400) % 1, nextBeatAt: (t) => Math.ceil(t / 400) * 400, alive: () => true };

test("21 heads in Lasers v2's order: A1-A8 (truss), B1-B8 (floor), SL1 SL2 SR1 SR2, HERO", () => {
  assert.equal(HEADS.length, 21);
  assert.deepEqual(HEADS.map((h) => h.name), [...Array.from({ length: 8 }, (_, i) => `A${i + 1}`), ...Array.from({ length: 8 }, (_, i) => `B${i + 1}`),
    "SL1", "SL2", "SR1", "SR2", "HERO"]);
  assert.equal(BANK_A.length, 8); assert.equal(BANK_B.length, 8);
  // the scene's projectors are in the same order
  assert.deepEqual(RIG.projectors.map((p) => p.name), HEADS.map((h) => h.name));
});

test("red is never emitted: a saturated-red theme colour is swapped", () => {
  const pal = laserPalette(["#ff0000", "#19ff4a"]);
  assert.ok(!pal.some(isSaturatedRed));
  const eng = new LaserEngine({ clock: clock150, colours: ["#ff0000", "#ff1010", "#19ff4a"] });
  for (let k = 0; k < 12; k++) eng.hit(k * 1000 + 3, 0.9);
  for (let t = 0; t < 14000; t += 1000 / 60) {
    const o = eng.frame(t);
    for (let i = 0; i < o.n; i++) {
      const b = i * SEG_FLOATS;
      assert.ok(!isSaturatedRed([o.seg[b + SEG.R], o.seg[b + SEG.G], o.seg[b + SEG.B]]), "a red beam");
    }
  }
});

test("retrigger tiers by beats since the last press: more than a bar = burst, within a bar = one-two, within a beat = triple", () => {
  const eng = new LaserEngine({ clock: clock150 });
  const a = eng.hit(400 * 8, 0.9);             // beat 8
  const b = eng.hit(400 * 10, 0.9);            // 2 beats later
  const c = eng.hit(400 * 10.5, 0.9);          // half a beat later
  assert.equal(a.tier, "burst"); assert.equal(b.tier, "onetwo"); assert.equal(c.tier, "triple");
  // onsets sit on the quarter-beat grid
  for (const h of [a, b, c]) assert.equal(h.onset * 4, Math.round(h.onset * 4));
});

test("a burst lights on its onset and goes dark after its tail; a held pad becomes a gate", () => {
  const eng = new LaserEngine({ clock: clock150 });
  eng.hit(400 * 4, 1); eng.release(400 * 4 + 50);
  assert.ok(eng.frame(400 * 4 + 10).n > 0, "lit on the onset");
  assert.equal(eng.frame(400 * 5.2).n, 0, "dark after the tail");
  const g = new LaserEngine({ clock: clock150 });
  g.hit(400 * 8, 1);
  const lv = [];
  for (let t = 400 * 8; t < 400 * 11; t += 1000 / 60) { const o = g.frame(t); lv.push(Math.max(...o.heads)); }
  // a quarter-note gate: full and the gate floor (a lift, never black: the fan may fill the frame in 3D), more than once
  let edges = 0; for (let i = 1; i < lv.length; i++) if (Math.abs(lv[i] - lv[i - 1]) > 0.2) edges++;
  assert.ok(edges >= 4, `a held pad gates (${edges} edges)`);
  assert.ok(Math.min(...lv.slice(30)) >= GATE_FLOOR * 0.55 - 1e-9, "the gate's dark phase stays at the floor");
  g.release(400 * 11);
  assert.equal(g.frame(400 * 12.5).n, 0, "the gate stops after release and its tail");
  // presses closer than a quarter beat retrigger the current hit instead of starting new onsets
  const r = new LaserEngine({ clock: clock150 });
  const h1 = r.hit(400 * 20, 1), h2 = r.hit(400 * 20 + 40, 1);
  assert.equal(h1, h2);
  assert.equal(r.count, 1);
});

test("lasers3d at reach k = 0: seen from front of house, the 3D beams draw the brain's 2D picture (mean angle error < 3 deg)", () => {
  const eng = new LaserEngine({ clock: clock150 });
  eng.setLook("lattice", 1);
  for (let k = 0; k < 4; k++) eng.hit(400 * (8 + 6 * k), 0.9);
  const l3 = new Lasers3D(RIG.projectors, RIG.venue);
  const cam = [0, 12, 50];
  const proj = (p) => [(p[0] - cam[0]) / (cam[2] - p[2]), (p[1] - cam[1]) / (cam[2] - p[2])];   // a pinhole looking down -z
  let sum = 0, n = 0;
  for (const t of [400 * 8 + 20, 400 * 14 + 20, 400 * 20 + 20, 400 * 26 + 20]) {
    const o = eng.frame(t);
    const out = l3.map(o, { reachScale: 0 });
    for (let i = 0; i < out.n; i++) {
      const b = i * L3_FLOATS, s = out.seg;
      const h = s[b + L3.HEAD];
      // the 2D segment this 3D one came from: same head, in order (the adapter keeps the order and skips none here)
      const b2 = i * SEG_FLOATS;
      assert.equal(o.seg[b2 + SEG.HEAD], h);
      const a2 = Math.atan2(o.seg[b2 + SEG.Y1] - o.seg[b2 + SEG.Y0], o.seg[b2 + SEG.X1] - o.seg[b2 + SEG.X0]);
      const p0 = proj([s[b + L3.OX], s[b + L3.OY], s[b + L3.OZ]]);
      const mid = [s[b + L3.OX] + (s[b + L3.EX] - s[b + L3.OX]) * 0.05, s[b + L3.OY] + (s[b + L3.EY] - s[b + L3.OY]) * 0.05, s[b + L3.OZ] + (s[b + L3.EZ] - s[b + L3.OZ]) * 0.05];
      const p1 = proj(mid);
      const a3 = Math.atan2(p1[1] - p0[1], p1[0] - p0[0]);
      let d = Math.abs(a3 - a2); if (d > Math.PI) d = 2 * Math.PI - d;
      sum += (d * 180) / Math.PI; n++;
    }
  }
  assert.ok(n > 20, `${n} beams compared`);
  assert.ok(sum / n < 3, `mean angle error ${sum / n} deg`);
});

test("L2: a projector's power is shared among its beams (each share within 1 %), the sum never above what it has", () => {
  const eng = new LaserEngine({ clock: clock150 });
  eng.setLook("ceiling", 1, 8);
  eng.hit(400 * 8, 1);
  const l3 = new Lasers3D(RIG.projectors, RIG.venue);
  const o = eng.frame(400 * 8 + 30);
  const out = l3.map(o, { master: 1 });
  const sumI = new Map();
  for (let i = 0; i < o.n; i++) { const b = i * SEG_FLOATS; const h = o.seg[b + SEG.HEAD]; sumI.set(h, (sumI.get(h) || 0) + o.seg[b + SEG.I]); }
  for (let i = 0; i < out.n; i++) {
    const b = i * L3_FLOATS, h = out.seg[b + L3.HEAD];
    const expected = out.seg[b + L3.I] / sumI.get(h);
    assert.ok(Math.abs(l3.share[i] - expected) <= 0.01 * expected + 1e-12);
  }
  for (let h = 0; h < 21; h++) {
    const P = RIG.projectors[h].power_w;
    for (let c = 0; c < 3; c++) assert.ok(out.power[h * 3 + c] <= P[c] + 1e-9, `projector ${h} channel ${c}: ${out.power[h * 3 + c]} W`);
  }
});

test("camera exclusion: a beam aimed within 2 degrees of the camera is cut to 10 %", () => {
  const eng = new LaserEngine({ clock: clock150 });
  eng.hit(400 * 8, 1);
  const o = eng.frame(400 * 8 + 30);
  const l3 = new Lasers3D(RIG.projectors, RIG.venue);
  const free = l3.map(o, {});
  const first = { o: [free.seg[L3.OX], free.seg[L3.OY], free.seg[L3.OZ]], e: [free.seg[L3.EX], free.seg[L3.EY], free.seg[L3.EZ]], p: free.seg[L3.PG] + free.seg[L3.PR] + free.seg[L3.PB] };
  // put the camera on that beam, 20 m out
  const d = first.e.map((v, i) => v - first.o[i]); const L = Math.hypot(...d);
  const camPos = first.o.map((v, i) => v + (d[i] / L) * 20);
  const ex = l3.map(o, { camera: { pos: camPos, fwd: d.map((v) => -v / L), near: 0.1 } });
  assert.ok(ex.excluded >= 1);
  assert.ok(ex.seg[L3.FLAGS] & 2);
  const p = ex.seg[L3.PG] + ex.seg[L3.PR] + ex.seg[L3.PB];
  // cut to 10 % for pointing at the camera, and faded further for passing through it
  assert.ok(p <= first.p * 0.1 * (1 + 1e-6), `${p} vs ${first.p * 0.1}`);
  // a camera 2 m beside the beam (not on its axis): faded by its distance, (2 - 1) / 3
  const side = [first.o[0] + (d[0] / L) * 20 + 2 * (d[2] / Math.hypot(d[0], d[2])), first.o[1] + (d[1] / L) * 20, first.o[2] + (d[2] / L) * 20 - 2 * (d[0] / Math.hypot(d[0], d[2]))];
  const nr = l3.map(o, { camera: { pos: side, fwd: [0, 0, -1], near: 0.1 } });
  assert.ok(nr.near >= 1 && (nr.seg[L3.FLAGS] & 8));
  const pn = nr.seg[L3.PG] + nr.seg[L3.PR] + nr.seg[L3.PB];
  assert.ok(Math.abs(pn - first.p / 3) < 1e-3 * first.p, `${pn} vs ${first.p / 3}`);
});

test("the room ends every ray: the floor's crowd, the roof, a wall", () => {
  const v = RIG.venue;
  assert.equal(roomHit([0, 20, 10], [0, -1, 0], v).what, "crowd");
  assert.ok(Math.abs(roomHit([0, 20, 10], [0, -1, 0], v).t - (20 - 1.9)) < 1e-9);
  assert.equal(roomHit([0, 2.3, 0.3], [0, 1, 0], v).what, "roof");
  assert.equal(roomHit([0, 10, 0], [1, 0, 0], v).what, "wall");
  const b = projectorBasis([0, 0, 1]);
  assert.deepEqual(b.r, [1, 0, 0]); assert.deepEqual(b.u, [0, 1, 0]);
  void HERO;
});
