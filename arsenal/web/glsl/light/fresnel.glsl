//! {"name": "light-fresnel", "kind": "helper", "cat": "F3", "family": "F", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Christophe Schlick, 'An inexpensive BRDF model for physically-based rendering' (Computer Graphics Forum 13(3), 1994; https://en.wikipedia.org/wiki/Schlick%27s_approximation): the fifth-power approximation",
//!   "Sebastien Lagarde, 'Memo on Fresnel equations' (https://seblagarde.wordpress.com/2013/04/29/memo-on-fresnel-equations/): F0 from the index, and where Schlick stops being honest",
//!   "Naty Hoffman, 'Fresnel Equations Considered Harmful' (https://renderwonk.com/publications/mam2019/): Schlick with a coloured F0 for metals"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "litFresnelSchlick(cosTheta, F0) = F0 + (1 - F0)(1 - c)^5 with c = clamp(cosTheta, 0, 1), and the vec3 overload litFresnelSchlick(F0, cosTheta) does the same per channel (coloured F0 for metals). Use c = v.h inside a BRDF and c = n.v for environment light and reflections. It equals F0 head-on and 1 at grazing, and stays within 0.02 of the exact dielectric Fresnel for glass below 80 degrees; it never produces total internal reflection (use the exact form, planned at P1, from inside glass). litF0FromIor(n) = ((n - 1) / (n + 1))^2 against air, n floored at 0, the same for n and 1/n: water 1.33 gives 0.020, glass 1.5 gives 0.04, diamond 2.42 gives 0.172. litRim(NoV, p) = (1 - clamp(NoV, 0, 1))^p with the base floored at 1e-30 (core-safe safePow): an art rim term, deliberately NOT a Fresnel.",
//!  "note": "Every surface becomes a mirror at grazing angles: that is why a lake mirrors the far shore yet lets you see the stones at your feet, and why glass edges glint. F0 is about 0.04 for nearly every non-metal (water 0.02, gems up to 0.17) and the coloured base colour for a metal. litRim is the thing shader art often calls 'fresnel': (1 - n.v)^p with no F0 floor. It is a legitimate edge glow (a small power such as 0.2 flattens a ball into a glowing disc), but it is named rim so nobody adds it to a physically based path on top of a real Fresnel, which double-counts the edge. Wrong looks like a bright white halo round everything (rim plus Fresnel), glass that reads as a hole cut in the scene (no Fresnel reflection), or a head-on metal that is grey (white F0 on gold).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "light-fresnel.card",
//!  "twin": "arsenal/shaders/twins/light.py", "status": "P0",
//!  "exemplars": ["XsSGDh", "3XdXRr", "43jXWt", "NslGRN", "XdcyDM", "4lj3Ww", "NlK3Wt", "llVXRd"],
//!  "learn": ["LM 5.1", "LM 5.2", "LM 5.3", "LM 5.6", "study:3XdXRr 4.6", "study:43jXWt 4.6"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published formulas (credits above).
//
// WHY. At a boundary between two materials part of the light bounces and the rest goes in, and the bounced share
// climbs from a small F0 head-on to everything at grazing. Schlick's curve is the fifth power of the "how far from
// head-on" amount, which matches the real equations closely for anything that is not seen from inside.

// The fifth power of the grazing amount 1 - cosTheta, by multiplication.
float litFresnelSchlick(float cosTheta, float F0) {
    float grazing = clamp(1.0 - cosTheta, 0.0, 1.0);
    float grazing2 = grazing * grazing;
    float fifth = grazing2 * grazing2 * grazing;
    return F0 + (1.0 - F0) * fifth;
}

// The same curve per channel, for a coloured F0 (a metal's base colour).
vec3 litFresnelSchlick(vec3 F0, float cosTheta) {
    float grazing = clamp(1.0 - cosTheta, 0.0, 1.0);
    float grazing2 = grazing * grazing;
    float fifth = grazing2 * grazing2 * grazing;
    return F0 + (vec3(1.0) - F0) * fifth;
}

// Reflectance at normal incidence from an index of refraction (against air, or a relative index).
float litF0FromIor(float ior) {
    float index = max(ior, 0.0);
    float ratio = (index - 1.0) / (index + 1.0);
    return ratio * ratio;
}

// An art rim: brightest where the surface turns away from the eye. Not a Fresnel.
float litRim(float NoV, float power) {
    float edgeOn = 1.0 - clamp(NoV, 0.0, 1.0);
    return safePow(edgeOn, power);
}
