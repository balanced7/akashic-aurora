// Meter, bar phase, pickups, the subdivision chip and the header readout for live sheet music:
// arsenal/web/piano/score/meter.js (pure ES module: no DOM, no clock). Stage T2.4 of
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (sections 2.1, 6.3), tempo-meter.md 6.4-6.5,
// amended by plan-amendments.md C11 (feel and the subdivision chip) and ls1-rulings.md (the header after a family press).
//
//   const ms = createMeterState({ meter: "4/4", feel: "straight" });   // his settings, remembered per session
//   const mm = createMeterModel({ meter: "4/4", feel: "straight" });
//   mm.step({ T, sample, beats, groups, pedals })   // every tick; decides once per whole second of event time
//     -> { suggestion: { label, margin } | null, chip: { kind: "triplets" | "straight" } | null, scores }
//   scoreMeters({ beats, groups, pedals })          // the tempo lane's tatum templates, every label's R² (pure)
//   inferPhase({ K, jK, tactusTime, groups, pedals }) // the bar phase whose tactus beats carry the most accent
//   pickupOf(bar, meter)                             // an anacrusis at a phrase start, in whole sub-beats
//   const hd = createHeaderModel(); hd.press(ratio, T, sample); hd.step(sample, T) -> { bpm, dim, word, ... }
//
// Meter is his setting (plan 6.3, tempo-meter.md D1): 4/4 by default, one tap for 3/4, 6/8, 12/8 or free. Nothing here
// changes it; a suggestion chip ("sounds like 3/4?") only asks.
// Suggestion (plan 6.3): the best settable meter's template score beats the current meter's by suggestMargin (0.15 R²)
// for suggestHold (8) consecutive decisions (one a second) while beat.js reads steady. The current meter under a grid
// that has no template for it (4/4 on a triplet grid) is scored by its compound twin (12/8), which is then not offered.
// A dismissed label is not offered again this session.
// Scoring (scoreMeters, tempo-meter.md 6.4 steps 1-3, beat.js meterOf / gridOf / meterTatum ported with every label kept):
// the subdivision grid over the last 32 beats (3 when thirds beat halves and exceed 25% of on-beat salience, 2 when
// halves exceed 25%, else 1); tatum accents (salience, +0.7 new low bass, +1.2 pitch-class change over 0.6 s, +0.8 for a
// pedal down within 0.3 s after); the R² of the whole accent sequence against each template expanded over it, best phase;
// priors 4/4 +0.02, 6/8 +0.05, 12-tatum bars −0.03.
// Subdivision chip (C11): feel is his setting ("straight" | "triplet", simple meters only). chipRule "grid" (the rule as
// written, the default): "sounds like triplets?" when feel is straight and beat.js subdivision reads 3 for chipHold (8)
// consecutive decisions; "sounds straight?" is the mirror (subdivision 2 while feel is triplet). No steady gate: the band
// must be steady or loose, never free or hold. chipRule "tatum" (a measured proposal, not the default): on grids 2 and 3
// the best compound template (6/8, 9/8, 12/8) beats the best simple one (2/4, 3/4, 4/4) by chipMargin, or the grid is 3;
// the mirror when a simple template leads by chipMargin on grid 2. A chip only suggests; nothing changes until he
// accepts (setOptions({ feel })). A dismissed chip kind waits chipHold new decisions before it can return.
// Bar phase (plan 6.3 priority jam -> song -> "This is 1" -> inferred): index.js applies the priority; inferPhase is the
// inferred rung's scorer (the LS2 stand-in moved here unchanged: per phase, the mean accent of its tactus beats over the
// last phaseBeats beats; the caller holds a change for phaseHold decisions with a margin).
// Pickups (plan 6.3): onsets before the first committed downbeat of a phrase are an anacrusis in whole sub-beats (an
// eighth: 12 ticks simple, 12 ticks compound), allowed only while the first bar is unsettled. index.js resets the phase
// of a segment only while none of its bars has settled, so a partial first bar of a segment is always a pickup; a partial
// bar later in a segment (a forward-only phase correction) is written as a partial bar of rests (partial: true).
// Header (plan 2.1, ls1-rulings.md "Readout after ×0.5"): the tempo is bpmShown (it changes at most once a bar), the word
// is steady | loose | free | hold, hold is dimmed. After a family press, until bpmShown confirms the request (within
// confirmTol, 3%), the header shows the requested tempo (beat.js levelBpm, which reads the request from the tick after the
// press), dimmed, with the word "hold". It never shows a blank: with no request value yet it keeps the last value shown.
// The request ends when bpmShown confirms it or the level lets go (levelBpm null after the press tick).

