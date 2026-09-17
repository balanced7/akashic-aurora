// Jam transport receipt (jam-spec 14, A1 and A3): Claude's band keeps time in an isolated, muted, headless Chrome.
//
//   node arsenal/lanes/jam_timing.mjs [--app http://127.0.0.1:8889 | --port 8889 --state <dir>] [--chrome-port 9871]
//                                     [--only a3,a1] [--short] [--out <dir>]
//
// With --app it uses a server that is already running; otherwise it starts `py -m arsenal serve --port <port>
// --performance-root <state>/performance` itself and stops only that one. Never 8793 (Daniel's). The page is
// /web/piano/transport-test.html with its onset probe (an AudioWorklet before the destination) and the click timbre.
// Runs are started, changed and stopped through the real jam routes; the page keeps time as the piano page will.
//
// A1 (5 minutes each unless --short): a 4-bar pulse loop, backing full, humanize 0.
//   run 72:  72 bpm, 90 bars, tempo 80 at bar 40, a fake 30 ms Date.now() step at bar 60
//   run 140: 140 bpm, 175 bars
//   run occluded: 100 bpm for 60 s with focus emulation off and the page in the background
//   (a) every handed event's `at` against the tempo map recomputed here from run.json (|d| <= 0.001 ms)
//   (b) note-on callback time minus planned time (p50 <= 8, p99 <= 16, max <= 33 ms, two 60 Hz frames; slope <= 0.2
//       ms/min; first 30 s minus last 30 s <= 1 ms). jam-rulings.md re-baselined (b) and (d): on Windows Chrome a
//       worker timer's message reaches the main thread p50 5-7 ms, p99 about 14 ms late, whatever the jam code does.
//   (c) onset sample frames from the probe against the planned time through the voice's fitted clock (p99 <= 2 ms,
//       slope <= 0.1 ms/min). Unchanged and binding: the re-baseline holds only while (c) passes.
//   (d) the occluded run: worker wake lateness p99 <= 20 ms, late_dropped 0
//   (e) the bar-40 downbeat at the formula +-0.5 ms, bars 41+ at the new length, an ack at version 2, effective_bar 40
//   (f) no bar line moves after the clock step (0.000 ms), and an ack reports offset_step_ms 30
// A3: count-ins at 60, 72, 140 bpm with 1 and 2 bars; 30 tempo changes and swaps at random times; a frame held 180 ms.
//
// GPU lock (arsenal/GPU-LOCK.md): it takes state/arsenal/gpu-render.lock through gpu_lock.mjs before it starts anything and
// holds it for the whole run (about 14 minutes, so it declares a 30-minute cap; 10 with --short). Render lanes also wait
// while this script runs, because its receipts are load-sensitive.
// Writes state/arsenal/receipts/jam/jam-timing-<date>/jam-timing-<stamp>.json and exits 1 if a check fails.
import { spawn, spawnSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { barOfRun, eventTimes } from "../web/piano/groove.js";
import { acquireGpuLock } from "./gpu_lock.mjs";
import { barMs, nextLine, segmentAt, tEpoch } from "../web/piano/tempomap.js";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
const { values: opt } = parseArgs({
  options: {
    app: { type: "string", default: "" },
    port: { type: "string", default: "8889" },  // jam-rulings: 8888 is Docker Desktop's; jam lanes default to 8889 or higher
    state: { type: "string", default: "" },
    "chrome-port": { type: "string", default: "9871" },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts", "jam") },
    only: { type: "string", default: "a3,a1" },
    short: { type: "boolean", default: false },
  },
});
const APP = opt.app || `http://127.0.0.1:${opt.port}`;
if (/:8793\b/.test(APP) || opt.port === "8793") {
  console.error("jam_timing: 8793 is Daniel's server; use a port of your own");
  process.exit(2);
}
const ONLY = new Set(opt.only.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean));
const SHORT = opt.short;
const now = new Date();
const stamp = now.toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const day = stamp.slice(0, 8);
const outDir = join(opt.out, `jam-timing-${day}`);
const jsonPath = join(outDir, `jam-timing-${stamp}.json`);
const profile = join(tmpdir(), `arsenal-jam-timing-${stamp}`);
mkdirSync(outDir, { recursive: true });

const KEY = "Eb major";
const LINE_A = "1maj7:4 | 4maj7:4 | 6m7:4 | 5:4";
const LINE_B = "6m7:4 | 2m7:4 | 5sus4:4 | 1maj9:4";
const PAGE = `p-jam7-timing-${stamp.replace("-", "")}`;

const report = {
  api: "arsenal.receipt/v0", lane: "J7", title: "Jam transport timing (A1, A3)", started_at: now.toISOString(),
  app: APP, chrome: null, page_id: PAGE, short: SHORT, only: [...ONLY],
  flags: ["--headless=new", "--mute-audio", "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
          "--disable-background-timer-throttling", "--autoplay-policy=no-user-gesture-required"],
  a1: {}, a3: {}, checks: {}, notes: [], console: [], exceptions: [], errors: [],
};
const check = (name, pass, detail) => {
  report.checks[name] = { pass: !!pass, ...detail };
  console.log(`${pass ? "PASS" : "FAIL"} ${name} ${JSON.stringify(detail)}`);
};

