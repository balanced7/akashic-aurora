#version 300 es
//! {"id": "vj-led-wall", "name": "VJ LED Wall", "author": "Vandor", "tags": ["vj", "generative", "led", "beat", "pads"], "params": [{"k": 1, "name": "dot size", "default": 0.5}, {"k": 2, "name": "chase", "default": 0.6}, {"k": 3, "name": "idle glow", "default": 0.45}, {"k": 4, "name": "panel frame", "default": 0.5}, {"k": 5, "name": "trails", "default": 0.35}, {"k": 6, "name": "bloom", "default": 0.5}]}
precision highp float;

// LED Wall (arsenal/web/vj.html, Play-loadable). A stage wall of round LEDs, 27 rows high, split into twelve panels laid
// out like the KeyLab's pads (pad 1 top left): a pad lights its panel in its colour, velocity sets how bright, and a ripple
// runs out from the panel's centre as it lands. Over the panels a chase plays on every predicted beat, a different one
// each bar (a column chase, a row wipe, a diagonal sweep, a ring from the centre, a sparkle), always a travelling band
// so the wall never switches on whole. Along the bottom, twelve meters show the sounding pitch classes in the house pitch
// colours. In silence a slow plasma keeps the wall alive. Every dot is drawn with its own value (a real LED shows one
// colour), the dots swell a little with the bass, and their light lingers like phosphor (u_prev, max with decay). The
// hex-neon recipe (arsenal/web/glsl/groups/hex-neon.glsl) is the model: each cell knows only its centre and its die, and
// from those when the wave reaches it.

uniform sampler2D u_video;   // the VJ page: its 16x6 VJ strip (u_has_video stays 0); Play: the video or a 1x1 black texture
uniform sampler2D u_prev;
uniform vec2  u_res;
uniform float u_time;
uniform float u_has_video;
uniform float u_pulse, u_beat, u_level, u_bass, u_mid, u_high;
uniform float u_hue;
uniform float u_intensity;
uniform float u_k1, u_k2, u_k3, u_k4, u_k5, u_k6;

in vec2 v_uv;
out vec4 outColor;

// The house pitch colours (arsenal/web/vj-core.js pitchColours, the piano's palette; tests/vj_core.test.mjs pins these)
const vec3 PC_COL[12] = vec3[12](
  vec3(0.0199, 0.5610, 0.6101), vec3(1.0108, 0.2104, 0.0136), vec3(0.0398, 0.2848, 1.3564), vec3(0.5096, 0.5152, 0.0170),
  vec3(0.9080, 0.0617, 1.2415), vec3(0.0201, 0.5962, 0.3555), vec3(1.2716, 0.0623, 0.1166), vec3(0.0171, 0.4642, 0.8374),
  vec3(0.7316, 0.3596, 0.0150), vec3(0.3590, 0.1178, 1.6413), vec3(0.0682, 0.6072, 0.0156), vec3(1.2075, 0.0548, 0.5141));

// ------------------------------------------------------------- the VJ strip (arsenal/web/vj-core.js STRIP, v1) --
bool gHost;
vec3 gPal[4];
float gPhase, gPulse, gCount, gConf;

vec4 vjAt(int x, int y) { return texelFetch(u_video, ivec2(x, y), 0); }

// the shared hit input (STRIP v2, row 2: vj-core.js): the latest pad hit's pulse (through the velocity curve), its velocity,
// its effect code and age, where it struck; the kick / snare / hat envelopes. 0 in Play and on a v1 host.
float gHit, gHitVel, gHitCode, gHitAge, gSnare, gHat;
vec2 gHitAt;
void hitLoad() {
  if (gHost && vjAt(15, 2).x >= 2.0) {
    vec4 h = vjAt(10, 2);
    gHit = h.x; gHitVel = h.y; gHitCode = h.z; gHitAge = h.w;
    vec4 b = vjAt(11, 2);
    gSnare = b.y; gHat = b.z;
    gHitAt = vjAt(12, 2).yz;
  } else {
    gHit = 0.0; gHitVel = 0.0; gHitCode = 0.0; gHitAge = 30.0; gSnare = 0.0; gHat = 0.0; gHitAt = vec2(0.0);
  }
}


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
    gConf = 1.0;
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.53); gPal[1] = hueLinear(h + 0.80); gPal[2] = hueLinear(h + 0.64); gPal[3] = hueLinear(h + 0.03);
    float beats = u_time * 2.0;
    gPhase = fract(beats); gPulse = u_beat; gCount = mod(floor(beats), 64.0);
    gConf = 0.6;
  }
}

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

// how lit a dot at (nx, ny) is by this bar's chase, 0..1; the band always travels, so the wall never switches on whole
float chase(float nx, float ny, vec2 cell, float mode, float phase, float beatN) {
  float dir = mod(beatN, 2.0) < 0.5 ? 1.0 : -1.0;
  if (mode < 0.5) {                                        // a column chase, back and forth
    float x = dir > 0.0 ? phase : 1.0 - phase;
    return exp(-pow((nx - x) / 0.05, 2.0));
  } else if (mode < 1.5) {                                 // a row wipe, top to bottom
    return exp(-pow((ny - (1.0 - phase)) / 0.07, 2.0));
  } else if (mode < 2.5) {                                 // a diagonal sweep
    float d = fract(nx * 0.8 + ny * 0.6 - phase * 1.4 * dir);
    return exp(-pow(min(d, 1.0 - d) / 0.05, 2.0));
  } else if (mode < 3.5) {                                 // a ring out of the centre
    float r = length((vec2(nx, ny) - 0.5) * vec2(1.6, 1.0));
    return exp(-pow((r - phase * 0.85) / 0.05, 2.0));
  }
  float s = hash12(cell + vec2(beatN * 7.13, beatN * 3.71));  // a sparkle, a new set of dots each beat
  return step(0.90, s) * exp(-phase * 3.0);
}

