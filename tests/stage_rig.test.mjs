// Virtual Stage v0: the rig model (arsenal/web/stage/rig.js). node --test tests/stage_rig.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SCENE_FORMAT, MVR_TO_STAGE, det3, mvrToStage, stageToMvr, validateScene, expandScene, headPose, elementMatrix,
         eulerToMat3, mat3MulVec } from "../arsenal/web/stage/rig.js";

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
