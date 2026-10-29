// The chord phrasing (arsenal/web/stage/grammar.js, the recogniser; ensemble.js, what it does): node --test tests/stage_grammar.test.mjs
//
// Daniel, 2026-10-29: "lets also land the chord phrasing." The cases are the round-3 design's pre-registered table
// (docs/library/design/20261028_kick-vocabulary-round3-codex-2026-10-28_4a3a13.md, section 11) for what this slice builds:
// immediate singles, chords, fast strums, slow sweeps (BREATH), the explicit BREATH modifier, moving intervals as a
// recognised label, auto-repeat, releases by press id and cancel. Each row of the table this slice covers is named.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Grammar, G, windowsFor, positionOf } from "../arsenal/web/stage/grammar.js";
import { Ensembles, chainLayers, TRANSPORT_RANK } from "../arsenal/web/stage/ensemble.js";

// play a script: [t, control, down?=true, source?="key"]; a down without an up stays held. Returns every decision, and
// the decisions grouped per input (index-aligned) so a test can ask what ONE key did on its own call.
function play(script, { B = 400, positional, settleAt = null } = {}) {
  const g = new Grammar({ beatMs: () => B, ...(positional ? { positional } : {}) });
  const per = [], all = [];
  for (const [t, control, down = true, source = "key"] of script) {
    const d = g.input({ source, control, down, t, velocity: 0.8 });
    per.push(d); all.push(...d);
  }
  if (settleAt !== null) all.push(...g.settle(settleAt));
  return { g, per, all };
}
const presses = (ds) => ds.filter((d) => d.type === "press");
const kinds = (ds) => ds.filter((d) => d.type === "settle").map((d) => `${d.kind}:${d.controls.join("")}`);
// keys pressed and released n ms apart (each held `hold` ms)
const run = (keys, gap, { t0 = 1000, hold = 40, source = "key" } = {}) => {
  const ev = [];
  keys.forEach((k, i) => { ev.push([t0 + i * gap, k, true, source]); ev.push([t0 + i * gap + hold, k, false, source]); });
  return ev.sort((a, b) => a[0] - b[0] || (a[2] === b[2] ? 0 : a[2] ? 1 : -1));
};

test("positions and windows: 0 sits at position 10; W = clamp(B/4, 60, 110); the slow band; the walk window", () => {
  assert.equal(positionOf("0"), 10); assert.equal(positionOf("1"), 1); assert.equal(positionOf("C"), null);
  assert.equal(windowsFor(400).W, 100);
  assert.equal(windowsFor(200).W, 60);
  assert.equal(windowsFor(600).W, 110);
  assert.ok(Math.abs(windowsFor(60000 / 154).W - 97.40) < 0.01);       // the design's 154 BPM arithmetic
  assert.ok(Math.abs(windowsFor(400).slowMin - 112) < 1e-9); assert.equal(windowsFor(400).slowMax, 380);
  assert.equal(windowsFor(375).slowMin, 110);
  assert.equal(windowsFor(400).walk, 800); assert.equal(windowsFor(300).walk, 600);
  // the slow and fast ranges never overlap, and the chord window sits under the slow band
  for (let B = 200; B <= 2000; B += 7) { const w = windowsFor(B); assert.ok(w.slowMin > G.strumGapMs && w.slowMin >= w.W); }
});

test("lone 8 or 9 followed by silence: the action dispatches on its own call, no recognition delay", () => {
  for (const k of ["8", "9"]) {
    const { per, all } = play([[1000, k]], { settleAt: 5000 });
    assert.deepEqual(per[0].filter((d) => d.type === "press").map((d) => [d.control, d.kind, d.member]), [[k, "single", 0]]);
    assert.deepEqual(kinds(all), [`single:${k}`]);
  }
});

