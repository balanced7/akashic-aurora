// Node tests for the live cadence judge (arsenal/web/piano/cadence-live.js), the rule-for-rule twin of arsenal/practice.py
// _cadence. Zero dependencies:
//   node tests/piano_cadence_live.test.mjs           everything: fixtures, kinds, allocation, and parity with the oracle
//   node tests/piano_cadence_live.test.mjs --quick   the fixtures and kinds only
// Sections: (a) the SYNTHETIC shared fixtures (tests/fixtures/cadence_cases.json, which tests/test_cadence_fixtures_python.py
// runs through practice._cadence itself); (b) the kind strings, verbatim; (c) judge() allocates nothing; (d) Level A parity:
// for every private oracle file (state/arsenal/story/oracle/<sid>.json, gitignored, written from practice.analyze's own rows)
// every n is judged and compared with the raw cadences practice found. Nothing from the oracle is written anywhere: the test
// prints totals and the first few mismatches only.
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { PerformanceObserver } from "node:perf_hooks";
import v8 from "node:v8";
import vm from "node:vm";
import { judge, KINDS, CADENCE, CADENCE_LIVE_API } from "../arsenal/web/piano/cadence-live.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const quick = process.argv.includes("--quick");
let pass = 0, fail = 0;
const report = [];
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const newOut = () => ({ kind: null, code: -1, first: -1, last: -1, startMs: 0, endMs: 0, dominant: false });
const areasById = (list) => { const a = []; for (const x of list) a[x.id] = { tonic: x.tonic, mode: x.mode }; return a; };

// ------------------------------------------------------------------------------------------------- (b) the shape
check("API string", CADENCE_LIVE_API === "arsenal.piano.cadence-live/v1");
check("constants are practice.py's", CADENCE.GAP_MS === 1500 && CADENCE.ARRIVAL_MS === 800 && CADENCE.DECEPTIVE_LEARNED === 3);
check("CADENCE and KINDS are frozen", Object.isFrozen(CADENCE) && Object.isFrozen(KINDS));
const EXPECTED_KINDS = [
  "5 -> 1 (authentic)", "5sus -> 1 (suspended dominant)", "2 -> 5 -> 1 (authentic)",
  "2 -> 5sus -> 1 (suspended dominant)", "5 over a 1 pedal -> 1", "5 -> 6m (deceptive)", "5 -> b6 (deceptive)",
  "4m -> 1 (minor plagal)", "4 -> 1 (plagal)", "b6 -> b7 -> 1 (Aeolian)", "b7 -> 1",
];
for (const k of EXPECTED_KINDS) check(`KINDS has ${JSON.stringify(k)}`, KINDS.includes(k));
check("KINDS has nothing else", KINDS.length === EXPECTED_KINDS.length, String(KINDS.length));
// the two "2 -> 5" kinds are Python's kind.replace("5", "2 -> 5", 1)
check("2 -> 5 kinds are the replace of the 5 kinds",
  KINDS.includes("5 -> 1 (authentic)".replace("5", "2 -> 5")) && KINDS.includes("5sus -> 1 (suspended dominant)".replace("5", "2 -> 5")));

