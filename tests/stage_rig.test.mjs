// Virtual Stage v0: the rig model (arsenal/web/stage/rig.js). node --test tests/stage_rig.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SCENE_FORMAT, MVR_TO_STAGE, det3, mvrToStage, stageToMvr, validateScene, expandScene, headPose, elementMatrix,
         eulerToMat3, mat3MulVec, ringTiltWindow, ringEnvelope, annulusOf, annulusGap, mountPose } from "../arsenal/web/stage/rig.js";
import { roomHit } from "../arsenal/web/stage/lasers3d.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v0.json", import.meta.url), "utf8"));
const clone = (o) => JSON.parse(JSON.stringify(o));
const close = (a, b, eps = 1e-9, msg = "") => assert.ok(Math.abs(a - b) <= eps, `${msg} ${a} != ${b}`);

test("the shipped scene is valid", () => {
  assert.equal(SCENE.format, SCENE_FORMAT);
  assert.deepEqual(validateScene(SCENE), []);
});

test("expansion counts: 12 rungs, 28 heads, 24 cubes, the strips, the rings, 21 projectors, 8 hazers", () => {
  const rig = expandScene(SCENE);
  const c = rig.counts;
  assert.equal(c.rungs, 12);
  assert.equal(c.heads, 28, "12 under the rungs, 8 on the overhead truss, 8 on the lip");
  assert.equal(c.by_type["beam-7r"], 28);
  assert.equal(c.cubes, 24);
  assert.equal(c.cube_cells, 24 * 6);
  assert.equal(c.dot_cells, 12 * 2 * 12);
  assert.equal(c.bar_cells, 12 * 2 * 32);
  assert.equal(c.rings, 4);
  // slats: 4 rings x 48 x 8; rims: one cell per 0.25 m round both edges of each ring
  let rims = 0;
  for (const [d, depth] of [[28, 2.5], [20, 2.2], [13, 2.0], [6, 1.5]]) {
    for (const r of [d / 2, d / 2 - depth]) rims += Math.max(8, Math.round((2 * Math.PI * r) / 0.25));
  }
  assert.equal(c.ring_cells, 4 * 48 * 8 + rims);
  assert.equal(c.projectors, 21);
  assert.equal(c.hazers, 8);
  assert.equal(c.hoists, 24, "two pickups per rung");
});

test("expansion is deterministic", () => {
  const a = expandScene(SCENE), b = expandScene(clone(SCENE));
  assert.deepEqual(Array.from(a.cells.pos), Array.from(b.cells.pos));
  assert.deepEqual(a.fixtures.map((f) => f.key), b.fixtures.map((f) => f.key));
  assert.deepEqual(Array.from(a.groups["strand.cubes"].keys.helix), Array.from(b.groups["strand.cubes"].keys.helix));
});

test("the MVR bridge is a proper rotation and round-trips; MVR upstage (+Y) is our -z", () => {
  assert.equal(det3(MVR_TO_STAGE), 1);
  for (const p of [[1000, 2000, 3000], [-4300, 15000, 20000], [0, 0, 0]]) {
    const q = stageToMvr(mvrToStage(p));
    p.forEach((v, i) => close(q[i], v, 1e-9));
  }
  assert.deepEqual(mvrToStage([0, 1000, 0]).map((v) => v + 0), [0, 0, -1]);
  assert.deepEqual(mvrToStage([0, 0, 1000]).map((v) => v + 0), [0, 1, 0]);
});

test("broken scenes are caught with a reason", () => {
  const s1 = clone(SCENE); s1.format = "arsenal.arena/v0";
  assert.ok(validateScene(s1).some((e) => e.startsWith("format")));
  const s2 = clone(SCENE); s2.objects[0].children[0].type = "nope";
  assert.ok(validateScene(s2).some((e) => e.includes("unknown type")));
  const s3 = clone(SCENE); s3.objects[0].repeat.count = 0;
  assert.ok(validateScene(s3).some((e) => e.includes("count")));
  const s4 = clone(SCENE); s4.objects.push(clone(s4.objects[0]));
  assert.ok(validateScene(s4).some((e) => e.includes("duplicate")));
  const s5 = clone(SCENE); s5.types["beam-7r"].attrs.Pan.real_fade = 0;
  assert.ok(validateScene(s5).some((e) => e.includes("real_fade")));
  const s6 = clone(SCENE); s6.objects[3].repeat.values.tilt = [1, 2];
  assert.ok(validateScene(s6).some((e) => e.includes("one value per instance")));
  assert.throws(() => expandScene(s1));
});

