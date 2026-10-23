#version 300 es
//! {"id": "vj-aurora-curtains", "name": "VJ Aurora Curtains", "author": "Vandor", "tags": ["vj", "generative", "aurora", "chord", "pads"], "params": [{"k": 1, "name": "flow", "default": 0.5}, {"k": 2, "name": "curtains", "default": 0.6}, {"k": 3, "name": "rays", "default": 0.5}, {"k": 4, "name": "fringe", "default": 0.4}, {"k": 5, "name": "trails", "default": 0.3}, {"k": 6, "name": "height", "default": 0.5}]}
precision highp float;

// Aurora Curtains (arsenal/web/vj.html, Play-loadable). The stage painter's aurora of the aurora-band recipe
// (arsenal/web/glsl/groups/aurora-band.glsl), reduced: up to three curtains, each a hem that sways like fabric on a line,
// filament strands stretched tall above it and rays reaching higher, coloured by height alone (hem, body, crown), over a
// still lake that mirrors them. The colours are the chord's: on a chord change the new colours travel along the curtains
// from left to right (the page hands over the palette before and after, and how far the change has travelled). Each beat
// sends a brightening along the hem; the twelve pads raise twelve ray columns across the sky (velocity sets their
// height); tension puts a coral fringe on the hem and agitates the fabric; bass makes it sway.

uniform sampler2D u_video;   // the VJ page: its 16x6 VJ strip (u_has_video stays 0); Play: the video or a 1x1 black texture
uniform sampler2D u_prev;
uniform vec2  u_res;
uniform float u_time;
uniform float u_has_video;
uniform float u_pulse, u_beat, u_level, u_bass, u_mid, u_high;
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
vec3 gPalBefore[4];
float gTravel, gPhase, gPulse, gTension, gConf;

vec4 vjAt(int x, int y) { return texelFetch(u_video, ivec2(x, y), 0); }

vec3 hueLinear(float turns) {
  vec3 c = clamp(abs(fract(turns + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0, 0.0, 1.0);
  return c * c;
}

void vjLoad() {
  gHost = u_has_video < 0.5 && textureSize(u_video, 0) == ivec2(16, 6);
  if (gHost) {
    for (int i = 0; i < 4; i++) {
      gPal[i] = vjAt(i, 2).rgb;
      gPalBefore[i] = vjAt(i + 4, 2).rgb;
    }
    gTravel = vjAt(8, 2).x;
    vec4 beat = vjAt(12, 0);
    gPhase = beat.x; gPulse = beat.y;
    gTension = vjAt(14, 0).z;
    gConf = 1.0;
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.42); gPal[1] = hueLinear(h + 0.58); gPal[2] = hueLinear(h + 0.76); gPal[3] = hueLinear(h + 0.03);
    for (int i = 0; i < 4; i++) gPalBefore[i] = gPal[i];
    gTravel = 1.0;
    gPhase = fract(u_time * 2.0); gPulse = u_beat;
    gTension = 0.0;
    gConf = 0.5;
  }
}

vec3 padColour(int i) { return gHost ? vjAt(i, 3).rgb : gPal[i - 4 * (i / 4)]; }

vec2 padLevel(int i) {          // (envelope, velocity)
  if (gHost) return vjAt(i, 0).xy;
  float band = i < 4 ? u_high : (i < 8 ? u_mid : u_bass);
  float gate = smoothstep(0.6, 0.98, 0.5 + 0.5 * sin(u_time * 0.6 + float(i) * 2.4));
  return vec2(smoothstep(0.55, 0.9, band) * gate, band);
}

// ------------------------------------------------------------------------------------------------- the fabric --
float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash12(i), hash12(i + vec2(1.0, 0.0)), u.x), mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), u.x), u.y);
}
// colour by height above the hem: hem, body, crown (a colour keyed over brightness, as aurora-band does)
vec3 ramp(vec3 hem, vec3 body, vec3 crown, float h) {
  return mix(mix(hem, body, smoothstep(0.0, 0.35, h)), crown, smoothstep(0.35, 1.0, h));
}

