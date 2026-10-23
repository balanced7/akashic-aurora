#version 300 es
//! {"id": "vj-laser-cathedral", "name": "VJ Laser Cathedral", "author": "Vandor", "tags": ["vj", "generative", "laser", "beat", "pads"], "params": [{"k": 1, "name": "sweep", "default": 0.55}, {"k": 2, "name": "haze", "default": 0.55}, {"k": 3, "name": "beam width", "default": 0.4}, {"k": 4, "name": "fan spread", "default": 0.55}, {"k": 5, "name": "trails", "default": 0.45}, {"k": 6, "name": "arches", "default": 0.45}]}
precision highp float;

// Laser Cathedral (arsenal/web/vj.html, Play-loadable). A rig of twelve laser heads laid out like the KeyLab's pads, three
// rows of four, behind a nave of pointed arches. Every head throws one beam at a moving focus, odd heads at one focus and
// even heads at its mirror, so the beams scissor; the foci step on every predicted beat (an eased snap in the first half
// of the beat, then a hold), and a chord change kicks them on. A pad fires its head as a fan: velocity sets the beam count
// (3-12) and how wide the fan opens. The beams are neon lines (arsenal/web/glsl/groups/neon-line.glsl, reduced here): a
// pixel-wide hot core that whitens with energy inside a Lorentzian halo, and the halo is dimmed and lit by a slow haze, so
// the light looks like it is in smoke. Trails come from u_prev (max, never add: crossings stay crisp). In Play the bands
// stand in for the pads: the top row listens to the highs, the middle to the mids, the bottom to the bass.

uniform sampler2D u_video;   // the VJ page: its 16x6 VJ strip (u_has_video stays 0); Play: the video or a 1x1 black texture
uniform sampler2D u_prev;
uniform vec2  u_res;
uniform float u_time;
uniform float u_has_video;
uniform float u_beat, u_level, u_bass, u_mid, u_high;
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
float gPhase, gPulse, gCount, gTension, gChordPulse;

vec4 vjAt(int x, int y) { return texelFetch(u_video, ivec2(x, y), 0); }

