// Virtual Stage, the chord phrasing's ensembles: arsenal/web/stage/ensemble.js. What a chord, a strum and a fade DO on the
// Stage, as intents the page applies with the actions it already has. Pure (no DOM, no WebGL); tests in
// tests/stage_grammar.test.mjs. The recogniser is grammar.js; the design of record is the round-3 design
// (docs/library/design/20261028_kick-vocabulary-round3-codex-2026-10-28_4a3a13.md), sections 3, 4, 6 and 8.
//
// Daniel, 2026-10-28: "like 5 7 6 could become laser sections 1-4 sections 8-12 then everything in the middle, then all of
// them could flash together"; "i mean like 8 7 6 5 4 then 456789". 2026-10-29: "lets also land the chord phrasing."
//
// A THIN ADAPTER on purpose: it speaks only in the page's own pad actions (1-0, C) and one level, so it composes with
// whatever kick 5 becomes on stage-v3 (a whole-stage palette bank): an ensemble is "these controls, as one lineage".
//
//   chord   every member's own action, dispatched as it arrives (the union of their areas), with ONE attack identity: the
//           first luminance attack of the lineage (a kick's punch) is the lineage's, and every later member's kick JOINS
//           it at its current age -- no second punch, no replayed peak (design 5: "a later member joins the envelope at its
//           CURRENT age"). attack(lineage, rec) does that on the kick's record (kick.js: rec.punchFrom, the beat position
//           its punch counts from; -Infinity: none).
//           Transport collapses once per lineage: STOP > NEXT > GO (a lower one after a higher one is skipped).
//           C asks for at most one camera composition per lineage (design 8: never several cuts).
//   strum   the same lineage, its members lit in their measured order inside the one attack.
//   fade    BREATH: a level 0..1 over the look's own light (the heads' and LEDs' dimmers before the kicks, the room's fill,
//           the lasers' master), never the grand master and never the kicks: "a candlelight bed can coexist with a vivid
//           manual" hit (design 7). Each step moves the TARGET by its delta; the level follows at one step (1/9) per 120 ms
//           (a continuous ramp: speed of stepping is speed of fading). The fade LATCHES where the hands leave it (Daniel's
//           own run fades out and then back in); handBack() returns it to 1 over four beats (Esc).
//           A sweep's start names the run's earlier keys whose pending commands can still be withdrawn (cancel intents):
//           the honest 8/9 tradeoff -- photons already shown stay shown.

export const ENSEMBLE_API = "arsenal.stage-ensemble/v1";
export const TRANSPORT_RANK = Object.freeze({ "3": 1, "4": 2, "7": 3 });   // GO < NEXT < STOP
export const BREATH = Object.freeze({ stepLevel: 1 / 9, stepMs: 120, handBackBeats: 4, floor: 0 });
const clamp01 = (x) => Math.max(0, Math.min(1, x));

