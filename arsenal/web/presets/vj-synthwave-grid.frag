#version 300 es
//! {"id": "vj-synthwave-grid", "name": "VJ Synthwave Grid", "author": "Vandor", "tags": ["vj", "generative", "beat", "chord", "keys", "pads"], "params": [{"k": 1, "name": "drive", "default": 0.5}, {"k": 2, "name": "grid glow", "default": 0.6}, {"k": 3, "name": "sun", "default": 0.6}, {"k": 4, "name": "mountains", "default": 0.55}, {"k": 5, "name": "trails", "default": 0.2}, {"k": 6, "name": "lasers", "default": 0.7}]}
precision highp float;

// Synthwave Grid (arsenal/web/vj.html, Play-loadable). The outrun postcard, played: a sun with its slatted lower half sits
// on the horizon behind two ranges of wireframe mountains, and a neon grid floor runs toward you. The chord sets the sky:
// the palette (which the page recolours on every chord change) paints the gradient from zenith to horizon and the sun's
// two ends. Every beat the grid lurches one quarter of a tile forward with an eased step (64 beats make 16 whole tiles,
// so the 64-beat counter wrapping never shows); the kick thickens the lines and lifts the horizon glow. Keys light floor
// tiles in their pitch colour, the column chosen by the pitch class. The pads fire laser fans from the vanishing point, one
// fan per pad, spread across the sky from left to right; velocity sets the number of beams and their width. Any pad
// hit (the strip's shared hit input, 2026-10-24) pulses the horizon: the line blazes and lifts, the sun swells, and a
// band of light rolls down the floor from the horizon toward you.

uniform sampler2D u_video;   // the VJ page: its 16x6 VJ strip (u_has_video stays 0); Play: the video or a 1x1 black texture
uniform sampler2D u_prev;
uniform vec2  u_res;
uniform float u_time;
uniform float u_has_video;
uniform float u_pulse, u_beat, u_level, u_bass, u_mid, u_high, u_flux;
uniform float u_hue;
uniform float u_intensity;
uniform float u_k1, u_k2, u_k3, u_k4, u_k5, u_k6;

in vec2 v_uv;
out vec4 outColor;

const float PI = 3.14159265358979;
const float TAU = 6.28318530717959;

// The house pitch colours (arsenal/web/vj-core.js pitchColours, the piano's palette; tests/vj_core.test.mjs pins these)
const vec3 PC_COL[12] = vec3[12](
  vec3(0.0199, 0.5610, 0.6101), vec3(1.0108, 0.2104, 0.0136), vec3(0.0398, 0.2848, 1.3564), vec3(0.5096, 0.5152, 0.0170),
  vec3(0.9080, 0.0617, 1.2415), vec3(0.0201, 0.5962, 0.3555), vec3(1.2716, 0.0623, 0.1166), vec3(0.0171, 0.4642, 0.8374),
  vec3(0.7316, 0.3596, 0.0150), vec3(0.3590, 0.1178, 1.6413), vec3(0.0682, 0.6072, 0.0156), vec3(1.2075, 0.0548, 0.5141));

// ------------------------------------------------------------- the VJ strip (arsenal/web/vj-core.js STRIP, v1) --
bool gHost;
vec3 gPal[4];
float gPhase, gPulse, gCount, gChordPulse, gKick;

vec4 vjAt(int x, int y) { return texelFetch(u_video, ivec2(x, y), 0); }

