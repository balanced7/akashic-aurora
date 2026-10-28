// Virtual Stage, KICK v2 (arsenal/web/stage/kick.js through programmer.js). node --test tests/stage_kick.test.mjs
//
// Daniel, 2026-10-27, on the phone bar: "Hitting kick sometimes had an impact at other times nothing changed"; then "Can
// we make kick trigger different rows of lights and or lasers with a peak in brightness or a row turning on and panning,
// it could be also lit for duration of press and on keylab velocity can change parameters too"; then "lets make it a
// vertically longer button that presses and holds the light while the finger is on it and you can sweep up and down to
// adjust brightness! Lets have two kick buttons with vertical "velocity" one kick for white one kick for color, you can
// press both at same time and two rows can light up at once!"; and after trying it, "The kick buttons dont really change
// anything.  Can we make the kick buttons override existing scene lights and cause them to change color with a high
// intensity".
//
// Round 2's acceptance is the SCREEN (arsenal/lanes/stage_verify.mjs, phase kickpix: the share of an 832 x 384 frame whose
// colour moves by more than dE76 10). These node tests pin the logic under it: the deck of areas, the override, the colours,
// the level curve, hold = gate and the re-strike, the wheel's red-free way, the strobe and the flash budget.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { expandScene } from "../arsenal/web/stage/rig.js";
import { Programmer, H, HEAD_FLOATS, ROLE_NAMES } from "../arsenal/web/stage/programmer.js";
import { BeatGrid } from "../arsenal/web/stage/grid.js";
import { FrameLimiter } from "../arsenal/web/stage/flash.js";
import { isSaturatedRed } from "../arsenal/web/stage/lasers.js";
import * as KICK from "../arsenal/web/stage/kick.js";

const SCENE1 = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const SCENE0 = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v0.json", import.meta.url), "utf8"));
const RIG1 = expandScene(SCENE1);
const RIG0 = expandScene(SCENE0);
const THEME1 = { name: "source-violet", ...SCENE1.themes["source-violet"] };
const THEME0 = { name: "source-violet", ...SCENE0.themes["source-violet"] };
const FPS = 60, DT = 1 / FPS;
const W = "kick-white", C = "kick-colour";

function locked(bpm) {
  const g = new BeatGrid({ bpm, t0: 0 });
  g.beat({ due_ms: 0, bpm, n: 0, conf: 1, bar: 1, ver: 0 }, 0);
  return g;
}
function fresh({ rig = RIG1, theme = THEME1, look = "drop", seed = 7 } = {}) {
  const p = new Programmer(rig, { theme, seed });
  p.setLook(look, 0);
  return p;
}
// tick a programmer from beat a to beat b (60 fps) on grid g, calling each(pos, t) before every tick
function play(p, g, a, b, each = null) {
  for (let t = a * g.period; t < b * g.period; t += 1000 / FPS) {
    const pos = g.posAt(t);
    if (each) each(pos, t);
    p.tick(g, t, DT);
  }
}
const cardIx = (name) => KICK.kickConfig(RIG1).cards.findIndex((c) => c.name === name);
const force = (p, name) => { const i = cardIx(name); assert.ok(i >= 0, `the deck has ${name}`); p.kick.deck.forceNext = i; };
// the light a member emits as the programmer hands it to the renderer (linear RGB x level)
const emitted = (p, kind, i) => (kind === "h" ? [p.heads[i * HEAD_FLOATS + H.R] * p.heads[i * HEAD_FLOATS + H.DIM], p.heads[i * HEAD_FLOATS + H.G] * p.heads[i * HEAD_FLOATS + H.DIM], p.heads[i * HEAD_FLOATS + H.B] * p.heads[i * HEAD_FLOATS + H.DIM]]
  : [p.pixels[i * 4], p.pixels[i * 4 + 1], p.pixels[i * 4 + 2]]);
const levelOf = (p, kind, i) => (kind === "h" ? p.heads[i * HEAD_FLOATS + H.DIM] : p.pixels[i * 4 + 3]);
const members = (card) => [...Array.from(card.heads, (i) => ["h", i]), ...Array.from(card.cells, (c) => ["c", c])];
const areaLevel = (p, card) => { const ms = members(card); return ms.reduce((s, [k, i]) => s + levelOf(p, k, i), 0) / ms.length; };
const colourOf = (p, kind, i) => { const e = emitted(p, kind, i), l = levelOf(p, kind, i); return l > 1e-4 ? e.map((x) => x / l) : [0, 0, 0]; };
// share of an area's members whose emitted light differs by more than dE76 de between two programmers
const changedShare = (pA, pB, card, de = 10) => { const ms = members(card); return ms.filter(([k, i]) => KICK.deltaE(emitted(pA, k, i), emitted(pB, k, i)) > de).length / ms.length; };

// ---------------------------------------------------------------------------------------------------- the deck --
test("the deck deals AREAS, big and disjoint; seeded and deterministic, never the same area twice running for a button, never one area twice in a round", () => {
  const cfg = KICK.kickConfig(RIG1);
  assert.deepEqual(cfg.cards.map((c) => c.name), ["rings", "beams", "halo", "strand"]);
  for (const c of cfg.cards) assert.ok(c.heads.length + c.cells.length >= 16, `${c.name}: ${c.heads.length} heads, ${c.cells.length} cells`);
  const deal = (seed) => {
    const g = locked(150), p = fresh({ look: "intro", seed });
    const rows = [];
    let k = 0;
    play(p, g, 0, 4 + 60 * 4 + 4, (pos) => {
      if (pos >= 4 + 4 * k && k < 60) {                      // a bar apart: each area has faded before the next press
        const kind = k % 3 === 2 ? C : W;
        const rec = p.pad(kind, 0.6, pos, { hold: true });
        rows.push({ kind, name: rec.card.name, round: rec.round, restrike: rec.presses > 1 });
        p.padRelease(kind, pos + 0.01);
        k++;
      }
    });
    return rows;
  };
  const a = deal(7), b = deal(7), c = deal(8);
  assert.ok(a.every((x) => !x.restrike), "a bar apart, every press deals afresh");
  assert.deepEqual(a.map((x) => x.name), b.map((x) => x.name), "the same seed deals the same areas");
  assert.notDeepEqual(a.map((x) => x.name), c.map((x) => x.name), "another seed deals another order");
  for (const kind of [W, C]) {
    const mine = a.filter((x) => x.kind === kind);
    for (let i = 1; i < mine.length; i++) assert.notEqual(mine[i].name, mine[i - 1].name, `${kind}: the same area twice running at deal ${i}`);
  }
  for (let i = 1; i < a.length; i++) assert.notEqual(a[i].name, a[i - 1].name, `the deck dealt ${a[i].name} twice running`);
  const byRound = new Map();
  for (const x of a) { const s = byRound.get(x.round) || []; assert.ok(!s.includes(x.name), `round ${x.round}: ${x.name} twice`); s.push(x.name); byRound.set(x.round, s); }
  assert.ok(new Set(a.map((x) => x.name)).size === 4, `the deck reaches its areas: ${[...new Set(a.map((x) => x.name))].join(", ")}`);
  assert.deepEqual(KICK.validateKick(RIG1), [], "and the set's areas share no fixture");
});

