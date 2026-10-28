// Virtual Stage, KICK v2: arsenal/web/stage/kick.js (pure ES module: no DOM, no WebGL). Tests: tests/stage_kick.test.mjs.
// The programmer (programmer.js) owns one Kicks and runs it as its step 3 (the playbacks); stage.js routes the pads to it.
//
// Daniel, 2026-10-27, on the phone bar while testing the Stage: "Hitting kick sometimes had an impact at other times nothing
// changed", and "Can we make kick trigger different rows of lights and or lasers with a peak in brightness or a row turning
// on and panning, it could be also lit for duration of press and on keylab velocity can change parameters too like
// lighting color, animation and strobe". Then: "lets make it a vertically longer button that presses and holds the light
// while the finger is on it and you can sweep up and down to adjust brightness! Lets have two kick buttons with vertical
// "velocity" one kick for white one kick for color, you can press both at same time and two rows can light up at once!"
// And after trying round 1 with the thumb strips: "The kick buttons dont really change anything.  Can we make the kick
// buttons override existing scene lights and cause them to change color with a high intensity", and "Also currently kick
// doesnt always trigger when its pressed. It looks so cool when it does on the color one, can we make sure that the kick
// buttons are responsive and work with powerful impact hits and repeat hits so that it always feels responsive and looks
// visually stunning and cohesive"
//
// Round 1 lifted one row highest-takes-precedence and judged itself on that row's dimmer: on a phone, inside a bright
// moving scene, a single row changing by 0.2 reads as nothing. Round 2 (this file) is judged on the screen's pixels
// (arsenal/lanes/stage_verify.mjs, phase kickpix) and does this:
//   KINDS         what a kick does is data: the set's kick.kinds (kick-white and kick-colour first; see DEFAULT_KINDS),
//                 and the pad map names a kind as a pad's action. kick-white (pad 1, key 1) and kick-colour (pad 5, key 5)
//                 each deal their own AREA; held together they light two different areas, never one twice.
//   AREAS         the deck deals AREAS, not rows: every ring's slats and rims; the whole halo; the strand (its heads,
//                 cubes, dots and bars); and the beams (the truss and lip heads, the towers and pods with their strips, the
//                 delay towers). Measured on the screen, thinner areas (the towers alone, the delay towers alone) cover 5
//                 to 8 % of a wide shot: too little to read on a phone, so they ride with the beams.
//                 A seeded shuffle-bag: never an area a live kick shows, an area the hit will SHOW on (in the camera's view
//                 when the page says what the camera sees, its light visibly brighter or another colour) and of those the
//                 one that covers most of the frame, then never the area the same button had last and another zone of
//                 the stage when it can. Showing comes before variety, and every press lights an area: none is ever skipped.
//   OVERRIDE      while a kick is live its area's intensity AND colour are the kick's (latest takes precedence), the look
//                 running on underneath; on release the area crossfades back to the look as the kick fades.
//   COLOUR        KICK WHITE: full-intensity white. KICK COLOUR: a vivid colour from the set's contrast palette (never a
//                 saturated red), the next one round the palette that is at least 90 degrees of hue from the area's current
//                 colour, and 60 degrees from the other button's (two kicks at once do not clash). Moving heads change
//                 colour too: their wheel goes to the slot nearest the kick's colour (never the red slot) the shortest way
//                 that does not pass the red slot (programmer.js), and comes back the same way after.
//   LEVEL         the finger's height (velocity, then padLevel live), slewed so it never zippers, through a curve that
//                 keeps the whole strip HIGH: intensity = floor + (1 - floor) x level^gamma (0.5 + 0.5 sqrt(level): the
//                 bottom of the strip is half intensity, a quarter of the way up 75 %, the top half 85 % to full).
//   VELOCITY      at the press picks the ANIMATION: soft = the area simply on; medium = a sweep (heads tilt through a motion
//                 of the V2 library, vj-motions.js, sized to 80 % of the tilt motor; LED rows chase it); hard = twice the throw.
//   RESPONSIVE    the light starts AT THE PRESS (the next frame; a head's dimmer motor takes 0.04 s more), with a punch: an
//                 overshoot of 0.15 (kinds.*.punch) over the held intensity settling over 0.15 s. The beat a press
//                 belongs to is still the nearest one (onset, the stats, the receipts' "lands on its beat"); only v0's
//                 kick waits for its line.
//   HOLD = GATE   lit while held; the light lingers a second after the last press (a tap is a one-second hit), then fades
//                 over 0.3 beat. A press of a button while its area is still lit RE-STRIKES it: the light stays up and the
//                 kind's repeat changes what it shows -- the colour kick the most different palette colour of about the same
//                 luminance (every tap a visibly new colour, no brightness jump), the white kick a fresh motion and the chase
//                 jumped on -- and the area flips a comb (alternate heads, and alternate stripes of its LEDs, at full and at
//                 35 %: visible within the dimmer motor's 0.04 s, where a colour wheel needs 0.12 s a slot, the area's mean
//                 brightness unchanged from tap to tap), so a roll
//                 of taps is a run of hits, never big areas flashing on and off faster than the flash gate.
//                 A stuck pad lets go after 64 beats.
//   THE STROBE    only while the live level is in the top band (>= 0.95). ONE strobe clock for every kick, locked to the
//                 bar, at the slowest beat division that keeps it at or under 1.9 flashes a second, and every edge of it at
//                 least 0.263 s after the last: at most 4 edges in any 1.01 s, which the final limiter (flash.js, 5 counted
//                 transitions per 1.01 s) never has to touch. The first row to want it joins at once (the strobe engages as
//                 the finger reaches the band; the clock still keeps an edge's spacing from that row's light-up); any other
//                 row joins, and every row leaves, only while the clock is lit, so all the strobing rows change together
//                 and a joining or leaving row adds no edge of its own. The limiter stays the backstop and is not changed.
//                 The strobe engages only after the pad has been held strobe.hold_s (0.25 s) in the band: a tap is a hit.
//   THE FLASH GOVERNOR  big full-intensity areas make every luminance change count in the final limiter's windows. The
//                 page hands the kick the limiter's headroom each frame (how many more counted transitions its most
//                 loaded window can take, read from flash.js's counters, which it never changes); below governor.need (2)
//                 the kick makes none of its optional changes -- the punch, a re-strike's colour step, comb flip and fresh
//                 motion, the start of a fade (held up to governor.defer_s), the strobe going dark -- and a live area's
//                 motion and LED chase stand still (moving on from there once there is room for one more), so the limiter
//                 does not have to dim a hit. A press always lights at once.
//   THE WHEELS    a kick turns a head's colour wheel the short way, never through red, and only on a way whose brightness
//                 runs clean (governor.equal_luma: no slot on the way that dips or spikes by more), never to a much darker
//                 slot, never white for a colour, a re-strike only to a slot of about the same brightness; else the wheel
//                 stays and the LEDs carry the colour (a run through the dark slots flickers a big area 8 times a second).
//   WITHOUT A BLOCK  (source-v0) KICK is v0's strand lift exactly: the strand's heads and cube cells, 0.6 + 0.4 x velocity,
//                 decaying over 0.3 beat from the line, highest takes precedence, no colour, no motion, no strobe.

import { MotionDealer, valueAt, headSign, CLASSES, seededRng } from "../vj-motions.js";
import { ORDERS, orderKey, rankBy } from "./effects.js";
import { hexToLinear, isSaturatedRed } from "./lasers.js";
import { elementMatrix, eulerToMat3, mat3MulVec } from "./rig.js";

