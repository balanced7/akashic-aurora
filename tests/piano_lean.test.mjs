// Node tests for the lean (arsenal/web/piano/lean.js): the rule that decides, from what sounds and the page's own reading,
// whether the key's 7 leans home, which voice leans, and when a lean lands. Zero dependencies, synthetic host states on a
// manual clock:
//   node tests/piano_lean.test.mjs           everything, the cost and allocation measurements included
//   node tests/piano_lean.test.mjs --quick   without them
// Sections: the frame budget (measured first, while every entry has the host's one shape); the shape of a frame and the
// header; the rule (dominants, the bright 4, the chords that make no claim, home in the bass, an unsure key, chords on the
// 7, the diminished 7th by its pitch classes); settling; landing and sidestepping (the 7 must rise to the key it pointed
// to; the six-four is not home); touching; the bass dominant with no reading; the light kept through a change of the same
// lean; frame-rate independence; the host's wiring; the painter run in node (the arch's shape, the damped bridge);
// robustness.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { PerformanceObserver } from "node:perf_hooks";
import v8 from "node:v8";
import vm from "node:vm";
import { createLean, LEAN, LEAN_API, KINDS, NONE, DOMINANT, BRIGHT4 } from "../arsenal/web/piano/lean.js";

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
const notes = (text) => text.trim().split(/\s+/).filter(Boolean).map(midiOf);
const C_MAJOR = { tonic: 0, minor: false, conf: 2 };

// Plays a script against one lean, the way the page feeds it: the page's sounding map (entries of the host's shape), the
// root of the page's own reading (or -1), and the key the page shows.
// script events: { t, on: "G2 B3 D4", off: "B3" | "all", root: 0..11 | -1, key: { tonic, minor, conf } }
// opts: fps, key (the starting key), options (createLean options).
function play(script, until, opts = {}) {
  const fps = opts.fps || 60;
  const lean = createLean(opts.options);
  const map = new Map();
  const k = opts.key || C_MAJOR;
  const input = { sounding: map, rootPc: -1, keyTonic: k.tonic, keyMinor: !!k.minor, keyConf: k.conf };
  const events = script.map((ev) => ({ ...ev })).sort((a, b) => a.t - b.t);
  const frames = [];
  const strikes = new Map();
  let e = 0;
  for (let i = 0; i <= Math.round(until * fps); i++) {
    const t = i / fps;
    while (e < events.length && events[e].t <= t + 1e-9) {
      const ev = events[e++];
      if (ev.off === "all") map.clear();
      else for (const m of ev.off ? notes(ev.off) : []) map.delete(m);
      for (const m of ev.on ? notes(ev.on) : []) {
        const n = (strikes.get(m) || 0) + 1;
        strikes.set(m, n);
        map.set(m, { held: true, vel: 80, t0: t, tRelease: 0, strike: n, trail: null });
      }
      if ("root" in ev) input.rootPc = ev.root;
      if (ev.key) { input.keyTonic = ev.key.tonic; input.keyMinor = !!ev.key.minor; input.keyConf = ev.key.conf; }
    }
    const f = lean.update(input, i === 0 ? 0 : 1 / fps, t);
    frames.push({ t, i, active: f.active, level: f.level, kind: f.kind, from: f.fromMidi, to: f.toMidi, touching: f.touching,
                  landMidi: f.land.midi, landLevel: f.land.level, kept: f.land.kept, leaned: f.events.leaned, landed: f.events.landed });
  }
  return { frames, lean, input, map, fps, at: (t) => frames[Math.min(frames.length - 1, Math.round(t * fps))] };
}
const last = (run) => run.frames[run.frames.length - 1];
const count = (run, key) => run.frames.filter((fr) => fr[key]).length;
// One chord held from t=0 (with its reading's root), read at the end.
function hold(text, root, secs = 1.5, opts = {}) {
  return last(play([{ t: 0, on: text, root }], secs, opts));
}

// ============================================================================================ the frame budget ==
// Measured first, before any other section has run: the claim is about the module in a host, where every entry and every
// input has one shape. (Measured after the robustness section below, which feeds nonsense on purpose, the property loads
// turn polymorphic and the same loop reads boxed numbers the module never allocates in a host.)
if (!quick) {
  // twenty notes each: a G7 spread up from G1 (G B D F), then C major spread up from C2 (C E G), with a C just above the
  // top B, so every other 0.8 s a lean settles and the next one lands
  const tones = (from, pcs) => { const out = []; for (let m = from; out.length < 20; m++) if (pcs.includes(m % 12)) out.push(m); return out; };
  const dom = new Map(), home = new Map();
  tones(31, [7, 11, 2, 5]).forEach((m, i) => dom.set(m, { held: true, vel: 70 + i, t0: i * 0.01, tRelease: 0, strike: 1, trail: null }));
  tones(36, [0, 4, 7]).forEach((m, i) => home.set(m, { held: i % 3 !== 0, vel: 64, t0: 0.5, tRelease: 0, strike: 1, trail: null }));
  const input = { sounding: dom, rootPc: 7, keyTonic: 0, keyMinor: false, keyConf: 2 };
  const lean = createLean();
  const times = new Array(40000);
  times[0] = "boxed";  // a tagged array: the times are already boxed, so this harness allocates nothing per call either
  for (let i = 0; i < times.length; i++) times[i] = i / 60 + 0.5;
  const DT = 1 / 60;
  // every 48 frames (0.8 s) the hands move: a dominant that settles and leans, then home, which lands
  const run = (n, from) => {
    for (let i = 0; i < n; i++) {
      const phase = ((from + i) / 48 | 0) & 1;
      input.sounding = phase ? home : dom;
      input.rootPc = phase ? 0 : 7;
      lean.update(input, DT, times[(from + i) % times.length]);
    }
  };
  run(200000, 0);
  check("the budget run leans and lands", lean.frame.fromMidi >= 0 && lean.frame.land.midi >= 0,
    `${lean.frame.fromMidi} ${lean.frame.land.midi}`);

  let best = Infinity;
  for (let trial = 0; trial < 5; trial++) {
    const t0 = performance.now();
    run(100000, 0);
    const ms = (performance.now() - t0) / 100000;
    if (ms < best) best = ms;
  }
  report.push(`update() with 20 sounding notes: ${(best * 1000).toFixed(2)} us (${best.toFixed(5)} ms) per frame, best of 5 x 100k`);
  check("update costs under 0.05 ms for 20 sounding notes", best < 0.05, `${best.toFixed(5)} ms`);

  let collect = null;
  try { v8.setFlagsFromString("--expose-gc"); collect = vm.runInNewContext("gc"); } catch { collect = null; }
  if (typeof collect === "function") {
    // A frame that allocated even one boxed number would fill the young generation and force collections: 1.6M frames of
    // 16 bytes is over 25 MB. So collect by hand first, then watch for any collection at all. With no collection, every
    // byte allocated is still in the young generation, so its growth is what the run allocated (the whole heap's size also
    // moves with old-space sweeping, by tens of KB either way, so it is reported but not judged). The growth is measured as
    // a SLOPE, not against a bound: the same run at 400k and at 1.6M frames (a chord change every 48 frames, so 8,333 and
    // 33,333 changes), the extra growth divided by the extra changes being what one chord change allocates. The fixed cost
    // of measuring (the observer, the timers) is the same in both runs and drops out.
    let collections = 0, seen = 0;
    const watch = new PerformanceObserver((list) => { collections += list.getEntries().length; });
    watch.observe({ entryTypes: ["gc"] });
    run(50000, 3);
    const young = () => v8.getHeapSpaceStatistics().filter((sp) => sp.space_name === "new_space").reduce((s, sp) => s + sp.space_used_size, 0);
    const measure = async (n) => {
      collect(); collect();
      await new Promise((r) => setTimeout(r, 30));
      collections = 0;
      const heap0 = v8.getHeapStatistics().used_heap_size, young0 = young();
      run(n, 7);
      const grew = young() - young0, heap = v8.getHeapStatistics().used_heap_size - heap0;
      await new Promise((r) => setTimeout(r, 60));
      seen += collections;
      return { grew, heap };
    };
    // two pairs, interleaved, averaged: the fixed cost wanders by some 20 KB from one measurement to the next (about 0.8
    // bytes per change on its own), where one boxed number per change would add 12 to 16
    const runs = [];
    for (const n of [400000, 1600000, 400000, 1600000]) runs.push(await measure(n));
    watch.disconnect();
    const perChange = ((runs[1].grew + runs[3].grew) - (runs[0].grew + runs[2].grew)) / 2 / (1600000 / 48 - 400000 / 48);
    const shown = runs.map((r, i) => `+${r.grew} over ${i % 2 ? "1.6M" : "400k"}`).join(", ");
    report.push(`allocation after a collection by hand: young generation ${shown} (whole heap ${runs.map((r) => `+${r.heap}`).join(", ")}): `
      + `${perChange.toFixed(2)} bytes per chord change, ${seen} collections`);
    check("nothing is allocated per frame once it is warm: no collection was needed", seen === 0, String(seen));
    check("nothing is allocated per chord change either: near zero per change (under 2 bytes; one boxed number is 12 to 16)",
      perChange < 2, `${perChange.toFixed(2)} bytes per change (young ${shown})`);
  } else report.push("allocation: skipped (no gc available)");
}

