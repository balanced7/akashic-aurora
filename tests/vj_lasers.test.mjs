// Node tests for the laser engine (arsenal/web/vj-lasers.js). Zero dependencies, no GPU:
//   node --test tests/vj_lasers.test.mjs        (or: node tests/vj_lasers.test.mjs)
//
// Daniel, 2026-10-24: "did we update the lasor to have more permutations and to have different effects depending on the
// rapidness of retrigger? also do we have multiple start locations beyond the 3, i want us to have two banks of laser."
// The receipts, from the build spec (research/reviewed/keylab-liberation-2026-10-22/vj-lasers-v2-and-colour-themes-
// 2026-10-24.md): A1 variety over 32 hits, A2 gate timing against a beat clock (fake clocks here, plus the page's own
// BeatClock), A5a flash safety from the lasers' own geometry (the change estimator, and the verifier's additive raster of
// the overlay's light model at 960 x 540 and 1920 x 1080 with sliding windows). Also: the two banks and their modes, the
// retrigger tiers, Vibrate's decay, the shapes' geometry, the output format, determinism. The tests marked "Round-1 fix"
// are the verifier's must-fix repros: each failed against the round-0 engine and passes now; "Round-2 fix" likewise
// against the round-1 engine (A5-style runs across the theme library, figures under loop dials, realistic mashing);
// "Round 3" against the round-2 engine (a new hit plays alone; the acceptance runs draw fresh seeds every run).
// Every number here is synthetic: nothing reads Daniel's playing. (The whole file takes about six minutes.)
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import * as L from "../arsenal/web/vj-lasers.js";
import { BeatClock } from "../arsenal/web/vj-core.js";

const F = 1000 / 60;

// -------------------------------------------------------------------------------------------------- the themes --
// From the v2 theme library in the spec (verbatim fields that a laser reads).
const THEMES = {
  "night-sea": L.DEFAULT_THEME,
  "laser-green": { id: "laser-green", A: "#05d987", B: "#72ba4f", W: "#c33661", beam: { A: "#29d889", B: "#72ba4f" },
    lasers: ["A", "B"], strobe: { triple: ["A", "A", "W"], flicker: ["A", "B"] }, burst: ["A", "B", "W"], held: [], split_only: false },
  "golden-wings": { id: "golden-wings", A: "#e89029", B: "#5435d9", W: "#f9e5c5", beam: { A: "#e89029", B: "#6d5bf9" },
    lasers: ["A"], strobe: { triple: ["A", "A", "W"], flicker: ["A", "W"] }, burst: ["A", "W"], held: [], split_only: false },
  "acid-screech": { id: "acid-screech", A: "#a8ff24", B: "#4a00e0", W: "#ffffff", beam: { A: "#8ed726", B: "#685df9" },
    lasers: ["A", "B"], strobe: { triple: ["A", "A", "W"], flicker: ["A", "B"] }, burst: ["A", "W"], held: [], split_only: true },
  limbo: { id: "limbo", A: "#eef4ff", B: "#4fa8ff", W: "#ff1a3c", beam: { A: "#eef4ff", B: "#55a8fb" }, lasers: ["A"],
    strobe: { triple: ["A", "A", "A"], flicker: ["A", "B"] }, burst: ["A", "B"], held: ["W"], split_only: false },
  "red-tribe": { id: "red-tribe", A: "#db0001", B: "#e89029", W: "#fbfcfc", beam: { A: "#e11c14", B: "#e89029" },
    lasers: ["B", "W"], strobe: { triple: ["B", "B", "W"], flicker: ["B", "W"] }, burst: ["B", "W"], held: ["A"], split_only: false },
};

// -------------------------------------------------------------------------------------------------- the clocks --
// A steady clock: beats at t0 + k * period. posAt is optional (the page's BeatClock has none).
function steadyClock(bpm, { t0 = 0, posAt = true, conf = 1 } = {}) {
  const per = 60000 / bpm;
  const c = { bpm, conf, phaseAt: (t) => { const x = (t - t0) / per; return x - Math.floor(x); },
    nextBeatAt: (t) => t0 + Math.ceil((t - t0) / per - 1e-12) * per };
  if (posAt) c.posAt = (t) => (t - t0) / per;
  return c;
}
// A tempo ramp: bpm0 until tA, linear to bpm1 over rampMs, then bpm1. pos integrates the tempo. `now` is advanced by the
// driver so that `bpm` reads the tempo of the moment.
function rampClock(bpm0, bpm1, tA, rampMs) {
  const posAt = (t) => {
    if (t <= tA) return t * bpm0 / 60000;
    const r = Math.min(t - tA, rampMs);
    let p = tA * bpm0 / 60000 + r * (bpm0 + (bpm1 - bpm0) * r / (2 * rampMs)) / 60000;
    if (t > tA + rampMs) p += (t - tA - rampMs) * bpm1 / 60000;
    return p;
  };
  const c = { now: 0, conf: 1, posAt, phaseAt: (t) => { const p = posAt(t); return p - Math.floor(p); }, nextBeatAt: () => null };
  Object.defineProperty(c, "bpm", { get: () => (c.now <= tA ? bpm0 : c.now >= tA + rampMs ? bpm1 : bpm0 + (bpm1 - bpm0) * (c.now - tA) / rampMs) });
  c.timeOf = (P) => { let lo = 0, hi = 1e7; for (let i = 0; i < 80; i++) { const m = (lo + hi) / 2; if (posAt(m) < P) lo = m; else hi = m; } return hi; };
  return c;
}

// Drive an engine at 60 frames a second from `from` to `to`, applying timed events. onFrame(out, t, j) sees each frame;
// a pulse's presentation time is t + presentLag (one frame).
function drive(eng, events, { from, to, onFrame = null, clock = null }) {
  const ev = events.slice().sort((a, b) => a.t - b.t);
  let ei = 0;
  for (let j = 0; ; j++) {
    const t = from + j * F;
    if (t > to) break;
    if (clock && "now" in clock) clock.now = t;
    while (ei < ev.length && ev[ei].t <= t) { const e = ev[ei++]; e.fn(eng, e.t); }
    const out = eng.frame(t);
    if (onFrame) onFrame(out, t, j);
  }
}
const tap = (t, vel, hold = 60) => [{ t, fn: (e, x) => e.hit(x, vel) }, { t: t + hold, fn: (e, x) => e.release(x) }];
const mulberry = (s) => L.mulberry32(s);
// the output's line records, decoded by the module's reference decoder (group headers skipped): fn(record, row, head)
const DEC = {};
function eachLine(out, fn) { for (let i = 0; i < out.n; i++) { const r = L.decodeSeg(out.seg, i, DEC); if (!r.header) fn(r, i, out.head[i]); } }
const pulseTimes = (onsets) => onsets.map((o) => o.t);

// ------------------------------------------------------------------------------------------- 1. the two banks --
test("two banks of 8, two towers, the hero: 21 distinct start locations, all on screen", () => {
  assert.equal(L.BANK_A.length, 8);
  assert.equal(L.BANK_B.length, 8);
  assert.equal(L.SIDE_HEADS.length, 4);
  assert.equal(L.HEADS[L.HERO_HEAD].name, "HERO");
  const names = new Set(L.HEADS.map((h) => h.name));
  assert.equal(names.size, L.HEADS.length);
  const spots = new Set(L.HEADS.map((h) => `${h.u.toFixed(3)},${h.y.toFixed(3)}`));
  assert.ok(spots.size >= 16, `distinct start locations: ${spots.size}`);
  for (const i of L.BANK_A) assert.ok(L.HEADS[i].y > 0.4, "Bank A hangs along the top");
  for (const i of L.BANK_B) assert.ok(L.HEADS[i].y < -0.4, "Bank B stands along the bottom");
  for (const asp of [16 / 9, 4 / 3]) for (const h of L.HEADS) {
    assert.ok(Math.abs(h.u * asp / 2) < asp / 2 && Math.abs(h.y) < 0.5, `${h.name} inside a ${asp.toFixed(2)} frame`);
  }
  for (const h of L.HEADS) {
    assert.ok(L.HEADS[h.twin] && Math.abs(L.HEADS[h.twin].u + h.u) < 1e-9, `${h.name} has a mirror twin`);
    if (h.bank === "A" || h.bank === "B") assert.equal(L.HEADS[L.HEADS[h.flip].flip].index, h.index, `${h.name} has a twin in the other bank`);
    assert.ok(h.pad >= 1 && h.pad <= 12);
  }
});

// --------------------------------------------------------------------------------- 2. A1: variety over 32 hits --
// The spec's fixture: 32 pad-2 presses on a 150 BPM clock, 8 in an anti-climax, 8 in a build, 16 in a climax; velocities
// from a fixed list covering all three tiers; 6 second presses and 2 holds.
const VELS = [0.3, 0.62, 0.92, 0.5, 0.85, 0.2, 0.7, 0.95, 0.4, 0.66, 0.88, 0.35, 0.75, 0.55, 0.98, 0.25];
function a1Run({ seed = 11, theme = THEMES["night-sea"], variety = 1, vibrate = false } = {}) {
  const per = 400, clk = steadyClock(150);
  const eng = L.createLaserEngine({ seed, clock: clk, theme, variety, vibrate });
  const events = [];
  const second = new Set([3, 11, 12, 19, 25, 30]);         // second presses (2.5 beats after the previous one)
  const holds = new Set([14, 27]);                          // held for 3 beats
  let t = 2000;
  const sectionAt = (i) => (i < 8 ? "anti" : i < 16 ? "build" : "climax");
  for (let i = 0; i < 32; i++) {
    if (i > 0) t += second.has(i) ? 2.5 * per : 8 * per;
    const s = sectionAt(i), ti = t;
    if (i === 0 || sectionAt(i - 1) !== s) events.push({ t: ti - 1, fn: (e) => e.setSection(s) });
    events.push(...tap(ti, VELS[i % VELS.length], holds.has(i) ? 3 * per : 60));
  }
  const frames = [];
  let hash = 0x811c9dc5 | 0, red = 0, maxW = 0;
  drive(eng, events, { from: 1500, to: t + 3000, onFrame: (out) => {
    for (let k = 0; k < out.n * L.SEG_FLOATS; k++) hash = Math.imul(hash ^ (Math.round(out.seg[k] * 1e5) | 0), 0x01000193);
    eachLine(out, (r) => { if (r.I > 0.002 && L.isSaturatedRed([r.r, r.g, r.b])) red++; });
    maxW = Math.max(maxW, out.area.window);
  } });
  const presses = eng.log.filter((x) => x.tier !== "held" && !x.ext);
  return { eng, presses, all: eng.log, hash, red, maxW, frames, sectionAt };
}

test("A1: 32 presses never show the same combination twice, and every axis varies", () => {
  const { presses, all, red } = a1Run();
  assert.equal(presses.length, 32);
  const sigs = presses.map((p) => p.sig);
  assert.equal(new Set(sigs).size, 32, "distinct combinations over 32 consecutive presses");
  const axes = ["pattern", "gate", "order", "colour", "start"];
  for (let i = 1; i < presses.length; i++) {
    const d = axes.filter((k) => presses[i][k] !== presses[i - 1][k]).length;
    assert.ok(d >= 2, `presses ${i - 1} and ${i} differ on ${d} axes`);
  }
  const count = (k, list = presses) => new Set(list.map((p) => p[k])).size;
  const gates = new Set(all.map((p) => p.gate));
  console.log(`  A1: ${count("pattern")} patterns, ${gates.size} gates (${[...gates].join(" ")}), ${count("order")} orders, ` +
    `${count("colour")} colour modes, ${count("start")} start heads, ${count("bank")} banks over 32 presses`);
  assert.ok(count("pattern") >= 8, `patterns ${count("pattern")}`);
  assert.ok(gates.size >= 6, `gates ${gates.size}`);
  assert.ok(count("order") >= 6, `orders ${count("order")}`);
  assert.ok(count("colour") >= 5, `colour modes ${count("colour")}`);
  assert.ok(count("start") >= 12, `start heads ${count("start")}`);
  assert.equal(red, 0, "no saturated red emitted");
});

test("A1: every hit is legal for its section and theme; heroes are at most 1 in 6", () => {
  const { presses, sectionAt } = a1Run({ theme: THEMES["acid-screech"] });
  presses.forEach((p, i) => {
    const P = L.PATTERNS[p.pattern];
    if (!p.hero) assert.ok(P.sections === "all" || P.sections.includes(sectionAt(i)), `${p.pattern} in ${sectionAt(i)}`);
    assert.ok(!["split", "gradient", "headgrad"].includes(p.colour), `split-only theme never blends (${p.colour})`);
  });
  const heroes = presses.map((p, i) => (p.hero ? i : -1)).filter((i) => i >= 0);
  assert.ok(heroes.length >= 1 && heroes.length <= Math.ceil(32 / 6), `heroes ${heroes.length}`);
  for (let i = 1; i < heroes.length; i++) assert.ok(heroes[i] - heroes[i - 1] >= 6, "heroes 6 hits apart");
  for (const p of presses.filter((x) => x.hero)) assert.ok(["crown", "star", "bloom"].includes(p.pattern));
});

test("A1: the same seed gives byte-identical hits and frames; another seed differs; Variety 0 repeats one hit", () => {
  const a = a1Run({ seed: 5 }), b = a1Run({ seed: 5 }), c = a1Run({ seed: 6 });
  assert.equal(JSON.stringify(a.all), JSON.stringify(b.all));
  assert.equal(a.hash, b.hash, "frames bit for bit");
  assert.notEqual(JSON.stringify(a.presses.map((p) => p.sig)), JSON.stringify(c.presses.map((p) => p.sig)));
  const z = a1Run({ variety: 0 });
  assert.equal(new Set(z.presses.map((p) => p.sig)).size, 1, "Variety 0: 32 identical signatures");
  const half = a1Run({ variety: 0.5 });
  const n = new Set(half.presses.map((p) => p.sig)).size;
  assert.ok(n > 1 && n <= 32);
});

test("start locations: auto banks spread the starts over at least 16 of the 21 heads in 64 presses", () => {
  const clk = steadyClock(150);
  const eng = L.createLaserEngine({ seed: 21, clock: clk, section: "climax" });
  const ev = [];
  for (let i = 0; i < 64; i++) ev.push(...tap(2000 + i * 8 * 400, VELS[i % VELS.length]));
  drive(eng, ev, { from: 1900, to: 2000 + 64 * 8 * 400 });
  const starts = new Set(eng.log.map((x) => x.start));
  const banks = new Set(eng.log.map((x) => x.bank));
  console.log(`  starts: ${starts.size} distinct heads; banks: ${[...banks].join(" ")}`);
  assert.ok(starts.size >= 16, `distinct starts ${starts.size}`);
  for (const b of ["A", "B", "both", "call", "mirror"]) assert.ok(banks.has(b), `bank mode ${b} dealt`);
});

// ------------------------------------------------------------------------------------- 3. the retrigger tiers --
function tierRun(presses, { section = "any", bpm = 150, opts = {} } = {}) {
  const per = 60000 / bpm, clk = steadyClock(bpm);
  const eng = L.createLaserEngine({ seed: 3, clock: clk, section, ...opts });
  const ev = [];
  for (const p of presses) ev.push(...tap(2000 + p.beat * per, p.vel ?? 0.6, (p.hold ?? 0.15) * per));
  const end = 2000 + Math.max(...presses.map((p) => p.beat + (p.hold ?? 0))) * per + 8 * per;
  const onsets = [];
  drive(eng, ev, { from: 1900, to: end, onFrame: (out, t) => { for (const e of out.events) if (e.type === "pulse") onsets.push({ t: t + F, hit: e.hit, k: e.k }); } });
  return { eng, log: eng.log, onsets, per };
}

test("tiers: slow = burst; within a bar = escalate, then a crown from the hero; a bar of rest settles it", () => {
  const { log } = tierRun([{ beat: 0 }, { beat: 6 }, { beat: 8.5 }, { beat: 11 }, { beat: 17 }, { beat: 19.5 }, { beat: 22 }]);
  const t = log.map((x) => x.tier);
  assert.deepEqual(t.slice(0, 4), ["burst", "burst", "escalate", "hero"]);
  assert.equal(log[2].level, 2);
  assert.ok(log[2].heads.length >= 2, "tier 2 lights more heads");
  assert.ok(["split", "gradient", "halves", "chase", "flip", "trinity", "headgrad", "burst", "barswap"].includes(log[2].colour), "tier 2: a second colour");
  assert.ok(["crown", "star", "bloom"].includes(log[3].pattern) && log[3].hero);
  assert.ok(log[3].pattern === "bloom" || log[3].start === "HERO", "the hero fires from the centre");
  assert.equal(t[4], "burst", "after more than a bar of rest it settles back");
  assert.equal(log[4].level, 1);
  assert.equal(t[6], "escalate", "the next third press is held back to tier 2 (fewer than 6 hits since the hero)");
});

test("tiers: within a beat = a one-two flicker; an eighth or faster = a strobe roll locked to the grid", () => {
  const a = tierRun([{ beat: 0 }, { beat: 0.8 }]);
  assert.equal(a.log[1].tier, "flicker");
  assert.equal(a.log[1].gate, "onetwo");
  const b = tierRun([{ beat: 0 }, { beat: 0.5 }, { beat: 1.0 }, { beat: 1.3 }, { beat: 1.6 }, { beat: 1.9 }]);
  const rolls = b.log.filter((x) => x.tier === "rapid");
  assert.equal(rolls[0].gate, "roll8");
  assert.ok(rolls.slice(1).every((x) => x.ext && x.id === rolls[0].id), "rapid presses extend one roll");
  assert.equal(rolls[rolls.length - 1].gate, "roll16", "faster presses tighten the roll to 16ths");
  // the roll's pulses sit on the grid (never late, at most a frame early)
  const rollOn = b.onsets.filter((o) => o.hit === rolls[0].id);
  assert.ok(rollOn.length >= 4, `roll pulses ${rollOn.length}`);
  for (const o of rollOn.slice(1)) {
    const beats = (o.t - 2000) / b.per, grid = Math.round(beats * 4) / 4, err = o.t - (2000 + grid * b.per);
    assert.ok(err <= 0.01 && err >= -F - 0.01, `roll pulse ${err.toFixed(2)} ms from the 16th grid`);
  }
});

