// arsenal/web/palettes.js -- THE PALETTE LIBRARY: thirty palettes that drive every colour on the Stage and the VJ page.
// Pure ES module (no DOM, no WebGL). Data: arsenal/web/palettes.json (format arsenal.palettes/v1). Tests:
// tests/stage_palettes.test.mjs. Design: research/in-flight/palettes-2026-10-28/DESIGN.md.
//
// Daniel, 2026-10-28: "when i tried the color options on my phone the lights just turn amber, the dns strands just change
// amber sometimes or dont change at all, i love the built in gradients you built for the dna strands can we make more high
// quality color theme presets and animations. I want us to have 30 color palates that are high quality and what is used
// for driving the colors so it always looks careful and deliberate, perhaps for the lights we can also have color gradient
// patches as well as single colors"
//
// One active palette drives every colour: a bed (base), its neighbour for the strand (partner), the air (deep), a tinted
// white, and two LIFT colours (kick, highlight) that are what a colour kick turns cells into. This module:
//   - validates a palette (validatePalette): the stricter VJ red rule (encoded OR linear R / (R + G + B)) at 0.78 for
//     anything that moves and 0.80 for a held pin, the red sector, the strand pair, the kick's contrast, the re-strike
//     ladder's matched luminance, the decay midpoints, the amber guard, the moving heads' wheel plan checked with the kick's
//     own wheel rules, every gradient's 32 samples, the lasers. A palette that fails is REFUSED with its reasons and the page
//     keeps running on the others (a crash at load, ?theme=molten's, is not possible any more);
//   - builds the lookup tables (linear rgb, from each gradient's 32 samples);
//   - hands out the Stage's roles (stageTheme), the VJ page's theme (vjTheme), the kick block and the wheel plan
//     (planOf), and says whether two palettes are neighbours (a crossfade) or not (a dip through the air's deep colour).

export const PALETTES_API = "arsenal.palettes/v1";
export const RED_RULE = 0.8;            // the house rule (vj-themes.js isSaturatedRed): encoded OR linear R share
export const RED_CAP = 0.78;            // everything that pulses, chases, kicks or is a laser keeps both shares at or under
export const PIN_RED_CAP = 0.80;        // a held pin only has to pass the house rule itself
export const AMBER = Object.freeze([40, 105]);   // OKLCh hues that read amber, orange or yellow on a phone
export const EQUAL_LUMA = 0.35;         // kick.js governor.equal_luma: the wheel's clean-way tolerance
export const SAT_COLOUR = 0.3;          // kick.js: a wheel slot at or over this HSV saturation is a colour
export const REST_FORBIDDEN = Object.freeze([1, 2, 11, 12, 13]);
export const LIFT_FORBIDDEN = Object.freeze([0, 1, 2, 8, 11, 12, 13]);
export const NEIGHBOUR_DEG = 60;        // beds this close in hue crossfade; anything else dips through deep
export const CTO_SLOT = 12;             // the wheel's warm white: never a head's colour unless a palette declares it
export const STAGE_ROLES = Object.freeze(["A", "B", "W", "beamA", "beamB", "warm", "bumpA", "bumpB", "accent", "accent2", "accentLift", "pin"]);

