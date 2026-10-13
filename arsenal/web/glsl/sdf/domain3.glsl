//! {"name": "sdf-domain3", "kind": "helper", "cat": "D4", "family": "D", "version": "1.0.1", "order": 22,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'Domain repetition' (https://iquilezles.org/articles/sdfrepetition/): the cell id, limited repetition by clamping the id, and when one evaluation is not enough",
//!   "Mercury, 'hg_sdf' (https://mercury.sexy/hg_sdf/): domain operators that take the point in-out and return the cell or sector, and the fold across an arbitrary plane",
//!   "John C. Hart, 'Sphere tracing' (The Visual Computer 12, 1996, https://doi.org/10.1007/s003710050084): a warp multiplies the field's Lipschitz constant by its largest stretch",
//!   "Wikipedia, 'Icosahedral symmetry' (https://en.wikipedia.org/wiki/Icosahedral_symmetry): the reflection group of order 120 and its fundamental triangle with angles pi/2, pi/3, pi/5",
//!   "Wikipedia, 'Inversive geometry' (https://en.wikipedia.org/wiki/Inversive_geometry): inversion in a sphere and its local stretch"],
//!  "cost": {"class": "C1", "loop": "domFoldIcosa: 5 folds; every other operator: none", "tex": 0},
//!  "contract": "Operators on the point, applied before the shape is evaluated. domRigid returns the object-space point of an object placed by an orthonormal rotation (its columns are the object's axes in the world) and then a position: exact. domMirror takes abs() of the axes whose mask is 1: exact while the content does not cross a mirror. domTwistY turns the xz plane by rate * y radians (counter-clockwise seen from +y); domBend turns the xy plane by rate * x; divide either field by lipTwist(rate, R), (|rate| R + sqrt(rate^2 R^2 + 4)) / 2, to keep a bound within radius R of the axis (sqrt(1 + rate^2 R^2) is too small). domRepeat and domRepeatLimited write the point centred in its cell (each part within half a period) and return the cell id, floor(p / period + 0.5), clamped to [idMin, idMax] by the limited one, the period floored at 1e-6 per axis (as domRepeat2's): one evaluation is exact only for identical content symmetric within its cell. domPolar rounds count to a whole number of sectors n (at least 1, as domKaleido does), writes the point turned into its sector (within pi / n of +x) and returns the sector id in 0..n-1, sector 0 centred on +x; the centre has no angle and is sector 0. domReflect folds the point across the plane dot(p, n) + offset = 0 (n unit) onto its positive side and returns -1 if it was folded, else +1. domFoldIcosa folds the point into one 1/120 chamber of the icosahedral group (x >= 0, y >= 0 and on the positive side of its third mirror), with corners on a 2-fold axis (0, 0, 1), a 5-fold vertex (0, 1, PHI) and a 3-fold face centre (1, 0, PHI^2): every point and its 119 images fold to one point, and length is kept. domInvert3 inverts the point in the sphere of squared radius radiusSq (|p| |p'| = radiusSq) and multiplies scale by the local stretch radiusSq / |p|^2; divide the final distance by scale. That quotient is an estimate, not a bound: it is first-order exact at the surfaces but can run up to 1 + 2 |p| d / radiusSq times faster than distance where the distance d after inversion is large, so march an inverted field under-relaxed (rmSphereTrace with omega below 1) or with rmBacktrack.",
//!  "note": "The mirrors and jigs of the workshop: model one piece, let space make the copies. The id a repetition returns is the free per-copy identity (hash it for size, colour, phase), and it is a cell id, so never take a derivative of it. Repeating varied or rotated copies with one evaluation over-reports near cell walls (cracks and bites that crawl as the camera moves): keep each copy well inside half a cell, or evaluate the neighbours. A twist or a bend is a warp, not a rigid move: forget lipTwist and the marcher steps through the surface. Keep repetition near the origin: at a coordinate of 10,000 a float resolves only about a thousandth, and fine detail inside each cell stair-steps. domFoldIcosa makes density a free knob: one sliver of geometry placed in the chamber tiles the whole sphere exactly (the geodesic look); put a feature at a chamber corner and you get 12, 20 or 30 of it. lipTwist is honest only within the radius you pass: give it the farthest the content (or the ray) reaches from the axis. Wrong looks like a seam at a fixed angle around a polar pattern (asymmetric content), a twisted column with holes (no lipTwist, or a radius too small), or a fractal that shrinks to nothing (scale not divided out after domInvert3) or punches holes between its spheres (an inverted field marched at full step).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "sdf-domain3.card", "twin": "arsenal/shaders/twins/sdf.py",
//!  "status": "P0",
//!  "exemplars": ["7cjGRR", "3XdXRr", "XtyXzW", "llK3Dy", "XsSGDh", "4tcXRr", "cs2GWD", "llVXRd", "7d2fDW"],
//!  "learn": ["SR 4.7", "SR 4.8", "SR 4.9", "SR 3.3", "PF 10.5", "study:llVXRd 6.1"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public sources credited above.
//
// WHY. Most of a scene's richness is repetition and symmetry: a lattice of boxes, seven vanes, a geodesic ball. Rather
// than evaluating many shapes, these operators move the POINT into one copy's frame and evaluate one shape there. They
// are where most hole-punching bugs come from (a warp that stretches space without saying how much), so each states its
// honesty and, where it stretches, ships its stretch factor beside it.