// Round-1 fix (verifier, must fix 3): the tier edges sat exactly ON the musical divisions, so human taps flipped tiers:
// eighth-note taps with 10-20 ms of jitter gave 18 flickers / 11 new rolls / 2 extensions (each flicker choked the
// roll), quarter notes 13 flicker / 13 escalate / 5 hero, one tap a bar 18 burst / 11 escalate / 2 hero.
test("tiers: jittered human taps keep their tier (8ths one roll, 16ths a 16th roll, beats flicker, bars escalate)", () => {
  const gaussRng = (seed) => { const r = mulberry(seed); return () => { let u = 0; for (let i = 0; i < 6; i++) u += r(); return (u - 3) / Math.sqrt(0.5); }; };
  const cases = [
    ["16ths", 0.25, (t) => t.every((x) => x.tier === "rapid") && t.at(-1).gate === "roll16"],
    ["8ths", 0.5, (t) => t.every((x) => x.tier === "rapid") && t.filter((x) => !x.ext).length === 1],
    ["quarters", 1, (t) => t.every((x) => x.tier === "flicker")],
    ["half notes", 2, (t) => t.every((x) => x.tier === "escalate" || x.tier === "hero")],
    ["one a bar", 4, (t) => t.every((x) => x.tier === "escalate" || x.tier === "hero")],
    ["one in 2 bars", 8, (t) => t.every((x) => x.tier === "burst")],
  ];
  const rows = [];
  for (const bpm of [128, 150, 180]) for (const sd of [10, 20]) for (const [name, div, ok] of cases) {
    const per = 60000 / bpm, g = gaussRng(bpm * 100 + sd);
    const eng = L.createLaserEngine({ seed: 3, clock: steadyClock(bpm) });
    const ev = [];
    for (let i = 0; i < 32; i++) { const t = 2000 + i * div * per + g() * sd; ev.push(...tap(t, 0.8, 50)); }
    drive(eng, ev, { from: 1990, to: 2000 + 33 * div * per });
    const t = eng.log.filter((x) => x.tier !== "held").slice(1);
    const counts = {};
    for (const x of t) { const k = x.ext ? "rapid+ext" : x.tier; counts[k] = (counts[k] || 0) + 1; }
    rows.push(`${bpm}/${sd}ms ${name}: ${JSON.stringify(counts)}`);
    assert.equal(t.length, 31, `${bpm} BPM ${name}: 31 presses after the first`);
    assert.ok(ok(t), `${bpm} BPM, ${sd} ms jitter, ${name}: ${JSON.stringify(counts)}`);
  }
  console.log(`  ${rows.filter((r, i) => i % 6 === 1).join("; ")}`);
});

// Round-1 fix (verifier, must fix 1): with the dial on a short gate, three presses inside an eighth note threw
// "Cannot read properties of null (reading 'endP')" from the rapid branch (it assumed the earlier rapid hit had a loop).
test("rapid presses with the dial on any gate never throw; a short-gate dial fires its own gate on every press", () => {
  for (const g of L.GATE_IDS) {
    const eng = L.createLaserEngine({ seed: 7, clock: steadyClock(150), gateMode: g });
    const infos = [];
    assert.doesNotThrow(() => {
      for (const t of [1000, 1150, 1300, 1450, 1520]) { infos.push(eng.hit(t, 0.8)); eng.release(t + 30); eng.frame(t + 40); }
      for (let t = 1560; t < 4000; t += F) eng.frame(t);
    }, `dial ${g}`);
    if (L.GATES[g].kind === "short") assert.ok(infos.every((x) => x.gate === g && !x.ext), `dial ${g}: every press fires ${g} (${infos.map((x) => x.gate)})`);
    else assert.ok(infos.slice(1).some((x) => x.ext), `dial ${g}: rapid presses extend the running loop`);
  }
  // the verifier's repro, verbatim
  const e = L.createLaserEngine({ clock: steadyClock(150), gateMode: "single" });
  assert.doesNotThrow(() => { e.hit(1000); e.hit(1150); e.hit(1300); });
  // the dial turned to a short gate while an auto roll runs; a press with no usable time
  const m = L.createLaserEngine({ clock: steadyClock(150) });
  assert.doesNotThrow(() => {
    m.hit(1000, 0.8); m.hit(1100, 0.8); m.frame(1110); m.set({ gateMode: "triple" }); m.hit(1200, 0.8); m.hit(1300, 0.8); m.frame(1310);
    m.hit(NaN, 0.5); m.frame(1330);
  });
  assert.equal(m.log[m.log.length - 2].gate, "triple", "after the dial turns, rapid presses fire the dial's gate");
});

test("tiers: held = a continuous gate by section, and it stops when released", () => {
  const cases = [["build", 0.6, "doubling"], ["drop", 0.6, "pushpull"], ["drop", 0.95, "roll16"], ["anti", 0.6, "military"], ["break", 0.6, "roll8"]];
  for (const [section, vel, gate] of cases) {
    const r = tierRun([{ beat: 0, vel, hold: 6 }], { section });
    const held = r.log.find((x) => x.tier === "held");
    assert.ok(held, `${section}: a hold spawns a loop`);
    assert.equal(held.gate, gate, `${section} vel ${vel}`);
    const after = r.onsets.filter((o) => o.hit === held.id && o.t > 2000 + 6.6 * r.per);
    assert.equal(after.length, 0, `${section}: nothing new after the release (${after.length})`);
    assert.ok(r.onsets.filter((o) => o.hit === held.id).length >= 3, `${section}: the loop ran`);
  }
  // the doubling roll speeds up while held: 1 beat, then 1/2, then 1/4
  const d = tierRun([{ beat: 0, vel: 0.6, hold: 14 }], { section: "build" });
  const held = d.log.find((x) => x.tier === "held");
  const ts = d.onsets.filter((o) => o.hit === held.id).map((o) => o.t);
  const gaps = ts.slice(1).map((x, i) => Math.round((x - ts[i]) / d.per * 4) / 4);
  assert.ok(gaps.includes(1) && gaps.includes(0.5) && gaps.includes(0.25), `doubling steps ${gaps.join(",")}`);
  assert.ok(gaps.indexOf(0.25) > gaps.lastIndexOf(1), "it only ever speeds up");
});

test("tiers: velocity picks the gate (soft single, medium one-two, hard triple), and the option inverts it", () => {
  const vg = (vel, inv = false) => tierRun([{ beat: 0, vel }], { opts: { velocityTiers: inv ? "inverted" : "normal" } }).log[0].gate;
  assert.equal(vg(0.3), "single");
  assert.equal(vg(0.6), "onetwo");
  assert.ok(["triple", "triplet"].includes(vg(0.95)));
  assert.ok(["triple", "triplet"].includes(vg(0.3, true)));
  assert.equal(vg(0.95, true), "single");
});

// ------------------------------------------------------------------------------------ 4. A2: the gate timing --
function onsetErrors(gate, bpm, phaseMs, { rule = "early", hitOffset = -50, clockOpts = {} } = {}) {
  const per = 60000 / bpm, clk = steadyClock(bpm, clockOpts);
  const eng = L.createLaserEngine({ seed: 9, clock: clk, gateMode: gate, patternMode: "fan", bankMode: "A", onsetRule: rule });
  const beat = 40 * per, hitT = beat + hitOffset;
  const ons = [], onFrames = [];
  let lastOn = false, runOn = 0, runOff = 0;
  drive(eng, tap(hitT, 0.7), { from: beat - 500 + phaseMs, to: beat + 4 * per, onFrame: (out, t) => {
    for (const e of out.events) if (e.type === "pulse") ons.push(t + F);
    const on = eng.hits.some((h) => h.on);
    if (on) { if (!lastOn && runOff) onFrames.push({ off: runOff }); runOn++; runOff = 0; }
    else { if (lastOn) onFrames.push({ on: runOn }); runOff++; runOn = 0; }
    lastOn = on;
  } });
  const G = L.GATES[gate];
  return { errs: ons.map((t, k) => t - (beat + G.pulses[k].at * per)), count: ons.length, expected: G.pulses.length, onFrames, ons, per };
}

test("A2: short gates land on the beat grid, never late and at most one frame early, with no missing or doubled pulse", () => {
  const rnd = mulberry(77);
  const all = [];
  for (const bpm of [150, 180]) for (const gate of ["single", "onetwo", "triple", "triplet", "bar", "tttou"]) for (let r = 0; r < 6; r++) {
    const res = onsetErrors(gate, bpm, rnd() * F);
    assert.equal(res.count, res.expected, `${gate} at ${bpm}: ${res.count} pulses`);
    for (const e of res.errs) { assert.ok(e <= 0.01 && e >= -F - 0.01, `${gate} at ${bpm}: ${e.toFixed(2)} ms`); all.push(e); }
    // the frame rules: a pulse on for 3 frames or more, a gap of 2 or more, a step of 5 or more
    for (const f of res.onFrames) { if (f.on !== undefined) assert.ok(f.on >= 3, `${gate} ${bpm}: on ${f.on} frames`); if (f.off !== undefined) assert.ok(f.off >= 2, `${gate} ${bpm}: off ${f.off} frames`); }
    for (let k = 1; k < res.ons.length; k++) assert.ok(res.ons[k] - res.ons[k - 1] >= 5 * F - 0.01, `${gate} ${bpm}: step ${(res.ons[k] - res.ons[k - 1]).toFixed(1)} ms`);
  }
  const mean = all.reduce((a, b) => a + b, 0) / all.length;
  console.log(`  A2 early rule: ${all.length} pulses, mean ${mean.toFixed(2)} ms, worst ${Math.min(...all).toFixed(2)} ms (negative = early)`);
});

// Round-1 fix (verifier, must fix 2): at some press offsets a one-two showed 1 flash, a triple 2 and the phrase 5 (42 of
// 300 presses at 120 BPM; at 160-180 BPM even presses exactly on the beat). Pulse 1 could only be lit late, pulse 2 fell
// under the 83 ms step, and the guard discarded it after its index had moved on. Spec 3.3: it moves to the next grid point.
test("A2: an isolated press at ANY offset in the beat fires every pulse of its gate, on the grid, inside the frame rules", () => {
  const want = { onetwo: 2, triple: 3, triplet: 3, tttou: 6, single: 1, bar: 1 };
  let presses = 0;
  for (const bpm of [120, 128, 150, 180]) {
    const per = 60000 / bpm;
    for (const gate of Object.keys(want)) {
      const g = L.GATES[gate].grid;
      for (let off = 0; off < per; off += 7) {
        const clk = steadyClock(bpm);
        const eng = L.createLaserEngine({ seed: 7, clock: clk, gateMode: gate, patternMode: "fan", bankMode: "A", orderMode: "all" });
        const press = 20 * per + off, phase = (off * 0.37) % F;
        const ons = [];
        let runOn = 0, runOff = 0, lastOn = false, pressed = false;
        for (let t = press - 3 * F + phase; t < press + 3.5 * per; t += F) {
          if (!pressed && t >= press) { eng.hit(press, 0.9); eng.release(press + 40); pressed = true; }
          const out = eng.frame(t);
          for (const e of out.events) if (e.type === "pulse") ons.push(t + F);
          const on = eng.hits.some((h) => h.on);
          if (on) { if (!lastOn && runOff && ons.length > 1) assert.ok(runOff >= 2, `${gate} ${bpm} +${off}: off ${runOff} frames`); runOn++; runOff = 0; }
          else { if (lastOn) assert.ok(runOn >= 3, `${gate} ${bpm} +${off}: on ${runOn} frames`); runOff++; runOn = 0; }
          lastOn = on;
        }
        presses++;
        assert.equal(ons.length, want[gate], `${gate} at ${bpm} BPM, press ${off} ms into the beat: ${ons.length} pulses`);
        for (let k = 1; k < ons.length; k++) {
          assert.ok(ons[k] - ons[k - 1] >= 5 * F - 0.01, `${gate} ${bpm} +${off}: step ${(ons[k] - ons[k - 1]).toFixed(1)} ms`);
          const beats = ons[k] / per, gridP = Math.round(beats / g) * g, err = ons[k] - gridP * per;
          assert.ok(err <= 0.01 && err >= -F - 0.01, `${gate} ${bpm} +${off}: pulse ${k} ${err.toFixed(2)} ms from the grid`);
        }
      }
    }
  }
  console.log(`  ${presses} isolated presses at every 7 ms of the beat: every pulse fired, on the grid`);
});

test("A2: the nearest-frame rule meets the spec's bound (max 8.4 ms, mean 4.5 ms)", () => {
  const all = [];      // evenly spaced frame phases: at 150 BPM every pulse of a gate shares one phase, so random ones are few samples
  for (const bpm of [150, 180]) for (const gate of ["single", "onetwo", "triple", "triplet", "tttou"]) for (let r = 0; r < 12; r++) {
    const res = onsetErrors(gate, bpm, (r + 0.5) * F / 12, { rule: "nearest" });
    assert.equal(res.count, res.expected);
    all.push(...res.errs);
  }
  const absMax = Math.max(...all.map(Math.abs)), mean = all.reduce((a, b) => a + Math.abs(b), 0) / all.length;
  console.log(`  A2 nearest rule: max |error| ${absMax.toFixed(2)} ms, mean ${mean.toFixed(2)} ms`);
  assert.ok(absMax <= 8.4 + 0.01 && mean <= 4.5);
});

test("A2: a hit 60 ms early waits for the beat; a hit mid-beat fires now and the rest land on the 16th grid", () => {
  const per = 400;
  const early = onsetErrors("triple", 150, 3.3, { hitOffset: -58 });
  for (const e of early.errs) assert.ok(e <= 0.01 && e >= -F - 0.01);
  // a press closer to the beat than two frames arrives after the frame that would have shown it early was drawn: it
  // lands within (2 frames - lead) of the beat, never more
  const rnd = mulberry(5);
  for (let r = 0; r < 12; r++) {
    const close = onsetErrors("onetwo", 150, rnd() * F, { hitOffset: -30 });
    assert.ok(close.errs[0] <= 2 * F - 30 + 0.01, `a press 30 ms ahead: ${close.errs[0].toFixed(2)} ms`);
    assert.ok(close.errs[1] <= 0.01, "and the next pulse is on time again");
  }
  const mid = onsetErrors("triple", 150, 3.3, { hitOffset: 120 });    // 120 ms after a beat: the next 16th is 80 ms on
  assert.equal(mid.count, 3);
  assert.ok(mid.ons[0] - (40 * per + 150) <= 2 * F, "pulse 1 fires at once");
  for (let k = 1; k < 3; k++) {
    const P = (mid.ons[k] - 0) / per, grid = Math.round(P * 4) / 4;
    assert.ok(mid.ons[k] - grid * per <= 0.01 && mid.ons[k] - grid * per >= -F - 0.01, "later pulses on the 16th grid");
    assert.ok(mid.ons[k] - mid.ons[k - 1] >= 83 - F, "never closer than 83 ms");
  }
});

test("A2: the clock without posAt (phase unwrapped) and the page's own BeatClock give the same grid", () => {
  for (const bpm of [150, 174]) {
    const a = onsetErrors("tttou", bpm, 5.5), b = onsetErrors("tttou", bpm, 5.5, { clockOpts: { posAt: false } });
    assert.deepEqual(b.ons.map((x) => x.toFixed(3)), a.ons.map((x) => x.toFixed(3)), `${bpm}: unwrapped phase = posAt`);
  }
  // vj-core's BeatClock, fed the engine's beat events 250 ms ahead, through clockFromBeatClock
  const bpm = 150, per = 400, bc = new BeatClock();
  const eng = L.createLaserEngine({ seed: 4, clock: L.clockFromBeatClock(bc), gateMode: "triple", patternMode: "fan", bankMode: "B" });
  let nextAnnounce = 0;
  const ons = [];
  const target = 30 * per;
  let prev = null;
  for (let j = 0; ; j++) {
    const t = 1000 + 7.1 + j * F;
    if (t > target + 3 * per) break;
    while (nextAnnounce * per <= t + 250) { if (nextAnnounce * per >= t - 30) bc.schedule(t, { due_ms: nextAnnounce * per - t, bpm, conf: 0.9, n: nextAnnounce, on_beat: null }); nextAnnounce++; }
    bc.update(t, prev === null ? F : t - prev);
    prev = t;
    if (Math.abs(t - (target - 30)) < F / 2) { eng.hit(t, 0.9); eng.release(t + 50); }
    const out = eng.frame(t);
    for (const e of out.events) if (e.type === "pulse") ons.push(t + F);
  }
  const G = L.GATES[eng.log[0].gate];
  assert.equal(ons.length, G.pulses.length);
  ons.forEach((t, k) => { const e = t - (target + G.pulses[k].at * per); assert.ok(e <= 0.5 && e >= -F - 0.5, `BeatClock pulse ${k}: ${e.toFixed(2)} ms`); });
});

test("A2: a tempo ramp 150 -> 156 BPM keeps a held 16th roll on the moving grid", () => {
  const per0 = 400, tA = 20 * per0, ramp = 16 * per0;
  const clk = rampClock(150, 156, tA, ramp);
  const eng = L.createLaserEngine({ seed: 2, clock: clk, gateMode: "roll16", patternMode: "chase", section: "build" });
  const ons = [];
  drive(eng, tap(tA - 2 * per0 - 20, 0.7, 18 * per0), { from: tA - 3 * per0, to: tA + ramp + 2 * per0, clock: clk,
    onFrame: (out, t) => { for (const e of out.events) if (e.type === "pulse") ons.push(t + F); } });
  assert.ok(ons.length > 30, `pulses ${ons.length}`);
  let worst = 0;
  for (const t of ons) {
    const P = clk.posAt(t), grid = Math.round(P * 4) / 4, err = t - clk.timeOf(grid);
    worst = Math.max(worst, Math.abs(err));
    assert.ok(err <= 0.5 && err >= -F - 0.5, `ramp pulse ${err.toFixed(2)} ms from the grid`);
  }
  console.log(`  A2 ramp: ${ons.length} pulses, worst ${worst.toFixed(2)} ms from the moving grid`);
});

test("A2: above 180 BPM a 16th roll runs at half speed; a clock jump never doubles or re-fires a pulse", () => {
  const clk = steadyClock(200), per = 300;
  const eng = L.createLaserEngine({ seed: 2, clock: clk, gateMode: "roll16", patternMode: "chase" });
  const ons = [];
  drive(eng, tap(30 * per, 0.7, 4 * per), { from: 29 * per, to: 36 * per, onFrame: (out, t) => { for (const e of out.events) if (e.type === "pulse") ons.push(t); } });
  for (let k = 1; k < ons.length; k++) assert.ok(ons[k] - ons[k - 1] >= 83 - F, `step ${(ons[k] - ons[k - 1]).toFixed(1)} ms`);
  // a forward jump of half a beat mid-roll, then a backward one
  let shift = 0;
  const per2 = 400, base = steadyClock(150);
  const jumpy = { get bpm() { return 150; }, conf: 1, posAt: (t) => base.posAt(t) + shift, phaseAt: (t) => { const p = base.posAt(t) + shift; return p - Math.floor(p); }, nextBeatAt: () => null };
  const e2 = L.createLaserEngine({ seed: 2, clock: jumpy, gateMode: "roll16", patternMode: "chase" });
  const seen = [];
  drive(e2, [...tap(20 * per2, 0.7, 8 * per2), { t: 23 * per2 + 10, fn: () => { shift = 0.5; } }, { t: 25 * per2 + 10, fn: () => { shift = 0.25; } }],
    { from: 19 * per2, to: 30 * per2, onFrame: (out, t) => { for (const e of out.events) if (e.type === "pulse") seen.push({ t, k: e.k }); } });
  assert.equal(new Set(seen.map((s) => s.k)).size, seen.length, "every pulse fires once");
  for (let k = 1; k < seen.length; k++) assert.ok(seen[k].t - seen[k - 1].t >= 83 - F - 0.01, "no doubled pulse across the jumps");
});

