//! {"name": "colour-palette", "kind": "helper", "cat": "H4", "family": "H", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'Palettes' (https://iquilezles.org/articles/palettes/): the cosine palette and the roles of its four vectors",
//!   "Bjorn Ottosson, OKLab and OKLCH (https://bottosson.github.io/posts/oklab/): constant-lightness sweeps and perceptual ramps",
//!   "W3C CSS Color Module Level 4 (https://www.w3.org/TR/css-color-4/#interpolation): multi-stop gradients interpolated in OKLab",
//!   "the piano page's pitch palette (arsenal/web/piano.js, colour section): the circle of fifths from 200 degrees, cusp-seeking lightness at 95% of the gamut edge, and the pull toward one shared luminance, which palPitchFifths reproduces within one 8-bit code"],
//!  "cost": {"class": "C1", "loop": "palOklch 16 bisection steps (oklchClip); palPitchFifths 24 for the cusp plus three 24-step chroma searches; palPitchLumaMean is twelve palPitchFifths (compute once, never per pixel); the rest C0", "tex": 0},
//!  "contract": "palCos returns DISPLAY values exactly as Quilez's palettes are tuned on screen (a whole-number c loops seamlessly) and palCosLinear the same palette as linear light; palOklch, palRamp3, palHeatPowers and palPitchFifths return linear light; palOklch holds lightness and chroma constant wherever the gamut allows and clips chroma (never hue) where it does not; palPitchFifths(pc, octave, palPitchPiano()) equals the piano page's own note colour within one 8-bit code for every pitch class (it rounds pc to a whole semitone; the piano ignores octave, and so does palPitchPiano, whose octaveL is 0).",
//!  "note": "Name the currency: Quilez's cosine palettes were tuned on a screen that shows values directly, so they are display values; a lit linear pipeline wants palCosLinear, or every palette goes pale. For an evenly bright sweep use palOklch (a cosine rainbow pumps lightness like HSV); for the house's 'analogous, never a rainbow' rule use palRamp3 through neighbouring hues; for neon and embers palHeatPowers (one intensity, channels saturating in turn). Note colour comes only from palPitchFifths, so C is the same colour on every surface.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "colour-palette.card",
//!  "twin": "arsenal/shaders/twins/palette.py", "status": "P0",
//!  "exemplars": ["WdB3Dw", "llVXRd", "wsl3WB", "Mts3zM", "7d2fDW", "NslGRN", "ffG3Rc", "ttScDc", "MtXczn", "llK3Dy", "MdX3zr", "3XdXRr", "l3cfW4"],
//!  "learn": ["CP 3.1", "CP 3.2", "craft secret 7", "arc-piano-core (3)", "arc-arcs"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published mathematics and the piano's own algorithm (credits above).
//
// WHY. A palette is a promise about colour that many surfaces share. The pitch palette most of all: on 2026-10-13 the
// house had nine copies with different starting angles, so C was a different colour on different surfaces. One
// function here, pinned three ways (this GLSL on SwiftShader, its Python twin, and the piano's JavaScript), makes a note
// one colour everywhere.

// The knobs of the pitch palette. palPitchPiano() returns the piano page's own values.
struct PitchPalette {
    float hueC;        // hue of pitch class C, in turns (the piano: 200 degrees)
    float hueStep;     // hue added per fifth, in turns (1/12: twelve fifths close the circle)
    float baseL;       // the lightness every hue starts from (0.72)
    float cuspPull;    // 0..1: how far each hue moves toward its own most colourful lightness (0.75)
    float cuspGrid;    // the cusp lightness snaps to this grid, as the piano's scan does (0.01); 0 = the exact cusp
    float edge;        // fraction of the sRGB chroma edge used (0.95: near the wall, never on it)
    float gamutEps;    // in-gamut tolerance of the chroma search (the piano's 1e-4)
    float lumaTarget;  // the shared luminance every colour is pulled toward (palPitchLumaMean); 0 = no pull
    float lumaPull;    // 0..1: how far toward it (0.65: velocity, not the note's name, decides brightness)
    float octaveL;     // lightness added per octave above octave 4 (the piano: 0, it ignores the octave)
};

// The piano page's pitch palette (arsenal/web/piano.js, colour mode "pitch"). lumaTarget is palPitchLumaMean of these
// same knobs, computed once by the twin (arsenal/shaders/twins/palette.py) and held equal to it by a test.
PitchPalette palPitchPiano() {
    return PitchPalette(200.0 / 360.0, 1.0 / 12.0, 0.72, 0.75, 0.01, 0.95, 1.0e-4, 0.37631920377545836, 0.65, 0.0);
}

