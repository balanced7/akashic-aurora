#version 300 es
//! {"id": "feedback-tunnel", "name": "Feedback Tunnel", "author": "Navi", "tags": ["feedback", "tunnel", "beat"], "params": [{"k": 1, "name": "trails", "default": 0.6}, {"k": 2, "name": "zoom", "default": 0.45}, {"k": 3, "name": "spin", "default": 0.35}, {"k": 4, "name": "tunnel", "default": 0.5}, {"k": 5, "name": "punch", "default": 0.55}]}
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

mat2 rot(float a) { float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }

void main() {
  vec2 uv = v_uv;
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = vec2((uv.x - 0.5) * asp, uv.y - 0.5);

  // source for this frame: the video (if any) or a generative centre; the trails
  // come from u_prev. Zoom + spin about the centre creates the tunnel.
  float zoom = 0.90 + 0.08 * u_k2;                     // <<1: squeeze inward = tunnel
  float spin = 0.02 + 0.06 * u_k3;
  float beatZoom = 1.0 + 0.10 * u_k5 * u_beat;         // punched by the beat
  vec2 cp = rot(spin + u_beat * 0.05) * (p * (zoom * beatZoom));

  // trails: previous frame pulled inward
  float trails = 0.90 + 0.08 * u_k1;                    // how much of the past survives
  vec3 prev = texture(u_prev, clamp(cp + 0.5, 0.0, 1.0)).rgb;
  // subtract a little so an 8-bit buffer never leaves permanent residue
  prev = max(prev * trails - 1.0 / 255.0, 0.0);

  // fresh injection at the tunnel's mouth (centre), seeded EVERY frame from a ring + spectrum
  // petals that drift on their own in silence, so the trails always have something to carry.
  bool hasVideo = u_has_video > 0.5;
  vec3 core;
  if (hasVideo) {
    vec2 vuv = video_uv(uv);
    bool inside = vuv.x >= 0.0 && vuv.x <= 1.0 && vuv.y >= 0.0 && vuv.y <= 1.0;
    core = inside ? texture(u_video, vuv).rgb : vec3(0.0);
  } else {
    // generative core: a waveform ring + spectrum petals, alive on an idle floor (not gated)
    // Silence must still show a VISIBLE ring/petal floor so the trails have something to
    // carry: the idle amplitude is raised and always adds to the ring, not just modulates it.
    float rc = length(p) + 1.0e-9;
    float a = atan(p.y, p.x);
    float spec = texture(u_audio, vec2(0.5 + 0.4 * cos(a + u_time), 0.25)).r;
    float idle = 0.18 + 0.06 * sin(u_time * 0.5 + a * 2.0);  // higher + always-positive floor
    float ring = smoothstep(0.30, 0.0, abs(rc - (0.13 + 0.08 * (idle + spec))));
    float petalK = 5.0 + 3.0 * sin(u_time * 0.2);
    float petal = 0.5 + 0.5 * cos(petalK * a + u_time * 0.15) * smoothstep(0.6, 0.05, rc);
    // idle is ADDED to the ring (so silence still outlines the ring) while spectrum adds the
    // bright lobes when the music hits.
    core = vec3(0.12, 0.30, 0.55) * (ring * (0.45 + u_level * 2.0 + 1.2 * idle) + 0.24 * petal * (idle + spec))
         + vec3(0.55, 0.25, 0.08) * ring * (idle + spec);
  }

  // tunnel depth: a SOFT vignette (strong edges were blacking out half the frame). Use a
  // raised floor so the centre-to-edge falloff never reaches full black except at the rim.
  float r = length(p);
  float depth = clamp(1.0 - pow(r * (1.05 + 0.6 * u_k4), 2.2), 0.06, 1.0);

  // hue rotates ONLY the freshly injected core, never the u_prev trail (compounds per frame).
  // A wrap-safe desaturating hue-turn that keeps the lit core from blowing out before the bloom.
  vec3 hsv = rgb2hsv(core);
  vec3 hued = hsv2rgb(vec3(fract(hsv.x + u_hue / 360.0), min(hsv.y * 1.1, 1.0), hsv.z));
  vec3 col = hued * mix(0.30, 1.0, u_k1) * (0.6 + u_bass) * depth + prev * 0.85 * depth;

  // SOFT SHOULDER on the core BEFORE the beat punch and bloom accumulate: a full-range
  // x/(1+x) compression (via tanh proportional to magnitude) keeps the hue-rotated centre
  // from ever slamming into 1.0 while leaving the midtones alone.
  float mag = max(col.r, max(col.g, col.b));
  float b = max(mag, 1.0e-5);
  col *= (tanh(b * 1.6) / b);

  // beat punch: brighten on the beat (the shoulder above already caps the centre, so this
  // lift never re-blowouts)
  col += col * (0.30 * u_k5 * u_beat);
  col *= mix(0.35, 1.0, u_intensity);

  // final soft clip (highlights only) then clamp for the feedback buffer
  vec3 over = max(col - 0.8, 0.0);
  col = min(col, vec3(0.8)) + 0.2 * tanh(over / 0.2);

  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