// --------------------------------------------------------------------------------------------- 5. bank modes --
function bankRun(bankMode, presses = 3, gate = "triple") {
  const clk = steadyClock(150), per = 400;
  const eng = L.createLaserEngine({ seed: 12, clock: clk, bankMode, gateMode: gate, patternMode: "fan", orderMode: "lr" });
  const ev = [];
  for (let i = 0; i < presses; i++) ev.push(...tap(2000 + i * 6 * per, 0.7));
  const frames = [];
  drive(eng, ev, { from: 1900, to: 2000 + presses * 6 * per + 1000, onFrame: (out, t) => {
    const lit = [];
    eachLine(out, (r, i, head) => { if (r.I > 0.3 && r.kind === 0) lit.push(head); });
    const pulses = out.events.filter((e) => e.type === "pulse");
    frames.push({ t, heads: [...new Set(lit)], pulses });
  } });
  return { eng, frames, log: eng.log };
}
const bankOf = (h) => L.HEADS[h].bank;

test("bank modes: A only the truss, B only the floor, alternate switches, both spans the rig", () => {
  for (const [mode, want] of [["A", "A"], ["B", "B"]]) {
    const r = bankRun(mode);
    const lit = r.frames.flatMap((f) => f.heads);
    assert.ok(lit.length > 0 && lit.every((h) => bankOf(h) === want), `${mode}: ${[...new Set(lit.map(bankOf))]}`);
  }
  const alt = bankRun("alternate", 4);
  assert.deepEqual(alt.log.map((x) => x.bank), ["A", "B", "A", "B"]);
  const both = bankRun("both", 2, "triple");
  const banks = new Set(both.log.flatMap((x) => x.heads.map((n) => n[0])));
  assert.ok(banks.has("A") && banks.has("B"), "both: the hit's heads span both banks");
});

// Round-1 (verifier's note): with dial, order and pattern fixed the anti-repeat loop redeals, and the alternation counter
// advanced on every attempt, so 6 of 63 consecutive hits repeated a bank.
test("bank modes: alternate switches banks on every hit even when the deal has to redeal", () => {
  const clk = steadyClock(150), per = 400;
  const eng = L.createLaserEngine({ seed: 12, clock: clk, bankMode: "alternate", gateMode: "single", patternMode: "fan", orderMode: "lr", section: "climax" });
  const ev = [];
  for (let i = 0; i < 64; i++) ev.push(...tap(2000 + i * 6 * per, 0.7));
  drive(eng, ev, { from: 1900, to: 2000 + 64 * 6 * per });
  const banks = eng.log.map((x) => x.bank);
  const repeats = banks.slice(1).filter((b, i) => b === banks[i]).length;
  assert.equal(repeats, 0, `consecutive hits on the same bank: ${repeats} of ${banks.length - 1}`);
});

test("bank modes: call = A fires, B answers half a beat later; mirror = each A head with its B twin", () => {
  const r = bankRun("call", 1, "single");
  const firstA = r.frames.find((f) => f.heads.some((h) => bankOf(h) === "A"));
  const firstB = r.frames.find((f) => f.heads.some((h) => bankOf(h) === "B"));
  assert.ok(firstA && firstB, "both banks fire");
  const lag = (firstB.t - firstA.t) / 400;
  assert.ok(Math.abs(lag - 0.5) <= F / 400 + 1e-9, `B answers ${lag.toFixed(3)} beats after A`);
  const m = bankRun("mirror", 2);
  const litFrames = m.frames.filter((f) => f.heads.length);
  assert.ok(litFrames.length > 5);
  for (const f of litFrames) {
    const A = f.heads.filter((h) => bankOf(h) === "A").map((h) => L.HEADS[h].u).sort(), B = f.heads.filter((h) => bankOf(h) === "B").map((h) => L.HEADS[h].u).sort();
    assert.deepEqual(A, B, "mirror: the same positions on both banks");
  }
});

// -------------------------------------------------------------------------------------------------- 6. shapes --
test("shapes: every figure is 96 finite segments round the hero; circles round, polygons on their edges", () => {
  const R = 0.2;
  for (const name of L.SHAPES) for (const pos of [0, 1.3, 5.7]) {
    const s = L.shapeSegments(name, { pos, R });
    assert.equal(s.length, L.SHAPE_SEGS * 4);
    for (let i = 0; i < s.length; i++) assert.ok(Number.isFinite(s[i]));
    for (let i = 0; i < s.length; i += 2) assert.ok(Math.hypot(s[i] - L.HERO.x, s[i + 1] - L.HERO.y) <= 1.5 * R + 1e-9, `${name} within the perspective bound`);
  }
  const c = L.shapeSegments("circle", { R });
  for (let i = 0; i < c.length; i += 2) { const d = Math.hypot(c[i] - L.HERO.x, c[i + 1] - L.HERO.y); assert.ok(d <= R + 1e-6 && d >= R * Math.cos(Math.PI / 48) - 1e-6); }
  const corners = (name, n, rot) => Array.from({ length: n }, (_, k) => [L.HERO.x + R * Math.cos(rot + 2 * Math.PI * k / n), L.HERO.y + R * Math.sin(rot + 2 * Math.PI * k / n)]);
  for (const [name, n, rot] of [["triangle", 3, Math.PI / 2], ["square", 4, Math.PI / 4]]) {
    const s = L.shapeSegments(name, { R });
    const pts = [];
    for (let i = 0; i < s.length; i += 2) pts.push([s[i], s[i + 1]]);
    const cs = corners(name, n, rot);
    for (const q of cs) assert.ok(pts.some((p) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 1e-6), `${name} reaches each corner`);
    for (const p of pts) {
      const onEdge = cs.some((a, k) => { const b = cs[(k + 1) % n]; const cr = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]); return Math.abs(cr) / Math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6; });
      assert.ok(onEdge, `${name} points lie on its edges`);
    }
  }
});

test("shapes: the 3D wireframes have their edges, turn with the beat, and are drawn in perspective", () => {
  assert.equal(L.shapeStrokes("tetrahedron", 0).length, 6);
  assert.equal(L.shapeStrokes("cube", 0).length, 12);
  assert.equal(L.shapeStrokes("octahedron", 0).length, 12);
  const a = JSON.stringify(L.shapeStrokes("cube", 0)), b = JSON.stringify(L.shapeStrokes("cube", 1)), c = L.shapeStrokes("cube", 16);
  assert.notEqual(a, b, "the cube turns");
  L.shapeStrokes("cube", 0).forEach((e, i) => e.forEach((p, j) => p.forEach((v, k) => assert.ok(Math.abs(v - c[i][j][k]) < 1e-9, "one full cycle every 16 beats"))));
  const lens = L.shapeStrokes("cube", 0.7).map(([p, q]) => Math.hypot(p[0] - q[0], p[1] - q[1]));
  assert.ok(Math.max(...lens) / Math.min(...lens) > 1.2, "near edges look longer than far ones (perspective)");
});

test("shapes: a held figure morphs into the next one on each beat", () => {
  const clk = steadyClock(150), per = 400;
  const eng = L.createLaserEngine({ seed: 8, clock: clk, shapeMode: "auto", section: "break" });
  const seen = [];
  let checked = 0;
  drive(eng, tap(2000, 0.7, 5 * per), { from: 1900, to: 2000 + 6 * per, onFrame: (out, t) => {
    const H = eng.hits.find((h) => h.pattern === "figure" && h.shapeNow);
    if (!H || !H.started) return;
    if (!seen.includes(H.shapeNow)) seen.push(H.shapeNow);
    const posE = eng.posE, f = posE - Math.floor(posE);
    if (f > 0.3 && f < 0.9 && out.n >= L.SHAPE_SEGS && checked < 3) {      // the morph is over: the figure IS the shape
      const want = L.shapeSegments(H.shapeNow, { pos: posE, R: 0.2 * (0.9 + 0.2 * H.vel) * (H.level >= 2 ? 1.15 : 1) });
      let worst = 0, k = 0;
      eachLine(out, (r) => {
        if (r.kind !== 1 || k >= L.SHAPE_SEGS) return;
        [r.x0, r.y0, r.x1, r.y1].forEach((v, q) => { worst = Math.max(worst, Math.abs(v - want[k * 4 + q])); });
        k++;
      });
      assert.ok(worst < 1e-3, `figure = ${H.shapeNow} after the morph (${worst})`);
      checked++;
    }
  } });
  assert.ok(seen.length >= 3, `figures over the hold: ${seen.join(" -> ")}`);
  assert.ok(checked >= 1);
});

// ------------------------------------------------------------------------------------------------- 7. Vibrate --
test("Vibrate: three standing-wave modes, nodes at both ends, each overtone dying faster, gone in about 3 tau", () => {
  const amp = 12;
  for (const t of [0, 0.1, 0.4, 1]) {
    assert.equal(L.vibEnvelope(0, t, amp), 0);
    assert.ok(Math.abs(L.vibEnvelope(1, t, amp)) < 1e-9, "a node at the far end");
    assert.ok(Math.abs(L.vibDisplacement(0, t, amp, 0.7)) < 1e-12 && Math.abs(L.vibDisplacement(1, t, amp, 0.7)) < 1e-9);
  }
  let prev = Infinity, prevRatio = Infinity;
  for (let t = 0; t <= 3; t += 0.05) {
    const m = L.vibModes(t, amp);
    const total = m.reduce((a, b) => a + b, 0);
    assert.ok(total <= prev + 1e-12, "the ring only decays");
    prev = total;
    const ratio = m[2] / m[0];
    assert.ok(ratio <= prevRatio + 1e-12, "the top mode dies first");
    prevRatio = ratio;
  }
  assert.ok(L.vibModes(3 * L.VIB.TAU1_S, amp)[0] / amp < 0.06);
  assert.ok(L.vibModes(0.3, amp, 0.3)[0] / L.vibModes(0.3, amp)[0] < 0.02, "Vibrate off damps the ring in 0.3 s");
});

test("Vibrate: a ringing beam is ONE record bent by its mode coefficients, with a blur band, and it settles straight", () => {
  const clk = steadyClock(150), per = 400;
  const eng = L.createLaserEngine({ seed: 8, clock: clk, vibrate: true, gateMode: "single", patternMode: "hot", bankMode: "A", orderMode: "one" });
  let maxN = 0, maxBlur = 0, bent = false, ringed = 0, lateRing = null, worstBend = 0;
  drive(eng, tap(2000, 0.9), { from: 1900, to: 2000 + 1.2 * per, onFrame: (out, t) => {
    maxN = Math.max(maxN, out.n);
    eachLine(out, (r, i, head) => {
      maxBlur = Math.max(maxBlur, r.blur);
      if (!r.ring) return;
      ringed++;
      // still at both ends, displaced in between; the blur band follows sin(pi u)
      assert.ok(Math.abs(L.ringOffsetPx(r, 0)) < 1e-9 && Math.abs(L.ringOffsetPx(r, 1)) < 1e-9);
      if ([0.2, 0.5, 0.7].some((u) => Math.abs(L.ringOffsetPx(r, u)) > 0.5)) bent = true;
      assert.ok(Math.abs(L.blurPx(r, 0.5) - r.blur) < 1e-9 && L.blurPx(r, 0) < 1e-9);
      // the coefficients are the string's own: the bend is vibDisplacement at this moment (risen through the pluck's
      // attack), within the 8-bit steps
      const v = eng.vib[head], age = (t - v.t0) / 1000;
      for (const u of [0.15, 0.3, 0.5, 0.8]) worstBend = Math.max(worstBend, Math.abs(L.ringOffsetPx(r, u) - L.ringAttack(age) * L.vibDisplacement(u, age, v.amp, v.ph, null)));
    });
  } });
  assert.equal(maxN, 1, "one beam is one record, ringing or not");
  assert.ok(ringed > 5 && bent, `the record rings and bends (${ringed} frames)`);
  assert.ok(worstBend < 0.15, `the bend matches the string within ${worstBend.toFixed(3)} px`);
  assert.ok(maxBlur > 1 && maxBlur <= L.VIB.BLUR_MAX_PX, `blur ${maxBlur}`);
  // without Vibrate the same beam is one straight record with no blur
  const plain = L.createLaserEngine({ seed: 8, clock: clk, vibrate: false, gateMode: "single", patternMode: "hot", bankMode: "A", orderMode: "one" });
  let pN = 0, pBlur = 0, pRing = false;
  drive(plain, tap(2000, 0.9), { from: 1900, to: 2000 + per, onFrame: (out) => { pN = Math.max(pN, out.n); eachLine(out, (r) => { pBlur = Math.max(pBlur, r.blur); pRing = pRing || r.ring; }); } });
  assert.equal(pN, 1);
  assert.equal(pBlur, 0);
  assert.equal(pRing, false);
  // a bar marker (a long tail) with Vibrate switched off mid-ring: the string settles straight inside the tail
  const ring = L.createLaserEngine({ seed: 8, clock: clk, vibrate: true, gateMode: "bar", patternMode: "hot", bankMode: "A", orderMode: "one" });
  drive(ring, [...tap(2000, 1), { t: 2000 + 150, fn: (e, x) => e.setVibrate(false, x) }], { from: 1900, to: 2000 + 2 * per,
    onFrame: (out, t) => { if (lateRing === null && t > 2000 + 150 + 300 && out.n > 0) { lateRing = false; eachLine(out, (r) => { lateRing = lateRing || r.ring; }); } } });
  assert.equal(lateRing, false, "damped: straight again, while the tail still shows");
});

test("\"t t tou blur blur flash\": tick, tick, pluck, smear, smear, flash, beat-locked, ringing even with Vibrate off", () => {
  const clk = steadyClock(150), per = 400;
  const eng = L.createLaserEngine({ seed: 8, clock: clk, patternMode: "fan", bankMode: "A" });
  const acts = [], flashes = [], blurAt = {};
  let phase = "";
  drive(eng, [{ t: 40 * per - 20, fn: (e, x) => e.phrase(x, 0.9) }], { from: 40 * per - 300, to: 44 * per, onFrame: (out, t) => {
    for (const e of out.events) { if (e.type === "pulse") { acts.push({ act: e.act, t: t + F }); phase = e.act; } if (e.type === "flash") flashes.push(t); }
    let b = 0;
    eachLine(out, (r) => { b = Math.max(b, r.blur); });
    blurAt[phase] = Math.max(blurAt[phase] || 0, b);
  } });
  assert.deepEqual(acts.map((a) => a.act), ["tick", "tick", "pluck", "smear", "smear", "flash"]);
  const at = [0, 0.25, 0.5, 1, 1.5, 2];
  acts.forEach((a, k) => { const e = a.t - (40 + at[k]) * per; assert.ok(e <= 0.01 && e >= -F - 0.01, `${a.act} ${e.toFixed(2)} ms`); });
  assert.equal(flashes.length, 1, "one flash event, for the page's FlashGate");
  assert.equal(blurAt.tick || 0, 0, "the ticks are clean");
  assert.ok(blurAt.pluck > 0, "tou: the beams ring");
  assert.ok(blurAt.smear > blurAt.pluck, `blur blur: the ring smears wider (${blurAt.smear.toFixed(2)} > ${blurAt.pluck.toFixed(2)})`);
});

// ---------------------------------------------------------------------------- 8. A5a: area and flash safety --
const SAFETY_GATES = ["single", "onetwo", "triple", "triplet", "bar", "tttou", "roll8", "roll16", "stutter", "military", "pushpull", "revbass", "doubling", "stopshort", "inhale"];
test("A5a: every pattern x gate x bank at 150 and 180 BPM, Vibrate on and off, keeps its CHANGE inside the budget", () => {
  const worst = { fast: 0, single: 0, frame: 0 };
  const byPattern = {};
  let overFrames = 0;
  for (const bpm of [150, 180]) for (const pattern of L.PATTERN_IDS) for (const gate of SAFETY_GATES) for (const vibrate of [false, true]) {
    const bank = ["both", "mirror", "A"][(L.PATTERN_IDS.indexOf(pattern) + SAFETY_GATES.indexOf(gate)) % 3];
    const per = 60000 / bpm, clk = steadyClock(bpm);
    const eng = L.createLaserEngine({ seed: 31, clock: clk, patternMode: pattern, gateMode: gate, bankMode: bank, orderMode: "all", vibrate, section: "climax" });
    // a hard press, a second press inside the bar (tier 2), and a hold
    const ev = [...tap(2000, 1), ...tap(2000 + 2 * per, 1), ...tap(2000 + 4 * per, 1, 3 * per)];
    drive(eng, ev, { from: 1950, to: 2000 + 9 * per, onFrame: (out) => {
      const fast = eng.hits.some((h) => h.started && h.fast);
      const w = out.area.window;
      if (fast) worst.fast = Math.max(worst.fast, w); else worst.single = Math.max(worst.single, w);
      worst.frame = Math.max(worst.frame, out.area.frame);
      byPattern[pattern] = Math.max(byPattern[pattern] || 0, w);
      if (out.area.over) overFrames++;
      assert.ok(w <= (fast ? L.BUDGET.fast.window : L.BUDGET.single.window) + 1e-9, `${pattern}/${gate}/${bank}/${bpm}${vibrate ? "/vib" : ""}: window ${w.toFixed(3)}`);
      assert.ok(out.area.frame <= L.BUDGET.single.frame + 1e-9, `${pattern}/${gate}: frame ${out.area.frame.toFixed(3)}`);
      const heads = new Set();
      eachLine(out, (r, i, head) => {
        assert.ok(r.width <= L.CORE_MAX_PX + 1e-6);
        if (r.kind === 0 && r.I > 0.002) heads.add(head);
      });
      if (eng.hits.some((h) => h.started && !h.finished && h.fast)) assert.ok(heads.size <= L.BUDGET.fast.heads, `${pattern}/${gate}: ${heads.size} heads lit in a fast gate`);
    } });
  }
  console.log(`  A5a estimator (change per frame): worst window ${(100 * worst.fast).toFixed(1)} % with a fast hit, ${(100 * worst.single).toFixed(1)} % without; ` +
    `worst frame ${(100 * worst.frame).toFixed(1)} %; frames sent over budget: ${overFrames}`);
  console.log(`  by pattern: ${Object.entries(byPattern).map(([p, w]) => `${p} ${(100 * w).toFixed(1)}`).join(", ")}`);
  assert.equal(overFrames, 0, "no frame had to go out over its budget");
});

