// arsenal/web/haze-bench.js -- the haze bench: three plates that show the house haze module (glsl/atmos/haze.glsl),
// built from the SAME module files every scene composes, through the browser twin of the composer (glsl/modlib.js).
//
// WHY. Three judges failed three VJ builds on light in haze (research/reviewed/keylab-liberation-2026-10-22: Void Star,
// Laser Sky, Virtual Stage v0). This page is where the shared fix is seen and measured on its own, before any scene
// takes it: P1 a Berlin sky (acid-green and cyan-white fans of many lines breaking into a cloud of dashes over
// deep-blue air), P2 Void Star's sheet-beam V on true black, P3 a 3D hall with moving-head cones and an LED ring in
// haze, P4 the Qlimax 2014 Source Ring (four LED bands whose light fills the haze round them).
//
// Pipeline: the plate writes scene-linear light (1.0 = SDR white, unclamped) into a float target; the final pass shows
// it through tmStage(x, heat, 1) and the exact sRGB encode. window.HB is the harness door (headless SwiftShader only):
// HB.setup / HB.render / HB.png / HB.float / HB.flash. ?pale=1 shows P2's inner sheets pale-and-bright.
//
// Apache-2.0, Akashic Aurora. Written fresh; no corpus code.

import { loadLibrary } from './glsl/modlib.js';

const MODULES = ['atmos-haze', 'colour-tone', 'colour-transfer', 'noise-value'];

const VERT = `#version 300 es
precision highp float;
void main() {
    vec2 corner = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
    gl_Position = vec4(corner * 2.0 - 1.0, 0.0, 1.0);
}`;

// ------------------------------------------------------------------------------------------------------------ plates
// Each plate defines vec3 plateLight(vec2 pixel, vec2 res, float t, float haze, float gain): scene-linear light.
// gain is 1 for SDR levels (cores near 1) and 2.5 for HDR levels. HDR headroom goes to cores, roots and lenses only
// (Look v2 1.9): a hazeBeam or hazeSheet called with phase 0 is exactly its core line and hot root, so the plates add
// (gain - 1) of that and leave haze, bodies and halos where they were. uBeams (0 or 1) turns the plate's lights off,
// which must leave nothing but P1's sky.
const PLATES = {};

