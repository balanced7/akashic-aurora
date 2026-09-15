// Node tests for arsenal/web/piano/score/quantize.js, measures.js and the index.js transcriber (slice LS2 of the live
// sheet music plan, research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md sections 3, 6.4-6.5 and 10.2,
// amended by plan-amendments.md C1, C2, C7, C10, C11 and ls1-rulings.md). Zero dependencies, synthetic fixtures only
// (tests/fixtures/score/gen.mjs):
//   node tests/score_quantize.test.mjs                      unit contracts, then receipts LR4a-k
//   node tests/score_quantize.test.mjs --quick              unit contracts only
//   node tests/score_quantize.test.mjs --params '{"d6MinGroups":0}'   receipts under other quantizer params (C2 as written)
// Receipts of record run quantize.js defaults: the C2 alphabet (simple straight {1: 0, 2: 0.5, 4: 1.5, 6: 1.75, 3: 2.0},
// compound {1: 0, 3: 0.5, 6: 1.5, 2: 1.75}) with the d = 6 gate d6MinGroups 5 (ls1-rulings.md LS2 rulings), div8 off.
// Onset groups are onsets.js defaults (the product grouping); scores are the section 3 run's metrics (metrics.mjs
// scoreS3: onsets exact, bars onset-exact, first 5 s skipped) on the section 3 suite, and scoreTicks / barsFullyExact /
// durationsExact on the LS0 families (held-out seeds 71-73). Reported beside the receipts, not gated: the section 3
// tables re-run (live and clean, every beat source, the jitter sweep), the div8 run (C2 decision rule), and C2 as written
// (d6MinGroups 0) as evidence for the ruling.
import * as G from "./fixtures/score/gen.mjs";
import * as MX from "./fixtures/score/metrics.mjs";
import * as S3 from "./fixtures/score/s3ref.mjs";
import { newAudit, auditScore, auditOk, auditLine } from "./fixtures/score/audit.mjs";
import { groupNotes, createOnsets, S3_ONSET_PARAMS } from "../arsenal/web/piano/score/onsets.js";
import { trackEvents } from "../arsenal/web/piano/score/beat.js";
import * as Q from "../arsenal/web/piano/score/quantize.js";
import { createGrid, writeDurations, buildMeasures, barGeometry, lowestLowerVoice } from "../arsenal/web/piano/score/measures.js";
import { createTranscriber, clean, replayInto, SCORE_API, TRANSCRIBER_OPTIONS } from "../arsenal/web/piano/score/index.js";

const argv = process.argv.slice(2);
const quick = argv.includes("--quick");
const pIdx = argv.indexOf("--params");
const PARAMS = pIdx >= 0 ? JSON.parse(argv[pIdx + 1]) : {};
let pass = 0, fail = 0;
const receipts = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