// An independent check of what the beam layer draws over black: the verifier's ADDITIVE raster of the overlay's light
// model, reading the output records through the module's reference decoder exactly as a shader would. Each line: its
// core is the overlay's aaWire, whitened by its heat as hotCore() does, spread over its blur band; its halo is the
// overlay's Lorentzian (16 px at 1080) at its glow, out to 6 halo radii; both fade along a beam by its falloff; a ringing
// beam is bent by its coefficients; a figure group takes the nearest of its pieces and adds its light once. Light is
// SUMMED per channel in linear rgb (additive blending), clamped, then turned into relative luminance. A pixel FLASHES
// between two frames when its luminance moves by 0.1 or more with the darker state below 0.8 (WCAG 2.3.1). Windows are
// one third of each side, slid in steps of a quarter window (or finer), so the worst window anywhere is found.
// Reads the round-1 records; the pre-fix 16-float rows are read too, so this check can be run against the old engine.
function decodeAny(seg, i, r) {
  if (L.decodeSeg) return L.decodeSeg(seg, i, r);
  const o = i * 16;
  Object.assign(r, { header: false, x0: seg[o], y0: seg[o + 1], x1: seg[o + 2], y1: seg[o + 3], r: seg[o + 4], g: seg[o + 5], b: seg[o + 6],
    I: seg[o + 7], width: seg[o + 8], glow: seg[o + 9], blur: seg[o + 10], heat: seg[o + 11], kind: seg[o + 12], falloff: seg[o + 14],
    flags: seg[o + 15], ring: false, run: (seg[o + 15] & 2) !== 0, cont: (seg[o + 15] & 4) !== 0 });
  return r;
}
function makeRaster(RW, RH, aspect = 16 / 9) {
  const sc = RH / 1080, haloPx = 16 * sc, reach = Math.ceil(6 * haloPx + 4);
  const R = new Float32Array(RW * RH), G = new Float32Array(RW * RH), B = new Float32Array(RW * RH), Y = new Float32Array(RW * RH);
  const dmin = new Float32Array(RW * RH).fill(Infinity), dAlong = new Float32Array(RW * RH), dU = new Float32Array(RW * RH), dRec = new Int32Array(RW * RH);
  const touched = new Int32Array(RW * RH);
  let nt = 0, bx0 = RW, by0 = RH, bx1 = -1, by1 = -1;          // the dirty box, so a dark frame costs nothing
  const recs = [];
  for (let i = 0; i < 512; i++) recs.push({});
  // the nearest distance (px) from each pixel near line r to it, bent if it rings
  function visit(r, ri, alongBase) {
    const dx = r.x1 - r.x0, dy = r.y1 - r.y0, len = Math.hypot(dx, dy);
    if (!(len > 1e-9)) return 0;
    const ux = dx / len, uy = dy / len;
    const ringMax = r.ring ? (Math.abs(r.c1) + Math.abs(r.c2) + Math.abs(r.c3)) * sc : 0;
    const ext = reach + ringMax + r.blur * sc + 2;
    const pxA = (r.x0 / aspect + 0.5) * RW, pyA = (0.5 - r.y0) * RH, pxB = (r.x1 / aspect + 0.5) * RW, pyB = (0.5 - r.y1) * RH;
    const x0 = Math.max(0, Math.floor(Math.min(pxA, pxB) - ext)), x1 = Math.min(RW - 1, Math.ceil(Math.max(pxA, pxB) + ext));
    const y0 = Math.max(0, Math.floor(Math.min(pyA, pyB) - ext)), y1 = Math.min(RH - 1, Math.ceil(Math.max(pyA, pyB) + ext));
    for (let y = y0; y <= y1; y++) {
      const cy = 0.5 - (y + 0.5) / RH;
      // only the pixels of this row within ext of the line's axis
      let xa = x0, xb = x1;
      if (Math.abs(uy) > 1e-6) {
        const xl = r.x0 + (cy - r.y0) * ux / uy, half = (ext / RH) / Math.abs(uy) + 2 / RW * aspect;
        xa = Math.max(x0, Math.floor(((xl - half) / aspect + 0.5) * RW)); xb = Math.min(x1, Math.ceil(((xl + half) / aspect + 0.5) * RW));
      }
      for (let x = xa; x <= xb; x++) {
        const cx = (x + 0.5) / RW * aspect - aspect / 2, px = cx - r.x0, py = cy - r.y0;
        const t = px * ux + py * uy;
        let d, u;
        if (t <= 0) { d = Math.hypot(px, py); u = 0; } else if (t >= len) { d = Math.hypot(cx - r.x1, cy - r.y1); u = 1; }
        else { u = t / len; d = Math.abs(-px * uy + py * ux - (r.ring && L.ringOffsetPx ? L.ringOffsetPx(r, u) / 1080 : 0)); }
        d *= RH;
        if (d > ext) continue;
        const k = y * RW + x;
        if (dmin[k] === Infinity) { touched[nt++] = k; if (x < bx0) bx0 = x; if (x > bx1) bx1 = x; if (y < by0) by0 = y; if (y > by1) by1 = y; }
        if (d < dmin[k]) { dmin[k] = d; dAlong[k] = alongBase + Math.max(0, Math.min(t, len)); dU[k] = u; dRec[k] = ri; }
      }
    }
    return len;
  }
  function flush() {
    for (let i = 0; i < nt; i++) {
      const k = touched[i], r = recs[dRec[k]], d = dmin[k];
      const fade = Math.exp(-dAlong[k] * r.falloff), peak = Math.max(r.r, r.g, r.b), kw = r.heat * r.heat / (1 + r.heat * r.heat);
      const wpx = r.width * sc, blur = (L.blurPx ? L.blurPx(r, dU[k]) : r.blur) * sc;
      const Wd = blur > 0 ? wpx + 2 * blur : wpx, drawn = Math.max(Wd, 1);
      const core = Math.min(1, Math.max(0, 0.5 * drawn + 0.5 - d)) * (wpx / drawn);
      const q = d / haloPx, halo = 0.5 * r.glow * 0.0625 / (0.0625 + q * q);
      const ci = r.I * core * fade, hi = halo * fade;
      R[k] += (r.r + (peak - r.r) * kw) * ci + r.r * hi; G[k] += (r.g + (peak - r.g) * kw) * ci + r.g * hi; B[k] += (r.b + (peak - r.b) * kw) * ci + r.b * hi;
      dmin[k] = Infinity;
    }
    nt = 0;
  }
  let cx0 = RW, cy0 = RH, cx1 = -1, cy1 = -1;               // last frame's dirty box (cleared before drawing)
  function render(out) {
    for (let y = Math.max(0, cy0); y <= cy1; y++) { const a = y * RW + cx0, b = y * RW + cx1 + 1; R.fill(0, a, b); G.fill(0, a, b); B.fill(0, a, b); Y.fill(0, a, b); }
    bx0 = RW; by0 = RH; bx1 = -1; by1 = -1;
    const seg = out.seg;
    for (let i = 0; i < out.n; i++) decodeAny(seg, i, recs[i]);
    let i = 0;
    while (i < out.n) {
      const r = recs[i];
      if (r.header) {                              // a figure group: nearest piece, light once
        for (let j = i + 1; j <= i + r.count && j < out.n; j++) visit(recs[j], j, 0);
        flush(); i += r.count + 1; continue;
      }
      if (r.I < 0.002 && r.glow < 0.002) { i++; continue; }
      let along = 0, j = i;
      for (;;) { along += visit(recs[j], j, along); if (recs[j].run && j + 1 < out.n && recs[j + 1].cont) j++; else break; }
      flush(); i = j + 1;
    }
    cx0 = bx0; cy0 = by0; cx1 = bx1; cy1 = by1;
    for (let y = Math.max(0, by0); y <= by1; y++) for (let x = bx0; x <= bx1; x++) {
      const k = y * RW + x;
      Y[k] = 0.2126 * Math.min(1, R[k]) + 0.7152 * Math.min(1, G[k]) + 0.0722 * Math.min(1, B[k]);
    }
    return { Y, box: [bx0, by0, bx1, by1] };
  }
  const sat = new Float64Array((RW + 1) * (RH + 1));
  function worstWindow(flags, stepDiv = 4) {
    for (let y = 0; y < RH; y++) { let row = 0; for (let x = 0; x < RW; x++) { row += flags[y * RW + x]; sat[(y + 1) * (RW + 1) + x + 1] = sat[y * (RW + 1) + x + 1] + row; } }
    const wW = Math.round(RW / 3), wH = Math.round(RH / 3), sx = Math.max(1, Math.round(wW / stepDiv)), sy = Math.max(1, Math.round(wH / stepDiv));
    let worst = 0;
    for (let ya = 0; ya + wH <= RH; ya += sy) for (let xa = 0; xa + wW <= RW; xa += sx) {
      const s = sat[(ya + wH) * (RW + 1) + xa + wW] - sat[ya * (RW + 1) + xa + wW] - sat[(ya + wH) * (RW + 1) + xa] + sat[ya * (RW + 1) + xa];
      if (s > worst) worst = s;
    }
    return worst / (wW * wH);
  }
  return { RW, RH, render, worstWindow };
}
// Drive an engine through a script and raster every frame. Returns the worst changed and lit share of any window, the
// worst share of the whole frame that changed, frames at or over 25 % and the most of them in any second.
function rasterRun(eng, events, { from, to, RW = 960, RH = 540, stepDiv = 4 }) {
  const rz = makeRaster(RW, RH);
  let prevY = new Float32Array(RW * RH), prevBox = [RW, RH, -1, -1];
  const changed = new Uint8Array(RW * RH), lit = new Uint8Array(RW * RH);
  const over = [];
  let worstChange = 0, worstLit = 0, worstFrame = 0, worstAt = 0, onsets = 0, est = 0, flagged = 0;
  drive(eng, events, { from, to, onFrame: (out, t) => {
    for (const e of out.events) if (e.type === "pulse") onsets++;
    est = Math.max(est, out.area.window);
    if (out.area.over) flagged++;
    const { Y, box } = rz.render(out);
    // only the union of this frame's and the last frame's dirty boxes can change
    const x0 = Math.min(box[0], prevBox[0]), y0 = Math.min(box[1], prevBox[1]), x1 = Math.max(box[2], prevBox[2]), y1 = Math.max(box[3], prevBox[3]);
    if (x1 < x0) { prevBox = box; return; }
    let nch = 0;
    changed.fill(0); lit.fill(0);
    for (let y = Math.max(0, y0); y <= y1; y++) for (let x = Math.max(0, x0); x <= x1; x++) {
      const k = y * RW + x, a = Y[k], b = prevY[k];
      if (Math.abs(a - b) >= 0.1 && Math.min(a, b) < 0.8) { changed[k] = 1; nch++; }
      if (a >= 0.1) lit[k] = 1;
      prevY[k] = a;
    }
    const ch = nch ? rz.worstWindow(changed, stepDiv) : 0, li = rz.worstWindow(lit, stepDiv);
    if (ch > worstChange) { worstChange = ch; worstAt = t; }
    worstLit = Math.max(worstLit, li);
    worstFrame = Math.max(worstFrame, nch / (RW * RH));
    if (ch >= 0.25) over.push(t);
    prevBox = box;
  } });
  let maxPerSecond = 0;
  for (let i = 0; i < over.length; i++) { let n = 0; for (let j = i; j < over.length && over[j] - over[i] < 1000; j++) n++; maxPerSecond = Math.max(maxPerSecond, n); }
  return { worstChange, worstLit, worstFrame, over: over.length, maxPerSecond, worstAt, onsets, est, flagged };
}
const pct = (x) => (100 * x).toFixed(1);
const RASTER_THEMES = { ...THEMES, white: { id: "white", L1: "#ffffff", L2: "#ffffff", W: "#ffffff" } };
function checkRaster(name, r) {
  assert.ok(r.worstChange < 0.25, `${name}: ${pct(r.worstChange)} % of a window changed in one frame (at ${r.worstAt.toFixed(0)} ms)`);
  assert.equal(r.over, 0, `${name}: ${r.over} frames over the area threshold`);
  assert.ok(r.worstFrame <= 0.08 + 1e-9, `${name}: ${pct(r.worstFrame)} % of the frame changed in one frame`);
}

test("A5a raster: the spec's scripts at 150 and 180 BPM change under a quarter of any window and 8 % of the frame", () => {
  const presses = (n, every, opts = {}) => (per) => Array.from({ length: n }, (_, i) => tap(2000 + i * every * per, 1, opts.hold ? opts.hold * per : 60)).flat();
  const scripts = [
    { name: "triple every beat, 2 bars", beats: 9, opts: { gateMode: "triple", patternMode: "fan", bankMode: "both", orderMode: "all" }, events: presses(8, 1) },
    { name: "one-two every beat (Night Sea)", beats: 9, theme: "night-sea", opts: { gateMode: "onetwo", patternMode: "fan", bankMode: "both", orderMode: "all" }, events: presses(8, 1) },
    { name: "16th roll held 2 bars (Golden Wings)", beats: 10, theme: "golden-wings", opts: { gateMode: "roll16", patternMode: "fan", bankMode: "mirror", orderMode: "all", section: "build" }, events: presses(1, 1, { hold: 8 }) },
    { name: "single fans, every 2 beats", beats: 13, opts: { gateMode: "single", patternMode: "fan", bankMode: "both", orderMode: "all" }, events: presses(6, 2) },
    { name: "starburst + crown", beats: 10, opts: { section: "drop" }, events: (per) => [...tap(2000, 1), ...tap(2000 + 2 * per, 1), ...tap(2000 + 4 * per, 1), ...tap(2000 + 6 * per, 1)] },
    { name: "the phrase, Vibrate on", beats: 5, opts: { patternMode: "fan", bankMode: "both", orderMode: "all", vibrate: true }, events: (per) => [{ t: 2000, fn: (e, x) => e.phrase(x, 1) }] },
    { name: "figures held, Vibrate on", beats: 6, opts: { shapeMode: "auto", vibrate: true, gateMode: "roll8" }, events: presses(1, 1, { hold: 4 }) },
  ];
  const rows = [];
  for (const bpm of [150, 180]) for (const s of scripts) {
    const per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: 41, clock: steadyClock(bpm), theme: THEMES[s.theme || "laser-green"], ...s.opts });
    const r = rasterRun(eng, s.events(per), { from: 1950, to: 2000 + s.beats * per });
    rows.push(`  raster ${bpm} BPM, ${s.name}: changed ${pct(r.worstChange)} % of a window, ${pct(r.worstFrame)} % of the frame; lit ${pct(r.worstLit)} %; ${r.onsets} onsets`);
    checkRaster(`${s.name} at ${bpm}`, r);
  }
  console.log(rows.join("\n"));
});

// Round-1 fix (verifier, must fix 4): with Vibrate OFF (the default) the flash-area check failed. The builder's own audit
// recipe reached 31.8 % of a window changing in one frame (Laser Green, 150, scissors/bar/mirror) and 26.9 % in white;
// moving single onsets (sweep, bloom's snap, zigzag's jumps, wave) reached 27-34 %; single presses every 0.55-0.75 beat
// 25-27 % and ~10 % of the frame. Root causes: the budget measured LIT area, not change; single onsets swept, drifted and
// snapped freely; press rate never selected the fast budget; overlapping halos were under-counted. These are the
// verifier's own cases, through the additive raster at 960 x 540 with sliding windows.
test("A5a raster, Vibrate off: the verifier's worst cases change under a quarter of any window and 8 % of the frame", () => {
  const rows = [];
  const run = (name, theme, bpm, opts, events, beats) => {
    const per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: opts.seed ?? 13, clock: steadyClock(bpm), theme: RASTER_THEMES[theme], section: "climax", ...opts });
    const r = rasterRun(eng, events(per), { from: 1950, to: 2000 + beats * per });
    rows.push(`  ${name} (${theme} ${bpm}): changed ${pct(r.worstChange)} %, frame ${pct(r.worstFrame)} %, lit ${pct(r.worstLit)} %, frames >= 25 %: ${r.over}`);
    checkRaster(`${name} (${theme} ${bpm})`, r);
  };
  // the builder's audit recipe (a hard press, a second inside the bar, a hold), Vibrate off: the verifier's worst runs
  const recipe = (per) => [...tap(2000, 1), ...tap(2000 + 2 * per, 1), ...tap(2000 + 4 * per, 1, 3 * per)];
  for (const [theme, bpm, pattern, gate, bank] of [["laser-green", 150, "scissors", "bar", "mirror"], ["white", 150, "scissors", "single", "A"],
    ["white", 180, "wave", "single", "mirror"], ["laser-green", 150, "cross", "military", "mirror"], ["laser-green", 180, "fan", "pushpull", "A"],
    ["white", 150, "bloom", "bar", "A"], ["white", 150, "cone", "single", "both"]]) {
    run(`audit ${pattern}/${gate}/${bank}`, theme, bpm, { seed: 31, patternMode: pattern, gateMode: gate, bankMode: bank, orderMode: "all" }, recipe, 9);
  }
  // moving single onsets: six full-velocity presses, one every 2.13 beats
  const slow = (per) => Array.from({ length: 6 }, (_, i) => tap(2000 + i * 2.13 * per, 1, 40)).flat();
  for (const [theme, bpm, pattern, gate, bank] of [["white", 180, "bloom", "bar", "A"], ["white", 150, "zigzag", "bar", "A"], ["white", 180, "zigzag", "single", "A"],
    ["laser-green", 150, "sweep", "bar", "A"], ["laser-green", 150, "sweep", "single", "call"], ["white", 180, "figure", "bar", "call"]]) {
    run(`moving ${pattern}/${gate}/${bank}`, theme, bpm, { patternMode: pattern, gateMode: gate, bankMode: bank, orderMode: "all" }, slow, 13);
  }
  // single presses faster than 3 a second with the dial on Single or Bar (each one a new single-onset hit before)
  for (const [theme, bpm, gate, every] of [["laser-green", 150, "single", 0.55], ["white", 180, "single", 0.75], ["laser-green", 150, "bar", 0.55], ["white", 150, "single", 0.55]]) {
    run(`dial ${gate}, a press every ${every} beat`, theme, bpm, { gateMode: gate, section: "any" }, (per) => Array.from({ length: Math.floor(8 / every) }, (_, i) => tap(2000 + i * every * per, 1, 40)).flat(), 10);
  }
  // auto gate, soft presses (velocity 0.44 gives Single), Scanner Sweep on Bank A
  run("auto soft sweep A", "laser-green", 150, { patternMode: "sweep", bankMode: "A", orderMode: "all" }, (per) => Array.from({ length: 6 }, (_, i) => tap(2000 + i * 5.13 * per, 0.44, 40)).flat(), 31);
  console.log(rows.join("\n"));
});

// The verifier's own full-resolution check: an additive raster at 1920 x 1080 with sliding windows, auto gate and soft
// presses (velocity 0.44 gives Single), Scanner Sweep with every head, Laser Green. Before round 1: 31.4 % of a window
// changed in one frame at 150 BPM on Bank A (the estimator read 18.6 %), up to 4 frames at 25 % or more in a second.
test("A5a raster at 1920 x 1080: the soft auto-gate sweep changes under a quarter of any window", () => {
  for (const [bpm, bank] of [[150, "A"], [180, "both"]]) {
    const per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: 13, clock: steadyClock(bpm), theme: THEMES["laser-green"], patternMode: "sweep", bankMode: bank, orderMode: "all", section: "climax" });
    const ev = Array.from({ length: 6 }, (_, i) => tap(2000 + i * 5.13 * per, 0.44, 40)).flat();
    const r = rasterRun(eng, ev, { from: 1950, to: 2000 + 31 * per, RW: 1920, RH: 1080, stepDiv: 8 });
    console.log(`  1920x1080 laser-green ${bpm} sweep ${bank}, vel 0.44: changed ${pct(r.worstChange)} % of a window (estimator ${pct(r.est)} %), frame ${pct(r.worstFrame)} %, lit ${pct(r.worstLit)} %, frames >= 25 %: ${r.over}`);
    checkRaster(`1080p sweep ${bpm} ${bank}`, r);
  }
});

