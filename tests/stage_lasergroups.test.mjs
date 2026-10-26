// Virtual Stage v1: laser groups and their effects (arsenal/web/stage/lasers.js group lines, lasers3d.js aim overrides).
// node --test tests/stage_lasergroups.test.mjs
//
// Daniel, 2026-10-24: "give myself the ability to tie groups of lasers together and allow them to play various
// "animations" and triggers". The output contract stays Lasers v2's: 16-float segments in the picture frame.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { LaserEngine, extraHeadsFrom, groupGate, levelPhases, GROUP_SHAPES, GATE_FLOOR, HEADS, SEG, SEG_FLOATS, isSaturatedRed, PICTURE }
  from "../arsenal/web/stage/lasers.js";
import { Lasers3D, L3, L3_FLOATS } from "../arsenal/web/stage/lasers3d.js";
import { compileRepeat, resolveMods } from "../arsenal/web/stage/phrases.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const clock = (pos) => ({ bpm: 150, conf: 1, posAt: () => pos.v, phaseAt: () => pos.v % 1, nextBeatAt: () => 0, alive: () => true });
function engine() {
  const pos = { v: 0 };
  const e = new LaserEngine({ seed: 7, clock: clock(pos), colours: SCENE.themes["source-violet"].laser, heads: extraHeadsFrom(RIG.projectors) });
  return { e, pos };
}
const line = (group, laser) => ({ group, kind: "lasers", heads: RIG.laserGroups[group].heads.slice(), laser });
const headsOf = (o) => { const s = new Set(); for (let i = 0; i < o.n; i++) s.add(o.seg[i * SEG_FLOATS + SEG.HEAD]); return s; };

test("the brain keeps the 21 Lasers v2 heads at 0..20 and places the halo's twelve where front of house sees them", () => {
  const { e } = engine();
  assert.equal(e.heads.length, 33);
  for (let i = 0; i < 21; i++) assert.equal(e.heads[i], HEADS[i]);
  // the picture map puts Bank A's truss and Bank B's floor where Lasers v2 has them
  const A1 = RIG.projectors[0], B1 = RIG.projectors[8];
  assert.ok(Math.abs(A1.pos[0] * PICTURE.sx_per_m - HEADS[0].sx) < 1e-6 && Math.abs((A1.pos[1] - PICTURE.y0_m) * PICTURE.y_per_m - HEADS[0].y) < 1e-6);
  assert.ok(Math.abs((B1.pos[1] - PICTURE.y0_m) * PICTURE.y_per_m - HEADS[8].y) < 0.01);
  const R1 = e.heads[21];
  assert.equal(R1.name, "R1"); assert.equal(R1.level, 0);
  assert.ok(R1.y > 0.4, "a top-third halo laser sits high in the picture");
});

test("group gates: the one-two and the triple dip to the gate floor, never to black", () => {
  const sample = (g) => Array.from({ length: 16 }, (_, i) => groupGate(g, i / 16));
  assert.deepEqual(sample("none"), Array(16).fill(1));
  const ot = sample("onetwo");
  assert.equal(ot.filter((v) => v === 1).length, 8); assert.ok(ot.every((v) => v === 1 || v === GATE_FLOOR));
  const tr = sample("triple");
  assert.equal(tr.filter((v) => v === 1).length, 6); assert.ok(tr.every((v) => v === 1 || v === GATE_FLOOR));
  assert.throws(() => groupGate("strobe", 0));
});

test("every shape draws only from its group's heads, in the Lasers v2 segment layout, never in saturated red", () => {
  for (const shape of GROUP_SHAPES) {
    const { e, pos } = engine();
    const group = shape === "levels" || shape === "rim-corona" ? "halo.lasers" : shape === "tunnel" ? "lasers.hero" : "lasers.core";
    const extra = shape === "rim-corona" ? { followDef: RIG.effects["ring-chopper"] } : shape === "levels" ? { scheduleDef: RIG.effects["levels-step"] } : {};
    e.setLookMute(true);
    e.setGroupLines([line(group, { shape, level: 0.8, colour: 0, ...extra })], 0);
    let drew = 0;
    for (let k = 0; k < 24; k++) {
      pos.v = k / 8;
      const o = e.frame(0);
      drew += o.n;
      for (const h of headsOf(o)) assert.ok(RIG.laserGroups[group].heads.includes(h), `${shape}: head ${h} is not in ${group}`);
      for (let i = 0; i < o.n; i++) {
        const b = i * SEG_FLOATS;
        assert.ok(!isSaturatedRed([o.seg[b + SEG.R], o.seg[b + SEG.G], o.seg[b + SEG.B]]));
        assert.ok(o.seg[b + SEG.I] > 0 && o.seg[b + SEG.I] <= 1 + 1e-9);
      }
    }
    assert.ok(drew > 0, `${shape} draws`);
  }
});

