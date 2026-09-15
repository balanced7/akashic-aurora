// The groove bridge: arsenal/web/piano/groove.js under node, for Python (jam-spec 3; 11.3 step 13, the riff's
// rebuild of Claude's notes; v2 FL Route F). No dependencies. It imports the page's own module, so the page and this
// bridge give the same events for the same run, byte for byte (A2).
//
//   echo '{"run": {...}, "defs": {"1": {...}}, "to_bar": 16}' | node arsenal/groove_bridge.mjs
//   node arsenal/groove_bridge.mjs request.json [--pretty]
//
// Requests: one JSON object, on stdin or in a file named on the command line.
//   Run form   {run, defs, from_bar?, to_bar?, times?, flat?}
//     run      run.json, or anything with its beats_per_bar, segments, settings, mode, count_in_bars and stop_bar.
//     defs     {"<def_version>": def} (the defs of the run's start and change lines), or one def for every version.
//     from_bar defaults to -count_in_bars (0 for a play run); to_bar (exclusive) to stop_bar. A play run defaults to
//              one bar past its cycle, where the last chord's tail is carried. A run with no stop_bar needs to_bar.
//     times    default true: every event also gets epoch_ms (onset, ms included) and end_epoch_ms through the tempo
//              map (groove.eventTimes).
//     flat     true adds notes: every struck note (no carries, no ticks) as {bar, ...event}, for the loopback guard.
//   Plain form {def, settings, bars? | from_bar and to_bar, def_from_bar?, bpm?, mode?}: groove.bar for each bar.
//   Batch      {batch: [request, ...]}: one node start for many requests.
// Answers: {ok: true, api, engine, ...}, or {ok: false, error, field}. The exit code is 0 when ok (a batch is ok
// when every one of its requests is), else 1.
//   Run form   {ok, api, engine, run, from_bar, to_bar, warnings, bars: [{bar, pass, def_version, def_from_bar, bpm,
//              settings_from_bar, events}], notes?}
//   Plain form {ok, api, engine, warnings, bars: [{bar, pass, events}]}
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import * as G from "./web/piano/groove.js";

export const MAX_BARS = 20000;

function fail(error, field = null) { return { ok: false, error, field }; }

function barsRange(req, fromDefault, toDefault) {
  const from = req.from_bar ?? fromDefault;
  const to = req.to_bar ?? toDefault;
  if (to == null) return fail("to_bar is needed: the run has no stop_bar", "to_bar");
  if (!Number.isInteger(from)) return fail(`from_bar must be an integer (got ${JSON.stringify(from)})`, "from_bar");
  if (!Number.isInteger(to) || to < from) return fail(`to_bar must be an integer not below from_bar (got ${JSON.stringify(to)})`, "to_bar");
  if (to - from > MAX_BARS) return fail(`at most ${MAX_BARS} bars per request (asked for ${to - from})`, "to_bar");
  return { from, to };
}

function runAnswer(req) {
  const run = req.run;
  if (!run || typeof run !== "object") return fail("run must be an object", "run");
  if (!Number.isInteger(run.beats_per_bar)) return fail("run.beats_per_bar must be an integer", "run.beats_per_bar");
  if (!Array.isArray(run.segments) || !run.segments.length) return fail("run.segments must be a non-empty list", "run.segments");
  const defs = req.defs ?? req.def;
  if (!defs || typeof defs !== "object") return fail("defs must be a def or an object def_version -> def", "defs");
  const play = run.mode === "play";
  let toDefault = run.stop_bar ?? null;
  if (toDefault == null && play) {
    const first = defs.cycle_beats !== undefined ? defs : defs[run.segments[0].def_version];
    if (first && first.cycle_beats) toDefault = first.cycle_beats / run.beats_per_bar + 1;
  }
  const range = barsRange(req, play ? 0 : -(run.count_in_bars ?? 0), toDefault);
  if (range.ok === false) return range;
  const warnings = [];
  const bars = [];
  for (let n = range.from; n < range.to; n++) {
    const r = G.barOfRun(run, defs, n);
    for (const w of r.warnings) if (!warnings.includes(w)) warnings.push(w);
    const events = req.times === false ? r.events : G.eventTimes(run.segments, run.beats_per_bar, n, r.events);
    bars.push({ bar: r.bar, pass: r.pass, def_version: r.def_version, def_from_bar: r.def_from_bar, bpm: r.bpm,
      settings_from_bar: r.settings_from_bar, events });
  }
  const out = { ok: true, api: G.API, engine: G.ENGINE, run: run.run ?? null, from_bar: range.from, to_bar: range.to,
    warnings, bars };
  if (req.flat) {
    out.notes = bars.flatMap((b) => b.events.filter((e) => !e.carry && e.voice !== "tick").map((e) => ({ bar: b.bar, ...e })));
  }
  return out;
}

function plainAnswer(req) {
  const def = req.def;
  const settings = req.settings ?? {};
  const opts = { def_from_bar: req.def_from_bar ?? 0, bpm: req.bpm ?? null, mode: req.mode ?? null };
  let list;
  if (req.bars != null) {
    if (!Array.isArray(req.bars) || !req.bars.every(Number.isInteger)) return fail("bars must be a list of integers", "bars");
    if (req.bars.length > MAX_BARS) return fail(`at most ${MAX_BARS} bars per request`, "bars");
    list = req.bars;
  } else {
    const range = barsRange(req, null, null);
    if (req.from_bar == null) return fail("the plain form needs bars, or from_bar and to_bar", "bars");
    if (range.ok === false) return range;
    list = [];
    for (let n = range.from; n < range.to; n++) list.push(n);
  }
  const E = G.effectiveSettings(def, settings, opts);
  const cycleBars = def.cycle_beats / def.beats_per_bar;
  const bars = list.map((n) => {
    const pass = Math.floor((n - opts.def_from_bar) / cycleBars);
    return { bar: n, pass, events: G.bar(def, settings, pass, n, opts) };
  });
  return { ok: true, api: G.API, engine: G.ENGINE, warnings: E.warnings, bars };
}

// One answer for one request object (exported for tests; the command line below calls it).
export function answer(req) {
  if (!req || typeof req !== "object" || Array.isArray(req)) return fail("the request must be a JSON object");
  try {
    if (req.batch !== undefined) {
      if (!Array.isArray(req.batch)) return fail("batch must be a list of requests", "batch");
      const results = req.batch.map((r) => answer(r));
      return { ok: results.every((r) => r.ok), api: G.API, engine: G.ENGINE, results };
    }
    if (req.run !== undefined) return runAnswer(req);
    if (req.def !== undefined) return plainAnswer(req);
    return fail("the request needs run (with defs), def, or batch");
  } catch (e) {
    return fail(e.message, e.field ?? null);
  }
}

async function readStdin() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks).toString("utf8");
}

const invoked = process.argv[1] ? pathToFileURL(resolve(process.argv[1])).href.toLowerCase() : "";
if (invoked === import.meta.url.toLowerCase()) {
  const args = process.argv.slice(2);
  const pretty = args.includes("--pretty");
  const file = args.find((a) => a !== "--pretty");
  let out;
  try {
    const text = file ? readFileSync(file, "utf8") : await readStdin();
    out = answer(JSON.parse(text));
  } catch (e) {
    out = fail(`the request is not readable JSON: ${e.message}`);
  }
  process.stdout.write(JSON.stringify(out, null, pretty ? 2 : 0) + "\n");
  process.exitCode = out.ok ? 0 : 1;
}
