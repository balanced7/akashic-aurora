#version 300 es
//! {"id": "mirror-hue", "name": "Mirror Hue", "author": "Vandor", "tags": ["video", "generative", "feedback", "kaleidoscope"], "params": [{"k": 1, "name": "segments", "default": 0.4}, {"k": 2, "name": "rotate", "default": 0.0}, {"k": 3, "name": "zoom", "default": 0.45}, {"k": 4, "name": "hue swing", "default": 0.5}, {"k": 5, "name": "trails", "default": 0.55}]}
precision highp float;

// Mirror Hue: a K-segment mirrored kaleidoscope of the clip, or, without video, of a u_prev
// feedback swirl seeded by a waveform ring, spectrum petals and an orbiting spark. The hue
// turns slowly and perceptually (HSV, never an RGB lerp), and bass breathes the zoom.
// Continuity rules: knobs set angles and amounts, never rates, because a rate times u_time jumps
// the whole picture when the knob moves. The hue rotation touches only fresh colour, never the
// feedback, where it would compound every frame.
// Contract: arsenal/PLAY-NIGHT-SPEC.md.
//   k1 segments   mirrored wedges, 2..12
//   k2 rotate     the kaleidoscope's angle (the clock adds a slow drift)
//   k3 zoom       base zoom into the clip
//   k4 hue swing  a radial hue wave on top of the slow full turn (one turn per 3 minutes)
//   k5 trails     feedback persistence (echoes with video, the swirl without)
// Texture reads per pixel: video 1 + prev 1 + audio 2 = 4.

uniform sampler2D u_video, u_prev, u_audio;
uniform vec2 u_res, u_video_res;
uniform float u_time, u_has_video, u_pulse, u_bass, u_beat, u_hue, u_intensity;
uniform float u_k1, u_k2, u_k3, u_k4, u_k5;

in vec2 v_uv;
out vec4 outColor;

vec3 rgb2hsv(vec3 c) {
  vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
  vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
  vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10;
  return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
  vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0);
  return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

