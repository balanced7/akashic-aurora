// Node test for the practice log's note timing — arsenal/web/piano.js, the onMidiMessage -> noteOn/noteOff/setSustain
// path. Zero dependencies, synthetic MIDI only:
//   node tests/piano_receipt_time.test.mjs
//
// What it pins (measured 2026-10-11 against an OBS recording of a live session; see the commit message):
//   A Web MIDI message is time-stamped (ev.timeStamp) when it ARRIVES, on performance.now()'s timeline. But
//   onMidiMessage used to call noteOn(m, vel), which stamps the log with clock() = now, when THIS handler runs.
//   Under a heavy frame the main thread runs the handler tens to >100 ms late, so the logged note time drifted
//   that far behind the key (an isolated note measured ~96 ms late). The fix: onMidiMessage computes the receipt
//   lag (eventLagMs) and passes it so the log records when the key was struck, while the visuals still animate
//   from now (clock()), so nothing on screen changes. Direct callers (computer keys, Demo, replay) pass no lag
//   and are unchanged.
//
// The page's own functions are sliced out of piano.js (the house pattern, tests/piano_instrument_state.test.mjs)
// and run against stubs, so this is the page's code, not a copy of it. `logged` is captured and `clock` /
// `performance.now` are driven, so the exact stamped time is observable.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createBoundaryGate } from "../arsenal/web/piano/boundary.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const pianoSrc = readFileSync(here("../arsenal/web/piano.js"), "utf8");
let pass = 0, fail = 0;
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

const DECLS = ["KEY", "looks", "sounding", "strikeCount", "sustain", "lookEvent", "lookNoteOn", "lookNoteOff",
  "lookNoteEnd", "refreshSounding", "hasRinging", "noteOn", "noteOff", "setSustain", "allNotesOff",
  "eventLagMs", "onMidiMessage"];
const decls = DECLS.map((n) => [n, declSource(n)]);
check("piano.js declares the MIDI handler and note engine this test slices", decls.every(([, x]) => x),
  decls.filter(([, x]) => !x).map(([n]) => n).join(", "));
if (!decls.every(([, x]) => x)) { console.log(`${pass} passed, ${fail} failed`); process.exit(1); }

// ---------------------------------------------------------------- source pins (the fix is wired, not reverted) --
check("onMidiMessage derives the receipt lag and passes it to the note handlers",
  /const lag = eventLagMs\(ev\.timeStamp\);/.test(pianoSrc)
  && /noteOn\(d\[1\], d\[2\], lag\)/.test(pianoSrc)
  && /noteOff\(d\[1\], lag\)/.test(pianoSrc)
  && /setSustain\(d\[2\] >= 64, d\[2\], lag\)/.test(pianoSrc));
check("the note handlers stamp the log at the receipt time (t - recvLagMs), the visuals at t",
  /const tLog = recvLagMs > 0 \? t - recvLagMs \/ 1000 : t;/.test(pianoSrc)
  && /log\.noteOn\(m, vel, pageSec\(tLog\)\)/.test(pianoSrc)
  && /spectacle\?\.noteOn\(m, vel, t\)/.test(pianoSrc));

// ---------------------------------------------------------------- the page, with the rest of it stubbed --
const STUBS = ["clock", "performance", "spectacle", "beforeChange", "afterChange", "trails", "logged", "pageSec",
  "keys", "glowLevel", "noteColor", "burst", "lightNote", "hintCamera", "jamRest", "jamHeard", "hideIdleHint",
  "demo", "Theory", "stats", "detectDirty", "pcHistory", "pcHistoryAt", "lookFailed", "midiHint", "theoryUi",
  "boundaryGate", "midi", "cueMidiOutName", "hushClaude"];
function makePage() {
  let now = 0, perfNowMs = 0;
  const captured = [];
  const fakeLog = {
    noteOn: (m, vel, t) => captured.push({ kind: "on", m, vel, t }),
    noteOff: (m, t) => captured.push({ kind: "off", m, t }),
    soundEnd: (m, by, t) => captured.push({ kind: "sound_end", m, by, t }),
    pedal: (on, value, t) => captured.push({ kind: "pedal", on, value, t }),
    chord: () => {}, metro: () => {},
  };
  const keyMap = new Map();
  for (let m = 21; m <= 108; m++) keyMap.set(m, { target: 0, glowTarget: 0, color: {} });
  const stubs = {
    clock: () => now,
    performance: { now: () => perfNowMs },
    spectacle: null,
    beforeChange: () => {}, afterChange: () => {},
    trails: { start: (m, vel, t) => ({ m, vel, t }), release: () => {}, end: () => {} },
    logged: (fn) => fn(fakeLog),
    pageSec: (t) => t,
    keys: keyMap,
    glowLevel: () => 1,
    noteColor: () => {}, burst: () => {}, lightNote: () => {}, hintCamera: () => {},
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
    midiHint: null,
    theoryUi: { boundary: "notes" },
    boundaryGate: createBoundaryGate(),
    midi: { echoes: 0, events: 0, last: null },
    cueMidiOutName: null,
    hushClaude: () => {},
  };
  const body = decls.map(([, x]) => x).join("\n");
  const page = new Function(...STUBS,
    `${body}\nreturn { noteOn, noteOff, setSustain, allNotesOff, onMidiMessage, eventLagMs, sounding,`
    + ` get sustain() { return sustain; } };`)(...STUBS.map((k) => stubs[k]));
  // drive the two clocks: `now` is clock() seconds; `perfMs` is performance.now() ms (defaults to now*1000)
  page.set = (nowSec, perfMs) => { now = nowSec; perfNowMs = perfMs === undefined ? nowSec * 1000 : perfMs; };
  page.captured = captured;
  return page;
}

