#version 300 es
//! {"id": "vj-lissajous-chords", "name": "VJ Lissajous Chords", "author": "Vandor", "tags": ["vj", "generative", "chord", "keys", "pads", "scope"], "params": [{"k": 1, "name": "beam", "default": 0.55}, {"k": 2, "name": "glow", "default": 0.55}, {"k": 3, "name": "turn", "default": 0.45}, {"k": 4, "name": "graticule", "default": 0.4}, {"k": 5, "name": "phosphor", "default": 0.55}, {"k": 6, "name": "sweep", "default": 0.5}]}
precision highp float;

// Lissajous Chords (arsenal/web/vj.html, Play-loadable). An oscilloscope in XYZ mode whose oscillators ARE the chord. Each
// sounding tone is tuned to its just ratio above the root (major third 5/4, fifth 3/2, minor third 6/5, harmonic seventh
// 7/4 over a major third, 9/5 under a minor one ...), the ratios are brought to whole numbers over their least common
// denominator, and those numbers drive x, y and z: a major triad traces 4:5:6, a minor triad 10:12:15, a dominant seventh
// 4:5:6:7 (the fourth voice swells the radius), a minor seventh 10:12:15:18, a diminished triad 5:6:7. Simple ratios close
// into open, slow figures; dense ones weave. The phases drift slowly, the way two analogue oscillators beat, so the figure
// turns over in depth. On a chord change the new figure draws itself on (the page's draw-on clock) while the old one fades
// in the phosphor (the feedback buffer). The beam is a moving head with a phosphor tail along the curve; the beat brightens
// it, the bass widens the glow, and the pads kick the figure's rotation, each pad about its own axis, tinting the beam.

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

const vec3 PC_COL[12] = vec3[12](
  vec3(0.0199, 0.5610, 0.6101), vec3(1.0108, 0.2104, 0.0136), vec3(0.0398, 0.2848, 1.3564), vec3(0.5096, 0.5152, 0.0170),
  vec3(0.9080, 0.0617, 1.2415), vec3(0.0201, 0.5962, 0.3555), vec3(1.2716, 0.0623, 0.1166), vec3(0.0171, 0.4642, 0.8374),
  vec3(0.7316, 0.3596, 0.0150), vec3(0.3590, 0.1178, 1.6413), vec3(0.0682, 0.6072, 0.0156), vec3(1.2075, 0.0548, 0.5141));

// just ratios above the root, by semitone: numerators and denominators (the minor seventh is decided per chord)
const int RNUM[12] = int[12](1, 16, 9, 6, 5, 4, 7, 3, 8, 5, 9, 15);
const int RDEN[12] = int[12](1, 15, 8, 5, 4, 3, 5, 2, 5, 3, 5, 8);
// which tones the figure takes first: thirds, fifths, sevenths, then colour tones
const int PRIORITY[11] = int[11](4, 3, 7, 10, 11, 6, 8, 9, 2, 5, 1);

// ------------------------------------------------------------- the VJ strip (arsenal/web/vj-core.js STRIP, v1) --
bool gHost;
vec3 gPal[4];
float gPulse, gChordPulse, gKick, gDrawOn;

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
    gChordPulse = vjAt(15, 0).x;
    vec4 hit = vjAt(12, 1);
    gKick = max(hit.y, max(0.6 * hit.x, 0.7 * gPulse));
    gDrawOn = vjAt(15, 1).w;
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.36); gPal[1] = hueLinear(h + 0.55); gPal[2] = hueLinear(h + 0.45); gPal[3] = hueLinear(h + 0.10);
    gPulse = u_beat;
    gChordPulse = 0.0;
    gKick = max(u_beat, 0.7 * u_flux);
    gDrawOn = clamp(fract(u_time / 4.0) * 4.0, 0.0, 1.0);
  }
}

vec3 padColour(int i) { return gHost ? vjAt(i, 3).rgb : gPal[i - 4 * (i / 4)]; }

