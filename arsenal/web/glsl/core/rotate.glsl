//! {"name": "core-rotate", "kind": "helper", "cat": "A1", "family": "A", "version": "1.0.0", "order": 14,
//!  "license": "Apache-2.0",
//!  "credits": ["Patricio Gonzalez Vivo and Jen Lowe, The Book of Shaders, chapter 8 'Matrices' (https://thebookofshaders.com/08/): the 2D rotation matrix"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "rotate2(a) * p turns p counter-clockwise by a radians about the origin (p * rotate2(a) turns it clockwise). The matrix is orthonormal to float precision for every a, so lengths and angles survive any number of turns, and rotate2(a) * rotate2(b) equals rotate2(a + b).",
//!  "note": "Use the exact matrix, never the golfed spelling that builds it from cos of the angle plus a vector of constant offsets: the golf is a few thousandths of a radian off, which shows as a slow drift when many rotations compose (a kaleidoscope of nested folds, a tumbling camera). To spin a picture counter-clockwise, turn the point the other way: p = rotate2(-angle) * p. Wrong looks like a shape that shrinks or shears as it turns (a matrix that is not orthonormal), or a spin in the opposite direction (the matrix on the wrong side of the point).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "core-rotate.card", "twin": "arsenal/shaders/twins/core.py",
//!  "status": "P0", "exemplars": ["XtyXzW", "llVXRd", "XfXGz4", "7cjGRR", "l3cfW4"], "learn": ["PF 5.1"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics.
//
// WHY. Every loved shader rotates something, and three of them build the matrix from a golfed approximation. One
// exact rotation, written once, keeps every surface turning by the angle it asked for.

// The counter-clockwise rotation by a radians. GLSL fills a mat2 column by column: the first column is where the x
// axis goes (cos a, sin a), the second where the y axis goes (-sin a, cos a).
mat2 rotate2(float a) {
    float cosA = cos(a);
    float sinA = sin(a);
    return mat2(cosA, sinA, -sinA, cosA);
}
