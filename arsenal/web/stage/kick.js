// Virtual Stage, KICK v2: arsenal/web/stage/kick.js (pure ES module: no DOM, no WebGL). Tests: tests/stage_kick.test.mjs.
// The programmer (programmer.js) owns one Kicks and runs it as its step 3 (the playbacks); stage.js routes the pads to it.
//
// Daniel, 2026-10-27, on the phone bar while testing the Stage: "Hitting kick sometimes had an impact at other times nothing
// changed", and "Can we make kick trigger different rows of lights and or lasers with a peak in brightness or a row turning
// on and panning, it could be also lit for duration of press and on keylab velocity can change parameters too like
// lighting color, animation and strobe". Then: "lets make it a vertically longer button that presses and holds the light
// while the finger is on it and you can sweep up and down to adjust brightness! Lets have two kick buttons with vertical
// "velocity" one kick for white one kick for color, you can press both at same time and two rows can light up at once!"
//
// Why a KICK was sometimes nothing: v0's KICK was an intensity lift on the strand only, merged highest-takes-precedence. In
// the drop the strand already pulses to full on every beat and in the build it sits at 0.75, so a lift had nowhere to go
// (measured: 13 of 20 presses dead in the drop, 10 of 20 in the build). Intensity alone cannot show over a bright look.
//
// What a KICK is now (the set's `kick` block is the data; sets/source-v1.json):
//   TWO BUTTONS   kick-white (pad 1, key 1) and kick-colour (pad 5, key 5). Each press deals its OWN row; held together
//                 they light two different rows at once, never one row twice.
//   THE DECK      the rows are named groups of the set (the truss, the lip, the halo's thirds, the towers, the delay
//                 towers over the crowd, each ring's slats, the strips, the strand's cubes...), dealt from a seeded
//                 shuffle-bag: every row once a round, never the row a kick just had, never a row a live kick (held or still
//                 fading) is showing, and -- when it can -- in another ZONE of the picture than the last one (so successive
//                 hits hop round the stage). A row that would not show this hit now (no headroom for its level, no colour
//                 to give) is passed over and stays in the round for later: that is what makes a dead press impossible.
//   WHAT A ROW DOES   it comes on at the kick's level (merged highest-takes-precedence) in the button's colour: the white
//                 kick paints the theme's white (W) on LED rows, the colour kick paints the theme's colour (a lit LED keeps
//                 its own look colour when that is already a colour). Moving heads never have their colour wheel turned by
//                 a kick (a wheel runs past every slot between, red included, at 0.12 s a slot): the white kick deals a
//                 head row only while its wheel shows white, the colour kick only while it shows a colour.
//   VELOCITY      at the press picks the ANIMATION (the bands are data): soft = a peak; medium = a sweep (heads tilt
//                 through a motion of the V2 motion library, vj-motions.js, beat-locked and looping while held; LED rows
//                 chase it member by member); hard = the same with twice the throw. Every sweep is sized so the head's
//                 tilt motor can make it: never faster than 80 % of its speed or its acceleration.
//   LEVEL         the brightness, from the press's velocity and then live: padLevel() moves it while the pad is held (the
//                 phone's tall pads: the finger's height), slewed over a few frames so it never zippers.
//   HOLD = GATE   the row stays lit while the pad is held and fades on release (0.3 beat); a tap is a quick hit (it holds
//                 an eighth of a beat). A press waits for its beat line when it is early and lights at once when it is late
//                 (the beat it belongs to is the nearest one: the receipts' onset rule). A stuck pad lets go after 64 beats.
//   THE STROBE    only while the live level is in the top band (>= 0.95). ONE strobe clock for every kick, locked to the
//                 bar, at the slowest beat division that keeps it at or under 1.9 flashes a second, and every edge of it at
//                 least 0.263 s after the last: at most 4 edges in any 1.01 s, which the final limiter (flash.js, 5 counted
//                 transitions per 1.01 s) never has to touch. The first row to want it joins at once (the strobe engages as
//                 the finger reaches the band; the clock still keeps an edge's spacing from that row's light-up); any other
//                 row joins, and every row leaves, only while the clock is lit, so all the strobing rows change together
//                 and a joining or leaving row adds no edge of its own. The limiter stays the backstop and is not changed.
//   WITHOUT A BLOCK  (source-v0) KICK is v0's strand lift exactly: the strand's heads and cube cells, 0.6 + 0.4 x velocity,
//                 decaying over 0.3 beat from the line, no colour, no motion, no strobe.

import { MotionDealer, valueAt, headSign, CLASSES, seededRng } from "../vj-motions.js";
import { ORDERS, orderKey, rankBy } from "./effects.js";

