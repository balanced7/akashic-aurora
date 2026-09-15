// Beat, rough BPM and steadiness from expressive MIDI: arsenal/web/piano/score/beat.js (pure ES module: no DOM, no clock).
// Stage T2 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (sections 6.2, 5.2), amended by
// plan-amendments.md (C4 count-in validity, C11 subdivision). The inferred rung is the tempo lane's causal tracker
// (tempo-meter.md 4.1, recommended configuration) moved here unchanged: IOI induction with periodicity strength, up to
// 24 competing agents, lag-2 settled beats, the tatum meter. On top of it sit the product rules: steadiness bands with
// hysteresis, bpmShown, the family for the ÷2 / ×2 / 2↔3 buttons, taps and "This is 1", and the rung 3-5 ladder.
//
//   const bt = createBeatTracker({}, { meter: "4/4" });
//   bt.addGroup(group)            // groups from onsets.js flush(), in order (t, s, low, pcs, avail)
//   bt.pedal(true, t)             // pedal crossings (meter accents)
//   bt.tap(t); bt.thisIsOne(t)    // rung 3
//   const s = bt.tick(nowMs)      // every 250 ms of event time: { bpm, bpmShown, mode, source, drawing, family, ... }
//
// All times are ms in one timebase. tick() does the work; addGroup() only queues, so a replay and the live page agree.
//
// Steadiness (plan 6.2): periodicity strength = best induction score / mean score. Bands >= 4.5 steady, 3-4.5 loose,
// < 3 free. A higher band must hold for bandHoldMs (2 s) before the word rises; a lower band takes over after
// bandLowerMs (500 ms, a start value): with a symmetric 2 s the word stayed steady for 0.8% of random playing (LR3a),
// and lowering the word toward tape is the safe direction. The chosen agent's hit share over its last 8 beats may only
// lower the word: below hitVeto (0.5, a start value) it drops one step. "hold" (no onset for max(2 s, 2.5 beats))
// overrides the word.
// Readout: the median of the last 4 beat intervals, leaving out an interval that ends at a beat re-anchored after a hold
// (it measures the pause, not the tempo; the hold keeps the period). Counting it read half tempo after pauses on S5.
// bpmShown (T2.3): an integer that changes at most once a bar (of the shown tempo under the meter) and only by >= 3 bpm.
// A value is shown only after the readout has held it for shownConfirmBars bars at its own tempo with no flip (x1.25
// between ticks), no gap and no hold, so a transient is never latched for a whole bar (LR3b measures shown flips).
// Tactus under the committed meter (plan 6.2 readout): with a set meter the tracked beat is converted by the measured
// subdivision (1, 2 or 3 tatums, held for meterHold decisions): simple meters x1/2 when grid 1 at >= 125 bpm, else x1;
// compound meters x1 on grid 3, x2/3 on grid 2, x1/3 on grid 1 at >= 125 bpm. The grid and the 125 bpm test change
// together, only after meterHold decisions (tested per tick, an agent near 125 bpm flipped the display x2 on S14 about
// once a minute with no change of level). No conversion while taps are valid or a chosen level holds.
// meter "auto" is the tempo lane's own
// tatum-template meter with 4-decision hysteresis and its priors (4/4 +0.02, 6/8 +0.05, 12-tatum bars -0.03): kept to
// reproduce the lane's tables (LR1) and as the evidence meter.js (LS3) will turn into suggestions. It never commits a
// meter on the page.
// Taps (deck.js TEMPO rule): 4 taps, median gap, 40-200 bpm, reset after 2 s. A tap period within 8% of a live agent
// whose grid is within its hit window of the last tap selects that agent; otherwise a tap agent is seeded at the taps.
// Either way that agent's lineage (it and its children) is the only one shown while taps are valid: tapValidBars (4,
// C4 start value) bars of the tap period after the last tap. After that rung-4 rules apply: no pool restriction, the
// 1.5x switching law and the tactus conversion. Taps replace any chosen level.
// Chosen level (chooseLevel, the family buttons): the shown agent is kept within levelOct (0.2 octave) of the level.
// The playing tempo is read from a shadow of the rung-4 choice (the same 1.5x switching law over every agent) by its
// readout period (median of its last 4 intervals). At the press the level stores q = level period / shadow period, so
// the level expected from the playing tempo is shadow x q. Once a second, while the level is within levelOct of shadow
// x q, the chosen agent's period is held within familyOct of it (a x2 or x1/2 agent hits only some beats and drifted
// 15-20% on its own under rub1) and the window follows the agent: the level carries the playing tempo, the agent only
// its phase. After levelHold (4) decisions in a row where it is not, the level lets go and rung-4 rules apply: the
// playing tempo left the window (a tempo change the shadow did not follow in place, or the shadow moved to another
// agent), or no agent is left near the level. q is never re-based on a shadow move: re-basing moves that looked
// metrical (x1.5, x2/3, ...) kept a stuck level after a 70 -> 95 step whenever the stuck shadow's period had drifted to
// a metrical ratio of the new one (942 / 626 ms), and it bought nothing on the rubato suites (LS1-level receipt).

export const BEAT_API = "arsenal.piano.score.beat/v0";

