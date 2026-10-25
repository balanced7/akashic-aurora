// Virtual Stage v0, the laser brain: arsenal/web/stage/lasers.js (pure ES module). Tests: tests/stage_lasers.test.mjs.
//
// THE CONTRACT IS LASERS V2's. The Lasers v2 engine (arsenal/web/vj-lasers.js, "arsenal.vj-lasers/v1", built on its own
// lane and not on master when this was written) is meant to be the single laser brain for every surface. This module is
// the minimal local stand-in the stage brief allows until it lands: the same 21 heads (Bank A on the overhead truss,
// Bank B on the floor, two heads on each side tower, the hero), the same picture frame (centred units, frame height 1,
// +y up, the hero point at (0, 0.05)), the same segment layout (16 floats per segment: x0 y0 x1 y1 | r g b intensity |
// width glow blur heat | kind head falloff flags), the same clock interface ({bpm, posAt, phaseAt, nextBeatAt, alive}),
// hit() / release() / frame(t). When vj-lasers.js reaches master, lasers3d.js takes its frame() output unchanged and this
// file retires. What it does NOT have (Lasers v2 does): the 17-pattern deck with anti-repeat signatures, the 15 named
// gates, Vibrate, the figure shapes, the area estimator and its budgets.
//
// What it has: hits on a pad with retrigger tiers measured in beats since the previous press (more than a bar = one
// burst; within a bar = a one-two; within a beat = a triple), hold = a quarter-note gate; pulses whose onsets sit on the
// grid; eight hit patterns (fan, cross, scissors, crown, cone, rain, sweep, chase) dealt from a seeded deck; and the
// continuous LOOKS a section runs under the hits (lattice, ceiling, tunnel, fans), which move with the beat position and
// never gate. Red is never emitted: a saturated red (R / (R + G + B) >= 0.8) is swapped for the theme's next colour.
// Safety in 3D (until Lasers v2's area estimator can read the 3D picture): fast gates dip to GATE_FLOOR, never to black;
// a new fast hit chokes the older fast ones; a press within a quarter beat of the last onset retriggers that hit
// instead of starting another (a pad storm becomes one held gate, not fifteen onsets a second).
//
// v1 (2026-10-25), LASER GROUPS: Daniel wants "the ability to tie groups of lasers together and allow them to play
// various "animations" and triggers". The scene's laser_groups (rig.js buildLaserGroups: banks A, B, S, H and the halo's
// R, by level) are addressed by phrase steps; each group line runs a SHAPE (fan, sweep, chase across the bank in x order,
// scissors, ceiling, lattice, tunnel, fans, rain, bloom: an entry that opens on the ONE, levels: the halo lasers fire
// with their third on the phrase's level schedule, rim-corona: one spoke per halo laser, lit as the ring's chopper blade
// passes) through a GATE (none, onetwo: two pulses a beat, triple: three a beat; both dip to GATE_FLOOR, never to black).
// The output contract does not change: the same 16-float segments, the same picture frame. The 21 Lasers v2 heads keep
// their indices 0..20; heads past them (the halo lasers) are placed in the picture where the front-of-house camera sees
// their projectors. A laser on a ring points where the ring holds it, which a flat picture cannot say: out.aim carries a
// per-head aim override [x, y, z, k] (k: the depth ratio, 0 = none) that lasers3d.js reads, a side channel beside the
// picture rather than a change to it. While a phrase owns the lasers, the section's look is muted (setLookMute).

import { spreadValues, waveform } from "./effects.js";

export const LASERS_API = "arsenal.stage-lasers/v1";
export const CONTRACT = "arsenal.vj-lasers/v1";
export const HERO = Object.freeze({ x: 0, y: 0.05 });
export const SEG_FLOATS = 16;
export const MAX_SEGMENTS = 512;
export const SEG = Object.freeze({ X0: 0, Y0: 1, X1: 2, Y1: 3, R: 4, G: 5, B: 6, I: 7, WIDTH: 8, GLOW: 9, BLUR: 10,
  HEAT: 11, KIND: 12, HEAD: 13, FALLOFF: 14, FLAGS: 15 });
export const KIND = Object.freeze({ BEAM: 0, FIGURE: 1 });

