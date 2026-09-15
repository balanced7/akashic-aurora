// The section 3 quantizer exactly as it ran: tests/fixtures/score/s3ref.mjs (slice LS0, frozen reference).
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md section 3 (scratch quant.mjs), moved
// unchanged so the section 3 tables reproduce under LR1 and LS2's quantize.js has a fixed oracle for its s3Compat
// mode (plan-amendments.md C2: DIVS {1, 2, 4, 3} for every meter, 12/8 included). Not product code: the amended
// alphabet, feel and loose export land in arsenal/web/piano/score/quantize.js. Times in seconds, positions in twelfths
// of a beat, as the run used them.
import { rng, gauss } from "./gen.mjs";
import { scoreS3, mean } from "./metrics.mjs";

export const S3_OPTIONS = Object.freeze({ sigma0: 0.04, adapt: true, lp: 0.8, lbar: 0.8, COLL: 6 });
export const S3_NO_PRIORS = Object.freeze({ ...S3_OPTIONS, lp: 0, lbar: 0 });
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

// T1 grouping of the run: 40 ms chords plus the near-chord rule (<= 60 ms, register gap >= 7)
export function groupsOf(notes, mergeMs = 40, nearMs = 60) {
  const gs = [];
  for (const n of notes) {
    const g = gs[gs.length - 1];
    const join = g && (n.t - g.t <= mergeMs / 1000 || (n.t - g.t <= nearMs / 1000 && (n.note >= g.hi + 7 || n.note <= g.lo - 7)));
    if (join) { g.notes.push(n); g.hi = Math.max(g.hi, n.note); g.lo = Math.min(g.lo, n.note); if (n.pos !== g.pos) g.mixed = true; }
    else gs.push({ t: n.t, notes: [n], hi: n.note, lo: n.note, pos: n.pos, mixed: false });
  }
  return gs;
}

export function assign(gs, beats) {
  let b = 0;
  for (const g of gs) {
    g.bb = null;
    if (beats.length < 3 || g.t < beats[0] - 0.125 * (beats[1] - beats[0]) || g.t >= beats[beats.length - 1]) continue;
    while (b + 1 < beats.length && beats[b + 1] <= g.t) b++;
    const bb0 = g.t < beats[0] ? 0 : b;
    let bb = bb0;
    if (bb + 1 >= beats.length) continue;
    let f = (g.t - beats[bb]) / (beats[bb + 1] - beats[bb]);
    if (f > 0.875) { if (bb + 2 >= beats.length) continue; bb++; f = (g.t - beats[bb]) / (beats[bb + 1] - beats[bb]); }
    g.bb = bb; g.f = f;
  }
}

const LAM = { 1: 0, 2: 0.5, 4: 1.5, 3: 2.0 };
const DIVS = [1, 2, 4, 3];
function beatCost(its, Pms, d, sigma, COLL) {
  let fit = 0, coll = 0; const used = new Set(), ks = [];
  for (const it of its) {
    const k = clamp(Math.round(it.f * d), 0, d - 1), e = (it.f - k / d) * Pms;
    fit += e * e / (2 * sigma * sigma); if (used.has(k)) coll++; used.add(k); ks.push(k);
  }
  return { cost: fit + LAM[d] + coll * COLL, ks };
}
const byBeatOf = (gs) => { const m = new Map(); for (const g of gs) if (g.bb != null) { if (!m.has(g.bb)) m.set(g.bb, []); m.get(g.bb).push(g); } return m; };

export function quantLive(gs, beats, bpb, o) {
  const byBeat = byBeatOf(gs), div = new Map(); let prev = null, s2 = o.sigma0 ** 2;
  for (const bb of [...byBeat.keys()].sort((a, b) => a - b)) {
    const its = byBeat.get(bb), Pms = beats[bb + 1] - beats[bb], back = div.get(bb - bpb);
    const sigma = o.adapt ? Math.sqrt(s2) : o.sigma0;
    let best = null;
    for (const d of DIVS) {
      const c = beatCost(its, Pms, d, sigma, o.COLL);
      let cost = c.cost; if (prev != null && d !== prev) cost += o.lp; if (back != null && d !== back) cost += o.lbar;
      if (!best || cost < best.cost) best = { d, cost, ks: c.ks };
    }
    div.set(bb, best.d); prev = best.d;
    its.forEach((g, i) => { g.live = bb * 12 + best.ks[i] * 12 / best.d; const e = (g.f - best.ks[i] / best.d) * Pms; s2 = 0.95 * s2 + 0.05 * e * e; });
    s2 = clamp(s2, 0.015 ** 2, 0.06 ** 2);
  }
  return { div, sigma: Math.sqrt(s2) };
}

