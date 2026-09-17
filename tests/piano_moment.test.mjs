// Node tests for the moment (arsenal/web/piano/moment.js): the energy, pace, pulse, flow, density, intensity, artifact, arc
// and mood the "Instruments of light" round hangs its wind, fog and crystal on. Zero dependencies, synthetic performances
// on a manual clock, read through a real harmony-feel:
//   node tests/piano_moment.test.mjs           everything, the cost and allocation measurements included
//   node tests/piano_moment.test.mjs --quick   without them
// Sections: the shape of the reading; silence; a tender ballad; a metronomic staccato run; the artifact an altered dominant
// builds and releases; a plain triad that builds nothing; a pedal wash; the arc of a crescendo; the eight mood labels; the
// restart event; frame-rate independence; robustness; the pins of the musical-behaviour audit's must-fixes (MF1..MF6); and
// the frame budget.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { PerformanceObserver } from "node:perf_hooks";
import v8 from "node:v8";
import vm from "node:vm";
import { createHarmonyFeel } from "../arsenal/web/piano/harmony-feel.js";
import { createMoment, MOMENT, ARCS, LABELS, MOMENT_API } from "../arsenal/web/piano/moment.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const quick = process.argv.includes("--quick");
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const near = (a, b, eps = 1e-9) => Math.abs(a - b) <= eps;
const LETTER_PC = [0, 2, 4, 5, 7, 9, 11];
function midiOf(tok) {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(tok);
  if (!m) throw new Error(`bad note ${tok}`);
  return (Number(m[3]) + 1) * 12 + LETTER_PC["CDEFGAB".indexOf(m[1])] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0);
}
const notes = (text) => text.trim().split(/\s+/).map(midiOf);
const fx = (v) => (typeof v === "number" ? v.toFixed(3) : String(v));

// Plays a script against one harmony-feel and one moment, the way the host does: state.sounding holds every note that
// sounds, a strike replaces the entry with a new t0 and a bumped strike counter, a release while the pedal is down keeps the
// entry with held false and pedal true, and the pedal coming up drops what only it was holding.
// script events: { t, on: "C4 E4", vel, dur, off: "E4", chord: "C" | null, pedal: true | false }
//   on with dur: the notes come off dur seconds later (or fall to the pedal).
// opts: fps, options (createMoment options), pressed (an older host: state.pressed, entries with no held or strike field).
function play(script, until, opts = {}) {
  const fps = opts.fps || 60;
  const feel = createHarmonyFeel();
  const moment = createMoment(opts.options);
  const map = new Map();
  const state = opts.pressed ? { pressed: map, pedal: false, chord: null } : { sounding: map, pedal: false, chord: null };
  if (opts.noChordField) delete state.chord;
  const events = script.map((ev) => ({ ...ev })).sort((a, b) => a.t - b.t);
  const offs = [];  // { t, midi }
  const frames = [];
  const strikes = new Map();
  function release(mi, t) {
    const e = map.get(mi);
    if (!e) return;
    if (state.pedal && !opts.pressed) { e.held = false; e.pedal = true; e.tRelease = t; } else map.delete(mi);
  }
  let k = 0;
  for (let i = 0; i <= Math.round(until * fps); i++) {
    const t = i / fps;
    for (;;) {
      const nextEv = k < events.length ? events[k].t : Infinity;
      let oi = -1, nextOff = Infinity;
      for (let j = 0; j < offs.length; j++) if (offs[j].t < nextOff) { nextOff = offs[j].t; oi = j; }
      if (nextEv > t + 1e-9 && nextOff > t + 1e-9) break;
      if (nextOff <= nextEv) { const o = offs.splice(oi, 1)[0]; release(o.midi, o.t); continue; }
      const ev = events[k++];
      if ("pedal" in ev) {
        state.pedal = ev.pedal;
        if (!ev.pedal) for (const [mi, e] of map) if (!e.held) map.delete(mi);
      }
      for (const mi of ev.off ? notes(ev.off) : []) release(mi, ev.t);
      for (const mi of ev.on ? notes(ev.on) : []) {
        const n = (strikes.get(mi) || 0) + 1;
        strikes.set(mi, n);
        const vel = ev.vel ?? 80;
        map.set(mi, opts.pressed ? { vel, t0: ev.t } : { vel, t0: ev.t, held: true, pedal: false, tRelease: 0, strike: n });
        if (ev.dur) offs.push({ t: ev.t + ev.dur, midi: mi });
      }
      if ("chord" in ev) state.chord = ev.chord ? { name: ev.chord, nns: "", key: "" } : null;
    }
    const dt = i === 0 ? 0 : 1 / fps;
    const f = feel.update(state, dt, t);
    const m = moment.update(state, dt, t, f);
    frames.push({
      t, i, energy: m.energy, pace: m.pace, pulse: m.pulse, flow: m.flow, density: m.density, intensity: m.intensity,
      artifact: { ...m.artifact }, arc: m.arc, mood: { ...m.mood }, events: { ...m.events }, raw: { ...m.raw },
      colour: { ...f.colour }, count: f.voices.count,
    });
  }
  return { frames, feel, moment, state, map, fps, at: (t) => frames[Math.min(frames.length - 1, Math.round(t * fps))] };
}
const last = (run) => run.frames[run.frames.length - 1];
// A line of single notes: names in order, starting at t0, with the gaps between onsets (cycled), each held dur.
function line(names, t0, gaps, dur, vel) {
  const out = [];
  let t = t0;
  notes(names).forEach((mi, i) => {
    out.push({ t: +t.toFixed(6), on: "", midi: mi, dur, vel });
    t += gaps[i % gaps.length];
  });
  return out.map((e) => ({ t: e.t, on: nameOf(e.midi), dur: e.dur, vel: e.vel }));
}
const NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const nameOf = (mi) => `${NAMES[mi % 12]}${Math.floor(mi / 12) - 1}`;
const transitions = (frames, key) => frames.reduce((acc, fr, i) => (i === 0 || fr[key] !== frames[i - 1][key] ? [...acc, { t: fr.t, v: fr[key] }] : acc), []);