const TAU = Math.PI * 2;
const ASPECT = 16 / 9;
const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const frac = (x) => x - Math.floor(x);

// The 21 heads, as Lasers v2 places them: u = a fraction of the half-width, y in frame heights.
const BANK_U = [-0.84, -0.6, -0.36, -0.12, 0.12, 0.36, 0.6, 0.84];
const DEFS = [
  ...BANK_U.map((u, i) => ({ name: `A${i + 1}`, bank: "A", u, y: 0.47 })),
  ...BANK_U.map((u, i) => ({ name: `B${i + 1}`, bank: "B", u, y: -0.47 })),
  { name: "SL1", bank: "S", u: -0.9, y: -0.12 }, { name: "SL2", bank: "S", u: -0.9, y: 0.18 },
  { name: "SR1", bank: "S", u: 0.9, y: -0.12 }, { name: "SR2", bank: "S", u: 0.9, y: 0.18 },
  { name: "HERO", bank: "H", u: 0, y: HERO.y },
];
export const HEADS = Object.freeze(DEFS.map((d, i) => Object.freeze({ ...d, index: i, sx: (d.u * ASPECT) / 2 })));
export const BANK_A = Object.freeze(HEADS.filter((h) => h.bank === "A").map((h) => h.index));
export const BANK_B = Object.freeze(HEADS.filter((h) => h.bank === "B").map((h) => h.index));
export const SIDE = Object.freeze(HEADS.filter((h) => h.bank === "S").map((h) => h.index));
export const HERO_HEAD = HEADS.length - 1;

// Heads past the 21: from the scene's projectors (index 21 on), placed in the picture by their 3D position (the same
// linear map that puts Bank A's truss at y 0.47 and Bank B's floor at -0.47: x 17.5 m -> 0.747, y 22 m -> 0.47).
export const PICTURE = Object.freeze({ sx_per_m: 0.746667 / 17.5, y_per_m: 0.94 / 19.7, y0_m: 22 - 0.47 / (0.94 / 19.7) });
export function extraHeadsFrom(projectors) {
  return (projectors || []).slice(HEADS.length).map((p, k) => Object.freeze({
    name: p.name, bank: p.bank, index: HEADS.length + k, u: 0, sx: p.pos[0] * PICTURE.sx_per_m, y: (p.pos[1] - PICTURE.y0_m) * PICTURE.y_per_m,
    level: p.level ?? -1, clock: p.clock ?? null, pos: p.pos.slice(), radial: p.radial ? p.radial.slice() : null, normal: p.normal ? p.normal.slice() : null,
  }));
}
export const GROUP_SHAPES = Object.freeze(["fan", "sweep", "chase", "scissors", "ceiling", "lattice", "tunnel", "fans", "rain", "bloom", "levels", "rim-corona"]);
export const GROUP_GATES = Object.freeze(["none", "onetwo", "triple"]);
// A group gate's level at `age` beats into its line: the one-two (two pulses a beat) and the triple (three a beat) dip to
// GATE_FLOOR between pulses, the fast-gate rule.
export function groupGate(gate, age) {
  if (!gate || gate === "none") return 1;
  const x = age - Math.floor(age + 1e-9);
  if (gate === "onetwo") return x < 0.25 - 1e-9 || (x >= 0.5 - 1e-9 && x < 0.75 - 1e-9) ? 1 : GATE_FLOOR;
  if (gate === "triple") return x < 0.125 - 1e-9 || (x >= 0.25 - 1e-9 && x < 0.375 - 1e-9) || (x >= 0.5 - 1e-9 && x < 0.625 - 1e-9) ? 1 : GATE_FLOOR;
  throw new Error(`unknown laser gate ${gate}`);
}

