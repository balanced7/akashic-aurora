// The spectacle wides (source-v1.json cameras): ten full-set shots, zoomed out so the rings and the whole rig read as one
// picture. Daniel, 2026-10-29: "also can we add some more full set spectacle camera positions, i think a lot of ours are
// close and we dont have many good zoom out ones so i can appreciate the crazy ring effects and full set magic".
// Pins (fix round 1: each measured where the director really plays it, not where a list names it):
//   the ten are in the set, quote him, and follow FOH_WIDE in the shot table (C from the front-of-house wide walks them);
//   each keeps the WHOLE rig in frame at every u (the halo, both towers and laser trusses, the strand from its first rung
//   to its last, the crowd's edge) and every ring formation's rings, 40 m or more from the rings, with the ring core clear
//   of the hall's structure and of the strand; each static is its own picture, not an existing shot's;
//   the real order of play reaches them: the demo's drop and break windows (the phrase owns the drop's first 16 bars),
//   the groove from its first bars (engine mode restarts it after every drop), the ring morphs' first deck cycle;
//   every cut they take part in, there (the phrase's last shot into the drop, the sections' ends at their real u, the
//   landings' glide into hero), keeps the 30-degree rule and the strand's axis;
//   they fly within the drone's limits (15 m/s, 5 m/s^2 over a quarter second) wherever they play, at 150 and 175 BPM.
//   node --test tests/stage_spectacle.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Director, DRONE, cameraModel, formationPoseSets, isJumpCut, prepareShot, shotPose, segmentHitsBox, viewBlocked } from "../arsenal/web/stage/camera.js";
import { expandScene, hallStructure } from "../arsenal/web/stage/rig.js";
import { RingFormations } from "../arsenal/web/stage/formations.js";
import { askedShot } from "../arsenal/web/stage/stills.js";

const V1 = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG = expandScene(V1), MODEL = cameraModel(RIG), CAM = V1.cameras, SHOW = V1.show;
const SPECTACLE = ["SPEC_EDGE_MID_L", "SPEC_CORNER_LOW_R", "SPEC_HALL_CORNER_REAR_L", "SPEC_HALL_CORNER_FRONT_R", "SPEC_HALL_SIDE_PANO",
  "SPEC_HALL_ORBIT", "SPEC_HALL_REAR_DRIFT", "SPEC_HALL_PULLBACK", "SPEC_GRAND_ARC", "SPEC_SPIRAL_RISE"];
// the pull-back opens high over the strand's head, 26 m from the rings' centre with the rings filling the frame: the whole
// rig is in its frame from u 0.6, and it rides the strand's axis looking down it (the strand over the rings is the move)
const FRAMED_FROM = { SPEC_HALL_PULLBACK: 0.6 }, ON_THE_AXIS = new Set(["SPEC_HALL_PULLBACK"]);
const pose0 = () => ({ pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 });
const shot1 = (id) => prepareShot({ id, ...CAM.shots[id] });
const P = (id, u) => shotPose(shot1(id), u, 0, pose0());
const DEG = Math.PI / 180;
const US = Array.from({ length: 11 }, (_, i) => i / 10);