test("the dealer deals only an area the camera sees, when the page tells it what the camera sees", () => {
  const g = locked(150), p = fresh({ look: "drop" });
  const seen = new Set(["rings", "beams"]);
  p.kick.view = (card) => (seen.has(card.name) ? 1 : 0);
  const got = [];
  let k = 0;
  play(p, g, 0, 4 + 12 * 4, (pos) => {
    if (pos >= 4 + 4 * k && k < 12) { const r = p.pad(k % 2 ? C : W, 0.8, pos, { hold: true }); got.push(r.card.name); p.padRelease(k % 2 ? C : W, pos + 0.01); k++; }
  });
  assert.ok(got.every((n) => seen.has(n)), `dealt: ${got.join(", ")}`);
});

// ------------------------------------------------------------------------------ the override and the colours --
test("OVERRIDE: a white kick turns a lit area full-intensity white over the look; a colour kick a vivid colour 90 degrees or more from the look's; release hands it back to the look", () => {
  for (const [kind, check] of [[W, "white"], [C, "colour"]]) {
    const g = locked(150), p = fresh({ look: "drop" }), base = fresh({ look: "drop" });
    force(p, "rings");
    let rec = null, during = null, after = null;
    for (let t = 0; t < 20 * g.period; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (!rec && pos >= 8.1) rec = p.pad(kind, 0.8, pos, { hold: true });
      if (rec && rec.releasedAt === null && pos >= 12) p.padRelease(kind, pos);
      p.tick(g, t, DT); base.tick(g, t, DT);
      if (!during && pos >= 10) {
        const ms = members(rec.card);
        const I = KICK.intensityOf(KICK.kickConfig(RIG1), 0.8);
        let lowLevel = 0, sat = 0, hueOff = 0, n = 0;
        for (const [k, i] of ms) {
          const l = levelOf(p, k, i);
          if (l < I * 0.6 - 1e-6) lowLevel++;                    // the chase never takes a member under 60 % of the intensity
          const c = colourOf(p, k, i), b0 = colourOf(base, k, i);
          sat += KICK.saturation(...c);
          hueOff += KICK.saturation(...b0) > 0.2 ? Math.min(Math.abs(KICK.hue(...c) - KICK.hue(...b0)), 360 - Math.abs(KICK.hue(...c) - KICK.hue(...b0))) : 180;
          n++;
        }
        during = { lowLevel, sat: sat / n, hueOff: hueOff / n, changed: changedShare(p, base, rec.card), level: areaLevel(p, rec.card), I };
      }
      if (!after && pos >= 17) after = changedShare(p, base, rec.card, 2);
    }
    assert.equal(rec.card.name, "rings");
    assert.equal(during.lowLevel, 0, `${check}: no ring LED under 60 % of the kick's intensity ${during.I.toFixed(3)}`);
    assert.ok(during.changed >= 0.95, `${check}: ${(100 * during.changed).toFixed(1)} % of the rings' LEDs changed by dE76 > 10`);
    if (check === "white") assert.ok(during.sat < 0.05, `white: saturation ${during.sat.toFixed(3)}`);
    else { assert.ok(during.sat > 0.6, `colour: saturation ${during.sat.toFixed(3)}`); assert.ok(during.hueOff >= 90, `colour: ${during.hueOff.toFixed(0)} degrees of hue from the look's`); }
    assert.ok(after < 0.01, `${check}: five beats after the release the rings are the look's again (${(100 * after).toFixed(2)} % differ)`);
  }
});

test("a re-strike while lit is a new hit at about the same brightness: the colour kick steps to the next palette colour of similar luminance on EVERY tap (never a saturated red), the white kick to a fresh motion", () => {
  const g = locked(150), p = fresh({ look: "break" });
  force(p, "rings");
  const seen = [];
  let k = 0, rec = null;
  play(p, g, 0, 30, (pos) => {
    // presses every 0.6 beat (0.24 s at 150 BPM) for 20 presses: each re-strikes the lit rings
    if (pos >= 8 + 0.6 * k && k < 20) {
      const r = p.pad(C, 0.9, pos, { hold: true });
      if (!rec) rec = r;
      assert.equal(r, rec, "every press re-strikes the same kick");
      p.padRelease(C, pos + 0.1);
      seen.push(p.kick.status().live.find((x) => x.kind === C).colour);
      k++;
    }
  });
  assert.equal(rec.card.name, "rings");
  assert.equal(seen.length, 20);
  const luma = (h) => { const c = hexLin(h); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
  for (let i = 1; i < seen.length; i++) {
    assert.notEqual(seen[i], seen[i - 1], `tap ${i}: a new colour`);
    assert.ok(KICK.deltaE(hexLin(seen[i]), hexLin(seen[i - 1])) >= 25, `tap ${i}: ${seen[i - 1]} -> ${seen[i]} reads as another colour`);
    const l0 = luma(seen[i - 1]), l1 = luma(seen[i]);
    assert.ok(Math.abs(l1 - l0) <= 0.35 * Math.max(l0, l1) + 1e-9, `tap ${i}: ${seen[i - 1]} (luminance ${l0.toFixed(2)}) -> ${seen[i]} (${l1.toFixed(2)})`);
  }
  for (const h of seen) assert.ok(!isSaturatedRed(hexLin(h)), `${h} is a saturated red`);
  // the white kick's re-strike: a fresh motion each tap, the chase jumped on
  const q = fresh({ look: "break" });
  force(q, "rings");
  const motions = [], shifts = [];
  let n = 0, wr = null;
  play(q, locked(150), 0, 20, (pos) => {
    if (pos >= 8 + 0.6 * n && n < 8) { wr = q.pad(W, 0.3, pos, { hold: true }); q.padRelease(W, pos + 0.1); motions.push(wr.motion && wr.motion.id); shifts.push(wr.chaseShift); n++; }
  });
  assert.ok(motions.slice(1).every((m) => m), `every re-strike moves, even at velocity 0.3: ${motions.join(", ")}`);
  for (let i = 2; i < shifts.length; i++) assert.notEqual(shifts[i], shifts[i - 1]);
});
function hexLin(h) { const v = parseInt(h.slice(1), 16); const f = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }; return [f(v >> 16 & 255), f(v >> 8 & 255), f(v & 255)]; }

test("moving heads change colour too: the wheel goes to the slot nearest the kick's colour the short way, never through the red slot, and comes back the same way", () => {
  const wheel = SCENE1.types["beam-7r"].attrs.Color1.colours.map(hexLin);
  const red = KICK.redSlots(wheel);
  assert.deepEqual(red, [1], "the beam's red slot");
  // every pair of slots: the way the kick turns passes no red slot
  for (let a = 0; a < 14; a++) for (let b = 0; b < 14; b++) {
    if (red.includes(a) || red.includes(b)) continue;
    const way = KICK.wheelWay(a, b, 14, red);
    for (let x = a, s = 0; x !== b && s < 14; s++) { x = (x + way + 14) % 14; assert.ok(!red.includes(x), `${a} -> ${b} passes red`); }
  }
  // and in the programmer: kicks on the halo and the beams in every look; no head ever shows the red slot
  let shownRed = 0, moved = 0;
  for (const look of ["intro", "build", "drop", "break", "groove"]) {
    const g = locked(150), p = fresh({ look });
    let k = 0;
    play(p, g, 0, 4 + 16 * 4, (pos) => {
      if (pos >= 4 + 4 * k && k < 16) { force(p, k % 2 ? "halo" : "beams"); p.pad(k % 4 < 2 ? C : W, 0.7, pos, { hold: true }); p.padRelease(k % 4 < 2 ? C : W, pos + 1.5); k++; }
      for (let i = 0; i < p.nH; i++) {
        if (!p.wheelOwn[i]) continue;
        moved++;
        const c = [p.heads[i * HEAD_FLOATS + H.R], p.heads[i * HEAD_FLOATS + H.G], p.heads[i * HEAD_FLOATS + H.B]];
        if (isSaturatedRed(c)) shownRed++;
      }
    });
  }
  assert.ok(moved > 1000, `kick-owned wheel frames: ${moved}`);
  assert.equal(shownRed, 0, "a kick's wheel never showed the red slot");
  // a white kick on the dark halo (its wheel parked on the theme's violet) takes it to white, one slot the short way
  const g = locked(150), p = fresh({ look: "break" });
  force(p, "halo");
  let rec = null;
  play(p, g, 0, 12, (pos) => { if (!rec && pos >= 8.1) rec = p.pad(W, 0.8, pos, { hold: true }); });
  const sats = Array.from(rec.card.heads, (i) => KICK.saturation(p.heads[i * HEAD_FLOATS + H.R], p.heads[i * HEAD_FLOATS + H.G], p.heads[i * HEAD_FLOATS + H.B]));
  assert.ok(Math.max(...sats) < 0.05, `the halo's wheels show white (saturation up to ${Math.max(...sats).toFixed(3)})`);
});

