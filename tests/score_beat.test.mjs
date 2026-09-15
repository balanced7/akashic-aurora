// Node tests for arsenal/web/piano/score/onsets.js and beat.js (slice LS1 of the live sheet music plan,
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md sections 6.1-6.2 and 10.1, amended by
// plan-amendments.md C4 and section 4). Zero dependencies, synthetic fixtures only (tests/fixtures/score/gen.mjs):
//   node tests/score_beat.test.mjs           unit contracts, then receipts LR2a-g and LR3a
//   node tests/score_beat.test.mjs --quick   unit contracts only
// Receipts run the product configuration: onsets.js defaults (40 ms chords, near-chord, rolls) and the meter set to
// the piece's own meter (his setting, as the page will run). The tempo lane's configuration (meter "auto", 40 ms
// groups) is LR1 in tests/score_fixtures.test.mjs; its numbers are printed here beside the product ones. Held-out
// seeds 37, 41, 53 carry the thresholds; seeds 59, 61, 67 are reported as a fresh check.
// LR3b, LR3c and the C2 x2-family share run on the practice sessions locally (a scratch bench, outputs under
// state/arsenal/score/), never here.
import { createOnsets, groupNotes, salienceOf, LANE_ONSET_PARAMS, ONSET_PARAMS } from "../arsenal/web/piano/score/onsets.js";
import { createBeatTracker, trackEvents, ladder, FAMILY_RATIOS, BEAT_PARAMS, LANE_BEAT_PARAMS } from "../arsenal/web/piano/score/beat.js";
import * as G from "./fixtures/score/gen.mjs";
import * as MX from "./fixtures/score/metrics.mjs";
import * as S3 from "./fixtures/score/s3ref.mjs";

const argv = process.argv.slice(2);
const quick = argv.includes("--quick");
let pass = 0, fail = 0;
const receipts = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const near = (a, b, tol) => Math.abs(a - b) <= tol;

