// Pedal marks, dynamics, accents, key signatures and tape words for live sheet music: arsenal/web/piano/score/marks.js
// (pure ES module: no DOM, no clock). Stages T6 and T8 of research/in-flight/live-sheet-music-2026-09-14/
// live-sheet-music-plan.md (sections 5.1, 6.5, 6.6) and transcription.md T6-T8, amended by plan-amendments.md C8 (accents
// off in v1) and C5 (pedal crossings only).
//
//   pedalMarks(pedal, { groups, phrases })      -> { marks: [{ type: start | change | stop | conPed, t_ms, at_ms, group }], conPed }
//   dynamicMarks(notes)                         -> [{ band, at_ms, median }]
//   accentMarks(notes, { accents: "off" })      -> [note id]
//   keySignatureChanges(areas)                  -> [{ at_ms, fifths, key, initial }]
//   createKeySignature(); ks.step({ keyView, bar, firstUnsettled }) -> the live signature (first unsettled bar line)
//   freelyMarks(spans)                          -> [{ at_ms }] at each entry into tape
//   placeAt(measures, t_ms)                     -> { bar, pos } | null
//
// Pedal (T6, plan 6.5; C5: only crossings are logged, half-pedal is not in the data): a down within pedalSnapMs (250 ms)
// after an onset group is placed at that group (his pedal lags the chord by a median of 110-190 ms); an up then a down
// within changeMs (300 ms) is one change notch, placed where the down is placed; a longer up is a stop, then a new start.
// con Ped. (plan 6.5): in a phrase (a span split at holds: the caller's segments) whose pedal is down conPedShare (80%) or
// more of the time, one "con Ped." at the phrase start replaces its notches (option conPed, on by default).
// Dynamics (T8): the median velocity of the onsets in consecutive 4 s windows from the first onset maps to bands pp < 36,
// p < 50, mp < 64, mf < 80, f < 96, ff; a band prints once it holds dynHold (2) non-empty windows in a row, placed at the
// first onset of that run (empty windows neither count nor break a run). Absolute bands (a loud night reads louder).
// Accents (C8): accents "off" is the v1 default: no accent marks. accents "voice": a note at least accentOver (25) above the
// running median velocity of the last accentWindow (16) notes in its own voice (at least accentMinHistory, 4, of them),
// with at least accentGap (2) notes of that voice since the last accent, and never the top note of a chord unless every
// note of its onset group clears +25 over its own voice's median. "Voice" is the score voice (hands.js).
// Key signatures (T7): a minor key uses its relative major's signature; fifths from the major tonic as performance.py
// MAJOR_KEY_NAMES spells it (Db, not C#; F# at +6). Clean copies read the closed session's key areas (summary.json
// nashville.areas, 30 s minimum): the first area gives the opening signature, and every later area with other fifths is one
// change at its start. Live (createKeySignature): a new signature is placed at the first unsettled bar line once the key
// tracker has held a non-provisional key with other fifths for holdBars (2) bars; never on a settled bar.
// Tape words (plan 6.5): "freely" at each entry into tape (a run of tape bars or unplaced notes after metric bars or at
// the start). rit. / a tempo and fermatas are not in LS3.

export const MARKS_API = "arsenal.piano.score.marks/v0";

export const MARKS_PARAMS = Object.freeze({
  pedalSnapMs: 250, changeMs: 300, conPed: true, conPedShare: 0.8,
  dynWindowMs: 4000, dynHold: 2, bands: Object.freeze([[36, "pp"], [50, "p"], [64, "mp"], [80, "mf"], [96, "f"], [Infinity, "ff"]]),
  accents: "off", accentOver: 25, accentWindow: 16, accentGap: 2, accentMinHistory: 4,
  holdBars: 2, minAreaMs: 30000,
});

