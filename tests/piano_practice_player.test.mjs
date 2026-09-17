// Node tests for the Studio practice player (arsenal/web/piano/practice/player.js). Zero dependencies:
//   node tests/piano_practice_player.test.mjs
// The real cue player (arsenal/web/piano/cues.js createCuePlayer) on a manual clock, with a voice that only records what it
// is handed and the real practice library. Sections: play, pause (nothing sounds while paused) and resume from the paused
// chord; next and prev; loops; auto-advance across a group and a family, and the end of the library; external clears (hush,
// an SSE clear, pagehide, a clear inside the voice's lookahead); transpose (numbers constant, names respelled, register
// folding) and a key or tempo change while playing; chips and ghost keys; a stalled page; the voice unlock inside a click.
// Every chord heard is checked against its expected time (within 5 ms; on this clock it is exact).
import { createCuePlayer, CANCEL_FADE_MS } from "../arsenal/web/piano/cues.js";
import { formatNumber, nashvilleFromName } from "../arsenal/web/piano/nashville.js";
import { FAMILIES, EXERCISES } from "../arsenal/web/piano/practice/library.js";
import {
  createExercisePlayer, viewOf, transposeKey, foldExercise, libraryOrder, createNavigator,
  LEAD_MS, HAND_AHEAD_MS, POLL_MS, LEGATO_MS, RANGE, ID_PREFIX,
} from "../arsenal/web/piano/practice/player.js";

