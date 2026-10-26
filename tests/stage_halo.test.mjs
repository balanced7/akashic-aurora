// Virtual Stage v1: the halo and the verticals in the rig model (arsenal/web/stage/rig.js, sets/source-v1.json).
// node --test tests/stage_halo.test.mjs
//
// Daniel, 2026-10-25: "the three levels seems to be altitudes on the circular array where they group the lasers into
// thirds". The study lane's spec places 48 heads (16 per third) on rings 0-2 and 12 lasers on ring 0.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { validateScene, expandScene, elementMatrix, headPose, aimAt, clockOf, levelOf, clusterRank, buildLaserGroups }
  from "../arsenal/web/stage/rig.js";
import { resolvePreset, presetDirection } from "../arsenal/web/stage/phrases.js";
import { roomHit } from "../arsenal/web/stage/lasers3d.js";
import { clearanceToRungs } from "../arsenal/web/stage/camera.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const V0 = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v0.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const close = (a, b, eps, msg = "") => assert.ok(Math.abs(a - b) <= eps, `${msg} ${a} != ${b} (eps ${eps})`);

test("the v1 set is valid and v0 still expands unchanged (28 heads, 21 projectors)", () => {
  assert.deepEqual(validateScene(SCENE), []);
  const v0 = expandScene(V0);
  assert.equal(v0.counts.heads, 28);
  assert.equal(v0.counts.projectors, 21);
  assert.equal(RIG.counts.heads, 128);
  assert.equal(RIG.counts.projectors, 33);
});

test("clock angle and level: 0 at the top, clockwise from front of house; thirds by the ring-local angle", () => {
  close(clockOf(Math.PI / 2), 0, 1e-9, "top");
  close(clockOf(0), 90, 1e-9, "house right is 3 o'clock");
  close(clockOf(Math.PI), -90, 1e-9, "house left is 9 o'clock");
  close(Math.abs(clockOf(-Math.PI / 2)), 180, 1e-9, "bottom");
  assert.equal(levelOf(59.9), 0); assert.equal(levelOf(-59.9), 0);
  assert.equal(levelOf(60), 1); assert.equal(levelOf(120), 1); assert.equal(levelOf(-100), 1);
  assert.equal(levelOf(120.1), 2); assert.equal(levelOf(180), 2);
});

test("the halo: 24 / 16 / 8 heads on rings 0, 1, 2 (ring parameters name the polar count, start and step), 16 per third", () => {
  const per = ["halo.r0", "halo.r1", "halo.r2"].map((g) => RIG.groups[g].n);
  assert.deepEqual(per, [24, 16, 8]);
  for (const t of ["halo.top", "halo.mid", "halo.bot"]) assert.equal(RIG.groups[t].n, 16, t);
  // per ring per third: ring 0 8/8/8, ring 1 6/4/6, ring 2 2/4/2
  const tally = {};
  const g = RIG.groups.halo;
  for (let m = 0; m < g.n; m++) { const k = `${g.keys.element[m]}:${g.keys.level[m]}`; tally[k] = (tally[k] || 0) + 1; }
  assert.deepEqual(tally, { "0:0": 8, "0:1": 8, "0:2": 8, "1:0": 6, "1:1": 4, "1:2": 6, "2:0": 2, "2:1": 4, "2:2": 2 });
  assert.equal(RIG.groups["halo.tb"].n, 32, "top and bottom together");
});

test("halo positions match the spec at the v0 tilts (x = r sin(clock), y = 14 + r cos(clock) cos(tilt), z = -11 - r cos(clock) sin(tilt))", () => {
  const g = RIG.groups["halo.r0"];
  const want = { 7.5: [1.83, 21.96, -22.37], 67.5: [12.93, 17.07, -15.39], 172.5: [1.83, 6.04, 0.37] };
  for (const [clock, xyz] of Object.entries(want)) {
    const m = Array.from(g.keys.clock).findIndex((c) => Math.abs(c - Number(clock)) < 1e-6);
    assert.ok(m >= 0, `a head at clock ${clock}`);
    for (let k = 0; k < 3; k++) close(g.world[m][k], xyz[k], 0.01, `clock ${clock} axis ${k}`);
  }
  // heights by third (ring 0: top 18.9-22.0, middle 10.9-17.1, bottom 6.0-9.1)
  const r0 = RIG.groups["halo.r0"];
  const ys = [[], [], []];
  for (let m = 0; m < r0.n; m++) ys[r0.keys.level[m]].push(r0.world[m][1]);
  close(Math.min(...ys[0]), 18.89, 0.02); close(Math.max(...ys[0]), 21.96, 0.02);
  close(Math.min(...ys[1]), 10.93, 0.02); close(Math.max(...ys[1]), 17.07, 0.02);
  close(Math.min(...ys[2]), 6.04, 0.02); close(Math.max(...ys[2]), 9.11, 0.02);
});