// ============================================================================================ the frame budget ==
// Measured first, before any other section has run: the budget claim is about the module in a host, where every entry
// has one shape. The harness below feeds entries of several shapes (an older host, nonsense, fakes), which turns the
// property loads polymorphic, and a polymorphic load of a double field boxes a number. Measured after that, the same
// loop reads a few hundred bytes a frame that the module never allocates in a host.
const budgetReport = [];
if (!quick) {
  const big = new Map();
  const spread = [0, 7, 12, 16, 19, 23, 26, 28, 31, 35, 38, 40, 43, 47, 50, 52, 55, 59, 62, 64];
  for (let i = 0; i < 20; i++) big.set(36 + spread[i], { vel: 70 + i, t0: i * 0.01, held: i % 5 !== 0, pedal: i % 5 === 0, tRelease: 0, strike: 1 });
  const state = { sounding: big, pedal: true, chord: { name: "Cmaj9", nns: "", key: "" } };
  const other = { sounding: big, pedal: true, chord: { name: "G7b9", nns: "", key: "" } };
  const feel = createHarmonyFeel(), moment = createMoment();
  const times = new Array(20000);
  times[0] = "boxed";
  for (let i = 0; i < times.length; i++) times[i] = i / 60 + 0.5;
  const DT = 1 / 60;
  const entries = [...big.values()];
  // every 16th frame one entry is re-struck (its counter bumps and its t0 moves up), every 32nd the chord name changes
  const runBoth = (n, from) => {
    for (let i = 0; i < n; i++) {
      const t = times[(from + i) % times.length];
      if ((i & 15) === 0) { const e = entries[i % 20]; e.strike++; e.t0 = t; }
      const s = (i >> 5) % 2 ? other : state;
      moment.update(s, DT, t, feel.update(s, DT, t));
    }
  };
  const runFeel = (n, from) => {
    for (let i = 0; i < n; i++) {
      const t = times[(from + i) % times.length];
      if ((i & 15) === 0) { const e = entries[i % 20]; e.strike++; e.t0 = t; }
      feel.update((i >> 5) % 2 ? other : state, DT, t);
    }
  };
  runBoth(200000, 0);
  check("twenty notes read as full density", moment.frame.density > 0.99 && moment.frame.energy > 0.2, `${fx(moment.frame.density)} ${fx(moment.frame.energy)}`);

  let bestBoth = Infinity, bestFeel = Infinity;
  for (let trial = 0; trial < 5; trial++) {
    let t0 = performance.now(); runBoth(100000, 0); const both = (performance.now() - t0) / 100000;
    t0 = performance.now(); runFeel(100000, 0); const only = (performance.now() - t0) / 100000;
    if (both < bestBoth) bestBoth = both;
    if (only < bestFeel) bestFeel = only;
  }
  const cost = Math.max(0, bestBoth - bestFeel);
  budgetReport.push(`update() with 20 sounding notes: ${(cost * 1000).toFixed(2)} us (${cost.toFixed(5)} ms) per frame for the moment alone `
    + `(feel + moment ${(bestBoth * 1000).toFixed(2)} us, feel alone ${(bestFeel * 1000).toFixed(2)} us), best of 5 x 100k`);
  check("update costs under 0.05 ms for 20 sounding notes", cost < 0.05 && bestBoth < 0.1, `${cost.toFixed(5)} ms`);

  let collect = null;
  try { v8.setFlagsFromString("--expose-gc"); collect = vm.runInNewContext("gc"); } catch { collect = null; }
  if (typeof collect === "function") {
    let collections = 0;
    const watch = new PerformanceObserver((list) => { collections += list.getEntries().length; });
    watch.observe({ entryTypes: ["gc"] });
    runBoth(50000, 3);
    collect(); collect();
    await new Promise((r) => setTimeout(r, 30));
    collections = 0;
    const before = v8.getHeapStatistics().used_heap_size;
    runBoth(400000, 7);
    const grew = v8.getHeapStatistics().used_heap_size - before;
    await new Promise((r) => setTimeout(r, 60));
    watch.disconnect();
    budgetReport.push(`400k frames (feel + moment) after a collection by hand: ${collections} collections, heap +${grew} bytes `
      + `(${(grew / 400000).toFixed(3)} a frame)`);
    check("nothing is allocated per frame once it is warm: no collection was needed", collections === 0, String(collections));
    check("nothing is allocated per frame once it is warm: the heap barely moves", grew < 400000, `${grew} bytes over 400k frames`);
  } else budgetReport.push("allocation: skipped (no gc available)");
}

// ============================================================================================ the shape of a reading ==
check("MOMENT_API", MOMENT_API === "arsenal.piano.moment/v1");
{
  const moment = createMoment();
  const m = moment.update({ sounding: new Map(), pedal: false, chord: null }, 0, 0, null);
  const keys = (o) => Object.keys(o).join(",");
  check("m keys", keys(m) === "energy,pace,pulse,flow,density,intensity,artifact,arc,mood,events,raw", keys(m));
  check("m.artifact keys", keys(m.artifact) === "growth,seed,age,released,releaseStrength", keys(m.artifact));
  check("m.mood keys", keys(m.mood) === "valence,arousal,label", keys(m.mood));
  check("m.events keys", keys(m.events) === "build,peak,release,restart", keys(m.events));
  check("a new moment sits at rest", m.energy === 0 && m.pace === 0 && m.pulse === 0 && m.flow === 0 && m.density === 0
    && m.intensity === 0 && m.artifact.growth === 0 && m.arc === "resting" && m.mood.label === "calm" && m.mood.arousal === 0);
  check("the seed is a small integer", Number.isInteger(m.artifact.seed) && m.artifact.seed > 0 && m.artifact.seed < 2 ** 30);
  check("ARCS and LABELS are the documented words", ARCS.join(",") === "resting,building,peak,sustaining,releasing"
    && LABELS.join(",") === "calm,tender,yearning,searching,playful,tense,dark,triumphant");
  check("createMoment reports its constants and takes overrides", createMoment({ growFull: 9 }).constants.growFull === 9
    && moment.constants.growFull === MOMENT.growFull);
}
{  // every constant carries a plain-language line in the module header, and the header says what the mood is not
  const source = readFileSync(here("../arsenal/web/piano/moment.js"), "utf8");
  const header = source.slice(0, source.indexOf("\nexport const MOMENT_API"));
  const documented = new Set(header.split("\n").map((line) => line.replace(/^\/\/\s*/, "").trim().split(/\s+/)[0]));
  const missing = Object.keys(MOMENT).filter((k) => !documented.has(k));
  check("every MOMENT constant is documented in the header", missing.length === 0, missing.join(" "));
  check("the header explains every output", ["m.energy", "m.pace", "m.pulse", "m.flow", "m.density", "m.intensity",
    "m.artifact", "growth", "seed", "age", "released", "releaseStrength", "m.arc", "m.mood", "valence", "arousal", "label",
    "m.events", "build", "peak", "release", "restart", "m.raw"].every((w) => header.includes(w)));
  check("the header says the mood is an estimate of the music, not the player's emotions",
    header.includes("ESTIMATE OF THE MUSIC'S CHARACTER") && header.includes("not a claim about"));
  check("every label has its rule in the header", LABELS.every((l) => new RegExp(`^//\\s+${l}\\s`, "m").test(header)));
  check("no CRLF in the module or the test", !source.includes("\r") && !readFileSync(here("./piano_moment.test.mjs"), "utf8").includes("\r"));
}
{  // one object, refreshed in place, through strikes, chords and silence
  const feel = createHarmonyFeel(), moment = createMoment();
  const map = new Map();
  const state = { sounding: map, pedal: false, chord: null };
  const m0 = moment.update(state, 0, 0, feel.update(state, 0, 0));
  const ids = [m0, m0.artifact, m0.mood, m0.events, m0.raw];
  let stable = true, sawNaN = false;
  for (let i = 1; i <= 600; i++) {
    const t = i / 60;
    if (i % 40 === 0) { map.set(60 + (i % 24), { vel: 90, t0: t, held: true, pedal: false, tRelease: 0, strike: i }); state.chord = { name: i % 80 ? "C" : "G7", nns: "", key: "" }; }
    if (i % 200 === 150) { map.clear(); state.chord = null; }
    const m = moment.update(state, 1 / 60, t, feel.update(state, 1 / 60, t));
    const now = [m, m.artifact, m.mood, m.events, m.raw];
    for (let j = 0; j < ids.length; j++) if (now[j] !== ids[j]) stable = false;
    for (const v of [m.energy, m.pace, m.pulse, m.flow, m.density, m.intensity, m.artifact.growth, m.artifact.age, m.mood.valence, m.mood.arousal]) if (v !== v) sawNaN = true;
  }
  check("update returns the same objects every frame", stable);
  check("moment.frame is that same object", moment.frame === m0);
  check("no NaN anywhere over ten seconds of strikes and rests", !sawNaN);
}

