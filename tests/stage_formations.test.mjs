// Virtual Stage v2: the ring formations (arsenal/web/stage/formations.js). node --test tests/stage_formations.test.mjs
// The orrery and the spiral with its energy beam, the vortex, the crown and the portal: every ring inside the room and
// clear of its neighbours at every phase, every beam ending on the roof, the deck, the upstage floor, the back wall or the
// core (never the crowd or the stands), MORPH on the next bar line, HERO once per eight bars on the next ONE through the
// FlashGate, the reveal in depth order, steady light (no frame-to-frame jumps but the gated discharge), and the camera's
// hero views for each formation resolved and clear before anything renders (the spec's amendment 6).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene, elementMatrix, mountPose, headPose } from "../arsenal/web/stage/rig.js";
import { RingFormations, validateRingFormations, beamEnds, ringClearance, coreAxis, ringTables, aimInto, MAX_FORMATION_EMIT, BEAM_END_OK }
  from "../arsenal/web/stage/formations.js";
import { Programmer, FlashGate, H, HEAD_FLOATS } from "../arsenal/web/stage/programmer.js";
import { LaserEngine, extraHeadsFrom } from "../arsenal/web/stage/lasers.js";
import { Lasers3D } from "../arsenal/web/stage/lasers3d.js";
import { BeatGrid } from "../arsenal/web/stage/grid.js";
import { Director, cameraModel, formationPoseSets, shotRingClearance, shotSight, shotStructure, CLEARANCE_M } from "../arsenal/web/stage/camera.js";
import { formationTarget } from "../arsenal/web/stage/kinetics.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const KEYS = ["home", "orrery", "spiral", "vortex", "crown", "portal"];
const FPS = 60, DT = 1 / FPS;
const C = SCENE.ring_formations.centre;

test("the scene's ring formations are valid: the deck resolves, dream flags where the rings turn", () => {
  assert.deepEqual(validateRingFormations(RIG), []);
  assert.deepEqual(SCENE.ring_formations.deck, KEYS);
  const R = new RingFormations(RIG);
  assert.deepEqual(R.formations.sort(), [...KEYS].sort());
  for (const k of ["orrery", "spiral"]) assert.equal(R.dream(k), true, `${k} is a dream formation`);
  for (const k of ["home", "vortex", "crown", "portal"]) assert.equal(R.dream(k), false, `${k} is real-capable`);
  // a real formation asking for a rotator is refused (a 3-point hung ring only lifts and tilts)
  const bad = expandScene({ ...SCENE, ring_formations: { ...SCENE.ring_formations, vortex: { ...SCENE.ring_formations.vortex, rings: [{ tilt: 55, yaw_beats: 37 }, {}, {}, {}] } } });
  assert.ok(validateRingFormations(bad).some((e) => /dream-only/.test(e)));
});

test("the energy beam's axis: up through the core to the roof, down to the floor upstage of the deck", () => {
  const A = coreAxis(RIG);
  assert.equal(A.toWhat, "roof");
  assert.equal(A.fromWhat, "floor");
  assert.ok(A.from[2] < SCENE.venue.deck.z[0] && A.from[2] > SCENE.venue.floor.z[0], `the column stands at z ${A.from[2]}`);
  assert.ok(Math.abs(A.from[2] + 20.8) < 0.05 && Math.abs(A.C[1] + A.n[1] * A.toLen - 38) < 1e-6);
});

test("every formation keeps every ring inside the room and clear of the others, at every phase of its turning", () => {
  for (const key of KEYS) {
    for (const pos of [0, 7, 19, 33, 52, 71, 96, 113]) {
      const r = ringClearance(RIG, key, pos);
      for (const e of r.env) assert.ok(e.ok, `${key} at beat ${pos}: ring ${e.k} is ${e.margin.toFixed(2)} m into the ${e.why}`);
      for (const g of r.gaps) assert.ok(g.gap >= 0.3, `${key} at beat ${pos}: rings ${g.a} and ${g.b} are ${g.gap.toFixed(2)} m apart`);
    }
  }
  // the orrery's gimbals: R0 holds the dial at 55 (its only legal window at the hang is 47.5..63), the others tilt apart
  const o = ringClearance(RIG, "orrery", 0).poses;
  assert.deepEqual(o.map((p) => Math.round(p.tilt)), [55, 80, 60, 30]);
  // the portal stands ring 0 upright only after lifting the cluster 4.5 m (at the hang the window stops at 47.5)
  const p = ringClearance(RIG, "portal", 0).poses;
  assert.ok(Math.abs(p[0].y - 18.5) < 1e-9 && Math.abs(p[0].tilt) < 1e-9);
});