// ---------------------------------------------------------------------------------------------- onsets ---
function feed(list, params = {}) {
  const on = createOnsets(params), out = [];
  const evs = [...list].sort((a, b) => a.t - b.t);
  for (const e of evs) {
    out.push(...on.flush(e.t - 1e-6));
    if (e.kind === "on") on.noteOn(e.note, e.vel ?? 80, e.t);
    else if (e.kind === "off") on.noteOff(e.note, e.t);
    else if (e.kind === "pedal") on.pedal(e.down, e.t);
  }
  out.push(...on.flush(Infinity));
  return out;
}
const ons = (pairs) => pairs.map(([t, note, vel]) => ({ t, kind: "on", note, vel }));
{
  let g = feed(ons([[1000, 60], [1040, 64]]));
  check("onsets: 40 ms joins a chord", g.length === 1 && g[0].kind === "chord" && g[0].notes.length === 2);
  g = feed(ons([[1000, 60], [1041, 64]]));
  check("onsets: 41 ms apart, near register: two groups", g.length === 2);
  g = feed(ons([[1000, 48], [1055, 72]]));
  check("onsets: near-chord 55 ms, 24 semitones up: joins", g.length === 1);
  check("onsets: lane params keep the near note apart", feed(ons([[1000, 48], [1055, 72]]), LANE_ONSET_PARAMS).length === 2);
  g = feed(ons([[1000, 60], [1025, 64], [1050, 67], [1075, 72]]));
  check("onsets: 75 ms ascending held roll merges", g.length === 1 && g[0].kind === "roll" && g[0].spread === 75, JSON.stringify(g.map((x) => [x.t, x.kind, x.notes.length])));
  check("onsets: lane params split that roll at 40 ms", feed(ons([[1000, 60], [1025, 64], [1050, 67], [1075, 72]]), LANE_ONSET_PARAMS).length === 2);
  g = feed(ons([[1000, 60], [1060, 64], [1120, 67]]));
  check("onsets: 60 ms gaps are not a roll", g.length === 3);
  g = feed([...ons([[1000, 60], [1030, 64], [1060, 67]]), { t: 1045, kind: "off", note: 60 }]);
  check("onsets: a note released before the last, pedal up: not a roll", g.length === 2);
  g = feed([...ons([[1000, 60], [1030, 64], [1060, 67]]), { t: 1045, kind: "off", note: 60 }, { t: 900, kind: "pedal", down: true }]);
  check("onsets: the same under the pedal is a roll", g.length === 1 && g[0].kind === "roll");
  g = feed(ons([[1000, 60], [1030, 67], [1060, 64]]));
  check("onsets: a non-monotonic chain is not a roll", !g.some((x) => x.kind === "roll"));
  g = feed(ons([[1000, 60], [1100, 62], [1200, 64], [1300, 65], [1400, 67]]));
  check("onsets: a 100 ms scale is a run of single groups", g.length === 5 && g.every((x) => x.run && x.kind === "single"));
  g = feed([...ons([[1000, 64], [1080, 65]]), { t: 1060, kind: "off", note: 64 }]);
  check("onsets: a 60 ms note 80 ms before a step is a grace candidate", g[0].grace && g[0].grace.to === 65 && g[0].grace.leadMs === 80, JSON.stringify(g[0].grace));
  g = feed([...ons([[1000, 64], [1080, 67]]), { t: 1060, kind: "off", note: 64 }]);
  check("onsets: a leap is not a grace", !g[0].grace);
  check("onsets: salience with bass bonus", near(salienceOf([{ note: 40, vel: 127 }]), Math.sqrt(1.4) + 0.5, 1e-12) && near(salienceOf([{ note: 60, vel: 0 }, { note: 64, vel: 0 }]), Math.sqrt(0.8), 1e-12));
  g = feed(ons([[1000, 60]]), LANE_ONSET_PARAMS);
  check("onsets: lane avail = t + 40", g[0].avail === 1040);
  g = feed(ons([[1000, 60]]));
  check("onsets: default avail waits for a possible roll", g[0].avail === 1000 + ONSET_PARAMS.rollSpanMs);
  const on = createOnsets(LANE_ONSET_PARAMS);
  on.noteOn(60, 80, 1000);
  check("onsets: nothing handed out before the window closes", on.flush(1039).length === 0 && on.flush(1040).length === 1);
  const take = G.genTake({ meter: "4/4", texture: "ballad", seed: 9, bars: 8 });
  const streamed = [];
  const s = createOnsets();
  for (const e of take.events) {
    streamed.push(...s.flush(e.t_ms - 1e-6));
    if (e.kind === "on") s.noteOn(e.note, e.vel, e.t_ms); else if (e.kind === "off") s.noteOff(e.note, e.t_ms); else if (e.kind === "pedal") s.pedal(e.down, e.t_ms); else if (e.kind === "sound_end") s.soundEnd(e.note, e.t_ms, e.by);
  }
  streamed.push(...s.flush(Infinity));
  const offline = groupNotes(take.events);
  check("onsets: offline groupNotes equals the stream", JSON.stringify(streamed.map((x) => [x.t, x.kind, x.notes.map((n) => n.note)])) === JSON.stringify(offline.map((x) => [x.t, x.kind, x.notes.map((n) => n.note)])));
  check("onsets: sound ends attach to notes", s.recent().some((x) => x.notes.some((n) => n.soundEnd != null && n.by)));
}

