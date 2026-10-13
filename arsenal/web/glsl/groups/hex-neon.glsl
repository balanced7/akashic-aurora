//! {"name": "hex-neon", "kind": "recipe", "cat": "C5", "family": "C", "version": "1.0.0", "order": 62,
//!  "license": "Apache-2.0",
//!  "credits": ["Martijn Steinrucken (The Art of Code), 'Hexagone' (https://www.shadertoy.com/view/wsl3WB): size-coupled spin, rings that pulse from the centre, a shape larger than its cell seen from the six neighbours (the technique, read in words; no code taken)",
//!   "Hadyn, 'Pretty Hip' (https://www.shadertoy.com/view/XsBfRW): a delay per tile from the tile centre's distance, so the wave arrives as a mosaic of whole tiles (read in words)",
//!   "Hex Glitch study (https://www.shadertoy.com/view/lfscD7): constant pen width while cells change size, and XOR as a graphic combine (read in words)",
//!   "Amit Patel, Red Blob Games, 'Hexagonal Grids' (https://www.redblobgames.com/grids/hexagons/): axial coordinates and the six neighbours",
//!   "Leonhard Euler's Tonnetz and the harmonic table note layout (https://en.wikipedia.org/wiki/Tonnetz): fifths along one axis and major thirds along the next, so a chord is a small cluster of cells"],
//!  "cost": {"class": "C1", "loop": "7 cells per pixel (own cell and six neighbours), each one sd2Hexagon, one hash and one palette lookup where it shows; palette 1 adds palPitchFifths' searches per visible cell", "tex": 0},
//!  "entry": "vec3 hexNeon(vec2 p, float px, float t, vec2 origin, float cellSize, float lineWidth, float haloPx, float waveSpeed, float sizeAmp, float spin, int palette, float accent, int combine, int view)",
//!  "params": [
//!   {"name": "cellSize", "label": "Cell size", "unit": "world", "range": [0.05, 1], "default": 0.28, "step": 0.01, "group": "tiling",
//!    "uniform": "u_hexNeon_cellSize", "help": "The distance between neighbouring cell centres, in the units of p (the house frame is 2 tall)."},
//!   {"name": "lineWidth", "label": "Line width", "unit": "px", "range": [0.5, 6], "default": 1.5, "step": 0.1, "group": "line",
//!    "uniform": "u_hexNeon_lineWidth", "help": "The outline's width in screen pixels, the same for big cells and small ones; below a pixel it dims instead of breaking."},
//!   {"name": "haloPx", "label": "Glow", "unit": "px", "range": [0, 24], "default": 4.5, "step": 0.5, "group": "line",
//!    "uniform": "u_hexNeon_haloPx", "help": "How far each outline's glow reaches, in screen pixels (a Gaussian skirt, so the space between cells stays dark); 0 is bare lines."},
//!   {"name": "waveSpeed", "label": "Wave speed", "unit": "per-sec", "range": [0, 4], "default": 0.6, "step": 0.05, "group": "motion",
//!    "uniform": "u_hexNeon_waveSpeed", "help": "How many cells per second the swell travels out from the origin. Every cell starts when the wave reaches its centre, so the front arrives tile by tile."},
//!   {"name": "sizeAmp", "label": "Size swing", "unit": "ratio", "range": [0, 1], "default": 0.55, "step": 0.01, "group": "motion",
//!    "uniform": "u_hexNeon_sizeAmp", "help": "How much each hexagon breathes around its rest size. Past about 0.6 the biggest overlap their neighbours."},
//!   {"name": "spin", "label": "Spin coupling", "unit": "turns", "range": [0, 1], "default": 0.35, "step": 0.01, "group": "motion",
//!    "uniform": "u_hexNeon_spin", "help": "Turns of twist per unit of size change: growing and turning are one gesture, like an iris. 0 keeps every hexagon upright."},
//!   {"name": "palette", "label": "Palette", "unit": "choice", "group": "colour", "default": 0, "uniform": "u_hexNeon_palette",
//!    "choices": [{"value": 0, "label": "Neon (cool, with a coral accent)"}, {"value": 1, "label": "Pitch (harmonic table)"}],
//!    "help": "Neon: an analogous cool family from cyan to violet, a few cells coral. Pitch: the house note colours laid out as a harmonic table, a fifth to the right and a major third up and to the right, so a chord lights a small cluster."},
//!   {"name": "accent", "label": "Coral accent", "unit": "ratio", "range": [0, 0.5], "default": 0.1, "step": 0.01, "group": "colour",
//!    "uniform": "u_hexNeon_accent", "help": "The share of cells drawn coral in the Neon palette: one warm accent among cool cells."},
//!   {"name": "combine", "label": "Combine", "unit": "choice", "group": "colour", "default": 0, "uniform": "u_hexNeon_combine",
//!    "choices": [{"value": 0, "label": "Add (light)"}, {"value": 1, "label": "Max (crisp)"}, {"value": 2, "label": "XOR (graphic)"}],
//!    "help": "How neighbouring cells meet. Add: overlapping glows brighten, as light does. Max: an overlap is no brighter than one cell. XOR: filled hexagons whose overlaps cancel, a printed, op-art look."},
//!   {"name": "view", "label": "Debug view", "unit": "choice", "group": "debug", "default": 0, "uniform": "u_hexNeon_view",
//!    "choices": [{"value": 0, "label": "Picture"}, {"value": 1, "label": "Cells"}],
//!    "help": "Cells colours each cell by its id with its border drawn, to check the tiling and its numbering."}],
//!  "contract": "hexNeon(p, px, t, origin, ...) is linear HDR light (tonemap after) for a point p of a plane whose pixel size is px in the same units, at time t. The plane is tiled by latHex at cellSize (pointy-top hexagons, centres cellSize apart). Each cell is posed by its centre alone (hexNeonPose): its swell is hexNeonSwell(t - patCellDelay(centre, origin, waveSpeed), hash21 of its axial id), in [0, 1]; its hexagon has inradius 0.36 (1 + sizeAmp' 0.65 (2 swell - 1)) cells with sizeAmp' = clamp(sizeAmp, 0, 1), turned by TAU spin (size / rest size - 1) radians. The outline is aaWire of sd2Hexagon at lineWidth pixels, the glow glowExp of the squared distance in pixels beyond the line at 1 / haloPx^2, a Gaussian skirt (none at haloPx 0); a cell shines energy (0.04 + 0.96 swell^3) times (1.5 line + 0.35 glow) in its colour (hexNeonColour: palette 0 the cool cosine family with a share `accent` of cells coral, chosen by the low bits of the same hash; palette 1 palPitchFifths of (7q + 4r) mod 12 for axial (q, r)). Every pixel evaluates its own cell and the six neighbours, and each cell's light and fill fade to nothing between 0.8 and 1.15 cells from its centre, so the picture is continuous across every border for any knob. combine 0 adds the cells, 1 takes the per-channel max, 2 XORs their filled hexagons (cmpXor of aaFill coverages) and colours the ink by the coverage-weighted mean of their colours. view 1 returns dbgCells with the hexagon borders, decoded to linear. Lines keep lineWidth pixels for any cellSize and canvas; everything is finite and non-negative.",
//!  "note": "One id drives everything (atlas craft secret 10): the hash of a cell's axial pair sets its colour, its accent and the detune of its breathing, and the wave's arrival is its centre's distance, so whole tiles fire together and the front is a mosaic. Spin is coupled to size, so a swelling hexagon twists like an iris instead of merely pulsing. Feed p from the unwarped frame (uvCentered) with px from uvPixel, or a floor's coordinates with its footprint; move origin to a note's cell and the ring starts there. The Pitch palette lays the twelve note colours as a harmonic table: a step right is a fifth, up and right a major third, up and left a minor third, so a triad is a triangle of three cells and a key is a stripe. Keep the halo small next to the cell size: a glow wider than about a third of a cell is faded where it would leave the seven-cell neighbourhood. Wrong looks like outlines that thicken on a big canvas (px not from the unwarped frame), straight cuts through the glow along cell borders (a neighbour missing from the pass), a front that slices through tiles (a delay from the pixel, not the centre), cells sharing a colour along a row (the raw centre hashed), or flat-topped hexagons.",
//!  "debug": ["cells"],
//!  "targets": {"glsl": "300es", "needs": ["uint"]}, "card": "hex-neon.card",
//!  "twin": "arsenal/shaders/twins/hex_neon.py", "status": "P0",
//!  "exemplars": ["wsl3WB", "NlK3Wt", "lfscD7", "XsBfRW", "llVXRd"],
//!  "learn": ["atlas 16.7", "craft secret 5", "craft secret 10", "study:wsl3WB 4.3", "study:wsl3WB 4.6", "study:XsBfRW 5.4", "study:lfscD7 5.4", "study:lfscD7 5.5"]}
// Apache-2.0, Akashic Aurora. Written fresh: a wiring of house parts, each credited in its own module.
//
// WHY. A stadium full of cards held up row by row: each seat is told only when to lift, and the picture travels.
// Here each cell is told only its centre and its die; from those it knows when the wave reaches it, how big to be,
// how far to turn and what colour to glow. A shape that swells past its seat spills into the neighbours' seats, so
// every pixel also asks its six neighbours what they are showing, the way a theatre lights a stage from the wings.