test("safety: every beam a formation owns ends on the roof, the deck, the upstage floor, the back wall or the core", () => {
  const seen = {};
  for (const key of KEYS) {
    for (const pos of [0, 5, 13, 29, 47]) {
      const ends = beamEnds(RIG, key, pos);
      for (const e of ends) {
        assert.ok(e.ok, `${key} at beat ${pos}: ${e.kind} ${e.index} ends on the ${e.what} at ${e.at}`);
        seen[e.what] = (seen[e.what] || 0) + 1;
      }
      if (key !== "home") assert.ok(ends.length > 1, `${key} draws beams`);
    }
  }
  for (const w of Object.keys(seen)) assert.ok(BEAM_END_OK.includes(w) || w === "floor", w);
  assert.ok(seen.orb > 0 && seen.roof > 0 && seen.backwall > 0, JSON.stringify(seen));
  // the orrery's spokes stop on the core: 48 heads and 12 ring lasers
  const orb = beamEnds(RIG, "orrery", 0).filter((e) => e.what === "orb");
  assert.equal(orb.length, 60);
});

// a stage-like frame loop without the renderer: the same order stage.js runs
function makeStage({ key = "home", theme = "dreaming-city" } = {}) {
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  const programmer = new Programmer(RIG, { theme: { name: theme, ...SCENE.themes[theme] } });
  const rings = new RingFormations(RIG);
  rings.roles = programmer.roleRGB;
  programmer.setLayer(rings);
  if (key !== "home") rings.set(key, 0);
  const lasers = new LaserEngine({ seed: RIG.seed, clock: grid.clock(), colours: SCENE.themes[theme].laser, heads: extraHeadsFrom(RIG.projectors) });
  const l3d = new Lasers3D(RIG.projectors, RIG.venue, { heads: lasers.heads });
  programmer.setLook("groove", 0);
  let f = 0, last = null;
  const step = (n = 1, cam = [0, 8, 60]) => {
    for (let i = 0; i < n; i++, f++) {
      const t = f * (1000 / FPS), pos = grid.posAt(t);
      rings.update(grid, t, DT, programmer.flashGate);
      programmer.setLiveElements(rings.live ? rings.emOf : null);
      programmer.tick(grid, t, DT);
      if (rings.live) rings.updateMounts(l3d, lasers.heads);
      const l2 = lasers.frame(t);
      rings.drawLasers(lasers, pos);
      const rf = rings.frame(cam);
      l3d.hitOpts = rf.hitOpts;
      const out = l3d.map(l2, { camera: { pos: cam, fwd: [0, 0, -1], near: 0.1 } });
      last = { t, pos, rf, l2, l3: out };
    }
    return last;
  };
  return { grid, programmer, rings, lasers, l3d, step, now: () => f * (1000 / FPS) };
}
const ringCellMean = (programmer) => {
  const T = ringTables(RIG);
  let s = 0;
  for (const x of T.cells) s += programmer.pixels[x.c * 4 + 3];
  return s / T.cells.length;
};

test("MORPH steps the deck on the next bar line; a formation lands on a bar line; the orrery reveals in depth order", () => {
  const S = makeStage();
  S.step(30);
  const r = S.rings.morph(S.grid, S.now());
  assert.equal(r.key, "orrery");
  assert.equal(r.start, 4, "on the next bar line");
  assert.ok(r.posLand % 4 === 0 && r.posLand > r.start && r.dream);
  // the core lights first, then ring 3, ring 0 last (once the look has handed the rings over, 4 beats in)
  let coreAt = null, r3At = null, r0At = null;
  const T = ringTables(RIG);
  const mean = (k) => { const xs = T.cells.filter((x) => x.k === k); return xs.reduce((s, x) => s + S.programmer.pixels[x.c * 4 + 3], 0) / xs.length; };
  for (let i = 0; i < 60 * 30 && !(coreAt && r3At && r0At); i++) {
    const st = S.step(1);
    if (coreAt === null && st.rf.core.level > 0.05) coreAt = st.pos;
    if (st.pos < r.start + 4) continue;
    if (r3At === null && mean(3) > 0.05) r3At = st.pos;
    if (r0At === null && mean(0) > 0.05) r0At = st.pos;
  }
  assert.ok(coreAt !== null && r3At !== null && r0At !== null, JSON.stringify({ coreAt, r3At, r0At }));
  assert.ok(coreAt < r3At && r3At < r0At, `core ${coreAt}, ring 3 ${r3At}, ring 0 ${r0At}`);
  // the next presses: spiral, vortex, crown, portal, home again
  const order = [];
  for (let k = 0; k < 5; k++) order.push(S.rings.morph(S.grid, S.now()).key);
  assert.deepEqual(order, ["spiral", "vortex", "crown", "portal", "home"]);
});