export function quantClean(gs, beats, bpb, o, liveDiv, sigma) {
  const byBeat = byBeatOf(gs), keys = [...byBeat.keys()].sort((a, b) => a - b);
  if (!keys.length) return;
  let backDiv = liveDiv;
  for (let iter = 0; iter < 2; iter++) {
    const V = [];
    keys.forEach((bb, i) => {
      const its = byBeat.get(bb), Pms = beats[bb + 1] - beats[bb], back = backDiv.get(bb - bpb), row = {};
      for (const d of DIVS) {
        const c = beatCost(its, Pms, d, sigma, o.COLL), e = c.cost + (back != null && d !== back ? o.lbar : 0);
        let from = null, bp = 0;
        if (i > 0) { bp = Infinity; for (const pd of DIVS) { const v = V[i - 1][pd].cost + (pd !== d ? o.lp : 0); if (v < bp) { bp = v; from = pd; } } }
        row[d] = { cost: e + bp, from, ks: c.ks };
      }
      V.push(row);
    });
    const nd = new Map(); const last = V[V.length - 1];
    let d = DIVS.reduce((m, x) => (last[x].cost < last[m].cost ? x : m), 1);
    for (let i = keys.length - 1; i >= 0; i--) {
      nd.set(keys[i], d); const ks = V[i][d].ks;
      byBeat.get(keys[i]).forEach((g, j) => (g.clean = keys[i] * 12 + ks[j] * 12 / d));
      d = V[i][d].from ?? d;
    }
    backDiv = nd;
  }
}

export function naive(gs) { const S = [0, 3, 4, 6, 8, 9, 12]; for (const g of gs) if (g.bb != null) { const x = g.f * 12; const k = S.reduce((m, s) => (Math.abs(s - x) < Math.abs(m - x) ? s : m), 0); g.naive = g.bb * 12 + k; } }

// One piece under every beat source of the run. inferredBeats(piece) -> lag-2 settled beat times in seconds, or null.
export function runPiece(pc, { seed, inferredBeats = null }) {
  const out = {};
  let gs = groupsOf(pc.notes); assign(gs, pc.beats); naive(gs);
  out.mixedShare = gs.filter((g) => g.mixed).length / gs.length;
  quantLive(gs, pc.beats, pc.bpb, S3_NO_PRIORS); out.oNoPrior = scoreS3(gs, "live", pc.bpb);
  const t0 = performance.now();
  const L = quantLive(gs, pc.beats, pc.bpb, S3_OPTIONS);
  const t1 = performance.now();
  out.oLive = scoreS3(gs, "live", pc.bpb);
  quantClean(gs, pc.beats, pc.bpb, S3_OPTIONS, L.div, L.sigma);
  const t2 = performance.now();
  out.oClean = scoreS3(gs, "clean", pc.bpb); out.oNaive = scoreS3(gs, "naive", pc.bpb);
  out.churn = mean(gs.filter((g) => g.bb != null && g.t >= 5).map((g) => +(g.live !== g.clean)));
  out.msPerBarLive = (t1 - t0) / pc.bars; out.msPerBarClean = (t2 - t1) / pc.bars;
  for (const [name, e] of [["t30", 0.03], ["t45", 0.045]]) {
    const r = rng(seed + 99), noisy = pc.beats.map((t) => t + e * gauss(r));
    for (let i = 1; i < noisy.length; i++) if (noisy[i] <= noisy[i - 1] + 0.05) noisy[i] = noisy[i - 1] + 0.05;
    gs = groupsOf(pc.notes); assign(gs, noisy);
    const Lt = quantLive(gs, noisy, pc.bpb, S3_OPTIONS); out[name + "Live"] = scoreS3(gs, "live", pc.bpb);
    quantClean(gs, noisy, pc.bpb, S3_OPTIONS, Lt.div, Lt.sigma); out[name + "Clean"] = scoreS3(gs, "clean", pc.bpb);
  }
  if (inferredBeats) {
    const raw = inferredBeats(pc);
    const est = [...raw].sort((a, b) => a - b).filter((t, i, a) => i === 0 || t - a[i - 1] > 0.1);
    const trueIdx = est.map((t) => { let j = 0, bd = Infinity; pc.beats.forEach((b, k) => { const d = Math.abs(b - t); if (d < bd) { bd = d; j = k; } }); return bd <= 0.07 ? j : null; });
    gs = groupsOf(pc.notes); assign(gs, est);
    const mapPos = (v, g) => { const bb = g.bb; const a = trueIdx[bb], b = trueIdx[bb + 1]; if (a == null || b == null || b !== a + 1) return null; return a * 12 + (v - bb * 12); };
    const Li = quantLive(gs, est, pc.bpb, S3_OPTIONS); out.iLive = scoreS3(gs, "live", pc.bpb, 5, mapPos);
    quantClean(gs, est, pc.bpb, S3_OPTIONS, Li.div, Li.sigma); out.iClean = scoreS3(gs, "clean", pc.bpb, 5, mapPos);
    const iv = []; for (let i = 0; i + 1 < est.length; i++) if (est[i] >= 5) iv.push(trueIdx[i] != null && trueIdx[i + 1] === trueIdx[i] + 1);
    out.iIntervalsOk = mean(iv.map(Number));
  }
  return out;
}

export function aggregate(rows) {
  const line = { n: rows.length };
  for (const k of ["oNaive", "oNoPrior", "oLive", "oClean", "t30Live", "t30Clean", "t45Live", "t45Clean", "iLive", "iClean"]) {
    if (!rows[0][k]) continue;
    const f = (m) => mean(rows.map((r) => r[k] && r[k][m]));
    line[k] = { acc: f("acc"), cov: f("cov"), beat: f("beatOk"), bar: f("barOk") };
  }
  line.churn = mean(rows.map((r) => r.churn));
  return line;
}