// ============================================================================================ the shape of a frame ==
check("LEAN_API", LEAN_API === "arsenal.piano.lean/v1");
check("LEAN is frozen", Object.isFrozen(LEAN));
check("LEAN's starting values", LEAN.SETTLE === 0.3 && LEAN.ATTACK === 0.25 && LEAN.RELEASE === 0.45 && LEAN.LAND === 0.6
  && LEAN.MIN_CONF === 1, JSON.stringify(LEAN));
// a landing takes the exact key the thread pointed to (the 7 rose to it), never a home note within some reach of it
check("no LAND_REACH: a landing is on toMidi itself", !("LAND_REACH" in LEAN), JSON.stringify(LEAN));
check("KINDS name the kinds", KINDS[NONE] === "none" && KINDS[DOMINANT] === "dominant" && KINDS[BRIGHT4] === "bright4");
{
  const lean = createLean();
  const f = lean.update({ sounding: new Map(), rootPc: -1, keyTonic: 0, keyMinor: false, keyConf: 2 }, 0, 0);
  const keys = (o) => Object.keys(o).join(",");
  check("frame keys", keys(f) === "active,level,kind,fromMidi,toMidi,touching,land,events", keys(f));
  check("land keys", keys(f.land) === "midi,level,kept", keys(f.land));
  check("events keys", keys(f.events) === "leaned,landed", keys(f.events));
  check("a new lean sits at rest", !f.active && f.level === 0 && f.kind === NONE && f.fromMidi === -1 && f.toMidi === -1
    && !f.touching && f.land.midi === -1 && f.land.level === 0 && f.land.kept === false && !f.events.leaned && !f.events.landed);
  check("frame is the object update returns", lean.frame === f);
  check("constants are frozen and folded", Object.isFrozen(lean.constants) && lean.constants.SETTLE === LEAN.SETTLE);
  const g = createLean({ SETTLE: 0.5, nonsense: 3, ATTACK: "x" });
  check("options override a constant by name, and nothing else", g.constants.SETTLE === 0.5 && g.constants.ATTACK === LEAN.ATTACK
    && !("nonsense" in g.constants));
}
{  // one object, refreshed in place, through a lean, a landing and silence
  const run = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "C3 E4 G4 C5", root: 0 }, { t: 2, off: "all", root: -1 }], 3);
  const f = run.lean.frame;
  check("the frame keeps its identity", run.lean.update(run.input, 1 / 60, 3.1) === f && f.land === run.lean.frame.land
    && f.events === run.lean.frame.events);
}
{  // every constant carries a plain-language line in the module header, and nothing is named after harmony-feel's words
  const source = readFileSync(here("../arsenal/web/piano/lean.js"), "utf8");
  const header = source.slice(0, source.indexOf("\nexport const LEAN_API"));
  check("header line 1", source.split("\n")[0] === "// Lean: arsenal/web/piano/lean.js (pure ES module: no three.js, no DOM). Tests: tests/piano_lean.test.mjs.");
  const documented = new Set(header.split("\n").map((line) => line.replace(/^\/\/\s*/, "").trim().split(/\s+/)[0]));
  const missing = Object.keys(LEAN).filter((k) => !documented.has(k));
  check("every LEAN constant is documented in the header, one line each starting with its name", missing.length === 0, missing.join(" "));
  check("the header quotes Daniel", header.includes("\"can you enable the lean visualization thing\"")
    && header.includes("\"What would it take to have more musical concepts be apparent, parseable, knowable and"));
  check("the header explains every output and the input", ["f.active", "f.level", "f.kind", "f.fromMidi", "f.touching", "f.land",
    "f.events", "leaned", "landed", "kept", "input.sounding", "input.rootPc", "input.keyTonic", "input.keyMinor", "input.keyConf",
    "Smoothing", "Constants"].every((w) => header.includes(w)));
  // identifiers only: comments and string literals stripped first
  const code = source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "").replace(/"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`/g, '""');
  check("no identifier named pull or tension (harmony-feel's dance.pull and colour.tension)", !/\b(pull|tension)\b/i.test(code));
  check("no DOM and no three.js", !/\b(document|window|THREE)\b/.test(code) && !/from\s+["']three/.test(source));
  check("no CRLF in the module", !source.includes("\r"));
}

// ==================================================================================================== the rule ==
{
  const g = hold("G2 B3 D4 G4 B4", 7);
  check("G B D (root 7) held past SETTLE leans: active DOMINANT", g.active && g.kind === DOMINANT && g.level > 0.9, JSON.stringify(g));
  check("... from the highest B (B4) to the C just above it", g.from === midiOf("B4") && g.to === midiOf("C5"), `${g.from} ${g.to}`);
  check("... and the C is not pressed: not touching", g.touching === false);
  const g7 = hold("G2 D3 F3 B3", 7);
  check("G7 (G D F B) leans the same way: DOMINANT from its B", g7.active && g7.kind === DOMINANT && g7.from === midiOf("B3")
    && g7.to === midiOf("C4"), JSON.stringify(g7));
  const b4 = hold("F2 A3 C4 E4 B4", 5);
  check("Fmaj7#11 (F A C E B, root 5) holds the 7 inside the 4: BRIGHT4", b4.active && b4.kind === BRIGHT4 && b4.from === midiOf("B4")
    && b4.to === midiOf("C5"), JSON.stringify(b4));
  const f4 = hold("F2 A3 C4 F4", 5);
  check("a plain F (no B) makes no claim", !f4.active && f4.kind === NONE);
  const vii = hold("B3 D4 F4", 11);
  check("vii (B D F, root 11) leans: DOMINANT from its B", vii.active && vii.kind === DOMINANT && vii.from === midiOf("B3"), JSON.stringify(vii));
  for (const [name, text, root] of [["C major triad", "C3 E4 G4", 0], ["Cmaj7 (B present)", "C3 E4 G4 B4", 0],
    ["Em (B present, root 4)", "E3 G3 B3", 4], ["Am7", "A2 E3 G3 C4", 9], ["Am9 (B present)", "A2 G3 B3 C4 E4", 9],
    ["Dm9 (ii, B absent)", "D3 F3 A3 C4 E4", 2], ["G over a C bass (root 7)", "C2 G3 B3 D4", 7],
    ["Fmaj7#11 over a C bass (root 5)", "C2 F3 A3 B3 E4", 5], ["vii over a C bass", "C2 B3 D4 F4", 11]]) {
    const r = hold(text, root);
    check(`${name}: no lean`, !r.active && r.kind === NONE && r.level === 0, JSON.stringify(r));
  }
  const unsure = hold("G2 B3 D4 G4 B4", 7, 1.5, { key: { tonic: 0, minor: false, conf: 0 } });
  check("an unsure key (keyConf 0): no lean", !unsure.active && unsure.level === 0);
  const fair = hold("G2 B3 D4 G4 B4", 7, 1.5, { key: { tonic: 0, minor: false, conf: 1 } });
  check("a fair key (keyConf 1, MIN_CONF): the lean shows", fair.active && fair.kind === DOMINANT);
  const nokey = hold("G2 B3 D4 G4 B4", 7, 1.5, { key: { tonic: -1, minor: false, conf: 3 } });
  check("no key at all: no lean", !nokey.active);
  const g_noB = hold("G2 D3 G3 D4", 7);
  check("a G with no B (no 3rd) makes no claim: the leading tone must sound", !g_noB.active);
  // minor: the raised 7th is the leading tone; the natural v makes no claim
  const am = { tonic: 9, minor: true, conf: 2 };
  const e7 = hold("E2 B3 D4 G#4", 4, 1.5, { key: am });
  check("A minor: E7 (G# present) leans from G#4 to A4", e7.active && e7.kind === DOMINANT && e7.from === midiOf("G#4")
    && e7.to === midiOf("A4"), JSON.stringify(e7));
  const em = hold("E2 B3 E4 G4", 4, 1.5, { key: am });
  check("A minor: the natural v (Em, G natural) makes no claim", !em.active);

  // A chord on the 7 leans home only as the leading-tone chord: its own minor 3rd (the key's 2) and no major 3rd. A major
  // or dominant chord on the 7 is a secondary dominant (V/iii in a major key) leaning somewhere else: its tendency tone is
  // its major 3rd, toward the key's 3 (practice.classify() calls B7 in C major "5 of 3m"). Roots as the page's reader spells them.
  const bb = { tonic: 10, minor: false, conf: 2 };
  for (const [name, text, root, key] of [["C major: B7 (B D# F# A, V/iii)", "B2 D#3 F#3 A3", 11, C_MAJOR],
    ["C major: B major (B D# F#)", "B2 D#3 F#3 B3", 11, C_MAJOR], ["Bb major: A7 (A C# E G, V/iii)", "A2 C#3 E3 G3", 9, bb]]) {
    const r = hold(text, root, 1.5, { key });
    check(`${name} on the 7: no lean (a secondary dominant leans elsewhere)`, !r.active && r.kind === NONE && r.level === 0, JSON.stringify(r));
  }
  const halfdim = hold("B2 D3 F3 A3", 11);
  check("C major: Bm7b5 (B D F A, vii half-diminished) leans: DOMINANT from its B", halfdim.active && halfdim.kind === DOMINANT
    && halfdim.from === midiOf("B2"), JSON.stringify(halfdim));

  // The leading-tone diminished 7th is symmetric, so the reader may spell its root on any of its four notes. Its pitch
  // classes decide, not the spelling: every inversion leans DOMINANT from its highest leading tone, whatever the root reads.
  for (const [key, keyName, voicings] of [[C_MAJOR, "C major", [["B2 D3 F3 Ab3", 11, "B2"], ["D3 F3 Ab3 B3", 2, "B3"],
      ["F3 Ab3 B3 D4", 5, "B3"], ["Ab2 B2 D3 F3", 8, "B2"]]],
    [am, "A minor", [["G#2 B2 D3 F3", 8, "G#2"], ["B2 D3 F3 G#3", 11, "G#3"], ["D3 F3 G#3 B3", 2, "G#3"], ["F3 G#3 B3 D4", 5, "G#3"]]]]) {
    for (const [text, root, lt] of voicings) {
      const r = hold(text, root, 1.5, { key });
      check(`${keyName}: the diminished 7th ${text} (read on root ${root}) leans DOMINANT from ${lt}`, r.active && r.kind === DOMINANT
        && r.from === midiOf(lt) && r.to === midiOf(lt) + 1, JSON.stringify(r));
    }
  }
  const spelled = [-1, ...Array.from({ length: 12 }, (_, i) => i)].map((root) => hold("Ab2 B2 D3 F3 B3", root));
  check("... the same dim 7th under every root the reader could spell (or none): DOMINANT from the highest B (B3)",
    spelled.every((r) => r.active && r.kind === DOMINANT && r.from === midiOf("B3")),
    spelled.map((r) => `${r.kind}/${r.from}`).join(" "));
  const dimTriad = [-1, 2, 5, 11].map((root) => hold("D3 F3 B3", root));
  check("... and the diminished triad on the 7 (D F B) likewise, whatever its root reads", dimTriad.every((r) => r.active
    && r.kind === DOMINANT && r.from === midiOf("B3")), dimTriad.map((r) => `${r.kind}/${r.from}`).join(" "));
}

// ==================================================================================================== settling ==
{
  const quickG = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 0.2, off: "all", root: -1 }], 2);
  check("a G chord held only 0.2 s never lights", quickG.frames.every((fr) => !fr.active && fr.level === 0) && count(quickG, "leaned") === 0);
  const g = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }], 1.5);
  check("nothing before SETTLE", g.frames.filter((fr) => fr.t < LEAN.SETTLE - 1e-9).every((fr) => fr.level === 0));
  check("leaned fires once, at the settle", count(g, "leaned") === 1 && near(g.frames.find((fr) => fr.leaned).t, 0.3, 1 / 60 + 1e-9));
  check("the light rises with ATTACK from the settle moment", near(g.at(0.55).level, 1 - Math.exp(-0.25 / 0.25), 1e-9),
    g.at(0.55).level.toFixed(6));
  // a rolled chord: every new pitch class restarts the clock, so it lights SETTLE after the last one
  const rolled = play([{ t: 0, on: "G2", root: -1 }, { t: 0.1, on: "D3" }, { t: 0.2, on: "F3" }, { t: 0.3, on: "B3", root: 7 }], 1.5);
  const firstLit = rolled.frames.find((fr) => fr.level > 0);
  check("a rolled chord lights SETTLE after its last new pitch class", firstLit && firstLit.t > 0.6 - 1e-9 && firstLit.t < 0.6 + 0.02
    && count(rolled, "leaned") === 1, firstLit ? String(firstLit.t) : "never");
  // the identity is the pitch-class set and the bass: a doubling adds no pitch class, so it does not restart the clock,
  // and the leaning voice follows the top B at once
  const doubled = play([{ t: 0, on: "G2 B3 D4", root: 7 }, { t: 0.2, on: "G4" }, { t: 0.25, on: "B4" }], 1.5);
  const lit = doubled.frames.find((fr) => fr.level > 0);
  check("a doubling (same pitch classes, same bass) does not restart the clock", lit && lit.t > 0.3 - 1e-9 && lit.t < 0.3 + 0.02,
    lit ? String(lit.t) : "never");
  check("... and the light leans from the top B it ended on", last(doubled).from === midiOf("B4") && count(doubled, "leaned") === 1);
}

