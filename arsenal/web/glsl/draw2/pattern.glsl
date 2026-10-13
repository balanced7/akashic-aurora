//! {"name": "draw2-pattern", "kind": "helper", "cat": "C6", "family": "C", "version": "1.0.0", "order": 24,
//!  "license": "Apache-2.0",
//!  "credits": ["Hadyn, 'Pretty Hip' (https://www.shadertoy.com/view/XsBfRW): a delay per tile from the tile centre's distance, so a circular wave arrives as a mosaic of whole tiles",
//!   "Mercury, 'hg_sdf' (https://mercury.sexy/hg_sdf/): everything per copy derives from the id a domain operator returns"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "patCellDelay(cellId, centre, speed) = |cellId - centre| / speed, the speed floored at 1e-6 (a speed of zero or less is a wave that has not left yet: a very large, finite delay). cellId is any per-cell constant position in the units of centre and speed: latHex's centre (.zw) in lattice units, or domRepeat2's id in cells (then centre is in cells and speed in cells per unit of time). Every pixel of a cell gets the same delay, so t - patCellDelay(...) is that cell's own clock and the whole tile fires at once when the continuous front reaches the tile's centre.",
//!  "note": "The stadium wave on an LED wall: one animation, started later the farther each tile sits from the wave's origin, so a circular ripple arrives tile by tile and the front is quantised into a mosaic. Feed the cell's clock to an envelope (motion-envelope) and drive size, spin, brightness or colour from it; move the centre to a note's tile and the ripple starts there. Put any wrap of the clock (fract of the local time) where the cell is fully empty or fully lit, so the cut never shows (atlas craft secret 5). Wrong looks like a smooth circular front that slices through tiles (the delay taken from the pixel, not the cell), a front shaped like a square on a square grid (a Chebyshev distance: correct only if square fronts were wanted), or tiles flickering at the front (a derivative or an antialiasing width taken of the per-cell delay).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "draw2-pattern.card",
//!  "twin": "arsenal/shaders/twins/draw2.py", "status": "P0",
//!  "exemplars": ["XsBfRW", "llVXRd"],
//!  "learn": ["study:XsBfRW 6.4"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public pages credited above.
//
// WHY. Most tiled animation is one program run in every tile with a different start time, the way a phased-array
// antenna steers a beam with nothing but delays. Taking the delay from the tile's centre, not from the pixel, is the
// whole trick: the wave front stops being a smooth circle and becomes a staircase of whole tiles lighting together.

// How long after the wave leaves `centre` it reaches this cell, at `speed` units per unit of time.
float patCellDelay(vec2 cellId, vec2 centre, float speed) {
    return length(cellId - centre) / max(speed, 1e-6);
}
