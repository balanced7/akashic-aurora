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
//   3. THE COMPOSITE: mixes the sets, bends them (kaleidoscope, glitch, shockwave refraction, freeze), adds the overlay and
//      applies the full-frame accents (invert, the gated white flash and strobe pulses), saturation and master brightness.
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
// Safety: full-frame flashes pass the FlashGate (<= 3 in any second) in JS and envFlashSafe in the composite shader.
import {
  VJ_API, STRIP, createStrip, stripSet, parseEvent, pitchColours, hueColour, linearToOklab, oklabToLinear, rgbToHex,
  starPosition, fifthsIndex, EFFECTS, CONTROLS, PAD_ACTIONS, DEFAULT_PAD_MAP, normalizePadMap, actionLabel, TARGETS,
  DEFAULT_CTL_MAP, normalizeCtlMap, learnBinding, applyCtl, FlashGate, EffectBank, BeatClock, PedalDetector,
  pedalSignature, EngineLink, EngineHarmony, DemoScript,
} from "./vj-core.js";
import { createStage } from "./vj-stage.js";   // wave 2: beat-synced transitions, the post look, the showcase tour

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
const STORE = { pads: "arsenal.vj.padMap", ctl: "arsenal.vj.ctlMap", values: "arsenal.vj.values", opts: "arsenal.vj.options" };
const KEY_PADS = { Digit1: 1, Digit2: 2, Digit3: 3, Digit4: 4, Digit5: 5, Digit6: 6, Digit7: 7, Digit8: 8, Digit9: 9,
                   Digit0: 10, Minus: 11, Equal: 12 };
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
uniform vec4 u_waveB[4];     // width px, velocity, -, -
uniform vec3 u_waveCol[4];
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

