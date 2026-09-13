#version 300 es
//! {"id": "chromatic-bloom", "name": "Chromatic Bloom", "author": "Navi", "tags": ["video", "bloom", "aberration"], "params": [{"k": 1, "name": "bloom", "default": 0.6}, {"k": 2, "name": "aberration", "default": 0.5}, {"k": 3, "name": "leaks", "default": 0.5}, {"k": 4, "name": "saturate", "default": 0.5}, {"k": 5, "name": "bleed", "default": 0.4}]}
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
float h31(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453123); }
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
  vec2 vuv = video_uv(uv);
  bool hasVideo = u_has_video > 0.5;
  bool inside = hasVideo && vuv.x >= 0.0 && vuv.x <= 1.0 && vuv.y >= 0.0 && vuv.y <= 1.0;

  // aberration (k2), pulse-driven
  float aber = 0.006 * u_k2 * (u_pulse + 0.2);
  vec2 du = (uv - 0.5) * aber;

  // base color: video, or a generative luminous field in visualizer mode
  vec3 col;
  if (hasVideo) {
    vec2 g = video_uv(uv);
    vec2 gr = video_uv(clamp(uv + du, 0.0, 1.0));
    vec2 gb = video_uv(clamp(uv - du, 0.0, 1.0));
    bool ir = gr.x >= 0.0 && gr.x <= 1.0 && gr.y >= 0.0 && gr.y <= 1.0;
    bool ib = gb.x >= 0.0 && gb.x <= 1.0 && gb.y >= 0.0 && gb.y <= 1.0;
    bool ig = inside;
    vec3 r = ig ? texture(u_video, gr).rgb : vec3(0.0);
    vec3 grn = ig ? texture(u_video, g).rgb : vec3(0.0);
    vec3 b = ig ? texture(u_video, gb).rgb : vec3(0.0);
    // channel recombine with the shifted samples = chromatic fringe
    col = vec3(r.r, grn.g, b.b);
  } else {
    // generative glow: a slow drifting plasma field. Drive is an idle floor + spectrum,
    // so silence gives a soft luminous wash instead of a flat grey-pink void.
    float asp = u_res.x / max(u_res.y, 1.0);
    vec2 p = vec2((uv.x - 0.5) * asp, uv.y - 0.5);
    float r = length(p) + 1.0e-9;
    float a = atan(p.y, p.x);
    float s0 = texture(u_audio, vec2(0.15, 0.25)).r;
    float s1 = texture(u_audio, vec2(0.55, 0.25)).r;
    float s2 = texture(u_audio, vec2(0.85, 0.25)).r;
    // slow, smooth drifting structure (analytic, no noise crawl): two travelling blobs
    float t = u_time;
    float blob1 = smoothstep(0.55, 0.0, abs(r - (0.34 + 0.12 * sin(t * 0.25))));
    float blob2 = smoothstep(0.5, 0.0, abs(r - (0.55 + 0.14 * sin(t * 0.19 + 2.1 + a))));
    float idle = 0.045 + 0.020 * sin(t * 0.3 + a * 3.0);
    col = vec3(0.035, 0.030, 0.050)                                      // soft lavender-black floor
        + vec3(0.45, 0.18, 0.34) * (blob1 + 0.5 * blob2) * (idle + s0)    // rose-magenta core
        + vec3(0.10, 0.30, 0.48) * (blob2 + 0.5 * blob1) * (idle + s1 + s2); // cool blue halo
  }

  // bloom (k1): cheap multi-tap radial blur APPROXIMATED with just two u_prev taps (the core
  // weight is the fresh colour itself), so the total texture reads stay at 8.
  float bloomAmt = 0.05 + 0.30 * u_k1 * (0.4 + u_pulse);
  vec3 bloom = col * 0.5;
  bloom += texture(u_prev, clamp(uv + vec2(0.013, 0.0) * bloomAmt, 0.0, 1.0)).rgb * 0.28;
  bloom += texture(u_prev, clamp(uv - vec2(0.013, 0.0) * bloomAmt, 0.0, 1.0)).rgb * 0.22;

  // light leaks (k3): bright soft bars that sweep with the pulse (small idle so they breathe)
  float leak = 0.0;
  leak += smoothstep(0.6, 0.0, abs(uv.y - (0.5 + 0.3 * sin(u_time * 0.4 + u_bass * 4.0)))) * (0.25 + u_pulse);
  leak += smoothstep(0.5, 0.0, abs(uv.x - (0.5 + 0.3 * cos(u_time * 0.3)))) * 0.15 * (0.15 + u_mid);
  vec3 leakCol = vec3(0.9, 0.35, 0.10) * leak * u_k3 * 0.32;

  // combine: base + bloom halo + leaks; then saturation (k4) and bleed (k5) toward warm
  col = col + bloom * bloomAmt + leakCol;
  // saturation boost: mix toward a saturated version
  float lum = dot(col, vec3(0.299, 0.587, 0.114));
  col = mix(vec3(lum), col, mix(0.9, 1.4, u_k4));
  // bleed: add a little spectrum-tinted warmth that trails the beat
  col += vec3(0.06, 0.02, 0.0) * u_k5 * (0.15 + u_bass + u_beat);

  // hue rotates ONLY the fresh frame colour — never the u_prev bloom — so a rotated hue
  // does not compound every frame.
  col = hueRot(col, u_hue);
  col *= mix(0.35, 1.0, u_intensity);

  vec3 over = max(col - 0.8, 0.0);
  col = min(col, vec3(0.8)) + 0.2 * tanh(over / 0.2);

  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