PLATES.p1 = {
  name: 'Berlin sky',
  glsl: `
// P1: deep-blue air (the plate's one ambient: a blue-hour sky, as the Berlin frames show; it is the sky, not haze), a
// low deck of acid-green fans and cyan-white fans of many lines thrown up through a lopsided cloud, where every line
// breaks into short dashes and neighbouring lines break in step: a cloud made of dashes. The fans swing; a swinging
// line is blurred over the shutter (hazeBeamSwept). Each fan draws only its two nearest lines per pixel, plus one
// hazeSheet for the glow between its lines. Frame-height units.
const vec3 P1_AIR = vec3(0.0072, 0.024, 0.165);
const vec3 P1_GREEN = vec3(0.006, 1.0, 0.135);
const vec3 P1_SHEET = vec3(0.22, 0.84, 1.0);
const float P1_SHUTTER = 1.0 / 60.0;
const vec4 P1_DASH = vec4(0.014, 0.008, 0.95, 0.010);   // dash length, cell angle, contrast, drift (frame heights)

vec2 p1Dir(float a) {                       // (cos a, sin a) as one sine of two phases
    return sin(vec2(a + 1.5707963, a));
}

float p1Ground(float x) {
    return -0.335 + 0.010 * sin(11.0 * x + 0.4) + 0.006 * sin(29.0 * x + 1.3);
}

vec3 p1Air(vec2 p, float ground, float aspect, float t) {
    float up = max(p.y - ground, 0.0);
    float side = abs(p.x) / (0.5 * aspect);
    float shape = exp(-up / 0.40) * (1.0 - 0.6 * smoothstep(0.25, 1.0, side) * smoothstep(0.0, 0.5, up));
    float patchy = (hazeDensity(p, -2.0, vec4(1.4, 50.0, 0.010, 0.0), t) - 0.55) / 0.45;     // 0..1, big and slow
    return P1_AIR * (shape * (0.55 + 0.9 * patchy));
}

// One fan of n lines from root (aim and spread in radians from +x; spin = the fan's angular speed, rad/s; reach in
// frame heights): the two lines nearest the pixel through hazeBeamSwept, the glow between all of them (the halos of
// the lines not drawn) through one hazeSheet, shown only as far as there is haze to hold it.
vec3 p1Fan(vec2 p, float px, vec2 root, float aim, float halfSpread, float n, float spin, float reach, vec3 col,
           float level, float dens, float glowDens, float widthPx, float coreFloor, float glow, float pale, float gain) {
    vec2 d = p - root;
    float r = length(d);
    float stepA = 2.0 * halfSpread / max(n - 1.0, 1.0);
    float a0 = aim - halfSpread;
    float th = atan(d.y, d.x);
    float fk = (th - a0) / stepA;
    float k = clamp(floor(fk + 0.5), 0.0, n - 1.0);
    float k2 = fk > k ? k + 1.0 : k - 1.0;                          // the next line on the pixel's side ...
    k2 = k2 < 0.0 || k2 > n - 1.0 ? k + (k < 0.5 ? 1.0 : -1.0) : k2;   // ... or, past an edge line, the one inside
    float sweep = abs(spin) * P1_SHUTTER * r / px;
    vec3 lit = vec3(0.0);
    for (int pick = 0; pick < 2; ++pick) {
        float kk = pick == 0 ? k : k2;
        if (pick == 1 && (kk == k || n < 1.5)) break;
        vec3 f = hazeBeamCoords(p, root, p1Dir(a0 + kk * stepA), reach);
        lit += hazeBeamSwept(f.x / px, sweep, f.y, col, level, dens, widthPx, hazePhase(0.12), coreFloor);
        if (gain > 1.0) lit += hazeBeamSwept(f.x / px, sweep, f.y, col, level * (gain - 1.0), dens, widthPx, 0.0,
                                             coreFloor);
    }
    vec3 g = hazeBeamCoords(p, root, p1Dir(aim), reach);
    lit += hazeSheet(g.z, 0.75 * halfSpread, g.y, col, glow * min(2.0 * glowDens, 1.0), glowDens, 1.0, pale);
    return lit;
}

vec3 plateLight(vec2 pixel, vec2 res, float t, float haze, float gain) {
    float aspect = res.x / res.y;
    vec2 p = (pixel - 0.5 * res) / res.y;
    float px = 1.0 / res.y;
    float ground = p1Ground(p.x);
    if (p.y < ground) return vec3(0.0);                         // the crowd: a black silhouette
    vec3 sky = p1Air(p, ground, aspect, t);
    // the cloud: a lopsided mass over the deck, heavier to the right, with ragged edges
    float band = smoothstep(-0.16, -0.04, p.y) * (1.0 - smoothstep(0.16, 0.34, p.y));
    float lean = 0.40 + 0.60 * smoothstep(-0.9, 0.5, p.x);
    float field = 0.5 + 0.5 * (0.7 * noiseValue2(p * vec2(2.4, 3.4) + vec2(0.012 * t, 0.0), 11u)
                             + 0.3 * noiseValue2(p * vec2(6.1, 7.3) + vec2(0.02 * t, 3.1), 12u));
    float cloud = band * lean * smoothstep(0.30, 0.62, field);
    float deck = 0.75 * hazeDensity(p, ground, vec4(4.0, 0.07, 0.012, 0.0), t);   // the haze low over the deck
    float thin = 0.06 * hazeDensity(p, ground, vec4(3.0, 0.6, 0.012, 0.0), t);    // a thin veil above it
    float dens = clamp((deck + thin + 1.5 * cloud) * haze, 0.0, 1.0);
    float deckY = -0.300;
    float widthPx = (7.0 + 3.0 * cloud) * res.y / 1080.0;
    vec3 light = vec3(0.0);
    for (int emitter = 0; emitter < 6; ++emitter) {             // acid-green fans, alternate banks leaning left/right
        float fk = float(emitter);
        vec2 root = vec2(-0.66 + 0.264 * fk, deckY);
        float side = mod(fk, 2.0) < 0.5 ? 1.0 : -1.0;
        float rate = 0.35 + 0.22 * fk;
        float aim = radians(90.0 + side * (34.0 + 14.0 * sin(rate * t + 1.9 * fk + 0.6)));
        float spin = radians(side * 14.0) * rate * cos(rate * t + 1.9 * fk + 0.6);
        float streak = hazeStreak(p, root, P1_DASH, t);
        light += p1Fan(p, px, root, aim, radians(30.0), 14.0, spin, 0.75, P1_GREEN, 0.9, dens * streak,
                       dens * (0.6 + 0.4 * streak), widthPx, 0.03, 0.025, 0.0, gain);
        light += hazePoint(p, root, 0.010, vec3(1.0, 1.0, 0.92), 3.0 * gain, 1.0);
    }
    for (int sheet = 0; sheet < 3; ++sheet) {                   // cyan-white fans of dense lines from the stage
        float fs = float(sheet) - 1.0;
        vec2 root = vec2(0.20 * fs, deckY - 0.004);
        float rate = 0.9 + 0.3 * fs;
        float aim = radians(90.0 - 40.0 * fs + 9.0 * sin(rate * t + 2.0 * fs));
        float spin = radians(9.0) * rate * cos(rate * t + 2.0 * fs);
        float streak = hazeStreak(p, root, P1_DASH, t);
        light += p1Fan(p, px, root, aim, radians(9.0 + 2.0 * abs(fs)), 18.0, spin, 0.85, P1_SHEET, 0.75, dens * streak,
                       dens * (0.6 + 0.4 * streak), 0.8 * widthPx, 0.03, 0.10, 0.0, gain);
        light += hazePoint(p, root, 0.012, vec3(1.0), 3.0 * gain, 1.0);
    }
    return sky + uBeams * light;
}`,
};

