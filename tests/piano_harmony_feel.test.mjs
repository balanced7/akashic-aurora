// Node tests for the harmony feel (arsenal/web/piano/harmony-feel.js): the numbers the "Instruments of light" round hangs its
// colour, bloom and motion on. Zero dependencies, synthetic host states only:
//   node tests/piano_harmony_feel.test.mjs           everything, the cost and allocation measurements included
//   node tests/piano_harmony_feel.test.mjs --quick   without them
// Sections: the shape of the reading (the frozen output objects, one object refreshed in place, every constant documented);
// the colour of named and unnamed chords (a power chord, a triad, a wide maj9#11, an altered dominant, a minor triad, a
// cluster, and the chords between them); the voices (bass, top, the melody voice over a held chord, an older host's
// state.pressed); the dance (contrary, parallel, oblique, static, pull, phase); the smoothing (attack and release, the same
// answer at 30 and at 144 frames a second, silence decaying to rest); the event flags; and the frame budget (cost per
// update, and nothing allocated once it is warm).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { PerformanceObserver } from "node:perf_hooks";
import v8 from "node:v8";
import vm from "node:vm";
import { createHarmonyFeel, FEEL, CONSONANCE, REST, HARMONY_FEEL_API } from "../arsenal/web/piano/harmony-feel.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const quick = process.argv.includes("--quick");
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const near = (a, b, eps = 1e-9) => Math.abs(a - b) <= eps;
const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
function midiOf(tok) {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(tok);
  if (!m) throw new Error(`bad note ${tok}`);
  return (Number(m[3]) + 1) * 12 + LETTER_PC["CDEFGAB".indexOf(m[1])] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0);
}
const notes = (text) => text.trim().split(/\s+/).map(midiOf);
const entry = (t0, held = true, pedal = false) => ({ vel: 80, t0, held, pedal, tRelease: held ? 0 : t0, strike: 1 });

// Plays a script of note events against one feel and keeps every frame's reading.
// script: [{ t, on: "C4 E4", off: "E4", lift: "C4" (finger up, the pedal holds it), chord: "C" | null, pedalDown: true }]
// opts: fps, options (createHarmonyFeel options), pressed (an older host: state.pressed and entries with no held flag),
//       noChordField (a host with no state.chord at all), sustainPedal (every strike marked pedal-held).
function play(script, until, opts = {}) {
  const fps = opts.fps || 60;
  const feel = createHarmonyFeel(opts.options);
  const map = new Map();
  const state = opts.pressed ? { pressed: map, pedal: false } : { sounding: map, pedal: false };
  if (!opts.noChordField) state.chord = null;
  const frames = [];
  let k = 0;
  for (let i = 0; i <= Math.round(until * fps); i++) {
    const t = i / fps;
    while (k < script.length && script[k].t <= t + 1e-9) {
      const ev = script[k++];
      for (const m of ev.off ? notes(ev.off) : []) map.delete(m);
      for (const m of ev.on ? notes(ev.on) : []) map.set(m, opts.pressed ? { vel: 80, t0: t } : entry(t, true, !!opts.sustainPedal));
      for (const m of ev.lift ? notes(ev.lift) : []) { const e = map.get(m); if (e) { e.held = false; e.tRelease = t; } }
      if ("chord" in ev) state.chord = ev.chord ? { name: ev.chord, nns: "", key: "" } : null;
      if ("pedalDown" in ev) state.pedal = ev.pedalDown;
    }
    const f = feel.update(state, i === 0 ? 0 : 1 / fps, t);
    frames.push({
      t, i,
      voices: { count: f.voices.count, bass: f.voices.bass, top: f.voices.top, solo: f.voices.solo, spread: f.voices.spread },
      colour: { ...f.colour }, dance: { ...f.dance },
      raw: { colour: { ...f.raw.colour }, dance: { ...f.raw.dance } },
      events: { ...f.events },
    });
  }
  return { frames, feel, state, map, fps, at: (t) => frames[Math.round(t * fps)] };
}
// One chord, held until it has settled: the reading at the end.
function settle(text, chordName = null, secs = 2, opts = {}) {
  const run = play([{ t: 0, on: text, chord: chordName }], secs, opts);
  return run.frames[run.frames.length - 1];
}

