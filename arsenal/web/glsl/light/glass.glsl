//! {"name": "light-glass", "kind": "helper", "cat": "F7", "family": "F", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Willebrord Snellius (1621) and the GLSL ES 3.00 specification's refract() (https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf, section 8.5): the refraction formula and its total-internal-reflection case",
//!   "Khronos Group, KHR_materials_volume (https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_materials_volume): attenuation colour at a distance, so sigma = -ln(c) / d",
//!   "August Beer (1852) and Johann Heinrich Lambert (1760), the Beer-Lambert law (https://en.wikipedia.org/wiki/Beer%E2%80%93Lambert_law): exponential absorption"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "litRefractTIR(i, n, eta, out t): i is the unit incident direction, n a unit normal on EITHER side of the surface (it is turned to face the incoming ray), eta = n_from / n_to (1/1.5 entering glass, 1.5 leaving it). It returns true with t the unit refracted direction, obeying Snell's law (sin of the transmitted angle = eta times sin of the incident one, in the plane of i and n); under total internal reflection (eta sin > 1) it returns false and t holds the unit mirror direction, so the caller can simply keep tracing t. litSigmaFromColour(c, dist) = -ln(clamp(c, 1e-6, 1)) / max(dist, 1e-6): the absorption coefficient that turns white light into c after dist, so exp(-sigma d) is c at d = dist, c^2 at 2 dist, and white for c = 1.",
//!  "note": "Glass bends light toward the normal going in and away from it coming out; from inside, past the critical angle (about 42 degrees for glass) nothing gets out and the surface becomes a perfect mirror. That mirror is light, not darkness: treating it as 'no ray' paints black edges on every glass object, which is the commonest glass bug. A sphere can never trap its first exit (symmetry), but blocks, prisms and gems do, and the light that bounces inside is what makes them sparkle. Colour glass by absorption, not by multiplying a tint: pick the colour white light should have after a known thickness and let Beer-Lambert do the rest, so thick parts go deep and saturated and thin edges stay pale. Wrong looks like black rims (TIR dropped), refraction bending away from the normal on entry (eta inverted), or a uniformly tinted object with no thickness cue.",
//!  "targets": {"glsl": "100", "needs": []}, "card": "light-glass.card",
//!  "twin": "arsenal/shaders/twins/light.py", "status": "P0",
//!  "exemplars": ["XsSGDh", "NslGRN", "XdcyDM"],
//!  "learn": ["LM 9.4", "LM 10.1", "LM 10.2", "LM 15"]}
// Apache-2.0, Akashic Aurora. Written fresh from the physics (credits above).
//
// WHY. Light slows down in glass, and a wavefront that hits the surface at a slant has one edge slowed first, so it
// pivots: that is refraction, the way a marching column wheels when one end steps onto mud. Coming out of the dense
// side at too steep a slant there is no angle that satisfies Snell's law, and every bit of the light reflects.

// Snell refraction with total internal reflection reported, not hidden. t is always a usable unit direction.
bool litRefractTIR(vec3 i, vec3 n, float eta, out vec3 t) {
    vec3 facing = dot(i, n) > 0.0 ? -n : n;                // the normal on the side the ray arrives from
    float cosIn = -dot(i, facing);
    float sinOut2 = eta * eta * (1.0 - cosIn * cosIn);
    if (sinOut2 > 1.0) {
        t = i + 2.0 * cosIn * facing;                      // no way out: the mirror direction
        return false;
    }
    float cosOut = sqrt(1.0 - sinOut2);
    t = eta * i + (eta * cosIn - cosOut) * facing;
    return true;
}

// The Beer-Lambert absorption coefficient that turns white light into colourAtDist after dist.
vec3 litSigmaFromColour(vec3 colourAtDist, float dist) {
    vec3 kept = clamp(colourAtDist, vec3(1e-6), vec3(1.0));
    return -log(kept) / max(dist, 1e-6);
}
