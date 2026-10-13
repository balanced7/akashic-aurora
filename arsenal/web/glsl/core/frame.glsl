//! {"name": "core-frame", "kind": "helper", "cat": "A4", "family": "A", "version": "1.0.0", "order": 14,
//!  "license": "Apache-2.0",
//!  "credits": ["Patricio Gonzalez Vivo and Jen Lowe, The Book of Shaders, chapter 5 'Shaping functions' (https://thebookofshaders.com/05/): the normalised, aspect-correct frame",
//!   "Sebastien Durand, 'Isoline Simple' (https://www.shadertoy.com/view/Ms2XWc): the Euclidean length of the derivative pair, not fwidth, for an even line weight"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "uvCentered(fragCoord, res) puts the origin at the canvas centre with y from -1 at the bottom to 1 at the top and x scaled by the same factor (aspect-true, y up). uvPixel(res) is the size of one pixel in those units, 2 / res.y, exact for any domain that has only been shifted, rotated or uniformly scaled. uvFootprint(p) is the larger of the lengths of p's screen derivatives along x and y: the pixel size of any continuous coordinate, honest only for continuous p and only in uniform control flow (outside a branch that splits a 2 by 2 pixel quad).",
//!  "note": "Write the pixel size down once and carry it everywhere: every antialiased edge, every one-pixel line, every fade of detail too fine to show needs it. uvPixel is free and steady for an unwarped domain. For a warped one (polar, folded, inverted, displaced by noise) measure it with uvFootprint, and measure BEFORE you fold: pass the continuous coordinate, never fract(p) or a cell id, because the derivative of a jump is a spike and a whole row of pixels shreds (shader-craft floor 6). The derivative is taken over a 2 by 2 pixel quad, so it is two pixels coarse. Wrong looks like circles that are ellipses (x and y divided by different sizes), edges whose softness changes with resolution, or bright two-pixel lines along every tile border.",
//!  "targets": {"glsl": "300es", "needs": ["derivatives"]}, "card": "core-frame.card",
//!  "twin": "arsenal/shaders/twins/core.py", "status": "P0", "exemplars": ["Mts3zM", "Xt3yDS", "Ms2XWc", "ltdcW7"],
//!  "learn": ["PF 1", "PF 4.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the articles credited above.
//
// WHY. Every 2D effect starts by turning a pixel position into coordinates it can reason about, and then needs to
// know how big one pixel is in those coordinates. Get the first wrong and circles squash; get the second wrong and
// edges crawl, blur or vanish as the canvas changes size.

// The house 2D frame: origin at the centre, y up, the canvas height spanning -1 to 1, x scaled by the same factor.
vec2 uvCentered(vec2 fragCoord, vec2 res) {
    vec2 fromCentre = fragCoord - 0.5 * res;
    return fromCentre * (2.0 / res.y);
}

// One pixel in uvCentered units: the height spans 2 units over res.y pixels.
float uvPixel(vec2 res) {
    return 2.0 / res.y;
}

// The pixel size of a continuous coordinate p: how far p moves to the next pixel, along whichever screen axis moves
// it further. The Euclidean length, not fwidth (fwidth adds the two axes and reads up to 41 percent wide on diagonals).
float uvFootprint(vec2 p) {
    vec2 acrossX = dFdx(p);
    vec2 acrossY = dFdy(p);
    float widestSq = max(dot(acrossX, acrossX), dot(acrossY, acrossY));
    return sqrt(widestSq);
}