test("a tilt never moves a head between thirds (the level is the ring-local angle)", () => {
  const s = JSON.parse(JSON.stringify(SCENE));
  s.objects.find((o) => o.id === "ring").repeat.values.tilt = [80, 70, 60, 50];
  const r = expandScene(s);
  for (const t of ["halo.top", "halo.mid", "halo.bot"]) assert.deepEqual(Array.from(r.groups[t].members), Array.from(RIG.groups[t].members), t);
});

test("halo heads stand on the ring face: at pan 0 / tilt 0 the beam leaves along the ring's face normal", () => {
  const g = RIG.groups.halo;
  const f = RIG.fixtures[g.memberFixture[0]], el = RIG.elements[f.element];
  const out = { lens: [0, 0, 0], dir: [0, 0, 0] };
  headPose(elementMatrix(el), f, 0, 0, out);
  const t = el.params.tilt * Math.PI / 180;
  close(out.dir[0], 0, 1e-9); close(out.dir[1], Math.sin(t), 1e-9); close(out.dir[2], Math.cos(t), 1e-9);
});

test("the verticals: V1 pods at x +-5, V2 at +-13, V3 = the +-22 pods and towers; columns and depth rows rank outward", () => {
  const v = RIG.groups.vert;
  assert.equal(v.n, 20);
  for (let m = 0; m < v.n; m++) {
    const ax = Math.abs(v.keys.x[m]);
    const want = ax < 8 ? 0 : ax < 17 ? 1 : 2;
    assert.equal(v.keys.column[m], want, `column of x ${v.keys.x[m]}`);
  }
  const d = RIG.groups["vert.depth"];
  assert.equal(d.n, 24);
  for (let m = 0; m < d.n; m++) assert.equal(d.keys.depth[m], d.keys.z[m] < 10 ? 0 : d.keys.z[m] < 40 ? 1 : 2);
  assert.equal(RIG.groups["vert.strips"].n, 24 * 4 + 64 * 2);
  assert.deepEqual([...new Set(RIG.groups["vert.strips"].keys.column)].sort(), [0, 1, 2]);
  // the lip row: 24 heads 2 m apart at y 2.2, z 0.6
  const h = RIG.groups.hrow;
  assert.equal(h.n, 24);
  close(h.keys.x[0], -23, 1e-9); close(h.keys.x[23], 23, 1e-9); close(h.keys.y[5], 2.2, 1e-9); close(h.keys.z[5], 0.6, 1e-9);
});

test("groups: where filters and unions of one kind; a union of heads and cells is refused; an unknown union name is invalid", () => {
  assert.equal(RIG.groups["heads.all"].n, 128);
  assert.equal(RIG.groups["leds.all"].n, RIG.counts.cells);
  const s = JSON.parse(JSON.stringify(SCENE));
  s.groups.bad = { union: ["halo", "rings.slats"] };
  assert.throws(() => expandScene(s), /mixes/);
  const s2 = JSON.parse(JSON.stringify(SCENE));
  s2.groups = { bad: { union: ["nope"] }, ...s2.groups };
  assert.ok(validateScene(s2).some((e) => e.includes("not a group defined above")));
  const s3 = JSON.parse(JSON.stringify(SCENE));
  s3.groups["halo.top"].where = { colour: 1 };
  assert.ok(validateScene(s3).some((e) => e.includes("where.colour")));
  // ring slats by third
  const thirds = ["rings.slats.top", "rings.slats.mid", "rings.slats.bot"].map((g) => RIG.groups[g].n);
  assert.equal(thirds.reduce((a, b) => a + b, 0), RIG.groups["rings.slats"].n);
});

test("clusterRank groups near-equal values", () => {
  assert.deepEqual(Array.from(clusterRank([5.3, 4.7, 13.1, 22, 21.6, 12.7], 2)), [0, 0, 1, 2, 2, 1]);
});

test("the halo lasers: twelve mounted on ring 0 at the spec's points, four per third, with their mount's radial and normal", () => {
  const R = RIG.projectors.filter((p) => p.bank === "R");
  assert.equal(R.length, 12);
  const want = [[3.62, 21.76, -22.08], [9.90, 19.68, -19.11], [13.52, 16.08, -13.97], [13.52, 11.92, -8.03], [9.90, 8.32, -2.89], [3.62, 6.24, 0.08]];
  for (const w of want) for (const sx of [1, -1]) {
    const p = R.find((q) => Math.abs(q.pos[0] - sx * w[0]) < 0.01 && Math.abs(q.pos[1] - w[1]) < 0.01);
    assert.ok(p, `a laser at ${sx * w[0]}, ${w[1]}`);
    close(p.pos[2], w[2], 0.01);
    close(Math.hypot(...p.radial), 1, 1e-9); close(Math.hypot(...p.normal), 1, 1e-9);
  }
  const by = [0, 1, 2].map((l) => R.filter((p) => p.level === l).length);
  assert.deepEqual(by, [4, 4, 4]);
  const lg = RIG.laserGroups;
  assert.equal(lg["halo.lasers.top"].n, 4); assert.equal(lg["halo.lasers.tb"].n, 8);
  assert.equal(lg["lasers.A"].n, 8); assert.equal(lg["lasers"].n, 21); assert.equal(lg["lasers.all"].n, 33);
  // a chase across a bank runs house left to house right
  const xs = lg["lasers.B"].heads.map((i) => RIG.projectors[i].pos[0]);
  assert.deepEqual(xs, [...xs].sort((a, b) => a - b));
  assert.deepEqual(buildLaserGroups(RIG.projectors, { x: { banks: ["Q"] } }).x.n, 0);
});

