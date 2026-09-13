#version 300 es
//! {"id": "halftone-pop", "name": "Halftone Pop", "author": "Vandor", "tags": ["video", "generative", "audio", "print"], "params": [{"k": 1, "name": "cell", "default": 0.4}, {"k": 2, "name": "levels", "default": 0.35}, {"k": 3, "name": "angle", "default": 0.33}, {"k": 4, "name": "sparkle", "default": 0.6}, {"k": 5, "name": "paper", "default": 0.1}]}
precision highp float;

// Halftone Pop: a rotated halftone screen over the letterboxed clip (or a drifting generative
// field without video), posterized into two pop ramps picked per dot by the source colour: warm
// (violet -> magenta -> red -> yellow) and cool (deep blue -> cyan). The mid band sets dot size,
// the beat swells the dots, and the high band lights stars between the dots. Each star cell is
// chosen by a static hash, so the same cells glint for the same loudness; they twinkle on smooth
// sines and never crawl.
// Each pixel evaluates its 2x2 nearest dots, so a large dot merges into its neighbours cleanly.
// Contract: arsenal/PLAY-NIGHT-SPEC.md.
//   k1 cell     dot pitch (scales with canvas height)
//   k2 levels   posterize levels, 3..6
//   k3 angle    screen angle, 0..45 degrees
//   k4 sparkle  how many stars the high band may light
//   k5 paper    paper tone, from ink-black to cream
// Texture reads per pixel: 4 (one per nearest dot centre).

uniform sampler2D u_video;
uniform vec2 u_res, u_video_res;
uniform float u_time, u_has_video, u_beat, u_bass, u_mid, u_high, u_level, u_hue, u_intensity;
uniform float u_k1, u_k2, u_k3, u_k4, u_k5;

in vec2 v_uv;
out vec4 outColor;

