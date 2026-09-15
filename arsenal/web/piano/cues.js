// Claude's hand — arsenal/web/piano/cues.js  (ES module: no three.js, no drawing)
//
// Daniel, 2026-09-14: "can we make a verb for you to be able to play a chord you are curious about or hovering it in
// the viewer?" Claude POSTs a cue to /api/piano/cue, the server fans it out as server-sent events on /api/piano/cues,
// and this module turns each cue into the page's note and hover calls and sounds it in Claude's own voice.
//
//   normalizeCue       the protocol's validation and defaults (the server's 400 rules, mirrored)
//   createCueClient    the EventSource: status, reconnect with Last-Event-ID, dedupe, stale drop (clock-skew tolerant)
//   createCuePlayer    schedules play / hover / sequence / clear on the performance.now() clock
//   createClaudeVoice  a small WebAudio felt/electric piano, plus optional Web MIDI out, that only Claude plays
//
// The player only ever releases notes it started. Daniel may be playing at the same moment and his notes live in the
// page's own map, so every callback carries meta.source ("claude" or "replay") and the page keeps cue notes out of the
// practice log, the key tracker and anything that counts his playing. See the integration notes for piano.js.
//
// The jam space (jam-spec 9.3, 9.5-9.7, section 6) adds, all additive (a page that uses none of it behaves as before):
//   createCueClient({events: {deck, jam}})  named deck and jam frames on the same stream, deduped, never dropped as stale
//   player.handle(cue, {id, at, ticks, grace, timbre})
//                                            at: an absolute performance.now() start (transport.js hands one bar at a
//                                            time); a step more than AT_LATE_MS late is dropped, a grace step (the
//                                            downbeat bass) up to AT_GRACE_MS; ticks: count-in and ghost clicks
//   player.extend(id, stepIndex, offAt)      moves a planned or sounding note's release (a tie into the next bar)
//   player.cancel(id)                        ends one cue: actions not started go, sounding notes fade over 80 ms
//   voice.tick, setPolyphony, setDuck/duck, timbre("keys"), sampleClock (the fitted audio clock), extend

export const STALE_MS = 10000;
export const NOTE_MIN = 21;
export const NOTE_MAX = 108;
export const CUE_DEFAULTS = Object.freeze({ velocity: 80, hold_ms: 2500, arpeggio_ms: 0 });
export const AT_LATE_MS = 20;       // an at-cue step later than this when it would sound is dropped (9.3)
export const AT_GRACE_MS = 40;      // ...except a grace step (the downbeat bass), up to this
export const CANCEL_FADE_MS = 80;   // cancel(id): notes already sounding fade out over this
export const TICK_MS = 20;          // voice.tick: a short sine
export const TIMBRES = Object.freeze(["default", "keys", "click"]);

// ------------------------------------------------------------------ protocol --
const TYPES = new Set(["play", "hover", "sequence", "clear"]);
const STEP_TYPES = new Set(["play", "hover"]);
const SOURCES = new Set(["claude", "replay"]);
const MAX_STEPS = 4096;

class CueError extends Error {}
const isObj = (x) => x !== null && typeof x === "object" && !Array.isArray(x);
const isInt = (x) => typeof x === "number" && Number.isInteger(x);

function readNotes(src, where) {
  const notes = src.notes;
  if (!Array.isArray(notes) || notes.length === 0) {
    throw new CueError(`${where}notes must be a non-empty list of MIDI notes ${NOTE_MIN}..${NOTE_MAX}`);
  }
  for (const n of notes) {
    if (!isInt(n) || n < NOTE_MIN || n > NOTE_MAX) {
      throw new CueError(`${where}notes has ${JSON.stringify(n)}, which is not a MIDI note ${NOTE_MIN}..${NOTE_MAX}`);
    }
  }
  return [...new Set(notes)].sort((a, b) => a - b);  // bottom-up, so an arpeggio rolls from the bass
}
function readInt(src, field, lo, hi, fallback, where) {
  const v = src[field];
  if (v === undefined || v === null) {
    if (fallback === undefined) throw new CueError(`${where}${field} is required`);
    return fallback;
  }
  if (!isInt(v) || v < lo || v > hi) {
    throw new CueError(`${where}${field} must be an integer ${hi === Infinity ? `>= ${lo}` : `${lo}..${hi}`}, not ${JSON.stringify(v)}`);
  }
  return v;
}
function readText(src, field, where) {
  const v = src[field];
  if (v === undefined || v === null) return null;
  if (typeof v !== "string") throw new CueError(`${where}${field} must be a string or null`);
  return v;
}
// A time field: whole ms on the wire (the server's rule); a page-local cue with an absolute `at` (the transport) may
// carry fractions of a ms, so a bar's notes land on the tempo map exactly.
function readTime(src, field, fallback, where, exact) {
  if (!exact) return readInt(src, field, 0, Infinity, fallback, where);
  const v = src[field];
  if (v === undefined || v === null) {
    if (fallback === undefined) throw new CueError(`${where}${field} is required`);
    return fallback;
  }
  if (typeof v !== "number" || !Number.isFinite(v) || v < 0) {
    throw new CueError(`${where}${field} must be a number >= 0, not ${JSON.stringify(v)}`);
  }
  return v;
}
function readCue(raw, { exact = false, emptySteps = false } = {}) {
  if (!isObj(raw)) throw new CueError("a cue must be a JSON object");
  if (!TYPES.has(raw.type)) throw new CueError(`type must be play, hover, sequence or clear, not ${JSON.stringify(raw.type)}`);
  const source = raw.source === undefined || raw.source === null ? "claude" : raw.source;
  if (!SOURCES.has(source)) throw new CueError(`source must be claude or replay, not ${JSON.stringify(raw.source)}`);
  const cue = { type: raw.type, source, label: readText(raw, "label", ""), detail: readText(raw, "detail", "") };
  if (cue.type === "clear") return cue;
  cue.velocity = readInt(raw, "velocity", 1, 127, CUE_DEFAULTS.velocity, "");
  cue.hold_ms = readTime(raw, "hold_ms", CUE_DEFAULTS.hold_ms, "", exact);
  cue.arpeggio_ms = readTime(raw, "arpeggio_ms", CUE_DEFAULTS.arpeggio_ms, "", exact);
  if (raw.sound !== undefined && raw.sound !== null && typeof raw.sound !== "boolean") throw new CueError("sound must be true or false");
  cue.sound = cue.type === "hover" ? false : raw.sound !== false;
  if (cue.type !== "sequence") {
    cue.notes = readNotes(raw, "");
    return cue;
  }
  if (!Array.isArray(raw.steps) || (raw.steps.length === 0 && !emptySteps)) throw new CueError("a sequence needs steps, a non-empty list");
  if (raw.steps.length > MAX_STEPS) throw new CueError(`a sequence may have at most ${MAX_STEPS} steps`);
  cue.steps = raw.steps.map((s, i) => {
    const where = `steps[${i}].`;
    if (!isObj(s)) throw new CueError(`steps[${i}] must be an object`);
    if (!STEP_TYPES.has(s.type)) throw new CueError(`${where}type must be play or hover, not ${JSON.stringify(s.type)}`);
    return {
      index: i, at_ms: readTime(s, "at_ms", undefined, where, exact), type: s.type, notes: readNotes(s, where),
      velocity: readInt(s, "velocity", 1, 127, cue.velocity, where),
      hold_ms: readTime(s, "hold_ms", cue.hold_ms, where, exact),
      arpeggio_ms: readTime(s, "arpeggio_ms", cue.arpeggio_ms, where, exact),
      label: readText(s, "label", where), detail: readText(s, "detail", where),
    };
  }).sort((a, b) => a.at_ms - b.at_ms || a.index - b.index);
  return cue;
}

// { ok: true, cue } with every default filled in, or { ok: false, error } saying what is wrong. Idempotent.
// opts (page-local cues only, never the wire): exact lets time fields carry fractions of a ms; emptySteps accepts a
// sequence with no steps (a count-in bar that is only ticks).
export function normalizeCue(raw, opts = {}) {
  try {
    return { ok: true, cue: readCue(raw, opts) };
  } catch (e) {
    if (e instanceof CueError) return { ok: false, error: e.message };
    throw e;
  }
}