test("chase runs across the bank in x order, one head at a time; bloom opens over its beats; from/until bound a line", () => {
  const { e, pos } = engine();
  e.setGroupLines([line("lasers.B", { shape: "chase", measure: 2, beams: 1 })], 0);
  const order = [];
  for (let k = 0; k < 8; k++) { pos.v = k * 0.25 + 0.01; order.push([...headsOf(e.frame(0))]); }
  assert.ok(order.every((h) => h.length === 1));
  assert.deepEqual(order.map((h) => h[0]), RIG.laserGroups["lasers.B"].heads);
  const spread = (o) => { let lo = Infinity, hi = -Infinity; for (let i = 0; i < o.n; i++) { const b = i * SEG_FLOATS; if (o.seg[b + SEG.HEAD] !== 8) continue; const a = Math.atan2(o.seg[b + SEG.Y1] - o.seg[b + SEG.Y0], o.seg[b + SEG.X1] - o.seg[b + SEG.X0]); lo = Math.min(lo, a); hi = Math.max(hi, a); } return hi - lo; };
  e.setGroupLines([line("lasers.B", { shape: "bloom", open_beats: 1, until_beats: 2 })], 10);
  pos.v = 10; const s0 = spread(e.frame(0)); pos.v = 10.5; const s1 = spread(e.frame(0)); pos.v = 11; const s2 = spread(e.frame(0));
  assert.ok(s0 < s1 && s1 < s2, `the bloom opens: ${s0.toFixed(3)} < ${s1.toFixed(3)} < ${s2.toFixed(3)}`);
  pos.v = 12; assert.equal(e.frame(0).groups, 0, "until_beats ends the line");
  e.setGroupLines([line("lasers.B", { shape: "ceiling", from_beats: 2 })], 20);
  pos.v = 21.9; assert.equal(e.frame(0).groups, 0); pos.v = 22; assert.ok(e.frame(0).groups > 0, "from_beats starts it on its beat");
});

test("the halo lasers fire with their third on the phrase's schedule, aimed at their layer out over the crowd (the aim side channel)", () => {
  const mods = resolveMods(SCENE.phrases["halo-levels"].vary.per_repeat, 0, 1);
  const rep = compileRepeat(RIG, "halo-levels", "daniel", { ...mods, layer_shift: 0 });
  const las = rep.steps[0].lines.find((l) => l.kind === "lasers");
  const { e, pos } = engine();
  e.setGroupLines([las], 0);
  const l3 = new Lasers3D(RIG.projectors, RIG.venue, { heads: e.heads });
  const ph = levelPhases(las.laser.scheduleDef);
  assert.deepEqual(ph.map((v) => +v.toFixed(4)), [0, -0.3333, -0.6667]);
  const layerY = [26, 15, 8];
  for (let beat = 0; beat < 6; beat++) {
    pos.v = beat + 0.5;
    const o = e.frame(0);
    const lit = [...headsOf(o)];
    const want = beat % 3;
    assert.ok(lit.length === 4 && lit.every((h) => e.heads[h].level === want), `beat ${beat}: third ${want} (${lit.map((h) => e.heads[h].level)})`);
    for (const h of lit) assert.ok(o.aim[h * 4 + 3] > 0, "an aim override for each lit halo laser");
    const o3 = l3.map(o, { camera: null });
    for (let i = 0; i < o3.n; i++) {
      const b = i * L3_FLOATS;
      const dx = o3.seg[b + L3.EX] - o3.seg[b + L3.OX], dy = o3.seg[b + L3.EY] - o3.seg[b + L3.OY], dz = o3.seg[b + L3.EZ] - o3.seg[b + L3.OZ];
      assert.ok(dz > 0, "out over the crowd");
      const t30 = (30 - o3.seg[b + L3.OZ]) / dz;
      const y30 = o3.seg[b + L3.OY] + dy * t30;
      assert.ok(Math.abs(y30 - layerY[want]) < 8, `a third-${want} beam crosses z 30 at y ${y30.toFixed(1)} (layer ${layerY[want]})`);
    }
  }
});

test("rim-corona: one spoke per halo laser, lit as the chopper blade passes it (two blades: each spoke twice a turn)", () => {
  const { e, pos } = engine();
  e.setGroupLines([line("halo.lasers", { shape: "rim-corona", followDef: RIG.effects["ring-chopper"], level: 0.8 })], 0);
  const litCount = new Map();
  let frames = 0;
  for (let k = 0; k < 96; k++) {
    pos.v = k / 96;                              // one beat = one turn of the blades
    const o = e.frame(0);
    frames++;
    for (const h of headsOf(o)) litCount.set(h, (litCount.get(h) || 0) + 1);
    for (const h of headsOf(o)) assert.ok(o.aim[h * 4 + 3] > 0);
  }
  assert.equal(litCount.size, 12, "every spoke lights during a turn");
  for (const [h, n] of litCount) { const share = n / frames; assert.ok(share > 0.3 && share < 0.95, `spoke ${h} lit ${(share * 100).toFixed(0)} % of the turn`); }
});

test("Lasers3D: the aim override replaces the projector's aim and depth ratio for that head only", () => {
  const { e, pos } = engine();
  const l3 = new Lasers3D(RIG.projectors, RIG.venue, { heads: e.heads });
  e.setGroupLines([line("lasers.B", { shape: "fan", beams: 1 })], 0);
  pos.v = 0;
  const o = e.frame(0);
  const before = l3.map(o, {});
  const firstB = RIG.laserGroups["lasers.B"].heads[0];
  const dirOf = (out, h) => { for (let i = 0; i < out.n; i++) { const b = i * L3_FLOATS; if (out.seg[b + L3.HEAD] === h) { const d = [out.seg[b + L3.EX] - out.seg[b + L3.OX], out.seg[b + L3.EY] - out.seg[b + L3.OY], out.seg[b + L3.EZ] - out.seg[b + L3.OZ]]; const l = Math.hypot(...d); return d.map((v) => v / l); } } return null; };
  const d0 = dirOf(before, firstB);
  o.aim.set([-1, 0, 0, 50], firstB * 4);        // straight house left, almost no deviation
  const after = l3.map(o, {});
  const d1 = dirOf(after, firstB);
  assert.ok(d1[0] < -0.99, `aimed house left: ${d1.map((v) => v.toFixed(3))}`);
  assert.ok(Math.abs(d0[0] - d1[0]) > 0.3, "it changed");
  const other = RIG.laserGroups["lasers.B"].heads[1];
  assert.deepEqual(dirOf(after, other), dirOf(before, other), "the other heads keep their own aim");
});