// ============================================================================================ the shape of a reading ==
check("HARMONY_FEEL_API", HARMONY_FEEL_API === "arsenal.piano.harmony-feel/v1");
{
  const feel = createHarmonyFeel();
  const f = feel.update({ sounding: new Map(), pedal: false, chord: null }, 0, 0);
  const keys = (o) => Object.keys(o).join(",");
  check("f.voices keys", keys(f.voices) === "count,bass,top,solo,spread", keys(f.voices));
  check("f.colour keys", keys(f.colour) === "simplicity,lushness,tension,brightness,openness", keys(f.colour));
  check("f.dance keys", keys(f.dance) === "interval,family,consonance,motion,pull,stretch,phase", keys(f.dance));
  check("f.events keys", keys(f.events) === "chordChanged,bassMoved,soloMoved", keys(f.events));
  check("f.raw keys", keys(f.raw) === "voices,colour,dance", keys(f.raw));
  check("f.raw.colour keys match f.colour", keys(f.raw.colour) === keys(f.colour));
  check("f.raw.dance keys match f.dance", keys(f.raw.dance) === keys(f.dance));
  check("a new feel sits at rest", f.colour.simplicity === REST.simplicity && f.colour.lushness === REST.lushness
    && f.colour.brightness === REST.brightness && f.dance.consonance === REST.consonance && f.dance.motion === "static");
  check("silence has no voices", f.voices.count === 0 && f.voices.bass === null && f.voices.top === null && f.voices.solo === null);
  check("CONSONANCE covers the twelve interval classes", CONSONANCE.length === 12 && CONSONANCE[0] === 1 && CONSONANCE[7] > CONSONANCE[6]);
}
{  // every constant carries a plain-language line in the module header
  const source = readFileSync(here("../arsenal/web/piano/harmony-feel.js"), "utf8");
  const header = source.slice(0, source.indexOf("\nimport {"));
  const documented = new Set(header.split("\n").map((line) => line.replace(/^\/\/\s*/, "").trim().split(/\s+/)[0]));
  const missing = Object.keys(FEEL).filter((k) => !documented.has(k));
  check("every FEEL constant is documented in the header", missing.length === 0, missing.join(" "));
  check("the header explains every output", ["f.voices", "f.colour", "f.dance", "f.events", "f.raw", "simplicity", "lushness",
    "tension", "brightness", "openness", "interval", "family", "consonance", "motion", "pull", "stretch", "phase"]
    .every((w) => header.includes(w)));
  check("no CRLF in the module", !source.includes("\r"));
}
{  // one object, refreshed in place, through chords, steps and silence
  const feel = createHarmonyFeel();
  const map = new Map([[midiOf("C3"), entry(0)], [midiOf("E3"), entry(0)], [midiOf("G3"), entry(0)]]);
  const state = { sounding: map, pedal: false, chord: { name: "C", nns: "", key: "" } };
  const f0 = feel.update(state, 0, 0);
  const ids = [f0, f0.voices, f0.colour, f0.dance, f0.events, f0.raw, f0.raw.colour, f0.raw.dance];
  let stable = true;
  for (let i = 1; i <= 240; i++) {
    if (i === 60) { map.delete(midiOf("E3")); map.set(midiOf("F3"), entry(i / 60)); state.chord.name = "F"; }
    if (i === 120) { map.clear(); state.chord = null; }
    if (i === 180) { map.set(midiOf("A2"), entry(i / 60)); state.chord = { name: "Am", nns: "", key: "" }; }
    const f = feel.update(state, 1 / 60, i / 60);
    const now = [f, f.voices, f.colour, f.dance, f.events, f.raw, f.raw.colour, f.raw.dance];
    for (let j = 0; j < ids.length; j++) if (now[j] !== ids[j]) stable = false;
  }
  check("update returns the same objects every frame", stable);
  check("f.raw.voices is f.voices (nothing smooths a note number)", f0.raw.voices === f0.voices);
  check("feel.frame is that same object", feel.frame === f0);
}
{  // a host that hands over nothing, or nonsense, is silence and not an exception
  const feel = createHarmonyFeel();
  let threw = null;
  try {
    feel.update(null, 1 / 60, 0);
    feel.update({}, 1 / 60, 1 / 60);
    feel.update({ sounding: null, chord: { name: 42 } }, 1 / 60, 2 / 60);
    feel.update({ sounding: new Map([[200, entry(0)], [-3, entry(0)], [60, null], [61.5, entry(0)]]), chord: null }, 1 / 60, 3 / 60);
  } catch (e) { threw = e; }
  check("a missing or nonsense state reads as silence and never throws", threw === null && feel.frame.voices.count === 0,
    threw ? String(threw.message) : String(feel.frame.voices.count));
  check("an unreadable chord name falls back to the sounding notes", (() => {
    const odd = settle("C4 E4 G4", "not a chord at all").raw.colour, plain = settle("C4 E4 G4", null).raw.colour;
    return near(odd.brightness, plain.brightness) && near(odd.simplicity, plain.simplicity);
  })());
}
{  // options: any constant can be overridden, and the feel says what it is running on
  const slowFeel = createHarmonyFeel({ attack: 0.5 });
  check("createHarmonyFeel reports its constants", slowFeel.constants.attack === 0.5 && slowFeel.constants.release === FEEL.release);
  const map = new Map([[midiOf("C4"), entry(0)], [midiOf("E4"), entry(0)], [midiOf("G4"), entry(0)], [midiOf("B4"), entry(0)]]);
  const state = { sounding: map, pedal: false, chord: { name: "Cmaj7", nns: "", key: "" } };
  const fast = createHarmonyFeel();
  let slowV = 0, fastV = 0;
  for (let i = 0; i <= 12; i++) {
    slowV = slowFeel.update(state, i ? 1 / 60 : 0, i / 60).colour.lushness;
    fastV = fast.update(state, i ? 1 / 60 : 0, i / 60).colour.lushness;
  }
  check("a longer attack arrives more slowly", slowV < fastV * 0.6, `${slowV.toFixed(4)} against ${fastV.toFixed(4)}`);
}

// ======================================================================================================== the colour ==
const power = settle("C3 G3 C4", "C5");
const triad = settle("C4 E4 G4", "C");
const lush = settle("C2 G2 E3 B3 D4 F#4", "Cmaj9#11");
const alt = settle("G2 B3 F4 G#4 A#4 D5", "G7b9#9");
const minor = settle("A3 C4 E4", "Am");
const cluster = settle("C4 C#4 D4", null);
const one = settle("C4", null);
const maj7 = settle("C4 E4 G4 B4", "Cmaj7");
const dim7 = settle("C4 D#4 F#4 A4", "Cdim7");
report.push(`power simp ${power.raw.colour.simplicity.toFixed(2)} open ${power.raw.colour.openness.toFixed(2)} | triad simp `
  + `${triad.raw.colour.simplicity.toFixed(2)} bright ${triad.raw.colour.brightness.toFixed(2)} | maj9#11 lush `
  + `${lush.raw.colour.lushness.toFixed(2)} bright ${lush.raw.colour.brightness.toFixed(2)} | 7b9#9 tens `
  + `${alt.raw.colour.tension.toFixed(2)} | Am bright ${minor.raw.colour.brightness.toFixed(2)} | cluster tens `
  + `${cluster.raw.colour.tension.toFixed(2)} simp ${cluster.raw.colour.simplicity.toFixed(2)}`);

