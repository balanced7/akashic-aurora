// Node tests for arsenal/web/piano/spell.js, the one shared speller (research/in-flight/piano-theory-nextgen-2026-09-14/
// tn1-rulings.md, "Round 5-6 status and the spelling ruling for TN2", rules 1-5; live sheet music LS6's key signatures,
// research/in-flight/live-sheet-music-2026-09-14/ls1-rulings.md). Zero dependencies, synthetic voicings only:
//   node tests/piano_spell.test.mjs            everything, the full synthetic sweep (rule 5's receipt) included
//   node tests/piano_spell.test.mjs --quick    without the full sweep
// Sections: the module and its API; key signatures (24 keys); notes; spellChord's rule; the ruling's cases through the
// reader (chordread.js, which names every reading with this speller); the round-6 musical findings; the E♭ minor
// Cb+(add9); the full sweep: every 3-7 pitch-class set, three voicings, 24 keys and no key at both biases, 0 triple
// accidentals anywhere and 0 double accidentals on a root or bass (read() names, detect() infos and ALSO names).
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as NV from "../arsenal/web/piano/nashville.js";
import * as S from "../arsenal/web/piano/spell.js";
import { createReader, parseSuffix } from "../arsenal/web/piano/chordread.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const quick = process.argv.includes("--quick");
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const mod = (a, n) => ((a % n) + n) % n;
const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
function midiOf(tok) {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(tok);
  return m ? (Number(m[3]) + 1) * 12 + LETTER_PC["CDEFGAB".indexOf(m[1])] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0) : null;
}
const midis = (text) => text.trim().split(/\s+/).map(midiOf);
const plainText = (s) => String(s).replace(/♭/g, "b").replace(/♯/g, "#");
const chordOf = (name) => { const c = NV.parseChord(plainText(name)); return c && c.kind === "chord" ? c : null; };

const pianoSrc = readFileSync(here("../arsenal/web/piano.js"), "utf8");
const THEORY_A = pianoSrc.indexOf("// ===== THEORY BEGIN"), THEORY_B = pianoSrc.indexOf("// ===== THEORY END");
const sliceTheory = () => new Function(pianoSrc.slice(THEORY_A, THEORY_B) + "\nreturn Theory;")();
const reader = createReader({ Theory: sliceTheory(), NV });
const Templates = sliceTheory();  // today's Theory.detect, whose names ALSO respells
const MAJOR_KEYS = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"].map((t) => `${t} major`);
const MINOR_KEYS = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"].map((t) => `${t} minor`);
const KEYS24 = [...MAJOR_KEYS, ...MINOR_KEYS];
const biasOf = (key, bias = 0) => (key ? NV.parseKey(key).bias : bias);

// ------------------------------------------------------------------------------------------ the module and its API --
const spellSrc = readFileSync(here("../arsenal/web/piano/spell.js"), "utf8");
const code = spellSrc.replace(/\/\/.*$/gm, "");
check("SPELL_API is arsenal.piano.spell/v1", S.SPELL_API === "arsenal.piano.spell/v1");
for (const fn of ["spellChord", "chordName", "spellNote", "spellMidi", "keySignature", "toneCost", "keyContext", "spellAlone", "spellingsOf", "spellInterval", "defaultSteps"]) {
  check(`spell.js exports ${fn}`, typeof S[fn] === "function");
}
check("spell.js is pure: it imports ./nashville.js only and touches no DOM or three.js", [...code.matchAll(/^import .* from "([^"]+)";/gm)].map((m) => m[1]).join() === "./nashville.js"
  && !/\b(document|window|THREE|localStorage)\b/.test(code));
const readerSrc = readFileSync(here("../arsenal/web/piano/chordread.js"), "utf8").replace(/\/\/.*$/gm, "");
check("rule 4, one speller: chordread.js imports spell.js and keeps no speller of its own", /from "\.\/spell\.js"/.test(readerSrc)
  && !/function (spellRoot|augRoot|spellFromRoot)|oddOffKey|Theory\.spell(Alone|Interval)/.test(readerSrc));
const T = sliceTheory();
let aloneSame = 0;
for (const bias of [-1, 0, 1]) for (let pc = 0; pc < 12; pc++) { const a = S.spellAlone(pc, bias), b = T.spellAlone(pc, bias); if (a.letter === b.letter && a.acc === b.acc) aloneSame++; }
check("spellAlone is Theory.spellAlone (36 of 36 at bias -1, 0 and 1)", aloneSame === 36, String(aloneSame));