void main() {
  vjLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float u = p.x / max(asp * 0.5, 1e-3);          // -1 at the left edge, 1 at the right
  float t = u_time;
  float lakeY = -0.30;

  // the lake mirrors last frame's sky (one frame late, which nobody can see), rippled by the bass
  if (p.y < lakeY) {
    float depth = lakeY - p.y;
    float ripple = (vnoise(vec2(p.x * 18.0, p.y * 60.0 - t * 0.8)) - 0.5) * (0.004 + 0.012 * u_bass) * (1.0 + depth * 6.0);
    vec2 mirrored = vec2(v_uv.x + ripple, 2.0 * lakeY - p.y + 0.5);   // the sky point mirrored about the shore
    vec3 sky = texture(u_prev, vec2(mirrored.x, clamp(mirrored.y, 0.0, 1.0))).rgb;
    vec3 water = sky * (0.42 - 0.6 * depth) + vec3(0.0008, 0.0015, 0.003);
    float shore = exp(-depth / (2.0 * px));
    outColor = vec4(clamp(water + gPal[0] * 0.05 * shore, 0.0, 1.0), 1.0);
    return;
  }

  // the night: near black overhead, a faint glow toward the horizon, and a few stars that breathe slowly
  vec3 col = mix(vec3(0.0045, 0.006, 0.013), vec3(0.0004, 0.0005, 0.0015), smoothstep(lakeY, 0.5, p.y));
  vec2 sc = floor(p * 140.0);
  float sh = hash12(sc);
  if (sh > 0.985) {
    vec2 sp = (sc + 0.5 + 0.35 * (vec2(hash12(sc + 3.1), hash12(sc + 7.7)) - 0.5)) / 140.0;
    float tw = 0.65 + 0.35 * sin(t * (0.4 + sh) + sh * 40.0);
    col += vec3(0.6, 0.65, 0.8) * exp(-dot(p - sp, p - sp) / (2.0 * px * px)) * tw * (sh - 0.985) * 40.0;
  }

  // the chord's colours, arriving from the left as the change travels
  float front = mix(-1.5, 1.5, gTravel);
  float arrived = 1.0 - smoothstep(front - 0.3, front + 0.3, u);
  vec3 hem = mix(gPalBefore[0], gPal[0], arrived);
  vec3 body = mix(gPalBefore[1], gPal[1], arrived);
  vec3 crown = mix(gPalBefore[2], gPal[2], arrived);
  vec3 fringeTint = mix(gPal[3], vec3(1.0, 0.16, 0.10), 0.5 * gTension);

  float bass = clamp(0.6 * u_bass + 0.4 * u_pulse, 0.0, 1.5);
  float agitate = 1.0 + 1.5 * gTension;
  // a brightening that walks along the hem through each beat
  float walker = exp(-pow((u - mix(-1.3, 1.3, gPhase)) / 0.35, 2.0)) * gConf;

  int curtains = 1 + int(floor(u_k2 * 2.0 + 0.5));
  vec3 light = vec3(0.0);
  for (int c = 0; c < 3; c++) {
    if (c >= curtains) break;
    float fc = float(c);
    float scale = 1.0 + 0.75 * fc;
    float share = 1.0 / (1.0 + 1.1 * fc);
    float along = p.x * scale * 1.5 + 13.7 * fc;
    // the hem: a broad arc that sways slowly, more with the bass
    float sway = (vnoise(vec2(along * 0.55 + t * 0.04 * agitate, fc * 3.1)) - 0.5) * (0.20 + 0.35 * u_k1) * (1.0 + 0.6 * bass) / scale;
    float hemY = -0.22 + 0.30 * u_k6 + 0.15 * fc + sway + 0.05 * (1.0 - u * u);
    float above = (p.y - hemY) * scale;
    if (above < -0.02) continue;
    // folds: the fabric's address pushed sideways by a slow field, so strands bunch where it folds
    float fold = along + (0.25 + 0.5 * u_k1) * (vnoise(vec2(along * 1.3 - t * 0.03, above * 0.8 + t * 0.02 + fc)) - 0.5) * 2.0;
    // strands: ridged noise stretched tall; rays: sparse brighter columns reaching higher
    float ridge = 1.0 - abs(2.0 * vnoise(vec2(fold * 7.0, above * 0.9 + t * 0.05 * agitate + fc * 5.0)) - 1.0);
    float strands = pow(ridge, 5.0) * 1.4 + 0.12;
    float ray = pow(vnoise(vec2(fold * 2.6 + t * 0.06, fc * 7.3)), 3.0) * (0.3 + 1.8 * u_k3);
    float reach = 0.10 + 0.22 * ray + 0.08 * bass;
    float profile = exp(-max(above, 0.0) / reach) * smoothstep(-0.004, 0.006, above);
    float bright = (strands * (0.55 + 0.6 * ray)) * profile * share * (0.55 + 0.6 * bass + 0.5 * walker * (1.0 - smoothstep(0.0, 0.1, above)));
    vec3 tint = ramp(hem, body, crown, clamp(above / 0.45, 0.0, 1.0));
    light += tint * bright;
    // the fringe: a thin warm layer at the very hem, from the knob and from tension
    float fringe = exp(-max(above, 0.0) / 0.010) * smoothstep(-0.003, 0.002, above) * (0.25 * u_k4 + 0.9 * gTension);
    light += fringeTint * fringe * share * strands;
  }

  // the pads: twelve ray columns across the sky, velocity sets how high they reach
  for (int i = 0; i < 12; i++) {
    vec2 lv = padLevel(i);
    if (lv.x < 0.002) continue;
    float xi = (-0.9 + 1.8 * float(i) / 11.0) * asp * 0.5;
    float w = 0.010 + 0.028 * lv.y;
    float base = -0.18 + 0.30 * u_k6;
    float top = base + (0.20 + 0.55 * lv.y) * (0.4 + 0.6 * lv.x);
    float column = exp(-pow((p.x - xi) / w, 2.0)) * smoothstep(base - 0.04, base + 0.02, p.y) * (1.0 - smoothstep(base, top, p.y));
    float flare = 0.7 + 0.3 * vnoise(vec2(p.y * 12.0 - t * 1.5, float(i)));
    light += padColour(i) * column * flare * lv.x * 1.2;
  }

  col += light;
  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.2);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  vec3 prev = texture(u_prev, v_uv).rgb;
  col = max(col, max(prev * (0.25 + 0.6 * u_k5) - 1.5 / 255.0, 0.0));
  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