export const BEAT_PARAMS = Object.freeze({
  tickMs: 250,
  // induction
  winMs: 12000, pMinMs: 150, pMaxMs: 3000, binOct: 1 / 60, sigma: 0.035, gamma: 0.8, priorBpm: 80, priorOct: 0.7,
  // agents (tempo lane recommended configuration)
  inner: 0.18, innerMinMs: 60, phaseGain: 0.8, periodGain: 0.35, periodMin: 0.7, periodMax: 1.4, tauMs: 10000,
  miss: 0.15, maxAgents: 24, switchRatio: 1.5, candidates: 3, anchors: 2, anchorSpanMs: 2500, dupOct: 0.04, dupPhaseMs: 70,
  // pauses
  holdMs: 2000, holdBeats: 2.5,
  // steadiness
  steady: 4.5, loose: 3, bandHoldMs: 2000, bandLowerMs: 500, hitVeto: 0.5,
  // readout
  ibiAcrossHolds: false, shownMinDelta: 3, shownConfirmBars: 1, shownFlip: 1.25, familyOct: 0.06, levelOct: 0.2, levelHold: 4,
  // meter evidence (tatum templates) and tactus conversion
  meterHold: 4, meterBeats: 32, meterMinBeats: 12, fastBpm: 125, bonus44: 0.02, bonus68: 0.05, pen12: 0.03,
  accentBass: 0.7, accentHarm: 1.2, accentPedal: 0.8,
  // taps (deck.js TEMPO) and rung 3 validity (C4)
  taps: 4, tapResetMs: 2000, tapMin: 40, tapMax: 200, tapSelect: 0.08, tapValidBars: 4,
});

// The tempo lane's tracker as it ran (LR1 reproduces its tables): the readout counts the interval across a hold, and
// bpmShown shows a value without confirmation.
export const LANE_BEAT_PARAMS = Object.freeze({ ibiAcrossHolds: true, shownConfirmBars: 0 });

export const METERS = Object.freeze({
  "2/4": Object.freeze({ label: "2/4", beats: 2, beatType: 4, tactusPerBar: 2, compound: false }),
  "3/4": Object.freeze({ label: "3/4", beats: 3, beatType: 4, tactusPerBar: 3, compound: false }),
  "4/4": Object.freeze({ label: "4/4", beats: 4, beatType: 4, tactusPerBar: 4, compound: false }),
  "6/8": Object.freeze({ label: "6/8", beats: 6, beatType: 8, tactusPerBar: 2, compound: true }),
  "12/8": Object.freeze({ label: "12/8", beats: 12, beatType: 8, tactusPerBar: 4, compound: true }),
});

export const FAMILY_RATIOS = Object.freeze([2, 0.5, 1.5, 2 / 3]);
const BAND_RANK = Object.freeze({ free: 0, loose: 1, steady: 2 });

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const median = (a) => { if (!a.length) return NaN; const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

function pearson(x, y) {
  const n = x.length, mx = x.reduce((a, b) => a + b) / n, my = y.reduce((a, b) => a + b) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; }
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : 0;
}

// ------------------------------------------------------------------------------------------------ the ladder ---
// Which rung draws, from what the page knows at a tick (plan 6.2 ladder table). Rungs 1-2 are decided here from
// their inputs; their beats arrive in LS7 (jam, via tempomap.js) and LS8 (song listener).
//   jam:      { live, aligned }                        -> bars
//   song:     { phaseConf, floor, one }                -> bars once "This is 1" is known, else beat-aligned tape
//   taps:     { valid, one }                           -> bars once "This is 1" is known, else beat-aligned tape
//   inferred: { mode }                                  -> bars only while steady (LR4g), else tape
//   meter "free" always draws tape.
export function ladder({ jam = null, song = null, taps = null, inferred = null, meter = "4/4" } = {}) {
  const free = meter === "free";
  if (jam && jam.live && jam.aligned) return { source: "jam", drawing: free ? "tape" : "bars" };
  if (song && song.phaseConf != null && song.phaseConf >= (song.floor ?? 0.5)) return { source: "song", drawing: free ? "tape" : song.one ? "bars" : "beat-tape" };
  if (taps && taps.valid) return { source: "taps", drawing: free ? "tape" : taps.one ? "bars" : "beat-tape" };
  if (inferred && inferred.mode) return { source: "inferred", drawing: !free && inferred.mode === "steady" ? "bars" : "tape" };
  return { source: "free", drawing: "tape" };
}

