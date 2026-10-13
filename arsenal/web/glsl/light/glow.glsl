//! {"name": "light-glow", "kind": "helper", "cat": "F9", "family": "F", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Xor, the GM Shaders volumetric tutorial (https://mini.gmshaders.com/): colour divided by distance per march step, the shader-art 1/d glow",
//!   "Inigo Quilez, 'Rendering Worlds with Two Triangles' (NVSCENE 2008, https://iquilezles.org/articles/nvscene2008/): glow and occlusion read from the distances a march already measures",
//!   "Hendrik Antoon Lorentz and the Cauchy distribution (https://en.wikipedia.org/wiki/Cauchy_distribution): k / (k + d^2), the line shape with the long tail",
//!   "XT95, 'Flame' (https://www.shadertoy.com/view/MdX3zr): brightness from how long the ray loitered (the technique, read in words; no code taken)"],
//!  "cost": {"class": "C0", "loop": "none (each call is one step's or one sample's worth)", "tex": 0},
//!  "contract": "glowAccum(acc, colour, d, minD) = acc + colour / max(d, max(minD, 1e-6)): one march step of the 1/d halo; a negative d (inside) counts as the floor. glowEmitStep(density, stepLen, k) = k * density * max(stepLen, 0): emission integrated over one step, so a march's sum converges to the integral of k * density whatever the step count. glowExp(minDist, k) = exp(-k * max(minDist, 0)) from the closest approach. glowLorentz(d, k) = k / (k + d^2) with k floored at 1e-12: 1 at d = 0, one half at d = sqrt(k), tails falling as k / d^2. glowTwoGauss(d, coreHalo) = coreHalo.y * exp(-coreHalo.x d^2) + coreHalo.w * exp(-coreHalo.z d^2): (core sharpness, core gain, halo sharpness, halo gain); (24, 1, 3, 0.18) is gyre-flight's light line and (38, 0.78, 5, 0.12) gyre-light-rays'. glowHotCore(tint, i) = i * mix(tint, vec3(peak), i^2 / (1 + i^2)) with i floored at 0 and tint at 0, peak its largest channel: the hottest channel is always exactly i * peak, the others climb toward it, half way at i = 1 and within 2 per cent by i = 8; linear HDR, tonemap after. glowStepCount(steps, maxSteps, k) = 1 - (1 - s)^k with s = clamp(steps / max(maxSteps, 1), 0, 1) and k floored at 1e-3.",
//!  "note": "Most single-pass glow is not post-processing: while a ray marches, every step already knows how far the nearest glowing thing is, and adding a falloff of that distance is bloom computed at the source. Choose the falloff by look: glowAccum's 1/d is the popular hot halo, but it is a Riemann sum whose brightness changes with the step count and the epsilon; glowEmitStep (a density times the step length) is the same idea done as an integral, so it does not; glowExp of the closest approach is stable but cannot tell one glowing tube from two in a row; glowLorentz is a needle core whose tails, summed over hundreds of segments, become bloom with no blur pass; glowTwoGauss is the house's own light-line profile. glowHotCore is how neon, plasma and fire read as BRIGHT rather than merely coloured: the core whitens while the halo keeps its hue. glowStepCount turns marcher effort into light: silhouettes, folds and inner rims glow because that is where the ray loitered (k < 1 keeps quick misses dark, k > 1 lifts faint counts). Glow is light: add it after shading, stop accumulating at a hit or multiply by the transmittance so it does not shine through walls, and give the tone curve a shoulder. Wrong looks like glow that changes when the step count changes (1/d where an integral was meant), a halo that whitens before its core, or banded rings (step counts with no jitter).",
//!  "targets": {"glsl": "100", "needs": []}, "card": "light-glow.card",
//!  "twin": "arsenal/shaders/twins/light.py", "status": "P0",
//!  "exemplars": ["7cjGRR", "MdsXWM", "WdB3Dw", "tsScDG", "3XdXRr", "XfXGz4", "ldSfWV", "l3cfW4", "MdX3zr", "llK3Dy", "4tcXRr"],
//!  "learn": ["LM 12.1", "LM 12.2", "LM 12.3", "CP 6.6", "arc-piano-studies D2", "study:MdX3zr 6.1", "study:4tcXRr 4.6", "study:WdB3Dw 5.8"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics (credits above).
//
// WHY. A glowing thing lights the air around it, and a ray passing near it collects that light. The march measures
// the distance to the glowing thing at every step for free, so the halo costs one falloff per step: the choice of
// falloff is the choice of lens, and the step length is what turns a per-step guess into a measured integral.

// One step of the inverse-distance halo, with a floor so a ray through the emitter stays finite.
vec3 glowAccum(vec3 acc, vec3 colour, float d, float minD) {
    float nearest = max(d, max(minD, 1e-6));
    return acc + colour / nearest;
}

// Emission density times the step length: what one step adds to an integral along the ray.
float glowEmitStep(float density, float stepLen, float k) {
    float stepCovered = max(stepLen, 0.0);
    return k * density * stepCovered;
}

// Glow from the closest approach of the whole ray.
float glowExp(float minDist, float k) {
    float closest = max(minDist, 0.0);
    return exp(-k * closest);
}

// The Lorentzian line shape: height 1, half height at d = sqrt(k).
float glowLorentz(float d, float k) {
    float width2 = max(k, 1e-12);
    return width2 / (width2 + d * d);
}

// A narrow Gaussian core plus a wide Gaussian halo; coreHalo = (core sharpness, core gain, halo sharpness, halo gain).
float glowTwoGauss(float d, vec4 coreHalo) {
    float d2 = d * d;
    float core = coreHalo.y * exp(-coreHalo.x * d2);
    float halo = coreHalo.w * exp(-coreHalo.z * d2);
    return core + halo;
}

// A tint that whitens as it gets hotter: the brightest channel leads at i * peak and the others rise to meet it.
vec3 glowHotCore(vec3 tint, float intensity) {
    float heat = max(intensity, 0.0);
    vec3 hue = max(tint, vec3(0.0));
    float peak = max(hue.r, max(hue.g, hue.b));
    float whiten = heat * heat / (1.0 + heat * heat);
    return heat * mix(hue, vec3(peak), whiten);
}

// How much of the step budget the ray spent, as light: 1 - (1 - used)^k.
float glowStepCount(float steps, float maxSteps, float k) {
    float used = clamp(steps / max(maxSteps, 1.0), 0.0, 1.0);
    return 1.0 - pow(1.0 - used, max(k, 1e-3));
}
