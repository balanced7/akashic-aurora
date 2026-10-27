// Virtual Stage v0: the camera crew (arsenal/web/stage/camera.js). node --test tests/stage_camera.test.mjs
// Cuts on bar lines only, no shot under 2 beats, the strand flythrough arrives on the downbeat, the paths keep clear of
// the rungs.
// v2 (2026-10-27): the strand frame, the formation-validity filter (never a shot within 1.5 m of a rung, in any of the
// camera lane's thirteen altitude shapes), the guard, roll curves, the easings, the dolly zoom, the landing grammar (one
// glide, the cut ON the landing bar line to the hero view), the new shots' hall, speed and cutting rules.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { catmullRom, arcTable, atArc, minJerk, prepareShot, shotPose, Director, clearanceToRungs, vfovOf, MIN_SHOT_BEATS,
         CLEARANCE_M, GUARD_M, EASES, snapEase, easeOf, keyframes, dollyHfov, isJumpCut, strandPoint, lowestRungY, pendulumLatch,
         clearanceToStrand, clearanceToRings, ringAnnulus, cameraModel, shotClearance, formationPoseSets, listAllows, HOME_LINE }
  from "../arsenal/web/stage/camera.js";
import { formationTarget } from "../arsenal/web/stage/kinetics.js";
import { expandScene } from "../arsenal/web/stage/rig.js";

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

// ------------------------------------------------------------------------------------------------------------ v2 --
const V1 = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG1 = expandScene(V1);
const MODEL = cameraModel(RIG1);
const ZS = MODEL.z;
const CAM = V1.cameras;
const N = 12, IDX = [...Array(N).keys()];
const P = (f) => IDX.map(f);
const pose0 = () => ({ pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 });
const waveSets = (centre) => [0, 4, 8, 12, 16, 20, 24, 28].map((ph) => P((i) => {
  const t = formationTarget("wave", { centre, size: 0.9, roll: 16, measure: 32 }, i, N, ph);
  return { y: t.y, roll: t.roll };
}));
// The clearance matrix's formations: the set's two waves, the ceiling, the old dream star, and the camera lane's altitude
// shapes C1-C11 (camera.research.md, "library"), each as the rung poses it lands in.
const CATALOGUE = {
  ceiling: [P(() => ({ y: 20, roll: 0 }))],
  "high-wave": waveSets(17), "low-wave": waveSets(14.5),
  stairs_to_ring: [P((i) => ({ y: 21 - 12 * i / 11, roll: 0 }))],
  stairs_to_crowd: [P((i) => ({ y: 9 + 12 * i / 11, roll: 0 }))],
  valley: [P((i) => ({ y: 9 + 12 * ((i - 5.5) / 5.5) ** 2, roll: 0 }))],
  cathedral: [P((i) => ({ y: 21 - 11 * ((i - 5.5) / 5.5) ** 2, roll: 0 }))],
  zipper: [P((i) => (i % 2 ? { y: 11.5, roll: -18 } : { y: 19.5, roll: 18 }))],
  terraces: [P((i) => ({ y: i < 4 ? 19.5 : i < 8 ? 15 : 10.5, roll: 0 }))],
  spiral_real: [P((i) => ({ y: 10 + 10 * i / 11, roll: -50 + 100 * i / 11 }))],
  spiral_dream: [P((i) => ({ y: 10 + 10 * i / 11, roll: -165 + 330 * i / 11 }))],
  curtain_low: [P(() => ({ y: 9, roll: 0 }))],
  louvres: [P((i) => ({ y: 13 + 6 * i / 11, roll: 35 }))],
  eq_pyramid: [P((i) => { const r = 50 * (1 - Math.abs(i - 5.5) / 5.5); return { y: 12 + 4.45 * Math.sin(r * Math.PI / 180), roll: r }; })],
  star: [P((i) => (i < 6 ? { y: 10, roll: 30 * i } : { y: 21, roll: 0 }))],
};
const FORMATIONS = Object.keys(CATALOGUE);
const failsIn = (shot) => FORMATIONS.filter((f) => shotClearance(shot, CATALOGUE[f], ZS) < CLEARANCE_M);
const shot1 = (id) => prepareShot({ id, ...CAM.shots[id] });