// KICK round 2, case K3: the colour kick's re-strikes sent the beams' wheels from indigo toward cyan through pink, magenta,
// violet and deep blue, eight slots a second, and the final limiter held 35 % of a roll of taps. A kick's wheel move must
// run clean (no dip or spike past governor.equal_luma on the way), never to a much darker slot, never white for a colour,
// and a re-strike's only between slots of about equal luminance.
test("a kick never runs a wheel through a flash: clean ways only, never to a much darker slot, a colour never white, a roll's wheels hold their brightness", () => {
  const wheel = SCENE1.types["beam-7r"].attrs.Color1.colours.map(hexLin);
  const red = KICK.redSlots(wheel), tol = KICK.kickConfig(RIG1).governor.equal_luma;
  const L = (i) => 0.2126 * wheel[i][0] + 0.7152 * wheel[i][1] + 0.0722 * wheel[i][2];
  const targets = [[1, 1, 1], ...SCENE1.kick.colour.palette.map(hexLin)];
  let moves = 0;
  for (let a = 0; a < 14; a++) {
    if (red.includes(a)) continue;
    for (const rgb of targets) {
      const t = KICK.nearestShortSlot(wheel, rgb, a, red, { tol });
      assert.ok(!red.includes(t), `${a}: never the red slot`);
      if (t === a) continue;
      moves++;
      const way = KICK.wheelWay(a, t, 14, red, wheel, tol);
      assert.ok(KICK.wayLumaClean(wheel, a, t, way, tol), `${a} -> ${t}: the way the wheel turns runs clean`);
      for (let x = a, k = 0; x !== t && k < 14; k++) { x = (x + way + 14) % 14; assert.ok(!red.includes(x), `${a} -> ${t} passes red`); }
      assert.ok(L(t) >= L(a) * (1 - tol) - 1e-9, `${a} -> ${t}: not a much darker slot (${L(a).toFixed(2)} -> ${L(t).toFixed(2)})`);
      if (KICK.saturation(...rgb) >= KICK.SAT_COLOUR) assert.ok(KICK.saturation(...wheel[t]) >= KICK.SAT_COLOUR, `${a} -> ${t}: a colour kick never turns a head white`);
      const near = KICK.nearestShortSlot(wheel, rgb, a, red, { tol, near: tol });
      assert.ok(near === a || Math.abs(L(near) - L(a)) <= tol * Math.max(L(near), L(a)) + 1e-9, `a re-strike's step ${a} -> ${near} keeps about the brightness`);
    }
  }
  assert.ok(moves > 20, `the kicks still turn wheels: ${moves} moves`);
  // in the programmer: a roll of colour taps on the beams and the halo (8 a second for 3 s, the white kick alternating) --
  // each head's shown slot luminance never turns back by more than tol
  for (const [colourArea, whiteArea] of [["beams", "halo"], ["halo", "beams"]]) {
    const g = locked(150), p = fresh({ look: "drop" });
    const seqs = new Map();
    let rec = null;
    play(p, g, 0, 16, (pos, t) => {
      const f = Math.round(t / (1000 / FPS)) - 4 * 60;
      if (f >= 0 && f < 184) {
        const pad = Math.floor(f / 8) % 2 ? C : W;
        if (f % 8 === 0 && f < 180) { if (f === 0) force(p, whiteArea); else if (f === 8) force(p, colourArea); const r = p.pad(pad, 1, pos, { hold: true }); if (pad === C) rec = r; }
        if (f % 8 === 4) p.padRelease(pad, pos);
      }
      if (rec && f > 8 && f < 184) for (const i of rec.card.heads) { if (!seqs.has(i)) seqs.set(i, []); seqs.get(i).push(L(p.wheelSlotOf(i))); }
    });
    assert.ok(rec && rec.card.name === colourArea && rec.presses > 5, `the colour kick re-struck ${colourArea}`);
    let turns = 0;
    for (const sq of seqs.values()) {
      let dir = 0, ext = sq[0];
      for (const v of sq) {
        if (dir >= 0 && v < ext * (1 - tol) - 1e-9) { if (dir > 0) turns++; dir = -1; ext = v; }
        else if (dir <= 0 && v > ext / (1 - tol) + 1e-9) { if (dir < 0) turns++; dir = 1; ext = v; }
        else ext = dir >= 0 ? Math.max(ext, v) : Math.min(ext, v);
      }
    }
    assert.equal(turns, 0, `${colourArea}: no head's wheel turned its brightness back during the roll`);
  }
});

// -------------------------------------------------------------------------------------- the level and the gate --
test("the level curve keeps the whole strip high: intensity = 0.5 + 0.5 sqrt(level); padLevel moves a held area with the finger, monotone and slewed", () => {
  const cfg = KICK.kickConfig(RIG1);
  const I = (v) => KICK.intensityOf(cfg, v);
  assert.equal(I(0), 0.5); assert.equal(I(1), 1);
  assert.ok(Math.abs(I(0.25) - 0.75) < 1e-9 && Math.abs(I(0.5) - 0.8536) < 1e-3);
  for (let v = 0; v < 1; v += 0.05) assert.ok(I(v + 0.05) > I(v));
  const g = locked(128), p = fresh({ look: "intro" });
  force(p, "beams");
  let rec = null, si = 0;
  const steps = [[8, 0.1], [10, 0.4], [12, 0.6], [14, 0.8], [16, 0.9]];
  const seen = [];
  play(p, g, 0, 18.5, (pos) => {
    if (!rec && pos >= 7) rec = p.pad(W, 0.3, pos, { hold: true });
    if (si < steps.length && pos >= steps[si][0]) { p.padLevel(W, steps[si][1]); si++; }
    if (rec) seen.push([pos, areaLevel(p, rec.card)]);
  });
  assert.equal(rec.card.name, "beams");
  const settled = steps.map(([b, v]) => [I(v), seen.filter(([pos]) => pos > b + 1.5 && pos < b + 1.9).map((x) => x[1])]);
  for (const [want, xs] of settled) assert.ok(xs.length && xs.every((x) => Math.abs(x - want) < 0.01), `intensity ${want.toFixed(3)}: the area settled at ${xs[0] && xs[0].toFixed(3)}`);
  for (let i = 1; i < settled.length; i++) assert.ok(settled[i][1][0] > settled[i - 1][1][0], "brighter with every step up");
  assert.ok(settled[0][1][0] > 0.6, `the bottom of the strip (level 0.1) is still ${settled[0][1][0].toFixed(2)}`);
  let worst = 0;
  for (let i = 1; i < seen.length; i++) if (seen[i][0] > 8) worst = Math.max(worst, Math.abs(seen[i][1] - seen[i - 1][1]));
  assert.ok(worst < 0.08, `the largest one-frame step ${worst.toFixed(3)} (no zipper)`);
});

