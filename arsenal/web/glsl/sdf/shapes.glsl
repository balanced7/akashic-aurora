//! {"name": "sdf-shapes", "kind": "helper", "cat": "D1", "family": "D", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'Distance functions' (https://iquilezles.org/articles/distfunctions/): the exact primitives and the 'positive part plus clamped interior' pattern they share",
//!   "Inigo Quilez, 'Ellipsoid SDF' (https://iquilezles.org/articles/ellipsoids/): dividing the stretched sphere by its gradient for a tight bound",
//!   "Mercury, 'hg_sdf' (https://mercury.sexy/hg_sdf/): the generalised distance functions, a solid as the farthest of a table of face planes",
//!   "Ergun Akleman and Jianer Chen, 'Generalized distance functions' (Shape Modeling International 1999, https://doi.org/10.1109/SMA.1999.749340): the face-normal construction",
//!   "John C. Hart, 'Sphere tracing' (The Visual Computer 12, 1996, https://doi.org/10.1007/s003710050084): a field divided by its Lipschitz constant never overestimates"],
//!  "cost": {"class": "C1", "loop": "sbPolyhedron: 19 face planes; every other shape: none", "tex": 0},
//!  "contract": "Every shape is centred at the origin with y up, negative inside. sd* is the exact Euclidean signed distance inside and outside (sdPlane only when its normal is unit length; sdRoundBox while cornerRadius <= the smallest half size; sdRoundConeAB is the hull of the two balls, the bigger ball when one holds the other). sb* never exceeds the true distance and is zero exactly on the surface (sbEllipsoid tight near the surface; sbPolyhedron exact inside; sbSuperquadric divides by how much faster than distance its Lp norm can run). udTriangle is the exact unsigned distance to a triangle. sdCapsule is the segment endA-endB inflated. sdHexPrismZ has its apothem along y (flat edges top and bottom); sdConeCappedY runs from radius rBottom at y = -h to rTop at y = +h; sbPolyhedron's solidKind is 0 cube, 1 octahedron, 2 dodecahedron, 3 icosahedron, 4 truncated octahedron, 5 truncated icosahedron, every face r from the centre, oriented so (0, 1, PHI) is an icosahedron vertex (the orientation domFoldIcosa folds into).",
//!  "note": "The parts bin of the 3D shelf. The prefix is the datasheet: a marcher can step a full sd distance and a full sb distance and never pass through a surface, while a field that over-reports punches holes that crawl as the camera moves. Reach for an exact primitive first, then the exact modifiers (round, onion), and only then a bound: a bound marches slower and darkens shadows and occlusion a little (the ellipsoid's caps, a polyhedron's corners). Build a stretched sphere from sbEllipsoid, never by scaling space, which over-reports along the long axis. A shape that should be hollow is opOnion of a solid, not a second shape subtracted. Wrong looks like holes or ghost slabs when the camera moves (an overestimate: a non-unit plane normal, a cornerRadius bigger than the box), unevenly spaced iso-lines in a distance slice, or a cone whose caps swap (rBottom and rTop are bottom and top, at y = -h and +h).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "sdf-shapes.card", "twin": "arsenal/shaders/twins/sdf.py",
//!  "status": "P0",
//!  "exemplars": ["cs2GWD", "llK3Dy", "7cjGRR", "ltdcW7", "XfXGz4", "XsjXRm", "MdX3zr", "XtyXzW", "XdcyDM", "43jXWt", "3XdXRr", "MtXczn"],
//!  "learn": ["SR 4.1", "SR 3.2", "SR 3.3", "SR 12.1"]}
// Apache-2.0, Akashic Aurora. Written fresh from the geometry and the public articles credited above.
//
// WHY. A marcher asks one question of a scene, "how far is the nearest surface?", and steps exactly that far. Each
// function here answers it for one shape, and its name says how honestly: sd is the exact answer, sb is an answer that
// is never too large, ud has no inside. Most exact shapes are three moves: fold the point into one symmetric piece with
// abs(), reduce it to a 2D problem (the meridian of a solid of revolution, the cross-section of a prism), then find the
// nearest point on a few segments.

