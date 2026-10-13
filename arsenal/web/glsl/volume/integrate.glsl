//! {"name": "volume-integrate", "kind": "helper", "cat": "G1", "family": "G", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Sebastien Hillaire, 'Physically Based and Unified Volumetric Rendering in Frostbite' (SIGGRAPH 2015, https://www.ea.com/frostbite/news/physically-based-unified-volumetric-rendering-in-frostbite) and 'Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite' (2016): the energy-conserving segment integral",
//!   "Toft, Bowles and Zimmermann, 'Optimisations for Real-Time Volumetric Cloudscapes' (2016, https://arxiv.org/abs/1609.05344): brightness that follows the step length, the artefact this removes",
//!   "Max, 'Optical Models for Direct Volume Rendering' (IEEE TVCG 1995, https://doi.org/10.1109/2945.468400): emission, absorption and front-to-back compositing"],
//!  "cost": {"class": "C0", "loop": "none (one call per march step)", "tex": 0},
//!  "contract": "Beer-Lambert and its front-to-back bookkeeping. volTransmittance(3) is exp(-sigmaT * dist), scalar or per channel. volOpacityFactor(x) is (1 - e^-x) / x, exactly 1 at x = 0 and accurate to a few millionths in 32-bit floats for every x >= 0 (a series below 0.01). VolAccum holds L (light gathered, linear) and T (transmittance, per channel), and volAccumInit gives L = 0, T = 1. volStepScatter adds T * sigmaS * Lin * dt * F(sigmaT * dt) and multiplies T by exp(-sigmaT * dt): the exact integral of a segment with constant coefficients, so a uniform medium gives the same light at one step or a thousand, and with sigmaS <= sigmaT the light never exceeds what the medium removed. volStepEmit is the same for a glowing medium (with sigmaT = 0 it is the plain sum T * emission * dt). volSaturated is true when every channel of T is below eps; volResolve is L + T * background. Honest for sigmaT, sigmaS, dt >= 0.",
//!  "note": "The accounting under every fog, cloud, smoke and aurora: a chain of neutral-density filters, each with a faint lamp inside. Reach for it in every march: start with volAccumInit, call volStepScatter (lit media) or volStepEmit (glowing media) once per step, stop when volSaturated, finish with volResolve over whatever lies behind. Because each step is integrated exactly, a quality tier that halves the steps changes the cost, not the exposure, and a dense slice cannot glow brighter than its albedo. The naive order (add light, then dim) is 35 per cent too bright at an optical depth of 0.64 per step and 131 per cent at 2. Wrong looks like fog that brightens when the step count drops, a dense bank that glows hotter than its light, or banded 'tree rings' (the steps are fine; jitter the start, see dthIgn).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "volume-integrate.card",
//!  "twin": "arsenal/shaders/twins/volume.py", "status": "P0",
//!  "exemplars": ["tsScDG", "XsSGDh", "4slGWM", "llK3Dy", "XtS3DD", "WlVyRV", "ttScDc"],
//!  "learn": ["VA 1.2", "VA 1.3", "VA 1.4", "VA 3.4"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public papers credited above.
//
// WHY. Light crossing a medium loses a fixed fraction per unit length (Beer-Lambert), so optical depth ADDS along a
// ray the way decibels add through a signal chain while the gains multiply. A march cuts the ray into segments and
// keeps two running numbers: the light gathered so far and the fraction of the background still showing. The one
// subtle line is how much light a segment adds: the medium dims its own light as it goes, and integrating that exactly
// gives albedo times the segment's opacity, the "over" operator of compositing, at no extra cost.

// The front-to-back accumulator of one ray.
struct VolAccum {
    vec3 L;     // light gathered so far, linear radiance
    vec3 T;     // transmittance so far, per channel: 1 is clear, 0 is opaque
};

// Nothing gathered yet; everything behind still shows.
VolAccum volAccumInit() {
    VolAccum fresh;
    fresh.L = vec3(0.0);
    fresh.T = vec3(1.0);
    return fresh;
}

// Beer-Lambert: the fraction of light that survives `dist` through extinction sigmaT (per unit length).
float volTransmittance(float sigmaT, float dist) {
    return exp(-sigmaT * dist);
}

// The same, per colour channel, for a medium that dims red, green and blue differently.
vec3 volTransmittance3(vec3 sigmaT, float dist) {
    return exp(-sigmaT * dist);
}

// (1 - e^-x) / x: a segment's opacity per unit of optical depth. Near zero the subtraction would cancel to nothing in
// 32-bit floats, so there the series 1 - x/2 + x^2/6 - x^3/24 is used (its first missing term is below 1e-10).
float volOpacityFactor(float x) {
    if (abs(x) < 0.01) {
        return 1.0 - x * (0.5 - x * (1.0 / 6.0 - x / 24.0));
    }
    return (1.0 - exp(-x)) / x;
}

// Per channel.
vec3 volOpacityFactor(vec3 x) {
    return vec3(volOpacityFactor(x.x), volOpacityFactor(x.y), volOpacityFactor(x.z));
}

// One segment of a lit medium: sigmaS scatters the light Lin toward the eye, sigmaT removes light, over length dt.
void volStepScatter(inout VolAccum a, vec3 sigmaS, vec3 sigmaT, vec3 Lin, float dt) {
    vec3 depth = sigmaT * dt;
    a.L += a.T * sigmaS * Lin * dt * volOpacityFactor(depth);
    a.T *= volTransmittance3(sigmaT, dt);
}

// One segment of a glowing medium (fire, nebula gas, aurora): it emits `emission` per unit length and absorbs sigmaT.
void volStepEmit(inout VolAccum a, vec3 emission, vec3 sigmaT, float dt) {
    vec3 depth = sigmaT * dt;
    a.L += a.T * emission * dt * volOpacityFactor(depth);
    a.T *= volTransmittance3(sigmaT, dt);
}

// The early exit: true once no channel lets more than eps of the background through.
bool volSaturated(VolAccum a, float eps) {
    return max(a.T.r, max(a.T.g, a.T.b)) < eps;
}

// The ray's colour: what it gathered, over what lies behind, dimmed by the medium.
vec3 volResolve(VolAccum a, vec3 background) {
    return a.L + a.T * background;
}
