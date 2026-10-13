//! {"name": "atmos-fog", "kind": "helper", "cat": "G7", "family": "G", "version": "1.0.0", "order": 24,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'fog' (https://iquilezles.org/articles/fog/): exponential distance fog and its colour controls",
//!   "Pierre Bouguer and Johann Heinrich Lambert, the attenuation law (https://en.wikipedia.org/wiki/Beer%E2%80%93Lambert_law): the transmittance it is built on"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "fogExp(col, fogCol, dist, k) is mix(col, fogCol, 1 - exp(-k * dist)) in linear light: exactly col at distance 0, approaching fogCol with distance, the fog's share growing by Beer's law (it calls volTransmittance). Fog over a then over b with the same colour and density equals fog over a + b. A negative distance or density reads as no fog. Honest for a uniform medium whose in-scattered light is the constant fogCol.",
//!  "note": "The classic depth fade: sells distance, hides the far edge of a scene, and makes everything share the sky's colour. Use the ray's travel distance, not the view-space depth, or the fog wraps round the screen's corners differently. Choose k from the distance at which a scene should be half gone: k = 0.693 / halfDistance. Set fogCol to the sky colour at the horizon so the far ground meets the sky without a line, or to black for the fade-to-black of a starfield. Wrong looks like a visible line where geometry ends and sky begins (fogCol is not the horizon colour), fog that brightens nearby objects in a dark scene (fogCol brighter than the scene's light), or a fog that slides as the camera turns (depth instead of distance).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "atmos-fog.card",
//!  "twin": "arsenal/shaders/twins/atmos.py", "status": "P0", "exemplars": ["llK3Dy", "MfjyWK", "NslGRN"],
//!  "learn": ["VA 5.1"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public sources credited above.
//
// WHY. Air between the eye and a surface does two things at once: it dims the surface (Beer's law) and it adds its own
// glow of scattered light. With uniform air both follow the same exponential, so the surface simply fades toward the
// air's colour with distance. That one line is what makes a scene look deep.

// The surface colour seen through `dist` of uniform fog of density k and colour fogCol.
vec3 fogExp(vec3 col, vec3 fogCol, float dist, float k) {
    return mix(fogCol, col, volTransmittance(max(k, 0.0), max(dist, 0.0)));
}
