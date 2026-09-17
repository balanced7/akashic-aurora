// Ornithopter — arsenal/web/piano/instruments/light-vandor-ornithopter.js  (ES module, a piano instrument)
// "Instruments of light" house round, 2026-09-17 (research/in-flight/piano-light-instruments-2026-09-17/brief.md).
// Tests: tests/piano_light_vandor.test.mjs. Entry note: research/in-flight/piano-light-instruments-2026-09-17/entry_vandor.md.
//
// Daniel: "Notes that are lower could have more of a blur and vibration similar to the wings in the helicopters from the
// movie dune", "the strings could be bands of light being struck with hammers where the feel looks realistic and is
// responsive to velocity and the sustain pedal", "lush chords could emit a wind or fog or something", "When a chord feels
// really intense it can start building some kind of artifact, then when the chord changes it can change."
//
// THE CREATURE. A long insect lies behind the keys, head at the bass end, tail at the treble: an armoured head with two
// compound lenses and antennae, a thick thorax on six jointed legs planted on the floor, a segmented chitin abdomen
// tapering to a tail with two cerci, propped by four prolegs. Sand-gold spars on shadow. From its back rise 88 wing
// membranes, one per key, in two ranks like a dragonfly's fore and hind wings (white keys forewings, black keys hindwings):
// long, wide and soft in the bass, short and stiff in the treble.
//
// THE STRIKE. A thorax piston under each wing root snaps up (faster the harder) and hits the wing; the membrane lights in
// the note colour and BEATS. The beat is never animated frame by frame: every pixel draws the exact time average of a blade
// sweeping a sinusoid (the arcsine density, bright at the two ends of the stroke where a real wing dwells, translucent in
// the middle), which is what a film camera saw of the ornithopter wings. Wide and slow in the bass (A0 a broad soft
// envelope), a stiff fast shimmer in the treble. Velocity: stroke amplitude, membrane brightness, piston speed. The flash
// at the knuckle (the piston's blow, a hot core running up the wing from the root) is the only light over the bloom line; a
// runner carries it up the wing.
//
// THE SOUND (state.sounding, the page's own sustain record): the same envelope as the concert grand, a flash, a prompt
// decay, a pitch-dependent aftersound, then a velocity-scaled floor held for the whole sound, finger or pedal, and a 0.30 s
// damping fade at its end. The wing stands up while its note sounds and beats at a settling amplitude while the pedal
// holds it; when the sound ends the light fades and the wing folds to rest in about 0.3 s. A re-strike re-flashes from the
// level it finds. The pedal alone lights nothing (it opens the clasps on the body, which is the frame showing the pedal).
//
// THE MATERIAL (harmony-feel): lushness raises the membranes' thin-film iridescence (a hue ramp on the fresnel term) and
// lets a sand haze exhale from the thorax (four noise-textured translucent quads, soft-edged, alpha capped at HAZE_MAX);
// tension tightens the wing-beat (breathing and ghost rate) and cools the palette around the note colour (spars, edges,
// haze); simplicity stills everything to clean chitin and bare spars.
// THE DANCE (harmony-feel): a hairline filament from the bass wing to the solo wing, two strands that twist into a braid in
// contrary motion, tighten with pull and straighten with stretch, coloured by consonance (gold sweet, indigo sour).
// THE MOMENT (moment.js): intensity grows a sand-glass crystal between the wing roots of the held chord, in the chord's
// mixed colour; when the chord changes it shatters into motes with the release strength (two alternating shard clusters,
// so a new chord can start building while the last one is still flying). mood.valence warms or cools the haze; energy
// scales the creature's breathing (a peristaltic wave along the body) and the stir of the dust.
//
// Contract: export default { id, name, keyStyle, keySpan, create(ctx) } ->
//   { group, update(dt, t, state), resize(framing), setActive(on), dispose(), stageHints: { floorY, hideHostBody } }.
// Draws only itself (no camera, renderer, fog, background or layer writes). No allocation inside update (all scratch is
// typed arrays sized in create; the sounding Map is walked with forEach). Fixed draw calls: body, lenses, keybed, pistons,
// clasps, wing membranes, wing light, dust, haze, braid, artifact A, artifact B, pool = 13, always drawn (everything is
// frustumCulled = false and an idle part collapses in its vertex shader). dispose() returns geometries, textures and
// programs to baseline. Nothing downloaded: the noise texture is a DataTexture built in code.
//
// ---- the envelope (the concert grand's table, the same numbers, so the two answer a held pedal identically) ----
//   PEAK_EXP        body at the strike = v^PEAK_EXP                                    1.35
//   FLASH_EXP       the flash's height = v^FLASH_EXP                                   2.0
//   TAU_FLASH       the flash's decay: the only light allowed over the bloom line       0.09 s
//   FLOOR_LO/HI     the floor, as a share of the strike body, vel 1 -> vel 127          0.33 -> 0.50, held for the WHOLE sound
//   AFTER_SHARE     how much of the above-floor body is the slow aftersound             0.55
//   TAU_PROMPT      the prompt decay                                                    1.00 s at A0 -> 0.45 s at C8
//   TAU_AFTER       the aftersound                                                      7.0 s at A0 -> 1.2 s at C8
//   TAU_DAMP        the damper landing when the sound ENDS                              0.16 s
//   DAMP_FADE       the window that closes that fall to exactly 0 (a fade, not a snap)  0.30 s
//   TAU_VIB_OFF     the ghost and tremor stop before the light is gone                  0.07 s
//   LIGHT_EXP       shown light = SUS_GAIN * body^LIGHT_EXP: a soft note still reads    0.75 (v30 shows 24 % of ff)
//   SUS_GAIN        the sustained light gain (the shader caps every sustained CHANNEL   1.6
//                   at 0.85: the light pass blends with a per-channel max, so the cap
//                   has to hold per channel for ten hues stacked to stay under the line)
//   FLASH_REACH     wings flashing within this many semitones share one flash: each     1 semitone
//   FLASH_SHARE     one's flash is divided by (1 + n)^FLASH_SHARE, n the neighbours     3.0 (a semitone pair: an eighth each;
//   FLASH_NEIGH     flashing (a neighbour counts fully from this raw flash, less below)  0.25   two whole sparks 2+ semitones
//                   apart never white out, an fff semitone pair of the host's complementary neighbour hues did at 1.0 and 2.0)
//   KNUCKLE         the strike's core: across the wing exp(-across u^2), u in key units;   12 / 0.07 / 0.08 / 5.5
//                   along it exp(-((s - along) / width)^2), s in wing units, so it runs up the membrane from the blow past
//                   the clasp and piston in front of the root; gain over the note colour times the flash (repair 2)
//   AMP_BASS/TREBLE the stroke half-amplitude at full body, degrees, over pitch         19 -> 3 (power AMP_POW 1.7)
//   AMP_EXP         amplitude = AMP(pitch) * body^AMP_EXP: a pedalled note settles to   0.8
//                   about half its strike stroke and never stops while it sounds
//   VIB_HZ          the envelope's breathing rate (never the pitch), bass -> top        2.2 -> 6.0 Hz, +-VIB_DEPTH 0.12
//   GHOST_HZ        the strobe ghost's rate, bass only (it fades out toward the top)    1.6 -> 5.0 Hz
//   FOLD_UP/DOWN    the wing stands up in FOLD_UP and folds to rest in ~3 x FOLD_DOWN   0.05 / 0.10 s
import { createHarmonyFeel } from "../harmony-feel.js";
import { createMoment } from "../moment.js";

const ID = "light-vandor-ornithopter";
const N = 88, FIRST = 21;
const DEG = Math.PI / 180;

const PEAK_EXP = 1.35, FLASH_EXP = 2;
const FLOOR_LO = 0.33, FLOOR_HI = 0.50;
const AFTER_SHARE = 0.55;
const TAU_PROMPT_BASS = 1.00, TAU_PROMPT_TREBLE = 0.45;
const TAU_AFTER_BASS = 7.0, TAU_AFTER_TREBLE = 1.2;
const TAU_FLASH = 0.09, TAU_DAMP = 0.16, DAMP_FADE = 0.30, TAU_VIB_OFF = 0.07;
const LIGHT_EXP = 0.75, SUS_GAIN = 1.6, FLASH_GAIN = 1.8;
const FLASH_REACH = 1, FLASH_NEIGH = 0.25, FLASH_SHARE = 3.0;   // wings flashing within FLASH_REACH semitones share one flash
const AMP_BASS = 19, AMP_TREBLE = 3, AMP_POW = 1.7, AMP_EXP = 0.8;
const VIB_HZ_BASS = 2.2, VIB_HZ_TREBLE = 6.0, VIB_DEPTH = 0.12;
const GHOST_HZ_BASS = 1.6, GHOST_HZ_TREBLE = 5.0;
const FOLD_UP = 0.05, FOLD_DOWN = 0.10;
const FLINCH = 0.4, FLINCH_TAU = 0.16, FLINCH_HZ = 1.9;
const HAZE_MAX = 0.3;

// ---- layout (host units: one white-key pitch; key tops y = 0, key backs z = -3.1, span centre x = 0) ----
const SPINE = { x0: -31.5, x1: 30.0, y: 2.3, z: -7.2 };
const HEAD_LEN = 3.2, THORAX_END = 11.0;     // from x0: the head, then the thorax to its waist
const FLOOR_Y = -9.5;
const WING = {
  lenTreble: 10.5, lenBass: 30.0, lenPow: 1.62,
  chordTreble: 1.05, chordBass: 2.5, chordPow: 1.15, hindChord: 1.06,
  leanBass: 0.12, leanTreble: -0.14, hindLean: -0.13,
  backBass: 54 * DEG, backTreble: 43 * DEG, hindBack: 7 * DEG,
  restSweep: 11 * DEG, hindRestSweep: 15 * DEG,   // folded to rest: swept toward the tail; a struck wing stands up
  bend: 0.75,                                      // tip amplitude = root amplitude * (1 + bend * s^2): long wings flex
};
const PISTON = { rest: -0.45, gap: 0.3, check: 0.34, k: 1100, c: 42, vSoft: 44, vHard: 78, rebound: 0.32 };
const LIGHT = { maxChannel: 1.15, membrane: 0.8, vein: 1.2, ptero: 1.3, flashTravel: 0.17 };
// the strike's knuckle core: across the wing exp(-u^2 * across), u in key units (a third of a key at 1/e, so the cores of
// adjacent wings never overlap); along the wing exp(-((s - along) / width)^2), s in wing units, so it runs up the membrane
// from the piston's blow past the clasp and piston standing in front of the root (repair 2: a core centred on the root
// itself hid behind them and a lone strike showed no spark); gain is its height over the note colour times the flash
const KNUCKLE = { across: 12.0, along: 0.07, width: 0.08, gain: 5.5 };
const KEY_STYLE = { whiteColor: 0xe9e3d6, blackColor: 0x0b0907, capHeight: null, frontLip: 0 };

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
const pitchOf = (m) => (m - FIRST) / (N - 1);
const overPitch = (m, lo, hi) => lo * Math.pow(hi / lo, pitchOf(m));
const dampFade = (x) => { if (x >= DAMP_FADE) return 0; const u = x / DAMP_FADE; return 1 - u * u * (3 - 2 * u); };