// Quilez's cosine palette: per channel a + b cos(2 pi (c t + d)). a is the centre, b the swing (a = b = 0.5 uses all
// of 0..1 and never clips), c the cycles per unit t (whole numbers loop seamlessly), d the phase (thirds apart give a
// rainbow; close together, a two-hue gradient). Returns DISPLAY values, as tuned on screen.
vec3 palCos(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    vec3 cycles = c * t + d;              // where each channel's oscillator is, in turns
    return a + b * cos(6.28318530718 * cycles);
}

// The same palette as linear light, for lit and blended pipelines that encode at the end.
vec3 palCosLinear(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return srgbDecode(palCos(t, a, b, c, d));
}

// A hue sweep at constant OKLab lightness L and chroma C: hue runs from h0 through `turns` as t goes 0 to 1. Every step
// is equally bright and equally colourful, the even rainbow HSV cannot give; chroma is clipped (never hue) where the
// gamut is too narrow. Linear light.
vec3 palOklch(float t, float L, float C, float h0, float turns) {
    return oklchClip(vec3(L, C, h0 + turns * t));
}

// Three linear colours as one gradient interpolated in OKLab: A at t = 0, B at 0.5, C at 1 (t clamped). Pick three
// neighbouring hues (cyan, electric blue, indigo) for the house's analogous palettes. Linear light.
vec3 palRamp3(float t, vec3 linA, vec3 linB, vec3 linC) {
    float u = 2.0 * clamp(t, 0.0, 1.0);
    vec3 lab = mix(oklabFromLinear(linA), oklabFromLinear(linB), clamp(u, 0.0, 1.0));
    lab = mix(lab, oklabFromLinear(linC), clamp(u - 1.0, 0.0, 1.0));
    return linearFromOklab(lab);
}

// One intensity to a colour by a power per channel, x^e (exponents > 0). Below 1 the smallest exponent leads, so dim is
// deep; at 1 every channel meets in white; past 1 the largest leads. (1, 2, 4) is an ember (red, orange, yellow,
// white); (2, 1, 0.5) a neon blue that whitens. The cheapest convincing glow colour there is.
vec3 palHeatPowers(float x, vec3 exponents) {
    return pow(vec3(max(x, 1.0e-20)), exponents);
}

// The house note colour, linear light. pitchClass is rounded to a whole semitone, mod 12 (C = 0, C# = 1, ...).
//   hue:   walks the circle of fifths, so a key's notes share one arc of hues and a modulation visibly shifts it;
//   light: each hue sits near the lightness where sRGB lets it be most colourful (blue and violet peak dark, yellow
//          and teal light), at `edge` of the gamut wall, so no note is a pastel;
//   level: the colour is scaled toward one shared luminance, because at full colour yellow-green is about 4.7 times
//          brighter than violet, and a soft yellow note must not outshine a hard violet one.
// The piano scans 68 lightness steps for each hue's cusp; this finds the cusp exactly (oklchCusp) and snaps it to the
// same 0.01 grid, which gives the same colours for a fraction of the work.
vec3 palPitchFifths(float pitchClass, float octave, PitchPalette pp) {
    float pc = mod(floor(pitchClass + 0.5), 12.0);
    float hue = fract(pp.hueC + pp.hueStep * mod(pc * 7.0, 12.0));
    float cuspL = oklchCusp(hue).x;
    if (pp.cuspGrid > 0.0) {
        float below = floor(cuspL / pp.cuspGrid) * pp.cuspGrid;
        float above = below + pp.cuspGrid;
        bool belowWins = oklchMaxChroma(below, hue, pp.gamutEps) >= oklchMaxChroma(above, hue, pp.gamutEps);
        cuspL = belowWins ? below : above;
    }
    float baseL = pp.baseL + pp.octaveL * (octave - 4.0);
    float L = clamp(mix(baseL, cuspL, pp.cuspPull), 0.0, 1.0);
    float chroma = pp.edge * oklchMaxChroma(L, hue, pp.gamutEps);
    vec3 rgb = max(linearFromOklab(oklabFromOklch(vec3(L, chroma, hue))), vec3(0.0));
    if (pp.lumaTarget > 0.0) {
        rgb *= pow(pp.lumaTarget / max(luminance(rgb), 1.0e-4), pp.lumaPull);
    }
    return rgb;
}

// The geometric mean luminance of the twelve pitch colours before the pull: the level palPitchFifths pulls toward.
// Twelve palette evaluations: compute it once (the twin, or a one-off pass) and store it in lumaTarget; never per pixel.
float palPitchLumaMean(PitchPalette pp) {
    PitchPalette raw = pp;
    raw.lumaTarget = 0.0;
    float logSum = 0.0;
    for (int note = 0; note < 12; note++) {
        logSum += log(max(luminance(palPitchFifths(float(note), 4.0, raw)), 1.0e-30));
    }
    return exp(logSum / 12.0);
}
