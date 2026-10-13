//! {"name": "noise-value", "kind": "helper", "cat": "B1", "family": "B", "version": "1.1.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Ken Perlin, 'Improving Noise' (SIGGRAPH 2002, https://mrl.cs.nyu.edu/~perlin/paper445.pdf): the quintic fade, flat in slope and curvature at both ends",
//!   "Inigo Quilez, 'Value noise derivatives' (https://iquilezles.org/articles/morenoise/): value noise as a polynomial in the fade weights",
//!   "Mark Jarzynski and Marc Olano (https://jcgt.org/published/0009/03/02/): hashing the lattice corner with a native multi-lane integer hash"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0, "hashes": "4 pcg3d (2D) or 8 pcg4d (3D)"},
//!  "contract": "Signed value noise: a random value in [-1, 1) at every lattice corner (2D: pcg3d of (cell, seed ^ 0x03707344); 3D: pcg4d of (cell, seed ^ 0xA4093822)), blended by the quintic fade 6t^5 - 15t^4 + 10t^3. Equal to its corner value on the lattice, always within [-1, 1), mean 0. One seed is one independent field, also across kinds: the tag in the seed lane keeps value noise off the dice of gradient noise and of the hash wrappers at the same seed (measured |r| < 0.05). Honest while |p| < 2^24 (beyond that a 32-bit float cannot hold the fraction inside a cell).",
//!  "note": "The cheapest lattice noise and the softest: rounded blobs with a lot of low-frequency energy, which is right for fog and clouds evaluated hundreds of times a pixel, and wrong for anything that is looked at closely, where faint plus signs and diamonds aligned to the axes show through (use noise-gradient, or rotate octaves in an fBm). Remap to 0..1 with 0.5 + 0.5 * n. Wrong looks like a visible square grid (a cubic fade, or no fade), blocky tiles (mediump), or two seeds giving the same field.",
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "noise-value.card",
//!  "twin": "arsenal/shaders/twins/noise.py", "status": "P0",
//!  "exemplars": ["4slGWM", "MdX3zr", "MsjfRG", "WlVyRV", "llK3Dy", "tsScDG"],
//!  "learn": ["NP 3"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. Put a random value on every crossing of a grid, then fill each square between its four corners with a smooth
// blend: that is value noise, the "random but smooth" field under clouds and fog. The blend's curve is what keeps the
// grid hidden: the quintic fade arrives at each corner flat in both slope and curvature, like a train that brakes
// smoothly instead of hitting the buffers, so neither the field nor its shading shows a crease at the cell edges.
//
// THE TAG. Value noise, gradient noise and the hash wrappers all roll pcg3d and pcg4d, so each kind XORs its own tag
// into the seed lane, like two radio stations on one band given different channels. Without it, value noise at seed 0
// read exactly the dice of hash31 at z = 0, and each corner's sign was the y sign of gradient noise's slope there. The
// tags are words of pi's fraction; the twin (arsenal/shaders/twins/noise.py) holds the same numbers.

// Signed 2D value noise in [-1, 1).
float noiseValue2(vec2 p, uint seed) {
    uint stream = seed ^ 0x03707344u;                   // value noise's own dice (see THE TAG)
    vec2 inCell = p - floor(p);                         // where p sits inside its cell, 0..1 per axis
    uvec2 cell = cellU2(p);
    float c00 = 2.0 * u01(pcg3d(uvec3(cell, stream)).x) - 1.0;
    float c10 = 2.0 * u01(pcg3d(uvec3(cell + uvec2(1u, 0u), stream)).x) - 1.0;
    float c01 = 2.0 * u01(pcg3d(uvec3(cell + uvec2(0u, 1u), stream)).x) - 1.0;
    float c11 = 2.0 * u01(pcg3d(uvec3(cell + uvec2(1u, 1u), stream)).x) - 1.0;
    vec2 ease = inCell * inCell * inCell * (inCell * (inCell * 6.0 - 15.0) + 10.0);   // the quintic fade
    return mix(mix(c00, c10, ease.x), mix(c01, c11, ease.x), ease.y);
}

// Signed 3D value noise in [-1, 1): eight corners, each hashed with the tagged seed as a fourth lane.
float noiseValue3(vec3 p, uint seed) {
    uint stream = seed ^ 0xA4093822u;                   // 3D value noise's own dice
    vec3 inCell = p - floor(p);
    uvec3 cell = cellU3(p);
    float c000 = 2.0 * u01(pcg4d(uvec4(cell, stream)).x) - 1.0;
    float c100 = 2.0 * u01(pcg4d(uvec4(cell + uvec3(1u, 0u, 0u), stream)).x) - 1.0;
    float c010 = 2.0 * u01(pcg4d(uvec4(cell + uvec3(0u, 1u, 0u), stream)).x) - 1.0;
    float c110 = 2.0 * u01(pcg4d(uvec4(cell + uvec3(1u, 1u, 0u), stream)).x) - 1.0;
    float c001 = 2.0 * u01(pcg4d(uvec4(cell + uvec3(0u, 0u, 1u), stream)).x) - 1.0;
    float c101 = 2.0 * u01(pcg4d(uvec4(cell + uvec3(1u, 0u, 1u), stream)).x) - 1.0;
    float c011 = 2.0 * u01(pcg4d(uvec4(cell + uvec3(0u, 1u, 1u), stream)).x) - 1.0;
    float c111 = 2.0 * u01(pcg4d(uvec4(cell + uvec3(1u, 1u, 1u), stream)).x) - 1.0;
    vec3 ease = inCell * inCell * inCell * (inCell * (inCell * 6.0 - 15.0) + 10.0);
    float near = mix(mix(c000, c100, ease.x), mix(c010, c110, ease.x), ease.y);
    float far = mix(mix(c001, c101, ease.x), mix(c011, c111, ease.x), ease.y);
    return mix(near, far, ease.z);
}
