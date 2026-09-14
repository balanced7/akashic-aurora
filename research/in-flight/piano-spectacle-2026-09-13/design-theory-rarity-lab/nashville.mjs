// Nashville numbers: arsenal/web/piano/nashville.js (pure ES module: no three.js, no DOM).
// Twin: arsenal/nashville.py. Both run every case in tests/fixtures/nashville_cases.json.
//
//   const tracker = createKeyTracker();
//   const { key } = tracker.update(pcHistory, t);   // the displayed key, held against flicker
//   nashville(Theory.detect(notes, key.bias), key)  // { text: "5^7/3", degree: 5, suffix: "7", ... }
//
// Conventions (the same words head arsenal/nashville.py):
// - Degree = letter distance from the key tonic's letter + 1. Accidental = semitone difference from that
//   degree of the tonic's MAJOR scale (b, #, bb rarely). In C major: Eb -> b3, F# -> #4, Bb -> b7.
// - Spelling is respected: F# stays #4 and Gb stays b5. A spelling that fits the key worse than its
//   enharmonic twin is respelled first (D#m in Eb minor reads 1m, not #7m); ties keep the spelling given.
// - Minor keys, option minor: "tonic" (default) numbers from the minor tonic with major-scale accidentals
//   (A minor: Am=1m, C=b3, Dm=4m, E=5, Em=5m, F=b6, G=b7). minor: "relative" numbers from the relative
//   major (A minor: Am=6m, C=1, F=4, G=5, E=3).
// - Suffixes: "m" -> minorMark ("m" by default, or "-"; it also replaces the leading m of m7, m9, m(add9)...),
//   "dim" -> "°", "dim7" -> "°7", "m7b5" -> "ø7", "aug" -> "+"; every other Theory.TEMPLATES suffix unchanged.
// - The text form is never ambiguous: a suffix digit that would touch the degree (or a "-" minor mark) is
//   joined with "^" ("5^7", "1^6", "1^5", "2-^7"). The structured fields let the overlay draw a superscript.
// - Slash chords add "/" + the bass degree ("1/3", "5/2", "4/b7").
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

