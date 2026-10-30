// arsenal/web/stage/setups.js -- SETUPS: a palette x a PLACEMENT (which colour goes on which part of the rig), the colour
// layer the Stage rotates on its 16-bar phrase lines. Pure ES module (no DOM, no WebGL). Data: sets/setups.json (format
// arsenal.stage-setups/v1). Tests: tests/stage_setups.test.mjs. The programmer (programmer.js, "THE SETUP LAYER") runs it.
//
// Daniel, 2026-10-29, with a screenshot of the drop (TUNNEL_UP): "also amber is perhaps a touch overrepresented, maybe we
// can change it to gold or orange, or gold and blue, we have a lot of stuff that just stays white, in the screenshot the
// middle row being white with the other lights being blue and lasers flashing green or purple or pink, can you think of a
// few cool color palates using the screenshot as a reference for placement and ideas, we could also leverage gradients on
// the led cubes" ... then: "not permantly only orange and gold, i want the lights to cycle different color palates and
// setups".
//
// A SETUP names its own colours (hex, drawn from the palettes, or "@Role": the active palette's stage role live, so a
// setup can be the palette's own colours placed differently) and places them:
//   place.<group>      for each of the bank's 13 light groups (programmer.js BANK_GROUPS): the group's colour a (the look's
//                      bed roles: A, beamA, accent, warm, pin), b (its partner roles: B, beamB, accent2; b defaults to a, so
//                      a two-role cell -- the strand's helix, the slats' two-colour cells -- is an a->b GRADIENT), w (the
//                      look's whites, W -- named, the group keeps them that colour; left out, they take the group's b, since
//                      Daniel found "a lot of stuff that just stays white"); "left" / "right" give the members on that side
//                      (the group's side key: -1 left, +1 right) their own a / b; pin: true holds the group (the centre row
//                      white); join: n puts a group whose colours are off the cycle (a white) into the bank at offset n
//   cycle              the colours kick 5's bank turns WITHIN the setup: a colour on the cycle moves one place a press
//   lasers, laser_bank the laser colours (by index, as the palettes' three) and the pool the bank turns them through;
//                      "@lasers": the palette's own (and the palette bank's turn)
//   cubes              the HAL cubes' glow (top and bottom rung) and, optionally, their core's hue (cubes.js THE HOOK);
//                      left out, the glow follows the strand.cubes group's a -> b
//   warm               true for the setups that are ABOUT gold, amber or orange (Daniel: "amber is perhaps a touch
//                      overrepresented"): no other setup may hold an amber colour
//
// THE BANK WITHIN A SETUP (kick 5): bank k shows each colour on the cycle k places on; a group off the cycle that joins
// takes the cycle's colour (k - 1 + its offset) from the first press; a pinned group holds; the look's whites (W) in a
// group that does not name its own w show the group's b (so they turn with it), so every non-pinned group changes colour
// on every press and a white-pinned group stays white. The validator proves it for every setup (bankProblems).
//
// THE CROSSFADE: a setup lands on its line and crossfades every group's colours from what is showing, each colour on the
// first clean path of: a straight line in OKLab, the OKLCh short way round, the OKLCh long way round (clean: no sample
// over the red rule or in the red sector, and none washed out -- under half the ends' chroma); a pair with no clean path
// cuts at the half way (pathOf; the tests check every pair of every two setups has one).
import { STAGE_ROLES, hexToLin, linToHex, lchOfLin, linToOklab, oklabToLin, deOK, hueGap, redMax, inRedSector, mixLch, fromLch, mixLin, isHex,
         RED_CAP, AMBER } from "../palettes.js";

export const SETUPS_API = "arsenal.stage-setups/v1";
// the light groups a setup places (programmer.js BANK_GROUPS, the same list in the same order: a test pins it)
export const SETUP_GROUPS = Object.freeze(["rings.slats", "rings.rims", "truss.heads", "lip.heads", "vert", "vert.strips", "delay.30", "delay.55",
                                           "halo", "strand.heads", "strand.cubes", "strand.dots", "strand.bars"]);
