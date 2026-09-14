// Spec calibration: the bloom tracker at real note level, with harmonySet (PIANO-V2-SPEC 6.1) and the overlay settle.
// Compares the design's tracker (window 1.6 s from the bloom's start, maxLen 2.5 s, committed-set superset test)
// with the spec's tracker (gesture-based boundaries, no fixed window, maxLen 8 s), at fast and slow tempi, plus
// pedal-point chord changes that must stay separate events.
// Run: node bloom-sim.mjs  (Node 24)
import { Theory } from "../design-theory-rarity-lab/theory.mjs";
import { intrinsic } from "../design-theory-rarity-lab/rarity.mjs";

const mod = (a, n) => ((a % n) + n) % n;
const RECENT = 1.5;
const KEY = { tonic: 5, mode: "major", name: "F major", bias: -1 };
const fOf = (info) => intrinsic({ info, key: KEY, keyConfidence: "sure" }).F;

function harmonySet(sounding, t) {
  const notes = [];
  let lowest = Infinity, lowestPedal = Infinity;
  for (const [m, st] of sounding) {
    if (m < lowest) lowest = m;
    if (st.held) notes.push(m);
    else { if (t - st.t0 <= RECENT) notes.push(m); if (m < lowestPedal) lowestPedal = m; }
  }
  if (lowest !== Infinity && lowestPedal === lowest && !notes.includes(lowest)) notes.push(lowest);
  return notes.sort((a, b) => a - b);
}

function arpeggioBars(bars, step, fingerHold = 0.25, repeats = 40) {
  const ev = [];
  let t = 0;
  for (let r = 0; r < repeats; r++) {
    for (const notes of bars) {
      ev.push({ t, kind: "pedal", down: true });
      notes.forEach((m, i) => { const at = t + i * step; ev.push({ t: at, kind: "on", m }); ev.push({ t: at + fingerHold, kind: "off", m }); });
      const end = t + notes.length * step + 0.35;
      ev.push({ t: end, kind: "pedal", down: false });
      t = end + 0.05;
    }
  }
  return ev.sort((a, b) => a.t - b.t);
}
// Rolled chords: each bar's notes rolled bottom to top over 150 ms, held, re-pedalled.
function rolledBars(bars, roll = 0.15, dur = 2.2, repeats = 40) {
  const ev = [];
  let t = 0;
  for (let r = 0; r < repeats; r++) {
    for (const notes of bars) {
      ev.push({ t, kind: "pedal", down: true });
      notes.forEach((m, i) => { const at = t + (i * roll) / Math.max(1, notes.length - 1); ev.push({ t: at, kind: "on", m }); ev.push({ t: t + dur * 0.8, kind: "off", m }); });
      ev.push({ t: t + dur, kind: "pedal", down: false });
      t += dur + 0.05;
    }
  }
  return ev.sort((a, b) => a.t - b.t);
}
// Pedal point: a low C struck once and held by the pedal under three right-hand chords, pedal never lifted.
function pedalPointBars(repeats = 40, gap = 1.8) {
  const ev = [];
  let t = 0;
  const chords = [[53, 57, 60], [55, 58, 62], [52, 55, 58, 60]];  // F/C, Gm/C, C7 over the low C
  for (let r = 0; r < repeats; r++) {
    ev.push({ t, kind: "pedal", down: true });
    ev.push({ t, kind: "on", m: 36 }); ev.push({ t: t + 0.2, kind: "off", m: 36 });
    chords.forEach((c, i) => {
      const at = t + 0.05 + i * gap;
      for (const m of c) { ev.push({ t: at, kind: "on", m }); ev.push({ t: at + gap * 0.9, kind: "off", m }); }
    });
    const end = t + 0.05 + chords.length * gap;
    ev.push({ t: end, kind: "pedal", down: false });
    t = end + 0.05;
  }
  return ev.sort((a, b) => a.t - b.t);
}
function blockBars(bars, dur = 2.0, repeats = 40) {
  const ev = [];
  let t = 0;
  for (let r = 0; r < repeats; r++) {
    for (const notes of bars) {
      ev.push({ t, kind: "pedal", down: true });
      for (const m of notes) { ev.push({ t, kind: "on", m }); ev.push({ t: t + dur * 0.8, kind: "off", m }); }
      ev.push({ t: t + dur, kind: "pedal", down: false });
      t += dur + 0.05;
    }
  }
  return ev.sort((a, b) => a.t - b.t);
}

