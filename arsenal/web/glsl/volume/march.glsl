//! {"name": "volume-march", "kind": "helper", "cat": "G5", "family": "G", "version": "1.0.0", "order": 22,
//!  "license": "Apache-2.0",
//!  "credits": ["nimitz, 'Auroras' (https://www.shadertoy.com/view/XtGGRt) and Valdex's Chromatic Aurora Curtains (https://www.shadertoy.com/view/ffG3Rc): sheets spaced by a power of their index, dense at the bright hem",
//!   "Inigo Quilez, 'directional derivative' (https://iquilezles.org/articles/derivative/), and nimitz's Cloud Ten (https://www.shadertoy.com/view/XtS3DD): one density probe toward the sun, with a floor so shadows never go black"],
//!  "cost": {"class": "C0", "loop": "none (one call per layer or per sample)", "tex": 0, "hooks": 1},
//!  "hooks": ["float densityAt(vec3 p)"],
//!  "contract": "marchStepPoly(i, base, scale, power) is base + scale * i^power for power > 0: layer 0 sits at base, a negative i reads as 0, and the gaps grow with i when power > 1. volLightOneTap(p, toLight, dist, floorShadow) is the light's visibility from p in [floorShadow, 1]: mix(floorShadow, 1, exp(-sigma * dist)), where sigma is ONE call of the host's densityAt at the midpoint p + 0.5 * dist * toLight (the midpoint rule, exact when the extinction varies linearly along the probe; a negative density reads as 0). The host defines float densityAt(vec3 p), the extinction per unit length at p; toLight is a unit vector and dist >= 0. Composing this module obliges the host to define densityAt even when it calls only marchStepPoly: WebGL (ANGLE) refuses a program in which a defined function calls an undefined one (measured on SwiftShader, 2026-10-13), so a host with no volume defines float densityAt(vec3 p) { return 0.0; }.",
//!  "note": "Two ways to spend fewer samples. marchStepPoly spaces a stack of aurora sheets (or any layered volume) densely where the subject is bright and sharp and sparsely where it is faint: power about 1.3 to 1.4 puts the detail at the hem. volLightOneTap is the cheapest self-shadow there is: one extra density sample per march step gives lit tops and shaded lee slopes, and the floor (about 0.15) stands in for the light that real clouds scatter in from everywhere else, so shadows never go black. The probe length sets the shadow's softness and reach. It is not a light march: thin shapes far from p cast no shadow, and long probes miss detail (use volLightMarch for that). Wrong looks like sheets bunched at the top (power below 1), black shadow cores (floor 0), or shadows on the sunny side (toLight pointing away from the light).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "volume-march.card",
//!  "twin": "arsenal/shaders/twins/volume.py", "status": "P0", "exemplars": ["ffG3Rc", "XtS3DD"],
//!  "learn": ["VA 7.2 family B", "study:XtS3DD 6.6"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public sources credited above.
//
// WHY. A march's cost is its sample count, so the craft is putting the samples where the eye looks. An aurora is
// brightest and sharpest at its hem, so its sheets crowd there; a cloud's shading needs to know how much stuff lies
// toward the sun, and one well-placed probe (the middle of the stretch it stands for) says most of it.

// Where layer i sits when the spacing grows as a power of the index: dense near base, sparse far from it.
float marchStepPoly(int i, float base, float scale, float power) {
    float k = max(float(i), 0.0);
    return base + scale * (k > 0.0 ? pow(k, power) : 0.0);
}

// How much of the light reaches p, from one density probe halfway along `dist` toward it, never below floorShadow.
float volLightOneTap(vec3 p, vec3 toLight, float dist, float floorShadow) {
    float reach = max(dist, 0.0);
    float sigma = max(densityAt(p + (0.5 * reach) * toLight), 0.0);
    return mix(floorShadow, 1.0, volTransmittance(sigma, reach));
}