test("v2 easings: arrive_fast is fastest on the ONE, snap holds then lands, arrive_u ends the shot on its point still moving", () => {
  const f = EASES.arrive_fast;
  close(f(0), 0, 0); close(f(1), 1, 1e-12); close(f(0.5), Math.pow(0.5, 2.2), 1e-12);
  const v = (g, u) => (g(Math.min(1, u + 1e-4)) - g(Math.max(0, u - 1e-4))) / 2e-4;
  close(v(f, 1 - 1e-4), 2.2, 0.01, "arrive_fast's speed on the ONE");
  for (const u of [0.25, 0.5, 0.75]) assert.ok(v(f, u) < v(f, 0.999), "arrive_fast still accelerates");
  assert.equal(snapEase(0.5), 0); assert.equal(snapEase(0.75), 0); close(snapEase(0.875), 0.5, 1e-12); assert.equal(snapEase(1), 1);
  close(EASES.snap(0.875), 0.5, 1e-12);
  const s = prepareShot({ kind: "path", pos_path: [[0, 10, 40], [0, 10, 0], [0, 10, -20]], look: [0, 10, -40], arrive_u: 0.92 });
  close(easeOf(s, 1), 0.92, 1e-9, "the path point that lands on the bar line");
  assert.ok(easeOf(s, 1) - easeOf(s, 0.99) > 0.005, "and the camera is still moving there");
  close(easeOf(s, 0), 0, 1e-12);
  const p = shotPose(s, 1, 0, pose0());
  assert.ok(p.pos[2] > -20 + 1, "the shot ends short of the path's end");
  // keyframes: a number holds, two ramp, more pass through every keyframe
  assert.equal(keyframes(7, 0.3), 7); close(keyframes([0, 20], 0.5), 10, 1e-12);
  const k = [0, 8, -8, 8, 0];
  k.forEach((x, i) => close(keyframes(k, i / (k.length - 1)), x, 1e-9));
});

test("the dolly zoom: VERTIGO_TUNNEL keeps the halo's frame width fixed from 87 m to 42 m, where a straight ramp is 10 % off mid-move", () => {
  const s = shot1("VERTIGO_TUNNEL");
  const dz = s.dolly_zoom, width = dz.width_m / dz.fill;
  const lens = [];
  for (const u of [0, 0.25, 0.5, 0.75, 1]) {
    const p = shotPose(s, u, 0, pose0());
    const d = Math.hypot(p.pos[0] - dz.target[0], p.pos[1] - dz.target[1], p.pos[2] - dz.target[2]);
    close(2 * d * Math.tan((p.hfov * Math.PI / 180) / 2), width, 1e-6, `the frame width at the halo, u ${u}`);
    lens.push(p.hfov);
  }
  close(lens[0], 29.0, 0.1, "28.9-29 degrees from 87 m"); close(lens[4], 56.8, 0.2, "57 degrees from 42 m");
  close(dollyHfov(28, 0.62, Math.hypot(8, 87)), lens[0], 1e-9);
  const ramp = (lens[0] + lens[4]) / 2;
  assert.ok(Math.abs(ramp - lens[2]) / lens[2] > 0.08, `a linear hfov mid-move ${ramp} vs ${lens[2]}: the ring would breathe`);
});

test("roll curves: [from, to] turns with the move, keyframes bank through the zipper's slalom", () => {
  const ic = shot1("UNDER_RUNG_ICON");
  close(shotPose(ic, 0, 0, pose0()).roll, 0, 1e-12); close(shotPose(ic, 1, 0, pose0()).roll, 20, 1e-12);
  close(shotPose(ic, 0.5, 0, pose0()).roll, 10, 1e-12);
  const td = shot1("TOPDOWN_DESCEND");
  close(shotPose(td, 1, 0, pose0()).roll, 45, 1e-12);
  const z = shot1("THREAD_THE_ZIPPER");
  const signs = new Set();
  for (let u = 0.3; u <= 0.85; u += 0.01) { const r = shotPose(z, u, 0, pose0()).roll; if (Math.abs(r) > 6) signs.add(Math.sign(r)); }
  assert.deepEqual([...signs].sort(), [-1, 1], "it banks both ways past the rungs");
  close(shotPose(z, 0, 0, pose0()).roll, 0, 1e-12); close(shotPose(z, 1, 0, pose0()).roll, 0, 1e-12);
});

