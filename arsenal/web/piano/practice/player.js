// Practice player for the Studio drawer — arsenal/web/piano/practice/player.js  (ES module: no DOM, no drawing)
//
// Plays an exercise from practice/library.js through the page's own cue player and Claude's voice, as LOCAL at-cues, so
// its notes never reach the practice log, the key tracker, the chord reader, the Nashville row, the staff, the schemes or
// a recording (the page keeps cue notes apart from the pianist's own playing: cues.js header). Nothing goes to the server.
//
//   const player = createExercisePlayer({ cues, voice, now, onState });
//   player.load(exercise | id, { transpose, bpm, loops, autoAdvance });
//   await player.play();  player.pause();  await player.resume();  player.stop();
//   await player.next();  await player.prev();  await player.playChord(i);  player.showChord(i);
//   player.setBpm(bpm);  player.setTranspose(semis);  player.setLoops(n);  player.setAutoAdvance(on);
//   player.state()  ->  { status: "idle" | "playing" | "paused" | "stopped", reason, exerciseId, index, key, ... }
//
// cues: the page's cue surface. Either the cue player itself (createCuePlayer: handle, cancel, extend, state) or an
// adapter with play(cue, { id, at, grace }) (window.__piano.cues once it passes `at` through), cancel(id, opts),
// extend(id, stepIndex, offAt) and clears() (the cue player's state().clears).
// voice: Claude's voice (createClaudeVoice). Every method that can start sound calls voice.unlock() before anything
// else, so a click handler that calls it keeps the browser's user gesture, and awaits it. Sound off still plays the keys.
// now: performance.now(). timer: { set(fn, ms), clear(id) }; default createCueTimer("auto") (a worker timer that a hidden
// tab does not throttle). library: { FAMILIES, EXERCISES } (default ./library.js). beforeStart(): called just before a
// run is scheduled (the page can stop a running jam band there, so both never sound through one player).
//
// Scheduling (proven in the Studio pause spike against the real createCuePlayer on a manual clock and on real timers):
//   - One at-cue per chord: a sequence with a bass step and an upper step at 0 ms, id exercise:<exercise>:<run>:<pass>:<i>,
//     grace [0, 1] so a chord sounds whole or not at all. Label: the chord name; detail: "<number> in <key>".
//   - A chord goes to the cue player HAND_AHEAD_MS before it sounds; the first chord after a click sounds LEAD_MS later
//     (at least 120 ms: an at-cue step later than 20 ms is dropped, cues.js AT_LATE_MS). The player wakes at the next
//     hand-off, the next onset (to light the playing chip) and at least every POLL_MS.
//   - Slip rule: a wake too late to hand the next chord with MIN_LEAD_MS to spare moves the rest of the exercise later
//     instead of losing that chord to the late-drop (a stalled page).
//   - Pause: remember the chord sounding now, cancel every chord handed (not yet started: removed; sounding: an 80 ms
//     fade). Resume: a fresh run from that chord, LEAD_MS after the click; the chord restarts whole.
//   - External clear (Esc/Backspace hush, deck Stop, MIDI panic, an SSE clear, pagehide/freeze, dispose): the cue
//     player's clear counter moved since the run started. Noticed within POLL_MS; the player goes to stopped and hands
//     nothing more. Its own cancels never move the counter. (cueInfo(id).cancelled stays false after a clear: not a signal.)
//   - Pedal: a chord lets go LEGATO_MS after the next chord marked "change" sounds; a chord marked "hold" lets the one
//     before it ring on through it (holdOf).
//   - Loops 1, 2, 4 or forever. autoAdvance: after the last pass, one beat of silence, then the next exercise in the
//     library's menu order (the next in its group, then the next group, then the next family); the end of the library stops.
//   - A tempo, key or loops change while playing takes back the chords not yet sounding and hands them again; the
//     sounding chord's release moves with the new timing (extend).
//
// Transpose (-6..+6 semitones; the key picker offers the 12 keys of transposeChoices): numbers never change. Every note
// moves by the shift, then each hand moves by one octave amount for the WHOLE exercise, chosen so the bass line (each
// chord's lowest note) stays inside E1-E3, then the fewest notes outside, then the smallest move (ties: the lower
// octave); a note still outside (an octave doubling) moves by an octave on its own and merges with its partner. So the
// bass line and the right-hand shape are the same in every key. Names are respelled in the new key by the page's one
// speller, as chordread.js respellName does (parseChord, parseSuffix's letter steps, spell.js spellChord, chordName); key
// names are spell.js's (the page's) names.

