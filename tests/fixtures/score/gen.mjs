// Synthetic performances with ground truth for live sheet music: tests/fixtures/score/gen.mjs (slice LS0).
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md section 3 and 5.1, plan-amendments.md
// section 6 LS0. Zero dependencies, deterministic by seed, no session content: every note here is generated.
//
// Three generators:
// 1. genPiece / genFree: the tempo lane's generator (tempo-meter.md 4.2, scratch tracker.mjs), moved unchanged. Same
//    random draws in the same order, so its tables reproduce (LR1). Truth gains tick positions (TPQ 24), no new draws.
// 2. genScore: the section 3 quantizer run's generator (scratch quant.mjs), moved unchanged (s3Compat). Positions stay
//    in twelfths of a beat (pos) as the run scored them, plus tick (TPQ 24: x2 simple, x3 compound).
// 3. genTake: the amended families (plan-amendments.md LS0 checklist), with written durations, voices, staves, a pedal
//    model and sound ends, emitted as practice-log events (t_ms, kind on/off/pedal/sound_end, performance.py shape).
//
// genTake truth durations. Composition decides onset ticks, voices and each note's intended key release; the pedal
// model (a change per harmony, some dry harmonies, 30% of pedalled notes released at 20-60% of their length) decides
// the sound. The written duration is then the C1/C7 rule applied on the IDEAL performance (no jitter, no roll or bass
// lead): exact ticks and exact pedal times, so every case is far from a rule boundary. This is the fixture oracle for
// LR4h; measures.js (LS2) must reach the same answers from jittered events and estimated beats.
//   tol = one 16th of the beat (P/4 simple, P/6 compound) = 6 ticks either way.
//   pedal up from release to the next onset in the voice (C1 case 1): end = release, filled to the next onset when the
//     gap is under tol, snapped forward to the beat's division, capped at the bar end.
//   pedal down at release or pressed before the next onset (case 2): sound end >= next - tol -> min(next, bar end);
//     else the sound end snapped to the nearest slot (at least one slot after the onset), then a rest.
//   lowest voice of the lower staff (C7): end = min(sound end, next onset, bar end) with the case-1 fill; one bar-line tie
//     only when the next bar has no onset in that voice before its midpoint (end then capped at the next bar's end).
// A beat's division is the smallest d (1, 2, 3, 4, 6, 8, 12) holding every onset of the beat, all voices.

export const TPQ = 24;