// ========================================================================================================== silence ==
{
  const run = play([{ t: 0, on: "C3 E3 G3 B3 D4", vel: 100, chord: "Cmaj9", pedal: true }, { t: 1, off: "C3 E3 G3 B3 D4", pedal: false, chord: null }], 12);
  const q = last(run);
  check("silence decays energy, intensity and density to 0", q.energy < 0.01 && q.intensity < 0.01 && q.density < 0.01,
    `${fx(q.energy)} ${fx(q.intensity)} ${fx(q.density)}`);
  check("silence decays pace, pulse and flow to 0", q.pace < 0.01 && q.pulse < 0.01 && q.flow < 0.01, `${fx(q.pace)} ${fx(q.pulse)} ${fx(q.flow)}`);
  check("silence rests the arc, the artifact and the mood", q.arc === "resting" && q.artifact.growth === 0 && q.artifact.age === 0
    && q.mood.label === "calm" && q.mood.arousal < 0.01, `${q.arc} ${fx(q.artifact.growth)} ${q.mood.label}`);
  check("the chord was alive before the silence", run.at(0.9).energy > 0.3 && run.at(0.9).density > 0.4 && run.at(0.9).artifact.age > 0.8);
  check("reset() puts everything back at rest", (() => {
    run.moment.reset();
    const m = run.moment.frame;
    return m.energy === 0 && m.arc === "resting" && m.mood.label === "calm" && m.artifact.growth === 0 && m.raw.energy === 0;
  })());
}

// ================================================================================================= a tender ballad ==
// Soft, major, legato under the pedal, the melody in free time.
const BALLAD = [
  { t: 0, pedal: true, chord: "Cmaj7", on: "C3 E3 G3 B3", vel: 40, dur: 1.8 }, { t: 0, on: "E4", vel: 42, dur: 0.6 },
  { t: 0.55, on: "G4", vel: 44, dur: 0.7 }, { t: 1.2, on: "A4", vel: 40, dur: 0.5 }, { t: 1.65, on: "G4", vel: 38, dur: 0.4 },
  { t: 1.95, pedal: false }, { t: 2.0, pedal: true, chord: "Fmaj7", on: "F3 A3 C4 E4", vel: 40, dur: 1.8 }, { t: 2.0, on: "A4", vel: 42, dur: 0.8 },
  { t: 2.7, on: "C5", vel: 44, dur: 0.6 }, { t: 3.25, on: "B4", vel: 40, dur: 0.9 },
  { t: 3.95, pedal: false }, { t: 4.0, pedal: true, chord: "G", on: "G3 B3 D4", vel: 40, dur: 1.8 }, { t: 4.0, on: "D5", vel: 42, dur: 0.7 },
  { t: 4.6, on: "B4", vel: 40, dur: 0.5 }, { t: 5.05, on: "G4", vel: 38, dur: 0.9 },
  { t: 5.95, pedal: false }, { t: 6.0, pedal: true, chord: "Cmaj7", on: "C3 E3 G3 B3", vel: 40, dur: 1.8 }, { t: 6.0, on: "E4", vel: 42, dur: 0.6 },
  { t: 6.55, on: "G4", vel: 44, dur: 0.7 }, { t: 7.2, on: "C5", vel: 40, dur: 0.5 },
];
{
  const run = play(BALLAD, 7.6);
  const q = last(run);
  report.push(`ballad: energy ${fx(q.energy)} pace ${fx(q.pace)} pulse ${fx(q.pulse)} flow ${fx(q.flow)} density ${fx(q.density)} `
    + `valence ${fx(q.mood.valence)} arousal ${fx(q.mood.arousal)} label ${q.mood.label}`);
  check("ballad: flow reads legato", q.flow > 0.6, fx(q.flow));
  check("ballad: pulse reads low-mid (rubato)", q.pulse > 0.1 && q.pulse < 0.6, fx(q.pulse));
  check("ballad: arousal is low", q.mood.arousal < 0.35, fx(q.mood.arousal));
  check("ballad: valence is positive (major, consonant)", q.mood.valence > 0.15, fx(q.mood.valence));
  check("ballad: the label is tender", q.mood.label === "tender", q.mood.label);
  check("ballad: pace is a few notes a second", q.pace > 1 && q.pace < 5, fx(q.pace));
}

// ===================================================================================== a metronomic staccato run ==
{
  const RUN = "C4 D4 E4 F4 G4 A4 B4 C5 B4 A4 G4 F4 E4 D4 C4 D4 E4 F4 G4 A4 B4 C5 B4 A4 G4 F4 E4 D4 C4 D4 E4 F4";
  const run = play(line(RUN, 0.5, [0.125], 0.03, 95), 4.4);  // 8 notes a second for 4 s, each held 30 ms
  const q = run.at(4.4);
  report.push(`staccato run: pace ${fx(q.pace)} pulse ${fx(q.pulse)} flow ${fx(q.flow)} energy ${fx(q.energy)} arousal ${fx(q.mood.arousal)} label ${q.mood.label}`);
  check("run: pulse reads metronomic", q.pulse > 0.85, fx(q.pulse));
  check("run: flow reads detached (a note held a quarter of its gap)", q.flow < 0.4, fx(q.flow));
  check("run: the same run with every note held into the next reads legato", play(line(RUN, 0.5, [0.125], 0.14, 95), 4.4).at(4.4).flow > 0.9);
  check("run: pace reads 8 a second within 5%", Math.abs(q.pace - 8) / 8 < 0.05, fx(q.pace));
  check("run: the label is playful (major, detached, steady)", q.mood.label === "playful", q.mood.label);
  check("run: arousal is mid-high", q.mood.arousal >= 0.4, fx(q.mood.arousal));
  // the same run over a held altered dominant is tense
  const tense = play([{ t: 0.3, on: "G2 F3 B3 Ab3", vel: 100, chord: "G7b9", pedal: true, dur: 0.2 }, ...line(RUN, 0.5, [0.125], 0.05, 95)], 4.4);
  const tq = tense.at(4.4);
  report.push(`the same run over G7b9: tension ${fx(tq.colour.tension)} label ${tq.mood.label}`);
  check("run over an altered dominant: the label is tense", tq.mood.label === "tense", tq.mood.label);
}

