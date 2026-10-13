//! {"name": "colour-oklab", "kind": "helper", "cat": "H2", "family": "H", "version": "1.0.0", "order": 12,
//!  "license": "Apache-2.0",
//!  "credits": ["Bjorn Ottosson, 'A perceptual color space for image processing' (https://bottosson.github.io/posts/oklab/): OKLab, its two matrices and OKLCH",
//!   "Bjorn Ottosson, 'sRGB gamut clipping' (https://bottosson.github.io/posts/gamutclipping/): clip by reducing chroma at fixed lightness and hue; the cusp",
//!   "W3C CSS Color Module Level 4 (https://www.w3.org/TR/css-color-4/#interpolation): shortest-arc hue interpolation and the powerless hue of a grey",
//!   "the piano page's own maxChroma bisection (arsenal/web/piano.js, colour section): the chroma search this module twins"],
//!  "cost": {"class": "C1", "loop": "oklchMaxChroma and oklchCusp 24 bisection steps, oklchClip (so mixOklch and hueRotateOklch) 16; the conversions are C0", "tex": 0},
//!  "contract": "Linear sRGB to OKLab and back (white is L = 1, a = b = 0; round trip within 1e-5 in gamut) and the polar OKLCH with hue in TURNS 0..1 (a grey's hue is 0, never NaN); mixOklab blends without clipping, so its result may step a hair outside 0..1; mixOklch, oklchClip and hueRotateOklch return linear light inside the gamut with hue unmoved (within 1e-4 turns), and keep HDR light at its own level; oklchCusp is exact everywhere, while oklchMaxChroma and oklchClip assume each hue's gamut slice is a fan from grey, which fails only in the 0.14-degree sliver just past pure blue, where they return a safe but duller chroma.",
//!  "note": "Reach for OKLab whenever a colour must change without its brightness changing: gradients between designer colours, state-colour transitions, hue rotation, saturation. HSV cannot do it: pure blue and pure yellow share an HSV value yet differ thirteen times in luminance. Blend linear light for light (glow, blur, bloom); blend OKLab for colour choices. Wrong looks like a muddy grey middle in a blend (an RGB lerp), blue turning purple as it lightens (CIELAB or HSV), or a hue that jumps when chroma is clipped per channel.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "colour-oklab.card",
//!  "twin": "arsenal/shaders/twins/colour.py", "status": "P0",
//!  "exemplars": [], "learn": ["CP 2.2", "CP 2.3", "CP 2.4", "CP 14.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published mathematics (credits above); no corpus shader uses OKLab.
//
// WHY. RGB is how a screen drives its three lamps; OKLab is how an eye judges the result: one axis for lightness and two
// opponent axes (green to red, blue to yellow), fitted so that equal steps look equal. Working there is like an audio
// engineer mixing in decibels rather than in volts: the knob moves what the listener hears. Two matrix multiplies and a
// cube root, about the cost of one pow per channel.
//
// THE GAMUT. sRGB is a lumpy shape inside OKLab. At each hue its slice is roughly a triangle: black, white and a cusp,
// the most colourful colour of that hue, which sits at very different lightness per hue (yellow near L = 0.97, blue near
// 0.45; this is why HSV's V lies about brightness). Pushing chroma past the edge makes channels leave 0..1; clamping
// them one by one turns the hue, so this module clips by lowering chroma at fixed lightness and hue instead.
//
// Hue is in turns everywhere (0..1, the palette convention); 6.28318530718 is one turn in radians (spelled out so the
// module needs nothing but colour-transfer).

// Linear sRGB -> OKLab (L, a, b): to cone responses, cube root, to opponent axes.
vec3 oklabFromLinear(vec3 lin) {
    vec3 cone = vec3(dot(vec3(0.4122214708, 0.5363325363, 0.0514459929), lin),
                     dot(vec3(0.2119034982, 0.6806995451, 0.1073969566), lin),
                     dot(vec3(0.0883024619, 0.2817188376, 0.6299787005), lin));
    vec3 response = cbrtSigned(cone);
    return vec3(dot(vec3(0.2104542553, 0.7936177850, -0.0040720468), response),
                dot(vec3(1.9779984951, -2.4285922050, 0.4505937099), response),
                dot(vec3(0.0259040371, 0.7827717662, -0.8086757660), response));
}