test("HERO fires once per charge (8 bars), lands on the next ONE, through the FlashGate; a refused flash only lifts", () => {
  const S = makeStage({ key: "spiral" });
  S.step(10);
  const a = S.rings.hero(S.grid, S.now());
  assert.ok(a.ok && a.at === 4, JSON.stringify(a));
  assert.equal(S.rings.hero(S.grid, S.now()).why, "armed");
  // before the ONE nothing; on it the discharge (granted: up in one frame), the column at full
  const before = S.step(Math.round(((a.at - 0.05) * 400) / (1000 / FPS)) - 10);
  assert.ok(!(S.rings.hl > 0) && before.pos < a.at);
  let on = null;
  for (let i = 0; i < 20 && !on; i++) { const st = S.step(1); if (S.rings.hl > 0) on = { pos: st.pos, hl: S.rings.hl, col: st.rf.beams[0], sheath: st.rf.beams[1] }; }
  assert.ok(on && on.pos - a.at < 1 / 24 + 1e-9 && on.hl > 0.95, JSON.stringify(on));
  assert.ok(S.programmer.flashGate.grants.includes(a.at), "the FlashGate granted it");
  // the payoff: the needle swells to hero_beam_deg at hero_flux_lm (fix round 1: it had been the needle at 2.9 x its own
  // idle), then narrows back to the needle as the discharge decays
  const Col = SCENE.ring_formations.column, idle = Col.flux_lm * SCENE.ring_formations.spiral.column.level;
  assert.ok(on.col && on.col.flux > 10 * idle && Math.abs(on.col.beamDeg - Col.hero_beam_deg) < 0.2, JSON.stringify(on.col));
  assert.ok(on.sheath && on.sheath.beamDeg === Col.sheath_deg && on.sheath.flux > 0.85 * Col.sheath_flux_lm, "inside its sheath");
  let tail = null;
  for (let i = 0; i < 60 * 3 && !tail; i++) { const st = S.step(1); if (!(S.rings.hl > 0)) tail = st.rf.beams; }
  assert.ok(tail && tail.length === 1 && Math.abs(tail[0].beamDeg - Col.beam_deg) < 1e-9 && Math.abs(tail[0].flux - idle) < 1e-6, `back to the idle needle: ${JSON.stringify(tail)}`);
  // recharging: a press within eight bars is refused
  S.step(60);
  const b = S.rings.hero(S.grid, S.now());
  assert.equal(b.ok, false); assert.equal(b.why, "charging"); assert.equal(b.ready, a.at + 32);
  // a refused grant (another flash took the bar) rises over an eighth of a beat instead of one frame
  const S2 = makeStage({ key: "orrery" });
  S2.step(10);
  const c = S2.rings.hero(S2.grid, S2.now());
  S2.programmer.flashGate.request(c.at - 1);          // a phrase's flash a beat earlier holds the gate
  let lv = [];
  for (let i = 0; i < 400 && lv.length < 8; i++) { S2.step(1); if (S2.rings.hl > 0) lv.push(S2.rings.hl); }
  assert.ok(lv[0] < 0.5 && lv[2] > lv[0], `a lift: ${lv.slice(0, 4).map((v) => v.toFixed(2))}`);
  assert.equal(S2.rings.heroState.fired.at(-1).granted, false);
});

test("the orrery's light is steady: no frame moves the rings' mean level more than 2 % (the shimmer far away, no discharge)", () => {
  const S = makeStage({ key: "orrery" });
  S.step(5);
  let prev = ringCellMean(S.programmer), worst = 0;
  for (let i = 0; i < 60 * 8; i++) { S.step(1); const m = ringCellMean(S.programmer); worst = Math.max(worst, Math.abs(m - prev) / Math.max(1e-6, prev)); prev = m; }
  assert.ok(worst < 0.02, `worst frame-to-frame change ${(worst * 100).toFixed(2)} %`);
  // the spiral's ladder falls down the well each beat, but travelling: the mean over its rings holds within 6 % over a beat
  const P = makeStage({ key: "spiral" });
  P.step(5);
  const ms = [];
  for (let i = 0; i < 24 * 4; i++) { P.step(1); ms.push(ringCellMean(P.programmer)); }
  const lo = Math.min(...ms), hi = Math.max(...ms);
  assert.ok((hi - lo) / hi < 0.06, `the spiral's mean swings ${(((hi - lo) / hi) * 100).toFixed(1)} %`);
});

