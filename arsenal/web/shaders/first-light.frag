#version 300 es
//! {"name": "first-light", "kind": "sketch", "from": "built for the arsenal First Light build (T399 Lane A), not lifted from any single chunk", "note": "The First Light effect: sample u_video, letterbox it to contain, drive a beat pulse (zoom + glow + chromatic aberration) off u_pulse, rotate hue perceptually (RGB->HSV->rotate->RGB so luminance and saturation survive and no RGB-lerp grey-mud) by u_hue degrees, scale intensity by u_intensity, texture with u_bass/mid/high/flux. GLSL ES 3.00. #version sits on line 1 (a standalone .frag must: ANGLE rejects #version after any leading byte). Reuses house chunks: zoom-pulse (domain warp), tanh-tonemap + superlinear-highlight (tone shoulder), vignette-cubic (aspect-normalised frame), hash31 (static, time-invariant dither dust -- NOT per-frame grain, per the no-crawl floor). Deliberately does NOT reuse channel-rotate (it shifts hue and destroys the signal; we need a perceptual rotation).", "order": 50, "cat": "effect", "in": {"video": "sampler2D"}, "out": {"col": "vec4"}}
precision highp float;

// -- the contract with the shader (arsenal/FIRST-LIGHT-SPEC.md, section "Uniforms") --
uniform sampler2D u_video;
uniform vec2  u_res;          // canvas resolution, device pixels
uniform vec2  u_video_res;    // video's own resolution, for the contain/letterbox
uniform float u_time;         // media time, seconds
uniform float u_pulse;        // 0..1, beat energy (0.65*bass + 0.35*flux, smoothed)
uniform float u_hue;          // degrees 0..360, from the KeyLab knob
uniform float u_intensity;    // 0..1, overall effect strength
uniform float u_bass, u_mid, u_high, u_flux;  // 0..1 per-frame features

in vec2 v_uv;
out vec4 outColor;

// --- house helper: cheap static hash (hash31) ---
float h31(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453123); }

// --- perceptual hue rotation: RGB -> HSV, rotate hue, HSV -> RGB ---
// Colour eases the perceptual way (house ceiling): luminance and saturation survive a hue
// change; an RGB lerp or swizzle passes through desaturated grey-brown (a "fault"). This is the
// full rotation the spec asks for, not a two-endpoint ease. (hc2/rgb2hsv+hsv2rgb, Iq's form.)
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
vec3 hsv_rotate(vec3 c, float deg) {
  vec3 hsv = rgb2hsv(c);
  hsv.x = fract(hsv.x + deg / 360.0);   // rotate the hue, wrap 0..1
  return hsv2rgb(hsv);
}

void main() {
  // -- letterbox: "contain" the video inside the canvas, black bars, itself (no external quad) --
  float canvas_aspect = u_res.x / u_res.y;
  float video_aspect  = u_video_res.x / u_video_res.y;

  // Map v_uv (which already has origin bottom-left, per the page's UNPACK_FLIP_Y_WEBGL) into
  // the video's "contained" rect. The page guarantees video_aspect>0 for a real clip.
  vec2 uv = v_uv;
  if (video_aspect > canvas_aspect) {
    // video is wider: fit width, letterbox top/bottom
    float h = canvas_aspect / video_aspect;      // fraction of canvas height the video occupies
    float y0 = 0.5 - 0.5 * h;
    float y1 = 0.5 + 0.5 * h;
    if (uv.y < y0 || uv.y > y1) { outColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
    uv.y = (uv.y - y0) / (y1 - y0);
  } else {
    // video is taller (or equal): fit height, letterbox left/right
    float w = video_aspect / canvas_aspect;      // fraction of canvas width the video occupies
    float x0 = 0.5 - 0.5 * w;
    float x1 = 0.5 + 0.5 * w;
    if (uv.x < x0 || uv.x > x1) { outColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
    uv.x = (uv.x - x0) / (x1 - x0);
  }

  // -- domain warp for the beat: zoom-pulse's breathing scale, applied to the UV (the cheapest
  //    way to give a static source a heartbeat, and it only touches magnitude). Centre-origin. --
  vec2 c = uv - 0.5;
  float zoom = 1.0 + 0.16 * u_pulse * sin(u_time * 1.3);   // pulsing zoom, inherited from zoom-pulse
  c /= zoom;
  // built-in aberration on the beat, for taste: scale R and B channels differently by a tiny
  // amount so loud transients fringe the edges -- constant, no per-frame crawl, cheap (one extra sample pair).
  float aber = 0.004 * u_pulse;
  vec2 cr = c * (1.0 + aber);
  vec2 cb = c * (1.0 - aber);
  vec2 cuv = c + 0.5;

  // -- sample the video (three times for the chromatic fringe; centre sample is the main one) --
  vec3 col;
  vec3 col_r = texture(u_video, cr + 0.5).rgb;
  vec3 col_g = texture(u_video, cuv).rgb;
  vec3 col_b = texture(u_video, cb + 0.5).rgb;
  col = vec3(col_r.r, col_g.g, col_b.b);   // fringe only where the channels overlap the beat

  // -- pulse glow: lift the image toward a subtle warm bloom on the beat, scaled by intensity --
  float pulse_glow = u_pulse * 0.30 * u_intensity;
  col += col * pulse_glow;

  // -- perceptual hue rotation (the KeyLab knob), gated so 0 deg is a no-op --
  if (u_hue > 0.5 || u_hue < -0.5) {
    col = hsv_rotate(col, u_hue);
  }

  // -- intensity: scale everything (brightness), 0..1 --
  col *= mix(0.15, 1.0, u_intensity);

  // -- tone: superlinear highlight then the tanh shoulder (house order: square-then-shoulder,
  //    so the crests bloom and the shoulder never re-expands). tanh is per-component here
  //    because GLSL ES 3.00 has no vec3-overload of the hyperbolic functions. --
  col += col * col * 0.85;      // superlinear-highlight
  col = vec3(tanh(col.r), tanh(col.g), tanh(col.b));   // tanh-tonemap, [0,inf)->[0,1)

  // -- texture from the other bands: subtle time-invariant dust, a gentle baseline lift from
  //    mid/high, and a flux shimmer. Static per-pixel (no per-frame crawl): the hash is keyed
  //    only on a fixed per-slot uv, never on u_time. --
  float dust = h31(vec3(floor(gl_FragCoord.xy), 0.0));   // static noise, banded highp-safe enough for dust
  col += (dust - 0.5) * 0.018 * u_flux;                  // flux makes a faint static grain
  col += 0.05 * u_mid;                                    // subtle mid-derived lift
  col += 0.03 * u_high;                                   // air from the highs

  // -- frame: aspect-corrected cubic vignette (house fix: normalise by the real corner) --
  float asp = u_res.x / u_res.y;
  vec2 vuv = gl_FragCoord.xy / u_res;
  vuv.x = (vuv.x - 0.5) * asp + 0.5;
  float vd = length(vuv - 0.5) / length(vec2(0.5 * asp, 0.5));
  col *= mix(1.0, 1.0 - pow(clamp(vd * 0.94, 0.0, 1.0), 3.0), 0.45 * u_intensity);

  outColor = vec4(col, 1.0);
}
