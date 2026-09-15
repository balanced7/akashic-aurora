// Per-beat rhythm for live sheet music: arsenal/web/piano/score/quantize.js (pure ES module: no DOM, no clock).
// Stage T3 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (sections 3 and 6.4), amended by
// plan-amendments.md C2 (the alphabet {1, 2, 3, 4, 6}, λ6 = 1.75, the compound set, div8, loose export on the d = 6
// grid) and C11 (feel). Times are ms; positions are ticks, TPQ 24 (a simple beat is 24 ticks, a compound beat 36).
//
//   const slots = assignBeats(groupTimes, beatTimes);          // [{ bb, f } | null]: the beat each onset group sits in
//   const q = createLiveQuantizer({ beatTicks: 24, beatsPerBar: 4 });
//   q.decide(bb, [{ f, t }...], periodMs) -> { d, ks, cost, loose, ... }   // greedy and causal, beat by beat
//   cleanDivisions(beats, { ... })                             // Viterbi over divisions with the bar-back prior, twice
//
// Cost of division d for a beat with period P, onset fractions f and timing spread σ (plan 6.4, unchanged by C2):
//   C(d) = Σ ((f − k/d)·P)² / 2σ²  +  λ[d]  +  0.8·[d ≠ previous non-empty beat]  +  0.8·[d ≠ same beat one bar back]
//          +  6·collisions,   k = round(f·d) clamped to 0..d−1
//   σ₀ 40 ms, EMA 0.05 of squared residuals after each beat, clamped 15-60 ms; f > 0.875 belongs to the next beat.
// λ tables (C2; the order is fixed, values are start values):
//   simple, feel straight   1: 0, 2: 0.5, 4: 1.5, 6: 1.75, 3: 2.0
//   simple, feel triplet    1: 0, 3: 0.5, 6: 1.5, 2: 1.75, 4: 2.0
//   compound (36-tick beat) 1: 0, 3: 0.5, 6: 1.5, 2: 1.75           (feel is ignored)
//   s3Compat                1: 0, 2: 0.5, 4: 1.5, 3: 2.0            in every meter, 12/8 included, as section 3 ran
// div8 (32nds, simple meters only) is off by default; lambda8 is its start value when a run turns it on.
// The d = 6 gate (ls1-rulings.md LS2 rulings, 2026-09-15; plan-amendments.md section 5): in simple meters, both feels,
// d = 6 is a candidate only on a beat holding at least d6MinGroups (5) onset groups. C2 as written (d6MinGroups 0) failed
// LR4a-e and the false d = 6 row: the d = 6 grid holds every d = 3 slot at a lower straight λ, so triplets were priced
// at λ6 and the slots only d = 6 has (1/6, 5/6) picked up jittered 16ths and 8ths. Compound and s3Compat sets are ungated.
// Divisions are tried in λ order and the first of equal costs wins, as the section 3 run did. `div` in a decision is the
// normalized division (the smallest one holding the chosen positions), which is what notation and the receipts read.
//
// Loose beats (plan 6.4, C2): the best cost is above looseCost (12), not counting the penalty of collisions T1 explains,
// or the best division still has a collision that T1 cannot explain. A collision is explained when the two groups start within looseCollisionMs (120 ms, the roll span) of
// each other (a chord or roll T1 left split), or one of them is a grace candidate. Live, a loose beat keeps its
// decided positions and is drawn proportionally; the clean copy places its groups with looseSlots() on the beat's d = 6
// grid (time order, least total displacement, closest pair merged first when there are more than 6).

export const QUANTIZE_API = "arsenal.piano.score.quantize/v0";
export const TPQ = 24;

export const QUANT_PARAMS = Object.freeze({
  sigma0Ms: 40, sigmaMinMs: 15, sigmaMaxMs: 60, emaWeight: 0.05, adapt: true,
  continuity: 0.8, barBack: 0.8, collision: 6, nextBeat: 0.875,
  looseCost: 12, looseCollisionMs: 120,
  div8: false, lambda8: 2.5, s3Compat: false,
  // lambdas overrides a table ({ straight: [[d, λ]...], ... }), a measurement hook. d6MinGroups: in simple meters d = 6
  // is a candidate only on beats with at least that many onset groups (ls1-rulings.md LS2 rulings, 2026-09-15: 5 is the
  // default; 0 is C2 as written, where d = 6 competes on every beat)
  lambdas: null, d6MinGroups: 5,
});

