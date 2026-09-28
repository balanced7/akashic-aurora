// Pins for the metronome and the external-beat path it exists to feed.
//
// WHAT THIS PROTECTS, and why it is worth a test file of its own. The 2026-09-27 review found that
// beat.js snaps every inferred beat 80% onto the player's nearest onset (phaseGain, beat.js:74),
// so a grid derived from the notes cannot say whether the player was ahead of the beat -- the ruler
// is cut from the thing being measured. score/index.js:102 has always accepted a FIXED `beats`
// array that bypasses the tracker, and nothing ever supplied one (score_cli.mjs returned
// `beats: null`, hardcoded). The metronome supplies it. These pins hold that path open.
//
//   node tests/score_metronome.test.mjs

import assert from "node:assert/strict";
import { buildTake } from "../arsenal/score_cli.mjs";

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); pass++; console.log(`  ok   ${name}`); }
  catch (e) { fail++; console.log(`  FAIL ${name}\n       ${e.message}`); }
}

//: A player on a steady grid, humanly imperfect. The scatter is deliberate: a take that lands
//: exactly on the grid would make the fixed-beats path look good for the wrong reason.
function take({ bpm = 100, bars = 16, jitterMs = 18, withMetro = true } = {}) {
  const P = 60000 / bpm, ev = [];
  let seed = 7;
  const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x3fffffff - 1; };
  const beats = bars * 4;
  for (let b = 0; b < beats; b++) {
    for (const frac of [0, 0.5]) {
      const t = Math.round((b + frac) * P + rnd() * jitterMs);
      const note = [60, 64, 67, 72][(b * 2 + (frac ? 1 : 0)) % 4];
      ev.push({ kind: "on", t_ms: t, note, vel: 80 });
      ev.push({ kind: "off", t_ms: t + 200, note });
      ev.push({ kind: "sound_end", t_ms: t + 200, note, by: "release" });
    }
  }
  if (withMetro) {
    for (let b = 0; b < beats; b++) {
      ev.push({ kind: "metro", t_ms: Math.round(b * P), bpm, beat: b,
                bar: Math.floor(b / 4), meter: 4, feel: "straight", latency_ms: 10 });
    }
  }
  ev.sort((a, b) => a.t_ms - b.t_ms);
  return ev;
}
const OPTS = { span: null, meter: "4/4", feel: "straight", one: null, bpm: null, taps: [], beats: null, metro: true };
const barsOf = (b) => b.view.bars || b.view.measures || [];
const tapeOf = (b) => barsOf(b).filter((x) => x.kind === "tape" || x.source === "tape").length;

console.log("score_metronome");

test("a logged click turns tape into metric bars", () => {
  const withClick = buildTake({ events: take({ withMetro: true }), options: { ...OPTS } });
  assert.ok(barsOf(withClick).length > 0, "no bars at all");
  assert.equal(tapeOf(withClick), 0, `expected no tape with a click, got ${tapeOf(withClick)}`);
});

test("the SAME notes without a click fall back to tape -- the click is what changed it", () => {
  // The control. Without this the test above could pass because the notes were easy.
  const noClick = buildTake({ events: take({ withMetro: false }), options: { ...OPTS } });
  assert.ok(tapeOf(noClick) > 0, "the inferred rung notated this take metrically without any click; "
    + "either the tracker improved or the fixture is too easy to prove anything");
});

test("--no-metro ignores the clicks, so the inferred rung stays comparable", () => {
  const forced = buildTake({ events: take({ withMetro: true }), options: { ...OPTS, metro: false } });
  assert.ok(tapeOf(forced) > 0, "metro:false still used the clicks; the comparison path is gone");
});

test("supplied beats outrank the logged click", () => {
  const ev = take({ withMetro: true });
  const mine = [];
  for (let b = 0; b < 64; b++) mine.push(b * 600);
  const b = buildTake({ events: ev, options: { ...OPTS, beats: mine } });
  assert.equal(tapeOf(b), 0);
});

test("fewer than three clicks is not a grid and must not be used as one", () => {
  const ev = take({ withMetro: false });
  ev.push({ kind: "metro", t_ms: 0, bpm: 100, beat: 0 });
  ev.push({ kind: "metro", t_ms: 600, bpm: 100, beat: 1 });
  const b = buildTake({ events: ev, options: { ...OPTS } });
  assert.ok(tapeOf(b) > 0, "two clicks were accepted as a beat grid; index.js:102 requires >= 3");
});

test("metro events never enter the note stream", () => {
  // LOG_KINDS must not carry "metro": a click is not a note, and counting it as one would put
  // phantom onsets into every statistic the lane computes.
  const withClick = buildTake({ events: take({ withMetro: true }), options: { ...OPTS } });
  const noClick = buildTake({ events: take({ withMetro: false }), options: { ...OPTS, metro: false } });
  const count = (b) => (b.view.notes || []).length || (b.notes || []).length || 0;
  if (count(withClick) || count(noClick)) {
    assert.equal(count(withClick), count(noClick),
      "the click changed the note count; metro leaked into the note stream");
  }
});

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