test("the holographic shimmer wakes as the camera nears and sleeps far away; per cell, so the sum stays steady", () => {
  const far = makeStage({ key: "orrery" }), near = makeStage({ key: "orrery" });
  far.step(10, [0, 8, 60]); near.step(10, [0, 8, 60]);
  const R0 = (S) => { const T = ringTables(RIG); return T.cells.filter((x) => x.k === 0).map((x) => S.programmer.pixels[x.c * 4 + 3]); };
  // put the near camera 3 m from ring 0's rim
  const m = near.rings.ringM[0], rim = [m[9] + m[1] * 14, m[10] + m[4] * 14, m[11] + m[7] * 14];
  near.rings.camera = [rim[0], rim[1] - 3, rim[2] + 1];
  const series = [];
  for (let i = 0; i < 30; i++) { near.step(1, near.rings.camera); far.step(1); series.push(R0(near).reduce((s, v) => s + v, 0)); }
  const a = R0(far), b = R0(near);
  const changed = b.filter((v, i) => Math.abs(v - a[i]) > 1e-3).length;
  assert.ok(changed > 20, `${changed} cells of ring 0 flicker near the camera`);
  const sum = (xs) => xs.reduce((s, v) => s + v, 0);
  assert.ok(sum(b) < sum(a) && sum(b) > 0.6 * sum(a), "it dims a little, never blacks out");
  const swing = (Math.max(...series) - Math.min(...series)) / Math.max(...series);
  assert.ok(swing < 0.1, `the near ring's sum swings ${(swing * 100).toFixed(1)} % across frames`);
});

test("the orrery's scenery: the core, five wireframe bands, eight planets, star motes, inside the renderer's room", () => {
  const S = makeStage({ key: "orrery" });
  const st = S.step(5);
  // the orrery report's 1.2 m core (fix round 1: 0.85 m read as a speck inside a 28 m dial), inside ring 3's 1.5 m hole
  assert.ok(st.rf.core.on && st.rf.core.level > 0.9 && st.rf.core.r === 1.2);
  const r3 = RIG.elements.filter((e) => e.id === "ring")[3].params, bands = SCENE.ring_formations.orrery.core.bands.map((b) => b.r);
  assert.ok(st.rf.core.r < r3.diameter / 2 - r3.depth, "the core fits inside ring 3");
  assert.ok(Math.min(...bands) / 1.2 >= 1.05 && Math.max(...bands) / 1.2 <= 1.8, `the bands at ${bands} hug the core at 1.05-1.8 x`);
  assert.ok(st.rf.emit.n > 1500 && st.rf.emit.n <= MAX_FORMATION_EMIT, `${st.rf.emit.n} emitters`);
  assert.equal(st.rf.hitOpts.orb.r, 1.2);
  // the motes are densest near the core: more within 6 m than between 18 and 24 m (a shell five times the volume)
  let inner = 0, outer = 0;
  for (const m of S.rings.motes) { const d = Math.hypot(m.p[0] - C[0], m.p[1] - C[1], m.p[2] - C[2]); if (d < 6) inner++; else if (d > 18 && d < 24) outer++; }
  assert.ok(inner > outer, `${inner} near the core, ${outer} far`);
  // the spiral hides the core (the well is clear to its vanishing point) and runs the column
  const P = makeStage({ key: "spiral" });
  const sp = P.step(5);
  assert.equal(sp.rf.core.on, false);
  assert.ok(sp.rf.beams.length === 1 && sp.rf.hitOpts === null);
});

test("home is the Qlimax rule: the rings hold still and the formation layer writes nothing", () => {
  const S = makeStage();
  const before = Float32Array.from(S.programmer.pixels);
  S.step(120);
  const R = S.rings;
  assert.equal(R.live, false);
  R.rr.poses.forEach((p, k) => assert.ok(Math.abs(p.tilt - [55, 40, 25, 10][k]) < 1e-9 && p.yaw === 0 && p.spin === 0));
  // a frame of the look with and without the layer is the same
  const tH = new Float64Array(RIG.heads.length * 7).fill(0.5), tC = new Float64Array(RIG.cells.n * 4).fill(0.5);
  R.apply(tH, tC, 30);
  assert.ok(tH.every((v) => v === 0.5) && tC.every((v) => v === 0.5));
  void before;
});

