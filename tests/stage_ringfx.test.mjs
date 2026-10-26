// Virtual Stage v1: the ring-effect library and the effects engine's v1 additions (arsenal/web/stage/effects.js and the
// set's effects table). node --test tests/stage_ringfx.test.mjs
//
// Daniel, 2026-10-25: "The effects they had on the rings also looked sick!" The study lane measured the chopper (two
// opposite lit arcs, about 0.9 turns a beat, counter-clockwise from the crowd) and a pink/blue colour bump once a beat.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { spreadValues, waveform, EffectInstance, ORDERS, FORMS } from "../arsenal/web/stage/effects.js";
import { BeatGrid } from "../arsenal/web/stage/grid.js";
import { Programmer } from "../arsenal/web/stage/programmer.js";
import { hexToLinear } from "../arsenal/web/stage/lasers.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const THEME = { name: "source-violet", ...SCENE.themes["source-violet"] };
const close = (a, b, eps, msg = "") => assert.ok(Math.abs(a - b) <= eps, `${msg} ${a} != ${b} (eps ${eps})`);
const FPS = 60, FB = 150 / 60 / FPS;

test("the v1 orders and forms are known; block 'ties' gives equal keys one slot", () => {
  for (const o of ["clock", "level", "level_mirror", "column", "depth", "spiral"]) assert.ok(ORDERS.includes(o));
  assert.ok(FORMS.includes("sparkle"));
  const keys = { level: Float64Array.from([0, 0, 1, 2, 2, 1, 0]), index: Float64Array.from([0, 1, 2, 3, 4, 5, 6]) };
  const v = Array.from(spreadValues(keys, { order: "level", block: "ties", from: 0, to: -360, cyclic: true }, 7));
  assert.deepEqual(v, [0, 0, -120, -240, -240, -120, 0]);
  const m = { level_mirror: Float64Array.from([0, 1, 0, 1]) };
  assert.deepEqual(Array.from(spreadValues(m, { order: "level_mirror", block: "ties", from: 0, to: -360, cyclic: true }, 4)), [0, -180, 0, -180]);
});

test("an anchored effect starts its cycle on the cue's ONE whatever the grid's phase, and ignores the speed fader", () => {
  const g = RIG.groups["halo.top"];
  const def = { attrs: ["Dimmer"], mode: "absolute", form: "square", width: 0.3333, measure: 3, phase: { order: "index", from: 0, to: 0 } };
  for (const anchor of [61, 62.5, 100]) {
    const e = new EffectInstance("t", def, g, { anchorPos: anchor, speed: 2, pos: anchor });
    e.tick(anchor, 0);
    assert.ok(e.value(0) > 0.99, `lit on its ONE (anchor ${anchor})`);
    e.tick(anchor + 1.5, 0);
    assert.equal(e.value(0), 0, "dark a beat and a half later (the speed fader would have doubled it)");
    e.tick(anchor + 3, 0);
    assert.ok(e.value(0) > 0.99, "lit again three beats on");
  }
});

test("one-shots hold their first value before the delay and their last after the shots; clean starts stay dark until their onset", () => {
  const g = RIG.groups.hrow;
  const e = new EffectInstance("p", { attrs: ["Pan"], mode: "relative", form: "rampUp", size: 40, measure: 2, shots: 1, delay: 1, phase: { order: "x", from: 0, to: 0 } }, g, { anchorPos: 10, pos: 10 });
  const at = (p) => { e.tick(p, 0); return e.apply("Pan", 0, 0); };
  close(at(10), -40, 1e-6); close(at(10.9), -40, 1e-6); close(at(12), 0, 1e-3); close(at(12.99), 39.6, 0.1); close(at(14), 40, 1e-6); close(at(20), 40, 1e-6);
  const c = new EffectInstance("c", { attrs: ["Dimmer"], mode: "absolute", form: "square", width: 0.5, measure: 2, clean: true, phase: { order: "index", from: 0, to: -180, cyclic: true } }, RIG.groups["vert.v1"], { anchorPos: 0, pos: 0 });
  c.tick(0, 0);
  assert.ok(c.value(0) > 0.9, "the first member lights on the ONE");
  assert.equal(c.value(c.group.n - 1), 0, "a later member is dark before its own onset (no tail of a cycle that never ran)");
});

test("sparkle: a seeded subset per cycle, the same on every run; by_phase shares one draw per block", () => {
  const p = { seed: 5, density: 0.3, width: 0.9, transition: 0 };
  const draws = Array.from({ length: 400 }, (_, m) => waveform("sparkle", 0.4, { ...p, member: m }));
  const lit = draws.filter((v) => v > 0).length / draws.length;
  assert.ok(lit > 0.2 && lit < 0.4, `density ${lit}`);
  assert.deepEqual(draws, Array.from({ length: 400 }, (_, m) => waveform("sparkle", 0.4, { ...p, member: m })));
  assert.notDeepEqual(draws, Array.from({ length: 400 }, (_, m) => waveform("sparkle", 1.4, { ...p, member: m })), "a new subset next cycle");
  const g = RIG.groups["rings.slats"];
  const e = new EffectInstance("hold", RIG.effects["ring-segment-hold"], g, { pos: 0 });
  e.tick(0, 0);
  const vals = Array.from({ length: g.n }, (_, m) => e.value(m));
  const byPhase = new Map();
  for (let m = 0; m < g.n; m++) { const k = e.phase[m].toFixed(6); if (!byPhase.has(k)) byPhase.set(k, new Set()); byPhase.get(k).add(vals[m]); }
  assert.ok([...byPhase.values()].every((s) => s.size === 1), "every block holds one value");
  assert.ok(vals.some((v) => v > 0) && vals.some((v) => v === 0), "some arcs held, some dark");
});

