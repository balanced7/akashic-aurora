// VJ colour themes: arsenal/web/vj-themes.js (pure ES module: no DOM, no WebGL). The library: arsenal/web/vj-themes.json.
// Tests: tests/vj_themes.test.mjs (node --test) and tests/test_vj_themes_library.py (the pad and red rules in Python).
//
// Daniel, 2026-10-24: "I want there to be a lot of variety and strong color themes". The build spec is slice S5 of
// research/reviewed/keylab-liberation-2026-10-22/vj-lasers-v2-and-colour-themes-2026-10-24.md (sections 2.1-2.3 and 4.1):
// 21 themes in 8 families, built from the measured Q-dance palettes. Two colours per section, white is the peak, and a
// saturated red is held (shown steadily on the scene), never strobed.
//
// This module decides, without a browser:
//   - whether a library is sound: every pad stand-in readable on the KeyLab pads, no saturated red that a laser, a
//     strobe, a burst or a flash can emit, every fader detent, playbook and Camelot entry resolving
//                                                                                     validateLibrary, loadLibrary
//   - which theme: by the theme fader's detent (a curated walk round the colour wheel), by a step (a pad or button),
//     by the song's key (Camelot number, then family, then the family's playbook) and by the section (the playbook)
//                                      themeAtFader, FaderPicker, stepTheme, parseKey, familyForKey, themeForSection
//   - when it lands: Daniel's picks on the next bar, automatic ones on a phrase line and at least 8 bars apart, and a
//     big hue jump (or a flagged theme) cuts through black on the beat              ThemeDirector, landing, needsDip
//   - what a theme gives: the scene's four palette stops (linear rgb, the strip's row 2 layout), the kick glow, the
//     lasers' two-colour pair with their strobe and burst colours and legal colour modes, the effects' colours (with
//     twelve red-safe hit colours for the DAW pads' effects), and the pad lights (LED stand-ins, never screen colours)
//                                                                                  themeLook, padLeds, familyLed
// The page owns the clock, the GL and the posting: it hands this module a clock adapter and reads plans back. Nothing
// here schedules a timer; ThemeDirector.tick(now) is called from the frame loop.

import { linearToOklab, oklabToLinear, rgbToHex, EFFECTS, CONTROLS, DEFAULT_PAD_MAP } from "./vj-core.js";
import { nextDownbeatAt } from "./vj-show.js";

export const THEMES_API = "arsenal.vj-themes/v1";

// --------------------------------------------------------------------------------------------------- the rules --
export const ROLES = Object.freeze(["A", "B", "W"]);            // primary, secondary, accent / white-hot
const FX_ROLES = new Set(["A", "B", "W", "line", "white"]);
// The KeyLab pads render hues from orange to lime (HLS 15-100 degrees) close to white, and low saturation reads as
// white too: a stand-in is pure white, or has HLS saturation above 0.5 and a hue outside the zone (tests/test_keylab_w0.py)
export const LED_WASH_ZONE = Object.freeze([15, 100]);
export const LED_MIN_SAT = 0.5;
// Saturated red (WCAG 2.3.1's red flash): R/(R+G+B) at or above 0.8 on display OR linear values (WCAG does not say which)
export const RED_RATIO = 0.8;
export const CHOKE_LED = "#ff3c00";        // Choke's own #ff9a1f (hue 36) washes to white on the pads (spec 2.2)
export const LASER_TIER_LEVEL = Object.freeze([1, 0.6, 0.8, 1]);   // pad 2's light by laser tier: none, 1, 2, 3 (spec 1.8)
export const FADER_REST_MS = 150;          // a fader pick lands once the fader has rested this long on one detent
export const HOLD_BARS = 8;                // an automatic theme holds at least one 8-bar phrase
export const KEY_CONF = 0.6;               // chordsense's key takes over at this confidence...
export const KEY_STABLE_BARS = 8;          // ...once no other key has arrived for this long
export const DIP_HUE_DEG = 100;            // primaries further apart than this cut through black
export const GRADIENT_MAX_DEG = 80;        // a gradient fan only between hues this close (else it passes through grey)
const CHROMA_MIN = 0.03;                   // OKLCH chroma below this has no hue worth comparing (whites, bone, brass)
const FALLBACK_BAR_MS = 1600;              // one bar at 150 BPM: "within a bar" when no tempo is known

// Daniel's family tabs light in their family's colour. Pads cannot show orange or gold, so each family is shown by the
// stand-in of one of its own themes, chosen so neighbouring tabs differ as much as the pads allow.
const FAMILY_LED = Object.freeze({
  ritual: ["red-tribe", "A"], fire: ["fire-and-ice", "A"], celestial: ["uv-euphoria", "A"], night: ["night-sea", "B"],
  green: ["laser-green", "A"], pyro: ["pink-pyro", "A"], worship: ["cathedral-jewel", "A"], line: ["bone-line", "W"],
});