export const PARTS = Object.freeze(["all", "left", "right"]);     // a group member's part: its side key 0, -1, +1
export const partOfSide = (side) => (side < 0 ? 1 : side > 0 ? 2 : 0);
// which of a placement's colours each stage role shows
export const ROLE_SLOT = Object.freeze({ A: "a", B: "b", W: "w", beamA: "a", beamB: "b", warm: "a", bumpA: "a", bumpB: "b",
                                         accent: "a", accent2: "b", accentLift: "b", pin: "a" });
const ROLE_SLOT_IDX = STAGE_ROLES.map((r) => ROLE_SLOT[r] || "a");
const lumaLin = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
export const NR = STAGE_ROLES.length;
// the numbers (tests/stage_setups.test.mjs pins them)
export const SETUP_LIMITS = Object.freeze({
  bank_de: 0.08,        // every non-pinned group's colours move at least this far (dEOK) on every press
  bank_mid_de: 0.04,    // ... and its a->b gradient's middle (a helix only mirrored reads as no change)
  cycle_de: 0.1,        // two colours of a cycle (or a laser bank) at least this far apart
  cycle_chroma: 0.06,   // a cycle colour is a colour (a white is never on a cycle: it would wash a group out)
  laser_floor: 0.58,    // a laser colour's OKLCh lightness (the palettes' beam floor)
  path_samples: 17,
  // THE LEVEL (measured, stage_verify --phases setups, 2026-10-29). A light's colour is also its brightness: a setup's
  // white centre row, gold beams or all-white rig sat at relative luminance 0.6-0.9 where the palettes' beds sit at
  // 0.1-0.35, so the show's own moves swung the frame twice as far, and kick 5's steps between a gold and a sapphire (0.6
  // and 0.1) swung whole groups; with the same input the flash limiter acted on 35-49 frames of 480 where every palette's
  // own looks made it act on 0-12 (with the beams mastered off: 0 under every setup). So a setup's colours are LEVELLED, as
  // a console's dimmer would, hue and chroma ratio kept: every colour a group turns through (kick 5's bank) is taken down
  // to the setup's level -- the dimmest colour on its cycle -- so a bank step changes hue, never brightness (the palettes'
  // re-strike ladder rule); a pinned group (the white centre row) is taken down to luma_cap; the beams the same, by the
  // luminance of the wheel slot they show (programmer.js). The looks' levels, the kicks (the white kick is the setup's
  // white at full) and the lasers are not touched.
  luma_cap: 0.35,
});

// ------------------------------------------------------------------------------------------------- crossfades --
export const PATH = Object.freeze({ LAB: 0, LCH_SHORT: 1, LCH_LONG: 2, CUT: 3 });
export const PATH_NAMES = Object.freeze(["oklab", "oklch-short", "oklch-long", "cut"]);
const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
function mixLab(a, b, t, out) {
  const A = linToOklab(a), B = linToOklab(b);
  const c = oklabToLin(A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t);
  out[0] = clamp01(c[0]); out[1] = clamp01(c[1]); out[2] = clamp01(c[2]);
  return out;
}
function mixLchLong(a, b, t) {
  const A = lchOfLin(a), B = lchOfLin(b);
  let ha = A.h, hb = B.h;
  if (A.C < 0.02) ha = hb;
  if (B.C < 0.02) hb = ha;
  let dh = hb - ha; dh -= 360 * Math.round(dh / 360);
  if (Math.abs(dh) > 1e-6) dh = dh > 0 ? dh - 360 : dh + 360;
  return fromLch(A.L + (B.L - A.L) * t, A.C + (B.C - A.C) * t, ha + dh * t);
}
// a colour on the path from a to b at t (linear rgb in, linear rgb out)
export function mixPath(a, b, t, type, out = [0, 0, 0]) {
  if (t <= 0) { out[0] = a[0]; out[1] = a[1]; out[2] = a[2]; return out; }
  if (t >= 1) { out[0] = b[0]; out[1] = b[1]; out[2] = b[2]; return out; }
  if (type === PATH.LAB) return mixLab(a, b, t, out);
  if (type === PATH.CUT) { const s = t < 0.5 ? a : b; out[0] = s[0]; out[1] = s[1]; out[2] = s[2]; return out; }
  const c = type === PATH.LCH_LONG ? mixLchLong(a, b, t) : mixLch(a, b, t);
  out[0] = c[0]; out[1] = c[1]; out[2] = c[2];
  return out;
}
// is the path clean? Every sample under the red rule's moving cap and out of the red sector, and none washed out: when both
// ends are colours, every sample keeps at least half the weaker end's chroma (capped at 0.06)
export function pathClean(a, b, type, n = SETUP_LIMITS.path_samples) {
  const la = lchOfLin(a), lb = lchOfLin(b), lo = Math.min(la.C, lb.C), floor = lo >= 0.04 ? Math.min(0.06, 0.5 * lo) : 0;
  const s = [0, 0, 0];
  for (let i = 1; i < n - 1; i++) {
    mixPath(a, b, i / (n - 1), type, s);
    const c = lchOfLin(s);
    if (redMax(s) > RED_CAP + 1e-9 || inRedSector(c)) return false;
    if (c.C < floor - 1e-4) return false;
  }
  return true;
}
// the first clean path from a to b (an unchanged colour: OKLab, trivially clean)
export function pathOf(a, b) {
  if (Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]) < 1e-6) return PATH.LAB;
  for (const t of [PATH.LAB, PATH.LCH_SHORT, PATH.LCH_LONG]) if (pathClean(a, b, t)) return t;
  return PATH.CUT;
}