test("head pose: hung points down, upright points up, tilt leans toward the audience", () => {
  const rig = expandScene(SCENE);
  const hung = rig.fixtures[rig.heads[0]];                   // under rung 0
  const lip = rig.fixtures.find((f) => f.type === "beam-7r" && rig.elements[f.element].id === "lip");
  const out = { lens: [0, 0, 0], dir: [0, 0, 0] };
  headPose(elementMatrix(rig.elements[hung.element]), hung, 0, 0, out);
  close(out.dir[1], -1, 1e-9, "hung dir y");
  assert.ok(out.lens[1] < 20 - 0.6, "the lens hangs below the rung");
  headPose(elementMatrix(rig.elements[lip.element]), lip, 0, 0, out);
  close(out.dir[1], 1, 1e-9, "upright dir y");
  headPose(elementMatrix(rig.elements[lip.element]), lip, 0, 90, out);
  close(out.dir[2], 1, 1e-9, "tilt 90 points out over the crowd");
  headPose(elementMatrix(rig.elements[lip.element]), lip, 90, 90, out);
  close(out.dir[0], 1, 1e-9, "pan 90 + tilt 90 points house right");
});

test("a rolled rung carries its children: roll +30 lifts the house-right cube", () => {
  const rig = expandScene(SCENE);
  const el = rig.elements.find((e) => e.id === "rung");
  const m = elementMatrix(el, { y: 15, roll: 30 });
  const right = [m[0] * 4.5 + m[9], m[3] * 4.5 + m[10]];
  close(right[1], 15 + 4.5 * Math.sin(Math.PI / 6), 1e-9);
  assert.ok(right[0] > 0);
});

test("groups and their order keys", () => {
  const rig = expandScene(SCENE);
  const g = rig.groups["strand.heads"];
  assert.equal(g.kind, "heads");
  assert.equal(g.n, 12);
  // world z increases with the rung index
  for (let i = 1; i < 12; i++) assert.ok(g.keys.z[i] > g.keys.z[i - 1]);
  const cubes = rig.groups["strand.cubes"];
  assert.equal(cubes.kind, "cells");
  assert.equal(cubes.n, 144);
  // helix: the left backbone (x < 0) sorts before the right one
  const left = [], right = [];
  for (let i = 0; i < cubes.n; i++) (cubes.keys.side[i] < 0 ? left : right).push(cubes.keys.helix[i]);
  assert.ok(Math.max(...left) < Math.min(...right));
  assert.equal(rig.groups["truss.heads"].n, 8);
  assert.equal(rig.groups["lip.heads"].n, 8);
  assert.equal(rig.groups["rings.slats"].n, 4 * 48 * 8);
});

test("euler matrices are rotations (columns orthonormal, det +1)", () => {
  for (const r of [[180, 0, 0], [12, -40, 77], [0, 90, 0]]) {
    const m = eulerToMat3(r);
    const mm = [[m[0], m[1], m[2]], [m[3], m[4], m[5]], [m[6], m[7], m[8]]];
    close(det3(mm), 1, 1e-12);
    const v = mat3MulVec(m, [0, 1, 0]);
    close(Math.hypot(...v), 1, 1e-12);
  }
});

// ------------------------------------------------------------------------------------- v2: kinetics wave A --
const V1 = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG1 = expandScene(V1);
const RINGS1 = RIG1.elements.filter((e) => e.id === "ring");

test("elementMatrix v2: yaw, spin and axial travel; at zero the v1 matrix, number for number", () => {
  const el = RINGS1[0];
  const a = elementMatrix(el, { tilt: 55 }), b = elementMatrix(el, { tilt: 55, yaw: 0, spin: 0, axial: 0 });
  assert.deepEqual(Array.from(a), Array.from(b));
  // spin turns the ring about its own normal: the normal stays, a point on the rim moves round it
  const s = elementMatrix(el, { tilt: 55, spin: 90 });
  for (const k of [2, 5, 8]) close(s[k], a[k], 1e-12);
  for (const k of [0, 3, 6]) close(s[k], a[k + 1], 1e-12, "a quarter spin: local +x now lies where local +y was");
  // yaw turns the tilted ring about the world vertical through its centre: the normal's height stays
  const y = elementMatrix(el, { tilt: 55, yaw: 90 });
  close(y[5], a[5], 1e-12); close(Math.hypot(y[2], y[8]), Math.hypot(a[2], a[8]), 1e-12); close(y[8], 0, 1e-12);
  // axial: the centre moves along the face normal
  const t = elementMatrix(el, { tilt: 55, axial: 3 });
  close(t[9] - a[9], 3 * a[2], 1e-12); close(t[10] - a[10], 3 * a[5], 1e-12); close(t[11] - a[11], 3 * a[8], 1e-12);
  for (const m of [s, y, t]) close(det3([[m[0], m[1], m[2]], [m[3], m[4], m[5]], [m[6], m[7], m[8]]]), 1, 1e-12);
});