test("9,8,7,6 at 180 ms: the first two singles speak, the third establishes the fade (no STOP), the fourth steps it", () => {
  const { per, all } = play(run(["9", "8", "7", "6"], 180), { settleAt: 9000 });
  const downs = per.filter((_, i) => i % 2 === 0);
  assert.deepEqual(presses(downs[0]).map((d) => d.control), ["9"]);
  assert.deepEqual(presses(downs[1]).map((d) => d.control), ["8"]);
  assert.equal(presses(downs[2]).length, 0, "7 (STOP) must not fire");
  const start = downs[2].find((d) => d.type === "breath");
  assert.equal(start.phase, "start");
  assert.ok(Math.abs(start.delta - -2 / 9) < 1e-12, "the run's movement so far: two positions down");
  assert.deepEqual(start.cancel.map((c) => c.control), ["9", "8"]);
  assert.equal(presses(downs[3]).length, 0);
  assert.ok(Math.abs(downs[3].find((d) => d.type === "breath").delta - -1 / 9) < 1e-12);
  // their releases: the suppressed keys release nothing legacy
  const rel = all.filter((d) => d.type === "release");
  assert.deepEqual(rel.map((d) => [d.control, d.dispatched]), [["9", true], ["8", true], ["7", false], ["6", false]]);
  // counted once, as a fade (the two singles are the sweep's)
  assert.deepEqual(kinds(all), []);
  assert.ok(all.some((d) => d.type === "breath" && d.phase === "end" && d.why === "gap"));
});

test("Daniel's run, 8 7 6 5 4 then 4 5 6 7 8 9: fades out, then (a fresh run) fades back in", () => {
  const a = run(["8", "7", "6", "5", "4"], 200), b = run(["4", "5", "6", "7", "8", "9"], 200, { t0: 3000 });
  const { all, g } = play([...a, ...b], { settleAt: 9000 });
  const br = all.filter((d) => d.type === "breath" && d.phase !== "end");
  const sum = (xs) => xs.reduce((s, d) => s + d.delta, 0);
  const out = br.filter((d) => d.t < 3000), back = br.filter((d) => d.t >= 3000);
  assert.ok(Math.abs(sum(out) - -4 / 9) < 1e-12, `out ${sum(out)}`);
  assert.ok(Math.abs(sum(back) - 5 / 9) < 1e-12, `back ${sum(back)}`);
  // what fired as singles: 8, 7 (the run's first two), then 4, 5 (the next run's first two)
  assert.deepEqual(presses(all).map((d) => d.control), ["8", "7", "4", "5"]);
  assert.equal(g.counts.sweeps, 2);
});

test("B held, then the same run: the fade from the first key, no HERO / MORPH / STOP", () => {
  const ev = [[900, "B"], ...run(["9", "8", "7", "6"], 180), [2000, "B", false]];
  const { all } = play(ev, { settleAt: 9000 });
  assert.equal(presses(all).length, 0);
  const br = all.filter((d) => d.type === "breath");
  assert.deepEqual(br.map((d) => d.phase), ["arm", "start", "step", "step", "step", "end"]);
  assert.ok(Math.abs(br.reduce((s, d) => s + d.delta, 0) - -3 / 9) < 1e-12);
  // a jump under B moves by the distance (the row is a fader)
  const j = play([[0, "B"], [100, "9"], [400, "3"]]).all.filter((d) => d.type === "breath");
  assert.ok(Math.abs(j[2].delta - -6 / 9) < 1e-12);
});

test("9,8,7,6 at 39 ms: one strum lineage, ordered expansion, no fade, no second lineage", () => {
  const { all } = play(run(["9", "8", "7", "6"], 39, { hold: 200 }), { B: 60000 / 154, settleAt: 9000 });
  const p = presses(all);
  assert.deepEqual(p.map((d) => d.control), ["9", "8", "7", "6"]);
  assert.equal(new Set(p.map((d) => d.lineage)).size, 1);
  assert.deepEqual(p.map((d) => d.kind), ["single", "chord", "strum", "strum"]);
  assert.ok(!all.some((d) => d.type === "breath"));
  assert.deepEqual(kinds(all), ["strum:9876"]);
});