// ------------------------------------------------------------------------------------------------ key signatures --
const SIG = {
  "C major": "", "G major": "F#", "D major": "F# C#", "A major": "F# C# G#", "E major": "F# C# G# D#", "B major": "F# C# G# D# A#", "F# major": "F# C# G# D# A# E#",
  "F major": "Bb", "Bb major": "Bb Eb", "Eb major": "Bb Eb Ab", "Ab major": "Bb Eb Ab Db", "Db major": "Bb Eb Ab Db Gb",
  "A minor": "", "E minor": "F#", "B minor": "F# C#", "F# minor": "F# C# G#", "C# minor": "F# C# G# D#", "G# minor": "F# C# G# D# A#",
  "D minor": "Bb", "G minor": "Bb Eb", "C minor": "Bb Eb Ab", "F minor": "Bb Eb Ab Db", "Bb minor": "Bb Eb Ab Db Gb", "Eb minor": "Bb Eb Ab Db Gb Cb",
};
for (const key of KEYS24) {
  const sig = S.keySignature(key), want = SIG[key], names = sig.accidentals.map((a) => a.name).join(" ");
  check(`keySignature(${key}) is ${want || "none"}, in staff order`, names === want && sig.key === key && sig.count === (want ? want.split(" ").length : 0)
    && sig.type === (!want ? "none" : want.includes("#") ? "sharps" : "flats") && sig.accidentals.every((a) => S.nameOf(a) === a.name), `${names} ${sig.count} ${sig.type}`);
}
check("keySignature with no key is none", JSON.stringify(S.keySignature(null)) === JSON.stringify({ key: null, type: "none", count: 0, accidentals: [] })
  && S.keySignature("not a key").type === "none");
check("keySignature reads a tracker key ({ tonic, mode }) and a parsed key", S.keySignature({ tonic: 1, mode: "major" }).key === "Db major" && S.keySignature(NV.parseKey("Eb minor")).count === 6);

// ------------------------------------------------------------------------------------------------------- notes --
// LS6: every note of the key is spelled on its scale letter, so a flat key never shows a sharp (and a sharp key never a
// flat) on its own notes, and a G♭ passage carries its flats in the signature, not beside the notes.
const scaleBad = [];
for (const key of KEYS24) {
  const k = NV.parseKey(key), sig = S.keySignature(key), tonic = NV.parseChord(key.split(" ")[0], "note").root;
  (k.mode === "major" ? [0, 2, 4, 5, 7, 9, 11] : [0, 2, 3, 5, 7, 8, 10]).forEach((semis, d) => {
    const want = S.spellInterval(tonic, semis, d), got = S.spellNote(k.tonic + semis, key);
    if (got.letter !== want.letter || got.acc !== want.acc || !got.inScale || (sig.type === "flats" && got.acc > 0) || (sig.type === "sharps" && got.acc < 0)) {
      scaleBad.push(`${key} degree ${d + 1}: ${got.name}`);
    }
  });
}
check("LS6: every note of each of the 24 keys is spelled on its scale letter (flat keys show no sharps and sharp keys no flats on their own notes)", scaleBad.length === 0, scaleBad.slice(0, 6).join(" | "));
for (const [pc, key, bias, want, why] of [
  [6, "Db major", 0, "Gb", "the key's 4"], [11, "Db major", 0, "B", "Cb is an odd letter off the scale"], [4, "Eb major", 0, "E", "a natural off the scale"],
  [0, "E major", 0, "C", "B# is an odd letter off the scale"], [5, "F# major", 0, "E#", "the scale's own E#"], [11, "Gb major", 0, "Cb", "the scale's own Cb"],
  [0, "C# minor", 0, "B#", "the leading tone"], [3, "E major", 0, "D#", "the key's 7"], [6, "C major", 0, "F#", "a tie goes to the key's #4"],
  [10, "C major", 0, "Bb", "a tie goes to the key's b7"], [7, "G# minor", 0, "G", "alone, F## is a double (3) and G a scale pitch on another letter (2)"],
  [1, null, -1, "Db", "the bias"], [1, null, 1, "C#", "the bias"], [1, null, 0, "Db", "neutral: Db Eb F# Ab Bb"], [6, null, 0, "F#", "neutral"], [5, null, 1, "F", "never E# alone"],
]) {
  const got = S.spellNote(pc, key, { bias }).name;
  check(`spellNote(${pc}, ${key ?? "no key, bias " + bias}) is ${want} (${why})`, got === want, got);
}
const d7 = S.spellChord({ rootPc: 3, tonesPc: [3, 7, 10, 1], key: "G# minor", steps: { 4: 2, 7: 4, 10: 6 }, suffix: "7" });
check("spellNote in a chord keeps the chord's spelling: F## in D#7 in G# minor", S.chordName(d7, "7") === "D#7" && S.spellNote(7, "G# minor", { chord: d7 }).name === "F##", S.chordName(d7, "7"));
const m60 = S.spellMidi(60, "C# minor"), m61 = S.spellMidi(61, "Db major");
check("spellMidi counts octaves by the spelling (B#3 is MIDI 60) and diatonic steps (C4 = 28)", m60.name === "B#" && m60.octave === 3 && m60.diatonic === 27
  && m61.name === "Db" && m61.octave === 4 && m61.diatonic === 29, `${m60.name}${m60.octave} ${m60.diatonic}; ${m61.name}${m61.octave} ${m61.diatonic}`);

