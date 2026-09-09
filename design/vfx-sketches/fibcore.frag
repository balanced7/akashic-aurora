#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// ingested: fibcore
#define iTime (u_time)
#define iResolution vec3(u_res, 1.0)
#define iMouse vec4(0.0)
#define iTimeDelta (1.0 / 60.0)
#define iFrameRate (60.0)
#define iFrame (int(u_time * 60.0))
#define iSampleRate (44100.0)
#define iDate vec4(2026.0, 1.0, 1.0, u_time)

// fibcore — fibshell + core + orbiters + chroma wave + two-scale morph (Vandor, 2026-09-03)
//
// CLEAN-ROOM, same provenance as fibshell: spherical Fibonacci lattice (published math),
// exhaustive candidate window, analytic sphere + analytic point-glow orbiters. No raymarch.
//
// NEW IN THIS SKETCH (Daniil's round-two directions):
//  * CHROMA — an RGB illumination wave that travels in LEDGER ORDER along the spiral;
//    tiles lift (height+bevel, fake-3D) as the wave passes. 0.0 = pure identity.
//  * MORPH — the tessellation breathes between two golden-ratio scales (N and ~phi^2*N):
//    cells subdivide into children and merge back. Self-similar, hence "from fractals".
//  * CORE + ORBITERS — a breathing nucleus seen through the grout, and movers that hop
//    waypoint-to-waypoint between tile centers, dimming (never vanishing) behind the shell.
//
// PLAY KNOBS (edit + re-ingest):
#define CHROMA   0.45      // 0..1  how much RGB rides the wave (identity always the base)
#define MORPH    1         // 0/1   two-scale tessellation breathing
#define ORBITERS 7         // 0..10 movers on waypoint hops

const float PI = 3.14159265359;
const float GA = 2.39996322973;
const float N1 = 150.0;            // coarse shell
const float N2 = 393.0;            // child lattice ~ phi^2 * N1

vec3 fibPt(float k, float N) {
  float y = 1.0 - 2.0 * (k + 0.5) / N;
  float r = sqrt(max(0.0, 1.0 - y * y));
  float a = k * GA;
  return vec3(cos(a) * r, y, sin(a) * r);
}