test("C+5+3, 6+3+5, 3+4+6 within W: one ensemble lineage each, every order of C+5+3 the same final ensemble", () => {
  const perms = [["C", "5", "3"], ["C", "3", "5"], ["5", "C", "3"], ["5", "3", "C"], ["3", "C", "5"], ["3", "5", "C"]];
  for (const keys of [...perms, ["6", "3", "5"], ["3", "4", "6"]]) {
    const { all } = play(keys.map((k, i) => [1000 + i * 30, k]), { B: 60000 / 154, settleAt: 9000 });
    const p = presses(all);
    assert.deepEqual(p.map((d) => d.control), keys, "the visible singles follow arrival order");
    assert.equal(new Set(p.map((d) => d.lineage)).size, 1, keys.join("+"));
    assert.equal(kinds(all).length, 1);
    assert.deepEqual(kinds(all)[0].split(":")[1].split("").sort(), keys.slice().sort());
    // the ensemble: C asks for one camera composition, transport collapses STOP > NEXT > GO
    const e = new Ensembles();
    const intents = all.flatMap((d) => e.plan(d));
    assert.equal(intents.filter((i) => i.do === "press" && i.control === "C").length, keys.includes("C") ? 1 : 0);
  }
  // releases preserve the remaining holds: let go of 5, 3 and C stay held
  const { g } = play([[0, "C"], [20, "5"], [40, "3"], [300, "5", false]]);
  assert.deepEqual(g.status().sources.key.held.sort(), ["3", "C"]);
});

test("boundaries: W-1 / W / W+1 join, join, single (B = 400: W = 100; B = 500: W = 110 so 109 / 110 / 111)", () => {
  for (const [B, W] of [[400, 100], [500, 110]]) {
    for (const [dt, joined] of [[W - 1, true], [W, true], [W + 1, false]]) {
      const { all } = play([[1000, "1"], [1000 + dt, "5"]], { B, settleAt: 9000 });
      const p = presses(all);
      assert.equal(p[0].lineage === p[1].lineage, joined, `B ${B} dt ${dt}`);
      assert.deepEqual(kinds(all), joined ? ["chord:15"] : ["single:1", "single:5"]);
    }
  }
});

test("boundaries: strum intervals 89 / 90 / 91 ms (B = 240: W = 60, so only the run makes them one)", () => {
  for (const [gap, strum] of [[89, true], [90, true], [91, false]]) {
    const { all } = play(run(["1", "2", "3"], gap, { hold: 300 }), { B: 240, settleAt: 9000 });
    const p = presses(all);
    assert.equal(p.length, 3, "every key spoke on its own call");
    assert.deepEqual(kinds(all), strum ? ["strum:123"] : ["single:1", "single:2", "single:3"], `gap ${gap}`);
    if (strum) {
      const rc = all.find((d) => d.type === "reclassify" && d.to === "strum");
      assert.equal(rc.absorbed.length, 1, "the second key's own lineage merges into the first's");
    }
  }
  // the span: 4 keys at 90 ms is 270 <= 300, all one strum; a fifth at 360 is past the span and starts afresh
  const { all } = play(run(["1", "2", "3", "4", "5"], 90, { hold: 400 }), { B: 240, settleAt: 9000 });
  assert.deepEqual(kinds(all), ["strum:1234", "single:5"]);
});

test("boundaries: the slow sweep's floor 109 / 110 / 111 ms (B = 375: max(110, 0.28 B) = 110)", () => {
  for (const [gap, fade] of [[109, false], [110, true], [111, true]]) {
    const { all } = play(run(["7", "6", "5"], gap), { B: 375, settleAt: 9000 });
    assert.equal(all.some((d) => d.type === "breath" && d.phase === "start"), fade, `gap ${gap}`);
    assert.equal(presses(all).length, fade ? 2 : 3);
  }
  // the ceiling: min(450, 0.95 B) = 356.25 at B = 375
  assert.ok(play(run(["7", "6", "5"], 356), { B: 375 }).all.some((d) => d.type === "breath"));
  assert.ok(!play(run(["7", "6", "5"], 357), { B: 375 }).all.some((d) => d.type === "breath"));
  // the intervening band (between the strum's 90 and the sweep's floor) stays singles
  assert.deepEqual(kinds(play(run(["7", "6", "5"], 100), { B: 240, settleAt: 9000 }).all), ["single:7", "single:6", "single:5"]);
});

