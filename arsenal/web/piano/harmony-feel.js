// Harmony feel: arsenal/web/piano/harmony-feel.js (pure ES module: no three.js, no DOM). Tests: tests/piano_harmony_feel.test.mjs.
//
// Daniel's ask for the /piano instruments round "Instruments of light", in his words: "certain chords and chord combinations can
// change the color or rendering of things", and "If we could visually represent the lushness and vibrance or simplicity of certain
// chords or relationships between bass note and solo, I think it would be cool if we had a way of capturing that dance".
// This module turns what is sounding into a handful of slow, smooth numbers a renderer can hang colour, bloom, grain, sway and
// geometry on. It draws nothing and decides no look: an instrument or scheme maps the numbers to its own light.
//
//   import { createHarmonyFeel } from "../harmony-feel.js";
//   const feel = createHarmonyFeel(options?);   // one per instrument or scheme; options override any FEEL constant by name
//   const f = feel.update(state, dt, t);        // every frame; f is ONE object refreshed in place (nothing allocated per frame)
//   feel.reset();                               // back to rest (a new song, a seek)
//   feel.frame                                  // the same object update returns, for a reader that is handed no frame
//   feel.constants                              // the constants this feel runs on (FEEL with the options folded in)
//
// Input, the instrument host's state (read only, never written):
//   state.sounding  Map midi -> { vel, t0, held, pedal, tRelease, strike }: every note that sounds, held by a finger or by the
//                   pedal. An older host without it: state.pressed (Map midi -> entry with vel and t0) is read instead.
//                   Used here: the key (midi), t0 (the strike time, on the same clock as t), held (false: the finger is up and
//                   the pedal holds the sound) and pedal (true: sustained by the pedal). vel, tRelease and strike are not used.
//   state.chord     { name, nns, key } while a chord reads, else null. The name ("Cmaj9#11", "G7b9#9", "Am/C") is parsed with
//                   the house readers (nashville.js parseChord for root and suffix, chordread.js parseSuffix for the tones) and
//                   decides what an ambiguous tone is: a #9 or a minor 3rd, a #11 or a b5, a b13 or a #5, a 6th or a dim7's 7th.
//                   A name is trusted only while it covers what sounds: at most one sounding pitch class outside its tones,
//                   and the bass is one of its tones or the bass it names. A name left over from the chord before ("Am" while
//                   F A C F sounds) fails both halves, so a stale name never colours the next chord. With no usable name the tones are
//                   read from the bass, or from another sounding note when the bass is plainly an inversion. The bass keeps the
//                   root while it plainly roots what sounds: a 3rd with a 7th above it (a seventh-chord shell, the 5th being the
//                   first note a voicing drops, so a C13 with no G is still a C), or a 3rd with a 5th and no b6. Otherwise the
//                   first sounding pitch class upward with both a 3rd and a 5th takes the root: E G C reads as C major, not as
//                   E with a b6, and E G B C as Cmaj7, not as E minor with a b6 (a b6 and no 7th is the mark of an inversion,
//                   not a chord tone). Where the pitch classes alone cannot tell them apart -- Eb G Bb C is a Cm7 and an Eb6
//                   note for note -- the bass decides, and a chord name, when the host has one, overrules it.
//   state.pedal     the host's pedal, read for nothing here: the entries already say which voices the pedal is holding (a
//                   voice with held false sounds only because of the pedal), which is what the colour needs.
//   dt, t           seconds since the last frame, and the clock time now (the host's clock, the one t0 is written in). A
//                   missing dt is taken from t; a t that goes backwards (a seek, a replay) forgets the steps and pulls.
//
// Output f (the same object every frame; f.voices, f.colour, f.dance, f.events and f.raw keep their identity too):
//   f.voices = { count, bass, top, solo, spread }
//     count   how many notes sound.
//     bass    the lowest sounding note (midi), or null in silence. top: the highest, or null.
//     solo    the melody voice: the highest note struck in the last soloWindow seconds that is not part of the chord block
//             (its strike more than blockGap from the block's), preferring notes a finger still holds; else top. The chord
//             block is the group of notes struck together with the bass when that group has blockMin notes or more, else the
//             biggest such group (the latest on a tie), else there is none (two voices moving together are two voices).
//     spread  top - bass in semitones (0 in silence).
//   f.colour = { simplicity, lushness, tension, brightness, openness }, each 0..1 and smoothed
//     simplicity  1 for one note, an octave or a power chord; about 0.8 for a plain triad; lower as pitch classes are added,
//                 lower still for a shape that holds no chord at all (a cluster; a triad, a sus shape and a seventh-chord
//                 shell all count as chords, so a C13 reads simpler than three notes a semitone apart) and for tension.
//                 The fall is a tendency, not a strict law: a note that completes a chord shape (the 5th over a rootless
//                 shell, the 3rd over a bare fifth) can lift simplicity a little, because a shape that holds a chord earns
//                 back part of what the extra pitch class costs.
//     lushness    how much colour the chord carries: maj7, 6/13, 9, 11 and #11 weigh most, a b7 a little. A wide voicing and
//                 pedal-held voices raise it. Altered tones count toward tension, not here. A plain triad is never lush: a
//                 triad and a power chord are both exactly 0, deliberately -- the 3rd carries no colour weight of its own --
//                 and it is simplicity and openness, not lushness, that tell those two apart.
//     tension     how rough it sounds: minor 2nds and major 7ths and the tritone weigh most, major 2nds and minor 7ths a
//                 little (a pair that really sounds a step apart weighs more than the same pitch classes spread wider), plus
//                 the altered tones (b9, #9, b13, the #5 of a 7#5) and a diminished or augmented quality.
//     brightness  0.5 is neutral. A major 3rd over the root and a #11 (Lydian) lift it, a maj7 a little; a minor 3rd, a b6 or
//                 b13, a b9 and a #9 darken it. A high register lifts it slightly, a low one darkens it slightly.
//     openness    the share of neighbouring voices a 4th, 5th or octave apart (compound ones too), plus how far the voicing
//                 spreads across the keyboard.
//   f.dance = { interval, family, consonance, motion, pull, stretch, phase }: the bass and the solo as a couple
//     interval    semitones from bass to solo (0 for one voice or silence).
//     family      harmony-model.js intervalFamily of it: "octave", "third", "fifth" or "tension".
//     consonance  0..1 (smoothed): how sweetly bass and solo agree (octave 1, 5th 0.95 ... minor 2nd 0.05; a compound interval,
//                 an octave or more apart, is gentler).
//     motion      "contrary" (one up, one down), "similar" (both the same way, by different steps), "parallel" (both by the
//                 same step: parallel octaves, 5ths ... a lone line moving is parallel with itself), "oblique" (one moves,
//                 the other holds), or "static" (nothing has stepped for motionHold seconds, or silence). A bass step and a
//                 solo step count as one move when they land within motionWindow of each other.
//     pull        0..1 (smoothed): how fast bass and solo are closing in or pulling apart (the interval's change per second).
//     stretch     0..1 (smoothed): the register distance between them, over 0..stretchFull semitones.
//     phase       0..1, cyclic and smooth: every voice step turns it a little, contrary motion one way and similar or parallel
//                 motion the other (oblique half a turn step forward). For animation: a slow rotation, a sway, a swirl.
//   f.events = { chordChanged, bassMoved, soloMoved }: true only on the frame it happens.
//     chordChanged  a new chord name, different from the last one (a return to the same chord after silence is no change).
//                   A host with no state.chord at all: a new set of three or more sounding pitch classes.
//     bassMoved     the bass is a different note than the last bass (a first note, or the first after a rest longer than
//                   motionHold, is no move). soloMoved: the same for the solo.
//   f.raw = { voices, colour, dance }: the same numbers unsmoothed (raw.voices is f.voices; raw.dance.phase is where the
//           smoothed phase is heading).
//
// Smoothing: exponential and frame-rate independent (it uses dt): a value moving away from its resting value eases with the
// attack time, one returning toward rest with the release time, so a new chord arrives quickly and fades slowly. Each frame
// eases toward the reading that was in force over the frame that just passed and then takes its new reading, so the same
// playing gives the same curve at 30 and at 144 frames a second (an exponential composes exactly over any step). In silence
// every value returns to rest: simplicity 1, lushness 0, tension 0, brightness 0.5, openness 0, consonance 1, pull 0,
// stretch 0. The phase keeps its place. Whole numbers and words (count, bass, top, solo, spread, interval, family, motion,
// the event flags) are never smoothed: f gives them as they are now.
//
// Constants (FEEL; any of them may be overridden by name in createHarmonyFeel's options):
//   attack 0.12 s             time constant of a value moving away from rest (a new colour arriving)
//   release 0.6 s             time constant of a value returning to rest (a colour fading, silence)
//   maxDt 0.5 s               the longest frame step used (a stalled tab does not jump the phase)
//   soloWindow 1.5 s          a note struck longer ago than this is no longer a melody candidate
//   blockGap 0.06 s           strikes this close together belong to the same group (a chord struck at once)
//   blockMin 3                notes a group needs to count as the chord block
//   sustainForget 12 s        a note only the pedal holds stops counting this long after its strike (a long pedal wash
//                             would otherwise colour everything forever)
//   motionWindow 0.3 s        a bass step and a solo step this close in time are one move of the couple
//   motionHold 1.5 s          motion reads "static" after this long without a step; a rest this long forgets the last bass
//                             and solo, so the next phrase starts fresh
//   pullTau 0.6 s             how long a move keeps pulling (the decay of the interval-change accumulator)
//   pullFull 8 semitones      interval change within about pullTau that reads as full pull
//   stretchFull 60 semitones  bass-to-solo distance that reads as full stretch (five octaves)
//   phaseStep 0.0625          how far one voice step turns the phase (1/16 of a cycle)
//   phaseTau 0.25 s           how quickly the shown phase follows its target
//   roughSemitoneClose 2.0    tension weight of a minor 2nd that really sounds a semitone apart (a cluster)
//   roughSemitoneWide 0.5     the same pitch classes only further apart (a major 7th, a minor 9th)
//   roughTritone 0.8          a tritone (augmented 4th, diminished 5th)
//   roughToneClose 0.5        a major 2nd that really sounds a whole step apart
//   roughToneWide 0.2         the same pitch classes only further apart (a minor 7th, a 9th)
//   tensionAltered 1.0        each altered tone: b9, #9, b13, the #5 of a 7#5, the b5 of a 7b5
//   tensionDim 0.8            a diminished quality (dim, dim7, m7b5)
//   tensionAug 0.6            an augmented quality (aug, 7#5, maj7#5)
//   tensionScale 3.0          tension = 1 - exp(-score / tensionScale): the score at which tension reads about 0.63
//   simpleDyadThird 0.1       simplicity cost of two pitch classes a 3rd or 6th apart (a 4th or 5th costs nothing)
//   simpleDyadStep 0.2        two pitch classes a 2nd or 7th apart (major)
//   simpleDyadRough 0.25      two pitch classes a semitone or a tritone apart
//   simpleTriad 0.2           a three pitch class chord
//   simplePerPc 0.14          each pitch class beyond three
//   simpleNonTriad 0.15       extra cost for three or more pitch classes that hold no triad or sus shape (a cluster)
//   simpleTension 0.6         how much tension takes off: simplicity = (1 - cost) * (1 - simpleTension * tension)
//   simpleMaxCost 0.95        the most the pitch-class cost can take
//   lushMaj7 0.5              lushness weight of a major 7th
//   lushSix 0.45              a 6th or 13th
//   lushNine 0.45             a 9th (add9)
//   lushEleven 0.35           an 11th over a 3rd (a sus4 is shape, not colour)
//   lushSharp11 0.5           a #11
//   lushFlat7 0.15            a minor 7th
//   lushScale 1.0             lushness = 1 - exp(-weights / lushScale), before the voicing boosts
//   lushSpreadFrom 12         voicings wider than this many semitones start to boost lushness
//   lushSpreadOver 24         ... reaching the full boost this many semitones further (three octaves in all)
//   lushSpreadBoost 0.35      the full spread boost (x1.35)
//   lushPedalFull 6           pedal-held voices that give the full pedal boost
//   lushPedalBoost 0.25       the full pedal boost (x1.25)
//   brightMajor3 0.2          brightness lift of a major 3rd over the root
//   brightSharp11 0.15        lift of a #11 (Lydian)
//   brightMaj7 0.05           lift of a major 7th
//   brightMinor3 0.2          darkening of a minor 3rd
//   brightFlat6 0.1           darkening of a b6 or b13
//   brightFlat9 0.1           darkening of a b9
//   brightSharp9 0.06         darkening of a #9
//   brightRegister 0.06       the most the register tilts brightness ...
//   brightRegisterSpan 24     ... reached this many semitones above or below middle C (the average sounding pitch)
//   openShareWeight 0.65      openness = openShareWeight * open share + openSpreadWeight * spread
//   openSpreadWeight 0.35
//   openSpreadFull 36         a spread of this many semitones (three octaves) is fully open
//   consonanceCompound 0.25   a compound interval (an octave or more) closes this share of its gap to full consonance
//   CONSONANCE                consonance of bass to solo by interval class: unison/octave 1, m2 0.05, M2 0.35, m3 0.75,
//                             M3 0.8, P4 0.8, tritone 0.2, P5 0.95, m6 0.65, M6 0.75, m7 0.4, M7 0.15
import { intervalFamily, pc, pitchClass } from "./harmony-model.js";
import { parseSuffix } from "./chordread.js";
import { parseChord } from "./nashville.js";

