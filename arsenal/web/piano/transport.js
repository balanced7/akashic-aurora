// Claude's band keeps time — arsenal/web/piano/transport.js (ES module, no DOM)
//
// Daniel, 2026-09-14: "I want us to be able to play in this space ... show loops of chords for me to try, I can then
// riff on that". The server records every Play, Loop and Try as a run (arsenal/jam/runs.py); this module is the page's
// half (jam-spec 8.2, 8.9, 9.2-9.5): it keeps the run's time on performance.now(), hands the cue player one bar at a
// time, lands every change on its bar line, acks the clock pair the riff analysis aligns by, and decides when a run
// Claude sends may start while Daniel is playing (the courtesy gate).
//
//   createTransport({player, voice, api, pageId, now, wallNow, log, isResting, onPosition, onGhosts, onState, ...})
//     apply(jamFrame)      a `jam` frame from the cue stream (start, launch, change, stop, owner, mark), or a sync doc
//     start(opts)          POST /api/piano/jam/start as Daniel (by daniel, this page's id)
//     control(op, args)    POST .../control on the loop (or play) run sounding now
//     stop(at = "now")     "now": every run stops here at once (80 ms fade), and the server hears of it
//     takeKnock(), declineKnock(), claimOwner(), sync(), whenResting(maxMs)
//     noteOn(), input()    Daniel played (duck, the owner lease) / touched the page (the owner lease)
//     streamStatus(s)      the cue client's status: a lost stream stops the run after 2 bars; an open re-reads state
//     tick(t)              from the page's frame loop (optional: a worker timer keeps time without it)
//     state(), stats(), records(), dispose()
//
// Time (9.1-9.3):
// - Page time of an epoch is epoch - offset. The offset (Date.now() - performance.now(), the median of 5 paired reads)
//   is taken when the run arrives and kept for the whole run. It is re-read before every bar; a move of more than 2 ms
//   (a system clock step) is never applied, so no bar line jumps, and the acks report it as offset_step_ms.
// - Bar n goes to the player at H(n) = t(n) - (one beat of bar n-1 + 150 ms) (tempomap handoffEpoch), as one local
//   sequence cue "jam:<run>:<version>:<n>" with an absolute `at`: groove.js bar n (its pickups included), one play step
//   per note, count-in and ghost ticks as player ticks. A worker timer wakes at each H(n), and at each beat line and
//   every 100 ms for the strip.
// - Ties: a note marked tie "next" is handed with its release at the next downbeat + 30 ms; when bar n+1 carries it
//   the transport extends that release instead of striking again. A carry with nothing to extend strikes at beat 0.
// - Changes on bar lines (9.4): the server lands every change at least 1 beat + 250 ms after it has it, so its frame
//   normally arrives before the bar is handed. A frame that arrives after (a slow stream) cancels the bars it changes,
//   restores the ties they had extended, regenerates them under the new version and acks late_frame_ms.
// - Stops: a stop on a bar line hands nothing from that bar on (a passes count is predicted here, so the pass after
//   the last never sounds). A stop that is due now cancels every handed bar and fades what sounds (80 ms).
// - A run with a count-in starts in silence: the pickups bar 0 owns would sound over the count-in, so they are dropped
//   (A3: no backing note before bar 0). A swapped-in run has no count-in and keeps them: they lead into the new card.
// - Clock honesty (Heimdall): the player drops a note it would sound more than 20 ms late (the downbeat bass: 40 ms)
//   rather than play it late; the count goes into the ack as late_dropped.
//
// Sound (9.5, 9.6): only the owner page sounds a run; the others hand the same bars silently, so their keys still move.
// While a run sounds the voice gets polyphony 40 and, for Loop and Try with "Duck Claude when I play" on, the duck.
// Loop and Try play the `keys` timbre; Play keeps today's voice.
//
// The courtesy gate (8.9): a run Claude starts without --now arrives pending. The owner page (or, when nobody owns the
// jam for 2 s, the first page that has it) launches it at once when Daniel rests, waits up to 20 s for a rest, then
// knocks; a knock is taken (takeKnock), declined (declineKnock: stop "declined") or expires after 60 s (stop
// "expired"). isResting() is the page's reading of his rest (createRestDetector gives one).
//
// House ideas folded in (house-ideas/vandor-integration.md): the late-note skip above (Heimdall's clock honesty), and
// Heimdall's confirmation bar on a pattern switch, opt-in (turnBar: true): the first bar of a new card or chord line
// inside a running loop plays only the bass and one upper note, so the turn is heard without watching the strip.
import { EPS_MS, barAt, barMs, handoffEpoch, medianOffset, position as mapPosition, segmentAt, tEpoch } from "./tempomap.js";
import { barOfRun, chordsInBar, eventTimes } from "./groove.js";
import { CANCEL_FADE_MS, createCueTimer } from "./cues.js";

export const TRANSPORT_API = "arsenal.jam.transport/v0";
export const WAKE_MS = 100;             // the strip's cadence while a run is live
export const ACK_EVERY_BARS = 16;       // the owner acks once per version and again every 16 bars (4.3)
export const STREAM_LOSS_BARS = 2;      // a page that lost the stream keeps a run this long (5.2)
export const OFFSET_READS = 5;
export const OFFSET_STEP_MS = 2;
export const TIE_RELEASE_MS = 30;
export const REST_WAIT_MS = 20000;
export const KNOCK_EXPIRE_MS = 60000;
export const OWNERLESS_MS = 2000;
export const LAUNCH_LEAD_MS = 250;      // the launch epoch; the server wants at least 150 ms
export const CLAIM_EVERY_MS = 10000;    // the lease is 30 s; Daniel's input renews it at most this often
export const RUN_POLYPHONY = 40;
export const IDLE_POLYPHONY = 24;
export const FOUND_HOLD_MS = 150;
export const FOUND_SHOW_MS = 600;
export const SYNC_FALLBACK_MS = 300;    // a start or launch whose frame has not arrived by then: read the state
export const REST_QUIET_MS = 1200;
export const REST_PEDAL_MS = 3000;
const EPS = 1e-6;
const RECORD_CAP = 400000;

const isObj = (x) => x !== null && typeof x === "object" && !Array.isArray(x);
const round3 = (x) => Math.round(x * 1000) / 1000;

// {n, min, p50, p99, max, mean} of a list of numbers (receipts)
export function summarize(values) {
  const s = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (!s.length) return { n: 0, min: null, p50: null, p99: null, max: null, mean: null };
  const q = (p) => s[Math.min(s.length - 1, Math.max(0, Math.ceil(p * s.length) - 1))];
  return { n: s.length, min: round3(s[0]), p50: round3(q(0.5)), p99: round3(q(0.99)), max: round3(s[s.length - 1]),
           mean: round3(s.reduce((a, b) => a + b, 0) / s.length) };
}