test("live ring mounts: the ring lasers ride ring 0's spin; the halo heads aim at the core through the live pose", () => {
  const S = makeStage({ key: "orrery" });
  S.step(60 * 6);
  const T = ringTables(RIG), L = T.lasers[0];
  const mp = mountPose(S.rings.ringM[0], L.mount);
  const o = S.l3d.p[L.i].pos;
  assert.ok(Math.hypot(o[0] - mp.pos[0], o[1] - mp.pos[1], o[2] - mp.pos[2]) < 1e-9, "the projector's origin is the live mount");
  const home = RIG.projectors[L.i].pos;
  assert.ok(Math.hypot(o[0] - home[0], o[1] - home[1], o[2] - home[2]) > 1, "and ring 0 has spun it away from home");
  // a halo head's beam, at the programmer's slewed pan and tilt, points at the core
  const hp = { lens: [0, 0, 0], dir: [0, 0, 0] };
  for (const h of T.heads.filter((x) => x.k === 0).slice(0, 6)) {
    const f = RIG.fixtures[h.fi], b = h.h * HEAD_FLOATS;
    headPose(S.rings.ringM[0], f, S.programmer.heads[b + H.PAN], S.programmer.heads[b + H.TILT], hp);
    const to = [C[0] - hp.lens[0], C[1] - hp.lens[1], C[2] - hp.lens[2]], l = Math.hypot(...to);
    const cos = (to[0] * hp.dir[0] + to[1] * hp.dir[1] + to[2] * hp.dir[2]) / l;
    assert.ok(cos > Math.cos((1.5 * Math.PI) / 180), `head ${h.h} is ${(Math.acos(Math.min(1, cos)) * 180 / Math.PI).toFixed(2)} degrees off the core`);
  }
});

test("aimInto agrees with rig.js aimAt without allocating", async () => {
  const { aimAt } = await import("../arsenal/web/stage/rig.js");
  const T = ringTables(RIG), out = [0, 0];
  for (const h of T.heads.slice(0, 20)) {
    const em = elementMatrix(RIG.elements[RIG.fixtures[h.fi].element], { tilt: 70, yaw: 33, spin: 12 });
    const tgt = [3, 20, 5];
    const a = aimAt(em, RIG.fixtures[h.fi], tgt, { panHint: 10 });
    aimInto(em, h, tgt, 10, out);
    assert.ok(Math.abs(a.pan - out[0]) < 1e-9 && Math.abs(a.tilt - out[1]) < 1e-9, `${a.pan},${a.tilt} vs ${out}`);
  }
});

test("the camera's views of every formation resolve and are clear before anything renders (amendment 6)", () => {
  const V = SCENE.cameras.formation_views, R = new RingFormations(RIG), model = cameraModel(RIG);
  const ringKeys = R.formations.filter((k) => k !== "home");
  // each view key names a ring formation, a set formation, a strand shape or a kinetics formation
  const kinetics = (k) => { try { formationTarget(k, {}, 0, 12, 0); return true; } catch { return false; } };
  for (const key of Object.keys(V)) {
    if (key.startsWith("_")) continue;
    assert.ok(ringKeys.includes(key) || RIG.formations[key] || RIG.strandShapes[key] || kinetics(key), `formation_views.${key} resolves`);
  }
  for (const k of ringKeys) assert.ok(V[k] && V[k].hero.length, `the ring formation ${k} has a hero view`);
  // the ring formations' shots, judged as the stage judges them: against the rings each sweeps and every strand formation
  const strandSets = [].concat(...Object.values(RIG.formations).map((f) => formationPoseSets(f, model.z.length) || []));
  const d = new Director(SCENE.cameras.shots, SCENE.cameras.sequences, {
    model, formations: { ...RIG.formations, ...Object.fromEntries(ringKeys.map((k) => [k, R.def(k)])) }, views: V, safe: SCENE.cameras.safe,
    posesOf: (key, def) => (ringKeys.includes(key) ? strandSets : formationPoseSets(def, model.z.length)), ringsOf: (key) => (ringKeys.includes(key) ? R.annuliSets(key) : null),
    sightOf: (key) => (ringKeys.includes(key) ? R.sight(key) : null) });
  for (const k of ringKeys) {
    const ok = d.validFor(k);
    assert.ok(ok, `${k} is judged`);
    for (const id of [...V[k].glide, ...V[k].hero]) {
      assert.ok(ok.has(id), `${k}: ${id} clears the rings it sweeps and the strand by ${CLEARANCE_M} m`);
      assert.ok(!SCENE.cameras.shots[id].placeholder, `${id} is retuned (no placeholder left)`);
    }
  }
  // the spiral's hero looks up the well: its rings, stepped up the axis, all in front of the lens
  const sets = R.annuliSets("spiral");
  assert.ok(shotRingClearance(SCENE.cameras.shots.SPIRAL_HERO, sets) >= CLEARANCE_M);
});

