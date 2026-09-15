// Node tests for the live sheet music fixtures and metrics (slice LS0): tests/fixtures/score/{gen,metrics,s3ref}.mjs.
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md sections 3, 9, 10 and plan-amendments.md
// sections 2 and 6. Zero dependencies:
//   node tests/score_fixtures.test.mjs            generator contracts, metric helpers, then LR1 (both tables)
//   node tests/score_fixtures.test.mjs --quick    skip LR1 (the two suites take a few seconds)
// LR1: the generator is deterministic by seed, and the section 3 tables (s3Compat: the run's generator, grouping and
// DIVS {1, 2, 4, 3} quantizer in s3ref.mjs, the inferred row fed by arsenal/web/piano/score/beat.js) and the tempo
// lane's recommended-configuration table (genPiece through beat.js with meter "auto" and the lane's 40 ms groups)
// reproduce within 1 point of tests/fixtures/score/lr1_reference.json. Shares compare at +-0.01; flips per minute at
// +-0.10; mean time to lock at +-1.0 s; pieces never locked at +-1.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as G from "./fixtures/score/gen.mjs";
import * as MX from "./fixtures/score/metrics.mjs";
import * as S3 from "./fixtures/score/s3ref.mjs";
import { createOnsets, LANE_ONSET_PARAMS } from "../arsenal/web/piano/score/onsets.js";
import { trackEvents, LANE_BEAT_PARAMS } from "../arsenal/web/piano/score/beat.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const argv = process.argv.slice(2);
const quick = argv.includes("--quick");
let pass = 0, fail = 0;
const receipts = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const KINDS = ["on", "off", "pedal", "chord", "sound_end"], BY = ["release", "pedal", "repeat", "all-off"];