function biasOf(tonic, mode) {
  const relMajor = mode === "major" ? tonic : mod(tonic + 3, 12);
  const fifths = mod(relMajor * 7, 12);
  return fifths === 0 ? 0 : fifths <= 6 ? 1 : -1;
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
  return { tonic, mode, name: `${nameOf(n.sp)} ${mode}`, bias: biasOf(tonic, mode) };
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

function respell(sp, ctx) {
  let best = sp, cost = Math.abs(scaleOffset(sp, ctx));
  const pc = pcOf(sp);
  for (let letter = 0; letter < 7; letter++) {
    const acc = mod(pc - LETTER_PC[letter] + 6, 12) - 6;
    if (Math.abs(acc) > 2 || letter === sp.letter) continue;  // double sharps too: G dim in G# minor is F## dim, 7°
    const c = Math.abs(scaleOffset({ letter, acc }, ctx));
    if (c < cost) { best = { letter, acc }; cost = c; }
  }
  return best;
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

// { degree, acc, text } in the chosen numbering, plus tonic-numbered tdeg/tacc for the diatonic test.
function numberNote(sp, ctx, minor) {
  const s = respell(sp, ctx);
  const t = degreeFrom(s, ctx.sp);
  const out = ctx.mode === "minor" && minor === "relative" ? degreeFrom(s, relativeMajor(ctx)) : t;
  return { ...out, tdeg: t.degree, tacc: t.acc };
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
  const r = numberNote(root, ctx, minor);
  if (kind === "note") {
    return { text: r.text, degree: r.degree, acc: r.acc, root: r.text, suffix: "", bass: null, upper: null,
             diatonic: inScale(r, ctx), kind };
  }
  if (kind === "interval") {
    const u = numberNote(upper, ctx, minor);
    return { text: `${r.text}-${u.text}`, degree: r.degree, acc: r.acc, root: r.text, suffix: "", bass: null,
             upper: pub(u), diatonic: inScale(r, ctx) && inScale(u, ctx), kind };
  }
  const sfx = suffixText(suffix, minorMark);
  const b = bass ? numberNote(bass, ctx, minor) : null;
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
// The displayed key changes only after one different key leads it by >= margin for holdSec without a break.
// The first key appears once the best r reaches minR (and FIRST_WEIGHT of notes is in). Silence holds the key.
//
// Three guards, each found on the F/A C/G Dm Bbmaj7 -> D A/C# Bm G test score (tests/nashville_js.test.mjs):
// - Rank by score, not raw r. Krumhansl-Kessler alone cannot separate a key from its relative minor when the
//   harmony leans on vi (that F major loop correlates best with D minor). A minor key whose raised leading
//   tone (C# in D minor, the major V's third) is unheard scores just under its relative major; a leading tone
//   at LT_SHARE of the tonic's weight lifts it back to its own r, and part of one lifts it part way. The rule
//   phases in over the histogram's first YOUNG_SEC, since no V chord can have been heard yet in bar one.
//   A natural-minor loop with no leading tone therefore settles on its relative major (Am F C G -> C major,
//   numbered 6m 4 1 5), the way Nashville charts number it; lock() is there for the other reading.
// - A challenger must also be heard now: it counts only while it scores >= minR on a FAST_TAU histogram of the
//   notes played since recent updates. The 12 s histogram blends the old key into the new one (F major memory
//   plus a fresh C# reads as D minor for eight seconds of a move to D major); the recent notes do not.
// - A young histogram holds one or two bars, and any bar reads as its own key (C/G is C major), so no switch
//   completes until YOUNG_SEC after the histogram starts, or restarts after a pause long enough to fade it.
const MIN_WEIGHT = 2;     // estimateKey's own floor: under two note-ons of weight there is nothing to read
const FIRST_WEIGHT = 6;   // about five notes before a first key is shown
const LT_SHARE = 0.25;
const LT_EDGE = 0.02;     // how far under its relative major an unproven minor key sits
const FAST_TAU = 4;       // seconds: about a bar at 80 bpm
const YOUNG_SEC = 12;     // piano.js's pcHistory decay time
const FRESH_DROP = 4;     // total weight falling below a quarter between updates means the old notes have faded
const SURE_R = 0.75, SURE_GAP = 0.08;

// scoreKeys plus a tracker score (see above), best score first. maturity 0..1 phases the leading-tone rule in.
export function rankKeys(hist, maturity = 1) {
  const scores = scoreKeys(hist);
  const rOf = (tonic, mode) => scores.find((s) => s.tonic === tonic && s.mode === mode).r;
  return scores.map((k) => {
    if (k.mode === "major") return { ...k, score: k.r };
    const tonicW = hist[k.tonic], lt = hist[mod(k.tonic + 11, 12)];
    const heard = tonicW > 0 ? Math.min(1, lt / (LT_SHARE * tonicW)) : 0;
    const over = Math.max(0, k.r - rOf(mod(k.tonic + 3, 12), "major") + LT_EDGE);
    return { ...k, score: k.r - maturity * (1 - heard) * over };
  }).sort((a, b) => b.score - a.score);
}

export function createKeyTracker({ holdSec = 3, margin = 0.04, minR = 0.55 } = {}) {
  let key = null, cand = null, since = 0, locked = false;
  let prev = null, prevT = 0, prevW = 0, freshAt = null, fast = new Array(12).fill(0);
  const strip = (k) => ({ tonic: k.tonic, mode: k.mode, name: k.name, bias: k.bias });
  const same = (a, b) => !!(a && b && a.tonic === b.tonic && a.mode === b.mode);
  const sum = (xs) => xs.reduce((a, b) => a + b, 0);
  const state = { key: null, r: 0, confidence: "unsure", candidate: null, locked: false };

  // hist: the caller's decaying pitch-class histogram (read, never kept). t: seconds on any steady clock.
  function update(hist, t) {
    const W = sum(hist);
    const faded = prev !== null && W < prevW / FRESH_DROP;
    if (prev === null || faded) {
      fast = hist.slice();
      freshAt = null;
    } else {
      const f = Math.exp(-Math.max(0, t - prevT) / FAST_TAU);
      fast = fast.map((x, i) => x * f + Math.max(0, hist[i] - prev[i]));  // what grew since the last update
    }
    prev = hist.slice(); prevT = t; prevW = W;
    const heard = W >= MIN_WEIGHT;
    if (heard && freshAt === null) freshAt = t;
    if (!heard) freshAt = null;

    const maturity = freshAt === null ? 0 : Math.min(1, (t - freshAt) / YOUNG_SEC);
    const ranked = rankKeys(hist, maturity);
    const best = ranked[0];
    if (heard && !key && W >= FIRST_WEIGHT && best.r >= minR) key = strip(best);
    let cur = key ? ranked.find((s) => same(s, key)) : best;
    let challenger = null;
    if (heard && key && !locked && sum(fast) >= MIN_WEIGHT) {
      const now = rankKeys(fast, maturity);
      challenger = ranked.find((k) => !same(k, key) && k.score - cur.score >= margin && k.r >= minR
                                      && now.find((s) => same(s, k)).score >= minR) || null;
    }
    if (challenger) {
      if (!same(cand, challenger)) { cand = strip(challenger); since = t; }
      if (t - since >= holdSec && t - freshAt >= YOUNG_SEC) { key = cand; cand = null; cur = challenger; }
    } else if (heard) {
      cand = null;
    }
    const rival = key ? ranked.find((s) => !same(s, key)) : null;
    const gap = rival ? cur.score - rival.score : 0;
    state.key = key;
    state.r = cur.r;
    state.confidence = !key || !heard ? "unsure"
      : cur.score >= SURE_R && gap >= SURE_GAP ? "sure" : cur.score >= minR && gap >= 0 ? "fair" : "unsure";
    state.candidate = cand ? { ...cand, r: ranked.find((s) => same(s, cand)).r, heldSec: t - since } : null;
    state.locked = locked;
    return state;
  }

  // lock("D major") pins a key (the name's own tonic spelling is kept); lock(null) resumes tracking from it.
  function lock(keyName) {
    cand = null;
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
