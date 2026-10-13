//! {"name": "light-env", "kind": "helper", "cat": "F6", "family": "F", "version": "1.0.1", "order": 24,
//!  "license": "Apache-2.0",
//!  "credits": ["mrange, 'Just a Cube' (https://www.shadertoy.com/view/3XdXRr) and 'Saturday weirdness' (https://www.shadertoy.com/view/43jXWt): an analytic studio, a soft box brighter at its rim than at its centre and a pool of light on the floor (the technique, read in words; no code taken)",
//!   "morimea, 'Cube Lines' (https://www.shadertoy.com/view/NslGRN): a floor that dissolves into the brightest band of the sky, so there is no ground edge (the technique, read in words)",
//!   "Johann Heinrich Lambert (1772; https://en.wikipedia.org/wiki/Lambert_azimuthal_equal-area_projection): the equal-area projection that keeps a blurred panel's solid angle",
//!   "the house piano studies (arsenal/web/piano-crystal-studies.js and four other copies): soft boxes baked into a reflection map, and a Gaussian floor halo"],
//!  "cost": {"class": "C0", "loop": "none (two soft boxes, each a few dot products and one pow)", "tex": 0},
//!  "contract": "StudioParams holds one studio, shared by litStudioEnv (what reflections see) and rigStudio (what lights the diffuse), so an object's lighting always matches its reflections. litFloorPool(p, centre, radius, col) = col * exp(-|p.xz - centre.xz|^2 / radius^2) (radius floored at 1e-6): a Gaussian disc of light on a horizontal floor, col at the centre, col / e at the radius, under 2 per cent by twice the radius, height ignored. litStudioEnv(dir, roughness, s) is linear radiance for any direction (normalised inside; roughness clamped to [0, 1]): above the horizon a dome from horizonCol at the horizon to skyCol at about 37 degrees up; below it a floor floorDrop under the subject carrying a pool (litFloorPool, poolRadius, floorCol) and fading into horizonCol with distance, so the floor meets the dome with no edge; plus a key and a fill soft box, rounded squares (an L4 superellipse) of half-size boxSize radians around keyDir and fillDir in Lambert equal-area coordinates. At roughness 0 a box shows its colour exactly at its centre and (1 + rimBright) times it at its rim; with roughness its edge widens from 0.04 to 0.9 of its radius and its rim brightening fades away while its total light over the sphere stays constant, for any rimBright (within a few per cent): the blur's skirt is divided out exactly in the equal-area measure, and the rim's light is spread back over the panel as it fades, so a fully rough box is an even panel of (1 + rimBright / 2) times its colour. Within about 1.1 degrees of straight away from a box (0.5 + 0.5 dot(dir, boxDir) < 1e-4, where the projection is 0 / 0) that box adds nothing. Everything is finite and non-negative.",
//!  "note": "Metal and glass have no colour of their own to speak of: they show their surroundings, so in a flat grey world chrome looks like grey plastic. A studio is the cheapest world that makes them read: a near-black dome for contrast, a few large bright panels for the highlights to be windows of, a pool of light on the floor for weight, and a horizon band for the edge of every reflection. The panels widen with roughness as a crude prefilter (a rough reflection is a blurred one) and keep their energy while doing it, so a rough ball is not brighter or darker than a polished one, only softer. Real diffuser panels are hotter at their frame, which gives reflections a crisp outline; rimBright sets that. Feed it the mirror direction reflect(-v, n) and the surface's perceptual roughness (the square root of alpha). A neutral product-shot studio to start from (the one the cards and the twin use): StudioParams(normalize(vec3(-0.55, 0.75, 0.4)), vec3(3.6, 3.3, 2.9), normalize(vec3(0.65, 0.55, -0.55)), vec3(0.55, 0.7, 1.0), vec2(0.42, 0.28), 0.8, vec3(0.008, 0.01, 0.016), vec3(0.07, 0.075, 0.09), vec3(0.32, 0.27, 0.22), 1.0, 1.1, 0.3): a warm key high on the upper left, a cool fill behind on the right, a near-black dome. Wrong looks like chrome reading as plastic (a soft gradient world), a visible line where the floor meets the sky, or a box that floods the reflection as it blurs (energy not kept).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "light-env.card",
//!  "twin": "arsenal/shaders/twins/light.py", "status": "P0",
//!  "exemplars": ["3XdXRr", "43jXWt", "XdcyDM", "NslGRN"],
//!  "learn": ["LM 8.1", "LM 13.1", "study:3XdXRr 4.8", "study:3XdXRr 4.9", "study:43jXWt 4.5", "study:NslGRN T19", "arc-piano-studies F1", "arc-piano-studies F2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the techniques credited above.
//
// WHY. A product photographer does not light a chrome kettle with bare bulbs; she surrounds it with big soft boxes in
// a dark room, because the kettle will show whatever is around it. This module is that room as a function of
// direction, so every hero object in the house can stand in the same studio and every reflection agrees with the
// light that shaded the diffuse part (rigStudio reads the same StudioParams).

