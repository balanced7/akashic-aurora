// VJ Rig: arsenal/web/vj.js (ES module), the page at /web/vj.html. Pure logic lives in vj-core.js (tests/vj_core.test.mjs);
// the browser receipt is arsenal/lanes/vj_verify.mjs.
//
// Daniel, 2026-10-23: "this makes me want to vj so bad with the pads triggering effects ... perhaps faders for colors too,
// go wild" and "there could be a pad to play an effect with velocity changing something about the element, then we could
// have sort of crash close buttons to dampen or stop the effect".
//
// Layers, bottom to top, all in one WebGL2 context:
//   1. THE SET: one Play preset (arsenal/web/presets/*.frag, Play's header and uniform contract), rendered into its own
//      ping-pong feedback pair exactly as Play does. VJ-aware presets (tag "vj") read the VJ strip -- a 16x6 float
//      texture of pads, beat, palette, chord, pedal and stars (vj-core.js STRIP) -- bound to u_video while u_has_video
//      stays 0, so the same files still load in Play. A second set (the cued one) renders while the sets crossfade.
//   2. THE ACCENT OVERLAY: shockwave rings, laser bursts, particles and note glints, with its own feedback for trails.
//   2b. THE BEAM LAYER (Lasers v2, 2026-10-25): the laser engine's beams and figures (vj-lasers.js frame(): records of
//      two RGBA32F texels each), drawn every frame with the overlay's light model (the aaWire core whitened by its heat,
//      the Lorentzian halo, the fade along a beam, a ringing beam bent by its coefficients) and NO feedback, so a gate's
//      dark gap is really dark; added in the composite at the screen's own place (never punched, shaken or bent).
//   3. THE COMPOSITE: mixes the sets, bends them (kaleidoscope, glitch, shockwave refraction, freeze), adds the overlay and
//      applies the full-frame accents (invert, the gated white flash and strobe pulses), saturation and master brightness.
//      Since 2026-10-24 it draws into its own ping-pong pair, so the previous composited frame is there to read (the
//      glitch's datamosh and stutter), and the look (vj-stage.js) or a plain copy takes it to the screen.
//   THE IMPACT PASS (2026-10-24, Daniel: "How do we make the effects feel more impactful and make the vj sets even more
//   reponsive!"): every pad hit, through the velocity curve (vj-core.js velCurve), punches the whole frame (a zoom kick,
//   fast out and eased back), shakes it on hard hits, dips the scene for ~40 ms under the accent's light (never deeper
//   than the measured scene allows: the dip can never be a flash, vj-core.js dipSafeDepth) and lets its light trail longer
//   (the afterglow); the sets get a shared hit input in the strip (row 2, texels 10-12) and each reacts in its own way;
//   the music drives fast-attack / slow-release band envelopes (kick: scale pump, snare: a colour and contrast kick, hat:
//   sparkle); the glitch (pad 4) picks one of six modes, or two, per hit; the beat snap (B, off by default) holds a hit to
//   the next 16th of a live beat; the transport and the dial switch scenes and the page tells the engine which scene
//   shows (POST /api/scene) for the KeyLab's screen.
//   LASERS V2 AND THE COLOUR THEMES (2026-10-25; the build spec: research/reviewed/keylab-liberation-2026-10-22/
//   vj-lasers-v2-and-colour-themes-2026-10-24.md, slices S2, S4, S5; Daniel's calls: daniel-calls-2026-10-25.md): pad 2
//   is the laser engine's hit -- the retrigger tiers (a burst; again within a bar, one tier up and the third press a crown
//   from the hero; within a beat a one-two flicker; eighths or faster a roll locked to the grid; held, the section's loop),
//   the velocity tiers (soft single, medium one-two, hard triple) and the gate the dial picks (AUTO, or one of 15 fixed
//   gates; its click back to AUTO); V (or the learnable Laser vibrate) makes the beams ring; C (or Lasers: classic) brings
//   back the old burst exactly. The gates run on the page grid, the continuous beat position of the BeatClock (vj-core.js,
//   S2). A scene tagged `laser-heads` (the Laser Cathedral) draws its own heads from the strip's head bus (v3) and the beam
//   layer only the hero's. Fader 1 is the THEME fader (21 themes, Custom at the top: Hue A and B, turned by fader 2), the
//   family tabs (F1-F8, or learned buttons) pick a family, and the song's key picks one too (key auto); a theme lands on
//   the next bar and sets the scene's palette, the kick glow, the lasers' colours and the pad lights (LED stand-ins). The
//   engine's hello names its tap controls (the Tap button and pad 12 by default): a pad that taps fires no effect.
// The engine (arsenal keylab-vj, GET <engine>/api/events, Server-Sent Events) feeds beats, energy, hits, chords, notes,
// pads and controls; with chordsense (vj --chords sense) also the key, each chord's roman numeral and the harmony's
// tension (vj-core.js EngineHarmony: the HUD shows key and numeral, the tension feeds the strip, a key change accents
// through the chord-change path). ?demo=1 plays a scripted show through the same path; the keyboard plays the pads
// without either.
// The page posts its pad colours back (POST <engine>/api/pads, at most ten a second) only while the engine's hello says
// it has LEDs, and stops at the first refusal until the engine's next hello (vj-core.js EngineLink).
//
// URL: ?engine=http://127.0.0.1:8794 (default; "off" for none) ?demo=1 ?demopads=0 ?sets=id,id,... ?hud=0
//      ?transport=off (Rewind / Fast forward stop stepping the sets and go to the control map)
//      ?laserseed=N (the laser engine's deal; a fresh one each load otherwise) ?theme=<id> (the theme at load)
// Safety: full-frame flashes pass the FlashGate (<= 3 in any second) in JS and envFlashSafe in the composite shader; and
// since 2026-10-24 every frame passes gate v2 last (vj-limiter.js on the GPU, its rules and JS twin in vj-gate.js): the
// picture actually shown, after every layer, every pixel metered, in every rectangle of 8 x 8 cells covering a quarter of
// the screen or more (311 windows, at every offset) and in every cell, never makes a fourth flash in any second (it holds
// each window to two and a half; nor a red one, nor flashes for more than about five seconds without a rest). The gate
// still decides which flashes are asked for at all; the limiter only ever takes light away from the rest. Without a
// running limiter (its programs still compiling, or a GPU that cannot run them) the page is in its SAFE MODE: every pad
// effect is refused (the set plays on; dampen, choke, kill and the scene keys still work), so nothing on the screen is
// left to the FlashGate alone. ?limiter=cpu decides on the CPU (the JS twin, a readback a frame); ?limiter=off forces the
// safe mode (receipts).
import {
  VJ_API, STRIP, createStrip, stripSet, parseEvent, pitchColours, hueColour, linearToOklab, oklabToLinear, rgbToHex,
  starPosition, fifthsIndex, EFFECTS, CONTROLS, PAD_ACTIONS, DEFAULT_PAD_MAP, normalizePadMap, serializePadMap, actionLabel,
  TARGETS, DEFAULT_CTL_MAP, normalizeCtlMap, learnBinding, applyCtl, FlashGate, EffectBank, BeatClock, PedalDetector,
  pedalSignature, EngineLink, EngineHarmony, DemoScript,
  // the impact pass (2026-10-24)
  velCurve, ImpactLayer, DIP_SAFE_DELTA, glitchPlan, BandEnvelopes, snapDelayMs, SceneControl, SCENE_ACTIONS,
  SCENE_ACTION_IDS, zoomDepth, EFFECT_CODES,
  // Lasers v2 (2026-10-25): the laser and theme actions, the control map's v2 storage, a button's press
  LASER_ACTIONS, LASER_ACTION_IDS, FAMILY_ACTIONS, FAMILY_ACTION_IDS, PressGate, serializeCtlMap,
} from "./vj-core.js";
import { createStage } from "./vj-stage.js";   // wave 2: beat-synced transitions, the post look, the showcase tour
import { createLimiter } from "./vj-limiter.js";   // gate v2: the final-output flash limiter (rules: vj-gate.js)
// Lasers v2 (2026-10-25): the laser engine (pad 2), the colour themes (fader 1, the family tabs, key auto) and the pure
// hook-up between them and the page (the clock, the beam records, the head bus, the tap pads, the gate dial, Custom)
import { createLaserEngine, SEG_TEXELS, MAX_SEGMENTS, SEG_FLOATS, HALO_CUTOFF_PX, TIER_LED, catalogue as laserCatalogue } from "./vj-lasers.js";
import { fetchLibrary, ThemeDirector, themeAtFader, padLeds, ledHexAt, ledPostedOk, CHOKE_LED,
         clockFromBeatClock as themeClockOf, customTurnFromFader } from "./vj-themes.js";
import { laserClock, packBeams, headBus, writeHeadBus, tapPadsOf, isTapPad, GateDial, gateLabel,
         customLaserTheme, standInLed, capHue } from "./vj-hookup.js";