// ------------------------------------------------------------------------------------------------- the library --
const ROLE_REF = /^@(A|B|W|beamA|beamB|warm|bumpA|bumpB|accent|accent2|accentLift|pin)$/;
const isName = (x) => typeof x === "string" && /^[a-z][a-z0-9-]{0,30}$/.test(x);
// a placement part's names ({a, b, w}), the part's own over the group's
function partOf(pl, part) {
  const side = part === 1 ? pl.left : part === 2 ? pl.right : null;
  const a = (side && side.a) || pl.a;
  return { a, b: (side && (side.b || side.a)) || pl.b || a, w: (side && side.w) || pl.w || "white" };
}
// compile one setup (already valid): its colour table, its placement per group and part, and whether each group is pinned
export function compileSetup(raw) {
  const S = { id: raw.id, name: raw.name, warm: !!raw.warm, about: raw.about || "", drawn_from: (raw.drawn_from || []).slice(),
              names: Object.keys(raw.colours), hex: {}, ref: {}, cycle: raw.cycle.slice(), place: {}, lasers: null, laserBank: null,
              cubes: { glow: null, core: null, glowMix: null }, lumaCap: Number.isFinite(raw.luma_cap) ? raw.luma_cap : null, level: null };
  for (const [n, v] of Object.entries(raw.colours)) {
    if (isHex(v)) { S.hex[n] = hexToLin(v.toLowerCase()); S.ref[n] = -1; }
    else { S.hex[n] = null; S.ref[n] = STAGE_ROLES.indexOf(v.slice(1)); }
  }
  const onCycle = (x) => S.cycle.includes(x);
  for (const g of SETUP_GROUPS) {
    const pl = raw.place[g];
    const parts = [0, 1, 2].map((k) => partOf(pl, k));
    const anyOn = parts.some((p) => onCycle(p.a) || onCycle(p.b));
    // a group off the cycle that does not say it joins holds (Daniel's centre row stays white)
    const pin = pl.pin === true || (!Number.isInteger(pl.join) && !anyOn);
    // the look's whites (W) keep the setup's white only in a pinned group or where the placement names w; elsewhere they
    // take the group's b (Daniel: "we have a lot of stuff that just stays white")
    const keepW = pin || pl.w !== undefined || !!(pl.left && pl.left.w) || !!(pl.right && pl.right.w);
    S.place[g] = { pin, join: Number.isInteger(pl.join) ? pl.join : 0, parts, sided: !!(pl.left || pl.right), keepW };
  }
  // the level the turning colours share: the dimmest on the cycle, under the cap (an "@Role" cycle: the cap)
  const cap = S.lumaCap ?? SETUP_LIMITS.luma_cap, ys = S.cycle.map((n) => S.hex[n]).filter(Boolean).map(lumaLin);
  S.level = ys.length === S.cycle.length && ys.length ? Math.min(cap, ...ys) : cap;
  if (raw.lasers === "@lasers") S.lasers = "@lasers";
  else { S.lasers = raw.lasers.slice(); S.laserBank = (raw.laser_bank || raw.lasers).slice(); }
  const cb = raw.cubes || {};
  S.cubes = { glow: Array.isArray(cb.glow) ? cb.glow.slice(0, 2) : null, core: Array.isArray(cb.core) ? cb.core.slice(0, 2) : null,
              glowMix: Number.isFinite(cb.glow_mix) ? cb.glow_mix : null };
  return S;
}
// a setup's colour by name, linear rgb (an "@Role" from the palette's live roles, roleRGB in STAGE_ROLES order)
export function colourOf(S, name, roles = null) {
  const h = S.hex[name];
  if (h) return h;
  const r = S.ref[name];
  return r >= 0 && roles && roles[r] ? roles[r] : [1, 1, 1];
}
// the cycle as it stands with these palette roles: an "@Role" colour that is a grey here, or the same colour as one before it,
// drops out (a static setup's cycle is its own)
export function cycleOf(S, roles = null) {
  if (S.names.every((n) => S.hex[n])) return S.cycle;
  const out = [];
  for (const n of S.cycle) {
    const c = colourOf(S, n, roles);
    if (lchOfLin(c).C < SETUP_LIMITS.cycle_chroma) continue;
    if (out.some((m) => deOK(colourOf(S, m, roles), c) < SETUP_LIMITS.cycle_de)) continue;
    out.push(n);
  }
  return out;
}
// the NAME a placement's colour shows at bank k (which: "a" | "b" | "w")
export function nameAt(S, g, part, which, k, cycle = S.cycle) {
  const pl = S.place[g], p = pl.parts[part], x = p[which];
  if (which === "w" || pl.pin || !(k > 0) || cycle.length < 2) return x;
  const m = cycle.length, i = cycle.indexOf(x);
  if (i >= 0) return cycle[(i + k) % m];
  // off the cycle (a white): the group joins at its offset; a two-colour part keeps two colours
  const o = pl.join + (which === "b" && p.b !== p.a ? 1 : 0);
  return cycle[(((k - 1 + o) % m) + m) % m];
}
// do the look's whites in this group take its b? Always, unless the group is pinned or its placement names its own w
// (the colour stage turns the look's W into B for it before the kicks: a white kick, painted after, stays the white)
export const whitesTurn = (S, g, k = 0) => !!(S && S.place[g] && !S.place[g].keepW);
// the role table of group g's part at bank k: 12 linear colours in STAGE_ROLES order, into out (a Float32Array at off)
// a placed colour at the setup's level (THE LEVEL above): scaled down to the cap when it is brighter
export function levelled(c, cap = SETUP_LIMITS.luma_cap) {
  const y = lumaLin(c);
  return y > cap ? [c[0] * cap / y, c[1] * cap / y, c[2] * cap / y] : c;
}
// the luminance group g's colours (and beams) are levelled to: a pinned group the cap, a turning one the setup's level
export const levelOf = (S, g) => (S.place[g] && S.place[g].pin ? S.lumaCap ?? SETUP_LIMITS.luma_cap : S.level ?? SETUP_LIMITS.luma_cap);
export function tableInto(S, g, part, k, roles, out, off = 0, cycle = null) {
  const cy = cycle || cycleOf(S, roles), cap = levelOf(S, g);
  const ca = levelled(colourOf(S, nameAt(S, g, part, "a", k, cy), roles), cap), cb = levelled(colourOf(S, nameAt(S, g, part, "b", k, cy), roles), cap);
  // (the look's whites W: the setup's white at full -- it is also what the white kick paints)
  const cw = colourOf(S, nameAt(S, g, part, "w", k, cy), roles);
  for (let r = 0; r < NR; r++) {
    const c = ROLE_SLOT_IDX[r] === "a" ? ca : ROLE_SLOT_IDX[r] === "b" ? cb : cw, o = off + r * 3;
    out[o] = c[0]; out[o + 1] = c[1]; out[o + 2] = c[2];
  }
  return out;
}
// the laser colours at bank k (linear), and the fan's gradient between the first two (a clean path, 32 samples); null for
// "@lasers" (the palette's own lasers and their bank)
export function lasersAt(S, k, roles = null) {
  if (!S || S.lasers === "@lasers" || !S.lasers) return null;
  const pool = S.laserBank, m = pool.length;
  const names = S.lasers.map((n, i) => (k > 0 && m >= 2 ? pool[((pool.indexOf(n) < 0 ? i : pool.indexOf(n)) + k) % m] : n));
  const colours = names.map((n) => colourOf(S, n, roles).slice());
  let fanRamp = null;
  if (colours.length >= 2) {
    fanRamp = new Float32Array(96);
    const t = pathOf(colours[0], colours[1]), s = [0, 0, 0];
    for (let i = 0; i < 32; i++) fanRamp.set(mixPath(colours[0], colours[1], i / 31, t === PATH.CUT ? PATH.LCH_LONG : t, s), i * 3);
  }
  return { names, colours, fanRamp };
}
// the HAL cubes' tint at bank k (cubes.js THE HOOK, linear): the glow named (each end turned with the bank as the cubes'
// group turns its colours), else the strand.cubes group's own a -> b; the core's hue only where the setup names it
export function cubesAt(S, k, roles = null) {
  const cy = cycleOf(S, roles), g = "strand.cubes", pl = S.place[g];
  const turn = (x) => { if (pl.pin || !(k > 0) || cy.length < 2) return x; const i = cy.indexOf(x); return i >= 0 ? cy[(i + k) % cy.length] : x; };
  const glow = S.cubes.glow ? S.cubes.glow.map(turn) : [nameAt(S, g, 0, "a", k, cy), nameAt(S, g, 0, "b", k, cy)];
  const core = S.cubes.core ? S.cubes.core.map(turn) : null;
  return { glowTop: colourOf(S, glow[0], roles).slice(), glowBottom: colourOf(S, glow[1], roles).slice(),
           coreTop: core ? colourOf(S, core[0], roles).slice() : null, coreBottom: core ? colourOf(S, core[1], roles).slice() : null,
           glowMix: S.cubes.glowMix, names: { glow, core } };
}

