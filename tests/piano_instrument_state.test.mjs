// Node test for the instrument host's state contract — arsenal/web/piano.js, the `looks.state` an instrument's
// update(dt, t, state) is handed. Zero dependencies, synthetic MIDI only:
//   node tests/piano_instrument_state.test.mjs
//
// What it pins (the header beside looks.state says the same in prose):
//   state.sounding mirrors the page's OWN sound model: an entry exists exactly while the notes engine holds that note
//   sounding — finger down, or released with CC64 down — and leaves the map on the sound's end (release with no pedal,
//   pedal lift, re-strike, all-notes-off). held is the finger, pedal is !held, tRelease is when the finger lifted (null
//   while held), strike counts that key's strikes (two strikes in one frame share a t0, not a strike number), entry
//   objects are pooled per key so their identity is stable, and the keys outside the 88 never enter the map.
//   state.pressed / pedal / chord / notes keep the shape every shipped instrument and scheme already reads.
//
// The page's own functions are sliced out of piano.js (the house pattern, tests/piano_keysig.test.mjs:213) and run against
// stubs, so this is the page's code, not a copy of it.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const pianoSrc = readFileSync(here("../arsenal/web/piano.js"), "utf8");
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}

// A top-level declaration's source, by name (braces matched outside strings, template literals and comments).
function declSource(name) {
  const m = new RegExp(`^(?:function\\s+${name}\\s*\\(|(?:const|let)\\s+${name}\\s*=)`, "m").exec(pianoSrc);
  if (!m) return null;
  const s = pianoSrc, isFn = m[0].startsWith("function");
  let depth = 0, body = false;
  for (let i = m.index; i < s.length; i++) {
    const ch = s[i];
    if (ch === "/" && s[i + 1] === "/") { i = s.indexOf("\n", i); continue; }
    if (ch === "/" && s[i + 1] === "*") { i = s.indexOf("*/", i + 2) + 1; continue; }
    if (ch === "'" || ch === '"' || ch === "`") { for (i++; i < s.length && s[i] !== ch; i++) if (s[i] === "\\") i++; continue; }
    if (ch === "{" || ch === "(" || ch === "[") { depth++; if (ch === "{") body = true; }
    else if (ch === "}" || ch === ")" || ch === "]") { depth--; if (isFn && body && depth === 0 && ch === "}") return s.slice(m.index, i + 1); }
    else if (ch === ";" && depth === 0 && !isFn) return s.slice(m.index, i + 1);
  }
  return null;
}

const DECLS = ["KEY", "looks", "sounding", "strikeCount", "sustain", "lookEvent", "lookNoteOn", "lookNoteOff", "lookNoteEnd",
  "refreshSounding", "noteOn", "noteOff", "setSustain", "allNotesOff"];
const decls = DECLS.map((n) => [n, declSource(n)]);
check("piano.js declares the notes engine and the looks host this test drives", decls.every(([, x]) => x),
  decls.filter(([, x]) => !x).map(([n]) => n).join(", "));
if (!decls.every(([, x]) => x)) { console.log(`${pass} passed, ${fail} failed`); process.exit(1); }

// ---------------------------------------------------------------- the page, with the rest of it stubbed --
const STUBS = ["clock", "spectacle", "beforeChange", "afterChange", "trails", "logged", "pageSec", "keys", "glowLevel",
  "noteColor", "burst", "lightNote", "hintCamera", "jamRest", "jamHeard", "hideIdleHint", "demo", "Theory", "stats",
  "detectDirty", "pcHistory", "pcHistoryAt", "lookFailed"];
function makePage() {
  let now = 0;
  const events = [];   // what the scheme host was told, in order
  const keyMap = new Map();
  for (let m = 21; m <= 108; m++) keyMap.set(m, { target: 0, glowTarget: 0, color: {} });
  const stubs = {
    clock: () => now,
    spectacle: null,
    beforeChange: () => {}, afterChange: () => {},
    trails: { start: (m, vel, t) => ({ m, vel, t, ended: false }), release: (tr) => { if (tr) tr.released = true; }, end: (tr) => { if (tr) tr.ended = true; } },
    logged: () => {},
    pageSec: (t) => t,
    keys: keyMap,
    glowLevel: () => 1,
    noteColor: () => {},
    burst: () => {}, lightNote: () => {}, hintCamera: () => {},
    jamRest: { noteOff: () => {}, sustain: () => {} },
    jamHeard: () => {},
    hideIdleHint: () => {},
    demo: { running: false },
    Theory: { mod: (a, n) => ((a % n) + n) % n },
    stats: { noteOns: 0 },
    detectDirty: false,
    pcHistory: new Array(12).fill(0),
    pcHistoryAt: 0,
    lookFailed: (kind, entry, method, e) => { throw e; },
  };
  const body = decls.map(([, x]) => x).join("\n");
  const page = new Function(...STUBS,
    `${body}\nreturn { KEY, looks, sounding, strikeCount, noteOn, noteOff, setSustain, allNotesOff, refreshSounding,`
    + ` get sustain() { return sustain; } };`)(...STUBS.map((k) => stubs[k]));
  page.at = (t) => { now = t; };
  page.events = events;
  page.keys = keyMap;
  // what an instrument is handed: the host refreshes state.sounding in place, once a frame (updateLooks)
  page.frame = () => { page.refreshSounding(page.looks.state.sounding); return page.looks.state; };
  return page;
}