// ---------------------------------------------------------------------------------------------------- colours --
const HEX = /^#[0-9a-fA-F]{6}$/;
export const isHex = (v) => typeof v === "string" && HEX.test(v);
const clamp01 = (x) => (x > 1 ? 1 : x < 0 ? 0 : x);
export function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
const decode = (c) => { const s = c / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
export function hexToLinear(hex) { return hexToRgb(hex).map(decode); }
export function linearToHex(lin) { return rgbToHex(lin[0], lin[1], lin[2]); }

// HLS exactly as Python's colorsys.rgb_to_hls (the rule's own test uses it): channels 0..255 in, hue in degrees
export function hls(rgb) {
  const r = rgb[0] / 255, g = rgb[1] / 255, b = rgb[2] / 255;
  const maxc = Math.max(r, g, b), minc = Math.min(r, g, b), range = maxc - minc, l = (maxc + minc) / 2;
  if (range === 0) return { h: 0, l, s: 0 };
  const s = l <= 0.5 ? range / (maxc + minc) : range / (2 - maxc - minc);
  const rc = (maxc - r) / range, gc = (maxc - g) / range, bc = (maxc - b) / range;
  const h = r === maxc ? bc - gc : g === maxc ? 2 + rc - bc : 4 + gc - rc;
  return { h: ((((h / 6) % 1) + 1) % 1) * 360, l, s };
}

// The pad rule for a stand-in (a colour as the theme names it, at full brightness).
export function ledRule(hex) {
  if (!isHex(hex)) return { ok: false, reason: "not a #rrggbb colour" };
  const rgb = hexToRgb(hex);
  if (rgb[0] === 255 && rgb[1] === 255 && rgb[2] === 255) return { ok: true, white: true, h: 0, s: 0 };
  const { h, s } = hls(rgb);
  if (!(s > LED_MIN_SAT)) return { ok: false, h, s, reason: `HLS saturation ${s.toFixed(2)} reads as white on the pads` };
  if (h >= LED_WASH_ZONE[0] && h <= LED_WASH_ZONE[1]) return { ok: false, h, s, reason: `hue ${h.toFixed(0)} washes to white` };
  return { ok: true, white: false, h, s };
}

// The pad rule for a colour as posted (a stand-in times a brightness): dimming keeps a colour's identity, so the check is
// on the colour scaled back to full brightness; a grey is white dimmed, and black is off.
export function ledPostedOk(hex) {
  if (!isHex(hex)) return false;
  const rgb = hexToRgb(hex), m = Math.max(rgb[0], rgb[1], rgb[2]);
  if (m === 0 || (rgb[0] === rgb[1] && rgb[1] === rgb[2])) return true;
  const { h, s } = hls(rgb.map((c) => (c * 255) / m));
  return s > LED_MIN_SAT && !(h >= LED_WASH_ZONE[0] && h <= LED_WASH_ZONE[1]);
}

export function redRatios(hex) {
  const rgb = hexToRgb(hex), lin = rgb.map(decode);
  const se = rgb[0] + rgb[1] + rgb[2], sl = lin[0] + lin[1] + lin[2];
  return { encoded: se > 0 ? rgb[0] / se : 0, linear: sl > 0 ? lin[0] / sl : 0 };
}
// a #rrggbb colour, or a linear [r, g, b] (judged as it will be displayed: rounded to #rrggbb)
export function isSaturatedRed(colour) {
  const r = redRatios(typeof colour === "string" ? colour : linearToHex(colour));
  return r.encoded >= RED_RATIO || r.linear >= RED_RATIO;
}

// OKLCH through the page's own OKLab (vj-core.js), hue in degrees 0..360
const labTmp = [0, 0, 0];
export function toOklch(lin) {
  linearToOklab(lin[0], lin[1], lin[2], labTmp);
  let h = (Math.atan2(labTmp[2], labTmp[1]) * 180) / Math.PI;
  if (h < 0) h += 360;
  return { L: labTmp[0], C: Math.hypot(labTmp[1], labTmp[2]), h };
}
// linear rgb for an OKLab colour, or null outside sRGB (vj-core clamps a negative channel to 0, which a round trip shows)
function labInGamut(L, a, b) {
  const out = oklabToLinear(L, a, b, [0, 0, 0]);
  if (out[0] > 1 + 1e-6 || out[1] > 1 + 1e-6 || out[2] > 1 + 1e-6) return null;
  linearToOklab(out[0], out[1], out[2], labTmp);
  if (Math.abs(labTmp[0] - L) + Math.abs(labTmp[1] - a) + Math.abs(labTmp[2] - b) > 2e-3) return null;
  return out.map(clamp01);
}
// OKLCH to linear rgb, chroma reduced until it fits sRGB (lightness and hue kept)
export function fromOklch(L, C, h) {
  L = clamp01(L);
  const rad = (h * Math.PI) / 180, cos = Math.cos(rad), sin = Math.sin(rad);
  const at = (c) => labInGamut(L, c * cos, c * sin);
  const direct = at(Math.max(0, C));
  if (direct) return direct;
  let lo = 0, hi = Math.max(0, C);
  for (let i = 0; i < 20; i++) { const mid = (lo + hi) / 2; if (at(mid)) lo = mid; else hi = mid; }
  return at(lo) || oklabToLinear(L, 0, 0, [0, 0, 0]).map(clamp01);
}
// the short way round the hue circle, in degrees (0..180)
export function hueGapDeg(h1, h2) {
  const d = Math.abs((((h2 - h1) % 360) + 540) % 360 - 180);
  return d;
}
// two linear colours mixed through OKLCH, the hue turning the short way round (vj.js's oklabMix, as a pure function)
export function mixOklch(a, b, t) {
  const A = toOklch(a), B = toOklch(b);
  let ha = A.h, hb = B.h;
  if (A.C < 1e-4) ha = hb;
  if (B.C < 1e-4) hb = ha;
  let dh = hb - ha;
  dh -= 360 * Math.round(dh / 360);
  return fromOklch(A.L + (B.L - A.L) * t, A.C + (B.C - A.C) * t, ha + dh * t);
}
const TOWARD = Object.freeze({ yellow: toOklch(hexToLinear("#ffff00")).h, blue: toOklch(hexToLinear("#0000ff")).h });

// A colour a laser, strobe, burst, flash, shockwave or kick glow emits: never saturated red. A transform (a key nudge, a
// hue drift, Custom's turn of the wheel) that would make one is answered by taking chroma out until it passes.
function safeEmit(lin) {
  if (!isSaturatedRed(lin)) return lin;
  const { L, C, h } = toOklch(lin);
  let lo = 0, hi = C;
  for (let i = 0; i < 24; i++) { const mid = (lo + hi) / 2; if (isSaturatedRed(fromOklch(L, mid, h))) hi = mid; else lo = mid; }
  return fromOklch(L, lo, h);
}

// ---------------------------------------------------------------------------------------------- the library --
const roleHexOf = (t, role) => (role === "white" ? "#ffffff" : role === "line" ? t.line : ROLES.includes(role) ? t[role] : null);
const laserHexOf = (t, role) => (t.beam && t.beam[role]) || roleHexOf(t, role);
// every role a laser gate can emit (lasers, strobe and burst lists)
const emitRoles = (t) => [...t.lasers, ...t.strobe.triple, ...t.strobe.flicker, ...t.burst];

// Checks a parsed library (vj-themes.json). Returns { ok, errors, warnings }: errors are what would put a washing colour
// on the pads, a red into a strobe, or leave a detent or playbook entry pointing nowhere.
export function validateLibrary(raw) {
  const errors = [], warnings = [];
  const bad = (where, msg) => errors.push(`${where}: ${msg}`);
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return { ok: false, errors: ["the library is not an object"], warnings };
  if (raw.version !== 2) bad("version", `expected 2, found ${JSON.stringify(raw.version)}`);
  if (!Array.isArray(raw.themes) || raw.themes.length === 0) {
    bad("themes", "missing or empty");
    return { ok: false, errors, warnings };
  }
  const ids = new Set(), families = new Set();
  const isRole = (r) => ROLES.includes(r);
  const roleList = (at, name, v, len) => {
    if (!Array.isArray(v) || v.length === 0 || (len && v.length !== len) || !v.every(isRole)) {
      bad(at, `${name} must be ${len ? `${len} roles` : "a non-empty list of roles"} from A, B, W`);
      return false;
    }
    return true;
  };
  raw.themes.forEach((t, i) => {
    const at = `themes[${i}]${t && typeof t.id === "string" ? ` ${t.id}` : ""}`;
    if (!t || typeof t !== "object") { bad(at, "not an object"); return; }
    if (typeof t.id !== "string" || !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(t.id)) bad(at, "id must be lower-case words joined by hyphens");
    else if (ids.has(t.id)) bad(at, "duplicate id");
    else ids.add(t.id);
    if (typeof t.name !== "string" || !t.name) bad(at, "no name");
    if (typeof t.family !== "string" || !t.family) bad(at, "no family");
    else families.add(t.family);
    let coloursOk = true;
    for (const r of ROLES) if (!isHex(t[r])) { bad(at, `${r} is not a #rrggbb colour`); coloursOk = false; }
    for (const k of ["ground", "line"]) if (k in t && !isHex(t[k])) { bad(at, `${k} is not a #rrggbb colour`); coloursOk = false; }
    if (t.beam !== undefined) {
      if (!t.beam || typeof t.beam !== "object") { bad(at, "beam must be an object"); coloursOk = false; }
      else for (const [r, v] of Object.entries(t.beam)) {
        if (!isRole(r)) bad(at, `beam names an unknown role ${r}`);
        if (!isHex(v)) { bad(at, `beam.${r} is not a #rrggbb colour`); coloursOk = false; }
      }
    }
    // the pads: stand-ins only, each readable
    if (!t.led || typeof t.led !== "object") bad(at, "no led stand-ins");
    else for (const r of ROLES) {
      const res = ledRule(t.led[r]);
      if (!res.ok) bad(at, `led.${r} ${t.led[r]}: ${res.reason}`);
    }
    if (t.led_level !== undefined) {
      if (!t.led_level || typeof t.led_level !== "object") bad(at, "led_level must be an object");
      else for (const [r, v] of Object.entries(t.led_level)) {
        if (!isRole(r)) bad(at, `led_level names an unknown role ${r}`);
        else if (!(typeof v === "number" && v > 0 && v <= 1)) bad(at, `led_level.${r} must be in (0, 1]`);
        else if (t.led && String(t.led[r]).toLowerCase() !== "#ffffff") bad(at, `led_level.${r} dims a stand-in that is not white`);
      }
    }
    const listsOk = [
      roleList(at, "lasers", t.lasers),
      t.strobe && typeof t.strobe === "object"
        ? roleList(at, "strobe.triple", t.strobe.triple, 3) && roleList(at, "strobe.flicker", t.strobe.flicker, 2)
        : (bad(at, "no strobe roles"), false),
      roleList(at, "burst", t.burst),
    ].every(Boolean);
    if (Array.isArray(t.lasers) && t.lasers.length > 2) {
      warnings.push(`${at}: lasers names ${t.lasers.length} roles; only the first two make the pair`);
    }
    if (!Array.isArray(t.held) || !t.held.every(isRole)) bad(at, "held must be a list of roles from A, B, W");
    const held = new Set(Array.isArray(t.held) ? t.held : []);
    let fxOk = !!t.fx && typeof t.fx === "object";
    if (!fxOk) bad(at, "no fx roles");
    else for (const k of ["shockwave", "particles", "flash"]) {
      const r = t.fx[k];
      if (!FX_ROLES.has(r) || (r === "line" && !isHex(t.line))) {
        bad(at, `fx.${k} ${JSON.stringify(r)} does not resolve to a colour`);
        fxOk = false;
      }
    }
    if (fxOk && t.fx.flash !== "W" && t.fx.flash !== "white") {
      bad(at, "fx.flash must be W or white (the flash stays white or the W tint)");
    }
    for (const k of ["split_only", "one_family", "crossfade_needs_dip"]) {
      if (typeof t[k] !== "boolean") bad(at, `${k} must be true or false`);
    }
    if (!Array.isArray(t.sections) || !t.sections.every((s) => typeof s === "string")) bad(at, "sections must be a list of names");
    if (typeof t.hero !== "string") warnings.push(`${at}: no hero description`);
    if (!coloursOk) return;
    // red: every saturated red is held (scene only), and nothing a laser gate, a flash or a shockwave emits is red
    for (const r of ROLES) {
      if (isSaturatedRed(t[r]) && !held.has(r)) bad(at, `${r} ${t[r]} is saturated red but not held`);
      if (t.beam && t.beam[r] && isSaturatedRed(t.beam[r]) && !held.has(r)) {
        bad(at, `beam.${r} ${t.beam[r]} is saturated red but ${r} is not held`);
      }
    }
    for (const r of held) if (!isSaturatedRed(t[r])) warnings.push(`${at}: held role ${r} ${t[r]} is not a saturated red`);
    if (listsOk) {
      for (const r of new Set(emitRoles(t))) {
        if (held.has(r)) bad(at, `held role ${r} appears in a laser, strobe or burst list`);
        else if (isSaturatedRed(laserHexOf(t, r))) bad(at, `laser colour ${laserHexOf(t, r)} (role ${r}) is saturated red`);
      }
    }
    if (fxOk) for (const k of ["flash", "shockwave"]) {
      if (isSaturatedRed(roleHexOf(t, t.fx[k]))) bad(at, `fx.${k} ${roleHexOf(t, t.fx[k])} is saturated red`);
    }
  });
  // the theme fader: every theme exactly once, plus Custom
  if (!Array.isArray(raw.fader_order)) bad("fader_order", "missing");
  else {
    const seen = new Map();
    for (const id of raw.fader_order) seen.set(id, (seen.get(id) || 0) + 1);
    for (const id of ids) if (seen.get(id) !== 1) bad("fader_order", `${id} appears ${seen.get(id) || 0} times (expected once)`);
    for (const id of seen.keys()) if (id !== "custom" && !ids.has(id)) bad("fader_order", `unknown theme ${id}`);
    if (seen.get("custom") !== 1) bad("fader_order", "Custom must appear exactly once");
    else if (raw.fader_order[raw.fader_order.length - 1] !== "custom") warnings.push("fader_order: Custom is not at the top");
  }
  // the playbooks: every family has one, every entry a theme
  if (!raw.families || typeof raw.families !== "object") bad("families", "missing");
  else {
    for (const [fam, book] of Object.entries(raw.families)) {
      if (!book || typeof book !== "object" || !Object.keys(book).length) { bad(`families.${fam}`, "empty playbook"); continue; }
      for (const [slot, id] of Object.entries(book)) if (!ids.has(id)) bad(`families.${fam}.${slot}`, `unknown theme ${id}`);
    }
    for (const fam of families) if (!raw.families[fam]) bad("families", `no playbook for family ${fam}`);
  }
  // the key wheel: twelve Camelot numbers, each naming a family with a playbook
  if (!raw.camelot || typeof raw.camelot !== "object") bad("camelot", "missing");
  else for (let n = 1; n <= 12; n++) {
    const e = raw.camelot[String(n)];
    if (!e || typeof e.family !== "string") bad(`camelot.${n}`, "missing");
    else if (!raw.families || !raw.families[e.family]) bad(`camelot.${n}`, `family ${e.family} has no playbook`);
  }
  // the key's mode nudge
  const mode = raw.mode;
  if (!mode || typeof mode !== "object") bad("mode", "missing");
  else {
    for (const m of ["major", "minor"]) {
      const e = mode[m];
      if (!e || typeof e.dL !== "number" || !(e.chroma > 0) || typeof e.hue_nudge_deg !== "number" || !(e.toward in TOWARD)) {
        bad(`mode.${m}`, "needs dL, chroma > 0, hue_nudge_deg and toward (yellow or blue)");
      }
    }
    if (!(typeof mode.cap_deg === "number" && mode.cap_deg >= 0)) bad("mode.cap_deg", "must be a number of degrees");
  }
  return { ok: errors.length === 0, errors, warnings };
}

// Validates and indexes a library (the parsed JSON, or its text). Throws, listing every problem, when it is unsound.
export function loadLibrary(raw) {
  const data = typeof raw === "string" ? JSON.parse(raw) : JSON.parse(JSON.stringify(raw));
  const v = validateLibrary(data);
  if (!v.ok) throw new Error(`vj-themes: the library has ${v.errors.length} problem(s):\n  ${v.errors.join("\n  ")}`);
  const deepFreeze = (o) => { if (o && typeof o === "object") { Object.values(o).forEach(deepFreeze); Object.freeze(o); } return o; };
  const themes = data.themes.map(deepFreeze);
  const familyThemes = {};
  for (const t of themes) (familyThemes[t.family] ||= []).push(t.id);
  return Object.freeze({
    api: THEMES_API,
    version: data.version,
    themes: Object.freeze(themes),
    ids: Object.freeze(themes.map((t) => t.id)),
    byId: new Map(themes.map((t) => [t.id, t])),
    faderOrder: deepFreeze(data.fader_order),
    families: deepFreeze(data.families),                   // family -> { slot: theme id } (the playbooks)
    familyThemes: deepFreeze(familyThemes),                // family -> its own themes, in library order
    camelot: deepFreeze(data.camelot),
    mode: deepFreeze(data.mode),
    rules: deepFreeze(data.rules || {}),
    warnings: Object.freeze(v.warnings),
  });
}

// The page's loader: fetch, validate, index. A library that fails validation rejects (the page keeps its fader palette).
export async function fetchLibrary(url = new URL("./vj-themes.json", import.meta.url), fetchImpl = globalThis.fetch) {
  const res = await fetchImpl(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`vj-themes: ${url} answered ${res.status}`);
  return loadLibrary(await res.text());
}

// ------------------------------------------------------------------------------------------ choosing a theme --
// The theme fader: one detent per entry of fader_order (21 themes in colour-wheel order, Custom at the top), equal widths
// so a 0..127 fader gives every detent at least five positions.
export function faderIndex(lib, x) {
  const n = lib.faderOrder.length;
  return Math.min(n - 1, Math.max(0, Math.floor(clamp01(Number.isFinite(x) ? x : 0) * n)));
}
export function themeAtFader(lib, x) { return lib.faderOrder[faderIndex(lib, x)]; }
// the fader position at the centre of a theme's detent (for a HUD or a soft takeover)
export function faderCentre(lib, id) {
  const i = lib.faderOrder.indexOf(id);
  return i < 0 ? null : (i + 0.5) / lib.faderOrder.length;
}

// A pick lands once the fader has rested on one detent for restMs. Near a detent's edge the fader stays on the detent it
// is on until it moves a quarter detent past the edge, so a fader parked on a boundary does not flicker between two.
// Once another source has changed the theme (forget()), touching the fader picks its detent again, even the same one;
// a fader nobody touches never picks.
export class FaderPicker {
  constructor(lib, { restMs = FADER_REST_MS, hysteresis = 0.25 } = {}) {
    this.order = lib.faderOrder;
    this.restMs = restMs;
    this.hysteresis = hysteresis;
    this.index = -1;          // the detent last picked
    this.cand = -1;           // the detent the fader sits on now
    this.since = 0;           // when it arrived there
    this.touched = false;     // moved since the last poll that picked or passed
    this.stale = false;       // the theme has moved on from the detent last picked
  }
  move(x, nowMs) {
    const n = this.order.length, pos = clamp01(Number.isFinite(x) ? x : 0) * n;
    let i = Math.min(n - 1, Math.floor(pos));
    const ref = this.cand >= 0 ? this.cand : this.index;
    if (ref >= 0 && i !== ref && pos > ref - this.hysteresis && pos < ref + 1 + this.hysteresis) i = ref;
    if (i !== this.cand) { this.cand = i; this.since = nowMs; }
    this.touched = true;
  }
  forget() { this.stale = true; }
  // the id picked by a touched fader that has rested on a detent (a new one, or any after forget()), else null
  poll(nowMs) {
    if (!this.touched || this.cand < 0 || nowMs - this.since < this.restMs) return null;
    this.touched = false;
    if (this.cand === this.index && !this.stale) return null;
    this.index = this.cand;
    this.stale = false;
    return this.order[this.index];
  }
}

// Fader 2: inside a theme a hue drift of +-15 degrees with a centre detent ("as designed"); in Custom a turn of the wheel.
export function hueDriftFromFader(x, capDeg = 15) {
  const d = clamp01(Number.isFinite(x) ? x : 0.5) - 0.5;
  return Math.abs(d) < 0.04 ? 0 : (Math.sign(d) * (Math.abs(d) - 0.04) * capDeg) / 0.46;
}
export function customTurnFromFader(x) { return clamp01(Number.isFinite(x) ? x : 0) * 360; }

// One step along the fader's walk (a pad or a button), wrapping; Custom is not a step.
export function stepTheme(lib, id, delta = 1) {
  const order = lib.faderOrder.filter((t) => t !== "custom");
  let i = order.indexOf(id);
  if (i < 0) i = delta > 0 ? -1 : 0;
  const n = order.length, d = Math.trunc(delta) || 1;
  return order[(((i + d) % n) + n) % n];
}

// The next theme of a family (a family tab pressed again inside a bar), wrapping; a theme from elsewhere starts it.
export function nextInFamily(lib, id, family) {
  const list = lib.familyThemes[family];
  if (!list || !list.length) return id;
  const i = list.indexOf(id);
  return list[(i + 1) % list.length];
}

// The family tab's light: { hex, level } from one of the family's own stand-ins.
export function familyLed(lib, family) {
  const pick = FAMILY_LED[family];
  const t = pick && lib.byId.get(pick[0]);
  if (t && t.family === family) return { hex: t.led[pick[1]], level: (t.led_level && t.led_level[pick[1]]) || 1 };
  const first = (lib.familyThemes[family] || []).map((id) => lib.byId.get(id))[0];
  if (!first) return { hex: "#ffffff", level: 1 };
  const role = ROLES.find((r) => first.led[r].toLowerCase() !== "#ffffff") || "W";
  return { hex: first.led[role], level: (first.led_level && first.led_level[role]) || 1 };
}

// The song's key as a Camelot number. Spellings: chordsense's "Db major" / "F# minor"; a song database's "Am", "F#m",
// "C" (a bare note is major), "Ebmaj", "Bbmin"; or the Camelot code itself, "8A". Relative major and minor share a
// number, so they share a family; neighbouring numbers share 6 of 7 notes. name is the key spelled chordsense's way
// (a Camelot code is spelled with the flats chordsense uses); camelot identifies the key whatever the spelling.
const NOTE_PC = Object.freeze({ C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 });
const PC_SPELLING = Object.freeze(["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]);
function keyOf(note, pc, mode) {
  const majorPc = mode === "major" ? pc : (pc + 3) % 12;
  const number = ((((majorPc * 7) % 12) + 7) % 12) + 1;
  const letter = mode === "major" ? "B" : "A";
  return { pc, mode, number, letter, camelot: `${number}${letter}`, name: `${note} ${mode}` };
}
export function parseKey(name) {
  const s = typeof name === "string" ? name.trim() : "";
  const cam = /^(1[0-2]|[1-9])([AB])$/.exec(s);
  if (cam) {
    const majorPc = ((((Number(cam[1]) - 8) * 7) % 12) + 12) % 12;      // 8B is C major; each step round the wheel a fifth
    const mode = cam[2] === "B" ? "major" : "minor";
    const pc = mode === "major" ? majorPc : (majorPc + 9) % 12;
    return keyOf(PC_SPELLING[pc], pc, mode);
  }
  const m = /^([A-G])([#b]?)\s*([Mm]aj(?:or)?|[Mm]in(?:or)?|m)?$/.exec(s);
  if (!m) return null;
  const pc = (NOTE_PC[m[1]] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0) + 12) % 12;
  const mode = m[3] && /^m(in|$)/i.test(m[3]) ? "minor" : "major";
  return keyOf(m[1] + m[2], pc, mode);
}
export function familyForKey(lib, name) {
  const k = parseKey(name);
  const e = k && lib.camelot[String(k.number)];
  return e ? e.family : null;
}

// Sections, as the section sense (spec 1.9) or a hand names them, to the playbook slots that answer them, most specific
// first. A build or a screech lives inside another section and changes nothing; an unknown section rotates nothing.
const SECTION_SLOTS = Object.freeze({
  intro: ["intro", "quiet", "anti", "break"],
  anti: ["anti", "quiet", "intro"],
  climax: ["climax", "chorus", "drop2"],
  drop2: ["drop2", "climax", "chorus"],
  finale: ["finale", "drop2", "climax", "chorus"],
  break: ["break", "bridge", "quiet"],
  outro: ["break", "quiet", "intro"],
  piano: ["break", "quiet", "verse"],
  quiet: ["quiet", "break", "intro"],
  verse: ["verse", "break", "quiet"],
  chorus: ["chorus", "climax"],
  bridge: ["bridge", "break"],
  build: [], screech: [],
});
const SECTION_ALIAS = Object.freeze({
  "anti-climax": "anti", antilimax: "anti", drop: "climax", "drop-2": "drop2", "second-drop": "drop2",
  endshow: "finale", "end-show": "finale", "mid-outro": "outro",
});
const NO_SECTION_SLOTS = Object.freeze(["intro", "anti", "quiet", "climax", "chorus", "break"]);
// { kind, slots } for a section name or { kind, n } (n = which drop of the track: a second climax answers as drop2)
export function sectionSlots(section) {
  const kindRaw = typeof section === "string" ? section : section && typeof section.kind === "string" ? section.kind : null;
  if (!kindRaw) return null;
  let kind = kindRaw.trim().toLowerCase().replace(/[\s_]+/g, "-");
  kind = SECTION_ALIAS[kind] || kind;
  if (kind === "climax" && section && typeof section === "object" && section.n >= 2) kind = "drop2";
  const slots = SECTION_SLOTS[kind];
  return slots ? { kind, slots } : null;
}
// { slot, id } the family's playbook gives a section (null section = the first slot it has of a quiet start), or null.
// A playbook may borrow a theme from another family (Fire's anti-climax is Void Ritual). ownFamily: only the family's own
// themes answer (a family tab Daniel pressed shows that family), falling back to its first theme.
export function themeForSection(lib, family, section, { ownFamily = false } = {}) {
  const book = lib.families[family];
  if (!book) return null;
  const s = section === null || section === undefined ? { slots: NO_SECTION_SLOTS } : sectionSlots(section);
  if (!s || !s.slots.length) return null;
  const fits = (id) => !ownFamily || (lib.byId.has(id) && lib.byId.get(id).family === family);
  for (const slot of s.slots) if (book[slot] && fits(book[slot])) return { slot, id: book[slot] };
  const first = Object.entries(book).find(([, id]) => fits(id));
  if (first) return { slot: first[0], id: first[1] };
  const own = ownFamily && lib.familyThemes[family] && lib.familyThemes[family][0];
  return own ? { slot: null, id: own } : null;
}

// A change between themes whose primaries sit more than 100 degrees apart, or into or out of a theme flagged
// crossfade_needs_dip (its pair greys out in a blend), cuts through black on the beat instead of crossfading.
// fromHueDeg / toHueDeg: the turn each side is drawn with (Custom's turn of the wheel, or fader 2's drift), so Custom
// turned half way round and then stepped to a neighbour of its theme, or back to its own theme, dips too.
export function needsDip(lib, fromId, toId, { fromHueDeg = 0, toHueDeg = 0 } = {}) {
  const fromTurn = Number.isFinite(fromHueDeg) ? fromHueDeg : 0, toTurn = Number.isFinite(toHueDeg) ? toHueDeg : 0;
  if (fromId === toId && hueGapDeg(fromTurn, toTurn) < 1e-9) return false;
  const a = lib.byId.get(fromId), b = lib.byId.get(toId);
  if (!a || !b) return false;
  if (fromId !== toId && (a.crossfade_needs_dip || b.crossfade_needs_dip)) return true;
  const ha = toOklch(hexToLinear(a.A)), hb = toOklch(hexToLinear(b.A));
  if (ha.C < CHROMA_MIN || hb.C < CHROMA_MIN) return false;
  return hueGapDeg(ha.h + fromTurn, hb.h + toTurn) > DIP_HUE_DEG;
}

// The long-drop rule: every 16 bars the lasers swap which role they use (themeLook's swap option).
export const laserSwapDue = (barsIntoDrop) => Math.floor(Math.max(0, barsIntoDrop) / 16) % 2 === 1;

// ----------------------------------------------------------------------------------------------- when it lands --
// A clock adapter: { alive(now), beatMs(), nextBeatAt(now), nextBarAt(now), nextPhraseAt(now) }, each time in ms or null,
// and optionally beatsPerBar, barsPerPhrase and observe(now) (called by ThemeDirector.tick every frame).
// This one reads the page's BeatClock (vj-core.js). bars: whether the beat source numbers its bars (n % 4 === 0 is a
// downbeat: the demo does, today's engine does not say); without bars, a bar or phrase request lands on the next beat.
//
// The BeatClock numbers only the beats the engine announces. When the beat drops out it fires unnumbered flywheel beats
// on the same grid for up to 4 s, while its beat number stays on the last announced beat, so counting bars from it
// (vj-show.js's nextDownbeatAt, given the BeatClock itself) puts "the next bar" on the wrong beat. The adapter keeps its
// own count of the last beat's number, flywheel beats included, per BeatClock (a WeakMap, so an adapter built afresh each
// frame shares it), brought up to date whenever it is asked, and hands nextDownbeatAt the corrected number.
const BEAT_COUNTS = new WeakMap();
function countedBeat(bc) {
  let s = BEAT_COUNTS.get(bc);
  if (!s) {
    s = { fired: bc.count, raw: bc.n, n: bc.n, t: bc.lastBeat };
    BEAT_COUNTS.set(bc, s);
    return s;
  }
  if (bc.count !== s.fired) {
    if (bc.n !== s.raw) s.n = bc.n;                                  // an announced beat fired: its own number
    else if (s.n >= 0) {                                             // flywheel beats: whole periods on from the last one
      const p = bc.period();
      if (p > 0) s.n += Math.max(1, Math.round((bc.lastBeat - s.t) / p));
    }
    s.raw = bc.n;
    s.t = bc.lastBeat;
    s.fired = bc.count;
  }
  return s;
}
export function clockFromBeatClock(bc, { bars = false, beatsPerBar = 4, barsPerPhrase = 8 } = {}) {
  const counted = () => {
    const s = countedBeat(bc);
    return { period: () => bc.period(), alive: (now) => bc.alive(now), n: s.n, lastBeat: s.t, q: bc.q, qn: bc.qn, qlen: bc.qlen };
  };
  return {
    beatsPerBar, barsPerPhrase,
    observe: () => { countedBeat(bc); },
    alive: (now) => bc.alive(now),
    beatMs: () => bc.period(),
    nextBeatAt: (now) => bc.nextBeatAt(now),
    nextBarAt: (now) => (bars ? nextDownbeatAt(now, counted(), beatsPerBar) : null),
    nextPhraseAt: (now) => (bars ? nextDownbeatAt(now, counted(), beatsPerBar * barsPerPhrase) : null),
  };
}
// how long one quantum of the clock is (a beat, a bar or a phrase), or Infinity when the tempo is unknown
function quantumMs(clock, on) {
  const beat = clock && typeof clock.beatMs === "function" ? clock.beatMs() : 0;
  if (!(beat > 0)) return Infinity;
  const bpb = clock.beatsPerBar > 0 ? clock.beatsPerBar : 4, bpp = clock.barsPerPhrase > 0 ? clock.barsPerPhrase : 8;
  return beat * (on === "phrase" ? bpb * bpp : on === "bar" ? bpb : 1);
}
const NEXT = Object.freeze({ phrase: "nextPhraseAt", bar: "nextBarAt", beat: "nextBeatAt" });
const CHAIN = Object.freeze({ phrase: ["phrase", "bar", "beat"], bar: ["bar", "beat"], beat: ["beat"], now: [] });
// When a change asked for at nowMs lands: { atMs, on } with on = phrase | bar | beat | now. Each quantum falls back to the
// next finer one the clock knows; no clock (or a dead one) lands now.
export function landing(nowMs, clock, want = "bar") {
  if (!clock || !CHAIN[want] || (typeof clock.alive === "function" && !clock.alive(nowMs))) return { atMs: nowMs, on: "now" };
  for (const q of CHAIN[want]) {
    const f = clock[NEXT[q]];
    const t = typeof f === "function" ? f.call(clock, nowMs) : null;
    if (typeof t === "number" && Number.isFinite(t) && t >= nowMs) return { atMs: t, on: q };
  }
  return { atMs: nowMs, on: "now" };
}
function barMsOf(clock) {
  const b = clock && typeof clock.beatMs === "function" ? clock.beatMs() : 0;
  return b > 0 ? 4 * b : FALLBACK_BAR_MS;
}

// ------------------------------------------------------------------------------------------- what a theme gives --
function tintFor(lib, { mode = null, hueDeg = 0, custom = false } = {}) {
  const m = mode === "major" || mode === "minor" ? lib.mode[mode] : null;
  const cap = typeof lib.mode.cap_deg === "number" ? lib.mode.cap_deg : 15;
  const drift = Number.isFinite(hueDeg) ? hueDeg : 0;
  if (!m && drift === 0) return null;
  return {
    dL: m ? m.dL : 0, chroma: m ? m.chroma : 1, drift: custom ? drift : Math.max(-cap, Math.min(cap, drift)),
    toward: m ? TOWARD[m.toward] : null, nudge: m ? m.hue_nudge_deg : 0, cap: custom ? Infinity : cap,
  };
}
function tint(lin, t) {
  if (!t) return lin;
  const { L, C, h } = toOklch(lin);
  let dh = t.drift;
  if (t.toward !== null && C >= CHROMA_MIN) {
    let d = t.toward - h;
    d -= 360 * Math.round(d / 360);
    dh += Math.sign(d) * Math.min(Math.abs(d), t.nudge);
  }
  dh = Math.max(-t.cap, Math.min(t.cap, dh));
  return fromOklch(L + t.dL, C * t.chroma, h + dh);
}
// snap a linear colour to the #rrggbb it will be shown as, so hex and lin always agree (and the red check judged it)
function entry(role, lin) {
  const hex = linearToHex(lin);
  return Object.freeze({ role, hex, lin: Object.freeze(hexToLinear(hex)) });
}
const ledOf = (t, role) => Object.freeze({ role, hex: t.led[role], level: (t.led_level && t.led_level[role]) || 1 });
const DIAGONAL_ROLES = Object.freeze(["A", "B", "A", "W"]);   // palette stops 0-3 as LED roles (stop 2 has no stand-in)

// Everything a theme gives, for one moment. opts:
//   mode: "major" | "minor" | null  the key's nudge (major: lighter, more chroma, toward yellow; minor the opposite)
//   hueDeg: the hue drift (fader 2), capped with the key's nudge at +-15 degrees inside a theme; free in Custom
//   custom: true in Custom (the theme's pair turned round the wheel by hueDeg)
//   swap: the long-drop swap of the lasers' role (A <-> B, never onto a held role)
// The stand-ins for the pads are never tinted: they are calibrated to the device.
export function themeLook(lib, id, opts = {}) {
  const t = lib.byId.get(id);
  if (!t) throw new Error(`vj-themes: no theme ${JSON.stringify(id)}`);
  const tn = tintFor(lib, opts);
  const held = new Set(t.held);
  const scene = (hex) => tint(hexToLinear(hex), tn);
  const emit = (role, hex) => entry(role, safeEmit(scene(hex)));
  const laser = (role) => emit(role, laserHexOf(t, role));

  // the scene: stops A, B, their OKLCH midpoint, W -- linear rgb, the strip's row 2 layout (palNow / palTarget in vj.js).
  // Where a blend of the pair would grey (split_only, crossfade_needs_dip), stop 2 is A lifted by up to 0.1 L: as far as
  // it goes while keeping 85 % of A's chroma (an acid or a gold near the top of the gamut would lift into white)
  const A = scene(t.A), B = scene(t.B), W = scene(t.W);
  let mid;
  if (t.split_only || t.crossfade_needs_dip) {
    const a = toOklch(A);
    for (let k = 10; k >= 0; k--) { mid = fromOklch(a.L + k * 0.01, a.C, a.h); if (toOklch(mid).C >= 0.85 * a.C) break; }
  } else mid = mixOklch(A, B, 0.5);
  const stops = [entry("A", A), entry("B", B), entry("mid", mid), entry("W", W)];
  const palette = new Float32Array(12);
  stops.forEach((s, k) => { palette[k * 3] = s.lin[0]; palette[k * 3 + 1] = s.lin[1]; palette[k * 3 + 2] = s.lin[2]; });

  // the lasers: L1 = lasers[0], L2 = lasers[1] or W (pure white where W is a held pin, as in Limbo); strobe, flicker and
  // burst colours; the colour modes this pair allows
  let roles = [...t.lasers];
  if (opts.swap) roles = roles.map((r) => (r === "A" && !held.has("B") ? "B" : r === "B" && !held.has("A") ? "A" : r));
  const L1 = laser(roles[0]), L2 = roles[1] ? laser(roles[1]) : held.has("W") ? emit("white", "#ffffff") : laser("W");
  const triple = t.strobe.triple.map(laser), flicker = t.strobe.flicker.map(laser), burst = t.burst.map(laser);
  const c1 = toOklch(L1.lin), c2 = toOklch(L2.lin);
  const two = L1.hex !== L2.hex;
  const gap = c1.C >= CHROMA_MIN && c2.C >= CHROMA_MIN ? hueGapDeg(c1.h, c2.h) : null;
  const gradientOk = !t.split_only && two && (gap === null || gap <= GRADIENT_MAX_DEG);
  const modes = ["M1"];
  if (!t.split_only && two) modes.push("M2");
  if (gradientOk) modes.push("M3");
  modes.push("M4");
  if (two) modes.push("M5", "M6");
  if (flicker[0].hex !== flicker[1].hex) modes.push("M7");
  modes.push("M8");
  if (two) modes.push("M9");

  // the effects; the flash and the kick glow take the theme's flash colour (W, or white where W is a pin). The particles
  // keep the scene's colour (an ember may be a held red); held marks a colour to show steadily, never flashed: the theme's
  // own colour is a held red, or the colour actually emitted (after the key's nudge, the drift or Custom's turn) is one.
  const partHex = roleHexOf(t, t.fx.particles), particles = entry(t.fx.particles, scene(partHex));
  // the pads' hit colours: vj.js colours each DAW pad's effects (the shockwave, the classic laser, the particles, the
  // strip's row 3 that the preset scenes react to) from the palette stops on a diagonal. These are the same stops made
  // safe to flash: a held role hits as the lasers' first colour, any other saturated red loses chroma until it passes.
  const padHits = Array.from({ length: 12 }, (_, i) => {
    const s = stops[((i % 4) + ((i / 4) | 0)) % 4];
    if (held.has(s.role)) return Object.freeze({ role: s.role, hex: L1.hex, lin: L1.lin });
    return isSaturatedRed(s.hex) ? entry(s.role, safeEmit(s.lin)) : s;
  });
  const fx = Object.freeze({
    shockwave: emit(t.fx.shockwave, roleHexOf(t, t.fx.shockwave)),
    particles: Object.freeze({ ...particles, held: isSaturatedRed(partHex) || isSaturatedRed(particles.hex) }),
    flash: emit(t.fx.flash, roleHexOf(t, t.fx.flash)),
    padHits: Object.freeze(padHits),
  });

  return Object.freeze({
    id: t.id, name: t.name, family: t.family, custom: !!opts.custom,
    sections: t.sections, hero: t.hero, held: Object.freeze([...held]),
    flags: Object.freeze({ splitOnly: t.split_only, oneFamily: t.one_family, crossfadeNeedsDip: t.crossfade_needs_dip }),
    scene: Object.freeze({
      palette, stops: Object.freeze(stops),
      ground: t.ground ? entry("ground", scene(t.ground)) : null,
      line: t.line ? entry("line", scene(t.line)) : null,
      kickGlow: fx.flash,                                  // the composite bloom on the kick (today: Hue A's complement)
    }),
    lasers: Object.freeze({
      roles: Object.freeze(roles), L1, L2, triple: Object.freeze(triple), flicker: Object.freeze(flicker),
      burst: Object.freeze(burst), splitOnly: t.split_only, hueGapDeg: gap, gradientOk,
      modes: Object.freeze(modes), burstModes: Object.freeze(modes.filter((m) => ["M2", "M3", "M5", "M8"].includes(m))),
      tailTo: L1,                                          // a burst's tail settles into L1 within 200 ms
    }),
    fx,
    pads: Object.freeze({
      A: ledOf(t, "A"), B: ledOf(t, "B"), W: ledOf(t, "W"),
      laser: ledOf(t, roles[0]),                           // pad 2: the lasers' own stand-in
      diagonal: Object.freeze(Array.from({ length: 12 }, (_, i) => ledOf(t, DIAGONAL_ROLES[((i % 4) + ((i / 4) | 0)) % 4]))),
    }),
  });
}

// The twelve DAW pads' lights for a look and the page's pad map: [{ hex, level, kind, role }]. hex is a stand-in (or a
// control colour) at full brightness and level its brightness 0..1; effect pads take the stand-ins on today's diagonal,
// the laser pad its own stand-in with the tier as brightness, control pads their colours (Choke moved out of the wash
// zone). The page multiplies level by its envelope and posts ledHexAt(light, brightness).
export function padLeds(look, padMap = DEFAULT_PAD_MAP, { tier = 0, laserAction = "laser", controls = CONTROLS } = {}) {
  const tierLevel = LASER_TIER_LEVEL[Math.max(0, Math.min(3, tier | 0))];
  return Array.from({ length: 12 }, (_, i) => {
    const action = padMap[i];
    if (action === laserAction) return { ...look.pads.laser, level: look.pads.laser.level * tierLevel, kind: "laser" };
    if (EFFECTS[action]) return { ...look.pads.diagonal[i], kind: "effect" };
    if (action === "none" || !controls[action]) return { hex: "#000000", level: 0, kind: "none", role: null };
    return { hex: action === "choke" ? CHOKE_LED : controls[action].colour, level: 1, kind: "control", role: action };
  });
}
// The #rrggbb to post for a light at a brightness 0..1. The level is in display units (a stand-in white at 0.76 is the
// researcher's grey #c2c2c2); the brightness is linear light, as the page's own pad envelope is.
export function ledHexAt(light, brightness = 1) {
  const k = clamp01(typeof light.level === "number" ? light.level : 1), g = clamp01(brightness);
  const lin = hexToRgb(light.hex).map((c) => decode(c * k));
  return rgbToHex(lin[0] * g, lin[1] * g, lin[2] * g);
}

// --------------------------------------------------------------------------------------------- the director --
// Who picks the theme, and when it lands. The page calls the input methods as events arrive and tick(now, clock) every
// frame; tick returns a change record the frame it lands ({ id, custom, from, atMs, on, cut, reason }), else null.
//
//   Daniel's picks (manual) land on the next bar (the next phrase line under Theme Lock):
//     onFader(x)      the theme fader; lands once it rests 150 ms on a detent. Pins the theme until the next track.
//     onStep(d)       one step along the fader's walk. Pins.
//     onFamilyTab(f)  a family tab: one of the family's own themes (for the current section when the section is
//                     known: the playbook's, which may borrow from another family); pressed again inside a bar, the
//                     family's next theme. Daniel's family beats key auto until the next track; sections rotate in it.
//   Automatic changes land on a phrase line, at least 8 bars after the last change of any kind, never while a pin or
//   the lock holds, and never over a pick of Daniel's still waiting to land:
//     onKey(ev)       the song's key: the database's at track start ({ src: "db" }) at once; chordsense's once it has
//                     confidence >= 0.6 and no other key (however unsure) has arrived for 8 bars. The key's family,
//                     then the playbook.
//     onSection(s)    the section: the family's playbook theme for it; a returning section returns to its theme. A
//                     section detected late (startedAt within the last bar) lands on the next bar, not the next phrase.
//   newTrack() clears the pins, Daniel's family, the key and the section memory. setLock(on) is Theme Lock.
//   onFader2(x)  fader 2 (optional): look() then draws with its drift (or Custom's turn), and the black-dip test sees it.
//   A waiting change's line is re-read from the clock every frame until it lands, so it follows a tempo that moves, a
//   tap that re-anchors the grid and the flywheel through a dropout; a line that moves earlier past the frame lands at once.
export class ThemeDirector {
  constructor(lib, { initial = "celestial-violet", keyAuto = true, rotate = true } = {}) {
    this.lib = lib;
    this.current = lib.byId.has(initial) ? initial : lib.ids[0];
    this.base = this.current;          // the theme in use (in Custom, the one whose pair is turned round the wheel)
    this.custom = false;
    this.pending = null;               // { id, custom, manual, reason, want, notBefore, atMs, on }
    this.family = null;                // the family sections rotate within
    this.familySrc = null;             // "tab" (Daniel's, until the next track) | "key"
    this.pinned = false;
    this.locked = false;
    this.keyAuto = keyAuto;
    this.rotate = rotate;
    this.key = null;                   // the key in force, spelled chordsense's way ("A minor")
    this.keyCand = null;               // { name, id, since } a chordsense key waiting out its 8 bars (id: its Camelot code)
    this.mode = null;                  // "major" | "minor": the key's nudge, for themeLook
    this.section = null;               // the section kind last heard
    this.slot = null;                  // the playbook slot it answered to
    this.memory = new Map();           // "family:slot" -> theme id, this track
    this.lastLandAt = -Infinity;       // when the last change landed (the 8-bar hold runs from it)
    this.tab = null;                   // { family, atMs } the last family-tab press
    this.fader2 = null;                // fader 2's position 0..1 when routed here (onFader2), else null
    this.shownHueDeg = null;           // the hue turn the last look() drew, null until a look is drawn after a change
    this.picker = new FaderPicker(lib);
    this.log = [];
  }

  // inputs ------------------------------------------------------------------------------------------------------
  onFader(x, nowMs) { this.picker.move(x, nowMs); }
  onFader2(x) { this.fader2 = Number.isFinite(x) ? clamp01(x) : null; }
  onStep(delta, nowMs, clock) {
    this.pinned = true;
    return this._request(stepTheme(this.lib, this._targetBase(), delta), { manual: true, reason: "step" }, nowMs, clock);
  }
  onFamilyTab(family, nowMs, clock) {
    if (!this.lib.families[family] || !this.lib.familyThemes[family]) return false;
    const again = !!this.tab && this.tab.family === family && nowMs - this.tab.atMs <= barMsOf(clock);
    this.tab = { family, atMs: nowMs };
    this.family = family;
    this.familySrc = "tab";
    this.pinned = false;
    let id;
    if (again) {
      id = nextInFamily(this.lib, this._targetBase(), family);
      if (this.slot) this.memory.set(`${family}:${this.slot}`, id);
    } else {
      id = this._pickFor(family, { own: true });
    }
    return this._request(id, { manual: true, reason: again ? "family-next" : "family" }, nowMs, clock);
  }
  onKey(ev, nowMs, clock) {
    const k = ev && parseKey(ev.name);
    if (!k) return false;
    if (ev.src === "db") { this._acceptKey(k.name, nowMs, clock, "db-key"); return true; }
    if (!(typeof ev.conf === "number" && ev.conf >= KEY_CONF)) {
      if (this.keyCand && this.keyCand.id !== k.camelot) this.keyCand.since = nowMs;   // another key heard: not quiet
      return false;
    }
    if (this.key && parseKey(this.key).camelot === k.camelot) { this.keyCand = null; return false; }
    if (!this.keyCand || this.keyCand.id !== k.camelot) this.keyCand = { name: k.name, id: k.camelot, since: nowMs };
    return true;
  }
  onSection(section, nowMs, clock, { startedAt = null } = {}) {
    const s = sectionSlots(section);
    if (!s) return false;                                 // unknown: nothing rotates
    this.section = s.kind;
    if (!s.slots.length) return false;                    // a build or a screech: the section around it holds
    const fam = this.family || this.lib.byId.get(this.base).family;
    const pick = themeForSection(this.lib, fam, s.kind);
    if (!pick) return false;
    this.slot = pick.slot;
    const mem = `${fam}:${pick.slot}`;
    if (!this.memory.has(mem)) this.memory.set(mem, pick.id);
    if (!this.rotate) return false;
    return this._auto(this.memory.get(mem), "section", nowMs, clock, startedAt);
  }
  newTrack() {
    this.pinned = false;
    this.family = null;
    this.familySrc = null;
    this.key = null;
    this.keyCand = null;
    this.mode = null;
    this.section = null;
    this.slot = null;
    this.memory.clear();
    this.lastLandAt = -Infinity;
    this.tab = null;
    if (this.pending && !this.pending.manual) this.pending = null;
  }
  setLock(on) {
    this.locked = !!on;
    const p = this.pending;
    if (!p) return;
    if (this.locked) {
      if (!p.manual) this.pending = null;                 // the lock holds the theme
      else { p.want = "phrase"; p.atMs = null; }          // Daniel's pick waits for the phrase line
    } else if (p.manual && p.want === "phrase") {
      p.want = "bar";                                     // lock off: his pick goes back to the next bar
      p.atMs = null;
    }
  }
  unpin() { this.pinned = false; }

  // the frame loop ----------------------------------------------------------------------------------------------
  tick(nowMs, clock) {
    if (clock && typeof clock.observe === "function") clock.observe(nowMs);
    const picked = this.picker.poll(nowMs);
    if (picked) {
      this.pinned = true;
      this._request(picked, { manual: true, reason: "fader", custom: picked === "custom" }, nowMs, clock);
    }
    if (this.keyCand && nowMs - this.keyCand.since >= KEY_STABLE_BARS * barMsOf(clock)) {
      this._acceptKey(this.keyCand.name, nowMs, clock, "key");
    }
    const p = this.pending;
    if (!p || !this._due(nowMs, clock)) return null;
    const toBase = p.custom ? this.base : p.id;
    const change = Object.freeze({ id: p.id, custom: p.custom, from: this.current, atMs: p.atMs, on: p.on, reason: p.reason,
                                   cut: needsDip(this.lib, this.base, toBase,
                                                 { fromHueDeg: this._hueFor(this.custom), toHueDeg: this._hueFor(p.custom) }) });
    this.current = p.id;
    this.custom = p.custom;
    if (!p.custom) this.base = p.id;
    this.lastLandAt = p.atMs;
    this.shownHueDeg = null;
    if (p.reason !== "fader") this.picker.forget();        // the fader's detent no longer names the theme in use
    this.pending = null;
    this.log.push(change);
    if (this.log.length > 64) this.log.shift();
    return change;
  }

  // what the page draws with: the look for the theme in use (opts as themeLook's; the key's mode added when key auto is
  // on, and fader 2's drift or turn when it is routed here and no hueDeg is given)
  lookOpts(extra = {}) {
    const o = { mode: this.keyAuto ? this.mode : null, custom: this.custom, ...extra };
    if (!Number.isFinite(o.hueDeg) && this.fader2 !== null) o.hueDeg = this._hueFor(o.custom);
    return o;
  }
  look(extra = {}) {
    const o = this.lookOpts(extra);
    if (!!o.custom === this.custom) this.shownHueDeg = Number.isFinite(o.hueDeg) ? o.hueDeg : 0;
    return themeLook(this.lib, this.base, o);
  }
  get state() {
    return {
      current: this.current, base: this.base, custom: this.custom, family: this.family, familySrc: this.familySrc,
      pinned: this.pinned, locked: this.locked, key: this.key, mode: this.mode, section: this.section, slot: this.slot,
      pending: this.pending ? { ...this.pending } : null,
    };
  }

  // internals ---------------------------------------------------------------------------------------------------
  _targetBase() {
    const p = this.pending;
    return p && !p.custom ? p.id : this.base;
  }
  // the hue turn a look in Custom (custom true) or inside a theme is drawn with: fader 2's when it is routed here, else
  // the turn last drawn on that side (an unknown turn counts as none)
  _hueFor(custom) {
    if (this.fader2 !== null) return custom ? customTurnFromFader(this.fader2) : hueDriftFromFader(this.fader2);
    return !!custom === this.custom && this.shownHueDeg !== null ? this.shownHueDeg : 0;
  }
  _pickFor(family, { own = false } = {}) {
    if (this.section === null) {
      if (this.lib.byId.get(this.base).family === family) return this.base;
      const first = themeForSection(this.lib, family, null, { ownFamily: own });
      return first ? first.id : this.lib.familyThemes[family][0];
    }
    const pick = themeForSection(this.lib, family, this.section);
    if (!pick) return this.lib.byId.get(this.base).family === family ? this.base : this.lib.familyThemes[family][0];
    this.slot = pick.slot;
    return this.memory.get(`${family}:${pick.slot}`) || pick.id;
  }
  _acceptKey(name, nowMs, clock, reason) {
    this.key = name;
    this.keyCand = null;
    if (!this.keyAuto) return;
    this.mode = parseKey(name).mode;
    if (this.familySrc === "tab") return;                 // Daniel's family wins until the next track
    const fam = familyForKey(this.lib, name);
    if (!fam || !this.lib.familyThemes[fam]) return;
    this.family = fam;
    this.familySrc = "key";
    this._auto(this._pickFor(fam), reason, nowMs, clock, null);
  }
  _auto(id, reason, nowMs, clock, startedAt) {
    if (this.pinned || this.locked) return false;
    const bar = barMsOf(clock);
    const notBefore = Number.isFinite(this.lastLandAt) ? this.lastLandAt + HOLD_BARS * bar : -Infinity;
    const late = typeof startedAt === "number" && nowMs - startedAt <= bar && notBefore <= nowMs;
    return this._request(id, { manual: false, reason, want: late ? "bar" : "phrase", notBefore }, nowMs, clock);
  }
  _request(id, { manual, reason, custom = false, want = null, notBefore = -Infinity }, nowMs, clock) {
    const p = this.pending;
    if (!manual && p && p.manual) return false;
    if (p && p.id === id && p.custom === custom && p.manual === manual) return false;   // already on its way
    if (id === this.current && custom === this.custom) {    // already there: a waiting change is called off
      if (p && (manual || !p.manual)) this.pending = null;
      return false;
    }
    const w = want || (this.locked ? "phrase" : "bar");
    this.pending = { id, custom, manual, reason, want: manual && this.locked ? "phrase" : w, notBefore, atMs: null, on: null };
    this._schedule(nowMs, clock);
    return true;
  }
  // the first estimate of a waiting change's line (shown in state.pending), once its hold has run out
  _schedule(nowMs, clock) {
    const p = this.pending;
    if (!p || p.atMs !== null || nowMs < p.notBefore) return;
    const l = landing(nowMs, clock, p.want);
    p.atMs = l.atMs;
    p.on = l.on;
  }
  // every frame: re-read the waiting change's line from the clock; true when it is due. The line it waits for may have
  // moved since the last frame: later (a slower tempo, a tap) or earlier. If it moved earlier past this frame (or this
  // frame is simply past it) the clock now names the line after it, more than half a quantum on from the last estimate:
  // the line has been reached, and the change lands now (recorded at the line, as the clock now places it).
  _due(nowMs, clock) {
    const p = this.pending;
    if (nowMs < p.notBefore) return false;
    const l = landing(nowMs, clock, p.want);
    const q = quantumMs(clock, l.on);
    if (l.atMs > nowMs && p.atMs !== null && l.on === p.on && l.on !== "now" && l.atMs - p.atMs > q / 2) {
      p.atMs = Math.min(nowMs, l.atMs - q);
      return true;
    }
    p.atMs = l.atMs;
    p.on = l.on;
    return nowMs >= p.atMs;
  }
}