// --------------------------------------------------------------------------------------------------- constants --
const QS = new URLSearchParams(location.search);
const DEMO_AT_START = QS.get("demo") === "1";
const DEMO_PADS = QS.get("demopads") !== null ? QS.get("demopads") !== "0" : QS.get("showcase") !== "1";   // the tour plays its own accents
const ENGINE_URL = (() => {
  const asked = QS.get("engine");
  if (asked === "off") return null;
  if (asked && /^https?:\/\/[^\s"'<>]+$/i.test(asked)) return asked.replace(/\/+$/, "");
  return DEMO_AT_START ? null : "http://127.0.0.1:8794";
})();
const DEFAULT_SETS = ["vj-laser-cathedral", "vj-reactor", "vj-aurora-curtains", "vj-led-wall", "vj-chord-constellations",
                      "feedback-tunnel",
                      // wave 2
                      "vj-hyperspace", "vj-synthwave-grid", "vj-liquid-chrome", "vj-lissajous-chords", "vj-note-rain",
                      "vj-fractal-bloom", "vj-geometry-hall", "vj-particle-galaxy"];
const SET_IDS = (() => {
  const asked = (QS.get("sets") || "").split(",").map((s) => s.trim()).filter((s) => /^[a-z0-9][a-z0-9-]{1,40}$/.test(s));
  return asked.length ? asked : DEFAULT_SETS;
})();
const DPR_CAP = 2;
const BACKING_SCALE_MIN = 0.5;
const TRANSPORT_SETS = QS.get("transport") !== "off";   // Rewind / Fast forward step the sets (onCtl)
const WATCHDOG = QS.get("watchdog") !== "0";   // ?watchdog=0 keeps the full backing size (receipts, recordings)
const WATCHDOG_STREAK = 20;
const FRAME_BUDGET_MS = 1000 / 60;
const HUD_INTERVAL_MS = 100;
const LED_INTERVAL_MS = 100;           // pad lights: at most 10 posts a second
const XFADE_BEATS = 2;
const XFADE_FALLBACK_MS = 1200;
const KILL_OUT_S = 0.3, KILL_IN_S = 0.5;
const KEY_ACCENT = 0.5;                // a key change's accent: half a chord change's pulse (and no palette move, no flash)
const STORE = { pads: "arsenal.vj.padMap", ctl: "arsenal.vj.ctlMap", values: "arsenal.vj.values", opts: "arsenal.vj.options",
                theme: "arsenal.vj.theme" };
// Lasers v2 and the themes
const LASER_SEED = (() => { const s = Number(QS.get("laserseed")); return Number.isInteger(s) && s > 0 ? s : 1 + Math.floor(Math.random() * 2 ** 30); })();
const THEME_AT_START = (() => { const t = QS.get("theme"); return t && /^[a-z0-9-]{2,40}$/.test(t) ? t : null; })();
const FAMILY_KEYS = { F1: 0, F2: 1, F3: 2, F4: 3, F5: 4, F6: 5, F7: 6, F8: 7 };
const LASER_DAMPEN_TAU_S = 0.06;       // Dampen: the beams fade over ~60 ms (spec 1.8: tails x0.15)
const KEY_PADS = { Digit1: 1, Digit2: 2, Digit3: 3, Digit4: 4, Digit5: 5, Digit6: 6, Digit7: 7, Digit8: 8, Digit9: 9,
                   Digit0: 10, Minus: 11, Equal: 12 };
const SCENE_POST_MIN_MS = 120;         // the scene report to the engine: newest wins, at most ~8 a second
// ?limiter=cpu (the JS twin decides, always), off (the safe mode), late (the twin until two seconds in, then the GPU)
const LIMITER_MODE = (() => { const m = QS.get("limiter"); return m === "cpu" || m === "off" || m === "late" ? m : "auto"; })();
const LATENCY_KEEP = 64;
const NOTE_NAMES = ["C", "D♭", "D", "E♭", "E", "F", "G♭", "G", "A♭", "A", "B♭", "B"];
const PLAY_UNIFORMS = [
  "u_video", "u_prev", "u_audio", "u_res", "u_video_res", "u_time", "u_media_time", "u_frame", "u_has_video", "u_pulse",
  "u_beat", "u_level", "u_bass", "u_mid", "u_high", "u_flux", "u_hue", "u_intensity",
  "u_k1", "u_k2", "u_k3", "u_k4", "u_k5", "u_k6", "u_k7", "u_k8"];
const K_UNIFORMS = ["u_k1", "u_k2", "u_k3", "u_k4", "u_k5", "u_k6", "u_k7", "u_k8"];
const AUDIO_TEX_W = 512;

// ------------------------------------------------------------------------------------------------------ shaders --
const VERT_SRC = `#version 300 es
precision highp float;
out vec2 v_uv;
void main() {
  vec2 pos[3] = vec2[3](vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0));
  vec2 p = pos[gl_VertexID];
  v_uv = (p + 1.0) * 0.5;
  gl_Position = vec4(p, 0.0, 1.0);
}`;

// The accent overlay: linear light with its own trails (fbDecay, max with the fresh light so trails never bloom).
const OVERLAY_FS = `#version 300 es
precision highp float;
uniform sampler2D u_prevOv;
uniform vec2 u_res;
uniform float u_keep;
uniform vec4 u_wave[4];      // centre xy (centred space), radius, energy
uniform vec4 u_waveB[4];     // width px, velocity, age s, velocity through the curve
uniform vec3 u_waveCol[4];
uniform float u_sparkle;     // the hat envelope: sparkle amount
uniform float u_sparkleT;    // its tick (a new constellation of sparks ~30 times a second)
uniform vec3 u_sparkleCol;
uniform vec4 u_laser[4];     // origin xy, aim (radians), energy
uniform vec4 u_laserB[4];    // beams, spread (radians), width px, velocity
uniform vec3 u_laserCol[4];
uniform vec4 u_part[4];      // emitter xy, age s, energy
uniform vec4 u_partB[4];     // count, speed, seed, emission end (age s)
uniform vec3 u_partCol[4];
uniform vec4 u_note[8];      // x, -, age s, velocity (velocity 0 = empty)
uniform vec3 u_noteCol[8];
uniform float u_bars;        // strobe scanner bars: amount
uniform float u_barsPhase;   // 0..1 through the strobe cycle
uniform vec3 u_barsCol;
in vec2 v_uv;
out vec4 outColor;
const float PI = 3.14159265358979;
const float TAU = 6.28318530717959;
float hash11(float x) { return fract(sin(x * 127.1 + 311.7) * 43758.5453123); }
float wrapPi(float a) { return a - TAU * floor((a + PI) / TAU); }
float aaWire(float dPx, float widthPx) {
  float drawn = max(widthPx, 1.0);
  return clamp(0.5 * drawn + 0.5 - dPx, 0.0, 1.0) * (max(widthPx, 0.0) / drawn);
}
float lorentz(float dPx, float haloPx) { float x = dPx / max(haloPx, 1e-3); return 0.0625 / (0.0625 + x * x); }
vec3 hotCore(vec3 tint, float heat) {
  float h = max(heat, 0.0); vec3 hue = max(tint, vec3(0.0)); float peak = max(hue.r, max(hue.g, hue.b));
  return h * mix(hue, vec3(peak), h * h / (1.0 + h * h));
}
void main() {
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float rs = max(u_res.y / 1080.0, 0.35);
  vec3 prev = texture(u_prevOv, v_uv).rgb;
  vec3 trail = max(prev * u_keep - 1.5 / 255.0, 0.0);
  vec3 fresh = vec3(0.0);
  for (int i = 0; i < 4; i++) {                       // shockwave rings
    vec4 w = u_wave[i];
    if (w.w < 0.001) continue;
    float d = abs(length(p - w.xy) - w.z) / px;
    float wd = max(u_waveB[i].x * rs, 1.0);
    fresh += u_waveCol[i] * w.w * (exp(-d * d / (wd * wd)) * 0.9 + 0.35 * lorentz(d, wd * 3.0));
    fresh += vec3(1.0) * w.w * u_waveB[i].y * 0.5 * exp(-d * d / (0.3 * wd * wd));
    // the strike (2026-10-24): a small hot core at the ring's centre for its first ~80 ms, so the hit shows in the very
    // next frame while the ring is still small (a few percent of the frame: no flash)
    float flare = exp(-u_waveB[i].z / 0.05) * (0.35 + 0.65 * u_waveB[i].w);
    if (flare > 0.002) {
      float dc = length(p - w.xy) / (0.05 + 0.05 * u_waveB[i].w);
      fresh += hotCore(u_waveCol[i], 2.5) * 0.4 * flare * exp(-dc * dc * 3.0);
    }
  }
  if (u_sparkle > 0.002) {                            // the hat: a scatter of short-lived sparks
    for (int i = 0; i < 14; i++) {
      float fi = float(i);
      vec2 at = vec2((hash11(fi * 3.17 + u_sparkleT * 1.31) - 0.5) * asp * 0.96, hash11(fi * 7.41 + u_sparkleT * 0.77) - 0.5);
      float dPx = length(p - at) / px;
      float s = (1.0 + 1.6 * hash11(fi + u_sparkleT)) * rs;
      fresh += u_sparkleCol * u_sparkle * (exp(-dPx * dPx / (s * s)) * 1.2 + 0.08 * lorentz(dPx, s * 5.0));
    }
  }
  for (int i = 0; i < 4; i++) {                       // laser bursts: the nearest beam of a fan
    vec4 l = u_laser[i];
    if (l.w < 0.001) continue;
    float n = u_laserB[i].x, spread = u_laserB[i].y;
    vec2 d = p - l.xy;
    float len = length(d), ang = atan(d.y, d.x);
    float stepA = n > 1.0 ? spread / (n - 1.0) : 0.0;
    float idx = n > 1.0 ? clamp(floor(wrapPi(ang - l.z) / max(stepA, 1e-4) + 0.5 * (n - 1.0) + 0.5), 0.0, n - 1.0) : 0.0;
    float off = wrapPi(ang - (l.z + (idx - 0.5 * (n - 1.0)) * stepA));
    float along = len * cos(off);
    float dPx = (along > 0.0 ? len * abs(sin(off)) : len) / px;
    float e = l.w * exp(-max(along, 0.0) * 0.5);
    vec3 tint = u_laserCol[i];
    float heat = (1.0 + 2.0 * u_laserB[i].w) * e;
    fresh += (heat > 1e-4 ? hotCore(tint, heat) / heat : tint) * e * aaWire(dPx, u_laserB[i].z * rs) + tint * e * 0.5 * lorentz(dPx, 16.0 * rs);
  }
  for (int e = 0; e < 4; e++) {                       // particles: analytic, each one born, flung, slowed, fallen
    vec4 em = u_part[e];
    if (em.w < 0.001) continue;
    float speed = u_partB[e].y;
    if (length(p - em.xy) > speed * 0.62 + 0.25) continue;
    float count = u_partB[e].x, seed = u_partB[e].z, emitEnd = u_partB[e].w;
    for (int j = 0; j < 48; j++) {
      if (float(j) >= count) break;
      float fj = float(j);
      float h1 = hash11(seed * 97.0 + fj * 1.13), h2 = hash11(seed * 31.0 + fj * 2.71), h3 = hash11(seed * 13.0 + fj * 5.37);
      float life = 0.9 + 0.7 * h3;
      float a0 = em.z - h3 * 0.6;                     // births spread over 0.6 s, then every life while held
      if (a0 < 0.0) continue;
      float cyc = floor(a0 / life);
      if (cyc * life + h3 * 0.6 > emitEnd) continue;  // born after the pad let go: never shown
      float a = a0 - cyc * life;
      float ang = TAU * h1;
      float spd = speed * (0.35 + 0.65 * h2);
      vec2 pos = em.xy + vec2(cos(ang), sin(ang)) * spd * (1.0 - exp(-2.4 * a)) / 2.4 + vec2(0.0, -0.09 * a * a);
      float fade = 1.0 - a / life;
      fade *= fade;
      float size = (1.0 + 2.2 * h2) * rs;
      float dPx = length(p - pos) / px;
      fresh += u_partCol[e] * em.w * fade * (exp(-dPx * dPx / (size * size)) * 1.3 + 0.12 * lorentz(dPx, size * 4.0));
    }
  }
  for (int i = 0; i < 8; i++) {                       // note glints: a rising spark per struck key
    vec4 n = u_note[i];
    if (n.w < 0.001 || n.z > 2.2) continue;
    float rise = 1.0 - exp(-n.z * 1.8);
    vec2 at = vec2(n.x * asp * 0.5, -0.46 + 0.34 * rise);
    vec2 d = (p - at) / px;
    float f = exp(-n.z * 1.5) * n.w;
    float dot2 = exp(-dot(d, d) / (4.0 * rs * rs));
    float streak = exp(-abs(d.x) / (1.0 * rs)) * exp(-max(-d.y, 0.0) / (40.0 * rs)) * step(d.y, 0.0);
    fresh += u_noteCol[i] * f * (dot2 * 1.4 + streak * 0.35);
  }
  if (u_bars > 0.001) {                               // strobe scanner bars: thin, a few percent of the frame
    float on = 1.0 - smoothstep(0.22, 0.32, u_barsPhase);
    for (int b = 0; b < 3; b++) {
      float y = -0.3 + 0.3 * float(b);
      float dy = abs(p.y - y) / px;
      fresh += u_barsCol * u_bars * on * exp(-dy * dy / (16.0 * rs * rs));
    }
  }
  outColor = vec4(max(trail, fresh), 1.0);
}`;

// THE BEAM LAYER (Lasers v2): the laser engine's records (vj-lasers.js THE OUTPUT; decodeSeg is the reference decoder
// and tests/vj_lasers.test.mjs's raster the reference light, which this pass follows): per pixel, every beam record's
// light, and each figure group's light once from its nearest piece. Linear light, no feedback (a gate's dark gap is
// dark); the composite adds it. A record far from the pixel costs one fetch: texel 1 is read only within the cull radius.
const BEAM_FS = `#version 300 es
precision highp float;
precision highp int;
uniform highp sampler2D u_seg;   // RGBA32F, 2 x MAX_SEGMENTS: record i in row i
uniform int u_n;                 // records this frame
uniform vec2 u_res;
in vec2 v_uv;
out vec4 outColor;
const float GROUP_MARK = 1000.0;
const float LEVEL_MAX = 1.25;
const float FALLOFF = 0.5;       // a beam fades along itself by exp(-along * FALLOFF), along in frame heights
const float HALO_CUT = ${HALO_CUTOFF_PX.toFixed(1)};    // px at 1080: the halo is windowed off from half this radius to it
const float PI = 3.14159265358979;
// a line's nearest point: x = the signed distance across it (frame heights, + to its left), y = u along 0..1, z = the
// distance travelled along it (frame heights), w = the plain distance (to an end when the point is past it)
vec4 lineNear(vec2 at, vec2 from, vec2 to) {
  vec2 rel = at - from;
  float len = distance(to, from);
  if (len < 1e-9) return vec4(0.0, 0.0, 0.0, length(rel));
  vec2 dir = (to - from) / len;
  float t = dot(rel, dir);
  float across = rel.y * dir.x - rel.x * dir.y;
  if (t <= 0.0) return vec4(across, 0.0, 0.0, length(rel));
  if (t >= len) return vec4(across, 1.0, len, distance(at, to));
  return vec4(across, t / len, t, abs(across));
}
// a record's light at a pixel, from its texel 1 and its nearest point (nr); sc = frame height / 1080
vec3 recordLight(vec4 t1, vec4 nr, float sc, float hpx) {
  float colq = t1.x, lv = t1.y, sh = t1.z, rg = t1.w;
  vec3 c = vec3(floor(colq / 65536.0), mod(floor(colq / 256.0), 256.0), mod(colq, 256.0)) / 255.0;
  c *= c;                                                           // square-root encoded
  float I = floor(lv / 4096.0) / 4095.0 * LEVEL_MAX;
  float G = mod(lv, 4096.0) / 4095.0 * LEVEL_MAX;
  float W = mod(sh, 64.0) / 16.0;
  float s = floor(sh / 64.0);
  float H = mod(s, 128.0) / 8.0; s = floor(s / 128.0);
  float B = mod(s, 128.0) / 4.0; s = floor(s / 128.0);
  float kind = mod(s, 2.0);
  float flags = floor(s / 2.0);
  bool ringing = mod(floor(flags / 2.0), 2.0) > 0.5;
  float u = nr.y;
  float d = nr.w;
  float blur = B;
  if (ringing) {                                                    // one record, bent by the shader: still at both ends
    float c1 = (mod(rg, 256.0) - 128.0) * 0.15, c2 = (mod(floor(rg / 256.0), 256.0) - 128.0) * 0.075;
    float c3 = (floor(rg / 65536.0) - 128.0) * 0.04;
    float off = c1 * sin(PI * u) + c2 * sin(2.0 * PI * u) + c3 * sin(3.0 * PI * u);
    if (u > 0.0 && u < 1.0) d = abs(nr.x - off / 1080.0);
    blur = B * sin(PI * u);
  }
  float dPx = d * hpx;
  float wpx = W * sc, bpx = blur * sc;
  float Wd = bpx > 0.0 ? wpx + 2.0 * bpx : wpx;
  float drawn = max(Wd, 1.0);
  float core = clamp(0.5 * drawn + 0.5 - dPx, 0.0, 1.0) * (wpx / drawn);
  float q = dPx / (16.0 * sc);
  float halo = 0.5 * G * 0.0625 / (0.0625 + q * q) * (1.0 - smoothstep(0.5 * HALO_CUT * sc, HALO_CUT * sc, dPx));
  float fade = kind > 0.5 ? 1.0 : exp(-nr.z * FALLOFF);
  vec2 hi2 = max(c.rg, c.gb);
  float peak = max(hi2.x, hi2.y);                                  // the brightest channel
  float kw = H * H / (1.0 + H * H);
  return ((c + (vec3(peak) - c) * kw) * I * core + c * halo) * fade;
}
void main() {
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float hpx = u_res.y;
  float sc = u_res.y / 1080.0;
  // beyond this a record adds nothing: the halo's cut, the most a ring can bend a beam (~34 px) and its blur band
  float cull = (HALO_CUT + 40.0) * sc / hpx;
  vec3 acc = vec3(0.0);
  int i = 0;
  for (int guard = 0; guard < ${MAX_SEGMENTS}; guard++) {
    if (i >= u_n) break;
    vec4 t0 = texelFetch(u_seg, ivec2(0, i), 0);
    if (t0.w >= GROUP_MARK - 0.5) {                                 // a figure: its nearest piece, its light once
      int count = int(t0.w - GROUP_MARK + 0.5);
      if (length(p - t0.xy) > t0.z + cull) { i += count + 1; continue; }
      float best = 1e9; int bi = -1; vec4 bnr = vec4(0.0);
      for (int j = 1; j <= 256; j++) {
        if (j > count || i + j >= u_n) break;
        vec4 s0 = texelFetch(u_seg, ivec2(0, i + j), 0);
        vec4 nr = lineNear(p, s0.xy, s0.zw);
        if (nr.w < best) { best = nr.w; bi = i + j; bnr = nr; }
      }
      if (bi >= 0 && best < cull) acc += recordLight(texelFetch(u_seg, ivec2(1, bi), 0), bnr, sc, hpx);
      i += count + 1;
      continue;
    }
    vec4 nr = lineNear(p, t0.xy, t0.zw);
    if (nr.w < cull) acc += recordLight(texelFetch(u_seg, ivec2(1, i), 0), nr, sc, hpx);
    i++;
  }
  outColor = vec4(acc, 1.0);
}`;

// The composite: sets (display values) -> punch and shake -> bends (shockwave refraction, glitch, kaleidoscope, freeze)
// -> the dip -> overlay (linear) -> full-frame accents -> master. It draws into the page's composite pair (G.cmp), so
// u_hist is the previous composited frame (the glitch's datamosh feeds on it) and u_stut the frame held at the last glitch.
const COMPOSITE_FS = `#version 300 es
precision highp float;
uniform sampler2D u_a, u_b, u_ov, u_frz, u_hist, u_stut, u_meter, u_beam;
uniform vec2 u_res;
uniform float u_beamGain;    // the beam layer's gain (Lasers v2): the accent fader capped at 1, Dampen and Choke
uniform float u_mix;
uniform float u_kal, u_kalN, u_kalRot;
uniform float u_glitch, u_glitchT, u_gSize, u_gSeed, u_gAge;
uniform vec2 u_gMode;        // the glitch's primary and second mode (vj-core.js GLITCH_MODES; -1 = none)
uniform float u_freeze, u_freezeZoom;
uniform vec4 u_wave[4];
uniform vec4 u_waveB[4];
uniform float u_flash, u_flashGap;
uniform float u_invert;
uniform float u_bright, u_sat, u_accent;
uniform float u_metro;
uniform vec3 u_metroCol;
uniform float u_bloom;
uniform vec3 u_bloomCol;
uniform float u_punch;       // the frame's zoom kick (fraction): the hits' punch + the zoom punch + the kick's pump
uniform float u_blur;        // the zoom punch's radial blur (fraction of the way to the centre)
uniform vec2 u_shake;        // the frame's jolt (fractions of the frame height)
uniform float u_dip, u_dipGranted, u_dipSafe;   // the dip: asked depth; 1 = it rides a granted flash; the safe delta
uniform float u_snare;       // the snare's kick: contrast and colour
in vec2 v_uv;
out vec4 outColor;
const float PI = 3.14159265358979;
const float TAU = 6.28318530717959;
const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);
// motion-envelope envFlashSafe (arsenal/web/glsl/motion/envelope.glsl): 0 until a third of a second after the previous
// full-field flash, 1 from half a second on -- the shader's own copy of the gate the page keeps (FlashGate, vj-core.js)
float envFlashSafe(float sinceLastFlash) { return smoothstep(1.0 / 3.0, 0.5, sinceLastFlash); }
float h12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec2 mirrorUv(vec2 uv) { return 1.0 - abs(1.0 - mod(uv, 2.0)); }
vec3 sets(vec2 uv) {
  uv = mirrorUv(uv);
  vec3 a = texture(u_a, uv).rgb;
  if (u_mix > 0.001) {
    float m = clamp(u_mix, 0.0, 1.0);
    a = mix(a, texture(u_b, uv).rgb, m * m * (3.0 - 2.0 * m));
  }
  return a;
}
vec3 scene(vec2 uv) {                                  // the sets, smeared toward the centre while the zoom punch springs
  if (u_blur < 1e-3) return sets(uv);
  vec2 d = uv - 0.5;
  vec3 s = vec3(0.0);
  for (int i = 0; i < 5; i++) s += sets(0.5 + d * (1.0 - u_blur * float(i) / 4.0));
  return s * 0.2;
}
bool modeOn(float m) { return abs(u_gMode.x - m) < 0.5 || abs(u_gMode.y - m) < 0.5; }
// the glitch's displacing modes: slices and blocks shoved, rows torn and wobbling, the channels pulled apart
void glitchUv(inout vec2 q, inout vec2 split, float asp) {
  float a = u_glitch, sz = u_gSize, sd = u_gSeed, tk = u_glitchT;
  // the strike: whatever the modes, the first ~120 ms tear the frame into shoved blocks with the channels apart, so every
  // glitch lands hard in the very next frame and the modes carry it on
  float burst = max(0.0, 1.0 - u_gAge / 0.12) * a;
  if (burst > 0.001) {
    // its own shape every hit, from the seed: the block grid (5 to 22 rows), the shove's direction (across, along or
    // diagonal) and the channels' split angle
    float n = mix(5.0, 22.0, fract(sd * 7.13));
    vec2 cell = floor(q * vec2(n * asp * mix(0.3, 1.2, fract(sd * 3.7)), n));
    float h = h12(cell * 1.9 + sd * 21.0);
    float dirA = floor(fract(sd * 5.31) * 3.0);        // 0 across, 1 along, 2 diagonal
    vec2 dir = dirA < 0.5 ? vec2(1.0, 0.0) : dirA < 1.5 ? vec2(0.0, 1.0) : normalize(vec2(1.0, 0.6));
    if (h < 0.55) q += dir * (h12(cell * 2.7 + sd * 5.0) - 0.5) * (0.16 + 0.26 * sz) * burst;
    float ang = sd * 6.2832;
    split += vec2(cos(ang), sin(ang) * 0.5) * 0.03 * burst;
  }
  if (modeOn(0.0)) {                                   // split: horizontal slices shoved sideways
    float rows = mix(40.0, 7.0, sz);
    float sl = floor(q.y * rows);
    float h = h12(vec2(sl, tk + sd * 17.0));
    if (h < 0.6) q.x += (h12(vec2(sl * 1.7, tk * 0.37 + sd * 3.0)) - 0.5) * 0.18 * a;
    split += vec2(0.006 + 0.034 * a, 0.006 * a * (h - 0.5));
  }
  if (modeOn(1.0)) {                                   // tear: blocks displaced, scanlines torn
    float n = mix(28.0, 6.0, sz);
    vec2 cells = vec2(n * asp * 0.6, n);
    vec2 cell = floor(q * cells);
    float h = h12(cell + tk * 13.17 + sd * 5.0);
    if (h < 0.1 + 0.45 * a) q += vec2((h12(cell * 1.7 + tk) - 0.5) * 0.28, (h12(cell * 2.3 - tk) - 0.5) * 0.06) * a;
    float row = h12(vec2(floor(q.y * 220.0), tk + sd * 11.0));
    if (row < 0.16 * a) q.x += (row - 0.08 * a) * 2.2 + 0.02 * sin(q.y * 300.0 + tk);
    split += vec2(0.008 * a, 0.0);
  }
  if (modeOn(5.0)) {                                   // VHS: rows wobble, a tracking band rolls through, chroma bleeds
    float t = u_gAge;
    q.x += (sin(q.y * 38.0 + t * 11.0) * 0.012 + sin(q.y * 7.0 - t * 4.0) * 0.022) * a;
    q.x += (h12(vec2(floor(q.y * 300.0), floor(t * 30.0))) - 0.5) * 0.02 * a;
    float bar = fract(q.y * 0.7 - t * 1.4 - sd);
    float band = smoothstep(0.0, 0.05, bar) * (1.0 - smoothstep(0.12, 0.2, bar));
    q.x += band * (0.06 + 0.05 * sin(q.y * 120.0 + t * 40.0)) * a;   // the tracking error: a band torn sideways
    q.y += band * 0.025 * a;
    split += vec2(0.022 * a, 0.0);
  }
}
// the glitch's colour modes: a datamosh smear through the previous frame, pixel-sort streaks, a stutter of held slices
vec3 glitchColour(vec3 c, vec2 q, vec2 uv, float asp) {
  float a = u_glitch, sz = u_gSize, sd = u_gSeed;
  float burst = max(0.0, 1.0 - u_gAge / 0.12) * a;
  if (burst > 0.001) {                                 // the strike: some blocks have their channels turned round
    float n = mix(5.0, 22.0, fract(sd * 7.13));
    vec2 cell = floor(uv * vec2(n * asp * mix(0.3, 1.2, fract(sd * 3.7)), n));
    if (h12(cell * 4.1 + sd * 9.0) < 0.4) c = mix(c, fract(sd * 11.3) < 0.5 ? c.gbr : c.brg, burst);
  }
  if (modeOn(2.0)) {                                   // datamosh: blocks drag the previous frame along their own vector
    float n = mix(18.0, 5.0, sz);
    vec2 cell = floor(uv * vec2(n * asp, n));
    vec2 mv = (vec2(h12(cell + sd * 31.0), h12(cell * 1.3 + sd * 7.0)) - 0.5) * 0.09 * (0.4 + a);
    vec3 prev = texture(u_hist, mirrorUv(uv - mv)).rgb;
    // it takes over from the strike after ~50 ms: the first frames show the hit, not the frame before it
    float keep = clamp(0.92 * a * step(0.25, h12(cell * 0.7 + sd)), 0.0, 0.93) * smoothstep(0.03, 0.08, u_gAge);
    vec3 live = c;
    c = mix(c, prev, keep);                            // the smear feeds on itself: each frame drags the last one further
    c += abs(prev - live) * 0.25 * a * keep;           // where the drag tears from the live picture, the seam glows
  }
  if (modeOn(3.0)) {                                   // pixel sort: bright pixels pulled into streaks along lanes
    bool vertical = sd < 0.5;
    float lane = vertical ? floor(uv.x * u_res.x / mix(2.0, 8.0, sz)) : floor(uv.y * u_res.y / mix(2.0, 8.0, sz));
    if (h12(vec2(lane, sd * 9.0)) < 0.35 + 0.5 * a) {
      vec2 dir = vertical ? vec2(0.0, 1.0) : vec2(1.0 / asp, 0.0);
      float stepL = (0.006 + 0.03 * sz) * a;
      vec3 best = c;
      float bl = dot(c, LUMA);
      for (int i = 1; i <= 10; i++) {
        vec3 s = scene(q - dir * stepL * float(i));
        float l = dot(s, LUMA);
        float w = 1.0 - float(i) / 11.0;
        if (l * w > bl && l > 0.18) { best = s * (0.55 + 0.45 * w); bl = l * w; }
      }
      c = max(c, best);
    }
  }
  if (modeOn(4.0)) {                                   // stutter: bands of the frame held at the hit flicker back in
    float b = floor(uv.y * mix(14.0, 3.0, sz));
    float step12 = floor(u_gAge * 12.0);                // each band jumps to a new offset twelve times a second
    if (h12(vec2(b, sd * 13.0)) < 0.6 && fract(u_gAge * 12.0) < 0.7 && u_gAge > 0.06) {   // after the strike
      vec2 off = vec2((h12(vec2(b, 3.0 + sd + step12)) - 0.5) * 0.22 * a, (h12(vec2(b * 1.3, step12)) - 0.5) * 0.04 * a);
      vec3 held = texture(u_stut, mirrorUv(uv + off)).rgb;
      c = mix(c, held, clamp(0.5 + 0.5 * a, 0.0, 1.0));
    }
  }
  if (modeOn(5.0)) {                                   // VHS: a little washed out, specks along the rows
    float l = dot(c, LUMA);
    c = mix(c, vec3(l) * vec3(1.02, 0.98, 1.05), 0.25 * a);
    float speck = step(0.996, h12(vec2(floor(uv.x * u_res.x * 0.25), floor(uv.y * u_res.y * 0.5) + floor(u_gAge * 30.0))));
    c += speck * 0.5 * a;
  }
  return c;
}
void main() {
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p0 = (v_uv - 0.5) * vec2(asp, 1.0);             // the screen's own place (the metronome and bloom stay put)
  float px = 1.0 / max(u_res.y, 1.0);
  // the whole frame's punch and shake (u_punch 0 and u_shake 0 leave uv exactly v_uv)
  vec2 uv = 0.5 + (v_uv - 0.5) / (1.0 + max(u_punch, 0.0)) + u_shake * vec2(1.0 / asp, 1.0);
  vec2 p = (uv - 0.5) * vec2(asp, 1.0);
  // shockwaves refract the picture behind their rings (a lens: the front gathers light, red bends further than blue)
  vec2 disp = vec2(0.0);
  float lens = 0.0;
  for (int i = 0; i < 4; i++) {
    vec4 w = u_wave[i];
    if (w.w < 0.001) continue;
    vec2 d = p - w.xy;
    float r = length(d);
    float width = max(u_waveB[i].x, 1.0) * px * 3.0;
    float ring = (r - w.z) / width;
    float prof = exp(-ring * ring);
    disp += (d / max(r, 1e-4)) * prof * ring * 0.034 * w.w * u_accent / vec2(asp, 1.0);
    lens += prof * max(-ring, 0.0) * w.w;
  }
  vec2 q = uv + disp;
  vec2 split = vec2(0.0);
  if (u_glitch > 0.001) glitchUv(q, split, asp);
  vec3 c;
  if (dot(split, split) > 1e-10 || dot(disp, disp) > 1e-12) {
    c = vec3(scene(q + split + disp * 0.35).r, scene(q).g, scene(q - split - disp * 0.35).b);
  } else c = scene(q);
  if (u_glitch > 0.001) c = glitchColour(c, q, uv, asp);
  c *= 1.0 + 0.6 * min(lens, 1.0);
  if (u_kal > 0.001) {                                 // kaleidoscope: fold the angle into mirrored segments
    vec2 kq = (uv - 0.5) * vec2(asp, 1.0);
    float seg = TAU / max(u_kalN, 2.0);
    float a = mod(atan(kq.y, kq.x) + u_kalRot, seg);
    a = min(a, seg - a);
    vec2 k = length(kq) * vec2(cos(a), sin(a));
    vec2 kuv = k / vec2(asp, 1.0) + 0.5;
    c = mix(c, scene(kuv), clamp(u_kal, 0.0, 1.0));
  }
  if (u_freeze > 0.001) {
    vec2 fuv = (uv - 0.5) * (1.0 - u_freezeZoom) + 0.5;
    c = mix(c, texture(u_frz, mirrorUv(fuv)).rgb, clamp(u_freeze, 0.0, 1.0));
  }
  // to linear light; the dip (never deeper than the measured scene allows: vj-core.js dipSafeDepth); the accents; a soft
  // shoulder; back to display values
  vec3 lin = pow(max(c, vec3(0.0)), vec3(2.2));
  float meanLin = texelFetch(u_meter, ivec2(0, 0), 0).r;
  // the dip (2026-10-24 safety pass): never under Invert (inverted, a dip is a brightening the meter never measured: it
  // fades out as Invert comes in), and a dip that rides a granted white flash goes only as deep as the flash will show
  // (the shader blanks a flash that follows the last one too soon: envFlashSafe), the rest held to the safe depth
  float dipOn = 1.0 - clamp(u_invert, 0.0, 1.0);
  if (u_dip > 0.001 && dipOn > 0.001) {
    float shown = meanLin * pow(max(u_bright, 0.0), 2.2);
    float safeDip = min(u_dip, u_dipSafe / max(shown, 1e-4));
    float dip = u_dipGranted > 0.5 ? mix(safeDip, u_dip, envFlashSafe(u_flashGap)) : safeDip;
    lin *= 1.0 - clamp(dip, 0.0, 0.9) * dipOn;
  }
  lin += texture(u_ov, mirrorUv(uv)).rgb * u_accent;
  // the lasers' beams, at the screen's own place: the scene punches, shakes and bends behind them; the engine fitted
  // their light to its flash budget as drawn, so they are only ever scaled down here
  if (u_beamGain > 0.0005) lin += texture(u_beam, v_uv).rgb * u_beamGain;
  float edge = smoothstep(0.30, 0.62, max(abs(p0.x) / max(asp, 1e-3), abs(p0.y)));
  lin += u_metroCol * u_metro * edge;                  // the metronome: a breath at the frame's edge
  lin += u_bloomCol * u_bloom * exp(-dot(p0, p0) * 5.0); // hits: a soft lift at the centre (kept under the flash line)
  vec3 over = max(lin - 0.8, 0.0);
  lin = min(lin, vec3(0.8)) + 0.2 * tanh(over / 0.2);
  c = pow(lin, vec3(1.0 / 2.2));
  if (u_snare > 0.001) {                               // the snare: contrast around the scene's own mean (its mean holds)
    float m = pow(max(meanLin, 0.0), 1.0 / 2.2);
    c = max(m + (c - m) * (1.0 + 0.3 * u_snare), 0.0);
  }
  float l = dot(c, LUMA);
  c = mix(vec3(l), c, u_sat * (1.0 + 0.35 * u_snare));
  c = mix(c, 1.0 - c, clamp(u_invert, 0.0, 1.0));
  c = mix(c, vec3(1.0), clamp(u_flash, 0.0, 1.0) * envFlashSafe(u_flashGap));
  c *= u_bright;
  if (any(isnan(c)) || any(isinf(c))) c = vec3(0.0);
  c += (h12(gl_FragCoord.xy) - 0.5) / 255.0 * u_bright;   // a static dither (per pixel, never per frame)
  outColor = vec4(clamp(c, 0.0, 1.0), 1.0);
}`;

// The scene meter: the mean relative luminance (linear) of the sets AND the accent overlay as the composite adds them,
// measured every frame on the GPU (64 x 36 cells of 16 taps, then one texel), read by the composite in the same frame: the
// dip's safety limit and the snare's pivot. (Since the 2026-10-24 safety pass it includes the overlay, and the final
// guarantee for every layer is gate v2, vj-limiter.js, on the frame actually shown. A 16 x 9 grid with the same taps was
// tried and cost ~5 ms a frame on SwiftShader: a pass of 144 heavy fragments runs on one thread there.)
const METER_FS = `#version 300 es
precision highp float;
uniform sampler2D u_a, u_b, u_ov;
uniform float u_mix;          // already eased, as the composite eases it
uniform float u_accent;       // the overlay's gain in the composite
out vec4 outColor;
void main() {
  vec2 cell = 1.0 / vec2(64.0, 36.0);
  vec2 base = floor(gl_FragCoord.xy) * cell;
  float s = 0.0;
  for (int j = 0; j < 4; j++) for (int i = 0; i < 4; i++) {
    vec2 uv = base + (vec2(float(i), float(j)) + 0.5) * cell * 0.25;
    vec3 c = texture(u_a, uv).rgb;
    if (u_mix > 0.001) c = mix(c, texture(u_b, uv).rgb, u_mix);
    vec3 lin = pow(max(c, vec3(0.0)), vec3(2.2)) + texture(u_ov, uv).rgb * u_accent;
    s += dot(lin, vec3(0.2126, 0.7152, 0.0722));
  }
  outColor = vec4(s / 16.0, 0.0, 0.0, 1.0);
}`;
// ... reduced in two steps, 64 x 36 -> 8 x 6 -> 1, each fragment averaging an 8 x 6 block (2026-10-24: one fragment
// summing all 2304 cells ran on a single SwiftShader thread, ~1-2 ms of the impact pass's added frame time)
const METER2_FS = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D u_src;
uniform ivec2 u_block;
out vec4 outColor;
void main() {
  ivec2 o = ivec2(gl_FragCoord.xy) * u_block;
  float s = 0.0;
  for (int y = 0; y < u_block.y; y++) for (int x = 0; x < u_block.x; x++) s += texelFetch(u_src, o + ivec2(x, y), 0).r;
  outColor = vec4(s / float(u_block.x * u_block.y), 0.0, 0.0, 1.0);
}`;
// the composite to the screen when the look is off
const COPY_FS = `#version 300 es
precision highp float;
uniform sampler2D u_src;
in vec2 v_uv;
out vec4 outColor;
void main() { outColor = vec4(texture(u_src, v_uv).rgb, 1.0); }`;

// ---------------------------------------------------------------------------------------------------- the state --
const $ = (id) => document.getElementById(id);
const canvas = $("gl");
const stageEl = $("stage");
const errors = [];
const T = {};
for (const t of TARGETS) if (t.def !== null) T[t.id] = t.def;
// snap: the beat snap (off by default; the panel and the B key): a hit waits for the next 16th of a live beat
// punch: the impact layer on pad hits (punch, shake, dip, afterglow); a velocity-0 hit still feeds the sets' hit texel
// lasersClassic: pad 2 fires the classic overlay burst exactly (Lasers v2 off); vibrate: the v2 beams ring
const options = { hits: true, leds: true, snap: false, punch: true, lasersClassic: false, vibrate: false, keyAuto: true };

const sets = SET_IDS.map((id) => ({
  id, name: id, author: "", tags: [], params: [], knobs: new Float32Array(8), defaults: new Float32Array(8),
  status: "loading", problem: "", program: null, uniforms: null, fb: null, frame: 0, vj: false, source: "", trailsK: -1, laserHeads: false,
}));
const deck = { a: 0, b: Math.min(1, sets.length - 1), running: false, start: 0, ms: 0, pickup: true, from: 0 };

const gate = new FlashGate();
const fx = new EffectBank();
const beat = new BeatClock();
const pedal = new PedalDetector();
const impact = new ImpactLayer();      // every hit's punch, shake, dip and afterglow (vj-core.js)
const bands = new BandEnvelopes();     // kick / snare / hat: fast attack, slower release
const scenes = new SceneControl();     // rewind / fast-forward / the dial -> scenes
const snapQ = [];                      // pad hits waiting for the beat snap: { pad, vel, src, at, off }
const glitchState = { serial: -1, plan: null, t0: 0 };
const latency = { records: [] };       // pad event arrival -> the frame that drew it (window.__vj.latency())
const sceneReport = { want: null, sentKey: "", inflight: false, lastAt: -1e9, retryAt: 0, posts: 0, log: [], last: null };
// Lasers v2: the engine (pad 2), its last frame's records as uploaded, the head bus, the gate dial, Dampen / Choke
const lasers = {
  eng: createLaserEngine({ seed: LASER_SEED, aspect: 16 / 9 }), seed: LASER_SEED,
  dial: new GateDial(), presses: new PressGate(),
  packed: new Float32Array(MAX_SEGMENTS * SEG_FLOATS), n: 0, heroOnly: false,
  bus: new Float32Array(24), busOn: false,
  gain: 1, cut: false, dampT: null,          // Choke cuts the beams until the next hit; Dampen fades them
  pinned: false,                             // P: every hit repeats the last one (vj-lasers.js pin)
  hits: 0, refused: 0, last: null, pad: 0, held: false,
  frames: 0, litFrames: 0, over: 0, maxWindow: 0, maxFrame: 0, pulses: 0, flashes: 0,
  out: null, themeId: "", log: [],
};
lasers.eng.setClock(laserClock(beat));
// the colour themes (vj-themes.js): the library loads at boot; until then (or if it cannot) the page keeps its palette
const themes = { lib: null, dir: null, look: null, error: "", changes: 0, cuts: 0, dipUntil: 0, dipAt: 0, family: null,
                 lastChange: null, customTurn: 0, laserKey: "", ledLook: null, faderTouched: false, keyEvents: 0 };
// the engine's tap pads (its hello's tap list): a pad that taps fires no effect
let tapPads = [];
let tapPresses = 0, tapLast = null;
let padMap = DEFAULT_PAD_MAP.slice();
let ctlMap = { ...DEFAULT_CTL_MAP };
let learnTarget = null;
let lastCtl = null;
let lastPadSrc = "";
const padHeld = new Uint8Array(12);
const padT0 = new Float64Array(12).fill(-1e9);
const padPress = new Float32Array(12);           // a press flash for the control pads' lights
const keyPadDown = new Uint8Array(13);

// music (the energy levels come from the band envelopes since 2026-10-24: bands.level)
// stamps: the engine's last 256 energy events (their rate over the last second is in window.__vj.stats())
const energy = { bass: 0, mid: 0, high: 0, level: 0, last: -1e9, events: 0, stamps: new Float64Array(256).fill(-1e9) };
const hit = { pulse: 0, bloom: 0 };     // kick / snare / hat: bands.env (vj-core.js BandEnvelopes)
let pulseEnv = 0;
const chord = { name: "", root: -1, pcs: [], src: "", t: -1e9, quality: "", roman: "", key: "", bass: -1, conf: null };
const harm = new EngineHarmony();      // the engine's key and tension (chordsense); the page's own estimate without them
let keyAccents = 0;
let chordPulse = 0, travel = 1, drawOn = 1, lastDrawRestart = -1e9;
const kHeld = new Uint8Array(128), kSus = new Uint8Array(128);
const kVel = new Float32Array(128), kT0 = new Float64Array(128), kStrike = new Float32Array(128);
const pcLevel = new Float32Array(12), pcStrike = new Float32Array(12), pcReg = new Float32Array(12).fill(0.5), pcHeld = new Float32Array(12);
let sustainPedal = false;
const feelState = { sounding: new Map(), chord: null, pedal: false };
let feel = null, feelFrame = null;
const glints = Array.from({ length: 8 }, () => ({ x: 0, t0: -1e9, vel: 0, pc: 0 }));
let glintNext = 0;

// palette (linear rgb, 4 stops x 3)
const palNow = new Float32Array(12), palBefore = new Float32Array(12), palTarget = new Float32Array(12), padCol = new Float32Array(36);
const chordStops = new Float32Array(12);
let chordPresence = 0;
const lab1 = new Float64Array(3), lab2 = new Float64Array(3), mixOut = new Float64Array(3);
const PC_RGB = pitchColours();

// kill, flash, strobe, freeze
const kill = { gain: 1, target: 1, pending: null, at: null };
const flash = { t0: -1e9, peak: 0, decay: 0.15, gap: 1e9 };
let strobeNext = 0;
let freezeCapture = false;
let stutterCapture = false;
// this frame's impact values (updateImpact): the punch (hits + zoom punch + the kick's pump), the zoom punch's blur, the
// shake, the dip and whether it rides a granted flash, the afterglow, the snare's kick and the hat's sparkle
const frame = { punch: 0, zoom: 0, pump: 0, blur: 0, shakeX: 0, shakeY: 0, dip: 0, dipGranted: 0, glow: 0, snare: 0, sparkle: 0 };
let demo = null;

// engine
// link: open, the engine's hello and status, and whether pad colours may be posted (vj-core.js EngineLink)
const engine = { url: ENGINE_URL, es: null, link: new EngineLink(), events: 0, bad: 0, demoEvents: 0, lastMsg: -1e9 };
const led = { last: "", lastAt: -1e9, computedAt: -1e9, inflight: false, backoffUntil: 0, posts: 0, log: [], washed: 0 };

// GL
const G = { gl: null, lost: false, parallel: null, fbInternal: 0, fbType: 0, fbFormat: "", stripTex: null, audioTex: null,
            blackTex: null, ov: null, frz: null, ovProg: null, ovU: null, compProg: null, compU: null, pool: [],
            width: 1, height: 1, scale: 1,
            // the impact pass: the composite's own pair (its previous frame feeds the glitch), the stutter's held frame,
            // the scene meter (64 x 36, then 1 x 1) and their programs
            cmp: null, stut: null, meter1: null, meter2: null, meterProg: null, meterU: null, meter2Prog: null,
            limiter: null, limiterError: "",
            meter2U: null, copyProg: null, copyU: null };
const strip = createStrip();
const audioBytes = new Uint8Array(AUDIO_TEX_W * 2);
const U = {   // uniform scratch (no allocation per frame)
  wave: new Float32Array(16), waveB: new Float32Array(16), waveCol: new Float32Array(12),
  laser: new Float32Array(16), laserB: new Float32Array(16), laserCol: new Float32Array(12),
  part: new Float32Array(16), partB: new Float32Array(16), partCol: new Float32Array(12),
  note: new Float32Array(32), noteCol: new Float32Array(24),
};
const starPos = [0, 0];
const starKeys = new Int16Array(128);

// frame stats
const stats = { frames: 0, fps: 0, fpsCount: 0, fpsStart: 0, last: 0, slowStreak: 0, gaps: new Float32Array(240), gapIdx: 0,
                gapN: 0, scaleDrops: 0 };
const probe = { on: false, trace: [], buf: null, waiters: [] };
const SRGB_TO_LINEAR = new Float32Array(256).map((_, i) => {
  const s = i / 255;
  return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
});

// ------------------------------------------------------------------------------------------------------ helpers --
const clamp = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);
const smooth = (x) => { const t = clamp(x, 0, 1); return t * t * (3 - 2 * t); };
function safeGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
function safeSet(key, value) { try { localStorage.setItem(key, value); } catch { /* private window or blocked storage */ } }
function recordError(kind, id, message) {
  const entry = { kind, id, message: String(message).slice(0, 2000), t: Math.round(performance.now()) };
  errors.push(entry);
  if (errors.length > 50) errors.shift();
  console.warn(`[vj] ${kind}${id ? " " + id : ""}: ${entry.message.split("\n")[0]}`);
}
function banner(text) {
  const b = $("banner");
  if (!text) { b.hidden = true; return; }
  b.textContent = text;
  b.hidden = false;
}
let toastTimer = 0;
function toast(text) {
  const el = $("toast");
  el.textContent = text;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1600);
}
function hexToLinear(hex) {
  const n = parseInt(hex.slice(1), 16);
  const dec = (v) => { const s = v / 255; return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
  return [dec((n >> 16) & 255), dec((n >> 8) & 255), dec(n & 255)];
}
const CONTROL_RGB = Object.fromEntries(Object.entries(CONTROLS).map(([k, v]) => [k, hexToLinear(v.colour)]));
function noteName(key) { return `${NOTE_NAMES[key % 12]}${Math.floor(key / 12) - 1}`; }

// mix two linear colours through OKLCH, the hue turning the short way round: lightness and colourfulness hold between
// distant hues (a straight line through OKLab or rgb from red to teal passes through grey), writing into out[o..o+2]
function oklabMix(src1, o1, src2, o2, t, out, o) {
  linearToOklab(src1[o1], src1[o1 + 1], src1[o1 + 2], lab1);
  linearToOklab(src2[o2], src2[o2 + 1], src2[o2 + 2], lab2);
  const c1 = Math.hypot(lab1[1], lab1[2]), c2 = Math.hypot(lab2[1], lab2[2]);
  let h1 = Math.atan2(lab1[2], lab1[1]), h2 = Math.atan2(lab2[2], lab2[1]);
  if (c1 < 1e-4) h1 = h2;
  if (c2 < 1e-4) h2 = h1;
  let dh = h2 - h1;
  dh -= 2 * Math.PI * Math.round(dh / (2 * Math.PI));
  const L = lab1[0] + (lab2[0] - lab1[0]) * t, C = c1 + (c2 - c1) * t, h = h1 + dh * t;
  oklabToLinear(L, C * Math.cos(h), C * Math.sin(h), mixOut);
  out[o] = mixOut[0]; out[o + 1] = mixOut[1]; out[o + 2] = mixOut[2];
}

// --------------------------------------------------------------------------------------------------------- GL --
function createTexture(gl, filter) {
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
  return tex;
}
function compileShader(gl, type, src) {
  const sh = gl.createShader(type);
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(sh) || "unknown compile error";
    gl.deleteShader(sh);
    throw new Error(log);
  }
  return sh;
}
function linkSync(gl, fsSrc) {
  const vs = compileShader(gl, gl.VERTEX_SHADER, VERT_SRC);
  let fs;
  try { fs = compileShader(gl, gl.FRAGMENT_SHADER, fsSrc); } catch (err) { gl.deleteShader(vs); throw err; }
  const prog = gl.createProgram();
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.linkProgram(prog);
  const ok = gl.getProgramParameter(prog, gl.LINK_STATUS);
  const log = ok ? "" : gl.getProgramInfoLog(prog) || "unknown link error";
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  if (!ok) { gl.deleteProgram(prog); throw new Error(log); }
  return prog;
}
// Presets compile without blocking a frame when KHR_parallel_shader_compile exists (as Play does).
function linkAsync(gl, fsSrc) {
  return new Promise((resolve, reject) => {
    const vs = gl.createShader(gl.VERTEX_SHADER), fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(vs, VERT_SRC); gl.compileShader(vs);
    gl.shaderSource(fs, fsSrc); gl.compileShader(fs);
    const prog = gl.createProgram();
    gl.attachShader(prog, vs); gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    const finish = () => {
      if (gl.isContextLost()) { reject(new Error("WebGL context lost during compile")); return; }
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
        const log = (!gl.getShaderParameter(fs, gl.COMPILE_STATUS) ? gl.getShaderInfoLog(fs) : gl.getProgramInfoLog(prog)) || "link failed";
        gl.deleteProgram(prog); gl.deleteShader(vs); gl.deleteShader(fs);
        reject(new Error(log));
        return;
      }
      gl.deleteShader(vs); gl.deleteShader(fs);
      resolve(prog);
    };
    if (!G.parallel) { finish(); return; }
    (function poll() {
      if (gl.isContextLost()) { reject(new Error("WebGL context lost during compile")); return; }
      if (gl.getProgramParameter(prog, G.parallel.COMPLETION_STATUS_KHR)) finish(); else setTimeout(poll, 10);
    })();
  });
}
function uniformsOf(gl, prog, names) {
  const u = {};
  for (const n of names) u[n] = gl.getUniformLocation(prog, n);
  return u;
}

const SAFE_MODE_BANNER = "The flash limiter could not start: the VJ rig runs in its safe mode (the sets play; pad effects are refused).";
function initGL() {
  const gl = G.gl || canvas.getContext("webgl2", { alpha: false, antialias: false, depth: false, stencil: false,
    premultipliedAlpha: false, preserveDrawingBuffer: false, powerPreference: "high-performance" });
  if (!gl) {
    banner("WebGL2 is unavailable: the VJ rig needs Chrome or Edge with WebGL2.");
    recordError("runtime", null, "WebGL2 unavailable");
    return false;
  }
  G.gl = gl;
  G.parallel = gl.getExtension("KHR_parallel_shader_compile");
  const half = gl.getExtension("EXT_color_buffer_half_float"), full = gl.getExtension("EXT_color_buffer_float");
  if (half || full) { G.fbInternal = gl.RGBA16F; G.fbType = gl.HALF_FLOAT; G.fbFormat = "RGBA16F"; }
  else { G.fbInternal = gl.RGBA8; G.fbType = gl.UNSIGNED_BYTE; G.fbFormat = "RGBA8"; }
  gl.disable(gl.DEPTH_TEST);
  gl.disable(gl.BLEND);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);

  // the VJ strip: float texels read with texelFetch, so NEAREST (a float texture is not filterable everywhere)
  G.stripTex = createTexture(gl, gl.NEAREST);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, STRIP.W, STRIP.H, 0, gl.RGBA, gl.FLOAT, strip);
  G.audioTex = createTexture(gl, gl.LINEAR);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, AUDIO_TEX_W, 2, 0, gl.RED, gl.UNSIGNED_BYTE, audioBytes);
  G.blackTex = createTexture(gl, gl.LINEAR);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 255]));
  // the laser engine's records (Lasers v2): RGBA32F, SEG_TEXELS (2) wide, one row per record, read with texelFetch
  G.segTex = createTexture(gl, gl.NEAREST);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, SEG_TEXELS, MAX_SEGMENTS, 0, gl.RGBA, gl.FLOAT, null);
  G.pool = [];
  G.ov = null;
  G.frz = null;
  try {
    G.ovProg = linkSync(gl, OVERLAY_FS);
    G.ovU = uniformsOf(gl, G.ovProg, ["u_prevOv", "u_res", "u_keep", "u_wave", "u_waveB", "u_waveCol", "u_laser", "u_laserB",
      "u_laserCol", "u_part", "u_partB", "u_partCol", "u_note", "u_noteCol", "u_bars", "u_barsPhase", "u_barsCol",
      "u_sparkle", "u_sparkleT", "u_sparkleCol"]);
    G.compProg = linkSync(gl, COMPOSITE_FS);
    G.compU = uniformsOf(gl, G.compProg, ["u_a", "u_b", "u_ov", "u_frz", "u_hist", "u_stut", "u_meter", "u_res", "u_mix",
      "u_kal", "u_kalN", "u_kalRot", "u_glitch", "u_glitchT", "u_gSize", "u_gSeed", "u_gAge", "u_gMode", "u_freeze",
      "u_freezeZoom", "u_wave", "u_waveB", "u_flash", "u_flashGap", "u_invert", "u_bright", "u_sat", "u_accent", "u_metro",
      "u_metroCol", "u_bloom", "u_bloomCol", "u_punch", "u_blur", "u_shake", "u_dip", "u_dipGranted", "u_dipSafe", "u_snare",
      "u_beam", "u_beamGain"]);
    gl.useProgram(G.compProg);
    gl.uniform1i(G.compU.u_a, 0); gl.uniform1i(G.compU.u_b, 1); gl.uniform1i(G.compU.u_ov, 2); gl.uniform1i(G.compU.u_frz, 3);
    gl.uniform1i(G.compU.u_hist, 4); gl.uniform1i(G.compU.u_stut, 5); gl.uniform1i(G.compU.u_meter, 6);
    gl.uniform1i(G.compU.u_beam, 7);
    G.beamProg = linkSync(gl, BEAM_FS);
    G.beamU = uniformsOf(gl, G.beamProg, ["u_seg", "u_n", "u_res"]);
    gl.useProgram(G.beamProg);
    gl.uniform1i(G.beamU.u_seg, 0);
    gl.useProgram(G.ovProg);
    gl.uniform1i(G.ovU.u_prevOv, 0);
    G.meterProg = linkSync(gl, METER_FS);
    G.meterU = uniformsOf(gl, G.meterProg, ["u_a", "u_b", "u_ov", "u_mix", "u_accent"]);
    gl.useProgram(G.meterProg);
    gl.uniform1i(G.meterU.u_a, 0); gl.uniform1i(G.meterU.u_b, 1); gl.uniform1i(G.meterU.u_ov, 2);
    G.meter2Prog = linkSync(gl, METER2_FS);
    G.meter2U = uniformsOf(gl, G.meter2Prog, ["u_src", "u_block"]);
    gl.useProgram(G.meter2Prog);
    gl.uniform1i(G.meter2U.u_src, 0);
    G.copyProg = linkSync(gl, COPY_FS);
    G.copyU = uniformsOf(gl, G.copyProg, ["u_src"]);
    gl.useProgram(G.copyProg);
    gl.uniform1i(G.copyU.u_src, 0);
  } catch (err) {
    recordError("compile", "vj-built-in", err.message || err);
    banner("A built-in VJ shader failed to compile; see the console.");
    return false;
  }
  if (stage) stage.initGL(gl, { internalFormat: G.fbInternal, type: G.fbType });   // transitions and the look
  // gate v2, the final-output flash limiter. Without a float target it cannot meter: the page then runs in its safe mode
  // (every pad effect refused) and says so.
  if (G.limiter) { try { G.limiter.dispose(); } catch { /* a lost context took it */ } }
  G.limiter = null;
  try {
    if (LIMITER_MODE === "off") throw new Error("?limiter=off: the safe mode, asked for");
    G.limiter = createLimiter(gl, { preInternal: G.fbInternal, preType: G.fbType, decide: LIMITER_MODE === "cpu" ? "cpu" : "auto",
                                    lateFrames: LIMITER_MODE === "late" ? 120 : 0 });
    G.limiterError = "";
  } catch (err) {
    G.limiterError = String(err.message || err);
    recordError("compile", "vj-limiter", G.limiterError);
    banner(SAFE_MODE_BANNER);
  }
  return true;
}

function createPair(w, h) {
  const gl = G.gl;
  const pair = { w, h, texs: [], fbos: [], read: 0 };
  for (let i = 0; i < 2; i++) {
    const tex = createTexture(gl, gl.LINEAR);
    gl.texImage2D(gl.TEXTURE_2D, 0, G.fbInternal, w, h, 0, gl.RGBA, G.fbType, null);
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    pair.texs.push(tex);
    pair.fbos.push(fbo);
  }
  const complete = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  if (!complete && G.fbInternal !== gl.RGBA8) {
    deletePair(pair);
    recordError("runtime", null, "RGBA16F framebuffer incomplete; falling back to RGBA8");
    G.fbInternal = gl.RGBA8; G.fbType = gl.UNSIGNED_BYTE; G.fbFormat = "RGBA8";
    return createPair(w, h);
  }
  clearPair(pair);
  return pair;
}
function deletePair(pair) {
  const gl = G.gl;
  if (!gl || !pair) return;
  for (const t of pair.texs) gl.deleteTexture(t);
  for (const f of pair.fbos) gl.deleteFramebuffer(f);
}
function clearPair(pair) {
  const gl = G.gl;
  gl.clearColor(0, 0, 0, 1);   // alpha 1: presets that keep a field in alpha store it as 1 - field, so this is empty
  for (let i = 0; i < pair.fbos.length; i++) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, pair.fbos[i]);
    gl.viewport(0, 0, pair.w, pair.h);
    gl.clear(gl.COLOR_BUFFER_BIT);
  }
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  pair.read = 0;
}
function takePair(w, h) {
  for (let i = 0; i < G.pool.length; i++) {
    if (G.pool[i].w === w && G.pool[i].h === h) {
      const pair = G.pool.splice(i, 1)[0];
      clearPair(pair);
      return pair;
    }
  }
  return createPair(w, h);
}
function releaseFb(set) {
  if (!set || !set.fb) return;
  G.pool.push(set.fb);
  set.fb = null;
  while (G.pool.length > 2) deletePair(G.pool.shift());
}
function dropAllFbs() {
  for (const s of sets) { deletePair(s.fb); s.fb = null; }
  for (const p of G.pool) deletePair(p);
  G.pool = [];
  deletePair(G.ov); G.ov = null;
  if (G.frz) { deletePair(G.frz); G.frz = null; }
  for (const k of ["cmp", "stut", "meter1", "meterMid", "meter2", "beam"]) if (G[k]) { deletePair(G[k]); G[k] = null; }
}
function ensureFb(set) {
  if (set.fb && (set.fb.w !== G.width || set.fb.h !== G.height)) { deletePair(set.fb); set.fb = null; }
  if (!set.fb) set.fb = takePair(G.width, G.height);
}

function resizeIfNeeded() {
  const rect = stageEl.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, DPR_CAP);
  const w = Math.max(1, Math.round(rect.width * dpr * G.scale));
  const h = Math.max(1, Math.round(rect.height * dpr * G.scale));
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
    dropAllFbs();
  }
  G.width = canvas.width;
  G.height = canvas.height;
  if (!G.ov) G.ov = createPair(G.width, G.height);
  if (!G.frz) G.frz = createSingle(G.width, G.height);   // one target is enough for a freeze
  if (!G.cmp) G.cmp = createPair(G.width, G.height);     // the composite's own pair: its previous frame feeds the glitch
  if (!G.stut) G.stut = createSingle(G.width, G.height); // the frame held at the last glitch (the stutter's slices)
  if (!G.beam) G.beam = createSingle(G.width, G.height); // the beam layer (Lasers v2): redrawn every frame, no feedback
  if (!G.meter1) G.meter1 = createSingle(64, 36, true);  // the scene meter: NEAREST, read with texelFetch
  if (!G.meterMid) G.meterMid = createSingle(8, 6, true);
  if (!G.meter2) G.meter2 = createSingle(1, 1, true);
}
function createSingle(w, h, nearest = false) {
  const gl = G.gl;
  const tex = createTexture(gl, nearest ? gl.NEAREST : gl.LINEAR);
  gl.texImage2D(gl.TEXTURE_2D, 0, G.fbInternal, w, h, 0, gl.RGBA, G.fbType, null);
  const fbo = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  const single = { w, h, texs: [tex], fbos: [fbo], read: 0 };
  clearPair(single);
  return single;
}

// ------------------------------------------------------------------------------------------------- the sets --
function parseHeader(src) {
  const lines = src.split(/\r?\n/);
  if (lines[0].trim() !== "#version 300 es") throw new Error("line 1 must be '#version 300 es'");
  if (!lines[1] || !lines[1].startsWith("//!")) throw new Error("line 2 must be the '//! {json}' header");
  return JSON.parse(lines[1].slice(3));
}
async function loadSet(set) {
  try {
    const res = await fetch(`presets/${set.id}.frag`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    set.source = await res.text();
    const header = parseHeader(set.source);
    set.name = (header.name || set.id).replace(/^VJ\s+/, "");
    set.author = header.author || "";
    set.tags = Array.isArray(header.tags) ? header.tags : [];
    set.vj = set.tags.includes("vj");
    set.laserHeads = set.tags.includes("laser-heads");   // Lasers v2: the scene draws its own laser heads from the head bus
    set.params = (Array.isArray(header.params) ? header.params : []).filter((p) => p && p.k >= 1 && p.k <= 8).slice(0, 8);
    set.defaults.fill(0.5);
    set.trailsK = -1;
    for (const p of set.params) {
      set.defaults[p.k - 1] = clamp(+p.default || 0, 0, 1);
      if (String(p.name).toLowerCase() === "trails") set.trailsK = p.k - 1;
    }
    set.knobs.set(set.defaults);
    await compileSet(set);
  } catch (err) {
    set.status = "broken";
    set.problem = String(err.message || err).split("\n")[0];
    recordError("load", set.id, err.message || err);
  }
  renderSetList();
}
async function compileSet(set) {
  const gl = G.gl;
  if (!gl || G.lost) return;
  try {
    const prog = await linkAsync(gl, set.source);
    set.program = prog;
    set.uniforms = uniformsOf(gl, prog, PLAY_UNIFORMS);
    gl.useProgram(prog);
    if (set.uniforms.u_video) gl.uniform1i(set.uniforms.u_video, 0);
    if (set.uniforms.u_prev) gl.uniform1i(set.uniforms.u_prev, 1);
    if (set.uniforms.u_audio) gl.uniform1i(set.uniforms.u_audio, 2);
    set.status = "ok";
    set.problem = "";
  } catch (err) {
    set.program = null;
    set.status = "broken";
    set.problem = String(err.message || err).split("\n")[0];
    recordError("compile", set.id, err.message || err);
  }
}
function validSet(i) { return i >= 0 && i < sets.length && sets[i].status !== "broken"; }
function nextValid(from) {
  for (let s = 1; s <= sets.length; s++) {
    const i = (from + s) % sets.length;
    if (validSet(i) && i !== from) return i;
  }
  return from;
}
function prevValid(from) {
  for (let s = 1; s <= sets.length; s++) {
    const i = (from - s + sets.length) % sets.length;
    if (validSet(i) && i !== from) return i;
  }
  return from;
}
// Switch to set `to` (the next valid one by default): the stage (vj-stage.js) plans it on the next bar or beat, in the
// panel's transition style (or `style`), two beats long; 1.2 s from now without a beat.
// THE SAFE MODE's scenes (no limiter running): a switch is a crossfade, at most one a second, never cut short by the next
// (a switch while a fade runs would land the fade at once: a cut, and a storm of them flashes like pads do)
const SAFE_SCENE_MIN_MS = 1000;
let safeSceneAt = -1e9;
function safeSceneRefused(nowMs) {
  if (limiterLive()) return false;
  if (deck.running || nowMs - safeSceneAt < SAFE_SCENE_MIN_MS) { safeRefused++; return true; }
  safeSceneAt = nowMs;
  return false;
}
function nextSet(to = null, nowMs = performance.now(), style = null) {
  if (safeSceneRefused(nowMs)) return;
  if (deck.running) finishFade();
  const target = to === null ? nextValid(deck.a) : to;
  if (!validSet(target) || target === deck.a) return;
  deck.b = target;
  deck.running = true;
  deck.from = effectiveManualMix();
  const plan = stage ? stage.plan(nowMs, deck.a, target, style) : null;
  if (plan) {
    deck.start = plan.startMs; deck.ms = plan.ms; deck.code = plan.code; deck.seed = plan.seed;
  } else {
    const p = beat.period();
    deck.start = nowMs; deck.code = 0;
    deck.ms = beat.alive(nowMs) && p > 0 ? clamp(XFADE_BEATS * p, 400, 4000) : XFADE_FALLBACK_MS;
  }
  toast(`→ ${sets[target].name}${plan && plan.on !== "now" ? ` · on the ${plan.on}` : ""}`);
  renderSetList();
}
function finishFade() {
  const old = sets[deck.a];
  deck.a = deck.b;
  deck.b = nextValid(deck.a);
  deck.running = false;
  // the crossfade fader picks up again only once it is pulled back to the bottom (no jump to the new cued set)
  deck.pickup = T.xfade <= 0.02;
  if (old !== sets[deck.a] && old !== sets[deck.b]) releaseFb(old);
  renderSetList();
  renderParams();
  queueSceneReport(false);        // the KeyLab's screen shows the scene that landed
  if (stage) stage.landed(performance.now());
}
function selectSet(i, boot = false) {   // a cut, for the test hook and a click while nothing plays
  if (!validSet(i)) return false;
  if (!boot && !limiterLive() && sets[deck.a]) {   // the safe mode: no cuts, a crossfade at most once a second
    if (i === deck.a) return true;
    const before = deck.b, running = deck.running;
    nextSet(i);
    return deck.running && (!running || deck.b !== before);
  }
  if (deck.running) finishFade();
  const old = sets[deck.a];
  deck.a = i;
  deck.b = nextValid(i);
  if (old !== sets[deck.a] && old !== sets[deck.b]) releaseFb(old);
  renderSetList();
  renderParams();
  queueSceneReport(false);
  return true;
}
function effectiveManualMix() { return deck.pickup ? T.xfade : 0; }
function currentMix(nowMs) {
  const manual = effectiveManualMix();
  if (!deck.running) return manual;
  const p = clamp((nowMs - deck.start) / Math.max(deck.ms, 1), 0, 1);
  return deck.from + (1 - deck.from) * smooth(p);
}

// ------------------------------------------------------------------------------------------------- the events --
// `from` is "engine" (the stream, or the test hook speaking for it) or "demo" (the page's own scripted show). The demo's
// hello and status never reach the engine link: they would overwrite a connected engine's own (its leds, its name in the
// HUD), and its events are counted apart so the engine's counters stay the engine's.
function handleEvent(raw, from = "engine") {
  const ev = parseEvent(raw);
  const fromDemo = from === "demo";
  if (!ev) { if (!fromDemo) engine.bad++; return; }
  if (fromDemo) engine.demoEvents++; else engine.events++;
  const nowMs = performance.now();
  const nowS = nowMs / 1000;
  switch (ev.t) {
    case "hello":
      if (!fromDemo) {
        engine.link.event(ev); harm.reset();     // a new engine: its key and tension are still to come
        tapPads = tapPadsOf(ev);                 // the pads it taps the tempo with (pad 12 by default): no effects
        sceneReport.sentKey = "";                // ... and it has not been told which scene shows
        queueSceneReport(false);
      }
      break;
    case "scene":                                // the engine's echo of our own report (the screen shows it)
      if (!fromDemo) sceneReport.last = ev;
      break;
    case "status":
      if (!fromDemo) engine.link.event(ev);
      break;
    case "key":
      if (harm.event(ev)) keyChange(nowS);
      if (themes.dir) { themes.keyEvents++; themes.dir.onKey(ev, nowMs, themeClock); }   // key auto (chordsense's key)
      break;
    case "tap":                                  // the Tap button / pad 12 reaching the engine's beat clock
      tapLast = { mode: ev.mode, count: ev.count, bpm: ev.bpm, shift: ev.shift, at: Math.round(nowMs) };
      break;
    case "track":                                // a new track: key auto starts over (the song database's key first)
      if (themes.dir) {
        themes.dir.newTrack();
        if (ev.key_db) themes.dir.onKey({ name: ev.key_db, src: "db" }, nowMs, themeClock);
      }
      break;
    case "tension":
      harm.event(ev);
      break;
    case "beat":
      beat.schedule(nowMs, ev);
      break;
    case "energy":
      bands.energy(ev, nowMs);
      energy.last = nowMs;
      if (!fromDemo) { energy.stamps[energy.events % 256] = nowMs; energy.events++; }
      break;
    case "hit": {
      hit.pulse = Math.max(hit.pulse, ev.strength);
      bands.hit(ev.band, ev.strength);
      if (options.hits && ev.band !== "hat") hit.bloom = Math.max(hit.bloom, ev.strength);
      break;
    }
    case "chord":
      setChord(ev, nowS);
      break;
    case "note":
      if (ev.on && ev.vel > 0) noteOn(ev.key, ev.vel, nowS); else noteOff(ev.key);
      break;
    case "pedal":
      setSustain(ev.on);
      break;
    case "pad":
      if (ev.on && ev.vel > 0) padOn(ev.pad, ev.vel, ev.src, nowS); else padOff(ev.pad, nowS, ev.src);
      break;
    case "ctl":
      onCtl(ev);
      break;
  }
}

function setChord(ev, nowS) {
  const key = ev.pcs.join(",");
  const changed = ev.name !== chord.name || key !== chord.pcs.join(",");
  chord.name = ev.name;
  chord.root = ev.root;
  chord.pcs = ev.pcs;
  chord.src = ev.src;
  chord.quality = ev.quality;
  chord.roman = ev.roman;
  chord.key = ev.key;
  chord.bass = ev.bass;
  chord.conf = ev.conf;
  chord.t = nowS;
  // 'N' (the audio hears no chord: drums, noise, a lone line) is no chord for the harmony feel either
  feelState.chord = ev.name && !(ev.name === "N" && ev.root < 0) ? { name: ev.name } : null;
  if (changed && ev.changed) chordChange(nowS);
}
// The accent every harmonic change gives: the chord pulse (strip row 0, texel 15) and a restart of the constellation's
// draw-on. A chord change gives it whole and moves the palette to the chord's colours; a key change (the engine's key
// event) gives a smaller one and leaves the palette to the chords. Neither asks the flash gate: no flash, ever.
function chordAccent(nowS, strength) {
  chordPulse = Math.max(chordPulse, strength);
  if (nowS - lastDrawRestart > 0.25) { drawOn = 0; lastDrawRestart = nowS; }
}
function keyChange(nowS) {
  keyAccents++;
  chordAccent(nowS, KEY_ACCENT);
}
function chordChange(nowS) {
  palBefore.set(palNow);
  travel = 0;
  chordAccent(nowS, 1);
  // the chord's stops: its root, then its other tones by how far above the root they sit
  const root = chord.root >= 0 ? chord.root : (chord.pcs[0] ?? -1);
  if (root < 0) { chordPresence = 0; return; }
  const tones = [...new Set([root, ...chord.pcs])].sort((a, b) => ((a - root + 12) % 12) - ((b - root + 12) % 12));
  const fill = [root, (root + 4) % 12, (root + 7) % 12, (root + 10) % 12];
  for (let k = 0; k < 4; k++) {
    const pc = tones[k] ?? fill[k];
    chordStops[k * 3] = PC_RGB[pc * 3]; chordStops[k * 3 + 1] = PC_RGB[pc * 3 + 1]; chordStops[k * 3 + 2] = PC_RGB[pc * 3 + 2];
  }
  chordPresence = 1;
}

function lowestOther(key) {
  for (let k = 0; k < 128; k++) if (k !== key && (kHeld[k] || kSus[k])) return k;
  return -1;
}
function noteOn(key, vel, nowS) {
  kHeld[key] = 1; kSus[key] = 0; kVel[key] = vel; kT0[key] = nowS; kStrike[key] = 1;
  pcStrike[key % 12] = 1;
  feelState.sounding.set(key, { vel: Math.round(vel * 127), t0: nowS, held: true, pedal: false, tRelease: null, strike: true });
  const low = lowestOther(key);
  pedal.strike(key, nowS, pedalSignature(low, chord.name));
  const g = glints[glintNext];
  glintNext = (glintNext + 1) % glints.length;
  g.x = clamp((key - 21) / 87, 0, 1) * 1.8 - 0.9;
  g.t0 = nowS;
  g.vel = vel;
  g.pc = key % 12;
}
function noteOff(key) {
  if (!kHeld[key]) return;
  kHeld[key] = 0;
  const entry = feelState.sounding.get(key);
  if (sustainPedal) {
    kSus[key] = 1;
    if (entry) { entry.held = false; entry.pedal = true; entry.tRelease = performance.now() / 1000; }
  } else {
    kSus[key] = 0;
    feelState.sounding.delete(key);
  }
}
function setSustain(on) {
  sustainPedal = on;
  feelState.pedal = on;
  if (!on) {
    for (let k = 0; k < 128; k++) {
      if (kSus[k]) { kSus[k] = 0; if (!kHeld[k]) feelState.sounding.delete(k); }
    }
  }
}

// ------------------------------------------------------------------------------------------ pads and effects --
function padOn(pad, vel, src, nowS = performance.now() / 1000) {
  const i = pad - 1;
  // a pad the engine says taps its tempo (its hello's tap list: pad 12 by default since 2026-10-25) is the tap and
  // nothing else: the engine's beat clock takes the press, the page fires no effect for it
  if (isTapPad(tapPads, pad, src)) { tapPresses++; padPress[i] = 1; padT0[i] = nowS; lastPadSrc = src; return; }
  const action = padMap[i];
  // the beat snap: an effect pad waits for the next 16th of a live beat (controls never wait)
  if (options.snap && EFFECTS[action]) {
    const wait = snapDelayMs(nowS * 1000, beat);
    if (wait > 0) {
      for (const q of snapQ) if (q.pad === pad) q.off = false;
      snapQ.push({ pad, vel, src, at: nowS * 1000 + wait, off: false, arrive: nowS * 1000, beatAt: beat.lastBeat, grid: beat.period() / 4 });
      padHeld[i] = 1;
      return;
    }
  }
  padFire(pad, vel, src, nowS, nowS * 1000);
}
function padFire(pad, vel, src, nowS, arriveMs, snap = null) {
  const i = pad - 1;
  padHeld[i] = 1;
  padT0[i] = nowS;
  padPress[i] = 1;
  lastPadSrc = src;
  const action = padMap[i];
  // THE SAFE MODE (2026-10-25, the round-2 verifier): without a running limiter, the one-shots, the glitch, the zoom
  // punch and Invert put 5-10 flashes a second on the screen with only the FlashGate in front of them. So until the
  // limiter runs (and for good if it cannot) every pad effect is refused; the controls still work.
  if (EFFECTS[action] && !limiterLive()) { safeRefused++; if (action === "laser") lasers.refused++; return; }
  if (action === "laser" && !options.lasersClassic) laserHit(pad, vel, src, nowS, arriveMs, snap);
  else if (EFFECTS[action]) {
    const f = triggerEffect(action, vel, pad, nowS);
    if (f) {   // the latency record: this event's arrival; the frame that draws it fills in `frame` and `env`
      // performance.now() for the page's own gaps; Date.now() (the wall clock the engine shares on this machine) so a
      // receipt can measure from the moment the engine SENT the event, queueing in the page included
      latency.records.push({ pad, type: action, arrive: +arriveMs.toFixed(2), fired: +(nowS * 1000).toFixed(2), frame: null,
                             env: null, serial: f.serial, src, arriveWall: Date.now(), frameWall: null,
                             snapAt: snap ? +snap.at.toFixed(2) : null, snapBeat: snap ? +snap.beatAt.toFixed(2) : null,
                             snapGrid: snap ? +snap.grid.toFixed(3) : null });
      if (latency.records.length > LATENCY_KEEP) latency.records.shift();
    }
  } else if (action === "dampen") dampenAll(nowS);
  else if (action === "choke") choke();
  else if (action === "kill") toggleKill();
  else if (action === "next") nextSet();
}
function padOff(pad, nowS = performance.now() / 1000, src = "") {
  if (src && isTapPad(tapPads, pad, src)) return;                       // the tap's release: nothing to let go of
  for (const q of snapQ) if (q.pad === pad) { q.off = true; return; }   // still waiting for its 16th: let go right after
  padHeld[pad - 1] = 0;
  fx.release(pad, nowS);
  if (lasers.held && lasers.pad === pad) { lasers.held = false; lasers.eng.release(nowS * 1000); }
}
// ------------------------------------------------------------------------------------------------ Lasers v2 --
// Pad 2 (the pad mapped to the laser) is the laser engine's hit (vj-lasers.js): it deals the pattern, the head order, the
// colour split and the bank; the retrigger tiers (beats since the last press) and the velocity tiers (soft single,
// medium one-two, hard triple: Daniel, 2026-10-25, "4. option 1!") or the dial's fixed gate pick the gate; holding it runs
// the section's loop until release. Its light is the beam layer's; the impact layer still punches the scene behind it.
function laserHit(pad, vel, src, nowS, arriveMs, snap = null) {
  const t = nowS * 1000;
  lasers.cut = false; lasers.gain = 1; lasers.dampT = null;
  const info = lasers.eng.hit(t, vel);
  lasers.hits++;
  lasers.pad = pad; lasers.held = true;
  lasers.last = { t: +t.toFixed(1), vel: info.vel, tier: info.tier, gate: info.gate, pattern: info.pattern, order: info.order,
                  colour: info.colour, bank: info.bank, start: info.start, heads: info.heads ? info.heads.length : 0,
                  beams: info.beams, hero: !!info.hero, fast: !!info.fast, ext: !!info.ext, shape: info.shape || null, src };
  lasers.log.push(lasers.last);
  if (lasers.log.length > 64) lasers.log.shift();
  // the impact layer: the scene punches, shakes and dips behind the beams (never the beams themselves)
  impact.hit("laser", vel, nowS, { seed: ((info.id || lasers.hits) * 0.6180339887) % 1, granted: false, x: 0, y: 0.05,
                                   punch: options.punch && limiterLive() });
  latency.records.push({ pad, type: "laser", v2: true, arrive: +arriveMs.toFixed(2), fired: +t.toFixed(2), frame: null,
                         env: null, lit: null, serial: -1 - lasers.hits, src, arriveWall: Date.now(), frameWall: null,
                         gate: info.gate, tier: info.tier, snapAt: snap ? +snap.at.toFixed(2) : null,
                         snapBeat: snap ? +snap.beatAt.toFixed(2) : null, snapGrid: snap ? +snap.grid.toFixed(3) : null });
  if (latency.records.length > LATENCY_KEEP) latency.records.shift();
}
// The laser engine's frame (before the strip is built: a `laser-heads` scene reads the head bus from it).
function updateLasers(nowMs, dt) {
  const eng = lasers.eng;
  const live = sets[deck.running ? deck.b : deck.a];
  lasers.heroOnly = !!(live && live.laserHeads);
  const asp = G.width > 0 && G.height > 0 ? G.width / G.height : 16 / 9;
  const out = eng.frame(nowMs, { aspect: asp });
  lasers.out = out;
  for (const e of out.events) {
    if (e.type === "pulse") lasers.pulses++;
    else if (e.type === "flash") {                 // the phrase's last syllable: a white flash, through the FlashGate
      lasers.flashes++;
      if (!lasers.cut && limiterLive()) requestFlash(nowMs / 1000, 0.5 * T.accent, 0.1);
    }
  }
  if (lasers.dampT !== null) lasers.gain *= Math.exp(-dt / LASER_DAMPEN_TAU_S);
  const p = packBeams(out, lasers.heroOnly, lasers.packed);
  lasers.seg = p.seg; lasers.n = lasers.cut || lasers.gain < 0.002 ? 0 : p.n;
  lasers.frames++;
  if (out.n > 0) lasers.litFrames++;
  if (out.area.over) lasers.over++;
  lasers.maxWindow = Math.max(lasers.maxWindow, out.area.window);
  lasers.maxFrame = Math.max(lasers.maxFrame, out.area.frame);
  // the head bus, for a scene that draws its own heads (the Cathedral): the engine's levels scaled by Dampen / Choke
  lasers.busOn = lasers.heroOnly && !options.lasersClassic;
  if (lasers.busOn) {
    headBus(eng, lasers.bus);
    const g = lasers.cut ? 0 : Math.min(1, lasers.gain);
    for (let k = 4; k < 16; k++) {
      const v = lasers.bus[k], slot = Math.floor(v), lv = (v - slot) * g;
      lasers.bus[k] = lv > 1e-4 ? slot + lv : 0;
    }
    if (lasers.cut) lasers.bus[3] = 1;
  }
}
// the beam layer: the frame's records into the texture, then the pass (cleared once when there is nothing to draw)
function renderBeams() {
  const gl = G.gl, b = G.beam;
  gl.bindFramebuffer(gl.FRAMEBUFFER, b.fbos[0]);
  gl.viewport(0, 0, b.w, b.h);
  if (!lasers.n || options.lasersClassic) {
    if (!G.beamClear) { gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT); G.beamClear = true; }
    return;
  }
  G.beamClear = false;
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, G.segTex);
  gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, SEG_TEXELS, lasers.n, gl.RGBA, gl.FLOAT, lasers.seg, 0);
  gl.useProgram(G.beamProg);
  gl.uniform1i(G.beamU.u_n, lasers.n);
  gl.uniform2f(G.beamU.u_res, b.w, b.h);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}
function laserGate() { lasers.eng.set({ gateMode: lasers.dial.gate }); }
function setVibrate(on) {
  options.vibrate = !!on;
  lasers.eng.setVibrate(options.vibrate, performance.now());
  safeSet(STORE.opts, JSON.stringify(options));
  const box = $("opt-vibrate");
  if (box) box.checked = options.vibrate;
}
function setLasersClassic(on) {
  options.lasersClassic = !!on;
  if (lasers.held) { lasers.held = false; lasers.eng.release(performance.now()); }
  safeSet(STORE.opts, JSON.stringify(options));
  const box = $("opt-classic");
  if (box) box.checked = options.lasersClassic;
}
function fireSnapped(nowMs) {
  for (let k = 0; k < snapQ.length;) {
    const q = snapQ[k];
    if (q.at > nowMs) { k++; continue; }
    snapQ.splice(k, 1);
    padFire(q.pad, q.vel, q.src, nowMs / 1000, q.arrive, q);
    if (q.off) { padHeld[q.pad - 1] = 0; fx.release(q.pad, nowMs / 1000 + 0.06); }
  }
}
function choke() {
  fx.choke();
  impact.clear();
  snapQ.length = 0;
  flash.peak = 0;
  // the lasers: every beam cut now (spec 1.8), until the next hit; a held loop let go
  lasers.cut = true; lasers.held = false;
  lasers.eng.release(performance.now());
}
// Dampen (pad 9, Q): every effect released fast; the lasers' loops end and their light fades in ~60 ms
function dampenAll(nowS) {
  fx.dampen(nowS);
  lasers.held = false;
  lasers.eng.release(nowS * 1000);
  if (lasers.n || (lasers.out && lasers.out.n)) lasers.dampT = nowS * 1000;
}
// Ask the gate for a full-frame flash; granted flashes decay from `peak` over `decay` seconds.
function requestFlash(nowS, peak, decay) {
  if (!gate.request(nowS)) return false;
  flash.t0 = nowS;
  flash.peak = clamp(peak, 0, 1);
  flash.decay = decay;
  flash.gap = gate.prevGap;
  return true;
}
function triggerEffect(type, vel, pad, nowS) {
  let granted = true;
  if (type === "flash") granted = requestFlash(nowS, (0.45 + 0.55 * vel) * T.accent, 0.08 + 0.14 * vel);
  else if (type === "invert") granted = gate.request(nowS);   // its onset spends a slot; refused, it fades in slowly
  else if (type === "strobe") strobeNext = nowS;
  const f = fx.trigger(type, vel, nowS, { pad, granted });
  if (type === "freeze") freezeCapture = true;
  if (type === "glitch") stutterCapture = true;               // the stutter's slices: the frame as it was at the hit
  // the impact layer: punch, shake, dip, afterglow (a white flash's dip rides its own granted slot; any other dip is held
  // under the flash line by the composite's scene meter: vj-core.js dipSafeDepth)
  if (f) {
    const at = hitOrigin(f);
    impact.hit(type, vel, nowS, { seed: f.seed, granted: type === "flash" && granted, x: at[0], y: at[1],
                                 punch: options.punch && limiterLive() });
  }
  return f;
}
// Where an effect instance sits in the preset's centred space (the overlay's own placement), for the strip's hit texel.
const originScratch = [0, 0];
function hitOrigin(f) {
  const asp = G.width / Math.max(G.height, 1);
  if (f.type === "shockwave") { originScratch[0] = (f.seed - 0.5) * 0.3 * asp; originScratch[1] = (((f.seed * 7.31) % 1) - 0.5) * 0.25; }
  else if (f.type === "laser") {
    const slot = f.serial % 4;
    originScratch[0] = slot === 1 ? -0.48 * asp : slot === 2 ? 0.48 * asp : 0;
    originScratch[1] = slot === 3 ? 0.52 : -0.52;
  } else if (f.type === "particles") { originScratch[0] = (f.seed - 0.5) * 0.5 * asp; originScratch[1] = (((f.seed * 3.7) % 1) - 0.5) * 0.3; }
  else { originScratch[0] = 0; originScratch[1] = 0; }
  return originScratch;
}
function toggleKill() {
  const now = performance.now();
  kill.pending = kill.pending === null ? (kill.target > 0.5 ? 0 : 1) : null;   // a second press before the beat cancels
  if (kill.pending !== null) {
    const at = beat.nextBeatAt(now);
    kill.at = at === null ? now : at;
  } else kill.at = null;
}

// ------------------------------------------------------------------------------------------------- controls --
function onCtl(ev) {
  lastCtl = { id: ev.id, kind: ev.kind, value: ev.value, delta: ev.delta, target: null };
  // Rewind / Fast forward step the sets, always (Daniel, 2026-10-25: "lets try always we can make it an option"): the
  // DAW port's CC 25 / 26, through the ONE scene path (vj-core.js SceneControl: on the press, never the release; a held
  // button repeating 127 moves once; a bounce inside 160 ms is one press). Our FL script swallows them (SCRUB_TO_FL), so
  // FL does not scrub as well. The keys input's same numbers are not the transport (they reach the control map like
  // any control, where nothing binds them by default), and ?transport=off hands the DAW port's back to the control map
  // too, unbound and free to learn.
  if (TRANSPORT_SETS && (ev.id === "cc25" || ev.id === "cc26") && ev.port !== "midi") {
    lastCtl.target = "sets";
    sceneCtl(ev, ev.id === "cc26" ? "sceneNext" : "scenePrev", performance.now());
    return;
  }
  if (stage && stage.onCtl(ev)) { lastCtl.target = "look"; return; }   // the look's fader (vj-stage.js)
  if (learnTarget) {
    ctlMap = learnBinding(ctlMap, ev.id, learnTarget);
    lastCtl.target = learnTarget;
    saveCtlMap();
    $("learn-status").textContent = `${ev.id} → ${targetLabel(learnTarget)}`;
    learnTarget = null;
    renderTargets();
    return;
  }
  const target = ctlMap[ev.id];
  lastCtl.target = target || null;
  if (!target) return;
  const nowMs = performance.now();
  if (SCENE_ACTION_IDS.includes(target)) sceneCtl(ev, target, nowMs);
  else if (LASER_ACTION_IDS.includes(target)) laserCtl(ev, target, nowMs);
  else if (FAMILY_ACTION_IDS.includes(target)) familyCtl(ev, target, nowMs);
  else setTarget(target, ev);
}
function saveCtlMap() { safeSet(STORE.ctl, JSON.stringify(serializeCtlMap(ctlMap))); }
// the laser actions (vj-core.js LASER_ACTIONS): the dial steps the gate, its click goes back to AUTO, the toggles
function laserCtl(ev, action, nowMs) {
  if (action === "laserGate") {
    if (lasers.dial.turn(ev, nowMs)) { laserGate(); toast(`laser gate: ${gateLabel(lasers.dial.gate)}`); }
    return;
  }
  if (!lasers.presses.press(ev, action, nowMs)) return;
  if (action === "laserAuto") { lasers.dial.auto(); laserGate(); toast("laser gate: AUTO"); }
  else if (action === "laserVibrate") { setVibrate(!options.vibrate); toast(options.vibrate ? "lasers vibrate" : "vibrate off"); }
  else if (action === "laserClassic") { setLasersClassic(!options.lasersClassic); toast(options.lasersClassic ? "lasers: classic burst" : "Lasers v2"); }
  else if (action === "themeLock" && themes.dir) { themes.dir.setLock(!themes.dir.locked); toast(themes.dir.locked ? "theme locked" : "theme unlocked"); }
}
// a family tab: that family's theme for the section, again inside a bar its next theme (vj-themes.js ThemeDirector)
function familyCtl(ev, action, nowMs) {
  const a = FAMILY_ACTIONS.find((x) => x.id === action);
  if (!a || !lasers.presses.press(ev, action, nowMs)) return;
  pickFamily(a.family, nowMs);
}
function pickFamily(family, nowMs = performance.now()) {
  if (!themes.dir) return false;
  themes.family = family;
  const ok = themes.dir.onFamilyTab(family, nowMs, themeClock);
  const p = themes.dir.state.pending;
  toast(`family ${family}${p ? ` -> ${themes.lib.byId.get(p.id)?.name || p.id}, on the next bar` : ""}`);
  return ok;
}
// ------------------------------------------------------------------------------- scenes from the transport and dial --
// vj-core.js SceneControl decides (a press, never a release; one dial step per message at most every 60 ms); the page
// works on the list of sets that load (a broken set is never a scene to land on).
function sceneList() { const out = []; for (let i = 0; i < sets.length; i++) if (validSet(i)) out.push(i); return out; }
function sceneCtl(ev, action, nowMs) {
  const list = sceneList();
  const liveSet = deck.running ? deck.b : deck.a;
  const live = Math.max(0, list.indexOf(liveSet));
  const r = scenes.ctl(ev, action, nowMs, list.length, live);
  if (!r) return;
  sceneAct(r, list, nowMs);
}
function sceneAct(r, list, nowMs) {
  if (r.do === "prev" || r.do === "next" || r.do === "go") {
    const to = list[r.index];
    if (to !== undefined && to !== (deck.running ? deck.b : deck.a)) nextSet(to, nowMs);
    queueSceneReport(false);
  } else if (r.do === "browse") {
    const s = sets[list[r.index]];
    if (s) toast(`▸ ${s.name}  (click the dial to go)`);
    queueSceneReport(true);
  } else if (r.do === "browse-end") {
    queueSceneReport(false);
  }
}
// The scene the page shows (or the one under the dial while browsing), reported to the engine for the KeyLab's screen:
// newest wins, one POST in flight, at most one every SCENE_POST_MIN_MS; an engine without the route (an older one: 404)
// or one that refuses is not asked again until its next hello (vj-core.js EngineLink.sceneResult); 429 waits a moment.
function queueSceneReport(browsing) {
  const list = sceneList();
  let idx = deck.running ? deck.b : deck.a;
  if (browsing && scenes.browsing()) idx = list[scenes.cursor] ?? idx;
  const s = sets[idx];
  if (!s) return;
  sceneReport.want = { name: s.name, index: list.indexOf(idx), count: list.length, browsing: !!(browsing && scenes.browsing()),
                       color: rgbToHex(palNow[0], palNow[1], palNow[2]), id: s.id };
}
function sceneTick(nowMs) {
  const r = scenes.tick(nowMs);
  if (r) sceneAct(r, sceneList(), nowMs);
  const w = sceneReport.want;
  if (!w || !engine.url || !engine.link.mayPostScene() || sceneReport.inflight) return;
  if (nowMs - sceneReport.lastAt < SCENE_POST_MIN_MS || nowMs < sceneReport.retryAt) return;
  const key = `${w.name}|${w.index}|${w.browsing}`;
  if (key === sceneReport.sentKey) { sceneReport.want = null; return; }
  const body = JSON.stringify({ name: w.name, index: w.index, count: w.count, browsing: w.browsing, color: w.color });
  sceneReport.inflight = true;
  sceneReport.lastAt = nowMs;
  sceneReport.posts++;
  sceneReport.log.push({ t: Math.round(nowMs), name: w.name, browsing: w.browsing });
  if (sceneReport.log.length > 100) sceneReport.log.shift();
  const gen = engine.link.gen;
  sceneReport.want = null;
  // a plain-text body keeps this a simple request (no CORS preflight); the engine reads the JSON either way
  fetch(`${engine.url}/api/scene`, { method: "POST", body })
    .then((res) => {
      const out = engine.link.sceneResult(res.status, gen);
      if (out === "ok") sceneReport.sentKey = key;
      else if (out === "busy") { sceneReport.retryAt = performance.now() + 400; if (!sceneReport.want) sceneReport.want = w; }
      else if (out === "error") sceneReport.retryAt = performance.now() + 2000;
    })
    .catch(() => { sceneReport.retryAt = performance.now() + 2000; if (!sceneReport.want) sceneReport.want = w; })
    .finally(() => { sceneReport.inflight = false; });
}
function targetLabel(id) {
  const act = SCENE_ACTIONS.find((a) => a.id === id) || LASER_ACTIONS.find((a) => a.id === id) || FAMILY_ACTIONS.find((a) => a.id === id);
  if (act) return act.label;
  if (/^k[1-8]$/.test(id)) {
    const s = sets[deck.a];
    const p = s && s.params.find((q) => q.k === +id[1]);
    return p ? `${id} ${p.name}` : id;
  }
  const t = TARGETS.find((x) => x.id === id);
  return t ? t.label : id;
}
function setTarget(target, ev) {
  if (target === "theme" || target === "hueDrift") {
    T[target] = applyCtl(T[target], ev);
    if (themes.dir) {
      if (target === "theme") { themes.faderTouched = true; themes.dir.onFader(T.theme, performance.now()); }
      else themes.dir.onFader2(T.hueDrift);
    }
    valuesDirty = true;
    return;
  }
  if (/^k[1-8]$/.test(target)) {
    const s = sets[deck.a];
    const k = +target[1] - 1;
    if (k === s.trailsK) T.trails = applyCtl(T.trails, ev);
    else s.knobs[k] = applyCtl(s.knobs[k], ev);
  } else {
    T[target] = applyCtl(T[target], ev);
    if (target === "xfade" && !deck.pickup && T.xfade <= 0.02) deck.pickup = true;
  }
  valuesDirty = true;
}
let valuesDirty = false, valuesSavedAt = 0;
function persistValues(nowMs) {
  if (!valuesDirty || nowMs - valuesSavedAt < 1000) return;
  valuesDirty = false;
  valuesSavedAt = nowMs;
  const out = {};
  for (const t of TARGETS) if (t.def !== null && t.id !== "xfade") out[t.id] = +T[t.id].toFixed(4);
  safeSet(STORE.values, JSON.stringify(out));
}
function savePadMap() { safeSet(STORE.pads, JSON.stringify(serializePadMap(padMap))); }
function loadStored() {
  try { padMap = normalizePadMap(JSON.parse(safeGet(STORE.pads) || "null")); } catch { padMap = DEFAULT_PAD_MAP.slice(); }
  try { ctlMap = normalizeCtlMap(JSON.parse(safeGet(STORE.ctl) || "null")); } catch { ctlMap = { ...DEFAULT_CTL_MAP }; }
  try {
    const v = JSON.parse(safeGet(STORE.values) || "null");
    if (v && typeof v === "object") for (const t of TARGETS) {
      if (t.def !== null && t.id !== "xfade" && typeof v[t.id] === "number" && Number.isFinite(v[t.id])) T[t.id] = clamp(v[t.id], 0, 1);
    }
  } catch { /* defaults */ }
  try {
    const o = JSON.parse(safeGet(STORE.opts) || "null");
    if (o && typeof o === "object") {
      options.hits = o.hits !== false; options.leds = o.leds !== false;
      options.snap = o.snap === true; options.punch = o.punch !== false;
      options.lasersClassic = o.lasersClassic === true; options.vibrate = o.vibrate === true; options.keyAuto = o.keyAuto !== false;
    }
  } catch { /* defaults */ }
}

// ------------------------------------------------------------------------------------------- the frame update --
function updateMusic(nowMs, nowS, dt) {
  beat.update(nowMs, dt);
  // energy and the band envelopes: a rise lands within a frame, the fall takes its band's time (vj-core.js
  // BandEnvelopes); silence after 1.5 s without an energy event
  bands.update(nowMs, dt);
  energy.bass = bands.level.bass; energy.mid = bands.level.mid; energy.high = bands.level.high; energy.level = bands.level.all;
  hit.pulse *= Math.exp(-dt / 0.18);
  hit.bloom *= Math.exp(-dt / 0.15);
  // the sets' pulse: the bass level, the kick's onset and the hits (a pad hit pumps the set too, through its strip pulse)
  const target = Math.max(0.55 * energy.bass + 0.45 * bands.env.kick, 0.35 * hit.pulse + 0.65 * bands.env.kick);
  pulseEnv += (target - pulseEnv) * (1 - Math.exp(-dt / (target > pulseEnv ? 0.006 : 0.18)));
  chordPulse *= Math.exp(-dt / 0.5);
  harm.update(dt);
  travel = Math.min(1, travel + dt / 0.9);
  drawOn = Math.min(1, drawOn + dt / (0.25 + 0.1 * Math.max(3, starCount)));
  pedal.update(nowS, dt);
  // keys: strike pulses, pitch-class levels and registers
  const kd = Math.exp(-dt / 0.25);
  for (let pc = 0; pc < 12; pc++) { pcStrike[pc] *= kd; pcHeld[pc] = 0; }
  const sumVel = pcLevelTarget, regSum = pcRegSum;
  sumVel.fill(0); regSum.fill(0);
  for (let k = 0; k < 128; k++) {
    kStrike[k] *= kd;
    if (kHeld[k] || kSus[k]) {
      const pc = k % 12;
      sumVel[pc] += kVel[k] * (kHeld[k] ? 1 : 0.7);
      regSum[pc] += clamp((k - 21) / 87, 0, 1);
      pcHeld[pc] += 1;
    }
  }
  for (let pc = 0; pc < 12; pc++) {
    const tgt = Math.min(1, sumVel[pc]);
    pcLevel[pc] += (tgt - pcLevel[pc]) * (1 - Math.exp(-dt / (tgt > pcLevel[pc] ? 0.03 : 0.25)));
    if (pcHeld[pc] > 0) pcReg[pc] = regSum[pc] / pcHeld[pc];
  }
  if (feel) {
    try {
      feelFrame = feel.update(feelState, dt, nowS);
      if (feelFrame.events.chordChanged && nowS - chord.t > 0.3 && nowS - lastDrawRestart > 0.25) {
        drawOn = 0; lastDrawRestart = nowS;
      }
    } catch (err) {
      recordError("runtime", "harmony-feel", err.message || err);
      feel = null;
    }
  }
}
const pcLevelTarget = new Float32Array(12), pcRegSum = new Float32Array(12);

function updatePalette() {
  const fader = faderStops;
  const look = themes.look;
  let fa = null, fb = null;
  if (look) {
    // a theme (vj-themes.js themeLook): its four stops -- A, B, their midpoint (or A lifted where a blend would grey), W
    fader.set(look.scene.palette);
  } else {
    // Custom (or no theme library): the fader palette of before -- hue A, hue B, the hue between them and hue A's
    // complement as the accent -- turned together round the wheel by fader 2 in Custom
    const turn = themes.dir && themes.dir.custom ? customTurnFromFader(T.hueDrift) / 360 : 0;
    const a = T.hueA + turn, b = T.hueB + turn;
    let d = b - a; d -= Math.round(d);
    fa = hueColour(a, 0.70); fb = hueColour(b, 0.62);
    const fm = hueColour(a + d * 0.5, 0.78), fc = hueColour(a + 0.5, 0.72);
    fader[0] = fa[0]; fader[1] = fa[1]; fader[2] = fa[2];
    fader[3] = fb[0]; fader[4] = fb[1]; fader[5] = fb[2];
    fader[6] = fm[0]; fader[7] = fm[1]; fader[8] = fm[2];
    fader[9] = fc[0]; fader[10] = fc[1]; fader[11] = fc[2];
  }
  const amt = T.chordAmt * chordPresence;
  if (look && chord.src === "audio" && amt > 0.001) {
    // the audio names the chords (hardstyle): a hue nudge of at most 15 degrees, so the theme's two colours stay two
    // (spec 2.2); the keys (the piano) colour freely, up to the Chord colour knob, as before
    for (let k = 0; k < 4; k++) {
      capScratchA[0] = fader[k * 3]; capScratchA[1] = fader[k * 3 + 1]; capScratchA[2] = fader[k * 3 + 2];
      capScratchB[0] = chordStops[k * 3]; capScratchB[1] = chordStops[k * 3 + 1]; capScratchB[2] = chordStops[k * 3 + 2];
      capHue(capScratchA, capScratchB, amt, 15, capScratchC);
      palTarget[k * 3] = capScratchC[0]; palTarget[k * 3 + 1] = capScratchC[1]; palTarget[k * 3 + 2] = capScratchC[2];
    }
  } else for (let k = 0; k < 4; k++) oklabMix(fader, k * 3, chordStops, k * 3, amt, palTarget, k * 3);
  const e = smooth(travel);
  for (let k = 0; k < 4; k++) oklabMix(palBefore, k * 3, palTarget, k * 3, e, palNow, k * 3);
  // pad colours: the palette stops on a diagonal, so neighbouring pads differ; the top row a little lighter. Under a
  // theme, its red-safe hit colours (vj-themes.js fx.padHits: a held red hits as the lasers' first colour), lifted in
  // float (never re-rounded to hex: the verifier's note)
  for (let i = 0; i < 12; i++) {
    const c = i % 4, r = (i / 4) | 0;
    const s = ((c + r) % 4) * 3;
    const lift = 1.12 - 0.08 * r;
    if (look) {
      const h = look.fx.padHits[i].lin;
      padCol[i * 3] = h[0] * lift; padCol[i * 3 + 1] = h[1] * lift; padCol[i * 3 + 2] = h[2] * lift;
    } else {
      padCol[i * 3] = palNow[s] * lift; padCol[i * 3 + 1] = palNow[s + 1] * lift; padCol[i * 3 + 2] = palNow[s + 2] * lift;
    }
  }
  // the lasers take the theme's laser roles (or Custom's two hues); a hit keeps the colours it was fitted to
  lasersTheme(fa, fb);
}
const capScratchA = [0, 0, 0], capScratchB = [0, 0, 0], capScratchC = [0, 0, 0];
function lasersTheme(fa, fb) {
  let key, theme;
  if (themes.look) {
    const t = themes.lib.byId.get(themes.look.id);
    theme = { ...t, lasers: themes.look.lasers.roles.slice() };
    key = `${t.id}|${theme.lasers.join("")}`;
  } else {
    if (!fa) { fa = hueColour(T.hueA, 0.70); fb = hueColour(T.hueB, 0.62); }
    theme = customLaserTheme(fa, fb);
    key = `custom|${theme.L1}|${theme.L2}`;
  }
  if (key === themes.laserKey) return;
  themes.laserKey = key;
  lasers.themeId = theme.id;
  lasers.eng.setTheme(theme);
}

// -------------------------------------------------------------------------------------- the colour themes --
// The theme director (vj-themes.js): Daniel's picks (fader 1, the family tabs) land on the next bar, key auto on the song's
// key, a big hue jump cuts through black on the beat. Its clock: the engine's bar when it sends one (--tap-one: the
// grid puts the ONE on a multiple of 4, vj-core.js BeatClock), the demo's counted bars, else beats only (a pick then
// lands on the next beat).
const themeClockBars = themeClockOf(beat, { bars: true });
function gridNext(nowMs, every) {
  const pos = beat.posAt(nowMs);
  if (pos === null || !beat.alive(nowMs)) return null;
  const k = Math.ceil(pos / every - 1e-9) * every;
  return nowMs + (k - pos) * beat.period();
}
function barsCounted() { return !!demo || !!(engine.link.hello && engine.link.hello.beat_engine === "demo"); }
const themeClock = {
  beatsPerBar: 4, barsPerPhrase: 8,
  observe: (now) => themeClockBars.observe(now),
  alive: (now) => beat.alive(now),
  beatMs: () => beat.period(),
  nextBeatAt: (now) => beat.nextBeatAt(now),
  nextBarAt: (now) => (beat.bar > 0 ? gridNext(now, 4) : barsCounted() ? themeClockBars.nextBarAt(now) : null),
  nextPhraseAt: (now) => (beat.bar > 0 ? gridNext(now, 32) : barsCounted() ? themeClockBars.nextPhraseAt(now) : null),
};
async function loadThemes() {
  try {
    const lib = await fetchLibrary();
    themes.lib = lib;
    let initial = THEME_AT_START && lib.byId.has(THEME_AT_START) ? THEME_AT_START : null, custom = false;
    if (!initial) {
      try {
        const st = JSON.parse(safeGet(STORE.theme) || "null");
        if (st && typeof st.id === "string" && lib.byId.has(st.id)) { initial = st.id; custom = st.custom === true; }
      } catch { /* the director's own default */ }
    }
    const dir = new ThemeDirector(lib, initial ? { initial, keyAuto: options.keyAuto } : { keyAuto: options.keyAuto });
    if (custom) { dir.current = "custom"; dir.custom = true; }
    dir.onFader2(T.hueDrift);
    themes.dir = dir;
    themeTick(performance.now());
    updatePalette();
    palBefore.set(palNow);
  } catch (err) {
    themes.error = String((err && err.message) || err);
    recordError("load", "vj-themes", themes.error);
  }
}
function themeTick(nowMs) {
  const d = themes.dir;
  if (!d) return;
  d.keyAuto = options.keyAuto;
  const ch = d.tick(nowMs, themeClock);
  if (ch) {
    themes.changes++;
    themes.lastChange = { id: ch.id, from: ch.from, on: ch.on, reason: ch.reason, cut: !!ch.cut, at: Math.round(nowMs),
                          atMs: ch.atMs === null ? null : Math.round(ch.atMs) };
    palBefore.set(palNow);
    travel = 0;
    if (ch.cut) { themes.cuts++; themes.dipAt = nowMs; }
    safeSet(STORE.theme, JSON.stringify({ id: d.base, custom: d.custom }));
  }
  const key = `${d.base}|${d.custom}|${d.keyAuto ? d.mode || "" : ""}|${d.fader2 === null ? "" : d.fader2.toFixed(3)}`;
  if (key !== themes.lookKey) { themes.lookKey = key; themes.look = d.custom ? null : d.look(); }
}
// a theme change flagged to cut through black (a hue jump over 100 degrees, or a theme that asks for it): the frame dips
// to 15 % over 80 ms at the change and comes back over 160 ms -- one dark breath, at most one a bar
function themeDip(nowMs) {
  const t = nowMs - themes.dipAt;
  if (!(t >= 0) || t > 240) return 1;
  return t < 80 ? 1 - 0.85 * (t / 80) : 0.15 + 0.85 * ((t - 80) / 160);
}
const faderStops = new Float32Array(12);

function updateKill(nowMs, dt) {
  if (kill.at !== null && nowMs >= kill.at) {
    kill.target = kill.pending;
    kill.pending = null;
    kill.at = null;
  }
  const rate = kill.target < kill.gain ? dt / KILL_OUT_S : dt / KILL_IN_S;
  kill.gain = kill.target < kill.gain ? Math.max(kill.target, kill.gain - rate) : Math.min(kill.target, kill.gain + rate);
}

// This frame's impact values from the impact layer (vj-core.js ImpactLayer), the zoom punch (an effect: its envelope is
// the spring back) and the band envelopes. The accent fader scales them all (1 at its default, 0.85).
function updateImpact(nowS) {
  const o = impact.sample(nowS);
  const gain = clamp(T.accent / 0.85, 0, 1.2);
  const z = fx.strongest("zoom");
  frame.zoom = z ? zoomDepth(z.vel) * z.env * gain : 0;
  frame.blur = Math.min(0.12, 0.35 * frame.zoom);
  frame.pump = options.hits ? bands.env.kick * 0.012 * (0.25 + 1.5 * T.bassReact) : 0;
  frame.punch = Math.min(0.45, (o.punch + frame.zoom) * gain + frame.pump);
  frame.shakeX = o.shakeX * gain; frame.shakeY = o.shakeY * gain;
  frame.dip = Math.min(0.9, o.dip * gain);
  frame.dipGranted = o.dipGranted ? 1 : 0;
  frame.glow = o.glow;
  frame.snare = options.hits ? bands.env.snare * T.accent : 0;
  frame.sparkle = options.hits ? bands.env.hat * 0.5 * T.accent : 0;
}

let starCount = 0;
function buildStrip(nowMs, nowS) {
  const S = strip;
  // row 0: pads (effect pads only: control pads do not play the set), beat, colour, mood, chord
  const padEnv = padEnvScratch, padVel = padVelScratch;
  padEnv.fill(0); padVel.fill(0);
  for (const f of fx.fx) {
    if (!f.active || f.pad < 1) continue;
    if (f.env > padEnv[f.pad - 1]) { padEnv[f.pad - 1] = f.env; padVel[f.pad - 1] = f.vel; }
  }
  for (let i = 0; i < 12; i++) stripSet(S, i, 0, padEnv[i] * T.accent, padVel[i], Math.min(30, nowS - padT0[i]), padHeld[i]);
  const ph = beat.phase(nowMs);
  stripSet(S, 12, 0, ph, beat.pulse, ((beat.count % 4) + ph) / 4, beat.count % 64);
  stripSet(S, 13, 0, T.hueA, T.hueB, T.sat, T.bright);
  const c = feelFrame ? feelFrame.colour : null;
  // tension: the engine's (chordsense) while it sends one, else the page's own; then the page's pedal star (EngineHarmony)
  stripSet(S, 14, 0, T.trails, T.bassReact, harm.stripTension(c ? c.tension : 0, pedal.tension()), c ? c.lushness : 0);
  stripSet(S, 15, 0, chordPulse, chord.root, Math.min(60, nowS - chord.t), c ? c.brightness : 0.5);
  // row 1: pitch classes, hit, energy, pedal
  for (let pc = 0; pc < 12; pc++) stripSet(S, pc, 1, pcLevel[pc], pcStrike[pc], pcReg[pc], pcHeld[pc]);
  stripSet(S, 12, 1, hit.pulse, bands.env.kick, bands.env.snare, bands.env.hat);
  stripSet(S, 13, 1, energy.bass, energy.mid, energy.high, energy.level);
  const pk = pedal.key;
  if (pk >= 0) starPosition(pk, starPos);
  else if (pedal.resolvedKey >= 0) starPosition(pedal.resolvedKey, starPos);
  stripSet(S, 14, 1, starPos[0], starPos[1], pk >= 0 ? pedal.pulse : 0, pedal.tension());
  stripSet(S, 15, 1, pk >= 0 ? pk % 12 : (pedal.resolvedKey >= 0 ? pedal.resolvedKey % 12 : -1), pk >= 0 ? 1 : 0,
           pedal.resolvePulse, drawOn);
  // row 2: palette now and before, travel, mix gains, star count, version
  for (let k = 0; k < 4; k++) {
    stripSet(S, k, 2, palNow[k * 3], palNow[k * 3 + 1], palNow[k * 3 + 2], 1);
    stripSet(S, 4 + k, 2, palBefore[k * 3], palBefore[k * 3 + 1], palBefore[k * 3 + 2], 1);
  }
  stripSet(S, 8, 2, travel, T.accent, T.metro, kill.gain);
  // row 3: pad colours
  for (let i = 0; i < 12; i++) stripSet(S, i, 3, padCol[i * 3], padCol[i * 3 + 1], padCol[i * 3 + 2], 1);
  // rows 4-5: stars -- every sounding key (and the pedal key between its strikes), sorted round the circle of fifths
  let n = 0;
  for (let k = 0; k < 128; k++) if (kHeld[k] || kSus[k] || k === pk) starKeys[n++] = k;
  if (n === 0 && chord.src === "audio" && nowS - chord.t < 8) {
    for (const pc of chord.pcs) if (n < 16) starKeys[n++] = 60 + pc;
  }
  // keep the 16 most recent when more sound (a pedal wash)
  while (n > 16) {
    let oldest = 0;
    for (let j = 1; j < n; j++) if (kT0[starKeys[j]] < kT0[starKeys[oldest]] && starKeys[j] !== pk) oldest = j;
    starKeys[oldest] = starKeys[--n];
  }
  for (let j = 1; j < n; j++) {     // insertion sort by (fifths index, key)
    const v = starKeys[j];
    const kv = fifthsIndex(v % 12) * 128 + v;
    let m = j - 1;
    while (m >= 0 && fifthsIndex(starKeys[m] % 12) * 128 + starKeys[m] > kv) { starKeys[m + 1] = starKeys[m]; m--; }
    starKeys[m + 1] = v;
  }
  starCount = n;
  for (let s = 0; s < 16; s++) {
    if (s < n) {
      const k = starKeys[s];
      starPosition(k, starPos);
      const sounding = kHeld[k] || kSus[k];
      let bright = sounding ? kVel[k] * (0.55 + 0.45 * kStrike[k]) * (kHeld[k] ? 1 : 0.65) : 0.55 + 0.45 * chordPulse;
      if (k === pk) bright = Math.max(bright, 0.45 + 0.55 * pedal.pulse);
      stripSet(S, s, 4, starPos[0], starPos[1], clamp(bright, 0, 1.3), k % 12);
      stripSet(S, s, 5, kVel[k], Math.min(30, nowS - kT0[k]), (k % 12) === chord.root ? 1 : 0, k === pk ? 1 : 0);
    } else {
      stripSet(S, s, 4, 0, 0, 0, -1);
      stripSet(S, s, 5, 0, 0, 0, 0);
    }
  }
  // v3: the head bus for a scene tagged laser-heads (vj-hookup.js; texel 9's .x stays the star count), idle otherwise
  writeHeadBus(S, lasers.busOn ? lasers.bus : null, n);
  // v2: the shared hit input (vj-core.js STRIP row 2, texels 10-12) -- each set reacts to a pad hit in its own way
  const im = impact.out;
  stripSet(S, 10, 2, limiterLive() ? im.pulse * T.accent : 0, im.vel, im.code, im.since);   // the safe mode: no set reactions
  stripSet(S, 11, 2, bands.env.kick, bands.env.snare, bands.env.hat, frame.punch);
  stripSet(S, 12, 2, im.seed, im.x, im.y, 0);
  stripSet(S, 15, 2, STRIP.VERSION, 0, 0, 1);
}
const padEnvScratch = new Float32Array(12), padVelScratch = new Float32Array(12);

// u_audio for presets that read Play's audio texture (the MilkDrop tunnel): no microphone here, so a spectrum is
// synthesised from the engine's bands plus a line for every sounding key, and a waveform from those keys.
function buildAudio(nowS) {
  const lo = Math.log(20), span = Math.log(16000) - lo;
  for (let x = 0; x < AUDIO_TEX_W; x++) {
    const hz = Math.exp(lo + (span * (x + 0.5)) / AUDIO_TEX_W);
    const b = hz < 150 ? energy.bass : hz < 2000 ? energy.mid : energy.high;
    const tilt = 0.75 - 0.25 * (x / AUDIO_TEX_W);
    audioBytes[x] = clamp(Math.round(255 * clamp(b * tilt * 0.9, 0, 1)), 0, 255);
    audioBytes[AUDIO_TEX_W + x] = 128;
  }
  for (let k = 21; k < 109; k++) {
    if (!(kHeld[k] || kSus[k])) continue;
    const hz = 440 * Math.pow(2, (k - 69) / 12);
    const col = Math.round(((Math.log(hz) - lo) / span) * AUDIO_TEX_W);
    const v = kVel[k] * (0.6 + 0.4 * kStrike[k]);
    for (let dx = -2; dx <= 2; dx++) {
      const x = col + dx;
      if (x < 0 || x >= AUDIO_TEX_W) continue;
      audioBytes[x] = Math.min(255, audioBytes[x] + Math.round(200 * v * Math.exp(-dx * dx * 0.6)));
    }
    for (let x = 0; x < AUDIO_TEX_W; x++) {   // 512 samples at 48 kHz, its phase drifting so the trace moves
      const w = Math.sin(2 * Math.PI * (hz * (x / 48000) + nowS * 0.5 * (k % 5 + 1)));
      audioBytes[AUDIO_TEX_W + x] = clamp(audioBytes[AUDIO_TEX_W + x] + Math.round(w * 40 * v), 0, 255);
    }
  }
}

// ------------------------------------------------------------------------------------------------- rendering --
function renderSet(set, nowS) {
  const gl = G.gl;
  ensureFb(set);
  const fb = set.fb;
  const write = 1 - fb.read;
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb.fbos[write]);
  gl.viewport(0, 0, fb.w, fb.h);
  gl.useProgram(set.program);
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, G.stripTex);
  gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, fb.texs[fb.read]);
  gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, G.audioTex);
  const u = set.uniforms;
  const react = 0.25 + 1.5 * T.bassReact;
  gl.uniform2f(u.u_res, fb.w, fb.h);
  gl.uniform2f(u.u_video_res, 1, 1);
  gl.uniform1f(u.u_time, nowS);
  gl.uniform1f(u.u_media_time, 0);
  gl.uniform1f(u.u_frame, set.frame);
  gl.uniform1f(u.u_has_video, 0);
  // a VJ-aware set hears pad hits through its strip (row 2, texel 10) and reacts in its own way; any other Play preset
  // gets them through its pulse, so every set answers a hit
  const padPulse = set.vj || !limiterLive() ? 0 : 0.9 * impact.out.pulse * T.accent;
  gl.uniform1f(u.u_pulse, clamp(Math.max(pulseEnv * react, padPulse), 0, 1.5));
  gl.uniform1f(u.u_beat, Math.max(beat.pulse, 0.8 * hit.pulse, 0.9 * bands.env.kick, padPulse));
  gl.uniform1f(u.u_level, energy.level);
  gl.uniform1f(u.u_bass, clamp(energy.bass * react, 0, 1.5));
  gl.uniform1f(u.u_mid, energy.mid);
  gl.uniform1f(u.u_high, energy.high);
  gl.uniform1f(u.u_flux, hit.pulse);
  // a VJ-aware set takes its colour from the strip's palette; any other Play preset gets hue A as Play's hue turn
  gl.uniform1f(u.u_hue, set.vj ? 0 : ((T.hueA - 0.53) * 360));
  gl.uniform1f(u.u_intensity, set.vj ? 1.0 : 0.8);
  if (set.trailsK >= 0) set.knobs[set.trailsK] = T.trails;
  for (let k = 0; k < 8; k++) gl.uniform1f(u[K_UNIFORMS[k]], set.knobs[k]);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  fb.read = write;
  set.frame++;
}

// write four floats / three floats into a uniform scratch array (no array literal, so nothing is allocated)
function put4(a, o, x, y, z, w) { a[o] = x; a[o + 1] = y; a[o + 2] = z; a[o + 3] = w; }
function putCol(a, o, pad) {      // the colour of pad 1..12, or the palette's third stop
  const s = pad >= 1 ? (pad - 1) * 3 : -1;
  a[o] = s >= 0 ? padCol[s] : palNow[6]; a[o + 1] = s >= 0 ? padCol[s + 1] : palNow[7]; a[o + 2] = s >= 0 ? padCol[s + 2] : palNow[8];
}
function fillOverlayUniforms(nowS) {
  const asp = G.width / Math.max(G.height, 1);
  U.wave.fill(0); U.laser.fill(0); U.part.fill(0); U.note.fill(0);
  let w = 0, l = 0, pa = 0;
  for (let i = 0; i < fx.fx.length; i++) {
    const f = fx.fx[i];
    if (!f.active) continue;
    const age = nowS - f.t0;
    if (f.type === "shockwave" && w < 4) {
      const ox = (f.seed - 0.5) * 0.3 * asp, oy = (((f.seed * 7.31) % 1) - 0.5) * 0.25;
      const speed = 0.45 + 0.7 * f.vel;
      put4(U.wave, w * 4, ox, oy, 0.02 + speed * (1 - Math.exp(-age * 2.6)), f.env * (0.45 + 0.55 * f.vel));
      put4(U.waveB, w * 4, 4 + 16 * f.vel, f.vel, age, velCurve(f.vel));
      putCol(U.waveCol, w * 3, f.pad);
      w++;
    } else if (f.type === "laser" && l < 4) {
      const slot = f.serial % 4;
      const ox = slot === 1 ? -0.48 * asp : slot === 2 ? 0.48 * asp : 0;
      const oy = slot === 3 ? 0.52 : -0.52;
      const aim = Math.atan2(-oy, -ox) + Math.sin(age * 2.4 + f.seed * 6.28) * (0.25 + 0.35 * f.vel);
      put4(U.laser, l * 4, ox, oy, aim, f.env * (0.6 + 0.5 * f.vel));
      put4(U.laserB, l * 4, 3 + Math.round(9 * f.vel), 0.4 + 1.3 * f.vel, 1.2 + 2.4 * f.vel, f.vel);
      putCol(U.laserCol, l * 3, f.pad);
      l++;
    } else if (f.type === "particles" && pa < 4) {
      const ox = (f.seed - 0.5) * 0.5 * asp, oy = (((f.seed * 3.7) % 1) - 0.5) * 0.3;
      const emitEnd = f.tr === null ? 1e4 : Math.max(0, f.tr - f.t0);
      put4(U.part, pa * 4, ox, oy, age, f.env);
      put4(U.partB, pa * 4, 12 + Math.round(36 * f.vel), 0.25 + 0.55 * f.vel, f.seed * 10 + 1, emitEnd);
      putCol(U.partCol, pa * 3, f.pad);
      pa++;
    }
  }
  for (let i = 0; i < glints.length; i++) {
    const gl8 = glints[i];
    const age = nowS - gl8.t0;
    if (age > 2.2) continue;
    put4(U.note, i * 4, gl8.x, 0, age, gl8.vel);
    U.noteCol[i * 3] = PC_RGB[gl8.pc * 3]; U.noteCol[i * 3 + 1] = PC_RGB[gl8.pc * 3 + 1]; U.noteCol[i * 3 + 2] = PC_RGB[gl8.pc * 3 + 2];
  }
}

function renderOverlay(nowS) {
  const gl = G.gl;
  const ov = G.ov;
  const write = 1 - ov.read;
  gl.bindFramebuffer(gl.FRAMEBUFFER, ov.fbos[write]);
  gl.viewport(0, 0, ov.w, ov.h);
  gl.useProgram(G.ovProg);
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, ov.texs[ov.read]);
  const u = G.ovU;
  gl.uniform2f(u.u_res, ov.w, ov.h);
  // the overlay's trails fade by time, not by frame: the same streak at 30 and at 144 frames a second; a hit's afterglow
  // (the impact layer) lengthens them for ~0.35 s, so a hard hit's light lingers through the trails
  gl.uniform1f(u.u_keep, Math.exp(-frameDt / (0.03 + 0.17 * T.trails + 0.22 * frame.glow)));
  gl.uniform1f(u.u_sparkle, frame.sparkle);
  gl.uniform1f(u.u_sparkleT, Math.floor(nowS * 30) % 997);
  gl.uniform3f(u.u_sparkleCol, 0.6 + 0.4 * palNow[9], 0.6 + 0.4 * palNow[10], 0.6 + 0.4 * palNow[11]);
  gl.uniform4fv(u.u_wave, U.wave); gl.uniform4fv(u.u_waveB, U.waveB); gl.uniform3fv(u.u_waveCol, U.waveCol);
  gl.uniform4fv(u.u_laser, U.laser); gl.uniform4fv(u.u_laserB, U.laserB); gl.uniform3fv(u.u_laserCol, U.laserCol);
  gl.uniform4fv(u.u_part, U.part); gl.uniform4fv(u.u_partB, U.partB); gl.uniform3fv(u.u_partCol, U.partCol);
  gl.uniform4fv(u.u_note, U.note); gl.uniform3fv(u.u_noteCol, U.noteCol);
  const st = fx.strongest("strobe");
  const rate = 2 + 10 * T.strobeRate;
  gl.uniform1f(u.u_bars, st ? st.env * (0.35 + 0.65 * st.vel) : 0);
  gl.uniform1f(u.u_barsPhase, st ? ((nowS - st.t0) * rate) % 1 : 0);
  gl.uniform3f(u.u_barsCol, 0.9, 0.92, 1.0);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  ov.read = write;
}

// The scene meter: the mean relative luminance of what the composite will show of the sets and the overlay, into a 1x1
// texture the composite reads in the same frame (the dip's safety limit). Tiny passes: 64 x 36 cells, 8 x 6, one texel.
function meterPass(texA, texB, mixEased) {
  const gl = G.gl;
  gl.useProgram(G.meterProg);
  gl.bindFramebuffer(gl.FRAMEBUFFER, G.meter1.fbos[0]);
  gl.viewport(0, 0, 64, 36);
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, texA);
  gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, texB);
  gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, G.ov.texs[G.ov.read]);
  gl.uniform1f(G.meterU.u_mix, mixEased);
  gl.uniform1f(G.meterU.u_accent, 0.25 + 1.0 * T.accent);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  gl.useProgram(G.meter2Prog);
  gl.uniform2i(G.meter2U.u_block, 8, 6);
  gl.bindFramebuffer(gl.FRAMEBUFFER, G.meterMid.fbos[0]);
  gl.viewport(0, 0, 8, 6);
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, G.meter1.texs[0]);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  gl.bindFramebuffer(gl.FRAMEBUFFER, G.meter2.fbos[0]);
  gl.viewport(0, 0, 1, 1);
  gl.bindTexture(gl.TEXTURE_2D, G.meterMid.texs[0]);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}
// The composite, into the page's composite pair (G.cmp): returns the texture it drew. The look (vj-stage.js) or the copy
// pass takes it to the screen; next frame it is u_hist, the frame the glitch's datamosh drags along.
function composite(nowMs, nowS, mixAB, mixedTex = null) {
  const gl = G.gl;
  const A = sets[deck.a], B = sets[deck.b];
  const texA = mixedTex || (A && A.fb ? A.fb.texs[A.fb.read] : G.blackTex);
  const texB = B && B.fb && mixAB > 0.001 && !mixedTex ? B.fb.texs[B.fb.read] : G.blackTex;
  const mixUsed = A && A.fb && !mixedTex ? mixAB : 0;
  const m = clamp(mixUsed, 0, 1);
  meterPass(texA, texB, mixUsed > 0.001 ? m * m * (3 - 2 * m) : 0);
  if (stutterCapture) { captureStutter(); stutterCapture = false; }
  const cmp = G.cmp;
  const write = 1 - cmp.read;
  gl.bindFramebuffer(gl.FRAMEBUFFER, cmp.fbos[write]);
  gl.viewport(0, 0, G.width, G.height);
  gl.useProgram(G.compProg);
  // a transition in flight (vj-stage.js) arrives already mixed as u_a, with u_mix 0
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, texA);
  gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, texB);
  gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, G.ov.texs[G.ov.read]);
  gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, G.frz ? G.frz.texs[0] : G.blackTex);
  gl.activeTexture(gl.TEXTURE4); gl.bindTexture(gl.TEXTURE_2D, cmp.texs[cmp.read]);
  gl.activeTexture(gl.TEXTURE5); gl.bindTexture(gl.TEXTURE_2D, G.stut.texs[0]);
  gl.activeTexture(gl.TEXTURE6); gl.bindTexture(gl.TEXTURE_2D, G.meter2.texs[0]);
  const u = G.compU;
  gl.uniform2f(u.u_res, G.width, G.height);
  gl.uniform1f(u.u_mix, mixUsed);
  const k = fx.strongest("kaleido");
  gl.uniform1f(u.u_kal, k ? k.env : 0);
  gl.uniform1f(u.u_kalN, k ? 2 * Math.round(2 + 4 * k.vel) : 6);
  gl.uniform1f(u.u_kalRot, k ? (nowS - k.t0) * (0.15 + 0.5 * k.vel) : 0);
  // the glitch: this hit's plan (vj-core.js glitchPlan: its mode or pair of modes, intensity, size), from its seed
  const g = fx.strongest("glitch");
  if (g && g.serial !== glitchState.serial) { glitchState.serial = g.serial; glitchState.plan = glitchPlan(g.seed, g.vel); glitchState.t0 = g.t0; }
  const gp = g ? glitchState.plan : null;
  gl.uniform1f(u.u_glitch, g ? g.env * gp.amount : 0);
  gl.uniform1f(u.u_glitchT, Math.floor(nowS * 14) % 997);
  gl.uniform2f(u.u_gMode, gp ? gp.primary : -1, gp ? gp.secondary : -1);
  gl.uniform1f(u.u_gSize, gp ? gp.size : 0.5);
  gl.uniform1f(u.u_gSeed, gp ? gp.seed : 0);
  gl.uniform1f(u.u_gAge, g ? Math.max(0, nowS - g.t0) : 0);
  const fz = fx.strongest("freeze");
  gl.uniform1f(u.u_freeze, fz ? fz.env * (0.55 + 0.45 * fz.vel) : 0);
  gl.uniform1f(u.u_freezeZoom, fz ? Math.min(0.2, (nowS - fz.t0) * 0.03 * fz.vel) : 0);
  gl.uniform4fv(u.u_wave, U.wave);
  gl.uniform4fv(u.u_waveB, U.waveB);
  // the full-frame flash: granted by the gate in JS; envFlashSafe in the shader checks the gap again
  const fAge = nowS - flash.t0;
  gl.uniform1f(u.u_flash, fAge >= 0 ? flash.peak * Math.exp(-fAge / Math.max(flash.decay, 0.02)) : 0);
  gl.uniform1f(u.u_flashGap, flash.gap);
  const inv = fx.strongest("invert");
  let invert = 0;
  if (inv) {
    invert = inv.env * (0.6 + 0.4 * inv.vel);
    if (!inv.granted) invert *= smooth((nowS - inv.t0) / 1.2);   // refused by the gate: a slow fade is not a flash
  }
  gl.uniform1f(u.u_invert, invert);
  gl.uniform1f(u.u_bright, T.bright * kill.gain * themeDip(nowMs));
  gl.uniform1f(u.u_sat, 0.15 + 1.0 * T.sat);
  gl.uniform1f(u.u_accent, 0.25 + 1.0 * T.accent);
  gl.uniform1f(u.u_metro, Math.min(0.03, T.metro * 0.03 * beat.pulse));   // linear light: a few percent at most
  gl.uniform3f(u.u_metroCol, palNow[0], palNow[1], palNow[2]);
  gl.uniform1f(u.u_bloom, Math.min(0.06, hit.bloom * 0.07 * T.accent));
  gl.uniform3f(u.u_bloomCol, palNow[9], palNow[10], palNow[11]);
  // the impact pass: punch, shake, the zoom punch's blur, the dip (its safety limit is applied in the shader, from the
  // meter), the snare's kick
  gl.uniform1f(u.u_punch, frame.punch);
  gl.uniform1f(u.u_blur, frame.blur);
  gl.uniform2f(u.u_shake, frame.shakeX, frame.shakeY);
  gl.uniform1f(u.u_dip, frame.dip);
  gl.uniform1f(u.u_dipGranted, frame.dipGranted);
  gl.uniform1f(u.u_dipSafe, DIP_SAFE_DELTA);
  gl.uniform1f(u.u_snare, frame.snare);
  // the beam layer (Lasers v2): never brighter than the engine fitted it (the accent fader only takes light away here)
  gl.activeTexture(gl.TEXTURE7); gl.bindTexture(gl.TEXTURE_2D, G.beam ? G.beam.texs[0] : G.blackTex);
  gl.uniform1f(u.u_beamGain, options.lasersClassic || G.beamClear ? 0 : Math.min(1, (0.25 + T.accent) / 1.1) * (lasers.cut ? 0 : Math.min(1, lasers.gain)));
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  cmp.read = write;
  return cmp.texs[write];
}
// The composite to the screen when the look is off.
function copyToScreen(tex) {
  const gl = G.gl;
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  gl.viewport(0, 0, G.width, G.height);
  gl.useProgram(G.copyProg);
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}
// The stutter's held frame: the last composited frame, as it was when the glitch hit.
function captureStutter() {
  const gl = G.gl;
  if (!G.cmp || !G.stut) return;
  gl.bindFramebuffer(gl.READ_FRAMEBUFFER, G.cmp.fbos[G.cmp.read]);
  gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, G.stut.fbos[0]);
  gl.blitFramebuffer(0, 0, G.cmp.w, G.cmp.h, 0, 0, G.stut.w, G.stut.h, gl.COLOR_BUFFER_BIT, gl.NEAREST);
  gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null);
  gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, null);
}

function captureFreeze() {
  const gl = G.gl;
  const A = sets[deck.a];
  if (!A || !A.fb || !G.frz) return;
  gl.bindFramebuffer(gl.READ_FRAMEBUFFER, A.fb.fbos[A.fb.read]);
  gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, G.frz.fbos[0]);
  gl.blitFramebuffer(0, 0, A.fb.w, A.fb.h, 0, 0, G.frz.w, G.frz.h, gl.COLOR_BUFFER_BIT, gl.NEAREST);
  gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null);
  gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, null);
}

function runProbe(nowMs) {
  const gl = G.gl;
  const n = G.width * G.height * 4;
  if (!probe.buf || probe.buf.length !== n) probe.buf = new Uint8Array(n);
  gl.readPixels(0, 0, G.width, G.height, gl.RGBA, gl.UNSIGNED_BYTE, probe.buf);
  // the mean RELATIVE luminance (WCAG: linear light), every 7th pixel
  let sum = 0, count = 0;
  const step = 4 * 7;
  const lut = SRGB_TO_LINEAR;
  for (let i = 0; i < n; i += step) {
    sum += 0.2126 * lut[probe.buf[i]] + 0.7152 * lut[probe.buf[i + 1]] + 0.0722 * lut[probe.buf[i + 2]];
    count++;
  }
  const luma = sum / Math.max(count, 1);
  if (probe.on) {
    probe.trace.push({ t: Math.round(nowMs), luma: +luma.toFixed(4) });
    if (probe.trace.length > 4000) probe.trace.shift();
  }
  const waiters = probe.waiters;
  probe.waiters = [];
  for (const w of waiters) w(luma);
}

// ------------------------------------------------------------------------------------------- the pad lights --
function padLights(nowMs, dt) {
  const pd = Math.exp(-dt / 0.25);
  for (let i = 0; i < 12; i++) padPress[i] *= pd;
  if (nowMs - led.computedAt < LED_INTERVAL_MS) return;   // colours as text ten times a second, not every frame
  led.computedAt = nowMs;
  const out = ledColours;
  // the pads get LED STAND-INS, never screen colours (spec 2.2): the pads wash orange to lime and pale colours to white,
  // so a theme names a stand-in for each of its colours (vj-themes.js padLeds); Custom's are made from its hues
  // (vj-hookup.js standInLed). The laser pad lights in the lasers' own stand-in, its brightness the tier (60 / 80 / 100 %).
  const tier = lasers.out && lasers.out.pad.level > 0 ? lasers.out.pad.tier | 0 : 0;
  const lights = themes.look ? padLeds(themes.look, padMap, { tier }) : null;
  for (let i = 0; i < 12; i++) {
    const action = padMap[i];
    let v = 0, light = null;
    if (isTapPad(tapPads, i + 1, "daw")) {
      // the engine's tap pad: white, a blink on every beat, brighter on the ONE
      const one = beat.barAt(nowMs) === 1;
      light = TAP_LIGHT;
      v = Math.max(0.12 + (one ? 0.88 : 0.5) * beat.pulse, padPress[i]);
    } else if (action === "laser" && !options.lasersClassic) {
      light = lights ? lights[i] : standInLed(lasers.eng.col.L1);
      if (!lights) light = { ...light, level: light.level * (tier ? TIER_LED[tier] : 1) };
      v = 0.12 + 0.88 * Math.max(lasers.out && lasers.out.pad.level > 0 ? 1 : 0, lasers.held ? 0.6 : 0);
    } else if (EFFECTS[action]) {
      light = lights ? lights[i] : standInLed([padCol[i * 3], padCol[i * 3 + 1], padCol[i * 3 + 2]]);
      v = 0.10 + 0.9 * Math.max(padEnvScratch[i] / Math.max(T.accent, 0.05), padHeld[i] ? 0.6 : 0);
    } else if (CONTROLS[action]) {
      light = action === "none" ? null : { hex: action === "choke" ? CHOKE_LED : CONTROLS[action].colour, level: 1 };
      v = 0.10 + 0.9 * padPress[i];
      if (action === "kill") v = kill.target < 0.5 ? 1 : kill.pending !== null ? (beat.pulse > 0.5 ? 1 : 0.4) : 0.12;
      if (action === "next" && deck.running) v = 0.9;
    }
    out[i] = light ? ledHexAt(light, Math.min(v, 1)) : "#000000";
    if (!ledPostedOk(out[i])) { led.washed++; out[i] = ledHexAt({ hex: "#ffffff", level: 1 }, Math.min(v, 1)); }
  }
  // an engine whose hello says it has no LEDs, or that refused a post, is not asked again until its next hello
  if (!options.leds || !engine.url || !engine.link.mayPostLeds()) return;
  if (led.inflight || nowMs < led.backoffUntil || nowMs - led.lastAt < LED_INTERVAL_MS) return;
  const body = JSON.stringify({ colors: out });
  if (body === led.last) return;
  led.inflight = true;
  led.lastAt = nowMs;
  led.last = body;
  led.posts++;
  led.log.push(Math.round(nowMs));
  if (led.log.length > 200) led.log.shift();
  const gen = engine.link.gen;
  // a plain-text body keeps this a simple request (no CORS preflight); the engine reads the JSON either way
  fetch(`${engine.url}/api/pads`, { method: "POST", body })
    .then((res) => {
      if (engine.link.postResult(res.status, gen)) led.last = "";   // resend the frame once the engine allows it
      else if (!res.ok) led.backoffUntil = performance.now() + 2000;
    })
    .catch(() => { led.backoffUntil = performance.now() + 2000; led.last = ""; })
    .finally(() => { led.inflight = false; });
}
const ledColours = new Array(12).fill("#000000");
const TAP_LIGHT = Object.freeze({ hex: "#ffffff", level: 1 });

// ------------------------------------------------------------------------------------------------ the engine --
// The engine may start after the page (or restart): reconnect with a backoff from 1 s to 10 s, so an absent engine
// costs one failed request every few seconds instead of EventSource's own fixed retry.
let engineBackoff = 1000;
function connectEngine() {
  if (!engine.url) return;
  try {
    engine.es = new EventSource(`${engine.url}/api/events`);
  } catch (err) {
    recordError("engine", null, err.message || err);
    return;
  }
  const es = engine.es;
  es.onopen = () => { engine.link.connected(); engineBackoff = 1000; };
  es.onerror = () => {
    es.close();
    if (engine.es !== es) return;
    engine.link.disconnected();          // the old engine's hello and status are no longer the truth
    tapPads = [];                        // ... nor its tap pads
    harm.reset();                        // ... nor its key and tension: the page's own estimate takes over again
    engine.es = null;
    setTimeout(connectEngine, engineBackoff);
    engineBackoff = Math.min(10000, engineBackoff * 1.6);
  };
  es.onmessage = (m) => {
    engine.lastMsg = performance.now();
    engine.link.connected();
    let obj;
    try { obj = JSON.parse(m.data); } catch { engine.bad++; return; }
    handleEvent(obj);
  };
}

const demoEvent = (ev) => handleEvent(ev, "demo");
function setDemo(on) {
  if (on && !demo) {
    demo = new DemoScript({ pads: DEMO_PADS });
  } else if (!on && demo) {
    for (const [key] of demo.held) noteOff(key);
    for (const [pad] of demo.padOff) padOff(pad);
    demo = null;
  }
  toast(demo ? "demo on" : "demo off");
}

// ------------------------------------------------------------------------------------------------- the frame --
function onFrame(rafNow) {
  requestAnimationFrame(onFrame);
  const gap = stats.last ? rafNow - stats.last : 0;
  stats.last = rafNow;
  const dt = clamp(gap / 1000, 0, 0.1);
  frameDt = dt > 0 ? dt : 1 / 60;
  trackTiming(gap, rafNow);
  const nowMs = performance.now();
  const nowS = nowMs / 1000;
  if (demo) {
    demo.tick(nowMs, demoEvent);
    demo.flush(nowMs, demoEvent);
  }
  if (snapQ.length) fireSnapped(nowMs);   // the beat snap's held hits whose 16th has come
  updateMusic(nowMs, nowS, dt);
  fx.update(nowS);
  updateImpact(nowS);
  updateKill(nowMs, dt);
  themeTick(nowMs);
  updatePalette();
  // the strobe's full-frame pulses: asked for at the strobe rate, granted at most three times a second
  const st = fx.strongest("strobe");
  if (st && st.env > 0.05 && nowS >= strobeNext) {
    const rate = Math.min(2 + 10 * T.strobeRate, 3);
    requestFlash(nowS, (0.22 + 0.33 * st.vel) * T.accent, 0.06);
    strobeNext = nowS + 1 / rate;
  }
  if (deck.running && nowMs - deck.start >= deck.ms) finishFade();
  updateLasers(nowMs, dt);        // before the strip: a laser-heads scene reads the head bus
  buildStrip(nowMs, nowS);
  buildAudio(nowS);
  padLights(nowMs, dt);
  persistValues(nowMs);
  sceneTick(nowMs);               // the dial's browse timeout; the scene report to the engine
  if (stage) stage.tick(nowMs);   // the showcase tour and the name card

  if (G.gl && !G.lost) {
    try {
      const gl = G.gl;
      resizeIfNeeded();
      gl.bindTexture(gl.TEXTURE_2D, G.stripTex);
      gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, STRIP.W, STRIP.H, gl.RGBA, gl.FLOAT, strip);
      gl.bindTexture(gl.TEXTURE_2D, G.audioTex);
      gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, AUDIO_TEX_W, 2, gl.RED, gl.UNSIGNED_BYTE, audioBytes);
      const mixAB = currentMix(nowMs);
      const A = sets[deck.a], B = sets[deck.b];
      if (A && A.program) renderSet(A, nowS);
      // the cued set also runs while a switch waits for its beat, so its feedback is warm when the transition starts
      if (B && B !== A && B.program && (mixAB > 0.001 || deck.running)) renderSet(B, nowS);
      if (freezeCapture) { captureFreeze(); freezeCapture = false; }
      fillOverlayUniforms(nowS);
      renderOverlay(nowS);
      renderBeams();
      const mixed = stage && A && A.fb && B && B.fb && B !== A ?
        stage.mix(deck, A.fb.texs[A.fb.read], B.fb.texs[B.fb.read], G.width, G.height, nowMs, nowS) : null;
      const drawn = composite(nowMs, nowS, mixAB, mixed);
      if (limiterLive()) {
        // the look draws into the limiter's input; the limiter meters it, decides and puts the frame on the canvas
        const looked = stage && stage.post(G.width, G.height, drawn, G.limiter.preTarget(G.width, G.height));
        G.limiter.run(looked ? G.limiter.preTexture() : drawn, G.width, G.height, frameDt);
      } else if (!(stage && stage.post(G.width, G.height, drawn))) copyToScreen(drawn);
      if (probe.on || probe.waiters.length) runProbe(nowMs);
      noteDrawn(nowMs);
      stats.frames++;
    } catch (err) {
      if (!frameErrorRecorded) {
        frameErrorRecorded = true;
        recordError("runtime", sets[deck.a] && sets[deck.a].id, `render: ${err.message || err}`);
      }
    }
  }
  if (nowMs - hudAt >= HUD_INTERVAL_MS) { hudAt = nowMs; updateHud(nowMs, nowS); }
}
let frameErrorRecorded = false;
let hudAt = 0;
let safeRefused = 0;              // pad effects refused in the safe mode
// gate v2 runs once its meter and apply programs have linked (they compile in the background; the decision too, and until
// it has, the JS twin decides on the CPU); until then, and for good if they fail, the page is in its safe mode: every pad
// effect refused
function limiterLive() {
  if (!G.limiter) return false;
  if (G.limiter.live()) {
    // the decision could not link: the limiter runs on, deciding on the CPU (said once)
    const err = G.limiter.error();
    if (err && !G.limiterError) { G.limiterError = err; recordError("compile", "vj-limiter", err); }
    return true;
  }
  const err = G.limiter.error();
  if (err && G.limiter.fatal() && G.limiterError !== err) {
    G.limiterError = err;
    recordError("compile", "vj-limiter", err);
    banner(SAFE_MODE_BANNER);
  }
  return false;
}
let frameDt = 1 / 60;
// the latency record: the first frame drawn after a pad event, and the effect's level in it
function noteDrawn(nowMs) {
  for (let i = latency.records.length - 1; i >= 0; i--) {
    const r = latency.records[i];
    if (r.frame !== null) break;
    if (nowMs < r.fired) continue;
    r.frame = +nowMs.toFixed(2);
    r.frameWall = Date.now();
    let env = 0;
    for (const f of fx.fx) if (f.active && f.serial === r.serial) env = f.env;
    r.env = +env.toFixed(3);
  }
}

function trackTiming(gap, rafNow) {
  if (!stats.fpsStart) stats.fpsStart = rafNow;
  stats.fpsCount++;
  if (rafNow - stats.fpsStart >= 1000) {
    stats.fps = (stats.fpsCount * 1000) / (rafNow - stats.fpsStart);
    stats.fpsCount = 0;
    stats.fpsStart = rafNow;
  }
  if (gap > 0 && gap < 250) {
    stats.gaps[stats.gapIdx] = gap;
    stats.gapIdx = (stats.gapIdx + 1) % stats.gaps.length;
    stats.gapN = Math.min(stats.gapN + 1, stats.gaps.length);
    // First Light's watchdog: 20 frames in a row slower than twice the 60 Hz budget lower the backing scale (min 0.5);
    // the HUD always shows the scale, so a lower resolution is never silent
    if (gap > 2 * FRAME_BUDGET_MS) stats.slowStreak++; else stats.slowStreak = 0;
    if (WATCHDOG && stats.slowStreak >= WATCHDOG_STREAK && G.scale > BACKING_SCALE_MIN) {
      G.scale = Math.max(BACKING_SCALE_MIN, G.scale * 0.75);
      stats.slowStreak = 0;
      stats.scaleDrops++;
    }
  }
}
function p95Gap() {
  if (!stats.gapN) return 0;
  const a = Array.from(stats.gaps.subarray(0, stats.gapN)).sort((x, y) => x - y);
  return a[Math.min(a.length - 1, Math.floor(a.length * 0.95))];
}

// ------------------------------------------------------------------------------------------------------- HUD --
let hudVisible = QS.get("hud") !== null ? QS.get("hud") !== "0" : QS.get("showcase") !== "1";   // the tour opens clean
function setText(id, text) { const el = $(id); if (el.textContent !== text) el.textContent = text; }
function setTextIf(id, text) { const el = $(id); if (el && el.textContent !== text) el.textContent = text; }
function updateHud(nowMs) {
  $("hud").classList.toggle("hidden", !hudVisible);
  $("hud-beatdot").classList.toggle("on", beat.pulse > 0.45);
  const A = sets[deck.a], B = sets[deck.b];
  const mixAB = currentMix(nowMs);
  let setLine = A ? A.name : "-";
  if (deck.running) setLine += `  → ${B.name} ${Math.round(mixAB * 100)}%`;
  else if (mixAB > 0.01) setLine += `  ⇄ ${B.name} ${Math.round(mixAB * 100)}%`;
  else if (B && B !== A) setLine += `  · next: ${B.name}`;
  if (!deck.pickup) setLine += "  (fader 8: pull down to pick up)";
  if (scenes.browsing()) { const b = sets[sceneList()[scenes.cursor]]; if (b) setLine += `  ▸ dial: ${b.name} (click to go)`; }
  if (options.snap) setLine += "  · beat snap";
  setText("hud-set", setLine);
  let eng;
  if (demo && !engine.url) eng = "demo (scripted show; ?engine= to use the KeyLab engine)";
  else if (!engine.url) eng = "off · keyboard pads only";
  else if (engine.link.open) {
    const h = engine.link.hello;
    eng = h ? `connected · ${h.src || "engine"} · beat ${h.beat_engine || "?"}${h.chords ? ` · chords ${h.chords}` : ""}` +
              ` · pads ${h.pads_mode || "?"}` : "connected";
    if (h && h.pads_mode === "daw") eng += " · FL may see pads 1-8";
    if (options.leds && engine.link.ledsOff) eng += ` · pad lights off: ${engine.link.ledsOff}`;
    if (engine.link.sceneOff) eng += ` · scene not reported: ${engine.link.sceneOff}`;
    if (demo) eng += " · demo playing on top";
  } else eng = `connecting to ${engine.url}… (keyboard pads work meanwhile)`;
  if (engine.link.status) eng += ` · ${engine.link.status}`;    // cleared on disconnect: never a dead engine's last word
  setText("hud-engine", eng);
  const bpm = beat.bpm > 0 && beat.alive(nowMs) ? `${beat.bpm.toFixed(1)} bpm · conf ${beat.conf.toFixed(2)}` : "no beat";
  setText("hud-beat", bpm + (beat.onBeat !== null && beat.alive(nowMs) ? ` · on-beat ${beat.onBeat.toFixed(2)}` : "") + ` · #${beat.count}` +
    (beat.src && beat.alive(nowMs) ? ` · ${beat.src}` : "") + (beat.bar > 0 && beat.alive(nowMs) ? ` · bar ${beat.barAt(nowMs)}` : ""));
  // Lasers v2: the gate the dial picked, the newest hit's deal, the area its light changes; the tap pads
  const lo = lasers.out;
  let lz = options.lasersClassic ? "classic burst (C: Lasers v2)" : `gate ${gateLabel(lasers.dial.gate)}`;
  if (!options.lasersClassic) {
    if (lo && lo.n) lz += ` · ${lo.tier || "-"} ${lo.gate} · ${lo.pattern} · bank ${lo.bank} · ${lo.order} · ${lo.colour}`;
    if (options.vibrate) lz += " · vibrate";
    if (lasers.pinned) lz += " · pinned";
    if (lo) lz += ` · change ${(100 * lo.area.window).toFixed(1)} % of a window`;
    if (lasers.heroOnly) lz += " · heads drawn by the scene";
  }
  if (tapPads.length) lz += ` · tap: pad ${[...new Set(tapPads.map((t) => t.pad))].join("/")}` +
    (tapLast ? ` (${tapLast.mode}${tapLast.bpm ? ` ${tapLast.bpm.toFixed(1)} bpm` : ""})` : "");
  setTextIf("hud-lasers", lz);
  const d = themes.dir;
  let th;
  if (!d) th = themes.error ? `themes unavailable: ${themes.error}` : "loading themes…";
  else {
    const base = themes.lib.byId.get(d.base);
    th = d.custom ? "Custom (Hue A and B; fader 2 turns them)" : `${base ? base.name : d.base} · ${base ? base.family : ""}`;
    const pend = d.state.pending;
    if (pend) th += ` → ${pend.custom ? "Custom" : (themes.lib.byId.get(pend.id)?.name || pend.id)}${pend.on ? ` on the ${pend.on}` : ""}`;
    if (d.locked) th += " · locked";
    if (options.keyAuto && d.key) th += ` · key ${d.key}`;
  }
  setTextIf("hud-theme", th);
  const c = feelFrame ? feelFrame.colour : null;
  const tension = harm.live ? `tension ${harm.value.toFixed(2)} (engine)` : c ? `tension ${c.tension.toFixed(2)}` : "";
  const colour = [tension, c ? `lush ${c.lushness.toFixed(2)}` : ""].filter(Boolean).join(" · ");
  const none = chord.name === "N" && chord.root < 0;
  // the confidence only for a chord heard in the audio (a played chord is read exactly: always 1)
  const conf = chord.src === "audio" && chord.conf !== null && !none ? ` ${chord.conf.toFixed(2)}` : "";
  setText("hud-chord", chord.name ? `${none ? "no chord" : chord.name}${chord.roman ? `  ${chord.roman}` : ""} (${chord.src}` +
    `${conf})${colour ? ` · ${colour}` : ""}` : "—");
  // the key: the engine's key event, else the key the last chord's numeral was read in
  const keyNow = harm.key || chord.key;
  setText("hud-key", keyNow ? `${keyNow}${harm.key ? ` · conf ${harm.keyConf.toFixed(2)}${harm.keySrc ? ` (${harm.keySrc})` : ""}` : ""}` +
    `${chord.roman && chord.key === keyNow ? ` · ${chord.roman}` : ""}` : "—");
  setText("hud-pedal", pedal.key >= 0 ? `${noteName(pedal.key)} ×${pedal.strikes()} · tension ${pedal.tension().toFixed(2)}` :
    (pedal.resolvePulse > 0.05 ? `released (${pedal.resolvedCount} strikes)` :
      harm.live && harm.pedalPc >= 0 ? `${NOTE_NAMES[harm.pedalPc]} held under the harmony (engine)` : "—"));
  const parts = [];
  for (const f of fx.fx) {
    if (!f.active) continue;
    const modes = f.type === "glitch" && glitchState.serial === f.serial && glitchState.plan ? `(${glitchState.plan.names.join("+")})` : "";
    parts.push(`${f.type}${modes}${f.tr === null && EFFECTS[f.type].hold ? "●" : ""} ${f.env.toFixed(2)}`);
  }
  if (frame.punch > 0.004) parts.push(`punch ${(frame.punch * 100).toFixed(1)}%`);
  if (kill.pending !== null) parts.push(kill.pending === 0 ? "KILL on beat" : "revive on beat");
  else if (kill.target < 0.5) parts.push("KILLED");
  setText("hud-fx", parts.length ? parts.join(" · ") : "—");
  setText("hud-flash", `granted ${gate.granted} · refused ${gate.refused} · most in a second ${gate.maxInAnyWindow()} (limit 3)`);
  setText("hud-ctl", learnTarget ? `learn: move a control for ${targetLabel(learnTarget)}` :
    lastCtl ? `${lastCtl.id} (${lastCtl.kind}) → ${lastCtl.target ? targetLabel(lastCtl.target) : "unbound"}` + (lastPadSrc ? ` · pads from ${lastPadSrc}` : "") :
    (lastPadSrc ? `pads from ${lastPadSrc}` : "—"));
  setText("hud-gl", `${G.width}×${G.height} · ${stats.fps.toFixed(0)} fps · p95 ${p95Gap().toFixed(1)} ms · ${G.fbFormat} · scale ${G.scale.toFixed(2)}`);
  const cells = padCells;
  for (let i = 0; i < 12; i++) {
    if (!cells[i]) continue;
    cells[i].style.background = ledColours[i];
    const label = isTapPad(tapPads, i + 1, "daw") ? "Tap (tempo)" : padMap[i] === "laser" && !options.lasersClassic ? "Lasers v2" : actionLabel(padMap[i]);
    if (cells[i].textContent !== `${i + 1} ${label}`) cells[i].textContent = `${i + 1} ${label}`;
  }
  if (!$("panel").hidden) refreshPanelValues();
}
const padCells = [];