// ---------------------------------------------------------------------------------------------- spellChord's rule --
const names = (s) => s.tones.map((t) => t.name).join(" ");
const cand = (s, root) => s.candidates.find((x) => x.root === root);
const vPlus = S.spellChord({ rootPc: 6, tonesPc: [6, 10, 2], key: "B minor", steps: { 4: 2, 8: 4 }, suffix: "aug" });
check("rule 1, counted against the key: F#+ in B minor is F# A# C## (3), Gb+ is Gb Bb D (4: Gb and Bb are the key's F# and A# on other letters)",
  names(vPlus) === "F# A# C##" && vPlus.score === 3 && cand(vPlus, "Gb")?.score === 4, `${names(vPlus)} ${JSON.stringify(vPlus.candidates)}`);
const vPlusNoKey = S.spellChord({ rootPc: 6, tonesPc: [6, 10, 2], steps: { 4: 2, 8: 4 }, bias: 1 });
check("with no key every note is off the scale: the same notes read Gb+ at bias 1 (Gb Bb D, 2, against F# A# C##, 5)", vPlusNoKey.parts.root === "Gb" && vPlusNoKey.score === 2, JSON.stringify(vPlusNoKey.candidates));
for (const [bias, want] of [[1, "F#"], [-1, "Gb"], [0, "F#"]]) {
  const s = S.spellChord({ rootPc: 6, tonesPc: [6, 10, 1], bias });
  check(`rule 2, a tie with no key goes to the bias spelling: F# A# C# and Gb Bb Db (3 each) at bias ${bias} read ${want}`, s.parts.root === want && cand(s, "F#").score === cand(s, "Gb").score, JSON.stringify(s.candidates));
}
const tieKey = S.spellChord({ rootPc: 6, tonesPc: [6, 10, 1], key: "C major", suffix: "" }), tieNote = S.spellChord({ rootPc: 6, tonesPc: [6, 10, 1], key: "C major", suffix: "m7b5" });
check("rule 2, a tie in a key goes to the key's spelling: a major chord on C major's tritone reads Gb (b5), and the same pitch spelled as the key's #4 for other families", tieKey.parts.root === "Gb" && tieNote.parts.root === "F#",
  `${tieKey.parts.root} ${tieNote.parts.root}`);
const fixed = S.spellChord({ rootPc: 8, tonesPc: [8, 0, 3], rootSp: { letter: 4, acc: 1 } });
check("rootSp fixes the root and the rest follows it: G# B# D#", names(fixed) === "G# B# D#" && fixed.candidates.length === 1, names(fixed));
const triple = S.spellChord({ rootPc: 0, tonesPc: [0, 3], rootSp: { letter: 6, acc: 1 }, steps: { 3: 1 } });
check("a triple accidental is forbidden: a #9 above B# (C###) is written in the key instead, and counted as forced", triple.forced === 1 && triple.tones.every((t) => Math.abs(t.acc) <= 2), names(triple));
const overFive = S.spellChord({ rootPc: 6, tonesPc: [6, 10, 2], bassPc: 2, key: "B minor", steps: { 4: 2, 8: 4 }, suffix: "aug" });
check("never a double accidental on a bass: F#+ over its #5 would be F#aug/C##, so the root that needs no forced note wins (Gbaug/D)", S.chordName(overFive, "aug") === "Gbaug/D"
  && cand(overFive, "F#").forced === 1 && cand(overFive, "Gb").forced === 0, `${S.chordName(overFive, "aug")} ${JSON.stringify(overFive.candidates)}`);
const lean = S.spellChord({ rootPc: 8, tonesPc: [8, 11, 3], bassPc: 1 }), leanFlat = S.spellChord({ rootPc: 8, tonesPc: [8, 11, 3], bassPc: 1, bias: -1 });
check("rule 3 with no key: a bass outside the chord leans the way the chord's accidentals lean (G#m/C#, at bias 0 and -1)", S.chordName(lean, "m") === "G#m/C#" && S.chordName(leanFlat, "m") === "G#m/C#",
  `${S.chordName(lean, "m")} ${S.chordName(leanFlat, "m")}`);