let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + (typeof detail === "string" ? detail : JSON.stringify(detail)) : ""}`);
}
const TOL_MS = 5;
const EPS = 1e-6;
const byId = new Map(EXERCISES.map((e) => [e.id, e]));
const ex = (id) => byId.get(id);

// ------------------------------------------------------------------------------------------- the manual clock --
// setTimeout / clearTimeout / now on one time line. The cue player's plain timer calls the global setTimeout when it arms
// (cues.js createTimer), so install() swaps the globals for the length of the test.
function createManualClock(start = 10000) {
  let t = start, seq = 0;
  const timers = new Map(), saved = {};
  const clock = {
    now: () => t,
    setTimeout(fn, delay = 0, ...args) { const id = ++seq; timers.set(id, { id, due: t + Math.max(0, Number(delay) || 0), fn: () => fn(...args) }); return id; },
    clearTimeout(id) { timers.delete(id); },
    // run every timer due up to target, in time order (ties: the order set), the clock at each one's due time
    advanceTo(target) {
      for (let guard = 0; guard < 1e6; guard++) {
        let next = null;
        for (const x of timers.values()) if (x.due <= target && (!next || x.due < next.due || (x.due === next.due && x.id < next.id))) next = x;
        if (!next) break;
        timers.delete(next.id);
        if (next.due > t) t = next.due;
        next.fn();
      }
      if (target > t) t = target;
    },
    advance(ms) { clock.advanceTo(t + ms); },
    stall(ms) { t += ms; },  // a frozen main thread: time moves, nothing runs
    install() { saved.set = globalThis.setTimeout; saved.clear = globalThis.clearTimeout; globalThis.setTimeout = clock.setTimeout; globalThis.clearTimeout = clock.clearTimeout; return clock; },
    uninstall() { globalThis.setTimeout = saved.set; globalThis.clearTimeout = saved.clear; },
  };
  return clock;
}

// A voice that records. The synth's rule: a release at or before a strike's own time means it never sounds.
function createRecordingVoice(now, { status = "ready", unlockDelay = null } = {}) {
  let h = 0;
  const strikes = [], byHandle = new Map();
  const voice = {
    strikes, unlocks: 0, statusNow: status,
    noteOn(midi, velocity, when = {}) {
      const s = { handle: ++h, midi, velocity, at: when.at, handedAt: now(), cue_id: when.cue_id ?? null, releasedAt: null, fadeMs: null, synthOnly: !!when.synthOnly };
      strikes.push(s);
      byHandle.set(s.handle, s);
      return s.handle;
    },
    release(handle, when = {}) {
      const s = byHandle.get(handle);
      if (!s) return false;
      const at = when.at ?? now();
      if (s.releasedAt === null || at < s.releasedAt) { s.releasedAt = at; s.fadeMs = when.fadeMs ?? null; }
      return true;
    },
    extend(handle, when = {}) { const s = byHandle.get(handle); if (!s) return false; s.releasedAt = when.at; return true; },
    unlock() { voice.unlocks++; return unlockDelay ? unlockDelay() : Promise.resolve(voice.statusNow); },
    status: () => voice.statusNow,
    heard: () => strikes.filter((s) => !s.synthOnly && (s.releasedAt === null || s.releasedAt > s.at)),
  };
  return voice;
}

function makeEnv({ lifecycle = null, voiceOpts = {}, adapter = false, playerOpts = {} } = {}) {
  const clock = createManualClock().install();
  const voice = createRecordingVoice(clock.now, voiceOpts);
  const captions = [], errors = [], states = [], lit = [];
  const cuePlayer = createCuePlayer({
    voice, now: clock.now, timer: "timeout", lifecycleTarget: lifecycle,
    noteOn: (m, vel, meta) => lit.push({ t: clock.now(), m, cue: meta.cue_id, source: meta.source }),
    caption: (info) => captions.push({ t: clock.now(), label: info ? info.label : null, detail: info ? info.detail : null, cue: info ? info.cue_id : null }),
    onError: (e) => errors.push(String((e && e.message) || e)),
  });
  // adapter: the shape window.__piano.cues takes (play with at passed through, cancel, extend, clears)
  const cues = adapter
    ? { play: (cue, o) => cuePlayer.handle(cue, { id: o.id, at: o.at, grace: o.grace }), cancel: (id, o) => cuePlayer.cancel(id, o),
        extend: (id, s, at) => cuePlayer.extend(id, s, at), clears: () => cuePlayer.state().clears }
    : cuePlayer;
  const timer = { set: (fn, ms) => clock.setTimeout(fn, ms), clear: (id) => clock.clearTimeout(id) };
  const player = createExercisePlayer({ cues, voice, now: clock.now, timer, onState: (s) => states.push({ t: clock.now(), ...s }), ...playerOpts });
  return { clock, voice, cuePlayer, player, captions, errors, states, lit,
           done() { player.dispose(); cuePlayer.dispose(); clock.uninstall(); } };
}

// Heard strikes grouped into chords by their time.
function chordsHeard(voice, from = -Infinity, to = Infinity) {
  const groups = new Map();
  for (const s of voice.heard()) {
    if (s.at < from - EPS || s.at > to + EPS) continue;
    const k = s.at.toFixed(3);
    if (!groups.has(k)) groups.set(k, { at: s.at, midis: [], cues: new Set() });
    groups.get(k).midis.push(s.midi);
    groups.get(k).cues.add(s.cue_id);
  }
  return [...groups.values()].sort((a, b) => a.at - b.at).map((g) => ({ at: g.at, midis: g.midis.sort((a, b) => a - b), cues: [...g.cues] }));
}
const notesOf = (view, i) => [...view.chords[i].bass, ...view.chords[i].upper].sort((a, b) => a - b);
// heard vs expected [{at, midis}]: the largest timing error, and missing / extra / wrong / doubled chords
function compare(heard, expected) {
  const errs = [], used = new Set();
  let missing = 0, wrong = 0;
  for (const e of expected) {
    const j = heard.findIndex((h, k) => !used.has(k) && Math.abs(h.at - e.at) <= 50);
    if (j < 0) { missing++; continue; }
    used.add(j);
    errs.push(Math.abs(heard[j].at - e.at));
    if (heard[j].midis.join() !== e.midis.join()) wrong++;
  }
  const extra = heard.length - used.size;
  const doubled = heard.filter((h) => new Set(h.midis).size !== h.midis.length).length;
  return { maxErrMs: errs.length ? Math.max(...errs) : null, missing, extra, wrong, doubled,
           ok: missing === 0 && extra === 0 && wrong === 0 && doubled === 0 && (errs.length === 0 || Math.max(...errs) <= TOL_MS) };
}
const cmpText = (c, heard, t0) => `${JSON.stringify({ maxErrMs: c.maxErrMs, missing: c.missing, extra: c.extra, wrong: c.wrong, doubled: c.doubled })} heard at ${heard.map((h) => Math.round(h.at - t0)).join(",")}`;
const strikesSoundingIn = (voice, from, to) => voice.strikes.filter((s) => s.at > from + EPS && s.at <= to + EPS);
const handedIn = (voice, from, to) => voice.strikes.filter((s) => s.handedAt > from + EPS && s.handedAt <= to + EPS);

// ============================================================================ 1. play, pause, resume, next, prev ==
{
  const E = makeEnv();
  const { clock, player, voice, cuePlayer } = E;
  const A = ex("stepwise-bass-g");
  const T0 = clock.now();
  const v = player.load(A);
  check("load: idle, the exercise's own key and tempo", player.status === "idle" && v.key === "G major" && v.bpm === 72 && v.chords.length === 8, player.state());
  const unlocksBefore = voice.unlocks;
  const playing = player.play();
  check("play calls voice.unlock() at once, inside the click (before any await)", voice.unlocks === unlocksBefore + 1);
  await playing;
  check("play: playing", player.status === "playing", player.state());
  const dur = v.chords[0].durMs;
  const on = (k) => T0 + LEAD_MS + k * dur;
  clock.advanceTo(on(1) + 1200);  // 1.2 s into chord 2
  check("the state follows the chord sounding (chord 2: D/F#, 5/7)", player.state().index === 1 && player.state().chord === "D/F#" && player.state().number === "5/7", player.state());
  const tPause = clock.now();
  check("pause: paused on chord 2", player.pause() === true && player.status === "paused" && player.state().index === 1, player.state());
  const faded = voice.strikes.filter((s) => Math.abs(s.at - on(1)) < EPS);
  check("pause fades the sounding chord at once over the cancel fade", faded.length === 4 && faded.every((s) => s.releasedAt === tPause && s.fadeMs === CANCEL_FADE_MS),
    faded.map((s) => [s.releasedAt - tPause, s.fadeMs]));
  clock.advanceTo(tPause + 6000);
  const tResume = clock.now();
  check("zero strikes handed or sounding while paused (6 s)", strikesSoundingIn(voice, tPause, tResume).length === 0 && handedIn(voice, tPause, tResume).length === 0,
    { sounding: strikesSoundingIn(voice, tPause, tResume).length, handed: handedIn(voice, tPause, tResume).length });
  check("the cue player is empty while paused", cuePlayer.state().pending === 0 && cuePlayer.state().sounding.length === 0, cuePlayer.state());
  await player.resume();
  const rOn = (k) => tResume + LEAD_MS + k * dur;
  clock.advanceTo(rOn(2) + 500);  // inside chord 4 (resumed chords 2, 3, 4)
  check("resume: playing again, now on chord 4", player.status === "playing" && player.state().index === 3, player.state());
  const tNext = clock.now();
  const nexting = player.next();
  await nexting;
  const B = player.view;
  check("next while playing: the next exercise in the library (line-cliche-em, the next group) and still playing",
    B.id === "line-cliche-em" && player.status === "playing" && B.bpm === 66, { id: B.id, status: player.status, bpm: B.bpm });
  const bOn = (k) => tNext + LEAD_MS + k * B.chords[0].durMs;
  clock.advanceTo(bOn(1) + 300);
  const heard = chordsHeard(voice, T0, clock.now());
  const expected = [
    { at: on(0), midis: notesOf(v, 0) }, { at: on(1), midis: notesOf(v, 1) },
    { at: rOn(0), midis: notesOf(v, 1) }, { at: rOn(1), midis: notesOf(v, 2) }, { at: rOn(2), midis: notesOf(v, 3) },
    { at: bOn(0), midis: notesOf(B, 0) }, { at: bOn(1), midis: notesOf(B, 1) },
  ];
  const cmp = compare(heard, expected);
  check("every chord heard within 5 ms of its time (play, resume from the paused chord, next), nothing missing, extra or doubled", cmp.ok, cmpText(cmp, heard, T0));
  report.push(`play/pause/resume/next: ${heard.length} chords heard, largest timing error ${cmp.maxErrMs} ms`);
  const oldAfterNext = voice.heard().filter((s) => String(s.cue_id).startsWith(`${ID_PREFIX}stepwise-bass-g:`) && s.at > tNext);
  check("nothing of the first exercise sounds after next", oldAfterNext.length === 0, oldAfterNext.length);
  check("every strike reaches the voice at least the lead time before it sounds", voice.strikes.every((s) => s.at - s.handedAt >= LEAD_MS - EPS),
    Math.min(...voice.strikes.map((s) => s.at - s.handedAt)));
  const cap = E.captions.find((c) => c.label === "Em7/D");
  check("the chip names the chord and its number in the key, formatted, on an exercise: id", !!cap && cap.detail === `${formatNumber("6m7/5").display} in G major`
    && String(cap.cue).startsWith(ID_PREFIX), cap);
  const tPrev = clock.now();
  await player.prev();
  check("prev while playing: back to stepwise-bass-g, playing from its first chord", player.view.id === "stepwise-bass-g" && player.status === "playing" && player.state().index === 0,
    player.state());
  clock.advance(LEAD_MS + 10);
  const prevHeard = chordsHeard(voice, tPrev, clock.now());
  check("prev: its first chord 150 ms after the click", prevHeard.length === 1 && Math.abs(prevHeard[0].at - (tPrev + LEAD_MS)) <= TOL_MS && prevHeard[0].midis.join() === notesOf(player.view, 0).join(),
    prevHeard);
  player.stop();
  check("stop: stopped, nothing pending", player.status === "stopped" && player.state().reason === "stop" && cuePlayer.state().pending === 0, player.state());
  player.load(ex("stepwise-bass-g"));
  check("prev at the first exercise of the library does nothing", (await player.prev()) === false && player.view.id === "stepwise-bass-g");
  await player.next();
  check("next while idle loads the next exercise and stays idle", player.view.id === "line-cliche-em" && player.status === "idle");
  const ps = cuePlayer.state();
  check("no dropped notes and no player errors", ps.atLateDropped === 0 && ps.lateDropped === 0 && E.errors.length === 0, { ps: { atLateDropped: ps.atLateDropped }, errors: E.errors });
  check("the practice log path is never used: every cue is Claude's local cue (source claude, exercise: id)",
    E.lit.every((x) => x.source === "claude" && String(x.cue).startsWith(ID_PREFIX)));
  E.done();
}

// ============================================================================================ 2. loops ==
{
  const E = makeEnv();
  const { clock, player, voice, cuePlayer } = E;
  const A = ex("tonic-pedal-g");
  const T0 = clock.now();
  const v = player.load(A, { loops: 2 });
  await player.play();
  const onAt = [];
  for (let p = 0, t = T0 + LEAD_MS; p < 2; p++) v.chords.forEach((c) => { onAt.push(t); t += c.durMs; });
  const end = T0 + LEAD_MS + 2 * v.passMs;
  clock.advanceTo(end + 3000);
  const heard = chordsHeard(voice, T0, clock.now());
  const cmp = compare(heard, onAt.map((at, k) => ({ at, midis: notesOf(v, k % v.chords.length) })));
  check(`loops 2: ${2 * v.chords.length} chords on the grid, then stopped (ended)`, cmp.ok && player.status === "stopped" && player.state().reason === "ended",
    cmpText(cmp, heard, T0) + " " + JSON.stringify(player.state()));
  const stopped = E.states.find((s) => s.status === "stopped");
  check("loops 2: it stops at the end of the last chord", !!stopped && stopped.t >= end - EPS && stopped.t - end <= POLL_MS, stopped && stopped.t - end);
  // forever
  const T1 = clock.now();
  player.load(A, { loops: Infinity });
  await player.play();
  clock.advanceTo(T1 + LEAD_MS + 3 * v.passMs + 500);
  const forever = chordsHeard(voice, T1, clock.now());
  check("loops forever: still playing after 3 passes", player.status === "playing" && forever.length === 3 * v.chords.length + 1 && player.state().pass === 3,
    { heard: forever.length, state: player.state() });
  player.stop();
  const tStop = clock.now();
  clock.advance(20000);
  check("stop: nothing sounds after it, the cue player is empty", chordsHeard(voice, tStop + EPS, clock.now()).length === 0 && cuePlayer.state().pending === 0
    && cuePlayer.state().sounding.length === 0);
  // loops 4 by setLoops while playing, then lowered back to 1: ends after the pass that is sounding
  const T2 = clock.now();
  player.load(A, { loops: 1 });
  await player.play();
  player.setLoops(4);
  clock.advanceTo(T2 + LEAD_MS + v.passMs + 200);
  check("setLoops(4) while playing: a second pass starts", player.status === "playing" && player.state().pass === 1, player.state());
  player.setLoops(1);
  clock.advanceTo(T2 + LEAD_MS + 3 * v.passMs);
  check("setLoops(1) during the second pass: it ends after that chord and hands nothing more", player.status === "stopped" && player.state().reason === "ended", player.state());
  E.done();
}

// ============================================================ 3. auto-advance across a group and a family; the end ==
{
  const order = libraryOrder(FAMILIES);
  const nav = createNavigator({ FAMILIES, EXERCISES });
  check("the navigator walks the menu order and stops at both ends", nav(order[0], -1) === null && nav(order.at(-1), +1) === null
    && nav("stepwise-bass-g", +1).id === "line-cliche-em");
  const E = makeEnv();
  const { clock, player, voice } = E;
  const path = ["stepwise-bass-g", "line-cliche-em", "lament-bass-am", "lydian-bass-g"];
  check("the path crosses a group (inversions -> chromatic-lines) and a family (moving-bass -> bass-decides-home)",
    ex(path[0]).group !== ex(path[1]).group && ex(path[0]).family === ex(path[1]).family && ex(path[2]).family !== ex(path[3]).family
    && path.every((id, k) => k === 0 || nav(path[k - 1], +1).id === id));
  const T0 = clock.now();
  player.load(ex(path[0]), { loops: 1, autoAdvance: true, transpose: 0 });
  player.setBpm(90);  // a tempo of its own: the next exercises take theirs
  await player.play();
  const views = path.map((id, k) => viewOf(ex(id), { bpm: k === 0 ? 90 : null }));
  const expected = [];
  let t = T0 + LEAD_MS;
  views.forEach((vw, k) => {
    vw.chords.forEach((c, i) => { expected.push({ at: t, midis: notesOf(vw, i) }); t += c.durMs; });
    if (k < views.length - 1) t += vw.beatMs;  // one beat of air between exercises
  });
  const lydianEnd = t;
  clock.advanceTo(lydianEnd - 10);
  const seen = [...new Set(E.states.filter((s) => s.status === "playing").map((s) => s.exerciseId))];
  check("auto-advance plays stepwise-bass-g, then the next group's two exercises, then the next family's first", JSON.stringify(seen) === JSON.stringify(path), seen);
  const heard = chordsHeard(voice, T0, clock.now());
  const cmp = compare(heard, expected);
  check("auto-advance: every chord of the four exercises within 5 ms, each exercise at its own tempo, one beat between them", cmp.ok, cmpText(cmp, heard, T0));
  report.push(`auto-advance: ${heard.length} chords over ${path.length} exercises (${((lydianEnd - T0) / 1000).toFixed(1)} s), largest timing error ${cmp.maxErrMs} ms`);
  check("after advancing, the header shows the new exercise at its own tempo", player.state().exerciseId === "lydian-bass-g" && player.state().bpm === ex("lydian-bass-g").bpm,
    player.state());
  player.stop();
  // the end of the library
  const last = ex(order.at(-1));
  const T1 = clock.now();
  const lv = player.load(last, { loops: 1, autoAdvance: true });
  await player.play();
  clock.advanceTo(T1 + LEAD_MS + lv.passMs + 2000);
  check("auto-advance at the last exercise of the library stops at its end", player.status === "stopped" && player.state().reason === "ended"
    && chordsHeard(voice, T1, clock.now()).length === lv.chords.length, player.state());
  E.done();
}

// ======================================================================================= 4. external clears ==
async function clearScenario(label, doClear, { lifecycle = null, when = "mid" } = {}) {
  const E = makeEnv({ lifecycle });
  const { clock, player, voice, cuePlayer } = E;
  const T0 = clock.now();
  const v = player.load(ex("flip-e"), { loops: Infinity });
  await player.play();
  const on = (k) => T0 + LEAD_MS + v.chords.slice(0, k).reduce((s, c) => s + c.durMs, 0);
  const tClear = when === "mid" ? on(1) + 1000 : on(2) - 100;  // lookahead: chord 3 already with the voice
  clock.advanceTo(tClear);
  const withVoice = voice.strikes.filter((s) => s.at > tClear);
  doClear(E);
  const tC = clock.now();
  clock.advanceTo(tC + POLL_MS);
  const stopped = E.states.find((s) => s.t >= tC && s.status === "stopped");
  check(`${label}: noticed within ${POLL_MS} ms, stopped (cleared)`, !!stopped && stopped.reason === "cleared" && stopped.t - tC <= POLL_MS,
    stopped ? { after: stopped.t - tC, reason: stopped.reason } : player.state());
  clock.advance(15000);
  check(`${label}: nothing sounds after the clear`, voice.heard().filter((s) => s.at > tC + EPS).length === 0);
  if (when === "lookahead") check(`${label}: the chord already with the voice is released before it sounds`, withVoice.length > 0 && withVoice.every((s) => s.releasedAt !== null && s.releasedAt <= s.at));
  const ringing = voice.strikes.filter((s) => s.at <= tC && (s.releasedAt === null || s.releasedAt > tC + 1));
  check(`${label}: no ghosts (nothing ringing, nothing pending, nothing handed again)`, ringing.length === 0 && cuePlayer.state().sounding.length === 0
    && cuePlayer.state().pending === 0 && player.state().handed.length === 0, { ringing: ringing.length, pending: cuePlayer.state().pending });
  const tAgain = clock.now();
  await player.play();
  clock.advance(LEAD_MS + 10);
  const again = chordsHeard(voice, tAgain, clock.now());
  check(`${label}: Play works again from the first chord`, again.length === 1 && Math.abs(again[0].at - (tAgain + LEAD_MS)) <= TOL_MS && again[0].midis.join() === notesOf(v, 0).join(), again);
  E.done();
}
await clearScenario("hush (Esc/Backspace, deck Stop, MIDI panic: the cue player's clear)", (E) => E.cuePlayer.clear());
await clearScenario("an SSE clear cue", (E) => E.cuePlayer.handle({ type: "clear" }, { id: 424242, sent_at: Date.now(), age_ms: 5 }));
{
  const listeners = new Map();
  const lifecycle = { addEventListener: (type, fn) => listeners.set(type, fn), removeEventListener: (type) => listeners.delete(type) };
  await clearScenario("pagehide", () => listeners.get("pagehide")(), { lifecycle });
}
await clearScenario("a clear inside the voice's lookahead", (E) => E.cuePlayer.clear(), { when: "lookahead" });
{  // the player's own pause and stop never read as an external clear
  const E = makeEnv();
  const { clock, player, cuePlayer } = E;
  player.load(ex("flip-e"));
  await player.play();
  clock.advance(2000);
  const c0 = cuePlayer.state().clears;
  player.pause();
  await player.resume();
  clock.advance(2000);
  player.stop();
  check("pause, resume and stop never move the cue player's clear counter", cuePlayer.state().clears === c0 && player.state().reason === "stop");
  E.done();
}

// ============================================================================================ 5. transpose ==
{
  // names respelled in the new key, numbers constant
  const lc = viewOf(ex("line-cliche-em"), { transpose: 3 });
  check("line-cliche-em +3: G minor, Gm Gm(maj7)/F# Gm7/F Em7b5 Ebmaj7 D7 Gm", lc.key === "G minor"
    && lc.chords.map((c) => c.name).join(" ") === "Gm Gm(maj7)/F# Gm7/F Em7b5 Ebmaj7 D7 Gm", `${lc.key}: ${lc.chords.map((c) => c.name).join(" ")}`);
  const sw = viewOf(ex("stepwise-bass-g"), { transpose: -1 });
  check("stepwise-bass-g -1: F# major, spelled with E# and A# (not F and Bb)", sw.key === "F# major"
    && sw.chords.map((c) => c.name).join(" ") === "F# C#/E# D#m D#m7/C# Bmaj7 F#/A# G#m7 C#", `${sw.key}: ${sw.chords.map((c) => c.name).join(" ")}`);
  check("-6 and +6 name the same key", transposeKey("E minor", -6) === transposeKey("E minor", 6) && transposeKey("E minor", 6) === "Bb minor");
  let numberBad = [], rangeBad = [], shapeBad = [], shifts = 0;
  for (const e of EXERCISES) {
    for (let t = -6; t <= 6; t++) {
      const vw = viewOf(e, { transpose: t });
      shifts++;
      vw.chords.forEach((c, i) => {
        const n = nashvilleFromName(c.name, vw.key, { minor: "tonic" });
        if (c.number !== e.chords[i].number || !n || n.text !== e.chords[i].number) numberBad.push(`${e.id} ${t}: ${c.name} in ${vw.key} = ${n && n.text}`);
        if (c.bass.some((m) => m < RANGE.bassLo || m > RANGE.bassHi) || c.upper.some((m) => m < RANGE.upperLo || m > RANGE.upperHi)) rangeBad.push(`${e.id} ${t} #${i + 1}`);
        if (c.upper.join() !== e.chords[i].upper.map((m) => m + vw.upperShift).join()) shapeBad.push(`${e.id} ${t} #${i + 1}`);
      });
      const line = vw.chords.map((c) => c.bass[0]), orig = e.chords.map((c) => c.bass[0]);
      if (!line.every((m, i) => i === 0 || m - line[i - 1] === orig[i] - orig[i - 1])) shapeBad.push(`${e.id} ${t}: bass line`);
    }
  }
  check(`numbers constant across every exercise and every shift -6..+6 (${shifts} views), by the view and by nashville.js on the respelled name`, numberBad.length === 0, numberBad.slice(0, 5).join(" | "));
  check("register folding: bass in E1-E3 and right hand in A2-C6 in every key", rangeBad.length === 0, rangeBad.slice(0, 5).join(" | "));
  check("register folding: one octave move per hand for the whole exercise (bass line and right-hand shape kept)", shapeBad.length === 0, shapeBad.slice(0, 5).join(" | "));
  // a fold that has to merge an octave doubling: A1 A2 moved down a half step folds up to G#2 alone
  const la = viewOf(ex("lament-bass-am"), { transpose: -1 });
  check("lament-bass-am -1: the whole left hand moves up (bass shift +11), the doubling that would pass E3 merges (G#2)",
    la.bassShift === 11 && la.chords[0].bass.join() === "44" && la.chords[0].upper.join() === ex("lament-bass-am").chords[0].upper.map((m) => m - 1).join() && la.merged > 0,
    { bassShift: la.bassShift, bass: la.chords[0].bass, merged: la.merged });
  const f0 = foldExercise([{ bass: [40, 52], upper: [67, 71] }], 0);
  check("foldExercise leaves an exercise in range untouched", f0.bassShift === 0 && f0.upperShift === 0 && f0.merged === 0 && f0.chords[0].bass.join() === "40,52");

  // a key change while playing: the sounding chord rings on; later chords sound once, in the new key, on time
  const E = makeEnv();
  const { clock, player, voice } = E;
  const T0 = clock.now();
  const vUp = player.load(ex("flip-e"), { transpose: 3 });
  check("load with transpose 3: G minor", vUp.key === "G minor" && player.state().key === "G minor");
  await player.play();
  const on = (vw, k) => T0 + LEAD_MS + vw.chords.slice(0, k).reduce((s, c) => s + c.durMs, 0);
  clock.advanceTo(on(vUp, 1) + 500);
  player.setTranspose(-5);
  clock.advanceTo(on(vUp, 2) - 600);  // chord 3 went to the cue player already, in B minor
  player.setTranspose(6);              // inside the hand-off horizon: taken back and handed again
  const vSix = player.view;
  clock.advanceTo(on(vUp, 3) + 100);
  const heard = chordsHeard(voice, T0, clock.now());
  const cmp = compare(heard, [
    { at: on(vUp, 0), midis: notesOf(vUp, 0) }, { at: on(vUp, 1), midis: notesOf(vUp, 1) },
    { at: on(vUp, 2), midis: notesOf(vSix, 2) }, { at: on(vUp, 3), midis: notesOf(vSix, 3) },
  ]);
  check("a key change while playing: later chords sound once, in the last key picked, on time", cmp.ok && vSix.key === "Bb minor", cmpText(cmp, heard, T0));
  const sounding1 = voice.strikes.filter((s) => Math.abs(s.at - on(vUp, 1)) < EPS);
  check("... and the chord sounding at the change was not cut", sounding1.length > 0 && sounding1.every((s) => s.releasedAt === null || s.releasedAt >= on(vUp, 2) - EPS),
    sounding1.map((s) => s.releasedAt - T0));
  const caps = new Set(E.captions.filter((c) => c.label).map((c) => `${c.label} | ${c.detail}`));
  check("captions follow the key", [...caps].some((c) => c.endsWith("in G minor")) && [...caps].some((c) => c.endsWith("in Bb minor")), [...caps]);
  E.done();
}