// ======================================================================== the artifact an altered dominant builds ==
{
  const script = [{ t: 0, on: "G2 B3 F4 G#4 A#4 D5", vel: 105, chord: "G7b9#9", pedal: true, dur: 0.3 },
    { t: 3, off: "G2 B3 F4 G#4 A#4 D5", pedal: false }, { t: 3, on: "C3 E3 G3 C4", vel: 95, chord: "C", pedal: true, dur: 0.3 }];
  const run = play(script, 5);
  const a = run.at(0.75), b = run.at(1.5), c = run.at(2.2), d = run.at(2.95);
  report.push(`G7b9#9 held: intensity ${fx(a.intensity)} at 0.75 s, ${fx(b.intensity)} at 1.5 s, ${fx(c.intensity)} at 2.2 s, `
    + `${fx(d.intensity)} at 2.95 s; growth ${fx(d.artifact.growth)} at the change; energy ${fx(b.energy)}`);
  check("intensity builds over the held chord", a.intensity < b.intensity && b.intensity < c.intensity && b.intensity > 0.3,
    `${fx(a.intensity)} ${fx(b.intensity)} ${fx(c.intensity)}`);
  check("intensity eases toward the midpoint of its targets with intensityBuild rising and intensityDecay falling, every frame", (() => {
    let worst = 0;
    for (let i = 1; i < run.frames.length; i++) {
      const p = run.frames[i - 1], c = run.frames[i], mid = 0.5 * (p.raw.intensity + c.raw.intensity);
      const k = Math.exp(-(1 / 60) / (mid > p.intensity ? MOMENT.intensityBuild : MOMENT.intensityDecay));
      worst = Math.max(worst, Math.abs(c.intensity - (mid + (p.intensity - mid) * k)));
    }
    return worst < 1e-9;
  })());
  check("intensity is about 63% of the way to a settled target after one build time constant", (() => {
    // a fixed target: a tense chord read by a fake feel at full energy
    const moment = createMoment({ intensityEnergyFull: 1e-9 });
    const f = { voices: { spread: 0 }, colour: { tension: 0.8, lushness: 0, brightness: 0.5, openness: 0 }, dance: { consonance: 1, motion: "static" }, events: { chordChanged: false } };
    const map = new Map([[60, { vel: 100, t0: 0, held: true, pedal: false, tRelease: 0, strike: 1 }]]);
    const state = { sounding: map, pedal: false, chord: { name: "C", nns: "", key: "" } };
    let v = 0;
    for (let i = 0; i <= 90; i++) v = moment.update(state, i ? 1 / 60 : 0, i / 60, f).intensity;
    return near(v, 0.8 * (1 - Math.exp(-1)), 0.01);
  })());
  check("growth rises and never falls while the chord holds", run.frames.slice(1, run.at(2.95).i + 1)
    .every((fr, i, arr) => i === 0 || fr.artifact.growth >= arr[i - 1].artifact.growth) && d.artifact.growth > 0.3, fx(d.artifact.growth));
  check("age counts from the chord's start", near(d.artifact.age, 2.95, 1e-6), fx(d.artifact.age));
  const releases = run.frames.filter((fr) => fr.artifact.released);
  check("the chord change releases on exactly one frame", releases.length === 1 && near(releases[0].t, 3, 1e-9),
    releases.map((fr) => fr.t).join(" "));
  check("releaseStrength is the growth at release, on that frame only", releases.length === 1
    && near(releases[0].artifact.releaseStrength, d.artifact.growth, 0.02) && run.at(3 + 1 / 60).artifact.releaseStrength === 0
    && run.frames.every((fr) => fr.artifact.released || fr.artifact.releaseStrength === 0), fx(releases[0]?.artifact.releaseStrength));
  check("the release event fires with it", releases.length === 1 && releases[0].events.release
    && run.frames.filter((fr) => fr.events.release).length === 1);
  check("the seed changes at the change and holds otherwise", d.artifact.seed !== run.at(3).artifact.seed
    && run.at(1).artifact.seed === d.artifact.seed && run.at(3).artifact.seed === run.at(4.5).artifact.seed);
  check("growth restarts from 0 on the new chord", run.at(3).artifact.growth === 0 && run.at(3).artifact.age === 0
    && run.at(4.5).artifact.age > 1.4, `${fx(run.at(3).artifact.growth)} ${fx(run.at(4.5).artifact.age)}`);
  check("intensity decays on the plain chord that follows", run.at(5).intensity < d.intensity * 0.3
    && run.frames.slice(run.at(3.3).i).every((fr, i, arr) => i === 0 || fr.intensity <= arr[i - 1].intensity + 1e-12), fx(run.at(5).intensity));
}
// a plain triad builds nothing worth releasing
{
  const run = play([{ t: 0, on: "C3 E3 G3 C4", vel: 100, chord: "C", pedal: true, dur: 0.3 },
    { t: 3, off: "C3 E3 G3 C4", pedal: false }, { t: 3, on: "F3 A3 C4 F4", vel: 100, chord: "F", pedal: true, dur: 0.3 }], 4);
  const q = run.at(2.95);
  report.push(`C triad held: intensity ${fx(q.intensity)} growth ${fx(q.artifact.growth)} energy ${fx(run.at(1).energy)}`);
  check("a plain triad keeps intensity low", q.intensity < 0.05, fx(q.intensity));
  check("a plain triad builds no artifact worth releasing", q.artifact.growth < MOMENT.releaseMin
    && run.frames.every((fr) => !fr.artifact.released && !fr.events.release), fx(q.artifact.growth));
  check("the seed still changes at the chord change", run.at(2.95).artifact.seed !== run.at(3).artifact.seed);
}
// the pedal wash of a wide lush chord
{
  const wash = play([{ t: 0, on: "C2 G2 E3 B3 D4 F#4 A4", vel: 90, chord: "Cmaj13#11", pedal: true, dur: 0.25 }], 2.5);
  const dry = play([{ t: 0, on: "C2 G2 E3 B3 D4 F#4 A4", vel: 90, chord: "Cmaj13#11", dur: 2.5 }], 2.5);
  const triad = play([{ t: 0, on: "C3 E3 G3", vel: 90, chord: "C", pedal: true, dur: 0.25 }], 2.5);
  const w = wash.at(2), d = dry.at(2), p = triad.at(2);
  report.push(`Cmaj13#11 wash: energy ${fx(w.energy)} lushness ${fx(w.colour.lushness)} intensity ${fx(w.intensity)}; fingers only: `
    + `energy ${fx(d.energy)} intensity ${fx(d.intensity)}; a pedalled triad: intensity ${fx(p.intensity)}`);
  check("a lush wash raises intensity well above a triad", w.intensity > 0.3 && w.intensity > p.intensity + 0.25, `${fx(w.intensity)} against ${fx(p.intensity)}`);
  check("the pedal wash carries more energy than the same chord held by fingers", w.energy > d.energy, `${fx(w.energy)} against ${fx(d.energy)}`);
  check("the wash reads lush in harmony-feel and that lushness is what intensity follows", w.colour.lushness > 0.8
    && w.raw.intensity <= w.colour.lushness + 1e-9);
}

// ======================================================================================= the arc of a crescendo ==
{
  // an arpeggio that gets louder and faster over four seconds, holds full for one, then stops
  const script = [{ t: 0, chord: null }];
  const arp = notes("C3 G3 C4 E4 G4 C5 E5 G5");
  let t = 0.2, k = 0;
  while (t < 5) {
    const u = Math.min(1, t / 4);
    script.push({ t: +t.toFixed(4), on: nameOf(arp[k++ % arp.length]), vel: Math.round(30 + 95 * u), dur: 0.5 });
    t += 0.4 - 0.31 * u;
  }
  const run = play(script, 12);
  const seq = transitions(run.frames, "arc");
  report.push(`crescendo arc: ${seq.map((s) => `${s.v}@${s.t.toFixed(2)}`).join(" > ")}; drive peak ${fx(Math.max(...run.frames.map((fr) => fr.raw.drive)))}`);
  const words = seq.map((s) => s.v);
  check("the arc runs resting > building > peak > releasing", words.slice(0, 4).join(",") === "resting,building,peak,releasing", words.join(","));
  check("and comes to rest after the stop", words[words.length - 1] === "resting" && words.length <= 6, words.join(","));
  check("no arc state flickers: every state holds at least arcHold", seq.every((s, i) => i === seq.length - 1 || seq[i + 1].t - s.t >= MOMENT.arcHold - 1e-9));
  const builds = run.frames.filter((fr) => fr.events.build), peaks = run.frames.filter((fr) => fr.events.peak);
  check("build and peak events fire once each, on the entry frames", builds.length === 1 && peaks.length === 1
    && builds[0].arc === "building" && peaks[0].arc === "peak" && builds[0].t < peaks[0].t);
  check("peak comes after the crescendo's rise and before the stop", peaks[0].t > 2 && peaks[0].t < 6, fx(peaks[0]?.t));
}