// ------------------------------------------------------------------------------------------ unit contracts ---
{
  const ds = (o) => Q.divisionSet(o).map((x) => x.d);
  check("divisionSet straight order", same(ds({}), [1, 2, 4, 6, 3]));
  check("divisionSet triplet order", same(ds({ feel: "triplet" }), [1, 3, 6, 2, 4]));
  check("divisionSet compound order (feel ignored)", same(ds({ compound: true, feel: "triplet" }), [1, 3, 6, 2]));
  check("divisionSet s3Compat", same(ds({ s3Compat: true, compound: true }), [1, 2, 4, 3]));
  check("divisionSet div8 in simple meters only", same(ds({ div8: true }), [1, 2, 4, 6, 3, 8]) && same(ds({ div8: true, compound: true }), [1, 3, 6, 2]));
  check("lambda straight: 6 at 1.75 between 4 and 3", same(Q.LAMBDAS.straight.map((x) => x[1]), [0, 0.5, 1.5, 1.75, 2.0]));
  check("normalizedDivision", Q.normalizedDivision([0, 8, 16], 24) === 3 && Q.normalizedDivision([0, 4], 24) === 6 && Q.normalizedDivision([0, 18], 36) === 2 && Q.normalizedDivision([0], 36) === 1);

  const beats = [1000, 1600, 2200, 2800];
  const a = Q.assignBeats([900, 1000, 1540, 1580, 2799, 2800], beats);
  check("assignBeats: before the first beat's window is out", a[0] === null);
  check("assignBeats: f > 0.875 belongs to the next beat", a[1].bb === 0 && a[1].f === 0 && a[2].bb === 1 && Math.abs(a[2].f + 60 / 600) < 1e-9 && a[3].bb === 1 && Math.abs(a[3].f + 20 / 600) < 1e-9, JSON.stringify(a));
  check("assignBeats: no beat after the last one to move to, and the last beat time closes the grid", a[4] === null && a[5] === null);

  const set = Q.divisionSet({}), sig = 40;
  const at = (fs) => fs.map((f) => ({ f }));
  let r = Q.divideBeat(at([0, 0.25, 0.5, 0.75]), 600, { set, sigma: sig });
  check("divideBeat: four 16ths -> d 4", r.d === 4 && same(r.ks, [0, 1, 2, 3]) && !r.loose);
  check("d6MinGroups: 5 by default (ls1-rulings.md LS2 rulings), simple meters only", Q.QUANT_PARAMS.d6MinGroups === 5 && set.find((x) => x.d === 6).minGroups === 5
    && Q.divisionSet({ feel: "triplet" }).find((x) => x.d === 6).minGroups === 5 && Q.divisionSet({ compound: true }).every((x) => !x.minGroups) && Q.divisionSet({ s3Compat: true }).every((x) => !x.minGroups));
  r = Q.divideBeat(at([0, 1 / 3, 2 / 3]), 600, { set, sigma: sig });
  check("divideBeat: a triplet under straight is d 3 (d 6 needs 5 groups)", r.d === 3 && same(r.ks, [0, 1, 2]), JSON.stringify(r));
  r = Q.divideBeat(at([0, 1 / 3, 2 / 3]), 600, { set: Q.divisionSet({ d6MinGroups: 0 }), sigma: sig, params: { ...Q.QUANT_PARAMS, d6MinGroups: 0 } });
  check("divideBeat: C2 as written (d6MinGroups 0) decides the triplet on d 6 at the triplet's slots", r.d === 6 && same(r.ks, [0, 2, 4]));
  r = Q.divideBeat(at([0, 1 / 3, 2 / 3]), 600, { set: Q.divisionSet({ feel: "triplet" }), sigma: sig });
  check("divideBeat: a triplet under triplet feel -> d 3", r.d === 3);
  r = Q.divideBeat(at([0, 1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6]), 600, { set, sigma: sig });
  check("divideBeat: six sextuplet groups -> d 6", r.d === 6 && same(r.ks, [0, 1, 2, 3, 4, 5]) && !r.loose);
  r = Q.divideBeat(at([0, 0.5]), 600, { set, sigma: sig, prev: 4, back: 4 });
  check("divideBeat: continuity and bar-back keep d 4 for two 8ths", r.d === 4 && same(r.ks, [0, 2]));
  r = Q.divideBeat([{ f: 0, t: 0 }, { f: 0.04, t: 24 }], 600, { set, sigma: sig });
  check("divideBeat: a 24 ms collision is explained (not loose)", r.collisions === 1 && !r.loose);
  r = Q.divideBeat(at([0, 0.1, 0.3, 0.45, 0.6, 0.72, 0.9 - 0.1]), 600, { set, sigma: 15 });
  check("divideBeat: seven groups in a beat are loose", r.loose);
  r = Q.divideBeat(at([0, 0.5, 0.52]), 600, { set: Q.divisionSet({ d6MinGroups: 5 }), sigma: sig, params: { ...Q.QUANT_PARAMS, d6MinGroups: 5 } });
  check("divideBeat: d6MinGroups 5 keeps d 6 off a 3-group beat", r.d !== 6);

  const ls = Q.looseSlots([0.02, 0.2, 0.4, 0.6, 0.8]);
  check("looseSlots: five groups keep time order on distinct d 6 slots", ls.every((k, i) => i === 0 || k > ls[i - 1]) && ls[4] <= 5, JSON.stringify(ls));
  const l8 = Q.looseSlots([0, 0.1, 0.12, 0.3, 0.5, 0.52, 0.7, 0.9]);
  check("looseSlots: eight groups merge the closest pairs into 6 slots", new Set(l8).size === 6 && l8[1] === l8[2] && l8[4] === l8[5] && l8.every((k, i) => i === 0 || k >= l8[i - 1]), JSON.stringify(l8));
  check("exportPositions: a loose beat goes to the d 6 grid", same(Q.exportPositions({ loose: true, pos: [0, 0] }, at([0, 0.3]), 24), [0, 8]));

  // rewind: decisions from a checkpoint equal one pass over the final beats
  const items = [[0, 0.5], [0, 0.25, 0.5, 0.75], [0.02], [0, 1 / 3, 2 / 3], [0, 0.5], [0.5]].map(at);
  const one = Q.createLiveQuantizer(), outA = items.map((it, i) => one.decide(i, it, 700));
  const two = Q.createLiveQuantizer();
  items.forEach((it, i) => two.decide(i, it, 700));
  two.rewind(2);
  two.decide(2, at([0.3]), 700);
  two.rewind(2);
  const outB = items.slice(2).map((it, i) => two.decide(i + 2, it, 700));
  check("live quantizer: rewind restores sigma and the previous division", same(outA.slice(2).map((x) => [x.d, x.ks, x.sigma]), outB.map((x) => [x.d, x.ks, x.sigma])) && Math.abs(one.sigma() - two.sigma()) < 1e-12);

  // measures: the C1 cases on a hand-built bar (4/4, 600 ms beats, voice 1 upper, voice 4 bass)
  const bts = Array.from({ length: 13 }, (_, k) => 1000 + 600 * k);
  const grid = createGrid(bts, { origin: 0, beatTicks: 24 });
  const meter = { beatTicks: 24, barTicks: 96, compound: false };
  const ns = [
    { id: 1, note: 72, tick: 0, on_ms: 1000, off_ms: 1250, se_ms: 1250, voice: 1, staff: 1 },      // dry, released at 10/24 of a beat
    { id: 2, note: 74, tick: 24, on_ms: 1600, off_ms: 2180, se_ms: 2180, voice: 1, staff: 1 },     // dry, legato fill to 48
    { id: 3, note: 76, tick: 48, on_ms: 2200, off_ms: 2350, se_ms: 2790, voice: 1, staff: 1 },     // pedal down at release, rings to 2790 -> fill to 72
    { id: 4, note: 77, tick: 72, on_ms: 2800, off_ms: 2900, se_ms: 3040, voice: 1, staff: 1 },     // pedal down, lifted early -> snap 3040 to 84 (d 2 beat), rest
    { id: 8, note: 60, tick: 84, on_ms: 3100, off_ms: 3350, se_ms: 3350, voice: 2, staff: 1 },     // makes beat 3 a d = 2 beat
    { id: 5, note: 79, tick: 96, on_ms: 3400, off_ms: 3500, se_ms: 3500, voice: 1, staff: 1 },
    { id: 6, note: 36, tick: 0, on_ms: 990, off_ms: 1500, se_ms: 4600, voice: 4, staff: 2 },       // held bass rings to 4600 (tick 144), next bar empty before its midpoint -> tie
    { id: 7, note: 38, tick: 168, on_ms: 5200, off_ms: 5500, se_ms: 5500, voice: 4, staff: 2 },
  ];
  const pedal = [{ t_ms: 2300, down: true }, { t_ms: 3040, down: false }, { t_ms: 3060, down: true }, { t_ms: 4600, down: false }];
  const dd = writeDurations(ns, { grid, meter, pedal });
  const got = Object.fromEntries([...dd].map(([id, x]) => [id, x.dur]));
  check("writeDurations: dry release snapped forward to the beat's division", got[1] === 24 && dd.get(1).rule === "dry", JSON.stringify(dd.get(1)));
  check("writeDurations: dry legato fill to the next onset", got[2] === 24);
  check("writeDurations: pedal ring to the next onset (case 2)", got[3] === 24 && dd.get(3).rule === "pedal");
  check("writeDurations: pedal lifted early snaps the sound end, then a rest", got[4] === 12, JSON.stringify(dd.get(4)));
  check("writeDurations: held bass ends at its sound end and ties once over an empty half bar (C7)", got[6] === 144 && dd.get(6).tied, JSON.stringify(dd.get(6)));
  const single = writeDurations([{ id: 1, note: 77, tick: 72, on_ms: 2800, off_ms: 2900, se_ms: 3040, voice: 1, staff: 1 }, { id: 2, note: 79, tick: 96, on_ms: 3400, off_ms: 3500, se_ms: 3500, voice: 1, staff: 1 }], { grid, meter, pedal });
  check("writeDurations: a one-onset beat is a d = 1 beat, so the early lift keeps one slot (a whole beat)", single.get(1).dur === 24, JSON.stringify(single.get(1)));
  check("lowestLowerVoice", lowestLowerVoice(ns) === 4);
  const bars = buildMeasures(ns.map((n) => ({ ...n, dur: got[n.id] })), { meter });
  const b0 = bars.find((b) => b.index === 0), b1 = bars.find((b) => b.index === 1);
  check("buildMeasures: bar-line tie pieces", b0.voices.find((v) => v.voice === 4).notes[0].tieStart && b1.voices.find((v) => v.voice === 4).notes[0].tieStop && b1.voices.find((v) => v.voice === 4).notes[0].dur === 48);
  check("buildMeasures: the early pedal lift leaves a rest", b0.voices.find((v) => v.voice === 1).rests.some((x) => x.pos === 84 && x.dur === 12), JSON.stringify(b0.voices.find((v) => v.voice === 1).rests));
  const geo = barGeometry(96, [-24, 0, 96]);
  check("barGeometry: a pickup bar and extension", geo.indexAt(-10) === 0 && geo.indexAt(0) === 1 && geo.indexAt(200) === 3 && geo.end(0) === 0 && geo.start(3) === 192);

  // measures: rhythm spelling (plan 6.5, transcription.md T4). Every note piece and rest is one written value; notes are
  // tied at the strongest metric line, dotted values start on the beat or the main subdivision, rests follow the beats.
  const M44 = { beatTicks: 24, barTicks: 96, compound: false }, M34 = { beatTicks: 24, barTicks: 72, compound: false };
  const M68 = { beatTicks: 36, barTicks: 72, compound: true }, M128 = { beatTicks: 36, barTicks: 144, compound: true };
  const sp = (ns, m) => {
    const b = buildMeasures(ns.map((x, i) => ({ id: i + 1, note: 60 + i, voice: 1, staff: 1, ...x })), { meter: m })[0], v = b.voices[0];
    const ty = (p) => p.type + ".".repeat(p.dots);
    return { notes: v.notes.map((p) => [p.id, p.pos, p.dur, ty(p), (p.tieStop ? "<" : "") + (p.tieStart ? ">" : "")]), rests: v.rests.map((r) => [r.pos, r.dur, ty(r)]), tuplets: b.tuplets.map((t) => [t.beat, t.actual, t.normal]) };
  };
  let w = sp([{ tick: 0, dur: 30 }, { tick: 30, dur: 18 }, { tick: 60, dur: 20 }], M44);
  check("spelling: the LS2 r1 failing case is tied into values (off-beat dotted 8th -> 16th + 8th; a triplet end stays in its bracket)",
    same(w.notes, [[1, 0, 24, "quarter", ">"], [1, 24, 6, "16th", "<"], [2, 30, 6, "16th", ">"], [2, 36, 12, "eighth", "<"], [3, 60, 12, "eighth", ">"], [3, 72, 8, "eighth", "<"]])
    && same(w.rests, [[48, 12, "eighth"], [80, 8, "eighth"], [88, 8, "eighth"]]) && same(w.tuplets, [[3, 3, 2]]), JSON.stringify(w));
  w = sp([{ tick: 24, dur: 72 }], M44);
  check("spelling: 4/4 dotted half on beat 2 shows beat 3 (quarter + half)", same(w.notes, [[1, 24, 24, "quarter", ">"], [1, 48, 48, "half", "<"]]) && same(w.rests, [[0, 24, "quarter"]]), JSON.stringify(w));
  w = sp([{ tick: 24, dur: 48 }], M44);
  check("spelling: 4/4 half on beat 2 stays whole", same(w.notes, [[1, 24, 48, "half", ""]]) && same(w.rests, [[0, 24, "quarter"], [72, 24, "quarter"]]), JSON.stringify(w));
  w = sp([{ tick: 0, dur: 12 }, { tick: 12, dur: 24 }, { tick: 36, dur: 12 }, { tick: 48, dur: 12 }, { tick: 60, dur: 36 }], M44);
  check("spelling: syncopated quarter and dotted quarter after an eighth stay single values", same(w.notes.map((x) => x[3] + x[4]), ["eighth", "quarter", "eighth", "eighth", "quarter."]), JSON.stringify(w));
  w = sp([{ tick: 36, dur: 36 }], M44);
  check("spelling: 4/4 off-beat note crossing beat 3 is split there", same(w.notes, [[1, 36, 12, "eighth", ">"], [1, 48, 24, "quarter", "<"]]), JSON.stringify(w));
  w = sp([{ tick: 6, dur: 18 }], M44);
  check("spelling: rests after an off-beat note follow the beats (4/4 half rest on beats 3-4)", same(w.notes, [[1, 6, 6, "16th", ">"], [1, 12, 12, "eighth", "<"]]) && same(w.rests, [[0, 6, "16th"], [24, 24, "quarter"], [48, 48, "half"]]), JSON.stringify(w));
  w = sp([{ tick: 0, dur: 60 }], M34);
  check("spelling: 3/4 note of 2.5 beats -> half + eighth; rests are not dotted and do not cross beats", same(w.notes, [[1, 0, 48, "half", ">"], [1, 48, 12, "eighth", "<"]]) && same(w.rests, [[60, 12, "eighth"]]) && same(sp([{ tick: 0, dur: 24 }], M34).rests, [[24, 24, "quarter"], [48, 24, "quarter"]]), JSON.stringify(w));
  w = sp([{ tick: 0, dur: 48 }], M68);
  check("spelling: 6/8 note crossing the beat not ending on a beat -> dotted quarter + eighth; eighth rests from the 2nd eighth", same(w.notes, [[1, 0, 36, "quarter.", ">"], [1, 36, 12, "eighth", "<"]]) && same(w.rests, [[48, 12, "eighth"], [60, 12, "eighth"]]), JSON.stringify(w));
  check("spelling: 12/8 dotted half on beat 2 ending by beat 4 stays; to the bar end it shows the half bar",
    same(sp([{ tick: 36, dur: 72 }], M128).notes, [[1, 36, 72, "half.", ""]]) && same(sp([{ tick: 36, dur: 108 }], M128).notes, [[1, 36, 36, "quarter.", ">"], [1, 72, 72, "half.", "<"]]));
  check("spelling: 12/8 rests are whole dotted beats", same(sp([{ tick: 0, dur: 36 }], M128).rests, [[36, 36, "quarter."], [72, 72, "half."]]));
  w = sp([{ tick: 0, dur: 8 }, { tick: 8, dur: 8 }, { tick: 16, dur: 32 }], M44);
  check("spelling: a note leaving a triplet beat is tied at the beat (one bracket per beat)", same(w.notes.slice(2), [[3, 16, 8, "eighth", ">"], [3, 24, 24, "quarter", "<"]]) && same(w.tuplets, [[0, 3, 2]]), JSON.stringify(w));
  w = sp([{ tick: 0, dur: 18 }, { tick: 18, dur: 18 }], M68);
  check("spelling: 6/8 duplet eighths are eighths under a 2:3 bracket", same(w.notes.map((x) => x[3]), ["eighth", "eighth"]) && same(w.tuplets, [[0, 2, 3]]), JSON.stringify(w));

  // construction check on scores: every piece is a value by an independent reading of the T4 rules; each note's pieces
  // tile its written duration with ties; every bar-line tie leads into the next bar of the same segment, which holds the
  // continuation (tieStop at position 0); a note crosses at most one bar line (C7); a continuation never overlaps a later
  // onset in its voice
  // (tests/fixtures/score/audit.mjs, shared with the S1..Sn sessions check in tests/score_settle.test.mjs)
  // oracle beats and truth voices: clean() copies of the pedal, held-bass and sextuplet families
  const bad = newAudit();
  for (const family of ["pedal", "heldBass", "sextuplet"]) for (const { take, spec } of G.familySuite(family)) {
    const T = take.truth, byKey = new Map(T.notes.map((n) => [n.note + "|" + Math.round(n.on_ms), n]));
    auditScore(bad, clean(take.events, { beats: T.beats_ms, one: T.downbeats_ms[0], meter: spec.meter, voiceOf: (n) => byKey.get(n.note + "|" + n.t) }), family);
  }
  check("spelling on clean() copies: every note piece and rest is one written value (T4), pieces tile each note, bar ties lead into their continuation", bad.notes > 15000 && auditOk(bad), JSON.stringify(bad));
  console.log("SPELLING", JSON.stringify(auditLine(bad)));
  // inferred beats (rung 4, beat.js defaults, meter set to the piece's meter), the bench voice split: the live transcriber
  // (replayed on the tick clock, then finished) and clean() on the held-out tempo suite and on every LS0 family. Segments
  // close on holds and source switches, and phase corrections make partial bars, so bar-line ties meet segment ends here.
  const badInf = { live: newAudit(), clean: newAudit() };
  let settledViolations = 0;
  const infTakes = [...G.tempoSuite().map((r) => ({ family: "tempo", events: G.eventsOf(r.piece), meter: r.meter })), ...G.FAMILIES.flatMap((f) => G.familySuite(f).map(({ take, spec }) => ({ family: f, events: take.events, meter: spec.meter })))];
  for (const x of infTakes) {
    const trI = createTranscriber({ options: { meter: x.meter } });
    replayInto(trI, x.events);
    trI.finish();
    settledViolations += trI.stats().violations;
    auditScore(badInf.live, trI.score(), x.family);
    auditScore(badInf.clean, clean(x.events, { meter: x.meter }), x.family);
  }
  check("spelling on inferred beats (tempo suite and every family, live and clean): values, tiles, bar ties lead into their continuation, one bar line per note",
    badInf.live.notes > 50000 && badInf.clean.notes > 50000 && auditOk(badInf.live) && auditOk(badInf.clean) && settledViolations === 0, JSON.stringify({ live: badInf.live, clean: badInf.clean, settledViolations }));
  console.log("SPELLING-INFERRED", JSON.stringify({ takes: infTakes.length, live: auditLine(badInf.live), clean: auditLine(badInf.clean), settledViolations }));
  {
    // the verifier's case: tempo suite piece 0 (4/4 ballad, rub 0, seed 37), live; its last bar's held bass no longer ties
    // into a bar that does not exist
    const pc = G.tempoSuite()[0];
    const trP = createTranscriber({ options: { meter: "4/4" } });
    replayInto(trP, G.eventsOf(pc.piece));
    trP.finish();
    const sP = trP.score(), lastIdx = Math.max(...sP.measures.map((m) => m.index)), lastM = sP.measures.find((m) => m.index === lastIdx);
    const ties = lastM.voices.flatMap((v) => v.notes.filter((p) => p.barTie));
    const lowNotes = sP.notes.filter((n) => n.bar === lastIdx && n.staff === 2);
    check("held bass: the last bar of tempo piece 0 carries no bar-line tie and its notes end in the bar", pc.meter === "4/4" && pc.tex === "ballad" && pc.rub === 0 && pc.seed === 37 && ties.length === 0 && lowNotes.every((n) => n.pos + n.dur <= lastM.barTicks), JSON.stringify({ lastIdx, ties, lowNotes: lowNotes.map((n) => [n.pos, n.dur]) }));
  }
  {
    // a segment close: fixed beats run two bars past the last onset; the held bass rings over an empty next bar (a C7 tie
    // inside the segment), but that bar is dropped at the close, so the end is capped at the last bar with an onset
    const beatsC = Array.from({ length: 16 }, (_, k) => 1000 + 600 * k);
    const evC = [
      { t_ms: 1000, kind: "on", note: 36, vel: 70 }, { t_ms: 1000, kind: "on", note: 72, vel: 70 },
      { t_ms: 1300, kind: "off", note: 72 }, { t_ms: 1300, kind: "sound_end", note: 72, by: "release" },
      { t_ms: 1400, kind: "pedal", down: true, value: 100 }, { t_ms: 1500, kind: "off", note: 36 },
      { t_ms: 4600, kind: "pedal", down: false, value: 0 }, { t_ms: 4600, kind: "sound_end", note: 36, by: "pedal" },
    ];
    for (const [kind, sC] of [["clean", clean(evC, { beats: beatsC, one: 1000, meter: "4/4" })], ["live", (() => { const t = createTranscriber({ options: { meter: "4/4", beats: beatsC, one: 1000 } }); replayInto(t, evC); t.finish(); return t.score(); })()]]) {
      const bass = sC.notes.find((n) => n.note === 36), pieces = sC.measures.flatMap((m) => m.voices.flatMap((v) => v.notes.filter((p) => p.note === 36).map((p) => [m.index, p.pos, p.dur, p.barTie])));
      check(`held bass at a segment close (${kind}): capped at the last bar with an onset, no tie`, same(sC.measures.map((m) => m.index), [0]) && bass && bass.dur === 96 && same(pieces, [[0, 0, 96, false]]), JSON.stringify({ bars: sC.measures.map((m) => m.index), bass, pieces }));
    }
  }

  // transcriber and clean(): API surface and monotonic clock
  const tr = createTranscriber();
  tr.tick(1000);
  check("transcriber: tick() throws when the clock goes back", (() => { try { tr.tick(999); return false; } catch (e) { return e instanceof RangeError; } })());
  const take = G.genTake({ meter: "4/4", texture: "ballad", seed: 9, bars: 8, rub: 0 });
  const truthKey = new Map(take.truth.notes.map((n) => [n.note + "|" + Math.round(n.on_ms), n]));
  const sc = clean(take.events, { beats: take.truth.beats_ms, one: take.truth.downbeats_ms[0], meter: "4/4", voiceOf: (n) => truthKey.get(n.note + "|" + n.t) });
  check("clean(): score shape", sc.api === SCORE_API && sc.kind === "clean" && sc.tpq === 24 && sc.rhythm === "jam" && sc.measures.every((m) => m.state === "settled") && sc.notes.length + sc.tape.length === take.truth.notes.length, JSON.stringify({ n: sc.notes.length, tape: sc.tape.length, rhythm: sc.rhythm }));
  const sc2 = clean(take.events, { beats: take.truth.beats_ms, one: take.truth.downbeats_ms[0], meter: "4/4", voiceOf: (n) => truthKey.get(n.note + "|" + n.t) });
  check("clean(): deterministic, a new transcriber per call", same(sc.notes.map((n) => [n.tick, n.dur]), sc2.notes.map((n) => [n.tick, n.dur])));
}

