// The piano plays the lighting (arsenal/web/stage/piano.js): node --test tests/stage_piano.test.mjs
// Daniel, 2026-11-02: "Any ideas how we can marry what we have built with the piano visualizer and our new lightshow rig?
// ... then lets build it, we have 20m, so go crazy." The mapping is pure, so the whole thing is pinned here without a
// page: the toggle (default OFF), velocity -> the hit's intensity, the pedal -> the air and the bloom with the F5 fader
// as the ceiling, the held register -> the camera's own presets, the chord quality -> a palette FAMILY (never a colour),
// and the two rules the layer must never break: a repeated stop is never asked twice, and a family the library does not
// have changes nothing.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { PIANO_API, PIANO_KEY, PIANO_CFG, parsePiano, levelOfVel, intensityOf, hitOf, pedalHaze, pedalBloom,
         heldRegister, registerStop, qualityClass, familyLadder, pickFamily, resolveFamily, emptyState, pianoStep, pianoTick,
         pianoStatus, FAMILY_LADDER, clamp01 } from "../arsenal/web/stage/piano.js";
import { KICK_DEFAULTS, intensityOf as kickIntensity } from "../arsenal/web/stage/kick.js";

const CFG = PIANO_CFG;
// kick.js's own arithmetic, called directly: Kicks.levelOfVel is `clamp01(a + (b - a) * clamp01(vel))` over the config's
// from_velocity, and intensityOf(every kick's config, the level) is what the lit fixture actually shows.
const KICK_CFG = { level: KICK_DEFAULTS.level };
const kickLevel = (vel) => { const [a, b] = KICK_DEFAULTS.level.from_velocity; return clamp01(a + (b - a) * clamp01(vel)); };
const ctx = (over = {}) => ({ nowMs: 0, pos: 0, faderHaze: 0.85, bloomBase: 0.05, families: ["violet", "blue", "warm", "green", "pink", "neutral"], ...over });
const on = (over = {}) => emptyState({ on: true, ...over });
const note = (key, vel = 0.8, up = false) => ({ t: "note", key, vel, on: !up });
const run = (state, evs, c = ctx()) => { let s = state, out = []; for (const [i, ev] of evs.entries()) { const r = pianoStep(s, ev, c); s = r.state; out.push(...r.deltas); } return { state: s, deltas: out }; };

test("the toggle: ?piano=1 is ON and everything else is OFF (default OFF, every existing show unchanged)", () => {
  assert.equal(PIANO_API, "arsenal.stage-piano/v1");
  assert.deepEqual(parsePiano("?piano=1"), { on: true, asked: "1" });
  assert.equal(parsePiano("piano=on").on, true);
  assert.equal(parsePiano("?piano=yes").on, true);
  assert.equal(parsePiano("?piano=Y").on, true);
  for (const q of ["", "?", "?piano=0", "?piano=off", "?piano=false", "?pianox=1", "?demo=1", "?piano=maybe"]) assert.equal(parsePiano(q).on, false, q);
  assert.equal(parsePiano(null).on, false);
  assert.equal(parsePiano(new URLSearchParams("?piano=1")).on, true);
  // and the reducer is inert until the page turns it on
  const r = pianoStep(emptyState(), note(60, 1), ctx());
  assert.deepEqual(r.deltas, []);
  assert.equal(r.state.on, false);
});