float hash12(vec2 p) {  // static hash without sine, stable for large inputs
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

vec3 hsv2rgb(vec3 c) {
  vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0);
  return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

vec2 video_uv(vec2 uv) {  // screen uv -> video uv; outside 0..1 means no video there
  float ca = u_res.x / max(u_res.y, 1.0), va = u_video_res.x / max(u_video_res.y, 1.0);
  vec2 s = va > ca ? vec2(1.0, ca / max(va, 1e-4)) : vec2(va / max(ca, 1e-4), 1.0);
  return (uv - 0.5) / max(s, vec2(1e-4)) + 0.5;
}

// Tone and coolness at a dot centre. Tone is the clip's luma, or in visualizer mode three
// drifting blobs, a bass-lifted ripple and a slow wash. Coolness picks the ramp: cyan, green and
// blue sources (or wherever the second blob dominates) go cool, everything else warm.
// Every time term is a constant-rate sine.
vec2 tone_at(vec2 suv, vec2 res) {
  vec2 vu = video_uv(suv);
  vec2 inR = step(vec2(0.0), vu) * step(vu, vec2(1.0));
  vec2 texel = 0.5 / max(u_video_res, vec2(1.0));
  vec3 v = textureLod(u_video, clamp(vu, texel, 1.0 - texel), 0.0).rgb * (inR.x * inR.y);
  float lv = dot(v, vec3(0.2126, 0.7152, 0.0722));
  float chroma = max(max(v.r, v.g), v.b) - min(min(v.r, v.g), v.b);
  float cv = smoothstep(0.05, 0.25, max(v.g, v.b) - v.r) * smoothstep(0.06, 0.16, chroma);

  float t = u_time;
  vec2 q = (suv - 0.5) * vec2(res.x / res.y, 1.0);
  vec2 b1 = 0.42 * vec2(sin(t * 0.31), cos(t * 0.23));
  vec2 b2 = 0.36 * vec2(cos(t * 0.19 + 2.0), sin(t * 0.27 + 1.0));
  vec2 b3 = 0.30 * vec2(sin(t * 0.13 + 4.0), sin(t * 0.17 + 3.0));
  float e1 = exp(-dot(q - b1, q - b1) * 7.0);
  float e2 = 0.8 * exp(-dot(q - b2, q - b2) * 10.0);
  float e3 = 0.7 * exp(-dot(q - b3, q - b3) * 14.0);
  float g = e1 + e2 + e3;
  float rr = length(q);
  g += (0.2 + 0.4 * clamp(u_bass, 0.0, 1.0)) * (0.5 + 0.5 * sin(rr * 16.0 - t * 1.3)) * exp(-rr * 1.8);
  g += 0.1 * (0.5 + 0.5 * sin(q.x * 2.0 + q.y * 1.3 + t * 0.2));
  g *= 0.8 + 0.35 * clamp(u_level, 0.0, 1.0);
  float cf = smoothstep(0.02, 0.12, e2 - max(e1, e3));

  float hv = clamp(u_has_video, 0.0, 1.0);
  return vec2(mix(clamp(g, 0.0, 1.0), lv, hv), mix(cf, cv, hv));
}

void main() {
  vec2 res = max(u_res, vec2(1.0));
  float amt = clamp(u_intensity, 0.0, 1.0);
  float beat = clamp(u_beat, 0.0, 1.0);
  float hueT = u_hue / 360.0;

  // ---- a rotated dot lattice, in device pixels ----
  float cellPx = max(5.0, floor(mix(10.0, 36.0, clamp(u_k1, 0.0, 1.0)) * res.y / 1080.0 + 0.5));
  float ang = clamp(u_k3, 0.0, 1.0) * 0.7853982;
  float ca = cos(ang), sa = sin(ang);
  mat2 R = mat2(ca, sa, -sa, ca);   // grid -> screen
  mat2 Ri = mat2(ca, -sa, sa, ca);  // screen -> grid
  vec2 g = (Ri * (gl_FragCoord.xy - 0.5 * res)) / cellPx;
  vec2 base = floor(g - 0.5);       // the 2x2 nearest dot centres are base + 0.5 .. base + 1.5

  float L = floor(mix(3.0, 6.0, clamp(u_k2, 0.0, 1.0)) + 0.5);
  float sizeMul = mix(0.7, 1.2, clamp(u_mid, 0.0, 1.0)) * (1.0 + 0.25 * beat * amt);

  vec3 inkSum = vec3(0.0);
  float covSum = 0.0;
  for (int j = 0; j < 2; j++) {
    for (int i = 0; i < 2; i++) {
      vec2 cc = base + vec2(float(i), float(j)) + 0.5;
      vec2 tc = tone_at((R * (cc * cellPx) + 0.5 * res) / res, res);
      // posterize with narrow soft steps: flat levels, no flicker where a tone sits on a boundary
      float tl = clamp(tc.x, 0.0, 1.0) * L - 0.5;
      float lvl = floor(tl);
      float lv = clamp(lvl + smoothstep(0.35, 0.65, tl - lvl), 0.0, L - 1.0);
      float lt = lv / max(L - 1.0, 1.0);
      float rad = min(cellPx * 0.5 * (0.24 + 0.86 * sqrt((lv + 0.5) / L)) * sizeMul, cellPx * 0.74);
      float cov = clamp(rad - length(g - cc) * cellPx + 0.5, 0.0, 1.0);
      // the two ramps blend in HSV the short way round over a narrow band, so a boundary never greys out
      float ramp = smoothstep(0.4, 0.6, tc.y);
      float hw = 0.74 + 0.44 * lt, hc = 0.66 - 0.17 * lt;
      float dh = fract(hc - hw + 0.5) - 0.5;
      vec3 ink = hsv2rgb(vec3(fract(hw + dh * ramp + hueT),
                              mix(mix(0.92, 0.78, lt), mix(0.95, 0.55, lt), ramp),
                              mix(mix(0.5, 1.0, lt), mix(0.55, 1.0, lt), ramp)));
      inkSum += ink * cov;
      covSum += cov;
    }
  }
  vec3 ink = inkSum / max(covSum, 1e-4);
  float cov = clamp(covSum, 0.0, 1.0);

  vec3 paper = mix(vec3(0.03, 0.025, 0.055), vec3(0.97, 0.93, 0.84), clamp(u_k5, 0.0, 1.0));
  paper *= 0.97 + 0.05 * hash12(floor(gl_FragCoord.xy));  // static paper tooth, never per frame
  vec3 col = mix(paper, ink * mix(0.35, 1.0, amt) * (1.0 + 0.3 * beat * amt), cov);

  // ---- sparkle: stars on the lattice corners; the high band sets how many, static hashes pick which ----
  vec2 g2 = g + 0.5;
  vec2 sid = floor(g2);
  vec2 sf = (g2 - sid - 0.5) * cellPx;  // device px from the corner
  float hs = hash12(sid + 71.3);
  float thr = 1.0 - clamp(u_high, 0.0, 1.0) * 0.3 * clamp(u_k4, 0.0, 1.0);
  float on = smoothstep(thr, thr + 0.015, hs);
  float tw = 0.6 + 0.4 * sin(u_time * (2.0 + 3.0 * fract(hs * 13.7)) + hs * 60.0);
  vec2 aq = abs(sf) / (cellPx * (0.42 + 0.06 * beat));  // spikes stay inside half a cell
  float star = max(max(0.0, 1.0 - (aq.x * 7.0 + aq.y)), max(0.0, 1.0 - (aq.y * 7.0 + aq.x)));
  star = star * star + max(0.0, 1.0 - length(aq) * 4.0);
  vec3 sparkCol = hsv2rgb(vec3(fract(0.5 + hueT), 0.3, 1.0));
  col += sparkCol * star * on * tw * (1.1 + 0.8 * beat) * mix(0.4, 1.0, amt);

  vec2 vc = (v_uv - 0.5) * vec2(res.x / res.y, 1.0);
  float vd = length(vc) / length(vec2(0.5 * res.x / res.y, 0.5));
  col *= 1.0 - 0.3 * vd * vd * vd;
  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
