// Cadence live: arsenal/web/piano/cadence-live.js (pure ES module: no three.js, no DOM). Tests: tests/piano_cadence_live.test.mjs.
//
// Daniel's ask, verbatim: "What would it take to have more musical concepts be apparent, parseable, knowable and
// understandable at once? Certain chord progressions carry feeling, the cadence of notes, the tensions, the warmth, what
// storytelling is happening, what is the progressions of moods and feels. You can tell a whole story with a melody"
//
// This module names the cadence (if any) that arrives on a window, the moment it arrives, so the piano can show the
// story while it is being played rather than in the report afterwards.
//
// Usage:
//   import { judge, KINDS, CADENCE } from "./cadence-live.js";
//   const out = { kind: null, code: -1, first: -1, last: -1, startMs: 0, endMs: 0, dominant: false };  // allocate once
//   // ws: windows shaped like the oracle's (root_pc, mask, bass_pc, low_bass, third, texture, area, start_ms, end_ms)
//   // areas: indexed by area id, each {tonic, mode}; a window's area is an id, null/undefined for none
//   if (judge(ws, areas, n, out)) show(out.kind, ws[out.first], ws[out.last]);
//
// It is a rule-for-rule twin of arsenal/practice.py _cadence (with _passing_moment, _bass_dominant, _chordal and _rel):
// the same branch order, the same guards, the same kind strings. It is proven window-fed against the private oracle
// (state/arsenal/story/oracle, written from practice.analyze's own rows) by tests/piano_cadence_live.test.mjs, and on
// synthetic fixtures (tests/fixtures/cadence_cases.json) that tests/test_cadence_fixtures_python.py runs through
// practice._cadence itself. judge() allocates nothing: pitch-class sets are 12-bit masks, the kinds are frozen strings.

export const CADENCE_LIVE_API = "arsenal.piano.cadence-live/v1";

// practice.py constants, verbatim: CADENCE_GAP_MS, CADENCE_ARRIVAL_MS, DECEPTIVE_LEARNED.
export const CADENCE = Object.freeze({ GAP_MS: 1500, ARRIVAL_MS: 800, DECEPTIVE_LEARNED: 3 });

// Every kind string practice._cadence can return, verbatim (the two "2 -> 5" kinds are kind.replace("5", "2 -> 5", 1)).
export const KINDS = Object.freeze([
  "5 -> 1 (authentic)",                    // 0
  "5sus -> 1 (suspended dominant)",        // 1
  "2 -> 5 -> 1 (authentic)",               // 2
  "2 -> 5sus -> 1 (suspended dominant)",   // 3
  "5 over a 1 pedal -> 1",                 // 4
  "5 -> 6m (deceptive)",                   // 5
  "5 -> b6 (deceptive)",                   // 6
  "4m -> 1 (minor plagal)",                // 7
  "4 -> 1 (plagal)",                       // 8
  "b6 -> b7 -> 1 (Aeolian)",               // 9
  "b7 -> 1",                               // 10
]);
const AUTHENTIC = 0, SUS = 1, TWO_AUTHENTIC = 2, TWO_SUS = 3, PEDAL = 4, DECEPTIVE_MAJOR = 5, DECEPTIVE_MINOR = 6,
  MINOR_PLAGAL = 7, PLAGAL = 8, AEOLIAN = 9, FLAT_SEVEN = 10;

const GAP = CADENCE.GAP_MS;
const ARRIVAL = CADENCE.ARRIVAL_MS;

function popcount12(m) {
  m = m - ((m >> 1) & 0x555);
  m = (m & 0x333) + ((m >> 2) & 0x333);
  return (m + (m >> 4) + (m >> 8)) & 0xf;
}

// Python truthiness of an area: a window has one when its id is a number (0 included).
function hasArea(w) { return w.area !== null && w.area !== undefined; }
function hasPc(v) { return v !== null && v !== undefined; }
// Python truthiness of third: "major"/"minor" truthy; None (null/undefined) falsy.
function truthyThird(t) { return t !== null && t !== undefined && t !== ""; }
function eqThird(t, s) { return t === s; }
// a pc rotated so the tonic is 0, as a bit: is (tonic + rel) % 12 in the mask
function has(mask, tonic, rel) { return (mask >> ((tonic + rel) % 12)) & 1; }

// _chordal: a root, and three or more root-relative pcs or exactly {0, 7}
function chordal(w) {
  const r = w.root_pc;
  if (!hasPc(r)) return false;
  const m = w.mask | 0;
  return popcount12(m) >= 3 || m === ((1 << r) | (1 << ((r + 7) % 12)));
}

// _bass_dominant: an unnamed held set over the 5 in the bass, holding the key's leading tone
function bassDominant(w, areas) {
  if (hasPc(w.root_pc) || !hasArea(w) || !hasPc(w.bass_pc) || !w.low_bass) return false;
  const tex = w.texture;
  if (tex !== undefined && tex !== "chord") return false;  // a missing texture counts as "chord" (w.get("texture", "chord"))
  const m = w.mask | 0;
  if (popcount12(m) < 3) return false;
  const tonic = areas[w.area].tonic;
  return (w.bass_pc - tonic + 12) % 12 === 7 && ((m >> ((tonic + 11) % 12)) & 1) === 1;
}