vec3 hueLinear(float turns) {
  vec3 c = clamp(abs(fract(turns + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0, 0.0, 1.0);
  return c * c;
}

void vjLoad() {
  gHost = u_has_video < 0.5 && textureSize(u_video, 0) == ivec2(16, 6);
  if (gHost) {
    for (int i = 0; i < 4; i++) gPal[i] = vjAt(i, 2).rgb;
    vec4 beat = vjAt(12, 0);
    gPhase = beat.x; gPulse = beat.y; gCount = beat.w;
    gChordPulse = vjAt(15, 0).x;
    vec4 hit = vjAt(12, 1);
    gKick = max(hit.y, max(0.6 * hit.x, 0.7 * gPulse));
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.88); gPal[1] = hueLinear(h + 0.75); gPal[2] = hueLinear(h + 0.52); gPal[3] = hueLinear(h + 0.10);
    gPhase = fract(u_time * 2.0); gPulse = u_beat;
    gCount = mod(floor(u_time * 2.0), 64.0);
    gChordPulse = 0.0;
    gKick = max(u_beat, 0.7 * u_flux);
  }
}

vec3 padColour(int i) { return gHost ? vjAt(i, 3).rgb : gPal[i - 4 * (i / 4)]; }

// the shared hit input (STRIP v2, row 2: vj-core.js): the latest pad hit's pulse (through the velocity curve), its velocity,
// its effect code and age, where it struck; the kick / snare / hat envelopes. 0 in Play and on a v1 host.
float gHit, gHitVel, gHitCode, gHitAge, gSnare, gHat;
vec2 gHitAt;
void hitLoad() {
  if (gHost && vjAt(15, 2).x >= 2.0) {
    vec4 h = vjAt(10, 2);
    gHit = h.x; gHitVel = h.y; gHitCode = h.z; gHitAge = h.w;
    vec4 b = vjAt(11, 2);
    gSnare = b.y; gHat = b.z;
    gHitAt = vjAt(12, 2).yz;
  } else {
    gHit = 0.0; gHitVel = 0.0; gHitCode = 0.0; gHitAge = 30.0; gSnare = 0.0; gHat = 0.0; gHitAt = vec2(0.0);
  }
}


vec2 padLevel(int i) {          // (envelope, velocity)
  if (gHost) return vjAt(i, 0).xy;
  float band = i < 4 ? u_high : (i < 8 ? u_mid : u_bass);
  float gate = smoothstep(0.6, 0.98, 0.5 + 0.5 * sin(u_time * 0.7 + float(i) * 2.4));
  return vec2(smoothstep(0.55, 0.9, band) * gate, band);
}

float pcStrike(int pc) {
  if (gHost) return max(vjAt(pc, 1).y, 0.6 * vjAt(pc, 1).x);
  return step(0.82, fract(sin(floor(u_time * 4.0) * 91.7 + float(pc) * 17.3) * 43758.5)) * u_mid;
}

// ------------------------------------------------------------------------------------------------- light parts --
float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
float vnoise1(float x) {
  float i = floor(x), f = fract(x);
  float u = f * f * (3.0 - 2.0 * f);
  return mix(hash12(vec2(i, 0.5)), hash12(vec2(i + 1.0, 0.5)), u);
}
vec3 hotCore(vec3 tint, float heat) {      // light-glow glowHotCore
  float h = max(heat, 0.0);
  vec3 hue = max(tint, vec3(0.0));
  float peak = max(hue.r, max(hue.g, hue.b));
  return h * mix(hue, vec3(peak), h * h / (1.0 + h * h));
}
float lorentz(float dPx, float haloPx) { float x = dPx / max(haloPx, 1e-3); return 0.0625 / (0.0625 + x * x); }
// a mountain ridge: the height of range `seed` at x (fBm of value noise, three octaves)
float ridge(float x, float seed) {
  float h = 0.0, amp = 0.5, f = 1.0;
  for (int o = 0; o < 3; o++) {
    h += amp * vnoise1(x * f + seed);
    f *= 2.13; amp *= 0.5;
  }
  return h;
}

void main() {
  vjLoad();
  hitLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float rs = max(u_res.y / 1080.0, 0.35);
  float t = u_time;
  float bass = clamp(0.65 * u_bass + 0.35 * u_pulse, 0.0, 1.5);
  float yh = -0.06 + 0.004 * gKick + 0.012 * gHit;        // the horizon (a hit lifts it)

  // ------------------------------------------------------------------------------------------------ the sky --
  float up = clamp((p.y - yh) / (0.5 - yh), 0.0, 1.0);
  // three stops: a deep zenith in the second palette colour, its body, and a warm horizon toward the accent colour
  vec3 zenith = mix(gPal[1], vec3(0.03, 0.0, 0.08), 0.5) * 0.03;
  vec3 mid = gPal[1] * 0.10;
  vec3 low = mix(gPal[1], gPal[3], 0.6) * 0.42;
  vec3 col = up < 0.35 ? mix(low, mid, smoothstep(0.0, 0.35, up)) : mix(mid, zenith, smoothstep(0.35, 1.0, up));
  col *= 1.0 + 0.8 * gChordPulse;
  // stars: a sparse field, twinkling, fading toward the horizon glow
  vec2 sc = floor(p * 90.0);
  float sh = hash12(sc);
  if (p.y > yh && sh > 0.965) {
    vec2 sp = (sc + 0.5 + 0.5 * (vec2(hash12(sc + 3.1), hash12(sc + 7.7)) - 0.5)) / 90.0;
    float d = length(p - sp) / px;
    col += vec3(0.8, 0.85, 1.0) * exp(-d * d / (1.6 * rs * rs)) * (sh - 0.965) * 22.0 * (0.6 + 0.4 * sin(t * (1.0 + 3.0 * sh) + sh * 40.0)) * up;
  }

  // ------------------------------------------------------------------------------------------------ the sun --
  vec2 sunC = vec2(0.0, yh + 0.13 + 0.06 * u_k3);
  float sunR = (0.12 + 0.10 * u_k3) * (1.0 + 0.025 * gKick + 0.02 * bass + 0.07 * gHit);
  float sd = length(p - sunC);
  float sv = clamp((p.y - (sunC.y - sunR)) / (2.0 * sunR), 0.0, 1.0);   // 0 at the sun's foot, 1 at its crown
  vec3 sunCol = mix(gPal[1] * 1.3, mix(gPal[3], vec3(1.0, 0.85, 0.35), 0.55) * 1.6, sv);
  // the slats: bands across the lower half that thicken toward the horizon and drift down
  float slat = 1.0;
  if (sv < 0.55) {
    float y = (0.55 - sv) / 0.55;                        // 0 at the sun's middle, 1 at its foot
    float bands = fract(y * 5.0 + t * 0.35);
    float gap = 0.08 + 0.55 * y;
    slat = smoothstep(gap - 0.03, gap + 0.03, bands);
  }
  float disc = 1.0 - smoothstep(sunR - 1.5 * px, sunR + 1.5 * px, sd);
  col = mix(col, sunCol * (0.55 + 0.45 * u_k3), disc * slat * step(yh, p.y));
  col += sunCol * 0.10 * exp(-max(sd - sunR, 0.0) * 9.0) * (0.6 + 0.6 * u_k3) * step(yh, p.y);

  // --------------------------------------------------------------------------------------- the mountains --
  for (int m = 0; m < 2; m++) {
    float fm = float(m);
    float scale = fm == 0.0 ? 3.0 : 5.5;
    float hgt = (fm == 0.0 ? 0.20 : 0.11) * (0.45 + 0.9 * u_k4);
    float x = p.x * scale + fm * 13.7 + t * (fm == 0.0 ? 0.004 : 0.009);
    // keep the middle low so the sun shows: the ridges rise toward the sides
    float side = smoothstep(0.05, 0.75, abs(p.x) / max(asp * 0.5, 1e-3));
    float top = yh + hgt * ridge(x, fm * 5.0) * (0.25 + 0.75 * side);
    // the wireframe: contour lines up the slope (derivatives taken outside any branch) and a glowing crest
    float hy = (p.y - yh) / max(top - yh, 1e-4);
    float lines = abs(fract(hy * 5.0 - fm * 0.5) - 0.5) / max(fwidth(hy * 5.0), 1e-4);
    if (p.y > yh && p.y < top) {
      vec3 rock = mix(vec3(0.004, 0.002, 0.012), gPal[1] * 0.012, fm);
      vec3 wire = mix(gPal[2], gPal[1], fm) * (0.05 + 0.10 * u_k2) * (1.0 - smoothstep(0.0, 1.4, lines)) * hy;
      col = rock + wire;
    }
    float crestD = abs(p.y - top) / px;
    col += mix(gPal[2], gPal[3], 0.3 * fm) * (exp(-crestD * crestD / (1.2 * rs * rs)) * 0.55 + lorentz(crestD, 5.0 * rs) * 0.12) *
           (0.4 + 0.6 * u_k4) * step(yh, p.y) * (fm == 0.0 ? 1.0 : 0.6);
  }

  // ----------------------------------------------------------------------------------------- the floor grid --
  // the floor's coordinates and their derivatives, for every pixel (fwidth must not sit inside a branch)
  float below = max(yh - p.y, 2e-3);
  float z = 0.12 / below;                                // depth of the floor under this pixel
  float lurch = 0.25 * (gCount + smoothstep(0.0, 0.35, gPhase));   // 64 beats = 16 whole tiles
  float travel = t * (0.25 + 1.2 * u_k1) + lurch;
  vec2 g = vec2(p.x * z * 11.0, z * 1.6 + travel);
  vec2 fw = max(fwidth(g), vec2(1e-4));
  if (p.y < yh) {
    vec2 gd = abs(fract(g + 0.5) - 0.5) / fw;
    // the kick thickens and heats the floor (2026-10-24 safety pass: half the response it had; with the fast kick envelope
    // of the impact pass the floor alone flashed a quarter of the screen 2.5 times a second under the demo's music)
    float thick = 0.9 + 0.7 * gKick;
    float line = max(1.0 - smoothstep(0.0, thick, gd.x), 1.0 - smoothstep(0.0, thick, gd.y));
    float glowL = max(exp(-gd.x * 0.25), exp(-gd.y * 0.25)) * 0.25;
    float fog = exp(-z * 0.075);
    vec3 gridCol = mix(gPal[0], gPal[1], smoothstep(0.0, 0.6, abs(p.x) / asp));
    col = vec3(0.002, 0.0015, 0.006) + gPal[1] * 0.02 * exp(-below * 6.0);
    col += hotCore(gridCol, 0.7 + 0.4 * gKick) * (line + glowL) * fog * (0.25 + 0.75 * u_k2);
    // keys light floor tiles: the tile's column picks a pitch class, the row band rolls with the floor
    vec2 tile = floor(g);
    int pc = int(mod(tile.x + 6.0, 12.0));
    float tileOn = step(0.55, hash12(tile + vec2(0.0, floor(gCount / 4.0)))) * pcStrike(pc);
    vec2 tf = abs(fract(g) - 0.5);
    float inside = 1.0 - smoothstep(0.38, 0.47, max(tf.x, tf.y));
    col += PC_COL[pc] * tileOn * inside * fog * 0.22;
    // the sun's reflection: a shimmering column down the floor
    float shimmer = 0.6 + 0.4 * sin(z * 40.0 - t * 6.0 + p.x * 30.0);
    col += sunCol * 0.06 * exp(-abs(p.x) / (sunR * 0.6)) * exp(-below * 5.0) * shimmer * (0.5 + 0.5 * u_k3);
    // a pad hit rolls a band of light from the horizon toward you (depth 20 to 0.3 in about 0.4 s)
    float zb = 20.0 * exp(-gHitAge * 10.0) + 0.25;
    col += hotCore(mix(gPal[3], gPal[0], 0.4), 1.3) * gHit * (0.5 + 0.5 * gHitVel) * exp(-pow((z - zb) / (0.18 * zb), 2.0)) * 0.6;
    // the bass rolls a band of light down the floor
    col += gPal[2] * 0.05 * bass * exp(-pow(fract(z * 0.08 - t * 0.5) - 0.5, 2.0) * 60.0) * fog;
  }
  // the horizon line, lifted by the kick and by chord changes
  float hd = abs(p.y - yh) / px;
  col += mix(gPal[0], vec3(1.0, 0.8, 0.9), 0.3) * (exp(-hd * hd / (2.0 * rs * rs)) * 0.5 + lorentz(hd, 14.0 * rs) * 0.15) *
         (0.5 + 0.8 * gKick + 0.8 * gChordPulse + 1.8 * gHit);

  // --------------------------------------------------------------------- the pads: laser fans from the horizon --
  vec2 vp = vec2(0.0, yh);
  vec2 dv = p - vp;
  float dl = length(dv);
  float ang = atan(dv.y, dv.x);
  for (int i = 0; i < 12; i++) {
    vec2 lv = padLevel(i);
    if (lv.x < 0.002) continue;
    float fi = float(i);
    float aim = PI * (0.93 - 0.86 * fi / 11.0) + 0.12 * sin(t * 1.7 + fi);   // pad 1 far left, pad 12 far right
    float beams = 2.0 + floor(4.0 * lv.y + 0.5);
    float spread = 0.10 + 0.35 * lv.y;
    float stepA = spread / max(beams - 1.0, 1.0);
    float idx = clamp(floor((ang - aim) / max(stepA, 1e-4) + 0.5 * (beams - 1.0) + 0.5), 0.0, beams - 1.0);
    float off = ang - (aim + (idx - 0.5 * (beams - 1.0)) * stepA);
    float dPx = abs(dl * sin(off)) / px;
    float along = dl * cos(off);
    if (along < 0.0) continue;
    float w = (0.8 + 2.2 * lv.y) * rs;
    vec3 tint = padColour(i);
    float e = lv.x * u_k6 * exp(-along * 0.8);
    col += (hotCore(tint, 1.4) * exp(-dPx * dPx / (w * w)) + tint * 0.35 * lorentz(dPx, 9.0 * rs)) * e;
  }

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.25);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  vec3 prev = texture(u_prev, v_uv).rgb;
  vec3 trail = max(prev * (0.2 + 0.6 * u_k5) - 2.0 / 255.0, 0.0);
  outColor = vec4(clamp(max(col, trail), 0.0, 1.0), 1.0);
}
