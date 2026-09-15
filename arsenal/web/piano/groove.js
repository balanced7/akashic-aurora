// The groove generator: Claude's backing, one bar at a time (jam-spec 10.2-10.6; design-music 5).
//
// Pure: no DOM, no clock, no state kept between calls. The page transport calls bar() once per bar at H(n) (9.3), and
// arsenal/groove_bridge.mjs runs this same module under node for Python (the riff rebuild, v2 FL), so the same def,
// settings, seed and bar give the same events on every route, byte for byte.
//
//   bar(def, settings, pass, barIndex, opts?) -> [{beat, midi, vel, len, role, voice, tie, ms, carry, slot, row, freq}]
//
//   def       a resolved def (arsenal.jam.def/v0, 4.2): beats_per_bar, cycle_beats, slots with at_beat, beats, key,
//             section, tones_pc, bass_pc, voicings {play, full, comp, bass}, roles, vel, arp_ms, hold.
//   settings  one run settings entry (4.3): groove, backing, level, humanize, seed, walk, try_backing, muted, and the
//             optional dropout (0..1, default 0: off). A v2 groove plays ballad, pad plays comp (as schemas.card_settings).
//   pass      the pass of barIndex, as tempomap passOf gives it; a pass that disagrees with barIndex and def_from_bar
//             throws, because it means the caller has the wrong def_from_bar.
//   barIndex  the run's bar number n. The bar inside the def is k = n - def_from_bar.
//   opts      {def_from_bar = 0, bpm = null, mode = null}: the segment's def_from_bar and bpm (segmentAt(n)), and the
//             run mode (loop | try | play; a settings.try_backing makes it try).
//
// Events (all numbers are plain JSON; beats are rounded to 1e-6, ms to 1e-3):
//   beat   from this bar's downbeat. A negative beat (never below -1) is a pickup this bar owns: the approach bass on
//          the last beat of the bar before, or the early step on its "and". Bar 0's pickups sound over the count-in.
//   len    in beats. ms is the humanising and roll offset, added after beats become milliseconds.
//   voice  bass | upper | tick. Ticks have midi null, len 0 and a freq (Hz); voice.tick plays them (20 ms sine).
//   tie    "next": the note still sounds at the next downbeat. Hand it with its release at that downbeat + 30 ms;
//          bar n+1 carries it.
//   carry  true: no strike. The note was struck in an earlier bar and goes on sounding here for len beats from beat
//          0 (vel is its strike's). The transport extends bar n-1's tie:"next" note with the same midi and voice; when
//          there is none (a change landed on this bar line), it strikes the note at beat 0 instead.
//   slot   the def slot the note belongs to (a pickup: the chord it leads into). row names the table row: bass,
//          upper, second, inner, breath, approach, early, eighth, restrike, play, count, ghost.
//
// Rules (10.2-10.6), and what this module decides where the tables are silent:
// - Pieces. A chord is cut at bar lines into pieces. Beat-0 rows strike at the chord's onset and, for ballad and
//   pulse, again on every downbeat the chord holds through. Rows at a later beat (2 or 3; waltz 1 and 2) are bar
//   beats and play only in a piece that starts on the downbeat. A piece shorter than the table plays the rows that
//   fit: a 2-beat chord gets its beat-0 rows, plus the approach in ballad, pulse and Try bass; hold needs more than 2
//   beats for an approach.
// - The approach bass (walk 1) sits on the chord's last beat and leads into the next chord when that chord starts
//   exactly where this one ends. Around the loop's wrap the next chord is slot 0 again (the ring). It replaces a
//   second bass on the same beat. Its pitch uses the key of the chord it leaves.
// - A bass line is one voice: a bass note ends 0.05 beat before the next bass onset inside its chord (so 1.9 becomes
//   0.95 before a beat-4 approach, as the tables say), and at the gate before the next chord's bass. An upper note
//   ends 0.03 beat before the same note strikes again. A note listed twice in a voicing sounds once.
// - Gate: no note outlives its chord (0.03 beat before its end) unless it ties or is the early step.
// - Ties (hold, and Try bass): a note held to chord end ties into the next chord when that chord's beat-0 rows voice
//   the same MIDI note in the same voice. Ties never cross the loop's wrap, so every pass strikes its first chord.
//   Hold's breath re-strike skips voices that tie into or out of the chord. That is why the lament's upper voices
//   (upper: "same") hold through the whole pass and only the bass walks. In ballad and pulse an upper-same slot
//   plays the groove's rows over the unchanged shape.
// - Meter 3: ballad is the waltz (bass L+4 for 2.9 beats; upper L-2, top L+2, for 0.95; inner voices L-10 for 0.8
//   on beats 1 and 2). Pulse has 6 eighths, its bass L+2 for 2.9, and no second bass. Meters 2, 5, 6 and 7 play hold
//   (effectiveSettings warns).
// - Play (mode play): voicings.play per slot, rolled arp_ms per voice, at slot.vel. hold legato = to the next chord
//   + 80 ms, detached = length - 40 ms, a number = beats (bpm from opts, else 66). Play is not humanised and has no
//   ties; a note struck again ends where it strikes again.
// - Try: `ghosts` gives a tick on every beat (velocity 40, 1.5 kHz); `bass` gives the bass at L+2 (L = level) held to
//   chord end, with approaches; `loop` plays the settings' groove and backing. Count-in bars (k < 0) give ticks at
//   velocity 60, 2 kHz on beat 1 and 1.5 kHz on the others, in every mode but play.
//
// House liveness (Heimdall, house-ideas/heimdall.md; the same rules as arsenal/band.py and the FL VFX band):
// - HUMANIZE INVARIANT: every random draw comes from mulberry32 seeded with FNV-1a-32 of
//   "${seed}:${pass}:${bar}:${lane}", where bar is the run bar that owns the note and lane is the voice (0 = bass,
//   1.. = upper voices from the bottom, or roll, breath, dropout). A bar's wobble is its own, never one sequence for
//   the session. Two passes of the same loop bar differ, and one seed rebuilds the whole run. Within a lane, notes
//   draw in onset order: a timing normal, a velocity normal, a length uniform.
// - Humanising (h = humanize; 0 is machine-exact, for receipts): timing N(0, 5h ms) upper and N(0, 2.5h ms) bass,
//   clamped to +-12h ms, and a downbeat bass is never earlier than -4 ms. Roll: hold U(4,9)*h ms and ballad
//   U(8,14)*h ms per voice, bottom-up. Velocity: L + table + round(N(0, 2.5h)) + breath + arc - 2 on the first two
//   passes (when h > 0). breath is the per-bar walk of steps -1/0/+1 (0.3/0.4/0.3) times h, clamped to +-4 and
//   walked from the def's first bar. arc is round(3h sin(pi (q + 0.5) / B)) for loop bar q of B. The top voice stays
//   at or under L + max(2, its table offset). Table lengths (not "to chord end") take x (1 + U(-0.03, 0.03) h),
//   never past their gate.
// - Dropout (settings.dropout, 0..1, default 0 = off): a one-bar hole where everything but the bass rests. Upper
//   notes owned by the bar are dropped, notes ringing into it end at its bar line, and a held note that would ring on
//   past it strikes again on the bar after. It is never bar k = 0 (a run's first bar, or the first bar after a card
//   swap), and never two in a row: bar k rests when roll(k) and not roll(k-1). A roll leans on phrase ends:
//   roll(k) = U < 1 - (1 - dropout) ^ PHRASE_WEIGHT[k % 4], so bar 4 of each 4-bar phrase rests most.
// - The early step (ballad, walk 1): before a section change (a key item) and before the pass top (the loop coming
//   round), the bass steps to the next bass note on the "and" of the last beat, tied over the bar line: the next
//   chord's downbeat bass is not struck again. It replaces the approach, and it never leads into the def's first
//   downbeat (k = 0), where the count-in has just ended and the bass lands on the beat.
import { segmentAt, tEpoch } from "./tempomap.js";