const eOverC = S.spellChord({ rootPc: 4, tonesPc: [4, 8, 11], bassPc: 0, key: "C# minor" }), d6 = S.spellChord({ rootPc: 3, tonesPc: [3, 7, 0], bassPc: 0, key: "C# minor", steps: { 4: 2, 9: 5 }, suffix: "6" });
check("a minor key's raised 7th leaves the scale while the chord holds the lowered 7th: E G# B over C in C# minor is E/C; D#6 over its 6th keeps B# (no B sounds)",
  S.chordName(eOverC, "") === "E/C" && S.chordName(d6, "6") === "D#6/B#", `${S.chordName(eOverC, "")} ${S.chordName(d6, "6")}`);
check("default letter steps: an 8 is a #5 without a 5th (C E G#) and a b13 with one (C E G Ab); a dim7's 7th is the cheaper of a diminished 7th and a 6th (C Eb Gb A with no key)",
  names(S.spellChord({ rootPc: 0, tonesPc: [0, 4, 8] })) === "C E G#" && names(S.spellChord({ rootPc: 0, tonesPc: [0, 4, 7, 8] })) === "C E G Ab"
  && names(S.spellChord({ rootPc: 0, tonesPc: [0, 3, 6, 9] })) === "C Eb Gb A");
check("toneCost: 0 on the key's scale, a natural off it 0, one accidental 1, an odd letter or a scale pitch on another letter 2, a double 3, a triple forbidden",
  S.toneCost({ letter: 3, acc: 1 }, "B minor") === 0 && S.toneCost({ letter: 0, acc: 0 }, "Eb major") === 0 && S.toneCost({ letter: 3, acc: 1 }, "C major") === 1
  && S.toneCost({ letter: 6, acc: 1 }, "C major") === 2 && S.toneCost({ letter: 4, acc: -1 }, "B minor") === 2 && S.toneCost({ letter: 0, acc: 2 }, "B minor") === 3
  && S.toneCost({ letter: 0, acc: 3 }) === Infinity && S.toneCost({ letter: 2, acc: 1 }, "F# major") === 0);

// -------------------------------------------------------------------------------- the ruling's cases, through the reader --
// Each: notes, key, bias with no key, the top reading's name (read() and detect()), detect()'s chips when given.
function readCase(label, notes, key, bias, want, chips = null, runnerUp = null) {
  const ms = midis(notes), res = reader.read(ms, { key, keyBias: bias }), info = reader.detect(ms, biasOf(key, bias), { key });
  const top = res.readings[0]?.name, second = res.readings.slice(1).map((r) => r.name);
  const ok = top === want && info.name === want && (!chips || info.pcNames.join(" ") === chips) && (!runnerUp || second.includes(runnerUp));
  check(`${label}: ${notes} in ${key ?? "no key, bias " + bias} reads ${want}${chips ? ` (${chips})` : ""}${runnerUp ? `, ${runnerUp} listed` : ""}`, ok,
    `read ${res.readings.slice(0, 3).map((r) => r.name).join(" | ")}; detect ${info.name} (${info.pcNames?.join(" ")})`);
}
readCase("ruling: the augmented root whose 3rd needs no double", "C3 E3 G#3 D4", "C# minor", 0, "C+(add9)", "C E G# D", "E7#5/B#");
readCase("ruling: F+(add9) in F# major, not E#+(add9)", "F3 A3 C#4 G4", "F# major", 0, "F+(add9)", "F A C# G", "A7#5/E#");
readCase("ruling: Eb+(add9) in A major", "Eb3 G3 B3 F4", "A major", 0, "Eb+(add9)", "Eb G B F", "G7#5/D#");