test("the strand frame: theta 0 is above the centre line and 90 house right; the same shot re-frames a strand at a new height", () => {
  const line = (y) => ({ ys: Array(N).fill(y), zs: ZS });
  const s = prepareShot({ kind: "strand", strand: { s: [0.5, 0.5], r: 8, theta: [0, 90], look_ahead_s: 0.2 }, ease: "linear" });
  const zMid = ZS[0] + 0.5 * (ZS[N - 1] - ZS[0]);
  for (const y of [20, 12]) {
    const a = shotPose(s, 0, 0, pose0(), { line: line(y) }), b = shotPose(s, 1, 0, pose0(), { line: line(y) });
    [0, y + 8, zMid].forEach((v, k) => close(a.pos[k], v, 1e-9, `theta 0 over a strand at ${y} m`));
    [8, y, zMid].forEach((v, k) => close(b.pos[k], v, 1e-9, `theta 90 beside a strand at ${y} m`));
    close(a.look[1], y, 1e-9, "it looks along the centre line");
  }
  // the centre line passes through every rung centre and runs on level past the ends
  const ys = P((i) => 10 + i);
  ys.forEach((y, i) => close(strandPoint({ ys, zs: ZS }, i / (N - 1))[1], y, 1e-9));
  close(strandPoint({ ys, zs: ZS }, 1.3)[1], ys[N - 1], 1e-12);
  // the under-ride: a dip at the middle rungs pulls the lens under them
  const dip = { ys: P((i) => (i === 6 ? 11 : 19)), zs: ZS };
  assert.equal(lowestRungY(dip, ZS[6] - 4, ZS[6] + 4), 11);
  const ur = prepareShot({ kind: "strand", strand: { s: [6 / 11, 6 / 11], under: 3, ahead: 0 } });
  close(shotPose(ur, 0.5, 0, pose0(), { line: dip }).pos[1], 8, 1e-9);
  // a low strand latches the corkscrew into a pendulum over the top (no crowd skim)
  const hc = shot1("HELIX_CORKSCREW");
  assert.equal(pendulumLatch(hc, line(20)), false); assert.equal(pendulumLatch(hc, line(9)), true);
  const low = { line: line(9), pendulum: true };
  for (let u = 0; u <= 1; u += 0.01) assert.ok(shotPose(hc, u, 0, pose0(), low).pos[1] >= 9 - 8 * Math.cos(70 * Math.PI / 180) - 1e-6);
});

test("the clearance model: the rung's six boxes (the turned diamond, the head inside it, two arms, two ends) and the rings' annuli", () => {
  const level = P(() => ({ y: 20, roll: 0 }));
  const vertex = Math.SQRT2 * (3 / Math.SQRT2 - 0.76);              // 3 m from the centre, 1.93 m from the diamond's vertex
  close(clearanceToStrand([0, 23, ZS[3]], level, ZS), vertex, 1e-9, "3 m over the diamond's top vertex");
  close(clearanceToStrand([0, 17, ZS[3]], level, ZS), vertex, 1e-9, "3 m under: the lower vertex (the head hangs inside it)");
  close(clearanceToStrand([3, 20, ZS[3]], level, ZS), 0, 1e-9, "on the arm");
  close(clearanceToStrand([0, 20, ZS[3] + 1.8], level, ZS), Math.hypot(0.35, 1.55), 1e-9, "midway between two rungs: the hung head's corner");
  // rolled 90 degrees, the rung's end stands where the lens was 5 m over its centre
  const rolled = P((i) => ({ y: 20, roll: i === 3 ? 90 : 0 }));
  assert.equal(clearanceToStrand([0, 25, ZS[3]], rolled, ZS), 0);
  assert.ok(clearanceToStrand([0, 25, ZS[3]], level, ZS) > 3.5);
  // the old one-box helper and the five boxes agree that a point far away is far
  close(clearanceToRungs([0, 40, 20], [{ centre: [0, 20, 20], half: [5.1, 0.95, 0.6], roll: 0 }]), 19.05, 1e-9);
  // the inner ring's 3 m hole is under the 1.5 m rule from its very centre (Daniel's call 5: no threading tonight)
  const inner = MODEL.rings[3];
  close(clearanceToRings(inner.centre, [inner]), 1.4, 1e-9);
  const flat = ringAnnulus([0, 10, 0], 10, 2, 90);
  close(clearanceToRings([9, 15, 0], [flat]), 5 - 0.15, 1e-9, "5 m over a ring lying flat");
  close(clearanceToRings([12, 10, 0], [flat]), 12 - 10.45, 1e-9, "beside it: its heads stand 0.45 m out");
});

