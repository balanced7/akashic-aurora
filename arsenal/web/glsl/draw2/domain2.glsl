//! {"name": "draw2-domain2", "kind": "helper", "cat": "C4", "family": "C", "version": "1.0.0", "order": 22,
//!  "license": "Apache-2.0",
//!  "credits": ["Mercury, 'hg_sdf' (https://mercury.sexy/hg_sdf/): domain operators change the point in place and return the cell or sector index",
//!   "Inigo Quilez, 'domain repetition' (https://iquilezles.org/articles/sdfrepetition/): centred repetition and its limits, angular repetition",
//!   "Patricio Gonzalez Vivo and Jen Lowe, The Book of Shaders, chapter 7 'Shapes' (https://thebookofshaders.com/07/): polar coordinates as a drawing space"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "domToPolar(p) is (|p|, angle) with the angle in (-pi, pi] from +x counter-clockwise; at the origin the angle is 0 (atan(0, 0) is undefined in GLSL). domFromPolar inverts it, as exactly as the GPU's atan, sin and cos allow (the round trip lands within about 1e-4 of the radius on SwiftShader, 1e-7 in the twin). domRepeat2(p, period) sets id = floor(p / period + 0.5), moves p to p - id * period, in [-period / 2, period / 2) about the cell centre, and returns id (whole numbers, constant over each cell); the period is floored at 1e-6 per axis. domKaleido(p, sectors) splits the turn into n = max(round(sectors), 1) sectors of width TAU / n, sector 0 centred on +x; it replaces p's angle by the absolute angle from its sector's centre line (keeping |p|), so the folded p lies between angle 0 and half a sector and neighbouring sectors are mirror images, and returns the sector index in [0, n). The repetition is exact for a shape that stays inside its cell (a larger or offset one needs its neighbours evaluated); the fold is exact for a shape symmetric about the sector's centre line.",
//!  "note": "Draw once, see it everywhere: these move the pixel into one cell or one wedge, so a shape drawn about the origin appears in every cell for the price of one, and the returned id is what lets each copy differ (hash it for a colour, a size, a delay; the house kaleido and tile chunks threw it away). The cell id is constant and jumps between cells: never take its derivative or fwidth it (shader-craft floor 6); measure the pixel size on the coordinate before the fold. Angular stripes thin toward the centre (their pixel width is r times the angle). Wrong looks like a shape cut by a straight line at the cell border (bigger than its cell: evaluate the neighbours), a hairline seam along every mirror (lit or antialiased content that is not symmetric about the fold), a seam along the negative x axis (an angle that is not wrapped), or a black dot at the centre (atan of the origin).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "draw2-domain2.card",
//!  "twin": "arsenal/shaders/twins/draw2.py", "status": "P0",
//!  "exemplars": ["MdsXWM", "Mts3zM", "MtXczn", "XsBfRW", "ltffzl", "wsl3WB"],
//!  "learn": ["PF 5.1", "PF 6.1", "PF 5.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. Most of the repetition in a picture is the coordinate's doing, not the shape's. Fold or wrap the coordinate
// first and a single shape becomes a wallpaper, a ring of copies or a snowflake, at the cost of one. The house
// convention (hg_sdf's): an operator changes the point in place and hands back which cell or sector it came from.

// (radius, angle). The angle runs counter-clockwise from +x in (-pi, pi]; the origin's angle is defined as 0.
vec2 domToPolar(vec2 p) {
    bool origin = p.x == 0.0 && p.y == 0.0;
    float angle = atan(p.y, origin ? 1.0 : p.x);
    angle = angle <= -PI ? PI : angle;                 // -pi and pi are one direction: keep the closed end
    return vec2(length(p), angle);
}

// The point at radius ra.x and angle ra.y.
vec2 domFromPolar(vec2 ra) {
    return ra.x * vec2(cos(ra.y), sin(ra.y));
}

// Centred repetition: p becomes its position within its cell (origin at the cell centre) and the cell's id returns.
vec2 domRepeat2(inout vec2 p, vec2 period) {
    vec2 size = max(period, vec2(1e-6));
    vec2 cell = floor(p / size + 0.5);
    p -= cell * size;
    return cell;
}

// The mirrored kaleidoscope: p's angle becomes its distance in angle from the centre line of its sector, so every
// sector holds the same picture and each sector is the mirror image of its neighbours. Returns the sector, 0 to n - 1.
float domKaleido(inout vec2 p, float sectors) {
    float count = max(floor(sectors + 0.5), 1.0);
    float width = TAU / count;
    vec2 ra = domToPolar(p);
    float sector = floor(ra.y / width + 0.5);
    p = domFromPolar(vec2(ra.x, abs(ra.y - sector * width)));
    return sector - count * floor(sector / count);
}