check("power chord: simplicity is full", power.raw.colour.simplicity > 0.95, String(power.raw.colour.simplicity));
check("power chord: nothing lush", power.raw.colour.lushness < 0.05, String(power.raw.colour.lushness));
check("power chord: openness is high", power.raw.colour.openness > 0.6, String(power.raw.colour.openness));
check("power chord: no tension", power.raw.colour.tension < 0.05, String(power.raw.colour.tension));
check("power chord: the smoothed reading has arrived too", power.colour.simplicity > 0.95 && power.colour.openness > 0.6);
check("one note and an octave are as simple as it gets", one.raw.colour.simplicity > 0.99
  && settle("C3 C4", null).raw.colour.simplicity > 0.99);

check("major triad: plainly simple, below a power chord", triad.raw.colour.simplicity > 0.7 && triad.raw.colour.simplicity < 0.9
  && triad.raw.colour.simplicity < power.raw.colour.simplicity, String(triad.raw.colour.simplicity));
check("major triad: bright", triad.raw.colour.brightness > 0.6, String(triad.raw.colour.brightness));
check("major triad: not lush, not tense", triad.raw.colour.lushness < 0.05 && triad.raw.colour.tension < 0.05);
check("major triad, close voicing: not open", triad.raw.colour.openness < 0.25, String(triad.raw.colour.openness));

check("wide Cmaj9#11: lush", lush.raw.colour.lushness > 0.8, String(lush.raw.colour.lushness));
check("wide Cmaj9#11: bright", lush.raw.colour.brightness > 0.75, String(lush.raw.colour.brightness));
check("wide Cmaj9#11: lusher than a plain triad and than a maj7", lush.raw.colour.lushness > maj7.raw.colour.lushness
  && maj7.raw.colour.lushness > triad.raw.colour.lushness);
check("wide Cmaj9#11: far from simple", lush.raw.colour.simplicity < 0.4, String(lush.raw.colour.simplicity));
check("wide Cmaj9#11: the same reading with no chord name (the bass tells the same story)", (() => {
  const noName = settle("C2 G2 E3 B3 D4 F#4", null).raw.colour;
  return near(noName.lushness, lush.raw.colour.lushness) && near(noName.brightness, lush.raw.colour.brightness)
    && near(noName.tension, lush.raw.colour.tension);
})());

check("G7b9#9: tense", alt.raw.colour.tension > 0.75, String(alt.raw.colour.tension));
check("G7b9#9: tenser than a lush maj9#11 and than a plain dominant", alt.raw.colour.tension > lush.raw.colour.tension
  && alt.raw.colour.tension > settle("G2 B3 D4 F4", "G7").raw.colour.tension);
check("G7b9#9: not simple", alt.raw.colour.simplicity < 0.3, String(alt.raw.colour.simplicity));
check("G7b9#9: the altered tones read as tension, not as lushness", alt.raw.colour.lushness < 0.4);

check("A minor triad: below neutral brightness", minor.raw.colour.brightness < 0.45, String(minor.raw.colour.brightness));
check("A minor triad: darker than C major, as simple", minor.raw.colour.brightness < triad.raw.colour.brightness - 0.3
  && near(minor.raw.colour.simplicity, triad.raw.colour.simplicity, 0.02));

check("cluster C Db D: tense", cluster.raw.colour.tension > 0.7, String(cluster.raw.colour.tension));
check("cluster C Db D: tenser than the triad, and not simple", cluster.raw.colour.tension > triad.raw.colour.tension + 0.5
  && cluster.raw.colour.simplicity < 0.45, String(cluster.raw.colour.simplicity));
check("a semitone that really sounds a semitone apart is rougher than the same notes spread out",
  cluster.raw.colour.tension > settle("C2 C#4 D6", null).raw.colour.tension);

check("dim7: tense and dark", dim7.raw.colour.tension > 0.4 && dim7.raw.colour.brightness < 0.4);
check("an inversion with no name is read from the chord, not from the bass (E G C is C major)",
  settle("E4 G4 C5", null).raw.colour.brightness > 0.6, String(settle("E4 G4 C5", null).raw.colour.brightness));
check("a stale chord name is ignored when it no longer covers what sounds (F A C F named Am)",
  settle("F3 A3 C4 F4", "Am").raw.colour.brightness > 0.6, String(settle("F3 A3 C4 F4", "Am").raw.colour.brightness));
check("a slash name is read from its root (Fmaj7/A is bright and lush)",
  settle("A3 C4 F4 E5", "Fmaj7/A").raw.colour.brightness > 0.6 && settle("A3 C4 F4 E5", "Fmaj7/A").raw.colour.lushness > 0.3);
check("the name decides an ambiguous tone: C7#5 is augmented, C7b13 keeps its 5th",
  settle("C3 E3 G#3 A#3", "C7#5").raw.colour.tension > settle("C3 E3 G3 A#3 G#4", "C7b13").raw.colour.tension - 0.5);