import { formatNumber, parseChord, parseKey } from "../nashville.js";
import { DIM7_SEVENTH, chordName, keyContext, pcOf, spellChord } from "../spell.js";
import { parseSuffix } from "../chordread.js";
import { createCueTimer } from "../cues.js";
import { FAMILIES as LIBRARY_FAMILIES, EXERCISES as LIBRARY_EXERCISES } from "./library.js";

export const PRACTICE_PLAYER_API = "arsenal.piano.practice.player/v1";
export const LEAD_MS = 150;        // a click's first chord sounds this long after it (>= 120)
export const MIN_LEAD_MS = 120;    // a chord is never handed with less time than this before it sounds
export const HAND_AHEAD_MS = 1000; // a chord goes to the cue player this long before it sounds
export const POLL_MS = 100;        // the longest the player sleeps while playing (an external clear is noticed within it)
export const FADE_MS = 80;         // a cancel's fade (cues.js CANCEL_FADE_MS)
export const LEGATO_MS = 30;       // pedal "change": the old chord lets go this long after the new one sounds
export const CHIP_HOLD_MS = 1500;  // a chip click rings at least this long
export const LOOP_CHOICES = Object.freeze([1, 2, 4, Infinity]);
export const TRANSPOSE_MIN = -6, TRANSPOSE_MAX = 6;
export const BPM_MIN = 20, BPM_MAX = 300;
export const RANGE = Object.freeze({ bassLo: 28, bassHi: 52, upperLo: 45, upperHi: 84 });  // E1..E3, A2..C6
export const ID_PREFIX = "exercise:";
const GRACE = Object.freeze([0, 1]);  // both steps get the grace limit: a chord sounds whole or not at all

const mod = (a, n) => ((a % n) + n) % n;
const clampInt = (x, lo, hi) => Math.min(hi, Math.max(lo, Math.round(Number(x) || 0)));

// ------------------------------------------------------------------------------------------------------ transpose --
// The key an exercise lands in after a shift, named as the page names keys (spell.js keyContext; -6 and +6 name the same).
export function transposeKey(keyName, semis) {
  const k = keyContext(keyName);
  if (!k) return keyName;
  return keyContext({ tonic: mod(k.tonic + Math.round(Number(semis) || 0), 12), mode: k.mode }).name;
}

// A chord name moved by `semis` and respelled in `toKey` by the one speller (chordread.js respellName's steps).
export function transposeName(name, semis, toKey, minor = "tonic") {
  const c = parseChord(String(name));
  if (!c || c.kind !== "chord" || !keyContext(toKey)) return name;
  const shift = Math.round(Number(semis) || 0);
  const rootPc = mod(pcOf(c.root) + shift, 12);
  const p = parseSuffix(c.suffix);
  const steps = { ...p.tones };
  if (p.base === "dim7" && 9 in steps) steps[9] = DIM7_SEVENTH.slice();
  const ivs = Object.keys(p.tones).map(Number);
  const s = spellChord({ rootPc, tonesPc: ivs.map((iv) => rootPc + iv), steps, bassPc: c.bass ? mod(pcOf(c.bass) + shift, 12) : null,
                         key: toKey, suffix: c.suffix, minor: minor === "relative" ? "relative" : "tonic" });
  return chordName(s, c.suffix);
}