// ----------------------------------------------------------------------------------------------------- panel --
function buildHudPads() {
  const host = $("hud-pads");
  host.textContent = "";
  for (let i = 0; i < 12; i++) {
    const d = document.createElement("div");
    d.className = "hud-pad";
    host.appendChild(d);
    padCells[i] = d;
  }
}
function renderSetList() {
  const ol = $("set-list");
  if (!ol) return;
  ol.textContent = "";
  sets.forEach((s, i) => {
    const li = document.createElement("li");
    if (i === deck.a) li.classList.add("active");
    if (i === deck.b && i !== deck.a) li.classList.add("cued");
    if (s.status === "broken") li.classList.add("broken");
    const name = document.createElement("span");
    name.textContent = s.name;
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = s.status === "broken" ? `broken: ${s.problem}` : i === deck.a ? "live" : i === deck.b ? "cued" : s.status;
    li.append(name, tag);
    li.title = s.problem || s.id;
    li.addEventListener("click", () => { if (validSet(i) && i !== deck.a) nextSet(i); });
    ol.appendChild(li);
  });
}
function renderParams() {
  const host = $("params");
  if (!host) return;
  const s = sets[deck.a];
  $("param-set-name").textContent = s ? s.name : "";
  host.textContent = "";
  if (!s) return;
  for (const p of s.params) {
    const row = document.createElement("div");
    row.className = "param";
    const label = document.createElement("label");
    label.textContent = `k${p.k} ${p.name}`;
    const input = document.createElement("input");
    input.type = "range"; input.min = "0"; input.max = "1"; input.step = "0.01";
    input.value = String(s.knobs[p.k - 1]);
    input.dataset.k = String(p.k);
    const val = document.createElement("span");
    val.className = "val";
    input.addEventListener("input", () => {
      const v = +input.value;
      if (p.k - 1 === s.trailsK) T.trails = v; else s.knobs[p.k - 1] = v;
    });
    row.append(label, input, val);
    host.appendChild(row);
  }
}
function renderPadMap() {
  const host = $("pad-map");
  host.textContent = "";
  for (let i = 0; i < 12; i++) {
    const cell = document.createElement("div");
    cell.className = "pad-cell";
    const no = document.createElement("div");
    no.className = "pad-no";
    const label = document.createElement("span");
    label.textContent = `pad ${i + 1}`;
    const sw = document.createElement("span");
    sw.className = "swatch";
    sw.dataset.pad = String(i);
    no.append(label, sw);
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", `Pad ${i + 1} action`);
    for (const a of PAD_ACTIONS) {
      const opt = document.createElement("option");
      opt.value = a;
      opt.textContent = actionLabel(a) + (EFFECTS[a] ? (EFFECTS[a].hold ? " (hold)" : " (one-shot)") : "");
      if (padMap[i] === a) opt.selected = true;
      sel.appendChild(opt);
    }
    sel.addEventListener("change", () => {
      padMap[i] = sel.value;
      savePadMap();
      sel.blur();   // hand the keys back to the pads
    });
    const help = EFFECTS[padMap[i]] ? `velocity: ${EFFECTS[padMap[i]].velocity}` : CONTROLS[padMap[i]] ? CONTROLS[padMap[i]].help : "";
    cell.title = help;
    cell.append(no, sel);
    host.appendChild(cell);
  }
}
function renderTargets() {
  const host = $("targets");
  host.textContent = "";
  const boundTo = {};
  for (const [id, t] of Object.entries(ctlMap)) (boundTo[t] = boundTo[t] || []).push(id);
  for (const t of TARGETS) {
    const row = document.createElement("div");
    row.className = "target";
    const label = document.createElement("label");
    label.textContent = targetLabel(t.id);
    label.title = t.help;
    const input = document.createElement("input");
    input.type = "range"; input.min = "0"; input.max = "1"; input.step = "0.01";
    input.dataset.target = t.id;
    input.addEventListener("input", () => setTarget(t.id, { kind: "abs", value: +input.value, delta: 0 }));
    const bind = document.createElement("span");
    bind.className = "bind";
    bind.textContent = (boundTo[t.id] || []).join(" ") || "unbound";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn" + (learnTarget === t.id ? " armed" : "");
    btn.textContent = learnTarget === t.id ? "Move…" : "Learn";
    btn.addEventListener("click", () => {
      learnTarget = learnTarget === t.id ? null : t.id;
      $("learn-status").textContent = learnTarget ? `move a control for ${targetLabel(t.id)}` : "";
      renderTargets();
    });
    row.append(label, input, bind, btn);
    host.appendChild(row);
  }
  // the action rows: the scenes (rewind / fast-forward step the sets on the DAW port; the scene dial and its click by
  // learn, since the dial picks the laser gate), the lasers and theme lock, the colour families (F1-F8, or learn the
  // buttons under the screen)
  const groups = [
    ["Scenes (Rewind / Fast forward step the sets; learn a dial to browse)", SCENE_ACTIONS],
    ["Lasers (the dial picks the gate, its click AUTO)", LASER_ACTIONS],
    ["Colour families (F1-F8)", FAMILY_ACTIONS],
  ];
  for (const [title, list] of groups) {
  const head = document.createElement("div");
  head.className = "target-head";
  head.textContent = title;
  host.appendChild(head);
  for (const a of list) {
    const row = document.createElement("div");
    row.className = "target scene-action";
    const label = document.createElement("label");
    label.textContent = a.label;
    label.title = a.help;
    const what = document.createElement("span");
    what.className = "val";
    what.textContent = a.id === "sceneDial" || a.id === "laserGate" ? "turn" : "press";
    const bind = document.createElement("span");
    bind.className = "bind";
    bind.textContent = (boundTo[a.id] || []).join(" ") || "unbound";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn" + (learnTarget === a.id ? " armed" : "");
    btn.textContent = learnTarget === a.id ? "Move…" : "Learn";
    btn.addEventListener("click", () => {
      learnTarget = learnTarget === a.id ? null : a.id;
      $("learn-status").textContent = learnTarget ? `press or turn a control for ${a.label}` : "";
      renderTargets();
    });
    row.append(label, what, bind, btn);
    host.appendChild(row);
  }
  }
  refreshPanelValues();
}
function refreshPanelValues() {
  const s = sets[deck.a];
  for (const input of document.querySelectorAll("#targets input[data-target]")) {
    const id = input.dataset.target;
    let v;
    if (/^k[1-8]$/.test(id)) { const k = +id[1] - 1; v = s ? (k === s.trailsK ? T.trails : s.knobs[k]) : 0; }
    else v = T[id];
    if (document.activeElement !== input) input.value = String(v);
  }
  for (const input of document.querySelectorAll("#params input[data-k]")) {
    const k = +input.dataset.k - 1;
    const v = k === s.trailsK ? T.trails : s.knobs[k];
    if (document.activeElement !== input) input.value = String(v);
    const val = input.parentElement.querySelector(".val");
    if (val) val.textContent = v.toFixed(2);
  }
  for (const sw of document.querySelectorAll("#pad-map .swatch")) sw.style.background = ledColours[+sw.dataset.pad];
}
function togglePanel(force) {
  const p = $("panel");
  p.hidden = force === undefined ? !p.hidden : !force;
  if (!p.hidden) { renderSetList(); renderParams(); renderPadMap(); renderTargets(); }
  else { learnTarget = null; }
}

