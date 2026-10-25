#version 300 es
//! {"id": "vj-hyperspace", "name": "VJ Hyperspace", "author": "Vandor", "tags": ["vj", "generative", "beat", "bass", "pads", "feedback"], "params": [{"k": 1, "name": "cruise", "default": 0.45}, {"k": 2, "name": "star density", "default": 0.6}, {"k": 3, "name": "beat warp", "default": 0.6}, {"k": 4, "name": "nebula", "default": 0.5}, {"k": 5, "name": "trails", "default": 0.45}, {"k": 6, "name": "jump", "default": 0.7}]}
precision highp float;

// Hyperspace (arsenal/web/vj.html, Play-loadable). Stars stream out of a vanishing point. Each star is a point at depth z
// in a polar cell, travelling toward the eye at a constant rate (so a tempo change never makes the field jump); what the
// music changes is the EXPOSURE: a streak is the star's path over the last dz of depth, so a kick stretches every star into
// a streak and the twelve pads punch hyperjumps -- the streaks lengthen several times over, the field of view widens and the
// jumping pad's colour runs down the streaks, with a ring of its colour thrown down the tunnel. Bass lights the vanishing
// point; the chord's palette tints the nebula behind it. The feedback buffer is resampled a little toward the centre every
// frame, so light drifts outward along the streaks' own direction (a radial motion blur that costs one texture read).
// Any pad hit (the strip's shared hit input, 2026-10-24) is a warp-jump on top: the streaks stretch at once, the field
// of view snaps wide, the vanishing point blazes and the trails pull harder, by the hit's velocity.

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

