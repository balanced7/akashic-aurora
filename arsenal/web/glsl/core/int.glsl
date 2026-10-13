//! {"name": "core-int", "kind": "helper", "cat": "A2", "family": "A", "version": "1.0.0", "order": 12,
//!  "license": "Apache-2.0",
//!  "credits": ["Fabrice Neyret, 'Compatibility issues in Shadertoy / webGLSL' (https://shadertoyunofficial.wordpress.com/2016/07/22/compatibility-issues-in-shadertoy-webglsl/): -3 % 4 measured as 1 on OpenGL and -3 on Windows/ANGLE",
//!   "Khronos, the GLSL ES 3.00 specification, section 5.9 (https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf): % is undefined when an operand is negative, and int() truncates toward zero"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "imodFloor(a, b) is the floor modulo, in [0, b) for every sign of a, computed with % only on non-negative operands (the one case GLSL defines); b below 1 is read as 1. The ivec2 forms work per component. cellIndex(x) is int(floor(x)), the cell x lies in, honest while |x| < 2^31 (and exact cell edges need |x| < 2^24, where floats still hold every integer).",
//!  "note": "Tilings that reach negative coordinates need these. The % operator is undefined for a negative operand and really does differ between drivers, and int(-0.5) is 0 (it truncates toward zero), so a naive tiling draws a double-width tile at the origin and repeats in the wrong order to its left. Dry Ice adds 100 before converting to dodge the same trap; these make the dodge unnecessary. Wrong looks like a seam, a doubled cell or a pattern that reverses exactly at x = 0 or y = 0.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "core-int.card", "twin": "arsenal/shaders/twins/core.py",
//!  "status": "P0", "exemplars": ["WlVyRV"], "learn": ["GP 5.9"]}
// Apache-2.0, Akashic Aurora. Written fresh from the GLSL ES 3.00 specification.
//
// WHY. A tile pattern is a grid of cells numbered by integers, and the numbering has to keep counting through zero
// the same way it counts everywhere else: ..., -2, -1, 0, 1, ... with the colour cycle unbroken. GLSL's own integer
// tools break exactly there, and differently on different machines.

// Floor modulo for b >= 1: the result is in [0, b) for any a. For a < 0 it counts down from the top of the period:
// -1 maps to b - 1, -b to 0. a + 1 is taken before negating so the most negative int does not overflow.
int imodFloor(int a, int b) {
    int period = max(b, 1);
    if (a >= 0) {
        return a % period;
    }
    int stepsBelowZero = -(a + 1);
    return period - 1 - stepsBelowZero % period;
}

ivec2 imodFloor(ivec2 a, ivec2 b) {
    return ivec2(imodFloor(a.x, b.x), imodFloor(a.y, b.y));
}

ivec2 imodFloor(ivec2 a, int b) {
    return ivec2(imodFloor(a.x, b), imodFloor(a.y, b));
}

// The cell a coordinate lies in: floor first, so -0.5 is in cell -1 (int() alone would say 0).
int cellIndex(float x) {
    float cellStart = floor(x);
    return int(cellStart);
}
