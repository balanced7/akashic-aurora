//! {"name": "ray-normals", "kind": "helper", "cat": "E4", "family": "E", "version": "1.0.0", "order": 24,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'Normals for an SDF' (https://iquilezles.org/articles/normalsSDF/): the four-tap tetrahedron gradient (after Paulo Falcao and Paul Malin) and an epsilon from the pixel footprint",
//!   "Fabrice Neyret, 'Avoiding compiler crash or endless compilation' (https://shadertoyunofficial.wordpress.com/2017/11/19/avoiding-compiler-crash-or-endless-compilation/): a loop whose start the compiler cannot know keeps the scene compiled once",
//!   "Wikipedia, 'Mean curvature' (https://en.wikipedia.org/wiki/Mean_curvature): the Laplacian of a distance function is the sum of the principal curvatures"],
//!  "cost": {"class": "C1", "loop": "nrmTetra 4 hook calls, nrmCentral 6, nrmCurvature 5 (each tap loop runs twice as long for an h below -1)", "tex": 0, "hooks": 1},
//!  "hooks": ["float mapScene(vec3 p)"],
//!  "contract": "The normal is the normalised gradient of the host's mapScene(p), measured by finite differences at offset |h|. nrmTetra samples the four corners (+-1, +-1, +-1) of a tetrahedron (corner products all +1) and returns their mapScene-weighted sum normalised: central-difference quality for forward-difference cost. nrmCentral uses the six axis taps; reference and debug. Both return (0, 1, 0) where the gradient vanishes, never NaN. nrmCurvature returns the Laplacian of mapScene from the tetrahedron taps and the centre, (sum of taps - taps * centre) / (taps * h^2 / 2): on an exact distance field it is the sum of the principal curvatures (2 / R on a sphere of radius R, 1 / R on a cylinder, 0 on a plane; positive where the surface bulges out). nrmEps(t, pixelAngle, materialScale) = materialScale * max(pixelAngle t, 1e-5): one pixel's footprint at the hit, scaled per material. nrmFacet snaps n to the nearest direction of the integer lattice scaled by steps, normalised (n itself if that rounds to zero). Each tap loop starts at a value the compiler cannot prove is zero (0 for any h above -1), so the scene is compiled into the loop once, not inlined per tap.",
//!  "note": "Shading lives or dies on the normal. Take h from the footprint (nrmEps): a tiny constant h samples detail far smaller than a pixel and distant surfaces sparkle; a big one blurs the foreground; a per-material scale on it is a cheap bevel that rounds every edge by the same few pixels. Four taps (nrmTetra) are the house default; six (nrmCentral) are for checking it. nrmCurvature is the jeweller's polishing wheel: threshold it at one width for an edge highlight, at another to wear texture off convex edges. nrmFacet keeps a low-poly look on the light while textures keep the smooth normal. Wrong looks like shimmering distant detail (h constant), mushy edges on thin parts (h too big), a black pixel at a crease (a gradient of zero, guarded here), or a page that hangs on its first frame (a scene inlined many times: the taps must stay in their loop).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "ray-normals.card", "twin": "arsenal/shaders/twins/ray.py",
//!  "status": "P0",
//!  "exemplars": ["7cjGRR", "ltdcW7", "XdcyDM", "ttScDc", "cs2GWD", "XtyXzW", "llVXRd", "MtXczn", "43jXWt"],
//!  "learn": ["SR 6.1", "SR 5.11", "study:XdcyDM 6.2", "study:ltdcW7"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the articles credited above.
//
// WHY. A distance field's gradient is the surface normal, and the field is the only description of the surface a
// raymarcher has, so the normal is measured by probing the field around the hit. Four probes at the corners of a
// tetrahedron do the work of six: expanded to first order, the corners' weights sum to zero and their outer products
// sum to four times the identity, so the weighted sum is exactly four h times the gradient.

// The unit normal from four tetrahedron taps at offset |h|.
vec3 nrmTetra(vec3 p, float h) {
    float reach = max(abs(h), 1e-7);
    // A start the compiler cannot prove is 0 keeps the loop a loop (one compiled copy of mapScene, not four). It is 0
    // for any h above -1; below that it is -4 and every corner is visited twice, which leaves the direction unchanged.
    int first = 4 * clamp(int(min(h, 0.0)), -1, 0);
    vec3 gradient = vec3(0.0);
    for (int tap = first; tap < 4; tap++) {
        int corner = (tap + 4) & 3;
        float high = float(corner >> 1) * 2.0 - 1.0;
        float low = float(corner & 1) * 2.0 - 1.0;
        vec3 toCorner = vec3(high * low, high, low);
        gradient += toCorner * mapScene(p + toCorner * reach);
    }
    vec3 noSlope = vec3(0.0, 1.0, 0.0);                   // what a flat field (no gradient at all) reports
    return safeNormalize(gradient, noSlope);
}

// The normal epsilon at distance t: one pixel's footprint there, times a per-material scale (a bevel knob).
float nrmEps(float t, float pixelAngle, float materialScale) {
    float footprint = max(pixelAngle * t, 1e-5);
    return materialScale * footprint;
}

// The unit normal from six axis taps at offset |h|: the reference the tetrahedron is checked against.
vec3 nrmCentral(vec3 p, float h) {
    float reach = max(abs(h), 1e-7);
    int first = 6 * clamp(int(min(h, 0.0)), -1, 0);
    vec3 gradient = vec3(0.0);
    for (int tap = first; tap < 6; tap++) {
        int index = (tap + 6) % 6;
        int axis = index >> 1;
        float side = float(index & 1) * 2.0 - 1.0;
        vec3 toTap = side * vec3(float(axis == 0), float(axis == 1), float(axis == 2));
        gradient += toTap * mapScene(p + toTap * reach);
    }
    vec3 noSlope = vec3(0.0, 1.0, 0.0);
    return safeNormalize(gradient, noSlope);
}

// The Laplacian of mapScene at p from the tetrahedron taps and the centre: the corners' second-order terms sum to
// 2 h^2 times the Laplacian per four taps. On a distance field it is the sum of the principal curvatures.
float nrmCurvature(vec3 p, float h) {
    float reach = max(abs(h), 1e-7);
    int first = 4 * clamp(int(min(h, 0.0)), -1, 0);
    float around = 0.0;
    for (int tap = first; tap < 4; tap++) {
        int corner = (tap + 4) & 3;
        float high = float(corner >> 1) * 2.0 - 1.0;
        float low = float(corner & 1) * 2.0 - 1.0;
        around += mapScene(p + vec3(high * low, high, low) * reach);
    }
    float taps = float(4 - first);
    float centre = mapScene(p);
    return (around - taps * centre) / (0.5 * taps * reach * reach);
}

// n snapped to the nearest integer-lattice direction at `steps` divisions per unit, normalised: faceted light.
vec3 nrmFacet(vec3 n, float steps) {
    vec3 snapped = floor(n * steps + 0.5);
    return safeNormalize(snapped, n);
}