// -------------------------------------------------------------------------------------------- beat.js ---
function metronome({ bpm = 80, seconds = 60, start = 500, gapAt = null, gapMs = 0, vel = 80 } = {}) {
  const ev = [], P = 60000 / bpm;
  let t = start, k = 0;
  while (t < start + seconds * 1000) {
    if (gapAt != null && k === gapAt) t += gapMs;
    ev.push({ t_ms: t, kind: "on", note: k % 4 === 0 ? 43 : 67, vel: k % 4 === 0 ? vel + 20 : vel });
    t += P; k++;
  }
  return ev;
}
// press a family button (chooseLevel) once, on the first tick at or after `at`
function levelRun(events, { meter = "4/4", at, ratio, endMs = null, taps = [] }) {
  let done = false;
  return trackEvents(events, { createOnsets, options: { meter }, endMs, taps, onTick: (y, bt) => { if (!done && y.t_ms >= at) done = !!bt.chooseLevel(ratio); } }).samples;
}
{
  const { samples, tracker } = trackEvents(metronome({ bpm: 80 }), { createOnsets });
  const late = samples.filter((x) => x.t_ms > 20000 && x.t_ms < 60000);
  check("beat: metronome 80 reads 80 within 2%", late.every((x) => x.bpm && near(x.bpm, 80, 1.6)), JSON.stringify(late.find((x) => !(x.bpm && near(x.bpm, 80, 1.6)))));
  check("beat: metronome reads steady", late.every((x) => x.mode === "steady"), JSON.stringify([...new Set(late.map((x) => x.mode))]));
  check("beat: metronome bpmShown is 80", late.every((x) => x.bpmShown === 80));
  check("beat: inferred source, bars while steady", late.every((x) => x.source === "inferred" && x.drawing === "bars"));
  check("beat: family ratios are the button set", late.every((x) => x.family.every((f) => FAMILY_RATIOS.includes(f.ratio))));
  const settled = samples.flatMap((x) => x.settled);
  check("beat: settled beats carry increasing indices", settled.length > 60 && settled.every((b, i) => i === 0 || b.index > settled[i - 1].index));
  const st = tracker.state();
  check("beat: state() has the beatState fields", ["source", "mode", "beats", "period_ms", "bpmShown", "family", "meter", "barPhase", "pickup", "holds"].every((k) => k in st));
  check("beat: meter defaults to 4/4", st.meter.label === "4/4" && st.meter.source === "default");

  const held = trackEvents(metronome({ bpm: 80, seconds: 40, gapAt: 30, gapMs: 5000 }), { createOnsets });
  const gapStart = 500 + 30 * 750;
  const inGap = held.samples.filter((x) => x.t_ms > gapStart + 3000 && x.t_ms < gapStart + 4900);
  check("beat: a 5 s pause reads hold", inGap.length > 0 && inGap.every((x) => x.mode === "hold" && x.drawing === "tape"), JSON.stringify([...new Set(inGap.map((x) => x.mode))]));
  check("beat: the hold is recorded when playing resumes", held.tracker.state().holds.length >= 1);

  const bt = createBeatTracker();
  for (const t of [1000, 1500, 2000]) bt.tap(t);
  const r4 = bt.tap(2500);
  check("beat: four taps give the tempo", r4 && near(r4.bpm, 120, 1e-9) && r4.selected === "seeded");
  bt.thisIsOne(1000);
  let x = bt.tick(2750);
  check("beat: taps are the source with bars after This is 1", x.source === "taps" && x.drawing === "bars" && bt.state().barPhase.downbeatIndex === 0, JSON.stringify([x.source, x.drawing, bt.state().barPhase]));
  x = bt.tick(2500 + 4 * 4 * 500 + 250);
  check("beat: taps lapse after tapValidBars bars", x.source !== "taps");
  const bt2 = createBeatTracker();
  bt2.tap(1000); bt2.tap(1500); bt2.tap(1600);
  check("beat: fewer than four taps give nothing", bt2.tap(5000) === null);

  // taps in phase with the metronome (beat k at 500 + 750 k): beats 27-30
  const sel = trackEvents(metronome({ bpm: 80, seconds: 30 }), { createOnsets, taps: [27, 28, 29, 30].map((k) => 500 + 750 * k + 12) });
  const selRes = sel.samples.filter((y) => y.t_ms > 23500 && y.t_ms < 25000);
  check("beat: taps on a live hypothesis select it (source taps, tempo kept)", selRes.every((y) => y.source === "taps" && near(y.bpm, 80, 2)), JSON.stringify(selRes.slice(0, 2).map((y) => [y.source, y.bpm])));

  const lv = createBeatTracker();
  const onsL = createOnsets();
  const evs = metronome({ bpm: 70, seconds: 40 });
  let i = 0, chose = null;
  for (let T = 250; T <= 40000; T += 250) {
    while (i < evs.length && evs[i].t_ms <= T) { onsL.noteOn(evs[i].note, evs[i].vel, evs[i].t_ms); i++; }
    for (const g of onsL.flush(T)) lv.addGroup(g);
    const y = lv.tick(T);
    if (T === 15000) chose = lv.chooseLevel(2);
    if (T === 25000) check("beat: chooseLevel(2) doubles the readout and keeps it", chose && y.bpm && near(y.bpm, 140, 7), JSON.stringify([chose, y.bpm]));
  }
  check("beat: setMeter rejects an unknown meter", (() => { try { createBeatTracker().setMeter("5/4"); return false; } catch { return true; } })());

  check("ladder: jam wins", ladder({ jam: { live: true, aligned: true }, taps: { valid: true } }).source === "jam");
  check("ladder: song without 1 is beat tape", ladder({ song: { phaseConf: 0.8, floor: 0.5, one: false } }).drawing === "beat-tape");
  check("ladder: song below its floor falls to taps", ladder({ song: { phaseConf: 0.3, floor: 0.5 }, taps: { valid: true, one: true } }).source === "taps");
  check("ladder: inferred loose is tape", ladder({ inferred: { mode: "loose" } }).drawing === "tape");
  check("ladder: inferred steady is bars", ladder({ inferred: { mode: "steady" } }).drawing === "bars");
  check("ladder: meter free is always tape", ladder({ jam: { live: true, aligned: true }, meter: "free" }).drawing === "tape");
  check("ladder: nothing is free tape", ladder({}).source === "free" && ladder({}).drawing === "tape");

  // tactus under a set compound meter: a 6/8 piece at 50 (dotted quarter) reads near 50 under meter 6/8
  const pc = G.genPiece("6/8", "arp", 0, 50, 4242, { pickup: 0 });
  const c68 = trackEvents(G.eventsOf(pc), { createOnsets, options: { meter: "6/8" } }).samples.filter((y) => y.t_ms > 30000 && y.bpm);
  const med68 = MX.median(c68.map((y) => y.bpm));
  check("beat: 6/8 at 50 reads the dotted quarter under meter 6/8", near(med68, 50, 4), String(med68));

  // the once-a-second meter step runs off event time, whatever the tick phase: a live page's performance clock never
  // lands on the 250 ms grid (before the fix the grid, the subdivision and meter "auto" only ran on ticks at k * 1000)
  const ev68 = G.eventsOf(pc);
  const grid0 = trackEvents(ev68, { createOnsets, options: { meter: "6/8" } }).samples.filter((y) => y.t_ms > 30000);
  for (const phaseMs of [1, 137]) {
    const off = trackEvents(ev68, { createOnsets, options: { meter: "6/8" }, phaseMs }).samples.filter((y) => y.t_ms > 30000);
    check(`beat: tick phase +${phaseMs} ms keeps the subdivision and the tactus factor`, off.every((y) => y.subdivision != null) && MX.median(off.map((y) => y.factor)) === MX.median(grid0.map((y) => y.factor)) && near(MX.median(off.map((y) => y.bpm)), 50, 4),
      JSON.stringify([off.filter((y) => y.subdivision == null).length, MX.median(off.map((y) => y.factor)), MX.median(grid0.map((y) => y.factor)), MX.median(off.map((y) => y.bpm))]));
    check(`beat: tick phase +${phaseMs} ms, meter auto still commits a meter`, trackEvents(ev68, { createOnsets, options: { meter: "auto" }, phaseMs }).tracker.state().meter.label != null);
  }

  // pauses: two holds two beats apart. The readout must not count the intervals across them (it read (750 + 3250) / 2
  // = 2000 ms, 30 bpm), and bpmShown must never show such a transient
  {
    const ev = [], P = 750; let t = 500, k = 0;
    const put = (n) => { for (let j = 0; j < n; j++) { ev.push({ t_ms: t, kind: "on", note: k % 4 === 0 ? 43 : 67, vel: k % 4 === 0 ? 100 : 80 }); t += P; k++; } };
    put(24); t += 2500; put(2); t += 2500; put(24);
    const s = trackEvents(ev, { createOnsets }).samples;
    const after = s.filter((y) => y.t_ms > 25000 && y.t_ms < 42000 && y.bpm != null && y.mode !== "hold");
    check("beat: after two pauses the readout keeps the period", after.length > 20 && after.every((y) => near(y.bpm, 80, 6.4)), JSON.stringify(after.filter((y) => !near(y.bpm, 80, 6.4)).slice(0, 3).map((y) => [y.t_ms, y.bpm])));
    check("beat: bpmShown stays 80 through the pauses", s.filter((y) => y.t_ms > 12000).every((y) => y.bpmShown === 80), JSON.stringify([...new Set(s.filter((y) => y.t_ms > 12000).map((y) => y.bpmShown))]));
    const lane = trackEvents(ev, { createOnsets, params: LANE_BEAT_PARAMS }).samples.filter((y) => y.t_ms > 25000 && y.t_ms < 42000 && y.bpm != null && y.mode !== "hold");
    check("beat: LANE_BEAT_PARAMS keeps the lane's readout across holds (LR1)", lane.some((y) => y.bpm < 40));
  }

  // count-in taps, then a step from 70 to 95 at bar 8: once tapValidBars have passed the tapped level must not hold the
  // agent pool (C4: rung-4 rules), so the readout follows the step as it does without taps
  for (const seed of [71001, 72001, 73001]) {
    const take = G.genTake({ meter: "4/4", texture: "mixed", rub: 0, bpm: 70, countIn: true, bars: 24, tempoStep: { atBar: 8, bpm: 95 }, seed });
    const step = take.truth.downbeats_ms[8], end = take.truth.beats_ms[take.truth.beats_ms.length - 1];
    const acc = (a, v) => MX.mean(a.map((y) => +(Math.abs(y.bpm / v - 1) <= 0.08)));
    const s = trackEvents(take.events, { createOnsets, taps: take.taps }).samples.filter((y) => y.bpm != null);
    const pre = s.filter((y) => y.t_ms > 8000 && y.t_ms < step), late = s.filter((y) => y.t_ms > step + 20000 && y.t_ms < end);
    check(`beat: count-in taps then a step to 95 (seed ${seed}): Acc1 before >= 0.9 and 20 s after >= 0.9`, acc(pre, 70) >= 0.9 && acc(late, 95) >= 0.9 && late.every((y) => y.source === "inferred"),
      JSON.stringify({ pre: acc(pre, 70), late: acc(late, 95), med: MX.median(late.map((y) => y.bpm)) }));
  }

  // chosen level: holds on steady playing and reads the level; taps replace it; after a step from 70 to 95 it follows
  // the playing tempo or lets go, and never stays at a tempo that is no level of the new one
  // (from 26 s: a x0.5 level reads only once its own agent has 4 intervals, 4 x 1714 ms after the press)
  for (const ratio of [2, 0.5]) {
    const s = levelRun(metronome({ bpm: 70, seconds: 60 }), { at: 15000, ratio }).filter((y) => y.t_ms > 26000 && y.t_ms < 60000);
    const bad = s.find((y) => !(y.levelBpm != null && y.bpm && near(y.bpm, 70 * ratio, 0.05 * 70 * ratio)));
    check(`beat: chooseLevel(${ratio}) on a steady 70 holds and reads ${70 * ratio}`, s.length > 100 && !bad, JSON.stringify(bad));
  }
  {
    const P70 = 60000 / 70;
    const s = levelRun(metronome({ bpm: 70, seconds: 40 }), { at: 15000, ratio: 2, taps: [27, 28, 29, 30].map((k) => 500 + P70 * k + 10) });
    check("beat: taps replace a chosen level", s.filter((y) => y.t_ms > 16000 && y.t_ms < 500 + P70 * 27).every((y) => y.levelBpm != null) && s.filter((y) => y.t_ms > 500 + P70 * 30 + 250).every((y) => y.levelBpm == null));
  }
  for (const seed of [71001, 72001, 73001]) {
    const take = G.genTake({ meter: "4/4", texture: "mixed", rub: 0, bpm: 70, countIn: true, bars: 24, tempoStep: { atBar: 8, bpm: 95 }, seed });
    const step = take.truth.downbeats_ms[8], end = take.truth.beats_ms[take.truth.beats_ms.length - 1];
    const s = levelRun(take.events, { at: 12000, ratio: 2 });
    const pre = s.filter((y) => y.bpm && y.t_ms > 16000 && y.t_ms < step), late = s.filter((y) => y.bpm && y.t_ms > step + 20000 && y.t_ms < end);
    const at140 = MX.mean(pre.map((y) => +(Math.abs(y.bpm / 140 - 1) <= 0.08)));
    const fam = MX.mean(late.map((y) => +(Math.abs(y.bpm / 95 - 1) <= 0.08 || Math.abs(y.bpm / 190 - 1) <= 0.08)));
    check(`beat: chooseLevel(2) then a step 70 -> 95 (seed ${seed}): 140 before, 95 or 190 after`, at140 >= 0.9 && fam >= 0.85, JSON.stringify({ at140, fam, med: MX.median(late.map((y) => y.bpm)) }));
  }
}

