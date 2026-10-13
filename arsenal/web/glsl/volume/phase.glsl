//! {"name": "volume-phase", "kind": "helper", "cat": "G2", "family": "G", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["L. G. Henyey and J. L. Greenstein, 'Diffuse radiation in the Galaxy' (Astrophysical Journal 93, 1941, https://doi.org/10.1086/144246): the phase function with mean cosine g",
//!   "Matt Pharr, Wenzel Jakob and Greg Humphreys, 'Physically Based Rendering', 4th ed., section 11.3 (https://pbr-book.org/4ed/Volume_Scattering/Phase_Functions): normalisation and the sign convention"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Phase functions in units of per steradian, each integrating to 1 over the sphere. mu is dot(viewRayDir, dirToLight), the house convention, so a positive g glows around the light you look at. phaseIso() is 1 / (4 pi). phaseHG(mu, g) is the normalised Henyey-Greenstein lobe (1 - g^2) / (4 pi (1 + g^2 - 2 g mu)^(3/2)), mean cosine exactly g; mu is clamped to [-1, 1] and g to [-0.9999, 0.9999] (at |g| = 1 the lobe is a spike and the formula 0/0); the denominator is computed as the sum of squares (1 - g mu)^2 + g^2 (1 - mu^2), so it stays positive in 32-bit floats.",
//!  "note": "Where scattered light turns: the radiation pattern of a scatterer, an omnidirectional antenna at g = 0 and a high-gain dish at g near 1. Multiply the light arriving at a sample by phaseHG(dot(rd, toLight), g) before volStepScatter. Haze and droplets scatter forward (g about 0.6 to 0.9): a bright halo around the sun, and at g = 0.8 the back side is 16 times darker than isotropic, which is why one strong lobe makes clouds dull with the sun behind you (blend a second, backward lobe). The forward peak at g = 0.99 is 20,000 times isotropic: keep it in HDR and never clamp before the tonemap. Wrong looks like a halo on the side opposite the sun (the cosine's sign flipped), a brightness ten times off between two shaders (a normalisation typo), or a black or NaN pixel straight at the light (the textbook denominator going negative in float32).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "volume-phase.card",
//!  "twin": "arsenal/shaders/twins/volume.py", "status": "P0", "exemplars": [],
//!  "learn": ["VA 1.5"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public sources credited above.
//
// WHY. A particle that scatters light does not send it everywhere equally: molecules split it fore and aft, droplets
// throw almost all of it forward. A phase function is that preference as a probability over directions, so it
// integrates to one over the sphere and only redistributes light, never adds any.

// Isotropic scattering: the same in every direction, 1 / (4 pi) per steradian.
float phaseIso() {
    return 0.25 / PI;
}

// Henyey-Greenstein with mean cosine g. mu = dot(viewRayDir, dirToLight); positive g glows around the light.
float phaseHG(float mu, float g) {
    float cosine = clamp(mu, -1.0, 1.0);
    float asym = clamp(g, -0.9999, 0.9999);
    float lean = 1.0 - asym * cosine;
    float spread = lean * lean + asym * asym * (1.0 - cosine * cosine);   // 1 + g^2 - 2 g mu, as two squares: >= 0
    float numerator = 1.0 - asym * asym;
    return numerator / (4.0 * PI * spread * sqrt(spread));
}