// ======================================================================================= 6. tempo change ==
{
  const E = makeEnv({ adapter: true });  // through the adapter shape the page will hand in
  const { clock, player, voice } = E;
  const T0 = clock.now();
  const v = player.load(ex("tonic-pedal-g"));
  await player.play();
  clock.advanceTo(T0 + LEAD_MS + 1000);  // 1 s into chord 1
  player.setBpm(v.bpm * 2);
  const half = v.chords[0].durMs / 2;
  clock.advanceTo(T0 + LEAD_MS + half + v.chords[1].durMs / 2 + 200);
  const heard = chordsHeard(voice, T0, clock.now());
  const want = [T0 + LEAD_MS, T0 + LEAD_MS + half, T0 + LEAD_MS + half + v.chords[1].durMs / 2];
  const cmp = compare(heard, want.map((at, k) => ({ at, midis: notesOf(v, k) })));
  check("double tempo while chord 1 sounds: chord 2 lands at chord 1's onset plus its new length, chord 3 after that", cmp.ok, cmpText(cmp, heard, T0));
  const firstOff = voice.strikes.filter((s) => Math.abs(s.at - (T0 + LEAD_MS)) < EPS).map((s) => s.releasedAt);
  check("the sounding chord's release moved to the new change (extend), a legato overlap, no gap", firstOff.length > 0
    && firstOff.every((x) => Math.abs(x - (T0 + LEAD_MS + half + LEGATO_MS)) <= TOL_MS), firstOff.map((x) => x - T0));
  check("setBpm clamps to a playable tempo", player.setBpm(0) === v.bpm && player.setBpm(5000) === 300);
  E.done();
}