// ---------------------------------------------------------------------------------------------------------- maths
const round3 = (x) => (x === null || x === undefined || !Number.isFinite(x) ? x : Math.round(x * 1000) / 1000);
function stats(values) {
  const s = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!s.length) return { n: 0 };
  const q = (p) => s[Math.min(s.length - 1, Math.max(0, Math.ceil(p * s.length) - 1))];
  return { n: s.length, min: round3(s[0]), p50: round3(q(0.5)), p99: round3(q(0.99)), max: round3(s[s.length - 1]),
           mean: round3(s.reduce((a, b) => a + b, 0) / s.length), max_abs: round3(Math.max(...s.map(Math.abs))) };
}
// least-squares slope of y against x (both ms), in ms per minute
function slopePerMin(points) {
  const n = points.length;
  if (n < 3) return null;
  let sx = 0, sy = 0;
  for (const [x, y] of points) { sx += x; sy += y; }
  const xm = sx / n, ym = sy / n;
  let sxx = 0, sxy = 0;
  for (const [x, y] of points) { sxx += (x - xm) ** 2; sxy += (x - xm) * (y - ym); }
  return sxx > 0 ? round3((sxy / sxx) * 60000) : null;
}
function nearest(sorted, want, within) {
  let lo = 0, hi = sorted.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (sorted[mid] < want) lo = mid + 1; else hi = mid; }
  let best = null;
  for (const i of [lo - 1, lo]) {
    if (i >= 0 && i < sorted.length && Math.abs(sorted[i] - want) <= within && (best === null || Math.abs(sorted[i] - want) < Math.abs(best - want))) best = sorted[i];
  }
  return best;
}
const defsOf = (events) => {
  const defs = {};
  for (const e of events) if (e.def && Number.isInteger(e.version)) defs[e.version] = e.def;
  return defs;
};
const beatKey = (b) => Math.round(b * 1e6) / 1e6;

