//! {"name": "sdf-combine", "kind": "helper", "cat": "D3", "family": "D", "version": "1.0.0", "order": 22,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'Smooth minimum' (https://iquilezles.org/articles/smin/): the kernel family, normalising k to the junction's thickening, rigidity and the circular kernel",
//!   "Inigo Quilez, 'Interior SDFs' (https://iquilezles.org/articles/interiordistance/): why a union is wrong deep inside, and xor exact on both sides",
//!   "Inigo Quilez, 'Distance functions' (https://iquilezles.org/articles/distfunctions/): rounding, onion shells, uniform scale",
//!   "John C. Hart, 'Sphere tracing' (The Visual Computer 12, 1996, https://doi.org/10.1007/s003710050084): a displaced field divided by its Lipschitz figure stays a bound"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Each operator takes signed distances (negative inside) and says how honest its answer is. opUnion (min) is exact outside, unreliable deep inside; opIntersect (max) and opSubtract (a minus b: max(a, -b)) are bounds; opXor is exact inside and outside for exact inputs; opPick is the union of (distance, material id) pairs keeping the nearer id (a tie keeps a). The smooth operators are bounds whose k is the blend's thickness in world units: opSmin dips exactly k below min where a = b and is plain min once |a - b| >= 4k (quadratic kernel, order-dependent); opSminMix returns opSmin in .x and in .y the weight of b (0 to 1) that also blends the two gradients into the result's own, so materials and normals mix with the shape; opSmax is -opSmin(-a, -b, k) and opSsubtract is opSmax(a, -b, k); opSminCircular dips k and draws an exactly circular fillet of radius k / (1 - sqrt(1/2)) between perpendicular surfaces, plain min beyond that radius apart; opSminExp dips k, is order-independent and associative, and never quite reaches min (it softens shapes everywhere). opRound(d, r) = d - r and opOnion(d, t) = |d| - t are exact when d is; opUniformScale(d at p / s, s) = d * s is exact; opDisplace(d, g, L) = (d + g) / (1 + L) stays a bound when L is an honest bound on the gradient length of g.",
//!  "note": "The solder joints. The house order is opSubtract(a, b) = a minus b (Quilez's opSubtraction removes its FIRST argument from its second; flip it on every port). Reach for opSmin as the everyday weld (cheap, conservative, a fillet that looks round) and opSminExp only when a long chain of blends must not depend on its order. Keep k smaller than the parts it joins: a k far larger than both turns sticks into sinew (Alien Core's look, on purpose). Never read refraction or thickness from a union's interior; build the inside as its own exact field. Displacement is a debt: divide by 1 + L, and if the marcher still punches holes the L you passed is a lie (for a product of sines it is amplitude times frequency). Wrong looks like a carved part that grew instead (subtract order swapped), a seam that changes when two blends are reordered (expected for opSmin, a bug for opSminExp), or holes in a displaced surface (an L that is too small).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "sdf-combine.card", "twin": "arsenal/shaders/twins/sdf.py",
//!  "status": "P0",
//!  "exemplars": ["4tcXRr", "7cjGRR", "cs2GWD", "4lj3Ww", "ltdcW7", "7d2fDW", "tsScDG", "XtyXzW", "WdB3Dw", "llVXRd", "MdX3zr", "XsjXRm", "lfscD7", "llK3Dy", "3XdXRr"],
//!  "learn": ["SR 4.3", "SR 4.4", "SR 4.5", "SR 4.7", "SR 4.9", "SR 4.10"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. A scene is a handful of shapes joined together, and every join is a promise about distance that the marcher will
// trust. Min, max and their smooth cousins are each written once here with their honesty stated, so a surface that
// blends two shapes cannot quietly use the other argument order, or a blend whose k means something different.

// EO: exact outside, unreliable deep inside.
float opUnion(float a, float b) {
    float nearer = min(a, b);
    return nearer;
}

// B: a bound.
float opIntersect(float a, float b) {
    float farther = max(a, b);
    return farther;
}

// B: a minus b, the house order (inside b is carved out of a).
float opSubtract(float a, float b) {
    float carved = max(a, -b);
    return carved;
}