test("the clearance matrix: the old flythrough hits most new shapes, HEAD_ORBIT the lane's four, the strand-frame corkscrew clears 14 of 15", () => {
  assert.deepEqual(FORMATIONS.filter((f) => !failsIn(shot1("STRAND_FLYTHROUGH")).includes(f)), ["ceiling", "high-wave", "low-wave", "louvres"]);
  assert.deepEqual(failsIn(shot1("HEAD_ORBIT")), ["valley", "spiral_dream", "curtain_low", "star"]);
  assert.deepEqual(failsIn(shot1("HELIX_CORKSCREW")), ["zipper"]);
  // the same corkscrew round a FIXED centre (y 15, r 9) rises into high rungs and dips into low ones
  const fixed = prepareShot({ ...CAM.shots.HELIX_CORKSCREW, strand: { ...CAM.shots.HELIX_CORKSCREW.strand, r: 9, pendulum: undefined } });
  const fixedLine = { line: { ys: Array(N).fill(15), zs: ZS } };
  const fixedFails = FORMATIONS.filter((f) => CATALOGUE[f].some((poses) => {
    for (let k = 0; k <= 160; k++) if (clearanceToStrand(shotPose(fixed, k / 160, 0, pose0(), fixedLine).pos, poses, ZS) < CLEARANCE_M) return true;
    return false;
  }));
  assert.ok(fixedFails.length >= 5, `the fixed-centre corkscrew fails ${fixedFails.join(", ")}`);
  assert.deepEqual(failsIn(shot1("THREAD_THE_ZIPPER")).filter((f) => ["zipper", "ceiling", "curtain_low"].includes(f)), [], "the gap it flies is open in its own three");
});

test("the director never deals a shot within 1.5 m of the strand: every sequence, in every altitude shape, the stand-in named", () => {
  const d = new Director(CAM.shots, CAM.sequences, { model: MODEL, views: CAM.formation_views, safe: CAM.safe,
                                                    formations: Object.fromEntries(FORMATIONS.map((f) => [f, {}])), posesOf: (key) => CATALOGUE[key] || null });
  const stats = { frames: 0, swaps: 0 };
  for (const f of FORMATIONS) {
    for (const [name, seq] of Object.entries(CAM.sequences)) {
      const beats = seq.reduce((a, e) => a + e.bars * 4, 0);
      d.start(name, 0); d.key = null; d.cuts = []; d.lastCutPos = -Infinity;
      for (let k = 0; k <= beats * 12; k++) {
        const pos = k / 12, sets = CATALOGUE[f], poses = sets[Math.floor(pos / 4) % sets.length];
        const p = d.update(pos, { formation: f, poses, dt: 0.4 / 12 });
        const c = clearanceToStrand(p.pos, poses, ZS);
        assert.ok(c >= CLEARANCE_M - 0.02, `${f}/${name} at beat ${pos}: ${p.shot} is ${c.toFixed(2)} m from a rung`);
        stats.frames++;
      }
      stats.swaps += d.cuts.filter((c) => c.for).length;
    }
  }
  assert.equal(d.clear.guards, 0, "the validity filter dealt clear shots: the guard never had to act");
  assert.ok(stats.swaps > 10, `stand-ins dealt: ${stats.swaps}`);
  // the build's flythrough under a valley: the safe wide stands in, and the cut says for whom
  d.start("build", 0); d.key = null; d.cuts = [];
  assert.equal(d.update(0, { formation: "valley", poses: CATALOGUE.valley[0], dt: 1 / 60 }).shot, "FOH_WIDE");
  assert.deepEqual([d.cuts[0].shot, d.cuts[0].for], ["FOH_WIDE", "STRAND_FLYTHROUGH"]);
});

test("the demo is unchanged: in the set's own formations every shot its sections and phrases play is dealt as written", () => {
  const d = new Director(CAM.shots, CAM.sequences, { model: MODEL, formations: RIG1.formations, views: CAM.formation_views, safe: CAM.safe });
  const played = new Set();
  for (const sec of Object.values(V1.show.sections)) for (const e of CAM.sequences[sec.camera]) played.add(e.shot);
  // the phrases' cameras: their steps', their alternates' and their variants' (every "shot" and "alt" in the phrase data)
  for (const m of JSON.stringify(V1.phrases || {}).matchAll(/"(?:shot|alt)":"([A-Z0-9_]+)"/g)) played.add(m[1]);
  assert.ok(played.has("SIDE_TRACK_PARALLEL") && played.has("WORM_RING"), "a variant's and a split step's shots are counted");
  for (const key of Object.keys(RIG1.formations)) {
    const ok = d.validFor(key);
    assert.ok(ok, `${key} is judged`);
    for (const id of played) assert.ok(ok.has(id), `${id} is clear of the strand in ${key}`);
  }
  // and with no scene the director is v1's (no filter, no guard)
  const v1 = new Director(CAM.shots, CAM.sequences);
  v1.start("build", 0);
  assert.equal(v1.update(0).shot, "STRAND_FLYTHROUGH");
});

