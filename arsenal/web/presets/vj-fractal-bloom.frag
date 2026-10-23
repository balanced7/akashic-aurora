#version 300 es
//! {"id": "vj-fractal-bloom", "name": "VJ Fractal Bloom", "author": "Vandor", "tags": ["vj", "generative", "beat", "chord", "pads", "fractal"], "params": [{"k": 1, "name": "petals", "default": 0.5}, {"k": 2, "name": "depth", "default": 0.55}, {"k": 3, "name": "twist", "default": 0.45}, {"k": 4, "name": "glow", "default": 0.55}, {"k": 5, "name": "trails", "default": 0.25}, {"k": 6, "name": "unfold", "default": 0.7}]}
precision highp float;

// Fractal Bloom (arsenal/web/vj.html, Play-loadable). A kaleidoscopic iterated function system: the plane is folded into
// mirrored petals, then folded, turned and scaled again and again; orbit traps (rings and lines met along the way) draw the
// flower, each pixel lit by the single trap it passes nearest, so the levels cross as clean lines. It unfolds with the beat: every beat adds one level of folding, eased in with a little overshoot, over four beats,
// and the next four fold it back again (an eight-beat breath), so the flower blooms and closes in time. The chord's palette
// colours the levels, the root sets the petals' turn, a chord change twists the whole bloom and lets it settle; the kick
// breathes the zoom, the bass feeds the glow, and each pad twists its own level of the fractal and tints it in its colour.

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

// ------------------------------------------------------------- the VJ strip (arsenal/web/vj-core.js STRIP, v1) --
bool gHost;
vec3 gPal[4];
float gPhase, gPulse, gCount, gTension, gChordPulse, gKick, gRoot;

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
    gTension = vjAt(14, 0).z;
    vec4 ch = vjAt(15, 0);
    gChordPulse = ch.x; gRoot = ch.y;
    vec4 hit = vjAt(12, 1);
    gKick = max(hit.y, max(0.6 * hit.x, 0.7 * gPulse));
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.95); gPal[1] = hueLinear(h + 0.70); gPal[2] = hueLinear(h + 0.50); gPal[3] = hueLinear(h + 0.12);
    gPhase = fract(u_time * 2.0); gPulse = u_beat;
    gCount = mod(floor(u_time * 2.0), 64.0);
    gTension = 0.0;
    gChordPulse = 0.0; gRoot = -1.0;
    gKick = max(u_beat, 0.7 * u_flux);
  }
}

vec3 padColour(int i) { return gHost ? vjAt(i, 3).rgb : gPal[i - 4 * (i / 4)]; }

vec2 padLevel(int i) {          // (envelope, velocity)
  if (gHost) return vjAt(i, 0).xy;
  float band = i < 4 ? u_high : (i < 8 ? u_mid : u_bass);
  float gate = smoothstep(0.6, 0.98, 0.5 + 0.5 * sin(u_time * 0.7 + float(i) * 2.4));
  return vec2(smoothstep(0.55, 0.9, band) * gate, band);
}

// ------------------------------------------------------------------------------------------------- light parts --
vec3 hotCore(vec3 tint, float heat) {      // light-glow glowHotCore
  float h = max(heat, 0.0);
  vec3 hue = max(tint, vec3(0.0));
  float peak = max(hue.r, max(hue.g, hue.b));
  return h * mix(hue, vec3(peak), h * h / (1.0 + h * h));
}
mat2 rot(float a) { float c = cos(a), s = sin(a); return mat2(c, s, -s, c); }
// an eased step with a little overshoot: 0 at x = 0, 1 from x = 1 on, peaking near 1.08
float springStep(float x) {
  float k = clamp(x, 0.0, 1.0);
  return 1.0 + 1.6 * pow(k - 1.0, 3.0) + 0.6 * pow(k - 1.0, 2.0);
}