// ------------------------------------------------------------------------------------------- the tracker ---
export function createBeatTracker(params = {}, options = {}) {
  const c = { ...BEAT_PARAMS, ...params };
  const trace = !!options.trace;
  let meterSetting = options.meter || "4/4";
  let meterSource = options.meter ? (options.meter === "auto" ? "auto" : "user") : "default";

  const prior = (bpm) => Math.exp(-0.5 * (Math.log2(bpm / c.priorBpm) / c.priorOct) ** 2);
  let AID = 0;
  const agentOf = (p, next, t) => ({ id: ++AID, p, p0: p, next, score: 0, last: t, beats: [], base: 0, line: null });

  const gs = [];                 // processed groups, oldest trimmed after 120 s
  const queue = [];              // groups added since the last tick
  const pedals = [];             // pedal downs (meter accents), last 40 s
  let agents = [], chosen = null, lastT = -1, nGroups = 0;
  let sal = [], perNow = null;
  const pending = [];            // [{ a, b, rec }] beats of the chosen agent waiting to settle (lag 2)
  // lane meter (auto) and grid hysteresis state
  let meter = null, cand = null, candN = 0;
  let grid = null, gridCand = null, gridN = 0;
  let meterSec = -Infinity;      // the last whole event second the meter / grid step ran for
  // product state
  let band = "free", bandCand = null, bandSince = 0;
  let shown = null, shownAt = -Infinity, shownCand = null;
  const beatLog = [];            // product beats: [{ t_ms, index, conf, settled, agentId }], last 128
  let lastEmit = null;
  let barPhase = null, pendingOne = null;
  let tapTimes = [], tapLine = null, tapUntil = -Infinity;
  let level = null, shadow = null;   // chosen level { p, rel, off } and the rung-4 shadow choice (see header)
  let holdFrom = null;
  const holds = [];
  let lastSample = null;
  const tr = trace ? { emitted: [], emittedLag: [], meterLog: [], samples: [] } : null;

  // ---------------------------------------------------------------------------------------- induction ---
  function induce(i1, now) {
    const lmin = Math.log2(c.pMinMs), nb = Math.ceil((Math.log2(c.pMaxMs) - lmin) / c.binOct) + 1;
    const H = new Float64Array(nb), sb = c.sigma / c.binOct;
    let i0 = i1; while (i0 > 0 && gs[i0 - 1].t >= now - c.winMs) i0--;
    for (let i = i0; i < i1; i++) for (let j = i + 1; j < i1; j++) {
      const d = gs[j].t - gs[i].t; if (d < c.pMinMs) continue; if (d > c.pMaxMs) break;
      const w = gs[i].s * gs[j].s * Math.pow(c.gamma, j - i - 1), x = (Math.log2(d) - lmin) / c.binOct;
      for (let b = Math.max(0, Math.floor(x - 3 * sb)); b <= Math.min(nb - 1, Math.ceil(x + 3 * sb)); b++) { const z = (b - x) / sb; H[b] += w * Math.exp(-0.5 * z * z); }
    }
    const at = (lp) => { const x = (lp - lmin) / c.binOct; if (x < 0 || x > nb - 1) return 0; const b = Math.floor(x), f = x - b; return H[b] * (1 - f) + (b + 1 < nb ? H[b + 1] * f : 0); };
    const C = new Float64Array(nb);
    for (let b = 0; b < nb; b++) {
      const lp = lmin + b * c.binOct, bpm = 60000 / 2 ** lp; if (bpm < 35 || bpm > 200) continue;
      C[b] = (at(lp) + 0.5 * at(lp + 1) + 0.33 * at(lp + Math.log2(3)) + 0.25 * at(lp + 2)) * prior(bpm);
    }
    const cands = [];
    for (let b = 1; b < nb - 1; b++) if (C[b] > 0 && C[b] >= C[b - 1] && C[b] > C[b + 1]) cands.push({ p: 2 ** (lmin + b * c.binOct), score: C[b] });
    cands.sort((a, b) => b.score - a.score);
    let sum = 0, cnt = 0; for (let b = 0; b < nb; b++) if (C[b] > 0) { sum += C[b]; cnt++; }
    const per = cands.length && sum > 0 ? cands[0].score / (sum / cnt) : 0;
    return { cands: cands.slice(0, 4), i0, per };
  }

  // ------------------------------------------------------------------------------------------- agents ---
  function stepAgent(a, g, meanS, kids) {
    const inner = Math.max(c.innerMinMs, c.inner * a.p), out = [];
    while (a.next < g.t - inner) { const b = { t: a.next, s: 0, g: null, idx: a.base + a.beats.length }; if (a.anchor) { b.anchor = true; a.anchor = false; } a.beats.push(b); out.push(b); a.next += a.p; a.score -= c.miss * meanS; }
    const err = g.t - a.next;
    a.score *= Math.exp(-(g.t - a.last) / c.tauMs); a.last = g.t;
    if (Math.abs(err) <= inner) {
      a.p = clamp(a.p + c.periodGain * err, a.p0 * c.periodMin, a.p0 * c.periodMax);
      const b = { t: a.next + c.phaseGain * err, s: g.s, g, idx: a.base + a.beats.length }; if (a.anchor) { b.anchor = true; a.anchor = false; } a.beats.push(b); out.push(b);
      a.next = b.t + a.p; a.score += g.s * (1 - 0.5 * Math.abs(err) / inner);
    } else if (kids && err > -0.2 * a.p && err < 0.35 * a.p && g.s >= meanS) {
      const k = agentOf(clamp(a.p + c.periodGain * err, a.p0 * c.periodMin, a.p0 * c.periodMax), g.t + a.p, g.t);
      k.p0 = a.p0; k.score = a.score * 0.9; k.line = a.line;
      k.beats = a.beats.slice(-16); k.base = a.base + a.beats.length - k.beats.length;
      k.beats.push({ t: g.t, s: g.s, g, idx: k.base + k.beats.length }); kids.push(k);
    }
    if (a.beats.length > 64) { const cut = a.beats.length - 48; a.beats.splice(0, cut); a.base += cut; }
    return out;
  }

  const rank = (a) => a.score * prior(60000 / a.p);
  // an agent's intervals over its last 9 beats as the readout counts them (an interval ending at a beat re-anchored
  // after a hold is left out, see header), and its readout period: the median of the last 4
  function intervalsOf(a) {
    const B = a.beats.slice(-9), ibis = [];
    for (let i = 1; i < B.length; i++) if (c.ibiAcrossHolds || !B[i].anchor) ibis.push(B[i].t - B[i - 1].t);
    return ibis;
  }
  const beatPeriod = (a) => { const ibis = intervalsOf(a); return ibis.length >= 3 ? median(ibis.slice(-4)) : a.p; };
  const tapsValid = (now) => tapLine != null && now <= tapUntil;
  function eligible(now) {
    let pool = agents;
    if (tapsValid(now)) { const line = agents.filter((a) => a.line === tapLine); if (line.length) pool = line; }
    else if (level) { const lv = agents.filter((a) => Math.abs(Math.log2(a.p / level.p)) < c.levelOct); if (lv.length) pool = lv; }
    return pool;
  }

  // ------------------------------------------------------------------------------- product beat output ---
  function emit(b, a, now) {
    if (trace) tr.emitted.push({ t: b.t, agent: a.id, idx: b.idx, down: downOf(b, a), label: meter ? meter.label : null });
    let rec = null;
    if (!lastEmit || b.t >= lastEmit.t_ms + 0.5 * a.p) {
      const index = lastEmit ? lastEmit.index + Math.max(1, Math.round((b.t - lastEmit.t_ms) / a.p)) : 0;
      rec = { t_ms: b.t, index, conf: b.s > 0 ? 1 : 0, settled: false, agentId: a.id };
      beatLog.push(rec); if (beatLog.length > 128) beatLog.splice(0, beatLog.length - 128);
      lastEmit = rec;
      if (pendingOne != null && Math.abs(rec.t_ms - pendingOne) <= 0.5 * a.p) { barPhase = { downbeatIndex: rec.index, source: "this-is-1", t_ms: rec.t_ms }; pendingOne = null; }
    }
    pending.push({ a, b, rec });
    return rec;
  }
  function downOf(b, a) {
    if (!meter || meter.agentId !== a.id) return null;
    return ((((b.idx * (meter.sub || 1) - meter.phase) % meter.K) + meter.K) % meter.K) === 0;
  }

  // ------------------------------------------------------------------------------- meter evidence (lane) ---
  const TEMPLATES = [
    { K: 2, w: [1, 0], name: "2" }, { K: 3, w: [1, 0, 0], name: "3" }, { K: 4, w: [1, 0, 0.5, 0], name: "4" },
    { K: 6, w: [1, 0, 0, 0.6, 0, 0], name: "6:3+3", fast: true }, { K: 6, w: [1, 0, 0.4, 0, 0.4, 0], name: "6:2+2+2", fast: true },
  ];
  const TATUM_T = {
    2: [{ K: 4, w: [1, 0, 0.3, 0], label: "2/4", tactus: 2 }, { K: 6, w: [1, 0, 0.4, 0, 0.4, 0], label: "3/4", tactus: 2 },
      { K: 8, w: [1, 0, 0.3, 0, 0.6, 0, 0.3, 0], label: "4/4", tactus: 2 }, { K: 6, w: [1, 0, 0, 0.6, 0, 0], label: "6/8", tactus: 3 },
      { K: 12, w: [1, 0, 0, 0.4, 0, 0, 0.7, 0, 0, 0.4, 0, 0], label: "12/8", tactus: 3 }],
    3: [{ K: 6, w: [1, 0, 0, 0.6, 0, 0], label: "6/8", tactus: 3 }, { K: 9, w: [1, 0, 0, 0.4, 0, 0, 0.4, 0, 0], label: "9/8", tactus: 3 },
      { K: 12, w: [1, 0, 0, 0.4, 0, 0, 0.7, 0, 0, 0.4, 0, 0], label: "12/8", tactus: 3 }],
  };
  function meterOf(a, gEnd, peds) {
    const B = a.beats.slice(-c.meterBeats); if (B.length < c.meterMinBeats) return null;
    const bpm = 60000 / a.p, acc = [], pcsSpan = [];
    let gi = gEnd; while (gi > 0 && gs[gi - 1].t >= B[0].t - 0.1 * a.p) gi--;
    let offW2 = 0, offW3 = 0;
    for (let k = 0; k < B.length - 1; k++) {
      const lo = B[k].t - 0.1 * a.p, hi = B[k + 1].t - 0.1 * a.p, pcs = new Set(); let sHit = 0, bass = 0;
      while (gi < gEnd && gs[gi].t < lo) gi++;
      for (let j = gi; j < gEnd && gs[j].t < hi; j++) {
        const g = gs[j]; g.pcs.forEach((x) => pcs.add(x));
        const ph = (g.t - B[k].t) / (B[k + 1].t - B[k].t);
        if (Math.abs(g.t - B[k].t) <= Math.max(c.innerMinMs, c.inner * a.p)) { sHit = Math.max(sHit, g.s); if (g.low <= 55) bass = 1; }
        else { if (Math.abs(ph - 0.5) < 0.08) offW2 += g.s; if (Math.abs(ph - 1 / 3) < 0.06 || Math.abs(ph - 2 / 3) < 0.06) offW3 += g.s; }
      }
      let harm = 0; const prev = pcsSpan[k - 1];
      if (prev && prev.size && pcs.size) { let inter = 0; pcs.forEach((x) => { if (prev.has(x)) inter++; }); harm = 1 - inter / (pcs.size + prev.size - inter); }
      pcsSpan.push(pcs);
      const ped = peds.some((p) => p.t >= B[k].t - 50 && p.t <= B[k].t + 0.45 * a.p) ? 1 : 0;
      acc.push({ idx: B[k].idx, v: sHit + c.accentBass * bass + c.accentHarm * harm + c.accentPedal * ped });
    }
    let best = null;
    const seq = acc.map((x) => x.v);
    for (const T of TEMPLATES) {
      if (T.fast && bpm < c.fastBpm) continue;
      if (acc.length < 2 * T.K) continue;
      for (let ph = 0; ph < T.K; ph++) {
        const xs = acc.map((x) => T.w[(((x.idx - ph) % T.K) + T.K) % T.K]);
        const r = pearson(xs, seq);
        if (r <= 0) continue;
        const sc = r * r + (T.name === "4" ? c.bonus44 : 0);
        if (!best || sc > best.score) best = { K: T.K, name: T.name, phase: ph, score: sc };
      }
    }
    if (!best) return null;
    const tern = offW3 + offW2 > 0 ? offW3 / (offW3 + offW2) : 0;
    const compound = tern > 0.6;
    let label;
    if (best.name === "6:3+3") label = "6/8"; else if (best.name === "6:2+2+2") label = "3/4";
    else label = compound ? { 2: "6/8", 3: "9/8", 4: "12/8" }[best.K] : { 2: "2/4", 3: "3/4", 4: "4/4" }[best.K];
    return { ...best, compound, tern, label, agentId: a.id };
  }
  // The subdivision grid over the last 32 beats (tempo lane 6.4 step 1): 3 when thirds beat halves and exceed 25% of
  // on-beat salience, 2 when halves exceed 25%, else 1.
  function gridOf(a, gEnd) {
    const B = a.beats.slice(-c.meterBeats);
    let on = 0, h = 0, th = 0, gi = gEnd; while (gi > 0 && gs[gi - 1].t >= B[0].t) gi--;
    const G = gs.slice(gi, gEnd); let k = 0;
    for (const g of G) {
      if (g.t >= B[B.length - 1].t) break;
      while (k < B.length - 2 && B[k + 1].t <= g.t) k++;
      const ph = (g.t - B[k].t) / (B[k + 1].t - B[k].t);
      if (ph < 0.1 || ph > 0.9) on += g.s; else if (Math.abs(ph - 0.5) < 0.08) h += g.s; else if (Math.abs(ph - 1 / 3) < 0.06 || Math.abs(ph - 2 / 3) < 0.06) th += g.s;
    }
    return { sub: th > h && th > 0.25 * on ? 3 : h > 0.25 * on ? 2 : 1, on, h, th, G, B };
  }
  function meterTatum(a, gEnd, peds) {
    const base = meterOf(a, gEnd, peds); if (!base) return null;
    const { sub, h, th, G, B } = gridOf(a, gEnd);
    if (sub === 1) return { ...base, sub: 1, tactus: base.name === "6:3+3" ? 3 : base.name === "6:2+2+2" ? 2 : 1 };
    const tat = [];
    for (let i = 0; i < B.length - 1; i++) for (let j = 0; j < sub; j++) tat.push({ t: B[i].t + j / sub * (B[i + 1].t - B[i].t), idx: B[i].idx * sub + j, len: (B[i + 1].t - B[i].t) / sub, v: 0 });
    const lowAround = (t) => { let m = 999; for (const g of G) if (Math.abs(g.t - t) <= 800) m = Math.min(m, g.low); return m; };
    let q = 0;
    for (const g of G) {
      while (q < tat.length - 1 && tat[q + 1].t <= g.t) q++;
      let best = null;
      for (const x of [tat[q], tat[q + 1]]) if (x && Math.abs(g.t - x.t) <= Math.max(40, 0.25 * x.len) && (!best || Math.abs(g.t - x.t) < Math.abs(g.t - best.t))) best = x;
      if (!best) continue;
      let v = g.s; if (g.low <= 55 && g.low <= lowAround(g.t)) v += c.accentBass;
      const pre = new Set(), post = new Set();
      for (const h2 of G) { if (h2.t >= g.t - 600 && h2.t < g.t) h2.pcs.forEach((x) => pre.add(x)); if (h2.t >= g.t && h2.t < g.t + 600) h2.pcs.forEach((x) => post.add(x)); }
      if (pre.size && post.size) { let inter = 0; post.forEach((x) => { if (pre.has(x)) inter++; }); v += c.accentHarm * (1 - inter / (pre.size + post.size - inter)); }
      best.v = Math.max(best.v, v);
    }
    for (const p of peds) { if (p.t < tat[0].t) continue; let bi = null; for (const x of tat) { if (x.t > p.t) break; if (p.t - x.t <= 300) bi = x; } if (bi) bi.v += c.accentPedal; }
    const seq = tat.map((x) => x.v); let best = null;
    for (const T of TATUM_T[sub]) {
      if (tat.length < 2 * T.K) continue;
      for (let ph = 0; ph < T.K; ph++) {
        const xs = tat.map((x) => T.w[(((x.idx - ph) % T.K) + T.K) % T.K]); const r = pearson(xs, seq); if (r <= 0) continue;
        const sc = r * r + (T.label === "4/4" ? c.bonus44 : 0) + (T.label === "6/8" ? c.bonus68 : 0) - (T.K === 12 ? c.pen12 : 0);
        if (!best || sc > best.score) best = { K: T.K, phase: ph, score: sc, label: T.label, tactus: T.tactus };
      }
    }
    if (!best) return { ...base, sub: 1, tactus: 1 };
    return { ...best, sub, name: "tatum" + sub, agentId: a.id, tern: th / (h + th || 1), compound: best.tactus === 3 };
  }

  // tactus factor under a set meter, from the held grid (subdivision and the fast test held together); none while taps
  // are valid or a chosen level holds, because that level is the tactus
  function factorFor(now) {
    const m = METERS[meterSetting];
    if (!m || tapsValid(now) || level || !grid || !chosen || grid.agentId !== chosen.id) return 1;
    if (!m.compound) return grid.sub === 1 && grid.fast ? 0.5 : 1;
    if (grid.sub === 3) return 1;
    if (grid.sub === 2) return 2 / 3;
    return grid.fast ? 1 / 3 : 1;
  }

  function familyOf() {
    if (!chosen) return [];
    const base = rank(chosen) || 1e-9, out = [];
    for (const ratio of FAMILY_RATIOS) {
      const target = chosen.p / ratio;
      let best = null;
      for (const a of agents) if (Math.abs(Math.log2(a.p / target)) < c.familyOct && (!best || rank(a) > rank(best))) best = a;
      if (best) out.push({ ratio, score: rank(best) / base, bpm: 60000 / best.p });
    }
    return out;
  }

  // ------------------------------------------------------------------------------------------ inputs ---
  function addGroup(g) { queue.push(g); }
  function pedal(down, t) { if (down) { pedals.push({ t, down: true }); while (pedals.length && pedals[0].t < t - 40000) pedals.shift(); } }

  function tap(t) {
    if (tapTimes.length && t - tapTimes[tapTimes.length - 1] > c.tapResetMs) tapTimes = [];
    tapTimes.push(t);
    if (tapTimes.length > c.taps) tapTimes.shift();
    if (tapTimes.length < c.taps) return null;
    const gaps = tapTimes.slice(1).map((x, i) => x - tapTimes[i]).sort((a, b) => a - b);
    const med = gaps.length % 2 ? gaps[(gaps.length - 1) / 2] : (gaps[gaps.length / 2 - 1] + gaps[gaps.length / 2]) / 2;
    const bpm = clamp(60000 / med, c.tapMin, c.tapMax), p = 60000 / bpm;
    let pick = null;
    for (const a of agents) {
      if (Math.abs(a.p / p - 1) > c.tapSelect) continue;
      const inner = Math.max(c.innerMinMs, c.inner * a.p);
      const d = ((t - a.next) % a.p + a.p) % a.p;
      if (Math.min(d, a.p - d) > inner) continue;
      if (!pick || rank(a) > rank(pick)) pick = a;
    }
    if (!pick) {
      pick = agentOf(p, t + p, t);
      const top = agents.reduce((m, a) => Math.max(m, a.score), 0);
      pick.score = Math.max(top, 1) * 1.1;
      for (const x of tapTimes) {
        const b = { t: x, s: 0, g: null, idx: pick.base + pick.beats.length };
        pick.beats.push(b);
        emit({ ...b, s: 1 }, pick, t);
      }
      agents.push(pick);
    }
    pick.line = pick.id;
    tapLine = pick.id;
    tapUntil = t + c.tapValidBars * tactusPerBar() * p;
    chosen = pick;
    level = null; shadow = pick;   // taps replace a chosen level; their own validity ends at tapUntil (C4)
    return { bpm, period_ms: p, selected: pick.beats.length > c.taps ? "hypothesis" : "seeded" };
  }

  function thisIsOne(t) {
    let best = null;
    for (const r of beatLog) if (!best || Math.abs(r.t_ms - t) < Math.abs(best.t_ms - t)) best = r;
    const p = chosen ? chosen.p : 750;
    if (best && Math.abs(best.t_ms - t) <= 0.5 * p) { barPhase = { downbeatIndex: best.index, source: "this-is-1", t_ms: best.t_ms }; pendingOne = null; }
    else pendingOne = t;
    return barPhase;
  }

  function setMeter(label) {
    if (label !== "auto" && label !== "free" && !METERS[label]) throw new Error(`unknown meter ${label}`);
    meterSetting = label; meterSource = label === "auto" ? "auto" : "user"; grid = null; gridCand = null; gridN = 0;
  }

  function chooseLevel(ratio) {
    if (!chosen) return null;
    const ref = level && shadow && agents.includes(shadow) ? shadow : chosen;
    const target = chosen.p / ratio;
    let best = null;
    for (const a of agents) if (Math.abs(Math.log2(a.p / target)) < c.familyOct && (!best || rank(a) > rank(best))) best = a;
    if (!best) {
      const last = chosen.beats[chosen.beats.length - 1];
      best = agentOf(target, (last ? last.t : chosen.next - chosen.p) + target, last ? last.t : chosen.last);
      if (last) best.beats.push({ ...last, idx: 0 });
      best.score = chosen.score;
      agents.push(best);
    }
    chosen = best;
    level = { p: best.p, q: best.p / beatPeriod(ref), off: 0 };
    shadow = ref;
    if (tapLine != null) best.line = tapLine;
    return { bpm: 60000 / best.p };
  }

  const tactusPerBar = () => (METERS[meterSetting] ? METERS[meterSetting].tactusPerBar : 4);

  // ------------------------------------------------------------------------------------------- tick ---
  function tick(T) {
    let newG = false;
    const born = [];
    while (queue.length) {
      const g = queue.shift();
      sal.push(g.s); if (sal.length > 40) sal.shift();
      const meanS = sal.reduce((a, b) => a + b, 0) / sal.length;
      if (lastT >= 0 && g.t - lastT > Math.max(c.holdMs, c.holdBeats * (chosen ? chosen.p : 750))) {
        for (const a of agents) { const gap = g.t - a.next; if (gap > 0) { a.next = g.t; a.score *= 0.5; a.last = g.t; a.anchor = true; } }
      }
      if (holdFrom != null) { holds.push({ from_ms: holdFrom, to_ms: g.t }); if (holds.length > 64) holds.shift(); holdFrom = null; }
      const kids = [];
      for (const a of agents) {
        const out = stepAgent(a, g, meanS, agents.length < c.maxAgents ? kids : null);
        if (chosen && a.id === chosen.id) for (const b of out) born.push(emit(b, a, T));
      }
      agents.push(...kids);
      gs.push(g); lastT = g.t; nGroups++; newG = true;
    }
    if (gs.length > 2000 && gs[0].t < T - 120000) { let k = 0; while (k < gs.length && gs[k].t < T - 120000) k++; gs.splice(0, k); }

    const settledNow = [];
    for (let q = pending.length - 1; q >= 0; q--) {
      const { a, b, rec } = pending[q]; const alive = agents.includes(a), last = a.base + a.beats.length - 1;
      if (last >= b.idx + 2 || !alive) {
        let t = b.g ? b.g.t : b.t; const i = b.idx - a.base;
        if (alive && !b.g && i >= 0) {
          let lo = i - 1, hi = i + 1; while (lo >= 0 && !a.beats[lo].g) lo--; while (hi < a.beats.length && !a.beats[hi].g) hi++;
          if (lo >= 0 && hi < a.beats.length) t = a.beats[lo].g.t + (a.beats[hi].g.t - a.beats[lo].g.t) * (i - lo) / (hi - lo);
        }
        if (trace) tr.emittedLag.push(t);
        if (rec) { rec.t_ms = t; rec.settled = true; settledNow.push(rec); }
        pending.splice(q, 1);
      }
    }
    settledNow.sort((x, y) => x.t_ms - y.t_ms);

    if (newG && nGroups >= 3) {
      const gi = gs.length;
      const { cands, i0, per } = induce(gi, T);
      perNow = per;
      const meanS = sal.reduce((a, b) => a + b, 0) / sal.length;
      for (const cd of cands.slice(0, c.candidates)) {
        if (agents.some((a) => Math.abs(Math.log2(a.p / cd.p)) < c.dupOct)) continue;
        const win = []; for (let j = i0; j < gi; j++) if (gs[j].t <= gs[i0].t + c.anchorSpanMs) win.push(j);
        win.sort((x, y) => gs[y].s - gs[x].s);
        for (const aj of win.slice(0, c.anchors)) {
          const a = agentOf(cd.p, gs[aj].t, gs[aj].t);
          a.beats.push({ t: gs[aj].t, s: gs[aj].s, g: gs[aj], idx: 0 }); a.next = gs[aj].t + cd.p; a.score = gs[aj].s;
          for (let j = aj + 1; j < gi; j++) stepAgent(a, gs[j], meanS, null);
          agents.push(a);
        }
      }
      agents.sort((x, y) => y.score - x.score);
      const keep = [];
      for (const a of agents) {
        const dupOf = keep.find((k) => Math.abs(Math.log2(k.p / a.p)) < c.dupOct && (() => { const d = Math.abs(((a.next - k.next) % k.p + k.p) % k.p); return Math.min(d, k.p - d) < c.dupPhaseMs; })());
        if (!dupOf) keep.push(a);
        else if (a.line != null && dupOf.line == null) dupOf.line = a.line;
        if (keep.length >= c.maxAgents) break;
      }
      if (tapsValid(T) && !keep.some((a) => a.line === tapLine)) {
        const line = agents.filter((a) => a.line === tapLine);
        if (line.length) keep.push(line[0]);
      }
      agents = keep;
      const pool = eligible(T);
      const best = pool.reduce((m, a) => (!m || rank(a) > rank(m) ? a : m), null);
      if (best && (!chosen || !pool.includes(chosen) || rank(best) > rank(chosen) * c.switchRatio)) chosen = best;
      if (level) {
        const top = agents.reduce((m, a) => (!m || rank(a) > rank(m) ? a : m), null);
        if (top && (!shadow || !agents.includes(shadow) || rank(top) > rank(shadow) * c.switchRatio)) shadow = top;
      } else shadow = chosen;
    }

    // readout
    let bpm = null, conf = 0, cv = 1, state = "none";
    if (chosen) {
      const B = chosen.beats.slice(-9);
      if (B.length >= 5) {
        const ibis = intervalsOf(chosen);
        conf = B.slice(-8).filter((b) => b.s > 0).length / 8;
        if (ibis.length >= 3) {
          bpm = 60000 / median(ibis.slice(-4));
          const m = ibis.reduce((a, b) => a + b) / ibis.length; cv = Math.sqrt(ibis.reduce((a, b) => a + (b - m) ** 2, 0) / ibis.length) / m;
        }
      }
      const gap = lastT >= 0 ? T - lastT : 0;
      if (bpm && gap > Math.max(c.holdMs, c.holdBeats * 60000 / bpm)) state = "hold";
      else if (bpm && conf >= 0.6 && cv < 0.15) state = "lock";
      else if (bpm && (conf < 0.35 || cv > 0.3)) state = "free";
      else if (bpm) state = "tent";
    }
    if (state === "hold" && holdFrom == null) holdFrom = lastT;

    // meter evidence once a second of event time: the lane's committed label (auto) and the held grid (set meters).
    // The step runs on the first tick in each new whole second, whatever the tick phase: a live page ticks at
    // performance-clock times that never land on a whole second, and a stall that skips seconds counts as one decision.
    // On the 250 ms replay grid this is the tick at 1000, 2000, ... as the tempo lane ran it (LR1).
    const sec = Math.floor(T / 1000), meterStep = sec > meterSec;
    if (meterStep) meterSec = sec;
    if (chosen && meterStep) {
      const peds = pedals.filter((p) => p.t <= T && p.t >= T - 40000);
      if (meterSetting === "auto" || trace) {
        const m = meterTatum(chosen, gs.length, peds);
        if (m) {
          if (!meter || m.agentId !== meter.agentId || m.label === meter.label) { meter = m; cand = null; candN = 0; }
          else { if (cand && cand.label === m.label) candN++; else candN = 1; cand = m; if (candN >= c.meterHold) { meter = m; cand = null; candN = 0; } }
          if (trace) tr.meterLog.push({ T, label: meter.label, raw: m.label });
        }
      }
      if (chosen.beats.length >= c.meterMinBeats) {
        const sub = gridOf(chosen, gs.length).sub, fast = 60000 / chosen.p >= c.fastBpm, key = sub + (fast ? "f" : "s");
        if (!grid || grid.agentId !== chosen.id || grid.key === key) { grid = { sub, fast, key, agentId: chosen.id }; gridCand = null; gridN = 0; }
        else { if (gridCand === key) gridN++; else { gridCand = key; gridN = 1; } if (gridN >= c.meterHold) { grid = { sub, fast, key, agentId: chosen.id }; gridCand = null; gridN = 0; } }
      }
    }
    // a chosen level, once a second (header): hold the chosen agent near shadow x q and follow it while the level is
    // within levelOct of shadow x q; let go after levelHold decisions in a row that it is not
    if (level && meterStep) {
      const exp = shadow ? beatPeriod(shadow) * level.q : level.p;
      const inWin = !!chosen && Math.abs(Math.log2(chosen.p / level.p)) < c.levelOct;
      const ok = inWin && Math.abs(Math.log2(level.p / exp)) < c.levelOct;
      if (ok) {
        const lo = exp * 2 ** -c.familyOct, hi = exp * 2 ** c.familyOct;
        if (chosen.p < lo || chosen.p > hi) {
          chosen.p = clamp(chosen.p, lo, hi); chosen.p0 = exp;
          const lb = chosen.beats[chosen.beats.length - 1]; if (lb) chosen.next = lb.t + chosen.p;
        }
        level.p = chosen.p;
      }
      level.off = ok ? 0 : level.off + 1;
      if (level.off >= c.levelHold) level = null;
    }
    let factor = 1;
    if (meterSetting === "auto") factor = bpm && meter && chosen && meter.agentId === chosen.id ? (meter.sub || 1) / (meter.tactus || 1) : 1;
    else if (bpm) factor = factorFor(T);
    const bpmT = bpm ? bpm * factor : null;
    if (trace) tr.samples.push({ T, bpm, bpmT: bpm && meter && chosen && meter.agentId === chosen.id ? bpm * (meter.sub || 1) / (meter.tactus || 1) : bpm, state, per: perNow, conf });

    // steadiness bands with hysteresis; hit share may only lower the word
    let raw = perNow == null ? "free" : perNow >= c.steady ? "steady" : perNow >= c.loose ? "loose" : "free";
    if (bpm && conf < c.hitVeto) raw = raw === "steady" ? "loose" : "free";
    if (raw !== band) {
      if (bandCand !== raw) { bandCand = raw; bandSince = T; }
      if (T - bandSince >= (BAND_RANK[raw] < BAND_RANK[band] ? c.bandLowerMs : c.bandHoldMs)) { band = raw; bandCand = null; }
    } else bandCand = null;
    const mode = state === "hold" ? "hold" : band;

    // bpmShown: the readout must have held without a flip, gap or hold for shownConfirmBars bars at its own tempo; then
    // at most once a bar, only by >= shownMinDelta
    if (bpmT && state !== "hold") {
      if (!shownCand || bpmT / shownCand.last > c.shownFlip || shownCand.last / bpmT > c.shownFlip) shownCand = { since: T, last: bpmT };
      else shownCand.last = bpmT;
      if (T - shownCand.since >= c.shownConfirmBars * tactusPerBar() * 60000 / bpmT) {
        const v = Math.round(bpmT);
        if (shown == null) { shown = v; shownAt = T; }
        else if (Math.abs(v - shown) >= c.shownMinDelta && T - shownAt >= tactusPerBar() * 60000 / shown) { shown = v; shownAt = T; }
      }
    } else shownCand = null;

    const valid = tapsValid(T);
    const source = valid ? "taps" : chosen ? "inferred" : "none";
    const rung = ladder({ taps: { valid, one: !!barPhase }, inferred: chosen ? { mode } : null, meter: meterSetting === "auto" ? "4/4" : meterSetting });
    lastSample = {
      t_ms: T, bpm: bpmT, bpmBeat: bpm, bpmShown: shown, mode, band, per: perNow, hitShare: conf, cv,
      source, drawing: rung.drawing, period_ms: chosen ? chosen.p : null, factor, levelBpm: level ? 60000 / level.p : null,
      subdivision: grid && chosen && grid.agentId === chosen.id ? grid.sub : null,
      family: familyOf(), beats: born.filter(Boolean), settled: settledNow,
    };
    return lastSample;
  }

  function state() {
    const m = METERS[meterSetting];
    return {
      api: BEAT_API, source: lastSample ? lastSample.source : "none", mode: lastSample ? lastSample.mode : "free",
      beats: beatLog.slice(-32).map((r) => ({ ...r })), period_ms: chosen ? chosen.p : null,
      bpm: lastSample ? lastSample.bpm : null, bpmShown: shown, family: lastSample ? lastSample.family : [],
      meter: meterSetting === "auto"
        ? { label: meter ? meter.label : null, source: "auto", subdivision: meter ? meter.sub || 1 : null }
        : { label: meterSetting, beats: m ? m.beats : null, beatType: m ? m.beatType : null, tactusPerBar: m ? m.tactusPerBar : null,
          subdivision: grid ? grid.sub : null, source: meterSource },
      barPhase, pickup: null, holds: holds.slice(), per: perNow,
      taps: { valid: lastSample ? lastSample.source === "taps" : false, until_ms: tapLine != null ? tapUntil : null },
    };
  }

  return { addGroup, pedal, tap, thisIsOne, setMeter, chooseLevel, tick, state, trace: () => tr, params: () => ({ ...c }) };
}