export const KICK_API = "arsenal.stage-kick/v2.1";
export const KICK_KINDS = Object.freeze(["kick-white", "kick-colour"]);
// what the dealer counts as a hit that shows (tests/stage_kick.test.mjs pins the same numbers): at least half the area's
// members change their emitted light by more than CIE76 dE 10 (the pixel metric's own bar)
export const KICK_VISIBLE = Object.freeze({ de: 10, share: 0.5 });
const VIS_MARGIN = 0.1;                  // the dealer asks for a larger share than the bar: it judges targets, not pixels
const VIS_DE_MARGIN = 5;                 // and a member to move by dE76 15, not 10, for the same reason
export const SAT_COLOUR = 0.3;           // a colour at or over this saturation reads as a colour, under it as white
// the house strobe cap: 1.9 flashes a second, so an edge at least 1 / 3.8 s after the last, so at most 4 edges in the
// limiter's 1.01 s window (flash.js LIMIT.N_MAX is 5): the strobe alone leaves the limiter a transition to spare
export const STROBE_HZ_CAP = 1.9;
export const STROBE_MIN_EDGE_S = 1 / (2 * STROBE_HZ_CAP);
// the programmer's colour roles, in its order (programmer.js ROLE_NAMES; tests/stage_kick.test.mjs checks they agree). The
// kick's own colours (its white, its palette) are appended after them as extra roles.
export const KICK_ROLES = Object.freeze(["A", "B", "W", "beamA", "beamB", "warm", "bumpA", "bumpB"]);
export const CLASSES_BEATS = (cls) => (CLASSES[cls] ? CLASSES[cls].beats : NaN);
export const DEFAULT_PALETTE = Object.freeze(["#00e5ff", "#ff2bd6", "#ffd21a", "#2a5bff", "#19ff4a", "#ff9a1a", "#b84bff", "#a8ff2a"]);
// THE KINDS: what a kick does to the area it is dealt, as data (the set's kick.kinds; the pad map names a kind as a pad's
// action, so a new kind is a new entry here and a new pad there). Each kind:
//   colour    "white" (the block's white), "palette" (the contrast palette), "keep" (the area's own colour) or "#rrggbb"
//   override  true: the kick's intensity and colour REPLACE the look's (latest takes precedence); false: a lift (highest)
//   motion    "bands": velocity's animation (the bands: a peak, a sweep, twice the throw); "none"
//   strobe    true: the strobe runs while the live level is in the top band
//   repeat    what a re-strike (a press while the area is lit) changes: "colour" (the next palette colour of about the same
//             luminance), "motion" (a fresh motion, the chase jumped on), "none"
//   punch     the attack's overshoot over the held intensity on a fresh hit (0 none), settling over punch_s seconds
// Round 3 adds kinds (a MOVE that steps the panning phrases, a BLAST of narrow full beams, a SWAP of which lights are on)
// as new fields read here and new branches where press() and apply() read them.
export const KIND_FIELDS = Object.freeze({ colour: ["white", "palette", "keep"], motion: ["bands", "none"], repeat: ["colour", "motion", "none"] });
export const DEFAULT_KINDS = Object.freeze({
  "kick-white": Object.freeze({ colour: "white", override: true, motion: "bands", strobe: true, repeat: "motion", punch: 0.15 }),
  "kick-colour": Object.freeze({ colour: "palette", override: true, motion: "bands", strobe: true, repeat: "colour", punch: 0.15 }),
});
const LEGACY_KIND = Object.freeze({ colour: "keep", override: false, motion: "none", strobe: false, repeat: "none", punch: 0 });

export const KICK_DEFAULTS = Object.freeze({
  release_beats: 0.3, tap_hold_beats: 0.125, max_hold_beats: 64,
  level: Object.freeze({ from_velocity: [0, 1], slew_s: 0.06, floor: 0.5, gamma: 0.5 }),
  bands: Object.freeze([
    { name: "peak", from: 0 },
    { name: "sweep", from: 0.45, sweep: { class: "M1", deg: 25 } },
    { name: "drive", from: 0.85, sweep: { class: "M1", deg: 50 } },
  ]),
  chase: Object.freeze({ floor: 0.8, lag: 0.6 }),
  strobe: Object.freeze({ from_level: 0.95, max_hz: STROBE_HZ_CAP, beats: [0.5, 1, 2, 4], on: 0.35, floor: 0, hold_s: 0.25 }),
  white: Object.freeze({ colour: "#ffffff" }),
  colour: Object.freeze({ palette: DEFAULT_PALETTE, contrast_deg: 90 }),
  governor: Object.freeze({ linger_s: 1.0, punch_s: 0.15, equal_luma: 0.35, comb_floor: 0.35, need: 2, defer_s: 2 }),
  view: Object.freeze({ min_share: 0.25, min_cover: 0.12 }),
  recent_fall_per_beat: 0.15,
});

// ------------------------------------------------------------------------------------------------- colour maths --
const srgb = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055);
// HSV saturation of a linear colour as the screen shows it (sRGB-encoded): 0 white or grey, 1 a pure hue
export function saturation(r, g, b) {
  const R = srgb(Math.max(0, r)), G = srgb(Math.max(0, g)), B = srgb(Math.max(0, b));
  const mx = Math.max(R, G, B), mn = Math.min(R, G, B);
  return mx > 1e-6 ? (mx - mn) / mx : 0;
}
// HSV hue (degrees) of a linear colour as the screen shows it
export function hue(r, g, b) {
  const R = srgb(Math.max(0, r)), G = srgb(Math.max(0, g)), B = srgb(Math.max(0, b));
  const mx = Math.max(R, G, B), mn = Math.min(R, G, B), d = mx - mn;
  if (d < 1e-6) return 0;
  let h = mx === R ? ((G - B) / d) % 6 : mx === G ? (B - R) / d + 2 : (R - G) / d + 4;
  h *= 60;
  return h < 0 ? h + 360 : h;
}
const hueDist = (a, b) => { const d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; };
// CIELAB (D65) of a LINEAR colour (light as emitted, before the screen's encoding) and CIE76 dE between two
const labF = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
export function labOfLinear(c) {
  const r = Math.max(0, Math.min(1, c[0])), g = Math.max(0, Math.min(1, c[1])), b = Math.max(0, Math.min(1, c[2]));
  const fx = labF((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047), fy = labF(0.2126 * r + 0.7152 * g + 0.0722 * b), fz = labF((0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883);
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}
export function deltaE(c1, c2) { const a = labOfLinear(c1), b = labOfLinear(c2); return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]); }
const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const isNum = (x) => typeof x === "number" && Number.isFinite(x);
const isHex = (h) => typeof h === "string" && /^#[0-9a-f]{6}$/i.test(h);

// ----------------------------------------------------------------------------------------------- the colour wheel --
// A wheel fixture's slots that are saturated red (the house rule: red is never the result of an effect that pulses).
export function redSlots(wheel) { const out = []; for (let i = 0; i < wheel.length; i++) if (isSaturatedRed(wheel[i])) out.push(i); return out; }
// The luminance a wheel shows on its way from slot `at` to slot `to` in direction dir (both ends included) runs CLEAN when
// it never turns back by more than tol of its running extreme: a slot on the way much darker than where an upward move has
// been (or much brighter than where a downward one has been) is a dip (a spike) of its own, and on a big area a flash.
// KICK round 2 found it: the beams' wheels running from indigo to cyan through pink, magenta, violet and deep blue flickered
// at the wheel's eight slots a second, and the final limiter held 35 % of a roll of taps.
export function wayLumaClean(wheel, at, to, dir, tol) {
  if (!(tol < 1) || at === to) return true;
  const n = wheel.length, L = (i) => lumaOf(wheel[i]);
  const up = L(to) >= L(at);
  let ext = L(at);
  for (let x = at, s = 0; x !== to && s < n; s++) {
    x = (((x + dir) % n) + n) % n;
    const v = L(x);
    if (up) { if (v < ext * (1 - tol) - 1e-9) return false; ext = Math.max(ext, v); }
    else { if (v > ext / (1 - tol) + 1e-9) return false; ext = Math.min(ext, v); }
  }
  return true;
}
// The way a wheel turns from slot `from` to slot `to` (+1 up, -1 down, 0 there): the shorter way round that passes no red
// slot; if both ways pass one (only when it starts on a red slot), the shorter. Given the wheel and a tol, a red-free way
// whose luminance runs clean (wayLumaClean) comes first.
export function wheelWay(from, to, n, red = [], wheel = null, tol = Infinity) {
  if (from === to) return 0;
  const up = ((to - from) % n + n) % n, down = n - up;
  const passes = (dir, steps) => { for (let k = 1; k < steps; k++) if (red.includes(((from + dir * k) % n + n) % n)) return true; return false; };
  const okUp = !passes(1, up), okDown = !passes(-1, down);
  if (okUp && okDown) {
    if (wheel && tol < 1) {
      const cUp = wayLumaClean(wheel, from, to, 1, tol), cDown = wayLumaClean(wheel, from, to, -1, tol);
      if (cUp !== cDown) return cUp ? 1 : -1;
    }
    return up <= down ? 1 : -1;
  }
  if (okUp) return 1;
  if (okDown) return -1;
  return up <= down ? 1 : -1;
}
// The slot nearest a colour on chromaticity, never a red slot
export function nearestAllowedSlot(wheel, rgb, red = redSlots(wheel)) {
  const n = (c) => { const s = c[0] + c[1] + c[2] || 1; return [c[0] / s, c[1] / s, c[2] / s]; };
  const q = n(rgb);
  let best = -1, bd = Infinity;
  for (let i = 0; i < wheel.length; i++) {
    if (red.includes(i)) continue;
    const p = n(wheel[i]);
    const d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 + 0.02 * Math.abs((wheel[i][0] + wheel[i][1] + wheel[i][2]) - (rgb[0] + rgb[1] + rgb[2]));
    if (d < bd - 1e-12) { bd = d; best = i; }
  }
  return best;
}