// ===================================================================================================== landing ==
{
  const gc = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "C3 E4 G4 C5", root: 0 }], 4);
  const landedAt = gc.frames.filter((fr) => fr.landed);
  check("G -> C held: landed fires once", landedAt.length === 1, String(landedAt.length));
  check("... SETTLE after the C chord arrives", landedAt.length === 1 && near(landedAt[0].t, 1.3, 1 / 60 + 1e-9), landedAt[0] && String(landedAt[0].t));
  check("... on toMidi itself (C5, the C just above the B the lean came from)", landedAt.length === 1
    && landedAt[0].landMidi === landedAt[0].to && landedAt[0].landMidi === midiOf("C5"),
    landedAt[0] && `${landedAt[0].landMidi} ${landedAt[0].to}`);
  check("the landing glow eases from 1 to 0 over LAND", landedAt.length === 1 && landedAt[0].landLevel > 0.99
    && gc.at(1.6).landLevel > 0.3 && gc.at(1.6).landLevel < 0.7 && gc.at(1.95).landLevel === 0,
    `${landedAt[0] && landedAt[0].landLevel} ${gc.at(1.6).landLevel} ${gc.at(1.95).landLevel}`);
  check("the glow never rises after its first frame", gc.frames.filter((fr) => fr.t >= landedAt[0].t - 1e-9)
    .every((fr, i, a) => i === 0 || fr.landLevel <= a[i - 1].landLevel + 1e-12));
  check("no glow before the landing", gc.frames.filter((fr) => fr.t < landedAt[0].t - 1e-9).every((fr) => fr.landLevel === 0 && fr.landMidi === -1));
  check("the lean's light fades once home arrives, and its voice is kept while it fades", gc.at(1.5).level < gc.at(1).level
    && gc.at(1.5).from === midiOf("B4") && gc.at(1.5).to === midiOf("C5") && gc.at(1.5).kind === DOMINANT);
  check("and it goes out: kind 0 once the light is out", last(gc).level < 0.01 && !last(gc).active && last(gc).kind === NONE);

  const ga = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "A2 E4 A4 C5", root: 9 },
    { t: 2, off: "all", on: "C3 E4 G4 C5", root: 0 }], 5);
  check("G -> Am: no landed event (a sidestep marks nothing), not even when C follows", count(ga, "landed") === 0);
  check("... and the light falls to 0", last(ga).level < 1e-3 && !last(ga).active, last(ga).level.toExponential(3));

  const far = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "C2 C3 E3 G3", root: 0 }], 3);
  check("a home whose Cs are all far below the C the thread pointed to does not land", count(far, "landed") === 0);

  // LANDING TRUTH (the design record's binding rule): never draw that the 7 rose unless a voice actually left the 7 and
  // arrived on the 1 the thread pointed to. Home that keeps the 7, home over the 7 in the bass, and home whose 1 sounds only
  // in another octave all just let the thread fade: nothing glows. land.kept marks, for receipts only, the frame home
  // settled still holding the 7.
  const noGlow = (run) => count(run, "landed") === 0 && run.frames.every((fr) => fr.landLevel === 0 && fr.landMidi === -1);
  const keptAt = (run) => run.frames.filter((fr) => fr.kept).map((fr) => fr.t);
  const keptTop = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "C4 E4 G4 B4", root: 0 }], 3);
  check("G (B4 leaning to C5) -> Cmaj7 C4 E4 G4 B4, keeping B4: no landing, nothing glows", noGlow(keptTop),
    `${count(keptTop, "landed")} ${last(keptTop).landMidi}`);
  check("... and land.kept is true for exactly one frame, as home settles", keptAt(keptTop).length === 1
    && near(keptAt(keptTop)[0], 1.3, 1 / 60 + 1e-9), keptAt(keptTop).join(" "));
  const keptLow = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "C2 C4 E4 G4 B4", root: 0 }], 3);
  check("G -> C2 C4 E4 G4 B4 (Cmaj7 over a C bass, B4 kept): no landing", noGlow(keptLow) && keptAt(keptLow).length === 1);
  const overB = play([{ t: 0, on: "G2 B3 D4 F4", root: 7 }, { t: 1, off: "all", on: "B2 C4 E4 G4", root: 0 }], 3);
  check("G7 (B3 leaning to C4) -> Cmaj7/B (B2 C4 E4 G4, the 7 in the bass): no landing", noGlow(overB),
    `${count(overB, "landed")} ${last(overB).landMidi}`);
  check("... and home keeps the 7 there (in the bass): kept", keptAt(overB).length === 1);
  const fell = play([{ t: 0, on: "G2 B3 D4 F4", root: 7 }, { t: 1, off: "all", on: "C3 E3 G3", root: 0 }], 3);
  check("G7 (thread B3 -> C4) -> C3 E3 G3: no C4 sounds, the B fell: no landing, nothing glows (not on C3)", noGlow(fell),
    `${count(fell, "landed")} ${last(fell).landMidi}`);
  check("... and nothing is kept (no B sounds)", keptAt(fell).length === 0);
  const rose = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "C4 E4 G4 C5", root: 0 }], 3);
  const roseAt = rose.frames.filter((fr) => fr.landed);
  check("G (B4) -> C4 E4 G4 C5: B4 let go and C5 sounds: lands, on 72 (C5)", roseAt.length === 1 && roseAt[0].landMidi === 72
    && near(roseAt[0].t, 1.3, 1 / 60 + 1e-9), roseAt.map((fr) => `${fr.t}@${fr.landMidi}`).join(" "));
  check("... and nothing is kept", keptAt(rose).length === 0);
  const roseKept = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "C3 B3 E4 G4 C5", root: 0 }], 3);
  check("G (B4) -> Cmaj7 C3 B3 E4 G4 C5: B4 rose to C5 while another voice keeps B3: lands on C5, and kept says the 7 stayed",
    count(roseKept, "landed") === 1 && roseKept.frames.find((fr) => fr.landed).landMidi === 72 && keptAt(roseKept).length === 1);

  // SIX-FOUR IS NOT HOME: home's chord over the 5 (I6/4 after V) is still on the way. It neither lands nor ends the lean's
  // memory, so the real I after it can still land (while the faded light is not yet out).
  const sixFour = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "G2 C4 E4 G4 C5", root: 0 }], 3);
  check("G -> C/G (G2 C4 E4 G4 C5, the six-four): no landing", noGlow(sixFour) && keptAt(sixFour).length === 0);
  const sixFourHome = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "G2 C4 E4 G4 C5", root: 0 },
    { t: 2, off: "G2", on: "C2", root: 0 }], 4);
  const sixFourAt = sixFourHome.frames.filter((fr) => fr.landed);
  check("G -> C/G -> C (C2 C4 E4 G4 C5): the real I lands, SETTLE after it, on C5 (B4 let go, C5 sounds)",
    sixFourAt.length === 1 && near(sixFourAt[0].t, 2.3, 1 / 60 + 1e-9) && sixFourAt[0].landMidi === 72,
    sixFourAt.map((fr) => `${fr.t}@${fr.landMidi}`).join(" "));

  const breath = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", root: -1 },
    { t: 1.5, on: "C3 E4 G4 C5", root: 0 }], 3);
  check("a breath of silence between V and I still lands (silence is no identity)", count(breath, "landed") === 1);
  const longRest = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", root: -1 },
    { t: 4, on: "C3 E4 G4 C5", root: 0 }], 6);
  check("after the faded light is out (a long rest) the lean is forgotten: no landing", count(longRest, "landed") === 0);

  // LAND_FROM: a lean left before its light reached 0.3 does not land; one that reached it does
  const brief = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 0.35, off: "all", on: "C3 E4 G4 C5", root: 0 }], 2);
  check("a lean left at level 0.18 (under LAND_FROM) does not land", near(brief.at(0.35).level, 1 - Math.exp(-0.05 / 0.25), 1e-9)
    && count(brief, "landed") === 0, brief.at(0.35).level.toFixed(4));
  const enough = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 0.45, off: "all", on: "C3 E4 G4 C5", root: 0 }], 2);
  check("a lean left at level 0.45 (over LAND_FROM) lands", enough.at(0.45).level >= LEAN.LAND_FROM && count(enough, "landed") === 1);

  const passing = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "A2 E4 A4", root: 9 },
    { t: 1.1, off: "all", on: "C3 E4 G4 C5", root: 0 }], 3);
  check("an unsettled chord on the way (0.1 s) does not stop the landing", count(passing, "landed") === 1);

  const lyd = play([{ t: 0, on: "F2 A3 C4 E4 B4", root: 5 }, { t: 1, off: "all", on: "C3 E4 G4 C5", root: 0 }], 3);
  check("the bright 4 lands home too", count(lyd, "landed") === 1 && lyd.frames.find((fr) => fr.landed).landMidi === midiOf("C5"));

  const lone = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "C3 C5", root: -1 }], 3);
  check("no chord reading and C in the bass is home", count(lone, "landed") === 1);
}