export const KICK_API = "arsenal.stage-kick/v2";
export const KICK_KINDS = Object.freeze(["kick-white", "kick-colour"]);
// what the dealer counts as a hit that shows (tests/stage_kick.test.mjs pins the same numbers): a mean lift of the row's
// level of 0.15, or a mean drop in saturation (sRGB HSV) of 0.20 toward white
export const KICK_VISIBLE = Object.freeze({ lift: 0.15, white: 0.2 });
const VIS_MARGIN = 0.03;                 // the dealer asks a little more than the bar, because it judges targets, not pixels
export const SAT_COLOUR = 0.3;           // a colour at or over this saturation reads as a colour, under it as white
// the house strobe cap: 1.9 flashes a second, so an edge at least 1 / 3.8 s after the last, so at most 4 edges in the
// limiter's 1.01 s window (flash.js LIMIT.N_MAX is 5): the strobe alone leaves the limiter a transition to spare
export const STROBE_HZ_CAP = 1.9;
export const STROBE_MIN_EDGE_S = 1 / (2 * STROBE_HZ_CAP);
// the programmer's colour roles, in its order (programmer.js ROLE_NAMES; tests/stage_kick.test.mjs checks they agree)
export const KICK_ROLES = Object.freeze(["A", "B", "W", "beamA", "beamB", "warm", "bumpA", "bumpB"]);
export const CLASSES_BEATS = (cls) => (CLASSES[cls] ? CLASSES[cls].beats : NaN);

export const KICK_DEFAULTS = Object.freeze({
  release_beats: 0.3, tap_hold_beats: 0.125, max_hold_beats: 64,
  level: Object.freeze({ from_velocity: [0, 1], slew_s: 0.06 }),
  bands: Object.freeze([
    { name: "peak", from: 0 },
    { name: "sweep", from: 0.45, sweep: { class: "M1", deg: 25 } },
    { name: "drive", from: 0.85, sweep: { class: "M1", deg: 50 } },
  ]),
  chase: Object.freeze({ floor: 0.6, lag: 0.6 }),
  strobe: Object.freeze({ from_level: 0.95, max_hz: STROBE_HZ_CAP, beats: [0.5, 1, 2, 4], on: 0.35, floor: 0 }),
  white: Object.freeze({ role: "W" }),
  colour: Object.freeze({ cells: ["A", "B", "bumpA"], keep_lit_colour: true }),
  recent_fall_per_beat: 0.15,
});

// ------------------------------------------------------------------------------------------------- colour maths --
const srgb = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);
// HSV saturation of a linear colour as the screen shows it (sRGB-encoded): 0 white or grey, 1 a pure hue
export function saturation(r, g, b) {
  const R = srgb(Math.max(0, r)), G = srgb(Math.max(0, g)), B = srgb(Math.max(0, b));
  const mx = Math.max(R, G, B), mn = Math.min(R, G, B);
  return mx > 1e-6 ? (mx - mn) / mx : 0;
}
const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const isNum = (x) => typeof x === "number" && Number.isFinite(x);

