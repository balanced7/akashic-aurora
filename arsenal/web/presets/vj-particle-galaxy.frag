#version 300 es
//! {"id": "vj-particle-galaxy", "name": "VJ Particle Galaxy", "author": "Vandor", "tags": ["vj", "generative", "bass", "keys", "chord", "pads", "feedback"], "params": [{"k": 1, "name": "arms", "default": 0.4}, {"k": 2, "name": "swirl", "default": 0.65}, {"k": 3, "name": "dust", "default": 0.5}, {"k": 4, "name": "core", "default": 0.55}, {"k": 5, "name": "trails", "default": 0.25}, {"k": 6, "name": "novae", "default": 0.75}]}
precision highp float;

// Particle Galaxy (arsenal/web/vj.html, Play-loadable). A spiral galaxy seen at a tilt. The arms are a density wave: a
// logarithmic spiral pattern that turns slowly and rigidly while the stars themselves orbit faster inside than out (the
// angular speed falls as 1/r, a flat rotation curve), so stars stream through the arms the way they do in the sky. The
// bass winds the arms tighter -- the swirl -- and lets them relax; the kick flares the core. Every star has a pitch class:
// when you play a note, every star of that class across the disc lights up in its pitch colour, so a chord lights a
// galaxy-wide constellation of its colours. The chord's palette tints the arms and the dust. The pads set off novae in the
// arms at twelve fixed places on the disc (they orbit with it): a flash in the pad's colour and a shell that expands with
// time since the hit. Stars live in co-rotating cells; the shear of differential rotation would wind any field into
// threads, so two copies of the field, half a period apart, fade into each other every 24 seconds. Any pad hit (the
// strip's shared hit input, 2026-10-24) spins the galaxy up: the arms whirl forward and wind tighter, the trails smear
// round with them, the core flares and the stars brighten, then it all settles back as the hit decays.

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

// ------------------------------------------------------------- the VJ strip (arsenal/web/vj-core.js STRIP, v1) --
bool gHost;
vec3 gPal[4];
float gPulse, gChordPulse, gKick;
float gPcLevel[12];

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
    for (int pc = 0; pc < 12; pc++) { vec4 v = vjAt(pc, 1); gPcLevel[pc] = max(v.x, v.y); }
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.58); gPal[1] = hueLinear(h + 0.78); gPal[2] = hueLinear(h + 0.66); gPal[3] = hueLinear(h + 0.08);
    gPulse = u_beat;
    gChordPulse = 0.0;
    gKick = max(u_beat, 0.7 * u_flux);
    float slot = floor(u_time / 2.0);
    for (int pc = 0; pc < 12; pc++) gPcLevel[pc] = step(0.75, fract(sin(slot * 37.1 + float(pc) * 11.7) * 43758.5)) * u_mid;
  }
}

vec3 padColour(int i) { return gHost ? vjAt(i, 3).rgb : gPal[i - 4 * (i / 4)]; }

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