// ==================================================================================================== touching ==
{
  const ebm = { tonic: 3, minor: true, conf: 2 };
  const r = hold("Bb2 D4 Eb4 F4", 10, 1.5, { key: ebm });
  check("Eb minor, Bb D Eb F over Bb (root 10): DOMINANT from D4 to Eb4", r.active && r.kind === DOMINANT && r.from === midiOf("D4")
    && r.to === midiOf("Eb4"), JSON.stringify(r));
  check("... and Eb4 sounds: touching", r.touching === true);
  const g11 = hold("G2 F3 B3 C4 D4", 7);
  check("C major, G7 with C4 pressed against B3: touching", g11.active && g11.from === midiOf("B3") && g11.touching === true);
  const g11hi = hold("G2 B3 D4 C5", 7);
  check("the C an octave away is not touching", g11hi.active && g11hi.from === midiOf("B3") && g11hi.touching === false);
}

// ======================================================================================= the bass dominant (no reading) ==
{
  const r = hold("G1 B3 D4 F4", -1);
  check("an unnamed G B D F over a low G (rootPc -1): DOMINANT", r.active && r.kind === DOMINANT && r.from === midiOf("B3"), JSON.stringify(r));
  const two = hold("G1 B3", -1);
  check("... but two pitch classes are no chord", !two.active);
  const noB = hold("G1 D4 F4", -1);
  check("... and without the B there is no lean", !noB.active);
  const otherBass = hold("D2 B3 G4 F4", -1);
  check("... nor over another bass", !otherBass.active);
}

