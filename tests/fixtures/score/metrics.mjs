// Metric helpers for live sheet music receipts: tests/fixtures/score/metrics.mjs (slice LS0). Zero dependencies.
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md section 10, plan-amendments.md section 2
// (metric names) and section 6 LS0. Times are ms, positions are ticks (TPQ 24) unless a helper says otherwise.
//
// Tempo and beat (the tempo lane's evalSynth, moved unchanged apart from units):
//   fmeasure(est, ref, tol)           beat F at +-tol (70 ms, MIREX / mir_eval)
//   evalTempo(truth, run)             Acc1 (8%), Acc1 4%, Acc2 (x2, 1/2, x3, 1/3, x1.5, 2/3), level errors, flips per
//                                     minute, time to lock (within 8% for 2 s), beat F (causal, lag 2, any level),
//                                     meter right (late majority label), downbeat F
//   bandShares(samples, fromMs)       share of ticks steady / loose / free / hold
//   perBands(samples, fromMs)         the lane's raw periodicity bands (no hysteresis, no veto)
//   flipRates(samples, minutes, key)  display flips per minute, with the x1.5 and x2 subsets (sessions2 rule)
// Rhythm:
//   scoreS3(gs, key, bpb, ...)        the section 3 run's score() exactly (onsets / coverage / beats / bars)
//   scoreTicks(est, truth, meter)     onsetsExact, beatsExact, barsOnsetExact on tick positions
//   barsFullyExact(est, truth, meter) onsets, written durations, rests, ties and voices all equal truth, per bar
//   durationsExact(est, truth)        share of matched notes with the truth's written duration
//   restsPerVoicePerBar(notes, meter) rests per voice per bar (all bars and pedalled bars)
//   rung4Precision(shown, truthBars)  precision of metric bars shown from rung 4 (LR4i)
//   accentsPerMinute(marks, minutes)

