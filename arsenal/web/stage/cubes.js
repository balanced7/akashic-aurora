// Virtual Stage, the strand's cubes as light-drawn objects: arsenal/web/stage/cubes.js. The pure half of the HAL 4000 cube
// (the GLSL is shaders.js CUBE_HAL_FRAGMENT, the draw is render.js): which style a viewer gets, the cube's two colours
// (the core line's and the glow's), the gradient along the strand, how far a kick takes the glow with it, and the spin.
//
// Daniel, 2026-10-29, with a screenshot of the strand's pink cubes: "we could also leverage gradients on the led cubes and
// perhaps even change the render shader for them to that crazy cool blue cube shader thing we have and then change the
// colors, what do you think?" ... "the hal 4000 shader". And: "not permantly only orange and gold, i want the lights to
// cycle different color palates and setups". So nothing here is blue: the core is the programmer's own cube colour
// (the palette's strand helix, the kicks, the levels), the glow comes from the palette's roles, and a setup can name both.
//
// The look (HAL 4000, Manwe, https://www.shadertoy.com/view/MtXczn, read in words for the shader atlas; no code taken):
// sparse, pillowy rounded-square loops, ONE hot thin core among dim hairlines in a deep wide glow, crossings combined by
// max so they stay crisp. Round 2 (the review of e8acaee81): two loops a face (the outer hot, the inner a hairline in the
// glow's colour), only the outer loop on the far faces, the hot core on the face that looks at the viewer (the others at
// HAL.hotFloor), corners at half the loop's size; the cubes blend by MAX (render.js), so cubes, faces and neighbours never
// sum to cream.
//
// THE HOOK (the "setups" build drives it): fs.cubeTint = cubeTintOf(palette defaults, override, out), every override field
// a linear-RGB triple or null (null: the palette's default):
//   glowTop, glowBottom   the glow's colour at the strand's first and last rung (the gradient ALONG the strand; only the
//                         hue counts: each end at unit brightness, mixed through OKLCh, so a dark deep never loses to a
//                         bright B and two complements turn round the hue circle instead of passing through white)
//   coreTop, coreBottom   null: the core is the programmer's live cube colour (its helix, kicks and level). A colour here
//                         replaces the core's HUE along the strand; the programmer's level still sets its brightness
//   glowMix               how far each cube's glow leans from its own core hue to the strand's glow colour (0..1). A kick on
//                         the cube's cells takes it back toward 0 (cubeKickOf): the whole cube shows the hit, as the solid
//                         cube does, and returns to the gradient as the kick fades
// The palette defaults (stage.js): glowTop the palette's deep (programmer.ambient, which crossfades with the palette),
// glowBottom its B role (the strand's second stop). On HAL's own palette that is a cyan core in a deep-blue glow.
import { mixLch } from "../palettes.js";

export const CUBE_STYLES = Object.freeze(["hal", "solid"]);

// ?cubes=hal|solid wins; automation keeps the solid cubes every lane was measured on; a viewer gets HAL
export function cubeStyleOf(asked, webdriver) {
  if (CUBE_STYLES.includes(asked)) return asked;
  return webdriver ? "solid" : "hal";
}

// The HAL cube's constants (the shader's uniforms). The cube is 1.1 m (half 0.55). rings: the loops on each face, outer
// first, in the cube's own metres: half-size, corner radius, light (x the cube's level), how much of the glow colour the
// loop's own core takes (0: the core colour, 1: the glow colour -- the gradient inside one cube), and the pen (x widthPx).
// A ring with gain 0 is not drawn (the shader has room for three).
export const HAL = Object.freeze({
  half: 0.55,
  rings: Object.freeze([
    Object.freeze({ half: 0.44, radius: 0.22, gain: 1.0, glow: 0.0, pen: 1.0 }),
    Object.freeze({ half: 0.29, radius: 0.15, gain: 0.32, glow: 0.85, pen: 0.7 }),
    Object.freeze({ half: 0.15, radius: 0.08, gain: 0, glow: 1.0, pen: 0.7 }),
  ]),
  widthPx: 1.5,      // the core's pen, screen pixels (never below one: neonLine's wire dims instead)
  haloPx: 18,        // the glow's reach, screen pixels (Lorentzian) ...
  haloMaxM: 0.035,   // ... but never wider than this on the face (m): a far cube's halo would fill its face and cut off
                     // hard at its silhouette (a painted box); there the bloom carries the glow instead
  ringStep: 0.15,    // the gap between the rings (m): the inner ring fades in from 3 to 8 px of it
  hotFloor: 0.4,     // the outer loop's light on a face turned away (x its full); the face that looks at the viewer ...
  hotFacing: Object.freeze([0.6, 0.95]),   // ... (|cos| of the view angle) runs hot: one hot loop, the others dim
  grazeFacing: Object.freeze([0.06, 0.35]), // a face seen edge-on fades out entirely (no aliased slivers on the outline)
  heat: 0.35,        // neonLine coreHeat at full level: the outer core leans toward white only near full
  lineGain: 1.1,     // the core line's light against the solid cube's face (x its emission)
  haloGain: 0.5,     // the halo's light, the same scale
  innerGain: 0.1,    // the soft inner bloom at the cube's heart (front faces only, so it is counted once): low, or a cube
                     // reads as a lit glass panel (round 2: 0.22 filled the faces once the cage thinned out)
  innerSigma: 0.3,   // its radius (m), a Gaussian across the view ray's miss distance from the centre
  backDim: 0.4,      // the far faces' outer loops, seen through the cube: dimmer, and spread by neonLine's defocus
  defocus: 0.45,
  glowMix: 0.7,
  tumble: 1,         // 0 holds every cube square to its rung
});