// ------------------------------------------------------------------------------------------- receipts ---
function productRun(r, { meter = null, onsetParams = {}, params = {} } = {}) {
  const pc = r.piece, emitted = [], settled = [], samples = [];
  const endMs = pc.notes[pc.notes.length - 1].t * 1000 + 1000;
  trackEvents(G.eventsOf(pc), {
    createOnsets, onsetParams, params, options: { meter: meter || r.meter }, endMs,
    onTick: (s) => { samples.push({ t_ms: s.t_ms, bpm: s.bpm, bpmShown: s.bpmShown, hold: s.mode === "hold", mode: s.mode }); for (const b of s.beats) emitted.push(b.t_ms); for (const b of s.settled) settled.push(b.t_ms); },
  });
  return { samples, emitted_ms: emitted, settled_ms: settled, meterLog: [], downs_ms: [] };
}
function shownAudit(samples, truth, meterLabel) {
  const tpb = { "4/4": 4, "3/4": 3, "6/8": 2 }[meterLabel];
  let violations = 0, prevAt = null, prevVal = null;
  const changes = [];
  for (const s of samples) {
    if (s.bpmShown == null) continue;
    if (prevVal == null) { prevVal = s.bpmShown; prevAt = s.t_ms; continue; }
    if (s.bpmShown !== prevVal) {
      if (s.t_ms - prevAt < tpb * 60000 / prevVal - 1e-6 || Math.abs(s.bpmShown - prevVal) < 3) violations++;
      changes.push(s.t_ms); prevVal = s.bpmShown; prevAt = s.t_ms;
    }
  }
  const downs = truth.downs_ms, perBar = [];
  for (let b = 0; b + 1 < downs.length; b++) perBar.push(changes.filter((t) => t >= downs[b] && t < downs[b + 1]).length);
  return { violations, perBarMedian: MX.median(perBar), perBarMax: Math.max(...perBar), perBarMean: MX.mean(perBar) };
}
const pickT = (rs) => { const f = (k) => MX.mean(rs.map((x) => x[k])); return { n: rs.length, acc1: f("acc1"), acc1s: f("acc1s"), acc2: f("acc2"), fb: f("fb"), fbLag: f("fbLag"), fAny: f("fAny"), levelErr: f("octave"), flips: f("flipsPerMin"), flipsShown: f("flipsShown"), lockT: MX.mean(rs.map((x) => x.lockT).filter((v) => v != null)), never: rs.filter((x) => x.lockT == null).length }; };