// _passing_moment: no harmony of its own (not a bass dominant, and no root or not chordal)
function passingMoment(w, areas) {
  if (bassDominant(w, areas)) return false;
  return !hasPc(w.root_pc) || !chordal(w);
}

// _rel(w, pc) for a w known to have an area and a pc known to be set
function rel(pc, tonic) { return (pc - tonic + 12) % 12; }

/** The cadence (if any) from ws[n-1] (or the chord before the passing moments) into ws[n]: practice._cadence. */
export function judge(ws, areas, n, out) {
  out.kind = null;
  if (n < 1 || n >= ws.length) return false;  // practice judges n in 1..len-1: no window before 0, none after the end
  const b = ws[n];
  let lead = n - 1;
  while (lead >= 1 && passingMoment(ws[lead], areas) && b.start_ms - ws[lead].start_ms <= GAP) lead--;
  const a = ws[lead];
  if (!hasArea(a)) return false;
  const area = a.area;
  if (b.area !== area || b.start_ms - a.end_ms > GAP) return false;
  const dominant = bassDominant(a, areas);
  const aRoot = dominant ? a.bass_pc : a.root_pc;
  const aThird = dominant ? "major" : a.third;
  if (!hasPc(aRoot) || !hasPc(b.root_pc) || !(dominant || chordal(a)) || !chordal(b)) return false;
  if (b.end_ms - b.start_ms < ARRIVAL || !hasPc(a.bass_pc) || !hasPc(b.bass_pc)) return false;
  const ar = areas[area];
  const tonic = ar.tonic;
  const major = ar.mode === "major";
  const arel = rel(aRoot, tonic), brel = rel(b.root_pc, tonic);
  const bassA = rel(a.bass_pc, tonic), bassB = rel(b.bass_pc, tonic);
  let kind = -1, first = lead, last = n;
  const prev = lead >= 1 ? ws[lead - 1] : null;
  const prevOk = prev !== null && hasPc(prev.root_pc) && prev.area === area && a.start_ms - prev.end_ms <= GAP &&
    popcount12(prev.mask | 0) >= 3;
  const am = a.mask | 0, bm = b.mask | 0;
  const six = major ? 9 : 8;
  const sixThird = major ? "minor" : "major";
  const nxt = n + 1 < ws.length ? ws[n + 1] : null;
  if (arel === 7 && brel === 0 && bassB === 0) {
    if (bassA === 7) {
      kind = truthyThird(aThird) ? AUTHENTIC : SUS;
      if (prevOk && rel(prev.root_pc, tonic) === 2) {
        kind = kind === AUTHENTIC ? TWO_AUTHENTIC : TWO_SUS;
        first = lead - 1;
      }
    } else if (bassA === 0) {
      kind = PEDAL;
    }
  } else if (brel === 0 && bassA === 0 && bassB === 0 && has(am, tonic, 7) && has(am, tonic, 11) && has(am, tonic, 2) &&
      !has(am, tonic, 3) && !has(am, tonic, 4) && !has(bm, tonic, 11) && truthyThird(b.third) &&
      has(bm, tonic, major ? 4 : 3)) {
    kind = PEDAL;  // the 5 chord's notes over the home note in the bass, resolving above it
  } else if (arel === 7 && bassA === 7 && bassB === six && brel === bassB && eqThird(b.third, sixThird)) {
    kind = major ? DECEPTIVE_MAJOR : DECEPTIVE_MINOR;
  } else if (arel === 7 && bassA === 7 && truthyThird(aThird) && bassB === six && brel === six && !hasPc(b.third) &&
      nxt !== null && nxt.area === area && nxt.start_ms - b.end_ms <= GAP &&
      nxt.root_pc === b.root_pc && nxt.bass_pc === b.bass_pc && eqThird(nxt.third, sixThird)) {
    kind = major ? DECEPTIVE_MAJOR : DECEPTIVE_MINOR;  // through a sus on 6
    last = n + 1;
  }
  if (kind === DECEPTIVE_MAJOR || kind === DECEPTIVE_MINOR) {
    let k = lead - 1;  // a 6m -> 5 -> 6m neighbour motion never expected home: no deceptive cadence
    while (k >= 0 && ws[k].root_pc === aRoot && ws[k].area === area) k--;
    if (k >= 0 && ws[k].area === area && ws[k].root_pc === b.root_pc && eqThird(ws[k].third, sixThird) &&
        ws[k + 1].start_ms - ws[k].end_ms <= GAP) return false;
  } else if (brel === 0 && bassB === 0 && bassA !== 0) {
    if (arel === 5) {
      kind = aThird === "minor" ? MINOR_PLAGAL : PLAGAL;
    } else if (arel === 10) {
      if (prevOk && rel(prev.root_pc, tonic) === 8) {
        kind = AEOLIAN;
        first = lead - 1;
      } else {
        kind = FLAT_SEVEN;
      }
    }
  }
  if (kind < 0) return false;
  out.kind = KINDS[kind];
  out.code = kind;
  out.first = first;
  out.last = last;
  out.startMs = ws[first].start_ms;
  out.endMs = ws[last].end_ms;
  out.dominant = dominant;
  return true;
}