// -------------------------------------------------------------------- client --
// onCue(cue, { id, sent_at, age_ms, skew_ms }) gets each fresh, valid cue once. onStatus(status) hears "connecting",
// "listening", "reconnecting", "paused" (the page is hidden in the back/forward cache) and "closed". onDrop(reason,
// detail) hears "stale", "duplicate" and "malformed".
//
// Reconnects: the browser's own EventSource retry resends Last-Event-ID, and the server replays the newer cues from its
// last ten seconds. The server opens every stream with an "id:" line, so the browser has an id to send back even before
// the first cue. Server ids count up from its boot time in epoch ms, so a restarted server never reuses an id the page
// has seen. When the EventSource gives up (an HTTP error) this client opens a new one with a backoff; a fresh
// EventSource cannot set the header, so it asks with ?lastEventId= (the id of the last cue seen, or the server's
// last_id from the status probe at the previous open). Cues are also deduped by id and sent_at.
//
// Back/forward cache and frozen tabs: a page Daniel navigates away from can stay alive, frozen, with its stream open,
// and so can a background tab the browser freezes; the server would keep counting it as a listener (so `pianocue play`
// would report a page nobody can hear). On pagehide or freeze the client closes its stream ("paused"); on pageshow
// from the cache, or on resume after a freeze, it reconnects without replaying what was sent meanwhile.
//
// Staleness: a cue is dropped when (page clock + skew) - sent_at > staleMs. The skew comes from the Date header of
// GET <url>/status on every (re)connect (one-second resolution, so offsets under 1.5 s count as none). Events that
// arrive while that probe is out are held, at most a second, so a replay burst is judged with the right clock.
// Named frames (jam-spec 6): events: {deck: fn, jam: fn} registers a listener per kind on the same EventSource.
// fn(payload, {id, sent_at, age_ms, skew_ms, kind}) gets each frame once (the same id:sent_at dedupe as cues). They are
// never dropped as stale and never held behind the clock probe: a deck or jam frame is idempotent by rev or version,
// and its epochs place a late one correctly. The page opens the stream as /api/piano/cues?caps=jam1,deck1&page=<id>.
export function createCueClient({
  url = "/api/piano/cues", statusUrl = null, onCue = () => {}, onStatus = () => {}, onDrop = () => {},
  staleMs = STALE_MS, EventSourceImpl = globalThis.EventSource, fetchImpl = globalThis.fetch ? globalThis.fetch.bind(globalThis) : null,
  wallNow = () => Date.now(), backoffMs = [1000, 2000, 4000, 8000, 15000], autoStart = true,
  lifecycleTarget = typeof window !== "undefined" ? window : null, events = {},
} = {}) {
  if (!EventSourceImpl) throw new Error("EventSource is unavailable in this browser");
  const probeUrl = statusUrl || `${url.replace(/[?#].*$/, "").replace(/\/+$/, "")}/status`;
  const CLOSED = EventSourceImpl.CLOSED ?? 2;
  const seen = new Map();  // `${id}:${sent_at}`, oldest first
  const held = [];
  const counts = { received: 0, accepted: 0, stale: 0, duplicate: 0, malformed: 0, opens: 0, errors: 0, pauses: 0 };
  const namedKinds = isObj(events) ? Object.keys(events).filter((k) => k !== "cue" && typeof events[k] === "function") : [];
  const named = Object.fromEntries(namedKinds.map((k) => [k, 0]));
  let es = null, status = "idle", closed = false, parked = false, retryTimer = 0, attempt = 0;
  let skewMs = 0, skewKnown = false, probing = false, lastId = null, server = null;
  let cursor = null, cueSinceOpen = false;  // the id a fresh EventSource asks to resume from

  const warn = (what, e) => console.warn(`[cues] ${what}:`, e && (e.message || e));
  function setStatus(next) {
    if (next === status) return;
    status = next;
    try { onStatus(next); } catch (e) { warn("onStatus failed", e); }
  }
  function drop(reason, detail) {
    counts[reason]++;
    try { onDrop(reason, detail); } catch (e) { warn("onDrop failed", e); }
  }

  function connect() {
    if (closed || parked) return;
    clearTimeout(retryTimer);
    setStatus(counts.opens || attempt ? "reconnecting" : "connecting");
    // A first open never resumes (a freshly opened page must not play old cues); a reopen asks for what it missed.
    const target = cursor === null ? url : `${url}${url.includes("?") ? "&" : "?"}lastEventId=${encodeURIComponent(cursor)}`;
    const source = new EventSourceImpl(target);
    es = source;
    source.onopen = () => {
      if (source !== es || closed) return;
      attempt = 0;
      counts.opens++;
      cueSinceOpen = false;
      probeClock();
      setStatus("listening");
    };
    source.addEventListener("cue", (ev) => {
      if (source !== es || closed) return;
      counts.received++;
      if (probing) held.push(ev); else handle(ev);
    });
    for (const kind of namedKinds) {
      source.addEventListener(kind, (ev) => {
        if (source !== es || closed) return;
        counts.received++;
        handleNamed(kind, ev);
      });
    }
    source.onerror = () => {
      if (source !== es || closed) return;
      counts.errors++;
      if (source.readyState === CLOSED) {  // EventSource gave up: retry here
        source.close();
        es = null;
        const wait = backoffMs[Math.min(attempt, backoffMs.length - 1)];
        attempt++;
        retryTimer = setTimeout(connect, wait);
      }
      setStatus("reconnecting");  // CONNECTING: the browser is already retrying with Last-Event-ID
    };
  }

  function probeClock() {
    if (!fetchImpl) return;
    probing = true;
    const started = wallNow();
    const ask = fetchImpl(probeUrl, { cache: "no-store" }).then(async (res) => {
      const ended = wallNow();
      const date = res.headers.get("Date");
      let body = null;
      try { body = await res.json(); } catch { /* not JSON: the body is read either way */ }
      return { date, mid: (started + ended) / 2, body, ok: res.ok };
    }).catch(() => null);
    const timeout = new Promise((resolve) => setTimeout(resolve, 1000, null));
    Promise.race([ask, timeout]).then((r) => {
      if (r && r.date) {
        const serverMs = Date.parse(r.date);
        if (Number.isFinite(serverMs)) {
          const offset = serverMs + 500 - r.mid;  // the header is floored to the second: take the middle of it
          skewMs = Math.abs(offset) > 1500 ? offset : 0;
          skewKnown = true;
        }
      }
      if (r && r.ok && isObj(r.body)) {
        server = { listeners: r.body.listeners, last_id: r.body.last_id };
        if (!cueSinceOpen && isInt(r.body.last_id)) cursor = String(r.body.last_id);
      }
      probing = false;
      for (const ev of held.splice(0)) handle(ev);
    });
  }

  function handle(ev) {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return drop("malformed", "the event data is not JSON"); }
    if (!isObj(msg) || !isInt(msg.id) || typeof msg.sent_at !== "number" || !("cue" in msg)) {
      return drop("malformed", "an event needs id, cue and sent_at");
    }
    const key = `${msg.id}:${msg.sent_at}`;
    if (seen.has(key)) return drop("duplicate", { id: msg.id });
    seen.set(key, true);
    if (seen.size > 256) seen.delete(seen.keys().next().value);
    if (ev.lastEventId) lastId = ev.lastEventId;
    cursor = String(msg.id);
    cueSinceOpen = true;
    const age = wallNow() + skewMs - msg.sent_at;
    if (age > staleMs) return drop("stale", { id: msg.id, age_ms: Math.round(age) });
    const n = normalizeCue(msg.cue);
    if (!n.ok) return drop("malformed", { id: msg.id, error: n.error });
    counts.accepted++;
    try {
      onCue(n.cue, { id: msg.id, sent_at: msg.sent_at, age_ms: Math.round(age), skew_ms: Math.round(skewMs) });
    } catch (e) { warn("onCue failed", e); }
  }
  // A deck or jam frame: deduped with the cues (one id sequence), never stale, never held behind the clock probe.
  function handleNamed(kind, ev) {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return drop("malformed", `the ${kind} event data is not JSON`); }
    if (!isObj(msg) || !isInt(msg.id) || typeof msg.sent_at !== "number" || !isObj(msg[kind])) {
      return drop("malformed", `a ${kind} event needs id, ${kind} and sent_at`);
    }
    const key = `${msg.id}:${msg.sent_at}`;
    if (seen.has(key)) return drop("duplicate", { id: msg.id, kind });
    seen.set(key, true);
    if (seen.size > 256) seen.delete(seen.keys().next().value);
    if (ev.lastEventId) lastId = ev.lastEventId;
    cursor = String(msg.id);
    cueSinceOpen = true;
    named[kind]++;
    const age = wallNow() + skewMs - msg.sent_at;
    try {
      events[kind](msg[kind], { id: msg.id, sent_at: msg.sent_at, age_ms: Math.round(age), skew_ms: Math.round(skewMs), kind });
    } catch (e) { warn(`on ${kind} failed`, e); }
  }

  // Close the stream while the page cannot play (hidden in the back/forward cache, or frozen), reopen when it comes
  // back. A page restored from the cache fires resume before pageshow, so resume reopens only a stream freeze closed.
  let parkedBy = null;
  const onPageHide = () => park("pagehide");
  const onFreeze = () => park("freeze");
  const onResume = () => { if (parked && parkedBy === "freeze") onPageShow(null); };
  function park(by) {
    if (closed || parked) return;
    parked = true;
    parkedBy = by;
    counts.pauses++;
    clearTimeout(retryTimer);
    if (es) es.close();
    es = null;
    held.length = 0;
    setStatus("paused");
  }
  function onPageShow(e) {
    if (closed || !(parked || (e && e.persisted))) return;
    parked = false;
    parkedBy = null;
    if (es) es.close();
    es = null;
    attempt = 0;
    // No resume: while the page sat in the cache the server did not count it, so `pianocue` told Claude nobody was
    // listening. Coming back must not then play what was sent meanwhile.
    cursor = null;
    connect();
  }
  const lifeDoc = lifecycleTarget && lifecycleTarget.document && typeof lifecycleTarget.document.addEventListener === "function"
    ? lifecycleTarget.document : null;
  if (lifecycleTarget && typeof lifecycleTarget.addEventListener === "function") {
    lifecycleTarget.addEventListener("pagehide", onPageHide);
    lifecycleTarget.addEventListener("pageshow", onPageShow);
  }
  if (lifeDoc) {
    lifeDoc.addEventListener("freeze", onFreeze);
    lifeDoc.addEventListener("resume", onResume);
  }

  const client = {
    get status() { return status; },
    stats: () => ({ status, ...counts, lastId, cursor, skewMs: Math.round(skewMs), skewKnown, server, events: { ...named } }),
    start() { if (!es && !closed) { parked = false; connect(); } },
    reconnect() { if (closed) return; if (es) es.close(); es = null; parked = false; attempt = 0; connect(); },
    close() {
      closed = true;
      clearTimeout(retryTimer);
      if (es) es.close();
      es = null;
      held.length = 0;
      if (lifecycleTarget && typeof lifecycleTarget.removeEventListener === "function") {
        lifecycleTarget.removeEventListener("pagehide", onPageHide);
        lifecycleTarget.removeEventListener("pageshow", onPageShow);
      }
      if (lifeDoc) {
        lifeDoc.removeEventListener("freeze", onFreeze);
        lifeDoc.removeEventListener("resume", onResume);
      }
      setStatus("closed");
    },
  };
  if (autoStart) connect();
  return client;
}

// -------------------------------------------------------------------- player --
// Chrome throttles a hidden page's timers to about once a second, and on Windows a window fully covered by another
// counts as hidden. A dedicated worker's timers are not throttled that way, so the player keeps time with one whenever
// it can (the piano window may well sit behind the Claude app while Claude plays into it).
const WORKER_TIMER = "const t=new Map();onmessage=(e)=>{const d=e.data;if(d.cancel){clearTimeout(t.get(d.id));t.delete(d.id);return;}" +
                     "t.set(d.id,setTimeout(()=>{t.delete(d.id);postMessage(d.id);},d.delay));};";
// The same timer for other page modules that keep time (transport.js): {kind, set(fn, delayMs), clear(id), dispose()}.
export function createCueTimer(mode = "auto") { return createTimer(mode); }
function createTimer(mode) {
  const plain = { kind: "timeout", set: (fn, delay) => setTimeout(fn, delay), clear: (id) => clearTimeout(id), dispose() {} };
  if (mode === "timeout" || typeof Worker !== "function" || typeof Blob !== "function" || !globalThis.URL?.createObjectURL) return plain;
  try {
    const worker = new Worker(URL.createObjectURL(new Blob([WORKER_TIMER], { type: "text/javascript" })));
    const fns = new Map();
    let seq = 0, broken = false;
    const timer = {
      kind: "worker",
      set(fn, delay) {
        if (broken) return plain.set(fn, delay);
        const id = `w${++seq}`;
        fns.set(id, fn);
        worker.postMessage({ id, delay });
        return id;
      },
      clear(id) {
        if (typeof id !== "string") return plain.clear(id);
        if (fns.delete(id) && !broken) worker.postMessage({ id, cancel: true });
      },
      dispose() { fns.clear(); worker.terminate(); },
    };
    worker.onmessage = (e) => { const fn = fns.get(e.data); fns.delete(e.data); if (fn) fn(); };
    worker.onerror = () => {  // a blocked worker: fall back, and fire what it was holding
      broken = true;
      timer.kind = "timeout";
      const pending = [...fns.values()];
      fns.clear();
      for (const fn of pending) setTimeout(fn, 0);
    };
    return timer;
  } catch {
    return plain;
  }
}