// ------------------------------------------------------------------------------------------------- validation --
// Every problem with one setup, as sentences ([] = it passes). roles: a palette's live roles to resolve "@Role" colours
// (without them only the static colours are checked).
export function validateSetup(raw, { roles = null } = {}) {
  const out = [], bad = (m) => out.push(m);
  if (!raw || typeof raw !== "object") return ["not an object"];
  if (!/^[a-z0-9][a-z0-9-]{0,40}$/.test(raw.id || "")) bad("id: lower-case letters, digits and dashes");
  if (!raw.name) bad("name: missing");
  const cols = raw.colours;
  if (!cols || typeof cols !== "object") return [...out, "colours: missing"];
  for (const [n, v] of Object.entries(cols)) {
    if (!isName(n)) bad(`colour name ${n}: lower-case letters, digits and dashes`);
    if (!isHex(v) && !ROLE_REF.test(v || "")) bad(`colour ${n}: ${v} is neither #rrggbb nor @Role`);
  }
  if (!cols.white) bad("colours.white: missing (the look's whites)");
  const known = (x) => typeof x === "string" && Object.prototype.hasOwnProperty.call(cols, x);
  // the red rule and the amber guard on every colour as it resolves
  const lin = (n) => (isHex(cols[n]) ? hexToLin(cols[n].toLowerCase()) : roles && ROLE_REF.test(cols[n]) ? roles[STAGE_ROLES.indexOf(cols[n].slice(1))] : null);
  for (const n of Object.keys(cols)) {
    const c = lin(n);
    if (!c) continue;
    const L = lchOfLin(c);
    if (redMax(c) > RED_CAP + 1e-9) bad(`colour ${n} ${linToHex(c)}: red share ${redMax(c).toFixed(3)} over ${RED_CAP}`);
    if (inRedSector(L)) bad(`colour ${n} ${linToHex(c)}: in the red sector (C ${L.C.toFixed(3)}, h ${L.h.toFixed(0)})`);
    if (!raw.warm && isHex(cols[n]) && L.C >= 0.06 && L.h >= AMBER[0] && L.h <= AMBER[1]) bad(`colour ${n} ${cols[n]} reads amber (h ${L.h.toFixed(0)}) in a setup not about it (warm: true)`);
  }
  // the cycle: colours, apart
  if (!Array.isArray(raw.cycle) || raw.cycle.length < 2) bad("cycle: two or more colour names");
  else {
    for (const n of raw.cycle) if (!known(n)) bad(`cycle: ${n} is not one of the setup's colours`);
    if (new Set(raw.cycle).size !== raw.cycle.length) bad("cycle: a colour twice");
    const cs = raw.cycle.filter(known).map(lin).filter(Boolean);
    if (cs.length === raw.cycle.length) {
      for (const [i, c] of cs.entries()) if (lchOfLin(c).C < SETUP_LIMITS.cycle_chroma - 1e-4) bad(`cycle: ${raw.cycle[i]} is a white or a grey (chroma ${lchOfLin(c).C.toFixed(3)})`);
      for (let i = 0; i < cs.length; i++) for (let j = i + 1; j < cs.length; j++) if (deOK(cs[i], cs[j]) < SETUP_LIMITS.cycle_de - 1e-4) bad(`cycle: ${raw.cycle[i]} and ${raw.cycle[j]} only dEOK ${deOK(cs[i], cs[j]).toFixed(3)} apart`);
    }
  }
  // the placement: every group, known names, pin or join
  const place = raw.place || {};
  for (const g of Object.keys(place)) if (!SETUP_GROUPS.includes(g)) bad(`place.${g}: not one of the bank's groups`);
  for (const g of SETUP_GROUPS) {
    const pl = place[g];
    if (!pl || typeof pl !== "object") { bad(`place.${g}: missing (a setup places every group)`); continue; }
    if (!known(pl.a)) bad(`place.${g}.a: ${pl.a} is not one of the setup's colours`);
    for (const k of ["b", "w"]) if (pl[k] !== undefined && !known(pl[k])) bad(`place.${g}.${k}: ${pl[k]} is not one of the setup's colours`);
    for (const s of ["left", "right"]) if (pl[s] !== undefined) {
      if (!pl[s] || typeof pl[s] !== "object" || !known(pl[s].a)) bad(`place.${g}.${s}.a: a colour name`);
      else for (const k of ["b", "w"]) if (pl[s][k] !== undefined && !known(pl[s][k])) bad(`place.${g}.${s}.${k}: ${pl[s][k]} is not one of the setup's colours`);
    }
    if (pl.pin !== undefined && typeof pl.pin !== "boolean") bad(`place.${g}.pin: true or false`);
    if (pl.join !== undefined && !(Number.isInteger(pl.join) && pl.join >= 0)) bad(`place.${g}.join: an offset 0, 1, 2 ...`);
    if (pl.pin === true && pl.join !== undefined) bad(`place.${g}: pinned and joining`);
  }
  // the lasers
  if (raw.lasers !== "@lasers") {
    if (!Array.isArray(raw.lasers) || raw.lasers.length < 1 || raw.lasers.length > 3) bad("lasers: one to three colour names, or \"@lasers\"");
    else {
      const bank = raw.laser_bank || raw.lasers;
      if (!Array.isArray(bank) || bank.length < 2) bad("laser_bank: two or more colour names (kick 5 turns the lasers through it)");
      else {
        for (const n of raw.lasers) if (!bank.includes(n)) bad(`laser_bank: holds no ${n} (every laser colour is on it)`);
        for (const n of new Set([...raw.lasers, ...bank])) {
          if (!known(n)) { bad(`lasers: ${n} is not one of the setup's colours`); continue; }
          const c = lin(n);
          if (c && lchOfLin(c).L < SETUP_LIMITS.laser_floor - 2e-3) bad(`laser ${n}: L ${lchOfLin(c).L.toFixed(2)} under the beam floor ${SETUP_LIMITS.laser_floor}`);
        }
        const bs = bank.filter(known).map(lin);
        if (bs.every(Boolean)) for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) if (deOK(bs[i], bs[j]) < SETUP_LIMITS.cycle_de - 1e-4) bad(`laser_bank: ${bank[i]} and ${bank[j]} only dEOK ${deOK(bs[i], bs[j]).toFixed(3)} apart`);
      }
    }
  }
  const cb = raw.cubes;
  if (cb !== undefined) {
    if (!cb || typeof cb !== "object") bad("cubes: an object");
    else {
      for (const k of ["glow", "core"]) if (cb[k] !== undefined && cb[k] !== null && !(Array.isArray(cb[k]) && cb[k].length === 2 && cb[k].every(known))) bad(`cubes.${k}: two colour names (the top rung's, the bottom rung's)`);
      if (cb.glow_mix !== undefined && !(Number.isFinite(cb.glow_mix) && cb.glow_mix >= 0 && cb.glow_mix <= 1)) bad("cubes.glow_mix: 0..1");
    }
  }
  if (out.length) return out;
  // what the setup shows: no gradient that greys out at any bank, and the bank changes every non-pinned group every press
  if (raw.colours && Object.values(cols).every((v) => isHex(v) || roles)) out.push(...bankProblems(compileSetup(raw), roles));
  return out;
}
// the bank within the setup, k = 0 .. 2 x the cycle's length: every non-pinned group's a, b, its gradient's middle and its
// whites move on every press, a pinned one never; no a->b gradient's linear middle greys out (the palettes' strand rule)
export function bankProblems(S, roles = null) {
  const out = [], cy = cycleOf(S, roles), M = 2 * Math.max(2, cy.length);
  if (cy.length < 2) return [`cycle: under two colours with this palette (${cy.join(", ")})`];
  const t0 = new Float32Array(NR * 3), t1 = new Float32Array(NR * 3);
  const at = (t, r) => [t[r * 3], t[r * 3 + 1], t[r * 3 + 2]];
  const RA = STAGE_ROLES.indexOf("A"), RB = STAGE_ROLES.indexOf("B"), RW = STAGE_ROLES.indexOf("W");
  const muddy = new Set();
  for (const g of SETUP_GROUPS) for (let part = 0; part < 3; part++) {
    if (part && !S.place[g].sided) continue;
    for (let k = 0; k <= M; k++) {
      tableInto(S, g, part, k, roles, t0, 0, cy);
      tableInto(S, g, part, k + 1, roles, t1, 0, cy);
      const a0 = at(t0, RA), b0 = at(t0, RB), a1 = at(t1, RA), b1 = at(t1, RB);
      // the look's whites as the colour stage shows them (W to b from the first press in a group that turns)
      const w0 = whitesTurn(S, g, k) ? b0 : at(t0, RW), w1 = whitesTurn(S, g, k + 1) ? b1 : at(t1, RW);
      const m0 = mixLin(a0, b0, 0.5), m1 = mixLin(a1, b1, 0.5);
      const la = lchOfLin(a0), lb = lchOfLin(b0), mc = lchOfLin(m0).C, lo = Math.min(la.C, lb.C);
      if (deOK(a0, b0) > 0.05 && lo >= 0.06 && mc < (lo >= 0.07 ? 0.07 : 0.5 * lo) - 2e-3) muddy.add(`${g}${part ? "." + PARTS[part] : ""} ${linToHex(a0)}->${linToHex(b0)} (middle chroma ${mc.toFixed(3)})`);
      const tag = `${g}${part ? "." + PARTS[part] : ""} bank ${k}->${k + 1}`;
      if (S.place[g].pin) {
        if (deOK(a0, a1) > 1e-6 || deOK(b0, b1) > 1e-6) out.push(`${tag}: a pinned group changed`);
        continue;
      }
      const d = { a: deOK(a0, a1), b: deOK(b0, b1), mid: deOK(m0, m1), w: deOK(w0, w1) };
      if (d.a < SETUP_LIMITS.bank_de - 1e-4 || d.b < SETUP_LIMITS.bank_de - 1e-4 || d.w < SETUP_LIMITS.bank_de - 1e-4 || d.mid < SETUP_LIMITS.bank_mid_de - 1e-4)
        out.push(`${tag}: does not change (a ${d.a.toFixed(3)}, b ${d.b.toFixed(3)}, middle ${d.mid.toFixed(3)}, whites ${d.w.toFixed(3)})`);
    }
  }
  for (const m of muddy) out.push(`gradient greys out: ${m}`);
  return out;
}
// the library: loadSetups(raw) -> {list, byId, ids, order, refused: [{id, problems}], cfg}. A setup that fails is refused with
// its reasons and the rest load. roles: a palette's roles to check "@Role" setups against (else they are checked live).
export function loadSetups(raw, { roles = null } = {}) {
  if (!raw || raw.format !== SETUPS_API || !Array.isArray(raw.setups)) throw new Error("setups: not an arsenal.stage-setups/v1 library");
  const list = [], refused = [];
  for (const s of raw.setups) {
    const problems = validateSetup(s, { roles });
    if (problems.length) refused.push({ id: s && s.id, problems });
    else list.push(compileSetup(s));
  }
  const byId = Object.fromEntries(list.map((s) => [s.id, s]));
  const order = (Array.isArray(raw.order) ? raw.order : list.map((s) => s.id)).filter((id) => byId[id]);
  for (const s of list) if (!order.includes(s.id)) order.push(s.id);
  return { list, byId, ids: order, refused, cfg: { rotate_bars: raw.rotate_bars ?? 16, fade_beats: raw.fade_beats ?? 4, min_bars: raw.min_bars ?? 8 } };
}
export async function fetchSetups(url, fetchImpl = globalThis.fetch, opts = {}) {
  const res = await fetchImpl(url);
  if (!res.ok) throw new Error(`setups: HTTP ${res.status}`);
  return loadSetups(await res.json(), opts);
}
export function stepSetup(lib, id, delta = 1) {
  const i = lib.ids.indexOf(id), n = lib.ids.length;
  return lib.ids[(((i < 0 ? (delta > 0 ? -1 : 0) : i) + delta) % n + n) % n];
}