// Octave folding for a shifted exercise (see the header). chords: [{ bass, upper }]. Returns { chords: [{ bass, upper }],
// bassShift, upperShift (semitones, the shift included), merged (notes that folded on their own), lineOutside }.
export function foldExercise(chords, semis, range = RANGE) {
  const t = Math.round(Number(semis) || 0);
  const pick = (notesOf, lo, hi, lineOf) => {
    let best = null;
    for (let k = -3; k <= 3; k++) {
      const sh = t + 12 * k;
      let lineOut = 0, out = 0;
      for (const c of chords) {
        const notes = notesOf(c);
        for (const m of notes) if (m + sh < lo || m + sh > hi) out++;
        if (lineOf && notes.length) { const low = Math.min(...notes) + sh; if (low < lo || low > hi) lineOut++; }
      }
      const score = [lineOut, out, Math.abs(sh)];
      if (!best || score[0] < best.score[0] || (score[0] === best.score[0] && (score[1] < best.score[1]
          || (score[1] === best.score[1] && score[2] < best.score[2])))) best = { sh, score };
    }
    return best;
  };
  const b = pick((c) => c.bass, range.bassLo, range.bassHi, true);
  const u = pick((c) => c.upper, range.upperLo, range.upperHi, false);
  let merged = 0;
  const into = (m, lo, hi) => {
    let x = m;
    if (x < lo || x > hi) merged++;
    while (x < lo) x += 12;
    while (x > hi) x -= 12;
    return x;
  };
  const hand = (notes, sh, lo, hi) => [...new Set(notes.map((m) => into(m + sh, lo, hi)))].sort((x, y) => x - y);
  return {
    chords: chords.map((c) => ({ bass: hand(c.bass, b.sh, range.bassLo, range.bassHi), upper: hand(c.upper, u.sh, range.upperLo, range.upperHi) })),
    bassShift: b.sh, upperShift: u.sh, merged, lineOutside: b.score[0],
  };
}

// The 12 keys an exercise can move to, one shift each (-5..+6), lowest first: [{ semis, key }].
export function transposeChoices(exercise) {
  const out = [];
  for (let semis = -5; semis <= 6; semis++) out.push({ semis, key: semis ? transposeKey(exercise.key, semis) : exercise.key });
  return out;
}

const numberDisplay = (text) => { const f = text ? formatNumber(text) : null; return f ? f.display : String(text ?? ""); };

// An exercise as it will sound: shifted, folded, respelled, each chord's length in ms. Numbers never change.
export function viewOf(exercise, { transpose = 0, bpm = null } = {}) {
  const semis = clampInt(transpose, TRANSPOSE_MIN, TRANSPOSE_MAX);
  const tempo = Number.isFinite(Number(bpm)) && Number(bpm) > 0 ? Math.min(BPM_MAX, Math.max(BPM_MIN, Number(bpm))) : exercise.bpm;
  const beatMs = 60000 / tempo;
  const minor = exercise.minor === "relative" ? "relative" : "tonic";
  const key = semis && parseKey(exercise.key) ? transposeKey(exercise.key, semis) : exercise.key;
  const folded = foldExercise(exercise.chords, semis);
  const chords = exercise.chords.map((c, i) => ({
    name: semis ? transposeName(c.name, semis, key, minor) : c.name,
    number: c.number, display: numberDisplay(c.number),
    bass: folded.chords[i].bass, upper: folded.chords[i].upper,
    beats: c.beats, pedal: c.pedal === "hold" ? "hold" : "change", durMs: c.beats * beatMs,
  }));
  return { id: exercise.id, exercise, key, semis, bpm: tempo, beatMs, chords, merged: folded.merged,
           bassShift: folded.bassShift, upperShift: folded.upperShift, passMs: chords.reduce((s, c) => s + c.durMs, 0) };
}

// How long chord i rings: its own length, then on through every chord after it marked "hold" (a "hold" chord lets the one
// before it ring: library.js header), then the short legato overlap into the next chord with a fresh pedal. The chain
// stops at the end of the exercise (a library chord 0 is always "change", so a hold never crosses into the next pass).
export function holdOf(view, i) {
  const cs = view.chords;
  let ms = cs[i].durMs;
  for (let k = i + 1; k < cs.length && cs[k].pedal === "hold"; k++) ms += cs[k].durMs;
  return ms + LEGATO_MS;
}

// Chord i as a local cue: a bass step and an upper step at 0 ms (an empty hand left out).
export function chordCue(view, i, holdMs = holdOf(view, i), { bassVel = 74, upperVel = 66 } = {}) {
  const c = view.chords[i];
  const steps = [];
  if (c.bass.length) steps.push({ type: "play", at_ms: 0, notes: c.bass, velocity: bassVel, hold_ms: holdMs });
  if (c.upper.length) steps.push({ type: "play", at_ms: 0, notes: c.upper, velocity: upperVel, hold_ms: holdMs });
  return { type: "sequence", source: "claude", label: c.name, detail: `${c.display} in ${view.key}`, sound: true, steps };
}

