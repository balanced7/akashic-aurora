#version 300 es
//! {"id": "scope-bars", "name": "Scope Bars", "author": "Vandor", "tags": ["audio", "video", "generative", "feedback"], "params": [{"k": 1, "name": "bars", "default": 0.33}, {"k": 2, "name": "height", "default": 0.55}, {"k": 3, "name": "scope", "default": 0.6}, {"k": 4, "name": "trails", "default": 0.6}, {"k": 5, "name": "backdrop", "default": 0.4}]}
precision highp float;

// Scope Bars: MilkDrop-style log spectrum bars and a waveform scope drawn from u_audio.
// With video they sit over the letterboxed clip, dimmed by `backdrop`. In visualizer mode they
// sit over this preset's own u_prev, which rises, spreads and decays (multiply plus subtract,
// so an 8-bit buffer still clears). The beat brightens the bars and thickens the scope.
// Silence: a slow idle wave along the bar floor and a flat, glowing scope line.
// Contract: arsenal/PLAY-NIGHT-SPEC.md (uniforms v1, craft floors).
//   k1 bars      bar count, 24..96
//   k2 height    bar height gain
//   k3 scope     scope amplitude and brightness (0 hides it)
//   k4 trails    visualizer-mode trail persistence
//   k5 backdrop  how far the video dims behind the bars
// Texture reads per pixel: video 1 + prev 1 + spectrum 2 + waveform 3 = 7.
// u_hue rotates only freshly drawn colour, never the feedback: a rotation inside a feedback
// loop compounds every frame and strobes.

uniform sampler2D u_video, u_prev, u_audio;
uniform vec2 u_res, u_video_res;
uniform float u_time, u_has_video, u_beat, u_pulse, u_hue, u_intensity;
uniform float u_k1, u_k2, u_k3, u_k4, u_k5;

in vec2 v_uv;
out vec4 outColor;

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

