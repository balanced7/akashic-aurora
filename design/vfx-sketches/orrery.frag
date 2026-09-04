#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;

// ingested: orrery
#define iTime (u_time)
#define iResolution vec3(u_res, 1.0)

// orrery v2 — the two lineages married (Vandor, 2026-09-03)
//
// Daniil: "look at the quadratic slices shader and the original shader that inspired
// the avatar and improve your design." Both studied; both are IN here:
//
//  FROM THE ORIGINAL GEODESIC (llVXRd, the three canned animations):
//   * anim2's TRAVELING HEIGHT BANDS -- tiles brighten/lift in horizontal waves that
//     sweep VERTICALLY across the shell (dot(tile, up) phase), the up/down life.
//   * anim3's GAP-OPENING RINGS -- the tile grout WIDENS in rings that propagate from
//     a drifting pole, so the shell structurally BREATHES OPEN in traveling waves...
//   * ...and what the opening reveals is the point:
//
//  FROM THE QUADRIC SLICES SHADER (hal-superquadric):
//   * THE HEART: a superquadric whose single parameter k walks sphere -> cube -> torus
//     (n = 8-6k exponent sweep + a revolution hollow), tumbling on three
//     incommensurate axis rates, morphing forever without repeating.
//   * Z-SLICED rendering: the heart is drawn as thin glowing contours on a ladder of
//     depth slices, far slices dimmed -- translucent layered wire, no raymarch.
//
//  KEPT FROM v1 (the structural answer to "no rotating elements"):
//   * two independent counter-rotating rings of standing pillar-columns, Kepler-coupled
//     (omega ~ r^-1.5; the outer orbit elliptical, fast at perihelion), counter-phased
//     bob on core, rings, and every pillar; honest occlusion; slow orbit-cam parallax.
//
// The composition: a tiled shell that breathes open in traveling rings, and through
// every opening you see a glowing quadric heart becoming other shapes inside it.
// All analytic. No raymarch. Nothing loops on a schedule an eye can learn.

const float PI = 3.14159265359;
const float GA = 2.39996322973;
const float N1 = 150.0;

