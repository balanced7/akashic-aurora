// The KeyLab 88 mk3 in a web page: arsenal/web/lib/keylab-client.js (an ES module; no build step, no dependency but
// the house param schema next door).
//
// Two halves:
//
//   createKeyLabClient()  listens to the VJ engine (arsenal/keylab/vj.py, Server-Sent Events on
//                         http://127.0.0.1:8794/api/events) or, while the engine is not running, to BOTH KeyLab inputs
//                         over Web MIDI ("KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW"), and turns either into one
//                         normalised stream: fader 3 moved to 0.42, knob 2 turned 4 ticks, pad 7 hit at 0.8, the chord
//                         is Dbmaj7, the next beat lands in 240 ms. It only ever LISTENS: it sends nothing to the
//                         keyboard (no DAW connect or disconnect, no SysEx), so it is safe while FL Studio owns the
//                         connection. The one optional write is postPads(), which asks the ENGINE to colour the pads;
//                         the engine's governor keeps the rate legal.
//   createBinder()        drives a host page's parameters from that stream: learn-on-touch bindings, fader PICKUP (a
//                         fader takes over a parameter only once it passes the parameter's current value, so nothing
//                         jumps), relative knobs (no jumps, ever), smoothing, the "desk" layout (fader n drives the
//                         active shader's n-th parameter and knob n trims it), pads that switch scenes or recall and
//                         store snapshots, and the chord root on a hue parameter. Bindings, options and snapshots
//                         persist in localStorage (a convenience: everything works without it).
//
// The control numbers are Arturia's (read from their FL Studio script and the factory template; see
// research/reviewed/keylab-liberation-2026-10-22/keylab-full-surface-map-2026-10-23.md, rows F1-F3, N1-N3, D1-D3,
// T1-T12, C1). They are INFERRED until the morning census confirms them, so every CC is also learnable by touch, and
// the relative/absolute decision for a knob is learned from what it sends (the engine's rule, mirrored here for the
// Web MIDI path), never trusted blindly from the table.
//
//   import { createKeyLabClient, createBinder } from "/web/lib/keylab-client.js";
//   const kl = createKeyLabClient();                       // ?keylab=<url> on the page overrides the engine address
//   kl.on("control", (e) => ...);                          // {control: "fader3", kind: "abs", value: 0.42, ...}
//   kl.onBeat((b) => flash(b.bpm));  kl.onChord((c) => show(c.name));
//   const binder = createBinder(kl, host, { namespace: "shader-desk" });
//   kl.start();
//
// The host a binder drives:
//   { params(): [{ id, label, min = 0, max = 1, unit = "ratio", step, curve, role: "hue" | "master" | undefined }],
//     get(id) -> number, set(id, value, info),               // set is called every frame while a value glides
//     scenes?() -> [{ id, label, colour? }], scene?() -> id, selectScene?(id), pulse?(velocity) }
// A host that changes a value itself (a mouse on its own slider) calls binder.notifyExternal(id), so a fader that had
// caught that value lets go of it until it passes the new one.
import { formatValue, positionToValue, valueToPosition } from "./params.js";

export const KEYLAB_CLIENT_API = "arsenal.keylab-client/v1";
export const DEFAULT_EVENTS_URL = "http://127.0.0.1:8794/api/events";
export const STORAGE_PREFIX = "arsenal.keylab";

// ------------------------------------------------------------------------------------------------ the surface --
// Port "daw" = the DAW program (Prog + 6th screen button, FL Studio protocol); port "midi" = the Arturia / User
// programs (factory template numbers). INFERRED: the morning census turns these into receipts.
export const SURFACE = Object.freeze({
  daw: Object.freeze({
    faders: [105, 106, 107, 108, 109, 110, 111, 112, 113],          // F1, F2: absolute
    knobs: [91, 92, 94, 95, 96, 97, 102, 103, 104],                 // N1, N2: relative, 64 +- n
    faderTouch: [28, 29, 30, 31, 33, 34, 35, 36, 37],               // F3 (32 is skipped)
    knobTouch: [8, 9, 10, 11, 12, 13, 14, 15, 38],                  // N3
    dial: 116, dialClick: 117,                                      // D1, D2
    buttons: { 20: "stop", 21: "play", 22: "record", 23: "tap", 24: "loop", 25: "rewind", 26: "forward",
      27: "metronome", 40: "back", 41: "save", 42: "quantize", 43: "undo", 44: "redo",
      45: "screen1", 46: "screen2", 47: "screen3", 48: "screen4", 49: "screen5", 50: "screen6", 51: "screen7",
      52: "screen8" },
    wheels: { 1: "modwheel", 64: "sustain" },
  }),
  midi: Object.freeze({
    faders: [73, 75, 79, 72, 80, 81, 82, 83, 85],                   // F1, F2: absolute
    knobs: [74, 71, 76, 77, 93, 18, 19, 16, 17],                    // N1, N2: factory Global Mode = Absolute
    faderTouch: [], knobTouch: [],                                  // what touch sends in MIDI mode: UNKNOWN
    dial: 114, dialClick: 115,
    buttons: { 60: "screen5", 61: "screen6", 62: "screen7", 63: "screen8" },
    wheels: { 1: "modwheel", 11: "expression", 64: "sustain" },
  }),
});