// The slot nearest a colour among those a wheel at slot `at` reaches the SHORT way round without passing a red slot (a tie
// in distance counts as short) -- and, given a tol, on a way whose luminance runs clean (wayLumaClean), and, given near,
// with about the slot's own luminance (within near of the brighter: a re-strike's step), and, for a colour (saturation
// SAT_COLOUR or more), never a white or near-white slot (a colour kick never turns a head white); never a slot much darker
// than the one it shows (more than tol: a hit never dims a head's colour). When nothing qualifies,
// the wheel stays where it is (the nearest allowed slot, if that is red).
export function shortWayClear(at, to, n, red, wheel = null, tol = Infinity) {
  if (red.includes(to)) return false;
  if (at === to) return true;
  const up = ((to - at) % n + n) % n, down = n - up;
  const clear = (dir, steps) => {
    for (let k = 1; k < steps; k++) if (red.includes(((at + dir * k) % n + n) % n)) return false;
    return !wheel || wayLumaClean(wheel, at, to, dir, tol);
  };
  return (up <= down && clear(1, up)) || (down <= up && clear(-1, down));
}
export function nearestShortSlot(wheel, rgb, at, red = redSlots(wheel), { tol = Infinity, near = Infinity } = {}) {
  const colourOnly = tol < 1 && saturation(...rgb) >= SAT_COLOUR;
  const n = (c) => { const s = c[0] + c[1] + c[2] || 1; return [c[0] / s, c[1] / s, c[2] / s]; };
  const q = n(rgb), la = at >= 0 && at < wheel.length ? lumaOf(wheel[at]) : null;
  let best = -1, bd = Infinity;
  for (let i = 0; i < wheel.length; i++) {
    if (!shortWayClear(at, i, wheel.length, red, tol < 1 ? wheel : null, tol)) continue;
    if (near < 1 && la !== null && i !== at) { const li = lumaOf(wheel[i]); if (Math.abs(li - la) > near * Math.max(li, la)) continue; }
    if (colourOnly && saturation(...wheel[i]) < SAT_COLOUR) continue;
    if (tol < 1 && la !== null && i !== at && lumaOf(wheel[i]) < la * (1 - tol) - 1e-9) continue;     // never a much darker slot
    const p = n(wheel[i]);
    const d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 + 0.02 * Math.abs((wheel[i][0] + wheel[i][1] + wheel[i][2]) - (rgb[0] + rgb[1] + rgb[2]));
    if (d < bd - 1e-12) { bd = d; best = i; }
  }
  if (best >= 0) return best;
  return tol < 1 && at >= 0 && at < wheel.length && !red.includes(at) ? at : nearestAllowedSlot(wheel, rgb, red);
}

// ---------------------------------------------------------------------------------------------- configuration --
// The kick block with the defaults under it, and its cards resolved to members. Without a block: the v0 strand lift.
export function kickConfig(rig) {
  const block = rig.kick || null;
  if (!block) return legacyConfig(rig);
  const cfg = { legacy: false, seed: block.seed ?? rig.seed ?? 1, about: block.about || "" };
  for (const k of ["release_beats", "tap_hold_beats", "max_hold_beats", "recent_fall_per_beat"]) cfg[k] = block[k] ?? KICK_DEFAULTS[k];
  cfg.level = { ...KICK_DEFAULTS.level, ...(block.level || {}) };
  cfg.bands = (block.bands || KICK_DEFAULTS.bands).map((b) => ({ ...b })).sort((a, b) => a.from - b.from);
  cfg.chase = { ...KICK_DEFAULTS.chase, ...(block.chase || {}) };
  cfg.strobe = { ...KICK_DEFAULTS.strobe, ...(block.strobe || {}) };
  cfg.strobe.max_hz = Math.min(STROBE_HZ_CAP, cfg.strobe.max_hz);          // the cap is the code's, not the set's
  cfg.white = { ...KICK_DEFAULTS.white, ...(block.white || {}) };
  cfg.colour = { ...KICK_DEFAULTS.colour, ...(block.colour || {}) };
  cfg.colour.palette = (cfg.colour.palette || DEFAULT_PALETTE).filter((h) => isHex(h) && !isSaturatedRed(hexToLinear(h)));
  if (!cfg.colour.palette.length) cfg.colour.palette = DEFAULT_PALETTE.slice();
  cfg.governor = { ...KICK_DEFAULTS.governor, ...(block.governor || {}) };
  cfg.view = { ...KICK_DEFAULTS.view, ...(block.view || {}) };
  cfg.override = true;
  cfg.kinds = {};
  for (const [name, spec] of Object.entries(block.kinds || DEFAULT_KINDS)) cfg.kinds[name] = { ...LEGACY_KIND, punch: 0.15, override: true, ...spec, name };
  cfg.kindNames = Object.keys(cfg.kinds);
  cfg.cards = (block.deck || []).map((c, i) => resolveCard(rig, c, i)).filter(Boolean);
  return cfg;
}
function legacyConfig(rig) {
  const heads = [], cells = [];
  for (let i = 0; i < rig.heads.length; i++) if (rig.elements[rig.fixtures[rig.heads[i]].element].id === "rung") heads.push(i);
  for (let c = 0; c < rig.cells.n; c++) if (rig.elements[rig.cells.element[c]].id === "rung" && rig.cells.kind[c] === 2) cells.push(c);
  return {
    legacy: true, override: false, seed: rig.seed ?? 1, about: "v0: the strand lift",
    release_beats: 0.3, tap_hold_beats: 0, max_hold_beats: KICK_DEFAULTS.max_hold_beats, recent_fall_per_beat: KICK_DEFAULTS.recent_fall_per_beat,
    level: { from_velocity: [0.6, 1], slew_s: KICK_DEFAULTS.level.slew_s, floor: 0, gamma: 1 },
    bands: [{ name: "lift", from: 0 }], chase: { ...KICK_DEFAULTS.chase }, strobe: { ...KICK_DEFAULTS.strobe, from_level: Infinity },
    white: null, colour: null, governor: { linger_s: 0, punch_s: 0, equal_luma: 0, comb_floor: 1, need: 0, defer_s: 0 }, view: { min_share: 0 },
    kinds: { kick: { ...LEGACY_KIND, name: "kick" } }, kindNames: ["kick"],
    cards: [{ name: "strand", zone: "strand", heads: Int32Array.from(heads), cells: Int32Array.from(cells), pan: null, tilt: null,
              headSide: new Float64Array(heads.length).fill(1), headLower: new Uint8Array(heads.length), headRank: Int32Array.from(heads.map((_, i) => i)),
              cellQ: new Int32Array(cells.length), samples: new Float64Array(0) }],
  };
}
// a card: {name, row | rows, zone, order, pan, tilt} -> its heads and cells (groups of the set), each head's side and
// height (the motion's mirror modes), the members' places in the card's order (the sweep's ripple, the chase's travel),
// and up to 96 world points the camera check samples (fixtures and LED cells where they hang at home, and for each head a
// point 10 m out along its beam at rest)
function resolveCard(rig, c, i) {
  const names = c.rows || (c.row ? [c.row] : []);
  const heads = [], cells = [], hSide = [], hY = [], hKeyH = [], cKey = [], pts = [];
  const order = c.order || null;
  for (const name of names) {
    const g = rig.groups[name];
    if (!g || !g.n || (g.kind !== "heads" && g.kind !== "cells")) continue;
    const ord = order && ORDERS.includes(order) ? order : g.kind === "heads" ? "x" : "along";
    const key = orderKey(g.keys, ord, g.n, rig.seed || 1);
    for (let m = 0; m < g.n; m++) {
      const w = g.world[m];
      if (g.kind === "heads") {
        heads.push(g.members[m]); hSide.push(g.keys.side[m] || 1); hY.push(g.keys.y[m]); hKeyH.push(key[m]);
        const f = rig.fixtures[g.memberFixture[m]], em = elementMatrix(rig.elements[f.element]);
        const dE = mat3MulVec(eulerToMat3(f.rot), [0, 1, 0]);
        const dW = [em[0] * dE[0] + em[1] * dE[1] + em[2] * dE[2], em[3] * dE[0] + em[4] * dE[1] + em[5] * dE[2], em[6] * dE[0] + em[7] * dE[1] + em[8] * dE[2]];
        pts.push(w, [w[0] + 10 * dW[0], w[1] + 10 * dW[1], w[2] + 10 * dW[2]]);
      } else { cells.push(g.members[m]); cKey.push(key[m]); pts.push(w); }
    }
  }
  if (!heads.length && !cells.length) return null;
  const cy = hY.length ? hY.reduce((s, y) => s + y, 0) / hY.length : 0;
  // heads: their rank in the order (ties by index); cells: their place 0..1000 along the order (ties share a place)
  const headRank = heads.length ? rankBy({ k: hKeyH }, "k", heads.length) : new Int32Array(0);
  let lo = Infinity, hi = -Infinity;
  for (const k of cKey) { lo = Math.min(lo, k); hi = Math.max(hi, k); }
  const cellQ = Int32Array.from(cKey.map((k) => (hi > lo ? Math.round(((k - lo) / (hi - lo)) * 1000) : 0)));
  const stride = Math.max(1, Math.ceil(pts.length / 96));
  const sample = [];
  for (let k = 0; k < pts.length; k += stride) sample.push(...pts[k]);
  return { name: c.name || names.join("+"), index: i, zone: c.zone || names[0], heads: Int32Array.from(heads), cells: Int32Array.from(cells),
           pan: isNum(c.pan) ? c.pan : null, tilt: isNum(c.tilt) ? c.tilt : null,
           headSide: Float64Array.from(hSide), headLower: Uint8Array.from(hY.map((y) => (y < cy - 0.5 ? 1 : 0))), headRank, cellQ,
           samples: Float64Array.from(sample) };
}
export function bandFor(cfg, vel) {
  let b = cfg.bands[0];
  for (const x of cfg.bands) if (vel >= x.from - 1e-9) b = x;
  return b;
}
// the intensity a live level gives (round 2: the whole strip reads high)
export function intensityOf(cfg, level) { const L = cfg.level; return clamp01((L.floor ?? 0) + (1 - (L.floor ?? 0)) * Math.pow(clamp01(level), L.gamma ?? 1)); }