// ===================================================================================== the eight mood labels ==
{
  const passages = {
    calm: { script: [{ t: 0, chord: null }, ...line("C4 E4 G4 E4 D4 C4 E4 G4", 0.2, [1.5], 0.5, 40)], until: 11 },
    tender: { script: BALLAD, until: 7.6 },
    yearning: { script: [
      { t: 0, pedal: true, chord: "Am9", on: "A2 E3 G3 C4 B4", vel: 45, dur: 3.5 }, { t: 0.3, on: "E5", vel: 45, dur: 1.2 },
      { t: 1.4, on: "D5", vel: 42, dur: 1.1 }, { t: 2.4, on: "C5", vel: 40, dur: 1.2 }, { t: 3.9, pedal: false },
      { t: 4.0, pedal: true, chord: "Am9", on: "A2 E3 G3 C4 B4", vel: 45, dur: 3.5 }, { t: 4.3, on: "E5", vel: 45, dur: 1.2 },
      { t: 5.4, on: "D5", vel: 42, dur: 1.1 }, { t: 6.4, on: "C5", vel: 40, dur: 1.2 }], until: 7.5 },
    searching: { script: [{ t: 0, chord: null }, ...line("D4 F4 E4 G4 F#4 A4 G4 E4 F4 D4 E4 C4", 0.2, [0.4, 0.9, 0.5, 1.3, 0.6, 1.1, 0.45, 1.2, 0.5], 0.7, 50)], until: 8.5 },
    playful: { script: [{ t: 0, chord: null }, ...line("C4 E4 G4 C5 E5 C5 G4 E4 C4 E4 G4 C5 E5 C5 G4 E4 C4 E4 G4 C5 E5 C5 G4 E4 C4 E4 G4 C5", 0.3, [0.16], 0.06, 85)], until: 4.9 },
    tense: { script: [{ t: 0, chord: "G7b9#9", pedal: true, on: "G2 B3 F4 G#4 A#4 D5", vel: 110, dur: 0.3 },
      { t: 0.5, on: "G2 B3 F4 G#4 A#4 D5", vel: 112, dur: 0.3 }, { t: 1.0, on: "G2 B3 F4 G#4 A#4 D5", vel: 115, dur: 0.3 },
      { t: 1.5, on: "G2 B3 F4 G#4 A#4 D5", vel: 118, dur: 0.3 }, { t: 2.0, on: "G2 B3 F4 G#4 A#4 D5", vel: 120, dur: 0.3 },
      { t: 2.5, on: "G2 B3 F4 G#4 A#4 D5", vel: 120, dur: 0.3 }, { t: 3.0, on: "G2 B3 F4 G#4 A#4 D5", vel: 120, dur: 0.3 }], until: 3.4 },
    dark: { script: [
      { t: 0, pedal: true, chord: "Am", on: "A1 E2 A2 C3 E3", vel: 70, dur: 3.5 }, { t: 0.4, on: "C4", vel: 66, dur: 1.2 },
      { t: 1.5, on: "E4", vel: 64, dur: 1.1 }, { t: 2.5, on: "A3", vel: 62, dur: 1.2 }, { t: 3.9, pedal: false },
      { t: 4.0, pedal: true, chord: "Am", on: "A1 E2 A2 C3 E3", vel: 70, dur: 3.5 }, { t: 4.4, on: "C4", vel: 66, dur: 1.2 },
      { t: 5.5, on: "E4", vel: 64, dur: 1.1 }, { t: 6.5, on: "A3", vel: 62, dur: 1.2 }], until: 7.5 },
    triumphant: { script: [{ t: 0, pedal: true, chord: "C" }, ...[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5].map((t) => ({ t, on: "C2 G2 C3 G3 E4 G4 C5", vel: 120, dur: 0.4 }))], until: 3.9 },
  };
  for (const [want, p] of Object.entries(passages)) {
    const run = play(p.script, p.until);
    const q = last(run);
    report.push(`mood ${want.padEnd(10)} -> ${q.mood.label.padEnd(10)} valence ${fx(q.mood.valence)} arousal ${fx(q.mood.arousal)} `
      + `tension ${fx(q.colour.tension)} lush ${fx(q.colour.lushness)} bright ${fx(q.colour.brightness)} open ${fx(q.colour.openness)} `
      + `flow ${fx(q.flow)} pulse ${fx(q.pulse)} density ${fx(q.density)}`);
    check(`mood: the ${want} passage reads ${want}`, q.mood.label === want, q.mood.label);
  }
  // hysteresis: the label never changes more often than moodHold allows
  const run = play(BALLAD, 7.6);
  const seq = transitions(run.frames, (fr) => fr.mood.label);
  const labelSeq = run.frames.reduce((acc, fr, i) => (i === 0 || fr.mood.label !== run.frames[i - 1].mood.label ? [...acc, fr.t] : acc), []);
  check("mood labels hold at least moodHold between changes", labelSeq.every((t, i) => i === 0 || t - labelSeq[i - 1] >= MOMENT.moodHold - 1e-9), labelSeq.join(" "));
  void seq;
}

// ================================================================================================ the restart ==
{
  const run = play([{ t: 0.5, on: "C4 E4 G4", vel: 80, chord: "C", dur: 1 }, { t: 2.5, on: "C4 E4 G4", vel: 80, chord: "C", dur: 1 },
    { t: 6, on: "F4 A4 C5", vel: 80, chord: "F", dur: 1 }], 7);
  const restarts = run.frames.filter((fr) => fr.events.restart).map((fr) => fr.t);
  check("restart fires on the first sound and after a rest of restartGap or more, not after a shorter rest",
    restarts.length === 2 && near(restarts[0], 0.5, 1e-9) && near(restarts[1], 6, 1e-9), restarts.join(" "));
  check("the same chord coming back after a rest starts a fresh artifact (new seed, age 0)",
    run.at(2.5).artifact.seed !== run.at(1).artifact.seed && run.at(2.5).artifact.age === 0 && run.at(3.4).artifact.age > 0.8);
}

// ===================================================================================== frame-rate independence ==
{
  // every event on a frame both rates share (multiples of 1/6 s), so the raw readings change on the same instants
  const script = [{ t: 0, on: "G2 B3 F4 G#4 A#4 D5", vel: 105, chord: "G7b9#9", pedal: true, dur: 1 / 6 },
    ...line("C5 D5 E5 F5 G5 A5", 1, [1 / 6], 1 / 6, 100),
    { t: 2.5, off: "G2 B3 F4 G#4 A#4 D5", pedal: false }, { t: 2.5, on: "C2 G2 E3 B3 D4 F#4", vel: 90, chord: "Cmaj9#11", pedal: true, dur: 1 / 6 },
    { t: 4, off: "C2 G2 E3 B3 D4 F#4", pedal: false, chord: null }];
  const slow = play(script, 5.5, { fps: 30 }), fast = play(script, 5.5, { fps: 144 });
  let worst = 0, worstAt = "";
  for (const t of [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]) {
    const a = slow.at(t), b = fast.at(t);
    for (const key of ["energy", "intensity"]) {
      const d = Math.abs(a[key] - b[key]) / Math.max(0.05, Math.abs(a[key]));
      if (d > worst) { worst = d; worstAt = `${key} at ${t}: ${a[key].toFixed(6)} vs ${b[key].toFixed(6)}`; }
    }
    const d = Math.abs(a.artifact.growth - b.artifact.growth) / Math.max(0.05, a.artifact.growth);
    if (d > worst) { worst = d; worstAt = `growth at ${t}: ${a.artifact.growth.toFixed(6)} vs ${b.artifact.growth.toFixed(6)}`; }
  }
  report.push(`30 fps against 144 fps: energy, intensity and growth differ by ${(worst * 100).toFixed(3)}% at worst (${worstAt})`);
  check("30 fps and 144 fps agree within 2% on energy, intensity and growth", worst < 0.02, worstAt);
  const relS = slow.frames.filter((fr) => fr.artifact.released), relF = fast.frames.filter((fr) => fr.artifact.released);
  check("both rates release the artifact twice (the change at 2.5 s, the end after the stop) with the same strength within 2%",
    relS.length === 2 && relF.length === 2 && near(relS[0].t, 2.5, 1e-9) && near(relF[0].t, 2.5, 1e-9)
    && relS.every((fr, i) => Math.abs(fr.artifact.releaseStrength - relF[i].artifact.releaseStrength) / fr.artifact.releaseStrength < 0.02),
    `${relS.map((fr) => `${fr.t.toFixed(3)}:${fx(fr.artifact.releaseStrength)}`).join(" ")} against ${relF.map((fr) => `${fr.t.toFixed(3)}:${fx(fr.artifact.releaseStrength)}`).join(" ")}`);
}

