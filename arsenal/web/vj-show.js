// VJ show logic: arsenal/web/vj-show.js (pure ES module: no DOM, no WebGL). Tests: tests/vj_show.test.mjs.
//
// Daniel, 2026-10-23: "see if you cxan't make multiple VJ scenes and think of some cool features ... make a badass vj /
// visualization engine". This module decides, without a browser:
//   - the set transitions (crossfade, radial wipe, glitch cut, zoom-through), how long each lasts in beats, and WHEN one
//     starts: on the next predicted beat, or on the next downbeat when the beat source numbers its bars      planTransition
//   - the showcase tour (?showcase=1): which set plays next, for how long, with which transition, when its name card
//     shows, and which tasteful accents it plays on the downbeats (never a flash, a strobe or an invert)     ShowcaseTour
//   - the post look's stored settings and its fader binding (learned on touch, like the page's other controls)  LOOK
//   - a one-line description of every set, for the name card                                                  BLURBS
// The page (vj.js) owns the clock and the deck; these functions only read a BeatClock (vj-core.js) and return plans.

export const SHOW_API = "arsenal.vj-show/v1";

// --------------------------------------------------------------------------------------------- the transitions --
// code: the transition shader's style number (vj-fx.js); beats: its length on the beat; ms: its length without a beat.
export const TRANSITIONS = Object.freeze({
  crossfade: { label: "Crossfade", code: 0, beats: 2, ms: 1200, help: "the two sets blend through each other" },
  radial:    { label: "Radial wipe", code: 1, beats: 2, ms: 1200, help: "an iris opens from the centre with a lit rim" },
  glitch:    { label: "Glitch cut", code: 2, beats: 1, ms: 700, help: "blocks flip to the new set one by one, torn and split" },
  zoom:      { label: "Zoom-through", code: 3, beats: 2, ms: 1300, help: "fly into the old set and out of the new one" },
});
export const TRANSITION_IDS = Object.freeze(Object.keys(TRANSITIONS));
// what the mapping panel offers: a fixed style, or a cycle through all four
export const STYLE_CHOICES = Object.freeze([...TRANSITION_IDS, "cycle"]);
// when a switch lands: on the next bar when the beat source numbers its beats (else the next beat), the next beat, or now
export const QUANTIZE_CHOICES = Object.freeze(["bar", "beat", "now"]);
const QUANTIZE_LABELS = { bar: "next bar (beat if bars unknown)", beat: "next beat", now: "immediately" };
export function quantizeLabel(q) { return QUANTIZE_LABELS[q] || q; }
export function styleLabel(s) { return s === "cycle" ? "Cycle all four" : TRANSITIONS[s] ? TRANSITIONS[s].label : s; }

// The style to use for transition number `serial` under a panel choice (cycle rotates crossfade, radial, zoom, glitch).
const CYCLE_ORDER = ["crossfade", "radial", "zoom", "glitch"];
export function pickStyle(choice, serial = 0) {
  if (TRANSITIONS[choice]) return choice;
  return CYCLE_ORDER[((serial % CYCLE_ORDER.length) + CYCLE_ORDER.length) % CYCLE_ORDER.length];
}

// The time (ms) of the next beat whose number is a multiple of beatsPerBar, after nowMs; null when the clock does not
// know its beat numbers or has no tempo. The engine's 'beat' events carry a running number n; the demo's n counts from
// its first beat with bar lines every 4, so n % 4 === 0 is a downbeat there.
export function nextDownbeatAt(nowMs, clock, beatsPerBar = 4) {
  const p = clock.period();
  if (!(p > 0) || !clock.alive(nowMs) || !(clock.n >= 0)) return null;
  // anchor on the earliest numbered prediction still ahead, else on the last fired beat
  let tA = clock.lastBeat, nA = clock.n;
  let bestT = Infinity;
  for (let i = 0; i < clock.qlen; i++) {
    if (clock.qn[i] >= 0 && clock.q[i] >= nowMs && clock.q[i] < bestT) { bestT = clock.q[i]; tA = clock.q[i]; nA = clock.qn[i]; }
  }
  // step forward from the anchor to the first beat at or after now
  let k = tA >= nowMs ? 0 : Math.ceil((nowMs - tA) / p);
  let t = tA + k * p, n = nA + k;
  const toBar = ((beatsPerBar - (n % beatsPerBar)) % beatsPerBar);
  t += toBar * p;
  n += toBar;
  return t;
}

