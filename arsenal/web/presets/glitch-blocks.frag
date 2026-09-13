#version 300 es
//! {"id": "glitch-blocks", "name": "Glitch Blocks", "author": "Vandor", "tags": ["video", "generative", "audio", "glitch"], "params": [{"k": 1, "name": "blocks", "default": 0.45}, {"k": 2, "name": "shift", "default": 0.5}, {"k": 3, "name": "rgb split", "default": 0.45}, {"k": 4, "name": "tears", "default": 0.5}, {"k": 5, "name": "rest", "default": 0.3}]}
precision highp float;

// Glitch Blocks: flux-driven block displacement, RGB split and scanline tears on the
// letterboxed clip, or on a generative field (gradient, grid, striped sun) without video.
// u_beat opens a short burst: more blocks move, further, with a wider split and torn bands.
// At rest only a few blocks drift, a pixel or two apart, so the picture stays readable.
// No per-frame crawl: every moving term is a sine of u_time at a constant rate, with phases
// from static per-block hashes. Nothing hashes u_time, and no rate is multiplied by a uniform.
// Contract: arsenal/PLAY-NIGHT-SPEC.md.
//   k1 blocks     block grid, coarse to fine
//   k2 shift      displacement distance
//   k3 rgb split  channel separation
//   k4 tears      scanline tears and scanline depth
//   k5 rest       how much glitch survives in silence
// Texture reads per pixel: 3 (one per colour channel).

uniform sampler2D u_video;
uniform vec2 u_res, u_video_res;
uniform float u_time, u_has_video, u_beat, u_flux, u_bass, u_mid, u_hue, u_intensity;
uniform float u_k1, u_k2, u_k3, u_k4, u_k5;

in vec2 v_uv;
out vec4 outColor;