test("hold = gate: held, the area stays at its intensity; let go, it fades over a third of a beat; a tap is a one-second hit; a re-press while it is lit re-strikes it", () => {
  const cfg = KICK.kickConfig(RIG1);
  const g = locked(150), p = fresh({ look: "break" }), base = fresh({ look: "break" });
  force(p, "beams");
  let rec = null;
  const lv = [];
  for (let t = 0; t < 20 * g.period; t += 1000 / FPS) {
    const pos = g.posAt(t);
    if (!rec && pos >= 6) rec = p.pad(W, 0.4, pos, { hold: true });       // the peak band: the area simply on
    if (rec && rec.releasedAt === null && pos >= 14) p.padRelease(W, pos);
    p.tick(g, t, DT); base.tick(g, t, DT);
    if (rec) lv.push([pos, areaLevel(p, rec.card), areaLevel(base, rec.card)]);
  }
  const want = KICK.intensityOf(cfg, 0.4);
  const held = lv.filter(([pos]) => pos >= 6.5 && pos < 14);           // after the punch (0.15 s)
  assert.ok(held.every(([, x]) => Math.abs(x - want) < 0.01), `held 8 beats at ${want.toFixed(3)}: ${Math.min(...held.map((x) => x[1])).toFixed(3)}..${Math.max(...held.map((x) => x[1])).toFixed(3)}`);
  const at = (b) => lv.find(([pos]) => pos >= b)[1];
  assert.ok(at(14.3) < at(14) * 0.45 && at(14.3) > at(14) * 0.2, `released at 14 (long after the press: no linger): ${at(14).toFixed(3)} -> ${at(14.3).toFixed(3)}`);
  const baseAt = (b) => lv.find(([pos]) => pos >= b)[2];
  assert.ok(Math.abs(at(16) - baseAt(16)) < 0.01, `two beats after the release the area is the look's again: ${at(16).toFixed(4)} (the look: ${baseAt(16).toFixed(4)})`);
  // a tap a tenth of a beat before its line lights AT THE PRESS (Daniel, 2026-10-27: "currently kick doesnt always trigger
  // when its pressed ... can we make sure that the kick buttons are responsive"; round 1 waited for the line) and stays lit
  // a second (2.5 beats at 150 BPM) after the press; the press still belongs to beat 8
  const p2 = fresh({ look: "break" });
  force(p2, "beams");
  let r2 = null; const lv2 = [];
  play(p2, locked(150), 0, 14, (pos) => {
    if (!r2 && pos >= 7.9) { r2 = p2.pad(W, 0.9, pos, { hold: true }); p2.padRelease(W, pos); }
    if (r2) lv2.push([pos, areaLevel(p2, r2.card)]);
  });
  const lit = lv2.filter((x) => x[1] > 0.5);
  assert.ok(lit[0][0] >= 7.9 - 1e-9 && lit[0][0] < 7.9 + 0.1, `lit at the press: from ${lit[0][0].toFixed(3)}`);
  assert.ok(lit.at(-1)[0] > 7.9 + 2.5 && lit.at(-1)[0] < 7.9 + 2.5 + 0.4, `a one-second hit: lit until ${lit.at(-1)[0].toFixed(3)}`);
  assert.equal(p2.stats.kicks.at(-1), 8);
  // a re-press while the area is lit re-strikes it: the same kick, no new area
  const p3 = fresh({ look: "break" });
  force(p3, "beams");
  const r = [];
  play(p3, locked(150), 0, 14, (pos) => {
    if (r.length === 0 && pos >= 6) { r.push(p3.pad(W, 0.8, pos, { hold: true })); p3.padRelease(W, pos + 0.05); }
    if (r.length === 1 && pos >= 7) { r.push(p3.pad(W, 0.8, pos, { hold: true })); p3.padRelease(W, pos + 0.05); }
    if (r.length === 2 && pos >= 12) { r.push(p3.pad(W, 0.8, pos, { hold: true })); p3.padRelease(W, pos + 0.05); }
  });
  assert.equal(r[1], r[0], "a press 0.4 s later re-strikes the lit area");
  assert.equal(r[0].presses, 2);
  assert.notEqual(r[2], r[0], "a press after it has faded deals afresh");
});

test("velocity picks the animation: soft = the area on, medium = a sweep, hard = twice the throw, within the tilt motor; LED areas chase", () => {
  const cfg = KICK.kickConfig(RIG1);
  const band = (v) => KICK.bandFor(cfg, v).name;
  assert.equal(band(0), "peak"); assert.equal(band(0.44), "peak");
  assert.equal(band(0.45), "sweep"); assert.equal(band(0.8), "sweep");
  assert.equal(band(0.85), "drive"); assert.equal(band(1), "drive");
  const tiltSwing = (vel) => {
    const g = locked(150), p = fresh({ look: "intro" }), b = fresh({ look: "intro" });
    force(p, "beams");
    let rec = null, swing = 0;
    for (let t = 0; t < 16 * g.period; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (!rec && pos >= 8) rec = p.pad(C, vel, pos, { hold: true });
      p.tick(g, t, DT); b.tick(g, t, DT);
      if (rec) for (const i of rec.card.heads) swing = Math.max(swing, Math.abs(p.heads[i * HEAD_FLOATS + H.TILT] - b.heads[i * HEAD_FLOATS + H.TILT]));
    }
    return { swing, rec };
  };
  const soft = tiltSwing(0.3), med = tiltSwing(0.7), hard = tiltSwing(0.9);
  assert.equal(soft.rec.card.name, "beams");
  assert.equal(soft.rec.band, "peak"); assert.equal(soft.rec.motion, null);
  assert.ok(soft.swing < 0.5, `a peak leaves the heads where they are (${soft.swing.toFixed(2)} deg)`);
  assert.ok(med.rec.motion && med.swing > 4, `a sweep moves them (${med.swing.toFixed(1)} deg, ${med.rec.motion && med.rec.motion.id})`);
  assert.ok(hard.rec.motion && hard.swing > 4, `a hard sweep moves them (${hard.swing.toFixed(1)} deg, ${hard.rec.motion && hard.rec.motion.id})`);
  assert.ok(hard.rec.motion.want > 1.5 * med.rec.motion.want, `asked: ${hard.rec.motion.want.toFixed(1)} vs ${med.rec.motion.want.toFixed(1)} deg`);
  assert.ok(hard.rec.motion.deg >= med.rec.motion.deg - 1e-9, `thrown: ${hard.rec.motion.deg.toFixed(1)} vs ${med.rec.motion.deg.toFixed(1)} deg`);
  for (const r of [med.rec, hard.rec]) assert.ok(r.motion.peakDegPerS <= (270 / 1.4) * 0.8 + 1e-6, `${r.motion.id}: ${r.motion.peakDegPerS.toFixed(0)} deg/s asked`);
  const g = locked(150), p = fresh({ look: "intro" });
  force(p, "rings");
  let rec = null, spread = 0;
  play(p, g, 0, 16, (pos) => {
    if (!rec && pos >= 8) rec = p.pad(W, 0.7, pos, { hold: true });
    if (rec && pos > 9) {
      let lo = 1, hi = 0;
      for (const c of rec.card.cells) { const a = p.pixels[c * 4 + 3]; lo = Math.min(lo, a); hi = Math.max(hi, a); }
      spread = Math.max(spread, hi - lo);
    }
  });
  assert.ok(rec.motion && spread > 0.15, `the chase runs round the rings (level spread ${spread.toFixed(2)})`);
});