// s3Compat identity: quantize.js in s3Compat mode equals the section 3 quantizer (s3ref.mjs) position for position
{
  let mism = 0, total = 0;
  for (const r of G.s3Suite()) {
    const pc = r.piece, beatsMs = pc.beats.map((t) => t * 1000);
    const ref = S3.groupsOf(pc.notes); S3.assign(ref, pc.beats);
    const L = S3.quantLive(ref, pc.beats, pc.bpb, S3.S3_OPTIONS); S3.quantClean(ref, pc.beats, pc.bpb, S3.S3_OPTIONS, L.div, L.sigma);
    const gs = S3.groupsOf(pc.notes), asg = Q.assignBeats(gs.map((g) => g.t * 1000), beatsMs), byBeat = new Map();
    gs.forEach((g, i) => { if (asg[i]) { g.bb = asg[i].bb; g.f = asg[i].f; if (!byBeat.has(g.bb)) byBeat.set(g.bb, []); byBeat.get(g.bb).push(g); } else g.bb = null; });
    const q = Q.createLiveQuantizer({ beatTicks: 12, beatsPerBar: pc.bpb, params: { s3Compat: true } });
    const keys = [...byBeat.keys()].sort((a, b) => a - b);
    for (const bb of keys) { const its = byBeat.get(bb), d = q.decide(bb, its.map((g) => ({ f: g.f })), beatsMs[bb + 1] - beatsMs[bb]); its.forEach((g, k) => { g.live = bb * 12 + d.pos[k]; }); }
    const cd = Q.cleanDivisions(keys.map((bb) => ({ bb, items: byBeat.get(bb).map((g) => ({ f: g.f })), P: beatsMs[bb + 1] - beatsMs[bb] })), { beatTicks: 12, beatsPerBar: pc.bpb, params: { s3Compat: true }, liveDiv: q.divisions(), sigma: q.sigma() });
    for (const bb of keys) byBeat.get(bb).forEach((g, k) => { g.clean = bb * 12 + cd.get(bb).pos[k]; });
    ref.forEach((g, i) => { total++; if (g.bb !== gs[i].bb || (g.bb != null && (g.live !== gs[i].live || g.clean !== gs[i].clean))) mism++; });
  }
  check("s3Compat: quantize.js equals the section 3 quantizer (live and clean, 81 pieces)", mism === 0 && total > 15000, `${mism} of ${total}`);
}