// The composite: sets (display values) -> bends -> overlay (linear) -> full-frame accents -> master.
const COMPOSITE_FS = `#version 300 es
precision highp float;
uniform sampler2D u_a, u_b, u_ov, u_frz;
uniform vec2 u_res;
uniform float u_mix;
uniform float u_kal, u_kalN, u_kalRot;
uniform float u_glitch, u_glitchT, u_glitchCells;
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
in vec2 v_uv;
out vec4 outColor;
const float PI = 3.14159265358979;
const float TAU = 6.28318530717959;
// motion-envelope envFlashSafe (arsenal/web/glsl/motion/envelope.glsl): 0 until a third of a second after the previous
// full-field flash, 1 from half a second on -- the shader's own copy of the gate the page keeps (FlashGate, vj-core.js)
float envFlashSafe(float sinceLastFlash) { return smoothstep(1.0 / 3.0, 0.5, sinceLastFlash); }
float h12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec3 sets(vec2 uv) {
  vec3 a = texture(u_a, uv).rgb;
  if (u_mix > 0.001) {
    float m = clamp(u_mix, 0.0, 1.0);
    a = mix(a, texture(u_b, uv).rgb, m * m * (3.0 - 2.0 * m));
  }
  return a;
}
vec3 glitched(vec2 uv, float asp) {
  if (u_glitch < 0.001) return sets(uv);
  vec2 cells = vec2(u_glitchCells * asp * 0.6, u_glitchCells);
  vec2 cell = floor(uv * cells);
  float h = h12(cell + u_glitchT * 13.17);
  vec2 off = vec2(0.0);
  if (h < 0.35 * u_glitch) off.x = (h12(cell * 1.7 + u_glitchT) - 0.5) * 0.18 * u_glitch;
  float row = h12(vec2(floor(uv.y * cells.y * 3.0), u_glitchT));
  if (row < 0.12 * u_glitch) off.x += (row - 0.06) * 0.5;
  float split = 0.004 + 0.012 * u_glitch;
  vec2 q = uv + off;
  return vec3(sets(q + vec2(split, 0.0)).r, sets(q).g, sets(q - vec2(split, 0.0)).b);
}
void main() {
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 uv = v_uv;
  vec2 p = (uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  // shockwaves bend the picture where their rings pass
  for (int i = 0; i < 4; i++) {
    vec4 w = u_wave[i];
    if (w.w < 0.001) continue;
    vec2 d = p - w.xy;
    float r = length(d);
    float width = max(u_waveB[i].x, 1.0) * px * 3.0;
    float ring = (r - w.z) / width;
    uv += (d / max(r, 1e-4)) * exp(-ring * ring) * ring * 0.010 * w.w * u_accent / vec2(asp, 1.0);
  }
  vec3 c = glitched(uv, asp);
  if (u_kal > 0.001) {                                 // kaleidoscope: fold the angle into mirrored segments
    vec2 q = (uv - 0.5) * vec2(asp, 1.0);
    float seg = TAU / max(u_kalN, 2.0);
    float a = mod(atan(q.y, q.x) + u_kalRot, seg);
    a = min(a, seg - a);
    vec2 k = length(q) * vec2(cos(a), sin(a));
    vec2 kuv = k / vec2(asp, 1.0) + 0.5;
    kuv = abs(mod(kuv - 1.0, 2.0) - 1.0);               // mirror at the edges instead of smearing them
    c = mix(c, sets(kuv), clamp(u_kal, 0.0, 1.0));
  }
  if (u_freeze > 0.001) {
    vec2 fuv = (uv - 0.5) * (1.0 - u_freezeZoom) + 0.5;
    c = mix(c, texture(u_frz, fuv).rgb, clamp(u_freeze, 0.0, 1.0));
  }
  // to linear light, add the accents, a soft shoulder, back to display values
  vec3 lin = pow(max(c, vec3(0.0)), vec3(2.2));
  lin += texture(u_ov, v_uv).rgb * u_accent;
  float edge = smoothstep(0.30, 0.62, max(abs(p.x) / max(asp, 1e-3), abs(p.y)));
  lin += u_metroCol * u_metro * edge;                  // the metronome: a breath at the frame's edge
  lin += u_bloomCol * u_bloom * exp(-dot(p, p) * 5.0); // hits: a soft lift at the centre (kept under the flash line)
  vec3 over = max(lin - 0.8, 0.0);
  lin = min(lin, vec3(0.8)) + 0.2 * tanh(over / 0.2);
  c = pow(lin, vec3(1.0 / 2.2));
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  c = mix(vec3(l), c, u_sat);
  c = mix(c, 1.0 - c, clamp(u_invert, 0.0, 1.0));
  c = mix(c, vec3(1.0), clamp(u_flash, 0.0, 1.0) * envFlashSafe(u_flashGap));
  c *= u_bright;
  if (any(isnan(c)) || any(isinf(c))) c = vec3(0.0);
  c += (h12(gl_FragCoord.xy) - 0.5) / 255.0 * u_bright;   // a static dither (per pixel, never per frame)
  outColor = vec4(clamp(c, 0.0, 1.0), 1.0);
}`;

// ---------------------------------------------------------------------------------------------------- the state --
const $ = (id) => document.getElementById(id);
const canvas = $("gl");
const stageEl = $("stage");
const errors = [];
const T = {};
for (const t of TARGETS) if (t.def !== null) T[t.id] = t.def;
const options = { hits: true, leds: true };

const sets = SET_IDS.map((id) => ({
  id, name: id, author: "", tags: [], params: [], knobs: new Float32Array(8), defaults: new Float32Array(8),
  status: "loading", problem: "", program: null, uniforms: null, fb: null, frame: 0, vj: false, source: "", trailsK: -1,
}));
const deck = { a: 0, b: Math.min(1, sets.length - 1), running: false, start: 0, ms: 0, pickup: true, from: 0 };

const gate = new FlashGate();
const fx = new EffectBank();
const beat = new BeatClock();
const pedal = new PedalDetector();
let padMap = DEFAULT_PAD_MAP.slice();
let ctlMap = { ...DEFAULT_CTL_MAP };
let learnTarget = null;
let lastCtl = null;
let lastPadSrc = "";
const padHeld = new Uint8Array(12);
const padT0 = new Float64Array(12).fill(-1e9);
const padPress = new Float32Array(12);           // a press flash for the control pads' lights
const keyPadDown = new Uint8Array(13);