check("pedal-held voices and a wide voicing lift lushness", (() => {
  const close = settle("C4 E4 G4 B4 D5", "Cmaj9").raw.colour.lushness;
  const wide = play([{ t: 0, on: "C2 E3 G3 B3 D5", chord: "Cmaj9" }, { t: 0.2, lift: "C2 E3 G3 B3 D5" }], 2)
    .frames.at(-1).raw.colour.lushness;
  return wide > close;
})());

// ============================================================= the voicings a pianist actually plays (the audit's must-fixes) ==
// MF1. The 5th is the first note a real voicing drops, so a bass with a 3rd and a 7th above it roots the chord and the root
// hunt must leave it alone. Before this, Cm11 with no 5th was re-rooted to its own b7 and lit up major: a minor chord in
// bright light. The test of the fix is that each voicing reads the same blind (no chord name) as it does named.
{
  const voicings = [
    ["Cm11 with no 5th", "C3 Eb4 Bb4 D5 F5", "Cm11"],
    ["Dm11 with no 5th", "D2 F4 C5 E5 G5", "Dm11"],
    ["a G13 shell", "G2 F4 B4 E5", "G13"],
    ["C13 with no 5th", "C2 E4 Bb4 D5 A5", "C13"],
    ["an altered C7#5b9", "C2 E4 Bb4 Db5 Ab5", "C7#5b9"],
  ];
  for (const [label, text, name] of voicings) {
    const blind = settle(text, null).raw.colour, named = settle(text, name).raw.colour;
    check(`${label}: the same colour with the name and without it`,
      near(blind.brightness, named.brightness, 0.02) && near(blind.lushness, named.lushness, 0.02)
      && near(blind.tension, named.tension, 0.02),
      `blind ${blind.brightness.toFixed(2)}/${blind.lushness.toFixed(2)}/${blind.tension.toFixed(2)} against named `
      + `${named.brightness.toFixed(2)}/${named.lushness.toFixed(2)}/${named.tension.toFixed(2)} (bright/lush/tense)`);
  }
  const cm11 = settle("C3 Eb4 Bb4 D5 F5", null).raw.colour, g13 = settle("G2 F4 B4 E5", null).raw.colour;
  const alt75b9 = settle("C2 E4 Bb4 Db5 Ab5", null).raw.colour;
  report.push(`the voicings a pianist plays, blind: Cm11 no 5th bright ${cm11.brightness.toFixed(2)} | G13 shell bright `
    + `${g13.brightness.toFixed(2)} lush ${g13.lushness.toFixed(2)} | C7#5b9 tens ${alt75b9.tension.toFixed(2)} lush `
    + `${alt75b9.lushness.toFixed(2)} | Cmaj7/E bright ${settle("E4 G4 B4 C5", null).raw.colour.brightness.toFixed(2)}`);
  check("a minor 11th with no 5th is still minor: it stays dark", cm11.brightness < 0.4, String(cm11.brightness));
  check("a 13th shell is bright and lush, not a dark minor", g13.brightness > 0.6 && g13.lushness > 0.4,
    `${g13.brightness.toFixed(2)} / ${g13.lushness.toFixed(2)}`);
  check("an altered dominant renders electric, not creamy: tension over lushness",
    alt75b9.tension > 0.6 && alt75b9.lushness < 0.4, `${alt75b9.tension.toFixed(2)} / ${alt75b9.lushness.toFixed(2)}`);
  check("putting the omitted 5th back barely moves the colour (C13)", (() => {
    const no5 = settle("C2 E4 Bb4 D5 A5", null).raw.colour, with5 = settle("C2 G3 E4 Bb4 D5 A5", null).raw.colour;
    return near(no5.brightness, with5.brightness, 0.05) && near(no5.lushness, with5.lushness, 0.05);
  })());
  check("putting the omitted 5th back barely moves the colour (Cm11)", (() => {
    const bare = settle("C3 Eb4 Bb4 D5 F5", null).raw.colour, with5 = settle("C3 G3 Eb4 Bb4 D5 F5", null).raw.colour;
    return near(bare.brightness, with5.brightness, 0.05) && near(bare.lushness, with5.lushness, 0.05);
  })());
  // the hunt still fires where it should: neither of these basses carries a 7th
  check("the hunt still reads E G C as C major", settle("E3 G3 C4", null).raw.colour.brightness > 0.6);
  check("the hunt still gives C E A a fair hearing as Am/C", settle("C3 E4 A4", null).raw.colour.brightness < 0.4,
    String(settle("C3 E4 A4", null).raw.colour.brightness));
}
// MF2. The mirror of MF1: with a 3rd and a 5th over the bass the hunt never fired, so a seventh chord in first inversion kept
// its 3rd as the root and one inversion of the three flipped the light cold. A b6 with no 7th over the bass is the mark of an
// inversion, not a chord tone, so it sends the hunt out as well.
{
  const onE = settle("E4 G4 B4 C5", null).raw.colour, onG = settle("G4 B4 C5 E5", null).raw.colour;
  const onB = settle("B3 C4 E4 G4", null).raw.colour, named = settle("E4 G4 B4 C5", "Cmaj7/E").raw.colour;
  check("rolling through the inversions of one chord keeps one light: Cmaj7 on E, G and B",
    Math.max(onE.brightness, onG.brightness, onB.brightness) - Math.min(onE.brightness, onG.brightness, onB.brightness) < 0.05,
    `${onE.brightness.toFixed(2)} / ${onG.brightness.toFixed(2)} / ${onB.brightness.toFixed(2)}`);
  check("a maj7 in first inversion is bright, not a minor triad with a b6", onE.brightness > 0.6 && onE.lushness > 0.3,
    `${onE.brightness.toFixed(2)} / ${onE.lushness.toFixed(2)}`);
  check("the first inversion blind reads as it does with its name", near(onE.brightness, named.brightness, 0.02)
    && near(onE.lushness, named.lushness, 0.02));
  check("the same for a maj7 on its 3rd in another key: A C E F is F major, not A minor with a b6",
    settle("A3 C4 E4 F4", null).raw.colour.brightness > 0.6, String(settle("A3 C4 E4 F4", null).raw.colour.brightness));
  check("a minor triad with a b6 is heard as the maj7 it is: C Eb G Ab is Abmaj7/C",
    settle("C4 Eb4 G4 Ab4", null).raw.colour.brightness > 0.6, String(settle("C4 Eb4 G4 Ab4", null).raw.colour.brightness));
  // Left standing on purpose: Eb G Bb C is a Cm7 and an Eb6 note for note, the same shape over its bass either way, so no
  // rule over pitch classes can part them. The bass decides, and a chord name overrules it. Darkening the one would darken
  // a plain C6 with it, which would be the worse trade.
  const ebSix = settle("Eb4 G4 Bb4 C5", null).raw.colour, cSix = settle("C4 E4 G4 A4", null).raw.colour;
  check("a 6th chord and the m7 a 3rd below it are one shape: they read alike, and the bass decides",
    near(ebSix.brightness, cSix.brightness, 0.02) && cSix.brightness > 0.6,
    `${ebSix.brightness.toFixed(2)} / ${cSix.brightness.toFixed(2)}`);
  check("and the name still parts them: Cm7/Eb reads minor",
    settle("Eb4 G4 Bb4 C5", "Cm7/Eb").raw.colour.brightness < 0.45,
    String(settle("Eb4 G4 Bb4 C5", "Cm7/Eb").raw.colour.brightness));
}
// MF3. A 3rd with a 7th is a chord shape, not a cluster, so it pays no simpleNonTriad. A C13 read as a less simple object
// than three notes a semitone apart, and adding the omitted 5th used to make a chord read simpler than it did without it.
{
  const c13 = settle("C2 E4 Bb4 D5 A5", "C13").raw.colour.simplicity;
  check("a C13 reads simpler than three notes a semitone apart", c13 > cluster.raw.colour.simplicity,
    `${c13.toFixed(2)} against ${cluster.raw.colour.simplicity.toFixed(2)}`);
  check("adding a pitch class does not make a chord simpler (Cmaj9 with and without its 5th)", (() => {
    const no5 = settle("C3 E4 B4 D5", null).raw.colour.simplicity, with5 = settle("C3 G3 E4 B4 D5", null).raw.colour.simplicity;
    return with5 < no5;
  })(), `${settle("C3 E4 B4 D5", null).raw.colour.simplicity.toFixed(2)} then `
    + `${settle("C3 G3 E4 B4 D5", null).raw.colour.simplicity.toFixed(2)}`);
  check("a seventh-chord shell is no cluster: a C7 with no 5th is simpler than C Db D",
    settle("C3 E4 Bb4", null).raw.colour.simplicity > cluster.raw.colour.simplicity);
  check("a cluster is still a cluster: C Db D holds no chord", cluster.raw.colour.simplicity < 0.45);
}
// MF4. The brief asked for lushness maj13#11 spread > maj7 close > triad > power chord. It is a tie at the bottom, and it is
// recorded here and in the module header as the musically right answer: a major triad is not lush, and neither is a bare
// fifth. Simplicity and openness are what part those two, and they part them widely.
{
  const wide13 = settle("C2 G2 E3 B3 D4 F#4 A4", "Cmaj13#11").raw.colour;
  check("lushness falls maj13#11 spread, then maj7 close, then a tie at zero",
    wide13.lushness > maj7.raw.colour.lushness && maj7.raw.colour.lushness > 0.2
    && triad.raw.colour.lushness === 0 && power.raw.colour.lushness === 0,
    `${wide13.lushness.toFixed(2)} > ${maj7.raw.colour.lushness.toFixed(2)} > `
    + `${triad.raw.colour.lushness.toFixed(2)} = ${power.raw.colour.lushness.toFixed(2)}`);
  check("what parts a triad from a power chord is simplicity and openness, not lushness",
    power.raw.colour.simplicity > triad.raw.colour.simplicity + 0.15
    && power.raw.colour.openness > triad.raw.colour.openness + 0.5,
    `simp ${power.raw.colour.simplicity.toFixed(2)} against ${triad.raw.colour.simplicity.toFixed(2)}, open `
    + `${power.raw.colour.openness.toFixed(2)} against ${triad.raw.colour.openness.toFixed(2)}`);
  check("the tie is written down in the module header", (() => {
    const source = readFileSync(here("../arsenal/web/piano/harmony-feel.js"), "utf8");
    return source.slice(0, source.indexOf("\nimport {")).includes("triad and a power chord are both exactly 0");
  })());
}

