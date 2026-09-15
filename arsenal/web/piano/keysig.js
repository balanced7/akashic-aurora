// Key signatures for the "now" staff: arsenal/web/piano/keysig.js (pure ES module: no three.js, no DOM).
// Ruling: research/in-flight/live-sheet-music-2026-09-14/ls1-rulings.md, "LS6 rulings" (Daniel, 2026-09-15: "if it could
// change depending on the key so we dont have a million flats", and for the signature "Auto, after it settles"). Spelling:
// the one shared speller, piano/spell.js (tn1-rulings.md, the TN2 spelling ruling). Tests: tests/piano_keysig.test.mjs.
//
//   const sig = createKeySignatureModel();
//   sig.update({ t, key: "Eb major", sure: true, manual: null, bar: null, chord: 17 })   // at the key tracker's 10 Hz tick
//   sig.view(t)   // { key: "Eb major", signature: { type: "flats", count: 3, ... }, showing: false, change: null, id, ... }
//   staffAccidental({ letter: 5, acc: -1 }, sig.view(t).signature)   // null: A-flat needs no accidental under three flats
//   signaturePlaces(sig.view(t).signature, "treble")                  // [{ acc: -1, diatonic: 34 }, ...] B4 E5 A4 (C4 = 28)
//
// The rule (LS6, as built here):
// - Source: the key the Nashville numbers use (the page's key tracker, or the jam key while Claude's band plays). A key Daniel
//   locks by hand wins at once: no settle gate, no spacing, even inside an open chord.
// - Settle gate: a new key is adopted once the tracker has shown it with lock confidence (fair or sure; the jam key counts
//   as sure) without a break for 2 bars, or 4 s in free time (no bar clock).
// - Never inside an open chord: once the gate is met, the change waits until the chord sounding at that moment has ended (a
//   new onset, or silence). With a bar clock it waits for the next bar line instead.
// - At most one change per 8 bars (16 s in free time, 2 s a bar, as the 4 s gate counts 2 bars). A change the spacing holds
//   back keeps waiting, and is dropped if the tracker moves on.
// - While the tracker is unsure, or names no key, the last settled signature stays.
// - A change draws a double bar and the new signature (and a small "-> key" tag) for showSec, 2 s. The first key after none
//   draws no double bar: there is no signature to change from.
// Inputs (update): t, seconds on a steady clock; key, the key shown (a name, a tracker key { name } or { tonic, mode }, or
// null); sure, whether the tracker holds it with lock confidence; manual, a key Daniel locked (null in auto); bar, null in
// free time or { index: the bar number, pos: bars as a float }; chord, an id of the chord sounding (any value that changes
// with each new onset, e.g. the page's note-on count) or null in silence.
import { keyContext, keySignature } from "./spell.js";

export const KEYSIG_API = "arsenal.piano.keysig/v1";

// Staff positions of a signature's accidentals, as diatonic steps (C4 = 28, piano.js Theory.diatonicOf), in the order a staff
// writes them: sharps F C G D A E B, flats B E A D G C F.
const PLACES = {
  treble: { sharps: [38, 35, 39, 36, 33, 37, 34], flats: [34, 37, 33, 36, 32, 35, 31] },  // F5 C5 G5 D5 A4 E5 B4 / B4 E5 A4 D5 G4 C5 F4
  bass: { sharps: [24, 21, 25, 22, 19, 23, 20], flats: [20, 23, 19, 22, 18, 21, 17] },    // F3 C3 G3 D3 A2 E3 B2 / B2 E3 A2 D3 G2 C3 F2
};

const nameOfKey = (key) => {
  const K = key ? keyContext(key) : null;
  return K ? K.name : null;
};

export function createKeySignatureModel({ holdBars = 2, holdSec = 4, gapBars = 8, barSec = 2, showSec = 2 } = {}) {
  let settled = null;   // the key the staff shows
  let signature = keySignature(null);
  let change = null;    // { from, to, at, manual }: the last change from one signature to another
  let last = null;      // { t, pos }: when the signature last changed (the first key included)
  let cand = null;      // { key, t, pos }: a key the gate is timing, shown with lock confidence since t (bar position pos)
  let gate = null;      // { key, chord, bar }: a key whose gate and spacing are met, waiting for its chord or bar to close
  let cached = null;
  const history = [];   // [{ t, from, to, manual }]

  function adopt(key, t, pos, manual) {
    change = settled ? { from: settled, to: key, at: t, manual } : null;
    history.push({ t, from: settled, to: key, manual });
    settled = key;
    signature = keySignature(key);
    last = { t, pos };
    cand = null;
    gate = null;
  }

  function update({ t, key = null, sure = false, manual = null, bar = null, chord = null } = {}) {
    const pos = bar && Number.isFinite(bar.pos) ? bar.pos : null;
    const index = bar && Number.isFinite(bar.index) ? bar.index : pos !== null ? Math.floor(pos) : null;
    const m = nameOfKey(manual);
    if (m) {  // a key Daniel locked wins at once
      if (m !== settled) adopt(m, t, pos, true);
      cand = null;
      gate = null;
      return view(t);
    }
    const k = nameOfKey(key);
    if (!k || !sure || k === settled) {  // unsure, no key, or the key already shown: keep the signature, time nothing
      cand = null;
      gate = null;
      return view(t);
    }
    if (!cand || cand.key !== k) { cand = { key: k, t, pos }; gate = null; }
    const held = pos !== null && cand.pos !== null ? pos - cand.pos >= holdBars : t - cand.t >= holdSec;
    if (!held) return view(t);
    const spaced = !last || (pos !== null && last.pos !== null ? pos - last.pos >= gapBars : t - last.t >= gapBars * barSec);
    if (!spaced) return view(t);
    if (!gate) gate = { key: k, chord, bar: index };
    const closed = index !== null && gate.bar !== null ? index > gate.bar : chord == null || chord !== gate.chord;
    if (closed) adopt(k, t, pos, false);
    return view(t);
  }

  // What the staff draws at time t. id changes exactly when the drawing does (a new key, or the change mark going away).
  function view(t) {
    const showing = !!change && t >= change.at && t - change.at < showSec;
    const id = `${settled || "-"}|${showing ? change.at : ""}`;
    if (!cached || cached.id !== id) {
      cached = { id, key: settled, signature, showing, change: showing ? { ...change } : null };
    }
    return cached;
  }

  const state = () => ({ key: settled, signature, change, last, candidate: cand ? { ...cand } : null, waiting: gate ? { ...gate } : null,
                         changes: history.length });
  return { update, view, state, history: () => history.map((h) => ({ ...h })) };
}

// The accidental a staff draws for a spelled note ({ letter, acc }) under a signature: null when the signature already gives
// it, 0 for a natural that cancels the signature, else the note's own accidental (-2..2). No signature: the note's own
// accidental, or null for a natural.
export function staffAccidental(sp, signature) {
  const inSig = signature && Array.isArray(signature.accidentals) ? signature.accidentals.find((a) => a.letter === sp.letter) : null;
  const sigAcc = inSig ? inSig.acc : 0;
  return sp.acc === sigAcc ? null : sp.acc;
}

// Where each of a signature's accidentals sits on a staff ("treble" or "bass"): [{ acc, name, diatonic }].
export function signaturePlaces(signature, clef = "treble") {
  if (!signature || !signature.count) return [];
  const row = PLACES[clef === "bass" ? "bass" : "treble"][signature.type === "flats" ? "flats" : "sharps"];
  return signature.accidentals.map((a, i) => ({ acc: a.acc, name: a.name, diatonic: row[i] }));
}