// When and how long a switch plays.
//   nowMs: the press; clock: the page's BeatClock; opts.style: a TRANSITIONS id; opts.quantize: bar | beat | now;
//   opts.bars: whether the beat source numbers its bars (the demo does; the engine does not say).
// Returns { startMs, ms, style, code, on } where on is "bar", "beat" or "now" (what the start was snapped to).
export function planTransition(nowMs, clock, { style = "crossfade", quantize = "bar", bars = false, minMs = 300, maxMs = 4000,
                                               maxWaitBeats = 4 } = {}) {
  const def = TRANSITIONS[style] || TRANSITIONS.crossfade;
  const id = TRANSITIONS[style] ? style : "crossfade";
  const p = clock.period();
  const alive = p > 0 && clock.alive(nowMs);
  if (!alive) return { startMs: nowMs, ms: def.ms, style: id, code: def.code, on: "now" };
  const ms = Math.min(maxMs, Math.max(minMs, def.beats * p));
  if (quantize === "now") return { startMs: nowMs, ms, style: id, code: def.code, on: "now" };
  let at = null, on = "beat";
  if (quantize === "bar" && bars) {
    at = nextDownbeatAt(nowMs, clock);
    on = "bar";
  }
  if (at === null || at - nowMs > maxWaitBeats * p + 1) {
    at = clock.nextBeatAt(nowMs);
    on = "beat";
  }
  if (at === null || at < nowMs) return { startMs: nowMs, ms, style: id, code: def.code, on: "now" };
  return { startMs: at, ms, style: id, code: def.code, on };
}

// The transition's progress 0..1 at nowMs (0 before it starts).
export function transitionProgress(nowMs, startMs, ms) {
  const x = (nowMs - startMs) / Math.max(ms, 1);
  return x <= 0 ? 0 : x >= 1 ? 1 : x;
}

// ---------------------------------------------------------------------------------------------------- the look --
// The post pass's settings: on/off, the master amount, the transition style and quantize, and the control id bound to
// the look amount (a fader learned on touch; null when unbound). Stored under one localStorage key by the page.
export const LOOK_DEFAULTS = Object.freeze({ on: true, amount: 0.55, style: "cycle", quantize: "bar", ctl: null });
export function normalizeLook(stored) {
  const out = { ...LOOK_DEFAULTS };
  if (!stored || typeof stored !== "object" || Array.isArray(stored)) return out;
  if (typeof stored.on === "boolean") out.on = stored.on;
  if (typeof stored.amount === "number" && Number.isFinite(stored.amount)) out.amount = Math.min(1, Math.max(0, stored.amount));
  if (STYLE_CHOICES.includes(stored.style)) out.style = stored.style;
  if (QUANTIZE_CHOICES.includes(stored.quantize)) out.quantize = stored.quantize;
  if (typeof stored.ctl === "string" && /^[A-Za-z0-9_.:-]{1,32}$/.test(stored.ctl)) out.ctl = stored.ctl;
  return out;
}

// What the look's post pass does at a master amount (0..1) -- every stage scales from nothing at 0.
//   bloom: the glow's gain; vignette: how dark the corners go (fraction); grain: the grain's amplitude (display value);
//   aberration: the colour split per unit of hit (fraction of the frame's half-diagonal); bloomCap: the most mean linear
//   luminance the glow may add to a frame (the flash budget: the post pass can never make a flash on its own).
export function lookParams(amount) {
  const a = Math.min(1, Math.max(0, Number(amount) || 0));
  return { bloom: 0.55 * a, vignette: 0.32 * a, grain: 0.030 * a, aberration: 0.006 * a, bloomCap: 0.025 };
}

// ------------------------------------------------------------------------------------------------- the blurbs --
export const BLURBS = Object.freeze({
  "vj-laser-cathedral": "beams vault into an arch of haze; the pads fire the fans",
  "vj-reactor": "a plasma core in x-ray glass shells; every kick a shockwave",
  "vj-aurora-curtains": "curtains of aurora that the chords recolour",
  "vj-led-wall": "a wall of LEDs chasing the beat",
  "vj-chord-constellations": "every note a star on the circle of fifths; the pedal note pulls the strings",
  "feedback-tunnel": "Navi's MilkDrop tunnel, fed by the keys",
  "vj-hyperspace": "stars stream past; kicks warp them, pads punch hyperjumps",
  "vj-synthwave-grid": "an outrun sun on a neon grid; the chord paints the sky, pads fire lasers",
  "vj-liquid-chrome": "mercury blobs that swell with the bass and mirror a studio",
  "vj-lissajous-chords": "the chord's just ratios drawn as an oscilloscope figure: 4:5:6 major, 10:12:15 minor",
  "vj-note-rain": "every note falls as a bar in its pitch colour onto a wet floor",
  "vj-fractal-bloom": "a kaleidoscopic fractal that blooms one level per beat",
  "vj-geometry-hall": "a polyhedron of the chord's size that snaps round on every beat",
  "vj-particle-galaxy": "a spiral galaxy whose arms wind with the bass; notes light their stars",
});
export function blurbFor(id) { return BLURBS[id] || ""; }

