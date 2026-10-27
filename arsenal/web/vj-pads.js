// VJ pads v2: arsenal/web/vj-pads.js (pure ES module: no DOM, no WebGL). Tests: tests/vj_pads.test.mjs.
//
// Daniel, 2026-10-27 (the north star): "visual spectacle increase as well as driveable in a dynamic way ergonomically from
// the pads where each button does something worth doing visually"; before that, "trigger a vast array of visual effects
// through a simple interface and combos ... repeated triggers don't do the exact same thing in the exact same space".
// The build spec: research/in-flight/vj-v2-build-spec-2026-10-27.md section B, after the pads lane
// (research/reviewed/keylab-liberation-2026-10-22/vj-v2-research-2026-10-27/pads.research.md).
//
// The rows keep their meaning (row 1 HITS, row 2 HOLDS, row 3 MOVES); pad 2 stays the lasers and pad 12 the tap. This
// module is the grammar every pad speaks, decided without a browser (the page, vj.js, owns the clock and the light):
//   - VELOCITY IS SIZE: a soft press plays a small version, a hard one the full one, and the press's place in the bar
//     adds the accent (vj-motions.js metricAccent: a downbeat plays bigger than an off-beat)              PadPlay.press
//   - A SECOND PRESS WITHIN A BAR ESCALATES (the laser engine's edge, 5.66 beats), up to three levels; presses faster
//     than 3 a second never grow (they play smaller: the flash rule)                                          PadPlay.press
//   - A ONE-SHOT LANDS: its life ends on the grid (the motion library's landing rule: the start is the press, never
//     delayed; the end is the first grid line at or after three quarters of its length)                       PadPlay.press
//   - REPEATS MOVE: each pad deals its own motion (vj-motions.js MotionDealer, a deck of its own) and its own place from
//     an 8-spot deck, never one of the last two                                                       PadPlay.press, SPOTS
//   - HOLDS BECOME MOTIONS: held half a beat, a pad turns into a standing motion of its section's budget (a bar in a drop,
//     two bars in a break); a TAP of a hold pad plays its own short version (a bar of the shutters, a puff of CO2, a
//     hit-stop of the freeze); a release lands on the grid too                               PadPlay.hold, PadPlay.release
//   - A HIT PAD HELD KEEPS STRIKING on the beat (the ring ripples, the glitch repeats)                     PadPlay.repeats
//   - HERO: one charge per 8 bars; the payoff lands on the next ONE                                            HeroCharge
//   - BUILD then DROP: a tap builds 4, 8 or 16 bars by velocity and drops on the downbeat after; a second tap drops on
//     the next downbeat; a hold is a riser that drops on release                                               BuildDrop
//   - SAFETY: a tap dampens, a hard tap chokes, a hold is black while held                                     safetyAct
// Positions are beats on the page grid (vj-core.js BeatClock.posAt, or a free-running count at the fallback tempo).

import { MotionDealer, metricAccent, seededRng } from "./vj-motions.js";

export const PADS_API = "arsenal.vj-pads/v1";

const clamp01 = (x) => (x > 1 ? 1 : x < 0 ? 0 : x);
const EPS = 1e-9;

// ------------------------------------------------------------------------------------------------------ the edges --
// In beats since the pad's own previous press: the laser engine's escalate edge (vj-lasers.js RETRIGGER.escalate, halfway
// between a bar and two bars), so every pad escalates exactly as pad 2 does. A pad held this long is a hold (the laser
// engine's held tier). Presses closer than 1/3 s are the flash rule's: they never grow a picture.
export const ESCALATE_BEATS = Math.sqrt(32);
export const HOLD_BEATS = 1 / 2;
export const RAPID_MS = 1000 / 3;
export const ESC_MAX = 3;
export const SIZE_MAX = 1.6;               // the most a hit grows (hard, on the phrase's ONE, escalated): vj-motions AMP_MAX
export const ESC_GROWTH = 0.25;            // each escalation level adds this much size
export const RAPID_SIZE = 0.7;             // a press faster than 3 a second plays this much smaller
export const ESC_LED = Object.freeze([0.6, 0.8, 1.0]);   // a pad's light by the level its next press reaches (TIER_LED's)
export const GRACE_BEATS = 1 / 16;         // a press this late after a line still lands on it (the hero, the drop)