// OKLab -> linear sRGB. Cubing keeps the sign by itself. The result may leave 0..1: clip when it matters.
vec3 linearFromOklab(vec3 lab) {
    vec3 response = vec3(dot(vec3(1.0, 0.3963377774, 0.2158037573), lab),
                         dot(vec3(1.0, -0.1055613458, -0.0638541728), lab),
                         dot(vec3(1.0, -0.0894841775, -1.2914855480), lab));
    vec3 cone = response * response * response;
    return vec3(dot(vec3(4.0767416621, -3.3077115913, 0.2309699292), cone),
                dot(vec3(-1.2684380046, 2.6097574011, -0.3413193965), cone),
                dot(vec3(-0.0041960863, -0.7034186147, 1.7076147010), cone));
}

// OKLab -> OKLCH (lightness, chroma, hue in turns 0..1). atan(0, 0) is undefined in GLSL, so a grey asks atan(0, 1).
vec3 oklchFromOklab(vec3 lab) {
    float chroma = length(lab.yz);
    float angle = atan(lab.z, lab.y + step(chroma, 0.0));
    return vec3(lab.x, chroma, fract(angle / 6.28318530718));
}

// OKLCH -> OKLab.
vec3 oklabFromOklch(vec3 lch) {
    float angle = 6.28318530718 * lch.z;
    return vec3(lch.x, lch.y * cos(angle), lch.y * sin(angle));
}

// The signed shortest step from hue h0 to hue h1, in turns, in [-0.5, 0.5). 0.9 to 0.1 is +0.2, not -0.8.
float hueDelta(float h0, float h1) {
    float d = h1 - h0 + 0.5;
    return d - floor(d) - 0.5;
}

// Every channel within [-eps, 1 + eps].
bool inGamut(vec3 lin, float eps) {
    return all(greaterThanEqual(lin, vec3(-eps))) && all(lessThanEqual(lin, vec3(1.0 + eps)));
}

// The largest chroma at lightness L and hue h whose colour stays inside sRGB (within eps): 24 halvings of [0, 0.4],
// and 0.4 is above every sRGB chroma (magenta's, the largest, is about 0.32). The same search as the piano's maxChroma,
// so the piano's tolerance (eps = 1e-4) reproduces its colours.
float oklchMaxChroma(float L, float h, float eps) {
    float inC = 0.0;                      // the largest chroma known to be inside
    float outC = 0.4;                     // the smallest chroma known to be outside
    for (int halving = 0; halving < 24; halving++) {
        float probe = 0.5 * (inC + outC);
        bool inside = inGamut(linearFromOklab(oklabFromOklch(vec3(L, probe, h))), eps);
        inC = inside ? probe : inC;
        outC = inside ? outC : probe;
    }
    return inC;
}

// The cusp of hue h: (L, C) of the most colourful sRGB colour of that hue. It always lies on the cube's saturated edge
// (one channel 1, one 0), so this walks that hexagon by HSV hue u, where OKLab hue rises with u -- except beside pure
// blue, where it doubles back along the cyan-to-blue edge (hue 264.05 to 264.19 degrees is met three times). So the
// walk is split at the blue corner: a hue at or past blue's own is searched from blue through magenta to red, where
// its most colourful crossing lives; any other from red through yellow, green and cyan to blue.
vec2 oklchCusp(float h) {
    float hueRed = oklchFromOklab(oklabFromLinear(vec3(1.0, 0.0, 0.0))).z;
    float hueBlue = oklchFromOklab(oklabFromLinear(vec3(0.0, 0.0, 1.0))).z;
    float target = fract(h - hueRed);
    bool pastBlue = target >= fract(hueBlue - hueRed);
    const vec3 thirds = vec3(3.0, 2.0, 1.0) / 3.0;          // each channel's place on the hexagon
    float early = pastBlue ? 2.0 / 3.0 : 0.0;           // HSV hue known to lie before the target
    float late = pastBlue ? 1.0 : 2.0 / 3.0;            // ... and after it
    for (int halving = 0; halving < 24; halving++) {
        float probe = 0.5 * (early + late);
        vec3 tent = abs(6.0 * fract(vec3(probe) + thirds) - 3.0);
        vec3 rim = clamp(tent - 1.0, 0.0, 1.0);
        bool before = fract(oklchFromOklab(oklabFromLinear(rim)).z - hueRed) < target;
        early = before ? probe : early;
        late = before ? late : probe;
    }
    vec3 tent = abs(6.0 * fract(vec3(0.5 * (early + late)) + thirds) - 3.0);
    vec3 lab = oklabFromLinear(clamp(tent - 1.0, 0.0, 1.0));
    return vec2(lab.x, length(lab.yz));
}