PLATES.p2 = {
  name: 'Void Star sheets',
  glsl: `
// P2: a mirrored V of sheet beams from one root on true black: cyan-white inside, violet outside, white-hot at the
// root, coloured above, fading upward, the haze's texture streaked along each sheet. The inner sheets are the
// brightest (the Void Star frame's luminous cyan-white); uPale picks their look: 0 saturated (the default, the one
// that holds chroma), 1 pale-and-bright. Frame-height units.
const vec3 P2_VIOLET = vec3(0.42, 0.06, 1.0);
const vec3 P2_CYAN = vec3(0.06, 0.74, 1.0);

vec3 plateLight(vec2 pixel, vec2 res, float t, float haze, float gain) {
    vec2 p = (pixel - 0.5 * res) / res.y;
    float px = 1.0 / res.y;
    vec2 root = vec2(0.0, -0.24);
    float air = hazeDensity(p, -0.6, vec4(2.2, 1.4, 0.008, 0.006), t);
    float streak = hazeStreak(p, root, vec4(0.06, 0.012, 0.6, 0.014), t);
    float dens = clamp(air * streak * haze, 0.0, 1.0);
    vec3 light = vec3(0.0);
    for (int ring = 0; ring < 3; ++ring) {
        float fi = float(ring);
        float lean = radians(15.0 + 15.0 * fi + 1.5 * sin(0.09 * t + 1.3 * fi));
        float hw = radians(3.0 + 1.2 * fi);
        vec3 col = ring == 0 ? P2_CYAN : P2_VIOLET;
        float level = ring == 0 ? 1.4 : 0.52;
        float pale = ring == 0 ? uPale : 0.0;
        for (int side = 0; side < 2; side++) {
            float sgn = side == 0 ? -1.0 : 1.0;
            vec3 f = hazeBeamCoords(p, root, vec2(sgn * sin(lean), cos(lean)), 0.80);
            light += hazeSheet(f.z, hw, f.y, col, level, dens, 1.0, pale);
            if (gain > 1.0) light += hazeSheet(f.z, hw, f.y, col, level * (gain - 1.0), dens, 0.0, pale);
        }
    }
    for (int side = 0; side < 2; side++) {                      // two thin line beams between the sheets
        float sgn = side == 0 ? -1.0 : 1.0;
        float lean = radians(23.0 + 1.0 * sin(0.13 * t));
        vec3 f = hazeBeamCoords(p, root, vec2(sgn * sin(lean), cos(lean)), 0.85);
        light += hazeBeam(f.x / px, f.y, P2_VIOLET, 0.9, dens, 6.0 * res.y / 1080.0, 1.0, 0.05);
        if (gain > 1.0) light += hazeBeam(f.x / px, f.y, P2_VIOLET, 0.9 * (gain - 1.0), dens, 6.0 * res.y / 1080.0,
                                          0.0, 0.05);
    }
    light += hazePoint(p, root, 0.016, vec3(1.0, 0.96, 1.0), 4.0 * gain, 1.0);         // the blinding root
    light += hazePoint(p, root, 0.08, mix(P2_VIOLET, P2_CYAN, 0.4), 0.10, dens);         // its glow in the haze
    return uBeams * light;
}`,
};

