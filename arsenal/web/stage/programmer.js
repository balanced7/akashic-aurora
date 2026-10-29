// Virtual Stage v0, the programmer: arsenal/web/stage/programmer.js (pure ES module). Tests: tests/stage_programmer.test.mjs.
//
// What a lighting console does every frame, in the design's order (section 3.2), for the v0 rig:
//   1. the LOOK (the running section's cue): base values per group (Dimmer, Pan, Tilt, Zoom, Color, Color2) and the
//      effects it runs; a new look crossfades its dimmers over its fade (beats) and starts / stops effects with their own
//      fade-in and fade-out, so nothing snaps;
//   2. the EFFECTS (effects.js), in the look's line order, on the group's members;
//   3. the PLAYBACKS on top (pads): KICK is a flash playback, merged HTP (highest takes precedence) on Dimmer; FLY-OUT is a
//      one-shot that adds an outward tilt and a dimmer pop, its delay spread by distance from the centre;
//   4. the MASTERS: the strand (F1), the beams (everything else with a lens), the pixels, the grand master (F9);
//   5. COLOUR: theme roles (A, B, W, beamA, beamB) resolve to linear RGB; a wheel fixture snaps to the nearest of its 14
//      slots, and its wheel turns at its real speed (0.12 s per slot), so a far colour change runs past the colours between;
//      saturated red (R / (R + G + B) >= 0.8) is never the result of an effect that pulses (the theme refuses red roles);
//   6. PHYSICS: every attribute follows its target no faster than its motor (velocity = range / real_fade, acceleration =
//      velocity / real_accel, from the type's attribute table); snap attributes (wheel slots) jump.
// The output is the design's FrameState: heads (16 floats each: pan, tilt, dimmer, r, g, b, zoomDeg, frost, iris, gobo,
// goboRot, prism, prismRot, shutter, focus, flags) and pixels (4 floats each: r, g, b, a, linear, before each cell kind's
// luminance scale, which the renderer owns). Gobo, prism and frost are modelled at their home values and drawn in v1.
//
// v1 (2026-10-25): the PHRASE LAYER (phrases.js plays it). A phrase step is an overlay over the section's look, merged
// latest-takes-precedence member by member and attribute by attribute: the attributes a step's lines name (values, a
// position preset's pan and tilt, the attributes its effects drive) come from the step; everything else stays the look's.
// Dimmers crossfade from what was showing over a line's fade (beats); the step's effects are anchored on its ONE and
// ignore the speed fader (a cue counts beats). The FLASHGATE grants at most one horizontal flash per bar: a granted flash
// rises in one frame and decays over at least half a beat to its hold; a refused one becomes a lift over an eighth of a
// beat. clearOverlay() hands the fixtures back to the look over a fade.
//
// v2 (2026-10-27): a ring formation's light (formations.js) is one more layer after the phrase layer (setLayer), and
// while a ring is off its home pose the phrase layer's position presets are re-aimed on the live rig (setLiveElements).
// Both go through the same physics: a re-aimed head still turns no faster than its motor.

//
// KICK v2 (2026-10-27): the kicks are their own module (kick.js) and this file's step 3 runs them: two buttons
// (kick-white, kick-colour), each dealing a row of the set's deck that will show the hit now, lit at a live level while
// held, with velocity's animation (a peak, or a sweep from the V2 motion library) and a strobe in the level's top band.
// Without a kick block in the set it is v0's strand lift, number for number.

//
// PALETTES (2026-10-28, arsenal/web/palettes.js; research/in-flight/palettes-2026-10-28/DESIGN.md): one active palette
// drives every colour. The roles gain the split and pin roles (accent, accent2, accentLift, pin); a theme built from a
// palette (palettes.js stageTheme) carries the palette, and from it the programmer takes
//   - the moving heads' WHEEL PLAN: a head shows only the palette's slots (white, rest, alt, the lifts), never the wheel's
//     warm white unless the palette declares it, and every wheel move takes the red-free short way, snapping while the
//     head is dark (a move in black) -- a look change no longer slews a lit head through the red slot;
//   - the SPLITS and PINS: a split's groups show the palette's second family (accent, accent2: a strand wing, the rims, the
//     tower strips) and never cross-fade into the bed; a pin's cells hold their colour and follow the scene's level slowly
//     (never kicked, chased, strobed or flashed); a split's heads rest on their own slot (Lime Rows' lime rows);
//   - the 3-STOP STRANDS (Lantern Walk, Aurora): an A/B pair on a bed cell is sampled from the palette's strand gradient
//     (OKLCh, 32 samples) instead of a two-colour lerp; two-stop strands keep the linear mix that made the loved helix;
//   - the TEMPO: the strand's helix and the ring ladder turn at the palette's own rate (drive, slow, raw, still, walk), in
//     beats; Lantern Walk's bed walks one stop per 16-bar phrase;
//   - the SWITCH: beginPalette() lands a new palette on a beat position -- a neighbour crossfades its roles in OKLCh over
//     the given beats, anything else cuts on the line through a one-beat dip (the rig dims to black and back, the colours
//     and the wheels change at the bottom, in the dark).
// A theme without a palette (the set's own themes, the tests') resolves as before and takes the same kick rules from its
// own roles (bumpB the lift of a base cell, bumpA of a partner cell, W the white kick).

import { EffectInstance, hashSeed } from "./effects.js";
import { hexToLinear } from "./lasers.js";
import { aimPreset } from "./phrases.js";
import { Kicks, redSlots, wheelWay, wayLumaClean as wayLumaCleanKick } from "./kick.js";
import { STAGE_ROLES, planOf, tableOf, sampleTable, mixLch, isSaturatedRed, deOK, lchOfLin, hueGap, mixLin } from "../palettes.js";

export const PROGRAMMER_API = "arsenal.stage-programmer/v1";
export const HEAD_FLOATS = 16;
export const H = Object.freeze({ PAN: 0, TILT: 1, DIM: 2, R: 3, G: 4, B: 5, ZOOM: 6, FROST: 7, IRIS: 8, GOBO: 9, GOBOROT: 10,
  PRISM: 11, PRISMROT: 12, SHUTTER: 13, FOCUS: 14, FLAGS: 15 });
const ROLES = STAGE_ROLES.slice();
export const ROLE_NAMES = ROLES;
export const ROLE = Object.freeze(Object.fromEntries(ROLES.map((r, i) => [r, i])));
// how a split's cells show the look's roles (the palette's second family, never the bed): a strand wing's cells take the
// accent pair; a pin's cells take the pin
const REMAP_SPLIT = Object.freeze({ A: "accent", B: "accent2", W: "W", beamA: "accent", beamB: "accent2", warm: "accentLift", bumpA: "accentLift",
                                     bumpB: "accent", accent: "accent", accent2: "accent2", accentLift: "accentLift", pin: "pin" });
export const CELL_KIND = Object.freeze({ BED: 0, ACCENT: 1, PIN: 2 });
// the colour kick's LIFT: what each role becomes on a colour kick (swap 0), and on the re-strike that swaps the ladder
// (swap 1). bumpB is the palette's kick colour and bumpA its highlight (palettes.js stageTheme), so a base cell lifts into
// the partner's family and a partner cell to the highlight; a split's cells lift to accentLift; a pin is never lifted.
export const LIFT = Object.freeze([
  Object.freeze({ A: "bumpB", W: "bumpB", beamA: "bumpB", warm: "bumpB", bumpA: "bumpB", B: "bumpA", beamB: "bumpA", bumpB: "bumpA",
                  accent: "accentLift", accent2: "accentLift", accentLift: "accentLift", pin: "pin" }),
  Object.freeze({ A: "bumpA", W: "bumpA", beamA: "bumpA", warm: "bumpA", bumpA: "bumpA", B: "bumpB", beamB: "bumpB", bumpB: "bumpB",
                  accent: "accentLift", accent2: "accentLift", accentLift: "accentLift", pin: "pin" }),
]);
const roleIdx = (map) => Int16Array.from(ROLES, (r) => ROLES.indexOf(map[r] ?? r));
const REMAP_IDX = [null, roleIdx(REMAP_SPLIT), Int16Array.from(ROLES, () => ROLES.indexOf("pin"))];
export const LIFT_IDX = Object.freeze([roleIdx(LIFT[0]), roleIdx(LIFT[1])]);
// THE COLOUR BANK (KICK round 3, 2026-10-29; the design is kick.js's header). Daniel: "pressing 5 never seems to change the
// full stage worth of lights, just a few accent lights. I want 5 to change light groups using a palate across all the
// elements". A bank is the palette's colours dealt to every light group: the CYCLE is the palette's own colour roles (bed,
// partner, highlight, kick colour and the split's accents; never the white, the warm white, the air or a pin), each kept
// once, in the order that moves every step furthest in hue (a cell's both roles and the midpoint of a helix); each group
// stands at its own place on the cycle, and a role shows the cycle's colour BANK_ORD[role] places on from there. A press of
// kick 5 steps every group one place: every group changes colour, every press. The moving heads alternate between the two
// slots of their pair (one clean wheel slot apart, never red). Pins hold.
export const BANK_ROLES = Object.freeze(["A", "B", "bumpA", "bumpB", "accent", "accent2", "accentLift"]);
export const BANK_ORD = Object.freeze({ A: 0, beamA: 0, accent: 0, bumpB: 1, B: 2, beamB: 2, accent2: 2, W: 2, warm: 2, bumpA: 3, accentLift: 3 });
// the rig groups the bank deals, in this order (each member to the first that names it; the kick deck's rows, every light)
export const BANK_GROUPS = Object.freeze(["rings.slats", "rings.rims", "truss.heads", "lip.heads", "vert", "vert.strips", "delay.30", "delay.55",
                                          "halo", "strand.heads", "strand.cubes", "strand.dots", "strand.bars"]);
