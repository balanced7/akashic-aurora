// Next-gen chord reader: arsenal/web/piano/chordread.js (pure ES module: no three.js, no DOM).
// Spec: research/in-flight/piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md 2.1-2.2 (TN1), with the grammar, costs,
// bands and tags of design-engine.md 3.1-3.2 and 4.1-4.5 and the amendments A1-A7. Tests: tests/theory_chordread.test.mjs
// against tests/fixtures/theory/ (the TN0 corpus).
//
//   import { createReader, installReader } from "./piano/chordread.js";
//   const reader = createReader({ Theory, NV });              // Theory: piano.js's THEORY block, injected (never copied)
//   const res = reader.read(midis, { key: "Db major", prev: { root: 8 } });
//   res.readings[0].name                                      // "Gbmaj13#11", res.band "clear"
//   reader.alsoOf(res, Theory.detectTemplates(midis, bias), heldMs)   // { name: "Bbm11/Gb", kind: "was" } once held 1 s
//   reader.closeOf(res, heldMs)                               // the HUD's close runner-up, or null
//   installReader(Theory, NV)                                 // Theory.detectTemplates = today's detect; Theory.read and
//                                                             // Theory.detect come from the reader (same info shape)
//
// Frozen shapes (tests/fixtures/theory/contracts.schema.json $defs; additive fields are allowed):
//   Reading    = { root: pc, suffix, bass: pc | null (null when the bass is the root), name, cost, p: 0..1,
//                  reasons: [plain strings, each a lexicon reason.* entry], base: { id, family }, tensions: [semis],
//                  omit: { no3, no5, rootless }, path: "full" | "slash" | "drop" | "template" }
//   ReadResult = { kind: "chord" | "cluster" | "small", readings: [Reading], band: "clear" | "leaning" | "ambiguous" | "none",
//                  margin, confidence: 0..1, tags: [{ tag: "upper structure" | "polychord" | "quartal" | "cluster", ... }],
//                  key: key name | null (additive: alsoOf spells in it) }
//   AlsoResult = { name, kind: "was" } | null
//   DetectInfo = today's Theory.detect info ({ kind, root, suffix, bass, name, sub, pcNames, notes, cost }) plus readings,
//                band, tags, no3, rootless. Its root and bass always sound (both are among info.notes), so piano.js's
//                spellForKey, the label, the number, the HUD and the practice log's chord event read it as they read
//                today's info. A top reading whose root does not sound (rootless) is named by the first listed reading
//                whose root sounds (else today's template info), and the rootless top is the additive
//                info.rootless = { root: spelling, name, suffix, bass: spelling | null } (null otherwise). tn1-rulings.md 2.
//   ParsedSuffix = { tones: { semis: letterSteps }, family, dominant, tensions: [semis] } (+ base, quality, no3, known)
//
// Rulings (research/in-flight/piano-theory-nextgen-2026-09-14/tn1-rulings.md; they win over the spec where they differ):
// - A6, honest calibration, stacked-4ths cap (ratified): three pitch classes holding bass+5 and bass+10 (D G C) are never
//   clear. They are D7sus4 without its 5th, Gsus4 over its 5th or Csus2 over its 9. It demotes 3 real windows of S1-S6
//   and changes no fixture band.
// - Cluster band: a result of kind "cluster" reports band "none" (it makes no chord-name claim).
// - The 6/9 without its 5th (root, 3rd, 6th, 9th: C E A D) reads C6/9 on top in every key and with no key. Its other
//   name, the relative minor over its own 3rd with the 11 added (Am(add11)/C), is the same notes named from the 6th: it
//   ranks directly behind the 6/9, SAME_NOTES_STEP behind, where its 5th-present twin (Am7(11)/C behind C6/9) ranks. A
//   rank rule, not a cost term: the voicings that sound the 5th never meet it (Gb6/9 over Ebm7(11)/Gb keeps its reading).
// - The 9 chord with no 3rd with its root doubled above (C3 G3 C4 D4 Bb4) reads C9(no3) on top (Cm9(no3) where the key
//   gives C a minor 3rd), leaning, in every key and with no key: its twin Gm(add11)/C, the minor on its 5th over its own
//   11, ranks SAME_NOTES_STEP behind it (round 4, the same rank rule as the 6/9). With the root only in the bass
//   (C3 G3 Bb3 D4) Gm/C stays on top as the costs give it.
// - Same-notes twins are never clear while the other is a reading within 1.5: the Lydian 4 and the gospel 5 over 4
//   (Ab6/9#11 and Bb11/Ab, design-engine 9.9) and a maj13 with no 9 and its relative m9 over its 3rd (Dbmaj13 and
//   Bbm9/Db). Round 4, a measured band rule, awaiting the conductor's ratification as A6's cap had.
// - Template fallback: when the grammar has no reading, the page's template name is taken over opts.bassMidi when it is
//   given, and dropped when its bass is another sounding note.
//
// Conventions:
// - Families (Reading.base.family): maj, min, dom, sus, dim, hdim, aug; "open" for a no-3rd reading read without a key
//   (A1: it gets no number and no scale); "other" for a template fallback whose suffix does not parse.
// - A key (opts.key) is the shown key, passed when the tracker's key is sure, fair, locked or the jam key. Pass null for
//   an unsure key: the no-3rd rule (A1) then reads the family as open and names are spelled by opts.keyBias alone.
// - "(no3)" stays in Reading.suffix and Reading.name (the grammar's identity, as the offline engine writes it). The big
//   label and the number never draw it (D12): detect() strips it from info.name and info.suffix and sets info.no3.
// - "11" has its 3rd (Bb11 = Bb D F Ab C Eb; 7(11) without the 9). A no-3rd shape with an 11 is a sus4 chord (9sus4,
//   7sus4) and is never named 11 (D6, A4).
// - Costs are summed in one fixed order (read() below), so equal inputs give bit-identical costs, margins and bands.
// - read() cleans its inputs: a note weight that is missing or not a number counts as 1 (others clamp to 0..1), and a
//   bassMidi whose pitch class is not among the notes joins them at full weight, so a name's bass always sounds.
// - Duplicates go before ranking: a slash reading over its 6th, b7 or 7th when a full reading on that root exists over the
//   same bass (A2), and an augmented triad with a tension when the same notes read as a 7#5 chord on its 3rd or #5.
// - Additive read() options: keyBias (spelling with no key), reach (readings within this much of the top, default 1.5).
import * as Nashville from "./nashville.js";

export const READER_API = "arsenal.piano.chordread/v1";

const mod = (a, n) => ((a % n) + n) % n;
const LETTERS = ["C", "D", "E", "F", "G", "A", "B"];
const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
const ODD = new Set(["E#", "B#", "Cb", "Fb"]);
const accText = (acc) => (acc > 0 ? "#".repeat(acc) : "b".repeat(-acc));
const spName = (sp) => LETTERS[sp.letter] + accText(sp.acc);
const spPc = (sp) => mod(LETTER_PC[sp.letter] + sp.acc, 12);