// ------------------------------------------------------------------------------------------------------ the menu --
// The practice order: family -> group -> exercise, flattened (auto-advance and next/prev walk it).
export function libraryOrder(families) {
  return families.flatMap((f) => f.groups.flatMap((g) => g.exercises));
}
// (id, dir) -> the exercise before (dir < 0) or after, or null at either end of the library.
export function createNavigator({ FAMILIES, EXERCISES }) {
  const byId = new Map(EXERCISES.map((e) => [e.id, e]));
  const order = libraryOrder(FAMILIES);
  const navigate = (id, dir) => {
    const i = order.indexOf(id);
    const j = i + (dir < 0 ? -1 : 1);
    return i >= 0 && j >= 0 && j < order.length ? byId.get(order[j]) || null : null;
  };
  navigate.byId = byId;
  navigate.order = order;
  return navigate;
}

// The cue surface, however it was handed in (see the header).
function adaptCues(cues) {
  if (!cues) throw new Error("createExercisePlayer needs cues");
  const player = cues.player && typeof cues.player.handle === "function" ? cues.player : cues;
  const pick = (name) => (typeof cues[name] === "function" ? cues[name].bind(cues)
    : typeof player[name] === "function" ? player[name].bind(player) : null);
  const handle = typeof cues.play === "function" ? cues.play.bind(cues) : pick("handle");
  const cancel = pick("cancel");
  const extend = pick("extend");
  const clears = typeof cues.clears === "function" ? cues.clears.bind(cues)
    : typeof player.state === "function" ? () => player.state().clears : null;
  if (!handle || !cancel || !clears) throw new Error("createExercisePlayer needs cues with play or handle, cancel, and clears or state");
  return { handle, cancel, extend, clears };
}

