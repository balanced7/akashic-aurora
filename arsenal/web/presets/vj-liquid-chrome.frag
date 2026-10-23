#version 300 es
//! {"id": "vj-liquid-chrome", "name": "VJ Liquid Chrome", "author": "Vandor", "tags": ["vj", "generative", "bass", "chord", "keys", "pads"], "params": [{"k": 1, "name": "mass", "default": 0.55}, {"k": 2, "name": "flow", "default": 0.45}, {"k": 3, "name": "mirror", "default": 0.6}, {"k": 4, "name": "drops", "default": 0.65}, {"k": 5, "name": "trails", "default": 0.15}, {"k": 6, "name": "tint", "default": 0.45}]}
precision highp float;

// Liquid Chrome (arsenal/web/vj.html, Play-loadable). Seven blobs of mercury drift on slow Lissajous paths and merge where
// their fields overlap (metaballs: F = sum r^2 / d^2, the surface where F = 1). The surface is read as a height field whose
// slope is the field's own gradient, summed in the same loop, so every pixel knows its normal without a second pass, and
// it is shaded as a mirror of a studio -- a bright ceiling with a key light, coloured softboxes either side, a thin
// horizon over a dark floor -- so the tops carry the soft light and the rims, which face sideways, catch the strips, the
// horizon line and the dark. The chord's palette paints the strips. Bass swells every blob; the kick bumps them; the snare runs a
// ripple over the skin. Keys drop small beads in their pitch colour on the circle of fifths, the pads throw drops in from
// the rim at their clock positions, sized by velocity, and those merge into the mass like everything else.

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

const vec3 PC_COL[12] = vec3[12](
  vec3(0.0199, 0.5610, 0.6101), vec3(1.0108, 0.2104, 0.0136), vec3(0.0398, 0.2848, 1.3564), vec3(0.5096, 0.5152, 0.0170),
  vec3(0.9080, 0.0617, 1.2415), vec3(0.0201, 0.5962, 0.3555), vec3(1.2716, 0.0623, 0.1166), vec3(0.0171, 0.4642, 0.8374),
  vec3(0.7316, 0.3596, 0.0150), vec3(0.3590, 0.1178, 1.6413), vec3(0.0682, 0.6072, 0.0156), vec3(1.2075, 0.0548, 0.5141));

// ------------------------------------------------------------- the VJ strip (arsenal/web/vj-core.js STRIP, v1) --
bool gHost;
vec3 gPal[4];
float gPulse, gChordPulse, gKick, gSnare;

vec4 vjAt(int x, int y) { return texelFetch(u_video, ivec2(x, y), 0); }