void main() {
  vec2 res = max(u_res, vec2(1.0));
  float asp = res.x / res.y;
  float amt = clamp(u_intensity, 0.0, 1.0);
  float hv = clamp(u_has_video, 0.0, 1.0);
  float beat = clamp(u_beat, 0.0, 1.0);
  float t = u_time;
  float breath = clamp(0.6 * u_pulse + 0.4 * u_bass, 0.0, 1.0);  // bass, smoothed by the pulse envelope

  // ---- fold the plane into K mirrored wedges ----
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float r = length(p);
  float ang = atan(p.y, p.x + 1e-6 * step(r, 1e-6));  // atan(0, 0) is undefined
  float K = floor(mix(2.0, 12.0, clamp(u_k1, 0.0, 1.0)) + 0.5);
  float seg = 6.2831853 / K;
  float a = abs(mod(ang + clamp(u_k2, 0.0, 1.0) * 6.2831853 + t * 0.045, seg) - 0.5 * seg);
  vec2 q = r * vec2(cos(a), sin(a));

  // ---- hue: a slow full turn plus a radial swing; the wheel wraps, so fract never shows ----
  float hueTurn = u_hue / 360.0 + fract(t / 180.0) + clamp(u_k4, 0.0, 1.0) * 0.35 * sin(t * 0.11 - r * 3.0);

  // ---- video: sample the fold, mirror-repeat so the lookup never leaves the frame ----
  float va = u_video_res.x / max(u_video_res.y, 1.0);
  float zoom = mix(0.6, 1.9, clamp(u_k3, 0.0, 1.0)) * (1.0 + 0.18 * breath);
  vec2 drift = 0.16 * vec2(sin(t * 0.071), cos(t * 0.053));
  vec2 vq = vec2(q.x / max(va, 1e-3), q.y) / zoom + 0.5 + drift;
  vq = 1.0 - abs(1.0 - mod(vq, 2.0));
  vec2 vTexel = 0.5 / max(u_video_res, vec2(1.0));
  vec3 vid = texture(u_video, clamp(vq, vTexel, 1.0 - vTexel)).rgb;
  vec3 hsv = rgb2hsv(vid);
  hsv.x = fract(hsv.x + hueTurn);
  hsv.y = min(1.0, hsv.y * mix(1.0, 1.3, amt));
  vec3 vidCol = hsv2rgb(hsv);
  // greys have no hue to turn: lay a luma-true tint of the cycle over them
  float lum = dot(vid, vec3(0.2126, 0.7152, 0.0722));
  vec3 tint = hsv2rgb(vec3(fract(hueTurn + 0.6), 0.6, 1.0)) * lum * 1.2;
  vidCol = mix(vidCol, tint, 0.3 * amt * (1.0 - hsv.y));
  vidCol *= mix(0.55, 1.0, amt) * (1.0 + 0.2 * beat * amt);

  // ---- feedback swirl: sample slightly inward and rotated, so the past spirals outward ----
  float tw = 0.012 + 0.016 * breath;
  float cs = cos(tw), sn = sin(tw);
  vec2 pc = mat2(cs, sn, -sn, cs) * p * (0.985 - 0.012 * breath);
  vec2 pTexel = 0.5 / res;
  vec3 prev = texture(u_prev, clamp(pc / vec2(asp, 1.0) + 0.5, pTexel, 1.0 - pTexel)).rgb;
  float trails = clamp(u_k5, 0.0, 1.0);
  vec3 trail = max(prev * mix(0.88, 0.975, trails) - 1.0 / 255.0, 0.0);

  // ---- visualizer seed, drawn in the folded wedge so it carries the symmetry ----
  float an = a / (0.5 * seg);  // 0..1 across the half wedge
  // A narrow slice of the waveform per half wedge. The whole 512-sample frame squeezed into 30
  // degrees put a cycle every few pixels, which aliased into speckle that the feedback smeared.
  float wv = textureLod(u_audio, vec2(0.5 + (an - 0.5) * 0.18, 0.75), 0.0).r - 0.5;
  float ringR = 0.23 * (1.0 + 0.2 * breath) + wv * 0.07;
  float dR = abs(r - ringR) * res.y;
  float ring = clamp(1.8 + 1.2 * beat - dR, 0.0, 1.0) + exp(-dR / 6.0) * 0.4;
  float sv = textureLod(u_audio, vec2(clamp(r * 1.7, 0.002, 0.998), 0.25), 0.0).r;
  float petal = clamp((sv * sv * 0.45 * seg - a) * r * res.y + 0.5, 0.0, 1.0) * sv * smoothstep(0.6, 0.08, r);
  float sa = abs(mod(t * 0.37, seg) - 0.5 * seg);
  vec2 sp = (0.36 + 0.06 * sin(t * 0.23)) * vec2(cos(sa), sin(sa));
  float spark = exp(-length(q - sp) * res.y / (5.0 + 8.0 * beat));
  vec3 ringCol = hsv2rgb(vec3(fract(hueTurn + 0.08 * an), 0.65, 1.0));
  vec3 petalCol = hsv2rgb(vec3(fract(hueTurn + 0.12 + 0.2 * r), 0.8, 1.0));
  vec3 sparkCol = hsv2rgb(vec3(fract(hueTurn + 0.5), 0.35, 1.0));
  vec3 seed = (ringCol * ring + petalCol * petal * 0.8 + sparkCol * spark * 1.2) * mix(0.35, 1.0, amt);
  vec3 vis = trail + seed * 0.55;

  vec3 withVideo = max(vidCol, trail * trails * 0.6);  // bright moving parts leave swirling echoes
  vec3 col = mix(vis, withVideo, hv);

  float vd = r / length(vec2(0.5 * asp, 0.5));
  col *= 1.0 - 0.4 * hv * vd * vd * vd;
  vec3 over = max(col - 0.8, 0.0);
  col = min(col, vec3(0.8)) + 0.2 * tanh(over / 0.2);
  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