export const API = "arsenal.jam.groove/v0";
export const ENGINE = "groove/1";
export const LEVEL = 44;
export const DEFAULT_HUMANIZE = 0.6;
export const DEFAULT_BPM = 66;
export const GROOVES_V1 = Object.freeze(["hold", "ballad", "pulse"]);
export const GROOVES_V2 = Object.freeze(["swell", "arp", "gospel"]);
export const BACKINGS_V1 = Object.freeze(["full", "comp", "bass"]);
export const TRY_BACKINGS = Object.freeze(["ghosts", "bass", "loop"]);
export const MODES = Object.freeze(["loop", "try", "play"]);
export const GROOVE_OFFSET = Object.freeze({ hold: -2, ballad: 0, pulse: -4 });
export const PULSE_ACCENTS = Object.freeze({ 4: Object.freeze([6, -6, -2, -6, 3, -6, -2, -4]),
  3: Object.freeze([6, -6, -2, -6, 2, -6]) });
export const PHRASE_WEIGHT = Object.freeze([0.5, 0.75, 0.5, 2.25]);  // arsenal/band.py, arsenal/fl/vfx/arsenal_band.py
export const GATE = 0.03;          // beats: "to chord end" releases this far before the next chord
export const BASS_GAP = 0.05;      // beats: a bass note ends this far before the next bass onset
export const E1 = 28;              // the lowest bass note (10.1)
export const BASS_OCTAVE = Object.freeze([28, 52]);  // groove octave notes stay in E1-E3 (MUSIC 5.8)
export const BREATH_MAX_BPM = 100; // hold's breath row needs a beat of 0.6 s or more
export const PLAY_LEGATO_MS = 80;
export const PLAY_DETACHED_MS = 40;
export const COUNT_TICK = Object.freeze({ vel: 60, down_hz: 2000, beat_hz: 1500 });
export const GHOST_TICK = Object.freeze({ vel: 40, hz: 1500 });

const EPS = 1e-6;
const MIN_LEN = 0.02;
const VOICE_RANK = { tick: 0, bass: 1, upper: 2 };
const ROLE_ORDER = ["root", "third", "fifth", "sixth", "seventh", "ninth", "eleventh", "thirteenth", "sus"];
const LETTER_PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };

export class GrooveError extends Error {
  constructor(field, message) {
    super(field ? `${field}: ${message}` : message);
    this.name = "GrooveError";
    this.field = field || null;
  }
}

const near = (a, b) => Math.abs(a - b) <= EPS;
const clamp = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);
const zero = (v) => (v === 0 ? 0 : v);  // no -0 in the JSON
const r6 = (x) => zero(Math.round(x * 1e6) / 1e6);
const r3 = (x) => zero(Math.round(x * 1e3) / 1e3);
const mod = (a, n) => ((a % n) + n) % n;