// The ring cells' dimmers over time from the programmer (the FrameState), with one effect on the rings.
function ringRun(effectName, { beats = 8, group = "rings.r0.slats", values = { Dimmer: 0.9, Color: "W", Color2: "A" }, with: over = {} } = {}) {
  const grid = new BeatGrid({ bpm: 150, t0: 0 });
  grid.beat({ due_ms: 0, bpm: 150, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
  const prog = new Programmer(RIG, { theme: THEME });
  prog.setLook("drop", 0, { fade: 0 });
  const g = RIG.groups[group];
  const def = { ...RIG.effects[effectName], ...over, phase: { ...RIG.effects[effectName].phase, ...(over.phase || {}) } };
  prog.setOverlay([{ g, kind: "cells", values, positions: null, effects: [{ id: `t:${effectName}`, name: effectName, def }], fade: 0, flash: null }], 0);
  const frames = [];
  for (let f = 0; f <= Math.round(beats / FB); f++) {
    prog.tick(grid, (f * 1000) / FPS, 1 / FPS);
    frames.push({ pos: grid.posAt((f * 1000) / FPS), dim: Array.from(g.members, (c) => prog.pixels[c * 4 + 3]),
                  rgb: Array.from(g.members, (c) => [prog.pixels[c * 4], prog.pixels[c * 4 + 1], prog.pixels[c * 4 + 2]]) });
  }
  return { g, frames };
}
// the n-th circular harmonic of the lit part (above the floor) and its phase
function harmonic(dims, angles, n) {
  const lo = Math.min(...dims);
  let re = 0, im = 0, w = 0;
  for (let k = 0; k < dims.length; k++) { const d = dims[k] - lo; re += d * Math.cos(n * angles[k]); im += d * Math.sin(n * angles[k]); w += d; }
  return { amp: w > 0 ? Math.hypot(re, im) / w : 0, phase: Math.atan2(im, re) };
}

test("target 4 (FrameState): the chopper is two opposite blades (2nd harmonic >= 0.6), 1 turn a beat, counter-clockwise from the crowd by default", () => {
  for (const [to, wantSign] of [[-720, 1], [720, -1]]) {
    const { g, frames } = ringRun("ring-chopper", { beats: 6, with: { phase: { to } } });
    const ang = Array.from(g.keys.angle);
    const h2 = frames.map((f) => harmonic(f.dim, ang, 2)), h1 = frames.map((f) => harmonic(f.dim, ang, 1));
    const a2 = h2.reduce((s, h) => s + h.amp, 0) / h2.length, a1 = h1.reduce((s, h) => s + h.amp, 0) / h1.length;
    assert.ok(a2 >= 0.6 && a2 > a1, `second harmonic ${a2.toFixed(3)}, first ${a1.toFixed(3)}`);
    // the blade angle = phase / 2 (mod 180), unwrapped; a linear fit gives the rate
    const ang2 = [h2[0].phase / 2];
    for (let i = 1; i < h2.length; i++) {
      let d = h2[i].phase / 2 - h2[i - 1].phase / 2;
      while (d > Math.PI / 2) d -= Math.PI; while (d < -Math.PI / 2) d += Math.PI;
      ang2.push(ang2.at(-1) + d);
    }
    const xs = frames.map((f) => f.pos), n = xs.length;
    const mx = xs.reduce((a, b) => a + b) / n, my = ang2.reduce((a, b) => a + b) / n;
    let sxy = 0, sxx = 0;
    for (let i = 0; i < n; i++) { sxy += (xs[i] - mx) * (ang2[i] - my); sxx += (xs[i] - mx) ** 2; }
    const slope = sxy / sxx;                                // radians per beat
    const turns = slope / (2 * Math.PI);
    assert.ok(Math.abs(Math.abs(turns) - 1) <= 0.05, `rate ${turns.toFixed(3)} turns a beat`);
    assert.equal(Math.sign(turns), wantSign, `direction for to ${to} (polar angle grows counter-clockwise seen from the crowd)`);
    const within = ang2.filter((a, i) => Math.abs(a - (my + slope * (xs[i] - mx))) <= (30 * Math.PI) / 180).length / n;
    assert.ok(within >= 0.9, `${(within * 100).toFixed(1)} % of frames within 30 degrees of the fit`);
  }
});

test("target 5 (FrameState): the colour bump swaps the bump colours once a beat (pink from the off-beat) and moves the slats' luminance 3 % or less", () => {
  const { g, frames } = ringRun("ring-colour-bump", { beats: 8, group: "rings.slats", values: { Dimmer: 0.35, Color: "bumpA", Color2: "bumpB" } });
  const Y = frames.map((f) => f.rgb.reduce((s, c) => s + 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2], 0) / f.rgb.length);
  const mean = Y.reduce((a, b) => a + b) / Y.length;
  const swing = (Math.max(...Y) - Math.min(...Y)) / mean;
  assert.ok(swing <= 0.03, `luminance swing ${(swing * 100).toFixed(2)} %`);
  // the mix (pink share) per frame: its strongest period over 0.5-3 beats
  const pinkRGB = hexToLinear(THEME.bumpB), blueRGB = hexToLinear(THEME.bumpA);
  const share = frames.map((f) => { const c = f.rgb[0]; const s = c[0] + c[1] + c[2]; return (c[0] / s - blueRGB[0] / (blueRGB[0] + blueRGB[1] + blueRGB[2])) / (pinkRGB[0] / (pinkRGB[0] + pinkRGB[1] + pinkRGB[2]) - blueRGB[0] / (blueRGB[0] + blueRGB[1] + blueRGB[2])); });
  let best = 0, bestP = 0;
  for (let P = 0.5; P <= 3.0001; P += 0.01) {
    let re = 0, im = 0;
    frames.forEach((f, i) => { re += share[i] * Math.cos((2 * Math.PI * f.pos) / P); im += share[i] * Math.sin((2 * Math.PI * f.pos) / P); });
    const a = Math.hypot(re, im);
    if (a > best) { best = a; bestP = P; }
  }
  assert.ok(Math.abs(bestP - 1) <= 0.05, `the bump's period is ${bestP.toFixed(2)} beats`);
  const at = (pos) => share[frames.findIndex((f) => f.pos >= pos - 1e-9)];
  assert.ok(at(2.25) < 0.2 && at(2.75) > 0.8, "blue just after the kick, pink from the off-beat into the next kick");
  // luminance-matched: OKLab L within 0.03 (the set's bump colours)
  const L = (hex) => { const [r, gg, b] = hexToLinear(hex); const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * gg + 0.0514459929 * b), m = Math.cbrt(0.2119034982 * r + 0.6806995451 * gg + 0.1073969566 * b), s = Math.cbrt(0.0883024619 * r + 0.2817188376 * gg + 0.6299787005 * b); return 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s; };
  assert.ok(Math.abs(L(THEME.bumpA) - L(THEME.bumpB)) <= 0.03);
});