// Pads: DAW port, channel 10, notes 0-11 = pads 1-12 (P1); the MIDI port's bank A, channel 10 (P3, protocol.PAD_NOTE).
export const PAD_NOTE = Object.freeze({ 1: 44, 2: 45, 3: 46, 4: 47, 5: 40, 6: 41, 7: 42, 8: 43, 9: 36, 10: 37, 11: 38, 12: 39 });
const NOTE_PAD = Object.fromEntries(Object.entries(PAD_NOTE).map(([pad, note]) => [note, Number(pad)]));
// The physical grid, 4 across x 3 down in reading order, rows top (farthest from the player) to bottom: a mirror of
// protocol.GRID, the one copy, and tests/test_keylab_w0.py pins this line equal to it. Daniel at the device, 2026-10-23:
// pad 1 is the top-left pad, the top row runs 1-4, then 5-8, and the bottom row is 9-12 (the 2026-10-22 grid was read
// from a photo turned sideways).
export const PAD_GRID = Object.freeze([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]);
export const PC_NAMES = Object.freeze(["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]);

function buildIndex(port) {
  const s = SURFACE[port];
  const idx = new Map();
  s.faders.forEach((cc, i) => idx.set(cc, { control: `fader${i + 1}`, role: "fader", prior: "abs" }));
  s.knobs.forEach((cc, i) => idx.set(cc, { control: `knob${i + 1}`, role: "knob", prior: port === "daw" ? "rel" : "abs" }));
  s.faderTouch.forEach((cc, i) => idx.set(cc, { control: `fader${i + 1}`, role: "touch" }));
  s.knobTouch.forEach((cc, i) => idx.set(cc, { control: `knob${i + 1}`, role: "touch" }));
  idx.set(s.dial, { control: "dial", role: "dial", prior: "rel" });
  idx.set(s.dialClick, { control: "dialClick", role: "button" });
  for (const [cc, name] of Object.entries(s.buttons)) idx.set(Number(cc), { control: name, role: "button" });
  for (const [cc, name] of Object.entries(s.wheels)) {
    if (idx.has(Number(cc))) continue;   // DAW CC 11 is knob 4's touch, not the expression pedal
    idx.set(Number(cc), { control: name, role: name === "sustain" ? "pedal" : "wheel", prior: "abs" });
  }
  return idx;
}
const INDEX = { daw: buildIndex("daw"), midi: buildIndex("midi") };

// What a CC on a port is. A port the event does not name is looked up DAW first (the engine's port-less events came
// from the DAW map), then MIDI. An unknown CC is still a control ("cc20.midi"), so it can be learned by touch.
export function resolveCC(port, cc) {
  const hit = port === "daw" || port === "midi" ? INDEX[port].get(cc) : (INDEX.daw.get(cc) || INDEX.midi.get(cc));
  if (hit) return { ...hit, port: port || null, cc };
  return { control: `cc${cc}${port ? "." + port : ""}`, role: "cc", prior: null, port: port || null, cc };
}

const CONTROL_WORDS = { dial: "Dial", dialClick: "Dial click", modwheel: "Mod wheel", pitch: "Pitch wheel",
  expression: "Expression", aftertouch: "Aftertouch", sustain: "Sustain", stop: "Stop", play: "Play",
  record: "Record", tap: "Tap", loop: "Loop", rewind: "Rewind", forward: "Fast forward", metronome: "Metronome",
  back: "Back", save: "Save", quantize: "Quantize", undo: "Undo", redo: "Redo" };
export function controlLabel(id) {
  if (typeof id !== "string") return "";
  if (CONTROL_WORDS[id]) return CONTROL_WORDS[id];
  let m = /^(fader|knob|screen|pad)(\d+)$/.exec(id);
  if (m) return `${m[1][0].toUpperCase()}${m[1].slice(1)} ${m[2]}`;
  m = /^cc(\d+)(?:\.(\w+))?$/.exec(id);
  if (m) return `CC ${m[1]}${m[2] ? " (" + m[2] + ")" : ""}`;
  return id;
}
export const controlShort = (id) => {
  const m = /^(fader|knob)(\d+)$/.exec(id || "");
  return m ? `${m[1] === "fader" ? "F" : "K"}${m[2]}` : controlLabel(id);
};

// ------------------------------------------------------------------------------------- absolute or relative --
// The engine's rule (vj.CCDecoder), so the Web MIDI path decides the same way: an encoder repeats a value near 64
// (absolute controls send only on change), an encoder turned back flips across 64, an absolute control wanders far
// from 64. The table's guess is a prior, held at +-4 until touch evidence moves it.
const PRIOR = 4, SCORE_CAP = 6;
export function createKindLearner() {
  const st = new Map();
  return {
    feed(key, prior, value, t) {
      let s = st.get(key);
      if (!s) { s = { score: prior === "rel" ? PRIOR : prior === "abs" ? -PRIOR : 0, last: null, t: -1e9 }; st.set(key, s); }
      const far = Math.abs(value - 64);
      let ev = 0;
      if (far > 24) ev -= 2;
      if (s.last !== null && t - s.t < 1000) {
        if (value === s.last && far > 0 && far <= 16) ev += 2;
        else if (far <= 16 && Math.abs(s.last - 64) <= 16 && (value - 64) * (s.last - 64) < 0 && Math.abs(value - s.last) >= 2) ev += 1;
      }
      s.score = Math.max(-SCORE_CAP, Math.min(SCORE_CAP, s.score + ev));
      const last = s.last;
      s.last = value; s.t = t;
      return { kind: s.score > 0 ? "rel" : "abs", last };
    },
    kindOf: (key) => { const s = st.get(key); return s ? (s.score > 0 ? "rel" : "abs") : null; },
  };
}

// ------------------------------------------------------------------------------------------- chord naming --
// The Web MIDI fallback's own small namer (the engine's naming, chordview + theory.analyze, is the real one; the
// piano page's reader is stronger still). Root first: the hue follows the root.
const TEMPLATES = [
  ["", [0, 4, 7]], ["m", [0, 3, 7]], ["dim", [0, 3, 6]], ["aug", [0, 4, 8]], ["sus2", [0, 2, 7]], ["sus4", [0, 5, 7]],
  ["7", [0, 4, 7, 10]], ["maj7", [0, 4, 7, 11]], ["m7", [0, 3, 7, 10]], ["m7b5", [0, 3, 6, 10]], ["dim7", [0, 3, 6, 9]],
  ["6", [0, 4, 7, 9]], ["m6", [0, 3, 7, 9]], ["add9", [0, 2, 4, 7]], ["9", [0, 2, 4, 7, 10]], ["maj9", [0, 2, 4, 7, 11]],
  ["m9", [0, 2, 3, 7, 10]], ["5", [0, 7]], ["mmaj7", [0, 3, 7, 11]], ["7sus4", [0, 5, 7, 10]],
];
export function nameChord(midis) {
  const notes = [...new Set((midis || []).filter(Number.isInteger))].sort((a, b) => a - b);
  if (notes.length < 2) return null;
  const pcs = [...new Set(notes.map((n) => ((n % 12) + 12) % 12))];
  const bass = ((notes[0] % 12) + 12) % 12;
  let best = null;
  for (const root of pcs) {
    const rel = new Set(pcs.map((p) => (p - root + 12) % 12));
    for (const [suffix, tones] of TEMPLATES) {
      const t = new Set(tones);
      const missing = tones.filter((x) => !rel.has(x));
      // a chord of four or more tones may drop its fifth (voicings do); nothing else may be missing
      if (missing.length > 1 || (missing.length === 1 && !(tones.length >= 4 && missing[0] === 7))) continue;
      let extra = 0;
      for (const x of rel) if (!t.has(x)) extra++;
      const hit = tones.length - missing.length;
      const score = hit * 2 - missing.length * 2.5 - extra * 1.5 + (root === bass ? 0.75 : 0) - tones.length * 0.01;
      if (!best || score > best.score) best = { root, suffix, score };
    }
  }
  if (!best) return null;
  const name = PC_NAMES[best.root] + best.suffix + (bass !== best.root ? "/" + PC_NAMES[bass] : "");
  return { name, root: best.root, quality: best.suffix || "maj", pcs: pcs.sort((a, b) => a - b) };
}

// The hue a root sits at: around the circle of fifths, so keys a fifth apart are neighbours in colour (the piano's
// palettes do the same). 0..1 of a turn; C = 0.
export const fifthsTurn = (root) => (((root * 7) % 12) + 12) % 12 / 12;

// ------------------------------------------------------------------------------------------------- helpers --
const isNum = (v) => typeof v === "number" && Number.isFinite(v);
const clamp = (x, a, b) => Math.min(Math.max(x, a), b);
function safeStorage(s) {
  if (s === null) return null;
  if (s) return s;
  try { return globalThis.localStorage || null; } catch { return null; }
}
function readJSON(storage, key) {
  if (!storage) return null;
  try { const raw = storage.getItem(key); return raw ? JSON.parse(raw) : null; } catch { return null; }
}
function writeJSON(storage, key, value) {
  if (!storage) return false;
  try { storage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
}
function queryParam(name) {
  try { return new URLSearchParams(globalThis.location?.search || "").get(name); } catch { return null; }
}
function emitter() {
  const subs = new Map();
  return {
    on(type, fn) {
      if (!subs.has(type)) subs.set(type, new Set());
      subs.get(type).add(fn);
      return () => subs.get(type)?.delete(fn);
    },
    emit(type, evt) {
      for (const key of [type, "*"]) {
        const set = subs.get(key);
        if (!set) continue;
        for (const fn of [...set]) {
          try { fn(evt); } catch (err) { try { console.error("[keylab]", err); } catch { /* no console */ } }
        }
      }
    },
  };
}

// ====================================================================================================================
// the client
// ====================================================================================================================
// opts: url, fallback ("auto" | "manual" | "off"), engine (false = Web MIDI only), EventSource, requestMIDIAccess,
// permissions, fetch, now, setTimeout, clearTimeout, connectTimeoutMs, dropGraceMs, retryMs, padDedupMs,
// chordSettleMs, inputFilter(name) -> bool.
export function createKeyLabClient(opts = {}) {
  const nav = globalThis.navigator;
  const q = queryParam("keylab");   // ?keylab=<events url>, or ?keylab=midi for Web MIDI only
  const env = {
    url: opts.url || (q && q !== "midi" ? q : DEFAULT_EVENTS_URL),
    EventSource: opts.EventSource !== undefined ? opts.EventSource : globalThis.EventSource,
    requestMIDIAccess: opts.requestMIDIAccess !== undefined ? opts.requestMIDIAccess
      : (nav && typeof nav.requestMIDIAccess === "function" ? nav.requestMIDIAccess.bind(nav) : null),
    permissions: opts.permissions !== undefined ? opts.permissions : (nav && nav.permissions) || null,
    fetch: opts.fetch || globalThis.fetch?.bind(globalThis),
    now: opts.now || (() => (globalThis.performance ? performance.now() : Date.now())),
    setTimeout: opts.setTimeout || ((fn, ms) => setTimeout(fn, ms)),
    clearTimeout: opts.clearTimeout || ((h) => clearTimeout(h)),
    fallback: opts.fallback || "auto",
    useEngine: opts.engine !== false && q !== "midi",
    connectTimeoutMs: opts.connectTimeoutMs ?? 1500,
    dropGraceMs: opts.dropGraceMs ?? 2500,
    retryMs: opts.retryMs ?? 8000,
    padDedupMs: opts.padDedupMs ?? 40,
    chordSettleMs: opts.chordSettleMs ?? 30,
    inputFilter: opts.inputFilter || null,
  };
  const bus = emitter();
  const status = {
    api: KEYLAB_CLIENT_API, source: "none", engine: env.useEngine ? "off" : "disabled", midi: "off", screen: "unknown",
    url: env.url, inputs: [], lastEventAt: null, hello: null, events: 0,
  };
  let es = null, connectTimer = null, dropTimer = null, retryTimer = null, started = false;
  let access = null, midiAttached = false;
  const learner = createKindLearner();
  let midiPending = false;
  const padSeen = new Map();    // pad -> { t, src } (a hit seen on both inputs within padDedupMs counts once)
  const keys = { held: new Set(), sustained: new Set(), pedal: false, timer: null, shown: null };

  const setStatus = (patch) => {
    Object.assign(status, patch);
    bus.emit("status", { type: "status", ...snapshotStatus() });
  };
  const snapshotStatus = () => ({ ...status, inputs: status.inputs.slice() });
  const setSource = (source, why) => {
    if (status.source === source) return;
    status.source = source;
    bus.emit("source", { type: "source", source, why: why || "", status: snapshotStatus() });
    bus.emit("status", { type: "status", ...snapshotStatus() });
  };
  const deliver = (evt) => {
    status.lastEventAt = env.now();
    status.events++;
    bus.emit(evt.type, evt);
  };

  // ---------------------------------------------------------------------------------------------- engine --
  function openEngine() {
    if (!env.useEngine || !env.EventSource || es) return;
    try {
      es = new env.EventSource(env.url);
    } catch (err) {
      setStatus({ engine: "down" });
      engineDown("the engine address could not be opened: " + (err && err.message ? err.message : err));
      return;
    }
    setStatus({ engine: "connecting" });
    env.clearTimeout(connectTimer);
    connectTimer = env.setTimeout(() => { if (status.engine !== "up") engineDown("no answer from the VJ engine"); }, env.connectTimeoutMs);
    es.onopen = () => engineUp();
    es.onmessage = (m) => {
      if (status.engine !== "up") engineUp();
      let evt;
      try { evt = JSON.parse(m.data); } catch { return; }
      feedEngine(evt);
    };
    es.onerror = () => {
      const closed = es && es.readyState === 2;   // EventSource.CLOSED: the browser gave up (HTTP error, CORS)
      if (status.engine === "up") {
        setStatus({ engine: "reconnecting" });
        env.clearTimeout(dropTimer);
        dropTimer = env.setTimeout(() => { if (status.engine !== "up") engineDown("the VJ engine went away"); }, env.dropGraceMs);
      }
      if (closed) {
        try { es.close(); } catch { /* already closed */ }
        es = null;
        if (status.engine !== "up") engineDown("the VJ engine refused the event stream");
        env.clearTimeout(retryTimer);
        retryTimer = env.setTimeout(() => { if (started) openEngine(); }, env.retryMs);
      }
    };
  }
  function engineUp() {
    env.clearTimeout(connectTimer); env.clearTimeout(dropTimer);
    setStatus({ engine: "up" });
    detachMidi();                 // one source at a time: the engine already reads both inputs
    setSource("engine", "the VJ engine is running");
  }
  function engineDown(why) {
    if (status.engine === "up") return;
    setStatus({ engine: env.useEngine ? "down" : "disabled" });
    // A browser's EventSource retries a refused connection every few seconds, and logs each refusal. Close it and ask
    // again every retryMs instead: the engine is still found when it starts, with a quiet console meanwhile.
    if (es && started) {
      try { es.close(); } catch { /* closed */ }
      es = null;
      env.clearTimeout(retryTimer);
      retryTimer = env.setTimeout(() => { if (started && !es) openEngine(); }, env.retryMs);
    }
    if (env.fallback === "off") { setSource("none", why); return; }
    if (access) { attachMidi(); return; }
    if (env.fallback === "manual") { setStatus({ midi: "needs-permission" }); setSource("none", why); return; }
    tryMidiSilently(why);
  }
  async function tryMidiSilently(why) {
    if (!env.requestMIDIAccess) { setStatus({ midi: "unavailable" }); setSource("none", why); return; }
    if (midiPending) return;
    midiPending = true;
    try {
      let state = "granted";
      if (env.permissions && typeof env.permissions.query === "function") {
        try { state = (await env.permissions.query({ name: "midi", sysex: false })).state; } catch { state = "prompt"; }
      }
      if (state === "granted") { await connectMidi(); return; }
      // Never pop a permission prompt nobody asked for: the page shows a button that calls connectMidi().
      setStatus({ midi: state === "denied" ? "denied" : "needs-permission" });
      setSource("none", why);
    } finally {
      midiPending = false;
    }
  }

  // The engine's event, normalised. Exported as feedEngine so a page that already holds the stream (or a test) can
  // hand events in.
  function feedEngine(evt) {
    if (!evt || typeof evt !== "object") return;
    const t = env.now();
    switch (evt.t) {
      case "hello": status.hello = { ...evt }; deliver({ type: "hello", ...evt, t }); return;
      case "status": deliver({ type: "engine-status", msg: String(evt.msg || ""), t }); return;
      case "beat": return scheduleBeat(evt, t);
      case "energy": deliver({ type: "energy", bass: +evt.bass || 0, mid: +evt.mid || 0, high: +evt.high || 0, level: +evt.level || 0, t }); return;
      case "hit": deliver({ type: "hit", strength: +evt.strength || 0, band: evt.band || "full", t }); return;
      case "chord": deliver({ type: "chord", name: evt.name, root: evt.root, quality: evt.quality, pcs: evt.pcs || [],
        src: evt.src || "keys", changed: evt.changed !== false, t }); return;
      case "note": deliver({ type: "note", key: evt.key, vel: +evt.vel || 0, on: !!evt.on, src: "engine", t }); return;
      case "pedal": deliver({ type: "pedal", on: !!evt.on, t }); return;
      case "pad": deliver({ type: "pad", pad: evt.pad, vel: +evt.vel || 0, on: !!evt.on, src: evt.src || "daw", t }); return;
      case "ctl": return engineCtl(evt, t);
      default: deliver({ type: "engine-other", evt, t });
    }
  }
  function engineCtl(evt, t) {
    const id = String(evt.id || "");
    const port = evt.port === "daw" || evt.port === "midi" ? evt.port : null;
    const value = isNum(evt.value) ? clamp(evt.value, 0, 1) : 0;
    const delta = isNum(evt.delta) ? Math.round(evt.delta) : 0;
    let m;
    if ((m = /^cc(\d+)$/.exec(id))) {
      const r = resolveCC(port, Number(m[1]));
      if (r.role === "touch") return deliver({ type: "touch", control: r.control, on: value >= 0.5, port, cc: r.cc, src: "engine", t });
      if (r.role === "button") return deliver({ type: "button", control: r.control, on: value >= 0.5, port, cc: r.cc, src: "engine", t });
      if (r.role === "pedal") return deliver({ type: "pedal", on: value >= 0.5, t });
      const kind = evt.kind === "rel" ? "rel" : "abs";
      return deliver({ type: "control", control: r.control, role: r.role, kind, value: kind === "abs" ? value : null,
        delta, raw: kind === "abs" ? Math.round(value * 127) : 64 + delta, port, ch: evt.ch ?? null, cc: r.cc, src: "engine", t });
    }
    if (id === "pb") return deliver({ type: "control", control: "pitch", role: "wheel", kind: "abs", value, delta, raw: null, port, ch: evt.ch ?? null, cc: null, src: "engine", t });
    if (id === "at") return deliver({ type: "control", control: "aftertouch", role: "wheel", kind: "abs", value, delta: 0, raw: null, port, ch: evt.ch ?? null, cc: null, src: "engine", t });
    if ((m = /^pad(\d+)_at$/.exec(id))) return deliver({ type: "pressure", pad: Number(m[1]), value, t });
    if ((m = /^note(\d+)$/.exec(id))) return deliver({ type: "button", control: id, on: value > 0, port, cc: null, src: "engine", t });
    deliver({ type: "engine-other", evt, t });
  }
  function scheduleBeat(evt, t) {
    const due = Math.max(0, isNum(evt.due_ms) ? evt.due_ms : 0);
    const beat = { type: "beat", bpm: +evt.bpm || 0, conf: +evt.conf || 0, n: evt.n ?? null, onBeat: evt.on_beat ?? null, at: t + due, t };
    deliver({ ...beat, type: "beat-ahead" });
    env.setTimeout(() => deliver({ ...beat, t: env.now() }), due);
  }

  // ---------------------------------------------------------------------------------------------- Web MIDI --
  async function connectMidi() {
    if (!env.requestMIDIAccess) { setStatus({ midi: "unavailable" }); return false; }
    try {
      access = access || await env.requestMIDIAccess({ sysex: false });
    } catch (err) {
      setStatus({ midi: "denied" });
      return false;
    }
    access.onstatechange = () => { if (midiAttached) attachMidi(true); };
    if (status.engine !== "up") attachMidi();
    else setStatus({ midi: "standby" });
    return true;
  }
  const portKind = (name) => (/\bdaw\b/i.test(name || "") ? "daw" : "midi");
  function midiInputs() {
    if (!access) return [];
    const all = [...access.inputs.values()].filter((i) => i.state !== "disconnected");
    const pick = env.inputFilter ? all.filter((i) => env.inputFilter(i.name || "")) : all.filter((i) => /keylab/i.test(i.name || ""));
    return pick.length || env.inputFilter ? pick : all;   // no KeyLab found: listen to whatever is there
  }
  function attachMidi(rescan) {
    if (!access) return;
    if (midiAttached && !rescan) return;
    detachMidi(true);
    const ins = midiInputs();
    for (const input of ins) {
      const kind = portKind(input.name);
      input.onmidimessage = (m) => feedMidi(kind, m.data, m.timeStamp);
    }
    midiAttached = true;
    setStatus({ midi: ins.length ? "open" : "no-inputs", inputs: ins.map((i) => i.name || "MIDI input") });
    if (status.engine !== "up") setSource(ins.length ? "webmidi" : "none", ins.length ? "Web MIDI" : "no MIDI inputs");
  }
  function detachMidi(quiet) {
    if (!access || !midiAttached) return;
    for (const input of access.inputs.values()) input.onmidimessage = null;
    midiAttached = false;
    if (!quiet) setStatus({ midi: "standby" });
  }

  // One raw MIDI message from a KeyLab input ("daw" or "midi"), normalised the way the engine normalises it.
  function feedMidi(kind, data, timeStamp) {
    if (!data || data.length < 2) return;
    const t = isNum(timeStamp) && timeStamp > 0 ? timeStamp : env.now();
    const hi = data[0] & 0xf0, ch = (data[0] & 0x0f) + 1, d1 = data[1], d2 = data.length > 2 ? data[2] : 0;
    const port = kind === "daw" ? "daw" : "midi";
    if (hi === 0x90 || hi === 0x80) {
      const on = hi === 0x90 && d2 > 0;
      if (ch === 10) {
        let pad = null, bank = null;
        if (port === "daw" && d1 >= 0 && d1 <= 11) { pad = d1 + 1; bank = "DAW"; }
        else if (port === "midi" && d1 >= 36 && d1 <= 83) { pad = NOTE_PAD[36 + ((d1 - 36) % 12)]; bank = "ABCD"[Math.floor((d1 - 36) / 12)]; }
        if (pad) return midiPad(pad, port, on ? d2 : 0, on, bank, t);
      }
      if (port === "midi") return midiKey(d1, on ? d2 : 0, on, t);
      return deliver({ type: "button", control: `note${d1}`, on, port, cc: null, src: "webmidi", t });
    }
    if (hi === 0xb0) {
      const r = resolveCC(port, d1);
      if (r.role === "pedal") return midiPedal(d2 >= 64, t);
      if (r.role === "touch") return deliver({ type: "touch", control: r.control, on: d2 >= 64, port, cc: d1, src: "webmidi", t });
      if (r.role === "button") return deliver({ type: "button", control: r.control, on: d2 >= 64, port, cc: d1, src: "webmidi", t });
      const key = `${port}:${ch}:${d1}`;
      const { kind: k, last } = learner.feed(key, r.prior, d2, t);
      if (k === "rel") {
        return deliver({ type: "control", control: r.control, role: r.role, kind: "rel", value: null, delta: d2 - 64, raw: d2, port, ch, cc: d1, src: "webmidi", t });
      }
      return deliver({ type: "control", control: r.control, role: r.role, kind: "abs", value: d2 / 127,
        delta: last === null ? 0 : d2 - last, raw: d2, port, ch, cc: d1, src: "webmidi", t });
    }
    if (hi === 0xe0) {
      const v14 = (d2 << 7) | d1;
      return deliver({ type: "control", control: "pitch", role: "wheel", kind: "abs", value: v14 / 16383, delta: 0, raw: null, port, ch, cc: null, src: "webmidi", t });
    }
    if (hi === 0xd0) return deliver({ type: "control", control: "aftertouch", role: "wheel", kind: "abs", value: d1 / 127, delta: 0, raw: null, port, ch, cc: null, src: "webmidi", t });
    if (hi === 0xa0 && ch === 10) {
      const pad = port === "daw" && d1 <= 11 ? d1 + 1 : NOTE_PAD[d1 >= 36 ? 36 + ((d1 - 36) % 12) : -1];
      if (pad) deliver({ type: "pressure", pad, value: d2 / 127, t });
    }
  }
  function midiPad(pad, src, vel, on, bank, t) {
    const prev = padSeen.get(pad);
    if (on) {
      if (prev && prev.on && prev.src !== src && t - prev.t < env.padDedupMs) return;   // the same hit, other input
      padSeen.set(pad, { t, src, on: true });
    } else if (prev && prev.src !== src) {
      return;   // the other input's release of a hit counted once already
    } else {
      padSeen.set(pad, { t, src, on: false });
    }
    deliver({ type: "pad", pad, vel: on ? vel / 127 : 0, on, src: src === "daw" ? "daw" : "bank", bank, t });
  }
  function midiKey(key, vel, on, t) {
    deliver({ type: "note", key, vel: vel / 127, on, src: "webmidi", t });
    if (on) { keys.held.add(key); keys.sustained.delete(key); }
    else { keys.held.delete(key); if (keys.pedal) keys.sustained.add(key); }
    keysChanged(t);
  }
  function midiPedal(on, t) {
    if (on === keys.pedal) return;
    keys.pedal = on;
    if (!on) keys.sustained.clear();
    deliver({ type: "pedal", on, t });
    if (!on) keysChanged(t);
  }
  function keysChanged() {
    env.clearTimeout(keys.timer);
    keys.timer = env.setTimeout(() => {
      const sounding = [...keys.held, ...keys.sustained];
      const c = nameChord(sounding);
      if (!c || c.name === keys.shown) return;
      keys.shown = c.name;
      deliver({ type: "chord", ...c, src: "keys", changed: true, t: env.now() });
    }, env.chordSettleMs);
  }

  // ------------------------------------------------------------------------------------------- the engine's screen --
  // Show a parameter on the KeyLab's own screen (the knob / fader screens, protocol.screen_param 28 / 29: a name, the
  // value as text and a 0-127 bar). The ENGINE draws it; this asks. PROPOSED CONTRACT, not in vj.py yet:
  //   POST /api/screen {"screen": "fader" | "knob", "name": "flow", "value": "42%", "level": 0..127, "color": [r, g, b]}
  // Latest wins, at most one request per 80 ms (the screen renders flicker-free at 60 ms spacing: surface map Y3).
  // An engine without the route answers 404 and the client stops asking for a minute.
  const scr = { pending: null, timer: null, lastAt: -1e9, offUntil: -1e9 };
  const ascii = (t, n = 32) => String(t ?? "").replace(/\u00b0/g, " deg").replace(/\u2192/g, "->").normalize("NFKD")
    .replace(/[^\x20-\x7e]/g, "").slice(0, n);
  function postScreen(payload) {
    if (status.engine !== "up" || !env.fetch || env.now() < scr.offUntil || !payload) return false;
    scr.pending = { screen: payload.screen === "knob" ? "knob" : "fader", name: ascii(payload.name), value: ascii(payload.value),
      level: Math.max(0, Math.min(127, Math.round(+payload.level || 0))),
      color: Array.isArray(payload.color) ? payload.color.slice(0, 3).map((c) => Math.max(0, Math.min(255, Math.round(+c || 0)))) : [0, 200, 160] };
    if (scr.timer) return true;
    scr.timer = env.setTimeout(flushScreen, Math.max(0, 80 - (env.now() - scr.lastAt)));
    return true;
  }
  async function flushScreen() {
    scr.timer = null;
    const body = scr.pending;
    scr.pending = null;
    if (!body) return;
    scr.lastAt = env.now();
    const base = env.url.replace(/\/api\/events.*$/, "");
    try {
      const r = await env.fetch(base + "/api/screen", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (r && (r.status === 404 || r.status === 405 || r.status === 501)) { scr.offUntil = env.now() + 60_000; setStatus({ screen: "unsupported" }); }
      else if (r && r.ok) setStatus({ screen: "ok" });
    } catch { /* the engine went away: the status machine handles that */ }
  }

  // ------------------------------------------------------------------------------------------- the engine's pads --
  // Ask the engine to colour the 12 DAW-bank pads ("#rrggbb" x 12). The engine paints through its governor; this
  // sends nothing to the keyboard itself, and refuses unless the engine is up.
  async function postPads(colors) {
    if (status.engine !== "up" || !env.fetch) return false;
    const base = env.url.replace(/\/api\/events.*$/, "");
    try {
      const r = await env.fetch(base + "/api/pads", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ colors: colors.slice(0, 12) }) });
      return !!(r && r.ok);
    } catch { return false; }
  }

  function start() {
    if (started) return api;
    started = true;
    if (env.useEngine && env.EventSource) openEngine();
    else engineDown(env.useEngine ? "this browser has no EventSource" : "the engine is switched off for this page");
    return api;
  }
  function stop() {
    started = false;
    env.clearTimeout(connectTimer); env.clearTimeout(dropTimer); env.clearTimeout(retryTimer); env.clearTimeout(keys.timer); env.clearTimeout(scr.timer);
    if (es) { try { es.close(); } catch { /* closed */ } es = null; }
    detachMidi(true);
    setStatus({ engine: env.useEngine ? "off" : "disabled", midi: access ? "standby" : "off" });
    setSource("none", "stopped");
  }

  const api = {
    api: KEYLAB_CLIENT_API,
    on: bus.on,
    onBeat: (fn) => bus.on("beat", fn),
    onChord: (fn) => bus.on("chord", fn),
    start, stop, connectMidi, feedEngine, feedMidi, postPads, postScreen,
    status: snapshotStatus,
    get source() { return status.source; },
  };
  return api;
}

// ====================================================================================================================
// the binder
// ====================================================================================================================
export const PICKUP_TOLERANCE = 0.02;     // a fader within 2 % of the value (about 2.5 of its 127 steps) has caught it
export const DEFAULT_OPTIONS = Object.freeze({ layout: "desk", chordHue: true, smoothMs: 80, lightPads: false, screen: false });

function descriptorOf(p) {
  const min = isNum(p.min) ? p.min : 0, max = isNum(p.max) && p.max > min ? p.max : min + 1;
  return { id: String(p.id), label: p.label || String(p.id), type: "range", unit: p.unit || "ratio",
    range: { min, max, step: isNum(p.step) ? p.step : null }, curve: p.curve || "linear", role: p.role || null,
    wrap: !!p.wrap || p.role === "hue", format: typeof p.format === "function" ? p.format : null, min, max };
}

// opts: namespace, storage (null = none), raf, now, setTimeout, clearTimeout, scenePads [1..8], snapshotPads
// [9..12], holdMs, relTicks, fineTicks, glideMs, chordGlideMs, options (defaults over DEFAULT_OPTIONS).
export function createBinder(client, host, opts = {}) {
  const ns = String(opts.namespace || "default");
  const storage = safeStorage(opts.storage);
  const KEY_BIND = `${STORAGE_PREFIX}.bindings.v1:${ns}`;
  const KEY_SNAP = `${STORAGE_PREFIX}.snapshots.v1:${ns}`;
  const KEY_OPTS = `${STORAGE_PREFIX}.options.v1:${ns}`;
  const now = opts.now || (() => (globalThis.performance ? performance.now() : Date.now()));
  const raf = opts.raf || (globalThis.requestAnimationFrame ? (fn) => requestAnimationFrame(fn) : (fn) => setTimeout(() => fn(now()), 16));
  const later = opts.setTimeout || ((fn, ms) => setTimeout(fn, ms));
  const cancel = opts.clearTimeout || ((h) => clearTimeout(h));
  const scenePads = opts.scenePads || [1, 2, 3, 4, 5, 6, 7, 8];
  const snapshotPads = opts.snapshotPads || [9, 10, 11, 12];
  const holdMs = opts.holdMs ?? 650;
  const relTicks = opts.relTicks ?? 128;       // a full sweep in this many encoder ticks (a learned knob)
  const fineTicks = opts.fineTicks ?? 384;     // the desk layout's knob: a fine trim of the fader's parameter
  const glideMs = opts.glideMs ?? 320;         // a snapshot recall glides this long
  const chordGlideMs = opts.chordGlideMs ?? 420;
  const bus = emitter();

  const stored = readJSON(storage, KEY_BIND);
  let learned = stored && stored.version === 1 && stored.bindings && typeof stored.bindings === "object" ? { ...stored.bindings } : {};
  const storedOpts = readJSON(storage, KEY_OPTS);
  const options = { ...DEFAULT_OPTIONS, ...(opts.options || {}), ...(storedOpts && typeof storedOpts === "object" ? storedOpts : {}) };
  let snapshots = readJSON(storage, KEY_SNAP) || {};
  if (typeof snapshots !== "object" || Array.isArray(snapshots)) snapshots = {};

  const ctl = new Map();        // control -> { lastPos, picked, param }
  const motion = new Map();     // param id -> { cur, target, tauMs, source }
  const holds = new Map();      // snapshot pad -> { timer, stored }
  let learning = null;
  let ticking = false, lastTick = 0;
  let readout = null;
  let unsubs = [];

  const params = () => {
    let list = [];
    try { list = (host.params ? host.params() : []) || []; } catch { list = []; }
    return list.filter((p) => p && p.id !== undefined).map(descriptorOf);
  };
  const paramById = (id, list = params()) => list.find((p) => p.id === id) || null;
  const hostGet = (p) => {
    let v;
    try { v = host.get ? host.get(p.id) : undefined; } catch { v = undefined; }
    return isNum(v) ? v : p.min;
  };
  const currentOf = (p) => (motion.has(p.id) ? motion.get(p.id).target : hostGet(p));
  const ctlState = (control) => {
    let s = ctl.get(control);
    if (!s) { s = { lastPos: null, picked: false, param: null }; ctl.set(control, s); }
    return s;
  };
  const textOf = (p, v) => {
    if (p.format) { try { return String(p.format(v)); } catch { /* fall through */ } }
    try { return formatValue({ type: "range", unit: p.unit, range: p.range }, v); } catch { return (+v).toFixed(2); }
  };
  const posOf = (p, v) => (p.wrap ? clamp((v - p.min) / (p.max - p.min), 0, 1) : valueToPosition({ range: p.range, curve: p.curve }, v));
  const valueAt = (p, pos) => (p.wrap ? p.min + (p.max - p.min) * pos : positionToValue({ range: p.range, curve: p.curve }, pos));

  // The binding a control has now: a learned one wins; otherwise the desk layout's positional one.
  function bindingFor(control, list = params()) {
    const lp = learned[control];
    if (lp !== undefined) {
      const p = paramById(lp, list);
      if (p) return { param: p, how: "learned" };
    }
    if (options.layout !== "desk") return null;
    const m = /^(fader|knob)(\d)$/.exec(control);
    if (!m) return null;
    const n = Number(m[2]);
    const primary = list.filter((p) => !p.role);
    let p = null;
    if (n <= 8) p = primary[n - 1] || null;
    else if (m[1] === "fader") p = list.find((x) => x.role === "master") || primary[8] || null;
    else p = list.find((x) => x.role === "hue") || primary[8] || null;
    return p ? { param: p, how: "desk", fine: m[1] === "knob" && n <= 8 } : null;
  }

  function emitReadout(r) {
    readout = { ...r, t: now() };
    bus.emit("readout", readout);
  }

  // ------------------------------------------------------------------------------------------- moving values --
  function setTarget(p, value, info = {}) {
    let v = p.wrap ? value : clamp(value, p.min, p.max);
    if (p.wrap) { const span = p.max - p.min; v = p.min + ((((v - p.min) % span) + span) % span); }
    const m = motion.get(p.id);
    const tauMs = info.tauMs ?? options.smoothMs;
    if (m) { m.target = v; m.tauMs = tauMs; m.source = info.source || null; }
    else motion.set(p.id, { cur: hostGet(p), target: v, tauMs, source: info.source || null, p });
    // Anything that moved this value from elsewhere lets go of the faders that held it.
    for (const [control, s] of ctl) if (s.param === p.id && control !== info.source) s.picked = false;
    kick();
    return v;
  }
  function kick() {
    if (ticking) return;
    ticking = true;
    lastTick = now();
    raf(tick);
  }
  function tick() {
    const t = now();
    const dt = Math.max(0, Math.min(250, t - lastTick));
    lastTick = t;
    for (const [id, m] of motion) {
      const p = m.p;
      const span = p.max - p.min;
      let diff = m.target - m.cur;
      if (p.wrap) { diff = ((diff % span) + span * 1.5) % span - span / 2; }
      let done = false;
      if (!(m.tauMs > 0) || Math.abs(diff) <= span * 5e-4) { m.cur = m.target; done = true; }   // 1/2000 of the range: far under one 7-bit step
      else m.cur += diff * (1 - Math.exp(-dt / m.tauMs));
      if (p.wrap && !done) m.cur = p.min + ((((m.cur - p.min) % span) + span) % span);
      try { host.set(id, m.cur, { smoothing: !done, source: m.source }); } catch (err) { try { console.error("[keylab] host.set", err); } catch { /* */ } }
      if (done) motion.delete(id);
    }
    if (motion.size) raf(tick); else ticking = false;
  }

  // ------------------------------------------------------------------------------------------- controls --
  function onControl(e) {
    const s = ctlState(e.control);
    if (learning) {
      finishLearn(e.control);
      if (e.kind === "abs") s.lastPos = e.value;
      return;
    }
    const list = params();
    const b = bindingFor(e.control, list);
    if (!b) {
      if (e.kind === "abs") s.lastPos = e.value;
      if (e.control === "dial") return dialScenes(e.delta);
      emitReadout({ control: e.control, controlLabel: controlLabel(e.control), param: null, label: "not bound",
        text: "", pos: e.kind === "abs" ? e.value : null, pending: null, how: null, source: "control" });
      return;
    }
    const p = b.param;
    if (s.param !== p.id) { s.param = p.id; s.picked = false; }
    if (e.kind === "abs") {
      const v = clamp(e.value, 0, 1);
      const want = posOf(p, currentOf(p));
      if (!s.picked) {
        const within = Math.abs(v - want) <= PICKUP_TOLERANCE;
        const crossed = s.lastPos !== null && (s.lastPos - want) * (v - want) <= 0;
        if (within || crossed) s.picked = true;
      }
      s.lastPos = v;
      if (!s.picked) {
        emitReadout({ control: e.control, controlLabel: controlLabel(e.control), param: p.id, label: p.label,
          value: currentOf(p), text: textOf(p, currentOf(p)), pos: want, how: b.how, source: "control",
          pending: { at: v, want, dir: v < want ? "up" : "down" } });
        return;
      }
      const value = setTarget(p, valueAt(p, v), { source: e.control });
      emitReadout({ control: e.control, controlLabel: controlLabel(e.control), param: p.id, label: p.label, value,
        text: textOf(p, value), pos: v, pending: null, how: b.how, source: "control" });
      return;
    }
    // relative: ticks move the position; a fine knob moves it less
    const ticks = b.fine ? fineTicks : relTicks;
    let pos = posOf(p, currentOf(p)) + (e.delta || 0) / ticks;
    pos = p.wrap ? ((pos % 1) + 1) % 1 : clamp(pos, 0, 1);
    const value = setTarget(p, valueAt(p, pos), { source: e.control });
    emitReadout({ control: e.control, controlLabel: controlLabel(e.control), param: p.id, label: p.label, value,
      text: textOf(p, value), pos: posOf(p, value), pending: null, how: b.how, source: "control", fine: !!b.fine });
  }
  function onTouch(e) {
    if (!e.on) return;
    if (learning) { finishLearn(e.control); return; }
    const b = bindingFor(e.control);
    if (!b) { emitReadout({ control: e.control, controlLabel: controlLabel(e.control), param: null, label: "not bound", text: "", pos: null, pending: null, how: null, source: "peek" }); return; }
    const p = b.param, v = currentOf(p);
    emitReadout({ control: e.control, controlLabel: controlLabel(e.control), param: p.id, label: p.label, value: v,
      text: textOf(p, v), pos: posOf(p, v), pending: null, how: b.how, source: "peek" });
  }
  function onButton(e) {
    if (!e.on) return;
    if (e.control === "forward") return stepScene(1);
    if (e.control === "rewind") return stepScene(-1);
  }

  // ------------------------------------------------------------------------------------------- scenes --
  const sceneList = () => { try { return (host.scenes ? host.scenes() : []) || []; } catch { return []; } };
  const sceneNow = () => { try { return host.scene ? host.scene() : null; } catch { return null; } };
  function selectScene(id, via) {
    if (!host.selectScene || id === undefined || id === null) return false;
    let ok = false;
    try { ok = host.selectScene(id) !== false; } catch { ok = false; }
    if (ok) {
      resync();
      bus.emit("scene", { id, via: via || null });
      const sc = sceneList().find((s) => s.id === id);
      emitReadout({ control: via || null, controlLabel: via ? controlLabel(via) : "", param: null, label: sc ? sc.label : String(id),
        text: "", pos: null, pending: null, how: null, source: "scene" });
    }
    return ok;
  }
  function stepScene(dir) {
    const list = sceneList();
    if (!list.length) return;
    const i = list.findIndex((s) => s.id === sceneNow());
    const next = list[(((i < 0 ? 0 : i + dir) % list.length) + list.length) % list.length];
    selectScene(next.id, dir > 0 ? "forward" : "rewind");
  }
  function dialScenes(delta) { if (delta) stepScene(delta > 0 ? 1 : -1); }

  // ------------------------------------------------------------------------------------------- pads --
  function onPad(e) {
    if (snapshotPads.includes(e.pad)) return snapshotPad(e);
    if (!e.on) return;
    const i = scenePads.indexOf(e.pad);
    if (i < 0) return;
    const sc = sceneList()[i];
    if (!sc) return;
    if (sc.id !== sceneNow()) selectScene(sc.id, `pad${e.pad}`);
    try { if (host.pulse) host.pulse(e.vel); } catch { /* optional */ }
  }
  function snapshotPad(e) {
    const slot = snapshotPads.indexOf(e.pad) + 1;
    const h = holds.get(e.pad);
    if (e.on) {
      if (h) cancel(h.timer);
      const rec = { stored: false, timer: null };
      rec.timer = later(() => { rec.stored = true; storeSnapshot(slot); }, holdMs);
      holds.set(e.pad, rec);
      return;
    }
    if (!h) return recallSnapshot(slot);   // a release without a press we saw: treat as a tap
    cancel(h.timer);
    holds.delete(e.pad);
    if (!h.stored) recallSnapshot(slot);
  }
  const sceneKey = () => String(sceneNow() ?? "_");
  function storeSnapshot(slot) {
    const list = params();
    const values = Object.fromEntries(list.map((p) => [p.id, currentOf(p)]));
    const key = sceneKey();
    snapshots[key] = { ...(snapshots[key] || {}), [slot]: { values, at: Date.now() } };
    writeJSON(storage, KEY_SNAP, snapshots);
    bus.emit("snapshot", { slot, action: "store", scene: key });
    emitReadout({ control: `pad${snapshotPads[slot - 1]}`, controlLabel: `Pad ${snapshotPads[slot - 1]}`, param: null,
      label: `Snapshot ${"ABCD"[slot - 1] || slot} stored`, text: "", pos: null, pending: null, how: null, source: "snapshot" });
    return values;
  }
  function recallSnapshot(slot) {
    const snap = snapshots[sceneKey()] && snapshots[sceneKey()][slot];
    if (!snap) {
      emitReadout({ control: `pad${snapshotPads[slot - 1]}`, controlLabel: `Pad ${snapshotPads[slot - 1]}`, param: null,
        label: `Snapshot ${"ABCD"[slot - 1] || slot} is empty: hold the pad to store one`, text: "", pos: null, pending: null, how: null, source: "snapshot" });
      return false;
    }
    const list = params();
    for (const p of list) if (isNum(snap.values[p.id])) setTarget(p, snap.values[p.id], { source: "snapshot", tauMs: glideMs });
    for (const s of ctl.values()) s.picked = false;
    bus.emit("snapshot", { slot, action: "recall", scene: sceneKey() });
    emitReadout({ control: `pad${snapshotPads[slot - 1]}`, controlLabel: `Pad ${snapshotPads[slot - 1]}`, param: null,
      label: `Snapshot ${"ABCD"[slot - 1] || slot}`, text: "recalled", pos: null, pending: null, how: null, source: "snapshot" });
    return true;
  }
  const hasSnapshot = (slot) => !!(snapshots[sceneKey()] && snapshots[sceneKey()][slot]);

  // ------------------------------------------------------------------------------------------- chords --
  function onChord(e) {
    if (!options.chordHue || !isNum(e.root)) return;
    const p = params().find((x) => x.role === "hue");
    if (!p) return;
    const value = setTarget(p, valueAt(p, fifthsTurn(e.root)), { source: "chord", tauMs: chordGlideMs });
    emitReadout({ control: null, controlLabel: "Chord", param: p.id, label: `${e.name || PC_NAMES[e.root]} → ${p.label}`,
      value, text: textOf(p, value), pos: posOf(p, value), pending: null, how: "chord", source: "chord" });
  }

  // ------------------------------------------------------------------------------------------- learn --
  function learn(paramId) {
    if (learning === paramId) { cancelLearn(); return false; }
    if (!paramById(paramId)) return false;
    learning = paramId;
    bus.emit("learn", { state: "armed", param: paramId });
    return true;
  }
  function cancelLearn() {
    if (!learning) return;
    const was = learning;
    learning = null;
    bus.emit("learn", { state: "cancelled", param: was });
  }
  function finishLearn(control) {
    const paramId = learning;
    learning = null;
    // One learned control per parameter and family: a fader and a knob may share a parameter (coarse and fine), two
    // faders may not (they would fight).
    const family = (c) => { const m = /^(fader|knob)/.exec(c); return m ? m[1] : "other"; };
    for (const [c, p] of Object.entries(learned)) if (p === paramId && c !== control && family(c) === family(control)) delete learned[c];
    learned[control] = paramId;
    const s = ctlState(control);
    s.param = paramId; s.picked = false;
    persistBindings();
    bus.emit("learn", { state: "bound", param: paramId, control });
    const p = paramById(paramId);
    if (p) emitReadout({ control, controlLabel: controlLabel(control), param: p.id, label: p.label, value: currentOf(p),
      text: textOf(p, currentOf(p)), pos: posOf(p, currentOf(p)), pending: null, how: "learned", source: "learn" });
  }
  function unbind(control) {
    if (!(control in learned)) return false;
    delete learned[control];
    persistBindings();
    return true;
  }
  function unbindParam(paramId) {
    let n = 0;
    for (const [c, p] of Object.entries(learned)) if (p === paramId) { delete learned[c]; n++; }
    if (n) persistBindings();
    return n;
  }
  function clearLearned() { learned = {}; persistBindings(); }
  function persistBindings() {
    writeJSON(storage, KEY_BIND, { version: 1, bindings: learned });
    bus.emit("bindings", describe());
  }
  function setOption(key, value) {
    if (!(key in DEFAULT_OPTIONS)) return false;
    options[key] = value;
    writeJSON(storage, KEY_OPTS, options);
    if (key === "layout") resync();
    bus.emit("options", { ...options });
    bus.emit("bindings", describe());
    return true;
  }

  // Every parameter and the controls that drive it now, for a map view.
  function describe() {
    const list = params();
    const controls = [...Array.from({ length: 9 }, (_, i) => `fader${i + 1}`), ...Array.from({ length: 9 }, (_, i) => `knob${i + 1}`),
      ...Object.keys(learned).filter((c) => !/^(fader|knob)\d$/.test(c))];
    const by = new Map(list.map((p) => [p.id, []]));
    for (const c of new Set(controls)) {
      const b = bindingFor(c, list);
      if (b && by.has(b.param.id)) by.get(b.param.id).push({ control: c, how: b.how, fine: !!b.fine, picked: !!(ctl.get(c) && ctl.get(c).picked) });
    }
    return {
      learning, options: { ...options },
      params: list.map((p) => ({ id: p.id, label: p.label, role: p.role, value: currentOf(p), text: textOf(p, currentOf(p)),
        pos: posOf(p, currentOf(p)), controls: by.get(p.id) })),
    };
  }

  // A scene change, a preset load or a layout switch: every fader must catch its value again.
  function resync() {
    for (const s of ctl.values()) { s.picked = false; s.param = null; }
    motion.clear();
    bus.emit("bindings", describe());
  }
  function notifyExternal(id) {
    motion.delete(id);
    for (const s of ctl.values()) if (s.param === id) s.picked = false;
  }

  unsubs = [
    client.on("control", onControl), client.on("touch", onTouch), client.on("button", onButton),
    client.on("pad", onPad), client.on("chord", onChord),
  ];

  return {
    on: bus.on, learn, cancelLearn, unbind, unbindParam, clearLearned, setOption, describe, resync, notifyExternal,
    storeSnapshot, recallSnapshot, hasSnapshot, selectScene, stepScene, bindingFor: (c) => {
      const b = bindingFor(c); return b ? { param: b.param.id, how: b.how, fine: !!b.fine } : null;
    },
    setValue: (id, value, info = {}) => { const p = paramById(id); return p ? setTarget(p, value, info) : null; },
    get learning() { return learning; },
    get readout() { return readout; },
    get options() { return { ...options }; },
    // The pad colours this binder would show: scene pads in their scene colour (the current one bright), snapshot
    // pads lit when they hold a snapshot. "#rrggbb" x 12, pad 1 first.
    padColors() {
      const list = sceneList(), cur = sceneNow();
      const out = Array.from({ length: 12 }, () => "#000000");
      scenePads.forEach((pad, i) => {
        const sc = list[i];
        if (!sc) return;
        const c = /^#[0-9a-f]{6}$/i.test(sc.colour || "") ? sc.colour : "#4a2a7a";
        out[pad - 1] = sc.id === cur ? c : dim(c, 0.18);
      });
      snapshotPads.forEach((pad, i) => { out[pad - 1] = hasSnapshot(i + 1) ? "#1030a0" : "#000000"; });
      return out;
    },
    destroy() { for (const u of unsubs) u(); unsubs = []; for (const h of holds.values()) cancel(h.timer); holds.clear(); },
  };
}

function dim(hex, k) {
  const n = parseInt(hex.slice(1), 16);
  const ch = (s) => Math.round(((n >> s) & 255) * k).toString(16).padStart(2, "0");
  return "#" + ch(16) + ch(8) + ch(0);
}