// ---------------------------------------------------------------------------------------------------- random source
export function fnv1a32(text) {
  let h = 0x811c9dc5;
  const s = String(text);
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

// mulberry32: next() in [0, 1).
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// The draws of one lane of one bar: "${seed}:${pass}:${bar}:${lane}" (the HUMANIZE INVARIANT above).
export function laneRandom(seed, pass, bar, lane) {
  const next = mulberry32(fnv1a32(`${seed}:${pass}:${bar}:${lane}`));
  return {
    next,
    uniform: (lo, hi) => lo + (hi - lo) * next(),
    normal: () => {  // Box-Muller, one standard normal per call (two uniforms)
      const u1 = 1 - next();
      const u2 = next();
      return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    },
  };
}

// ---------------------------------------------------------------------------------------------------- music helpers
// The pitch classes of a key name ("Eb major", "C# minor", "Dm"); null when the name does not parse.
export function keyScale(keyName) {
  const m = /^\s*([A-Ga-g])([#b♯♭]*)\s*(major|minor|maj|min|m|M)?\s*$/.exec(String(keyName ?? ""));
  if (!m) return null;
  let pc = LETTER_PC[m[1].toUpperCase()];
  for (const ch of m[2]) pc += ch === "#" || ch === "♯" ? 1 : -1;
  const minor = m[3] === "minor" || m[3] === "min" || m[3] === "m";
  const steps = minor ? [0, 2, 3, 5, 7, 8, 10] : [0, 2, 4, 5, 7, 9, 11];
  return steps.map((s) => mod(pc + s, 12));
}

// The approach note from bass b to the next bass nb (10.2), or null when none is played.
export function approachNote(b, nb, scalePcs = null) {
  const d = nb - b;
  const ad = Math.abs(d);
  if (ad <= 2) return null;
  if (ad <= 4) {
    const lo = Math.min(b, nb), hi = Math.max(b, nb), mid = (b + nb) / 2;
    let best = null;
    if (Array.isArray(scalePcs)) {
      for (let p = lo + 1; p < hi; p++) {  // ascending, so a tie in distance keeps the lower note
        if (!scalePcs.includes(mod(p, 12))) continue;
        if (best === null || Math.abs(p - mid) < Math.abs(best - mid)) best = p;
      }
    }
    return best !== null ? best : Math.floor(mid);
  }
  return nb - 1 < E1 ? nb + 1 : nb - 1;
}

// Ballad's second bass: the natural 5th nearest the first bass when the chord has one, stands in root position and
// the note is in E1-E3; else the first bass again.
export function secondBass(slot, b) {
  const t = slot.tones_pc || {};
  if (t.root == null || t.fifth == null || mod(t.root + 7, 12) !== t.fifth || slot.bass_pc !== t.root) return b;
  for (const c of [b - 5, b + 7]) if (c >= BASS_OCTAVE[0] && c <= BASS_OCTAVE[1]) return c;
  return b;
}

function roleOfPc(slot, midi) {
  const t = slot.tones_pc || {};
  const pc = mod(midi, 12);
  for (const r of ROLE_ORDER) if (t[r] === pc) return r;
  return null;
}

// {bass, upper: [{midi, role, lane}]} of a slot's voicing for a backing (sorted, roles kept with their notes).
function voicingOf(slot, backing) {
  const v = slot.voicings || {};
  const notes = Array.isArray(v[backing]) ? v[backing] : [];
  const roles = slot.roles && Array.isArray(slot.roles[backing]) ? slot.roles[backing] : [];
  const seen = new Set();
  const pairs = notes.map((midi, i) => ({ midi, role: roles[i] ?? null })).sort((a, b) => a.midi - b.midi)
    .filter((p) => !seen.has(p.midi) && seen.add(p.midi));  // a note listed twice sounds once
  if (!pairs.length) return { bass: null, upper: [] };
  const upper = backing === "bass" ? [] : pairs.slice(1).map((p, i) => ({ midi: p.midi, role: p.role, lane: i + 1 }));
  return { bass: pairs[0].midi, upper };
}

// Pulse's upper voices (10.5): the 3rd or sus, the 7th or 6th and the top colour, from the full voicing; comp plays
// the voices it has.
export function pulseVoices(upper, backing) {
  if (backing !== "full" || upper.length <= 3) return upper.slice();
  const pick = new Set();
  const highest = (roles) => {
    for (let i = upper.length - 1; i >= 0; i--) if (!pick.has(i) && roles.includes(upper[i].role)) return i;
    return -1;
  };
  for (const roles of [["third", "sus"], ["seventh", "sixth"], ["ninth", "eleventh", "thirteenth"]]) {
    const i = highest(roles);
    if (i >= 0) pick.add(i);
  }
  for (let i = upper.length - 1; i >= 0 && pick.size < 3; i--) pick.add(i);
  return upper.filter((_, i) => pick.has(i));
}

// ---------------------------------------------------------------------------------------------------- checks
function checkDef(def) {
  if (!def || typeof def !== "object") throw new GrooveError("def", "must be a resolved def object");
  const m = def.beats_per_bar;
  if (!Number.isInteger(m) || m < 1) throw new GrooveError("def.beats_per_bar", `must be a positive integer (got ${m})`);
  const c = def.cycle_beats;
  if (typeof c !== "number" || !(c > 0) || !near(c / m, Math.round(c / m))) {
    throw new GrooveError("def.cycle_beats", `must be a positive whole number of bars (got ${c})`);
  }
  if (!Array.isArray(def.slots)) throw new GrooveError("def.slots", "must be a list");
  let end = 0;
  def.slots.forEach((s, i) => {
    const at = `def.slots[${i}]`;
    if (!s || typeof s !== "object") throw new GrooveError(at, "must be an object");
    if (typeof s.at_beat !== "number" || s.at_beat < end - EPS) throw new GrooveError(`${at}.at_beat`, "must be ordered and not overlap");
    if (typeof s.beats !== "number" || !(s.beats > 0)) throw new GrooveError(`${at}.beats`, "must be a positive number");
    end = s.at_beat + s.beats;
    if (end > c + EPS) throw new GrooveError(`${at}.beats`, `must end inside cycle_beats ${c}`);
    if (!s.voicings || typeof s.voicings !== "object") throw new GrooveError(`${at}.voicings`, "must be an object");
  });
}

function numberSetting(value, fallback, field, lo, hi) {
  if (value == null) return fallback;
  if (typeof value !== "number" || !Number.isFinite(value) || value < lo || value > hi) {
    throw new GrooveError(field, `must be a number from ${lo} to ${hi} (got ${JSON.stringify(value)})`);
  }
  return value;
}

// The settings a bar actually plays, with v1 fallbacks: {mode, groove, backing, level, L, humanize, seed, walk,
// dropout, try_backing, muted, warnings}. L is the base velocity: level plus the groove's offset (level alone for
// Try bass).
export function effectiveSettings(def, settings = {}, opts = {}) {
  checkDef(def);
  const s = settings || {};
  const warnings = [];
  const m = def.beats_per_bar;
  const tryBacking = s.try_backing ?? null;
  if (tryBacking !== null && !TRY_BACKINGS.includes(tryBacking)) {
    throw new GrooveError("settings.try_backing", `must be one of ${TRY_BACKINGS.join(", ")} (got ${JSON.stringify(tryBacking)})`);
  }
  const mode = tryBacking !== null ? "try" : (opts.mode ?? "loop");
  if (!MODES.includes(mode)) throw new GrooveError("mode", `must be one of ${MODES.join(", ")} (got ${JSON.stringify(mode)})`);
  let groove = s.groove ?? ((opts.bpm ?? DEFAULT_BPM) < 80 ? "ballad" : "pulse");
  if (GROOVES_V2.includes(groove)) {
    warnings.push(`groove ${groove} is v2: ballad plays instead`);
    groove = "ballad";
  }
  if (!GROOVES_V1.includes(groove)) {
    throw new GrooveError("settings.groove", `must be one of ${GROOVES_V1.join(", ")} (got ${JSON.stringify(groove)})`);
  }
  if (groove !== "hold" && m !== 4 && m !== 3) {
    warnings.push(`meter ${m} has hold only: ${groove} plays hold`);
    groove = "hold";
  }
  let backing = s.backing ?? def.backing ?? "comp";
  if (backing === "pad") {
    warnings.push("backing pad is v2: comp plays instead");
    backing = "comp";
  }
  if (!BACKINGS_V1.includes(backing)) {
    throw new GrooveError("settings.backing", `must be one of ${BACKINGS_V1.join(", ")} (got ${JSON.stringify(backing)})`);
  }
  const level = numberSetting(s.level, LEVEL, "settings.level", 1, 127);
  const humanize = numberSetting(s.humanize, DEFAULT_HUMANIZE, "settings.humanize", 0, 1);
  const seed = s.seed ?? 0;
  if (!Number.isInteger(seed)) throw new GrooveError("settings.seed", `must be an integer (got ${JSON.stringify(seed)})`);
  let walk = s.walk ?? 1;
  if (!Number.isInteger(walk) || walk < 0 || walk > 2) throw new GrooveError("settings.walk", `must be 0, 1 or 2 (got ${JSON.stringify(walk)})`);
  if (walk === 2) {
    warnings.push("walk 2 is v2: walk 1 plays instead");
    walk = 1;
  }
  const dropout = numberSetting(s.dropout, 0, "settings.dropout", 0, 1);
  const L = level + (mode === "try" && tryBacking === "bass" ? 0 : GROOVE_OFFSET[groove]);
  return { mode, groove, backing, level, L, humanize, seed, walk, dropout, try_backing: tryBacking, muted: !!s.muted,
    warnings };
}

// ---------------------------------------------------------------------------------------------------- structure
// A chord [X0, X1) cut at bar lines. X counts beats from the def's first downbeat; s0/s1 are bar beats.
function piecesOf(X0, X1, m) {
  const out = [];
  let a = X0;
  while (a < X1 - EPS) {
    const k = Math.floor(a / m + EPS);
    const barX = k * m;
    const b = Math.min(X1, barX + m);
    out.push({ k, barX, X: a, s0: a - barX, s1: b - barX, first: out.length === 0, last: false });
    a = b;
  }
  if (out.length) out[out.length - 1].last = true;
  return out;
}

// The chord after slot i (it must start where slot i ends), with wrap true when it is slot 0 of the next pass.
function nextOf(def, i) {
  const slots = def.slots;
  const end = slots[i].at_beat + slots[i].beats;
  if (i + 1 < slots.length) return near(slots[i + 1].at_beat, end) ? { j: i + 1, wrap: false } : null;
  return near(end, def.cycle_beats) && near(slots[0].at_beat, 0) ? { j: 0, wrap: true } : null;
}

// Slot pieces sounding in bar k of the def: [{slot, beat, beats, onset, n, name}] (for the Now header and ghosts).
export function chordsInBar(def, barIndex, { def_from_bar = 0 } = {}) {
  checkDef(def);
  const m = def.beats_per_bar, C = def.cycle_beats;
  const k = barIndex - def_from_bar;
  if (k < 0) return [];
  const p = Math.floor(k / (C / m));
  const s = k * m, e = s + m;
  const out = [];
  def.slots.forEach((slot, i) => {
    const X0 = p * C + slot.at_beat, X1 = X0 + slot.beats;
    if (X1 <= s + EPS || X0 >= e - EPS) return;
    const a = Math.max(X0, s), b = Math.min(X1, e);
    out.push({ slot: i, beat: r6(a - s), beats: r6(b - a), onset: X0 >= s - EPS, n: slot.n ?? null, name: slot.name ?? null });
  });
  return out;
}

function dropoutRolls(def, E, dfb) {
  const B = def.cycle_beats / def.beats_per_bar;
  const roll = (k) => {
    if (k < 0) return false;
    const chance = 1 - Math.pow(1 - E.dropout, PHRASE_WEIGHT[k % 4]);
    return laneRandom(E.seed, Math.floor(k / B), dfb + k, "dropout").next() < chance;
  };
  return (k) => E.dropout > 0 && k > 0 && roll(k) && !roll(k - 1);
}

// True when bar barIndex is a dropout bar under these settings (everything but the bass rests).
export function dropoutBar(def, settings, barIndex, opts = {}) {
  const E = effectiveSettings(def, settings, opts);
  if (E.mode === "play" || E.muted) return false;
  const dfb = opts.def_from_bar ?? 0;
  return dropoutRolls(def, E, dfb)(barIndex - dfb);
}

// Every note of pass p (plus the pickups into its first chord), before slicing: loop and Try.
function buildPass(def, E, p, opts) {
  const m = def.beats_per_bar, C = def.cycle_beats, slots = def.slots;
  const B = C / m;
  const dfb = opts.def_from_bar ?? 0;
  const bpm = opts.bpm ?? DEFAULT_BPM;
  const tryBass = E.mode === "try" && E.try_backing === "bass";
  const groove = tryBass ? "trybass" : E.groove;
  const backing = tryBass ? "bass" : E.backing;
  const notes = [];
  const inst = (pass, i) => ({ pass, i, key: `${pass}:${i}`, slot: slots[i], X0: pass * C + slots[i].at_beat,
    X1: pass * C + slots[i].at_beat + slots[i].beats });
  const chords = slots.map((_, i) => inst(p, i));
  const add = (n) => {
    const note = { removed: false, limit: Infinity, fixed: true, toEnd: false, top: false, rolled: false, early: false,
      role: null, freq: null, ...n };
    if (note.owner === undefined) note.owner = note.X;
    note.rawLen = note.len;
    notes.push(note);
    return note;
  };

  // 1. The table rows of every chord.
  for (const ch of chords) {
    const { bass, upper } = voicingOf(ch.slot, backing);
    const top = upper.length ? upper[upper.length - 1].midi : null;
    const bassRow = (X, off, len, row, extra = {}) => {
      if (bass == null) return;
      add({ X, len, midi: extra.midi ?? bass, off, voice: "bass", lane: 0, role: "bass", row, slot: ch.i, chord: ch.key,
        chordEnd: ch.X1, ...extra });
    };
    const upperRow = (X, voices, off, topOff, len, row, extra = {}) => {
      for (const v of voices) {
        const isTop = v.midi === top;
        add({ X, len, midi: v.midi, off: isTop ? topOff : off, top: isTop, voice: "upper", lane: v.lane, role: v.role,
          row, slot: ch.i, chord: ch.key, chordEnd: ch.X1, ...extra });
      }
    };
    const inner = upper.filter((v) => v.midi !== top);
    for (const piece of piecesOf(ch.X0, ch.X1, m)) {
      const onDownbeat = near(piece.s0, 0);
      const has = (b) => onDownbeat && b < piece.s1 - EPS;  // a later bar-beat row fits this piece
      if (groove === "hold" || groove === "trybass") {
        if (!piece.first) continue;
        const len = ch.X1 - GATE - ch.X0;
        bassRow(ch.X0, 2, len, "bass", { toEnd: true, fixed: false });
        if (groove === "hold") upperRow(ch.X0, upper, -4, 0, len, "upper", { toEnd: true, fixed: false, rolled: true });
      } else if (groove === "ballad" && m === 3) {
        if (piece.first || onDownbeat) {
          bassRow(piece.X, 4, 2.9, "bass");
          upperRow(piece.X, upper, -2, 2, 0.95, "upper", { rolled: true });
        }
        for (const b of [1, 2]) if (has(b)) upperRow(piece.barX + b, inner, -10, -10, 0.8, "inner");
      } else if (groove === "ballad") {
        if (piece.first || onDownbeat) {
          bassRow(piece.X, 4, 1.9, "bass");
          upperRow(piece.X, upper, -2, 2, 1.95, "upper", { rolled: true });
        }
        if (has(2)) {
          if (bass != null) bassRow(piece.barX + 2, -2, 1.9, "second", { midi: secondBass(ch.slot, bass) });
          upperRow(piece.barX + 2, inner, -10, -10, 1.95, "inner");
        }
      } else {  // pulse
        const voices = pulseVoices(upper, backing);
        const vTop = voices.length ? voices[voices.length - 1].midi : null;
        const accents = PULSE_ACCENTS[m];
        for (let e = Math.ceil(piece.s0 * 2 - EPS); e / 2 < piece.s1 - EPS; e++) {
          const off = -4 + accents[e % accents.length];
          for (const v of voices) {
            add({ X: piece.barX + e / 2, len: 0.28, midi: v.midi, off, top: v.midi === vTop, voice: "upper", lane: v.lane,
              role: v.role, row: "eighth", slot: ch.i, chord: ch.key, chordEnd: ch.X1 });
          }
        }
        if (piece.first || onDownbeat) bassRow(piece.X, 2, m === 4 ? 1.9 : 2.9, "bass");
        if (m === 4 && has(2)) bassRow(piece.barX + 2, 0, 1.9, "second");
      }
    }
  }

  // 2. Ties (hold, Try bass): last chord first, so a chain of ties grows backwards. Never across the wrap.
  const tiedIn = new Map(), tiedOut = new Map();
  const mark = (map, key, v) => { if (!map.has(key)) map.set(key, new Set()); map.get(key).add(v); };
  if (groove === "hold" || groove === "trybass") {
    const heads = new Map();  // chord|voice|midi -> the beat-0 held note
    for (const n of notes) if (n.toEnd) heads.set(`${n.chord}|${n.voice}|${n.midi}`, n);
    for (let i = chords.length - 1; i >= 0; i--) {
      const nx = nextOf(def, i);
      if (!nx || nx.wrap) continue;
      const A = chords[i], Bc = chords[nx.j];
      for (const a of notes) {
        if (a.removed || a.chord !== A.key || !a.toEnd) continue;
        const b = heads.get(`${Bc.key}|${a.voice}|${a.midi}`);
        if (!b || b.removed) continue;
        a.len = b.X + b.len - a.X;
        a.chordEnd = b.chordEnd;
        b.removed = true;
        mark(tiedOut, A.key, `${a.voice}:${a.midi}`);
        mark(tiedIn, Bc.key, `${a.voice}:${a.midi}`);
      }
    }
  }

  // 3. Hold's breath re-strike: bar beat 2, once the chord has sounded 2 beats, for voices that do not tie.
  if (groove === "hold" && bpm <= BREATH_MAX_BPM && m >= 3) {
    for (const ch of chords) {
      if (ch.slot.beats < 4 - EPS) continue;
      const { upper } = voicingOf(ch.slot, backing);
      const skip = (v) => tiedIn.get(ch.key)?.has(`upper:${v.midi}`) || tiedOut.get(ch.key)?.has(`upper:${v.midi}`);
      const voices = upper.filter((v) => !skip(v));
      for (const piece of piecesOf(ch.X0, ch.X1, m)) {
        const X = piece.barX + 2;
        if (X < piece.X - EPS || X > piece.barX + piece.s1 - EPS || X < ch.X0 + 2 - EPS) continue;
        for (const v of voices) {
          add({ X, len: ch.X1 - GATE - X, midi: v.midi, off: -12, voice: "upper", lane: v.lane, role: v.role, row: "breath",
            slot: ch.i, chord: ch.key, chordEnd: ch.X1, toEnd: true, fixed: false });
        }
      }
    }
  }

  // 4. Pickups: the approach bass, or ballad's early step, from each chord into the next (and into this pass's first
  // chord from the ring's last chord of the pass before).
  const pickup = (A, Bc) => {
    if (E.walk < 1) return;
    const b = voicingOf(A.slot, backing).bass, nb = voicingOf(Bc.slot, backing).bass;
    if (b == null || nb == null || b === nb) return;
    const ps = piecesOf(A.X0, A.X1, m);
    const last = ps[ps.length - 1];
    const room = last.s1 - last.s0;
    if (groove === "hold" ? room <= 2 + EPS : room < 2 - EPS) return;
    const sectionChange = Bc.slot.section !== A.slot.section || Bc.i === 0;
    if (groove === "ballad" && sectionChange && !near(Bc.X0, 0)) {
      add({ X: Bc.X0 - 0.5, len: 0.5, midi: nb, off: 4, voice: "bass", lane: 0, role: "bass", row: "early", slot: Bc.i,
        chord: Bc.key, chordEnd: Bc.X1, owner: Bc.X0, early: true, fixed: false });
      return;
    }
    const midi = approachNote(b, nb, keyScale(A.slot.key) ?? A.slot.scale ?? null);
    if (midi == null) return;
    const X = Bc.X0 - 1;
    for (const n of notes) if (!n.removed && n.voice === "bass" && n.chord === A.key && near(n.X, X)) n.removed = true;
    add({ X, len: 0.9, midi, off: -6, voice: "bass", lane: 0, role: "approach", row: "approach", slot: Bc.i, chord: A.key,
      chordEnd: A.X1, owner: Bc.X0 });
  };
  chords.forEach((A, i) => {
    const nx = nextOf(def, i);
    if (nx) pickup(A, nx.wrap ? inst(p + 1, nx.j) : chords[nx.j]);
  });
  const lastSlot = slots.length - 1;
  const into = lastSlot >= 0 ? nextOf(def, lastSlot) : null;
  if (into && into.wrap) pickup(inst(p - 1, lastSlot), chords[0]);

  // 5. One bass voice; an upper note ends before it strikes again.
  const byX = (a, b) => a.X - b.X || a.midi - b.midi;
  const live = () => notes.filter((n) => !n.removed);
  const bassLine = live().filter((n) => n.voice === "bass").sort(byX);
  for (let i = 0; i + 1 < bassLine.length; i++) {
    const a = bassLine[i];
    const nextX = bassLine[i + 1].X;
    const cap = nextX - a.X - (near(nextX, a.chordEnd) ? GATE : BASS_GAP);  // the next chord's bass: the gate
    a.limit = Math.min(a.limit, cap);
    a.len = Math.max(Math.min(a.len, cap), MIN_LEN);
  }
  const uppers = new Map();
  for (const n of live()) if (n.voice === "upper") { if (!uppers.has(n.midi)) uppers.set(n.midi, []); uppers.get(n.midi).push(n); }
  for (const list of uppers.values()) {
    list.sort(byX);
    for (let i = 0; i + 1 < list.length; i++) {
      const a = list[i];
      if (near(list[i + 1].X, a.X)) continue;
      const cap = list[i + 1].X - a.X - GATE;
      a.limit = Math.min(a.limit, cap);
      a.len = Math.max(Math.min(a.len, cap), MIN_LEN);
    }
  }

  // 6. Gate: nothing outlives its chord, except ties (already to their last chord's end) and the early step.
  for (const n of live()) {
    if (n.early) continue;
    const cap = n.chordEnd - GATE - n.X;
    n.limit = Math.min(n.limit, cap);
    n.len = Math.max(Math.min(n.len, cap), MIN_LEN);
  }

  // 7. The early step takes over its chord's (gated) downbeat bass, so it never rings past that chord.
  const downbeats = new Map();
  for (const n of live()) if (n.voice === "bass" && n.row === "bass") downbeats.set(`${n.chord}|${r6(n.X)}`, n);
  for (const e of live()) {
    if (!e.early) continue;
    const d = downbeats.get(`${e.chord}|${r6(e.owner)}`);
    if (!d || d.removed) continue;
    e.len = d.X + d.len - e.X;
    d.removed = true;
  }

  // 8. Dropout bars: the upper voices rest for one bar.
  if (E.dropout > 0) {
    const isDrop = dropoutRolls(def, E, dfb);
    const passEnd = (p + 1) * C;
    for (let k = p * B; k < (p + 1) * B; k++) {
      if (!isDrop(k)) continue;
      const Ds = k * m, De = Ds + m;
      for (const n of live()) {
        if (n.voice !== "upper") continue;
        const end = n.X + n.len;
        if (Math.floor(n.owner / m + EPS) === k) {
          n.removed = true;                                  // struck in the hole: it rests
        } else if (n.X < Ds - EPS && end > Ds + EPS) {
          n.len = Math.max(Ds - GATE - n.X, MIN_LEN);        // ringing into the hole: it ends at the bar line
          n.limit = Math.min(n.limit, n.len);
        } else {
          continue;
        }
        if (end > De + EPS && De < passEnd - EPS && !isDrop(k + 1)
          && !notes.some((o) => !o.removed && o.voice === "upper" && o.midi === n.midi && near(o.X, De))) {
          add({ X: De, len: end - De, midi: n.midi, off: n.off, top: n.top, voice: "upper", lane: n.lane, role: n.role,
            row: "restrike", slot: n.slot, chord: n.chord, chordEnd: n.chordEnd, toEnd: n.toEnd, fixed: false });
        }
      }
    }
  }

  // 9. Humanise, lane by lane, bar by bar (the HUMANIZE INVARIANT).
  const h = E.humanize;
  const breaths = [];  // breaths[j]: the walk after bar j, walked from the def's first bar
  const breathAt = (k) => {
    if (k < 0) return 0;
    while (breaths.length <= k) {
      const j = breaths.length;
      const u = laneRandom(E.seed, Math.floor(j / B), dfb + j, "breath").next();
      const step = u < 0.3 ? -1 : u < 0.7 ? 0 : 1;
      breaths.push(clamp((j ? breaths[j - 1] : 0) + step * h, -4, 4));
    }
    return breaths[k];
  };
  const groups = new Map();
  const rolls = new Map();
  for (const n of live()) {
    n.ownerBar = Math.floor(n.owner / m + EPS);
    const key = `${n.ownerBar}|${n.lane}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(n);
    if (n.rolled) {
      if (!rolls.has(n.ownerBar)) rolls.set(n.ownerBar, new Map());
      const strikes = rolls.get(n.ownerBar);
      if (!strikes.has(n.X)) strikes.set(n.X, []);
      strikes.get(n.X).push(n);
    }
  }
  for (const list of groups.values()) {
    list.sort((a, b) => a.X - b.X || a.midi - b.midi || (a.row < b.row ? -1 : a.row > b.row ? 1 : 0));
    const ob = list[0].ownerBar;
    const pass = Math.floor(ob / B);
    const rng = laneRandom(E.seed, pass, dfb + ob, list[0].lane);
    const q = mod(ob, B);
    const shade = breathAt(ob) + Math.round(3 * h * Math.sin(Math.PI * (q + 0.5) / B)) + (h > 0 && (pass === 0 || pass === 1) ? -2 : 0);
    for (const n of list) {
      const tN = rng.normal(), vN = rng.normal(), lU = rng.uniform(-1, 1);
      const bass = n.voice === "bass";
      let t = clamp((bass ? 2.5 : 5) * h * tN, -12 * h, 12 * h);
      if (bass && near(mod(n.X, m), 0)) t = Math.max(t, -4);
      n.ms = t;
      let v = Math.round(E.L + n.off + Math.round(2.5 * h * vN) + shade);
      if (n.top) v = Math.min(v, E.L + Math.max(2, n.off));
      n.vel = clamp(v, 1, 127);
      if (n.fixed) n.len = Math.max(Math.min(n.rawLen * (1 + 0.03 * h * lU), n.limit), MIN_LEN);
    }
  }
  for (const [ob, strikes] of rolls) {
    const rng = laneRandom(E.seed, Math.floor(ob / B), dfb + ob, "roll");
    const [lo, hi] = E.groove === "hold" ? [4, 9] : [8, 14];
    for (const X of [...strikes.keys()].sort((a, b) => a - b)) {
      const r = rng.uniform(lo, hi) * h;
      strikes.get(X).sort((a, b) => a.midi - b.midi).forEach((n, i) => { n.ms += i * r; });
    }
  }
  return live();
}

// Every note of a Play run (one pass, no humanising).
function buildPlay(def, opts) {
  const m = def.beats_per_bar;
  const bpm = opts.bpm ?? DEFAULT_BPM;
  const beats = (ms) => ms * bpm / 60000;
  const notes = [];
  def.slots.forEach((slot, i) => {
    const play = Array.isArray(slot.voicings.play) ? [...new Set(slot.voicings.play)].sort((a, b) => a - b) : [];
    if (!play.length) return;
    const hold = slot.hold ?? "legato";
    let len;
    if (typeof hold === "number") len = hold;
    else if (hold === "detached") len = Math.max(slot.beats - beats(PLAY_DETACHED_MS), MIN_LEN);
    else len = slot.beats + beats(PLAY_LEGATO_MS);
    const vel = clamp(Math.round(slot.vel ?? 48), 1, 127);
    const arp = slot.arp_ms ?? 0;
    play.forEach((midi, v) => {
      notes.push({ X: slot.at_beat, len, midi, vel, ms: v * arp, voice: v === 0 ? "bass" : "upper",
        role: v === 0 ? "bass" : roleOfPc(slot, midi), row: "play", slot: i, freq: null, ownerBar: Math.floor(slot.at_beat / m + EPS) });
    });
  });
  const same = new Map();
  for (const n of notes) { if (!same.has(n.midi)) same.set(n.midi, []); same.get(n.midi).push(n); }
  for (const list of same.values()) {
    list.sort((a, b) => a.X - b.X);
    for (let i = 0; i + 1 < list.length; i++) {
      if (list[i + 1].X > list[i].X + EPS) list[i].len = Math.min(list[i].len, list[i + 1].X - list[i].X);
    }
  }
  return notes;
}

function ticks(m, vel, downHz, beatHz, row) {
  const out = [];
  for (let b = 0; b < m; b++) {
    out.push({ beat: b, midi: null, vel, len: 0, role: null, voice: "tick", tie: null, ms: 0, carry: false, slot: null,
      row, freq: b === 0 ? downHz : beatHz });
  }
  return out;
}

function sortEvents(events) {
  return events.sort((a, b) => a.beat - b.beat || VOICE_RANK[a.voice] - VOICE_RANK[b.voice] || (a.midi ?? 0) - (b.midi ?? 0)
    || (a.carry === b.carry ? 0 : a.carry ? -1 : 1) || (a.row < b.row ? -1 : a.row > b.row ? 1 : 0));
}

// Bar k's slice of the notes: what it strikes (its own notes and pickups) and what it carries.
function sliceBar(notes, k, m) {
  const s = k * m, e = s + m;
  const out = [];
  for (const n of notes) {
    const end = n.X + n.len;
    const tie = end > e + EPS ? "next" : null;
    if (n.ownerBar === k) {
      out.push({ beat: r6(n.X - s), midi: n.midi, vel: n.vel, len: r6(n.len), role: n.role, voice: n.voice, tie,
        ms: r3(n.ms), carry: false, slot: n.slot, row: n.row, freq: null });
    } else if (n.ownerBar < k && n.X < s - EPS && end > s + EPS) {
      out.push({ beat: 0, midi: n.midi, vel: n.vel, len: r6(end - s), role: n.role, voice: n.voice, tie, ms: 0,
        carry: true, slot: n.slot, row: n.row, freq: null });
    }
  }
  return sortEvents(out);
}

// ---------------------------------------------------------------------------------------------------- public API
export function bar(def, settings, pass, barIndex, opts = {}) {
  const E = effectiveSettings(def, settings, opts);
  if (!Number.isInteger(barIndex)) throw new GrooveError("barIndex", `must be an integer (got ${JSON.stringify(barIndex)})`);
  const m = def.beats_per_bar;
  const B = def.cycle_beats / m;
  const dfb = opts.def_from_bar ?? 0;
  if (!Number.isInteger(dfb)) throw new GrooveError("def_from_bar", `must be an integer (got ${JSON.stringify(dfb)})`);
  const k = barIndex - dfb;
  const p = Math.floor(k / B);
  if (pass != null && pass !== p) {
    throw new GrooveError("pass", `bar ${barIndex} with def_from_bar ${dfb} is pass ${p}, not ${pass}`);
  }
  if (E.muted) return [];
  if (k < 0) return E.mode === "play" ? [] : ticks(m, COUNT_TICK.vel, COUNT_TICK.down_hz, COUNT_TICK.beat_hz, "count");
  if (E.mode === "play") return sliceBar(buildPlay(def, opts), k, m);
  if (E.mode === "try" && E.try_backing === "ghosts") return ticks(m, GHOST_TICK.vel, GHOST_TICK.hz, GHOST_TICK.hz, "ghost");
  return sliceBar(buildPass(def, E, p, { ...opts, def_from_bar: dfb }), k, m);
}

function settingsAt(list, barIndex) {
  if (!Array.isArray(list) || !list.length) throw new GrooveError("run.settings", "must be a non-empty list");
  let chosen = list[0];
  for (const s of list) {
    if (s.from_bar <= barIndex) chosen = s;
    else break;
  }
  return chosen;
}

function defFor(defs, version) {
  if (defs && typeof defs === "object" && defs.cycle_beats !== undefined) return defs;
  if (defs && typeof defs === "object" && defs[version] != null) return defs[version];
  throw new GrooveError("defs", `no def for def_version ${version}`);
}

// One bar of a run (run.json's beats_per_bar, segments, settings and mode): the def version, settings entry, bpm
// and def_from_bar come from the bar's segment. `defs` is a def or an object def_version -> def.
export function barOfRun(run, defs, barIndex) {
  if (!run || typeof run !== "object") throw new GrooveError("run", "must be an object");
  const m = run.beats_per_bar;
  const seg = segmentAt(run.segments, barIndex);
  if (!seg) throw new GrooveError("run.segments", "must be a non-empty list");
  const def = defFor(defs, seg.def_version);
  if (def.beats_per_bar !== m) throw new GrooveError("def.beats_per_bar", `is ${def.beats_per_bar} but the run's is ${m}`);
  const settings = settingsAt(run.settings, barIndex);
  const opts = { def_from_bar: seg.def_from_bar, bpm: seg.bpm, mode: run.mode ?? null };
  const pass = Math.floor((barIndex - seg.def_from_bar) / (def.cycle_beats / m));
  const E = effectiveSettings(def, settings, opts);
  return { bar: barIndex, pass, def_version: seg.def_version, def_from_bar: seg.def_from_bar, bpm: seg.bpm,
    settings_from_bar: settings.from_bar ?? null, warnings: E.warnings, events: bar(def, settings, pass, barIndex, opts) };
}

// The epoch of beat position x counted from bar barIndex's downbeat, x negative or past the bar included: each bar
// is measured at its own segment's tempo, so a pickup sits at the tempo of the bar before (as handoffEpoch).
export function beatEpoch(segments, m, barIndex, x) {
  const k = Math.floor(x / m + EPS);
  return tEpoch(segments, m, barIndex + k, Math.max(0, x - k * m));
}

// The events of bar barIndex with epoch_ms (onset, ms included) and end_epoch_ms (release) through the tempo map.
export function eventTimes(segments, m, barIndex, events) {
  return events.map((ev) => {
    const at = beatEpoch(segments, m, barIndex, ev.beat) + ev.ms;
    const end = ev.voice === "tick" ? at : beatEpoch(segments, m, barIndex, ev.beat + ev.len) + ev.ms;
    return { ...ev, epoch_ms: at, end_epoch_ms: end };
  });
}
