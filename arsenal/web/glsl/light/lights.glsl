//! {"name": "light-lights", "kind": "helper", "cat": "F4", "family": "F", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Brian Karis, 'Real Shading in Unreal Engine 4' (SIGGRAPH 2013 course notes, https://blog.selfshadow.com/publications/s2013-shading-course/karis/s2013_pbs_epic_notes_v2.pdf): the windowed inverse square",
//!   "Romain Guy and Mathias Agopian, 'Physically Based Rendering in Filament', section on punctual lights (https://google.github.io/filament/Filament.html): the 1 cm floor under d^2"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "litInverseSquare(dist, radius) = clamp(1 - (d / r)^4, 0, 1)^2 / max(d^2, 0.01^2) with d = max(dist, 0) and r floored at 1e-6, in scene units: within 1 per cent of plain 1/d^2 out to a quarter of the radius, falling smoothly to exactly 0 at the radius and staying 0 beyond, monotone, and finite at the light itself (1e4 at d = 0). It is irradiance per unit of light intensity; multiply by the cosine at the receiver (litLambert) and the light's colour.",
//!  "note": "A point light's energy spreads over a sphere that grows with the square of the distance, so it falls as 1/d^2. Real light never stops, but a shader wants each light to end somewhere (so it can be skipped, and so a pool does not leak across the whole scene): the window bends the curve to zero at the radius without a visible edge. The floor under d^2 (one centimetre if the scene is in metres) keeps a light that touches a surface from becoming infinite. Pick the radius where the light has become negligible against the others; a cosine on a floor makes the pool fall as 1/r^3 (Apollonian's tighter pool). Wrong looks like a hard circular edge (a linear window or a cutoff), a pool that keeps glowing faintly across the scene (no window), or a white-hot speck where a light touches a surface (no floor).",
//!  "targets": {"glsl": "100", "needs": []}, "card": "light-lights.card",
//!  "twin": "arsenal/shaders/twins/light.py", "status": "P0",
//!  "exemplars": ["WlVyRV", "7d2fDW", "tsScDG"],
//!  "learn": ["LM 6.1", "LM 6.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published formulas (credits above).
//
// WHY. A bulb's light is a balloon being blown up: the same rubber spread over a sphere four times bigger each time
// the radius doubles. The window is a fader at the end of the cable run, easing the level to silence by the radius so
// the light can be culled there without anyone hearing the cut.

// Windowed inverse-square falloff; reaches exactly zero at radius.
float litInverseSquare(float dist, float radius) {
    float d = max(dist, 0.0);
    float ofReach = d / max(radius, 1e-6);
    float reach2 = ofReach * ofReach;
    float window = clamp(1.0 - reach2 * reach2, 0.0, 1.0);
    float spreadArea = max(d * d, 1e-4);
    return window * window / spreadArea;
}