test("velocity -> the note's light hit: the same level/intensity kick.js gives a pad at that velocity", () => {
  // the defaults MIRROR kick.js KICK_DEFAULTS.level (from_velocity [0,1], floor 0.5, gamma 0.5) -- pinned against the
  // real module, so the piano cannot quietly drift from what the pads do
  assert.deepEqual([...CFG.level_from_velocity], [...KICK_DEFAULTS.level.from_velocity]);
  assert.equal(CFG.intensity_floor, KICK_DEFAULTS.level.floor);
  assert.equal(CFG.intensity_gamma, KICK_DEFAULTS.level.gamma);
  for (const vel of [0, 0.25, 0.5, 0.75, 1]) {
    const lvl = levelOfVel(vel);
    assert.equal(lvl, kickLevel(vel), `level ${vel}`);
    assert.ok(Math.abs(intensityOf(lvl) - kickIntensity(KICK_CFG, lvl)) < 1e-12, `intensity ${vel}`);
  }
  // monotonic, and the floor: the softest note is still half a light
  let prev = -1;
  for (let v = 0; v <= 1.0001; v += 0.05) { const i = intensityOf(levelOfVel(v)); assert.ok(i >= prev - 1e-12); prev = i; }
  assert.equal(intensityOf(levelOfVel(0)), 0.5);
  assert.equal(intensityOf(levelOfVel(1)), 1);
  // a note-on -> one hit; a note-off, garbage, or a non-note -> none
  const h = hitOf(note(60, 0.9));
  assert.equal(h.type, "hit");
  assert.equal(h.kind, CFG.hit_kind);
  assert.equal(h.key, 60);
  assert.ok(Math.abs(h.level - 0.9) < 1e-12);
  assert.ok(Math.abs(h.intensity - (0.5 + 0.5 * Math.sqrt(0.9))) < 1e-12);
  assert.equal(hitOf(note(60, 0.9, true)), null);
  assert.equal(hitOf(note(200, 0.9)), null);
  assert.equal(hitOf({ t: "energy", level: 1 }), null);
  assert.equal(hitOf(null), null);
});

test("a note played is a hit, once per press: the gap swallows a bounced key, a re-press is a new hit", () => {
  const c = ctx({ nowMs: 1000 });
  const r = run(on(), [note(60, 0.8)], c);
  assert.equal(r.deltas.length, 1);
  assert.equal(r.deltas[0].type, "hit");
  // the same key 5 ms later (a bounce or a doubled message) is not a second hit
  const r2 = pianoStep(r.state, note(60, 0.8), ctx({ nowMs: 1005 }));
  assert.deepEqual(r2.deltas.filter((d) => d.type === "hit"), []);
  // past the gap it is a new hit
  const r3 = pianoStep(r2.state, note(60, 0.8), ctx({ nowMs: 1000 + CFG.hit_gap_ms + 1 }));
  assert.equal(r3.deltas.filter((d) => d.type === "hit").length, 1);
  // a chord rolled up: three notes, three hits, and the register is all three
  const r4 = run(on(), [note(60), note(64), note(67)]);
  assert.equal(r4.deltas.filter((d) => d.type === "hit").length, 3);
  assert.deepEqual(r4.state.reg, { low: 60, high: 67, mid: 63.5, count: 3 });
});

test("the pedal: the air and the bloom held while it is down, and the F5 fader stays the CEILING", () => {
  for (const f of [0, 0.2, 0.5, 0.85, 1]) {
    assert.equal(pedalHaze(f, true), f);                     // down: exactly the fader, never past it
    assert.ok(pedalHaze(f, false) <= f + 1e-12);             // up: the fader's own value times the floor
    assert.ok(pedalHaze(f, false) <= pedalHaze(f, true) + 1e-12);
  }
  assert.equal(pedalHaze(0.85, false), 0.85 * CFG.haze_floor);
  assert.equal(pedalHaze(0, true), 0);                       // the fader at zero: the pedal cannot make air
  // the bloom: the base plus the add, capped (the base is stage.js BLOOM_MIX, itself ?bloommix=)
  assert.equal(pedalBloom(0.05, false), 0.05);
  assert.equal(pedalBloom(0.05, true), 0.05 + CFG.bloom_add);
  assert.ok(pedalBloom(0.9, true) <= CFG.bloom_cap + 1e-12);
  assert.ok(pedalBloom(1, true) <= 1);
  // a pedal event is one delta, and only on a CHANGE
  const r = run(on(), [{ t: "pedal", on: true }, { t: "pedal", on: true }]);
  assert.equal(r.deltas.length, 1);
  assert.deepEqual(r.deltas[0], { type: "pedal", on: true, haze: 0.85, bloom: 0.05 + CFG.bloom_add });
  const up = pianoStep(r.state, { t: "pedal", on: false }, ctx());
  assert.equal(up.deltas[0].haze, 0.85 * CFG.haze_floor);
  assert.equal(up.deltas[0].bloom, 0.05);
});