export const LAMBDAS = Object.freeze({
  straight: Object.freeze([[1, 0], [2, 0.5], [4, 1.5], [6, 1.75], [3, 2.0]]),
  triplet: Object.freeze([[1, 0], [3, 0.5], [6, 1.5], [2, 1.75], [4, 2.0]]),
  compound: Object.freeze([[1, 0], [3, 0.5], [6, 1.5], [2, 1.75]]),
  s3: Object.freeze([[1, 0], [2, 0.5], [4, 1.5], [3, 2.0]]),
});

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

// The ordered division set for a beat: [{ d, lambda }].
export function divisionSet({ compound = false, feel = "straight", div8 = false, lambda8 = QUANT_PARAMS.lambda8, s3Compat = false, lambdas = null, d6MinGroups = QUANT_PARAMS.d6MinGroups } = {}) {
  const name = s3Compat ? "s3" : compound ? "compound" : feel === "triplet" ? "triplet" : "straight";
  const table = (lambdas && lambdas[name]) || LAMBDAS[name];
  const simple = !compound && !s3Compat;
  const set = table.map(([d, lambda]) => ({ d, lambda, minGroups: simple && d === 6 ? d6MinGroups : 0 }));
  if (div8 && simple) set.push({ d: 8, lambda: lambda8, minGroups: 0 });
  return set;
}
const setOf = (c, compound, feel) => divisionSet({ compound, feel, div8: c.div8, lambda8: c.lambda8, s3Compat: c.s3Compat, lambdas: c.lambdas, d6MinGroups: c.d6MinGroups });

// The smallest division of a beat holding every position (ticks within the beat), from the notation alphabet.
const NORM_DIVS = [1, 2, 3, 4, 6, 8, 12];
export function normalizedDivision(positions, beatTicks) {
  for (const d of NORM_DIVS) {
    if (beatTicks % d) continue;
    const step = beatTicks / d;
    if (positions.every((p) => p % step === 0)) return d;
  }
  return beatTicks;
}

// The beat each onset sits in (the section 3 run's assign, in ms). times ascending; beats ascending.
export function assignBeats(times, beats, { nextBeat = QUANT_PARAMS.nextBeat } = {}) {
  const out = new Array(times.length).fill(null);
  if (beats.length < 3) return out;
  let b = 0;
  for (let i = 0; i < times.length; i++) {
    const t = times[i];
    if (t < beats[0] - (1 - nextBeat) * (beats[1] - beats[0]) || t >= beats[beats.length - 1]) continue;
    while (b + 1 < beats.length && beats[b + 1] <= t) b++;
    let bb = t < beats[0] ? 0 : b;
    if (bb + 1 >= beats.length) continue;
    let f = (t - beats[bb]) / (beats[bb + 1] - beats[bb]);
    if (f > nextBeat) {
      if (bb + 2 >= beats.length) continue;
      bb++;
      f = (t - beats[bb]) / (beats[bb + 1] - beats[bb]);
    }
    out[i] = { bb, f };
  }
  return out;
}

function fitOf(items, P, d, sigma) {
  let fit = 0, coll = 0;
  const used = new Map(), ks = [], pairs = [];
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    const k = clamp(Math.round(it.f * d), 0, d - 1), e = (it.f - k / d) * P;
    fit += e * e / (2 * sigma * sigma);
    if (used.has(k)) { coll++; pairs.push([used.get(k), i]); }
    else used.set(k, i);
    ks.push(k);
  }
  return { fit, coll, ks, pairs };
}

function unexplainedOf(items, pairs, c) {
  let n = 0;
  for (const [a, b] of pairs) {
    const ia = items[a], ib = items[b];
    const near = ia.t != null && ib.t != null && Math.abs(ib.t - ia.t) <= c.looseCollisionMs;
    if (!(near || ia.grace || ib.grace)) n++;
  }
  return n;
}

