#version 300 es
//! {"id": "first-light", "name": "First Light", "author": "Navi", "tags": ["video", "generative", "pulse"], "params": [{"k": 1, "name": "zoom", "default": 0.5}, {"k": 2, "name": "aberration", "default": 0.55}, {"k": 3, "name": "glow", "default": 0.6}, {"k": 4, "name": "vignette", "default": 0.45}, {"k": 5, "name": "flux", "default": 0.4}]}
precision highp float;

// uniforms v1 (a preset uses only what it needs)
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

// ---- helpers
vec2 video_uv(vec2 uv) {
  float ca = u_res.x / max(u_res.y, 1.0);
  float va = u_video_res.x / max(u_video_res.y, 1.0);
  vec2 s = va > ca ? vec2(1.0, ca / va) : vec2(va / ca, 1.0);
  return (uv - 0.5) / s + 0.5;
}
float h31(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453123); }

// perceptual hue rotation (Iq): luminance + saturation survive a hue change
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

// generative background for visualizer mode (no video): a slow colour field
// driven by the spectrum on top of an idle floor, so silence gives a gentle
// drifting banded wash instead of a near-flat navy.
vec3 generative(vec2 uv, float t) {
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = vec2((uv.x - 0.5) * asp, uv.y - 0.5);
  float r = length(p) + 1.0e-9;
  float a = atan(p.y, p.x);
  // spectrum-driven energy on an idle floor (never zero in silence)
  float spec = texture(u_audio, vec2(0.5 + 0.4 * cos(a + t * 0.2), 0.25)).r;
  float idle = 0.08 + 0.04 * sin(t * 0.25 + a * 2.0);
  float bands = idle + 0.33 * u_bass + 0.33 * u_mid + 0.34 * u_high + 0.5 * u_level;
  // two smooth drifting rings for depth (analytic, no noise crawl)
  float ring1 = smoothstep(0.85, 0.0, abs(r - (0.34 + 0.10 * sin(t * 0.2 + a))));
  float ring2 = smoothstep(0.8, 0.0, abs(r - (0.56 + 0.10 * sin(t * 0.15 + 2.0))));
  vec3 col = vec3(0.035, 0.05, 0.09);
  col += vec3(0.06, 0.15, 0.26) * (ring1 + 0.6 * ring2) * (0.5 + bands);
  col += vec3(0.16, 0.08, 0.03) * spec * (0.25 + idle) * ring1;
  return col;
}

void main() {
  vec2 uv = v_uv;
  vec2 vuv = video_uv(uv);
  bool hasVideo = u_has_video > 0.5;
  bool inside = hasVideo && vuv.x >= 0.0 && vuv.x <= 1.0 && vuv.y >= 0.0 && vuv.y <= 1.0;

  // beat-driven zoom about the centre (k1); only meaningful when there is a picture
  float zoomAmt = 1.0 + 0.16 * u_k1 * u_pulse * sin(u_time * 1.3);
  vec2 c = uv - 0.5;

  // chromatic aberration off the beat (k2)
  float aber = 0.004 * u_k2 * u_pulse;
  vec2 cuv = c / zoomAmt + 0.5;
  vec2 cr = c * (1.0 + aber) / zoomAmt + 0.5;
  vec2 cb = c * (1.0 - aber) / zoomAmt + 0.5;

  vec3 col;
  if (hasVideo) {
    vec3 colR = texture(u_video, video_uv(cr)).rgb;
    vec3 colG = texture(u_video, video_uv(cuv)).rgb;
    vec3 colB = texture(u_video, video_uv(cb)).rgb;
    // outside the letterbox: sample the centre so bars stay black
    colR = inside ? colR : vec3(0.0);
    colG = inside ? colG : vec3(0.0);
    colB = inside ? colB : vec3(0.0);
    col = vec3(colR.r, colG.g, colB.b);
  } else {
    // visualizer mode: generative field gets the same pulse/aberration treatment
    col = generative(cuv, u_time);
  }

  // pulse glow (k3); a small floor keeps the field breathing in silence
  col += col * (0.30 * u_k3 * (0.3 + u_pulse));

  // global hue (MIDI/global) + a small spectrum-tinted internal hue drift
  col = hueRot(col, u_hue);

  // intensity: never below a visible floor, so visualizer silence is not dead
  col *= mix(0.35, 1.0, u_intensity);

  // tone: highlights shoulder only (midtones untouched), clamp for the feedback buffer
  vec3 over = max(col - 0.8, 0.0);
  col = min(col, vec3(0.8)) + 0.2 * tanh(over / 0.2);

  // static dust keyed on fixed coord (no crawl), amplitude from flux (k5)
  float dust = h31(vec3(floor(gl_FragCoord.xy), 0.0));
  col += (dust - 0.5) * 0.018 * u_k5 * u_flux;

  // subtle spectral lift in visualizer mode so the field breathes
  if (!hasVideo) {
    float spec = texture(u_audio, vec2(0.5 + 0.4 * sin(uv.x * 6.2831), 0.25)).r;
    col += 0.12 * (0.25 + spec);
  }

  // aspect-corrected cubic vignette (k4), raised floor so corners never fully black out
  float asp2 = u_res.x / max(u_res.y, 1.0);
  vec2 fuv = gl_FragCoord.xy / u_res;
  fuv.x = (fuv.x - 0.5) * asp2 + 0.5;
  float vd = length(fuv - 0.5) / length(vec2(0.5 * asp2, 0.5));
  float vig = 1.0 - 0.4 * u_k4 * u_intensity * pow(clamp(vd * 0.94, 0.0, 1.0), 3.0);
  col *= clamp(vig, 0.12, 1.0);

  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
