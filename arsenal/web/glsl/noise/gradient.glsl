//! {"name": "noise-gradient", "kind": "helper", "cat": "B1", "family": "B", "version": "1.1.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Ken Perlin, 'An Image Synthesizer' (SIGGRAPH 1985) and 'Improving Noise' (SIGGRAPH 2002, https://mrl.cs.nyu.edu/~perlin/paper445.pdf): gradient noise, the quintic fade and the twelve cube-edge gradients",
//!   "Stefan Gustavson, 'Simplex noise demystified' (https://weber.itn.liu.se/~stegu/simplexnoise/simplexnoise.pdf): the plain-words account of the gradient lattice",
//!   "Mark Jarzynski and Marc Olano (https://jcgt.org/published/0009/03/02/): integer hashing of the lattice corners"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0, "hashes": "4 pcg3d (2D) or 8 pcg4d (3D)"},
//!  "contract": "Improved Perlin gradient noise: every lattice corner holds a gradient (2D: one of eight unit vectors at 22.5 + 45k degrees, chosen by the top three bits of pcg3d(cell, seed ^ 0x299F31D0).x; 3D: one of Perlin's twelve cube-edge vectors, chosen by pcg4d(cell, seed ^ 0x082EFA98).x mod 12), each corner contributes the ramp gradient . (p - corner), and the ramps blend by the quintic fade. Exactly zero on every lattice point; within [-1, 1] (the scales put the exact supremum at 0.99995 in 2D and 0.99997 in 3D); mean 0. One seed is one independent field, also across kinds: the tag in the seed lane keeps it off the dice of value noise and of the hash wrappers at the same seed (measured |r| < 0.05). Honest while |p| < 2^24.",
//!  "note": "The default lattice noise when the field is looked at: zero crossings on every lattice point pull the low-frequency drift out, so it reads sharper and more varied than value noise, closer to one octave of energy. It is the basis of noise-fbm and noise-warp. The grid is still faintly there (every lattice point is a zero), so stack octaves with a turn between them. Wrong looks like a visible pinch at the origin of an fBm (octaves not stepped off the lattice), faceted highlights on a displaced surface (a cubic fade), or splotches of extra-high values (a clumping gradient set).",
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "noise-gradient.card",
//!  "twin": "arsenal/shaders/twins/noise.py", "status": "P0", "exemplars": ["ttScDc"],
//!  "learn": ["NP 4"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. Value noise stores a random HEIGHT at every grid crossing; gradient noise stores a random SLOPE. Each corner
// lays down a tilted plane that passes through zero at the corner itself, and the quintic fade blends the four (or
// eight) planes. Because the field is pinned to zero at every crossing it cannot drift into broad bright or dark
// blobs, so it looks crisper, like a speaker whose bass roll-off keeps the mix from getting muddy.
//
// THE TAG. noiseGrad2 and noiseGrad3 XOR their own tag into the seed lane before any corner is hashed (value noise
// and the hash wrappers hold others), so one seed never hands two kinds the same dice: before the tags, a value-noise
// corner's sign was the y sign of the gradient chosen at the same corner. The twin holds the same two numbers.

// One corner's ramp in 2D: the gradient of the cell's corner (0 or 1 on each axis) dotted with the offset from that
// corner. The gradient is one of eight unit vectors at 22.5 + 45k degrees (never on an axis or a diagonal): bit 29
// swaps the long and short component, bit 30 flips x, bit 31 flips y. `stream` is the seed already tagged.
float noiseGradRamp2(uvec2 cell, uvec2 corner, uint stream, vec2 inCell) {
    uint word = pcg3d(uvec3(cell + corner, stream)).x;
    vec2 offset = inCell - vec2(corner);
    vec2 g = ((word >> 29u) & 1u) == 0u ? vec2(0.92387953, 0.38268343) : vec2(0.38268343, 0.92387953);
    g.x = ((word >> 30u) & 1u) == 0u ? g.x : -g.x;
    g.y = (word >> 31u) == 0u ? g.y : -g.y;
    return dot(g, offset);
}

// Improved gradient noise in 2D, within [-1, 1].
float noiseGrad2(vec2 p, uint seed) {
    uint stream = seed ^ 0x299F31D0u;                   // gradient noise's own dice (see THE TAG)
    vec2 inCell = p - floor(p);                         // where p sits inside its cell, 0..1 per axis
    uvec2 cell = cellU2(p);
    float ramp00 = noiseGradRamp2(cell, uvec2(0u, 0u), stream, inCell);
    float ramp10 = noiseGradRamp2(cell, uvec2(1u, 0u), stream, inCell);
    float ramp01 = noiseGradRamp2(cell, uvec2(0u, 1u), stream, inCell);
    float ramp11 = noiseGradRamp2(cell, uvec2(1u, 1u), stream, inCell);
    vec2 ease = inCell * inCell * inCell * (inCell * (inCell * 6.0 - 15.0) + 10.0);   // the quintic fade
    return 1.5132 * mix(mix(ramp00, ramp10, ease.x), mix(ramp01, ramp11, ease.x), ease.y);
}

// One corner's ramp in 3D: the corner's gradient is one of Perlin's twelve cube-edge vectors, (+-1, +-1, 0) and its
// permutations, numbered k = hash mod 12: k / 4 names the plane the gradient lies in (xy, xz or yz), bits 0 and 1 its
// two signs. A dot product with such a vector is one signed add, no multiply. `stream` is the seed already tagged.
float noiseGradRamp3(uvec3 cell, uvec3 corner, uint stream, vec3 inCell) {
    uint k = pcg4d(uvec4(cell + corner, stream)).x % 12u;
    vec3 offset = inCell - vec3(corner);
    uint plane = k >> 2u;
    float a = plane == 2u ? offset.y : offset.x;
    float b = plane == 0u ? offset.y : offset.z;
    return ((k & 1u) == 0u ? a : -a) + ((k & 2u) == 0u ? b : -b);
}

// Improved gradient noise in 3D, within [-1, 1].
float noiseGrad3(vec3 p, uint seed) {
    uint stream = seed ^ 0x082EFA98u;                   // 3D gradient noise's own dice
    vec3 inCell = p - floor(p);
    uvec3 cell = cellU3(p);
    float ramp000 = noiseGradRamp3(cell, uvec3(0u, 0u, 0u), stream, inCell);
    float ramp100 = noiseGradRamp3(cell, uvec3(1u, 0u, 0u), stream, inCell);
    float ramp010 = noiseGradRamp3(cell, uvec3(0u, 1u, 0u), stream, inCell);
    float ramp110 = noiseGradRamp3(cell, uvec3(1u, 1u, 0u), stream, inCell);
    float ramp001 = noiseGradRamp3(cell, uvec3(0u, 0u, 1u), stream, inCell);
    float ramp101 = noiseGradRamp3(cell, uvec3(1u, 0u, 1u), stream, inCell);
    float ramp011 = noiseGradRamp3(cell, uvec3(0u, 1u, 1u), stream, inCell);
    float ramp111 = noiseGradRamp3(cell, uvec3(1u, 1u, 1u), stream, inCell);
    vec3 ease = inCell * inCell * inCell * (inCell * (inCell * 6.0 - 15.0) + 10.0);
    float near = mix(mix(ramp000, ramp100, ease.x), mix(ramp010, ramp110, ease.x), ease.y);
    float far = mix(mix(ramp001, ramp101, ease.x), mix(ramp011, ramp111, ease.x), ease.y);
    return 0.9649 * mix(near, far, ease.z);
}