// Replays a score on a 10 ms clock: re-detects every tick (so pedal notes ageing out of harmonySet relabel the chord,
// as the spec requires), commits names like overlay.update (120 ms after a note-on, 300 ms otherwise).
function replay(score, tracker) {
  const sounding = new Map();
  let pedal = false, pedalLifted = false, onCount = 0, lastOnT = -1e9;
  const onTimes = [];
  let shown = null, pending = null, pendingSince = 0, pendingGrew = false, lastOn = 0, lastCommitOnT = -1e9;
  let i = 0;
  const end = score[score.length - 1].t + 2;
  for (let step = 0; step * 0.01 <= end; step++) {
    const t = step * 0.01;
    while (i < score.length && score[i].t <= t + 1e-9) {
      const e = score[i++];
      if (e.kind === "pedal") {
        pedal = e.down;
        if (!pedal) { for (const [m, st] of [...sounding]) if (!st.held) sounding.delete(m); pedalLifted = true; }
      } else if (e.kind === "on") {
        sounding.set(e.m, { held: true, t0: e.t }); onCount++; lastOnT = e.t; onTimes.push(e.t);
      } else if (e.kind === "off") {
        const st = sounding.get(e.m);
        if (st) { if (pedal) st.held = false; else sounding.delete(e.m); }
      }
    }
    const hs = harmonySet(sounding, t);
    const info = hs.length ? Theory.detect(hs, KEY.bias) : null;
    if (info) {
      const grew = onCount !== lastOn; lastOn = onCount;
      if (!pending || pending.name !== info.name) { pending = info; pendingSince = t; pendingGrew = grew; }
      if (shown && shown.name === info.name) shown = info;
      else if (t - pendingSince >= (pendingGrew ? 0.12 : 0.3)) {
        shown = pending;
        if (shown.kind === "chord" && shown.suffix !== "5") {
          // a block strike: 3+ note-ons within 80 ms, the newest of them after the previous commit's newest note-on
          const cluster = onTimes.filter((x) => x >= lastOnT - 0.08 && x <= lastOnT);
          const blockStrike = cluster.length >= 3 && lastOnT > lastCommitOnT;
          tracker.commit(shown, t, { pedalLifted, lastOnT, blockStrike });
          pedalLifted = false;
          lastCommitOnT = lastOnT;
        }
      }
    }
    tracker.tick(t, shown ? shown.name : null);
  }
  return tracker.result();
}

const pcsOf = (info) => new Set(info.notes.map((n) => mod(n.midi, 12)));
const bassOf = (info) => mod(info.notes[0].midi, 12);
const isSuperset = (a, b) => [...b].every((x) => a.has(x));
const overlap = (a, b) => [...a].filter((x) => b.has(x)).length;

// The design's tracker (design-theory-rarity.md 5.2), as written: scores the latest name at settle.
function designTracker({ settle = 0.4, window = 1.6, maxLen = 2.5 } = {}) {
  let bloom = null, blooms = 0, scorings = 0;
  const scored = [];
  return {
    commit(info, t, ctx) {
      const pcs = pcsOf(info), bassPc = bassOf(info);
      const grows = bloom && !ctx.pedalLifted && t - bloom.t0 <= window && bassPc === bloom.bassPc && isSuperset(pcs, bloom.pcs);
      if (grows) { Object.assign(bloom, { info, pcs, lastChange: t }); return; }
      bloom = { t0: t, lastChange: t, info, pcs, bassPc, scoredAt: null }; blooms++;
    },
    tick(t) {
      if (!bloom) return;
      const settled = t - bloom.lastChange >= settle || t - bloom.t0 >= maxLen;
      if (!settled || bloom.scoredAt === bloom.lastChange) return;
      bloom.scoredAt = bloom.lastChange; scorings++; scored.push(bloom.info.name);
    },
    result() { return { blooms, scorings, scored }; },
  };
}

