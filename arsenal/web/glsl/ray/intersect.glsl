//! {"name": "ray-intersect", "kind": "helper", "cat": "E1", "family": "E", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'Intersectors' (https://iquilezles.org/articles/intersectors/): the ray-sphere solve from the perpendicular offset for precision, and the slab box with its entry normal",
//!   "Tavian Barnes, 'Fast, branchless ray/bounding box intersections' (https://tavianator.com/2011/ray_box.html): the slab method",
//!   "Inigo Quilez, 'SDF bounding volumes' (https://iquilezles.org/articles/sdfbounding/): skip a part whose bound cannot beat the best distance so far",
//!   "Eric Bruneton, 'Precomputed atmospheric scattering: a new implementation' (https://ebruneton.github.io/precomputed_atmospheric_scattering/): ray-sphere from radius and zenith cosine, robust at planet scale",
//!   "William H. Press et al., Numerical Recipes, section 5.6 'Quadratic and cubic equations' (https://numerical.recipes/): the quadratic root that never cancels"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Closed-form ray tests; rd is unit length. ixSphere returns the entry and exit t (either may be negative: .x < 0 < .y means the origin is inside, .y < 0 the sphere is behind) or vec2(-1) on a miss, computed from the centre's perpendicular offset so a small sphere far away keeps its precision. ixBox works in box space (centre at the origin): entry and exit t by the slab method, vec2(-1) on a miss or when the box is wholly behind, entryNormal the outward normal of the face entered (zero on a miss; when the origin is inside, the face behind it); a zero direction component is treated as 1e-12, so axis-parallel rays give no NaN. ixPlane returns t where the ray meets dot(p, n) + offset = 0, or -1 when it is parallel or behind. ixSlabY returns the t range inside y0 <= y <= y1, its entry clamped to 0; far < near means a miss (parallel outside, or wholly behind); parallel inside gives (0, 1e30). ixShell returns the first t range inside the shell rIn <= |p - c| <= rOut from wherever the origin is; far < near means a miss. rmClipToBox narrows tRange to a box (centre, halfSize); x > y means skip the march. bvCanSkip is true when a part's enclosing bound is already farther than the best distance so far. ixSphereAlt returns the two t of a ray starting at radius r0 with zenith cosine mu0 against the sphere of radius R round the same centre, or vec2(-1), without forming r0^2 - R^2 from two huge squares.",
//!  "note": "Analytic before iterative: a closed form costs a dozen operations where a march costs dozens of steps, and it cannot miss. Clip every march to its bounding box or slab first (a sky with no clouds in view then costs nothing), cap a march with the ground plane (rays parallel to a floor otherwise creep for ever), and keep both of a sphere's roots: glass needs the exit and a halo needs the chord. Planet-scale numbers want ixSphereAlt in kilometres. Wrong looks like a small far sphere that shimmers or vanishes (the textbook b*b - c form in float32), black speckle on axis-aligned rays (a 0 * Inf in the slab), or clouds drawn below the horizon (a slab range whose behind case was not a miss).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "ray-intersect.card", "twin": "arsenal/shaders/twins/ray.py",
//!  "status": "P0",
//!  "exemplars": ["XsSGDh", "XsjXRm", "XsfBRH", "4slGWM", "WlVyRV", "ltdcW7", "XdcyDM", "NslGRN", "cs2GWD", "ttScDc", "wsl3WB", "MfjyWK", "XtS3DD"],
//!  "learn": ["SR 5.10", "VA 3.1", "VA 4.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the geometry and the public sources credited above.
//
// WHY. "Analytic before iterative" is the house's first rule for rays: when a closed form exists, solve it. These are
// the closed forms every 3D surface needs, as accelerators (clip a march to a box, cap it at the floor) and as
// renderers in their own right (a glass marble is two roots of a quadratic).

// Entry and exit t of a unit ray against a sphere, or vec2(-1). The centre's offset is split into its part along the
// ray and its part across it; the room left inside the circle is r^2 minus the across part squared, which stays
// accurate when the sphere is small and far (the textbook b*b - c subtracts two nearly equal huge numbers).
vec2 ixSphere(vec3 ro, vec3 rd, vec3 centre, float r) {
    vec3 fromCentre = ro - centre;
    float alongRay = dot(fromCentre, rd);
    vec3 acrossRay = fromCentre - rd * alongRay;
    float room = r * r - dot(acrossRay, acrossRay);
    if (room < 0.0) {
        return vec2(-1.0);
    }
    float halfChord = sqrt(room);
    return vec2(-alongRay - halfChord, -alongRay + halfChord);
}