// music
const energy = { bass: 0, mid: 0, high: 0, level: 0, tBass: 0, tMid: 0, tHigh: 0, tLevel: 0, last: -1e9 };
const hit = { pulse: 0, kick: 0, snare: 0, hat: 0, bloom: 0 };
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
let demo = null;

// engine
// link: open, the engine's hello and status, and whether pad colours may be posted (vj-core.js EngineLink)
const engine = { url: ENGINE_URL, es: null, link: new EngineLink(), events: 0, bad: 0, demoEvents: 0, lastMsg: -1e9 };
const led = { last: "", lastAt: -1e9, computedAt: -1e9, inflight: false, backoffUntil: 0, posts: 0, log: [] };

// GL
const G = { gl: null, lost: false, parallel: null, fbInternal: 0, fbType: 0, fbFormat: "", stripTex: null, audioTex: null,
            blackTex: null, ov: null, frz: null, ovProg: null, ovU: null, compProg: null, compU: null, pool: [],
            width: 1, height: 1, scale: 1 };
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
  G.pool = [];
  G.ov = null;
  G.frz = null;
  try {
    G.ovProg = linkSync(gl, OVERLAY_FS);
    G.ovU = uniformsOf(gl, G.ovProg, ["u_prevOv", "u_res", "u_keep", "u_wave", "u_waveB", "u_waveCol", "u_laser", "u_laserB",
      "u_laserCol", "u_part", "u_partB", "u_partCol", "u_note", "u_noteCol", "u_bars", "u_barsPhase", "u_barsCol"]);
    G.compProg = linkSync(gl, COMPOSITE_FS);
    G.compU = uniformsOf(gl, G.compProg, ["u_a", "u_b", "u_ov", "u_frz", "u_res", "u_mix", "u_kal", "u_kalN", "u_kalRot",
      "u_glitch", "u_glitchT", "u_glitchCells", "u_freeze", "u_freezeZoom", "u_wave", "u_waveB", "u_flash", "u_flashGap",
      "u_invert", "u_bright", "u_sat", "u_accent", "u_metro", "u_metroCol", "u_bloom", "u_bloomCol"]);
    gl.useProgram(G.compProg);
    gl.uniform1i(G.compU.u_a, 0); gl.uniform1i(G.compU.u_b, 1); gl.uniform1i(G.compU.u_ov, 2); gl.uniform1i(G.compU.u_frz, 3);
    gl.useProgram(G.ovProg);
    gl.uniform1i(G.ovU.u_prevOv, 0);
  } catch (err) {
    recordError("compile", "vj-built-in", err.message || err);
    banner("A built-in VJ shader failed to compile; see the console.");
    return false;
  }
  if (stage) stage.initGL(gl, { internalFormat: G.fbInternal, type: G.fbType });   // transitions and the look
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
}
function createSingle(w, h) {
  const gl = G.gl;
  const tex = createTexture(gl, gl.LINEAR);
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
function nextSet(to = null, nowMs = performance.now(), style = null) {
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
  if (stage) stage.landed(performance.now());
}
function selectSet(i) {           // a cut, for the test hook and a click while nothing plays
  if (!validSet(i)) return false;
  if (deck.running) finishFade();
  const old = sets[deck.a];
  deck.a = i;
  deck.b = nextValid(i);
  if (old !== sets[deck.a] && old !== sets[deck.b]) releaseFb(old);
  renderSetList();
  renderParams();
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
      if (!fromDemo) { engine.link.event(ev); harm.reset(); }   // a new engine: its key and tension are still to come
      break;
    case "status":
      if (!fromDemo) engine.link.event(ev);
      break;
    case "key":
      if (harm.event(ev)) keyChange(nowS);
      break;
    case "tension":
      harm.event(ev);
      break;
    case "beat":
      beat.schedule(nowMs, ev);
      break;
    case "energy":
      energy.tBass = ev.bass; energy.tMid = ev.mid; energy.tHigh = ev.high; energy.tLevel = ev.level; energy.last = nowMs;
      break;
    case "hit": {
      hit.pulse = Math.max(hit.pulse, ev.strength);
      if (ev.band === "kick" || ev.band === "full") hit.kick = Math.max(hit.kick, ev.strength);
      if (ev.band === "snare" || ev.band === "full") hit.snare = Math.max(hit.snare, ev.strength);
      if (ev.band === "hat") hit.hat = Math.max(hit.hat, ev.strength);
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
      if (ev.on && ev.vel > 0) padOn(ev.pad, ev.vel, ev.src, nowS); else padOff(ev.pad, nowS);
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
  padHeld[i] = 1;
  padT0[i] = nowS;
  padPress[i] = 1;
  lastPadSrc = src;
  const action = padMap[i];
  if (EFFECTS[action]) triggerEffect(action, vel, pad, nowS);
  else if (action === "dampen") fx.dampen(nowS);
  else if (action === "choke") choke();
  else if (action === "kill") toggleKill();
  else if (action === "next") nextSet();
}
function padOff(pad, nowS = performance.now() / 1000) {
  padHeld[pad - 1] = 0;
  fx.release(pad, nowS);
}
function choke() {
  fx.choke();
  flash.peak = 0;
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
  fx.trigger(type, vel, nowS, { pad, granted });
  if (type === "freeze") freezeCapture = true;
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
  // DAW port's CC 25 / 26, on the press. Our FL script swallows them (SCRUB_TO_FL), so FL does not scrub as well.
  // ?transport=off hands them back to the control map like any other control.
  if (TRANSPORT_SETS && (ev.id === "cc25" || ev.id === "cc26") && ev.port !== "midi") {
    lastCtl.target = "sets";
    if (ev.value >= 0.5) nextSet(ev.id === "cc26" ? nextValid(deck.a) : prevValid(deck.a));
    return;
  }
  if (stage && stage.onCtl(ev)) { lastCtl.target = "look"; return; }   // the look's fader (vj-stage.js)
  if (learnTarget) {
    ctlMap = learnBinding(ctlMap, ev.id, learnTarget);
    lastCtl.target = learnTarget;
    safeSet(STORE.ctl, JSON.stringify(ctlMap));
    $("learn-status").textContent = `${ev.id} → ${targetLabel(learnTarget)}`;
    learnTarget = null;
    renderTargets();
    return;
  }
  const target = ctlMap[ev.id];
  lastCtl.target = target || null;
  if (target) setTarget(target, ev);
}
function targetLabel(id) {
  if (/^k[1-8]$/.test(id)) {
    const s = sets[deck.a];
    const p = s && s.params.find((q) => q.k === +id[1]);
    return p ? `${id} ${p.name}` : id;
  }
  const t = TARGETS.find((x) => x.id === id);
  return t ? t.label : id;
}
function setTarget(target, ev) {
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
    if (o && typeof o === "object") { options.hits = o.hits !== false; options.leds = o.leds !== false; }
  } catch { /* defaults */ }
}

// ------------------------------------------------------------------------------------------- the frame update --
function updateMusic(nowMs, nowS, dt) {
  beat.update(nowMs, dt);
  // energy: quick to rise, slower to fall; silence after 1.5 s without an energy event
  if (nowMs - energy.last > 1500) { energy.tBass = energy.tMid = energy.tHigh = energy.tLevel = 0; }
  energy.bass = easeTo(energy.bass, energy.tBass, dt);
  energy.mid = easeTo(energy.mid, energy.tMid, dt);
  energy.high = easeTo(energy.high, energy.tHigh, dt);
  energy.level = easeTo(energy.level, energy.tLevel, dt);
  const decay = Math.exp(-dt / 0.18);
  hit.pulse *= decay; hit.kick *= decay; hit.snare *= decay; hit.hat *= Math.exp(-dt / 0.08);
  hit.bloom *= Math.exp(-dt / 0.15);
  const target = 0.65 * energy.bass + 0.35 * hit.pulse;
  pulseEnv += (target - pulseEnv) * (1 - Math.exp(-dt / (target > pulseEnv ? 0.012 : 0.18)));
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
function easeTo(cur, tgt, dt) { return cur + (tgt - cur) * (1 - Math.exp(-dt / (tgt > cur ? 0.03 : 0.12))); }

function updatePalette() {
  // the fader palette: hue A, hue B, the hue between them, and hue A's complement as the accent
  const a = T.hueA, b = T.hueB;
  let d = b - a; d -= Math.round(d);
  const fa = hueColour(a, 0.70), fb = hueColour(b, 0.62), fm = hueColour(a + d * 0.5, 0.78), fc = hueColour(a + 0.5, 0.72);
  const fader = faderStops;
  fader[0] = fa[0]; fader[1] = fa[1]; fader[2] = fa[2];
  fader[3] = fb[0]; fader[4] = fb[1]; fader[5] = fb[2];
  fader[6] = fm[0]; fader[7] = fm[1]; fader[8] = fm[2];
  fader[9] = fc[0]; fader[10] = fc[1]; fader[11] = fc[2];
  const amt = T.chordAmt * chordPresence;
  for (let k = 0; k < 4; k++) oklabMix(fader, k * 3, chordStops, k * 3, amt, palTarget, k * 3);
  const e = smooth(travel);
  for (let k = 0; k < 4; k++) oklabMix(palBefore, k * 3, palTarget, k * 3, e, palNow, k * 3);
  // pad colours: the palette stops on a diagonal, so neighbouring pads differ; the top row a little lighter
  for (let i = 0; i < 12; i++) {
    const c = i % 4, r = (i / 4) | 0;
    const s = ((c + r) % 4) * 3;
    const lift = 1.12 - 0.08 * r;
    padCol[i * 3] = palNow[s] * lift; padCol[i * 3 + 1] = palNow[s + 1] * lift; padCol[i * 3 + 2] = palNow[s + 2] * lift;
  }
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
  stripSet(S, 12, 1, hit.pulse, hit.kick, hit.snare, hit.hat);
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
  stripSet(S, 9, 2, n, 0, 0, 0);
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
  gl.uniform1f(u.u_pulse, clamp(pulseEnv * react, 0, 1.5));
  gl.uniform1f(u.u_beat, Math.max(beat.pulse, 0.8 * hit.pulse));
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
      put4(U.waveB, w * 4, 4 + 16 * f.vel, f.vel, 0, 0);
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
  // the overlay's trails fade by time, not by frame: the same streak at 30 and at 144 frames a second
  gl.uniform1f(u.u_keep, Math.exp(-frameDt / (0.03 + 0.17 * T.trails)));
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

function composite(nowMs, nowS, mixAB, mixedTex = null, target = null) {
  const gl = G.gl;
  const A = sets[deck.a], B = sets[deck.b];
  gl.bindFramebuffer(gl.FRAMEBUFFER, target);   // the stage's look target, or the screen
  gl.viewport(0, 0, G.width, G.height);
  gl.useProgram(G.compProg);
  // a transition in flight (vj-stage.js) arrives already mixed as u_a, with u_mix 0
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, mixedTex || (A && A.fb ? A.fb.texs[A.fb.read] : G.blackTex));
  gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, B && B.fb && mixAB > 0.001 && !mixedTex ? B.fb.texs[B.fb.read] : G.blackTex);
  gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, G.ov.texs[G.ov.read]);
  gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, G.frz ? G.frz.texs[0] : G.blackTex);
  const u = G.compU;
  gl.uniform2f(u.u_res, G.width, G.height);
  gl.uniform1f(u.u_mix, A && A.fb && !mixedTex ? mixAB : 0);
  const k = fx.strongest("kaleido");
  gl.uniform1f(u.u_kal, k ? k.env : 0);
  gl.uniform1f(u.u_kalN, k ? 2 * Math.round(2 + 4 * k.vel) : 6);
  gl.uniform1f(u.u_kalRot, k ? (nowS - k.t0) * (0.15 + 0.5 * k.vel) : 0);
  const g = fx.strongest("glitch");
  gl.uniform1f(u.u_glitch, g ? g.env * (0.35 + 0.65 * g.vel) : 0);
  gl.uniform1f(u.u_glitchT, Math.floor(nowS * 14) % 997);
  gl.uniform1f(u.u_glitchCells, g ? 6 + 18 * (1 - g.vel) : 12);
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
  gl.uniform1f(u.u_bright, T.bright * kill.gain);
  gl.uniform1f(u.u_sat, 0.15 + 1.0 * T.sat);
  gl.uniform1f(u.u_accent, 0.25 + 1.0 * T.accent);
  gl.uniform1f(u.u_metro, Math.min(0.03, T.metro * 0.03 * beat.pulse));   // linear light: a few percent at most
  gl.uniform3f(u.u_metroCol, palNow[0], palNow[1], palNow[2]);
  gl.uniform1f(u.u_bloom, Math.min(0.06, hit.bloom * 0.07 * T.accent));
  gl.uniform3f(u.u_bloomCol, palNow[9], palNow[10], palNow[11]);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
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
  for (let i = 0; i < 12; i++) {
    const action = padMap[i];
    let r = 0, g = 0, b = 0, v = 0;
    if (EFFECTS[action]) {
      r = padCol[i * 3]; g = padCol[i * 3 + 1]; b = padCol[i * 3 + 2];
      v = 0.10 + 0.9 * Math.max(padEnvScratch[i] / Math.max(T.accent, 0.05), padHeld[i] ? 0.6 : 0);
    } else if (CONTROL_RGB[action]) {
      [r, g, b] = CONTROL_RGB[action];
      v = 0.10 + 0.9 * padPress[i];
      if (action === "kill") v = kill.target < 0.5 ? 1 : kill.pending !== null ? (beat.pulse > 0.5 ? 1 : 0.4) : 0.12;
      if (action === "next" && deck.running) v = 0.9;
      if (action === "none") v = 0;
    }
    v = Math.min(v, 1);
    out[i] = rgbToHex(r * v, g * v, b * v);
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
  updateMusic(nowMs, nowS, dt);
  fx.update(nowS);
  updateKill(nowMs, dt);
  updatePalette();
  // the strobe's full-frame pulses: asked for at the strobe rate, granted at most three times a second
  const st = fx.strongest("strobe");
  if (st && st.env > 0.05 && nowS >= strobeNext) {
    const rate = Math.min(2 + 10 * T.strobeRate, 3);
    requestFlash(nowS, (0.22 + 0.33 * st.vel) * T.accent, 0.06);
    strobeNext = nowS + 1 / rate;
  }
  if (deck.running && nowMs - deck.start >= deck.ms) finishFade();
  buildStrip(nowMs, nowS);
  buildAudio(nowS);
  padLights(nowMs, dt);
  persistValues(nowMs);
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
      const mixed = stage && A && A.fb && B && B.fb && B !== A ?
        stage.mix(deck, A.fb.texs[A.fb.read], B.fb.texs[B.fb.read], G.width, G.height, nowMs, nowS) : null;
      const target = stage ? stage.compositeTarget(G.width, G.height) : null;
      composite(nowMs, nowS, mixAB, mixed, target);
      if (target) stage.post(G.width, G.height);
      if (probe.on || probe.waiters.length) runProbe(nowMs);
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
let frameDt = 1 / 60;

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
    if (demo) eng += " · demo playing on top";
  } else eng = `connecting to ${engine.url}… (keyboard pads work meanwhile)`;
  if (engine.link.status) eng += ` · ${engine.link.status}`;    // cleared on disconnect: never a dead engine's last word
  setText("hud-engine", eng);
  const bpm = beat.bpm > 0 && beat.alive(nowMs) ? `${beat.bpm.toFixed(1)} bpm · conf ${beat.conf.toFixed(2)}` : "no beat";
  setText("hud-beat", bpm + (beat.onBeat !== null && beat.alive(nowMs) ? ` · on-beat ${beat.onBeat.toFixed(2)}` : "") + ` · #${beat.count}`);
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
  for (const f of fx.fx) if (f.active) parts.push(`${f.type}${f.tr === null && EFFECTS[f.type].hold ? "●" : ""} ${f.env.toFixed(2)}`);
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
    const label = actionLabel(padMap[i]);
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
      safeSet(STORE.pads, JSON.stringify(padMap));
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
  $("btn-reset-pads").addEventListener("click", () => { padMap = DEFAULT_PAD_MAP.slice(); safeSet(STORE.pads, JSON.stringify(padMap)); renderPadMap(); });
  $("btn-reset-ctl").addEventListener("click", () => { ctlMap = { ...DEFAULT_CTL_MAP }; safeSet(STORE.ctl, JSON.stringify(ctlMap)); renderTargets(); });
  const hits = $("opt-hits"), leds = $("opt-leds");
  hits.checked = options.hits; leds.checked = options.leds;
  const saveOpts = () => { options.hits = hits.checked; options.leds = leds.checked; safeSet(STORE.opts, JSON.stringify(options)); };
  hits.addEventListener("change", saveOpts);
  leds.addEventListener("change", saveOpts);
  const typing = (el) => el && (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA") && el.type !== "range";
  window.addEventListener("keydown", (e) => {
    if (typing(e.target) || e.ctrlKey || e.metaKey || e.altKey) return;
    const pad = KEY_PADS[e.code];
    if (pad) {
      e.preventDefault();
      if (!e.repeat && !keyPadDown[pad]) { keyPadDown[pad] = 1; padOn(pad, e.shiftKey ? 1.0 : 0.6, "key"); }
      return;
    }
    if (e.repeat) return;
    const nowS = performance.now() / 1000;
    switch (e.code) {
      case "KeyQ": fx.dampen(nowS); break;
      case "KeyW": choke(); break;
      case "KeyE": toggleKill(); break;
      case "KeyR": nextSet(); break;
      case "KeyH": hudVisible = !hudVisible; $("hud").classList.toggle("hidden", !hudVisible); break;
      case "KeyF": toggleFullscreen(); break;
      case "KeyM": togglePanel(); break;
      case "KeyD": setDemo(!demo); break;
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
    G.pool = []; G.ov = null; G.frz = null;
    if (initGL()) for (const s of sets) if (s.source) compileSet(s);
  });
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
    safeSet(STORE.ctl, JSON.stringify(ctlMap));
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
  }),
  errors: () => errors.slice(),
  event: (obj) => handleEvent(obj),
  press: (pad, vel = 0.8) => padOn(pad, vel, "test"),
  release: (pad) => padOff(pad),
  learn: (target) => { learnTarget = target; },
  probe: (on) => { probe.on = !!on; if (on) probe.trace = []; return probe.on; },
  trace: () => probe.trace.slice(),
  luma: () => new Promise((resolve) => probe.waiters.push(resolve)),
  demo: (on) => { setDemo(!!on); return !!demo; },
};

// ------------------------------------------------------------------------------------------------------ boot --
async function boot() {
  if (location.protocol === "file:") {   // modules and presets need a server; and never a GPU page from a file pane
    banner("Open the VJ rig through a server: py -m arsenal serve, then http://127.0.0.1:8793/web/vj.html");
    return;
  }
  loadStored();
  wireUi();
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
    if (validSet(opener)) selectSet(opener);
  }
  renderSetList();
  renderParams();
  window.__vj.ready = true;
  toast(sets[deck.a] ? sets[deck.a].name : "no sets");
  stage.boot();
}
boot();