// ================================================================================================= robustness ==
{
  const feel = createHarmonyFeel(), moment = createMoment();
  const map = new Map([[60, { vel: 90, t0: 0, held: true, pedal: false, tRelease: 0, strike: 1 }]]);
  const state = { sounding: map, pedal: false, chord: { name: "C", nns: "", key: "" } };
  let threw = null;
  const values = (m) => [m.energy, m.pace, m.pulse, m.flow, m.density, m.intensity, m.artifact.growth, m.artifact.age,
    m.artifact.releaseStrength, m.mood.valence, m.mood.arousal, m.raw.slope, m.raw.drive];
  let clean = true;
  try {
    for (const [dt, t] of [[0, 0], [0, 0], [1e9, 1e9], [NaN, 1e9 + 1], [undefined, undefined], [-1, 5], [1 / 60, 5], [1 / 60, 2], [1e-12, 2.5]]) {
      const m = moment.update(state, dt, t, feel.update(state, dt, t));
      if (values(m).some((v) => v !== v || v === Infinity || v === -Infinity)) clean = false;
    }
    moment.update(null, 1 / 60, 6, null);
    moment.update({}, 1 / 60, 6.1, {});
    moment.update({ sounding: null }, 1 / 60, 6.2, undefined);
    moment.update({ sounding: new Map([[200, { vel: 1, t0: 6 }], [-3, { vel: 1, t0: 6 }], [61, null], [61.5, { vel: 1, t0: 6 }]]) }, 1 / 60, 6.3, feel.frame);
    if (values(moment.frame).some((v) => v !== v)) clean = false;
  } catch (e) { threw = e; }
  check("dt 0, a huge dt, NaN, a missing dt, a clock going back, and a missing or nonsense state or f never throw and never NaN",
    threw === null && clean, threw ? String(threw.stack) : "NaN or Infinity seen");
}
{  // an older host: state.pressed, entries with no held, pedal or strike field (a re-strike replaces the entry: new t0)
  const old = play(line("C4 E4 G4 C5 G4 E4 C4 E4 G4 C5 G4 E4", 0.2, [0.25], 0.2, 90), 3.3, { pressed: true });
  const q = last(old);
  check("state.pressed is read when state.sounding is missing: strikes, pace and energy are seen", q.pace > 3 && q.energy > 0.2 && q.density > 0.3,
    `${fx(q.pace)} ${fx(q.energy)} ${fx(q.density)}`);
  const re = play([{ t: 0, on: "C4", vel: 90, dur: 0.2 }, { t: 0.5, on: "C4", vel: 90, dur: 0.2 }, { t: 1, on: "C4", vel: 90, dur: 0.2 }], 1.2, { pressed: true });
  check("a re-strike of the same key counts as a strike", re.at(1.2).raw.pace > 1.1, fx(re.at(1.2).raw.pace));
}
{  // a host with no state.chord at all: three or more voices are the chord
  const run = play([{ t: 0, on: "G2 B3 F4 G#4 A#4 D5", vel: 105, pedal: true, dur: 0.3 }, { t: 3, off: "G2 B3 F4 G#4 A#4 D5", pedal: false },
    { t: 3, on: "C3 E3 G3", vel: 95, pedal: true, dur: 0.3 }], 4, { noChordField: true });
  check("with no chord field the artifact still builds on the pitch-class set and releases on its change",
    run.at(2.9).artifact.growth > 0.2 && run.frames.filter((fr) => fr.artifact.released).length === 1, fx(run.at(2.9).artifact.growth));
}

