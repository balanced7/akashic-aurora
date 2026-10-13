//! {"name": "hash-pcg", "kind": "helper", "cat": "A6", "family": "A", "version": "1.1.0", "order": 10,
//!  "license": "Apache-2.0",
//!  "credits": ["Mark Jarzynski and Marc Olano, 'Hash Functions for GPU Rendering', JCGT 9(3), 2020 (https://jcgt.org/published/0009/03/02/): pcg3d, pcg4d and the one-lane pcg hash, and the finding that native multi-lane hashes beat sums of coordinates; written fresh from the paper's description",
//!   "Melissa O'Neill, PCG (https://www.pcg-random.org/): the permuted output stage (a shift chosen by the top bits, a multiply, a fold) that hides an LCG's weak low bits",
//!   "Nathan Reed, 'Hash Functions for GPU Rendering' (https://www.reedbeta.com/blog/hash-functions-for-gpu-rendering/): PCG as the default one-in-one-out GPU hash"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Bit-exact on every GPU (32-bit unsigned arithmetic only). hashU1 is a bijection on 32 bits with full avalanche: one flipped input bit flips about half the output bits. pcg3d and pcg4d give that avalanche across all their output bits for the low 17 bits of every input lane (lattice ids and seeds live there); the high input bits mix less (bit 31 reaches about a quarter), so a seed that varies only in its high bits is pre-hashed with hashU1. u01 keeps the top 24 bits over 2^24: exact in a float, in [0, 1), never 1.0. cellU2/cellU3 floor and reinterpret, wrapping negative cells by two's complement; honest while |p| < 2^31. hash21, hash22, hash31 and hash33 are [0, 1) per cell of p, constant across the cell; the 2D ones put a fixed tag (0x9E3779B9) in the third lane and the 3D ones XOR a tag (0xEC4E6C89) into the z lane, so the wrappers never repeat each other's dice, nor those of value or gradient noise (which tag their seed lanes) nor of a direct pcg3d call with a small third lane, for any seed or cell z of magnitude below 2^16.",
//!  "note": "The house dice: reach for hash33 when a cell needs three independent decisions (one hash, three dice: size, type, phase), for pcg3d/pcg4d with a seed lane when a lattice needs streams, and for hashU1 to scramble a seed. Never sum coordinates into a one-lane hash (x + 57y patterns repeat), never feed a growing clock into a hash (wrap time on the host), never derive more randoms by nudging the input of a weak hash. Wrong looks like stripes, diagonal moire or repeating tiles in what should be grain, or a pattern that differs between two machines (a float hash, not this one).",
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "hash-pcg.card",
//!  "twin": "arsenal/shaders/twins/hash.py", "status": "P0", "exemplars": ["cs2GWD", "lfscD7"],
//!  "learn": ["NP 2.3", "NP 2.4", "NP 15.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. A GPU paints millions of pixels at once and pixel 1000 cannot wait for pixel 999, so a shader does not draw
// random numbers from a sequence: it HASHES an address (a pixel, a lattice corner, a seed) straight to a number. A
// good hash works like the bank-scrambling in a DRAM controller: neighbouring addresses land in unrelated places, or
// the picture shows stripes. The house hashes in 32-bit unsigned integers, so every GPU computes the same bits; the old
// fract(sin(...)) hash lives on only as a legacy twin (legacy/hash-sine.glsl) for surfaces that must not move a pixel.

// One word in, one word out. One step of PCG's 32-bit LCG, then its output permutation: a right shift whose size the
// top four bits choose, a multiply, and a fold of the high half down. Every output bit depends on every input bit.
uint hashU1(uint x) {
    uint lcg = x * 747796405u + 2891336453u;
    uint shift = (lcg >> 28u) + 4u;
    uint mixed = ((lcg >> shift) ^ lcg) * 277803737u;
    return (mixed >> 22u) ^ mixed;
}

// Three lanes in, three out (Jarzynski and Olano's pcg3d): an LCG step on every lane, then each lane adds the product
// of the other two, the high halves fold into the low ones, and the lanes cross-multiply once more. A miniature
// Feistel cipher: the same family as real block ciphers, cut down to a few multiply-adds.
uvec3 pcg3d(uvec3 v) {
    uvec3 lane = v * 1664525u + 1013904223u;
    lane.x += lane.y * lane.z;
    lane.y += lane.z * lane.x;
    lane.z += lane.x * lane.y;
    lane ^= lane >> 16u;                                   // multiplies push information up; this brings it down
    lane.x += lane.y * lane.z;
    lane.y += lane.z * lane.x;
    lane.z += lane.x * lane.y;
    return lane;
}

// Four lanes in, four out: the same recipe with the cyclic four-lane mix (x takes y times w). Use it for
// (x, y, z, seed) lattice corners or (x, y, frame, seed).
uvec4 pcg4d(uvec4 v) {
    uvec4 lane = v * 1664525u + 1013904223u;
    lane.x += lane.y * lane.w;
    lane.y += lane.z * lane.x;
    lane.z += lane.x * lane.y;
    lane.w += lane.y * lane.z;
    lane ^= lane >> 16u;
    lane.x += lane.y * lane.w;
    lane.y += lane.z * lane.x;
    lane.z += lane.x * lane.y;
    lane.w += lane.y * lane.z;
    return lane;
}

// A word as a float in [0, 1): the top 24 bits over 2^24, which a 32-bit float holds exactly. (All 32 bits over 2^32
// would round the largest words up to exactly 1.0, a quiet bug when the result indexes anything.)
float u01(uint x) { return float(x >> 8u) * (1.0 / 16777216.0); }
vec2 u01(uvec2 x) { return vec2(x >> 8u) * (1.0 / 16777216.0); }
vec3 u01(uvec3 x) { return vec3(x >> 8u) * (1.0 / 16777216.0); }
vec4 u01(uvec4 x) { return vec4(x >> 8u) * (1.0 / 16777216.0); }

// The integer cell a point lies in, as unsigned lanes: -1 becomes 0xFFFFFFFF, so negative cells hash like any other.
uvec2 cellU2(vec2 p) { return uvec2(ivec2(floor(p))); }
uvec3 cellU3(vec3 p) { return uvec3(ivec3(floor(p))); }

// Float-facing wrappers: [0, 1) for the cell of p. hash33 is three independent dice for one cell; hash31 is its .x.
// Each wrapper family keeps to its own lanes: the 2D ones hold the golden-ratio word as their whole third lane, the 3D
// ones XOR a word of pi's fraction into z. Untagged lanes are left to direct callers of pcg3d and pcg4d (a star field
// hashing (cell, 0u) does not draw the same stars as hash33 of (cell, 0.0)), and the noises tag their seed lanes.
float hash21(vec2 at) {
    uvec3 dice = pcg3d(uvec3(cellU2(at), 0x9E3779B9u));
    return u01(dice.x);
}

vec2 hash22(vec2 at) {
    uvec3 dice = pcg3d(uvec3(cellU2(at), 0x9E3779B9u));
    return u01(dice.xy);
}

float hash31(vec3 at) {
    uvec3 dice = pcg3d(cellU3(at) ^ uvec3(0u, 0u, 0xEC4E6C89u));
    return u01(dice.x);
}

vec3 hash33(vec3 at) {
    uvec3 dice = pcg3d(cellU3(at) ^ uvec3(0u, 0u, 0xEC4E6C89u));
    return u01(dice);
}
