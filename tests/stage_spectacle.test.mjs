// The spectacle wides (source-v1.json cameras): ten full-set shots, zoomed out so the rings and the whole rig read as one
// picture. Daniel, 2026-10-29: "also can we add some more full set spectacle camera positions, i think a lot of ours are
// close and we dont have many good zoom out ones so i can appreciate the crazy ring effects and full set magic".
// Pins: the ten are in the set and quote him; each keeps the whole rig in frame (the halo whole, the towers, the laser
// trusses, the strand's first rung, the crowd's front edge); the director deals them (the live sections' sequences and the
// formations' landing views), clear of the strand and the rings in every formation of the set; their cuts keep the
// 30-degree rule and the strand's axis; they fly within the drone's 15 m/s wherever they play; C reaches every one.
//   node --test tests/stage_spectacle.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Director, DRONE, cameraModel, formationPoseSets, isJumpCut, prepareShot, shotPose } from "../arsenal/web/stage/camera.js";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { RingFormations } from "../arsenal/web/stage/formations.js";

const V1 = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG = expandScene(V1), MODEL = cameraModel(RIG), CAM = V1.cameras;
const SPECTACLE = ["SPEC_FOH_HIGH", "SPEC_REAR_LONGLENS", "SPEC_HIGH_ORBIT", "SPEC_HALL_CORNER_REAR_L", "SPEC_HALL_CORNER_FRONT_R",
  "SPEC_HALL_SIDE_PANO", "SPEC_HALL_PULLBACK", "SPEC_HALL_REAR_DRIFT", "SPEC_GRAND_ARC", "SPEC_SPIRAL_CROWN"];
const OPENS_IN_THE_RINGS = new Set(["SPEC_HALL_PULLBACK"]);   // the zoom-out as a move: it starts inside the rings
const LIVE = ["drop", "break", "groove"];                       // the sections' own sequences (show.sections.*.camera)
const pose0 = () => ({ pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 });
const shot1 = (id) => prepareShot({ id, ...CAM.shots[id] });
const SEC_PER_BEAT = 60 / 150;

// the rig's landmarks (as arsenal/lanes/stage_stills.mjs places them) and the frame test (16:9)
const ring0 = MODEL.rings.reduce((a, b) => (b.outer > a.outer ? b : a), MODEL.rings[0]);
const up = [0, ring0.normal[2], -ring0.normal[1]];
const at = (c, d, k) => c.map((v, i) => v + d[i] * k);
const WHOLE_RIG = {
  "halo top": at(ring0.centre, up, ring0.outer), "halo bottom": at(ring0.centre, up, -ring0.outer),
  "halo left": at(ring0.centre, [1, 0, 0], -ring0.outer), "halo right": at(ring0.centre, [1, 0, 0], ring0.outer),
  "rings centre": ring0.centre.slice(), "strand first rung": [0, MODEL.homeY, MODEL.z[0]],
  "tower L top": [-22, 16, -2], "tower R top": [22, 16, -2], "laser truss L": [-22, 22, -2], "laser truss R": [22, 22, -2],
  "crowd front": [0, 1.9, 6],
};
function inFrame(pose, p, aspect = 16 / 9) {
  const f = [0, 1, 2].map((k) => pose.look[k] - pose.pos[k]), fl = Math.hypot(...f);
  for (let i = 0; i < 3; i++) f[i] /= fl;
  const rl = Math.hypot(f[2], f[0]), r = [-f[2] / rl, 0, f[0] / rl];
  const u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]];
  const d = [0, 1, 2].map((k) => p[k] - pose.pos[k]), z = d[0] * f[0] + d[1] * f[1] + d[2] * f[2];
  if (z < 0.5) return false;
  const tanH = Math.tan((pose.hfov * Math.PI) / 360), tanV = tanH / aspect;
  return Math.abs((d[0] * r[0] + d[1] * r[1] + d[2] * r[2]) / z) <= tanH && Math.abs((d[0] * u[0] + d[1] * u[1] + d[2] * u[2]) / z) <= tanV;
}
const peakSpeed = (s, bars, n = 400) => {
  let m = 0, prev = null;
  const dt = (bars * 4 * SEC_PER_BEAT) / n;
  for (let i = 0; i <= n; i++) {
    const p = shotPose(s, i / n, 0, pose0()).pos;
    if (prev) m = Math.max(m, Math.hypot(p[0] - prev[0], p[1] - prev[1], p[2] - prev[2]) / dt);
    prev = p;
  }
  return m;
};