// Rule 5: sharp-key V+ chords keep the key's letters where only the #5 is doubled (and the V7#5 alike). In G# minor the V+
// would double its 3rd as well (D# F## A##), so it takes the enharmonic (Eb G B), as round 6 ruled.
for (const [key, root, chips] of [["E major", "B", "B D# F##"], ["B major", "F#", "F# A# C##"], ["F# major", "C#", "C# E# G##"], ["E minor", "B", "B D# F##"],
  ["B minor", "F#", "F# A# C##"], ["F# minor", "C#", "C# E# G##"], ["C# minor", "G#", "G# B# D##"], ["D major", "A", "A C# E#"], ["A major", "E", "E G# B#"]]) {
  const r = NV.parseChord(root, "note").root, pc = mod(LETTER_PC[r.letter] + r.acc, 12), ms = [48 + pc, 52 + pc, 56 + pc];
  const res = reader.read(ms, { key }), info = reader.detect(ms, biasOf(key), { key }), sev = reader.read([...ms, 58 + pc], { key });
  const inKey = NV.spellInKey(r, key, { suffix: "aug" });
  check(`rule 5: the V+ of ${key} keeps the key's letters: ${root}aug (${chips}), and ${root}7#5`, res.readings[0]?.name === `${root}aug` && info.pcNames.join(" ") === chips
    && inKey.letter === r.letter && inKey.acc === r.acc && sev.readings[0]?.name === `${root}7#5`, `${res.readings[0]?.name} (${info.pcNames.join(" ")}), ${sev.readings[0]?.name}`);
}
readCase("rule 5: the V+ of G# minor would double its 3rd (D# F## A##)", "D#3 G3 B3", "G# minor", 0, "Ebaug", "Eb G B");