function wireUi() {
  buildHudPads();
  $("btn-close-panel").addEventListener("click", () => togglePanel(false));
  $("btn-reset-pads").addEventListener("click", () => { padMap = DEFAULT_PAD_MAP.slice(); savePadMap(); renderPadMap(); });
  $("btn-reset-ctl").addEventListener("click", () => { ctlMap = { ...DEFAULT_CTL_MAP }; saveCtlMap(); renderTargets(); });
  const hits = $("opt-hits"), leds = $("opt-leds"), snapBox = $("opt-snap"), punchBox = $("opt-punch");
  const classicBox = $("opt-classic"), vibrateBox = $("opt-vibrate"), keyAutoBox = $("opt-keyauto");
  hits.checked = options.hits; leds.checked = options.leds;
  if (snapBox) snapBox.checked = options.snap;
  if (punchBox) punchBox.checked = options.punch;
  if (classicBox) classicBox.checked = options.lasersClassic;
  if (vibrateBox) vibrateBox.checked = options.vibrate;
  if (keyAutoBox) keyAutoBox.checked = options.keyAuto;
  const saveOpts = () => {
    options.hits = hits.checked; options.leds = leds.checked;
    if (snapBox) options.snap = snapBox.checked;
    if (punchBox) options.punch = punchBox.checked;
    if (keyAutoBox) options.keyAuto = keyAutoBox.checked;
    safeSet(STORE.opts, JSON.stringify(options));
  };
  for (const box of [hits, leds, snapBox, punchBox, keyAutoBox]) if (box) box.addEventListener("change", saveOpts);
  if (classicBox) classicBox.addEventListener("change", () => setLasersClassic(classicBox.checked));
  if (vibrateBox) vibrateBox.addEventListener("change", () => setVibrate(vibrateBox.checked));
  const typing = (el) => el && (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA") && el.type !== "range";
  window.addEventListener("keydown", (e) => {
    if (typing(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
    if (FAMILY_KEYS[e.code] !== undefined) {   // F1-F8: the family tabs
      e.preventDefault();
      if (!e.repeat) pickFamily(FAMILY_ACTIONS[FAMILY_KEYS[e.code]].family);
      return;
    }
    const pad = KEY_PADS[e.code];
    if (pad) {
      e.preventDefault();
      if (!e.repeat && !keyPadDown[pad]) { keyPadDown[pad] = 1; padOn(pad, e.shiftKey ? 1.0 : 0.6, "key"); }
      return;
    }
    if (e.repeat) return;
    const nowS = performance.now() / 1000;
    switch (e.code) {
      case "KeyQ": dampenAll(nowS); break;
      case "KeyW": choke(); break;
      case "KeyE": toggleKill(); break;
      case "KeyR": nextSet(); break;
      case "KeyH": hudVisible = !hudVisible; $("hud").classList.toggle("hidden", !hudVisible); break;
      case "KeyF": toggleFullscreen(); break;
      case "KeyM": togglePanel(); break;
      case "KeyD": setDemo(!demo); break;
      case "KeyB": setSnap(!options.snap); break;
      // Lasers v2: Vibrate, the classic burst, the gate (the dial's twin: [ and ], \ for AUTO)
      case "KeyV": setVibrate(!options.vibrate); toast(options.vibrate ? "lasers vibrate" : "vibrate off"); break;
      case "KeyC": setLasersClassic(!options.lasersClassic); toast(options.lasersClassic ? "lasers: classic burst" : "Lasers v2"); break;
      case "BracketLeft": case "BracketRight":
        lasers.dial.turn({ id: "key", kind: "rel", value: 0.5, delta: e.code === "BracketRight" ? 1 : -1 }, -1e9);
        laserGate(); toast(`laser gate: ${gateLabel(lasers.dial.gate)}`); break;
      case "Backslash": lasers.dial.auto(); laserGate(); toast("laser gate: AUTO"); break;
      case "KeyP": lasers.pinned = !lasers.pinned; lasers.eng.pin(lasers.pinned);   // spec 1.8: repeat the last hit exactly
        toast(lasers.pinned ? "lasers pinned: every hit repeats the last one" : "lasers unpinned"); break;
      case "Escape": if (learnTarget) { learnTarget = null; renderTargets(); } else togglePanel(false); break;
      default: return;
    }
    e.preventDefault();
  });
  window.addEventListener("keyup", (e) => {
    const pad = KEY_PADS[e.code];
    if (pad && keyPadDown[pad]) { keyPadDown[pad] = 0; padOff(pad); }
  });
  window.addEventListener("blur", () => {
    for (let p = 1; p <= 12; p++) if (keyPadDown[p]) { keyPadDown[p] = 0; padOff(p); }
  });
  let cursorTimer = 0;
  stageEl.addEventListener("mousemove", () => {
    stageEl.classList.remove("no-cursor");
    clearTimeout(cursorTimer);
    cursorTimer = setTimeout(() => stageEl.classList.add("no-cursor"), 2000);
  });
  canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); G.lost = true; recordError("runtime", null, "WebGL context lost"); });
  canvas.addEventListener("webglcontextrestored", () => {
    G.lost = false;
    for (const s of sets) { s.program = null; s.fb = null; }
    G.pool = []; G.ov = null; G.frz = null; G.cmp = null; G.stut = null; G.meter1 = null; G.meterMid = null; G.meter2 = null; G.limiter = null;
    G.beam = null;
    if (initGL()) for (const s of sets) if (s.source) compileSet(s);
  });
}
function setSnap(on) {
  options.snap = !!on;
  const box = $("opt-snap");
  if (box) box.checked = options.snap;
  safeSet(STORE.opts, JSON.stringify(options));
  toast(options.snap ? "beat snap on: hits land on the next 16th of the beat" : "beat snap off");
}
function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  else document.documentElement.requestFullscreen().catch(() => {});
}