float hash1(float k) { return fract(sin(k * 127.1) * 43758.5453); }
float ign(vec2 p) { return fract(52.9829189 * fract(0.06711056 * p.x + 0.00583715 * p.y)); }
vec3 aces(vec3 x) { return clamp(x * (2.51 * x + 0.03) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
float ease(float x) { return x * x * (3.0 - 2.0 * x); }

// classic RGB cycle for the chroma wave
vec3 rgbCycle(float x) { return 0.5 + 0.5 * cos(6.2831 * x + vec3(0.0, 2.094, 4.188)); }

// nearest-2 on lattice N over window +/-W around latitude estimate
void nearest2(vec3 m, float N, float W, out float d1, out float d2, out float bk) {
  float k0 = floor((1.0 - m.y) * 0.5 * N - 0.5);
  d1 = 1e9; d2 = 1e9; bk = 0.0;
  for (float j = -W; j <= W; j += 1.0) {
    float k = clamp(k0 + j, 0.0, N - 1.0);
    vec3 q = fibPt(k, N);
    float d = dot(m - q, m - q);
    if (d < d1)                 { d2 = d1; d1 = d; bk = k; }
    else if (d < d2 && k != bk) { d2 = d; }
  }
}

// circular ledger distance (wave chases k/N around the append loop)
float ringDist(float a, float b) { float d = abs(a - b); return min(d, 1.0 - d); }

void mainImage(out vec4 O, in vec2 F) {
  vec2 uv = (2.0 * F - iResolution.xy) / iResolution.y;
  float t = iTime;

  vec3 idA = vec3(0.878, 0.569, 0.361);
  vec3 idB = vec3(0.949, 0.788, 0.627);
  vec3 idC = vec3(0.722, 0.384, 0.235);

  float cyc = mod(t, 12.0);
  float mat = smoothstep(0.0, 5.0, cyc) * (1.0 - smoothstep(10.5, 12.0, cyc));
  float R = 1.0 + 0.015 * sin(t * 1.7);

  vec3 ro = vec3(0.0, 0.0, 2.6);
  vec3 rd = normalize(vec3(uv, -1.75));

  vec2 drift = 0.35 * vec2(sin(t * 0.23), cos(t * 0.31));
  float w1 = sin(PI * smoothstep(-1.3, 1.3, uv.x + drift.x));
  float w2 = sin(PI * smoothstep(-1.3, 1.3, uv.y + drift.y));
  vec3 field = mix(idA, idB, w1);
  field = mix(field, idC, 0.60 * w2);

  float b = dot(ro, rd);
  float c = dot(ro, ro) - R * R;
  float h = b * b - c;
  float dClose = length(ro + rd * (-b));

  // tiling-space rotation (world -> lattice); movers use the inverse (lattice -> world)
  float sp = t * 0.25, cs = cos(sp), sn = sin(sp);
  float wb = 0.18 * sin(t * 0.13), cw = cos(wb), sw = sin(wb);

  vec3 col = vec3(0.031, 0.035, 0.055);
  float tHit = 1e9;
  float tileMask = 0.0;     // solid written tile face covering this pixel
  float unwritten = 0.0;    // shell not yet materialized here

  if (h > 0.0) {
    tHit = -b - sqrt(h);
    vec3 pos = ro + rd * tHit;
    vec3 n = pos / R;

    vec3 m = vec3(cs * n.x + sn * n.z, n.y, -sn * n.x + cs * n.z);
    m = vec3(m.x, cw * m.y - sw * m.z, sw * m.y + cw * m.z);

    // coarse lattice
    float d1, d2, bk;  nearest2(m, N1, 26.0, d1, d2, bk);
    float edge1 = (sqrt(d2) - sqrt(d1)) * sqrt(N1) * 0.5;
    float aa1 = clamp(length(fwidth(m)) * sqrt(N1) * 0.75, 0.02, 0.10);

    // child lattice: TRUE subdivision — parent borders stay as the skeleton,
    // child borders fade in WITHIN the faces, then merge away again.
    float edge = edge1, bkv = bk, Nv = N1, aa = aa1;
#if MORPH
    float mph = smoothstep(0.25, 0.75, 0.5 + 0.5 * sin(t * 0.21));
    float e1c, e2c, bkc; nearest2(m, N2, 42.0, e1c, e2c, bkc);
    float edge2 = (sqrt(e2c) - sqrt(e1c)) * sqrt(N2) * 0.5;
    // child grout only cuts as deep as mph allows; parent grout always wins (min)
    edge = min(edge1, mix(edge1, edge2, mph * 0.85));
#endif

    float g = 0.24;
    float tile = smoothstep(g - aa, g + aa, edge);

    float ord = bkv / Nv;
    float vis = smoothstep(0.0, 0.015, mat - ord);
    float wh  = exp(-abs(mat - ord) * 90.0) * (1.0 - step(5.2, cyc));

    // ----- chroma wave in ledger order: illumination + HEIGHT -----
    float wavePos = fract(t * 0.09);
    float chase = exp(-ringDist(ord, wavePos) * 16.0);
    float height = 0.32 * chase + 0.10 * sin(t * 1.1 + hash1(bkv) * 6.2831);
    vec3 waveCol = rgbCycle(ord + t * 0.05);

    float jit = 0.90 + 0.18 * hash1(bkv);
    float shim = 0.06 * sin(t * 1.3 + hash1(bkv) * 6.2831);
    vec3 L = normalize(vec3(0.5, 0.75, 0.55));
    float diff = 0.45 + 0.55 * max(dot(n, L), 0.0);
    float rim = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);

    vec3 faceCol = mix(field, waveCol, CHROMA * chase);
    vec3 tileCol = faceCol * jit * diff * (0.55 + shim) * (0.75 + 0.85 * height);
    tileCol += idB * rim * 0.45;
    tileCol += faceCol * wh * 2.2;

    // bevel ring just inside the face edge — the fake extrusion's lit chamfer
    float bev = smoothstep(g + aa, g + aa + 0.10, edge) - smoothstep(g + aa + 0.10, g + aa + 0.26, edge);
    tileCol += idB * bev * (0.15 + 0.9 * height);

    vec3 grout = field * 0.04;
    col = mix(grout, tileCol, tile) * vis;
    col += field * 0.02 * (1.0 - vis);
    col += idA * rim * 0.25;

    tileMask = tile * vis;
    unwritten = 1.0 - vis;
  } else {
    float halo = exp(-max(dClose - R, 0.0) * 8.0);
    col += field * halo * 0.40 * (0.25 + 0.75 * mat);
  }

  // ----- the core: a breathing nucleus — GLIMPSED through grout, radiant only
  // when the shell is unwritten (naked-core frames stay dramatic) -----
  float coreGlow = exp(-max(dClose - 0.28, 0.0) * 14.0);
  vec3 coreCol = mix(idB, vec3(1.0, 0.95, 0.88), 0.55) * (1.0 + 0.25 * sin(t * 2.4));
  float reveal = clamp((1.0 - tileMask) * 0.30 + unwritten, 0.0, 1.0);
  col += coreCol * coreGlow * reveal * 0.85;

  // ----- orbiters: hop between waypoints (tile centers), occluded => dimmed -----
#if ORBITERS > 0
  for (int i = 0; i < ORBITERS; i++) {
    float sd = float(i) * 17.3 + 4.7;
    float P = 2.2 + 1.5 * hash1(sd);
    float ph = t / P + hash1(sd + 9.1) * 7.0;
    float seg = floor(ph);
    float f = ease(fract(ph));
    float wA = floor(hash1(sd + seg * 3.7) * N1);
    float wB = floor(hash1(sd + (seg + 1.0) * 3.7) * N1);
    vec3 q = normalize(mix(fibPt(wA, N1), fibPt(wB, N1), f)) * (R + 0.16 + 0.05 * sin(t * 2.0 + sd));
    // lattice -> world (inverse of the tiling rotation)
    q = vec3(q.x, cw * q.y + sw * q.z, -sw * q.y + cw * q.z);
    q = vec3(cs * q.x - sn * q.z, q.y, sn * q.x + cs * q.z);

    vec3 toQ = q - ro;
    float tt = dot(toQ, rd);
    float dPt = length(toQ - rd * tt);
    float occ = (tt > tHit) ? 0.15 : 1.0;              // behind the shell: dim, never vanish
    vec3 mCol = mix(idB, rgbCycle(hash1(sd) + t * 0.05), CHROMA);
    float spark = exp(-dPt * dPt * 1600.0) * 1.4;
    float trail = exp(-dPt * dPt * 500.0) * 0.20 * (0.5 + 0.5 * sin(t * 3.0 + sd));
    col += mCol * (spark + trail) * occ * (0.3 + 0.7 * mat);
  }
#endif

  col *= 1.25;
  col = aces(col);
  col += (ign(F) - 0.5) * 0.012;
  O = vec4(col, 1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