// ------------------------------------------------------------- 8a. round 2: the budget holds in ordinary play --
// The tests marked "Round-2 fix" are the round-2 verifier's repros; each fails against the round-1 engine (commit
// 57aa0676) and passes now. Their scenes come from the verifier's probes: jittered human taps (a linear congruential
// generator and a sum-of-six gaussian, as the probes draw them), the v2 theme library read from the build spec's own
// JSON, and white set in the Custom slot.
const LIBRARY = (() => {
  const md = fs.readFileSync(new URL("../research/reviewed/keylab-liberation-2026-10-22/vj-lasers-v2-and-colour-themes-2026-10-24.md", import.meta.url), "utf8");
  return Object.fromEntries(JSON.parse(/```json\n([\s\S]*?)\n```/.exec(md)[1]).themes.map((t) => [t.id, t]));
})();
const WHITE = { id: "white", L1: "#ffffff", L2: "#ffffff", W: "#ffffff" };
const themeOf = (id) => (id === "white" ? WHITE : LIBRARY[id]);
const lcg = (seed) => { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; };
const gauss = (r) => { let u = 0; for (let i = 0; i < 6; i++) u += r(); return (u - 3) / Math.sqrt(0.5); };
// drive at a frame step from dtFn(j) (ms; dropped frames are a longer step), applying timed events
function driveDt(eng, events, { from, to, dtFn = () => F, onFrame = null }) {
  const ev = events.slice().sort((a, b) => a.t - b.t);
  let ei = 0;
  for (let j = 0, t = from; t < to; t += dtFn(j), j++) {
    while (ei < ev.length && ev[ei].t <= t) { const e = ev[ei++]; e.fn(eng, e.t); }
    const out = eng.frame(t);
    if (onFrame) onFrame(out, t, j);
  }
}

// Round-2 fix (verifier, must fix 4 again): figures (Shape auto) under a loop dial with Vibrate, tapped by hand once a
// beat. Round 1 fitted a loop on its first beat only (its first four steps), but a figure morphs into the next of its 16
// figures every beat: a hit fitted on a triangle lit a 4-ring tunnel at full light on beat 2. In white (the Custom slot)
// 26.2 % of a window changed in one frame (25.9 % at 1920 x 1080), in Temple Light at full velocity 25.4 %, and the
// engine's own estimate read 29.7 % (area.over). And the per-frame check could only dim a figure, to 0.25 at the least,
// and when that left it one step short it put the whole frame back intact. Now the fit covers the loop's whole 16-beat
// cycle, each figure gives way on its own (a dense one sharpens and dims, a sparse one keeps its light), and the
// per-frame check keeps its best reduction.
test("A5a raster, round 2: figures under a loop dial with Vibrate, tapped by hand once a beat, in white and Temple Light at 128 BPM", () => {
  const bpm = 128, per = 60000 / bpm, rows = [];
  const run = (name, theme, gate, vel, jitter, seed, n, beats, size = {}) => {
    const r = lcg(seed);
    const eng = L.createLaserEngine({ seed: 17, clock: steadyClock(bpm), theme, section: "climax", shapeMode: "auto", vibrate: true, gateMode: gate });
    const ev = Array.from({ length: n }, (_, i) => tap(2000 + i * per + gauss(r) * jitter, vel, 60)).flat();
    const res = rasterRun(eng, ev, { from: 1950, to: 2000 + beats * per, ...size });
    rows.push(`  ${name}: changed ${pct(res.worstChange)} % of a window (estimator ${pct(res.est)} %), frame ${pct(res.worstFrame)} %, frames >= 25 %: ${res.over}, frames over budget: ${res.flagged}`);
    checkRaster(name, res);
    assert.equal(res.flagged, 0, `${name}: ${res.flagged} frames went out over the engine's own budget`);
  };
  for (const gate of ["stutter", "military", "stopshort"]) {
    run(`white ${gate}, vel 0.9`, WHITE, gate, 0.9, 15, bpm * 7 + 35, 12, 15);
    run(`Temple Light ${gate}, vel 1.0`, LIBRARY["temple-light"], gate, 1, 12, bpm * 7 + 3 + 17, 14, 16);
  }
  run("white stutter, vel 0.9, 1920 x 1080", WHITE, "stutter", 0.9, 15, bpm * 7 + 35, 12, 15, { RW: 1920, RH: 1080, stepDiv: 8 });
  console.log(rows.join("\n"));
});

// Round-2 fix (verifier, must fix 4, cause B): the per-frame check alone. With the fit switched off, every pulse onset
// of a white tunnel under the stutter dial (Vibrate on) goes out inside the fast budget: the check now keeps the best
// reduction it finds and may dim a hit whose every line is new down to almost nothing (a blurred line's band stays as
// wide from about 0.6 of full light down to 0.15). Before, onsets went out at 16.3 % and 19.7 %, flagged over. (Light
// that goes dark cannot be taken back, so the frames after an onset are the fit's to keep.)
test("the per-frame check alone keeps its best reduction: with the fit off, every onset of a white tunnel fits", () => {
  const bpm = 128, per = 60000 / bpm;
  const eng = L.createLaserEngine({ seed: 17, clock: steadyClock(bpm), theme: WHITE, shapeMode: "tunnel", gateMode: "stutter", vibrate: true, section: "climax" });
  eng._fitHit = () => {};
  let onsets = 0, worst = 0;
  drive(eng, tap(2000, 0.9, 60), { from: 1950, to: 2000 + 3 * per, onFrame: (out, t) => {
    if (!out.events.some((e) => e.type === "pulse")) return;
    onsets++; worst = Math.max(worst, out.area.window);
    assert.ok(out.area.window <= L.BUDGET.fast.window + 1e-9 && !out.area.over, `onset at ${t.toFixed(0)} ms: ${pct(out.area.window)} % of a window`);
  } });
  assert.ok(onsets >= 4, `${onsets} onsets`);
  console.log(`  fit off, white tunnel stutter: ${onsets} onsets, the worst ${pct(worst)} % of a window`);
});

// Round-2 fix (verifier, must fix 2): in ordinary play the engine sent frames over its own budget (area.over): spec 4.1
// rule 3 caps a gated pulse at 15 % of a window and spec 4.3 expects zero limiter interventions. These are the A5-style
// runs across the whole theme library and white: in white the A5a grid (every pattern x gate, bank rotated, 150 and 180
// BPM, Vibrate off and on); in every theme the spec's A5 scripts at 128, 150 and 180 BPM, and figures under each loop
// dial with jittered quarter-note taps, Vibrate on and off. The round-1 engine sent 1,621 frames over budget in these
// runs and the rest of each theme's grid (231 in white); none now.
test("A5, round 2: no frame goes out over its budget across the 21 library themes and white", () => {
  const GATES = ["single", "onetwo", "triple", "triplet", "bar", "tttou", "roll8", "roll16", "stutter", "military", "pushpull", "revbass", "doubling", "stopshort", "inhale"];
  const bad = [];
  let runs = 0, frames = 0;
  const go = (name, eng, ev, beats, per) => {
    runs++;
    let over = 0;
    drive(eng, ev, { from: 1950, to: 2000 + beats * per, onFrame: (out) => { frames++; if (out.area.over) over++; } });
    if (over) bad.push(`${name}: ${over}`);
  };
  for (const bpm of [150, 180]) for (const pattern of L.PATTERN_IDS) for (const gate of GATES) for (const vibrate of [false, true]) {
    const bank = ["both", "mirror", "A"][(L.PATTERN_IDS.indexOf(pattern) + GATES.indexOf(gate)) % 3], per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: 31, clock: steadyClock(bpm), theme: WHITE, patternMode: pattern, gateMode: gate, bankMode: bank, orderMode: "all", vibrate, section: "climax" });
    go(`white grid ${bpm} ${pattern}/${gate}/${bank}${vibrate ? "/vib" : ""}`, eng, [...tap(2000, 1), ...tap(2000 + 2 * per, 1), ...tap(2000 + 4 * per, 1, 3 * per)], 9, per);
  }
  const presses = (n, every, hold = 60) => (per) => Array.from({ length: n }, (_, i) => tap(2000 + i * every * per, 1, hold === "bars" ? 8 * per : hold)).flat();
  const scripts = [
    ["triple every beat", 9, { gateMode: "triple", patternMode: "fan", bankMode: "both", orderMode: "all" }, presses(8, 1)],
    ["one-two every beat", 9, { gateMode: "onetwo", patternMode: "fan", bankMode: "both", orderMode: "all" }, presses(8, 1)],
    ["16th roll held", 10, { gateMode: "roll16", patternMode: "fan", bankMode: "mirror", orderMode: "all", section: "build" }, presses(1, 1, "bars")],
    ["single fans", 13, { gateMode: "single", patternMode: "fan", bankMode: "both", orderMode: "all" }, presses(6, 2)],
    ["starburst + crown", 10, { section: "drop" }, presses(4, 2)],
    ["the phrase, Vibrate", 5, { patternMode: "fan", bankMode: "both", orderMode: "all", vibrate: true }, () => [{ t: 2000, fn: (e, x) => e.phrase(x, 1) }]],
    ["figures held, Vibrate", 6, { shapeMode: "auto", vibrate: true, gateMode: "roll8" }, (per) => tap(2000, 1, 4 * per)],
  ];
  for (const id of [...Object.keys(LIBRARY), "white"]) {
    for (const bpm of [128, 150, 180]) for (const [name, beats, opts, ev] of scripts) {
      const per = 60000 / bpm;
      go(`${id} ${name} ${bpm}`, L.createLaserEngine({ seed: 41, clock: steadyClock(bpm), theme: themeOf(id), ...opts }), ev(per), beats, per);
    }
    for (const bpm of [128, 150]) for (const gate of ["stutter", "military", "stopshort", "roll16", "roll8", "doubling"]) for (const vib of [true, false]) {
      const per = 60000 / bpm, r = lcg(bpm * 13 + gate.length * 7 + (vib ? 1 : 0));
      const eng = L.createLaserEngine({ seed: 17, clock: steadyClock(bpm), theme: themeOf(id), section: "climax", shapeMode: "auto", vibrate: vib, gateMode: gate });
      go(`${id} figures ${gate} ${bpm}${vib ? " vib" : ""}`, eng, Array.from({ length: 12 }, (_, i) => tap(2000 + i * per + gauss(r) * 15, 0.9, 60)).flat(), 15, per);
    }
  }
  console.log(`  ${runs} runs, ${frames} frames: ${bad.length ? bad.length + " runs went over budget" : "no frame over budget"}`);
  assert.deepEqual(bad, [], `frames over budget: ${bad.slice(0, 12).join(", ")}`);
});

// Round-2 fix (verifier, must fix 2): the verifier's realistic play -- a human on pad 2 for 20 s a run (8th and 16th
// mashing, quarter and dotted presses, holds, the phrase, bar presses; the dial, Vibrate, Shape and bank changed now and
// then), library themes and white, 120-180 BPM, at a steady 60 fps and with 4 % of frames dropped. The round-1 engine
// sent frames over budget in each of these runs (26 frames in the steady ones, 15 with drops); none now. What they
// caught besides the figures: a rapid press changed a roll's velocity mid-pulse (a lit figure's size follows it), a
// harder rapid press widened a roll past its fit, barswap flipped a lit pulse's colours on the bar line, a ringing beam
// whose band was set by its blur could not give way, and a dropped frame doubled a ringing figure's step.
test("realistic mashing (the verifier's 20 s runs), steady and with dropped frames: no frame goes out over its budget", () => {
  const themeIds = [...Object.keys(LIBRARY), "white"];
  const pick = (r, a) => a[Math.floor(r() * a.length)];
  const rows = [];
  for (const [run, drop] of [[18, false], [19, false], [22, false], [24, false], [27, false], [28, false], [104, true], [108, true], [113, true], [116, true]]) {
    const r = L.makeRng(run, "mash-r1");
    const bpm = pick(r, [120, 128, 140, 150, 160, 174, 180]), per = 60000 / bpm, th = pick(r, themeIds);
    const cfg = { seed: run, clock: steadyClock(bpm), theme: themeOf(th), section: pick(r, ["climax", "drop", "build", "groove", "anti", "break"]),
      vibrate: r() < 0.5, shapeMode: r() < 0.25 ? "auto" : null, gateMode: r() < 0.6 ? "auto" : pick(r, L.GATE_IDS),
      bankMode: r() < 0.5 ? "auto" : pick(r, Object.keys(L.BANK_MODES)) };
    const eng = L.createLaserEngine(cfg);
    const ev = [], end = 2000 + 20000;
    for (let t = 2000; t < end;) {
      const style = r();
      if (style < 0.25) {
        const div = r() < 0.6 ? 0.5 : 0.25, n = 4 + Math.floor(r() * 12);
        for (let i = 0; i < n; i++) { const tt = t + i * div * per + gauss(r) * 12; ev.push({ t: tt, fn: (e, x) => e.hit(x, 0.5 + 0.5 * r()) }, { t: tt + 35, fn: (e, x) => e.release(x) }); }
        t += n * div * per;
      } else if (style < 0.5) {
        const div = pick(r, [1, 0.75, 2 / 3, 1.5]), n = 3 + Math.floor(r() * 6);
        for (let i = 0; i < n; i++) { const tt = t + i * div * per + gauss(r) * 15; ev.push({ t: tt, fn: (e, x) => e.hit(x, r()) }, { t: tt + 50, fn: (e, x) => e.release(x) }); }
        t += n * div * per;
      } else if (style < 0.65) {
        const hold = (1 + Math.floor(r() * 6)) * per;
        ev.push({ t, fn: (e, x) => e.hit(x, 0.4 + 0.6 * r()) }, { t: t + hold, fn: (e, x) => e.release(x) });
        t += hold + per * r();
      } else if (style < 0.75) {
        ev.push({ t, fn: (e, x) => e.phrase(x, 0.7 + 0.3 * r()) });
        t += per * (1 + Math.floor(r() * 3));
      } else if (style < 0.85) {
        const n = 2 + Math.floor(r() * 4);
        for (let i = 0; i < n; i++) { const tt = t + i * 4 * per + gauss(r) * 20; ev.push({ t: tt, fn: (e, x) => e.hit(x, 0.6 + 0.4 * r()) }, { t: tt + 60, fn: (e, x) => e.release(x) }); }
        t += n * 4 * per;
      } else {
        const a = r();
        if (a < 0.3) ev.push({ t, fn: (e) => e.set({ gateMode: r() < 0.4 ? "auto" : pick(r, L.GATE_IDS) }) });
        else if (a < 0.55) ev.push({ t, fn: (e, x) => e.setVibrate(r() < 0.5, x) });
        else if (a < 0.75) ev.push({ t, fn: (e) => e.set({ shapeMode: r() < 0.6 ? null : "auto" }) });
        else ev.push({ t, fn: (e) => e.set({ bankMode: r() < 0.4 ? "auto" : pick(r, Object.keys(L.BANK_MODES)) }) });
        t += per * r() * 2;
      }
    }
    const dr = L.makeRng(run, "drop-r1");
    let over = 0, frames = 0;
    driveDt(eng, ev, { from: 1950, to: end + 3 * per, dtFn: () => (drop && dr() < 0.04 ? 33.33 : F), onFrame: (out) => { frames++; if (out.area.over) over++; } });
    rows.push(`run ${run}${drop ? " (drops)" : ""} ${th} ${bpm}: ${over} of ${frames} frames over budget`);
    assert.equal(over, 0, `mashing run ${run}${drop ? " with dropped frames" : ""} (${th}, ${bpm} BPM): ${over} frames over budget`);
  }
  console.log("  " + rows.join("; "));
});

// Round-2 fix (from the realistic runs): a rapid press reaches a running roll at its NEXT pulse. Its velocity used to
// land at once, and a lit figure's size (and a lit beam's width) follows the velocity: the whole figure moved in one
// frame (16.7-18.3 % of a window, over budget). Before: the figure moved within a lit pulse; now never.
test("a rapid press never moves a lit figure: its velocity reaches the roll at the next pulse", () => {
  for (const [bpm, gate, v0, v1] of [[128, "roll8", 0.9, 0.4], [150, "roll16", 1, 0.2]]) {
    const per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: 5, clock: steadyClock(bpm), theme: WHITE, shapeMode: "auto", gateMode: gate, section: "climax" });
    // a burst, then a roll spawned hard and stretched by softer rapid presses (one every 0.45 beat)
    const ev = [...tap(2000, v0, 40), ...Array.from({ length: 6 }, (_, i) => tap(2000 + (i + 1) * 0.45 * per, i === 0 ? v0 : v1, 30)).flat()];
    let prevKey = null, prev = null, moved = 0, lit = 0;
    drive(eng, ev, { from: 1950, to: 2000 + 5 * per, onFrame: (out) => {
      const H = eng.hits.find((h) => h.started && !h.done && h.on);
      const key = H ? `${H.id}:${H.cur.onFrame}` : null, xs = [];
      eachLine(out, (r) => { if (r.kind === L.KIND.FIGURE) xs.push(r.x0, r.y0, r.x1, r.y1); });
      if (key && key === prevKey && prev && prev.length === xs.length) {
        lit++;
        if (xs.some((x, i) => Math.abs(x - prev[i]) > 1e-6)) moved++;
      }
      prevKey = key; prev = xs;
    } });
    assert.ok(lit > 10, `${lit} lit frame pairs`);
    assert.equal(moved, 0, `${gate} at ${bpm}: the lit figure moved in ${moved} frames`);
  }
});

// Round-2 fix (from the realistic runs): a harder rapid press never widens a roll past the velocity it was fitted at
// (it used to take the press's velocity: a roll fitted at 0.6 drew 0.93's wider, hotter beams, and went dark at 15.3 %
// of a window). Before: cores 2.63 px at the first press, 3.56 px later; now 2.63 px throughout.
test("a harder rapid press never widens a roll past the press it was fitted for", () => {
  for (const [bpm, gate] of [[128, "roll8"], [150, "roll16"]]) {
    const per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: 9, clock: steadyClock(bpm), theme: LIBRARY["laser-green"], patternMode: "zigzag", gateMode: gate, bankMode: "both", orderMode: "oddeven", section: "anti" });
    const ev = [...tap(2000, 0.6, 30), ...Array.from({ length: 8 }, (_, i) => tap(2000 + (i + 1) * 0.4 * per, i === 0 ? 0.6 : 1, 30)).flat()];
    let first = 0, widest = 0;
    drive(eng, ev, { from: 1950, to: 2000 + 5 * per, onFrame: (out, t) => {
      eachLine(out, (r) => { if (r.I < 0.01) return; if (t < 2000 + 0.4 * per) first = Math.max(first, r.width); widest = Math.max(widest, r.width); });
    } });
    assert.ok(first > 0);
    assert.ok(widest <= first + 1e-9, `${gate} at ${bpm}: cores ${first.toFixed(3)} px at the first press, ${widest.toFixed(3)} px later`);
  }
});

// Round-2 fix (from the realistic runs): barswap swaps the sides' colours on the bar line the PULSE lands on, so a lit
// pulse (or its tail) never changes colour mid-flight. It read the live beat position: a lit figure in Fire and Ice
// flipped from blue to white as a bar line passed, every line at once (16.8 % of a window, over budget, and nothing could
// give way: the lines stood still). Before: 144 lit lines jumped colour between frames with no new pulse; now none.
test("barswap never changes a lit pulse's colour: the swap waits for the next onset", () => {
  const bpm = 128, per = 60000 / bpm;
  const eng = L.createLaserEngine({ seed: 3, clock: steadyClock(bpm), theme: LIBRARY["fire-and-ice"], colourMode: "barswap", gateMode: "triple", shapeMode: "auto", section: "climax" });
  // a triple whose last pulse and tail span a bar line, three times (a burst each: two bars apart)
  const ev = [3.2, 11.2, 19.2].flatMap((b) => tap(b * per, 0.9, 40));
  const last = new Map();
  let jumps = 0, compared = 0;
  drive(eng, ev, { from: 3 * per, to: 22 * per, onFrame: (out) => {
    const buf = eng.drawn, now = new Map();
    for (let i = 0; i < buf.n; i++) { const o = i * L.W_FLOATS; now.set(buf.keys[i], [buf.W[o + L.W.R], buf.W[o + L.W.G], buf.W[o + L.W.B], buf.W[o + L.W.I] + buf.W[o + L.W.GLOW]]); }
    if (!out.events.some((e) => e.type === "pulse")) {
      for (const [k, c] of now) {
        const p = last.get(k);
        if (!p || p[3] < 0.05 || c[3] < 0.05) continue;
        compared++;
        if (Math.max(Math.abs(c[0] - p[0]), Math.abs(c[1] - p[1]), Math.abs(c[2] - p[2])) > 0.5) jumps++;
      }
    }
    last.clear(); for (const [k, c] of now) last.set(k, c);
  } });
  assert.ok(compared > 500, `${compared} lit lines compared`);
  assert.equal(jumps, 0, `${jumps} lit lines jumped colour between frames`);
});

