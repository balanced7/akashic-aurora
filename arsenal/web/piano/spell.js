// The one shared speller: arsenal/web/piano/spell.js (pure ES module: no three.js, no DOM).
// Ruling: research/in-flight/piano-theory-nextgen-2026-09-14/tn1-rulings.md, "Round 5-6 status and the spelling ruling for
// TN2" (rules 1-5). The chord reader (chordread.js) names every reading with it; live sheet music (LS6,
// research/in-flight/live-sheet-music-2026-09-14/ls1-rulings.md) spells staff notes and draws key signatures with it.
// Tests: tests/piano_spell.test.mjs.
//
//   import { spellChord, chordName, spellNote, keySignature } from "./piano/spell.js";
//   const s = spellChord({ rootPc: 10, tonesPc: [10, 2, 6, 8], bassPc: 2, key: "F# major", steps: { 4: 2, 8: 4, 10: 6 } });
//   chordName(s, "7#5")                  // "Bb7#5/D" (A#7#5/D would spell its 3rd and #5 C## and E##)
//   s.map[2]                             // { letter: 1, acc: 0 }: every tone and the bass, by pitch class
//   spellNote(6, "Db major").name        // "Gb"
//   keySignature("Db major")             // { key: "Db major", type: "flats", count: 5, accidentals: [{ letter: 6, acc: -1, name: "Bb" }, ...] }
//
// The rule (tn1-rulings.md rules 1-3, as built here):
// 1. Chord tones first. Each candidate root (every spelling of the root's pitch class with one accidental at most: the
//    key's spelling and its enharmonic) spells every chord tone by its letter steps from the root, and the bass (3). A
//    candidate's score is the sum of its notes' costs; the lowest score wins.
// 2. Ties go to the key's spelling of the root (nashville.js spellInKey: the letters the Nashville number reads), then to
//    the bias spelling (Theory.spellAlone: sharps in sharp keys, flats in flat keys, Db Eb F# Ab Bb when neutral).
// 3. The bass is spelled as a chord tone of the chosen root when it is one, and otherwise in the key by the same note cost
//    (with no key, leaning the way the chord's own accidentals lean: G#m/C#, not G#m/Db).
// Note cost, counted against the key (a note on the key's scale needs no accidental, as its key signature shows it):
//   0  the key's own scale spelling (a minor key's raised 7th included, unless the chord also holds its lowered 7th);
//      off the scale, a natural;
//   1  one sharp or flat off the key's scale;
//   2  an odd letter (B#, E#, Cb, Fb) off the key's scale, or a pitch of the key's scale written on another letter
//      (A# in Bb major, Gb in B minor);
//   3  a double accidental, on or off the scale;
//   a triple accidental is forbidden.
// With no key every note is off the scale: naturals 0, sharps and flats 1, odd letters 2, doubles 3.
// Hard edges (rule 5's receipts): a root never takes a double accidental (every candidate holds one at most); a bass that
// would need one as a chord tone, and a tone that would need a triple, are written in the key instead. A candidate that
// needs either is taken only when every candidate does.
// The key's own root on a double accidental (TN2 repair round 1): when the key spells the root with two accidentals (F## dim7,
// the leading-tone chord of G# minor), one more candidate spells every other tone from that spelling and writes only the root
// on its neighbouring letter (G A# C# E, not G Bb Db E: A#, C# and E are the key's own notes). It wins only on a strictly lower
// score.
// A dim7's 7th (repair round 1): letter steps may offer a choice (steps [6, 5]: a diminished 7th, or a 6th as lead sheets write
// C Eb Gb A); the cheaper spelling against the key wins, ties to the first. B D F Ab in C minor (Ab is the key's own note, G#
// would need an accidental); C Eb Gb A with no key (Bbb would be a double).
//
// Why the count is against the key (rule 1 says "the sum of accidentals"): the ruling's own receipt keeps F#+ in B minor
// (F# A# C##), and a plain sum picks Gb+ (Gb Bb D: 2 against 5). Counted against B minor, F# and A# are the key's own notes
// (0) and Gb and Bb are its F# and A# on other letters (2 each): F#+ 3, Gb+ 4. The same count gives the ruling's other
// cases (C+(add9) in C# minor, F+(add9) in F# major, Eb+(add9) in A major, Cb+(add9) in Eb minor), and flat keys never show
// sharps for their own notes (LS6).
// Why a minor key's raised 7th leaves its scale when the chord holds the lowered 7th: E G# B over C in C# minor holds B,
// so its C is no leading tone (E/C, not E/B#, which would put B and B# on one letter).
import { parseKey, spellInKey } from "./nashville.js";