// ======================================================================================================== the voices ==
{
  const run = play([{ t: 0, on: "C3 E3 G3 C5", chord: "C" }, { t: 0.7, on: "A4", chord: "C" }], 3);
  const before = run.at(0.5), during = run.at(1), after = run.at(2.5);
  check("a chord struck together has no melody voice: the solo is the top",
    before.voices.solo === midiOf("C5") && before.voices.top === midiOf("C5") && before.voices.bass === midiOf("C3"));
  check("a melody note struck over the held chord becomes the solo, chord tone or not",
    during.voices.solo === midiOf("A4") && during.voices.top === midiOf("C5"), String(during.voices.solo));
  check("the melody note stops counting once it is older than soloWindow", after.voices.solo === midiOf("C5"));
  check("spread is top minus bass", during.voices.spread === midiOf("C5") - midiOf("C3") && during.voices.count === 5);
  check("the bass-to-solo interval and its family come from the solo, not the top",
    during.dance.interval === midiOf("A4") - midiOf("C3") && during.dance.family === "third", String(during.dance.interval));
}
{  // an older host: state.pressed, entries with no held or pedal field
  const old = play([{ t: 0, on: "C3 E3 G3 B3 D4", chord: "Cmaj9" }], 2, { pressed: true }).frames.at(-1);
  const now = play([{ t: 0, on: "C3 E3 G3 B3 D4", chord: "Cmaj9" }], 2).frames.at(-1);
  check("state.pressed is read when state.sounding is missing", old.voices.count === 5 && old.voices.bass === midiOf("C3")
    && old.voices.top === midiOf("D4"));
  check("the pressed fallback reads the same colour", near(old.colour.lushness, now.colour.lushness)
    && near(old.colour.brightness, now.colour.brightness) && near(old.colour.tension, now.colour.tension));
}