const median = (a) => { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

// ------------------------------------------------------------------------------------------------ pedal ---
// pedal: [{ t_ms, down }]; groups: [{ t, id }] ascending; phrases: [{ start_ms, end_ms }] or null.
export function pedalMarks(pedal, { groups = [], phrases = null, params = {} } = {}) {
  const c = { ...MARKS_PARAMS, ...params };
  const P = [...pedal].sort((a, b) => a.t_ms - b.t_ms);
  const snap = (t) => {
    let lo = 0, hi = groups.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (groups[m].t <= t) lo = m + 1; else hi = m; }
    const g = lo > 0 ? groups[lo - 1] : null;
    return g && t - g.t <= c.pedalSnapMs ? { at: g.t, group: g.id } : { at: t, group: null };
  };
  let marks = [];
  let down = false, lastUp = null;
  for (const p of P) {
    if (p.down && !down) {
      const s = snap(p.t_ms);
      if (lastUp && p.t_ms - lastUp.t_ms <= c.changeMs && marks.length && marks[marks.length - 1].type === "stop") {
        marks.pop();
        marks.push({ type: "change", t_ms: p.t_ms, up_ms: lastUp.t_ms, at_ms: s.at, group: s.group });
      } else marks.push({ type: "start", t_ms: p.t_ms, at_ms: s.at, group: s.group });
      down = true;
    } else if (!p.down && down) {
      marks.push({ type: "stop", t_ms: p.t_ms, at_ms: p.t_ms, group: null });
      lastUp = p; down = false;
    }
  }
  const conPed = [];
  if (c.conPed && phrases) {
    for (const ph of phrases) {
      const len = ph.end_ms - ph.start_ms;
      if (!(len > 0)) continue;
      let st = false, t = ph.start_ms, dn = 0;
      for (const p of P) { if (p.t_ms <= ph.start_ms) { st = p.down; continue; } if (p.t_ms >= ph.end_ms) break; if (st) dn += p.t_ms - t; st = p.down; t = p.t_ms; }
      if (st) dn += ph.end_ms - t;
      if (dn / len >= c.conPedShare) conPed.push({ ...ph, share: dn / len });
    }
    if (conPed.length) {
      marks = marks.filter((m) => !conPed.some((ph) => m.at_ms >= ph.start_ms && m.at_ms < ph.end_ms));
      for (const ph of conPed) marks.push({ type: "conPed", t_ms: ph.start_ms, at_ms: ph.start_ms, group: null });
      marks.sort((a, b) => a.at_ms - b.at_ms);
    }
  }
  return { marks, conPed };
}

// ----------------------------------------------------------------------------------------------- dynamics ---
// notes: [{ t_ms, vel }] (every note-on)
export function dynamicMarks(notes, { params = {} } = {}) {
  const c = { ...MARKS_PARAMS, ...params };
  const N = [...notes].sort((a, b) => a.t_ms - b.t_ms);
  if (!N.length) return [];
  const t0 = N[0].t_ms, wins = new Map();
  for (const n of N) { const k = Math.floor((n.t_ms - t0) / c.dynWindowMs); if (!wins.has(k)) wins.set(k, []); wins.get(k).push(n); }
  const bandOf = (v) => c.bands.find(([lim]) => v < lim)[1];
  const out = [];
  let printed = null, cand = null, run = 0, runStart = null;
  for (const k of [...wins.keys()].sort((a, b) => a - b)) {
    const w = wins.get(k), med = median(w.map((n) => n.vel)), b = bandOf(med);
    if (b === printed) { cand = null; run = 0; continue; }
    if (b === cand) run++; else { cand = b; run = 1; runStart = w[0].t_ms; }
    if (run >= c.dynHold) { out.push({ band: b, at_ms: runStart, median: med }); printed = b; cand = null; run = 0; }
  }
  return out;
}

// ----------------------------------------------------------------------------------------------- accents ---
// notes: [{ id, t_ms, vel, voice, note, group }] (group: the onset group id)
export function accentMarks(notes, { accents = MARKS_PARAMS.accents, params = {} } = {}) {
  const c = { ...MARKS_PARAMS, ...params };
  if (accents !== "voice") return [];
  const N = [...notes].sort((a, b) => a.t_ms - b.t_ms || a.note - b.note);
  const hist = new Map(), since = new Map(), med = new Map();
  for (const n of N) {
    const h = hist.get(n.voice) || [];
    med.set(n.id, h.length >= c.accentMinHistory ? median(h.slice(-c.accentWindow)) : null);
    h.push(n.vel); hist.set(n.voice, h);
  }
  const clears = (n) => med.get(n.id) != null && n.vel >= med.get(n.id) + c.accentOver;
  const byGroup = new Map();
  for (const n of N) { if (!byGroup.has(n.group)) byGroup.set(n.group, []); byGroup.get(n.group).push(n); }
  const out = [];
  for (const n of N) {
    const gap = since.get(n.voice) ?? Infinity;
    let ok = clears(n) && gap >= c.accentGap;
    const G = byGroup.get(n.group);
    if (ok && G.length > 1 && n.note === Math.max(...G.map((x) => x.note)) && !G.every(clears)) ok = false;
    if (ok) { out.push(n.id); since.set(n.voice, 0); } else since.set(n.voice, gap + 1);
  }
  return out;
}