// -------------------------------------------------------------------------------------------- harnesses ---
// One section 3 piece: product onset groups, the quantizer under `params`, on beats (s). Scores with the run's metric.
function s3Piece(pc, params, { beatsSec = pc.beats, feel = "straight", meterAs = null, onsetParams = {} } = {}) {
  const meter = meterAs || pc.meter, comp = meter === "12/8" && !params.s3Compat, BT = params.s3Compat ? 12 : comp ? 36 : 24;
  const evs = pc.notes.map((n) => ({ t_ms: n.t * 1000, kind: "on", note: n.note, vel: n.vel }));
  const posOf = new Map(pc.notes.map((n) => [n.t * 1000 + "|" + n.note, n.pos]));
  const groups = groupNotes(evs, onsetParams).map((g) => ({ t: g.t, pos: posOf.get(g.notes[0].t + "|" + g.notes[0].note), grace: !!g.grace }));
  const beatsMs = beatsSec.map((t) => t * 1000), asg = Q.assignBeats(groups.map((g) => g.t), beatsMs), byBeat = new Map();
  groups.forEach((g, i) => { g.bb = asg[i] ? asg[i].bb : null; if (asg[i]) { g.f = asg[i].f; if (!byBeat.has(g.bb)) byBeat.set(g.bb, []); byBeat.get(g.bb).push(g); } });
  const q = Q.createLiveQuantizer({ beatTicks: BT, beatsPerBar: pc.bpb, compound: comp, feel, params });
  const keys = [...byBeat.keys()].sort((a, b) => a - b);
  let looseN = 0, d6raw = 0;
  const ms0 = performance.now();
  for (const bb of keys) {
    const its = byBeat.get(bb), d = q.decide(bb, its.map((g) => ({ f: g.f, t: g.t, grace: g.grace })), beatsMs[bb + 1] - beatsMs[bb]);
    if (d.loose) looseN++; if (d.d === 6) d6raw++;
    its.forEach((g, k) => { g.live = bb * 12 + d.pos[k] * 12 / BT; });
  }
  const ms1 = performance.now();
  const list = keys.map((bb) => ({ bb, items: byBeat.get(bb).map((g) => ({ f: g.f, t: g.t, grace: g.grace })), P: beatsMs[bb + 1] - beatsMs[bb] }));
  const cd = Q.cleanDivisions(list, { beatTicks: BT, beatsPerBar: pc.bpb, compound: comp, feel, params, liveDiv: q.divisions(), sigma: q.sigma() });
  for (const it of list) { const pos = Q.exportPositions(cd.get(it.bb), it.items, BT); byBeat.get(it.bb).forEach((g, k) => { g.clean = it.bb * 12 + pos[k] * 12 / BT; }); }
  const ms2 = performance.now();
  const S = [0, 3, 4, 6, 8, 9, 12];
  for (const g of groups) if (g.bb != null) { const x = g.f * 12; g.naive = g.bb * 12 + S.reduce((m, s) => (Math.abs(s - x) < Math.abs(m - x) ? s : m), 0); }
  const gs = groups.map((g) => ({ t: g.t / 1000, pos: g.pos, bb: g.bb, live: g.live, clean: g.clean, naive: g.naive }));
  // false d = 6 (normalized estimated positions) on non-empty beats whose truth normalizes to 1-4, simple meters, after 5 s
  let f6 = 0, ne = 0;
  if (!comp && !params.s3Compat) {
    const tB = new Map(), eB = new Map();
    for (const n of pc.notes) { if (n.t < 5) continue; const k = Math.floor(n.pos / 12); if (!tB.has(k)) tB.set(k, new Set()); tB.get(k).add((n.pos % 12) * 2); }
    for (const g of gs) if (g.bb != null) { const k = Math.floor(g.live / 12); if (!eB.has(k)) eB.set(k, []); eB.get(k).push((g.live - k * 12) * 2); }
    for (const [k, s] of tB) { if (MX.normDiv([...s], 24) > 4) continue; ne++; const e = eB.get(k); if (e && MX.normDiv(e, 24) === 6) f6++; }
  }
  return { live: MX.scoreS3(gs, "live", pc.bpb), clean: MX.scoreS3(gs, "clean", pc.bpb), naive: MX.scoreS3(gs, "naive", pc.bpb), f6, ne, loose: looseN, beats: keys.length, d6raw, msLive: (ms1 - ms0) / pc.bars, msClean: (ms2 - ms1) / pc.bars };
}
const noisyBeats = (pc, seed, e) => { const r = G.rng(seed + 99), b = pc.beats.map((t) => t + e * G.gauss(r)); for (let i = 1; i < b.length; i++) if (b[i] <= b[i - 1] + 0.05) b[i] = b[i - 1] + 0.05; return b; };
const agg = (rows, key) => ({ acc: MX.mean(rows.map((x) => x[key].acc)), bar: MX.mean(rows.map((x) => x[key].barOk)), beat: MX.mean(rows.map((x) => x[key].beatOk)), cov: MX.mean(rows.map((x) => x[key].cov)) });