// The first grid line at or after pos + minAhead (beats). grid 4 = a bar line, 1 = a beat, 1/2 = an eighth.
export function lineAfter(pos, grid, minAhead = 0) {
  return Math.ceil((pos + minAhead) / grid - EPS) * grid || 0;
}
// The first grid line strictly after pos (a strike just made on a line books the next one).
export function lineBeyond(pos, grid) { return (Math.floor(pos / grid + EPS) + 1) * grid; }

// ------------------------------------------------------------------------------------------------------- the verbs --
// Each pad action's grammar as data:
//   row         1 HITS, 2 HOLDS, 3 MOVES (0: a learnable action off the default map)
//   life, grid  a one-shot's life in beats (velocity stretches it x0.6 to x1.4) and the grid its end lands on
//   repeat      held, a hit pad strikes again on every line of this grid (beats)
//   hold        a hold pad: tap = the short version, ending on the first `tap` line at least `tapMin` beats on; a release
//               after a hold lands on the first `exit` line at least an eighth of a beat on; maxHoldS: a hold this long
//               lets go by itself (CO2: a real CO2 cannon fires for seconds, never for ever)
//   motion      deals a motion per press (and a standing motion when held)
//   spots       deals a place from SPOTS per press
export const PAD_VERBS = Object.freeze({
  shockwave: Object.freeze({ row: 1, name: "Ring", life: 2.75, grid: 1, repeat: 1, motion: true, spots: true }),
  laser:     Object.freeze({ row: 1, name: "Lasers" }),        // the laser engine's own grammar (vj-lasers.js)
  co2:       Object.freeze({ row: 1, name: "CO2", hold: true, tap: 1 / 2, tapMin: 1 / 4, exit: 1 / 2, maxHoldS: 3, motion: true, spots: true }),
  glitch:    Object.freeze({ row: 1, name: "Glitch Lift", life: 1.25, grid: 1 / 2, repeat: 1, motion: true }),
  strobe:    Object.freeze({ row: 2, name: "Shutters", hold: true, tap: 4, tapMin: 1, exit: 1 / 2, motion: true }),
  particles: Object.freeze({ row: 2, name: "Fog + Swarm", hold: true, tap: 4, tapMin: 1, exit: 1 / 2, motion: true, spots: true }),
  kaleido:   Object.freeze({ row: 2, name: "Morph", hold: true, tap: 4, tapMin: 1, exit: 1 / 2, motion: true }),
  freeze:    Object.freeze({ row: 2, name: "Lower", hold: true, tap: 1 / 4, tapMin: 1 / 8, exit: 1 / 2, motion: true }),
  safety:    Object.freeze({ row: 3, name: "Safety", hold: true }),
  hero:      Object.freeze({ row: 3, name: "Hero" }),
  build:     Object.freeze({ row: 3, name: "Build / Drop", hold: true }),
  zoom:      Object.freeze({ row: 3, name: "Zoom punch", life: 1, grid: 1 / 2 }),
  flash:     Object.freeze({ row: 0, name: "White flash", life: 0.5, grid: 1 / 2 }),
  invert:    Object.freeze({ row: 0, name: "Invert", hold: true, tap: 1, tapMin: 1 / 2, exit: 1 / 2 }),
});
export const verbOf = (action) => PAD_VERBS[action] || null;

// The 8 places a placed hit is dealt from: x in half-widths of the frame (the page multiplies by aspect / 2), y in frame
// heights, +y up, in the overlay's centred space. Spot 0 is the hero point (vj-lasers.js HERO); the rest frame it in
// thirds, so a run of rings walks the stage instead of piling up within 15 % of the centre.
export const SPOTS = Object.freeze([[0, 0.05], [-0.42, 0.16], [0.42, 0.16], [-0.42, -0.18], [0.42, -0.18], [-0.72, 0.0],
                                    [0.72, 0.0], [0, -0.22]].map((s) => Object.freeze(s)));

