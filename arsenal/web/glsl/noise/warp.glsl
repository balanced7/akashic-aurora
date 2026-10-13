//! {"name": "noise-warp", "kind": "helper", "cat": "B4", "family": "B", "version": "1.0.0", "order": 28,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'Domain Warping' (https://iquilezles.org/articles/warp/): f(p + h(p)) with h built from fBm, nested twice, and the intermediate fields as colour",
//!   "F. Kenton Musgrave, domain distortion in 'Procedural Fractal Terrains' (https://www.classes.cs.uchicago.edu/archive/2015/fall/23700-1/final-project/MusgraveTerrain00.pdf): fBm distorted by fBm"],
//!  "cost": {"class": "C1", "loop": "octaves <= 8 per fBm", "tex": 0, "fbm_calls": "warpVec2 2, warpFbm2 3, warpNested2 5"},
//!  "contract": "warpVec2 is a displacement whose two components are fBm of gradient noise (lacunarity 2, gain 0.5) read at far-apart points and hashed with unrelated streams (hashU1 of the seed and a tag), so they are decorrelated; each lies within [-1, 1], mostly within +-0.5. warpFbm2 is fbm(p + amount * warpVec2(p)); warpNested2 is fbm(p + amount * r) with r = warpVec2(p + amount * q) on seed + 1 and q = warpVec2(p), returning q and r for colouring. Both results lie within [-1, 1]; amount 0 gives the plain fBm of the final stream. Honest while amount * octaves stays moderate: a strong warp squeezes space, raising the effective frequency until the fine octaves alias into threads.",
//!  "note": "Bend the address before the lookup, like a crooked address bus in front of an ordinary memory: marble, smoke, gas giants, flowing paint. q and r are free colour data (how far and which way the fabric moved): mix a palette by length(q) and by r.x for the lush, layered look. Animate by sliding the inner level only (add a slow vector to p before warpVec2) and let the outer level carry the motion. Use fewer octaves inside than outside. Wrong looks like stretched glittering threads along the flow (too much amount for the octave count), or a plain fBm with a tilt (both components correlated: one stream fed to both).",
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "noise-warp.card",
//!  "twin": "arsenal/shaders/twins/noise.py", "status": "P0",
//!  "exemplars": ["4s23zz", "4slGWM", "MdBfzR", "MsjfRG"],
//!  "learn": ["NP 8"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. Instead of reading the fabric at p, read it at p pushed sideways by another fabric. The memory (the fBm) is
// ordinary; the crookedness comes from the address. Do it twice, each push made from the last, and straight bands curl
// into marble and smoke. Every fBm here hashes with its own stream, made from the caller's seed by hashU1 and a tag
// (the tags are the first fractional bits of pi, chosen only to be unrelated), so the two components of a push are
// independent: one stream fed to both would push only along a diagonal.

// A 2D push: two decorrelated fBm, read at far-apart points.
vec2 warpVec2(vec2 p, int octaves, uint seed) {
    return vec2(fbmGrad2(p, octaves, 2.0, 0.5, hashU1(seed ^ 0x243F6A88u)),
                fbmGrad2(p + vec2(57.3, -21.9), octaves, 2.0, 0.5, hashU1(seed ^ 0x85A308D3u)));
}

// One level of warp: the fabric read at p pushed by amount * warpVec2(p). Three fBm calls.
float warpFbm2(vec2 p, float amount, int octaves, uint seed) {
    vec2 push = warpVec2(p, octaves, seed);
    return fbmGrad2(p + amount * push, octaves, 2.0, 0.5, hashU1(seed ^ 0x13198A2Eu));
}

// Two nested levels: q pushes the second push r, and r pushes the final read. Five fBm calls. q and r come back for
// colouring.
float warpNested2(vec2 p, float amount, int octaves, uint seed, out vec2 q, out vec2 r) {
    q = warpVec2(p, octaves, seed);
    r = warpVec2(p + amount * q, octaves, seed + 1u);
    return fbmGrad2(p + amount * r, octaves, 2.0, 0.5, hashU1(seed ^ 0x13198A2Eu));
}