void main() {
  vec2 res = max(u_res, vec2(1.0));
  vec2 uv = v_uv;
  float amt = mix(0.3, 1.0, clamp(u_intensity, 0.0, 1.0));
  float beat = clamp(u_beat, 0.0, 1.0);
  float hueOff = u_hue / 360.0;
  float hasVideo = clamp(u_has_video, 0.0, 1.0);

  // ---- backdrop: the letterboxed clip, or the rising trail ----
  vec2 vu = video_uv(uv);
  vec2 inRect = step(vec2(0.0), vu) * step(vu, vec2(1.0));
  vec2 vTexel = 0.5 / max(u_video_res, vec2(1.0));
  vec3 vid = texture(u_video, clamp(vu, vTexel, 1.0 - vTexel)).rgb * (inRect.x * inRect.y);
  if (abs(u_hue) > 0.5) {
    vec3 hsv = rgb2hsv(vid);
    hsv.x = fract(hsv.x + hueOff);
    vid = hsv2rgb(hsv);
  }
  float backdrop = clamp(u_k5, 0.0, 1.0);
  vid *= mix(1.0, 0.5, backdrop) * mix(1.0, 0.55 + 0.45 * smoothstep(0.02, 0.7, uv.y), backdrop);

  vec2 pTexel = 0.5 / res;
  vec2 pv = vec2(0.5 + (uv.x - 0.5) * 0.996, uv.y - 0.0026);  // content rises and spreads a touch
  vec3 prev = texture(u_prev, clamp(pv, pTexel, 1.0 - pTexel)).rgb;
  vec3 trail = max(prev * mix(0.86, 0.975, clamp(u_k4, 0.0, 1.0)) - 1.0 / 255.0, 0.0);

  vec3 col = mix(trail, vid, hasVideo);

  // ---- spectrum bars (row 0 is already log-spaced, so even columns are log bars) ----
  const float X0 = 0.03, X1 = 0.97, BASE = 0.1;
  float N = floor(mix(24.0, 96.0, clamp(u_k1, 0.0, 1.0)) + 0.5);
  float bx = (uv.x - X0) / (X1 - X0);
  float inX = step(0.0, bx) * step(bx, 1.0);
  float cellF = clamp(bx, 0.0, 1.0) * N;
  float id = min(floor(cellF), N - 1.0);
  float fx = cellF - id;  // 0..1 across the bar's cell
  float spec = max(textureLod(u_audio, vec2((id + 0.3) / N, 0.25), 0.0).r,
                   textureLod(u_audio, vec2((id + 0.7) / N, 0.25), 0.0).r);
  float idle = 0.009 + 0.008 * (0.5 + 0.5 * sin(u_time * 0.9 - id * 0.45));
  float tilt = 0.85 + 0.3 * (id + 0.5) / N;  // highs read a touch taller
  float h = idle + pow(max(spec, 1e-5), 1.35) * mix(0.22, 0.7, clamp(u_k2, 0.0, 1.0)) * tilt;
  float top = BASE + h;

  float barPx = (X1 - X0) * res.x / N;
  float covX = clamp((0.38 - abs(fx - 0.5)) * barPx + 0.5, 0.0, 1.0) * inX;  // analytic AA, no fwidth of an id
  float dTop = (top - uv.y) * res.y;    // device px below the bar top
  float dBase = (uv.y - BASE) * res.y;  // device px above the floor
  float cov = covX * clamp(dTop + 0.5, 0.0, 1.0) * clamp(dBase + 0.5, 0.0, 1.0);
  float ledGap = step(1.0, mod(gl_FragCoord.y, max(4.0, floor(res.y / 140.0))));
  float cap = covX * clamp(1.0 - abs(dTop - 1.5) / 2.0, 0.0, 1.0) * step(0.0, dBase);
  float cellMask = smoothstep(0.5, 0.2, abs(fx - 0.5)) * inX;  // glow fades to 0 at cell edges: no seams
  float glow = exp(-max(-dTop, 0.0) / (5.0 + 12.0 * beat)) * cellMask * step(0.0, dBase) * step(dTop, 0.0);
  float below = BASE - uv.y;
  float refl = covX * step(0.0, below) * clamp((top - (BASE + below * 2.2)) * res.y + 0.5, 0.0, 1.0)
             * (1.0 - clamp(below / BASE, 0.0, 1.0)) * 0.3;

  float ht = clamp((uv.y - BASE) / 0.62, 0.0, 1.0);
  vec3 barCol = hsv2rgb(vec3(fract(0.6 + 0.42 * ht + hueOff), mix(0.82, 0.6, ht), 1.0));  // blue -> violet -> coral, in hue space
  vec3 reflCol = hsv2rgb(vec3(fract(0.6 + hueOff), 0.8, 1.0));
  float bright = (0.8 + 0.9 * beat) * amt;

  col = mix(col, barCol * bright * mix(0.55, 1.0, ledGap), cov * 0.92);
  col += mix(barCol, vec3(1.0), 0.5) * cap * 0.7 * bright;
  col += barCol * glow * 0.3 * bright + reflCol * refl * bright;

  // ---- waveform scope ----
  const float DX = 1.5 / 512.0;
  float sc = clamp(u_k3, 0.0, 1.0);
  float wx = clamp(uv.x, DX + 0.001, 1.0 - DX - 0.001);
  float w0 = textureLod(u_audio, vec2(wx, 0.75), 0.0).r - 0.5;
  float wl = textureLod(u_audio, vec2(wx - DX, 0.75), 0.0).r - 0.5;
  float wr = textureLod(u_audio, vec2(wx + DX, 0.75), 0.0).r - 0.5;
  float amp = 0.17 * sc;
  float yLine = 0.78 + w0 * 2.0 * amp;
  float slope = (wr - wl) * 2.0 * amp * res.y / (2.0 * DX * res.x);  // dy/dx in device px
  float dist = abs(uv.y - yLine) * res.y / sqrt(1.0 + slope * slope);
  float edge = smoothstep(0.0, 0.05, uv.x) * smoothstep(1.0, 0.95, uv.x);
  float scope = (clamp(1.2 + 1.3 * beat - dist, 0.0, 1.0) + exp(-dist / (4.0 + 6.0 * clamp(u_pulse, 0.0, 1.0))) * 0.5)
              * edge * step(0.001, sc) * mix(0.45, 1.0, sc);
  vec3 scopeCol = hsv2rgb(vec3(fract(0.53 + hueOff), 0.35, 1.0));
  col += scopeCol * scope * (0.7 + 0.6 * beat) * amt;

  // ---- highlight shoulder only (midtones untouched), clamped for the feedback buffer ----
  vec3 over = max(col - 0.8, 0.0);
  col = min(col, vec3(0.8)) + 0.2 * tanh(over / 0.2);
  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