export class Ensembles {
  constructor(opts = {}) {
    this.o = { ...BREATH, ...opts };
    this.lin = new Map();                  // lineage id -> {transport, camera, attack, members}
    this.breath = { level: 1, target: 1, source: null, active: false, hand: null, lastMs: null };
    this.stats = { presses: 0, skipped: 0, attacks: 0, joined: 0, cancels: 0, breaths: 0 };
    this.log = [];                         // the last 64 gestures, for the HUD and the receipts
  }
  _lineage(id) {
    let L = this.lin.get(id);
    if (!L) {
      L = { id, kind: "single", transport: 0, camera: false, attack: undefined, controls: [] };
      this.lin.set(id, L);
      if (this.lin.size > 256) this.lin.delete(this.lin.keys().next().value);
    }
    return L;
  }
  _note(e) { this.log.push(e); if (this.log.length > 64) this.log.shift(); }
  // one recogniser decision -> the intents the page applies, in order
  plan(d) {
    if (d.type === "press") {
      const L = this._lineage(d.lineage);
      L.kind = d.kind; L.controls.push(d.control);
      const rank = TRANSPORT_RANK[d.control];
      if (rank) {
        if (L.transport >= rank) { this.stats.skipped++; return [{ do: "skip", control: d.control, lineage: d.lineage, why: "transport" }]; }
        L.transport = rank;
      }
      if (d.control === "C") {
        if (L.camera) { this.stats.skipped++; return [{ do: "skip", control: d.control, lineage: d.lineage, why: "camera" }]; }
        L.camera = true;
      }
      this.stats.presses++;
      return [{ do: "press", control: d.control, velocity: d.velocity, lineage: d.lineage, kind: d.kind, member: d.member }];
    }
    if (d.type === "reclassify") {
      const L = this._lineage(d.lineage);
      L.kind = d.to;
      for (const a of d.absorbed || []) {
        const A = this.lin.get(a);
        if (!A) continue;
        L.transport = Math.max(L.transport, A.transport); L.camera = L.camera || A.camera;
        if (L.attack === undefined) L.attack = A.attack;
        L.controls.push(...A.controls);
        this.lin.set(a, L);                // a late kick of an absorbed lineage joins the root's attack
      }
      this._note({ gesture: d.to, lineage: d.lineage, controls: L.controls.slice(), t: d.t });
      return [];
    }
    if (d.type === "release") return d.dispatched ? [{ do: "release", control: d.control, lineage: d.lineage }] : [];
    if (d.type === "breath") return this._breath(d);
    if (d.type === "walk" && d.phase !== "end") this._note({ gesture: "walk", walk: d.walk, gap: d.gap, pairs: d.pairs, t: d.t });
    if (d.type === "settle" && d.kind !== "single") this._note({ gesture: `${d.kind} settled`, lineage: d.lineage, controls: d.controls, t: d.t0 });
    return [];
  }
  _breath(d) {
    const B = this.breath, out = [];
    if (d.phase === "arm") { B.active = true; B.source = "explicit"; B.hand = null; return out; }
    if (d.phase === "end") { B.active = false; this._note({ gesture: "fade end", level: +B.target.toFixed(3), why: d.why, t: d.t }); return out; }
    // start / step: the first recognition anchors at the CURRENT target (never the key's number), then moves it
    if (d.phase === "start") { this.stats.breaths++; B.active = true; B.source = d.explicit ? "explicit" : "sweep"; }
    B.hand = null;
    B.target = Math.max(this.o.floor, clamp01(B.target + (d.delta || 0)));
    this._note({ gesture: d.phase === "start" ? (d.explicit ? "fade (B)" : "fade") : "fade step", delta: +(d.delta || 0).toFixed(4), target: +B.target.toFixed(4), t: d.t });
    for (const c of d.cancel || []) { this.stats.cancels++; out.push({ do: "cancel", control: c.control, lineage: c.lineage, why: "fade" }); }
    out.push({ do: "breath", target: B.target });
    return out;
  }
  // after a kick press of lineage id: the lineage's first attack is its identity; a later member joins it at its age
  attack(lineageId, rec) {
    if (!rec || !("punchFrom" in rec)) return null;
    const L = this._lineage(lineageId);
    if (L.attack === undefined) { L.attack = rec.punchFrom; this.stats.attacks++; return { own: true, from: rec.punchFrom }; }
    if (rec.punchFrom !== L.attack) { rec.punchFrom = L.attack; }
    this.stats.joined++;
    return { own: false, from: L.attack };
  }
  // Esc: the level goes back to 1 over handBackBeats (from where it is: an interrupted fade starts from its current value)
  handBack(nowMs, beatMs) {
    const B = this.breath;
    if (B.target >= 1 && B.level >= 1) return false;
    const ms = Math.max(250, Math.min(1000, beatMs || 400)) * this.o.handBackBeats;
    B.hand = { from: B.level, t0: nowMs, ms }; B.active = false;
    this._note({ gesture: "fade hand-back", from: +B.level.toFixed(3), t: nowMs });
    return true;
  }
  // each frame: the level follows its target (one step per stepMs), or the hand-back's ramp
  tick(nowMs) {
    const B = this.breath;
    const dt = B.lastMs === null ? 0 : Math.max(0, Math.min(250, nowMs - B.lastMs));
    B.lastMs = nowMs;
    if (B.hand) {
      const u = Math.min(1, (nowMs - B.hand.t0) / B.hand.ms);
      B.level = B.hand.from + (1 - B.hand.from) * u; B.target = B.level;
      if (u >= 1) { B.hand = null; B.level = 1; B.target = 1; }
      return B.level;
    }
    const rate = this.o.stepLevel / this.o.stepMs;
    const d = B.target - B.level, m = rate * dt;
    B.level = Math.abs(d) <= m ? B.target : B.level + Math.sign(d) * m;
    return B.level;
  }
  get level() { return this.breath.level; }
  // the programmer's layer hook (after the look, the phrase layer and the rings; before the kicks): the look's own light
  apply(tH, tC) {
    const l = this.breath.level;
    if (l >= 1) return;
    for (let i = 2; i < tH.length; i += 7) tH[i] *= l;
    for (let i = 0; i < tC.length; i += 4) tC[i] *= l;
  }
  status() {
    const B = this.breath;
    return { api: ENSEMBLE_API, stats: { ...this.stats }, breath: { level: +B.level.toFixed(4), target: +B.target.toFixed(4), active: B.active, source: B.source, handBack: !!B.hand },
             log: this.log.slice(-16) };
  }
}
// the programmer has one layer slot (the ring formations hold it): both, in order
export function chainLayers(...layers) {
  const L = layers.filter(Boolean);
  return { apply(tH, tC, pos) { for (const l of L) l.apply(tH, tC, pos); } };
}
