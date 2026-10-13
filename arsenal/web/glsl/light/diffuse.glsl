//! {"name": "light-diffuse", "kind": "helper", "cat": "F1", "family": "F", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Johann Heinrich Lambert, Photometria (1760; https://en.wikipedia.org/wiki/Lambert%27s_cosine_law): the cosine law",
//!   "Jason Mitchell, Gary McTaggart and Chris Green, 'Shading in Valve's Source Engine' (SIGGRAPH 2006; https://developer.valvesoftware.com/wiki/Half_Lambert): half-Lambert",
//!   "Simon Green, 'Real-Time Approximations to Subsurface Scattering' (GPU Gems, chapter 16, https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-16-real-time-approximations-subsurface-scattering): wrap lighting",
//!   "Steve McAuley, 'Energy-conserving wrapped diffuse' (http://blog.stevemcauley.com/2011/12/03/energy-conserving-wrapped-diffuse/): the (1 + w)^2 divisor",
//!   "Inigo Quilez, 'outdoors lighting' (https://iquilezles.org/articles/outdoorslighting/): the sky term 0.5 + 0.5 n.y"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "n and l are unit vectors, l pointing from the surface toward the light; the house folds 1/pi into light colours, so a light's diffuse is albedo * lightCol * litLambert(n, l). litLambert is max(n.l, 0). litHalfLambert is (0.5 n.l + 0.5)^2: zero only straight behind, a stylisation that does not conserve energy. litWrapDiffuse is max((n.l + w) / (1 + w)^2, 0) with w clamped to [0, 1]: it lights up to n.l = -w, peaks at 1 / (1 + w), and integrates over all directions to exactly pi for every w, Lambert's own energy. litHemisphere is mix(groundCol, skyCol, 0.5 + 0.5 n.y), the exact irradiance (pi folded) of a uniform sky dome over a uniform ground with nothing in the way; y is up.",
//!  "note": "Diffuse is the matte part of a surface: light that went in, scattered and came out in every direction, so only the angle to the light matters, never the eye. Lambert is the physical one and the right default once the maths is in linear light (Quilez: then plain n.l falls off realistically and needs no softening). Reach for wrap to soften a terminator on skin, wax, leaves or a studio product (the energy-normalised form, so the softened light is paid for by a dimmer peak, not added), for half-Lambert when a stylised object must keep its shape on the dark side, and for litHemisphere as the sky fill under a key, multiplied by ambient occlusion (never the key). Wrong looks like a hard black terminator on something soft (plain Lambert where wrap was meant), a glowing grey back face that reads as fog (half-Lambert on a realistic scene), or a wrapped object brighter overall than its Lambert twin (an unnormalised wrap adding light).",
//!  "targets": {"glsl": "100", "needs": []}, "card": "light-diffuse.card",
//!  "twin": "arsenal/shaders/twins/light.py", "status": "P0",
//!  "exemplars": ["NslGRN", "XtyXzW", "4s23zz", "llVXRd"],
//!  "learn": ["LM 1.3", "LM 2.1", "LM 2.2", "LM 2.4", "study:XtyXzW 5.12"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published formulas (credits above).
//
// WHY. A torch beam hitting a wall at a slant spreads over a bigger patch, so each bit of the patch gets less: that
// spreading is the cosine n.l, and it is all a matte surface needs to know. The variants below bend that one curve:
// half-Lambert lifts the back side for stylised shapes, wrap lets light creep past the terminator the way it does
// through skin, and the hemisphere term is the whole sky seen from a tilted patch.

// The clamped cosine between the normal and the direction to the light.
float litLambert(vec3 n, vec3 l) {
    float facing = dot(n, l);
    return max(facing, 0.0);
}

// The cosine remapped from [-1, 1] to [0, 1] and squared: dark only straight behind.
float litHalfLambert(vec3 n, vec3 l) {
    float lifted = 0.5 * dot(n, l) + 0.5;
    return lifted * lifted;
}

// Wrapped diffuse, energy-normalised: (n.l + w) / (1 + w)^2, clamped at zero. w = 0 is Lambert; w = 1 lights all
// the way round to the back with a peak of one half.
float litWrapDiffuse(vec3 n, vec3 l, float w) {
    float wrap = clamp(w, 0.0, 1.0);
    float spread = 1.0 + wrap;
    float wrapped = (dot(n, l) + wrap) / (spread * spread);
    return max(wrapped, 0.0);
}

// Sky above, ground below: the share of an unoccluded upper dome a normal faces is 0.5 + 0.5 n.y.
vec3 litHemisphere(vec3 n, vec3 skyCol, vec3 groundCol) {
    float skyShare = 0.5 + 0.5 * n.y;
    return mix(groundCol, skyCol, skyShare);
}
