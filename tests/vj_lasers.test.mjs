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
// are the verifier's must-fix repros: each failed against the round-0 engine and passes now.
// Every number here is synthetic: nothing reads Daniel's playing. (The raster tests take about two minutes.)
import { test } from "node:test";
import assert from "node:assert/strict";
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
  let worstChange = 0, worstLit = 0, worstFrame = 0, worstAt = 0, onsets = 0, est = 0;
  drive(eng, events, { from, to, onFrame: (out, t) => {
    for (const e of out.events) if (e.type === "pulse") onsets++;
    est = Math.max(est, out.area.window);
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
  return { worstChange, worstLit, worstFrame, over: over.length, maxPerSecond, worstAt, onsets, est };
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
