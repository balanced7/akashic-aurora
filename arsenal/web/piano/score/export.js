// The export view of a clean copy: arsenal/web/piano/score/export.js (pure ES module: no DOM, no clock).
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md sections 7.4 and 8, amended by
// plan-amendments.md C3 (a span with no rung 1-3 exports forced bars at the rough BPM, every measure marked "freely").
//
//   exportScore(events, opts)      -> score   clean(events, opts) (or pinnedClean when opts.bpm), then forceTape
//   pinnedClean(events, opts)      -> score   clean() on a fixed grid at opts.bpm (tactus beats) with opts.one (ms) a
//                                             downbeat, else the first onset: rhythm "unverified", every measure forced
//   forceTape(score, events, opts) -> score   notes the clean copy leaves as tape (outside every segment) become forced
//                                             bars: each run of tape notes (split where an onset follows the previous
//                                             note-on or release by runGapMs, 2 s, or where a measure starts between them)
//                                             is re-transcribed by clean() on a fixed grid at the rough BPM of the nearest
//                                             measures (the median tactus beat of their segment; else the score's; else
//                                             750 ms), first beat leadShare (3%) of a beat before its first onset, with
//                                             the same speller, key areas and options. Its measures go in before the first
//                                             measure starting after the run, kind "tape", forced true, segment "f<run>.<seg>".
// The result is the score JSON with measures reindexed 0..n-1 in written order, startTick cumulative, note ids of forced
// notes offset past every id in the clean copy, notes' bar and tick remapped, tape empty, clefs and octave lines
// recomputed over the whole sequence (hands.js), and marks placed again on it by time (pedal, dynamics, freely; key
// signatures at the first measure starting at or after their area; accents by note id). A mark time outside every
// measure goes to the next measure's start, or to the end of the last measure. score.view = "export";
// score.forced = { runs, notes, measures, tapeInsideMeasure (tape notes whose time lies inside a clean measure's span:
// their run is written after that measure), tapeLeft (notes a forced pass still left as tape: expected 0) }.

import { clean, meterInfo } from "./index.js";
import { clefsAndOctaves } from "./hands.js";
import { freeTimeMarks } from "./musicxml.js";

export const EXPORT_API = "arsenal.piano.score.export/v0";
export const EXPORT_PARAMS = Object.freeze({ defaultPeriodMs: 750, runGapMs: 2000, leadShare: 0.03, pedalLookbackMs: 60000, forcedMeter: "4/4" });