export function rng(seed) { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
export function gauss(r) { let u = 0; while (u === 0) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const mix = (seed, k) => (Math.imul(seed >>> 0, 0x9E3779B1) ^ Math.imul(k + 1, 0x85EBCA77)) >>> 0;

// ============================================================================ 1. the tempo lane's generator ===
const LANE_METERS = { "4/4": { bpb: 4, sub: 2 }, "3/4": { bpb: 3, sub: 2 }, "6/8": { bpb: 2, sub: 3 } };

export function genPiece(meter, texture, rub, bpm, seed, o = {}) {
  const r = rng(seed), M = LANE_METERS[meter], bars = o.bars || 32, pickup = o.pickup ?? (r() < 0.5 ? 1 : 0);
  const nBeats = bars * M.bpb + pickup + 1, phrase = 4 * M.bpb;
  const beatTicks = M.sub === 3 ? 36 : 24;
  const nom = [], extra = [], ferm = []; let drift = 0;
  for (let k = 0; k < nBeats; k++) {
    const kb = k - pickup, pos = ((kb % phrase) + phrase) % phrase, x = pos / phrase;
    const bpmHere = o.jumpAtBar != null && kb >= o.jumpAtBar * M.bpb ? o.jumpBpm : bpm;
    let f = 1, ex = 0;
    if (rub === 1) { drift = clamp(drift + 0.01 * gauss(r), -0.06, 0.06); f = 1 + 0.04 * Math.sin(2 * Math.PI * x) + drift; if (pos === phrase - 1) f *= 1.15; }
    if (rub === 2) { drift = clamp(drift + 0.02 * gauss(r), -0.12, 0.12); f = 1 + 0.1 * Math.sin(2 * Math.PI * x) + drift; if (pos === phrase - 2) f *= 1.2; if (pos === phrase - 1) { f *= 1.5; if (r() < 0.4) ex = (1 + 1.5 * r()) * 60 / bpmHere; } }
    nom.push(60 / bpmHere * f); extra.push(ex); ferm.push(ex > 0);
  }
  const bt = [0.5]; for (let k = 0; k < nBeats; k++) bt.push(bt[k] + nom[k] + extra[k]);
  const tAt = (bp) => { const k = Math.floor(bp + 1e-9); return bt[k] + (bp - k) * nom[Math.min(k, nom.length - 1)]; };
  const sig = [0.01, 0.02, 0.03][rub];
  const notes = [], pedals = [];
  const add = (bp, note, vel, jitter = true, dt = 0) => notes.push({ t: tAt(bp) + dt + (jitter ? sig * gauss(r) : 0), note, vel: clamp(Math.round(vel + 6 * gauss(r)), 1, 127), beat: bp, tick: Math.round((bp - pickup) * beatTicks) });
  const ROOTS = [0, 9, 5, 7, 2, 4];
  for (let b = -1; b < bars; b++) {
    const k0 = pickup + b * M.bpb;
    if (b === -1) { if (pickup) { add(0, 76, 58); if (M.sub === 2 && r() < 0.5) add(0.5, 74, 55); if (M.sub === 3 && r() < 0.5) add(2 / 3, 74, 55); } continue; }
    const root = ROOTS[Math.floor(r() * 4)], minor = root === 9 || root === 2 || root === 4, bass = 36 + root, third = root + (minor ? 3 : 4), fifth = root + 7;
    const tri = [60 + root, 60 + third, 60 + fifth];
    const accOf = (j) => (j === 0 ? 12 : M.bpb === 4 && j === 2 ? 6 : 0);
    const tb = tAt(k0);
    pedals.push({ t: tb + 0.02, down: false }, { t: tb + 0.1 + 0.1 * r(), down: true });
    const roll = (bp, ns, vel) => { const rolled = r() < 0.6, sp = 0.02 + 0.05 * r(); ns.forEach((n, i) => add(bp, n, vel, i === 0, rolled ? (sp * i) / (ns.length - 1) : 0)); };
    if (texture === "ballad") {
      add(k0, bass, 72 + accOf(0)); if (M.bpb === 4 && r() < 0.5) add(k0 + 2, bass + 7, 62);
      roll(k0, tri, 58 + accOf(0));
      for (let j = 0; j < M.bpb; j++) {
        const pats = M.sub === 2 ? [[0], [0], [0, 0.5], [], [0.5]] : [[0], [0, 2 / 3], [0, 1 / 3, 2 / 3], []];
        const pat = j === 0 ? [0] : pats[Math.floor(r() * pats.length)];
        for (const f of pat) add(k0 + j + f, 72 + third + (Math.floor(r() * 3) - 1) * 2, 62 + accOf(j) * (f === 0 ? 1 : 0));
      }
    } else if (texture === "arp") {
      const cyc = [bass, bass + 7, bass + 12 + third, bass + 7];
      let q = 0;
      for (let j = 0; j < M.bpb; j++) for (let s = 0; s < M.sub; s++) { add(k0 + j + s / M.sub, cyc[q % 4], (s === 0 ? 60 + accOf(j) : 48)); q++; }
      add(k0, 72 + third, 66 + accOf(0));
      for (let j = 1; j < M.bpb; j++) if (r() < 0.6) add(k0 + j, 72 + (r() < 0.5 ? fifth : root) % 12 + 0, 62 + accOf(j));
    } else {
      add(k0, bass, 74 + accOf(0));
      if (M.sub === 3) { for (let j = 0; j < M.bpb; j++) { if (j) add(k0 + j, bass + 7, 64); for (const f of [1 / 3, 2 / 3]) roll(k0 + j + f, tri, 50); } }
      else if (M.bpb === 3) { roll(k0 + 1, tri, 52); roll(k0 + 2, tri, 52); add(k0, 72 + third, 66); }
      else { for (let j = 0; j < M.bpb; j++) { if (j === 2 && r() < 0.5) add(k0 + 2, bass + 7, 64); roll(k0 + j, tri, 56 + accOf(j)); } }
    }
  }
  notes.sort((a, b) => a.t - b.t);
  const truth = { beats: bt.slice(0, nBeats), nom, ferm, downs: [], meter, pickup, beatTicks, tpq: TPQ };
  for (let b = 0; b < bars; b++) truth.downs.push(bt[pickup + b * M.bpb]);
  truth.beats_ms = truth.beats.map((t) => t * 1000);
  truth.nom_ms = nom.map((t) => t * 1000);
  truth.downs_ms = truth.downs.map((t) => t * 1000);
  return { notes, pedals: pedals.sort((a, b) => a.t - b.t), truth };
}

export function genFree(seed, dur = 90) {
  const r = rng(seed), notes = [], pedals = []; let t = 0.5;
  while (t < dur) {
    const n = 1 + Math.floor(r() * 4), base = 40 + Math.floor(r() * 36);
    for (let i = 0; i < n; i++) notes.push({ t: t + 0.03 * r(), note: base + i * 4, vel: 40 + Math.floor(50 * r()) });
    if (r() < 0.3) pedals.push({ t: t + 0.1, down: true });
    t += Math.exp(Math.log(0.5) + 0.55 * gauss(r));
  }
  notes.sort((a, b) => a.t - b.t);
  return { notes, pedals, truth: null };
}

// The lane's synthSuite pieces: 3 meters x 3 textures x 3 rubato levels x seeds. Held-out seeds 37, 41, 53 (81 pieces).
export const TEMPO_TUNE_SEEDS = Object.freeze([11, 23]);
export const TEMPO_TEST_SEEDS = Object.freeze([37, 41, 53]);
export function tempoSuite(seeds = TEMPO_TEST_SEEDS) {
  const rows = [];
  for (const meter of Object.keys(LANE_METERS)) for (const tex of ["ballad", "arp", "block"]) for (const rub of [0, 1, 2]) for (const sd of seeds) {
    const r = rng(sd * 7 + rub * 13 + tex.length * 3 + meter.charCodeAt(0));
    const bpm = meter === "6/8" ? 45 + 30 * r() : 60 + 50 * r();
    rows.push({ meter, tex, rub, seed: sd, bpm, piece: genPiece(meter, tex, rub, bpm, sd * 1000 + rub * 10 + tex.length + meter.charCodeAt(0)) });
  }
  return rows;
}
// The lane's random unmetered pieces for the periodicity bands (9 pieces, seeds 700-708).
export function freeSuite(n = 9, base = 700) { return Array.from({ length: n }, (_, i) => genFree(base + i)); }

// Notes and pedals ({t} in s) as practice-log shaped events (t_ms may be fractional: replay only, never logged).
export function eventsOf(piece) {
  const ev = piece.notes.map((n) => ({ t_ms: n.t * 1000, kind: "on", note: n.note, vel: n.vel }));
  for (const p of piece.pedals || []) ev.push({ t_ms: p.t * 1000, kind: "pedal", down: !!p.down, value: p.down ? 100 : 0 });
  return ev.sort((a, b) => a.t_ms - b.t_ms);
}

// ========================================================================== 2. the section 3 run's generator ===
const pickW = (r, list) => { const tot = list.reduce((s, x) => s + x[1], 0); let u = r() * tot; for (const x of list) { if ((u -= x[1]) <= 0) return x[0]; } return list[list.length - 1][0]; };
const S3_SETS = {
  full: [[[0], 6], [[0, 6], 5], [[6], 1], [[0, 3, 6, 9], 1.5], [[0, 9], 1], [[0, 6, 9], 1], [[0, 3, 6], 0.7], [[0, 4, 8], 1.2], [[0, 8], 0.6], [[], 1]],
  simple: [[[0], 5], [[0, 6], 3], [[], 2]],
  compound: [[[0], 3], [[0, 4, 8], 4], [[0, 8], 2], [[0, 4], 1], [[], 1]],
  csimple: [[[0], 5], [[0, 8], 2], [[], 2]],
};
export const S3_METERS = Object.freeze({
  "4/4": { bpb: 4, mel: "full", arpDiv: 2, acc: "simple", beatTicks: 24 },
  "3/4": { bpb: 3, mel: "full", arpDiv: 2, acc: "simple", beatTicks: 24 },
  "12/8": { bpb: 4, mel: "compound", arpDiv: 3, acc: "csimple", beatTicks: 36 },
});

function s3Tempo(nBeats, bpb, bpm, rub, r) {
  const phrase = 4 * bpb, nom = []; let drift = 0;
  for (let k = 0; k < nBeats; k++) {
    const pos = k % phrase, x = pos / phrase; let f = 1;
    if (rub === 1) { drift = clamp(drift + 0.01 * gauss(r), -0.06, 0.06); f = 1 + 0.04 * Math.sin(2 * Math.PI * x) + drift; if (pos === phrase - 1) f *= 1.15; }
    if (rub === 2) { drift = clamp(drift + 0.02 * gauss(r), -0.12, 0.12); f = 1 + 0.1 * Math.sin(2 * Math.PI * x) + drift;
      if (pos === phrase - 2) f *= 1.2; if (pos === phrase - 1) { f *= 1.5; if (r() < 0.4) f *= 1 + (1 + 1.5 * r()) / 1.5; } }
    nom.push(60 / bpm * f);
  }
  const bt = [0.5]; for (let k = 0; k < nBeats; k++) bt.push(bt[k] + nom[k]);
  return bt;
}

export function genScore(meter, tex, rub, bpm, seed, sigOverride = null, bars = 24) {
  const r = rng(seed), M = S3_METERS[meter], nBeats = bars * M.bpb;
  const bt = s3Tempo(nBeats + 3, M.bpb, bpm, rub, r);
  const sig = sigOverride ?? [0.01, 0.02, 0.03][rub];
  const notes = [];
  const tAt = (k, p) => bt[k] + (p / 12) * (bt[k + 1] - bt[k]);
  const add = (k, p, note, vel, dt) => notes.push({ t: tAt(k, p) + dt, note, vel: clamp(Math.round(vel + 6 * gauss(r)), 1, 127), pos: k * 12 + p, tick: (k * 12 + p) * (M.beatTicks / 12) });
  const one = (k, p, note, vel, extra = 0) => add(k, p, note, vel, sig * gauss(r) + extra);
  let prevBar = null;
  for (let b = 0; b < bars; b++) {
    const k0 = b * M.bpb;
    const root = [0, 9, 5, 7][Math.floor(r() * 4)], bass = 36 + root, tri = [60 + root, 64 + root, 67 + root];
    const pats = prevBar && r() < 0.5 ? prevBar : Array.from({ length: M.bpb }, () => pickW(r, S3_SETS[tex === "arp" ? M.acc : M.mel]));
    prevBar = pats;
    one(k0, 0, bass, 72, -0.02 * r());
    if (tex === "ballad") {
      const rolled = r() < 0.4, sp = 0.02 + 0.04 * r(), j0 = sig * gauss(r);
      tri.forEach((n, i) => add(k0, 0, n, 56, j0 + (rolled ? sp * i / 2 : 0.004 * i)));
      if (M.bpb === 4 && r() < 0.5) one(k0 + 2, 0, bass + 7, 62);
    } else if (tex === "arp") {
      const cyc = [bass, bass + 7, bass + 16, bass + 7]; let q = 0;
      for (let j = 0; j < M.bpb; j++) for (let s = 0; s < M.arpDiv; s++) { if (j === 0 && s === 0) { q++; continue; } one(k0 + j, s * 12 / M.arpDiv, cyc[q % 4], s ? 48 : 60); q++; }
    } else {
      for (let j = 1; j < M.bpb; j++) if (r() < 0.3) { const j0 = sig * gauss(r); add(k0 + j, 0, bass + 7, 58, j0); add(k0 + j, 0, bass + 12, 54, j0 + 0.006); }
    }
    for (let j = 0; j < M.bpb; j++) for (const p of pats[j]) one(k0 + j, p, 72 + [0, 2, 4, 7][Math.floor(r() * 4)] + root % 5, 64);
  }
  notes.sort((a, b) => a.t - b.t);
  return { notes, beats: bt, bpb: M.bpb, bars, beatTicks: M.beatTicks, meter };
}

// The section 3 suite exactly as run: 3 meters x 3 textures x 3 rubato levels x seeds 101, 202, 303.
export function s3Suite() {
  const rows = [];
  for (const meter of Object.keys(S3_METERS)) for (const tex of ["ballad", "arp", "mixed"]) for (const rub of [0, 1, 2]) for (const sd of [101, 202, 303]) {
    const r = rng(sd * 7 + rub * 13 + tex.length * 3 + meter.charCodeAt(0));
    const bpm = meter === "12/8" ? 45 + 25 * r() : 60 + 40 * r();
    const seed = sd * 1000 + rub * 10 + tex.length + meter.charCodeAt(0) * 3;
    rows.push({ meter, tex, rub, seed, bpm, piece: genScore(meter, tex, rub, bpm, seed) });
  }
  return rows;
}
// The section 3 jitter sweep: rub1 tempo at 80 (55 for 12/8), note jitter 15, 30, 45, 60 ms, 27 pieces each.
export function s3JitterSuite(sig) {
  const rows = [];
  for (const meter of Object.keys(S3_METERS)) for (const tex of ["ballad", "arp", "mixed"]) for (const sd of [101, 202, 303]) {
    const seed = sd * 1000 + tex.length + meter.charCodeAt(0) * 3 + 7;
    rows.push({ meter, tex, seed, sig, piece: genScore(meter, tex, 1, meter === "12/8" ? 55 : 80, seed, sig) });
  }
  return rows;
}

// ======================================================================= 3. amended families with full truth ===
export const METER_DEFS = Object.freeze({
  "2/4": Object.freeze({ label: "2/4", tactus: 2, beatTicks: 24, compound: false }),
  "3/4": Object.freeze({ label: "3/4", tactus: 3, beatTicks: 24, compound: false }),
  "4/4": Object.freeze({ label: "4/4", tactus: 4, beatTicks: 24, compound: false }),
  "6/8": Object.freeze({ label: "6/8", tactus: 2, beatTicks: 36, compound: true }),
  "12/8": Object.freeze({ label: "12/8", tactus: 4, beatTicks: 36, compound: true }),
});

// Per-beat melody patterns in ticks of the beat. restAt: ticks where the voice's sounding note is released (a rest).
const MEL_SIMPLE = [
  { on: [0], w: 6 }, { on: [0, 12], w: 5 }, { on: [12], w: 1, restAt: [0] }, { on: [0, 6, 12, 18], w: 1.5 },
  { on: [0, 18], w: 1 }, { on: [0, 12, 18], w: 1 }, { on: [0, 6, 12], w: 0.7 }, { on: [0, 8, 16], w: 1.2 },
  { on: [0, 16], w: 0.6, restAt: [8] }, { on: [], w: 1, restAt: [0] },
];
const MEL_COMPOUND = [
  { on: [0], w: 3 }, { on: [0, 12, 24], w: 4 }, { on: [0, 24], w: 2 }, { on: [0, 12], w: 1 }, { on: [], w: 1, restAt: [0] },
  { on: [0, 18], w: 0.3 },
];
const ACC_SIMPLE = [{ on: [0], w: 5 }, { on: [0, 12], w: 3 }, { on: [], w: 2, restAt: [0] }];
const ACC_COMPOUND = [{ on: [0], w: 5 }, { on: [0, 24], w: 2 }, { on: [], w: 2, restAt: [0] }];
const T32 = [{ on: [0, 3, 6, 9, 12], w: 1, run: true }, { on: [0, 3, 6, 9, 12, 15, 18, 21], w: 0.5, run: true }, { on: [0, 12, 15, 18, 21], w: 0.7, run: true }];
const pickPat = (r, list) => { const tot = list.reduce((s, x) => s + x.w, 0); let u = r() * tot; for (const x of list) { if ((u -= x.w) <= 0) return x; } return list[list.length - 1]; };

export const TAKE_DEFAULTS = Object.freeze({
  meter: "4/4", texture: "ballad", rub: 1, bpm: 80, seed: 1, bars: 16, jitterMs: null, startMs: 500,
  pedal: "harmony", dryShare: 0.2, earlyReleaseShare: 0.3, pickupBeats: 0, countIn: false, tapErrMs: 30,
  tempoStep: null, fermatas: true, sextupletShare: 0, thirtySecondShare: 0, heldBassShare: 0, voicedTop: false,
});

const DIVS = [1, 2, 3, 4, 6, 8, 12];
function divisionOf(positions, beatTicks) {
  for (const d of DIVS) { if (beatTicks % d) continue; const step = beatTicks / d; if (positions.every((p) => p % step === 0)) return d; }
  return beatTicks;
}

export function genTake(spec = {}) {
  const o = { ...TAKE_DEFAULTS, ...spec };
  const M = METER_DEFS[o.meter];
  if (!M) throw new Error(`genTake: unknown meter ${o.meter}`);
  const BT = M.beatTicks, bpb = M.tactus, barT = BT * bpb;
  const r = rng(o.seed), rp = rng(mix(o.seed, 1)), rt = rng(mix(o.seed, 2));
  const countBeats = o.countIn ? 4 : 0, lead = countBeats + o.pickupBeats;
  const nBeats = lead + o.bars * bpb + 2;

  // ---- tempo: beat k starts at B[k]; notes inside a beat use its nominal length (a fermata adds silence after it)
  const nom = [], ferm = [], B = [o.startMs]; let drift = 0;
  for (let k = 0; k < nBeats; k++) {
    const kb = k - lead, bar = Math.floor(kb / bpb);
    const bpmHere = o.tempoStep && bar >= o.tempoStep.atBar ? o.tempoStep.bpm : o.bpm;
    let f = 1, extra = 0;
    if (kb >= 0) {
      const phrase = 4 * bpb, pos = kb % phrase, x = pos / phrase;
      if (o.rub === 1) { drift = clamp(drift + 0.01 * gauss(r), -0.06, 0.06); f = 1 + 0.04 * Math.sin(2 * Math.PI * x) + drift; if (pos === phrase - 1) f *= 1.15; }
      if (o.rub === 2) { drift = clamp(drift + 0.02 * gauss(r), -0.12, 0.12); f = 1 + 0.1 * Math.sin(2 * Math.PI * x) + drift; if (pos === phrase - 2) f *= 1.2; if (pos === phrase - 1) { f *= 1.5; if (o.fermatas && r() < 0.4) extra = (1 + 1.5 * r()) * 60000 / bpmHere; } }
    }
    nom.push(60000 / bpmHere * f); ferm.push(extra > 0); B.push(B[k] + nom[k] + extra);
  }
  const tAt = (tick) => { const q = Math.floor(tick / BT), k = lead + q; return B[k] + ((tick - q * BT) / BT) * nom[k]; };
  const beatOfMs = (ms) => { let k = 0; while (k + 1 < B.length && B[k + 1] <= ms) k++; return k; };
  const tickAtMs = (ms) => { const k = beatOfMs(ms); return (k - lead) * BT + Math.min(1, (ms - B[k]) / nom[Math.min(k, nom.length - 1)]) * BT; };

  // ---- composition
  const ROOTS = [0, 9, 5, 7, 2, 4];
  const comp = [];       // { voice, staff, note, vel, tick, roll, leadMs, rel? }
  const restAt = new Map([[1, []], [2, []], [3, []], [4, []]]);
  const harm = [];       // pedal changes at harmony entries: { tick }
  const hold = Array.from({ length: o.bars }, (_, b) => b < o.bars - 1 && o.texture !== "arp" && r() < o.heldBassShare);
  const mid = Math.ceil(bpb / 2) * BT;
  for (let j = 0; j < o.pickupBeats; j++) {
    const k0 = -(o.pickupBeats - j) * BT, pat = r() < 0.5 ? [0] : [0, M.compound ? 24 : 12];
    pat.forEach((p, i) => comp.push({ voice: 1, staff: 1, note: 76 - 2 * i, vel: 58, tick: k0 + p }));
  }
  let prevPats = null;
  for (let b = 0; b < o.bars; b++) {
    const s0 = b * barT;
    const root = ROOTS[Math.floor(r() * 4)], minor = root === 9 || root === 2 || root === 4, bass = 36 + root;
    const third = root + (minor ? 3 : 4), fifth = root + 7;
    const entry = b > 0 && hold[b - 1] ? mid : 0;
    harm.push({ tick: s0 + entry });
    const accent = (j) => (j === 0 ? 12 : bpb === 4 && j === 2 ? 6 : 0);
    const top = o.voicedTop ? 15 + Math.floor(r() * 11) : 0;
    if (o.texture === "ballad") {
      comp.push({ voice: 4, staff: 2, note: bass, vel: 70 + (entry ? 0 : 12), tick: s0 + entry, leadMs: 20 * r() });
      if (bpb === 4 && !entry && !hold[b] && r() < 0.5) comp.push({ voice: 4, staff: 2, note: bass + 7, vel: 62, tick: s0 + 2 * BT });
      const rolled = r() < 0.4, spread = 20 + 40 * r();
      [60 + root, 60 + third, 60 + fifth].forEach((n, i) => comp.push({ voice: 2, staff: 1, note: n, vel: 54 + accent(0) * (entry ? 0 : 1), tick: s0 + entry, roll: rolled ? { i, n: 3, spreadMs: spread } : null }));
    } else if (o.texture === "arp") {
      const cyc4 = [bass, bass + 7, bass + 12 + third, bass + 7], cyc6 = [bass, bass + 7, bass + 12, bass + 12 + third, bass + 12, bass + 7];
      for (let j = 0; j < bpb; j++) {
        const sext = r() < o.sextupletShare, div = sext ? 6 : M.compound ? 3 : 2;
        for (let s = 0; s < div; s++) {
          const note = sext ? cyc6[s] : cyc4[(j + s) % 4];
          comp.push({ voice: 3, staff: 2, note, vel: s === 0 ? 60 + accent(j) : 48, tick: s0 + j * BT + s * (BT / div) });
        }
      }
    } else {
      comp.push({ voice: 4, staff: 2, note: bass, vel: 74 + accent(0) * (entry ? 0 : 1), tick: s0 + entry, leadMs: 20 * r() });
      for (let j = 1; j < bpb; j++) if (r() < 0.3) {
        const at = s0 + j * BT + (M.compound ? 12 : 12);
        if (at < s0 + entry) continue;
        comp.push({ voice: 3, staff: 2, note: bass + 7, vel: 58, tick: at }, { voice: 3, staff: 2, note: bass + 12, vel: 54, tick: at, leadMs: -6 });
      }
    }
    const set = o.texture === "arp" ? (M.compound ? ACC_COMPOUND : ACC_SIMPLE) : (M.compound ? MEL_COMPOUND : MEL_SIMPLE);
    const pats = prevPats && r() < 0.5 ? prevPats : Array.from({ length: bpb }, () => (!M.compound && o.thirtySecondShare > 0 && r() < o.thirtySecondShare ? pickPat(r, T32) : pickPat(r, set)));
    prevPats = pats;
    for (let j = 0; j < bpb; j++) {
      const pat = pats[j], base = 72 + [0, 2, 4, 7][Math.floor(r() * 4)] + root % 5;
      pat.on.forEach((p, i) => comp.push({ voice: 1, staff: 1, note: pat.run ? base + (i % 5) : 72 + [0, 2, 4, 7][Math.floor(r() * 4)] + root % 5, vel: 64 + accent(j) * (p === 0 ? 1 : 0) + top, tick: s0 + j * BT + p }));
      for (const x of pat.restAt || []) restAt.get(1).push(s0 + j * BT + x);
    }
  }
  const endTick = o.bars * barT;
  comp.sort((a, b) => a.tick - b.tick || a.voice - b.voice || a.note - b.note);
  comp.forEach((n, i) => { n.id = i; });

  // ---- intended key release per voice: next onset, next rest, bar end (held-bass bars: the bar end, the pedal rings on)
  const onsetsBy = new Map();
  for (const n of comp) { if (!onsetsBy.has(n.voice)) onsetsBy.set(n.voice, []); const l = onsetsBy.get(n.voice); if (l[l.length - 1] !== n.tick) l.push(n.tick); }
  for (const l of restAt.values()) l.sort((a, b) => a - b);
  const nextAfter = (list, tick) => { for (const x of list) if (x > tick) return x; return Infinity; };
  const barEndOf = (tick) => (Math.floor(tick / barT) + 1) * barT;
  for (const n of comp) n.rel = Math.min(nextAfter(onsetsBy.get(n.voice), n.tick), nextAfter(restAt.get(n.voice) || [], n.tick), barEndOf(n.tick));

  // ---- pedal model (ms): lift 10-30 ms after each harmony entry, press 100-200 ms after it, unless the harmony is dry
  const pedalEv = [];
  const useP = o.pedal !== "none";
  for (const h of harm) {
    const t0 = tAt(h.tick);
    if (pedalEv.length && pedalEv[pedalEv.length - 1].down) pedalEv.push({ t: t0 + 10 + 20 * rp(), down: false, value: 0 });
    if (useP && rp() >= o.dryShare) pedalEv.push({ t: t0 + 100 + 100 * rp(), down: true, value: 90 + Math.floor(14 * rp()) });
  }
  if (pedalEv.length && pedalEv[pedalEv.length - 1].down) pedalEv.push({ t: tAt(endTick) + 200, down: false, value: 0 });
  const downAt = (ms) => { let d = false; for (const p of pedalEv) { if (p.t > ms) break; d = p.down; } return d; };
  const liftAfter = (ms) => { for (const p of pedalEv) if (p.t > ms && !p.down) return p.t; return Infinity; };
  const pressIn = (a, b) => pedalEv.some((p) => p.down && p.t > a && p.t < b);

  // ---- performance (rp stream): jitter per voice cluster, bass lead, rolls, releases, sound ends
  const sig = o.jitterMs ?? [10, 20, 30][o.rub];
  const clusters = new Map();
  for (const n of comp) { const k = n.voice + ":" + n.tick; if (!clusters.has(k)) clusters.set(k, []); clusters.get(k).push(n); }
  for (const cl of clusters.values()) {
    const j = sig * gauss(rp), relMs = tAt(cl[0].rel), onIdeal = tAt(cl[0].tick);
    const early = useP && downAt(relMs - 5) && rp() < o.earlyReleaseShare, f = 0.2 + 0.4 * rp();
    cl.forEach((n, i) => {
      const roll = n.roll ? n.roll.spreadMs * n.roll.i / (n.roll.n - 1) : 4 * i;
      n.on = onIdeal + j + roll - (n.leadMs || 0);
      n.off = early ? n.on + f * (relMs - n.on) : relMs - (5 + 25 * rp());
      n.off = Math.max(n.off, n.on + 20);
      n.early = early;
      n.onIdeal = onIdeal;
      n.offIdeal = early ? onIdeal + f * (relMs - onIdeal) : relMs;
      n.vel = clamp(Math.round(n.vel + 6 * gauss(rp)), 1, 127);
    });
  }
  const byPitch = new Map();
  for (const n of comp) { if (!byPitch.has(n.note)) byPitch.set(n.note, []); byPitch.get(n.note).push(n); }
  for (const l of byPitch.values()) {
    l.sort((a, b) => a.on - b.on);
    for (let i = 0; i + 1 < l.length; i++) if (l[i].off > l[i + 1].on - 5) { l[i].off = Math.max(l[i].on + 10, l[i + 1].on - 5); l[i].offIdeal = Math.min(l[i].offIdeal, l[i + 1].onIdeal); }
  }
  const soundOf = (n, off, onKey) => {
    const next = byPitch.get(n.note).find((m) => m[onKey] > n[onKey]);
    const rep = next ? next[onKey] : Infinity;
    if (!downAt(off)) return { t: Math.min(off, rep), by: rep < off ? "repeat" : "release" };
    const lift = liftAfter(off);
    if (rep < lift) return { t: rep, by: "repeat" };
    if (lift === Infinity) return { t: off, by: "all-off" };
    return { t: lift, by: "pedal" };
  };

  // ---- truth: the C1 / C7 written-duration rule on the ideal performance
  const beatPos = new Map();
  for (const n of comp) { const k = Math.floor(n.tick / BT); if (!beatPos.has(k)) beatPos.set(k, new Set()); beatPos.get(k).add(n.tick - k * BT); }
  const divAt = (k) => (beatPos.has(k) ? divisionOf([...beatPos.get(k)], BT) : 1);
  const slotAt = (tick) => BT / divAt(Math.floor(tick / BT));
  const snap = (tickF, forward) => { const k = Math.floor(tickF / BT), step = BT / divAt(k), base = k * BT, x = (tickF - base) / step; return base + step * (forward ? Math.ceil(x - 1e-6) : Math.round(x)); };
  const lowestLower = onsetsBy.has(4) ? 4 : 3;
  const tol = 6;
  for (const n of comp) {
    const list = onsetsBy.get(n.voice);
    const nextTick = Math.min(nextAfter(list, n.tick), endTick);
    const tNext = tAt(nextTick), barEnd = barEndOf(n.tick);
    const tolMs = (tol / BT) * nom[lead + Math.floor(n.tick / BT)];
    const se = soundOf(n, n.offIdeal, "onIdeal").t;
    const oneSlot = n.tick + slotAt(n.tick);
    let end;
    if (n.staff === 2 && n.voice === lowestLower) {
      end = se >= tNext - tolMs ? nextTick : Math.max(snap(tickAtMs(se), false), oneSlot);
      let cap = barEnd;
      if (end > barEnd) { const early = list.some((x) => x >= barEnd && x < barEnd + barT / 2); cap = early ? barEnd : barEnd + barT; }
      end = Math.min(end, cap, endTick);
    } else if (!(downAt(n.offIdeal) || pressIn(n.offIdeal, tNext))) {
      end = tNext - n.offIdeal < tolMs ? nextTick : Math.max(snap(tickAtMs(n.offIdeal), true), oneSlot);
      end = Math.min(end, barEnd);
    } else {
      end = se >= tNext - tolMs ? Math.min(nextTick, barEnd) : Math.min(Math.max(snap(tickAtMs(se), false), oneSlot), barEnd);
    }
    n.dur = end - n.tick;
  }

  // ---- events (integer ms, performance.py shape) and truth
  const events = [];
  const sounds = comp.map((n) => soundOf(n, n.off, "on"));
  comp.forEach((n, i) => {
    events.push({ t_ms: Math.round(n.on), kind: "on", note: n.note, vel: n.vel });
    events.push({ t_ms: Math.max(Math.round(n.on) + 1, Math.round(n.off)), kind: "off", note: n.note });
    events.push({ t_ms: Math.max(Math.round(n.on) + 1, Math.round(sounds[i].t)), kind: "sound_end", note: n.note, by: sounds[i].by });
  });
  for (const p of pedalEv) events.push({ t_ms: Math.round(p.t), kind: "pedal", down: p.down, value: p.value });
  const order = { off: 0, sound_end: 1, pedal: 2, on: 3 };
  events.sort((a, b) => a.t_ms - b.t_ms || order[a.kind] - order[b.kind]);
  const taps = o.countIn ? [0, 1, 2, 3].map((i) => B[i] + o.tapErrMs * gauss(rt)) : [];

  const bars = [];
  for (let b = 0; b < o.bars; b++) {
    const a = tAt(b * barT), z = tAt((b + 1) * barT);
    let down = 0, state = downAt(a), t = a;
    for (const p of pedalEv) { if (p.t <= a) continue; if (p.t >= z) break; if (state) down += p.t - t; state = p.down; t = p.t; }
    if (state) down += z - t;
    bars.push({ index: b, startTick: b * barT, pedalledShare: down / (z - a), held: hold[b] });
  }
  const truth = {
    tpq: TPQ, meter: { ...M, barTicks: barT }, lead, countInBeats: countBeats, pickupBeats: o.pickupBeats, bars: o.bars,
    beats_ms: B.slice(0, lead + o.bars * bpb + 1), nom_ms: nom.slice(0, lead + o.bars * bpb), ferm: ferm.slice(0, lead + o.bars * bpb),
    downbeats_ms: Array.from({ length: o.bars + 1 }, (_, b) => B[lead + b * bpb]),
    notes: comp.map((n, i) => ({ id: n.id, note: n.note, vel: n.vel, voice: n.voice, staff: n.staff, tick: n.tick, dur: n.dur,
      on_ms: n.on, off_ms: n.off, se_ms: sounds[i].t, by: sounds[i].by, early: n.early })),
    divisions: Array.from({ length: o.bars * bpb + o.pickupBeats }, (_, i) => divAt(i - o.pickupBeats)),
    barInfo: bars, taps_ms: taps, pedal: pedalEv.map((p) => ({ ...p })),
  };
  if (M.compound) truth.under44 = { meter: "4/4", beatTicks: 24, notes: truth.notes.map((n) => ({ id: n.id, tick: n.tick * 2 / 3, dur: n.dur * 2 / 3 })) };
  return { spec: o, events, truth, taps: taps.slice() };
}

// Unmetered tape density runs (C6, LR11f): single notes at `rate` groups a second for `seconds`, a scale up and down.
export function genTapeRun({ seconds = 1.5, rate = 10, seed = 1, startMs = 500 } = {}) {
  const r = rng(seed), events = [], n = Math.round(seconds * rate), notes = [];
  const scale = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79];
  for (let i = 0; i < n; i++) {
    const t = startMs + i * 1000 / rate + 3 * gauss(r), idx = i % 22 < 11 ? i % 22 : 21 - (i % 22), note = scale[idx % scale.length];
    notes.push({ id: i, note, on_ms: t, off_ms: t + 80 });
    events.push({ t_ms: Math.round(t), kind: "on", note, vel: 60 + Math.floor(20 * r()) }, { t_ms: Math.round(t + 80), kind: "off", note }, { t_ms: Math.round(t + 80), kind: "sound_end", note, by: "release" });
  }
  events.sort((a, b) => a.t_ms - b.t_ms);
  return { events, truth: { groups: n, seconds, rate, notes } };
}

// ============================================================================ suites of amended families ===
// Held-out by default; a family's tuning seeds are its first two.
export const FAMILY_SEEDS = Object.freeze({ tune: [5, 6], test: [71, 72, 73] });
export function familySuite(family, seeds = FAMILY_SEEDS.test) {
  const rows = [];
  const add = (spec) => rows.push({ family, spec, take: genTake(spec) });
  for (const sd of seeds) for (const rub of [0, 1, 2]) {
    const tempo = (m) => 60 + ((sd * 7 + rub * 13 + m.length) % 41);
    const base = { rub, seed: sd * 1000 + rub * 10, bars: 16 };
    if (family === "sextuplet") for (const meter of ["4/4", "3/4"]) add({ ...base, meter, texture: "arp", bpm: tempo(meter), sextupletShare: 0.15, seed: base.seed + meter.length });
    if (family === "thirtysecond") for (const meter of ["4/4", "3/4"]) add({ ...base, meter, texture: "ballad", bpm: 60 + (tempo(meter) - 60) / 2, thirtySecondShare: 0.12, seed: base.seed + meter.length + 1 });
    if (family === "pedal") for (const meter of ["4/4", "3/4", "12/8"]) for (const texture of ["ballad", "arp", "mixed"]) add({ ...base, meter, texture, bpm: meter === "12/8" ? 45 + (tempo(meter) - 60) / 2 : tempo(meter), seed: base.seed + meter.length * 3 + texture.length });
    if (family === "heldBass") for (const meter of ["4/4", "3/4"]) add({ ...base, meter, texture: "ballad", bpm: tempo(meter), heldBassShare: 0.35, seed: base.seed + meter.length + 2 });
    if (family === "voiced") for (const meter of ["4/4", "3/4"]) add({ ...base, meter, texture: "mixed", bpm: tempo(meter), voicedTop: true, seed: base.seed + meter.length + 3 });
    if (family === "compound44") for (const texture of ["ballad", "arp", "mixed"]) add({ ...base, meter: "12/8", texture, bpm: 45 + (tempo(texture) - 60) / 2, seed: base.seed + texture.length + 4 });
    if (family === "countIn" && rub > 0) for (const texture of ["ballad", "arp", "mixed"]) add({ ...base, meter: "4/4", texture, bpm: tempo(texture), countIn: true, bars: 12, seed: base.seed + texture.length + 5 });
    if (family === "pickup") add({ ...base, meter: "4/4", texture: "ballad", bpm: tempo("p"), pickupBeats: 1, seed: base.seed + 6 });
    if (family === "tempoStep" && rub < 2) add({ ...base, meter: "4/4", texture: "mixed", bpm: 70, tempoStep: { atBar: 8, bpm: 95 }, seed: base.seed + 7 });
  }
  return rows;
}
export const FAMILIES = Object.freeze(["sextuplet", "thirtysecond", "pedal", "heldBass", "voiced", "compound44", "countIn", "pickup", "tempoStep"]);