// A spot deck: every spot once a round (shuffled, seeded), never one of the last two dealt while another is left.
class SpotDeck {
  constructor(rng) { this.rng = rng; this.hist = []; this.order = []; }
  next() {
    if (!this.order.length) {
      const a = SPOTS.map((_, i) => i);
      for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(this.rng() * (i + 1)); const t = a[i]; a[i] = a[j]; a[j] = t; }
      this.order = a;
    }
    let k = this.order.findIndex((s) => !this.hist.includes(s));
    if (k < 0) k = 0;
    const s = this.order.splice(k, 1)[0];
    this.hist.push(s); if (this.hist.length > 2) this.hist.shift();
    return s;
  }
}

// ------------------------------------------------------------------------------------------------------- PadPlay --
// One per page. press() on every pad press (the page passes the beat position, the beat's length, the velocity and
// whether a live beat stands behind the position: without one there is no bar to accent, every press is mid-weight).
export class PadPlay {
  constructor({ seed = 1 } = {}) {
    this.seed = seed;
    this.pads = Array.from({ length: 12 }, () => ({
      lastPos: -Infinity, lastMs: -Infinity, esc: 0, down: false, downPos: 0, downMs: 0, held: false, action: null,
      nextRepeat: Infinity, expired: false, hit: null, standing: null,
    }));
    this.dealers = new Map();
    this.spots = new Map();
    this.presses = 0;
  }
  _dealer(action) {
    let d = this.dealers.get(action);
    if (!d) { d = new MotionDealer({ seed: `${this.seed}|${action}` }); this.dealers.set(action, d); }
    return d;
  }
  _spot(action) {
    let d = this.spots.get(action);
    if (!d) { d = new SpotDeck(seededRng(this.seed, "spots", action)); this.spots.set(action, d); }
    return d.next();
  }
  // Choke: every pad's ladder back to its start, every hold let go (the next press is a fresh first hit).
  reset() {
    for (const p of this.pads) { p.lastPos = -Infinity; p.lastMs = -Infinity; p.esc = 0; p.down = false; p.held = false; p.nextRepeat = Infinity; }
  }

  // A press. Returns the hit: { pad, action, esc 1..3, size 0..SIZE_MAX, rapid, accent, spot (index into SPOTS, or null),
  // motion (a vj-motions deal record, or null), lifeBeats, endPos (a one-shot's landed end; null for a hold pad: its end
  // is decided by the release) }.
  press(pad, action, { pos, perMs = 400, vel = 0.7, nowMs = 0, section = "any", live = true } = {}) {
    const p = this.pads[pad - 1];
    if (!p || !Number.isFinite(pos)) return null;
    const verb = verbOf(action) || {};
    // (a gap that runs backward is a clock that changed under the pad -- the beat came or went: a fresh first hit)
    const gapB = pos - p.lastPos, rapid = nowMs - p.lastMs >= 0 && nowMs - p.lastMs < RAPID_MS;
    let esc;
    if (!(gapB >= 0 && gapB <= ESCALATE_BEATS + EPS)) esc = 1;
    else if (rapid) esc = Math.max(1, p.esc);
    else esc = Math.min(ESC_MAX, Math.max(1, p.esc) + 1);
    const v = clamp01(vel);
    const accent = live ? metricAccent(pos) : { name: "free", mul: 0.85 };
    const size = Math.min(SIZE_MAX, (0.4 + 0.6 * v) * accent.mul * (1 + ESC_GROWTH * (esc - 1)) * (rapid ? RAPID_SIZE : 1));
    let lifeBeats = null, endPos = null;
    if (verb.life && !verb.hold) {
      endPos = lineAfter(pos, verb.grid, 0.75 * verb.life * (0.6 + 0.8 * v));
      lifeBeats = endPos - pos;
    }
    const dealer = verb.motion ? this._dealer(action) : null;
    let motion = null;
    if (dealer) {
      dealer.press(pos);
      motion = dealer.deal({ pos, perMs, vel: v, tier: rapid ? "rapid" : esc > 1 ? "escalate" : "burst", level: esc,
                             lifeBeats: lifeBeats ?? (verb.tap || 1), section, bank: "both", gaps: false, twoColours: false });
    }
    const spot = verb.spots ? this._spot(action) : null;
    p.lastPos = pos; p.lastMs = nowMs; p.esc = esc;
    p.down = true; p.downPos = pos; p.downMs = nowMs; p.held = false; p.action = action; p.expired = false;
    p.nextRepeat = Infinity; p.standing = null;
    this.presses++;
    const hit = Object.freeze({ pad, action, esc, size, rapid, accent: accent.name, spot, motion, lifeBeats, endPos });
    p.hit = hit;
    return hit;
  }