// ---------------------------------------------------------------------------------------------- configuration --
// The kick block with the defaults under it, and its cards resolved to members. Without a block: the v0 strand lift.
export function kickConfig(rig) {
  const block = rig.kick || null;
  if (!block) return legacyConfig(rig);
  const cfg = { legacy: false, seed: block.seed ?? rig.seed ?? 1, about: block.about || "" };
  for (const k of ["release_beats", "tap_hold_beats", "max_hold_beats", "recent_fall_per_beat"]) cfg[k] = block[k] ?? KICK_DEFAULTS[k];
  cfg.level = { ...KICK_DEFAULTS.level, ...(block.level || {}) };
  cfg.bands = (block.bands || KICK_DEFAULTS.bands).map((b) => ({ ...b })).sort((a, b) => a.from - b.from);
  cfg.chase = { ...KICK_DEFAULTS.chase, ...(block.chase || {}) };
  cfg.strobe = { ...KICK_DEFAULTS.strobe, ...(block.strobe || {}) };
  cfg.strobe.max_hz = Math.min(STROBE_HZ_CAP, cfg.strobe.max_hz);          // the cap is the code's, not the set's
  cfg.white = { ...KICK_DEFAULTS.white, ...(block.white || {}) };
  cfg.colour = { ...KICK_DEFAULTS.colour, ...(block.colour || {}) };
  cfg.cards = (block.deck || []).map((c, i) => resolveCard(rig, c, i)).filter(Boolean);
  return cfg;
}
function legacyConfig(rig) {
  const heads = [], cells = [];
  for (let i = 0; i < rig.heads.length; i++) if (rig.elements[rig.fixtures[rig.heads[i]].element].id === "rung") heads.push(i);
  for (let c = 0; c < rig.cells.n; c++) if (rig.elements[rig.cells.element[c]].id === "rung" && rig.cells.kind[c] === 2) cells.push(c);
  return {
    legacy: true, seed: rig.seed ?? 1, about: "v0: the strand lift",
    release_beats: 0.3, tap_hold_beats: 0, max_hold_beats: KICK_DEFAULTS.max_hold_beats, recent_fall_per_beat: KICK_DEFAULTS.recent_fall_per_beat,
    level: { from_velocity: [0.6, 1], slew_s: KICK_DEFAULTS.level.slew_s },
    bands: [{ name: "lift", from: 0 }], chase: { ...KICK_DEFAULTS.chase }, strobe: { ...KICK_DEFAULTS.strobe, from_level: Infinity },
    white: null, colour: null,
    cards: [{ name: "strand", zone: "strand", heads: Int32Array.from(heads), cells: Int32Array.from(cells), pan: null, tilt: null,
              headSide: new Float64Array(heads.length).fill(1), headLower: new Uint8Array(heads.length), headRank: Int32Array.from(heads.map((_, i) => i)),
              cellQ: new Int32Array(cells.length) }],
  };
}
// a card: {row | rows, zone, order, pan, tilt} -> its heads and cells (each a group of the set), with each head's side and
// height (the motion's mirror modes), the members' places in the card's order (the sweep's ripple, the chase's travel)
function resolveCard(rig, c, i) {
  const names = c.rows || (c.row ? [c.row] : []);
  const heads = [], cells = [], hSide = [], hY = [], hKeyH = [], cKey = [];
  const order = c.order || null;
  for (const name of names) {
    const g = rig.groups[name];
    if (!g || !g.n || (g.kind !== "heads" && g.kind !== "cells")) continue;
    const ord = order && ORDERS.includes(order) ? order : g.kind === "heads" ? "x" : "along";
    const key = orderKey(g.keys, ord, g.n, rig.seed || 1);
    for (let m = 0; m < g.n; m++) {
      if (g.kind === "heads") { heads.push(g.members[m]); hSide.push(g.keys.side[m] || 1); hY.push(g.keys.y[m]); hKeyH.push(key[m]); }
      else { cells.push(g.members[m]); cKey.push(key[m]); }
    }
  }
  if (!heads.length && !cells.length) return null;
  const cy = hY.length ? hY.reduce((s, y) => s + y, 0) / hY.length : 0;
  // heads: their rank in the order (ties by index); cells: their place 0..1000 along the order (ties share a place)
  const headRank = heads.length ? rankBy({ k: hKeyH }, "k", heads.length) : new Int32Array(0);
  let lo = Infinity, hi = -Infinity;
  for (const k of cKey) { lo = Math.min(lo, k); hi = Math.max(hi, k); }
  const cellQ = Int32Array.from(cKey.map((k) => (hi > lo ? Math.round(((k - lo) / (hi - lo)) * 1000) : 0)));
  return { name: c.name || names.join("+"), index: i, zone: c.zone || names[0], heads: Int32Array.from(heads), cells: Int32Array.from(cells),
           pan: isNum(c.pan) ? c.pan : null, tilt: isNum(c.tilt) ? c.tilt : null,
           headSide: Float64Array.from(hSide), headLower: Uint8Array.from(hY.map((y) => (y < cy - 0.5 ? 1 : 0))), headRank, cellQ };
}
export function bandFor(cfg, vel) {
  let b = cfg.bands[0];
  for (const x of cfg.bands) if (vel >= x.from - 1e-9) b = x;
  return b;
}

