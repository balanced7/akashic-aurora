//! {"name": "draw2-sdf2", "kind": "helper", "cat": "C1", "family": "C", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, '2D distance functions' (https://iquilezles.org/articles/distfunctions2d/): the exact circle, box, rounded box and segment, and the habit of folding by symmetry before measuring",
//!   "Amit Patel, Red Blob Games, 'Hexagonal Grids' (https://www.redblobgames.com/grids/hexagons/): pointy-top orientation, inradius against circumradius"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Exact signed distances in the caller's units, negative inside, |gradient| = 1 everywhere off the shape's skeleton (never an overestimate, so a marcher or a glow can trust them). sd2Circle is |p| - r. sd2Box takes the half-size. sd2RoundBox keeps its outer extent at halfSize and rounds the corners by cornerRadius, held in [0, min(halfSize)]. sd2Segment returns (distance, parameter): the parameter runs 0 at a to 1 at b, held at the ends; a segment of zero length is its point, parameter 0. sd2Hexagon is the pointy-top hexagon of the given inradius (flat sides at x = +-inradius, vertices straight up and down at 2 inradius / sqrt 3), the orientation of latHex. Honest for |p| below about 1e18 (beyond that dot products overflow).",
//!  "note": "One number per pixel buys the fill, an outline of any width, a glow, a drop shadow and the antialiased edge, because a distance is already in the units of the pixel size (feed it to draw2-aa). Prefer these exact forms for anything stroked or glowed: a bound draws an outline that thins where the bound is loose and a glow that goes lopsided. Combine with min (union) and max (intersection); round any shape by subtracting a radius, hollow it with abs(d) - w. sd2Segment's parameter is free texture coordinates along a line: dashes, arrows, a gradient from tail to head. Wrong looks like isolines that bunch or spread instead of running evenly spaced (a bound, not a distance), a rounded box that grows past its half-size, a hexagon lying on its side next to a latHex tiling, or a black dot where a zero-length segment divides by zero.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "draw2-sdf2.card",
//!  "twin": "arsenal/shaders/twins/draw2.py", "status": "P0",
//!  "exemplars": ["MdsXWM", "ltffzl", "cs2GWD", "XsBfRW", "ldSfWV", "XsjXRm", "wsl3WB", "lfscD7"],
//!  "learn": ["PF 3"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. A signed distance is the one currency of 2D drawing: how far this pixel is from the shape's edge, negative
// inside. Every edge, outline and glow the house draws is a function of it, so the shapes are written once, exactly,
// and every surface measures with the same ruler. Each one folds the plane by the shape's own symmetry first (a box
// is the same in all four quadrants, a hexagon in all twelve half-wedges) and then measures to a single edge.

// A circle of radius r about the origin.
float sd2Circle(vec2 p, float r) {
    float fromCentre = length(p);
    return fromCentre - r;
}

// An axis-aligned box of half-size halfSize. Folded into the first quadrant, q is how far past each side p is:
// outside, the distance is the length of q's positive part (to a side or to the corner); inside, it is q's largest
// component, the nearer side, which is negative.
float sd2Box(vec2 p, vec2 halfSize) {
    vec2 past = abs(p) - halfSize;
    float outside = length(max(past, 0.0));
    float inside = min(max(past.x, past.y), 0.0);
    return outside + inside;
}

// A box of outer half-size halfSize whose corners are quarter circles of radius cornerRadius: the box shrunk by the
// radius, measured, then grown back by it.
float sd2RoundBox(vec2 p, vec2 halfSize, float cornerRadius) {
    float radius = clamp(cornerRadius, 0.0, min(halfSize.x, halfSize.y));
    vec2 past = abs(p) - halfSize + radius;
    float outside = length(max(past, 0.0));
    float inside = min(max(past.x, past.y), 0.0);
    return outside + inside - radius;
}

// The segment from a to b: x is the distance to it, y how far along it the nearest point lies (0 at a, 1 at b).
vec2 sd2Segment(vec2 p, vec2 a, vec2 b) {
    const float pointLike = 1e-30;                        // a segment shorter than this is its own start point
    vec2 run = b - a;
    vec2 fromA = p - a;
    float along = clamp(dot(fromA, run) / max(dot(run, run), pointLike), 0.0, 1.0);
    float gap = length(fromA - run * along);
    return vec2(gap, along);
}

// The pointy-top hexagon of the given inradius. Its twelve-fold symmetry is used three times: abs() folds the plane
// into the first quadrant, a reflection in the mirror at 30 degrees (through the upper-right vertex) folds the wedge
// from 30 to 90 degrees down onto -30 to 30, and abs() of y once more leaves the wedge from 0 to 30 degrees. There the
// nearest boundary is the flat right-hand side, x = inradius, between y = 0 and the vertex at y = inradius / sqrt 3.
float sd2Hexagon(vec2 p, float inradius) {
    const vec2 mirror = vec2(-0.5, 0.86602540378443865);     // unit normal of the 30-degree mirror line
    vec2 q = abs(p);
    q -= 2.0 * max(dot(q, mirror), 0.0) * mirror;
    q = vec2(q.x, abs(q.y));
    float halfSide = inradius / SQRT3;
    vec2 toSide = q - vec2(inradius, clamp(q.y, -halfSide, halfSide));
    return length(toSide) * sign(q.x - inradius);
}
