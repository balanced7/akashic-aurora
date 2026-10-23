#version 300 es
//! {"id": "vj-chord-constellations", "name": "VJ Chord Constellations", "author": "Vandor", "tags": ["vj", "generative", "chord", "keys", "pedal"], "params": [{"k": 1, "name": "night sky", "default": 0.5}, {"k": 2, "name": "lines", "default": 0.7}, {"k": 3, "name": "spikes", "default": 0.5}, {"k": 4, "name": "wheel", "default": 0.5}, {"k": 5, "name": "trails", "default": 0.4}, {"k": 6, "name": "pedal", "default": 0.85}]}
precision highp float;

// Chord Constellations (arsenal/web/vj.html, Play-loadable). Every sounding note is a star: its angle walks the circle of
// fifths (C at twelve o'clock, G one step clockwise), its distance from the centre is its register, its colour the house
// pitch colour. The stars of a chord are joined into a constellation, in order round the circle, and the lines draw
// themselves again on every chord change; on the circle of fifths a major triad is a narrow wedge, a diminished seventh a
// square, an augmented triad an equilateral triangle. THE PEDAL STAR: when one note is struck again and again while the
// harmony moves under it (Daniel's Joy to the World ends on D-flat struck 95 times over a walking bass), that star ripples
// on every strike and is tied to every other star by a string that trembles harder as the repeats pile up (tension = 1 -
// exp(-strikes / 24)); its glow heats toward white. When the repeats stop, the tension lets go in a bloom.
// Ripples live in the alpha channel of the feedback buffer (stored as 1 - field) and expand around the pedal star.

uniform sampler2D u_video;   // the VJ page: its 16x6 VJ strip (u_has_video stays 0); Play: the video or a 1x1 black texture
uniform sampler2D u_prev;
uniform vec2  u_res;
uniform float u_time;
uniform float u_has_video;
uniform float u_beat, u_level, u_bass, u_mid, u_high;
uniform float u_hue;
uniform float u_intensity;
uniform float u_k1, u_k2, u_k3, u_k4, u_k5, u_k6;

in vec2 v_uv;
out vec4 outColor;

const float PI = 3.14159265358979;
const float TAU = 6.28318530717959;

// The house pitch colours (arsenal/web/vj-core.js pitchColours, the piano's palette; tests/vj_core.test.mjs pins these)
const vec3 PC_COL[12] = vec3[12](
  vec3(0.0199, 0.5610, 0.6101), vec3(1.0108, 0.2104, 0.0136), vec3(0.0398, 0.2848, 1.3564), vec3(0.5096, 0.5152, 0.0170),
  vec3(0.9080, 0.0617, 1.2415), vec3(0.0201, 0.5962, 0.3555), vec3(1.2716, 0.0623, 0.1166), vec3(0.0171, 0.4642, 0.8374),
  vec3(0.7316, 0.3596, 0.0150), vec3(0.3590, 0.1178, 1.6413), vec3(0.0682, 0.6072, 0.0156), vec3(1.2075, 0.0548, 0.5141));

bool gHost;
vec4 vjAt(int x, int y) { return texelFetch(u_video, ivec2(x, y), 0); }

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
float aaWire(float dPx, float widthPx) {   // draw2-aa aaWire, in pixels
  float drawn = max(widthPx, 1.0);
  return clamp(0.5 * drawn + 0.5 - dPx, 0.0, 1.0) * (max(widthPx, 0.0) / drawn);
}
float lorentz(float dPx, float haloPx) {
  float x = dPx / max(haloPx, 1e-3);
  return 0.0625 / (0.0625 + x * x);
}
// distance from p to the segment a..b, and where along it (0 at a, 1 at b)
vec2 segment(vec2 p, vec2 a, vec2 b) {
  vec2 ab = b - a;
  float s = clamp(dot(p - a, ab) / max(dot(ab, ab), 1e-9), 0.0, 1.0);
  return vec2(length(p - a - ab * s), s);
}
// a star's angle on the circle of fifths
float starAngle(float pc) { return PI * 0.5 - mod(pc * 7.0, 12.0) * (PI / 6.0); }

// one star: a hot core, a halo and four diffraction spikes
vec3 star(vec2 p, vec2 at, vec3 tint, float b, float px, float rs, float spikeAmt, float heat) {
  vec2 d = p - at;
  float dPx = length(d) / px;
  float coreR = (1.6 + 3.2 * b) * rs;
  float core = exp(-dPx * dPx / (coreR * coreR));
  float halo = lorentz(dPx, (10.0 + 26.0 * b) * rs);
  float ca = cos(0.35), sa = sin(0.35);
  vec2 r = vec2(ca * d.x - sa * d.y, sa * d.x + ca * d.y) / px;
  float len = (12.0 + 70.0 * b * spikeAmt) * rs;
  float spikes = exp(-abs(r.y) / (0.9 * rs)) * exp(-abs(r.x) / len) + exp(-abs(r.x) / (0.9 * rs)) * exp(-abs(r.y) / len);
  return hotCore(tint, 1.0 + heat) * core * b * 1.4 + tint * (halo * 0.45 + spikes * 0.6 * spikeAmt) * b;
}

