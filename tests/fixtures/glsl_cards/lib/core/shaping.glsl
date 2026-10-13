//! {"name": "core-shaping", "kind": "helper", "cat": "core", "order": 10, "version": "0.1.0",
//!  "license": "Apache-2.0",
//!  "credits": ["Ken Perlin and Eric Hoffert, 'Hypertexture' (SIGGRAPH 1989): bias and gain as shaping curves"],
//!  "cost": "O(1)",
//!  "note": "TEST FIXTURE for tests/test_glsl_cards*.py, not the house module: three shaping curves on [0, 1]."}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics for the card tests; it stands in for
// core/shaping.glsl, which the library has not built yet.

// A linear 0-to-1 ramp from a to b, clamped: the edge a box filter makes.
float shpLinstep(float a, float b, float x) {
    float along = (x - a) / (b - a);   // 0 at a, 1 at b
    return clamp(along, 0.0, 1.0);
}

// Gain: two mirrored power curves that meet at the centre. k > 1 is an S, k < 1 an inverse S, k = 1 the diagonal;
// every k passes through 0, one half and 1. x is clamped first, because a negative base under pow() is undefined.
float shpGain(float x, float k) {
    float u = clamp(x, 0.0, 1.0);
    float nearEdge = min(u, 1.0 - u);
    float arm = 0.5 * pow(2.0 * nearEdge, k);
    return u < 0.5 ? arm : 1.0 - arm;
}

// An impulse: 0 at x = 0, rising to exactly 1 at x = 1/k, then decaying. With kx = k*x, kx * e^(1 - kx) peaks where
// kx = 1, and the peak is e^0 = 1.
float shpImpulse(float x, float k) {
    float kx = k * x;
    return kx * exp(1.0 - kx);
}