// ========================================================================================================= the dance ==
{  // contrary: the bass steps down while the solo steps up
  const run = play([{ t: 0, on: "C3 E5" }, { t: 1, on: "B2 F5", off: "C3 E5" }, { t: 2, on: "A2 G5", off: "B2 F5" }], 2.5);
  const step1 = run.at(1), step2 = run.at(2), quiet = run.at(0.5);
  check("contrary motion is named", step1.dance.motion === "contrary" && step2.dance.motion === "contrary", step1.dance.motion);
  check("both voices report their step on the frame it happens", step1.events.bassMoved && step1.events.soloMoved
    && !run.frames[run.at(1).i + 1].events.bassMoved);
  check("a held pair reads static before the first step", quiet.dance.motion === "static" && quiet.raw.dance.pull === 0);
  check("pulling apart raises pull", step2.raw.dance.pull > 0.3 && step2.dance.interval === 34, String(step2.raw.dance.pull));
  check("stretch follows the register distance", near(step2.raw.dance.stretch, 34 / FEEL.stretchFull, 1e-12));
  check("contrary motion turns the phase one way", step2.raw.dance.phase > 0 && step2.raw.dance.phase < 0.5,
    String(step2.raw.dance.phase));
  check("pull fades once the voices settle", run.at(2.5).raw.dance.pull < step2.raw.dance.pull);
}
{  // parallel octaves: the interval never changes
  const run = play([{ t: 0, on: "C3 C4" }, { t: 1, on: "D3 D4", off: "C3 C4" }, { t: 2, on: "E3 E4", off: "D3 D4" }], 2.2);
  const step = run.at(2);
  check("parallel motion is named", step.dance.motion === "parallel" && run.at(1).dance.motion === "parallel");
  check("parallel octaves never pull", step.raw.dance.pull === 0 && step.dance.pull < 0.001);
  check("the octave reads as an octave", step.dance.interval === 12 && step.dance.family === "octave"
    && step.raw.dance.consonance > 0.95);
  check("parallel motion turns the phase the other way", step.raw.dance.phase > 0.5, String(step.raw.dance.phase));
}
{  // oblique: a pedal bass under a moving line
  const run = play([{ t: 0, on: "C2" }, { t: 0.02, lift: "C2", pedalDown: true }, { t: 1, on: "E4" },
    { t: 1.5, on: "G4", off: "E4" }, { t: 2, on: "A4", off: "G4" }], 4);
  check("oblique motion is named while only one voice steps", run.at(1.5).dance.motion === "oblique"
    && run.at(2).dance.motion === "oblique", run.at(2).dance.motion);
  check("the pedal bass never steps", run.frames.every((fr) => !fr.events.bassMoved));
  check("the solo steps on the strike frames", run.at(1.5).events.soloMoved && run.at(2).events.soloMoved
    && !run.at(1.75).events.soloMoved);
  check("motion falls back to static once the steps stop", run.at(3.8).dance.motion === "static");
  check("the pedal bass is still sounding under the line", run.at(2).voices.bass === midiOf("C2"));
}
{  // a held chord: nothing moves
  const run = play([{ t: 0, on: "C3 E3 G3 C4", chord: "C" }], 3);
  check("a held chord is static", run.frames.every((fr) => fr.dance.motion === "static"));
  check("a held chord raises no step events after its first frame",
    run.frames.every((fr, i) => i === 0 || (!fr.events.bassMoved && !fr.events.soloMoved && !fr.events.chordChanged)));
  check("phase holds still while nothing steps", run.at(3).raw.dance.phase === 0 && run.at(3).dance.phase === 0);
}
{  // similar motion: both voices up, by different steps
  const run = play([{ t: 0, on: "C3 E4" }, { t: 1, on: "E3 G4", off: "C3 E4" }], 1.5);
  check("similar motion is named", run.at(1).dance.motion === "similar", run.at(1).dance.motion);
}