// Round-2 fix (from the realistic runs): a ringing beam hit whose band is set by its blur band gives way by sharpening.
// The fit could only dim it, thin it and trim heads, but a blurred line's band stays as wide from about 0.6 of full light
// down to 0.15: an escalated chase triplet (call bank, Vibrate) ran every lever to its floor (one head a step, light 0.3)
// and still went dark at 15.2 %. Before: over budget in white, Temple Light and Limbo; now never.
test("a ringing beam hit whose lines are blur-bound sharpens to fit: an escalated chase triplet with Vibrate", () => {
  for (const [id, bpm, gate] of [["white", 128, "triplet"], ["white", 150, "triple"], ["temple-light", 128, "triplet"], ["limbo", 128, "triplet"]]) {
    const per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: 24, clock: steadyClock(bpm), theme: themeOf(id), patternMode: "chase", gateMode: gate, bankMode: "call", orderMode: "oddeven", vibrate: true, section: "anti" });
    let over = 0;
    drive(eng, [...tap(2000, 0.88, 50), ...tap(2000 + 2 * per, 0.88, 50), ...tap(2000 + 4.1 * per, 0.88, 50)], { from: 1950, to: 2000 + 9 * per, onFrame: (out) => { if (out.area.over) over++; } });
    assert.equal(over, 0, `${id} ${bpm} chase/${gate}: ${over} frames over budget`);
  }
});

// Round-2 fix (from the realistic runs, 4 % of frames dropped): the strings keep their own clock, which follows the
// frame clock but never steps more than 1.2 frames at once (catching up 0.2 frame a frame), so a dropped frame cannot
// double a ringing line's step. A figure roll ringing in Golden Wings at 160 BPM with one frame dropped late in a lit
// pulse: before, 16.7 % of a window (over budget) against 13.5 % with no drop; with the fixes but not this clock, 14.3 %
// against 11.7 %; now the drop adds nothing.
test("a dropped frame never doubles a ringing figure's step: the strings keep their own clock", () => {
  const bpm = 160, per = 60000 / bpm;
  const worstWith = (drops) => {
    const eng = L.createLaserEngine({ seed: 104, clock: steadyClock(bpm), theme: LIBRARY["golden-wings"], section: "break", vibrate: true, shapeMode: "auto", bankMode: "A" });
    const ev = [[2728, 0.79], [2927, 0.67], [3108, 0.94], [3304, 0.59], [3480, 0.68], [3659, 0.81], [3851, 0.74]].flatMap(([t, v]) => tap(t, v, 35));
    let worst = 0, over = 0;
    // frames on the 60 fps grid from 1950 ms, skipping the dropped ones
    const grid = (j) => 1950 + j * F, dropped = (t) => drops.some((d) => Math.abs(t - d) < 1);
    let j = 0;
    driveDt(eng, ev, { from: 1950, to: 5000, dtFn: () => { let k = j + 1; while (dropped(grid(k))) k++; const dt = grid(k) - grid(j); j = k; return dt; },
      onFrame: (out) => { worst = Math.max(worst, out.area.window); if (out.area.over) over++; } });
    return { worst, over };
  };
  const clean = worstWith([]), dropped = worstWith([1950 + 122 * F]);    // the frame at 3983 ms
  console.log(`  ringing figure roll, Golden Wings 160: worst ${pct(clean.worst)} % with no drop, ${pct(dropped.worst)} % with a frame dropped late in a lit pulse`);
  assert.equal(dropped.over, 0, "no frame over budget with the drop");
  assert.ok(dropped.worst <= clean.worst + 0.005, `the dropped frame added change: ${pct(dropped.worst)} % against ${pct(clean.worst)} %`);
});

// ------------------------------------------------------------------------- 8b. what the contact sheet caught --
// Round-1 fix (verifier, must fix 5): the output was 4 texels a segment, a ringing beam 8 segments (32 taps) and a figure
// 96 segments with no way to skip them (384 taps); the halo had no cutoff. Now: 2 texels a record, a ringing beam is ONE
// record bent by the shader, a figure sits behind a group header a pixel can skip with one fetch, and HALO_CUTOFF_PX.
test("the output: 2 texels a record, one record per beam, figures behind a skippable group header", () => {
  assert.equal(L.SEG_TEXELS, 2);
  assert.equal(L.SEG_FLOATS, 8);
  assert.ok(L.HALO_CUTOFF_PX > 0 && L.HALO_CUTOFF_PX <= 64);
  const clk = steadyClock(150), per = 400;
  // heavy play, Vibrate on, figures included: no record is ever more than one beam, every group is well formed
  let maxN = 0, groups = 0, rings = 0, maxPieces = 0;
  for (const opts of [{ vibrate: true }, { vibrate: true, shapeMode: "auto" }, { vibrate: true, patternMode: "cone" }]) {
    const eng = L.createLaserEngine({ seed: 9, clock: clk, section: "climax", ...opts });
    const ev = [];
    for (let i = 0; i < 24; i++) ev.push(...tap(2000 + i * 1.6 * per, VELS[i % VELS.length], i % 5 === 0 ? 2 * per : 60));
    drive(eng, ev, { from: 1950, to: 2000 + 42 * per, onFrame: (out) => {
      maxN = Math.max(maxN, out.n);
      for (let i = 0; i < out.n; i++) {
        const r = L.decodeSeg(out.seg, i, {});
        for (let q = 0; q < 8; q++) assert.ok(Number.isFinite(out.seg[i * 8 + q]) && (q < 4 || (out.seg[i * 8 + q] >= 0 && out.seg[i * 8 + q] < 2 ** 24 && Number.isInteger(out.seg[i * 8 + q]))), "texel 1 holds exact 24-bit integers");
        if (r.header) {
          groups++;
          assert.equal(out.head[i], -1);
          assert.ok(r.count >= 1 && i + r.count < out.n, "a group's pieces follow its header");
          maxPieces = Math.max(maxPieces, r.count);
          for (let j = i + 1; j <= i + r.count; j++) {
            const p = L.decodeSeg(out.seg, j, {});
            assert.ok(!p.header && p.kind === 1, "a group holds figure pieces only");
            for (const [x, y] of [[p.x0, p.y0], [p.x1, p.y1]]) assert.ok(Math.hypot(x - r.cx, y - r.cy) <= r.radius + 1e-6, "inside the group's radius");
          }
          i += r.count;
          continue;
        }
        if (r.ring) rings++;
        assert.equal(r.kind, 0, "a line outside a group is a beam");
      }
    } });
  }
  console.log(`  records: at most ${maxN} rows a frame; ${groups} figure groups (up to ${maxPieces} pieces); ${rings} ringing beams as single records`);
  assert.ok(rings > 50, "Vibrate rang beams as single records");
  assert.ok(groups > 50, "figures came behind headers");
  // the packing round-trips the engine's own records within its quantisation
  const eng = L.createLaserEngine({ seed: 9, clock: clk, vibrate: true, section: "climax" });
  let checked = 0;
  drive(eng, tap(2000, 0.9), { from: 1950, to: 2600, onFrame: (out) => {
    const d = eng.drawn;
    for (let i = 0, k = 0; i < out.n; i++) {
      const r = L.decodeSeg(out.seg, i, {});
      if (r.header) continue;
      const o = k * L.W_FLOATS; k++;
      assert.ok(Math.abs(r.I - d.W[o + L.W.I]) < 1e-3 && Math.abs(r.glow - d.W[o + L.W.GLOW]) < 1e-3);
      assert.ok(r.width <= d.W[o + L.W.WIDTH] + 1e-9 && d.W[o + L.W.WIDTH] - r.width < 1 / 16 && Math.abs(r.blur - d.W[o + L.W.BLUR]) <= 1 / 8 + 1e-9);
      assert.ok(Math.abs(r.c1 - d.W[o + L.W.C1]) <= L.RING_Q[0] / 2 + 1e-9);
      for (const [a, b] of [[r.r, d.W[o + L.W.R]], [r.g, d.W[o + L.W.G]], [r.b, d.W[o + L.W.B]]]) assert.ok(Math.abs(Math.sqrt(a) - Math.sqrt(b)) <= 0.5 / 255 + 1e-6, "colour within its 8-bit step");
      checked++;
    }
  } });
  assert.ok(checked > 10);
});

test("a capped step keeps whole mirrored rings: the rig stays symmetric and a two-bank cage really crosses", () => {
  const clk = steadyClock(150);
  for (const [bank, gate] of [["both", "single"], ["both", "triple"], ["A", "triple"], ["mirror", "roll16"]]) {
    const eng = L.createLaserEngine({ seed: 15, clock: clk, patternMode: "cage", bankMode: bank, orderMode: "all", gateMode: gate });
    eng.frame(1990); eng.hit(2000, 1);
    const step = eng.hits[0].steps[0];
    const us = step.map((h) => L.HEADS[h].u).sort((a, b) => a - b);
    assert.ok(Math.abs(us.reduce((a, b) => a + b, 0)) < 1e-9, `${bank}/${gate}: left and right balance (${step.map((h) => L.HEADS[h].name)})`);
    let out = null;
    for (let j = 0; j < 8 && !(out && out.n); j++) out = eng.frame(2040 + j * F);
    const slopes = new Set();
    eachLine(out, (r) => slopes.add(Math.sign((r.y1 - r.y0) * (r.x1 - r.x0))));
    assert.ok(slopes.has(1) && slopes.has(-1), `${bank}/${gate}: two families that cross`);
  }
});

test("a gradient round a closed figure has no seam; across a fan it runs end to end", () => {
  const clk = steadyClock(150);
  const eng = L.createLaserEngine({ seed: 3, clock: clk, theme: THEMES["night-sea"], patternMode: "figure", shapeMode: "circle", colourMode: "gradient", gateMode: "single" });
  eng.frame(1990); eng.hit(2000, 0.8);
  let out = null;
  for (let j = 0; j < 10 && !(out && out.n); j++) out = eng.frame(2000 + j * F);
  const cols = [];
  eachLine(out, (r) => cols.push([r.r, r.g, r.b]));
  const first = cols[0], last = cols[cols.length - 1], mid = cols[cols.length >> 1];
  assert.ok(Math.hypot(first[0] - last[0], first[1] - last[1], first[2] - last[2]) < 0.03, "the loop closes on one colour");
  assert.ok(Math.hypot(first[0] - mid[0], first[1] - mid[1], first[2] - mid[2]) > 0.1, "and turns through the second colour");
});

// ------------------------------------------------------------------------------------- 9. the output format --
test("the output: the records, head and pad lights, the strip bus, and no red ever", () => {
  const clk = steadyClock(150), per = 400;
  for (const theme of [THEMES.limbo, THEMES["red-tribe"], { L1: "#ff0000", L2: "#ee0505" }, THEMES["golden-wings"]]) {
    const eng = L.createLaserEngine({ seed: 5, clock: clk, theme, section: "climax", vibrate: true });
    const ev = [];
    for (let i = 0; i < 12; i++) ev.push(...tap(2000 + i * 2.5 * per, VELS[i]));
    let sawSolo = false, sawPad = new Set(), sawHeads = false;
    drive(eng, ev, { from: 1950, to: 2000 + 32 * per, onFrame: (out) => {
      assert.ok(out.seg instanceof Float32Array && out.seg.length === L.MAX_SEGMENTS * L.SEG_FLOATS);
      assert.ok(out.n >= 0 && out.n <= L.MAX_SEGMENTS);
      for (let i = 0; i < out.n * L.SEG_FLOATS; i++) assert.ok(Number.isFinite(out.seg[i]));
      eachLine(out, (r, i, h) => {
        for (const c of [r.r, r.g, r.b]) assert.ok(c >= 0 && c <= 1);
        assert.ok([0, 1].includes(r.kind));
        assert.ok(h >= 0 && h < L.HEADS.length);
        if (r.I > 0.002 || r.glow > 0.002) assert.ok(!L.isSaturatedRed([r.r, r.g, r.b]), "never a saturated red");
      });
      assert.equal(out.heads.length, L.HEADS.length);
      assert.equal(out.padGrid.length, 12);
      if (out.solo < 1) sawSolo = true;
      sawPad.add(out.pad.level);
      if (out.heads.some((x) => x > 0)) sawHeads = true;
      const bus = L.stripBus(eng);
      assert.equal(bus.length, 24);
      for (let p = 0; p < 12; p++) assert.ok(bus[4 + p] >= 0 && bus[4 + p] < 1);
    } });
    assert.ok(sawSolo && sawHeads);
    for (const lv of sawPad) assert.ok([0, 0.6, 0.8, 1].includes(lv), `pad level ${lv}`);
    assert.ok(sawPad.has(0.6) && sawPad.has(0.8), "the pad shows the tier");
  }
  const c = L.themeColours({ L1: "#ff0000" });
  assert.deepEqual(c.L1, [1, 1, 1], "a red laser colour is replaced by white");
  const limbo = L.themeColours(THEMES.limbo);
  assert.ok(!L.isSaturatedRed(limbo.W), "a held red W never reaches a laser");
  assert.deepEqual(L.catalogue().patterns.length, 17);
});

// ------------------------------------------------------------------------------------------- 10. round 3 --
// The verifier's round-2 must-fixes. Round 2 fitted each hit alone and drew hits together (two Reverse-Bass loops
// pressed a beat apart lit the same off-beats twice and went dark in the same frame), and its acceptance held only on
// the seeds it was tuned on. Each test below fails on the round-2 engine (a9bb0554) and passes now. The acceptance runs
// draw FRESH seeds: every run of this file takes a new base, printed with the result; replay a failure with
// LASERS_SEED=<base> node --test tests/vj_lasers.test.mjs.
const FRESH = Number(process.env.LASERS_SEED) || (Date.now() % 1000000007);
// hits lit (any light) in a frame
const litHits = (eng) => eng.hits.filter((h) => h.started && !h.done && h.level01 > 0.002).length;

// Round-3 fix (must fix 1, the verifier's repro): the crown under the Reverse-Bass dial, 8 presses exactly a beat apart
// at 165 BPM, white, Vibrate on. Each press is a 2-beat loop pulsing on the off-beat, so pressing once a beat left two
// loops lighting every off-beat: round 2 sent 7 of 222 frames over its own budget (estimate 25.2-26.3 % against 22 %,
// raster 17.8-18.7 %), seeds 1-3 alike. Now a new loop takes the grid over from its first pulse (the older one fires
// nothing from there; if it is already lighting that very pulse, the new one starts a step later), so each off-beat
// shows one crown and one hit is lit at a time.
test("Round 3: the Reverse-Bass Gate pressed once a beat -- a new loop takes the grid over, one crown per off-beat, never over budget", () => {
  const bpm = 165, per = 60000 / bpm, rows = [];
  for (const seed of [1, 2, 3]) {
    const ev = Array.from({ length: 8 }, (_, i) => tap(2000 + i * per, 0.85, 60)).flat();
    const res = rasterRun(L.createLaserEngine({ seed, clock: steadyClock(bpm), theme: WHITE, patternMode: "crown", gateMode: "revbass", vibrate: true }), ev, { from: 1950, to: 2000 + 10 * per });
    rows.push(`seed ${seed}: estimate worst ${pct(res.est)} %, raster ${pct(res.worstChange)} %, frames over budget ${res.flagged}, onsets ${res.onsets}`);
    checkRaster(`crown/revbass seed ${seed}`, res);
    assert.equal(res.flagged, 0, `seed ${seed}: ${res.flagged} frames over the engine's own budget`);
    assert.ok(res.est <= L.BUDGET.single.window + 1e-9, `seed ${seed}: estimate ${pct(res.est)} %`);
    assert.ok(res.onsets >= 8, `seed ${seed}: every off-beat still pulses (${res.onsets} onsets)`);
    const eng = L.createLaserEngine({ seed, clock: steadyClock(bpm), theme: WHITE, patternMode: "crown", gateMode: "revbass", vibrate: true });
    let most = 0;
    drive(eng, ev, { from: 1950, to: 2000 + 10 * per, onFrame: () => { most = Math.max(most, litHits(eng)); } });
    assert.equal(most, 1, `seed ${seed}: ${most} hits lit in one frame`);
  }
  // ... and with Vibrate off, rastered at 1920 x 1080 with windows slid in eighth steps (round 2: 7 frames over budget,
  // estimate 22.7 %, raster 18.7 %)
  const ev = Array.from({ length: 8 }, (_, i) => tap(2000 + i * per, 0.85, 60)).flat();
  const res = rasterRun(L.createLaserEngine({ seed: 1, clock: steadyClock(bpm), theme: WHITE, patternMode: "crown", gateMode: "revbass", vibrate: false }), ev,
    { from: 1950, to: 2000 + 10 * per, RW: 1920, RH: 1080, stepDiv: 8 });
  rows.push(`Vibrate off, 1920 x 1080: estimate worst ${pct(res.est)} %, raster ${pct(res.worstChange)} %, frames over budget ${res.flagged}`);
  checkRaster("crown/revbass, Vibrate off, 1920 x 1080", res);
  assert.equal(res.flagged, 0, `Vibrate off: ${res.flagged} frames over the engine's own budget`);
  console.log("  " + rows.join("; "));
});

// Round-3 fix (must fix 1): every pattern under the Reverse-Bass dial, pressed once a beat (8 presses, velocity 0.85),
// at 128-174 BPM, Vibrate off and on, in white, Night Sea and Molten. Round 2: 45 runs over budget in the verifier's
// 5-theme grid, every one of them Reverse-Bass (crown 25, figure 14, tunnel 4, scissors 1, cross 1), worst 27.9 %.
test("Round 3: the Reverse-Bass dial pressed once a beat, every pattern, in white, Night Sea and Molten (fresh seeds) -- no frame over budget", () => {
  const r = L.makeRng(FRESH, "revbass-grid");
  const bad = [];
  let runs = 0;
  for (const id of ["white", "night-sea", "molten"]) for (const bpm of [128, 140, 150, 165, 174]) for (const pattern of L.PATTERN_IDS) for (const vibrate of [false, true]) {
    const per = 60000 / bpm, seed = 1 + Math.floor(r() * 1e6);
    const eng = L.createLaserEngine({ seed, clock: steadyClock(bpm), theme: id === "night-sea" ? THEMES["night-sea"] : themeOf(id), patternMode: pattern, gateMode: "revbass", vibrate });
    let over = 0;
    drive(eng, Array.from({ length: 8 }, (_, i) => tap(2000 + i * per, 0.85, 60)).flat(), { from: 1950, to: 2000 + 10 * per, onFrame: (out) => { if (out.area.over) over++; } });
    runs++;
    if (over) bad.push(`${id} ${bpm} ${pattern}${vibrate ? "/vib" : ""} seed ${seed}: ${over}`);
  }
  console.log(`  base ${FRESH}: ${runs} runs, ${bad.length} over budget`);
  assert.deepEqual(bad, [], `base ${FRESH}: ${bad.slice(0, 8).join(", ")}`);
});