test("the rings' legal tilt windows at their hang (the orrery report): R0 only 47.5..63, R1 from 18; lifted 4.5 m R0 stands upright", () => {
  assert.deepEqual(ringTiltWindow(RINGS1[0], 14, RIG1.venue), [47.5, 63]);
  const w1 = ringTiltWindow(RINGS1[1], 14, RIG1.venue);
  assert.ok(w1[0] >= 18 && w1[0] <= 18.5 && w1[1] === 90, JSON.stringify(w1));
  assert.deepEqual(ringTiltWindow(RINGS1[2], 14, RIG1.venue), [0, 90]);
  assert.equal(ringTiltWindow(RINGS1[0], 18.5, RIG1.venue)[0], 0);
  // home is legal with a metre to the back wall; tilt 0 at the hang puts R0's rim through the deck
  const home = ringEnvelope(RINGS1[0], { tilt: 55 }, RIG1.venue);
  assert.ok(home.ok && home.why === "back wall" && home.margin > 1 && home.margin < 1.1);
  const flat = ringEnvelope(RINGS1[0], { tilt: 0 }, RIG1.venue);
  assert.ok(!flat.ok && flat.why === "deck", JSON.stringify(flat));
});

test("nested rings: concentric shells never touch at any tilt; stepped up a shared axis they keep their spacing", () => {
  const ann = (k, pose) => annulusOf(RINGS1[k], pose);
  for (const [t0, t1] of [[55, 40], [55, 90], [10, 80], [30, 0]]) {
    const g = annulusGap(ann(0, { tilt: t0, yaw: 37 }), ann(1, { tilt: t1, spin: 12 }));
    assert.ok(g >= 1.0, `R0 at ${t0}, R1 at ${t1}: ${g.toFixed(2)} m`);
  }
  const g2 = annulusGap(ann(1, { tilt: 55, axial: 3 }), ann(2, { tilt: 55, axial: 6 }));
  assert.ok(g2 > 2.5 && g2 < 3, `${g2}`);
  // and the check sees a collision: two rings of one radius on one centre at different tilts cross each other
  assert.ok(annulusGap(ann(1, { tilt: 55 }), ann(1, { tilt: 0 })) < 1e-9);
});

test("a ring-mounted laser keeps its mount in the ring's frame: at home its pose is v1's, on a live ring it rides along", () => {
  const p = RIG1.projectors.find((x) => x.mount);
  const el = RIG1.elements[p.element];
  const home = mountPose(elementMatrix(el), p.mount);
  for (let k = 0; k < 3; k++) { close(home.pos[k], p.pos[k], 1e-12); close(home.radial[k], p.radial[k], 1e-12); close(home.normal[k], p.normal[k], 1e-12); }
  const spun = mountPose(elementMatrix(el, { tilt: 55, spin: 180 }), p.mount);
  const c = [el.origin[0], el.home.y, el.origin[2]];
  for (let k = 0; k < 3; k++) close(spun.pos[k] - c[k], -(home.pos[k] - c[k]), 1e-9, "half a turn puts it opposite");
});

test("the hit check knows the audience stands: a side or back hit below their top row is 'stands', never a wall", () => {
  const v = RIG1.venue;
  assert.equal(roomHit([0, 10, 0], [1, 0, 0], v).what, "wall", "the legacy box (the renderer's beam lengths) is unchanged");
  const s = roomHit([0, 10, 0], [1, 0, 0], v, { stands: true });
  assert.equal(s.what, "stands");
  close(s.t, 38 + 10 / Math.tan(30 * Math.PI / 180), 1e-9, "the raked seats 17.3 m out from the floor's edge at 10 m up");
  assert.equal(roomHit([0, 10, 50], [0, 0, 1], v, { stands: true }).what, "stands", "the back stand");
  assert.equal(roomHit([0, 20, -8], [0, 0, -1], v, { stands: true }).what, "backwall");
  assert.equal(roomHit([0, 20, 0], [0.05, 1, 0.1], v, { stands: true }).what, "roof");
  assert.equal(roomHit([0, 20, 0], [0, -1, 0.2], v, { stands: true }).what, "crowd");
  // the core stops a beam aimed into it (a ray from inside does not stop)
  const o = roomHit([0, 22, -22], [0, -8 / Math.hypot(8, 11), 11 / Math.hypot(8, 11)], v, { orb: { c: [0, 14, -11], r: 0.85 } });
  assert.equal(o.what, "orb"); close(o.t, Math.hypot(8, 11) - 0.85, 1e-9);
  assert.notEqual(roomHit([0, 14, -11], [0, 1, 0], v, { orb: { c: [0, 14, -11], r: 0.85 } }).what, "orb");
});
