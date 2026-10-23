#version 300 es
//! {"id": "vj-geometry-hall", "name": "VJ Geometry Hall", "author": "Vandor", "tags": ["vj", "generative", "raymarch", "beat", "chord", "pads"], "params": [{"k": 1, "name": "snap", "default": 0.6}, {"k": 2, "name": "edges", "default": 0.65}, {"k": 3, "name": "hall", "default": 0.55}, {"k": 4, "name": "fog", "default": 0.5}, {"k": 5, "name": "trails", "default": 0.2}, {"k": 6, "name": "size", "default": 0.5}]}
precision highp float;

// Geometry Hall (arsenal/web/vj.html, Play-loadable). A raymarched hall of pillars that drifts toward you, and in it one
// polyhedron of dark glass with neon edges. The solid is the chord: three tones a tetrahedron, four an octahedron, five
// or more an icosahedron, a bare note or two a cube; on a chord change it pops small and springs back as the new solid
// while the palette travels. It snaps to a new orientation on every beat (a quarter-beat eased snap with a little
// overshoot; the angles step by fractions of a turn that come round whole over the 64-beat counter, so the wrap never
// shows). The kick lights the edges, the bass the fog; the pads light the pillars' strips in their colours, pad 1 to 6
// on the left, 7 to 12 on the right, nearest first. Cost is bounded: 64 march steps at most, and the hall is one box per
// side under domain repetition.

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
const float PHI = 1.61803398875;

// ------------------------------------------------------------- the VJ strip (arsenal/web/vj-core.js STRIP, v1) --
bool gHost;
vec3 gPal[4];
float gPhase, gPulse, gCount, gChordPulse, gKick, gTravel;
int gTones;

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
    gChordPulse = vjAt(15, 0).x;
    vec4 hit = vjAt(12, 1);
    gKick = max(hit.y, max(0.6 * hit.x, 0.7 * gPulse));
    gTravel = vjAt(8, 2).x;
    // distinct pitch classes among the stars
    int count = int(vjAt(9, 2).x + 0.5);
    int seen[12];
    for (int i = 0; i < 12; i++) seen[i] = 0;
    gTones = 0;
    for (int s = 0; s < 16; s++) {
      if (s >= count) break;
      float pcf = vjAt(s, 4).w;
      if (pcf < -0.5) continue;
      int pc = int(pcf + 0.5);
      pc = pc - 12 * (pc / 12);
      if (seen[pc] == 0) { seen[pc] = 1; gTones++; }
    }
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.52); gPal[1] = hueLinear(h + 0.80); gPal[2] = hueLinear(h + 0.62); gPal[3] = hueLinear(h + 0.05);
    gPhase = fract(u_time * 2.0); gPulse = u_beat;
    gCount = mod(floor(u_time * 2.0), 64.0);
    gChordPulse = 0.0;
    gKick = max(u_beat, 0.7 * u_flux);
    gTravel = clamp(fract(u_time / 6.0) * 6.0, 0.0, 1.0);
    gTones = 1 + int(mod(floor(u_time / 6.0), 5.0));
  }
}

vec3 padColour(int i) { return gHost ? vjAt(i, 3).rgb : gPal[i - 4 * (i / 4)]; }

float padEnv(int i) {
  if (gHost) return vjAt(i, 0).x;
  float band = i < 4 ? u_high : (i < 8 ? u_mid : u_bass);
  float gate = smoothstep(0.6, 0.98, 0.5 + 0.5 * sin(u_time * 0.7 + float(i) * 2.4));
  return smoothstep(0.55, 0.9, band) * gate;
}

// ------------------------------------------------------------------------------------------------- light parts --
vec3 hotCore(vec3 tint, float heat) {      // light-glow glowHotCore
  float h = max(heat, 0.0);
  vec3 hue = max(tint, vec3(0.0));
  float peak = max(hue.r, max(hue.g, hue.b));
  return h * mix(hue, vec3(peak), h * h / (1.0 + h * h));
}
mat3 rotX(float a) { float c = cos(a), s = sin(a); return mat3(1.0, 0.0, 0.0, 0.0, c, s, 0.0, -s, c); }
mat3 rotY(float a) { float c = cos(a), s = sin(a); return mat3(c, 0.0, -s, 0.0, 1.0, 0.0, s, 0.0, c); }
mat3 rotZ(float a) { float c = cos(a), s = sin(a); return mat3(c, s, 0.0, -s, c, 0.0, 0.0, 0.0, 1.0); }

