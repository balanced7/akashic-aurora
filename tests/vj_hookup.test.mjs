// Node tests for the Lasers v2 hook-up (arsenal/web/vj-hookup.js) and the control-map changes it rides on
// (arsenal/web/vj-core.js): Daniel's calls of 2026-10-25 -- the Tap button and pad 12 tap the tempo (the page fires no
// effect for a tap pad), fader 1 is the theme fader (Hue A and B move into Custom), the dial is the laser gate picker,
// Rewind / Fast forward step the sets through one path -- plus the beam records, the head bus (strip v3), Custom's laser
// colours and pad stand-ins, the chord cap. Zero dependencies, no GPU:
//   node --test tests/vj_hookup.test.mjs
// Every number here is synthetic: nothing reads Daniel's playing.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as C from "../arsenal/web/vj-core.js";
import * as L from "../arsenal/web/vj-lasers.js";
import * as H from "../arsenal/web/vj-hookup.js";
import { ledPostedOk, isSaturatedRed, toOklch, hexToLinear } from "../arsenal/web/vj-themes.js";

const here = (p) => new URL(p, import.meta.url);
const F = 1000 / 60;

test("the control map v2: fader 1 is the theme, fader 2 the hue drift, the dial the laser gate, its click AUTO", () => {
  const m = C.DEFAULT_CTL_MAP;
  assert.equal(m.cc105, "theme");
  assert.equal(m.cc106, "hueDrift");
  assert.equal(m.cc116, "laserGate");
  assert.equal(m.cc117, "laserAuto");
  assert.ok(!("cc25" in m) && !("cc26" in m), "Rewind / Fast forward are the transport path's, not the map's");
  for (const t of ["theme", "hueDrift", "hueA", "hueB"]) assert.ok(C.TARGET_IDS.includes(t), t);
  assert.match(C.TARGETS.find((t) => t.id === "hueA").label, /Custom/, "Hue A moved into Custom");
});

test("a control map stored before v2 takes the new defaults where it held the old ones, and keeps every choice", () => {
  const legacy = { cc105: "hueA", cc106: "hueB", cc107: "sat", cc116: "sceneDial", cc117: "sceneGo", cc25: "scenePrev",
                   cc26: "sceneNext", cc120: "bright", cc60: "hueA" };
  const m = C.normalizeCtlMap(legacy);
  assert.equal(m.cc105, "theme");
  assert.equal(m.cc106, "hueDrift");
  assert.equal(m.cc116, "laserGate");
  assert.equal(m.cc117, "laserAuto");
  assert.ok(!("cc25" in m) && !("cc26" in m), "the old scene defaults on the transport are gone");
  assert.equal(m.cc120, "bright", "a learned control stays");
  assert.equal(m.cc60, "hueA", "a control learned to Hue A stays (Hue A lives on in Custom)");
  // the v2 shape round-trips, an unbound default stays unbound
  const v2 = C.serializeCtlMap({ ...C.DEFAULT_CTL_MAP, cc116: null, cc61: "laserVibrate", cc62: "fam_night" });
  assert.equal(v2.v, 2);
  const back = C.normalizeCtlMap(JSON.parse(JSON.stringify(v2)));
  assert.ok(!("cc116" in back), "unbound stays unbound");
  assert.equal(back.cc61, "laserVibrate");
  assert.equal(back.cc62, "fam_night");
  assert.equal(back.cc105, "theme");
  // learn moves an action like a target
  const learned = C.learnBinding(C.DEFAULT_CTL_MAP, "cc118", "laserGate");
  assert.equal(learned.cc118, "laserGate");
  assert.ok(!("cc116" in learned));
});