export const METER_API = "arsenal.piano.score.meter/v0";

export const METER_PARAMS = Object.freeze({
  meterBeats: 32, meterMinBeats: 12, fastBpm: 125, bonus44: 0.02, bonus68: 0.05, pen12: 0.03,
  accentBass: 0.7, accentHarm: 1.2, accentPedal: 0.8, inner: 0.18, innerMinMs: 60,
  suggestMargin: 0.15, suggestHold: 8,
  chipRule: "grid", chipHold: 8, chipMargin: 0.05,
  confirmTol: 0.03,
});

export const SETTABLE_METERS = Object.freeze(["4/4", "3/4", "6/8", "12/8"]);
const COMPOUND = new Set(["6/8", "9/8", "12/8"]);
const TWIN = Object.freeze({ "4/4": "12/8", "3/4": "9/8", "2/4": "6/8", "12/8": "4/4", "9/8": "3/4", "6/8": "2/4" });
const SUB_BEAT = (compound) => 12;

const median = (a) => { if (!a.length) return NaN; const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
function pearson(x, y) {
  const n = x.length, mx = x.reduce((a, b) => a + b) / n, my = y.reduce((a, b) => a + b) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; }
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : 0;
}

// ------------------------------------------------------------------------------------------- meter state ---
export function createMeterState({ meter = "4/4", feel = "straight" } = {}) {
  let m = meter, f = feel;
  const dismissed = new Set();
  return {
    get: () => ({ meter: m, feel: f, dismissed: [...dismissed] }),
    setMeter(label) { if (label !== "free" && !SETTABLE_METERS.includes(label) && label !== "2/4") throw new Error(`unknown meter ${label}`); m = label; return m; },
    setFeel(x) { if (x !== "straight" && x !== "triplet") throw new Error(`unknown feel ${x}`); f = x; return f; },
    dismiss(key) { dismissed.add(key); },
    isDismissed: (key) => dismissed.has(key),
    serialize: () => JSON.stringify({ meter: m, feel: f, dismissed: [...dismissed] }),
  };
}

// ------------------------------------------------------------------------------------------ the scorer ---
const BEAT_T = [
  { K: 2, w: [1, 0], name: "2" }, { K: 3, w: [1, 0, 0], name: "3" }, { K: 4, w: [1, 0, 0.5, 0], name: "4" },
  { K: 6, w: [1, 0, 0, 0.6, 0, 0], name: "6:3+3", fast: true }, { K: 6, w: [1, 0, 0.4, 0, 0.4, 0], name: "6:2+2+2", fast: true },
];
const TATUM_T = {
  2: [{ K: 4, w: [1, 0, 0.3, 0], label: "2/4" }, { K: 6, w: [1, 0, 0.4, 0, 0.4, 0], label: "3/4" },
    { K: 8, w: [1, 0, 0.3, 0, 0.6, 0, 0.3, 0], label: "4/4" }, { K: 6, w: [1, 0, 0, 0.6, 0, 0], label: "6/8" },
    { K: 12, w: [1, 0, 0, 0.4, 0, 0, 0.7, 0, 0, 0.4, 0, 0], label: "12/8" }],
  3: [{ K: 6, w: [1, 0, 0, 0.6, 0, 0], label: "6/8" }, { K: 9, w: [1, 0, 0, 0.4, 0, 0, 0.4, 0, 0], label: "9/8" },
    { K: 12, w: [1, 0, 0, 0.4, 0, 0, 0.7, 0, 0, 0.4, 0, 0], label: "12/8" }],
};
const jaccardDist = (a, b) => { let inter = 0; b.forEach((x) => { if (a.has(x)) inter++; }); return 1 - inter / (a.size + b.size - inter); };