// The step from a hex centre to its k-th neighbour (k = 0..5, counter-clockwise from +x; centres 1 apart).
vec2 hexNeonStep(int k) {
    float turn = float(k) * (PI / 3.0);
    return vec2(cos(turn), sin(turn));
}

// How swollen a cell is, 0..1, at its own clock `since` (seconds since the wave reached it): a breath at 0.23 Hz,
// detuned per cell by its die, over a slower drift at 0.097 Hz, so the rings beat and never quite repeat.
float hexNeonSwell(float since, float dice) {
    float breath = sin(TAU * 0.23 * since + 1.2 * dice);
    float drift = sin(TAU * 0.097 * since + 2.0);
    return 0.5 + 0.3 * breath + 0.2 * drift;
}

// A cell's pose from its centre alone: (inradius in cells, turn in radians, swell).
vec3 hexNeonPose(vec2 centre, float t, vec2 originLat, float waveSpeed, float sizeAmp, float spin) {
    float dice = hash21(latHexAxial(centre));
    float swell = hexNeonSwell(t - patCellDelay(centre, originLat, waveSpeed), dice);
    float size = 1.0 + clamp(sizeAmp, 0.0, 1.0) * 0.65 * (2.0 * swell - 1.0);
    return vec3(0.36 * size, TAU * spin * (size - 1.0), swell);
}