// ---------------------------------------------------------------- 1. eventLagMs: the receipt-lag contract --
{
  const p = makePage();
  p.set(0, 1000);  // performance.now() == 1000 ms
  check("eventLagMs: a recent arrival gives the positive lag in ms", p.eventLagMs(900) === 100, String(p.eventLagMs(900)));
  check("eventLagMs: an arrival 'in the future' (negative lag) -> 0", p.eventLagMs(1100) === 0);
  check("eventLagMs: a lag past the 1 s cap -> 0", p.eventLagMs(-600) === 0);           // 1000 - (-600) = 1600 ms
  check("eventLagMs: a foreign-epoch stamp (Unix ms) -> 0", p.eventLagMs(1.7e12) === 0);
  check("eventLagMs: a missing stamp -> 0", p.eventLagMs(undefined) === 0);
}

// ---------------------------------------------------------------- 2. a delayed note-on logs the receipt time --
{
  const p = makePage();
  p.set(1.120, 1120);  // the handler runs at clock 1.120 s / perf 1120 ms ...
  p.onMidiMessage({ data: Uint8Array.from([0x90, 69, 80]), timeStamp: 1000 });  // ... but A4 arrived 120 ms earlier
  const on = p.captured.find((e) => e.kind === "on" && e.m === 69);
  check("a delayed MIDI note-on logs the receipt time (ev.timeStamp), not the handler time",
    !!on && Math.abs(on.t - 1.000) < 1e-9, on ? `t=${on.t} expected 1.000` : "no on event");
  check("the on-screen key (sounding entry t0) keeps the handler clock -- the visuals are unchanged",
    p.sounding.get(69)?.t0 === 1.120, `t0=${p.sounding.get(69)?.t0}`);
}

// ---------------------------------------------------------------- 3. a synthetic event (lag 0) is unchanged --
{
  const p = makePage();
  p.set(2.000, 2000);
  p.onMidiMessage({ data: Uint8Array.from([0x90, 72, 64]), timeStamp: 2000 });  // timeStamp == performance.now()
  const on = p.captured.find((e) => e.kind === "on" && e.m === 72);
  check("a synthetic note-on (timeStamp == performance.now()) logs the handler time (lag 0)",
    !!on && Math.abs(on.t - 2.000) < 1e-9, on ? `t=${on.t}` : "no on event");
}

// ---------------------------------------------------------------- 4. a foreign-epoch stamp falls back to now --
{
  const p = makePage();
  p.set(3.000, 3000);
  p.onMidiMessage({ data: Uint8Array.from([0x90, 64, 70]), timeStamp: 1.7e12 });  // e.g. a Unix-ms timeStamp
  const on = p.captured.find((e) => e.kind === "on" && e.m === 64);
  check("a foreign-epoch timeStamp falls back to the handler clock (no absurd backdate)",
    !!on && Math.abs(on.t - 3.000) < 1e-9, on ? `t=${on.t}` : "no on event");
}

// ---------------------------------------------------------------- 5. direct callers (no lag arg) are unchanged --
{
  const p = makePage();
  p.set(4.000, 4000);
  p.noteOn(60, 90);  // the computer keyboard / Demo / replay path: already on the page clock
  const on = p.captured.find((e) => e.kind === "on" && e.m === 60);
  check("noteOn with no lag argument logs the handler clock (computer keys / Demo / replay)",
    !!on && Math.abs(on.t - 4.000) < 1e-9, on ? `t=${on.t}` : "no on event");
}

// ---------------------------------------------------------------- 6. note-off (and its sound_end) too --
{
  const p = makePage();
  p.set(5.000, 5000);
  p.onMidiMessage({ data: Uint8Array.from([0x90, 50, 72]), timeStamp: 5000 });  // on, lag 0
  p.set(5.200, 5200);
  p.onMidiMessage({ data: Uint8Array.from([0x80, 50, 0]), timeStamp: 5100 });   // off, lag 100 -> receipt 5.100
  const off = p.captured.find((e) => e.kind === "off" && e.m === 50);
  const end = p.captured.find((e) => e.kind === "sound_end" && e.m === 50);
  check("a delayed MIDI note-off logs the receipt time", !!off && Math.abs(off.t - 5.100) < 1e-9, off ? `t=${off.t}` : "no off");
  check("the release sound_end rides the same receipt time",
    !!end && end.by === "release" && Math.abs(end.t - 5.100) < 1e-9, end ? `${end.by} t=${end.t}` : "no sound_end");
}

// ---------------------------------------------------------------- 7. the sustain pedal (CC64) too --
{
  const p = makePage();
  p.set(6.080, 6080);
  p.onMidiMessage({ data: Uint8Array.from([0xB0, 64, 127]), timeStamp: 6000 });  // pedal down, lag 80 -> 6.000
  const ped = p.captured.find((e) => e.kind === "pedal");
  check("a delayed sustain-pedal (CC64) crossing logs the receipt time",
    !!ped && ped.on === true && Math.abs(ped.t - 6.000) < 1e-9, ped ? `on=${ped.on} t=${ped.t}` : "no pedal");
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