// Exact: the distance to the centre, less the radius.
float sdSphere(vec3 p, float r) {
    float fromCentre = length(p);
    return fromCentre - r;
}

// Exact inside and outside. Folded into one octant, `past` says how far the point is beyond each pair of faces
// (negative while between them): outside, the distance is the length of the positive part; inside, it is the nearest
// face, the largest of the negative parts.
float sdBox(vec3 p, vec3 halfSize) {
    vec3 past = abs(p) - halfSize;
    float outside = length(max(past, 0.0));
    float inside = min(max(past.x, max(past.y, past.z)), 0.0);
    return outside + inside;
}

// Exact while cornerRadius <= the smallest half size: a box shrunk by the radius, grown back as a rounded skin, so the
// outer extent stays halfSize.
float sdRoundBox(vec3 p, vec3 halfSize, float cornerRadius) {
    float core = sdBox(p, halfSize - cornerRadius);
    return core - cornerRadius;
}

// Exact when unitNormal has length 1 (the caller's duty): the plane is dot(p, unitNormal) + offset = 0.
float sdPlane(vec3 p, vec3 unitNormal, float offset) {
    float height = dot(p, unitNormal);
    return height + offset;
}

// Exact: a ring of radius ringRadius in the xz plane, its tube tubeRadius thick. In the tube's own cross-section the
// torus is a circle.
float sdTorusY(vec3 p, float ringRadius, float tubeRadius) {
    vec2 meridian = vec2(length(p.xz) - ringRadius, p.y);
    return length(meridian) - tubeRadius;
}

// Exact: the segment from endA to endB inflated by `inflate`. The nearest point of the segment is the projection onto
// it, held to its ends; endA == endB is a sphere (the projection divides by at least 1e-12).
float sdCapsule(vec3 p, vec3 endA, vec3 endB, float inflate) {
    vec3 run = endB - endA;
    vec3 fromA = p - endA;
    float along = clamp(dot(fromA, run) / max(dot(run, run), 1e-12), 0.0, 1.0);
    return length(fromA - run * along) - inflate;
}

// Exact capped cylinder along y: a rectangle in the meridian plane, past the wall and past the caps.
float sdCylinderY(vec3 p, float r, float halfHeight) {
    vec2 past = vec2(length(p.xz) - r, abs(p.y) - halfHeight);
    float outside = length(max(past, 0.0));
    float inside = min(max(past.x, past.y), 0.0);
    return outside + inside;
}

// Exact cone frustum along y: radius rBottom at y = -h, rTop at y = +h (either may be 0, for a point). In the meridian
// plane it is a trapezoid; the distance is to the nearer cap or to the slanted side, and the point is inside when it
// is under the side and between the caps.
float sdConeCappedY(vec3 p, float h, float rBottom, float rTop) {
    float radial = length(p.xz);
    vec2 meridian = vec2(radial, p.y);
    float capRadius = meridian.y < 0.0 ? rBottom : rTop;
    vec2 toCap = vec2(meridian.x - min(meridian.x, capRadius), abs(meridian.y) - h);
    vec2 foot = vec2(rBottom, -h);
    vec2 slant = vec2(rTop - rBottom, h + h);
    float along = clamp(dot(meridian - foot, slant) / max(dot(slant, slant), 1e-12), 0.0, 1.0);
    vec2 toSide = meridian - foot - slant * along;
    bool within = toSide.x < 0.0 && toCap.y < 0.0;
    float nearest = sqrt(min(dot(toCap, toCap), dot(toSide, toSide)));
    return within ? -nearest : nearest;
}