// ------------------------------------------------------------------------------------------------- (a) fixtures
const cases = JSON.parse(readFileSync(here("./fixtures/cadence_cases.json"), "utf8"));
check("at least 24 fixtures", cases.length >= 24, String(cases.length));
const seenKinds = new Set();
let nulls = 0;
for (const c of cases) {
  const out = newOut();
  const got = judge(c.windows, areasById(c.areas), c.n, out);
  if (c.expect === null) {
    nulls++;
    check(`${c.name}: no cadence`, got === false && out.kind === null, `got ${out.kind}`);
    continue;
  }
  seenKinds.add(c.expect.kind);
  check(`${c.name}: a cadence`, got === true, "none found");
  if (!got) continue;
  check(`${c.name}: kind`, out.kind === c.expect.kind, `${out.kind} vs ${c.expect.kind}`);
  check(`${c.name}: code`, KINDS[out.code] === out.kind);
  check(`${c.name}: chain`, out.first === c.expect.first && out.last === c.expect.last,
    `${out.first}..${out.last} vs ${c.expect.first}..${c.expect.last}`);
  check(`${c.name}: times`, out.startMs === c.windows[out.first].start_ms && out.endMs === c.windows[out.last].end_ms);
}
for (const k of EXPECTED_KINDS) check(`a fixture covers ${k}`, seenKinds.has(k));
check("fixtures include no-cadence cases", nulls >= 10, String(nulls));
{
  const c = cases.find((x) => x.name.startsWith("bass dominant: "));
  const out = newOut();
  check("the bass-dominant departure is flagged dominant", c && judge(c.windows, areasById(c.areas), c.n, out) && out.dominant === true);
  const d = cases.find((x) => x.name === "authentic G -> C");
  check("a named 5 chord is not flagged dominant", d && judge(d.windows, areasById(d.areas), d.n, out) && out.dominant === false);
  const t = cases.find((x) => x.name.startsWith("bass dominant with no texture key"));
  check("the no-texture fixture really has no texture key", t && !("texture" in t.windows[0]));
  check("a bass dominant with no texture key is flagged dominant",
    t && judge(t.windows, areasById(t.areas), t.n, out) && out.dominant === true);
}
{
  // n outside 1..ws.length-1 is no cadence and throws nothing (practice never judges n = 0)
  const c = cases.find((x) => x.name === "authentic G -> C");
  const out = newOut();
  let threw = null, at0 = null, atEnd = null;
  try {
    out.kind = "stale";  // a stale kind must be cleared even when n is out of range
    at0 = judge(c.windows, areasById(c.areas), 0, out);
    const k0 = out.kind;
    out.kind = "stale";
    atEnd = judge(c.windows, areasById(c.areas), c.windows.length, out);
    at0 = at0 === false && k0 === null;
    atEnd = atEnd === false && out.kind === null;
  } catch (e) { threw = e; }
  check("judge(ws, areas, 0) is false and throws nothing", !threw && at0 === true, threw ? String(threw) : "");
  check("judge(ws, areas, ws.length) is false and throws nothing", !threw && atEnd === true, threw ? String(threw) : "");
}
{
  // a miss leaves out untouched except kind
  const c = cases.find((x) => x.expect === null);
  const out = newOut();
  out.first = 77; out.startMs = 5; out.kind = "stale";
  judge(c.windows, areasById(c.areas), c.n, out);
  check("a miss clears kind and leaves the rest", out.kind === null && out.first === 77 && out.startMs === 5);
}

// ------------------------------------------------------------------------------------------------- (c) allocation
if (!quick) {
  const prepared = cases.map((c) => ({ ws: c.windows, areas: areasById(c.areas), n: c.n }));
  const out = newOut();
  out.startMs = 0.5; out.endMs = 0.5;  // fields that may hold fractional ms, from the first store
  let hits = 0;
  const run = (count) => {
    for (let i = 0; i < count; i++) {
      const p = prepared[i % prepared.length];
      if (judge(p.ws, p.areas, p.n, out)) hits++;
    }
  };
  run(200000);
  let best = Infinity;
  for (let trial = 0; trial < 5; trial++) {
    const t0 = performance.now();
    run(200000);
    const us = (performance.now() - t0) * 1000 / 200000;
    if (us < best) best = us;
  }
  report.push(`judge(): ${best.toFixed(3)} us a call, best of 5 x 200k over ${prepared.length} fixtures`);
  check("judge costs under 2 us a call", best < 2, `${best.toFixed(3)} us`);

  let collect = null;
  try { v8.setFlagsFromString("--expose-gc"); collect = vm.runInNewContext("gc"); } catch { collect = null; }
  if (typeof collect === "function") {
    let collections = 0;
    const watch = new PerformanceObserver((list) => { collections += list.getEntries().length; });
    watch.observe({ entryTypes: ["gc"] });
    run(50000);
    collect(); collect();
    await new Promise((r) => setTimeout(r, 30));
    collections = 0;
    const before = v8.getHeapStatistics().used_heap_size;
    run(400000);
    const grew = v8.getHeapStatistics().used_heap_size - before;
    await new Promise((r) => setTimeout(r, 60));
    watch.disconnect();
    report.push(`400k judge() calls after a collection by hand: ${collections} collections, heap +${grew} bytes`);
    check("judge allocates nothing: no collection was needed", collections === 0, String(collections));
    check("judge allocates nothing: the heap barely moves", grew < 400000, `${grew} bytes over 400k calls`);
  } else report.push("allocation: skipped (no gc available)");
  check("the timing loops found cadences", hits > 0);
}