// A cell's colour, linear light: the cool cosine family with a coral accent, or the house note colour of the cell's
// place in the harmonic table.
vec3 hexNeonColour(vec2 axial, float dice, int palette, float accent) {
    if (palette == 1) {
        float pitchClass = mod(7.0 * axial.x + 4.0 * axial.y, 12.0);
        return palPitchFifths(pitchClass, 4.0, palPitchPiano());
    }
    float second = fract(dice * 64.0);                       // the hash's low bits: a second die from the same roll
    if (second < accent) {
        return vec3(0.745, 0.168, 0.078);                    // coral (#e0724f, the house accent), linear
    }
    return palCosLinear(dice, vec3(0.35, 0.575, 0.9), vec3(0.25, 0.275, 0.08), vec3(0.5), vec3(0.5, 0.0, 0.0));
}

// One cell's neon seen from `offset` (in cells) away from its centre: (light, filled coverage). In XOR mode the rgb
// is the cell's colour at its energy, for the caller to paint the parity with.
vec4 hexNeonCell(vec2 offset, vec2 centre, float pxLat, float t, vec2 originLat, float lineWidth, float haloPx,
                 float waveSpeed, float sizeAmp, float spin, int palette, float accent, int combine) {
    float reach = 1.0 - smoothstep(0.8, 1.15, length(offset));   // fade out before the cell leaves the seven
    if (reach <= 0.0) {
        return vec4(0.0);
    }
    vec3 pose = hexNeonPose(centre, t, originLat, waveSpeed, sizeAmp, spin);
    vec2 turned = rotate2(-pose.y) * offset;
    float pixel = max(pxLat, 1e-6);
    float d = sd2Hexagon(turned, pose.x);
    float fill = aaFill(d, pixel) * reach;
    float energy = 0.04 + 0.96 * pose.z * pose.z * pose.z;   // a steep curve after the swell: crests bright, the rest low
    vec2 axial = latHexAxial(centre);
    if (combine == 2) {
        return fill > 0.0 ? vec4(hexNeonColour(axial, hash21(axial), palette, accent) * energy, fill) : vec4(0.0);
    }
    float line = aaWire(d, lineWidth, pixel);
    float beyond = max(abs(d) / pixel - 0.5 * max(lineWidth, 1.0), 0.0);   // pixels past the line's edge
    // glowExp of the squared distance: a Gaussian skirt that is gone a few widths out, so the gaps stay black
    float glow = haloPx > 0.0 ? glowExp(beyond * beyond, 1.0 / (haloPx * haloPx)) : 0.0;
    float shine = reach * energy * (1.5 * line + 0.35 * glow);
    if (shine <= 1e-5) {
        return vec4(0.0, 0.0, 0.0, fill);
    }
    return vec4(hexNeonColour(axial, hash21(axial), palette, accent) * shine, fill);
}

