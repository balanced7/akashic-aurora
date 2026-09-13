#version 300 es
//! {"id": "aurora-ribbons", "name": "Aurora Ribbons", "author": "Navi", "tags": ["generative", "spectrum"], "params": [{"k": 1, "name": "flow", "default": 0.5}, {"k": 2, "name": "bands", "default": 0.6}, {"k": 3, "name": "spread", "default": 0.5}, {"k": 4, "name": "warmth", "default": 0.45}, {"k": 5, "name": "bloom", "default": 0.5}]}
precision highp float;

uniform sampler2D u_video;
uniform sampler2D u_prev;
uniform sampler2D u_audio;
uniform vec2  u_res;
uniform vec2  u_video_res;
uniform float u_time;
uniform float u_media_time;
uniform float u_frame;
uniform float u_has_video;
uniform float u_pulse;
uniform float u_beat;
uniform float u_level;
uniform float u_bass, u_mid, u_high, u_flux;
uniform float u_hue;
uniform float u_intensity;
uniform float u_k1, u_k2, u_k3, u_k4, u_k5, u_k6, u_k7, u_k8;

in vec2 v_uv;
out vec4 outColor;

vec2 video_uv(vec2 uv) {
  float ca = u_res.x / max(u_res.y, 1.0);
  float va = u_video_res.x / max(u_video_res.y, 1.0);
  vec2 s = va > ca ? vec2(1.0, ca / va) : vec2(va / ca, 1.0);
  return (uv - 0.5) / s + 0.5;
}
vec3 rgb2hsv(vec3 c) {
  vec4 K = vec4(0.0, -1.0/3.0, 2.0/3.0, -1.0);
  vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
  vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10;
  return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}
vec3 hsv2rgb(vec3 c) {
  vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
  vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}
vec3 hueRot(vec3 c, float deg) {
  vec3 h = rgb2hsv(c);
  h.x = fract(h.x + deg / 360.0);
  return hsv2rgb(h);
}

void main() {
  vec2 uv = v_uv;
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = vec2((uv.x - 0.5) * asp, uv.y - 0.5);

  // Spectrum: sample the log-spaced spectrum row (y=0.25) across x.
  // A smooth flowing band is a sum of travelling sines whose phase/amp tracks the
  // spectrum at a few fixed frequencies. Silent -> gentle, slow, low amplitude.
  float flow = 0.1 + 0.6 * u_k1;                       // time speed
  float nBands = 2.0 + 5.0 * u_k2;                     // band count (fixed, not a loop)
  float spread = 0.25 + 1.0 * u_k3;

  // three spectrum taps, spread across log-frequency, feeding three layers
  float s0 = texture(u_audio, vec2(0.12, 0.25)).r;      // low / bass-ish
  float s1 = texture(u_audio, vec2(0.45, 0.25)).r;      // mid
  float s2 = texture(u_audio, vec2(0.80, 0.25)).r;      // high-ish

  // drifting field, three sine families (analytic, no noise crawl).
  // Each band's drive is an IDLE floor + a spectrum term: silent visualizer mode still
  // breathes a slow, gentle aurora instead of collapsing to near-black.
  float t = u_time * flow;
  float y = p.y * 3.0;
  float idle0 = 0.12 + 0.06 * sin(t * 0.7 + p.x * 2.0);
  float idle1 = 0.12 + 0.06 * sin(t * 0.5 - p.x * 1.5);
  float idle2 = 0.12 + 0.06 * sin(t * 0.6 + p.y * 1.5);
  float d0 = idle0 + 2.0 * s0;
  float d1 = idle1 + 2.0 * s1;
  float d2 = idle2 + 2.0 * s2;
  float w0 = sin(p.x * (3.0 + 0.5 * d0) + t * 1.3 + d0 * 3.0);
  float w1 = sin(p.x * (5.0 + 0.6 * d1) - t * 0.9 + p.y * 2.0);
  float w2 = sin(p.x * (7.0 + 0.7 * d2) + t * 0.6 + d2 * 2.0);

  // band = a soft vertical ribbon; spread bends them with the spectrum
  float band = 0.0;
  band += pow(clamp(1.0 - abs(y - (w0 * spread - 1.0)) * (1.5 - s0 * 0.6), 0.0, 1.0), 2.0) * (0.10 + 0.30 * clamp(d0, 0.0, 1.0));
  band += pow(clamp(1.0 - abs(y - (w1 * spread)) * (1.6 - s1 * 0.6), 0.0, 1.0), 2.0) * (0.10 + 0.30 * clamp(d1, 0.0, 1.0));
  band += pow(clamp(1.0 - abs(y - (w2 * spread + 1.0)) * (1.4 - s2 * 0.6), 0.0, 1.0), 2.0) * (0.10 + 0.30 * clamp(d2, 0.0, 1.0));

  // analogous palette (cool indigo -> periwinkle -> warm accent), swayed by u_hue + warmth;
  // the base tint stays soft-lit in silence rather than dropping to 0.
  vec3 col = vec3(0.03, 0.05, 0.10);
  col += vec3(0.05, 0.16, 0.38) * band * (0.5 + 0.5 * d1);
  col += vec3(0.20, 0.42, 0.62) * band * d2 * 0.5;
  float warmth = u_k4;
  col += vec3(0.60, 0.30, 0.12) * band * d0 * 0.5 * warmth;   // coral accent on the bass

  // video layer, if any: softly gate the ribbons over the video (additive, low alpha)
  bool hasVideo = u_has_video > 0.5;
  if (hasVideo) {
    vec2 vuv = video_uv(uv);
    bool inside = vuv.x >= 0.0 && vuv.x <= 1.0 && vuv.y >= 0.0 && vuv.y <= 1.0;
    vec3 vid = inside ? texture(u_video, vuv).rgb : vec3(0.0);
    // dim the video so the ribbons read, but keep the picture as the base
    col = vid * 0.35 + col;
  }

  // bloom / pulse lift (k5), and beat punch; a small floor keeps the aurora glowing in silence
  col += col * (0.25 * u_k5 * (0.4 + u_pulse + u_beat));

  // global hue + intensity
  col = hueRot(col, u_hue);
  col *= mix(0.35, 1.0, u_intensity);

  // filmic shoulder (highlights only, midtones untouched) then clamp for the feedback buffer
  vec3 over = max(col - 0.8, 0.0);
  col = min(col, vec3(0.8)) + 0.2 * tanh(over / 0.2);

  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