test("the ten spectacle wides are in the set, quote Daniel, and none is held", () => {
  for (const id of SPECTACLE) {
    const def = CAM.shots[id];
    assert.ok(def, `${id} is in source-v1.json cameras.shots`);
    assert.ok(!def.held, `${id} is not held`);
    assert.ok(def.source.includes("so i can appreciate the crazy ring effects and full set magic"), `${id}: its source quotes Daniel`);
  }
  // and every shot that was there before is still there
  for (const id of ["FOH_WIDE", "ROOF_ESTABLISH", "REAR_TELE_ZIGGURAT", "HIGH_REAR_CRANE", "HALO_ORBIT", "HALO_LOCK", "TRIBUNE_34", "TRIBUNE_HIGH_R"]) assert.ok(CAM.shots[id], id);
  assert.equal(Object.keys(CAM.shots).length, 58);
});

test("each keeps the whole rig in one picture: the halo whole, both towers and laser trusses, the strand's head, the crowd's edge", () => {
  for (const id of SPECTACLE) {
    const s = shot1(id);
    for (const u of [0, 0.25, 0.5, 0.75, 1]) {
      if (u < 0.5 && OPENS_IN_THE_RINGS.has(id)) continue;
      const p = shotPose(s, u, 0, pose0());
      const missing = Object.entries(WHOLE_RIG).filter(([, q]) => !inFrame(p, q)).map(([k]) => k);
      assert.deepEqual(missing, [], `${id} at u ${u}: out of frame`);
    }
    // zoomed out: 40 m or more from the rings' centre (the reveal from the moment it has left them)
    for (let u = OPENS_IN_THE_RINGS.has(id) ? 0.5 : 0; u <= 1.0001; u += 0.05) {
      const p = shotPose(s, u, 0, pose0()).pos;
      assert.ok(Math.hypot(...[0, 1, 2].map((k) => p[k] - ring0.centre[k])) >= 40, `${id} at u ${u.toFixed(2)} is close`);
    }
  }
});

test("the director deals them: the drop, the break and the groove play them, and the formations' landings view through them", () => {
  const live = new Set(), views = new Set();
  for (const name of LIVE) for (const e of CAM.sequences[name]) live.add(e.shot);
  for (const [k, v] of Object.entries(CAM.formation_views)) if (!k.startsWith("_")) for (const id of [...v.glide, ...v.hero]) views.add(id);
  for (const id of SPECTACLE) assert.ok(live.has(id), `${id} plays in a live section`);
  for (const sec of LIVE) assert.ok(Object.values(V1.show.sections).some((s) => s.camera === sec), `a section plays ${sec}`);
  // weighted up where the ring effects play: wides hold at least 40 % of the drop's and the break's bars
  const share = (name) => {
    const seq = CAM.sequences[name], all = seq.reduce((a, e) => a + e.bars, 0);
    return seq.filter((e) => SPECTACLE.includes(e.shot)).reduce((a, e) => a + e.bars, 0) / all;
  };
  assert.ok(share("drop") >= 0.4, `drop ${share("drop")}`);
  assert.ok(share("break") >= 0.8, `break ${share("break")}`);
  assert.ok(share("groove") >= 0.5, `groove ${share("groove")}`);
  assert.equal(CAM.sequences.drop[0].shot, "SPEC_HALL_CORNER_FRONT_R", "the drop's sequence opens wide (the demo's drop bars 16-23, beams and lasers)");
  assert.equal(CAM.sequences.break[0].shot, "SPEC_HALL_REAR_DRIFT", "the break opens on the slow drift across the hall");
  for (const id of ["SPEC_FOH_HIGH", "SPEC_REAR_LONGLENS", "SPEC_HALL_CORNER_FRONT_R", "SPEC_HALL_CORNER_REAR_L", "SPEC_HALL_SIDE_PANO", "SPEC_HIGH_ORBIT"]) {
    assert.ok(views.has(id), `${id} is a landing view`);
  }
  // the ring formations' views take a wide second in line, so the second landing of a ring formation shows the whole rig
  assert.equal(CAM.formation_views.crown.hero[1], "SPEC_FOH_HIGH");
  assert.equal(CAM.formation_views.vortex.hero[1], "SPEC_REAR_LONGLENS");
  assert.equal(CAM.formation_views.portal.hero[1], "SPEC_HALL_CORNER_FRONT_R");
  assert.equal(CAM.formation_views.spiral.hero[2], "SPEC_HALL_CORNER_REAR_L");
});