// ---------------------------------------------------------------------------------------------- the grammar --
// Bases (design-engine 3.1): tones in semitones above the root, cost, family, which tones may be missing, the tensions
// each allows. no3 is the cost of leaving out the 3rd (only these three bases may).
const DOM_T = [1, 2, 3, 5, 6, 8, 9];
const B = (id, tones, cost, family, o = {}) => ({ id, tones, cost, family, omit5: !!o.omit5, no3: o.no3 ?? null,
  rootless: !!o.rootless, tens: o.tens || [] });
const BASES = [
  B("", [0, 4, 7], 0.0, "maj", { no3: 1.4, tens: [2, 5, 6] }),
  B("m", [0, 3, 7], 0.1, "min", { tens: [2, 5, 8] }),
  B("dim", [0, 3, 6], 1.0, "dim"),
  B("aug", [0, 4, 8], 1.2, "aug", { tens: [2, 6] }),
  B("sus4", [0, 5, 7], 1.5, "sus", { tens: [2] }),
  B("sus2", [0, 2, 7], 1.6, "sus", { tens: [6, 9] }),
  B("7", [0, 4, 7, 10], 0.9, "dom", { omit5: true, no3: 1.1, rootless: true, tens: DOM_T }),
  B("maj7", [0, 4, 7, 11], 0.9, "maj", { omit5: true, no3: 0.8, rootless: true, tens: [2, 5, 6, 9] }),
  B("m7", [0, 3, 7, 10], 0.9, "min", { omit5: true, rootless: true, tens: [2, 5, 8, 9] }),
  B("m7b5", [0, 3, 6, 10], 1.3, "hdim", { rootless: true, tens: [2, 5, 8] }),
  B("dim7", [0, 3, 6, 9], 1.4, "dim", { tens: [2, 5, 8, 11] }),
  B("6", [0, 4, 7, 9], 1.2, "maj", { omit5: true, tens: [2, 6] }),
  B("m6", [0, 3, 7, 9], 1.4, "min", { omit5: true, tens: [2, 5] }),
  B("m(maj7)", [0, 3, 7, 11], 1.7, "min", { omit5: true, tens: [2, 5, 9] }),
  B("7sus4", [0, 5, 7, 10], 1.3, "sus", { omit5: true, tens: [1, 2, 9] }),
  B("7#5", [0, 4, 8, 10], 1.9, "dom", { tens: [1, 2, 3, 6] }),
  B("maj7#5", [0, 4, 8, 11], 2.1, "aug", { tens: [2, 6] }),
  B("7b5", [0, 4, 6, 10], 2.1, "dom", { tens: [1, 3] }),
];
const BASE_BY_ID = new Map(BASES.map((b) => [b.id, b]));
// A1: a no-3rd shape whose key gives its root a minor 3rd is read in the minor family. The shape keeps its own cost.
const MINOR_OF = { "": "m", "7": "m7", maj7: "m(maj7)" };
const TN = { 1: "b9", 2: "9", 3: "#9", 5: "11", 6: "#11", 8: "b13", 9: "13", 11: "maj7" };
const ALTERED = new Set([1, 3, 6, 8]);
const ORDER = [1, 2, 3, 5, 6, 8, 9, 11];

// Cost terms (design-engine 4.2) the loss tuning round (A5) moved, each checked in both directions on the real windows of
// S1-S6 (scratch theory-nextgen/tn1/sweep.mjs): gains held at every step, and the fixtures stayed whole. Every other term
// is written where it applies.
export const COSTS = Object.freeze({
  slash: 1.6,               // the chord above a bass that sounds only as the lowest note
  b13MinorSeventh: 1.2,     // b13 over a minor 7th (1.4 and 1.5 each cost a gain: kept)
  b13MinorTriad: 1.6,       // b13 over a minor triad (from 1.4: one loss fixed, no gain lost)
  minorAddOverThird: 0.8,   // a minor triad with added tones over its own 3rd (Ebm(add11)/Gb against Gb6/9; the two seed
                            // slots Gm(add9,11)/Bb and Em(add9,11)/G read Bbmaj13 and Gmaj13)
  minorAddOverFifth: 1.0,   // the same over its 5th (Gm(add9,11)/D against Bbmaj13/D)
  sixNineInversion: -0.3,   // a 6/9 chord over its 3rd or 5th (Ab6/9/Eb against Fm7(11)/Eb, the same notes): 13 losses fixed
});
// Not a tuned cost: the gap a minor name over its own 3rd keeps behind the bass-rooted 6/9 of the same notes when the 5th
// is left out (C E A D: Am(add11)/C behind C6/9). It is the gap the 5th-present twin already has (C E G A D: Am7(11)/C
// 0.25 behind C6/9), so both voicings read in the same band with the same HUD runner-up (tn1-rulings.md must-fix 1).
const SAME_NOTES_STEP = 0.25;

// The lead-sheet name of a base plus tensions (design-engine 3.2).
function suffixOf(base, ext, flags = {}) {
  const has = (x) => ext.has(x), rest = new Set(ext), take = (...xs) => xs.forEach((x) => rest.delete(x));
  let s;
  switch (base.id) {
    case "7":
      if (has(9)) { s = "13"; take(9, 2); } else if (has(5) && has(2)) { s = "11"; take(5, 2); } else if (has(2)) { s = "9"; take(2); } else s = "7";
      break;
    case "maj7": if (has(9)) { s = "maj13"; take(9, 2); } else if (has(2)) { s = "maj9"; take(2); } else s = "maj7"; break;
    case "m7": if (has(9)) { s = "m13"; take(9, 2); } else if (has(5) && has(2)) { s = "m11"; take(5, 2); } else if (has(2)) { s = "m9"; take(2); } else s = "m7"; break;
    case "7sus4": if (has(9)) { s = "13sus4"; take(9, 2); } else if (has(2)) { s = "9sus4"; take(2); } else s = "7sus4"; break;
    case "6": if (has(2)) { s = "6/9"; take(2); } else s = "6"; break;
    case "m6": if (has(2)) { s = "m6/9"; take(2); } else s = "m6"; break;
    case "m7b5": if (has(2)) { s = "m9b5"; take(2); } else s = "m7b5"; break;
    case "m(maj7)": if (has(2)) { s = "m(maj9)"; take(2); } else s = "m(maj7)"; break;
    case "": if (has(2) && !has(5) && !has(6)) { s = "add9"; take(2); } else s = ""; break;
    case "m": if (has(2) && !has(5) && !has(8)) { s = "m(add9)"; take(2); } else s = "m"; break;
    default: s = base.id;
  }
  const left = ORDER.filter((x) => rest.has(x));
  let out = s;
  if (left.length) {
    const seventh = /7|9|11|13/.test(s) && !/6\/9/.test(s);
    const alt = left.filter((x) => ALTERED.has(x)).map((x) => TN[x]).join("");
    const nat = left.filter((x) => !ALTERED.has(x)).map((x) => TN[x]);
    if (seventh && base.id !== "dim7") out = s + alt + (nat.length ? `(${nat.join(",")})` : "");
    else if (s === "") out = "add" + TN[left[0]] + (left.length > 1 ? `(${left.slice(1).map((x) => TN[x]).join(",")})` : "");
    else if (/6\/9/.test(s)) out = s + alt + (nat.length ? `(${nat.join(",")})` : "");
    else if (s === "m") out = `m(add${left.map((x) => TN[x]).join(",")})`;
    else out = s + `(${left.map((x) => TN[x]).join(",")})`;
  }
  if (flags.no3) out += "(no3)";
  return out;
}