// The hex-neon group: linear light at p (pixel size px in p's units) at time t, the wave starting at origin.
vec3 hexNeon(vec2 p, float px, float t, vec2 origin, float cellSize, float lineWidth, float haloPx, float waveSpeed,
             float sizeAmp, float spin, int palette, float accent, int combine, int view) {
    float scale = max(cellSize, 1e-4);
    vec2 lat = p / scale;
    float pxLat = max(px, 1e-6) / scale;
    vec4 home = latHex(lat);
    if (view == 1) {
        vec3 cells = dbgCells(home.xy, latHexAxial(home.zw), vec2(1.0, 2.0 / SQRT3), pxLat);
        cells = mix(cells, vec3(1.0), aaWire(latHexEdge(home.xy), 1.0, pxLat));
        return srgbDecode(clamp(cells, 0.0, 1.0));
    }
    vec2 originLat = origin / scale;
    vec3 light = vec3(0.0);
    float ink = 0.0;
    vec3 inkColour = vec3(0.0);
    float inkWeight = 0.0;
    for (int seat = 0; seat < 7; seat++) {                     // the home cell, then its six neighbours
        vec2 toCell = seat == 0 ? vec2(0.0) : hexNeonStep(seat - 1);
        vec4 cell = hexNeonCell(home.xy - toCell, home.zw + toCell, pxLat, t, originLat, lineWidth, haloPx,
                                waveSpeed, sizeAmp, spin, palette, accent, combine);
        if (combine == 2) {
            ink = cmpXor(ink, cell.a);
            inkColour += cell.rgb * cell.a;
            inkWeight += cell.a;
        } else if (combine == 1) {
            light = cmpMax(light, cell.rgb);
        } else {
            light = cmpAdd(light, cell.rgb);
        }
    }
    if (combine == 2) {
        light = inkColour / max(inkWeight, 1e-6) * ink;
    }
    return light;
}