PLATES.p3 = {
  name: 'Qlimax air (3D)',
  glsl: `
// P3: from the crowd in a hall (metres): two trusses of moving heads over the crowd (blue and violet, two lime)
// slanting down through haze, four uplights on the stage raking up and back, a big LED ring behind the stage that
// lights the air round it (hazeRing3: one area light, not a string of lamps), two washes raking over the crowd
// toward the roof, the floor catching the pools. Nothing else is lit: the hall itself is black. The per-pixel jitter
// is hazeBlueNoise. Its roots are the cones' own in-scatter near each lens (1/D), 4-20 in scene-linear light at any
// level setting, so gain is not used here.
const vec3 P3_BLUE = vec3(0.10, 0.22, 1.0);
const vec3 P3_VIOLET = vec3(0.42, 0.10, 1.0);
const vec3 P3_LIME = vec3(0.45, 1.0, 0.04);
const vec3 P3_RING = vec3(0.09, 0.11, 1.0);
const vec3 P3_RING_C = vec3(0.0, 16.5, -46.0);
const vec3 P3_RING_N = vec3(0.0, 0.0, 1.0);          // the ring faces the crowd

vec3 p3Apex(int i) {
    if (i < 12) return vec3(-11.0 + 4.4 * float(i % 6), 13.0, -6.0 - 12.0 * float(i / 6));
    return vec3(-9.0 + 6.0 * float(i - 12), 1.2, -30.0);
}

vec3 p3Axis(int i, float t) {
    float fi = float(i);
    if (i < 12) {
        float x = -11.0 + 4.4 * float(i % 6);
        return vec3(-0.04 * x + 0.32 * sin(0.15 * t + 0.9 * fi), -1.0, 0.55 + 0.2 * cos(0.11 * t + 1.7 * fi));
    }
    float u = fi - 13.5;
    return vec3(0.22 * u + 0.12 * sin(0.09 * t + fi), 1.0, -0.45 + 0.1 * cos(0.13 * t + fi));
}

vec3 p3Colour(int i) {
    if (i == 2 || i == 9) return P3_LIME;
    return i % 2 == 0 ? P3_BLUE : P3_VIOLET;
}

float p3Level(int i) {
    return i < 12 ? 48.0 : 85.0;
}

vec3 plateLight(vec2 pixel, vec2 res, float t, float haze, float gain) {
    vec2 uv = (pixel - 0.5 * res) / res.y;
    vec3 ro = vec3(0.0, 1.7, 12.0);
    vec3 ahead = vec3(0.0, 0.2079117, -0.9781476);              // looking 12 degrees up the hall
    vec3 lift = vec3(0.0, 0.9781476, 0.2079117);                 // the camera's up, square to ahead
    vec3 across = vec3(1.0, 0.0, 0.0) * uv.x;
    vec3 rd = normalize(1.1 * ahead + uv.y * lift + across);
    float tFloor = rd.y < 0.0 ? -ro.y / rd.y : 1e4;
    float tMax = min(160.0, tFloor);
    if (rd.z < 0.0) tMax = min(tMax, (-50.0 - ro.z) / rd.z);
    if (rd.y > 0.0) tMax = min(tMax, (32.0 - ro.y) / rd.y);
    vec2 air = vec2(haze, 0.0);
    vec4 hz = vec4(0.30, 12.0, 0.20, 0.05);
    vec4 clump = vec4(1.3, 0.11, 0.85, 0.35);
    float jitter = hazeBlueNoise(pixel);
    vec3 light = vec3(0.0);
    for (int head = 0; head < 16; ++head) {
        light += hazeCone(ro, rd, tMax, p3Apex(head), p3Axis(head, t), 0.05, p3Colour(head), p3Level(head), air, hz,
                          clump, t, jitter);
    }
    for (int wash = 0; wash < 2; ++wash) {                      // washes raking over the crowd toward the roof
        float sw = float(wash) * 2.0 - 1.0;
        vec3 apex = vec3(11.0 * sw, 21.0, -40.0);
        vec3 aim = vec3(5.0 * sw + 2.0 * sin(0.05 * t + sw), 27.0, 6.0) - apex;
        light += hazeCone(ro, rd, tMax, apex, aim, 0.13, wash == 0 ? P3_RING : P3_VIOLET, 200.0, air, hz, clump,
                          t, jitter);
    }
    // the LED ring: its band (an emitter the ray sees on the back wall's plane) and the air it lights
    light += hazeRing3(ro, rd, tMax, P3_RING_C, P3_RING_N, vec3(15.0, 0.45, 17.0), P3_RING, 14.0, air, hz, t,
                       jitter);
    if (rd.z < 0.0) {
        float tWall = (ro.z - P3_RING_C.z) / -rd.z;              // where the ray meets the ring's plane
        if (tWall < tMax + 0.01) {
            vec3 w = ro + rd * tWall - P3_RING_C;
            float rho = length(w.xy);
            float pxM = tWall / (1.1 * res.y);                     // a pixel's size in metres on the wall
            float band = 1.0 - smoothstep(0.45 - pxM, 0.45 + pxM, abs(rho - 15.0));
            float seg = 0.6 + 0.4 * smoothstep(0.15, 0.45, abs(fract(atan(w.y, w.x) * 7.6394373) - 0.5));
            light += glowHotCoreTo(P3_RING, 0.9 * seg, vec3(0.62, 0.9, 1.0)) * band;
        }
    }
    if (tFloor <= tMax) {
        vec3 f = ro + rd * tFloor;
        vec3 pools = vec3(0.0);
        for (int head = 0; head < 12; ++head) {
            vec3 down = f - p3Apex(head);
            float far2 = dot(down, down);
            pools += p3Colour(head) * (p3Level(head) * hazeConeProfile(f, p3Apex(head), p3Axis(head, t), 0.05)
                                       * (-down.y / sqrt(far2)) / far2);
        }
        light += pools * (0.06 * exp(-0.035 * tFloor));                       // a dark floor, albedo 0.06
    }
    return uBeams * light;
}`,
};

