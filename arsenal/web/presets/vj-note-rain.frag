#version 300 es
//! {"id": "vj-note-rain", "name": "VJ Note Rain", "author": "Vandor", "tags": ["vj", "generative", "keys", "chord", "pads", "feedback"], "params": [{"k": 1, "name": "fall", "default": 0.5}, {"k": 2, "name": "glow", "default": 0.6}, {"k": 3, "name": "rain", "default": 0.45}, {"k": 4, "name": "reflection", "default": 0.6}, {"k": 5, "name": "fade", "default": 0.4}, {"k": 6, "name": "shafts", "default": 0.7}]}
precision highp float;

// Note Rain (arsenal/web/vj.html, Play-loadable). A piano roll that rains. Every note you play is born at the cloud line
// across the top, at its key's place on an 88-key span, and falls as a glowing bar as long as you hold it; it lands on a
// wet floor that reflects the whole fall. Colour is the house pitch colour, so a chord falls as a band of colours that
// sit together on the circle of fifths, and a struck note's head is brighter than its sustain (the strike pulse rides in
// the brightness). A chord change lays a thin spectrum line across the fall.
//
// The fall is history, kept in the ALPHA channel of the feedback buffer (as 1 - intensity, so a cleared buffer is empty):
// each frame copies it down by whole pixels with texelFetch -- no resampling, so bars stay sharp all the way down -- and
// the colour is recomputed from each pixel's key every frame, so everything else (glow, rain, shafts, the reflection) is
// drawn fresh and never smears. The scroll is frame-rate independent: two state texels in the bottom row hold the last
// frame's time (fract seconds) and the sub-pixel remainder. The pads open shafts of light in their colours across the fall;
// the bass lights the floor and the kick makes the landing notes splash.

uniform sampler2D u_video;   // the VJ page: its 16x6 VJ strip (u_has_video stays 0); Play: the video or a 1x1 black texture
uniform sampler2D u_prev;
uniform vec2  u_res;
uniform float u_time;
uniform float u_has_video;
uniform float u_pulse, u_beat, u_level, u_bass, u_mid, u_high, u_flux;
uniform float u_hue;
uniform float u_intensity;
uniform float u_k1, u_k2, u_k3, u_k4, u_k5, u_k6;

in vec2 v_uv;
out vec4 outColor;

const float PI = 3.14159265358979;
const float TAU = 6.28318530717959;
const float Y_TOP = 0.40;      // the cloud line, in the centred space (height 1)
const float Y_FLOOR = -0.30;   // the floor

const vec3 PC_COL[12] = vec3[12](
  vec3(0.0199, 0.5610, 0.6101), vec3(1.0108, 0.2104, 0.0136), vec3(0.0398, 0.2848, 1.3564), vec3(0.5096, 0.5152, 0.0170),
  vec3(0.9080, 0.0617, 1.2415), vec3(0.0201, 0.5962, 0.3555), vec3(1.2716, 0.0623, 0.1166), vec3(0.0171, 0.4642, 0.8374),
  vec3(0.7316, 0.3596, 0.0150), vec3(0.3590, 0.1178, 1.6413), vec3(0.0682, 0.6072, 0.0156), vec3(1.2075, 0.0548, 0.5141));

// ------------------------------------------------------------- the VJ strip (arsenal/web/vj-core.js STRIP, v1) --
bool gHost;
vec3 gPal[4];
float gPulse, gChordPulse, gChordAge, gKick, gRoot;

vec4 vjAt(int x, int y) { return texelFetch(u_video, ivec2(x, y), 0); }