test("PressGate: a press is the value rising through 0.5; a release, a held repeat and a bounce are not", () => {
  const g = new C.PressGate();
  const ev = (value, id = "cc42") => ({ id, kind: "abs", value, delta: 0 });
  assert.equal(g.press(ev(1), "a", 1000), true);
  assert.equal(g.press(ev(1), "a", 1040), false, "a repeat while held");
  assert.equal(g.press(ev(0), "a", 1080), false, "the release");
  assert.equal(g.press(ev(1), "a", 1100), false, "a bounce inside 160 ms");
  assert.equal(g.press(ev(0), "a", 1150), false);
  assert.equal(g.press(ev(1), "a", 1400), true, "the next real press");
  assert.equal(g.press({ id: "k", kind: "rel", value: 0.5, delta: 1 }, "b", 2000), true, "a relative nudge up presses");
});

test("the gate dial: AUTO, then every gate of the engine, one detent a step, a fast spin cannot run away, the click is AUTO", () => {
  assert.equal(H.GATE_DIAL[0], "auto");
  assert.deepEqual(H.GATE_DIAL.slice(1), L.GATE_IDS);
  const d = new H.GateDial();
  const turn = (delta, t) => d.turn({ id: "cc116", kind: "rel", value: 0.5, delta }, t);
  assert.equal(d.gate, "auto");
  assert.equal(turn(1, 1000), true);
  assert.equal(d.gate, "single");
  assert.equal(turn(3, 1100), true, "a message of any size is one step");
  assert.equal(d.gate, "onetwo");
  let moved = 0;
  for (let t = 2000; t < 2300; t += 10) if (turn(4, t)) moved++;
  assert.ok(moved <= 6, `30 messages in 300 ms move at most one step per 60 ms: ${moved}`);
  assert.ok(d.ignored >= 20);
  assert.equal(d.auto(), true);
  assert.equal(d.gate, "auto");
  assert.equal(turn(-1, 5000), true);
  assert.equal(d.gate, L.GATE_IDS[L.GATE_IDS.length - 1], "it wraps round");
  // an absolute dial steps by the direction it moved
  const a = new H.GateDial();
  a.turn({ id: "x", kind: "abs", value: 0.5 }, 0);
  a.turn({ id: "x", kind: "abs", value: 0.6 }, 100);
  assert.equal(a.gate, "single");
  assert.equal(H.gateLabel("triple"), "Triple Strobe");
  assert.equal(H.gateLabel("auto"), "AUTO");
});

test("the tap pads: the engine's hello names them; pad 12 on the DAW port taps, the bank's pad 12 does not", () => {
  const hello = C.parseEvent({ t: "hello", v: 1, src: "keylab-vj", beat_engine: "a", pads_mode: "both", leds: true,
                               tap: "daw:cc23,daw:pad12", tap_one: true });
  assert.equal(hello.tap, "daw:cc23,daw:pad12");
  assert.equal(hello.tap_one, true);
  const taps = H.tapPadsOf(hello);
  assert.deepEqual(taps, [{ pad: 12, port: "daw" }]);
  assert.equal(H.isTapPad(taps, 12, "daw"), true);
  assert.equal(H.isTapPad(taps, 12, "bank"), false, "the bank's pad 12 is not the tap");
  assert.equal(H.isTapPad(taps, 2, "daw"), false);
  assert.equal(H.isTapPad(taps, 12, "key"), false, "the keyboard never taps the engine");
  assert.equal(H.isTapPad(taps, 12, "demo"), false);
  assert.deepEqual(H.tapPadsOf({ tap: "pad3" }), [{ pad: 3, port: null }]);
  assert.equal(H.tapPadsOf({ tap: "pads" }).length, 12);
  assert.deepEqual(H.tapPadsOf({ tap: "off" }), []);
  assert.deepEqual(H.tapPadsOf(C.parseEvent({ t: "hello", v: 1 })), [], "an older engine taps no pad");
  assert.equal(C.parseEvent({ t: "hello", v: 1, tap: "<script>" }).tap, "", "a malformed list is dropped");
});

test("laserClock gives the laser engine the page grid's posAt (NaN before the first beat)", () => {
  const bc = new C.BeatClock();
  const clk = H.laserClock(bc);
  assert.ok(Number.isNaN(clk.posAt(0)));
  bc.schedule(0, { due_ms: 100, bpm: 120, conf: 0.9, n: 0, ver: 1, bar: 0 });
  bc.update(120, 0.016);
  assert.equal(clk.bpm, 120);
  assert.ok(Math.abs(clk.posAt(350) - 0.5) < 1e-9, "half a beat after the beat");
  assert.equal(clk.alive(350), true);
});