// ------------------------------------------------------------------------------------ generator contracts ---
{
  check("genPiece deterministic", same(G.genPiece("4/4", "ballad", 1, 80, 123), G.genPiece("4/4", "ballad", 1, 80, 123)));
  check("genPiece seed matters", !same(G.genPiece("4/4", "ballad", 1, 80, 123).notes, G.genPiece("4/4", "ballad", 1, 80, 124).notes));
  check("genScore deterministic", same(G.genScore("12/8", "arp", 2, 55, 9), G.genScore("12/8", "arp", 2, 55, 9)));
  check("genFree deterministic", same(G.genFree(700), G.genFree(700)));
  const pc = G.genPiece("6/8", "arp", 0, 60, 77);
  check("genPiece ticks are integers on the 6/8 grid", pc.notes.every((n) => Number.isInteger(n.tick) && n.tick % 12 === 0));
  const sc = G.genScore("12/8", "mixed", 1, 50, 5);
  check("genScore ticks: twelfths x3 in 12/8", sc.notes.every((n) => n.tick === n.pos * 3));

  for (const family of G.FAMILIES) {
    const rows = G.familySuite(family, G.FAMILY_SEEDS.tune);
    check(`${family}: suite not empty`, rows.length > 0);
    const again = G.familySuite(family, G.FAMILY_SEEDS.tune);
    check(`${family}: deterministic`, same(rows.map((r) => r.take), again.map((r) => r.take)));
    for (const { take, spec } of rows) {
      const tag = `${family} seed ${spec.seed} ${spec.meter} rub${spec.rub}`;
      const { events, truth } = take;
      const bad = events.find((e) => !Number.isInteger(e.t_ms) || e.t_ms < 0 || !KINDS.includes(e.kind)
        || ((e.kind === "on" || e.kind === "off" || e.kind === "sound_end") && !(Number.isInteger(e.note) && e.note >= 0 && e.note <= 127))
        || (e.kind === "on" && !(Number.isInteger(e.vel) && e.vel >= 1 && e.vel <= 127))
        || (e.kind === "sound_end" && !BY.includes(e.by))
        || (e.kind === "pedal" && !(typeof e.down === "boolean" && Number.isInteger(e.value) && e.value >= 0 && e.value <= 127)));
      check(`${tag}: events have the performance.py shape`, !bad, JSON.stringify(bad));
      check(`${tag}: events in time order`, events.every((e, i) => i === 0 || e.t_ms >= events[i - 1].t_ms));
      const ons = events.filter((e) => e.kind === "on").length;
      check(`${tag}: one on, off and sound_end per note`, ons === truth.notes.length && events.filter((e) => e.kind === "off").length === ons && events.filter((e) => e.kind === "sound_end").length === ons);
      const BT = truth.meter.beatTicks, barT = truth.meter.barTicks;
      check(`${tag}: positive integer durations`, truth.notes.every((n) => Number.isInteger(n.tick) && Number.isInteger(n.dur) && n.dur > 0), JSON.stringify(truth.notes.find((n) => !(n.dur > 0))));
      // within a voice, a note never runs past the next onset of that voice
      const byVoice = new Map();
      for (const n of truth.notes) { if (!byVoice.has(n.voice)) byVoice.set(n.voice, []); byVoice.get(n.voice).push(n); }
      let overlap = null;
      for (const l of byVoice.values()) {
        const ticks = [...new Set(l.map((n) => n.tick))].sort((a, b) => a - b);
        for (const n of l) { const nx = ticks.find((t) => t > n.tick); if (nx != null && n.tick + n.dur > nx) overlap = n; }
      }
      check(`${tag}: no note runs past the next onset in its voice`, !overlap, JSON.stringify(overlap));
      // only the lowest voice of the lower staff crosses a bar line (C7), and by at most one bar
      const lowest = byVoice.has(4) ? 4 : 3;
      const cross = truth.notes.filter((n) => Math.floor(n.tick / barT) !== Math.floor((n.tick + n.dur - 1) / barT));
      check(`${tag}: bar-line ties only in the lowest lower voice, at most one`, cross.every((n) => n.voice === lowest && n.staff === 2 && Math.floor((n.tick + n.dur - 1) / barT) - Math.floor(n.tick / barT) === 1), JSON.stringify(cross.find((n) => n.voice !== lowest)));
      check(`${tag}: sound end after onset, release after onset`, truth.notes.every((n) => n.se_ms >= n.on_ms && n.off_ms > n.on_ms));
      check(`${tag}: divisions per beat`, truth.divisions.every((d) => BT % d === 0));
      if (truth.under44) check(`${tag}: 12/8 under 4/4 ticks are integers`, truth.under44.notes.every((n) => Number.isInteger(n.tick) && Number.isInteger(n.dur)));
      if (spec.countIn) {
        check(`${tag}: 4 count-in taps before the music`, take.taps.length === 4 && take.taps[3] < truth.downbeats_ms[0] + 100);
        const gaps = take.taps.slice(1).map((t, i) => t - take.taps[i]), beat = 60000 / spec.bpm;
        check(`${tag}: taps near the beat`, gaps.every((g) => Math.abs(g - beat) < 200), JSON.stringify(gaps));
      }
      if (spec.pickupBeats) check(`${tag}: pickup notes before bar 0`, truth.notes.some((n) => n.tick < 0));
      if (spec.tempoStep) check(`${tag}: tempo step lands`, Math.abs(60000 / MX.median(truth.nom_ms.slice(-8)) / spec.tempoStep.bpm - 1) < 0.15);
    }
  }

  // family properties the amendments name (LS0 checklist), over the test seeds
  const beatsWith5 = [];
  for (const { take } of G.familySuite("sextuplet")) {
    const BT = take.truth.meter.beatTicks, per = new Map();
    for (const n of take.truth.notes) { const k = Math.floor(n.tick / BT); if (!per.has(k)) per.set(k, new Set()); per.get(k).add(n.tick); }
    const counts = [...per.values()].map((s) => s.size);
    beatsWith5.push(counts.filter((x) => x >= 5).length / counts.length);
  }
  const sext = MX.mean(beatsWith5);
  check("sextuplet family: beats with 5+ onset groups in 10-22% (suite mean)", sext >= 0.10 && sext <= 0.22, sext.toFixed(3));

  let pedalled = 0, early = 0;
  for (const { take } of G.familySuite("pedal")) {
    const down = (t) => { let d = false; for (const p of take.truth.pedal) { if (p.t > t) break; d = p.down; } return d; };
    for (const n of take.truth.notes) { if (n.early) { early++; pedalled++; } else if (down(n.off_ms)) pedalled++; }
  }
  const earlyShare = early / pedalled;
  check("pedal family: 30% of pedalled notes released early (25-35%)", earlyShare >= 0.25 && earlyShare <= 0.35, earlyShare.toFixed(3));

  let bassN = 0, bassLong = 0;
  for (const { take } of G.familySuite("heldBass")) {
    const barMs = (take.truth.beats_ms[take.truth.beats_ms.length - 1] - take.truth.beats_ms[take.truth.lead]) / take.truth.bars;
    // "past a bar" = sounding more than a bar and a quarter: a bar-long bass always overshoots by its pedal lag
    for (const n of take.truth.notes) if (n.voice === 4) { bassN++; if (n.se_ms - n.on_ms > 1.25 * barMs) bassLong++; }
  }
  const ring = bassLong / bassN;
  check("heldBass family: about 20% of bass notes ring past a bar (14-26%)", ring >= 0.14 && ring <= 0.26, ring.toFixed(3));

  const vgap = [];
  for (const { take } of G.familySuite("voiced")) {
    const top = take.truth.notes.filter((n) => n.voice === 1).map((n) => n.vel), rest = take.truth.notes.filter((n) => n.voice !== 1).map((n) => n.vel);
    vgap.push(MX.median(top) - MX.median(rest));
  }
  check("voiced family: top line 15-25 velocity above the rest (median, +-6 noise)", MX.median(vgap) >= 12 && MX.median(vgap) <= 30, JSON.stringify(vgap));

  let t32 = 0, t32Beats = 0;
  for (const { take } of G.familySuite("thirtysecond")) for (const d of take.truth.divisions) { t32Beats++; if (d === 8) t32++; }
  check("thirtysecond family: 32nd beats present", t32 > 0, String(t32));

  const run15 = G.genTapeRun({ seconds: 1.5 }), run4 = G.genTapeRun({ seconds: 4, seed: 2 });
  check("tape runs: 15 and 40 groups at 10 per second", run15.truth.groups === 15 && run4.truth.groups === 40);
  receipts.push({ id: "LS0-families", sextupletBeatsWith5: +sext.toFixed(3), earlyReleaseShare: +earlyShare.toFixed(3), heldBassRingPastBar: +ring.toFixed(3), voicedTopGap: MX.median(vgap), thirtySecondBeats: t32, thirtySecondBeatShare: +(t32 / t32Beats).toFixed(3) });

  // truth rests per voice per bar in pedalled bars (C1 construction: at most the bar-start rest)
  const rv = [];
  for (const { take } of G.familySuite("pedal")) {
    const ped = new Set(take.truth.barInfo.filter((b) => b.pedalledShare >= 0.5).map((b) => b.index));
    rv.push(MX.restsPerVoicePerBar(take.truth.notes, take.truth.meter, { pedalled: ped }).pedalledMedian);
  }
  check("pedal family truth: median rests per voice per pedalled bar <= 1", MX.median(rv) <= 1, JSON.stringify(rv));
}