test("the orrery is never shot through the rig: its views see the heart whole, and the director keeps the blocked views off it", () => {
  // fix round 1: the PA hang at x = -5 covered the lower half of the core in ORRERY_HERO, two hangs flanked it in the
  // landing glide, Bank A's truss crossed it in the high arc; HEAD_ORBIT (a drop and groove shot) put two slabs over it
  const R = new RingFormations(RIG), V = SCENE.cameras.formation_views.orrery, hero = R.sight("orrery", { hero: true });
  assert.ok(hero && hero.r === 3 && hero.boxes.some((b) => b.what === "pa") && hero.boxes.some((b) => b.what === "bank-a"));
  // ... and the composition: no more of the frame given to hangs and trusses than the front-of-house wide gives (6.3 %)
  for (const id of [...V.glide, ...V.hero]) {
    const s = shotSight(SCENE.cameras.shots[id], hero), f = shotStructure(SCENE.cameras.shots[id], hero.boxes);
    assert.equal(s.worst, 0, `${id}: ${(s.worst * 100).toFixed(0)} % of the heart behind the hall's structure on its worst frame`);
    assert.ok(f <= 0.07, `${id}: the hall's structure fills ${(f * 100).toFixed(1)} % of its frame`);
  }
  // the first ORRERY_HERO, for the record: the hang over the heart on every frame, 13 % of the frame black slab
  const old = { kind: "static", pos: [-15, 21, 21], look: [0, 15, -11], hfov: 46 };
  assert.ok(shotSight(old, hero).worst > 0 && shotStructure(old, hero.boxes) > 0.12);
  // the director, while the orrery stands: HEAD_ORBIT hides close to half the core on average, so it is not dealt; the
  // front-of-house wides see it whole
  const d = new Director(SCENE.cameras.shots, SCENE.cameras.sequences, { model: cameraModel(RIG), formations: { orrery: R.def("orrery") },
    safe: SCENE.cameras.safe, posesOf: () => null, ringsOf: () => null, sightOf: (key) => R.sight(key) });
  const ok = d.validFor("orrery");
  assert.ok(shotSight(SCENE.cameras.shots.HEAD_ORBIT, R.sight("orrery")).mean > 0.25);
  assert.equal(ok.has("HEAD_ORBIT"), false);
  for (const id of ["FOH_WIDE", "HALO_LOCK", ...V.glide, ...V.hero]) assert.ok(ok.has(id), id);
  assert.equal(d.deal("HEAD_ORBIT", ["orrery"]) !== "HEAD_ORBIT", true, "HEAD_ORBIT is swapped for a stand-in");
  // fix round 2: TRIBUNE_HIGH_R (groove, drop-v2) has the x = +5 PA hang over the core's lower half on every frame of its
  // move (22 %, under the old quarter): it is swapped too; no shot the director may deal hides more than 15 %
  const tr = shotSight(SCENE.cameras.shots.TRIBUNE_HIGH_R, R.sight("orrery"));
  assert.ok(tr.mean > 0.15 && tr.worst > 0.15, `TRIBUNE_HIGH_R hides ${(tr.mean * 100).toFixed(0)} % of the core`);
  assert.equal(ok.has("TRIBUNE_HIGH_R"), false);
  assert.equal(d.deal("TRIBUNE_HIGH_R", ["orrery"]) !== "TRIBUNE_HIGH_R", true, "TRIBUNE_HIGH_R is swapped for a stand-in");
  for (const id of ok) assert.ok(shotSight(SCENE.cameras.shots[id], R.sight("orrery")).mean <= 0.15, `${id} may be dealt over the orrery`);
  // a formation without a core asks nothing of the sightlines
  assert.equal(R.sight("spiral"), null);
});