export const SPELL_API = "arsenal.piano.spell/v1";

const LETTERS = ["C", "D", "E", "F", "G", "A", "B"];
const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
const MAJOR = [0, 2, 4, 5, 7, 9, 11];
const NATURAL_MINOR = [0, 2, 3, 5, 7, 8, 10];
const MAJOR_KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const MINOR_KEY_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"];
const ODD = new Set(["E#", "B#", "Cb", "Fb"]);
const NEUTRAL = { 1: -1, 3: -1, 6: 1, 8: -1, 10: -1 };  // Db Eb F# Ab Bb, as Theory.spellAlone
const SHARP_ORDER = [3, 0, 4, 1, 5, 2, 6];              // F C G D A E B
const FLAT_ORDER = [6, 2, 5, 1, 4, 0, 3];               // B E A D G C F
const mod = (a, n) => ((a % n) + n) % n;

// Letter steps above a root by semitones, as Theory.detect's templates count them (a 6 is a 4th letter up, a b5).
export const IV_STEPS = Object.freeze([0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6]);
export const accText = (acc) => (acc > 0 ? "#".repeat(acc) : "b".repeat(-acc));
export const nameOf = (sp) => LETTERS[sp.letter] + accText(sp.acc);
export const pcOf = (sp) => mod(LETTER_PC[sp.letter] + sp.acc, 12);
const plain = (sp) => ({ letter: sp.letter, acc: sp.acc });
const same = (a, b) => !!a && !!b && a.letter === b.letter && a.acc === b.acc;
const isOdd = (sp) => (sp.acc === 1 && (sp.letter === 2 || sp.letter === 6)) || (sp.acc === -1 && (sp.letter === 0 || sp.letter === 3));  // E# B# Cb Fb

// The note `steps` letters and `semis` semitones above a spelling (Theory.spellInterval).
export function spellInterval(rootSp, semis, steps) {
  const letter = mod(rootSp.letter + steps, 7);
  return { letter, acc: mod(pcOf(rootSp) + semis - LETTER_PC[letter] + 6, 12) - 6 };
}

// Every spelling of a pitch class with one accidental at most (Theory.spellingsOf): two for every pitch class but D, G and A.
export function spellingsOf(pc) {
  const out = [];
  for (let letter = 0; letter < 7; letter++) {
    const acc = mod(pc - LETTER_PC[letter] + 6, 12) - 6;
    if (Math.abs(acc) <= 1) out.push({ letter, acc });
  }
  return out;
}

// A note on its own, by the bias alone (Theory.spellAlone, the same costs): never B#, E#, Cb or Fb; sharps when the bias is
// positive, flats when negative; when neutral, Db Eb F# Ab Bb.
const ALONE = new Map();  // only the bias's sign matters: memoised by pitch class and sign
export function spellAlone(pc, bias = 0) {
  const p = mod(Math.round(pc), 12), id = p * 3 + (bias > 0 ? 1 : bias < 0 ? 2 : 0);
  if (!ALONE.has(id)) {
    let top = null;
    for (const sp of spellingsOf(p)) {
      const a = Math.abs(sp.acc);
      let c = a + (isOdd(sp) ? 1 : 0);
      if ((bias > 0 && sp.acc < 0) || (bias < 0 && sp.acc > 0)) c += 0.6 * a;
      if (NEUTRAL[p] && Math.sign(sp.acc) !== NEUTRAL[p]) c += 0.01;
      if (!top || c < top.c) top = { sp, c };
    }
    ALONE.set(id, top.sp);
  }
  const s = ALONE.get(id);
  return { letter: s.letter, acc: s.acc };
}