// beats: [{ t_ms, index }] ascending (the chosen agent's beats); groups: [{ t, s, low, pcs }] ascending; pedals: pedal
// downs [{ t_ms }]. -> { sub, scores: { label: R² with priors }, phases: { label: tatum phase }, best, tern } or null
export function scoreMeters({ beats, groups, pedals = [], params = {} }) {
  const c = { ...METER_PARAMS, ...params };
  const B = beats.slice(-c.meterBeats).map((b) => ({ t: b.t_ms, idx: b.index }));
  if (B.length < c.meterMinBeats) return null;
  const ibis = []; for (let i = 1; i < B.length; i++) ibis.push((B[i].t - B[i - 1].t) / Math.max(1, B[i].idx - B[i - 1].idx));
  const p = median(ibis), bpm = 60000 / p, inner = Math.max(c.innerMinMs, c.inner * p);
  const peds = pedals.filter((x) => x.down !== false).map((x) => ({ t: x.t_ms ?? x.t }));
  let gi = groups.length; while (gi > 0 && groups[gi - 1].t >= B[0].t - 0.1 * p) gi--;
  const G = groups.slice(gi).filter((g) => g.t < B[B.length - 1].t);
  // the subdivision grid (gridOf)
  let on = 0, h = 0, th = 0, k = 0;
  for (const g of G) {
    if (g.t < B[0].t) continue;
    while (k < B.length - 2 && B[k + 1].t <= g.t) k++;
    const ph = (g.t - B[k].t) / (B[k + 1].t - B[k].t);
    if (ph < 0.1 || ph > 0.9) on += g.s; else if (Math.abs(ph - 0.5) < 0.08) h += g.s; else if (Math.abs(ph - 1 / 3) < 0.06 || Math.abs(ph - 2 / 3) < 0.06) th += g.s;
  }
  const sub = th > h && th > 0.25 * on ? 3 : h > 0.25 * on ? 2 : 1;
  const scores = {}, phases = {};
  const keep = (label, sc, ph) => { if (scores[label] == null || sc > scores[label]) { scores[label] = sc; phases[label] = ph; } };
  let tern = 0;
  if (sub === 1) {
    // beat-level accents (meterOf)
    const acc = [], spans = [];
    let offW2 = 0, offW3 = 0, gj = 0;
    for (let q = 0; q < B.length - 1; q++) {
      const lo = B[q].t - 0.1 * p, hi = B[q + 1].t - 0.1 * p, pcs = new Set();
      let sHit = 0, bass = 0;
      while (gj < G.length && G[gj].t < lo) gj++;
      for (let j = gj; j < G.length && G[j].t < hi; j++) {
        const g = G[j]; g.pcs.forEach((x) => pcs.add(x));
        const ph = (g.t - B[q].t) / (B[q + 1].t - B[q].t);
        if (Math.abs(g.t - B[q].t) <= inner) { sHit = Math.max(sHit, g.s); if (g.low <= 55) bass = 1; }
        else { if (Math.abs(ph - 0.5) < 0.08) offW2 += g.s; if (Math.abs(ph - 1 / 3) < 0.06 || Math.abs(ph - 2 / 3) < 0.06) offW3 += g.s; }
      }
      const prev = spans[q - 1];
      const harm = prev && prev.size && pcs.size ? jaccardDist(prev, pcs) : 0;
      spans.push(pcs);
      const ped = peds.some((x) => x.t >= B[q].t - 50 && x.t <= B[q].t + 0.45 * p) ? 1 : 0;
      acc.push({ idx: B[q].idx, v: sHit + c.accentBass * bass + c.accentHarm * harm + c.accentPedal * ped });
    }
    tern = offW3 + offW2 > 0 ? offW3 / (offW3 + offW2) : 0;
    const compound = tern > 0.6, seq = acc.map((x) => x.v);
    for (const T of BEAT_T) {
      if (T.fast && bpm < c.fastBpm) continue;
      if (acc.length < 2 * T.K) continue;
      const label = T.name === "6:3+3" ? "6/8" : T.name === "6:2+2+2" ? "3/4" : compound ? { 2: "6/8", 3: "9/8", 4: "12/8" }[T.K] : { 2: "2/4", 3: "3/4", 4: "4/4" }[T.K];
      for (let ph = 0; ph < T.K; ph++) {
        const r = pearson(acc.map((x) => T.w[(((x.idx - ph) % T.K) + T.K) % T.K]), seq);
        if (r <= 0) continue;
        keep(label, r * r + (T.name === "4" ? c.bonus44 : 0), ph);
      }
    }
  } else {
    // tatum-level accents (meterTatum)
    tern = th / (h + th || 1);
    const tat = [];
    for (let i = 0; i < B.length - 1; i++) for (let j = 0; j < sub; j++) tat.push({ t: B[i].t + (j / sub) * (B[i + 1].t - B[i].t), idx: B[i].idx * sub + j, len: (B[i + 1].t - B[i].t) / sub, v: 0 });
    const GT = G.filter((g) => g.t >= B[0].t);
    const lowAround = (t) => { let m = 999; for (const g of GT) if (Math.abs(g.t - t) <= 800) m = Math.min(m, g.low); return m; };
    let q = 0;
    for (const g of GT) {
      while (q < tat.length - 1 && tat[q + 1].t <= g.t) q++;
      let best = null;
      for (const x of [tat[q], tat[q + 1]]) if (x && Math.abs(g.t - x.t) <= Math.max(40, 0.25 * x.len) && (!best || Math.abs(g.t - x.t) < Math.abs(g.t - best.t))) best = x;
      if (!best) continue;
      let v = g.s; if (g.low <= 55 && g.low <= lowAround(g.t)) v += c.accentBass;
      const pre = new Set(), post = new Set();
      for (const h2 of GT) { if (h2.t >= g.t - 600 && h2.t < g.t) h2.pcs.forEach((x) => pre.add(x)); if (h2.t >= g.t && h2.t < g.t + 600) h2.pcs.forEach((x) => post.add(x)); }
      if (pre.size && post.size) v += c.accentHarm * jaccardDist(pre, post);
      best.v = Math.max(best.v, v);
    }
    for (const x of peds) { if (x.t < tat[0].t) continue; let bi = null; for (const y of tat) { if (y.t > x.t) break; if (x.t - y.t <= 300) bi = y; } if (bi) bi.v += c.accentPedal; }
    const seq = tat.map((x) => x.v);
    for (const T of TATUM_T[sub]) {
      if (tat.length < 2 * T.K) continue;
      for (let ph = 0; ph < T.K; ph++) {
        const r = pearson(tat.map((x) => T.w[(((x.idx - ph) % T.K) + T.K) % T.K]), seq);
        if (r <= 0) continue;
        keep(T.label, r * r + (T.label === "4/4" ? c.bonus44 : 0) + (T.label === "6/8" ? c.bonus68 : 0) - (T.K === 12 ? c.pen12 : 0), ph);
      }
    }
  }
  let best = null;
  for (const [label, sc] of Object.entries(scores)) if (!best || sc > best.score) best = { label, score: sc };
  return { sub, scores, phases, best, tern, bpm };
}