// The spec's tracker. Boundaries are gestures, not a clock:
//   a new bloom starts on a pedal lift, a bass change, a block strike (3+ notes within 80 ms), a rest (> 1.2 s with no
//   note-on) or after 8 s; otherwise the commit joins the bloom, unless it shares fewer than 2 pitch classes with the
//   bloom's last name (a real change under a held pedal and bass).
// The bloom scores its RICHEST reading (highest fanciness F, latest on ties) once it settles: 400 ms after the last join,
// or 1.3x the bloom's latest note gap when that is longer (capped at 1.0 s), and rescores only when the richest
// reading changed (an upgrade).
function specTracker({ settleMin = 0.4, settleMax = 1.0, maxLen = 8, restGap = 1.2, adaptive = true } = {}) {
  let bloom = null, blooms = 0, scorings = 0;
  const scored = [];
  return {
    commit(info, t, ctx) {
      const pcs = pcsOf(info), bassPc = bassOf(info), F = fOf(info);
      const joins = bloom && !ctx.pedalLifted && bassPc === bloom.bassPc && !ctx.blockStrike
        && t - bloom.t0 <= maxLen && ctx.lastOnT - bloom.lastOnT <= restGap && overlap(pcs, bloom.lastPcs) >= 2;
      if (joins) {
        const ioi = ctx.lastOnT - bloom.lastOnT;
        if (ioi > 0.02) bloom.ioi = ioi;
        bloom.lastPcs = pcs; bloom.lastChange = t; bloom.lastOnT = ctx.lastOnT;
        if (F >= bloom.best.F) bloom.best = { info, F };
        return;
      }
      bloom = { t0: t, lastChange: t, lastPcs: pcs, bassPc, lastOnT: ctx.lastOnT, ioi: 0, best: { info, F }, scoredBest: null }; blooms++;
    },
    tick(t) {
      if (!bloom) return;
      const settle = adaptive ? Math.min(settleMax, Math.max(settleMin, 1.3 * bloom.ioi)) : settleMin;
      if (t - bloom.lastChange < settle || bloom.scoredBest === bloom.best) return;
      bloom.scoredBest = bloom.best; scorings++; scored.push(bloom.best.info.name);
    },
    result() { return { blooms, scorings, scored }; },
  };
}

const BLOOMS = [
  [29, 41, 48, 57, 64, 67, 72],   // F  -> Fmaj7 -> Fmaj9
  [38, 45, 53, 60, 64, 69],       // Dm -> Dm7 -> Dm9
  [34, 41, 50, 57, 60, 64],       // Bb -> Bbmaj7 -> ... -> Dm9/Bb
  [36, 43, 46, 50, 53, 60],       // C  -> C7 -> C9sus4
];
const BLOCKS = [[41, 53, 57, 60], [36, 55, 60, 64], [38, 53, 57, 62], [34, 50, 53, 57, 58]];

const cases = [
  ["pedalled arpeggio bars, 0.33 s a note (bar ~2.3 s)", arpeggioBars(BLOOMS, 0.33), 160, 1],
  ["pedalled arpeggio bars, 0.50 s a note (bar ~3.4 s)", arpeggioBars(BLOOMS, 0.5), 160, 1],
  ["pedalled arpeggio bars, 0.65 s a note (bar ~4.3 s)", arpeggioBars(BLOOMS, 0.65), 160, 1],
  ["rolled chords (150 ms roll), re-pedalled each bar", rolledBars(BLOOMS), 160, 1],
  ["block chords, re-pedalled each bar", blockBars(BLOCKS), 160, 1],
  ["pedal point: F/C -> Gm/C -> C7 over a held low C, no lift", pedalPointBars(), 40, 3],
];
const rows = ["| case | bars | expected events per bar | design tracker: events / scorings per bar | spec tracker, fixed 0.4 s settle | spec tracker, adaptive settle |", "|---|---|---|---|---|---|"];
const samples = [];
for (const [name, score, bars, expect] of cases) {
  const d = replay(score, designTracker());
  const f = replay(score, specTracker({ adaptive: false }));
  const s = replay(score, specTracker());
  const cell = (r) => `${(r.blooms / bars).toFixed(2)} / ${(r.scorings / bars).toFixed(2)}`;
  rows.push(`| ${name} | ${bars} | ${expect} | ${cell(d)} | ${cell(f)} | ${cell(s)} |`);
  samples.push(`${name}\n  design scored (first 8): ${d.scored.slice(0, 8).join(" · ")}\n  spec, adaptive settle, scored (first 8): ${s.scored.slice(0, 8).join(" · ")}`);
}
console.log(rows.join("\n"));
console.log("\nWhat each tracker scored:\n" + samples.join("\n"));