// Every problem with a rig's kick block, as plain sentences (none: [] -- including no block at all, the v0 kick).
export function validateKick(rig) {
  const k = rig.kick;
  if (!k) return [];
  const out = [];
  const err = (m) => out.push(`kick.${m}`);
  if (!Array.isArray(k.deck) || !k.deck.length) err("deck: a list of rows");
  const owner = new Map();
  for (const [i, c] of (k.deck || []).entries()) {
    const names = c && (c.rows || (c.row ? [c.row] : []));
    if (!names || !names.length) { err(`deck[${i}]: {row: a group name} (or rows: [names])`); continue; }
    for (const n of names) {
      const g = rig.groups[n];
      if (!g) { err(`deck[${i}]: no group ${JSON.stringify(n)} in the set`); continue; }
      if (g.kind !== "heads" && g.kind !== "cells") { err(`deck[${i}]: group ${n} is ${g.kind} (heads or LED cells only)`); continue; }
      if (!g.n) err(`deck[${i}]: group ${n} is empty`);
      for (let m = 0; m < g.n; m++) {
        const key = `${g.kind}:${g.members[m]}`;
        const j = owner.get(key);
        if (j !== undefined && j !== i) { err(`deck[${i}] and deck[${j}] share members (${n}): two kicks could light one fixture twice`); break; }
        owner.set(key, i);
      }
    }
    if (c.order !== undefined && !ORDERS.includes(c.order)) err(`deck[${i}].order: one of ${ORDERS.join(", ")}`);
    if (c.pan !== undefined && !(isNum(c.pan) && Math.abs(c.pan) <= 270)) err(`deck[${i}].pan: degrees within +-270`);
    if (c.tilt !== undefined && !(isNum(c.tilt) && Math.abs(c.tilt) <= 135)) err(`deck[${i}].tilt: degrees within +-135`);
  }
  const bands = k.bands || KICK_DEFAULTS.bands;
  if (!Array.isArray(bands) || !bands.length) err("bands: a list");
  else {
    if (!bands.some((b) => b.from === 0)) err("bands: one band must start at velocity 0");
    const names = new Set();
    for (const [i, b] of bands.entries()) {
      if (!b.name || names.has(b.name)) err(`bands[${i}].name: a name of its own`);
      names.add(b.name);
      if (!(isNum(b.from) && b.from >= 0 && b.from <= 1)) err(`bands[${i}].from: a velocity 0..1`);
      if (b.sweep) {
        const C = CLASSES[b.sweep.class];
        if (!C || C.texture) err(`bands[${i}].sweep.class: a whole motion class of vj-motions.js (M8 .. M4b)`);
        if (!(isNum(b.sweep.deg) && b.sweep.deg > 0 && b.sweep.deg <= 90)) err(`bands[${i}].sweep.deg: 0 < deg <= 90`);
      }
    }
  }
  const s = { ...KICK_DEFAULTS.strobe, ...(k.strobe || {}) };
  if (!(isNum(s.max_hz) && s.max_hz > 0 && s.max_hz <= STROBE_HZ_CAP)) err(`strobe.max_hz: above 0 and at most the house cap ${STROBE_HZ_CAP} (got ${s.max_hz})`);
  if (!(isNum(s.from_level) && s.from_level > 0 && s.from_level <= 1)) err("strobe.from_level: a level 0..1");
  if (!(Array.isArray(s.beats) && s.beats.length && s.beats.every((x) => isNum(x) && x > 0))) err("strobe.beats: beat divisions > 0");
  if (!(isNum(s.on) && s.on > 0 && s.on < 1)) err("strobe.on: the lit share of a period, 0..1");
  if (!(isNum(s.floor) && s.floor >= 0 && s.floor < 1)) err("strobe.floor: the dark level, 0 <= floor < 1");
  const lv = { ...KICK_DEFAULTS.level, ...(k.level || {}) };
  if (!(Array.isArray(lv.from_velocity) && lv.from_velocity.length === 2 && lv.from_velocity.every((x) => isNum(x) && x >= 0 && x <= 1))) err("level.from_velocity: [level at velocity 0, level at velocity 1]");
  if (!(isNum(lv.slew_s) && lv.slew_s > 0 && lv.slew_s <= 1)) err("level.slew_s: seconds, 0 < s <= 1");
  for (const key of ["release_beats", "max_hold_beats"]) if (k[key] !== undefined && !(isNum(k[key]) && k[key] > 0)) err(`${key}: beats > 0`);
  if (k.tap_hold_beats !== undefined && !(isNum(k.tap_hold_beats) && k.tap_hold_beats >= 0)) err("tap_hold_beats: beats >= 0");
  if (k.white && k.white.role !== undefined && !KICK_ROLES.includes(k.white.role)) err(`white.role: one of ${KICK_ROLES.join(", ")}`);
  if (k.colour && k.colour.cells !== undefined && !(Array.isArray(k.colour.cells) && k.colour.cells.length && k.colour.cells.every((r) => KICK_ROLES.includes(r)))) err(`colour.cells: roles from ${KICK_ROLES.join(", ")}`);
  return out;
}

// ------------------------------------------------------------------------------------------------------ the deck --
// A seeded shuffle-bag of card indices. deal(eligible) scans the rest of the round in bag order for the first card that
// passes eligible(card, pass) -- pass 0 the strictest (it shows, in another zone), 1 (it shows), 2 the loosest (not live)
// -- and moves it to the front of the rest; a new round's first card is never the one dealt last.
export class KickDeck {
  constructor(n, seed) {
    this.n = n; this.rng = seededRng(...[].concat(seed), "kick-deck"); this.round = 0; this.order = []; this.i = 0; this.last = -1;
    this.forceNext = -1;          // the receipts' door: deal this card next (if no live kick has it), whatever it shows
    this._shuffle();
  }
  _shuffle() {
    const a = Array.from({ length: this.n }, (_, i) => i);
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(this.rng() * (i + 1)); const t = a[i]; a[i] = a[j]; a[j] = t; }
    if (a.length > 1 && a[0] === this.last) { const t = a[0]; a[0] = a[1]; a[1] = t; }
    this.order = a; this.i = 0; this.round++;
  }
  _take(j) {
    const c = this.order[j];
    this.order.splice(j, 1); this.order.splice(this.i, 0, c); this.i++;
    this.last = c;
    return c;
  }
  // Passes 0 and 1 over the rest of the round; when no card left in it can show the hit, the round ends there and a new
  // one is shuffled (the passed-over cards come round again in it); then, over the fresh round, pass 2 (any row no kick
  // shows) and pass 3 (the button's own fading row: a re-press takes it over, as v0's one-row KICK always did).
  deal(eligible) {
    if (this.forceNext >= 0) {
      const f = this.forceNext; this.forceNext = -1;
      if (eligible(f, -1)) { const j = this.order.indexOf(f, this.i); if (j >= 0) return this._take(j); this._shuffle(); return this._take(this.order.indexOf(f)); }
    }
    for (let attempt = 0; attempt < 2; attempt++) {
      for (const pass of [0, 1]) for (let j = this.i; j < this.order.length; j++) if (eligible(this.order[j], pass)) return this._take(j);
      if (attempt === 0) this._shuffle();
    }
    for (const pass of [2, 3]) for (let j = this.i; j < this.order.length; j++) if (eligible(this.order[j], pass)) return this._take(j);
    return -1;
  }
}