// the polyhedra as planes (generalized distance functions): the largest plane distance, the runner-up (for the edges)
// and the winning normal
vec3 gNormal;
float gSecond;
void plane(vec3 p, vec3 n, inout float best) {
  float d = dot(p, n);
  if (d > best) { gSecond = best; best = d; gNormal = n; }
  else if (d > gSecond) gSecond = d;
}
void plane2(vec3 p, vec3 n, inout float best) { plane(p, n, best); plane(p, -n, best); }
float solid(vec3 p, int kind, float r) {
  float best = -1e9;
  gSecond = -1e9;
  gNormal = vec3(0.0, 0.0, 1.0);
  if (kind == 0) {                       // cube
    plane2(p, vec3(1.0, 0.0, 0.0), best); plane2(p, vec3(0.0, 1.0, 0.0), best); plane2(p, vec3(0.0, 0.0, 1.0), best);
    return best - r * 0.62;
  }
  vec3 a = vec3(0.57735);
  if (kind == 1) {                       // tetrahedron
    plane(p, a, best); plane(p, vec3(-a.x, -a.y, a.z), best); plane(p, vec3(-a.x, a.y, -a.z), best); plane(p, vec3(a.x, -a.y, -a.z), best);
    return best - r * 0.42;
  }
  plane2(p, a, best); plane2(p, vec3(-a.x, a.y, a.z), best); plane2(p, vec3(a.x, -a.y, a.z), best); plane2(p, vec3(a.x, a.y, -a.z), best);
  if (kind == 2) return best - r * 0.62; // octahedron
  // icosahedron: the octahedron's eight faces and twelve more
  float k = 1.0 / sqrt(1.0 + (PHI + 1.0) * (PHI + 1.0));
  plane2(p, vec3(0.0, 1.0, PHI + 1.0) * k, best); plane2(p, vec3(0.0, -1.0, PHI + 1.0) * k, best);
  plane2(p, vec3(PHI + 1.0, 0.0, 1.0) * k, best); plane2(p, vec3(-PHI - 1.0, 0.0, 1.0) * k, best);
  plane2(p, vec3(1.0, PHI + 1.0, 0.0) * k, best); plane2(p, vec3(-1.0, PHI + 1.0, 0.0) * k, best);
  return best - r * 0.72;
}

// the hall: a pillar every 4 units on each side, a floor and a ceiling
float hall(vec3 p, out float side, out float row) {
  side = p.x < 0.0 ? 0.0 : 1.0;
  row = floor(p.z / 4.0 + 0.5);
  vec3 q = vec3(abs(p.x) - 3.2, p.y, p.z - row * 4.0);
  vec3 b = abs(q) - vec3(0.32, 6.0, 0.32);
  float pillar = length(max(b, 0.0)) + min(max(b.x, max(b.y, b.z)), 0.0);
  float floorD = p.y + 1.7;
  float ceil = 3.4 - p.y;
  return min(pillar, min(floorD, ceil));
}

int gKind;
mat3 gRot;
vec3 gCenter;
float gR;
float scene(vec3 p, out int what) {
  float s, rw;
  float h = hall(p, s, rw);
  float d = solid(gRot * (p - gCenter), gKind, gR);
  what = d < h ? 1 : 0;
  return min(d, h);
}