  // Every frame while the pad is down. Once the press has been held HOLD_BEATS it becomes a hold: returns { held: true,
  // standing } that frame (standing: the hold's standing motion, its section's budget, looping until release; a hit pad
  // with `repeat` gets its first repeat line). A hold pad held past its maxHoldS lets go by itself: { expire: true }, once.
  // Otherwise null.
  hold(pad, { pos, perMs = 400, nowMs = 0, section = "any" } = {}) {
    const p = this.pads[pad - 1];
    if (!p || !p.down) return null;
    const verb = verbOf(p.action) || {};
    if (!p.held && pos - p.downPos >= HOLD_BEATS - EPS) {
      p.held = true;
      if (verb.repeat) p.nextRepeat = lineBeyond(pos, verb.repeat);
      if (verb.motion) {
        const d = this._dealer(p.action);
        p.standing = d.deal({ pos, perMs, vel: p.hit ? (p.hit.size / SIZE_MAX) : 0.7, tier: "held", level: p.esc, looping: true,
                              section, bank: "both", gaps: false, twoColours: false });
      }
      return { held: true, standing: p.standing };
    }
    if (verb.maxHoldS && !p.expired && nowMs - p.downMs >= verb.maxHoldS * 1000) { p.expired = true; return { expire: true }; }
    return null;
  }

  // Held, a hit pad strikes again on each line of its repeat grid: the number of strikes due by pos (0 or 1 a frame;
  // a frame that skipped a line strikes once, never in a burst).
  repeats(pad, pos) {
    const p = this.pads[pad - 1];
    if (!p || !p.down || !p.held || !(pos >= p.nextRepeat - EPS)) return 0;
    const verb = verbOf(p.action) || {};
    p.nextRepeat = lineBeyond(pos, verb.repeat || 1);
    return 1;
  }

  // The pad let go. Returns { tap, held, endPos }: a tap of a hold pad plays its short version to the first `tap` line at
  // least `tapMin` beats after the press; a release after a hold lands on the first `exit` line an eighth of a beat on;
  // a hit pad's release ends nothing (its life is already landed).
  release(pad, { pos } = {}) {
    const p = this.pads[pad - 1];
    if (!p || !p.down) return null;
    const verb = verbOf(p.action) || {};
    const held = p.held;
    p.down = false; p.held = false; p.nextRepeat = Infinity;
    let endPos = null;
    if (verb.hold && Number.isFinite(pos)) {
      if (!held && verb.tap) endPos = Math.max(lineAfter(p.downPos, verb.tap, verb.tapMin || 0), lineAfter(pos, verb.tap));
      else if (verb.exit) endPos = lineAfter(pos, verb.exit, 1 / 8);
    }
    return { tap: !held, held, endPos, standing: p.standing };
  }

  isDown(pad) { const p = this.pads[pad - 1]; return !!(p && p.down); }
  isHeld(pad) { const p = this.pads[pad - 1]; return !!(p && p.down && p.held); }
  standing(pad) { const p = this.pads[pad - 1]; return p && p.down && p.held ? p.standing : null; }
  // The level the pad's NEXT press would reach if it came at pos (1 fresh, up to 3), for its light: a pad whose next press
  // escalates shows it before it is pressed.
  nextEsc(pad, pos) {
    const p = this.pads[pad - 1];
    if (!p || !(pos - p.lastPos >= 0 && pos - p.lastPos <= ESCALATE_BEATS + EPS)) return 1;
    return Math.min(ESC_MAX, Math.max(1, p.esc) + 1);
  }
  ledLevel(pad, pos) { return ESC_LED[this.nextEsc(pad, pos) - 1]; }
}