// -------------------------------------------------------------------------------------- metric helpers ---
{
  const ref = [1000, 1500, 2000, 2500];
  check("fmeasure: identical", MX.fmeasure(ref, ref) === 1);
  check("fmeasure: 80 ms off", MX.fmeasure(ref.map((t) => t + 80), ref) === 0);
  check("fmeasure: 60 ms off", MX.fmeasure(ref.map((t) => t + 60), ref) === 1);
  check("fmeasure: half the beats", Math.abs(MX.fmeasure([1000, 2000], ref) - 2 / 3) < 1e-9);
  const lv = MX.levelsOf([0, 100, 200]);
  check("levelsOf: double level", same(lv.dbl, [0, 50, 100, 150]));

  const meter = { beatTicks: 24, barTicks: 96 };
  const truth = [{ id: 0, tick: 0 }, { id: 1, tick: 12 }, { id: 2, tick: 24 }, { id: 3, tick: 96 }, { id: 4, tick: 104 }];
  let s = MX.scoreTicks(truth, truth, meter);
  check("scoreTicks: truth scores 1", s.onsetsExact === 1 && s.beatsExact === 1 && s.barsOnsetExact === 1 && s.coverage === 1);
  s = MX.scoreTicks(truth.map((n) => (n.id === 4 ? { ...n, tick: 102 } : n)), truth, meter);
  check("scoreTicks: one wrong onset fails its bar and beat", s.onsetsExact === 0.8 && s.barsOnsetExact === 0.5 && Math.abs(s.beatsExact - 2 / 3) < 1e-9, JSON.stringify(s));
  s = MX.scoreTicks(truth.filter((n) => n.id !== 1), truth, meter);
  check("scoreTicks: a missing onset lowers coverage and fails its bar", s.coverage === 0.8 && s.barsOnsetExact === 0.5);
  check("normDiv: sextuplet, triplet, 32nd", MX.normDiv([0, 4, 8], 24) === 6 && MX.normDiv([0, 8, 16], 24) === 3 && MX.normDiv([0, 3], 24) === 8 && MX.normDiv([0, 9], 36) === 4);

  const notes = [{ id: 0, voice: 1, note: 60, tick: 0, dur: 48 }, { id: 1, voice: 1, note: 62, tick: 48, dur: 48 }, { id: 2, voice: 4, note: 36, tick: 0, dur: 144 }];
  check("barsFullyExact: truth", MX.barsFullyExact(notes, notes, meter).barsFullyExact === 1);
  check("barsFullyExact: a shorter note fails its bar", MX.barsFullyExact(notes.map((n) => (n.id === 0 ? { ...n, dur: 24 } : n)), notes, meter).barsFullyExact === 0.5);
  check("barsFullyExact: a tie split differently fails both bars", MX.barsFullyExact(notes.map((n) => (n.id === 2 ? { ...n, dur: 96 } : n)), notes, meter).barsFullyExact === 0);
  check("barsFullyExact: another voice fails", MX.barsFullyExact(notes.map((n) => (n.id === 1 ? { ...n, voice: 2 } : n)), notes, meter).barsFullyExact === 0.5);
  check("durationsExact", MX.durationsExact(notes.map((n) => (n.id === 0 ? { ...n, dur: 24 } : n)), notes).durationsExact === 2 / 3);
  const rv = MX.restsPerVoicePerBar([{ voice: 1, tick: 12, dur: 12 }, { voice: 1, tick: 48, dur: 48 }, { voice: 2, tick: 0, dur: 96 }], meter, { pedalled: new Set([0]) });
  check("restsPerVoicePerBar: leading and inner rests counted, full voice none", rv.voiceBars === 2 && rv.mean === 1 && rv.pedalledMedian === 1, JSON.stringify(rv));

  const bars = [0, 2000, 4000, 6000, 8000];
  const p = MX.rung4Precision([{ start_ms: 10, end_ms: 2030, onsetsExact: true }, { start_ms: 2000, end_ms: 6000, onsetsExact: true }, { start_ms: 6000, end_ms: 8000, onsetsExact: false }], bars, 4);
  check("rung4Precision: level error and wrong onsets fail", p.precision === 1 / 3 && p.shownShare === 0.75, JSON.stringify(p));
  const fr = MX.flipRates([{ bpm: 80 }, { bpm: 120 }, { bpm: 60, mode: "hold" }, { bpm: 60 }, { bpm: 120 }], 1);
  check("flipRates: x1.5 then a hold, then x2", fr.flips === 2 && fr.sesq === 1 && fr.oct === 1, JSON.stringify(fr));
  const bs = MX.bandShares([{ t_ms: 9000, mode: "steady" }, { t_ms: 9250, mode: "free" }, { t_ms: 100, mode: "steady" }]);
  check("bandShares after 8 s", bs.steady === 0.5 && bs.free === 0.5);
  check("accentsPerMinute", MX.accentsPerMinute([1, 2, 3], 1.5) === 2);
}