if (!quick) {
  const t0 = performance.now();
  const suite = (seeds, opts) => G.tempoSuite(seeds).map((r) => {
    const run = productRun(r, opts);
    const ev = MX.evalTempo(r.piece.truth, run);
    const shownRun = { ...run, samples: run.samples.map((s) => ({ ...s, bpm: s.bpmShown })) };
    const evShown = MX.evalTempo(r.piece.truth, shownRun);
    return { ...r, ...ev, flipsShown: evShown.flipsPerMin, acc1Shown: evShown.acc1, audit: shownAudit(run.samples, r.piece.truth, r.meter) };
  });
  const held = suite(G.TEMPO_TEST_SEEDS, {});
  const fresh = suite([59, 61, 67], {});
  const laneGroups = suite(G.TEMPO_TEST_SEEDS, { onsetParams: LANE_ONSET_PARAMS });
  const all = pickT(held), rub = [0, 1, 2].map((k) => pickT(held.filter((x) => x.rub === k)));
  const meters = Object.fromEntries(["4/4", "3/4", "6/8"].map((m) => [m, pickT(held.filter((x) => x.meter === m))]));
  const shownAcc1 = MX.mean(held.map((x) => x.acc1Shown));
  const ms = performance.now() - t0;

  const rec = (id, measured, threshold, ok) => { receipts.push({ id, measured, threshold, pass: ok }); check(`${id} ${threshold}`, ok, JSON.stringify(measured)); };
  rec("LR2a", { all: all.acc1, rub0: rub[0].acc1, rub1: rub[1].acc1, shownAll: shownAcc1, fresh: pickT(fresh).acc1, laneGroups: pickT(laneGroups).acc1 }, ">= 0.68 / >= 0.85 / >= 0.80", all.acc1 >= 0.68 && rub[0].acc1 >= 0.85 && rub[1].acc1 >= 0.80);
  rec("LR2b", { all: all.acc2, fresh: pickT(fresh).acc2 }, ">= 0.78", all.acc2 >= 0.78);
  rec("LR2c", { all: all.fb, settled: all.fbLag, anyLevel: all.fAny, fresh: pickT(fresh).fb }, ">= 0.60", all.fb >= 0.60);
  rec("LR2d", { levelErr: all.levelErr, flipsPerMin: all.flips, flipsShownPerMin: all.flipsShown, fresh: { levelErr: pickT(fresh).levelErr, flips: pickT(fresh).flips } }, "<= 0.13 / <= 2.0", all.levelErr <= 0.13 && all.flips <= 2.0);
  rec("LR2e", { lockTmean: all.lockT, never: all.never, fresh: { lockT: pickT(fresh).lockT, never: pickT(fresh).never } }, "<= 12 s; <= 5 of 81", all.lockT <= 12 && all.never <= 5);
  const viol = held.reduce((s, x) => s + x.audit.violations, 0);
  rec("LR2f", { violations: viol, medianChangesPerBar: MX.median(held.map((x) => x.audit.perBarMedian)), meanChangesPerBar: MX.mean(held.map((x) => x.audit.perBarMean)), maxInOneTrueBar: Math.max(...held.map((x) => x.audit.perBarMax)) }, "<= 1 per bar (by construction)", viol === 0);
  receipts.push({ id: "LR2-detail", byRubato: rub, byMeter: meters, laneGroupsAll: pickT(laneGroups), freshAll: pickT(fresh), ms: Math.round(ms) });

  // LR2g: count-in taps, then N bars without taps; bars onset-exact at bar N (the section 3 live quantizer on the
  // tracker's settled beats, indexed from the first tap, so level and phase errors count as wrong)
  const t1 = performance.now();
  const takes = G.familySuite("countIn");
  const barExact = (take, beatsByIndex) => {
    const BT = 24, notes = take.truth.notes.map((n) => ({ t: n.on_ms / 1000, note: n.note, vel: n.vel, pos: 48 + n.tick / 2 })).sort((a, b) => a.t - b.t);
    const beats = beatsByIndex.map((t) => t / 1000);
    const gs = S3.groupsOf(notes); S3.assign(gs, beats); S3.quantLive(gs, beats, 4, S3.S3_OPTIONS);
    const out = [];
    for (let n = 0; n < take.truth.bars; n++) {
      const inBar = gs.filter((g) => g.pos >= 48 + 48 * n && g.pos < 96 + 48 * n);
      out.push(inBar.length > 0 && inBar.every((g) => g.bb != null && g.live === g.pos));
    }
    return out;
  };
  const byIndex = (settled, offset = 0) => {
    const m = new Map(); for (const b of settled) if (!m.has(b.index + offset)) m.set(b.index + offset, b.t_ms);
    const keys = [...m.keys()].filter((k) => k >= 0).sort((a, b) => a - b), arr = [];
    if (!keys.length) return arr;
    for (let k = 0; k <= keys[keys.length - 1]; k++) {
      if (m.has(k)) { arr.push(m.get(k)); continue; }
      const lo = keys.filter((x) => x < k).pop(), hi = keys.find((x) => x > k);
      arr.push(lo == null ? NaN : m.get(lo) + (m.get(hi) - m.get(lo)) * (k - lo) / (hi - lo));
    }
    return arr[0] != null && Number.isFinite(arr[0]) ? arr : arr.map((t, k) => (Number.isFinite(t) ? t : m.get(keys[0]) - (keys[0] - k) * 700));
  };
  const curves = {};
  for (const [name, cfg] of [["K4", { params: {} }], ["Kinf", { params: { tapValidBars: 1e6 } }], ["noTaps", { params: {}, noTaps: true }]]) {
    for (const rubLevel of [1, 2]) {
      const rows = [];
      for (const { take, spec } of takes.filter((x) => x.spec.rub === rubLevel)) {
        const settled = [];
        trackEvents(take.events, { createOnsets, params: cfg.params, options: { meter: "4/4" }, taps: cfg.noTaps ? [] : take.taps, one: cfg.noTaps ? null : take.taps[0],
          onTick: (s) => { for (const b of s.settled) settled.push({ index: b.index, t_ms: b.t_ms }); } });
        let offset = 0;
        if (cfg.noTaps) {
          // control: align the first settled beat after the music starts to its nearest true beat
          const first = settled.find((b) => b.t_ms >= take.truth.downbeats_ms[0] - 100);
          if (first) { let j = 0, bd = Infinity; take.truth.beats_ms.forEach((t, k) => { const d = Math.abs(t - first.t_ms); if (d < bd) { bd = d; j = k; } }); offset = j - first.index; }
        }
        rows.push(barExact(take, byIndex(settled, offset)));
      }
      const at = [], upto = [];
      for (let N = 1; N <= 8; N++) { at.push(MX.mean(rows.map((r) => +r[N - 1]))); upto.push(MX.mean(rows.map((r) => MX.mean(r.slice(0, N).map(Number))))); }
      curves[`${name}.rub${rubLevel}`] = { pieces: rows.length, barN: Object.fromEntries([1, 2, 4, 8].map((N) => [N, at[N - 1]])), bars1toN: Object.fromEntries([1, 2, 4, 8].map((N) => [N, upto[N - 1]])) };
    }
  }
  receipts.push({ id: "LR2g", measured: curves, threshold: "reported; sets K (C4 start value 4)", pass: true, ms: Math.round(performance.now() - t1) });

  // chosen level under rubato (reported; rub0 x2 checked): x2 or x0.5 pressed at 15 s on the held-out 4/4 and 3/4
  // pieces. Acc1 at the chosen level = the readout divided by the ratio against the true tempo, after the press.
  const t2 = performance.now(), levelRep = {};
  for (const ratio of [2, 0.5]) for (const rubLevel of [0, 1, 2]) {
    const rows = G.tempoSuite(G.TEMPO_TEST_SEEDS).filter((x) => x.rub === rubLevel && x.meter !== "6/8").map((r) => {
      const s = levelRun(G.eventsOf(r.piece), { meter: r.meter, at: 15000, ratio, endMs: r.piece.notes[r.piece.notes.length - 1].t * 1000 + 1000 }).filter((y) => y.t_ms > 16000);
      const ev = MX.evalTempo(r.piece.truth, { samples: s.map((y) => ({ t_ms: y.t_ms, bpm: y.bpm ? y.bpm / ratio : y.bpm, hold: y.mode === "hold" })), emitted_ms: [], settled_ms: [] }, { readFromMs: 16000 });
      return { released: s.some((y) => y.levelBpm == null), held: MX.mean(s.map((y) => +(y.levelBpm != null))), acc1: ev.acc1 };
    });
    levelRep[`x${ratio}.rub${rubLevel}`] = { pieces: rows.length, released: rows.filter((x) => x.released).length, heldShare: MX.mean(rows.map((x) => x.held)), acc1AtLevel: MX.mean(rows.map((x) => x.acc1)) };
  }
  const lv0 = levelRep["x2.rub0"], lvOk = lv0.released <= 2 && lv0.acc1AtLevel >= 0.9;
  receipts.push({ id: "LS1-level", measured: levelRep, threshold: "reported; x2 rub0: <= 2 of 18 released and Acc1 at the level >= 0.90", pass: lvOk, ms: Math.round(performance.now() - t2) });
  check("LS1-level x2 rub0 holds", lvOk, JSON.stringify(lv0));

  // LR3a: random unmetered playing, share of time steady / free (product words: bands, hysteresis, hit veto, hold)
  const fr = [], perS = [];
  for (const pc of G.freeSuite()) {
    const out = trackEvents(G.eventsOf(pc), { createOnsets, endMs: pc.notes[pc.notes.length - 1].t * 1000 + 1000 }).samples;
    fr.push(...out); perS.push(...out);
  }
  const bands = MX.bandShares(fr, 8000), raw = MX.perBands(perS, 8000);
  rec("LR3a", { steady: bands.steady, free: bands.free, loose: bands.loose, hold: bands.hold, freeOrHold: bands.free + bands.hold, rawPeriodicityBands: raw }, "steady 0%; free >= 75%", bands.steady === 0 && bands.free >= 0.75);
}

for (const r of receipts) console.log("RECEIPT", JSON.stringify(r, (k, v) => (typeof v === "number" ? Math.round(v * 10000) / 10000 : v)));
console.log(`score_beat: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
