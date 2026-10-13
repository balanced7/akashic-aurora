//! {"name": "draw2-lattice", "kind": "helper", "cat": "C5", "family": "C", "version": "1.0.0", "order": 22,
//!  "license": "Apache-2.0",
//!  "credits": ["Martijn Steinrucken (The Art of Code), 'Hexagonal Tiling Explained' (https://www.youtube.com/watch?v=VmrIDyYiJBA): hex centres as two interleaved rectangular grids, keep the nearer",
//!   "Amit Patel, Red Blob Games, 'Hexagonal Grids' (https://www.redblobgames.com/grids/hexagons/): axial and cube coordinates, hex distance as the largest cube difference"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "latHex(p) tiles the plane with pointy-top regular hexagons whose centres are 1 apart (rows sqrt 3 / 2 apart, alternate rows shifted by 1/2; inradius 1/2): xy is p's offset from the nearest centre, zw that centre, constant over the cell and unique to it (offset + centre = p; on an exact border the first grid wins). latHexEdge(offset) is 0.5 - max(|x|, |x| / 2 + sqrt 3 / 2 |y|): the Euclidean distance to the cell's border, 0.5 at the centre and 0 on the border, equal to -sd2Hexagon(offset, 0.5). latHexAxial(centre) is the integer pair (q, r) with centre = q (1, 0) + r (1/2, sqrt 3 / 2): one pair per cell, whole numbers safe to hash. latHexSteps(a, b) is the number of hex steps between two axial pairs, max(|dq|, |dr|, |dq + dr|). Honest while |p| < 2^22 (the centre needs the fraction).",
//!  "note": "The honeycomb under the hex-neon group, piano harmony floors and the bench's hex-grid chunk (whose own edge measure draws chevrons, PF 15.1). Draw a shape about the origin with the offset, colour or time it from the centre: hash latHexAxial(centre), never the raw centre (two centres of different rows can share a floor()), and never a derivative of either (they jump between cells). latHexEdge is a true distance in lattice units, so lines of constant pixel width are aaStroke(latHexEdge(offset), w, px) with px from the unwarped coordinate. A shape bigger than its cell gets cut at the border: evaluate the six neighbours too. Wrong looks like flat-top hexagons or squashed ones (a stretch on x, the chunk's 1.1547), chevrons instead of outlines (an asymmetric edge measure), cells sharing a colour across a row (a floored centre hashed), or a tile that changes inside itself (an id from the rectangular grid).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "draw2-lattice.card",
//!  "twin": "arsenal/shaders/twins/draw2.py", "status": "P0",
//!  "exemplars": ["wsl3WB", "NlK3Wt", "lfscD7"],
//!  "learn": ["PF 6.4"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. Hexagons tile with every neighbour the same distance away, which a square grid cannot do (its diagonal
// neighbours are 41 percent farther), so waves, rings and per-cell timings spread evenly in every direction. The
// centres form two rectangular grids of size 1 by sqrt 3, one shifted by half a cell in both directions: find the
// nearest centre in each with plain rounding and keep the nearer. No branches on cell shapes, no trigonometry.

// (offset from the nearest hex centre, that centre) for pointy-top hexagons with centres 1 apart.
vec4 latHex(vec2 p) {
    const vec2 cellSize = vec2(1.0, SQRT3);             // one cell of each rectangular grid
    const vec2 shift = vec2(0.5, 0.5 * SQRT3);           // where the second grid's centres sit
    vec2 centreA = cellSize * floor(p / cellSize + 0.5);
    vec2 centreB = cellSize * floor((p - shift) / cellSize + 0.5) + shift;
    vec2 offA = p - centreA;
    vec2 offB = p - centreB;
    return dot(offA, offA) <= dot(offB, offB) ? vec4(offA, centreA) : vec4(offB, centreB);
}

// The distance from a hex offset to its cell's border. Of the three pairs of sides, the one p faces most squarely is
// nearest: their normals are (1, 0) and (1/2, +-sqrt 3 / 2), and the inradius is 1/2.
float latHexEdge(vec2 offset) {
    vec2 o = abs(offset);
    float hexNorm = max(o.x, 0.5 * o.x + 0.5 * SQRT3 * o.y);
    return 0.5 - hexNorm;
}

// The integer axial coordinates of a hex centre: how many steps along (1, 0) and along (1/2, sqrt 3 / 2).
vec2 latHexAxial(vec2 centre) {
    float r = centre.y * (2.0 / SQRT3);
    float q = centre.x - 0.5 * r;
    return floor(vec2(q, r) + 0.5);
}

// Hex steps between two cells given by axial pairs: the third cube coordinate is -(q + r), and the distance is the
// largest of the three differences.
float latHexSteps(vec2 a, vec2 b) {
    vec2 d = b - a;
    return max(max(abs(d.x), abs(d.y)), abs(d.x + d.y));
}
