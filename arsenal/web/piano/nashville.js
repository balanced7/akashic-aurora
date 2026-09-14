// Nashville numbers: arsenal/web/piano/nashville.js (pure ES module: no three.js, no DOM).
// Twin: arsenal/nashville.py. Both run every case in tests/fixtures/nashville_cases.json.
//
//   const tracker = createKeyTracker();
//   const { key } = tracker.update(pcHistory, t, lastInfo);  // the displayed key, held against flicker; lastInfo
//                                                            // (what sounds, or null) feeds the V7 -> I cue
//   spellInKey(info.root, key, { suffix: info.suffix })     // Ab in C# minor: { letter: 4, acc: 1, inScale: true } (G#)
//   nashville(Theory.detect(notes, key.bias), key)  // G7/B in C major: { text: "5^7/7", degree: 5, suffix: "7", ... }
//
// Conventions (the same words head arsenal/nashville.py):
// - Degree = letter distance from the key tonic's letter + 1. Accidental = semitone difference from that
//   degree of the tonic's MAJOR scale (b, #, bb rarely). In C major: Eb -> b3, F# -> #4, Bb -> b7.
// - Spelling follows the key, not the chord name: a spelling that fits the key worse than its enharmonic twin
//   is respelled first (D#m in Eb minor reads 1m, not #7m). A pitch between two scale notes reads the way charts
//   write it, whatever its given spelling (CHART below): major keys b2 b3 #4 b6 b7, minor keys (tonic numbering)
//   b2 3 #4 6 7, minor keys numbered from the relative major use that major key's table. Diminished chords lead
//   up (#1°, #2°, #5° in major, #1° in minor) and a major or dominant chord on the tritone is b5.
// - Minor keys, option minor: "tonic" (default) numbers from the minor tonic with major-scale accidentals
//   (A minor: Am=1m, C=b3, Dm=4m, E=5, Em=5m, F=b6, G=b7). minor: "relative" numbers from the relative
//   major (A minor: Am=6m, C=1, F=4, G=5, E=3).
// - Suffixes: "m" -> minorMark ("m" by default, or "-"; it also replaces the leading m of m7, m9, m(add9)...),
//   "dim" -> "°", "dim7" -> "°7", "m7b5" -> "ø7", "aug" -> "+"; every other Theory.TEMPLATES suffix unchanged.
// - The text form is never ambiguous: a suffix digit that would touch the degree (or a "-" minor mark) is
//   joined with "^" ("5^7", "1^6", "1^5", "2-^7"). The structured fields let the overlay draw a superscript.
// - Slash chords add "/" + the bass degree ("1/3", "5/2", "4/b7"). The bass, and an interval's top note, are read
//   from the root, not on their own: a chromatic chord tone keeps its letter (E/G# in C major is 3/#5, A/C# is 6/#1,
//   E-G# is 3-#5), unless its own reading is on the scale and the root-relative one is not (C#-E in C major: b2-3).
// - kind "note": the note's degree ("3"). kind "interval": "lo-hi" degrees ("1-3"). A cluster, or no key: null.
// - diatonic: the root degree and the triad family (major, minor, diminished, augmented; sus, power and
//   other) fit the key. Major key: 1 maj, 2 min, 3 min, 4 maj, 5 maj, 6 min, 7 dim. Minor key (tonic
//   numbering): 1 min, 2 dim, b3 maj, 4 min, 5 min or maj, b6 maj, b7 maj, 7 dim. Sus, power and other
//   chords are diatonic when the root degree is in the scale. Notes and intervals: every note in the scale.
//   Non-diatonic means borrowed or chromatic: flagged, never judged. The flag is decided the same way
//   under both minor numberings.

const LETTERS = ["C", "D", "E", "F", "G", "A", "B"];
const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];  // also the major scale, degree 1..7
const MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10];
const mod = (a, n) => ((a % n) + n) % n;
const pcOf = (sp) => mod(LETTER_PC[sp.letter] + sp.acc, 12);
const accText = (acc) => (acc > 0 ? "#".repeat(acc) : "b".repeat(-acc));
const nameOf = (sp) => LETTERS[sp.letter] + accText(sp.acc);

// ------------------------------------------------------------------ keys --
// Krumhansl-Kessler, names and bias exactly as Theory.estimateKey in piano.js.
const KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88];
const KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17];
const MAJOR_KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const MINOR_KEY_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"];

function pearson(xs, ys) {
  const n = xs.length;
  const mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { sxy += (xs[i] - mx) * (ys[i] - my); sxx += (xs[i] - mx) ** 2; syy += (ys[i] - my) ** 2; }
  return sxx > 0 && syy > 0 ? sxy / Math.sqrt(sxx * syy) : 0;
}

// Spelling bias as Theory.estimateKey: +1 in sharp keys, -1 in flat keys. Six accidentals go by the name: F# major
// sharps, Eb minor flats. A spelled name decides for itself ("Gb major" flats, "D# minor" sharps).
function biasOf(tonic, mode, sp = null) {
  if (sp && sp.acc) return Math.sign(sp.acc);
  const relMajor = mode === "major" ? tonic : mod(tonic + 3, 12);
  const fifths = mod(relMajor * 7, 12);
  return fifths === 0 ? 0 : fifths < 6 ? 1 : fifths > 6 ? -1 : mode === "major" ? 1 : -1;
}

const keyNameOf = (tonic, mode) => (mode === "major" ? MAJOR_KEY_NAMES : MINOR_KEY_NAMES)[tonic] + " " + mode;

// Every one of the 24 keys, best first. The sort is stable, so ties keep estimateKey's scan order and
// scoreKeys(hist)[0] is the key estimateKey(hist) names (when it names one).
export function scoreKeys(hist) {
  const out = [];
  for (let tonic = 0; tonic < 12; tonic++) {
    const rotated = hist.map((_, i) => hist[mod(i + tonic, 12)]);
    for (const [mode, profile] of [["major", KK_MAJOR], ["minor", KK_MINOR]]) {
      out.push({ tonic, mode, r: pearson(rotated, profile), name: keyNameOf(tonic, mode), bias: biasOf(tonic, mode) });
    }
  }
  return out.sort((a, b) => b.r - a.r);
}