test("two kicks at once: white and colour held together light two different areas, never one twice, both at high intensity; an area still fading is not the other button's", () => {
  const g = locked(150), p = fresh({ look: "drop" });
  const pairs = [];
  let k = 0;
  play(p, g, 0, 4 + 30 * 8, (pos) => {
    const slot = Math.floor((pos - 4) / 8);
    if (pos >= 4 && slot === k && k < 30) {
      const w = p.pad(W, 0.55 + 0.35 * ((k * 7) % 10) / 10, pos, { hold: true });
      const c = p.pad(C, 0.5 + 0.4 * ((k * 3) % 10) / 10, pos + 0.01, { hold: true });
      pairs.push({ w, c, at: pos, checked: false, released: false });
      k++;
    }
    const cur = pairs.at(-1);
    if (cur && !cur.checked && pos >= cur.at + 1) {
      cur.checked = true;
      cur.lw = areaLevel(p, cur.w.card); cur.lc = areaLevel(p, cur.c.card);
      cur.live = p.kick.list.filter((x) => x.held).map((x) => x.card.name);
    }
    if (cur && cur.checked && pos >= cur.at + 2 && !cur.released) { p.padRelease(W, pos); p.padRelease(C, pos); cur.released = true; }
  });
  assert.equal(pairs.length, 30);
  for (const x of pairs) {
    assert.notEqual(x.w.card.name, x.c.card.name, `pair at ${x.at.toFixed(2)}: one area twice`);
    assert.deepEqual(x.live.sort(), [x.w.card.name, x.c.card.name].sort(), "both held at once");
    assert.ok(x.lw > 0.45 && x.lc > 0.45, `both areas high: ${x.w.card.name} ${x.lw.toFixed(2)}, ${x.c.card.name} ${x.lc.toFixed(2)}`);
  }
  assert.ok(new Set(pairs.flatMap((x) => [x.w.card.name, x.c.card.name])).size === 4, "the two buttons went round the stage");
  // forced at the white kick's fading area, the colour kick is dealt another; the white button's re-press takes its own
  const q = fresh({ look: "break" });
  let w = null, c = null, w2 = null;
  play(q, locked(150), 0, 16, (pos) => {
    if (!w && pos >= 6) { force(q, "beams"); w = q.pad(W, 0.8, pos, { hold: true }); }
    if (w && w.releasedAt === null && pos >= 7) q.padRelease(W, pos);
    // the white kick lingers a second after its press (to beat 8.5 at 150 BPM), then fades: at 8.7 it is still at half
    if (w && !c && pos >= 8.7) { force(q, "beams"); c = q.pad(C, 0.8, pos, { hold: true }); }
    if (c && !w2 && pos >= 8.8) { force(q, "beams"); w2 = q.pad(W, 0.8, pos, { hold: true }); }
  });
  assert.equal(w.card.name, "beams");
  assert.ok(w.releasedAt !== null && q.kick._env(w, 8.7) < 1 && q.kick._env(w, 8.7) > 0.3, "the white kick's area was fading when the colour kick came");
  assert.notEqual(c.card.name, "beams", "the colour kick never takes the white kick's fading area");
  assert.equal(w2.card.name, "beams", "the white button's re-press takes its own fading area over");
});

// ------------------------------------------------------------------------------------------- the flash budget --
test("a roll of taps holds the areas instead of flashing them: both buttons alternately at full level every 8 frames for 3 s, two rises and two falls in all, and the limiter never acts", () => {
  for (const bpm of [128, 150]) {
    const g = locked(bpm), p = fresh({ look: "break" });
    const series = [];
    let f = 0, presses = 0;
    const areas = new Set();
    for (let t = 0; t < 7000; t += 1000 / FPS, f++) {
      const pos = g.posAt(t);
      if (f >= 120 && f < 300) {
        const q = f - 120, kind = Math.floor(q / 8) % 2 ? C : W;
        if (q % 8 === 0) { const r = p.pad(kind, 1, pos, { hold: true }); areas.add(r.card.name); presses++; }
        if (q % 8 === 4) p.padRelease(kind, pos);
      }
      p.tick(g, t, DT);
      // the frame a viewer sees, simplified: the kicks' areas as two halves of the screen (their mean emitted luminance)
      const lum = (card) => { const ms = members(card); return ms.reduce((s, [k, i]) => { const e = emitted(p, k, i); return s + 0.2126 * e[0] + 0.7152 * e[1] + 0.0722 * e[2]; }, 0) / ms.length; };
      const live = p.kick.list.filter((k) => !k.dead);
      series.push([t, live.map((k) => [k.kind, lum(k.card)])]);
    }
    assert.equal(areas.size, 2, `${bpm} BPM: the roll held two areas: ${[...areas].join(", ")}`);
    assert.equal(p.kick.restrikes, presses - 2, `${bpm} BPM: ${presses} presses, ${p.kick.restrikes} re-strikes (all but the first of each button)`);
    // the two areas' luminance as the top and bottom halves of a 4 x 4 frame
    const lim = new FrameLimiter();
    const byKind = (row, kind) => { const x = row.find((r) => r[0] === kind); return x ? x[1] : 0; };
    for (const [t, row] of series) {
      const L = new Float64Array(16), top = Math.min(1, 3 * byKind(row, W)), bot = Math.min(1, 3 * byKind(row, C));
      for (let c = 0; c < 8; c++) L[c] = top;
      for (let c = 8; c < 16; c++) L[c] = bot;
      lim.step({ L, R: new Float64Array(16) }, t / 1000, DT);
    }
    assert.equal(lim.stats().interventions, 0, `${bpm} BPM: the limiter acted on ${lim.stats().interventions} frames`);
  }
});