// ================================================================ the musical-behaviour audit's must-fixes, pinned ==
// One pin per must-fix of the audit that read twelve scripted passages through the module, so none of them comes back.
{  // MF1: calm is a low-arousal word. Loud playing with a dark or neutral colour used to fall back to 'calm' whenever
   // no rule fitted; now a fortissimo minor riff reads dark, a shout-chorus stab tense or triumphant, an fff Am dark.
  const riff = [{ t: 0, pedal: true, chord: "Em" }];
  for (let k = 0; k < 28; k++) riff.push({ t: +(0.2 + k * 0.2143).toFixed(4), on: k % 2 ? "E3 G3 B3" : "E2 B2 E3", vel: 118, dur: 0.15 });
  const rock = play(riff, 7);
  const rockLabels = new Set(rock.frames.filter((fr) => fr.t >= 2 && fr.t <= 6.2).map((fr) => fr.mood.label));
  const stabs = [{ t: 0, chord: "Bb13" }];
  for (let k = 0; k < 16; k++) {
    const bar = k >> 2, at = +(0.2 + k * 0.5625).toFixed(4);
    stabs.push(bar % 2 ? { t: at, chord: "G7#9", on: "G2 F3 B3 D#4 A#4", vel: 120, dur: 0.16 } : { t: at, chord: "Bb13", on: "Bb2 Ab3 D4 G4 C5", vel: 120, dur: 0.16 });
  }
  const shout = play(stabs, 9.5);
  const shoutLabels = new Set(shout.frames.filter((fr) => fr.t >= 2 && fr.t <= 9.2).map((fr) => fr.mood.label));
  const am = play([{ t: 0, pedal: true, chord: "Am" }, ...[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5].map((t) => ({ t, on: "A1 E2 A2 C3 E3 A3 C4 E4", vel: 127, dur: 0.4 }))], 4);
  report.push(`MF1: ff Em riff ${[...rockLabels].join(",")} (arousal ${fx(rock.at(4).mood.arousal)} valence ${fx(rock.at(4).mood.valence)}); `
    + `shout stabs ${[...shoutLabels].join(",")} (arousal ${fx(shout.at(6).mood.arousal)}); fff Am ${am.at(3.9).mood.label} (arousal ${fx(am.at(3.9).mood.arousal)})`);
  check("MF1: a fortissimo minor riff never reads calm or tender, and reads dark", !rockLabels.has("calm") && !rockLabels.has("tender") && rockLabels.has("dark"), [...rockLabels].join(","));
  check("MF1: shout-chorus stabs read tense, triumphant or playful, never calm", shoutLabels.size > 0 && [...shoutLabels].every((l) => ["tense", "triumphant", "playful"].includes(l)), [...shoutLabels].join(","));
  check("MF1: an fff low A minor reads dark", am.at(3.9).mood.label === "dark", am.at(3.9).mood.label);
  check("MF1: calm never shows once arousal is mid or high", [...rock.frames, ...shout.frames, ...am.frames].every((fr) => fr.t < 1.5 || fr.mood.label !== "calm" || fr.mood.arousal < MOMENT.moodLowArousal));
}
{  // MF2: pulse is rhythm-invariant. The coefficient of variation of the intervals read any steady rhythm with mixed
   // note values (swing, quarter-eighth-eighth) as rubato; the grid fit reads the rhythm's unit and does not care.
  const swing = [{ t: 0, chord: "C" }];
  for (let bar = 0; bar < 10; bar++) for (let b = 0; b < 4; b++) {
    const t0 = +(0.2 + bar * 1.2 + b * 0.3).toFixed(4);
    swing.push({ t: t0, on: b % 2 ? "C4 E4 G4" : "C2", vel: 90, dur: 0.12 });                       // LH oom-pah on the beat
    swing.push({ t: t0, on: "E5", vel: 85, dur: 0.15 }, { t: +(t0 + 0.2).toFixed(4), on: "G5", vel: 80, dur: 0.08 });  // RH long-short (2:1)
  }
  const sw = play(swing, 12.4);
  const march = play([{ t: 0, chord: "C" }, ...line("C4 E4 G4 C5 G4 E4 C4 E4 G4 C5 G4 E4 C4 E4 G4 C5 G4 E4 C4 E4 G4 C5 G4 E4", 0.2, [0.5, 0.25, 0.25], 0.2, 90)], 8.4);
  const rubato = play([{ t: 0, chord: null }, ...line("D4 F4 E4 G4 F#4 A4 G4 E4 F4 D4 E4 C4", 0.2, [0.4, 0.9, 0.5, 1.3, 0.6, 1.1, 0.45, 1.2, 0.5], 0.7, 50)], 8.5);
  const meanPulse = (run, from, to) => { const fs = run.frames.filter((fr) => fr.t >= from && fr.t <= to); return fs.reduce((a, fr) => a + fr.pulse, 0) / fs.length; };
  report.push(`MF2: pulse swing ${fx(meanPulse(sw, 3, 12))} march ${fx(meanPulse(march, 3, 8.2))} rubato ${fx(rubato.at(8.5).pulse)} straight run ${fx(play(line("C4 D4 E4 F4 G4 A4 B4 C5 B4 A4 G4 F4 E4 D4 C4 D4 E4 F4 G4 A4", 0.5, [0.125], 0.03, 95), 3).at(3).pulse)}`);
  check("MF2: a swung stride at a fixed tempo reads steady (pulse >= 0.7 over the passage)", meanPulse(sw, 3, 12) >= 0.7, fx(meanPulse(sw, 3, 12)));
  check("MF2: a march (quarter, eighth, eighth) at a fixed tempo reads steady (pulse >= 0.7)", meanPulse(march, 3, 8.2) >= 0.7, fx(meanPulse(march, 3, 8.2)));
  check("MF2: a rubato line still reads rubato (pulse 0.1..0.4)", rubato.at(8.5).pulse > 0.1 && rubato.at(8.5).pulse < 0.4, fx(rubato.at(8.5).pulse));
  check("MF2: two beats are no evidence of a grid (the fit counts in full only from pulseConfident intervals)",
    play([{ t: 0, chord: null }, { t: 0.2, on: "C4", vel: 60, dur: 0.3 }, { t: 1.2, on: "E4", vel: 60, dur: 0.3 }, { t: 2.2, on: "G4", vel: 60, dur: 0.3 }], 2.8).at(2.8).raw.pulse <= 0.5 + 1e-9);
}
{  // MF3: the artifact needs no chord name. The host hands over state.chord null for a cluster (its reader names only
   // chords); the sounding pitch-class set is the chord then: it holds from the frame three or more pitch classes
   // sound, a different set changes it, and it builds and releases like a named chord.
  const CL = "C2 C#2 D2 D#2 C4 C#4 D4 D#4 E4 F4 F#4 G4", CL2 = "F2 F#2 G2 G#2 A4 A#4 B4 C5 C#5";
  const script = [{ t: 0, pedal: true, chord: null }];
  {  // API audit: a partial f must not poison later frames (the NaN stayed for good before)
    const feelP = createHarmonyFeel(), moP = createMoment();
    const st = { sounding: new Map([[60, { vel: 90, t0: 0, held: true, pedal: false, tRelease: null, strike: 1 }]]), chord: null, pedal: false };
    let tt = 0;
    for (let i = 0; i < 120; i++) { tt += 1 / 60; moP.update(st, 1 / 60, tt, feelP.update(st, 1 / 60, tt)); }
    const nonFinite = (o, p = "") => Object.entries(o).flatMap(([k, v]) => typeof v === "number" ? (Number.isFinite(v) ? [] : [p + k]) : (v && typeof v === "object" && !Array.isArray(v) ? nonFinite(v, p + k + ".") : []));
    const mA = moP.update(st, 1 / 60, tt + 1 / 60, { voices: { count: 1 }, colour: {}, dance: {}, events: {} });
    check("partial f: every number stays finite on that frame", nonFinite(mA).length === 0, nonFinite(mA).join(","));
    const mB = moP.update(st, 1 / 60, tt + 2 / 60, feelP.update(st, 1 / 60, tt + 2 / 60));
    check("partial f: and on the next frame with a whole f again", nonFinite(mB).length === 0, nonFinite(mB).join(","));
  }
  for (let k = 0; k < 16; k++) script.push({ t: +(k * 0.4).toFixed(4), on: CL, vel: Math.round(28 + 99 * Math.min(1, k / 14)), dur: 0.3 });
  script.push({ t: 6.4, pedal: false }, { t: 6.4, pedal: true, on: CL2, vel: 120, dur: 0.3 }, { t: 6.8, on: CL2, vel: 120, dur: 0.3 }, { t: 7.2, on: CL2, vel: 120, dur: 0.3 }, { t: 8, pedal: false });
  const run = play(script, 10);
  const rel = run.frames.filter((fr) => fr.artifact.released);
  report.push(`MF3: null-named cluster: tension ${fx(run.at(6).colour.tension)} growth ${fx(run.at(6.35).artifact.growth)} at 6.35 s, releases ${rel.map((fr) => `${fr.t.toFixed(2)}:${fx(fr.artifact.releaseStrength)}`).join(" ")}`);
  const firstGrowth = run.frames.find((fr) => fr.artifact.growth > 0);
  check("MF3: state.chord stayed null and the artifact began from the pitch-class set within the first strike", run.state.chord === null && !!firstGrowth && firstGrowth.t <= 0.5, firstGrowth && firstGrowth.t);
  check("MF3: a null-named cluster holds one artifact: growth climbs past 0.7 across the whole crescendo", run.at(6.35).artifact.growth > 0.7, fx(run.at(6.35).artifact.growth));
  check("MF3: its age counts from the frame the set began", near(run.at(6.35).artifact.age, 6.35, 1e-6), fx(run.at(6.35).artifact.age));
  check("MF3: a different pitch-class set is the change (a release at 6.40 s), and the end releases the next set",
    rel.length === 2 && near(rel[0].t, 6.4, 1e-9) && rel[0].artifact.releaseStrength > 0.7 && rel[1].t > 8 && rel[1].artifact.releaseStrength > MOMENT.releaseMin,
    rel.map((fr) => `${fr.t.toFixed(2)}:${fx(fr.artifact.releaseStrength)}`).join(" "));
  check("MF3: the seed changed at the change and at the end", run.at(6.3).artifact.seed !== run.at(6.4).artifact.seed && run.at(6.4).artifact.seed !== run.at(9.9).artifact.seed);
}
{  // MF4: velocity sets the loudness, not the note count, and arousal's pace is the beat rate. The strike level used to
   // be a SUM of fading strikes saturating at three, so four mp strikes a second read as loud as anything, and arousal
   // counted every note of every chord, so a pp oom-pah-pah read mid arousal.
  const RUN = "C4 D4 E4 F4 G4 A4 B4 C5 B4 A4 G4 F4 E4 D4 C4 D4 E4 F4 G4 A4 B4 C5 B4 A4 G4 F4 E4 D4 C4 D4 E4 F4 G4 A4 B4 C5 B4 A4 G4 F4";
  const pp = play([{ t: 0, chord: null }, ...line(RUN, 0.2, [0.1], 0.03, 30)], 7.5), ff = play([{ t: 0, chord: null }, ...line(RUN, 0.2, [0.1], 0.03, 110)], 7.5);
  report.push(`MF4: presto at pp: energy ${fx(pp.at(4).energy)} arousal ${fx(pp.at(4).mood.arousal)}; at ff: energy ${fx(ff.at(4).energy)} arousal ${fx(ff.at(4).mood.arousal)}; `
    + `ff energy ${fx(ff.at(4.2).energy)} as the run stops, ${fx(ff.at(5.2).energy)} a second later, ${fx(ff.at(6.7).energy)} after 2.5 s`);
  check("MF4: a pp presto sits well under an ff presto in energy (0.4 or more apart)", ff.at(4).energy - pp.at(4).energy >= 0.4, `${fx(pp.at(4).energy)} ${fx(ff.at(4).energy)}`);
  check("MF4: and in arousal (0.3 or more apart), the pp one under 0.6 and the ff one over 0.85", ff.at(4).mood.arousal - pp.at(4).mood.arousal >= 0.3 && pp.at(4).mood.arousal < 0.6 && ff.at(4).mood.arousal > 0.85,
    `${fx(pp.at(4).mood.arousal)} ${fx(ff.at(4).mood.arousal)}`);
  check("MF4: energy starts falling the moment the run stops (the strike level does not hold until its weight drains: under 90% a second later, under half after 2.5 s)",
    ff.at(5.2).energy < 0.9 * ff.at(4.2).energy && ff.at(6.7).energy < 0.5 * ff.at(4.2).energy, `${fx(ff.at(4.2).energy)} -> ${fx(ff.at(5.2).energy)} -> ${fx(ff.at(6.7).energy)}`);
  const chords = play([{ t: 0, chord: "C" }, ...[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5].map((t) => ({ t, on: "C3 E3 G3 C4", vel: 80, dur: 0.4 }))], 5,
    { options: { arousalEnergy: 0, arousalDensity: 0, arousalPace: 1 } });
  check("MF4: arousal's pace term is the beat rate: four-note chords twice a second read 2 / arousalPaceFull, not 8",
    near(chords.at(5).mood.arousal, 2 / MOMENT.arousalPaceFull, 0.05) && chords.at(5).pace > 6, `${fx(chords.at(5).mood.arousal)} pace ${fx(chords.at(5).pace)}`);
  const lull = [];
  for (let bar = 0; bar < 8; bar++) {
    const t0 = +(bar * 1.8).toFixed(4);
    if (bar) lull.push({ t: +(t0 - 0.03).toFixed(4), pedal: false });
    lull.push({ t: t0, pedal: true, chord: "F" }, { t: t0, on: "F2", vel: 42, dur: 1.7 }, { t: +(t0 + 0.6).toFixed(4), on: "A3 C4 F4", vel: 34, dur: 0.55 },
      { t: +(t0 + 1.2).toFixed(4), on: "A3 C4 F4", vel: 32, dur: 0.55 }, { t: t0, on: "A4", vel: 48, dur: 0.85 }, { t: +(t0 + 0.9).toFixed(4), on: "C5", vel: 44, dur: 0.85 });
  }
  const lullaby = play(lull, 14.4);
  const mid = lullaby.frames.filter((fr) => fr.t >= 3 && fr.t <= 14.2);
  report.push(`MF4: pp oom-pah-pah: energy up to ${fx(Math.max(...mid.map((fr) => fr.energy)))}, arousal up to ${fx(Math.max(...mid.map((fr) => fr.mood.arousal)))}, pace ${fx(lullaby.at(10).pace)}`);
  check("MF4: a pp oom-pah-pah with a tune is low energy (under 0.3) and low arousal (under moodLowArousal) however busy its hands",
    mid.every((fr) => fr.energy < 0.3 && fr.mood.arousal < MOMENT.moodLowArousal) && lullaby.at(10).pace > 3, `${fx(Math.max(...mid.map((fr) => fr.energy)))} ${fx(Math.max(...mid.map((fr) => fr.mood.arousal)))}`);
}
{  // MF5: the mood does not swing at beat rate. An oom-pah over one chord (the bass alone on one, the chord on two and
   // three) swung harmony-feel's per-frame colour, and with it the valence and the label, every beat.
  const oom = [{ t: 0, pedal: false, chord: "F" }];
  for (let bar = 0; bar < 12; bar++) {
    const t0 = +(bar * 1.8).toFixed(4);
    oom.push({ t: t0, on: "F2", vel: 70, dur: 0.55 }, { t: +(t0 + 0.6).toFixed(4), on: "A3 C4 F4", vel: 60, dur: 0.5 }, { t: +(t0 + 1.2).toFixed(4), on: "A3 C4 F4", vel: 60, dur: 0.5 });
  }
  const run = play(oom, 21.6), raw = play(oom, 21.6, { options: { moodTau: 0.15 } });
  const changes = run.frames.filter((fr, i) => i > 0 && fr.t >= 2 && fr.t <= 21.5 && fr.mood.label !== run.frames[i - 1].mood.label);
  const swing = (r) => { const v = r.frames.filter((fr) => fr.t >= 18 && fr.t < 19.8).map((fr) => fr.mood.valence); return Math.max(...v) - Math.min(...v); };
  report.push(`MF5: oom-pah over one F: labels ${transitions(run.frames.slice(0, run.at(21.5).i), (fr) => fr.mood.label).length - 1} changes; valence swing within a bar ${fx(swing(run))} (unsmoothed ${fx(swing(raw))})`);
  check("MF5: an oom-pah over one chord changes label at most once after 2 s", changes.length <= 1, changes.map((fr) => `${fr.mood.label}@${fr.t.toFixed(2)}`).join(" "));
  check("MF5: the valence's swing within a bar is small (under 0.12) where the unsmoothed colour swings over 0.2", swing(run) < 0.12 && swing(raw) > 0.2, `${fx(swing(run))} ${fx(swing(raw))}`);
  check("MF5: the label holds moodHold at least between changes", (() => {
    const ts = run.frames.reduce((acc, fr, i) => (i === 0 || fr.mood.label !== run.frames[i - 1].mood.label ? [...acc, fr.t] : acc), []);
    return ts.every((t, i) => i === 0 || t - ts[i - 1] >= MOMENT.moodHold - 1e-9);
  })());
}
{  // MF6: build and peak fire once per build, not once per chord strike. The slope alone entered building on every
   // strike of a level ballad and on every step of a crescendo; the drive must now clear the level by arcStep.
  const level = [{ t: 0, pedal: true, chord: "Cmaj7" }, ...[0, 2, 4, 6, 8, 10].map((t) => ({ t, on: "C3 E3 G3 B3", vel: 62, dur: 1.8 }))];
  const lv = play(level, 12);
  const builds = lv.frames.filter((fr) => fr.events.build), peaks = lv.frames.filter((fr) => fr.events.peak);
  const steps = [{ t: 0, pedal: true, chord: "G7b9#9" }];
  for (let k = 0; k < 16; k++) steps.push({ t: +(k * 0.4).toFixed(4), on: "G2 B3 F4 G#4 A#4 D5", vel: Math.round(30 + 90 * Math.min(1, k / 14)), dur: 0.3 });
  const st = play(steps, 8);
  const sb = st.frames.filter((fr) => fr.events.build), sp = st.frames.filter((fr) => fr.events.peak);
  report.push(`MF6: level ballad arc ${transitions(lv.frames, "arc").map((s) => `${s.v}@${s.t.toFixed(2)}`).join(" > ")}; stepped crescendo arc ${transitions(st.frames, "arc").map((s) => `${s.v}@${s.t.toFixed(2)}`).join(" > ")}`);
  check("MF6: a level ballad emits at most one build and one peak, both in its opening, none per chord", builds.length <= 1 && peaks.length <= 1 && builds.every((fr) => fr.t < 3) && peaks.every((fr) => fr.t < 3),
    `builds ${builds.map((fr) => fr.t.toFixed(2)).join(" ")} peaks ${peaks.map((fr) => fr.t.toFixed(2)).join(" ")}`);
  check("MF6: a stepped crescendo is one build and one peak", sb.length === 1 && sp.length === 1 && sb[0].t < sp[0].t && sp[0].t > 3, `builds ${sb.map((fr) => fr.t.toFixed(2)).join(" ")} peaks ${sp.map((fr) => fr.t.toFixed(2)).join(" ")}`);
}

for (const line of report) console.log(line);
for (const line of budgetReport) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
