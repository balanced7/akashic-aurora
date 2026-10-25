// Virtual Stage v0, the effects engine: arsenal/web/stage/effects.js (pure ES module). Tests: tests/stage_effects.test.mjs.
//
// Every console's effects engine is the same machine under different names (the lighting lane, 2026-10-24): a WAVEFORM
// read at a PHASE that runs in beats, offset per fixture by a SPREAD across a group. One Spread object here covers MA's
// MAtricks, ChamSys's spread and Hog's fan (the vocabulary table is fromMA / fromChamSys / fromHog below):
//
//   order    how the group is ranked: index, x, y, z (world, at home), helix (the strand parameter), along (a strip),
//            angle (round a ring), azimuth / radius (about the group's centre), element, side, random
//   block    n neighbours share a value            MA Block   = ChamSys Segments = Hog Buddying
//   repeat   the pattern restarts every n          MA Group   = ChamSys Parts    = Hog Segments
//   wings    the group folds into n wings; mirror reverses every other wing     MA Wings = ChamSys Wings = Hog Wings
//   wingOffset  each wing w adds w x this to u (two backbones 180 degrees apart: wings 2, wingOffset 0.5)
//   shuffle  a seeded permutation of the slots; shift moves the pattern n slots; reverse flips it
//   from/to  the value range (degrees of phase, or attribute units for a fan); cyclic: u = i / N (0 and 360 coincide),
//            otherwise u = i / (N - 1) (a fan's ends land exactly on from and to)
//
// The phase runs in BEATS, never in seconds. Each effect keeps an accumulator: phi += dPos * scale / measure each frame,
// where dPos is the beat position's advance (grid.js). Fixture i reads x = frac(phi + phase_i). The rules that keep it
// locked to the music through every tempo change, speed change and tap:
//   - never t * bpm: a tempo change changes dPos per second, not phi's continuity;
//   - a speed change (the Speed fader's detents, an effect's own scale) lands on the next BEAT line, a change of x4 or
//     more on the next BAR line; phi stays continuous across it and only its rate changes, so the cycle stays on the grid;
//   - a tap (grid ver re-anchor) snaps every accumulator back onto the grid: phi = frac(pos * scale / measure + offset).
//
// v1 (2026-10-25): the order keys clock (round a ring from the top, clockwise from front of house), level (the ring's
// altitude thirds: top 0, middle 1, bottom 2), level_mirror (top and bottom share 0, middle 1), column (1, 2, 3 outward by
// |x|) and depth (by z); block "ties" (members with an equal key share one slot: a whole third, column or depth row lights
// as one); cue-anchored phase (anchorPos: the cycle starts on the cue's ONE, not wherever the grid's phase happens to be,
// and the speed fader does not reach a cue's timing); one-shots (shots: the number of cycles to run, then the last value
// holds; delay: beats before the first cycle); the sparkle form (a seeded random subset of members each cycle); and a
// clean start (clean: true on an anchored effect: a member stays at the form's zero until its first onset after the
// anchor, so a chase that starts on a cue's ONE never shows the tail of a cycle that did not happen).
//
// Safety rule (design section 3.10, a unison beat pulse is a lift, not a flash): an effect that drives Dimmer with a
// phase spread under 90 degrees (unison, or nearly) gets floor >= 0.6, so it swings 60 -> 100 %, never 0 -> 100 %.
// Full-depth pulses are allowed only as chases spread over at least 90 degrees. governEffect() applies it; the engine
// calls it on every effect it starts.

export const EFFECTS_API = "arsenal.stage-effects/v1";
export const UNISON_FLOOR = 0.6;
export const UNISON_SPREAD_DEG = 90;
// The frame clock lands a beat line within float error (pos 61.999999999998 for beat 62): a phase this close to the line
// counts as on it, so the light is lit in the beat's own frame and never one frame late.
export const LINE_EPS = 1e-6;

const TAU = Math.PI * 2;
const frac = (x) => x - Math.floor(x);
const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);