export const PATTERNS = Object.freeze(["fan", "cross", "scissors", "crown", "cone", "rain", "sweep", "chase"]);
export const LOOKS = Object.freeze(["off", "lattice", "ceiling", "tunnel", "fans"]);
// pulses {at, len} in beats from the onset, then a tail (beats) on the last
// FAST gates (more than one pulse a beat: the one-two, the triple, the held gate) dip to GATE_FLOOR between pulses instead
// of to black: in 3D a fan can fill the frame when the camera flies through it, and a full-depth strobe of that much light
// is a flash. A lift, not a flash -- the dimmers' rule (effects.js), applied to the lasers until Lasers v2's area
// estimator can read the 3D picture (its areaProject hook, design 4.6).
export const GATE_FLOOR = 0.7;
export const MIN_ONSET_BEATS = 0.25;      // presses closer than a quarter beat retrigger the current hit (no new onset)
export const GATES = Object.freeze({
  burst:  { pulses: [{ at: 0, len: 0.5 }], tail: 0.5 },
  onetwo: { pulses: [{ at: 0, len: 0.25 }, { at: 0.5, len: 0.25 }], tail: 0.25 },
  triple: { pulses: [{ at: 0, len: 0.125 }, { at: 0.25, len: 0.125 }, { at: 0.5, len: 0.125 }], tail: 0.25 },
  hold:   { loop: 0.5, on: 0.25, tail: 0.25 },
});