// One beat. items: [{ f, t?, grace? }] in time order; P: the beat period (ms); ctx: { set, sigma, prev, back, params }.
export function divideBeat(items, P, ctx) {
  const c = ctx.params || QUANT_PARAMS;
  const { set, sigma } = ctx, prev = ctx.prev ?? null, back = ctx.back ?? null;
  let best = null, second = null;
  for (const { d, lambda, minGroups } of set) {
    if (minGroups && items.length < minGroups) continue;
    const r = fitOf(items, P, d, sigma);
    let cost = r.fit + lambda + r.coll * c.collision;
    if (prev != null && d !== prev) cost += c.continuity;
    if (back != null && d !== back) cost += c.barBack;
    const row = { d, cost, ks: r.ks, fit: r.fit, coll: r.coll, pairs: r.pairs };
    if (!best || cost < best.cost) { second = best; best = row; }
    else if (!second || cost < second.cost) second = row;
  }
  const unexplained = unexplainedOf(items, best.pairs, c);
  // an explained collision's penalty is not evidence against the rhythm: it does not count toward the loose ceiling
  const loose = best.cost - (best.coll - unexplained) * c.collision > c.looseCost || unexplained > 0;
  return { d: best.d, ks: best.ks, cost: best.cost, fit: best.fit, collisions: best.coll, loose, runnerUp: second ? { d: second.d, cost: second.cost } : null };
}

// Slots on a d-slot grid for a loose beat's groups (C2 export): time order kept, distinct slots, least total
// displacement |f·d − k|; with more than d groups the closest pair (in f) merges first, repeatedly. fs ascending.
export function looseSlots(fs, d = 6) {
  const n = fs.length;
  if (!n) return [];
  let clusters = fs.map((f, i) => ({ f, members: [i] }));
  while (clusters.length > d) {
    let bi = 0, bd = Infinity;
    for (let i = 0; i + 1 < clusters.length; i++) { const g = clusters[i + 1].f - clusters[i].f; if (g < bd) { bd = g; bi = i; } }
    const a = clusters[bi], b = clusters[bi + 1];
    const m = [...a.members, ...b.members];
    clusters.splice(bi, 2, { f: m.reduce((s, i) => s + fs[i], 0) / m.length, members: m });
  }
  const m = clusters.length, x = clusters.map((cl) => clamp(cl.f, 0, 1) * d);
  // DP: cost[i][k] = least displacement placing clusters 0..i with cluster i at slot k (strictly increasing slots)
  const cost = Array.from({ length: m }, () => new Array(d).fill(Infinity)), from = Array.from({ length: m }, () => new Array(d).fill(-1));
  for (let k = 0; k < d; k++) cost[0][k] = Math.abs(x[0] - k);
  for (let i = 1; i < m; i++) {
    let run = Infinity, arg = -1;
    for (let k = 1; k < d; k++) {
      if (cost[i - 1][k - 1] < run) { run = cost[i - 1][k - 1]; arg = k - 1; }
      if (run < Infinity) { cost[i][k] = run + Math.abs(x[i] - k); from[i][k] = arg; }
    }
  }
  let k = 0;
  for (let j = 1; j < d; j++) if (cost[m - 1][j] < cost[m - 1][k]) k = j;
  const out = new Array(n);
  for (let i = m - 1; i >= 0; i--) { for (const idx of clusters[i].members) out[idx] = k; k = from[i][k]; }
  return out;
}