// ====================================================================================================== the smoothing ==
{  // attack, release, monotonic approach
  const run = play([{ t: 0, on: "C2 G2 E3 B3 D4 F#4", chord: "Cmaj9#11" }, { t: 2, off: "C2 G2 E3 B3 D4 F#4", chord: null }], 4,
    { fps: 100 });
  const target = run.at(1).raw.colour;
  let rising = true, capped = true;
  for (let i = 1; i <= 200; i++) {
    const a = run.frames[i - 1].colour, b = run.frames[i].colour;
    if (b.lushness < a.lushness - 1e-12 || b.tension < a.tension - 1e-12 || b.brightness < a.brightness - 1e-12
      || b.simplicity > a.simplicity + 1e-12) rising = false;
    if (b.lushness > target.lushness + 1e-12 || b.brightness > target.brightness + 1e-12) capped = false;
  }
  check("the approach is monotonic and never overshoots", rising && capped);
  const atAttack = run.at(FEEL.attack).colour.lushness;
  check("one attack time constant covers about 63% of the way", near(atAttack, target.lushness * (1 - Math.exp(-1)), 0.005),
    `${atAttack.toFixed(4)} of ${target.lushness.toFixed(4)}`);
  check("three attack time constants are as good as arrived", run.at(3 * FEEL.attack).colour.lushness > 0.94 * target.lushness);
  const left = run.at(2 + FEEL.release).colour.lushness;
  check("release is the slower half: one release time constant leaves about 37%",
    near(left, target.lushness * Math.exp(-1), 0.02), `${left.toFixed(4)} of ${target.lushness.toFixed(4)}`);
  check("attack is faster than release", run.at(FEEL.attack).colour.lushness > target.lushness * 0.5
    && run.at(2 + FEEL.attack).colour.lushness > target.lushness * 0.5);
}
{  // the same answer at 30 and at 144 frames a second
  const script = [{ t: 0, on: "C2 G2 E3 B3 D4 F#4", chord: "Cmaj9#11" }, { t: 1, on: "A2 E4", off: "C2 G2", chord: "Am9" },
    { t: 2, off: "A2 E4 E3 B3 D4 F#4", chord: null }];
  const slow = play(script, 3, { fps: 30 }), fast = play(script, 3, { fps: 144 });
  let worstStep = 0, worstStepAt = "", worstMoving = 0, worstMovingAt = "";
  for (const t of [1 / 6, 1 / 3, 1 / 2, 5 / 6, 4 / 3, 5 / 3, 13 / 6, 8 / 3]) {
    const a = slow.at(t), b = fast.at(t);
    // A chord holds its reading between changes, so these follow exactly the same curve at any frame rate.
    for (const key of ["simplicity", "lushness", "tension", "brightness", "openness"]) {
      const d = Math.abs(a.colour[key] - b.colour[key]) / Math.max(0.05, Math.abs(a.colour[key]));
      if (d > worstStep) { worstStep = d; worstStepAt = `${key} at ${t.toFixed(3)}: ${a.colour[key].toFixed(9)} vs ${b.colour[key].toFixed(9)}`; }
    }
    for (const key of ["consonance", "stretch"]) {
      const d = Math.abs(a.dance[key] - b.dance[key]) / Math.max(0.05, Math.abs(a.dance[key]));
      if (d > worstStep) { worstStep = d; worstStepAt = `${key} at ${t.toFixed(3)}: ${a.dance[key].toFixed(9)} vs ${b.dance[key].toFixed(9)}`; }
    }
    // pull chases a target that is itself decaying, so a coarser frame rate samples it a touch higher: within the 2% bar.
    const d = Math.abs(a.dance.pull - b.dance.pull) / Math.max(0.05, Math.abs(a.dance.pull));
    if (d > worstMoving) { worstMoving = d; worstMovingAt = `pull at ${t.toFixed(3)}: ${a.dance.pull.toFixed(5)} vs ${b.dance.pull.toFixed(5)}`; }
  }
  report.push(`30 fps against 144 fps: colour, consonance and stretch differ by ${(worstStep * 100).toFixed(7)}% at worst `
    + `(${worstStepAt}); pull, which chases a decaying target, by ${(worstMoving * 100).toFixed(3)}% (${worstMovingAt})`);
  check("30 fps and 144 fps give the same colour to the last decimal", worstStep < 1e-9, worstStepAt);
  check("30 fps and 144 fps agree within 2% on pull", worstMoving < 0.02, worstMovingAt);
}
{  // silence decays to rest
  const run = play([{ t: 0, on: "C3 E3 G3 A#3", chord: "C7" }, { t: 1, off: "C3 E3 G3 A#3", chord: null }], 5);
  const sounding = run.at(1), quiet = run.at(5);
  check("the chord read before the silence", sounding.colour.tension > 0.1 && sounding.colour.brightness > 0.6);
  check("silence decays colour to rest", near(quiet.colour.simplicity, REST.simplicity, 0.01)
    && near(quiet.colour.lushness, REST.lushness, 0.01) && near(quiet.colour.tension, REST.tension, 0.01)
    && near(quiet.colour.brightness, REST.brightness, 0.01) && near(quiet.colour.openness, REST.openness, 0.01));
  check("silence decays the dance to rest", near(quiet.dance.consonance, REST.consonance, 0.01)
    && near(quiet.dance.pull, REST.pull, 0.01) && near(quiet.dance.stretch, REST.stretch, 0.01)
    && quiet.dance.motion === "static" && quiet.dance.interval === 0);
  check("silence empties the voices", quiet.voices.count === 0 && quiet.voices.bass === null && quiet.voices.spread === 0);
  let falling = true;
  for (let i = run.at(1).i + 2; i < run.frames.length; i++) {
    if (run.frames[i].colour.tension > run.frames[i - 1].colour.tension + 1e-12) falling = false;
  }
  check("the decay is monotonic", falling);
  check("reset() puts everything back at rest", (() => {
    run.feel.reset();
    const f = run.feel.frame;
    return f.colour.simplicity === REST.simplicity && f.colour.brightness === REST.brightness && f.voices.count === 0
      && f.dance.phase === 0;
  })());
}