// Exact: the object-space point of an object placed by `rotation` (orthonormal; its columns are the object's axes in
// the world) and then `position`. A row vector times the matrix applies its transpose, which is its inverse.
vec3 domRigid(vec3 p, mat3 rotation, vec3 position) {
    vec3 offset = p - position;
    return offset * rotation;
}

// abs() on the axes whose mask is 1 (0 leaves the axis alone): model one half, get the mirror image free.
vec3 domMirror(vec3 p, vec3 axisMask) {
    return mix(p, abs(p), axisMask);
}

// Turn the xz plane by rate * y radians. Not rigid: divide the field by lipTwist(rate, maxRadius).
vec3 domTwistY(vec3 p, float rate) {
    vec2 swung = rotate2(rate * p.y) * p.xz;
    return vec3(swung.x, p.y, swung.y);
}

// The twist's (and the bend's) largest stretch within maxRadius of its axis: the Jacobian is a rotation times a shear of
// size s = |rate| * maxRadius, whose largest singular value is (s + sqrt(s * s + 4)) / 2 (the golden ratio at s = 1).
float lipTwist(float rate, float maxRadius) {
    float shear = abs(rate) * maxRadius;
    return 0.5 * (shear + sqrt(shear * shear + 4.0));
}

// Turn the xy plane by rate * x radians: the x axis curls round. Not rigid: divide the field by lipTwist(rate, R) with R
// the largest |(x, y)| the content reaches.
vec3 domBend(vec3 p, float rate) {
    vec2 swung = rotate2(rate * p.x) * p.xy;
    return vec3(swung, p.z);
}

// Infinite grid repetition: p becomes the point centred in its cell; the cell id comes back.
vec3 domRepeat(inout vec3 p, vec3 period) {
    vec3 size = max(period, vec3(1e-6));               // a zero period would divide by zero
    vec3 cell = floor(p / size + 0.5);
    p -= size * cell;
    return cell;
}

// Finite grid repetition: the id is clamped to [idMin, idMax], so outside the block the edge copy is simply seen from
// further away, and the field stays a distance (never intersect an infinite grid with a box instead).
vec3 domRepeatLimited(inout vec3 p, vec3 period, vec3 idMin, vec3 idMax) {
    vec3 size = max(period, vec3(1e-6));
    vec3 cell = clamp(floor(p / size + 0.5), idMin, idMax);
    p -= size * cell;
    return cell;
}

// Rotational repetition round the origin: p is turned into its sector (within half a wedge of +x); the sector id, 0 to
// count - 1, comes back. The centre has no angle (atan(0, 0) is undefined), so it is sector 0. The count is rounded to
// a whole number of sectors: a fractional count would leave one narrower wedge, a seam at a fixed angle.
float domPolar(inout vec2 p, float count) {
    float sectors = max(floor(count + 0.5), 1.0);
    float wedge = TAU / sectors;
    float angle = (p.x == 0.0 && p.y == 0.0) ? 0.0 : atan(p.y, p.x);
    float turns = floor(angle / wedge + 0.5);
    p = rotate2(-turns * wedge) * p;
    return turns - sectors * floor(turns / sectors);
}

// Fold across the plane dot(p, n) + offset = 0 (n unit): a point on the negative side is mirrored onto the positive
// side. Returns -1 when it was folded, +1 otherwise.
float domReflect(inout vec3 p, vec3 n, float offset) {
    float side = dot(p, n) + offset;
    if (side < 0.0) {
        p -= (side + side) * n;
        return -1.0;
    }
    return 1.0;
}

// Fold into one chamber of the icosahedral reflection group. The chamber's walls are the planes x = 0 and y = 0 (90
// degrees apart) and a third mirror whose unit normal makes 120 degrees with the y wall's and 144 with the x wall's, so
// the chamber's corners carry 2-, 3- and 5-fold symmetry. Each pass reflects across every wall the point is on the
// wrong side of; five passes bring any point home (measured: the farthest, the antipode of the chamber, needs five).
vec3 domFoldIcosa(vec3 p) {
    vec3 thirdWall = vec3(-0.5 * PHI, -0.5, 0.5 * (PHI - 1.0));
    vec3 folded = p;
    for (int foldPass = 0; foldPass < 5; foldPass++) {
        folded.xy = abs(folded.xy);
        float behind = min(dot(folded, thirdWall), 0.0);
        folded -= (behind + behind) * thirdWall;
    }
    return folded;
}

// Inversion in the sphere of squared radius radiusSq round the origin. Near p it stretches space by radiusSq / |p|^2;
// that factor is multiplied into scale, and a distance measured after the inversion is divided by scale. The quotient
// is right at the surfaces; between them the stretch itself changes across the distance, so it over-reports there.
vec3 domInvert3(vec3 p, float radiusSq, inout float scale) {
    float stretch = radiusSq / max(dot(p, p), 1e-20);
    scale *= stretch;
    return p * stretch;
}