export const HARMONY_FEEL_API = "arsenal.piano.harmony-feel/v1";

export const FEEL = Object.freeze({
  attack: 0.12, release: 0.6, maxDt: 0.5,
  soloWindow: 1.5, blockGap: 0.06, blockMin: 3, sustainForget: 12,
  motionWindow: 0.3, motionHold: 1.5, pullTau: 0.6, pullFull: 8, stretchFull: 60, phaseStep: 1 / 16, phaseTau: 0.25,
  roughSemitoneClose: 2.0, roughSemitoneWide: 0.5, roughTritone: 0.8, roughToneClose: 0.5, roughToneWide: 0.2,
  tensionAltered: 1.0, tensionDim: 0.8, tensionAug: 0.6, tensionScale: 3.0,
  simpleDyadThird: 0.1, simpleDyadStep: 0.2, simpleDyadRough: 0.25, simpleTriad: 0.2, simplePerPc: 0.14, simpleNonTriad: 0.15,
  simpleTension: 0.6, simpleMaxCost: 0.95,
  lushMaj7: 0.5, lushSix: 0.45, lushNine: 0.45, lushEleven: 0.35, lushSharp11: 0.5, lushFlat7: 0.15, lushScale: 1.0,
  lushSpreadFrom: 12, lushSpreadOver: 24, lushSpreadBoost: 0.35, lushPedalFull: 6, lushPedalBoost: 0.25,
  brightMajor3: 0.2, brightSharp11: 0.15, brightMaj7: 0.05, brightMinor3: 0.2, brightFlat6: 0.1, brightFlat9: 0.1,
  brightSharp9: 0.06, brightRegister: 0.06, brightRegisterSpan: 24,
  openShareWeight: 0.65, openSpreadWeight: 0.35, openSpreadFull: 36,
  consonanceCompound: 0.25,
});
export const CONSONANCE = Object.freeze([1.0, 0.05, 0.35, 0.75, 0.8, 0.8, 0.2, 0.95, 0.65, 0.75, 0.4, 0.15]);
const CONSONANCE_F = new Float64Array(CONSONANCE);  // the hot path reads it from here: a plain array hands back a boxed number
export const REST = Object.freeze({ simplicity: 1, lushness: 0, tension: 0, brightness: 0.5, openness: 0, consonance: 1, pull: 0,
  stretch: 0 });