// ----------------------------------------------------------------------------------------- wave 2: the stage --
// vj-stage.js: beat-synced transitions, the post look and the showcase tour, reading the page through these accessors.
const stage = createStage({
  stage: stageEl,
  beat: () => beat, deck: () => deck, sets: () => sets, setId: (i) => (sets[i] ? sets[i].id : null),
  // the demo numbers its bars; the engine does not. The page's own demo is known by `demo` (its hello never reaches the
  // engine link); an engine replaying its own demo groove (--replay-audio demo) says so in its hello.
  barsKnown: () => !!demo || !!(engine.link.hello && engine.link.hello.beat_engine === "demo"),
  palette: () => palNow, hit: () => hit.pulse,
  nextSet: (style) => nextSet(null, performance.now(), style),
  setDemo: (on) => setDemo(on), demoOn: () => !!demo,
  engineUrl: () => engine.url, engineOpen: () => engine.link.open, engineLastMsg: () => engine.lastMsg,
  press: (pad, vel) => padOn(pad, vel, "tour"), release: (pad) => padOff(pad), padMap: () => padMap,
  learning: () => !!learnTarget,
  unbindCtl: (id) => {
    ctlMap = { ...ctlMap, [id]: null };
    saveCtlMap();
    if (!$("panel").hidden) renderTargets();
  },
  toast, recordError,
});