// ---------------------------------------------------------------------------------------- the round-6 musical findings --
// 1. A triple-sharp 7#5 in G# minor (F##7#5: F## A## C### E#), and its D# minor twin.
readCase("round 6 finding 1: no triple-sharp 7#5 in G# minor", "G3 B3 D#4 F4", "G# minor", 0, "G7#5", "G B D# F");
readCase("round 6 finding 1: its runner-up over D# is G7#5/D#", "Eb3 G3 B3 F4", "G# minor", 0, "Eb+(add9)", "Eb G B F", "G7#5/D#");
readCase("round 6 finding 1: no C##7#5 in D# minor", "D3 F#3 A#3 C4", "D# minor", 0, "D7#5", "D F# A# C");
// 2. A real window whose 7#5 root and bass letters disagreed (A#7#5/D in F# major: D is the chord's 3rd, C##). Its
//    synthetic twin, D F# G# A#, in the keys that name A# and with no key: Bb7#5/D, the bass on its chord letter.
for (const [key, bias] of [["F# major", 0], ["B major", 0], ["E major", 0], ["C# minor", 0], ["A major", 0], [null, 1], [null, -1]]) {
  readCase("round 6 finding 2: a 7#5 whose root and bass letters agree", "D3 F#3 G#3 A#3", key, bias, "Bb7#5/D", "D F# Ab Bb");
}
// 3. Odd basses on top slash names (the page named the same chords on plain basses).
readCase("round 6 finding 3: no odd bass on a top slash name", "C3 C#3 E3 G3", "C major", 0, "C#dim/C", "C C# E G");
readCase("round 6 finding 3: no odd bass on a top slash name", "B3 C#4 E4 G#4", "C major", 0, "C#m7/B", "B C# E G#");
readCase("round 6 finding 3: no odd bass on a top slash name", "E3 F#3 A#3 C#4", "C major", 0, "F#7/E", "E F# A# C#");
readCase("round 6 finding 3: no odd bass on a top slash name", "F3 F#3 A3 C4", "C major", 0, "F#dim/F", "F F# A C");
// 4. maj7#5 voicings named as slash triads escaped the augmented rule (Ab/Fb, B#/G#, C##/A#, E#/C#, F##/D#).
readCase("round 6 finding 4: a maj7#5 voicing named as a slash triad", "E3 G#3 C4 D#4", "C major", 0, "Ab/E", "E Ab C Eb", "Emaj7#5");
readCase("round 6 finding 4: a maj7#5 voicing named as a slash triad", "G#3 C4 E4 G4", "C# minor", 0, "C/G#", "G# C E G");
readCase("round 6 finding 4: a maj7#5 voicing named as a slash triad", "A#3 D4 F#4 A4", "D# minor", 0, "D/A#", "A# D F# A");
readCase("round 6 finding 4: a maj7#5 voicing named as a slash triad", "C#3 F3 A3 C4", "F# major", 0, "F/C#", "C# F A C");
readCase("round 6 finding 4: a maj7#5 voicing named as a slash triad", "D#3 G3 B3 D4", "G# minor", 0, "G/D#", "D# G B D");
readCase("round 6 finding 4: the slash triad and its maj7#5 twin share their letters (A# C## E# over F#)", "F#3 A#3 D4 F4", "F# major", 0, "A#/F#", "F# A# C## E#", "F#maj7#5");
// The verifier's two sweeps, over every 3-4 note set holding C in 12 transpositions, in the 24 keys and with no key:
// augmented and 7#5 names on a double-accidental root (a triple-accidental #5): 8 before; any name with a triple or a
// double-accidental root: 277 tops and 433 runner-ups before (4-note sets in the 24 keys).
let sweepTops = 0, dblRootNames = 0, tripleNames = 0;
const sweepEx = [];
for (const key of [...KEYS24, null]) {
  for (let mask = 1; mask < 4096; mask++) {
    if (!(mask & 1)) continue;
    const pcs = [];
    for (let i = 0; i < 12; i++) if ((mask >> i) & 1) pcs.push(i);
    if (pcs.length < 3 || pcs.length > 4) continue;
    for (let t = 0; t < 12; t++) {
      const res = reader.read(pcs.map((p) => 48 + t + p), { key });
      if (res.readings.length) sweepTops++;
      for (const r of res.readings) {
        const c = chordOf(r.name);
        if (c && (Math.abs(c.root.acc) > 1 || (c.bass && Math.abs(c.bass.acc) > 1))) { dblRootNames++; if (sweepEx.length < 4) sweepEx.push(`${key}: ${r.name}`); }
        if (/###|bbb/.test(plainText(r.name))) tripleNames++;
      }
    }
  }
}
report.push(`round-6 verifier sweep: ${sweepTops} results; ${dblRootNames} names on a double-accidental root or bass, ${tripleNames} with a triple`);
check("round 6 findings 1-2 over the verifier's sweep: no name on a double-accidental root or bass and none with a triple, in the 24 keys and with no key", dblRootNames === 0 && tripleNames === 0 && sweepTops > 0,
  sweepEx.join(" | "));

// ------------------------------------------------------------------------ TN2 repair round 1: the dim7 and the key --
// Finding 1: the viio7 of every minor key wrote its 7th as an augmented 6th (B D F G# in C minor, B# D# F# G## in C# minor),
// so the chips and the staff put accidentals on notes the key already has. A dim7's 7th is now the cheaper of a diminished
// 7th and a 6th against the key (spell.js DIM7_SEVENTH). Finding 3: in G# minor the key's root is F## (a double accidental
// no root may take), so the chord's other tones are spelled from it and only the root is written G: G A# C# E.
// 24-key pin: in each minor key the viio7 (close, and spread over its root) needs no accidental on its 3rd, 5th or 7th in
// read()'s name, detect()'s chips and against the key signature; in each major key its 3rd and 5th need none and its 7th
// one at most (the borrowed b6: Ab in C major, never G#), and no chip anywhere takes a double accidental.
check("DIM7_SEVENTH is [6, 5] (a diminished 7th first), defaultSteps offers it in a dim7's shape only, and the page's spellForKey uses the same choice",
  S.DIM7_SEVENTH.join() === "6,5" && S.defaultSteps([0, 3, 6, 9], 9).join() === "6,5" && S.defaultSteps([0, 4, 7, 9], 9) === 5 && S.defaultSteps([0, 3, 7, 9], 9) === 5
  && /parsed\.base === "dim7" && 9 in steps\) steps\[9\] = \[6, 5\]/.test(pianoSrc));
{
  const sigAcc = (sp, sig) => { const a = sig.accidentals.find((x) => x.letter === sp.letter); return sp.acc === (a ? a.acc : 0) ? null : sp.acc; };
  const bad = [];
  let cases = 0;
  for (const key of KEYS24) {
    const k = NV.parseKey(key), sig = S.keySignature(key), lt = mod(k.tonic + 11, 12);
    for (const ms of [[48 + lt, 51 + lt, 54 + lt, 57 + lt], [36 + lt, 51 + lt, 57 + lt, 66 + lt]]) {
      cases++;
      const res = reader.read(ms, { key }), info = reader.detect(ms, k.bias, { key }), top = res.readings[0]?.name;
      const c = chordOf(top || "");
      if (!c || c.suffix !== "dim7" || info.name !== top || mod(LETTER_PC[c.root.letter] + c.root.acc, 12) !== lt) { bad.push(`${key}: read ${top}, detect ${info.name}`); continue; }
      const tone = (iv) => info.notes.find((n) => mod(n.midi - lt, 12) === iv);
      const [third, fifth, seventh] = [3, 6, 9].map(tone);
      const chips = info.pcNames.join(" ");
      const ok = sigAcc(third, sig) === null && sigAcc(fifth, sig) === null && info.notes.every((n) => Math.abs(n.acc) <= 1)
        && (k.mode === "minor" ? sigAcc(seventh, sig) === null
          : Math.abs(seventh.acc) <= 1 && (seventh.letter === mod(c.root.letter + 6, 7) || Math.abs(S.spellInterval(c.root, 9, 6).acc) >= 2));
      if (!ok) bad.push(`${key}: ${top} (${chips})`);
    }
  }
  check(`repair round 1 finding 1: the viio7 in each of the 24 keys (${cases} voicings): minor keys need no accidental on the 3rd, 5th or 7th; major keys none on the 3rd or 5th and one at most on the 7th`, bad.length === 0 && cases === 48, bad.join(" | "));
}
readCase("repair round 1 finding 1: C minor's viio7", "B2 D3 F3 Ab3", "C minor", 0, "Bdim7", "B D F Ab");
readCase("repair round 1 finding 1: E♭ minor's viio7 keeps the signature's C♭", "D3 F3 Ab3 Cb4", "Eb minor", 0, "Ddim7", "D F Ab Cb");
readCase("repair round 1 finding 1: A minor's viio7 is G# B D F, never E#", "G#2 B2 D3 F3", "A minor", 0, "G#dim7", "G# B D F");
readCase("repair round 1 finding 1: C# minor's viio7 writes a plain A, never G##", "C3 D#3 F#3 A3", "C# minor", 0, "B#dim7", "B# D# F# A");
readCase("repair round 1 finding 1: the lead-sheet C Eb Gb A with no key (Bbb would be a double)", "C3 Eb3 Gb3 A3", null, -1, "Cdim7", "C Eb Gb A");
readCase("repair round 1 finding 1: C#dim7 with no key writes its 7th Bb", "C#3 E3 G3 Bb3", null, 1, "C#dim7", "C# E G Bb");
readCase("repair round 1 finding 3: G# minor's viio7 keeps the key's A#, C# and E (the root F## is written G)", "G2 A#2 C#3 E3", "G# minor", 0, "Gdim7", "G A# C# E");
{
  const gm = S.spellChord({ rootPc: 7, tonesPc: [7, 10, 1, 4], steps: { 3: 2, 6: 4, 9: S.DIM7_SEVENTH.slice() }, key: "G# minor", suffix: "dim7" });
  check("repair round 1 finding 3: spellChord spells G# minor's leading-tone dim7 from the key's F## and writes the root G (score 2: G on another letter; A# C# E the key's own)",
    names(gm) === "G A# C# E" && gm.parts.root === "G" && gm.score === 2 && gm.candidates.some((x) => x.from === "F##" && x.score === 2)
    && cand(gm, "G").score > 2, `${names(gm)} ${JSON.stringify(gm.candidates)}`);
  const g7 = S.spellChord({ rootPc: 7, tonesPc: [7, 11, 3, 5], steps: { 4: 2, 8: 4, 10: 6 }, key: "G# minor", suffix: "7#5" });
  check("repair round 1: the F## candidate wins only on a strictly lower score (G7#5 in G# minor stays G B D# F: from F## it needs a forced note)",
    names(g7) === "G B D# F" && g7.candidates.some((x) => x.from === "F##" && x.forced === 1), `${names(g7)} ${JSON.stringify(g7.candidates)}`);
}

