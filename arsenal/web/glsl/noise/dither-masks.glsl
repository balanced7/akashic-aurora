//! {"name": "dither-masks", "kind": "helper", "cat": "B7", "family": "B", "version": "1.0.0", "order": 12,
//!  "license": "Apache-2.0",
//!  "credits": ["Jorge Jimenez, 'Next Generation Post Processing in Call of Duty: Advanced Warfare' (SIGGRAPH 2014, http://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare): interleaved gradient noise",
//!   "Alan Wolfe, 'Interleaved Gradient Noise: A Different Kind of Low Discrepancy Sequence' (https://blog.demofox.org/2022/01/01/interleaved-gradient-noise-a-different-kind-of-low-discrepancy-sequence/): the 3x3 'sudoku' property",
//!   "Martin Roberts, 'The Unreasonable Effectiveness of Quasirandom Sequences' (https://extremelearning.com.au/unreasonable-effectiveness-of-quasirandom-sequences/): the R2 sequence as a dither mask",
//!   "Stanley Lipshitz, Robert Wannamaker and John Vanderkooy, 'Quantization and Dither: A Theoretical Survey' (JAES 1992, https://www.aes.org/e-lib/browse.cfm?elib=7047): why triangular dither"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Static per-pixel masks in [0, 1) that depend on nothing but the pixel: dthIgn is Jimenez's fract(52.9829189 * fract(0.06711056 x + 0.00583715 y)), whose every 3x3 block holds nearly all ninths; dthR2 is Roberts' R2 on the integer pixel, fract(x / rho + y / rho^2) with rho the plastic number, each axis reduced before the sum so 32-bit floats stay within a few ten-thousandths out to an 8K canvas. dthTriFromUniform is the triangle distribution's inverse CDF: [0, 1) to [-1, 1), monotone, so a mask keeps its spatial pattern while its histogram becomes a triangle (mean 0, variance 1/6). GLSL ES 1.00 safe.",
//!  "note": "Two jobs share these masks: the start jitter of a ray march (march banding becomes fine grain: offset the first step by mask * step) and the output dither (post-dither calls dthIgn and dthTriFromUniform). Static on purpose: per-frame dither is crawling grain, which Daniel had removed (shader-craft floor 8); a frame-animated mask is only for a host that accumulates frames. IGN can show faint diagonal structure on a high-contrast dark ramp; R2 is the even alternative. Never use one mask value for two decisions in one pixel. Wrong looks like contour bands in a dark gradient (no dither, or dither before an 8-bit buffer), a visible crosshatch (an ordered matrix), or grain that crawls when nothing moves (a clock in the mask).",
//!  "targets": {"glsl": "100", "needs": []}, "card": "dither-masks.card",
//!  "twin": "arsenal/shaders/twins/noise.py", "status": "P0", "exemplars": ["ffG3Rc"],
//!  "learn": ["NP 13", "NP 13.2", "NP 13.3"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. An 8-bit screen is a staircase of 256 steps, and a slow dark gradient shows each step as a band. Dither is the
// audio engineer's trick: add a whisper of noise before the rounding, so the error turns into fine grain the eye
// averages away. The noise must be EVEN (no clumps the eye can see) and STILL (the house rule: grain that moves when
// nothing else does is a fault), so these masks are pure functions of the pixel, like a memory interleave stride
// chosen so no two nearby requests hit the same bank.

// Jimenez's interleaved gradient noise in [0, 1). pixel: the fragment coordinate (centres or integers both work).
float dthIgn(vec2 pixel) {
    float ramp = fract(dot(vec2(0.06711056, 0.00583715), pixel));
    return fract(52.9829189 * ramp);
}

// Roberts' R2 low-discrepancy mask in [0, 1): a two-dimensional golden-ratio stride on the integer pixel.
float dthR2(vec2 pixel) {
    vec2 cell = floor(pixel);
    float along = fract(cell.x * 0.75487766625);           // 1 / rho, rho = 1.32471795724 (x^3 = x + 1)
    float across = fract(cell.y * 0.56984029100);          // 1 / rho^2
    return fract(along + across);
}

// A uniform u in [0, 1) as a triangular value in [-1, 1) of the same rank (the inverse of the triangle's CDF). u is
// clamped to [0, 1] first, so a value a hair outside never becomes a NaN under the square root.
float dthTriFromUniform(float u) {
    float v = clamp(u, 0.0, 1.0);
    return v < 0.5 ? sqrt(2.0 * v) - 1.0 : 1.0 - sqrt(2.0 - 2.0 * v);
}