const NOTE_RE = /^([A-Ga-g])(#{1,2}|b{1,2})?/;
const cleanText = (s) => String(s).trim().replace(/♭/g, "b").replace(/♯/g, "#");

function parseNote(text) {
  const m = NOTE_RE.exec(text);
  if (!m) return null;
  const acc = !m[2] ? 0 : m[2][0] === "#" ? m[2].length : -m[2].length;
  return { sp: { letter: LETTERS.indexOf(m[1].toUpperCase()), acc }, rest: text.slice(m[0].length) };
}

// "F major", "C# minor", "Bbm", "A" (major) -> { tonic, mode, name, bias }, or null when unreadable.
export function parseKey(keyName) {
  const n = parseNote(cleanText(keyName));
  if (!n) return null;
  const rest = n.rest.trim();
  const mode = /^(major|maj)?$/i.test(rest) ? "major" : /^(minor|min|m)$/i.test(rest) ? "minor" : null;
  if (!mode) return null;
  const tonic = pcOf(n.sp);
  return { tonic, mode, name: `${nameOf(n.sp)} ${mode}`, bias: biasOf(tonic, mode, n.sp) };
}

// A key as numbering needs it: the tonic spelling comes from the key's name (so "Eb minor" numbers from E-flat).
function keyContext(key) {
  if (!key) return null;
  const k = typeof key === "string" ? parseKey(key)
    : typeof key.name === "string" ? parseKey(key.name)
    : Number.isInteger(key.tonic) && (key.mode === "major" || key.mode === "minor") ? parseKey(keyNameOf(mod(key.tonic, 12), key.mode))
    : null;
  if (!k) return null;
  const sp = parseNote(k.name).sp;
  return { ...k, sp };
}

// ------------------------------------------------------------- numbering --
// Signed distance of a spelling from the key's own scale at its letter (minor keys also accept the leading tone).
function scaleOffset(sp, ctx) {
  const d = mod(sp.letter - ctx.sp.letter, 7);
  const scale = ctx.mode === "major" ? LETTER_PC : MINOR_SCALE;
  const diff = (step) => mod(pcOf(sp) - (ctx.tonic + step), 12);
  const signed = (x) => mod(x + 6, 12) - 6;
  const offs = [signed(diff(scale[d]))];
  if (ctx.mode === "minor" && d === 6) offs.push(signed(diff(11)));
  return offs.reduce((a, b) => (Math.abs(b) < Math.abs(a) ? b : a));
}

// Degree and major-scale accidental of a spelling, counted from a tonic spelling.
function degreeFrom(sp, tonicSp) {
  const d = mod(sp.letter - tonicSp.letter, 7);
  const acc = mod(pcOf(sp) - (pcOf(tonicSp) + LETTER_PC[d]) + 6, 12) - 6;
  return { degree: d + 1, acc, text: accText(acc) + (d + 1) };
}

const relativeMajor = (ctx) => {
  const letter = mod(ctx.sp.letter + 2, 7);
  return { letter, acc: mod(ctx.tonic + 3 - LETTER_PC[letter] + 6, 12) - 6 };
};

// Chart degrees for the pitches between two scale notes, by semitones above the tonic numbered from.
const CHART = { major: { 1: "b2", 3: "b3", 6: "#4", 8: "b6", 10: "b7" }, minor: { 1: "b2", 4: "3", 6: "#4", 9: "6" } };
const CHART_DIM = { major: { 1: "#1", 3: "#2", 8: "#5" }, minor: { 1: "#1" } };  // passing diminished chords lead up

// The spelling numbers are read from: the one closest to the key's scale (double sharps and flats too: G dim in
// G# minor is F## dim, 7°). Enharmonic ties go to the chart degree, then to the fewer accidentals in the degree,
// then to the spelling given. family: FAMILY of a chord root's suffix, or null for a note, bass or interval.
function respell(sp, ctx, minor = "tonic", family = null) {
  const pc = pcOf(sp);
  const ties = [];
  let least = Infinity;
  for (let letter = 0; letter < 7; letter++) {
    const acc = mod(pc - LETTER_PC[letter] + 6, 12) - 6;
    if (Math.abs(acc) > 2) continue;
    const c = Math.abs(scaleOffset({ letter, acc }, ctx));
    if (c < least) { least = c; ties.length = 0; }
    if (c === least) ties.push({ letter, acc });
  }
  if (ties.length < 2) return ties[0] || sp;
  const relative = ctx.mode === "minor" && minor === "relative";
  const home = relative ? relativeMajor(ctx) : ctx.sp;
  const table = relative ? "major" : ctx.mode;
  const above = mod(pc - pcOf(home), 12);
  const want = (family === "dim" && CHART_DIM[table][above]) || (family === "maj" && above === 6 ? "b5" : CHART[table][above]);
  const rank = (s) => {
    const d = degreeFrom(s, home);
    return [d.text === want ? 0 : 1, Math.abs(d.acc), s.letter === sp.letter ? 0 : 1];
  };
  const before = (a, b) => { const ra = rank(a), rb = rank(b); return ra[0] - rb[0] || ra[1] - rb[1] || ra[2] - rb[2]; };
  return ties.sort(before)[0];
}

// A spelling as it reads in a key: { letter, acc, inScale } (inScale: on the key's own scale, or a minor key's
// leading tone), or null without a readable key. piano.js spells the chord name and chips with it, so the name
// beside a number uses the same letters (G#7 next to 5^7 in C# minor, not Ab7).
export function spellInKey(sp, key, opts = {}) {
  const ctx = keyContext(key);
  if (!ctx || !sp || !Number.isInteger(sp.letter)) return null;
  const family = opts.suffix == null ? null : FAMILY[opts.suffix] || "other";
  const s = respell({ letter: sp.letter, acc: sp.acc }, ctx, opts.minor === "relative" ? "relative" : "tonic", family);
  return { letter: s.letter, acc: s.acc, inScale: scaleOffset(s, ctx) === 0 };
}

// { degree, acc, text } of a spelling already read in the key, in the chosen numbering, plus tonic-numbered
// tdeg/tacc for the diatonic test.
function numberSpelled(s, ctx, minor) {
  const t = degreeFrom(s, ctx.sp);
  const out = ctx.mode === "minor" && minor === "relative" ? degreeFrom(s, relativeMajor(ctx)) : t;
  return { ...out, tdeg: t.degree, tacc: t.acc };
}
const numberNote = (sp, ctx, minor, family = null) => numberSpelled(respell(sp, ctx, minor, family), ctx, minor);

// A slash chord's bass and an interval's top note are read from the root: the note sits `steps` letters above the
// root's respelling, so a chromatic chord tone keeps its function (E/G# in C major is 3/#5, not 3/b6; A/C# is 6/#1).
// The note's own reading stands when it is on the key's scale and the moved spelling is not (C#-E in C major reads
// b2-3, not b2-b4), or when the moved spelling would need more than one accidental in a degree.
function spellFrom(sp, steps, rootSp, ctx, minor) {
  const own = respell(sp, ctx, minor);
  const letter = mod(rootSp.letter + steps, 7);
  const moved = { letter, acc: mod(pcOf(sp) - LETTER_PC[letter] + 6, 12) - 6 };
  if (Math.abs(moved.acc) > 2 || Math.abs(degreeFrom(moved, ctx.sp).acc) > 1) return own;
  if (ctx.mode === "minor" && Math.abs(degreeFrom(moved, relativeMajor(ctx)).acc) > 1) return own;
  return scaleOffset(moved, ctx) !== 0 && scaleOffset(own, ctx) === 0 ? own : moved;
}

// Letter steps of each chord tone above the root, by semitones above it: Theory.detect's TEMPLATES in piano.js (the
// tests check both twins against them), except dim7's 7th, a diminished 7th here (G#dim7/F in A major is 7°7/b6).
// detect spells it as a 6th but always names a dim7 from its bass, so only a written name reaches that entry. A bass
// that is no chord tone is spelled as detect spells a foreign bass.
const IV_STEPS = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6];
export const TONE_STEPS = Object.fromEntries(Object.entries({
  "": "0:0 4:2 7:4", m: "0:0 3:2 7:4", dim: "0:0 3:2 6:4", aug: "0:0 4:2 8:4", sus4: "0:0 5:3 7:4", sus2: "0:0 2:1 7:4",
  "5": "0:0 7:4", "7": "0:0 4:2 7:4 10:6", maj7: "0:0 4:2 7:4 11:6", m7: "0:0 3:2 7:4 10:6", m7b5: "0:0 3:2 6:4 10:6",
  dim7: "0:0 3:2 6:4 9:6", "6": "0:0 4:2 7:4 9:5", m6: "0:0 3:2 7:4 9:5", add9: "0:0 2:1 4:2 7:4",
  "m(add9)": "0:0 2:1 3:2 7:4", "m(maj7)": "0:0 3:2 7:4 11:6", "7sus4": "0:0 5:3 7:4 10:6", add11: "0:0 4:2 5:3 7:4",
  "7#5": "0:0 4:2 8:4 10:6", "maj7#5": "0:0 4:2 8:4 11:6", "7b5": "0:0 4:2 6:4 10:6", "6/9": "0:0 2:1 4:2 7:4 9:5",
  "m6/9": "0:0 2:1 3:2 7:4 9:5", "9": "0:0 2:1 4:2 7:4 10:6", maj9: "0:0 2:1 4:2 7:4 11:6", m9: "0:0 2:1 3:2 7:4 10:6",
  "9sus4": "0:0 2:1 5:3 7:4 10:6", "7b9": "0:0 1:1 4:2 7:4 10:6", "7#9": "0:0 3:1 4:2 7:4 10:6",
  "maj7#11": "0:0 4:2 6:3 7:4 11:6", "7#11": "0:0 4:2 6:3 7:4 10:6", "13": "0:0 2:1 4:2 7:4 9:5 10:6",
  maj13: "0:0 2:1 4:2 7:4 9:5 11:6", m11: "0:0 2:1 3:2 5:3 7:4 10:6", m13: "0:0 2:1 3:2 7:4 9:5 10:6",
  "11": "0:0 2:1 4:2 5:3 7:4 10:6",
}).map(([suffix, tones]) => [suffix, Object.fromEntries(tones.split(" ").map((x) => x.split(":").map(Number)))]));

