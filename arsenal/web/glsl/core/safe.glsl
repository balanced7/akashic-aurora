//! {"name": "core-safe", "kind": "helper", "cat": "A1", "family": "A", "version": "1.0.0", "order": 12,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, '2D distance functions' (https://iquilezles.org/articles/distfunctions2d/): dot2, the squared length his distance formulas lean on",
//!   "Fabrice Neyret, 'Compatibility issues in Shadertoy / webGLSL' (https://shadertoyunofficial.wordpress.com/2016/07/22/compatibility-issues-in-shadertoy-webglsl/): clamp of a NaN came out 0 on one driver and 1 on another, so a guard must stand before the NaN, not after it",
//!   "Emil Persson, 'Low-level thinking in shader code' (GDC 2013, http://www.humus.name/Articles/Persson_LowLevelThinking.pdf): a compiler may assume NaN never happens and fold a NaN test away, which is why finiteOr tests the bits",
//!   "Khronos, the GLSL ES 3.00 specification, section 8 (https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf): the inputs that leave sqrt, pow and acos undefined"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Every function is defined for every finite input. dot2 is dot(v, v). safeDiv divides n by d with |d| floored at eps (eps > 0) and its sign kept, zero counting as positive, so it is finite while |n| / eps is. safeNormalize returns v / |v| when dot(v, v) > 1e-24 and the fallback otherwise (honest for |v| below about 1e19, where dot(v, v) itself overflows). safeSqrt and safeAcos clamp into their domain first; safePow floors the base at 1e-30, so it is defined everywhere but a tiny base under a negative exponent can still overflow to Inf. finiteOr swaps each NaN or Inf component of v for the fallback's, by an exponent-bit test a compiler cannot fold away.",
//!  "note": "The fuses on the power rail. NaN is contagious in a feedback loop: next frame's blur spreads one pixel's NaN to its neighbours and the black blob grows for ever, because no arithmetic turns a NaN back into a number. In any pass that writes a buffer it reads back, guard every normalise, divide, root and power at the source, and make finiteOr the last thing before the write. Wrong looks like a black or white speck that grows every frame, or black pixels exactly where a direction is zero: the centre of a radial pattern, the pole of a sphere, the axis of a twist.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "core-safe.card", "twin": "arsenal/shaders/twins/core.py",
//!  "status": "P0", "exemplars": ["XsSGDh", "NslGRN", "43jXWt", "ldSfWV", "WlVyRV"],
//!  "learn": ["SR 12.2", "GP 5.8", "WS 1.4"]}
// Apache-2.0, Akashic Aurora. Written fresh from the GLSL ES 3.00 specification and the articles credited above.
//
// WHY. The specification leaves sqrt of a negative, pow of a negative base and acos beyond [-1, 1] undefined, and the
// classic sources of NaN are rounding a hair past those edges: a dot product of unit vectors that comes out
// 1.0000001, a discriminant that should be zero and comes out -1e-9, a direction of length zero. On a still image a
// NaN is one bad pixel; in a feedback buffer it is a hole that eats the picture.

// The squared length. Compare distances with it, or let a formula take one square root at the very end.
float dot2(vec2 v) {
    float lengthSq = dot(v, v);
    return lengthSq;
}

float dot2(vec3 v) {
    float lengthSq = dot(v, v);
    return lengthSq;
}

// n / d with the denominator kept at least eps away from zero, on the side its sign says (zero counts as positive).
float safeDiv(float n, float d, float eps) {
    float awayFromZero = d < 0.0 ? min(d, -eps) : max(d, eps);
    return n / awayFromZero;
}

// The unit vector along v, or the fallback when v is too short to have a direction (dot(v, v) at or below 1e-24).
vec2 safeNormalize(vec2 v, vec2 fallback) {
    float lengthSq = dot(v, v);
    return lengthSq > 1e-24 ? v * inversesqrt(lengthSq) : fallback;
}

vec3 safeNormalize(vec3 v, vec3 fallback) {
    float lengthSq = dot(v, v);
    return lengthSq > 1e-24 ? v * inversesqrt(lengthSq) : fallback;
}

// sqrt of a value that should be >= 0 but may have been rounded a hair below it.
float safeSqrt(float x) {
    float clipped = max(x, 0.0);
    return sqrt(clipped);
}

// acos of a cosine that rounding may have pushed past 1 or -1 by an ulp.
float safeAcos(float x) {
    float cosine = clamp(x, -1.0, 1.0);
    return acos(cosine);
}

// pow with the base floored at 1e-30: 0^0 becomes 1 and a negative base acts as zero, instead of undefined.
float safePow(float b, float e) {
    float base = max(b, 1e-30);
    return pow(base, e);
}

// Each component of v that is NaN or Inf replaced by the same component of fallback. An IEEE float is non-finite
// exactly when its eight exponent bits are all ones; an integer test of those bits survives a compiler that assumes
// finite maths, where isnan() and isinf() may not. mix() with a bool vector selects; it does no arithmetic, so the
// NaN it drops cannot leak into the result.
vec4 finiteOr(vec4 v, vec4 fallback) {
    ivec4 exponentBits = floatBitsToInt(v) & 0x7f800000;
    bvec4 broken = equal(exponentBits, ivec4(0x7f800000));
    return mix(v, fallback, broken);
}