test("the strobe: only while the live level is in the top band (>= 0.95), on and off as the level crosses it, never more than 4 edges in any 1.01 s, and the limiter never has to act on it", () => {
  const report = [];
  for (const bpm of [100, 128, 150, 174]) {
    const g = locked(bpm), p = fresh({ look: "break" });
    force(p, "beams");
    let rec = null;
    const series = [];
    const tA = 2000, tB = tA + 4000, tC = tB + 6000, tD = tC + 3000;
    const marks = [[tB, 1], [tC, 0.9]];
    let mi = 0, released = false;
    for (let t = 0; t < tD + 2000; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (!rec && t >= tA) rec = p.pad(W, 0.9, pos, { hold: true });
      if (mi < marks.length && t >= marks[mi][0]) { p.padLevel(W, marks[mi][1]); mi++; }
      if (!released && t >= tD) { p.padRelease(W, pos); released = true; }
      p.tick(g, t, DT);
      if (rec) series.push([t, areaLevel(p, rec.card), rec.strobing]);
    }
    const edges = [];
    let on = series[0][1] > 0.45;
    for (const [t, x] of series) { const now = x > 0.45; if (now !== on) { edges.push(t); on = now; } }
    const inside = (a, b) => edges.filter((t) => t >= a && t < b);
    assert.equal(inside(tA + 300, tB).length, 0, `${bpm} BPM: no strobe at level 0.9`);
    assert.ok(inside(tB, tC).length >= 6, `${bpm} BPM: it strobes at level 1.0 (${inside(tB, tC).length} edges in 6 s)`);
    assert.ok(inside(tB, tB + 400).length >= 1, `${bpm} BPM: the strobe engages as the level reaches the band`);
    assert.ok(series.some(([t, , s]) => t > tB && t < tC && s) && !series.some(([t, , s]) => t > tC + 600 && s), `${bpm} BPM: strobing only in the band`);
    assert.equal(inside(tC + 600, tD).length, 0, `${bpm} BPM: the strobe stops below the band`);
    let most = 0;
    for (let i = 0; i < edges.length; i++) most = Math.max(most, edges.filter((t) => t >= edges[i] && t < edges[i] + 1010).length);
    assert.ok(most <= 4, `${bpm} BPM: ${most} edges inside one 1.01 s window`);
    const flashes = inside(tB, tC).length / 2 / 6;
    assert.ok(flashes <= KICK.STROBE_HZ_CAP + 0.05, `${bpm} BPM: ${flashes.toFixed(2)} flashes a second`);
    const lim = new FrameLimiter();
    for (const [t, x] of series) lim.step({ L: new Float64Array(16).fill(0.6 * x), R: new Float64Array(16) }, t / 1000, DT);
    assert.equal(lim.stats().interventions, 0, `${bpm} BPM: the limiter acted on ${lim.stats().interventions} frames`);
    report.push(`${bpm} BPM: ${flashes.toFixed(2)} flashes/s, most edges in 1.01 s ${most}, limiter interventions ${lim.stats().interventions}`);
  }
  console.log(`  the strobe alone, the whole screen strobing:\n  ${report.join("\n  ")}`);
});

test("two kicks strobing together stay inside the gate by themselves: the strobes share one beat-locked clock", () => {
  for (const bpm of [128, 150]) {
    const g = locked(bpm), p = fresh({ look: "break" });
    let w = null, c = null, rel = false;
    const series = [];
    for (let t = 0; t < 14000; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (!w && t >= 1000) { force(p, "beams"); w = p.pad(W, 1, pos, { hold: true }); }
      if (!c && t >= 1700) { force(p, "halo"); c = p.pad(C, 1, pos, { hold: true }); }
      if (!rel && t >= 12000) { p.padRelease(W, pos); p.padRelease(C, pos); rel = true; }
      p.tick(g, t, DT);
      if (w && c) series.push([t, (areaLevel(p, w.card) + areaLevel(p, c.card)) / 2, w.maskOn, c.maskOn]);
    }
    assert.notEqual(w.card.name, c.card.name);
    // after the second one joins, the two strobe masks are one: they go dark and light on the same frames
    const apart = series.filter(([t, , a, b]) => t > 2600 && t < 12000 && a !== b).length;
    assert.ok(apart === 0, `${bpm} BPM: ${apart} frames with one area's strobe lit and the other's dark`);
    const lim = new FrameLimiter();
    for (const [t, x] of series) lim.step({ L: new Float64Array(16).fill(0.6 * x), R: new Float64Array(16) }, t / 1000, DT);
    assert.equal(lim.stats().interventions, 0, `${bpm} BPM: the limiter acted on ${lim.stats().interventions} frames`);
  }
});

// ------------------------------------------------------------------------------------ dead kicks (node level) --
// Round 1's acceptance, kept as a regression and re-cut to the emitted light: a press is dead when fewer than half the
// dealt area's members change their emitted light (linear RGB x level) by more than dE76 10 within a beat of it. (The
// round-2 acceptance proper is the screen's pixels: stage_verify kickpix.)
test("no dead kicks: in every look of source-v1, both kicks pressed at 20 phases across a beat at velocity 0.8 change most of their area, every press", () => {
  const looks = Object.keys(SCENE1.looks);
  const table = [], dead = [];
  for (const bpm of [128, 150]) {
    for (const look of looks) {
      const g = locked(bpm), base = fresh({ look });
      const runs = [W, C].map((kind) => ({ kind, p: fresh({ look }), next: 0, cur: null, out: [] }));
      const at = (k) => 8 + 4 * k + k / 20;
      for (let f = 0; f < FPS * 600; f++) {
        const t = f * (1000 / FPS), pos = g.posAt(t);
        for (const r of runs) {
          if (r.next < 20 && pos >= at(r.next)) {
            const rec = r.p.pad(r.kind, 0.8, pos, { hold: true });
            r.cur = { phase: r.next / 20, pos, rec, best: 0 };
            r.next++;
          }
          if (r.cur && r.cur.rec.releasedAt === null && pos >= r.cur.pos + 0.25) r.p.padRelease(r.kind, pos);
        }
        base.tick(g, t, DT);
        let busy = false;
        for (const r of runs) {
          r.p.tick(g, t, DT);
          if (!r.cur) { busy = busy || r.next < 20; continue; }
          busy = true;
          r.cur.best = Math.max(r.cur.best, changedShare(r.p, base, r.cur.rec.card));
          if (pos > r.cur.pos + 1) { r.out.push(r.cur); r.cur = null; }
        }
        if (!busy) break;
      }
      for (const r of runs) {
        assert.equal(r.out.length, 20);
        const d = r.out.filter((x) => x.best < KICK.KICK_VISIBLE.share);
        table.push(`${String(bpm).padStart(3)} BPM ${look.padEnd(6)} ${r.kind.padEnd(11)} dead ${String(d.length).padStart(2)}/20  min changed ${(100 * Math.min(...r.out.map((x) => x.best))).toFixed(0)} %  areas ${[...new Set(r.out.map((x) => x.rec.card.name))].join(", ")}`);
        for (const x of d) dead.push(`${bpm} ${look} ${r.kind} phase ${x.phase.toFixed(2)}: ${x.rec.card.name} ${(100 * x.best).toFixed(0)} %`);
      }
    }
  }
  console.log(`  no dead kicks (at least half the area's members change by dE76 > 10):\n  ${table.join("\n  ")}`);
  assert.deepEqual(dead, [], `dead presses:\n${dead.slice(0, 24).join("\n")}`);
});

// --------------------------------------------------------------------------------------- the fallback and data --
test("without a kick block (source-v0) KICK is the v0 strand lift: the strand's cubes and heads, 0.6 + 0.4 x velocity, decaying over 0.3 beat", () => {
  assert.equal(KICK.kickConfig(RIG0).legacy, true);
  const g = locked(150), p = fresh({ rig: RIG0, theme: THEME0, look: "break" });
  const cube = RIG0.cells.kind.indexOf(2);
  let rec = null; const lv = [];
  play(p, g, 0, 12, (pos) => { if (!rec && pos >= 7.9) rec = p.pad("kick", 0.5, pos); lv.push([pos, p.kickLevel(pos), p.pixels[cube * 4 + 3]]); });
  assert.ok(rec.card.cells.includes(cube) && rec.card.heads.length === 12, "the strand: its heads and its cube cells");
  for (const [pos, k] of lv) {
    const want = pos < 8 - 1e-6 ? 0 : 0.8 * Math.exp(-(pos - 8) / 0.3);
    assert.ok(Math.abs(k - want) < 1e-6 || (want < 0.004 && k === 0), `at ${pos.toFixed(3)}: ${k} (v0: ${want})`);
  }
  const line = lv.find(([pos]) => pos >= 8 - 1e-9);
  assert.ok(line[2] >= 0.8 - 1e-4, `the cube at the line: ${line[2]}`);
});

