// Virtual Stage, the strand's cubes as light-drawn objects: arsenal/web/stage/cubes.js. The pure half of the HAL 4000 cube
// (the GLSL is shaders.js CUBE_HAL_FRAGMENT, the draw is render.js): which style a viewer gets, the cube's two colours
// (the core line's and the glow's), the gradient along the strand, and the slow tumble.
//
// Daniel, 2026-10-29, with a screenshot of the strand's pink cubes: "we could also leverage gradients on the led cubes and
// perhaps even change the render shader for them to that crazy cool blue cube shader thing we have and then change the
// colors, what do you think?" ... "the hal 4000 shader". And: "not permantly only orange and gold, i want the lights to
// cycle different color palates and setups". So nothing here is blue: the core is the programmer's own cube colour
// (the palette's strand helix, the kicks, the levels), the glow comes from the palette's roles, and a setup can name both.
//
// The look (HAL 4000, Manwe, https://www.shadertoy.com/view/MtXczn, read in words for the shader atlas; no code taken):
// nested rounded-square outlines, a hot thin core over a deep wide glow, crossings combined by max so they stay crisp,
// a tumble at three incommensurate rates (the atlas's rotateEuler, A1.13, P1: not yet a house module, so the angles are
// computed here and the matrix on the CPU, once per cube per frame).
//
// THE HOOK (the "setups" build drives it): fs.cubeTint = cubeTintOf(palette defaults, override), where every field is a
// linear-RGB triple or null (null: the palette's default):
//   glowTop, glowBottom   the glow's colour at the strand's first and last rung (the gradient ALONG the strand)
//   coreTop, coreBottom   null: the core is the programmer's live cube colour (its helix, kicks and level). A colour here
//                         replaces the core's HUE along the strand; the programmer's level still sets its brightness
//   glowMix               how far each cube's glow leans from its own core hue to the strand's glow colour (0..1)
// The palette defaults (stage.js): glowTop the palette's deep (programmer.ambient, which crossfades with the palette),
// glowBottom its B role (the strand's second stop). On HAL's own palette that is a cyan core in a deep-blue glow.

export const CUBE_STYLES = Object.freeze(["hal", "solid"]);

// ?cubes=hal|solid wins; automation keeps the solid cubes every lane was measured on; a viewer gets HAL
export function cubeStyleOf(asked, webdriver) {
  if (CUBE_STYLES.includes(asked)) return asked;
  return webdriver ? "solid" : "hal";
}

// The HAL cube's constants (the shader's uniforms). rings: the nested outlines on each face, outer first, in the cube's
// own metres (the cube is 1.1 m, half 0.55): half-size, corner radius, light (x the cube's level), and how much of the
// glow colour the ring's own core takes (0: the core colour, 1: the glow colour -- the gradient inside one cube).
export const HAL = Object.freeze({
  rings: Object.freeze([
    Object.freeze({ half: 0.47, radius: 0.16, gain: 1.0, glow: 0.0 }),
    Object.freeze({ half: 0.33, radius: 0.11, gain: 0.5, glow: 0.65 }),
    Object.freeze({ half: 0.19, radius: 0.065, gain: 0.3, glow: 1.0 }),
  ]),
  widthPx: 1.5,      // the core's pen, screen pixels (never below one: neonLine's wire dims instead)
  haloPx: 18,        // the glow's reach, screen pixels (Lorentzian) ...
  haloMaxM: 0.035,   // ... but never wider than this on the face (m): a far cube's halo would fill its face and cut off
                     // hard at its silhouette (a painted box); there the bloom carries the glow instead
  ringStep: 0.14,    // the gap between the rings (m): the inner rings fade in from 3 to 8 px of it
  graze: 0.3,        // a face seen edge-on keeps this much of its light
  heat: 0.35,        // neonLine coreHeat at full level: the outer core leans toward white only near full
  lineGain: 1.1,     // the core line's light against the solid cube's face (x its emission)
  haloGain: 0.5,     // the halo's light, the same scale
  innerGain: 0.22,   // the soft inner bloom at the cube's heart (front faces only, so it is counted once)
  innerSigma: 0.3,   // its radius (m), a Gaussian across the view ray's miss distance from the centre
  backDim: 0.55,     // the far faces' outlines, seen through the cube: dimmer, and spread by neonLine's defocus
  defocus: 0.45,
  glowMix: 0.7,
  tumble: 1,         // 0 holds every cube square to its rung
});

