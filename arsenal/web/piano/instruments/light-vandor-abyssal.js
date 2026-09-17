// Abyssal — arsenal/web/piano/instruments/light-vandor-abyssal.js  (ES module; a piano instrument for the "Instruments of
// light" round, research/in-flight/piano-light-instruments-2026-09-17/brief.md)
//
// A bioluminescent deep-sea instrument on a blue-black stage. Above the keys hangs a school of seven jellyfish, one per
// octave (the A0-B1 animal large and high, the C7-C8 one small and low), and every one of the 88 keys owns a translucent
// tentacle that falls from its bell's rim to a photophore bead sitting just behind that key. The piano is strung with
// living light, and it never stops being a piano: each tentacle lands exactly on its key.
//
//   strike     the bead behind the key sparks (the hammer), the bell over it flinches in a swim stroke, and a pulse of light
//              leaves the bell and races DOWN the tentacle to the key, shedding plankton as it passes. Velocity sets the
//              pulse's brightness, its speed (pp 0.40 s, ff 0.13 s) and how many sparkles it sheds; only this flash may
//              cross the bloom line.
//   sustain    while the note sounds (state.sounding) the tentacle keeps a slow breathing glow on a velocity-scaled floor,
//              with a pitch-dependent aftersound: the same envelope the concert grand and the crystal grand run, so the
//              three answer a held pedal identically (PEAK/FLOOR/TAU table below). A finger-held tentacle breathes shallow;
//              one only the damper pedal holds breathes deep. A re-strike sends a new pulse from the level it finds.
//   damping    when the sound ends the glow drains in 0.30 s (a smoothstep window, never a snap) and the sparkles die with it.
//   pedal      only what sounds lights. The pedal alone never lights an unstruck tentacle; it relaxes the bells open a little.
//   low notes  bass tentacles are thick and sway, and while they sound they vibrate as a wide translucent motion blur: three
//              phase-offset ghost strands sweeping inside a time-averaged (arcsine) envelope, the Dune ornithopter wing.
//              Light is conserved (a wider blur is a dimmer one). Treble tentacles are fine filaments with a fast shimmer.
//   material   harmony-feel.js: lushness thickens a marine snow (drifting motes in curl-noise water, lit by the bells),
//              tension quickens the bells' breathing and darkens the water toward indigo, simplicity clears the water and
//              stills the bells.
//   dance      a faint current runs between the bass tentacle and the solo (melody) tentacle: two strands that braid tighter
//              in contrary motion, sag as the voices spread and tighten as they pull together; its colour follows the
//              consonance of the interval (sea-green when sweet, hot magenta when sour).
//   moment     moment.js: intensity inflates a luminous artifact inside the bell over the chord's root register, seeded per
//              chord, which bursts into a cloud of plankton when the chord changes (artifact.released, scaled by
//              releaseStrength); mood.valence shifts the water's hue (teal when bright, violet when dark); energy drives the
//              bells' breathing rate.
//
// Contract: export default { id, name, create(ctx) } -> { group, update(dt, t, state), resize(framing), setActive(on),
// dispose() }, plus keyStyle and hints (hideHostBody, floorY). Everything comes through ctx (THREE, keyX, isBlack,
// noteColor, framing); no camera, renderer, fog, background or layer is ever written.
//
// Draw calls: 6, fixed (tentacles + oral arms + the dance strands as one instanced ribbon; the bells instanced; the beads
// instanced; marine snow + plankton as one Points; the water column; the sea-bed pool). No allocation in update(): every
// per-note number lives in typed arrays and one 88 x 6 float texture, particles in a preallocated ring, the harmony-feel and
// moment helpers refresh one object each in place. dispose() returns every geometry, texture and program.
//
// ---- the string light envelope (the concert grand's table, kept identical so the three instruments agree) ----
//   PEAK_EXP        body height at the strike = v^PEAK_EXP (v = vel/127)                1.35
//   FLASH_EXP       the strike transient's height = v^FLASH_EXP                        2.0
//   TAU_FLASH       the transient's decay: the only part allowed over the bloom line     0.09 s
//   FLOOR_LO/HI     the floor the body settles on, as a share of the strike body,        0.33 at vel 1 -> 0.50 at vel 127
//                   held for the WHOLE sound, finger or pedal
//   AFTER_SHARE     how much of the above-floor body is in the slow aftersound           0.55
//   TAU_PROMPT      the prompt decay                                                      1.00 s at A0 -> 0.45 s at C8
//   TAU_AFTER       the aftersound, pitch-dependent                                       7.0 s at A0 -> 1.2 s at C8
//   TAU_DAMP        the damper landing when the sound ENDS (fall time constant)           0.16 s
//   DAMP_FADE       the window that closes that fall to exactly 0                        0.30 s
//   TAU_VIB_OFF     the blur dies faster than the light                                   0.07 s
// ---- the tentacle blur (Dune's wings) ----
//   ENV_BASS/TREBLE swing half-amplitude at full body, world units, geometric in pitch  1.05 -> 0.03
//   ENV_EXP         amplitude = ENV(pitch) * body^ENV_EXP: narrows as the note settles, never stops while it sounds  0.8
//   GHOST_HZ        the ghost strands' sweep rate: slow in the bass, a shimmer at the top  2.2 Hz -> 7.5 Hz
// ---- the strike ----
//   TRAVEL_PP/FF    the pulse's trip from the bell to the key                             0.40 s -> 0.13 s
//   PULSE_GAIN      the pulse head = v^2 * PULSE_GAIN (crosses the bloom line from ~mf)  2.4
//   CONTACT_GAIN    the bead's spark at the key                                           2.3
//   SPARKS_MIN/VEL  plankton shed per strike = SPARKS_MIN + SPARKS_VEL * v^1.5            3 + 34
// ---- the bells ----
//   BELL_SUS_CAP    luma cap of a bell's sustained tint (rest is far below it)            0.16
//   BELL_FLASH_CAP  luma cap of a bell's strike flash                                     0.9
//   BREATH_HZ       bell breathing: BREATH_HZ + energy * 0.35 + tension * 0.5             0.22 Hz
import { createHarmonyFeel } from "../harmony-feel.js";
import { createMoment } from "../moment.js";

export const ABYSSAL = Object.freeze({
  PEAK_EXP: 1.35, FLASH_EXP: 2, FLOOR_LO: 0.33, FLOOR_HI: 0.50, AFTER_SHARE: 0.55,
  TAU_PROMPT_BASS: 1.00, TAU_PROMPT_TREBLE: 0.45, TAU_AFTER_BASS: 7.0, TAU_AFTER_TREBLE: 1.2,
  TAU_FLASH: 0.09, TAU_DAMP: 0.16, DAMP_FADE: 0.30, TAU_VIB_OFF: 0.07,
  ENV_BASS: 1.05, ENV_TREBLE: 0.03, ENV_EXP: 0.8, GHOST_HZ_BASS: 2.2, GHOST_HZ_TREBLE: 7.5,
  TRAVEL_PP: 0.40, TRAVEL_FF: 0.13, PULSE_GAIN: 2.4, CONTACT_GAIN: 2.3, SUS_GAIN: 0.78,
  SPARKS_MIN: 3, SPARKS_VEL: 34,
  BELL_SUS_CAP: 0.16, BELL_FLASH_CAP: 0.9, BREATH_HZ: 0.22, PUMP_CONTRACT: 0.14, PUMP_TAU_UP: 0.045, PUMP_TAU_DECAY: 0.3,
  CORE_BASS: 0.13, CORE_TREBLE: 0.018, SWAY_BASS: 0.5, SWAY_TREBLE: 0.05,
  SNOW_MIN: 0.05, SNOW_TAU_IN: 1.4, SNOW_TAU_OUT: 2.6,
  FLOOR_Y: -8,
});
const K = ABYSSAL;
const TAU = Math.PI * 2;
const N = 88, FIRST = 21, BELLS = 7, ARMS_PER_BELL = 5, STRANDS = 2;
const SEG = 56;                                   // ribbon segments along a tentacle
const ROWS = 6;                                   // note texture rows (see writeNote)
const SNOW = 1400, PLANKTON = 2800;               // the points pool: marine snow first, then the plankton ring
const BELL_FIRST = [21, 36, 48, 60, 72, 84, 96];
const BELL_LAST = [35, 47, 59, 71, 83, 95, 108];
const BELL_Z = [-14.5, -6.2, -11.8, -5.0, -9.4, -4.4, -7.6];    // the school hangs at different depths
const BELL_JITTER = [1.06, 0.93, 1.02, 0.96, 1.05, 0.94, 1.0];  // no two of them the same size
const TIP_Y = 0.95, TIP_Z = -3.62, TIP_Z_BLACK = -3.98;         // the beads: just behind the key backs, never over the keybed
export const bellOf = (m) => (m <= 35 ? 0 : m >= 96 ? 6 : Math.floor((m - 36) / 12) + 1);
export const pitchOf = (m) => (m - FIRST) / (N - 1);            // 0 at A0, 1 at C8
export const overPitch = (m, lo, hi) => lo * Math.pow(hi / lo, pitchOf(m));
export const travelOf = (v) => K.TRAVEL_PP + (K.TRAVEL_FF - K.TRAVEL_PP) * v;

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
const damp = (a, b, tau, dt) => b + (a - b) * Math.exp(-dt / Math.max(tau, 1e-4));
const luma = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
// The damper's fade, x seconds after the sound ended: the stored terms already fall at TAU_DAMP, and this window closes
// that fall to exactly 0 at DAMP_FADE with zero slope, so the light never outlives the sound and never snaps.
export const dampFade = (x) => { if (x >= K.DAMP_FADE) return 0; if (x <= 0) return 1; const u = x / K.DAMP_FADE; return 1 - u * u * (3 - 2 * u); };