// ------------------------------------------------------------------------------------------- the model ---
export function createMeterModel({ meter = "4/4", feel = "straight", params = {} } = {}) {
  const c = { ...METER_PARAMS, ...params };
  let cur = meter, fl = feel;
  let sec = -Infinity, candLabel = null, candN = 0, suggestion = null, n3 = 0, n2 = 0, chip = null, lastScores = null, decisions = 0;
  const dismissed = new Set(), chipBlock = { triplets: -Infinity, straight: -Infinity };
  const log = [];

  function decide(T, sample, beats, groups, pedals) {
    decisions++;
    const band = sample ? sample.mode : "free";
    const sc = beats && beats.length ? scoreMeters({ beats, groups, pedals, params: c }) : null;
    lastScores = sc;
    // meter suggestion
    let next = null;
    if (sc && cur !== "free" && band === "steady") {
      const curScore = sc.scores[cur] ?? sc.scores[TWIN[cur]] ?? 0;
      const excluded = new Set([cur, sc.scores[cur] == null ? TWIN[cur] : null]);
      let best = null;
      for (const label of SETTABLE_METERS) { if (excluded.has(label) || dismissed.has(label) || sc.scores[label] == null) continue; if (!best || sc.scores[label] > best.score) best = { label, score: sc.scores[label] }; }
      if (best && best.score - curScore >= c.suggestMargin) next = { label: best.label, margin: best.score - curScore };
    }
    if (next && next.label === candLabel) candN++; else { candLabel = next ? next.label : null; candN = next ? 1 : 0; }
    suggestion = next && candN >= c.suggestHold ? next : null;
    // subdivision chip
    const compoundMeter = cur === "6/8" || cur === "12/8";
    const okBand = band === "steady" || band === "loose";
    let vote3 = false, vote2 = false;
    if (okBand && !compoundMeter && cur !== "free") {
      if (c.chipRule === "tatum") {
        if (sc && sc.sub >= 2) {
          let cb = -Infinity, sb = -Infinity;
          for (const [label, v] of Object.entries(sc.scores)) { if (COMPOUND.has(label)) cb = Math.max(cb, v); else sb = Math.max(sb, v); }
          vote3 = sc.sub === 3 || cb - sb >= c.chipMargin;
          vote2 = sc.sub === 2 && sb - cb >= c.chipMargin;
        }
      } else {
        vote3 = sample && sample.subdivision === 3;
        vote2 = sample && sample.subdivision === 2;
      }
    }
    n3 = vote3 ? n3 + 1 : 0;
    n2 = vote2 ? n2 + 1 : 0;
    const kind = fl === "straight" && n3 >= c.chipHold ? "triplets" : fl === "triplet" && n2 >= c.chipHold ? "straight" : null;
    chip = kind && decisions >= chipBlock[kind] ? { kind, since: T } : null;
    if (chip && log.length && log[log.length - 1].kind === kind && log[log.length - 1].open) { /* still showing */ } else if (chip) log.push({ kind, T, open: true });
    if (!chip && log.length && log[log.length - 1].open) log[log.length - 1].open = false;
  }

  return {
    // sample: beat.js tick() output; beats: the chosen agent's beats [{ t_ms, index }]; groups; pedals [{ t_ms, down }]
    step({ T, sample = null, beats = [], groups = [], pedals = [] }) {
      const s = Math.floor(T / 1000);
      if (s > sec) { sec = s; decide(T, sample, beats, groups, pedals); }
      return { suggestion, chip, scores: lastScores };
    },
    setMeter(label) { cur = label; candLabel = null; candN = 0; suggestion = null; n3 = 0; n2 = 0; chip = null; },
    setFeel(x) { fl = x; n3 = 0; n2 = 0; chip = null; },
    dismissSuggestion(label) { dismissed.add(label); if (suggestion && suggestion.label === label) suggestion = null; candLabel = null; candN = 0; },
    dismissChip(kind) { chipBlock[kind] = decisions + c.chipHold; chip = null; },
    state: () => ({ meter: cur, feel: fl, suggestion, chip, chipLog: log.map((x) => ({ ...x })), decisions }),
  };
}