test("a sweep ends on a gap over 450 ms or a non-adjacent down; that down is decided as usual; reversal steps the fader", () => {
  const ev = run(["6", "5", "4"], 200);
  // reversal inside the gap: a step up, never a single
  ev.push([1600, "5", true], [1640, "5", false]);
  // a non-adjacent key ends the fade and fires its own single
  ev.push([1800, "9", true], [1840, "9", false]);
  const { per, all } = play(ev.sort((a, b) => a[0] - b[0]), { settleAt: 9000 });
  const br = all.filter((d) => d.type === "breath");
  assert.deepEqual(br.map((d) => d.phase), ["start", "step", "end"]);
  assert.ok(br[1].delta > 0);
  assert.equal(br[2].why, "jump");
  assert.deepEqual(presses(all).map((d) => d.control), ["6", "5", "9"]);
  // past the gap: 451 ms after the last, the next adjacent key is a single again
  const late = play([...run(["6", "5", "4"], 200), [1400 + 451, "3"]].sort((a, b) => a[0] - b[0]), { settleAt: 9000 });
  assert.deepEqual(presses(late.all).map((d) => d.control), ["6", "5", "3"]);
  const ok = play([...run(["6", "5", "4"], 200), [1400 + 450, "3"]].sort((a, b) => a[0] - b[0]), { settleAt: 9000 });
  assert.deepEqual(presses(ok.all).map((d) => d.control), ["6", "5"]);
});

test("0+8, 9+7, 8+6, 7+5, 6+4, 9+7, 7+5, 9+7: one gap-2 walk, the reversal kept, no spurious 3-key chord", () => {
  const pairs = [["0", "8"], ["9", "7"], ["8", "6"], ["7", "5"], ["6", "4"], ["9", "7"], ["7", "5"], ["9", "7"]];
  const ev = [];
  pairs.forEach(([a, b], i) => {
    const t = 1000 + i * 300;
    ev.push([t, a, true], [t + 25, b, true]);
    // the release overlaps the next pair's downs (held 330 ms: a fleeting 3- and 4-key overlap) unless the next pair
    // presses the same key again (a key is let go before it can be pressed again)
    const next = pairs[i + 1] || [];
    ev.push([t + (next.includes(a) ? 280 : 330), a, false], [t + (next.includes(b) ? 290 : 340), b, false]);
  });
  ev.sort((x, y) => x[0] - y[0] || (x[2] === y[2] ? 0 : x[2] ? 1 : -1));
  const { all, g } = play(ev, { B: 400, settleAt: 99999 });
  const w = all.filter((d) => d.type === "walk");
  assert.equal(w[0].phase, "start");
  assert.equal(w.filter((d) => d.phase === "step").length, 6);
  assert.equal(w.filter((d) => d.phase === "end").length, 1);
  assert.equal(w.at(-1).pairs, 8);
  assert.equal(g.counts.walks, 1, "the whole walk is one settled gesture");
  assert.equal(g.counts.chords, 0, "its pairs are not counted again");
  assert.ok(presses(all).every((d) => d.kind !== "strum"));
  assert.equal(new Set(presses(all).map((d) => d.lineage)).size, 8, "eight two-key lineages, none of three");
});

test("a walk pause beyond min(800, 2B), then an unrelated pair: the old walk expires and settles once, the new pair is not captured", () => {
  const ev = [[1000, "9"], [1020, "7"], [1300, "8"], [1320, "6"], [2200, "5"], [2220, "3"]];
  const { all, g } = play(ev, { B: 400, settleAt: 99999 });
  const w = all.filter((d) => d.type === "walk");
  assert.deepEqual(w.map((d) => d.phase), ["start", "end"]);
  assert.equal(w[1].why, "timeout");
  assert.equal(g.counts.walks, 1);
  // the walk's pairs settle labelled with their walk (counted once, as the walk); the new pair is its own chord
  const settles = all.filter((d) => d.type === "settle");
  assert.deepEqual(settles.filter((d) => d.walk).map((d) => d.controls.join("")), ["97", "86"]);
  assert.deepEqual(settles.filter((d) => !d.walk).map((d) => `${d.kind}:${d.controls.join("")}`), ["chord:53"]);
  assert.equal(g.counts.chords, 1);
});