// A small seeded generator (mulberry32 over a string hash): shuffles and random forms are the same on every run.
export function hashSeed(...xs) {
  let h = 2166136261 >>> 0;
  for (const x of xs) {
    const s = String(x);
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
    h ^= 0x9e37; h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ---------------------------------------------------------------------------------------------------- spreads --
export const ORDERS = Object.freeze(["index", "x", "y", "z", "helix", "along", "angle", "azimuth", "radius", "element",
                                     "side", "random", "gridX", "gridY", "gridZ", "clock", "level", "level_mirror", "column",
                                     "depth", "spiral"]);

// The rank of each member under `order` (0 .. n-1), stable (ties keep index order). keys: the group's key arrays.
// The key values a spread orders by (spiral: round the ring from the top, one turn spread over the radius).
export function orderKey(keys, order, n, seed = 1) {
  let k;
  if (order === "random") { const r = rng(hashSeed(seed, "rank")); k = Array.from({ length: n }, () => r()); }
  else if (order === "gridX") k = keys.x; else if (order === "gridY") k = keys.y; else if (order === "gridZ") k = keys.z;
  else if (order === "spiral" && keys.clock && keys.radius) {
    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < n; i++) { lo = Math.min(lo, keys.radius[i]); hi = Math.max(hi, keys.radius[i]); }
    const span = hi - lo || 1;
    k = Array.from({ length: n }, (_, i) => frac(keys.clock[i] / 360 + (keys.radius[i] - lo) / span));
  }
  else k = keys[order];
  if (!k) throw new Error(`unknown spread order ${order}`);
  return k;
}
export function rankBy(keys, order, n, seed = 1) {
  const k = orderKey(keys, order, n, seed);
  const idx = Array.from({ length: n }, (_, i) => i);
  idx.sort((a, b) => (k[a] - k[b]) || (a - b));
  const rank = new Int32Array(n);
  for (let r = 0; r < n; r++) rank[idx[r]] = r;
  return rank;
}

// The per-member values of a Spread: from + u (to - from), following the steps of the design's section 3.4.
export function spreadValues(keys, spread, n, seed = 1, out = new Float64Array(n)) {
  const s = { order: "index", block: 1, repeat: 0, wings: 1, mirror: false, wingOffset: 0, shuffle: 0, shift: 0, reverse: false,
              from: 0, to: 0, cyclic: false, ...(spread || {}) };
  if (n === 0) return out;
  let rank, N = n, block;
  if (s.block === "ties") {
    // members with an equal key share one slot: the rank of each member's key among the distinct keys (dense rank)
    const k = orderKey(keys, s.order, n, seed);
    const distinct = [...new Set(Array.from(k, (v) => +v.toFixed(9)))].sort((a, b) => a - b);
    const at = new Map(distinct.map((v, i) => [v, i]));
    rank = Int32Array.from(k, (v) => at.get(+v.toFixed(9)));
    N = distinct.length;
    block = 1;
  } else {
    rank = rankBy(keys, s.order, n, seed);
    block = Math.max(1, Math.floor(s.block));
  }
  const wings = Math.max(1, Math.min(N, Math.floor(s.wings)));
  const wingLen = Math.ceil(N / wings);
  for (let i = 0; i < n; i++) {
    let r = rank[i];
    const w = Math.floor(r / wingLen);
    let inW = r - w * wingLen;
    const lenW = Math.min(wingLen, N - w * wingLen);
    if (s.mirror && (w % 2 === 1)) inW = lenW - 1 - inW;
    let slot = Math.floor(inW / block);
    let slots = Math.ceil(wingLen / block);
    if (s.repeat >= 1) { slot %= Math.floor(s.repeat); slots = Math.min(slots, Math.floor(s.repeat)); }
    out[i] = slot + w * 1e6;            // keep the wing for the offset below
    rank[i] = slots;                     // reuse: the slot count of this member's pattern
  }
  // shuffle, shift, reverse act on the slots of one pattern; the same permutation for every wing and repeat
  const slots = rank[0] || 1;
  let perm = null;
  if (s.shuffle) {
    const r = rng(hashSeed(seed, "shuffle", s.shuffle));
    perm = Array.from({ length: slots }, (_, i) => i);
    for (let i = slots - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [perm[i], perm[j]] = [perm[j], perm[i]]; }
  }
  for (let i = 0; i < n; i++) {
    const w = Math.floor(out[i] / 1e6);
    let slot = out[i] - w * 1e6;
    if (perm) slot = perm[slot];
    if (s.shift) slot = ((slot + Math.round(s.shift)) % slots + slots) % slots;
    if (s.reverse) slot = slots - 1 - slot;
    let u = s.cyclic ? slot / slots : (slots > 1 ? slot / (slots - 1) : 0);
    if (s.wingOffset) u += w * s.wingOffset;
    out[i] = s.from + u * (s.to - s.from);
  }
  return out;
}

// The vocabulary table: three consoles' words for the same Spread.
export const fromMA = ({ block = 1, group = 0, wings = 1, ...rest }) => ({ ...rest, block, repeat: group, wings });
export const fromChamSys = ({ segments = 1, parts = 0, wings = 1, ...rest }) => ({ ...rest, block: segments, repeat: parts, wings });
export const fromHog = ({ buddying = 1, segments = 0, wings = 1, ...rest }) => ({ ...rest, block: buddying, repeat: segments, wings });

// -------------------------------------------------------------------------------------------------- waveforms --
// Every form returns 0..1 at x in [0, 1); x = 0 is the beat line the cycle starts on, and the forms that pulse peak there.
export const FORMS = Object.freeze(["sine", "cos", "triangle", "rampUp", "rampDown", "square", "pulse", "step", "random", "const",
                                    "sparkle"]);
export function waveform(form, x, p = {}) {
  const xf = frac(x);
  switch (form) {
    case "sine": return 0.5 + 0.5 * Math.cos(TAU * xf);            // 1 on the line, 0 half a cycle later
    case "cos": return 0.5 - 0.5 * Math.cos(TAU * xf);             // 0 on the line
    case "triangle": return 1 - 2 * Math.min(xf, 1 - xf);
    case "rampUp": return xf;
    case "rampDown": return 1 - xf;
    case "square": {
      const w = p.width ?? 0.5, tr = clamp01(p.transition ?? 0) * Math.min(w, 1 - w) * 0.5;
      if (tr <= 0) return xf < w ? 1 : 0;
      if (xf < tr) return xf / tr;
      if (xf < w - tr) return 1;
      if (xf < w + tr) return 1 - (xf - (w - tr)) / (2 * tr);
      if (xf > 1 - tr) return 0;
      return 0;
    }
    case "pulse": {                                                  // instant attack on the line, a quadratic fall
      const w = p.width ?? 0.5;
      if (xf >= w) return 0;
      const u = 1 - xf / w;
      return u * u;
    }
    case "step": {
      const n = Math.max(2, Math.floor(p.steps ?? 4));
      return Math.floor(xf * n) / (n - 1);
    }
    case "random": {                                                 // one seeded value per cycle (cycle = floor of x)
      const r = rng(hashSeed(p.seed ?? 1, Math.floor(x)));
      return r();
    }
    case "const": return 1;
    case "sparkle": {                                                // a seeded subset of members each cycle, soft edges
      const r = rng(hashSeed(p.seed ?? 1, p.member ?? 0, Math.floor(x)));
      if (r() >= (p.density ?? 0.15)) return 0;
      const w = p.width ?? 0.5, tr = clamp01(p.transition ?? 0.5) * Math.min(w, 1 - w) * 0.5;
      if (xf >= w) return 0;
      if (tr > 0 && xf < tr) return xf / tr;
      if (tr > 0 && xf > w - tr) return (w - xf) / tr;
      return 1;
    }
    default: throw new Error(`unknown waveform ${form}`);
  }
}

// ------------------------------------------------------------------------------------------- the safety rule --
export function phaseSpreadDeg(def) {
  const ph = def.phase || {};
  return Math.abs((ph.to ?? 0) - (ph.from ?? 0));
}
// A copy of def with the unison floor applied where the rule asks for it; governed: true when it changed anything.
export function governEffect(def) {
  const d = { ...def };
  const drivesDimmer = (d.attrs || []).includes("Dimmer");
  if (drivesDimmer && phaseSpreadDeg(d) < UNISON_SPREAD_DEG && d.form !== "const") {
    if (d.mode === "absolute") {
      // absolute: the level swings floor x size .. size, so the floor itself is the ratio
      if ((d.floor ?? 0) < UNISON_FLOOR) { d.floor = UNISON_FLOOR; d.governed = true; }
    } else {
      // relative: base x (1 - size (1 - level)); the trough is base x (1 - size (1 - floor)) >= 0.6 x base
      const depth = (d.size ?? 1) * (1 - (d.floor ?? 0));
      if (depth > 1 - UNISON_FLOOR + 1e-9) {
        d.floor = 1 - (1 - UNISON_FLOOR) / Math.max(d.size ?? 1, 1e-9);
        d.governed = true;
      }
    }
  }
  return d;
}

// --------------------------------------------------------------------------------------------- the accumulator --
// One effect's phase. tick(pos, ver) advances it by the beat position; setScale(s, pos) asks for a new rate, applied on
// the next beat line (or bar line for a change of x4 or more). barAnchor: the beat position of a bar's ONE.
export class Phasor {
  constructor({ measure = 4, scale = 1, offset = 0 } = {}) {
    this.measure = Math.max(1e-6, measure);
    this.scale = scale;
    this.offset = offset;      // the phase the cycle is at on pos 0 (re-anchor target)
    this.phi = 0;
    this.lastPos = null;
    this.ver = null;
    this.pending = null;       // {scale, at} the next scale and the beat position it lands at
    this.changes = [];         // [{pos, from, to}] for receipts (bounded)
  }
  rate() { return this.scale / this.measure; }
  setScale(scale, pos, barAnchor = 0) {
    if (scale === this.scale && !this.pending) return;
    const ratio = scale > this.scale ? scale / this.scale : this.scale / scale;
    // asked for within 0.05 beat after a line (a frame at 150 BPM is 0.042), it lands on that line: now
    const grace = 0.05;
    let at;
    if (ratio >= 4 - 1e-9) {
      const q = (pos - barAnchor) / 4, k = Math.floor(q + 1e-9);
      at = (pos - (barAnchor + 4 * k)) < grace ? barAnchor + 4 * k : barAnchor + 4 * (k + 1);
    } else {
      const k = Math.floor(pos + 1e-9);
      at = pos - k < grace ? k : k + 1;
    }
    this.pending = { scale, at };
  }
  // Re-anchor onto the grid at `pos` (a tap): phi = frac(pos * scale / measure + offset).
  anchor(pos) { this.phi = frac(pos * this.rate() + this.offset); this.lastPos = pos; }
  tick(pos, ver = null) {
    if (this.lastPos === null) { this.anchor(pos); this.ver = ver; return this.phi; }
    if (ver !== null && this.ver !== null && ver !== this.ver) { this.ver = ver; this.anchor(pos); return this.phi; }
    this.ver = ver;
    let p0 = this.lastPos;
    const p1 = Math.max(pos, p0);      // the grid never runs backward; guard anyway
    if (this.pending && p1 >= this.pending.at) {
      const at = Math.max(p0, this.pending.at);
      this.phi += (at - p0) * this.rate();
      if (this.changes.length < 64) this.changes.push({ pos: at, from: this.scale, to: this.pending.scale });
      this.scale = this.pending.scale;
      this.pending = null;
      p0 = at;
    }
    this.phi += (p1 - p0) * this.rate();
    this.phi -= Math.floor(this.phi);
    this.lastPos = p1;
    return this.phi;
  }
}

// --------------------------------------------------------------------------------------------- the effect runner --
// An effect running on a group: its def (governed), its phasor, the per-member phase offsets (turns) and fan values,
// and a level (fades in and out over fadeIn / fadeOut beats).
// Cue options (v1): anchorPos (phase 0 lands on that beat position: a cue's ONE; the effect then ignores the speed fader,
// because a cue's steps are counted in beats); def.shots (one-shot: run that many cycles from the anchor plus def.delay
// beats, then hold the last value; before the first cycle hold the first).
export class EffectInstance {
  constructor(id, def, group, { seed = 1, speed = 1, pos = 0, anchorPos = null } = {}) {
    this.id = id;
    this.def = governEffect(def);
    this.group = group;
    const n = group.n;
    this.phase = new Float64Array(n);
    if (this.def.phase) spreadValues(group.keys, this.def.phase, n, hashSeed(seed, id, "phase"), this.phase);
    for (let i = 0; i < n; i++) this.phase[i] /= 360;
    this.fan = this.def.fan ? spreadValues(group.keys, { cyclic: false, ...this.def.fan }, n, hashSeed(seed, id, "fan")) : null;
    this.anchorPos = anchorPos;
    const measure = this.def.measure ?? 4, scale = this.def.scale ?? 1;
    const offset = anchorPos === null ? (this.def.offset ?? 0) : frac((this.def.offset ?? 0) - (anchorPos * scale) / measure);
    this.phasor = new Phasor({ measure, scale: anchorPos === null ? scale * speed : scale, offset });
    this.formParams = { ...this.def, seed: this.def.seed ?? hashSeed(seed, id, "form"), member: 0 };
    this.level = this.def.fadeIn ? 0 : 1;
    this.target = 1;
    this.startPos = pos;
    this.lastPos = pos;
    this.dead = false;
  }
  stop() { this.target = 0; if (!this.def.fadeOut) { this.level = 0; this.dead = true; } }
  start() { this.target = 1; this.dead = false; }
  tick(pos, ver) {
    const dPos = Math.max(0, pos - this.lastPos);
    this.lastPos = pos;
    if (this.target > this.level) this.level = Math.min(1, this.level + (this.def.fadeIn ? dPos / this.def.fadeIn : 1));
    else if (this.target < this.level) this.level = Math.max(0, this.level - (this.def.fadeOut ? dPos / this.def.fadeOut : 1));
    if (this.level <= 0 && this.target <= 0) this.dead = true;
    return this.phasor.tick(pos, ver);
  }
  // The waveform value 0..1 of member i now.
  value(i) {
    const d = this.def, fp = this.formParams;
    // by_phase: members that share a phase share the seeded draw (a sparkle or a held segment mask by block, not by cell)
    fp.member = d.by_phase ? Math.round(this.phase[i] * 1e6) : i;
    if (d.clean && this.anchorPos !== null) {
      const u = (this.lastPos - this.anchorPos) * (d.scale ?? 1) / Math.max(1e-6, d.measure ?? 4) + (d.offset ?? 0) + this.phase[i] + LINE_EPS;
      if (u < 0) return 0;
    }
    if (d.shots !== undefined && this.anchorPos !== null) {
      // a one-shot: the unwrapped cycle count since the anchor (plus the delay), clamped to [0, shots)
      const u = (this.lastPos - this.anchorPos - (d.delay ?? 0)) * (d.scale ?? 1) / Math.max(1e-6, d.measure ?? 4) + this.phase[i] + LINE_EPS;
      const end = Math.max(1e-9, d.shots) - 1e-9;
      return waveform(d.form || "sine", u <= 0 ? 0 : u >= end ? end : u, fp);
    }
    return waveform(d.form || "sine", this.phasor.phi + this.phase[i] + LINE_EPS, fp);
  }
  // Apply to an attribute value of member i (relative unless the def says absolute). attr: the attribute name.
  apply(attr, base, i) {
    const d = this.def, size = d.size ?? 1, lv = this.level;
    if (lv <= 0) return base;
    const w = this.value(i);
    let v;
    if (attr === "Dimmer") {
      const floor = d.floor ?? 0;
      const level = floor + (1 - floor) * w;
      v = d.mode === "absolute" ? level * size : base * (1 - size * (1 - level));
    } else if (attr === "ColorMix") {
      v = d.mode === "relative" ? clamp01(base + size * w) : clamp01(w * size);
    } else if (this.fan) {
      v = base + this.fan[i] * w * size;            // a fan: closed (base) to open (base + fan_i) as w goes 0 -> 1
    } else {
      v = base + size * (2 * w - 1);                // around the base, +-size
    }
    return base + (v - base) * lv;
  }
}