// Letters from the root up to a slash chord's bass, read from the chord and not from the name's letters: piano.js
// spellForKey writes a bass that would need a double accidental as its plain twin (D#/G for D#/F##), and D# to G is
// a 4th by letter, though G is the chord's 3rd.
function bassSteps(bass, rootSp, suffix) {
  const semis = mod(pcOf(bass) - pcOf(rootSp), 12);
  const tones = TONE_STEPS[suffix];
  return tones && semis in tones ? tones[semis] : IV_STEPS[semis];
}

const FAMILY = {
  "": "maj", m: "min", dim: "dim", aug: "aug", sus4: "sus", sus2: "sus", "5": "power",
  "7": "maj", maj7: "maj", m7: "min", m7b5: "dim", dim7: "dim", "6": "maj", m6: "min", add9: "maj",
  "m(add9)": "min", "m(maj7)": "min", "7sus4": "sus", add11: "maj", "7#5": "aug", "maj7#5": "aug", "7b5": "other",
  "6/9": "maj", "m6/9": "min", "9": "maj", maj9: "maj", m9: "min", "9sus4": "sus", "7b9": "maj", "7#9": "maj",
  "maj7#11": "maj", "7#11": "maj", "13": "maj", maj13: "maj", m11: "min", m13: "min", "11": "maj",
};
const FITS = {  // tonic-numbered degree text -> triad families that fit
  major: { "1": ["maj"], "2": ["min"], "3": ["min"], "4": ["maj"], "5": ["maj"], "6": ["min"], "7": ["dim"] },
  minor: { "1": ["min"], "2": ["dim"], "b3": ["maj"], "4": ["min"], "5": ["min", "maj"], "b6": ["maj"], "b7": ["maj"], "7": ["dim"] },
};
const inScale = (n, ctx) => (accText(n.tacc) + n.tdeg) in FITS[ctx.mode];
function chordFits(n, suffix, ctx) {
  const fits = FITS[ctx.mode][accText(n.tacc) + n.tdeg];
  if (!fits) return false;
  const family = FAMILY[suffix] || "other";
  return family === "sus" || family === "power" || family === "other" || fits.includes(family);
}

const EXACT = { dim: "°", dim7: "°7", m7b5: "ø7", aug: "+" };
function suffixText(suffix, minorMark) {
  if (suffix in EXACT) return EXACT[suffix];
  if (suffix[0] === "m" && !suffix.startsWith("maj")) return minorMark + suffix.slice(1);
  return suffix;
}
function joinSuffix(base, suffix) {
  if (!suffix) return base;
  if (/^\d/.test(suffix)) return base + "^" + suffix;
  const m = /^-(\d.*)$/.exec(suffix);
  return m ? base + "-^" + m[1] : base + suffix;
}

const pub = (n) => (n ? { degree: n.degree, acc: n.acc, text: n.text } : null);

function build(kind, root, suffix, bass, upper, ctx, opts) {
  const minor = opts.minor === "relative" ? "relative" : "tonic";
  const minorMark = opts.minorMark == null ? "m" : String(opts.minorMark);
  const rootSp = respell(root, ctx, minor, kind === "chord" ? FAMILY[suffix] || "other" : null);
  const r = numberSpelled(rootSp, ctx, minor);
  if (kind === "note") {
    return { text: r.text, degree: r.degree, acc: r.acc, root: r.text, suffix: "", bass: null, upper: null,
             diatonic: inScale(r, ctx), kind };
  }
  if (kind === "interval") {
    const u = numberSpelled(spellFrom(upper, mod(upper.letter - root.letter, 7), rootSp, ctx, minor), ctx, minor);  // the letters written
    return { text: `${r.text}-${u.text}`, degree: r.degree, acc: r.acc, root: r.text, suffix: "", bass: null,
             upper: pub(u), diatonic: inScale(r, ctx) && inScale(u, ctx), kind };
  }
  const sfx = suffixText(suffix, minorMark);
  const b = bass ? numberSpelled(spellFrom(bass, bassSteps(bass, rootSp, suffix), rootSp, ctx, minor), ctx, minor) : null;
  return { text: joinSuffix(r.text, sfx) + (b ? "/" + b.text : ""), degree: r.degree, acc: r.acc, root: r.text,
           suffix: sfx, bass: pub(b), upper: null, diatonic: chordFits(r, suffix, ctx), kind: "chord" };
}