test("3,3,3,1 (no combos in this slice): every press keeps its single, nothing is deferred, auto-repeat never presses", () => {
  const ev = [[0, "3"], [50, "3", false], [300, "3"], [350, "3", false], [600, "3"], [650, "3", false], [900, "1"], [950, "1", false]];
  const { all } = play(ev, { settleAt: 9000 });
  assert.deepEqual(presses(all).map((d) => d.control), ["3", "3", "3", "1"]);
  // OS auto-repeat: keydowns of a held key, repeated, are ignored; the release is one
  const r = play([[0, "1"], [500, "1"], [530, "1"], [560, "1"], [600, "1", false]], { settleAt: 9000 });
  assert.equal(presses(r.all).length, 1);
  assert.equal(r.g.counts.repeats, 3);
  assert.equal(r.all.filter((d) => d.type === "release").length, 1);
  // a utility key never enters the grammar (the page routes F / H / L / P directly), so it cannot join a chord
});

test("releases go by press id: an old session's release cannot end a new press on the same control", () => {
  const g = new Grammar();
  g.input({ source: "phone", control: "1", down: true, t: 0, id: "s1-a" });
  g.input({ source: "phone", control: "1", down: false, t: 100, id: "s1-a" });
  g.input({ source: "phone", control: "1", down: true, t: 200, id: "s2-a" });
  const stale = g.input({ source: "phone", control: "1", down: false, t: 250, id: "s1-a" });
  assert.deepEqual(stale, []);
  assert.deepEqual(g.status().sources.phone.held, ["1"]);
  assert.equal(g.input({ source: "phone", control: "1", down: false, t: 300, id: "s2-a" })[0].dispatched, true);
});

test("blur / cancel: the source's presses let go, its prefixes are abandoned; another source plays on", () => {
  const g = new Grammar({ beatMs: () => 400 });
  for (const [t, c] of [[0, "6"], [200, "5"]]) g.input({ source: "key", control: c, down: true, t });
  g.input({ source: "midi", control: "1", down: true, t: 250 });
  const out = g.cancel("key", 300);
  assert.deepEqual(out.filter((d) => d.type === "release").map((d) => d.control).sort(), ["5", "6"]);
  // the run's prefix is gone: a 4 at 400 ms is a single, not the sweep's third key
  const after = g.input({ source: "key", control: "4", down: true, t: 400 });
  assert.equal(presses(after).length, 1);
  assert.deepEqual(g.status().sources.midi.held, ["1"]);
  // a cancel during an explicit B ends the fade there (no stuck modifier)
  const h = new Grammar();
  h.input({ source: "key", control: "B", down: true, t: 0 });
  h.input({ source: "key", control: "9", down: true, t: 10 });
  assert.ok(h.cancel("key", 20).some((d) => d.type === "breath" && d.phase === "end" && d.why === "cancel"));
  assert.equal(presses(h.input({ source: "key", control: "9", down: true, t: 30 })).length, 1);
});

test("source-local: a phone tap and a key 30 ms apart are two singles; the phone and the KeyLab chord but never strum or sweep", () => {
  const { all } = play([[0, "1", true, "key"], [30, "5", true, "phone"]], { settleAt: 9000 });
  assert.equal(new Set(presses(all).map((d) => d.lineage)).size, 2);
  const ph = play(run(["9", "8", "7", "6"], 39, { source: "phone", hold: 200 }), { settleAt: 9000 });
  assert.ok(!ph.all.some((d) => d.type === "reclassify" && d.to === "strum"));
  const pm = play(run(["9", "8", "7", "6"], 180, { source: "midi" }), { settleAt: 9000 });
  assert.equal(presses(pm.all).length, 4);
  assert.ok(!pm.all.some((d) => d.type === "breath"));
  assert.deepEqual(kinds(play([[0, "1", true, "midi"], [40, "5", true, "midi"]], { settleAt: 9000 }).all), ["chord:15"]);
});