// ================================================================================ the light through a change of the same lean ==
{
  const run = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, on: "F4", root: 7 }], 2);
  const at = run.at(1).level;
  check("a 7th added to a held V keeps the light (no dip while the new identity settles)",
    run.frames.filter((fr) => fr.t >= 1).every((fr) => fr.level >= at - 1e-12) && count(run, "leaned") === 1);
  // letting go of the top B and G keeps the identity (G B D over G), so the light moves at once: the key it came from is up
  const moved = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "B4 G4" }], 2);
  check("the top B let go: the lean moves to the B below at once (a new leaned)", moved.at(1).from === midiOf("B3")
    && last(moved).from === midiOf("B3") && count(moved, "leaned") === 2 && moved.frames.find((fr, i) => i > 30 && fr.leaned).t === 1);
  // a new bass is a new identity: the old light fades while it settles, then the new voice lights
  const rebass = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "G2 B4", on: "D2", root: 7 }], 2);
  check("a new bass under the dominant: the light waits SETTLE, then leans from the B that is left", rebass.at(1.15).from === midiOf("B4")
    && rebass.at(1.15).level < rebass.at(1).level && last(rebass).from === midiOf("B3") && count(rebass, "leaned") === 2);
  const touchOn = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, on: "C5", root: 7 }], 2);
  check("pressing home against the 7 makes a bridge at once, and keeps the light", touchOn.at(1).touching === true
    && touchOn.at(1.1).level >= touchOn.at(1).level - 1e-12);
}

// ======================================================================================== frame-rate independence ==
{
  // every event on a time both frame rates land on (a multiple of 1/6 s), so the only difference is the frame step
  const script = [{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }, { t: 1, off: "all", on: "C3 E4 G4 C5", root: 0 },
    { t: 2, off: "all", on: "G2 D3 F3 B3", root: 7 }, { t: 2 + 1 / 6, on: "C4", root: 7 }, { t: 3, off: "all", on: "A2 E4 A4 C5", root: 9 },
    { t: 3.5, off: "all", on: "F2 A3 C4 E4 B4", root: 5 }, { t: 4 + 1 / 3, off: "all", root: -1 }, { t: 4.5, on: "C3 E4 G4 C5", root: 0 }];
  const a = play(script, 6, { fps: 30 }), b = play(script, 6, { fps: 144 });
  let worst = 0, worstLand = 0;
  for (let k = 0; k <= 36; k++) {
    const t = k / 6;
    const fa = a.frames[Math.round(t * 30)], fb = b.frames[Math.round(t * 144)];
    worst = Math.max(worst, Math.abs(fa.level - fb.level));
    worstLand = Math.max(worstLand, Math.abs(fa.landLevel - fb.landLevel));
  }
  report.push(`frame-rate independence, 30 vs 144 fps over 37 shared instants: level ${worst.toExponential(2)}, land ${worstLand.toExponential(2)}`);
  check("30 and 144 fps give the same level (within 1e-6)", worst < 1e-6, worst.toExponential(3));
  check("30 and 144 fps give the same landing glow (within 1e-6)", worstLand < 1e-6, worstLand.toExponential(3));
  check("and the same events", count(a, "landed") === count(b, "landed") && count(a, "leaned") === count(b, "leaned")
    && count(a, "landed") === 2, `${count(a, "landed")} ${count(b, "landed")} ${count(a, "leaned")} ${count(b, "leaned")}`);
}