// ------------------------------------------------------------------------------------------------ shaders --
const WING_VERT = /* glsl */ `
attribute vec4 aShape;   // length, chord, pitch 0..1, seed
attribute vec4 aState;   // amplitude (rad), centre (rad), ghost phase (rad), light level
attribute vec4 aStrike;  // age (s), velocity 0..1, flash, stand (0 folded .. 1 standing)
attribute vec3 aColor;   // the note colour, linear
varying vec2 vP;
varying vec4 vShape;
varying vec4 vState;
varying vec4 vStrike;
varying vec3 vColor;
varying vec3 vN;
varying vec3 vView;
uniform float uBend;
void main() {
  float L = aShape.x, W = aShape.y;
  float sweep = (abs(aState.y) + aState.x) * (1.0 + uBend);
#ifdef LIGHT_PASS
  if (aState.w + aStrike.z < 0.0015) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
#endif
  float halfU = L * sin(min(sweep, 1.2)) + W * 0.62 + 0.12;
  float u = position.x * halfU;
  float v = mix(-0.25, L * 1.03, position.y);
  vec4 world = modelMatrix * instanceMatrix * vec4(u, v, 0.0, 1.0);
  vP = vec2(u, v);
  vShape = aShape; vState = aState; vStrike = aStrike; vColor = aColor;
  vN = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * vec3(0.0, 0.0, 1.0));
  vView = cameraPosition - world.xyz;
  gl_Position = projectionMatrix * viewMatrix * world;
}`;

const WING_FRAG = /* glsl */ `
#define PI 3.14159265
varying vec2 vP;
varying vec4 vShape;
varying vec4 vState;
varying vec4 vStrike;
varying vec3 vColor;
varying vec3 vN;
varying vec3 vView;
uniform float uTime;
uniform float uBend;
uniform float uMaxChannel;
uniform float uIrid;     // lushness: thin-film iridescence on the fresnel term
uniform float uStill;    // simplicity: no shimmer, crisp veins
uniform vec3 uGold;      // the spar colour (cools with tension)
uniform vec3 uSmoke;
uniform vec3 uCool;      // the grazing-edge tint (cools with tension)
uniform vec4 uLight;     // membrane, vein, ptero, flash travel
uniform vec4 uKnuckle;   // across (1 / key units^2), along centre (s), along half-width (s), gain

// time-averaged coverage of a blade of angular half-width hw whose angle is c + A sin(wt): the arcsine CDF
float F(float x, float A) { return 0.5 + asin(clamp(x / A, -1.0, 1.0)) / PI; }
float sweepCover(float phi, float c, float hw, float A) { return clamp(F(phi - c + hw, A) - F(phi - c - hw, A), 0.0, 1.0); }
float hash1(float n) { return fract(sin(n * 91.3458) * 47453.5453); }
float line(float d, float w, float fw) { return 1.0 - smoothstep(w, w + fw * 1.25, abs(d)); }
vec3 film(float x) { return 0.5 + 0.5 * cos(6.2831853 * (x + vec3(0.0, 0.33, 0.67))); }

void main() {
  float L = vShape.x, W = vShape.y, pn = vShape.z, seed = vShape.w;
  float amp = vState.x, cen = vState.y, ph = vState.z, level = vState.w;
  vec2 p = vP;
  float r = length(p);
  float s = r / L;
  if (s > 1.03) discard;
  float phi = atan(p.x, p.y);
  float bendF = 1.0 + uBend * s * s;
  float A = amp * bendF;
  float C = cen * bendF;

  // planform: a narrow stalk at the root, an ellipse from s 0.08 to 1.0, broadest a little past the middle
  float e = (s - 0.5) / 0.53;
  float pf = sqrt(max(0.0, 1.0 - e * e));
  pf *= 1.0 - 0.78 * smoothstep(0.5, 1.0, s);             // a drawn-out tip, so the tip's own arc stays a filament
  float stalk = 0.16 * (1.0 - smoothstep(0.0, 0.25, s)) + 0.04 * (1.0 - smoothstep(0.35, 0.98, s));
  float halfChord = W * 0.5 * max(pf, stalk);
  float tipFade = 1.0 - 0.75 * smoothstep(0.78, 1.0, s);
  float hw = halfChord / max(r, 0.06);
  float pix = fwidth(phi) * 0.8 + 1e-5;
  float Aeff = max(A, pix);

  float cover = sweepCover(phi, C, hw, Aeff);
  float spread = A / max(hw, 1e-3);                    // how many blade widths the stroke covers
  float blur = smoothstep(0.15, 2.2, spread);
  float gain = min(pow(1.0 + spread, 0.42), 2.3);      // a wide envelope holds the same light, spread thinner
  float envelope = min(cover * gain, 1.0);
  envelope = mix(envelope, envelope * envelope * (1.5 - 0.5 * envelope), blur * 0.85);   // hollow in the middle, dense at the turns

  // the strobe ghost: where the blade is now, smeared by its own speed; bass only, it fades out toward the top
  float theta = C + A * sin(ph);
  float smear = pix + A * abs(cos(ph)) * 0.35;
  float dq = phi - theta;
  float ghost = 1.0 - smoothstep(hw - smear, hw + smear, abs(dq));
  float ghostW = (1.0 - pn) * (1.0 - pn);
  float body = max(envelope, ghost * 0.35 * blur * ghostW) * tipFade;

  // The two spars the membrane is stretched between, swept the same way. A thin blade smeared over a sinusoid piles up
  // where the stroke turns, so a beating wing is bounded by two bright arcs and nearly hollow between them: the
  // ornithopter's ghost wings. At rest they are simply the leading spar and the trailing edge.
  float tipEnd = tipFade;
  float rootEnd = smoothstep(0.02, 0.14, s);
  float hwc = max(hw * 0.05, pix * 0.55);
  float sparGain = min(pow(1.0 + A / hwc, 0.5), 5.0);
  float spar = min(sweepCover(phi, C - hw * 0.92, hwc, Aeff) * sparGain, 1.0) * tipEnd * rootEnd;
  float trailEdge = min(sweepCover(phi, C + hw * 0.96, max(hw * 0.05, pix * 0.5), Aeff) * sparGain * 0.8, 1.0) * tipEnd * rootEnd;

  // veins, in the ghost blade's own frame; they smear away as the blur opens
  float q = dq * r / max(halfChord, 1e-3);             // -1 leading edge .. +1 trailing edge
  float fwU = fwidth(vP.x) + fwidth(vP.y);
  float chordPx = 2.0 * halfChord / max(fwU, 1e-5);
  float fq = fwidth(q);
  float inside = 1.0 - smoothstep(0.98, 1.0 + fq, abs(q));
  float veins = 0.0;
  float longFade = smoothstep(9.0, 22.0, chordPx);
  veins = max(veins, line(q + 0.62, 0.025, fq) * 0.8 * longFade);
  veins = max(veins, line(q + 0.22, 0.02, fq) * 0.7 * longFade);
  veins = max(veins, line(q - 0.22, 0.02, fq) * 0.65 * longFade);
  veins = max(veins, line(q - 0.6, 0.02, fq) * 0.6 * longFade);
  float band = floor((q + 1.0) * 2.6);
  float cellLen = max(W * 0.36, 0.1);
  float ct = (s * L) / cellLen + hash1(band * 7.1 + seed * 13.0) * 1.7 + s * s * 1.3;
  float cfw = fwidth(ct);
  float crossV = line(fract(ct + 0.5) - 0.5, 0.045, cfw) * smoothstep(20.0, 42.0, chordPx);
  veins = max(veins, crossV * 0.55 * step(0.12, s));
  veins *= inside * (1.0 - smoothstep(0.985, 1.02, s));
  float veinVis = 1.0 - 0.9 * blur;

  // pterostigma: a small cell on the leading edge near the tip; blurred, it draws the stroke's arc at the tip
  float pRad = smoothstep(0.76, 0.785, s) * (1.0 - smoothstep(0.865, 0.89, s));
  float hwp = hw * 0.13;
  float ptero = sweepCover(phi, C - hw * 0.8, hwp, Aeff) * pRad;
  ptero = min(ptero * min(sqrt(1.0 + A / max(hwp, 1e-3)) * 0.8, 4.0), 1.0);

  vec3 Nn = normalize(vN);
  vec3 V = normalize(vView);
  float ndv = abs(dot(Nn, V));
  float fres = pow(max(1.0 - ndv, 0.0), 3.0);           // never a base under zero: pow() would hand the bloom a NaN
  // a glossy sheen band running along the membrane, so it reads as a stretched film and not as empty air
  float sheenQ = 1.0 - smoothstep(0.0, 0.62, abs(q + 0.25));
  float sheen = sheenQ * (0.35 + 0.65 * smoothstep(0.1, 0.55, s)) * (1.0 - smoothstep(0.9, 1.02, s));
  vec3 Hwarm = normalize(normalize(vec3(-0.42, 0.78, 0.52)) + V);
  vec3 Hcool = normalize(normalize(vec3(0.34, 0.42, -0.86)) + V);
  float specWarm = pow(max(dot(Nn, Hwarm), 0.0), 30.0);
  float specCool = pow(max(dot(Nn, Hcool), 0.0), 14.0);
  // thin-film iridescence on the fresnel term: a lush chord lets the membrane split the light
  vec3 irid = film(fres * 2.2 + s * 0.6 + uTime * 0.05 + seed);

#ifdef LIGHT_PASS
  vec3 base = vColor;
  float mc = max(max(base.r, base.g), base.b);
  vec3 sus = base * min(1.0, uMaxChannel / max(mc, 1e-3));
  // the treble shimmer: a slow wave travelling along the membrane (about a second a cycle), never a flicker
  float shimmer = 1.0 + 0.16 * pn * (1.0 - 0.7 * uStill) * sin(uTime * (6.0 + 3.0 * seed) - s * 14.0 + seed * 40.0);
  float glow = body * uLight.x * (0.7 + 0.5 * sheen + 0.3 * fres)
             + veins * veinVis * uLight.y
             + max(spar, trailEdge * 0.55) * uLight.y * 1.25
             + ptero * uLight.z;
  vec3 col = sus * level * min(glow * shimmer, 1.0);
  col *= mix(vec3(1.0), irid * 2.0, uIrid * 0.35 * (0.3 + 0.7 * fres) * body);
  // sustained light never crosses the bloom line, whatever the tuning. The cap is on the brightest CHANNEL, not the luma:
  // this pass blends with a per-channel max, and the max over ten hues is a neutral whose luma is the channel cap.
  col *= min(1.0, 0.85 / max(max(col.r, col.g), max(col.b, 1e-4)));
  // the strike: a flash at the knuckle where the piston lands, and a runner that carries it up the wing
  float age = vStrike.x, flash = vStrike.z;
  if (flash > 0.001) {
    float front = age / uLight.w;
    float dr = (s - front) / 0.11;
    float runner = exp(-dr * dr) * (1.0 - smoothstep(1.0, 1.25, front));
    // the knuckle: a core a third of a key wide ACROSS the wing (u in key units whatever the wing's length, so the cores
    // of adjacent wings never overlap) that runs UP the wing from the piston's blow (s in wing units), where the membrane
    // is and the clasp and piston standing in front of the root cannot hide it; the host's bloom draws its halo
    float ds = (s - uKnuckle.y) / uKnuckle.z;
    float knuckle = exp(-(p.x * p.x * uKnuckle.x + ds * ds)) * (0.75 + 0.25 * pn);
    vec3 fcol = base * flash * (runner * max(body, spar) * 0.8 + knuckle * uKnuckle.w + ptero * runner);
    // the flash claims its pixel instead of stacking on the sustained light: the sustained part gives way as the flash
    // nears the bloom line, so the total is never more than the larger of 0.9 and the flash itself, and two wings meeting
    // at the cap cannot stack their flashes past it
    float fl = dot(fcol, vec3(0.2126, 0.7152, 0.0722));
    col = col * (1.0 - min(fl / 0.9, 1.0)) + fcol;
  }
  gl_FragColor = vec4(col, 1.0);
#else
  // the membrane itself: smoky amber film, sand-gold spars and veins lit from the upper left, a cool grazing edge
  float lit = 0.35 + 0.65 * max(dot(Nn, normalize(vec3(-0.35, 0.75, 0.55))), 0.0);
  float stand = vStrike.w;
  float restDim = 0.5 + 0.5 * smoothstep(0.0, 0.5, level);
  float film_ = body * (0.5 + 0.5 * sheen) * restDim;
  float alpha = film_ * (0.09 + 0.16 * fres + 0.07 * specWarm + 0.05 * specCool);
  vec3 col = uSmoke * film_ * (1.0 + 1.6 * sheen) + uCool * fres * body * 0.5
           + vec3(0.03, 0.022, 0.013) * specWarm * film_ * (0.5 + 0.9 * sheen)
           + uCool * 0.8 * specCool * film_;
  col += irid * uIrid * 0.02 * film_ * (0.4 + 0.6 * sheen) * fres;
  float veinA = veins * veinVis * mix(0.3, 0.7, smoothstep(0.0, 0.4, level));
  // unlit, the spar fades toward the tip and is kept off the root (nothing gold sits behind the keys at rest); a
  // standing wing carries its full spar
  float sparA = max(spar, trailEdge * 0.5) * mix((1.0 - 0.55 * s) * smoothstep(0.04, 0.3, s) * 0.2, 1.0, smoothstep(0.0, 0.4, level));
  col += uGold * (veinA * (0.004 + 0.006 * lit) + sparA * (0.016 + 0.028 * lit) * (0.7 + 0.3 * stand));
  col += uGold * ptero * (0.016 + 0.014 * lit);
  alpha = max(alpha, max(max(veinA, sparA), ptero) * 0.75);
  gl_FragColor = vec4(col, alpha);
#endif
}`;