// The host really does refresh it where the instrument's update() is called, and only the instrument branch does
check("updateLooks refreshes state.sounding beside state.pedal, in the instrument branch", /S\.pedal = sustain;\s*\n\s*S\.chord = lookChord\(info\);\s*\n\s*refreshSounding\(S\.sounding\);/.test(pianoSrc));
check("noteOn stamps the strike counter into the sounding entry (not diffed per frame)",
  /sounding\.set\(m, \{ held: true, vel, t0: t, tRelease: 0, strike: \+\+strikeCount\[m\]/.test(pianoSrc));
check("looks.state still carries pressed, pedal, chord and notes (every shipped instrument reads them)",
  /state: \{ pressed: new Map\(\), pedal: false, chord: null, notes: \[\], sounding: new Map\(\) \}/.test(pianoSrc));
check("the instrument-host header documents state.sounding and its pitfall",
  /state\.sounding.*is the page's answer|sounding  Map midi/s.test(pianoSrc)
  && /struck and released between two frames never appears here/.test(pianoSrc));

// ---------------------------------------------------------------- 1. a plain note: on, held, released, gone --
{
  const p = makePage();
  p.at(1.0); p.noteOn(60, 80);
  let S = p.frame();
  const e = S.sounding.get(60);
  check("note on: one entry, exact fields", !!e && S.sounding.size === 1 && e.vel === 80 && e.t0 === 1.0 && e.held === true
    && e.pedal === false && e.tRelease === null && e.strike === 1, JSON.stringify(e));
  check("note on: state.pressed still holds the live sounding entry (unchanged contract)", S.pressed.get(60)?.vel === 80);
  p.at(1.5);
  const again = p.frame().sounding.get(60);
  check("held across frames: the same entry object, refreshed in place", again === e && e.held === true && e.strike === 1);
  p.at(2.0); p.noteOff(60);
  S = p.frame();
  check("release with the pedal up: the sound ends, the entry is gone", S.sounding.size === 0 && !S.sounding.has(60));
  check("release with the pedal up: state.pressed is empty too", S.pressed.size === 0);
}

// ---------------------------------------------------------------- 2. released under the pedal: the hole pressed leaves --
{
  const p = makePage();
  p.at(0.5); p.setSustain(true);
  p.at(1.0); p.noteOn(45, 100);
  p.at(1.4); p.noteOff(45);
  const S = p.frame();
  const e = S.sounding.get(45);
  check("released under the pedal: the note still sounds, held false, pedal true, tRelease stamped",
    !!e && e.held === false && e.pedal === true && Math.abs(e.tRelease - 1.4) < 1e-9 && e.t0 === 1.0, JSON.stringify(e));
  check("released under the pedal: state.pressed has dropped it (that is the hole state.sounding fills)", !S.pressed.has(45));
  p.at(4.0);
  check("a pedal-held sound has no time limit: still there seconds later", p.frame().sounding.has(45));
  p.at(4.2); p.setSustain(false);
  check("pedal lift: the sound ends and the entry leaves", p.frame().sounding.size === 0);
}

// ---------------------------------------------------------------- 3. the pedal pressed later does not revive a sound --
{
  const p = makePage();
  p.at(1.0); p.noteOn(50, 90);
  p.at(1.2); p.noteOff(50);                 // the pedal was up: this sound is over
  check("release before the pedal: gone", p.frame().sounding.size === 0);
  p.at(1.3); p.setSustain(true);
  check("a later pedal press revives nothing (no resurrection)", p.frame().sounding.size === 0);
  p.at(1.4); p.noteOn(50, 40);
  const e = p.frame().sounding.get(50);
  check("the new strike of that key counts 2, not 1", e.strike === 2 && e.vel === 40 && e.t0 === 1.4, JSON.stringify(e));
  p.at(1.5); p.noteOff(50);
  check("finger up under the pedal: still sounding, held false", p.frame().sounding.get(50).held === false);
  p.at(1.6); p.setSustain(false);
  check("pedal lift ends it", p.frame().sounding.size === 0);
}

// ---------------------------------------------------------------- 4. re-strikes, including two inside one frame --
{
  const p = makePage();
  p.at(1.0); p.noteOn(64, 70);
  const first = p.frame().sounding.get(64);
  p.at(1.6); p.noteOn(64, 120);             // a re-strike while it still sounds
  const second = p.frame().sounding.get(64);
  check("re-strike while sounding: one entry, the new velocity and t0, strike 2", p.frame().sounding.size === 1
    && second.vel === 120 && second.t0 === 1.6 && second.strike === 2, JSON.stringify(second));
  check("re-strike: the entry object an instrument holds is the same one (pooled per key)", second === first);
  // two strikes inside one frame: the clock never moves, so t0 cannot tell them apart — the counter must
  p.at(2.0); p.noteOn(64, 60); p.noteOn(64, 61);
  const third = p.frame().sounding.get(64);
  check("two strikes inside one frame: t0 is identical, strike counts both", third.t0 === 2.0 && third.vel === 61
    && third.strike === 4, JSON.stringify(third));
  let bad = 0;
  for (let i = 0; i < 300; i++) { p.at(3 + i * 0.01); p.noteOn(64, 1 + (i % 120)); if (p.frame().sounding.get(64).strike !== 5 + i) bad++; }
  check("a 300-note repeat: the counter never repeats or skips", bad === 0, String(bad));
}

// ---------------------------------------------------------------- 5. the keys outside the 88, and all-notes-off --
{
  const p = makePage();
  p.at(1.0); p.noteOn(12, 90); p.noteOn(120, 90); p.noteOn(21, 90); p.noteOn(108, 90);
  const S = p.frame();
  check("out-of-range keys sound for the page but never enter the mirror", p.sounding.size === 4 && S.sounding.size === 2
    && S.sounding.has(21) && S.sounding.has(108) && !S.sounding.has(12) && !S.sounding.has(120),
    `${p.sounding.size} sounding, ${S.sounding.size} mirrored`);
  check("the ends of the 88 are in (21 and 108)", S.sounding.get(21).vel === 90 && S.sounding.get(108).vel === 90);
  p.at(1.5); p.allNotesOff();
  check("all-notes-off empties the mirror", p.frame().sounding.size === 0 && p.sounding.size === 0);
  check("all-notes-off lifts the pedal too", p.sustain === false);
}

// ---------------------------------------------------------------- 6. a chord under the pedal, and removal is exact --
{
  const p = makePage();
  p.at(0.0); p.setSustain(true);
  const chord = [36, 48, 55, 60, 64, 67, 72];
  chord.forEach((m, i) => { p.at(1.0 + i * 0.01); p.noteOn(m, 60 + i * 8); });
  chord.forEach((m, i) => { p.at(1.3 + i * 0.01); p.noteOff(m); });
  let S = p.frame();
  check("seven notes released under the pedal all still sound", S.sounding.size === 7
    && chord.every((m) => S.sounding.get(m).pedal === true && S.sounding.get(m).held === false));
  p.at(2.0); p.noteOn(60, 110);             // one of them re-struck: still seven, that one held again
  S = p.frame();
  check("re-striking one of them keeps seven, and that one is held again", S.sounding.size === 7
    && S.sounding.get(60).held === true && S.sounding.get(60).pedal === false && S.sounding.get(60).tRelease === null);
  p.at(2.2); p.setSustain(false);
  S = p.frame();
  check("the pedal lift ends the six the pedal held and keeps the one the finger holds", S.sounding.size === 1 && S.sounding.has(60));
  p.at(2.4); p.noteOff(60);
  check("the last finger up ends it", p.frame().sounding.size === 0);
  check("the pool is not the map: it keeps its objects, the map is empty", p.looks.sounds.size >= 7);
}

// ---------------------------------------------------------------- 7. the mirror never lags the page by a frame --
{
  const p = makePage();
  const live = () => { const m = new Map(); for (const [k, v] of p.sounding) if (k >= 21 && k <= 108) m.set(k, v); return m; };
  const same = () => {
    const a = live(), b = p.frame().sounding;
    if (a.size !== b.size) return false;
    for (const [m, st] of a) {
      const e = b.get(m);
      if (!e || e.vel !== st.vel || e.t0 !== st.t0 || e.held !== st.held || e.pedal !== !st.held) return false;
      if (e.tRelease !== (st.held ? null : st.tRelease)) return false;
    }
    return true;
  };
  let bad = 0, seed = 7;
  const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  for (let i = 0; i < 4000; i++) {
    p.at(i * 0.013);
    const r = rnd();
    const m = 21 + Math.floor(rnd() * 88);
    if (r < 0.45) p.noteOn(m, 1 + Math.floor(rnd() * 127));
    else if (r < 0.8) p.noteOff(m);
    else if (r < 0.95) p.setSustain(rnd() < 0.5);
    else p.allNotesOff();
    if (!same()) bad++;
  }
  report.push(`random walk: 4000 events, ${p.sounding.size} sounding at the end, ${p.looks.state.sounding.size} mirrored`);
  check("4000 random note/pedal/panic events: the mirror equals the page's own sounding map every time", bad === 0, String(bad));
}

for (const line of report) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