// ------------------------------------------------------------------------------------ bar phase (rung 4) ---
// The inferred rung's phase scorer (moved unchanged from the LS2 stand-in in index.js): over the last phaseBeats tactus
// beats, each beat's accent is its strongest onset salience within max(60 ms, 0.18 P), +0.7 when that onset holds a new
// low bass (<= G3, lowest within ±0.8 s), +1.2 × the pitch-class Jaccard distance of 0.6 s before against after, +0.8 when
// a pedal down follows within 0.3 s. -> { phase, margin, mean } or null before 2 bars of beats.
export function inferPhase({ K, jK, tactusTime, groups, pedals, phaseBeats = 32 }) {
  if (jK < 2 * K) return null;
  const j0 = Math.max(0, jK - phaseBeats), tStart = tactusTime(j0) - 900;
  let gi = groups.length; while (gi > 0 && groups[gi - 1].t >= tStart) gi--;
  const G = groups.slice(gi), peds = pedals.filter((p) => p.down && p.t_ms >= tStart);
  const acc = new Array(K).fill(0), cnt = new Array(K).fill(0);
  for (let j = j0; j <= jK; j++) {
    const tb = tactusTime(j), Pj = tactusTime(j + 1) - tb, win = Math.max(60, 0.18 * Pj);
    let sal = 0, low = 999, lowAround = 999;
    const pre = new Set(), post = new Set();
    for (const g of G) {
      const d = g.t - tb;
      if (Math.abs(d) <= win) { sal = Math.max(sal, g.s); low = Math.min(low, g.low); }
      if (Math.abs(d) <= 800) lowAround = Math.min(lowAround, g.low);
      if (d >= -600 && d < -win) g.pcs.forEach((x) => pre.add(x));
      else if (d >= -win && d < 600) g.pcs.forEach((x) => post.add(x));
    }
    let v = sal;
    if (low <= 55 && low <= lowAround) v += 0.7;
    if (pre.size && post.size) { let inter = 0; post.forEach((x) => { if (pre.has(x)) inter++; }); v += 1.2 * (1 - inter / (pre.size + post.size - inter)); }
    if (peds.some((p) => p.t_ms >= tb && p.t_ms <= tb + 300)) v += 0.8;
    const ph = ((j % K) + K) % K;
    acc[ph] += v; cnt[ph]++;
  }
  const means = acc.map((a, k) => (cnt[k] ? a / cnt[k] : 0));
  let best = 0;
  for (let k = 1; k < K; k++) if (means[k] > means[best]) best = k;
  const others = means.filter((_, k) => k !== best);
  const mo = others.length ? others.reduce((a, b) => a + b, 0) / others.length : 0;
  return { phase: best, margin: means[best] - mo, mean: means.reduce((a, b) => a + b, 0) / K };
}