PLATES.p4 = {
  name: 'Source Ring',
  glsl: `
// P4: the Qlimax 2014 ring in a break (the study's ref-17): a shallow dish of LED bands behind the stage, one closed
// outer band and three open arcs stepping inward (a spiral read from the front), shimmering blue-violet with cores
// turning toward cyan; four black speaker stacks hang in front and slice it. The ring is an area light: the haze in
// front of it glows in its colour (hazeRing), most inside the ring, falling to exactly black before the corners.
// Frame-height units.
const vec3 P4_RING = vec3(0.14, 0.10, 1.0);          // the bands' blue-violet
const vec3 P4_AIR = vec3(0.065, 0.05, 1.0);          // the haze they light: the same hue, deeper (the break haze)
const vec3 P4_CORE = vec3(0.62, 0.9, 1.0);           // where a band's core blows out: toward cyan
const vec2 P4_C = vec2(0.0, 0.07);

// One band's LED light: a soft band of radial segments along the arc, a shimmer running round it.
vec3 p4Band(vec2 p, float px, float R, float hw, vec2 arc, float level, float t, float k) {
    vec2 v = p - P4_C;
    float rho = length(v);
    float phi = atan(v.y, v.x);
    float delta = mod(phi - arc.x + 3.1415927, 6.2831853) - 3.1415927;
    float inArc = arc.y >= 3.1415926 ? 1.0 : 1.0 - smoothstep(arc.y - 0.01, arc.y + 0.01, abs(delta));
    float across = 1.0 - smoothstep(hw - px, hw + px, abs(rho - R));
    float segs = floor(6.2831853 * R / 0.016);
    float slat = smoothstep(0.08, 0.22, abs(fract(phi / 6.2831853 * segs) - 0.5));
    float shimmer = 0.75 + 0.25 * sin(3.0 * phi - 0.6 * t + 1.7 * k) * sin(7.0 * phi + 0.9 * t + k);
    float edge = exp(-abs(abs(rho - R) - 0.7 * hw) / (0.25 * hw));               // brighter lines at the band edges
    float i = level * (0.55 + 0.45 * slat) * shimmer * (0.8 + 0.6 * edge);
    return glowHotCoreTo(P4_RING, i, P4_CORE) * (across * inArc);
}

float p4Stacks(vec2 p) {                                         // the hanging speaker stacks: 1 = clear, 0 = black
    float open = 1.0;
    for (int stack = 0; stack < 4; ++stack) {
        bool outer = stack % 2 == 0;
        float x = (stack < 2 ? -1.0 : 1.0) * (outer ? 0.55 : 0.30);
        float bottom = outer ? 0.02 : 0.10;                      // they hang from above the frame
        float halfW = outer ? 0.040 : 0.032;
        float inside = (1.0 - smoothstep(halfW - 0.002, halfW, abs(p.x - x))) * step(bottom, p.y) * step(p.y, 0.52);
        open *= 1.0 - inside;
    }
    return open;
}

vec3 plateLight(vec2 pixel, vec2 res, float t, float haze, float gain) {
    vec2 p = (pixel - 0.5 * res) / res.y;
    float px = 1.0 / res.y;
    float clear = p4Stacks(p);
    if (clear <= 0.0) return vec3(0.0);
    float air = hazeDensity(p, -0.5, vec4(2.0, 0.9, 0.010, 0.004), t);
    float dens = clamp(air * haze, 0.0, 1.0);
    // ring = (radius, half-width, haze depth, reach); arc = (centre angle, half-span); the inner arcs open downward
    vec4 bands[4] = vec4[4](vec4(0.445, 0.016, 0.12, 0.34), vec4(0.345, 0.014, 0.11, 0.30),
                            vec4(0.255, 0.013, 0.10, 0.27), vec4(0.165, 0.012, 0.09, 0.24));
    vec2 arcs[4] = vec2[4](vec2(0.0, 3.1415927), vec2(1.95, 2.55), vec2(1.45, 2.45), vec2(1.5708, 2.30));
    vec3 light = vec3(0.0);
    for (int b = 0; b < 4; ++b) {
        float k = float(b);
        light += hazeRing(p, P4_C, bands[b], arcs[b], P4_AIR, 0.40, dens);
        light += p4Band(p, px, bands[b].x, bands[b].y, arcs[b], (b == 0 ? 0.42 : 0.34) * (gain > 1.0 ? 1.6 : 1.0),
                        t, k);
    }
    return uBeams * clear * light;
}`,
};

