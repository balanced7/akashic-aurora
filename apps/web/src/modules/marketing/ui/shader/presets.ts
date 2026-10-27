/**
 * The site's shader backgrounds: one GLSL program per preset, each with a CSS gradient that stands
 * in for it before hydration, without WebGL, or after a lost context.
 *
 * Colours are the theme tokens in assets/styles/marketing.css, as 0..1 RGB: hud-cyan #0ac8b9,
 * hud-cyan-deep #0397ab, hud-gold #c8aa6e, hud-gold-deep #785a28, mk-blue #0099ff, hud-ink
 * #010a13, and the aurora backdrop's violet rgb(120 90 220).
 *
 * Sources: `aurora` is the hero shader this site already had; `curtains` is house preset 01, the
 * background of akashiclabs.io; `nebula`, `network`, `caustics` and `lattice` are written here from
 * techniques in the Bifrost shader lab (design/vfx-chunks: plasma-field's domain warp, hex-grid's
 * tiling, segment-distance, triangular-dither). No outside shader code is used.
 */

const PRELUDE = `
precision highp float;
uniform vec2 uResolution;
uniform float uTime;
uniform vec2 uPointer;
uniform float uIntensity;
uniform float uSeed;

const vec3 CYAN = vec3(0.039, 0.784, 0.725);
const vec3 CYAN_DEEP = vec3(0.012, 0.592, 0.671);
const vec3 GOLD = vec3(0.784, 0.667, 0.431);
const vec3 GOLD_DEEP = vec3(0.471, 0.353, 0.157);
const vec3 BLUE = vec3(0.0, 0.6, 1.0);
const vec3 INK = vec3(0.004, 0.039, 0.075);
const vec3 VIOLET = vec3(0.47, 0.353, 0.863);

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec2 hash2(vec2 p) {
  return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
  float value = 0.0;
  float amplitude = 0.5;
  mat2 turn = mat2(0.8, 0.6, -0.6, 0.8);
  for (int i = 0; i < 4; i++) {
    value += amplitude * noise(p);
    p = turn * p * 2.03;
    amplitude *= 0.5;
  }
  return value;
}

float segment(vec2 p, vec2 a, vec2 b) {
  vec2 pa = p - a;
  vec2 ba = b - a;
  float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
  return length(pa - ba * h);
}

// Static triangular dither, one code value wide: it breaks banding on dark ramps and, having no
// time term, never crawls.
vec3 finish(vec3 color) {
  return color + (hash(gl_FragCoord.xy) - hash(gl_FragCoord.yx + 17.0)) * (1.6 / 255.0);
}
`;

/** The hero aurora: curtains of light leaning right, away from the copy column, following the pointer. */
const AURORA = `
float curtain(vec2 uv, float seed, float height, float speed) {
  float t = uTime * speed;
  float wave = fbm(vec2(uv.x * 1.6 + seed, t * 0.35)) - 0.5;
  float edge = height + wave * 0.32 + sin(uv.x * 2.3 + seed + t) * 0.04;
  float d = uv.y - edge;
  float ribbon = exp(-abs(d) * 16.0);
  float rays = pow(fbm(vec2(uv.x * 34.0 + seed * 3.0, t * 0.6)), 3.4) * 2.2;
  float hang = smoothstep(0.0, -0.08, d) * smoothstep(-0.42, -0.04, d);
  return ribbon * 1.1 + rays * hang;
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;
  float aspect = uResolution.x / uResolution.y;
  vec2 p = vec2(uv.x * aspect, uv.y);
  p.x += (uPointer.x - 0.5) * 0.12;
  p.y += (uPointer.y - 0.5) * 0.04;

  vec3 teal = vec3(0.01, 0.42, 0.50);
  float a = curtain(p, 1.7, 0.86, 0.22);
  float b = curtain(p + vec2(0.35, 0.0), 6.1, 0.78, 0.17);
  float c = curtain(p - vec2(0.6, 0.0), 11.3, 0.94, 0.13);

  vec3 color = CYAN * a + teal * b * 0.9 + mix(VIOLET, GOLD, uv.x) * c * 0.55;
  color += GOLD * pow(a * b, 1.5) * 0.6;

  float fade = smoothstep(0.25, 0.95, uv.y);
  float side = mix(0.22, 1.0, smoothstep(0.2, 0.8, uv.x));
  float vignette = smoothstep(1.25, 0.25, length((uv - vec2(0.5, 0.75)) * vec2(1.0, 1.4)));
  color = color / (1.0 + color) * 1.6;
  color *= fade * vignette * side * uIntensity;
  gl_FragColor = vec4(finish(color), 1.0);
}
`;

