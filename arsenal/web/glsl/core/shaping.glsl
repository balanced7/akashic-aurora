//! {"name": "core-shaping", "kind": "helper", "cat": "A5", "family": "A", "version": "1.0.0", "order": 16,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'Remapping functions' (https://iquilezles.org/articles/functions/): the impulse, the cubic pulse, gain, the parabola",
//!   "Patricio Gonzalez Vivo and Jen Lowe, The Book of Shaders, chapter 5 'Shaping functions' (https://thebookofshaders.com/05/): plotting a curve to see it; the linear, smooth and quintic ramps",
//!   "Ken Perlin, 'Improving Noise' (SIGGRAPH 2002, https://mrl.cs.nyu.edu/~perlin/paper445.pdf): the quintic fade 6t^5 - 15t^4 + 10t^3, flat in slope and curvature at both ends",
//!   "mrange, 'Starry planes' (https://www.shadertoy.com/view/MfjyWK, CC0): the smooth absolute value that rounds a mirror's crease",
//!   "alro, 'AURORA' (https://www.shadertoy.com/view/ttScDc, MIT): the inverse power as a soft threshold with enormous gain"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Each curve keeps the points its comment names. shpLinstep and shpSmoother ramp from 0 at a to 1 at b and clamp outside (b != a); shpSmoother is the quintic, flat in slope and curvature at both ends and exactly point-symmetric. shpImpulse is 0 at x = 0 and exactly 1 at x = 1/k (k > 0). shpPulse is 1 at centre and exactly 0 from halfWidth out. shpGain passes through 0, one half and 1 for every k > 0 (an S for k > 1, an inverse S below 1, the diagonal at 1). shpParabola is 0 at 0 and 1 and exactly 1 at one half, and 0 outside [0, 1]. shpSoftAbs is sqrt(x^2 + k): never below |x|, at most sqrt(k) above it. shpTri is 0 at whole numbers and 1 at halves. shpRemap maps a to c and b to d and does not clamp. shpInvPower is (r / d)^k, exactly 1 at d = r, held at or below 2^64 at the centre (d at or below 0) so it stays finite.",
//!  "note": "Most of the magic in the loved shaders is a well-chosen curve applied after a dull field (atlas craft secret 3): shape after the noise, never before, because contrast is a decision and not a property of the field. Pick the curve with the continuity its use downstream needs: anything you later antialias or light should be at least smooth in slope (shpSmoother, shpSoftAbs), because a crease becomes a visible line. shpRemap is the carving tool: remap a density so its soft edges fall below zero and only the cores stay (Cloud Ten). shpInvPower is the filament maker: (r / d)^k of a mild noise turns its valleys into hot hairlines, keep d off zero with an offset so the curve works on its steep flank (AURORA), and the same curve draws stars and glare. If you divide by a sum of shpTri waves, offset or clamp the sum: its valleys reach exactly 0. Wrong looks like a crease or band in a lit surface (a C0 curve where C1 was needed), a curve that never quite reaches 1, or a filament field that is all white (k too low or the offset gone).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "core-shaping.card", "twin": "arsenal/shaders/twins/shaping.py",
//!  "status": "P0", "exemplars": ["tsScDG", "ldSfWV", "MfjyWK", "XsjXRm", "Mts3zM", "ffG3Rc", "llK3Dy", "XtS3DD", "ttScDc"],
//!  "learn": ["PF 2", "NP 12", "VA 2.2", "VA 7.2", "study:ttScDc 6.3"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the articles credited above.
//
// WHY. A shaping curve bends one number into another, usually 0..1 into 0..1: the tone control of procedural art.
// Every ease, every falloff, every edge in the library is one of these, so each is written once, with the points it
// promises to keep, and pinned by a CPU twin at exactly those points.

// A straight ramp: 0 at a, 1 at b, clamped outside. The edge a box filter makes.
float shpLinstep(float a, float b, float x) {
    float along = x - a;
    float span = b - a;
    return clamp(along / span, 0.0, 1.0);
}

// The quintic ramp 10r^3 - 15r^4 + 6r^5 of the straight one: flat in slope and curvature at both ends, so stacked bands
// and watched motion never kick. Evaluated from whichever end is nearer (the curve is point-symmetric about one half),
// because straight through, 10 + r(6r - 15) cancels to about 1 near the top and float rounding makes it jitter.
float shpSmoother(float a, float b, float x) {
    float ramp = shpLinstep(a, b, x);
    float nearEnd = min(ramp, 1.0 - ramp);
    float tail = nearEnd * nearEnd * nearEnd * (10.0 + nearEnd * (6.0 * nearEnd - 15.0));
    return ramp < 0.5 ? tail : 1.0 - tail;
}

// A fast attack and a slow exponential release: k x e^(1 - k x) peaks at exactly 1 when x = 1/k.
float shpImpulse(float x, float k) {
    float reach = k * x;
    return reach * exp(1.0 - reach);
}

// A smooth bump, 1 at centre, falling as a cubic to exactly 0 at halfWidth and staying 0 beyond.
float shpPulse(float x, float centre, float halfWidth) {
    float spread = min(abs(x - centre) / max(halfWidth, 1e-9), 1.0);
    return 1.0 - spread * spread * (3.0 - 2.0 * spread);
}

// Gain: two mirrored power curves meeting at one half. k > 1 is an S (contrast up), k < 1 an inverse S (contrast down),
// k = 1 the diagonal; 0, one half and 1 never move. Input clamped to [0, 1] first (a negative base under pow is undefined).
float shpGain(float x, float k) {
    float u = clamp(x, 0.0, 1.0);
    float arm = 0.5 * pow(2.0 * min(u, 1.0 - u), k);
    return u < 0.5 ? arm : 1.0 - arm;
}

// A bump on [0, 1]: (4 x (1 - x))^k, 1 at the middle, 0 at both ends and outside. k = 2 is the Welch window, the bell
// Oscillo Donut weights its beam with; larger k is narrower.
float shpParabola(float x, float k) {
    float bump = 4.0 * x * (1.0 - x);
    return pow(max(bump, 0.0), k);
}

// |x| with its crease rounded: sqrt(x^2 + k). Use it in mirrors and turbulence, where abs() makes a sharp line and
// high frequencies. It lifts |x| by sqrt(k) at the crease and by almost nothing far from it.
float shpSoftAbs(float x, float k) {
    float squared = x * x;
    return sqrt(squared + k);
}

// A triangle wave of period 1: 0 at whole numbers, 1 at halves, straight lines between.
float shpTri(float x) {
    float cycle = fract(x);
    return 1.0 - abs(2.0 * cycle - 1.0);
}

// The straight line through (a, c) and (b, d), not clamped: refit a range, or carve a density so that what falls
// below c's side vanishes and the cores stay.
float shpRemap(float v, float a, float b, float c, float d) {
    float along = (v - a) / (b - a);
    return c + along * (d - c);
}

// (r / d)^k: exactly 1 at d = r, enormous gain below it, a long fade above it. Computed as exp2(k log2(r / d)), which is
// what pow does inside, with r and d floored at 1e-30 (d at or below 0 is the centre itself) and the exponent held at
// 64, so the centre is 2^64 rather than Inf and sums of thousands of these stay finite.
float shpInvPower(float d, float r, float k) {
    float ratio = max(r, 1e-30) / max(d, 1e-30);
    return exp2(min(k * log2(ratio), 64.0));
}
