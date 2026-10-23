// Tests for arsenal/web/vj-show.js: the transition plans (on the beat, on the bar), the showcase tour, the look settings.
//   node --test tests/vj_show.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { BeatClock } from "../arsenal/web/vj-core.js";
import * as S from "../arsenal/web/vj-show.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));

// a clock that has heard beats numbered n at 120 bpm (500 ms), the last one fired at lastMs, the next predicted at nextMs
function clockAt({ lastMs = 1000, n = 0, nextMs = null, bpm = 120 } = {}) {
  const c = new BeatClock();
  c.schedule(lastMs - 200, { due_ms: 200, bpm, conf: 0.9, n, on_beat: null });
  c.update(lastMs, 0.016);
  if (nextMs !== null) c.schedule(lastMs + 10, { due_ms: nextMs - (lastMs + 10), bpm, conf: 0.9, n: n + 1, on_beat: null });
  return c;
}

test("four transition styles, each with a shader code, a length in beats and a fallback length", () => {
  assert.deepEqual(S.TRANSITION_IDS, ["crossfade", "radial", "glitch", "zoom"]);
  const codes = S.TRANSITION_IDS.map((id) => S.TRANSITIONS[id].code);
  assert.deepEqual(codes, [0, 1, 2, 3]);
  for (const id of S.TRANSITION_IDS) {
    assert.ok(S.TRANSITIONS[id].beats >= 1 && S.TRANSITIONS[id].ms >= 500, id);
  }
  assert.ok(S.STYLE_CHOICES.includes("cycle"));
});

test("cycle rotates through all four styles; a fixed choice stays fixed", () => {
  const seen = new Set([0, 1, 2, 3].map((i) => S.pickStyle("cycle", i)));
  assert.equal(seen.size, 4);
  assert.equal(S.pickStyle("zoom", 7), "zoom");
});

test("without a beat a switch starts now and lasts the style's fallback", () => {
  const c = new BeatClock();
  const p = S.planTransition(5000, c, { style: "radial", quantize: "bar", bars: true });
  assert.equal(p.on, "now");
  assert.equal(p.startMs, 5000);
  assert.equal(p.ms, S.TRANSITIONS.radial.ms);
});

test("with a beat a switch starts ON the next predicted beat and lasts two beats", () => {
  const c = clockAt({ lastMs: 1000, n: 5, nextMs: 1500 });
  const p = S.planTransition(1200, c, { style: "crossfade", quantize: "beat" });
  assert.equal(p.on, "beat");
  assert.equal(p.startMs, 1500);
  assert.equal(p.ms, 1000);
  const g = S.planTransition(1200, c, { style: "glitch", quantize: "beat" });
  assert.equal(g.ms, 500, "the glitch cut is one beat");
});

test("the flywheel's next beat counts when nothing is queued", () => {
  const c = clockAt({ lastMs: 1000, n: 5 });
  const p = S.planTransition(1100, c, { style: "zoom", quantize: "beat" });
  assert.equal(p.startMs, 1500);
});

test("when the beat source numbers its bars a switch waits for the next downbeat (n % 4 === 0)", () => {
  // the last beat fired was n = 5 at 1000 ms; beats 6, 7, 8 follow at 1500, 2000, 2500: 8 is the downbeat
  const c = clockAt({ lastMs: 1000, n: 5, nextMs: 1500 });
  assert.equal(S.nextDownbeatAt(1200, c), 2500);
  const p = S.planTransition(1200, c, { style: "crossfade", quantize: "bar", bars: true });
  assert.equal(p.on, "bar");
  assert.equal(p.startMs, 2500);
  // the same clock without bar numbers falls back to the beat
  const q = S.planTransition(1200, c, { style: "crossfade", quantize: "bar", bars: false });
  assert.equal(q.on, "beat");
  assert.equal(q.startMs, 1500);
});