// ------------------------------------------------------------------------------------------------------ keys --
// A key as the speller reads it: { name, tonic, mode, bias, tonicSp, scale (letter -> accidentals on the scale), scalePcs,
// signature (letter -> accidental in the key signature), subtonicPc, natural }. A minor key's scale holds its raised 7th
// (the leading tone, as nashville.js and chordread.js count it); `natural` is the same key without it. Cached by name.
// key: a key name ("Db major"), a tracker key ({ name } or { tonic, mode }), a context, or null.
const KEYS = new Map();
export function keyContext(key) {
  if (!key) return null;
  if (Array.isArray(key.scale) && key.scalePcs instanceof Set) return key;
  const text = typeof key === "string" ? key
    : typeof key.name === "string" ? key.name
    : Number.isInteger(key.tonic) && (key.mode === "major" || key.mode === "minor")
      ? `${(key.mode === "major" ? MAJOR_KEY_NAMES : MINOR_KEY_NAMES)[mod(key.tonic, 12)]} ${key.mode}` : null;
  if (text == null) return null;
  if (KEYS.has(text)) return KEYS.get(text);
  const k = parseKey(text);
  let ctx = null;
  if (k) {
    const m = /^([A-G])(#{1,2}|b{1,2})?/.exec(k.name);
    const tonicSp = { letter: LETTERS.indexOf(m[1]), acc: !m[2] ? 0 : m[2][0] === "#" ? m[2].length : -m[2].length };
    const degrees = k.mode === "major" ? MAJOR : NATURAL_MINOR;
    const signature = LETTERS.map(() => 0);
    degrees.forEach((semis, d) => { signature[mod(tonicSp.letter + d, 7)] = spellInterval(tonicSp, semis, d).acc; });
    const scaleOf = (leading) => {
      const scale = LETTERS.map(() => []);
      degrees.forEach((semis, d) => { const s = spellInterval(tonicSp, semis, d); scale[s.letter].push(s.acc); });
      if (leading) { const s = spellInterval(tonicSp, 11, 6); if (!scale[s.letter].includes(s.acc)) scale[s.letter].push(s.acc); }
      const scalePcs = new Set();
      scale.forEach((accs, letter) => accs.forEach((a) => scalePcs.add(mod(LETTER_PC[letter] + a, 12))));
      return { scale, scalePcs };
    };
    const common = { name: k.name, tonic: k.tonic, mode: k.mode, bias: k.bias, tonicSp, signature, keySp: new Map() };
    const minor = k.mode === "minor";
    ctx = { ...common, ...scaleOf(minor), subtonicPc: minor ? mod(k.tonic + 10, 12) : null, natural: null };
    if (minor) ctx.natural = { ...common, keySp: common.keySp, ...scaleOf(false), subtonicPc: null, natural: null };
  }
  KEYS.set(text, ctx);
  return ctx;
}

// The cost of one spelled note against a key (null: no key). See the header.
export function toneCost(sp, key = null) {
  const K = keyContext(key);
  const a = Math.abs(sp.acc);
  if (a >= 3) return Infinity;
  if (a === 2) return 3;
  if (K && K.scale[sp.letter].includes(sp.acc)) return 0;
  if (isOdd(sp) || (K && K.scalePcs.has(pcOf(sp)))) return 2;
  return a;
}

// The key's spelling of a pitch class (nashville.js spellInKey, from the bias spelling; suffix: a chord root's suffix, so a
// chord on the tritone reads b5 and a diminished chord leads up, as the number does). Cached on the key.
function keySpelling(pc, K, suffix, bias, minor) {
  if (!K) return null;
  // a note (suffix null) and a major triad (suffix "") read the chart differently on the tritone: never one cache entry
  const id = `${pc}|${suffix == null ? "~note" : suffix}|${bias}|${minor === "relative" ? "r" : "t"}`;
  if (!K.keySp.has(id)) {
    const s = spellInKey(spellAlone(pc, bias), K.name, { suffix: suffix ?? null, minor: minor === "relative" ? "relative" : "tonic" });
    K.keySp.set(id, s ? { letter: s.letter, acc: s.acc } : null);
  }
  return K.keySp.get(id);
}

// The best of scored spellings: fewest forced notes, then the lowest score, then a plain candidate before one spelled from
// the key's double-accidental root (it.virtual), then the key's spelling, then the bias spelling, then the order given.
function best(items, keySp, biasSp) {
  let top = null, tk = 1, tb = 1;
  for (const it of items) {
    const k = same(it.sp, keySp) ? 0 : 1, b = same(it.sp, biasSp) ? 0 : 1, v = it.virtual ? 1 : 0, tv = top && top.virtual ? 1 : 0;
    if (!top || it.forced < top.forced || (it.forced === top.forced && (it.score < top.score
      || (it.score === top.score && (v < tv || (v === tv && (k < tk || (k === tk && b < tb)))))))) { top = it; tk = k; tb = b; }
  }
  return top;
}

// A note in a key context (no chord): the cheapest spelling, ties to the key's spelling, then the bias.
function noteIn(pc, K, bias, minor) {
  const biasSp = spellAlone(pc, bias);
  if (!K) return biasSp;
  const keySp = keySpelling(pc, K, null, bias, minor);
  const cands = spellingsOf(pc);
  if (keySp && !cands.some((c) => same(c, keySp))) cands.push(keySp);
  return best(cands.map((sp) => ({ sp, forced: 0, score: toneCost(sp, K) })), keySp, biasSp).sp;
}

// One note: { letter, acc, name, inScale }. context (all optional): bias (with no key), minor ("tonic" or "relative", the
// page's numbering), chord (a spellChord result: its tones and bass keep the chord's spelling).
// With no key it is Theory.spellAlone's spelling; in a key, the cheapest spelling by the note cost, ties to the key's.
export function spellNote(pc, key = null, context = {}) {
  const p = mod(Math.round(pc), 12);
  const K = keyContext(key);
  const known = context && context.chord && context.chord.map ? context.chord.map[p] : null;
  const sp = known || noteIn(p, K, K ? K.bias : Number(context && context.bias) || 0, context && context.minor);
  return { letter: sp.letter, acc: sp.acc, name: nameOf(sp), inScale: !!K && K.scale[sp.letter].includes(sp.acc) };
}

// A sounding MIDI note spelled for a staff: spellNote plus octave (B#3 is MIDI 60) and diatonic (C4 = 28), as piano.js
// Theory.octaveOf and Theory.diatonicOf count them.
export function spellMidi(midi, key = null, context = {}) {
  const m = Math.round(midi);
  const s = spellNote(m, key, context);
  const octave = Math.floor((m - s.acc) / 12) - 1;
  return { midi: m, ...s, octave, diatonic: octave * 7 + s.letter };
}

// Letter steps for a tone when the caller gives none, from the tones beside it (chordread.js letterSteps): a 3 is a #9 over
// a major 3rd, else a minor 3rd; a 6 is a #11 over a 5th (or a major 3rd with no minor 3rd), else a b5; an 8 is a b13 over
// a 5th or a b5, else a #5; a 9 is a 6th, except in a dim7's shape (a minor 3rd and a b5, no 3rd, 5th or b7), where it is
// the choice [6, 5]: a diminished 7th, or a 6th when that is cheaper (spellChord picks; C Eb Gb A, B D F Ab in C minor).
// Returns a number of letter steps, or an array of choices, first preferred.
export function defaultSteps(ivs, iv) {
  const has = ivs instanceof Set ? (x) => ivs.has(x) : (x) => ivs.includes(x);
  if (iv === 3) return has(4) ? 1 : 2;
  if (iv === 6) return has(7) || (has(4) && !has(3)) ? 3 : 4;
  if (iv === 8) return has(7) || has(6) ? 5 : 4;
  if (iv === 9 && has(3) && has(6) && !has(4) && !has(7) && !has(10)) return DIM7_SEVENTH.slice();
  return IV_STEPS[iv];
}
// A dim7's 7th: a diminished 7th (6 letter steps), or a 6th (5) when that needs fewer accidentals against the key.
export const DIM7_SEVENTH = Object.freeze([6, 5]);

// A chord: rootPc, tonesPc (the pitch classes it names; the root is added), steps ({ semitones above the root: letter
// steps }, from the chord's suffix; defaultSteps fills the rest), bassPc (null when the bass is the root), key, bias (with no
// key), suffix (the root's suffix for the key's spelling, nashville.js FAMILY: "maj7", "m", "aug"), minor, rootSp (a fixed
// root spelling: the rest spelled from it, as a name already chosen).
// Returns { root, bass, parts: { root, bass } (names), tones: [{ iv, pc, steps, letter, acc, name }], map: { pc: spelling },
// score, forced (notes written in the key because letter steps would give a triple, or a double on the bass), key,
// candidates: [{ root, score, forced }] }.
export function spellChord({ rootPc, tonesPc = [], steps = null, bassPc = null, key = null, bias = 0, suffix = null, minor = "tonic", rootSp = null } = {}) {
  const root = mod(Math.round(rootPc), 12);
  const K0 = keyContext(key);
  const b = K0 ? K0.bias : Number(bias) || 0;
  const ivs = [...new Set([0, ...(tonesPc || []).filter((p) => Number.isFinite(p)).map((p) => mod(Math.round(p) - root, 12))])].sort((x, y) => x - y);
  const has = new Set(ivs);
  const bpc = Number.isFinite(bassPc) ? mod(Math.round(bassPc), 12) : null;
  const bassIv = bpc === null || bpc === root ? null : mod(bpc - root, 12);
  const bassTone = bassIv !== null && has.has(bassIv);
  // A minor key's raised 7th is no scale note while the chord holds the lowered 7th (E G# B over C in C# minor: E/C).
  const K = K0 && K0.natural && (ivs.some((iv) => mod(root + iv, 12) === K0.subtonicPc) || bpc === K0.subtonicPc) ? K0.natural : K0;
  const stepChoice = (x) => Number.isInteger(x) || (Array.isArray(x) && x.length > 0 && x.every(Number.isInteger));
  const stepOf = (iv) => (steps && stepChoice(steps[iv]) ? steps[iv] : defaultSteps(has, iv));
  // A tone spelled from a root: by its letter steps, or, from a choice, the key's own scale spelling first, then one that
  // needs no double accidental, then the first choice (a dim7: B D F Ab in C minor, D F Ab Cb in Eb major, C Eb Gb A with
  // no key or in Db major, where Bbb would be a double).
  const choiceRank = (sp) => (Math.abs(sp.acc) >= 2 ? 2 : K && K.scale[sp.letter].includes(sp.acc) ? 0 : 1);
  const toneFrom = (from, iv) => {
    const choice = stepOf(iv);
    let top = null;
    for (const st of Array.isArray(choice) ? choice : [choice]) {
      const sp = spellInterval(from, iv, st), rank = choiceRank(sp);
      if (!top || rank < top.rank) top = { sp, st, rank, c: toneCost(sp, K) };
    }
    return top;
  };
  // With no key, a bass spelled on its own leans the way the chord's accidentals lean (G#m/C#, not G#m/Db), then the bias.
  const bassBias = (tones) => (K ? b : Math.sign(tones.reduce((s, t) => s + Math.sign(t.acc), 0)) || b);
  const keySp = keySpelling(root, K, suffix, b, minor);
  const biasSp = spellAlone(root, b);
  const fixedRoot = !!rootSp && Number.isInteger(rootSp.letter) && Number.isInteger(rootSp.acc);
  const cands = (fixedRoot ? [plain(rootSp)] : spellingsOf(root)).map((sp) => ({ written: sp, from: sp, virtual: false }));
  // The key's root on a double accidental (F## in G# minor): the chord's other tones spelled from it, the root written on its
  // neighbouring letter (G). See the header. Only a double the key's scale holds (a leading tone: F## in G# minor, C## in D#
  // minor), never a chart degree (Ebb, the b5 of A-flat major, would spell Dmaj7 D Gb Bbb Db). A fixed root (a name already
  // chosen) takes it too when it is that neighbour.
  if (K && keySp && Math.abs(keySp.acc) === 2 && K.scale[keySp.letter].includes(keySp.acc)) {
    const written = spellingsOf(root).find((sp) => sp.letter === mod(keySp.letter + Math.sign(keySp.acc), 7));
    if (written && (!fixedRoot || same(written, rootSp))) cands.push({ written, from: plain(keySp), virtual: true });
  }
  const trials = cands.map(({ written: rsp, from, virtual }) => {
    const map = { [root]: rsp };
    const tones = [{ iv: 0, pc: root, steps: 0, letter: rsp.letter, acc: rsp.acc }];
    let score = toneCost(rsp, K), forced = 0;
    for (const iv of ivs) {
      if (iv === 0) continue;
      const pc = mod(root + iv, 12);
      let { sp, st, c } = toneFrom(from, iv);
      if (c === Infinity) { sp = noteIn(pc, K, b, minor); c = toneCost(sp, K); forced++; }  // a triple is forbidden
      map[pc] = sp;
      score += c;
      tones.push({ iv, pc, steps: st, letter: sp.letter, acc: sp.acc });
    }
    let bass = null;
    if (bassIv !== null) {
      if (bassTone) {
        bass = map[bpc];
        if (Math.abs(bass.acc) > 1) {                                                      // never a double on the bass
          const was = toneCost(bass, K);
          bass = noteIn(bpc, K, bassBias(tones), minor);
          score += toneCost(bass, K) - was;
          forced++;
          map[bpc] = bass;
          const t = tones.find((x) => x.pc === bpc);
          t.letter = bass.letter;
          t.acc = bass.acc;
        }
      } else {
        bass = noteIn(bpc, K, bassBias(tones), minor);
        score += toneCost(bass, K);
        map[bpc] = bass;
      }
    }
    return { sp: rsp, from, virtual, map, tones, bass, score, forced };
  });
  const top = best(trials, keySp, biasSp);
  const map = {};
  for (const [pc, sp] of Object.entries(top.map)) map[pc] = plain(sp);
  return {
    root: plain(top.sp), bass: top.bass ? plain(top.bass) : null,
    parts: { root: nameOf(top.sp), bass: top.bass ? nameOf(top.bass) : null },
    tones: top.tones.map((t) => ({ ...t, name: nameOf(t) })), map, score: top.score, forced: top.forced, key: K0 ? K0.name : null,
    // from: a candidate spelled from the key's double-accidental root (its tones' letters), written on `root`
    candidates: trials.map((t) => ({ root: nameOf(t.sp), score: t.score, forced: t.forced, ...(t.virtual ? { from: nameOf(t.from) } : {}) })),
  };
}

// A chord name from a spellChord result and its suffix: "Bb" + "7#5" + "/D".
export const chordName = (spelled, suffix = "") => spelled.parts.root + (suffix || "") + (spelled.parts.bass ? "/" + spelled.parts.bass : "");

// A key signature: { key, type: "sharps" | "flats" | "none", count, accidentals: [{ letter, acc, name }] } in the order a
// staff writes them (F C G D A E B for sharps, B E A D G C F for flats). A minor key takes its relative major's signature.
// No key (or an unreadable one) has none.
export function keySignature(key) {
  const K = keyContext(key);
  if (!K) return { key: null, type: "none", count: 0, accidentals: [] };
  const flats = K.signature.some((a) => a < 0), sharps = K.signature.some((a) => a > 0);
  const order = flats && !sharps ? FLAT_ORDER : SHARP_ORDER;
  const accidentals = order.filter((l) => K.signature[l] !== 0).map((l) => ({ letter: l, acc: K.signature[l], name: nameOf({ letter: l, acc: K.signature[l] }) }));
  return { key: K.name, type: sharps ? "sharps" : flats ? "flats" : "none", count: accidentals.length, accidentals };
}
