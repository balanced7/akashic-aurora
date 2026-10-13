// Lean: arsenal/web/piano/lean.js (pure ES module: no three.js, no DOM). Tests: tests/piano_lean.test.mjs.
//
// Daniel, 2026-10-12, in his words: "What would it take to have more musical concepts be apparent, parseable, knowable and
// understandable at once?" The story layer's one question back to him (docs/library/design, story-layer v1): "While you
// play, may your own screen show the lean: a thin light from the note that is leaning to the note it leans toward, there
// while you hold, gone when you move on? It would stay off your recordings unless you switch it on for a take." His answer,
// 2026-10-13: "can you enable the lean visualization thing".
// This module decides, by rule and nothing else, whether what sounds now leans home in the key, and which voice leans: the
// key's 7 (the leading tone; in minor the raised 7th) sitting under its 1. It draws nothing and names nothing: piano.js
// paints the frame on its own unrecorded glass, with no text. The KIND comes from the rule below, never from a chord name's
// suffix, and the lean is one of the four ingredients of how a chord feels (rub, lean, distance, wait): it is never summed
// with the others into one meter.
//
//   import { createLean } from "./piano/lean.js";
//   const lean = createLean(options?);         // options override any LEAN constant by name
//   const f = lean.update(input, dt, t);       // every frame; f is ONE object refreshed in place (nothing allocated per frame)
//   lean.reset();                              // back to rest (a new song, a seek)
//   lean.frame                                 // the same object update returns
//   lean.constants                             // the constants this lean runs on (LEAN with the options folded in)
//
// Input, read only, never written (the host hands the same object every frame):
//   input.sounding  Map midi -> { held, t0, ... }: the page's sounding map, every note the page holds sounding (a finger or
//                   the pedal). Only the keys (midi) are read: what sounds, not how.
//   input.rootPc    0..11: the root of the page's own chord reading while that reading is a chord (kind "chord"), else -1.
//   input.keyTonic  0..11: the tonic of the key the page shows, or -1 with no key.
//   input.keyMinor  true in a minor key. Read for nothing in v1: the leading tone is (tonic + 11) % 12 in both modes, which
//                   in minor is the raised 7th.
//   input.keyConf   how sure the page is of that key: 0 unsure, 1 fair, 2 sure, 3 locked by hand or set by Claude's band.
//   dt, t           seconds since the last frame, and the clock time now (the host's clock). A missing dt is taken from t; a
//                   t that goes backwards (a seek, a replay) starts the lean again from rest.
//
// The identity of what sounds is its pitch-class set together with its bass pitch class (the lowest sounding note % 12). A new
// identity must hold SETTLE seconds before it can make or end a claim, and every change starts that clock again, so a rolled
// chord, a passing note or a chord touched on the way somewhere else never lights anything. One exception keeps a light from
// blinking: a change that leaves the same leaning voice leaning to the same key (a 7th added to a held V, a note doubled, the
// home key pressed against the 7) keeps the light where it is while the new identity settles. Silence is no identity: it
// never makes a claim and never counts as going somewhere else.
//
// The rule (T the key's tonic, LT = (T + 11) % 12 its leading tone):
//   no lean when keyConf < MIN_CONF, when there is no key, when LT is not sounding, or when the bass is T (home is already
//   underneath: no claim). Otherwise:
//     the leading-tone diminished triad or 7th: DOMINANT, decided by its pitch classes (exactly LT, T + 2 and T + 5, with
//       or without T + 8) whatever root the reader spelled: the diminished 7th is symmetric, so any of its notes can read
//       as its root, and every inversion leans the same way.
//   Else, with r = (rootPc - T + 12) % 12:
//     r 7   DOMINANT  the 5 with its 3rd (V, V7, V9, V7sus with the 3rd ...)
//     r 11  DOMINANT  the 7 chord as the leading-tone chord: its own minor 3rd (T + 2) sounds and no major 3rd (T + 3) does
//                     (vii, vii half-diminished). A major or dominant chord on the 7 (B or B7 in C major, A7 in Bb major)
//                     is a secondary dominant leaning somewhere else (practice.classify(): "5 of 3m"): no lean.
//     r 5   BRIGHT4   the 4 holding the key's 7: his bright 4, "the 7 inside the 4" (IVmaj7#11, the Lydian 4)
//     any other r: no lean (I, ii, iii and vi make no claim even when they hold the 7).
//   With no chord reading (rootPc -1): a bass on the 5 ((T + 7) % 12) under three or more pitch classes with LT among them
//   is DOMINANT (practice.py's bass dominant); anything else is no lean.
// The voice: fromMidi is the HIGHEST sounding note whose pitch class is LT (the top voice is the one listeners follow,
// Bigand 1996), and toMidi = fromMidi + 1, home just above it. touching: toMidi itself sounds (the 7 pressed right against
// home, as in his add11 dominants).
// Landing, by the design record's binding rule: never say or draw that the 7 rose unless a voice actually left scale degree
// 7 and arrived on 1. When a lean that reached LAND_FROM is left, and the next identity that settles is home, events.landed
// fires only when the 7 rose to the very key the thread pointed to: the leaning note (fromMidi) no longer sounds, no other
// leading tone sounds a whole step or less below toMidi, toMidi itself sounds, and the bass is not the 7. land.midi is then
// toMidi. Home is a reading rooted on T (or, with no chord reading, a bass on T) whose bass is not the 5. Home's chord over
// the 5 (I6/4 after V, the cadential six-four) is still on the way: it neither lands nor ends the lean's memory, so the real
// I after it can still land. Home that keeps the 7 (his maj7 and maj9 homes), home over the 7 in the bass, and home whose 1
// sounds only in another octave all let the thread fade with nothing marked, as does going anywhere else: there is no
// "miss". The lean is remembered for this until its faded light is out (level under ACTIVE).
//
// Output f (the same object every frame; f.land and f.events keep their identity too):
//   f.active     level > ACTIVE: the light is showing (holding, or still fading out).
//   f.level      0..1, eased: toward 1 while a settled lean holds, toward 0 otherwise.
//   f.kind       0 none, 1 dominant, 2 bright4 (the KINDS words). Kept while the light fades; 0 once it is out.
//   f.fromMidi   the leaning note, toMidi the note it leans toward (fromMidi + 1). -1 before the first lean. Both are kept
//                while the light fades out, so a painter draws the fade where the light was.
//   f.touching   toMidi sounds too (kept while the light fades).
//   f.land = { midi, level, kept }: the home note a lean landed on (-1 before the first landing), and its glow, 1 at the
//                moment the home identity settled, easing to 0 over LAND seconds. kept is true for the one frame a remembered
//                lean's home settles still holding the key's 7 anywhere in it (the design record's ltKept), whether or not
//                another voice rose: it is for receipts only, and nothing is drawn for it.
//   f.events = { leaned, landed }: true only on the frame it happens. leaned: a settled lean appears, or moves to another
//                voice. landed: a lean landed (above).
//
// Smoothing: exponential and frame-rate independent (it uses dt). The level eases with ATTACK toward 1 and RELEASE toward 0.
// Its target changes only at an identity change (the frame it is seen, at t) and at a settle moment, which is placed exactly
// at the change time + SETTLE inside whichever frame it falls in, with the easing split at that moment, so the same playing
// gives the same level at 30 and at 144 frames a second. The landing glow is a function of the time since its settle
// moment, so it is exact at any frame rate.
//
// Constants (LEAN; labelled starting values for presentation only, no truth claim; any may be overridden by name):
//   SETTLE 0.3 s        an identity must hold this long before it can light, end or land a lean; any change restarts it
//   ATTACK 0.25 s       time constant of the light rising while a settled lean holds
//   RELEASE 0.45 s      time constant of the light fading once the lean is left
//   LAND 0.6 s          the landing glow eases from 1 to 0 over this long
//   MIN_CONF 1          the least key confidence a lean needs (0 unsure, 1 fair, 2 sure, 3 locked or the band's key)
//   LAND_FROM 0.3       a lean must have reached this level, when it is left, for its landing to count
//   ACTIVE 0.01         the level over which the light counts as showing (and the lean as remembered for a landing)
export const LEAN_API = "arsenal.piano.lean/v1";