// Saturated red (the theme library's rule, on linear values): never emitted by a laser.
export function isSaturatedRed(c) { const s = c[0] + c[1] + c[2]; return s > 1e-6 && c[0] / s >= 0.8; }
export function hexToLinear(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
  if (!m) return [1, 1, 1];
  const v = parseInt(m[1], 16);
  const lin = (c) => { const s = c / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
  return [lin((v >> 16) & 255), lin((v >> 8) & 255), lin(v & 255)];
}
// the theme's laser colours with any saturated red replaced (the next safe colour, else a warm white)
export function laserPalette(colours) {
  const lin = (colours && colours.length ? colours : ["#19ff4a", "#4a3cff", "#e6ffe9"]).map((c) => (Array.isArray(c) ? c.slice() : hexToLinear(c)));
  const safe = lin.filter((c) => !isSaturatedRed(c));
  const fallback = safe.length ? safe : [[1, 0.85, 0.6]];
  return lin.map((c, i) => (isSaturatedRed(c) ? fallback[i % fallback.length] : c));
}

function rngOf(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class LaserEngine {
  constructor({ seed = 2014, clock = null, colours = null, fallbackBpm = 150, heads = null } = {}) {
    this.heads = heads && heads.length ? [...HEADS, ...heads.filter((h) => h.index >= HEADS.length)] : HEADS;
    this.groupLines = [];
    this.lookMute = false;
    this.groupStats = { lines: 0, frames: 0, segments: 0, byGroup: {} };
    this.seed = seed;
    this.clock = clock;
    this.fallbackBpm = fallbackBpm;
    this.palette = laserPalette(colours);
    this.rng = rngOf(seed);
    this.deck = [];
    this.hits = [];
    this.lastHitPos = -Infinity;
    this.down = null;           // the hit a held pad is driving
    this.look = { name: "off", level: 0, reach: 1 };
    this.section = "any";
    this.count = 0;              // onsets (new hits)
    this.presses = 0;            // pad presses (a press within a quarter beat retriggers instead of starting a hit)
    this.out = { t: 0, pos: 0, seg: new Float32Array(MAX_SEGMENTS * SEG_FLOATS), n: 0, heads: new Float32Array(this.heads.length),
                 aim: new Float32Array(this.heads.length * 4), events: [], pattern: "", gate: "", look: "off", reach: 1, hits: 0, groups: 0 };
  }
  setClock(c) { this.clock = c; }
  setColours(colours) { this.palette = laserPalette(colours); }
  setLook(name, level = 1, reach = 1) {
    this.look = { name: LOOKS.includes(name) ? name : "off", level: clamp01(level), reach: reach > 0 ? reach : 1 };
  }
  setSection(name) { this.section = String(name || "any"); }
  setLookMute(on) { this.lookMute = !!on; }
  // Phrase group lines (phrases.js compiled laser lines {group, heads, laser: {shape, gate, ...}}) anchored on pos;
  // replace: a new step (the previous lines go), otherwise a cue adds to them.
  setGroupLines(lines, pos, { replace = true } = {}) {
    if (replace) this.groupLines = [];
    for (const l of lines || []) {
      if (!l || l.kind !== "lasers") continue;
      if (!GROUP_SHAPES.includes(l.laser.shape)) throw new Error(`unknown laser shape ${l.laser.shape}`);
      groupGate(l.laser.gate, 0);
      this.groupLines.push({ ...l.laser, heads: l.heads.filter((h) => h < this.heads.length), group: l.group, anchor: pos });
      this.groupStats.lines++;
    }
  }
  clearGroups() { this.groupLines = []; }
  posAt(t) {
    const c = this.clock;
    if (c && typeof c.posAt === "function") return c.posAt(t);
    return (t * this.fallbackBpm) / 60000;
  }
  _deal() {
    if (!this.deck.length) {
      this.deck = PATTERNS.slice();
      for (let i = this.deck.length - 1; i > 0; i--) { const j = Math.floor(this.rng() * (i + 1)); [this.deck[i], this.deck[j]] = [this.deck[j], this.deck[i]]; }
    }
    return this.deck.pop();
  }
  // A pad press at time t (ms) with velocity 0..1. The onset sits on the nearest quarter beat at or after the press
  // (within an eighth: a press just after the line keeps the line), so pulses land on the grid.
  hit(t, vel = 0.8) {
    const pos = this.posAt(t);
    const since = pos - this.lastHitPos;
    this.presses++;
    // a press within a quarter beat of the last onset retriggers that hit: it stays lit as a gate while held
    if (since < MIN_ONSET_BEATS && this.hits.length) {
      const h = this.hits[this.hits.length - 1];
      h.held = true; h.released = null; h.gate = "hold"; h.vel = Math.max(h.vel, clamp01(vel));
      this.down = h;
      return h;
    }
    this.lastHitPos = pos;
    const tier = since > 4 ? "burst" : since > 1 ? "onetwo" : "triple";
    const q = Math.round(pos * 4) / 4;
    const onset = q < pos - 0.125 ? q + 0.25 : q;
    const pattern = this._deal();
    const k = this.count++;
    const bank = ["A", "B", "both", "alternate"][k % 4];
    const heads = bank === "A" ? BANK_A : bank === "B" ? BANK_B : bank === "both" ? [...BANK_A, ...BANK_B]
                : (k % 2 ? BANK_A : BANK_B);
    const h = { k, onset, pattern, tier, gate: tier, vel: clamp01(vel), heads: pattern === "crown" ? [HERO_HEAD] : heads,
                colour: k % this.palette.length, colour2: (k + 1) % this.palette.length, seed: (this.seed * 7919 + k) >>> 0,
                released: null, held: true };
    // a new fast hit chokes the older fast ones (as Lasers v2 does): one strobing picture at a time
    if (tier !== "burst") this.hits = this.hits.filter((o) => o.tier === "burst" && !o.held);
    this.hits.push(h);
    while (this.hits.length > 4) this.hits.shift();
    this.down = h;
    this.out.events.push({ type: "hit", k, pattern, tier, onset });
    return h;
  }
  release(t) {
    if (!this.down) return;
    const pos = this.posAt(t);
    // a press held past half a beat became a gate: it runs until now, then its tail
    if (this.down.gate === "hold") this.down.released = Math.max(pos, this.down.onset);
    this.down.held = false;
    this.down = null;
  }
  // the hit's level at beat position pos: its gate's pulses (1 inside a pulse, the tail fading after the last)
  level(h, pos) {
    if (pos - h.onset < -1e-6) return 0;                         // within float error of its line it is on it
    const age = Math.max(0, pos - h.onset);
    if (h.held && h.gate !== "hold" && age > 0.5) { h.gate = "hold"; }
    const g = GATES[h.gate];
    if (h.gate === "hold") {
      const end = h.released;
      if (end !== null && pos >= end) { const tAge = pos - end; return tAge < g.tail ? 1 - tAge / g.tail : 0; }
      return frac(age / g.loop) * g.loop < g.on ? 1 : GATE_FLOOR;
    }
    const fast = g.pulses.length > 1;
    for (const p of g.pulses) if (age >= p.at && age < p.at + p.len) return 1;
    const last = g.pulses[g.pulses.length - 1];
    if (fast && age < last.at + last.len) return GATE_FLOOR;          // between the pulses of a fast gate
    const tAge = age - (last.at + last.len);
    const from = 1;
    return tAge >= 0 && tAge < g.tail ? from * (1 - tAge / g.tail) : 0;
  }
  frame(t) {
    const o = this.out;
    o.t = t; o.n = 0; o.heads.fill(0); o.events.length = 0; o.aim.fill(0); o.groups = 0;
    const pos = this.posAt(t);
    o.pos = pos;
    for (const h of this.hits) {
      const lv = this.level(h, pos) * (0.55 + 0.45 * h.vel);
      if (lv <= 0) continue;
      this._pattern(h, pos, lv);
      o.pattern = h.pattern; o.gate = h.gate;
    }
    this.hits = this.hits.filter((h) => !(h.released !== null && pos > h.released + 1) && pos - h.onset < 64 && (h.held || h.gate === "hold" || pos - h.onset < 4));
    o.groupStart = o.n;                                   // the phrase group segments follow the hits
    if (this.groupLines.length) {
      const n0 = o.n;
      this._groups(pos);
      o.groups = o.n - n0;
      if (o.groups) { this.groupStats.frames++; this.groupStats.segments += o.groups; }
    }
    if (!this.lookMute && this.look.name !== "off" && this.look.level > 0) this._look(pos, this.look.level);
    o.look = this.lookMute ? "phrase" : this.look.name; o.reach = this.look.reach; o.hits = this.hits.length;
    return o;
  }
  _emit(head, x1, y1, col, intensity, width = 1.6) {
    const o = this.out;
    if (o.n >= MAX_SEGMENTS || intensity <= 0) return;
    const h = this.heads[head];
    const s = o.n * SEG_FLOATS, c = this.palette[((col % this.palette.length) + this.palette.length) % this.palette.length];
    o.seg[s + SEG.X0] = h.sx; o.seg[s + SEG.Y0] = h.y; o.seg[s + SEG.X1] = x1; o.seg[s + SEG.Y1] = y1;
    o.seg[s + SEG.R] = c[0]; o.seg[s + SEG.G] = c[1]; o.seg[s + SEG.B] = c[2]; o.seg[s + SEG.I] = intensity;
    o.seg[s + SEG.WIDTH] = width; o.seg[s + SEG.GLOW] = intensity; o.seg[s + SEG.BLUR] = 0; o.seg[s + SEG.HEAT] = 0;
    o.seg[s + SEG.KIND] = KIND.BEAM; o.seg[s + SEG.HEAD] = head; o.seg[s + SEG.FALLOFF] = 0.5; o.seg[s + SEG.FLAGS] = 0;
    o.n++;
    o.heads[head] = Math.max(o.heads[head], intensity);
  }
  // a beam from head h at angle a (radians, 0 = +x, pi/2 = up) of length L
  _ray(head, a, L, col, lv) { const h = this.heads[head]; this._emit(head, h.sx + L * Math.cos(a), h.y + L * Math.sin(a), col, lv); }
  _toHero(hd) { const h = this.heads[hd]; return Math.atan2(HERO.y - h.y, HERO.x - h.sx); }
  _dirOf(hd, dir) {
    if (dir === "up") return Math.PI / 2;
    if (dir === "down") return -Math.PI / 2;
    if (dir === "out") return this._toHero(hd) + Math.PI;
    return this._toHero(hd);
  }
  _fan(hd, centre, spread, nB, col, lv, L = 2.2) {
    if (nB <= 1) { this._ray(hd, centre, L, col, lv); return; }
    for (let b = 0; b < nB; b++) this._ray(hd, centre + spread * (b / (nB - 1) - 0.5), L, col, lv);
  }
  // the phrase's laser group lines
  _groups(pos) {
    const DEG = Math.PI / 180;
    for (const L of this.groupLines) {
      const age = pos - L.anchor;
      if (L.from_beats !== undefined && age < L.from_beats - 1e-9) continue;
      if (L.until_beats !== undefined && age >= L.until_beats - 1e-9) continue;
      const local = age - (L.from_beats || 0);
      const lv = clamp01(L.level ?? 0.8) * groupGate(L.gate, local);
      if (lv <= 0) continue;
      const col = L.colour ?? 0, col2 = L.colour2 ?? col + 1;
      const heads = L.heads, n0 = this.out.n;
      switch (L.shape) {
        case "fan": for (const hd of heads) this._fan(hd, this._dirOf(hd, L.dir), (L.spread ?? 36) * DEG, L.beams ?? 5, col, lv); break;
        case "sweep": {
          const sw = Math.sin((local / (L.measure ?? 4)) * TAU) * (L.swing ?? 30) * DEG;
          for (const hd of heads) this._fan(hd, this._dirOf(hd, L.dir) + (L.mirror && this.heads[hd].sx < 0 ? -sw : sw), (L.spread ?? 24) * DEG, L.beams ?? 4, col, lv);
          break;
        }
        case "chase": {
          if (!heads.length) break;
          const slot = Math.floor(frac(local / (L.measure ?? 2)) * heads.length) % heads.length;
          this._fan(heads[slot], this._dirOf(heads[slot], L.dir), (L.spread ?? 30) * DEG, L.beams ?? 4, col, lv);
          break;
        }
        case "scissors": {
          const step = Math.floor(local * 2) % 2 ? 1 : -1;
          for (const [j, hd] of heads.entries()) this._ray(hd, this._toHero(hd) + step * Math.sign(this.heads[hd].sx || 1) * 0.35, 2.2, j % 2 ? col2 : col, lv);
          break;
        }
        case "ceiling": {
          const sway = Math.sin((pos / 8) * TAU) * 0.08;
          for (const hd of heads) for (let b = 0; b < 5; b++) this._ray(hd, Math.PI / 2 + (b / 4 - 0.5) * 1.1 + sway, 0.5, col, lv * 0.7);
          break;
        }
        case "lattice": {
          const breathe = Math.sin((pos / 16) * TAU) * 0.16;
          for (const hd of heads) {
            const up = this.heads[hd].y < 0;
            for (const sg of [-1, 1]) this._ray(hd, (up ? Math.PI / 2 : -Math.PI / 2) + sg * (0.45 + (up ? breathe : -breathe)), 2.4, sg > 0 ? col : col2, lv * 0.7);
          }
          break;
        }
        case "tunnel": {
          const spin = (pos / 8) * TAU;
          for (const hd of heads) for (let b = 0; b < 12; b++) {
            const a = spin + (TAU * b) / 12, h = this.heads[hd];
            this._emit(hd, HERO.x + 0.3 * Math.cos(a) + (h.sx - HERO.x) * 0.0, HERO.y + 0.3 * Math.sin(a), b % 2 ? col2 : col, lv);
          }
          break;
        }
        case "fans": {
          const open = 0.5 + 0.5 * Math.sin((pos / 8) * TAU);
          for (const hd of heads) this._fan(hd, this._toHero(hd), 0.3 + 0.9 * open, 7, col, lv * 0.8, 2.4);
          break;
        }
        case "rain": for (const hd of heads) this._ray(hd, this.heads[hd].y > 0 ? -Math.PI / 2 : Math.PI / 2, 2.2, col, lv); break;
        case "bloom": {
          // the entry on the ONE: each head's fan opens from a closed beam to its full spread over open_beats
          const open = Math.min(1, Math.max(0, local / (L.open_beats ?? 1)));
          for (const hd of heads) this._fan(hd, this._toHero(hd), (L.spread ?? 64) * DEG * (0.08 + 0.92 * open), L.beams ?? 7, col, lv * (1 - 0.15 * open));
          break;
        }
        case "levels": this._levels(L, local, lv, col); break;
        case "rim-corona": this._corona(L, local, lv, col); break;
        default: break;
      }
      const made = this.out.n - n0;
      if (made) this.groupStats.byGroup[L.group] = (this.groupStats.byGroup[L.group] || 0) + made;
    }
  }
  // the halo lasers on the level schedule (the same effect definition the halo heads run, so they fire with their third)
  _levels(L, age, lv, col) {
    const def = L.scheduleDef || { form: "square", width: 1 / 3, transition: 0.2, measure: 3, phase: { order: "level", block: "ties", from: 0, to: -360, cyclic: true } };
    const ph = levelPhases(def);
    const lay = L.layers || { x_scale: 1.8, y: { 0: 26, 1: 15, 2: 8 }, z: 30 };
    const measure = Math.max(1e-6, def.measure ?? 3);
    for (const hd of L.heads) {
      const h = this.heads[hd];
      if (!(h.level >= 0) || !h.pos) continue;
      const u = age / measure + (def.offset ?? 0) + ph[h.level] + 1e-6;
      if (def.clean && u < 0) continue;                       // a clean start: dark until this third's first onset
      const v = waveformLite(def, u);
      const s = (def.floor ?? 0) + (1 - (def.floor ?? 0)) * v;
      if (s <= 0.02) continue;
      const ty = (lay.y[h.level] ?? lay.y[String(h.level)] ?? 15) + (L.layerShift || 0);
      const t = [(lay.x_scale ?? 1.8) * h.pos[0], ty, lay.z ?? 30];
      const d = [t[0] - h.pos[0], t[1] - h.pos[1], t[2] - h.pos[2]], dl = Math.hypot(d[0], d[1], d[2]) || 1;
      const o = this.out.aim, b = hd * 4;
      o[b] = d[0] / dl; o[b + 1] = d[1] / dl; o[b + 2] = d[2] / dl; o[b + 3] = L.k ?? 8;
      for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1]]) this._emit(hd, h.sx + 0.3 * dx, h.y + 0.3 * dy, col, lv * s);
    }
  }
  // one spoke per halo laser, radially out and tipped toward the crowd, lit while the ring's chopper blade covers it
  _corona(L, age, lv, col) {
    const def = L.followDef || { form: "square", width: 0.39, transition: 0.6, measure: 0.5, phase: { from: 0, to: -720 } };
    const DEG = Math.PI / 180, fw = (L.forward_deg ?? 25) * DEG;
    const measure = Math.max(1e-6, def.measure ?? 0.5);
    const from = (def.phase && def.phase.from) ?? 0, to = (def.phase && def.phase.to) ?? -720;
    for (const hd of L.heads) {
      const h = this.heads[hd];
      if (h.clock === null || h.clock === undefined || !h.radial || !h.normal) continue;
      let a = 90 - h.clock;                                   // the polar angle, as the ring's cells rank it
      a = ((a + 180) % 360 + 360) % 360 - 180;
      const u = frac((a + 172.5) / 360);
      const v = waveformLite(def, age / measure + (def.offset ?? 0) + (from + u * (to - from)) / 360 + 1e-6);
      if (v <= 0.02) continue;
      const o = this.out.aim, b = hd * 4;
      const d = [Math.cos(fw) * h.radial[0] + Math.sin(fw) * h.normal[0], Math.cos(fw) * h.radial[1] + Math.sin(fw) * h.normal[1],
                 Math.cos(fw) * h.radial[2] + Math.sin(fw) * h.normal[2]];
      const dl = Math.hypot(d[0], d[1], d[2]) || 1;
      o[b] = d[0] / dl; o[b + 1] = d[1] / dl; o[b + 2] = d[2] / dl; o[b + 3] = L.k ?? 12;
      const px = h.sx - HERO.x, py = h.y - PICTURE_RING_Y, pl = Math.hypot(px, py) || 1;
      this._emit(hd, h.sx + 0.3 * px / pl, h.y + 0.3 * py / pl, col, lv * v);
    }
  }
  _pattern(hit, pos, lv) {
    const r = rngOf(hit.seed);
    const nB = 3 + Math.floor(r() * 4);              // beams per head in a fan
    const spread = (18 + 30 * r()) * Math.PI / 180;
    const age = pos - hit.onset;
    for (const [j, hd] of hit.heads.entries()) {
      const h = this.heads[hd];
      const toHero = Math.atan2(HERO.y - h.y, HERO.x - h.sx);
      const col = j % 2 ? hit.colour2 : hit.colour;
      switch (hit.pattern) {
        case "fan": for (let b = 0; b < nB; b++) this._ray(hd, toHero + spread * (b / (nB - 1) - 0.5), 2.2, hit.colour, lv); break;
        case "cross": this._emit(hd, HERO.x + (HERO.x - h.sx) * 1.6, HERO.y + (HERO.y - h.y) * 1.6, col, lv); break;
        case "scissors": {
          const step = Math.floor(age * 2) % 2 ? 1 : -1;
          this._ray(hd, toHero + step * Math.sign(h.sx || 1) * 0.35, 2.2, col, lv);
          break;
        }
        case "crown": for (let b = 0; b < 12; b++) this._ray(hd, Math.PI * (0.12 + 0.76 * b / 11), 2.4, b % 2 ? hit.colour2 : hit.colour, lv); break;
        case "cone": {
          const spin = pos * 0.25 * TAU;
          for (let b = 0; b < 6; b++) {
            const a = spin + (TAU * b) / 6;
            this._emit(hd, HERO.x + 0.16 * Math.cos(a), HERO.y + 0.1 * Math.sin(a), col, lv);
          }
          break;
        }
        case "rain": this._ray(hd, h.y > 0 ? -Math.PI / 2 : Math.PI / 2, 2.2, col, lv); break;
        case "sweep": {
          const sw = Math.sin(pos * 0.5 * TAU) * 0.6;
          for (let b = 0; b < nB; b++) this._ray(hd, toHero + sw + spread * 0.5 * (b / (nB - 1) - 0.5), 2.2, hit.colour, lv);
          break;
        }
        case "chase": if (j === Math.floor(age * 4) % hit.heads.length) this._ray(hd, toHero, 2.2, col, lv); break;
        default: break;
      }
    }
  }
  _look(pos, lv) {
    const name = this.look.name;
    if (name === "lattice") {
      // the Laser Lattice (signature routine 6): Bank B fires crossing pairs upward, Bank A crossing pairs downward;
      // the lattice breathes +-9 degrees over 16 beats
      const breathe = Math.sin((pos / 16) * TAU) * 0.16;
      for (const hd of BANK_B) for (const s of [-1, 1]) this._ray(hd, Math.PI / 2 + s * (0.42 + breathe), 2.4, s > 0 ? 0 : 1, lv * 0.8);
      for (const hd of BANK_A) for (const s of [-1, 1]) this._ray(hd, -Math.PI / 2 + s * (0.5 - breathe), 2.4, 0, lv * 0.6);
    } else if (name === "ceiling") {
      // a laser ceiling over the crowd: Bank B fans of nearly level beams (the 3D reach throws them out over the floor)
      const sway = Math.sin((pos / 8) * TAU) * 0.08;
      for (const hd of BANK_B) for (let b = 0; b < 5; b++) this._ray(hd, Math.PI / 2 + (b / 4 - 0.5) * 1.1 + sway, 0.5, 0, lv * 0.7);
    } else if (name === "tunnel") {
      const spin = (pos / 8) * TAU;
      for (let b = 0; b < 16; b++) {
        const a = spin + (TAU * b) / 16;
        this._emit(HERO_HEAD, HERO.x + 0.3 * Math.cos(a), HERO.y + 0.3 * Math.sin(a), b % 2, lv);
      }
    } else if (name === "fans") {
      const open = 0.5 + 0.5 * Math.sin((pos / 8) * TAU);
      for (const hd of SIDE) {
        const h = this.heads[hd], toHero = Math.atan2(HERO.y - h.y, HERO.x - h.sx);
        for (let b = 0; b < 7; b++) this._ray(hd, toHero + (b / 6 - 0.5) * (0.3 + 0.9 * open), 2.4, 0, lv * 0.8);
      }
    }
  }
}

// The ring centre in the picture (the rings hang at y 14 m).
export const PICTURE_RING_Y = (14 - PICTURE.y0_m) * PICTURE.y_per_m;
// The three levels' phase offsets (turns) under a schedule's spread: the same spread the fixtures' effect uses, on the
// three level values (level 0, 1, 2; level_mirror 0, 1, 0).
export function levelPhases(def) {
  const ph = def.phase || {};
  const keys = { level: Float64Array.from([0, 1, 2]), level_mirror: Float64Array.from([0, 1, 0]), index: Float64Array.from([0, 1, 2]) };
  const order = keys[ph.order] ? ph.order : "level";
  const out = spreadValues(keys, { ...ph, order }, 3);
  return Array.from(out, (v) => v / 360);
}
// The waveform without the effects module's seeded forms (the schedules are squares, pulses and sines).
function waveformLite(def, x) { return waveform(def.form || "square", x, def); }