vec3 hueLinear(float turns) {
  vec3 c = clamp(abs(fract(turns + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0, 0.0, 1.0);
  return c * c;
}

void vjLoad() {
  gHost = u_has_video < 0.5 && textureSize(u_video, 0) == ivec2(16, 6);
  if (gHost) {
    for (int i = 0; i < 4; i++) gPal[i] = vjAt(i, 2).rgb;
    vec4 beat = vjAt(12, 0);
    gPhase = beat.x; gPulse = beat.y; gCount = beat.w;
    gTension = vjAt(14, 0).z;
    gChordPulse = vjAt(15, 0).x;
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.53); gPal[1] = hueLinear(h + 0.80); gPal[2] = hueLinear(h + 0.64); gPal[3] = hueLinear(h + 0.03);
    float beats = u_time * 2.0;                 // a 120 bpm clock to sweep on, without a beat tracker
    gPhase = fract(beats); gPulse = u_beat; gCount = mod(floor(beats), 64.0);
    gTension = 0.0;
    gChordPulse = 0.0;
  }
}

vec3 padColour(int i) { return gHost ? vjAt(i, 3).rgb : gPal[i - 4 * (i / 4)]; }

vec2 padLevel(int i) {          // (envelope, velocity)
  if (gHost) return vjAt(i, 0).xy;
  float band = i < 4 ? u_high : (i < 8 ? u_mid : u_bass);
  float gate = smoothstep(0.6, 0.98, 0.5 + 0.5 * sin(u_time * 0.9 + float(i) * 2.4));
  return vec2(smoothstep(0.55, 0.9, band) * gate, band);
}

// ------------------------------------------------------------------------------------------------- light parts --
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
vec3 hotCore(vec3 tint, float heat) {      // light-glow glowHotCore
  float h = max(heat, 0.0);
  vec3 hue = max(tint, vec3(0.0));
  float peak = max(hue.r, max(hue.g, hue.b));
  return h * mix(hue, vec3(peak), h * h / (1.0 + h * h));
}
float aaWire(float dPx, float widthPx) {   // draw2-aa aaWire, in pixels
  float drawn = max(widthPx, 1.0);
  return clamp(0.5 * drawn + 0.5 - dPx, 0.0, 1.0) * (max(widthPx, 0.0) / drawn);
}
// one neon line's light: (core, halo) kept apart so the haze can scale the halo alone
vec3 neonCore(float dPx, vec3 tint, float energy, float widthPx, float heat) {
  float h = heat * energy;
  vec3 coreCol = h > 1e-4 ? hotCore(tint, h) / h : tint;
  return energy * coreCol * aaWire(dPx, widthPx);
}
float halo(float dPx, float haloPx) {
  float x = dPx / max(haloPx, 1e-3);
  return 0.0625 / (0.0625 + x * x);           // the Lorentzian: long tails that pile into haze where beams meet
}
float wrapPi(float a) { return a - TAU * floor((a + PI) / TAU); }

// The beam (or the nearest beam of a fan of n, `spread` radians wide) from o toward angle `aim`: distance in pixels and
// the distance travelled along it (negative behind the head).
vec2 fanDistance(vec2 p, vec2 o, float aim, float n, float spread, float px) {
  vec2 d = p - o;
  float len = length(d);
  float ang = atan(d.y, d.x);
  float stepA = n > 1.0 ? spread / (n - 1.0) : 0.0;
  float idx = n > 1.0 ? clamp(floor(wrapPi(ang - aim) / max(stepA, 1e-4) + 0.5 * (n - 1.0) + 0.5), 0.0, n - 1.0) : 0.0;
  float beam = aim + (idx - 0.5 * (n - 1.0)) * stepA;
  float off = wrapPi(ang - beam);
  float along = len * cos(off);
  float across = along > 0.0 ? len * abs(sin(off)) : len;
  return vec2(across / px, along);
}

// A pointed (equilateral) arch spanning [-w, w] at x = cx, springing at y0: distance to its outline.
float archDist(vec2 p, float cx, float w, float y0) {
  vec2 q = vec2(abs(p.x - cx), p.y - y0);
  if (q.y < 0.0) return abs(q.x - w);
  float apex = 1.7320508 * w;
  if (q.y > apex && q.x < 0.02) return length(q - vec2(0.0, apex));
  return abs(length(vec2(q.x + w, q.y)) - 2.0 * w);
}

void main() {
  vjLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float rs = max(u_res.y / 1080.0, 0.35);       // halos are sized for 1080 rows and scale with the frame

  // trails: the previous frame fades by a multiplier and a floor step (an 8-bit buffer must reach black)
  vec3 prev = texture(u_prev, v_uv).rgb;
  float keep = 0.45 + 0.47 * u_k5;
  vec3 trail = max(prev * keep - 1.5 / 255.0, 0.0);

  // the nave: near black, a little lift toward the floor where the haze collects
  vec3 col = vec3(0.0012, 0.0015, 0.003) + gPal[0] * 0.006 * (1.0 - smoothstep(-0.5, 0.2, p.y));

  // haze: slow smoke the halos travel through (moves at its own pace, never per-frame noise)
  float haze = 0.35 + 0.65 * vnoise(p * 3.2 + vec2(0.021 * u_time, -0.013 * u_time));
  haze *= 0.55 + 0.45 * vnoise(p * 9.0 - vec2(0.05 * u_time, 0.0));
  float hazeAmt = 0.25 + 0.95 * u_k2;

  // the foci the idle beams aim at: they step on each beat (snap in the first 45 % of the beat, then hold)
  float stepB = gCount + smoothstep(0.0, 0.45, gPhase) + 1.5 * gChordPulse;
  float amp = 0.15 + 0.55 * u_k1;
  vec2 focusA = vec2(amp * asp * 0.5 * sin(stepB * 1.5708), 0.05 + 0.32 * cos(stepB * 1.0472));
  vec2 focusB = vec2(-focusA.x, -0.05 - 0.3 * cos(stepB * 0.7854 + 1.0));
  float bassLift = 0.6 * u_bass + 0.25 * u_beat;
  float tremble = gTension * 0.02;

  vec3 beams = vec3(0.0);
  float hazeLight = 0.0;
  float widthPx = (0.9 + 2.4 * u_k3) * rs * (1.0 + 0.4 * u_bass);
  float haloPx = (8.0 + 26.0 * u_k2) * rs;
  for (int i = 0; i < 12; i++) {
    int c = i - 4 * (i / 4);
    int r = i / 4;
    // the head: the pad grid, top row at the top (pad 1 top left)
    vec2 o = vec2((float(c) - 1.5) * 0.30 * asp * 0.9, 0.36 - 0.36 * float(r));
    vec3 tint = padColour(i);
    vec2 focus = (c + r) - 2 * ((c + r) / 2) == 0 ? focusA : focusB;
    vec2 toF = focus - o;
    float aim = atan(toF.y, toF.x);
    if (tremble > 2e-4) aim += tremble * (vnoise(vec2(u_time * 1.7, float(i) * 3.1)) - 0.5) * 6.0;   // tension shivers
    // the idle beam: dim, always there
    vec2 bd = fanDistance(p, o, aim, 1.0, 0.0, px);
    float idleE = (0.20 + 0.22 * bassLift + 0.25 * gPulse) * exp(-max(bd.y, 0.0) * 0.55);
    beams += neonCore(bd.x, tint, idleE, widthPx * 0.8, 1.2);
    hazeLight += idleE * halo(bd.x, haloPx);
    vec3 tintH = tint * idleE * halo(bd.x, haloPx);
    // the fan: the pad's envelope opens it, velocity sets how many beams and how wide
    vec2 lv = padLevel(i);
    if (lv.x > 0.002) {
      float n = floor(3.0 + 9.0 * lv.y);
      float spread = (0.25 + 1.1 * u_k4 * (0.4 + 0.6 * lv.y)) * (0.35 + 0.65 * lv.x);
      float spin = 0.35 * sin(u_time * 0.8 + float(i));
      vec2 fd = fanDistance(p, o, aim + spin * lv.x, n, spread, px);
      float fanE = lv.x * (0.7 + 0.6 * lv.y) * exp(-max(fd.y, 0.0) * 0.35);
      beams += neonCore(fd.x, tint, fanE, widthPx * (1.0 + 0.6 * lv.y), 2.0);
      float fh = fanE * halo(fd.x, haloPx * (1.0 + lv.y));
      hazeLight += fh;
      tintH += tint * fh;
    }
    col += tintH * 0.55 * haze * hazeAmt;
    // the head itself: a small lens, hot when its pad fires
    float lens = exp(-dot(p - o, p - o) / (0.00004 + 0.00012 * lv.x));
    col += tint * lens * (0.25 + 1.2 * lv.x + 0.4 * gPulse);
  }

  // the nave's arches, lit only where beams pass through the smoke near them
  float arch = min(archDist(p, 0.0, 0.32, -0.12), min(archDist(p, -0.62 * asp * 0.5, 0.15, -0.2), archDist(p, 0.62 * asp * 0.5, 0.15, -0.2)));
  float archLine = exp(-arch / (2.5 * px * rs)) + 0.25 * exp(-arch / (14.0 * px * rs));
  col += vec3(0.55, 0.50, 0.46) * archLine * u_k6 * (0.012 + 0.6 * hazeLight * haze);

  col += beams;
  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.15);                 // an exposure curve: hot cores whiten, nothing clips hard
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  col = max(col, trail);                        // max, not add: light painting that never blooms to white
  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
