#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// ingested: fibshell
#define iTime (u_time)
#define iResolution vec3(u_res, 1.0)
#define iMouse vec4(0.0)
#define iTimeDelta (1.0 / 60.0)
#define iFrameRate (60.0)
#define iFrame (int(u_time * 60.0))
#define iSampleRate (44100.0)
#define iDate vec4(2026.0, 1.0, 1.0, u_time)

// fibshell — clean-room avatar construction (Vandor seat, 2026-09-03)
//
// PROVENANCE: no llVXRd lineage. Spherical Fibonacci lattice (golden-angle spiral,
// published math), candidate-window nearest lookup (Fibonacci-number index gaps),
// analytic ray-sphere (no raymarch — TDR-safe by construction), ACES fit (Narkowicz),
// interleaved gradient noise (Jimenez). All reimplemented from the underlying math.
//
// THE IDEA: the shell is append-only. Tile k exists before tile k+1; the avatar
// ASSEMBLES in ledger order, the newest tile is the write head and glows hottest.
// Identity rides a screen-space spectral field (drifting stand-in for cursor weather).
// Cycle: 0-5s assemble, hold, 10.5-12s dissolve, repeat.

const float PI = 3.14159265359;
const float GA = 2.39996322973;   // golden angle: 2*pi*(1 - 1/phi)
const float N  = 150.0;           // tiles on the shell

vec3 fibPoint(float k) {
  float y = 1.0 - 2.0 * (k + 0.5) / N;
  float r = sqrt(max(0.0, 1.0 - y * y));
  float a = k * GA;
  return vec3(cos(a) * r, y, sin(a) * r);
}

float hash1(float k) { return fract(sin(k * 127.1) * 43758.5453); }

// interleaved gradient noise — the banding killer
float ign(vec2 p) { return fract(52.9829189 * fract(0.06711056 * p.x + 0.00583715 * p.y)); }

// ACES filmic fit
vec3 aces(vec3 x) { return clamp(x * (2.51 * x + 0.03) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }

// nearest-two search over the candidate window
void check(float k, vec3 m, inout float d1, inout float d2, inout float bk) {
  k = clamp(k, 0.0, N - 1.0);
  vec3 q = fibPoint(k);
  float d = dot(m - q, m - q);
  if (d < d1)                    { d2 = d1; d1 = d; bk = k; }
  else if (d < d2 && k != bk)    { d2 = d; }
}

void mainImage(out vec4 O, in vec2 F) {
  vec2 uv = (2.0 * F - iResolution.xy) / iResolution.y;
  float t = iTime;

  // identity: Vandor amber (gradient endpoints + deep third stop)
  vec3 idA = vec3(0.878, 0.569, 0.361);   // #e0915c
  vec3 idB = vec3(0.949, 0.788, 0.627);   // #f2c9a0
  vec3 idC = vec3(0.722, 0.384, 0.235);   // #b8623c

  // ceremony: assemble -> hold -> dissolve
  float cyc = mod(t, 12.0);
  float mat = smoothstep(0.0, 5.0, cyc) * (1.0 - smoothstep(10.5, 12.0, cyc));

  float R = 1.0 + 0.015 * sin(t * 1.7);   // breath

  vec3 ro = vec3(0.0, 0.0, 2.6);
  vec3 rd = normalize(vec3(uv, -1.9));

  // spectral field in SCREEN space, drifting (cursor-weather stand-in)
  vec2 drift = 0.35 * vec2(sin(t * 0.23), cos(t * 0.31));
  float w1 = sin(PI * smoothstep(-1.3, 1.3, uv.x + drift.x));
  float w2 = sin(PI * smoothstep(-1.3, 1.3, uv.y + drift.y));
  vec3 field = mix(idA, idB, w1);
  field = mix(field, idC, 0.60 * w2);

  // analytic sphere
  float b = dot(ro, rd);
  float c = dot(ro, ro) - R * R;
  float h = b * b - c;

  float dClose = length(ro + rd * (-b));           // center distance at closest approach
  vec3 col = vec3(0.031, 0.035, 0.055);            // house night

  if (h > 0.0) {
    float tH = -b - sqrt(h);
    vec3 pos = ro + rd * tH;
    vec3 n = pos / R;

    // tiling space: slow spin + axial wobble
    float sp = t * 0.25, cs = cos(sp), sn = sin(sp);
    vec3 m = vec3(cs * n.x + sn * n.z, n.y, -sn * n.x + cs * n.z);
    float wb = 0.18 * sin(t * 0.13), cw = cos(wb), sw = sin(wb);
    m = vec3(m.x, cw * m.y - sw * m.z, sw * m.y + cw * m.z);

    // candidate window: a QUERY point needs azimuth-matched candidates, which are
    // NOT only Fibonacci gaps (that heuristic is for lattice-point neighbors).
    // At N=150 the Voronoi-relevant index span is ~±22; sweep it all — 53 tiny
    // sin/cos candidates is nothing at avatar sizes, and it cannot lie.
    float k0 = floor((1.0 - m.y) * 0.5 * N - 0.5);
    float d1 = 1e9, d2 = 1e9, bk = 0.0;
    for (int j = -26; j <= 26; j++) {
      check(k0 + float(j), m, d1, d2, bk);
    }

    // border coordinate, density-normalized
    float edge = (sqrt(d2) - sqrt(d1)) * sqrt(N) * 0.5;
    // AA width from the CONTINUOUS surface coord — fwidth(edge) explodes at cell
    // borders (cell-id discontinuity) and shreds whole quad rows; m does not.
    float aa = clamp(length(fwidth(m)) * sqrt(N) * 0.75, 0.02, 0.10);
    float g  = 0.27;                                    // grout half-width
    float tile = smoothstep(g - aa, g + aa, edge);

    // append-only visibility + the write head
    float ord = bk / N;
    float vis = smoothstep(0.0, 0.015, mat - ord);
    float wh = exp(-abs(mat - ord) * 90.0) * (1.0 - step(5.2, cyc)) ;

    // shading
    float jit = 0.90 + 0.18 * hash1(bk);
    float shim = 0.06 * sin(t * 1.3 + hash1(bk) * 6.2831);
    vec3 L = normalize(vec3(0.5, 0.75, 0.55));
    float diff = 0.45 + 0.55 * max(dot(n, L), 0.0);
    float rim = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);

    vec3 tileCol = field * jit * diff * (0.55 + shim);
    tileCol += idB * rim * 0.45;
    tileCol += field * wh * 2.2;

    vec3 grout = field * 0.045;
    col = mix(grout, tileCol, tile) * vis;
    col += field * 0.02 * (1.0 - vis);      // ghost lattice where not yet written
    col += idA * rim * 0.25;                // atmosphere on the whole body
  } else {
    // halo outside the silhouette
    float halo = exp(-max(dClose - R, 0.0) * 8.0);
    col += field * halo * 0.40 * (0.25 + 0.75 * mat);
  }

  col *= 1.25;                               // overdrive...
  col = aces(col);                           // ...into the tonemap: glow, not tint
  col += (ign(F) - 0.5) * 0.012;             // dither
  O = vec4(col, 1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