void main() {
  gHost = u_has_video < 0.5 && textureSize(u_video, 0) == ivec2(16, 6);
  float asp = u_res.x / max(u_res.y, 1.0);
  vec2 p = (v_uv - 0.5) * vec2(asp, 1.0);
  float px = 1.0 / max(u_res.y, 1.0);
  float rs = max(u_res.y / 1080.0, 0.35);
  float t = u_time;

  // the pedal: position, strike pulse, tension, and the ripples it leaves in the feedback's alpha
  vec4 ped = gHost ? vjAt(14, 1) : vec4(0.0);
  vec4 ped2 = gHost ? vjAt(15, 1) : vec4(-1.0, 0.0, 0.0, 1.0);
  float pedalOn = ped2.y;
  vec2 pedalAt = ped.xy;
  float tension = ped.w * u_k6;
  float drawOn = gHost ? ped2.w : 1.0;
  float resolveP = ped2.z;

  vec2 centreR = pedalOn > 0.5 ? pedalAt : vec2(0.0);
  vec2 back = centreR + (p - centreR) * 0.982;
  vec4 prev = texture(u_prev, back / vec2(asp, 1.0) + 0.5);
  vec3 trail = max(texture(u_prev, v_uv).rgb * (0.30 + 0.55 * u_k5) - 1.5 / 255.0, 0.0);
  float ripple = max((1.0 - prev.a) * 0.955 - 1.0 / 255.0, 0.0);
  if (pedalOn > 0.5) {
    float rp = length(p - pedalAt);
    ripple = max(ripple, ped.z * u_k6 * exp(-pow((rp - 0.018) / 0.006, 2.0)));
  }
  ripple = min(ripple, 1.0);

  // the night: a deep gradient and a field of faint stars that breathe at their own slow rates
  vec3 col = mix(vec3(0.0012, 0.0018, 0.005), vec3(0.004, 0.0032, 0.009), smoothstep(-0.5, 0.6, p.y));
  for (int layer = 0; layer < 2; layer++) {
    float density = layer == 0 ? 110.0 : 48.0;
    vec2 sc = floor(p * density);
    float sh = hash12(sc + float(layer) * 17.0);
    if (sh > 0.93) {
      vec2 sp = (sc + 0.5 + 0.6 * (vec2(hash12(sc + 3.1), hash12(sc + 7.7)) - 0.5)) / density;
      float tw = 0.6 + 0.4 * sin(t * (0.3 + 0.9 * sh) + sh * 50.0);
      float size = (layer == 0 ? 0.8 : 1.3) * rs;
      col += vec3(0.75, 0.8, 1.0) * exp(-dot(p - sp, p - sp) / (size * size * px * px)) * tw * (sh - 0.93) * 9.0 * u_k1;
    }
  }

  // the circle of fifths: a faint rim and twelve sockets in their pitch colours, the nearest one lit by its pitch class
  float r = length(p);
  float rimR = 0.445;
  col += vec3(0.30, 0.32, 0.42) * aaWire(abs(r - rimR) / px, 0.8 * rs) * 0.10 * u_k4;
  float ang = atan(p.y, p.x);
  float slot = mod(floor((PI * 0.5 - ang) / (PI / 6.0) + 0.5), 12.0);   // the fifths step nearest this pixel's angle
  float pcHere = mod(slot * 7.0, 12.0);                                 // the pitch class at that step
  vec2 sock = rimR * vec2(cos(starAngle(pcHere)), sin(starAngle(pcHere)));
  float lvl = gHost ? vjAt(int(pcHere), 1).x : 0.0;
  float sd = length(p - sock) / px;
  col += PC_COL[int(pcHere)] * (exp(-sd * sd / (9.0 * rs * rs)) * (0.12 + 0.9 * lvl) + lorentz(sd, 9.0 * rs) * 0.06) * (0.4 + 0.6 * u_k4);

  // the stars: from the strip (sorted round the circle), or in Play a ghost triad walking the circle of fifths
  int count = gHost ? int(vjAt(9, 2).x + 0.5) : 3;
  float nSeg = count >= 3 ? float(count) : max(float(count) - 1.0, 0.0);
  vec2 first = vec2(0.0), last = vec2(0.0);
  vec3 firstCol = vec3(0.0), lastCol = vec3(0.0);
  float firstB = 0.0, lastB = 0.0;
  int seen = 0;
  vec3 stars = vec3(0.0);
  vec3 lines = vec3(0.0);
  vec3 strings = vec3(0.0);
  float ghostRoot = mod(floor(t / 6.0) * 7.0, 12.0);
  for (int i = 0; i < 16; i++) {
    if (i >= count) break;
    vec4 s;
    vec4 aux;
    if (gHost) {
      s = vjAt(i, 4);
      aux = vjAt(i, 5);
    } else {
      float pc = mod(ghostRoot + (i == 0 ? 0.0 : (i == 1 ? 4.0 : 7.0)), 12.0);
      float rad = 0.20 + 0.06 * float(i);
      s = vec4(rad * cos(starAngle(pc)), rad * sin(starAngle(pc)), 0.35 + 0.5 * u_mid, pc);
      aux = vec4(0.6, 1.0, i == 0 ? 1.0 : 0.0, 0.0);
    }
    if (s.w < -0.5) continue;
    vec3 tint = PC_COL[int(s.w + 0.5)];
    float b = s.z * (aux.z > 0.5 ? 1.25 : 1.0);
    bool isPedal = aux.w > 0.5 && pedalOn > 0.5;
    float heat = isPedal ? 2.5 * tension + 1.5 * ped.z : 0.3 * aux.x;
    stars += star(p, s.xy, tint, b * (isPedal ? 1.0 + 0.8 * tension : 1.0), px, rs * (isPedal ? 1.0 + tension : 1.0), u_k3, heat);
    // the constellation: a line from the previous star, drawn on in order after a chord change
    if (seen > 0) {
      float f = clamp(drawOn * nSeg - float(seen - 1), 0.0, 1.0);
      if (f > 0.0) {
        vec2 dst = mix(last, s.xy, f);
        vec2 sg = segment(p, last, dst);
        float e = 0.55 * u_k2 * min(lastB, b) * (0.6 + 0.4 * f);
        vec3 lc = mix(lastCol, tint, sg.y);
        float dl = sg.x / px;
        lines += lc * e * (aaWire(dl, 1.1 * rs) + 0.5 * lorentz(dl, 7.0 * rs));
      }
    } else {
      first = s.xy; firstCol = tint; firstB = b;
    }
    // the pedal's strings: from the pedal star to every other star, trembling with the tension
    if (pedalOn > 0.5 && !isPedal && tension > 0.01) {
      vec2 ab = s.xy - pedalAt;
      float L = length(ab);
      vec2 dir = ab / max(L, 1e-5);
      vec2 rel = p - pedalAt;
      float along = dot(rel, dir) / max(L, 1e-5);
      if (along > 0.0 && along < 1.0) {
        float across = dot(rel, vec2(-dir.y, dir.x));
        float wave = sin(PI * along) * sin(t * (9.0 + 7.0 * float(i)) + float(i) * 1.7) * (1.5 + 10.0 * tension) * rs * px;
        float dPx = abs(across - wave) / px;
        float e = tension * 0.5 * min(b, 1.0);
        strings += mix(PC_COL[int(ped2.x + 0.5) - 12 * (int(ped2.x + 0.5) / 12)], tint, along) * e * (aaWire(dPx, 0.9 * rs) + 0.35 * lorentz(dPx, 5.0 * rs));
      }
    }
    last = s.xy; lastCol = tint; lastB = b;
    seen++;
  }
  // close the constellation (three stars or more)
  if (seen >= 3) {
    float f = clamp(drawOn * nSeg - float(seen - 1), 0.0, 1.0);
    if (f > 0.0) {
      vec2 sg = segment(p, last, mix(last, first, f));
      float dl = sg.x / px;
      lines += mix(lastCol, firstCol, sg.y) * 0.55 * u_k2 * min(lastB, firstB) * (aaWire(dl, 1.1 * rs) + 0.5 * lorentz(dl, 7.0 * rs));
    }
  }

  col += lines + strings + stars;
  // the pedal's ripples, in its colour; and when the repeats stop, the tension lets go in a bloom
  if (gHost) {
    int ppc = int(max(ped2.x, 0.0) + 0.5);
    vec3 pedCol = PC_COL[ppc - 12 * (ppc / 12)];
    col += mix(pedCol, vec3(1.0), 0.3) * ripple * 0.6;
    float bloom = resolveP * exp(-length(p - pedalAt) / (0.10 + 0.25 * (1.0 - resolveP)));
    col += mix(pedCol, vec3(1.0, 0.95, 0.85), 0.5) * bloom * 0.7 * u_k6;
  }
  col += vec3(0.45, 0.5, 0.75) * u_beat * 0.3 * u_k4 * aaWire(abs(r - rimR) / px, 1.4 * rs);   // the beat: the rim, not the disc

  col *= mix(0.4, 1.0, u_intensity);
  col = 1.0 - exp(-col * 1.2);
  col = pow(col, vec3(1.0 / 2.2));             // linear light to display values (Play presents a preset as it is)
  col = max(col, trail);
  outColor = vec4(clamp(col, 0.0, 1.0), 1.0 - ripple);
}