test("a landing: one glide from the next bar line while the hoists move, the cut ON the landing bar line to the hero view", () => {
  // stairs: the lane's stairs-to-ring; spiral: a ring formation (lane D's) while the strand hangs at curtain height
  const formations = { ceiling: { name: "ceiling", params: { y: 20 } }, stairs: {}, spiral: {} };
  const posesOf = (key, def) => (key === "stairs" ? CATALOGUE.stairs_to_ring : key === "spiral" ? CATALOGUE.curtain_low : formationPoseSets(def, N));
  const d = new Director(CAM.shots, CAM.sequences, { model: MODEL, formations, views: CAM.formation_views, safe: CAM.safe, posesOf });
  d.start("groove", 0);
  const run = (from, to, sc) => { const cuts = []; for (let k = Math.round(from * 24); k <= Math.round(to * 24); k++) { const p = d.update(k / 24, sc(k / 24)); if (p.cut) cuts.push([k / 24, p.shot, d.cuts.at(-1).why]); } return cuts; };
  const ceil = { formation: "ceiling", poses: CATALOGUE.ceiling[0], dt: 1 / 60 };
  run(0, 13, () => ceil);
  // at beat 13.25 MORPH asks for the stairs; the hoists land them on beat 96 (a real-mode 20-bar move)
  const stairs = (pos) => ({ formation: "stairs", posLand: 96, poses: CATALOGUE.stairs_to_ring[0], dt: 1 / 60 });
  const cuts = run(13.25, 140, stairs);
  const L = d.landings.at(-1);
  assert.deepEqual([L.glide, L.hero, L.posLand], ["PROFILE_GRAPH", "REAR_TELE_ZIGGURAT", 96]);
  // PROFILE_GRAPH is 8 bars: stretched to at most 16, so it starts on bar line 32 (the groove plays until then)
  assert.deepEqual(cuts.find((c) => c[2] === "landing-glide"), [32, "PROFILE_GRAPH", "landing-glide"]);
  assert.deepEqual(cuts.find((c) => c[2] === "landing-hero"), [96, "REAR_TELE_ZIGGURAT", "landing-hero"]);
  assert.ok(cuts.filter((c) => c[0] > 32 && c[0] < 96).length === 0, "no cut while the hoists move: the move shows the motion");
  assert.ok(cuts.some((c) => c[0] === 128 && c[2] === "bar"), "after the hero's 8 bars the groove plays on");
  // the next landing on the same shape deals the next views
  run(141, 150, () => ceil);
  d.update(151, { formation: "stairs", posLand: 200, poses: CATALOGUE.stairs_to_ring[0], dt: 1 / 60 });
  assert.deepEqual([d.landings.at(-1).glide, d.landings.at(-1).hero], ["STRAND_ORBIT_FULL", "TRUSS_REVERSE"]);
  // a view that would come within 1.5 m of the strand is skipped: the spiral's hero looks up its axis from under the
  // strand, so with the strand hung at curtain height (9 m) the next view (HALO_LOCK) is dealt instead
  d.update(201, ceil);
  d.update(202, { formation: "spiral", posLand: 260, poses: CATALOGUE.curtain_low[0], dt: 1 / 60 });
  assert.equal(d.landings.at(-1).hero, "HALO_LOCK");
  // a phrase that owns the camera keeps it
  d.update(261, ceil);
  d.plan([{ shot: "HALO_LOCK", p0: 264, p1: 296 }]);
  d.update(262.5, { formation: "stairs", posLand: 320, poses: CATALOGUE.stairs_to_ring[0], dt: 1 / 60 });
  assert.equal(d.landings.at(-1).posLand, 260, "no landing plan over the phrase's");
  // the orrery and spiral slots exist with heroes and glides; a hero of the orrery is a placeholder lane D retunes
  for (const k of ["orrery", "spiral"]) { const v = CAM.formation_views[k]; assert.ok(v.hero.length && v.glide.length && v.placeholder, k); }
});