// ------------------------------------------------------------------------------------------------- (d) parity
if (!quick) {
  const dir = here("../state/arsenal/story/oracle/");
  // one file a session; the oracle builder's manifest.json (no windows) is not a session
  const files = existsSync(dir) ?
    readdirSync(dir).filter((f) => f.endsWith(".json") && f !== "manifest.json").sort() : [];
  const listed = existsSync(dir + "manifest.json");
  if (!existsSync(dir)) {
    report.push("SKIP parity: no private oracle");
  } else if (files.length === 0 && !listed) {
    report.push("SKIP parity: the private oracle folder holds no session files");
  } else if (files.length === 0) {
    check("the oracle folder holds the session files its manifest lists", false, "manifest.json without session files");
  } else {
    let manifest = null;
    if (existsSync(dir + "manifest.json")) {
      try { manifest = JSON.parse(readFileSync(dir + "manifest.json", "utf8")); } catch (e) {
        check("oracle manifest.json parses", false, String(e));
      }
    }
    const perKind = new Map();  // kind -> [oracle count, reproduced]
    const mismatches = [];
    let sessions = 0, judged = 0, wrong = 0, rawTotal = 0, unstamped = 0, countsBad = 0;
    const out = newOut();
    for (const f of files) {
      let o;
      try { o = JSON.parse(readFileSync(dir + f, "utf8")); } catch (e) { check(`oracle ${f} parses`, false, String(e)); continue; }
      if (o.api !== "arsenal.story.oracle/v1") { check(`oracle ${f} api`, false, String(o.api)); continue; }
      if (!Array.isArray(o.areas) || !Array.isArray(o.windows) || !Array.isArray(o.raw_cadences)) {
        check(`oracle ${f} has areas, windows and raw_cadences`, false); continue;
      }
      sessions++;
      if (typeof o.rules_sha !== "string") unstamped++;
      rawTotal += o.raw_cadences.length;
      if (manifest && manifest.sessions) {
        const m = manifest.sessions[f.slice(0, -".json".length)];
        if (!m || m.windows !== o.windows.length || m.raw_cadences !== o.raw_cadences.length) countsBad++;
      }
      const areas = [];
      for (const a of o.areas) areas[a.id] = { tonic: a.tonic, mode: a.mode };
      const want = new Map();
      for (const r of o.raw_cadences) want.set(r.n, r);
      for (const r of o.raw_cadences) {
        const e = perKind.get(r.kind) || [0, 0];
        e[0]++;
        perKind.set(r.kind, e);
      }
      const ws = o.windows;
      for (let n = 1; n < ws.length; n++) {
        judged++;
        const got = judge(ws, areas, n, out);
        const w = want.get(n);
        let bad = null;
        if (!w && got) bad = `live found ${out.kind}, practice none`;
        else if (w && !got) bad = `practice found ${w.kind}, live none`;
        else if (w && got) {
          if (out.kind !== w.kind) bad = `kind ${out.kind} vs ${w.kind}`;
          else if (out.startMs !== w.start_ms || out.endMs !== w.end_ms) {
            bad = `times ${out.startMs}..${out.endMs} vs ${w.start_ms}..${w.end_ms}`;
          } else perKind.get(w.kind)[1]++;
        }
        if (bad) { wrong++; if (mismatches.length < 8) mismatches.push(`${o.sid} n=${n}: ${bad}`); }
      }
    }
    // The oracle is a model of Daniel's private playing: by default only pass/fail leaves this test. Counts, kinds
    // and session ids print only when asked for on this machine (--private-detail), never in a shared log.
    if (process.argv.includes("--private-detail")) {
      report.push(`parity: ${sessions} oracle sessions, ${judged} windows judged, ${wrong} mismatches`);
      for (const [k, [have, made]] of [...perKind.entries()].sort()) report.push(`  ${k}: ${made}/${have} reproduced`);
      for (const m of mismatches) report.push(`  MISMATCH ${m}`);
    } else {
      report.push(`parity: ${wrong === 0 ? "exact" : "MISMATCHES (re-run with --private-detail to list them)"}`);
    }
    if (unstamped) {
      report.push("WARNING: some oracle files carry no rules_sha (built before the stamp): " +
        "rebuild with py -m arsenal.story_corpus oracle");
    }
    check("parity with practice._cadence on every oracle window", wrong === 0, `${wrong} mismatches`);
    check("the oracle had sessions", sessions > 0);
    check("parity judged windows", judged > 0);
    check("the oracle holds raw cadences", rawTotal > 0);
    let expected = 0, reproduced = 0;
    for (const [have, made] of perKind.values()) { expected += have; reproduced += made; }
    check("every raw cadence was reproduced (sum over kinds)", reproduced === expected && expected === rawTotal);
    if (manifest) {
      const keys = Object.keys(manifest.sessions || {}).sort();
      const names = files.map((f) => f.slice(0, -".json".length));
      check("the oracle session files are exactly the manifest's sessions",
        keys.length === names.length && keys.every((k, i) => k === names[i]));
      check("every session's windows and raw cadences match the manifest's counts", countsBad === 0);
    } else report.push("parity: no manifest.json, the manifest cross-check was skipped");
  }
}

for (const line of report) console.log(line);
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