// Greedy causal quantizer (the section 3 "live" pass). Beats are decided in increasing bb; rewind(bb) drops the
// decisions from bb on and restores σ and the previous division, so a transcriber can re-decide unsettled beats when
// their beat times move, and the final result equals one pass over the final beat times.
export function createLiveQuantizer({ params = {}, beatTicks = TPQ, beatsPerBar = 4, compound = false, feel = "straight" } = {}) {
  const c = { ...QUANT_PARAMS, ...params };
  const set = setOf(c, compound, feel);
  const s2Init = c.sigma0Ms * c.sigma0Ms, s2Min = c.sigmaMinMs * c.sigmaMinMs, s2Max = c.sigmaMaxMs * c.sigmaMaxMs;
  let s2 = s2Init, prev = null;
  const dec = new Map();
  let order = [];

  function decide(bb, items, P) {
    if (order.length && bb <= order[order.length - 1]) rewind(bb);
    const sigma = c.adapt ? Math.sqrt(s2) : c.sigma0Ms;
    const backDec = dec.get(bb - beatsPerBar);
    const r = divideBeat(items, P, { set, sigma, prev, back: backDec ? backDec.d : null, params: c });
    prev = r.d;
    const w = c.emaWeight;
    for (let i = 0; i < items.length; i++) { const e = (items[i].f - r.ks[i] / r.d) * P; s2 = (1 - w) * s2 + w * e * e; }
    s2 = clamp(s2, s2Min, s2Max);
    const step = beatTicks / r.d;
    const pos = r.ks.map((k) => k * step);
    const out = { ...r, bb, P, sigma, pos, div: normalizedDivision(pos, beatTicks), s2After: s2, prevAfter: prev };
    dec.set(bb, out); order.push(bb);
    return out;
  }
  function rewind(bb) {
    let cut = order.length;
    while (cut > 0 && order[cut - 1] >= bb) { cut--; dec.delete(order[cut]); }
    order = order.slice(0, cut);
    const last = cut ? dec.get(order[cut - 1]) : null;
    s2 = last ? last.s2After : s2Init;
    prev = last ? last.prevAfter : null;
  }
  return {
    decide, rewind,
    decision: (bb) => dec.get(bb) || null,
    divisions: () => new Map(order.map((bb) => [bb, dec.get(bb).d])),
    sigma: () => Math.sqrt(s2),
    set: () => set.slice(),
    params: () => ({ ...c }),
  };
}

// Viterbi over divisions (the section 3 "clean" pass), run `passes` times with the bar-back prior from the previous
// pass (first: liveDiv). beats: [{ bb, items, P }] in increasing bb (non-empty beats only). Returns Map bb -> decision.
export function cleanDivisions(beats, { params = {}, beatTicks = TPQ, beatsPerBar = 4, compound = false, feel = "straight", liveDiv = new Map(), sigma = QUANT_PARAMS.sigma0Ms, passes = 2 } = {}) {
  const c = { ...QUANT_PARAMS, ...params };
  const set = setOf(c, compound, feel);
  const out = new Map();
  if (!beats.length) return out;
  let backDiv = liveDiv;
  for (let pass = 0; pass < passes; pass++) {
    const V = [];
    beats.forEach((bt, i) => {
      const back = backDiv.get(bt.bb - beatsPerBar), row = new Map();
      for (const { d, lambda, minGroups } of set) {
        const r = fitOf(bt.items, bt.P, d, sigma);
        const gated = minGroups && bt.items.length < minGroups;
        const e = gated ? Infinity : (r.fit + lambda + r.coll * c.collision) + (back != null && d !== back ? c.barBack : 0);
        let from = null, bp = 0;
        if (i > 0) {
          bp = Infinity;
          for (const { d: pd } of set) { const v = V[i - 1].get(pd).cost + (pd !== d ? c.continuity : 0); if (v < bp) { bp = v; from = pd; } }
        }
        row.set(d, { cost: e + bp, from, ks: r.ks, fit: r.fit, coll: r.coll, pairs: r.pairs, local: e });
      }
      V.push(row);
    });
    const nd = new Map();
    const last = V[V.length - 1];
    let d = set.reduce((m, x) => (last.get(x.d).cost < last.get(m).cost ? x.d : m), set[0].d);
    for (let i = beats.length - 1; i >= 0; i--) {
      const cell = V[i].get(d), bt = beats[i], step = beatTicks / d, pos = cell.ks.map((k) => k * step);
      const unexplained = unexplainedOf(bt.items, cell.pairs, c);
      nd.set(bt.bb, d);
      out.set(bt.bb, { bb: bt.bb, d, ks: cell.ks, pos, div: normalizedDivision(pos, beatTicks), cost: cell.local, collisions: cell.coll, loose: cell.local - (cell.coll - unexplained) * c.collision > c.looseCost || unexplained > 0, P: bt.P });
      d = cell.from ?? d;
    }
    backDiv = nd;
  }
  return out;
}

// Positions (ticks within the beat) for a clean-copy beat: the decided ones, or looseSlots on the d = 6 grid when the
// beat is loose (C2 export).
export function exportPositions(decision, items, beatTicks = TPQ) {
  if (!decision.loose) return decision.pos.slice();
  const d = 6, step = beatTicks / d;
  return looseSlots(items.map((it) => it.f), d).map((k) => k * step);
}