vec3 fibPt(float k, float N) {
  float y = 1.0 - 2.0 * (k + 0.5) / N;
  float r = sqrt(max(0.0, 1.0 - y * y));
  float a = k * GA;
  return vec3(cos(a) * r, y, sin(a) * r);
}
float hash1(float k) { return fract(sin(k * 127.1) * 43758.5453); }
float ign(vec2 p) { return fract(52.9829189 * fract(0.06711056 * p.x + 0.00583715 * p.y)); }
vec3 aces(vec3 x) { return clamp(x * (2.51 * x + 0.03) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
void pR(inout vec2 p, float a) { p = cos(a) * p + sin(a) * vec2(p.y, -p.x); }

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

float raySeg(vec3 ro, vec3 rd, vec3 a, vec3 b, out float depth) {
  vec3 u = b - a, w = a - ro;
  float ru = dot(rd, u), rw = dot(rd, w), uu = dot(u, u), uw = dot(u, w);
  float den = max(uu - ru * ru, 1e-5);
  float s = clamp((ru * rw - uw) / den, 0.0, 1.0);
  vec3 p = a + u * s;
  depth = dot(p - ro, rd);
  return length(p - (ro + rd * max(depth, 0.0)));
}

// ---- THE HEART (quadric slices lineage) --------------------------------------------
// Superquadric field: k=0 sphere-ish, k -> 1 cube -> torus (exponent sweep + hollow).
// Tumbles on three incommensurate rates exactly as the reference does.
float sqField(vec3 o, float k, float t) {
  vec3 r = vec3(t / 2.3, t / 1.95, t / 2.7), s = sin(r), c = cos(r);
  o *= mat3(
       c.y,     s.z * s.y,                 -s.y * c.z,
      -s.x*s.y, c.x*c.z + s.x*s.z*c.y,      s.z*c.x - s.x*c.z*c.y,
       c.x*s.y, s.x*c.z - c.x*s.z*c.y,      s.z*s.x + c.x*c.z*c.y);
  float n = 8.0 - 6.0 * k, l = 3.8 * k - 2.0;
  o = abs(o);
  return pow(pow(o.x, n) + pow(o.y, n) + pow(o.z, n) + l, 2.0) - k * 8.0 * (o.x*o.x + o.y*o.y);
}
float wireGlow(float d) { return pow(1.0 - min(1.0, abs(d)), 4.0); }

void mainImage(out vec4 O, in vec2 F) {
  vec2 uv = (2.0 * F - iResolution.xy) / iResolution.y;
  float t = iTime;

  vec3 idA = vec3(0.878, 0.569, 0.361);   // house coral (shell)
  vec3 idB = vec3(0.949, 0.788, 0.627);
  vec3 idC = vec3(0.478, 0.635, 0.969);   // peri (outer ring)
  vec3 idH = vec3(0.30, 0.85, 0.95);      // the heart's cyan-white wire

  vec3 ro = vec3(0.0, 0.5, 3.55);
  vec3 rd = normalize(vec3(uv, -1.8));
  pR(ro.xz, t * 0.05); pR(rd.xz, t * 0.05);            // orbit-cam parallax

  float coreBob = 0.14 * sin(t * 0.43);                // core vs rings: counter-phased travel
  vec3 cc = vec3(0.0, coreBob, 0.0);
  float R = 1.02;

  vec3 col = vec3(0.028, 0.031, 0.050);
  col += idB * 0.015 * exp(-uv.x * uv.x * 9.0) * (0.5 + 0.5 * sin(uv.y * 2.0 - t * 0.7));

  // ---------- THE SHELL: fib-tiled sphere with the original's traveling waves --------
  vec3 rc = ro - cc;
  float b = dot(rc, rd), c2 = dot(rc, rc) - R * R, disc = b * b - c2;
  float tHit = 1e9;
  float openness = 0.0;        // how open the shell is along THIS pixel's ray
  if (disc > 0.0) {
    tHit = -b - sqrt(disc);
    vec3 pos = ro + rd * tHit;
    vec3 n = (pos - cc) / R;
    vec3 m = n;
    pR(m.xz, t * 0.20);                                 // the shell body rotates
    float d1, d2, bk; nearest2(m, N1, 26.0, d1, d2, bk);
    float edge = (sqrt(d2) - sqrt(d1)) * sqrt(N1) * 0.5;
    float aa = clamp(length(fwidth(m)) * sqrt(N1) * 0.75, 0.02, 0.10);
    vec3 tc = fibPt(bk, N1);                            // this tile's center, lattice frame

    // anim2 lineage: HEIGHT BANDS traveling vertically -- tiles lift in horizontal
    // waves sweeping up the shell. Brightness + bevel carry the lift (fake-3D).
    float lift = 0.5 + 0.5 * sin(tc.y * 9.0 + t * 1.1);

    // anim3 lineage: GAP-OPENING RINGS from a DRIFTING pole -- the pole itself wanders
    // (three incommensurate rates) so the rings never repeat a path. Where the wave
    // passes, the grout widens: the shell structurally breathes OPEN.
    vec3 pole = normalize(vec3(sin(t * 0.083), cos(t * 0.061), sin(t * 0.047 + 1.7)));
    float ringPhase = acos(clamp(dot(tc, pole), -1.0, 1.0));
    float openWave = pow(0.5 + 0.5 * cos(ringPhase * 7.0 - t * 0.9), 3.0);
    float g = mix(0.20, 0.62, openWave);                // grout width rides the wave
    float tile = smoothstep(g - aa, g + aa, edge);
    openness = 1.0 - tile;                              // open grout = window to the heart

    // v3: NO DEAD HEMISPHERE. Key light from above, a warm bounce fill from below,
    // and the heart's own light leaking onto inner tile faces on the dark side --
    // half the composition was reading as void in Daniil's screenshot.
    vec3 L = normalize(vec3(0.5, 0.8, 0.5));
    float dif = 0.55 + 0.45 * max(dot(n, L), 0.0);
    float bounce = 0.22 * max(dot(n, normalize(vec3(-0.2, -1.0, 0.3))), 0.0);
    float rim = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
    vec3 face = mix(idA, idB, 0.30 + 0.45 * lift) * (0.85 + 0.30 * hash1(bk));
    float bev = smoothstep(g + aa, g + aa + 0.10, edge) - smoothstep(g + aa + 0.10, g + aa + 0.26, edge);
    vec3 shellCol = face * (dif * (0.8 + 0.5 * lift) + bounce)
                  + idB * bev * (0.2 + 0.9 * lift)
                  + idH * 0.10 * openWave;              // heart-light grazing opened regions
    col = mix(col, shellCol, tile);
    col += idB * rim * 0.35;
  } else {
    float dClose = length(rc + rd * (-b));
    col += idA * exp(-max(dClose - R, 0.0) * 8.0) * 0.18;   // modest halo, not a corona
    openness = 0.0;
  }

  // ---------- THE HEART: sliced superquadric, seen THROUGH the openings --------------
  // Visible where the shell is open (grout, opened rings) or missed entirely; occluded
  // to embers behind closed tiles. k wanders on incommensurate rates: the heart is
  // always BECOMING another shape -- this is the morph, at form level, forever.
  // v3 fixes, both found by reading Daniil's screenshot against the code:
  //  * THE LEAK: outside the sphere silhouette `see` was 1.0, so the heart rendered
  //    AROUND the ball as a giant corona. The heart lives INSIDE: zero visibility
  //    outside the silhouette (the halo above is its only outward trace).
  //  * THE MUSH: coords were scaled 3.4x into a polynomial with exponents up to 8,
  //    so field values blew past the wire-glow band and the cube/torus contours
  //    collapsed into a white smudge. The reference operates its field at |o|~1-3;
  //    2.1 keeps the whole slice ladder inside that regime, and the contours return.
  float heartK = clamp(0.42 + 0.30 * sin(t * 0.117) + 0.18 * sin(t * 0.071 + 2.3), 0.05, 0.95);
  float see = (disc > 0.0) ? clamp(openness + 0.10, 0.0, 1.0) : 0.0;
  if (see > 0.01) {
    float ct = 0.0;
    float tCore = -b;                                    // ray depth of closest core approach
    for (int i = 0; i < 14; i++) {
      float z = mix(-0.55, 0.55, (float(i) + 0.5) / 14.0);
      vec3 sp = ro + rd * (tCore + z);
      vec3 o = (sp - cc) * 2.1;
      float fd = sqField(o, heartK, t);
      float glow = wireGlow(fd * 0.8);
      ct = max(ct, glow / (1.0 + abs(z) * 1.6));
    }
    vec3 heart = mix(idH, vec3(1.0, 0.97, 0.9), 0.35 * ct);
    col += heart * ct * ct * see * 1.6;
  }

  // ---------- THE RINGS v4: small SOLID SUPERQUADRIC BODIES, not streaks ----------
  // Daniil, from my own snapshot's evidence: "add the cube shader to the outer edges
  // in a 3d way, so the outer elements are not just flat." Confirmed -- v3's columns
  // were flat light-rods and their linear glow term fogged the whole frame.
  //
  // Each orbiting element is now a miniature of the HEART: a superquadric rendered by
  // its own tiny slice ladder, so the outer edges carry the same 3D wire-solid language
  // as the center. Each body morphs cube<->torus on its OWN phase and tumbles at its
  // own incommensurate rate while it orbits -- twelve small shapes each mid-become.
  // A bounding test keeps cost honest: most pixels evaluate zero bodies.
  for (int ring = 0; ring < 2; ring++) {
    float rr    = (ring == 0) ? 1.30 : 1.95;
    float ecc   = (ring == 0) ? 0.0  : 0.24;
    float omega = 0.55 * pow(rr, -1.5) * ((ring == 0) ? 1.0 : -1.0);
    float tilt  = (ring == 0) ? 0.35 : -0.52;
    float prec  = t * ((ring == 0) ? 0.045 : -0.031);
    float NP    = (ring == 0) ? 5.0 : 7.0;
    vec3  tint  = (ring == 0) ? idA : idC;
    float ringBob = ((ring == 0) ? 0.12 : -0.12) * sin(t * 0.43 + float(ring) * 2.1);
    float bodyR = (ring == 0) ? 0.23 : 0.19;             // bounding radius of one body

    for (float i = 0.0; i < 7.0; i += 1.0) {
      if (i >= NP) break;
      float base = i / NP * 2.0 * PI;
      float ang = base + t * omega * (1.0 + ecc * 1.6 * cos(base + t * omega));
      float rad = rr * (1.0 - ecc * ecc) / (1.0 + ecc * cos(ang));
      vec3 p = vec3(cos(ang) * rad, 0.0, sin(ang) * rad);
      p.y += ringBob + 0.08 * sin(t * 0.9 + hash1(i * 7.7 + float(ring) * 31.0) * 6.28);
      pR(p.yz, tilt); pR(p.xz, prec);

      // bounding test: distance from ray to body center
      vec3 toP = p - ro;
      float tb = dot(toP, rd);
      float db = length(toP - rd * tb);
      if (db > bodyR * 1.6 || tb < 0.0) continue;

      float occ = (tb > tHit) ? 0.25 : 1.0;
      // per-body morph phase + tumble rates: no two bodies are the same shape twice
      float ph = hash1(i * 13.7 + float(ring) * 5.3);
      float kb = clamp(0.5 + 0.42 * sin(t * (0.19 + 0.11 * ph) + ph * 6.28), 0.05, 0.95);
      float ct2 = 0.0;
      for (int s = 0; s < 5; s++) {
        float z = mix(-bodyR, bodyR, (float(s) + 0.5) / 5.0);
        vec3 o = (ro + rd * (tb + z) - p) * (2.6 / bodyR);
        // reuse the heart's field but give each body its own tumble time-origin
        float fd = sqField(o, kb, t * (0.8 + 0.5 * ph) + ph * 40.0);
        ct2 = max(ct2, wireGlow(fd * 0.8) / (1.0 + abs(z / bodyR) * 1.2));
      }
      vec3 bcol = mix(tint, vec3(1.0, 0.97, 0.9), 0.30 * ct2);
      col += bcol * ct2 * ct2 * occ * 1.9;
    }
  }

  col *= 1.05;
  col = aces(col);
  col += (ign(F) - 0.5) * 0.012;
  O = vec4(col, 1.0);
}

void main(){ mainImage(outColor, gl_FragCoord.xy); }
