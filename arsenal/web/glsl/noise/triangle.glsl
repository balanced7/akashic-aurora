//! {"name": "noise-triangle", "kind": "helper", "cat": "B1", "family": "B", "version": "1.0.0", "order": 22,
//!  "license": "Apache-2.0",
//!  "credits": ["nimitz, 'Auroras' (https://www.shadertoy.com/view/XtGGRt) and 'Overly satisfying' (https://www.shadertoy.com/view/Mts3zM): triangle-wave noise, octaves of folded triangle waves pushed by a turning field, cheap enough for an aurora to evaluate dozens of times a pixel; the house version is our own construction",
//!   "Inigo Quilez, 'fBM' (https://iquilezles.org/articles/fbm/): turn every octave so no lattice lines up, and normalise by the summed amplitudes"],
//!  "cost": {"class": "C1", "loop": "octaves <= 8", "tex": 0, "per_octave": "five triangle waves and one sine-cosine pair"},
//!  "contract": "A field in [0, 1] with mean 0.5, continuous everywhere (slope under about 20 per unit for 8 octaves), creased (V-shaped valleys) along long ragged lines about one unit apart. Over n = min(octaves, 8) octaves (fewer than 1 gives exactly 0.5) it sums 0.5^i shpTri(q.x + 0.5 shpTri(q.y)) and divides by the sum of 0.5^i. q starts at p; w, the warp's own coordinate, starts at p turned by 1.1 rad and scaled by 0.43. Each octave first pushes q by 1.2 times the warp field (shpTri(w.x + 0.5 shpTri(w.y)), shpTri(w.y + 0.5 shpTri(w.x))) - 0.5 turned by spin_i = 0.5 t (-1.37)^i radians, adds its term, then turns q by one radian counter-clockwise, scales it by PHI and steps it by (0.31, -0.47), and turns w by one radian clockwise, scales it by 1.41 and steps it by (-0.23, 0.19). t is the churn clock: one octave alone repeats every 4 pi of t; together the rates never fall in step. Honest while |p| < 2^14 and the host wraps t below about 1e4.",
//!  "note": "The aurora's filament fabric: texture-free, hash-free, all fract and abs, so a sheet stack can read it 50 times a pixel. Its bright features are its valleys: run it through a steep transfer that rewards small values, shpInvPower(n, about 0.1, 2 to 3), and the creases light as hairline filaments; stretch p (for example by (5, 0.5)) and they become hanging rays. Time turns the warp rather than sliding it, so the field churns in place instead of scrolling. Octave 1 alone is a crisp polyline zig-zag; 3 to 4 is the ragged curtain fabric; past 5 adds sparkle that only aliases. Wrong looks like a visible repeating tile (the warp sharing the octaves' lattice), filaments that slide sideways as a sheet (t added to p instead of turning the warp), a field that brightens or darkens as octaves are added (not normalised), or a hard seam (a discontinuity: fract of something other than a triangle wave).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "noise-triangle.card",
//!  "twin": "arsenal/shaders/twins/triangle.py", "status": "P0",
//!  "exemplars": ["ffG3Rc", "Mts3zM"],
//!  "learn": ["VA 7.2 family B", "study:Mts3zM"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public pages credited above.
//
// WHY. An aurora curtain drawn as a stack of sheets samples one 2D footprint per sheet, dozens of times a pixel, so
// its fabric must be nearly free: no texture to fetch, no hash to mix. A triangle wave (the zig-zag a function
// generator makes) is two instructions, and its valleys are creases. Bend one triangle wave by another and the valleys
// become long zig-zag lines; push the coordinate with a slow field that turns over time, add a few smaller, turned
// octaves, and the lines fray into ragged filaments that churn in place. The warp is read on its own, differently
// turned, coarser copy of the plane, so the triangle waves' period never lines up into a visible tile.

// Filament noise in [0, 1]: small (dark) along thin creases, about 0.5 on average. t turns the warp; octaves <= 8.
float noiseTriangle2(vec2 p, float t, int octaves) {
    const mat2 octaveTurn = mat2(0.54030231, 0.84147098, -0.84147098, 0.54030231);   // one radian, counter-clockwise
    const mat2 warpTurn = mat2(0.54030231, -0.84147098, 0.84147098, 0.54030231);     // one radian, clockwise
    const mat2 warpStart = mat2(0.45359612, 0.89120736, -0.89120736, 0.45359612);    // 1.1 radians
    if (octaves < 1) return 0.5;
    vec2 q = p;
    vec2 w = (warpStart * p) * 0.43;
    float total = 0.0;
    float amp = 1.0;
    float ampSum = 0.0;
    float spin = 0.5 * t;
    for (int band = 0; band < 8; band++) {                 // a constant ceiling: at most 8 octaves
        if (band >= octaves) break;
        vec2 field = vec2(shpTri(w.x + 0.5 * shpTri(w.y)), shpTri(w.y + 0.5 * shpTri(w.x))) - 0.5;
        q += 1.2 * (rotate2(spin) * field);
        total += amp * shpTri(q.x + 0.5 * shpTri(q.y));
        ampSum += amp;
        amp *= 0.5;
        q = (octaveTurn * q) * PHI + vec2(0.31, -0.47);
        w = (warpTurn * w) * 1.41 + vec2(-0.23, 0.19);
        spin *= -1.37;                                      // each octave churns faster, the other way round
    }
    return total / ampSum;
}