void main() {
  vjLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float t = u_time;
  float bass = clamp(0.65 * u_bass + 0.35 * u_pulse, 0.0, 1.5);

  // the solid: the chord's size picks it; a chord change pops it small and springs it back
  gKind = gTones <= 2 ? 0 : (gTones == 3 ? 1 : (gTones == 4 ? 2 : 3));
  float tr = clamp(gTravel, 0.0, 1.0);
  float pop = 0.55 + 0.45 * (1.0 + 2.2 * pow(tr - 1.0, 3.0) + 1.2 * pow(tr - 1.0, 2.0));
  gR = (0.75 + 0.6 * u_k6) * pop * (1.0 + 0.06 * gKick);
  // the beat snap: angles step by whole fractions of a turn (64 steps make whole turns), eased over a quarter beat
  float k = clamp(gPhase * 4.0, 0.0, 1.0);
  float snap = 1.0 + 2.4 * pow(k - 1.0, 3.0) + 1.4 * pow(k - 1.0, 2.0);
  float beats = gCount - 1.0 + snap * u_k1 + (1.0 - u_k1);
  gRot = rotY(beats * (TAU * 5.0 / 64.0) + t * 0.05) * rotX(beats * (TAU * 3.0 / 64.0)) * rotZ(beats * (TAU * 7.0 / 64.0) + 0.3);

  // the camera drifts down the hall at a constant pace
  float zc = t * 0.9;
  vec3 ro = vec3(0.25 * sin(t * 0.13), 0.35 + 0.1 * sin(t * 0.21), zc);
  gCenter = vec3(0.0, 0.55, zc + 5.0);
  vec3 fwd = normalize(gCenter - ro + vec3(0.0, -0.2, 0.0));
  vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), fwd));
  vec3 up = cross(fwd, right);
  vec3 rd = normalize(fwd * 1.35 + right * p.x + up * p.y);

  // march: at most 64 steps, out to 48 units; the glow around the solid gathers on the way
  float dist = 0.0;
  int what = 0;
  bool hit = false;
  float halo = 0.0;
  for (int i = 0; i < 64; i++) {
    vec3 pos = ro + rd * dist;
    int w;
    float d = scene(pos, w);
    if (w == 1) halo += exp(-max(d, 0.0) * 6.0) * 0.02;
    if (d < 0.0015 * dist + 0.0008) { hit = true; what = w; break; }
    dist += d * 0.9;
    if (dist > 48.0) break;
  }
  vec3 pos = ro + rd * dist;
  vec3 fogCol = mix(gPal[1], gPal[2], 0.5) * (0.006 + 0.03 * bass * u_k4);
  vec3 col = fogCol;
  if (hit) {
    if (what == 1) {
      vec3 lp = gRot * (pos - gCenter);
      solid(lp, gKind, gR);                            // sets gNormal and gSecond for the hit point
      vec3 n = transpose(gRot) * gNormal;              // the winning face's normal, back in world space
      float gap = dot(lp, gNormal) - gSecond;          // 0 where two faces meet: an edge
      float edge = 1.0 - smoothstep(0.0, 0.03 + 1.5 * dist * px, gap);
      float fres = pow(1.0 - clamp(dot(n, -rd), 0.0, 1.0), 3.0);
      vec3 face = gPal[1] * 0.02 + mix(gPal[0], gPal[2], 0.5 + 0.5 * n.y) * (0.03 + 0.12 * max(dot(n, normalize(vec3(0.4, 0.8, -0.5))), 0.0));
      face += mix(gPal[2], vec3(1.0), 0.3) * fres * 0.35;
      vec3 edgeCol = mix(gPal[0], gPal[3], 0.3 + 0.3 * sin(t * 0.4));
      col = face + hotCore(edgeCol, 1.0 + 1.5 * gKick + 0.8 * gChordPulse) * edge * (0.5 + 1.1 * u_k2);
    } else {
      float side, row;
      hall(pos, side, row);
      // pillars: a lit strip on the face toward the aisle; the pads light them, nearest rows first
      float strip = 0.0;
      vec3 stripCol = vec3(0.0);
      if (pos.y > -1.69 && pos.y < 3.39) {
        float rel = row - floor(zc / 4.0 + 0.5);
        int slot = int(clamp(rel - 1.0, 0.0, 5.0));
        int pad = int(side) * 6 + slot;
        float env = rel >= 1.0 && rel <= 6.0 ? padEnv(pad) : 0.0;
        float lz = abs(pos.z - row * 4.0);
        strip = (1.0 - smoothstep(0.05, 0.09, lz)) * step(abs(abs(pos.x) - 2.88), 0.02);
        stripCol = mix(gPal[2] * 0.12 * u_k3, hotCore(padColour(pad), 1.3), clamp(env, 0.0, 1.0));
      }
      // the floor: a faint grid in the palette, the ceiling dark
      float grid = 0.0;
      if (pos.y < -1.69) {
        vec2 g = abs(fract(pos.xz * 0.5) - 0.5);
        grid = exp(-min(g.x, g.y) / (0.012 + dist * 0.002));
      }
      col = vec3(0.004, 0.004, 0.007) + gPal[1] * 0.010 * u_k3 + stripCol * strip * 1.6 + gPal[0] * grid * 0.06 * u_k3;
      // the solid's light on the floor beneath it
      col += mix(gPal[0], gPal[2], 0.5) * 0.10 * exp(-length(pos.xz - gCenter.xz) * 0.7) * step(pos.y, -1.69) * (0.6 + gKick);
    }
  }
  float fog = 1.0 - exp(-dist * (0.025 + 0.06 * u_k4));
  col = mix(col, fogCol, fog);
  col += mix(gPal[0], gPal[3], 0.4) * halo * (0.6 + 1.2 * gKick) * u_k2;

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.2);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  vec3 prev = texture(u_prev, v_uv).rgb;
  vec3 trail = max(prev * (0.2 + 0.6 * u_k5) - 2.0 / 255.0, 0.0);
  outColor = vec4(clamp(max(col, trail), 0.0, 1.0), 1.0);
}