const DUST_VERT = /* glsl */ `
attribute vec4 aSeed;
uniform float uTime;
uniform sampler2D uWash;     // 88 x 1: rgb note colour * light, a = stroke energy
uniform float uPx;
uniform float uStir;         // the moment's energy
varying vec3 vCol;
varying float vA;
void main() {
  float x = mix(-30.0, 30.0, aSeed.x);
  float drift = uTime * (0.08 + 0.1 * aSeed.w);
  float y = mix(0.4, 26.0, pow(fract(aSeed.y + drift * 0.07), 1.25));
  float z = mix(-4.5, -24.0, aSeed.z);
  float ix = clamp((x + 26.0) / 52.0, 0.0, 1.0);
  vec4 w = texture2D(uWash, vec2(ix, 0.5));
  float stir = w.a + uStir * 0.35;
  float ang = uTime * (1.3 + 2.0 * aSeed.w) + aSeed.x * 40.0;
  x += sin(ang) * (0.25 + 1.6 * stir) + sin(uTime * 0.21 + aSeed.y * 30.0) * 0.4;
  y += cos(ang * 0.7) * 0.3 * (0.3 + stir);
  z += cos(ang) * 0.3;
  vec4 mv = modelViewMatrix * vec4(x, y, z, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = clamp(uPx * (0.08 + 0.09 * aSeed.w) / -mv.z, 1.0, 6.5);
  vCol = w.rgb;
  vA = (0.1 + 0.7 * smoothstep(0.02, 0.5, stir)) * (0.3 + 0.6 * aSeed.w);
}`;
const DUST_FRAG = /* glsl */ `
uniform vec3 uSand;
varying vec3 vCol;
varying float vA;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = 1.0 - smoothstep(0.1, 0.5, length(c));
  vec3 col = (uSand * 0.06 + vCol * 0.9) * vA * d;
  gl_FragColor = vec4(col, 1.0);
}`;