// Every problem with a rig's kick block, as plain sentences (none: [] -- including no block at all, the v0 kick).
export function validateKick(rig) {
  const k = rig.kick;
  if (!k) return [];
  const out = [];
  const err = (m) => out.push(`kick.${m}`);
  if (!Array.isArray(k.deck) || !k.deck.length) err("deck: a list of areas");
  const owner = new Map();
  for (const [i, c] of (k.deck || []).entries()) {
    const names = c && (c.rows || (c.row ? [c.row] : []));
    if (!names || !names.length) { err(`deck[${i}]: {rows: [group names]} (or row: a group name)`); continue; }
    for (const n of names) {
      const g = rig.groups[n];
      if (!g) { err(`deck[${i}]: no group ${JSON.stringify(n)} in the set`); continue; }
      if (g.kind !== "heads" && g.kind !== "cells") { err(`deck[${i}]: group ${n} is ${g.kind} (heads or LED cells only)`); continue; }
      if (!g.n) err(`deck[${i}]: group ${n} is empty`);
      for (let m = 0; m < g.n; m++) {
        const key = `${g.kind}:${g.members[m]}`;
        const j = owner.get(key);
        if (j !== undefined && j !== i) { err(`deck[${i}] and deck[${j}] share members (${n}): two kicks could light one fixture twice`); break; }
        owner.set(key, i);
      }
    }
    if (c.order !== undefined && !ORDERS.includes(c.order)) err(`deck[${i}].order: one of ${ORDERS.join(", ")}`);
    if (c.pan !== undefined && !(isNum(c.pan) && Math.abs(c.pan) <= 270)) err(`deck[${i}].pan: degrees within +-270`);
    if (c.tilt !== undefined && !(isNum(c.tilt) && Math.abs(c.tilt) <= 135)) err(`deck[${i}].tilt: degrees within +-135`);
  }
  const bands = k.bands || KICK_DEFAULTS.bands;
  if (!Array.isArray(bands) || !bands.length) err("bands: a list");
  else {
    if (!bands.some((b) => b.from === 0)) err("bands: one band must start at velocity 0");
    const names = new Set();
    for (const [i, b] of bands.entries()) {
      if (!b.name || names.has(b.name)) err(`bands[${i}].name: a name of its own`);
      names.add(b.name);
      if (!(isNum(b.from) && b.from >= 0 && b.from <= 1)) err(`bands[${i}].from: a velocity 0..1`);
      if (b.sweep) {
        const C = CLASSES[b.sweep.class];
        if (!C || C.texture) err(`bands[${i}].sweep.class: a whole motion class of vj-motions.js (M8 .. M4b)`);
        if (!(isNum(b.sweep.deg) && b.sweep.deg > 0 && b.sweep.deg <= 90)) err(`bands[${i}].sweep.deg: 0 < deg <= 90`);
      }
    }
  }
  const s = { ...KICK_DEFAULTS.strobe, ...(k.strobe || {}) };
  if (!(isNum(s.max_hz) && s.max_hz > 0 && s.max_hz <= STROBE_HZ_CAP)) err(`strobe.max_hz: above 0 and at most the house cap ${STROBE_HZ_CAP} (got ${s.max_hz})`);
  if (!(isNum(s.from_level) && s.from_level > 0 && s.from_level <= 1)) err("strobe.from_level: a level 0..1");
  if (!(Array.isArray(s.beats) && s.beats.length && s.beats.every((x) => isNum(x) && x > 0))) err("strobe.beats: beat divisions > 0");
  if (!(isNum(s.on) && s.on > 0 && s.on < 1)) err("strobe.on: the lit share of a period, 0..1");
  if (!(isNum(s.floor) && s.floor >= 0 && s.floor < 1)) err("strobe.floor: the dark level, 0 <= floor < 1");
  if (!(isNum(s.hold_s) && s.hold_s >= 0 && s.hold_s <= 2)) err("strobe.hold_s: seconds held before the strobe engages, 0..2");
  const lv = { ...KICK_DEFAULTS.level, ...(k.level || {}) };
  if (!(Array.isArray(lv.from_velocity) && lv.from_velocity.length === 2 && lv.from_velocity.every((x) => isNum(x) && x >= 0 && x <= 1))) err("level.from_velocity: [level at velocity 0, level at velocity 1]");
  if (!(isNum(lv.slew_s) && lv.slew_s > 0 && lv.slew_s <= 1)) err("level.slew_s: seconds, 0 < s <= 1");
  if (!(isNum(lv.floor) && lv.floor >= 0 && lv.floor < 1)) err("level.floor: the intensity at the bottom of the strip, 0 <= floor < 1");
  if (!(isNum(lv.gamma) && lv.gamma > 0 && lv.gamma <= 4)) err("level.gamma: the curve's exponent, 0 < gamma <= 4");
  for (const key of ["release_beats", "max_hold_beats"]) if (k[key] !== undefined && !(isNum(k[key]) && k[key] > 0)) err(`${key}: beats > 0`);
  if (k.tap_hold_beats !== undefined && !(isNum(k.tap_hold_beats) && k.tap_hold_beats >= 0)) err("tap_hold_beats: beats >= 0");
  if (k.white && k.white.colour !== undefined && !isHex(k.white.colour)) err("white.colour: a #rrggbb colour");
  const pal = k.colour && k.colour.palette;
  if (pal !== undefined) {
    if (!(Array.isArray(pal) && pal.length >= 2 && pal.every(isHex))) err("colour.palette: at least two #rrggbb colours");
    else for (const h of pal) if (isSaturatedRed(hexToLinear(h))) err(`colour.palette: ${h} is a saturated red (R / (R + G + B) >= 0.8), which a kick never flashes`);
  }
  if (k.kinds !== undefined) {
    if (!k.kinds || typeof k.kinds !== "object" || !Object.keys(k.kinds).length) err("kinds: an object of kind name -> what it does");
    else for (const [name, spec] of Object.entries(k.kinds)) {
      if (!/^[a-z][a-z0-9-]{0,31}$/.test(name)) err(`kinds.${name}: a kind name is lower-case letters, digits and dashes`);
      if (!spec || typeof spec !== "object") { err(`kinds.${name}: an object`); continue; }
      if (spec.colour !== undefined && !KIND_FIELDS.colour.includes(spec.colour) && !(isHex(spec.colour) && !isSaturatedRed(hexToLinear(spec.colour)))) err(`kinds.${name}.colour: one of ${KIND_FIELDS.colour.join(", ")} or a #rrggbb that is not a saturated red`);
      if (spec.motion !== undefined && !KIND_FIELDS.motion.includes(spec.motion)) err(`kinds.${name}.motion: one of ${KIND_FIELDS.motion.join(", ")}`);
      if (spec.repeat !== undefined && !KIND_FIELDS.repeat.includes(spec.repeat)) err(`kinds.${name}.repeat: one of ${KIND_FIELDS.repeat.join(", ")}`);
      for (const b of ["override", "strobe"]) if (spec[b] !== undefined && typeof spec[b] !== "boolean") err(`kinds.${name}.${b}: true or false`);
      if (spec.punch !== undefined && !(isNum(spec.punch) && spec.punch >= 0 && spec.punch <= 0.5)) err(`kinds.${name}.punch: 0 .. 0.5`);
    }
  }
  const gv = { ...KICK_DEFAULTS.governor, ...(k.governor || {}) };
  if (!(isNum(gv.linger_s) && gv.linger_s >= 0 && gv.linger_s <= 4)) err("governor.linger_s: seconds, 0..4");
  if (!(isNum(gv.punch_s) && gv.punch_s >= 0 && gv.punch_s <= 0.5)) err("governor.punch_s: seconds, 0..0.5");
  const vw = { ...KICK_DEFAULTS.view, ...(k.view || {}) };
  if (!(isNum(vw.min_share) && vw.min_share >= 0 && vw.min_share <= 1 && isNum(vw.min_cover) && vw.min_cover >= 0 && vw.min_cover <= 1)) err("view: {min_share, min_cover}, shares 0..1");
  if (!(isNum(gv.equal_luma) && gv.equal_luma > 0 && gv.equal_luma <= 1)) err("governor.equal_luma: a share, 0 < x <= 1");
  if (!(isNum(gv.comb_floor) && gv.comb_floor >= 0.3 && gv.comb_floor <= 1)) err("governor.comb_floor: the combed members' share of the level, 0.3..1");
  if (!(isNum(gv.need) && gv.need >= 1 && gv.need <= 5)) err("governor.need: the limiter headroom the kick keeps (transitions), 1..5");
  if (!(isNum(gv.defer_s) && gv.defer_s >= 0 && gv.defer_s <= 4)) err("governor.defer_s: seconds a fade may wait, 0..4");
  return out;
}