// ---------------------------------------------------------------------------------------------------- the shaders
function sceneSource(prelude, plate) {
  return `#version 300 es
precision highp float;
precision highp int;
uniform vec2 uRes;
uniform float uTime;
uniform float uHaze;
uniform float uGain;
uniform float uBeams;
uniform float uPale;
out vec4 outColour;
${prelude}
${plate.glsl}
void main() {
    outColour = vec4(plateLight(gl_FragCoord.xy, uRes, uTime, uHaze, uGain), 1.0);
}`;
}

function finalSource(prelude) {
  return `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D uScene;
uniform float uHeat;
out vec4 outColour;
${prelude}
void main() {
    vec3 light = texelFetch(uScene, ivec2(gl_FragCoord.xy), 0).rgb;
    outColour = vec4(srgbEncode(min(tmStage(light, uHeat, 1.0), vec3(1.0))), 1.0);
}`;
}

function compile(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'compile failed');
  return s;
}

function program(gl, fragSrc) {
  const p = gl.createProgram();
  gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, VERT));
  gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, fragSrc));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) || 'link failed');
  return p;
}

// ------------------------------------------------------------------------------------------------------ the bench
const canvas = document.getElementById('stage');
const params = new URLSearchParams(location.search);
const bare = params.has('bare');
if (bare) document.body.classList.add('bare');
const gl = canvas.getContext('webgl2', { antialias: false, alpha: false, preserveDrawingBuffer: true });
const state = { plate: params.get('plate') || 'p1', mode: params.get('mode') || 'slow',
                haze: Number(params.get('haze') || 1), heat: Number(params.get('heat') || 0.4),
                levels: params.get('levels') || 'sdr', t: Number(params.get('t') || 6), pale: Number(params.get('pale') || 0),
                programs: {}, target: null };
let library = null;
let prelude = { scene: '', final: '' };

function ensureTarget(w, h) {
  if (state.target && state.target.w === w && state.target.h === h) return state.target;
  if (state.target) { gl.deleteTexture(state.target.tex); gl.deleteFramebuffer(state.target.fb); }
  const tex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, tex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, w, h, 0, gl.RGBA, gl.FLOAT, null);
  const fb = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  state.target = { w, h, tex, fb };
  return state.target;
}

function plateProgram(id) {
  if (!state.programs[id]) {
    const prog = program(gl, sceneSource(prelude.scene, PLATES[id]));
    state.programs[id] = { prog, u: Object.fromEntries(['uRes', 'uTime', 'uHaze', 'uGain', 'uBeams', 'uPale']
      .map((n) => [n, gl.getUniformLocation(prog, n)])) };
  }
  return state.programs[id];
}

function finalProgram() {
  if (!state.programs.final) {
    const prog = program(gl, finalSource(prelude.final));
    state.programs.final = { prog, u: { uScene: gl.getUniformLocation(prog, 'uScene'),
                                        uHeat: gl.getUniformLocation(prog, 'uHeat') } };
  }
  return state.programs.final;
}

// Draw one frame: the plate into the float target, then the display stage onto the canvas.
function draw(o = {}) {
  const plate = o.plate || state.plate;
  const t = o.t ?? state.t;
  const haze = o.haze ?? state.haze;
  const heat = o.heat ?? state.heat;
  const gain = (o.levels || state.levels) === 'hdr' ? 2.5 : 1.0;
  const w = canvas.width;
  const h = canvas.height;
  const tgt = ensureTarget(w, h);
  const sp = plateProgram(plate);
  gl.bindFramebuffer(gl.FRAMEBUFFER, tgt.fb);
  gl.viewport(0, 0, w, h);
  gl.useProgram(sp.prog);
  gl.uniform2f(sp.u.uRes, w, h);
  gl.uniform1f(sp.u.uTime, t);
  gl.uniform1f(sp.u.uHaze, haze);
  gl.uniform1f(sp.u.uGain, gain);
  gl.uniform1f(sp.u.uBeams, o.beams ?? 1);
  gl.uniform1f(sp.u.uPale, o.pale ?? state.pale);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
  const fp = finalProgram();
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  gl.viewport(0, 0, w, h);
  gl.useProgram(fp.prog);
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, tgt.tex);
  gl.uniform1i(fp.u.uScene, 0);
  gl.uniform1f(fp.u.uHeat, heat);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}