// E: exact inside and outside. In each of the four sign cases the expression is a min of two non-negative distances,
// with the sign of the case, and the min of exterior distances is exact.
float opXor(float a, float b) {
    float nearer = min(a, b);
    float farther = max(a, b);
    return max(nearer, -farther);
}

// EO: the union of (distance, material id) pairs; the nearer id wins and a tie keeps a.
vec2 opPick(vec2 a, vec2 b) {
    return b.x < a.x ? b : a;
}

// B: the quadratic smooth union. Within a band of width 4k around a = b the blend digs below min by a parabola that
// is k deep at the junction and meets min smoothly at the band's edges; outside the band it is exactly min. The
// gradient there is a weighted average of the two unit gradients, so the field never runs faster than distance.
float opSmin(float a, float b, float k) {
    vec2 nearAndGap = vec2(min(a, b), abs(a - b));      // the nearer distance, and how far apart the two are
    float band = 4.0 * max(k, 1e-20);
    float overlap = max(band - nearAndGap.y, 0.0) / band;
    return nearAndGap.x - overlap * overlap * band * 0.25;
}

// opSmin in .x, and in .y the weight of b: how much of b's material and b's gradient the blended surface carries. For
// the quadratic kernel the gradient is mix(gradient of a, gradient of b, .y) exactly, half the overlap on the side of
// the nearer shape.
vec2 opSminMix(float a, float b, float k) {
    vec2 nearAndGap = vec2(min(a, b), abs(a - b));
    float band = 4.0 * max(k, 1e-20);
    float overlap = max(band - nearAndGap.y, 0.0) / band;
    float blended = nearAndGap.x - overlap * overlap * band * 0.25;
    float halfOverlap = 0.5 * overlap;
    float weightOfB = a < b ? halfOverlap : 1.0 - halfOverlap;
    return vec2(blended, weightOfB);
}

// B: smooth intersection, the smooth union of the outsides.
float opSmax(float a, float b, float k) {
    vec2 outsides = vec2(-a, -b);
    return -opSmin(outsides.x, outsides.y, k);
}

// B: smooth a minus b.
float opSsubtract(float a, float b, float k) {
    vec2 keptAndCut = vec2(a, -b);
    return opSmax(keptAndCut.x, keptAndCut.y, k);
}

// B: the circular smooth union. Between two perpendicular surfaces (a and b as plane coordinates) its zero set is a
// quarter circle of radius k / (1 - sqrt(1/2)) tangent to both, so the junction dips by exactly k. With u the gap
// |a - b| in units of that radius, the circle gives the dip as radius * (1 - (u + sqrt(2 - u * u)) / 2).
float opSminCircular(float a, float b, float k) {
    vec2 nearAndGap = vec2(min(a, b), abs(a - b));
    float radius = max(k, 1e-20) / (1.0 - sqrt(0.5));
    float gap = min(nearAndGap.y / radius, 1.0);
    float lift = 1.0 - 0.5 * (gap + sqrt(max(2.0 - gap * gap, 0.0)));
    return nearAndGap.x - radius * lift;
}

// B: the exponential smooth union, -k log2(2^(-a/k) + 2^(-b/k)), written from the nearer distance so no power can
// overflow. It dips exactly k at a = b, and since it is a log-sum, any order of a chain of blends gives one shape.
float opSminExp(float a, float b, float k) {
    vec2 nearAndGap = vec2(min(a, b), abs(a - b));
    float softness = max(k, 1e-20);
    return nearAndGap.x - softness * log2(1.0 + exp2(-nearAndGap.y / softness));
}

// Exact if d is: moves to the iso-surface r further out, rounding every convex edge and growing the shape by r.
float opRound(float d, float r) {
    return d - r;
}

// Exact if d is: a hollow shell of the given thickness either side of the surface. Apply again for concentric layers.
float opOnion(float d, float thickness) {
    return abs(d) - thickness;
}

// Exact: the caller evaluated the shape at p / scale; the distance comes back in world units.
float opUniformScale(float dAtScaledPoint, float scale) {
    return dAtScaledPoint * scale;
}

// B while lipschitz is an honest bound on how fast the displacement can change per unit of distance: the sum of the two
// can run 1 + lipschitz times faster than distance, so it is divided by that.
float opDisplace(float d, float displacement, float lipschitz) {
    return (d + displacement) / (1.0 + lipschitz);
}