// a real engine hit, framed until it lights
function litFrame(opts, vel = 0.9) {
  const per = 400;
  const clock = { bpm: 150, conf: 1, phaseAt: (t) => (t / per) % 1, nextBeatAt: (t) => Math.ceil(t / per) * per, posAt: (t) => t / per };
  const eng = L.createLaserEngine({ seed: 5, clock, ...opts });
  eng.hit(4000 - 10, vel);
  let out = null;
  for (let t = 3990; t < 4600; t += F) { out = eng.frame(t); if (out.n > 0 && out.heads.some((h) => h > 0.3)) break; }
  return { eng, out };
}

test("packBeams: all records for an ordinary scene; for a laser-heads scene only the hero's beams and figures", () => {
  const beams = litFrame({ patternMode: "fan", bankMode: "both", orderMode: "all" });
  assert.ok(beams.out.n > 0);
  const all = H.packBeams(beams.out, false);
  assert.equal(all.n, beams.out.n);
  assert.equal(all.seg, beams.out.seg, "no copy for an ordinary scene");
  const heroOnly = H.packBeams(beams.out, true);
  let heroRows = 0;
  for (let i = 0; i < beams.out.n; i++) if (beams.out.head[i] === L.HERO_HEAD) heroRows++;
  assert.equal(heroOnly.n, heroRows, "the bank heads are the scene's to draw");
  const fig = litFrame({ shapeMode: "circle", patternMode: "figure" });
  assert.ok(fig.out.n > 1);
  const kept = H.packBeams(fig.out, true);
  assert.equal(kept.n, fig.out.n, "a figure (drawn round the hero) is kept whole, its group headers with it");
  const r = L.decodeSeg(kept.seg, 0, {});
  assert.ok(r.header, "the group header first");
});

test("the head bus: the engine's levels on the pad grid, each head's colour slot from what it drew, into strip v3", () => {
  const themed = { id: "t", L1: "#2244ff", L2: "#22ffaa", W: "#ffffff" };
  const { eng } = litFrame({ patternMode: "fan", bankMode: "both", orderMode: "all", colourMode: "halves", theme: themed });
  const bus = H.headBus(eng);
  const heads = Array.from(bus.subarray(4, 16));
  assert.ok(heads.some((v) => v > 0), "some head lit");
  for (const v of heads) assert.ok(v === 0 || (v - Math.floor(v) > 0 && v - Math.floor(v) < 1 && Math.floor(v) <= 2), `slot + level: ${v}`);
  const slots = new Set(heads.filter((v) => v > 0).map(Math.floor));
  assert.ok(slots.has(0) && slots.has(1), `halves: left heads L1, right heads L2 -> slots ${[...slots]}`);
  assert.ok(bus[3] > 0 && bus[3] <= 1, "solo");
  // into the strip
  const strip = C.createStrip();
  H.writeHeadBus(strip, bus, 7);
  const at = (x, y) => Array.from(strip.subarray((y * 16 + x) * 4, (y * 16 + x) * 4 + 4));
  assert.equal(at(9, 2)[0], 7, "texel 9 keeps the star count");
  assert.deepEqual(at(12, 3).concat(at(13, 3), at(14, 3)).map((v) => +v.toFixed(5)), heads.map((v) => +v.toFixed(5)));
  assert.ok(Math.abs(at(13, 2)[0] - eng.col.L1[0]) < 1e-6 && Math.abs(at(14, 2)[1] - eng.col.L2[1]) < 1e-6, "L1, L2");
  H.writeHeadBus(strip, null, 3);
  assert.deepEqual(at(9, 2), [3, 0, 0, 1], "idle: no pattern, solo 1");
  assert.deepEqual(at(12, 3), [0, 0, 0, 0]);
  assert.equal(C.STRIP.VERSION, 3);
});