/** House preset 01 from akashiclabs.io: a night sky, sparse stars and three slow curtains. */
const CURTAINS = `
vec3 curtain(vec2 uv, float t, float seed, vec3 tint) {
  float x = uv.x * 2.2 + seed * 7.0;
  float drift = fbm(vec2(x * 0.7, t * 0.12 + seed)) * 1.6;
  float band = uv.y - 0.34 - 0.18 * sin(x * 0.9 + t * 0.25 + seed * 3.0) - drift * 0.16;
  // A bright hem with rays hanging above it, instead of one even glow.
  float body = exp(-band * band * 40.0) + 0.5 * exp(-max(-band, 0.0) * 6.0) * step(band, 0.0);
  float rays = pow(fbm(vec2(x * 4.0 - t * 0.35, t * 0.05 + seed)), 2.2) * 2.4;
  float fade = smoothstep(-0.35, 0.2, uv.y) * smoothstep(1.0, 0.45, uv.y);
  return tint * body * rays * fade;
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;
  float aspect = uResolution.x / uResolution.y;
  // Top-down, in units of a 16:10 frame's height, so a curtain keeps its size in a short band
  // or a tall phone hero instead of stretching to fill the section.
  vec2 p = vec2((uv.x + uSeed) * aspect / 1.6, (1.0 - uv.y) * 1.6 / aspect);
  float t = uTime;

  vec3 color = INK * 0.55 * smoothstep(1.0, 0.0, p.y);
  // One render pixel per star cell, so stars stay pin-sharp at any render scale.
  vec2 cell = floor(gl_FragCoord.xy / 5.0);
  float pin = step(4.0, mod(floor(gl_FragCoord.x), 5.0)) * step(4.0, mod(floor(gl_FragCoord.y), 5.0));
  float star = step(0.985, hash(cell + uSeed)) * pin;
  color += star * (0.3 + 0.25 * sin(t * 1.7 + hash(cell) * 40.0)) * smoothstep(0.75, 0.15, p.y) * 0.8;

  color += curtain(p, t, 0.0, CYAN) * 0.3;
  color += curtain(p, t * 1.13, 2.0, BLUE) * 0.2;
  color += curtain(p, t * 0.87, 4.0, VIOLET) * 0.16;
  color += CYAN_DEEP * exp(-pow((p.y - 0.30) * 5.0, 2.0)) * 0.06;
  gl_FragColor = vec4(finish(color * uIntensity), 1.0);
}
`;

/** A slow domain-warped cloud: banks of deep cyan and violet with dark sky between them. */
const NEBULA = `
void main() {
  vec2 uv = gl_FragCoord.xy / uResolution.y;
  float t = uTime * 0.035;
  vec2 p = uv * 1.25 + uSeed * 9.0;
  vec2 q = vec2(fbm(p + vec2(0.0, t)), fbm(p + vec2(5.2, 1.3) - t * 0.8));
  vec2 r = vec2(fbm(p + 3.0 * q + vec2(1.7, 9.2) + t * 0.6),
                fbm(p + 3.0 * q + vec2(8.3, 2.8) - t * 0.5));
  float f = fbm(p + 2.6 * r);

  vec3 color = mix(CYAN_DEEP, VIOLET, smoothstep(0.35, 0.85, q.y));
  color = mix(color, GOLD, smoothstep(0.62, 0.9, r.x) * 0.45);
  // A high threshold keeps emptiness between the banks: dark sky stays dark.
  float density = smoothstep(0.34, 0.88, f);
  color *= density * density * 0.6 + pow(density, 6.0) * 0.4;
  gl_FragColor = vec4(finish(color * uIntensity), 1.0);
}
`;

/**
 * Shared memory as a field: nodes drift in their cells and link to their neighbours, and now and
 * then a warm pulse runs along a link, a lesson passing from one agent to the next.
 */