test("a downbeat that is itself the next beat is taken, not skipped", () => {
  const c = clockAt({ lastMs: 1000, n: 7, nextMs: 1500 });   // the next beat is n = 8
  assert.equal(S.nextDownbeatAt(1100, c), 1500);
});

test("quantize 'now' starts at once even with a beat", () => {
  const c = clockAt({ lastMs: 1000, n: 5, nextMs: 1500 });
  const p = S.planTransition(1200, c, { style: "radial", quantize: "now" });
  assert.equal(p.on, "now");
  assert.equal(p.startMs, 1200);
  assert.equal(p.ms, 1000);
});

test("an unknown style falls back to the crossfade", () => {
  const c = new BeatClock();
  const p = S.planTransition(0, c, { style: "teleport" });
  assert.equal(p.style, "crossfade");
  assert.equal(p.code, 0);
});

test("transition progress is 0 before the start and 1 after the end", () => {
  assert.equal(S.transitionProgress(900, 1000, 1000), 0);
  assert.equal(S.transitionProgress(1500, 1000, 1000), 0.5);
  assert.equal(S.transitionProgress(2600, 1000, 1000), 1);
});

test("the look's stored settings are validated; anything odd keeps its default", () => {
  assert.deepEqual(S.normalizeLook(null), { ...S.LOOK_DEFAULTS });
  const l = S.normalizeLook({ on: false, amount: 3, style: "zoom", quantize: "beat", ctl: "cc114" });
  assert.deepEqual(l, { on: false, amount: 1, style: "zoom", quantize: "beat", ctl: "cc114" });
  const bad = S.normalizeLook({ on: "yes", amount: NaN, style: "warp", quantize: "later", ctl: "<script>" });
  assert.deepEqual(bad, { ...S.LOOK_DEFAULTS });
});

test("the look scales from nothing at 0, and its glow budget never changes", () => {
  const z = S.lookParams(0);
  assert.equal(z.bloom + z.vignette + z.grain + z.aberration, 0);
  const full = S.lookParams(1);
  assert.ok(full.bloom > 0 && full.vignette > 0 && full.vignette < 0.5 && full.grain <= 0.04 && full.aberration <= 0.01);
  assert.equal(full.bloomCap, z.bloomCap);
  assert.ok(full.bloomCap <= 0.03, "the look may add at most a few percent of mean luminance");
});

test("the tour shows a card first, plays each set for its dwell, then asks for the next in a rotating style", () => {
  const tour = new S.ShowcaseTour({ dwellMs: 20000 });
  let a = tour.tick(0, { active: 0, fading: false, downbeat: false });
  assert.deepEqual(a, [{ do: "card", index: 0 }]);
  a = tour.tick(19999, { active: 0, fading: false, downbeat: false });
  assert.deepEqual(a, []);
  a = tour.tick(20000, { active: 0, fading: false, downbeat: false });
  assert.deepEqual(a, [{ do: "next", style: S.TOUR_STYLES[0] }]);
  // asked once only while the transition is on its way
  assert.deepEqual(tour.tick(20100, { active: 0, fading: true, downbeat: false }), []);
  // it lands: a card for the new set, and the dwell starts again
  a = tour.tick(21500, { active: 1, fading: false, downbeat: false });
  assert.deepEqual(a, [{ do: "card", index: 1 }]);
  a = tour.tick(41500, { active: 1, fading: false, downbeat: false });
  assert.deepEqual(a, [{ do: "next", style: S.TOUR_STYLES[1] }]);
});