// ------------------------------------------------------------------------------------------------- LR1 ---
// LR1 measures the tempo-lane configuration (LANE_BEAT_PARAMS), per ls1-rulings.md; `params` swaps in the product
// configuration for the delta reported beside it, and `shown` collects bpmShown samples.
function laneRun(piece, { meter = "auto", onsetParams = LANE_ONSET_PARAMS, withPedals = true, params = LANE_BEAT_PARAMS, shown = null } = {}) {
  const events = G.eventsOf(withPedals ? piece : { ...piece, pedals: [] });
  const endMs = piece.notes[piece.notes.length - 1].t * 1000 + 1000;
  const onTick = shown ? (s) => shown.push({ t_ms: s.t_ms, bpm: s.bpmShown, hold: s.mode === "hold" }) : null;
  const { tracker } = trackEvents(events, { createOnsets, onsetParams, params, options: { meter, trace: true }, endMs, onTick });
  return tracker.trace();
}

if (!quick) {
  const ref = JSON.parse(readFileSync(here("./fixtures/score/lr1_reference.json"), "utf8"));
  const worst = { share: 0, where: "" };
  const cmp = (label, got, want, tol) => {
    const d = Math.abs(got - want);
    if (tol === 0.01 && d > worst.share) { worst.share = d; worst.where = label; }
    check(`LR1 ${label}`, d <= tol + 1e-9, `got ${got.toFixed(4)} want ${want} (|d| ${d.toFixed(4)})`);
  };

  // section 3 tables (s3Compat)
  const t0 = performance.now();
  const inferredBeats = (pc) => laneRun({ notes: pc.notes, pedals: [] }, { withPedals: false }).emittedLag.map((t) => t / 1000);
  const rows = G.s3Suite().map((r) => ({ ...r, ...S3.runPiece(r.piece, { seed: r.seed, inferredBeats }) }));
  const groups = { ALL: rows };
  for (const rub of [0, 1, 2]) groups["rub" + rub] = rows.filter((x) => x.rub === rub);
  for (const m of ["4/4", "3/4", "12/8"]) groups[m] = rows.filter((x) => x.meter === m);
  for (const t of ["ballad", "arp", "mixed"]) groups[t] = rows.filter((x) => x.tex === t);
  for (const sig of [0.015, 0.03, 0.045, 0.06]) groups["jit" + Math.round(sig * 1000) + "ms"] = G.s3JitterSuite(sig).map((r) => S3.runPiece(r.piece, { seed: r.seed }));
  const s3Out = {};
  for (const [name, rs] of Object.entries(groups)) {
    const got = S3.aggregate(rs), want = ref.section3[name];
    s3Out[name] = got;
    for (const k of Object.keys(want)) {
      if (k === "n") { check(`LR1 section3 ${name} n`, got.n === want.n); continue; }
      for (const m of ["acc", "cov", "beat", "bar"]) cmp(`section3 ${name} ${k}.${m}`, got[k][m], want[k][m], 0.01);
    }
  }
  const s3ms = performance.now() - t0;

  // tempo lane table (recommended configuration)
  const t1 = performance.now();
  const tempoRows = (params) => G.tempoSuite().map((r) => {
    const shown = [];
    const tr = laneRun(r.piece, { params, shown });
    const run = { samples: tr.samples.map((x) => ({ t_ms: x.T, bpm: x.bpmT, hold: x.state === "hold" })), emitted_ms: tr.emitted.map((e) => e.t), settled_ms: tr.emittedLag,
      meterLog: tr.meterLog.map((m) => ({ t_ms: m.T, label: m.label })), downs_ms: tr.emitted.filter((e) => e.down === true).map((e) => e.t) };
    const evShown = MX.evalTempo(r.piece.truth, { ...run, samples: shown });
    return { ...r, ...MX.evalTempo(r.piece.truth, run), acc1Shown: evShown.acc1, flipsShown: evShown.flipsPerMin };
  });
  const trows = tempoRows(LANE_BEAT_PARAMS);
  const pick = (rs) => { const f = (k) => MX.mean(rs.map((x) => (typeof x[k] === "boolean" ? +x[k] : x[k]))); return { fb: f("fb"), fbLag: f("fbLag"), fAny: f("fAny"), acc1: f("acc1"), acc1s: f("acc1s"), acc2: f("acc2"), oct: f("octave"), flips: f("flipsPerMin"), meter: f("meterOK"), fdb: f("fdb"), lockT: MX.mean(rs.map((x) => x.lockT).filter((x) => x != null)), never: rs.filter((x) => x.lockT == null).length }; };
  const tOut = { all: pick(trows) };
  for (const rub of [0, 1, 2]) tOut["rub" + rub] = pick(trows.filter((x) => x.rub === rub));
  for (const m of ["4/4", "3/4", "6/8"]) tOut[m] = pick(trows.filter((x) => x.meter === m));
  for (const [name, got] of Object.entries(tOut)) {
    const want = ref.tempoLane[name];
    for (const k of ["fb", "fbLag", "fAny", "acc1", "acc1s", "acc2", "oct", "meter", "fdb"]) cmp(`tempoLane ${name} ${k}`, got[k], want[k], 0.01);
    cmp(`tempoLane ${name} flips/min`, got.flips, want.flips, 0.10);
    cmp(`tempoLane ${name} lockT`, got.lockT, want.lockT, 1.0);
    cmp(`tempoLane ${name} never`, got.never, want.never, 1);
  }
  const conf = {}; trows.forEach((r) => { const k = r.meter + "->" + r.meterFinal; conf[k] = (conf[k] || 0) + 1; });
  const fr = [];
  for (const pc of G.freeSuite()) laneRun(pc).samples.filter((x) => x.T > 8000).forEach((x) => fr.push({ t_ms: x.T, per: x.per }));
  const fb = MX.perBands(fr, 8000);
  for (const k of ["steady", "loose", "free"]) cmp(`tempoLane freeBands ${k}`, fb[k], ref.tempoLane.freeBands[k], 0.01);
  const tms = performance.now() - t1;

  // product delta (ls1-rulings.md, LR1 row): the same suite and meter "auto" under the product defaults (BEAT_PARAMS: no
  // interval across a hold, bpmShown confirmed for a bar). Product minus lane, reported beside LR1, not gated.
  const t2 = performance.now();
  const prows = tempoRows({});
  const productDelta = {};
  for (const name of ["all", "rub0", "rub1", "rub2"]) {
    const sel = (rs) => (name === "all" ? rs : rs.filter((x) => x.rub === +name.slice(3)));
    const a = pick(sel(trows)), b = pick(sel(prows));
    const shownOf = (rs) => ({ acc1: MX.mean(sel(rs).map((x) => x.acc1Shown)), flips: MX.mean(sel(rs).map((x) => x.flipsShown)) });
    productDelta[name] = { ...Object.fromEntries(["acc1", "acc1s", "acc2", "fb", "oct", "flips", "lockT", "never"].map((k) => [k, b[k] - a[k]])), shownLane: shownOf(trows), shownProduct: shownOf(prows) };
  }
  const pms = performance.now() - t2;

  receipts.push({ id: "LR1", config: "LANE_BEAT_PARAMS (tempo-lane configuration, ls1-rulings.md)", section3: { ALL: s3Out.ALL, rub2: s3Out.rub2, jit30ms: s3Out.jit30ms, jit45ms: s3Out.jit45ms }, tempoLane: { all: tOut.all, rub0: tOut.rub0, rub1: tOut.rub1, rub2: tOut.rub2 },
    confusion: conf, freeBands: fb, worstShareDeviation: +worst.share.toFixed(4), worstAt: worst.where, ms: { section3: Math.round(s3ms), tempoLane: Math.round(tms), productDelta: Math.round(pms) } });
  receipts.push({ id: "LR1-productDelta", measured: productDelta, threshold: "reported, not gated (product minus lane)", pass: true });
}

for (const r of receipts) console.log("RECEIPT", JSON.stringify(r, (k, v) => (typeof v === "number" ? Math.round(v * 10000) / 10000 : v)));
console.log(`score_fixtures: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