// ------------------------------------------------------------------------------------------------ processes, CDP
let server = null, gpu = null;
async function getJSON(url) { const r = await fetch(url, { cache: "no-store" }); return r.json(); }
async function postJSON(path, body) {
  const r = await fetch(`${APP}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await r.json().catch(() => null);
  if (!r.ok) { const e = new Error(`${path}: ${r.status} ${data && data.error}`); e.status = r.status; e.body = data; throw e; }
  return data;
}
async function waitFor(fn, ms, what) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    try { const v = await fn(); if (v) return v; } catch { /* not yet */ }
    await delay(200);
  }
  throw new Error(`timed out waiting for ${what}`);
}
function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map();
    const listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) rej(new Error(JSON.stringify(msg.error))); else res(msg.result);
      } else if (msg.method) for (const l of listeners) l(msg);
    };
    ws.onopen = () => resolve({
      send: (method, params = {}) => new Promise((res, rej) => { const id = nextId++; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); }),
      on: (fn) => listeners.push(fn),
      close: () => { try { ws.close(); } catch { /* closed */ } },
    });
    ws.onerror = () => reject(new Error(`websocket error on ${wsUrl}`));
  });
}

let browser = null, page = null, pageTarget = null, chrome = null;
async function evaluate(expression, timeoutMs = 120000) {
  let timer;
  const r = await Promise.race([
    page.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }),
    new Promise((_, rej) => { timer = setTimeout(() => rej(new Error(`no answer in ${timeoutMs} ms: ${expression.slice(0, 100)}`)), timeoutMs); }),
  ]).finally(() => clearTimeout(timer));
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
}
const waitWall = (epoch) => delay(Math.max(0, epoch - Date.now()));

// ------------------------------------------------------------------------------------------------ jam helpers
async function runDoc(runId) { return getJSON(`${APP}/api/piano/jam/runs/${runId}`); }
async function startLoop(body) {
  return evaluate(`__jamTest.start(${JSON.stringify({ mode: "loop", key: KEY, groove: "pulse", backing: "full", humanize: 0, seed: 7, walk: 1, ...body })})`);
}
// the time to send a change so that it lands on bar B: half a bar before the landing limit for B
function sendTimeFor(segments, m, B) {
  const s = segmentAt(segments, B - 1);
  return tEpoch(segments, m, B) - (60000 / s.bpm + 250) - barMs(s.bpm, m) / 2;
}
async function pageData(runId) {
  return evaluate(`(() => {
    const t = __jamTest, r = t.transport.records(), pre = ${JSON.stringify(`jam:${runId}:`)}, id = ${JSON.stringify(runId)};
    const mine = (x) => typeof x.cue === "string" && x.cue.startsWith(pre);
    return {
      plans: r.plans.filter((p) => p.run === id), regens: r.regens.filter((x) => x.run === id),
      acks: r.acks.filter((a) => a.run === id).map((a) => ({ t: a.t, body: a.body, error: a.error })),
      wakes: r.wakes.slice(), frames: r.frames.filter((f) => f.run === id), stops: r.stops.filter((s) => s.run === id),
      ons: t.T.ons.filter(mine), offs: t.T.offs.filter(mine), ticks: t.T.ticks.filter(mine),
      schedules: t.T.schedules.filter((s) => typeof s.cue_id === "string" && s.cue_id.startsWith(pre)),
      onsets: t.T.onsets.slice(), strip: t.T.strip.filter((s) => s.run === id || s.run === null), pairs: t.T.pairs.slice(),
      sampleRate: t.ctx.sampleRate, errors: t.T.errors.slice(), stats: t.stats(),
    };
  })()`, 180000);
}

// The plan of a run recomputed here: groove.js and the tempo map on run.json's final segments and settings.
function expectedPlan(run, events) {
  const defs = defsOf(events);
  const m = run.beats_per_bar;
  const cache = new Map();
  return (bar) => {
    if (cache.has(bar)) return cache.get(bar);
    const out = barOfRun({ beats_per_bar: m, segments: run.segments, settings: run.settings, mode: run.mode }, defs, bar);
    const map = new Map();
    for (const ev of eventTimes(run.segments, m, bar, out.events)) {
      const k = ev.voice === "tick" ? `${bar}|tick|${ev.freq}|${beatKey(ev.beat)}` : `${bar}|${ev.voice}|${ev.midi}|${ev.row}|${beatKey(ev.beat)}|${!!ev.carry}`;
      map.set(k, ev);
    }
    cache.set(bar, map);
    return map;
  };
}
// Only each bar's last hand counts (a bar handed again after a late frame replaces the first)
function finalPlans(plans) {
  const lastCue = new Map();
  for (const p of plans) if (p.kind !== "extend") lastCue.set(p.bar, p.cue);
  return plans.filter((p) => p.kind !== "extend" && lastCue.get(p.bar) === p.cue);
}
function planDeltas(plans, run, events) {
  const exp = expectedPlan(run, events);
  const out = [];
  let missing = 0;
  for (const p of finalPlans(plans)) {
    const k = p.kind === "tick" ? `${p.bar}|tick|${p.freq}|${beatKey(p.beat)}` : `${p.bar}|${p.voice}|${p.midi}|${p.row}|${beatKey(p.beat)}|${!!p.carry}`;
    const ev = exp(p.bar).get(k);
    if (!ev) { missing++; continue; }
    out.push({ bar: p.bar, kind: p.kind, voice: p.voice, beat: p.beat, row: p.row, d: p.at - (ev.epoch_ms - p.off), at: p.at, epoch: ev.epoch_ms, off: p.off });
  }
  return { deltas: out, missing };
}
// probe onsets against the times the voice scheduled (the planned `at` through its fitted clock)
function soundDeltas(d, tFrom = -Infinity, tTo = Infinity) {
  const sr = d.sampleRate;
  const onsetMs = d.onsets.map((f) => (f / sr) * 1000).sort((a, b) => a - b);
  // One planned instant (a chord, a tick) is one onset: its strikes' sound starts at the earliest of their mapped times.
  // flam_ms: how far apart the voice mapped strikes planned for the same instant (0 when a chord maps through one line).
  const groups = new Map();
  for (const s of d.schedules) {
    if (!(s.at >= tFrom && s.at <= tTo) || !Number.isFinite(s.mapped)) continue;
    const key = Math.round(s.at * 1000);
    const g = groups.get(key) || { at: s.at, kind: s.kind, lo: Infinity, hi: -Infinity, clamped: false };
    g.lo = Math.min(g.lo, s.mapped * 1000);
    g.hi = Math.max(g.hi, s.mapped * 1000);
    if (s.time > s.mapped + 1e-9) g.clamped = true;
    groups.set(key, g);
  }
  const rows = [];
  let unmatched = 0;
  for (const g of groups.values()) {
    const got = nearest(onsetMs, g.lo, 8);
    if (got === null) { unmatched++; continue; }
    rows.push({ at: g.at, kind: g.kind, d: got - g.lo, flam_ms: g.hi - g.lo, clamped: g.clamped });
  }
  return { rows, unmatched, onsets: onsetMs.length };
}

// ------------------------------------------------------------------------------------------------------- A3
async function a3Ticks() {
  const out = [];
  const combos = SHORT ? [[72, 1], [140, 2]] : [[60, 1], [60, 2], [72, 1], [72, 2], [140, 1], [140, 2]];
  for (const [bpm, countIn] of combos) {
    await evaluate("__jamTest.clear()");
    const reply = await startLoop({ chords: LINE_A, bpm, count_in: countIn });
    const m = 4, beat = 60000 / bpm;
    await waitWall(reply.bar0_epoch_ms + 2 * barMs(bpm, m) + 400);
    await evaluate(`__jamTest.stop("now")`);
    await delay(700);
    const d = await pageData(reply.run);
    const off = d.plans.length ? d.plans[0].off : null;
    const startPerf = reply.start_epoch_ms - off, bar0Perf = reply.bar0_epoch_ms - off;
    const tickPlans = finalPlans(d.plans).filter((p) => p.kind === "tick").sort((a, b) => a.at - b.at);
    const tickSched = d.schedules.filter((s) => s.kind === "tick").sort((a, b) => a.at - b.at);
    const sr = d.sampleRate;
    const onsetMs = d.onsets.map((f) => (f / sr) * 1000).sort((a, b) => a - b);
    const live = tickSched.map((s, k) => {
      const got = nearest(onsetMs, s.mapped * 1000, 8);
      return got === null ? null : round3(got - s.mapped * 1000 + (s.at - (startPerf + k * beat)));
    });
    let peaks = [];
    if (tickSched.length) {
      const events = tickSched.map((s) => ({ kind: "tick", time: 0.1 + (s.at - tickSched[0].at) / 1000, freq: s.freq, velocity: s.velocity }));
      const r = await evaluate(`__jamTest.renderOffline(${JSON.stringify({ events })}).then((x) => x.peaks)`);
      peaks = r.map((p, k) => ({ k, want: k % m === 0 ? 2000 : 1500, freq: p.want, peak: round3(p.peak) }));
    }
    const notePlans = finalPlans(d.plans).filter((p) => p.kind === "note");
    const bass0 = notePlans.find((p) => p.bar === 0 && p.voice === "bass" && Math.abs(p.beat) < 1e-6);
    const bassSched = bass0 ? d.schedules.find((s) => s.kind === "note" && s.midi === bass0.midi && Math.abs(s.at - bass0.at) < 0.01) : null;
    const bassGot = bassSched ? nearest(onsetMs, bassSched.mapped * 1000, 8) : null;
    const countdown = d.strip.filter((s) => ["1", "2", "3", "4"].includes(s.text)).sort((a, b) => a.t - b.t);
    const stripD = countdown.map((s, k) => (tickPlans[k] ? round3(s.t - tickPlans[k].at) : null));
    const row = {
      bpm, count_in: countIn, run: reply.run, ticks_planned: tickPlans.length, ticks_scheduled: tickSched.length,
      plan_vs_formula_ms: stats(tickPlans.map((p, k) => p.at - (startPerf + k * beat))),
      sound_vs_formula_ms: stats(live.filter((x) => x !== null)), sound_unmatched: live.filter((x) => x === null).length,
      tick_freqs: peaks,
      count_in_ms: bass0 && tickPlans.length ? round3(bass0.at - tickPlans[0].at) : null, count_in_want_ms: round3(countIn * barMs(bpm, m)),
      notes_before_bar0: notePlans.filter((p) => p.at < bar0Perf - 0.001).length + d.ons.filter((o) => o.at < bar0Perf - 0.001).length,
      bar0_plan_ms: bass0 ? round3(bass0.at - bar0Perf) : null,
      bar0_sound_ms: bassGot !== null && bassSched ? round3(bassGot - bassSched.mapped * 1000 + (bassSched.at - bar0Perf)) : null,
      strip_changes: countdown.map((s) => s.text).join(" "), strip_ms: stats(stripD.filter((x) => x !== null)),
      late_dropped: d.stats.transport.runs.find((r) => r.run === reply.run)?.late_dropped ?? null,
      errors: d.errors.slice(-5),
    };
    out.push(row);
    console.log("[a3 ticks]", JSON.stringify({ bpm, countIn, ticks: row.ticks_planned, sound: row.sound_vs_formula_ms, strip: row.strip_ms, bar0: row.bar0_sound_ms }));
  }
  report.a3.count_ins = out;
  const all = (fn) => out.length > 0 && out.every(fn);
  check("A3 ticks: exactly 4 x count_in", all((r) => r.ticks_planned === 4 * r.count_in && r.ticks_scheduled === 4 * r.count_in), { rows: out.map((r) => [r.bpm, r.count_in, r.ticks_planned, r.ticks_scheduled]) });
  check("A3 tick onsets within 2 ms of start + k beat", all((r) => r.sound_unmatched === 0 && r.sound_vs_formula_ms.n === 4 * r.count_in && r.sound_vs_formula_ms.max_abs <= 2 && r.plan_vs_formula_ms.max_abs <= 2),
        { worst_sound_ms: Math.max(...out.map((r) => r.sound_vs_formula_ms.max_abs ?? Infinity)), worst_plan_ms: Math.max(...out.map((r) => r.plan_vs_formula_ms.max_abs ?? Infinity)) });
  check("A3 tick pitch: bar downbeats 2 kHz, others 1.5 kHz (+-20 Hz, offline FFT)", all((r) => r.tick_freqs.length === 4 * r.count_in && r.tick_freqs.every((p) => p.freq === p.want && Math.abs(p.peak - p.want) <= 20)),
        { worst_hz: round3(Math.max(...out.flatMap((r) => r.tick_freqs.map((p) => Math.abs(p.peak - p.want))))) });
  check("A3 count-in length count_in x barMs +-1 ms", all((r) => r.count_in_ms !== null && Math.abs(r.count_in_ms - r.count_in_want_ms) <= 1), { rows: out.map((r) => [r.count_in_ms, r.count_in_want_ms]) });
  check("A3 silence before bar 0", all((r) => r.notes_before_bar0 === 0), { rows: out.map((r) => r.notes_before_bar0) });
  check("A3 bar 0 bass onset within 2 ms of bar0_epoch_ms", all((r) => r.bar0_plan_ms !== null && Math.abs(r.bar0_plan_ms) <= 2 && r.bar0_sound_ms !== null && Math.abs(r.bar0_sound_ms) <= 2),
        { rows: out.map((r) => [r.bar0_plan_ms, r.bar0_sound_ms]) });
  check("A3 strip countdown changes within 17 ms of each tick", all((r) => r.strip_ms.n === 4 * r.count_in && r.strip_ms.max_abs <= 17), { rows: out.map((r) => [r.strip_changes, r.strip_ms.max_abs]) });
}

async function a3Changes() {
  const n = SHORT ? 6 : 30;
  const m = 4;
  let bpm = 100;
  await evaluate("__jamTest.clear()");
  const first = await startLoop({ chords: LINE_A, bpm, count_in: 1 });
  let current = first.run;
  const runsSeen = [first.run];
  await waitWall(first.bar0_epoch_ms + barMs(bpm, m));
  const requests = [];
  for (let i = 0; i < n; i++) {
    await delay(2300 + Math.random() * 1400);
    const kind = i % 2 === 0 ? "tempo" : "swap";
    const sent = Date.now();
    try {
      if (kind === "tempo") {
        bpm = bpm >= 104 ? 96 : 104;
        const reply = await postJSON(`/api/piano/jam/runs/${current}/control`, { op: "tempo", bpm, at: "bar", by: "daniel" });
        requests.push({ i, kind, run: current, sent, reply });
      } else {
        const reply = await postJSON("/api/piano/jam/start", { mode: "loop", chords: i % 4 === 1 ? LINE_B : LINE_A, key: KEY, bpm,
          groove: "pulse", backing: "full", humanize: 0, seed: 7, walk: 1, page_id: PAGE, by: "daniel" });
        requests.push({ i, kind, run: reply.run, from: current, sent, reply });
        current = reply.run;
        runsSeen.push(reply.run);
      }
    } catch (e) {
      requests.push({ i, kind, run: current, sent, error: String(e.message || e) });
    }
  }
  await delay(4000);
  await evaluate(`__jamTest.stop("now")`);
  await delay(800);
  const docs = {};
  for (const id of runsSeen) docs[id] = await runDoc(id);
  const data = {};
  for (const id of runsSeen) data[id] = await pageData(id);
  const rows = [];
  for (const q of requests) {
    const row = { i: q.i, kind: q.kind, error: q.error ?? null };
    if (q.error) { rows.push(row); continue; }
    if (q.kind === "tempo") {
      const doc = docs[q.run];
      const line = doc.events.find((e) => e.kind === "change" && e.op === "tempo" && e.version === q.reply.version);
      const B = line.effective_bar;
      // the map the server landed this change on: the segments in effect at receipt (not the run's final segments, whose
      // filter from_bar < B is empty when the change lands on the run's first segment bar), clamped as runs.py clamps
      const before = segmentsAtLine(doc, line);
      const want = landing(before, m, line.recorded_epoch_ms, "tempo");
      const beat = 60000 / segmentAt(before, barAtEpoch(before, m, line.recorded_epoch_ms)).bpm;
      const d = data[q.run];
      const planned = finalPlans(d.plans).filter((p) => p.bar === B);
      const off = planned.length ? planned[0].off : null;
      Object.assign(row, {
        run: q.run, received: line.recorded_epoch_ms, bar: B, epoch_ms: line.epoch_ms, want_bar: want.bar, want_epoch_ms: want.epoch_ms,
        lead_ms: round3(line.epoch_ms - line.recorded_epoch_ms), need_ms: round3(beat + 250),
        page_version: planned.length ? Math.min(...planned.map((p) => p.v)) : null, version: line.version,
        page_bar_ms: planned.length ? round3(Math.min(...planned.filter((p) => Math.abs(p.beat) < 1e-6).map((p) => p.at + off)) - line.epoch_ms) : null,
      });
      row.pass = row.bar === row.want_bar && Math.abs(row.epoch_ms - row.want_epoch_ms) <= 0.001 && row.lead_ms >= row.need_ms - 0.001
        && row.page_version !== null && row.page_version >= row.version && row.page_bar_ms !== null && Math.abs(row.page_bar_ms) <= 0.001;
    } else {
      const old = docs[q.from], neu = docs[q.run];
      const stop = old.events.find((e) => e.kind === "stop" && e.reason === "replaced");
      const startLine = neu.events.find((e) => e.kind === "start");
      // the old run's segments when the server received the swap (the replaced stop line is written at receipt; a tempo
      // change requested earlier may start after the swap request arrived), clamped to its own first bar as runs.py does
      const oldSegs = stop ? segmentsAtLine(old, stop) : old.run.segments;
      const want = landing(oldSegs, m, startLine.recorded_epoch_ms, "swap");
      const beat = 60000 / segmentAt(oldSegs, barAtEpoch(oldSegs, m, startLine.recorded_epoch_ms)).bpm;
      const swapEpoch = neu.run.segments[0].epoch_ms;
      const od = data[q.from], nd = data[q.run];
      const offOld = od.plans.length ? od.plans[0].off : 0, offNew = nd.plans.length ? nd.plans[0].off : 0;
      const oldAfter = od.ons.filter((o) => o.at + offOld >= swapEpoch - 0.001).length
        + finalPlans(od.plans).filter((p) => p.kind === "note" && p.at + p.off >= swapEpoch - 0.001).length;
      const newBar0 = finalPlans(nd.plans).filter((p) => p.bar === 0 && p.kind === "note" && Math.abs(p.beat) < 1e-6);
      Object.assign(row, {
        run: q.run, from: q.from, received: startLine.recorded_epoch_ms, stop_bar: stop ? stop.stop_bar : null, epoch_ms: swapEpoch,
        want_bar: want.bar, want_epoch_ms: want.epoch_ms, lead_ms: round3(swapEpoch - startLine.recorded_epoch_ms), need_ms: round3(beat + 250),
        old_notes_after: oldAfter, new_bar0_ms: newBar0.length ? round3(Math.min(...newBar0.map((p) => p.at)) + offNew - swapEpoch) : null,
      });
      row.pass = stop && stop.stop_bar === want.bar && Math.abs(swapEpoch - want.epoch_ms) <= 0.001 && row.lead_ms >= row.need_ms - 0.001
        && oldAfter === 0 && row.new_bar0_ms !== null && Math.abs(row.new_bar0_ms) <= 0.001;
    }
    rows.push(row);
  }
  report.a3.changes = rows;
  const passed = rows.filter((r) => r.pass).length;
  check(`A3 ${n} tempo changes and swaps land on the first bar line >= 1 beat + 250 ms after receipt, and play there`, passed === n && rows.length === n,
        { passed, of: n, failed: rows.filter((r) => !r.pass).slice(0, 5) });
}
function barAtEpoch(segments, m, epoch) {
  // the bar sounding at epoch (tempomap barAt without importing it twice)
  let bar = segments[0].from_bar;
  while (tEpoch(segments, m, bar + 1) <= epoch) bar++;
  return bar;
}
// The segments in effect when the server wrote `line`: the last earlier event line that carried segments (the start
// line always does, as does every tempo or next change), else the run's final segments.
function segmentsAtLine(doc, line) {
  let segs = null;
  for (const e of doc.events) {
    if (e === line) break;
    if (Array.isArray(e.segments) && e.segments.length) segs = e.segments;
  }
  return segs || doc.run.segments;
}
// Where runs.py lands a change or a swap received at `received` on `segs`: the first bar line >= 1 beat + 250 ms away,
// never before the run's first segment bar (a swapped-in run not yet at its bar 0), and a tempo asked for during a
// count-in lands on bar 0 (runs.py control 533-539, _swap_line).
function landing(segs, m, received, kind) {
  const raw = nextLine(segs, m, received, "bar");
  let bar = Math.max(raw.bar, segs[0].from_bar);
  if (kind === "tempo" && bar < 0) bar = 0;
  return { bar, epoch_ms: bar === raw.bar ? raw.epoch_ms : tEpoch(segs, m, bar), raw_bar: raw.bar };
}

async function a3LateFrame() {
  const m = 4, bpm = 90;
  let result = null;
  for (let attempt = 0; attempt < 3 && !(result && result.landed); attempt++) {
    await evaluate("__jamTest.clear()");
    const reply = await startLoop({ chords: LINE_A, bpm, count_in: 1 });
    await waitWall(reply.bar0_epoch_ms + 2 * barMs(bpm, m));
    const doc = await runDoc(reply.run);
    const segs = doc.run.segments;
    const nowBar = barAtEpoch(segs, m, Date.now());
    const B = nowBar + 3;
    // 30 ms inside the landing limit: the change lands on B, and a frame held 180 ms still arrives ~50 ms after H(B)
    const sendAt = tEpoch(segs, m, B) - (60000 / bpm + 250) - 30;
    await evaluate(`__jamTest.delayNext(180, { op: "change", change: "tempo" })`);
    await waitWall(sendAt);
    const sent = Date.now();
    const ctl = await postJSON(`/api/piano/jam/runs/${reply.run}/control`, { op: "tempo", bpm: 84, at: "bar", by: "daniel" });
    await waitWall(tEpoch(segs, m, B) + 2 * barMs(84, m));
    await evaluate(`__jamTest.stop("now")`);
    await delay(800);
    const d = await pageData(reply.run);
    const doc2 = await runDoc(reply.run);
    const line = doc2.events.find((e) => e.kind === "change" && e.version === ctl.version);
    const regen = d.regens.find((r) => r.bars.includes(ctl.effective_bar));
    const oldCue = `jam:${reply.run}:${ctl.version - 1}:${ctl.effective_bar}`;
    const cancelT = regen ? regen.t : null;
    const oldOnsAfter = cancelT === null ? null : d.ons.filter((o) => o.cue === oldCue && o.t >= cancelT).length;
    const oldOnsAny = d.ons.filter((o) => o.cue === oldCue).length;
    const newCue = `jam:${reply.run}:${ctl.version}:${ctl.effective_bar}`;
    const acks = doc2.events.filter((e) => e.kind === "ack" && e.late_frame_ms !== undefined);
    result = {
      attempt, run: reply.run, bar: ctl.effective_bar, want_bar: B, landed: ctl.effective_bar === B, sent, received: line ? line.recorded_epoch_ms : null,
      regenerated: !!regen, late_frame_ms: regen ? regen.late_frame_ms : null, old_cue: oldCue, old_note_ons_after_cancel: oldOnsAfter,
      old_note_ons_total: oldOnsAny, new_note_ons: d.ons.filter((o) => o.cue === newCue).length,
      ack_late_frame_ms: acks.map((a) => a.late_frame_ms), frames: d.frames.filter((f) => f.op === "change").map((f) => ({ t: f.t, version: f.version })),
    };
    console.log("[a3 late frame]", JSON.stringify(result));
  }
  report.a3.late_frame = result;
  check("A3 a frame held 180 ms: the bar is regenerated, 0 old note-ons after the cancel, the ack carries late_frame_ms",
        result && result.landed && result.regenerated && result.late_frame_ms > 0 && result.old_note_ons_after_cancel === 0 && result.new_note_ons > 0 && result.ack_late_frame_ms.length > 0,
        { result });
}

// ------------------------------------------------------------------------------------------------------- A1
async function a1Run({ name, bpm, bars, tempoAt = null, tempoTo = null, stepAt = null, hide = false }) {
  const m = 4;
  await evaluate("__jamTest.clear()");
  await evaluate("__jamTest.step(0)");
  const hidden = hide ? await hidePage() : null;
  const reply = await startLoop({ chords: LINE_A, bpm, count_in: 1 });
  const run = reply.run;
  let doc = await runDoc(run);
  let tempoReply = null, stepDone = null;
  if (tempoAt !== null) {
    await waitWall(sendTimeFor(doc.run.segments, m, tempoAt));
    tempoReply = await postJSON(`/api/piano/jam/runs/${run}/control`, { op: "tempo", bpm: tempoTo, at: "bar", by: "daniel" });
    doc = await runDoc(run);
  }
  if (stepAt !== null) {
    await waitWall(tEpoch(doc.run.segments, m, stepAt) - 200);
    await evaluate("__jamTest.step(30)");
    stepDone = { bar: stepAt, epoch: Date.now() };
  }
  await waitWall(sendTimeFor(doc.run.segments, m, bars));
  const stopReply = await postJSON(`/api/piano/jam/runs/${run}/control`, { op: "stop", at: "bar", by: "daniel" });
  await waitWall(stopReply.epoch_ms + 1500);
  if (hide) await showPage();
  await evaluate("__jamTest.step(0)");
  const d = await pageData(run);
  doc = await runDoc(run);
  const off = d.plans.length ? d.plans[0].off : null;
  const startPerf = reply.start_epoch_ms - off, stopPerf = stopReply.epoch_ms - off;

  const { deltas, missing } = planDeltas(d.plans, doc.run, doc.events);
  const ons = d.ons.filter((o) => o.sound !== false);
  const cb = ons.map((o) => o.t - o.at);
  const cbPoints = ons.map((o) => [o.t, o.t - o.at]);
  const firstT = ons.length ? ons[0].t : 0, lastT = ons.length ? ons[ons.length - 1].t : 0;
  const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
  const first30 = mean(ons.filter((o) => o.t - firstT <= 30000).map((o) => o.t - o.at));
  const last30 = mean(ons.filter((o) => lastT - o.t <= 30000).map((o) => o.t - o.at));
  const snd = soundDeltas(d, startPerf - 5, stopPerf + 5);
  const wakes = d.wakes.filter((w) => w.t >= startPerf - 5000 && w.t <= stopPerf + 100).map((w) => w.t - w.planned);
  const lastAck = [...doc.events].reverse().find((e) => e.kind === "ack");
  const row = {
    name, run, bpm, bars, hidden, start_epoch_ms: reply.start_epoch_ms, stop_bar: stopReply.effective_bar,
    plan: { n: deltas.length, missing, delta_ms: stats(deltas.map((x) => x.d)) },
    callback: { ...stats(cb), slope_ms_per_min: slopePerMin(cbPoints), first30_minus_last30_ms: first30 !== null && last30 !== null ? round3(first30 - last30) : null },
    sound: { ...stats(snd.rows.map((r) => r.d)), unmatched: snd.unmatched, clamped: snd.rows.filter((r) => r.clamped).length,
             flam_ms: stats(snd.rows.map((r) => r.flam_ms)),
             slope_ms_per_min: slopePerMin(snd.rows.map((r) => [r.at, r.d])), onsets_detected: snd.onsets },
    wake_late_ms: stats(wakes),
    late_dropped: { page: d.stats.transport.runs.find((r) => r.run === run)?.late_dropped ?? null, last_ack: lastAck ? lastAck.late_dropped : null },
    timer: d.stats.transport.timer, player_timer: d.stats.player.timer, clock: d.stats.transport.clock,
    visibility_end: d.stats.visibility, errors: d.errors.slice(-5),
  };
  if (tempoAt !== null) {
    const B = tempoReply.effective_bar;
    const tempoLine = doc.events.find((e) => e.kind === "change" && e.op === "tempo" && e.version === tempoReply.version);
    const before = tempoLine ? segmentsAtLine(doc, tempoLine) : doc.run.segments;  // the map bar B's downbeat was placed on
    const downs = finalPlans(d.plans).filter((p) => p.kind === "note" && p.voice === "bass" && Math.abs(p.beat) < 1e-6 && p.row === "bass");
    const down = (bar) => downs.find((p) => p.bar === bar);
    const lengths = [];
    for (let b = B; b < bars - 1; b++) if (down(b) && down(b + 1)) lengths.push(down(b + 1).at - down(b).at - barMs(tempoTo, m));
    const ack = doc.events.find((e) => e.kind === "ack" && e.version === tempoReply.version && e.effective_bar === B);
    row.tempo = { effective_bar: B, want_bar: tempoAt, version: tempoReply.version,
                  downbeat_vs_formula_ms: down(B) ? round3(down(B).at + off - tEpoch(before, m, B)) : null,
                  new_bar_length_delta_ms: stats(lengths), ack: ack ? { version: ack.version, effective_bar: ack.effective_bar, bar: ack.bar } : null };
  }
  if (stepAt !== null) {
    const after = deltas.filter((x) => x.bar > stepAt);
    const acks = doc.events.filter((e) => e.kind === "ack" && e.offset_step_ms !== undefined);
    row.step = { at_bar: stepAt, done: stepDone, bars_after: after.length, delta_after_ms: stats(after.map((x) => x.d)),
                 offsets_used: [...new Set(d.plans.map((p) => p.off))].length, acks: acks.map((a) => ({ bar: a.bar, offset_step_ms: a.offset_step_ms })) };
  }
  console.log(`[a1 ${name}]`, JSON.stringify({ plan: row.plan, callback: row.callback, sound: row.sound, wake: row.wake_late_ms, dropped: row.late_dropped }));
  return row;
}

async function hidePage() {
  const tries = [];
  try { await page.send("Emulation.setFocusEmulationEnabled", { enabled: false }); tries.push({ method: "Emulation.setFocusEmulationEnabled false", ok: true }); }
  catch (e) { tries.push({ method: "Emulation.setFocusEmulationEnabled false", error: String(e.message || e) }); }
  let vis = await evaluate("document.visibilityState");
  try {
    const t = await browser.send("Target.createTarget", { url: "about:blank" });
    hidePage.other = t.targetId;
    await browser.send("Target.activateTarget", { targetId: t.targetId });
    await delay(700);
    vis = await evaluate("document.visibilityState");
    tries.push({ method: "another tab activated", visibility: vis });
  } catch (e) { tries.push({ method: "another tab activated", error: String(e.message || e) }); }
  if (vis !== "hidden") {
    try {
      const w = await browser.send("Browser.getWindowForTarget", { targetId: pageTarget });
      hidePage.window = w.windowId;
      await browser.send("Browser.setWindowBounds", { windowId: w.windowId, bounds: { windowState: "minimized" } });
      await delay(700);
      vis = await evaluate("document.visibilityState");
      tries.push({ method: "window minimized", visibility: vis });
    } catch (e) { tries.push({ method: "window minimized", error: String(e.message || e) }); }
  }
  return { visibility: vis, focus: await evaluate("document.hasFocus()"), tries };
}
async function showPage() {
  try { if (hidePage.window) await browser.send("Browser.setWindowBounds", { windowId: hidePage.window, bounds: { windowState: "normal" } }); } catch { /* */ }
  try { if (hidePage.other) await browser.send("Target.closeTarget", { targetId: hidePage.other }); } catch { /* */ }
  try { await browser.send("Target.activateTarget", { targetId: pageTarget }); } catch { /* */ }
  try { await page.send("Emulation.setFocusEmulationEnabled", { enabled: true }); } catch { /* */ }
  hidePage.window = null;
  hidePage.other = null;
}

async function a1() {
  const rows = [];
  const spec72 = SHORT ? { name: "72", bpm: 72, bars: 16, tempoAt: 6, tempoTo: 80, stepAt: 10 } : { name: "72", bpm: 72, bars: 90, tempoAt: 40, tempoTo: 80, stepAt: 60 };
  const spec140 = SHORT ? { name: "140", bpm: 140, bars: 24 } : { name: "140", bpm: 140, bars: 175 };
  const specHidden = SHORT ? { name: "occluded", bpm: 100, bars: 8, hide: true } : { name: "occluded", bpm: 100, bars: 25, hide: true };
  for (const spec of [spec72, spec140, specHidden]) {
    try { rows.push(await a1Run(spec)); }
    catch (e) { report.errors.push(`a1 ${spec.name}: ${e.stack || e}`); console.log("ERROR", e); }
  }
  report.a1.runs = rows;
  const main = rows.filter((r) => r.name !== "occluded");
  const ok = (fn) => main.length === 2 && main.every(fn);
  check("A1a plan: every handed event at the tempo-map formula (|d| <= 0.001 ms)", ok((r) => r.plan.n > 0 && r.plan.missing === 0 && r.plan.delta_ms.max_abs <= 0.001),
        { runs: main.map((r) => ({ name: r.name, n: r.plan.n, missing: r.plan.missing, max_abs: r.plan.delta_ms.max_abs })) });
  // A1b and A1d carry jam-rulings.md's re-baselined bars (2026-09-15); A1c stays the binding sound bar.
  check("A1b player: note-on callbacks p50 <= 8, p99 <= 16, max <= 33 ms; slope <= 0.2 ms/min; first 30 s - last 30 s <= 1 ms",
        ok((r) => r.callback.n > 0 && r.callback.p50 <= 8 && r.callback.p99 <= 16 && r.callback.max <= 33 && Math.abs(r.callback.slope_ms_per_min) <= 0.2 && Math.abs(r.callback.first30_minus_last30_ms) <= 1),
        { runs: main.map((r) => ({ name: r.name, ...r.callback })) });
  check("A1c sound: probe onsets against the fitted clock p99 <= 2 ms, slope <= 0.1 ms/min",
        ok((r) => r.sound.n > 0 && r.sound.unmatched === 0 && r.sound.p99 <= 2 && Math.abs(r.sound.slope_ms_per_min) <= 0.1),
        { runs: main.map((r) => ({ name: r.name, ...r.sound })) });
  const hid = rows.find((r) => r.name === "occluded");
  check("A1d occluded: worker wake lateness p99 <= 20 ms, late_dropped 0",
        hid && hid.wake_late_ms.n > 0 && hid.wake_late_ms.p99 <= 20 &&hid.late_dropped.page === 0 && (hid.late_dropped.last_ack ?? 0) === 0,
        { hidden: hid ? hid.hidden : null, wake: hid ? hid.wake_late_ms : null, late_dropped: hid ? hid.late_dropped : null, callback: hid ? hid.callback : null });
  const r72 = rows.find((r) => r.name === "72");
  check("A1e tempo change: downbeat at the formula +-0.5 ms, new bar length, ack version 2 effective_bar",
        r72 && r72.tempo && r72.tempo.effective_bar === r72.tempo.want_bar && Math.abs(r72.tempo.downbeat_vs_formula_ms) <= 0.5
          && r72.tempo.new_bar_length_delta_ms.n > 0 && r72.tempo.new_bar_length_delta_ms.max_abs <= 0.001 && r72.tempo.ack && r72.tempo.ack.version === 2,
        { tempo: r72 ? r72.tempo : null });
  check("A1f clock step: no bar line moves (0.000 ms) and an ack reports offset_step_ms 30",
        r72 && r72.step && r72.step.bars_after > 0 && r72.step.delta_after_ms.max_abs <= 0.001 && r72.step.offsets_used === 1
          && r72.step.acks.some((a) => Math.abs(a.offset_step_ms - 30) <= 1),
        { step: r72 ? r72.step : null });
}

// ------------------------------------------------------------------------------------------------------- main
try {
  const lockWait = Date.now();
  gpu = await acquireGpuLock({ label: `jam_timing ${[...ONLY].join(",")}${SHORT ? " --short" : ""}`, yieldToJam: false, maxHoldMs: (SHORT ? 10 : 30) * 60_000 });
  report.gpu_lock = { waited_s: Math.round((Date.now() - lockWait) / 1000), acquired_at: gpu.owner.acquiredAt, inherited: gpu.inherited };
  if (!opt.app) {
    const state = opt.state || join(tmpdir(), `arsenal-jam-timing-state-${stamp}`);
    mkdirSync(join(state, "performance"), { recursive: true });
    server = spawn("py", ["-m", "arsenal", "serve", "--port", opt.port, "--performance-root", join(state, "performance")],
                   { cwd: REPO, stdio: "ignore", windowsHide: true });
    report.server = { port: Number(opt.port), performance_root: join(state, "performance"), pid: server.pid };
  }
  await waitFor(() => getJSON(`${APP}/api/health`), 30000, "the jam server");
  chrome = spawn(opt.chrome, [
    `--remote-debugging-port=${opt["chrome-port"]}`, `--user-data-dir=${profile}`, "--no-first-run", "--no-default-browser-check",
    ...report.flags, "--window-size=1400,1000", "about:blank",
  ], { stdio: "ignore" });
  const version = await waitFor(() => getJSON(`http://127.0.0.1:${opt["chrome-port"]}/json/version`), 20000, "Chrome DevTools");
  report.chrome = version.Browser;
  browser = await connect(version.webSocketDebuggerUrl);
  const target = (await getJSON(`http://127.0.0.1:${opt["chrome-port"]}/json/list`)).find((t) => t.type === "page");
  pageTarget = target.id;
  page = await connect(target.webSocketDebuggerUrl);
  page.on((msg) => {
    const p = msg.params;
    if (msg.method === "Runtime.consoleAPICalled" && (p.type === "error" || p.type === "warning")) {
      report.console.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 400) });
    } else if (msg.method === "Runtime.exceptionThrown") {
      const x = p.exceptionDetails;
      report.exceptions.push({ text: x.text, description: x.exception?.description, line: x.lineNumber, url: x.url });
    }
  });
  for (const domain of ["Runtime", "Page"]) await page.send(`${domain}.enable`);
  await page.send("Page.navigate", { url: `${APP}/web/piano/transport-test.html?probe=1&timbre=click&page=${PAGE}` });
  await waitFor(() => evaluate("!!(window.__jamTest && window.__jamTest.ready) && __jamTest.client.status === 'listening' && __jamTest.voice.status() === 'ready'"), 30000, "the transport test page");
  report.page = await evaluate("({ probe: __jamTest.probe, sampleRate: __jamTest.ctx.sampleRate, outputLatency: __jamTest.ctx.outputLatency, baseLatency: __jamTest.ctx.baseLatency, visibility: document.visibilityState })");
  await delay(1500);
  if (ONLY.has("a3")) {
    for (const [name, fn] of [["count-ins", a3Ticks], ["changes", a3Changes], ["late frame", a3LateFrame]]) {
      try { await fn(); } catch (e) { report.errors.push(`a3 ${name}: ${e.stack || e}`); console.log("ERROR", name, e); }
    }
  }
  if (ONLY.has("a1")) await a1();
} catch (err) {
  report.errors.push(String((err && err.stack) || err));
  console.log("ERROR", err);
} finally {
  report.finished_at = new Date().toISOString();
  const checks = Object.values(report.checks);
  report.verdict = { pass: checks.length > 0 && checks.every((c) => c.pass) && report.errors.length === 0 && report.exceptions.length === 0,
                     passed: checks.filter((c) => c.pass).length, of: checks.length };
  writeFileSync(jsonPath, JSON.stringify(report, null, 2));
  try { await browser?.send("Browser.close"); } catch { /* closed */ }
  await delay(1000);
  try { chrome?.kill(); } catch { /* gone */ }
  gpu?.release();
  if (server) {
    try { spawnSync("taskkill", ["/PID", String(server.pid), "/T", "/F"], { stdio: "ignore" }); } catch { /* gone */ }
  }
  await delay(500);
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold a file */ }
  console.log("verdict:", JSON.stringify(report.verdict));
  console.log("receipt:", jsonPath);
  process.exit(report.verdict.pass ? 0 : 1);
}