// An LS0 family take under oracle beats: scoreTicks per note (truth ids), optionally under 4/4 for 12/8 (under44).
function takePiece(take, params, { meterAs = null, feel = "straight" } = {}) {
  const T = take.truth, under = meterAs === "4/4" && T.meter.compound;
  const comp = !under && T.meter.compound, BT = under ? 24 : T.meter.beatTicks, barT = under ? 96 : T.meter.barTicks;
  const byKey = new Map(T.notes.map((n) => [n.note + "|" + Math.round(n.on_ms), n]));
  const groups = groupNotes(take.events), asg = Q.assignBeats(groups.map((g) => g.t), T.beats_ms), byBeat = new Map();
  groups.forEach((g, i) => { g.bb = asg[i] ? asg[i].bb : null; g.tick = null; if (asg[i]) { g.f = asg[i].f; if (!byBeat.has(g.bb)) byBeat.set(g.bb, []); byBeat.get(g.bb).push(g); } });
  const q = Q.createLiveQuantizer({ beatTicks: BT, beatsPerBar: T.meter.tactus, compound: comp, feel, params });
  for (const bb of [...byBeat.keys()].sort((a, b) => a - b)) { const its = byBeat.get(bb), d = q.decide(bb, its.map((g) => ({ f: g.f, t: g.t, grace: !!g.grace })), T.beats_ms[bb + 1] - T.beats_ms[bb]); its.forEach((g, k) => { g.tick = (bb - T.lead) * BT + d.pos[k]; }); }
  const est = [];
  for (const g of groups) for (const n of g.notes) { const tn = byKey.get(n.note + "|" + n.t); if (tn) est.push({ id: tn.id, tick: g.tick }); }
  return MX.scoreTicks(est, under ? T.under44.notes : T.notes, { beatTicks: BT, barTicks: barT });
}