const median = (a) => { const s = a.filter((x) => Number.isFinite(x) && x > 0).sort((x, y) => x - y); if (!s.length) return null; const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

// median tactus beat (ms) over measures: gaps inside beats_ms, else the span of an uncut bar over its beats
export function periodOfMeasures(ms) {
  const d = [];
  for (const m of ms || []) {
    const b = m.beats_ms || [];
    for (let k = 0; k + 1 < b.length; k++) d.push(b[k + 1] - b[k]);
    if (b.length < 2 && !m.cut && m.end_ms > m.start_ms && m.beats) d.push((m.end_ms - m.start_ms) / m.beats);
  }
  return median(d);
}

const spanOf = (events, span) => (span ? events.filter((e) => e.t_ms >= span.from_ms && e.t_ms <= span.to_ms) : events);

export function pinnedClean(events, opts = {}) {
  const c = { ...EXPORT_PARAMS, ...(opts.exportParams || {}) };
  const { span = null, meter = "4/4", bpm, one = null } = opts;
  const evs = spanOf(events, span);
  const ons = evs.filter((e) => e.kind === "on");
  const rest = { ...opts, bpm: undefined };
  if (!ons.length || !(bpm > 0)) return clean(events, rest);
  const M = meterInfo(meter === "free" ? c.forcedMeter : meter);
  const P = 60000 / bpm, firstOn = Math.min(...ons.map((e) => e.t_ms)), last = Math.max(...evs.map((e) => e.t_ms));
  const anchor = one ?? firstOn - c.leadShare * P;
  const kBack = Math.max(0, Math.ceil((anchor - (firstOn - c.leadShare * P)) / P - 1e-9));
  const b0 = anchor - kBack * P, n = Math.max(3, Math.ceil((last - b0) / P) + 2 * M.tactus + 2);
  const beats = Array.from({ length: n }, (_, k) => b0 + k * P);
  const sc = clean(evs, { ...rest, span: null, meter: meter === "free" ? c.forcedMeter : meter, beats, one: anchor });
  sc.span = span;
  sc.rhythm = "unverified";
  sc.pinned = { bpm, one_ms: anchor };
  for (const m of sc.measures) m.forced = true;
  return sc;
}

export function exportScore(events, opts = {}) {
  const base = opts.bpm ? pinnedClean(events, opts) : clean(events, opts);
  return forceTape(base, spanOf(events, opts.span || null), opts);
}

export function forceTape(sc, events, opts = {}) {
  const c = { ...EXPORT_PARAMS, ...(opts.exportParams || {}) };
  const measures = [...sc.measures].sort((a, b) => a.index - b.index);
  const tape = [...(sc.tape || [])].sort((a, b) => a.t_ms - b.t_ms || a.note - b.note);
  const slotOf = (t) => { let lo = 0, hi = measures.length; while (lo < hi) { const mid = (lo + hi) >> 1; if (measures[mid].start_ms <= t) lo = mid + 1; else hi = mid; } return lo; };

  // ---- runs of tape notes
  const runs = [];
  let tapeInsideMeasure = 0;
  for (const n of tape) {
    const k = slotOf(n.t_ms);
    if (k > 0 && n.t_ms < measures[k - 1].end_ms) tapeInsideMeasure++;
    const r = runs[runs.length - 1];
    if (r && r.slot === k && n.t_ms - r.lastHeard < c.runGapMs) { r.notes.push(n); r.lastHeard = Math.max(r.lastHeard, n.t_ms, n.off_ms ?? n.t_ms); }
    else runs.push({ i: runs.length, slot: k, notes: [n], lastHeard: Math.max(n.t_ms, n.off_ms ?? n.t_ms) });
  }

  // ---- re-transcribe each run on a fixed grid at the rough BPM
  const bySeg = new Map();
  for (const m of measures) { if (!bySeg.has(m.seg)) bySeg.set(m.seg, []); bySeg.get(m.seg).push(m); }
  const globalP = periodOfMeasures(measures);
  const periodNear = (k) => { for (const m of [measures[k - 1], measures[k]]) if (m) { const p = periodOfMeasures(bySeg.get(m.seg)); if (p) return p; } return globalP || c.defaultPeriodMs; };
  const forcedLabel = sc.meter && sc.meter.free ? c.forcedMeter : (sc.meter && sc.meter.label) || c.forcedMeter;
  const K = meterInfo(forcedLabel).tactus;
  const pedals = events.filter((e) => e.kind === "pedal").sort((a, b) => a.t_ms - b.t_ms);
  let idBase = 1 + Math.max(-1, ...(sc.notes || []).map((n) => n.id), ...tape.map((n) => n.id));
  let tapeLeft = 0;
  for (const r of runs) {
    const P = periodNear(r.slot), t0 = r.notes[0].t_ms, b0 = t0 - c.leadShare * P;
    const tEnd = Math.max(...r.notes.map((n) => Math.max(n.t_ms, n.off_ms ?? n.t_ms, n.se_ms ?? n.t_ms)));
    const beats = Array.from({ length: Math.max(3, Math.ceil((tEnd - b0) / P) + 2 * K + 2) }, (_, k) => b0 + k * P);
    const evs = [];
    for (const n of r.notes) {
      evs.push({ t_ms: n.t_ms, kind: "on", note: n.note, vel: n.vel });
      if (n.off_ms != null) evs.push({ t_ms: n.off_ms, kind: "off", note: n.note });
      if (n.se_ms != null) evs.push({ t_ms: n.se_ms, kind: "sound_end", note: n.note, by: null });
    }
    const w0 = t0 - c.pedalLookbackMs, w1 = beats[beats.length - 1];
    let before = null;
    for (const p of pedals) { if (p.t_ms < w0) before = p; else if (p.t_ms <= w1) evs.push(p); }
    if (before && before.down) evs.push({ ...before, t_ms: w0 });
    evs.sort((a, b) => a.t_ms - b.t_ms);
    const sub = clean(evs, { meter: forcedLabel, feel: sc.feel, beats, one: b0, spell: opts.spell || null, keyAreas: opts.keyAreas || null, key: opts.key || null, params: opts.params || {}, options: opts.options || {}, voiceOf: opts.voiceOf || null, tickMs: opts.tickMs || 250 });
    tapeLeft += sub.tape.length;
    r.P = P; r.beats = beats; r.sub = sub; r.idBase = idBase; r.barMap = new Map();
    idBase += 1 + Math.max(-1, ...sub.notes.map((n) => n.id), ...sub.tape.map((n) => n.id));
  }

  // ---- merge in written order
  const items = [];
  let ri = 0;
  for (let k = 0; k <= measures.length; k++) {
    while (ri < runs.length && runs[ri].slot === k) { const r = runs[ri++]; for (const m of [...r.sub.measures].sort((a, b) => a.index - b.index)) items.push({ m, run: r }); }
    if (k < measures.length) items.push({ m: measures[k], run: null });
  }
  const mapBase = new Map(), outMeasures = [];
  let tick = 0;
  items.forEach((it, i) => {
    const m = it.m, off = it.run ? it.run.idBase : 0;
    const nm = {
      ...m, index: i, startTick: tick, seg: it.run ? `f${it.run.i}.${m.seg}` : m.seg, forced: !!(it.run || m.forced),
      kind: it.run ? "tape" : m.kind, source: it.run ? "forced" : m.source,
      voices: m.voices.map((v) => ({ ...v, notes: v.notes.map((p) => ({ ...p, id: p.id + off })), rests: v.rests.map((x) => ({ ...x })) })),
      beams: (m.beams || []).map((b) => ({ ...b, ids: b.ids.map((id) => id + off) })),
    };
    if (it.run) it.run.barMap.set(m.index, i); else mapBase.set(m.index, i);
    outMeasures.push(nm);
    tick += m.barTicks;
  });
  const notes = [];
  for (const n of sc.notes || []) { const i = mapBase.get(n.bar); if (i == null) continue; notes.push({ ...n, bar: i, tick: outMeasures[i].startTick + n.pos }); }
  for (const r of runs) for (const n of r.sub.notes) { const i = r.barMap.get(n.bar); if (i == null) continue; notes.push({ ...n, id: n.id + r.idBase, bar: i, tick: outMeasures[i].startTick + n.pos, kind: "tape", forced: true }); }
  notes.sort((a, b) => a.tick - b.tick || a.note - b.note);

  // ---- clefs and octave lines over the whole sequence
  clefsAndOctaves(outMeasures, (opts.params && opts.params.hands) || {}).forEach((x, i) => { Object.assign(outMeasures[i], { clefs: x.clefs, octave: x.octave, clefChange: x.change, ledgerBeyond: x.beyond, ledgerOverflow: x.overflow }); });

  // ---- marks placed again by time
  const byTime = outMeasures.map((m, i) => i).sort((a, b) => outMeasures[a].start_ms - outMeasures[b].start_ms || a - b);
  const place = (t) => {
    if (!outMeasures.length || !Number.isFinite(t)) return { bar: null, pos: null };
    let lo = 0, hi = byTime.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (outMeasures[byTime[mid]].start_ms <= t) lo = mid + 1; else hi = mid; }
    const m = lo > 0 ? outMeasures[byTime[lo - 1]] : null;
    if (m && t < m.end_ms) { const f = (t - m.start_ms) / Math.max(1e-9, m.end_ms - m.start_ms); return { bar: m.index, pos: Math.min(m.barTicks - 1, Math.max(0, Math.round(f * m.barTicks))) }; }
    if (lo < byTime.length) return { bar: byTime[lo], pos: 0 };
    const lastM = outMeasures[outMeasures.length - 1];
    return { bar: lastM.index, pos: lastM.barTicks };
  };
  const firstNoteOfGroup = new Map();
  for (const n of notes) if (!n.forced && n.group != null && !firstNoteOfGroup.has(n.group)) firstNoteOfGroup.set(n.group, n);
  const M0 = sc.marks || {};
  const noteById = new Map(notes.map((n) => [n.id, n]));
  const marks = {
    ...M0,
    pedal: (M0.pedal || []).map((mk) => { const g = mk.group != null ? firstNoteOfGroup.get(mk.group) : null; return { ...mk, ...(g ? { bar: g.bar, pos: g.pos } : place(mk.at_ms)) }; }),
    dynamics: (M0.dynamics || []).map((d) => ({ ...d, ...place(d.at_ms) })),
    accents: (M0.accents || []).map((a) => { const n = noteById.get(a.id); return n ? { ...a, bar: n.bar, pos: n.pos } : a; }),
    keySignatures: (M0.keySignatures || []).map((k) => {
      if (k.initial) return { ...k, bar: outMeasures.length ? 0 : null };
      if (k.at_ms != null) { const m = outMeasures.find((x) => x.start_ms >= k.at_ms); return { ...k, bar: m ? m.index : null }; }
      return { ...k, bar: mapBase.has(k.bar) ? mapBase.get(k.bar) : null };
    }),
    // ls1-rulings.md LS4: "freely" once per free-time passage, "a tempo" where a tracked beat resumes (musicxml.js rule)
    freely: freeTimeMarks(outMeasures).filter((x) => x.text === "freely").map((x) => ({ at_ms: outMeasures[x.index].start_ms, bar: x.index, pos: 0 })),
    aTempo: freeTimeMarks(outMeasures).filter((x) => x.text === "a tempo").map((x) => ({ at_ms: outMeasures[x.index].start_ms, bar: x.index, pos: 0 })),
  };
  const segments = [...(sc.segments || []), ...runs.map((r) => ({ id: `f${r.i}`, source: "forced", factor: 1, start_ms: r.beats[0], end_ms: r.beats[r.beats.length - 1], period_ms: r.P, reason: "tape", sigma_ms: null }))];
  const meter = sc.meter && sc.meter.free ? { ...meterInfo(c.forcedMeter), label: "free", free: true } : sc.meter;
  return {
    ...sc, view: "export", meter, segments, measures: outMeasures, notes, tape: [], marks,
    forced: { runs: runs.length, notes: runs.reduce((s, r) => s + r.sub.notes.length, 0), measures: runs.reduce((s, r) => s + r.sub.measures.length, 0), tapeInsideMeasure, tapeLeft, pinned: !!sc.pinned },
  };
}
