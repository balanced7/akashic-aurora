// Node tests for arsenal/web/piano/nashville.js. Zero dependencies:  node tests/nashville_js.test.mjs
// Runs every case in tests/fixtures/nashville_cases.json (the Python twin runs the same file), checks that
// nashville(Theory.detect(...)) agrees with nashvilleFromName(info.name) using the exact THEORY block shipped in
// piano.js, that scoreKeys matches Theory.estimateKey, drives the key tracker through the scores the verifiers used,
// and checks that piano.js spells chord names in the shown key.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createKeyTracker, nashville, nashvilleFromName, parseChord, parseKey, rankKeys, scoreKeys, spellInKey, TONE_STEPS }
  from "../arsenal/web/piano/nashville.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
let pass = 0, fail = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want),
  `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);

// ------------------------------------------------------------------ fixture --
const { cases } = JSON.parse(readFileSync(here("./fixtures/nashville_cases.json"), "utf8"));
check("fixture has at least 100 cases", cases.length >= 100, String(cases.length));
for (const [i, c] of cases.entries()) {
  const r = nashvilleFromName(c.chord, c.key, c.opts);
  eq(`case ${i} ${c.chord} in ${c.key} ${JSON.stringify(c.opts)}`, r && { text: r.text, diatonic: r.diatonic }, c.expected);
}

// ------------------------------------------------------------ result shape --
eq("shape G7/B", nashvilleFromName("G7/B", "C major"), {
  text: "5^7/7", degree: 5, acc: 0, root: "5", suffix: "7", bass: { degree: 7, acc: 0, text: "7" }, upper: null,
  diatonic: true, kind: "chord" });
eq("shape F#-A", nashvilleFromName("F#-A", "C major"), {
  text: "#4-6", degree: 4, acc: 1, root: "#4", suffix: "", bass: null, upper: { degree: 6, acc: 0, text: "6" },
  diatonic: false, kind: "interval" });
eq("key object without a name", nashvilleFromName("C7", { tonic: 5, mode: "major" })?.text, "5^7");
eq("no key", nashvilleFromName("C", null), null);
eq("unreadable key", nashvilleFromName("C", "C lydian"), null);
eq("nashville(null info)", nashville(null, "C major"), null);
eq("parseChord 6/9 over a bass", parseChord("C6/9/E"),
  { kind: "chord", root: { letter: 0, acc: 0 }, suffix: "6/9", bass: { letter: 2, acc: 0 }, upper: null });
eq("parseChord G5 reads as a power chord", parseChord("G5").kind, "chord");
eq("parseChord G5 as a note on request", parseChord("G5", "note").kind, "note");
eq("parseKey Eb minor flats, as estimateKey", parseKey("Eb minor"), { tonic: 3, mode: "minor", name: "Eb minor", bias: -1 });
eq("parseKey spelled names decide their bias", [parseKey("D# minor").bias, parseKey("Gb major").bias, parseKey("F# major").bias], [1, -1, 1]);

// ------------------------------------------------- the THEORY block in piano.js --
const src = readFileSync(here("../arsenal/web/piano.js"), "utf8");
const a = src.indexOf("// ===== THEORY BEGIN"), b = src.indexOf("// ===== THEORY END");
check("theory markers present", a >= 0 && b > a);
const Theory = new Function(src.slice(a, b) + "\nreturn Theory;")();

// scoreKeys is estimateKey's scan, all 24 keys; parseKey reads every name it writes.
let seed = 7;
const rand7 = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
let named = 0;
for (let n = 0; n < 2000; n++) {
  const hist = Array.from({ length: 12 }, () => (rand7() < 0.3 ? 0 : rand7() * 6));
  const est = Theory.estimateKey(hist), all = scoreKeys(hist);
  if (all.length !== 24) { check("scoreKeys returns 24 keys", false); break; }
  if (!est) continue;
  named++;
  const top = all[0];
  check(`scoreKeys[0] is estimateKey (${n})`, top.name === est.name && top.bias === est.bias && Math.abs(top.r - est.r) < 1e-12,
        `${JSON.stringify(top)} vs ${JSON.stringify(est)}`);
}
check("estimateKey named enough random histograms", named > 200, String(named));
for (const k of scoreKeys([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])) {
  eq(`parseKey ${k.name}`, parseKey(k.name), { tonic: k.tonic, mode: k.mode, name: k.name, bias: k.bias });
}

// nashville(detect(notes), key) and nashvilleFromName(info.name, key.name) agree. A single pitch class sounded in
// octaves is named without an octave ("E") and "G5"/"C6"/"C7" read as chords by name, so notes pass kind "note".
const SHAPES = [[0, 4, 7], [0, 3, 7], [0, 3, 6], [0, 4, 8], [0, 5, 7], [0, 2, 7], [0, 4, 7, 10], [0, 4, 7, 11], [0, 3, 7, 10],
  [0, 3, 6, 10], [0, 3, 6, 9], [0, 4, 7, 9], [0, 2, 4, 7], [0, 4, 10, 14], [0, 3, 7, 14], [0, 7], [0, 4], [0, 3], [0, 6], [0], [0, 12],
  [0, 1, 2], [0, 1, 6, 7]];  // the last two are clusters
let agreed = 0;
const kinds = new Set();
for (const key of scoreKeys([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])) {
  for (let root = 36; root < 48; root++) {
    for (const shape of SHAPES) {
      for (const inversion of [0, 1, 2]) {
        let notes = shape.map((x) => root + 12 + x);
        if (inversion && shape.length > 2) notes = [notes[inversion] - 12, ...notes];
        const info = Theory.detect(notes, key.bias);
        for (const opts of [{}, { minor: "relative", minorMark: "-" }]) {
          const direct = nashville(info, key, opts);
          const byName = nashvilleFromName(info.name, key.name, info.kind === "note" ? { ...opts, kind: "note" } : opts);
          kinds.add(info.kind);
          if (JSON.stringify(direct) !== JSON.stringify(byName)) {
            check(`agree ${info.name} in ${key.name} ${JSON.stringify(opts)}`, false, `${JSON.stringify(direct)} vs ${JSON.stringify(byName)}`);
          } else agreed++;
        }
      }
    }
  }
}
check("agreement covered every kind", ["note", "interval", "chord", "cluster"].every((k) => kinds.has(k)), [...kinds].join());
check("agreement ran", agreed > 20000, String(agreed));
eq("a note in octave 4 needs no kind", nashvilleFromName(Theory.detect([64], 0).name, "C major")?.kind, "note");

// Every suffix detect can produce has a triad family: on the tonic of a major key only minor, diminished and
// augmented families are flagged.
for (const suffix of new Set([...Theory.TEMPLATES.map((t) => t.suffix), "5"])) {
  const minorish = suffix.startsWith("m") && !suffix.startsWith("maj");
  const flagged = minorish || ["dim", "dim7", "aug", "7#5", "maj7#5"].includes(suffix);
  eq(`family of "${suffix}"`, nashvilleFromName("C" + suffix, "C major")?.diatonic, !flagged);
}

// Both minor numberings flag the same chords.
for (const c of cases.filter((x) => x.key && x.key.endsWith("minor") && x.expected)) {
  const t = nashvilleFromName(c.chord, c.key, { ...c.opts, minor: "tonic" });
  const r = nashvilleFromName(c.chord, c.key, { ...c.opts, minor: "relative" });
  eq(`minor numberings flag ${c.chord} in ${c.key} alike`, t.diatonic, r.diatonic);
}

// ------------------------------------------------- chord names in the shown key --
// spellInKey reads a spelling the way the numbers do; piano.js spellForKey spells the chord name and chips with it.
eq("spellInKey: Ab reads G# in C# minor", spellInKey({ letter: 5, acc: -1 }, "C# minor"), { letter: 4, acc: 1, inScale: true });
eq("spellInKey: C reads B#, C# minor's leading tone", spellInKey({ letter: 0, acc: 0 }, "C# minor", { suffix: "dim7" }),
   { letter: 6, acc: 1, inScale: true });
eq("spellInKey: an F# major chord in C major reads Gb (b5)", spellInKey({ letter: 3, acc: 1 }, "C major", { suffix: "" }),
   { letter: 4, acc: -1, inScale: false });
eq("spellInKey: the note F# in C major stays F# (#4)", spellInKey({ letter: 3, acc: 1 }, "C major"), { letter: 3, acc: 1, inScale: false });
eq("spellInKey without a key", spellInKey({ letter: 0, acc: 0 }, null), null);

const sa = src.indexOf("const ODD_NAMES"), sb = src.indexOf("\n}\n", src.indexOf("function spellForKey"));
check("spellForKey present in piano.js", sa >= 0 && sb > sa);
const theoryUi = { minor: "tonic" };
const spellForKey = new Function("Theory", "spellInKey", "theoryUi", src.slice(sa, sb + 2) + "\nreturn spellForKey;")(Theory, spellInKey, theoryUi);
const QUALITY = { maj: [0, 4, 7], min: [0, 3, 7], dom7: [0, 4, 7, 10], dim: [0, 3, 6], dim7: [0, 3, 6, 9] };
const LETTERS = "CDEFGAB";
let spelled = 0;
for (const key of scoreKeys([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])) {
  const diatonic = key.mode === "major"
    ? [[0, "maj"], [2, "min"], [4, "min"], [5, "maj"], [7, "dom7"], [9, "min"], [11, "dim"]]
    : [[0, "min"], [2, "dim"], [3, "maj"], [5, "min"], [7, "min"], [7, "dom7"], [8, "maj"], [10, "maj"], [11, "dim7"]];
  for (const [semis, quality] of diatonic) {
    const root = (key.tonic + semis) % 12;
    const info = spellForKey(Theory.detect([36 + root, ...QUALITY[quality].map((x) => 60 + root + x)], key.bias), key);
    const n = nashville(info, key);
    const letterDegree = (LETTERS.indexOf(info.name[0]) - LETTERS.indexOf(key.name[0]) + 7) % 7 + 1;
    const chips = info.notes.every((x) => x.name === Theory.nameOf(x) && Theory.pcOf(x) === x.midi % 12);
    check(`${info.name} in ${key.name} is named with the key's letters (${n.text})`, letterDegree === n.degree && chips);
    spelled++;
  }
}
check("every diatonic chord of the 24 keys was spelled", spelled === 24 * 8, String(spelled));
const named_ = (notes, keyName) => {
  const key = parseKey(keyName);
  const info = spellForKey(Theory.detect(notes, key.bias), key);
  return [info.name, nashville(info, key).text];
};
eq("G#7 beside 5^7 in C# minor (detect alone wrote Ab7)", named_([44, 60, 63, 66], "C# minor"), ["G#7", "5^7"]);
eq("B#dim7 beside 7°7 in C# minor", named_([48, 51, 54, 57], "C# minor"), ["B#dim7", "7°7"]);
eq("Ebm beside 1m in Eb minor (detect alone wrote D#m)", named_([51, 54, 58], "Eb minor"), ["Ebm", "1m"]);
eq("A#m beside 3m in F# major", named_([46, 61, 65], "F# major"), ["A#m", "3m"]);
eq("a chromatic chord keeps a plain name: B beside b7 in Db major, not Cb", named_([47, 63, 66], "Db major"), ["B", "b7"]);
eq("Gb beside b5 in C major", named_([42, 58, 61], "C major"), ["Gb", "b5"]);
eq("spellForKey without a key leaves detect's name", spellForKey(Theory.detect([44, 60, 63, 66], 1), null).name, "Ab7");
// An interval's top note keeps plain letters where moving it with the root would need a double accidental, as a slash
// chord's bass does (the page named D7/F#'s F#-A in Bb major Gb-Bbb). The number reads from the root either way.
eq("F#-A in Bb major is Gb-A beside b6-7, not Gb-Bbb", named_([54, 57], "Bb major"), ["Gb-A", "b6-7"]);
{
  const keys = [...scoreKeys([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]).map((k) => k.name), "Gb major", "C# major", "Cb major", "D# minor", "A# minor", "Ab minor"];
  let intervals = 0;
  const doubled = [];
  for (const key of keys.map(parseKey)) {
    for (let lo = 0; lo < 12; lo++) {
      for (let size = 1; size < 12; size++) {
        const info = spellForKey(Theory.detect([60 + lo, 60 + lo + size], key.bias), key);
        if (info.kind !== "interval") continue;
        intervals++;
        for (const sp of [info.root, info.upper]) {
          const s = spellInKey(sp, key);
          if (Math.abs(sp.acc) > 1 && !(s && s.inScale && s.letter === sp.letter && s.acc === sp.acc)) doubled.push(`${info.name} in ${key.name}`);
        }
      }
    }
  }
  // every pair of pitch classes in every key but the fifths, which detect names as power chords (C5)
  check(`no interval is spelled with a double accidental off the key's scale (${intervals} checked)`, intervals >= 30 * 12 * 10 && doubled.length === 0,
        doubled.slice(0, 6).join(", "));
}