export const mean = (a) => { const b = a.filter(Number.isFinite); return b.length ? b.reduce((x, y) => x + y, 0) / b.length : NaN; };
export const median = (a) => { const s = a.filter(Number.isFinite).sort((x, y) => x - y); if (!s.length) return NaN; const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
export const pct = (a, p) => { const s = a.filter(Number.isFinite).sort((x, y) => x - y); return s.length ? s[Math.min(s.length - 1, Math.floor(p / 100 * s.length))] : NaN; };

// ------------------------------------------------------------------------------------------------ beats ---
export function fmeasure(est, ref, tol = 70) {
  let i = 0, j = 0, tp = 0; est = [...est].sort((a, b) => a - b); ref = [...ref].sort((a, b) => a - b);
  while (i < est.length && j < ref.length) { const d = est[i] - ref[j]; if (Math.abs(d) <= tol) { tp++; i++; j++; } else if (d < 0) i++; else j++; }
  const p = est.length ? tp / est.length : 0, rc = ref.length ? tp / ref.length : 0; return p + rc ? 2 * p * rc / (p + rc) : 0;
}
export function levelsOf(ref) {
  const dbl = []; for (let i = 0; i < ref.length - 1; i++) dbl.push(ref[i], (ref[i] + ref[i + 1]) / 2);
  const tri = []; for (let i = 0; i < ref.length - 1; i++) tri.push(ref[i], ref[i] + (ref[i + 1] - ref[i]) / 3, ref[i] + 2 * (ref[i + 1] - ref[i]) / 3);
  return { dbl, half0: ref.filter((_, i) => i % 2 === 0), half1: ref.filter((_, i) => i % 2 === 1), tri };
}

// truth: { beats_ms, nom_ms, ferm, downs_ms, meter }  (genPiece truth)
// run:   { samples: [{ t_ms, bpm, hold }], emitted_ms, settled_ms, meterLog: [{ t_ms, label }], downs_ms }
export function evalTempo(truth, run, { skipMs = 5000, readFromMs = 4000 } = {}) {
  const beats = truth.beats_ms, nom = truth.nom_ms, ferm = truth.ferm;
  const ref = beats.filter((t) => t >= skipMs), est = run.emitted_ms.filter((t) => t >= skipMs);
  const L = levelsOf(beats), ge = (a) => a.filter((t) => t >= skipMs);
  const fAny = Math.max(fmeasure(est, ref), fmeasure(est, ge(L.dbl)), fmeasure(est, ge(L.half0)), fmeasure(est, ge(L.half1)), fmeasure(est, ge(L.tri)));
  const localBpm = (T) => {
    let k = 0; while (k < beats.length - 1 && beats[k + 1] <= T) k++;
    if (ferm[k] || (k > 0 && ferm[k - 1])) return null;
    const w = [nom[Math.max(0, k - 1)], nom[k], nom[Math.min(nom.length - 1, k + 1)]]; return 60000 / median(w);
  };
  let n = 0, a1 = 0, a1s = 0, a2 = 0, flips = 0, lockT = null, run8 = 0, prev = null;
  const end = beats[beats.length - 1];
  for (const s of run.samples) {
    if (s.t_ms < readFromMs || s.t_ms > end) continue;
    const tb = localBpm(s.t_ms); if (!tb) { prev = null; continue; }
    n++;
    if (!s.bpm || s.hold) { prev = null; run8 = 0; continue; }
    const q = s.bpm / tb, ok1 = Math.abs(q - 1) <= 0.08, ok1s = Math.abs(q - 1) <= 0.04;
    const ok2 = ok1 || [2, 0.5, 3, 1 / 3, 1.5, 2 / 3].some((m) => Math.abs(q / m - 1) <= 0.08);
    if (ok1) a1++; if (ok1s) a1s++; if (ok2) a2++;
    if (ok1) { run8++; if (run8 >= 8 && lockT == null) lockT = (s.t_ms - 1750) / 1000; } else run8 = 0;
    if (prev) { const r2 = s.bpm / prev; if (r2 > 1.25 || r2 < 0.8) flips++; }
    prev = s.bpm;
  }
  const mins = (end - readFromMs) / 60000;
  const late = (run.meterLog || []).filter((m) => m.t_ms > end * 0.5);
  const votes = {}; late.forEach((m) => (votes[m.label] = (votes[m.label] || 0) + 1));
  const meterFinal = Object.entries(votes).sort((x, y) => y[1] - x[1])[0]?.[0] || null;
  const downs = (run.downs_ms || []).filter((t) => t >= skipMs), downRef = (truth.downs_ms || []).filter((t) => t >= skipMs);
  return {
    fb: fmeasure(est, ref), fbLag: fmeasure((run.settled_ms || []).filter((t) => t >= skipMs), ref), fAny,
    acc1: a1 / n, acc1s: a1s / n, acc2: a2 / n, octave: (a2 - a1) / n, flipsPerMin: flips / mins, lockT, meterFinal,
    meterOK: meterFinal === (typeof truth.meter === "string" ? truth.meter : truth.meter?.label), fdb: fmeasure(downs, downRef),
  };
}

export function bandShares(samples, fromMs = 8000) {
  const S = samples.filter((s) => s.t_ms > fromMs), n = S.length || 1, out = { steady: 0, loose: 0, free: 0, hold: 0 };
  for (const s of S) out[s.mode] = (out[s.mode] || 0) + 1;
  for (const k of Object.keys(out)) out[k] /= n;
  return out;
}
export function perBands(samples, fromMs = 8000) {
  const S = samples.filter((s) => s.t_ms > fromMs), n = S.length || 1;
  return { steady: S.filter((s) => s.per >= 4.5).length / n, loose: S.filter((s) => s.per >= 3 && s.per < 4.5).length / n, free: S.filter((s) => !(s.per >= 3)).length / n };
}
// Display flips (a ratio outside 0.8-1.25 between successive readouts), and the x1.5 and x2 ones (within 8%).
export function flipRates(samples, minutes, key = "bpm") {
  let flips = 0, sesq = 0, oct = 0, prev = null;
  for (const s of samples) {
    const v = s[key];
    if (!v || s.mode === "hold") { prev = null; continue; }
    if (prev) { const x = v / prev; if (x > 1.25 || x < 0.8) { flips++; if (Math.abs(x / 1.5 - 1) < 0.08 || Math.abs(x * 1.5 - 1) < 0.08) sesq++; if (Math.abs(x / 2 - 1) < 0.08 || Math.abs(x * 2 - 1) < 0.08) oct++; } }
    prev = v;
  }
  return { flips: flips / minutes, sesq: sesq / minutes, oct: oct / minutes };
}

// ---------------------------------------------------------------------------------------------- rhythm ---
// The section 3 run's score(): groups carry pos (twelfths of a beat, truth), t (s), bb (assigned beat) and the
// estimate under `key`. A bar is right when every onset position in it is right.
export const normDivS3 = (set) => { const a = [...set]; if (a.every((p) => p === 0)) return 1; if (a.every((p) => p % 6 === 0)) return 2; if (a.every((p) => p % 4 === 0)) return 3; if (a.every((p) => p % 3 === 0)) return 4; return 12; };
export function scoreS3(gs, key, bpb, skipT = 5, mapPos = (v) => v) {
  const ev = gs.filter((g) => g.t >= skipT);
  let ok = 0, cov = 0; const barsAll = new Map(), tB = new Map(), eB = new Map();
  for (const g of ev) {
    const v = g[key] == null || g.bb == null ? null : mapPos(g[key], g);
    const bar = Math.floor(g.pos / (12 * bpb)); if (!barsAll.has(bar)) barsAll.set(bar, true);
    const k = Math.floor(g.pos / 12); if (!tB.has(k)) tB.set(k, new Set()); tB.get(k).add(g.pos % 12);
    if (v == null) { barsAll.set(bar, false); continue; }
    cov++; if (v === g.pos) ok++; else barsAll.set(bar, false);
    const ke = Math.floor(v / 12); if (!eB.has(ke)) eB.set(ke, new Set()); eB.get(ke).add(((v % 12) + 12) % 12);
  }
  let dOk = 0, dN = 0; for (const [k, s] of tB) { dN++; if (eB.has(k) && normDivS3(eB.get(k)) === normDivS3(s) && [...eB.get(k)].sort().join() === [...s].sort().join()) dOk++; }
  const bars = [...barsAll.values()];
  return { acc: cov ? ok / cov : NaN, cov: ev.length ? cov / ev.length : NaN, beatOk: dN ? dOk / dN : NaN, barOk: bars.length ? bars.filter(Boolean).length / bars.length : NaN };
}

const DIVS = [1, 2, 3, 4, 6, 8, 12];
export function normDiv(positions, beatTicks) {
  const a = [...positions];
  for (const d of DIVS) { if (beatTicks % d) continue; const step = beatTicks / d; if (a.every((p) => p % step === 0)) return d; }
  return beatTicks;
}

// est, truth: [{ id, tick }] (est tick null = not placed). meter: { beatTicks, barTicks }. Onsets before skipTick are
// ignored. Matching is by id.
export function scoreTicks(est, truth, { beatTicks, barTicks }, { skipTick = -Infinity } = {}) {
  const byId = new Map(est.map((e) => [e.id, e]));
  let ok = 0, cov = 0, n = 0; const bars = new Map(), tB = new Map(), eB = new Map();
  const floorDiv = (a, b) => Math.floor(a / b);
  for (const tn of truth) {
    if (tn.tick < skipTick) continue;
    n++;
    const bar = floorDiv(tn.tick, barTicks); if (!bars.has(bar)) bars.set(bar, true);
    const k = floorDiv(tn.tick, beatTicks); if (!tB.has(k)) tB.set(k, new Set()); tB.get(k).add(tn.tick - k * beatTicks);
    const e = byId.get(tn.id);
    if (!e || e.tick == null) { bars.set(bar, false); continue; }
    cov++; if (e.tick === tn.tick) ok++; else bars.set(bar, false);
    const ke = floorDiv(e.tick, beatTicks); if (!eB.has(ke)) eB.set(ke, new Set()); eB.get(ke).add(e.tick - ke * beatTicks);
  }
  let dOk = 0, dN = 0;
  for (const [k, s] of tB) { dN++; const es = eB.get(k); if (es && normDiv(es, beatTicks) === normDiv(s, beatTicks) && [...es].sort((a, b) => a - b).join() === [...s].sort((a, b) => a - b).join()) dOk++; }
  const bv = [...bars.values()];
  return { onsetsExact: cov ? ok / cov : NaN, coverage: n ? cov / n : NaN, beatsExact: dN ? dOk / dN : NaN, barsOnsetExact: bv.length ? bv.filter(Boolean).length / bv.length : NaN, bars: bv.length };
}

// Clip a note list to bars: per bar, the sorted signature of (voice, pitch, start in bar, length in bar, tied in, tied out).
function barSignatures(notes, barTicks) {
  const out = new Map();
  for (const n of notes) {
    if (n.tick == null || n.dur == null) continue;
    let a = n.tick; const z = n.tick + n.dur;
    while (a < z) {
      const bar = Math.floor(a / barTicks), be = (bar + 1) * barTicks, e = Math.min(z, be);
      const sig = `${n.voice}|${n.note}|${a - bar * barTicks}|${e - a}|${a > n.tick ? 1 : 0}|${e < z ? 1 : 0}`;
      if (!out.has(bar)) out.set(bar, []);
      out.get(bar).push(sig);
      a = e;
    }
  }
  for (const l of out.values()) l.sort();
  return out;
}
export function barsFullyExact(est, truth, { barTicks }, { skipBars = 0 } = {}) {
  const T = barSignatures(truth, barTicks), E = barSignatures(est, barTicks);
  let ok = 0, n = 0;
  for (const [bar, sig] of T) { if (bar < skipBars) continue; n++; const e = E.get(bar); if (e && e.join("\n") === sig.join("\n")) ok++; }
  return { barsFullyExact: n ? ok / n : NaN, bars: n };
}
export function durationsExact(est, truth) {
  const byId = new Map(est.map((e) => [e.id, e]));
  let ok = 0, n = 0;
  for (const t of truth) { const e = byId.get(t.id); if (!e || e.dur == null) continue; n++; if (e.dur === t.dur && e.tick === t.tick) ok++; }
  return { durationsExact: n ? ok / n : NaN, matched: n };
}

// Rests per voice per bar: gaps inside the bar in each voice that sounds in that bar (a voice silent for a whole bar
// is not counted; voice 2 hides whole-bar rests). pedalled: a Set of bar indices (pedal down >= 50% of the bar).
export function restsPerVoicePerBar(notes, { barTicks }, { pedalled = null } = {}) {
  const per = new Map();
  for (const n of notes) {
    let a = n.tick; const z = n.tick + n.dur;
    while (a < z) { const bar = Math.floor(a / barTicks), e = Math.min(z, (bar + 1) * barTicks); const k = `${bar}|${n.voice}`; if (!per.has(k)) per.set(k, []); per.get(k).push([a - bar * barTicks, e - bar * barTicks]); a = e; }
  }
  const counts = [], pedCounts = [];
  for (const [k, spans] of per) {
    const bar = Number(k.split("|")[0]);
    spans.sort((x, y) => x[0] - y[0]);
    let rests = 0, at = 0;
    for (const [s, e] of spans) { if (s > at) rests++; at = Math.max(at, e); }
    if (at < barTicks) rests++;
    counts.push(rests);
    if (pedalled && pedalled.has(bar)) pedCounts.push(rests);
  }
  return { median: median(counts), mean: mean(counts), pedalledMedian: median(pedCounts), pedalledMean: mean(pedCounts), voiceBars: counts.length };
}

// shown: [{ start_ms, end_ms, onsetsExact: boolean }] bars drawn metric from rung 4 that settled; truthBars_ms: true bar
// lines. A bar counts only when both its lines lie within tolMs of consecutive true bar lines and every onset is exact.
export function rung4Precision(shown, truthBars_ms, allBars, { tolMs = 70 } = {}) {
  const near = (t) => { let best = -1, bd = Infinity; truthBars_ms.forEach((x, i) => { const d = Math.abs(x - t); if (d < bd) { bd = d; best = i; } }); return bd <= tolMs ? best : null; };
  let ok = 0;
  for (const b of shown) { const i = near(b.start_ms), j = near(b.end_ms); if (i != null && j === i + 1 && b.onsetsExact) ok++; }
  return { precision: shown.length ? ok / shown.length : NaN, shownShare: allBars ? shown.length / allBars : NaN, shown: shown.length, correct: ok };
}

export const accentsPerMinute = (marks, minutes) => (minutes > 0 ? marks.length / minutes : NaN);