test("a tempo change never reclassifies keys already played (W frozen when the lineage began)", () => {
  let B = 400;
  const g = new Grammar({ beatMs: () => B });
  g.input({ source: "key", control: "1", down: true, t: 0 });
  B = 240;                                                                // W would be 60 now
  const d = g.input({ source: "key", control: "5", down: true, t: 95 });
  assert.equal(presses(d)[0].kind, "chord");
  // no clock: 400 ms
  const n = new Grammar({ beatMs: () => null });
  n.input({ source: "key", control: "1", down: true, t: 0 });
  assert.equal(presses(n.input({ source: "key", control: "5", down: true, t: 100 }))[0].kind, "chord");
});

// ------------------------------------------------------------------------------------------------- the ensembles --
test("ensemble: a chord's later kick joins the first's attack at its age (no second punch); a single keeps its own", () => {
  const e = new Ensembles();
  const { all } = play([[0, "1"], [39, "5"], [2000, "1", false], [2000, "5", false], [3000, "5"]], { settleAt: 9000 });
  const recs = [];
  for (const d of all) for (const it of e.plan(d)) if (it.do === "press") {
    const rec = { punchFrom: recs.length === 0 ? 10.0 : recs.length === 1 ? 10.1 : 20.0 };
    recs.push(rec); e.attack(it.lineage, rec);
  }
  assert.deepEqual(recs.map((r) => r.punchFrom), [10.0, 10.0, 20.0]);
  assert.equal(e.stats.attacks, 2); assert.equal(e.stats.joined, 1);
  // a refused punch (the governor: -Infinity) is the lineage's identity too: the member gets none either
  const f = new Ensembles(), r1 = { punchFrom: -Infinity }, r2 = { punchFrom: 5 };
  f.attack("x", r1); f.attack("x", r2);
  assert.equal(r2.punchFrom, -Infinity);
});

test("ensemble: transport collapses STOP > NEXT > GO once per lineage; a strum's absorbed lineage shares the attack", () => {
  const e = new Ensembles();
  const go = (control, lineage, member = 0, kind = "chord") => e.plan({ type: "press", control, lineage, member, kind, velocity: 0.8 });
  assert.equal(go("3", "L")[0].do, "press");
  assert.equal(go("7", "L", 1)[0].do, "press");          // STOP over a GO: the higher one speaks
  assert.equal(go("4", "L", 2)[0].do, "skip");           // NEXT after STOP: collapsed
  assert.equal(TRANSPORT_RANK["7"] > TRANSPORT_RANK["4"], true);
  const s = new Ensembles(), a = { punchFrom: 1 }, b = { punchFrom: 2 }, c = { punchFrom: 3 };
  s.attack("L1", a); s.attack("L2", b);
  s.plan({ type: "reclassify", lineage: "L1", from: "single", to: "strum", absorbed: ["L2"], t: 0 });
  s.attack("L2", c);                                     // a late member of the absorbed lineage
  assert.equal(c.punchFrom, 1);
});

test("ensemble: BREATH anchors at the current level, ramps one step per 120 ms, latches, hands back over four beats", () => {
  const e = new Ensembles();
  const { all } = play(run(["8", "7", "6", "5", "4"], 200), { settleAt: 9000 });
  let t = 0;
  const path = [];
  const byT = all.filter((d) => d.type === "breath").sort((a, b) => a.t - b.t);
  for (let ms = 1000; ms <= 3500; ms += 10) {
    while (byT.length && byT[0].t <= ms) for (const it of e.plan(byT.shift())) void it;
    e.tick(ms); path.push(e.level);
    t = ms;
  }
  assert.ok(Math.abs(e.level - 5 / 9) < 1e-9, `latched at ${e.level}`);
  // monotonic, never faster than one step per 120 ms
  for (let i = 1; i < path.length; i++) { assert.ok(path[i] <= path[i - 1] + 1e-12); assert.ok(path[i - 1] - path[i] <= (1 / 9) * (10 / 120) + 1e-9); }
  // the layer: the look's dimmers scale, nothing else
  const tH = new Float64Array(14).fill(0.5), tC = new Float64Array(8).fill(0.5);
  chainLayers({ apply: (h) => { h[0] = 7; } }, e).apply(tH, tC, 0);
  assert.equal(tH[0], 7); assert.ok(Math.abs(tH[2] - 0.5 * 5 / 9) < 1e-9); assert.equal(tH[3], 0.5);
  assert.ok(Math.abs(tC[0] - 0.5 * 5 / 9) < 1e-9); assert.equal(tC[1], 0.5);
  // Esc: back to 1 over four beats (at 400 ms: 1.6 s), from where it is
  e.handBack(t, 400);
  e.tick(t + 800); assert.ok(Math.abs(e.level - (5 / 9 + (4 / 9) * 0.5)) < 1e-9);
  e.tick(t + 1600); assert.equal(e.level, 1);
  // a sweep's start asks to withdraw its first two keys' pending commands
  const f = new Ensembles();
  const start = all.find((d) => d.type === "breath" && d.phase === "start");
  assert.deepEqual(f.plan(start).filter((i) => i.do === "cancel").map((i) => i.control), ["8", "7"]);
});