vec2 padLevel(int i) {          // (envelope, velocity)
  if (gHost) return vjAt(i, 0).xy;
  float band = i < 4 ? u_high : (i < 8 ? u_mid : u_bass);
  float gate = smoothstep(0.6, 0.98, 0.5 + 0.5 * sin(u_time * 0.7 + float(i) * 2.4));
  return vec2(smoothstep(0.55, 0.9, band) * gate, band);
}

int gcd(int a, int b) {
  for (int i = 0; i < 12; i++) {
    if (b == 0) break;
    int r = a - (a / b) * b;
    a = b; b = r;
  }
  return max(a, 1);
}

// The chord as up to four whole-number frequencies, f.x = the root's. Returns how many voices sound.
int chordVoices(out vec4 f, out int rootPc) {
  int mask[12];
  for (int i = 0; i < 12; i++) mask[i] = 0;
  int root = -1;
  if (gHost) {
    int count = int(vjAt(9, 2).x + 0.5);
    int lowest = 999;
    for (int s = 0; s < 16; s++) {
      if (s >= count) break;
      vec4 st = vjAt(s, 4);
      if (st.w < -0.5) continue;
      int pc = int(st.w + 0.5);
      pc = pc - 12 * (pc / 12);
      mask[pc] = 1;
      // the register from the star's radius (vj-core.js starPosition: r = 0.11 + 0.31 * (midi - 21) / 87)
      int midi = int(21.0 + 87.0 * (length(st.xy) - 0.11) / 0.31 + 0.5);
      if (midi < lowest) { lowest = midi; root = pc; }
    }
    float named = vjAt(15, 0).y;
    if (named > -0.5 && mask[int(named + 0.5)] == 1) root = int(named + 0.5);
  } else {
    // Play: a slow progression through chord shapes, one every four seconds
    int which = int(mod(floor(u_time / 4.0), 6.0));
    root = 0;
    mask[0] = 1;
    if (which == 0) { mask[4] = 1; mask[7] = 1; }
    else if (which == 1) { mask[3] = 1; mask[7] = 1; }
    else if (which == 2) { mask[4] = 1; mask[7] = 1; mask[10] = 1; }
    else if (which == 3) { mask[3] = 1; mask[7] = 1; mask[10] = 1; }
    else if (which == 4) { mask[5] = 1; mask[7] = 1; }
    else { mask[4] = 1; mask[7] = 1; mask[11] = 1; }
  }
  rootPc = root;
  if (root < 0) { f = vec4(3.0, 4.0, 5.0, 0.0); return 0; }
  int iv[4];
  iv[0] = 0; iv[1] = -1; iv[2] = -1; iv[3] = -1;
  int n = 1;
  for (int k = 0; k < 11; k++) {
    if (n >= 4) break;
    int pc = root + PRIORITY[k];
    pc = pc - 12 * (pc / 12);
    if (mask[pc] == 1) { iv[n] = PRIORITY[k]; n++; }
  }
  bool minorThird = false;
  for (int j = 1; j < 4; j++) if (iv[j] == 3) minorThird = true;
  int num[4], den[4];
  int L = 1;
  for (int j = 0; j < 4; j++) {
    if (j >= n) { num[j] = 0; den[j] = 1; continue; }
    int s = iv[j];
    num[j] = RNUM[s]; den[j] = RDEN[s];
    if (s == 10 && !minorThird) { num[j] = 7; den[j] = 4; }    // the harmonic seventh over a major third or a sus
    L = L / gcd(L, den[j]) * den[j];
  }
  int fi[4];
  int cd = 0;                                   // the frequencies' greatest common divisor
  for (int j = 0; j < 4; j++) {
    fi[j] = j < n ? num[j] * (L / den[j]) : 0;
    if (j < n) cd = cd == 0 ? fi[j] : gcd(cd, fi[j]);
  }
  cd = max(cd, 1);
  f = vec4(float(fi[0] / cd), float(fi[1] / cd), float(fi[2] / cd), float(fi[3] / cd));
  return n;
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
mat3 rotX(float a) { float c = cos(a), s = sin(a); return mat3(1.0, 0.0, 0.0, 0.0, c, s, 0.0, -s, c); }
mat3 rotY(float a) { float c = cos(a), s = sin(a); return mat3(c, 0.0, -s, 0.0, 1.0, 0.0, s, 0.0, c); }
mat3 rotZ(float a) { float c = cos(a), s = sin(a); return mat3(c, s, 0.0, -s, c, 0.0, 0.0, 0.0, 1.0); }

void main() {
  vjLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float rs = max(u_res.y / 1080.0, 0.35);
  float t = u_time;
  float bass = clamp(0.65 * u_bass + 0.35 * u_pulse, 0.0, 1.5);

  vec4 f;
  int rootPc;
  int voices = chordVoices(f, rootPc);
  float fmax = max(max(f.x, f.y), max(f.z, f.w));

  // the beam's colour: the root's pitch colour, warmed by the palette; the pads tint it and kick the rotation
  vec3 beamCol = rootPc >= 0 ? mix(PC_COL[rootPc], gPal[0], 0.25) : gPal[0];
  float kickX = 0.0, kickY = 0.0, padBest = 0.0;
  for (int i = 0; i < 12; i++) {
    vec2 lv = padLevel(i);
    if (lv.x < 0.002) continue;
    float a = float(i) * (TAU / 12.0);
    kickX += lv.x * lv.y * cos(a) * 0.9;
    kickY += lv.x * lv.y * sin(a) * 0.9;
    if (lv.x > padBest) { padBest = lv.x; beamCol = mix(beamCol, padColour(i), clamp(lv.x, 0.0, 0.8)); }
  }

  // the crt: a dark glass, a faint graticule (ten by eight), and the centre cross with its ticks
  vec3 col = mix(vec3(0.0012, 0.0016, 0.0022), gPal[1] * 0.006, smoothstep(0.7, 0.0, length(p)));
  float scopeH = 0.86;
  vec2 gq = p / (scopeH / 8.0);
  vec2 gd = abs(fract(gq + 0.5) - 0.5) * (scopeH / 8.0) / px;
  float inScope = step(abs(p.x), scopeH * 0.625) * step(abs(p.y), scopeH * 0.5);
  float grid = max(exp(-gd.x * gd.x / (0.5 * rs * rs)), exp(-gd.y * gd.y / (0.5 * rs * rs)));
  vec2 cd = abs(p) / px;
  float ticks = (exp(-cd.x * cd.x / (0.5 * rs * rs)) * step(abs(fract(gq.y * 5.0 + 0.5) - 0.5), 0.08) +
                 exp(-cd.y * cd.y / (0.5 * rs * rs)) * step(abs(fract(gq.x * 5.0 + 0.5) - 0.5), 0.08));
  col += mix(gPal[2], vec3(0.6), 0.5) * (grid * 0.035 + ticks * 0.05) * u_k4 * inScope;

  // the figure: up to 320 segments of the closed curve; the pixel skips the loop when it is far outside the figure
  float R = 0.27 * (1.0 + 0.05 * gKick + 0.03 * bass);
  mat3 m = rotY(t * (0.05 + 0.25 * u_k3) + kickY) * rotX(0.45 + 0.25 * sin(t * 0.07) + kickX) * rotZ(0.15 * sin(t * 0.05));
  vec4 ph = vec4(0.0, PI * 0.5 + t * 0.11, PI * 0.25 + t * 0.07, t * 0.05);   // the slow analogue drift
  float wBeam = (0.7 + 1.4 * u_k1) * rs;
  float halo = (5.0 + 10.0 * u_k2 + 6.0 * bass) * rs;
  float headAt = fract(t * (0.25 + 0.6 * u_k6));            // where the beam is, as a fraction of the figure
  float draw = clamp(gDrawOn, 0.0, 1.0);
  float span = TAU * max(draw, 0.02);
  int nSeg = int(clamp(fmax * 20.0 + 40.0, 64.0, 320.0));     // about 20 segments per cycle of the fastest voice
  float stepA = span / float(nSeg);
  float fourth = voices >= 4 ? 0.22 : 0.0;
  vec3 beam = vec3(0.0);
  float rp = length(p);
  if (rp < R * 2.6 + halo * px * 6.0) {
    // the loop finds the NEAREST segment only (a squared distance and a compare per segment, no exp, no sqrt), and the
    // light is worked out once from it: the cost per segment is about twenty flops
    vec4 cs = cos(ph), sn = sin(ph);                     // phasors for each voice, rotated one step at a time
    vec4 dc = cos(f * stepA), ds = sin(f * stepA);
    vec2 prevPt = vec2(0.0);
    float d2Min = 1e9, sMin = 0.0, zMin = 0.0;
    for (int i = 0; i <= 320; i++) {
      if (i > nSeg) break;
      // the point: x, y, z from the first three voices; a fourth voice swells the radius
      vec3 q = (voices >= 3 || voices == 0) ? vec3(sn.x, sn.y, sn.z) : (voices == 2 ? vec3(sn.x, sn.y, 0.0) : vec3(sn.x, cs.x, 0.0));
      q *= 1.0 + fourth * sn.w;
      vec3 w3 = m * q;
      vec2 pt = R * w3.xy / (1.0 + 0.2 * w3.z);
      if (i > 0) {
        vec2 ab = pt - prevPt;
        float k = clamp(dot(p - prevPt, ab) / max(dot(ab, ab), 1e-12), 0.0, 1.0);
        vec2 e = p - prevPt - ab * k;
        float d2 = dot(e, e);
        if (d2 < d2Min) { d2Min = d2; sMin = (float(i - 1) + k) / float(nSeg) * draw; zMin = w3.z; }
      }
      prevPt = pt;
      // advance every voice by one step
      vec4 ncs = cs * dc - sn * ds;
      sn = sn * dc + cs * ds;
      cs = ncs;
    }
    float d = sqrt(d2Min) / px;
    float age = fract(headAt - sMin + 1.0);               // how long since the beam passed, as a fraction of the figure
    float lit = 0.30 + 0.70 * exp(-age * 5.0);
    float depth = 0.65 + 0.35 * clamp(1.0 - zMin, 0.0, 1.5);   // nearer is brighter
    float core = lit * depth * exp(-d * d / (wBeam * wBeam));
    // the glow depends on distance only (the nearest segment changes across the frame; its age and depth must not show)
    float glow = 0.75 * (exp(-d / halo) * 0.55 + exp(-d / (halo * 4.0)) * 0.18);
    float headGlow = exp(-age * 60.0) * exp(-d * d / (9.0 * wBeam * wBeam));
    float bright = (0.55 + 0.35 * gPulse + 0.25 * gChordPulse) * (voices == 0 ? 0.45 : 1.0);   // idle: a dim 3:4:5
    beam = hotCore(beamCol, 1.6 + 0.8 * gPulse) * core * bright * 1.5 + beamCol * glow * bright * (0.8 + 1.2 * u_k2);
    beam += vec3(1.0) * headGlow * 0.8;
  }
  col += beam;

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.2);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  // the phosphor: last frame's light fades slowly, so the old figure lingers under the new one
  vec3 prev = texture(u_prev, v_uv).rgb;
  vec3 trail = max(prev * (0.55 + 0.42 * u_k5) - 1.0 / 255.0, 0.0);
  outColor = vec4(clamp(max(col, trail), 0.0, 1.0), 1.0);
}