// ------------------------------------------------------------------------------------------------- the rotation --
// The 16-bar line the next automatic change lands on, after pos: the next phrase line (bars apart from the bar anchor) at
// least minBars after the current setup landed (a setup O landed by hand just before a line keeps its phrase)
export function nextAutoLine(pos, barAnchor, landedAt, { bars = 16, minBars = 8 } = {}) {
  const span = 4 * bars;
  let line = barAnchor + span * (Math.floor((pos - barAnchor) / span + 1e-6) + 1);
  while (Number.isFinite(landedAt) && line - landedAt < 4 * minBars - 1e-6) line += span;
  return line;
}
// the next bar line after pos (O lands there)
export function nextBarLine(pos, barAnchor) { return barAnchor + 4 * (Math.floor((pos - barAnchor) / 4 + 1e-6) + 1); }
// The colours ONE GROUP can show under a setup over a whole bank turn: for each of its parts (centre, left, right) its a,
// its b and its white at every bank k, so the set follows the placement through kick 5's cycle and nothing else. This is
// what a group's wheel may be drawn from -- another part's colour (the lasers', the cubes', the halo's) is NOT this group's
// business, and a beam that takes it reads as a different fixture's colour on the frame.
export function groupColours(S, g, cycle = null) {
  const out = new Set();
  if (!S || !S.place[g]) return out;
  const cy = cycle || S.cycle, pl = S.place[g], n = Math.max(1, cy.length);
  // (k runs one PAST the cycle's length: a group that JOINS at an offset takes cycle[join] on the first press, so its range
  //  reaches cycle[join] .. cycle[m-1] over m presses and the colour before its offset only on the press after)
  for (let k = 0; k <= n; k++) {
    for (let part = 0; part < 3; part++) {
      if (part && !pl.sided) continue;
      out.add(nameAt(S, g, part, "a", k, cy)); out.add(nameAt(S, g, part, "b", k, cy)); out.add(nameAt(S, g, part, "w", k, cy));
    }
  }
  return out;
}
// which wheel slots a head may show: the slot nearest each colour of the group it belongs to (group, the placement's own
// colours: THE BEAMS FOLLOW THE SETUP), or -- with no group -- each of the setup's colours (the whole rig's range, which is
// right for a crossfade's "what it replaces" set and wrong for a lit group). Never a saturated-red slot.
export function setupSlots(S, wheel, red = [], roles = null, nearest = null, group = null) {
  if (!S || !wheel) return null;
  const allowed = [];
  for (let i = 0; i < wheel.length; i++) if (!red.includes(i)) allowed.push(i);
  const set = new Set([0]);
  const names = group ? groupColours(S, group, cycleOf(S, roles)) : S.names;
  for (const n of names) set.add(nearest(wheel, colourOf(S, n, roles), allowed));
  return [...set].sort((a, b) => a - b);
}