vec3 hueLinear(float turns) {
  vec3 c = clamp(abs(fract(turns + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0, 0.0, 1.0);
  return c * c;
}

void vjLoad() {
  gHost = u_has_video < 0.5 && textureSize(u_video, 0) == ivec2(16, 6);
  if (gHost) {
    for (int i = 0; i < 4; i++) gPal[i] = vjAt(i, 2).rgb;
    gPulse = vjAt(12, 0).y;
    vec4 ch = vjAt(15, 0);
    gChordPulse = ch.x; gRoot = ch.y; gChordAge = ch.z;
    vec4 hit = vjAt(12, 1);
    gKick = max(hit.y, max(0.6 * hit.x, 0.7 * gPulse));
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.55); gPal[1] = hueLinear(h + 0.70); gPal[2] = hueLinear(h + 0.45); gPal[3] = hueLinear(h + 0.05);
    gPulse = u_beat;
    gChordPulse = 0.0; gRoot = -1.0; gChordAge = 60.0;
    gKick = max(u_beat, 0.7 * u_flux);
  }
}

vec3 padColour(int i) { return gHost ? vjAt(i, 3).rgb : gPal[i - 4 * (i / 4)]; }

vec2 padLevel(int i) {          // (envelope, velocity)
  if (gHost) return vjAt(i, 0).xy;
  float band = i < 4 ? u_high : (i < 8 ? u_mid : u_bass);
  float gate = smoothstep(0.6, 0.98, 0.5 + 0.5 * sin(u_time * 0.7 + float(i) * 2.4));
  return vec2(smoothstep(0.55, 0.9, band) * gate, band);
}

// ------------------------------------------------------------------------------------------------- light parts --
float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
vec3 hotCore(vec3 tint, float heat) {      // light-glow glowHotCore
  float h = max(heat, 0.0);
  vec3 hue = max(tint, vec3(0.0));
  float peak = max(hue.r, max(hue.g, hue.b));
  return h * mix(hue, vec3(peak), h * h / (1.0 + h * h));
}
float lorentz(float dPx, float haloPx) { float x = dPx / max(haloPx, 1e-3); return 0.0625 / (0.0625 + x * x); }

float gAsp;
float keyX(float key) { return ((key - 21.0) / 87.0 - 0.5) * gAsp * 0.94; }
float keyAt(float x) { return clamp(floor(21.0 + (x / (gAsp * 0.94) + 0.5) * 87.0 + 0.5), 21.0, 108.0); }
vec3 keyColour(float key) { int pc = int(mod(key, 12.0)); return PC_COL[pc]; }

// What is sounding at x right now (0..1): every star's key, its brightness carrying the strike pulse.
float fresh(float x, float px) {
  float kw = gAsp * 0.94 / 87.0;
  float halfW = 0.36 * kw;
  float v = 0.0;
  if (gHost) {
    int count = int(vjAt(9, 2).x + 0.5);
    for (int s = 0; s < 16; s++) {
      if (s >= count) break;
      vec4 st = vjAt(s, 4);
      if (st.w < -0.5) continue;
      // the key from the star's radius (vj-core.js starPosition: r = 0.11 + 0.31 * (midi - 21) / 87)
      float key = floor(21.0 + 87.0 * (length(st.xy) - 0.11) / 0.31 + 0.5);
      float d = abs(x - keyX(key)) - halfW;
      float cover = clamp(0.5 - d / px, 0.0, 1.0);
      v = max(v, cover * clamp(st.z, 0.0, 1.0));
    }
    if (gChordAge < 0.05) v = max(v, 0.012);           // a chord change: a thin spectrum line across the fall
  } else {
    for (int vce = 0; vce < 2; vce++) {               // Play: a wandering two-voice melody
      float rate = vce == 0 ? 2.0 : 0.75;
      float slot = floor(u_time * rate);
      float on = step(0.35, hash12(vec2(slot, float(vce) * 7.0)));
      float key = 33.0 + floor(hash12(vec2(slot * 1.3, 2.0 + float(vce))) * 54.0);
      float frac = fract(u_time * rate);
      float d = abs(x - keyX(key)) - halfW;
      v = max(v, on * step(frac, 0.8) * clamp(0.5 - d / px, 0.0, 1.0) * (0.45 + 0.55 * u_level));
    }
  }
  return v;
}

// last frame's history, `shift` rows above (x, y); nothing above the cloud line
float hist(int x, int y, int shift, int topRow) {
  return y + shift <= topRow ? 1.0 - texelFetch(u_prev, ivec2(x, y + shift), 0).a : 0.0;
}

void main() {
  vjLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  gAsp = asp;
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float H = u_res.y;
  float px = 1.0 / max(H, 1.0);
  float rs = max(H / 1080.0, 0.35);
  float t = u_time;
  float bass = clamp(0.65 * u_bass + 0.35 * u_pulse, 0.0, 1.5);
  float kw = asp * 0.94 / 87.0;

  ivec2 ip = ivec2(gl_FragCoord.xy);
  ivec2 prevSize = textureSize(u_prev, 0);
  bool sameSize = prevSize == ivec2(u_res + 0.5);
  int topRow = int(H * (0.5 + Y_TOP));
  int floorRow = int(H * (0.5 + Y_FLOOR));

  // the clock in the bottom row: last frame's time and the sub-pixel remainder
  float prevT = texelFetch(u_prev, ivec2(0, 0), 0).a;
  float rem = texelFetch(u_prev, ivec2(1, 0), 0).a;
  bool cleared = !sameSize || prevT > 0.99995;
  float dt = cleared ? 1.0 / 60.0 : fract(fract(t) - prevT + 1.0);
  dt = min(dt, 0.1);
  rem = cleared || rem > 0.99995 ? 0.0 : rem;
  float fallS = 1.6 + 3.0 * (1.0 - u_k1);               // seconds from the cloud line to the floor
  float speedPx = (Y_TOP - Y_FLOOR) * H / fallS;
  float total = rem + dt * speedPx;
  int shift = int(floor(total));
  float remNew = total - float(shift);
  float fade = exp(-dt * (0.05 + 0.6 * u_k5));

  // the history at a pixel of this frame is the pixel `shift` rows above it last frame (hist), or what sounds now
  float h = 0.0;
  bool zone = ip.y >= floorRow && ip.y <= topRow;
  if (zone) {
    if (cleared) h = 0.0;
    else if (ip.y + shift <= topRow) h = (1.0 - texelFetch(u_prev, ivec2(ip.x, ip.y + shift), 0).a) * fade;
    else h = fresh(p.x, px);
  }

  // ------------------------------------------------------------------------------------------ the room --
  vec3 col = mix(gPal[1] * 0.006, vec3(0.0010, 0.0012, 0.0024), smoothstep(-0.5, 0.5, p.y));
  // the rain: fine streaks falling a little faster than the notes, densest where the mids and highs are
  vec2 rc = vec2(p.x * 140.0, p.y * 7.0 + t * 2.2);
  vec2 cell = floor(rc);
  float rh = hash12(cell);
  float drop = step(0.86 - 0.12 * u_high, rh) * smoothstep(0.0, 0.2, fract(rc.y)) * (1.0 - smoothstep(0.2, 1.0, fract(rc.y)));
  float rx = abs(fract(rc.x) - 0.5) / (140.0 * px);
  col += mix(gPal[0], vec3(0.7, 0.8, 1.0), 0.5) * drop * exp(-rx * rx / (0.4 * rs * rs)) * (0.02 + 0.05 * u_mid) * u_k3 * step(Y_FLOOR, p.y);

  // ------------------------------------------------------------------------------------------- the fall --
  if (zone && !cleared) {
    vec3 kc = keyColour(keyAt(p.x));
    col += hotCore(kc, 0.7 + 1.5 * h) * h * 1.15;
    // the glow: the history beside this pixel, eight samples closer together than a bar is wide (so a bar's glow is one
    // smooth halo, not ghost copies), each in its own key's colour
    vec3 glow = vec3(0.0);
    for (int s = 0; s < 8; s++) {
      float k = float(s / 2 + 1);                       // 1, 1, 2, 2, 3, 3, 4, 4
      float off = 0.36 * k * kw * (s - 2 * (s / 2) == 0 ? -1.0 : 1.0);
      int sx = clamp(ip.x + int(floor(off / px + 0.5)), 0, prevSize.x - 1);
      float hs = hist(sx, ip.y, shift, topRow);
      glow += keyColour(keyAt(p.x + off)) * hs * (0.16 * exp(-0.55 * (k - 1.0)));
    }
    col += glow * (0.4 + 1.2 * u_k2);
  }
  // the cloud line: a haze in the palette, lit by the bass, with what sounds now burning in it
  float dTop = (p.y - Y_TOP) / px;
  float now = fresh(p.x, px);
  col += mix(gPal[0], gPal[2], 0.5 + 0.5 * sin(p.x * 3.0 + t * 0.3)) * exp(-abs(dTop) / (14.0 * rs)) * (0.03 + 0.06 * bass + 0.1 * gChordPulse);
  col += hotCore(keyColour(keyAt(p.x)), 1.4) * now * (exp(-dTop * dTop / (16.0 * rs * rs)) * 1.2 + lorentz(dTop, 20.0 * rs) * 0.25);

  // ------------------------------------------------------------------------------------------ the floor --
  float dFloor = (p.y - Y_FLOOR) / px;
  int landRow = floorRow + shift;
  float landed = 0.0;
  if (!cleared && landRow <= topRow) landed = 1.0 - texelFetch(u_prev, ivec2(ip.x, landRow), 0).a;
  vec3 kcx = keyColour(keyAt(p.x));
  col += mix(gPal[2], vec3(0.8, 0.85, 1.0), 0.4) * exp(-dFloor * dFloor / (1.5 * rs * rs)) * (0.12 + 0.25 * bass);
  // splashes where the notes land, kicked by the kick
  col += hotCore(kcx, 1.0) * landed * exp(-abs(dFloor) / (10.0 * rs)) * (0.35 + 0.6 * gKick) * u_k2;
  if (p.y < Y_FLOOR && !cleared) {
    // the reflection: the fall mirrored and stretched, rippled, darker with depth
    float depth = (Y_FLOOR - p.y);
    float yMirror = Y_FLOOR + depth * 1.8;
    float wob = sin(p.y * 260.0 + t * 3.0) * 2.5 * rs + sin(p.y * 90.0 - t * 1.7) * 1.5 * rs;
    float xm = p.x + wob * px;
    int my = int(H * (0.5 + yMirror));
    int mx = clamp(int((xm / asp + 0.5) * u_res.x), 0, prevSize.x - 1);
    float hm = (my <= topRow && my >= floorRow) ? hist(mx, my, shift, topRow) : 0.0;
    col += keyColour(keyAt(xm)) * hm * 0.35 * u_k4 * exp(-depth * 5.0);
    col += gPal[1] * 0.012 * bass * exp(-depth * 9.0);
  }

  // ------------------------------------------------------------------------------- the pads: light shafts --
  for (int i = 0; i < 12; i++) {
    vec2 lv = padLevel(i);
    if (lv.x < 0.002) continue;
    float xi = ((float(i) + 0.5) / 12.0 - 0.5) * asp * 0.92;
    float w = (0.02 + 0.05 * lv.y);
    float dx = (p.x - xi) / w;
    float shaft = exp(-dx * dx) * smoothstep(Y_FLOOR - 0.05, Y_FLOOR + 0.05, p.y) * (1.0 - smoothstep(Y_TOP - 0.02, Y_TOP + 0.08, p.y));
    float sparkle = hash12(floor(vec2(p.x * 300.0, p.y * 40.0 + t * 9.0 * (1.0 + lv.y))));
    sparkle = step(0.93, sparkle);
    col += padColour(i) * shaft * lv.x * (0.06 + 0.5 * sparkle * lv.y) * u_k6;
  }

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.2);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)

  // the alpha: the history (1 - intensity) inside the fall, the clock in the bottom row's first two texels
  float a = 1.0;
  if (zone) a = 1.0 - clamp(h, 0.0, 1.0);
  if (ip.y == 0 && ip.x == 0) a = fract(t);
  if (ip.y == 0 && ip.x == 1) a = remNew;
  outColor = vec4(clamp(col, 0.0, 1.0), a);
}