function lr4Suite(params) {
  const rows = G.s3Suite().map((r) => ({ ...r, o: s3Piece(r.piece, params), t30: s3Piece(r.piece, params, { beatsSec: noisyBeats(r.piece, r.seed, 0.03) }), t45: s3Piece(r.piece, params, { beatsSec: noisyBeats(r.piece, r.seed, 0.045) }) }));
  const jit = Object.fromEntries([0.015, 0.03, 0.045, 0.06].map((sig) => [Math.round(sig * 1000), G.s3JitterSuite(sig).map((r) => ({ ...r, o: s3Piece(r.piece, params), t30: s3Piece(r.piece, params, { beatsSec: noisyBeats(r.piece, r.seed, 0.03) }) }))]));
  const f6 = rows.reduce((s, x) => s + x.o.f6, 0) / Math.max(1, rows.reduce((s, x) => s + x.o.ne, 0));
  const sext = G.familySuite("sextuplet").map((x) => takePiece(x.take, params));
  const c44 = G.familySuite("compound44");
  const kS = c44.map((x) => takePiece(x.take, params, { meterAs: "4/4", feel: "straight" })), kT = c44.map((x) => takePiece(x.take, params, { meterAs: "4/4", feel: "triplet" })), kC = c44.map((x) => takePiece(x.take, params));
  const s128 = rows.filter((x) => x.meter === "12/8");
  const t = (a, k) => MX.mean(a.map((x) => x[k]));
  return {
    rows, jit, f6,
    LR4a: agg(rows.map((x) => x.o), "live"), LR4aClean: agg(rows.map((x) => x.o), "clean"),
    LR4b: agg(rows.filter((x) => x.rub === 2).map((x) => x.o), "live"),
    LR4c: agg(rows.map((x) => x.t30), "live"),
    LR4d: agg(jit[45].map((x) => x.o), "live"),
    LR4e: { live: agg(jit[30].map((x) => x.o), "live").bar, naive: agg(jit[30].map((x) => x.o), "naive").bar },
    LR4j: { onsetsExact: t(sext, "onsetsExact"), barsOnsetExact: t(sext, "barsOnsetExact"), falseD6: f6, rawD6Share: rows.reduce((s, x) => s + x.o.d6raw, 0) / rows.reduce((s, x) => s + x.o.beats, 0) },
    LR4k: { straight: { onsetsExact: t(kS, "onsetsExact"), barsOnsetExact: t(kS, "barsOnsetExact") }, triplet: { onsetsExact: t(kT, "onsetsExact"), barsOnsetExact: t(kT, "barsOnsetExact") },
      s3_128_compound: agg(s128.map((x) => x.o), "live"), family128_compound: { onsetsExact: t(kC, "onsetsExact"), barsOnsetExact: t(kC, "barsOnsetExact") } },
    loose: { beats: rows.reduce((s, x) => s + x.o.loose, 0), of: rows.reduce((s, x) => s + x.o.beats, 0) },
    msPerBar: { live: MX.mean(rows.map((x) => x.o.msLive)), clean: MX.mean(rows.map((x) => x.o.msClean)) },
  };
}
const r4 = (v) => (typeof v === "number" ? Math.round(v * 10000) / 10000 : v);
function tables(S) {
  const out = {};
  const groups = { ALL: S.rows };
  for (const rub of [0, 1, 2]) groups["rub" + rub] = S.rows.filter((x) => x.rub === rub);
  for (const m of ["4/4", "3/4", "12/8"]) groups[m] = S.rows.filter((x) => x.meter === m);
  for (const [name, rs] of Object.entries(groups)) out[name] = { naive: agg(rs.map((x) => x.o), "naive"), live: agg(rs.map((x) => x.o), "live"), clean: agg(rs.map((x) => x.o), "clean"), t30Live: agg(rs.map((x) => x.t30), "live"), t30Clean: agg(rs.map((x) => x.t30), "clean"), t45Live: agg(rs.map((x) => x.t45), "live"), t45Clean: agg(rs.map((x) => x.t45), "clean") };
  for (const [ms, rs] of Object.entries(S.jit)) out["jit" + ms + "ms"] = { naive: agg(rs.map((x) => x.o), "naive"), live: agg(rs.map((x) => x.o), "live"), clean: agg(rs.map((x) => x.o), "clean"), t30Live: agg(rs.map((x) => x.t30), "live") };
  const slim = (x) => Object.fromEntries(Object.entries(x).map(([k, v]) => [k, `${(v.acc * 100).toFixed(1)} / ${(v.bar * 100).toFixed(1)}`]));
  return Object.fromEntries(Object.entries(out).map(([k, v]) => [k, slim(v)]));
}