// ------------------------------------------------------------------------------------------ the E♭ minor Cb+(add9) --
readCase("ruling: Cb+(add9) in E♭ minor stays correct (C♭ is on the scale)", "Cb3 Eb3 G3 Db4", "Eb minor", 0, "Cb+(add9)", "Cb Eb G Db");
const cbAlso = reader.alsoOf(reader.read(midis("Eb3 G3 Cb4"), { key: "Eb minor" }), { kind: "chord", name: "B+/D#" }, 1000);
check("the E♭ minor augmented triad keeps C♭ in ALSO too (a template's B+/D# respelled)", !cbAlso || /^Cb/.test(cbAlso.name), cbAlso?.name);

// ----------------------------------------------------------------------------------------------- the full sweep --
// Rule 5's receipt: every set of 3-7 pitch classes, in three voicings (close; spread over its lowest pitch class; spread
// over its second), in the 24 keys and with no key at bias -1 and 1 (a key sets its own bias). Every read() reading's
// name (tops, runner-ups, rootless and template readings), its chord's tones as the one speller spells them, detect()'s
// info (name and chips) and the canvas ALSO name: 0 triple accidentals, and 0 double accidentals on a root or bass.
if (!quick) {
  const t0 = performance.now();
  let sets = 0, reads = 0, readings = 0, infos = 0, alsos = 0, tones = 0, triples = 0, dblRoot = 0, dblBass = 0, oddTone = 0, oddOutside = 0;
  const ODD_NAMES = ["B#", "E#", "Cb", "Fb"];
  const ex = [];
  const bad = (what, where) => { if (ex.length < 6) ex.push(`${what}: ${where}`); };
  const contexts = [...KEYS24.map((k) => [k, 0]), [null, -1], [null, 1]];
  const nameFaults = (name, where) => {
    const c = chordOf(name);
    if (!c) return;
    if (Math.abs(c.root.acc) > 1) { dblRoot++; bad("a double-accidental root", where); }
    if (c.bass && Math.abs(c.bass.acc) > 1) { dblBass++; bad("a double-accidental bass", where); }
    if (Math.abs(c.root.acc) > 2 || (c.bass && Math.abs(c.bass.acc) > 2)) { triples++; bad("a triple", where); }
  };
  for (let mask = 1; mask < 4096; mask++) {
    const pcs = [];
    for (let bit = 0; bit < 12; bit++) if (mask & (1 << bit)) pcs.push(bit);
    if (pcs.length < 3 || pcs.length > 7) continue;
    sets++;
    const up = (list) => list.map((p, i) => 60 + p + (i % 2 ? 12 : 0));
    const voicings = [pcs.map((p) => 48 + p), [36 + pcs[0], ...up(pcs.slice(1))], [36 + pcs[1], ...up([pcs[0], ...pcs.slice(2)])]];
    for (const ms of voicings) {
      const heard = new Set(ms.map((m) => mod(m, 12)));
      for (const [key, bias] of contexts) {
        const where = `${ms.join(",")} ${key ?? "bias " + bias}`;
        const res = reader.read(ms, { key, keyBias: bias });
        reads++;
        for (const r of res.readings) {
          readings++;
          nameFaults(r.name, `${where}: ${r.name}`);
          // the chord's tones as the speller spells them for this name (its root and bass fixed from the name)
          const c = chordOf(r.name);
          if (!c) continue;
          const p = parseSuffix(r.suffix), steps = { ...p.tones };
          if (p.base === "dim7" && 9 in steps) steps[9] = S.DIM7_SEVENTH.slice();
          // rule 3: a bass on B#, E#, Cb or Fb off the key's scale is only ever a chord tone on the chord's letters
          if (c.bass && ODD_NAMES.includes(S.nameOf(c.bass))) {
            const inside = r.path === "template" ? mod(r.bass - r.root, 12) in steps : r.path !== "slash";
            const s0 = key ? NV.spellInKey(c.bass, key) : null, onScale = !!s0 && s0.inScale && s0.letter === c.bass.letter && s0.acc === c.bass.acc;
            if (!onScale) { if (inside) oddTone++; else { oddOutside++; bad("an odd bass outside the chord, off the key's scale", `${where}: ${r.name}`); } }
          }
          const tonesPc = Object.keys(steps).map(Number).filter((iv) => iv === 0 || heard.has(mod(r.root + iv, 12))).map((iv) => r.root + iv);
          const s = S.spellChord({ rootPc: r.root, tonesPc, steps, bassPc: r.bass, key, bias, rootSp: c.root });
          for (const t of s.tones) { tones++; if (Math.abs(t.acc) > 2) { triples++; bad("a triple tone", `${where}: ${r.name} ${t.name}`); } }
        }
        const info = reader.detect(ms, biasOf(key, bias), { key });
        infos++;
        if (info.kind === "chord") nameFaults(info.name, `${where}: detect ${info.name}`);
        for (const n of info.notes || []) if (Math.abs(n.acc) > 2) { triples++; bad("a triple chip", `${where}: detect ${info.name} ${n.name}`); }
        if (res.kind === "chord") {
          const also = reader.alsoOf(res, Templates.detect(ms, biasOf(key, bias)), 1000);
          if (also) { alsos++; nameFaults(also.name, `${where}: ALSO ${also.name}`); }
        }
      }
    }
  }
  const secs = (performance.now() - t0) / 1000;
  report.push(`full sweep: ${sets} pitch-class sets x 3 voicings x ${contexts.length} contexts = ${reads} reads, ${readings} readings (${tones} spelled tones), ${infos} detect infos, ${alsos} ALSO names in ${secs.toFixed(1)} s; `
    + `${triples} triple accidentals, ${dblRoot} double-accidental roots, ${dblBass} double-accidental basses; basses on B#, E#, Cb or Fb off the key's scale: ${oddTone} chord tones, ${oddOutside} outside the chord`);
  check("rule 5 receipt: the full synthetic sweep (every 3-7 pitch-class set, three voicings, 24 keys and no key at both biases) gives 0 triple accidentals and 0 double accidentals on roots and basses",
    sets === 3223 && reads === 3223 * 3 * 26 && triples === 0 && dblRoot === 0 && dblBass === 0 && alsos > 0, ex.join(" | "));
  check("rule 3 over the full sweep: a bass outside the chord is never B#, E#, Cb or Fb off the key's scale, in the 24 keys and with no key", oddOutside === 0 && oddTone > 0, ex.join(" | "));
}

console.log(report.join("\n"));
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
