#version 300 es
//! {"id": "vj-reactor", "name": "VJ Reactor", "author": "Vandor", "tags": ["vj", "generative", "beat", "bass", "pads", "feedback"], "params": [{"k": 1, "name": "core size", "default": 0.5}, {"k": 2, "name": "shells", "default": 0.6}, {"k": 3, "name": "tilt", "default": 0.4}, {"k": 4, "name": "jets", "default": 0.6}, {"k": 5, "name": "trails", "default": 0.5}, {"k": 6, "name": "shock", "default": 0.6}]}
precision highp float;

// Reactor (arsenal/web/vj.html, Play-loadable). A core that pulses on every kick inside three x-ray glass shells, after
// the glow-xray recipe (arsenal/web/glsl/groups/glow-xray.glsl): a wall glows by how much of it the eye looks through, so
// a shell is brightest at its rim, where it is seen edge-on, and its latitude and longitude lines show front and back at
// once. Each kick launches a shockwave: the ring is written into the alpha channel of the feedback buffer (stored as
// 1 - field, so a buffer cleared to alpha 1 starts empty) and the whole field is resampled a little further out every
// frame, so rings expand and thin on their own. Bass fills the room. The twelve pads are plasma jets at the twelve clock
// positions (pad 12 at twelve o'clock): velocity sets their reach. Tension makes the core unstable. Any pad hit (the
// strip's shared hit input, 2026-10-24) flares the core: it swells and whitens, throws a shock ring and lights the shells.

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
    gPal[0] = hueLinear(h + 0.53); gPal[1] = hueLinear(h + 0.80); gPal[2] = hueLinear(h + 0.64); gPal[3] = hueLinear(h + 0.03);
    gPhase = fract(u_time * 2.0); gPulse = u_beat;
    gTension = 0.0;
    gChordPulse = 0.0;
    gKick = u_beat;
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
mat3 rotX(float a) { float c = cos(a), s = sin(a); return mat3(1.0, 0.0, 0.0, 0.0, c, s, 0.0, -s, c); }
mat3 rotY(float a) { float c = cos(a), s = sin(a); return mat3(c, 0.0, -s, 0.0, 1.0, 0.0, s, 0.0, c); }

// A glass shell of radius R and wall w seen through: the length of wall on the eye's ray, 1 at the inner rim.
float shellGlow(float r, float R, float w) {
  float outer = sqrt(max(R * R - r * r, 0.0));
  float inner = sqrt(max((R - w) * (R - w) - r * r, 0.0));
  return (outer - inner) / sqrt(max(2.0 * R * w - w * w, 1e-6));
}

// The latitude and longitude lines of a sphere of radius R at p, seen front (z > 0) and back at once.
float gridLines(vec2 p, float R, mat3 m, float lines, float px) {
  float r2 = dot(p, p);
  if (r2 >= R * R) return 0.0;
  float z = sqrt(R * R - r2);
  // a line's footprint in grid units per pixel, wider toward the rim where the sphere turns away (no derivatives, so
  // the lines hold their width inside the loop and the branch)
  float turn = 1.0 / max(z / R, 0.2);
  vec2 fw = vec2(lines / TAU, lines * 0.5 / PI) * (px / R) * turn;
  float sum = 0.0;
  for (int side = 0; side < 2; side++) {
    vec3 q = m * (vec3(p, side == 0 ? z : -z) / R);
    float lon = atan(q.x, q.z) / TAU * lines;
    float lat = asin(clamp(q.y, -1.0, 1.0)) / PI * lines * 0.5;
    vec2 g = abs(fract(vec2(lon, lat) + 0.5) - 0.5);
    vec2 line = 1.0 - smoothstep(vec2(0.0), fw * 1.5 + 1e-4, g);
    float w = side == 0 ? 1.0 : 0.35;              // x-ray: the far side shows, fainter
    sum += w * max(line.x * (1.0 - smoothstep(0.85, 1.0, abs(q.y))), line.y);
  }
  return sum;
}

