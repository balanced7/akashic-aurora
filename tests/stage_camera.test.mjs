// Virtual Stage v0: the camera crew (arsenal/web/stage/camera.js). node --test tests/stage_camera.test.mjs
// Cuts on bar lines only, no shot under 2 beats, the strand flythrough arrives on the downbeat, the paths keep clear of
// the rungs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { catmullRom, arcTable, atArc, minJerk, prepareShot, shotPose, Director, clearanceToRungs, vfovOf, MIN_SHOT_BEATS }
  from "../arsenal/web/stage/camera.js";
import { formationTarget } from "../arsenal/web/stage/kinetics.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v0.json", import.meta.url), "utf8"));
const close = (a, b, eps, msg = "") => assert.ok(Math.abs(a - b) <= eps, `${msg} ${a} != ${b}`);

test("centripetal Catmull-Rom passes through its control points; the arc table is monotonic", () => {
  const pts = [[0, 0, 0], [3, 1, 0], [4, 5, 2], [10, 5, 2]];
  for (let i = 0; i < pts.length; i++) {
    const p = catmullRom(pts, i / (pts.length - 1));
    pts[i].forEach((v, k) => close(p[k], v, 1e-9));
  }
  const tab = arcTable(pts);
  for (let i = 1; i <= tab.samples; i++) assert.ok(tab.s[i] >= tab.s[i - 1]);
  const a = atArc(pts, tab, 0, [0, 0, 0]), b = atArc(pts, tab, 1, [0, 0, 0]);
  close(a[0], 0, 1e-9); close(b[0], 10, 1e-9);
  close(minJerk(0), 0, 0); close(minJerk(1), 1, 0); close(minJerk(0.5), 0.5, 1e-12);
  close(vfovOf(90, 1), 90, 1e-9);
});

test("the director cuts only on bar lines and never faster than every 2 beats", () => {
  const d = new Director(SCENE.cameras.shots, SCENE.cameras.sequences);
  const barAnchor = 0;
  let lastCut = null;
  for (const name of Object.keys(SCENE.cameras.sequences)) {
    d.start(name, 8);
    d.index = -1; d.cuts = [];
    for (let f = 0; f < 60 * 120; f++) {
      const pos = 8 + f * (150 / 60 / 60);          // 150 BPM at 60 fps
      const pose = d.update(pos);
      if (pose.cut) {
        const cutPos = d.entry.p0;
        assert.ok(Math.abs((cutPos - barAnchor) / 4 - Math.round((cutPos - barAnchor) / 4)) < 1e-9, `${name}: a cut off the bar line at ${cutPos}`);
        assert.ok(pos - cutPos < 150 / 60 / 60 + 1e-9, "the cut shows on the first frame of its bar");
        if (lastCut !== null) assert.ok(cutPos - lastCut >= MIN_SHOT_BEATS - 1e-9);
        lastCut = cutPos;
      }
    }
    lastCut = null;
  }
  assert.throws(() => new Director({ A: { kind: "static", pos: [0, 0, 0], look: [0, 0, -1] } }, { s: [{ shot: "A", bars: 0.25 }] }));
  // the bar line itself, a hair early in float (pos 60.999999999998 for 61): the sequence's first shot, never its last
  const d2 = new Director(SCENE.cameras.shots, SCENE.cameras.sequences);
  d2.start("drop", 61);
  assert.equal(d2.update(61 - 2e-12).shot, SCENE.cameras.sequences.drop[0].shot);
});