// ---------------------------------------------------------------------------------------------- colour maths --
const HEX = /^#[0-9a-f]{6}$/i;
export const isHex = (h) => typeof h === "string" && HEX.test(h);
const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const dec = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
const enc = (c) => { c = clamp01(c); return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; };
export function hexRgb8(h) { const v = parseInt(h.slice(1), 16); return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; }
export function hexToLin(h) { return hexRgb8(h).map((c) => dec(c / 255)); }
export function linToHex(lin) { return "#" + lin.map((x) => Math.round(enc(x) * 255).toString(16).padStart(2, "0")).join(""); }
export const lumaOf = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
// OKLab (Ottosson's matrices: the same numbers as vj-core.js and the synthesizer's colour.py)
export function linToOklab(c) {
  const l = 0.4122214708 * c[0] + 0.5363325363 * c[1] + 0.0514459929 * c[2];
  const m = 0.2119034982 * c[0] + 0.6806995451 * c[1] + 0.1073969566 * c[2];
  const s = 0.0883024619 * c[0] + 0.2817188376 * c[1] + 0.6299787005 * c[2];
  const l_ = Math.cbrt(l), m_ = Math.cbrt(m), s_ = Math.cbrt(s);
  return [0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
          1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
          0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_];
}
export function oklabToLin(L, a, b) {
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b, m_ = L - 0.1055613458 * a - 0.0638541728 * b, s_ = L - 0.0894841775 * a - 1.2914855480 * b;
  const l = l_ ** 3, m = m_ ** 3, s = s_ ** 3;
  return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
          -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
}
export function lchOfLin(c) { const [L, a, b] = linToOklab(c); let h = (Math.atan2(b, a) * 180) / Math.PI; if (h < 0) h += 360; return { L, C: Math.hypot(a, b), h }; }
export const lchOf = (hex) => lchOfLin(hexToLin(hex));
export function deOK(x, y) { const a = linToOklab(typeof x === "string" ? hexToLin(x) : x), b = linToOklab(typeof y === "string" ? hexToLin(y) : y); return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]); }
export function hueGap(a, b) { const d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; }
// OKLCh to linear rgb, chroma taken out until the colour fits sRGB (lightness and hue kept)
export function fromLch(L, C, h) {
  const r = (h * Math.PI) / 180, ca = Math.cos(r), sa = Math.sin(r);
  const at = (c) => oklabToLin(L, c * ca, c * sa);
  const inG = (v) => v.every((x) => x >= -1e-6 && x <= 1 + 1e-6);
  let v = at(Math.max(0, C));
  if (inG(v)) return v.map(clamp01);
  let lo = 0, hi = Math.max(0, C);
  for (let i = 0; i < 24; i++) { const mid = (lo + hi) / 2; if (inG(at(mid))) lo = mid; else hi = mid; }
  return at(lo).map(clamp01);
}
// two linear colours mixed through OKLCh, the hue turning the short way round (a palette crossfade)
export function mixLch(a, b, t) {
  const A = lchOfLin(a), B = lchOfLin(b);
  let ha = A.h, hb = B.h;
  if (A.C < 0.02) ha = hb;
  if (B.C < 0.02) hb = ha;
  let dh = hb - ha; dh -= 360 * Math.round(dh / 360);
  return fromLch(A.L + (B.L - A.L) * t, A.C + (B.C - A.C) * t, ha + dh * t);
}
export const mixLin = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
// the red shares of a colour as displayed: encoded (8-bit) and linear R / (R + G + B)
export function redShares(colour) {
  const hex = typeof colour === "string" ? colour : linToHex(colour);
  const e = hexRgb8(hex), l = e.map((c) => dec(c / 255));
  const se = e[0] + e[1] + e[2], sl = l[0] + l[1] + l[2];
  return { encoded: se > 0 ? e[0] / se : 0, linear: sl > 0 ? l[0] / sl : 0 };
}
export const redMax = (c) => { const r = redShares(c); return Math.max(r.encoded, r.linear); };
// THE house red rule as the VJ library has it (the stricter one: encoded OR linear), for a hex or a linear colour
export const isSaturatedRed = (c) => redMax(c) >= RED_RULE;
export const inRedSector = ({ C, h }, cmax = 0.12) => (h >= 345 || h <= 30) && C > cmax;
// HSV saturation as the screen shows it (kick.js saturation)
export function satOf(lin) { const e = lin.map(enc), mx = Math.max(...e), mn = Math.min(...e); return mx > 1e-6 ? (mx - mn) / mx : 0; }
// HLS of an 8-bit colour (the KeyLab pad rule, vj-themes.js ledRule)
function hls(rgb) {
  const [r, g, b] = rgb.map((c) => c / 255), mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  if (mx === mn) return { h: 0, l, s: 0 };
  const d = mx - mn, s = l <= 0.5 ? d / (mx + mn) : d / (2 - mx - mn);
  const rc = (mx - r) / d, gc = (mx - g) / d, bc = (mx - b) / d;
  const h = r === mx ? bc - gc : g === mx ? 2 + rc - bc : 4 + gc - rc;
  return { h: ((((h / 6) % 1) + 1) % 1) * 360, l, s };
}
export function padOk(hex) {
  if (!isHex(hex)) return false;
  const rgb = hexRgb8(hex);
  if (rgb[0] === 255 && rgb[1] === 255 && rgb[2] === 255) return true;
  const { h, s } = hls(rgb);
  return s > 0.5 && !(h >= 15 && h <= 100);
}