// ------------------------------------------------------------------------------------------- receipts ---
if (!quick) {
  const rec = (id, measured, threshold, ok, extra = {}) => { receipts.push({ id, measured, threshold, pass: ok, ...extra }); check(`${id} ${threshold}`, ok, JSON.stringify(measured)); };
  const t0 = performance.now();
  const S = lr4Suite(PARAMS);
  const label = Object.keys(PARAMS).length ? `params ${JSON.stringify(PARAMS)}` : "defaults: C2 alphabet with the d6MinGroups 5 gate";
  rec("LR4a", { onsetsExact: S.LR4a.acc, barsOnsetExact: S.LR4a.bar, clean: { onsetsExact: S.LR4aClean.acc, barsOnsetExact: S.LR4aClean.bar } }, "oracle, live: >= 0.985 / >= 0.94", S.LR4a.acc >= 0.985 && S.LR4a.bar >= 0.94, { config: label });
  rec("LR4b", { barsOnsetExact: S.LR4b.bar }, "oracle rub2 bars onset-exact >= 0.87", S.LR4b.bar >= 0.87);
  rec("LR4c", { onsetsExact: S.LR4c.acc, barsOnsetExact: S.LR4c.bar }, "listener rung (iid beat error 30 ms): >= 0.97 / >= 0.86", S.LR4c.acc >= 0.97 && S.LR4c.bar >= 0.86);
  rec("LR4d", { onsetsExact: S.LR4d.acc, barsOnsetExact: S.LR4d.bar }, "note jitter 45 ms, oracle: >= 0.90 / >= 0.60", S.LR4d.acc >= 0.90 && S.LR4d.bar >= 0.60);
  rec("LR4e", { gain: S.LR4e.live - S.LR4e.naive, live: S.LR4e.live, naive: S.LR4e.naive }, "jitter 30 ms bars onset-exact: priors minus naive >= +0.12", S.LR4e.live - S.LR4e.naive >= 0.12);
  rec("LR4j-falseD6", { falseD6: S.LR4j.falseD6, rawD6LabelShare: S.LR4j.rawD6Share }, "false d = 6 on s3 beats with truth 1-4, oracle <= 1% (start)", S.LR4j.falseD6 <= 0.01);
  // thresholds set at the first measurement, recorded in plan-amendments.md section 5 (2026-09-15) before this claim
  rec("LR4j-sextuplet", { onsetsExact: S.LR4j.onsetsExact, barsOnsetExact: S.LR4j.barsOnsetExact }, "sextuplet family: onsets exact >= 0.96, bars onset-exact >= 0.83 (section 5)", S.LR4j.onsetsExact >= 0.96 && S.LR4j.barsOnsetExact >= 0.83);
  const kMargin = S.LR4k.triplet.barsOnsetExact - S.LR4k.straight.barsOnsetExact;
  rec("LR4k-feel", { straight: S.LR4k.straight, triplet: S.LR4k.triplet, marginBars: kMargin }, "12/8 family under 4/4 at the dotted quarter: triplet minus straight >= +1.0 point bars onset-exact, triplet onsets not below (section 5)", kMargin >= 0.01 && S.LR4k.triplet.onsetsExact >= S.LR4k.straight.onsetsExact);
  rec("LR4k-compound", { s3_128: S.LR4k.s3_128_compound.bar, s3_128_onsets: S.LR4k.s3_128_compound.acc, family128: S.LR4k.family128_compound }, "s3 12/8 pieces under the compound set: bars onset-exact >= 0.94", S.LR4k.s3_128_compound.bar >= 0.94);
  receipts.push({ id: "LS2-section3-tables", config: label, note: "onsets exact / bars onset-exact, percent; product onset groups; 12/8 on the compound set", tables: tables(S), looseBeats: S.loose, msPerBar: S.msPerBar });

  // LR4f: inferred rung (beat.js product defaults, meter set to the piece's meter), conditional on matched intervals
  const tf = performance.now();
  const inf = [];
  for (const r of G.s3Suite()) {
    const pc = r.piece, settled = [];
    trackEvents(G.eventsOf({ notes: pc.notes, pedals: [] }), { createOnsets, options: { meter: pc.meter }, endMs: pc.notes[pc.notes.length - 1].t * 1000 + 1000, onTick: (s) => { for (const b of s.settled) settled.push(b.t_ms / 1000); } });
    const est = [...settled].sort((a, b) => a - b).filter((t, i, a) => i === 0 || t - a[i - 1] > 0.1);
    const trueIdx = est.map((t) => { let j = 0, bd = Infinity; pc.beats.forEach((b, k) => { const d = Math.abs(b - t); if (d < bd) { bd = d; j = k; } }); return bd <= 0.07 ? j : null; });
    const comp = pc.meter === "12/8" && !PARAMS.s3Compat, BT = comp ? 36 : 24;
    const evs = pc.notes.map((n) => ({ t_ms: n.t * 1000, kind: "on", note: n.note, vel: n.vel })), posOf = new Map(pc.notes.map((n) => [n.t * 1000 + "|" + n.note, n.pos]));
    const groups = groupNotes(evs).map((g) => ({ t: g.t, pos: posOf.get(g.notes[0].t + "|" + g.notes[0].note) }));
    const estMs = est.map((t) => t * 1000), asg = Q.assignBeats(groups.map((g) => g.t), estMs), byBeat = new Map();
    groups.forEach((g, i) => { g.bb = asg[i] ? asg[i].bb : null; if (asg[i]) { g.f = asg[i].f; if (!byBeat.has(g.bb)) byBeat.set(g.bb, []); byBeat.get(g.bb).push(g); } });
    const q = Q.createLiveQuantizer({ beatTicks: BT, beatsPerBar: pc.bpb, compound: comp, params: PARAMS });
    for (const bb of [...byBeat.keys()].sort((a, b) => a - b)) { const its = byBeat.get(bb), d = q.decide(bb, its.map((g) => ({ f: g.f, t: g.t })), estMs[bb + 1] - estMs[bb]); its.forEach((g, k) => { g.live = bb * 12 + d.pos[k] * 12 / BT; }); }
    const mapPos = (v, g) => { const a = trueIdx[g.bb], b = trueIdx[g.bb + 1]; if (a == null || b == null || b !== a + 1) return null; return a * 12 + (v - g.bb * 12); };
    inf.push({ rub: r.rub, meter: r.meter, sc: MX.scoreS3(groups.map((g) => ({ t: g.t / 1000, pos: g.pos, bb: g.bb, live: g.live })), "live", pc.bpb, 5, mapPos) });
  }
  const infAgg = (rs) => ({ acc: MX.mean(rs.map((x) => x.sc.acc)), coverage: MX.mean(rs.map((x) => x.sc.cov)) });
  const LR4f = { all: infAgg(inf), rub2: infAgg(inf.filter((x) => x.rub === 2)), byMeter: Object.fromEntries(["4/4", "3/4", "12/8"].map((m) => [m, infAgg(inf.filter((x) => x.meter === m))])) };
  rec("LR4f", LR4f, "conditional onsets exact inside matched intervals >= 0.95; coverage reported", LR4f.all.acc >= 0.95, { ms: Math.round(performance.now() - tf), config: "beat.js defaults, meter set to the piece" });

  // div8 (C2): one suite run with d = 8 on; kept only if LR4a and LR4d each drop by <= 0.5 points and the 32nd family's
  // onsets exact improves
  if (!PARAMS.div8) {
    const D = lr4Suite({ ...PARAMS, div8: true });
    const t32off = G.familySuite("thirtysecond").map((x) => takePiece(x.take, PARAMS)), t32on = G.familySuite("thirtysecond").map((x) => takePiece(x.take, { ...PARAMS, div8: true }));
    const drop = (a, b) => (a - b) * 100;
    const m = (a, k) => MX.mean(a.map((x) => x[k]));
    const dec = { LR4aDropPts: { onsets: drop(S.LR4a.acc, D.LR4a.acc), bars: drop(S.LR4a.bar, D.LR4a.bar) }, LR4dDropPts: { onsets: drop(S.LR4d.acc, D.LR4d.acc), bars: drop(S.LR4d.bar, D.LR4d.bar) },
      thirtysecond: { off: { onsetsExact: m(t32off, "onsetsExact"), barsOnsetExact: m(t32off, "barsOnsetExact") }, on: { onsetsExact: m(t32on, "onsetsExact"), barsOnsetExact: m(t32on, "barsOnsetExact") } }, lambda8: Q.QUANT_PARAMS.lambda8 };
    const keep = Math.max(dec.LR4aDropPts.onsets, dec.LR4aDropPts.bars) <= 0.5 && Math.max(dec.LR4dDropPts.onsets, dec.LR4dDropPts.bars) <= 0.5 && dec.thirtysecond.on.onsetsExact > dec.thirtysecond.off.onsetsExact;
    receipts.push({ id: "LS2-div8", measured: dec, decision: keep ? "keep div8 on" : "div8 stays off", pass: null });
  }

  // evidence beside the receipts of record: C2 as written (d = 6 competes on every beat), which the LS2 ruling replaced
  if (!Object.keys(PARAMS).length) {
    const Pp = lr4Suite({ d6MinGroups: 0 });
    receipts.push({ id: "LS2-evidence-C2-as-written", note: "reported, not gated: d6MinGroups 0, the rule the d6MinGroups 5 default replaced (ls1-rulings.md LS2 rulings)",
      measured: { LR4a: [Pp.LR4a.acc, Pp.LR4a.bar], LR4b: Pp.LR4b.bar, LR4c: [Pp.LR4c.acc, Pp.LR4c.bar], LR4d: [Pp.LR4d.acc, Pp.LR4d.bar], LR4e: Pp.LR4e.live - Pp.LR4e.naive, LR4j: Pp.LR4j, LR4k: { straight: Pp.LR4k.straight, triplet: Pp.LR4k.triplet, s3_128: Pp.LR4k.s3_128_compound.bar } },
      passesAsRuled: Pp.LR4a.acc >= 0.985 && Pp.LR4a.bar >= 0.94 && Pp.LR4b.bar >= 0.87 && Pp.LR4c.acc >= 0.97 && Pp.LR4c.bar >= 0.86 && Pp.LR4d.acc >= 0.90 && Pp.LR4d.bar >= 0.60 && Pp.LR4e.live - Pp.LR4e.naive >= 0.12 && Pp.LR4j.falseD6 <= 0.01, tables: tables(Pp) });
  }

  // LR4g + LR4i: the live transcriber on rung 4 only, meter set to truth (tempo suite held-out seeds, free suite)
  const tg = performance.now();
  const lr4i = (floor) => {
    let shownBars = [], allBars = 0, gViol = 0, metricInferred = 0;
    const perPiece = [];
    const pieces = [...G.tempoSuite().map((r) => ({ meter: r.meter, piece: r.piece, rub: r.rub })), ...G.freeSuite().map((pc) => ({ meter: "4/4", piece: pc, rub: "free" }))];
    for (const r of pieces) {
      const pc = r.piece, words = [];
      const tr = createTranscriber({ options: { meter: r.meter, rung4Floor: floor } });
      replayInto(tr, G.eventsOf(pc), { onTick: (out, T) => words.push({ T, word: out.header.word, drawing: out.header.drawing }), endMs: pc.notes[pc.notes.length - 1].t * 1000 + 1000 });
      tr.finish();
      const bars = tr.bars().filter((b) => b.state === "settled" && b.kind === "metric" && b.source === "inferred");
      metricInferred += bars.length;
      for (const b of bars) if (words.some((w) => w.T >= b.start_ms && w.T <= b.end_ms && w.word !== "steady")) gViol++;
      if (!pc.truth) continue;
      const T = pc.truth, barT = T.beatTicks * { "4/4": 4, "3/4": 3, "6/8": 2 }[r.meter], nBars = T.downs_ms.length;
      const lines = [...T.downs_ms, T.beats_ms[T.pickup + nBars * { "4/4": 4, "3/4": 3, "6/8": 2 }[r.meter]]];
      allBars += nBars;
      const tickOf = new Map(pc.notes.map((n) => [n.t * 1000 + "|" + n.note, n.tick]));
      const near = (t) => { let best = -1, bd = Infinity; lines.forEach((x, i) => { const d = Math.abs(x - t); if (d < bd) { bd = d; best = i; } }); return bd <= 70 ? best : null; };
      let ok = 0;
      for (const b of bars) {
        const i = near(b.start_ms), j = near(b.end_ms);
        let exact = i != null && j === i + 1;
        if (exact) {
          const truthIn = pc.notes.filter((n) => n.tick >= i * barT && n.tick < (i + 1) * barT).length;
          exact = b.notes.length === truthIn && b.notes.every((n) => tickOf.get(n.on_ms + "|" + n.note) - i * barT === n.pos);
        }
        shownBars.push({ start_ms: b.start_ms, end_ms: b.end_ms, onsetsExact: exact });
        if (exact) ok++;
      }
      perPiece.push({ meter: r.meter, rub: r.rub, shown: bars.length, correct: ok });
    }
    const correct = shownBars.filter((b) => b.onsetsExact).length;
    return { precision: shownBars.length ? correct / shownBars.length : NaN, shownShare: shownBars.length / allBars, shown: shownBars.length, correct, allBars, gViol, metricInferred,
      byRub: Object.fromEntries([0, 1, 2].map((k) => { const p = perPiece.filter((x) => x.rub === k); const s = p.reduce((a, x) => a + x.shown, 0), c = p.reduce((a, x) => a + x.correct, 0); return [k, { shown: s, correct: c, precision: s ? c / s : null }]; })) };
  };
  // LR4i runs at the transcriber's rung-4 gate (TRANSCRIBER_OPTIONS.rung4Floor, set by the 0.5-step rule and recorded in
  // plan-amendments.md section 5); the floors below it are re-measured and reported. LR4g runs at the default gate and at
  // the plain steady word (4.5), so the construction check covers both.
  const DEF = TRANSCRIBER_OPTIONS.rung4Floor;
  const I = lr4i(DEF), I45 = DEF > 4.5 ? lr4i(4.5) : I;
  rec("LR4g", { atGate: { metricBarsFromRung4: I.metricInferred, barsWithANonSteadyTick: I.gViol }, atSteady45: { metricBarsFromRung4: I45.metricInferred, barsWithANonSteadyTick: I45.gViol } }, "0 metric bars from rung 4 outside steady", I.gViol === 0 && I45.gViol === 0);
  const sweep = [];
  for (let f = 4.5; f < DEF - 1e-9; f += 0.5) { const S2 = f === 4.5 ? I45 : lr4i(f); sweep.push({ rung4Floor: f, precision: S2.precision, shownShare: S2.shownShare, shown: S2.shown }); }
  rec("LR4i", { rung4Floor: DEF, precision: I.precision, shownShare: I.shownShare, shown: I.shown, correct: I.correct, allBars: I.allBars, byRub: I.byRub, belowGate: sweep },
    `precision of shown rung-4 bars >= 0.80 at the rung-4 gate (rung4Floor ${DEF}; plan-amendments.md section 5)`, I.precision >= 0.8, { ms: Math.round(performance.now() - tg) });

  // LR4h: written durations on the pedal and held-bass families (C1, C7), oracle beats and truth voices, clean()
  const th = performance.now();
  const hRows = [];
  for (const family of ["pedal", "heldBass"]) for (const { take, spec } of G.familySuite(family)) {
    const T = take.truth, byKey = new Map(T.notes.map((n) => [n.note + "|" + Math.round(n.on_ms), n]));
    const sc = clean(take.events, { beats: T.beats_ms, one: T.downbeats_ms[0], meter: spec.meter, voiceOf: (n) => byKey.get(n.note + "|" + n.t), params: { quant: PARAMS } });
    const est = sc.notes.map((n) => { const tn = byKey.get(n.note + "|" + n.t_ms); return { id: tn ? tn.id : -1, note: n.note, voice: n.voice, tick: n.tick, dur: n.dur }; });
    const ped = new Set(T.barInfo.filter((b) => b.pedalledShare >= 0.5).map((b) => b.index));
    const matched = est.filter((e) => { const t = T.notes[e.id]; return t && t.tick === e.tick; });
    hRows.push({ family, meter: spec.meter, rub: spec.rub, dur: MX.durationsExact(est, T.notes).durationsExact, durGivenOnset: matched.length ? matched.filter((e) => T.notes[e.id].dur === e.dur).length / matched.length : NaN,
      full: MX.barsFullyExact(est, T.notes, T.meter).barsFullyExact, onsets: MX.scoreTicks(est, T.notes, T.meter).onsetsExact,
      restsEst: MX.restsPerVoicePerBar(est.filter((e) => e.id >= 0), T.meter, { pedalled: ped }).pedalledMedian, restsTruth: MX.restsPerVoicePerBar(T.notes, T.meter, { pedalled: ped }).pedalledMedian });
  }
  const hAgg = (rs) => ({ durationsExact: MX.mean(rs.map((x) => x.dur)), durationsGivenOnset: MX.mean(rs.map((x) => x.durGivenOnset)), barsFullyExact: MX.mean(rs.map((x) => x.full)), onsetsExact: MX.mean(rs.map((x) => x.onsets)), restsPedalledMedian: MX.median(hRows.map((x) => x.restsEst)), n: rs.length });
  const LR4h = { all: hAgg(hRows), pedal: hAgg(hRows.filter((x) => x.family === "pedal")), heldBass: hAgg(hRows.filter((x) => x.family === "heldBass")), byRub: Object.fromEntries([0, 1, 2].map((k) => [k, hAgg(hRows.filter((x) => x.rub === k))])),
    byMeter: Object.fromEntries(["4/4", "3/4", "12/8"].map((m) => [m, hAgg(hRows.filter((x) => x.meter === m))])), LR8bFixture: { estMedian: MX.median(hRows.map((x) => x.restsEst)), truthMedian: MX.median(hRows.map((x) => x.restsTruth)) } };
  rec("LR4h", LR4h, "durations exact (pedal + heldBass families, oracle beats, truth voices) >= 0.95 (section 5); barsFullyExact reported", LR4h.all.durationsExact >= 0.95, { ms: Math.round(performance.now() - th) });

  receipts.push({ id: "LS2-ms", ms: Math.round(performance.now() - t0) });
}

for (const r of receipts) console.log("RECEIPT", JSON.stringify(r, (k, v) => r4(v)));
console.log(`score_quantize: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