test("the Laser Cathedral is tagged laser-heads and reads the head bus only on a v3 host", () => {
  const src = readFileSync(here("../arsenal/web/presets/vj-laser-cathedral.frag"), "utf8");
  const header = JSON.parse(src.split("\n")[1].replace(/^\/\/!\s*/, ""));
  assert.ok(header.tags.includes("laser-heads") && header.tags.includes("vj"));
  assert.match(src, /vjAt\(15, 2\)\.x < 3\.0\) return;/, "an older host (strip v2) or Play: no bus");
  assert.match(src, /vjAt\(12 \+ i \/ 4, 3\)/, "the 12 heads from row 3");
  assert.match(src, /\* gSolo;/, "idle beams dip by the solo level");
});

test("Custom: the lasers take Hue A and B and never emit a saturated red; every Custom pad stand-in reads on the pads", () => {
  for (let h = 0; h < 360; h += 5) {
    const a = C.hueColour(h / 360, 0.7), b = C.hueColour((h + 97) / 360, 0.62);
    const theme = H.customLaserTheme(a, b);
    const col = L.themeColours(theme);
    for (const c of [col.L1, col.L2, col.W, ...col.triple, ...col.flicker, ...col.burst]) assert.ok(!L.isSaturatedRed(c), `hue ${h}`);
    for (const lin of [a, b, [a[0] * 0.3, a[1] * 0.3, a[2] * 0.3]]) {
      const s = H.standInLed(lin);
      assert.ok(ledPostedOk(s.hex), `stand-in ${s.hex} for hue ${h}`);
      assert.ok(s.level > 0 && s.level <= 1);
    }
  }
});

test("the chord colour on a theme while the audio names the chords: a hue turn of at most 15 degrees, no new red", () => {
  const stop = hexToLinear("#0155bc"), chord = hexToLinear("#ff00aa");
  const before = toOklch(stop);
  const out = H.capHue(stop, chord, 1, 15);
  const after = toOklch(out);
  let d = Math.abs(after.h - before.h); if (d > 180) d = 360 - d;
  assert.ok(d <= 15.5 && d > 5, `turned ${d.toFixed(1)} degrees`);
  assert.deepEqual(H.capHue(stop, chord, 0, 15), stop, "no chord, no turn");
  for (let h = 0; h < 360; h += 10) {
    const s = C.hueColour(h / 360, 0.6), c = C.hueColour(((h + 180) % 360) / 360, 0.6);
    const r = H.capHue(s, c, 1, 15);
    assert.ok(!isSaturatedRed(r) || isSaturatedRed(s), `hue ${h}`);
  }
});

test("the air (VJ V2): lane C's haze fluid is reached feature by feature, and a throwing one is dropped, never a crash", () => {
  assert.equal(H.airOf(null), null);
  assert.equal(H.airOf({ step() {} }), null, "nothing a pad can call");
  const calls = [];
  const fluid = { co2: (x, y, s) => calls.push(["co2", x, y, s]), fogPush: (l) => calls.push(["fog", l]), fogRelease: () => calls.push(["rel"]) };
  const air = H.airOf(fluid);
  assert.deepEqual(air.has, { co2: true, fog: true });
  assert.equal(air.co2(0.4, 0, 0.9), true);
  assert.equal(air.fogPush(0.7), true);
  assert.equal(air.fogRelease(), true);
  assert.deepEqual(calls, [["co2", 0.4, 0, 0.9], ["fog", 0.7], ["rel"]]);
  const onlyCo2 = H.airOf({ co2() {} });
  assert.deepEqual(onlyCo2.has, { co2: true, fog: false });
  assert.equal(onlyCo2.fogPush(1), false, "a missing method is a no-op");
  const bad = H.airOf({ co2() { throw new Error("lost context"); }, fogPush() {} });
  assert.equal(bad.co2(0.5, 0, 1), false);
  assert.match(bad.broken, /co2: lost context/);
  assert.equal(bad.fogPush(0.5), false, "once broken, the pads keep their own stand-ins");
});

