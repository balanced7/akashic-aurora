//! {"name": "noise-fbm", "kind": "helper", "cat": "B3", "family": "B", "version": "1.0.0", "order": 25,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'fBM' (https://iquilezles.org/articles/fbm/): the Hurst exponent, why G = 0.5 suits mountains and clouds, and octave hygiene (turn every octave, detune the lacunarity)",
//!   "F. Kenton Musgrave, 'Procedural Fractal Terrains' in Ebert et al., Texturing and Modeling (https://www.classes.cs.uchicago.edu/archive/2015/fall/23700-1/final-project/MusgraveTerrain00.pdf): fBm as a spectral synthesis with lacunarity, gain and octaves"],
//!  "cost": {"class": "C1", "loop": "octaves <= 8", "tex": 0, "per_octave": "one noiseGrad2 or noiseGrad3"},
//!  "contract": "gainFromHurst is lacunarity^(-hurst) (H = 1 gives 0.5 at L = 2). fbmGrad2 and fbmGrad3 sum gain^i times gradient noise over min(octaves, 8) octaves and divide by the sum of gain^i, i.e. by (1 - G^n)/(1 - G), so the result stays within [-1, 1] whatever the octave count (0 or fewer octaves give 0; one octave is exactly noiseGrad of p). Between octaves the point turns by the golden angle (in 3D about the axis (1, 2, 3)), scales by the lacunarity detuned upward by an irregular 0 to 2 per cent, steps off the lattice by a fixed offset, and the octave hashes with seed + i: no lattice shows and the origin has no pinch. Honest while the last octave's coordinates stay under about 2^20.",
//!  "note": "The house's fractal fabric: clouds, smoke, terrain, the fold under an aurora curtain. Octaves is how many faders are in the graphic equaliser, gain is the one slope knob that sets them all (0.5 for mountains and clouds, 0.707 for a rougher brown look; gainFromHurst gives it from the fractal exponent), lacunarity is the spacing of the faders (about 2). Use fewer octaves than you think: past about log2(resolution) - 2 the extra detail only sparkles. Wrong looks like a square grid or regular bumps (no turn or an exact lacunarity of 2), a symmetric pinch at the origin (octaves that never step off the lattice), or a picture that brightens as octaves are added (not normalised).",
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "noise-fbm.card",
//!  "twin": "arsenal/shaders/twins/noise.py", "status": "P0",
//!  "exemplars": ["4s23zz", "4slGWM", "MsjfRG", "XtS3DD", "tsScDG", "ttScDc"],
//!  "learn": ["NP 7.1"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. One noise call is one band of detail. Real surfaces have detail at every scale, smaller detail being weaker,
// so fBm adds copies of the noise at rising frequency and falling amplitude: a graphic equaliser where one slope knob
// sets every fader. The house version divides by the total amplitude, so turning the octave count up adds detail
// without turning the brightness up, and it keeps the lattice hidden: every octave turns by the golden angle (the most
// irrational turn there is, so no two octaves' grids ever line up again), scales by a lacunarity nudged off 2.0, and
// steps off the lattice so the octaves' zero points never stack at the origin.

// The gain that gives a fractal of Hurst exponent `hurst` at this lacunarity: L^(-H).
float gainFromHurst(float hurst, float lacunarity) {
    return pow(lacunarity, -hurst);
}

// Normalised fBm of 2D gradient noise, at most 8 octaves.
float fbmGrad2(vec2 p, int octaves, float lacunarity, float gain, uint seed) {
    const float turnCos = -0.73736888;                     // the golden angle, 137.5 degrees
    const float turnSin = 0.67549029;
    float total = 0.0;
    float amp = 1.0;
    float ampSum = 0.0;
    vec2 q = p;
    for (int band = 0; band < 8; band++) {               // a constant ceiling: at most 8 octaves
        if (band >= octaves) break;
        total += amp * noiseGrad2(q, seed + uint(band));
        ampSum += amp;
        amp *= gain;
        float stride = lacunarity * (1.0 + 0.02 * fract(0.6180339887 * float(band + 1)));
        q = vec2(turnCos * q.x - turnSin * q.y, turnSin * q.x + turnCos * q.y) * stride + vec2(19.19, -7.31);
    }
    return ampSum > 0.0 ? total / ampSum : 0.0;
}

// Normalised fBm of 3D gradient noise, at most 8 octaves; the turn is the golden angle about the axis (1, 2, 3).
float fbmGrad3(vec3 p, int octaves, float lacunarity, float gain, uint seed) {
    const mat3 turn = mat3(-0.61327110, 0.78979268, 0.01122858,     // columns
                           -0.29340157, -0.24097777, 0.92511904,
                           0.73335808, 0.56405429, 0.37951111);
    float total = 0.0;
    float amp = 1.0;
    float ampSum = 0.0;
    vec3 q = p;
    for (int band = 0; band < 8; band++) {               // a constant ceiling: at most 8 octaves
        if (band >= octaves) break;
        total += amp * noiseGrad3(q, seed + uint(band));
        ampSum += amp;
        amp *= gain;
        float stride = lacunarity * (1.0 + 0.02 * fract(0.6180339887 * float(band + 1)));
        q = turn * q * stride + vec3(19.19, -7.31, 11.57);
    }
    return ampSum > 0.0 ? total / ampSum : 0.0;
}