// OKLCH -> linear sRGB inside the gamut: lightness clamped to 0..1, then chroma lowered at fixed lightness and hue (16
// halvings of [0, C]) until every channel fits. Hue never moves, unlike clamp(rgb, 0, 1). Returns linear light.
vec3 oklchClip(vec3 lch) {
    float L = clamp(lch.x, 0.0, 1.0);
    float chroma = max(lch.y, 0.0);
    vec3 full = linearFromOklab(oklabFromOklch(vec3(L, chroma, lch.z)));
    if (inGamut(full, 0.0)) {
        return clamp(full, 0.0, 1.0);
    }
    float inC = 0.0;
    float outC = chroma;
    for (int halving = 0; halving < 16; halving++) {
        float probe = 0.5 * (inC + outC);
        bool inside = inGamut(linearFromOklab(oklabFromOklch(vec3(L, probe, lch.z))), 0.0);
        inC = inside ? probe : inC;
        outC = inside ? outC : probe;
    }
    return clamp(linearFromOklab(oklabFromOklch(vec3(L, inC, lch.z))), 0.0, 1.0);
}

// Blend two linear colours in OKLab (even steps, no muddy middle); returns linear, unclipped. OKLab commutes with
// gain, so HDR light blends at its own level.
vec3 mixOklab(vec3 a, vec3 b, float t) {
    return linearFromOklab(mix(oklabFromLinear(a), oklabFromLinear(b), t));
}

// Blend two linear colours in OKLCH: lightness and chroma move straight, hue takes the shorter way round, and the
// result is gamut-clipped. A grey end (chroma under 1e-4) has no hue of its own and borrows the other end's, so grey to
// teal stays teal instead of sweeping the wheel. The honest replacement for "ease through HSV the short way round":
// no grey midpoint and no lightness pumping. HDR-safe: both ends share one gain into the unit cube and back.
vec3 mixOklch(vec3 a, vec3 b, float t) {
    float level = max(1.0, max(max(max(a.r, a.g), a.b), max(max(b.r, b.g), b.b)));
    vec3 lchA = oklchFromOklab(oklabFromLinear(a / level));
    vec3 lchB = oklchFromOklab(oklabFromLinear(b / level));
    float hueA = lchA.y < 1e-4 ? lchB.z : lchA.z;
    float hueB = lchB.y < 1e-4 ? hueA : lchB.z;
    vec3 lch = vec3(mix(lchA.x, lchB.x, t), mix(lchA.y, lchB.y, t), hueA + hueDelta(hueA, hueB) * t);
    return oklchClip(lch) * level;
}

// Turn the hue by `turns` at constant OKLab lightness and chroma, then gamut-clip: the honest "change the colour, keep
// the brightness" (an HSV rotation can change luminance thirteenfold). HDR light turns at its own level.
vec3 hueRotateOklch(vec3 lin, float turns) {
    float level = max(1.0, max(max(lin.r, lin.g), lin.b));
    vec3 lch = oklchFromOklab(oklabFromLinear(lin / level));
    return oklchClip(vec3(lch.x, lch.y, lch.z + turns)) * level;
}