test("a formation that changes under a playing shot swaps it on the next bar line; the guard cuts away on a 2-beat line", () => {
  const formations = { "high-wave": RIG1.formations["high-wave"], valley: {} };
  const posesOf = (key, def) => (key === "valley" ? CATALOGUE.valley : key === "mystery" ? null : formationPoseSets(def, N));
  const d = new Director(CAM.shots, CAM.sequences, { model: MODEL, formations, safe: CAM.safe, posesOf });
  d.start("build", 0);
  for (let k = 0; k <= 9.7 * 24; k++) assert.equal(d.update(k / 24, { formation: "high-wave", poses: CATALOGUE["high-wave"][0], dt: 1 / 60 }).shot, "STRAND_FLYTHROUGH");
  let swap = null;
  for (let k = 9.75 * 24; k <= 16 * 24; k++) { const p = d.update(k / 24, { formation: "valley", poses: CATALOGUE.ceiling[0], dt: 1 / 60 }); if (p.cut) swap = [k / 24, p.shot, d.cuts.at(-1).why, d.cuts.at(-1).for]; }
  assert.deepEqual(swap, [12, "FOH_WIDE", "swap", "STRAND_FLYTHROUGH"]);
  // the guard: a formation nobody could judge ("mystery") with the strand hung low across the flythrough's path
  const g = new Director(CAM.shots, CAM.sequences, { model: MODEL, formations, safe: CAM.safe, posesOf });
  g.start("build", 0);
  let cut = null, minBefore = Infinity;
  for (let k = 0; k <= 32 * 24; k++) {
    const pos = k / 24, p = g.update(pos, { formation: "mystery", poses: CATALOGUE.curtain_low[0], dt: 1 / 60 });
    if (p.cut && pos > 0) { cut = [pos, p.shot, g.cuts.at(-1).why]; break; }
    minBefore = Math.min(minBefore, g.clear.now);
  }
  assert.ok(cut && cut[2] === "guard" && cut[1] === "FOH_WIDE", JSON.stringify(cut));
  close((cut[0] / 2) % 1, 0, 1e-9, "on a 2-beat line");
  assert.ok(minBefore >= GUARD_M, `the guard cut before the lens came within ${GUARD_M} m (closest ${minBefore.toFixed(2)} m)`);
  assert.equal(g.clear.guards, 1);
});

test("a ring formation's rings join the filter: with R0 laid flat, the shot from behind the rings is not dealt, and the guard sees live rings", () => {
  // lane D's orrery tilts the rings apart; ringsOf hands the director their annuli (a flat R0: the gimbal's horizontal)
  const flatR0 = [ringAnnulus([0, 14, -11], 14, 2.5, 90), ...MODEL.rings.slice(1)];
  const ringsOf = (key) => (key === "flat" ? [flatR0] : null);
  const d = new Director(CAM.shots, CAM.sequences, { model: MODEL, formations: { flat: {} }, safe: CAM.safe, ringsOf, posesOf: () => [CATALOGUE.ceiling[0]] });
  const ok = d.validFor("flat");
  assert.equal(ok.has("HALO_REVERSE"), false, "HALO_REVERSE sits inside a flat R0's sweep");
  assert.ok(ok.has("FOH_WIDE") && ok.has("ORRERY_HERO"));
  // an annulus may take any normal (a gimbal tilted about z as well as x)
  const g = ringAnnulus([0, 14, -11], 10, 2, 0, [1, 0, 0]);
  close(clearanceToRings([5, 23, -11], [g]), 5 - 0.15, 1e-9, "5 m off the band of a ring that faces house right");
  // the guard reads the live rings the scene hands it
  d.start("break", 0);
  for (let k = 0; k < 24; k++) d.update(k / 24, { formation: "flat", poses: CATALOGUE.ceiling[0], rings: flatR0, dt: 1 / 60 });
  close(d.clear.now, Math.min(clearanceToStrand(d.pose.pos, CATALOGUE.ceiling[0], ZS), clearanceToRings(d.pose.pos, flatR0)), 1e-9);
  assert.ok(d.clear.now >= CLEARANCE_M, `${d.pose.shot} keeps the rule round the flat ring`);
});