// Exact: the hull of a ball of radius ra at a and one of radius rb at b, joined by their tangent cone. In the plane of
// the axis the side is a line tangent to both circles; its outward normal leans by the angle whose sine is
// (ra - rb) / |b - a|. Past the tangent points the nearest surface is a ball's.
float sdRoundConeAB(vec3 p, vec3 a, vec3 b, float ra, float rb) {
    vec3 axis = b - a;
    float span = length(axis);
    if (span <= abs(ra - rb)) {
        return min(length(p - a) - ra, length(p - b) - rb);
    }
    vec3 up = axis / span;
    vec3 fromA = p - a;
    float height = dot(fromA, up);
    float radial = length(fromA - up * height);
    float slope = (ra - rb) / span;
    float lean = sqrt(max(1.0 - slope * slope, 0.0));
    float along = height * lean - radial * slope;
    if (along < 0.0) {
        return length(vec2(radial, height)) - ra;
    }
    if (along > span * lean) {
        return length(vec2(radial, height - span)) - rb;
    }
    return radial * lean + height * slope - ra;
}

// Exact hexagonal prism along z: the apothem (centre to edge) along y, so the top and bottom edges are flat. Folded by
// abs() and once more across the 60-degree line, every point sits under the top edge; the hexagon's distance is to that
// edge's segment, then extruded like a box in (hexagon, depth).
float sdHexPrismZ(vec3 p, float apothem, float halfDepth) {
    vec2 folded = abs(p.xy);
    vec2 mirror60 = vec2(-0.5 * SQRT3, 0.5);
    folded -= 2.0 * min(dot(folded, mirror60), 0.0) * mirror60;
    float halfEdge = apothem / SQRT3;
    vec2 toEdge = vec2(folded.x - clamp(folded.x, -halfEdge, halfEdge), folded.y - apothem);
    float across = length(toEdge) * sign(toEdge.y);
    vec2 past = vec2(across, abs(p.z) - halfDepth);
    float outside = length(max(past, 0.0));
    return min(max(past.x, past.y), 0.0) + outside;
}

// Exact regular octahedron |x| + |y| + |z| = s, its six vertices s from the centre (not the cheap planar bound). In one
// octant the face is the plane x + y + z = s. When the point's foot on that plane falls inside the face (every
// coordinate at least a third of the overshoot) the distance is to the plane; otherwise the coordinate that falls short
// names the nearest edge, the one from (0, s, 0) to (0, 0, s) after a cyclic swap, and the distance is to that segment.
float sdOctahedron(vec3 p, float vertexDistance) {
    float s = vertexDistance;
    vec3 octant = abs(p);
    float over = octant.x + octant.y + octant.z - s;
    float third = over / 3.0;
    vec3 swapped = octant;
    if (octant.x < third) {
        swapped = octant;
    } else if (octant.y < third) {
        swapped = octant.yzx;
    } else if (octant.z < third) {
        swapped = octant.zxy;
    } else {
        return over / SQRT3;
    }
    float slide = clamp(0.5 * (swapped.z - swapped.y) + 0.5 * s, 0.0, s);
    vec3 toEdge = vec3(swapped.x, swapped.y - s + slide, swapped.z - slide);
    return length(toEdge);
}

// A bound, tight near the surface. Outside: the stretched sphere |p / radii| - 1 divided by its own gradient's length,
// the first-order distance. Inside: the gap to a shrunken copy of the ellipsoid, times the smallest radius, which no
// interior point can beat (and which is exact at the centre, with no 0 / 0 there).
float sbEllipsoid(vec3 p, vec3 radii) {
    float stretched = length(p / radii);
    if (stretched < 1.0) {
        return (stretched - 1.0) * min(radii.x, min(radii.y, radii.z));
    }
    float steepness = length(p / (radii * radii));
    return stretched * (stretched - 1.0) / steepness;
}

