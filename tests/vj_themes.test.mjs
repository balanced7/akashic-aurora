// Tests for arsenal/web/vj-themes.js and arsenal/web/vj-themes.json (spec slice S5, receipt A4 and the module half of A8):
// the library is the spec's and validates, every pad stand-in passes the KeyLab LED rule, no saturated red reaches a
// strobing role in any variant, the fader walk covers every theme, changes land on the bar, the key picks a family, the
// section rotates within it, and what a theme gives the scene, the lasers, the effects and the pads.
//   node --test tests/vj_themes.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { BeatClock, CONTROLS, DEFAULT_PAD_MAP } from "../arsenal/web/vj-core.js";
import * as T from "../arsenal/web/vj-themes.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const RAW = JSON.parse(readFileSync(here("../arsenal/web/vj-themes.json"), "utf8"));
const lib = T.loadLibrary(RAW);
const clone = () => JSON.parse(JSON.stringify(RAW));
const theme = (id) => lib.byId.get(id);
const SPEC = here("../research/reviewed/keylab-liberation-2026-10-22/vj-lasers-v2-and-colour-themes-2026-10-24.md");

// a steady grid: beats every beatMs from 0, bars of 4 beats, phrases of 8 bars (a ThemeClock, as the page will hand in)
function grid(beatMs = 500) {
  const next = (now, every) => Math.ceil(now / every) * every;
  return {
    alive: () => true,
    beatMs: () => beatMs,
    nextBeatAt: (now) => next(now, beatMs),
    nextBarAt: (now) => next(now, 4 * beatMs),
    nextPhraseAt: (now) => next(now, 32 * beatMs),
  };
}
// tick a director every stepMs from t0 to t1; the changes that landed
function run(d, t0, t1, clock, stepMs = 50) {
  const out = [];
  for (let t = t0; t <= t1; t += stepMs) { const c = d.tick(t, clock); if (c) out.push(c); }
  return out;
}
// every colour a look can flash or strobe
const strobing = (L) => [L.lasers.L1, L.lasers.L2, ...L.lasers.triple, ...L.lasers.flicker, ...L.lasers.burst,
                         L.fx.flash, L.fx.shockwave, L.scene.kickGlow];

// ------------------------------------------------------------------------------------------------ the library --
test("the library file is the spec's validated v2 library, word for word (only a source line added)", () => {
  const md = readFileSync(SPEC, "utf8");
  const i = md.indexOf("## The theme library (v2, validated: 0 errors)");
  assert.ok(i > 0, "the spec's library section");
  const j = md.indexOf("```json", i) + "```json".length;
  const spec = JSON.parse(md.slice(j, md.indexOf("```", j)));
  const ours = clone();
  assert.match(ours.source, /vj-lasers-v2-and-colour-themes-2026-10-24\.md/);
  delete ours.source;
  assert.deepEqual(ours, spec);
});

test("the library validates with no errors and no warnings: 21 themes in 8 families, as the spec's table", () => {
  const v = T.validateLibrary(RAW);
  assert.deepEqual(v.errors, []);
  assert.deepEqual(v.warnings, []);
  assert.equal(lib.themes.length, 21);
  assert.deepEqual(lib.familyThemes, {
    ritual: ["void-ritual", "red-tribe", "red-blades"],
    fire: ["molten", "golden-wings", "fire-and-ice"],
    celestial: ["celestial-violet", "violet-rose", "uv-euphoria"],
    night: ["night-sea", "temple-light", "blue-raw", "limbo"],
    green: ["laser-green", "acid-screech"],
    pyro: ["pink-pyro", "magenta-classics"],
    worship: ["cathedral-jewel", "brass-break", "sanctuary-gold"],
    line: ["bone-line"],
  });
  assert.equal(Object.keys(lib.families).length, 8);
  assert.ok(Object.isFrozen(lib.themes) && Object.isFrozen(theme("molten").led), "a loaded library cannot be edited");
});