// ------------------------------------------------------------------------------------------------------ the deck --
// A seeded shuffle-bag of card indices. deal(eligible) scans the rest of the round in bag order for the first card that
// passes eligible(card, pass) -- pass 0 the strictest (it shows, in another zone, not the button's last), 1 (it shows, not
// the button's last), 2 (it shows: the button's last or its own fading area allowed), 3 (no kick shows it), 4 (the
// button's own fading card) -- and moves it to the front of the rest; a new round's first card is never the one dealt last.
// Showing on screen comes before variety: a press re-deals an area it can be seen on before it deals one it cannot.
export class KickDeck {
  constructor(n, seed) {
    this.n = n; this.rng = seededRng(...[].concat(seed), "kick-deck"); this.round = 0; this.order = []; this.i = 0; this.last = -1;
    this.forceNext = -1;          // the receipts' door: deal this card next (if no live kick has it), whatever it shows
    this._shuffle();
  }
  _shuffle() {
    const a = Array.from({ length: this.n }, (_, i) => i);
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(this.rng() * (i + 1)); const t = a[i]; a[i] = a[j]; a[j] = t; }
    if (a.length > 1 && a[0] === this.last) { const t = a[0]; a[0] = a[1]; a[1] = t; }
    this.order = a; this.i = 0; this.round++;
  }
  _take(j) {
    const c = this.order[j];
    this.order.splice(j, 1); this.order.splice(this.i, 0, c); this.i++;
    this.last = c;
    return c;
  }
  // Passes 0 and 1 over the rest of the round; when no card left in it can show the hit, the round ends there and a new
  // one is shuffled (the passed-over cards come round again in it); then, over the fresh round, passes 2, 3 and 4 (the
  // last: the button's own fading card, which a re-press takes over, as v0's one-row KICK always did).
  // score (optional): card -> how much of the frame it covers in the camera; passes 0 to 2 then take the best-scoring
  // eligible card of the rest of the round (the area the shot shows most of wins; the bag's order breaks ties, and the
  // "never the button's last area" and "another zone" passes still move the hits round the stage).
  deal(eligible, score = null, look = score ? Infinity : 3) {
    if (this.forceNext >= 0) {
      const f = this.forceNext; this.forceNext = -1;
      if (eligible(f, -1)) { const j = this.order.indexOf(f, this.i); if (j >= 0) return this._take(j); this._shuffle(); return this._take(this.order.indexOf(f)); }
    }
    const scan = (pass, k) => {
      let best = -1, bs = -Infinity, seen = 0;
      for (let j = this.i; j < this.order.length && seen < k; j++) {
        if (!eligible(this.order[j], pass)) continue;
        seen++;
        const sc = score ? score(this.order[j]) : -seen;
        if (sc > bs + 1e-9) { bs = sc; best = j; }
      }
      return best;
    };
    for (let attempt = 0; attempt < 2; attempt++) {
      for (const pass of [0, 1]) { const j = scan(pass, look); if (j >= 0) return this._take(j); }
      if (attempt === 0) this._shuffle();
    }
    { const j = scan(2, Infinity); if (j >= 0) return this._take(j); }
    for (const pass of [3, 4]) { const j = scan(pass, 1); if (j >= 0) return this._take(j); }
    return -1;
  }
}

