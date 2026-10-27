// Virtual Stage v2, the ring formations: arsenal/web/stage/formations.js (pure ES module: no DOM, no WebGL). Tests:
// tests/stage_formations.test.mjs.
//
// Daniel, 2026-10-27: "we could have the light rings morph possibly and re-arrange into other patterns ... or they form
// some sort of spiral with an energy beam inside, or perhaps an array that looks similar to the [Destiny place] ... the
// indoor thing with the glyphs and the stars". And of that place (the Dreaming City's orrery): "Just really complex
// motion that you could stare at for a long time and not get bored" / "how it flickers when you get close to it" /
// "wireframe elements" / "the effect on a spinning ring and how it's moving" / "it looks beautiful no matter where you
// look at it from" / "the way it gets revealed, but it has depth".
//
// The four Qlimax rings, re-arranged. A formation is DATA (the scene's ring_formations): each ring's pose (tilt, lift,
// and in DREAM formations the continuous rotators: yaw about the vertical, spin about the ring's own normal, axial travel
// along it), the order its rings reveal in, and the numbers of its light. This module plays them:
//   home    the Qlimax 2014 spiral (55 / 40 / 25 / 10): the ring is still, the looks own the light (the 2014 rule).
//   orrery  DREAM. The rings tilt apart into nested gimbals round a glowing violet core (a meridian line, a dotted
//           equator, port lights) and turn at incommensurate rates (prime beats per turn: 113 / 89 / 67 / 37, so each
//           is beat-locked and the set repeats after about 25 million beats); five thin wireframe bands hug the core at
//           their own rates; planets ride the rings on short arms; star motes hang in the haze, densest near the core;
//           the line-work shimmers as the camera comes near; it reveals in depth order, core first, outer ring last.
//   spiral  DREAM, the orrery's sister (the Well of Rings): the rings coplanar at 55 degrees and stepped up their shared
//           axis (a true funnel), each lit on a 300-degree arc whose 60-degree gap steps round ring by ring into a spiral
//           staircase that turns; a ladder chase falls down the well each beat; the ENERGY BEAM runs up the axis, wrapped
//           in a twisted cage of the ring lasers.
//   vortex  08, real-capable: the rings at home; every halo head aims at a circle round the axis turned by an offset
//           that swings +-60 degrees: a twisted cone of beams round the axial beam.
//   crown   09, real-capable: rings 1 and 2 tilt flat; their heads aim up at circles on the roof turned +D and -D: two
//           families of straight beams weave a hyperboloid lattice, cylinder to hourglass to knot and back.
//   portal  10, real-capable after the lift: the cluster lifts 4.5 m before ring 0 tilts upright, its heads converge on
//           a point behind it, a membrane of crossing beams (it needs the lift: at its hang ring 0 cannot pass 47).
// The MORPH pad steps to the next formation in the deck, starting on the next bar line (rigs move on time priority,
// rings.js / kinetics.js RingRig); the HERO pad fires the charged payoff -- the energy beam's discharge up the axis
// through the core -- once per charge_bars, landing on the next ONE, its flash through the stage's FlashGate.
//
// Safety: every beam a formation owns ends on the roof, the deck, the floor upstage of it, the back wall or the core
// (beamEnds; pinned): never on the crowd or the audience stands (lasers3d.js roomHit with the stands). The light layer
// writes TARGETS (programmer.setLayer): the heads still turn no faster than their motors. Inspiration only: nothing of
// Bungie's is copied; the geometry and the numbers are our own design, informed by the orrery report's measurements.

import { elementMatrix, mountPose, ringTiltWindow, ringEnvelope, annulusOf, annulusGap, headPose, eulerToMat3 } from "./rig.js";
import { RingRig } from "./kinetics.js";
import { presetTarget, preparePreset } from "./phrases.js";
import { roomHit } from "./lasers3d.js";
import { ringAnnulus } from "./camera.js";