// --------------------------------------------------------------------------------------------- the test hook --
window.__vj = {
  api: VJ_API,
  ready: false,
  sets: () => sets.map((s) => ({ id: s.id, name: s.name, status: s.status, problem: s.problem, vj: s.vj, broken: s.status === "broken" })),
  select: (id) => selectSet(sets.findIndex((s) => s.id === id)),
  next: () => { nextSet(); return deck.b; },
  active: () => { const s = sets[deck.a]; return s ? { id: s.id, compiled: s.status === "ok" && !!s.program, frame: s.frame } : null; },
  stats: () => ({
    frames: stats.frames, fps: +stats.fps.toFixed(1), p95: +p95Gap().toFixed(2), width: G.width, height: G.height,
    scale: G.scale, scaleDrops: stats.scaleDrops, format: G.fbFormat,
    setA: sets[deck.a] && sets[deck.a].id, setB: sets[deck.b] && sets[deck.b].id, mix: +currentMix(performance.now()).toFixed(3),
    fading: deck.running, pickup: deck.pickup,
    engine: { url: engine.url, open: engine.link.open, hello: engine.link.hello, events: engine.events, bad: engine.bad,
              demoEvents: engine.demoEvents, status: engine.link.status, ledsOff: engine.link.ledsOff, refused: engine.link.refused },
    demo: !!demo, bpm: beat.bpm, beats: beat.count, chord: chord.name, chordSrc: chord.src, stars: starCount,
    roman: chord.roman, chordKey: chord.key, bass: chord.bass, chordConf: chord.conf,
    harmony: { key: harm.key, keyConf: harm.keyConf, keySrc: harm.keySrc, keyChanges: harm.keyChanges, keyAccents,
               live: harm.live, tension: +harm.value.toFixed(3), target: harm.target, pedalPc: harm.pedalPc,
               src: harm.src, strip: +strip[(0 * STRIP.W + 14) * 4 + 2].toFixed(3), chordPulse: +chordPulse.toFixed(3) },
    pedal: { key: pedal.key, strikes: pedal.strikes(), tension: +pedal.tension().toFixed(3), resolved: pedal.resolvedCount },
    tension: feelFrame ? +feelFrame.colour.tension.toFixed(3) : null,
    effects: fx.fx.filter((f) => f.active).map((f) => ({ type: f.type, pad: f.pad, env: +f.env.toFixed(3), vel: f.vel,
      held: f.tr === null, granted: f.granted })),
    flash: { granted: gate.granted, refused: gate.refused, maxInAnyWindow: gate.maxInAnyWindow(), log: gate.log().map((t) => +t.toFixed(3)) },
    kill: { gain: +kill.gain.toFixed(3), target: kill.target, pending: kill.pending },
    leds: { posts: led.posts, refused: engine.link.refused, off: engine.link.ledsOff, last: ledColours.slice(),
            log: led.log.slice(-50) },
    values: { ...T }, padMap: padMap.slice(), ctlMap: { ...ctlMap }, lastCtl,
    // the impact pass
    impact: { punch: +frame.punch.toFixed(4), zoom: +frame.zoom.toFixed(4), shake: [+frame.shakeX.toFixed(4), +frame.shakeY.toFixed(4)],
              dip: +frame.dip.toFixed(3), dipGranted: frame.dipGranted, glow: +frame.glow.toFixed(3), hits: impact.count,
              pulse: +impact.out.pulse.toFixed(3), code: impact.out.code },
    bands: { kick: +bands.env.kick.toFixed(3), snare: +bands.env.snare.toFixed(3), hat: +bands.env.hat.toFixed(3),
             bass: +bands.level.bass.toFixed(3) },
    energyEvents: energy.events, energyRate: (() => { const t = performance.now(); let n = 0; for (const s of energy.stamps) if (t - s <= 1000) n++; return n; })(),
    glitch: glitchState.plan ? { serial: glitchState.serial, ...glitchState.plan } : null,
    options: { ...options }, snapQueued: snapQ.length,
    // gate v2 (no readback here: window.__vj.limiter() reads its state)
    limiter: { on: limiterLive(), mode: G.limiter ? G.limiter.mode() : "", format: G.limiter ? G.limiter.format : null,
               frames: G.limiter ? G.limiter.frames() : 0, compileMs: G.limiter ? G.limiter.compileMs() : null,
               gpuMs: G.limiter ? G.limiter.gpuMs() : null, parallel: G.limiter ? G.limiter.parallel : null,
               error: G.limiterError, fatal: G.limiter ? G.limiter.fatal() : !!G.limiterError, asked: LIMITER_MODE,
               safeRefused, grid: G.limiter ? G.limiter.grid() : null },
    scenes: { browsing: scenes.browsing(), cursor: scenes.cursor, ignored: scenes.ignored, posts: sceneReport.posts,
              log: sceneReport.log.slice(-20), sentKey: sceneReport.sentKey, off: engine.link.sceneOff,
              refused: engine.link.sceneRefused, echo: sceneReport.last },
    // Lasers v2 (vj-lasers.js through vj-hookup.js)
    lasers: (() => {
      const o = lasers.out;
      return { mode: options.lasersClassic ? "classic" : "v2", gate: lasers.dial.gate, gateIndex: lasers.dial.index,
               dialSteps: lasers.dial.steps, dialIgnored: lasers.dial.ignored, vibrate: options.vibrate, seed: lasers.seed,
               hits: lasers.hits, refused: lasers.refused, last: lasers.last, held: lasers.held, cut: lasers.cut,
               gain: +lasers.gain.toFixed(3), records: o ? o.n : 0, uploaded: lasers.n, heroOnly: lasers.heroOnly,
               busOn: lasers.busOn, bus: lasers.busOn ? Array.from(lasers.bus, (v) => +v.toFixed(3)) : null,
               pulses: lasers.pulses, flashes: lasers.flashes, frames: lasers.frames, litFrames: lasers.litFrames,
               overFrames: lasers.over, maxWindow: +lasers.maxWindow.toFixed(4), maxFrame: +lasers.maxFrame.toFixed(4),
               area: o ? { ...o.area } : null, tier: o ? o.tier : "", solo: o ? o.solo : 1,
               pad: o ? { level: +o.pad.level.toFixed(3), tier: o.pad.tier } : null, theme: lasers.themeId,
               labels: o ? { gate: o.gate, pattern: o.pattern, tier: o.tier, bank: o.bank, order: o.order, colour: o.colour } : null };
    })(),
    themes: (() => {
      const d = themes.dir;
      return { loaded: !!d, error: themes.error, current: d ? d.current : null, base: d ? d.base : null, custom: d ? d.custom : false,
               name: themes.look ? themes.look.name : d && d.custom ? "Custom" : null, family: themes.look ? themes.look.family : null,
               pending: d && d.state.pending ? { id: d.state.pending.id, on: d.state.pending.on, reason: d.state.pending.reason } : null,
               locked: d ? d.locked : false, key: d ? d.key : null, mode: d ? d.mode : null, keyAuto: options.keyAuto,
               changes: themes.changes, cuts: themes.cuts, last: themes.lastChange, keyEvents: themes.keyEvents,
               fader: +T.theme.toFixed(4), faderTheme: themes.lib ? themeAtFader(themes.lib, T.theme) : null,
               palette: Array.from(palNow, (v) => +v.toFixed(4)) };
    })(),
    tap: { pads: tapPads.map((t) => ({ ...t })), presses: tapPresses, last: tapLast },
    clock: { pos: beat.posAt(performance.now()), bar: beat.bar, barNow: beat.barAt(performance.now()), ver: beat.ver, src: beat.src,
             reanchors: beat.reanchors, slews: beat.slews, flushed: beat.flushed, lastError: +beat.lastError.toFixed(4) },
    ledsWashed: led.washed,
  }),
  // Lasers v2 receipts (arsenal/lanes/vj_verify.mjs): the hits dealt, the laser options, the beam layer's own light
  laserLog: () => lasers.log.map((h) => ({ ...h })),
  laser: (o = {}) => {
    if (typeof o.vibrate === "boolean") setVibrate(o.vibrate);
    if (typeof o.classic === "boolean") setLasersClassic(o.classic);
    if (typeof o.gate === "string") { lasers.dial.set(o.gate); laserGate(); }
    if (typeof o.bank === "string") lasers.eng.set({ bankMode: o.bank });
    return { gate: lasers.dial.gate, vibrate: options.vibrate, classic: options.lasersClassic };
  },
  // the beam layer as drawn this frame: pixels lit (relative luminance >= 0.02), the brightest, the mean (a GPU readback)
  beams: () => {
    if (!G.gl || !G.beam) return null;
    const gl = G.gl, b = G.beam, px = new Float32Array(b.w * b.h * 4);
    try {
      gl.bindFramebuffer(gl.FRAMEBUFFER, b.fbos[0]);
      gl.readPixels(0, 0, b.w, b.h, gl.RGBA, gl.FLOAT, px);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    } catch (err) { return { error: String(err.message || err) }; }
    let lit = 0, max = 0, sum = 0;
    for (let i = 0; i < px.length; i += 4) {
      const y = 0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2];
      if (y >= 0.02) lit++;
      if (y > max) max = y;
      sum += y;
    }
    return { w: b.w, h: b.h, lit, litShare: +(lit / (b.w * b.h)).toFixed(5), max: +max.toFixed(4), mean: +(sum / (b.w * b.h)).toFixed(6),
             records: lasers.n, clear: !!G.beamClear };
  },
  // a theme now (contact sheets, receipts): the director's base theme set at once, no bar to wait for
  theme: (id) => {
    const d = themes.dir;
    if (!d || !(id === "custom" || themes.lib.byId.has(id))) return null;
    if (id === "custom") { d.current = "custom"; d.custom = true; } else { d.current = id; d.base = id; d.custom = false; }
    d.pending = null;
    themes.lookKey = "";
    themeTick(performance.now());
    updatePalette();
    palBefore.set(palNow); travel = 1;
    return d.current;
  },
  catalogue: () => laserCatalogue(),
  // a pinned pattern (receipts, contact sheets): "auto", a vj-lasers.js PATTERNS id, or "figure" (line art from the shape deck)
  laserPattern: (p) => { lasers.eng.set({ patternMode: p === "auto" || !p ? "auto" : p, shapeMode: p === "figure" ? "auto" : null }); return p; },
  latency: () => ({ records: latency.records.map((r) => ({ ...r })) }),
  snap: (on) => { setSnap(on); return options.snap; },
  option: (k, v) => { if (k in options) { options[k] = !!v; } return { ...options }; },
  errors: () => errors.slice(),
  event: (obj) => handleEvent(obj),
  press: (pad, vel = 0.8) => padOn(pad, vel, "test"),
  release: (pad) => padOff(pad),
  learn: (target) => { learnTarget = target; },
  probe: (on) => { probe.on = !!on; if (on) probe.trace = []; return probe.on; },
  trace: () => probe.trace.slice(),
  luma: () => new Promise((resolve) => probe.waiters.push(resolve)),
  demo: (on) => { setDemo(!!on); return !!demo; },
  // gate v2 (receipts: arsenal/lanes/vj_storm.mjs). limiter() reads its state back (a GPU stall: receipts only);
  // limiterCells(cells, dt) runs the decision alone on given cell sums (the JS twin's input, vj-gate.js); limiterBench(n)
  // times n runs of the limiter's passes on the last frame, each fenced by readPixels of one pixel (the cost receipt)
  limiter: () => (limiterLive() ? { on: true, format: G.limiter.format, ...G.limiter.read() } : { on: false, error: G.limiterError || "compiling", safeRefused }),
  limiterCells: (cells, dt) => (limiterLive() ? G.limiter.decideCells(new Float32Array(cells), dt) : null),
  limiterReset: () => { if (limiterLive()) G.limiter.reset(); return limiterLive(); },
  limiterBench: (n = 20) => {
    if (!limiterLive() || !G.cmp) return null;
    const gl = G.gl, px = new Uint8Array(4), src = G.cmp.texs[G.cmp.read];
    const fence = () => gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    fence();
    // (Date.now: the receipts' virtual clock replaces performance.now, and a bench needs the wall clock)
    const parts = { meter: 0, decide: 0, apply: 0, blit: 0 };
    let tm = 0;
    const mark = (stage) => { fence(); const t = Date.now(); parts[stage] += t - tm; tm = t; };
    const t0 = Date.now();
    for (let i = 0; i < n; i++) { tm = Date.now(); G.limiter.run(src, G.width, G.height, 1 / 60, mark); }
    const t1 = Date.now();
    for (let i = 0; i < n; i++) { copyToScreen(src); fence(); }
    const t2 = Date.now();
    for (const k of Object.keys(parts)) parts[k] = +(parts[k] / n).toFixed(3);
    return { n, limiter_ms: (t1 - t0) / n, copy_ms: (t2 - t1) / n, parts_ms: parts, width: G.width, height: G.height };
  },
};

