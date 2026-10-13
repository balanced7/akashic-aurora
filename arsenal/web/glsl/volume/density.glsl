//! {"name": "volume-density", "kind": "helper", "cat": "G4", "family": "G", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'distance functions' (https://iquilezles.org/articles/distfunctions/): the signed distance fields this turns into fog",
//!   "Andrew Schneider, 'Nubis Cubed' (SIGGRAPH 2023 Advances in Real-Time Rendering, https://advances.realtimerendering.com/s2023/): a cloud's dimensional profile made from the signed distance of its shape"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "densFromSDF(sdf, softness) is clamp(-sdf / softness, 0, 1): exactly 0 on and outside the surface (sdf >= 0), rising in a straight line to 1 at depth `softness` inside, and 1 deeper in. softness 0 is a hard edge (read as 1e-6). Honest for any signed distance, exact or not; a field that overestimates distance only shifts where the ramp sits.",
//!  "note": "Every distance-field modelling tool becomes a fog-modelling tool: build the shape with SDFs (spheres, boxes, smooth unions, displacement) and read it as density, then scale by an extinction and march it with volStepScatter. Softness is the depth of the cloud's soft skin: small for a crisp puff, large for a haze with a dense core. Add noise to the distance before this (not after) to erode the edges while the core stays dense. Wrong looks like a hard shell where a soft skin was meant (softness near zero), a grey haze with no core (softness larger than the shape), or density outside the shape (the sign of the distance flipped).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "volume-density.card",
//!  "twin": "arsenal/shaders/twins/volume.py", "status": "P0", "exemplars": ["tsScDG"],
//!  "learn": ["VA 2.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public sources credited above.
//
// WHY. A signed distance field says how far a point is from a shape's surface, negative inside. Read that depth as
// thickness of fog and a solid becomes a cloud with a soft skin: the density ramps up over the first `softness` of
// depth and holds at one in the core.

// Density from a signed distance: 0 outside, a straight ramp over the first `softness` of depth, 1 deeper in.
float densFromSDF(float sdf, float softness) {
    return clamp(-sdf / max(softness, 1e-6), 0.0, 1.0);
}