// ------------------------------------------------------------------------------------------------ geometry --
const ring0 = MODEL.rings.reduce((a, b) => (b.outer > a.outer ? b : a), MODEL.rings[0]);
const up = [0, ring0.normal[2], -ring0.normal[1]];
const at = (c, d, k) => c.map((v, i) => v + d[i] * k);
const hy = MODEL.homeY, zF = MODEL.z[0], zL = MODEL.z[MODEL.z.length - 1];
const WHOLE_RIG = {
  "halo top": at(ring0.centre, up, ring0.outer), "halo bottom": at(ring0.centre, up, -ring0.outer),
  "halo left": at(ring0.centre, [1, 0, 0], -ring0.outer), "halo right": at(ring0.centre, [1, 0, 0], ring0.outer),
  "rings centre": ring0.centre.slice(), "strand first rung": [0, hy, zF], "strand last rung": [0, hy, zL],
  "strand first rung's ends": [-5, hy, zF], "strand first rung's other end": [5, hy, zF],
  "strand last rung's ends": [-5, hy, zL], "strand last rung's other end": [5, hy, zL],
  "tower L top": [-22, 16, -2], "tower R top": [22, 16, -2], "laser truss L": [-22, 22, -2], "laser truss R": [22, 22, -2],
  "crowd front": [0, 1.9, 6],
};
function basis(p) {
  const f = [0, 1, 2].map((k) => p.look[k] - p.pos[k]), fl = Math.hypot(...f);
  for (let i = 0; i < 3; i++) f[i] /= fl;
  const rl = Math.hypot(f[2], f[0]), r = [-f[2] / rl, 0, f[0] / rl];
  return { f, r, u: [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]] };
}
function inFrame(pose, q, margin = 1, aspect = 16 / 9) {
  const { f, r, u } = basis(pose), d = [0, 1, 2].map((k) => q[k] - pose.pos[k]), z = d[0] * f[0] + d[1] * f[1] + d[2] * f[2];
  if (z < 0.5) return false;
  const tanH = Math.tan((pose.hfov * DEG) / 2) * margin, tanV = tanH / aspect;
  return Math.abs((d[0] * r[0] + d[1] * r[1] + d[2] * r[2]) / z) <= tanH && Math.abs((d[0] * u[0] + d[1] * u[1] + d[2] * u[2]) / z) <= tanV;
}
const turn = (a, b) => { const fa = basis(a).f, fb = basis(b).f; return Math.acos(Math.max(-1, Math.min(1, fa[0] * fb[0] + fa[1] * fb[1] + fa[2] * fb[2]))) / DEG; };
function rim(g, n = 24, r = g.outer) {
  const nn = g.normal, a = Math.abs(nn[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
  let e1 = [a[1] * nn[2] - a[2] * nn[1], a[2] * nn[0] - a[0] * nn[2], a[0] * nn[1] - a[1] * nn[0]];
  const l = Math.hypot(...e1); e1 = e1.map((v) => v / l);
  const e2 = [nn[1] * e1[2] - nn[2] * e1[1], nn[2] * e1[0] - nn[0] * e1[2], nn[0] * e1[1] - nn[1] * e1[0]];
  return Array.from({ length: n }, (_, i) => { const t = (2 * Math.PI * i) / n; return [0, 1, 2].map((k) => g.centre[k] + r * (Math.cos(t) * e1[k] + Math.sin(t) * e2[k])); });
}
const RF = new RingFormations(RIG), RING_KEYS = RF.formations.filter((k) => k !== "home");
const HALL = (() => { const h = hallStructure(V1.venue); return [...h.solid, ...h.truss].filter((b) => b.what !== "deck"); })();
// the strand's rungs at home as boxes round each rung's diamond and arms (an upper bound on what they hide)
const RUNGS = MODEL.z.map((z) => ({ c: [0, hy, z], s: [10.1, 1.52, 1.12] }));
const RIMS = MODEL.rings.flatMap((g) => rim(g, 36, g.outer - 0.45));
const behindStrand = (p) => RIMS.filter((q) => RUNGS.some((b) => segmentHitsBox(p.pos, q, b))).length / RIMS.length;
// a picture of its own: the view's turn, the rig's size in frame and the lens's place, against every existing shot
const rigSize = (p) => 1 / (Math.hypot(...[0, 1, 2].map((k) => p.pos[k] - ring0.centre[k])) * Math.tan((p.hfov * DEG) / 2));
function sameness(a, b) {
  const sz = Math.max(rigSize(a), rigSize(b)) / Math.min(rigSize(a), rigSize(b));
  return turn(a, b) / 12 + Math.log(sz) / Math.log(1.35) + Math.hypot(...[0, 1, 2].map((k) => a.pos[k] - b.pos[k])) / 30;
}
// the drone's limits over the move's own time: peak speed, and acceleration over a quarter second
function motion(s, bars, bpm) {
  const T = (bars * 4 * 60) / bpm, n = Math.max(60, Math.round(T * 60)), dt = T / n, X = [];
  for (let i = 0; i <= n; i++) X.push(shotPose(s, i / n, 0, pose0()).pos.slice());
  const V = []; for (let i = 1; i <= n; i++) V.push([0, 1, 2].map((k) => (X[i][k] - X[i - 1][k]) / dt));
  let vmax = 0, amax = 0; const k = 15;
  for (const v of V) vmax = Math.max(vmax, Math.hypot(...v));
  for (let i = k; i < V.length; i++) amax = Math.max(amax, Math.hypot(...[0, 1, 2].map((j) => (V[i][j] - V[i - k][j]) / (k * dt))));
  return { vmax, amax };
}
const side = (p) => (p.pos[0] < -3 ? "L" : p.pos[0] > 3 ? "R" : "A");
function cleanCut(where, a, ua, b, ub) {
  const pa = P(a, ua), pb = P(b, ub);
  assert.ok(!isJumpCut(pa, pb), `${where}: ${a}@${ua.toFixed(2)} -> ${b}@${ub} is a jump cut (turn ${turn(pa, pb).toFixed(1)})`);
  const s = side(pa) + side(pb);
  assert.ok(s !== "LR" && s !== "RL", `${where}: ${a} -> ${b} crosses the strand's axis (${s})`);
}

// ------------------------------------------------------------------------------- the real order of play --
// stage.js: a section starts its camera sequence on its first bar; a section's phrase (show.sections.*.phrase) owns the
// camera for its length and, when it ends, the section's sequence starts again from its first entry (phraseEnded).
const SEQ = CAM.sequences;
const phraseOf = (sec) => { const ph = sec.phrase && V1.phrases[sec.phrase.name]; return ph ? { bars: (ph.steps.reduce((a, s) => a + s.beats, 0) * (sec.phrase.repeats ?? 1)) / 4, last: ph.steps.at(-1).camera.shot } : null; };
function played(seq, bars) {
  const r = []; let acc = 0;
  for (let k = 0; acc < bars - 1e-9; k = (k + 1) % seq.length) { const e = seq[k], len = Math.min(e.bars, bars - acc); r.push({ shot: e.shot, bars: len, u1: len / e.bars }); acc += len; }
  return r;
}
const DEMO = SHOW.demo.plan.map((p) => {
  const sec = SHOW.sections[p.section], ph = phraseOf(sec), own = p.bars - (ph ? ph.bars : 0);
  return { name: p.section, phrase: ph, plays: played(SEQ[sec.camera], own) };
});
const DROP = SHOW.sections.drop, DROP_PH = phraseOf(DROP);
const ENGINE_DROP = played(SEQ[DROP.camera], DROP.bars - DROP_PH.bars);
const wideBars = (plays) => plays.filter((e) => SPECTACLE.includes(e.shot)).reduce((a, e) => a + e.bars, 0);
// the ring morphs: two cycles of the set's deck through the director's own landing logic
const strandSets = [].concat(...Object.values(RIG.formations).map((f) => formationPoseSets(f, MODEL.z.length) || []));
const director = () => new Director(CAM.shots, CAM.sequences, {
  model: MODEL, formations: { ...RIG.formations, ...Object.fromEntries(RING_KEYS.map((k) => [k, RF.def(k)])) }, views: CAM.formation_views, safe: CAM.safe,
  posesOf: (key, def) => (RING_KEYS.includes(key) ? strandSets : formationPoseSets(def, MODEL.z.length)),
  ringsOf: (key) => (RING_KEYS.includes(key) ? RF.annuliSets(key) : null), sightOf: (key) => (RING_KEYS.includes(key) ? RF.sight(key) : null) });
function morphs(presses) {
  const d = director(), deck = V1.ring_formations.deck, grid = { period: 400, nextBarPos: (p) => Math.ceil(p / 4 - 1e-9) * 4 };
  d.start("groove", 0); d.formationKey = "high-wave";
  let cur = "home"; const out = [];
  for (let press = 1; press <= presses; press++) {
    const next = deck[(deck.indexOf(cur) + 1) % deck.length], rf = new RingFormations(RIG);
    if (cur !== "home") rf.set(cur, 0, 150);
    const pos = press * 256 + 2, r = rf.go(next, { ...grid, posAt: () => pos }, 0);
    d.formationPrev = cur === "home" ? "high-wave" : cur; d.formationKey = next === "home" ? "high-wave" : next; d.formationDef = RF.def(next);
    const e = next === "home" ? null : d.landing(next, pos, r.posLand);
    if (e) out.push({ press, formation: next, glide: e.find((x) => x.why === "landing-glide"), hero: e.find((x) => x.why === "landing-hero") });
    d.planEntries = null; cur = next;
  }
  return out;
}
const CYCLE = V1.ring_formations.deck.length, LANDINGS = morphs(2 * CYCLE);

// ------------------------------------------------------------------------------------------------- tests --
test("the ten spectacle wides are in the set, quote Daniel, none is held, and they follow FOH_WIDE in the shot table", () => {
  for (const id of SPECTACLE) {
    const def = CAM.shots[id];
    assert.ok(def, `${id} is in source-v1.json cameras.shots`);
    assert.ok(!def.held, `${id} is not held`);
    assert.ok(def.source.includes("so i can appreciate the crazy ring effects and full set magic"), `${id}: its source quotes Daniel`);
  }
  assert.deepEqual(Object.keys(CAM.shots).filter((k) => k.startsWith("SPEC_")).sort(), [...SPECTACLE].sort(), "exactly the ten");
  for (const id of ["FOH_WIDE", "ROOF_ESTABLISH", "REAR_TELE_ZIGGURAT", "HIGH_REAR_CRANE", "HALO_ORBIT", "HALO_LOCK", "TRIBUNE_34", "TRIBUNE_HIGH_R"]) assert.ok(CAM.shots[id], id);
  assert.equal(Object.keys(CAM.shots).length, 58);
  // C (stage.js KeyC) steps to the next id of the director's table from the shot on screen: from the front-of-house wide
  // (the intro's and the groove's opening shot is FOH_HOLD_ZOOM, the one before it) the next ten presses are the ten
  const ids = Object.keys(new Director(CAM.shots, CAM.sequences).shots), i = ids.indexOf("FOH_WIDE");
  assert.deepEqual(ids.slice(i + 1, i + 11), SPECTACLE);
  // ?shot=ID forces any one of them by hand, as C does
  for (const id of SPECTACLE) assert.deepEqual(askedShot(new URLSearchParams(`shot=${id}`), CAM.shots), { id, u: null });
});

test("each keeps the whole rig in one picture at every u, every ring formation's rings too, 40 m or more out", () => {
  const ringSets = { home: [MODEL.rings] };
  for (const k of RING_KEYS) ringSets[k] = RF.annuliSets(k);
  for (const id of SPECTACLE) {
    const s = shot1(id), from = FRAMED_FROM[id] ?? 0;
    for (const u of US) {
      if (u < from - 1e-9) continue;
      const p = shotPose(s, u, 0, pose0());
      const missing = Object.entries(WHOLE_RIG).filter(([, q]) => !inFrame(p, q, 0.97)).map(([k]) => k);
      assert.deepEqual(missing, [], `${id} at u ${u}: out of frame`);
      for (const [k, sets] of Object.entries(ringSets)) for (const rings of sets) {
        const out = rings.flatMap((g) => rim(g)).filter((q) => !inFrame(p, q));
        assert.equal(out.length, 0, `${id} at u ${u}: ${out.length} rim points of the ${k} rings out of frame`);
      }
      assert.ok(Math.hypot(...[0, 1, 2].map((k) => p.pos[k] - ring0.centre[k])) >= 40, `${id} at u ${u} is close`);
    }
  }
});

test("the ring core stays clear of the hall's structure and of the strand; each static is its own picture", () => {
  const existing = Object.entries(CAM.shots).filter(([k, d]) => !k.startsWith("SPEC_") && !d.held && d.kind !== "strand")
    .flatMap(([k]) => [0, 0.5, 1].map((u) => ({ id: `${k}@${u}`, p: P(k, u) })));
  for (const id of SPECTACLE) {
    const s = shot1(id), occ = [];
    for (const u of US) {
      const p = shotPose(s, u, 0, pose0());
      // the PA hangs and trusses in front of the inner ring (viewBlocked: the share of the core hidden)
      const hall = viewBlocked(p.pos, ring0.centre, 3.45, HALL, 16);
      assert.ok(hall <= 0.2, `${id} at u ${u}: ${(hall * 100).toFixed(0)} % of the ring core behind the hall's structure`);
      occ.push(behindStrand(p));
    }
    const mean = occ.reduce((a, b) => a + b, 0) / occ.length;
    if (CAM.shots[id].kind === "static") assert.ok(Math.max(...occ) <= 0.2, `${id}: ${(Math.max(...occ) * 100).toFixed(0)} % of the rings' rims behind the strand`);
    else if (!ON_THE_AXIS.has(id)) assert.ok(mean <= 0.2, `${id}: on average ${(mean * 100).toFixed(0)} % of the rings' rims behind the strand`);
    if (CAM.shots[id].kind === "static") {
      const p = P(id, 0.5), near = existing.map((e) => ({ id: e.id, v: sameness(p, e.p) })).sort((a, b) => a.v - b.v)[0];
      assert.ok(near.v >= 2, `${id} is ${near.id}'s picture again (${near.v.toFixed(2)})`);
    }
  }
});

test("the real order of play reaches them: the demo's drop and break, the groove from its first bars, the first ring morphs", () => {
  const drop = DEMO.find((s) => s.name === "drop"), brk = DEMO.find((s) => s.name === "break");
  assert.ok(drop.phrase && drop.phrase.bars === 16, "the drop's phrase owns its first 16 bars");
  // the drop's own 8 bars (its peak: the beams and lasers from bar 16) hold a 4-bar wide; the break's 8 a whole move
  assert.ok(wideBars(drop.plays) >= 4, `the demo's drop plays ${JSON.stringify(drop.plays)}`);
  assert.ok(brk.plays.some((e) => SPECTACLE.includes(e.shot) && e.bars >= 6 && e.u1 === 1), `the demo's break plays ${JSON.stringify(brk.plays)}`);
  // engine mode: the groove starts again from its first bar after every drop, so the wides come early
  const g8 = played(SEQ.groove, 8), g32 = played(SEQ.groove, 32);
  assert.ok(g8.some((e) => SPECTACLE.includes(e.shot)), "a wide within the groove's first 8 bars");
  assert.ok(new Set(g32.map((e) => e.shot).filter((id) => SPECTACLE.includes(id))).size >= 3, "three wides within its first 32 bars");
  assert.ok(wideBars(ENGINE_DROP) >= 4, "the engine's drop holds a wide too");
  // the ring morphs: the first cycle of the deck lands on two wides
  const first = LANDINGS.filter((l) => l.press <= CYCLE).flatMap((l) => [l.glide && l.glide.shot, l.hero.shot]).filter((id) => SPECTACLE.includes(id));
  assert.ok(new Set(first).size >= 2, `the first deck cycle deals ${first}`);
  // and every one is reached somewhere a show really goes: the demo, the groove, two deck cycles
  const reached = new Set([...DEMO.flatMap((s) => s.plays.map((e) => e.shot)), ...SEQ.groove.map((e) => e.shot),
    ...LANDINGS.flatMap((l) => [l.glide && l.glide.shot, l.hero.shot])]);
  for (const id of SPECTACLE) assert.ok(reached.has(id), `${id} is reached`);
  // a strand shape is landed once from ?strand= (its first hero only): no wide waits at the end of one of their lists
  for (const k of ["ramp", "stairs", "valley", "arch"]) for (const id of CAM.formation_views[k].hero.slice(1)) assert.ok(!SPECTACLE.includes(id), `${k}: ${id}`);
});

test("their cuts keep the 30-degree rule and the strand's axis where the director really makes them", () => {
  for (const name of ["drop", "break", "groove"]) {
    const seq = SEQ[name];
    for (let i = 0; i < seq.length; i++) {
      const a = seq[i].shot, b = seq[(i + 1) % seq.length].shot;
      if (SPECTACLE.includes(a) || SPECTACLE.includes(b)) cleanCut(`${name}[${i}]`, a, 1, b, 0);
    }
  }
  // the phrase's last shot into the drop's sequence (fix round 1: HALO_ORBIT -> the corner was a 28-degree jump)
  cleanCut("phrase -> drop", DROP_PH.last, 1, SEQ[DROP.camera][0].shot, 0);
  // the sections' ends at the u the section cuts them (the demo loops; the engine's drop hands back to the groove)
  for (let i = 0; i < DEMO.length; i++) {
    const a = DEMO[i].plays.at(-1), nx = DEMO[(i + 1) % DEMO.length], b = nx.phrase ? nx.phrase : nx.plays[0];
    if (!nx.phrase && (SPECTACLE.includes(a.shot) || SPECTACLE.includes(b.shot))) cleanCut(`demo ${DEMO[i].name} -> ${nx.name}`, a.shot, a.u1, b.shot, 0);
  }
  cleanCut("engine drop -> groove", ENGINE_DROP.at(-1).shot, ENGINE_DROP.at(-1).u1, SEQ.groove[0].shot, 0);
  // the landings: the glide's end into the hero, two cycles of the deck
  let n = 0;
  for (const l of LANDINGS) if (l.glide && (SPECTACLE.includes(l.glide.shot) || SPECTACLE.includes(l.hero.shot))) { cleanCut(`press ${l.press} ${l.formation}`, l.glide.shot, 1, l.hero.shot, 0); n++; }
  assert.ok(n >= 4, `${n} landings with a wide`);
});

test("they fly within the drone's limits wherever they play: 15 m/s and 5 m/s^2, at 150 and 175 BPM", () => {
  const where = [];
  for (const id of SPECTACLE) where.push([id, CAM.shots[id].bars ?? 4, "its own bars (C)"]);
  for (const name of ["drop", "break", "groove"]) for (const e of SEQ[name]) if (SPECTACLE.includes(e.shot)) where.push([e.shot, e.bars, name]);
  for (const l of LANDINGS) if (l.glide && SPECTACLE.includes(l.glide.shot)) where.push([l.glide.shot, (l.glide.p1 - l.glide.p0) / 4, `${l.formation} glide`]);
  for (const [id, bars, ctx] of where) for (const bpm of [150, 175]) {
    const m = motion(shot1(id), bars, bpm);
    assert.ok(m.vmax <= DRONE.vmax, `${id} (${ctx}, ${bars} bars at ${bpm}): ${m.vmax.toFixed(1)} m/s`);
    assert.ok(m.amax <= DRONE.amax, `${id} (${ctx}, ${bars} bars at ${bpm}): ${m.amax.toFixed(1)} m/s^2`);
  }
});