const NETWORK = `
vec2 node(vec2 cell) {
  vec2 h = hash2(cell + uSeed * 13.0);
  return cell + 0.5 + 0.38 * sin(h * 6.2831 + uTime * (0.12 + 0.18 * h.yx));
}

float link(vec2 p, vec2 a, vec2 b, float px, inout float pulse) {
  float len = length(b - a);
  float d = segment(p, a, b);
  float line = smoothstep(px * 1.6, 0.0, d) * smoothstep(1.55, 0.9, len);
  float k = hash(floor(a * 7.0) + floor(b * 3.0));
  if (k > 0.86) {
    float s = fract(uTime * (0.05 + 0.06 * k) + k * 11.0);
    vec2 head = mix(a, b, s);
    pulse += smoothstep(px * 7.0, 0.0, length(p - head)) * line * sin(s * 3.1416);
  }
  return line;
}

void main() {
  float scale = 7.5;
  vec2 p = gl_FragCoord.xy / uResolution.y * scale;
  float px = scale / uResolution.y;
  vec2 cell = floor(p);

  vec2 n[9];
  for (int y = -1; y <= 1; y++) {
    for (int x = -1; x <= 1; x++) {
      n[(y + 1) * 3 + (x + 1)] = node(cell + vec2(float(x), float(y)));
    }
  }

  float lines = 0.0;
  float pulse = 0.0;
  for (int i = 0; i < 9; i++) {
    if (i != 4) lines += link(p, n[4], n[i], px, pulse);
  }
  lines += link(p, n[1], n[3], px, pulse);
  lines += link(p, n[1], n[5], px, pulse);
  lines += link(p, n[7], n[3], px, pulse);
  lines += link(p, n[7], n[5], px, pulse);

  float dots = 0.0;
  for (int i = 0; i < 9; i++) {
    dots += smoothstep(px * 3.2, 0.0, length(p - n[i]));
  }

  // Regions of the field come and go, so it never reads as wallpaper.
  float region = smoothstep(0.3, 0.75, fbm(p * 0.12 + vec2(uTime * 0.015, uSeed)));
  vec3 color = CYAN_DEEP * lines * 0.16 + CYAN * dots * 0.32 + GOLD * pulse * 0.9;
  color *= region;
  color += VIOLET * 0.05 * region * fbm(p * 0.25 - uTime * 0.02);
  gl_FragColor = vec4(finish(color * uIntensity), 1.0);
}
`;

/** Soft caustics: light through moving water, cells of cyan with gold where the edges gather. */
const CAUSTICS = `
float edges(vec2 p, float t) {
  vec2 cell = floor(p);
  vec2 f = fract(p);
  float f1 = 8.0;
  float f2 = 8.0;
  for (int y = -1; y <= 1; y++) {
    for (int x = -1; x <= 1; x++) {
      vec2 o = vec2(float(x), float(y));
      vec2 h = hash2(cell + o + uSeed * 7.0);
      vec2 point = o + 0.5 + 0.42 * sin(t * (0.6 + h) + h * 6.2831) - f;
      float d = dot(point, point);
      if (d < f1) { f2 = f1; f1 = d; } else if (d < f2) { f2 = d; }
    }
  }
  return 1.0 - smoothstep(0.0, 0.32, sqrt(f2) - sqrt(f1));
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution.y;
  float t = uTime * 0.22;
  vec2 warp = vec2(fbm(uv * 1.4 + t * 0.2), fbm(uv * 1.4 - t * 0.2 + 4.0)) - 0.5;
  vec2 p = uv * 3.2 + warp * 0.9;
  float a = pow(edges(p, t), 3.0);
  float b = pow(edges(p * 1.7 + 3.1, t * 1.3), 4.0);
  float light = smoothstep(0.0, 1.0, gl_FragCoord.y / uResolution.y);
  float pools = smoothstep(0.35, 0.8, fbm(uv * 0.9 + vec2(t * 0.1, uSeed)));
  vec3 color = CYAN_DEEP * a * 0.28 + mix(CYAN, GOLD, 0.55) * a * b * 0.6;
  color *= pools * (0.35 + 0.65 * light);
  gl_FragColor = vec4(finish(color * uIntensity), 1.0);
}
`;

/**
 * The avatar's hex tiling, flattened: faint cell walls a slow wave of light crosses. A few cells
 * hold a gold charge, trust granted, and let it go.
 */