// --------------------------------------------------------------- key tracker --
// Performances as a pianist plays them, seeded so every run is the same. The histogram is built exactly like piano.js's
// noteOn (pcHistory *= exp(-dt / 12) at each note-on; pcHistory[pc] += 0.5 + vel / 127). Every note sounds from its
// strike to the end of its chord, and the tracker is handed the sounding chord (Theory.detect with the shown key's
// bias), as piano.js tickKey() hands it lastInfo.
let rng = 1;
const rand = () => ((rng = (rng * 16807) % 2147483647) / 2147483647);
const NOTE = { C: 0, "C#": 1, Db: 1, D: 2, Eb: 3, E: 4, F: 5, "F#": 6, G: 7, "G#": 8, Ab: 8, A: 9, Bb: 10, B: 11 };
const QUAL = { "": [0, 4, 7], m: [0, 3, 7], "7": [0, 4, 7, 10], maj7: [0, 4, 7, 11], m7: [0, 3, 7, 10], sus4: [0, 5, 7], "5": [0, 7] };
const rep = (plan, n) => Array.from({ length: n }, () => plan).flat();
const scaleOf = (tonic, steps) => steps.map((s) => (tonic + s) % 12);
const MAJOR = [0, 2, 4, 5, 7, 9, 11], AEOLIAN = [0, 2, 3, 5, 7, 8, 10], MINOR_PENT = [0, 3, 5, 7, 10];