const POOL_VERT = /* glsl */ `
varying vec2 vXZ;
void main() { vXZ = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const POOL_FRAG = /* glsl */ `
varying vec2 vXZ;
uniform vec3 uSand;
uniform vec3 uTint;
uniform float uBreath;
void main() {
  vec2 p = vXZ / vec2(46.0, 26.0);
  float fall = exp(-dot(p, p) * 2.2);
  float ripple = 0.5 + 0.5 * sin(vXZ.x * 0.9 + sin(vXZ.y * 0.35) * 2.4 + vXZ.y * 0.2);
  vec3 col = uSand * fall * (0.55 + 0.45 * ripple) * (0.8 + 0.4 * uBreath) + uTint * fall * 0.5;
  gl_FragColor = vec4(col, 1.0);
}`;

// the sand haze: four soft quads hanging off the thorax, each breathing on its own, drifting up and away
const HAZE_VERT = /* glsl */ `
attribute vec3 aQuad;        // quad index, seed a, seed b
uniform float uTime, uHaze, uEnergy;
uniform vec3 uOrigin;
varying vec2 vUv;
varying float vSeed;
varying float vFade;
void main() {
  if (uHaze < 0.002) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  float k = aQuad.x, sa = aQuad.y, sb = aQuad.z;
  float breath = 0.5 + 0.5 * sin(uTime * (0.45 + 0.5 * uEnergy) + k * 1.7 + sb * 4.0);
  vec3 c = uOrigin + vec3(5.0 + k * 4.0 + sa * 2.0, 3.5 + k * 2.4 + breath * 1.8, -2.0 - k * 2.8);
  vec2 sz = vec2(12.0 + k * 3.5, 7.5 + k * 1.8) * (0.85 + 0.5 * uHaze);
  vec3 p = c + vec3(position.x * sz.x, position.y * sz.y, 0.0);
  vUv = position.xy; vSeed = sa; vFade = 1.0 - k * 0.14;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}`;
const HAZE_FRAG = /* glsl */ `
uniform sampler2D uNoise;
uniform float uTime, uHaze;
uniform vec3 uHazeColor;
varying vec2 vUv;
varying float vSeed;
varying float vFade;
void main() {
  vec2 q = vUv;
  float edge = 1.0 - smoothstep(0.3, 1.0, length(q));
  vec2 w1 = vec2(uTime * 0.012 + vSeed, -uTime * 0.02);
  vec2 w2 = vec2(-uTime * 0.008, -uTime * 0.014 + vSeed * 3.0);
  float n1 = texture2D(uNoise, q * 0.9 + w1).r;
  float n2 = texture2D(uNoise, q * 1.7 + w2).g;
  float n = smoothstep(0.25, 0.85, n1 * 0.65 + n2 * 0.5);
  float a = uHaze * n * edge * edge * vFade;
  gl_FragColor = vec4(uHazeColor * a, a);
}`;

// the dance: two strands from the bass wing to the solo wing, a screen-space hairline, braided in the vertex shader
const BRAID_VERT = /* glsl */ `
uniform vec3 uA, uB;         // the two wings (group space)
uniform vec2 uRes;
uniform float uTwist, uPhase, uRadius, uSag, uPx, uLevel;
varying float vAcross;
varying float vU;
vec3 curve(float u, float strand) {
  vec3 d = uB - uA;
  vec3 p = uA + d * u + vec3(0.0, uSag * sin(3.14159265 * u), 0.0);
  vec3 t = normalize(d + vec3(1e-4, 0.0, 0.0));
  vec3 n1 = normalize(cross(t, vec3(0.0, 0.0, 1.0)) + vec3(0.0, 1e-4, 0.0));
  vec3 n2 = cross(t, n1);
  float th = 6.2831853 * (uTwist * u + uPhase) + strand * 3.14159265;
  float env = sin(3.14159265 * clamp(u, 0.0, 1.0));   // the strands meet at both wings
  return p + (n1 * cos(th) + n2 * sin(th)) * uRadius * env;
}
void main() {
  if (uLevel < 0.002) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  float u = position.x, side = position.y, strand = position.z;
  vec3 p0 = curve(u, strand), pa = curve(u - 0.01, strand), pb = curve(u + 0.01, strand);
  vec4 c0 = projectionMatrix * modelViewMatrix * vec4(p0, 1.0);
  vec4 ca = projectionMatrix * modelViewMatrix * vec4(pa, 1.0);
  vec4 cb = projectionMatrix * modelViewMatrix * vec4(pb, 1.0);
  vec2 sa = ca.xy / max(ca.w, 1e-4) * uRes * 0.5, sb = cb.xy / max(cb.w, 1e-4) * uRes * 0.5;
  vec2 tang = sb - sa;
  vec2 nrm = dot(tang, tang) > 1e-8 ? normalize(vec2(-tang.y, tang.x)) : vec2(1.0, 0.0);
  float w = max(c0.w, 1e-4);
  c0.xy += nrm * side * uPx / (uRes * 0.5) * w;
  gl_Position = c0;
  vAcross = side; vU = u;
}`;
const BRAID_FRAG = /* glsl */ `
uniform vec3 uColor;
uniform float uLevel;
varying float vAcross;
varying float vU;
void main() {
  float a = 1.0 - abs(vAcross);
  a = a * a * uLevel * smoothstep(0.0, 0.06, vU) * smoothstep(1.0, 0.94, vU);
  gl_FragColor = vec4(uColor * a, a);
}`;

// the artifact: a cluster of sand-glass shards growing between the wing roots; on release they fly apart and fade
const SHARD_VERT = /* glsl */ `
attribute vec4 aSeed;
uniform float uTime, uGrowth, uShatter, uRelease, uSpread;
uniform vec3 uCenter;
varying vec3 vN;
varying vec3 vView;
varying float vAlpha;
varying float vSeed;
mat3 rotY(float a) { float c = cos(a), s = sin(a); return mat3(c, 0.0, -s, 0.0, 1.0, 0.0, s, 0.0, c); }
mat3 rotX(float a) { float c = cos(a), s = sin(a); return mat3(1.0, 0.0, 0.0, 0.0, c, s, 0.0, -s, c); }
void main() {
  float s0 = aSeed.x * 0.7;
  float gi = smoothstep(s0, s0 + 0.3, uGrowth);
  float shat = max(uShatter, 0.0);
  float fade = 1.0 - smoothstep(0.0, 1.4, shat);
  float vis = gi * (uShatter < 0.0 ? 1.0 : fade);
  if (vis < 0.003) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  float ang = aSeed.y * 6.2831853, el = (aSeed.z - 0.5) * 2.4;
  vec3 dir = vec3(cos(ang) * cos(el), sin(el) * 0.8 + 0.35, sin(ang) * cos(el) * 0.6);
  float rad = (0.6 + 2.8 * aSeed.w) * (0.3 + 0.7 * uGrowth) * uSpread;
  vec3 c = uCenter + dir * rad;
  c += dir * shat * (2.5 + 7.0 * uRelease) * (0.5 + aSeed.x);
  c.y -= shat * shat * 2.0;
  float len = (0.7 + 1.3 * aSeed.z) * gi * (1.0 - 0.6 * smoothstep(0.0, 1.4, shat)) * uSpread;
  float wid = (0.22 + 0.2 * aSeed.y) * (0.6 + 0.4 * uSpread);
  vec3 lp = position * vec3(wid, len, wid);
  mat3 R = rotY(aSeed.y * 6.28 + uTime * (0.15 + 0.4 * aSeed.w) + shat * 5.0 * aSeed.x) * rotX(el * 0.8 + aSeed.x * 3.0 + shat * 4.0);
  vec3 p = c + R * lp;
  vec4 world = modelMatrix * vec4(p, 1.0);
  vN = normalize(mat3(modelMatrix) * (R * normal));
  vView = cameraPosition - world.xyz;
  vAlpha = vis; vSeed = aSeed.x;
  gl_Position = projectionMatrix * viewMatrix * world;
}`;
const SHARD_FRAG = /* glsl */ `
uniform vec3 uColor, uGold;
varying vec3 vN;
varying vec3 vView;
varying float vAlpha;
varying float vSeed;
vec3 film(float x) { return 0.5 + 0.5 * cos(6.2831853 * (x + vec3(0.0, 0.33, 0.67))); }
void main() {
  vec3 Nn = normalize(vN);
  vec3 V = normalize(vView);
  float ndv = abs(dot(Nn, V));
  float fres = pow(max(1.0 - ndv, 0.0), 2.5);
  float lit = 0.35 + 0.65 * max(dot(Nn, normalize(vec3(-0.4, 0.8, 0.5))), 0.0);
  vec3 col = mix(uGold, uColor, 0.7) * (0.18 + 0.5 * lit) + uColor * fres * 1.1 + film(fres * 1.5 + vSeed) * fres * 0.12;
  float lu = dot(col, vec3(0.2126, 0.7152, 0.0722));
  col *= min(1.0, 0.85 / max(lu, 1e-4));
  float a = vAlpha * (0.45 + 0.5 * fres);
  gl_FragColor = vec4(col * a, a);
}`;

// ------------------------------------------------------------------------------------------- geometry helpers --
// a minimal merge (non-indexed position/normal/uv), so the module needs no addon import
function mergeGeometries(THREE, list) {
  const flat = list.map((g) => (g.index ? g.toNonIndexed() : g));
  let count = 0;
  for (const g of flat) count += g.attributes.position.count;
  const pos = new Float32Array(count * 3), nor = new Float32Array(count * 3), uv = new Float32Array(count * 2);
  let o = 0;
  for (const g of flat) {
    if (!g.attributes.normal) g.computeVertexNormals();
    pos.set(g.attributes.position.array, o * 3);
    nor.set(g.attributes.normal.array, o * 3);
    if (g.attributes.uv) uv.set(g.attributes.uv.array, o * 2);
    o += g.attributes.position.count;
  }
  for (let k = 0; k < flat.length; k++) if (flat[k] !== list[k]) flat[k].dispose();
  for (const g of list) g.dispose();
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  out.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
  out.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  return out;
}

// value-noise texture for the haze (two independent channels), tileable
function noiseTexture(THREE, size = 128) {
  const data = new Uint8Array(size * size * 4);
  let h = 4242;
  const rnd = () => ((h = (h * 16807) % 2147483647) / 2147483647);
  const grid = 8, cells = size / grid;
  const lat = [new Float32Array(cells * cells), new Float32Array(cells * cells)];
  for (const l of lat) for (let i = 0; i < l.length; i++) l[i] = rnd();
  const smooth = (t) => t * t * (3 - 2 * t);
  const sample = (l, x, y) => {
    const cx = Math.floor(x / grid), cy = Math.floor(y / grid), fx = smooth((x % grid) / grid), fy = smooth((y % grid) / grid);
    const at = (i, j) => l[((j % cells) + cells) % cells * cells + ((i % cells) + cells) % cells];
    return lerp(lerp(at(cx, cy), at(cx + 1, cy), fx), lerp(at(cx, cy + 1), at(cx + 1, cy + 1), fx), fy);
  };
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const o = (y * size + x) * 4;
    // two octaves each, wrapped
    const a = 0.65 * sample(lat[0], x, y) + 0.35 * sample(lat[0], (x * 2) % size, (y * 2) % size);
    const b = 0.65 * sample(lat[1], x, y) + 0.35 * sample(lat[1], (x * 2) % size, (y * 2) % size);
    data[o] = Math.round(clamp(a, 0, 1) * 255); data[o + 1] = Math.round(clamp(b, 0, 1) * 255); data[o + 2] = 128; data[o + 3] = 255;
  }
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat, THREE.UnsignedByteType);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.magFilter = tex.minFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return tex;
}

// ------------------------------------------------------------------------------------------- the instrument --
function create(ctx) {
  const { THREE, isBlack } = ctx;
  const keyX = ctx.keyX;
  const noteColor = ctx.noteColor || ((m, vel, target) => target.setHSL(((m % 12) * 7 % 12) / 12, 0.9, 0.5));
  const S = ctx.span || {};
  const left = S.left ?? keyX(FIRST) - 0.5, right = S.right ?? keyX(FIRST + N - 1) + 0.5;
  const top = S.keyTop ?? 0;
  const cx = (left + right) / 2, k = (right - left) / 52;   // host units per canonical unit (1 on the page)
  const kx = (m) => (keyX(m) - cx) / k;                      // a key's centre in the creature's own space

  const group = new THREE.Group();
  group.name = "instrument:" + ID;
  group.position.set(cx, top, 0);
  group.scale.setScalar(k);
  const geos = [], mats = [], texs = [], instanced = [];
  const own = (x, list) => (list.push(x), x);

  const feel = createHarmonyFeel();
  const moment = createMoment();

  // ---------------------------------------------------------------- the body's radius along its length --
  const bodyR = (x) => {
    const u = x - SPINE.x0;
    if (u < HEAD_LEN) return 1.9;
    if (u < THORAX_END) { const w = (u - HEAD_LEN) / (THORAX_END - HEAD_LEN); return 1.85 + 0.95 * Math.sin(Math.PI * Math.pow(w, 0.8)) - 0.25 * w; }
    const v = clamp((u - THORAX_END) / (SPINE.x1 - SPINE.x0 - THORAX_END), 0, 1);
    return lerp(1.6, 0.42, Math.pow(v, 0.9));
  };

  // ---------------------------------------------------------------- per-note layout --
  const len = new Float32Array(N), chord = new Float32Array(N), ampMax = new Float32Array(N), pitch = new Float32Array(N);
  const seed = new Float32Array(N), vibHz = new Float32Array(N), ghostHz = new Float32Array(N), restSweep = new Float32Array(N);
  const rootX = new Float32Array(N), rootY = new Float32Array(N), rootZ = new Float32Array(N), pistonZ = new Float32Array(N), hitY = new Float32Array(N);
  const tauPrompt = new Float32Array(N), tauAfter = new Float32Array(N);
  const wingMid = new Float32Array(N * 3);   // a point half-way up each wing, where the braid attaches
  for (let i = 0; i < N; i++) {
    const m = FIRST + i, n = i / (N - 1), b = isBlack(m), lo = 1 - n;
    pitch[i] = n;
    len[i] = WING.lenTreble + (WING.lenBass - WING.lenTreble) * Math.pow(lo, WING.lenPow) * (b ? 0.97 : 1);
    chord[i] = (WING.chordTreble + (WING.chordBass - WING.chordTreble) * Math.pow(lo, WING.chordPow)) * (b ? WING.hindChord : 1);
    ampMax[i] = (AMP_TREBLE + (AMP_BASS - AMP_TREBLE) * Math.pow(lo, AMP_POW)) * DEG;
    seed[i] = (Math.sin(m * 12.9898) * 43758.5453) % 1;
    if (seed[i] < 0) seed[i] += 1;
    vibHz[i] = overPitch(m, VIB_HZ_BASS, VIB_HZ_TREBLE);
    ghostHz[i] = overPitch(m, GHOST_HZ_BASS, GHOST_HZ_TREBLE);
    restSweep[i] = b ? WING.hindRestSweep : WING.restSweep;
    tauPrompt[i] = overPitch(m, TAU_PROMPT_BASS, TAU_PROMPT_TREBLE);
    tauAfter[i] = overPitch(m, TAU_AFTER_BASS, TAU_AFTER_TREBLE);
    const x = kx(m), r = bodyR(x);
    rootX[i] = x;
    rootY[i] = SPINE.y + r * 0.86 + 0.12;
    rootZ[i] = SPINE.z + (b ? -0.55 : 0.45) * r;
    pistonZ[i] = SPINE.z + r + (b ? 0.25 : 0.7);
    hitY[i] = rootY[i] - PISTON.gap;
  }

  // ---------------------------------------------------------------- materials --
  const chitinU = { uTime: { value: 0 }, uBreath: { value: 0.05 }, uBreathRate: { value: 1.2 } };
  const chitin = own(new THREE.MeshStandardMaterial({ color: 0x2a1b0b, roughness: 0.5, metalness: 0.42, flatShading: true }), mats);
  const shadow = own(new THREE.MeshStandardMaterial({ color: 0x0e0905, roughness: 0.62, metalness: 0.25 }), mats);
  const lensMat = own(new THREE.MeshStandardMaterial({ color: 0x1a1109, roughness: 0.18, metalness: 0.8, emissive: 0x000000 }), mats);

  // ---------------------------------------------------------------- the creature (one draw) --
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const rod = (a, b, r0, r1, seg = 7) => {
    const dir = new THREE.Vector3().subVectors(b, a);
    const g = new THREE.CylinderGeometry(r1, r0, dir.length(), seg, 1, false);
    g.translate(0, dir.length() / 2, 0);
    g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize()));
    g.translate(a.x, a.y, a.z);
    return g;
  };
  const ball = (p, r, w = 8, h = 6) => { const g = new THREE.SphereGeometry(r, w, h); g.translate(p.x, p.y, p.z); return g; };
  // a jointed leg: coxa out of the body, femur up to a knee, tibia down to the floor, a flat tarsus
  const leg = (parts, hip, side, reach, kneeUp, kneeOut, foot) => {
    const knee = V(hip.x + side * kneeOut, hip.y + kneeUp, hip.z + reach * 0.45);
    const ankle = V(hip.x + side * (kneeOut + 0.4), FLOOR_Y + 0.35, hip.z + reach);
    const toe = V(ankle.x + side * 0.9, FLOOR_Y + 0.05, ankle.z + foot);
    parts.push(rod(hip, knee, 0.46, 0.28, 6), ball(knee, 0.34), rod(knee, ankle, 0.26, 0.12, 6), ball(ankle, 0.18, 6, 5), rod(ankle, toe, 0.12, 0.05, 5));
  };
  {
    const parts = [];
    // abdomen + thorax + head as one lathe: the profile bulges once per segment, swells at the thorax, rounds at both ends
    const pts = [];
    const K = 320;
    let phase = 0, prevX = SPINE.x0;
    for (let q = 0; q <= K; q++) {
      const x = SPINE.x0 + (SPINE.x1 - SPINE.x0) * (q / K);
      const u = x - SPINE.x0;
      let r = bodyR(x);
      if (u > THORAX_END) {                                     // abdomen: nine bulging segments, shortening toward the tail
        const v = (u - THORAX_END) / (SPINE.x1 - SPINE.x0 - THORAX_END);
        phase += (x - prevX) / lerp(4.4, 2.2, v);
        const f = phase % 1;
        r *= 0.8 + 0.2 * Math.pow(Math.sin(Math.PI * f), 0.45);
      } else if (u > HEAD_LEN) {                                // thorax: three plates
        const w = (u - HEAD_LEN) / (THORAX_END - HEAD_LEN);
        r *= 0.93 + 0.07 * Math.pow(Math.abs(Math.sin(Math.PI * w * 3)), 0.5);
      } else {                                                  // head: a rounded cap
        r *= 0.82 + 0.18 * Math.sin(Math.PI * Math.min(u / HEAD_LEN, 1));
      }
      prevX = x;
      const capA = clamp(u / 1.6, 0, 1), capB = clamp((SPINE.x1 - x) / 3.5, 0, 1);
      r *= Math.sqrt(1 - Math.pow(1 - capA, 2)) * Math.pow(capB, 0.55);
      pts.push(new THREE.Vector2(Math.max(r, 0.0001), x));
    }
    const body = new THREE.LatheGeometry(pts, 14);
    body.rotateZ(-Math.PI / 2);
    body.translate(0, SPINE.y, SPINE.z);
    parts.push(body);
    // the head: brow ridge, two mandibles and two antennae reaching forward
    const hx = SPINE.x0 + 1.4;
    parts.push(rod(V(hx - 0.9, SPINE.y - 0.5, SPINE.z + 0.55), V(hx - 2.6, SPINE.y - 1.3, SPINE.z + 0.9), 0.16, 0.04, 5));
    parts.push(rod(V(hx - 0.9, SPINE.y - 0.5, SPINE.z - 0.55), V(hx - 2.6, SPINE.y - 1.3, SPINE.z - 0.9), 0.16, 0.04, 5));
    for (const dz of [-1, 1]) {
      const base = V(hx - 0.6, SPINE.y + 1.1, SPINE.z + dz * 0.7), mid = V(hx - 3.4, SPINE.y + 3.2, SPINE.z + dz * 1.7), tip = V(hx - 6.2, SPINE.y + 3.6, SPINE.z + dz * 2.6);
      parts.push(rod(base, mid, 0.11, 0.06, 5), rod(mid, tip, 0.06, 0.02, 5));
    }
    // cerci: two fine filaments off the tail
    const tail = V(SPINE.x1 - 0.4, SPINE.y, SPINE.z);
    parts.push(rod(tail, V(SPINE.x1 + 3.8, SPINE.y + 0.9, SPINE.z - 0.5), 0.09, 0.012, 5));
    parts.push(rod(tail, V(SPINE.x1 + 3.4, SPINE.y - 0.5, SPINE.z - 1.1), 0.08, 0.012, 5));
    // six legs on the thorax, three a side: the near side steps down under the keybed, the far side back into the dark
    for (const [dx, reach, kneeOut] of [[4.2, 3.6, -1.6], [6.6, 4.4, 0.2], [9.0, 5.2, 2.0]]) {
      const x = SPINE.x0 + dx, r = bodyR(x);
      leg(parts, V(x, SPINE.y - r * 0.35, SPINE.z + r * 0.55), 1, reach, 2.6 + r * 0.6, kneeOut, 0.8);
      leg(parts, V(x, SPINE.y - r * 0.35, SPINE.z - r * 0.55), 1, -reach - 1.5, 2.4 + r * 0.6, kneeOut, -0.8);
    }
    // four prolegs holding the long abdomen up
    for (const x of [-6, 14]) {
      const r = bodyR(x);
      parts.push(rod(V(x, SPINE.y - r * 0.5, SPINE.z + r * 0.4), V(x + 0.4, FLOOR_Y, SPINE.z + 2.6), 0.2, 0.06, 5));
      parts.push(rod(V(x, SPINE.y - r * 0.5, SPINE.z - r * 0.4), V(x + 0.4, FLOOR_Y, SPINE.z - 2.8), 0.2, 0.06, 5));
    }
    const merged = own(mergeGeometries(THREE, parts), geos);
    const mesh = new THREE.Mesh(merged, chitin);
    mesh.name = "body";
    mesh.frustumCulled = false;
    group.add(mesh);
  }
  // the compound lenses: two faceted eyes that take the lowest sounding colour
  {
    const parts = [];
    for (const dz of [-1, 1]) {
      const g = new THREE.IcosahedronGeometry(0.95, 1);
      g.scale(1.0, 0.85, 0.8);
      g.translate(SPINE.x0 + 1.2, SPINE.y + 0.95, SPINE.z + dz * 1.4);
      parts.push(g);
    }
    const merged = own(mergeGeometries(THREE, parts), geos);
    const mesh = new THREE.Mesh(merged, lensMat);
    mesh.name = "lenses";
    mesh.frustumCulled = false;
    group.add(mesh);
  }

  // ---------------------------------------------------------------- keybed and cheeks (one draw) --
  {
    const parts = [];
    const bed = new THREE.BoxGeometry(56.2, 1.3, 7.6);
    bed.translate(0, -1.62, 0.1);
    parts.push(bed);
    for (const side of [-1, 1]) {   // cheeks: mandible crescents holding the key ends
      const s = new THREE.Shape();
      s.moveTo(-3.6, -2.3); s.lineTo(3.7, -2.3);
      s.quadraticCurveTo(4.3, -1.2, 3.4, 0.9);
      s.quadraticCurveTo(0.5, 2.1, -3.8, 1.2);
      s.quadraticCurveTo(-4.4, -0.6, -3.6, -2.3);
      const g = new THREE.ExtrudeGeometry(s, { depth: 1.1, bevelEnabled: true, bevelThickness: 0.18, bevelSize: 0.16, bevelSegments: 2, curveSegments: 10 });
      g.rotateY(Math.PI / 2);
      g.translate(side < 0 ? -28.35 : 27.25, 0, 0);
      parts.push(g);
    }
    const merged = own(mergeGeometries(THREE, parts), geos);
    const mesh = new THREE.Mesh(merged, shadow);
    mesh.name = "keybed";
    mesh.frustumCulled = false;
    group.add(mesh);
  }

  // ---------------------------------------------------------------- pistons (the hammers) --
  const pistonGeo = own((() => {
    const prof = [[0.0001, -3.2], [0.065, -3.1], [0.095, -2.7], [0.06, -2.4], [0.105, -2.15], [0.125, -1.8],
                  [0.07, -1.55], [0.13, -1.3], [0.15, -0.95], [0.085, -0.72], [0.145, -0.52], [0.165, -0.3],
                  [0.135, -0.12], [0.07, -0.02], [0.0001, 0]].map(([r, y]) => new THREE.Vector2(r, y));
    return new THREE.LatheGeometry(prof, 10);
  })(), geos);
  const pistonMat = own(new THREE.MeshStandardMaterial({ color: 0x4a3316, roughness: 0.4, metalness: 0.5 }), mats);
  const pistonGlow = new THREE.InstancedBufferAttribute(new Float32Array(N * 3), 3);
  pistonGlow.setUsage(THREE.DynamicDrawUsage);
  pistonGeo.setAttribute("aGlow", pistonGlow);
  pistonMat.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nattribute vec3 aGlow;\nvarying vec3 vGlow;\nvarying float vTipY;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvGlow = aGlow;\nvTipY = position.y;");
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vGlow;\nvarying float vTipY;")
      .replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += vGlow * smoothstep(-0.5, -0.05, vTipY);");
  };
  pistonMat.customProgramCacheKey = () => ID + "-piston";
  const pistons = own(new THREE.InstancedMesh(pistonGeo, pistonMat, N), instanced);
  pistons.name = "pistons";
  pistons.frustumCulled = false;
  pistons.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  group.add(pistons);

  // ---------------------------------------------------------------- clasps (the dampers) --
  const claspGeo = own((() => {
    const g = new THREE.CylinderGeometry(0.22, 0.3, 0.66, 8, 1, false, -Math.PI * 0.5, Math.PI);
    g.translate(0, 0.33, 0);
    return g;
  })(), geos);
  const clasps = own(new THREE.InstancedMesh(claspGeo, shadow, N), instanced);
  clasps.name = "clasps";
  clasps.frustumCulled = false;
  clasps.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  group.add(clasps);

  // ---------------------------------------------------------------- wings --
  const wingGeo = own(new THREE.PlaneGeometry(2, 1, 1, 1), geos);
  wingGeo.translate(0, 0.5, 0);
  const aShape = new THREE.InstancedBufferAttribute(new Float32Array(N * 4), 4);
  const aState = new THREE.InstancedBufferAttribute(new Float32Array(N * 4), 4);
  const aStrike = new THREE.InstancedBufferAttribute(new Float32Array(N * 4), 4);
  const aColor = new THREE.InstancedBufferAttribute(new Float32Array(N * 3), 3);
  for (const a of [aState, aStrike, aColor]) a.setUsage(THREE.DynamicDrawUsage);
  wingGeo.setAttribute("aShape", aShape);
  wingGeo.setAttribute("aState", aState);
  wingGeo.setAttribute("aStrike", aStrike);
  wingGeo.setAttribute("aColor", aColor);
  const stateArr = aState.array, strikeArr = aStrike.array, colArr = aColor.array;
  const GOLD = new THREE.Color(0.95, 0.66, 0.3), STEEL = new THREE.Color(0.55, 0.66, 0.85);
  const EDGE_WARM = new THREE.Color(0.044, 0.05, 0.07), EDGE_COLD = new THREE.Color(0.03, 0.05, 0.11);
  const wingUniforms = {
    uTime: { value: 0 }, uBend: { value: WING.bend }, uMaxChannel: { value: LIGHT.maxChannel },
    uIrid: { value: 0 }, uStill: { value: 1 },
    uGold: { value: GOLD.clone() }, uSmoke: { value: new THREE.Color(0.005, 0.0034, 0.0018) }, uCool: { value: EDGE_WARM.clone() },
    uLight: { value: new THREE.Vector4(LIGHT.membrane, LIGHT.vein, LIGHT.ptero, LIGHT.flashTravel) },
    uKnuckle: { value: new THREE.Vector4(KNUCKLE.across, KNUCKLE.along, KNUCKLE.width, KNUCKLE.gain) },
  };
  const membraneMat = own(new THREE.ShaderMaterial({
    vertexShader: WING_VERT, fragmentShader: WING_FRAG, uniforms: wingUniforms,
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
  }), mats);
  const lightMat = own(new THREE.ShaderMaterial({
    vertexShader: WING_VERT, fragmentShader: WING_FRAG, uniforms: wingUniforms, defines: { LIGHT_PASS: 1 },
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    blending: THREE.CustomBlending, blendEquation: THREE.MaxEquation,   // overlapping wings never stack their light
    blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
  }), mats);
  membraneMat.customProgramCacheKey = () => ID + "-membrane";
  lightMat.customProgramCacheKey = () => ID + "-light";
  const membranes = own(new THREE.InstancedMesh(wingGeo, membraneMat, N), instanced);
  const lights = own(new THREE.InstancedMesh(wingGeo, lightMat, N), instanced);
  membranes.name = "wing-membranes";
  lights.name = "wing-light";
  membranes.frustumCulled = lights.frustumCulled = false;
  membranes.renderOrder = 2;
  lights.renderOrder = 3;
  {
    const mat = new THREE.Matrix4(), rx = new THREE.Matrix4(), rz = new THREE.Matrix4(), up = new THREE.Vector3();
    for (let i = 0; i < N; i++) {
      const m = FIRST + i, n = pitch[i], lo = 1 - n, b = isBlack(m);
      const lean = WING.leanBass * Math.pow(lo, 1.3) + WING.leanTreble * Math.pow(n, 1.6) + (b ? WING.hindLean : 0);
      const back = lerp(WING.backTreble, WING.backBass, lo) + (b ? WING.hindBack : 0);
      rx.makeRotationX(-back);
      rz.makeRotationZ(lean);
      mat.multiplyMatrices(rx, rz);
      mat.setPosition(rootX[i], rootY[i], rootZ[i]);
      membranes.setMatrixAt(i, mat);
      lights.setMatrixAt(i, mat);
      aShape.setXYZW(i, len[i], chord[i], n, seed[i]);
      up.set(0, 1, 0).transformDirection(mat);
      wingMid[i * 3] = rootX[i] + up.x * len[i] * 0.5; wingMid[i * 3 + 1] = rootY[i] + up.y * len[i] * 0.5; wingMid[i * 3 + 2] = rootZ[i] + up.z * len[i] * 0.5;
    }
  }
  group.add(membranes, lights);

  // ---------------------------------------------------------------- dust in the wing wash --
  const WASH_W = 88;
  const washData = new Float32Array(WASH_W * 4);
  const washTex = own(new THREE.DataTexture(washData, WASH_W, 1, THREE.RGBAFormat, THREE.FloatType), texs);
  washTex.magFilter = washTex.minFilter = THREE.LinearFilter;
  washTex.needsUpdate = true;
  // the beating wings spill their colour onto the body under them, and the whole creature breathes: a peristaltic wave
  // along the body whose depth and rate follow the moment's energy
  chitin.onBeforeCompile = (sh) => {
    sh.uniforms.uWash = { value: washTex };
    sh.uniforms.uTime = chitinU.uTime;
    sh.uniforms.uBreath = chitinU.uBreath;
    sh.uniforms.uBreathRate = chitinU.uBreathRate;
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vWorld;\nuniform float uTime, uBreath, uBreathRate;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\ntransformed += objectNormal * uBreath * (0.5 + 0.5 * sin(uTime * uBreathRate - position.x * 0.32)) * smoothstep(-9.0, -6.0, position.y);\nvWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;");
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vWorld;\nuniform sampler2D uWash;")
      .replace("#include <emissivemap_fragment>",
               "#include <emissivemap_fragment>\n" +
               "vec4 wash = texture2D(uWash, vec2(clamp((vWorld.x + 26.0) / 52.0, 0.0, 1.0), 0.5));\n" +
               "totalEmissiveRadiance += wash.rgb * (0.02 + 0.16 * clamp(normal.y, 0.0, 1.0));");
  };
  chitin.customProgramCacheKey = () => ID + "-chitin";
  const DUST_N = 1800;
  const dustGeo = own(new THREE.BufferGeometry(), geos);
  {
    const seeds = new Float32Array(DUST_N * 4);
    let h = 1337;
    const rnd = () => ((h = (h * 16807) % 2147483647) / 2147483647);
    for (let q = 0; q < DUST_N * 4; q++) seeds[q] = rnd();
    dustGeo.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 4));
    dustGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(DUST_N * 3), 3));
  }
  const dustUniforms = { uTime: { value: 0 }, uWash: { value: washTex }, uPx: { value: 1000 }, uStir: { value: 0 }, uSand: { value: new THREE.Color(0.9, 0.62, 0.3) } };
  const dustMat = own(new THREE.ShaderMaterial({
    vertexShader: DUST_VERT, fragmentShader: DUST_FRAG, uniforms: dustUniforms, transparent: true, depthWrite: false,
    blending: THREE.CustomBlending, blendEquation: THREE.MaxEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
  }), mats);
  dustMat.customProgramCacheKey = () => ID + "-dust";
  const dust = new THREE.Points(dustGeo, dustMat);
  dust.name = "dust";
  dust.frustumCulled = false;
  dust.renderOrder = 4;
  group.add(dust);

  // ---------------------------------------------------------------- the sand haze (four quads, one draw) --
  const noiseTex = own(noiseTexture(THREE), texs);
  const HAZE_N = 4;
  const hazeGeo = own(new THREE.BufferGeometry(), geos);
  {
    const pos = new Float32Array(HAZE_N * 4 * 3), quad = new Float32Array(HAZE_N * 4 * 3), idx = new Uint16Array(HAZE_N * 6);
    let h = 99;
    const rnd = () => ((h = (h * 16807) % 2147483647) / 2147483647);
    for (let q = 0; q < HAZE_N; q++) {
      const sa = rnd(), sb = rnd();
      const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
      for (let c = 0; c < 4; c++) {
        const v = q * 4 + c;
        pos[v * 3] = corners[c][0]; pos[v * 3 + 1] = corners[c][1]; pos[v * 3 + 2] = 0;
        quad[v * 3] = q; quad[v * 3 + 1] = sa; quad[v * 3 + 2] = sb;
      }
      idx.set([q * 4, q * 4 + 1, q * 4 + 2, q * 4, q * 4 + 2, q * 4 + 3], q * 6);
    }
    hazeGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    hazeGeo.setAttribute("aQuad", new THREE.BufferAttribute(quad, 3));
    hazeGeo.setIndex(new THREE.BufferAttribute(idx, 1));
  }
  const hazeUniforms = { uTime: { value: 0 }, uHaze: { value: 0 }, uEnergy: { value: 0 }, uNoise: { value: noiseTex },
    uOrigin: { value: new THREE.Vector3(SPINE.x0 + 6, SPINE.y, SPINE.z) }, uHazeColor: { value: new THREE.Color(0.5, 0.4, 0.25) } };
  const hazeMat = own(new THREE.ShaderMaterial({
    vertexShader: HAZE_VERT, fragmentShader: HAZE_FRAG, uniforms: hazeUniforms, transparent: true, depthWrite: false, side: THREE.DoubleSide,
    blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
  }), mats);
  hazeMat.customProgramCacheKey = () => ID + "-haze";
  const haze = new THREE.Mesh(hazeGeo, hazeMat);
  haze.name = "haze";
  haze.frustumCulled = false;
  haze.renderOrder = 1;
  group.add(haze);

  // ---------------------------------------------------------------- the braid (bass to solo, one draw) --
  const BRAID_SEG = 56;
  const braidGeo = own(new THREE.BufferGeometry(), geos);
  {
    const verts = 2 * (BRAID_SEG + 1) * 2;
    const pos = new Float32Array(verts * 3), idx = new Uint16Array(2 * BRAID_SEG * 6);
    let vi = 0, ii = 0;
    for (let strand = 0; strand < 2; strand++) {
      const base = vi;
      for (let s = 0; s <= BRAID_SEG; s++) for (let side = -1; side <= 1; side += 2) {
        pos[vi * 3] = s / BRAID_SEG; pos[vi * 3 + 1] = side; pos[vi * 3 + 2] = strand; vi++;
      }
      for (let s = 0; s < BRAID_SEG; s++) {
        const a = base + s * 2;
        idx[ii++] = a; idx[ii++] = a + 2; idx[ii++] = a + 1; idx[ii++] = a + 1; idx[ii++] = a + 2; idx[ii++] = a + 3;
      }
    }
    braidGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    braidGeo.setIndex(new THREE.BufferAttribute(idx, 1));
  }
  const braidUniforms = { uA: { value: new THREE.Vector3() }, uB: { value: new THREE.Vector3() }, uRes: { value: new THREE.Vector2(1920, 1080) },
    uTwist: { value: 1.5 }, uPhase: { value: 0 }, uRadius: { value: 0.4 }, uSag: { value: -0.8 }, uPx: { value: 1.6 }, uLevel: { value: 0 },
    uColor: { value: new THREE.Color(1, 0.75, 0.35) } };
  const braidMat = own(new THREE.ShaderMaterial({
    vertexShader: BRAID_VERT, fragmentShader: BRAID_FRAG, uniforms: braidUniforms, transparent: true, depthWrite: false, side: THREE.DoubleSide,
    blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
  }), mats);
  braidMat.customProgramCacheKey = () => ID + "-braid";
  const braid = new THREE.Mesh(braidGeo, braidMat);
  braid.name = "braid";
  braid.frustumCulled = false;
  braid.renderOrder = 5;
  group.add(braid);
  const viewport = new THREE.Vector4();
  braid.onBeforeRender = (renderer, scene, camera) => {          // the pass actually drawing: its own size and lens
    renderer.getCurrentViewport(viewport);
    braidUniforms.uRes.value.set(viewport.z, viewport.w);
    braidUniforms.uPx.value = Math.max(1.2, viewport.w * 0.0015);
    dustUniforms.uPx.value = viewport.w * camera.projectionMatrix.elements[5] * 0.5;
  };

  // ---------------------------------------------------------------- the artifact (two shard clusters, two draws) --
  const SHARDS = 30;
  const shardGeo = own(new THREE.IcosahedronGeometry(1, 0), geos);
  {
    const seeds = new Float32Array(SHARDS * 4);
    let h = 777;
    const rnd = () => ((h = (h * 16807) % 2147483647) / 2147483647);
    for (let q = 0; q < SHARDS * 4; q++) seeds[q] = rnd();
    shardGeo.setAttribute("aSeed", new THREE.InstancedBufferAttribute(seeds, 4));
  }
  const shardShared = { uTime: { value: 0 }, uGold: { value: GOLD.clone() } };
  const artifacts = [];
  for (let a = 0; a < 2; a++) {
    const u = { uTime: shardShared.uTime, uGold: shardShared.uGold, uGrowth: { value: 0 }, uShatter: { value: -1 }, uRelease: { value: 0 }, uSpread: { value: 1 },
      uCenter: { value: new THREE.Vector3(0, SPINE.y + 3, SPINE.z) }, uColor: { value: new THREE.Color(0.9, 0.7, 0.4) } };
    const mat = own(new THREE.ShaderMaterial({
      vertexShader: SHARD_VERT, fragmentShader: SHARD_FRAG, uniforms: u, transparent: true, depthWrite: false, side: THREE.DoubleSide,
      blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
    }), mats);
    mat.customProgramCacheKey = () => ID + "-shard";
    const mesh = own(new THREE.InstancedMesh(shardGeo, mat, SHARDS), instanced);
    mesh.name = "artifact-" + a;
    mesh.frustumCulled = false;
    mesh.renderOrder = 4;
    group.add(mesh);
    artifacts.push(u);
  }

  // ---------------------------------------------------------------- stage pool --
  const poolGeo = own(new THREE.PlaneGeometry(120, 70, 1, 1), geos);
  const poolUniforms = { uSand: { value: new THREE.Color(0.05, 0.03, 0.012) }, uTint: { value: new THREE.Color(0, 0, 0) }, uBreath: { value: 0 } };
  const poolMat = own(new THREE.ShaderMaterial({
    vertexShader: POOL_VERT, fragmentShader: POOL_FRAG, uniforms: poolUniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }), mats);
  poolMat.customProgramCacheKey = () => ID + "-pool";
  const pool = new THREE.Mesh(poolGeo, poolMat);
  pool.rotation.x = -Math.PI / 2;
  pool.position.set(0, FLOOR_Y + 0.02, -6);
  pool.name = "pool";
  pool.frustumCulled = false;
  group.add(pool);

  if (ctx.scene) ctx.scene.add(group);

  // ---------------------------------------------------------------- per-note live state (preallocated) --
  // The envelope is integrated, not recomputed from the strike clock: a re-strike carries the level it finds, a sound's end
  // fades instead of snapping, and a pedal press never resurrects a note that is over.
  const bFloor = new Float32Array(N), bPrompt = new Float32Array(N), bAfter = new Float32Array(N), body = new Float32Array(N);
  const flash = new Float32Array(N), vibGate = new Float32Array(N), dampT = new Float32Array(N), stand = new Float32Array(N);
  const vel01 = new Float32Array(N), strikeT = new Float64Array(N).fill(-1e9), phase = new Float32Array(N), flinchSign = new Float32Array(N);
  const pistonH = new Float32Array(N).fill(PISTON.rest), pistonV = new Float32Array(N), claspOpen = new Float32Array(N);
  const rgb = new Float32Array(N * 3);
  const held = new Uint8Array(N), alive = new Uint8Array(N);
  const seenStrike = new Float64Array(N).fill(-1);            // state.sounding's per-key strike counter, last acted on
  const lastNote = new Float64Array(N).fill(-Infinity);        // the strike ring's high-water mark per key
  const lastT0 = new Float64Array(N).fill(-1);                 // the fallback host: a pressed entry's strike time
  for (let i = 0; i < N; i++) { phase[i] = seed[i] * Math.PI * 2; flinchSign[i] = seed[i] > 0.5 ? 1 : -1; }
  // doubles that live across frames or are read inside the Map walk sit in a typed array (a closure double would box)
  const D = new Float64Array(24);
  const T = 0, FIRST_FRAME = 1, LENS_R = 2, LENS_G = 3, LENS_B = 4, POOL_R = 5, POOL_G = 6, POOL_B = 7, HAZE = 8, IRID = 9, COOL = 10,
    STILL = 11, BRAID_LVL = 12, CONTRARY = 13, ART_CUR = 14, SHAT_A = 15, SHAT_B = 16, BREATH = 17, STIR = 18, ART_X = 19, ART_Y = 20;
  D[STILL] = 1; D[SHAT_A] = -1; D[SHAT_B] = -1; D[ART_X] = 0; D[ART_Y] = SPINE.y + 3;
  const braidA = new Float32Array(3), braidB = new Float32Array(3);
  const tmpColor = new THREE.Color();
  let active = true, framing = ctx.framing || null, seeded = false, pedalDown = false;

  const pArr = pistons.instanceMatrix.array, cArr = clasps.instanceMatrix.array, glowArr = pistonGlow.array;
  const writePiston = (i) => {
    const o = i * 16;
    pArr[o] = 1; pArr[o + 5] = 1; pArr[o + 10] = 1; pArr[o + 15] = 1;
    pArr[o + 12] = rootX[i]; pArr[o + 13] = pistonH[i]; pArr[o + 14] = pistonZ[i];
  };
  const writeClasp = (i) => {
    const ang = -0.15 - claspOpen[i] * 0.75, c = Math.cos(ang), s = Math.sin(ang), o = i * 16;
    cArr[o] = 1; cArr[o + 5] = c; cArr[o + 6] = s; cArr[o + 9] = -s; cArr[o + 10] = c; cArr[o + 15] = 1;
    cArr[o + 12] = rootX[i]; cArr[o + 13] = rootY[i] - 0.28; cArr[o + 14] = rootZ[i] + (isBlack(FIRST + i) ? -0.12 : 0.1);
  };
  for (let i = 0; i < N; i++) { writePiston(i); writeClasp(i); }

  // age > 0 seeds a sound already ringing when the creature was mounted. A strike never dips the light to dark first:
  // whatever is still showing above the new peak is folded into the prompt term and decays from there.
  function strike(i, vel, age) {
    const v = clamp(vel / 127, 0, 1);
    const peak = Math.pow(v, PEAK_EXP);
    const fl = peak * lerp(FLOOR_LO, FLOOR_HI, v);
    const above = peak - fl;
    const carry = Math.max(0, body[i] - peak);
    bFloor[i] = fl;
    bPrompt[i] = (above * (1 - AFTER_SHARE) + carry) * Math.exp(-age / tauPrompt[i]);
    bAfter[i] = above * AFTER_SHARE * Math.exp(-age / tauAfter[i]);
    body[i] = bFloor[i] + bPrompt[i] + bAfter[i];
    flash[i] = Math.max(flash[i], Math.pow(v, FLASH_EXP) * Math.exp(-age / TAU_FLASH));
    vibGate[i] = 1;
    dampT[i] = 0;
    vel01[i] = v;
    strikeT[i] = D[T] - age;
    if (age < 0.25) pistonV[i] = lerp(PISTON.vSoft, PISTON.vHard, v);   // the piston fires (a late-reported strike does not)
    noteColor(FIRST + i, vel, tmpColor);
    rgb[i * 3] = tmpColor.r; rgb[i * 3 + 1] = tmpColor.g; rgb[i * 3 + 2] = tmpColor.b;
  }
  // one sounding entry (Map.forEach: no per-entry allocation)
  function visitSound(e, m) {
    const i = m - FIRST;
    if (i < 0 || i >= N || !e) return;
    alive[i] = 1;
    held[i] = e.held ? 1 : 0;
    if (e.strike !== seenStrike[i]) {
      seenStrike[i] = e.strike;
      strike(i, e.vel, D[FIRST_FRAME] ? Math.max(0, D[T] - e.t0) : 0);   // a mid-chord mount picks the sound up where it is
      if (e.t0 > lastNote[i]) lastNote[i] = e.t0;
    }
  }
  function visitPressed(e, m) {   // an older host: fingers, and a strike on a new t
    const i = m - FIRST;
    if (i < 0 || i >= N || !e) return;
    alive[i] = 1; held[i] = 1;
    const t0 = typeof e.t === "number" ? e.t : typeof e.t0 === "number" ? e.t0 : D[T];
    if (t0 !== lastT0[i]) { lastT0[i] = t0; strike(i, e.vel ?? 90, D[FIRST_FRAME] ? Math.max(0, D[T] - t0) : 0); if (t0 > lastNote[i]) lastNote[i] = t0; }
  }

  function update(dt, t, state) {
    if (!active) return;
    dt = clamp(dt || 0, 0, 0.1);
    D[T] = t;
    D[FIRST_FRAME] = seeded ? 0 : 1;
    const first = !seeded;
    seeded = true;
    const f = feel.update(state, dt, t);
    const mo = moment.update(state, dt, t, f);
    held.fill(0);
    alive.fill(0);
    pedalDown = !!(state && state.pedal);
    const sounding = state ? state.sounding ?? null : null;
    if (sounding) sounding.forEach(visitSound);
    else if (state && state.pressed) {
      state.pressed.forEach(visitPressed);
      for (let i = 0; i < N; i++) if (!alive[i] && pedalDown && body[i] > 0 && dampT[i] === 0) alive[i] = 1;
    }
    // the strike ring: the only place a note struck and released inside one frame shows at all
    if (state && state.notes) {
      const notes = state.notes;
      for (let q = 0; q < notes.length; q++) {
        const n = notes[q], i = n.midi - FIRST;
        if (i < 0 || i >= N || !(n.t > lastNote[i])) continue;
        lastNote[i] = n.t;
        if (!first) strike(i, n.vel, Math.max(0, t - n.t));
      }
    }

    // ---- the material and the moment, before the wings read them
    const C = f.colour, Dn = f.dance, Vc = f.voices;
    const tension = C.tension, lush = C.lushness, still = C.simplicity;
    const kSlow = 1 - Math.exp(-dt / 0.35);
    D[IRID] += (lush - D[IRID]) * kSlow;
    D[COOL] += (tension - D[COOL]) * kSlow;
    D[STILL] += (still - D[STILL]) * kSlow;
    const hazeTarget = lush * lush * (0.4 + 0.6 * mo.energy) + 0.35 * lush;
    D[HAZE] += (hazeTarget - D[HAZE]) * (1 - Math.exp(-dt / (hazeTarget > D[HAZE] ? 1.2 : 2.0)));
    D[BREATH] += (0.04 + 0.22 * mo.energy - D[BREATH]) * kSlow;
    D[STIR] += (mo.energy - D[STIR]) * kSlow;
    wingUniforms.uIrid.value = D[IRID];
    wingUniforms.uStill.value = D[STILL];
    wingUniforms.uGold.value.copy(GOLD).lerp(STEEL, D[COOL] * 0.7);
    shardShared.uGold.value.copy(wingUniforms.uGold.value);
    wingUniforms.uCool.value.copy(EDGE_WARM).lerp(EDGE_COLD, D[COOL]);
    wingUniforms.uTime.value = t;
    dustUniforms.uTime.value = t;
    dustUniforms.uStir.value = D[STIR];
    chitinU.uTime.value = t;
    chitinU.uBreath.value = D[BREATH];
    chitinU.uBreathRate.value = 1.2 + 2.0 * D[STIR];
    hazeUniforms.uTime.value = t;
    hazeUniforms.uEnergy.value = D[STIR];
    hazeUniforms.uHaze.value = Math.min(HAZE_MAX, HAZE_MAX * D[HAZE] * (0.85 + 0.15 * Math.sin(t * 0.6)));
    const warm = clamp((mo.mood.valence + 1) * 0.5, 0, 1);
    hazeUniforms.uHazeColor.value.setRGB(lerp(0.30, 0.80, warm), lerp(0.36, 0.60, warm), lerp(0.55, 0.34, warm)).lerp(wingUniforms.uCool.value, D[COOL] * 0.5);
    poolUniforms.uBreath.value = D[STIR];
    shardShared.uTime.value = t;
    const tighten = 1 + 0.6 * D[COOL];   // tension tightens the beat

    const kFlash = Math.exp(-dt / TAU_FLASH), kDamp = Math.exp(-dt / TAU_DAMP), kVibOff = Math.exp(-dt / TAU_VIB_OFF);
    const kUp = 1 - Math.exp(-dt / FOLD_UP), kDown = 1 - Math.exp(-dt / FOLD_DOWN);
    const kClaspUp = 1 - Math.exp(-dt / 0.035), kClaspDown = 1 - Math.exp(-dt / 0.07);
    const tremorDepth = VIB_DEPTH * (1 - 0.6 * D[STILL]);
    let tr = 0, tg = 0, tb = 0, lowest = -1, ar = 0, ag = 0, ab = 0, aw = 0, ax = 0, ay = 0;
    for (let i = 0; i < N; i++) { flash[i] *= kFlash; if (flash[i] < 1e-4) flash[i] = 0; }   // every wing first: the budget reads this frame's values
    for (let i = 0; i < N; i++) {
      // the flash budget: wings flashing together share one flash. The host's bloom sums neighbouring halos and the light
      // pass takes a per-channel max, so ten adjacent knuckles at fff summed to white at the roots. Each wing's flash is
      // divided by (1 + n)^FLASH_SHARE, n the flashing wings within FLASH_REACH semitones, weighted smoothly below
      // FLASH_NEIGH so a neighbour's decay never pops this one.
      let fb = flash[i];
      if (fb > 0) {
        let n = 0;
        const j0 = i < FLASH_REACH ? 0 : i - FLASH_REACH, j1 = i + FLASH_REACH > N - 1 ? N - 1 : i + FLASH_REACH;
        for (let j = j0; j <= j1; j++) if (j !== i && flash[j] > 0) n += flash[j] > FLASH_NEIGH ? 1 : flash[j] / FLASH_NEIGH;
        if (n > 0) fb *= Math.pow(1 + n, -FLASH_SHARE);
      }
      if (alive[i]) {                                   // sounding: the two-stage decay onto a velocity-scaled floor
        bPrompt[i] *= Math.exp(-dt / tauPrompt[i]);
        bAfter[i] *= Math.exp(-dt / tauAfter[i]);
        vibGate[i] = 1;
        if (dampT[i]) dampT[i] = 0;
      } else if (body[i] > 0) {                         // the sound ended: the damper lands, a fade and not a snap
        dampT[i] += dt;
        bFloor[i] *= kDamp; bPrompt[i] *= kDamp; bAfter[i] *= kDamp;
        vibGate[i] *= kVibOff;                          // the ghost and tremor stop before the glow is gone
      }
      let b = bFloor[i] + bPrompt[i] + bAfter[i];
      if (dampT[i] > 0) b *= dampFade(dampT[i]);
      if (b < 1.5e-3) { b = 0; bFloor[i] = 0; bPrompt[i] = 0; bAfter[i] = 0; vibGate[i] = 0; }
      body[i] = b;
      // the wing stands up while its note sounds and folds to rest when it ends
      const st = alive[i] ? 1 : 0;
      stand[i] += (st - stand[i]) * (st > stand[i] ? kUp : kDown);
      const age = t - strikeT[i];
      let level = 0, amp = 0, cen = restSweep[i] * (1 - stand[i]);
      if (b > 0) {
        level = SUS_GAIN * Math.pow(b, LIGHT_EXP);
        const tremor = 1 + tremorDepth * vibGate[i] * Math.sin(t * vibHz[i] * tighten * 6.2832 + seed[i] * 6.2832);
        amp = ampMax[i] * Math.pow(b, AMP_EXP) * tremor;
        cen += ampMax[i] * FLINCH * flinchSign[i] * vibGate[i] * Math.exp(-age / FLINCH_TAU) * Math.cos(age * FLINCH_HZ * 6.2832);
        phase[i] = (phase[i] + dt * ghostHz[i] * tighten * 6.2832) % 6.2832;
        const w = b * (1 - pitch[i]);
        if (lowest < 0) lowest = i;
        tr += rgb[i * 3] * w; tg += rgb[i * 3 + 1] * w; tb += rgb[i * 3 + 2] * w;
      }
      if (alive[i]) { ar += rgb[i * 3] * b; ag += rgb[i * 3 + 1] * b; ab += rgb[i * 3 + 2] * b; aw += b; ax += rootX[i] * b; ay += rootY[i] * b; }
      const o = i * 4;
      stateArr[o] = amp; stateArr[o + 1] = cen; stateArr[o + 2] = phase[i]; stateArr[o + 3] = level;
      strikeArr[o] = age > 0 ? age : 0; strikeArr[o + 1] = vel01[i]; strikeArr[o + 2] = fb * FLASH_GAIN; strikeArr[o + 3] = stand[i];
      colArr[i * 3] = rgb[i * 3]; colArr[i * 3 + 1] = rgb[i * 3 + 1]; colArr[i * 3 + 2] = rgb[i * 3 + 2];
      washData[o] = rgb[i * 3] * level * 0.5; washData[o + 1] = rgb[i * 3 + 1] * level * 0.5; washData[o + 2] = rgb[i * 3 + 2] * level * 0.5;
      washData[o + 3] = Math.min(amp / (14 * DEG), 1);

      // piston: fired at the wing root, rebounds, then rests on its check while the key is held
      const travel = hitY[i] - PISTON.rest;
      const rest = held[i] ? PISTON.rest + PISTON.check * travel : PISTON.rest;
      const acc = -PISTON.k * (pistonH[i] - rest) - PISTON.c * pistonV[i];
      if (pistonV[i] > 0 && pistonH[i] < hitY[i]) pistonV[i] += acc * dt * 0.06;   // free flight on the way up
      else pistonV[i] += acc * dt;
      pistonH[i] += pistonV[i] * dt;
      if (pistonH[i] >= hitY[i]) { pistonH[i] = hitY[i]; pistonV[i] = -Math.abs(pistonV[i]) * PISTON.rebound; }
      writePiston(i);
      const pg = fb * 1.3 + level * 0.22;
      glowArr[i * 3] = rgb[i * 3] * pg; glowArr[i * 3 + 1] = rgb[i * 3 + 1] * pg; glowArr[i * 3 + 2] = rgb[i * 3 + 2] * pg;

      // clasps open while the key is held or the damper pedal is down (the frame shows the pedal; the wings do not move)
      const target = held[i] || pedalDown ? 1 : 0;
      claspOpen[i] += (target - claspOpen[i]) * (target > claspOpen[i] ? kClaspUp : kClaspDown);
      writeClasp(i);
    }
    aState.needsUpdate = true;
    aStrike.needsUpdate = true;
    aColor.needsUpdate = true;
    pistons.instanceMatrix.needsUpdate = true;
    pistonGlow.needsUpdate = true;
    clasps.instanceMatrix.needsUpdate = true;
    washTex.needsUpdate = true;

    // the lenses take the lowest sounding colour; the pool a wash of the bass
    let lr = 0.02, lg = 0.014, lb = 0.008;
    if (lowest >= 0) { const w = 0.1 * stateArr[lowest * 4 + 3]; lr += rgb[lowest * 3] * w; lg += rgb[lowest * 3 + 1] * w; lb += rgb[lowest * 3 + 2] * w; }
    D[LENS_R] += (lr - D[LENS_R]) * 0.1; D[LENS_G] += (lg - D[LENS_G]) * 0.1; D[LENS_B] += (lb - D[LENS_B]) * 0.1;
    lensMat.emissive.setRGB(D[LENS_R], D[LENS_G], D[LENS_B]);
    D[POOL_R] += (tr * 0.012 - D[POOL_R]) * 0.08; D[POOL_G] += (tg * 0.012 - D[POOL_G]) * 0.08; D[POOL_B] += (tb * 0.012 - D[POOL_B]) * 0.08;
    poolUniforms.uTint.value.setRGB(Math.min(D[POOL_R], 0.05), Math.min(D[POOL_G], 0.05), Math.min(D[POOL_B], 0.05));

    // ---- the dance: the filament from the bass wing to the solo wing
    const bassI = Vc.bass === null ? -1 : Vc.bass - FIRST, soloI = Vc.solo === null ? -1 : Vc.solo - FIRST;
    const dancing = bassI >= 0 && bassI < N && soloI >= 0 && soloI < N && soloI !== bassI;
    const kEnd = 1 - Math.exp(-dt / 0.06);
    if (dancing) {
      for (let c = 0; c < 3; c++) {
        braidA[c] += (wingMid[bassI * 3 + c] - braidA[c]) * kEnd;
        braidB[c] += (wingMid[soloI * 3 + c] - braidB[c]) * kEnd;
      }
    }
    D[BRAID_LVL] += ((dancing ? 1 : 0) - D[BRAID_LVL]) * (1 - Math.exp(-dt / (dancing ? 0.1 : 0.35)));
    D[CONTRARY] += ((Dn.motion === "contrary" ? 1 : 0) - D[CONTRARY]) * (1 - Math.exp(-dt / 0.3));
    braidUniforms.uA.value.set(braidA[0], braidA[1], braidA[2]);
    braidUniforms.uB.value.set(braidB[0], braidB[1], braidB[2]);
    braidUniforms.uLevel.value = D[BRAID_LVL] * 0.9;
    braidUniforms.uTwist.value = 1.0 + 4.0 * D[CONTRARY] + 1.0 * Dn.pull;
    braidUniforms.uPhase.value = Dn.phase;
    braidUniforms.uRadius.value = (0.3 + 0.7 * Dn.stretch) * (1 - 0.6 * Dn.pull) + 0.15;
    braidUniforms.uSag.value = -1.2 * (1 - Dn.stretch) * (1 - Dn.pull);
    const cons = Dn.consonance;
    braidUniforms.uColor.value.setRGB(lerp(0.30, 1.0, cons) * 0.8, lerp(0.22, 0.72, cons) * 0.8, lerp(0.95, 0.30, cons) * 0.8);

    // ---- the moment: the sand-glass artifact between the wing roots, the shatter on release
    const A = mo.artifact;
    if (A.released) {                                    // the current cluster flies apart; the other one starts to build
      const cur = D[ART_CUR] | 0;
      const uc = artifacts[cur];
      uc.uShatter.value = 0; uc.uRelease.value = A.releaseStrength;
      D[cur === 0 ? SHAT_A : SHAT_B] = 0;
      D[ART_CUR] = 1 - cur;
      const un = artifacts[1 - cur];
      un.uGrowth.value = 0; un.uShatter.value = -1;
      un.uCenter.value.set(D[ART_X], D[ART_Y], SPINE.z - 0.3);
    }
    for (let a = 0; a < 2; a++) {
      const key = a === 0 ? SHAT_A : SHAT_B;
      if (D[key] >= 0) { D[key] += dt; if (D[key] > 1.6) { D[key] = -1; artifacts[a].uShatter.value = -1; artifacts[a].uGrowth.value = 0; } else artifacts[a].uShatter.value = D[key]; }
    }
    const cur = artifacts[D[ART_CUR] | 0];
    if (aw > 1e-4) {
      D[ART_X] += (ax / aw - D[ART_X]) * (1 - Math.exp(-dt / 0.25));
      D[ART_Y] += (ay / aw + 2.2 + 1.5 * A.growth - D[ART_Y]) * (1 - Math.exp(-dt / 0.25));
      const mn = Math.min(ar, ag, ab) * 0.85, peak = Math.max(ar, ag, ab) - mn;  // a chord's mix pushed back toward saturation
      if (peak > 1e-6) cur.uColor.value.setRGB((ar - mn) / peak, (ag - mn) / peak, (ab - mn) / peak);
    }
    cur.uGrowth.value = A.growth;
    cur.uCenter.value.set(D[ART_X], D[ART_Y], SPINE.z - 0.3);
    cur.uSpread.value = clamp(0.8 + 0.03 * Vc.spread, 0.8, 2.4);
  }

  function resize(fr) { framing = fr || framing; }
  function setActive(on) {
    active = !!on;
    group.visible = active;
    if (!active) seeded = false;   // mounted again, it picks up whatever is sounding then
  }
  function dispose() {
    if (group.parent) group.parent.remove(group);
    for (const g of new Set(geos)) g.dispose();
    for (const m of new Set(mats)) m.dispose();
    for (const x of texs) x.dispose();
    for (const im of instanced) im.dispose();
  }

  return {
    group, update, resize, setActive, dispose,
    keyStyle: KEY_STYLE,
    stageHints: { floorY: top + FLOOR_Y * k, hideHostBody: true },
    parts: { membranes, lights, pistons, clasps, dust, haze, braid, pool },
    uniforms: wingUniforms,
    get framing() { return framing; },
    get feel() { return feel.frame; },
    get moment() { return moment.frame; },
  };
}

export default { id: ID, name: "Ornithopter", keyStyle: KEY_STYLE, keySpan: { first: FIRST, last: FIRST + N - 1 }, create };