// --------------------------------------------------------------------------------------------- pickups ---
// bar: a built measure { bar (index inside its segment), beats, barTicks, voices: [{ notes: [{ pos }] }] } of a segment;
// meter: { tactus, beatTicks, compound }. -> { pickup: { implicit, ticks, subBeats, offset } } for a segment's partial
// first bar, { partial: true } for a partial bar later in a segment, else {}.
export function pickupOf(bar, meter, { firstOfSegment = bar.bar === 0 } = {}) {
  const full = meter.tactus * meter.beatTicks;
  if (bar.barTicks == null || bar.barTicks >= full) return {};
  if (!firstOfSegment) return { partial: true };
  const sb = SUB_BEAT(meter.compound);
  let first = Infinity;
  for (const v of bar.voices || []) for (const n of v.notes) if (!n.tieStop) first = Math.min(first, n.pos);
  if (!Number.isFinite(first)) return { partial: true };
  const offset = Math.floor(first / sb) * sb, ticks = bar.barTicks - offset;
  return { pickup: { implicit: true, ticks, subBeats: ticks / sb, offset } };
}

// ------------------------------------------------------------------------------------------ the header ---
export function createHeaderModel(params = {}) {
  const c = { ...METER_PARAMS, ...params };
  let pending = null, lastValue = null;
  const within = (a, b) => a != null && b != null && Math.abs(a / b - 1) <= c.confirmTol;
  return {
    // a family press at T; sample: the last tick's beat.js output (the value on display before the press)
    press(ratio, T, sample) {
      const shownBefore = sample ? (sample.bpmShown ?? sample.bpm ?? lastValue) : lastValue;
      pending = { ratio, T, want: shownBefore != null ? shownBefore * ratio : null };
    },
    // -> { bpm (integer or null before any readout), dim, word, requested (the press being covered, or null), confirmed }
    step(sample, T) {
      const s = sample || {};
      let out = null, confirmed = false;
      if (pending) {
        const letGo = s.levelBpm == null && T > pending.T;
        const req = s.levelBpm ?? pending.want;
        if (letGo) pending = null;
        else if (s.bpmShown != null && req != null && within(s.bpmShown, req)) { pending = null; confirmed = true; }
        else {
          const v = req != null ? Math.round(req) : lastValue;
          out = { bpm: v, dim: true, word: "hold", requested: req };
        }
      }
      if (!out) {
        if (s.mode === "hold") out = { bpm: s.bpmShown ?? lastValue, dim: true, word: "hold", requested: null };
        else out = { bpm: s.bpmShown ?? null, dim: false, word: s.mode ?? "free", requested: null };
      }
      if (out.bpm != null) lastValue = out.bpm;
      return { ...out, confirmed };
    },
    pending: () => (pending ? { ...pending } : null),
  };
}