// ---------------------------------------------------------------------------------------------------- the player --
export function createExercisePlayer({
  cues: cuesIn, voice = null, now = () => performance.now(), onState = () => {}, timer = null,
  library = { FAMILIES: LIBRARY_FAMILIES, EXERCISES: LIBRARY_EXERCISES }, beforeStart = null,
  leadMs = LEAD_MS, minLeadMs = MIN_LEAD_MS, handAheadMs = HAND_AHEAD_MS, pollMs = POLL_MS, fadeMs = FADE_MS,
} = {}) {
  const cues = adaptCues(cuesIn);
  const ownTimer = !timer;
  const clock = timer || createCueTimer("auto");
  const navigate = createNavigator(library);

  let exercise = null, view = null;
  let opts = { transpose: 0, bpm: null, loops: 1, autoAdvance: false };
  let status = "idle", reason = null;
  let run = null;               // { seq, clears, cursor: { view, pass, i, onAt, done }, handed: [], shown }
  let mark = { pass: 0, i: 0 }; // where play / resume starts
  let runSeq = 0, timerId = null, timerAt = Infinity, chipSeq = 0, chipId = null, showId = null;
  let intent = 0;               // every call that decides what happens next moves it; a pending unlock that sees it moved gives up
  let disposed = false, lastEmit = "";
  const counts = { handed: 0, refused: 0, cancels: 0, externalClears: 0, slips: 0, passes: 0, advances: 0, wakes: 0, extends: 0 };

  const loopsOf = () => opts.loops;
  const normLoops = (n) => (n === Infinity || n === "forever" ? Infinity : LOOP_CHOICES.includes(Number(n)) ? Number(n) : 1);
  const idOf = (v, seq, pass, i) => `${ID_PREFIX}${v.id}:${seq}:${pass}:${i}`;
  const soundOf = () => {
    if (!voice) return "none";
    try { return typeof voice.status === "function" ? voice.status() : voice.enabled === false ? "off" : "ready"; } catch { return "unknown"; }
  };

  function snapshot() {
    const shown = run && run.shown ? run.shown : null;
    const v = shown ? shown.view : view;
    const i = shown ? shown.i : mark.i;
    const c = v && v.chords[i] ? v.chords[i] : null;
    return { status, reason, exerciseId: v ? v.id : null, title: v ? v.exercise.title : null, index: i, pass: shown ? shown.pass : mark.pass,
             loops: loopsOf(), autoAdvance: opts.autoAdvance, key: v ? v.key : null, bpm: v ? v.bpm : null, transpose: opts.transpose,
             chord: c ? c.name : null, number: c ? c.number : null, display: c ? c.display : null, sound: soundOf() };
  }
  function emit() {
    const s = snapshot();
    const sig = JSON.stringify({ ...s, loops: String(s.loops) });
    if (sig === lastEmit) return;
    lastEmit = sig;
    try { onState(s); } catch (e) { console.warn("[practice] onState failed:", e); }
  }
  function setStatus(next, why = null) { status = next; reason = why; emit(); }

  // Calls voice.unlock() now (inside the click), then waits for it. False when a later call has taken over meanwhile.
  async function unlocked() {
    const token = ++intent;
    let pending = null;
    try { pending = voice && typeof voice.unlock === "function" ? voice.unlock() : null; } catch { pending = null; }
    try { await pending; } catch { /* still locked: the keys play without sound */ }
    return token === intent && !disposed;
  }

  function clearTimer() { if (timerId !== null) clock.clear(timerId); timerId = null; timerAt = Infinity; }
  function arm(t) {
    if (status !== "playing" || !run) return;
    const c = run.cursor;
    let wake = t + pollMs;
    if (!c.done) wake = Math.min(wake, c.onAt - handAheadMs);              // the next hand-off
    for (const h of run.handed) if (h.onAt > t) wake = Math.min(wake, h.onAt);  // the next chord to light
    if (c.done) wake = Math.min(wake, c.onAt);                              // the end
    wake = Math.max(wake, t);
    if (timerId !== null && wake === timerAt) return;
    clearTimer();
    timerAt = wake;
    timerId = clock.set(() => { timerId = null; timerAt = Infinity; tick(); }, Math.max(0, wake - now()));
  }

  const succ = (v, pass, i) => (i + 1 < v.chords.length ? [pass, i + 1] : [pass + 1, 0]);
  // The cursor after the last pass: the next exercise one beat later (autoAdvance), else done.
  function afterLastPass(cursor, v) {
    const nextEx = opts.autoAdvance ? navigate(v.id, +1) : null;
    if (!nextEx) { cursor.done = true; return cursor; }
    counts.advances++;
    return { view: viewOf(nextEx, { transpose: opts.transpose, bpm: null }), pass: 0, i: 0, onAt: cursor.onAt + v.beatMs, done: false };
  }

  // Hand the cursor's chord to the cue player and move the cursor on.
  function handNext() {
    const c = run.cursor, v = c.view, i = c.i;
    const id = idOf(v, run.seq, c.pass, i);
    const hold = holdOf(v, i);
    const cue = chordCue(v, i, hold);
    let r;
    try { r = cues.handle(cue, { id, at: c.onAt, grace: GRACE }); } catch (e) { r = { ok: false, error: e.message }; }
    if (r && r.ok) counts.handed++; else { counts.refused++; console.warn("[practice] a chord was refused:", r && r.error); }
    run.handed.push({ id, view: v, pass: c.pass, i, onAt: c.onAt, offAt: c.onAt + hold, steps: cue.steps.length });
    c.onAt += v.chords[i].durMs;
    const [pass, next] = succ(v, c.pass, i);
    if (pass !== c.pass) counts.passes++;
    c.pass = pass;
    c.i = next;
    if (pass >= loopsOf()) run.cursor = afterLastPass(c, v);
  }

  function tick() {
    counts.wakes++;
    if (status !== "playing" || !run) return;
    const t = now();
    // 1. an external clear: stop, hand nothing more
    if (cues.clears() !== run.clears) {
      counts.externalClears++;
      run = null;
      clearTimer();
      mark = { pass: 0, i: 0 };
      return setStatus("stopped", "cleared");
    }
    const c = run.cursor;
    // 2. a stalled wake: move the rest later rather than lose the next chord to the late-drop
    if (!c.done && c.onAt - t < minLeadMs) {
      c.onAt += t + leadMs - c.onAt;
      counts.slips++;
    }
    // 3. hand every chord inside the horizon
    while (!run.cursor.done && run.cursor.onAt - t <= handAheadMs) handNext();
    // 4. the chord sounding now, for the chips and the header
    let shown = null;
    for (const h of run.handed) if (h.onAt <= t) shown = h;
    if (shown && shown !== run.shown) {
      run.shown = shown;
      if (shown.view.exercise !== exercise) { exercise = shown.view.exercise; opts = { ...opts, bpm: null }; }  // auto-advanced
      if (shown.view !== view) view = shown.view;
      mark = { pass: shown.pass, i: shown.i };
    }
    run.handed = run.handed.filter((h) => h.offAt > t || h === run.shown || h.onAt > t);
    emit();
    // 5. the end
    if (run.cursor.done && t >= run.cursor.onAt) {
      run = null;
      clearTimer();
      mark = { pass: 0, i: 0 };
      return setStatus("stopped", "ended");
    }
    arm(t);
  }

  function cancelHanded(filter = () => true) {
    if (!run) return 0;
    let n = 0;
    for (const h of run.handed) {
      if (!filter(h)) continue;
      try { if (cues.cancel(h.id, { fadeMs })) { counts.cancels++; n++; } } catch (e) { console.warn("[practice] cancel failed:", e); }
    }
    run.handed = run.handed.filter((h) => !filter(h));
    return n;
  }
  function cancelChip() {
    for (const id of [chipId, showId]) if (id) { try { cues.cancel(id, { fadeMs }); } catch { /* already gone */ } }
    chipId = showId = null;
  }
  function start(pass, i) {
    clearTimer();
    cancelChip();
    if (typeof beforeStart === "function") { try { beforeStart(); } catch (e) { console.warn("[practice] beforeStart failed:", e); } }
    run = { seq: ++runSeq, clears: cues.clears(), handed: [], shown: null,
            cursor: { view, pass, i, onAt: now() + leadMs, done: false } };
    status = "playing";
    reason = null;
    tick();
  }
  function halt() {
    clearTimer();
    cancelHanded();
    run = null;
  }
  // The chord to come back to: the one sounding now, else (inside the lead before the first) the first one handed.
  function markNow(t) {
    if (!run) return mark;
    let at = null;
    for (const h of run.handed) if (h.onAt <= t) at = h;
    const h = at || run.handed[0];
    if (h) {
      if (h.view.exercise !== exercise) { exercise = h.view.exercise; opts = { ...opts, bpm: null }; }
      if (h.view !== view) view = h.view;
      return { pass: h.pass, i: h.i };
    }
    return { pass: run.cursor.pass, i: run.cursor.i };
  }
  // A tempo, key, loops or auto-advance change while playing: chords not yet sounding go back and are handed again.
  function rehandle() {
    if (status !== "playing" || !run) return;
    const t = now();
    const future = run.handed.filter((h) => h.onAt > t);
    cancelHanded((h) => h.onAt > t);
    const cur = run.handed.filter((h) => h.onAt <= t).pop() || null;
    if (cur && cur.view.exercise === exercise) {
      const [pass, i] = succ(view, cur.pass, cur.i);
      const onAt = Math.max(cur.onAt + view.chords[cur.i].durMs, t + minLeadMs);
      run.cursor = { view, pass, i, onAt, done: false };
      if (pass >= loopsOf()) run.cursor = afterLastPass(run.cursor, view);
      // the sounding chord lets go where the new timing says (after the "hold" chords that follow it), and so does an
      // earlier chord still ringing through it under a hold (its release was after the sounding chord's next one)
      if (cues.extend) {
        const off = onAt + holdOf(view, cur.i) - view.chords[cur.i].durMs;
        const ringing = run.handed.filter((h) => h === cur || (h.onAt < cur.onAt && h.view.exercise === exercise && h.offAt > cur.onAt + LEGATO_MS + 1));
        for (const h of ringing) {
          for (let s = 0; s < h.steps; s++) { try { if (cues.extend(h.id, s, off)) counts.extends++; } catch { /* gone */ } }
          h.offAt = off;
        }
      }
    } else if (future.length) {
      const f = future[0];
      run.cursor = { view: f.view.exercise === exercise ? view : f.view, pass: f.pass, i: f.i, onAt: Math.max(f.onAt, t + minLeadMs), done: false };
    }
    clearTimer();
    tick();
  }

  const exerciseOf = (x) => (typeof x === "string" ? navigate.byId.get(x) || null : x && Array.isArray(x.chords) ? x : null);

  const player = {
    load(ex, o = {}) {
      const target = exerciseOf(ex);
      if (!target || disposed) return null;
      intent++;
      halt();
      cancelChip();
      exercise = target;
      opts = {
        transpose: clampInt(o.transpose ?? opts.transpose, TRANSPOSE_MIN, TRANSPOSE_MAX),
        bpm: o.bpm ?? null,
        loops: normLoops(o.loops ?? opts.loops),
        autoAdvance: !!(o.autoAdvance ?? opts.autoAdvance),
      };
      view = viewOf(exercise, opts);
      mark = { pass: 0, i: 0 };
      setStatus("idle");
      return view;
    },
    async play() {
      if (!view || disposed) return false;
      if (status === "playing") return true;
      if (status === "paused") return player.resume();
      if (!(await unlocked())) return false;
      start(Math.min(mark.pass, loopsOf() - 1), mark.i);
      return true;
    },
    pause() {
      if (status !== "playing") { intent++; return false; }
      intent++;
      mark = markNow(now());
      halt();
      setStatus("paused");
      return true;
    },
    async resume() {
      if (status !== "paused" || disposed) return false;
      if (!(await unlocked())) return false;
      if (status !== "paused") return false;
      start(Math.min(mark.pass, loopsOf() - 1), mark.i);  // (loops lowered while paused: the last pass)
      return true;
    },
    stop() {
      intent++;
      halt();
      cancelChip();
      mark = { pass: 0, i: 0 };
      setStatus("stopped", "stop");
      return true;
    },
    next: () => player.step(+1),
    prev: () => player.step(-1),
    // Next / prev keep the key, loops and auto-advance, and take the new exercise's own tempo. Playing stays playing.
    async step(dir) {
      if (disposed) return false;
      const base = run && run.shown ? run.shown.view.id : view ? view.id : null;
      const target = base ? navigate(base, dir) : null;
      if (!target) return false;
      if (!(await unlocked())) return false;
      const playing = status === "playing";
      halt();
      cancelChip();
      exercise = target;
      opts = { ...opts, bpm: null };
      view = viewOf(target, opts);
      mark = { pass: 0, i: 0 };
      if (playing) start(0, 0); else setStatus("idle");
      return true;
    },
    // A chip: while playing, jump there; otherwise hear it once (and Play starts from it).
    async playChord(i) {
      if (!view || !view.chords[i] || disposed) return false;
      if (!(await unlocked())) return false;
      if (!view.chords[i]) return false;
      if (status === "playing") {
        const pass = run && run.shown ? run.shown.pass : 0;
        halt();
        start(pass, i);
        return true;
      }
      cancelChip();
      chipId = `${ID_PREFIX}${view.id}:chip:${++chipSeq}`;
      let r;
      try { r = cues.handle(chordCue(view, i, Math.max(view.chords[i].durMs, CHIP_HOLD_MS)), { id: chipId, at: now() + leadMs, grace: GRACE }); }
      catch (e) { r = { ok: false, error: e.message }; }
      mark = { pass: mark.pass, i };
      emit();
      return !!(r && r.ok);
    },
    // Shift-click: ghost keys only, no sound (a hover held until the next chip, Play or Stop).
    showChord(i) {
      if (!view || !view.chords[i] || disposed) return false;
      if (showId) { try { cues.cancel(showId, { fadeMs: 0 }); } catch { /* gone */ } }
      const c = view.chords[i];
      showId = `${ID_PREFIX}${view.id}:show:${++chipSeq}`;
      let r;
      try {
        r = cues.handle({ type: "hover", source: "claude", label: c.name, detail: `${c.display} in ${view.key}`, notes: [...c.bass, ...c.upper], hold_ms: 0 },
                        { id: showId, at: now() });
      } catch (e) { r = { ok: false, error: e.message }; }
      if (status !== "playing") { mark = { pass: mark.pass, i }; emit(); }
      return !!(r && r.ok);
    },
    setBpm(bpm) {
      if (!exercise) return null;
      opts.bpm = bpm;
      view = viewOf(exercise, opts);
      rehandle();
      emit();
      return view.bpm;
    },
    setTranspose(semis) {
      if (!exercise) return null;
      opts.transpose = clampInt(semis, TRANSPOSE_MIN, TRANSPOSE_MAX);
      view = viewOf(exercise, opts);
      rehandle();
      emit();
      return view.key;
    },
    setLoops(n) { opts.loops = normLoops(n); rehandle(); emit(); return opts.loops; },
    setAutoAdvance(on) { opts.autoAdvance = !!on; rehandle(); emit(); return opts.autoAdvance; },
    get status() { return status; },
    get view() { return view; },
    get exercise() { return exercise; },
    get options() { return { ...opts }; },
    state: () => ({ ...snapshot(), handed: run ? run.handed.map((h) => h.id) : [], counts: { ...counts } }),
    dispose() {
      if (disposed) return;
      intent++;
      halt();
      cancelChip();
      disposed = true;
      status = "stopped";
      reason = "dispose";
      if (ownTimer && typeof clock.dispose === "function") clock.dispose();
    },
  };
  return player;
}