test("clear of the strand and the rings in every formation of the set (strand and ring formations): dealt as written", () => {
  const RF = new RingFormations(RIG), ringKeys = RF.formations.filter((k) => k !== "home");
  const strandSets = [].concat(...Object.values(RIG.formations).map((f) => formationPoseSets(f, MODEL.z.length) || []));
  const d = new Director(CAM.shots, CAM.sequences, {
    model: MODEL, formations: { ...RIG.formations, ...Object.fromEntries(ringKeys.map((k) => [k, RF.def(k)])) }, views: CAM.formation_views, safe: CAM.safe,
    posesOf: (key, def) => (ringKeys.includes(key) ? strandSets : formationPoseSets(def, MODEL.z.length)),
    ringsOf: (key) => (ringKeys.includes(key) ? RF.annuliSets(key) : null), sightOf: (key) => (ringKeys.includes(key) ? RF.sight(key) : null) });
  const keys = [...Object.keys(RIG.formations), ...ringKeys];
  assert.ok(keys.length >= 7);
  for (const key of keys) {
    const ok = d.validFor(key);
    assert.ok(ok, `${key} is judged`);
    for (const id of SPECTACLE) assert.ok(ok.has(id), `${id} is dealt in ${key}`);
  }
});

test("their cuts keep the 30-degree rule and the strand's axis, and they fly within the drone's limit wherever they play", () => {
  const side = (p) => (p.pos[0] < -3 ? "L" : p.pos[0] > 3 ? "R" : "A");
  for (const name of LIVE) {
    const seq = CAM.sequences[name];
    for (let i = 0; i < seq.length; i++) {
      const a = seq[i].shot, b = seq[(i + 1) % seq.length].shot;
      if (!SPECTACLE.includes(a) && !SPECTACLE.includes(b)) continue;   // the cuts the wides joined
      const pa = shotPose(shot1(a), 1, 0, pose0()), pb = shotPose(shot1(b), 0, 0, pose0());
      assert.ok(!isJumpCut(pa, pb), `${name}: ${a} -> ${b} is a jump cut`);
      const sides = side(pa) + side(pb);
      assert.ok(sides !== "LR" && sides !== "RL", `${name}: ${a} -> ${b} crosses the axis (${sides})`);
    }
    for (const e of seq) if (SPECTACLE.includes(e.shot)) {
      const v = peakSpeed(shot1(e.shot), e.bars);
      assert.ok(v <= DRONE.vmax, `${name}: ${e.shot} at ${e.bars} bars peaks at ${v.toFixed(1)} m/s`);
    }
  }
  // at their own bars (C plays a shot over its own bars), and a landing glide squeezed to half of them
  const glides = new Set(Object.entries(CAM.formation_views).filter(([k]) => !k.startsWith("_")).flatMap(([, v]) => v.glide));
  for (const id of SPECTACLE) {
    const s = shot1(id);
    assert.ok(peakSpeed(s, s.bars) <= DRONE.vmax, `${id} over its own ${s.bars} bars`);
    if (glides.has(id)) assert.ok(peakSpeed(s, s.bars / 2) <= DRONE.vmax, `${id} as a glide over ${s.bars / 2} bars`);
  }
});

test("C reaches every one: the hand-held cycle walks every shot of the set, the wides included, each over its own bars", () => {
  const d = new Director(CAM.shots, CAM.sequences, { model: MODEL, safe: CAM.safe });
  // stage.js KeyC: the next id after the current one in the director's shot table, played over its own bars
  const ids = Object.keys(d.shots);
  let cur = "FOH_WIDE";
  const seen = new Set();
  for (let k = 0; k < ids.length; k++) { cur = ids[(ids.indexOf(cur) + 1) % ids.length]; seen.add(cur); }
  for (const id of SPECTACLE) {
    assert.ok(seen.has(id), `C reaches ${id}`);
    d.manual = { shot: id, p0: 0, beats: (d.shots[id].bars ?? 4) * 4 };
    assert.equal(d.update(5).shot, id);
  }
});