// One studio: two soft boxes, a dome, a horizon band and a floor with a pool of light.
struct StudioParams {
    vec3 keyDir;      // unit, toward the key soft box; also rigStudio's key light
    vec3 keyCol;      // the key panel's radiance at its centre, linear HDR
    vec3 fillDir;     // unit, toward the second, dimmer panel; rigStudio's back light
    vec3 fillCol;     // its radiance at its centre
    vec2 boxSize;     // both panels' half-size in radians (across, along), equal-area measure
    float rimBright;  // a panel's rim over its centre: 0 is a flat panel, 0.8 makes the rim 1.8 times the centre
    vec3 skyCol;      // the dome high up; rigStudio's sky fill
    vec3 horizonCol;  // the band at the horizon, where the floor dissolves; rigStudio's rim light
    vec3 floorCol;    // the pool of light on the floor straight under the subject; rigStudio's ground fill
    float floorDrop;  // the floor's depth below the subject, in scene units
    float poolRadius; // the pool's radius on the floor (where it has fallen to 1/e)
    float keyWrap;    // rigStudio's key wrap, 0 (Lambert) to 1
};


// A Gaussian disc of light on a horizontal floor (y up): col at the centre, col / e at the radius.
vec3 litFloorPool(vec3 p, vec3 centre, float radius, vec3 col) {
    vec2 fromCentre = (p.xz - centre.xz) / max(radius, 1e-6);
    return col * exp(-dot(fromCentre, fromCentre));
}

// The studio's radiance along dir, for a surface of the given perceptual roughness. Each soft box is a rounded square
// around its direction, rim-bright when sharp and widening with roughness at constant energy: its coordinates are
// Lambert's equal-area projection around the box's direction, so the blur's skirt can be paid for exactly (a
// smoothstep edge of half-width w adds 0.2 w^2 of the panel's area).
vec3 litStudioEnv(vec3 dir, float roughness, StudioParams s) {
    float blur = clamp(roughness, 0.0, 1.0);
    vec3 look = safeNormalize(dir, vec2(0.0, 1.0).xyx);                // a zero direction looks straight up
    vec3 dome = mix(s.horizonCol, s.skyCol, smoothstep(0.0, 0.6, look.y));
    float toFloor = s.floorDrop / max(-look.y, 1e-6);
    vec3 onFloor = look * toFloor;
    float haze = 1.0 - exp(-length(onFloor.xz) / (4.0 * max(s.poolRadius, 1e-6)));
    vec3 ground = s.horizonCol * haze + litFloorPool(onFloor, vec3(0.0), s.poolRadius, s.floorCol);
    vec3 panels = vec3(0.0);
    float width = mix(0.04, 0.9, blur);
    float keep = (1.0 + 0.2 * 0.04 * 0.04) / (1.0 + 0.2 * width * width);
    // the rim's extra light, 1 + rimBright (1 - blur) edge^2, averages 1 + rimBright (1 - blur) / 2 over a panel and
    // fades as the box blurs; spread it back over the panel so the total stays the sharp box's at every roughness
    float spread = (1.0 + 0.5 * s.rimBright) / (1.0 + 0.5 * s.rimBright * (1.0 - blur));
    for (int box = 0; box < 2; box++) {
        vec3 boxDir = box == 0 ? s.keyDir : s.fillDir;
        float facing = 0.5 + 0.5 * dot(look, boxDir);
        if (facing < 1e-4) {
            continue;      // straight away from the box the projection is 0 / 0 and would land on its centre
        }
        vec3 across = safeNormalize(vec3(boxDir.z, 0.0, -boxDir.x), vec3(1.0, 0.0, 0.0));   // up x boxDir: level
        vec3 along = cross(boxDir, across);
        float equalArea = inversesqrt(max(facing, 1e-6));
        vec2 onPanel = vec2(dot(look, across), dot(look, along)) * equalArea / s.boxSize;
        vec2 square = onPanel * onPanel;
        float edge = pow(max(dot(square, square), 1e-20), 0.25);      // 1 on the panel's rim
        float inside = (1.0 - smoothstep(1.0 - width, 1.0 + width, edge)) * keep;
        float frame = (1.0 + s.rimBright * (1.0 - blur) * min(edge * edge, 1.0)) * spread;
        panels += (box == 0 ? s.keyCol : s.fillCol) * (inside * frame);
    }
    vec3 base = look.y < 0.0 ? ground : dome;
    return base + panels;
}