// ------------------------------------------------------------------------------------------------ tables --
const FAMILY_OF = Object.freeze(Array.from({ length: 12 }, (_, i) => intervalFamily(i)));  // intervalFamily reads the class only
const POP = new Uint8Array(4096);                                                          // set bits of a 12-bit mask
for (let i = 1; i < 4096; i++) POP[i] = POP[i >> 1] + (i & 1);
const rot = (mask, p) => ((mask >>> p) | (mask << (12 - p))) & 0xFFF;                     // the mask, relative to pitch class p
const bit = (mask, k) => (mask >>> k) & 1;
const THIRDS = (1 << 3) | (1 << 4), FIFTH = 1 << 7, SEVENTHS = (1 << 10) | (1 << 11), FLAT6 = 1 << 8;
const Q_DIM = 1, Q_DIM7 = 2, Q_AUG = 4, Q_B5 = 8;
const DIM_BASES = new Set(["dim", "dim7", "m7b5"]), AUG_BASES = new Set(["aug", "7#5", "maj7#5"]);
const MOTION_DIR = { contrary: 1, oblique: 0.5, similar: -1, parallel: -1, static: 0 };

// Chord names, parsed once each by the house readers and shared by every instance (a chord change parses, a frame never does).
const BAD_NAME = Object.freeze({ ok: false, root: 0, tones: 0, tens: 0, q: 0, bass: -1 });
const nameCache = new Map();
const NAME_CACHE_MAX = 512;
function readName(name) {
  const hit = nameCache.get(name);
  if (hit !== undefined) return hit;
  let rec = BAD_NAME;
  try {
    const p = parseChord(name);
    if (p && p.kind === "chord" && p.root) {
      const s = parseSuffix(p.suffix);
      let tones = 0, tens = 0, q = 0;
      for (const k of Object.keys(s.tones)) tones |= 1 << pc(Number(k));
      for (const x of s.tensions) tens |= 1 << pc(x);
      if (DIM_BASES.has(s.base)) q |= Q_DIM;
      if (s.base === "dim7") q |= Q_DIM7;
      if (AUG_BASES.has(s.base)) q |= Q_AUG;
      if (s.base === "7b5") q |= Q_B5;
      rec = Object.freeze({ ok: true, root: pitchClass(p.root), tones: tones & ~tens, tens, q, bass: p.bass ? pitchClass(p.bass) : -1 });
    }
  } catch { rec = BAD_NAME; }
  if (nameCache.size >= NAME_CACHE_MAX) nameCache.clear();
  nameCache.set(name, rec);
  return rec;
}