// ================================================================================== 7. chips and ghost keys ==
{
  const E = makeEnv();
  const { clock, player, voice, cuePlayer } = E;
  const v = player.load(ex("deceptive-g"));
  const tChip = clock.now();
  const u0 = voice.unlocks;
  const chip = player.playChord(3);
  check("a chip click calls voice.unlock() at once", voice.unlocks === u0 + 1);
  await chip;
  clock.advance(400);
  const heardChip = chordsHeard(voice, tChip, clock.now());
  check("a chip click while idle sounds that chord once, 150 ms after the click", heardChip.length === 1 && Math.abs(heardChip[0].at - (tChip + LEAD_MS)) <= TOL_MS
    && heardChip[0].midis.join() === notesOf(v, 3).join() && player.status === "idle" && player.state().index === 3, heardChip);
  const strikes0 = voice.strikes.length;
  player.showChord(5);
  clock.advance(1000);
  check("shift-click shows ghost keys only: a hover of that chord, no strike", voice.strikes.length === strikes0 && !!cuePlayer.state().hovering
    && cuePlayer.state().hovering.label === v.chords[5].name && cuePlayer.state().hovering.notes.join() === notesOf(v, 5).join(), cuePlayer.state().hovering);
  const tPlay = clock.now();
  await player.play();
  clock.advance(LEAD_MS + 10);
  const r = chordsHeard(voice, tPlay, clock.now());
  check("Play after a shift-click starts from that chord, and the ghost keys go", r.length === 1 && r[0].midis.join() === notesOf(v, 5).join()
    && cuePlayer.state().hovering === null, { r, hovering: cuePlayer.state().hovering });
  const tJump = clock.now();
  await player.playChord(1);
  clock.advance(LEAD_MS + 10);
  const j = chordsHeard(voice, tJump, clock.now());
  check("a chip click while playing jumps there and keeps playing", j.length === 1 && j[0].midis.join() === notesOf(v, 1).join() && player.status === "playing"
    && player.state().index === 1, j);
  player.pause();
  const tp = clock.now();
  await player.playChord(4);
  clock.advance(3000);
  check("a chip click while paused sounds that chord once and stays paused", chordsHeard(voice, tp, clock.now()).length === 1 && player.status === "paused");
  E.done();
}