test("held shots are never dealt; the data lists narrow a shot to its formations; C plays a shot in motion over its own bars", () => {
  const d = new Director(CAM.shots, CAM.sequences, { model: MODEL, safe: CAM.safe });
  assert.equal(d.deal("RING_THREAD", []), "FOH_WIDE");
  assert.throws(() => new Director(CAM.shots, { s: [{ shot: "RING_THREAD", bars: 4 }] }), /held/);
  assert.equal(listAllows(d.shots.THREAD_THE_ZIPPER, "zipper", null), true);
  assert.equal(listAllows(d.shots.THREAD_THE_ZIPPER, "low-wave", "wave"), false);
  assert.equal(listAllows(d.shots.THREAD_THE_ZIPPER, null, null), true);
  d.manual = { shot: "DIVE_FROM_ROOF", p0: 10, beats: 16 };
  close(d.update(14).u, 0.25, 1e-12); close(d.update(26 + 4).u, 0.25, 1e-12, "it loops");
  assert.equal(d.pose.shot, "DIVE_FROM_ROOF");
});

// the hall's solids (render.js _build): deck, DJ booth, PA hangs, the trusses, the towers, FOH, the lip row's heads
const SOLIDS = [
  { name: "deck", c: [0, 1, -8], h: [24, 1, 8] }, { name: "DJ booth", c: [0, 2.6, -4], h: [1.5, 0.6, 0.7] },
  ...[-22, -13, -5, 5, 13, 22].map((x) => ({ name: `PA ${x}`, c: [x, 12, Math.abs(x) > 6 ? -1 : -2], h: [0.65, 3, 0.7] })),
  { name: "Bank A truss", c: [0, 22.4, -2], h: [20, 0.23, 0.23] }, { name: "beam truss", c: [0, 26.5, -5], h: [20, 0.25, 0.25] },
  { name: "side tower L", c: [-22, 8, -2], h: [0.3, 8, 0.3] }, { name: "side tower R", c: [22, 8, -2], h: [0.3, 8, 0.3] },
  { name: "FOH riser", c: [0, 1.2, 50], h: [4, 1.2, 2.5] },
  ...[[-12, 30], [12, 30], [-12, 55], [12, 55]].map(([x, z]) => ({ name: `delay tower ${x},${z}`, c: [x, 5, z], h: [0.3, 5, 0.3] })),
  { name: "lip row", c: [0, 2.2, 0.6], h: [23.3, 0.35, 0.3] },
];
const sample = (s, k = 200) => Array.from({ length: k + 1 }, (_, i) => shotPose(s, i / k, 0, pose0()).pos);

test("every v1 shot stays out of the hall's solids, under the grid, over the stands; 1.5 m from the rings (the flythrough's arrival excepted)", () => {
  const V = V1.venue, tan = Math.tan(V.stands.rake_deg * Math.PI / 180);
  for (const [id, def] of Object.entries(CAM.shots)) {
    const s = prepareShot(def);
    let ring = Infinity;
    for (const p of sample(s)) {
      assert.ok(p[1] < V.grid_y - 1, `${id}: ${p[1].toFixed(2)} m is in the rigging grid`);
      for (const b of SOLIDS) assert.ok([0, 1, 2].some((k) => Math.abs(p[k] - b.c[k]) > b.h[k] + 0.5), `${id} at ${p.map((v) => v.toFixed(1))} is within 0.5 m of the ${b.name}`);
      const standY = Math.max(0, (Math.abs(p[0]) - V.floor.x[1]) * tan, (p[2] - V.floor.z[1]) * tan);
      if (standY > 0) assert.ok(p[1] - standY >= 2, `${id} is ${(p[1] - standY).toFixed(2)} m over the stands`);
      assert.ok(p[2] > V.floor.z[0] + 1.5, `${id} is in the drape`);
      ring = Math.min(ring, clearanceToRings(p, MODEL.rings));
    }
    // the flythrough's arrival in the inner ring's mouth (v0, pinned by the receipt: 1.36 m); RING_THREAD is held for Daniel
    if (id === "STRAND_FLYTHROUGH") assert.ok(ring >= 1.3, `${id}: ${ring.toFixed(2)} m from a ring`);
    else if (!def.held) assert.ok(ring >= CLEARANCE_M, `${id}: ${ring.toFixed(2)} m from a ring`);
  }
});

const V2_SHOTS = ["PROFILE_GRAPH", "PROFILE_LOW_SKYLINE", "REAR_TELE_ZIGGURAT", "VARINI_RESOLVE", "ROOF_ESTABLISH", "HIGH_REAR_CRANE",
  "TRIBUNE_HIGH_R", "STAGE_CORNER_REVERSE", "TRUSS_REVERSE", "HALO_REVERSE", "DIVE_FROM_ROOF", "CROWD_SKIM", "CROWD_POPUP",
  "STRAND_ORBIT_FULL", "SPIRAL_ASCENT", "RING_THREAD", "CURTAIN_FOLLOW", "THREAD_THE_ZIPPER"];