// ------------------------------------------------------------------------------------ replay convenience ---
// Run practice-log events (t_ms, kind on/off/pedal/sound_end) through onsets.js and a tracker on the tick clock.
// taps: [t_ms]; one: t_ms of "This is 1"; onTick(sample) sees every tick; phaseMs shifts every tick (a live page's clock
// never lands on the 250 ms grid). Returns the samples and the tracker.
export function trackEvents(events, { createOnsets, onsetParams = {}, params = {}, options = {}, taps = [], one = null, onTick = null, endMs = null, phaseMs = 0 } = {}) {
  const on = createOnsets(onsetParams);
  const bt = createBeatTracker(params, options);
  const evs = [...events].sort((a, b) => a.t_ms - b.t_ms);
  const tq = [...taps].sort((a, b) => a - b);
  const tickMs = bt.params().tickMs;
  const last = endMs ?? ((evs.length ? evs[evs.length - 1].t_ms : 0) + 1000);
  const samples = [];
  let i = 0, k = 0, oneDone = one == null;
  for (let T = tickMs + phaseMs; T <= last; T += tickMs) {
    while (true) {
      const e = i < evs.length && evs[i].t_ms <= T ? evs[i] : null;
      const tp = k < tq.length && tq[k] <= T ? tq[k] : null;
      if (e == null && tp == null) break;
      if (tp != null && (e == null || tp <= e.t_ms)) { bt.tap(tp); k++; if (!oneDone && one <= tp) { bt.thisIsOne(one); oneDone = true; } continue; }
      if (e.kind === "on") on.noteOn(e.note, e.vel, e.t_ms);
      else if (e.kind === "off") on.noteOff(e.note, e.t_ms);
      else if (e.kind === "pedal") { on.pedal(e.down, e.t_ms); bt.pedal(e.down, e.t_ms); }
      else if (e.kind === "sound_end") on.soundEnd(e.note, e.t_ms, e.by);
      i++;
    }
    for (const g of on.flush(T)) bt.addGroup(g);
    if (!oneDone && one <= T) { bt.thisIsOne(one); oneDone = true; }
    const s = bt.tick(T);
    samples.push(s);
    if (onTick) onTick(s, bt);
  }
  return { samples, tracker: bt };
}