// The jam routes over fetch: {get(path), post(path, body)}; a non-2xx answer rejects with .status and .body.
export function createJamApi({ base = "", fetchImpl = globalThis.fetch ? globalThis.fetch.bind(globalThis) : null } = {}) {
  async function call(method, path, body) {
    if (!fetchImpl) throw new Error("fetch is unavailable");
    const res = await fetchImpl(`${base}${path}`, {
      method, cache: "no-store",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let data = null;
    try { data = await res.json(); } catch { /* no JSON body */ }
    if (!res.ok) {
      const e = new Error((data && data.error) || `${method} ${path}: HTTP ${res.status}`);
      e.status = res.status;
      e.body = data;
      throw e;
    }
    return data;
  }
  return { get: (path) => call("GET", path), post: (path, body) => call("POST", path, body ?? {}) };
}

// Daniel's rest (8.9): 1.2 s with none of his notes sounding, or 3.0 s with no note-on while only pedal-held notes
// ring. The page feeds it his note-ons, note-offs and the sustain pedal.
export function createRestDetector({ now = () => performance.now() } = {}) {
  const down = new Set();
  let lastOn = -Infinity, lastOff = -Infinity, pedal = false, pedalHeld = false;
  return {
    noteOn(midi) { down.add(midi); lastOn = now(); },
    noteOff(midi) { if (down.delete(midi)) { lastOff = now(); if (pedal) pedalHeld = true; } },
    sustain(on) { pedal = !!on; if (!pedal) { if (pedalHeld) lastOff = now(); pedalHeld = false; } },
    resting() {
      const t = now();
      if (down.size) return false;
      if (pedal && pedalHeld) return t - lastOn >= REST_PEDAL_MS;
      return t - Math.max(lastOn, lastOff) >= REST_QUIET_MS;
    },
  };
}

export function createTransport({
  player, voice = null, api = null, pageId = null, now = () => performance.now(), wallNow = () => Date.now(),
  log = null, isResting = () => true, onPosition = () => {}, onGhosts = () => {}, onState = () => {},
  sounding = null, timbre = "keys", playTimbre = null, knock = true, duck = true, turnBar = false, record = false,
  timer = "auto", onError = null,
} = {}) {
  if (!player || typeof player.handle !== "function") throw new Error("createTransport needs a cue player (createCuePlayer)");
  const jam = api && typeof api.post === "function" ? api : createJamApi(typeof api === "string" ? { base: api } : {});
  const page = typeof pageId === "string" && /^[A-Za-z0-9_.:-]{1,80}$/.test(pageId)
    ? pageId : `p-${Math.random().toString(16).slice(2, 14)}`;
  const clock = createCueTimer(timer);
  const runs = new Map();
  let owner = null;                // the jam's owner page, as the last owner frame or sync said
  let disposed = false, waking = false, timerId = null, timerAt = Infinity, timerKind = null;
  let lastClaimAt = -Infinity, duckOn = !!duck, knockOn = !!knock, turnOn = !!turnBar;
  let streamLostAt = null, polyState = null, duckState = null;
  let lastPositionKey = null, lastGhostKey = null, lastStateKey = null;
  let foundState = { key: null, since: null, until: -Infinity };
  const resters = [];
  const expired = [];
  const counts = { frames: 0, stale: 0, bars: 0, cues: 0, refused: 0, notes: 0, ticks: 0, extends: 0, extendMisses: 0,
                   carriesStruck: 0, cancels: 0, regens: 0, lateFrames: 0, skipped: 0, countInPickups: 0, turnBars: 0,
                   acks: 0, ackErrors: 0, launches: 0, launchErrors: 0, claims: 0, syncs: 0, errors: 0, offsetSteps: 0,
                   wakes: 0, localStops: 0, streamLosses: 0 };
  const wakeLate = { handoff: [], beat: [], poll: [] };
  const rec = record ? { plans: [], wakes: [], acks: [], frames: [], regens: [], positions: [], errors: [], stops: [] } : null;

  const push = (list, x, cap = RECORD_CAP) => { list.push(x); if (list.length > cap) list.splice(0, list.length - cap); };
  function report(what, e) {
    counts.errors++;
    const msg = `${what}: ${e && (e.message || e)}`;
    if (rec) push(rec.errors, { t: now(), msg });
    if (onError) { try { onError(msg); } catch { /* the reporter failed */ } } else console.warn("[transport]", msg);
  }
  const safe = (fn, ...args) => { try { return fn(...args); } catch (e) { report("callback", e); return undefined; } };

  function readOffset() {
    const pairs = [];
    for (let i = 0; i < OFFSET_READS; i++) {
      const p0 = now(), w = wallNow(), p1 = now();
      pairs.push([w, (p0 + p1) / 2]);
    }
    return medianOffset(pairs);
  }

  // ------------------------------------------------------------------------------------------------------ runs
  function newRun(f) {
    return {
      id: f.run, mode: f.mode, state: f.state || "running", version: 0, m: f.beats_per_bar || 4, segments: [],
      settings: [], defs: {}, countIn: f.count_in_bars ?? 0, start: null, bar0: null, owner: f.owner ?? null,
      card: f.card ?? null, key: f.key ?? null, stop: null, handed: new Map(), nextBar: null, catchUp: false,
      offset: readOffset(), offsetStep: null, lastAckBar: null, ackVersions: new Set(), ackKeys: new Set(),
      pendingVersionAck: null, ackExtra: false, lateFrameMs: null, droppedDone: 0, arrivedAt: now(),
      gateSince: null, knock: null, launching: false, launchFailedAt: -Infinity, deviceRan: false,
      stoppedLocally: false, ownerlessAcked: false, swappedFrom: f.swapped_from ?? null,
    };
  }
  const soundsHere = (R) => R.owner === page;
  const hasSegments = (R) => Array.isArray(R.segments) && R.segments.length > 0;

  // The server's passes end (runs.py _passes_end): the page never strikes the pass after the last.
  function passesEnd(R) {
    const s = R.settings[R.settings.length - 1];
    if (!s || !s.passes || !hasSegments(R)) return null;
    const seg = R.segments[R.segments.length - 1];
    const d = R.defs[seg.def_version];
    if (!d) return null;
    const cycle = Math.floor(d.cycle_beats / R.m);
    if (!(cycle > 0)) return null;
    let end = seg.def_from_bar + s.passes * cycle;
    while (end < s.from_bar) end += cycle;
    return end;
  }
  // From this bar on nothing strikes: the stop line or the passes end, whichever is first. A play keeps that bar for
  // the legato tails it carries.
  function cutBar(R) {
    let cut = R.stop && Number.isInteger(R.stop.bar) ? R.stop.bar : null;
    const end = passesEnd(R);
    if (end !== null) cut = cut === null ? end : Math.min(cut, end);
    return cut;
  }
  function lastHandBar(R) {
    const cut = cutBar(R);
    if (cut === null) return Infinity;
    return R.mode === "play" ? cut : cut - 1;
  }
  function handoffPerf(R, n) {
    if (!hasSegments(R) || R.stoppedLocally || n === null || n > lastHandBar(R)) return null;
    if (R.state !== "running" && R.state !== "stopped") return null;
    return handoffEpoch(R.segments, R.m, n) - R.offset;
  }
  function initNext(R) {
    const first = R.segments[0].from_bar;
    let n = first;
    try {
      const cur = barAt(R.segments, R.m, now() + R.offset).bar;
      if (cur > first) n = cur;
    } catch { /* a map the tempo module refuses: start at the first bar */ }
    R.nextBar = n;
    R.catchUp = n > first;  // a page joining a run mid-bar skips what is already past, as the regenerate does
  }
  function live(R, tPerf) {
    if (R.stoppedLocally || !hasSegments(R)) return false;
    if (R.state === "running") return true;
    return R.state === "stopped" && !!R.stop && R.stop.epoch - R.offset > tPerf;
  }
  // The run the strip shows: the newest loop or try that has begun (a swapped-in run takes over at its bar 0), else a
  // play overlaying nothing.
  function primaryRun(tPerf = now()) {
    const loops = [], plays = [];
    for (const R of runs.values()) if (live(R, tPerf)) (R.mode === "play" ? plays : loops).push(R);
    const begun = (R) => R.segments[0].epoch_ms - R.offset <= tPerf + EPS_MS;
    loops.sort((a, b) => a.segments[0].epoch_ms - b.segments[0].epoch_ms);
    const started = loops.filter(begun);
    if (started.length) return started[started.length - 1];
    if (loops.length) return loops[0];
    return plays.length ? plays[plays.length - 1] : null;
  }

  // ------------------------------------------------------------------------------------------------------ bars
  function chordLabel(R, def, n, seg) {
    try {
      const chords = chordsInBar(def, n, { def_from_bar: seg.def_from_bar });
      if (!chords.length) return { label: null, detail: null };
      const names = chords.map((c) => c.name || c.n).filter(Boolean);
      const slot = def.slots[chords[0].slot];
      return { label: names.join(" · ") || null,
               detail: `${chords.map((c) => c.n).filter(Boolean).join(" · ")} in ${(slot && slot.key) || def.key}` };
    } catch {
      return { label: null, detail: null };
    }
  }

  // Hand bar n of run R to the player. regen: the bar is handed again (a late frame, an owner change, a page joining
  // mid-bar), so notes already past are skipped rather than counted late.
  function handBar(R, n, { regen = false } = {}) {
    const m = R.m, segs = R.segments;
    let out;
    try {
      out = barOfRun({ beats_per_bar: m, segments: segs, settings: R.settings, mode: R.mode }, R.defs, n);
    } catch (e) {
      report(`bar ${n} of run ${R.id}`, e);
      return null;
    }
    const events = eventTimes(segs, m, n, out.events);
    const tNow = now();
    const sound = soundsHere(R);
    const cut = cutBar(R);
    const carriesOnly = cut !== null && n >= cut;  // only a play gets here: its tails ring out
    const prevH = R.handed.get(n - 1) || null;
    const seg = segmentAt(segs, n);
    const def = R.defs[out.def_version];
    const H = { bar: n, version: R.version, cueId: `jam:${R.id}:${R.version}:${n}`, basePerf: null, sound, ties: [],
                extends: [], lastPerf: -Infinity, handedAt: tNow, regen };
    const perf = (epoch) => epoch - R.offset;
    const nextDown = perf(tEpoch(segs, m, n + 1));
    // Heimdall's confirmation bar (opt-in): the first bar of a new def inside a run plays the bass and one upper note
    const turn = turnOn && R.mode !== "play" && n === seg.def_from_bar && n > segs[0].from_bar && seg.def_version !== segs[0].def_version;
    let turnUpper = null;
    if (turn) {
      for (const ev of events) {
        if (ev.voice === "upper" && !ev.carry && Math.abs(ev.beat) < EPS && (turnUpper === null || ev.midi > turnUpper)) turnUpper = ev.midi;
      }
      counts.turnBars++;
    }
    const strikes = [];
    for (const ev of events) {
      const at = perf(ev.epoch_ms);
      const release = ev.tie === "next" ? nextDown + TIE_RELEASE_MS : perf(ev.end_epoch_ms);
      if (ev.carry) {
        const tie = prevH ? prevH.ties.find((t) => !t.claimed && t.midi === ev.midi && t.voice === ev.voice) : null;
        if (tie) {
          let ok = false;
          try { ok = player.extend(tie.cueId, tie.step, release); } catch (e) { report("extend", e); }
          if (ok) {
            counts.extends++;
            H.extends.push({ tie, fromPerf: tie.releasePerf });
            tie.claimed = true;
            tie.releasePerf = release;
            if (ev.tie === "next") H.ties.push({ midi: ev.midi, voice: ev.voice, cueId: tie.cueId, step: tie.step, releasePerf: release, claimed: false });
            H.lastPerf = Math.max(H.lastPerf, release);
            if (rec) push(rec.plans, { run: R.id, v: H.version, bar: n, cue: tie.cueId, i: tie.step, kind: "extend", at, epoch: ev.epoch_ms, off: R.offset, beat: ev.beat, midi: ev.midi, voice: ev.voice, row: ev.row, rel: release, regen });
            continue;
          }
          counts.extendMisses++;
        }
        if (carriesOnly) continue;
        counts.carriesStruck++;  // nothing to extend (a change landed on this bar line): strike it at beat 0
      } else if (carriesOnly) {
        continue;
      }
      if (ev.voice !== "tick" && R.countIn > 0 && n * m + ev.beat < -EPS) { counts.countInPickups++; continue; }
      if (turn && ev.voice === "upper" && !(ev.midi === turnUpper && Math.abs(ev.beat) < EPS)) continue;
      if (regen && at < tNow) { counts.skipped++; continue; }
      if (ev.voice === "tick" && !sound) continue;
      strikes.push({ ev, at, release });
    }
    if (strikes.length) {
      let base = Infinity;
      for (const s of strikes) base = Math.min(base, s.at);
      H.basePerf = base;
      const steps = [], ticks = [], grace = [];
      for (const s of strikes) {
        const ev = s.ev;
        if (ev.voice === "tick") {
          ticks.push({ at_ms: s.at - base, freq: ev.freq, velocity: Math.min(127, Math.max(1, Math.round(ev.vel))) });
          H.lastPerf = Math.max(H.lastPerf, s.at);
          counts.ticks++;
          if (rec) push(rec.plans, { run: R.id, v: H.version, bar: n, cue: H.cueId, i: ticks.length - 1, kind: "tick", at: base + (s.at - base), epoch: ev.epoch_ms, off: R.offset, beat: ev.beat, ms: ev.ms, freq: ev.freq, vel: ev.vel, row: ev.row, regen });
          continue;
        }
        const i = steps.length;
        steps.push({ at_ms: s.at - base, type: "play", notes: [ev.midi], velocity: Math.min(127, Math.max(1, Math.round(ev.vel))),
                     hold_ms: Math.max(1, s.release - s.at) });
        if (ev.voice === "bass" && Math.abs(ev.beat) < EPS) grace.push(i);
        if (ev.tie === "next" && !ev.carry) H.ties.push({ midi: ev.midi, voice: ev.voice, cueId: H.cueId, step: i, releasePerf: s.release, claimed: false });
        H.lastPerf = Math.max(H.lastPerf, s.release);
        counts.notes++;
        if (rec) push(rec.plans, { run: R.id, v: H.version, bar: n, cue: H.cueId, i, kind: "note", at: base + (s.at - base), epoch: ev.epoch_ms, off: R.offset, beat: ev.beat, ms: ev.ms, midi: ev.midi, voice: ev.voice, row: ev.row, vel: ev.vel, rel: s.release, tie: ev.tie, carry: !!ev.carry, regen });
      }
      const { label, detail } = def ? chordLabel(R, def, n, seg) : { label: null, detail: null };
      const cue = { type: "sequence", source: "claude", label, detail, sound, steps };
      let r;
      try {
        r = player.handle(cue, { id: H.cueId, at: base, ticks, grace, timbre: R.mode === "play" ? playTimbre : timbre });
      } catch (e) {
        r = { ok: false, error: e && (e.message || e) };
      }
      if (r && r.ok) counts.cues++;
      else { counts.refused++; report(`bar ${n} of run ${R.id}: the player refused it`, r && r.error); }
    }
    R.handed.set(n, H);
    counts.bars++;
    return H;
  }

  // Take bar n back: cancel its cue (sounding notes fade), and put the ties it had extended back where they were.
  function unhand(R, n) {
    const H = R.handed.get(n);
    if (!H) return;
    collectDropped(R, H);
    try { if (player.cancel(H.cueId, { fadeMs: CANCEL_FADE_MS })) counts.cancels++; } catch (e) { report("cancel", e); }
    for (let i = H.extends.length - 1; i >= 0; i--) {
      const x = H.extends[i];
      try { player.extend(x.tie.cueId, x.tie.step, x.fromPerf); } catch (e) { report("extend back", e); }
      x.tie.releasePerf = x.fromPerf;
      x.tie.claimed = false;
    }
    R.handed.delete(n);
  }
  function collectDropped(R, H) {
    if (H.collected) return;
    H.collected = true;
    const info = typeof player.cueInfo === "function" ? player.cueInfo(H.cueId) : null;
    if (info) R.droppedDone += info.dropped;
  }
  function lateDropped(R) {
    let n = R.droppedDone;
    if (typeof player.cueInfo !== "function") return n;
    for (const H of R.handed.values()) {
      if (H.collected) continue;
      const info = player.cueInfo(H.cueId);
      if (info) n += info.dropped;
    }
    return n;
  }

  // Hand every bar whose hand-off time has come, and ack as the owner does.
  function stepRun(R, tPerf) {
    if (R.stoppedLocally) return;
    if (R.state === "pending") { gate(R, tPerf); return; }
    if (!hasSegments(R) || (R.state !== "running" && R.state !== "stopped")) return;
    if (R.nextBar === null) initNext(R);
    if (streamLostAt !== null && R.state === "running") {
      const s = segmentAt(R.segments, barAt(R.segments, R.m, tPerf + R.offset).bar);
      if (tPerf - streamLostAt >= STREAM_LOSS_BARS * barMs(s.bpm, R.m)) {
        counts.streamLosses++;
        stopLocal(R, "stream-lost", { ackStopped: "stream-lost" });
        return;
      }
    }
    const ctx = voice && voice.context;
    if (ctx && soundsHere(R) && R.state === "running" && typeof ctx.state === "string") {
      if (ctx.state === "running") R.deviceRan = true;
      else if (R.deviceRan) { stopLocal(R, "device", { ackStopped: "device" }); return; }
    }
    const e = tPerf + R.offset;
    for (let guard = 0; guard < 256; guard++) {
      const n = R.nextBar;
      if (n > lastHandBar(R)) break;
      if (handoffEpoch(R.segments, R.m, n) > e + EPS_MS) break;
      remeasureOffset(R);
      const H = handBar(R, n, { regen: R.catchUp });
      R.catchUp = false;
      R.nextBar = n + 1;
      if (H) maybeAck(R, n);
    }
  }

  function remeasureOffset(R) {
    const d = readOffset() - R.offset;
    if (Math.abs(d) <= OFFSET_STEP_MS) return;
    const step = round3(d);
    if (R.offsetStep === null || Math.abs(step - R.offsetStep) > OFFSET_STEP_MS) {
      R.offsetStep = step;
      R.ackExtra = true;
      counts.offsetSteps++;
    }
  }

  // ------------------------------------------------------------------------------------------------------ acks
  function maybeAck(R, n) {
    const mine = soundsHere(R);
    const ownerless = R.owner == null && !R.ownerlessAcked;
    if (!mine && !ownerless) return;
    let extra = {};
    let due = ownerless;
    if (ownerless) R.ownerlessAcked = true;
    if (R.pendingVersionAck && n >= R.pendingVersionAck.bar) {
      extra = { effective_bar: R.pendingVersionAck.bar };
      R.pendingVersionAck = null;
      due = true;
    } else if (!R.pendingVersionAck && !R.ackVersions.has(R.version)) {
      due = true;
    }
    if (R.lastAckBar === null || n - R.lastAckBar >= ACK_EVERY_BARS) due = true;
    if (R.ackExtra) due = true;
    if (due) sendAck(R, n, { ...extra, role: "owner" });
  }
  function sendAck(R, n, extra = {}) {
    if (!hasSegments(R)) return null;
    let bar = n;
    while (R.ackKeys.has(`${R.version}:${bar}`)) bar++;  // the server keeps one ack per (page, version, bar)
    R.ackKeys.add(`${R.version}:${bar}`);
    const barEpoch = tEpoch(R.segments, R.m, bar);
    let tb = null;
    if (log && typeof log.timebase === "function") {
      try { tb = log.timebase(); } catch { tb = null; }
    }
    const ctx = voice && voice.context;
    const outLat = ctx && Number.isFinite(ctx.outputLatency) && ctx.outputLatency >= 0 ? round3(ctx.outputLatency * 1000) : null;
    const body = {
      page_id: page, role: extra.role || (soundsHere(R) ? "owner" : "viewer"), version: R.version, bar,
      bar_epoch_ms: barEpoch, perf_ms: barEpoch - R.offset, perf_offset_ms: R.offset, output_latency_ms: outLat,
      log: tb && isObj(tb) ? { local: tb.local, session: tb.session ?? null, t0_perf_ms: tb.t0_perf_ms } : null,
      stopped: extra.stopped ?? null, late_dropped: lateDropped(R),
    };
    if (R.lateFrameMs !== null) { body.late_frame_ms = R.lateFrameMs; R.lateFrameMs = null; }
    if (R.offsetStep !== null) body.offset_step_ms = R.offsetStep;
    if (extra.stop_bar !== undefined) body.stop_bar = extra.stop_bar;
    if (extra.effective_bar !== undefined) body.effective_bar = extra.effective_bar;
    R.lastAckBar = n;
    R.ackVersions.add(R.version);
    R.ackExtra = false;
    counts.acks++;
    const entry = rec ? { t: now(), run: R.id, body, reply: null, error: null } : null;
    if (entry) push(rec.acks, entry);
    return jam.post(`/api/piano/jam/runs/${R.id}/ack`, body).then((reply) => {
      if (entry) entry.reply = reply;
      return reply;
    }, (e) => {
      counts.ackErrors++;
      if (entry) entry.error = String(e && (e.message || e));
      report(`ack bar ${bar} of run ${R.id}`, e);
      return null;
    });
  }

  // ------------------------------------------------------------------------------------------------------ stops
  function stopLocal(R, reason, { ackStopped = null } = {}) {
    if (R.stoppedLocally) return;
    const tPerf = now();
    let bar = null;
    if (hasSegments(R)) {
      try { bar = barAt(R.segments, R.m, tPerf + R.offset).bar; } catch { bar = null; }
    }
    const mine = soundsHere(R);
    for (const n of [...R.handed.keys()]) {
      const H = R.handed.get(n);
      collectDropped(R, H);
      try { if (player.cancel(H.cueId, { fadeMs: CANCEL_FADE_MS })) counts.cancels++; } catch (e) { report("cancel", e); }
    }
    R.stoppedLocally = true;
    if (R.state !== "stopped" || !R.stop) R.stop = { epoch: tPerf + R.offset, bar, reason };
    R.state = "stopped";
    R.knock = null;
    counts.localStops++;
    if (rec) push(rec.stops, { t: tPerf, run: R.id, reason, bar });
    if (mine && hasSegments(R) && bar !== null) sendAck(R, bar, { role: "owner", stopped: ackStopped, stop_bar: bar });
    R.handed.clear();
    settleVoice();
    emitState();
  }

  function applyStop(R, tPerf) {
    if (R.stoppedLocally) return;
    const s = R.stop;
    const stopPerf = s.epoch - R.offset;
    // A stop without a whole bar (an older server's "replaced" had none) can never cut the run on a line: it stops here
    // at once, or the page would keep handing its bars with nothing to end them.
    const onLine = (s.reason === "count" || s.reason === "replaced") && Number.isInteger(s.bar);
    if (!hasSegments(R)) { R.stoppedLocally = true; emitState(); return; }
    if (!onLine && (s.bar === null || stopPerf <= tPerf + 50)) {
      stopLocal(R, s.reason || "page");
      return;
    }
    if (s.reason === "count") return;  // predicted here: nothing on or after that bar was struck
    for (const n of [...R.handed.keys()].filter((b) => b >= s.bar).sort((a, b) => b - a)) unhand(R, n);
  }

  // ------------------------------------------------------------------------------------------------------ frames
  function setOwner(pageOrNull) {
    owner = pageOrNull;
    if (pageOrNull === null) return;
    for (const R of runs.values()) {
      if (R.stoppedLocally || R.owner === pageOrNull) continue;
      const was = soundsHere(R);
      R.owner = pageOrNull;
      if (soundsHere(R) !== was) resound(R);
    }
    settleVoice();
  }
  // The owner moved: bars handed for later are handed again with or without sound; a bar already sounding keeps going.
  function resound(R) {
    if (!hasSegments(R)) return;
    const tPerf = now();
    const future = [...R.handed.values()].filter((H) => H.basePerf === null || H.basePerf > tPerf + 5).map((H) => H.bar).sort((a, b) => a - b);
    for (let i = future.length - 1; i >= 0; i--) unhand(R, future[i]);
    for (const n of future) handBar(R, n);
  }

  function apply(f, meta = {}) {
    if (disposed || !isObj(f)) return false;
    counts.frames++;
    const tPerf = now();
    if (rec) push(rec.frames, { op: f.op, run: f.run ?? null, version: f.version ?? null, change: f.change ?? null,
                                reason: f.reason ?? null, effective_bar: f.effective_bar ?? null, epoch_ms: f.epoch_ms ?? null,
                                at: f.at ?? null, t: tPerf, wall: wallNow(), id: meta.id ?? null });
    if (f.op === "owner") { setOwner(typeof f.owner === "string" ? f.owner : null); emitState(); return true; }
    if (f.op === "mark") return true;
    if (!["start", "launch", "change", "stop", "sync"].includes(f.op) || typeof f.run !== "string") return false;
    let R = runs.get(f.run);
    if (!R) {
      if (f.op === "stop") return false;  // a run this page never had
      if (f.op !== "start" && f.op !== "sync" && !f.def) { scheduleSync(0); return false; }
      R = newRun(f);
      runs.set(f.run, R);
    } else {
      const stale = f.op === "launch" ? R.state !== "pending"
        : f.op === "sync" ? !((f.version ?? 0) > R.version || (R.state === "pending" && f.state === "running"))
        : (f.version ?? 0) <= R.version;
      if (stale) { counts.stale++; return false; }
    }
    const prevSegments = R.segments;
    if (Array.isArray(f.segments)) R.segments = f.segments;
    if (Array.isArray(f.settings)) R.settings = f.settings;
    if (Number.isInteger(f.beats_per_bar)) R.m = f.beats_per_bar;
    if (Number.isInteger(f.count_in_bars)) R.countIn = f.count_in_bars;
    if (f.start_epoch_ms != null) R.start = f.start_epoch_ms;
    if (f.bar0_epoch_ms != null) R.bar0 = f.bar0_epoch_ms;
    if (typeof f.state === "string") R.state = f.state;
    if (Number.isInteger(f.version)) R.version = Math.max(R.version, f.version);
    if (f.card !== undefined) R.card = f.card;
    if (f.key) R.key = f.key;
    if (isObj(f.defs)) for (const [k, d] of Object.entries(f.defs)) if (isObj(d)) R.defs[k] = d;
    if (isObj(f.def)) R.defs[f.op === "change" ? f.version : (f.def_version ?? 1)] = f.def;
    if (f.owner !== undefined && f.owner !== R.owner) {
      const was = soundsHere(R);
      R.owner = f.owner;
      if (soundsHere(R) !== was && R.handed.size) resound(R);
    }
    const stopped = f.op === "stop" || (f.op === "sync" && f.closed);
    if (stopped) {
      R.stop = { epoch: f.epoch_ms ?? f.stopped_epoch_ms ?? (tPerf + R.offset), bar: Number.isInteger(f.stop_bar) ? f.stop_bar : null,
                 reason: f.reason ?? f.stop_reason ?? null };
      R.state = "stopped";
      R.knock = null;
      applyStop(R, tPerf);
    } else if (hasSegments(R)) {
      if (R.nextBar === null) initNext(R);
      if (f.op === "change" && Number.isInteger(f.effective_bar)) {
        const B = f.effective_bar;
        R.pendingVersionAck = { version: R.version, bar: B };
        const late = [...R.handed.values()].filter((H) => H.bar >= B && H.version < R.version).map((H) => H.bar).sort((a, b) => a - b);
        if (late.length) {
          const handPerf = handoffEpoch(prevSegments.length ? prevSegments : R.segments, R.m, B) - R.offset;
          let lateMs = null;
          if (f.at !== "now" && tPerf > handPerf) {
            lateMs = round3(tPerf - handPerf);
            R.lateFrameMs = lateMs;
            R.ackExtra = true;
            counts.lateFrames++;
          }
          const old = late.map((n) => R.handed.get(n).cueId);
          for (let i = late.length - 1; i >= 0; i--) unhand(R, late[i]);
          const fresh = [];
          for (const n of late) { const H = handBar(R, n, { regen: true }); fresh.push(H ? H.cueId : null); }
          counts.regens += late.length;
          if (rec) push(rec.regens, { t: tPerf, run: R.id, bars: late, old, fresh, late_frame_ms: lateMs, change: f.change ?? null, at: f.at ?? null });
          if (R.nextBar <= late[late.length - 1]) R.nextBar = late[late.length - 1] + 1;
        }
      }
    }
    settleVoice();
    emitState();
    wake("frame");
    return true;
  }

  let syncTimer = null, syncing = null;
  function scheduleSync(delayMs, onlyIfPending = null) {
    if (disposed) return;
    setTimeout(() => {
      if (onlyIfPending !== null) {
        const R = runs.get(onlyIfPending.run);
        if (R && !onlyIfPending.test(R)) return;
      }
      sync();
    }, delayMs);
  }
  async function defsOf(runId) {
    const doc = await jam.get(`/api/piano/jam/runs/${runId}`);
    const defs = {};
    for (const e of (doc && doc.events) || []) {
      if (isObj(e.def) && Number.isInteger(e.version)) defs[e.version] = e.def;
    }
    return defs;
  }
  async function sync() {
    if (disposed) return null;
    if (syncing) return syncing;
    counts.syncs++;
    syncing = (async () => {
      let doc;
      try { doc = await jam.get("/api/piano/jam"); } catch (e) { report("sync", e); return null; }
      if (!isObj(doc)) return null;
      if (doc.owner !== undefined) setOwner(doc.owner && doc.owner.page_id ? doc.owner.page_id : null);
      const liveIds = new Set();
      for (const run of [doc.run, doc.play, ...(Array.isArray(doc.pending) ? doc.pending : [])]) {
        if (!isObj(run)) continue;
        liveIds.add(run.run);
        let defs = run === doc.run && isObj(doc.defs) && Object.keys(doc.defs).length ? doc.defs : null;
        if (!defs) {
          try { defs = await defsOf(run.run); } catch (e) { report(`sync defs of ${run.run}`, e); continue; }
        }
        apply({ op: "sync", run: run.run, mode: run.mode, state: run.state, version: run.last_version, segments: run.segments,
                settings: run.settings, owner: run.owner_page_id, card: run.card, key: run.key, beats_per_bar: run.beats_per_bar,
                count_in_bars: run.count_in_bars, start_epoch_ms: run.start_epoch_ms, bar0_epoch_ms: run.bar0_epoch_ms, defs,
                closed: !!run.closed, stopped_epoch_ms: run.stopped_epoch_ms, stop_bar: run.stop_bar, stop_reason: run.stop_reason });
      }
      for (const R of [...runs.values()]) {
        if (!liveIds.has(R.id) && !R.stoppedLocally && (R.state === "running" || R.state === "pending")) stopLocal(R, "gone");
      }
      return doc;
    })();
    try { return await syncing; } finally { syncing = null; }
  }

  // ------------------------------------------------------------------------------------------------------ the gate
  function gate(R, tPerf) {
    if (R.launching || R.stoppedLocally || tPerf - R.launchFailedAt < 1000) return;
    const mine = R.owner === page || (R.owner == null && (owner === null || owner === page) && tPerf - R.arrivedAt >= OWNERLESS_MS);
    if (!mine) return;
    if (R.gateSince === null) { R.gateSince = tPerf; emitState(); }
    if (R.knock) {
      if (tPerf - R.knock.since >= KNOCK_EXPIRE_MS) {
        R.knock = null;
        expired.push({ run: R.id, card: R.card, mode: R.mode, at: wallNow() });
        if (expired.length > 20) expired.shift();
        controlRun(R, "stop", { at: "now", reason: "expired" }).catch(() => {});
        emitState();
      }
      return;
    }
    let resting = true;
    try { resting = !!isResting(); } catch { resting = true; }
    if (resting) { launch(R, "rest"); return; }
    if (knockOn && tPerf - R.gateSince >= REST_WAIT_MS) {
      R.knock = { run: R.id, mode: R.mode, card: R.card, since: tPerf, at_epoch_ms: wallNow() };
      emitState();
    }
  }
  function launch(R, via) {
    if (R.launching) return Promise.resolve(null);
    R.launching = true;
    counts.launches++;
    const body = { page_id: page, epoch_ms: wallNow() + LAUNCH_LEAD_MS, via };
    return jam.post(`/api/piano/jam/runs/${R.id}/launch`, body).then((reply) => {
      R.knock = null;
      emitState();
      scheduleSync(SYNC_FALLBACK_MS, { run: R.id, test: (x) => x.state === "pending" });
      return reply;
    }, (e) => {
      R.launching = false;
      R.launchFailedAt = now();
      counts.launchErrors++;
      report(`launch ${R.id}`, e);
      if (e && e.status === 409) scheduleSync(0);
      return null;
    });
  }
  function controlRun(R, op, args = {}) {
    return jam.post(`/api/piano/jam/runs/${R.id}/control`, { op, ...args, by: "daniel" });
  }

  // ------------------------------------------------------------------------------------------------------ strip
  function slotNotes(slot) {
    const v = slot && slot.voicings;
    return v && Array.isArray(v.play) ? v.play.slice() : [];
  }
  function requiredPcs(slot) {
    const tones = isObj(slot.tones_pc) ? slot.tones_pc : {};
    const pcs = new Set(Object.values(tones).filter((x) => Number.isInteger(x)));
    const omits = Array.isArray(slot.omits) ? slot.omits : [];
    if (omits.includes("fifth") && Number.isInteger(tones.fifth)) pcs.delete(tones.fifth);
    if (Number.isInteger(slot.bass_pc)) {
      if (slot.bass_pc !== tones.root) pcs.add(slot.bass_pc);   // a slash bass is part of the chord he finds
      else if (!Object.entries(tones).some(([k, v]) => k !== "root" && v === tones.root)) pcs.delete(tones.root);
    }
    return pcs;
  }
  function ghostsFor(R, p, tPerf) {
    const none = { run: null, slot: null, target: [], incoming: [], hold: [], found: false };
    if (!R || R.mode !== "try" || !p) return none;
    const def = R.defs[p.def_version];
    if (!def || !Array.isArray(def.slots) || !def.slots.length) return none;
    const slots = def.slots;
    const g = { run: R.id, slot: p.slot, target: [], incoming: [], hold: [], found: false };
    if (p.counting_in) {
      if (p.countdown === 1 && p.bar === -1) g.incoming = slotNotes(slots[0]);
      return g;
    }
    if (p.slot === null) return g;
    const slot = slots[p.slot];
    g.target = slotNotes(slot);
    const cb = p.cycle_beat;
    const nextI = (p.slot + 1) % slots.length;
    const prevI = (p.slot - 1 + slots.length) % slots.length;
    const shared = (a, b) => slotNotes(a).filter((mid) => Array.isArray(b.chord_pcs) && b.chord_pcs.includes(((mid % 12) + 12) % 12));
    if (slots.length > 1 && slot.at_beat + slot.beats - cb <= 1 + EPS) {
      g.incoming = slotNotes(slots[nextI]);
      g.hold = shared(slots[nextI], slot);
    } else if (slots.length > 1 && cb - slot.at_beat < 1 - EPS) {
      g.hold = shared(slot, slots[prevI]);
    }
    if (typeof sounding === "function") {
      const key = `${R.id}:${p.bar}:${p.slot}`;
      if (foundState.key !== key) foundState = { key, since: null, until: -Infinity };
      let held = [];
      try { held = [...(sounding() || [])]; } catch { held = []; }
      const have = new Set(held.map((mid) => ((mid % 12) + 12) % 12));
      const need = requiredPcs(slot);
      const all = need.size > 0 && [...need].every((pc) => have.has(pc));
      if (all) {
        if (foundState.since === null) foundState.since = tPerf;
        if (tPerf - foundState.since >= FOUND_HOLD_MS && foundState.until === -Infinity) foundState.until = tPerf + FOUND_SHOW_MS;
      } else {
        foundState.since = null;
      }
      g.found = tPerf < foundState.until;
    }
    return g;
  }

  // The def the run ends on (its last segment's): where a key or card change waiting for its line is going.
  function lastDefOf(R) {
    const s = R.segments[R.segments.length - 1];
    const d = s ? R.defs[s.def_version] : null;
    return d ? { def_version: s.def_version, from_bar: s.def_from_bar, key: d.key ?? null, card_id: d.card ? d.card.id ?? null : null,
                 variant: d.card ? d.card.variant ?? null : null } : null;
  }
  const defWhere = (d) => ({ def_key: d ? d.key ?? null : null, def_variant: d && d.card ? d.card.variant ?? null : null });
  function positionOf(R, tPerf) {
    const first = R.segments[0];
    if (tPerf + R.offset < first.epoch_ms - EPS_MS) {  // not begun: no bar, no countdown yet
      return {
        ...defWhere(R.defs[first.def_version]), last_def: lastDefOf(R),
        run: R.id, mode: R.mode, state: "waiting", version: R.version, def_version: first.def_version, bar: null, beat: null,
        beat_index: null, beats_per_bar: R.m, pass: null, cycle_beat: null, slot: null, rest: true, counting_in: false,
        countdown: null, bpm: first.bpm, key: R.key, chord: null, next: null, card: R.card, owner: R.owner,
        sounding_here: soundsHere(R), stop: null, starts_in_ms: round3(first.epoch_ms - (tPerf + R.offset)), perf_ms: tPerf,
      };
    }
    const pos = mapPosition(R.segments, R.m, tPerf + R.offset, R.defs);
    const def = R.defs[pos.def_version];
    const slots = def && Array.isArray(def.slots) ? def.slots : [];
    const slot = pos.slot !== null ? slots[pos.slot] : null;
    const beatIndex = Math.floor(pos.beat + 1e-6);
    let next = null;
    if (slots.length) {
      const i = pos.slot === null || pos.counting_in ? 0 : (pos.slot + 1) % slots.length;
      const nx = slots[i];
      let inBeats = null;
      if (pos.counting_in) inBeats = (-pos.bar) * R.m - pos.beat;
      else if (def.cycle_beats) inBeats = ((nx.at_beat - pos.cycle_beat) % def.cycle_beats + def.cycle_beats) % def.cycle_beats || def.cycle_beats;
      next = { slot: i, name: nx.name ?? null, n: nx.n ?? null, key: nx.key ?? def.key ?? null, in_beats: inBeats === null ? null : round3(inBeats) };
    }
    return {
      ...defWhere(def), last_def: lastDefOf(R),  // the key and variant sounding now, and the ones the run is going to
      run: R.id, mode: R.mode, state: R.state, version: R.version, def_version: pos.def_version, bar: pos.bar,
      beat: pos.beat, beat_index: beatIndex, beats_per_bar: R.m, pass: pos.pass, cycle_beat: pos.cycle_beat, slot: pos.slot,
      rest: pos.rest, counting_in: pos.counting_in, countdown: pos.counting_in ? R.m - beatIndex : null, bpm: pos.bpm,
      key: (slot && slot.key) || R.key, chord: slot ? { name: slot.name ?? null, n: slot.n ?? null, key: slot.key ?? null } : null,
      next, card: R.card, owner: R.owner, sounding_here: soundsHere(R),
      stop: R.stop ? { bar: R.stop.bar, reason: R.stop.reason } : null, perf_ms: tPerf,
    };
  }
  function emitPosition(tPerf) {
    const R = primaryRun(tPerf);
    let p = null;
    if (R) {
      try { p = positionOf(R, tPerf); } catch (e) { p = null; }
    }
    const key = p ? `${p.run}:${p.version}:${p.bar}:${p.beat_index}:${p.slot}:${p.state}:${p.sounding_here}` : "none";
    if (key !== lastPositionKey) {
      lastPositionKey = key;
      if (rec && p) push(rec.positions, { t: tPerf, run: p.run, bar: p.bar, beat: p.beat_index, countdown: p.countdown, slot: p.slot });
      safe(onPosition, p);
    }
    const g = ghostsFor(R, p, tPerf);
    const gk = `${g.run}:${g.slot}:${g.target.join(",")}|${g.incoming.join(",")}|${g.hold.join(",")}|${g.found}`;
    if (gk !== lastGhostKey) {
      lastGhostKey = gk;
      safe(onGhosts, g);
    }
  }

  function stateNow() {
    const tPerf = now();
    const R = primaryRun(tPerf);
    const pending = [...runs.values()].filter((x) => x.state === "pending" && !x.stoppedLocally)
      .map((x) => ({ run: x.id, mode: x.mode, card: x.card, waiting_ms: x.gateSince === null ? null : Math.round(tPerf - x.gateSince) }));
    const kn = [...runs.values()].find((x) => x.knock && !x.stoppedLocally);
    return {
      state: R ? R.state : pending.length ? "pending" : "idle", run: R ? R.id : null, mode: R ? R.mode : null,
      card: R ? R.card : null, pending, owner, page_id: page, owner_here: owner === page,
      knock: kn ? { run: kn.id, mode: kn.mode, card: kn.card, at_epoch_ms: kn.knock.at_epoch_ms } : null,
      expired: expired.slice(),
    };
  }
  function emitState() {
    const s = stateNow();
    const key = JSON.stringify([s.state, s.run, s.pending.map((x) => x.run), s.knock && s.knock.run, s.owner, s.expired.length]);
    if (key === lastStateKey) return;
    lastStateKey = key;
    safe(onState, s);
  }

  // ------------------------------------------------------------------------------------------------------ voice
  function settleVoice() {
    if (!voice) return;
    const tPerf = now();
    let active = false, loopish = false;
    for (const R of runs.values()) {
      if (!live(R, tPerf) || !soundsHere(R)) continue;
      active = true;
      if (R.mode !== "play") loopish = true;
    }
    if (typeof voice.setPolyphony === "function" && active !== polyState) {
      polyState = active;
      try { voice.setPolyphony(active ? RUN_POLYPHONY : IDLE_POLYPHONY); } catch (e) { report("polyphony", e); }
    }
    const wantDuck = duckOn && loopish;
    if (typeof voice.setDuck === "function" && wantDuck !== duckState) {
      duckState = wantDuck;
      try { voice.setDuck(wantDuck); } catch (e) { report("duck", e); }
    }
  }

  // ------------------------------------------------------------------------------------------------------ the clock
  function prune(tPerf) {
    for (const R of [...runs.values()]) {
      for (const H of [...R.handed.values()]) {
        if (H.lastPerf < tPerf - 2000 && (R.nextBar === null || H.bar < R.nextBar - 2)) {
          collectDropped(R, H);
          R.handed.delete(H.bar);
        }
      }
      const done = R.stoppedLocally || (R.state === "stopped" && R.stop && R.stop.epoch - R.offset < tPerf - 5000);
      if (done && R.handed.size === 0 && tPerf - (R.stop ? R.stop.epoch - R.offset : R.arrivedAt) > 60000) runs.delete(R.id);
      else if (done && R.state === "stopped" && !R.stoppedLocally && R.stop && R.stop.epoch - R.offset < tPerf) {
        // a run that stopped on a bar line has handed its last bar: it is over here too
        if ([...R.handed.values()].every((H) => H.lastPerf < tPerf)) R.stoppedLocally = true;
      }
    }
  }
  function nextBeatPerf(R, tPerf) {
    if (!live(R, tPerf)) return null;
    try {
      const e = tPerf + R.offset;
      const p = barAt(R.segments, R.m, e);
      let bar = p.bar, k = Math.floor(p.beat + 1e-6) + 1;
      if (k >= R.m) { bar += 1; k = 0; }
      return tEpoch(R.segments, R.m, bar, k) - R.offset;
    } catch {
      return null;
    }
  }
  function busy(tPerf) {
    if (resters.length) return true;
    for (const R of runs.values()) {
      if (R.stoppedLocally) continue;
      if (R.state === "pending" || live(R, tPerf) || R.handed.size) return true;
    }
    return false;
  }
  function arm() {
    if (disposed) return;
    const tPerf = now();
    let at = Infinity, kind = null;
    if (busy(tPerf) || lastPositionKey !== "none") { at = tPerf + WAKE_MS; kind = "poll"; }
    for (const R of runs.values()) {
      const h = handoffPerf(R, R.nextBar === null && hasSegments(R) ? R.segments[0].from_bar : R.nextBar);
      if (h !== null && h < at) { at = Math.max(h, tPerf); kind = "handoff"; }
      const b = nextBeatPerf(R, tPerf);
      if (b !== null && b + 0.5 < at) { at = b + 0.5; kind = "beat"; }
    }
    if (at === Infinity) {
      if (timerId !== null) { clock.clear(timerId); timerId = null; timerAt = Infinity; }
      return;
    }
    if (timerId !== null && Math.abs(at - timerAt) < 0.25) return;
    if (timerId !== null) clock.clear(timerId);
    timerAt = at;
    timerKind = kind;
    timerId = clock.set(() => {
      timerId = null;
      const planned = timerAt, k = timerKind;
      timerAt = Infinity;
      wake(k, planned);
    }, Math.max(0, Math.ceil(at - tPerf)));
  }
  function wake(kind = "call", planned = null) {
    if (disposed) return;
    if (waking) return;
    waking = true;
    try {
      const tPerf = now();
      counts.wakes++;
      if (planned !== null && wakeLate[kind]) {
        push(wakeLate[kind], tPerf - planned, 200000);
        if (rec && kind === "handoff") push(rec.wakes, { kind, planned, t: tPerf });
      }
      if (voice && typeof voice.sampleClock === "function") { try { voice.sampleClock(); } catch { /* no clock pair */ } }
      for (const R of [...runs.values()]) stepRun(R, tPerf);  // a run stopping on a bar line still hands the bars before it
      prune(tPerf);
      settleVoice();
      emitPosition(tPerf);
      emitState();
      for (let i = resters.length - 1; i >= 0; i--) {
        const w = resters[i];
        let rested = false;
        try { rested = !!isResting(); } catch { rested = true; }
        const waited = tPerf - w.since;
        if (rested || waited >= w.maxMs) { resters.splice(i, 1); w.resolve({ rested, waited_ms: Math.round(waited) }); }
      }
    } catch (e) {
      report("wake", e);
    } finally {
      waking = false;
    }
    arm();
  }

  // ------------------------------------------------------------------------------------------------------ API
  function loopRun() {
    const tPerf = now();
    const R = primaryRun(tPerf);
    if (R) return R;
    return [...runs.values()].find((x) => x.state === "pending" && !x.stoppedLocally) || null;
  }

  return {
    apply,
    sync,
    async start(opts = {}) {
      const body = { ...opts, page_id: page, by: opts.by || "daniel" };
      const reply = await jam.post("/api/piano/jam/start", body);
      if (reply && reply.run && !runs.has(reply.run)) {
        setTimeout(() => { if (!runs.has(reply.run)) sync(); }, SYNC_FALLBACK_MS);
      }
      return reply;
    },
    async control(op, args = {}) {
      const R = loopRun();
      if (!R) throw new Error("no run to change");
      return controlRun(R, op, args);
    },
    async stop(at = "now") {
      const tPerf = now();
      // every run that could still sound here: pending, live, or one whose stop line passed with bars still handed
      // (Esc and Stop always silence Claude)
      const targets = [...runs.values()].filter((R) => !R.stoppedLocally && (R.state === "pending" || live(R, tPerf) || R.handed.size > 0));
      const replies = [];
      for (const R of targets) {
        if (at === "now") stopLocal(R, "page");
        try { replies.push(await controlRun(R, "stop", { at: R.state === "pending" ? "now" : at, reason: "page" })); }
        catch (e) { if (!(e && e.status === 409)) report(`stop ${R.id}`, e); }
      }
      wake("stop");
      return replies;
    },
    takeKnock() {
      const R = [...runs.values()].find((x) => x.knock && !x.stoppedLocally);
      if (!R) return Promise.resolve(null);
      return launch(R, "knock");
    },
    declineKnock() {
      const R = [...runs.values()].find((x) => x.knock && !x.stoppedLocally);
      if (!R) return Promise.resolve(null);
      R.knock = null;
      emitState();
      return controlRun(R, "stop", { at: "now", reason: "declined" }).catch((e) => { report("decline", e); return null; });
    },
    async claimOwner(claim = true) {
      lastClaimAt = now();
      counts.claims++;
      try {
        const reply = await jam.post("/api/piano/jam/owner", { page_id: page, claim: !!claim });
        setOwner(reply && reply.owner ? reply.owner.page_id : null);
        emitState();
        return reply;
      } catch (e) {
        report("claim", e);
        return null;
      }
    },
    noteOn() {
      if (duckState && voice && typeof voice.duck === "function") { try { voice.duck(); } catch (e) { report("duck", e); } }
      this.input();
    },
    input() {
      const tPerf = now();
      if (tPerf - lastClaimAt < (owner === page ? CLAIM_EVERY_MS : 1000)) return;
      if (owner === page || [...runs.values()].some((R) => !R.stoppedLocally && (live(R, tPerf) || R.state === "pending"))) this.claimOwner(true);
      else lastClaimAt = tPerf;
    },
    streamStatus(status) {
      if (status === "listening") {
        streamLostAt = null;
        sync();
        return;
      }
      if (["reconnecting", "closed", "paused"].includes(status) && streamLostAt === null) {
        const tPerf = now();
        if ([...runs.values()].some((R) => live(R, tPerf))) streamLostAt = tPerf;
      }
    },
    whenResting(maxMs = 8000) {
      return new Promise((resolve) => { resters.push({ since: now(), maxMs, resolve }); wake("rest"); });
    },
    tick(t) {
      if (disposed) return;
      const tPerf = now();
      if (tPerf >= timerAt - 0.5) wake("frame");
      else emitPosition(tPerf);
    },
    setDuck(on) { duckOn = !!on; settleVoice(); return duckOn; },
    setKnock(on) { knockOn = !!on; return knockOn; },
    setTurnBar(on) { turnOn = !!on; return turnOn; },
    get pageId() { return page; },
    state: stateNow,
    stats() {
      const tPerf = now();
      return {
        api: TRANSPORT_API, page_id: page, owner, timer: clock.kind, ...counts,
        wake_late_ms: { handoff: summarize(wakeLate.handoff), beat: summarize(wakeLate.beat), poll: summarize(wakeLate.poll) },
        runs: [...runs.values()].map((R) => ({
          run: R.id, mode: R.mode, state: R.state, version: R.version, live: live(R, tPerf), owner: R.owner,
          sounding_here: soundsHere(R), next_bar: R.nextBar, handed: R.handed.size, offset_ms: R.offset,
          offset_step_ms: R.offsetStep, late_dropped: lateDropped(R), stop: R.stop, count_in_bars: R.countIn,
        })),
        clock: voice && typeof voice.clock === "function" ? voice.clock() : null,
      };
    },
    records() { return rec; },
    dispose() {
      if (disposed) return;
      for (const R of runs.values()) {
        for (const H of R.handed.values()) { try { player.cancel(H.cueId, { fadeMs: CANCEL_FADE_MS }); } catch { /* gone */ } }
        R.handed.clear();
      }
      disposed = true;
      if (timerId !== null) clock.clear(timerId);
      clock.dispose();
      for (const w of resters.splice(0)) w.resolve({ rested: false, waited_ms: 0, disposed: true });
    },
  };
}