// ----------------------------------------------------------------------------------------------------- the kicks --
// One per programmer. press / release / setLevel come from the pads; apply() is the programmer's step 3 each frame.
export class Kicks {
  constructor(prog) {
    this.p = prog;
    this.cfg = kickConfig(prog.rig);
    this.cards = this.cfg.cards;
    // seeded by the set's kick seed and the programmer's (the same set and seed always deal the same rows and motions)
    this.deck = new KickDeck(this.cards.length, [this.cfg.seed, prog.seed]);
    this.motions = new MotionDealer({ seed: `${this.cfg.seed}|${prog.seed}` });
    this.list = [];                       // live kicks
    this.log = [];                        // the last 64 presses, for the receipts
    this.presses = 0; this.passedOver = 0;
    this.lastZone = null;
    this.lastOf = {};                     // kind -> the card it had last
    // the pre-kick state of the last frame (the dealer judges a row on it) and each member's recent peak level
    this.preH = new Float64Array(prog.nH * 7); this.preC = new Float64Array(prog.nC * 4);
    this.recentH = new Float32Array(prog.nH); this.recentC = new Float32Array(prog.nC);
    this.lastPos = null;
    // the one strobe clock: on, and the time (s) of its last edge
    this.clock = { on: true, lastEdge: -Infinity, P: 2, onB: 0.7 };
  }
  kindOf(kind) {
    if (kind === "kick") return "kick-white";
    return KICK_KINDS.includes(kind) ? kind : null;
  }
  levelOfVel(vel) { const [a, b] = this.cfg.level.from_velocity; return clamp01(a + (b - a) * clamp01(vel)); }
  _roleIdx(name) { return Math.max(0, KICK_ROLES.indexOf(name)); }
  // the theme role the colour kick paints on LED cells: the first of the list that is a colour in this theme
  _colourRole() {
    const list = (this.cfg.colour && this.cfg.colour.cells) || ["A"];
    for (const r of list) { const c = this.p.roleRGB[this._roleIdx(r)]; if (c && saturation(c[0], c[1], c[2]) >= SAT_COLOUR) return this._roleIdx(r); }
    return this._roleIdx(list[0]);
  }
  _cellColour(c, buf = this.preC) {
    const b = c * 4, mix = clamp01(buf[b + 1]);
    const c1 = this.p.roleRGB[buf[b + 2] | 0], c2 = this.p.roleRGB[buf[b + 3] | 0];
    return [c1[0] + (c2[0] - c1[0]) * mix, c1[1] + (c2[1] - c1[1]) * mix, c1[2] + (c2[2] - c1[2]) * mix];
  }
  // How a card would show a kick of this kind at this level now: {lift, white, ok}. Heads are judged on the colour their
  // wheel shows (rendered last frame); LED cells on their targets. A chased LED row is judged at its chase floor.
  judge(ci, kind, level, band) {
    const card = this.cards[ci], p = this.p;
    if (this.cfg.legacy) return { lift: 1, white: 0, ok: true };
    let lift = 0, white = 0, n = 0, sat = 0;
    for (const i of card.heads) {
      lift += Math.max(0, level - this.recentH[i]);
      const o = i * 16;
      sat += saturation(p.heads[o + 3], p.heads[o + 4], p.heads[o + 5]);
      n++;
    }
    const nH = n;
    if (nH) {
      const s = sat / nH;
      if (kind === "kick-white" && s >= SAT_COLOUR) return { lift: 0, white: 0, ok: false, why: "the wheel shows a colour" };
      if (kind === "kick-colour" && s < SAT_COLOUR) return { lift: 0, white: 0, ok: false, why: "the wheel shows white" };
    }
    const Lc = level * (band.sweep && card.cells.length ? this.cfg.chase.floor : 1);
    if (card.cells.length) {
      const W = this.p.roleRGB[this._roleIdx(this.cfg.white.role)];
      const sW = saturation(W[0], W[1], W[2]);
      for (const c of card.cells) {
        lift += Math.max(0, Lc - this.recentC[c]);
        if (kind === "kick-white" && Lc >= 0.1) { const col = this._cellColour(c); white += Math.max(0, saturation(col[0], col[1], col[2]) - sW); }
        n++;
      }
    }
    lift /= Math.max(1, n); white /= Math.max(1, n);
    const ok = lift >= KICK_VISIBLE.lift + VIS_MARGIN || (kind === "kick-white" && white >= KICK_VISIBLE.white + VIS_MARGIN);
    return { lift, white, ok };
  }
  // A press: a kick of `kind` at velocity vel and beat position pos. hold: it stays lit until release() (the page's pads);
  // otherwise it is a tap. Returns the kick's record (null if the deck had nothing to give).
  press(kind, vel, pos, { hold = false } = {}) {
    kind = this.kindOf(kind) || "kick-white";
    const cfg = this.cfg, p = this.p;
    this.presses++;
    // a new press of a button lets go of that button's held kick (one finger, one row)
    for (const k of this.list) if (k.kind === kind && k.held) this._release(k, pos);
    const onset = Math.round(pos), from = Math.max(onset, pos);
    const band = bandFor(cfg, vel);
    const level = this.levelOfVel(vel);
    // the rows live kicks show: the other button's are never dealt; this button's own fading one only as the last resort
    const aliveOther = new Set(this.list.filter((k) => k.kind !== kind).map((k) => k.cardIndex));
    const aliveMine = new Set(this.list.filter((k) => k.kind === kind).map((k) => k.cardIndex));
    const lastMine = this.lastOf[kind] ?? -1;
    let passed = 0;
    const judged = new Map();
    const ci = this.deck.deal((c, pass) => {
      if (aliveOther.has(c)) return false;
      if (pass === -1 || pass === 3) return true;                     // a forced card (tests and receipts); the last resort
      if (aliveMine.has(c)) return false;
      if (pass === 2) return c !== lastMine;                          // nothing shows anywhere: the next row anyway
      if (c === lastMine || (c === this.deck.last && this.cards.length > 2)) return false;
      let j = judged.get(c);
      if (!j) { j = this.judge(c, kind, level, band); judged.set(c, j); if (!j.ok) passed++; }
      return pass === 0 ? j.ok && this.cards[c].zone !== this.lastZone : j.ok;
    });
    this.passedOver += passed;
    if (ci < 0) return null;
    const card = this.cards[ci];
    // a re-press on this button's own fading row takes it over from the moment the new kick lights
    for (const k of this.list) if (k.kind === kind && k.cardIndex === ci) k.supersededAt = from;
    this.lastOf[kind] = ci; this.lastZone = card.zone;
    // was the row dark when it was dealt (then the card's own pan and tilt aim it)?
    let dark = true;
    for (const i of card.heads) if (this.recentH[i] > 0.05) { dark = false; break; }
    // the colour kick keeps a lit LED's own colour when it is already a colour; everything else takes the button's colour
    let paint = null;
    if (!cfg.legacy && card.cells.length) {
      paint = new Int8Array(card.cells.length);
      const role = kind === "kick-white" ? this._roleIdx(cfg.white.role) : this._colourRole();
      for (let m = 0; m < card.cells.length; m++) {
        const c = card.cells[m];
        if (kind === "kick-colour" && cfg.colour.keep_lit_colour && this.recentC[c] > 0.05) {
          const col = this._cellColour(c);
          if (saturation(col[0], col[1], col[2]) >= SAT_COLOUR) { paint[m] = -1; continue; }
        }
        paint[m] = role;
      }
    }
    // the motion (velocity's animation): one dealt from the V2 library on the band's class, looping while held
    let motion = null;
    this.motions.press(pos);
    if (band.sweep && !cfg.legacy) motion = this._motion(card, band, vel, from);
    const rec = { kind, card, cardIndex: ci, round: this.deck.round, onset, from, pressPos: pos, vel, band: band.name, levelTarget: level, level,
                  held: !!hold, releasedAt: null, holdEnd: null, dark, paint, motion, attached: false, strobing: false, maskOn: true,
                  lit: false, dead: false };
    if (!hold) this._release(rec, pos);
    this.list.push(rec);
    if (this.log.length >= 64) this.log.shift();
    this.log.push({ kind, row: card.name, onset, pressPos: +pos.toFixed(4), vel: +vel.toFixed(3), band: band.name, motion: motion ? motion.id : null, passed });
    return rec;
  }
  _motion(card, band, vel, from) {
    const p = this.p, perMs = p.perMs || 400, bar = p.barAnchor || 0;
    const d = this.motions.deal({ pos: from - bar, perMs, vel, pinClass: band.sweep.class, looping: true, gaps: false, bank: "both",
                                  lifeBeats: CLASSES[band.sweep.class].beats });
    if (!d) return null;
    const m = d.m;
    const st = { m, p0: d.p0 + bar, p1: d.p1 + bar, beats: d.beats, looping: true, rev: d.rev, rotK: d.rotK };
    // heads: each one's sign (the motion's mode, the transform's mirrors) and the throw the motor can make
    const nH = card.heads.length;
    const sign = new Float64Array(nH);
    const aimN = (m.aim || 0) / 0.5, spreadN = (m.spread || 0) / 0.5;
    let smax = 0;
    for (let k = 0; k < nH; k++) {
      const side = card.headSide[k] || 1, lower = !!card.headLower[k];
      let s = aimN * headSign(m.mode, { side, bank: "A", lower }, card.headRank[k]);
      if (d.mx) s = -s;
      if (d.my && lower) s = -s;
      s += spreadN * side;
      sign[k] = s; smax = Math.max(smax, Math.abs(s));
    }
    // the throw: the band's degrees x the dealer's amplitude (velocity, the press's place in the bar), cut so the motion's
    // steepest moment asks at most 80 % of the slowest head's tilt speed. Its acceleration is left to the motor model
    // (programmer.js Slew, 0.2 s to full speed): a sharp start is rounded off there, as a real head rounds it off.
    const want = band.sweep.deg * d.amp;
    let deg = want, peakDegPerS = 0;
    if (nH && smax > 0) {
      const span = Math.max(1e-3, Math.min(d.p1 - d.p0, d.beats) * perMs / 1000);
      const slope = m.stats.slope / Math.max(0.1, 1 - (m.lag || 0));
      let vmax = Infinity;
      for (const i of card.heads) vmax = Math.min(vmax, p.slews[i].tilt.vmax);
      const rate = (A) => (A * smax * slope) / span;
      if (rate(deg) > 0.8 * vmax) deg *= (0.8 * vmax) / rate(deg);
      peakDegPerS = rate(deg);
    }
    // LED cells: the same motion as a chase, its order wave at least `lag` wide so it travels along the row
    const chaseSt = card.cells.length ? { ...st, m: { ...m, lag: Math.max(m.lag || 0, this.cfg.chase.lag) }, rotK: 0 } : null;
    return { id: d.id, label: d.label, cls: d.cls, xf: d.xf, amp: d.amp, want, deg, peakDegPerS, st, sign, chaseSt };
  }
  _release(k, pos) {
    if (k.releasedAt !== null) return;
    k.held = false; k.releasedAt = pos;
    k.holdEnd = Math.max(pos, k.from + this.cfg.tap_hold_beats);
    k.attached = false;                    // its strobe mask is frozen where it is: the fade adds no edge
  }
  release(kind, pos) { kind = this.kindOf(kind); for (const k of this.list) if (k.kind === kind && k.held) this._release(k, pos); }
  // the live level (the finger's height on the pad): every held kick of this kind
  setLevel(kind, v) { kind = this.kindOf(kind); if (!Number.isFinite(v)) return; for (const k of this.list) if (k.kind === kind && k.held) k.levelTarget = clamp01(v); }
  _env(k, pos) {
    if (pos < k.from - 1e-6) return 0;
    if (k.held) {
      if (pos - k.from >= this.cfg.max_hold_beats) this._release(k, pos);        // a stuck pad lets go
      else return 1;
    }
    return pos <= k.holdEnd ? 1 : Math.exp(-(pos - k.holdEnd) / this.cfg.release_beats);
  }
  // v0's kickLevel: the brightest kick now (before its strobe)
  levelNow(pos) { let lv = 0; for (const k of this.list) lv = Math.max(lv, this._env(k, pos) * k.level); return lv; }
  // the strobe's period (beats) and lit share at this tempo: the shortest of the set's divisions at or under the cap
  _strobeGrid(perMs) {
    const S = this.cfg.strobe, bps = 1000 / perMs, hz = Math.min(STROBE_HZ_CAP, S.max_hz);
    const divs = S.beats.slice().sort((a, b) => a - b);
    let P = divs.find((x) => bps / x <= hz + 1e-9);
    if (P === undefined) P = bps / hz;
    const minB = STROBE_MIN_EDGE_S * bps;
    const onB = Math.min(P - minB, Math.max(minB, S.on * P));
    return { P, onB };
  }
  // the programmer's step 3: remember the frame before the kicks, then light the kicks' rows
  apply(pos, tSec, dt) {
    const p = this.p, tH = p.tH, tC = p.tC, cfg = this.cfg;
    this.preH.set(tH); this.preC.set(tC);
    const dB = this.lastPos === null ? 0 : Math.max(0, pos - this.lastPos);
    this.lastPos = pos;
    const fall = cfg.recent_fall_per_beat * dB;
    for (let i = 0; i < p.nH; i++) { const d = tH[i * 7 + 2]; this.recentH[i] = Math.max(d, this.recentH[i] - fall); }
    for (let c = 0; c < p.nC; c++) { const d = tC[c * 4]; this.recentC[c] = Math.max(d, this.recentC[c] - fall); }
    if (!this.list.length) return;
    // the strobe clock: it runs while some held kick is at the top of its level (or has joined it)
    const S = cfg.strobe, clk = this.clock;
    const g = this._strobeGrid(p.perMs || 400);
    clk.P = g.P; clk.onB = g.onB;
    let wanted = false;
    for (const k of this.list) if (k.held && k.lit && k.levelTarget >= S.from_level - 1e-9) wanted = true;
    // the first row to want the strobe joins at once (the strobe engages as the level crosses into the band), and the
    // clock does not flip within an edge's spacing of that row's own light-up; later rows join while the clock is lit
    if (wanted && clk.on && !this.list.some((k) => k.attached)) {
      for (const k of this.list) if (k.held && k.lit && k.levelTarget >= S.from_level - 1e-9) { k.attached = true; clk.lastEdge = Math.max(clk.lastEdge, k.litAt); }
    }
    let want = true;
    if (wanted || this.list.some((k) => k.attached)) {
      const ph = (((pos - (p.barAnchor || 0)) % g.P) + g.P) % g.P;
      want = ph < g.onB;
    }
    if (want !== clk.on && tSec - clk.lastEdge >= STROBE_MIN_EDGE_S - 1e-9) { clk.on = want; clk.lastEdge = tSec; }
    const slewK = 1 - Math.exp(-Math.max(0, dt) / cfg.level.slew_s);
    for (const k of this.list) {
      const env = this._env(k, pos);
      if (pos < k.from - 1e-6) continue;                                   // an early press waits for its line
      if (!k.lit) {
        k.lit = true; k.litAt = tSec;
        // a kick lighting while the clock is idle starts the clock's count from its own edge
        if (k.levelTarget >= S.from_level - 1e-9 && !this.list.some((o) => o !== k && o.attached)) clk.lastEdge = Math.max(clk.lastEdge, tSec);
      }
      if ((k.releasedAt !== null && pos > k.holdEnd && env < 0.004) || (k.supersededAt !== undefined && pos >= k.supersededAt - 1e-6)) { k.dead = true; continue; }
      k.level += (k.levelTarget - k.level) * slewK;
      // join or leave the strobe clock only while it is on (so a joining or leaving row adds no edge of its own)
      if (k.held) {
        const wants = k.levelTarget >= S.from_level - 1e-9;
        if (wants && !k.attached && clk.on) k.attached = true;
        else if (!wants && k.attached && clk.on) k.attached = false;
        k.maskOn = k.attached ? clk.on : true;
      }
      k.strobing = k.attached;
      const off = !k.maskOn;                                               // the strobe clock's dark phase
      const lv = env * k.level;
      const floor = S.floor;
      const card = k.card, mo = k.motion;
      // heads: the level (highest takes precedence; a strobe's dark phase takes the row down), the dark row's aim, the sweep
      for (let m = 0; m < card.heads.length; m++) {
        const i = card.heads[m], b = i * 7;
        if (off) tH[b + 2] = floor * env;
        else tH[b + 2] = Math.max(tH[b + 2], lv);
        if (k.dark) { if (card.pan !== null) tH[b] = card.pan; if (card.tilt !== null) tH[b + 1] = card.tilt; }
        if (mo && mo.deg > 0) {
          const v = valueAt(mo.st, pos, card.headRank[m], card.heads.length);
          const t = tH[b + 1] + mo.deg * v * mo.sign[m];
          tH[b + 1] = Math.max(-135, Math.min(135, t));
        }
      }
      // LED cells: the level (a chase on the sweep bands, solid while strobing), and the button's colour, which fades
      // back to the look's with the light
      if (card.cells.length) {
        const chase = mo && mo.chaseSt && !k.strobing ? mo.chaseSt : null;
        const fl = cfg.chase.floor;
        const w = clamp01(env);
        for (let m = 0; m < card.cells.length; m++) {
          const c = card.cells[m], b = c * 4;
          let x = lv;
          if (chase) x *= fl + (1 - fl) * Math.min(1, Math.abs(valueAt(chase, pos, card.cellQ[m], 1001)));
          if (off) tC[b] = floor * env;
          else tC[b] = Math.max(tC[b], x);
          const role = k.paint ? k.paint[m] : -1;
          if (role >= 0) {
            const lead = tC[b + 1] <= 0.5 ? tC[b + 2] : tC[b + 3];          // the look's main role under the paint
            tC[b + 2] = lead; tC[b + 3] = role; tC[b + 1] = w;
          }
        }
      }
    }
    if (this.list.some((k) => k.dead)) this.list = this.list.filter((k) => !k.dead);
  }
  status() {
    return { api: KICK_API, legacy: this.cfg.legacy, presses: this.presses, passed_over: this.passedOver, round: this.deck.round,
             clock: { on: this.clock.on, period_beats: this.clock.P, on_beats: +this.clock.onB.toFixed(3) },
             live: this.list.map((k) => ({ kind: k.kind, row: k.card.name, band: k.band, level: +k.level.toFixed(3), target: +k.levelTarget.toFixed(3),
                                           held: k.held, strobing: k.strobing, motion: k.motion ? k.motion.id : null, onset: k.onset })),
             log: this.log.slice(-32) };
  }
}