// Daniel's option C (2026-10-28): "let the page's haze fluid light the scene's heads" -- the Cathedral's bus fans are
// beam records the page draws (so the haze fluid scatters them), with the scene's own geometry.
function cathedralStrip({ heads = {}, beams = 6, spread = 0.5, pattern = 3, phase = 0.2, count = 5, chordPulse = 0, pads = {} } = {}) {
  const strip = C.createStrip();
  C.stripSet(strip, 12, C.STRIP.ROW_PADS, phase, 0, 0, count);
  C.stripSet(strip, 15, C.STRIP.ROW_PADS, chordPulse, 0, 0, 0.5);
  for (const [i, env] of Object.entries(pads)) C.stripSet(strip, +i, C.STRIP.ROW_PADS, env, 0.8, 0, 0);
  const bus = new Array(24).fill(0);
  bus[1] = pattern; bus[3] = 0.3;
  for (const [i, v] of Object.entries(heads)) bus[4 + +i] = v;
  bus[16] = 0.1; bus[17] = 0.3; bus[18] = 0.9; bus[19] = beams;   // L1 and the beams per fan
  bus[20] = 0.9; bus[21] = 0.2; bus[22] = 0.6; bus[23] = spread;  // L2 and the spread
  H.writeHeadBus(strip, bus, 0);
  C.stripSet(strip, 15, C.STRIP.ROW_PALETTE, C.STRIP.VERSION, 0, 0, 1);
  return strip;
}

test("option C: the Cathedral's lit bus heads become beam records at the scene's own heads, one group per fan", () => {
  const asp = 16 / 9;
  const strip = cathedralStrip({ heads: { 0: 0.8, 5: 1.4, 11: 2.25 } });   // head 1 L1 0.8, head 6 L2 0.4, head 12 white 0.25
  const dst = new Float32Array(L.MAX_SEGMENTS * L.SEG_FLOATS);
  const rows = H.cathedralBeams(strip, { asp }, dst);
  assert.equal(rows, 3 * (6 + 1), "three fans of six beams, each behind its group header");
  const heads = [0, 5, 11];
  for (let f = 0; f < 3; f++) {
    const hdr = L.decodeSeg(dst, f * 7, {});
    assert.ok(hdr.header && hdr.count === 6, "a group header for the fan");
    const h = H.cathedralHead(heads[f], asp);
    assert.ok(Math.abs(hdr.cx - h.x) < 1e-6 && Math.abs(hdr.cy - h.y) < 1e-6, "the group sits at the scene's head");
    for (let j = 1; j <= 6; j++) {
      const r = L.decodeSeg(dst, f * 7 + j, {});
      assert.ok(!r.header && r.kind === L.KIND.BEAM, "a beam: it fades along itself");
      assert.ok(Math.abs(r.x0 - h.x) < 1e-6 && Math.abs(r.y0 - h.y) < 1e-6, "every beam starts at the head");
      const ex = Math.abs(r.x1) - asp / 2, ey = Math.abs(r.y1) - 0.5;
      assert.ok(Math.max(ex, ey) > 0 && Math.max(ex, ey) < 0.03, "and runs just past the frame's edge");
      assert.ok(r.width <= L.CORE_MAX_PX && r.width > 0.5);
      assert.ok(Math.abs(r.glow - r.I * H.CATHEDRAL.GLOW) < 0.002, "the halo at its share of the core's level");
    }
  }
  const lvl = (k) => L.decodeSeg(dst, k * 7 + 1, {}).I;
  assert.ok(Math.abs(lvl(0) - 0.8 * 1.21) < 0.002 && Math.abs(lvl(1) - 0.4 * 1.21) < 0.002 && Math.abs(lvl(2) - 0.25 * 1.21) < 0.002,
    "the scene's fan energy: the bus level x (0.7 + 0.6 x 0.85)");
  const col = (k) => { const r = L.decodeSeg(dst, k * 7 + 1, {}); return [r.r, r.g, r.b].map((v) => +v.toFixed(2)); };
  assert.deepEqual(col(0), [0.1, 0.3, 0.9], "slot 0: L1");
  assert.deepEqual(col(1), [0.9, 0.2, 0.6], "slot 1: L2");
  assert.deepEqual(col(2), [1, 1, 1], "slot 2: white");
  // the spread: the fan's outer beams are the bus's spread apart
  const a = (k) => { const r = L.decodeSeg(dst, k, {}); return Math.atan2(r.y1 - r.y0, r.x1 - r.x0); };
  let d = a(6) - a(1); d -= 2 * Math.PI * Math.round(d / (2 * Math.PI));
  assert.ok(Math.abs(Math.abs(d) - 0.5) < 1e-4, `spread ${d}`);
});