test("aimAt inverts headPose: the beam points at the asked world point (upright, hung and ring-face heads)", () => {
  const out = { lens: [0, 0, 0], dir: [0, 0, 0] };
  const picks = [RIG.groups.hrow.memberFixture[3], RIG.groups["vert.v1"].memberFixture[0], RIG.groups["halo.top"].memberFixture[2],
                 RIG.groups["halo.bot"].memberFixture[5], RIG.groups["halo.mid"].memberFixture[1]];
  for (const fi of picks) {
    const f = RIG.fixtures[fi], em = elementMatrix(RIG.elements[f.element]);
    for (const target of [[10, 20, 30], [-8, 9, 40], [0, 30, 10]]) {
      const r = aimAt(em, f, target);
      if (r.clamped) continue;
      headPose(em, f, r.pan, r.tilt, out);
      const d = [target[0] - out.lens[0], target[1] - out.lens[1], target[2] - out.lens[2]], l = Math.hypot(...d);
      const cos = (d[0] * out.dir[0] + d[1] * out.dir[1] + d[2] * out.dir[2]) / l;
      assert.ok(cos > Math.cos(0.6 * Math.PI / 180), `fixture ${f.key} at ${target}: off by ${(Math.acos(Math.min(1, cos)) * 180 / Math.PI).toFixed(3)} deg`);
      assert.ok(Math.abs(r.pan) <= 270 && Math.abs(r.tilt) <= 135);
    }
  }
});

test("the layers preset: each third's rays cross z = 30 m at its altitude (top 22-28, middle 13-19, bottom 6-11), never meet the crowd before z = 40 m and clear the strand", () => {
  const g = RIG.groups.halo;
  const pos = resolvePreset(RIG, g, RIG.presets.layers, { layer_shift: 0 });
  const bands = [[22, 28], [13, 19], [6, 11]];
  const out = { lens: [0, 0, 0], dir: [0, 0, 0] };
  // the strand at its home and its lowest wave pose: rung boxes 9 m wide, 2 m tall
  const rungs = RIG.elements.filter((e) => e.id === "rung");
  const boxes = (y) => rungs.map((e) => ({ centre: [0, y, e.origin[2]], half: [5.1, 1.0, 0.6], roll: 0 }));
  for (let m = 0; m < g.n; m++) {
    const f = RIG.fixtures[g.memberFixture[m]], em = elementMatrix(RIG.elements[f.element]);
    headPose(em, f, pos[m * 2], pos[m * 2 + 1], out);
    const t30 = (30 - out.lens[2]) / out.dir[2];
    assert.ok(t30 > 0, "the beam goes out over the crowd");
    const y30 = out.lens[1] + out.dir[1] * t30;
    const [lo, hi] = bands[g.keys.level[m]];
    assert.ok(y30 >= lo && y30 <= hi, `level ${g.keys.level[m]} head ${m} crosses z 30 at y ${y30.toFixed(2)}`);
    const hit = roomHit(out.lens, out.dir, RIG.venue);
    if (hit.what === "crowd" || hit.what === "floor") {
      const z = out.lens[2] + out.dir[2] * hit.t;
      assert.ok(z >= 40, `head ${m} meets the crowd at z ${z.toFixed(1)}`);
    }
    const dirN = presetDirection(RIG, g, pos, m);
    close(dirN[0] * out.dir[0] + dirN[1] * out.dir[1] + dirN[2] * out.dir[2], 1, 1e-6, "presetDirection agrees with headPose");
    for (const y of [17.0, 14.5]) {
      let minClear = Infinity;
      for (let t = 0; t < 60; t += 0.5) {
        const p = [out.lens[0] + out.dir[0] * t, out.lens[1] + out.dir[1] * t, out.lens[2] + out.dir[2] * t];
        minClear = Math.min(minClear, clearanceToRungs(p, boxes(y)));
      }
      assert.ok(minClear > 0.3, `head ${m} (level ${g.keys.level[m]}) passes ${minClear.toFixed(2)} m from the strand at y ${y}`);
    }
  }
});