function mulberry32(seed) {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ------------------------------------------------------------------------------------------------ shaders --
// Every material shares one uniform object. The note texture is 88 x 6 (RGBA float, nearest):
//   row 0  E body, F flash, H pulse head (0 bell .. 1 key, < 0 none), A blur amplitude (world units)
//   row 1  r g b the note's light, D the damper window (1 sounding, falling to 0 over DAMP_FADE after the sound ends)
//   row 2  P pulse brightness, B breath (0..1), M held mix (1 finger, 0 pedal only), R recoil
//   row 3  anchor on the bell rim (bell radii) xyz, bell index
//   row 4  tip xyz (the bead behind the key), phase
//   row 5  ring (the shock at the bead, 0..1 over 0.3 s), kick, velocity, register
const COMMON = /* glsl */ `
precision highp float;
uniform sampler2D uNotes;
uniform vec4 uBellPos[7];      // xyz, radius
uniform vec4 uBellAnim[7];     // pump (swim stroke), breath, artifact, open (pedal)
uniform vec4 uBellCol[7];      // sustained tint rgb (luma capped), w = lit amount 0..1
uniform vec4 uBellFlash[7];    // strike flash rgb
uniform vec4 uArtCol;          // the artifact's light rgb, w = seed phase
uniform vec4 uMat;             // lushness, tension, simplicity, brightness
uniform vec4 uMood;            // valence, energy, snow density, pedal
uniform vec4 uDance;           // bass note index, solo note index, consonance, braid
uniform vec4 uDance2;          // phase, stretch, pull, on
uniform vec4 uDanceCol;        // the current's colour, w = travel speed
uniform vec3 uWater;           // the water column's top tint
uniform vec2 uRes;             // drawing-buffer size of the pass drawing
// The pow function is undefined for a base under zero, and 1 - |n.v| or 0.5 + 0.5 cos land a rounding error under it; one NaN
// pixel then spreads through the host's bloom mips into a black rectangle (RX 9070 XT, about one frame in 200, traced to
// the bell's high-exponent terms). So no pow here ever sees a base under 1e-4: squares are products, the sharp cosine
// lobes are shaped with exp of a bounded argument, and the rest go through ppow.
float sq(float x) { return x * x; }
float ppow(float x, float y) { return pow(max(x, 1e-4), y); }
float lobe(float c, float k) { return exp(-k * (1.0 - c)); }   // ~ (0.5 + 0.5 c)^(2k) around the peak of a cosine c
uniform float uTime;
const float PI = 3.14159265;
vec4 noteRow(int n, int row) { return texelFetch(uNotes, ivec2(n, row), 0); }
vec3 bez(vec3 a, vec3 b, vec3 c, vec3 d, float t) { float u = 1.0 - t; return u*u*u*a + 3.0*u*u*t*b + 3.0*u*t*t*c + t*t*t*d; }
vec3 bezd(vec3 a, vec3 b, vec3 c, vec3 d, float t) { float u = 1.0 - t; return 3.0*u*u*(b - a) + 6.0*u*t*(c - b) + 3.0*t*t*(d - c); }
// A tentacle's curve: from its anchor on the bell rim (which squeezes with the swim stroke) to the bead behind its key.
void tentacleCtrl(int n, out vec3 p0, out vec3 p1, out vec3 p2, out vec3 p3) {
  vec4 an = noteRow(n, 3), tp = noteRow(n, 4);
  int bi = int(an.w + 0.5);
  vec4 bp = uBellPos[bi], ba = uBellAnim[bi];
  float contract = 1.0 - (${K.PUMP_CONTRACT.toFixed(3)} * ba.x + ba.y) * 0.87 + 0.05 * ba.w;
  p0 = bp.xyz + vec3(an.x * bp.w * contract, an.y * bp.w, an.z * bp.w * contract);
  p3 = tp.xyz;
  float L = p0.y - p3.y;
  p1 = p0 + vec3(an.x * bp.w * 0.22, -0.32 * L, an.z * bp.w * 0.3);
  p2 = p3 + vec3(0.0, 0.40 * L, -0.35);
}
vec3 swayOf(float s, float reg, float ph, float sway) {
  float bow = 4.0 * s * (1.0 - s);
  return vec3(sway * bow * sin(uTime * (0.37 + 0.35 * reg) + s * 2.4 + ph), 0.0,
              sway * bow * 0.7 * sin(uTime * (0.29 + 0.3 * reg) + s * 2.0 + ph * 1.7));
}
`;

const TENTACLE_VS = /* glsl */ `
${COMMON}
attribute vec4 aInfo;     // note index (kind 2: strand), bell index, kind (0 tentacle, 1 oral arm, 2 dance strand), phase
attribute vec3 aAnchor;   // rim offset in bell radii
attribute vec3 aTip;      // tentacle: world tip; arm: offset from its anchor
attribute vec4 aShape;    // core half width, sway, blur amplitude scale, register
varying float vS, vAcross, vCore, vEnv, vPx, vLen, vKind, vPhase, vReg, vBell, vOmega;
varying vec4 vN0, vN1, vN2;
void main() {
  float s = position.x, side = position.y;
  int ni = int(aInfo.x + 0.5), bi = int(aInfo.y + 0.5);
  float kind = aInfo.z;
  vec4 n0 = vec4(0.0, 0.0, -1.0, 0.0), n1 = vec4(0.0), n2 = vec4(0.0);
  vec3 P, Tn;
  float core = aShape.x, env = 0.0, len = 4.0, reg = aShape.w, ph = aInfo.w;
  if (kind < 0.5) {
    n0 = noteRow(ni, 0); n1 = noteRow(ni, 1); n2 = noteRow(ni, 2);
    vec3 p0, p1, p2, p3;
    tentacleCtrl(ni, p0, p1, p2, p3);
    P = bez(p0, p1, p2, p3, s);
    Tn = bezd(p0, p1, p2, p3, s);
    P += swayOf(s, reg, ph, aShape.y);
    // strike recoil: the tentacle flinches back from the key and rings out
    float bow = 4.0 * s * (1.0 - s);
    P.z -= n2.w * bow * (0.12 + 0.35 * (1.0 - reg));
    core *= mix(1.0, 0.55, s * s * s);
    // the standing wave: pinched at the bell and at the key, widest in the middle, a touch of the second mode
    env = max(0.0, aShape.z * n0.w * (ppow(sin(PI * s), 1.35) + 0.12 * sin(2.0 * PI * s + ph)));
    len = max(p0.y - p3.y, 1.0);
  } else if (kind < 1.5) {
    vec4 bp = uBellPos[bi], ba = uBellAnim[bi];
    float contract = 1.0 - (${K.PUMP_CONTRACT.toFixed(3)} * ba.x + ba.y) * 0.87 + 0.05 * ba.w;
    vec3 p0 = bp.xyz + vec3(aAnchor.x * bp.w * contract, aAnchor.y * bp.w, aAnchor.z * bp.w * contract);
    vec3 p3 = p0 + aTip * (1.0 + 0.1 * ba.x);
    vec3 p1 = p0 + vec3(aTip.x * 0.1, aTip.y * 0.35, aTip.z * 0.1);
    vec3 p2 = p0 + vec3(aTip.x * 0.8, aTip.y * 0.7, aTip.z * 0.8);
    P = bez(p0, p1, p2, p3, s);
    Tn = bezd(p0, p1, p2, p3, s);
    P.x += aShape.y * s * s * sin(uTime * 0.5 + s * 2.4 + ph);
    P.z += aShape.y * s * s * 0.7 * sin(uTime * 0.41 + s * 2.0 + ph * 1.7);
    core *= 0.6 + 0.4 * sin(s * PI);
  } else {
    // the dance: a current between the bass tentacle and the solo tentacle, two strands braided round the line between
    // them. It sags as the voices spread, tightens as they pull together and twists faster in contrary motion.
    int nb = int(uDance.x + 0.5), ns = int(uDance.y + 0.5);
    vec3 a0, a1, a2, a3, b0, b1, b2, b3;
    tentacleCtrl(nb, a0, a1, a2, a3);
    tentacleCtrl(ns, b0, b1, b2, b3);
    vec4 tb = noteRow(nb, 4), ts = noteRow(ns, 4);
    float rb = float(nb) / 87.0, rs = float(ns) / 87.0;
    vec3 A = bez(a0, a1, a2, a3, 0.52) + swayOf(0.52, rb, tb.w, mix(${K.SWAY_BASS.toFixed(3)}, ${K.SWAY_TREBLE.toFixed(3)}, pow(rb, 0.6)));
    vec3 B = bez(b0, b1, b2, b3, 0.52) + swayOf(0.52, rs, ts.w, mix(${K.SWAY_BASS.toFixed(3)}, ${K.SWAY_TREBLE.toFixed(3)}, pow(rs, 0.6)));
    float sag = max(0.3, 1.2 + 4.0 * uDance2.y - 2.5 * uDance2.z);
    vec3 c1 = mix(A, B, 0.33) - vec3(0.0, sag, 0.0), c2 = mix(A, B, 0.67) - vec3(0.0, sag, 0.0);
    P = bez(A, c1, c2, B, s);
    Tn = bezd(A, c1, c2, B, s);
    vec3 dir = normalize(B - A + vec3(1e-4, 0.0, 0.0));
    vec3 u = normalize(cross(dir, vec3(0.0, 1.0, 0.0)) + vec3(0.0, 0.0, 1e-4)), v = cross(dir, u);
    float twist = 1.5 + 7.0 * uDance.w;
    float th = s * twist * 2.0 * PI + uDance2.x * 2.0 * PI + aInfo.x * PI;
    float rad = (0.16 + 0.5 * uDance2.y) * sin(PI * s);
    P += (u * cos(th) + v * sin(th)) * rad;
    reg = 0.5;
  }
  Tn = normalize(Tn + vec3(0.0, -1e-4, 0.0));
  vec3 Pw = (modelMatrix * vec4(P, 1.0)).xyz;
  vec3 V = normalize(cameraPosition - Pw);
  vec3 across = normalize(cross(Tn, V) + vec3(1e-5, 0.0, 0.0));
  vec4 mv = viewMatrix * vec4(Pw, 1.0);
  float px = 2.0 * max(-mv.z, 0.1) / (projectionMatrix[1][1] * uRes.y);   // one drawing-buffer pixel in world units here
  float halfW = max(core, px) * 3.4 + env + 2.0 * px;
  Pw += across * side * halfW;
  vAcross = side * halfW;
  vS = s; vCore = core; vEnv = env; vPx = px; vKind = kind; vPhase = ph; vReg = reg; vBell = float(bi); vLen = len;
  vOmega = 2.0 * PI * mix(${K.GHOST_HZ_BASS.toFixed(2)}, ${K.GHOST_HZ_TREBLE.toFixed(2)}, reg);
  vN0 = n0; vN1 = n1; vN2 = n2;
  gl_Position = projectionMatrix * viewMatrix * vec4(Pw, 1.0);
}`;

const TENTACLE_FS = /* glsl */ `
${COMMON}
varying float vS, vAcross, vCore, vEnv, vPx, vLen, vKind, vPhase, vReg, vBell, vOmega;
varying vec4 vN0, vN1, vN2;
void main() {
  float a = abs(vAcross);
  float core = max(vCore, vPx * 0.8);
  float cover = min(1.0, vCore / core);            // a sub-pixel filament gets dimmer, not thinner
  float body = exp(-(a * a) / (core * core) * 1.9) * cover;
  float skirt = exp(-a / (core * 1.5)) * 0.16 * cover;
  float halo = exp(-(a * a) / (core * core * 9.0)) * 0.1 * cover;
  float coreShape = body + skirt * 0.6;
  // The vibrating tentacle as a camera sees a moving string: three phase-offset ghost strands sweep inside the arcsine
  // envelope (density 1/sqrt(1-(x/A)^2), brightest at the turning points). Light is conserved: the wider the swing, the
  // fainter each pixel, so a bass blur never stacks toward white.
  float env = vEnv;
  float envW = env + core;
  float xn = a / envW;
  float arcs = min(inversesqrt(max(1.0 - xn * xn, 0.03)), 4.0);
  float edge = 1.0 - smoothstep(0.6, 1.0 + (1.6 * core + vPx) / envW, xn);
  float spread = env / (env + core * 1.1);
  float wing = arcs * edge * (core * 1.05 / envW) * cover;
  float w = uTime * vOmega + vPhase, gw = core * 2.2;
  float ghosts = (exp(-sq((vAcross - env * sin(w)) / gw)) + exp(-sq((vAcross - env * sin(w + 2.0944)) / gw))
                + exp(-sq((vAcross - env * sin(w + 4.1888)) / gw))) * 0.34 * cover * (core / envW + 0.35);
  float shape = mix(body + skirt, wing * 0.55 + ghosts + body * 0.12 + halo * 0.6, spread);

  vec3 emit;
  if (vKind < 0.5) {
    float E = vN0.x, F = vN0.y, H = vN0.z, P = vN2.x, B = vN2.y, M = vN2.z;
    // the pulse: a bright head running from the bell (s = 0) to the key (s = 1) with a short wake behind it
    float d = vS - H;
    float hw = 0.03 + 0.03 * clamp(P * 0.4, 0.0, 1.0);
    float headG = H >= 0.0 ? exp(-(d * d) / (hw * hw)) : 0.0;
    float wake = H >= 0.0 && d < 0.0 ? exp(d * 9.0) * 0.35 : 0.0;
    float pulse = (headG + wake) * P;
    // the sustained light fills in BEHIND the head, so the glow descends from the animal instead of appearing at once
    float fill = H >= 0.0 && H < 1.2 ? 0.3 + 0.7 * (1.0 - smoothstep(H - 0.04, H + 0.08, vS)) : 1.0;
    // the strike: a flash over the whole tentacle and the hammer's spark at the key end
    float flash = F * exp(-(1.0 - vS) * 2.5) * 0.35;
    float contact = F * exp(-(1.0 - vS) * vLen * 1.6) * ${K.CONTACT_GAIN.toFixed(2)};
    // photophores: unevenly spaced beads along the tentacle, the way a real one carries its light organs
    float u = vS * vLen;
    float cell = floor(u / 0.85);
    float jitter = fract(sin(cell * 91.7 + vPhase) * 4371.13);
    float beads = ppow(0.5 + 0.5 * cos(2.0 * PI * (u / 0.85 - 0.35 * jitter)), 8.0) * (0.55 + 0.45 * jitter);
    // breathing: shallow under a finger, deep when only the pedal holds the sound
    float breathe = 1.0 - mix(0.32, 0.12, M) * B;
    // the light comes from the animal but the string is struck at the key: strongest along the middle, tapered at the
    // rim where a bell's tentacles converge (so their halos never stack toward the bloom line)
    float taper = smoothstep(0.0, 0.35, vS) * 0.7 + 0.3;
    float sus = E * breathe * taper * fill;
    vec3 col = vN1.rgb;
    vec3 rest = vec3(0.0075, 0.021, 0.04) + col * 0.012;
    vec3 sus3 = rest * (coreShape * (0.94 + 0.3 * beads)) * (1.0 - 0.6 * min(E, 1.0))
              + col * sus * ${K.SUS_GAIN.toFixed(2)} * (shape + coreShape * beads * 0.3);
    // sustained light never crosses the bloom line, whatever the tuning: the cap is read on screen (after Neutral tone
    // mapping and sRGB), where 0.57 linear is 0.85, and neighbouring tentacles stack under it
    float lu = dot(sus3, vec3(0.2126, 0.7152, 0.0722)) * 1.5;
    sus3 *= min(1.0, 0.85 / max(lu, 1e-4));
    emit = sus3 + col * (pulse * (coreShape + halo * 2.0) + flash * coreShape + contact * (body + skirt));
  } else if (vKind < 1.5) {
    int bi = int(vBell + 0.5);
    float frill = 0.68 + 0.32 * sin(vS * 22.0 + vPhase + uTime * 0.5);
    float taper = (1.0 - smoothstep(0.55, 1.0, vS)) * (0.35 + 0.65 * sin(PI * min(vS * 1.6, 1.0)));
    vec3 rest = vec3(0.008, 0.02, 0.038);
    vec3 sus3 = (rest + uBellCol[bi].rgb * 0.45 + uArtCol.rgb * uBellAnim[bi].z * 0.4) * (body + skirt + halo) * frill * taper;
    float lu = dot(sus3, vec3(0.2126, 0.7152, 0.0722)) * 1.5;
    sus3 *= min(1.0, 0.85 / max(lu, 1e-4));
    emit = sus3 + uBellFlash[bi].rgb * 0.05 * (body + skirt + halo) * frill * taper;
  } else {
    // the current: light travels along it from the bass toward the solo
    float flow = ppow(0.5 + 0.5 * cos(vS * 34.0 - uTime * uDanceCol.w + vPhase), 5.0);
    float ends = sin(PI * vS) * 0.6 + 0.4;
    emit = uDanceCol.rgb * uDance2.w * (0.35 + 0.6 * flow) * ends * (body + skirt * 1.4 + halo);
    float lu = dot(emit, vec3(0.2126, 0.7152, 0.0722));
    emit *= min(1.0, 0.4 / max(lu, 1e-4));             // two strands cross: each stays well under half the bloom line
  }
  gl_FragColor = vec4(emit, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

const BELL_VS = /* glsl */ `
${COMMON}
attribute float aBell;
attribute vec2 aBellShape;   // height factor, margin flare
varying vec3 vPosW, vNrmW;
varying float vRho, vPhi, vH, vB;
void main() {
  int bi = int(aBell + 0.5);
  vec4 bp = uBellPos[bi], ba = uBellAnim[bi];
  float rho = length(position.xz);
  float phi = atan(position.z, position.x);
  // a swim stroke: the margin squeezes in and the bell rises; the breath is the same stroke, slow and shallow; the damper
  // pedal lets it relax open; the artifact inflates it a little
  float squeeze = ba.x * ${K.PUMP_CONTRACT.toFixed(3)} + ba.y;
  float c = 1.0 - squeeze * (0.3 + 0.7 * rho * rho) + 0.055 * ba.w * rho;
  c *= (1.0 + aBellShape.y * smoothstep(0.7, 1.0, rho)) * (1.0 + 0.2 * ba.z);
  float lapp = 0.028 * sin(phi * 12.0 + float(bi)) * smoothstep(0.55, 1.0, rho)     // a soft scalloped margin
             + 0.062 * sin(phi * 3.0 + float(bi) * 1.7) * rho * rho;                // and a lopsided, living dome
  float swim = 0.011 * sin(rho * 3.0 - uTime * 0.7 + float(bi) * 2.1);              // the bell is never quite still
  vec3 p = vec3(position.x * c,
                position.y * aBellShape.x * (1.0 + 0.13 * ba.x + 0.8 * ba.y + 0.1 * ba.z) + lapp + swim - 0.05 * ba.w * rho * rho,
                position.z * c);
  vec3 Pw = (modelMatrix * vec4(bp.xyz + p * bp.w, 1.0)).xyz;
  vPosW = Pw;
  vNrmW = normalize(mat3(modelMatrix) * normal);
  vRho = rho; vPhi = phi; vH = position.y; vB = aBell;
  gl_Position = projectionMatrix * viewMatrix * vec4(Pw, 1.0);
}`;

const BELL_FS = /* glsl */ `
${COMMON}
varying vec3 vPosW, vNrmW;
varying float vRho, vPhi, vH, vB;
void main() {
  int bi = int(vB + 0.5);
  vec3 Nn = normalize(vNrmW);
  vec3 V = normalize(cameraPosition - vPosW);
  float fres = clamp(1.0 - abs(dot(Nn, V)), 0.0, 1.0);
  float rim = fres * fres * fres * (0.8 + 0.2 * fres);   // ~ fres^3.2: jelly is water, only the grazing angles hold light
  float sheen = fres * (0.5 + 0.5 * fres) * 0.28;         // ~ fres^1.4
  // four radial canals, thin and soft, fading before the margin (~ |cos 2 phi|^90)
  float canals = lobe(abs(cos(vPhi * 2.0)), 90.0) * smoothstep(0.15, 0.5, vRho) * (1.0 - smoothstep(0.82, 0.98, vRho));
  float ring = exp(-sq((vRho - 0.9) / 0.045)) * 0.8;     // the ring canal at the margin
  float margin = smoothstep(0.93, 1.0, vRho);
  // rhopalia: the little sense bulbs around the rim, where the tentacles hang from (~ (0.5 + 0.5 cos 24 phi)^14)
  float bulbs = lobe(cos(vPhi * 24.0), 7.0) * exp(-sq((vRho - 0.99) / 0.05));
  vec2 q = vec2(cos(vPhi), sin(vPhi)) * vRho;
  float gut = 0.0;                                   // the four-leaf gonads of a moon jelly, low and soft
  for (int k = 0; k < 4; k++) {
    float an = 0.785398 + float(k) * 1.570796;
    vec2 cc = vec2(cos(an), sin(an)) * 0.27;
    float dd = length(q - cc);
    gut += exp(-sq((dd - 0.115) / 0.05)) * smoothstep(-0.3, 0.7, dot(normalize(q - cc + 1e-5), -normalize(cc)));
  }
  gut *= smoothstep(0.06, 0.28, vH) * 0.8;
  // the artifact: a luminous mass growing inside the bell over the chord's root, its lobes seeded per chord
  float art = uBellAnim[bi].z;
  float lobes = 1.0 + 0.36 * sin(vPhi * (3.0 + floor(uArtCol.w * 4.0)) + uArtCol.w * 6.2832);
  float artMass = exp(-sq((vRho - 0.36 * art * lobes) / (0.2 + 0.16 * art))) * smoothstep(0.0, 0.22, vH)
                * art * (0.9 + 0.35 * sin(uTime * 2.6 + vRho * 9.0 + uArtCol.w * 6.0))
                + exp(-vRho * vRho * 2.5) * art * art * 0.6;                     // and a heart that fills the dome as it ripens
  vec3 glow = uBellCol[bi].rgb;
  vec3 flash = uBellFlash[bi].rgb;
  vec3 rest = vec3(0.011, 0.028, 0.055);
  vec3 sus3 = rest * (rim * 1.3 + sheen * 0.8 + canals * 0.4 + ring * 0.6 + margin * 0.6 + gut * 0.25 + bulbs * 1.3 + 0.035)
            + glow * (0.05 + rim * 0.75 + sheen * 0.5 + canals * 0.65 + ring * 0.75 + margin * 0.55 + gut * 0.95 + bulbs * 1.3)
            + uArtCol.rgb * (artMass * (1.0 + 0.6 * gut) + art * (rim * 0.25 + sheen * 0.2));
  float lu = dot(sus3, vec3(0.2126, 0.7152, 0.0722)) * 1.5;
  sus3 *= min(1.0, 0.85 / max(lu, 1e-4));              // sustained light never crosses the bloom line (0.57 linear = 0.85 on screen)
  vec3 emit = sus3 + flash * (0.05 + rim * 0.4 + ring * 0.6 + gut * 0.5 + bulbs * 0.5);
  gl_FragColor = vec4(emit, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

const TIP_VS = /* glsl */ `
${COMMON}
attribute vec4 aTipInfo;   // x, y, z, note index
varying vec2 vUv;
varying float vGrow, vRing;
varying vec4 vN0, vN1, vN5;
void main() {
  int ni = int(aTipInfo.w + 0.5);
  vN0 = noteRow(ni, 0); vN1 = noteRow(ni, 1); vN5 = noteRow(ni, 5);
  float reg = vN5.w, kick = vN5.y, ring = vN5.x, vel = vN5.z;
  float base = mix(0.36, 0.2, reg);
  float grow = 1.0 + 0.5 * kick + 3.2 * ring * vel * vel;
  vec4 mv = modelViewMatrix * vec4(aTipInfo.xyz, 1.0);
  mv.xy += position.xy * base * grow;
  vUv = position.xy; vGrow = grow; vRing = ring;
  gl_Position = projectionMatrix * mv;
}`;

const TIP_FS = /* glsl */ `
${COMMON}
varying vec2 vUv;
varying float vGrow, vRing;
varying vec4 vN0, vN1, vN5;
void main() {
  float r = length(vUv);
  if (r > 1.0) discard;
  float rb = r * vGrow;                                   // the bead keeps its size while the quad grows
  float vel = vN5.z;
  float bead = exp(-rb * rb * 9.0);
  float halo = exp(-rb * 3.0) * 0.3;
  vec3 col = vN1.rgb;
  float spark = vN0.y * 1.8;                              // the hammer: the strike flash, at the key
  float shock = vRing > 0.0
    ? exp(-sq((r - vRing) / (0.1 + 0.25 * vRing))) * (1.0 - vRing) * (1.0 - vRing) * vel * vel * 1.3 : 0.0;
  vec3 rest = (vec3(0.016, 0.04, 0.07) + col * 0.04) * bead;
  vec3 sus3 = rest + col * vN0.x * 0.7 * (bead + halo);
  float lu = dot(sus3, vec3(0.2126, 0.7152, 0.0722)) * 1.5;
  sus3 *= min(1.0, 0.85 / max(lu, 1e-4));
  vec3 emit = sus3 + col * (spark * (bead + halo * 0.6) + shock);
  gl_FragColor = vec4(emit * (1.0 - smoothstep(0.88, 1.0, r)), 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

const POINTS_VS = /* glsl */ `
${COMMON}
attribute vec4 aP;   // position; snow: rank, plankton: birth
attribute vec4 aV;   // velocity, life (< 0: marine snow)
attribute vec4 aC;   // rgb, size
attribute float aN;  // the note this sparkle belongs to (< 0: none)
varying vec3 vCol;
varying float vA;
// a cheap curl of the water: divergence-free enough to read as eddies, no texture, no CPU
vec3 curl(vec3 p, float t) {
  return vec3(sin(p.y * 0.31 + t * 0.17) * cos(p.z * 0.23 - t * 0.11),
              sin(p.z * 0.27 + t * 0.13) * cos(p.x * 0.19 + t * 0.07) * 0.5,
              sin(p.x * 0.21 - t * 0.09) * cos(p.y * 0.29 + t * 0.15));
}
void main() {
  vec3 p;
  float a = 0.0;
  if (aV.w < 0.0) {
    // marine snow: drifts through the water column behind the keys, thicker as the harmony grows lush, lit by the bells
    float show = smoothstep(aP.w - 0.08, aP.w + 0.02, uMood.z);
    if (show < 0.003) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
    vec3 box = vec3(76.0, 34.0, 26.0);
    vec3 lo = vec3(-38.0, -4.0, -30.0);
    float drift = 1.0 + 1.5 * uMood.y;
    p = lo + mod(aP.xyz - lo + aV.xyz * uTime * drift + curl(aP.xyz, uTime * drift) * 0.9, box);
    vec3 lit = vec3(0.0);
    for (int b = 0; b < 7; b++) {
      vec3 dd = p - uBellPos[b].xyz;
      float r2 = uBellPos[b].w * uBellPos[b].w;
      lit += (uBellCol[b].rgb * 1.6 + uBellFlash[b].rgb * 0.5 + uArtCol.rgb * uBellAnim[b].z * 0.8) * exp(-dot(dd, dd) / (r2 * 3.2));
    }
    vCol = (vec3(0.05, 0.085, 0.13) + uWater * 1.6) * (0.55 + 0.45 * sin(uTime * 0.7 + aP.w * 13.0)) + lit * 1.4;
    a = show;
  } else {
    float age = uTime - aP.w;
    if (age < 0.0 || age > aV.w) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
    float k = 1.4;
    p = aP.xyz + aV.xyz * (1.0 - exp(-age * k)) / k
        + vec3(sin(age * 1.3 + aP.w * 7.0) * 0.12, age * 0.16, cos(age * 1.1 + aP.w * 5.0) * 0.1);
    float life = age / aV.w;
    float birth = exp(-age / 0.12);
    float tw = 0.62 + 0.38 * sin(age * 7.0 + aP.w * 31.0);
    a = (1.0 - smoothstep(0.3, 1.0, life)) * tw;
    if (aN >= 0.0) a *= noteRow(int(aN + 0.5), 1).w;   // a note's sparkles die with its sound
    vCol = aC.rgb * (0.8 + 1.4 * birth);
  }
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  float pxPerUnit = uRes.y * projectionMatrix[1][1] * 0.5 / max(-mv.z, 0.1);
  float size = aC.w * pxPerUnit;
  vA = a * min(1.0, size / 1.6);
  gl_PointSize = max(size, 1.6);
  gl_Position = projectionMatrix * mv;
}`;

const POINTS_FS = /* glsl */ `
precision highp float;
varying vec3 vCol;
varying float vA;
void main() {
  vec2 q = gl_PointCoord * 2.0 - 1.0;
  float r2 = dot(q, q);
  if (r2 > 1.0) discard;
  float g = exp(-r2 * 3.5);
  gl_FragColor = vec4(vCol * g * vA, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

const WATER_VS = /* glsl */ `
varying vec2 vUv;
varying float vY;
void main() {
  vUv = uv;
  vec4 w = modelMatrix * vec4(position, 1.0);
  vY = w.y;
  gl_Position = projectionMatrix * viewMatrix * w;
}`;
const WATER_FS = /* glsl */ `
${COMMON}
varying vec2 vUv;
varying float vY;
void main() {
  float y = vUv.y;
  // Everything fades out well above the sea bed, so the water never draws an edge along the floor's horizon.
  float foot = smoothstep(0.0, 0.3, y) * smoothstep(2.0, 20.0, vY);
  float lush = uMat.x;
  vec3 c = mix(vec3(0.0, 0.0015, 0.005), uWater * (1.0 + 1.4 * lush), smoothstep(0.25, 1.0, y)) * foot;
  float x = vUv.x * 9.0 + (1.0 - y) * 2.2;
  float sh = ppow(0.5 + 0.5 * sin(x * 1.15 + uTime * 0.05), 6.0) * 0.7
           + ppow(0.5 + 0.5 * sin(x * 2.3 - uTime * 0.037 + 1.3), 12.0) * 0.6
           + ppow(0.5 + 0.5 * sin(x * 0.61 + uTime * 0.021 + 3.1), 4.0) * 0.35;
  c += uWater * (0.35 + 1.6 * lush) * sh * smoothstep(0.3, 1.0, y) * foot;
  gl_FragColor = vec4(c, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

// A soft pool of light on the sea bed under the school, so the floor is water and not a black shelf.
const BED_VS = /* glsl */ `
varying vec2 vXZ;
void main() {
  vec4 w = modelMatrix * vec4(position, 1.0);
  vXZ = w.xz;
  gl_Position = projectionMatrix * viewMatrix * w;
}`;
const BED_FS = /* glsl */ `
${COMMON}
uniform vec3 uBedTint;
varying vec2 vXZ;
void main() {
  float d = length(vec2(vXZ.x / 52.0, (vXZ.y + 6.0) / 34.0));
  float fall = exp(-d * d * 1.3);
  float ripple = 0.75 + 0.25 * sin(vXZ.x * 0.16 + uTime * 0.25) * sin(vXZ.y * 0.19 - uTime * 0.17);
  vec3 c = (vec3(0.005, 0.014, 0.028) + uWater * 0.25 + uBedTint * 1.5) * fall * ripple;
  gl_FragColor = vec4(c, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

// ------------------------------------------------------------------------------------------------ geometry --
// Built by hand from core buffers (no addons, and no LatheGeometry: a stub THREE can then run create() in a node test).
function ribbonGeometry(THREE) {
  const verts = new Float32Array((SEG + 1) * 2 * 3);
  const idx = new Uint16Array(SEG * 6);
  for (let k = 0; k <= SEG; k++) {
    const s = k / SEG;
    verts[k * 6] = s; verts[k * 6 + 1] = -1; verts[k * 6 + 2] = 0;
    verts[k * 6 + 3] = s; verts[k * 6 + 4] = 1; verts[k * 6 + 5] = 0;
    if (k < SEG) { const a = k * 2, o = k * 6; idx[o] = a; idx[o + 1] = a + 1; idx[o + 2] = a + 2; idx[o + 3] = a + 1; idx[o + 4] = a + 3; idx[o + 5] = a + 2; }
  }
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(verts, 3));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  return g;
}
// A low, wide medusa: a dome that slackens into a flared skirt, revolved about y (radius 1, height 0.5).
function bellGeometry(THREE) {
  const prof = [];
  for (let k = 0; k <= 26; k++) {
    const th = (k / 26) * (Math.PI / 2);
    prof.push([Math.max(1e-3, Math.pow(Math.sin(th), 0.88)), 0.5 * Math.pow(Math.cos(th), 1.7)]);
  }
  prof.push([1.02, -0.055], [1.005, -0.12], [0.93, -0.165]);
  const P = prof.length, R = 56;
  const pos = new Float32Array((R + 1) * P * 3), nor = new Float32Array((R + 1) * P * 3);
  const idx = new Uint16Array(R * (P - 1) * 6);
  for (let i = 0; i <= R; i++) {
    const phi = (i / R) * TAU, c = Math.cos(phi), s = Math.sin(phi);
    for (let j = 0; j < P; j++) {
      const [r, y] = prof[j];
      const a = prof[Math.max(0, j - 1)], b = prof[Math.min(P - 1, j + 1)];
      let nr = -(b[1] - a[1]), ny = b[0] - a[0];
      const l = Math.hypot(nr, ny) || 1;
      nr /= l; ny /= l;
      const o = (i * P + j) * 3;
      pos[o] = r * c; pos[o + 1] = y; pos[o + 2] = r * s;
      nor[o] = nr * c; nor[o + 1] = ny; nor[o + 2] = nr * s;
    }
  }
  let t = 0;
  for (let i = 0; i < R; i++) for (let j = 0; j < P - 1; j++) {
    const a = i * P + j, b = (i + 1) * P + j;
    idx[t++] = a; idx[t++] = b; idx[t++] = a + 1; idx[t++] = b; idx[t++] = b + 1; idx[t++] = a + 1;
  }
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  return g;
}
function quadGeometry(THREE, instanced, w = 1, h = 1) {
  const g = instanced ? new THREE.InstancedBufferGeometry() : new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array([-w, -h, 0, w, -h, 0, w, h, 0, -w, h, 0]), 3));
  g.setAttribute("uv", new THREE.BufferAttribute(new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]), 2));
  g.setIndex(new THREE.BufferAttribute(new Uint16Array([0, 1, 2, 0, 2, 3]), 1));
  return g;
}

// ------------------------------------------------------------------------------------------------ module --
const KEY_STYLE = Object.freeze({ whiteColor: 0xdde6ee, blackColor: 0x06090d });
const HINTS = Object.freeze({ hideHostBody: true, floorY: K.FLOOR_Y });

const ID = "light-vandor-abyssal";

function create(ctx) {
  const THREE = ctx.THREE;
  const keyX = ctx.keyX || ((m) => (m - 21 - 43.5) * 52 / 88);
  const isBlack = ctx.isBlack || ((m) => [1, 3, 6, 8, 10].includes(((m % 12) + 12) % 12));
  const noteColor = ctx.noteColor || ((m, vel, target) => target.setHSL((((m % 12) * 7) % 12) / 12, 0.9, 0.5));
  const group = new THREE.Group();
  group.name = "instrument:light-vandor-abyssal";
  const geos = [], mats = [], texs = [];
  const G = (g) => { geos.push(g); return g; };
  const M = (m) => { mats.push(m); return m; };
  const rand = mulberry32(0xab155a1);
  const feel = createHarmonyFeel();
  const moment = createMoment();

  // ---- layout ----
  const bells = [];
  for (let b = 0; b < BELLS; b++) {
    const x0 = keyX(BELL_FIRST[b]), x1 = keyX(BELL_LAST[b]);
    bells.push({
      x0, x1, cx: (x0 + x1) / 2,
      cy0: 12.4 + 8.4 * Math.exp(-0.42 * b), cy: 0,
      cz: BELL_Z[b],
      r: lerp(3.5, 2.0, b / 6) * BELL_JITTER[b],
      hf: 0.86 + 0.3 * ((b * 5) % 7) / 6,       // no two of the school the same silhouette
      flare: -0.04 + 0.1 * ((b * 3) % 5) / 4,
      pump: 0, kick: 0, breathPhase: rand() * TAU, breath: 0, art: 0,
    });
  }
  const REG = new Float32Array(N), BELL = new Uint8Array(N), PHASE = new Float32Array(N);
  const ANCH = new Float32Array(N * 3), TIPS = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const m = FIRST + i, b = bellOf(m), B = bells[b];
    REG[i] = pitchOf(m); BELL[i] = b; PHASE[i] = rand() * TAU;
    const u = (keyX(m) - B.x0) / Math.max(B.x1 - B.x0, 1e-3);
    const ax = (u - 0.5) * 2 * 0.9;
    const dz = Math.sqrt(Math.max(0, 0.81 - ax * ax)) * 0.62;
    ANCH[i * 3] = ax; ANCH[i * 3 + 1] = -0.04; ANCH[i * 3 + 2] = isBlack(m) ? -dz : dz;
    TIPS[i * 3] = keyX(m); TIPS[i * 3 + 1] = TIP_Y + (isBlack(m) ? 0.12 : 0); TIPS[i * 3 + 2] = isBlack(m) ? TIP_Z_BLACK : TIP_Z;
  }

  // ---- per-note state (typed, never reallocated) ----
  const bFloor = new Float32Array(N), bPrompt = new Float32Array(N), bAfter = new Float32Array(N), body = new Float32Array(N);
  const flash = new Float32Array(N), vibGate = new Float32Array(N), dampT = new Float32Array(N), dampW = new Float32Array(N);
  const strikeAt = new Float64Array(N).fill(-1e9), VEL = new Float32Array(N), COL = new Float32Array(N * 3);
  const alive = new Uint8Array(N), held = new Uint8Array(N), seenStrike = new Uint32Array(N);
  const lastNote = new Float64Array(N).fill(-Infinity);     // the strike ring's high-water mark per key
  const heldMix = new Float32Array(N).fill(1), breathPhase = new Float32Array(N);
  const tauPrompt = new Float32Array(N), tauAfter = new Float32Array(N), envMax = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const m = FIRST + i;
    tauPrompt[i] = overPitch(m, K.TAU_PROMPT_BASS, K.TAU_PROMPT_TREBLE);
    tauAfter[i] = overPitch(m, K.TAU_AFTER_BASS, K.TAU_AFTER_TREBLE);
    envMax[i] = overPitch(m, K.ENV_BASS, K.ENV_TREBLE);
    breathPhase[i] = rand() * TAU;
  }
  const tmpC = new THREE.Color();

  const texData = new Float32Array(N * ROWS * 4);
  const noteTex = new THREE.DataTexture(texData, N, ROWS, THREE.RGBAFormat, THREE.FloatType);
  texs.push(noteTex);
  noteTex.minFilter = noteTex.magFilter = THREE.NearestFilter;
  noteTex.generateMipmaps = false;
  for (let i = 0; i < N; i++) {                      // the static rows: anchors, tips, phases, registers
    const o3 = (3 * N + i) * 4, o4 = (4 * N + i) * 4, o5 = (5 * N + i) * 4;
    texData[o3] = ANCH[i * 3]; texData[o3 + 1] = ANCH[i * 3 + 1]; texData[o3 + 2] = ANCH[i * 3 + 2]; texData[o3 + 3] = BELL[i];
    texData[o4] = TIPS[i * 3]; texData[o4 + 1] = TIPS[i * 3 + 1]; texData[o4 + 2] = TIPS[i * 3 + 2]; texData[o4 + 3] = PHASE[i];
    texData[o5 + 3] = REG[i];
  }
  noteTex.needsUpdate = true;

  const V4 = () => { const a = []; for (let b = 0; b < BELLS; b++) a.push(new THREE.Vector4()); return a; };
  const uniforms = {
    uNotes: { value: noteTex }, uTime: { value: 0 }, uRes: { value: new THREE.Vector2(1920, 1080) },
    uBellPos: { value: V4() }, uBellAnim: { value: V4() }, uBellCol: { value: V4() }, uBellFlash: { value: V4() },
    uArtCol: { value: new THREE.Vector4(0, 0, 0, 0) },
    uMat: { value: new THREE.Vector4(0, 0, 1, 0.5) }, uMood: { value: new THREE.Vector4(0, 0, K.SNOW_MIN, 0) },
    uDance: { value: new THREE.Vector4(0, 0, 1, 0) }, uDance2: { value: new THREE.Vector4(0, 0, 0, 0) },
    uDanceCol: { value: new THREE.Vector4(0.5, 0.9, 0.85, 4) },
    uWater: { value: new THREE.Vector3(0.004, 0.017, 0.038) }, uBedTint: { value: new THREE.Vector3() },
  };
  const material = (vs, fs, extra) => M(new THREE.ShaderMaterial({
    uniforms, vertexShader: vs, fragmentShader: fs, transparent: true, depthWrite: false, depthTest: true,
    blending: THREE.AdditiveBlending, fog: false, toneMapped: true, ...extra,
  }));
  const meshes = [];
  const place = (mesh, order, name) => { mesh.renderOrder = order; mesh.name = name; group.add(mesh); meshes.push(mesh); return mesh; };

  // ---- tentacles + oral arms + the dance strands: one instanced ribbon ----
  {
    const g = G(ribbonGeometry(THREE));
    const count = N + BELLS * ARMS_PER_BELL + STRANDS;
    const info = new Float32Array(count * 4), anchor = new Float32Array(count * 3);
    const tip = new Float32Array(count * 3), shape = new Float32Array(count * 4);
    for (let i = 0; i < N; i++) {
      const reg = REG[i];
      info[i * 4] = i; info[i * 4 + 1] = BELL[i]; info[i * 4 + 2] = 0; info[i * 4 + 3] = PHASE[i];
      anchor[i * 3] = ANCH[i * 3]; anchor[i * 3 + 1] = ANCH[i * 3 + 1]; anchor[i * 3 + 2] = ANCH[i * 3 + 2];
      tip[i * 3] = TIPS[i * 3]; tip[i * 3 + 1] = TIPS[i * 3 + 1]; tip[i * 3 + 2] = TIPS[i * 3 + 2];
      shape[i * 4] = lerp(K.CORE_BASS, K.CORE_TREBLE, Math.pow(reg, 0.75));
      shape[i * 4 + 1] = lerp(K.SWAY_BASS, K.SWAY_TREBLE, Math.pow(reg, 0.6));
      shape[i * 4 + 2] = 1; shape[i * 4 + 3] = reg;
    }
    let j = N;
    for (let b = 0; b < BELLS; b++) {
      const B = bells[b];
      for (let k = 0; k < ARMS_PER_BELL; k++, j++) {
        const an = TAU * (k + 0.5) / ARMS_PER_BELL + b * 0.4;
        const ar = 0.14 + 0.12 * rand();
        const len = B.r * (1.3 + 0.7 * rand());
        info[j * 4] = 0; info[j * 4 + 1] = b; info[j * 4 + 2] = 1; info[j * 4 + 3] = rand() * TAU;
        anchor[j * 3] = Math.cos(an) * ar; anchor[j * 3 + 1] = 0.02; anchor[j * 3 + 2] = Math.sin(an) * ar;
        tip[j * 3] = Math.cos(an) * B.r * (0.25 + 0.35 * rand()); tip[j * 3 + 1] = -len; tip[j * 3 + 2] = Math.sin(an) * B.r * 0.3;
        shape[j * 4] = B.r * 0.05; shape[j * 4 + 1] = 0.26; shape[j * 4 + 2] = 0; shape[j * 4 + 3] = b / 6;
      }
    }
    for (let k = 0; k < STRANDS; k++, j++) {
      info[j * 4] = k; info[j * 4 + 1] = 0; info[j * 4 + 2] = 2; info[j * 4 + 3] = k * 2.1;
      shape[j * 4] = 0.045; shape[j * 4 + 1] = 0; shape[j * 4 + 2] = 0; shape[j * 4 + 3] = 0.5;
    }
    g.setAttribute("aInfo", new THREE.InstancedBufferAttribute(info, 4));
    g.setAttribute("aAnchor", new THREE.InstancedBufferAttribute(anchor, 3));
    g.setAttribute("aTip", new THREE.InstancedBufferAttribute(tip, 3));
    g.setAttribute("aShape", new THREE.InstancedBufferAttribute(shape, 4));
    g.instanceCount = count;
    const mesh = place(new THREE.Mesh(g, material(TENTACLE_VS, TENTACLE_FS, { side: THREE.DoubleSide })), 2, "abyssal-tentacles");
    mesh.frustumCulled = false;
    // the pass actually drawing (its viewport, not the canvas) sizes the pixel floors of every ribbon and point
    const vp = new THREE.Vector4();
    mesh.onBeforeRender = (renderer) => { renderer.getCurrentViewport(vp); uniforms.uRes.value.set(vp.z, vp.w); };
  }

  // ---- bells ----
  {
    const g = G(bellGeometry(THREE));
    const ab = new Float32Array(BELLS), ash = new Float32Array(BELLS * 2);
    for (let b = 0; b < BELLS; b++) { ab[b] = b; ash[b * 2] = bells[b].hf; ash[b * 2 + 1] = bells[b].flare; }
    g.setAttribute("aBell", new THREE.InstancedBufferAttribute(ab, 1));
    g.setAttribute("aBellShape", new THREE.InstancedBufferAttribute(ash, 2));
    g.instanceCount = BELLS;
    const mesh = place(new THREE.Mesh(g, material(BELL_VS, BELL_FS, { side: THREE.DoubleSide })), 3, "abyssal-bells");
    mesh.frustumCulled = false;
  }

  // ---- photophore beads at the keys ----
  {
    const g = G(quadGeometry(THREE, true));
    const ti = new Float32Array(N * 4);
    for (let i = 0; i < N; i++) { ti[i * 4] = TIPS[i * 3]; ti[i * 4 + 1] = TIPS[i * 3 + 1]; ti[i * 4 + 2] = TIPS[i * 3 + 2]; ti[i * 4 + 3] = i; }
    g.setAttribute("aTipInfo", new THREE.InstancedBufferAttribute(ti, 4));
    g.instanceCount = N;
    const mesh = place(new THREE.Mesh(g, material(TIP_VS, TIP_FS, {})), 4, "abyssal-beads");
    mesh.frustumCulled = false;
  }

  // ---- marine snow + plankton: one Points ----
  const POOL = SNOW + PLANKTON;
  const aP = new Float32Array(POOL * 4), aV = new Float32Array(POOL * 4), aC = new Float32Array(POOL * 4), aN = new Float32Array(POOL);
  let ring = 0, pointsDirty = false;
  const pointsGeo = G(new THREE.BufferGeometry());
  {
    for (let j = 0; j < SNOW; j++) {
      aP[j * 4] = -38 + rand() * 76; aP[j * 4 + 1] = -4 + rand() * 34; aP[j * 4 + 2] = -30 + rand() * 26; aP[j * 4 + 3] = rand();  // w = rank
      aV[j * 4] = (rand() - 0.5) * 0.12; aV[j * 4 + 1] = 0.02 + rand() * 0.06; aV[j * 4 + 2] = (rand() - 0.5) * 0.05; aV[j * 4 + 3] = -1;
      aC[j * 4 + 3] = 0.08 + rand() * 0.14;
      aN[j] = -1;
    }
    for (let j = SNOW; j < POOL; j++) { aP[j * 4 + 1] = -999; aP[j * 4 + 3] = -1000; aV[j * 4 + 3] = 0.001; aN[j] = -1; }
    pointsGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(POOL * 3), 3));
    pointsGeo.setAttribute("aP", new THREE.BufferAttribute(aP, 4).setUsage(THREE.DynamicDrawUsage));
    pointsGeo.setAttribute("aV", new THREE.BufferAttribute(aV, 4).setUsage(THREE.DynamicDrawUsage));
    pointsGeo.setAttribute("aC", new THREE.BufferAttribute(aC, 4).setUsage(THREE.DynamicDrawUsage));
    pointsGeo.setAttribute("aN", new THREE.BufferAttribute(aN, 1).setUsage(THREE.DynamicDrawUsage));
    const pts = place(new THREE.Points(pointsGeo, material(POINTS_VS, POINTS_FS, {})), 5, "abyssal-plankton");
    pts.frustumCulled = false;
  }

  // ---- the water column and the sea bed ----
  {
    const water = place(new THREE.Mesh(G(quadGeometry(THREE, false, 160, 75)), material(WATER_VS, WATER_FS, {})), 1, "abyssal-water");
    water.position.set(0, 46, -70);
    water.frustumCulled = false;
    const bed = place(new THREE.Mesh(G(quadGeometry(THREE, false, 95, 60)), material(BED_VS, BED_FS, {})), 1, "abyssal-bed");
    bed.rotation.x = -Math.PI / 2;
    bed.position.set(0, K.FLOOR_Y + 0.05, -14);
    bed.frustumCulled = false;
  }

  // CPU copy of a tentacle's curve at rest (for shedding plankton along it)
  const cp = new Float32Array(3);
  const curvePoint = (i, s) => {
    const B = bells[BELL[i]];
    const p0x = B.cx + ANCH[i * 3] * B.r, p0y = B.cy + ANCH[i * 3 + 1] * B.r, p0z = B.cz + ANCH[i * 3 + 2] * B.r;
    const p3x = TIPS[i * 3], p3y = TIPS[i * 3 + 1], p3z = TIPS[i * 3 + 2];
    const L = p0y - p3y;
    const p1x = p0x + ANCH[i * 3] * B.r * 0.22, p1y = p0y - 0.32 * L, p1z = p0z + ANCH[i * 3 + 2] * B.r * 0.3;
    const p2x = p3x, p2y = p3y + 0.4 * L, p2z = p3z - 0.35;
    const u = 1 - s, a = u * u * u, b = 3 * u * u * s, c = 3 * u * s * s, d = s * s * s;
    cp[0] = a * p0x + b * p1x + c * p2x + d * p3x;
    cp[1] = a * p0y + b * p1y + c * p2y + d * p3y;
    cp[2] = a * p0z + b * p1z + c * p2z + d * p3z;
  };
  const spawn = (x, y, z, birth, vx, vy, vz, life, r, g, b, size, note) => {
    const j = SNOW + ring;
    ring = (ring + 1) % PLANKTON;
    aP[j * 4] = x; aP[j * 4 + 1] = y; aP[j * 4 + 2] = z; aP[j * 4 + 3] = birth;
    aV[j * 4] = vx; aV[j * 4 + 1] = vy; aV[j * 4 + 2] = vz; aV[j * 4 + 3] = life;
    aC[j * 4] = r; aC[j * 4 + 1] = g; aC[j * 4 + 2] = b; aC[j * 4 + 3] = size;
    aN[j] = note;
    pointsDirty = true;
  };

  // A strike, age seconds ago (age > 0 seeds a sound already ringing when the instrument was mounted, or a strike the
  // ring reports late). The envelope is analytic, so it is simply advanced. A strike never dips the light to dark first:
  // whatever is still showing above the new peak is folded into the prompt term and decays from there.
  const strike = (i, vel, t0, age) => {
    const v = clamp(vel / 127, 0, 1);
    const peak = Math.pow(v, K.PEAK_EXP);
    const fl = peak * lerp(K.FLOOR_LO, K.FLOOR_HI, v);
    const above = peak - fl;
    const carry = Math.max(0, body[i] - peak);
    bFloor[i] = fl;
    bPrompt[i] = (above * (1 - K.AFTER_SHARE) + carry) * Math.exp(-age / tauPrompt[i]);
    bAfter[i] = above * K.AFTER_SHARE * Math.exp(-age / tauAfter[i]);
    body[i] = bFloor[i] + bPrompt[i] + bAfter[i];
    flash[i] = Math.max(flash[i], Math.pow(v, K.FLASH_EXP) * Math.exp(-age / K.TAU_FLASH));
    vibGate[i] = 1;
    dampT[i] = 0;
    strikeAt[i] = t0; VEL[i] = v;
    noteColor(FIRST + i, vel, tmpC);
    COL[i * 3] = tmpC.r; COL[i * 3 + 1] = tmpC.g; COL[i * 3 + 2] = tmpC.b;
    const B = bells[BELL[i]];
    B.kick = Math.max(B.kick, Math.pow(v, 1.4) * Math.exp(-age / K.PUMP_TAU_DECAY));
    if (age > 0.25) return;                            // a late or seeded strike sheds nothing
    const n = Math.round(K.SPARKS_MIN + K.SPARKS_VEL * Math.pow(v, 1.5));
    const size = lerp(0.2, 0.1, REG[i]), travel = travelOf(v), spread = 0.25 + 0.6 * v;
    for (let k = 0; k < n; k++) {
      const s = 0.06 + 0.9 * rand();
      curvePoint(i, s);
      spawn(cp[0] + (rand() - 0.5) * 0.3, cp[1], cp[2] + (rand() - 0.5) * 0.3, t0 + travel * s + rand() * 0.04,
            (rand() - 0.5) * 1.4 * spread, (0.1 + rand() * 0.5) * spread, (rand() - 0.5) * 1.0 * spread, 1.4 + rand() * 2.4,
            COL[i * 3], COL[i * 3 + 1], COL[i * 3 + 2], size * (0.6 + 0.8 * rand()), i);
    }
  };
  // the artifact's release: the mass inside the bell bursts into a cloud of plankton
  const burst = (b, strength, t) => {
    const B = bells[b], n = Math.round(50 + 190 * strength);
    const ac = uniforms.uArtCol.value;
    const L = luma(ac.x, ac.y, ac.z), k = L > 1e-4 ? 0.5 / L : 0;
    for (let q = 0; q < n; q++) {
      const th = rand() * TAU, ph = Math.acos(2 * rand() - 1), sp = (3.0 + 6.0 * rand()) * (0.5 + 0.5 * strength);
      const dx = Math.sin(ph) * Math.cos(th), dy = Math.cos(ph) * 0.7 - 0.25, dz = Math.sin(ph) * Math.sin(th);
      spawn(B.cx + dx * B.r * 0.3, B.cy + dy * B.r * 0.2, B.cz + dz * B.r * 0.3, t + rand() * 0.12,
            dx * sp, dy * sp, dz * sp, 1.8 + rand() * 2.4, ac.x * k, ac.y * k, ac.z * k, lerp(0.26, 0.12, b / 6) * (0.6 + 0.9 * rand()), -1);
    }
    B.kick = Math.max(B.kick, 0.6 + 0.4 * strength);
  };

  // ---- smoothed scene state ----
  let active = true, seeded = false, pedalAmt = 0, snow = K.SNOW_MIN, waterR = 0.004, waterG = 0.017, waterB = 0.038;
  let danceOn = 0, danceBass = 0, danceSolo = 0, braid = 0, danceStretch = 0, dancePull = 0, artLevel = 0, artBell = 3;
  let portrait = false;
  let dcR = 0.5, dcG = 0.9, dcB = 0.85;
  const visit = (e, m) => {                          // one state.sounding entry (forEach: no iterator, no destructuring)
    const i = m - FIRST;
    if (i < 0 || i >= N || !e) return;
    alive[i] = 1;
    held[i] = e.held ? 1 : 0;
    if (e.strike !== seenStrike[i]) {
      seenStrike[i] = e.strike;
      strike(i, e.vel, e.t0, seeded ? 0 : Math.max(0, visit.t - e.t0));
      if (e.t0 > lastNote[i]) lastNote[i] = e.t0;    // the ring reports the same strike: do not count it twice
    }
  };
  visit.t = 0;
  const visitPressed = (st, m) => { const i = m - FIRST; if (i >= 0 && i < N) { held[i] = 1; alive[i] = 1; } };

  function layoutBells() {
    for (let b = 0; b < BELLS; b++) bells[b].cy = bells[b].cy0 * (portrait ? 0.93 : 1);
  }
  layoutBells();

  function update(dt, t, state) {
    if (!active) return;
    dt = clamp(dt || 0, 0, 0.1);
    uniforms.uTime.value = t;
    const f = feel.update(state, dt, t);
    const mo = moment.update(state, dt, t, f);
    const pedal = !!(state && state.pedal);
    pedalAmt = damp(pedalAmt, pedal ? 1 : 0, 0.15, dt);
    alive.fill(0); held.fill(0);
    const first = !seeded;
    // The sustain record (piano.js, the instrument-host header): an entry lives exactly while the page holds that sound,
    // finger or pedal. This is the whole of "the light lasts as long as the note does".
    const sounding = state ? (state.sounding ?? null) : null;
    if (sounding) {
      visit.t = t;
      sounding.forEach(visit);
    } else if (state && state.pressed) {
      // A host with no sustain record: fingers and the pedal, as the grand reads them
      state.pressed.forEach(visitPressed);
      for (let i = 0; i < N; i++) if (!alive[i] && pedal && body[i] > 0 && FIRST + i <= 88) alive[i] = 1;
      for (let i = 88 - FIRST + 1; i < N; i++) if (body[i] > 0) alive[i] = 1;   // the top 20 notes have no damper
    }
    seeded = true;
    // The strike ring: the only place a note struck and released inside one frame shows at all.
    const notes = state && state.notes;
    if (notes) {
      for (let k = 0; k < notes.length; k++) {
        const n = notes[k], i = n.midi - FIRST;
        if (i < 0 || i >= N || !(n.t > lastNote[i]) || n.t > t + 0.05) continue;
        lastNote[i] = n.t;
        if (!first) strike(i, n.vel, n.t, Math.max(0, t - n.t));  // on the first frame the ring is history, not news
      }
    }

    // ---- the envelope, per note, into the texture ----
    const kFlash = Math.exp(-dt / K.TAU_FLASH), kDamp = Math.exp(-dt / K.TAU_DAMP), kVibOff = Math.exp(-dt / K.TAU_VIB_OFF);
    for (let i = 0; i < N; i++) {
      flash[i] *= kFlash;
      if (flash[i] < 1e-4) flash[i] = 0;
      if (alive[i]) {
        bPrompt[i] *= Math.exp(-dt / tauPrompt[i]);
        bAfter[i] *= Math.exp(-dt / tauAfter[i]);
        vibGate[i] = 1;
        if (dampT[i]) dampT[i] = 0;
      } else if (body[i] > 0) {
        dampT[i] += dt;
        bFloor[i] *= kDamp; bPrompt[i] *= kDamp; bAfter[i] *= kDamp;
        vibGate[i] *= kVibOff;
      }
      let b = bFloor[i] + bPrompt[i] + bAfter[i];
      const w = dampT[i] > 0 ? dampFade(dampT[i]) : 1;
      b *= w;
      if (b < 1.5e-3) { b = 0; bFloor[i] = 0; bPrompt[i] = 0; bAfter[i] = 0; vibGate[i] = 0; }
      body[i] = b;
      dampW[i] = b > 0 ? w : 0;
      const env = b > 0 ? envMax[i] * Math.pow(b, K.ENV_EXP) * vibGate[i] : 0;
      heldMix[i] = damp(heldMix[i], alive[i] ? held[i] : heldMix[i], 0.4, dt);
      breathPhase[i] += dt * TAU * (0.16 + 0.05 * REG[i] + 0.1 * mo.energy);
      if (breathPhase[i] > TAU) breathPhase[i] -= TAU;
      const age = t - strikeAt[i];
      const travel = travelOf(VEL[i]);
      const headPos = age >= 0 && age < travel * 1.25 ? age / travel : -1;
      const pulse = headPos >= 0 ? VEL[i] * VEL[i] * K.PULSE_GAIN * (1 - clamp((age - travel * 0.95) / (travel * 0.3), 0, 1)) : 0;
      const recoil = age >= 0 && age < 2 ? VEL[i] * Math.exp(-age * 3.4) * Math.sin(age * 10) * dampW[i] : 0;
      const ringT = age >= 0 && age < 0.3 ? age / 0.3 : 0;
      const kick = age >= 0 ? VEL[i] * Math.exp(-age / 0.12) : 0;
      const o0 = i * 4, o1 = (N + i) * 4, o2 = (2 * N + i) * 4, o5 = (5 * N + i) * 4;
      texData[o0] = b; texData[o0 + 1] = flash[i]; texData[o0 + 2] = headPos; texData[o0 + 3] = env;
      texData[o1] = COL[i * 3]; texData[o1 + 1] = COL[i * 3 + 1]; texData[o1 + 2] = COL[i * 3 + 2]; texData[o1 + 3] = dampW[i];
      texData[o2] = pulse * dampW[i]; texData[o2 + 1] = 0.5 + 0.5 * Math.sin(breathPhase[i]); texData[o2 + 2] = heldMix[i]; texData[o2 + 3] = recoil;
      texData[o5] = ringT; texData[o5 + 1] = kick; texData[o5 + 2] = VEL[i];
    }
    noteTex.needsUpdate = true;

    // ---- the material and the moment ----
    const C = f.colour;
    const snowTarget = clamp(K.SNOW_MIN + 1.15 * C.lushness * (1 - 0.35 * C.simplicity) - 0.12 * C.simplicity + 0.1 * mo.density, K.SNOW_MIN, 1);
    snow = damp(snow, snowTarget, snowTarget > snow ? K.SNOW_TAU_IN : K.SNOW_TAU_OUT, dt);
    const val = mo.mood.valence;
    // the water: blue-black at rest, toward teal when the mood is bright, toward violet when it darkens; tension dims it
    const tealR = 0.003, tealG = 0.03, tealB = 0.04, violR = 0.016, violG = 0.006, violB = 0.046;
    const wr0 = val >= 0 ? lerp(0.004, tealR, val) : lerp(0.004, violR, -val);
    const wg0 = val >= 0 ? lerp(0.017, tealG, val) : lerp(0.017, violG, -val);
    const wb0 = val >= 0 ? lerp(0.038, tealB, val) : lerp(0.038, violB, -val);
    const wScale = (1 - 0.45 * C.tension) * (0.8 + 0.4 * C.brightness);
    waterR = damp(waterR, wr0 * wScale, 0.8, dt); waterG = damp(waterG, wg0 * wScale, 0.8, dt); waterB = damp(waterB, wb0 * wScale, 0.8, dt);
    uniforms.uWater.value.set(waterR, waterG, waterB);
    uniforms.uMat.value.set(C.lushness, C.tension, C.simplicity, C.brightness);
    uniforms.uMood.value.set(val, mo.energy, snow, pedalAmt);

    // the artifact: it grows inside the bell over the chord's root register and bursts when the chord changes
    const V = f.voices;
    if (V.bass !== null) artBell = bellOf(V.bass);
    if (mo.artifact.released) burst(artBell, mo.artifact.releaseStrength, t);
    const artTarget = mo.artifact.growth * (0.55 + 0.45 * mo.intensity);
    artLevel = damp(artLevel, artTarget, artTarget > artLevel ? 0.25 : 0.12, dt);
    for (let b = 0; b < BELLS; b++) bells[b].art = damp(bells[b].art, b === artBell ? artLevel : 0, 0.2, dt);

    // the dance: bass and solo, when they are two voices
    const on = V.count >= 2 && V.solo !== null && V.bass !== null && V.solo !== V.bass;
    if (on) {
      const nb = V.bass - FIRST, ns = V.solo - FIRST;
      if (nb !== danceBass || ns !== danceSolo) { danceOn *= 0.35; danceBass = nb; danceSolo = ns; }
    }
    danceOn = damp(danceOn, on ? 1 : 0, on ? 0.3 : 0.45, dt);
    const D = f.dance;
    const braidTarget = D.motion === "contrary" ? 1 : D.motion === "oblique" ? 0.45 : D.motion === "static" ? 0.12 : 0.25;
    braid = damp(braid, braidTarget, 0.5, dt);
    danceStretch = damp(danceStretch, D.stretch, 0.4, dt);
    dancePull = damp(dancePull, D.pull, 0.3, dt);
    const cons = D.consonance;
    // sea-green when sweet, violet-blue between, hot magenta when sour (a straight blend would pass through grey)
    const cr = cons < 0.5 ? lerp(1.0, 0.5, cons * 2) : lerp(0.5, 0.35, cons * 2 - 1);
    const cg = cons < 0.5 ? lerp(0.2, 0.42, cons * 2) : lerp(0.42, 0.95, cons * 2 - 1);
    const cb = cons < 0.5 ? lerp(0.55, 1.0, cons * 2) : lerp(1.0, 0.8, cons * 2 - 1);
    dcR = damp(dcR, cr, 0.4, dt); dcG = damp(dcG, cg, 0.4, dt); dcB = damp(dcB, cb, 0.4, dt);
    uniforms.uDance.value.set(clamp(danceBass, 0, N - 1), clamp(danceSolo, 0, N - 1), cons, braid);
    uniforms.uDance2.value.set(D.phase, danceStretch, dancePull, danceOn);
    uniforms.uDanceCol.value.set(dcR, dcG, dcB, 3.5 + 4 * dancePull + 2 * mo.energy);

    // ---- bells: the swim stroke, the breath, the sustained tint, the strike flash, the artifact's colour ----
    const breathHz = K.BREATH_HZ + 0.35 * mo.energy + 0.5 * C.tension;
    const breathAmp = (0.025 + 0.05 * (1 - C.simplicity) + 0.03 * C.lushness) * (1 - 0.6 * C.simplicity * (1 - mo.energy));
    let wr = 0, wg = 0, wb = 0, ar = 0, ag = 0, ab = 0, aw = 0;
    for (let b = 0; b < BELLS; b++) {
      const B = bells[b];
      B.pump = damp(B.pump, B.kick, K.PUMP_TAU_UP, dt);
      B.kick *= Math.exp(-dt / K.PUMP_TAU_DECAY);
      B.breathPhase += dt * TAU * breathHz * (1 + 0.08 * Math.sin(b * 1.7));
      if (B.breathPhase > TAU) B.breathPhase -= TAU;
      B.breath = damp(B.breath, breathAmp * (0.5 + 0.5 * Math.sin(B.breathPhase)), 0.2, dt);
      let sr = 0, sg = 0, sb = 0, fr = 0, fg = 0, fb = 0;
      const i0 = BELL_FIRST[b] - FIRST, i1 = BELL_LAST[b] - FIRST;
      for (let i = i0; i <= i1; i++) {
        const e = body[i];
        if (e > 1e-3) { sr += COL[i * 3] * e; sg += COL[i * 3 + 1] * e; sb += COL[i * 3 + 2] * e; }
        const fl = flash[i];
        if (fl > 1e-3) { fr += COL[i * 3] * fl; fg += COL[i * 3 + 1] * fl; fb += COL[i * 3 + 2] * fl; }
      }
      // many notes average toward grey, and a grey bell blooms white: pull the summed hue back toward its dominant colour
      let mn = Math.min(sr, sg, sb) * 0.55; sr -= mn; sg -= mn; sb -= mn;
      let L = luma(sr, sg, sb);
      let k = L > 1e-5 ? Math.min(1.2, K.BELL_SUS_CAP / L) : 0;   // the summed hue at a capped brightness
      k *= Math.min(1, L / 0.25 + 0.35);                           // a lone soft note still reads, less than a chord
      uniforms.uBellCol.value[b].set(sr * k, sg * k, sb * k, Math.min(1, L * 2));
      mn = Math.min(fr, fg, fb) * 0.7; fr -= mn; fg -= mn; fb -= mn;
      L = luma(fr, fg, fb);
      k = L > K.BELL_FLASH_CAP ? K.BELL_FLASH_CAP / L : 1;
      uniforms.uBellFlash.value[b].set(fr * k * 1.2, fg * k * 1.2, fb * k * 1.2, 0);
      const y = B.cy + Math.sin(t * 0.31 + b * 1.9) * 0.14 + 0.28 * B.pump + 0.4 * B.art;
      const x = B.cx + Math.sin(t * 0.17 + b) * 0.08;
      uniforms.uBellPos.value[b].set(x, y, B.cz, B.r);
      uniforms.uBellAnim.value[b].set(B.pump, B.breath, B.art, pedalAmt);
      wr += sr; wg += sg; wb += sb;
      if (b === artBell) { ar = sr; ag = sg; ab = sb; aw = L; }
    }
    // the artifact's light: the root bell's chord colour, warmed as the intensity climbs, luma capped
    {
      let L = luma(ar, ag, ab);
      if (L < 1e-4) { ar = 0.5; ag = 0.7; ab = 1; L = luma(ar, ag, ab); }
      const warm = 0.35 * mo.intensity;
      let r = ar / L * (1 + warm), g = ag / L, bb = ab / L * (1 - 0.5 * warm);
      const L2 = luma(r, g, bb), cap = 0.7 * (0.4 + 0.6 * artLevel) / Math.max(L2, 1e-4);
      uniforms.uArtCol.value.set(r * cap, g * cap, bb * cap, (mo.artifact.seed % 997) / 997);
    }
    const wl = luma(wr, wg, wb);
    const bk = wl > 1e-5 ? Math.min(0.009, wl * 0.006) / wl : 0;
    uniforms.uBedTint.value.set(wr * bk, wg * bk, wb * bk);

    if (pointsDirty) {
      pointsGeo.attributes.aP.needsUpdate = true;
      pointsGeo.attributes.aV.needsUpdate = true;
      pointsGeo.attributes.aC.needsUpdate = true;
      pointsGeo.attributes.aN.needsUpdate = true;
      pointsDirty = false;
    }
  }

  function resize(framing) {
    portrait = !!framing && (framing.id === "9:16" || (framing.h > 0 && framing.h > framing.w));
    layoutBells();
  }
  function setActive(on) {
    active = !!on;
    group.visible = active;
    if (!active) seeded = false;                     // mounted again, it picks up whatever is sounding then
  }
  function dispose() {
    if (group.parent) group.parent.remove(group);
    for (const g of geos) g.dispose();
    for (const m of mats) m.dispose();
    for (const t of texs) t.dispose();
    geos.length = 0; mats.length = 0; texs.length = 0;
  }
  resize(ctx.framing);
  return { group, update, resize, setActive, dispose, keyStyle: KEY_STYLE, hints: HINTS,
           debug: { bells, body, flash, texData, uniforms, meshes, feel, moment, geos, mats, texs } };
}

export default { id: ID, name: "Abyssal", keyStyle: KEY_STYLE, hints: HINTS, create };