// ----------------------------------------------------------------------------------------------------------- CO2 --
// The jets a CO2 press fires, as data the page plays (into the haze fluid when it runs, else as its own plumes): a row of
// nozzles along the floor, centred on the press's spot; size and escalation set how many (2 to 8) and how hard; the order
// they fire in follows the spot and the level (centre-out, a chase across, alternating sides, all at once), 1/16 beat
// apart. Returns [{ x01 (0 left .. 1 right), delay (beats after the press), strength 0..1 }].
export const CO2_ORDERS = Object.freeze(["centreout", "chase", "alternate", "together"]);
export const CO2_STEP_BEATS = 1 / 16;
export function co2Jets(hit) {
  const size = Math.min(1, (hit && hit.size) || 0.5), esc = (hit && hit.esc) || 1;
  const n = Math.min(8, 2 + Math.round(4 * size) + 2 * (esc - 1));
  const sx = hit && hit.spot !== null && hit.spot !== undefined ? SPOTS[hit.spot][0] : 0;
  const centre = 0.5 + 0.25 * sx, spacing = n > 1 ? Math.min(0.11, 0.8 / (n - 1)) : 0;
  const order = CO2_ORDERS[(((hit && hit.spot) || 0) + esc) % CO2_ORDERS.length];
  const xs = Array.from({ length: n }, (_, i) => clamp01(centre + (i - (n - 1) / 2) * spacing));
  const rank = (i) => {
    if (order === "together") return 0;
    if (order === "chase") return sx > 0 ? n - 1 - i : i;
    const fromMid = Math.abs(i - (n - 1) / 2);
    if (order === "centreout") return Math.floor(fromMid);
    return (n - 1) / 2 - fromMid + (i < (n - 1) / 2 ? 0 : 0.5);   // alternate: outside in, left before right
  };
  const strength = Math.min(1, 0.45 + 0.4 * size + 0.1 * (esc - 1));
  return xs.map((x01, i) => Object.freeze({ x01, delay: rank(i) * CO2_STEP_BEATS, strength }));
}

// ---------------------------------------------------------------------------------------------------------- HERO --
// The charged payoff (pads lane, row 3: "one charge per 8 bars; it lands on the next ONE"). Full at the start; a payoff
// spends the charge, which refills over 8 bars from the ONE it landed on. A press while charged books the payoff on the
// next bar line (a press within 1/16 beat after a line plays on that line, at once); a press while charging books
// nothing. charge(pos) is 0..1 for the pad's light (dim while it refills, the page blinks it on the beat once full).
export const HERO_CHARGE_BARS = 8;
export class HeroCharge {
  constructor({ bars = HERO_CHARGE_BARS } = {}) { this.bars = bars; this.lastAt = -Infinity; this.pendingAt = null; this.fired = 0; }
  // (a position before the last payoff is a clock that changed under it -- the beat came or went: charged, never stuck)
  charge(pos) { return Number.isFinite(this.lastAt) && pos >= this.lastAt ? clamp01((pos - this.lastAt) / (4 * this.bars)) : 1; }
  ready(pos) { return this.pendingAt === null && this.charge(pos) >= 1 - EPS; }
  press(pos) {
    if (!this.ready(pos)) return null;
    const at = lineAfter(pos - GRACE_BEATS, 4);
    this.pendingAt = at;
    return { at };
  }
  // the booked payoff's line once pos reaches it (once), else null. A booking is never more than a bar ahead, so one two
  // bars ahead was made on a clock that has since changed: it moves to the next line of this one.
  due(pos) {
    if (this.pendingAt !== null && this.pendingAt - pos > 8) this.pendingAt = lineAfter(pos - GRACE_BEATS, 4);
    if (this.pendingAt === null || pos < this.pendingAt - EPS) return null;
    const at = this.pendingAt;
    this.pendingAt = null; this.lastAt = at; this.fired++;
    return at;
  }
  reset() { this.pendingAt = null; }
}