vec3 hueLinear(float turns) {
  vec3 c = clamp(abs(fract(turns + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0, 0.0, 1.0);
  return c * c;
}

void vjLoad() {
  gHost = u_has_video < 0.5 && textureSize(u_video, 0) == ivec2(16, 6);
  if (gHost) {
    for (int i = 0; i < 4; i++) gPal[i] = vjAt(i, 2).rgb;
    gPulse = vjAt(12, 0).y;
    gChordPulse = vjAt(15, 0).x;
    vec4 hit = vjAt(12, 1);
    gKick = max(hit.y, max(0.6 * hit.x, 0.7 * gPulse));
    gSnare = hit.z;
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.55); gPal[1] = hueLinear(h + 0.85); gPal[2] = hueLinear(h + 0.62); gPal[3] = hueLinear(h + 0.08);
    gPulse = u_beat;
    gChordPulse = 0.0;
    gKick = max(u_beat, 0.7 * u_flux);
    gSnare = u_high * u_flux;
  }
}

vec3 padColour(int i) { return gHost ? vjAt(i, 3).rgb : gPal[i - 4 * (i / 4)]; }

vec3 padLevel(int i) {          // (envelope, velocity, seconds since press)
  if (gHost) return vjAt(i, 0).xyz;
  float slot = floor(u_time / 2.5 + float(i) * 0.37);
  float age = u_time - (slot - float(i) * 0.37) * 2.5;
  float on = step(0.7, fract(sin(slot * 12.9898 + float(i) * 78.233) * 43758.5453));
  return vec3(on * exp(-age * 0.8) * smoothstep(0.4, 0.8, u_level + 0.2), 0.7, age);
}

vec2 pcLevel(int pc) {          // (level, strike)
  if (gHost) return vjAt(pc, 1).xy;
  return vec2(step(0.8, fract(sin(floor(u_time * 1.5) * 91.7 + float(pc) * 17.3) * 43758.5)) * u_mid, 0.0);
}

// ------------------------------------------------------------------------------------------------- light parts --
float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
float starAngle(float pc) { return PI * 0.5 - mod(pc * 7.0, 12.0) * (PI / 6.0); }

// one blob: add its field to f and its gradient to g
void blob(vec2 p, vec2 c, float r, inout float f, inout vec2 g) {
  vec2 d = p - c;
  float d2 = dot(d, d) + 1e-5;
  float k = r * r / d2;
  f += k;
  g += -2.0 * k / d2 * d;
}

// The studio the chrome reflects. The reflected ray r is mapped stereographically onto a backdrop behind the viewer,
// s = r.xy / (1 + r.z): a flat top reflects the backdrop's middle (s = 0), a rim facing sideways reflects its far edges
// (|s| > 1). The backdrop: a bright ceiling over a dark floor, a big soft key light high on the left, a thin bright
// horizon, and two tall softboxes in the palette's colours. fw is the screen footprint of s, so every edge stays soft
// by at least a pixel and steep rims do not alias.
vec3 studio(vec2 s, float fw, float t) {
  float soft = max(fw * 1.5, 0.004);
  vec3 ceiling = mix(vec3(0.30, 0.32, 0.36), gPal[2] * 0.35 + 0.12, 0.35);
  vec3 floorC = vec3(0.010, 0.010, 0.014) + gPal[1] * 0.05 * (1.0 - smoothstep(-0.2, -1.2, s.y));
  vec3 c = mix(floorC, ceiling, smoothstep(-0.2 - soft, 0.35 + soft, s.y));
  c *= 1.0 - 0.6 * smoothstep(1.0, 2.2, length(s));                 // the walls beyond the lights are darker
  // the key light: a big soft box high on the left
  c += vec3(1.0, 0.96, 0.9) * 2.2 * (1.0 - smoothstep(0.22 - soft, 0.40 + soft, length((s - vec2(-0.32, 0.55)) * vec2(1.0, 1.6))));
  // the horizon: a thin bright line where the floor meets the far wall
  c += mix(vec3(1.0), gPal[0], 0.3) * (1.0 - smoothstep(0.0, 0.025 + soft, abs(s.y + 0.18))) * 1.4;
  // two tall softboxes in the palette's colours, standing on the horizon
  float up = smoothstep(-0.2 - soft, -0.1 + soft, s.y) * (1.0 - smoothstep(1.1, 1.5, s.y));
  c += mix(gPal[0], vec3(1.0), 0.25) * (1.0 - smoothstep(0.07 - soft, 0.11 + soft, abs(s.x - 0.92 - 0.06 * sin(t * 0.21)))) * up * 1.8;
  c += mix(gPal[2], vec3(1.0), 0.2) * (1.0 - smoothstep(0.07 - soft, 0.11 + soft, abs(s.x + 0.98 + 0.05 * sin(t * 0.17)))) * up * 1.6;
  return c;
}

void main() {
  vjLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float t = u_time * (0.25 + 0.9 * u_k2);
  float bass = clamp(0.65 * u_bass + 0.35 * u_pulse, 0.0, 1.5);

  // the field: seven drifting blobs, swollen by the bass and bumped by the kick
  float f = 0.0;
  vec2 g = vec2(0.0);
  float swell = (0.75 + 0.5 * u_k1) * (1.0 + 0.28 * bass + 0.10 * gKick);
  for (int i = 0; i < 7; i++) {
    float fi = float(i);
    float h = hash12(vec2(fi, 3.7));
    vec2 c = vec2(0.42 * asp * sin(t * (0.21 + 0.07 * h) + fi * 2.1), 0.30 * cos(t * (0.17 + 0.05 * fi / 7.0) + fi * 1.3 + h));
    c *= 0.55 + 0.25 * sin(t * 0.09 + fi);
    float r = (0.050 + 0.030 * h) * swell;
    blob(p, c, r, f, g);
  }
  // keys: beads on the circle of fifths in their pitch colour (the colour is gathered alongside the field)
  vec3 tintAcc = vec3(0.0);
  float tintW = 0.0;
  for (int pc = 0; pc < 12; pc++) {
    vec2 lv = pcLevel(pc);
    if (lv.x < 0.01) continue;
    float a = starAngle(float(pc));
    vec2 c = (0.30 - 0.06 * lv.y) * vec2(cos(a), sin(a));
    float r = 0.028 * lv.x * (0.7 + 0.6 * lv.y) * swell;
    float before = f;
    blob(p, c, r, f, g);
    float w = f - before;
    tintAcc += PC_COL[pc] * w;
    tintW += w;
  }
  // pads: drops thrown in from the rim at their clock positions (pad 12 at twelve o'clock), falling toward the middle
  for (int i = 0; i < 12; i++) {
    vec3 lv = padLevel(i);
    if (lv.x < 0.003) continue;
    float a = PI * 0.5 - float(i + 1) * (PI / 6.0);
    float reach = 0.48 * exp(-lv.z * 1.6) + 0.06;
    vec2 c = reach * vec2(cos(a) * min(asp, 1.6), sin(a));
    float r = (0.025 + 0.05 * lv.y) * sqrt(lv.x) * (0.5 + u_k4);
    float before = f;
    blob(p, c, r, f, g);
    float w = f - before;
    tintAcc += padColour(i) * w * 1.5;
    tintW += w;
  }

  // the surface: F = 1, antialiased by the field's own screen-space slope
  float edgeW = max(length(g) * px * 1.2, 1e-4);
  float inside = smoothstep(1.0 - edgeW, 1.0 + edgeW, f);
  // a height field from 1/F: the slope is the field's gradient over F squared, steep at the rim and flat on top
  vec2 slope = g / max(f * f, 1e-4) * 0.05;
  // the snare runs a slow wave over the skin
  slope += gSnare * 0.12 * vec2(sin(p.y * 38.0 + u_time * 21.0), cos(p.x * 33.0 - u_time * 17.0));
  vec3 n = normalize(vec3(-slope, 1.0));
  vec3 r = reflect(vec3(0.0, 0.0, -1.0), n);
  vec2 sEnv = r.xy / max(1.0 + r.z, 0.08);
  float fwEnv = length(fwidth(sEnv));
  vec3 env = studio(sEnv, fwEnv, u_time);
  vec3 tint = tintW > 1e-4 ? tintAcc / tintW : vec3(1.0);
  float tintAmt = tintW > 1e-4 ? clamp(tintW / max(f, 1e-3), 0.0, 1.0) : 0.0;
  vec3 metal = mix(vec3(0.92, 0.94, 1.0), mix(vec3(1.0), gPal[0], 0.6), u_k6 * 0.7);
  metal = mix(metal, tint * 1.2, tintAmt * 0.85);
  vec3 chrome = env * metal * (0.45 + 0.8 * u_k3);
  chrome *= 1.0 + 0.35 * gKick + 0.3 * gChordPulse;

  // the room: dark, a soft backlight in the palette behind the mass, and a contact shadow around it
  vec3 room = vec3(0.0015, 0.0016, 0.0024) + gPal[1] * 0.018 * exp(-length(p * vec2(0.8, 1.2)) * 2.2);
  float shade = smoothstep(0.3, 1.0, f) * (1.0 - inside);
  room *= 1.0 - 0.7 * shade;
  room += gPal[0] * exp(-abs(f - 0.85) * 12.0) * (1.0 - inside) * (0.01 + 0.04 * gKick);

  vec3 col = mix(room, chrome, inside);
  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.2);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  vec3 prev = texture(u_prev, v_uv).rgb;
  vec3 trail = max(prev * (0.15 + 0.6 * u_k5) - 2.0 / 255.0, 0.0);
  outColor = vec4(clamp(max(col, trail), 0.0, 1.0), 1.0);
}