void main() {
  vjLoad();
  hitLoad();
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  vec2 p0 = p;                  // the reactor's own place: the feedback field never lurches (2026-10-24)
  // a hit makes the whole reactor lurch toward the side its prominence flares (the hit's seed sets the direction)
  float lurchA = (gHost ? vjAt(12, 2).x : 0.0) * TAU;
  p -= vec2(cos(lurchA), sin(lurchA)) * 0.03 * gHit;
  float px = 1.0 / max(u_res.y, 1.0);
  float r = length(p);
  float ang = atan(p.y, p.x);
  float bass = clamp(0.65 * u_bass + 0.35 * u_pulse, 0.0, 1.5);

  // the core's radius: size, bass, the kick, and a tremor that grows with harmonic tension
  float R0 = (0.045 + 0.04 * u_k1) * (1.0 + 0.30 * bass + 0.22 * gKick + 0.40 * gHit);
  float wobble = gTension * 0.22 * (vnoise(vec2(ang * 2.0 + u_time * 0.9, u_time * 1.3)) - 0.5);
  float rc = r / (R0 * (1.0 + wobble));

  // the feedback: rgb drifts outward a little (radiating trails), alpha holds the shock field as 1 - field
  float expand = 0.012 + 0.02 * u_k6 + 0.01 * bass;
  vec2 back = p0 * (1.0 - expand);
  vec4 prev = texture(u_prev, back / vec2(asp, 1.0) + 0.5);
  float keep = 0.40 + 0.50 * u_k5;
  vec3 trail = max(prev.rgb * keep - 1.5 / 255.0, 0.0);
  float shock = max((1.0 - prev.a) * (0.915 + 0.05 * u_k6) - 1.0 / 255.0, 0.0);
  // a kick writes a ring just outside the core; the expansion carries it out (written where the field lives: p0)
  float ringAt = R0 * 1.35;
  float r0 = length(p0);
  shock = max(shock, gKick * u_k6 * exp(-pow((r0 - ringAt) / (0.010 + 0.01 * gKick), 2.0)));
  shock = min(shock, 1.0);

  // the room: lit by the bass, darker at the corners
  vec3 col = gPal[1] * (0.012 + 0.06 * bass) * exp(-r * 2.4) + vec3(0.0009, 0.0012, 0.0024);

  // the shells: three nested glass spheres, brightest at their rims; the outer one carries the grid
  float tilt = 0.25 + 1.1 * u_k3;
  mat3 m = rotX(tilt) * rotY(u_time * (0.11 + 0.25 * gTension) + 1.3 * gChordPulse);
  float shellLight = 0.0;
  for (int k = 0; k < 3; k++) {
    float fk = float(k);
    float R = R0 * (2.0 + 1.25 * fk) * (1.0 + 0.04 * sin(u_time * 0.37 + fk * 2.1));
    float w = R * (0.10 + 0.04 * fk);
    float g = shellGlow(r, R, w);
    shellLight += g * (0.35 - 0.08 * fk);
    col += mix(gPal[0], gPal[2], fk * 0.5) * g * (0.10 + 0.22 * u_k2) * (1.0 + 1.5 * gChordPulse + 1.4 * gHit);
  }
  float Rg = R0 * 4.5 * (1.0 + 0.04 * sin(u_time * 0.37 + 4.2));
  col += mix(gPal[2], vec3(0.8), 0.25) * gridLines(p, Rg, m, 12.0, px) * (0.06 + 0.14 * u_k2) * (1.0 + gChordPulse);

  // the shockwave field, coloured
  col += mix(gPal[2], vec3(1.0), 0.35) * shock * 0.55;

  // the pads: plasma jets at the twelve clock positions (pad 12 at twelve o'clock), velocity sets their reach
  for (int i = 0; i < 12; i++) {
    vec2 lv = padLevel(i);
    if (lv.x < 0.002) continue;
    float a = PI * 0.5 - float(i + 1) * (PI / 6.0);
    vec2 dir = vec2(cos(a), sin(a));
    float reach = (0.10 + 0.32 * lv.y) * (0.45 + 0.55 * lv.x) * (0.5 + 0.7 * u_k4);
    float along = dot(p, dir) - R0 * 1.05;
    float across = abs(dot(p, vec2(-dir.y, dir.x)));
    float s = along / max(reach, 1e-3);
    if (s < -0.1 || s > 1.25) continue;
    float width = (0.004 + 0.012 * lv.y) * (1.0 - 0.75 * clamp(s, 0.0, 1.0)) + px;
    float flick = 0.65 + 0.35 * vnoise(vec2(s * 7.0 - u_time * 5.0, float(i) * 4.3));
    float body = exp(-pow(across / width, 2.0)) * smoothstep(-0.1, 0.05, s) * (1.0 - smoothstep(0.85, 1.25, s));
    vec3 tint = padColour(i);
    col += hotCore(tint, 0.8 + 1.6 * lv.x) * body * flick * lv.x * 0.9;
    col += tint * 0.15 * lv.x * exp(-across / (width * 6.0)) * smoothstep(-0.1, 0.2, s) * (1.0 - smoothstep(0.6, 1.25, s));
  }

  // the core: a ball of plasma, brightest at its heart and turning slowly inside, with a Lorentzian glow around it;
  // the kick heats it toward white, and only the kick
  float coreBall = 1.0 - smoothstep(0.55, 1.0, rc);   // a soft edge: plasma, not a billiard ball
  float coreGlow = 0.12 / (0.12 + rc * rc * 1.2);    // centred on the core, so no dark seam between ball and glow
  vec3 coreTint = mix(gPal[0], gPal[3], 0.5 * gTension);
  float limb = sqrt(max(1.0 - rc * rc, 0.0));
  float plasma = 0.55 + 0.45 * vnoise(p / max(R0, 1e-3) * 1.8 + vec2(u_time * 0.5, -u_time * 0.35));
  col += hotCore(coreTint, 0.35 + 1.0 * gKick + 0.2 * bass + 2.4 * gHit) * coreBall * (0.25 + 0.6 * limb) * plasma;
  col += coreTint * coreGlow * (0.35 + 0.5 * bass + 0.4 * gKick + 1.1 * gHit);
  // a pad hit's flare throws a ring of its own: DRAWN, not written into the shock field (written there, it lingered for
  // ~0.4 s as a dull grey ring offset by the lurch: the 2026-10-24 verifier's "ghost ring"), in the core's colour,
  // expanding fast and gone in ~0.15 s
  if (gHit > 0.01 && gHitAge < 0.2) {
    float rr = ringAt * 1.05 + gHitAge * (0.9 + 0.8 * gHitVel);
    float wr = 0.006 + 0.010 * gHitVel + px;
    float xr = (r - rr) / wr;
    col += hotCore(coreTint, 1.0 + gHit) * exp(-xr * xr) * exp(-gHitAge / 0.06) * gHit * 0.5;
  }
  // ... and throws a prominence: a tongue of plasma out of the core in the hit's own direction (from its seed), so no two
  // hits flare alike; velocity sets its reach
  if (gHit > 0.01) {
    float fa = (gHost ? vjAt(12, 2).x : 0.0) * TAU;
    vec2 fdir = vec2(cos(fa), sin(fa));
    float reachF = (0.10 + 0.28 * gHitVel) * (0.4 + 0.6 * gHit);
    float alongF = dot(p, fdir) - R0 * 0.8;
    float acrossF = abs(dot(p, vec2(-fdir.y, fdir.x)));
    float sF = clamp(alongF / max(reachF, 1e-3), 0.0, 1.0);
    float widthF = (0.008 + 0.03 * gHitVel) * (1.0 - 0.8 * sF) + px;
    float tongue = exp(-pow(acrossF / widthF, 2.0)) * step(0.0, alongF) * (1.0 - smoothstep(0.75, 1.0, alongF / max(reachF, 1e-3)));
    col += hotCore(mix(coreTint, gPal[3], 0.4), 1.2 + 1.5 * gHit) * tongue * gHit * (0.6 + 0.4 * vnoise(vec2(sF * 9.0 - u_time * 6.0, fa)));
  }

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.1);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  col = max(col, trail);
  outColor = vec4(clamp(col, 0.0, 1.0), 1.0 - shock);
}