// ===================================================================================== the host's wiring (static) ==
{
  // piano.html, piano.js and the Studio (workbench.js) as text: the menu, its registration, the layer, and REC's source
  const html = readFileSync(here("../arsenal/web/piano.html"), "utf8");
  const js = readFileSync(here("../arsenal/web/piano.js"), "utf8");
  const wb = readFileSync(here("../arsenal/web/piano/workbench.js"), "utf8");
  const group = html.slice(html.lastIndexOf('<div class="group">', html.indexOf('id="key-select"')), html.indexOf("</div>", html.indexOf('id="key-select"')));
  check("piano.html: the Lean menu sits in the theory group beside Key", group.includes('id="lean-select"')
    && group.includes(">Lean (your screen)<") && /<option value="on">/.test(group) && /<option value="off">/.test(group));
  check("piano.html: the lean layer is its own canvas, aria-hidden", /<canvas id="lean-glass" class="lean-glass" aria-hidden="true"><\/canvas>/.test(html));
  const ids = /const ids=\[([^\]]*)\]/.exec(wb);
  check("workbench.js: lean-select is in the ids list", !!ids && ids[1].includes("'lean-select'"));
  check("workbench.js: and moved into Harmony & notation with the theory selects",
    /for\(const id of \[[^\]]*'lean-select'[^\]]*\]\)move\(id,'theory-controls'\)/.test(wb));
  check("piano.js: the lean is fed and drawn every frame", /tickLean\(dt, t, info\)/.test(js) && /\n  drawLean\(\);/.test(js)
    && /import \{ createLean[^}]*\} from "\.\/piano\/lean\.js"/.test(js));
  check("piano.js: the Lean pref is stored like the theory prefs, on unless turned off",
    js.includes('lean: safeGet("arsenal.piano.lean") === "off" ? "off" : "on"') && js.includes('safeSet("arsenal.piano.lean", theoryUi.lean)'));
  // REC records the WebGL canvas only: every captureStream is the piano canvas's, and the lean layer is another element
  const streams = js.match(/\b(\w+)\.captureStream\(/g) || [];
  check("piano.js: REC's only stream is the WebGL canvas (the lean layer is never captured)",
    streams.length >= 1 && streams.every((s) => s === "canvas.captureStream(") && /const canvas = \$\("piano-canvas"\);/.test(js)
    && /const leanEl = \$\("lean-glass"\);/.test(js), streams.join(" "));
  check("piano.js and piano.html: LF line endings", !js.includes("\r") && !html.includes("\r") && !wb.includes("\r"));
  const painter = js.slice(js.indexOf("// The lean, on Daniel's own screen."), js.indexOf("return theoryUi.lean;"));
  check("the painter block is found, and nothing in it is named pull or tension", painter.length > 2000
    && !/\b(pull|tension)\b/i.test(painter), String(painter.length));
  check("the painter draws nothing for land.kept (it is for receipts only)", !/\bkept\b/.test(painter));
  const paintSrc = js.slice(js.indexOf("function paintLean() {"), js.indexOf("// The lean layer takes the canvas's exact CSS box"))
    .replace(/\/\/[^\n]*/g, "");
  check("paintLean allocates nothing per frame: no new, no closures, no array or object literals, no template strings",
    paintSrc.length > 1000 && !/\bnew\b|=>|`|\[\s*\]|\{\s*\}|\bfunction\b(?!\s+paintLean)/.test(paintSrc), String(paintSrc.length));
}

// ================================================================== the painter (piano.js's own code, run in node) ==
// The painter block of piano.js (LEAN_LOOK through paintLean) and the page's key geometry, sliced from the page and run
// against a stand-in camera built the way updateCamera builds the page's (distance from the span, the 22 or 17 degree
// elevation, the look target, the lens shift; no sway) and a 2D context that records what is drawn.
{
  const js = readFileSync(here("../arsenal/web/piano.js"), "utf8");
  const geo = new Function("Theory", js.slice(js.indexOf("const KEY = {"), js.indexOf("const RAIL_Y")) + "\nreturn { KEY, keyX, isBlack };")(
    { mod: (a, n) => ((a % n) + n) % n });
  const { KEY, keyX, isBlack } = geo;
  const keys = new Map();
  for (let m = KEY.first; m <= KEY.last; m++) {  // each key's rest-pose top face, as the page builds it
    const black = isBlack(m), len = black ? KEY.blackL : KEY.whiteL, hw = (black ? KEY.blackW : KEY.whiteW) / 2, top = black ? KEY.blackTop : 0, x = keyX(m);
    keys.set(m, { m, black, pivot: { visible: true },
                  face: new Float32Array([x - hw, top, KEY.back, x + hw, top, KEY.back, x + hw, top, KEY.back + len, x - hw, top, KEY.back + len]) });
  }
  const FRAMINGS = { "9:16": { w: 1080, h: 1920, fov: 31, minSpan: 16, follow: true }, "16:9": { w: 1920, h: 1080, fov: 23, minSpan: 56, follow: false } };
  function makeCamera(framing, focusX, span) {
    const vfov = framing.fov * Math.PI / 180, tanV = Math.tan(vfov / 2), tanH = tanV * framing.w / framing.h;
    const dist = span / 2 / tanH + 7, elev = (framing.follow ? 22 : 17) * Math.PI / 180, shift = framing.follow ? 0.25 : 0.29;
    const tg = [focusX, 0.4, -0.5], pos = [tg[0], tg[1] + dist * Math.sin(elev), tg[2] + dist * Math.cos(elev)];
    const fw = tg.map((v, i) => v - pos[i]), fl = Math.hypot(...fw);
    for (let i = 0; i < 3; i++) fw[i] /= fl;
    const rt = [-fw[2], 0, fw[0]], rl = Math.hypot(...rt);  // forward x world up
    for (let i = 0; i < 3; i++) rt[i] /= rl;
    const up = [rt[1] * fw[2] - rt[2] * fw[1], rt[2] * fw[0] - rt[0] * fw[2], rt[0] * fw[1] - rt[1] * fw[0]];
    const near = 0.5, far = 900;
    return { project(v) {
      const d = [v.x - pos[0], v.y - pos[1], v.z - pos[2]];
      const xc = d[0] * rt[0] + d[1] * rt[1] + d[2] * rt[2], yc = d[0] * up[0] + d[1] * up[1] + d[2] * up[2], zc = d[0] * fw[0] + d[1] * fw[1] + d[2] * fw[2];
      v.x = xc / (zc * tanH); v.y = yc / (zc * tanV) - 2 * shift; v.z = (far + near) / (far - near) - 2 * far * near / ((far - near) * zc);
    } };
  }
  const THREE = { Vector3: class { constructor() { this.x = 0.5; this.y = 0.5; this.z = 0.5; }
    set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; } project(cam) { cam.project(this); return this; } } };
  const document = { createElement: () => ({ width: 0, height: 0, getContext: () => ({ createRadialGradient: () => ({ addColorStop() {} }), fillRect() {} }) }) };
  // log: every drawing call with the state it drew in, for the byte-identical pins below (clearRect is left out: it clears
  // the box the previous paint drew, whichever case that was)
  const ctx = { globalAlpha: 1, path: [], fills: [], strokes: [], log: [],
    beginPath() { this.path = []; this.log.push("b"); }, moveTo(x, y) { this.path.push(x, y); this.log.push("m", x, y); },
    lineTo(x, y) { this.path.push(x, y); this.log.push("l", x, y); }, closePath() { this.log.push("z"); },
    fill() { this.fills.push(this.globalAlpha); this.log.push("fill", this.globalAlpha, this.fillStyle, this.shadowColor, this.shadowBlur); },
    stroke() { this.strokes.push({ alpha: this.globalAlpha, path: this.path });
      this.log.push("stroke", this.globalAlpha, this.strokeStyle, this.lineWidth, this.lineCap, this.lineJoin, this.shadowBlur); },
    drawImage(img, x, y, w, h) { this.log.push("img", this.globalAlpha, x, y, w, h); }, clearRect() {}, setTransform() {} };
  const frame = { active: true, level: 1, kind: DOMINANT, fromMidi: -1, toMidi: -1, touching: false,
                  land: { midi: -1, level: 0, kept: false }, events: { leaned: false, landed: false } };
  const host = { camera: null, framing: null };
  const body = js.slice(js.indexOf("const LEAN_LOOK = {"), js.indexOf("// The lean layer takes the canvas's exact CSS box"));
  const page = new Function("THREE", "document", "KEY", "keys", "host", "theoryUi", "lean", "leanCtx", "leanIn", "keyView", "Theory",
    `let camera = null, framing = null;\nconst aim = () => { camera = host.camera; framing = host.framing; };\n${body}\n`
    + "return { aim, paintLean, leanBox, leanXY, leanW, LEAN_LOOK };")(
    THREE, document, KEY, keys, host, { lean: "on" }, { frame }, ctx, {}, {}, { pcOf: () => 0 });
  // Paints one thread from `from` to `to` (from + 1 unless given) under a camera on that pair (or on `focus`), and returns its
  // centreline in CSS px. thread false paints no thread; land [midi, level] adds a landing glow.
  function paint(fm, framingId, { touching = false, level = 1, focus = null, to = fm + 1, thread = true, land = null } = {}) {
    const fr = FRAMINGS[framingId];
    host.framing = fr;
    host.camera = makeCamera(fr, focus === null ? (keyX(fm) + keyX(to)) / 2 : focus, fr.minSpan);
    page.aim();
    page.leanBox.css = fr.follow ? 900 : 1600; page.leanBox.cssH = fr.follow ? 1600 : 900; page.leanBox.dpr = 1;
    frame.active = thread; frame.fromMidi = fm; frame.toMidi = to; frame.touching = touching; frame.level = level;
    frame.land.midi = land ? land[0] : -1; frame.land.level = land ? land[1] : 0;
    ctx.fills.length = 0; ctx.strokes.length = 0; ctx.log.length = 0;
    page.paintLean();
    const line = ctx.strokes.length ? ctx.strokes[0].path : [];
    const pts = [];
    for (let i = 0; i + 1 < line.length; i += 2) pts.push([line[i], line[i + 1]]);
    return { pts, alpha: ctx.fills[0], up: [page.leanXY[6], page.leanXY[7]] };
  }
  // The thread's shape, against the line between its two feet (a the leaning key, b home): how far along that line each
  // point lies, and how far off it, on the side nearest the screen's up.
  function shape(pts) {
    const a = pts[0], b = pts[pts.length - 1], cx = b[0] - a[0], cy = b[1] - a[1], len = Math.hypot(cx, cy);
    const ux = cx / len, uy = cy / len;
    let nx = -uy, ny = ux;
    if (ny > 0 || (ny === 0 && nx > 0)) { nx = -nx; ny = -ny; }  // the normal on the screen-up side (y grows down)
    const along = pts.map((p) => (p[0] - a[0]) * ux + (p[1] - a[1]) * uy), off = pts.map((p) => (p[0] - a[0]) * nx + (p[1] - a[1]) * ny);
    const top = off.indexOf(Math.max(...off));
    return { len, along, off, apexAlong: along[top] / len, apexOff: off[top], mid: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2],
             middle: pts[(pts.length - 1) / 2] };
  }

  // MIXED PAIRS, white to black (G -> Ab in Ab major, D -> Eb, A -> Bb, C -> Db, F -> Gb) and black to white (G# -> A in
  // A minor, D# -> E, A# -> B, C# -> D, F# -> G). On each key's own anchor the black key's foot sat further back and higher,
  // so the two feet stood almost one over the other on screen: lifted along the screen's up the thread curled past home into
  // a hook, and lifted off the line between the feet it bowed sideways into a "C" (the visual verifier, 2026-10-13, both
  // framings). The decision (the spec owner, Vandor, 2026-10-13): the white key's foot at the black key's front depth, so the
  // feet sit side by side and the lift points up the screen. Pinned in both framings at the camera's centre, and in the wide
  // view at both edges (a key 22 units off the centre, where perspective slants the keys most): both feet on the black keys'
  // front line; the thread's middle within 15 degrees of straight up from the middle of its feet; its highest point between
  // the feet (at least 15% of their gap in from each) and over the higher one; and no part of it out past either foot.
  const FRONT_Z = KEY.back + KEY.blackL;
  const VIEWS = [["9:16", "centre", 0], ["16:9", "centre", 0], ["16:9", "right edge", -22], ["16:9", "left edge", 22]];
  const focusOf = (fm, tm, off) => (off === 0 ? (keyX(fm) + keyX(tm)) / 2 : keyX(fm) + off);
  const MIXED = [["G4 -> Ab4", 67], ["D4 -> Eb4", 62], ["A4 -> Bb4", 69], ["C4 -> Db4", 60], ["F4 -> Gb4", 65],
    ["G#4 -> A4", 68], ["D#4 -> E4", 63], ["A#4 -> B4", 70], ["C#4 -> D4", 61], ["F#4 -> G4", 66]];
  let worstDeg = 0, worstApex = 0.5;
  for (const [framingId, where, off] of VIEWS) {
    for (const [name, fm] of MIXED) {
      for (const touching of [false, true]) {
        const p = paint(fm, framingId, { focus: focusOf(fm, fm + 1, off), touching });
        const label = `${framingId} ${where}: ${name}${touching ? " touching (the bridge)" : ""}`;
        if (p.pts.length < 10) { check(`${label}: draws`, false); continue; }
        const W = page.leanW;
        check(`${label}: both feet stand side by side on the black keys' front line (z = KEY.back + KEY.blackL)`,
          Math.abs(W[2] - FRONT_Z) < 1e-6 && Math.abs(W[5] - FRONT_Z) < 1e-6, `from z ${W[2].toFixed(4)}, to z ${W[5].toFixed(4)}`);
        const a = p.pts[0], b = p.pts[p.pts.length - 1], m = p.pts[(p.pts.length - 1) / 2];
        const lx = m[0] - (a[0] + b[0]) / 2, ly = m[1] - (a[1] + b[1]) / 2;
        const deg = Math.acos(Math.max(-1, Math.min(1, -ly / Math.hypot(lx, ly)))) * 180 / Math.PI;
        check(`${label}: the lift points up the screen (the thread's middle within 15 degrees of straight up from its feet's)`,
          deg < 15, `${deg.toFixed(1)} degrees off straight up`);
        let top = p.pts[0];
        for (const q of p.pts) if (q[1] < top[1]) top = q;
        const apex = (top[0] - a[0]) / (b[0] - a[0]);
        check(`${label}: its apex lies between the feet (15% of their gap in from each) and over the higher foot`,
          apex >= 0.15 && apex <= 0.85 && top[1] <= Math.min(a[1], b[1]) - (touching ? 2 : 4),
          `apex at ${apex.toFixed(2)} of the way, ${(Math.min(a[1], b[1]) - top[1]).toFixed(1)} px over the higher foot, feet ${(b[0] - a[0]).toFixed(1)} px apart`);
        const xs = p.pts.map((q) => q[0]), lo = Math.min(a[0], b[0]), hi = Math.max(a[0], b[0]);
        check(`${label}: no sideways bow (no part of the thread more than 1 px out past either foot)`,
          Math.min(...xs) >= lo - 1 && Math.max(...xs) <= hi + 1, `x ${Math.min(...xs).toFixed(1)}..${Math.max(...xs).toFixed(1)}, feet ${lo.toFixed(1)}..${hi.toFixed(1)}`);
        if (!touching) { worstDeg = Math.max(worstDeg, deg); if (Math.abs(apex - 0.5) > Math.abs(worstApex - 0.5)) worstApex = apex; }
      }
    }
  }
  report.push(`white-black pairs, 4 views: the lift at most ${worstDeg.toFixed(1)} degrees off straight up, the apex at worst ${worstApex.toFixed(2)} of the way`);
  // the landing glow on home after a mixed step stands where the thread came down: over the same foot, on the front line
  for (const [framingId, where, off] of VIEWS) {
    for (const [name, fm] of [["G4 -> Ab4", 67], ["G#4 -> A4", 68]]) {
      paint(fm, framingId, { focus: focusOf(fm, fm + 1, off), land: [fm + 1, 0.6] });
      const xy = page.leanXY, W = page.leanW;
      check(`${framingId} ${where}: ${name} landed: the glow's foot is the thread's foot on home, on the black keys' front line`,
        Math.abs(xy[8] - xy[2]) < 1e-9 && Math.abs(xy[9] - xy[3]) < 1e-9 && Math.abs(W[8] - FRONT_Z) < 1e-6,
        `glow foot ${xy[8].toFixed(2)},${xy[9].toFixed(2)}, thread foot ${xy[2].toFixed(2)},${xy[3].toFixed(2)}, z ${W[8].toFixed(4)}`);
      paint(fm, framingId, { focus: focusOf(fm, fm + 1, off), land: [fm + 1, 0.3], thread: false });
      check(`${framingId} ${where}: ${name} landed, the thread gone: the glow's foot is still on the front line`,
        Math.abs(page.leanW[8] - FRONT_Z) < 1e-6 && ctx.log.includes("img"), `z ${page.leanW[8].toFixed(4)}`);
    }
  }
  // SAME-COLOUR PAIRS are untouched by that decision, to the byte: every drawing call (its points, opacity, colour, width,
  // blur) and the box kept for the next clear, hashed per view, against hashes taken from the painter before the decision.
  // White to white (B -> C, E -> F, the bridge), black to black (a painter fed C# -> D#, F# -> G#: the lean never makes one,
  // the painter must not care), and the landing glow on a white home whose leaning key was white (C5 after B4, F4 after E4).
  {
    const SAME = [[71, 72, {}], [64, 65, {}], [71, 72, { touching: true, level: 0.8 }], [76, 77, { level: 0.5 }],
      [61, 63, {}], [66, 68, {}], [68, 70, { touching: true }], [71, 72, { land: [72, 0.6] }], [64, 65, { land: [65, 0.3], thread: false }]];
    // taken 2026-10-13 from paintLean as it stood before the decision (every same-colour case above, in this order)
    const GOLDEN = { "9:16 centre": "604b26989468a16f", "16:9 centre": "4b1df8343660fbaf", "16:9 right edge": "1a89b3703d738478",
      "16:9 left edge": "4de5c8b3749ec317" };
    for (const [framingId, where, off] of VIEWS) {
      const hash = createHash("sha256");
      for (const [fm, tm, opts] of SAME) {
        paint(fm, framingId, { to: tm, focus: focusOf(fm, tm, off), ...opts });
        const bx = page.leanBox;
        hash.update(JSON.stringify(ctx.log) + JSON.stringify([bx.x0, bx.y0, bx.x1, bx.y1, bx.had]));
      }
      const got = hash.digest("hex").slice(0, 16), key = `${framingId} ${where}`;
      check(`${key}: white-white and black-black threads, bridges and landing glows draw byte-identical to before the decision`,
        got === GOLDEN[key], `${got} (pinned ${GOLDEN[key]})`);
    }
  }
  for (const framingId of ["9:16", "16:9"]) {
    // white to white (B -> C, E -> F): looks as it did, the lift along the screen's up over the arch (the projected world up)
    for (const [name, fm] of [["B4 -> C5", 71], ["E4 -> F4", 64]]) {
      const p = paint(fm, framingId);
      const s = shape(p.pts);
      const h = Math.hypot(s.middle[0] - s.mid[0], s.middle[1] - s.mid[1]);
      const was = [s.mid[0] + p.up[0] * h, s.mid[1] + p.up[1] * h];  // where the old lift put the arch's middle
      const moved = Math.hypot(s.middle[0] - was[0], s.middle[1] - was[1]);
      check(`${framingId}: ${name} (white to white) keeps its arch: the middle within 0.5 px of where the projected up put it`,
        p.pts.length > 10 && h >= 4 && moved < 0.5 && s.apexAlong > 0.3 && s.apexAlong < 0.7, `height ${h.toFixed(2)} px, moved ${moved.toFixed(3)} px`);
    }
  }
  // off the camera's centre, the far end of the wide view: still an arch, a few degrees off the projected up at most
  {
    const p = paint(83, "16:9", { focus: keyX(83) - 22 });
    const s = shape(p.pts), h = Math.hypot(s.middle[0] - s.mid[0], s.middle[1] - s.mid[1]);
    const dir = [(s.middle[0] - s.mid[0]) / h, (s.middle[1] - s.mid[1]) / h];
    const deg = Math.acos(Math.min(1, dir[0] * p.up[0] + dir[1] * p.up[1])) * 180 / Math.PI;
    report.push(`B5 -> C6 at the wide view's edge: the lift is ${deg.toFixed(2)} degrees off the projected up`);
    check("16:9, B5 -> C6 off centre: an arch, the lift within 6 degrees of the projected up", s.apexAlong > 0.3 && s.apexAlong < 0.7
      && deg < 6, `${deg.toFixed(2)} degrees`);
  }

  // BRIDGE DAMP: the touching bridge (the 7 pressed right against home) is no brighter than a normal lean at the same level:
  // the design record's near-anchor damp (an anchor already sounding within 2 semitones counts as rub)
  {
    const plain = paint(71, "9:16", { level: 0.8 }), bridge = paint(71, "9:16", { level: 0.8, touching: true });
    check("the touching bridge is damped: 0.85 of a normal lean's opacity at the same level", plain.alpha > 0 && bridge.alpha > 0
      && bridge.alpha <= plain.alpha && near(bridge.alpha, 0.85 * plain.alpha, 1e-12) && page.LEAN_LOOK.bridgeBright === 0.85,
      `${bridge.alpha} vs ${plain.alpha}`);
  }
}