// ------------------------------------------------------------------------------- the review's findings (2026-10-29) --
// a recogniser wired to an ensemble the way stage.js wires it (canFade reads the fade's target); every decision planned
function coupled({ B = 400 } = {}) {
  const e = new Ensembles();
  const g = new Grammar({ beatMs: () => B, canFade: (dir) => e.canFade(dir) });
  const per = [];
  const feed = (t, control, down = true) => {
    const ds = [...g.settle(t), ...g.input({ source: "key", control, down, t, velocity: 0.8, ...(down ? { id: `${control}@${t}` } : {}) })];
    for (const d of ds) e.plan(d);
    if (down) per.push({ t, control, down, ds });
    return ds;
  };
  // a tap: down, and up 30 ms later (only the downs are kept in per)
  const tap = (t, control) => { const ds = feed(t, control); feed(t + 30, control, false); return ds; };
  return { e, g, per, feed, tap };
}

test("F1: a chord never adds a punch -- a refused member stays refused, a re-strike member keeps its old punch", () => {
  // first granted, second refused by the flash governor (kick.js: punchFrom -Infinity)
  const e = new Ensembles(), a = { punchFrom: 8.0417, presses: 1 }, b = { punchFrom: -Infinity, presses: 1 };
  e.attack("g1", a); e.attack("g1", b);
  assert.equal(b.punchFrom, -Infinity, "the governor's refusal must stand");
  // the chord 1 + 5 where 5 is still lit from a tap 0.6 beat earlier: a re-strike, whose punch counts from its first press
  const f = new Ensembles(), w = { punchFrom: 8.625, presses: 1 }, c = { punchFrom: 8.0417, presses: 2 };
  f.attack("g1", w); f.attack("g1", c);
  assert.equal(c.punchFrom, 8.0417, "a re-strike must not get a fresh punch from the chord");
  // a fresh later member still joins at its age (older, never newer)
  const h = new Ensembles(), x = { punchFrom: 10, presses: 1 }, y = { punchFrom: 10.1, presses: 1 };
  h.attack("g", x); h.attack("g", y);
  assert.equal(y.punchFrom, 10);
});

test("F8b: a re-strike first in a chord is not the chord's attack: the first FRESH kick is, and keeps its own punch", () => {
  const e = new Ensembles(), r = { punchFrom: 5, presses: 3 }, k1 = { punchFrom: 10, presses: 1 }, k2 = { punchFrom: 10.05, presses: 1 };
  assert.equal(e.attack("g", r).restrike, true);
  assert.equal(r.punchFrom, 5);
  assert.equal(e.attack("g", k1).own, true);
  assert.equal(k1.punchFrom, 10, "the fresh kick keeps its punch");
  e.attack("g", k2);
  assert.equal(k2.punchFrom, 10);
  assert.equal(e.stats.attacks, 1); assert.equal(e.stats.restrikes, 1);
});