test("the ring-effect library: every effect runs on the rings, stays in 0..1, moves on the beat clock and repeats with its measure", () => {
  const lib = SCENE.ring_fx.effects;
  assert.ok(lib.length >= 12);
  for (const name of lib) {
    assert.ok(RIG.effects[name], name);
    const def = RIG.effects[name];
    const isMix = (def.attrs || []).includes("ColorMix");
    const { frames } = ringRun(name, { beats: 9, group: "rings.slats", values: { Dimmer: 0.8, Color: "A", Color2: "B" } });
    const read = (f) => (isMix ? f.rgb.map((c) => c[0] - c[2]) : f.dim);
    for (const f of frames) for (const v of f.dim) assert.ok(v >= -1e-9 && v <= 1 + 1e-9, `${name} out of range ${v}`);
    if (name === "ring-segment-hold") {
      const a = read(frames[3]), b = read(frames.at(-1));
      assert.deepEqual(a.map((v) => +v.toFixed(5)), b.map((v) => +v.toFixed(5)), "a held mask holds");
      assert.ok(new Set(a.map((v) => v.toFixed(3))).size > 1, "and it is a mask, not a flat level");
      continue;
    }
    const spread = (f) => { const r = read(f); return Math.max(...r) - Math.min(...r); };
    const moving = frames.some((f, i) => i > 0 && read(f).some((v, k) => Math.abs(v - read(frames[i - 1])[k]) > 1e-4));
    assert.ok(moving, `${name} moves`);
    // (the colour bump is unison by design: the whole ring swaps; the shimmer is a 4 % breath)
    if (name !== "ring-shimmer" && name !== "ring-colour-bump") assert.ok(frames.some((f) => spread(f) > 0.05), `${name} is a pattern across the cells`);
    // beat-locked: one measure later (whole frames: measures of 0.5, 1, 2, 3, 4, 8 beats) the cells read the same, except
    // the sparkle, which deals a new subset each cycle
    const m = def.measure;
    if (name === "ring-sparkle" || !(m <= 4)) continue;
    const step = Math.round(m / FB);
    const a = read(frames[24]), b = read(frames[24 + step]);
    const diff = Math.max(...a.map((v, k) => Math.abs(v - b[k])));
    assert.ok(diff < 0.02, `${name}: one measure (${m} beats) later the cells differ by ${diff.toFixed(4)}`);
  }
});