test("the kick block is checked: source-v1's is valid; unknown groups, areas sharing fixtures, a saturated-red palette colour and a strobe above the house cap are refused", () => {
  assert.deepEqual(KICK.validateKick(RIG1), []);
  assert.deepEqual(KICK.validateKick(RIG0), [], "no block is valid (the v0 kick)");
  const bad = (patch) => KICK.validateKick({ ...RIG1, kick: { ...SCENE1.kick, ...patch } });
  assert.ok(bad({ deck: [{ rows: ["no.such.group"] }] }).some((m) => /no\.such\.group/.test(m)));
  assert.ok(bad({ deck: [{ rows: ["halo"] }, { rows: ["halo.top"] }] }).some((m) => /share/.test(m)));
  assert.ok(bad({ strobe: { ...SCENE1.kick.strobe, max_hz: 3 } }).some((m) => /strobe/.test(m)));
  assert.ok(bad({ bands: [{ name: "x", from: 0.2 }] }).some((m) => /bands/.test(m)));
  assert.ok(bad({ colour: { palette: ["#00e5ff", "#ff2010"] } }).some((m) => /saturated red/.test(m)));
  assert.ok(bad({ governor: { linger_s: 1, punch_s: 0.15, equal_luma: 0 } }).some((m) => /equal_luma/.test(m)));
  assert.ok(bad({ kinds: { "kick-white": { colour: "#ff2010" } } }).some((m) => /kinds.kick-white.colour/.test(m)));
  assert.ok(bad({ kinds: { "kick-white": { repeat: "explode" } } }).some((m) => /kinds.kick-white.repeat/.test(m)));
  assert.deepEqual(Object.keys(SCENE1.kick.kinds), ["kick-white", "kick-colour"], "the set's kinds: white and colour first");
  for (const h of SCENE1.kick.colour.palette) assert.ok(!isSaturatedRed(hexLin(h)), `${h}`);
  assert.deepEqual({ ...KICK.KICK_VISIBLE }, { de: 10, share: 0.5 });
  assert.deepEqual([...KICK.KICK_ROLES], [...ROLE_NAMES]);
  assert.equal(SCENE1.show.pads["1"], "kick-white");
  assert.equal(SCENE1.show.pads["5"], "kick-colour");
});

// --------------------------------------------------------------------------------- responsive, punch and kinds --
test("responsive: a press at any phase of its beat lights its area on the very next frame, with a punch over the held level that settles in 0.15 s", () => {
  const cfg = KICK.kickConfig(RIG1);
  for (let ph = 0; ph < 1; ph += 0.125) {
    const g = locked(150), p = fresh({ look: "intro" });
    force(p, "rings");
    let rec = null, first = null, pressT = null;
    const lv = [];
    for (let t = 0; t < 12 * g.period; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (!rec && pos >= 8 + ph) { rec = p.pad(C, 0.3, pos, { hold: true }); pressT = t; }   // the peak band: no chase
      p.tick(g, t, DT);
      if (rec) { lv.push([t - pressT, areaLevel(p, rec.card)]); if (first === null) first = areaLevel(p, rec.card); }
    }
    assert.equal(rec.onset, Math.round(rec.pressPos), "the press still belongs to its nearest beat");
    const held = KICK.intensityOf(cfg, 0.3);
    assert.ok(first > held, `phase ${ph}: the first frame after the press is lit (${first.toFixed(3)}, held level ${held.toFixed(3)})`);
    const peak = Math.max(...lv.map((x) => x[1]));
    const punch = cfg.kinds[C].punch;
    assert.ok(peak >= Math.min(1, held + punch) - 0.01, `phase ${ph}: the punch overshoots the held level by ${punch} (${peak.toFixed(3)} over ${held.toFixed(3)})`);
    const later = lv.filter(([dt]) => dt > 200 && dt < 600).map((x) => x[1]);
    assert.ok(later.every((x) => Math.abs(x - held) < 0.01), `phase ${ph}: settled to ${held.toFixed(3)} after 0.15 s`);
  }
});

test("the kinds are data: a set may add a kind (its own colour, no repeat) and map a pad to it; two palette kinds held together never clash", () => {
  const scene = JSON.parse(JSON.stringify(SCENE1));
  scene.kick.kinds["kick-amber"] = { colour: "#ffd21a", override: true, motion: "none", strobe: false, repeat: "none", punch: 0 };
  scene.kick.kinds["kick-colour-2"] = { colour: "palette", override: true, motion: "none", strobe: false, repeat: "colour", punch: 0 };
  const rig = expandScene(scene);
  assert.deepEqual(KICK.validateKick(rig), []);
  const g = locked(150), p = fresh({ rig, look: "break" });
  assert.equal(p.kick.kindOf("kick-amber"), "kick-amber");
  assert.equal(p.kick.kindOf("kick"), "kick-white", "'kick' is the first kind");
  assert.equal(p.kick.kindOf("no-such-kind"), null);
  let a = null, c1 = null, c2 = null;
  play(p, g, 0, 12, (pos) => {
    if (!a && pos >= 6) { force(p, "rings"); a = p.pad("kick-amber", 0.8, pos, { hold: true }); }
    if (!c1 && pos >= 7) c1 = p.pad("kick-colour", 0.8, pos, { hold: true });
    if (!c2 && pos >= 7.2) c2 = p.pad("kick-colour-2", 0.8, pos, { hold: true });
  });
  assert.equal(a.card.name, "rings");
  const cells = Array.from(a.card.cells.slice(0, 50));
  assert.ok(cells.every((c) => Math.abs(KICK.hue(...colourOf(p, "c", c)) - KICK.hue(...hexLin("#ffd21a"))) < 3), "the amber kind paints its own colour");
  assert.equal(a.motion, null, "and does not move");
  const h1 = KICK.hue(...c1.colour.rgb), h2 = KICK.hue(...c2.colour.rgb);
  const d = Math.min(Math.abs(h1 - h2), 360 - Math.abs(h1 - h2));
  assert.ok(d >= 60, `two palette kinds at once: ${p.kick._hexOf(c1)} and ${p.kick._hexOf(c2)} are ${d.toFixed(0)} degrees apart`);
  assert.ok(new Set([a.card.name, c1.card.name, c2.card.name]).size === 3, "three kinds, three areas");
});