const LATTICE = `
void main() {
  float scale = 9.0;
  vec2 uv = gl_FragCoord.xy / uResolution.y;
  vec2 p = uv * scale;
  p.x *= 1.1547;
  vec2 a = mod(p, vec2(1.0, 1.732)) - vec2(0.5, 0.866);
  vec2 b = mod(p + vec2(0.5, 0.866), vec2(1.0, 1.732)) - vec2(0.5, 0.866);
  vec2 g = dot(a, a) < dot(b, b) ? a : b;
  vec2 id = p - g;
  float edge = 0.5 - abs(max(abs(g.x) * 0.866 + g.y * 0.5, g.y));
  float px = scale * 1.6 / uResolution.y;
  float wall = smoothstep(px, 0.0, abs(edge));

  vec2 centre = id / scale;
  centre.x /= 1.1547;
  float t = uTime;
  float wave = sin(dot(centre, vec2(0.8, 0.6)) * 2.2 - t * 0.35 + uSeed * 5.0);
  float swell = smoothstep(0.55, 1.0, wave);
  float field = smoothstep(0.25, 0.7, fbm(centre * 1.5 + vec2(t * 0.02, uSeed)));

  float k = hash(id + uSeed);
  float charge = step(0.94, k) * pow(0.5 + 0.5 * sin(t * (0.3 + k * 0.4) + k * 40.0), 6.0);
  float fill = smoothstep(0.5, 0.0, edge) * charge;

  vec3 color = CYAN_DEEP * wall * (0.07 + 0.3 * swell) * field;
  color += GOLD * fill * 0.18 * field + GOLD_DEEP * wall * charge * 0.3;
  gl_FragColor = vec4(finish(color * uIntensity), 1.0);
}
`;

export interface ShaderPreset {
  /** GLSL ES 1.0 fragment source, prelude included. */
  readonly fragment: string;
  /** CSS background that stands in for the shader. Kept as dark as the shader is. */
  readonly fallback: string;
  /** Frames per second the field needs: slow fields look the same at 30. */
  readonly fps: number;
  /** Render scale against CSS pixels × DPR: a soft field has no edges to lose. */
  readonly scale: number;
  /** The time shown as a still frame under reduced motion. */
  readonly still: number;
}

const preset = (body: string, rest: Omit<ShaderPreset, "fragment">) => ({
  fragment: PRELUDE + body,
  ...rest,
});

export const shaderPresets = {
  aurora: preset(AURORA, {
    fallback: "none",
    fps: 60,
    scale: 0.5,
    still: 12,
  }),
  curtains: preset(CURTAINS, {
    fallback:
      "radial-gradient(120% 60% at 50% 30%, rgb(10 200 185 / 0.16), transparent 60%), radial-gradient(60% 40% at 80% 20%, rgb(120 90 220 / 0.14), transparent 70%), linear-gradient(rgb(1 10 19 / 0.6), transparent)",
    fps: 60,
    scale: 0.5,
    still: 18,
  }),
  nebula: preset(NEBULA, {
    fallback:
      "radial-gradient(50% 45% at 25% 40%, rgb(3 151 171 / 0.12), transparent 70%), radial-gradient(45% 40% at 75% 60%, rgb(120 90 220 / 0.1), transparent 70%)",
    fps: 30,
    scale: 0.35,
    still: 40,
  }),
  network: preset(NETWORK, {
    fallback:
      "radial-gradient(55% 50% at 70% 45%, rgb(3 151 171 / 0.1), transparent 70%), radial-gradient(40% 35% at 20% 70%, rgb(120 90 220 / 0.06), transparent 70%)",
    fps: 30,
    scale: 0.6,
    still: 30,
  }),
  caustics: preset(CAUSTICS, {
    fallback:
      "radial-gradient(70% 55% at 50% 100%, rgb(3 151 171 / 0.12), transparent 70%), radial-gradient(40% 30% at 30% 80%, rgb(200 170 110 / 0.06), transparent 70%)",
    fps: 30,
    scale: 0.45,
    still: 25,
  }),
  lattice: preset(LATTICE, {
    fallback:
      "radial-gradient(60% 50% at 60% 50%, rgb(3 151 171 / 0.08), transparent 70%), radial-gradient(30% 25% at 30% 40%, rgb(200 170 110 / 0.05), transparent 70%)",
    fps: 30,
    scale: 0.6,
    still: 14,
  }),
} satisfies Record<string, ShaderPreset>;

export type ShaderPresetName = keyof typeof shaderPresets;