// Callbacks (all optional):
//   noteOn(midi, velocity, meta)   a cue note goes down (meta.retrigger: the player already held this midi)
//   noteOff(midi, meta)            the player's last hold on that midi ended (meta.reason: "hold", "clear", "pagehide"
//                                  or "dispose")
//   hover(notes, info)             the hover on top changed; clearHover(info) when none is left
//   caption(info | null)           the newest active cue or step with a label or detail, for the "Claude · ..." chip
// meta and info: { source, cue_id, group, kind, label, detail, notes, step, at }.
//
// Timing: every action has an absolute performance.now() time (cue arrival + startDelayMs + at_ms + i * arpeggio_ms),
// and the one timer is re-aimed at the next action after each wake, so lateness never accumulates. Sound is handed to
// the voice lookaheadMs early with that exact time, so the audio clock places it precisely; the visual call runs when
// the time arrives. A page may also call pump() every frame.
//
// Cues that reach the page together (after a freeze, a main-thread stall, or a reconnect that replays what the page
// missed) would all start at that one moment. So a cue that was already stale when it arrived (info.age_ms, the
// client's reading of how long ago Claude sent it, over freshMs) starts no earlier than the previous cue's start plus
// the gap between their sends (info.sent_at, on the server's clock), while that previous cue is still waiting to start:
// the backlog plays in order and as far apart as Claude sent it, late rather than on top of each other (state().spaced
// counts the cues moved). A cue that arrives fresh (age_ms up to freshMs, default 250 ms; a cue without age_ms counts as
// fresh) is live: it starts on arrival, never behind a backlog, and every backlog cue still waiting to start is dropped
// (the newest word from Claude wins, and late music is worse than none: state().backlogDropped counts them). So the lag
// ends when Claude's next live cue arrives, however steadily Claude keeps sending. A clear always acts at once: it ends
// every cue that arrived before it, a waiting backlog included. Differences under GAP_SLACK_MS are network jitter and
// left alone. A cue without sent_at (a local one) starts on arrival and leaves a backlog alone.
//
// Late steps: after a stall or a freeze without pagehide, a key-down or hover more than lateDropMs late that has not
// been handed to the voice is dropped only when a later step of its own cue has also fallen due (a 2 s stall inside a
// fast walk plays on from the newest step, not every missed one at once). A late step nothing has overtaken plays late:
// a short jank never deletes a chord from a slow progression (state().lateDropped counts drops).
//
// bassDouble (off by default; setBassDouble): a played chord of three or more notes whose lowest note is below C3 also
// sounds that note an octave up, at half its velocity, in the built-in synth only (never to MIDI out, never a key), so
// a slash bass is heard on laptop and phone speakers that cannot play its fundamental.
//
// hold_ms counts from each note's own onset (an arpeggio releases in the order it rolled); 0 holds until clear.
// A new cue never cancels an older one; only clear does. When two cues hold the same midi the key stays down until the
// last of them lets go, and each strike is its own voice.
//
// At-cues (jam-spec 9.3): handle(cue, {id, at, ticks, grace, timbre}) with `at` a performance.now() time starts the cue
// at `at` exactly (no start delay, no backlog spacing) and lets its time fields carry fractions of a ms. A note of an
// at-cue that would sound more than AT_LATE_MS late is dropped, when it is planned or when its time comes, and never
// played late (the grace steps, a bar's downbeat bass, get AT_GRACE_MS); state().atLateDropped and cueInfo(id).dropped
// count them. ticks: [{at_ms, freq, velocity}] from `at`, sounded by voice.tick (a sequence may then have no steps).
// timbre: the voice timbre for its notes ("keys" for the jam backing). An at-cue with an id can be extended
// (extend(id, stepIndex, offAt): stepIndex is the step's index as sent) and cancelled (cancel(id): what has not
// started goes, what sounds fades out over 80 ms). onTick(info) is called as each tick sounds.
//
// An at-cue's sound goes to the voice atLookaheadMs (200 ms) ahead, not lookaheadMs: the voice schedules for the time
// Daniel hears it (the fitted clock), and the render clock runs ahead of that by the output latency (64-72 ms
// measured headless) plus the bus dynamics' 12 ms, so a 60 ms hand-off would reach the voice already late.
export const AT_LOOKAHEAD_MS = 200;
export function createCuePlayer({
  noteOn = () => {}, noteOff = () => {}, hover = () => {}, clearHover = () => {}, caption = () => {}, onTick = () => {},
  voice = null, now = () => performance.now(), startDelayMs = 50, lookaheadMs = 60, timer = "auto", onError = null,
  lateDropMs = null, lifecycleTarget = typeof window !== "undefined" ? window : null, bassDouble = false, freshMs = 250,
  atLookaheadMs = AT_LOOKAHEAD_MS,
} = {}) {
  const clock = createTimer(timer);
  const maxLook = Math.max(lookaheadMs, atLookaheadMs);
  // an at-cue's actions (its notes, releases and ticks) go to the voice earlier than a plain cue's
  const lookFor = (a) => (a.atLimit !== undefined || (a.kind !== "capOn" && a.kind !== "capOff" && groupOfAction(a).rec)
    ? atLookaheadMs : lookaheadMs);
  const groupOfAction = (a) => (a.kind === "on" || a.kind === "off" ? a.strike.group : a.group);
  const EARLY_MS = 1;
  const GAP_SLACK_MS = 25;       // send-gap shortfall under this is jitter, not a backlog
  const BASS_DOUBLE_BELOW = 48;  // C3
  const BASS_DOUBLE_VEL = 0.5;
  const TRACK_MAX = 512;         // at-cues remembered by id (for extend, cancel and cueInfo)
  // How late a key-down may be and still play (see tooLate): the worker timer is never more than a few ms late unless
  // the page was frozen; plain timers in a hidden page wake about once a second.
  const lateLimit = () => lateDropMs ?? (clock.kind === "worker" ? 250 : 1500);
  let queue = [];            // actions, sorted by at, then offs, ons, then arrival
  let seq = 0, groupSeq = 0, timerId = null, timerAt = Infinity, pumping = false, disposed = false;
  let cueOrder = 0;          // every cue's place in arrival order
  let anchor = null;         // { base, sent }: the previous cue's start and send time (see startOf)
  let backlog = [];          // { order, base }: cues that arrived stale and have not started, since the last fresh cue
  let bassDoubleNow = !!bassDouble;
  const held = new Map();    // midi -> strikes whose key the player put down, oldest first
  const tracked = new Map(); // at-cue id -> { id, order, steps: Map(stepIndex -> strikes), dropped, ticks, cancelled }
  let hovers = [], captions = [];
  let shownHover = null, shownCaption = null, shownUnder = null;
  let hoverDirty = false, captionDirty = false;  // shown once per pump (see pump)
  const counts = { cues: 0, noteOns: 0, noteOffs: 0, hovers: 0, clears: 0, lateDropped: 0, pageHides: 0, spaced: 0,
                   backlogDropped: 0, doubled: 0, atCues: 0, atLateDropped: 0, ticks: 0, extended: 0, cancelled: 0 };
  const late = { n: 0, sum: 0, max: -Infinity };

  function report(e) {
    if (onError) { try { onError(e); } catch { /* the reporter itself failed */ } } else console.warn("[cues] player:", e);
  }
  function safe(fn, ...args) { try { fn(...args); } catch (e) { report(e); } }
  const meta = (g, extra = {}) => ({ source: g.source, cue_id: g.cueId, group: g.id, kind: g.kind, label: g.label,
                                     detail: g.detail, notes: g.notes, step: g.step, ...extra });

  function insert(action) {
    action.seq = seq++;
    let lo = 0, hi = queue.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1, q = queue[mid];
      if (q.at < action.at || (q.at === action.at && (q.rank < action.rank || (q.rank === action.rank && q.seq < action.seq)))) lo = mid + 1;
      else hi = mid;
    }
    queue.splice(lo, 0, action);
  }

  // One play or hover: a whole cue, or one step of a sequence (parent: the sequence's own caption group, if it has
  // one). Returns when it ends (Infinity: at clear).
  // ext (at-cues only): { rec, timbre, limitFor(step) } (see handleCue).
  function plan(kind, spec, cue, at, cueId, step, parent, order, voiceCue = null, ext = null) {
    const group = { id: ++groupSeq, kind, cueId, source: cue.source, label: spec.label, detail: spec.detail,
                    notes: spec.notes, step, parent, order, voiceCue, at, total: 0, offs: 0, started: false, finished: false,
                    rec: ext ? ext.rec : null, sound: false };
    if (kind === "hover") {
      insert({ at, rank: 1, kind: "hoverOn", group, audioDone: true });
      if (spec.hold_ms > 0) insert({ at: at + spec.hold_ms, rank: 0, kind: "hoverOff", group, audioDone: true });
      return spec.hold_ms > 0 ? at + spec.hold_ms : Infinity;
    }
    const sound = cue.sound && !!voice;
    group.sound = sound;
    const low = spec.notes[0];  // notes are sorted bottom-up
    const double = bassDoubleNow && sound && spec.notes.length >= 3 && low < BASS_DOUBLE_BELOW && !spec.notes.includes(low + 12)
      ? low + 12 : null;
    const tNow = ext ? now() : 0;
    const limit = ext ? ext.limitFor(step) : undefined;
    let end = at, planned = 0;
    spec.notes.forEach((midi, i) => {
      const onAt = at + i * spec.arpeggio_ms;
      const strike = { midi, vel: spec.velocity, group, handle: null, handle2: null, double: i === 0 ? double : null,
                       down: false, done: false, off: null, dropped: false, timbre: ext ? ext.timbre : null };
      if (ext) {
        const key = step ?? 0, list = ext.rec.steps.get(key) || [];
        list.push(strike);
        ext.rec.steps.set(key, list);
        if (tNow - onAt > limit) {  // already too late to sound on time: skipped, never played late
          strike.dropped = strike.done = true;
          ext.rec.dropped++;
          counts.atLateDropped++;
          return;
        }
      }
      const on = { at: onAt, rank: 1, kind: "on", strike, audioDone: !sound };
      if (ext) on.atLimit = limit;
      insert(on);
      if (spec.hold_ms > 0) {
        strike.off = { at: onAt + spec.hold_ms, rank: 0, kind: "off", strike, audioDone: !sound };
        insert(strike.off);
      }
      end = Math.max(end, onAt + spec.hold_ms);
      planned++;
    });
    group.total = planned;
    return spec.hold_ms > 0 ? end : Infinity;
  }

  function handleCue(raw, info = {}) {
    if (disposed) return { ok: false, error: "the player is disposed" };
    const atMode = typeof info.at === "number" && Number.isFinite(info.at);
    const ticks = atMode && Array.isArray(info.ticks) ? info.ticks : [];
    const n = normalizeCue(raw, atMode ? { exact: true, emptySteps: ticks.length > 0 } : {});
    if (!n.ok) return n;
    for (const [i, tk] of ticks.entries()) {
      if (!isObj(tk) || typeof tk.at_ms !== "number" || !Number.isFinite(tk.at_ms) || tk.at_ms < 0 || typeof tk.freq !== "number"
          || !(tk.freq > 0) || (tk.velocity !== undefined && (!isInt(tk.velocity) || tk.velocity < 1 || tk.velocity > 127))) {
        return { ok: false, error: `ticks[${i}] must be {at_ms >= 0, freq > 0, velocity 1..127}` };
      }
    }
    const cue = n.cue, cueId = info.id ?? null;
    counts.cues++;
    const order = ++cueOrder;
    if (cue.type === "clear") {  // at once, backlog or not: it ends every cue that arrived before it
      anchor = null;
      clearAll("clear");
      return { ok: true };
    }
    // An at-cue starts exactly at its `at` and stays out of the backlog rules (it has no send time).
    const base = atMode ? info.at : startOf(info, order);
    // One voice across tabs: as the cue arrives the voice notes which tabs had it (see createTabArbiter), and every
    // strike of it carries that key, so the voice never passes to a tab that does not have this cue.
    const voiceCue = cue.sound && voice && typeof voice.admitCue === "function" ? voice.admitCue(info) : null;
    let ext = null;
    if (atMode) {
      counts.atCues++;
      const rec = { id: cueId, order, steps: new Map(), dropped: 0, ticks: 0, cancelled: false };
      if (cueId !== null) {
        tracked.delete(cueId);
        tracked.set(cueId, rec);
        while (tracked.size > TRACK_MAX) tracked.delete(tracked.keys().next().value);
      }
      const grace = new Set(Array.isArray(info.grace) ? info.grace : []);
      ext = { rec, timbre: typeof info.timbre === "string" ? info.timbre : null,
              limitFor: (step) => (grace.has(step ?? 0) ? AT_GRACE_MS : AT_LATE_MS) };
    }
    if (cue.type === "play" || cue.type === "hover") {
      plan(cue.type, cue, cue, base, cueId, null, null, order, voiceCue, ext);
    } else {
      // The sequence's own caption spans it. A labelled step of Claude's shows over it (the chord sounding now is the
      // news); a replay of Daniel's playing keeps its own caption ("you, at 0:30") on top, with the step's under it.
      const group = (cue.label || cue.detail) && cue.steps.length
        ? { id: ++groupSeq, kind: "sequence", cueId, source: cue.source, label: cue.label, detail: cue.detail,
            notes: [...new Set(cue.steps.flatMap((s) => s.notes))].sort((a, b) => a - b), step: null, parent: null,
            order, at: base + cue.steps[0].at_ms, started: false, finished: false, rec: ext ? ext.rec : null }
        : null;
      let end = -Infinity;
      for (const step of cue.steps) end = Math.max(end, plan(step.type, step, cue, base + step.at_ms, cueId, step.index, group, order, voiceCue, ext));
      if (group) {
        insert({ at: base + cue.steps[0].at_ms, rank: 0, kind: "capOn", group, audioDone: true });
        if (end !== Infinity) insert({ at: end, rank: 1, kind: "capOff", group, audioDone: true });
      }
    }
    if (ticks.length) {
      const tickGroup = { id: ++groupSeq, kind: "tick", cueId, source: cue.source, label: null, detail: null, notes: [], step: null,
                          parent: null, order, voiceCue, at: base, rec: ext.rec, started: true, finished: false, sound: cue.sound && !!voice };
      const tNow = now();
      for (const tk of ticks) {
        const at = base + tk.at_ms;
        if (tNow - at > AT_LATE_MS) { ext.rec.dropped++; counts.atLateDropped++; continue; }
        insert({ at, rank: 1, kind: "tick", group: tickGroup, tick: { freq: tk.freq, velocity: tk.velocity ?? 60 },
                 audioDone: !tickGroup.sound, atLimit: AT_LATE_MS });
        ext.rec.ticks++;
      }
    }
    pump();
    return { ok: true };
  }

  // When a cue starts: on arrival plus startDelayMs, or later when it is part of a backlog (see the timing notes above).
  // A fresh cue starts on arrival and ends the backlog, so a live stream is never chained behind cues that came in late.
  // A stale cue keeps its send gap only while the previous cue is still waiting to start: that is what arriving together
  // means (a cue that came in late on its own, a reconnect replaying one cue 3 s old, is not pushed later).
  function startOf(info, order) {
    const t = now(), arrival = t + startDelayMs;
    const sent = typeof info.sent_at === "number" && Number.isFinite(info.sent_at) ? info.sent_at : null;
    if (sent === null) return arrival;
    const age = typeof info.age_ms === "number" && Number.isFinite(info.age_ms) ? info.age_ms : 0;
    if (age <= freshMs) {
      dropBacklog(t);
      anchor = { base: arrival, sent };
      return arrival;
    }
    let base = arrival;
    if (anchor && anchor.base > t && sent >= anchor.sent && sent - anchor.sent <= STALE_MS) {
      const spaced = anchor.base + (sent - anchor.sent);
      if (spaced - arrival > GAP_SLACK_MS) { base = spaced; counts.spaced++; }
    }
    anchor = { base, sent };
    backlog = backlog.filter((b) => b.base > t);  // (the ones that started are no longer waiting)
    backlog.push({ order, base });
    return base;
  }
  // A fresh cue arrived: the backlog cues still waiting to start are dropped; the ones already playing play on.
  function dropBacklog(t) {
    const waiting = new Set(backlog.filter((b) => b.base > t + EARLY_MS).map((b) => b.order));
    backlog = [];
    if (!waiting.size) return;
    counts.backlogDropped += waiting.size;
    cancel((order) => waiting.has(order), "backlog");
  }

  function startGroup(g) {
    if (g.started) return;
    g.started = true;
    if (g.label || g.detail) { captions.push(g); captionDirty = true; }
  }
  function endGroup(g) {
    if (g.finished) return;
    g.finished = true;
    const i = captions.indexOf(g);
    if (i >= 0) { captions.splice(i, 1); captionDirty = true; }
  }
  function emitHover(reason = "hold") {
    const top = hovers.length ? hovers[hovers.length - 1] : null;
    if (top === shownHover) return;
    const prev = shownHover;
    shownHover = top;
    if (top) { counts.hovers++; safe(hover, top.notes.slice(), meta(top)); }
    else safe(clearHover, meta(prev, { reason }));
  }
  // The caption on top, and the line under it: for a replay, the sequence's own caption with its newest step's under
  // it; otherwise the newest caption, with nothing under it.
  function captionNow() {
    const top = captions.length ? captions[captions.length - 1] : null;
    const seq = top && (top.kind === "sequence" ? top : top.parent);
    if (!seq || seq.source !== "replay" || !captions.includes(seq)) return [top, null];
    for (let i = captions.length - 1; i >= 0; i--) if (captions[i].parent === seq) return [seq, captions[i]];
    return [seq, null];
  }
  const underOf = (g) => (g ? { label: g.label, detail: g.detail, kind: g.kind, step: g.step, notes: g.notes } : null);
  function emitCaption() {
    const [top, under] = captionNow();
    if (top === shownCaption && under === shownUnder) return;
    shownCaption = top;
    shownUnder = under;
    safe(caption, top ? meta(top, { under: underOf(under) }) : null);
  }

  // A key-down (or hover) more than lateDropMs late that has not yet been handed to the voice is dropped rather than
  // played when a later step of the same cue, of the same kind, has also fallen due: after a freeze (a laptop asleep, a
  // tab the browser froze without a pagehide) or a long stall every step that fell due would otherwise sound at once.
  // A late step that nothing has overtaken plays late. A sound already handed to the voice on time keeps its key, even
  // if the key lights late. newest: dueNewest(t), computed once per pump.
  const groupOf = (a) => (a.kind === "on" || a.kind === "off" ? a.strike.group : a.group);
  function dueNewest(t) {
    let newest = null;
    for (const a of queue) {
      if (a.at > t + EARLY_MS) break;
      if (a.kind !== "on" && a.kind !== "hoverOn") continue;
      const g = groupOf(a);
      if (g.step === null) continue;  // a play or hover cue is a single step: nothing in it overtakes
      const k = `${g.order}:${a.kind}`;
      newest = newest || new Map();
      const top = newest.get(k);
      if (!top || g.at > top.at) newest.set(k, g);
    }
    return newest;
  }
  // An at-cue's note or tick (a.atLimit) is simply too late once its time is more than its limit past, unless its
  // sound already went to the voice on time: late music is worse than none (9.3; Heimdall's clock honesty).
  function tooLate(a, t, newest) {
    if (a.handed) return false;
    if (a.atLimit !== undefined) return (a.kind === "on" || a.kind === "tick") && t - a.at > a.atLimit;
    if ((a.kind !== "on" && a.kind !== "hoverOn") || t - a.at <= lateLimit() || !newest) return false;
    const g = groupOf(a), top = newest.get(`${g.order}:${a.kind}`);
    return !!top && top.at > g.at;
  }
  function dropLate(a, t) {
    if (a.atLimit !== undefined) {
      counts.atLateDropped++;
      const g = groupOf(a);
      if (g.rec) g.rec.dropped++;
    } else {
      counts.lateDropped++;
    }
    if (a.kind === "tick") return;
    if (a.kind === "hoverOn") { a.group.finished = true; return; }  // its hoverOff finds nothing to end
    const s = a.strike;
    s.done = true;
    s.dropped = true;
    if (++s.group.offs === s.group.total) endGroup(s.group);
  }

  function doAudio(a) {
    a.audioDone = true;
    a.handed = true;
    if (a.kind === "tick") {
      if (typeof voice.tick === "function") {
        try {
          const h = voice.tick({ at: a.at, freq: a.tick.freq, velocity: a.tick.velocity, cue: a.group.voiceCue, cue_id: a.group.cueId });
          a.tickHandle = h === undefined ? null : h;
        } catch (e) { report(e); }
      }
      return;
    }
    const s = a.strike;
    try {
      if (a.kind === "on") {
        const when = { at: a.at, source: s.group.source, cue: s.group.voiceCue };
        if (s.timbre) when.timbre = s.timbre;
        if (s.group.rec) when.cue_id = s.group.cueId;
        const h = voice.noteOn(s.midi, s.vel, when);
        s.handle = h === undefined ? null : h;
        if (s.double !== null && s.handle !== null) {
          const vel = Math.max(1, Math.round(s.vel * BASS_DOUBLE_VEL));
          const h2 = voice.noteOn(s.double, vel, { at: a.at, source: s.group.source, cue: s.group.voiceCue, synthOnly: true });
          s.handle2 = h2 === undefined ? null : h2;
          if (s.handle2 !== null) counts.doubled++;
        }
      } else if (a.kind === "off") {
        releaseStrike(s, a.at);
      }
    } catch (e) { report(e); }
  }
  function releaseStrike(s, at, fadeMs = null) {
    if (!voice) return;
    const when = fadeMs === null ? { at } : { at, fadeMs };
    if (s.handle !== null) safe(() => voice.release(s.handle, when));
    if (s.handle2 !== null) safe(() => voice.release(s.handle2, when));
  }

  function exec(a, t) {
    if (a.kind === "on" || a.kind === "off" || a.kind === "hoverOn" || a.kind === "tick") {
      const d = t - a.at;
      late.n++; late.sum += d; late.max = Math.max(late.max, d);
    }
    switch (a.kind) {
      case "on": {
        const s = a.strike, list = held.get(s.midi) || [];
        const retrigger = list.length > 0;
        list.push(s);
        held.set(s.midi, list);
        s.down = true;
        counts.noteOns++;
        startGroup(s.group);
        safe(noteOn, s.midi, s.vel, meta(s.group, { at: a.at, retrigger, sound: s.handle !== null }));
        break;
      }
      case "off": {
        const s = a.strike;
        if (!s.down || s.done) break;
        s.done = true;
        const list = held.get(s.midi) || [];
        const i = list.indexOf(s);
        if (i >= 0) list.splice(i, 1);
        if (!list.length) {
          held.delete(s.midi);
          counts.noteOffs++;
          safe(noteOff, s.midi, meta(s.group, { at: a.at, reason: "hold" }));
        }
        if (++s.group.offs === s.group.total) endGroup(s.group);
        break;
      }
      case "hoverOn": hovers.push(a.group); startGroup(a.group); hoverDirty = true; break;
      case "hoverOff": hovers = hovers.filter((g) => g !== a.group); endGroup(a.group); hoverDirty = true; break;
      case "capOn": startGroup(a.group); break;
      case "capOff": endGroup(a.group); break;
      case "tick":
        counts.ticks++;
        safe(onTick, { at: a.at, freq: a.tick.freq, velocity: a.tick.velocity, cue_id: a.group.cueId, source: a.group.source,
                       sound: a.tickHandle !== undefined && a.tickHandle !== null });
        break;
      default: break;
    }
  }

  // A tie (the transport's extend): move a strike's release to offAt, later or earlier. False when there is nothing
  // left to move: the note was dropped or has ended, or its release already went to a voice that cannot move it.
  function extendStrike(s, offAt) {
    if (s.dropped || s.done) return false;
    let a = s.off;
    if (a) {
      const i = queue.indexOf(a);
      if (i < 0) return false;
      queue.splice(i, 1);
      if (a.handed) {  // the release is already with the voice (inside the lookahead): the voice has to move it
        let moved = false;
        if (voice && typeof voice.extend === "function" && s.handle !== null) {
          try { moved = !!voice.extend(s.handle, { at: offAt }); } catch (e) { report(e); }
        }
        if (!moved) { insert(a); return false; }
        if (s.handle2 !== null) safe(() => voice.extend(s.handle2, { at: offAt }));
      } else {
        a.audioDone = !s.group.sound;
      }
    } else {  // held until clear: give it a release
      a = { rank: 0, kind: "off", strike: s, audioDone: !s.group.sound };
      s.off = a;
    }
    a.at = offAt;
    insert(a);
    return true;
  }

  // End every cue: its pending actions, its keys and sound, its hover and caption.
  function clearAll(reason) {
    counts.clears++;
    backlog = [];
    cancel(() => true, reason);
  }
  // End the cues whose arrival order `endsOrder(order)` accepts (clearAll: all of them; dropBacklog: backlog cues that
  // have not started; cancelCue: one at-cue, whose sounding notes fade over fadeMs).
  function cancel(endsOrder, reason, fadeMs = null) {
    const ended = (g) => endsOrder(g.order);
    const pending = [], kept = [];
    for (const a of queue) (ended(groupOf(a)) ? pending : kept).push(a);
    queue = kept;
    cancelTimer();
    const t = now();
    // sound already handed to the voice inside the lookahead, for a key that has not gone down: silence it
    for (const a of pending) {
      if (a.kind === "on" && !a.strike.down) releaseStrike(a.strike, t);
      else if (a.kind === "tick" && a.tickHandle !== undefined && a.tickHandle !== null && voice && typeof voice.stopTick === "function") {
        safe(() => voice.stopTick(a.tickHandle));
      }
    }
    for (const [midi, list] of [...held]) {
      const going = list.filter((s) => ended(s.group));
      if (!going.length) continue;
      for (const s of going) { releaseStrike(s, t, fadeMs); s.done = true; }
      const staying = list.filter((s) => !ended(s.group));
      if (staying.length) { held.set(midi, staying); continue; }  // a later cue still holds this key down
      held.delete(midi);
      counts.noteOffs++;
      safe(noteOff, midi, meta(list[list.length - 1].group, { at: t, reason }));
    }
    hovers = hovers.filter((g) => !ended(g));
    captions = captions.filter((g) => !ended(g));
    hoverDirty = captionDirty = false;
    emitHover(reason);
    emitCaption();
    arm();
  }

  function pump() {
    if (disposed || pumping) return;
    pumping = true;
    try {
      const t = now();
      const newest = dueNewest(t);
      if (voice) {
        for (const a of queue) {
          if (a.at - maxLook > t) break;
          if (a.audioDone || a.at - lookFor(a) > t) continue;
          if (tooLate(a, t, newest)) a.audioDone = true;  // not sounded: exec below drops it
          else doAudio(a);
        }
      }
      while (queue.length && queue[0].at <= t + EARLY_MS) {
        const a = queue.shift();
        if (tooLate(a, t, newest)) { dropLate(a, t); continue; }
        if (!a.audioDone) doAudio(a);
        exec(a, t);
      }
      // Hover and caption changes are reported once per pump, after every action due: a hover (or caption) that
      // hands over to the next at the same instant (a hover progression) never reports an empty moment in between.
      if (hoverDirty) { hoverDirty = false; emitHover(); }
      if (captionDirty) { captionDirty = false; emitCaption(); }
    } finally {
      pumping = false;
    }
    arm();
  }
  function cancelTimer() {
    if (timerId !== null) clock.clear(timerId);
    timerId = null;
    timerAt = Infinity;
  }
  function arm() {
    if (disposed) return;
    let wake = Infinity;
    for (const a of queue) {
      if (a.at - maxLook >= wake) break;
      wake = Math.min(wake, a.audioDone ? a.at - EARLY_MS : a.at - lookFor(a));
    }
    if (timerId !== null && wake === timerAt) return;
    cancelTimer();
    if (wake === Infinity) return;
    timerAt = wake;
    timerId = clock.set(() => { timerId = null; timerAt = Infinity; pump(); }, Math.max(0, wake - now()));
  }

  // Leaving the page: a page Daniel navigates away from can sit frozen in the back/forward cache with its queue intact,
  // and on return every step that fell due meanwhile would sound at once. On pagehide (and on the lifecycle freeze of a
  // background tab) the player clears as `clear` does, releasing its notes with reason "pagehide"; it does not resume.
  const onPageHide = () => { if (!disposed) { counts.pageHides++; anchor = null; clearAll("pagehide"); } };
  const lifeDoc = lifecycleTarget && lifecycleTarget.document && typeof lifecycleTarget.document.addEventListener === "function"
    ? lifecycleTarget.document : null;
  if (lifecycleTarget && typeof lifecycleTarget.addEventListener === "function") lifecycleTarget.addEventListener("pagehide", onPageHide);
  if (lifeDoc) lifeDoc.addEventListener("freeze", onPageHide);

  return {
    handle: handleCue,
    clear: () => { if (!disposed) { anchor = null; clearAll("clear"); } },
    pump,
    // Move the release of step stepIndex of at-cue `id` (every note of that step) to offAt (performance.now() ms).
    extend(id, stepIndex, offAt) {
      if (disposed || typeof offAt !== "number" || !Number.isFinite(offAt)) return false;
      const rec = tracked.get(id);
      if (!rec || rec.cancelled) return false;
      const strikes = rec.steps.get(stepIndex);
      if (!strikes || !strikes.length) return false;
      let ok = true;
      for (const s of strikes) ok = extendStrike(s, offAt) && ok;
      if (ok) counts.extended++;
      arm();
      return ok;
    },
    // End at-cue `id`: actions not started are removed, notes already sounding fade out over fadeMs.
    cancel(id, { fadeMs = CANCEL_FADE_MS } = {}) {
      if (disposed) return false;
      const rec = tracked.get(id);
      if (!rec || rec.cancelled) return false;
      rec.cancelled = true;
      counts.cancelled++;
      cancel((order) => order === rec.order, "cancel", fadeMs);
      return true;
    },
    // {id, strikes, dropped, ticks, pending, cancelled} for an at-cue still remembered, else null
    cueInfo(id) {
      const rec = tracked.get(id);
      if (!rec) return null;
      let pending = 0, strikes = 0;
      for (const a of queue) if (groupOf(a).order === rec.order) pending++;
      for (const list of rec.steps.values()) strikes += list.length;
      return { id, strikes, dropped: rec.dropped, ticks: rec.ticks, pending, cancelled: rec.cancelled };
    },
    get timer() { return clock.kind; },
    setBassDouble(on) { bassDoubleNow = !!on; return bassDoubleNow; },  // chords planned from now on
    get bassDouble() { return bassDoubleNow; },
    state: () => ({
      pending: queue.length,
      sounding: [...held.keys()].sort((a, b) => a - b),
      hovering: shownHover ? { notes: shownHover.notes.slice(), label: shownHover.label, detail: shownHover.detail } : null,
      caption: shownCaption ? { label: shownCaption.label, detail: shownCaption.detail, kind: shownCaption.kind,
                                source: shownCaption.source, under: underOf(shownUnder) } : null,
      timer: clock.kind, lateDropMs: lateLimit(), freshMs, ...counts,
      lateness: { n: late.n, mean_ms: late.n ? +(late.sum / late.n).toFixed(2) : null, max_ms: late.n ? +late.max.toFixed(2) : null },
    }),
    dispose() {
      if (disposed) return;
      clearAll("dispose");
      disposed = true;
      clock.dispose();
      if (lifecycleTarget && typeof lifecycleTarget.removeEventListener === "function") lifecycleTarget.removeEventListener("pagehide", onPageHide);
      if (lifeDoc) lifeDoc.removeEventListener("freeze", onPageHide);
    },
  };
}