test("a re-strike flips a comb on the area (alternate heads at full and at 35 %), the area's mean brightness kept", () => {
  const cfg = KICK.kickConfig(RIG1);
  const g = locked(150), p = fresh({ look: "break" });
  force(p, "beams");
  const snaps = [];
  let k = 0, rec = null;
  play(p, g, 0, 14, (pos) => {
    if (pos >= 8 + 0.8 * k && k < 4) { rec = p.pad(W, 0.3, pos, { hold: true }); p.padRelease(W, pos + 0.05); k++; snaps.push({ at: pos, done: false }); }
    for (const sn of snaps) if (!sn.done && pos >= sn.at + 0.45) {           // after the first hit's punch (0.15 s)
      sn.done = true;
      sn.levels = Array.from(rec.card.heads, (i) => p.heads[i * HEAD_FLOATS + H.DIM]);
    }
  });
  const I = KICK.intensityOf(cfg, 0.3), lo = I * cfg.governor.comb_floor;
  assert.equal(rec.card.name, "beams");
  assert.ok(snaps[0].levels.every((x) => Math.abs(x - I) < 0.02), "the first hit: every head at the intensity");
  for (let n = 1; n < 4; n++) {
    const lv = snaps[n].levels;
    const low = lv.filter((x) => Math.abs(x - lo) < 0.03).length, high = lv.filter((x) => Math.abs(x - I) < 0.03).length;
    assert.equal(low + high, lv.length, `re-strike ${n}: every head at full or at the comb's floor (${lv.map((x) => x.toFixed(2)).join(" ")})`);
    assert.ok(low >= 6 && high >= 6, `re-strike ${n}: half and half (${low} low, ${high} high)`);
    const flipped = lv.filter((x, i) => (x < (I + lo) / 2) !== (snaps[n - 1].levels[i] < (I + lo) / 2)).length;
    if (n >= 2) assert.ok(flipped >= lv.length * 0.75, `re-strike ${n}: the comb flipped (${flipped} of ${lv.length} heads changed side)`);
  }
});

// ----------------------------------------------------------------------------------------------- the governor --
test("the flash governor: with the limiter's budget spent the kick still lights every press, but holds back its optional changes (punch, colour step, comb, the start of a fade, the strobe going dark)", () => {
  const cfg = KICK.kickConfig(RIG1);
  const g = locked(150), p = fresh({ look: "break" });
  force(p, "rings");
  let rec = null, r2 = null;
  const lv = [];
  p.kick.headroom = 1;                                        // the limiter's most loaded window has one transition left
  play(p, g, 0, 16, (pos) => {
    if (!rec && pos >= 6) rec = p.pad(C, 0.3, pos, { hold: true });
    if (rec && !r2 && pos >= 6.5) { r2 = p.pad(C, 0.3, pos, { hold: true }); p.padRelease(C, pos + 0.05); }
    if (rec) lv.push([pos, areaLevel(p, rec.card)]);
  });
  const held = KICK.intensityOf(cfg, 0.3);
  assert.ok(lv.filter(([pos]) => pos > 6 && pos < 6.4).every(([, x]) => x <= held + 1e-6), "no punch without headroom");
  assert.ok(lv.find(([pos]) => pos >= 6.05)[1] > held - 0.01, "but the press lights at once");
  assert.equal(r2, rec, "the second press re-strikes");
  assert.equal(rec.presses, 2);
  assert.ok(p.kick.gov.colour >= 1 && p.kick.gov.comb >= 1 && p.kick.gov.punch >= 1, `held back: ${JSON.stringify(p.kick.gov)}`);
  assert.equal(rec.comb, 0, "no comb flip");
  // the fade waits (up to governor.defer_s) while the budget stays spent
  const lingerEnd = 6.5 + cfg.governor.linger_s * 1000 / g.period;
  const at = (b) => lv.find(([pos]) => pos >= b)[1];
  assert.ok(at(lingerEnd + 1) > held - 0.01, `still lit a beat after its linger (${at(lingerEnd + 1).toFixed(3)})`);
  assert.ok(p.kick.gov.fade > 0);
  // and with headroom back it fades as usual
  const q = fresh({ look: "break" });
  force(q, "rings");
  let k2 = null; const lv2 = [];
  play(q, locked(150), 0, 16, (pos) => {
    if (!k2 && pos >= 6) { k2 = q.pad(C, 0.3, pos, { hold: true }); q.padRelease(C, pos + 0.05); }
    if (k2) lv2.push([pos, areaLevel(q, k2.card)]);
  });
  const at2 = (b) => lv2.find(([pos]) => pos >= b)[1];
  assert.ok(at2(6 + cfg.governor.linger_s * 1000 / 400 + 1.5) < 0.5 * held, "with headroom the area fades after its linger");
});

test("the flash governor stands a live area's motion still while the budget is spent, and moves it on from there", () => {
  const g = locked(150), p = fresh({ look: "break" });
  force(p, "beams");
  let rec = null;
  const tilts = [];
  play(p, g, 0, 20, (pos) => {
    if (!rec && pos >= 4) rec = p.pad(W, 1, pos, { hold: true });
    p.kick.headroom = pos >= 8 && pos < 12 ? 0 : 5;
    if (rec) { const b = rec.card.heads[0] * 7; tilts.push([pos, p.tH[b + 1]]); }
  });
  assert.ok(rec && rec.motion && rec.motion.deg > 0, "a full-level press deals a sweep");
  const span = (a, b) => { const xs = tilts.filter(([pos]) => pos >= a && pos < b).map((x) => x[1]); return Math.max(...xs) - Math.min(...xs); };
  assert.ok(span(4.5, 8) > 1, `it sweeps with room: ${span(4.5, 8).toFixed(2)} degrees`);
  assert.ok(span(8.05, 12) < 1e-6, `it stands still with no room: ${span(8.05, 12)}`);
  assert.ok(span(12.05, 16) > 1, `and moves on after: ${span(12.05, 16).toFixed(2)} degrees`);
  assert.ok(p.kick.gov.still > 90, `frames it stood still: ${p.kick.gov.still}`);
});

test("closed loop: rapid alternating full-level taps of both kicks for 3 s with the limiter's own headroom fed back -- the limiter never acts, every press lights", () => {
  for (const bpm of [128, 150]) {
    const g = locked(bpm), p = fresh({ look: "drop" });
    const lim = new FrameLimiter();
    let f = 0, presses = 0;
    for (let t = 0; t < 7000; t += 1000 / FPS, f++) {
      const pos = g.posAt(t);
      let room = 5;
      for (const pair of lim.trackers) for (const tr of pair) room = Math.min(room, 5 - tr.count(t / 1000));
      p.kick.headroom = room;
      if (f >= 120 && f < 300) {
        const q = f - 120, kind = Math.floor(q / 8) % 2 ? C : W;
        if (q % 8 === 0) { const r = p.pad(kind, 1, pos, { hold: true }); assert.ok(r, "every press lights"); presses++; }
        if (q % 8 === 4) p.padRelease(kind, pos);
      }
      p.tick(g, t, DT);
      // the frame, simplified: each live kick's area luminance on its own half of a 4 x 4 frame
      const lum = (card) => { const ms = members(card); return ms.reduce((s, [k, i]) => { const e = emitted(p, k, i); return s + 0.2126 * e[0] + 0.7152 * e[1] + 0.0722 * e[2]; }, 0) / ms.length; };
      const L = new Float64Array(16);
      for (const k of p.kick.list) { const v = Math.min(1, 3 * lum(k.card)), off = k.kind === W ? 0 : 8; for (let c = 0; c < 8; c++) L[off + c] = Math.max(L[off + c], v); }
      lim.step({ L, R: new Float64Array(16) }, t / 1000, DT);
    }
    assert.equal(p.kick.unlit, 0);
    assert.equal(lim.stats().interventions, 0, `${bpm} BPM: the limiter acted on ${lim.stats().interventions} frames (${presses} presses; held back ${JSON.stringify(p.kick.gov)})`);
  }
});
