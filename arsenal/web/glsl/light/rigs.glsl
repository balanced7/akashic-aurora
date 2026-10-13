//! {"name": "light-rigs", "kind": "helper", "cat": "F10", "family": "F", "version": "1.0.0", "order": 26,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'outdoors lighting' (https://iquilezles.org/articles/outdoorslighting/): one light per role, each with its own visibility, and never ambient occlusion on the key",
//!   "tdhooper, 'Glitch Transform' (https://www.shadertoy.com/view/XtyXzW) and 'Geodesic' (https://www.shadertoy.com/view/llVXRd): the studio rig of wrapped key, sky, back and rim with the specular added after the albedo, and an emissive bypass (the technique, read in words; no code taken)",
//!   "Romain Guy and Mathias Agopian, 'Physically Based Rendering in Filament' (https://google.github.io/filament/Filament.html): the metallic split into a diffuse colour and F0, and fading the grazing reflection of an F0 below 0.02"],
//!  "cost": {"class": "C0", "loop": "none (one litStudioEnv lookup)", "tex": 0},
//!  "contract": "LitSurface is a resolved surface: diffuseColor (linear albedo of the diffuse part, 0 for metals), F0 (reflectance head-on: 0.04 for most dielectrics, the base colour for metals), alpha (microfacet roughness, the perceptual roughness squared) and emissive (linear HDR light it gives off). rigStudio(s, n, v, ao, sp) with unit n and v (v toward the eye; the parameter is spelled toEye) returns s.diffuseColor * (key + sky + back + rim) + reflection + s.emissive, where key = sp.keyCol * litWrapDiffuse(n, sp.keyDir, sp.keyWrap); sky = litHemisphere(n, sp.skyCol, sp.floorCol) * ao; back = sp.fillCol * litLambert(n, sp.fillDir) * ao; rim = sp.horizonCol * litRim(n.v, 2) * ao; reflection = litStudioEnv(reflect(-v, n), sqrt(alpha), sp) * F * ao with F = F0 + (Schlick(F0, n.v) - F0) * clamp(50 * mean(F0), 0, 1); ao is clamped to [0, 1]. So ao darkens the fills and the reflection and never the key; the emission is added unlit; a surface with F0 = 0 reflects nothing even at grazing; a metal (diffuse 0, F0 1) is exactly its studio. A host with a shadow ray scales sp.keyCol by it before the call.",
//!  "note": "The product-shot rig every hero object can call: a soft wrapped key for form, a sky fill and a cool back light for the shadow side, a faint rim to separate it from a dark backdrop, and the studio's reflection added AFTER the albedo multiply, which is what lets a near-black object still read as glossy black rather than a hole. Because the reflection comes from the same StudioParams as the lights, the highlight on a ball is the key soft box itself: move the key and the highlight follows. Keep albedos dim (0.04 to 0.8) and make the lights bright; let the tone curve have a shoulder. Wrong looks like flat CG with dark halos (AO on the key), a gold ball that reads as yellow plastic (a diffuse term on a metal), a black ball that disappears (no reflection), or an emissive part with a shaded dark side (emission put through the lighting).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "light-rigs.card",
//!  "twin": "arsenal/shaders/twins/light.py", "status": "P0",
//!  "exemplars": ["XtyXzW", "llVXRd", "43jXWt"],
//!  "learn": ["LM 4.6", "LM 6.4", "LM 6.5", "LM 8.1", "LM 13.1", "LM 14.1", "study:XtyXzW 5.12", "study:llVXRd 4.11"]}
// Apache-2.0, Akashic Aurora. Written fresh from the techniques credited above.
//
// WHY. A lighting rig is a mixing desk: each light is a channel with one job (the key gives form, the fills lift the
// shadows, the rim separates the subject from the backdrop) and its own gate (the key is gated by a shadow, the fills
// by occlusion). Putting the desk in one function means every hero object in the house is lit the same way, and a
// change to the rig reaches all of them.

// A resolved surface: what the rigs shade.
struct LitSurface {
    vec3 diffuseColor;   // linear albedo of the diffuse part (0 for metals)
    vec3 F0;             // reflectance head-on (0.04 for most dielectrics; the base colour for metals)
    float alpha;         // microfacet roughness: the perceptual roughness squared
    vec3 emissive;       // linear HDR light the surface gives off; never shaded, never occluded
};

// The studio rig: wrapped key + sky + back + rim on the diffuse colour, the studio's reflection, and the emission.
vec3 rigStudio(LitSurface s, vec3 n, vec3 toEye, float ao, StudioParams sp) {
    float unblocked = clamp(ao, 0.0, 1.0);
    float viewCos = clamp(dot(n, toEye), 0.0, 1.0);
    vec3 key = sp.keyCol * litWrapDiffuse(n, sp.keyDir, sp.keyWrap);
    vec3 sky = litHemisphere(n, sp.skyCol, sp.floorCol) * unblocked;
    vec3 back = sp.fillCol * litLambert(n, sp.fillDir) * unblocked;
    vec3 rim = sp.horizonCol * litRim(viewCos, 2.0) * unblocked;
    vec3 diffuse = s.diffuseColor * (key + sky + back + rim);
    vec3 mirrored = reflect(-toEye, n);
    float roughness = sqrt(clamp(s.alpha, 0.0, 1.0));
    float grazingGain = clamp(50.0 * dot(s.F0, vec3(1.0 / 3.0)), 0.0, 1.0);
    vec3 fresnel = s.F0 + (litFresnelSchlick(s.F0, viewCos) - s.F0) * grazingGain;
    vec3 reflection = litStudioEnv(mirrored, roughness, sp) * fresnel * unblocked;
    return diffuse + reflection + s.emissive;
}