// --------------------------------------------------------------------- voice --
// A soft felt/electric piano. Per strike: three detuned oscillators (a sine at 1x, a sine at 2x, a sawtooth at 1x; the
// last two fade faster and grow with velocity) through a lowpass whose cutoff opens with velocity and closes as the note
// rings, under a gain envelope with
// a 4 ms attack and an exponential decay of 2 s (C8) to 4 s (A0) to -60 dB. noteOff lets a short damper release take
// over. At most `polyphony` voices sound; a new strike past that steals the quietest one. All voices sum through a 2 dB
// trim into a gentle glue compressor (ratio 2, 20 ms attack), then a fast limiter that only catches peaks, then the
// master volume, so a dense chord never clips. The old ratio-8, 2 ms compressor pushed held notes down by up to 9.9 dB
// under a hard strike and pumped them back up over half a second; now 2.9 dB, back within 1 dB in 60 ms, and a medium
// strike 0.4 dB.
// The price is dynamic range given back: a lone mf note sits about 5 dB lower against full scale than before.
//
// Low lift: a slash bass under a spread voicing (Eb2 under Bb7sus4) is mostly fundamental, which a laptop or phone
// speaker cannot play (nothing much under 150 Hz), so the bass vanished. lowLift (0..1, default 1) gives notes below A3
// more 2nd and 3rd harmonic, and lets more of the tone through the lowpass as they ring, fading to nothing at A3: the
// ear hears the pitch from the harmonics even when the fundamental is gone. It is timbre only; no note is added.
//
// Autoplay: Chrome keeps an AudioContext suspended until the page has had a click or key press (MIDI from the KeyLab
// does not count). Until then status() is "needs a click", strikes are counted as silent (they are not queued: late
// music is worse than none), and the first pointerdown/keydown/touchend anywhere on the page unlocks it.
//
// Times: { at } is a performance.now() time in ms (mapped onto the audio clock through getOutputTimestamp, so the
// sound leaves the speakers at that moment); { time } is an AudioContext time in seconds (OfflineAudioContext).
// { synthOnly: true } sounds the built-in synth and never MIDI out (the player's bass octave).
// noteOn returns a handle for release(); noteOff(midi) releases every strike of that midi.
//
// One voice across tabs (exclusive, default on), decided per cue: see createTabArbiter. The player admits each cue as
// it arrives (admitCue(info) returns the cue's key) and passes the key with every strike ({ cue }). A strike another
// tab sounds returns null from noteOn (stats().yielded counts those); a strike without a cue key yields to whichever tab
// leads now. status() says "another tab" instead of "ready" while another tab would sound a new cue.
const ATTACK = 0.004;
const VOICE_LEVEL = 0.2;
// gain(v, lift): v is velocity 0..1, lift the note's low lift 0..1 (see createClaudeVoice); a partial at gain 0 is skipped
const PARTIALS = [
  { ratio: 1, cents: -3, type: "sine", gain: () => 1, fade: 0 },
  { ratio: 2, cents: 4, type: "sine", gain: (v, lift) => 0.18 + 0.22 * v + 0.5 * lift, fade: 0.45 },
  { ratio: 3, cents: -2, type: "sine", gain: (v, lift) => 0.3 * lift, fade: 0.6 },  // low lift only
  // A sawtooth a few cents off the fundamental. Its harmonics are what the velocity lowpass shapes (dull when soft, an
  // electric-piano bark when hard); sine partials alone left the filter nothing to cut (receipt 2026-09-14: a C4 at
  // velocity 120 was only 19% brighter than at 40). The detune against the sine beats as a slow chorus.
  { ratio: 1, cents: 5, type: "sawtooth", gain: (v) => 0.04 + 0.3 * v * v, fade: 0.3 },
];
const LIFT_TOP = 57;     // A3: low lift fades to nothing here
const LIFT_SPAN = 21;    // ...and is full at C2 and below
const clamp01 = (x) => Math.min(1, Math.max(0, Number.isFinite(+x) ? +x : 0));
// The bus dynamics (see above). trim_db is applied before them. `dynamics` overrides any of these (for measuring).
// Chosen from a sweep of seven settings (receipt scratchpad r3fix/dyn-sweep.json): a lower limiter threshold buys
// under 1 dB of headroom and ducks held notes 2 dB more.
export const VOICE_DYNAMICS = Object.freeze({
  trim_db: -2,
  glue: Object.freeze({ threshold: -16, knee: 16, ratio: 2, attack: 0.02, release: 0.35 }),
  limit: Object.freeze({ threshold: -3, knee: 0, ratio: 20, attack: 0.001, release: 0.12 }),
});