// ------------------------------------------------------------------------------------------------- the wheel --
// the beam head's wheel rules, the kick's own (kick.js wayLumaClean, shortWayClear, nearestShortSlot's filters)
export function wayLumaClean(wheel, at, to, dir, tol = EQUAL_LUMA) {
  if (at === to) return true;
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
export function redSlotsOf(wheel) { const out = []; for (let i = 0; i < wheel.length; i++) if (isSaturatedRed(wheel[i])) out.push(i); return out; }
export function shortWayClear(wheel, at, to, tol = EQUAL_LUMA, red = redSlotsOf(wheel)) {
  if (red.includes(to)) return false;
  if (at === to) return true;
  const n = wheel.length, up = (((to - at) % n) + n) % n, down = n - up;
  const clear = (dir, steps) => { for (let k = 1; k < steps; k++) if (red.includes((((at + dir * k) % n) + n) % n)) return false; return wayLumaClean(wheel, at, to, dir, tol); };
  return (up <= down && clear(1, up)) || (down <= up && clear(-1, down));
}
// may a kick move a head's wheel from slot at to slot to? (the short red-free clean way, not white for a colour, never a
// much darker slot) -> [ok, why]
export function kickMoveOk(wheel, at, to, tol = EQUAL_LUMA) {
  if (!shortWayClear(wheel, at, to, tol)) return [false, "no clean short way"];
  if (satOf(wheel[to]) < SAT_COLOUR) return [false, "a white slot for a colour"];
  if (to !== at && lumaOf(wheel[to]) < lumaOf(wheel[at]) * (1 - tol) - 1e-9) return [false, "a much darker slot"];
  return [true, ""];
}
const nearLuma = (wheel, a, b, tol = EQUAL_LUMA) => { const la = lumaOf(wheel[a]), lb = lumaOf(wheel[b]); return Math.abs(la - lb) <= tol * Math.max(la, lb); };

// ----------------------------------------------------------------------------------------------- the palette --
const roleHex = (p, role) => { const c = (p.colours || []).find((x) => x.role === role); return c ? c.hex : null; };
const grad = (p, name) => (p.gradients || []).find((g) => g.name === name) || null;
export const isNeutral = (p) => p.family === "neutral";

// Every problem with one palette, as sentences ([] = it passes). wheel: the beam head's wheel as hex strings.
export function validatePalette(p, wheelHex) {
  const out = [];
  const bad = (m) => out.push(m);
  if (!p || typeof p !== "object") return ["not an object"];
  if (!/^[a-z0-9][a-z0-9-]{0,40}$/.test(p.id || "")) bad("id: lower-case letters, digits and dashes");
  if (!p.name) bad("name: missing");
  const hexes = {};
  for (const c of p.colours || []) { if (!isHex(c.hex)) bad(`colour ${c.role}: ${c.hex} is not a #rrggbb colour`); else hexes[c.role] = c.hex.toLowerCase(); }
  for (const r of ["deep", "base", "partner", "highlight", "kick", "white"]) if (!hexes[r]) bad(`colour ${r}: missing`);
  if (out.length) return out;
  const warm = !!p.warm_declared, neutral = isNeutral(p);
  const L = {}; for (const [r, h] of Object.entries(hexes)) L[r] = lchOf(h);
  // the red rule and the red sector on every role (a pin is held: 0.80, and never in the sector rule)
  for (const [r, h] of Object.entries(hexes)) {
    const cap = r === "pin" ? PIN_RED_CAP : RED_CAP;
    if (redMax(h) > cap + 1e-9) bad(`${r} ${h}: red share ${redMax(h).toFixed(3)} over ${cap}`);
    if (r !== "pin" && inRedSector(L[r])) bad(`${r} ${h}: in the red sector (C ${L[r].C.toFixed(3)}, h ${L[r].h.toFixed(0)})`);
  }
  // the strand: two stops 0.16-0.32 apart (three stops 0.10-0.32 each), a hue gap of 66 degrees at most on one fixture,
  // chroma matched (unless a neutral bed), and a linear midpoint that stays a colour
  const sg = grad(p, "strand");
  if (!sg || !Array.isArray(sg.stops) || sg.stops.length < 2) bad("gradient strand: missing");
  else {
    const st = sg.stops.map((s) => s.hex);
    for (let j = 0; j + 1 < st.length; j++) {
      const a = st[j], b = st[j + 1], la = lchOf(a), lb = lchOf(b), d = deOK(a, b), lo = st.length === 2 ? 0.16 : 0.10;
      if (!(d >= lo - 1e-3 && d <= 0.32 + 1e-3)) bad(`strand ${j}->${j + 1}: dEOK ${d.toFixed(3)} (want ${lo}-0.32)`);
      const lightPair = hueGap(la.h, lb.h) < 30 && Math.abs(la.L - lb.L) >= 0.18;
      if (!neutral && Math.abs(la.C - lb.C) > (lightPair ? 0.12 : 0.08) + 1e-3) bad(`strand ${j}->${j + 1}: chroma ${la.C.toFixed(3)} against ${lb.C.toFixed(3)}`);
      if (la.C >= 0.05 && lb.C >= 0.05 && hueGap(la.h, lb.h) > 66 + 0.5) bad(`strand ${j}->${j + 1}: hue gap ${hueGap(la.h, lb.h).toFixed(0)} over 66 on one fixture`);
      const m = lchOfLin(mixLin(hexToLin(a), hexToLin(b), 0.5)), floor = Math.min(la.C, lb.C) >= 0.07 ? 0.07 : 0.5 * Math.min(la.C, lb.C);
      if (m.C < floor - 2e-3) bad(`strand ${j}->${j + 1}: linear midpoint chroma ${m.C.toFixed(3)} (muddy)`);
    }
  }
  // the kick: light first (0.15 L over the bed), a colour (0.15 from white, chroma 0.08), apart from the bed and from the
  // highlight; the highlight a step up from the partner or a new colour, and 0.10 from white
  const b = L.base, pt = L.partner, k = L.kick, hi = L.highlight;
  if (k.L - b.L < 0.15 - 2e-3) bad(`kick L ${k.L.toFixed(3)}: only ${(k.L - b.L).toFixed(3)} over the bed (want 0.15)`);
  if (hi.L - pt.L < 0.04 - 2e-3 && deOK(hexes.highlight, hexes.partner) < 0.12) bad("highlight: neither brighter than the partner nor a new colour");
  if (deOK(hexes.kick, hexes.white) < 0.15 - 2e-3) bad(`kick ~ white (dEOK ${deOK(hexes.kick, hexes.white).toFixed(3)})`);
  if (deOK(hexes.highlight, hexes.white) < 0.10 - 2e-3) bad(`highlight ~ white (dEOK ${deOK(hexes.highlight, hexes.white).toFixed(3)})`);
  if (deOK(hexes.kick, hexes.highlight) < 0.10 - 2e-3) bad(`kick ~ highlight (dEOK ${deOK(hexes.kick, hexes.highlight).toFixed(3)})`);
  if (k.C < 0.08 - 2e-3) bad(`kick chroma ${k.C.toFixed(3)} under 0.08: it would read as white`);
  if (deOK(hexes.kick, hexes.base) < 0.20 - 2e-3) bad(`kick against the bed dEOK ${deOK(hexes.kick, hexes.base).toFixed(3)} under 0.20`);
  // the re-strike ladder: the two lift colours at matched luminance (a re-strike is a colour flip, never a flash)
  const ya = lumaOf(hexToLin(hexes.kick)), yb = lumaOf(hexToLin(hexes.highlight)), ratio = Math.min(ya, yb) / Math.max(ya, yb);
  if (ratio < 0.80 - 5e-3) bad(`kick and highlight luminance ratio ${ratio.toFixed(2)} under 0.80 (a re-strike would flash)`);
  // the decay: every lift crossfades back to its own cell colour in linear rgb without greying out
  const pairs = [["kick", "base"], ["highlight", "partner"]];
  if (hexes.mid) pairs.push(["highlight", "mid"]);
  if (hexes.accent && hexes.accent_lift && hexes.accent_lift !== hexes.white) pairs.push(["accent_lift", "accent"]);
  for (const [x, y] of pairs) {
    const m = lchOfLin(mixLin(hexToLin(hexes[x]), hexToLin(hexes[y]), 0.5)), cx = L[x].C, cy = L[y].C;
    if (Math.min(cx, cy) >= 0.06 && (m.C < 0.06 - 2e-3 || m.C < 0.45 * Math.min(cx, cy) - 2e-3)) bad(`decay ${x}->${y}: linear midpoint chroma ${m.C.toFixed(3)} (greys out)`);
  }
  // amber: never a lift colour unless the palette is declared warm
  for (const r of ["kick", "highlight"]) if (!warm && L[r].C >= 0.06 && L[r].h >= AMBER[0] && L[r].h <= AMBER[1]) bad(`${r} ${hexes[r]} reads amber (h ${L[r].h.toFixed(0)}) in a palette not declared warm`);
  // the moving heads' wheel plan
  const wheel = (wheelHex || []).map(hexToLin);
  const hd = p.heads || {};
  if (!wheel.length) bad("heads: no wheel to check the plan against");
  else if (!hd.rest || !hd.alt) bad("heads: rest and alt slots missing");
  else {
    const fam = ["base", "partner", "mid", "accent"].filter((x) => L[x] && L[x].C >= 0.05).map((x) => L[x]);
    const groups = { all: { rest: hd.rest.slot, lift: hd.lift || [] } };
    for (const [g, s] of Object.entries(hd.groups || {})) groups[g] = { rest: s.rest, lift: s.lift || [] };
    for (const [g, spec] of Object.entries(groups)) {
      const rest = spec.rest;
      if (!(rest >= 0 && rest < wheel.length)) { bad(`heads ${g}: rest slot ${rest} is not on the wheel`); continue; }
      if (REST_FORBIDDEN.includes(rest)) bad(`heads ${g}: rest slot ${rest} is not allowed`);
      if (rest !== 0 && !fam.some((f) => hueGap(lchOfLin(wheel[rest]).h, f.h) <= 45 + 0.5)) bad(`heads ${g}: rest slot ${rest} is not a palette hue`);
      for (const l of spec.lift) {
        const [ok, why] = kickMoveOk(wheel, l.frm, l.to);
        if (!ok) bad(`heads ${g}: lift ${l.frm}->${l.to}: ${why}`);
        if (Math.abs(l.frm - l.to) !== 1) bad(`heads ${g}: lift ${l.frm}->${l.to} is more than one slot`);
        if (LIFT_FORBIDDEN.includes(l.to) || (l.to === 3 && !warm)) bad(`heads ${g}: lift target ${l.to} is not allowed`);
        const sh = lchOfLin(wheel[l.to]).h;
        let agree = Math.min(hueGap(sh, k.h), hueGap(sh, hi.h));
        if (g !== "all" && L.accent) agree = Math.min(agree, hueGap(sh, L.accent.h));
        if (agree > 45 && hd.mixed === "punch") agree = Math.min(agree, hueGap(sh, pt.h), hueGap(sh, b.h));
        if (agree > 45 + 0.5) bad(`heads ${g}: lift ${l.frm}->${l.to} is ${agree.toFixed(0)} degrees from every palette colour`);
      }
    }
    // the Stage's head roles are the rest and alt slots' exact colours (the look path never snaps a colour)
    const st = p.stage_theme || {};
    if (st.beamA && wheelHex[hd.rest.slot] && st.beamA.toLowerCase() !== wheelHex[hd.rest.slot].toLowerCase()) bad(`stage_theme.beamA ${st.beamA} is not the rest slot's colour ${wheelHex[hd.rest.slot]}`);
    if (st.beamB && wheelHex[hd.alt.slot] && st.beamB.toLowerCase() !== wheelHex[hd.alt.slot].toLowerCase()) bad(`stage_theme.beamB ${st.beamB} is not the alt slot's colour ${wheelHex[hd.alt.slot]}`);
    if (hd.mixed !== "step" && hd.mixed !== "punch") bad("heads.mixed: step or punch");
  }
  // the gradients: stops a step apart, never a hue gap over 80, no muddy middle, no lightness dip, all 32 samples red-safe
  for (const g of p.gradients || []) {
    const held = false, cap = held ? PIN_RED_CAP : RED_CAP;
    const S = g.samples32 || [];
    if (S.length !== 32 || !S.every(isHex)) { bad(`gradient ${g.name}: 32 #rrggbb samples`); continue; }
    const sl = S.map(lchOf);
    const redS = S.find((h) => redMax(h) > cap + 1e-9);
    if (redS) bad(`gradient ${g.name}: sample ${redS} red share ${redMax(redS).toFixed(3)}`);
    const secS = S.find((h, i) => inRedSector(sl[i]));
    if (secS) bad(`gradient ${g.name}: sample ${secS} in the red sector`);
    const stops = (g.stops || []).map((s) => s.hex);
    const ls = stops.map(lchOf);
    for (let j = 0; j + 1 < stops.length; j++) {
      const d = deOK(stops[j], stops[j + 1]), hiD = g.name === "strand" ? 0.32 : 0.30;
      if (g.name !== "lasers" && g.name !== "kick" && !(d >= 0.08 - 2e-3 && d <= hiD + 2e-3)) bad(`gradient ${g.name}: stops ${j}->${j + 1} dEOK ${d.toFixed(3)}`);
      if (ls[j].C >= 0.05 && ls[j + 1].C >= 0.05 && hueGap(ls[j].h, ls[j + 1].h) > 80 + 0.5) bad(`gradient ${g.name}: stops ${j}->${j + 1} hue gap over 80`);
    }
    if (ls.length) {
      const weak = Math.min(...ls.map((x) => x.C)), mc = Math.min(...sl.map((x) => x.C));
      if (weak >= 0.07 ? mc < 0.07 - 3e-3 || mc < 0.5 * weak - 3e-3 : mc < 0.5 * weak - 3e-3) bad(`gradient ${g.name}: chroma dips to ${mc.toFixed(3)}`);
      if (Math.min(...sl.map((x) => x.L)) < Math.min(ls[0].L, ls[ls.length - 1].L) - 0.05) bad(`gradient ${g.name}: a lightness dip`);
    }
  }
  // the lasers: bright enough for a beam, red-safe, the fan pair within 80 degrees
  const lz = p.lasers || [];
  if (lz.length !== 3 || !lz.every(isHex)) bad("lasers: three #rrggbb colours");
  else {
    for (const [i, h] of lz.entries()) {
      const c = lchOf(h);
      if (redMax(h) > RED_CAP + 1e-9) bad(`laser ${i} ${h}: red share ${redMax(h).toFixed(3)}`);
      if (inRedSector(c)) bad(`laser ${i} ${h}: in the red sector`);
      if (c.L < 0.58 - 2e-3) bad(`laser ${i} ${h}: L ${c.L.toFixed(2)} under the beam floor 0.58`);
      if (!warm && c.C >= 0.06 && c.h >= AMBER[0] && c.h <= AMBER[1] && !hexes.accent) bad(`laser ${i} ${h}: an amber laser without a declared accent`);
    }
    const a = lchOf(lz[0]), c = lchOf(lz[1]);
    if (a.C >= 0.05 && c.C >= 0.05 && hueGap(a.h, c.h) > 80 + 0.5) bad("lasers: the fan pair is more than 80 degrees apart");
  }
  // the bed must not vanish on a phone
  if (!neutral && lumaOf(hexToLin(hexes.base)) < 0.08 - 1e-3) bad(`base luma ${lumaOf(hexToLin(hexes.base)).toFixed(3)} under 0.08 (dim on a phone)`);
  // the kick block: the ladder is the lift pair, every lift is a palette colour
  const kb = p.kick || {};
  if (!Array.isArray(kb.ladder) || kb.ladder.length !== 2 || kb.ladder[0].toLowerCase() !== hexes.kick || kb.ladder[1].toLowerCase() !== hexes.highlight) bad("kick.ladder: [kick, highlight]");
  const lifts = new Set([hexes.kick, hexes.highlight, hexes.accent_lift, hexes.white].filter(Boolean));
  for (const [r, h] of Object.entries(kb.lift_by_stage_role || {})) if (r !== "pin" && !(isHex(h) && lifts.has(h.toLowerCase()))) bad(`kick.lift_by_stage_role.${r}: ${h} is not one of the palette's lift colours`);
  // the KeyLab pads' stand-ins (vj-themes.js ledRule)
  for (const r of ["A", "B", "W"]) { const pd = p.pads && p.pads[r]; if (!pd || !padOk(pd.hex)) bad(`pads.${r}: ${pd && pd.hex} fails the pad rule`); }
  return out;
}

// ---------------------------------------------------------------------------------------------- the library --
// loadPalettes(raw, {wheel}) -> {list, byId, ids, families, refused: [{id, problems}], wheel}. A palette that fails is
// refused (left out, with its reasons); the rest load.
export function loadPalettes(raw, { wheel = null } = {}) {
  if (!raw || raw.format !== "arsenal.palettes/v1" || !Array.isArray(raw.palettes)) throw new Error("palettes: not an arsenal.palettes/v1 library");
  const W = wheel || (raw.wheel || []).map((s) => s.hex);
  const list = [], refused = [];
  for (const p of raw.palettes) {
    const problems = validatePalette(p, W);
    if (problems.length) refused.push({ id: p && p.id, problems });
    else list.push(p);
  }
  const byId = Object.fromEntries(list.map((p) => [p.id, p]));
  const families = {};
  for (const p of list) (families[p.family] = families[p.family] || []).push(p.id);
  return { list, byId, ids: list.map((p) => p.id), families, refused, wheel: W, motions: raw.motions || {} };
}
export async function fetchPalettes(url = new URL("./palettes.json", import.meta.url), fetchImpl = globalThis.fetch, opts = {}) {
  const res = await fetchImpl(url);
  if (!res.ok) throw new Error(`palettes: HTTP ${res.status}`);
  return loadPalettes(await res.json(), opts);
}
// the next (delta +1) or previous (-1) palette in the library's order
export function stepPalette(lib, id, delta = 1) {
  const i = lib.ids.indexOf(id), n = lib.ids.length;
  return lib.ids[(((i < 0 ? 0 : i + delta) % n) + n) % n];
}

// ----------------------------------------------------------------------------------------------- the tables --
// a gradient's 32 samples as linear rgb (Float32Array of 96)
export function tableOf(g) { const t = new Float32Array(96); (g.samples32 || []).forEach((h, i) => t.set(hexToLin(h), i * 3)); return t; }
// a table sampled at u in 0..1 (linear interpolation between neighbouring samples), into out
export function sampleTable(t, u, out = [0, 0, 0]) {
  const n = t.length / 3, x = clamp01(u) * (n - 1), i = Math.min(n - 2, Math.floor(x)), f = x - i;
  for (let k = 0; k < 3; k++) out[k] = t[i * 3 + k] + (t[(i + 1) * 3 + k] - t[i * 3 + k]) * f;
  return out;
}

// --------------------------------------------------------------------------------------------- what pages get --
// The Stage's theme: the eight roles the looks name (A, B, W, beamA, beamB, warm, bumpA, bumpB), the split and pin roles
// (accent, accent2, accentLift, pin), lasers, ambient and air tint -- with the palette itself attached (programmer.js and
// kick.js read its lift colours, its wheel plan and its gradients from it).
export function stageTheme(p) {
  const st = p.stage_theme;
  const accent = roleHex(p, "accent"), accentLift = roleHex(p, "accent_lift");
  const sg = grad(p, "strand"), ag = grad(p, "accent");
  const wingB = sg && sg.wings && Array.isArray(sg.wings.B) ? sg.wings.B : null;
  const accent2 = wingB ? wingB[1] : ag && ag.stops && ag.stops[0] ? ag.stops[0].hex : accent || st.A;
  return { ...st, id: p.id, name: p.name, accent: accent || st.A, accent2, accentLift: accentLift || roleHex(p, "highlight"),
           pin: roleHex(p, "pin") || st.W, palette: p };
}
// The moving heads' wheel plan, ready for the programmer and the kick:
//   rest, alt          the slots beamA and beamB name
//   lift               Map from-slot -> {to, restrike: "alternate" | "hold"}
//   groups             group name -> {rest, lift Map}: a split's heads (Lime Rows' truss, lip and towers)
//   mixed              "step" (heads step with the LEDs in an area with both) or "punch" (dimmer and shutter only)
//   slots              every slot a head of this palette may show (white, rest, alt, every lift's ends, the groups')
export function planOf(p) {
  const hd = p.heads || {};
  const mk = (lift) => new Map((lift || []).map((l) => [l.frm, { to: l.to, restrike: l.restrike || "hold" }]));
  const groups = {};
  for (const [g, s] of Object.entries(hd.groups || {})) groups[g] = { rest: s.rest, lift: mk(s.lift) };
  const slots = new Set([0, hd.rest.slot, hd.alt.slot]);
  for (const l of hd.lift || []) { slots.add(l.frm); slots.add(l.to); }
  for (const g of Object.values(groups)) { slots.add(g.rest); for (const [f, l] of g.lift) { slots.add(f); slots.add(l.to); } }
  return { rest: hd.rest.slot, alt: hd.alt.slot, lift: mk(hd.lift), groups, mixed: hd.mixed || "punch", slots: [...slots].sort((a, b) => a - b),
           whiteKicksOnly: !(hd.lift && hd.lift.length) };
}
// are two palettes neighbours (a crossfade over 4 bars) or not (a cut on the downbeat through a 1-beat dip to deep)?
// Beds within 60 degrees of hue, and the heads' rest slots the same or one clean step apart on the wheel.
export function neighbours(a, b, wheelHex) {
  if (!a || !b) return false;
  if (a.id === b.id) return true;
  const ba = lchOf(roleHex(a, "base")), bb = lchOf(roleHex(b, "base"));
  const bedsClose = ba.C < 0.05 || bb.C < 0.05 ? deOK(roleHex(a, "base"), roleHex(b, "base")) < 0.12 : hueGap(ba.h, bb.h) <= NEIGHBOUR_DEG;
  if (!bedsClose) return false;
  const ra = a.heads.rest.slot, rb = b.heads.rest.slot, wheel = (wheelHex || []).map(hexToLin);
  const slotsOk = (x, y) => x === y || (Math.abs(x - y) === 1 && wheel.length && shortWayClear(wheel, x, y) && nearLuma(wheel, x, y));
  return slotsOk(ra, rb) && slotsOk(a.heads.alt.slot, b.heads.alt.slot);
}
// the beat position of the next N-bar line after pos (a palette change lands there; 16 bars by default)
export function landingPos(pos, barAnchor = 0, bars = 16) {
  const span = 4 * bars, k = Math.floor((pos - barAnchor) / span + 1e-6) + 1;
  return barAnchor + span * k;
}
// does a change from palette a to palette b dip through deep (true) or crossfade (false)? A split on either side always
// dips (its halves never crossfade into a bed); otherwise neighbours crossfade
export function needsDip(a, b, wheelHex) { return !(a && b && !a.split && !b.split && neighbours(a, b, wheelHex)); }
// The VJ page's theme (vj-themes.json's shape) for a palette: A, B, W, ground, line, beam, led from the palette, and the
// fields the VJ library asks of every theme filled in the same grammar (lasers on the beam pair, the strobes and bursts on
// the lift colours and white, the effects on the partner and white). family: the palette's family tab.
export function vjTheme(p) {
  const v = p.vj_theme;
  const t = { id: p.id, name: p.name, family: `pal-${p.family}`, A: v.A, B: v.B, W: v.W, ground: v.ground, line: v.line,
              beam: { ...v.beam }, led: { A: p.pads.A.hex, B: p.pads.B.hex, W: p.pads.W.hex },
              sections: ["intro", "build", "drop", "break", "outro"], scene: "A", lasers: ["A", "B"],
              fx: { shockwave: "B", particles: "A", flash: "W" }, strobe: { triple: ["W", "W", "W"], flicker: ["A", "W"] }, burst: ["A", "B", "W"],
              hero: "the palette's strand pair", held: [], split_only: !!v.split_only, one_family: !!v.one_family,
              crossfade_needs_dip: !!v.crossfade_needs_dip, fader: false, from: `arsenal/web/palettes.json (${p.id})`,
              palette: { kick: roleHex(p, "kick"), highlight: roleHex(p, "highlight"), accent_lift: roleHex(p, "accent_lift") } };
  return t;
}