void main() {
  vjLoad();
  hitLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float rs = max(u_res.y / 1080.0, 0.35);
  float bass = clamp(0.6 * u_bass + 0.4 * u_pulse, 0.0, 1.5);

  const float rows = 27.0;
  float cols = 4.0 * max(1.0, floor(rows * asp / 4.0 + 0.5));
  float cs = 1.0 / rows;
  vec2 q = p + vec2(cols * cs * 0.5, 0.5);
  vec2 cell = floor(q / cs);
  vec2 local = fract(q / cs) - 0.5;
  vec3 prev = texture(u_prev, v_uv).rgb;
  if (cell.x < 0.0 || cell.x >= cols || cell.y < 0.0 || cell.y >= rows) {
    outColor = vec4(max(prev * 0.5 - 2.0 / 255.0, 0.0), 1.0);   // outside the wall: black, with what was there fading
    return;
  }
  float nx = (cell.x + 0.5) / cols;
  float ny = (cell.y + 0.5) / rows;

  // the panel this dot belongs to (pad 1 top left), and whether it sits on the panel's frame
  float perX = cols / 4.0, perY = rows / 3.0;
  float pcol = floor(cell.x / perX);
  float prowUp = floor(cell.y / perY);
  int pad = int((2.0 - prowUp) * 4.0 + pcol);
  vec2 inPanel = vec2(cell.x - pcol * perX, cell.y - prowUp * perY);
  bool frame = inPanel.x < 0.5 || inPanel.y > perY - 1.5;

  vec3 led = vec3(0.0);
  // a slow plasma: the wall is never dead, even in silence
  float plasma = vnoise(cell * 0.11 + vec2(u_time * 0.07, -u_time * 0.05));
  led += mix(gPal[0], gPal[1], plasma) * (0.006 + 0.032 * u_k3) * smoothstep(0.35, 0.9, plasma);
  if (frame) led = max(led, gPal[2] * 0.02 * u_k4);

  // this bar's chase, riding the predicted beat
  float mode = mod(floor(gCount / 4.0), 5.0);
  float ch = chase(nx, ny, cell, mode, gPhase, gCount);
  led = max(led, gPal[int(mode) - 4 * (int(mode) / 4)] * ch * 0.32 * u_k2 * gConf);

  // the pad's panel: fill by its envelope and velocity, and a ripple out of its centre as it lands
  vec4 pv = gHost ? vjAt(pad, 0) : vec4(0.0);
  if (!gHost) {
    float band = pad < 4 ? u_high : (pad < 8 ? u_mid : u_bass);
    pv = vec4(smoothstep(0.55, 0.9, band) * smoothstep(0.6, 0.98, 0.5 + 0.5 * sin(u_time * 0.8 + float(pad) * 2.4)), band, 0.5, 0.0);
  }
  if (!frame && pv.x > 0.002) {
    vec3 tint = gHost ? vjAt(pad, 3).rgb : gPal[pad - 4 * (pad / 4)];
    vec2 centre = vec2(perX, perY) * 0.5;
    float dd = length(inPanel + 0.5 - centre);
    float ring = exp(-pow((dd - pv.z * 26.0) / 1.2, 2.0)) * (1.0 - smoothstep(0.3, 0.9, pv.z));
    float fill = pv.x * (0.30 + 0.55 * pv.y);
    led = max(led, tint * (fill + ring * pv.y * 0.9));
  }

  // any pad hit (the strip's shared hit input, 2026-10-24): a ripple across the whole wall from where the hit struck,
  // in the palette's accent, one ring racing out over ~0.6 s (a travelling band: the wall never switches on whole)
  if (gHitAge < 0.8) {
    vec2 cp = (cell + 0.5) * cs - vec2(cols * cs * 0.5, 0.5);
    float dist = length(cp - gHitAt);
    float front = gHitAge * 1.6;
    float rip = exp(-pow((dist - front) / 0.035, 2.0)) * (1.0 - smoothstep(0.25, 0.8, gHitAge)) * (0.45 + 0.55 * gHitVel);
    led = max(led, mix(gPal[3], vec3(1.0), 0.25) * rip * 0.75);
  }

  // the pitch-class meters along the bottom: C on the left, the sounding level as height, a strike as a bright cap
  if (gHost) {
    int g = int(floor(nx * 12.0));
    vec4 pcv = vjAt(g, 1);
    float h = pcv.x * 0.34;
    if (ny < h && pcv.x > 0.01) {
      float cap = smoothstep(h - 1.5 / rows, h, ny) * (0.4 + 0.6 * pcv.y);
      led = max(led, PC_COL[g] * (0.28 + 0.5 * cap));
    }
  }

  // the dot: round, antialiased in pixels, swelling a little with the bass; unlit LEDs stay faintly visible
  float radius = (0.27 + 0.15 * u_k1) * (1.0 + 0.16 * bass + 0.18 * gHit);
  float dPx = (length(local) - radius) * cs / px;
  float cover = clamp(0.5 - dPx, 0.0, 1.0);
  float glow = exp(-max(dPx, 0.0) / ((2.0 + 9.0 * u_k6) * rs)) * 0.45 * u_k6;
  vec3 col = vec3(0.004, 0.0048, 0.0064) * cover + led * (cover + glow) * (1.0 + 0.35 * gPulse * u_k2);

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.3);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  col = max(col, max(prev * (0.25 + 0.6 * u_k5) - 1.5 / 255.0, 0.0));
  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