test("the validator catches each fault the spec's four corrections fixed, and broken references", () => {
  const fault = (edit, pattern) => {
    const raw = clone();
    edit(raw);
    const v = T.validateLibrary(raw);
    assert.equal(v.ok, false, `expected a problem matching ${pattern}`);
    assert.ok(v.errors.some((e) => pattern.test(e)), `${pattern} not in ${JSON.stringify(v.errors)}`);
    assert.throws(() => T.loadLibrary(raw), /problem/);
  };
  const at = (raw, id) => raw.themes.find((t) => t.id === id);
  // 1. a grey stand-in (the colour lane's #c2c2c2) instead of #ffffff plus a level
  fault((r) => { at(r, "void-ritual").led.B = "#c2c2c2"; }, /led\.B #c2c2c2.*white/);
  // 2. a held (saturated red) colour in a burst (Molten's original list)
  fault((r) => { at(r, "molten").burst = ["A", "B", "W"]; }, /held role A appears/);
  // 3. Pink Pyro's original laser colour, saturated red on linear values
  fault((r) => { at(r, "pink-pyro").beam.A = "#db1b64"; }, /beam\.A #db1b64 is saturated red/);
  // 4. a saturated red that is not held
  fault((r) => { at(r, "red-tribe").held = []; }, /A #db0001 is saturated red but not held/);
  // references and shape
  fault((r) => { r.fader_order = r.fader_order.filter((id) => id !== "limbo"); }, /limbo appears 0 times/);
  fault((r) => { r.fader_order.push("custom"); }, /Custom must appear exactly once/);
  fault((r) => { r.families.night.climax = "night-ocean"; }, /families\.night\.climax: unknown theme night-ocean/);
  fault((r) => { delete r.camelot["5"]; }, /camelot\.5: missing/);
  fault((r) => { at(r, "night-sea").fx.flash = "A"; }, /fx\.flash must be W or white/);
  fault((r) => { at(r, "night-sea").strobe.triple = ["A", "B"]; }, /strobe\.triple must be 3 roles/);
  fault((r) => { at(r, "night-sea").led_level = { A: 0.5 }; }, /led_level\.A dims a stand-in that is not white/);
  fault((r) => { at(r, "uv-euphoria").led.A = "#ffb000"; }, /led\.A #ffb000: hue 41 washes to white/);
  fault((r) => { r.themes.push({ ...at(r, "limbo") }); }, /duplicate id/);
});

test("fetchLibrary loads through an injected fetch and rejects an unsound library", async () => {
  const text = readFileSync(here("../arsenal/web/vj-themes.json"), "utf8");
  const ok = await T.fetchLibrary("vj-themes.json", async () => ({ ok: true, status: 200, text: async () => text }));
  assert.equal(ok.themes.length, 21);
  const broken = clone();
  broken.themes[0].led.A = "#888888";
  await assert.rejects(T.fetchLibrary("x", async () => ({ ok: true, status: 200, text: async () => JSON.stringify(broken) })), /problem/);
  await assert.rejects(T.fetchLibrary("x", async () => ({ ok: false, status: 404, text: async () => "" })), /404/);
});

// --------------------------------------------------------------------------------------------- the pad rule --
test("the HLS port agrees with Python's colorsys (the rule's own test uses it)", () => {
  // reference values printed by colorsys.rgb_to_hls
  const ref = { "#8080ff": [240, 0.751, 1], "#ff9a1f": [32.9464, 0.5608, 1], "#ff3c00": [14.1176, 0.5, 1],
                "#c2c2c2": [0, 0.7608, 0], "#e8e8ff": [240, 0.9549, 1], "#00e5ff": [186.1176, 0.5, 1],
                "#ff2a00": [9.8824, 0.5, 1], "#4b3cff": [244.6154, 0.6176, 1], "#a8ff24": [83.8356, 0.5706, 1] };
  for (const [hex, [h, l, s]] of Object.entries(ref)) {
    const got = T.hls(T.hexToRgb(hex));
    assert.ok(Math.abs(got.h - h) < 1e-3 && Math.abs(got.l - l) < 1e-3 && Math.abs(got.s - s) < 1e-3, `${hex} ${JSON.stringify(got)}`);
  }
});

test("the pad rule: pure white passes, greys and orange-to-lime hues wash out, as tests/test_keylab_w0.py says", () => {
  assert.equal(T.ledRule("#ffffff").ok, true);
  for (const hex of ["#c2c2c2", "#f6f6f6", "#ff9a1f", "#a8ff24", "#ffb000"]) assert.equal(T.ledRule(hex).ok, false, hex);
  for (const hex of ["#ff0001", "#ff2a00", "#ff3c00", "#00ff9c", "#3000ff", "#8080ff"]) assert.equal(T.ledRule(hex).ok, true, hex);
  // every stand-in of every theme
  for (const t of lib.themes) for (const r of T.ROLES) assert.ok(T.ledRule(t.led[r]).ok, `${t.id} led.${r} ${t.led[r]}`);
});

test("pad lights for every theme, laser tier and brightness pass the rule: stand-ins only, Choke moved out of the wash zone", () => {
  assert.equal(T.ledRule(CONTROLS.choke.colour).ok, false, "today's Choke colour washes out (why it moves)");
  let posted = 0;
  for (const t of lib.themes) {
    const look = T.themeLook(lib, t.id);
    const standIns = new Set(Object.values(t.led));
    for (const tier of [0, 1, 2, 3]) {
      const lights = T.padLeds(look, DEFAULT_PAD_MAP, { tier });
      assert.equal(lights.length, 12);
      lights.forEach((light, i) => {
        if (light.kind === "effect" || light.kind === "laser") assert.ok(standIns.has(light.hex), `${t.id} pad ${i + 1}: ${light.hex} is a screen colour`);
        assert.ok(T.ledRule(light.hex).ok || light.kind === "none", `${t.id} pad ${i + 1} ${light.hex}`);
        for (const b of [0.1, 0.35, 0.6, 1]) {
          const hex = T.ledHexAt(light, b);
          assert.ok(T.ledPostedOk(hex), `${t.id} pad ${i + 1} at ${b}: ${hex}`);
          posted++;
        }
      });
      assert.equal(lights[1].kind, "laser");
      assert.equal(lights[1].level, look.pads.laser.level * T.LASER_TIER_LEVEL[tier]);
      assert.equal(lights[9].hex, T.CHOKE_LED);
    }
  }
  assert.ok(posted >= 21 * 4 * 12 * 4);
  // a white stand-in at its level is the colour lane's grey, as a level rather than a washing colour
  assert.equal(T.ledHexAt({ hex: "#ffffff", level: 0.76 }), "#c2c2c2");
  assert.equal(T.themeLook(lib, "pink-pyro").pads.laser.hex, "#ff004e", "pad 2 takes the laser role's stand-in");
  assert.deepEqual([1, 2, 3].map((tier) => T.padLeds(T.themeLook(lib, "pink-pyro"), DEFAULT_PAD_MAP, { tier })[1].level), [0.6, 0.8, 1]);
});

test("each family tab lights in a stand-in of its own family, eight different colours", () => {
  const seen = new Set();
  for (const fam of Object.keys(lib.families)) {
    const led = T.familyLed(lib, fam);
    assert.ok(T.ledRule(led.hex).ok, `${fam} ${led.hex}`);
    const own = lib.familyThemes[fam].flatMap((id) => Object.values(theme(id).led));
    assert.ok(own.includes(led.hex), `${fam}: ${led.hex} is not one of its themes' stand-ins`);
    seen.add(led.hex);
  }
  assert.equal(seen.size, 8);
});

// ----------------------------------------------------------------------------------------------- the red rule --
test("six distinct saturated reds among the screen colours, every one held, none in a laser list", () => {
  const reds = new Set();
  for (const t of lib.themes) {
    for (const r of T.ROLES) if (T.isSaturatedRed(t[r])) { reds.add(t[r]); assert.ok(t.held.includes(r), `${t.id} ${r}`); }
    for (const r of [...t.lasers, ...t.strobe.triple, ...t.strobe.flicker, ...t.burst]) assert.ok(!t.held.includes(r), `${t.id} emits held ${r}`);
  }
  assert.deepEqual([...reds].sort(), ["#85063f", "#ab0a1c", "#d63b09", "#db0001", "#ea7720", "#ff1a3c"]);
  // the encoded test alone catches two; the linear test catches the other four (why both are applied)
  const encodedOnly = [...reds].filter((h) => T.redRatios(h).encoded >= 0.8).sort();
  assert.deepEqual(encodedOnly, ["#ab0a1c", "#db0001"]);
});

test("no saturated red in any strobing role, in any variant: key nudges, hue drift, the drop swap and every Custom turn", () => {
  const variants = [{}, { mode: "major" }, { mode: "minor" }, { hueDeg: 15 }, { hueDeg: -15 }, { hueDeg: 7, mode: "major" },
                    { swap: true }, { swap: true, mode: "major", hueDeg: 15 }];
  for (let deg = 0; deg < 360; deg += 15) {
    variants.push({ custom: true, hueDeg: deg }, { custom: true, hueDeg: deg, mode: "major" }, { custom: true, hueDeg: deg, swap: true });
  }
  let checked = 0, pulled = 0;
  for (const t of lib.themes) {
    for (const opts of variants) {
      const L = T.themeLook(lib, t.id, opts);
      for (const c of strobing(L)) {
        const r = T.redRatios(c.hex);
        assert.ok(r.encoded < 0.8 && r.linear < 0.8, `${t.id} ${JSON.stringify(opts)} ${c.role} ${c.hex} ${JSON.stringify(r)}`);
        assert.equal(T.linearToHex(c.lin), c.hex, "hex and linear agree");
        checked++;
      }
    }
    // the base look emits the library's own colours untouched (no safety pull needed)
    const base = T.themeLook(lib, t.id);
    for (const c of [base.lasers.L1, ...base.lasers.triple, ...base.lasers.burst]) {
      const want = (t.beam && t.beam[c.role]) || t[c.role];
      if (c.hex !== want) pulled++;
    }
  }
  assert.equal(pulled, 0);
  assert.ok(checked > 21 * variants.length * 10);
  // the margin case: Laser Green's magenta pin strobes at 0.777 and a major key nudges it toward red; it is pulled back
  const pin = T.themeLook(lib, "laser-green", { mode: "major" }).lasers.triple[2];
  assert.ok(T.redRatios(pin.hex).linear < 0.8);
});

test("the held colours stay on the scene; an ember effect may use one and says so", () => {
  const molten = T.themeLook(lib, "molten");
  assert.equal(molten.scene.stops[0].hex, "#d63b09", "the ember is the scene's primary");
  assert.equal(molten.fx.particles.held, true, "Molten's embers use the held ember: steady, never flashed");
  assert.equal(T.themeLook(lib, "night-sea").fx.particles.held, false);
  assert.equal(T.themeLook(lib, "limbo").lasers.L2.hex, "#ffffff", "Limbo's red pin never becomes the second laser colour");
});

// ------------------------------------------------------------------------------------------ choosing a theme --
test("the fader walk covers every theme once in colour-wheel order, Custom at the top, each detent at least 5 positions", () => {
  const seq = [];
  const width = new Map();
  for (let cc = 0; cc <= 127; cc++) {
    const id = T.themeAtFader(lib, cc / 127);
    if (seq[seq.length - 1] !== id) seq.push(id);
    width.set(id, (width.get(id) || 0) + 1);
  }
  assert.deepEqual(seq, [...lib.faderOrder], "monotone: each detent visited once, in order");
  assert.equal(seq.length, 22);
  assert.deepEqual(new Set(seq.filter((id) => id !== "custom")), new Set(lib.ids));
  assert.equal(seq[seq.length - 1], "custom");
  for (const [id, n] of width) assert.ok(n >= 5, `${id} has ${n} positions`);
  for (const id of lib.faderOrder) assert.equal(T.themeAtFader(lib, T.faderCentre(lib, id)), id);
  assert.equal(T.themeAtFader(lib, -1), lib.faderOrder[0]);
  assert.equal(T.themeAtFader(lib, 2), "custom");
});

test("a fader pick lands only after 150 ms at rest, and a fader parked on a detent edge does not flicker", () => {
  const p = new T.FaderPicker(lib);
  const n = lib.faderOrder.length;
  p.move(5.5 / n, 0);
  assert.equal(p.poll(149), null);
  assert.equal(p.poll(150), lib.faderOrder[5]);
  assert.equal(p.poll(400), null, "picked once");
  // sweeping through detents: nothing lands until it rests
  for (let k = 0; k < 10; k++) p.move((6.5 + k) / n, 400 + k * 40);
  assert.equal(p.poll(400 + 9 * 40 + 100), null);
  assert.equal(p.poll(400 + 9 * 40 + 150), lib.faderOrder[15]);
  // jitter across the edge between detents 15 and 16 stays on 15
  for (let k = 0; k < 20; k++) p.move((16 + (k % 2 ? 0.1 : -0.1)) / n, 1000 + k * 30);
  assert.equal(p.poll(2000), null);
  p.move(16.5 / n, 2000);
  assert.equal(p.poll(2150), lib.faderOrder[16]);
});

test("after another source changes the theme, touching the fader picks its detent again; an untouched fader never does", () => {
  const clock = grid(500);
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  const x = T.faderCentre(lib, "molten");
  d.onFader(x, 0);
  run(d, 0, 2000, clock);
  assert.equal(d.current, "molten");
  d.onStep(1, 2100, clock);
  run(d, 2100, 4000, clock);
  assert.notEqual(d.current, "molten");
  run(d, 4000, 12000, clock);
  assert.notEqual(d.current, "molten", "the fader sat still: nothing re-picks");
  d.onFader(x + 0.001, 12000);                  // a touch inside the same detent
  const c = run(d, 12000, 14000, clock);
  assert.deepEqual(c.map((y) => [y.id, y.reason]), [["molten", "fader"]]);
});

test("a step walks the fader's order and wraps; Custom is not a step", () => {
  const order = lib.faderOrder.filter((id) => id !== "custom");
  assert.equal(T.stepTheme(lib, order[0], 1), order[1]);
  assert.equal(T.stepTheme(lib, order[0], -1), order[order.length - 1]);
  assert.equal(T.stepTheme(lib, order[order.length - 1], 1), order[0]);
  assert.equal(T.stepTheme(lib, "custom", 1), order[0]);
  let id = order[0];
  const seen = new Set();
  for (let k = 0; k < order.length; k++) { seen.add(id); id = T.stepTheme(lib, id, 1); }
  assert.equal(seen.size, 21);
  assert.equal(T.nextInFamily(lib, "night-sea", "night"), "temple-light");
  assert.equal(T.nextInFamily(lib, "limbo", "night"), "night-sea");
  assert.equal(T.nextInFamily(lib, "molten", "night"), "night-sea");
});

test("fader 2: a +-15 degree drift with a centre detent inside a theme; a full turn in Custom", () => {
  assert.equal(T.hueDriftFromFader(0.5), 0);
  assert.equal(T.hueDriftFromFader(0.53), 0);
  assert.ok(Math.abs(T.hueDriftFromFader(1) - 15) < 1e-9 && Math.abs(T.hueDriftFromFader(0) + 15) < 1e-9);
  assert.equal(T.customTurnFromFader(0.25), 90);
});

// --------------------------------------------------------------------------------------------- when it lands --
test("Daniel's pick lands on the next bar line, not before", () => {
  const clock = grid(500);                      // bars every 2000 ms
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  assert.equal(d.onStep(1, 1100, clock), true);
  assert.equal(d.state.pending.atMs, 2000);
  assert.equal(d.state.pending.on, "bar");
  assert.equal(d.tick(1999, clock), null);
  const c = d.tick(2000, clock);
  assert.equal(c.id, T.stepTheme(lib, "night-sea", 1));
  assert.equal(c.on, "bar");
  assert.equal(d.current, c.id);
  // the fader: rests 150 ms, then waits for the bar
  const f = new T.ThemeDirector(lib, { initial: "night-sea" });
  f.onFader(T.faderCentre(lib, "molten"), 2100);
  assert.equal(f.tick(2200, clock), null);
  assert.equal(f.state.pending, null, "not rested yet");
  assert.equal(f.tick(2250, clock), null);
  assert.equal(f.state.pending.atMs, 4000);
  const changes = run(f, 2300, 4000, clock);
  assert.deepEqual(changes.map((x) => [x.id, x.atMs, x.reason]), [["molten", 4000, "fader"]]);
  assert.equal(f.pinned, true);
});

test("with the page's BeatClock: on its downbeat when it numbers bars, else the next beat; with no clock, at once", () => {
  // the engine announced beat n = 1 at 1000 ms and n = 2 at 1500 ms (120 BPM)
  const bc = new BeatClock();
  bc.schedule(800, { due_ms: 200, bpm: 120, conf: 0.9, n: 1, on_beat: null });
  bc.update(1000, 0.016);
  bc.schedule(1010, { due_ms: 490, bpm: 120, conf: 0.9, n: 2, on_beat: null });
  const bars = T.clockFromBeatClock(bc, { bars: true });
  assert.deepEqual(T.landing(1100, bars, "bar"), { atMs: 2500, on: "bar" }, "n = 4 lands at 2500");
  assert.deepEqual(T.landing(1100, bars, "phrase"), { atMs: 1500 + 30 * 500, on: "phrase" }, "n = 32");
  const plain = T.clockFromBeatClock(bc, { bars: false });
  assert.deepEqual(T.landing(1100, plain, "bar"), { atMs: 1500, on: "beat" });
  assert.deepEqual(T.landing(1100, null, "bar"), { atMs: 1100, on: "now" });
  assert.deepEqual(T.landing(9000, bars, "bar"), { atMs: 9000, on: "now" }, "a clock silent past its flywheel lands now");
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  d.onStep(1, 1100, bars);
  assert.equal(d.tick(2499, bars), null);
  assert.equal(d.tick(2500, bars).on, "bar");
  const now = new T.ThemeDirector(lib, { initial: "night-sea" });
  now.onStep(1, 1100, null);
  assert.equal(now.tick(1100, null).on, "now");
});

test("Theme Lock: Daniel's picks wait for the phrase line, automatic changes are held", () => {
  const clock = grid(500);                      // phrases every 16000 ms
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  d.setLock(true);
  d.onStep(1, 1100, clock);
  assert.equal(d.state.pending.atMs, 16000);
  assert.equal(d.state.pending.on, "phrase");
  run(d, 1100, 16000, clock);
  d.unpin();
  assert.equal(d.onSection("break", 17000, clock), false, "the lock holds the theme");
  assert.equal(d.state.pending, null);
  // locking while a pick waits moves it to the phrase line
  const e = new T.ThemeDirector(lib, { initial: "night-sea" });
  e.onStep(1, 100, clock);
  assert.equal(e.state.pending.atMs, 2000);
  e.setLock(true);
  e.tick(200, clock);
  assert.equal(e.state.pending.atMs, 16000);
});

test("automatic changes land on phrase lines, at least 8 bars apart; a section detected late lands on the next bar", () => {
  const clock = grid(500);
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  d.onFamilyTab("celestial", 0, clock);         // Daniel's family tab, no section yet: its quiet start, on the bar (0 ms)
  assert.deepEqual(run(d, 0, 100, clock).map((x) => [x.id, x.reason]), [["celestial-violet", "family"]]);
  d.onSection("climax", 3000, clock);
  assert.equal(d.state.pending.atMs, null, "held 8 bars after the tab's pick landed at 0: it lands on the phrase line at 16000");
  let c = run(d, 3000, 16000, clock);
  assert.deepEqual(c.map((x) => [x.id, x.atMs, x.reason]), [["violet-rose", 16000, "section"]]);
  d.onSection("break", 17000, clock);            // inside the 8-bar hold (until 32000)
  assert.equal(d.state.pending.atMs, null);
  c = run(d, 17000, 31950, clock);
  assert.equal(c.length, 0);
  c = run(d, 32000, 32000, clock);
  assert.deepEqual(c.map((x) => [x.id, x.atMs]), [["temple-light", 32000]]);
  // a drop found one beat after it began (its own phrase line) lands on the next bar, not 8 bars later
  const e = new T.ThemeDirector(lib, { initial: "celestial-violet" });
  e.onFamilyTab("celestial", 0, clock);
  e.onSection("climax", 16500, clock, { startedAt: 16000 });
  assert.equal(e.state.pending.atMs, 18000);
  assert.equal(e.state.pending.on, "bar");
  // asking again for the same section keeps the time already set
  e.onSection("climax", 16700, clock);
  assert.equal(e.state.pending.atMs, 18000);
});

test("a big hue jump or a flagged theme cuts through black", () => {
  assert.equal(T.needsDip(lib, "void-ritual", "night-sea"), true, "red to deep blue: more than 100 degrees");
  assert.equal(T.needsDip(lib, "night-sea", "uv-euphoria"), false, "blue to UV violet");
  assert.equal(T.needsDip(lib, "night-sea", "fire-and-ice"), true, "Fire & Ice is flagged");
  assert.equal(T.needsDip(lib, "bone-line", "brass-break"), true, "both flagged");
  assert.equal(T.needsDip(lib, "molten", "molten"), false);
  const d = new T.ThemeDirector(lib, { initial: "void-ritual" });
  d.onFader(T.faderCentre(lib, "night-sea"), 0);
  const c = run(d, 0, 4000, grid(500));
  assert.equal(c.length, 1);
  assert.equal(c[0].cut, true);
});

// ----------------------------------------------------------------------------------------------- key families --
test("the key's family: every key on the Camelot wheel, relative major and minor together", () => {
  for (const [n, e] of Object.entries(lib.camelot)) {
    const [maj, min] = e.keys.split(" / ");
    const major = T.parseKey(`${maj} major`), minor = T.parseKey(`${min.replace(/m$/, "")} minor`);
    assert.equal(major.number, Number(n), `${maj} major`);
    assert.equal(minor.number, Number(n), `${min}`);
    assert.equal(major.camelot, `${n}B`);
    assert.equal(minor.camelot, `${n}A`);
    assert.equal(T.familyForKey(lib, `${maj} major`), e.family);
    assert.equal(T.familyForKey(lib, `${min.replace(/m$/, "")} minor`), e.family);
  }
  assert.equal(T.familyForKey(lib, "Db major"), "ritual");
  assert.equal(T.familyForKey(lib, "F minor"), "fire");
  assert.equal(T.familyForKey(lib, "A minor"), "night");
  assert.equal(T.familyForKey(lib, "C# minor"), "celestial");
  assert.equal(T.familyForKey(lib, "Bb minor"), T.familyForKey(lib, "A# minor"), "enharmonic spellings agree");
  for (const bad of ["H major", "C#x", "c major", "", null, 42]) assert.equal(T.parseKey(bad), null, String(bad));
  const fams = new Set(Object.values(lib.camelot).map((e) => e.family));
  for (const f of fams) assert.ok(lib.families[f], `${f} has a playbook`);
});

test("key auto: the database key lands at once, chordsense's after 8 bars at confidence 0.6, Daniel's pick wins until the next track", () => {
  const clock = grid(500);                      // bars of 2000 ms: 8 bars = 16000 ms
  const d = new T.ThemeDirector(lib, { initial: "celestial-violet" });
  d.onKey({ t: "key", name: "F minor", src: "db" }, 100, clock);
  assert.equal(d.family, "fire");
  assert.equal(d.mode, "minor");
  let c = run(d, 100, 16000, clock);
  assert.deepEqual(c.map((x) => [x.id, x.reason]), [[lib.families.fire.anti, "db-key"]], "no section yet: the quiet start");
  // chordsense: too unsure, then sure but not yet stable
  assert.equal(d.onKey({ t: "key", name: "Bb minor", conf: 0.5, src: "audio" }, 17000, clock), false);
  assert.equal(d.onKey({ t: "key", name: "Bb minor", conf: 0.7, src: "audio" }, 17000, clock), true);
  run(d, 17000, 32950, clock);
  assert.equal(d.state.key, "F minor", "not yet 8 bars");
  run(d, 33000, 33000, clock);
  assert.equal(d.state.key, "Bb minor");
  assert.equal(d.family, "ritual");
  // a different key arriving resets the wait
  d.onKey({ t: "key", name: "C major", conf: 0.9, src: "keys" }, 40000, clock);
  d.onKey({ t: "key", name: "G major", conf: 0.9, src: "keys" }, 50000, clock);
  run(d, 40000, 60000, clock);
  assert.equal(d.state.key, "Bb minor", "neither held 8 bars");
  // Daniel picks: the key changes the mode, not the theme
  d.onStep(1, 70000, clock);
  run(d, 70000, 72000, clock);
  const picked = d.current;
  d.onKey({ t: "key", name: "A minor", src: "db" }, 73000, clock);
  run(d, 73000, 120000, clock);
  assert.equal(d.current, picked);
  // his family tab beats the key until the next track
  d.onFamilyTab("pyro", 121000, clock);
  d.onKey({ t: "key", name: "C major", src: "db" }, 122000, clock);
  assert.equal(d.family, "pyro");
  d.newTrack();
  assert.equal(d.pinned, false);
  assert.equal(d.familySrc, null);
  d.onKey({ t: "key", name: "C major", src: "db" }, 130000, clock);
  assert.equal(d.family, "night");
  assert.equal(d.mode, "major");
});

// ----------------------------------------------------------------------------------------- section rotation --
test("section rotation: the family's playbook, a returning section returns to its theme, a build holds, an unknown rotates nothing", () => {
  const clock = grid(500);
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  d.onFamilyTab("celestial", 0, clock);
  const seq = [];
  let t = 0;
  const go = (section, opts) => { t += 40000; d.onSection(section, t, clock, opts); seq.push(...run(d, t, t + 39000, clock).map((x) => x.id)); };
  go("anti-climax");
  go("climax");
  go("break");
  go({ kind: "climax", n: 2 });
  assert.deepEqual(seq, ["celestial-violet", "violet-rose", "temple-light", "uv-euphoria"]);
  // Daniel presses the family tab twice inside a bar during a climax: the next theme of the family, remembered
  t += 40000;
  d.onSection("climax", t, clock);
  run(d, t, t + 39000, clock);
  assert.equal(d.current, "violet-rose", "the first climax's theme comes back");
  d.onFamilyTab("celestial", t + 39100, clock);
  d.onFamilyTab("celestial", t + 39500, clock);
  assert.equal(d.state.pending.atMs, t + 40000, "his pick lands on the next bar");
  run(d, t + 39100, t + 40000, clock);
  assert.equal(d.current, "uv-euphoria");
  seq.length = 0;
  go("break");
  go("climax");
  assert.deepEqual(seq, ["temple-light", "uv-euphoria"], "the climax returns to his pick");
  // a build lives inside the break; an unknown section changes nothing
  const before = d.current;
  t += 40000;
  assert.equal(d.onSection("build", t, clock), false);
  assert.equal(d.onSection("mystery", t, clock), false);
  assert.equal(d.onSection(null, t, clock), false);
  assert.equal(run(d, t, t + 39000, clock).length, 0);
  assert.equal(d.current, before);
});

test("the playbooks answer every section in every family", () => {
  const sections = ["intro", "anti-climax", "climax", { kind: "climax", n: 2 }, "finale", "break", "piano", "outro",
                    "quiet", "verse", "chorus", "bridge"];
  for (const fam of Object.keys(lib.families)) {
    for (const s of sections) {
      const pick = T.themeForSection(lib, fam, s);
      assert.ok(pick && lib.byId.has(pick.id), `${fam} ${JSON.stringify(s)}`);
    }
    assert.ok(T.themeForSection(lib, fam, null), `${fam} with no section`);
    assert.equal(T.themeForSection(lib, fam, "build"), null);
  }
  assert.equal(T.themeForSection(lib, "fire", "finale").id, "molten");
  assert.equal(T.themeForSection(lib, "worship", "chorus").id, "sanctuary-gold");
  assert.equal(T.themeForSection(lib, "night", { kind: "climax", n: 2 }).id, "uv-euphoria");
  assert.equal(T.themeForSection(lib, "line", "anti-climax").id, "bone-line");
});

// --------------------------------------------------------------------------------------- what a theme gives --
test("the scene: four linear palette stops A, B, their midpoint and W; the kick glow is W, or white where W is a pin", () => {
  for (const t of lib.themes) {
    const L = T.themeLook(lib, t.id);
    assert.ok(L.scene.palette instanceof Float32Array && L.scene.palette.length === 12);
    const near = (a, b) => a.every((v, i) => Math.abs(v - b[i]) < 1e-6);
    assert.ok(near([...L.scene.palette.slice(0, 3)], T.hexToLinear(t.A)), `${t.id} stop 0 = A`);
    assert.ok(near([...L.scene.palette.slice(3, 6)], T.hexToLinear(t.B)), `${t.id} stop 1 = B`);
    assert.ok(near([...L.scene.palette.slice(9, 12)], T.hexToLinear(t.W)), `${t.id} stop 3 = W`);
    const a = T.toOklch(T.hexToLinear(t.A)), b = T.toOklch(T.hexToLinear(t.B)), m = T.toOklch(L.scene.stops[2].lin);
    if (t.split_only || t.crossfade_needs_dip) {
      assert.ok(m.L >= a.L - 1e-3 && m.L <= a.L + 0.101, `${t.id} stop 2 is A lifted`);
      assert.ok(m.C >= 0.85 * a.C - 0.004, `${t.id} stop 2 keeps A's colour`);
    } else {
      assert.ok(m.C >= 0.9 * Math.min(a.C, b.C), `${t.id} stop 2 is no grey midpoint (${m.C.toFixed(3)})`);
    }
    const glow = t.fx.flash === "white" ? "#ffffff" : t.W;
    assert.equal(L.scene.kickGlow.hex, glow, t.id);
    assert.equal(L.scene.ground ? L.scene.ground.hex : null, t.ground || null);
  }
  assert.equal(T.themeLook(lib, "limbo").scene.kickGlow.hex, "#ffffff");
  assert.equal(T.themeLook(lib, "laser-green").scene.kickGlow.hex, "#ffffff");
});

test("the lasers: the two-colour pair, the strobe and burst colours, the colour modes the pair allows", () => {
  for (const t of lib.themes) {
    const L = T.themeLook(lib, t.id);
    const lc = (r) => (t.beam && t.beam[r]) || t[r];
    assert.equal(L.lasers.L1.hex, lc(t.lasers[0]), t.id);
    if (t.lasers[1]) assert.equal(L.lasers.L2.hex, lc(t.lasers[1]), t.id);
    assert.deepEqual(L.lasers.triple.map((c) => c.hex), t.strobe.triple.map(lc));
    assert.deepEqual(L.lasers.flicker.map((c) => c.hex), t.strobe.flicker.map(lc));
    assert.deepEqual(L.lasers.burst.map((c) => c.hex), t.burst.map(lc));
    if (t.split_only) assert.ok(!L.lasers.modes.includes("M2") && !L.lasers.modes.includes("M3"), `${t.id} is split-only`);
    if (L.lasers.modes.includes("M3") && L.lasers.hueGapDeg !== null) assert.ok(L.lasers.hueGapDeg <= 80, t.id);
    for (const m of ["M1", "M4", "M8"]) assert.ok(L.lasers.modes.includes(m));
    assert.ok(L.lasers.burstModes.length >= 1 && L.lasers.burstModes.every((m) => L.lasers.modes.includes(m)));
    // at most two hue families among everything the lasers emit, plus white (the headline brief's colour discipline)
    const hues = [...new Set(strobing(L).slice(0, -3).map((c) => c.hex))].map((h) => T.toOklch(T.hexToLinear(h)))
      .filter((c) => c.C >= 0.06).map((c) => c.h);
    const groups = [];
    for (const h of hues) { const g = groups.find((x) => x.some((y) => T.hueGapDeg(h, y) <= 45)); if (g) g.push(h); else groups.push([h]); }
    assert.ok(groups.length <= 2, `${t.id}: ${groups.length} hue families`);
  }
  assert.equal(T.themeLook(lib, "pink-pyro").lasers.L1.hex, "#ff5c9a", "the corrected Pink Pyro laser");
  assert.equal(T.themeLook(lib, "golden-wings").lasers.L2.hex, "#f9e5c5", "one laser role: L2 is W");
  assert.deepEqual(T.themeLook(lib, "violet-rose").lasers.modes, ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]);
  assert.deepEqual(T.themeLook(lib, "magenta-classics").lasers.modes, ["M1", "M4", "M5", "M6", "M7", "M8", "M9"]);
});

test("the long drop swaps the lasers' role every 16 bars, never onto a held colour", () => {
  assert.deepEqual([0, 15, 16, 31, 32, 48].map(T.laserSwapDue), [false, false, true, true, false, true]);
  assert.equal(T.themeLook(lib, "golden-wings", { swap: true }).lasers.L1.hex, "#6d5bf9", "gold swaps to violet");
  assert.deepEqual(T.themeLook(lib, "laser-green", { swap: true }).lasers.roles, ["B", "A"]);
  assert.deepEqual(T.themeLook(lib, "red-tribe", { swap: true }).lasers.roles, ["B", "W"], "A is held: no swap");
  assert.deepEqual(T.themeLook(lib, "pink-pyro", { swap: true }).lasers.roles, ["A"], "B is held: no swap");
});

test("the key's nudge and the drift tint the scene within +-15 degrees; the pads are never tinted", () => {
  for (const id of ["night-sea", "violet-rose", "laser-green", "golden-wings"]) {
    const base = T.themeLook(lib, id), maj = T.themeLook(lib, id, { mode: "major", hueDeg: 15 });
    const a0 = T.toOklch(base.scene.stops[0].lin), a1 = T.toOklch(maj.scene.stops[0].lin);
    assert.ok(T.hueGapDeg(a0.h, a1.h) <= 15.5, `${id} moved ${T.hueGapDeg(a0.h, a1.h).toFixed(1)} degrees`);
    assert.ok(a1.L > a0.L, `${id} major is lighter`);
    assert.deepEqual(maj.pads, base.pads);
  }
  const custom = T.themeLook(lib, "night-sea", { custom: true, hueDeg: 180 });
  const h0 = T.toOklch(T.themeLook(lib, "night-sea").scene.stops[0].lin).h, h1 = T.toOklch(custom.scene.stops[0].lin).h;
  assert.ok(T.hueGapDeg(h0, h1) > 150, "Custom turns the pair round the wheel");
});

test("the effects: shockwave, particles and flash take the theme's roles; the flash stays white or the W tint", () => {
  for (const t of lib.themes) {
    const L = T.themeLook(lib, t.id);
    assert.equal(L.fx.flash.hex, t.fx.flash === "white" ? "#ffffff" : t.W);
    const res = (r) => (r === "white" ? "#ffffff" : r === "line" ? t.line : t[r]);
    assert.equal(L.fx.shockwave.hex, res(t.fx.shockwave));
    assert.equal(L.fx.particles.hex, res(t.fx.particles));
  }
  assert.equal(T.themeLook(lib, "cathedral-jewel").fx.particles.hex, "#8e7165", "the bronze lead line");
});

test("themeLook is pure: the same inputs give the same look", () => {
  const plain = (L) => JSON.stringify(L, (k, v) => (v instanceof Float32Array ? [...v] : v));
  for (const opts of [{}, { mode: "minor", hueDeg: -9, swap: true }, { custom: true, hueDeg: 222 }]) {
    assert.equal(plain(T.themeLook(lib, "uv-euphoria", opts)), plain(T.themeLook(lib, "uv-euphoria", opts)));
  }
  assert.throws(() => T.themeLook(lib, "no-such-theme"), /no theme/);
  const d = new T.ThemeDirector(lib, { initial: "uv-euphoria" });
  assert.equal(plain(d.look()), plain(T.themeLook(lib, "uv-euphoria")));
});

// ------------------------------------------------------------------- round 1 fixes (the verifier's verdict on 087df62d) --
// The page's BeatClock fed the way the engine feeds it (each beat announced aheadMs early, with its number), 60 Hz frames, a
// fresh clock adapter every frame (as the page hook-up will build it). press(d, now, clock) is called once at pressAt; the
// result is the first change that lands, with the frame it landed on.
function beatSim(beats, { pressAt, press = (d, now, clock) => d.onStep(1, now, clock), lock = false, aheadMs = 250,
                          initial = "night-sea", endMs = null } = {}) {
  const bc = new BeatClock(), d = new T.ThemeDirector(lib, { initial });
  if (lock) d.setLock(true);
  const dt = 1000 / 60, end = endMs ?? Math.max(beats[beats.length - 1].t, pressAt) + 9000;
  let ai = 0, pressed = false;
  for (let now = 0; now < end; now += dt) {
    while (ai < beats.length && beats[ai].t - (beats[ai].ahead ?? aheadMs) <= now) {
      const b = beats[ai++];
      bc.schedule(now, { bpm: b.bpm, conf: 0.9, due_ms: b.t - now, n: b.n });
    }
    bc.update(now, dt / 1000);
    const clock = T.clockFromBeatClock(bc, { bars: true });
    if (!pressed && now >= pressAt) { pressed = true; press(d, now, clock); }
    const change = d.tick(now, clock);
    if (change) return { landed: now, change, d };
  }
  return { landed: null, change: null, d };
}
const FRAME = 1000 / 60 + 0.01;

test("fix 1 (must fix): particles are held when the colour actually emitted is a saturated red, whatever tinted it", () => {
  // the verifier's repro: Pink Pyro picked on the fader during a major-key track (key auto is on by default)
  const clock = grid(400);
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  d.onKey({ name: "E major", src: "db" }, 0, clock);
  d.onFader(T.faderCentre(lib, "pink-pyro"), 0);
  run(d, 0, 40000, clock, 1000 / 60);
  assert.equal(d.current, "pink-pyro");
  const p = d.look().fx.particles;
  assert.equal(p.hex, "#de3d56");
  assert.ok(T.isSaturatedRed(p.hex), "the emitted particle colour is a saturated red (linear ratio 0.839)");
  assert.equal(p.held, true, "so it must be held: steady embers, never pulsed");
  // fader 2's drift with no key at all: +4 and +6 degrees turn Pink Pyro's A red
  for (const hueDeg of [4, 6]) {
    const q = new T.ThemeDirector(lib, { initial: "pink-pyro", keyAuto: false }).look({ hueDeg }).fx.particles;
    assert.ok(T.isSaturatedRed(q.hex) && q.held, `drift +${hueDeg}: ${q.hex} held=${q.held}`);
  }
  // the sweep: every theme, both modes and none, drift -15..15 in 0.5 degree steps, and Custom round the wheel in 1 degree
  // steps; a red particle colour is always flagged held, and a theme whose own particle colour is a held red stays held
  let reds = 0, n = 0;
  for (const t of lib.themes) {
    const ownRed = T.isSaturatedRed(t.fx.particles === "white" ? "#ffffff" : t.fx.particles === "line" ? t.line : t[t.fx.particles]);
    for (const mode of [null, "major", "minor"]) {
      const variants = [];
      for (let h = -15; h <= 15; h += 0.5) variants.push({ mode, hueDeg: h });
      for (let h = 0; h < 360; h += 1) variants.push({ mode, hueDeg: h, custom: true });
      for (const opts of variants) {
        const q = T.themeLook(lib, t.id, opts).fx.particles;
        n++;
        if (T.isSaturatedRed(q.hex)) { reds++; assert.equal(q.held, true, `${t.id} ${JSON.stringify(opts)} ${q.hex}`); }
        if (ownRed) assert.equal(q.held, true, `${t.id} ${JSON.stringify(opts)}: the theme's held ember stays held`);
      }
    }
  }
  assert.ok(n > 20000 && reds > 800, `${reds} red particle colours among ${n} looks`);
});

test("fix 2: a waiting change follows the beat grid until it lands (tempo ramp, refinement, re-anchor)", () => {
  const ramp = [];
  for (let n = 0, t = 1000; n < 120; n++) {
    const bpm = n < 40 ? 150 : n < 56 ? 150 + (6 * (n - 40)) / 16 : 156;
    ramp.push({ n, t, bpm });
    t += 60000 / bpm;
  }
  // Theme Lock: the pick waits for the phrase line n = 64 through a 150 -> 156 ramp (was 240 ms late)
  let r = beatSim(ramp, { pressAt: ramp[33].t + 30, lock: true });
  assert.equal(r.change.on, "phrase");
  assert.ok(r.landed >= ramp[64].t - 0.01 && r.landed - ramp[64].t <= FRAME, `ramp: off by ${(r.landed - ramp[64].t).toFixed(1)} ms`);
  // the engine refines 150 -> 150.5 BPM after the press (was 40 ms late)
  const refine = [];
  for (let n = 0, t = 1000; n < 120; n++) { const bpm = n < 34 ? 150 : 150.5; refine.push({ n, t, bpm }); t += 60000 / bpm; }
  r = beatSim(refine, { pressAt: refine[33].t + 30, lock: true });
  assert.ok(r.landed >= refine[64].t - 0.01 && r.landed - refine[64].t <= FRAME, `refine: off by ${(r.landed - refine[64].t).toFixed(1)} ms`);
  // a tap moves the grid half a beat later between the press and the bar (was 183 ms early)
  const shifted = [];
  for (let n = 0; n < 120; n++) shifted.push({ n, t: 1000 + n * 400 + (n >= 42 ? 200 : 0), bpm: 150 });
  r = beatSim(shifted, { pressAt: shifted[40].t + 20 });
  assert.equal(r.change.on, "bar");
  assert.ok(r.landed >= shifted[44].t - 0.01 && r.landed - shifted[44].t <= FRAME, `re-anchor: off by ${(r.landed - shifted[44].t).toFixed(1)} ms`);
  // and a steady grid at 128, 150 and 180 BPM still lands every press within a frame of its downbeat, never early
  for (const bpm of [128, 150, 180]) {
    const steady = Array.from({ length: 80 }, (_, n) => ({ n, t: 1000 + (n * 60000) / bpm, bpm }));
    for (const k of [9, 22, 37]) {
      const s = beatSim(steady, { pressAt: steady[k].t + 50 });
      const down = steady.find((b) => b.n % 4 === 0 && b.t >= steady[k].t + 50);
      assert.ok(s.landed >= down.t - 0.01 && s.landed - down.t <= FRAME, `${bpm} BPM press after beat ${k}: ${(s.landed - down.t).toFixed(1)} ms`);
    }
  }
});

test("fix 2: a grid that jumps earlier past the waiting line lands at once, not a bar late", () => {
  // the pick waits for beat 44 at 18600 ms; the engine then announces beat 44 late (5 ms after it sounded, at 18560): the
  // frame that hears it is past the moved line, and the next bar line is 1600 ms away
  const beats = [];
  for (let n = 0; n < 120; n++) {
    beats.push(n < 44 ? { n, t: 1000 + n * 400, bpm: 150 } : { n, t: 1000 + n * 400 - 40, bpm: 150, ahead: n === 44 ? -5 : 250 });
  }
  const r = beatSim(beats, { pressAt: beats[41].t + 20 });
  assert.ok(r.landed >= 18560 && r.landed - 18560 <= FRAME, `landed ${(r.landed - 18560).toFixed(1)} ms after the moved line`);
});

test("fix 2 (with the flywheel): a pick pressed while the beat drops out lands on the true downbeat, counting flywheel beats", () => {
  // numbered beats 0..17, then silence: the BeatClock flywheels on (unnumbered beats) for 4 s after the last message.
  // Flywheel beat 20 fires at 9000 ms; the press at 9100 waits for beat 24 at 10600 ms
  const beats = Array.from({ length: 18 }, (_, n) => ({ n, t: 1000 + n * 400, bpm: 150 }));
  const r = beatSim(beats, { pressAt: 9100, endMs: 14000 });
  assert.ok(r.landed !== null, "it lands");
  assert.equal(r.change.on, "bar");
  assert.ok(r.landed >= 10600 - 0.01 && r.landed - 10600 <= FRAME, `landed at ${r.landed.toFixed(1)} (the downbeat is 10600)`);
});

test("fix 3: a family tab with no section known picks one of that family's own themes", () => {
  const clock = grid(400);
  const first = {};
  for (const fam of Object.keys(lib.families)) {
    const d = new T.ThemeDirector(lib, { initial: "night-sea" });
    d.onFamilyTab(fam, 100, clock);
    const id = d.state.pending ? d.state.pending.id : d.current;
    assert.equal(theme(id).family, fam, `tab ${fam} gave ${id} (${theme(id).family})`);
    first[fam] = id;
  }
  assert.deepEqual([first.fire, first.pyro, first.worship], ["molten", "pink-pyro", "sanctuary-gold"]);
  // presses inside a bar then walk the family from there
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  const ids = [];
  for (const t of [100, 600, 1100]) { d.onFamilyTab("fire", t, clock); ids.push(d.state.pending.id); }
  assert.deepEqual(ids, ["molten", "golden-wings", "fire-and-ice"]);
  // key auto keeps the family's playbook for a quiet start (Fire's anti-climax is Void Ritual by design)
  const k = new T.ThemeDirector(lib, { initial: "night-sea" });
  k.onKey({ name: "F minor", src: "db" }, 0, clock);
  assert.equal(k.state.pending.id, lib.families.fire.anti);
});

test("Theme Lock turned off before a pick lands puts it back on the next bar", () => {
  const clock = grid(500);
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  d.onStep(1, 100, clock);
  d.setLock(true);
  d.setLock(false);
  const c = run(d, 100, 20000, clock);
  assert.deepEqual(c.map((x) => [x.atMs, x.on]), [[2000, "bar"]]);
});

test("Custom's turn of the wheel counts in the black-dip test", () => {
  const clock = grid(500);
  // Custom turned half way round (the page draws it with hueDeg 180), then a step to Temple of Light
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  d.onFader(T.faderCentre(lib, "custom"), 0);
  run(d, 0, 2000, clock);
  assert.equal(d.custom, true);
  d.look({ hueDeg: 180 });
  d.onStep(1, 2100, clock);
  let c = run(d, 2100, 4000, clock);
  assert.deepEqual(c.map((x) => [x.id, x.cut]), [["temple-light", true]]);
  // fader 2 routed to the director: the same turn, and Custom turned 180 degrees back to its own theme dips too
  const e = new T.ThemeDirector(lib, { initial: "night-sea" });
  e.onFader2(0.5);
  e.onFader(T.faderCentre(lib, "custom"), 0);
  run(e, 0, 2000, clock);
  assert.ok(Math.abs(T.toOklch(e.look().scene.stops[0].lin).h - T.toOklch(T.themeLook(lib, "night-sea", { custom: true, hueDeg: 180 }).scene.stops[0].lin).h) < 1e-9);
  e.onFader2(0.5);
  e.onFader(T.faderCentre(lib, "night-sea"), 2100);
  c = run(e, 2100, 6000, clock);
  assert.deepEqual(c.map((x) => [x.id, x.custom, x.cut]), [["night-sea", false, true]]);
  // an unturned Custom (fader 2 at 0) stepping to Temple of Light is a short hue move: a crossfade
  const f = new T.ThemeDirector(lib, { initial: "night-sea" });
  f.onFader2(0);
  f.onFader(T.faderCentre(lib, "custom"), 0);
  run(f, 0, 2000, clock);
  f.onStep(1, 2100, clock);
  assert.deepEqual(run(f, 2100, 4000, clock).map((x) => [x.id, x.cut]), [["temple-light", false]]);
  assert.equal(T.needsDip(lib, "night-sea", "night-sea", { fromHueDeg: 180 }), true);
  assert.equal(T.needsDip(lib, "night-sea", "night-sea"), false);
});

test("a different key below confidence 0.6 still breaks a waiting chordsense key's 8 quiet bars", () => {
  const clock = grid(500);                      // bars of 2000 ms
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  d.onKey({ name: "Db major", conf: 0.7, src: "audio" }, 0, clock);
  for (let bar = 1; bar <= 8; bar++) d.onKey({ name: "C major", conf: 0.5, src: "audio" }, bar * 2000, clock);
  run(d, 0, 17000, clock);
  assert.equal(d.state.key, null, "C major kept arriving: Db major has not been stable for 8 bars");
  run(d, 17000, 32000, clock);
  assert.equal(d.state.key, "Db major", "8 quiet bars after the last other key");
});

test("an automatic change holds off for 8 bars after a family-tab pick too", () => {
  const clock = grid(500);                      // bars 2000 ms, phrases 16000 ms
  const d = new T.ThemeDirector(lib, { initial: "night-sea" });
  d.onFamilyTab("celestial", 13000, clock);     // lands on the bar at 14000, a bar before the phrase line
  const c = run(d, 13000, 14450, clock);
  d.onSection("climax", 14500, clock);
  c.push(...run(d, 14500, 40000, clock));
  assert.deepEqual(c.map((x) => [x.id, x.atMs, x.reason]), [["celestial-violet", 14000, "family"], ["violet-rose", 32000, "section"]]);
});

test("keys spelled the song-database way (Am, F#m, C, 8A) are understood, and spellings of one key agree", () => {
  assert.equal(T.parseKey("Am").camelot, "8A");
  assert.equal(T.parseKey("Am").name, "A minor");
  assert.equal(T.parseKey("F#m").camelot, T.parseKey("F# minor").camelot);
  assert.equal(T.parseKey("Gbm").camelot, T.parseKey("F#m").camelot);
  assert.equal(T.parseKey("C").camelot, "8B");
  assert.equal(T.parseKey("Ebmaj").camelot, T.parseKey("Eb major").camelot);
  assert.equal(T.parseKey("Bbmin").camelot, T.parseKey("Bb minor").camelot);
  assert.equal(T.parseKey("D Major").name, "D major");
  assert.equal(T.parseKey("A Minor").camelot, "8A");
  assert.equal(T.parseKey("CM"), null, "a capital M alone is ambiguous");
  assert.equal(T.parseKey("8A").name, "A minor");
  assert.equal(T.parseKey("12B").camelot, "12B");
  assert.equal(T.parseKey("5A").camelot, T.parseKey("C minor").camelot);
  for (const bad of ["H major", "Cm7", "c major", "13A", "0B", "", null]) assert.equal(T.parseKey(bad), null, String(bad));
  const clock = grid(500);
  const d = new T.ThemeDirector(lib, { initial: "celestial-violet" });
  d.onKey({ name: "Am", src: "db" }, 0, clock);
  assert.equal(d.state.key, "A minor");
  assert.equal(d.family, "night");
  // chordsense confirming the same key in another spelling is not a new key
  d.onKey({ name: "A minor", conf: 0.9, src: "audio" }, 1000, clock);
  assert.equal(d.state.pending ? d.state.pending.reason : "db-key", "db-key");
  assert.equal(d.keyCand, null);
});

test("twelve red-safe hit colours for the pads' effects: today's palette diagonal with saturated reds taken out", () => {
  const diag = (i) => ((i % 4) + ((i / 4) | 0)) % 4;
  const variants = [{}, { mode: "major" }, { mode: "minor" }, { hueDeg: 15 }, { hueDeg: -15 }, { swap: true }];
  for (let h = 0; h < 360; h += 5) variants.push({ custom: true, hueDeg: h }, { custom: true, hueDeg: h, mode: "major" });
  for (const t of lib.themes) {
    for (const opts of variants) {
      const L = T.themeLook(lib, t.id, opts);
      assert.equal(L.fx.padHits.length, 12);
      L.fx.padHits.forEach((c, i) => {
        assert.ok(!T.isSaturatedRed(c.hex), `${t.id} ${JSON.stringify(opts)} pad ${i + 1} ${c.hex}`);
        const stop = L.scene.stops[diag(i)];
        if (t.held.includes(stop.role)) assert.equal(c.hex, L.lasers.L1.hex, `${t.id} pad ${i + 1}: a held role hits as the laser colour`);
        else if (!T.isSaturatedRed(stop.hex)) assert.equal(c.hex, stop.hex, `${t.id} pad ${i + 1} keeps its stop`);
      });
    }
  }
  assert.deepEqual([0, 7].map((i) => T.themeLook(lib, "molten").fx.padHits[i].hex), ["#f0b225", "#f0b225"], "Molten's ember pads hit gold");
  assert.equal(T.themeLook(lib, "night-sea").fx.padHits[0].hex, "#0155bc");
});