test("the register -> the camera's own presets, and it must HOLD before the camera is asked to move", () => {
  // the bands: under 48 far, 48..71 medium, 72 and up close
  assert.equal(registerStop(null), "auto");
  assert.equal(registerStop({ mid: 40 }), "far");
  assert.equal(registerStop({ mid: 47.9 }), "far");
  assert.equal(registerStop({ mid: 48 }), "medium");
  assert.equal(registerStop({ mid: 71 }), "medium");
  assert.equal(registerStop({ mid: 72 }), "close");
  assert.equal(registerStop({ mid: 96 }), "close");
  // one note is its own register
  assert.deepEqual(heldRegister({ 55: 0.8 }), { low: 55, high: 55, mid: 55, count: 1 });
  assert.equal(heldRegister({}), null);
  assert.equal(heldRegister(), null);
  // low held -> far, but only after the hold; before it nothing is asked
  let s = on(), r = pianoStep(s, note(40, 0.9), ctx({ nowMs: 0 }));
  assert.equal(r.deltas.filter((d) => d.type === "distance").length, 0);
  assert.deepEqual(r.state.cand, { stop: "far", since: 0 });
  // the hold expires with no further event: the frame's tick lands it (stage.js calls pianoTick every frame)
  const t = pianoTick(r.state, ctx({ nowMs: CFG.distance_hold_ms - 1 }));
  assert.deepEqual(t.deltas, []);
  const t2 = pianoTick(t.state, ctx({ nowMs: CFG.distance_hold_ms }));
  assert.deepEqual(t2.deltas, [{ type: "distance", stop: "far" }]);
  // and the same stop is never asked twice (distance.js would hand the camera BACK on a repeated press)
  const t3 = pianoTick(t2.state, ctx({ nowMs: 9999 }));
  assert.deepEqual(t3.deltas, []);
  // a rolled chord upward does not walk the camera: the candidate is replaced, not issued
  const roll = run(on(), [note(48, 0.8), note(60, 0.8), note(72, 0.8)]);
  assert.equal(roll.deltas.filter((d) => d.type === "distance").length, 0);
  assert.equal(roll.state.cand.stop, "medium");              // mid of 48..72 = 60
  // letting go hands the camera back to the director, through the same hold
  const rel = run(on({ stop: "far" }), [note(40), note(40, 0, true)]);
  assert.equal(rel.state.stop, "far");
  const back = pianoTick(rel.state, ctx({ nowMs: 0 }));
  const back2 = pianoTick(back.state, ctx({ nowMs: CFG.distance_hold_ms }));
  assert.deepEqual(back2.deltas, [{ type: "distance", stop: "auto" }]);
});

test("the chord quality names a FAMILY, never a colour -- and only families the library actually has", () => {
  // the engine's own spellings (vj.py's qualities, chordsense's and theory's)
  const cases = { maj: "major", "": "unknown", N: "unknown", maj7: "major", 6: "major", m: "minor", m7: "minor", m9: "minor",
                  min: "minor", m6: "minor", sus2: "shimmer", sus4: "shimmer", add9: "shimmer", madd9: "shimmer", "7sus4": "shimmer",
                  dim: "tension", dim7: "tension", aug: "tension", m7b5: "tension", "5": "major", "7": "major", "9": "major" };
  for (const [q, cls] of Object.entries(cases)) assert.equal(qualityClass(q), cls, q);
  assert.equal(qualityClass(undefined), "unknown");
  // the four ladders are families only -- no hex, no "#", no colour word anywhere
  assert.deepEqual(Object.keys(FAMILY_LADDER).sort(), ["major", "minor", "shimmer", "tension"]);
  for (const l of Object.values(FAMILY_LADDER)) for (const f of l) assert.match(f, /^[a-z]+$/);
  assert.deepEqual([...familyLadder("major")], ["warm", "green", "violet"]);
  assert.equal(familyLadder("unknown"), null);
  // picking: the first family of the ladder the library has; none -> null (nothing changes, no invented colour)
  const have = ["violet", "blue", "pink", "neutral"];
  assert.equal(pickFamily("major", have), "violet");        // warm and green are not loaded
  assert.equal(pickFamily("minor", have), "blue");
  assert.equal(pickFamily("shimmer", have), "violet");
  assert.equal(pickFamily("tension", have), "pink");
  assert.equal(pickFamily("major", ["blue"]), null);        // a library with none of the ladder: no change
  assert.equal(pickFamily("unknown", have), null);
  assert.equal(pickFamily("major", null), null);
  // the library's own families are the ones the real palettes.json declares (the page passes exactly these)
  const lib = JSON.parse(readFileSync(new URL("../arsenal/web/palettes.json", import.meta.url), "utf8"));
  const fams = [...new Set(lib.palettes.map((p) => p.family))];
  for (const f of fams) assert.match(f, /^[a-z]+$/, f);
  for (const cls of Object.keys(FAMILY_LADDER)) assert.ok(pickFamily(cls, fams), `${cls} resolves against the real library`);
  // resolving a family to a palette: the family's first id, its next one when that is already showing, else null
  const list = [{ id: "a", family: "warm" }, { id: "b", family: "blue" }, { id: "c", family: "warm" }];
  assert.equal(resolveFamily(list, "warm"), "a");
  assert.equal(resolveFamily(list, "warm", "a"), "c");
  assert.equal(resolveFamily(list, "blue", "b"), "b");
  assert.equal(resolveFamily(list, "green"), null);
  assert.equal(resolveFamily(null, "warm"), null);
});

