// Node tests for arsenal/web/piano/tempomap.js (jam-spec 9.1). Zero dependencies:  node tests/jam_tempomap.test.mjs
// Runs every case in tests/fixtures/jam/tempomap_cases.json. The Python twin (arsenal/jam/tempomap.py) runs the same
// file in tests/test_arsenal_jam_schemas.py, so both agree with the fixture, and with each other, to 0.001 ms.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as TM from "../arsenal/web/piano/tempomap.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
let pass = 0, fail = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}

const fx = JSON.parse(readFileSync(here("./fixtures/jam/tempomap_cases.json"), "utf8"));
const INT_KEYS = new Set(["bar", "pass", "slot", "def_version", "from_bar", "def_from_bar"]);
const BEAT_KEYS = new Set(["beat", "cycle_beat", "at_beat"]);
const INT_OPS = new Set(["pass_of", "slot_at"]);
const BEAT_OPS = new Set(["cycle_beat"]);

// null when got agrees with want, else a description of the first difference
function differ(got, want, key, op, path = "") {
  const where = path || "(value)";
  if (want === null || typeof want === "boolean" || typeof want === "string") {
    return got === want ? null : `${where}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`;
  }
  if (typeof want === "number") {
    if (typeof got !== "number") return `${where}: got ${JSON.stringify(got)} want ${want}`;
    if (INT_KEYS.has(key) || (key === null && INT_OPS.has(op))) {
      return got === want ? null : `${where}: got ${got} want ${want}`;
    }
    const tol = BEAT_KEYS.has(key) || (key === null && BEAT_OPS.has(op)) ? fx.tolerance_beats : fx.tolerance_ms;
    return Math.abs(got - want) <= tol ? null : `${where}: got ${got} want ${want} (|d| ${Math.abs(got - want)})`;
  }
  if (Array.isArray(want)) {
    if (!Array.isArray(got) || got.length !== want.length) return `${where}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`;
    for (let i = 0; i < want.length; i++) {
      const d = differ(got[i], want[i], key, op, `${path}[${i}]`);
      if (d) return d;
    }
    return null;
  }
  if (got === null || typeof got !== "object") return `${where}: got ${JSON.stringify(got)} want an object`;
  const gk = Object.keys(got).sort(), wk = Object.keys(want).sort();
  if (JSON.stringify(gk) !== JSON.stringify(wk)) return `${where}: keys ${gk} want ${wk}`;
  for (const k of wk) {
    const d = differ(got[k], want[k], k, op, path ? `${path}.${k}` : k);
    if (d) return d;
  }
  return null;
}

function defsFor(c) {
  const args = c.args || {};
  if (Object.prototype.hasOwnProperty.call(args, "defs") && args.defs === null) return null;
  const map = fx.maps[c.map];
  if (!map) return null;
  if (typeof map.defs === "string") return fx.defs[map.defs];
  const out = {};
  for (const [version, name] of Object.entries(map.defs)) out[version] = fx.defs[name];
  return out;
}

function run(c) {
  const a = c.args || {};
  const map = fx.maps[c.map];
  const segs = map ? map.segments : null, m = map ? map.beats_per_bar : null;
  const defs = defsFor(c);
  switch (c.op) {
    case "t_epoch": return TM.tEpoch(segs, m, a.bar, a.beat ?? 0);
    case "bar_at": return TM.barAt(segs, m, a.epoch_ms);
    case "pass_of": return TM.passOf(segs, m, a.bar, defs);
    case "cycle_beat": return TM.cycleBeat(segs, m, a.bar, a.beat ?? 0, defs);
    case "slot_at": return TM.slotAt(fx.defs[a.def].slots, a.cycle_beat);
    case "position": return TM.position(segs, m, a.epoch_ms, defs);
    case "first_segment": return TM.firstSegment(a.start_epoch_ms, a.bpm, a.count_in, a.def_version);
    case "add_segment": {
      let out = segs;
      for (const ch of a.changes) {
        out = TM.addSegment(out, m, ch.bar, { bpm: ch.bpm ?? null, def_version: ch.def_version ?? null,
          def_from_bar: ch.def_from_bar ?? null });
      }
      return out;
    }
    case "next_line": return TM.nextLine(segs, m, a.received_epoch_ms, a.at, defs, a.lead_ms ?? TM.CHANGE_LEAD_MS);
    case "handoff_epoch": return TM.handoffEpoch(segs, m, a.bar, a.margin_ms ?? TM.HANDOFF_MARGIN_MS);
    case "session_t_ms": return TM.sessionTms(segs, m, a.bar, a.beat ?? 0, a.anchor);
    case "median_offset": return TM.medianOffset(a.pairs);
    case "beat_ms": return TM.beatMs(a.bpm);
    case "bar_ms": return TM.barMs(a.bpm, a.beats_per_bar);
    default: throw new Error(`unknown op ${c.op}`);
  }
}

// ---------------------------------------------------------------------------------------------- fixture --
check("fixture api", fx.api === "arsenal.jam.tempomap.cases/v0", fx.api);
check("fixture has at least 40 cases", fx.cases.length >= 40, String(fx.cases.length));
for (const [name, value] of Object.entries(fx.constants)) {
  check(`constant ${name} matches the fixture`, TM[name] === value, `${TM[name]} vs ${value}`);
}
const ids = new Set();
for (const c of fx.cases) {
  check(`case id ${c.id} is unique`, !ids.has(c.id));
  ids.add(c.id);
  if (c.raises) {
    let thrown = null;
    try { run(c); } catch (e) { thrown = e; }
    check(`${c.id} (${c.op}) throws ${c.raises}`, thrown && thrown.name === c.raises, thrown ? thrown.name : "nothing thrown");
    continue;
  }
  let got;
  try { got = run(c); } catch (e) { check(`${c.id} (${c.op})`, false, `threw ${e.message}`); continue; }
  const d = differ(got, c.expect, null, c.op);
  check(`${c.id} (${c.op})`, d === null, d);
}

// ------------------------------------------------------------------------------------------ properties --
const steady = fx.maps.steady66.segments;
const before = JSON.stringify(steady);
TM.addSegment(steady, 4, 8, { bpm: 72 });
check("addSegment leaves its input alone", JSON.stringify(steady) === before);
const seg = TM.firstSegment(1000, 66, 1);
check("a bar line maps back to itself", TM.barAt([seg], 4, TM.tEpoch([seg], 4, 12)).bar === 12);
check("perfOf subtracts the offset", TM.perfOf(1893456000500, 1893452400000.25) === 3600499.75);
let threw = false;
try { TM.tEpoch([], 4, 0); } catch (e) { threw = e instanceof TM.TempoMapError; }
check("an empty map throws TempoMapError", threw);

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