// The spin. The cube hangs on the rung's end with the rung's own dot strip running into its inner face, so it turns on
// that axle (the rung's x): the strip always meets that face square, never sticks out of a tumbling cube like a lollipop
// stick. A slow spin (about 40 s a turn) and a gentle wobble on the two other axes at incommensurate rates (sqrt 2 and the
// golden ratio x 0.11 rad/s, +-HAL_WOBBLE rad), a per-cube phase (the golden angle by index): no two cubes and no two
// moments line up. Angles are Euler XYZ (three.js order: the wobble first, then the spin about the axle).
export const SPIN_RATE = 0.16;
export const WOBBLE_RATES = Object.freeze([0.11 * Math.SQRT2, 0.11 * ((1 + Math.sqrt(5)) / 2)]);
export const HAL_WOBBLE = 0.14;
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
export function tumbleAngles(k, tSec, amount = 1, out = [0, 0, 0]) {
  const t = Number.isFinite(tSec) ? tSec : 0, a = Number.isFinite(amount) ? Math.min(1, Math.max(0, amount)) : 0;
  if (!(a > 0)) { out[0] = 0; out[1] = 0; out[2] = 0; return out; }
  const ph = GOLDEN_ANGLE * (k + 1);
  out[0] = a * (SPIN_RATE * t + ph);
  out[1] = a * HAL_WOBBLE * Math.sin(WOBBLE_RATES[0] * t + 2 * ph);
  out[2] = a * HAL_WOBBLE * Math.sin(WOBBLE_RATES[1] * t + 3 * ph);
  return out;
}

// a colour's hue at unit brightness (its brightest channel 1); black and non-finite input give black
export function unitHue(c, out = [0, 0, 0]) {
  const f = (x) => (Number.isFinite(+x) ? Math.max(0, +x) : 0);
  const r = f(c[0]), g = f(c[1]), b = f(c[2]);
  const m = Math.max(r, g, b);
  if (!(m > 1e-9)) { out[0] = 0; out[1] = 0; out[2] = 0; return out; }
  out[0] = r / m; out[1] = g / m; out[2] = b / m;
  return out;
}

const fin = (x) => Number.isFinite(+x);
const isRGB = (c) => (Array.isArray(c) || ArrayBuffer.isView(c)) && c.length >= 3 && fin(c[0]) && fin(c[1]) && fin(c[2]);

// The gradient along the strand, sampled: LUT_N unit hues from one end to the other through OKLCh (palettes.js mixLch, the
// palette crossfade's own mix), each end at unit brightness first. Rebuilt only when an end changes.
export const LUT_N = 17;
function hueRamp(a, b, lut) {
  const ua = unitHue(a), ub = unitHue(b), tmp = [0, 0, 0];
  for (let i = 0; i < LUT_N; i++) {
    const m = ua[0] + ua[1] + ua[2] > 0 && ub[0] + ub[1] + ub[2] > 0 ? mixLch(ua, ub, i / (LUT_N - 1)) : (i < LUT_N / 2 ? ua : ub);
    unitHue(m, tmp); lut[i * 3] = tmp[0]; lut[i * 3 + 1] = tmp[1]; lut[i * 3 + 2] = tmp[2];
  }
  return lut;
}
function sampleRamp(lut, u, out) {
  const x = Math.min(1, Math.max(0, u)) * (LUT_N - 1), i = Math.min(LUT_N - 2, Math.floor(x)), f = x - i;
  for (let c = 0; c < 3; c++) out[c] = lut[i * 3 + c] + (lut[(i + 1) * 3 + c] - lut[i * 3 + c]) * f;
  return out;
}
// one end of a ramp into the tint's own array (made once): true when it changed
function endInto(o, key, src) {
  if (!src) { const was = o[key] != null; o[key] = null; return was; }
  const dst = o[key] || (o[key] = [NaN, NaN, NaN]);
  if (dst[0] === +src[0] && dst[1] === +src[1] && dst[2] === +src[2]) return false;
  dst[0] = +src[0]; dst[1] = +src[1]; dst[2] = +src[2];
  return true;
}