const BANK_SAME = 0.05;
const BANK_GREY = 0.04;                   // OKLCh chroma under this: a white or a grey (no bank colour unless the bed is grey)
const BANK_PASTEL = 0.6;                  // a role under this share of the cycle's most colourful chroma is a pastel
const BANK_TWIN_DEG = 10;                 // ... and a washed-out twin when a more colourful role is this close in hue
// a role's place on from its group's (near: the partner roles one place on instead of two)
const ordOf = (r, near = 0) => { const o = BANK_ORD[ROLES[r]] ?? 1; return near && o === 2 ? 1 : o; };                   // two roles closer than this (dEOK) are one colour of the cycle
const BANK_ENGAGE_DE = 0.08;              // the first bank moves a group's colours at least this far from the look's
// the colour effects the palette's tempo drives (the strand's helix, the ring ladder), and how long a pin takes to follow
// the scene's level (seconds): slow enough that no chase, strobe or flash shows in it
const TEMPO_EFFECTS = Object.freeze({ "cube-colour": "strand", "ring-colour": "ring" });
const PIN_TAU_S = 1.2;
export const PALETTE_DIP_BEATS = 1;
export const FLASH_MIN_DECAY_BEATS = 0.5;
export const FLASH_LIFT_BEATS = 0.125;

// One flash per bar at most (0.6 a second at 150 BPM): a grant needs minBeats since the last one.
export class FlashGate {
  constructor({ minBeats = 4 } = {}) { this.minBeats = minBeats; this.last = -Infinity; this.grants = []; this.refusals = []; }
  request(pos) {
    const ok = pos - this.last >= this.minBeats - 1e-6;
    if (ok) { this.last = pos; if (this.grants.length < 512) this.grants.push(+pos.toFixed(4)); }
    else if (this.refusals.length < 512) this.refusals.push(+pos.toFixed(4));
    return ok;
  }
}

// ------------------------------------------------------------------------------------------------- physics --
// A slew-limited follower: velocity at most vmax, acceleration at most amax, braking in whole frames so it stops ON the
// target (no overshoot, no snap): each step takes the fastest speed toward the target from which a frame-by-frame
// deceleration of amax dt still lands exactly there.
export class Slew {
  constructor(x = 0, vmax = 1, amax = 10) { this.x = x; this.v = 0; this.vmax = vmax; this.amax = amax; }
  step(target, dt) {
    if (!(dt > 0)) return this.x;
    const d = target - this.x, sg = d < 0 ? -1 : 1, D = Math.abs(d), ad = this.amax * dt;
    if (D < 1e-9 && Math.abs(this.v) <= ad) { this.x = target; this.v = 0; return this.x; }
    // the distance a speed v still covers while braking by ad each frame: dt (v - ad) + dt (v - 2 ad) + ...
    const brake = (v) => { if (v <= ad) return 0; const m = Math.floor(v / ad); return dt * (m * v - (ad * m * (m + 1)) / 2); };
    const ok = (v) => v * dt + brake(v) <= D + 1e-12;
    const vc = this.v * sg;
    let lo = Math.max(-this.vmax, vc - ad), hi = Math.min(this.vmax, vc + ad), v;
    if (ok(hi)) v = hi;
    else if (!ok(lo)) v = lo;                       // the target jumped closer than we can stop: brake as hard as allowed
    else { for (let i = 0; i < 24; i++) { const mid = (lo + hi) / 2; if (ok(mid)) lo = mid; else hi = mid; } v = lo; }
    this.v = v * sg;
    this.x += this.v * dt;
    return this.x;
  }
}
export function slewFor(attr, x0 = 0) {
  const range = (attr.max ?? 1) - (attr.min ?? 0);
  const vmax = range / (attr.real_fade ?? 0.1);
  const amax = vmax / (attr.real_accel ?? 0.05);
  return new Slew(x0, vmax, amax);
}

// ----------------------------------------------------------------------------------------- the theme's colours --
// The roles as linear rgb. The red test is the house rule as the VJ library has it (encoded OR linear R / (R + G + B) at
// 0.8 or more); a pin is HELD (never pulsed), so it is not thrown on. A theme without the split roles shows its bed there
// (accent = A, accent2 = B, accentLift = bumpA) and its white as the pin.
export function resolveTheme(theme) {
  const out = {};
  const fallback = { accent: "A", accent2: "B", accentLift: "bumpA", pin: "W" };
  for (const r of ROLES) out[r] = theme && theme[r] ? hexToLinear(theme[r]) : null;
  for (const r of ROLES) if (!out[r]) out[r] = fallback[r] && out[fallback[r]] ? out[fallback[r]].slice() : [1, 1, 1];
  for (const r of ROLES) if (r !== "pin" && isSaturatedRed(out[r])) throw new Error(`theme ${theme && theme.name}: role ${r} is saturated red (held, never pulsed)`);
  out.laser = (theme && theme.laser) || ["#19ff4a", "#4a3cff", "#e6ffe9"];
  return out;
}
// the wheel slot nearest a colour (squared distance on chromaticity, then brightness); allowed: the slots it may pick
export function nearestSlot(wheel, rgb, allowed = null) {
  const n = (c) => { const s = c[0] + c[1] + c[2] || 1; return [c[0] / s, c[1] / s, c[2] / s]; };
  const q = n(rgb);
  let best = allowed && allowed.length ? allowed[0] : 0, bd = Infinity;
  const one = (i) => {
    const p = n(wheel[i]);
    const d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2;
    if (d < bd - 1e-12) { bd = d; best = i; }
  };
  if (allowed && allowed.length) for (const i of allowed) one(i);
  else for (let i = 0; i < wheel.length; i++) one(i);
  return best;
}

// ------------------------------------------------------------------------------------------------- the bank --
// The bank's CYCLE for a theme's role colours (roleRGB, linear, in ROLES order): role indices, each colour once. Of every
// order (the bed first) the one whose smallest step is largest (OKLab distance): a step is what a cell shows before and
// after a press -- a role's colour moving to the next on the cycle, and the midpoint of a cell between two roles one or two
// places apart moving to the next pair's (the helix, the slats' two-colour cells); between orders as good, the one whose
// steps move the hue most.
export function bankCycle(roleRGB) {
  let cand = [];
  // (review V6, 2026-10-29: a near-white or pastel role on the bed washed whole groups out -- Molten's bank 3 took the
  // cubes and rings from amber to cream -- and swung the stage's light up to 9.6 x across the cycle, S2.) In a palette
  // whose bed has a colour, a role of OKLCh chroma under BANK_GREY (a white by another name: Synthwave Dusk's #fdf1fc,
  // Leviathan Royal's #f8f5fe) is no bank colour, and while more than three remain the palest washed-out twin goes (never
  // the bed or its partner: they are the palette). A palette whose bed is grey (Noir, Titanium, Moon Hive) keeps its greys.
  const chroma = (r) => lchOfLin(roleRGB[r]).C, greyBed = roleRGB[ROLE.A] && chroma(ROLE.A) < BANK_GREY;
  for (const name of BANK_ROLES) {
    const r = ROLE[name], c = roleRGB[r];
    if (!c || isSaturatedRed(c)) continue;
    if (!greyBed && chroma(r) < BANK_GREY) continue;
    if (cand.some((x) => deOK(roleRGB[x], c) < BANK_SAME)) continue;
    cand.push(r);
  }
  if (!greyBed) {
    const cmax = Math.max(0, ...cand.map(chroma));
    while (cand.length > 3) {
      let lo = -1;
      // (a pastel: under BANK_PASTEL of the most colourful's chroma, with a more colourful role within BANK_TWIN_DEG of
      // its hue -- a washed-out twin that adds no hue of its own, like Molten's peach #ffcc9e beside its amber bed)
      const twin = (j) => cand.some((x, k) => k !== j && chroma(x) > chroma(cand[j]) && hueGap(lchOfLin(roleRGB[x]).h, lchOfLin(roleRGB[cand[j]]).h) <= BANK_TWIN_DEG);
      for (let j = 0; j < cand.length; j++) if (cand[j] !== ROLE.A && cand[j] !== ROLE.B && chroma(cand[j]) < BANK_PASTEL * cmax && twin(j) && (lo < 0 || chroma(cand[j]) < chroma(cand[lo]))) lo = j;
      if (lo < 0) break;
      cand = cand.filter((_, j) => j !== lo);
    }
  }
  if (cand.length < 2) return cand;
  const hue = (x, y) => { const a = lchOfLin(x), b = lchOfLin(y); return a.C >= 0.04 && b.C >= 0.04 ? hueGap(a.h, b.h) : 0; };
  const score = (ord) => {
    const n = ord.length, c = ord.map((r) => roleRGB[r]);
    let lo = Infinity, sum = 0;
    for (let i = 0; i < n; i++) {
      const pairs = [[c[i], c[(i + 1) % n]]];
      for (const d of n >= 3 ? [1, 2] : []) pairs.push([mixLin(c[i], c[(i + d) % n], 0.5), mixLin(c[(i + 1) % n], c[(i + 1 + d) % n], 0.5)]);
      for (const [x, y] of pairs) { lo = Math.min(lo, deOK(x, y)); sum += hue(x, y); }
    }
    // and an order with a place where a bed/partner gradient takes two new colours (not its own two, not swapped: with
    // three colours only one of the two mirror orders has it) goes first
    let fresh = 0;
    for (let i = 0; i < n; i++) { const x = ord[i], y = ord[(i + 2) % n]; if (x !== ROLE.A && y !== ROLE.B && !(x === ROLE.B && y === ROLE.A)) fresh = 1; }
    return fresh * 1e9 + lo * 1e5 + sum;
  };
  let best = cand.slice(), bs = score(best);
  const rest = cand.slice(1), used = new Array(rest.length).fill(false), cur = [cand[0]];
  const walk = () => {
    if (cur.length === cand.length) { const s = score(cur); if (s > bs + 1e-9) { bs = s; best = cur.slice(); } return; }
    for (let j = 0; j < rest.length; j++) if (!used[j]) { used[j] = true; cur.push(rest[j]); walk(); cur.pop(); used[j] = false; }
  };
  walk();
  return best;
}
// A head's PAIR of wheel slots for the bank, both on the palette's plan (never red, never pink, never the warm white): the
// palette's rest and alt when they are neighbours on the wheel, else the rest and its lift, else the alt and its lift, else
// the rest and the alt as they are (the palettes whose heads rest on white: Rose Fans, Moon Hive, Titanium, Noir); the head
// alternates between the two on every press. A pair one slot apart turns at the wheel's speed, lit; a pair further apart
// is never run lit through the slots between (they are off the plan): the head takes its new slot in black (programmer
// tick, the wheel).
export function bankPair(wheel, rest, alt, lift, { red = [] } = {}) {
  const n = wheel.length, adj = (a, b) => ((a - b + n) % n === 1 || (b - a + n) % n === 1);
  const ok = (x) => x >= 0 && x < n && !red.includes(x);
  if (ok(rest) && ok(alt) && adj(rest, alt)) return [rest, alt];
  const lr = lift && lift.get(rest), la = lift && lift.get(alt);
  if (lr && ok(rest) && ok(lr.to) && adj(rest, lr.to)) return [rest, lr.to];
  if (la && ok(alt) && ok(la.to) && adj(alt, la.to)) return [alt, la.to];
  return ok(alt) && alt !== rest ? [rest, alt] : [rest, rest];
}