// --------------------------------------------------------------------------------------------- the showcase tour --
// The tour plays each valid set for `dwellMs`, then asks the page for a transition (beat-quantized like any other), in a
// tasteful rotation. On each downbeat (every `accentEveryBars` bars) it plays one accent from a gentle list; it never
// plays a flash, a strobe or an invert (those stay for a person at the pads). It shows a name card when a set arrives.
// tick(nowMs, view) returns a list of actions; the page carries them out:
//   { do: "next", style }              start a transition to the next valid set
//   { do: "card", index }              show the name card for set `index` (the page knows its name)
//   { do: "accent", effect, vel, holdMs }   press the pad mapped to `effect` at velocity vel, release after holdMs
// view = { active: index of the live set, fading: bool, downbeat: bool (a bar started since the last tick),
//          beatCount: beats fired so far }
export const TOUR_STYLES = Object.freeze(["crossfade", "zoom", "radial", "crossfade", "glitch", "zoom", "radial"]);
export const TOUR_ACCENTS = Object.freeze([
  { effect: "shockwave", vel: 0.7, holdMs: 120 },
  { effect: "particles", vel: 0.65, holdMs: 1400 },
  { effect: "laser", vel: 0.6, holdMs: 120 },
  { effect: "kaleido", vel: 0.55, holdMs: 2600 },
  { effect: "shockwave", vel: 0.85, holdMs: 120 },
  { effect: "glitch", vel: 0.4, holdMs: 120 },
]);
export const NEVER_IN_TOUR = Object.freeze(["flash", "strobe", "invert", "freeze"]);

export class ShowcaseTour {
  constructor({ dwellMs = 20000, accentEveryBars = 2, cardFirst = true } = {}) {
    this.dwellMs = Math.max(2000, dwellMs);
    this.accentEveryBars = Math.max(1, accentEveryBars);
    this.since = null;          // when the live set arrived (ms)
    this.active = -1;
    this.requested = false;     // a transition was asked for and has not landed yet
    this.serial = 0;            // transitions asked for
    this.bars = 0;              // downbeats seen in this set
    this.accentSerial = 0;
    this.cardFirst = cardFirst;
    this.visits = 0;            // sets shown so far
  }
  tick(nowMs, view) {
    const out = [];
    if (this.since === null || view.active !== this.active) {
      // a set arrived (the first one, or a transition landed, or a person switched by hand): restart its clock
      const first = this.since === null;
      this.since = nowMs;
      this.active = view.active;
      this.requested = false;
      this.bars = 0;
      this.visits++;
      if (!first || this.cardFirst) out.push({ do: "card", index: view.active });
    }
    if (view.downbeat && !view.fading) {
      this.bars++;
      if (this.bars % this.accentEveryBars === 0) {
        const a = TOUR_ACCENTS[this.accentSerial % TOUR_ACCENTS.length];
        this.accentSerial++;
        out.push({ do: "accent", effect: a.effect, vel: a.vel, holdMs: a.holdMs });
      }
    }
    if (!this.requested && !view.fading && nowMs - this.since >= this.dwellMs) {
      this.requested = true;
      out.push({ do: "next", style: TOUR_STYLES[this.serial % TOUR_STYLES.length] });
      this.serial++;
    }
    return out;
  }
}

// ----------------------------------------------------------------------------------- the Lissajous chord ratios --
// The JS twin of vj-lissajous-chords.frag's chordVoices (tests/vj_show.test.mjs reads the shader's tables and holds the
// two to the same numbers). Each tone's just ratio above the root, by semitone; the minor seventh is 7/4 (the harmonic
// seventh) unless the chord has a minor third, then 9/5. Up to four voices: the root, then thirds, fifths, sevenths and
// colour tones in PRIORITY order. The ratios go to whole numbers over their least common denominator, reduced by their
// greatest common divisor: a major triad is 4:5:6, a minor triad 10:12:15.
export const JUST_NUM = Object.freeze([1, 16, 9, 6, 5, 4, 7, 3, 8, 5, 9, 15]);
export const JUST_DEN = Object.freeze([1, 15, 8, 5, 4, 3, 5, 2, 5, 3, 5, 8]);
export const VOICE_PRIORITY = Object.freeze([4, 3, 7, 10, 11, 6, 8, 9, 2, 5, 1]);
const gcd = (a, b) => { while (b) [a, b] = [b, a % b]; return Math.max(a, 1); };
export function chordFrequencies(pcs, root) {
  const set = new Set(pcs.map((p) => ((p % 12) + 12) % 12));
  if (!(root >= 0) || !set.has(root)) return [];
  const iv = [0];
  for (const s of VOICE_PRIORITY) if (iv.length < 4 && set.has((root + s) % 12)) iv.push(s);
  const minorThird = iv.includes(3);
  const num = [], den = [];
  for (const s of iv) {
    if (s === 10 && !minorThird) { num.push(7); den.push(4); } else { num.push(JUST_NUM[s]); den.push(JUST_DEN[s]); }
  }
  const L = den.reduce((l, d) => (l / gcd(l, d)) * d, 1);
  const f = num.map((n, j) => n * (L / den[j]));
  const g = f.reduce((a, b) => gcd(a, b));
  return f.map((x) => x / g);
}

// --------------------------------------------------------------------------------------------- name card timing --
// The name card's opacity at age (ms since shown): in over 600 ms, held, out over 900 ms; 0 after holdMs + 1500.
export function cardOpacity(ageMs, holdMs = 3200) {
  if (!(ageMs >= 0)) return 0;
  if (ageMs < 600) return ageMs / 600;
  if (ageMs < 600 + holdMs) return 1;
  const x = (ageMs - 600 - holdMs) / 900;
  return x >= 1 ? 0 : 1 - x;
}