// ---------------------------------------------------------- one voice across tabs --
// Two /piano tabs (or /piano and the cue test page) both hear every cue. Both sounding doubles Claude's voice (the same
// strike twice, 2-3 ms apart, louder and comb-filtered) and sends Kontakt every note twice. So the voices agree over a
// BroadcastChannel which one sounds: of the tabs that can sound (enabled, and unlocked or with a MIDI out), the visible
// one, then the one Daniel clicked, typed in or focused last (a new tab counts as touched when it opens), then an
// arbitrary but agreed id. The others still draw keys and captions. Each tab posts its state when it opens, on a
// click, key or focus, on a visibility or readiness change and every 4 s, and says bye on pagehide, freeze and dispose
// (closing its channel while away, so the page stays eligible for the back/forward cache; hello again on pageshow and
// resume). A peer not heard for 12 s (65 s for a hidden one, whose timers the browser may hold back for a minute) is
// forgotten, so a tab that crashed without a bye silences the others for at most that long.
// Without BroadcastChannel every tab sounds, as before.
//
// Per cue, not per strike. The tab that sounds a cue must be one that has it. A tab that opens mid-progression, or comes
// back from the back/forward cache with its player cleared, never received that progression; when it took the voice at
// the next strike, the rest of the progression sounded nowhere (verifier receipt, round 6: 17 of 28 steps silent). So as
// a cue arrives each tab notes which tabs were there to receive it (itself and every peer it has heard: all of them
// listen to the same stream), and each strike of that cue sounds in the tab that ranks first, by the order above, among
// those tabs that are still here and can sound. A tab that joins mid-cue takes the voice from the next cue on; mid-cue
// the voice moves only between tabs that both have the cue (a click, a visibility change), and a tab that leaves
// mid-cue (bye, or forgotten) hands its strikes to the next such tab. A tab back from the cache or a freeze returns under
// a new id, so the cues it had before (cleared with its player) are not counted as its own. A local cue (no sent_at: a
// test page button, piano.js's local play) exists in one tab only and sounds there.
const TAB_BEAT_MS = 4000;
const TAB_CUE_MEMORY = 256;  // cues remembered per tab (their keys and who had them); a sequence may last 30 minutes
const TAB_FORGET_MS = Object.freeze({ visible: 12000, hidden: 65000 });
function createTabArbiter({ name, target, canSound, onChange, wallNow = () => Date.now() }) {
  const BC = globalThis.BroadcastChannel;
  if (typeof BC !== "function") return null;
  let ch = null;  // open while the page is here; closed while it is away (see leave)
  const doc = target && target.document && typeof target.document.addEventListener === "function" ? target.document : null;
  const newId = () => `${wallNow().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  let id = newId();         // renewed on the way back from away (see back)
  const peers = new Map();  // id -> { id, visible, activeAt, canSound, heardAt }
  const cues = new Map();   // cue key -> Set of the tab ids that were here when it arrived, this tab's own included
  let localSeq = 0;
  let activeAt = wallNow(), closed = false, away = false, lastCan = null;
  const visible = () => !doc || doc.visibilityState !== "hidden";
  const me = () => ({ id, visible: visible(), activeAt, canSound: !!canSound() });
  function post(type) {
    if (closed || !ch) return;
    const m = me();
    lastCan = m.canSound;
    try { ch.postMessage({ type, ...m }); } catch { /* the channel closed */ }
  }
  const outranks = (a, b) => (a.visible !== b.visible ? a.visible : a.activeAt !== b.activeAt ? a.activeAt > b.activeAt : a.id > b.id);
  function forget() {
    const t = wallNow();
    for (const [pid, p] of peers) if (t - p.heardAt > (p.visible ? TAB_FORGET_MS.visible : TAB_FORGET_MS.hidden)) peers.delete(pid);
  }
  // This tab sounds unless a peer that `counts` and can sound outranks it
  function leads(counts) {
    if (closed) return true;
    forget();
    const self = me();
    for (const [pid, p] of peers) if (counts(pid) && p.canSound && outranks(p, self)) return false;
    return true;
  }
  const leader = () => leads(() => true);  // for a new cue
  // A cue arriving: note the tabs here to receive it. Its key is "<id>@<sent_at>", the same in every tab.
  function admit(info) {
    const shared = !!info && info.id !== undefined && info.id !== null && typeof info.sent_at === "number" && Number.isFinite(info.sent_at);
    const key = shared ? `${info.id}@${info.sent_at}` : `local:${id}:${++localSeq}`;
    if (closed) return key;
    forget();
    cues.delete(key);
    cues.set(key, new Set(shared ? [id, ...peers.keys()] : [id]));
    while (cues.size > TAB_CUE_MEMORY) cues.delete(cues.keys().next().value);
    return key;
  }
  // For a strike of that cue: only the tabs that had it count
  function leaderFor(key) {
    const had = cues.get(key);
    return had ? leads((pid) => had.has(pid)) : leader();
  }
  let lastLeader = true;
  function changed() {
    const lead = leader();
    if (lead === lastLeader) return;
    lastLeader = lead;
    try { onChange(lead); } catch (e) { console.warn("[cues] voice tab change failed:", e); }
  }
  function onMessage(e) {
    const m = e.data;
    if (closed || !isObj(m) || typeof m.id !== "string" || m.id === id) return;
    if (m.type === "bye") peers.delete(m.id);
    else peers.set(m.id, { id: m.id, visible: !!m.visible, activeAt: Number(m.activeAt) || 0, canSound: !!m.canSound, heardAt: wallNow() });
    if (m.type === "hello" && !away) post("state");
    changed();
  }
  function open() {
    if (ch) return true;
    try { ch = new BC(name); } catch { ch = null; return false; }
    ch.onmessage = onMessage;
    if (typeof ch.unref === "function") ch.unref();  // (node: never keeps a test alive)
    return true;
  }
  function shut() {
    if (!ch) return;
    try { ch.onmessage = null; ch.close(); } catch { /* already closed */ }
    ch = null;
  }
  if (!open()) return null;
  const touch = () => { activeAt = wallNow(); if (!away) post("state"); changed(); };
  const onKey = (e) => { if (!e || !e.repeat) touch(); };
  const onVisibility = () => { if (visible()) activeAt = wallNow(); if (!away) post("state"); changed(); };
  // Away (pagehide, freeze): say bye and close the channel. Chrome keeps no page with a BroadcastChannel listener in the
  // back/forward cache (receipt A18: "BroadcastChannelOnMessage"), and a frozen page hears nothing anyway. Back
  // (pageshow, resume): reopen and say hello; the other tabs answer with their state.
  // Back from away under a new id: the player was cleared on the way out, so no cue from before is this tab's now.
  // (pageshow also fires on a first load, which was never away: that keeps its id.)
  const leave = () => { if (away || closed) return; post("bye"); away = true; shut(); peers.clear(); cues.clear(); };
  const back = () => { if (closed || !open()) return; if (away) { id = newId(); away = false; } post("hello"); changed(); };
  const offs = [];
  const listen = (t, type, fn, capture = false) => {
    if (!t || typeof t.addEventListener !== "function") return;
    t.addEventListener(type, fn, capture);
    offs.push(() => t.removeEventListener(type, fn, capture));
  };
  listen(target, "pointerdown", touch, true);
  listen(target, "keydown", onKey, true);
  listen(target, "focus", touch);
  listen(target, "pagehide", leave);
  listen(target, "pageshow", back);
  listen(doc, "visibilitychange", onVisibility);
  listen(doc, "freeze", leave);
  listen(doc, "resume", back);
  const beat = setInterval(() => { if (!away) post("state"); changed(); }, TAB_BEAT_MS);
  if (beat && typeof beat.unref === "function") beat.unref();
  post("hello");
  return {
    leader,
    admit,
    leaderFor,
    // readiness may have changed (unlock, a MIDI out, enabled): tell the other tabs
    update() { if (!closed && !away && !!canSound() !== lastCan) post("state"); changed(); },
    stats: () => ({ id, leader: leader(), visible: visible(), activeAt, away, cues: cues.size,
                    peers: [...peers.values()].map((p) => ({ id: p.id, visible: p.visible, canSound: p.canSound, activeAt: p.activeAt })) }),
    dispose() {
      if (closed) return;
      post("bye");
      closed = true;
      clearInterval(beat);
      for (const off of offs) off();
      shut();
    },
  };
}

// Jam additions (jam-spec 9.3, 9.5-9.7):
//   polyphony: setPolyphony(n) (24 by default; the transport raises it to 40 while a run sounds); voices over the new
//     limit are stolen only as new strikes need room.
//   timbre(name) / noteOn(..., {timbre}): "default" (today's voice), "keys" (the backing: the sawtooth partial x 0.6, a
//     lowpass of min(6000, f(2 + 7v^2) + 200 + 1200v^2), sine partials only below E2) or "click" (a short sine blip
//     for timing receipts).
//   tick({at|time, freq, velocity}): a 20 ms sine tick through the same bus; never MIDI. stopTick(handle).
//   setDuck(on) / duck(): with the duck on, each of Daniel's note-ons (duck()) takes the master gain to 0.7 (-3 dB)
//     over 80 ms, holds it until 1.2 s after his last note-on, then lets it back with a 0.6 s time constant.
//   The fitted clock: `at` (performance.now() ms) maps to the audio clock through a least-squares line over
//     (performanceTime, contextTime) pairs from getOutputTimestamp in the last 10 s, sampled on every sampleClock()
//     call (the transport's worker wake) and whenever a strike finds the last pair older than 250 ms. A pair more than
//     5 ms off the line starts the line again. outputLatency is not added. clock() describes it.
//   The bus dynamics (two DynamicsCompressorNodes) delay what they pass by their look-ahead; strikes and ticks are
//     scheduled that much earlier (DYNAMICS_DELAY_S), so the sound leaves the bus at `at`.
//   release(handle, {at, fadeMs}) fades linearly over fadeMs; extend(handle, {at}) moves a release not yet begun.
//   onSchedule(info) (receipts): {kind: "note"|"tick", midi, freq, velocity, at, mapped, time, cue_id, fit} for every
//     sound scheduled; mapped is `at` through the clock (seconds), time what was used (never before currentTime).
export function createClaudeVoice({
  context = null, output = null, polyphony = 24, volume = 0.7, enabled = true, internal = true, lowLift = 1,
  onStatus = () => {}, midiAccess = null, unlockTarget = typeof window !== "undefined" ? window : null, dynamics = null,
  exclusive = true, channel = "arsenal.piano.cueVoice", lifecycleTarget = typeof window !== "undefined" ? window : null,
  timbre = "default", onSchedule = null,
} = {}) {
  const dyn = { trim_db: dynamics?.trim_db ?? VOICE_DYNAMICS.trim_db, glue: { ...VOICE_DYNAMICS.glue, ...(dynamics?.glue || {}) },
                limit: { ...VOICE_DYNAMICS.limit, ...(dynamics?.limit || {}) } };
  const AC = globalThis.AudioContext || globalThis.webkitAudioContext;
  const offline = !!context && typeof OfflineAudioContext !== "undefined" && context instanceof OfflineAudioContext;
  let ctx = context, graph = null, status = "", armed = false, ownContext = !context;
  let enabledNow = !!enabled, internalNow = !!internal, volumeNow = clamp01(volume), liftNow = clamp01(lowLift);
  const clampPoly = (n) => Math.min(128, Math.max(1, Math.round(Number.isFinite(+n) ? +n : 24)));
  let polyNow = clampPoly(polyphony), timbreNow = TIMBRES.includes(timbre) ? timbre : "default";
  let duckOn = false;
  const voices = [];            // synth voices still sounding, oldest first
  const strikes = new Map();    // handle -> { midi, voice, midiOn }
  const tickVoices = new Map(); // tick handle -> { osc, env }
  let handleSeq = 0;
  const counts = { strikes: 0, silent: 0, stolen: 0, midiOn: 0, midiOff: 0, yielded: 0, ticks: 0, silentTicks: 0, extended: 0,
                   faded: 0, ducks: 0 };
  const midi = { access: midiAccess, pending: null, port: null, held: new Map(), warned: false };
  let arbiter = null;  // one voice across tabs (created at start, below)

  function computeStatus() {
    if (!ctx && !AC) return "unsupported";
    if (!enabledNow) return "off";
    if (offline) return "offline";
    if (!ctx) return "needs a click";
    if (ctx.state === "running") return arbiter && !arbiter.leader() ? "another tab" : "ready";
    if (ctx.state === "closed") return "closed";
    return "needs a click";
  }
  function refresh() {
    if (arbiter) arbiter.update();
    const next = computeStatus();
    if (next === "needs a click") arm();
    if (next === status) return;
    status = next;
    try { onStatus(next); } catch (e) { console.warn("[cues] voice onStatus failed:", e); }
  }

  function ensureContext(fromGesture) {
    if (ctx) return ctx;
    if (!AC) return null;
    const ua = typeof navigator !== "undefined" ? navigator.userActivation : null;
    if (!fromGesture && ua && !ua.hasBeenActive) return null;  // it would only start suspended and warn in the console
    ctx = new AC({ latencyHint: "interactive" });
    ownContext = true;
    ctx.addEventListener("statechange", refresh);
    return ctx;
  }
  function ensureGraph() {
    if (graph || !ctx) return graph;
    const bus = ctx.createGain();
    bus.gain.value = 10 ** (dyn.trim_db / 20);
    const setUp = (node, p) => { for (const k of ["threshold", "knee", "ratio", "attack", "release"]) node[k].value = p[k]; return node; };
    // glue: gentle, and slow enough to let a strike's attack through without ducking the notes already ringing
    const comp = setUp(ctx.createDynamicsCompressor(), dyn.glue);
    // safety: only the peaks of a dense, hard chord reach it
    const limit = setUp(ctx.createDynamicsCompressor(), dyn.limit);
    const master = ctx.createGain();
    master.gain.value = volumeNow * volumeNow;
    const duck = ctx.createGain();  // the jam duck (setDuck, duck): after the volume, so each keeps its own automation
    duck.gain.value = 1;
    bus.connect(comp).connect(limit).connect(master).connect(duck).connect(output || ctx.destination);
    graph = { bus, comp, limit, master, duck };
    return graph;
  }

  const GESTURES = ["pointerdown", "keydown", "touchend"];
  const onGesture = () => { unlock(); };
  function arm() {
    if (armed || !unlockTarget || offline) return;
    armed = true;
    for (const g of GESTURES) unlockTarget.addEventListener(g, onGesture, true);
  }
  function disarm() {
    if (!armed) return;
    armed = false;
    for (const g of GESTURES) unlockTarget.removeEventListener(g, onGesture, true);
  }
  async function unlock() {
    const c = ensureContext(true);
    if (c) {
      ensureGraph();
      if (c.state === "suspended" && !offline) { try { await c.resume(); } catch { /* still blocked */ } }
      if (c.state === "running") disarm();
    }
    refresh();
    return status;
  }

  // ------------------------------------------------------------------ the fitted clock (jam-spec 9.7)
  const CLOCK_WINDOW_MS = 10000;   // pairs older than this leave the line
  const CLOCK_RESEED_MS = 5;       // a pair this far off the line starts it again (a device change, a suspend)
  const CLOCK_MIN_SPAN_MS = 2000;  // under this span the slope is taken as 1 (only the offset is fitted)
  const CLOCK_STALE_MS = 250;      // a strike after this long without a pair samples one itself
  const fit = { pairs: [], n: 0, slope: 1, xm: 0, ym: 0, span: 0, residual: null, reseeds: 0, samples: 0, frozen: 0,
                lastSampleAt: -Infinity };
  function refit() {
    const p = fit.pairs, n = p.length;
    fit.n = n;
    if (!n) return;
    let sx = 0, sy = 0;
    for (const [x, y] of p) { sx += x; sy += y; }
    const xm = sx / n, ym = sy / n;
    fit.span = p[n - 1][0] - p[0][0];
    let slope = 1;
    if (n >= 3 && fit.span >= CLOCK_MIN_SPAN_MS) {
      let sxx = 0, sxy = 0;
      for (const [x, y] of p) { sxx += (x - xm) * (x - xm); sxy += (x - xm) * (y - ym); }
      if (sxx > 0) slope = sxy / sxx;
    }
    fit.slope = slope;
    fit.xm = xm;
    fit.ym = ym;
    let r = 0;
    for (const [x, y] of p) r = Math.max(r, Math.abs(ym + slope * (x - xm) - y));
    fit.residual = r;
  }
  const fitMs = (perf) => fit.ym + fit.slope * (perf - fit.xm);
  function sampleClock() {
    const c = ctx;
    fit.lastSampleAt = typeof performance !== "undefined" ? performance.now() : 0;
    if (!c || offline || c.state !== "running" || typeof c.getOutputTimestamp !== "function") return null;
    const ts = c.getOutputTimestamp();
    if (!ts || !(ts.performanceTime > 0)) return null;
    const x = ts.performanceTime, y = ts.contextTime * 1000;
    const last = fit.pairs[fit.pairs.length - 1];
    if (last && x <= last[0]) { fit.frozen++; return null; }
    fit.samples++;
    if (fit.n >= 2 && Math.abs(fitMs(x) - y) > CLOCK_RESEED_MS) { fit.pairs = []; fit.reseeds++; }
    fit.pairs.push([x, y]);
    while (fit.pairs.length > 1 && x - fit.pairs[0][0] > CLOCK_WINDOW_MS) fit.pairs.shift();
    refit();
    return [x, y];
  }
  // `at` (performance.now() ms) on the audio clock in seconds, before any floor; a context is required. A stale line
  // takes a new pair only at the start of a burst (no map in the last 20 ms), so a chord's notes all map through the
  // same line: a pair taken between them could move the line by a few ms and flam the chord.
  let lastMapAt = -Infinity;
  function mapAt(at) {
    const c = ctx;
    const tNow = performance.now();
    if (tNow - fit.lastSampleAt > CLOCK_STALE_MS && tNow - lastMapAt > 20) sampleClock();
    lastMapAt = tNow;
    if (fit.n > 0) return fitMs(at) / 1000;
    const ts = typeof c.getOutputTimestamp === "function" ? c.getOutputTimestamp() : null;
    if (ts && ts.performanceTime > 0) return ts.contextTime + (at - ts.performanceTime) / 1000;
    return c.currentTime + (at - performance.now()) / 1000;
  }
  // The context time to schedule at so the sound leaves the bus at `at` (or `time`): the dynamics' look-ahead earlier.
  function ctxTime({ at = null, time = null } = {}) {
    const c = ctx;
    if (time !== null && time !== undefined) return Math.max(time - DYNAMICS_DELAY_S, c.currentTime);
    if (at === null || at === undefined || offline) return c.currentTime;
    return Math.max(mapAt(at) - DYNAMICS_DELAY_S, c.currentTime);
  }

  function levelAt(v, t) {
    if (t <= v.t) return 0;
    let l = t < v.t + ATTACK ? v.peak * (t - v.t) / ATTACK : v.peak * Math.exp(-(t - v.t - ATTACK) / v.tau);
    if (t > v.releasedAt) l *= Math.exp(-(t - v.releasedAt) / v.relTau);
    return l;
  }
  function finish(v) {
    if (v.ended) return;
    v.ended = true;
    const i = voices.indexOf(v);
    if (i >= 0) voices.splice(i, 1);
    for (const o of v.oscs) o.disconnect();
    for (const g of v.gains) g.disconnect();
    v.lp.disconnect();
    v.env.disconnect();
    const s = strikes.get(v.handle);
    if (s && !s.midiOn) strikes.delete(v.handle);
  }
  function stopOscs(v, when) {
    const at = Math.min(when, v.stopAt);
    for (const o of v.oscs) { try { o.stop(at); } catch { /* already stopped */ } }
    v.stopAt = at;
  }
  function steal(t) {
    let victim = null, quietest = Infinity;
    for (const v of voices) {
      const l = levelAt(v, t + ATTACK * 2);  // concurrent strikes compare by their peak, older ones by what is left
      if (l < quietest) { quietest = l; victim = v; }
    }
    if (!victim) return;
    counts.stolen++;
    voices.splice(voices.indexOf(victim), 1);
    const at = Math.max(t, ctx.currentTime);
    const gain = victim.env.gain;
    if (typeof gain.cancelAndHoldAtTime === "function") gain.cancelAndHoldAtTime(at);
    else { gain.cancelScheduledValues(at); gain.setValueAtTime(levelAt(victim, at), at); }
    gain.linearRampToValueAtTime(0, at + 0.012);
    victim.releasedAt = Math.min(victim.releasedAt, at);
    stopOscs(victim, at + 0.02);
  }

  // The bus dynamics' look-ahead: each DynamicsCompressorNode delays what it passes by 6 ms, and the bus has two.
  const DYNAMICS_DELAY_S = 0.012;
  const KEYS_SINE_BELOW = 40;  // E2: the keys timbre plays sine partials only under it
  const KEYS_SAW_GAIN = 0.6;
  const CLICK_TAU = 0.012;     // the click timbre: one sine, gone in about 80 ms
  const CLICK_LEN = 0.12;
  function startVoice(m, vel, t, timbre = timbreNow) {
    while (voices.length >= polyNow) steal(t);
    const c = ctx, g = ensureGraph();
    const f = 440 * 2 ** ((m - 69) / 12);
    const v = vel / 127;
    const keys = timbre === "keys", click = timbre === "click";
    const low = Math.min(1, Math.max(0, (108 - m) / 87));  // 1 at A0, 0 at C8
    const lift = click ? 0 : liftNow * Math.min(1, Math.max(0, (LIFT_TOP - m) / LIFT_SPAN));  // 1 at C2 and below, 0 from A3 up
    const t60 = click ? CLICK_TAU * 6.91 : 2 + 2 * low;
    const tau = t60 / 6.91;
    const peak = VOICE_LEVEL * (0.06 + 0.94 * v ** 1.6);
    const env = c.createGain();
    env.gain.setValueAtTime(0, t);
    env.gain.linearRampToValueAtTime(peak, t + ATTACK);
    env.gain.setTargetAtTime(0, t + ATTACK, tau);
    const lp = c.createBiquadFilter();
    lp.type = "lowpass";
    lp.Q.value = 0.5;
    const bright = keys ? Math.min(6000, f * (2 + 7 * v * v) + 200 + 1200 * v * v)
      : Math.min(16000, f * (2 + 14 * v * v) + 200 + 3000 * v * v);
    const dull = click ? bright : Math.min(bright, f * (1.5 + 3 * lift) + 200);  // a lifted bass keeps harmonics a small speaker can play
    lp.frequency.setValueAtTime(bright, t);
    lp.frequency.setTargetAtTime(dull, t + ATTACK, tau * 1.2);
    lp.connect(env).connect(g.bus);
    const stopAt = click ? t + CLICK_LEN : t + t60 * 1.1 + 0.05;
    const oscs = [], gains = [];
    for (const p of PARTIALS) {
      if (click && (p.ratio !== 1 || p.type !== "sine")) continue;
      if (keys && p.type !== "sine" && m < KEYS_SINE_BELOW) continue;
      const level = p.gain(v, lift) * (keys && p.type === "sawtooth" ? KEYS_SAW_GAIN : 1);
      if (f * p.ratio > 14000 || level <= 0) continue;
      const o = c.createOscillator();
      o.type = p.type;
      o.frequency.value = f * p.ratio;
      o.detune.value = p.cents;
      const pg = c.createGain();
      pg.gain.setValueAtTime(level, t);
      if (p.fade) pg.gain.setTargetAtTime(0, t + ATTACK, tau * p.fade);
      o.connect(pg).connect(lp);
      o.start(t);
      o.stop(stopAt);
      oscs.push(o);
      gains.push(pg);
    }
    const voice = { m, t, peak, tau, relTau: 0.045 + 0.08 * low, releasedAt: Infinity, stopAt, naturalStop: stopAt, oscs,
                    gains, env, lp, timbre, ended: false, handle: null };
    oscs[0].onended = () => finish(voice);
    voices.push(voice);
    return voice;
  }
  // fadeS: a linear fade to silence over that many seconds (cancel), instead of the damper's release
  function releaseVoice(v, tr, fadeS = null) {
    if (v.ended || tr >= v.releasedAt) return;  // an earlier release already stands
    const gain = v.env.gain;
    if (tr <= v.t) {  // it has not started (cleared inside the lookahead): never let it sound
      gain.cancelScheduledValues(0);
      gain.setValueAtTime(0, ctx.currentTime);
      v.releasedAt = tr;
      stopOscs(v, Math.max(ctx.currentTime, v.t));
      return;
    }
    if (typeof gain.cancelAndHoldAtTime === "function") gain.cancelAndHoldAtTime(tr);
    else { gain.cancelScheduledValues(tr); gain.setValueAtTime(levelAt(v, tr), tr); }
    v.releasedAt = tr;
    if (fadeS !== null) {
      gain.linearRampToValueAtTime(0, tr + fadeS);
      stopOscs(v, tr + fadeS + 0.005);
      counts.faded++;
      return;
    }
    gain.setTargetAtTime(0, tr, v.relTau);
    stopOscs(v, tr + v.relTau * 9);  // about -78 dB
  }
  // A release already scheduled but not begun moves to tr (a tie extended after its release reached the voice).
  function extendVoice(v, tr) {
    if (v.ended || !ctx) return false;
    if (v.releasedAt !== Infinity) {
      if (ctx.currentTime >= v.releasedAt - 0.003) return false;  // already letting go
      v.env.gain.cancelScheduledValues(v.releasedAt);
      v.releasedAt = Infinity;
      for (const o of v.oscs) { try { o.stop(v.naturalStop); } catch { /* ended */ } }  // the last stop() call wins
      v.stopAt = v.naturalStop;
    }
    releaseVoice(v, tr);
    return true;
  }

  function midiSend(bytes, at) {
    const port = midi.port;
    if (!port) return;
    try {
      if (at !== null && at !== undefined && at > performance.now()) port.send(bytes, at); else port.send(bytes);
    } catch (e) {
      if (!midi.warned) { midi.warned = true; console.warn("[cues] MIDI out failed:", e && (e.message || e)); }
    }
  }
  function midiNoteOn(m, vel, at) {
    const n = midi.held.get(m) || 0;
    if (n > 0) midiSend([0x80, m, 0], at);  // restrike: the sampler hears a fresh note, and one note-off ends it later
    midiSend([0x90, m, vel], at);
    midi.held.set(m, n + 1);
    counts.midiOn++;
  }
  function midiNoteOff(m, at) {
    const n = midi.held.get(m) || 0;
    if (n <= 0) return;
    if (n > 1) { midi.held.set(m, n - 1); return; }
    midi.held.delete(m);
    midiSend([0x80, m, 0], at);
    counts.midiOff++;
  }

  function noteOn(m, velocity = 80, when = {}) {
    if (!enabledNow || !isInt(m) || m < 0 || m > 127) return null;
    // another tab sounds Claude's voice: this cue's (when.cue, the key admitCue gave), or a new cue's
    if (arbiter && !(when.cue != null ? arbiter.leaderFor(when.cue) : arbiter.leader())) { counts.yielded++; return null; }
    const vel = Math.min(127, Math.max(1, Math.round(velocity)));
    const handle = ++handleSeq;
    const strike = { midi: m, voice: null, midiOn: false };
    counts.strikes++;
    if (midi.port && when.time === undefined && !when.synthOnly) { midiNoteOn(m, vel, when.at); strike.midiOn = true; }
    if (internalNow) {
      if (ctx && (offline || ctx.state === "running")) {
        const t = ctxTime(when);
        const tb = typeof when.timbre === "string" && TIMBRES.includes(when.timbre) ? when.timbre : timbreNow;
        strike.voice = startVoice(m, vel, t, tb);
        strike.voice.handle = handle;
        if (onSchedule) scheduled("note", when, t, { midi: m, velocity: vel, timbre: tb });
      } else {
        counts.silent++;
        refresh();
      }
    }
    if (!strike.voice && !strike.midiOn) return null;  // nothing sounded (needs a click, or the synth is off)
    strikes.set(handle, strike);
    return handle;
  }
  function scheduled(kind, when, t, extra) {
    let mapped = null;
    try {
      if (when.time !== null && when.time !== undefined) mapped = when.time;
      else if (when.at !== null && when.at !== undefined && !offline) mapped = mapAt(when.at);
    } catch { mapped = null; }
    try {
      onSchedule({ kind, ...extra, at: when.at ?? null, mapped, time: t + DYNAMICS_DELAY_S, cue_id: when.cue_id ?? null,
                   fit: fit.n > 0 ? "fit" : "timestamp" });
    } catch { /* a receipt hook must never stop the music */ }
  }
  function release(handle, when = {}) {
    const s = strikes.get(handle);
    if (!s) return false;
    if (s.midiOn) { midiNoteOff(s.midi, when.at); s.midiOn = false; s.midiReleased = true; }
    if (s.voice && !s.voice.ended && ctx) {
      const fade = typeof when.fadeMs === "number" && Number.isFinite(when.fadeMs) && when.fadeMs >= 0 ? when.fadeMs / 1000 : null;
      releaseVoice(s.voice, ctxTime(when), fade);
    }
    if (!s.voice || s.voice.ended) strikes.delete(handle);
    return true;
  }
  // Move a release the voice already has (it has not begun): true when moved. A MIDI note-off already sent cannot move.
  function extend(handle, when = {}) {
    const s = strikes.get(handle);
    if (!s || s.midiReleased) return false;
    if (!s.voice) return !!s.midiOn;
    if (!extendVoice(s.voice, ctxTime(when))) return false;
    counts.extended++;
    return true;
  }

  // A count-in or ghost tick: a 20 ms sine through the bus (so volume and duck apply), never MIDI out.
  const TICK_S = TICK_MS / 1000;
  function tick({ at = null, time = null, freq = 1500, velocity = 60, cue = null, cue_id = null } = {}) {
    if (!enabledNow || !internalNow) { counts.silentTicks++; return null; }
    if (arbiter && !(cue != null ? arbiter.leaderFor(cue) : arbiter.leader())) { counts.yielded++; return null; }
    if (!ctx || !(offline || ctx.state === "running")) { counts.silentTicks++; refresh(); return null; }
    const g = ensureGraph();
    const when = { at, time, cue_id };
    const t = ctxTime(when);
    const f = Number.isFinite(+freq) && +freq > 0 ? +freq : 1500;
    const vel = Math.min(127, Math.max(1, Math.round(Number.isFinite(+velocity) ? +velocity : 60)));
    const v = vel / 127;
    const peak = VOICE_LEVEL * (0.06 + 0.94 * v ** 1.6);
    const osc = ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.value = f;
    const env = ctx.createGain();
    env.gain.setValueAtTime(0, t);
    env.gain.linearRampToValueAtTime(peak, t + 0.001);
    env.gain.setValueAtTime(peak, t + TICK_S - 0.004);
    env.gain.linearRampToValueAtTime(0, t + TICK_S);
    osc.connect(env).connect(g.bus);
    osc.start(t);
    osc.stop(t + TICK_S + 0.005);
    const handle = ++handleSeq;
    tickVoices.set(handle, { osc, env });
    osc.onended = () => { try { osc.disconnect(); env.disconnect(); } catch { /* gone */ } tickVoices.delete(handle); };
    counts.ticks++;
    if (onSchedule) scheduled("tick", when, t, { freq: f, velocity: vel });
    return handle;
  }
  function stopTick(handle) {
    const k = tickVoices.get(handle);
    if (!k || !ctx) return false;
    try {
      k.env.gain.cancelScheduledValues(0);
      k.env.gain.setValueAtTime(0, ctx.currentTime);
      k.osc.stop(ctx.currentTime + 0.005);
    } catch { /* already ended */ }
    return true;
  }

  // The duck (jam-spec 9.5): Loop and Try only, the transport turns it on while a run sounds.
  const DUCK_GAIN = 0.7, DUCK_ATTACK_S = 0.08, DUCK_HOLD_S = 1.2, DUCK_RELEASE_TAU = 0.6;
  function holdGain(param, at) {
    if (typeof param.cancelAndHoldAtTime === "function") param.cancelAndHoldAtTime(at);
    else { const v = param.value; param.cancelScheduledValues(at); param.setValueAtTime(v, at); }
  }
  function setDuck(on) {
    duckOn = !!on;
    if (!duckOn && graph && ctx) {
      const now = ctx.currentTime;
      holdGain(graph.duck.gain, now);
      graph.duck.gain.setTargetAtTime(1, now, DUCK_RELEASE_TAU);
    }
    return duckOn;
  }
  function duck() {
    if (!duckOn || !ctx) return false;
    const gr = ensureGraph();
    if (!gr) return false;
    const now = ctx.currentTime;
    holdGain(gr.duck.gain, now);
    gr.duck.gain.linearRampToValueAtTime(DUCK_GAIN, now + DUCK_ATTACK_S);
    gr.duck.gain.setTargetAtTime(1, now + DUCK_HOLD_S, DUCK_RELEASE_TAU);
    counts.ducks++;
    return true;
  }
  function noteOff(m, when = {}) {
    for (const [h, s] of [...strikes]) if (s.midi === m) release(h, when);
  }
  function allOff() {
    for (const h of [...strikes.keys()]) release(h, {});
    if (midi.port) {
      for (const m of midi.held.keys()) midiSend([0x80, m, 0]);
      midi.held.clear();
    }
  }

  async function getMidiAccess() {
    if (midi.access) return midi.access;
    if (!midi.pending) {
      if (typeof navigator === "undefined" || !navigator.requestMIDIAccess) throw new Error("Web MIDI is unavailable in this browser");
      midi.pending = navigator.requestMIDIAccess({ sysex: false }).then(
        (a) => { midi.access = a; return a; },
        (e) => { midi.pending = null; throw e; });
    }
    return midi.pending;
  }

  // start: a context handed in is used as it is; otherwise one is made now only if the page has had a gesture
  if (ctx) { if (!offline) ctx.addEventListener("statechange", refresh); ensureGraph(); } else if (ensureContext(false)) ensureGraph();
  if (exclusive && !offline) {
    const canSound = () => enabledNow && (!!midi.port || (internalNow && !!ctx && ctx.state === "running"));
    arbiter = createTabArbiter({ name: channel, target: lifecycleTarget, canSound, onChange: () => refresh() });
  }
  refresh();

  return {
    noteOn,
    release,
    noteOff,
    allOff,
    unlock,
    extend,
    tick,
    stopTick,
    setDuck,
    duck,
    get ducking() { return duckOn; },
    // the timbre for strikes that name none: "default", "keys" or "click"; returns the one in use
    timbre(name) {
      if (name !== undefined) { if (!TIMBRES.includes(name)) throw new Error(`timbre must be one of ${TIMBRES.join(", ")}`); timbreNow = name; }
      return timbreNow;
    },
    setPolyphony(n) { polyNow = clampPoly(n); return polyNow; },  // strikes from now on; nothing sounding is cut
    get polyphony() { return polyNow; },
    sampleClock,
    // the fitted clock: {mode: "fit" | "timestamp" | "none", pairs, slope, span_ms, residual_ms, reseeds, samples, frozen}
    clock: () => ({ mode: fit.n > 0 ? "fit" : ctx && !offline ? "timestamp" : "none", pairs: fit.n, slope: fit.slope,
                    span_ms: +fit.span.toFixed(3), residual_ms: fit.residual === null ? null : +fit.residual.toFixed(3),
                    reseeds: fit.reseeds, samples: fit.samples, frozen: fit.frozen, dynamics_delay_ms: DYNAMICS_DELAY_S * 1000 }),
    // `at` (performance.now() ms) on the audio clock (seconds): when a strike at `at` leaves the bus. null without a context.
    perfToContext: (at) => (ctx && !offline && Number.isFinite(at) ? mapAt(at) : null),
    admitCue: (info) => (arbiter ? arbiter.admit(info) : null),  // the player calls this as each cue arrives
    status: () => status,
    get context() { return ctx; },
    setVolume(v) {
      volumeNow = clamp01(v);
      if (graph) graph.master.gain.setTargetAtTime(volumeNow * volumeNow, ctx.currentTime, 0.03);
      return volumeNow;
    },
    get volume() { return volumeNow; },
    setEnabled(on) {
      enabledNow = !!on;
      if (!enabledNow) allOff();
      refresh();
      return enabledNow;
    },
    get enabled() { return enabledNow; },
    setInternal(on) { internalNow = !!on; refresh(); return internalNow; },  // false: MIDI out only (a Kontakt route)
    get internal() { return internalNow; },
    setLowLift(x) { liftNow = clamp01(x); return liftNow; },  // strikes from now on; ringing notes keep theirs
    get lowLift() { return liftNow; },
    async listMidiOutputs() {
      const a = await getMidiAccess();
      return [...a.outputs.values()].map((o) => ({ id: o.id, name: o.name || o.id, manufacturer: o.manufacturer || "", state: o.state }));
    },
    async setMidiOutput(portId) {
      if (midi.port) { for (const m of midi.held.keys()) midiSend([0x80, m, 0]); }
      midi.held.clear();
      midi.port = null;
      for (const s of strikes.values()) s.midiOn = false;
      if (portId === null || portId === undefined || portId === "") { refresh(); return null; }
      const a = await getMidiAccess();
      const port = a.outputs.get(portId);
      if (!port) { refresh(); throw new Error(`no MIDI output ${portId}`); }
      midi.port = port;
      refresh();
      return { id: port.id, name: port.name || port.id };
    },
    get midiOutput() { return midi.port ? { id: midi.port.id, name: midi.port.name || midi.port.id } : null; },
    stats: () => ({
      status, live: voices.length, polyphony: polyNow, timbre: timbreNow, duck: duckOn, ...counts,
      midiOut: midi.port ? midi.port.name || midi.port.id : null,
      tab: arbiter ? arbiter.stats() : null,
      context: ctx ? { state: ctx.state, sampleRate: ctx.sampleRate, baseLatency: ctx.baseLatency ?? null,
                       outputLatency: ctx.outputLatency ?? null } : null,
    }),
    dispose() {
      allOff();
      disarm();
      if (arbiter) { arbiter.dispose(); arbiter = null; }
      for (const k of tickVoices.values()) { try { k.osc.stop(); k.osc.disconnect(); k.env.disconnect(); } catch { /* ended */ } }
      tickVoices.clear();
      if (graph) {
        graph.bus.disconnect(); graph.comp.disconnect(); graph.limit.disconnect(); graph.master.disconnect(); graph.duck.disconnect();
        graph = null;
      }
      if (ctx && ownContext && !offline && ctx.state !== "closed") ctx.close().catch(() => {});
    },
  };
}
