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