// ========================================================================================================= the events ==
{
  const run = play([{ t: 0, on: "C3 E3 G3", chord: "C" }, { t: 1, off: "C3 E3 G3", chord: null },
    { t: 1.5, on: "C3 E3 G3", chord: "C" }, { t: 2.5, on: "F2 A2 C3", off: "E3 G3", chord: "F" }], 3.5);
  const chordFrames = run.frames.filter((fr) => fr.events.chordChanged).map((fr) => +fr.t.toFixed(3));
  const bassFrames = run.frames.filter((fr) => fr.events.bassMoved).map((fr) => +fr.t.toFixed(3));
  check("chordChanged fires on the first chord and on a new name only", chordFrames.length === 2 && chordFrames[0] === 0
    && chordFrames[1] === 2.5, chordFrames.join(" "));
  check("the same chord coming back after a rest is no change", !run.at(1.5).events.chordChanged);
  check("bassMoved fires on the step frame only", bassFrames.length === 1 && bassFrames[0] === 2.5, bassFrames.join(" "));
  check("a first note after a long rest is no step", !run.at(1.5).events.bassMoved && !run.at(1.5).events.soloMoved);
  check("only two frames in the whole run carry a flag at all",
    run.frames.filter((fr) => fr.events.chordChanged || fr.events.bassMoved || fr.events.soloMoved)
      .map((fr) => +fr.t.toFixed(3)).join(" ") === "0 2.5");
}
{  // a host that has no state.chord at all: a new set of three or more pitch classes is the change
  const run = play([{ t: 0, on: "C3 E3 G3" }, { t: 1, on: "F3", off: "E3" }], 2, { noChordField: true });
  const changes = run.frames.filter((fr) => fr.events.chordChanged).map((fr) => +fr.t.toFixed(3));
  check("with no chord name, a new pitch-class set is the chord change", changes.length === 2 && changes[0] === 0
    && changes[1] === 1, changes.join(" "));
}

// ==================================================================================================== the frame budget ==
if (!quick) {
  const big = new Map();
  const spread = [0, 7, 12, 16, 19, 23, 26, 28, 31, 35, 38, 40, 43, 47, 50, 52, 55, 59, 62, 64];
  for (let i = 0; i < 20; i++) big.set(36 + spread[i], entry(i * 0.01, true, i % 5 === 0));
  const state = { sounding: big, pedal: true, chord: { name: "Cmaj9", nns: "", key: "" } };
  const other = { sounding: big, pedal: true, chord: { name: "Fmaj7#11", nns: "", key: "" } };
  const feel = createHarmonyFeel();
  const times = new Array(20000);
  times[0] = "boxed";  // a tagged array: the times are already boxed, so this harness allocates nothing per call either
  for (let i = 0; i < times.length; i++) times[i] = i / 60 + 0.5;
  const DT = 1 / 60;
  const run = (n, from) => { for (let i = 0; i < n; i++) feel.update((i >> 5) % 2 ? other : state, DT, times[(from + i) % times.length]); };
  run(200000, 0);
  check("twenty notes still read as twenty voices", feel.frame.voices.count === 20);

  let best = Infinity;
  for (let trial = 0; trial < 5; trial++) {
    const t0 = performance.now();
    run(100000, 0);
    const ms = (performance.now() - t0) / 100000;
    if (ms < best) best = ms;
  }
  report.push(`update() with 20 sounding notes: ${(best * 1000).toFixed(2)} us (${best.toFixed(5)} ms) per frame, best of 5 x 100k`);
  check("update costs under 0.05 ms for 20 sounding notes", best < 0.05, `${best.toFixed(5)} ms`);

  let collect = null;
  try { v8.setFlagsFromString("--expose-gc"); collect = vm.runInNewContext("gc"); } catch { collect = null; }
  if (typeof collect === "function") {
    // A frame that allocated even one boxed number would fill the young generation and force collections: 400k frames of
    // 16 bytes is over 6 MB. So collect by hand first, then watch for any collection at all, and for the heap growing.
    let collections = 0;
    const watch = new PerformanceObserver((list) => { collections += list.getEntries().length; });
    watch.observe({ entryTypes: ["gc"] });
    run(50000, 3);
    collect(); collect();
    await new Promise((r) => setTimeout(r, 30));
    collections = 0;
    const before = v8.getHeapStatistics().used_heap_size;
    run(400000, 7);
    const grew = v8.getHeapStatistics().used_heap_size - before;
    await new Promise((r) => setTimeout(r, 60));
    watch.disconnect();
    report.push(`400k frames after a collection by hand: ${collections} collections, heap +${grew} bytes `
      + `(${(grew / 400000).toFixed(3)} a frame, and nothing was freed in between)`);
    check("nothing is allocated per frame once it is warm: no collection was needed", collections === 0, String(collections));
    check("nothing is allocated per frame once it is warm: the heap barely moves", grew < 400000,
      `${grew} bytes over 400k frames`);
  } else report.push("allocation: skipped (no gc available)");
}

for (const line of report) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