// ------------------------------------------------------------- the VJ strip (arsenal/web/vj-core.js STRIP, v1) --
bool gHost;
vec3 gPal[4];
float gPhase, gPulse, gTension, gChordPulse, gKick;

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
    gPhase = beat.x; gPulse = beat.y;
    gTension = vjAt(14, 0).z;
    gChordPulse = vjAt(15, 0).x;
    vec4 hit = vjAt(12, 1);
    gKick = max(hit.y, max(0.6 * hit.x, 0.7 * gPulse));
  } else {
    float h = u_hue / 360.0;
    gPal[0] = hueLinear(h + 0.58); gPal[1] = hueLinear(h + 0.75); gPal[2] = hueLinear(h + 0.50); gPal[3] = hueLinear(h + 0.92);
    gPhase = fract(u_time * 2.0); gPulse = u_beat;
    gTension = 0.0;
    gChordPulse = 0.0;
    gKick = max(u_beat, 0.7 * u_flux);
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
  float slot = floor(u_time / 3.0);
  float on = step(0.5, fract(sin(slot * 12.9898 + float(i) * 78.233) * 43758.5453)) * step(float(i), 1.0);
  float age = u_time - slot * 3.0;
  return vec3(on * exp(-age * 1.5) * smoothstep(0.5, 0.9, u_level + 0.3), 0.8, age);
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

// One star in angular cell `cell` of a layer with `cells` cells: its streak's light at polar (r, a).
// fov scales the projection; dz is the depth the exposure spans (the streak length); tint colours the tail.
vec3 streak(float r, float a, float cell, float cells, float layer, float travel, float fov, float dz, float px,
            vec3 tint, vec3 jumpTint, float jump) {
  float h1 = hash12(vec2(cell, layer * 17.0 + 3.0));
  float h2 = hash12(vec2(cell * 1.37 + 9.1, layer * 5.0));
  float h3 = hash12(vec2(cell * 0.71 + 2.3, layer * 11.0 + 7.0));
  if (h3 < 0.18) return vec3(0.0);                       // not every cell holds a star
  float aStar = (cell + 0.5 + 0.7 * (h1 - 0.5)) / cells * TAU;
  float z = fract(h2 - travel * (0.55 + 0.45 * h3));   // depth: 1 far, 0 at the eye
  z = max(z, 0.012);
  float rOut = fov * 0.035 / z;                        // the head, nearest the eye
  float rIn = fov * 0.035 / min(z + dz, 1.4);          // the tail, where the star was dz ago
  if (r < rIn - 3.0 * px || r > rOut + 3.0 * px) return vec3(0.0);
  float da = a - aStar;
  da -= TAU * floor(da / TAU + 0.5);
  float across = abs(r * sin(da)) / px;                // pixels from the streak's line
  float near = 1.0 - z;
  float width = 0.55 + 1.6 * near * near;              // nearer stars draw wider
  float core = exp(-across * across / (width * width));
  float halo = 0.10 / (0.10 + across * across / (9.0 * width * width));
  float along = clamp((r - rIn) / max(rOut - rIn, 1e-5), 0.0, 1.0);
  float ends = smoothstep(rIn - 2.0 * px, rIn + 2.0 * px, r) * (1.0 - smoothstep(rOut, rOut + 2.5 * px, r));
  float birth = smoothstep(1.0, 0.82, z);              // fade in from the far distance
  float b = (0.25 + 1.75 * near * near) * birth * ends * (0.5 + 0.5 * h1);
  // the head is white-hot; the tail takes the palette, or the jumping pad's colour
  vec3 tailCol = mix(tint, jumpTint, clamp(jump, 0.0, 1.0));
  vec3 c = mix(tailCol * 0.9, hotCore(mix(tailCol, vec3(1.0), 0.6), 1.2), along * along);
  return c * b * (core * 1.1 + halo * 0.25) * (0.35 + 0.65 * along);
}

void main() {
  vjLoad();
  hitLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float t = u_time;
  float bass = clamp(0.65 * u_bass + 0.35 * u_pulse, 0.0, 1.5);

  // the pads: each one a hyperjump; the strongest lends its colour, all of them add their punch
  float jump = 0.0, jumpBest = 0.0;
  vec3 jumpTint = gPal[2];
  vec3 rings = vec3(0.0);
  vec2 cDrift = vec2(0.035 * sin(t * 0.13), 0.025 * cos(t * 0.11));
  for (int i = 0; i < 12; i++) {
    vec3 lv = padLevel(i);
    if (lv.x < 0.002) continue;
    float punch = lv.x * (0.5 + 0.5 * lv.y);
    jump += punch;
    if (punch > jumpBest) { jumpBest = punch; jumpTint = padColour(i); }
    // a ring of the pad's colour thrown down the tunnel: it starts at the rim and races in toward the vanishing point
    float rr = length(p - cDrift);
    float ringR = 0.95 * exp(-lv.z * 2.6);
    float d = abs(rr - ringR) / px;
    rings += padColour(i) * punch * (exp(-d * d / 36.0) * 0.6 + 0.15 / (1.0 + d * 0.05)) * smoothstep(0.0, 0.08, lv.z);
  }
  jump += gHit * (0.7 + 0.7 * gHitVel);                 // the warp-jump: any pad hit, at once
  jump = min(jump, 1.9) * u_k6;

  // the vanishing point drifts a little and shakes with the bass
  vec2 c = cDrift + 0.004 * bass * vec2(vnoise(vec2(t * 13.0, 1.0)) - 0.5, vnoise(vec2(2.0, t * 11.0)) - 0.5);
  vec2 q = p - c;
  float r = length(q) + 1e-6;
  float a = atan(q.y, q.x);

  // exposure: cruise, the kick's warp and the pads' jump stretch the streaks; the jump also widens the field of view
  float warp = gKick * u_k3;
  float dz = 0.010 + 0.05 * u_k1 + 0.16 * warp + 0.55 * jump;
  float fov = 1.0 + 0.35 * warp + 0.9 * jump;
  float travel = t * (0.07 + 0.10 * u_k1);

  // the room: the nebula behind the stars, swirled in polar coordinates and tinted by the palette (the chord)
  float swirl = a / TAU + 0.15 * log(r + 0.02) + t * 0.01;
  float neb = vnoise(vec2(swirl * 6.0, log(r + 0.05) * 2.2 - t * 0.25));
  neb = neb * neb * (0.6 + 0.4 * vnoise(vec2(swirl * 17.0, r * 9.0 - t * 0.6)));
  vec3 col = mix(gPal[1], gPal[0], neb) * neb * (0.020 + 0.05 * u_k4) * (1.0 + 1.6 * gChordPulse) * smoothstep(0.0, 0.25, r);
  col += vec3(0.0006, 0.0008, 0.0016);
  // the vanishing point: a pinhole of light the bass widens
  col += mix(gPal[0], vec3(1.0), 0.4) * (0.006 + 0.02 * bass + 0.05 * jump) / (0.006 + r * r * 14.0);

  // the stars: three layers of angular cells, each pixel looking at its own cell and the nearer neighbour
  float density = 0.6 + 0.8 * u_k2;
  vec3 stars = vec3(0.0);
  for (int layer = 0; layer < 3; layer++) {
    float fl = float(layer);
    float cells = floor((70.0 + 55.0 * fl) * density);
    float rot = fl * 0.37;                              // layers start at different angles
    float al = a - rot;
    float u = al / TAU * cells;
    float cell = floor(u);
    float side = fract(u) < 0.5 ? -1.0 : 1.0;
    vec3 tint = gPal[layer];
    for (int n = 0; n < 2; n++) {
      float cid = mod(cell + (n == 0 ? 0.0 : side), cells);
      stars += streak(r, al, cid, cells, fl, travel + fl * 0.31, fov, dz, px, tint, jumpTint, jump);
    }
  }
  col += stars * (0.9 + 0.6 * u_level);
  col += rings * u_k6;

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.15);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)

  // the feedback: resample a little toward the vanishing point, so last frame's light moves outward along the streaks
  float pull = 0.012 + 0.03 * u_k1 + 0.05 * warp + 0.12 * jump;
  vec2 back = c + q * (1.0 - pull);
  vec3 prev = texture(u_prev, back / vec2(asp, 1.0) + 0.5).rgb;
  float keep = 0.35 + 0.55 * u_k5;
  vec3 trail = max(prev * keep - 2.0 / 255.0, 0.0);
  outColor = vec4(clamp(max(col, trail), 0.0, 1.0), 1.0);
}