// ------------------------------------------------------------------------------------------------------ boot --
async function boot() {
  if (location.protocol === "file:") {   // modules and presets need a server; and never a GPU page from a file pane
    banner("Open the VJ rig through a server: py -m arsenal serve, then http://127.0.0.1:8793/web/vj.html");
    return;
  }
  loadStored();
  wireUi();
  if (options.vibrate) lasers.eng.setVibrate(true, performance.now());
  const themesLoaded = loadThemes();     // the colour themes' library (vj-themes.json), alongside the GL and the sets
  updatePalette();
  palBefore.set(palNow);
  if (!initGL()) return;
  try {
    const mod = await import("./piano/harmony-feel.js");
    feel = mod.createHarmonyFeel();
  } catch (err) {
    recordError("load", "harmony-feel", err.message || err);
  }
  connectEngine();
  if (DEMO_AT_START) setDemo(true);
  requestAnimationFrame(onFrame);
  await Promise.all(sets.map(loadSet));
  if (!validSet(deck.a)) deck.a = nextValid(deck.a);
  deck.b = nextValid(deck.a);
  if (QS.get("showcase") === "1") {   // the tour opens on the first wave-2 set
    const opener = sets.findIndex((s) => s.id === "vj-hyperspace");
    if (validSet(opener)) selectSet(opener, true);
  }
  renderSetList();
  renderParams();
  queueSceneReport(false);        // the sets have their names now: tell the engine which one shows
  await themesLoaded;
  window.__vj.ready = true;
  toast(sets[deck.a] ? sets[deck.a].name : "no sets");
  stage.boot();
}
boot();