// --------------------------------------------------------------------------------------------- the programmer --
export class Programmer {
  constructor(rig, { theme = null, seed = null } = {}) {
    this.rig = rig;
    this.seed = seed ?? rig.seed;
    this.nH = rig.heads.length;
    this.nC = rig.cells.n;
    this.heads = new Float32Array(this.nH * HEAD_FLOATS);
    this.pixels = new Float32Array(this.nC * 4);
    // targets before physics: per head pan, tilt, dimmer, zoom, mix, role, role2; per cell dimmer, mix, role, role2
    this.tH = new Float64Array(this.nH * 7);
    this.tC = new Float64Array(this.nC * 4);
    this.baseH = new Float64Array(this.nH * 7); this.fromH = new Float64Array(this.nH * 7);
    this.baseC = new Float64Array(this.nC * 4); this.fromC = new Float64Array(this.nC * 4);
    this.fade = { p0: 0, len: 0 };
    this.masters = { grand: 1, strand: 1, beams: 1, pixels: 1 };
    this.speed = 1;
    this.effects = new Map();      // "group:effect" -> EffectInstance
    this.lines = [];
    this.pads = [];                // running playbacks {kind, onset, vel}
    this.lookName = "";
    // a head no look has named yet shows the palette's rest slot (beamA, beamB), never role 0's nearest slot
    for (let i = 0; i < this.nH; i++) { this.baseH[i * 7 + 5] = this.fromH[i * 7 + 5] = ROLE.beamA; this.baseH[i * 7 + 6] = this.fromH[i * 7 + 6] = ROLE.beamB; }
    // the head's type data: attributes, wheel colours
    this.headType = rig.heads.map((fi) => rig.types[rig.fixtures[fi].type]);
    this.strandHead = rig.heads.map((fi) => rig.elements[rig.fixtures[fi].element].id === "rung");
    // FLY-OUT bursts the truss and lip beams (the show's flyout_groups, if it names them; else every head off the strand,
    // which in v0 is the same truss and lip): never the halo or the verticals a phrase is placing
    const fg = (rig.show && rig.show.flyout_groups) || ["truss.heads", "lip.heads"];
    const named = fg.filter((n) => rig.groups[n] && rig.groups[n].kind === "heads");
    this.flyoutHead = new Uint8Array(rig.heads.length);
    if (named.length) { for (const n of named) for (const k of rig.groups[n].members) this.flyoutHead[k] = 1; }
    else for (let i = 0; i < rig.heads.length; i++) this.flyoutHead[i] = this.strandHead[i] ? 0 : 1;
    this.strandCell = new Uint8Array(this.nC);
    for (let c = 0; c < this.nC; c++) this.strandCell[c] = rig.elements[rig.cells.element[c]].id === "rung" ? 1 : 0;
    this.slews = this.headType.map((t) => ({
      pan: slewFor(t.attrs.Pan || { min: -270, max: 270, real_fade: 2.2, real_accel: 0.2 }),
      tilt: slewFor(t.attrs.Tilt || { min: -135, max: 135, real_fade: 1.4, real_accel: 0.2 }),
      dim: slewFor(t.attrs.Dimmer || { min: 0, max: 1, real_fade: 0.08, real_accel: 0.02 }),
      zoom: slewFor(t.attrs.Zoom || { min: 0.5, max: 4, real_fade: 0.6, real_accel: 0.1 }, (t.attrs.Zoom && t.attrs.Zoom.home) ?? 2),
      wheel: new Slew(0, 1 / ((t.attrs.Color1 && t.attrs.Color1.slot_time) || 0.12), 1e6),
    }));
    this.wheels = this.headType.map((t) => (t.attrs.Color1 && t.attrs.Color1.colours ? t.attrs.Color1.colours.map(hexToLinear) : null));
    // each head's zoom range and home (degrees). A look that leaves Zoom unset holds 0 in its targets, which means HOME;
    // KICK v2 round 2 found a phrase's release crossfading the halo's zoom from 1.2 toward that literal 0, a 0-degree beam
    // (an infinitely narrow, infinitely bright line, below the fixture's 0.5-degree end stop) that only showed once a kick
    // lit the dark halo. The release now blends toward the home, and every zoom target stays inside the fixture's range.
    const zA = (t) => t.attrs.Zoom || { min: 0.5, max: 4, home: 2 };
    this.zoomMin = Float64Array.from(this.headType, (t) => zA(t).min ?? 0.5);
    this.zoomMax = Float64Array.from(this.headType, (t) => zA(t).max ?? 4);
    this.zoomHome = Float64Array.from(this.headType, (t) => zA(t).home ?? 2);
    // KICK v2 round 2: a kick may own a head's wheel (kickSlot: the slot it wants, -1 none; wheelOwn: 1 while it does, and
    // until the wheel is back on the look's slot after it). PALETTES: every wheel move, the look's too, turns the shortest
    // way round that passes no saturated-red slot (wheelPos, at the wheel's real speed), and snaps while the head is dark
    this.redSlotsByType = new Map();
    this.kickSlot = new Int16Array(this.nH).fill(-1);
    this.wheelOwn = new Uint8Array(this.nH);
    this.wheelPos = new Float64Array(this.nH).fill(-1);
    this.wheelWait = new Float64Array(this.nH).fill(-1);
    // KICK 5's move in black (review V1, 2026-10-29): a lit head the bank sends further than one clean slot (the palettes
    // whose heads rest on white: white and a colour far apart on the wheel) has its dimmer taken to black (bankDip 1) until
    // it is dark, the wheel moves there, and the dimmer comes back -- in Noir and Titanium the lit beams otherwise kept their
    // colour for good, since no look ever takes them dark
    this.bankDip = new Uint8Array(this.nH);
    // PALETTES: the members' place in the palette (a split's or a pin's cells, a split's heads and their own wheel plan),
    // the colour kick's light on each cell (kickC: r, g, b and its weight, written by kick.js each frame), a pin's held level
    this.cellKind = new Uint8Array(this.nC);
    this.headSlotOv = new Int16Array(this.nH).fill(-1);
    this.headLift = new Array(this.nH).fill(null);
    this.kickC = new Float32Array(this.nC * 4);
    this.pinDim = new Float32Array(this.nC);
    this.palX = null; this.dipLevel = 1; this.paletteEvents = [];
    this.tempoMeasure = {};
    this.roleRGB = [];
    // THE COLOUR BANK: each member's bank group (-1: none, a pin), the groups' places on the cycle, the heads' pairs and the
    // slot the bank has a head on (-1: the look's), the cells' roles before the bank (kick.js judges the next bank with them)
    this.bankG = { names: [], cellG: new Int16Array(this.nC).fill(-1), headG: new Int16Array(this.nH).fill(-1) };
    for (const gname of BANK_GROUPS) {
      const g = rig.groups[gname];
      if (!g) continue;
      const gi = this.bankG.names.push(gname) - 1;
      for (let m = 0; m < g.n; m++) {
        const k = g.members[m];
        if (g.kind === "cells" && this.bankG.cellG[k] < 0) this.bankG.cellG[k] = gi;
        else if (g.kind === "heads" && this.bankG.headG[k] < 0) this.bankG.headG[k] = gi;
      }
    }
    // a member none of them names (another set's rig) still takes the bank, in a group of its own
    const extra = this.bankG.names.length;
    let anyExtra = false;
    for (let c = 0; c < this.nC; c++) if (this.bankG.cellG[c] < 0) { this.bankG.cellG[c] = extra; anyExtra = true; }
    for (let i = 0; i < this.nH; i++) if (this.bankG.headG[i] < 0) { this.bankG.headG[i] = extra; anyExtra = true; }
    if (anyExtra) this.bankG.names.push("other");
    const nG = this.bankG.names.length;
    this.bank = { on: false, count: 0, serial: 0, cycle: [], idx: new Int32Array(nG), near: new Uint8Array(nG), maps: Array.from({ length: nG }, () => new Int16Array(ROLES.length)),
                  pairs: new Array(this.nH).fill(null), slot: new Int16Array(this.nH).fill(-1), log: [] };
    this.bankOrigC = new Int16Array(this.nC * 2);
    this.setTheme(theme || Object.values(rig.themes)[0] || null);
    this.stats = { kicks: [], flyouts: 0, lookChanges: 0, overlays: 0 };
    // the phrase layer
    const nH = this.nH, nC = this.nC;
    this.ov = { active: false, release: null, lines: [], p0: 0 };
    this.ovSetH = new Uint8Array(nH * 7); this.ovBaseH = new Float64Array(nH * 7); this.ovFromH = new Float64Array(nH * 7);
    this.ovTH = new Float64Array(nH * 7); this.ovOnH = new Uint8Array(nH); this.ovFadeH = new Float64Array(nH); this.ovP0H = new Float64Array(nH);
    this.ovSetC = new Uint8Array(nC * 4); this.ovBaseC = new Float64Array(nC * 4); this.ovFromC = new Float64Array(nC * 4);
    this.ovTC = new Float64Array(nC * 4); this.ovOnC = new Uint8Array(nC); this.ovFadeC = new Float64Array(nC); this.ovP0C = new Float64Array(nC);
    this.flashGate = new FlashGate();
    // KICK v2 (kick.js): reads the beat's length and the bar line the last tick saw
    this.perMs = 400; this.barAnchor = 0;
    this.kick = new Kicks(this);
  }
  // ---------------------------------------------------------------------------------------------- phrase layer --
  // lines: compiled phrase lines (phrases.js compileRepeat): {g, kind, values, positions, effects [{id, def}], fade,
  // flash}. replace: a new step (the previous step's lines go); otherwise a cue inside the step, merged on top.
  // positionsOnly (the pre-roll, before a phrase starts): only the pan and tilt of heads that are dark now, so heads move
  // in black to where the phrase will need them and nothing lit moves.
  setOverlay(lines, pos, { replace = true, positionsOnly = false } = {}) {
    if (positionsOnly) return this._preroll(lines, pos);
    const nH = this.nH, nC = this.nC;
    this.ovFromH.set(this.tH); this.ovFromC.set(this.tC);       // what each member showed in the last frame
    if (replace) {
      this.ovSetH.fill(0); this.ovSetC.fill(0); this.ovOnH.fill(0); this.ovOnC.fill(0);
      this.ov.lines = [];
    }
    const OFF = { Pan: 0, Tilt: 1, Dimmer: 2, Zoom: 3, ColorMix: 4 }, OFFC = { Dimmer: 0, ColorMix: 1 };
    if (!replace) {
      // a cue is newer than the step's lines: the members it names leave the older lines' effects (latest takes precedence)
      const named = { heads: new Set(), cells: new Set() };
      for (const L of lines) if (L && L.g && L.kind !== "lasers") for (let m = 0; m < L.g.n; m++) named[L.g.kind]?.add(L.g.members[m]);
      for (const old of this.ov.lines) {
        const set = named[old.g.kind];
        if (!set || !set.size) continue;
        for (let m = 0; m < old.g.n; m++) if (set.has(old.g.members[m])) old.mask[m] = 0;
      }
    }
    for (const L of lines) {
      if (!L || L.kind === "lasers" || !L.g) continue;
      const g = L.g, v = L.values || {};
      const effects = (L.effects || []).map((e) => new EffectInstance(e.id, e.def, g, { seed: hashSeed(this.seed, e.id), pos, anchorPos: pos }));
      const driven = new Set(effects.flatMap((e) => e.def.attrs || []));
      for (let m = 0; m < g.n; m++) {
        const k = g.members[m];
        if (g.kind === "heads") {
          const b = k * 7;
          const set = (j, val) => { this.ovSetH[b + j] = 1; this.ovBaseH[b + j] = val; };
          // a preset's position, then any explicit Pan / Tilt over it (a line can park a head off the preset in black)
          if (L.positions) { set(0, L.positions[m * 2]); set(1, L.positions[m * 2 + 1]); }
          if (v.Pan !== undefined) set(0, v.Pan);
          if (v.Tilt !== undefined) set(1, v.Tilt);
          if (v.Dimmer !== undefined) set(2, v.Dimmer);
          if (v.Zoom !== undefined) set(3, v.Zoom);
          if (v.ColorMix !== undefined) set(4, v.ColorMix);
          if (v.Color !== undefined) set(5, Math.max(0, ROLES.indexOf(v.Color)));
          if (v.Color2 !== undefined) set(6, Math.max(0, ROLES.indexOf(v.Color2)));
          for (const a of driven) if (OFF[a] !== undefined && !this.ovSetH[b + OFF[a]]) set(OFF[a], this.tH[b + OFF[a]]);
          this.ovOnH[k] = 1; this.ovFadeH[k] = L.fade || 0; this.ovP0H[k] = pos;
        } else if (g.kind === "cells") {
          const b = k * 4;
          const set = (j, val) => { this.ovSetC[b + j] = 1; this.ovBaseC[b + j] = val; };
          if (v.Dimmer !== undefined) set(0, v.Dimmer);
          if (v.ColorMix !== undefined) set(1, v.ColorMix);
          if (v.Color !== undefined) set(2, Math.max(0, ROLES.indexOf(v.Color)));
          if (v.Color2 !== undefined) set(3, Math.max(0, ROLES.indexOf(v.Color2)));
          for (const a of driven) if (OFFC[a] !== undefined && !this.ovSetC[b + OFFC[a]]) set(OFFC[a], this.tC[b + OFFC[a]]);
          this.ovOnC[k] = 1; this.ovFadeC[k] = L.fade || 0; this.ovP0C[k] = pos;
        }
      }
      const flash = L.flash ? { onset: pos + (L.flash.at || 0), to: L.flash.to ?? 1, base: v.Dimmer ?? 0,
                                decay: Math.max(FLASH_MIN_DECAY_BEATS, L.flash.decay_beats ?? FLASH_MIN_DECAY_BEATS), state: "wait" } : null;
      // a position preset (no explicit Pan/Tilt over it) is re-aimed each frame while the rig is live (setLiveElements)
      const aim = L.prepared && L.prepared.kind !== "values" && g.kind === "heads" && v.Pan === undefined && v.Tilt === undefined
        ? { prepared: L.prepared, buf: new Float64Array(g.n * 2), hints: L.positions ? Float64Array.from(L.positions) : null } : null;
      this.ov.lines.push({ g, effects, flash, mask: new Uint8Array(g.n).fill(1), aim });
    }
    this.ov.active = true; this.ov.preroll = false; this.ov.release = null; this.ov.p0 = pos;
    this.stats.overlays++;
  }
  _preroll(lines, pos) {
    if (this.ov.active && !this.ov.preroll) return;          // a phrase already owns the rig
    this.ovSetH.fill(0); this.ovSetC.fill(0); this.ovOnH.fill(0); this.ovOnC.fill(0);
    this.ov.lines = [];
    let n = 0;
    for (const L of lines) {
      if (!L || L.kind !== "heads" || !L.positions) continue;
      const g = L.g;
      for (let m = 0; m < g.n; m++) {
        const k = g.members[m], b = k * 7;
        if (this.tH[b + 2] > 0.01) continue;                 // lit now: it stays where the look has it
        this.ovSetH[b] = 1; this.ovBaseH[b] = L.positions[m * 2];
        this.ovSetH[b + 1] = 1; this.ovBaseH[b + 1] = L.positions[m * 2 + 1];
        this.ovOnH[k] = 1; this.ovFadeH[k] = 0; this.ovP0H[k] = pos;
        n++;
      }
    }
    this.ov.active = n > 0; this.ov.preroll = true; this.ov.release = null; this.ov.p0 = pos;
    this.stats.prerolls = (this.stats.prerolls || 0) + 1;
  }
  // Hand every overlaid fixture back to the look over `fade` beats from pos.
  clearOverlay(pos, fade = 0) {
    if (!this.ov.active) return;
    this.ov.release = { p0: pos, len: fade };
  }
  _flashLevel(fl, pos) {
    const age = pos - fl.onset;
    if (age < -1e-6) return 0;
    if (fl.state === "wait") fl.state = this.flashGate.request(fl.onset) ? "granted" : "refused";
    const attack = fl.state === "granted" ? 0 : FLASH_LIFT_BEATS;
    const a = Math.max(0, age);
    if (a < attack) return fl.base + (fl.to - fl.base) * (a / attack);
    const t = a - attack;
    return t >= fl.decay ? 0 : fl.base + (fl.to - fl.base) * (1 - t / fl.decay);
  }
  // v2: the live rig. emOf(elementIndex) -> that element's live matrix while some element (a ring) is off its home pose,
  // or null when the rig is home: the phrase layer's position presets are then re-aimed each frame (a world-locked aim
  // stays locked on the world while the ring under it tilts or turns), and the formation layer runs after the phrases.
  setLiveElements(emOf) { this.emOf = emOf || null; }
  // layer: {apply(tH, tC, pos)} -- the ring formations' light (formations.js), over the look and the phrase layer
  setLayer(layer) { this.layer = layer || null; }
  _reaim() {
    for (const L of this.ov.lines) {
      if (!L.aim) continue;
      aimPreset(this.rig, L.g, L.aim.prepared, this.emOf, L.aim.buf, { hints: L.aim.hints });
      L.aim.hints = L.aim.hints || new Float64Array(L.g.n * 2);
      L.aim.hints.set(L.aim.buf);
      for (let m = 0; m < L.g.n; m++) {
        if (!L.mask[m]) continue;
        const b = L.g.members[m] * 7;
        if (this.ovSetH[b]) this.ovBaseH[b] = L.aim.buf[m * 2];
        if (this.ovSetH[b + 1]) this.ovBaseH[b + 1] = L.aim.buf[m * 2 + 1];
      }
    }
  }
  _overlay(pos, ver) {
    const nH = this.nH, nC = this.nC, ov = this.ov;
    let w = 1;
    if (ov.release) {
      w = ov.release.len > 0 ? 1 - (pos - ov.release.p0) / ov.release.len : 0;
      if (w <= 0) { ov.active = false; ov.release = null; ov.lines = []; this.ovOnH.fill(0); this.ovOnC.fill(0); return; }
    }
    if (this.emOf) this._reaim();
    // 1. the step's base values, dimmers crossfading from what was shown
    for (let i = 0; i < nH; i++) {
      if (!this.ovOnH[i]) continue;
      const b = i * 7, fl = this.ovFadeH[i];
      const f = fl > 0 ? Math.min(1, Math.max(0, (pos - this.ovP0H[i]) / fl)) : 1;
      for (let j = 0; j < 7; j++) {
        if (!this.ovSetH[b + j]) { this.ovTH[b + j] = this.tH[b + j]; continue; }
        this.ovTH[b + j] = j === 2 ? this.ovFromH[b + j] + (this.ovBaseH[b + j] - this.ovFromH[b + j]) * f : this.ovBaseH[b + j];
      }
    }
    for (let c = 0; c < nC; c++) {
      if (!this.ovOnC[c]) continue;
      const b = c * 4, fl = this.ovFadeC[c];
      const f = fl > 0 ? Math.min(1, Math.max(0, (pos - this.ovP0C[c]) / fl)) : 1;
      for (let j = 0; j < 4; j++) {
        if (!this.ovSetC[b + j]) { this.ovTC[b + j] = this.tC[b + j]; continue; }
        this.ovTC[b + j] = j === 0 ? this.ovFromC[b + j] + (this.ovBaseC[b + j] - this.ovFromC[b + j]) * f : this.ovBaseC[b + j];
      }
    }
    // 2. the step's effects, in line order, on their own members; 3. the flash
    for (const L of ov.lines) {
      const g = L.g;
      for (const inst of L.effects) {
        inst.tick(pos, ver);
        const attrs = inst.def.attrs || [];
        for (let m = 0; m < g.n; m++) {
          if (!L.mask[m]) continue;
          const k = g.members[m];
          for (const a of attrs) {
            if (g.kind === "heads") {
              const off = a === "Pan" ? 0 : a === "Tilt" ? 1 : a === "Dimmer" ? 2 : a === "Zoom" ? 3 : a === "ColorMix" ? 4 : -1;
              if (off >= 0) this.ovTH[k * 7 + off] = inst.apply(a, this.ovTH[k * 7 + off], m);
            } else if (g.kind === "cells") {
              const off = a === "Dimmer" ? 0 : a === "ColorMix" ? 1 : -1;
              if (off >= 0) this.ovTC[k * 4 + off] = inst.apply(a, this.ovTC[k * 4 + off], m);
            }
          }
        }
      }
      if (L.flash) {
        const lv = this._flashLevel(L.flash, pos);
        if (lv > 0) for (let m = 0; m < g.n; m++) {
          if (!L.mask[m]) continue;
          const k = g.members[m];
          if (g.kind === "heads") this.ovTH[k * 7 + 2] = Math.max(this.ovTH[k * 7 + 2], lv);
          else if (g.kind === "cells") this.ovTC[k * 4] = Math.max(this.ovTC[k * 4], lv);
        }
      }
    }
    // 4. merged over the look (roles switch at the half-way point of a release)
    for (let i = 0; i < nH; i++) {
      if (!this.ovOnH[i]) continue;
      const b = i * 7;
      for (let j = 0; j < 7; j++) {
        if (!this.ovSetH[b + j]) continue;
        // (zoom: an unset look zoom, 0, is the head's home, and the blend runs toward that, never toward 0)
        const look = j === 3 && !(this.tH[b + 3] > 0) ? this.zoomHome[i] : this.tH[b + j];
        this.tH[b + j] = j >= 5 ? (w >= 0.5 ? this.ovTH[b + j] : this.tH[b + j]) : look + (this.ovTH[b + j] - look) * w;
      }
    }
    for (let c = 0; c < nC; c++) {
      if (!this.ovOnC[c]) continue;
      const b = c * 4;
      for (let j = 0; j < 4; j++) {
        if (!this.ovSetC[b + j]) continue;
        this.tC[b + j] = j >= 2 ? (w >= 0.5 ? this.ovTC[b + j] : this.tC[b + j]) : this.tC[b + j] + (this.ovTC[b + j] - this.tC[b + j]) * w;
      }
    }
  }
  // A theme now (no transition). The role array keeps its identity (the ring formations hold it by reference).
  setTheme(theme) {
    this.theme = theme;
    this.colours = resolveTheme(theme);
    this.roleRGB.length = 0;
    for (const r of ROLES) this.roleRGB.push(this.colours[r].slice());
    this.ownRoles = ROLES.map((r) => this.colours[r].slice());
    this._applyPalette(theme);
    this._bankReset();                                  // a new palette starts from its own colours; kick 5 deals its banks
    if (this.kick) this.kick.extendRoles();             // KICK v2's own colours ride after the theme's roles
  }
  // ------------------------------------------------------------------------------------------------ the bank --
  // the theme's cycle and the heads' pairs; the bank goes back to the palette's own colours (bank 0) until the next press
  _bankReset() {
    const B = this.bank;
    if (!B) return;
    B.cycle = bankCycle(this.roleRGB);
    const plan = this.plan;
    for (let i = 0; i < this.nH; i++) {
      const w = this.wheels[i];
      if (!w) { B.pairs[i] = null; continue; }
      const rest = this.headSlotOv[i] >= 0 ? this.headSlotOv[i] : plan ? plan.rest : nearestSlot(w, this.roleRGB[ROLE.beamA]);
      const alt = plan ? plan.alt : nearestSlot(w, this.roleRGB[ROLE.beamB]);
      B.pairs[i] = bankPair(w, rest, alt, this.headLift[i], { red: this.redSlotsOf(i) });
    }
    B.on = false; B.count = 0; B.serial++; B.idx.fill(0); B.near.fill(0); B.slot.fill(-1);
    if (this.bankDip) this.bankDip.fill(0);
  }
  // KICK 5: every group one place on round the cycle (the first press from the palette's own colours puts each group where
  // its colours move furthest from the look's), every head to the other slot of its pair. Lands on the next frame.
  bankAdvance(pos = null) {
    const B = this.bank, n = B.cycle.length;
    if (n < 2) return false;
    const nG = B.idx.length;
    if (!B.on) {
      // the first bank: each group at the place on the cycle where the fewest of its cells (sampled, weighted by level)
      // would show about the colour they show now (at their own mix: a cell half-way between two roles included)
      const cand = Array.from({ length: nG }, () => []);
      for (let c = 0; c < this.nC; c++) if (this.cellKind[c] !== CELL_KIND.PIN) cand[this.bankG.cellG[c]].push(c);
      const map = new Int16Array(ROLES.length), a = [0, 0, 0], b2 = [0, 0, 0], nR = ROLES.length;
      for (let g = 0; g < nG; g++) {
        const cells = cand[g], stride = Math.max(1, Math.floor(cells.length / 160));
        let bestI = g % n, bestNear = 0, bestCost = Infinity;
        // (with an odd number of colours a group may also show its partner role one place on instead of two: with three
        // colours a bed/highlight gradient and a bed/partner one cannot both take two new colours at one spread)
        for (let s = 0; s < n * (n % 2 ? 2 : 1); s++) {
          const i = (g + s) % n, near = s >= n ? 1 : 0;
          for (let r = 0; r < nR; r++) map[r] = B.cycle[(i + ordOf(r, near)) % n];
          let cost = 0, wsum = 0;
          const ma = [0, 0, 0], mb = [0, 0, 0];
          for (let m = 0; m < cells.length; m += stride) {
            const c = cells[m], o = c * 4, r1 = this.tC[o + 2] | 0, r2 = this.tC[o + 3] | 0, mx = Math.max(0, Math.min(1, this.tC[o + 1]));
            this.colourOfCell(c, r1, r2, mx, a);
            B.on = true;                                          // (the colour stage as the bank will run it)
            this.colourOfCell(c, r1 < nR ? map[r1] : r1, r2 < nR ? map[r2] : r2, mx, b2);
            B.on = false;
            const wt = 0.05 + Math.max(0, this.tC[o]);
            if (deOK(a, b2) < BANK_ENGAGE_DE) cost += wt;
            for (let j = 0; j < 3; j++) { ma[j] += a[j]; mb[j] += b2[j]; }
            wsum += wt;
          }
          // a gradient whose two colours only swap ends (a helix mirrored) reads as no change: the group's mean must move
          const cnt = Math.ceil(cells.length / stride);
          if (cnt && deOK(ma.map((x) => x / cnt), mb.map((x) => x / cnt)) < BANK_ENGAGE_DE / 2) cost += 10 * wsum;
          if (g > 0 && i === B.idx[g - 1]) cost += 1e-3;            // a group's neighbour in the list another colour when it can
          if (cost < bestCost - 1e-9) { bestCost = cost; bestI = i; bestNear = near; }
        }
        B.idx[g] = bestI; B.near[g] = bestNear;
      }
      B.on = true;
    } else for (let g = 0; g < nG; g++) B.idx[g] = (B.idx[g] + 1) % n;
    for (let g = 0; g < nG; g++) {
      const m = B.maps[g];
      for (let r = 0; r < ROLES.length; r++) m[r] = B.cycle[(B.idx[g] + ordOf(r, B.near[g])) % n];
      m[ROLE.pin] = ROLE.pin;
    }
    // the heads: each to the other slot of its pair (a head on neither starts on its group's side of the pair)
    for (let i = 0; i < this.nH; i++) {
      const pr = B.pairs[i];
      if (!pr) continue;
      const cur = B.slot[i] >= 0 ? B.slot[i] : this.wheelSlotOf(i);
      B.slot[i] = cur === pr[0] ? pr[1] : cur === pr[1] ? pr[0] : pr[this.bankG.headG[i] % 2];
    }
    B.count++; B.serial++;
    if (B.log.length >= 64) B.log.shift();
    B.log.push({ count: B.count, pos: pos === null ? null : +pos.toFixed(4), idx: Array.from(B.idx) });
    return true;
  }
  // the bank on the targets (after the look, the phrases and the formations, before the kicks): every cell's and head's
  // roles through its group's map; the cells' roles before it are kept for the kick's judge
  _bankApply() {
    const B = this.bank, tC = this.tC, tH = this.tH, cg = this.bankG.cellG, hg = this.bankG.headG, nR = ROLES.length;
    for (let c = 0; c < this.nC; c++) {
      const b = c * 4;
      this.bankOrigC[c * 2] = tC[b + 2]; this.bankOrigC[c * 2 + 1] = tC[b + 3];
      if (!B.on || this.cellKind[c] === CELL_KIND.PIN) continue;
      const m = B.maps[cg[c]], r1 = tC[b + 2] | 0, r2 = tC[b + 3] | 0;
      if (r1 < nR) tC[b + 2] = m[r1];
      if (r2 < nR) tC[b + 3] = m[r2];
    }
    if (!B.on) return;
    for (let i = 0; i < this.nH; i++) {
      const b = i * 7, m = B.maps[hg[i]], r1 = tH[b + 5] | 0, r2 = tH[b + 6] | 0;
      if (r1 < nR) tH[b + 5] = m[r1];
      if (r2 < nR) tH[b + 6] = m[r2];
    }
  }
  // what cell c shows under the bank as it stands (the kick's judge, right after a press advanced it): its look roles
  // through its group's map at its mix
  bankColourOfCell(c, mix, out = [0, 0, 0]) {
    const B = this.bank, nR = ROLES.length;
    let r1 = this.bankOrigC[c * 2], r2 = this.bankOrigC[c * 2 + 1];
    if (B.on && this.cellKind[c] !== CELL_KIND.PIN) { const m = B.maps[this.bankG.cellG[c]]; if (r1 < nR) r1 = m[r1]; if (r2 < nR) r2 = m[r2]; }
    return this.colourOfCell(c, r1, r2, mix, out);
  }
  // the colour of group g's bed under the bank (the record's swatch)
  bankSwatch(g = 0) { const B = this.bank; return B.on && B.cycle.length ? this.roleRGB[B.cycle[B.idx[g] % B.cycle.length]] : this.roleRGB[ROLE.A]; }
  bankStatus() {
    const B = this.bank;
    return { on: B.on, count: B.count, cycle: B.cycle.map((r) => ROLES[r]), groups: Object.fromEntries(this.bankG.names.map((n, g) => [n, B.on ? ROLES[B.cycle[B.idx[g] % B.cycle.length]] : "look"])),
             log: B.log.slice(-8) };
  }
  // the palette's structure: its wheel plan, its splits and pins, its 3-stop strand, its tempo, its walk, its air
  _applyPalette(theme) {
    const p = (theme && theme.palette) || null, rig = this.rig;
    this.palette = p;
    this.plan = p ? planOf(p) : null;
    this.headAllowed = this.plan ? this.plan.slots : null;
    this.cellKind.fill(0); this.headSlotOv.fill(-1);
    for (let i = 0; i < this.nH; i++) this.headLift[i] = this.plan ? this.plan.lift : null;
    if (p && p.split) for (const gname of p.split.accent_groups || []) {
      const wingB = / wing B$/.test(gname), g = rig.groups[wingB ? gname.replace(/ wing B$/, "") : gname];
      if (!g) continue;
      for (let m = 0; m < g.n; m++) {
        if (wingB && !(g.keys.side[m] > 0)) continue;
        const k = g.members[m];
        if (g.kind === "cells") this.cellKind[k] = CELL_KIND.ACCENT;
        else if (g.kind === "heads" && this.plan.groups[gname]) { this.headSlotOv[k] = this.plan.groups[gname].rest; this.headLift[k] = this.plan.groups[gname].lift; }
      }
    }
    if (p && p.pin) for (const gname of p.pin.groups || []) {
      const g = rig.groups[gname];
      if (g && g.kind === "cells") for (let m = 0; m < g.n; m++) this.cellKind[g.members[m]] = CELL_KIND.PIN;
    }
    const sg = p && (p.gradients || []).find((x) => x.name === "strand");
    this.ramp3 = sg && sg.stops && sg.stops.length >= 3 ? tableOf(sg) : null;
    this.walk = p && Array.isArray(p.walk) && p.walk.length ? p.walk.map(hexToLinear) : null;
    this.ambient = hexToLinear((theme && theme.ambient) || "#3a1a8a");
    this.airTint = theme && Number.isFinite(theme.air_tint) ? theme.air_tint : 0;
    // the palette's tempo turns the strand's helix and the ring ladder (a held ladder, "still", one turn in 16 bars)
    const t = p && p.tempo;
    this.tempoMeasure = t ? { "cube-colour": t.strand, "ring-colour": t.name === "still" ? 64 : t.ring } : {};
    for (const [id, inst] of this.effects) {
      const name = id.slice(id.indexOf(":") + 1), m = this.tempoMeasure[name] ?? (this.rig.effects[name] || {}).measure;
      if (TEMPO_EFFECTS[name] && Number.isFinite(m) && m > 0) inst.phasor.measure = m;
    }
  }
  // A new palette lands at beat position pos: a neighbour crossfades every role in OKLCh over `beats`; anything else
  // (dip: true) cuts ON pos through a one-beat dip -- the rig dims to black over the half beat before it and comes back in
  // the new palette over the half beat after, its colours and wheels changing at the bottom, in the dark.
  beginPalette(theme, pos, { beats = 16, dip = false } = {}) {
    const to = resolveTheme(theme);
    this.palX = { theme, to: ROLES.map((r) => to[r]), from: null, fromAmbient: null, toAmbient: hexToLinear(theme.ambient || "#3a1a8a"), dip: !!dip,
                  p0: dip ? pos - PALETTE_DIP_BEATS / 2 : pos, len: dip ? PALETTE_DIP_BEATS : Math.max(1e-3, beats), swapAt: pos, swapped: false };
    return { at: pos, until: this.palX.p0 + this.palX.len, dip: this.palX.dip };
  }
  // the palette's transition and Lantern Walk's walk, once a frame before the colours
  _paletteStep(pos) {
    const X = this.palX;
    this.dipLevel = 1;
    if (X) {
      const t = (pos - X.p0) / X.len;
      if (!X.swapped && pos >= (X.dip ? X.swapAt : X.p0) - 1e-9) {
        // the new palette's structure (the plan, the splits and pins, the tempo) and, for a dip, its colours: now; a
        // crossfade starts from the colours showing at this moment
        X.from = this.roleRGB.slice(0, ROLES.length).map((c) => c.slice()); X.fromAmbient = this.ambient.slice();
        this.setTheme(X.theme);
        if (!X.dip) { for (let r = 0; r < ROLES.length; r++) this.roleRGB[r] = X.from[r].slice(); this.ambient = X.fromAmbient.slice(); }
        X.swapped = true;
        this.paletteEvents.push({ type: "swap", id: X.theme.id || X.theme.name, pos });
      }
      if (X.dip) {
        const u = Math.max(0, Math.min(1, t));
        this.dipLevel = t <= 0 || t >= 1 ? 1 : 0.5 + 0.5 * Math.cos(2 * Math.PI * u);
      } else if (t >= 0 && X.from) {
        const u = Math.min(1, t);
        for (let r = 0; r < ROLES.length; r++) this.roleRGB[r] = mixLch(X.from[r], X.to[r], u);
        this.ambient = mixLch(X.fromAmbient, X.toAmbient, u);
      }
      if (t >= 1) {
        if (!X.dip) { for (let r = 0; r < ROLES.length; r++) this.roleRGB[r] = X.to[r].slice(); this.ambient = X.toAmbient.slice(); }
        this.palX = null;
        this.paletteEvents.push({ type: "landed", id: X.theme.id || X.theme.name, pos });
      }
    }
    // Lantern Walk: the bed walks its stops, one per 16-bar phrase, crossfading in OKLCh over the phrase's first 4 bars
    if (this.walk && !this.palX) {
      const ph = (pos - (this.barAnchor || 0)) / 64, k = Math.floor(ph), u = Math.min(1, (ph - k) * 4), n = this.walk.length;
      const cur = this.walk[((k % n) + n) % n], prev = this.walk[(((k - 1) % n) + n) % n];
      this.roleRGB[ROLE.A] = u >= 1 ? cur.slice() : mixLch(prev, cur, u);
    }
  }
  // a cell's colour for the roles r1, r2 at mix as this palette shows it (its split or pin, a 3-stop strand's ramp): the
  // colour stage below does the same inline; kick.js judges a hit with it
  colourOfCell(c, r1, r2, mix, out = [0, 0, 0]) {
    const kind = this.cellKind[c], nR = ROLES.length;
    if (kind && !(this.bank.on && kind === CELL_KIND.ACCENT)) { const map = REMAP_IDX[kind]; if (r1 < nR) r1 = map[r1]; if (r2 < nR) r2 = map[r2]; }
    if (this.ramp3 && !kind && ((r1 === ROLE.A && r2 === ROLE.B) || (r1 === ROLE.B && r2 === ROLE.A))) return sampleTable(this.ramp3, r1 === ROLE.A ? mix : 1 - mix, out);
    const c1 = this.roleRGB[r1], c2 = this.roleRGB[r2];
    for (let k = 0; k < 3; k++) out[k] = c1[k] + (c2[k] - c1[k]) * mix;
    return out;
  }
  // the colour kick's LIFT of that cell: each of its roles lifted inside the palette (LIFT; swap 1 the swapped ladder), its
  // mix -- its place in the gradient -- kept, so a lifted strand is still a helix
  liftOfCell(c, r1, r2, mix, swap = 0, out = [0, 0, 0]) {
    const kind = this.cellKind[c], nR = ROLES.length, L = LIFT_IDX[swap ? 1 : 0];
    if (kind && !(this.bank.on && kind === CELL_KIND.ACCENT)) { const map = REMAP_IDX[kind]; if (r1 < nR) r1 = map[r1]; if (r2 < nR) r2 = map[r2]; }
    const c1 = this.roleRGB[r1 < nR ? L[r1] : r1], c2 = this.roleRGB[r2 < nR ? L[r2] : r2];
    for (let k = 0; k < 3; k++) out[k] = c1[k] + (c2[k] - c1[k]) * mix;
    return out;
  }
  takePaletteEvents() { const e = this.paletteEvents; this.paletteEvents = []; return e; }
  // the slot a head shows for the look's colour: a split head's own slot (white stays white), else the palette's slot
  // nearest the colour (never a slot outside the palette's plan: the warm white only where a palette declares it)
  _lookSlot(i, b, rgb) {
    if (this.bank.on && this.bank.slot[i] >= 0) return this.bank.slot[i];     // KICK 5's bank: the head's side of its pair
    const ov = this.headSlotOv[i];
    if (ov >= 0) { const lead = this.tH[b + 4] <= 0.5 ? this.tH[b + 5] | 0 : this.tH[b + 6] | 0; if (lead !== ROLE.W) return ov; }
    return nearestSlot(this.wheels[i], rgb, this.headAllowed);
  }
  setSpeed(s, grid, tEval) {
    this.speed = s;
    const pos = grid.posAt(tEval);
    for (const inst of this.effects.values()) inst.phasor.setScale((inst.def.scale ?? 1) * s, pos, grid.barAnchor);
  }
  // Start a look (the scene's looks[name]): lines of {group, values, effects}; fade in beats.
  setLook(name, pos, { fade = null } = {}) {
    const look = this.rig.looks[name];
    if (!look) throw new Error(`no look ${name}`);
    this.lookName = name;
    this.stats.lookChanges++;
    this.fromH.set(this.baseH); this.fromC.set(this.baseC);
    // a look is a full state: every head and cell it does not name goes to black
    for (let i = 0; i < this.nH; i++) this.baseH[i * 7 + 2] = 0;
    for (let c = 0; c < this.nC; c++) this.baseC[c * 4] = 0;
    const wanted = new Set();
    this.lines = [];
    for (const line of look.lines || look) {
      if (!line.group) continue;
      const g = this.rig.groups[line.group];
      if (!g) throw new Error(`look ${name}: no group ${line.group}`);
      const v = line.values || {};
      for (let m = 0; m < g.n; m++) {
        const k = g.members[m];
        if (g.kind === "heads") {
          const b = k * 7;
          if (v.Pan !== undefined) this.baseH[b] = v.Pan;
          if (v.Tilt !== undefined) this.baseH[b + 1] = v.Tilt;
          this.baseH[b + 2] = v.Dimmer ?? 0;
          if (v.Zoom !== undefined) this.baseH[b + 3] = v.Zoom;
          this.baseH[b + 4] = v.ColorMix ?? 0;
          this.baseH[b + 5] = Math.max(0, ROLES.indexOf(v.Color || "W"));
          this.baseH[b + 6] = Math.max(0, ROLES.indexOf(v.Color2 || "B"));
        } else if (g.kind === "cells") {
          const b = k * 4;
          this.baseC[b] = v.Dimmer ?? 0;
          this.baseC[b + 1] = v.ColorMix ?? 0;
          this.baseC[b + 2] = Math.max(0, ROLES.indexOf(v.Color || "A"));
          this.baseC[b + 3] = Math.max(0, ROLES.indexOf(v.Color2 || "B"));
        }
      }
      const effs = [];
      for (const e of line.effects || []) {
        const ref = typeof e === "string" ? { name: e } : e;
        const def = { ...(this.rig.effects[ref.name] || {}), ...(ref.with || {}) };
        if (!this.rig.effects[ref.name]) throw new Error(`look ${name}: no effect ${ref.name}`);
        if (TEMPO_EFFECTS[ref.name] && this.tempoMeasure[ref.name] > 0) def.measure = this.tempoMeasure[ref.name];   // the palette's tempo
        const id = `${line.group}:${ref.name}`;
        wanted.add(id);
        let inst = this.effects.get(id);
        if (!inst) {
          inst = new EffectInstance(id, def, g, { seed: hashSeed(this.seed, id), speed: this.speed, pos });
          this.effects.set(id, inst);
        } else inst.start();
        effs.push(inst);
      }
      this.lines.push({ group: g, effects: effs });
    }
    for (const [id, inst] of this.effects) if (!wanted.has(id)) inst.stop();
    this.fade = { p0: pos, len: fade ?? look.fade ?? 2 };
  }
  // A pad playback at beat position pos. kick (kick-white, kick-colour; "kick" is the white one): onset on the nearest
  // beat (a press within half a beat of a line lands on it); its light starts at the later of its beat and the press: an
  // early press waits for its line, a late one (Daniel 2026-10-27, on the phone bar: "sometimes had an impact at other
  // times nothing changed") still belongs to the beat it fell after (onset, the stats, the receipts) but lights now --
  // before, it began its decay on the beat already gone and showed nothing once it was a sixth of a beat late.
  // {hold: true}: the kick stays lit until padRelease (the page's pads are gates); without it, a tap. Returns the kick's
  // record (kick.js). flyout: onset now.
  pad(kind, vel, pos, { hold = false } = {}) {
    const kk = this.kick.kindOf(kind);
    if (kk) {
      const rec = this.kick.press(kk, vel, pos, { hold });
      this.stats.kicks.push(Math.round(pos));
      if (this.stats.kicks.length > 256) this.stats.kicks.shift();
      return rec;
    }
    if (kind === "flyout") {
      this.pads.push({ kind, onset: pos, vel });
      this.stats.flyouts++;
    }
    while (this.pads.length > 16) this.pads.shift();
    return null;
  }
  // a held pad let go (the kicks fade from here); the live level of a held kick (0..1: the finger's height on the pad)
  padRelease(kind, pos) { if (this.kick.kindOf(kind)) this.kick.release(kind, pos); }
  padLevel(kind, level) { if (this.kick.kindOf(kind)) this.kick.setLevel(kind, level); }
  // the wheel slot a head shows now (the kick's red-free wheel while it owns it, else the linear one)
  wheelSlotOf(i) {
    const w = this.wheels[i];
    if (!w) return -1;
    const n = w.length, x = this.wheelPos[i] >= 0 ? this.wheelPos[i] : this.slews[i].wheel.x;
    return ((Math.round(x) % n) + n) % n;
  }
  // a head's saturated-red wheel slots (cached per fixture type)
  redSlotsOf(i) {
    const t = this.rig.fixtures[this.rig.heads[i]].type;
    let r = this.redSlotsByType.get(t);
    if (!r) { r = this.wheels[i] ? redSlots(this.wheels[i]) : []; this.redSlotsByType.set(t, r); }
    return r;
  }
  // the brightest kick now (v0's name for it)
  kickLevel(pos) { return this.kick.levelNow(pos); }
  tick(grid, tEval, dt) {
    const pos = grid.posAt(tEval);
    const ver = grid.ver;
    const nH = this.nH, nC = this.nC;
    this.perMs = grid.period || this.perMs; this.barAnchor = grid.barAnchor ?? 0;
    // 0. the palette: its transition (a crossfade, or a dip with the swap at the bottom) and Lantern Walk's walk
    this._paletteStep(pos);
    // 1. the look's base, crossfading dimmers from the previous look
    const f = this.fade.len > 0 ? Math.min(1, Math.max(0, (pos - this.fade.p0) / this.fade.len)) : 1;
    for (let i = 0; i < nH * 7; i++) {
      const isDim = i % 7 === 2;
      this.tH[i] = isDim ? this.fromH[i] + (this.baseH[i] - this.fromH[i]) * f : this.baseH[i];
    }
    for (let i = 0; i < nC * 4; i++) this.tC[i] = i % 4 === 0 ? this.fromC[i] + (this.baseC[i] - this.fromC[i]) * f : this.baseC[i];
    // 2. effects, in line order
    for (const inst of this.effects.values()) inst.tick(pos, ver);
    for (const line of this.lines) {
      const g = line.group;
      for (const inst of line.effects) {
        if (inst.level <= 0) continue;
        const attrs = inst.def.attrs || [];
        for (let m = 0; m < g.n; m++) {
          const k = g.members[m];
          for (const a of attrs) {
            if (g.kind === "heads") {
              const off = a === "Pan" ? 0 : a === "Tilt" ? 1 : a === "Dimmer" ? 2 : a === "Zoom" ? 3 : a === "ColorMix" ? 4 : -1;
              if (off >= 0) this.tH[k * 7 + off] = inst.apply(a, this.tH[k * 7 + off], m);
            } else if (g.kind === "cells") {
              const off = a === "Dimmer" ? 0 : a === "ColorMix" ? 1 : -1;
              if (off >= 0) this.tC[k * 4 + off] = inst.apply(a, this.tC[k * 4 + off], m);
            }
          }
        }
      }
    }
    for (const [id, inst] of this.effects) if (inst.dead) this.effects.delete(id);
    // 2b. the phrase layer (v1), over the look; 2c. the ring formations' light (v2), over both
    if (this.ov.active) this._overlay(pos, ver);
    if (this.layer) this.layer.apply(this.tH, this.tC, pos);
    // 2d. KICK 5's colour bank (latched): every group's roles through its place on the palette's cycle
    this._bankApply();
    // 3. playbacks: KICK v2 (kick.js: the dealt rows, HTP on the level, the button's colour, the sweep, the strobe) and
    // FLY-OUT (outward tilt and a pop on the beams)
    this.kick.apply(pos, tEval / 1000, dt);
    for (const p of this.pads) {
      if (p.kind !== "flyout") continue;
      for (let i = 0; i < nH; i++) {
        if (!this.flyoutHead[i]) continue;
        const fx = this.rig.fixtures[this.rig.heads[i]];
        const x = this.rig.elements[fx.element].origin[0] + fx.local[0];
        const delay = Math.min(0.5, Math.abs(x) / 40);           // the burst runs outward from the centre over half a beat
        const age = pos - p.onset - delay;
        if (age < 0 || age > 2) continue;
        const env = Math.sin(Math.min(1, age / 2) * Math.PI);
        this.tH[i * 7 + 1] += Math.sign(x || 1) * 28 * env * p.vel;
        this.tH[i * 7 + 2] = Math.max(this.tH[i * 7 + 2], Math.min(1, 0.85 * (1 - age / 2) + 0.15));
      }
    }
    this.pads = this.pads.filter((p) => pos - p.onset < 3);
    // 4-6. masters, colour, physics -> FrameState (a palette's dip dims the whole rig with the grand master)
    const M = this.masters, dipL = this.dipLevel;
    const tol = this.kick.wheelTol;
    // the bank's move in black: may heads waiting for one start their dip on this frame? (asked once a frame, so every
    // waiting head dips together: one dip of the beams, not a ripple of them)
    let dipOK = null;
    for (let i = 0; i < nH; i++) {
      const b = i * 7, o = i * HEAD_FLOATS, s = this.slews[i];
      const master = M.grand * dipL * (this.strandHead[i] ? M.strand : M.beams);
      const dim = Math.max(0, Math.min(1, s.dim.step(this.bankDip[i] ? 0 : Math.max(0, Math.min(1, this.tH[b + 2])) * master, dt)));
      const pan = s.pan.step(this.tH[b], dt), tilt = s.tilt.step(this.tH[b + 1], dt);
      const zt = this.tH[b + 3] > 0 ? this.tH[b + 3] : this.zoomHome[i];
      const zoom = s.zoom.step(Math.min(this.zoomMax[i], Math.max(this.zoomMin[i], zt)), dt);
      const mix = Math.max(0, Math.min(1, this.tH[b + 4]));
      const c1 = this.roleRGB[this.tH[b + 5] | 0], c2 = this.roleRGB[this.tH[b + 6] | 0];
      let r = c1[0] + (c2[0] - c1[0]) * mix, g = c1[1] + (c2[1] - c1[1]) * mix, bl = c1[2] + (c2[2] - c1[2]) * mix;
      const wheel = this.wheels[i];
      if (wheel) {
        // the wheel: the kick's slot while a kick owns it, else the look's (the palette's slot nearest the role colour). Every
        // move turns the red-free short way at the wheel's real speed; a head that is dark snaps (a move in black); a lit head
        // asked for more than one clean slot waits up to a beat for its dimmer to reach black before it turns
        const n = wheel.length, red = this.redSlotsOf(i), ks = this.kickSlot[i];
        const look = this._lookSlot(i, b, [r, g, bl]);
        let x = this.wheelPos[i];
        if (x < 0) x = look;                                              // the first frame: the wheel starts on its slot
        const at = ((Math.round(x) % n) + n) % n, resting = Math.abs(x - Math.round(x)) < 1e-9;
        let target = ks >= 0 ? ks : look;
        if (ks < 0 && target !== at && resting) {
          const one = Math.min(((target - at) % n + n) % n, ((at - target) % n + n) % n) === 1 && wayLumaCleanFor(wheel, at, target, red, tol);
          if (dim < 0.02) { x = target; this.wheelWait[i] = -1; this.bankDip[i] = 0; }           // dark: the move in black
          else if (!one) {
            if (this.wheelWait[i] < 0) this.wheelWait[i] = pos;
            // lit: wait (up to a beat) for black; a bank's far move (white to a colour) is never run lit through the slots
            // between: it takes its dimmer to black (the move in black), as soon as the flash governor has room for the
            // dip and its return (kick.js canDip), and waits until then
            if (this.bank.on && this.bank.slot[i] === target) {
              if (!this.bankDip[i]) { if (dipOK === null) dipOK = this.kick.canDip(); if (dipOK) this.bankDip[i] = 1; }
              target = at;
            } else if (pos - this.wheelWait[i] < 1) target = at;
          }
        } else if (ks >= 0 || target === at) { this.wheelWait[i] = -1; this.bankDip[i] = 0; }
        const cur = ((Math.round(x) % n) + n) % n;
        if (Math.abs(x - target) > 1e-9) {
          const way = wheelWay(cur, target, n, red, wheel, tol);
          if (way !== 0) {
            const left = way > 0 ? (((target - x) % n) + n) % n : (((x - target) % n) + n) % n;
            const stepS = dt * s.wheel.vmax;
            x = left <= stepS ? target : x + way * stepS;
            x = ((x % n) + n) % n;
          } else x = target;
        }
        this.wheelPos[i] = x;
        const shown = ((Math.round(x) % n) + n) % n;
        s.wheel.x = x; s.wheel.v = 0;
        this.wheelOwn[i] = ks >= 0 || (this.wheelOwn[i] && shown !== look) ? 1 : 0;
        const c = wheel[shown];
        r = c[0]; g = c[1]; bl = c[2];
      }
      const h = this.heads;
      h[o + H.PAN] = pan; h[o + H.TILT] = tilt; h[o + H.DIM] = dim; h[o + H.R] = r; h[o + H.G] = g; h[o + H.B] = bl;
      h[o + H.ZOOM] = zoom; h[o + H.FROST] = 0; h[o + H.IRIS] = 1; h[o + H.GOBO] = 0; h[o + H.GOBOROT] = 0;
      h[o + H.PRISM] = 0; h[o + H.PRISMROT] = 0; h[o + H.SHUTTER] = 1; h[o + H.FOCUS] = 0.5; h[o + H.FLAGS] = 0;
    }
    const kC = this.kickC, ramp = this.ramp3, nR = ROLES.length, tmp = [0, 0, 0], bankOn = this.bank.on;
    const pinK = 1 - Math.exp(-Math.max(0, dt) / PIN_TAU_S);
    for (let c = 0; c < nC; c++) {
      const b = c * 4, kind = this.cellKind[c];
      const master = M.grand * dipL * M.pixels * (this.strandCell[c] ? M.strand : 1);
      let dim = Math.max(0, Math.min(1, this.tC[b])) * master;
      const mix = Math.max(0, Math.min(1, this.tC[b + 1]));
      let r1 = this.tC[b + 2] | 0, r2 = this.tC[b + 3] | 0;
      // (a split's cells show its second family; under the bank they show the bank's colours like every other cell)
      if (kind && !(bankOn && kind === CELL_KIND.ACCENT)) { const map = REMAP_IDX[kind]; if (r1 < nR) r1 = map[r1]; if (r2 < nR) r2 = map[r2]; }
      let R, G, B;
      if (ramp && !kind && ((r1 === ROLE.A && r2 === ROLE.B) || (r1 === ROLE.B && r2 === ROLE.A))) {
        sampleTable(ramp, r1 === ROLE.A ? mix : 1 - mix, tmp); R = tmp[0]; G = tmp[1]; B = tmp[2];   // a 3-stop strand
      } else {
        const c1 = this.roleRGB[r1], c2 = this.roleRGB[r2];
        R = c1[0] + (c2[0] - c1[0]) * mix; G = c1[1] + (c2[1] - c1[1]) * mix; B = c1[2] + (c2[2] - c1[2]) * mix;
      }
      // the colour kick's lift over the look's colour (kick.js: each cell's own roles lifted, its gradient kept)
      const kw = kC[b + 3];
      if (kw > 0) { R += (kC[b] - R) * kw; G += (kC[b + 1] - G) * kw; B += (kC[b + 2] - B) * kw; }
      if (kind === CELL_KIND.PIN) { this.pinDim[c] += (dim - this.pinDim[c]) * pinK; dim = this.pinDim[c]; }   // a pin holds
      this.pixels[b] = R * dim;
      this.pixels[b + 1] = G * dim;
      this.pixels[b + 2] = B * dim;
      this.pixels[b + 3] = dim;
    }
    return { heads: this.heads, pixels: this.pixels };
  }
}
// a one-slot wheel move that runs clean (no red slot, the luminance way clean): a lit head may make it at once
function wayLumaCleanFor(wheel, at, to, red, tol) {
  if (red.includes(to)) return false;
  const n = wheel.length, dir = ((to - at) % n + n) % n === 1 ? 1 : -1;
  return wayLumaCleanKick(wheel, at, to, dir, tol < 1 ? tol : 0.35);
}