// A bound, exact inside: the solid is every point within r of the centre along each face direction, so the distance is
// the farthest reach along any of them, less r. The 19 directions (up to sign) cover six solids: the 3 axes (cube), the
// 4 diagonals (octahedron), the cyclic shifts of (0, 1, +-PHI) (dodecahedron) and, with the diagonals, the cyclic shifts
// of (0, PHI, +-1/PHI) (icosahedron); the truncated octahedron and icosahedron take two solids' directions together.
// Each direction is built from its number, so the table is arithmetic rather than nineteen literals.
float sbPolyhedron(vec3 p, float r, int solidKind) {
    float tail = PHI - 1.0;
    int kind = clamp(solidKind, 0, 5);
    // which of the four direction groups (bits: axes 1, diagonals 2, dodecahedron 4, icosahedron 8) this solid uses
    int groups = kind == 0 ? 1 : (kind == 1 ? 2 : (kind == 2 ? 4 : (kind == 3 ? 10 : (kind == 4 ? 3 : 14))));
    float reach = 0.0;
    for (int face = 0; face < 19; face++) {
        int group = face < 3 ? 1 : (face < 7 ? 2 : (face < 13 ? 4 : 8));
        if ((groups & group) == 0) {
            continue;
        }
        vec3 dir;
        if (face < 3) {
            dir = vec3(float(face == 0), float(face == 1), float(face == 2));
        } else if (face < 7) {
            int corner = face - 3;                       // (1,1,1), then one coordinate flipped: x, y or z
            dir = vec3(corner == 1 ? -1.0 : 1.0, corner == 2 ? -1.0 : 1.0, corner == 3 ? -1.0 : 1.0);
        } else {
            int member = face < 13 ? face - 7 : face - 13;
            float flip = (member & 1) == 0 ? 1.0 : -1.0;
            vec3 seed = face < 13 ? vec3(0.0, 1.0, flip * PHI) : vec3(0.0, PHI, flip * tail);
            int shift = member >> 1;                     // 0, 1 or 2 cyclic shifts of the seed
            dir = shift == 0 ? seed : (shift == 1 ? seed.yzx : seed.zxy);
        }
        reach = max(reach, abs(dot(p, dir)) / length(dir));
    }
    return reach - r;
}

// A bound for the superellipsoid (|x / r.x|^n + |y / r.y|^n + |z / r.z|^n)^(1/n) = 1: n = 2 is an ellipsoid (a sphere
// when r is equal), large n a rounded cube, n = 1 an octahedron. An Lp norm with n >= 2 never runs faster than distance;
// below 2 it can run up to 3^(1/n - 1/2) times faster, so the field is divided by that. The largest part is factored
// out first so no power overflows, however big n or far the point.
float sbSuperquadric(vec3 p, vec3 r, float n) {
    vec3 unitSpace = abs(p / r);
    float biggest = max(max(unitSpace.x, unitSpace.y), max(unitSpace.z, 1e-20));
    vec3 share = unitSpace / biggest;
    float lpNorm = biggest * pow(dot(pow(share, vec3(n)), vec3(1.0)), 1.0 / n);
    float runsAhead = pow(3.0, max(1.0 / n - 0.5, 0.0));
    return (lpNorm - 1.0) * min(r.x, min(r.y, r.z)) / runsAhead;
}

// Exact unsigned distance to the triangle a, b, c. Over the triangle (inside all three edge planes) it is the height
// above its plane; elsewhere the nearest point is on one of the three edges.
float udTriangle(vec3 p, vec3 a, vec3 b, vec3 c) {
    vec3 edgeAB = b - a;
    vec3 edgeBC = c - b;
    vec3 edgeCA = a - c;
    vec3 fromA = p - a;
    vec3 fromB = p - b;
    vec3 fromC = p - c;
    vec3 facing = cross(edgeAB, edgeCA);
    float sides = sign(dot(cross(edgeAB, facing), fromA)) + sign(dot(cross(edgeBC, facing), fromB))
                + sign(dot(cross(edgeCA, facing), fromC));
    if (sides < 2.0) {
        vec3 offAB = fromA - edgeAB * clamp(dot(edgeAB, fromA) / max(dot(edgeAB, edgeAB), 1e-20), 0.0, 1.0);
        vec3 offBC = fromB - edgeBC * clamp(dot(edgeBC, fromB) / max(dot(edgeBC, edgeBC), 1e-20), 0.0, 1.0);
        vec3 offCA = fromC - edgeCA * clamp(dot(edgeCA, fromC) / max(dot(edgeCA, edgeCA), 1e-20), 0.0, 1.0);
        return sqrt(min(min(dot(offAB, offAB), dot(offBC, offBC)), dot(offCA, offCA)));
    }
    return abs(dot(facing, fromA)) / max(length(facing), 1e-20);
}