// =============================================================================================== 8. stalls ==
{
  const E = makeEnv();
  const { clock, player, voice, cuePlayer } = E;
  const T0 = clock.now();
  const v = player.load(ex("flip-e"));
  await player.play();
  const on = (k) => T0 + LEAD_MS + v.chords.slice(0, k).reduce((s, c) => s + c.durMs, 0);
  clock.advanceTo(on(2) - HAND_AHEAD_MS - 100);
  clock.stall(HAND_AHEAD_MS + 200);  // frozen from before chord 3's hand-off until after chord 3 should sound
  clock.advance(4000);
  const heard = chordsHeard(voice, on(2) - 5, clock.now());
  check("a 1.2 s stall before a hand-off: the chord sounds late rather than being dropped (the rest moves later)",
    cuePlayer.state().atLateDropped === 0 && player.state().counts.slips === 1 && heard.length >= 1 && heard[0].midis.join() === notesOf(v, 2).join(),
    { dropped: cuePlayer.state().atLateDropped, slips: player.state().counts.slips, heard: heard.map((h) => h.at - on(2)) });
  E.done();
}

// ==================================================================================== 9. the unlock inside a click ==
{
  const waiting = [];
  const release = (value) => { for (const res of waiting.splice(0)) res(value); };
  const E = makeEnv({ voiceOpts: { unlockDelay: () => new Promise((res) => { waiting.push(res); }) } });
  const { clock, player, voice, cuePlayer } = E;
  player.load(ex("flip-e"));
  const p1 = player.play();
  check("play waits for the unlock: nothing is scheduled yet", player.status === "idle" && cuePlayer.state().pending === 0 && voice.unlocks === 1);
  player.pause();  // a pause (or stop, or another exercise) before the unlock finishes wins
  release("ready");
  check("a pause before the unlock finishes cancels the pending play", (await p1) === false && player.status === "idle" && cuePlayer.state().pending === 0);
  const p2 = player.play(), p3 = player.play();
  release("ready");
  const [r2, r3] = [await p2, await p3];
  clock.advance(LEAD_MS + 10);
  check("two quick clicks on Play start one run", r2 === false && r3 === true && player.status === "playing" && chordsHeard(voice).length === 1, { r2, r3, heard: chordsHeard(voice).length });
  player.stop();
  E.done();
}
{
  const E = makeEnv({ voiceOpts: { status: "off" } });
  const { clock, player, voice } = E;
  player.load(ex("flip-e"));
  await player.play();
  clock.advance(LEAD_MS + 10);
  check("with Claude's voice off the state says so (the drawer shows Turn sound on) and the keys still play", player.state().sound === "off"
    && player.status === "playing" && voice.strikes.length > 0);
  player.dispose();
  check("dispose: stopped, nothing more handed", player.status === "stopped" && player.state().handed.length === 0);
  E.done();
}
{
  let threw = null;
  try { createExercisePlayer({ cues: {} }); } catch (e) { threw = e; }
  check("a cue surface without play/handle, cancel and clears is refused at creation", threw instanceof Error);
  const E = makeEnv();
  check("load by id; an unknown id loads nothing", !!E.player.load("picardy-d") && E.player.view.id === "picardy-d" && E.player.load("no-such-exercise") === null);
  E.done();
}

for (const line of report) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