vec3 padLevel(int i) {          // (envelope, velocity, seconds since press)
  if (gHost) return vjAt(i, 0).xyz;
  float slot = floor(u_time / 3.0 + float(i) * 0.29);
  float age = u_time - (slot - float(i) * 0.29) * 3.0;
  float on = step(0.75, fract(sin(slot * 12.9898 + float(i) * 78.233) * 43758.5453));
  return vec3(on * exp(-age * 0.7) * smoothstep(0.4, 0.8, u_level + 0.2), 0.8, age);
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
mat2 rot(float a) { float c = cos(a), s = sin(a); return mat2(c, s, -s, c); }

// the stars of one field copy at disc position d (disc units), seed `seed`, time `tt` since the copy began; armD 0..1 is
// the arm density here and disc the disc's brightness profile: stars are likelier and brighter in the arms and near the core
vec3 starField(vec2 d, float r, float tt, float seed, float armD, float disc, float pxDisc) {
  vec3 acc = vec3(0.0);
  float omega = 0.10 / (r + 0.06);                       // flat rotation curve: angular speed ~ 1/r
  vec2 q = rot(-omega * tt) * d;                          // back to where this patch of disc was when the copy began
  for (int layer = 0; layer < 2; layer++) {
    float density = layer == 0 ? 60.0 : 130.0;
    vec2 cell = floor(q * density);
    float h = hash12(cell + seed * 31.0 + float(layer) * 7.0);
    float chance = (layer == 0 ? 0.05 : 0.08) * (0.25 + 1.6 * armD) * (0.3 + disc);
    if (h < 1.0 - chance) continue;
    vec2 sp = (cell + 0.5 + 0.6 * (vec2(hash12(cell + 1.7 + seed), hash12(cell + 4.3 + seed)) - 0.5)) / density;
    float dd = length(q - sp) / pxDisc;
    float size = layer == 0 ? 1.3 : 0.85;
    float b = 0.35 + 0.65 * hash12(cell * 2.9 + seed);
    int pc = int(floor(hash12(cell * 1.31 + seed + 9.0) * 12.0));
    float lit = gPcLevel[pc];
    // young blue-white stars in the arms, older yellow ones between them and in the bulge
    vec3 tint = mix(vec3(1.0, 0.82, 0.6), vec3(0.72, 0.82, 1.0), clamp(armD * 1.4, 0.0, 1.0));
    tint = mix(tint, gPal[2] * 1.4, 0.2 * armD);
    tint = mix(tint, PC_COL[pc] * 1.3, clamp(lit, 0.0, 1.0));
    acc += tint * exp(-dd * dd / (size * size)) * b * (0.35 + 0.65 * disc) * (1.0 + 2.5 * lit);
  }
  return acc;
}

void main() {
  vjLoad();
  hitLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float t = u_time;
  float bass = clamp(0.65 * u_bass + 0.35 * u_pulse, 0.0, 1.5);

  // the disc: tilted toward us and turned in the frame
  float tilt = 0.95 + 0.08 * sin(t * 0.05);
  vec2 s = rot(0.35) * p;
  vec2 d = vec2(s.x, s.y / cos(tilt)) * 1.15;
  float pxDisc = px * 1.15 / cos(tilt) * 0.75 + px * 0.25;
  float r = length(d) + 1e-5;
  float th = atan(d.y, d.x);

  // the arms: a log spiral pattern turning slowly and rigidly; the bass winds it tighter
  float arms = floor(2.0 + 3.0 * u_k1 + 0.5);
  float wind = (2.2 + 1.6 * u_k2 * bass) * (1.0 + 0.4 * gKick * u_k2);
  float pattern = th - t * 0.04 - 0.9 * gHit - log(r) * wind * (1.0 + 0.25 * gHit);
  float armD = pow(0.5 + 0.5 * cos(arms * pattern), 3.0) * smoothstep(0.03, 0.12, r) * exp(-r * 2.6);
  // dust lanes on the arms' inner edges, darker in the palette's deep colour
  float lane = pow(0.5 + 0.5 * cos(arms * (pattern + 0.35)), 8.0) * (0.5 + 0.5 * vnoise(d * 18.0 + t * 0.02));
  vec3 armCol = mix(gPal[0], gPal[2], 0.5 + 0.5 * sin(pattern * 0.5)) * (1.0 + 0.6 * gChordPulse);

  vec3 col = vec3(0.0006, 0.0006, 0.0012);
  // far stars behind the disc
  vec2 bc = floor(p * 120.0);
  float bh = hash12(bc + 77.0);
  if (bh > 0.985) col += vec3(0.6, 0.7, 1.0) * exp(-dot(p - (bc + 0.5) / 120.0, p - (bc + 0.5) / 120.0) / (1.2 * px * px)) * (bh - 0.985) * 40.0;
  // the diffuse glow of the arms and the disc
  float disc = exp(-r * 3.2);
  col += armCol * armD * (0.22 + 0.12 * bass) + mix(gPal[1], gPal[0], 0.5) * disc * 0.04;
  col *= 1.0 - 0.75 * lane * u_k3 * smoothstep(0.04, 0.15, r);

  // the stars: two copies of the co-rotating field, half a period apart, cross-fading
  float T = 24.0;
  float ta = mod(t, T), tb = mod(t + 0.5 * T, T);
  float wa = 1.0 - abs(ta / T * 2.0 - 1.0);              // a triangle: 0 when a copy starts or ends
  float wb = 1.0 - wa;
  float seedA = floor(t / T), seedB = floor((t + 0.5 * T) / T) + 0.5;
  float armS = clamp(armD * 4.0, 0.0, 1.0);
  float discS = exp(-r * 2.4);
  vec3 stars = starField(d, r, ta, seedA, armS, discS, pxDisc) * wa + starField(d, r, tb, seedB, armS, discS, pxDisc) * wb;
  col += stars * (0.9 + 0.4 * u_level + 0.8 * gHit);

  // the core: a bulge that the kick flares
  float bulge = exp(-r * r / (0.004 + 0.004 * u_k4));
  col += hotCore(mix(gPal[3], vec3(1.0, 0.9, 0.7), 0.6), 1.0 + 1.2 * gKick + 1.8 * gHit) * bulge * (0.25 + 0.5 * u_k4);
  col += mix(gPal[3], gPal[0], 0.3) * 0.02 / (0.02 + r * r * 30.0) * (0.3 + 0.5 * bass) * u_k4;

  // novae: pad i at a fixed place in the arms, orbiting with the disc; a flash and an expanding shell
  for (int i = 0; i < 12; i++) {
    vec3 lv = padLevel(i);
    if (lv.x < 0.002) continue;
    float fi = float(i);
    float rr = 0.10 + 0.028 * fi;
    float aa = fi * 2.399 + log(rr) * wind;              // on the golden angle, nudged onto the arms
    float om = 0.10 / (rr + 0.06);
    vec2 at = rr * vec2(cos(aa + om * t), sin(aa + om * t));
    float dn = length(d - at) / pxDisc;
    vec3 tint = padColour(i);
    float shellR = (8.0 + 160.0 * (1.0 - exp(-lv.z * 1.8))) * (0.6 + 0.6 * lv.y);
    float shell = exp(-pow((dn - shellR) / (2.0 + shellR * 0.08), 2.0));
    col += hotCore(tint, 1.5) * lv.x * (exp(-dn * dn / (9.0 + 30.0 * lv.y)) * 1.4 + 0.25 / (1.0 + dn * 0.08)) * u_k6;
    col += tint * shell * lv.x * 0.5 * u_k6;
  }

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.15);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  // trails: last frame turned with the inner disc, so bright things leave short arcs
  vec2 back = rot(-0.003 - 0.004 * bass - 0.035 * gHit) * p;
  vec3 prev = texture(u_prev, back / vec2(asp, 1.0) + 0.5).rgb;
  vec3 trail = max(prev * (0.3 + 0.6 * u_k5) - 2.0 / 255.0, 0.0);
  outColor = vec4(clamp(max(col, trail), 0.0, 1.0), 1.0);
}