// The tumble: three incommensurate rates (1, sqrt 2, the golden ratio, x 0.11 rad/s: the slowest axis turns once in
// about a minute) and a per-cube phase (the golden angle by index), so no two cubes and no two moments line up.
export const TUMBLE_RATES = Object.freeze([0.11, 0.11 * Math.SQRT2, 0.11 * ((1 + Math.sqrt(5)) / 2)]);
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
export function tumbleAngles(k, tSec, amount = 1, out = [0, 0, 0]) {
  const t = Number.isFinite(tSec) ? tSec : 0, a = Number.isFinite(amount) ? amount : 0;
  for (let i = 0; i < 3; i++) out[i] = a * (TUMBLE_RATES[i] * t + GOLDEN_ANGLE * (k + 1) * (i + 1));
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

const isRGB = (c) => Array.isArray(c) || ArrayBuffer.isView(c) ? c.length >= 3 && [0, 1, 2].every((i) => Number.isFinite(+c[i])) : false;
const pick = (ov, key, dflt) => (ov && isRGB(ov[key]) ? [+ov[key][0], +ov[key][1], +ov[key][2]] : dflt ? [dflt[0], dflt[1], dflt[2]] : null);

// The frame's tint: the palette's defaults ({deep, B}: linear RGB) with a setup's override on top (see THE HOOK above)
export function cubeTintOf(defaults, override = null) {
  const d = defaults || {};
  const deep = isRGB(d.deep) ? d.deep : [0.03, 0.01, 0.2], second = isRGB(d.B) ? d.B : deep;
  const mix = override && Number.isFinite(override.glowMix) ? Math.min(1, Math.max(0, override.glowMix)) : HAL.glowMix;
  // one core end named: the whole strand takes it
  const cT = pick(override, "coreTop", null), cB = pick(override, "coreBottom", null);
  return {
    glowTop: pick(override, "glowTop", deep), glowBottom: pick(override, "glowBottom", second),
    coreTop: cT || cB, coreBottom: cB || cT, glowMix: mix,
  };
}

// One cube's two colours. emit: the programmer's cube light (linear RGB, already in scene units: colour x level x nits);
// t: its place along the strand (0 at the first rung, 1 at the last); tint: cubeTintOf's. Writes the core light (scene
// units: the setup's core hue if it names one, at the programmer's brightness) to core, and the glow's HUE (unit
// brightness) to glow; the shader scales the glow by the core's level. Returns the level (the core's brightest channel).
const tmpA = [0, 0, 0], tmpB = [0, 0, 0], tmpC = [0, 0, 0];
export function cubeColours(emit, t, tint, core, glow) {
  const u = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0));
  const level = Math.max(0, +emit[0] || 0, +emit[1] || 0, +emit[2] || 0);
  if (tint && tint.coreTop && tint.coreBottom) {
    for (let i = 0; i < 3; i++) tmpA[i] = tint.coreTop[i] + (tint.coreBottom[i] - tint.coreTop[i]) * u;
    unitHue(tmpA, tmpB);
    for (let i = 0; i < 3; i++) core[i] = tmpB[i] * level;
  } else for (let i = 0; i < 3; i++) core[i] = Math.max(0, +emit[i] || 0);
  unitHue(core, tmpA);                                         // the core's own hue
  if (!tint) { glow[0] = tmpA[0]; glow[1] = tmpA[1]; glow[2] = tmpA[2]; return level; }
  for (let i = 0; i < 3; i++) tmpB[i] = tint.glowTop[i] + (tint.glowBottom[i] - tint.glowTop[i]) * u;
  unitHue(tmpB, tmpC);                                         // the strand's glow hue here
  const m = tint.glowMix;
  for (let i = 0; i < 3; i++) tmpB[i] = tmpA[i] + (tmpC[i] - tmpA[i]) * m;
  unitHue(level > 0 ? tmpB : tmpC, glow);
  return level;
}