// ---------------------------------------------------------------------------------------- key signatures ---
const MAJOR_FIFTHS = [0, -5, 2, -3, 4, -1, 6, 1, -4, 3, -2, 5];
export const fifthsOf = (tonic, mode) => MAJOR_FIFTHS[(((mode === "minor" ? tonic + 3 : tonic) % 12) + 12) % 12];

// areas: [{ start_ms, end_ms, key: { tonic, mode } }] ascending. An area shorter than minAreaMs (30 s, plan 6.6) never
// changes the signature: a short excursion stays accidentals (summary.json areas can be 12-19 s long). The first area
// gives the opening signature whatever its length.
export function keySignatureChanges(areas, { minAreaMs = MARKS_PARAMS.minAreaMs } = {}) {
  const out = [];
  let cur = null;
  for (const a of areas) {
    if (!a.key) continue;
    if (cur !== null && a.end_ms - a.start_ms < minAreaMs) continue;
    const f = fifthsOf(a.key.tonic, a.key.mode);
    if (cur === null) out.push({ at_ms: a.start_ms, fifths: f, key: a.key, initial: true });
    else if (f !== cur) out.push({ at_ms: a.start_ms, fifths: f, key: a.key, initial: false });
    cur = f;
  }
  return out;
}

// the live rule: keyView { tonic, mode, provisional } | null at each tick; bar: the index of the bar the playhead is in;
// firstUnsettled: the first unsettled bar
export function createKeySignature({ params = {} } = {}) {
  const c = { ...MARKS_PARAMS, ...params };
  let current = null, cand = null, candBar = null;
  const placed = [];
  return {
    step({ keyView, bar, firstUnsettled }) {
      if (keyView && !keyView.provisional && Number.isInteger(keyView.tonic)) {
        const f = fifthsOf(keyView.tonic, keyView.mode);
        if (f === current) { cand = null; candBar = null; }
        else if (f !== cand) { cand = f; candBar = bar; }
        else if (bar - candBar >= c.holdBars && firstUnsettled != null) {
          placed.push({ bar: Math.max(firstUnsettled, placed.length ? placed[placed.length - 1].bar : -Infinity), fifths: f, initial: current === null });
          current = f; cand = null; candBar = null;
        }
      }
      return { current, placed: placed.slice() };
    },
    placed: () => placed.slice(),
  };
}

// ------------------------------------------------------------------------------------------ tape words ---
// spans: [{ start_ms, kind: "metric" | "tape" }] ascending (bars and unplaced notes in time order)
export function freelyMarks(spans) {
  const out = [];
  let prev = null;
  for (const s of spans) { if (s.kind === "tape" && prev !== "tape") out.push({ at_ms: s.start_ms }); prev = s.kind; }
  return out;
}

// ------------------------------------------------------------------------------------------- placement ---
// measures: [{ index, start_ms, end_ms, barTicks }] ascending. A time inside a bar maps linearly to its ticks.
export function placeAt(measures, t_ms) {
  let lo = 0, hi = measures.length;
  while (lo < hi) { const m = (lo + hi) >> 1; if (measures[m].start_ms <= t_ms) lo = m + 1; else hi = m; }
  const b = lo > 0 ? measures[lo - 1] : null;
  if (!b || t_ms >= b.end_ms) return null;
  const f = (t_ms - b.start_ms) / Math.max(1e-9, b.end_ms - b.start_ms);
  return { bar: b.index, pos: Math.min(b.barTicks - 1, Math.max(0, Math.round(f * b.barTicks))) };
}
