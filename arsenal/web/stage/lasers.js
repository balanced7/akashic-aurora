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

export const LASERS_API = "arsenal.stage-lasers/v0";
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
  constructor({ seed = 2014, clock = null, colours = null, fallbackBpm = 150 } = {}) {
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
    this.out = { t: 0, pos: 0, seg: new Float32Array(MAX_SEGMENTS * SEG_FLOATS), n: 0, heads: new Float32Array(HEADS.length),
                 events: [], pattern: "", gate: "", look: "off", reach: 1, hits: 0 };
  }
  setClock(c) { this.clock = c; }
  setColours(colours) { this.palette = laserPalette(colours); }
  setLook(name, level = 1, reach = 1) {
    this.look = { name: LOOKS.includes(name) ? name : "off", level: clamp01(level), reach: reach > 0 ? reach : 1 };
  }
  setSection(name) { this.section = String(name || "any"); }
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
    o.t = t; o.n = 0; o.heads.fill(0); o.events.length = 0;
    const pos = this.posAt(t);
    o.pos = pos;
    for (const h of this.hits) {
      const lv = this.level(h, pos) * (0.55 + 0.45 * h.vel);
      if (lv <= 0) continue;
      this._pattern(h, pos, lv);
      o.pattern = h.pattern; o.gate = h.gate;
    }
    this.hits = this.hits.filter((h) => !(h.released !== null && pos > h.released + 1) && pos - h.onset < 64 && (h.held || h.gate === "hold" || pos - h.onset < 4));
    if (this.look.name !== "off" && this.look.level > 0) this._look(pos, this.look.level);
    o.look = this.look.name; o.reach = this.look.reach; o.hits = this.hits.length;
    return o;
  }
  _emit(head, x1, y1, col, intensity, width = 1.6) {
    const o = this.out;
    if (o.n >= MAX_SEGMENTS || intensity <= 0) return;
    const h = HEADS[head];
    const s = o.n * SEG_FLOATS, c = this.palette[col % this.palette.length];
    o.seg[s + SEG.X0] = h.sx; o.seg[s + SEG.Y0] = h.y; o.seg[s + SEG.X1] = x1; o.seg[s + SEG.Y1] = y1;
    o.seg[s + SEG.R] = c[0]; o.seg[s + SEG.G] = c[1]; o.seg[s + SEG.B] = c[2]; o.seg[s + SEG.I] = intensity;
    o.seg[s + SEG.WIDTH] = width; o.seg[s + SEG.GLOW] = intensity; o.seg[s + SEG.BLUR] = 0; o.seg[s + SEG.HEAT] = 0;
    o.seg[s + SEG.KIND] = KIND.BEAM; o.seg[s + SEG.HEAD] = head; o.seg[s + SEG.FALLOFF] = 0.5; o.seg[s + SEG.FLAGS] = 0;
    o.n++;
    o.heads[head] = Math.max(o.heads[head], intensity);
  }
  // a beam from head h at angle a (radians, 0 = +x, pi/2 = up) of length L
  _ray(head, a, L, col, lv) { const h = HEADS[head]; this._emit(head, h.sx + L * Math.cos(a), h.y + L * Math.sin(a), col, lv); }
  _pattern(hit, pos, lv) {
    const r = rngOf(hit.seed);
    const nB = 3 + Math.floor(r() * 4);              // beams per head in a fan
    const spread = (18 + 30 * r()) * Math.PI / 180;
    const age = pos - hit.onset;
    for (const [j, hd] of hit.heads.entries()) {
      const h = HEADS[hd];
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
        const h = HEADS[hd], toHero = Math.atan2(HERO.y - h.y, HERO.x - h.sx);
        for (let b = 0; b < 7; b++) this._ray(hd, toHero + (b / 6 - 0.5) * (0.3 + 0.9 * open), 2.4, 0, lv * 0.8);
      }
    }
  }
}