// info: a Theory.detect result. key: a tracker key ({ tonic, mode, name, bias }), an estimateKey result, or a key name.
export function nashville(info, key, opts = {}) {
  const ctx = keyContext(key);
  if (!info || !ctx || !info.root) return null;
  const sp = (x) => ({ letter: x.letter, acc: x.acc });
  if (info.kind === "note") return build("note", sp(info.root), "", null, null, ctx, opts);
  if (info.kind === "interval") return info.upper ? build("interval", sp(info.root), "", null, sp(info.upper), ctx, opts) : null;
  if (info.kind === "chord") return build("chord", sp(info.root), info.suffix || "", info.bass ? sp(info.bass) : null, null, ctx, opts);
  return null;
}

// A chord name as Theory.detect writes one: "Fmaj7/A", "Bbm7b5", "C6/9/E", "C5" (power chord), "C-E" (interval),
// "E4" (a note with its octave). A bare letter reads as a major chord and "G5"/"C6"/"C7" read as chords, as they
// would on a lead sheet; pass kind "note" to read them as notes. Returns { kind, root, suffix, bass, upper } or null.
export function parseChord(chordName, kind = null) {
  const text = cleanText(chordName == null ? "" : chordName);
  const head = parseNote(text);
  if (!head) return null;
  if (kind === "note") return /^(-?\d+)?$/.test(head.rest) ? { kind: "note", root: head.sp, suffix: "", bass: null, upper: null } : null;
  const iv = /^-([A-Ga-g](?:#{1,2}|b{1,2})?)$/.exec(head.rest);
  if (iv) return { kind: "interval", root: head.sp, suffix: "", bass: null, upper: parseNote(iv[1]).sp };
  if (/^-?\d+$/.test(head.rest) && !(head.rest in FAMILY)) return { kind: "note", root: head.sp, suffix: "", bass: null, upper: null };
  let suffix = head.rest, bass = null;
  const slash = suffix.lastIndexOf("/");
  if (slash >= 0) {
    const b = parseNote(suffix.slice(slash + 1));
    if (b && b.rest === "") { bass = b.sp; suffix = suffix.slice(0, slash); }
  }
  if (/\s/.test(suffix)) return null;  // a cluster ("C D E") has no number
  return { kind: "chord", root: head.sp, suffix, bass, upper: null };
}

export function nashvilleFromName(chordName, keyName, opts = {}) {
  const ctx = keyContext(keyName);
  const c = parseChord(chordName, opts.kind || null);
  if (!ctx || !c) return null;
  return build(c.kind, c.root, c.suffix, c.bass, c.upper, ctx, opts);
}

// ---------------------------------------------------------- key tracker --
// createKeyTracker names the key the notes are in and holds it against flicker. Its clocks count playing time only:
// seconds within ACTIVE_SEC of a note-on. piano.js's pcHistory is frozen in silence, so a pause is no evidence, and
// nothing banks, drains or ages while nobody plays (verifier, 2026-09-14: a pause after a loop's 4 chord handed the
// key to the 4, and every number after it was wrong).
//
// Ranking (rankKeys) is the Krumhansl-Kessler r plus two cues it cannot see:
// - The leading tone. KK alone cannot tell a key from its relative minor when the harmony leans on vi (the F/A C/G
//   Dm Bbmaj7 loop correlates best with D minor). A minor key whose raised 7th (C# in D minor, the major V's third)
//   is unheard sinks to just under its relative major; a raised 7th at LT_SHARE of the tonic's weight lifts it back,
//   and part of one lifts it part way. The rule only chooses between a minor key and its relative major, so once the
//   parallel major outscores that relative major the minor key stops sinking just above it: a harmonic-minor loop
//   whose G# is light stays A minor, never A major. A natural-minor loop settles on its relative major (Am F C G is
//   C major, numbered 6m 4 1 5), the way Nashville charts number it; lock() is there for the other reading.
// - The home chord. KK cannot tell i-bVII-bVI-bVII (Am G F G) from ii-I-bVII-I in G major: the notes weigh the same
//   as D C G D does in D major, and only D C G D is in the key of its most-heard chord. What differs is the minor
//   chord: every note of Am G F G is on one major scale (C major, A natural minor) and that scale's own minor chord
//   (Am) sounds as a chord. While a minor chord sounds for HOME_SHARE of the chord time (over SLOW_TAU) and its
//   natural-minor scale holds all but HOME_FIT of the sounding time, a key that leaves out HOME_OUT or more of it
//   (G major leaves out F, a quarter of the chords) ranks edge under the better of that minor key and its relative
//   major, so it can neither win nor stay. D C G D keeps D major (no Em sounds), and a V7 of the minor chord (E7 in
//   C E7 Am F: G# is off the natural-minor scale) never turns the rule on. The tracker passes how long each pitch class
//   sounded, not note-ons: a comped Am7 G F G strikes its F once a loop in the bass and a pedalled melody piles up
//   note-ons, so counted by note-ons F fell under HOME_OUT between F chords and G major came back "sure". A minor chord
//   counts under any name while its triad sounds over the bass: with the pedal down an Am bar reads C6/9/A, Cadd9/A or
//   a cluster once melody notes blend in.
// - The cadence. A dominant seventh resolving a fifth down to a major chord that holds for CAD_SETTLE is the plainest
//   key evidence there is: F7 -> Bbmaj7 says Bb major. Each one adds to that key's score, decaying over CAD_TAU. While
//   it stands, the key of the V (F major) can be neither picked nor switched to, and unless that key has more cadences
//   of its own it ranks the edge under the key it resolves to, so a shown F major gives way: in Em A A7 D the notes lean
//   to A major by more than the bonus, and A major stood for the whole piece. Counting notes alone reads a comp-voiced
//   ii-V-I in the key of its V. A momentary chord cannot fire it (in a blues, A7 -> D7 passing through a plain D for a
//   moment), and V7 -> I7 never does. A V7 resolving to a minor chord bars the key of the V, but adds to the minor key
//   only while that key and its parallel major rank best and second best: in a major key it is usually a secondary
//   dominant (E7 -> Am in C major), no evidence for A minor, while Dm D7/F# Gm A7 Dm Dm read D major for the whole piece
//   without it.
// - I -> I7 -> IV sounds exactly like V -> V7 -> I while it happens: G G7 C is a cadence in C major and colour in G
//   major. So a dominant seventh right after a chord on its own root held (major in any colour, sus or power; not
//   minor), whatever key shows, leaves its arrival undecided, and the chords after the arrival decide it by key (hear()):
//   - a chord in the arrival's key and not in the key of the I7's root makes it a cadence (Dm G G7 C | Dm: Dm is in C
//     major, not G major);
//   - a chord in the I7's key and not the arrival's makes it colour (C C7 F | G), and so do the arrival's own minor
//     chord (C C7 F Fm) and a return to the I7's root straight after the arrival (E E7 A E);
//   - a chord in both keys, or in neither, waits for the next one. A dominant seventh belongs where the chord it resolves
//     to does (D7 in C major, B7 in A major), so E E7 A B7 E waits until the loop comes round and gives no evidence.
//     While it waits, an arrival held ARRIVAL_DWELL times as long as the I before the I7 is a cadence (C D7 G G7 C C:
//     the C holds two bars, the G one), and one still undecided PENDING_SEC after it sounded gives no evidence.
//   No first key is picked while an arrival is undecided. Rejected on evidence (verifier, 2026-09-14): counting
//   everything but that minor chord and that return as a cadence read every I I7 IV V (C C7 F G, gospel and blues
//   turnarounds) in the key of the IV, often "sure"; deciding at the I7 itself kept the key of the V on screen whenever
//   it was picked first; waiting only when the shown key's tonic is under the I7 left G G7 C D and a blues' F F7 Bb in
//   the key of the IV; judging a dominant seventh by its own root (D7 as G major's V) lost C D7 G G7 C C to G major;
//   crediting an undecided arrival once the loop came round lost E E7 A B7 to A major.
//   Still ambiguous: a loop that is I I7 IV IV turned around (A E E7 A after a first pick of E major) keeps that key.
//
// Showing a key:
// - The first key waits for FIRST_SEC of playing (and while an I7-shaped arrival is undecided, up to FIRST_WAIT) and is
//   read from the slow histogram, which weighs everything played
//   so far about evenly (the 12 s one leans on the last bar, and F/A alone reads A minor). It shows then when one key
//   leads the next by FIRST_GAP, else once FIRST_WAIT has passed. While the histogram is young (YOUNG_SEC) the
//   confidence is "unsure", so the numbers dim.
// - A different key takes over once it has led the shown key by margin for holdSec of playing time: lead time is
//   banked while leading and drains at LEAD_DRAIN x while not, so a beat-long lapse costs about a beat. A key that was
//   shown within RECENT_SEC needs twice the hold, so a I-bVII-IV-I loop cannot toggle between I and IV.
// - The challenger must also be heard now: it counts only while it scores >= minR on a FAST_TAU histogram of the
//   recently played notes, and only the supported key the long histogram ranks highest may take over. While the
//   histogram is young only a key picked from a young histogram may be corrected.
// - A first key taken at FIRST_WAIT from a near tie (under FIRST_GAP) is provisional: "unsure" (the numbers dim)
//   until it has led its runner-up by margin for holdSec of playing. (Easier switching away from it made the F/A C/G
//   Dm Bbmaj7 loop hand F major to D minor after a pause.) Until then it is re-examined on the slow histogram: a key
//   related to it (parallel, relative, or a fifth away) that outscores it there and leaves out less of what sounds
//   takes over after holdSec (in an A minor blues C major, the near-tie pick before E7 has sounded, gave way at 25 s,
//   not 32 s).
// - A pause long enough for the histogram to restart (FRESH_DROP: about 17 s of silence) makes the shown key stale
//   (a real session, 2026-09-14: minutes of silence, then the old key stayed up for 14 s of playing in another). It stays,
//   "unsure", for FIRST_SEC of new playing; then it stands (correctable as a young pick) only if the new notes rank it
//   within margin of the best key, else it is dropped and the first-key rules read the new notes alone. Nothing takes
//   over before that: on a young histogram the leading-tone rule is not in yet, and a resume on Dm Bbmaj7 in F major
//   handed the key to D minor.
// Confidence is also "unsure" while the runner-up is a fifth away and within margin (F major against Bb major):
// every number would move by a fifth.
const MIN_WEIGHT = 2;     // estimateKey's own floor: under two note-ons of weight there is nothing to read
const FIRST_WEIGHT = 6;
const FIRST_SEC = 8;      // two to four bars of playing before a first key
const FIRST_GAP = 0.15;
const FIRST_WAIT = 16;    // a four-bar loop at 60 bpm
const LT_SHARE = 0.25;
const LT_EDGE = 0.08;     // how far under its relative major an unproven minor key sits: the tracker passes 2 x margin,
                          // so the relative major always leads it by enough to take the key back
const LT_FLOOR = 0.02;    // ...but never lower than this above its parallel major, once that major outscores the
const LT_FLOOR_FADE = 0.16;  // relative major (in full when by LT_FLOOR_FADE). arsenal/performance.py numbering_key twins both.
const ACTIVE_SEC = 1.5;   // seconds after a note-on that still count as playing
const FAST_TAU = 4;       // seconds: about a bar at 80 bpm
const SLOW_TAU = 24;      // seconds: two loops or so
const YOUNG_SEC = 12;     // piano.js's pcHistory decay time
const FRESH_DROP = 4;     // total weight falling below a quarter between updates means the old notes have faded
const LEAD_DRAIN = 2;     // a challenger must lead about two thirds of the time to bank toward a switch
const RECENT_SEC = 30;
const CAD_W = 0.1, CAD_MAX = 2, CAD_TAU = 16, CAD_WINDOW = 3, CAD_SETTLE = 0.6, CAD_BAR = 0.3;
const HOME_SHARE = 0.15, HOME_FIT = 0.03, HOME_OUT = 0.04;
const SURE_R = 0.75, SURE_GAP = 0.08;
const ARRIVAL_DWELL = 1.5, PENDING_SEC = 12;
const DOMINANT = new Set(["7", "9", "13", "7b9", "7#9", "7#11", "7sus4", "9sus4", "7b5", "7#5", "11"]);
const keyIndex = (tonic, mode) => tonic * 2 + (mode === "minor" ? 1 : 0);

// Whether a chord name (root pitch class, detect suffix) belongs to a key: FITS by semitones above the tonic, as the
// diatonic flag reads it. A dominant seventh also belongs where the chord it resolves to does (D7 in C major, V7/V).
const TRIADS = {
  major: { 0: ["maj"], 2: ["min"], 4: ["min"], 5: ["maj"], 7: ["maj"], 9: ["min"], 11: ["dim"] },
  minor: { 0: ["min"], 2: ["dim"], 3: ["maj"], 5: ["min"], 7: ["min", "maj"], 8: ["maj"], 10: ["maj"], 11: ["dim"] },
};
function fitsKey(root, suffix, tonic, mode) {
  if (DOMINANT.has(suffix)) {
    const target = TRIADS[mode][mod(root + 5 - tonic, 12)];
    if (target && (target.includes("maj") || target.includes("min"))) return true;
  }
  const fits = TRIADS[mode][mod(root - tonic, 12)];
  if (!fits) return false;
  const family = FAMILY[suffix] || "other";
  return family === "sus" || family === "power" || family === "other" || fits.includes(family);
}

// Share of a histogram's weight outside a key's scale (a minor key's scale includes its leading tone).
function outShare(hist, tonic, mode) {
  const scale = mode === "major" ? LETTER_PC : MINOR_SCALE;
  let out = 0, all = 0;
  for (let i = 0; i < 12; i++) {
    const step = mod(i - tonic, 12);
    all += hist[i];
    if (!scale.includes(step) && !(mode === "minor" && step === 11)) out += hist[i];
  }
  return all > 0 ? out / all : 0;
}

// What a sounding shape gives the home-chord rule: the keyIndex of a minor chord (a minor triad over the bass under any
// name, since with the pedal down melody notes rename an Am bar C6/9/A, Cadd9/A or a cluster; or a minor-family chord,
// Am/C), -1 for any other chord, null for silence, a note, an interval or any other cluster. midis: the MIDI notes
// sounding. Other clusters are no chord time: counted, pedalled clusters in a real session diluted a minor chord's share
// under HOME_SHARE, its rule switched off, and a key leaving out 12% of the sound took over from one leaving out 1%.
function homeChordOf(chord, midis) {
  if (!chord) return null;
  if (midis.length >= 3) {
    const bass = mod(Math.min(...midis), 12), pcs = new Set(midis.map((m) => mod(m, 12)));
    if (pcs.has(mod(bass + 3, 12)) && pcs.has(mod(bass + 7, 12))) return keyIndex(bass, "minor");
  }
  if (chord.kind === "chord" && chord.root) return FAMILY[chord.suffix || ""] === "min" ? keyIndex(pcOf(chord.root), "minor") : -1;
  return null;
}

// scoreKeys plus a tracker score (see above), best score first. maturity 0..1 phases the leading-tone rule in (no V
// chord can have sounded in bar one). bonus: optional per-key additions, indexed tonic * 2 + (minor ? 1 : 0).
// homes: optional, 12 flags by tonic: that minor chord has sounded as a chord (HOME_SHARE of the chord time), which
// turns on the home-chord rule.
export function rankKeys(hist, maturity = 1, edge = LT_EDGE, bonus = null, homes = null, homeHist = hist) {
  const scores = scoreKeys(hist);
  const rOf = (tonic, mode) => scores.find((s) => s.tonic === tonic && s.mode === mode).r;
  const ranked = scores.map((k) => {
    const extra = bonus ? bonus[keyIndex(k.tonic, k.mode)] : 0;
    if (k.mode === "major") return { ...k, score: k.r + extra };
    const tonicW = hist[k.tonic], lt = hist[mod(k.tonic + 11, 12)];
    const heard = tonicW > 0 ? Math.min(1, lt / (LT_SHARE * tonicW)) : 0;
    const rRel = rOf(mod(k.tonic + 3, 12), "major"), rPar = rOf(k.tonic, "major");
    let score = k.r - maturity * (1 - heard) * Math.max(0, k.r - rRel + edge);
    const floor = Math.min(k.r, rPar + LT_FLOOR);
    if (floor > score) score += Math.min(1, Math.max(0, (rPar - rRel) / LT_FLOOR_FADE)) * (floor - score);
    return { ...k, score: score + extra };
  });
  for (let tonic = 0; homes && tonic < 12; tonic++) {
    const rel = mod(tonic + 3, 12);
    if (!homes[tonic] || outShare(homeHist, rel, "major") > HOME_FIT) continue;
    const pair = (k) => (k.tonic === rel && k.mode === "major") || (k.tonic === tonic && k.mode === "minor");
    const cap = Math.max(...ranked.filter(pair).map((k) => k.score)) - edge;
    for (const k of ranked) if (!pair(k) && k.score > cap && outShare(homeHist, k.tonic, k.mode) >= HOME_OUT) k.score = cap;
  }
  return ranked.sort((a, b) => b.score - a.score);
}

export function createKeyTracker({ holdSec = 5, margin = 0.04, minR = 0.55 } = {}) {
  let key = null, locked = false, youngPick = false;
  let stale = false;                        // the key shown before a long pause, not yet checked against the new notes
  let provisional = false, confirmSec = 0;  // a near-tie first key, and the playing seconds it has led by margin
  let challenger = null;                    // { id, sec }: a key re-examining a provisional one, and the lead it banked
  let prev = null, prevT = 0, prevW = 0, lastNoteT = -Infinity;
  let age = 0, clock = 0;  // playing seconds since the histogram started (or restarted), and since the tracker did
  let fast = new Array(12).fill(0), slow = new Array(12).fill(0);
  const sounding = new Array(12).fill(0);  // playing seconds each pitch class sounded, decaying over SLOW_TAU
  let soundingPcs = null;                  // ...and the pitch classes that sounded since the last update
  const cadence = new Array(24).fill(0);  // V7 -> I evidence per key, keyIndex order
  const chordSec = new Array(24).fill(0);  // playing seconds each minor chord sounded (keyIndex order), decaying over SLOW_TAU
  let allChordSec = 0, sounded = null;     // ...any chord's; and what sounded since the last update (homeChordOf)
  let dominant = null;  // { root, at }: the dominant seventh last heard
  let arrival = null;   // { root, mode, since }: the chord it resolved to, still settling
  let between = null;   // { root, since }: another chord heard after the dominant, until it holds
  let held = null, before = null;  // { root, suffix, since }: the chord name sounding, and the one before it (plus sec held)
  let pending = null;   // { root, mode, since, from, settled, next }: the arrival of an I7-shaped V7, undecided
  const banked = new Map();   // "tonic:mode" -> playing seconds of lead over the shown key, capped at the hold
  const shownAt = new Map();  // "tonic:mode" -> clock when that key was last shown
  const strip = (k) => ({ tonic: k.tonic, mode: k.mode, name: k.name, bias: k.bias });
  const same = (a, b) => !!(a && b && a.tonic === b.tonic && a.mode === b.mode);
  const idOf = (k) => `${k.tonic}:${k.mode}`;
  const sum = (xs) => xs.reduce((a, b) => a + b, 0);
  // The keys a near tie can confuse a key with: its parallel, its relative, and the keys a fifth away in its mode.
  const related = (a, b) => a.tonic === b.tonic || (a.mode === b.mode && [5, 7].includes(mod(a.tonic - b.tonic, 12)))
    || (a.mode !== b.mode && mod(a.tonic + (a.mode === "minor" ? 3 : 0) - b.tonic - (b.mode === "minor" ? 3 : 0), 12) === 0);
  const state = { key: null, r: 0, confidence: "unsure", candidate: null, locked: false };

  // Only chords count: a note, an interval or a cluster between F7 and Bbmaj7 leaves what was heard in place. A chord
  // on the root, 3rd or 5th of the I between them (part of the I, struck first) ends the V7 only once it has held for
  // CAD_SETTLE: a shell voicing's G and Bb a moment before the Eb bass read "Gm" and cancelled every Bb7 -> Ebmaj7 when
  // the tracker updated on each note, and a block C chord's bass and fifth a moment before its E read "C5"
  // and cancelled G7 -> C (the cadences went quiet, and the key of the V took over). Any other chord ends it at once (in real pedalled playing a passing dominant-seventh
  // name, then a sus4 and an add11 on its I, named a wrong key for 6 s).
  // A dominant seventh right after a chord on its own root held CAD_SETTLE (any but a minor, diminished or augmented one:
  // Dsus4 or Dadd9 before D7 is the I too) may be I7 or V7: its arrival is pending until the chords after it, each one
  // that holds CAD_SETTLE, decide by key (see the header). "Before" is the last chord that held CAD_SETTLE: a block chord's first notes read as another chord for a
  // moment, and C -> (Edim) -> C7 hid the C before the C7.
  function hear(chord) {
    if (!chord || chord.kind !== "chord" || !chord.root) return;
    const root = pcOf(chord.root), suffix = chord.suffix || "", family = FAMILY[suffix];
    if (!held || held.root !== root || held.suffix !== suffix) {
      const sec = held ? clock - held.since : 0;
      if (held && sec >= CAD_SETTLE) before = { ...held, sec };
      held = held && sec < CAD_SETTLE && before && before.root === root && before.suffix === suffix
        ? { root, suffix, since: before.since } : { root, suffix, since: clock };  // back from a momentary shape
    }
    const credit = (a) => { const i = keyIndex(a.root, a.mode); cadence[i] = Math.min(CAD_MAX, cadence[i] + 1); };
    if (pending) {
      const onRoot = root === pending.root, minorOwn = onRoot && pending.mode === "major" && family === "min";
      if (onRoot && !minorOwn) pending.next = null;
      else if (!pending.settled && clock - pending.since < CAD_SETTLE) pending = null;  // a momentary arrival
      else {
        pending.settled = true;
        const id = `${root}:${suffix}`;
        if (!pending.next || pending.next.id !== id) pending.next = { id, since: clock, judged: false };
        else if (!pending.next.judged && clock - pending.next.since >= CAD_SETTLE) {  // each chord that holds is judged once
          pending.next.judged = true;
          if (pending.dwell == null) pending.dwell = pending.next.since - pending.since;  // how long the arrival held
          const inArrival = fitsKey(root, suffix, pending.root, pending.mode), inHome = fitsKey(root, suffix, pending.from, "major");
          if (minorOwn || (inHome && !inArrival) || (root === pending.from && !pending.waited)) pending = null;  // colour
          else if (inArrival && (!inHome || pending.dwell >= ARRIVAL_DWELL * pending.iSec)) { credit(pending); pending = null; }
          else pending.waited = true;  // it fits both keys, or neither: a later chord may tell
        }
      }
      if (pending && pending.waited && clock - pending.since > PENDING_SEC) pending = null;  // never told: no evidence
    }
    if (DOMINANT.has(suffix)) {
      if (!dominant || dominant.root !== root) {
        const family0 = before && FAMILY[before.suffix];
        const shaped = !!before && before.root === root && family0 !== "min" && family0 !== "dim" && family0 !== "aug"
          && !DOMINANT.has(before.suffix) && before.sec >= CAD_SETTLE;
        dominant = { root, at: clock, shaped, iSec: shaped ? before.sec : 0 };
      } else dominant.at = clock;
      arrival = null; between = null;
      return;
    }
    if (arrival && root === arrival.root) {
      if (clock - arrival.since >= CAD_SETTLE) { credit(arrival); arrival = null; }
      return;
    }
    arrival = null;
    if (dominant && root === mod(dominant.root + 5, 12) && clock - dominant.at <= CAD_WINDOW && (family === "maj" || family === "min")) {
      const heard = { root, mode: family === "maj" ? "major" : "minor", since: clock };
      if (dominant.shaped) pending = { ...heard, from: dominant.root, iSec: dominant.iSec, settled: false, next: null };
      else arrival = heard;
      dominant = null; between = null;
    } else if (dominant && root !== dominant.root) {
      const step = mod(root - dominant.root - 5, 12);  // from the I it would resolve to: its root, 3rd or 5th wait
      if (step !== 0 && step !== 3 && step !== 4 && step !== 7) { dominant = null; between = null; }
      else if (!between || between.root !== root) between = { root, since: clock };
      else if (clock - between.since >= CAD_SETTLE) { dominant = null; between = null; }
    }
  }

  // hist: the caller's decaying pitch-class histogram (read, never kept). t: seconds on any steady clock.
  // chord: what sounds now, a Theory.detect result or null (optional; it feeds the V7 -> I cue).
  function update(hist, t, chord = null) {
    const W = sum(hist);
    const first = prev === null;
    const act = first ? 0 : Math.max(0, Math.min(t, lastNoteT + ACTIVE_SEC) - prevT);  // playing time since last update
    const grew = first ? hist.slice() : hist.map((x, i) => Math.max(0, x - prev[i]));  // what was struck since then
    const g = Math.exp(-act / SLOW_TAU);
    if (first || W < prevW / FRESH_DROP) {
      fast = hist.slice(); slow = hist.slice(); age = 0;
      chordSec.fill(0); allChordSec = 0; sounded = null; sounding.fill(0); soundingPcs = null; pending = null;
      if (!first && key && !locked) { stale = true; youngPick = false; provisional = false; challenger = null; banked.clear(); }
    } else {
      const f = Math.exp(-act / FAST_TAU);
      for (let i = 0; i < 12; i++) { fast[i] = fast[i] * f + grew[i]; slow[i] = slow[i] * g + grew[i]; }
    }
    if (sum(grew) > 1e-9) lastNoteT = t;
    prev = hist.slice(); prevT = t; prevW = W;
    clock += act;
    const heard = W >= MIN_WEIGHT;
    age = heard ? age + act : 0;
    const maturity = Math.min(1, age / YOUNG_SEC);
    const fade = Math.exp(-act / CAD_TAU);
    for (let i = 0; i < 24; i++) { cadence[i] *= fade; chordSec[i] *= g; }
    allChordSec *= g;
    if (sounded !== null) { allChordSec += act; if (sounded >= 0) chordSec[sounded] += act; }
    for (let i = 0; i < 12; i++) sounding[i] = sounding[i] * g + (soundingPcs && soundingPcs.has(i) ? act : 0);
    const midis = chord && Array.isArray(chord.notes)
      ? chord.notes.map((n) => (typeof n === "number" ? n : n && n.midi)).filter(Number.isFinite) : [];
    soundingPcs = midis.length ? new Set(midis.map((m) => mod(m, 12))) : null;
    sounded = homeChordOf(chord, midis);
    hear(chord);
    const homes = allChordSec > 0 ? Array.from({ length: 12 }, (_, tonic) => chordSec[keyIndex(tonic, "minor")] >= HOME_SHARE * allChordSec) : null;
    const barred = (k) => k.mode === "major"  // the key of a V7 that just resolved: F major after F7 -> Bb
      && cadence[keyIndex(mod(k.tonic + 5, 12), "major")] + cadence[keyIndex(mod(k.tonic + 5, 12), "minor")] >= CAD_BAR;
    // Major arrivals always add to their key. A minor arrival adds to its key only while that key and its parallel major
    // rank best and second best: E7 -> Am in C major is a secondary dominant and no evidence for A minor, but without
    // the bonus Dm D7/F# Gm A7 Dm Dm read D major for the whole piece.
    const majorBonus = cadence.map((c, i) => (i % 2 ? 0 : CAD_W * c));
    // The key of a V7 that keeps resolving, with fewer cadences of its own, ranks the edge under the key it resolves to.
    const underI = (r) => {
      for (const k of r) {
        const i = keyIndex(mod(k.tonic + 5, 12), "major");
        if (k.mode !== "major" || cadence[i] < CAD_BAR || cadence[keyIndex(k.tonic, "major")] >= cadence[i]) continue;
        const cap = r.find((x) => x.tonic === mod(k.tonic + 5, 12) && x.mode === "major").score - 2 * margin;
        if (k.score > cap) k.score = cap;
      }
      return r.sort((a, b) => b.score - a.score);
    };
    const rank = (h, mat, withBonus = true) => {
      const r = rankKeys(h, mat, 2 * margin, withBonus ? majorBonus : null, homes, sounding);
      const minor = keyIndex(r[0].tonic, "minor");
      if (!withBonus) return r;
      if (r[0].tonic !== r[1].tonic || cadence[minor] <= 0) return underI(r);
      const bonus = majorBonus.slice();
      bonus[minor] = CAD_W * cadence[minor];
      return underI(rankKeys(h, mat, 2 * margin, bonus, homes, sounding));
    };
    const ranked = rank(hist, maturity);

    if (stale && heard && W >= FIRST_WEIGHT && age >= FIRST_SEC) {  // the key from before a long pause: keep or drop it
      stale = false;
      const pick = rank(slow, 1).filter((k) => !barred(k));
      const mine = pick.find((k) => same(k, key));
      if (!mine || pick[0].score - mine.score >= margin) { key = null; banked.clear(); }  // the first-key rules read the new notes
      else youngPick = true;  // it stands, and the notes may still correct it while the histogram is young
    }
    if (heard && !key && !locked && W >= FIRST_WEIGHT && age >= FIRST_SEC && !(pending && age < FIRST_WAIT)) {
      const pick = rank(slow, 1).filter((k) => !barred(k));
      const lead = pick[0].score - pick[1].score;
      if (pick[0].r >= minR && (lead >= FIRST_GAP || age >= FIRST_WAIT)) {
        key = strip(pick[0]);
        youngPick = age < YOUNG_SEC;
        provisional = lead < FIRST_GAP; confirmSec = 0; challenger = null;
      }
    }
    let cur = key ? ranked.find((s) => same(s, key)) : ranked[0];
    if (key) shownAt.set(idOf(key), clock);

    // Every key that leads the shown one (by margin on the long histogram, and >= minR on the recent notes) banks
    // the playing time it leads. Bar-to-bar churn between D major, A major and B minor during a move to D would
    // restart a strict "continuous" clock forever. Only the supported key the long histogram ranks highest may
    // take over: while the old key fades, A major (the A/C# bar) can bank a hold even though D major outranks it.
    const now = heard && key && !locked && sum(fast) >= MIN_WEIGHT ? rankKeys(fast, maturity, 2 * margin, null, homes) : null;
    let top = null, switchTo = null;
    for (const k of ranked) {
      if (!key || same(k, key)) continue;
      const supported = !!now && k.r >= minR && now.find((s) => same(s, k)).score >= minR;
      const leading = supported && !barred(k) && k.score - cur.score >= margin;
      const need = shownAt.has(idOf(k)) && clock - shownAt.get(idOf(k)) <= RECENT_SEC ? 2 * holdSec : holdSec;
      const had = banked.get(idOf(k)) || 0;
      const next = leading ? Math.min(need, had + act) : Math.max(0, had - LEAD_DRAIN * act);
      if (next > 0) banked.set(idOf(k), next); else banked.delete(idOf(k));
      if (supported && !top) {  // ranked is best first
        top = k;
        if (leading && next >= need && (youngPick || age >= YOUNG_SEC)) switchTo = k;
      }
    }
    if (switchTo) {
      key = strip(switchTo); cur = switchTo; banked.clear();
      youngPick = youngPick && age < YOUNG_SEC;
      provisional = false; stale = false; challenger = null;
      shownAt.set(idOf(key), clock);
    }
    // A provisional key is re-examined on the slow histogram: a related key that outscores it there and leaves out less
    // of what sounds takes over once it has done so for holdSec of playing (twice that if shown within RECENT_SEC). It
    // needs no margin and no support on the recent notes: in an A minor blues the Dm7 bars read D minor on those, and C
    // major stood until 32 s. The better fit keeps an A dorian vamp from handing A minor to D major, and related() keeps
    // an E dorian one from handing E major (numbered 1m7 4) to G major (6m7 2).
    if (provisional && key && !switchTo) {
      const pick = rank(slow, 1).filter((k) => !barred(k));
      const best = pick[0], mine = pick.find((k) => same(k, key));
      const leads = !same(best, key) && !!mine && best.r >= minR && related(best, key) && best.score > mine.score
        && outShare(sounding, best.tonic, best.mode) < outShare(sounding, key.tonic, key.mode);
      if (leads) challenger = challenger && challenger.id === idOf(best) ? { id: challenger.id, sec: challenger.sec + act } : { id: idOf(best), sec: act };
      else if (challenger && (challenger.sec -= LEAD_DRAIN * act) <= 0) challenger = null;
      const need = shownAt.has(idOf(best)) && clock - shownAt.get(idOf(best)) <= RECENT_SEC ? 2 * holdSec : holdSec;
      if (leads && challenger.sec >= need) {
        key = strip(best); cur = ranked.find((s) => same(s, best)); banked.clear(); challenger = null;
        provisional = best.score - pick[1].score < FIRST_GAP; confirmSec = 0;
        youngPick = age < YOUNG_SEC;
        shownAt.set(idOf(key), clock);
      }
    } else challenger = null;

    const rival = key ? ranked.find((s) => !same(s, key)) : null;
    const gap = rival ? cur.score - rival.score : 0;
    const fifthAway = !!rival && rival.mode === key.mode && [5, 7].includes(mod(rival.tonic - key.tonic, 12));
    if (provisional) {  // a near-tie first key stands once it has led its runner-up by margin for holdSec of playing
      confirmSec = gap >= margin ? confirmSec + act : Math.max(0, confirmSec - LEAD_DRAIN * act);
      if (confirmSec >= holdSec) provisional = false;
    }
    let cand = null;
    for (const [id, sec] of banked) if (!cand || sec > cand.sec) cand = { id, sec };
    const candKey = cand && ranked.find((s) => idOf(s) === cand.id);
    state.key = key;
    state.r = cur.r;
    state.confidence = !key || !heard || age < YOUNG_SEC || provisional || (fifthAway && gap < margin) ? "unsure"
      : cur.score >= SURE_R && gap >= SURE_GAP ? "sure" : cur.score >= minR && gap >= 0 ? "fair" : "unsure";
    state.candidate = candKey ? { ...strip(candKey), r: candKey.r, heldSec: cand.sec } : null;
    state.locked = locked;
    return state;
  }

  // lock("D major") pins a key (the name's own tonic spelling is kept); lock(null) resumes tracking from it.
  function lock(keyName) {
    banked.clear();
    shownAt.clear();  // a lock is a choice, not flicker: afterwards no key needs the doubled hold to come back
    youngPick = false; stale = false; provisional = false;
    if (keyName == null) { locked = false; state.locked = false; return state; }
    const k = keyContext(keyName);
    if (!k) return state;
    key = strip(k);
    locked = true;
    state.key = key;
    state.locked = true;
    state.candidate = null;
    return state;
  }

  return { update, lock, state };
}