test("option C: a dark bus, an older strip, a pad's own fan, Dampen's gain, Converge, Rain and the row cap", () => {
  const asp = 16 / 9, dst = new Float32Array(L.MAX_SEGMENTS * L.SEG_FLOATS);
  assert.equal(H.cathedralBeams(cathedralStrip(), { asp }, dst), 0, "no head lit: nothing");
  const old = cathedralStrip({ heads: { 0: 0.8 } });
  C.stripSet(old, 15, C.STRIP.ROW_PALETTE, 2, 0, 0, 1);
  assert.equal(H.cathedralBeams(old, { asp }, dst), 0, "a v2 strip has no head bus");
  assert.equal(H.cathedralBeams(cathedralStrip({ heads: { 2: 0.5 }, pads: { 2: 0.7 } }), { asp }, dst), 0,
    "a pad above its head's bus level keeps its own fan in the scene");
  // Dampen: the page scaled the bus by its gain; the records take it back (the beam layer applies the gain itself)
  H.cathedralBeams(cathedralStrip({ heads: { 0: 0.3 } }), { asp, gain: 0.5 }, dst);
  assert.ok(Math.abs(L.decodeSeg(dst, 1, {}).I - 0.6 * 1.21) < 0.002);
  // Converge (pattern 7): every beam's fan centred on the frame's centre; Rain (12): straight down from the top row
  H.cathedralBeams(cathedralStrip({ heads: { 0: 0.8 }, beams: 1, pattern: 7 }), { asp }, dst);
  const h0 = H.cathedralHead(0, asp), r = L.decodeSeg(dst, 0, {});
  const cross = (r.x1 - r.x0) * (0 - h0.y) - (r.y1 - r.y0) * (0 - h0.x);
  assert.ok(Math.abs(cross) < 1e-6 && !r.header, "one beam, no group: through the centre");
  H.cathedralBeams(cathedralStrip({ heads: { 1: 0.8 }, beams: 1, pattern: 12 }), { asp }, dst);
  const rain = L.decodeSeg(dst, 0, {});
  assert.ok(Math.abs(rain.x1 - rain.x0) < 1e-6 && rain.y1 < rain.y0, "Rain: down");
  // the cap: never past maxRows (the hero's rows come after)
  const all = cathedralStrip({ heads: Object.fromEntries(Array.from({ length: 12 }, (_, i) => [i, 0.9])), beams: 12 });
  assert.equal(H.cathedralBeams(all, { asp }, dst), 12 * 13);
  assert.equal(H.cathedralBeams(all, { asp }, dst, 0, 30), 2 * 13, "whole fans only, under the cap");
});