// Entry and exit t of a ray against a box centred at the origin (transform the ray into box space first), or vec2(-1).
// Per axis the ray is between that pair of faces from `enter` to `leave`; it is inside the box from the latest entry
// to the earliest exit. The axis that entered last is the face it came through.
vec2 ixBox(vec3 roLocal, vec3 rdLocal, vec3 halfSize, out vec3 entryNormal) {
    vec3 steady = mix(rdLocal, vec3(1e-12), lessThan(abs(rdLocal), vec3(1e-12)));
    vec3 perUnit = 1.0 / steady;
    vec3 middle = -roLocal * perUnit;
    vec3 spread = abs(perUnit) * halfSize;
    vec3 enter = middle - spread;
    vec3 leave = middle + spread;
    float near = max(max(enter.x, enter.y), enter.z);
    float far = min(min(leave.x, leave.y), leave.z);
    if (near > far || far < 0.0) {
        entryNormal = vec3(0.0);
        return vec2(-1.0);
    }
    float xEnteredLast = step(max(enter.y, enter.z), enter.x);
    float yEnteredLast = (1.0 - xEnteredLast) * step(enter.z, enter.y);
    vec3 entryAxis = vec3(xEnteredLast, yEnteredLast, 1.0 - xEnteredLast - yEnteredLast);
    entryNormal = -sign(steady) * entryAxis;
    return vec2(near, far);
}

// t where the ray meets the plane dot(p, n) + offset = 0, or -1 when it runs parallel or the plane is behind.
float ixPlane(vec3 ro, vec3 rd, vec3 n, float offset) {
    float facing = dot(rd, n);
    if (abs(facing) < 1e-8) {
        return -1.0;
    }
    float t = -(dot(ro, n) + offset) / facing;
    return t >= 0.0 ? t : -1.0;
}

// The t range inside the horizontal slab y0 <= y <= y1 for a ray starting at height oy climbing dy per unit, entry
// clamped to 0. far < near is a miss.
vec2 ixSlabY(float oy, float dy, float y0, float y1) {
    if (abs(dy) < 1e-12) {
        bool within = oy >= min(y0, y1) && oy <= max(y0, y1);
        return within ? vec2(0.0, 1e30) : vec2(1.0, -1.0);
    }
    float atY0 = (y0 - oy) / dy;
    float atY1 = (y1 - oy) / dy;
    return vec2(max(min(atY0, atY1), 0.0), max(atY0, atY1));
}

// The first t range inside a spherical shell (rIn <= |p - c| <= rOut), from outside, from inside the core, or from
// within the shell itself. far < near is a miss.
vec2 ixShell(vec3 o, vec3 d, vec3 c, float rIn, float rOut) {
    vec2 outer = ixSphere(o, d, c, rOut);
    if (outer.y < 0.0) {
        return vec2(1.0, -1.0);
    }
    float start = max(outer.x, 0.0);
    vec2 inner = ixSphere(o, d, c, rIn);
    if (inner.y < start) {
        return vec2(start, outer.y);        // the core is missed or behind: the shell runs to the outer exit
    }
    if (start < inner.x) {
        return vec2(start, inner.x);        // the core is ahead: the shell runs until the ray reaches it
    }
    return vec2(inner.y, outer.y);          // the origin is inside the core: the shell starts where the ray leaves it
}

// tRange narrowed to the box (centre, halfSize). x > y means nothing of the box is in range: skip the march.
vec2 rmClipToBox(vec3 ro, vec3 rd, vec3 centre, vec3 halfSize, vec2 tRange) {
    vec3 faceIn;
    vec2 box = ixBox(ro - centre, rd, halfSize, faceIn);
    if (box.y < 0.0) {
        return vec2(1.0, -1.0);
    }
    return vec2(max(tRange.x, box.x), min(tRange.y, box.y));
}

// True when a part whose enclosing bound is boundDistance away cannot be nearer than bestSoFar: the bound is never
// farther than the part, so if even the bound loses, the part loses, and its expensive field need not be evaluated.
bool bvCanSkip(float boundDistance, float bestSoFar) {
    return boundDistance > bestSoFar;
}

// The two t of a ray that starts r0 from a sphere's centre with zenith cosine mu0, against the sphere of radius R, or
// vec2(-1). The quadratic is t^2 + 2 (r0 mu0) t + (r0 - R)(r0 + R) = 0: the constant is formed as a product of a small
// and a large number (never as r0^2 - R^2, two squares of about 4e7 in kilometres), and the root that adds magnitudes is
// found first, the other as constant / root, so neither cancels.
vec2 ixSphereAlt(float r0, float mu0, float R) {
    float halfSlope = r0 * mu0;
    float gap = (r0 - R) * (r0 + R);
    float room = halfSlope * halfSlope - gap;
    if (room < 0.0) {
        return vec2(-1.0);
    }
    float root = sqrt(room);
    float big = -(halfSlope + (halfSlope >= 0.0 ? root : -root));
    if (abs(big) < 1e-30) {
        return vec2(0.0);
    }
    float small = gap / big;
    return vec2(min(big, small), max(big, small));
}