// ------------------------------------------------------------------------------------------------ BUILD then DROP --
// A tap builds 4, 8 or 16 bars by velocity (soft, medium, hard: the laser engine's velocity tiers) and drops on the bar
// line nearest that many bars on; a tap during the build drops on the next downbeat (at least a beat on). Held a beat,
// the pad is a riser: the build rises while it is held and drops on the downbeat after the release (a release within
// 1/16 beat after a bar line drops on it). After the drop the section is the drop's for DROP_BARS. tick(pos) returns
// "drop" once, on the frame the drop's line is reached. progress(pos) 0..1: how far the build has risen.
export const BUILD_BARS = Object.freeze([4, 8, 16]);
export const RISER_FULL_BEATS = 16;        // a riser is fully risen after four bars held
export const DROP_BARS = 16;               // the drop's section lasts this long
export const buildBarsFor = (vel) => BUILD_BARS[vel < 0.45 ? 0 : vel <= 0.8 ? 1 : 2];
export class BuildDrop {
  constructor() { this.reset(); this.drops = 0; }
  reset() { this.phase = "idle"; this.start = 0; this.dropAt = null; this.riser = false; this.downAt = null; this.droppedAt = null; }
  press(pos, vel = 0.7) {
    this.downAt = pos;
    if (this.phase === "build") {
      const next = lineAfter(pos, 4, 1);
      if (this.dropAt === null || next < this.dropAt) this.dropAt = next;
      return { act: "drop-next", at: this.dropAt };
    }
    const bars = buildBarsFor(vel);
    this.phase = "build"; this.start = pos; this.riser = false;
    this.dropAt = Math.max(lineAfter(pos + 4 * bars - 2, 4), lineAfter(pos, 4, 1));
    return { act: "build", bars, at: this.dropAt };
  }
  // the pad held a beat: a riser (it drops on the release)
  hold(pos) {
    if (this.downAt === null || this.riser || pos - this.downAt < 1 - EPS) return false;
    this.riser = true; this.phase = "build"; this.dropAt = null;
    if (!(this.start <= this.downAt)) this.start = this.downAt;
    return true;
  }
  release(pos) {
    const was = this.downAt;
    this.downAt = null;
    if (!this.riser || was === null) return null;
    this.riser = false;
    this.dropAt = lineAfter(pos - GRACE_BEATS, 4);
    return { act: "drop", at: this.dropAt };
  }
  tick(pos) {
    // a position before the build's start (or the drop's) is a clock that changed under it: the build keeps its length
    if (this.phase === "build" && pos < this.start - EPS) { if (this.dropAt !== null) this.dropAt += pos - this.start; this.start = pos; }
    if (this.phase === "drop" && pos < this.droppedAt - EPS) this.droppedAt = pos;
    if (this.phase === "build" && this.dropAt !== null && pos >= this.dropAt - EPS) {
      this.phase = "drop"; this.droppedAt = this.dropAt; this.dropAt = null; this.drops++;
      return "drop";
    }
    if (this.phase === "drop" && pos - this.droppedAt >= 4 * DROP_BARS - EPS) this.phase = "idle";
    return null;
  }
  progress(pos) {
    if (this.phase !== "build") return 0;
    if (this.riser || this.dropAt === null) return clamp01((pos - this.start) / RISER_FULL_BEATS);
    return clamp01((pos - this.start) / Math.max(EPS, this.dropAt - this.start));
  }
  // the build's feel: the shutters' division as it rises (a quarter, an eighth, a sixteenth in its last quarter)
  division(pos) { const k = this.progress(pos); return k < 0.5 ? 1 : k < 0.75 ? 1 / 2 : 1 / 4; }
}

// -------------------------------------------------------------------------------------------------------- SAFETY --
// One pad for the job dampen and choke did on two (pads lane: "three of those four have no picture"): a tap dampens, a
// tap harder than 0.8 chokes; held half a beat the whole frame goes black until the release (grandMA's Black: hold
// through the last beat, let go on the drop).
export const SAFETY_CHOKE_VEL = 0.8;
export function safetyAct(vel) { return vel > SAFETY_CHOKE_VEL ? "choke" : "dampen"; }