// Chord symbols voiced three ways: "block" (the triad on every beat, the bass on 1 and 3), "arp" (eighth-note
// arpeggios over the bass), "comp" (jazz: the root, then the 3rd, 5th and 7th on 1 and the and of 2, the fifth on 3).
// A melody takes a chord tone about two times in three, else a scale note.
function perform(plan, { bpm, style, melodyScale = null, jitter = 0.02 }) {
  const beat = 60 / bpm, ons = [];
  let t = 0;
  for (const [sym, nBeats] of plan) {
    const m = /^([A-G][#b]?)(maj7|m7|7|m|sus4|5)?(?:\/([A-G][#b]?))?$/.exec(sym);
    const root = NOTE[m[1]], pcs = QUAL[m[2] || ""].map((x) => (root + x) % 12), bass = m[3] ? NOTE[m[3]] : root;
    const nb = nBeats || 4, end = t + nb * beat;
    const rh = pcs.map((pc) => 60 + pc).sort((x, y) => x - y);
    const push = (tt, n, v) => ons.push({ t: Math.max(t, tt), n, v, off: end });
    if (style === "block") {
      for (let k = 0; k < nb; k++) {
        const tt = t + k * beat;
        if (k % 2 === 0) { push(tt + (rand() - 0.5) * jitter, 36 + bass, 80 + rand() * 25); if (rand() < 0.4) push(tt, 48 + bass, 70); }
        for (const n of rh) push(tt + (rand() - 0.5) * jitter, n, 50 + rand() * 30);
      }
    } else if (style === "arp") {
      push(t + (rand() - 0.5) * jitter, 36 + bass, 95);
      const arp = [...rh, rh[0] + 12, ...rh.slice(1).reverse()];
      for (let k = 0; k < nb * 2; k++) push(t + k * beat / 2 + (rand() - 0.5) * jitter, arp[k % arp.length] - 12, 55 + rand() * 25);
    } else {
      const shell = pcs.slice(1).map((pc) => 52 + ((pc - 4 + 12) % 12));
      push(t + (rand() - 0.5) * jitter, 36 + bass, 85);
      for (const off of [0, 1.5]) if (off < nb) for (const n of shell) push(t + off * beat + (rand() - 0.5) * jitter, n, 55 + rand() * 25);
      if (nb >= 4) push(t + 2 * beat, 43 + bass, 70);
    }
    if (melodyScale) {
      const count = 2 + Math.floor(rand() * 2);
      for (let k = 0; k < count; k++) {
        const pool = rand() < 0.65 ? pcs : melodyScale;
        const pc = pool[Math.floor(rand() * pool.length)];
        push(t + (k * nb * beat) / count + (rand() - 0.5) * jitter, 72 + pc, 75 + rand() * 30);
      }
    }
    t = end;
  }
  return { ons: ons.sort((x, y) => x.t - y.t), end: t };
}
// Hand voicings: [[[beat, midi, velocity], ...], beats] per chord.
function hand(plan, bpm) {
  const beat = 60 / bpm, ons = [];
  let t = 0;
  for (const [evs, beats] of plan) {
    const end = t + beats * beat;
    for (const [b_, n, v] of evs) ons.push({ t: Math.max(t, t + b_ * beat + (rand() - 0.5) * 0.02), n, v: Math.max(1, Math.min(127, v + (rand() - 0.5) * 20)), off: end });
    t = end;
  }
  return { ons: ons.sort((x, y) => x.t - y.t), end: t };
}
const md = (name, octave) => 12 * (octave + 1) + NOTE[name];
const triad = (root, third, fifth, bass) => [[0, md(bass, 2), 95], [0, md(root, 4), 70], [0, md(third, 4), 70], [0, md(fifth, 4), 70],
  [2, md(bass, 2), 85], [2, md(root, 4), 60], [2, md(third, 4), 60], [2, md(fifth, 4), 60]];
const F_BLOCK = [  // F/A C/G Dm Bbmaj7 in block chords with F/A first, the voicing that showed A minor for 12 s
  [[[0, md("A", 2), 95], [0, md("F", 4), 70], [0, md("A", 4), 70], [0, md("C", 5), 70], [2, md("A", 2), 85], [2, md("F", 4), 60], [2, md("A", 4), 60], [2, md("C", 5), 60], [0, md("A", 5), 90]], 4],
  [[[0, md("G", 2), 95], [0, md("E", 4), 70], [0, md("G", 4), 70], [0, md("C", 5), 70], [2, md("G", 2), 85], [2, md("E", 4), 60], [2, md("G", 4), 60], [2, md("C", 5), 60], [0, md("G", 5), 90]], 4],
  [[[0, md("D", 2), 95], [0, md("D", 4), 70], [0, md("F", 4), 70], [0, md("A", 4), 70], [2, md("D", 2), 85], [2, md("D", 4), 60], [2, md("F", 4), 60], [2, md("A", 4), 60], [0, md("F", 5), 90]], 4],
  [[[0, md("Bb", 2), 95], [0, md("D", 4), 70], [0, md("F", 4), 70], [0, md("A", 4), 70], [2, md("Bb", 2), 85], [2, md("D", 4), 60], [2, md("F", 4), 60], [2, md("A", 4), 60], [0, md("D", 5), 90]], 4]];
const SHELLS = [  // Cm7 F7 Bbmaj7 Bbmaj7: the root, then 3rd and 7th shells, the voicing that read Eb major for 88 s
  [[[0, md("C", 2), 90], [0, md("Eb", 4), 70], [0, md("Bb", 4), 70], [1.5, md("Eb", 4), 60], [1.5, md("Bb", 4), 60]], 4],
  [[[0, md("F", 2), 90], [0, md("A", 3), 70], [0, md("Eb", 4), 70], [1.5, md("A", 3), 60], [1.5, md("Eb", 4), 60]], 4],
  [[[0, md("Bb", 2), 90], [0, md("D", 4), 70], [0, md("A", 4), 70], [1.5, md("D", 4), 60], [1.5, md("A", 4), 60]], 4],
  [[[0, md("Bb", 2), 90], [0, md("D", 4), 70], [0, md("A", 4), 70], [2.5, md("D", 4), 60], [2.5, md("A", 4), 60]], 4]];
const D_ROCK = [[triad("D", "F#", "A", "D"), 4], [triad("C", "E", "G", "C"), 4], [triad("G", "B", "D", "G"), 4], [triad("D", "F#", "A", "D"), 4]];
const HARM_LIGHT = [[triad("A", "C", "E", "A"), 4], [triad("D", "F", "A", "D"), 4],  // the E chord's G# struck once
  [[[0, md("E", 2), 95], [0, md("E", 4), 70], [0, md("G#", 4), 70], [0, md("B", 4), 70], [2, md("E", 2), 85], [2, md("E", 4), 60], [2, md("B", 4), 60]], 4],
  [triad("A", "C", "E", "A"), 4]];
const AEOL_AM = [[triad("A", "C", "E", "A"), 4], [triad("G", "B", "D", "G"), 4], [triad("F", "A", "C", "F"), 4], [triad("G", "B", "D", "G"), 4]];

// Arpeggios at 80 bpm (a bar is 3 s): bass on beat 1, eight eighth notes, two melody notes.
const BAR = 3.0;
const PROGRESSIONS = {
  F: [{ bass: 45, arp: [53, 57, 60, 65, 69, 65, 60, 57], mel: [77, 76] },   // F/A
      { bass: 43, arp: [52, 55, 60, 64, 67, 64, 60, 55], mel: [76, 74] },   // C/G
      { bass: 38, arp: [50, 53, 57, 62, 65, 62, 57, 53], mel: [74, 72] },   // Dm
      { bass: 46, arp: [50, 53, 57, 58, 62, 58, 57, 53], mel: [74, 69] }],  // Bbmaj7
  D: [{ bass: 38, arp: [50, 54, 57, 62, 66, 62, 57, 54], mel: [74, 73] },   // D
      { bass: 37, arp: [49, 52, 57, 61, 64, 61, 57, 52], mel: [76, 73] },   // A/C#
      { bass: 35, arp: [47, 50, 54, 59, 62, 59, 54, 50], mel: [74, 71] },   // Bm
      { bass: 43, arp: [47, 50, 55, 59, 62, 59, 55, 50], mel: [71, 74] }],  // G
  HARM: [{ bass: 45, arp: [57, 60, 64, 69, 72, 69, 64, 60], mel: [76, 72] },  // Am
         { bass: 38, arp: [50, 53, 57, 62, 65, 62, 57, 53], mel: [74, 69] },  // Dm
         { bass: 40, arp: [52, 56, 59, 64, 68, 64, 59, 56], mel: [71, 68] },  // E
         { bass: 45, arp: [57, 60, 64, 69, 72, 69, 64, 60], mel: [69, 72] }], // Am
  AEOLIAN: [{ bass: 45, arp: [57, 60, 64, 69, 72, 69, 64, 60], mel: [76, 72] },  // Am
            { bass: 41, arp: [53, 57, 60, 65, 69, 65, 60, 57], mel: [72, 69] },  // F
            { bass: 48, arp: [48, 52, 55, 60, 64, 60, 55, 52], mel: [67, 64] },  // C
            { bass: 43, arp: [47, 50, 55, 59, 62, 59, 55, 50], mel: [71, 67] }], // G
};
function score(plan) {
  const ons = [];
  let bar = 0;
  for (const [name, bars] of plan) {
    for (let j = 0; j < bars; j++, bar++) {
      const t = bar * BAR, c = PROGRESSIONS[name][j % 4], off = t + BAR;
      ons.push({ t, n: c.bass, v: 95, off });
      c.arp.forEach((n, i) => ons.push({ t: t + i * BAR / 8, n, v: 58 + ((i * 17 + bar * 7) % 26), off }));
      ons.push({ t, n: c.mel[0], v: 100, off }, { t: t + BAR / 2, n: c.mel[1], v: 88, off });
    }
  }
  return { ons: ons.sort((x, y) => x.t - y.t), end: bar * BAR };
}
// A loop of block chords with a melody, a pause, then the loop picked up again from the next bar.
const LOOPS = {
  "D A/C# Bm G": { bar: 2.4, key: "D major", P: [{ bass: [38, 50], rh: [57, 62, 66], mel: [74, 78] }, { bass: [37, 49], rh: [57, 61, 64], mel: [73, 76] },
    { bass: [35, 47], rh: [54, 59, 62], mel: [71, 74] }, { bass: [31, 43], rh: [55, 59, 62], mel: [71, 79] }] },
  "F/A C/G Dm Bbmaj7": { bar: 3.0, key: "F major", P: [{ bass: [45], rh: [53, 57, 60, 65], mel: [77, 76] }, { bass: [43], rh: [52, 55, 60, 64], mel: [76, 74] },
    { bass: [38], rh: [50, 53, 57, 62], mel: [74, 72] }, { bass: [46], rh: [50, 53, 57, 58], mel: [74, 69] }] },
  "C G Am F": { bar: 2.4, key: "C major", P: [{ bass: [36, 48], rh: [60, 64, 67], mel: [72, 76] }, { bass: [43, 55], rh: [59, 62, 67], mel: [74, 71] },
    { bass: [45, 57], rh: [60, 64, 69], mel: [72, 76] }, { bass: [41, 53], rh: [60, 65, 69], mel: [72, 77] }] },
};
function pauseScore(name, bars, pauseSec, resumeBars, barSec = LOOPS[name].bar) {
  const { P } = LOOPS[name];
  const ons = [];
  const phrase = (start, from, count) => {
    for (let i = 0; i < count; i++) {
      const t = start + i * barSec, c = P[(from + i) % 4], off = t + barSec * 0.95;
      c.bass.forEach((n) => ons.push({ t, n, v: 90, off })); c.rh.forEach((n) => ons.push({ t, n, v: 70, off }));
      ons.push({ t: t + 0.25 * barSec, n: c.mel[0], v: 95, off }, { t: t + 0.5 * barSec, n: c.mel[1], v: 88, off }, { t: t + 0.75 * barSec, n: c.mel[0], v: 80, off });
    }
  };
  phrase(0.5, 0, bars);
  const resumeAt = 0.5 + bars * barSec + pauseSec;
  phrase(resumeAt, bars % 4, resumeBars);
  return { ons: ons.sort((x, y) => x.t - y.t), end: resumeAt + resumeBars * barSec + 1 };
}

// cadence "note": update on every note-on (as currentInfo() after a note). "tick": update at 10 Hz (piano.js's).
// offset: added to the tracker's clock, so a second performance fed to the same tracker runs forward in time.
function play(perf, cadence, tracker = createKeyTracker(), offset = 0) {
  const hist = new Array(12).fill(0), timeline = [];
  let at = 0, i = 0, last, key = null, valid = true;
  const step = (t) => {
    const notes = [];
    for (let j = 0; j < i; j++) if (perf.ons[j].off > t + 1e-9) notes.push(perf.ons[j].n);
    const s = tracker.update(hist, t + offset, notes.length ? Theory.detect(notes, key ? key.bias : 0) : null);
    key = s.key;
    if (!["sure", "fair", "unsure"].includes(s.confidence)) valid = false;
    const name = s.key ? s.key.name : null;
    if (name !== last) { timeline.push({ t: +t.toFixed(2), key: name, confidence: s.confidence }); last = name; }
  };
  for (let t = 0; t <= perf.end + 1e-9; t = +(t + 0.1).toFixed(2)) {
    while (i < perf.ons.length && perf.ons[i].t <= t + 1e-9) {
      const e = perf.ons[i++];
      const et = Math.max(e.t, at);
      const f = Math.exp(-(et - at) / 12);
      for (let k = 0; k < 12; k++) hist[k] *= f;
      at = et;
      hist[e.n % 12] += 0.5 + Math.max(1, Math.min(127, e.v)) / 127;
      if (cadence === "note") step(et);
    }
    if (cadence === "tick") step(t);
  }
  check(`confidence is always sure, fair or unsure (${cadence})`, valid);
  return { timeline, tracker, hist };
}
const shown = (timeline) => timeline.filter((x) => x.key !== null);
const fmt = (timeline) => timeline.map((x) => `${x.t}s ${x.key}`).join(" -> ");
const report = [];

const MODULATION = 32 * BAR;  // 96 s
for (const cadence of ["note", "tick"]) {
  const { timeline, tracker, hist } = play(score([["F", 32], ["D", 24]]), cadence);
  const keys = shown(timeline);
  report.push(`F32 then D24 (${cadence}): ${fmt(keys)}`);
  check(`F major first, by FIRST_WAIT (${cadence})`, keys[0]?.key === "F major" && keys[0].t <= 17, JSON.stringify(keys[0]));
  check(`one key before the modulation (${cadence})`, keys.filter((x) => x.t < MODULATION).length === 1, fmt(keys));
  const after = keys.filter((x) => x.t >= MODULATION);
  check(`D major within 15 s of the modulation, and nothing else (${cadence})`,
        after.length === 1 && after[0].key === "D major" && after[0].t <= MODULATION + 15, fmt(after));

  // Silence holds the key: the same histogram for a minute, then an emptied one.
  let s;
  for (let t = 168; t < 228; t += 0.1) s = tracker.update(hist, t);
  eq(`key holds through silence (${cadence})`, s.key?.name, "D major");
  s = tracker.update(new Array(12).fill(0), 229);
  eq(`key holds through an emptied histogram (${cadence})`, s.key?.name, "D major");

  // lock pins a key through contrary evidence; unlocking lets the evidence win it back after the hold.
  const pinned = play(score([["D", 8]]), cadence, createKeyTracker());
  s = pinned.tracker.lock("Eb minor");
  eq(`lock shows the pinned key (${cadence})`, [s.key?.name, s.locked], ["Eb minor", true]);
  for (let t = 0; t < 20; t += 0.1) s = pinned.tracker.update(pinned.hist, 24 + t);
  eq(`locked key survives contrary evidence (${cadence})`, [s.key?.name, s.locked], ["Eb minor", true]);
  s = pinned.tracker.lock(null);
  eq(`unlock keeps the key until evidence moves it (${cadence})`, [s.key?.name, s.locked], ["Eb minor", false]);
  const resumed = play(score([["D", 8]]), cadence, pinned.tracker, 50);
  eq(`after unlock D major playing wins it back (${cadence})`, shown(resumed.timeline).at(-1)?.key, "D major");
}

// The verifiers' scores (2026-09-14). Each shows exactly one key, never another, at the cadences and seeds listed.
const BOTH = ["tick", "note"];
const SCENARIOS = [
  ["F/A C/G Dm Bbmaj7 block, F/A first (showed A minor for 12 s)", () => hand(rep(F_BLOCK, 8), 80), "F major", BOTH, 3],
  ["F/A C/G Dm Bbmaj7 arpeggios with a melody", () => perform(rep([["F/A"], ["C/G"], ["Dm"], ["Bbmaj7"]], 8), { bpm: 80, style: "arp", melodyScale: scaleOf(5, MAJOR) }), "F major", BOTH, 3],
  ["Cm7 F7 Bbmaj7 Bbmaj7 in shells (read Eb major for 88 s)", () => hand(rep(SHELLS, 12), 132), "Bb major", BOTH, 3],
  ["Cm7 F7 Bbmaj7 Bbmaj7 comped (read F major, the key of V)", () => perform(rep([["Cm7"], ["F7"], ["Bbmaj7"], ["Bbmaj7"]], 12), { bpm: 132, style: "comp", melodyScale: scaleOf(10, MAJOR) }), "Bb major", ["tick"], 3],
  ["Cm7 F7 Bbmaj7 Gm7 comped", () => perform(rep([["Cm7"], ["F7"], ["Bbmaj7"], ["Gm7"]], 12), { bpm: 132, style: "comp", melodyScale: scaleOf(10, MAJOR) }), "Bb major", BOTH, 3],
  ["D C G D block triads (toggled D and G every 4.4 s)", () => hand(rep(D_ROCK, 12), 110), "D major", BOTH, 3],
  ["D C G D with a pentatonic melody", () => perform(rep([["D"], ["C"], ["G"], ["D"]], 12), { bpm: 110, style: "block", melodyScale: scaleOf(2, MINOR_PENT) }), "D major", BOTH, 3],
  ["Am Dm E Am with one G# per E bar (read A major from 12 s)", () => hand(rep(HARM_LIGHT, 12), 90), "A minor", BOTH, 3],
  ["Am Dm E Am arpeggios", () => score([["HARM", 24]]), "A minor", BOTH, 1],
  ["Am F C G block (a key change at exactly 12 s)", () => perform(rep([["Am"], ["F"], ["C"], ["G"]], 10), { bpm: 90, style: "block", melodyScale: scaleOf(9, AEOLIAN) }), "C major", BOTH, 3],
  ["Am F C G arpeggios settle on C major once", () => score([["AEOLIAN", 24]]), "C major", BOTH, 1],
  ["A blues: dominant sevenths that are not V7 -> I", () => perform(rep([["A7"], ["D7"], ["A7"], ["A7"], ["D7"], ["D7"], ["A7"], ["A7"], ["E7"], ["D7"], ["A7"], ["E7"]], 3), { bpm: 100, style: "block", melodyScale: scaleOf(9, MINOR_PENT) }), "A major", BOTH, 3],
  // Theory verifier, round 2 (2026-09-14). A natural-minor loop settles on its relative major (6m 5 4 5), as Am F C G does.
  ["Am G F G block triads, i-bVII-bVI-bVII (read G major, sure, F flagged)", () => hand(rep(AEOL_AM, 12), 100), "C major", BOTH, 2],
  ["Em D C D with an Aeolian melody", () => perform(rep([["Em"], ["D"], ["C"], ["D"]], 10), { bpm: 100, style: "block", melodyScale: scaleOf(4, AEOLIAN) }), "G major", BOTH, 2],
  ["Dm C Bb C arpeggios (Bb is under a twentieth of the weight)", () => perform(rep([["Dm"], ["C"], ["Bb"], ["C"]], 10), { bpm: 90, style: "arp", melodyScale: scaleOf(2, MINOR_PENT) }), "F major", BOTH, 2],
  ["Cm Fm Gm Cm block (read C major, which leaves out Eb, Ab and Bb)", () => perform(rep([["Cm"], ["Fm"], ["Gm"], ["Cm"]], 10), { bpm: 100, style: "block" }), "C minor", BOTH, 2],
  ["Am Dm G C block (read G major from a near tie at 16 s)", () => perform(rep([["Am"], ["Dm"], ["G"], ["C"]], 10), { bpm: 100, style: "block" }), "C major", BOTH, 2],
  ["Fm7 Bb7 Ebmaj7 Ebmaj7 comped (the shell's G and Bb before the Eb read Gm and cancelled the V7 -> I)", () => perform(rep([["Fm7"], ["Bb7"], ["Ebmaj7"], ["Ebmaj7"]], 12), { bpm: 120, style: "comp" }), "Eb major", BOTH, 3],
];
for (const [label, make, want, cadences, seeds] of SCENARIOS) {
  for (const cadence of cadences) {
    for (let s = 1; s <= seeds; s++) {
      rng = s * 7919;
      const keys = shown(play(make(), cadence).timeline);
      if (s === 1) report.push(`${label} (${cadence}): ${fmt(keys)}`);
      check(`${label} [${cadence}, seed ${s}] shows ${want} and nothing else`, keys.length === 1 && keys[0].key === want, fmt(keys));
    }
  }
}

const youngPick = shown(play(score([["HARM", 8]]), "tick").timeline);  // A minor at 8 s, its histogram still young
check("a key picked from a young histogram shows unsure, so the numbers dim", youngPick[0]?.t < 12 && youngPick[0]?.confidence === "unsure", JSON.stringify(youngPick[0]));

// A pause keeps the key, wherever in the loop it falls (the tracker used to bank the last chord's lead through it).
for (const [name, loop] of Object.entries(LOOPS)) {
  for (const bars of [9, 10, 11, 12]) {
    for (const pause of [3, 7, 15]) {
      for (const cadence of BOTH) {
        const keys = shown(play(pauseScore(name, bars, pause, 6), cadence).timeline);
        check(`${name}: ${bars} bars (last on loop chord ${(bars - 1) % 4 + 1}), ${pause} s of silence, resume -> ${loop.key} only [${cadence}]`,
              keys.length === 1 && keys[0].key === loop.key, fmt(keys));
      }
    }
  }
  const slow = shown(play(pauseScore(name, 8, 7, 6, 4), "tick").timeline);  // 4 s bars ending on the 4: one bar outlasts the hold
  check(`${name} at 4 s a bar, ending on the 4, 7 s of silence -> ${loop.key} only [tick]`, slow.length === 1 && slow[0].key === loop.key, fmt(slow));
}

// A first key taken at FIRST_WAIT from a near tie is provisional: unsure until it has led by margin for the hold.
const nearTie = shown(play(hand(rep(AEOL_AM, 12), 100), "tick").timeline);
check("a first key taken from a near tie at FIRST_WAIT shows unsure", nearTie[0]?.t >= 16 && nearTie[0]?.confidence === "unsure", JSON.stringify(nearTie[0]));

// Secondary dominants. E/G# and A7/C# lean the first bars to A minor, but from the second time round only C major shows.
// C E7 Am F (the V7 of a minor chord, no evidence for A minor) settles on one key and never flips.
const keyAt = (timeline, t) => { let k = null; for (const x of timeline) if (x.t <= t) k = x.key; return k; };
for (const cadence of BOTH) {
  rng = 7919;
  const sec = shown(play(perform(rep([["C"], ["E/G#"], ["Am"], ["A7/C#"], ["Dm"], ["G7"], ["C"], ["C"]], 5), { bpm: 100, style: "block", melodyScale: scaleOf(0, MAJOR) }), cadence).timeline);
  check(`C E/G# Am A7/C# Dm G7 C C: C major from 24 s on [${cadence}]`,
        sec.length <= 2 && sec.at(-1)?.key === "C major" && sec.filter((x) => x.t >= 24).every((x) => x.key === "C major"), fmt(sec));
  rng = 7919;
  const v7vi = shown(play(perform(rep([["C"], ["E7"], ["Am"], ["F"]], 10), { bpm: 100, style: "block", melodyScale: scaleOf(0, MAJOR) }), cadence).timeline);
  check(`C E7 Am F settles on one key [${cadence}]`, v7vi.length === 1, fmt(v7vi));
}

// A pause long enough to restart the histogram makes the shown key stale (in a real session the old key stayed up for
// 14 s of playing in a new key after minutes of silence). It goes within FIRST_SEC of new playing; the same music keeps it.
const thenAfter = (a, gap, b) => ({ ons: [...a.ons, ...b.ons.map((e) => ({ ...e, t: e.t + a.end + gap, off: e.off + a.end + gap }))], end: a.end + gap + b.end });
for (const cadence of BOTH) {
  rng = 7919;
  const ebF = play(thenAfter(perform(rep([["Eb"], ["Bb"], ["Cm"], ["Ab"]], 5), { bpm: 100, style: "block" }), 218,
                             perform(rep([["F"], ["C"], ["Dm"], ["Bb"]], 6), { bpm: 100, style: "block" })), cadence).timeline;
  const resume = 48 + 218;
  check(`Eb major, 218 s of silence, F major: Eb major gone 8 s into the new playing, then F major [${cadence}]`,
        shown(ebF).filter((x) => x.t < resume).every((x) => x.key === "Eb major") && keyAt(ebF, resume + 8.5) !== "Eb major"
        && shown(ebF).at(-1)?.key === "F major", fmt(ebF));
  rng = 7919;
  const loopD = () => perform(rep([["D"], ["A/C#"], ["Bm"], ["G"]], 5), { bpm: 100, style: "block" });
  const dd = play(thenAfter(loopD(), 218, loopD()), cadence).timeline;
  const d0 = dd.findIndex((x) => x.key);
  check(`D A/C# Bm G, 218 s of silence, the same loop: D major throughout, never blank [${cadence}]`,
        d0 >= 0 && dd.slice(d0).every((x) => x.key === "D major"), fmt(dd));
  rng = 7919;
  const ff = play(thenAfter(perform(rep([["F/A"], ["C/G"], ["Dm"], ["Bbmaj7"]], 5), { bpm: 80, style: "arp" }), 25,
                            perform(rep([["Dm"], ["Bbmaj7"], ["F/A"], ["C/G"]], 6), { bpm: 80, style: "arp" })), cadence).timeline;
  const f0 = ff.findIndex((x) => x.key);
  check(`F loop, 25 s of silence, resumed on Dm Bbmaj7: F major throughout [${cadence}]`, f0 >= 0 && ff.slice(f0).every((x) => x.key === "F major"), fmt(ff));
}

// The home-chord rule on Am G F G's weights (roots counted 1.6): KK alone names G major; with Am sounding as a chord,
// G major (which leaves out F) ranks the edge under C major. D C G D keeps D major unless an Em chord sounds too.
const weigh = (chords) => { const h = new Array(12).fill(0); for (const c of chords) { c.forEach((pc) => { h[pc] += 1; }); h[c[0]] += 0.6; } return h; };
const amGFG = weigh([[9, 0, 4], [7, 11, 2], [5, 9, 0], [7, 11, 2]]), dCGD = weigh([[2, 6, 9], [0, 4, 7], [7, 11, 2], [2, 6, 9]]);
const homeAt = (tonic) => Array.from({ length: 12 }, (_, t) => t === tonic);
eq("Am G F G by KK alone reads G major", rankKeys(amGFG)[0].name, "G major");
const withAm = rankKeys(amGFG, 1, 0.08, null, homeAt(9));
check("Am G F G with Am sounding: C major, G major at least the edge under it",
      withAm[0].name === "C major" && withAm.find((k) => k.name === "G major").score <= withAm[0].score - 0.08 + 1e-9, withAm.slice(0, 3).map((k) => k.name).join());
eq("D C G D with no minor chord sounding reads D major", rankKeys(dCGD, 1, 0.08, null, new Array(12).fill(false))[0].name, "D major");
eq("D C G D if Em sounded too: G major, every note on its scale", rankKeys(dCGD, 1, 0.08, null, homeAt(4))[0].name, "G major");

const early = rankKeys([3, 0, 0, 0, 2, 0, 0, 0, 0, 5, 0, 0], 0);  // A C E, nothing else yet
eq("an immature histogram ranks A C E as A minor", early[0].name, "A minor");
const light = [4, 0, 4, 0, 8, 2, 0, 0, 1, 10, 0, 2];  // A10 E8 C4 D4 F2 B2 G#1: the harmonic loop, its G# light
eq("a light raised 7th keeps A minor above A major (performance.py numbering_key agrees)", rankKeys(light).slice(0, 2).map((k) => k.name), ["A minor", "A major"]);

// ------------------------------------------------------ verifiers, round 3 (2026-09-14) --
// A slash chord's bass is read from the chord's own tones: TONE_STEPS is detect's TEMPLATES (a dim7's 7th excepted, a
// diminished 7th rather than detect's 6th, which only a written name reaches: detect names a dim7 from its bass).
const templateSteps = { "5": { 0: 0, 7: 4 } };
for (const t of Theory.TEMPLATES) for (const [semis, steps] of t.tones) (templateSteps[t.suffix] ||= {})[semis] = t.suffix === "dim7" && semis === 9 ? 6 : steps;
eq("TONE_STEPS is detect's TEMPLATES", TONE_STEPS, templateSteps);

// The page's numbers as Daniel sees them: Theory.detect -> spellForKey -> nashville for diatonic chords, secondary
// dominants, leading-tone dim7s and borrowed chords in every inversion, in 30 key spellings, against letters derived
// independently. spellForKey writes a bass that would need a double accidental as its plain twin (D#/G for D#/F##),
// and read by its letters that bass numbered V/V in first inversion 2/b5 in C# minor.
{
  const LET = "CDEFGAB", MAJ = [0, 2, 4, 5, 7, 9, 11], NMIN = [0, 2, 3, 5, 7, 8, 10];
  const m12 = (a) => ((a % 12) + 12) % 12, sg = (x) => m12(x + 6) - 6, acc = (a) => (a > 0 ? "#".repeat(a) : "b".repeat(-a));
  const TONES = { "": [[0, 0], [2, 4], [4, 7]], m: [[0, 0], [2, 3], [4, 7]], dim: [[0, 0], [2, 3], [4, 6]], "7": [[0, 0], [2, 4], [4, 7], [6, 10]],
    maj7: [[0, 0], [2, 4], [4, 7], [6, 11]], m7: [[0, 0], [2, 3], [4, 7], [6, 10]], m7b5: [[0, 0], [2, 3], [4, 6], [6, 10]], dim7: [[0, 0], [2, 3], [4, 6], [6, 9]] };
  const SHOWN = { "": "", m: "m", dim: "°", "7": "^7", maj7: "maj7", m7: "m7", m7b5: "ø7", dim7: "°7" };
  const chordsOf = (mode) => {  // { cat, rootL: letters above the tonic, rootPc: semitones above it, q }
    const s = mode === "major" ? MAJ : NMIN, out = [];
    const add = (cat, rootL, rootPc, q) => out.push({ cat, rootL, rootPc: m12(rootPc), q });
    if (mode === "major") {
      const tri = ["", "m", "m", "", "", "m", "dim"], sev = ["maj7", "m7", "m7", "maj7", "7", "m7", "m7b5"];
      for (let d = 0; d < 7; d++) { add("diatonic", d, s[d], tri[d]); add("diatonic 7th", d, s[d], sev[d]); }
      for (const x of [1, 2, 3, 4, 5]) { add(`V/${x + 1}`, x + 4, s[x] + 7, ""); add(`V7/${x + 1}`, x + 4, s[x] + 7, "7"); add(`vii°7/${x + 1}`, x + 6, s[x] - 1, "dim7"); }
      add("bVII", 6, 10, ""); add("bVI", 5, 8, ""); add("bIII", 2, 3, ""); add("iv", 3, 5, "m"); add("bVII7", 6, 10, "7"); add("II7", 1, 2, "7"); add("III", 2, 4, ""); add("VI7", 5, 9, "7");
    } else {
      const tri = ["m", "dim", "", "m", "m", "", ""];
      for (let d = 0; d < 7; d++) add("diatonic", d, s[d], tri[d]);
      add("V", 4, 7, ""); add("V7", 4, 7, "7"); add("vii°7", 6, 11, "dim7"); add("iiø7", 1, 2, "m7b5");
      for (const x of [2, 3, 4, 5, 6]) { add(`V/${x + 1}`, x + 4, s[x] + 7, ""); add(`V7/${x + 1}`, x + 4, s[x] + 7, "7"); }
      add("IV", 3, 5, ""); add("I", 0, 0, ""); add("bII", 1, 1, "");
    }
    return out;
  };
  const names = [...scoreKeys([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]).map((k) => k.name), "Gb major", "C# major", "Cb major", "D# minor", "A# minor", "Ab minor"];
  let piped = 0;
  for (const name of names) {
    const key = parseKey(name), tl = LET.indexOf(name[0]);
    for (const minor of key.mode === "minor" ? ["tonic", "relative"] : ["tonic"]) {
      theoryUi.minor = minor;
      const home = minor === "relative" ? { l: tl + 2, pc: key.tonic + 3 } : { l: tl, pc: key.tonic };
      const deg = (l, pc) => { const d = (((l - home.l) % 7) + 7) % 7; return acc(sg(pc - (home.pc + MAJ[d]))) + (d + 1); };
      for (const c of chordsOf(key.mode)) {
        const tones = TONES[c.q].map(([st, se]) => ({ l: tl + c.rootL + st, pc: m12(key.tonic + c.rootPc + se) }));
        tones.forEach((bass, inv) => {
          const info = spellForKey(Theory.detect([36 + bass.pc, ...tones.filter((_, i) => i !== inv).map((x) => 60 + x.pc)], key.bias), key);
          if (info.kind !== "chord" || Theory.pcOf(info.root) !== m12(key.tonic + c.rootPc) || info.suffix !== c.q) return;  // detect named another chord
          const want = deg(tones[0].l, tones[0].pc) + SHOWN[c.q] + (inv ? "/" + deg(bass.l, bass.pc) : "");
          const got = nashville(info, key, { minor })?.text;
          piped++;
          if (got !== want) check(`page numbers ${info.name} in ${name} (${minor}, ${c.cat}, inversion ${inv})`, false, `${got}, want ${want}`);
        });
      }
    }
  }
  theoryUi.minor = "tonic";
  check("page numbers checked for every chord and inversion the page names as played", piped > 3500, String(piped));
}

// The tracker on common playing outside the tuning set. settles: the timeline shows `want` by `by` seconds and nothing
// after it, and before it only keys in `before`.
const settles = (timeline, want, by, before = []) => {
  const keys = shown(timeline), i = keys.findIndex((x) => x.key === want);
  return i >= 0 && keys[i].t <= by && keys.slice(i).every((x) => x.key === want) && keys.slice(0, i).every((x) => before.includes(x.key));
};
const MINOR_BLUES = ["Am7", "Dm7", "Am7", "Am7", "Dm7", "Dm7", "Am7", "Am7", "E7", "Dm7", "Am7", "E7"];
const ROUND3 = [
  ["Am7 G F G comped, F only in the bass (showed G major, fair or sure, for 250 s)",
    () => perform(rep([["Am7"], ["G"], ["F"], ["G"]], 12), { bpm: 120, style: "comp" }), "C major", 17, []],
  ["Dm D7/F# Gm A7 Dm Dm (read D major for the whole piece)",
    () => perform(rep([["Dm"], ["D7/F#"], ["Gm"], ["A7"], ["Dm"], ["Dm"]], 7), { bpm: 100, style: "block" }), "D minor", 31, ["D major"]],
  ["C C7 F Fm, I-I7-IV-iv (C7 -> F read as V7 -> I showed F major for a minute)",
    () => perform(rep([["C"], ["C7"], ["F"], ["Fm"]], 10), { bpm: 100, style: "block" }), "C major", 12, []],
  ["E E7 A E, I-I7-IV-I (showed A major for over 200 s)",
    () => perform(rep([["E"], ["E7"], ["A"], ["E"]], 10), { bpm: 100, style: "block" }), "E major", 9, []],
  ["A minor blues, Am7 Dm7 E7 (a near-tie C major stood until 32 s)",
    () => perform(rep(MINOR_BLUES.map((c) => [c]), 3), { bpm: 100, style: "block" }), "A minor", 27, ["C major"]],
  ["Dm F C G, ii-IV-I-V (a near-tie F major stood until 49 s)",
    () => perform(rep([["Dm"], ["F"], ["C"], ["G"]], 10), { bpm: 100, style: "block" }), "C major", 31, ["F major"]],
];
for (const [label, make, want, by, before] of ROUND3) {
  for (const cadence of BOTH) {
    for (let s = 1; s <= 3; s++) {
      rng = s * 7919;
      const { timeline } = play(make(), cadence);
      if (s === 1) report.push(`${label} (${cadence}): ${fmt(shown(timeline))}`);
      check(`${label} [${cadence}, seed ${s}] shows ${want} by ${by} s, and before it only ${before.join(", ") || "nothing"}`,
            settles(timeline, want, by, before), fmt(shown(timeline)));
    }
  }
}

// ------------------------------------------------------ verifiers, round 4 (2026-09-14) --
// V -> V7 -> I is a cadence to I even while the key of the V shows. The colour rule used to decide at the I7, where
// V -> V7 -> I and I -> I7 -> IV look the same, and kept the key of the V on screen (Dm G G7 C read G major, sure, for
// the whole loop). A real I -> I7 -> IV (C C7 F Fm, E E7 A E above, and C C7 F F inside a C major tune) still cannot
// hand the key to the IV, and a blues' I7 IV7 V7 is no cadence at all.
const BLUES_C = ["C7", "F7", "C7", "C7", "F7", "F7", "C7", "C7", "G7", "F7", "C7", "G7"];
// A note-cadence seed of Dm G G7 C (and of Em A A7 D) picks D major (E major) for 6 s at FIRST_WAIT before the first
// cadence settles; that brief pick is allowed, any key after the cadence key is not.
// Still ambiguous, and not asserted: A E E7 A once E major is picked first (it is E E7 A A turned around, I I7 IV IV in
// E major), and C C7 F F G G7 C C from a cold start (the first C7 -> F -> F -> G reads as a cadence to F, and F stays).
const ROUND4 = [
  ["Dm G G7 C block, ii-V-V7-I (read G major, the key of V, for the whole loop)",
    () => perform(rep([["Dm"], ["G"], ["G7"], ["C"]], 10), { bpm: 100, style: "block" }), "C major", 23, ["G major", "D major"]],
  ["Em A A7 D block (read A major, sure, for 250 s)",
    () => perform(rep([["Em"], ["A"], ["A7"], ["D"]], 10), { bpm: 100, style: "block" }), "D major", 23, ["A major", "E major"]],
  ["Eb Ab Bb Bb7 comped, I-IV-V-V7 (read Bb major, sure)",
    () => perform(rep([["Eb"], ["Ab"], ["Bb"], ["Bb7"]], 12), { bpm: 120, style: "comp" }), "Eb major", 30, ["Bb major"]],
  ["C G Am F, then C C7 F F three times, then C G Am F again (a C major tune's I-I7-IV)",
    () => perform([...rep([["C"], ["G"], ["Am"], ["F"]], 6), ...rep([["C"], ["C7"], ["F"], ["F"]], 3), ...rep([["C"], ["G"], ["Am"], ["F"]], 3)],
      { bpm: 100, style: "block" }), "C major", 13, []],
  ["C blues comped, I7 IV7 V7", () => perform(rep(BLUES_C.map((c) => [c]), 3), { bpm: 120, style: "comp", melodyScale: scaleOf(0, MINOR_PENT) }),
    "C major", 17, []],
  ["G G7 C Cm arpeggios, I-I7-IV-iv (showed C major, sure, for the whole piece)",
    () => perform(rep([["G"], ["G7"], ["C"], ["Cm"]], 10), { bpm: 90, style: "arp" }), "G major", 13, []],
  ["C D7 G G7 C C block, a secondary dominant (read as I7 colour while D7 -> G fed G major's cadences, G major stayed)",
    () => perform(rep([["C"], ["D7"], ["G"], ["G7"], ["C"], ["C"]], 7), { bpm: 100, style: "block" }), "C major", 21, ["G major"]],
];
for (const [label, make, want, by, before] of ROUND4) {
  for (const cadence of BOTH) {
    for (let s = 1; s <= 3; s++) {
      rng = s * 7919;
      const { timeline } = play(make(), cadence);
      if (s === 1) report.push(`${label} (${cadence}): ${fmt(shown(timeline))}`);      check(`${label} [${cadence}, seed ${s}] shows ${want} by ${by} s, and before it only ${before.join(", ") || "nothing"}`,
            settles(timeline, want, by, before), fmt(shown(timeline)));
    }
  }
}
// G major on screen (as when the first bars read the key of the V), then F G G7 C in C major: the cadence takes it to C.
// And the same move played: a G major phrase, then the F G G7 C loop.
for (const cadence of BOTH) {
  for (let s = 1; s <= 3; s++) {
    rng = s * 7919;
    const tracker = createKeyTracker();
    tracker.lock("G major");
    tracker.lock(null);
    const loopC = () => perform(rep([["F"], ["G"], ["G7"], ["C"]], 10), { bpm: 100, style: "block" });
    const locked = play(loopC(), cadence, tracker).timeline;    check(`G major shown, then F G G7 C: C major by 16 s, only G major before [${cadence}, seed ${s}]`,
          settles(locked, "C major", 16, ["G major"]), fmt(shown(locked)));
    rng = s * 7919;
    const moved = play(thenAfter(perform(rep([["G"], ["D"], ["Em"], ["C"]], 3), { bpm: 100, style: "block" }), 0, loopC()), cadence).timeline;    check(`G D Em C, then F G G7 C from 28.8 s: G major, then C major by 51 s, nothing else [${cadence}, seed ${s}]`,
          settles(moved, "C major", 51, ["G major"]), fmt(shown(moved)));
  }
}

// ------------------------------------------------------ verifiers, round 5 (2026-09-14) --
// I -> I7 -> IV -> V is colour, never a cadence into the IV. Round 4 counted every chord after an I7's arrival but the
// arrival's own minor chord and a return to the I as a cadence, and C C7 F G read F major, "sure", for 220 s. The chords
// after the arrival now decide by key: G is in C major and not in F major (colour); Dm after Dm G G7 C is in C major and
// not in G major (a cadence); B7 after E E7 A resolves to E, in both keys, so it waits and gives no evidence.
const ROUND5 = [
  ["C C7 F G block, I-I7-IV-V (read F major, sure, for 220 s)", () => perform(rep([["C"], ["C7"], ["F"], ["G"]], 10), { bpm: 100, style: "block" }), "C major", 13],
  ["C C7 F G arpeggios", () => perform(rep([["C"], ["C7"], ["F"], ["G"]], 10), { bpm: 90, style: "arp" }), "C major", 13],
  ["E E7 A B7 block, I-I7-IV-V7 (read A major)", () => perform(rep([["E"], ["E7"], ["A"], ["B7"]], 10), { bpm: 100, style: "block" }), "E major", 17],
  ["G G7 C D comped (read D major, sure, for 240 s)", () => perform(rep([["G"], ["G7"], ["C"], ["D"]], 12), { bpm: 120, style: "comp" }), "G major", 17],
  ["Bb Bb7 Eb F arpeggios", () => perform(rep([["Bb"], ["Bb7"], ["Eb"], ["F"]], 10), { bpm: 90, style: "arp" }), "Bb major", 13],
  ["F F7 Bb C7 block", () => perform(rep([["F"], ["F7"], ["Bb"], ["C7"]], 10), { bpm: 100, style: "block" }), "F major", 17],
  ["D D7 G A D D block", () => perform(rep([["D"], ["D7"], ["G"], ["A"], ["D"], ["D"]], 8), { bpm: 110, style: "block" }), "D major", 13],
  ["C C7 F Dm G C block, I-I7-IV-ii-V-I", () => perform(rep([["C"], ["C7"], ["F"], ["Dm"], ["G"], ["C"]], 7), { bpm: 100, style: "block" }), "C major", 13],
  ["F blues arpeggios with I7 -> IV (read Bb major, the key of the IV)",
    () => perform(rep(["F7", "Bb", "F", "F7", "Bb", "Bb7", "F", "D7", "Gm7", "C7", "F", "C7"].map((c) => [c]), 3), { bpm: 80, style: "arp" }), "F major", 13],
  ["a C major tune: C G Am F six times, C C7 F G four times, C G Am F three times",
    () => perform([...rep([["C"], ["G"], ["Am"], ["F"]], 6), ...rep([["C"], ["C7"], ["F"], ["G"]], 4), ...rep([["C"], ["G"], ["Am"], ["F"]], 3)], { bpm: 100, style: "block" }), "C major", 13],
];
for (const [label, make, want, by] of ROUND5) {
  for (const cadence of BOTH) {
    for (let s = 1; s <= 3; s++) {
      rng = s * 7919;
      const { timeline } = play(make(), cadence);
      if (s === 1) report.push(`${label} (${cadence}): ${fmt(shown(timeline))}`);
      check(`${label} [${cadence}, seed ${s}] shows ${want} by ${by} s and nothing else`, settles(timeline, want, by), fmt(shown(timeline)));
    }
  }
}
// V -> V7 -> I from a key already on screen goes to the I, whatever the V's first voicing and after a pause (before round
// 4 these kept the key of the V up for minutes; the key rule must keep them).
const FROM_SHOWN = [
  ["G major shown, then Dm G G7 C", ["G", "D", "Em", "C"], 4, ["Dm", "G", "G7", "C"], 0, "G major", "C major", { bpm: 100, style: "block" }],
  ["G major shown, then Dm Gsus4 G7 C", ["G", "D", "Em", "C"], 4, ["Dm", "Gsus4", "G7", "C"], 0, "G major", "C major", { bpm: 100, style: "block" }],
  ["G major shown, then Dm G5 G7 C arpeggios", ["G", "D", "Em", "C"], 4, ["Dm", "G5", "G7", "C"], 0, "G major", "C major", { bpm: 90, style: "arp" }],
  ["G major shown, 10 s of silence, then Dm G G7 C", ["G", "D", "Em", "C"], 5, ["Dm", "G", "G7", "C"], 10, "G major", "C major", { bpm: 100, style: "block" }],
  ["F major shown, then Dm G G7 C", ["F", "C", "Dm", "Bb"], 5, ["Dm", "G", "G7", "C"], 0, "F major", "C major", { bpm: 100, style: "block" }],
  ["A minor shown, then F G G7 C", ["Am", "Dm", "E7", "Am"], 5, ["F", "G", "G7", "C"], 0, "A minor", "C major", { bpm: 100, style: "block" }],
];
for (const [label, a, loopsA, b, rest, ka, kb, opts] of FROM_SHOWN) {
  const tA = loopsA * a.length * 240 / opts.bpm, by = Math.round(tA + rest + 24);
  for (const cadence of BOTH) {
    for (let s = 1; s <= 3; s++) {
      rng = s * 7919;
      const first = perform(rep(a.map((c) => [c]), loopsA), opts);
      const { timeline } = play(thenAfter(first, rest, perform(rep(b.map((c) => [c]), 10), opts)), cadence);
      if (s === 1) report.push(`${label} (${cadence}): ${fmt(shown(timeline))}`);
      check(`${label} [${cadence}, seed ${s}]: only ${ka} before the move, then ${kb} by ${by} s and nothing else`,
            shown(timeline).filter((x) => x.t < tA).every((x) => x.key === ka) && settles(timeline, kb, by, [ka]), fmt(shown(timeline)));
    }
  }
}

// Pedalled playing, as the page verifier played it through /piano: a bass and a triad held for the bar, the pedal lifted
// just after each bar line (through half-pedal values) and pressed again, and a melody of eighths (chord tones an
// octave up on the beats, scale notes between, a restrike now and then) sounding on under the pedal. An Am bar then
// reads C6/9/A, Cadd9/A or a cluster, not Am, and Am G F G showed G major, "sure".
function pedalled(parts, seed) {
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const events = [];
  for (const { start, bars, loop, scale, holdPedalMs = 800 } of parts) {
    for (let b = 0; b < bars; b++) {
      const t = start + b * 3000, [bass, ...rh] = loop[b % loop.length], last = b === bars - 1, rolled = !last && b % 4 === 3;
      events.push({ t, kind: "on", n: bass, v: 70 + Math.floor(rnd() * 25) });
      rh.forEach((n, i) => events.push({ t: t + (rolled ? 110 * (i + 1) : 8 + 8 * i), kind: "on", n, v: 55 + Math.floor(rnd() * 30) }));
      if (b) events.push({ t: t + 45, kind: "up" });
      events.push({ t: t + 180, kind: "down" });
      if (last) {
        [bass, ...rh].forEach((n) => events.push({ t: t + 2500, kind: "off", n }));
        events.push({ t: t + 2500 + holdPedalMs, kind: "up" });
        continue;
      }
      events.push({ t: t + 2980, kind: "off", n: bass });
      rh.forEach((n) => events.push({ t: t + 2940, kind: "off", n }));
      let prev = null;
      for (let k = 1; k < 8; k++) {
        if (rnd() < 0.2) continue;
        const tones = k % 2 === 0 ? rh.map((n) => n + 12) : scale;
        const n = prev !== null && rnd() < 0.15 ? prev : tones[Math.floor(rnd() * tones.length)];
        events.push({ t: t + k * 375, kind: "on", n, v: 60 + Math.floor(rnd() * 35) }, { t: t + k * 375 + 300, kind: "off", n });
        prev = n;
      }
    }
  }
  events.sort((a, b) => a.t - b.t || (a.kind === "off" ? -1 : 0));
  const ons = [], sounding = new Map();
  let down = false;
  const stop = (n, t) => { const e = sounding.get(n); if (e) { e.off = t / 1000; sounding.delete(n); } };
  for (const e of events) {
    if (e.kind === "on") { stop(e.n, e.t); const on = { t: e.t / 1000, n: e.n, v: e.v, off: Infinity, held: true }; ons.push(on); sounding.set(e.n, on); }
    else if (e.kind === "off") { const on = sounding.get(e.n); if (on && on.held) { on.held = false; if (!down) stop(e.n, e.t); } }
    else { if (e.kind === "up") for (const [n, on] of [...sounding]) if (!on.held) stop(n, e.t); down = e.kind === "down"; }
  }
  const end = events.at(-1).t;
  for (const [n] of [...sounding]) stop(n, end);
  return { ons, end: end / 1000 + 1 };
}
const PEDAL_G = { loop: [[43, 55, 59, 62], [42, 57, 62, 66], [40, 55, 59, 64], [36, 55, 60, 64]], scale: [67, 69, 71, 72, 74, 76, 78, 79] };
const PEDAL_AM = { loop: [[45, 57, 60, 64], [43, 55, 59, 62], [41, 57, 60, 65], [43, 55, 59, 62]], scale: [69, 71, 72, 74, 76, 77, 79, 81] };
for (const cadence of BOTH) {
  for (let s = 1; s <= 3; s++) {
    const seed = 11 + (s - 1) * 7919;
    const cold = play(pedalled([{ start: 0, bars: 24, ...PEDAL_AM }], seed), cadence).timeline;
    if (s === 1) report.push(`Am G F G pedalled with a melody (${cadence}): ${fmt(shown(cold))}`);
    check(`Am G F G pedalled with a melody shows C major by 23 s and nothing else [${cadence}, seed ${s}]`, settles(cold, "C major", 23), fmt(shown(cold)));
    const resumed = play(pedalled([{ start: 0, bars: 17, ...PEDAL_G, holdPedalMs: 19500 }, { start: 250000, bars: 20, ...PEDAL_AM }], seed), cadence).timeline;
    if (s === 1) report.push(`G loop, 200 s of silence, Am G F G pedalled (${cadence}): ${fmt(resumed)}`);
    check(`G loop, 200 s of silence, Am G F G pedalled: G major gone 8.5 s into the new playing, never back, then C major [${cadence}, seed ${s}]`,
          shown(resumed).filter((x) => x.t < 250).every((x) => x.key === "G major") && keyAt(resumed, 258.5) !== "G major"
          && shown(resumed).filter((x) => x.t >= 250).every((x) => x.key !== "G major") && settles(resumed.filter((x) => x.t >= 250), "C major", 268),
          fmt(resumed));
  }
}

// The home-chord rule weighs how long notes sound: F struck once a bar in the bass is a small share of the note-ons
// but a quarter of the chords. By note-ons G major leaves out too little to be capped; by sounding time it cannot lead.
const struckOnce = [4, 0, 3, 0, 3, 0.8, 0, 8, 0, 4, 0, 3], soundedLong = [4, 0, 3, 0, 3, 3, 0, 8, 0, 4, 0, 3];  // C D E F G A B
eq("Am7 G F G by note-ons with Am sounding: G major", rankKeys(struckOnce, 1, 0.08, null, homeAt(9))[0].name, "G major");
const bySound = rankKeys(struckOnce, 1, 0.08, null, homeAt(9), soundedLong);
check("... by sounding time: C major, G major at least the edge under it", bySound[0].name === "C major"
      && bySound.find((k) => k.name === "G major").score <= bySound[0].score - 0.08 + 1e-9, bySound.slice(0, 3).map((k) => k.name).join());

console.log(report.join("\n"));
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
