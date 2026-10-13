//! {"name": "draw2-aa", "kind": "helper", "cat": "C2", "family": "C", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Fabrice Neyret, 'Advanced tricks' in Shadertoy Unofficial (https://shadertoyunofficial.wordpress.com/2021/03/09/advanced-tricks/): antialiasing is easy in 2D as long as shapes are distances",
//!   "Emil Persson, 'Graphics Gems for Games', phone-wire AA (https://www.humus.name/Articles/Persson_GraphicsGemsForGames.pdf): clamp a wire to one pixel and fade it by true over drawn width",
//!   "Inigo Quilez, 'distance' (https://iquilezles.org/articles/distance/): a non-distance field over its gradient is a distance near its zero set, so its threshold can be filtered at constant pixel width"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Coverage in [0, 1] of one pixel, for a straight edge under a box filter one pixel wide; px is the pixel size in the distance's own units (uvPixel, or uvFootprint of a warped domain) and is floored at 1e-6. aaFill(d, px) = clamp(0.5 - d / px, 0, 1): 0.5 on the edge, 1 half a pixel inside. aaStroke covers the band |d| <= halfWidth as fill(d - halfWidth) - fill(d + halfWidth), so its ink (summed across the line) is exactly 2 halfWidth and a band thinner than a pixel dims instead of breaking; a negative halfWidth is no band. aaWire(d, widthPx, px) draws a line of true width widthPx pixels at max(widthPx, 1) pixels and opacity widthPx / that, so its ink is always widthPx pixels and it stays connected. aaStep(x, edge) is a smoothstep from edge - f to edge + f, f the length of (dFdx(x), dFdy(x)) floored at 1e-30, so a flat x is a clean hard step; honest only for a continuous x in uniform control flow.",
//!  "note": "The pen of the house: every edge goes through one of these so that 'pixel perfect, un-aliased' (Daniel's ruling R4) is one module's job. Mix colours by coverage in linear light and encode once at the end; mixed in sRGB, light-on-dark edges look thin and dark-on-light ones bold. Pass the pixel size measured BEFORE any fold, tile or wrap (shader-craft floor 6). Use aaStroke for outlines of a set width in world units, aaWire for hairlines whose width is in pixels (grids, isolines, Truchet strokes, the neon line's core), aaStep for thresholds of non-distance fields (noise, a wipe, a mask), never on a cell id. Wrong looks like jaggies or edges whose softness changes with the canvas size (px forgotten or constant), hairlines that break into flickering dots (a step instead of aaWire), lines bolder on diagonals (fwidth's L1 width, not the Euclidean one), or two-pixel seams along tile borders (a derivative of a wrapped value).",
//!  "targets": {"glsl": "300es", "needs": ["derivatives"]}, "card": "draw2-aa.card",
//!  "twin": "arsenal/shaders/twins/draw2.py", "status": "P0",
//!  "exemplars": ["Xt3yDS", "Mts3zM", "wsl3WB", "XsBfRW"],
//!  "learn": ["PF 4.3", "PF 4.5", "NP 12"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. A pixel is a little square, not a point. Sampling a hard edge at the pixel centre gives stairs that crawl in
// motion, the wagon wheel turning backwards on film. The cure is the audio engineer's: filter before you sample. A
// signed distance makes the filter one line, because it is already measured in the units of the pixel: the fraction
// of a pixel-wide window on the inside of a straight edge is a ramp one pixel long, centred on the edge.

// The covered fraction of the inside (d < 0) of a straight edge: a linear ramp one pixel long, centred on d = 0.
float aaFill(float d, float px) {
    float pixel = max(px, 1e-6);
    return clamp(0.5 - d / pixel, 0.0, 1.0);
}

// The covered fraction of the band |d| <= halfWidth: inside its outer edge, minus inside its inner edge.
float aaStroke(float d, float halfWidth, float px) {
    float band = max(halfWidth, 0.0);                      // ("half" is a reserved word in GLSL ES)
    return aaFill(d - band, px) - aaFill(d + band, px);
}

// A line widthPx pixels wide that never draws thinner than one pixel: below that it keeps the one-pixel footprint
// and dims by the ratio of its true width to the drawn one, so its total light is right and it never breaks up.
float aaWire(float d, float widthPx, float px) {
    float trueWidth = max(widthPx, 0.0);
    float drawnWidth = max(trueWidth, 1.0);
    return aaStroke(d, 0.5 * drawnWidth * px, px) * (trueWidth / drawnWidth);
}

// A threshold of any continuous field x at edge, softened over the field's own change across one pixel (the length
// of its screen derivatives, not fwidth, which reads up to 41 percent wide on diagonals). The smoothstep is written
// out so a flat field (no change at all) is a clean step instead of smoothstep's undefined equal edges.
float aaStep(float x, float edge) {
    float acrossX = dFdx(x);
    float acrossY = dFdy(x);
    float footprint = max(sqrt(acrossX * acrossX + acrossY * acrossY), 1e-30);
    float rise = clamp((x - edge) / (2.0 * footprint) + 0.5, 0.0, 1.0);
    return rise * rise * (3.0 - 2.0 * rise);
}