// The frame's tint: the palette's defaults ({deep, B}: linear RGB) with a setup's override on top (see THE HOOK above).
// out (optional, the caller's own object, kept from frame to frame): its arrays and ramps are reused, and a ramp rebuilt
// only when an end moves (a palette crossfade, a setup), so a steady frame allocates nothing. The ends are copies, never
// the programmer's own arrays.
const DEEP_FALLBACK = Object.freeze([0.03, 0.01, 0.2]);
export function cubeTintOf(defaults, override = null, out = null) {
  const d = defaults || {}, ov = override && typeof override === "object" ? override : null;
  const deep = isRGB(d.deep) ? d.deep : DEEP_FALLBACK, second = isRGB(d.B) ? d.B : deep;
  const o = out || {};
  o.glowMix = ov && Number.isFinite(ov.glowMix) ? Math.min(1, Math.max(0, ov.glowMix)) : HAL.glowMix;
  const gT = ov && isRGB(ov.glowTop) ? ov.glowTop : deep, gB = ov && isRGB(ov.glowBottom) ? ov.glowBottom : second;
  // one core end named: the whole strand takes it
  const cT0 = ov && isRGB(ov.coreTop) ? ov.coreTop : null, cB0 = ov && isRGB(ov.coreBottom) ? ov.coreBottom : null;
  const cT = cT0 || cB0, cB = cB0 || cT0;
  const glowMoved = endInto(o, "glowTop", gT) | endInto(o, "glowBottom", gB);
  if (glowMoved || !o.glowLut) o.glowLut = hueRamp(o.glowTop, o.glowBottom, o.glowLut || new Float32Array(LUT_N * 3));
  const coreMoved = endInto(o, "coreTop", cT) | endInto(o, "coreBottom", cB);
  if (!cT) o.coreLut = null;
  else if (coreMoved || !o.coreLut) o.coreLut = hueRamp(o.coreTop, o.coreBottom, o.coreLut || new Float32Array(LUT_N * 3));
  return o;
}

// How much a kick holds one cube (0..1): the programmer's colour-kick weight on its cells (kickC[.. + 3], written by
// kick.js) and the white kick's (kick.js paints the white role over the look's with its weight as the cell's mix). src:
// { kickC, tC, whiteRole } from the programmer (stage.js), or null (no kicks: 0).
export function cubeKickOf(src, cell0, ncell) {
  if (!src) return 0;
  const kC = src.kickC, tC = src.tC, W = Number.isInteger(src.whiteRole) ? src.whiteRole : -1;
  let w = 0;
  for (let c = cell0; c < cell0 + ncell; c++) {
    const b = c * 4;
    if (kC && kC.length > b + 3) w = Math.max(w, +kC[b + 3] || 0);
    if (tC && W >= 0 && tC.length > b + 3) {
      const mix = Math.min(1, Math.max(0, +tC[b + 1] || 0));
      if ((tC[b + 3] | 0) === W) w = Math.max(w, mix);
      if ((tC[b + 2] | 0) === W) w = Math.max(w, 1 - mix);
    }
  }
  return Math.min(1, Math.max(0, w));
}

// One cube's two colours. emit: the programmer's cube light (linear RGB, already in scene units: colour x level x nits);
// t: its place along the strand (0 at the first rung, 1 at the last); tint: cubeTintOf's; kick: cubeKickOf's (0..1).
// Writes the core light (scene units: the setup's core hue if it names one, at the programmer's brightness) to core, and
// the glow's HUE (unit brightness) to glow; the shader scales the glow by the core's level. Returns the level (the core's
// brightest channel).
const tmpA = [0, 0, 0], tmpB = [0, 0, 0], tmpC = [0, 0, 0];
export function cubeColours(emit, t, tint, core, glow, kick = 0) {
  const u = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0));
  const level = Math.max(0, +emit[0] || 0, +emit[1] || 0, +emit[2] || 0);
  if (tint && tint.coreLut) {
    sampleRamp(tint.coreLut, u, tmpB); unitHue(tmpB, tmpB);
    for (let i = 0; i < 3; i++) core[i] = tmpB[i] * level;
  } else for (let i = 0; i < 3; i++) core[i] = Math.max(0, +emit[i] || 0);
  unitHue(core, tmpA);                                         // the core's own hue
  if (!tint || !tint.glowLut) { glow[0] = tmpA[0]; glow[1] = tmpA[1]; glow[2] = tmpA[2]; return level; }
  sampleRamp(tint.glowLut, u, tmpC); unitHue(tmpC, tmpC);     // the strand's glow hue here
  const k = Math.min(1, Math.max(0, Number.isFinite(kick) ? kick : 0));
  const m = (Number.isFinite(tint.glowMix) ? tint.glowMix : HAL.glowMix) * (1 - k);
  for (let i = 0; i < 3; i++) tmpB[i] = tmpA[i] + (tmpC[i] - tmpA[i]) * m;
  unitHue(level > 0 ? tmpB : tmpC, glow);
  return level;
}