void main() {
  vjLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float t = u_time;
  float bass = clamp(0.65 * u_bass + 0.35 * u_pulse, 0.0, 1.5);

  // the breath: up one level a beat for four beats, down for four (an eased triangle over eight beats)
  float c8 = mod(gCount, 8.0);
  float stepIn = springStep(gPhase * 1.6);           // over most of the beat, so the light never jumps
  float lvl = c8 < 4.0 ? c8 + stepIn : 8.0 - c8 - stepIn;     // 0..4, continuous across the turn
  float depth = 2.0 + 2.0 * u_k2 + lvl * (0.35 + 0.65 * u_k6);  // levels of folding: up to about 8
  float rootTurn = gRoot >= 0.0 ? mod(gRoot * 7.0, 12.0) / 12.0 * TAU / 6.0 : 0.0;
  float twistAll = 0.35 * gChordPulse + 0.15 * gTension * sin(t * 3.0);

  // the plane: zoom breathes with the kick, the whole flower turns slowly
  float zoom = 1.25 - 0.08 * gKick - 0.05 * bass;
  vec2 z = rot(t * 0.03 + rootTurn + twistAll) * p * zoom;
  float r = length(z);
  // petals: fold the angle into mirrored sectors
  float n = 2.0 * floor(3.0 + 3.0 * u_k1 + 0.5);                // 6..12 sectors
  float seg = TAU / n;
  float a = mod(atan(z.y, z.x + 1e-9), seg);
  a = abs(a - 0.5 * seg);
  z = r * vec2(cos(a), sin(a));

  float scale = 1.0;
  vec2 off = vec2(0.42 + 0.06 * sin(t * 0.11), 0.21 + 0.05 * cos(t * 0.13));
  float S = 1.55 + 0.1 * sin(t * 0.07);
  float baseTurn = (0.25 + 0.6 * u_k3) + 0.15 * sin(t * 0.05);
  // orbit traps, nearest wins: each pixel takes the one trap (ring or axis, at whichever level) it lies closest to, so
  // the levels' curves cross as clean lines instead of piling up into haze
  float trapMin = 1e9, trapW = 0.0, trapLvl = 0.0, trapAxis = 0.0;
  for (int i = 0; i < 8; i++) {
    float fi = float(i);
    float w = clamp(depth - fi, 0.0, 1.0);                   // the level's presence: the last one fades in
    if (w <= 0.0) break;
    // this level's pads twist it
    vec2 lv = padLevel(i);
    vec2 lv2 = padLevel(i + 8 > 11 ? i - 4 : i + 8);
    float padTw = lv.x * lv.y * 0.8 + lv2.x * lv2.y * 0.5;
    z = abs(z) - off;
    z = rot(baseTurn + 0.13 * fi + padTw) * z;
    z *= S;
    scale *= S;
    float ringR = 0.55 + 0.1 * sin(t * 0.3 + fi);
    float dRing = abs(length(z) - ringR) / scale;
    float dAxis = abs(z.y) / scale * 1.3;
    float d = min(dRing, dAxis);
    if (d < trapMin) { trapMin = d; trapW = w; trapLvl = fi; trapAxis = dAxis < dRing ? 1.0 : 0.0; }
  }
  int li = int(trapLvl);
  vec3 tint = mix(gPal[li - 4 * (li / 4)], gPal[(li + 1) - 4 * ((li + 1) / 4)], 0.5 + 0.5 * sin(t * 0.2 + trapLvl));
  vec2 lvT = padLevel(li);
  tint = mix(tint, padColour(li), clamp(lvT.x, 0.0, 1.0));
  float lw = (0.8 + 0.25 * trapLvl) * px;
  float line = exp(-trapMin / lw);
  float halo = exp(-trapMin / (lw * 9.0));
  float e = trapW * (1.0 - 0.35 * trapAxis);
  // the background: dark, with the bloom's own light pooling in the middle
  vec3 col = mix(gPal[1], gPal[0], 0.5) * 0.010 * exp(-length(p) * 3.0) * (1.0 + 1.5 * bass);
  float norm = 1.6 / (1.0 + 0.3 * depth);             // more levels, more lines: each one dimmer, the frame as bright
  col += hotCore(tint, 0.9 + 0.2 * gKick + 0.4 * trapLvl / 7.0) * line * e * 0.9 * norm;
  col += tint * halo * e * (0.04 + 0.10 * u_k4) * (0.7 + 0.4 * bass) * norm;
  // the centre breathes with the kick
  col += mix(gPal[0], vec3(1.0), 0.5) * (0.015 + 0.03 * gKick) * exp(-length(p) * 10.0) * u_k4;
  // a soft falloff to the edge so the bloom sits in the middle of the frame
  col *= smoothstep(0.98, 0.30, length(p));

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.1);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  // trails: last frame turned a hair and pulled in, so the bloom leaves a swirl as it folds
  vec2 back = rot(-0.004 - 0.01 * bass) * p * (1.0 + 0.004 + 0.01 * gKick);
  vec3 prev = texture(u_prev, back / vec2(asp, 1.0) + 0.5).rgb;
  vec3 trail = max(prev * (0.3 + 0.6 * u_k5) - 2.0 / 255.0, 0.0);
  outColor = vec4(clamp(max(col, trail), 0.0, 1.0), 1.0);
}