// ---------------------------------------------------------------------------------------------- the feel --
export function createHarmonyFeel(options = {}) {
  const K = { ...FEEL };
  for (const key of Object.keys(FEEL)) if (options && typeof options[key] === "number" && Number.isFinite(options[key])) K[key] = options[key];

  // The one frame object. Every number that is not always a whole number starts as a fraction, so the engine gives the field a
  // double slot from birth and every later frame writes it in place (reset() puts the resting values in before anyone sees them).
  const f = {
    voices: { count: 0, bass: null, top: null, solo: null, spread: 0 },
    colour: { simplicity: 1.5, lushness: 0.5, tension: 0.5, brightness: 0.5, openness: 0.5 },
    dance: { interval: 0, family: FAMILY_OF[0], consonance: 1.5, motion: "static", pull: 0.5, stretch: 0.5, phase: 0.5 },
    events: { chordChanged: false, bassMoved: false, soloMoved: false },
    raw: null,
  };
  f.raw = {
    voices: f.voices,
    colour: { simplicity: 1.5, lushness: 0.5, tension: 0.5, brightness: 0.5, openness: 0.5 },
    dance: { interval: 0, family: FAMILY_OF[0], consonance: 1.5, motion: "static", pull: 0.5, stretch: 0.5, phase: 0.5 },
  };

  // Per-frame scratch, gathered from the host's Map (typed arrays: nothing boxed, nothing allocated).
  const midis = new Int16Array(128), onsets = new Float64Array(128), helds = new Uint8Array(128), present = new Uint8Array(131);
  let count = 0, low = 128, high = -1, lowIdx = -1, pedalVoices = 0, mask = 0, midiSum = 0;
  // Doubles that live across frames sit in N (a closure variable holding a double would box a new number on every write).
  const N = new Float64Array(8);
  const LAST_T = 0, NOW = 1, BASS_STEP_T = 2, SOLO_STEP_T = 3, PULL = 4, PHASE_T = 5, PHASE_S = 6, SILENT_AT = 7;
  let lastBass = -1, lastSolo = -1, bassStepD = 0, soloStepD = 0, hadVoices = false, lastInterval = 0, silent = true, started = false;
  let lastChordName = null, lastChordMask = -1, infoName = null, info = BAD_NAME;

  function visit(e, key) {
    const m = key | 0;
    if (m !== key || m < 0 || m > 127 || present[m] === 1 || !e || count >= 128) return;
    const held = e.held !== false;
    const t0 = typeof e.t0 === "number" && e.t0 === e.t0 ? e.t0 : -1e9;  // no strike time: an old note
    if (!held && N[NOW] - t0 > K.sustainForget) return;
    present[m] = 1; midis[count] = m; onsets[count] = t0; helds[count] = held ? 1 : 0;
    if (!held || e.pedal === true) pedalVoices++;
    if (m < low) { low = m; lowIdx = count; }
    if (m > high) high = m;
    mask |= 1 << (m % 12);
    midiSum += m;
    count++;
  }

  // The melody voice. It reads the frame's time from N (a double passed as an argument would be boxed on every frame).
  function pickSolo() {
    const t = N[NOW], gap = K.blockGap, need = K.blockMin;
    let hasAnchor = false, anchor = 0;
    const bassOnset = onsets[lowIdx];
    let c = 0;
    for (let j = 0; j < count; j++) if (Math.abs(onsets[j] - bassOnset) <= gap) c++;
    if (c >= need) { hasAnchor = true; anchor = bassOnset; }
    else {
      let best = 0;
      for (let i = 0; i < count; i++) {
        const oi = onsets[i];
        let ci = 0;
        for (let j = 0; j < count; j++) if (Math.abs(onsets[j] - oi) <= gap) ci++;
        if (ci >= need && (ci > best || (ci === best && oi > anchor))) { best = ci; anchor = oi; hasAnchor = true; }
      }
    }
    let heldBest = -1, latest = -Infinity;
    for (let i = 0; i < count; i++) {
      const o = onsets[i];
      if (i === lowIdx || t - o > K.soloWindow || (hasAnchor && Math.abs(o - anchor) <= gap)) continue;
      if (helds[i] === 1 && midis[i] > heldBest) heldBest = midis[i];
      if (o > latest) latest = o;
    }
    if (heldBest >= 0) return heldBest;
    if (latest === -Infinity) return high;
    let best = -1;
    for (let i = 0; i < count; i++) {
      const o = onsets[i];
      if (i === lowIdx || t - o > K.soloWindow || (hasAnchor && Math.abs(o - anchor) <= gap) || o < latest - gap) continue;
      if (midis[i] > best) best = midis[i];
    }
    return best >= 0 ? best : high;
  }

  // Eases v toward x: attack while moving away from rest, release while returning to it (kA, kR: this frame's decay factors).
  function ease(v, x, rest, kA, kR) {
    const a = x - rest, b = v - rest;
    return x + (v - x) * (a * a > b * b || a * b < 0 ? kA : kR);
  }

  function forgetHistory() {
    lastBass = -1; lastSolo = -1; bassStepD = 0; soloStepD = 0; hadVoices = false; lastInterval = 0;
    N[BASS_STEP_T] = -1e9; N[SOLO_STEP_T] = -1e9; N[PULL] = 0;
    lastChordName = null; lastChordMask = -1;
  }

  function reset() {
    forgetHistory();
    N[PHASE_T] = 0; N[PHASE_S] = 0; N[LAST_T] = 0; N[SILENT_AT] = 0; silent = true; started = false;
    infoName = null; info = BAD_NAME;
    const C = f.colour, D = f.dance, R = f.raw.colour, RD = f.raw.dance, V = f.voices, E = f.events;
    C.simplicity = R.simplicity = REST.simplicity; C.lushness = R.lushness = REST.lushness; C.tension = R.tension = REST.tension;
    C.brightness = R.brightness = REST.brightness; C.openness = R.openness = REST.openness;
    D.consonance = RD.consonance = REST.consonance; D.pull = RD.pull = REST.pull; D.stretch = RD.stretch = REST.stretch;
    D.phase = RD.phase = 0; D.interval = RD.interval = 0; D.family = RD.family = FAMILY_OF[0]; D.motion = RD.motion = "static";
    V.count = 0; V.bass = null; V.top = null; V.solo = null; V.spread = 0;
    E.chordChanged = false; E.bassMoved = false; E.soloMoved = false;
  }

  function update(state, dt, t) {
    if (typeof t !== "number" || t !== t) t = N[LAST_T] + (typeof dt === "number" && dt > 0 ? dt : 0);
    if (typeof dt !== "number" || !(dt >= 0)) dt = started ? t - N[LAST_T] : 0;
    if (!(dt > 0)) dt = 0; else if (dt > K.maxDt) dt = K.maxDt;
    if (started && t < N[LAST_T] - 1e-6) forgetHistory();  // the clock went back (a seek, a replay): steps and pulls start fresh
    started = true;
    N[LAST_T] = t; N[NOW] = t;
    const E = f.events, V = f.voices, RC = f.raw.colour, RD = f.raw.dance, C = f.colour, D = f.dance;
    E.chordChanged = false; E.bassMoved = false; E.soloMoved = false;

    // ---- smoothing, before this frame's reading: it eases toward the reading that was in force over the frame that just
    // passed (RC and RD still hold it), so a new chord starts easing from the frame it arrives on. That is what makes the
    // curve the same at 30 and at 144 frames a second: the exponential composes exactly over whatever steps the host takes.
    const kA = Math.exp(-dt / K.attack), kR = Math.exp(-dt / K.release);
    C.simplicity = ease(C.simplicity, RC.simplicity, REST.simplicity, kA, kR);
    C.lushness = ease(C.lushness, RC.lushness, REST.lushness, kA, kR);
    C.tension = ease(C.tension, RC.tension, REST.tension, kA, kR);
    C.brightness = ease(C.brightness, RC.brightness, REST.brightness, kA, kR);
    C.openness = ease(C.openness, RC.openness, REST.openness, kA, kR);
    D.consonance = ease(D.consonance, RD.consonance, REST.consonance, kA, kR);
    D.pull = ease(D.pull, RD.pull, REST.pull, kA, kR);
    D.stretch = ease(D.stretch, RD.stretch, REST.stretch, kA, kR);
    const shift = Math.floor(N[PHASE_S]);  // keep both phases near zero; the fraction is what shows
    if (shift !== 0) { N[PHASE_S] -= shift; N[PHASE_T] -= shift; }
    N[PHASE_S] = N[PHASE_T] + (N[PHASE_S] - N[PHASE_T]) * Math.exp(-dt / K.phaseTau);
    D.phase = N[PHASE_S] - Math.floor(N[PHASE_S]);

    // ---- gather
    count = 0; low = 128; high = -1; lowIdx = -1; pedalVoices = 0; mask = 0; midiSum = 0;
    const src = state ? (state.sounding || state.pressed) : null;
    if (src && typeof src.forEach === "function") src.forEach(visit);

    // ---- voices
    let bass = -1, top = -1, solo = -1;
    if (count > 0) { bass = low; top = high; solo = pickSolo(); }
    V.count = count; V.bass = count > 0 ? bass : null; V.top = count > 0 ? top : null; V.solo = count > 0 ? solo : null;
    const spread = count > 0 ? top - bass : 0;
    V.spread = spread;

    // ---- the voicing: open neighbours, and which pitch-class pairs really sound a step apart
    let semiClose = 0, toneClose = 0, openN = 0, ivN = 0;
    if (count > 1) {
      let prev = bass;
      for (let m = bass + 1; m <= top; m++) {
        if (present[m] !== 1) continue;
        const d = m - prev, r = d % 12;
        if (d >= 5 && (r === 0 || r === 5 || r === 7)) openN++;
        ivN++; prev = m;
      }
      for (let i = 0; i < count; i++) {
        const m = midis[i];
        if (present[m + 1] === 1) semiClose |= 1 << (m % 12);
        if (present[m + 2] === 1) toneClose |= 1 << (m % 12);
      }
    }
    for (let i = 0; i < count; i++) present[midis[i]] = 0;

    // ---- the chord name (parsed once per name), and chordChanged
    const chord = state ? state.chord : undefined;
    const name = chord && typeof chord.name === "string" && chord.name !== "" ? chord.name : null;
    if (name !== infoName) { infoName = name; info = name === null ? BAD_NAME : readName(name); }
    if (name !== null) {
      if (name !== lastChordName) { E.chordChanged = true; lastChordName = name; }
    } else if (chord === undefined && count > 0 && POP[mask] >= 3 && mask !== lastChordMask) {
      E.chordChanged = true; lastChordMask = mask;
    }

    // ---- colour
    if (count > 0) {
      // the root and the tones relative to it
      let root = 0, rel = 0, useName = false, nameAll = 0, nameTones = 0, q = 0;
      if (info.ok) {
        const r = rot(mask, info.root);
        const all = info.tones | info.tens;
        const bassPc = bass % 12;
        // Trusted while it covers what sounds: at most one sounding pitch class outside its tones, and the bass is one of its
        // tones or the bass it names. A name left over from the chord before ("Am" while F A C F sounds) fails both halves.
        if (POP[r & ~all & 0xFFF] <= 1 && (bit(all, (bassPc - info.root + 12) % 12) === 1 || bassPc === info.bass)) {
          useName = true; root = info.root; rel = r; nameAll = all; nameTones = info.tones; q = info.q;
        }
      }
      if (!useName) {
        root = bass % 12; rel = rot(mask, root);
        // The bass keeps the root while it plainly roots what sounds: a 3rd with a 7th above it (a seventh-chord shell: the
        // 5th is the first note a voicing drops, so C13 without its G is still a C), or a 3rd with a 5th and no b6. A b6 with
        // no 7th is the mark of an inversion rather than a chord tone (E G C, A C E F), so it sends the hunt out as well.
        const shell = (rel & THIRDS) && (rel & SEVENTHS);
        if (!(shell || ((rel & THIRDS) && (rel & FIFTH) && !(rel & FLAT6)))) {
          for (let k = 1; k < 12; k++) {
            const p = (root + k) % 12;
            if (!bit(mask, p)) continue;
            const r = rot(mask, p);
            if ((r & THIRDS) && (r & FIFTH)) { root = p; rel = r; break; }
          }
        }
      }
      const h1 = bit(rel, 1), h2 = bit(rel, 2), h3 = bit(rel, 3), h4 = bit(rel, 4), h5 = bit(rel, 5), h6 = bit(rel, 6);
      const h7 = bit(rel, 7), h8 = bit(rel, 8), h9 = bit(rel, 9), h10 = bit(rel, 10), h11 = bit(rel, 11);
      // nameAll is 0 unless the name is trusted, so "the name says something about this tone" is one bit test.
      const major3 = h4;
      let minor3 = 0, sharp9 = 0;
      if (h3) {
        if (bit(nameAll, 3)) { if (bit(nameTones, 3)) minor3 = 1; else sharp9 = 1; }
        else if (h4) sharp9 = 1; else minor3 = 1;
      }
      const third = major3 | minor3, flat9 = h1;
      let nine = 0, eleven = 0, sharp11 = 0, flat5 = 0, sharp5 = 0, flat6 = 0, six = 0;
      if (h2) nine = bit(nameAll, 2) ? 1 - bit(nameTones, 2) : (third || !h7 ? 1 : 0);
      if (h5) eleven = bit(nameAll, 5) ? 1 - bit(nameTones, 5) : third;
      if (h6) {
        if (bit(nameAll, 6)) { if (bit(nameTones, 6)) flat5 = 1; else sharp11 = 1; }
        else if (h7 || (major3 && !minor3)) sharp11 = 1;
        else if (minor3) flat5 = 1;
      }
      if (h8) {
        if (bit(nameAll, 8)) { if (bit(nameTones, 8)) sharp5 = 1; else flat6 = 1; }
        else if (major3 && !h7) sharp5 = 1;
        else flat6 = 1;
      }
      if (h9) six = bit(nameAll, 9) ? ((q & Q_DIM7) ? 0 : 1) : (minor3 && h6 && !h7 ? 0 : 1);
      const dimQ = useName ? ((q & Q_DIM) ? 1 : 0) : (minor3 && flat5 && !h7 ? 1 : 0);
      const augQ = useName ? ((q & Q_AUG) ? 1 : 0) : sharp5;
      const flat13Altered = flat6 && (bit(nameAll, 8) || !minor3) ? 1 : 0;
      const altered = flat9 + sharp9 + flat13Altered + (sharp5 && h10 ? 1 : 0) + ((q & Q_B5) && flat5 ? 1 : 0);

      // tension: roughness of every sounding pitch-class pair, altered tones, quality
      let rough = 0;
      for (let a = 0; a < 12; a++) {
        if (!bit(mask, a)) continue;
        for (let b = a + 1; b < 12; b++) {
          if (!bit(mask, b)) continue;
          const d = b - a;
          if (d === 1) rough += bit(semiClose, a) ? K.roughSemitoneClose : K.roughSemitoneWide;
          else if (d === 11) rough += bit(semiClose, b) ? K.roughSemitoneClose : K.roughSemitoneWide;
          else if (d === 2) rough += bit(toneClose, a) ? K.roughToneClose : K.roughToneWide;
          else if (d === 10) rough += bit(toneClose, b) ? K.roughToneClose : K.roughToneWide;
          else if (d === 6) rough += K.roughTritone;
        }
      }
      const tensionScore = rough + K.tensionAltered * altered + K.tensionDim * dimQ + K.tensionAug * augQ;
      const tension = 1 - Math.exp(-tensionScore / K.tensionScale);

      // simplicity
      const pcs = POP[mask];
      let cost = 0;
      if (pcs === 2) {
        const lo = 31 - Math.clz32(mask & -mask), hi = 31 - Math.clz32(mask), d = hi - lo, ic = d > 6 ? 12 - d : d;
        cost = ic === 5 ? 0 : ic === 3 || ic === 4 ? K.simpleDyadThird : ic === 2 ? K.simpleDyadStep : K.simpleDyadRough;
      } else if (pcs >= 3) {
        // A 3rd with a 5th, a 6th or a #5 above the root is a triad; a 3rd with a 7th is a seventh-chord shell, which is a
        // chord shape too (a C13 is not a cluster), so it pays no simpleNonTriad either. A sus shape needs its 5th.
        const triadic = ((h3 | h4) && (h6 | h7 | h8 | h10 | h11)) || ((h2 | h5) && h7);
        cost = K.simpleTriad + (pcs - 3) * K.simplePerPc + (triadic ? 0 : K.simpleNonTriad);
        if (cost > K.simpleMaxCost) cost = K.simpleMaxCost;
      }
      const simplicity = (1 - cost) * (1 - K.simpleTension * tension);

      // lushness
      const colourWeight = h11 * K.lushMaj7 + six * K.lushSix + nine * K.lushNine + eleven * K.lushEleven
        + sharp11 * K.lushSharp11 + h10 * K.lushFlat7;
      let spreadT = (spread - K.lushSpreadFrom) / K.lushSpreadOver;
      spreadT = spreadT < 0 ? 0 : spreadT > 1 ? 1 : spreadT;
      const pedalT = pedalVoices >= K.lushPedalFull ? 1 : pedalVoices / K.lushPedalFull;
      let lushness = (1 - Math.exp(-colourWeight / K.lushScale)) * (1 + K.lushSpreadBoost * spreadT) * (1 + K.lushPedalBoost * pedalT);
      if (lushness > 1) lushness = 1;

      // brightness
      let register = (midiSum / count - 60) / K.brightRegisterSpan;
      register = register < -1 ? -1 : register > 1 ? 1 : register;
      let brightness = 0.5 + major3 * K.brightMajor3 + sharp11 * K.brightSharp11 + h11 * K.brightMaj7 - minor3 * K.brightMinor3
        - flat6 * K.brightFlat6 - flat9 * K.brightFlat9 - sharp9 * K.brightSharp9 + register * K.brightRegister;
      brightness = brightness < 0 ? 0 : brightness > 1 ? 1 : brightness;

      // openness
      const share = ivN > 0 ? openN / ivN : 1;
      const spreadOpen = spread >= K.openSpreadFull ? 1 : spread / K.openSpreadFull;
      const openness = K.openShareWeight * share + K.openSpreadWeight * spreadOpen;

      RC.simplicity = simplicity; RC.lushness = lushness; RC.tension = tension; RC.brightness = brightness; RC.openness = openness;
    } else {
      RC.simplicity = REST.simplicity; RC.lushness = REST.lushness; RC.tension = REST.tension;
      RC.brightness = REST.brightness; RC.openness = REST.openness;
    }

    // ---- the dance: steps, motion, pull, phase
    if (count === 0) {
      if (!silent) { silent = true; N[SILENT_AT] = t; }
      else if (t - N[SILENT_AT] > K.motionHold) { lastBass = -1; lastSolo = -1; }
      hadVoices = false;
    } else {
      silent = false;
      if (lastBass >= 0 && bass !== lastBass) { E.bassMoved = true; bassStepD = bass - lastBass; N[BASS_STEP_T] = t; }
      if (lastSolo >= 0 && solo !== lastSolo) { E.soloMoved = true; soloStepD = solo - lastSolo; N[SOLO_STEP_T] = t; }
      lastBass = bass; lastSolo = solo;
    }
    let motion = "static";
    if (count > 0) {
      const bRecent = t - N[BASS_STEP_T] <= K.motionHold, sRecent = t - N[SOLO_STEP_T] <= K.motionHold;
      if (bRecent && sRecent && Math.abs(N[BASS_STEP_T] - N[SOLO_STEP_T]) <= K.motionWindow) {
        motion = (bassStepD > 0) !== (soloStepD > 0) ? "contrary" : bassStepD === soloStepD ? "parallel" : "similar";
      } else if (bRecent || sRecent) motion = "oblique";
    }
    const steps = (E.bassMoved ? 1 : 0) + (E.soloMoved ? 1 : 0);
    if (steps > 0) N[PHASE_T] += steps * K.phaseStep * MOTION_DIR[motion];

    const interval = count > 0 ? solo - bass : 0;
    N[PULL] *= Math.exp(-dt / K.pullTau);
    if (count > 0 && hadVoices && interval !== lastInterval) N[PULL] += Math.abs(interval - lastInterval);
    if (count > 0) { hadVoices = true; lastInterval = interval; }

    const ic = interval % 12;
    let consonance = CONSONANCE_F[ic];
    if (interval >= 12) consonance += (1 - consonance) * K.consonanceCompound;
    if (count === 0) consonance = CONSONANCE_F[0];
    const pull = N[PULL] >= K.pullFull ? 1 : N[PULL] / K.pullFull;
    const stretch = interval >= K.stretchFull ? 1 : interval / K.stretchFull;

    RD.interval = interval; RD.family = FAMILY_OF[ic]; RD.motion = motion;
    RD.consonance = consonance; RD.pull = pull; RD.stretch = stretch;
    RD.phase = N[PHASE_T] - Math.floor(N[PHASE_T]);
    D.interval = interval; D.family = FAMILY_OF[ic]; D.motion = motion;  // whole numbers and words: never smoothed
    return f;
  }

  reset();
  return { update, reset, frame: f, constants: Object.freeze(K) };
}