// ----------------------------------------------------------------------------------------------------- the kicks --
// One per programmer. press / release / setLevel come from the pads; apply() is the programmer's step 3 each frame. view
// (optional, set by the page): card -> the share of its sample points the camera sees (0..1).
const lumaOf = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
export class Kicks {
  constructor(prog) {
    this.p = prog;
    this.cfg = kickConfig(prog.rig);
    this.cards = this.cfg.cards;
    this.kinds = this.cfg.kinds;
    // seeded by the set's kick seed and the programmer's (the same set and seed always deal the same areas and motions)
    this.deck = new KickDeck(this.cards.length, [this.cfg.seed, prog.seed]);
    this.motions = new MotionDealer({ seed: `${this.cfg.seed}|${prog.seed}` });
    this.list = [];                       // live kicks
    this.log = [];                        // the last 64 presses, for the receipts
    this.presses = 0; this.passedOver = 0; this.restrikes = 0; this.unlit = 0;
    this.lastZone = null;
    this.lastOf = {};                     // kind -> the card it had last
    this.palIdx = 0;                      // the palette kinds' place in the palette
    this.view = null;
    // THE FLASH GOVERNOR: the page tells the kick, each frame, how many more counted transitions the final limiter's most
    // loaded window can take in the next second (headroom; flash.js's N_MAX when nothing is known). While it is under
    // governor.need, the kick makes none of its OPTIONAL luminance changes -- the punch, a re-strike's colour step, comb flip
    // and fresh motion, the start of a release's fade (held up to governor.defer_s), the strobe going dark -- so the limiter never has
    // to dim a hit; a press always lights.
    // (and, round 2's last addition, a live area's motion and LED chase STAND STILL while the budget is spent: frames, in
    // gov.still; they move on from where they stood once a window has room again)
    this.headroom = 5; this.gov = { punch: 0, colour: 0, comb: 0, motion: 0, fade: 0, strobe: 0, still: 0 };
    // the pre-kick state of the last frame (the dealer judges a row on it) and each member's recent peak level
    this.preH = new Float64Array(prog.nH * 7); this.preC = new Float64Array(prog.nC * 4);
    this.recentH = new Float32Array(prog.nH); this.recentC = new Float32Array(prog.nC);
    this.lastPos = null;
    // the one strobe clock: on, and the time (s) of its last edge
    this.clock = { on: true, lastEdge: -Infinity, P: 2, onB: 0.7 };
    // the kick's own colours: its white, its palette and any kind's own colour, appended to the programmer's roles
    this.extendRoles();
  }
  // (re)append the kick's colours to the programmer's roles (a new theme rebuilds them)
  extendRoles() {
    const p = this.p, cfg = this.cfg;
    if (cfg.legacy || !p.roleRGB) return;
    p.roleRGB.length = KICK_ROLES.length;
    this.whiteRole = p.roleRGB.length; p.roleRGB.push(hexToLinear(cfg.white.colour));
    this.palette = cfg.colour.palette.map((h) => { const c = hexToLinear(h); return { hex: h, rgb: c, hue: hue(...c), sat: saturation(...c), luma: lumaOf(c), role: p.roleRGB.push(c) - 1 }; });
    this.kindRoles = {};
    for (const [name, k] of Object.entries(this.kinds)) if (isHex(k.colour)) this.kindRoles[name] = { hex: k.colour, rgb: hexToLinear(k.colour), role: p.roleRGB.push(hexToLinear(k.colour)) - 1 };
  }
  // the kind a pad action names ("kick" is the first kind; without a block every kick action is v0's one kick)
  kindOf(kind) {
    if (this.kinds[kind]) return kind;
    if (this.cfg.legacy) return /^kick(-|$)/.test(String(kind)) ? "kick" : null;
    if (kind === "kick") return this.cfg.kindNames[0];
    return null;
  }
  specOf(kind) { return this.kinds[kind] || LEGACY_KIND; }
  levelOfVel(vel) { const [a, b] = this.cfg.level.from_velocity; return clamp01(a + (b - a) * clamp01(vel)); }
  _secs(pos) { return (pos * (this.p.perMs || 400)) / 1000; }
  _cellColour(c, buf = this.preC) {
    const b = c * 4, mix = clamp01(buf[b + 1]);
    const c1 = this.p.roleRGB[buf[b + 2] | 0], c2 = this.p.roleRGB[buf[b + 3] | 0];
    return [c1[0] + (c2[0] - c1[0]) * mix, c1[1] + (c2[1] - c1[1]) * mix, c1[2] + (c2[2] - c1[2]) * mix];
  }
  _headColour(i) { const o = i * 16, h = this.p.heads; return [h[o + 3], h[o + 4], h[o + 5]]; }
  // the area's colour now (lit members weighted by their level; all of them alike when it is dark)
  _areaColour(card) {
    let r = 0, g = 0, b = 0, w = 0;
    const add = (c, k) => { r += c[0] * k; g += c[1] * k; b += c[2] * k; w += k; };
    for (const i of card.heads) add(this._headColour(i), 0.02 + this.recentH[i]);
    for (const c of card.cells) add(this._cellColour(c), 0.02 + this.recentC[c]);
    return w > 0 ? [r / w, g / w, b / w] : [1, 1, 1];
  }
  // may the kick make an optional luminance change now?
  _can(what) { if (this.cfg.legacy || this.headroom >= this.cfg.governor.need) return true; this.gov[what]++; return false; }
  // the hues other live kicks paint (so two kicks at once do not clash)
  _otherHues(not) {
    const out = [];
    for (const k of this.list) if (k !== not && !k.dead && k.colour && k.colour.pal >= 0) out.push(this.palette[k.colour.pal].hue);
    return out;
  }
  // The colour a kick of this kind paints now: white, keep (none), its own, or -- a palette kind -- the next palette colour
  // (from the palette's place) at least contrast_deg of hue from the area's colour (any, when the area is a white or dark)
  // and 60 degrees from any other live kick's colour, skipping `not` (a re-strike's colour)
  _pickColour(kind, card, { not = -1, self = null, preview = false } = {}) {
    const spec = this.specOf(kind);
    if (spec.colour === "keep") return null;
    if (spec.colour === "white") return { pal: -1, role: this.whiteRole, rgb: this.p.roleRGB[this.whiteRole] };
    if (isHex(spec.colour)) { const r = this.kindRoles[kind]; return { pal: -1, role: r.role, rgb: r.rgb }; }
    const P = this.palette, now = this._areaColour(card);
    const sNow = saturation(...now), hNow = hue(...now), others = this._otherHues(self);
    const tries = [
      (c) => (sNow < 0.2 || hueDist(c.hue, hNow) >= this.cfg.colour.contrast_deg) && others.every((h) => hueDist(c.hue, h) >= 60),
      (c) => sNow < 0.2 || hueDist(c.hue, hNow) >= this.cfg.colour.contrast_deg,
      () => true,
    ];
    for (const ok of tries) for (let k = 0; k < P.length; k++) {
      const j = (this.palIdx + k) % P.length;
      if (j === not || !ok(P[j])) continue;
      if (!preview) this.palIdx = (j + 1) % P.length;
      return { pal: j, role: P[j].role, rgb: P[j].rgb };
    }
    return { pal: 0, role: P[0].role, rgb: P[0].rgb };
  }
  // A re-strike's colour: of the palette colours with about the same luminance as the current one (within equal_luma of the
  // brighter), not the current one nor the one before it, not another live kick's hue, the one MOST different from the
  // current (CIE76 dE): every tap of a roll reads as a new hit without the area's brightness jumping (a brightness jump on
  // every tap would be a flash).
  _stepColour(k) {
    const P = this.palette, cur = k.colour && k.colour.pal >= 0 ? P[k.colour.pal] : null;
    if (!cur) return this._pickColour(k.kind, k.card, { self: k });
    const others = this._otherHues(k), tol = this.cfg.governor.equal_luma;
    const near = (c) => Math.abs(c.luma - cur.luma) <= tol * Math.max(c.luma, cur.luma);
    const tries = [(c) => near(c) && others.every((h) => hueDist(c.hue, h) >= 60), near, () => true];
    for (const ok of tries) {
      let best = -1, bd = 25;
      for (let j = 0; j < P.length; j++) {
        if (j === k.colour.pal || j === k.prevPal || !ok(P[j])) continue;
        const d = deltaE(P[j].rgb, cur.rgb);
        if (d > bd) { bd = d; best = j; }
      }
      if (best >= 0) { k.prevPal = k.colour.pal; return { pal: best, role: P[best].role, rgb: P[best].rgb }; }
    }
    const j = (k.colour.pal + 1) % P.length;
    k.prevPal = k.colour.pal;
    return { pal: j, role: P[j].role, rgb: P[j].rgb };
  }
  // the wheel slot each head of the card goes to for a colour: of the slots whose SHORT way round from where the wheel is
  // passes no red slot (and is not red), the one nearest the colour -- so a kick never sends a wheel the long way round
  // (round 2) on a way whose luminance runs clean (governor.equal_luma), and a re-strike's only to a slot of about the
  // luminance the wheel shows now: a roll of taps never runs the wheels through their dark slots
  _slotsFor(card, rgb, { restrike = false } = {}) {
    if (!card.heads.length || !rgb) return null;
    const out = new Int16Array(card.heads.length);
    const tol = this.wheelTol;
    for (let m = 0; m < card.heads.length; m++) {
      const i = card.heads[m], wheel = this.p.wheels[i];
      out[m] = wheel ? nearestShortSlot(wheel, rgb, this.p.wheelSlotOf(i), this.p.redSlotsOf(i), { tol, near: restrike ? tol : Infinity }) : -1;
    }
    return out;
  }
  // the luminance tolerance of a kick's wheel moves (none for v0's kick, which never turns a wheel)
  get wheelTol() { return this.cfg.legacy ? Infinity : this.cfg.governor.equal_luma; }
  // How a card would show a kick of this kind at this level now: {changed, view, ok}. Each member's emitted light before
  // (its look colour at its recent peak level, and at its level now: the closer of the two) and after (the kick's colour,
  // or its own for a "keep" kind, at the kick's full intensity); a member CHANGES when that moves by more than dE76 10 and
  // gets no darker (a hit is brighter or another colour, never a dimming); the card shows the hit when more than half its
  // members (plus a margin) change, and, when the page says what the camera sees, enough of it is on the screen.
  judge(ci, kind, level, band) {
    const card = this.cards[ci], cfg = this.cfg;
    if (cfg.legacy) return { changed: 1, view: 1, ok: true };
    // what the camera shows of it (the page's view: {share in view, cover of the frame}; a number is a share)
    const v0 = this.view ? this.view(card) : null;
    const view = v0 === null ? { share: 1, cover: 1 } : typeof v0 === "number" ? { share: v0, cover: v0 } : v0;
    if (view.share < cfg.view.min_share || view.cover < (cfg.view.min_cover ?? 0)) return { changed: 0, view, ok: false, why: "too little of it in the camera's view" };
    const spec = this.specOf(kind);
    const I = intensityOf(cfg, level), Ic = I;
    const pick = this._pickColour(kind, card, { preview: true });
    const col = pick ? pick.rgb : null;
    let ch = 0, n = 0;
    const sc = (c, k) => [c[0] * k, c[1] * k, c[2] * k];
    const test = (before, lvNow, lvPeak, after) => {
      const bNow = sc(before, lvNow), bPeak = sc(before, lvPeak), la = labOfLinear(after)[0];
      const brighter = la >= Math.max(labOfLinear(bNow)[0], labOfLinear(bPeak)[0]) - 3;
      const d = Math.min(deltaE(bNow, after), deltaE(bPeak, after));
      if (d > KICK_VISIBLE.de + VIS_DE_MARGIN && brighter) ch++;
      n++;
    };
    if (card.heads.length) {
      const slots = this._slotsFor(card, col);
      for (let m = 0; m < card.heads.length; m++) {
        const i = card.heads[m], w = this.p.wheels[i], now = this._headColour(i);
        const after = sc(col ? (w && slots[m] >= 0 ? w[slots[m]] : col) : now, I);
        test(now, this.preH[i * 7 + 2], this.recentH[i], after);
      }
    }
    for (const c of card.cells) { const now = this._cellColour(c); test(now, this.preC[c * 4], this.recentC[c], sc(col || now, Ic)); }
    const changed = n ? ch / n : 0;
    return { changed, view, ok: changed >= Math.min(0.95, KICK_VISIBLE.share + VIS_MARGIN) };
  }
  // A press: a kick of `kind` at velocity vel and beat position pos. hold: it stays lit until release() (the page's pads);
  // otherwise it is a tap. Returns the kick's record (null only if every area is lit by another kick).
  press(kind, vel, pos, { hold = false } = {}) {
    kind = this.kindOf(kind) || this.cfg.kindNames[0];
    const cfg = this.cfg, spec = this.specOf(kind);
    this.presses++;
    // the beat a press belongs to is the nearest one (the receipts' bookkeeping); its light starts AT THE PRESS. Daniel,
    // 2026-10-27: "currently kick doesnt always trigger when its pressed ... can we make sure that the kick buttons are
    // responsive" -- an early press used to wait for its beat line, up to half a beat of nothing. v0's kick (no block)
    // keeps waiting for the line.
    const onset = Math.round(pos), from = cfg.legacy ? Math.max(onset, pos) : pos;
    const band = bandFor(cfg, vel);
    const level = this.levelOfVel(vel);
    this.motions.press(pos);
    // a press while this button's area is still lit RE-STRIKES it: the same area, held again, and the kind's repeat (the
    // next colour of about the same luminance, or a fresh motion)
    if (!cfg.legacy) {
      const prev = this.list.filter((k) => k.kind === kind && !k.dead && k.supersededAt === undefined).pop();
      if (prev && pos >= prev.from - 1e-6 && this._env(prev, pos) >= 0.5) return this._restrike(prev, vel, pos, band, level, hold, spec);
    }
    // a new press of a button lets go of that button's held kick (one finger, one area)
    for (const k of this.list) if (k.kind === kind && k.held) this._release(k, pos);
    // the areas live kicks show (held, or still at 5 % or more): another button's are never dealt; this button's own
    // fading one only when nothing else shows the hit
    const live = this.list.filter((k) => !k.dead && (k.held || this._env(k, pos) >= 0.05));
    const aliveOther = new Set(live.filter((k) => k.kind !== kind).map((k) => k.cardIndex));
    const aliveMine = new Set(live.filter((k) => k.kind === kind).map((k) => k.cardIndex));
    const lastMine = this.lastOf[kind] ?? -1;
    let passed = 0;
    const judged = new Map();
    const shows = (c) => { let j = judged.get(c); if (!j) { j = this.judge(c, kind, level, band); judged.set(c, j); if (!j.ok) passed++; } return j.ok; };
    const ci = this.deck.deal((c, pass) => {
      if (aliveOther.has(c)) return false;
      if (pass === -1 || pass === 4) return true;                     // a forced card (tests and receipts); the last resort
      if (pass === 2) return shows(c);                                // it shows: the button's last or its own fading allowed
      if (aliveMine.has(c)) return false;
      if (pass === 3) return c !== lastMine;                          // nothing shows anywhere: the next area anyway
      if (c === lastMine || (c === this.deck.last && this.cards.length > 2)) return false;
      return pass === 0 ? shows(c) && this.cards[c].zone !== this.lastZone : shows(c);
    }, this.view ? (c) => { const j = judged.get(c); const v = j ? j.view : this.view(this.cards[c]); return typeof v === "number" ? v : v.cover; } : null);
    this.passedOver += passed;
    if (ci < 0) { this.unlit++; return null; }
    const card = this.cards[ci];
    // a re-press on this button's own fading area takes it over from the moment the new kick lights
    for (const k of this.list) if (k.kind === kind && k.cardIndex === ci) k.supersededAt = from;
    this.lastOf[kind] = ci; this.lastZone = card.zone;
    // was the area dark when it was dealt (then the card's own pan and tilt aim it)?
    let dark = true;
    for (const i of card.heads) if (this.recentH[i] > 0.05) { dark = false; break; }
    const rec = { kind, card, cardIndex: ci, round: this.deck.round, onset, from, pressPos: pos, lastPressPos: pos, vel, band: band.name,
                  levelTarget: level, level, held: !!hold, releasedAt: null, holdEnd: null, dark, motion: null, attached: false,
                  strobing: false, maskOn: true, lit: false, dead: false, presses: 1, colour: null, slots: null, colourAtS: this._secs(pos),
                  punchFrom: spec.punch > 0 && this._can("punch") ? from : -Infinity, chaseShift: 0, comb: 0, prevPal: -1, deferred: 0, heldSince: pos, mHold: 0, still: false };
    this._paint(rec, this._pickColour(kind, card, { self: rec }));
    if (band.sweep && spec.motion === "bands") rec.motion = this._motion(card, band, vel, from);
    if (!hold) this._release(rec, pos);
    this.list.push(rec);
    this._log(rec, passed, false);
    return rec;
  }
  _paint(rec, col, restrike = false) { rec.colour = col; rec.slots = col ? this._slotsFor(rec.card, col.rgb, { restrike }) : null; }
  _restrike(k, vel, pos, band, level, hold, spec) {
    this.restrikes++;
    k.held = !!hold; k.releasedAt = null; k.holdEnd = null; k.attached = k.attached && k.held;
    k.lastPressPos = pos; k.vel = vel; k.band = band.name; k.levelTarget = level; k.presses++;
    // every re-strike flips the area's comb (alternate heads, and alternate stripes of a twentieth of its LEDs along its
    // order, at full and at governor.comb_floor): a change a head shows within its dimmer motor's 0.04 s, where its colour
    // wheel needs 0.12 s a slot, and the area's mean brightness stays put from one tap to the next
    if (this._can("comb")) k.comb = (k.comb % 2) + 1;
    if (spec.repeat === "colour" && spec.colour === "palette" && this._can("colour")) { this._paint(k, this._stepColour(k), true); k.colourAtS = this._secs(pos); }
    k.heldSince = pos;                     // a new press is a new hold (the strobe's hold_s counts from it)
    // a fresh motion every re-strike (the sweep band's, at least: a roll always moves) and the chase jumped on -- both move
    // light about the frame, so they too wait for the limiter's headroom
    if (spec.repeat === "motion" && this._can("motion")) {
      const b = band.sweep ? band : this.cfg.bands.find((x) => x.sweep) || band;
      k.motion = b.sweep ? this._motion(k.card, b, Math.max(vel, b.from), pos) : null; k.mHold = 0;
      k.chaseShift = (k.chaseShift + 0.37) % 1;
    } else if (spec.repeat !== "motion" && spec.motion === "bands" && band.sweep && this._can("motion")) { k.motion = this._motion(k.card, band, vel, pos); k.mHold = 0; }
    if (!hold) this._release(k, pos);
    this._log(k, 0, true);
    return k;
  }
  _log(k, passed, restrike) {
    if (this.log.length >= 64) this.log.shift();
    this.log.push({ kind: k.kind, row: k.card.name, onset: k.onset, pressPos: +k.lastPressPos.toFixed(4), vel: +k.vel.toFixed(3), band: k.band,
                    colour: this._hexOf(k), motion: k.motion ? k.motion.id : null, passed, restrike });
  }
  _hexOf(k) { return k.colour ? (k.colour.pal >= 0 ? this.palette[k.colour.pal].hex : (this.kindRoles && this.kindRoles[k.kind] ? this.kindRoles[k.kind].hex : this.cfg.white.colour)) : null; }
  _motion(card, band, vel, from) {
    const p = this.p, perMs = p.perMs || 400, bar = p.barAnchor || 0;
    const d = this.motions.deal({ pos: from - bar, perMs, vel, pinClass: band.sweep.class, looping: true, gaps: false, bank: "both",
                                  lifeBeats: CLASSES[band.sweep.class].beats });
    if (!d) return null;
    const m = d.m;
    const st = { m, p0: d.p0 + bar, p1: d.p1 + bar, beats: d.beats, looping: true, rev: d.rev, rotK: d.rotK };
    // heads: each one's sign (the motion's mode, the transform's mirrors) and the throw the motor can make
    const nH = card.heads.length;
    const sign = new Float64Array(nH);
    const aimN = (m.aim || 0) / 0.5, spreadN = (m.spread || 0) / 0.5;
    let smax = 0;
    for (let k = 0; k < nH; k++) {
      const side = card.headSide[k] || 1, lower = !!card.headLower[k];
      let s = aimN * headSign(m.mode, { side, bank: "A", lower }, card.headRank[k]);
      if (d.mx) s = -s;
      if (d.my && lower) s = -s;
      s += spreadN * side;
      sign[k] = s; smax = Math.max(smax, Math.abs(s));
    }
    // the throw: the band's degrees x the dealer's amplitude (velocity, the press's place in the bar), cut so the motion's
    // steepest moment asks at most 80 % of the slowest head's tilt speed. Its acceleration is left to the motor model
    // (programmer.js Slew, 0.2 s to full speed): a sharp start is rounded off there, as a real head rounds it off.
    const want = band.sweep.deg * d.amp;
    let deg = want, peakDegPerS = 0;
    if (nH && smax > 0) {
      const span = Math.max(1e-3, Math.min(d.p1 - d.p0, d.beats) * perMs / 1000);
      const slope = m.stats.slope / Math.max(0.1, 1 - (m.lag || 0));
      let vmax = Infinity;
      for (const i of card.heads) vmax = Math.min(vmax, p.slews[i].tilt.vmax);
      const rate = (A) => (A * smax * slope) / span;
      if (rate(deg) > 0.8 * vmax) deg *= (0.8 * vmax) / rate(deg);
      peakDegPerS = rate(deg);
    }
    // LED cells: the same motion as a chase, its order wave at least `lag` wide so it travels along the row
    const chaseSt = card.cells.length ? { ...st, m: { ...m, lag: Math.max(m.lag || 0, this.cfg.chase.lag) }, rotK: 0 } : null;
    return { id: d.id, label: d.label, cls: d.cls, xf: d.xf, amp: d.amp, want, deg, peakDegPerS, st, sign, chaseSt };
  }
  _release(k, pos) {
    if (k.releasedAt !== null) return;
    k.held = false; k.releasedAt = pos;
    // lit at least tap_hold after its start, and (round 2) at least linger_s after its last press
    const linger = this.cfg.governor.linger_s * 1000 / (this.p.perMs || 400);
    k.holdEnd = Math.max(pos, k.from + this.cfg.tap_hold_beats, k.lastPressPos + linger);
    k.attached = false;                    // its strobe mask is frozen where it is: the fade adds no edge
  }
  release(kind, pos) { kind = this.kindOf(kind); for (const k of this.list) if (k.kind === kind && k.held) this._release(k, pos); }
  // the live level (the finger's height on the pad): every held kick of this kind
  setLevel(kind, v) { kind = this.kindOf(kind); if (!Number.isFinite(v)) return; for (const k of this.list) if (k.kind === kind && k.held) k.levelTarget = clamp01(v); }
  _env(k, pos) {
    if (pos < k.from - 1e-6) return 0;
    if (k.held) {
      if (pos - k.from >= this.cfg.max_hold_beats) this._release(k, pos);        // a stuck pad lets go
      else return 1;
    }
    return pos <= k.holdEnd ? 1 : Math.exp(-(pos - k.holdEnd) / this.cfg.release_beats);
  }
  // v0's kickLevel: the brightest kick now (before its strobe and punch)
  levelNow(pos) { let lv = 0; for (const k of this.list) lv = Math.max(lv, this._env(k, pos) * intensityOf(this.cfg, k.level)); return lv; }
  // the strobe's period (beats) and lit share at this tempo: the shortest of the set's divisions at or under the cap
  _strobeGrid(perMs) {
    const S = this.cfg.strobe, bps = 1000 / perMs, hz = Math.min(STROBE_HZ_CAP, S.max_hz);
    const divs = S.beats.slice().sort((a, b) => a - b);
    let P = divs.find((x) => bps / x <= hz + 1e-9);
    if (P === undefined) P = bps / hz;
    const minB = STROBE_MIN_EDGE_S * bps;
    const onB = Math.min(P - minB, Math.max(minB, S.on * P));
    return { P, onB };
  }
  // the programmer's step 3: remember the frame before the kicks, then light the kicks' areas
  apply(pos, tSec, dt) {
    const p = this.p, tH = p.tH, tC = p.tC, cfg = this.cfg;
    this.preH.set(tH); this.preC.set(tC);
    if (p.kickSlot) p.kickSlot.fill(-1);
    const dB = this.lastPos === null ? 0 : Math.max(0, pos - this.lastPos);
    this.lastPos = pos;
    const fall = cfg.recent_fall_per_beat * dB;
    for (let i = 0; i < p.nH; i++) { const d = tH[i * 7 + 2]; this.recentH[i] = Math.max(d, this.recentH[i] - fall); }
    for (let c = 0; c < p.nC; c++) { const d = tC[c * 4]; this.recentC[c] = Math.max(d, this.recentC[c] - fall); }
    if (!this.list.length) return;
    // the strobe clock: it runs while some held kick of a strobing kind is at the top of its level (or has joined it)
    const S = cfg.strobe, clk = this.clock;
    const g = this._strobeGrid(p.perMs || 400);
    clk.P = g.P; clk.onB = g.onB;
    // the strobe needs a deliberate hold: the pad held for strobe.hold_s with the level in the top band (a tap is a hit,
    // never a strobe)
    const holdB = (S.hold_s ?? 0) * 1000 / (p.perMs || 400);
    const wantsStrobe = (k) => k.held && this.specOf(k.kind).strobe && k.levelTarget >= S.from_level - 1e-9 && pos - k.heldSince >= holdB - 1e-9;
    let wanted = false;
    for (const k of this.list) if (k.lit && wantsStrobe(k)) wanted = true;
    // the first row to want the strobe joins at once (the strobe engages as the level crosses into the band), and the
    // clock does not flip within an edge's spacing of that row's own light-up; later rows join while the clock is lit
    if (wanted && clk.on && !this.list.some((k) => k.attached)) {
      for (const k of this.list) if (k.lit && wantsStrobe(k)) { k.attached = true; clk.lastEdge = Math.max(clk.lastEdge, k.litAt); }
    }
    let want = true;
    if (wanted || this.list.some((k) => k.attached)) {
      const ph = (((pos - (p.barAnchor || 0)) % g.P) + g.P) % g.P;
      want = ph < g.onB;
    }
    if (want !== clk.on && tSec - clk.lastEdge >= STROBE_MIN_EDGE_S - 1e-9 && (want || this._can("strobe"))) { clk.on = want; clk.lastEdge = tSec; }
    const slewK = 1 - Math.exp(-Math.max(0, dt) / cfg.level.slew_s);
    const perS = (p.perMs || 400) / 1000;
    for (const k of this.list) {
      let env = this._env(k, pos);
      if (pos < k.from - 1e-6) continue;                                   // (v0) an early press waits for its line
      if (!k.lit) {
        k.lit = true; k.litAt = tSec;
        // a kick lighting while the clock is idle starts the clock's count from its own edge
        if (wantsStrobe(k) && !this.list.some((o) => o !== k && o.attached)) clk.lastEdge = Math.max(clk.lastEdge, tSec);
      }
      // a fade about to start waits (up to governor.defer_s) while the limiter's budget is spent
      if (k.releasedAt !== null && !cfg.legacy && pos > k.holdEnd && pos - k.holdEnd < 0.1 && k.deferred < cfg.governor.defer_s * 1000 / (p.perMs || 400) && !this._can("fade")) {
        k.deferred += pos - k.holdEnd; k.holdEnd = pos;
        env = this._env(k, pos);
      }
      if ((k.releasedAt !== null && pos > k.holdEnd && this._env(k, pos) < 0.004) || (k.supersededAt !== undefined && pos >= k.supersededAt - 1e-6)) { k.dead = true; continue; }
      k.level += (k.levelTarget - k.level) * slewK;
      // join or leave the strobe clock only while it is on (so a joining or leaving row adds no edge of its own)
      if (k.held) {
        const wants = wantsStrobe(k);
        if (wants && !k.attached && clk.on) k.attached = true;
        else if (!wants && k.attached && clk.on) k.attached = false;
        k.maskOn = k.attached ? clk.on : true;
      }
      k.strobing = k.attached;
      const spec = this.specOf(k.kind);
      const off = !k.maskOn;                                               // the strobe clock's dark phase
      // the intensity: the level's curve, with the punch of a fresh hit on top (overshoot, settling over punch_s)
      const punchAge = (pos - k.punchFrom) * perS, ps = cfg.governor.punch_s || 0;
      const punch = spec.punch > 0 && ps > 0 && punchAge >= 0 && punchAge < ps ? spec.punch * (1 - punchAge / ps) : 0;
      const I = Math.min(1, intensityOf(cfg, k.level) + punch), floor = S.floor, w = env;
      const card = k.card, mo = k.motion;
      // the motion's own clock: it stands still while the limiter's budget is spent (under governor.need) and moves on
      // once there is room for one more (governor.need + 1), from where it stood
      if (mo && !cfg.legacy) {
        if (k.still ? this.headroom >= cfg.governor.need + 1 : this.headroom < cfg.governor.need) k.still = !k.still;
        if (k.still) { k.mHold = (k.mHold || 0) + dB; this.gov.still++; }
      }
      const mpos = pos - (k.mHold || 0);
      if (!spec.override) {
        // a lift (v0's kick, and any kind that does not override): highest takes precedence, nothing else
        const lv = env * I;
        for (const i of card.heads) tH[i * 7 + 2] = Math.max(tH[i * 7 + 2], lv);
        for (const c of card.cells) tC[c * 4] = Math.max(tC[c * 4], lv);
        continue;
      }
      // heads: the kick's intensity over the look's (latest takes precedence, crossfading back as the kick fades), the
      // wheel to the kick's slot, the dark area's aim, the sweep
      for (let m = 0; m < card.heads.length; m++) {
        const i = card.heads[m], b = i * 7;
        const combed = k.comb > 0 && ((card.headRank[m] + k.comb) & 1) === 1;
        const kd = off ? floor : combed ? I * cfg.governor.comb_floor : I;
        tH[b + 2] += (kd - tH[b + 2]) * w;
        if (k.slots && k.slots[m] >= 0 && w > 0.02 && p.kickSlot) p.kickSlot[i] = k.slots[m];
        if (k.dark) { if (card.pan !== null) tH[b] = card.pan; if (card.tilt !== null) tH[b + 1] = card.tilt; }
        if (mo && mo.deg > 0) {
          const v = valueAt(mo.st, mpos, card.headRank[m], card.heads.length);
          const t = tH[b + 1] + mo.deg * v * mo.sign[m];
          tH[b + 1] = Math.max(-135, Math.min(135, t));
        }
      }
      // LED cells: the kick's intensity (a chase on the sweep bands, solid while strobing) and the kick's colour over the
      // look's, crossfading back to the look's as the kick fades
      if (card.cells.length) {
        const chase = mo && mo.chaseSt && !k.strobing ? mo.chaseSt : null;
        const fl = cfg.chase.floor, role = k.colour ? k.colour.role : -1, shift = Math.round(k.chaseShift * 1000);
        for (let m = 0; m < card.cells.length; m++) {
          const c = card.cells[m], b = c * 4;
          let x = I;
          if (chase) x *= fl + (1 - fl) * Math.min(1, Math.abs(valueAt(chase, mpos, (card.cellQ[m] + shift) % 1001, 1001)));
          if (k.comb > 0 && ((Math.floor(card.cellQ[m] / 50) + k.comb) & 1) === 1) x *= cfg.governor.comb_floor;
          const kd = off ? floor : x;
          tC[b] += (kd - tC[b]) * w;
          if (role >= 0) {
            const lead = tC[b + 1] <= 0.5 ? tC[b + 2] : tC[b + 3];          // the look's main role under the paint
            tC[b + 2] = lead; tC[b + 3] = role; tC[b + 1] = w;
          }
        }
      }
    }
    if (this.list.some((k) => k.dead)) this.list = this.list.filter((k) => !k.dead);
  }
  status() {
    return { api: KICK_API, legacy: this.cfg.legacy, kinds: this.cfg.kindNames.slice(), presses: this.presses, presses_unlit: this.unlit,
             headroom: this.headroom, governor_held_back: { ...this.gov },
             restrikes: this.restrikes, areas_passed_over: this.passedOver, round: this.deck.round,
             clock: { on: this.clock.on, period_beats: this.clock.P, on_beats: +this.clock.onB.toFixed(3) },
             live: this.list.map((k) => ({ kind: k.kind, row: k.card.name, band: k.band, level: +k.level.toFixed(3), target: +k.levelTarget.toFixed(3),
                                           intensity: +intensityOf(this.cfg, k.level).toFixed(3), held: k.held, strobing: k.strobing,
                                           colour: this._hexOf(k), motion: k.motion ? k.motion.id : null, onset: k.onset, presses: k.presses })),
             log: this.log.slice(-32) };
  }
}