// Round-3 fix (must fix 2, the rest of what overlapped): a new hit PLAYS ALONE. Round 2 let a hit start while the hits
// before it were still lit (a Reverse-Bass loop's second pulse under the hero's starburst; a press's own tail under the
// loop its hold started), each fitted alone: their changes added up in one frame (22-27 % against 22 %; 15-17 % against
// the hold's fast 15 %). Now whatever is left of the hits before goes dark once the new first pulse comes due, and the
// new hit lights the frame after; and a held loop is fitted where it really starts (round 2 fitted it where a plain
// press would start, then moved it).
test("Round 3: a new hit plays alone -- the hits before it are dark before its first pulse, a held press hands over to its loop", () => {
  const rows = [];
  // the dial on Reverse-Bass, three presses two beats apart: the third is the hero (a crown, starburst or bloom)
  for (const [bpm, pattern, sec] of [[140, "crown", "drop"], [174, "zigzag", "drop"], [140, "cross", "climax"], [174, "chase", "build"]]) {
    const per = 60000 / bpm;
    for (let s = 0; s < 6; s++) {
      const eng = L.createLaserEngine({ seed: 700 + 31 * s, clock: steadyClock(bpm), theme: themeOf("brass-break"), patternMode: pattern, gateMode: "revbass", vibrate: true, section: sec });
      const ev = [...tap(2000, 0.8), ...tap(2000 + 2 * per, 0.95), ...tap(2000 + 4 * per, 0.95)];
      let most = 0, over = 0;
      drive(eng, ev, { from: 1950, to: 2000 + 8 * per, onFrame: (out) => { most = Math.max(most, litHits(eng)); if (out.area.over) over++; } });
      assert.equal(most, 1, `${pattern}/revbass ${bpm} seed ${700 + 31 * s}: ${most} hits lit in one frame`);
      assert.equal(over, 0, `${pattern}/revbass ${bpm} seed ${700 + 31 * s}: ${over} frames over budget`);
    }
  }
  // a press held into its section's loop (the drop's push-pull or 16th roll; the build's doubling roll)
  for (const [sec, pattern, vel] of [["drop", "bloom", 0.95], ["drop", "fan", 0.6], ["build", "bloom", 0.9], ["climax", "crown", 0.95]]) {
    const bpm = 128, per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: 41, clock: steadyClock(bpm), theme: WHITE, patternMode: pattern, gateMode: "bar", section: sec, vibrate: true });
    let most = 0, over = 0, held = null;
    drive(eng, [...tap(2000, 0.7), ...tap(2000 + 2 * per, 0.8), ...tap(2000 + 4 * per, vel, 3 * per)], { from: 1950, to: 2000 + 9 * per, onFrame: (out) => {
      most = Math.max(most, litHits(eng)); if (out.area.over) over++;
      held = held || eng.hits.find((h) => h.tier === "held") || null;
    } });
    assert.ok(held, `${sec}: the hold spawned its loop`);
    assert.equal(most, 1, `${sec} ${pattern} held: ${most} hits lit in one frame`);
    assert.equal(over, 0, `${sec} ${pattern} held: ${over} frames over budget`);
    rows.push(`${sec} ${pattern} held: loop ${held.gate}`);
  }
  console.log("  " + rows.join("; "));
});

// Round-3 fix (found on the way): a loop released -- or taken over -- in the dark gap between two pulses lit its last
// picture again at full light as a "tail" (an extra flash off the grid: 8-11 % of a window from dark, in white). Now a
// loop that runs out while dark simply ends; only a halo held lit through the gap fades from where it is.
test("Round 3: a loop released in the dark gap between pulses does not light its last picture again", () => {
  for (const [gate, bpm] of [["revbass", 150], ["pushpull", 150], ["roll8", 100], ["inhale", 120]]) {
    const per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: 5, clock: steadyClock(bpm), theme: WHITE, patternMode: "fan", gateMode: gate, bankMode: "A", orderMode: "all" });
    let released = null, relit = 0, wasDark = false;
    drive(eng, [{ t: 2000, fn: (e, x) => e.hit(x, 0.9) }], { from: 1950, to: 2000 + 8 * per, onFrame: (out, t) => {
      const H = eng.hits[0];
      if (released === null && H && H.started && !H.on && t > 2000 + 2.2 * per) { eng.release(t); released = t; wasDark = out.area.litWindow === 0; return; }
      if (released !== null && t > released && out.area.litWindow > 0.002 && !(H && H.on)) relit++;
    } });
    assert.ok(released !== null, `${gate}: released in a gap`);
    if (wasDark) assert.equal(relit, 0, `${gate}: ${relit} frames lit again after a release in the dark`);
  }
});

// Round-3 fix (from the realistic runs): the settings a hit is fitted to stay its own. Vibrate switched on while a hit
// fitted still ran made it pluck at its next pulse (a 16th roll of figures rang at the full 18 px, 16.8 % against 15 %);
// a theme picked mid-hit recoloured its lit pulse at once. Now both reach the next hit.
test("Round 3: Vibrate switched on mid-hit reaches the next hit; a theme picked mid-hit never recolours a lit pulse", () => {
  const bpm = 150, per = 400;
  const eng = L.createLaserEngine({ seed: 9, clock: steadyClock(bpm), theme: THEMES["night-sea"], shapeMode: "auto", gateMode: "roll16", vibrate: false, section: "climax" });
  drive(eng, [...tap(2000, 0.9, 2 * per), { t: 2000 + per, fn: (e, x) => e.setVibrate(true, x) }], { from: 1950, to: 2000 + 2.5 * per });
  assert.ok(eng.vib.every((v) => v.rings.length === 0), "the roll fitted with Vibrate off never plucked");
  drive(eng, tap(2000 + 4 * per, 0.9), { from: 2000 + 3 * per, to: 2000 + 6 * per });
  assert.ok(eng.vib.some((v) => v.rings.length > 0), "the next press rings");
  const e2 = L.createLaserEngine({ seed: 9, clock: steadyClock(bpm), theme: THEMES["night-sea"], patternMode: "fan", gateMode: "single", colourMode: "mono" });
  let before = null, recoloured = 0;
  drive(e2, [...tap(2000, 0.8), { t: 2034, fn: (e) => e.setTheme(THEMES["golden-wings"]) }], { from: 1990, to: 2100, onFrame: (out) => {
    const H = e2.hits[0];
    if (!H || !H.on) return;
    let rgb = null;
    eachLine(out, (r) => { if (!rgb && r.I > 0.01) rgb = [r.r, r.g, r.b]; });
    if (!rgb) return;
    if (before && Math.hypot(rgb[0] - before[0], rgb[1] - before[1], rgb[2] - before[2]) > 0.02) recoloured++;
    before = rgb;
  } });
  assert.equal(recoloured, 0, "the lit pulse kept its colours through the theme switch");
});

// Round-3 fix (from the crash fuzz): a hit fitted in one window shape kept its fit when the window turned (a resize, a
// fullscreen toggle): a held crown roll fitted at 21:9 lit 15.2 % of a window at every pulse in portrait (round 2: 26
// frames over budget across the grid below, the switch frame itself left out). Now a new aspect refits the live hits.
// (The switch frame itself re-lays every line out, as the page does: it is not counted.)
test("Round 3: a held roll refits when the window changes shape -- no frame over budget after the switch", () => {
  const bad = [];
  for (const [a0, a1] of [[21 / 9, 9 / 16], [16 / 9, 9 / 16], [4 / 3, 21 / 9]]) for (const pattern of ["crown", "fan", "figure", "tunnel", "cross", "rain"]) for (const theme of [WHITE, THEMES["night-sea"]]) {
    const per = 400, eng = L.createLaserEngine({ seed: 7, clock: steadyClock(150), theme, patternMode: pattern, gateMode: "doubling", section: "build", aspect: a0 });
    const ev = tap(2000, 0.95, 8 * per).sort((a, b) => a.t - b.t);
    let ei = 0, over = 0, sw = null;
    for (let t = 1950; t < 2000 + 9 * per; t += F) {
      while (ei < ev.length && ev[ei].t <= t) { const e = ev[ei++]; e.fn(eng, e.t); }
      if (sw === null && t > 2000 + 2 * per) sw = t;
      const out = eng.frame(t, { aspect: sw === null ? a0 : a1 });
      if (out.area.over && sw !== null && t > sw + 1) over++;
    }
    if (over) bad.push(`${a0.toFixed(2)} > ${a1.toFixed(2)} ${pattern} ${theme.id}: ${over}`);
  }
  assert.deepEqual(bad, [], bad.join(", "));
});

// Round-3 fix (must fix 2): the verifier's A5-style grid with other seeds -- BPMs 120-190, velocities 0.7-1.0, taps up to
// 20 ms off, random bank, order, colour and section, every pattern and gate, Vibrate on 60 % -- across the 21 library
// themes and white, on FRESH seeds. Round 2: 110 frames over budget in 72 of 17,600 such runs (every theme affected).
// What they caught, each fixed at its root: loops stacked on one grid (above); a loop fitted on the heads of one group
// per position while the walk (rapid presses, skipped pulses) lights any group anywhere; a loop fitted on its first
// beat's grid and the first pulse of each later beat, while a moving picture (the wave's phase, the sweep) is elsewhere
// at every step, and a rapid roll runs on the 16th grid its presses switch it to; the cross and the wave, which draw
// every step's heads at once, had no lever left but light and were left over their aim; and a life simulated only
// where a short gate's pulse is scheduled, not where spec 3.3 moves it.
test("Round 3: A5-style runs on fresh seeds across the library and white -- no frame over budget", () => {
  const ids = [...Object.keys(LIBRARY), "white"], pick = (r, a) => a[Math.floor(r() * a.length)];
  const bad = [];
  let runs = 0;
  for (const id of ids) {
    const r = L.makeRng(FRESH, "a5-fresh", id);
    for (let i = 0; i < 90; i++) {
      const bpm = pick(r, [120, 128, 136, 140, 160, 165, 174, 190]), per = 60000 / bpm;
      const pattern = pick(r, L.PATTERN_IDS), gate = pick(r, L.GATE_IDS), vibrate = r() < 0.6;
      const bankMode = r() < 0.3 ? "auto" : pick(r, Object.keys(L.BANK_MODES)), orderMode = r() < 0.4 ? "auto" : r() < 0.5 ? "all" : pick(r, L.ORDER_IDS);
      const colourMode = r() < 0.5 ? "auto" : pick(r, L.COLOUR_IDS), section = pick(r, ["climax", "drop", "build", "anti", "groove", "break"]);
      const shapeMode = pattern === "figure" && r() < 0.5 ? (r() < 0.5 ? "auto" : pick(r, L.SHAPES)) : null;
      const seed = 1 + Math.floor(r() * 1e9), jit = 20 * r(), style = r();
      const eng = L.createLaserEngine({ seed, clock: steadyClock(bpm), theme: themeOf(id), patternMode: pattern, gateMode: gate, bankMode, orderMode, colourMode, vibrate, section, shapeMode });
      const v = () => 0.7 + 0.3 * r();
      const ev = style < 0.5 ? [...tap(2000 + gauss(r) * jit, v()), ...tap(2000 + 2 * per + gauss(r) * jit, v()), ...tap(2000 + 4 * per + gauss(r) * jit, v(), 3 * per)]
        : style < 0.75 ? Array.from({ length: 8 }, (_, k) => tap(2000 + k * per + gauss(r) * jit, v())).flat()
          : Array.from({ length: 12 }, (_, k) => tap(2000 + k * 0.5 * per + gauss(r) * jit, v(), 30)).flat();
      let over = 0;
      drive(eng, ev, { from: 1950, to: 2000 + 10 * per, onFrame: (out) => { if (out.area.over) over++; } });
      runs++;
      if (over) bad.push(`${id} #${i} ${bpm} ${pattern}/${gate}/${bankMode}/${orderMode}/${colourMode}/${section}${vibrate ? "/vib" : ""} seed ${seed}: ${over}`);
    }
  }
  console.log(`  base ${FRESH}: ${runs} runs, ${bad.length} with frames over budget`);
  assert.deepEqual(bad, [], `base ${FRESH}: ${bad.slice(0, 8).join(", ")}`);
});

// Round-3 fix (must fix 2): the verifier's realistic mashing (20 s a run: 8th and 16th mashing, quarter and dotted
// presses, holds, the phrase, bar presses; the dial, Vibrate, Shape and bank changed now and then) on FRESH seeds, at a
// steady 60 fps, with 4 % of frames dropped, and with figures. Round 2 on fresh seeds: 2 frames in 200 steady runs,
// 4 in 100 with drops, 3 in 100 with figures.
test("Round 3: realistic mashing on fresh seeds, steady, with dropped frames and with figures -- no frame over budget", () => {
  const themeIds = [...Object.keys(LIBRARY), "white"], pick = (r, a) => a[Math.floor(r() * a.length)];
  const bad = [];
  let runs = 0;
  for (const [mode, n] of [["steady", 24], ["drops", 12], ["figures", 12]]) for (let k = 0; k < n; k++) {
    const r = L.makeRng(FRESH, "mash-fresh", mode, k), figs = mode === "figures";
    const bpm = pick(r, [120, 128, 140, 150, 160, 174, 180]), per = 60000 / bpm, th = pick(r, themeIds);
    const eng = L.createLaserEngine({ seed: 1 + Math.floor(r() * 1e9), clock: steadyClock(bpm), theme: themeOf(th), section: pick(r, ["climax", "drop", "build", "groove", "anti", "break"]),
      vibrate: r() < 0.5, shapeMode: r() < 0.25 || figs ? "auto" : null, gateMode: r() < 0.6 ? "auto" : pick(r, L.GATE_IDS),
      bankMode: r() < 0.5 ? "auto" : pick(r, Object.keys(L.BANK_MODES)) });
    const ev = [], end = 2000 + 20000;
    for (let t = 2000; t < end;) {
      const style = r();
      if (style < 0.25) {
        const div = r() < 0.6 ? 0.5 : 0.25, m = 4 + Math.floor(r() * 12);
        for (let i = 0; i < m; i++) { const tt = t + i * div * per + gauss(r) * 12, v = 0.5 + 0.5 * r(); ev.push({ t: tt, fn: (e, x) => e.hit(x, v) }, { t: tt + 35, fn: (e, x) => e.release(x) }); }
        t += m * div * per;
      } else if (style < 0.5) {
        const div = pick(r, [1, 0.75, 2 / 3, 1.5]), m = 3 + Math.floor(r() * 6);
        for (let i = 0; i < m; i++) { const tt = t + i * div * per + gauss(r) * 15, v = r(); ev.push({ t: tt, fn: (e, x) => e.hit(x, v) }, { t: tt + 50, fn: (e, x) => e.release(x) }); }
        t += m * div * per;
      } else if (style < 0.65) {
        const hold = (1 + Math.floor(r() * 6)) * per, v = 0.4 + 0.6 * r();
        ev.push({ t, fn: (e, x) => e.hit(x, v) }, { t: t + hold, fn: (e, x) => e.release(x) });
        t += hold + per * r();
      } else if (style < 0.75) {
        const v = 0.7 + 0.3 * r();
        ev.push({ t, fn: (e, x) => e.phrase(x, v) });
        t += per * (1 + Math.floor(r() * 3));
      } else if (style < 0.85) {
        const m = 2 + Math.floor(r() * 4);
        for (let i = 0; i < m; i++) { const tt = t + i * 4 * per + gauss(r) * 20, v = 0.6 + 0.4 * r(); ev.push({ t: tt, fn: (e, x) => e.hit(x, v) }, { t: tt + 60, fn: (e, x) => e.release(x) }); }
        t += m * 4 * per;
      } else {
        const a = r();
        if (a < 0.3) { const g = r() < 0.4 ? "auto" : pick(r, L.GATE_IDS); ev.push({ t, fn: (e) => e.set({ gateMode: g }) }); }
        else if (a < 0.55) { const on = r() < 0.5; ev.push({ t, fn: (e, x) => e.setVibrate(on, x) }); }
        else if (a < 0.75) { const sm = figs ? "auto" : r() < 0.6 ? null : "auto"; ev.push({ t, fn: (e) => e.set({ shapeMode: sm }) }); }
        else { const b = r() < 0.4 ? "auto" : pick(r, Object.keys(L.BANK_MODES)); ev.push({ t, fn: (e) => e.set({ bankMode: b }) }); }
        t += per * r() * 2;
      }
    }
    const dr = L.makeRng(FRESH, "mash-drop", k);
    let over = 0;
    driveDt(eng, ev, { from: 1950, to: end + 3 * per, dtFn: () => (mode === "drops" && dr() < 0.04 ? 33.33 : F), onFrame: (out) => { if (out.area.over) over++; } });
    runs++;
    if (over) bad.push(`${mode} #${k} ${th} ${bpm}: ${over}`);
  }
  console.log(`  base ${FRESH}: ${runs} runs of 20 s, ${bad.length} with frames over budget`);
  assert.deepEqual(bad, [], `base ${FRESH}: ${bad.join(", ")}`);
});

// Round-3 fix (must fix 2): a rapid roll walked through every group by the presses, and the patterns that draw every
// step's heads at once. Round 2 fitted a loop on one group per position (a rapid sweep of single heads went dark at
// 15.1-15.8 % against 15 %, pressed again and again) and left a cross under the call bank with no lever but light (all
// its levers at their floors, onsets fitted at 15.8-30 % against 13.5 %, held back only by the frame check).
test("Round 3: a roll walked through every group, and a cross or wave drawing every step's heads, fit their budget (fresh seeds)", () => {
  const r = L.makeRng(FRESH, "groups");
  const bad = [];
  let runs = 0;
  for (const pattern of ["sweep", "bloom", "fan", "scissors", "hot", "zigzag", "tunnel", "rain"]) for (const id of ["white", "golden-wings", "void-ritual"]) for (let s = 0; s < 3; s++) {
    const bpm = [128, 160, 190][s], per = 60000 / bpm, seed = 1 + Math.floor(r() * 1e9);
    const eng = L.createLaserEngine({ seed, clock: steadyClock(bpm), theme: themeOf(id), patternMode: pattern, gateMode: "stopshort", orderMode: "rl", bankMode: "auto", vibrate: true, section: "build" });
    const ev = Array.from({ length: 14 }, (_, i) => tap(2000 + i * 0.5 * per + gauss(r) * 10, 0.75 + 0.25 * r(), 30)).flat();
    let over = 0;
    drive(eng, ev, { from: 1950, to: 2000 + 10 * per, onFrame: (out) => { if (out.area.over) over++; } });
    runs++;
    if (over) bad.push(`walked ${pattern} ${id} ${bpm} seed ${seed}: ${over}`);
  }
  for (const pattern of ["cross", "wave"]) for (const gate of ["stopshort", "onetwo", "pushpull", "tttou", "military"]) for (const bankMode of ["call", "both"]) for (const id of ["laser-green", "white"]) {
    const bpm = 165, per = 60000 / bpm, seed = 1 + Math.floor(r() * 1e9);
    const eng = L.createLaserEngine({ seed, clock: steadyClock(bpm), theme: id === "laser-green" ? THEMES["laser-green"] : WHITE, patternMode: pattern, gateMode: gate, bankMode, vibrate: true, section: "climax" });
    let over = 0;
    drive(eng, [...tap(2000, 0.95), ...tap(2000 + 2 * per, 0.95), ...tap(2000 + 4 * per, 0.95)], { from: 1950, to: 2000 + 8 * per, onFrame: (out) => { if (out.area.over) over++; } });
    runs++;
    if (over) bad.push(`${pattern}/${gate}/${bankMode} ${id} seed ${seed}: ${over}`);
  }
  console.log(`  base ${FRESH}: ${runs} runs, ${bad.length} over budget`);
  assert.deepEqual(bad, [], `base ${FRESH}: ${bad.slice(0, 8).join(", ")}`);
});