test("the strand flythrough arrives inside the inner ring on the downbeat (the build's last bar line), within one frame", () => {
  const d = new Director(SCENE.cameras.shots, SCENE.cameras.sequences);
  const start = 64, bars = SCENE.cameras.sequences.build[0].bars;
  d.start("build", start);
  const end = start + bars * 4;
  const step = 150 / 60 / 60;
  let prev = null;
  const ring = SCENE.cameras.shots.STRAND_FLYTHROUGH.pos_path.at(-1);
  for (let f = 0; ; f++) {
    const pos = start + f * step;
    if (pos >= end) break;
    const p = d.update(pos);
    prev = { pos, cam: p.pos.slice(), u: p.u };
  }
  // the last frame before the downbeat is within one frame's travel of the ring centre
  const dist = Math.hypot(prev.cam[0] - ring[0], prev.cam[1] - ring[1], prev.cam[2] - ring[2]);
  const speed = d.shots.STRAND_FLYTHROUGH._pos.length / (bars * 4 * 0.4);   // the path's length over 8 bars at 150 BPM
  assert.ok(dist <= speed / 60 + 1e-6, `one frame before the downbeat the camera is ${dist} m from the ring centre`);
  // and on the downbeat itself it is there (u = 1)
  const at = shotPose(d.shots.STRAND_FLYTHROUGH, 1, end);
  ring.forEach((v, k) => close(at.pos[k], v, 1e-6));
});

test("the flythrough and the crane keep 1.5 m clear of the rungs at the wave's extremes", () => {
  const shots = SCENE.cameras.shots;
  const rungsAt = (centre, phase) => Array.from({ length: 12 }, (_, i) => {
    const t = formationTarget("wave", { centre, size: 0.9, roll: 16, measure: 32 }, i, 12, phase);
    return { centre: [0, t.y, 4 + 3.6 * i], half: [5.1, 0.95, 0.6], roll: t.roll };   // the rung's box, the under-rung head included
  });
  for (const id of Object.keys(shots)) {
    const s = prepareShot(shots[id]);
    for (const centre of [14.5, 17]) for (const phase of [0, 8, 16, 24]) {
      const rs = rungsAt(centre, phase);
      for (let u = 0; u <= 1.0001; u += 0.01) {
        const p = shotPose(s, u, 0);
        const c = clearanceToRungs(p.pos, rs);
        assert.ok(c >= 1.5, `${id} at u ${u.toFixed(2)} (wave centre ${centre}) is ${c.toFixed(2)} m from a rung`);
      }
    }
  }
});

test("no shot puts the camera inside the hall's solids: under the rigging grid, out of the FOH riser, the deck and the PA", () => {
  // the solid boxes render.js builds (centre, half extents), and the rigging grid's plane
  const boxes = [
    { name: "FOH riser", c: [0, 1.2, 50], h: [4, 1.2, 2.5] },
    { name: "deck", c: [0, 1, -8], h: [24, 1, 8] },
    ...[-22, -13, -5, 5, 13, 22].map((x) => ({ name: `PA ${x}`, c: [x, 12, Math.abs(x) > 6 ? -1 : -2], h: [0.65, 3, 0.7] })),
    { name: "Bank A truss", c: [0, 22.4, -2], h: [20, 0.23, 0.23] }, { name: "beam truss", c: [0, 26.5, -5], h: [20, 0.25, 0.25] },
  ];
  const shots = SCENE.cameras.shots;
  for (const [id, def] of Object.entries(shots)) {
    const s = prepareShot(def);
    for (let u = 0; u <= 1.0001; u += 0.02) {
      const p = shotPose(s, u, 0).pos;
      assert.ok(p[1] < 32, `${id} at u ${u.toFixed(2)} is at ${p[1].toFixed(2)} m: in or above the rigging grid`);
      for (const b of boxes) {
        const out = [0, 1, 2].some((k) => Math.abs(p[k] - b.c[k]) > b.h[k] + 0.5);
        assert.ok(out, `${id} at u ${u.toFixed(2)} is inside (or within 0.5 m of) the ${b.name}`);
      }
    }
  }
});

test("handheld noise is slow and small; static shots are still", () => {
  const s = prepareShot(SCENE.cameras.shots.CROWD_POV);
  const a = shotPose(s, 0.5, 10), b = shotPose(s, 0.5, 10 + 1 / 60 * 2.5);
  const turn = Math.hypot(a.look[0] - b.look[0], a.look[1] - b.look[1], a.look[2] - b.look[2]);
  assert.ok(turn < 0.05, `handheld moved ${turn} m of look point in one frame`);
  const f = prepareShot(SCENE.cameras.shots.FOH_WIDE);
  assert.deepEqual(shotPose(f, 0.2, 3).pos, shotPose(f, 0.9, 7).pos);
});