function readFloat() {
  const { w, h, fb } = state.target;
  const px = new Float32Array(w * h * 4);
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  gl.readPixels(0, 0, w, h, gl.RGBA, gl.FLOAT, px);
  return px;
}

// Stats of the scene-linear float frame: the HDR levels Look v2 caps (P3 primaries: Y uses the house Rec.709 weights
// because the bench works in linear sRGB, like the library).
function floatStats(px, w, h) {
  let max = 0, sumY = 0, over1 = 0, zero = 0, bad = 0;
  for (let i = 0; i < w * h; i++) {
    const r = px[4 * i], g = px[4 * i + 1], b = px[4 * i + 2];
    if (!Number.isFinite(r + g + b)) { bad++; continue; }
    const peak = Math.max(r, g, b);
    if (peak > max) max = peak;
    if (peak > 1) over1++;
    if (r === 0 && g === 0 && b === 0) zero++;
    sumY += 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }
  const n = w * h;
  return { w, h, max, meanY: sumY / n, over1Share: over1 / n, exactZeroShare: zero / n, nonFinite: bad };
}

// The flash check on a 60 fps virtual clock: per frame, the mean relative luminance of the displayed frame (decoded
// sRGB) in each cell of a 3x3 grid and the whole frame, and the saturated-red share; then the ITU-R BT.1702 / WCAG
// general-flash count: a flash is a pair of opposing changes of at least 0.1 where the darker state is below 0.8;
// more than 3 flashes in any one-second window, or a red flash, fails.
function flashCheck(o) {
  const frames = o.frames || 360, dt = 1 / 60, t0 = o.t0 ?? state.t;
  const w = canvas.width, h = canvas.height;
  const px = new Uint8Array(w * h * 4);
  const dec = new Float32Array(256);
  for (let i = 0; i < 256; i++) { const v = i / 255; dec[i] = v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
  const series = Array.from({ length: 10 }, () => []);
  const reds = [];
  for (let f = 0; f < frames; f++) {
    draw(Object.assign({}, o, { t: t0 + f * dt }));
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const cell = new Float64Array(9), cnt = new Float64Array(9);
    let all = 0, red = 0;
    for (let y = 0; y < h; y++) {
      const cy = Math.min(2, Math.floor(y * 3 / h));
      for (let x = 0; x < w; x++) {
        const i = 4 * (y * w + x);
        const r = px[i], g = px[i + 1], b = px[i + 2];
        const Y = 0.2126 * dec[r] + 0.7152 * dec[g] + 0.0722 * dec[b];
        const k = cy * 3 + Math.min(2, Math.floor(x * 3 / w));
        cell[k] += Y; cnt[k]++; all += Y;
        if (r + g + b > 30 && r / (r + g + b) >= 0.8) red++;
      }
    }
    for (let k = 0; k < 9; k++) series[k].push(cell[k] / cnt[k]);
    series[9].push(all / (w * h));
    reds.push(red / (w * h));
  }
  const report = { frames, perSecondMax: 0, flashes: 0, maxStep: 0, maxRedShare: Math.max(...reds) };
  for (const s of series) {
    for (let i = 1; i < s.length; i++) report.maxStep = Math.max(report.maxStep, Math.abs(s[i] - s[i - 1]));
    const turns = [];                                  // turning points of each monotone run
    let anchor = s[0], dir = 0;
    for (let i = 1; i < s.length; i++) {
      const d = s[i] - s[i - 1];
      const nd = d > 0 ? 1 : d < 0 ? -1 : dir;
      if (dir !== 0 && nd !== dir) { turns.push({ i: i - 1, from: anchor, to: s[i - 1] }); anchor = s[i - 1]; }
      dir = nd;
    }
    turns.push({ i: s.length - 1, from: anchor, to: s[s.length - 1] });
    const big = turns.filter((r) => Math.abs(r.to - r.from) >= 0.1 && Math.min(r.to, r.from) < 0.8);
    const flashes = [];
    for (let i = 1; i < big.length; i++) if (Math.sign(big[i].to - big[i].from) !== Math.sign(big[i - 1].to - big[i - 1].from)) flashes.push(big[i].i);
    report.flashes += flashes.length;
    for (const f of flashes) report.perSecondMax = Math.max(report.perSecondMax, flashes.filter((g) => g > f - 60 && g <= f).length);
  }
  report.redFlash = report.maxRedShare > 0.05;
  report.pass = report.perSecondMax <= 3 && !report.redFlash;
  return report;
}

// ---------------------------------------------------------------------------------------------- page and harness
const els = Object.fromEntries(['plate', 'mode', 'haze', 'heat', 'levels', 'measure', 'stats', 'hazeOut', 'heatOut']
  .map((id) => [id, document.getElementById(id)]));

function syncControls() {
  els.plate.value = state.plate; els.mode.value = state.mode; els.levels.value = state.levels;
  els.haze.value = state.haze; els.heat.value = state.heat;
  els.hazeOut.value = Number(state.haze).toFixed(2); els.heatOut.value = Number(state.heat).toFixed(2);
}

function fitCanvas() {
  const w = Number(params.get('w')) || Math.min(1920, Math.round(canvas.clientWidth * (window.devicePixelRatio || 1)));
  const h = Number(params.get('h')) || Math.round(w * 9 / 16);
  if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
}

let last = performance.now();
function frame(now) {
  if (state.mode === 'slow') state.t += Math.min(0.1, (now - last) / 1000);
  last = now;
  draw();
  requestAnimationFrame(frame);
}

async function start() {
  if (!gl) throw new Error('WebGL2 is not available');
  if (!gl.getExtension('EXT_color_buffer_float')) throw new Error('EXT_color_buffer_float is not available');
  library = await loadLibrary(new URL('./glsl/index.json', import.meta.url).href);
  prelude = { scene: library.compose(MODULES, 'webgl2'), final: library.compose(['colour-tone', 'colour-transfer'], 'webgl2') };
  fitCanvas();
  syncControls();
  for (const id of ['plate', 'mode', 'levels']) els[id].addEventListener('change', () => { state[id] = els[id].value; });
  for (const id of ['haze', 'heat']) els[id].addEventListener('input', () => { state[id] = Number(els[id].value); syncControls(); });
  els.measure.addEventListener('click', () => {
    draw();
    const s = floatStats(readFloat(), canvas.width, canvas.height);
    els.stats.textContent = `max ${s.max.toFixed(2)}  mean Y ${s.meanY.toFixed(4)}  above 1.0 ${(100 * s.over1Share).toFixed(2)}%`
      + `  exactly 0 ${(100 * s.exactZeroShare).toFixed(1)}%  non-finite ${s.nonFinite}`;
  });
  window.addEventListener('resize', () => { if (!params.get('w')) fitCanvas(); });
  if (!params.has('harness')) requestAnimationFrame(frame);
}

window.HB = {
  ready: false,
  error: null,
  setup(o = {}) {
    if (o.w && o.h) { canvas.width = o.w; canvas.height = o.h; }
    Object.assign(state, o.state || {});
    const t0 = performance.now();
    draw(o);
    gl.finish();
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    return { ms: performance.now() - t0, renderer: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
             modules: library.compose(MODULES, 'webgl2').split('\n')[1] };
  },
  render(o = {}) {
    const t0 = performance.now();
    draw(o);
    const b = new Uint8Array(4);
    gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, b);
    return { ms: performance.now() - t0 };
  },
  png() { return canvas.toDataURL('image/png'); },
  float(o = {}) {
    draw(o);
    const px = readFloat();
    const stats = floatStats(px, canvas.width, canvas.height);
    if (!o.raw) return stats;
    const rgb = new Float32Array(canvas.width * canvas.height * 3);   // float32 RGB, rows bottom up
    for (let i = 0; i < canvas.width * canvas.height; i++) { rgb[3 * i] = px[4 * i]; rgb[3 * i + 1] = px[4 * i + 1]; rgb[3 * i + 2] = px[4 * i + 2]; }
    window.HB.held = new Uint8Array(rgb.buffer);
    return Object.assign(stats, { bytes: window.HB.held.length });
  },
  // The held float frame in base64 pieces, so no single message to the harness is large.
  chunk(offset, length) {
    const part = window.HB.held.subarray(offset, offset + length);
    let s = '';
    for (let i = 0; i < part.length; i += 0x8000) s += String.fromCharCode.apply(null, part.subarray(i, i + 0x8000));
    return btoa(s);
  },
  flash(o = {}) { return flashCheck(o); },
};

start().then(() => { window.HB.ready = true; }).catch((e) => {
  window.HB.error = String(e && e.message || e);
  if (els.stats) els.stats.textContent = 'bench failed: ' + window.HB.error;
});