test("option C: the scissor foci and heads are the scene's (the frag's formulas), and the scene no longer draws bus fans", () => {
  const src = readFileSync(here("../arsenal/web/presets/vj-laser-cathedral.frag"), "utf8");
  assert.match(src, /vec2 o = vec2\(\(float\(c\) - 1\.5\) \* 0\.30 \* asp \* 0\.9, 0\.36 - 0\.36 \* float\(r\)\);/, "the heads");
  assert.match(src, /float stepB = gCount \+ smoothstep\(0\.0, 0\.45, gPhase\) \+ 1\.5 \* gChordPulse;/, "the beat step");
  assert.match(src, /vec2 focusA = vec2\(amp \* asp \* 0\.5 \* sin\(stepB \* 1\.5708\), 0\.05 \+ 0\.32 \* cos\(stepB \* 1\.0472\)\);/);
  assert.match(src, /vec2 focusB = vec2\(-focusA\.x, -0\.05 - 0\.3 \* cos\(stepB \* 0\.7854 \+ 1\.0\)\);/);
  assert.match(src, /if \(!fromBus && lv\.x > 0\.002\) \{/, "a bus head's fan is the page's beam layer");
  // the scissor: an even head (c + r even) aims at focus A, an odd one at B
  const asp = 16 / 9, dst = new Float32Array(L.MAX_SEGMENTS * L.SEG_FLOATS);
  const phase = 0.6, count = 9, sweep = 0.55;
  H.cathedralBeams(cathedralStrip({ heads: { 0: 0.8, 1: 0.8 }, beams: 1, phase, count }), { asp, sweep }, dst);
  const stepB = count + 1 + 0;   // smoothstep(0, 0.45, 0.6) = 1
  const amp = 0.15 + 0.55 * sweep;
  const fA = [amp * asp * 0.5 * Math.sin(stepB * 1.5708), 0.05 + 0.32 * Math.cos(stepB * 1.0472)];
  const fB = [-fA[0], -0.05 - 0.3 * Math.cos(stepB * 0.7854 + 1.0)];
  for (const [row, f] of [[0, fA], [1, fB]]) {
    const r = L.decodeSeg(dst, row, {});
    const cross = (r.x1 - r.x0) * (f[1] - r.y0) - (r.y1 - r.y0) * (f[0] - r.x0);
    assert.ok(Math.abs(cross) < 1e-5, `head ${row + 1} aims through its focus`);
  }
});

test("option C: while a gate runs the heads' halos are held through its gaps, only the cores pulse, and the cores are fitted", () => {
  const asp = 16 / 9, dst = new Float32Array(L.MAX_SEGMENTS * L.SEG_FLOATS);
  const heads = new H.CathedralHeads();
  const lit = cathedralStrip({ heads: { 1: 0.9, 2: 1.9, 5: 0.9, 6: 0.9, 9: 0.9, 10: 0.9 }, beams: 12, spread: 0.6 });
  const gap = cathedralStrip({ beams: 12, spread: 0.6 });                       // the same run (solo 0.3), every head dark
  heads.update(lit, { asp }, 1 / 60);
  assert.ok(heads.running && heads.fits === 1);
  assert.ok(heads.coreK < 1 && heads.coreK > 0.05, `six fans of twelve: the cores are fitted (${heads.coreK})`);
  // the fit holds: at the held levels, at every probed step of the foci, the cores stay under the caps
  for (let k = 0; k < 48; k++) {
    const n = H.cathedralBeams(lit, { asp, hold: heads, stepB: k / 2 }, dst);
    const c = H.coreCells(dst, n, asp);
    assert.ok(c.cell <= H.HEAD_HOLD.CELL_CAP + 1e-9 && c.window <= H.HEAD_HOLD.WIN_CAP + 1e-9, `step ${k / 2}: ${c.cell} ${c.window}`);
  }
  const k0 = heads.coreK;
  // a gap: no core, every halo held at its level, in the colour it last drew
  heads.update(gap, { asp }, 1 / 60);
  const n = H.cathedralBeams(gap, { asp, hold: heads }, dst);
  assert.equal(n, 6 * 13, "six held fans");
  for (let i = 0; i < n; i++) {
    const r = L.decodeSeg(dst, i, {});
    if (r.header) continue;
    assert.ok(r.I < 0.002 && Math.abs(r.glow - 0.9 * 1.21 * H.CATHEDRAL.GLOW) < 0.003 && r.held, "the core dark, the halo held");
  }
  assert.deepEqual([0, 1, 2].map((k) => +[L.decodeSeg(dst, 14, {}).r, L.decodeSeg(dst, 14, {}).g, L.decodeSeg(dst, 14, {}).b][k].toFixed(2)), [0.9, 0.2, 0.6],
    "head 3 keeps L2 through the gap");
  assert.equal(heads.coreK, k0, "the fit never gives light back mid-run");
  // the run ends (solo back to 1): the halos let go over RELEASE_S, and the next run fits afresh
  const idle = cathedralStrip();
  C.stripSet(idle, 9, C.STRIP.ROW_PALETTE, 0, 0, 0, 1);
  let frames = 0;
  while (heads.glow.some((g) => g > 0) && frames < 600) { heads.update(idle, { asp }, 1 / 60); frames++; }
  assert.ok(!heads.running && heads.coreK === 1);
  assert.ok(frames > 20 && frames < 240, `released in ${frames} frames`);
  // an older strip: nothing held
  heads.update(lit, { asp }, 1 / 60);
  const old = cathedralStrip({ heads: { 0: 0.8 } });
  C.stripSet(old, 15, C.STRIP.ROW_PALETTE, 2, 0, 0, 1);
  heads.update(old, { asp }, 1 / 60);
  assert.ok(heads.glow.every((g) => g === 0) && heads.coreK === 1);
});

test("coreCells: one beam's core on gate v2's grid -- its light per cell, the brightest window of 16 cells or more", () => {
  const asp = 16 / 9, seg = new Float32Array(2 * L.SEG_FLOATS);
  // a white, cold (heat 0), 2 px core at level 1, straight across the frame's middle row of cells, no fade to speak of
  seg[0] = -asp / 2; seg[1] = 0.0625; seg[2] = asp / 2; seg[3] = 0.0625;
  seg[4] = 255 * 65536 + 255 * 256 + 255;
  seg[5] = Math.round(1 / L.LEVEL_MAX * 4095) * 4096;
  seg[6] = 32;    // width 2 px, heat 0
  const c = H.coreCells(seg, 1, asp);
  // per cell: 2/1080 of a frame height of light, spread over a cell 1/8 tall; the first cell, before the fade
  const first = 2 / 1080 / (1 / 8);
  assert.ok(c.cell > 0.9 * first * Math.exp(-0.5 * asp / 8) && c.cell <= first * 1.0001, `${c.cell} vs ${first}`);
  assert.ok(c.window < c.cell && c.window > 0, "a window averages the row with the dark ones");
});

test("option C: a head the run has left lets its halo go after HOLD_S; the steady picture (the air's source) never pulses", () => {
  const asp = 16 / 9, dst = new Float32Array(L.MAX_SEGMENTS * L.SEG_FLOATS);
  const heads = new H.CathedralHeads();
  const a = cathedralStrip({ heads: { 0: 0.8 } }), b = cathedralStrip({ heads: { 3: 0.8 } }), gap = cathedralStrip();
  heads.update(a, { asp }, 1 / 60);
  const steadyLevels = [];
  // the run moves on to head 4 every beat (eighth-note pulses, two frames lit of fifteen); head 1 is never lit again
  for (let f = 1; f < 120; f++) {
    const s = f % 15 < 2 ? b : gap;
    heads.update(s, { asp }, 1 / 60);
    const n = H.cathedralBeams(s, { asp, hold: heads, steady: true }, dst);
    let I4 = 0;
    for (let i = 0; i < n; i++) { const r = L.decodeSeg(dst, i, {}); if (!r.header && Math.abs(r.x0 - H.cathedralHead(3, asp).x) < 1e-6) I4 = Math.max(I4, r.I); }
    if (f > 20) steadyLevels.push(I4);
  }
  assert.ok(heads.running);
  assert.ok(heads.glow[0] < 0.05, `head 1, left 2 s ago (held 0.75 s, then falling), has nearly let go: ${heads.glow[0]}`);
  assert.ok(heads.glow[3] > 0.79, "head 4, pulsed every quarter second, is held");
  assert.ok(heads.peak[0] > 0.79, "the fit still counts every head lit in this run");
  const lo = Math.min(...steadyLevels), hi = Math.max(...steadyLevels);
  assert.ok(lo > 0 && hi - lo < 1e-6, `the steady picture's core stays put through the pulses (${lo}..${hi})`);
});