// Letter steps above the root for a tone of a grammar reading.
function letterSteps(tones, iv) {
  if (iv === 3) return tones.includes(4) ? 1 : 2;
  if (iv === 6) return tones.includes(7) || (tones.includes(4) && !tones.includes(3)) ? 3 : 4;
  if (iv === 8) return tones.includes(7) || (tones.includes(4) && tones.includes(10)) ? 5 : 4;
  return [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6][iv];
}

// ------------------------------------------------------------------------------------------------ parseSuffix --
// A suffix string, grammar or template, read into its tones (semitones: letter steps, the root included), family (the
// triad family nashville.js FAMILY holds: maj, min, dim, aug, sus, power, other), dominant (a dominant seventh: nashville.js
// DOMINANT) and tensions (tones beyond the base chord). Additive: base (the base id), quality (the reader's family),
// no3, known (false when part of the suffix did not parse). "(no3)" drops the 3rd from tones; the family stays the
// written one (Cm7(no3) is min, as its number 6m7 reads).
const HEADS = [
  [/^m\(maj9\)/, "m(maj7)", [2]], [/^m\(maj7\)/, "m(maj7)", []],
  [/^maj13/, "maj7", [2, 9]], [/^maj9/, "maj7", [2]], [/^maj7#5/, "maj7#5", []], [/^maj7/, "maj7", []],
  [/^m13/, "m7", [2, 9]], [/^m11/, "m7", [2, 5]], [/^m9b5/, "m7b5", [2]], [/^m9/, "m7", [2]], [/^m7b5/, "m7b5", []],
  [/^m7/, "m7", []], [/^m6\/9/, "m6", [2]], [/^m6/, "m6", []], [/^min(?![a-z])/, "m", []], [/^m(?![a-z])/, "m", []],
  [/^dim7/, "dim7", []], [/^dim/, "dim", []], [/^aug/, "aug", []], [/^\+/, "aug", []],
  [/^13sus4?/, "7sus4", [2, 9]], [/^11sus4?/, "7sus4", [2]], [/^9sus4?/, "7sus4", [2]], [/^7sus4?/, "7sus4", []],
  [/^sus4/, "sus4", []], [/^sus2/, "sus2", []], [/^sus(?![0-9])/, "sus4", []],
  [/^13/, "7", [2, 9]], [/^11/, "7", [2, 5]], [/^9/, "7", [2]], [/^7#5/, "7#5", []], [/^7b5/, "7b5", []], [/^7/, "7", []],
  [/^6\/9/, "6", [2]], [/^6/, "6", []], [/^5(?![0-9])/, "5", []], [/^maj(?![0-9])/, "", []],
];
const TENSION_SEMIS = { b9: 1, "9": 2, "#9": 3, b11: 4, "11": 5, "#11": 6, b5: 6, "#5": 8, b13: 8, "13": 9, b6: 8, "6": 9, maj7: 11 };
const FAMILY_OF = { "": "maj", m: "min", dim: "dim", aug: "aug", sus4: "sus", sus2: "sus", "5": "power", "7": "maj", maj7: "maj",
  m7: "min", m7b5: "dim", dim7: "dim", "6": "maj", m6: "min", "m(maj7)": "min", "7sus4": "sus", "7#5": "aug", "maj7#5": "aug", "7b5": "other" };
const DOMINANT_BASES = new Set(["7", "7sus4", "7#5", "7b5"]);

export function parseSuffix(suffix) {
  let s = String(suffix == null ? "" : suffix).replace(/♭/g, "b").replace(/♯/g, "#").trim();
  const no3 = s.includes("(no3)");
  s = s.replace(/\(no3\)/g, "");
  let base = "", extra = [], known = true;
  for (const [re, id, add] of HEADS) {
    const m = re.exec(s);
    if (m) { base = id; extra = add.slice(); s = s.slice(m[0].length); break; }
  }
  const tens = new Set(extra);
  while (s.length) {
    const alt = /^(b9|#9|#11|b13|b5|#5)/.exec(s);
    if (alt) { tens.add(TENSION_SEMIS[alt[1]]); s = s.slice(alt[0].length); continue; }
    const add = /^add(b9|#9|9|#11|11|b13|13)/.exec(s);
    if (add) { tens.add(TENSION_SEMIS[add[1]]); s = s.slice(add[0].length); continue; }
    const group = /^\(([^)]*)\)/.exec(s);
    if (group) {
      for (const item of group[1].split(",").map((x) => x.trim().replace(/^add/, ""))) {
        if (item in TENSION_SEMIS) tens.add(TENSION_SEMIS[item]); else known = false;
      }
      s = s.slice(group[0].length);
      continue;
    }
    known = false;
    break;
  }
  const baseTones = base === "5" ? [0, 7] : (BASE_BY_ID.get(base) || BASE_BY_ID.get("")).tones;
  const all = [...new Set([...baseTones, ...tens])].filter((x) => !(no3 && (x === 3 || x === 4) && baseTones.includes(x)));
  all.sort((a, b) => a - b);
  const tones = {};
  for (const iv of all) {
    if (base === "dim7" && iv === 9) tones[iv] = 6;          // dim7's 7th, a diminished 7th (nashville.js TONE_STEPS)
    else if (iv === 3) tones[iv] = baseTones.includes(3) ? 2 : 1;
    else if (iv === 6) tones[iv] = baseTones.includes(6) ? 4 : 3;
    else if (iv === 8) tones[iv] = baseTones.includes(8) ? 4 : 5;
    else tones[iv] = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6][iv];
  }
  const quality = base === "5" ? "other" : BASE_BY_ID.get(base).family;
  return { tones, family: FAMILY_OF[base], dominant: DOMINANT_BASES.has(base), tensions: all.filter((x) => !baseTones.includes(x)),
           base, quality, no3, known };
}

// ------------------------------------------------------------------------------------------------ voicing tags --
// Words for the "why", never the name (design-engine 4.5, A3). Text comes from the lexicon's tag.* entries.
const TRIADS = [[0, 4, 7, ""], [0, 3, 7, "m"]];
const TAG_TEXT = {
  cluster: ["tag.cluster", "notes a step apart"], quartal: ["tag.quartal", "stacked 4ths"],
  polychord: ["tag.polychord", "two separate triads stacked"], "upper structure": ["tag.upper_structure", "a triad on top made of the colour tones"],
};
const tagOf = (tag, more = {}) => ({ tag, text: TAG_TEXT[tag][1], lexId: TAG_TEXT[tag][0], ...more });

// A3: 3 adjacent notes a semitone apart twice in a row, or 4 adjacent notes each a step or less apart with at least one
// semitone (scratch spec/merge_lab.mjs clusterTight: 4 of Daniel's 24 against 9 for the prototype's rule).
function clusterRun(ms) {
  const iv = ms.slice(1).map((m, i) => m - ms[i]);
  for (let i = 0; i < iv.length; i++) {
    const w3 = iv.slice(i, i + 2), w4 = iv.slice(i, i + 3);
    if (w3.length === 2 && w3.every((x) => x === 1)) return true;
    if (w4.length === 3 && w4.every((x) => x <= 2) && w4.some((x) => x === 1)) return true;
  }
  return false;
}
// A3: 4 or more notes within 5 semitones with an adjacent semitone are a cluster in any band (C D E F, not Dm9/C).
const isCluster = (ms) => ms.length >= 4 && ms[ms.length - 1] - ms[0] <= 5 && ms.slice(1).some((m, i) => m - ms[i] === 1);
// The notes with a given bass lowest, for the templates (which take the lowest note as the bass): every note under it
// moves up by octaves. Pitch classes are unchanged; with no bass given, or the bass already lowest, nothing moves.
const overBass = (midis, bassMidi) => (Number.isFinite(bassMidi)
  ? midis.map((m) => { let x = m; while (x < bassMidi) x += 12; return x; }) : midis.slice());

function voicingTags(ms) {
  const tags = [];
  const iv = ms.slice(1).map((m, i) => m - ms[i]);
  let run = 0, most = 0;
  for (const x of iv) { run = x === 5 || x === 6 ? run + (x === 5 ? 1 : 0.5) : 0; most = Math.max(most, run); }
  if (ms.length >= 4 && most >= 2.5 && iv.filter((x) => x === 5).length >= Math.max(2, iv.length - 1)) tags.push(tagOf("quartal"));
  if (clusterRun(ms)) tags.push(tagOf("cluster"));
  if (ms.length >= 6) {  // polychord: split at the widest gap; a triad below and a different triad above
    let gi = -1, gap = 0;
    iv.forEach((x, i) => { if (x > gap) { gap = x; gi = i; } });
    const lo = [...new Set(ms.slice(0, gi + 1).map((m) => mod(m, 12)))], hi = [...new Set(ms.slice(gi + 1).map((m) => mod(m, 12)))];
    const triadOf = (pcs) => {
      if (pcs.length !== 3) return null;
      for (const r of pcs) for (const [a, b, c, q] of TRIADS) {
        const set = new Set(pcs.map((p) => mod(p - r, 12)));
        if (set.has(a) && set.has(b) && set.has(c)) return { root: r, q };
      }
      return null;
    };
    const L = triadOf(lo), H = triadOf(hi);
    if (gap >= 3 && L && H && !hi.some((p) => lo.includes(p))) tags.push(tagOf("polychord", { lower: L, upper: H }));
  }
  return tags;
}

// A major or minor triad made of 2 or more of the chord's tensions, avoiding its root, 3rd and 7th.
function upperStructure(c, pcs) {
  if (c.family !== "dom" && c.family !== "maj") return null;
  const cand = [...c.ext].map((e) => mod(c.root + e, 12)).concat([mod(c.root + 7, 12)]);
  for (const x of cand) for (const [, b, d, q] of TRIADS) {
    const tri = [x, mod(x + b, 12), mod(x + d, 12)];
    if (x === c.root || !tri.every((p) => pcs.has(p))) continue;
    const rel = tri.map((p) => mod(p - c.root, 12));
    if (rel.some((v) => v === 0 || v === 3 || v === 4 || v === 10 || v === 11)) continue;
    if (rel.filter((v) => c.ext.has(v)).length < 2) continue;
    return { root: x, q };
  }
  return null;
}

// ------------------------------------------------------------------------------------------------- the reader --
export function createReader({ Theory, NV = Nashville, costs = null } = {}) {
  if (!Theory || typeof Theory.detect !== "function") throw new Error("createReader needs piano.js's Theory");
  const C = { ...COSTS, ...(costs || {}) };  // costs (additive): a lab overrides COSTS terms to tune them (A5)
  const detectTemplates = Theory.detectTemplates || Theory.detect;  // captured now: installReader swaps Theory.detect later
  const keyOf = (key) => (!key ? null : NV.parseKey(typeof key === "string" ? key : key.name));
  const keyScaleOf = (k) => new Set((k.mode === "major" ? [0, 2, 4, 5, 7, 9, 11] : [0, 2, 3, 5, 7, 8, 10, 11]).map((x) => mod(x + k.tonic, 12)));

  // A7: a root spelled in the key as the page's spellForKey spells it (piano.js): the key's spelling when it lies on the
  // key's scale (E# in F# major, Cb in Gb major) or needs one accidental at most and is not E#, B#, Cb or Fb.
  function spellRoot(pc, bias, keyName, suffix) {
    let rsp = Theory.spellAlone(pc, bias);
    if (keyName) {
      const s = NV.spellInKey(rsp, keyName, { suffix });
      if (s && (s.inScale || (Math.abs(s.acc) <= 1 && !ODD.has(spName(s))))) rsp = { letter: s.letter, acc: s.acc };
    }
    return rsp;
  }
  // A chord tone or bass spelled from the root by letter steps, as spellForKey moves it (C#/E#, Abm/Cb). A spelling that
  // would need two accidentals falls back to the note's own spelling in the key (with no key, by the bias).
  function spellFromRoot(rsp, pc, steps, bias, keyName = null) {
    const sp = Theory.spellInterval(rsp, mod(pc - spPc(rsp), 12), steps);
    return Math.abs(sp.acc) > 1 ? spellRoot(pc, bias, keyName, null) : sp;
  }
  const noteName = (pc, bias, keyName) => spName(spellRoot(pc, bias, keyName, null));

  // A written chord name respelled in a key (alsoOf's template name, the template fallback): the root by spellInKey, the
  // bass keeping its letter distance from the root.
  function respellName(name, keyName, bias = 0) {
    const c = NV.parseChord(name);
    if (!c || c.kind !== "chord") return name;
    const rootPc = spPc(c.root);
    const rsp = keyName ? spellRoot(rootPc, bias, keyName, c.suffix) : c.root;
    let out = spName(rsp) + c.suffix;
    if (c.bass) out += "/" + spName(spellFromRoot(rsp, spPc(c.bass), mod(c.bass.letter - c.root.letter, 7), bias, keyName));
    return out;
  }

  const identOfName = (name) => {
    const c = name == null ? null : NV.parseChord(String(name));
    if (!c || c.kind !== "chord") return null;
    return { root: spPc(c.root), suffix: c.suffix, bass: c.bass ? spPc(c.bass) : null };
  };
  const plainId = (x) => `${x.root}|${String(x.suffix).replace("(no3)", "")}|${x.bass ?? ""}`;

  function read(notesIn, opts = {}) {
    // Inputs are cleaned first (H5 hands in salience and the window's bass). A weight that is missing or not a number
    // counts as 1, and the rest clamp to 0..1. A bass whose pitch class is not among the notes still sounded in the
    // window, so it joins them at full weight: every name is built on a bass that sounds.
    const notes = [];
    for (const n of notesIn || []) {
      const midi = typeof n === "number" ? n : n ? n.midi : NaN;
      if (!Number.isFinite(midi)) continue;
      notes.push({ midi: Math.round(midi), w: typeof n === "number" || !Number.isFinite(n.w) ? 1 : Math.min(1, Math.max(0, n.w)) });
    }
    const bassIn = Number.isFinite(opts.bassMidi) ? Math.round(opts.bassMidi) : null;
    if (bassIn !== null && !notes.some((n) => mod(n.midi, 12) === mod(bassIn, 12))) notes.push({ midi: bassIn, w: 1 });
    notes.sort((a, b) => a.midi - b.midi);
    const key = keyOf(opts.key);
    const keyName = key ? key.name : null;
    const small = { kind: "small", readings: [], band: "none", margin: 0, confidence: 0, tags: [], key: keyName };
    if (!notes.length) return small;
    const sal = new Array(12).fill(0);
    for (const n of notes) sal[mod(n.midi, 12)] = Math.max(sal[mod(n.midi, 12)], n.w);
    const bassMidi = bassIn ?? notes[0].midi;
    const bassPc = mod(bassMidi, 12);
    const pcs = new Set(notes.map((n) => mod(n.midi, 12)));
    if (pcs.size < 3) return small;
    const lowestOther = notes.find((n) => mod(n.midi, 12) !== bassPc);
    const bassOnlyLow = notes.every((n) => mod(n.midi, 12) !== bassPc || n.midi < lowestOther.midi);
    const keyScale = key ? keyScaleOf(key) : null;
    const bias = key ? key.bias : Number(opts.keyBias) || 0;
    const out = [];
    let group = 0;  // one per evaluated note set, so a duplicate is only ever judged against readings of the same notes

    // A1: the key's diatonic 3rd above a root: "min", "maj", or null when the key holds both or neither.
    const keyThird = (root) => {
      const m3 = keyScale.has(mod(root + 3, 12)), M3 = keyScale.has(mod(root + 4, 12));
      return m3 && !M3 ? "min" : M3 && !m3 ? "maj" : null;
    };

    const evalSet = (set, bass, extra, path) => {
      const g = group++;
      for (let root = 0; root < 12; root++) {
        const rel = new Set([...set].map((p) => mod(p - root, 12)));
        for (const shape of BASES) {
          const flags = {};
          let cost = shape.cost + extra.cost, ok = true;
          for (const m of shape.tones) {
            if (rel.has(m)) continue;
            if (m === 7 && shape.omit5) { flags.no5 = true; cost += 0.3; }
            else if (m === 0 && shape.rootless && opts.allowRootless !== false) { flags.rootless = true; cost += 1.3; }
            else if (m === 4 && shape.no3 !== null) { flags.no3 = true; cost += shape.no3; }
            else { ok = false; break; }
          }
          if (!ok) continue;
          const present = shape.tones.filter((t) => rel.has(t)).length;
          if (present < 2 || (present < 3 && set.size < 4)) continue;
          if (flags.no3 && (flags.no5 || flags.rootless || bass !== root)) continue;
          if (flags.rootless && (!rel.has(shape.tones[1]) || !rel.has(shape.tones[3]) || set.size < 4 || bass === undefined)) continue;
          let base = shape, family = shape.family, third = null;
          if (flags.no3) {
            if (rel.has(5)) continue;                                     // A4: an 11 over no 3rd is a sus4 chord (D6)
            third = key ? keyThird(root) : "open";                        // A1: the key decides the quality
            if (third === "min") {
              if (rel.has(3)) continue;                                   // a minor 3rd sounds: that is the full reading
              base = BASE_BY_ID.get(MINOR_OF[shape.id]);
              family = base.family;
            } else if (third === "open") family = "open";
          }
          const ext = new Set([...rel].filter((x) => !base.tones.includes(x)));
          if ([...ext].some((e) => !base.tens.includes(e))) continue;
          if ((ext.has(1) && ext.has(2)) || (ext.has(2) && ext.has(3)) || (ext.has(8) && ext.has(9)) || (ext.has(5) && ext.has(6))) continue;
          if (ext.has(8) && base.family === "min" && flags.no5) continue;  // b13 over a minor chord needs its 5th (else it is #5)
          for (const e of ext) {
            cost += e === 8 && base.family === "min" ? (base.tones.length === 3 ? C.b13MinorTriad : C.b13MinorSeventh)
              : e === 8 && base.family === "hdim" ? 0.7 : ALTERED.has(e) ? 0.45 : 0.35;
          }
          const bassIv = bass !== undefined ? mod(bass - root, 12) : null;
          if (base.family === "dom" && ext.has(5) && !ext.has(2) && bassIv === 10) cost += 0.35;  // a 7(11) over its own 7th
          if (bass !== undefined && bass !== root && ext.size >= 2) cost += 0.25 * (ext.size - 1);  // an extended chord in inversion
          if (base.family === "sus" && bassIv === 10) cost += 0.3;                                  // a sus chord over its own 7th
          if (ext.has(5) && base.tones.includes(4)) cost += base.id === "maj7" ? 0.9 : base.family === "dom" ? (ext.has(2) ? 0.2 : 0.45) : 0.4;
          if ((ext.has(6) || ext.has(8)) && flags.no5 && ext.size === 1) cost += 0.6;
          const alteredOverFourth = bass !== undefined && bassIv === base.tones[3] && [...ext].some((e) => ALTERED.has(e));
          if (alteredOverFourth) cost += 0.3;
          const seventhBass = alteredOverFourth && !["6", "m6"].includes(base.id);  // a 7th in the bass, not a 6th (A1's band cap)
          if (ext.has(11) && base.id === "dim7") cost += 0.3;
          if (C.minorAddOverThird && base.id === "m" && ext.size >= 1 && bassIv === 3) cost += C.minorAddOverThird;
          if (C.minorAddOverFifth && base.id === "m" && ext.size >= 1 && bassIv === 7) cost += C.minorAddOverFifth;
          if (C.sixNineInversion && base.id === "6" && ext.has(2) && (bassIv === 4 || bassIv === 7)) cost += C.sixNineInversion;
          const reasons = [...extra.reasons];
          if (bass !== undefined && bass !== root) {
            if (base.tones.includes(bassIv)) {
              cost += bassIv === 3 || bassIv === 4 ? 0.55 : bassIv === 6 || bassIv === 7 || bassIv === 8 ? 0.6 : 0.7;
              reasons.push(`bass is the ${bassIv === 3 || bassIv === 4 ? "3rd" : bassIv >= 6 && bassIv <= 8 ? "5th" : bassIv === 9 && base.id !== "dim7" ? "6th" : "7th"}`);
            } else { cost += 1.4; reasons.push(`bass is the ${TN[bassIv]} (a colour tone)`); }  // the bass sounds, so it is an allowed tension
          } else if (bass !== undefined) reasons.push("bass is the root");
          if (!flags.rootless && sal[root] < 0.3 && bass !== root) cost += 0.3;
          if (flags.no5) reasons.push("no 5th");
          if (flags.no3) reasons.push(third === "min" || third === "maj" ? `no 3rd: the key gives it a ${third === "min" ? "minor" : "major"} 3rd` : "no 3rd");
          if (flags.rootless) reasons.push("no root: a rootless voicing");
          if (base.id === "7" && ext.has(5)) reasons.push("11 with its 3rd: a dominant 11");
          if (ext.has(6) && base.family === "maj") reasons.push("#11: the Lydian colour");
          if (keyScale && [...set].every((p) => keyScale.has(p))) { cost -= 0.15; reasons.push(`every note in ${keyName}`); }
          if (opts.prev && opts.prev.root === root) { cost -= 0.1; reasons.push("same root as the chord before"); }
          out.push({ root, base, family, ext, flags, bass: bass !== undefined && bass !== root ? bass : null, cost, reasons, path, seventhBass, group: g });
        }
      }
    };

    evalSet(pcs, bassPc, { cost: 0, reasons: [] }, "full");
    if (bassOnlyLow && pcs.size >= 4) {
      const upper = new Set([...pcs].filter((p) => p !== bassPc));
      const before = out.length;
      evalSet(upper, undefined, { cost: C.slash, reasons: ["slash: the bass is outside the chord"] }, "slash");
      for (let i = before; i < out.length; i++) out[i].bass = bassPc;
    }
    for (let pc = 0; pc < 12; pc++) {  // a faint note (salience under 0.35, not the bass) may be a passing tone
      if (!pcs.has(pc) || pc === bassPc || sal[pc] >= 0.35 || pcs.size < 4) continue;
      const set = new Set([...pcs].filter((p) => p !== pc));
      evalSet(set, bassPc, { cost: 0.3 + sal[pc], reasons: [`${noteName(pc, bias, keyName)} treated as passing (faint)`] }, "drop");
    }

    // A2: a slash reading whose bass is the 6th, b7 or 7th above its upper root is the same chord in inversion when a
    // full reading on that root exists over the same bass (Bbadd9(11)/Ab is Bb11/Ab), and it goes. With no full reading
    // it is no inversion and stays (Dmaj7/C, Dm(maj9)/C). The spec would rename it to the inversion, but the grammar has
    // no inversion name for those notes: the inversion's base refuses the same tones.
    // The augmented duplicate, by the same rule: an augmented triad with a tension is a 7#5 chord built on its 3rd or its
    // #5 (G#aug(#11) is E7#5/G#, Caug(9) is E7#5/C). It goes when that 7#5 reading of the same notes exists.
    const fullOn = new Set(out.filter((r) => r.path === "full").map((r) => `${r.root}|${r.bass}`));
    const sevenSharpFive = new Set(out.filter((r) => r.base.id === "7#5").map((r) => `${r.group}|${r.root}`));
    const kept = out.filter((r) => !(r.path === "slash" && [9, 10, 11].includes(mod(r.bass - r.root, 12)) && fullOn.has(`${r.root}|${r.bass}`))
      && !(r.base.id === "aug" && r.ext.size > 0 && [4, 8].some((up) => sevenSharpFive.has(`${r.group}|${mod(r.root + up, 12)}`))));

    // The 6/9 without its 5th (tn1-rulings.md must-fix 1). Root, 3rd, 6th and 9th (C E A D) are also the relative minor
    // over its own 3rd with the 11 added (Am(add11)/C): the same notes, named from the 6th. That minor name ranks
    // SAME_NOTES_STEP behind the 6/9 on the bass whatever the costs say (a key, no key, the chord before), and it stays
    // listed for the HUD. A minor triad over its 3rd is only ever this 6/9's twin: with the 6/9's 5th sounding, the minor
    // name holds a 7th and is a m7(11) (Ebm7(11)/Gb behind Gb6/9), which this rule never touches.
    const sixNoFifth = new Map(kept.filter((r) => r.base.id === "6" && r.flags.no5 && r.bass === null && r.path !== "slash")
      .map((r) => [`${r.group}|${r.root}`, r]));
    for (const r of kept) {
      if (r.base.id !== "m" || !r.ext.size || r.bass === null || r.path === "slash" || mod(r.bass - r.root, 12) !== 3) continue;
      const six = sixNoFifth.get(`${r.group}|${r.bass}`);
      if (six && r.cost < six.cost + SAME_NOTES_STEP) r.cost = six.cost + SAME_NOTES_STEP;
    }
    // The 9 chord with no 3rd (C G Bb D: root and 5th below, b7 and 9 above, the neo-soul and gospel sus-colour hand) is
    // also the minor triad on its 5th over its own 11 (Gm(add11)/C): the same notes, named from the 5th. When the bass
    // pitch sounds again above the lowest note, it is a chord tone, not only a bass, so that minor name ranks
    // SAME_NOTES_STEP behind the no-3rd 9 chord on the bass (C9(no3), or Cm9(no3) where the key gives C a minor 3rd), as the
    // 6/9's relative minor does. A rank rule, not a cost term. When the bass sounds only lowest, the slash name (Gm/C) is
    // the plain name and already ranks ahead of both, so the rule leaves that list, and its band, as the costs give it.
    const nineNoThird = new Map(kept.filter((r) => r.flags.no3 && (r.base.id === "7" || r.base.id === "m7") && r.ext.has(2)
      && r.bass === null && r.path !== "slash").map((r) => [`${r.group}|${r.root}`, r]));
    for (const r of bassOnlyLow ? [] : kept) {
      if (r.base.id !== "m" || r.bass === null || r.path === "slash" || mod(r.bass - r.root, 12) !== 5) continue;
      const nine = nineNoThird.get(`${r.group}|${r.bass}`);
      if (nine && r.cost < nine.cost + SAME_NOTES_STEP) r.cost = nine.cost + SAME_NOTES_STEP;
    }

    const seen = new Map();
    for (const r of kept) {
      r.suffix = suffixOf(r.base, r.ext, r.flags);
      const id = `${r.root}|${r.suffix}|${r.bass ?? ""}`;
      if (!seen.has(id) || seen.get(id).cost > r.cost) seen.set(id, r);
    }
    // Cheapest first; on a tie the reading rooted on the bass, then the order found (a consistent comparator, so every
    // engine sorts alike).
    const isBassRoot = (r) => r.root === bassPc;
    const cands = [...seen.values()].map((r, i) => ({ r, i }))
      .sort((a, b) => a.r.cost - b.r.cost || (isBassRoot(a.r) === isBassRoot(b.r) ? a.i - b.i : isBassRoot(a.r) ? -1 : 1)).map((x) => x.r);
    if (!cands.length) {  // nothing in the grammar: the page's own template reading stays (Fm(add9)/Ab without its 5th)
      // Over the window's bass (tn1-rulings.md): the templates take the lowest note as the bass, so every note under
      // opts.bassMidi moves up by octaves first, and a template name on any other bass is no name at all.
      const info = detectTemplates(overBass(notes.map((n) => n.midi), bassMidi), bias);
      const named = info && info.kind === "chord" ? identOfName(info.name) : null;
      const id = named && (named.bass ?? named.root) === bassPc ? named : null;
      if (id) {
        const ps = parseSuffix(id.suffix);
        cands.push({ root: id.root, suffix: id.suffix, bass: id.bass, cost: (info.cost ?? 3) + 0.5, reasons: ["the page's own name (fallback)"],
          base: { id: ps.base, tones: Object.keys(ps.tones).map(Number) }, family: ps.known ? ps.quality : "other", ext: new Set(ps.tensions),
          flags: {}, path: "template", fixedName: respellName(info.name, keyName, bias) });
      }
    }
    const ms = [...new Set(notes.map((n) => n.midi))];
    const tags = voicingTags(ms);
    const top = cands[0];
    const Z = cands.slice(0, 6).reduce((s, r) => s + Math.exp(-(r.cost - top.cost) / 0.3), 0);
    if (top && top.path !== "template") {
      const us = upperStructure(top, pcs);
      if (us) tags.push(tagOf("upper structure", { triad: us }));
    }
    const margin = cands.length > 1 ? cands[1].cost - cands[0].cost : 9;
    let band = !top ? "none" : margin >= 0.5 && top.cost <= 2.5 ? "clear" : margin >= 0.2 && top.cost <= 3.2 ? "leaning" : "ambiguous";
    // A1: a reading without its 3rd or root, or over its own 7th under altered tensions, is never clear.
    if (band === "clear" && (top.flags.no3 || top.flags.rootless || top.seventhBass)) band = "leaning";
    // A6, honest calibration: three pitch classes stacked in 4ths up from the bass (D G C) name no chord for sure. They
    // are D7sus4 without its 5th, Gsus4 over its 5th or Csus2 over its 9 (scratch tn1r/variants3.mjs: 3 real windows).
    if (band === "clear" && pcs.size === 3 && pcs.has(mod(bassPc + 5, 12)) && pcs.has(mod(bassPc + 10, 12))) band = "leaning";
    // Same-notes twins, honest calibration (spec 2.6's hand rule: leaning where the same notes carry a second name as plain
    // on another root or bass). Neither is clear while the other is a reading within 1.5 (alsoOf's reach), whichever tops:
    // - the Lydian 4 and the gospel 5 over 4 (design-engine 9.9: what follows decides): a root-position major chord with
    //   its #11 and no maj7 (Ab6/9#11), and the dominant 11 on its 2nd over it, with that dominant's 5th and 9 sounding
    //   (Bb11/Ab). Without the 5 chord's 5th (Ab Bb D C Eb, no F) Abadd9(#11) is the one plain name, and stays clear.
    // - a maj13 with no 9 (Dbmaj13: Db F Ab C Bb) and its relative minor over its 3rd, whose 9 is the maj7 (Bbm9/Db; with
    //   the #11 sounding, Gbmaj13#11 with no Ab and Ebm13/Gb). design-engine 5 on Abmaj13 and Fm9/Ab: "Both are right."
    // Measured on S1-S6 (scratch theory-nextgen/tn1t/diff_r4.mjs): 8 real windows leave clear, clear-band agreement rises
    // (0.960 to 0.966, multi-reading 0.952 to 0.959), and every lane receipt holds.
    const lydianFour = (x) => x.path === "full" && x.bass === null && x.root === bassPc && x.family === "maj" && !x.flags.no3
      && !x.flags.rootless && x.ext.has(6) && !x.base.tones.includes(11);
    const gospelFive = (x) => x.path === "full" && x.base.id === "7" && x.root === mod(bassPc + 2, 12) && x.bass === bassPc && !x.flags.no3
      && !x.flags.no5 && !x.flags.rootless && x.ext.has(2) && x.ext.has(5);
    const majThirteenNoNine = (x) => x.path === "full" && x.bass === null && x.root === bassPc && x.base.id === "maj7" && !x.flags.no3
      && !x.flags.rootless && x.ext.has(9) && !x.ext.has(2);
    const relativeMinorNine = (x) => x.path === "full" && x.base.id === "m7" && x.root === mod(bassPc + 9, 12) && x.bass === bassPc
      && !x.flags.rootless && x.ext.has(2);
    const TWINS = [[lydianFour, gospelFive], [majThirteenNoNine, relativeMinorNine]];
    if (band === "clear" && TWINS.some(([a, b]) => cands.some((x) => x !== top && x.cost - top.cost <= 1.5 && ((a(top) && b(x)) || (b(top) && a(x)))))) {
      band = "leaning";
    }
    // A3's cluster kind makes no chord-name claim, so no band sits beside it (tn1-rulings.md): the HUD never shows clear
    // beside letters. The readings stay listed.
    const kind = !top || isCluster(ms) ? "cluster" : "chord";
    if (kind === "cluster") band = "none";
    const fit = top ? Math.exp(-Math.max(0, top.cost - 1.0) / 1.5) : 0;  // an only reading that takes a lot of naming is still weak
    // The readings any consumer can use: every one within 1.5 of the top (alsoOf's reach), and at least three (the HUD).
    // opts.reach (additive) widens the list for a lab or a test; p sums to 1 over the readings returned.
    const reach = typeof opts.reach === "number" && opts.reach >= 0 ? opts.reach : 1.5;
    const shown = cands.filter((r, i) => i < 3 || r.cost - top.cost <= reach);
    const Zshown = shown.reduce((s, r) => s + Math.exp(-(r.cost - top.cost) / 0.3), 0);
    const readings = shown.map((r) => ({
      root: r.root, suffix: r.suffix, bass: r.bass, name: r.fixedName || nameOf(r, bias, keyName),
      cost: r.cost, p: Math.exp(-(r.cost - top.cost) / 0.3) / Zshown, reasons: r.reasons,
      base: { id: r.base.id, family: r.family }, tensions: [...r.ext].sort((a, b) => a - b),
      omit: { no3: !!r.flags.no3, no5: !!r.flags.no5, rootless: !!r.flags.rootless }, path: r.path,
    }));
    return { kind, readings, band,
             margin: Math.min(margin, 9), confidence: top ? Math.max(0, Math.min(1, (1 / Z) * fit)) : 0, tags, key: keyName };

    function nameOf(r, b, kn) {
      const rsp = spellRoot(r.root, b, kn, r.base.id);
      let name = spName(rsp) + r.suffix;
      if (r.bass != null) name += "/" + spName(spellFromRoot(rsp, r.bass, letterSteps(r.base.tones, mod(r.bass - r.root, 12)), b, kn));
      return name;
    }
  }

  // D5: the canvas ALSO, the "was" rule. The template name (today's page name) when it differs from the top reading in
  // root or bass and is itself a reading within 1.5, held 1 s.
  function alsoOf(result, templateInfo, heldMs) {
    if (!(heldMs >= 1000) || !templateInfo || templateInfo.kind !== "chord" || !result || result.kind !== "chord") return null;
    const top = result.readings[0], t = identOfName(templateInfo.name);
    if (!top || !t || plainId(t) === plainId(top)) return null;
    if (t.root === top.root && t.bass === top.bass) return null;  // a suffix difference only: not a second chord
    const r = result.readings.find((x) => plainId(x) === plainId(t));
    return r && r.cost - top.cost <= 1.5 ? { name: respellName(templateInfo.name, result.key || null), kind: "was" } : null;
  }

  // D5, HUD only: the close runner-up of a leaning or ambiguous reading, held 1 s. Slash duplicates never reach the
  // readings (A2), so a slash reading over its 6th, b7 or 7th that is listed is a name of its own and may be the close one.
  function closeOf(result, heldMs) {
    if (!(heldMs >= 1000) || !result || result.kind !== "chord" || result.band === "clear" || !result.readings.length) return null;
    const top = result.readings[0];
    const plausible = (x) => {
      if (x.omit.no3 || x.omit.rootless || x.path === "drop") return false;
      if (x.path === "slash" && x.bass != null && [1, 2, 6, 8].includes(mod(x.bass - x.root, 12))) return false;  // a colour-tone bass
      return x.root !== top.root || x.bass !== top.bass;
    };
    return result.readings.slice(1, 4).find((x) => plausible(x) && x.cost - top.cost <= 0.6) || null;
  }

  // Theory.detect's signature and info shape, named by the reader: a note, an interval or a power chord keeps today's
  // info; 3 or more pitch classes take the reading. opts (additive): { key, prev, bassMidi } for the reader.
  // The info's root and bass always sound (tn1-rulings.md must-fix 2), because piano.js's spellForKey, the label, the
  // number, the HUD and the practice log's chord event look them up among info.notes:
  // - a bassMidi whose pitch class is not among the notes joins the notes detect spells, as read() takes it;
  // - a top reading whose root does not sound (rootless) is named by the first listed reading whose root sounds, else by
  //   today's template info over the same bass. The rootless top stays first in info.readings, and the additive
  //   info.rootless = { root, name, suffix, bass } names it (null when the top's root sounds).
  function detect(midiNotes, keyBias = 0, opts = {}) {
    const notes = [...new Set(midiNotes || [])].sort((a, b) => a - b);
    const bassIn = Number.isFinite(opts.bassMidi) ? Math.round(opts.bassMidi) : null;
    if (bassIn !== null && !notes.some((n) => mod(n, 12) === mod(bassIn, 12))) { notes.push(bassIn); notes.sort((a, b) => a - b); }
    if (new Set(notes.map((n) => mod(n, 12))).size < 3) return detectTemplates(bassIn === null ? midiNotes : overBass(notes, bassIn), keyBias);
    const res = read(notes, { key: opts.key ?? null, prev: opts.prev ?? null, bassMidi: bassIn ?? undefined, keyBias });
    const key = keyOf(opts.key);
    const bias = key ? key.bias : keyBias;
    const keyName = key ? key.name : null;
    const pcs = [];
    for (const n of notes) if (!pcs.includes(mod(n, 12))) pcs.push(mod(n, 12));
    const extras = { readings: res.readings, band: res.band, tags: res.tags };
    const top = res.kind === "chord" ? res.readings[0] : null;
    const sounds = (pc) => pc == null || pcs.includes(pc);
    const spOf = (sp) => (sp ? { letter: sp.letter, acc: sp.acc } : null);
    let rootless = null;
    if (top && !sounds(top.root)) {
      const t = NV.parseChord(top.name);
      rootless = { root: spOf(t.root), name: top.name, suffix: top.suffix, bass: spOf(t.bass) };
    }
    const spelled = (map) => notes.map((midi) => {
      const sp = map[mod(midi, 12)];
      return { midi, letter: sp.letter, acc: sp.acc, name: spName(sp), octave: Theory.octaveOf(midi, sp), diatonic: Theory.diatonicOf(midi, sp) };
    });
    if (!top) {
      const map = {};
      for (const pc of pcs) map[pc] = spellRoot(pc, bias, keyName, null);
      return { kind: "cluster", root: null, suffix: "", bass: null, name: pcs.map((pc) => spName(map[pc])).join(" "), sub: "no chord name",
               pcNames: pcs.map((pc) => spName(map[pc])), notes: spelled(map), ...extras, no3: false, rootless: null };
    }
    const named = res.readings.find((r) => sounds(r.root) && sounds(r.bass));
    if (!named) {  // every listed reading is rootless: today's template info names the notes (its root and bass sound)
      const info = detectTemplates(bassIn === null ? notes : overBass(notes, bassIn), bias);
      return { ...info, ...extras, no3: false, rootless };
    }
    const c = NV.parseChord(named.name);
    const suffix = named.suffix.replace("(no3)", "");
    const tones = parseSuffix(named.suffix).tones;
    const map = {};
    for (const pc of pcs) {
      const iv = mod(pc - named.root, 12);
      map[pc] = iv in tones ? spellFromRoot(c.root, pc, tones[iv], bias, keyName) : spellRoot(pc, bias, keyName, null);
    }
    map[named.root] = c.root;
    if (c.bass) map[named.bass] = c.bass;
    const name = spName(c.root) + suffix + (c.bass ? "/" + spName(c.bass) : "");
    return { kind: "chord", root: c.root, suffix, bass: c.bass || null, name, sub: "", pcNames: pcs.map((pc) => spName(map[pc])),
             notes: spelled(map), cost: named.cost, ...extras, no3: named.omit.no3, rootless };
  }

  return { read, alsoOf, closeOf, detect, detectTemplates };
}

// The page's install (TN7) and the node loader's (TN6): Theory.detectTemplates keeps today's detect, Theory.read and
// Theory.detect come from the reader. Returns the reader. Installing twice keeps the first templates.
export function installReader(Theory, NV = Nashville) {
  Theory.detectTemplates = Theory.detectTemplates || Theory.detect;
  const reader = createReader({ Theory, NV });
  Theory.read = reader.read;
  Theory.detect = reader.detect;
  return reader;
}