test("a chord change lands a family on the NEXT BEAT LINE, rate-limited, and the audio's ear never drives it", () => {
  const c = ctx({ pos: 12.4 });
  const r = pianoStep(on(), { t: "chord", src: "keys", quality: "m9" }, c);
  assert.deepEqual(r.deltas, [{ type: "family", cls: "minor", family: "blue", at: 13 }]);
  assert.equal(r.state.family, "blue");
  // a second chord of the same class: no delta
  const r2 = pianoStep(r.state, { t: "chord", src: "keys", quality: "m7" }, c);
  assert.deepEqual(r2.deltas, []);
  // a class that resolves to the SAME family (major -> violet when warm/green are missing): no delta either
  const few = ctx({ pos: 20.4, families: ["violet"] });
  const maj = pianoStep(on(), { t: "chord", src: "keys", quality: "maj7" }, few);
  const shim = pianoStep(maj.state, { t: "chord", src: "keys", quality: "sus4" }, few);
  assert.equal(maj.deltas[0].family, "violet");
  assert.deepEqual(shim.deltas, []);
  // a real class change too soon after the last landing waits (the next chord that falls late enough lands)
  const soon = pianoStep(r.state, { t: "chord", src: "keys", quality: "sus2" }, ctx({ pos: 13.5, families: c.families }));
  assert.deepEqual(soon.deltas, []);
  const later = pianoStep(soon.state, { t: "chord", src: "keys", quality: "dim" }, ctx({ pos: 15.5 }));
  assert.equal(later.deltas.length, 1);
  assert.equal(later.deltas[0].family, "pink");
  assert.equal(later.deltas[0].at, 16);
  // the AUDIO's chords are not this layer's business (they would double the reading of the same chord)
  const audio = pianoStep(on(), { t: "chord", src: "audio", quality: "maj7" }, ctx({ pos: 0 }));
  assert.deepEqual(audio.deltas, []);
  assert.equal(audio.state.cls, null);
});

test("a stuck key-up cannot leak the held map, and the status is the page's whole story", () => {
  let s = on();
  for (let i = 0; i < CFG.held_max + 8; i++) s = pianoStep(s, note(20 + i, 0.5), ctx({ nowMs: i * 100 })).state;
  assert.ok(Object.keys(s.keys).length <= CFG.held_max);
  assert.ok(s.reg.low >= 20);
  // status: with the toggle off nothing is claimed as changed
  const off = pianoStatus(emptyState(), { faderHaze: 0.85, bloomBase: 0.05 });
  assert.equal(off.on, false);
  assert.equal(off.haze, 0.85);
  assert.equal(off.bloom, 0.05);
  const st = pianoStatus(on({ pedal: true, stop: "close", family: "blue" }), { faderHaze: 0.6, bloomBase: 0.05 });
  assert.deepEqual([st.on, st.pedal, st.stop, st.family, st.haze, st.bloom], [true, true, "close", "blue", 0.6, 0.05 + CFG.bloom_add]);
  // the key the page binds the live toggle to
  assert.equal(PIANO_KEY, "KeyY");
});