float hash12(vec2 p) {  // static hash without sine, stable for large inputs
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

// Smooth wobble in -1..1: rates and phases come from a static hash, so it slides, never re-rolls.
float wob(float h, float t) {
  return sin(t * (0.9 + 1.9 * h) + h * 43.0) * sin(t * (0.31 + 0.8 * fract(h * 7.13)) + h * 17.0);
}

vec2 video_uv(vec2 uv) {  // screen uv -> video uv; outside 0..1 means no video there
  float ca = u_res.x / max(u_res.y, 1.0), va = u_video_res.x / max(u_video_res.y, 1.0);
  vec2 s = va > ca ? vec2(1.0, ca / max(va, 1e-4)) : vec2(va / max(ca, 1e-4), 1.0);
  return (uv - 0.5) / max(s, vec2(1e-4)) + 0.5;
}

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

vec3 video_at(vec2 suv) {
  vec2 vu = video_uv(suv);
  vec2 inR = step(vec2(0.0), vu) * step(vu, vec2(1.0));
  vec2 texel = 0.5 / max(u_video_res, vec2(1.0));
  return textureLod(u_video, clamp(vu, texel, 1.0 - texel), 0.0).rgb * (inR.x * inR.y);
}

// Visualizer source: a slow indigo-violet gradient, a faint cyan grid and a striped coral sun,
// so displaced blocks have edges to show. AA widths are analytic: fwidth here would explode at
// block edges, where the displacement jumps (the shredded-rows trap).
vec3 field_at(vec2 p, vec2 res) {
  float asp = res.x / res.y;
  vec2 q = (p - 0.5) * vec2(asp, 1.0);
  float t = u_time;
  float hueOff = u_hue / 360.0;
  float a = 0.5 + 0.5 * sin(q.x * 2.1 + t * 0.21 + sin(q.y * 1.7 - t * 0.13) * 1.3);
  float b = 0.5 + 0.5 * sin(q.y * 2.6 - t * 0.17 + sin(q.x * 1.3 + t * 0.11) * 1.1);
  vec3 col = hsv2rgb(vec3(fract(0.66 + 0.1 * a - 0.06 * b + hueOff), 0.7,
                          0.12 + 0.3 * b + 0.12 * clamp(u_mid, 0.0, 1.0)));

  float gy = abs(fract(p.y * 16.0 + 0.5) - 0.5) / 16.0 * res.y;  // device px to the nearest rule
  float gx = abs(fract(q.x * 8.0 + 0.5) - 0.5) / 8.0 * res.y;
  float grid = max(clamp(1.2 - gy, 0.0, 1.0), clamp(1.2 - gx, 0.0, 1.0));
  col += hsv2rgb(vec3(fract(0.52 + hueOff), 0.6, 1.0)) * grid * 0.22;

  vec2 sq = q - vec2(0.0, 0.04);
  float sunR = 0.25 * (1.0 + 0.08 * clamp(u_bass, 0.0, 1.0));
  float sd = (sunR - length(sq)) * res.y;             // device px inside the sun's edge
  float sy = sq.y / sunR;                               // -1..1 inside the sun
  float bandW = 7.0 / (sunR * res.y);                   // one device px in band units
  float cutW = clamp(-sy, 0.0, 1.0) * 0.55;             // the stripes widen toward the bottom
  float cut = smoothstep(cutW - bandW, cutW + bandW, fract(sy * 7.0));
  float sun = clamp(sd + 0.5, 0.0, 1.0) * mix(1.0, cut, step(sy, 0.0));
  vec3 sunCol = hsv2rgb(vec3(fract(0.02 + 0.08 * clamp(sy * 0.5 + 0.5, 0.0, 1.0) + hueOff), 0.78, 1.0));
  col = mix(col, sunCol, sun * 0.92);
  col += sunCol * exp(-max(-sd, 0.0) / (res.y * 0.05)) * 0.12;
  return col;
}

void main() {
  vec2 res = max(u_res, vec2(1.0));
  vec2 uv = v_uv;
  float amt = clamp(u_intensity, 0.0, 1.0);
  float burst = clamp(u_beat, 0.0, 1.0);
  float flux = clamp(u_flux, 0.0, 1.0);
  float rest = clamp(u_k5, 0.0, 1.0);
  float hv = clamp(u_has_video, 0.0, 1.0);
  float t = u_time;
  float act = clamp(rest * 0.3 + flux * 0.45 + burst * 0.9, 0.0, 1.0) * amt;

  // ---- blocks: a 2:1 grid with some cells merged 2x2; each block has a static direction ----
  float asp = res.x / res.y;
  float rows = floor(mix(5.0, 26.0, clamp(u_k1, 0.0, 1.0)) + 0.5);
  vec2 grid = vec2(max(1.0, floor(rows * asp * 0.5 + 0.5)), rows);
  vec2 fine = floor(uv * grid);
  vec2 coarse = floor(uv * grid * 0.5);
  vec2 cid = mix(fine, coarse + 911.0, step(0.55, hash12(coarse + 3.7)));
  float hc = hash12(cid + 17.0);
  float thr = 1.0 - 0.62 * act;  // more activity lowers the bar for a block to move
  float sel = smoothstep(thr, thr + 0.05, 0.5 + 0.5 * wob(hc, t));
  vec2 dir = vec2(hash12(cid + 5.3) - 0.5, (hash12(cid + 9.1) - 0.5) * 0.3);
  vec2 disp = dir * sel * (0.04 + 0.26 * burst + 0.08 * flux) * mix(0.2, 1.2, clamp(u_k2, 0.0, 1.0)) * amt;

  // ---- scanline tears: bands slide sideways, with a fine ripple inside ----
  float tears = clamp(u_k4, 0.0, 1.0);
  float hb = hash12(vec2(floor(uv.y * 48.0), 91.7));
  float tthr = 1.0 - (0.06 * rest + 0.5 * burst + 0.22 * flux) * amt;
  float tear = smoothstep(tthr, tthr + 0.03, 0.5 + 0.5 * wob(hb, t * 1.7)) * step(0.001, tears);
  float tearShift = (hb - 0.5) * tear * (0.03 + 0.16 * burst) * tears * amt * 2.0
                  + sin(gl_FragCoord.y * 0.45 + t * 5.0) * 0.0015 * tear * tears;
  vec2 suv = uv + disp + vec2(tearShift, 0.0);

  // ---- RGB split: one tap per channel ----
  float splitPx = (0.8 + 2.0 * rest + 18.0 * burst + 6.0 * flux + 10.0 * sel * burst)
                * clamp(u_k3, 0.0, 1.0) * amt;
  vec2 so = vec2(splitPx / res.x, splitPx * 0.2 / res.y);
  vec3 cR = mix(field_at(suv + so, res), video_at(suv + so), hv);
  vec3 cG = mix(field_at(suv, res), video_at(suv), hv);
  vec3 cB = mix(field_at(suv - so, res), video_at(suv - so), hv);
  vec3 col = vec3(cR.r, cG.g, cB.b);

  // ---- corrupted blocks during a burst: channel rotation and a coarse posterize ----
  col = mix(col, col.brg, sel * burst * amt * step(0.62, hc) * 0.85);
  col = mix(col, floor(col * 5.0 + 0.5) / 5.0, sel * burst * amt);
  col += tear * tears * (0.04 + 0.1 * burst) * vec3(0.75, 0.9, 1.0);

  if (hv > 0.5 && abs(u_hue) > 0.5) {  // the field takes u_hue in its own palette
    vec3 hsv = rgb2hsv(clamp(col, 0.0, 1.0));
    hsv.x = fract(hsv.x + u_hue / 360.0);
    col = hsv2rgb(hsv);
  }

  // ---- static scanlines (fixed per device row, never per frame) and a framing vignette ----
  float scan = step(1.0, mod(gl_FragCoord.y, 3.0));
  col *= mix(1.0, 0.82 + 0.18 * scan, 0.35 + 0.65 * tears);
  float vd = length((uv - 0.5) * vec2(asp, 1.0)) / length(vec2(0.5 * asp, 0.5));
  col *= (1.0 - 0.35 * vd * vd * vd) * mix(0.65, 1.0, amt);
  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