export const FORMATIONS_API = "arsenal.stage-formations/v1";
export const MAX_FORMATION_EMIT = 4096;      // the renderer's extra emitter room (bands, planets, motes, the core's dots)
export const MAX_FORMATION_BEAMS = 4;        // and its extra beam proxies (the energy column)
export const ROLE = Object.freeze({ A: 0, B: 1, W: 2, beamA: 3, beamB: 4, warm: 5, bumpA: 6, bumpB: 7 });
const DEG = Math.PI / 180, TAU = Math.PI * 2;
const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const frac = (x) => x - Math.floor(x);
const smooth = (a, b, x) => { const t = clamp01((x - a) / (b - a || 1e-9)); return t * t * (3 - 2 * t); };
// a window [a, b] of beats (from the move's first bar) as a 0..1 ramp
const ramp = (w, x) => (w ? smooth(w[0], w[1], x) : 1);
function hash(a, b = 0) { let h = Math.imul(a ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(b + 0x632be5ab, 0xc2b2ae35); h ^= h >>> 15; h = Math.imul(h, 0x27d4eb2d); return ((h ^ (h >>> 13)) >>> 0) / 4294967296; }
function rngOf(seed) { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

// ------------------------------------------------------------------------------------------------- validation --
export function validateRingFormations(rig) {
  const errs = [], F = rig.ringFormations || {};
  const rings = rig.elements.filter((e) => e.id === "ring");
  for (const key of F.deck || []) if (!F[key]) errs.push(`ring_formations.deck: no formation ${key}`);
  for (const [key, def] of Object.entries(F)) {
    if (key.startsWith("_") || ["deck", "centre", "hero", "column"].includes(key)) continue;
    if (!def || !Array.isArray(def.rings) || def.rings.length !== rings.length) { errs.push(`ring_formations.${key}.rings: one entry per ring (${rings.length})`); continue; }
    for (const [k, r] of def.rings.entries()) {
      if (!def.dream && (r.yaw || r.yaw_beats || r.spin || r.spin_beats || r.axial)) errs.push(`ring_formations.${key}.rings[${k}]: yaw, spin and axial travel are dream-only (a 3-point hung ring only lifts and tilts)`);
      if (r.tilt !== undefined && !(r.tilt >= 0 && r.tilt <= 90)) errs.push(`ring_formations.${key}.rings[${k}].tilt: 0..90`);
    }
  }
  return errs;
}

// ----------------------------------------------------------------------------------------------- the geometry --
// What the formation module needs of the rig, computed once: the rings (elements), their cells, their halo heads, the
// ring-mounted lasers and the hero laser.
export function ringTables(rig) {
  const ringEls = [];
  rig.elements.forEach((e, i) => { if (e.id === "ring") ringEls.push(i); });
  const ringOf = new Int32Array(rig.elements.length).fill(-1);
  ringEls.forEach((e, k) => { ringOf[e] = k; });
  // cells: ring k, kind (0 slat, 1 outer rim, 2 inner rim), slat number 0..47, cell along the slat 0..7 (inner first),
  // polar angle (radians), and a radius rank across the whole cluster (0 = R0's outer rim .. 1 = R3's inner rim)
  const cells = [];
  for (let c = 0; c < rig.cells.n; c++) {
    const k = ringOf[rig.cells.element[c]];
    if (k < 0) continue;
    const f = rig.fixtures[rig.cells.fixture[c]], el = rig.elements[rig.cells.element[c]];
    const px = rig.cells.pos[c * 3], py = rig.cells.pos[c * 3 + 1], r = Math.hypot(px, py);
    const outer = el.params.diameter / 2, inner = outer - el.params.depth;
    const slat = f.type === "slat-8";
    const kind = slat ? 0 : Math.abs(r - outer) < Math.abs(r - inner) ? 1 : 2;
    const a = Math.atan2(py, px);
    cells.push({ c, k, kind, slat: slat ? ((Math.round(f.angle / (7.5 * DEG)) % 48) + 48) % 48 : -1, along: slat ? c - f.cell0 : -1, angle: a, r });
  }
  const rMax = Math.max(...cells.map((x) => x.r)) + 0, rings = ringEls.map((e) => rig.elements[e]);
  // the radius rank: R0 outer = 0 ... the innermost = 1 (by the ring's nesting, then the radius inside the ring)
  for (const x of cells) {
    const el = rings[x.k], outer = el.params.diameter / 2, inner = outer - el.params.depth;
    x.rank = clamp01((x.k + (outer - x.r) / Math.max(1e-6, outer - inner)) / (rings.length + 0.0001));
    x.clock = ((90 - x.angle / DEG) % 360 + 360) % 360;
  }
  // ladder: a pulse falling through the rank lights every rank band with the same total light (the rims crowd their
  // band, the slats spread thin), so the cluster's sum holds still while the pulse moves: the band's mean count over its own
  const BINS = 64, hist = new Float64Array(BINS);
  for (const x of cells) hist[Math.min(BINS - 1, Math.floor(x.rank * BINS))]++;
  const mean = cells.length / BINS;
  for (const x of cells) x.ladder = Math.min(1, mean / hist[Math.min(BINS - 1, Math.floor(x.rank * BINS))]);
  const heads = [];
  rig.heads.forEach((fi, h) => {
    const f = rig.fixtures[fi], k = ringOf[f.element];
    if (k >= 0) heads.push({ h, fi, k, angle: f.angle, body: eulerToMat3(f.rot), local: f.local.slice() });
  });
  const lasers = [];
  rig.projectors.forEach((p, i) => { if (p.mount && ringOf[p.element] >= 0) lasers.push({ i, k: ringOf[p.element], angle: p.mount.angle, mount: p.mount }); });
  const hero = rig.projectors.findIndex((p) => p.bank === "H");
  return { ringEls, ringOf, rings, cells, heads, lasers, hero, rMax };
}

// The core's axis: through the ring centre along ring 0's home normal (the energy beam's line). Up it meets the roof,
// down the floor upstage of the deck (the orrery report's arithmetic: about (0, 38, 5.8) and (0, 0, -20.8)).
export function coreAxis(rig) {
  const F = rig.ringFormations || {}, el = rig.elements.find((e) => e.id === "ring");
  const C = F.centre || (el ? [el.origin[0], el.home.y ?? el.origin[1], el.origin[2]] : [0, 14, -11]);
  const t = ((el && el.home.tilt) ?? 55) * DEG;
  const n = [0, Math.sin(t), Math.cos(t)];
  const down = roomHit(C, [-n[0], -n[1], -n[2]], rig.venue, { stands: true });
  const up = roomHit(C, n, rig.venue, { stands: true });
  return { C, n, from: [C[0] - n[0] * down.t, C[1] - n[1] * down.t, C[2] - n[2] * down.t], fromWhat: down.what, toLen: up.t, toWhat: up.what };
}
// a frame (u, v) perpendicular to n
function perp(n) {
  const a = Math.abs(n[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
  let u = [a[1] * n[2] - a[2] * n[1], a[2] * n[0] - a[0] * n[2], a[0] * n[1] - a[1] * n[0]];
  const l = Math.hypot(u[0], u[1], u[2]); u = [u[0] / l, u[1] / l, u[2] / l];
  return { u, v: [n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0]] };
}

// Pan and tilt that point a head (its body matrix and local position) at a world point, without allocating: aimAt's
// solution (rig.js), the pan nearest the hint inside +-270, the tilt clamped to +-135.
export function aimInto(em, head, target, panHint, out) {
  const b = head.body, L = head.local, ho = 0.32;
  const lx = L[0] + b[1] * ho, ly = L[1] + b[4] * ho, lz = L[2] + b[7] * ho;
  const px = em[0] * lx + em[1] * ly + em[2] * lz + em[9], py = em[3] * lx + em[4] * ly + em[5] * lz + em[10], pz = em[6] * lx + em[7] * ly + em[8] * lz + em[11];
  let dx = target[0] - px, dy = target[1] - py, dz = target[2] - pz;
  const len = Math.hypot(dx, dy, dz) || 1; dx /= len; dy /= len; dz /= len;
  const ex = em[0] * dx + em[3] * dy + em[6] * dz, ey = em[1] * dx + em[4] * dy + em[7] * dz, ez = em[2] * dx + em[5] * dy + em[8] * dz;
  const bx = b[0] * ex + b[3] * ey + b[6] * ez, by = b[1] * ex + b[4] * ey + b[7] * ez, bz = b[2] * ex + b[5] * ey + b[8] * ez;
  let tilt = Math.acos(Math.max(-1, Math.min(1, by))) / DEG, pan = Math.atan2(bx, bz) / DEG;
  if (tilt < 1e-6) pan = panHint;
  let bestP = pan, bestT = tilt, bestD = Infinity;
  for (let s = 0; s < 2; s++) {
    const p0 = s ? pan + 180 : pan, t0 = s ? -tilt : tilt;
    for (const k of [-360, 0, 360]) {
      const p = p0 + k;
      if (Math.abs(p) > 270 + 1e-9) continue;
      const d = Math.abs(p - panHint);
      if (d < bestD) { bestD = d; bestP = p; bestT = t0; }
    }
  }
  out[0] = bestP; out[1] = Math.max(-135, Math.min(135, bestT));
  return out;
}

// ---------------------------------------------------------------------------------------------- the show class --
export class RingFormations {
  constructor(rig, { seed = null } = {}) {
    this.rig = rig;
    this.F = rig.ringFormations || {};
    this.T = ringTables(rig);
    this.axis = coreAxis(rig);
    this.basis = perp(this.axis.n);
    const T = this.T;
    this.n = T.ringEls.length;
    this.rr = new RingRig({
      ringRig: rig.ringRig,
      rings: T.rings.map((el) => ({
        radius: el.params.diameter / 2, home: { y: el.home.y ?? el.origin[1], tilt: el.home.tilt ?? 0 },
        limits: { y: (el.limits && el.limits.y) || [el.home.y ?? el.origin[1], el.home.y ?? el.origin[1]], tilt: (el.limits && el.limits.tilt) || [0, 90] },
        window: (y) => ringTiltWindow(el, y, rig.venue),
      })),
    });
    this.homeM = rig.elements.map((e) => elementMatrix(e));
    this.ringM = T.ringEls.map((e) => Float64Array.from(this.homeM[e]));
    this.emOf = (e) => (T.ringOf[e] >= 0 ? this.ringM[T.ringOf[e]] : this.homeM[e]);
    this.key = "home"; this.from = null;          // the formation the rings are in (or moving to), the one they left
    this.move = null;                              // {key, from, start, posLand} of the running morph
    this.deckAt = 0;
    this.seed = seed ?? rig.seed ?? 2014;
    this.heroState = { last: -Infinity, at: null, granted: null, fired: [], refused: [] };
    this.camera = [0, 8, 60];
    // the light layer's working state, preallocated
    this.cellDim = new Float32Array(T.cells.length); this.cellRole = new Uint8Array(T.cells.length);
    this.headTgt = T.heads.map(() => [0, 0, 0]);
    this.headOut = T.heads.map(() => [0, 0]);
    this.headDim = new Float32Array(T.heads.length); this.headRole = new Uint8Array(T.heads.length); this.headZoom = new Float32Array(T.heads.length);
    this.headOwn = new Uint8Array(T.heads.length);
    this.laserOwn = new Uint8Array(rig.projectors.length);
    // the renderer's extra emitters and beams (filled each frame)
    this.emit = { n: 0, pos: new Float32Array(MAX_FORMATION_EMIT * 3), col: new Float32Array(MAX_FORMATION_EMIT * 3), size: new Float32Array(MAX_FORMATION_EMIT) };
    this.beams = [];
    this.core = { on: false, c: this.axis.C.slice(), r: 0.85, level: 0, hot: 0, col: [0.5, 0.2, 1], hotCol: [1, 0.9, 1], spin: 0, t: 0 };
    this.motes = this._motes();
    this.state = { pos: 0, w: 0, wFrom: 0, lightKey: "home" };
    this.mp = { pos: [0, 0, 0], radial: [0, 0, 0], normal: [0, 0, 0] };
    this.roles = null;                             // linear RGB per role (the theme), set by the stage
  }
  get formations() { return Object.keys(this.F).filter((k) => !k.startsWith("_") && !["deck", "centre", "hero", "column"].includes(k)); }
  def(key) { return this.F[key] || null; }
  dream(key = this.key) { const d = this.def(key); return !!(d && d.dream); }
  // the rings are off their home pose (the camera's guard and the phrase layer's re-aim need the live rig)
  get live() { return this.key !== "home" || !!this.move || this.from !== null; }

  // ------------------------------------------------------------------------------------------------ the moves --
  set(key, pos = 0, bpm = 150) {
    const d = this.def(key);
    if (!d) throw new Error(`no ring formation ${key}`);
    this.rr.set(key, d, pos, bpm);
    this.key = key; this.from = null; this.move = null;
    this.state.start = pos - 64;                   // revealed long ago: everything is lit
    this._matrices();
  }
  // Go to formation `key`: its rings start on the next bar line (each at its rank in the reveal order) and it lands on
  // the bar line its last ring makes.
  go(key, grid, nowMs) {
    const d = this.def(key);
    if (!d) throw new Error(`no ring formation ${key}`);
    const r = this.rr.land(key, d, grid, nowMs);
    const start = grid.nextBarPos(grid.posAt(nowMs) - 1e-9);
    this.from = this.key !== key ? this.key : this.from;
    this.fromStart = start;
    this.key = key;
    this.move = { key, from: this.from, start, posLand: r.posLand, rings: r.rings };
    this.state.start = start;
    return { key, start, posLand: r.posLand, dream: !!d.dream };
  }
  // MORPH: the next formation of the deck (after the one the rings are in or moving to).
  morph(grid, nowMs) {
    const deck = (this.F.deck && this.F.deck.length ? this.F.deck : this.formations);
    const i = deck.indexOf(this.key);
    return this.go(deck[(i + 1) % deck.length], grid, nowMs);
  }
  // HERO: the discharge, once a charge (charge_bars), landing on the next ONE. Returns {ok, at | why}.
  hero(grid, nowMs) {
    const H = this.F.hero || {}, pos = grid.posAt(nowMs);
    const charge = (H.charge_bars ?? 8) * 4;
    const at = grid.nextBarPos(pos - 0.05);
    if (this.heroState.at !== null && this.heroState.at >= pos) return { ok: false, why: "armed", at: this.heroState.at };
    if (at - this.heroState.last < charge - 1e-6) {
      if (this.heroState.refused.length < 64) this.heroState.refused.push(+pos.toFixed(3));
      return { ok: false, why: "charging", ready: this.heroState.last + charge };
    }
    this.heroState.at = at; this.heroState.granted = null;
    return { ok: true, at };
  }
  heroCharge(pos) { const H = this.F.hero || {}, c = (H.charge_bars ?? 8) * 4; return clamp01((pos - this.heroState.last) / c); }
  // the discharge's envelope at pos (0 when none): granted by the FlashGate it rises in one frame, refused it lifts over
  // an eighth of a beat; either way it decays over hero.beats (at least half a beat).
  heroLevel(pos, flashGate = null) {
    const S = this.heroState, H = this.F.hero || {};
    if (S.at !== null && pos >= S.at - 1e-6) {
      S.granted = flashGate ? flashGate.request(S.at) : true;
      S.last = S.at; if (S.fired.length < 64) S.fired.push({ at: S.at, granted: S.granted }); S.at = null; S.on = S.last;
    }
    if (S.on === undefined || S.on === null) return 0;
    const age = pos - S.on, len = Math.max(0.5, H.beats ?? 4), attack = S.granted ? 0 : 0.125;
    if (age < 0 || age > len + attack) return 0;
    if (age < attack) return age / attack;
    return Math.pow(1 - (age - attack) / len, 1.6);
  }

  // ------------------------------------------------------------------------------------------------ per frame --
  update(grid, tEval, dt, flashGate = null) {
    const pos = grid.posAt(tEval);
    this.rr.update(grid, tEval, dt);
    this._matrices();
    if (this.move && pos >= this.move.posLand + this._outBeats()) { this.move = null; }
    if (this.from !== null && pos >= (this.fromStart ?? -Infinity) + this._outBeats()) this.from = null;
    this.state.pos = pos;
    this.hl = this.heroLevel(pos, flashGate);
    this._tEval = tEval;
    return this.rr.poses;
  }
  _outBeats() { return (this.F.hero && this.F.hero.out_beats) ?? 2; }
  _matrices() {
    const T = this.T;
    for (let k = 0; k < this.n; k++) elementMatrix(T.rings[k], this.rr.poses[k], this.ringM[k]);
  }
  // The reveal clock: beats since the morph's first bar line (large when the formation has stood a while).
  _since(pos) { return pos - (this.state.start ?? -64); }
  // How much of the departing formation's light is left (it fades over out_beats from the morph's first bar).
  _fromW(pos) { return this.from === null ? 0 : 1 - smooth(0, this._outBeats(), pos - (this.fromStart ?? pos)); }

  // The ring-mounted lasers and the laser brain's extra heads ride the live rings.
  updateMounts(lasers3d = null, laserHeads = null) {
    for (const L of this.T.lasers) {
      const mp = mountPose(this.ringM[L.k], L.mount, this.mp);
      if (lasers3d) lasers3d.setOrigin(L.i, mp.pos);
      const h = laserHeads && laserHeads[L.i];
      if (h && h.pos) { for (let j = 0; j < 3; j++) { h.pos[j] = mp.pos[j]; if (h.radial) h.radial[j] = mp.radial[j]; if (h.normal) h.normal[j] = mp.normal[j]; } }
    }
  }

  // The camera's view of the rings: live annuli (camera.js ringAnnulus shape), or null at home.
  liveAnnuli() {
    if (!this.live) return null;
    return this.T.rings.map((el, k) => { const m = this.ringM[k]; return ringAnnulus([m[9], m[10], m[11]], el.params.diameter / 2, el.params.depth, 0, [m[2], m[5], m[8]]); });
  }
  // The annuli a formation's rings sweep, at `phases` positions over its slowest turn (the camera's validity filter).
  annuliSets(key, phases = 8) {
    const d = this.def(key);
    if (!d || key === "home") return null;
    const rr = new RingRig({ rings: this.rr.rings, ringRig: this.rig.ringRig });
    const slow = Math.max(4, ...d.rings.map((r) => Math.abs(r.yaw_beats || r.spin_beats || 0)));
    const out = [];
    for (let j = 0; j < phases; j++) {
      const pos = (j / phases) * slow;
      rr.set(key, d, pos);
      out.push(this.T.rings.map((el, k) => { const m = elementMatrix(el, rr.poses[k]); return ringAnnulus([m[9], m[10], m[11]], el.params.diameter / 2, el.params.depth, 0, [m[2], m[5], m[8]]); }));
    }
    return out;
  }

  // ------------------------------------------------------------------------------------------- the light layer --
  // programmer.setLayer(this): over the look and the phrase layer, for the members a formation owns.
  apply(tH, tC, pos) {
    const keys = [];
    if (this.from !== null && this.from !== "home" && this._fromW(pos) > 0) keys.push([this.from, this._fromW(pos), true]);
    if (this.key !== "home") keys.push([this.key, 1, false]);
    if (!keys.length) { this._handback(tH, pos); return; }
    const T = this.T;
    this.headOwn.fill(0);
    for (const [key, wKey, leaving] of keys) {
      const d = this.def(key), look = d.look || key;
      const since = leaving ? 1e9 : this._since(pos);
      const out = leaving ? wKey : 1;
      this.cellDim.fill(0); this.cellRole.fill(ROLE.W);
      this.headDim.fill(0); this.headRole.fill(ROLE.W); this.headZoom.fill(1.5);
      const own = (LOOKS[look] || LOOKS.home).call(this, d, pos, since);
      if (!own) continue;
      const hl = this.hl || 0;
      // cells: the formation's dimmer over the look's, by its weight (roles switch at half way)
      if (own.cells) {
        const wc = out * (leaving ? 1 : ramp(own.cellsIn, since));
        const sh = d.shimmer ? this._shimmerSetup(d.shimmer) : null;
        for (let j = 0; j < T.cells.length; j++) {
          if (own.cells !== true && !own.cells.includes(T.cells[j].k)) continue;
          const x = T.cells[j], b = x.c * 4;
          let v = this.cellDim[j];
          if (hl > 0 && own.ripple) v = Math.max(v, own.ripple * hl * rippleAt(x.rank, pos - this.heroState.last));
          if (sh) v *= this._shimmer(x, sh);
          tC[b] = tC[b] * (1 - wc) + v * wc;
          if (wc >= 0.5) { tC[b + 1] = 0; tC[b + 2] = this.cellRole[j]; }
        }
      }
      // heads: fade the look out in place, then the formation in at its own aims (they move dim, never lit across)
      if (own.heads) {
        const wh = out * (leaving ? 1 : ramp(own.headsIn, since));
        for (let j = 0; j < T.heads.length; j++) {
          const H = T.heads[j];
          if (!own.heads.includes(H.k)) continue;
          this.headOwn[j] = 1;
          const b = H.h * 7;
          if (wh < 0.5) { tH[b + 2] *= 1 - 2 * wh; continue; }
          // the last frame's pan as the hint: a turning ring never flips a yoke between the two solutions
          aimInto(this.ringM[H.k], H, this.headTgt[j], this.headOut[j][0], this.headOut[j]);
          tH[b] = this.headOut[j][0]; tH[b + 1] = this.headOut[j][1];
          const lit = Math.max(this.headDim[j], hl > 0 && own.heroHeads ? hl : 0);
          tH[b + 2] = lit * (2 * wh - 1); tH[b + 3] = this.headZoom[j]; tH[b + 4] = 0; tH[b + 5] = this.headRole[j]; tH[b + 6] = this.headRole[j];
        }
      }
    }
    this.lastOwnedHeads = this.headOwn;
  }
  // after a formation has gone home, its heads come back to the look over hand_beats (never a lit snap)
  _handback(tH, pos) {
    const end = (this.fromStart ?? -Infinity) + this._outBeats(), len = (this.F.hero && this.F.hero.hand_beats) ?? 2;
    const w = 1 - clamp01((pos - end) / len);
    if (!(w > 0) || !this.lastOwnedHeads) return;
    for (let j = 0; j < this.T.heads.length; j++) if (this.lastOwnedHeads[j]) tH[this.T.heads[j].h * 7 + 2] *= 1 - w;
  }
  _shimmerSetup(s) {
    return { near: s.near_m ?? 4, far: s.far_m ?? 15, depth: s.depth ?? 0.45, step: Math.floor((this._tEval || 0) / 1000 * (s.hz ?? 18)) };
  }
  // the bands' flicker (the orrery's shimmer numbers), by the dot's distance from the camera
  _bandShimmer(p, i) {
    const s = this.def("orrery") && this.def("orrery").shimmer;
    if (!s) return 1;
    const dist = Math.hypot(p[0] - this.camera[0], p[1] - this.camera[1], p[2] - this.camera[2]);
    const a = smooth(s.far_m ?? 15, s.near_m ?? 4, dist);
    if (a <= 0) return 1;
    return 1 - (s.depth ?? 0.45) * a * (0.5 + 0.5 * hash(i, Math.floor(((this._tEval || 0) / 1000) * (s.hz ?? 18))));
  }
  // the hologram's flicker: deeper the nearer the camera, each cell its own noise (so the frame's sum stays steady)
  _shimmer(x, sh) {
    const m = this.ringM[x.k], c = x.c * 3, P = this.rig.cells.pos;
    const lx = P[c], ly = P[c + 1], lz = P[c + 2];
    const wx = m[0] * lx + m[1] * ly + m[2] * lz + m[9], wy = m[3] * lx + m[4] * ly + m[5] * lz + m[10], wz = m[6] * lx + m[7] * ly + m[8] * lz + m[11];
    const dist = Math.hypot(wx - this.camera[0], wy - this.camera[1], wz - this.camera[2]);
    const a = smooth(sh.far, sh.near, dist);
    if (a <= 0) return 1;
    return 1 - sh.depth * a * (0.5 + 0.5 * hash(x.c, sh.step));
  }

  // The lasers a formation owns this frame: R1..R12 on ring 0 and the hero. lasers: the stage's LaserEngine (after its
  // frame()); the formation's beams replace that frame's segments for the heads it owns.
  drawLasers(lasers, pos) {
    this.laserOwn.fill(0);
    const key = this.key === "home" && this.from !== null ? this.from : this.key;
    const w = this.key === "home" ? this._fromW(pos) : 1;
    const d = this.def(key);
    const hl = this.hl || 0;
    const list = [];
    if (d && key !== "home") (LASERS[d.look || key] || (() => {})).call(this, d, pos, this.key === "home" ? 1e9 : this._since(pos), list);
    // the hero's discharge: the tube up the axis, in every formation
    if (hl > 0 && this.T.hero >= 0) {
      const H = this.F.hero || {}, h = this.rig.projectors[this.T.hero];
      const tgt = this._axisPoint(H.tube_at_m ?? 26);
      list.push({ i: this.T.hero, dir: [tgt[0] - h.pos[0], tgt[1] - h.pos[1], tgt[2] - h.pos[2]], coneDeg: H.tube_deg ?? 0.5, ring: 8, col: H.laser_colour ?? 0, level: hl, spin: pos * 0.5 });
    }
    for (const L of list) this.laserOwn[L.i] = 1;
    if (!list.length) return 0;
    lasers.dropHeads(this.laserOwn);
    for (const L of list) lasers.aimed(L.i, L.dir, { col: L.col, level: clamp01(L.level) * (L.i === this.T.hero ? 1 : w), coneDeg: L.coneDeg || 0, ring: L.ring || 1, spin: L.spin || 0 });
    return list.length;
  }
  // a ring laser's aperture on its ring's live pose
  _laserPos(r) { return mountPose(this.ringM[r.k], r.mount, this.mp).pos; }
  _axisPoint(s, out = [0, 0, 0]) { const A = this.axis; out[0] = A.C[0] + A.n[0] * s; out[1] = A.C[1] + A.n[1] * s; out[2] = A.C[2] + A.n[2] * s; return out; }

  // The renderer's share: ring matrices, the core, the extra emitters and the energy column. roles: linear RGB per role.
  frame(camera = null) {
    if (camera) { this.camera[0] = camera[0]; this.camera[1] = camera[1]; this.camera[2] = camera[2]; }
    const pos = this.state.pos;
    this.emit.n = 0; this.beams.length = 0;
    this.core.on = false; this.core.level = 0;
    const roles = this.roles || DEFAULT_ROLES;
    const keys = [];
    if (this.from !== null && this.from !== "home" && this._fromW(pos) > 0) keys.push([this.from, this._fromW(pos), true]);
    if (this.key !== "home") keys.push([this.key, 1, false]);
    for (const [key, w, leaving] of keys) {
      const d = this.def(key), f = SCENERY[d.look || key];
      if (f) f.call(this, d, pos, leaving ? 1e9 : this._since(pos), w, roles);
    }
    // the energy column (the hero's beam through the core), idle at the formation's level, full on the discharge
    const idle = keys.reduce((m, [key, w]) => Math.max(m, ((this.def(key).column || {}).level ?? 0) * w), 0);
    const lv = Math.max(idle, this.hl || 0);
    if (lv > 0.002) {
      const C = this.F.column || {}, A = this.axis;
      const col = roles[ROLE[C.role || "W"]] || [1, 1, 1];
      this.beams.push({ apex: A.from.slice(), axis: A.n.slice(), beamDeg: C.beam_deg ?? 0.6, flux: (C.flux_lm ?? 12000) * lv, len: A.toLen + Math.hypot(A.C[0] - A.from[0], A.C[1] - A.from[1], A.C[2] - A.from[2]), col });
    }
    return { mats: this.ringM, els: this.T.ringEls, core: this.core, emit: this.emit, beams: this.beams,
             hitOpts: this.core.on && this.core.r > 0 ? { orb: { c: this.core.c, r: this.core.r } } : null, liftRims: keys.length > 0 };
  }
  _emit(p, rgb, k, size) {
    const e = this.emit, n = e.n;
    if (n >= MAX_FORMATION_EMIT || !(k > 0)) return;
    e.pos[n * 3] = p[0]; e.pos[n * 3 + 1] = p[1]; e.pos[n * 3 + 2] = p[2];
    e.col[n * 3] = rgb[0] * k; e.col[n * 3 + 1] = rgb[1] * k; e.col[n * 3 + 2] = rgb[2] * k;
    e.size[n] = size; e.n = n + 1;
  }
  _motes() {
    const M = (this.F.orrery && this.F.orrery.motes) || { count: 1400, radius: 30, scale: 6 };
    const r = rngOf((this.seed * 131 + 7) >>> 0), C = this.axis.C, out = [];
    for (let i = 0; i < (M.count || 0) && out.length < 2400; i++) {
      // density ~ 1 / (1 + (d / scale)^2): radius by rejection, direction uniform; kept in the air over the stage
      let d = 0;
      for (let g = 0; g < 32; g++) { const t = r() * M.radius; if (r() < 1 / (1 + (t / M.scale) ** 2)) { d = t; break; } }
      const z = 2 * r() - 1, ph = TAU * r(), s = Math.sqrt(1 - z * z);
      const p = [C[0] + d * s * Math.cos(ph), C[1] + d * z, C[2] + d * s * Math.sin(ph)];
      if (p[1] < 3 || p[1] > 36 || p[2] > 26 || p[2] < -23) continue;
      out.push({ p, f: 0.1 + 0.5 * r(), ph: r(), b: 0.25 + 0.75 * r() ** 3, s: 0.01 + 0.02 * r() });
    }
    return out;
  }
}
const DEFAULT_ROLES = [[0.2, 0.05, 1], [1, 0.05, 0.7], [0.9, 0.85, 1], [1, 1, 1], [0.3, 0.13, 1], [1, 0.48, 0.15], [0.35, 0.47, 1], [0.84, 0.36, 0.76]];
// the hero's radial ripple: a pulse travelling outward (rank 1 -> 0: the core outward) at half-beat spacing
function rippleAt(rank, age) {
  if (age < 0 || age > 2.5) return 0;
  const front = age / 2;                           // the front reaches the outer rim in 2 beats
  const d = (1 - rank) - front;
  return Math.max(0, 1 - Math.abs(d) / 0.12) * (1 - age / 2.5);
}
// tri(x): 0 -> 1 -> 0 over a period
const tri = (x) => 1 - Math.abs(2 * frac(x) - 1);

// ------------------------------------------------------------------------------------------------ the looks --
// Each look writes this.cellDim / cellRole for the ring cells, this.headTgt / headDim / headRole / headZoom for the
// halo heads, and returns what it owns: {cells: true | [rings], heads: [rings], cellsIn, headsIn (reveal windows in beats
// from the morph's first bar), ripple (the hero's ripple depth), heroHeads (the heads join the discharge)}.
const LOOKS = {
  home() { return null; },
  orrery(d, pos, since) {
    const T = this.T, L = d.light || {}, rv = (d.reveal && d.reveal.light) || {};
    const ringIn = rv.rings || [[12, 20], [8, 16], [4, 12], [0, 8]];
    const sweep = L.sweep_beats || [31, 29, 23, 19];
    for (let j = 0; j < T.cells.length; j++) {
      const x = T.cells[j], w = ramp(ringIn[x.k], since);
      if (w <= 0) continue;
      // the write-on: a ring's cells light clockwise from the top as its window opens
      const wo = clamp01(w * 1.3 - (x.clock / 360) * 0.3);
      let v = 0, role = ROLE.W;
      if (x.k === 0) {                                  // the dial: ticks on every slat, long ticks every sixth, a dotted inner rim
        if (x.kind === 0) v = x.slat % 6 === 0 ? 1 : x.along >= 5 ? 0.32 : 0;
        else if (x.kind === 2) v = (Math.round(x.angle / (TAU / 360)) % 2) ? 0.55 : 0.08;
        else v = 0.22;
      } else if (x.k === 1) {                           // a lancet frieze: pointed arches, six slats a period, lavender
        if (x.kind === 0) { const crest = 7 * tri(x.slat / 6); v = Math.max(0, 1 - Math.abs(x.along - crest) / 1.2) * 0.55; role = ROLE.bumpA; }
        else v = x.kind === 1 ? 0.35 : 0.2;
      } else if (x.k === 2) {                           // a dot chain: one cell on every slat
        if (x.kind === 0) v = x.along === 3 ? 0.75 : 0;
        else v = 0.18;
      } else {                                          // the dense comb round the core, violet
        if (x.kind === 0) { v = x.along <= 3 ? 0.42 : 0; role = ROLE.A; }
        else v = x.kind === 2 ? 0.6 : 0.3;
      }
      // a lighter band sweeping round each ring at its own (prime) rate: the medium scale of motion
      const band = 0.72 + 0.28 * Math.cos(x.angle - (TAU * pos) / sweep[x.k] * (x.k % 2 ? -1 : 1));
      this.cellDim[j] = v * band * wo; this.cellRole[j] = role;
    }
    // the halo heads: spokes from every ring into the core (they sweep with the turning gimbals); lenses read as planets
    const H = d.heads || {}, C = this.axis.C;
    for (let j = 0; j < T.heads.length; j++) {
      const h = T.heads[j];
      this.headTgt[j][0] = C[0]; this.headTgt[j][1] = C[1]; this.headTgt[j][2] = C[2];
      this.headDim[j] = (H.level || [0.32, 0.22, 0.2, 0])[h.k] ?? 0.2; this.headRole[j] = ROLE[H.role || "W"]; this.headZoom[j] = H.zoom ?? 1.0;
    }
    return { cells: true, heads: [0, 1, 2], cellsIn: [0, 4], headsIn: rv.heads || [16, 24], ripple: 0.5, heroHeads: true };
  },
  spiral(d, pos, since) {
    const T = this.T, L = d.light || {};
    const g0 = (360 * pos) / (L.gap_beats ?? 16), step = L.gap_step_deg ?? 40, gap = (L.gap_deg ?? 60) / 2;
    const rates = L.arc_beats || [-53, 41, -29, 19];
    const bead = ((360 * pos) / (L.bead_beats ?? 11)) % 360;
    const ph = frac(pos);
    for (let j = 0; j < T.cells.length; j++) {
      const x = T.cells[j];
      // the gap of ring k: g0 + step k + its own counter-rotation; soft edges of 8 degrees
      const gc = g0 + step * x.k + (360 * pos) / rates[x.k];
      let dg = Math.abs((((x.clock - gc) % 360) + 540) % 360 - 180);
      const arc = smooth(gap - 4, gap + 4, dg);
      let v = 0, role = ROLE.W;
      if (x.kind === 1) v = 1.0 * arc;                          // the bright rings
      else if (x.kind === 2) { v = 0.5 * arc; role = ROLE.bumpA; }
      else if (x.along === 4) { v = 0.25 * arc; role = ROLE.bumpA; }   // a dotted circle in each ring
      else if (x.slat % 2 === 0) v = 0.1;                       // the web of straight lines
      // the ladder: a pulse falls down the well once a beat (outer to inner), over the steady rings
      v += 0.5 * x.ladder * Math.max(0, 1 - Math.abs(x.rank - ph) / 0.1);
      // the bead riding ring 1's outer rim
      if (x.k === 1 && x.kind === 1) { const db = Math.abs((((x.clock - bead) % 360) + 540) % 360 - 180); if (db < 3) v = Math.max(v, 1); }
      this.cellDim[j] = clamp01(v); this.cellRole[j] = role;
    }
    // heads: a spine of rays feeding the beam (every ring's heads aim at the axis above the funnel)
    const H = d.heads || {}, spine = H.spine_m || [[16, 26], [20, 28], [24, 30]];
    const per = [0, 0, 0, 0], tot = [0, 0, 0, 0];
    for (const h of T.heads) tot[h.k]++;
    for (let j = 0; j < T.heads.length; j++) {
      const h = T.heads[j], sp = spine[h.k] || [20, 28], m = per[h.k]++;
      this._axisPoint(sp[0] + ((sp[1] - sp[0]) * m) / Math.max(1, tot[h.k] - 1), this.headTgt[j]);
      this.headDim[j] = (H.level || [0.28, 0.2, 0.2])[h.k] ?? 0.2; this.headRole[j] = ROLE[H.role || "beamB"]; this.headZoom[j] = H.zoom ?? 1.2;
    }
    const rv = (d.reveal && d.reveal.light) || {};
    return { cells: true, heads: [0, 1, 2], cellsIn: rv.cells || [8, 16], headsIn: rv.heads || [12, 16], ripple: 0.6, heroHeads: true };
  },
  vortex(d, pos, since) {
    const T = this.T, L = d.light || {};
    const comet = (L.chase_deg_per_beat ?? 3.7) * pos;
    for (let j = 0; j < T.cells.length; j++) {
      const x = T.cells[j];
      if (x.kind === 0) { this.cellDim[j] = 0.15; this.cellRole[j] = ROLE.A; continue; }
      const da = Math.abs((((x.clock - comet - 90 * x.k) % 360) + 540) % 360 - 180);
      this.cellDim[j] = 0.25 + 0.75 * Math.exp(-((da / 22) ** 2)); this.cellRole[j] = ROLE.W;
    }
    const H = d.heads || {}, A = this.axis;
    const off = (H.offset_deg ?? 60) * Math.sin((TAU * pos) / (H.swing_beats ?? 8));
    const pre = this._vortexPreset || (this._vortexPreset = preparePreset({ kind: "twist", circle: { centre: this._axisPoint(H.centre_m ?? 20), normal: A.n, radius_scale: H.radius_scale ?? 0.2 }, offset_deg: 0 }));
    const fake = { n: 1, memberFixture: [0], keys: { level: [0], x: [0] } };
    for (let j = 0; j < T.heads.length; j++) {
      const h = T.heads[j];
      fake.memberFixture[0] = h.fi;
      presetTarget(this.rig, fake, pre, 0, this.ringM[h.k], this.headTgt[j], { offset_deg: off });
      this.headDim[j] = H.level ?? 0.7; this.headRole[j] = ROLE[H.role || "beamB"]; this.headZoom[j] = H.zoom ?? 1.5;
    }
    return { cells: true, heads: [0, 1, 2], cellsIn: [0, 4], headsIn: [2, 6], ripple: 0.4, heroHeads: true };
  },
  crown(d, pos, since) {
    const T = this.T, L = d.light || {};
    for (let j = 0; j < T.cells.length; j++) {
      const x = T.cells[j];
      if (x.k !== 1 && x.k !== 2) continue;
      if (x.kind === 0) { this.cellDim[j] = 0.2; this.cellRole[j] = ROLE.A; }
      else { this.cellDim[j] = 0.25 + 0.2 * Math.cos(x.angle - (TAU * pos) / (L.chase_beats ?? 24)); this.cellRole[j] = ROLE.W; }
    }
    const H = d.heads || {};
    // the offset breathes 0 -> 180 -> 0 over its period (cylinder, hourglass, every beam through one knot, and back)
    const D = 90 - 90 * Math.cos((TAU * pos) / (H.period_beats ?? 64));
    const roofY = this.rig.venue.roof_y ?? 38;
    const fake = { n: 1, memberFixture: [0], keys: { level: [0], x: [0] } };
    // the roof circles stand over each ring's centre (the crown only tilts its rings, so they are fixed: prepared once)
    const pres = this._crownPre || (this._crownPre = [1, 2].map((k) => { const m = this.ringM[k];
      return preparePreset({ kind: "twist", circle: { centre: [m[9], roofY, m[11]], normal: [0, 1, 0], radius_scale: 1 }, offset_deg: 0 }); }));
    for (let j = 0; j < T.heads.length; j++) {
      const h = T.heads[j];
      if (h.k !== 1 && h.k !== 2) continue;
      const m = this.ringM[h.k], pre = pres[h.k - 1];
      fake.memberFixture[0] = h.fi;
      presetTarget(this.rig, fake, pre, 0, m, this.headTgt[j], { offset_deg: h.k === 1 ? D : -D });
      this.headDim[j] = H.level ?? 0.8; this.headRole[j] = ROLE[h.k === 1 ? (H.role || "beamA") : (H.role2 || "beamB")]; this.headZoom[j] = H.zoom ?? 1.2;
    }
    return { cells: [1, 2], heads: [1, 2], cellsIn: [0, 4], headsIn: [0, 4], ripple: 0, heroHeads: false };
  },
  portal(d, pos, since) {
    const T = this.T, L = d.light || {};
    for (let j = 0; j < T.cells.length; j++) {
      const x = T.cells[j];
      if (x.k !== 0) continue;
      this.cellDim[j] = x.kind === 0 ? 0.12 : 0.6; this.cellRole[j] = ROLE.W;
    }
    const H = d.heads || {}, m = this.ringM[0];
    // the membrane: every R0 head at one point on the ring's axis, depth_m behind it (the beams cross and end upstage);
    // a slow iris twist of +-swing degrees about the axis
    const dep = H.depth_m ?? -10, sw = (H.swing_deg ?? 12) * Math.sin((TAU * pos) / (H.swing_beats ?? 16)) * DEG;
    const cx = m[9] + m[2] * dep, cy = m[10] + m[5] * dep, cz = m[11] + m[8] * dep;
    for (let j = 0; j < T.heads.length; j++) {
      const h = T.heads[j];
      if (h.k !== 0) continue;
      const a = h.angle + sw, r = H.iris_m ?? 1.5;
      this.headTgt[j][0] = cx + r * (m[0] * Math.cos(a) + m[1] * Math.sin(a));
      this.headTgt[j][1] = cy + r * (m[3] * Math.cos(a) + m[4] * Math.sin(a));
      this.headTgt[j][2] = cz + r * (m[6] * Math.cos(a) + m[7] * Math.sin(a));
      this.headDim[j] = H.level ?? 0.75; this.headRole[j] = ROLE[H.role || "beamA"]; this.headZoom[j] = H.zoom ?? 1.0;
    }
    void L;
    return { cells: [0], heads: [0], cellsIn: [0, 4], headsIn: [0, 4], ripple: 0.3, heroHeads: false };
  },
};

// The lasers of each look: {i (projector), dir (world), coneDeg, ring, col, level}.
const LASERS = {
  orrery(d, pos, since, list) {
    // the ring lasers lock on: twelve thin spokes into the core, low power (a lace, not a fan)
    const L = d.lasers || {}, C = this.axis.C, rv = (d.reveal && d.reveal.light) || {};
    const w = ramp(rv.lasers || [24, 25], since);
    if (w <= 0) return;
    for (const r of this.T.lasers) {
      const p = this._laserPos(r);
      list.push({ i: r.i, dir: [C[0] - p[0], C[1] - p[1], C[2] - p[2]], col: L.colour ?? 0, level: (L.level ?? 0.22) * w });
    }
  },
  spiral(d, pos, since, list) {
    // the twisted cage: each ring laser aims at a point on a small circle round the axis, turned by tau (locked to the
    // gap spiral), so the straight beams wring into a waist round the energy beam; the hero's discharge straightens them
    const L = d.lasers || {}, rv = (d.reveal && d.reveal.light) || {}, A = this.axis, B = this.basis;
    const w = ramp(rv.lasers || [16, 18], since);
    if (w <= 0) return;
    const tau = ((360 * pos) / ((d.light && d.light.gap_beats) ?? 16)) * DEG * (1 - (this.hl || 0));
    const Q = this._axisPoint(L.cage_at_m ?? 22, [0, 0, 0]), rad = L.cage_radius_m ?? 1.0;
    for (const r of this.T.lasers) {
      const p = this._laserPos(r), a = r.angle + tau;
      const t = [Q[0] + rad * (Math.cos(a) * B.u[0] + Math.sin(a) * B.v[0]), Q[1] + rad * (Math.cos(a) * B.u[1] + Math.sin(a) * B.v[1]), Q[2] + rad * (Math.cos(a) * B.u[2] + Math.sin(a) * B.v[2])];
      list.push({ i: r.i, dir: [t[0] - p[0], t[1] - p[1], t[2] - p[2]], col: L.colour ?? 1, level: (L.level ?? 0.3) * w });
    }
    if (this.T.hero >= 0) {
      const h = this.rig.projectors[this.T.hero].pos, t = this._axisPoint(L.tube_at_m ?? 26, [0, 0, 0]);
      list.push({ i: this.T.hero, dir: [t[0] - h[0], t[1] - h[1], t[2] - h[2]], coneDeg: 0.5, ring: 8, col: L.tube_colour ?? 0, level: (L.tube_level ?? 0.35) * w, spin: pos * 0.5 });
    }
  },
  vortex(d, pos, since, list) {
    const L = d.lasers || {};
    if (this.T.hero < 0) return;
    const h = this.rig.projectors[this.T.hero].pos, t = this._axisPoint(L.tube_at_m ?? 26, [0, 0, 0]);
    list.push({ i: this.T.hero, dir: [t[0] - h[0], t[1] - h[1], t[2] - h[2]], coneDeg: 0.4, ring: 6, col: L.tube_colour ?? 0, level: L.tube_level ?? 0.4, spin: pos * 0.7 });
  },
};

// The scenery each look adds for the renderer: the core, its bands, the planets on their arms, the motes.
const SCENERY = {
  orrery(d, pos, since, w, roles) {
    const Cd = d.core || {}, rv = (d.reveal && d.reveal.light) || {};
    const A = this.axis, C = A.C, hl = this.hl || 0;
    const coreW = ramp(rv.core || [0, 4], since) * w;
    const core = this.core;
    core.on = true; core.r = Cd.radius ?? 0.85; core.c = C;
    core.level = Math.max(core.level, coreW * (Cd.level ?? 1));
    core.hot = (Cd.hot ?? 0.35) + hl * (Cd.hero_hot ?? 1.2);
    core.col = roles[ROLE[Cd.role || "A"]]; core.hotCol = roles[ROLE[Cd.hot_role || "W"]];
    core.spin = (360 * pos) / (Cd.swirl_beats ?? 23);
    core.nits = Cd.nits ?? 180;
    const U = 1 / 30;
    // the dotted equator and the port lights, on the core's surface (turning with its swirl)
    const R = core.r * 1.02, eq = Cd.equator_dots ?? 48, sp = core.spin * DEG;
    const W = roles[ROLE.W], lav = roles[ROLE.bumpA];
    for (let i = 0; i < eq; i++) {
      const a = sp + (TAU * i) / eq;
      this._emit([C[0] + R * Math.cos(a), C[1], C[2] + R * Math.sin(a)], W, (Cd.dot_nits ?? 9000) * U * coreW, 0.018);
    }
    for (let i = 0; i < 6; i++) {
      const el = (i % 2 ? 1 : -1) * 0.5, a = sp * 0.6 + (TAU * i) / 6;
      this._emit([C[0] + R * Math.cos(el) * Math.cos(a), C[1] + R * Math.sin(el), C[2] + R * Math.cos(el) * Math.sin(a)], W, (Cd.port_nits ?? 30000) * U * coreW * (1 + hl), 0.05);
    }
    // the core's glow in the haze: one wide soft emitter
    this._emit(C, core.col, (Cd.glow_nits ?? 70) * U * coreW * (1 + 0.8 * hl), Cd.glow_m ?? 2.4);
    // the wireframe bands hugging the core: dot chains at their own radii, tilts and (prime) rates
    const bandsW = ramp(rv.bands || [2, 10], since) * w;
    for (const [bi, B] of (Cd.bands || []).entries()) {
      const r = B.r ?? 1.1, n = B.dots ?? 96, tl = (B.tilt_deg ?? 0) * DEG, az = (B.axis_deg ?? bi * 67) * DEG;
      const rot = ((360 * pos) / (B.beats ?? 13)) * DEG;
      const ct = Math.cos(tl), st = Math.sin(tl), ca = Math.cos(az), sa = Math.sin(az);
      const col = roles[ROLE[B.role || "W"]];
      for (let i = 0; i < n; i++) {
        let on = 1;
        if (B.texture === "lancet") on = (i % 5) < 3 ? 1 : 0;
        else if (B.texture === "ticks") on = i % 6 === 0 ? 1 : 0.35;
        else if (B.texture === "dots") on = i % 2 ? 0 : 1;
        if (!on) continue;
        const a = rot + (TAU * i) / n;
        // a circle in the x-z plane, tilted about x by tl, then turned about y by az
        const x0 = r * Math.cos(a), z0 = r * Math.sin(a), y1 = -z0 * st, z1 = z0 * ct;
        const p = [C[0] + x0 * ca + z1 * sa, C[1] + y1, C[2] - x0 * sa + z1 * ca];
        const shim = this._bandShimmer(p, i + 977 * bi);
        this._emit(p, col, (B.nits ?? 9000) * U * bandsW * on * shim, B.size ?? 0.016);
      }
    }
    // planets on arms, riding each ring at their own rates, inside first
    const plW = ramp(rv.planets || [16, 24], since) * w;
    for (const P of d.planets || []) {
      const el = this.T.rings[P.ring], m = this.ringM[P.ring];
      if (!el) continue;
      const rOut = el.params.diameter / 2, arm = P.arm_m ?? 0.9;
      for (let q = 0; q < (P.count ?? 1); q++) {
        const a = (TAU * q) / (P.count ?? 1) + ((TAU * pos) / (P.beats ?? 31));
        const ca = Math.cos(a), sa = Math.sin(a);
        const at = (rr) => [m[0] * rr * ca + m[1] * rr * sa + m[9], m[3] * rr * ca + m[4] * rr * sa + m[10], m[6] * rr * ca + m[7] * rr * sa + m[11]];
        for (let s = 1; s <= 3; s++) this._emit(at(rOut + (arm * s) / 4), lav, 4000 * U * plW, 0.02);
        const pp = at(rOut + arm);
        this._emit(pp, roles[ROLE[P.role || "W"]], (P.nits ?? 700) * U * plW, P.size ?? 0.28);
        this._emit(pp, lav, (P.halo_nits ?? 25) * U * plW, (P.size ?? 0.28) * 3);
      }
    }
    // star motes in the haze: sparse, uncorrelated twinkles (each its own frequency and phase: the sum stays steady)
    const M = d.motes || {}, moW = ramp(rv.motes || [24, 32], since) * w;
    if (moW > 0) {
      const t = (this._tEval || 0) / 1000, wind = M.wind || [0.05, 0, -0.02];
      for (const s of this.motes) {
        const tw = Math.pow(Math.max(0, Math.sin(TAU * (s.f * t + s.ph))), 6);
        const p = [s.p[0] + wind[0] * ((t * 0.3) % 20), s.p[1] + Math.sin(t * 0.2 + s.ph * 6) * 0.3, s.p[2] + wind[2] * ((t * 0.3) % 20)];
        this._emit(p, W, (M.nits ?? 6000) * U * moW * s.b * (0.15 + 0.85 * tw), s.s);
      }
    }
  },
  spiral(d, pos, since, w, roles) {
    // the vanishing point: a small bright bead at the top of the well (ring 3's centre) inside its double circle
    const m = this.ringM[this.n - 1], rv = (d.reveal && d.reveal.light) || {};
    const U = 1 / 30, lw = ramp(rv.cells || [8, 16], since) * w;
    this._emit([m[9], m[10], m[11]], roles[ROLE.W], 9000 * U * lw * (1 + (this.hl || 0) * 2), 0.12);
    this._emit([m[9], m[10], m[11]], roles[ROLE.bumpA], 50 * U * lw, 1.6);
  },
};

// ---------------------------------------------------------------------------------------------- the safety check --
// Where every beam a formation owns ends, landed at beat position pos: the heads (aimed at their targets, through the
// head geometry) and the lasers, ray-cast against the room WITH the audience stands and the core. Allowed surfaces:
// the roof, the deck, the floor upstage of the deck, the back wall, the core. Returns [{kind, index, what, at, ok}].
export const BEAM_END_OK = Object.freeze(["roof", "deck", "backwall", "orb"]);
export function beamEnds(rig, key, pos = 0) {
  const R = new RingFormations(rig);
  R.set(key, pos);
  R.state.pos = pos; R.state.start = pos - 1e6;
  const tH = new Float64Array(rig.heads.length * 7), tC = new Float64Array(rig.cells.n * 4);
  R.apply(tH, tC, pos);
  const fr = R.frame([0, 8, 60]);
  const hitOpts = { stands: true, ...(fr.hitOpts || {}) };
  const out = [];
  const deckZ0 = (rig.venue.deck_z || [-16, 0])[0];
  const verdict = (o, d) => {
    const h = roomHit(o, d, rig.venue, hitOpts);
    const at = [o[0] + d[0] * h.t, o[1] + d[1] * h.t, o[2] + d[2] * h.t];
    const ok = BEAM_END_OK.includes(h.what) || (h.what === "floor" && at[2] < deckZ0);
    return { what: h.what, at: at.map((v) => +v.toFixed(2)), ok };
  };
  const hp = { lens: [0, 0, 0], dir: [0, 0, 0] };
  for (let j = 0; j < R.T.heads.length; j++) {
    if (!R.headOwn[j]) continue;
    const H = R.T.heads[j], f = rig.fixtures[H.fi];
    headPose(R.ringM[H.k], f, tH[H.h * 7], tH[H.h * 7 + 1], hp);
    out.push({ kind: "head", index: H.h, ring: H.k, ...verdict(hp.lens, hp.dir) });
  }
  const origin = (i) => { const L = R.T.lasers.find((x) => x.i === i); return L ? mountPose(R.ringM[L.k], L.mount).pos : rig.projectors[i].pos; };
  const fake = { dropHeads() {}, aimed: (i, dir) => out.push({ kind: "laser", index: i, ...verdict(origin(i), norm3(dir)) }) };
  R.hl = 1;                                         // with the hero's tube too
  R.drawLasers(fake, pos);
  if (fr.beams.length) for (const b of fr.beams) out.push({ kind: "column", index: -1, ...verdict(b.apex, b.axis) });
  return out;
}
function norm3(v) { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }

// The rings' clearance in a formation at pos: each ring's envelope against the room and the gap between every pair.
export function ringClearance(rig, key, pos = 0) {
  const R = new RingFormations(rig);
  R.set(key, pos);
  const env = R.T.rings.map((el, k) => ({ k, ...ringEnvelope(el, R.rr.poses[k], rig.venue) }));
  const ann = R.T.rings.map((el, k) => annulusOf(el, R.rr.poses[k]));
  const gaps = [];
  for (let a = 0; a < ann.length; a++) for (let b = a + 1; b < ann.length; b++) gaps.push({ a, b, gap: annulusGap(ann[a], ann[b]) });
  return { env, gaps, poses: R.rr.poses.map((p) => ({ ...p })) };
}