test("F2: a mash 4 5 6 (a strum) and then 1 inside W is ONE gesture: 1 joins the strum's lineage (one attack)", () => {
  for (const order of [["4", "5", "6"], ["6", "5", "4"]]) {
    const { all } = play([[1000, order[0]], [1003, order[1]], [1006, order[2]], [1010, "1"]], { settleAt: 9000 });
    const ls = new Set(presses(all).map((d) => d.lineage));
    assert.equal(ls.size, 1, `${order.join("")} + 1: ${[...ls]}`);
    assert.deepEqual(kinds(all), [`strum:${order.join("")}1`]);
  }
  // outside W the key is its own gesture, as before
  const { all } = play([[1000, "4"], [1003, "5"], [1006, "6"], [1150, "1"]], { settleAt: 9000 });
  assert.equal(new Set(presses(all).map((d) => d.lineage)).size, 2);
});

test("F4: a slow run that cannot move the fade is ordinary playing -- 1 2 3 4 5 in eighths at full level all fire", () => {
  const { e, per, tap } = coupled({ B: 60000 / 154 });
  for (const [i, k] of ["1", "2", "3", "4", "5"].entries()) tap(1000 + i * 195, k);
  assert.deepEqual(per.map((p) => presses(p.ds).map((d) => d.control).join("")), ["1", "2", "3", "4", "5"]);
  assert.equal(e.breath.target, 1);
  // the same run DOWN the row does fade (the target can move), and back up ascends to full and no further:
  // 9 8 7 (start, -2/9), 8, 9 (+1/9 each: back to 1), then 0 cannot move it: the sweep ends and 0 fires DROP
  const c = coupled({ B: 400 });
  for (const [i, k] of ["9", "8", "7", "8", "9", "0"].entries()) c.tap(5000 + i * 200, k);
  assert.deepEqual(c.per.map((p) => presses(p.ds).map((d) => d.control).join("")), ["9", "8", "", "", "", "0"]);
  assert.ok(Math.abs(c.e.breath.target - 1) < 1e-9);
  assert.ok(c.per[5].ds.some((d) => d.type === "breath" && d.phase === "end" && d.why === "limit"));
});

test("F4: at black, a run down the row fires its keys (nothing left to fade); a run up still fades in", () => {
  const { e, per, feed, tap } = coupled({ B: 400 });
  feed(1000, "B");
  for (const [i, k] of ["9", "8", "7", "6", "5", "4", "3", "2", "1"].entries()) tap(1100 + i * 50, k);
  feed(1600, "B", false);
  // a single 1/9 above black: one more step down is possible, then nothing
  assert.ok(Math.abs(e.breath.target - 1 / 9) < 1e-9);
  const before = per.length;
  for (const [i, k] of ["4", "3", "2", "1"].entries()) tap(3000 + i * 200, k);
  const got = per.slice(before).map((p) => presses(p.ds).map((d) => d.control).join(""));
  // 4, 3 fire; 2 takes over (-2/9 floors at 0); 1 cannot move a black room further: it fires
  assert.deepEqual(got, ["4", "3", "", "1"]);
  assert.equal(e.breath.target, 0);
  const up0 = per.length;
  for (const [i, k] of ["2", "3", "4"].entries()) tap(6000 + i * 200, k);
  assert.deepEqual(per.slice(up0).map((p) => presses(p.ds).length), [1, 1, 0]);
  assert.ok(e.breath.target > 0);
});

test("F6: a key handled after a frame's settle, stamped inside W, still joins the chord (the settle keeps a slack)", () => {
  // the phone and the KeyLab (no number-row runs keep the lineage open) and the keyboard's C: W = 100 at B = 400
  for (const [source, first, second] of [["phone", "1", "5"], ["midi", "1", "5"], ["key", "C", "5"]]) {
    const g = new Grammar({ beatMs: () => 400 });
    g.input({ source, control: first, down: true, t: 1000 });
    g.settle(1105);                                                   // the frame ran first, 5 ms past W
    const d = g.input({ source, control: second, down: true, t: 1095 });
    assert.equal(presses(d)[0].kind, "chord", `${source} ${first}+${second}`);
    // past W the key is still its own single
    const h = new Grammar({ beatMs: () => 400 });
    h.input({ source, control: first, down: true, t: 1000 });
    h.settle(1105);
    assert.equal(presses(h.input({ source, control: second, down: true, t: 1101 }))[0].kind, "single");
  }
});