// Round-3 fix (must fix 2, the per-frame check): a ringing figure whose pieces at the string's nodes stand still could
// not give way: round 2 dimmed a hit only when every one of its lines moved, so a figure ringing past its fit went out
// over budget in the middle of a lit pulse (with the fit switched off: 44 such frames over the grid below, every 4-ring
// tunnel). Now such a hit dims (the frame keeps the best state it tried). (A pulse going DARK is the fit's to keep:
// light that goes dark cannot be taken back in that frame.)
test("Round 3: with the fit off, a ringing figure whose node pieces stand still gives way in the middle of its pulse", () => {
  let mid = 0, frames = 0;
  for (const shape of ["tunnel", "circle", "spiral", "cube"]) for (const gate of ["roll8", "roll16", "pushpull"]) for (const bpm of [100, 128, 150]) {
    const per = 60000 / bpm;
    const eng = L.createLaserEngine({ seed: 17, clock: steadyClock(bpm), theme: WHITE, shapeMode: shape, gateMode: gate, vibrate: true, section: "climax" });
    eng._fitHit = () => {};
    let wasOn = false;
    drive(eng, tap(2000, 1, 4 * per), { from: 1950, to: 2000 + 6 * per, onFrame: (out) => {
      const H = eng.hits.find((h) => h.started && !h.done), on = !!(H && H.on);
      if (on && wasOn && !out.events.some((e) => e.type === "pulse")) { frames++; if (out.area.over) mid++; }
      wasOn = on;
    } });
  }
  console.log(`  ${frames} mid-pulse frames, ${mid} over budget`);
  assert.ok(frames > 500);
  assert.equal(mid, 0, `${mid} mid-pulse frames over budget with the fit off`);
});

// ------------------------------------------------------------------------------------------- 11. round 4 --
// The verifier's round-3 must-fix: the "plays alone" hand-over put the hits before a new hit out only in the frame the
// new first pulse was due, so that frame went out dark and the pulse lit a frame or more late -- whenever any light of
// the hit before was still alive, even a 1-3 % tail that lights nothing a window would count. A held press's loop was
// late in 40 of 40 holds at 150 BPM (worst 50-62 ms; round 2: 3 of 40, where the hold was known after the loop's first
// grid point); Bar Marker taps 1.25 beats apart lit 360 of 400 first pulses a frame late (round 2: none). Now the hits
// before go out in the frame BEFORE the new first pulse; when no frame is left between (a press within a frame of its
// beat) they go out with it if what is left of them changes nothing measurable, or fits the budget with the new onset,
// or is a tail dim enough to go out in two unmeasured halves; a pulse lit when the press comes ends the frame rules' gap
// before the new one; and a held loop starts on a grid point it can still light on time. Each test fails on the round-3
// engine (df24413e) and passes now. "On time" is spec 3.3's early rule, as A2 measures it: a pulse's picture (one frame
// after its frame's rAF time) lands at or before its grid point, at most one frame early.
const photonErr = (t, P, per) => t + F - P * per;
// The hits that light anything measurable (0.1 or more, by the module's own estimator) in the frame just drawn: each
// hit's records (a record's key carries its hit id, key = hit * 8192 + ..., see _write). A tail going out in two halves
// under a new onset is still drawn for that one frame, at a level that lights nothing measurable: litHits counts it,
// this does not.
function measurablyLit(eng) {
  const d = eng.drawn, by = new Map();
  for (let i = 0; i < d.n; i++) { const id = Math.floor(d.keys[i] / 8192); if (!by.has(id)) by.set(id, []); by.get(id).push(i); }
  let n = 0;
  for (const rows of by.values()) {
    const Wa = new Float64Array(rows.length * L.W_FLOATS);
    rows.forEach((i, k) => Wa.set(d.W.subarray(i * L.W_FLOATS, (i + 1) * L.W_FLOATS), k * L.W_FLOATS));
    const a = L.estimateArea(Wa, rows.length, eng.asp || 16 / 9);
    if (a.window > 1e-9 || a.frame > 1e-9) n++;
  }
  return n;
}

test("Round 4: a held press's loop lights its first pulse on its grid point -- never late, at most a frame early -- with the press dark the frame before", () => {
  const rows = [], bad = [];
  // the verifier's repro (one press held 4 beats, 40 seeds, presses on every eighth of the beat), and more tempos and
  // sections; each run twice, with the frames on the beat grid and 7.3 ms off it
  const cases = [[150, "drop", "auto", 0.8, false, "night-sea"], [150, "anti", "auto", 0.8, false, "night-sea"], [174, "drop", "auto", 1.0, false, "night-sea"],
    [140, "drop", "single", 0.6, true, "molten"], [150, "build", "auto", 0.8, false, "night-sea"], [128, "climax", "auto", 0.95, true, "white"],
    [165, "break", "auto", 0.7, false, "golden-wings"], [160, "groove", "auto", 0.85, true, "laser-green"]];
  for (const [bpm, section, gateMode, vel, vibrate, th] of cases) {
    const per = 60000 / bpm, theme = THEMES[th] || themeOf(th);
    let n = 0, worst = -Infinity, best = Infinity;
    for (let seed = 1; seed <= 40; seed++) for (const off of [0, 7.3]) {
      const eng = L.createLaserEngine({ seed, clock: steadyClock(bpm), theme, section, gateMode, vibrate });
      const tp = 2000 + (seed % 8) * per / 8, tag = `${bpm} ${section} seed ${seed} off ${off}`;
      let pressLit = false, seen = false;
      drive(eng, tap(tp, vel, 4 * per), { from: 1950 + off, to: tp + 6 * per, onFrame: (out, t) => {
        const ev = out.events.find((e) => e.type === "pulse" && e.k === 0 && (eng.hits.find((h) => h.id === e.hit) || {}).tier === "held");
        if (ev && !seen) {
          seen = true; n++;
          const H = eng.hits.find((h) => h.id === ev.hit), G = L.GATES[H.gate], step = G.stages ? G.stages[0] : G.step, q = (H.cur.P - (G.offset || 0)) / step;
          const err = photonErr(t, H.cur.P, per);
          worst = Math.max(worst, err); best = Math.min(best, err);
          if (err > 1e-6 || err <= -F - 1e-6) bad.push(`${tag}: first pulse ${err.toFixed(1)} ms from its grid point`);
          if (Math.abs(q - Math.round(q)) > 1e-6) bad.push(`${tag}: first pulse off the ${H.gate} grid (P ${H.cur.P})`);
          if (pressLit) bad.push(`${tag}: the press still lit the frame before its loop's first pulse`);
          if (litHits(eng) !== 1) bad.push(`${tag}: ${litHits(eng)} hits lit with the loop's first pulse`);
        }
        const press = eng.hits.find((h) => h.id === 1);
        pressLit = !!(press && press.started && press.level01 > 0.002);
      } });
    }
    rows.push(`${bpm} ${section}${vibrate ? "/vib" : ""} ${th}: ${n} holds, first pulse ${best.toFixed(1)} to ${worst.toFixed(1)} ms`);
    assert.equal(n, 80, `${bpm} ${section}: ${n} of 80 holds lit their loop`);
  }
  console.log("  " + rows.join("; "));
  assert.deepEqual(bad, [], bad.slice(0, 8).join("; "));
});

// The first frame at or after the press whose picture has reached beat P (spec 3.3's early rule, presentLag one frame).
function couldLightIn(frames, t0, P, per) {
  for (const t of frames) if (t >= t0 - 1e-9 && t + 2 * F - 1e-6 >= P * per) return t;
  return Infinity;
}
// presses `gap` beats apart with the dial on `gate` (the verifier's x13 / x7 layout): how many first pulses light a frame
// (or more) later than the frame they could light in
function tapDelays(gate, gap, bpm, off, theme = WHITE) {
  const per = 60000 / bpm, hist = {};
  let late = 0, n = 0;
  for (let seed = 1; seed <= 40; seed++) {
    const eng = L.createLaserEngine({ seed, clock: steadyClock(bpm), theme, gateMode: gate, vibrate: false });
    const presses = Array.from({ length: 10 }, (_, i) => 2000 + (seed % 5) * 37 + i * gap * per);
    const from = 1950 + off, to = presses[9] + 3 * per, frames = [];
    for (let j = 0; from + j * F < to; j++) frames.push(from + j * F);
    drive(eng, presses.flatMap((p) => tap(p, 0.8)), { from, to, onFrame: (out, t) => {
      for (const e of out.events) if (e.type === "pulse" && e.k === 0) {
        const H = eng.hits.find((h) => h.id === e.hit);
        const d = Math.round((t - couldLightIn(frames, H.t0, H.cur.P, per)) / F);
        n++; hist[d] = (hist[d] || 0) + 1; if (d > 0) late++;
      }
    } });
  }
  return { late, n, hist };
}

test("Round 4: taps after a long tail light their first pulse in the frame they could light in (Bar Marker 1.25 beats apart, Inhale and Single a beat apart)", () => {
  const rows = [];
  // the verifier's repro (Bar Marker at 140 BPM, white, the frames where its probe ran them; round 3: 360 of 400 a frame
  // late, round 2: none), and two more with the frames off the beat grid: the Inhale's ramp, lit right up to the beat
  // the next press takes over (round 3: 360 of 400, mostly 2 frames late: the lit ramp ran on into the new pulse's
  // frame), and a Single a beat apart (round 3: 51 of 400)
  for (const [gate, gap, bpm, off] of [["bar", 1.25, 140, 0], ["inhale", 1, 128, 7.1], ["single", 1, 174, 7.1]]) {
    const r = tapDelays(gate, gap, bpm, off);
    rows.push(`${gate} ${gap} beats apart at ${bpm}: ${r.late} of ${r.n} late ${JSON.stringify(r.hist)}`);
    assert.equal(r.n, 400, `${gate}: ${r.n} first pulses`);
    assert.equal(r.late, 0, `${gate} ${gap} beats apart at ${bpm} BPM: ${r.late} of ${r.n} first pulses lit later than they could ${JSON.stringify(r.hist)}`);
  }
  console.log("  " + rows.join("; "));
});

// When the press leaves no frame between (it came within a frame of its beat, or fires now), the hits before go out in
// the frame the new pulse comes on in -- and only as the budget allows: what is left of them changes nothing measurable
// as it goes, or that change plus the new onset fits the budget, or (a tail too bright for that, dim enough for this) it
// goes out in two halves that each change nothing measurable: in its half frame it is drawn as last frame's very records
// at half their level (nothing of it moves), then not at all. The verifier's Bar Marker repro needs the halves three
// times (seeds 6, 21, 22) and a Triple Strobe 1.5 beats apart at 128 six times; each is checked here on the records.
function subsetOf(buf, ids) {
  const out = L.recordBuffer();
  for (let i = 0; i < buf.n; i++) {
    if (!ids.has(Math.floor(buf.keys[i] / 8192))) continue;
    out.W.set(buf.W.subarray(i * L.W_FLOATS, (i + 1) * L.W_FLOATS), out.n * L.W_FLOATS);
    out.keys[out.n] = buf.keys[i]; out.map.set(buf.keys[i], out.n); out.n++;
  }
  return out;
}
test("Round 4: a hand-over with no frame to spare changes nothing measurable or fits the budget; a dim tail goes out in two unmeasured halves", () => {
  const n = { cutDark: 0, cutFits: 0, halve: 0, wait: 0 }, bad = [];
  for (const [gate, gap, bpm] of [["bar", 1.25, 140], ["triple", 1.5, 128]]) {
    const per = 60000 / bpm;
    for (let seed = 1; seed <= 40; seed++) {
      const eng = L.createLaserEngine({ seed, clock: steadyClock(bpm), theme: WHITE, gateMode: gate, vibrate: false });
      const orig = eng._cutsClean.bind(eng), made = [];
      eng._cutsClean = (H, wait) => {
        const D = eng._drawnLight(wait), how = orig(H, wait);
        const kind = !how ? "wait" : how === "halve" ? "halve" : !D || (D.area.window <= 1e-9 && D.area.frame <= 1e-9) ? "cutDark" : "cutFits";
        n[kind]++;
        if (how) made.push({ kind, ids: new Set(wait.map((h) => h.id)), H });
        return how;
      };
      const presses = Array.from({ length: 10 }, (_, i) => 2000 + (seed % 5) * 37 + i * gap * per);
      let prev = null, watch = [];
      drive(eng, presses.flatMap((p) => tap(p, 0.8)), { from: 1950, to: presses[9] + 3 * per, onFrame: (out, t) => {
        const chg = { frame: 0, window: 0 };
        // the frame after a half: what is left goes out, unmeasured
        for (const w of watch) {
          L.estimateChange(subsetOf(prev, w.ids), subsetOf(eng.drawn, w.ids), eng.asp, chg);
          if (chg.window > 1e-9 || chg.frame > 1e-9) bad.push(`${gate} seed ${seed} at ${t.toFixed(0)}: a halved tail went out changing ${(100 * chg.window).toFixed(2)} % of a window`);
        }
        watch = [];
        for (const m of made) {
          const own = L.estimateChange(prev && subsetOf(prev, m.ids), subsetOf(eng.drawn, m.ids), eng.asp, { frame: 0, window: 0 });
          if (m.kind !== "cutFits" && (own.window > 1e-9 || own.frame > 1e-9)) bad.push(`${gate} seed ${seed} at ${t.toFixed(0)}: ${m.kind} changed ${(100 * own.window).toFixed(2)} % of a window`);
          if (out.area.over) bad.push(`${gate} seed ${seed} at ${t.toFixed(0)}: ${m.kind} frame over budget`);
          if (!m.H.started || m.H.cur.onFrame !== eng.frameIdx) bad.push(`${gate} seed ${seed}: the new hit did not light in its hand-over frame`);
          if (m.kind === "halve") watch.push(m);
        }
        made.length = 0;
        prev = L.recordBuffer();
        prev.W.set(eng.drawn.W.subarray(0, eng.drawn.n * L.W_FLOATS)); prev.keys.set(eng.drawn.keys.subarray(0, eng.drawn.n));
        prev.n = eng.drawn.n; for (let i = 0; i < prev.n; i++) prev.map.set(prev.keys[i], i);
      } });
    }
  }
  console.log(`  hand-overs with no frame to spare: ${JSON.stringify(n)}`);
  assert.ok(n.halve >= 9 && n.cutFits > 0 && n.cutDark > 0, JSON.stringify(n));
  assert.deepEqual(bad, [], bad.slice(0, 8).join("; "));
});

// Realistic play on FRESH seeds (taps at many spacings, holds, sparse presses; the dial, Vibrate, Shape and banks
// drawn per run; the frames at a random offset from the beat grid): every held loop's first pulse on its grid point
// (the verifier's mashing run: 28 of 35 in round 2, 3 of 35 in round 3), still one hit lit at a time, no frame over
// budget.
test("Round 4: realistic play on fresh seeds -- every held loop's first pulse on its grid point, one hit lit at a time, no frame over budget", () => {
  const themeIds = [...Object.keys(LIBRARY), "white"], pick = (r, a) => a[Math.floor(r() * a.length)];
  const bad = [];
  let held = 0, runs = 0, slow = 0, slowLate = 0;
  for (let k = 0; k < 16; k++) {
    const r = L.makeRng(FRESH, "play-timing", k);
    const bpm = pick(r, [120, 128, 140, 150, 160, 174, 180]), per = 60000 / bpm, off = 13 * r();
    const eng = L.createLaserEngine({ seed: 1 + Math.floor(r() * 1e9), clock: steadyClock(bpm), theme: themeOf(pick(r, themeIds)), section: pick(r, ["climax", "drop", "build", "groove", "anti", "break"]),
      vibrate: r() < 0.5, shapeMode: r() < 0.25 ? "auto" : null, gateMode: r() < 0.6 ? "auto" : pick(r, L.GATE_IDS), bankMode: r() < 0.5 ? "auto" : pick(r, Object.keys(L.BANK_MODES)) });
    const ev = [], end = 2000 + 20000;
    for (let t = 2000; t < end;) {
      const style = r();
      if (style < 0.3) {
        const div = pick(r, [0.5, 1, 0.75, 1.25, 1.5]), m = 3 + Math.floor(r() * 8);
        for (let i = 0; i < m; i++) ev.push(...tap(t + i * div * per + gauss(r) * 12, 0.4 + 0.6 * r(), 40));
        t += m * div * per;
      } else if (style < 0.7) {
        const hold = (1 + Math.floor(r() * 4)) * per;
        ev.push(...tap(t + gauss(r) * 10, 0.4 + 0.6 * r(), hold));
        t += hold + per * (0.5 + r());
      } else {
        const m = 2 + Math.floor(r() * 3);
        for (let i = 0; i < m; i++) ev.push(...tap(t + i * pick(r, [2, 3, 4]) * per + gauss(r) * 20, 0.6 + 0.4 * r(), 60));
        t += m * 4 * per;
      }
    }
    let most = 0, over = 0;
    drive(eng, ev, { from: 1950 + off, to: end + 3 * per, onFrame: (out, t) => {
      most = Math.max(most, measurablyLit(eng)); if (out.area.over) over++;
      for (const e of out.events) if (e.type === "pulse" && e.k === 0) {
        const H = eng.hits.find((h) => h.id === e.hit);
        if (H.tier === "held") {
          held++;
          const err = photonErr(t, H.cur.P, per);
          if (err > 1e-6 || err <= -F - 1e-6) bad.push(`#${k} ${bpm} held ${H.gate} at ${t.toFixed(0)}: ${err.toFixed(1)} ms`);
        } else if (!H.fast) { slow++; if (t - Math.max(H.t0, H.cur.P * per - 2 * F) >= F - 1e-6) slowLate++; }
      }
    } });
    runs++;
    if (most > 1) bad.push(`#${k}: ${most} hits measurably lit in one frame`);
    if (over) bad.push(`#${k}: ${over} frames over budget`);
  }
  console.log(`  base ${FRESH}: ${runs} runs of 20 s, ${held} held loops (all on their grid point), ${slow} slow first pulses, ${slowLate} of them a frame or more after they could`);
  assert.ok(held >= 20, `only ${held} held loops`);
  assert.deepEqual(bad, [], `base ${FRESH}: ${bad.slice(0, 8).join("; ")}`);
});