test("the tour's accents land on every other downbeat and never flash, strobe or invert", () => {
  const tour = new S.ShowcaseTour({ dwellMs: 1e9, accentEveryBars: 2 });
  tour.tick(0, { active: 0, fading: false, downbeat: false });
  const accents = [];
  for (let bar = 1; bar <= 40; bar++) {
    for (const x of tour.tick(bar * 2000, { active: 0, fading: false, downbeat: true })) if (x.do === "accent") accents.push(x);
  }
  assert.equal(accents.length, 20);
  for (const x of accents) assert.ok(!S.NEVER_IN_TOUR.includes(x.effect), x.effect);
  for (const x of S.TOUR_ACCENTS) assert.ok(!S.NEVER_IN_TOUR.includes(x.effect), x.effect);
  // no accents during a transition
  assert.equal(tour.tick(90000, { active: 0, fading: true, downbeat: true }).length, 0);
});

test("the name card fades in, holds and fades out", () => {
  assert.equal(S.cardOpacity(-1), 0);
  assert.equal(S.cardOpacity(300), 0.5);
  assert.equal(S.cardOpacity(2000), 1);
  assert.ok(S.cardOpacity(600 + 3200 + 450) > 0.4 && S.cardOpacity(600 + 3200 + 450) < 0.6);
  assert.equal(S.cardOpacity(10000), 0);
});

test("the Lissajous figure's frequencies ARE the chord's just ratios", () => {
  assert.deepEqual(S.chordFrequencies([0, 4, 7], 0), [4, 5, 6], "major triad");
  assert.deepEqual(S.chordFrequencies([0, 3, 7], 0), [10, 12, 15], "minor triad");
  assert.deepEqual(S.chordFrequencies([0, 4, 7, 10], 0), [4, 5, 6, 7], "dominant seventh: the harmonic seventh");
  assert.deepEqual(S.chordFrequencies([0, 3, 7, 10], 0), [10, 12, 15, 18], "minor seventh");
  assert.deepEqual(S.chordFrequencies([0, 4, 7, 11], 0), [8, 10, 12, 15], "major seventh");
  assert.deepEqual(S.chordFrequencies([0, 3, 6], 0), [5, 6, 7], "diminished triad");
  assert.deepEqual(S.chordFrequencies([0, 5, 7], 0), [6, 9, 8], "sus4 (voice order: root, the fifth before the fourth)");
  assert.deepEqual(S.chordFrequencies([1, 5, 8], 1), [4, 5, 6], "D-flat major: transposition does not matter");
  assert.deepEqual(S.chordFrequencies([0, 7], 0), [2, 3], "a bare fifth");
  assert.deepEqual(S.chordFrequencies([4, 7], 0), [], "no root, no figure");
});

test("the Lissajous shader's tables are the JS twin's tables", () => {
  const src = readFileSync(here("../arsenal/web/presets/vj-lissajous-chords.frag"), "utf8");
  const arr = (name) => src.match(new RegExp(`const int ${name}\\[\\d+\\] = int\\[\\d+\\]\\(([^)]*)\\)`))[1].split(",").map((x) => +x.trim());
  assert.deepEqual(arr("RNUM"), [...S.JUST_NUM]);
  assert.deepEqual(arr("RDEN"), [...S.JUST_DEN]);
  assert.deepEqual(arr("PRIORITY"), [...S.VOICE_PRIORITY]);
  assert.match(src, /if \(s == 10 && !minorThird\) \{ num\[j\] = 7; den\[j\] = 4; \}/);
});

test("every set the page loads by default has a blurb, and every vj-*.frag preset is in the default list", () => {
  const src = readFileSync(here("../arsenal/web/vj.js"), "utf8");
  const block = src.match(/const DEFAULT_SETS = \[([\s\S]*?)\];/)[1];
  const ids = [...block.matchAll(/"([a-z0-9-]+)"/g)].map((m) => m[1]);
  for (const id of ids) assert.ok(S.blurbFor(id).length > 10, `blurb for ${id}`);
  const presets = readdirSync(here("../arsenal/web/presets")).filter((f) => /^vj-.*\.frag$/.test(f)).map((f) => f.slice(0, -5));
  for (const id of presets) assert.ok(ids.includes(id), `${id} is in DEFAULT_SETS`);
  assert.ok(ids.length >= 14);
});