export const LEAN = Object.freeze({
  SETTLE: 0.3, ATTACK: 0.25, RELEASE: 0.45, LAND: 0.6, MIN_CONF: 1, LAND_FROM: 0.3, ACTIVE: 0.01,
});
export const KINDS = Object.freeze(["none", "dominant", "bright4"]);
export const NONE = 0, DOMINANT = 1, BRIGHT4 = 2;

const POP = new Uint8Array(4096);  // set bits of a 12-bit pitch-class mask
for (let i = 1; i < 4096; i++) POP[i] = POP[i >> 1] + (i & 1);
const NO_TIME = -1e9;

export function createLean(options = {}) {
  const K = { ...LEAN };
  for (const key of Object.keys(LEAN)) if (options && typeof options[key] === "number" && Number.isFinite(options[key])) K[key] = options[key];

  // The one frame object. level starts as a fraction so the engine gives it a double slot from birth, and every later frame
  // writes it in place (reset() puts the resting values in first); the same for land.level.
  const f = {
    active: false, level: 0.5, kind: NONE, fromMidi: -1, toMidi: -1, touching: false,
    land: { midi: -1, level: 0.5, kept: false },
    events: { leaned: false, landed: false },
  };
  const L = f.land, E = f.events;

  // What sounds this frame (typed arrays: nothing boxed, nothing allocated).
  const there = new Uint8Array(128);   // 1 where a midi sounds now
  const list = new Int16Array(128);    // the midis set in `there`, to clear them next frame
  let listN = 0, mask = 0, low = 128, ltPc = -1, ltTop = -1;
  // Doubles sit in N: a closure variable holding a double would box a new number on every write, and so would a double
  // passed as an argument to a helper the engine does not inline (the settle moment, an easing span), once per chord change.
  const N = new Float64Array(5);
  const LAST_T = 0, ID_AT = 1, LAND_AT = 2, SETTLE_AT = 3, SPAN = 4;
  let started = false;
  // The identity held so far, and the lean state.
  let idSet = false, idSettled = false, idMask = 0, idBass = -1;
  let holding = false, armed = false, landing = false;
  // The reading of the stored identity as last frame saw it, for a settle moment that falls in the frame its identity left.
  let pKind = NONE, pFrom = -1, pTouch = false, pHome = false, pSix = false, pLand = -1, pKept = false;

  function visit(e, key) {
    const m = key | 0;
    if (m !== key || m < 0 || m > 127 || there[m] === 1) return;
    there[m] = 1;
    list[listN++] = m;
    const pcm = m % 12;
    mask |= 1 << pcm;
    if (m < low) low = m;
    if (pcm === ltPc && m > ltTop) ltTop = m;
  }

  // The key a lean lands on, for what sounds now: toMidi itself when the 7 rose to it (the leaning note and any leading
  // tone a whole step or less below toMidi are silent, toMidi sounds, and the bass is not the 7), else -1.
  function roseTo(bass) {
    const to = f.toMidi;
    if (to < 0 || to > 127 || there[to] !== 1 || bass === ltPc) return -1;
    if (f.fromMidi >= 0 && there[f.fromMidi] === 1) return -1;
    for (let m = to - 2; m < to; m++) if (m >= 0 && there[m] === 1 && m % 12 === ltPc) return -1;
    return to;
  }

  // The level eases toward target (0 or 1) over N[SPAN] seconds.
  function ease(target) {
    const span = N[SPAN];
    if (!(span > 0)) return;
    const tau = target > f.level ? K.ATTACK : K.RELEASE;
    f.level = target + (f.level - target) * Math.exp(-span / tau);
  }

  // The stored identity settles at time N[SETTLE_AT] with this reading.
  function settle(kind, from, touch, home, six, landAt, kept) {
    idSettled = true;
    if (idMask === 0) return;  // silence: no claim, and not somewhere else either
    if (kind !== NONE) {
      if (!holding || from !== f.fromMidi) E.leaned = true;
      holding = true;
      armed = false;  // a new lean replaces the old expectation
      f.kind = kind; f.fromMidi = from; f.toMidi = from + 1; f.touching = touch;
      return;
    }
    holding = false;
    if (!armed || six) return;  // the six-four is still on the way: the lean stays remembered
    armed = false;
    if (!home) return;  // somewhere else: the light fades and nothing is marked
    if (kept) L.kept = true;  // home keeps the 7 (receipts only)
    if (landAt >= 0) {
      E.landed = true;
      landing = true;
      L.midi = landAt;
      N[LAND_AT] = N[SETTLE_AT];
    }
  }

  function reset() {
    for (let i = 0; i < listN; i++) there[list[i]] = 0;
    listN = 0;
    N[LAST_T] = 0; N[ID_AT] = NO_TIME; N[LAND_AT] = NO_TIME; N[SETTLE_AT] = NO_TIME; N[SPAN] = 0;
    started = false; idSet = false; idSettled = false; idMask = 0; idBass = -1;
    holding = false; armed = false; landing = false;
    pKind = NONE; pFrom = -1; pTouch = false; pHome = false; pSix = false; pLand = -1; pKept = false;
    f.active = false; f.level = 0; f.kind = NONE; f.fromMidi = -1; f.toMidi = -1; f.touching = false;
    L.midi = -1; L.level = 0; L.kept = false;
    E.leaned = false; E.landed = false;
  }

  function update(input, dt, t) {
    if (typeof t !== "number" || t !== t) t = N[LAST_T] + (typeof dt === "number" && dt > 0 ? dt : 0);
    if (typeof dt !== "number" || !(dt >= 0)) dt = started ? t - N[LAST_T] : 0;
    if (!(dt > 0)) dt = 0;
    if (started && t < N[LAST_T] - 1e-6) { reset(); dt = 0; }
    started = true;
    N[LAST_T] = t;
    E.leaned = false; E.landed = false; L.kept = false;

    // ---- the key and the reading
    const inp = input || null;
    const r0 = inp ? inp.rootPc : -1, t0 = inp ? inp.keyTonic : -1, c0 = inp ? inp.keyConf : 0;
    const rootPc = typeof r0 === "number" && r0 === (r0 | 0) && r0 >= 0 && r0 < 12 ? r0 : -1;
    const T = typeof t0 === "number" && t0 === (t0 | 0) && t0 >= 0 && t0 < 12 ? t0 : -1;
    const conf = typeof c0 === "number" && c0 === c0 ? c0 : 0;

    // ---- what sounds now
    for (let i = 0; i < listN; i++) there[list[i]] = 0;
    listN = 0; mask = 0; low = 128; ltTop = -1;
    ltPc = T >= 0 ? (T + 11) % 12 : -1;
    const src = inp ? inp.sounding : null;
    if (src && typeof src.forEach === "function") src.forEach(visit);
    const bass = low < 128 ? low % 12 : -1;

    // ---- the rule, for what sounds now
    let kind = NONE;
    if (conf >= K.MIN_CONF && T >= 0 && ltTop >= 0 && bass !== T) {
      const two = 1 << ((T + 2) % 12), dim = (1 << ltPc) | two | (1 << ((T + 5) % 12)), dim7 = dim | (1 << ((T + 8) % 12));
      if ((mask & dim) === dim && (mask & ~dim7) === 0) {
        kind = DOMINANT;  // the leading-tone diminished triad or 7th, by its pitch classes, whatever root it reads
      } else if (rootPc >= 0) {
        const r = (rootPc - T + 12) % 12;
        if (r === 7) kind = DOMINANT;
        else if (r === 5) kind = BRIGHT4;
        else if (r === 11 && (mask & two) !== 0 && (mask & (1 << ((T + 3) % 12))) === 0) kind = DOMINANT;
      } else if (bass === (T + 7) % 12 && POP[mask] >= 3) {
        kind = DOMINANT;
      }
    }
    const from = kind !== NONE ? ltTop : -1;
    const touch = kind !== NONE && from + 1 <= 127 && there[from + 1] === 1;
    // home: rooted on T (or, unread, over a T bass) with the bass not on the 5; six: home's chord over the 5 (the six-four)
    const homeChord = T >= 0 && mask !== 0 && (rootPc >= 0 ? rootPc === T : bass === T);
    const six = homeChord && bass === (T + 7) % 12;
    const home = homeChord && !six;
    const landAt = home ? roseTo(bass) : -1;
    const kept = home && ltPc >= 0 && (mask & (1 << ltPc)) !== 0;
    const changed = !idSet || mask !== idMask || bass !== idBass;

    // ---- ease over the frame that just passed, with the target that was in force (split at a settle moment)
    const tPrev = t - dt;
    if (idSet && !idSettled && N[ID_AT] + K.SETTLE <= t) {
      let s = N[ID_AT] + K.SETTLE;
      if (s < tPrev) s = tPrev;
      N[SETTLE_AT] = s;
      N[SPAN] = s - tPrev;
      ease(holding ? 1 : 0);
      if (changed) settle(pKind, pFrom, pTouch, pHome, pSix, pLand, pKept);  // it settled just before it left
      else settle(kind, from, touch, home, six, landAt, kept);
      N[SPAN] = t - N[SETTLE_AT];
      ease(holding ? 1 : 0);
    } else {
      N[SPAN] = dt;
      ease(holding ? 1 : 0);
    }

    // ---- take the new reading, at t
    if (changed) {
      if (holding && !(kind !== NONE && from === f.fromMidi)) {
        holding = false;  // the lean is left: remembered for a landing if it was showing enough
        if (f.level >= K.LAND_FROM) armed = true;
      } else if (holding) {
        f.kind = kind; f.touching = touch;  // the same voice leaning to the same key: the light stays
      }
      idSet = true; idSettled = false; idMask = mask; idBass = bass; N[ID_AT] = t;
    } else if (idSettled && mask !== 0) {
      // the same identity, settled: it follows its own reading (a key that firms up or changes under a held chord)
      if (kind !== NONE) {
        if (!holding || from !== f.fromMidi) { E.leaned = true; armed = false; }
        holding = true;
        f.kind = kind; f.fromMidi = from; f.toMidi = from + 1; f.touching = touch;
      } else if (holding) {
        holding = false;  // the reading changed under the same notes: no move was made, so nothing is remembered
      }
    } else if (holding && kind !== NONE && from === f.fromMidi) {
      f.touching = touch;
    }
    pKind = kind; pFrom = from; pTouch = touch; pHome = home; pSix = six; pLand = landAt; pKept = kept;

    // ---- the outputs
    if (armed && !holding && f.level <= K.ACTIVE) armed = false;  // the faded light is out: the lean is forgotten
    f.active = f.level > K.ACTIVE;
    if (!f.active && !holding) f.kind = NONE;
    if (landing) {
      const u = (t - N[LAND_AT]) / K.LAND;
      if (u >= 1) { landing = false; L.level = 0; }
      else { const v = u > 0 ? u : 0; L.level = 1 - v * v * (3 - 2 * v); }  // a smooth fall: 1, gently, to 0
    }
    return f;
  }

  reset();
  return { update, reset, frame: f, constants: Object.freeze(K) };
}