// ================================================================================================== robustness ==
{
  const lean = createLean();
  const map = new Map([[midiOf("G2"), {}], [midiOf("B4"), null], [130, {}], [-3, {}], [60.5, {}]]);
  let ok = true;
  try {
    lean.update(null, 0.016, 0);
    lean.update({}, 0.016, 0.016);
    lean.update({ sounding: map, rootPc: "7", keyTonic: 0, keyConf: 2 }, NaN, 0.1);
    lean.update({ sounding: map, rootPc: 7, keyTonic: 12, keyConf: NaN }, -1, 0.2);
    lean.update({ sounding: [1, 2, 3], rootPc: 7, keyTonic: 0, keyConf: 2 }, 0.016, undefined);
  } catch (e) { ok = false; console.log(e); }
  const f = lean.frame;
  check("nonsense input never throws and never poisons the frame", ok && Number.isFinite(f.level) && f.level >= 0 && f.level <= 1
    && Number.isFinite(f.land.level));
  // a t that goes backwards starts again from rest
  const run = play([{ t: 0, on: "G2 B3 D4 G4 B4", root: 7 }], 1.5);
  run.lean.update(run.input, 1 / 60, 0.2);
  check("a seek backwards starts again from rest", run.lean.frame.level === 0 && !run.lean.frame.active);
  run.lean.reset();
  check("reset() goes back to rest", run.lean.frame.level === 0 && run.lean.frame.fromMidi === -1 && run.lean.frame.land.midi === -1);
  const g = createLean();
  const input = { sounding: new Map([[43, { held: true }], [59, { held: true }], [62, { held: true }]]), rootPc: 7, keyTonic: 0, keyMinor: false, keyConf: 2 };
  for (let i = 0; i <= 60; i++) g.update(input, i ? 1 / 60 : 0, i / 60);
  const before = g.frame.level;
  const after = g.update(input, undefined, 1.2).level;
  check("a missing dt is taken from t", near(after, 1 - (1 - before) * Math.exp(-0.2 / LEAN.ATTACK), 1e-12) && g.frame.active,
    `${before} ${after}`);
}

for (const line of report) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