const V2_SEQUENCES = ["groove", "showcase", "build-dive", "drop-v2"];
const pathLength = (s) => { const pts = sample(s, 400); let L = 0; for (let i = 1; i < pts.length; i++) L += Math.hypot(...[0, 1, 2].map((k) => pts[i][k] - pts[i - 1][k])); return L; };

test("the camera lane's Tier A (18) and the new engine's shots are in the set, and fly within the drone's 15 m/s at 150 BPM", () => {
  for (const id of [...V2_SHOTS, "HELIX_CORKSCREW", "TUBE_RIDE", "VERTIGO_TUNNEL", "UNDER_RUNG_ICON", "TOPDOWN_DESCEND", "DIVE_FROM_ROOF_2", "DIVE_FROM_ROOF_1"]) {
    assert.ok(CAM.shots[id], `${id} is in the set`);
    const s = prepareShot(CAM.shots[id]);
    const v = pathLength(s) / (s.bars * 4 * 0.4);
    assert.ok(v <= 15, `${id}: ${v.toFixed(1)} m/s over its ${s.bars} bars`);
  }
  for (const name of V2_SEQUENCES) for (const e of CAM.sequences[name]) {
    const v = pathLength(prepareShot(CAM.shots[e.shot])) / (e.bars * 4 * 0.4);
    assert.ok(v <= 15, `${name}: ${e.shot} at ${e.bars} bars flies ${v.toFixed(1)} m/s`);
  }
  // the budget variants shorten the path, never speed the camera past the limit
  assert.ok(pathLength(prepareShot(CAM.shots.DIVE_FROM_ROOF_1)) <= 24 && pathLength(prepareShot(CAM.shots.DIVE_FROM_ROOF_2)) <= 48);
});

test("the new sequences cut by the book: no jump cut (under 30 degrees and a 1.5 x size change) and no crossing of the strand's axis", () => {
  const side = (p) => (p.pos[0] < -3 ? "L" : p.pos[0] > 3 ? "R" : "A");
  for (const name of V2_SEQUENCES) {
    const seq = CAM.sequences[name];
    for (let i = 0; i < seq.length; i++) {
      const a = prepareShot(CAM.shots[seq[i].shot]), b = prepareShot(CAM.shots[seq[(i + 1) % seq.length].shot]);
      if (a.id === b.id || seq[i].shot === seq[(i + 1) % seq.length].shot) continue;
      const pa = shotPose(a, 1, 0, pose0()), pb = shotPose(b, 0, 0, pose0());
      assert.ok(!isJumpCut(pa, pb), `${name}: ${seq[i].shot} -> ${seq[(i + 1) % seq.length].shot} is a jump cut`);
      const sides = side(pa) + side(pb);
      assert.ok(sides !== "LR" && sides !== "RL", `${name}: ${seq[i].shot} -> ${seq[(i + 1) % seq.length].shot} crosses the axis (${sides})`);
    }
  }
  // a move that arrives where the next shot holds is no cut at all (VARINI_RESOLVE into REAR_TELE_ZIGGURAT)
  assert.equal(isJumpCut(shotPose(shot1("VARINI_RESOLVE"), 1, 0, pose0()), shotPose(shot1("REAR_TELE_ZIGGURAT"), 0, 0, pose0())), false);
  const a = shotPose(shot1("FOH_WIDE"), 0, 0, pose0()), b = { ...a, pos: [a.pos[0] + 2, a.pos[1], a.pos[2]], look: a.look.slice() };
  assert.equal(isJumpCut(a, b), true, "a 2 m nudge on the same lens is a jump cut");
});

test("the orrery's placeholder views keep 16.75 m from the ring hub (R0's radius, its heads, the rule): clear at any ring pose", () => {
  const hub = [0, 14, -11], R0 = 14 + 0.45 + 1.5 + 0.8;
  for (const id of new Set([...CAM.formation_views.orrery.glide, ...CAM.formation_views.orrery.hero])) {
    for (const p of sample(prepareShot(CAM.shots[id]))) assert.ok(Math.hypot(p[0] - hub[0], p[1] - hub[1], p[2] - hub[2]) >= R0, `${id} comes within ${R0} m of the hub`);
  }
  for (const [k, v] of Object.entries(CAM.formation_views)) if (!k.startsWith("_")) for (const id of [...v.glide, ...v.hero]) assert.ok(CAM.shots[id] && !CAM.shots[id].held, `${k}: ${id}`);
});
