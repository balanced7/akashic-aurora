//! {"name": "debug-views", "kind": "helper", "cat": "A7", "family": "A", "version": "1.0.0", "order": 28,
//!  "license": "Apache-2.0",
//!  "credits": ["Fabrice Neyret, 'shadertoy - unofficial' (https://shadertoyunofficial.wordpress.com/2023/11/26/performance-tricks/): make the cost visible; the shader draws its own step count",
//!   "Martijn Steinrucken (BigWings), The Art of Code videos and his Hexagone (https://www.shadertoy.com/view/wsl3WB): the development view of a tiling, local coordinate as red and green with the cell borders drawn",
//!   "Martin Roberts, 'The unreasonable effectiveness of quasirandom sequences' (https://extremelearning.com.au/unreasonable-effectiveness-of-quasirandom-sequences/): the R2 sequence, so neighbouring cells always get different tints",
//!   "Sebastien Durand, 'Isoline Simple' (https://www.shadertoy.com/view/Ms2XWc): the Euclidean derivative length for even iso-lines"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Display-referred views that replace the picture, written straight to the screen after any tone mapping. dbgHeatRamp(t) runs black, violet, red-orange, amber, white over t in [0, 1] (clamped) with Rec. 709 luma climbing in even steps, never dipping. dbgHeatCount(count, budget) is the ramp of count / budget, pure magenta above the budget. dbgRangeScope(c) is magenta if any channel is NaN, else cyan if any is Inf, else blue if any is negative, else red if any is above 1, else a grey from the colour's luma. dbgNaN(c) is magenta where any channel is NaN or Inf, else c unchanged. dbgSlice(d, spacing) colours a signed distance warm inside and cool outside, with a light iso-line every spacing (faded out where lines would fall under six pixels apart) and a white zero line; it measures d's screen derivative itself, so call it in uniform control flow. dbgCells(local, cellId, period, px) shows the local coordinate (centred, spanning period) as red and green, the cell id as a tint that differs between neighbours, and a white border px wide. Non-finite tests read the exponent bits, which a compiler cannot fold away.",
//!  "note": "The multimeter on the bench. Every loved shader that taught well also showed its own wiring (Glitch Transform's NORMALS switch, Dark Cloud's red overflow flag, Dry Ice's flat view of its buffer), and the house makes it a rule: every module ships its where-am-I-wrong views and every host can switch to them. One frame of dbgRangeScope finds most black-blob bugs; dbgHeatCount on a march's step count shows where the slow pixels are (silhouettes and grazing floors glow); dbgSlice proves a field is a distance (its lines stay evenly spaced) or shows where it lies (lines that bunch or spread); dbgCells shows a tiling's numbering and seams. These keep their own non-finite tests rather than calling core-safe: a meter that shares the circuit it measures cannot be trusted when that circuit is broken. Wrong looks like a ramp that darkens somewhere along its length, or a NaN view that shows nothing on a shader known to be broken (the test folded away).",
//!  "targets": {"glsl": "300es", "needs": ["derivatives"]}, "card": "debug-views.card",
//!  "twin": "arsenal/shaders/twins/core.py", "status": "P0", "exemplars": ["4slGWM", "wsl3WB", "ltffzl"],
//!  "learn": ["GP 10", "GP 10.4", "SR 9.1", "LM 16", "PF 14.3"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the articles credited above.
//
// WHY. A shader cannot print. These turn the numbers it cannot print into colours a person (or a seat counting pixels
// in a render) can read at a glance: how many steps, where the NaN is, whether a field is a true distance, how a tiling
// is numbered. They write straight to the screen, replacing the picture, so they work in display values.

// A dark-to-bright ramp for t in [0, 1]: five stops, black, violet, red-orange, amber and white, whose Rec. 709 luma is
// 0, 0.25, 0.5, 0.75 and 1. Each stop takes over across its quarter, so brightness climbs evenly and never dips.
vec3 dbgHeatRamp(float t) {
    float quarter = clamp(t, 0.0, 1.0) * 4.0;
    vec3 heat = vec3(0.0);
    heat = mix(heat, vec3(0.40, 0.15, 0.85), clamp(quarter, 0.0, 1.0));
    heat = mix(heat, vec3(1.00, 0.38, 0.25), clamp(quarter - 1.0, 0.0, 1.0));
    heat = mix(heat, vec3(1.00, 0.74, 0.20), clamp(quarter - 2.0, 0.0, 1.0));
    heat = mix(heat, vec3(1.0), clamp(quarter - 3.0, 0.0, 1.0));
    return heat;
}

// How much of a budget a count used (loop trips, texture fetches), as heat; pure magenta once it is over budget.
vec3 dbgHeatCount(float count, float budget) {
    vec3 heat = dbgHeatRamp(count / max(budget, 1e-6));
    return count > budget ? vec3(1.0, 0.0, 1.0) : heat;
}

// A value-range oscilloscope for a colour about to be written. The worst problem in any channel wins: NaN (magenta),
// then Inf (cyan), then a negative (blue), then above 1 (red); a value in range shows as a grey from its luma. The
// sign bit is masked off, then exponent bits all ones with a zero fraction is Inf, with any fraction NaN.
vec3 dbgRangeScope(vec4 c) {
    ivec4 magnitude = floatBitsToInt(c) & 0x7fffffff;
    bool anyNan = any(greaterThan(magnitude, ivec4(0x7f800000)));
    bool anyInf = any(equal(magnitude, ivec4(0x7f800000)));
    vec3 weights709 = vec3(0.2126, 0.7152, 0.0722);
    float lumaInRange = clamp(dot(weights709, c.rgb), 0.0, 1.0);
    vec3 scope = vec3(0.2 + 0.6 * lumaInRange);
    if (any(greaterThan(c, vec4(1.0)))) {
        scope = vec3(1.0, 0.0, 0.0);
    }
    if (any(lessThan(c, vec4(0.0)))) {
        scope = vec3(0.0, 0.0, 1.0);
    }
    if (anyInf) {
        scope = vec3(0.0, 1.0, 1.0);
    }
    if (anyNan) {
        scope = vec3(1.0, 0.0, 1.0);
    }
    return scope;
}

// c unchanged, or pure magenta where any channel is NaN or Inf (exponent bits all ones).
vec3 dbgNaN(vec3 c) {
    ivec3 exponentBits = floatBitsToInt(c) & 0x7f800000;
    bool broken = any(equal(exponentBits, ivec3(0x7f800000)));
    return broken ? vec3(1.0, 0.0, 1.0) : c;
}

// A plane through a signed distance field: warm inside (d < 0), cool outside, darker with distance, a light line
// every `spacing` and a white line where d = 0. In a true distance the lines are evenly spaced; where they bunch the
// field overestimates (a marcher will overstep there), where they spread it is a loose bound. The pixel size is the
// Euclidean length of d's screen derivatives, taken first, before anything could branch.
vec3 dbgSlice(float d, float spacing) {
    float acrossX = dFdx(d);
    float acrossY = dFdy(d);
    float px = max(sqrt(acrossX * acrossX + acrossY * acrossY), 1e-6);
    float gap = max(spacing, 1e-6);
    vec3 side = d < 0.0 ? vec3(0.92, 0.55, 0.22) : vec3(0.25, 0.55, 0.92);
    vec3 slice = side * (0.4 + 0.25 * exp(-abs(d) / (3.0 * gap)));
    float band = d / gap + 0.5;
    float toLine = abs(fract(band) - 0.5) * gap;
    float lineInk = (1.0 - smoothstep(0.5 * px, 1.5 * px, toLine)) * smoothstep(3.0 * px, 6.0 * px, gap);
    float zeroInk = 1.0 - smoothstep(0.75 * px, 2.0 * px, abs(d));
    slice = mix(slice, mix(side, vec3(1.0), 0.35), lineInk);
    return mix(slice, vec3(1.0), zeroInk);
}

// The development view of a tiling. local is the point's position in its cell, centred (from -period/2 to period/2,
// the domain-repeat convention); it shows as red (across) and green (up). cellId picks a tint: one step of the R2
// sequence per cell around a cosine hue wheel, so neighbours always differ. A white border px wide marks each cell.
vec3 dbgCells(vec2 local, vec2 cellId, vec2 period, float px) {
    vec2 across = local / period + 0.5;
    float wheel = fract(dot(vec2(0.7548776662, 0.5698402910), cellId));
    vec3 cellTint = 0.5 + 0.5 * cos(TAU * wheel + vec3(0.0, 2.0, 4.0) * (PI / 3.0));
    vec3 cells = 0.55 * vec3(across, 0.0) + 0.45 * cellTint;
    vec2 toEdge = 0.5 * period - abs(local);
    float borderInk = 1.0 - smoothstep(0.5 * px, 1.5 * px, min(toEdge.x, toEdge.y));
    return mix(cells, vec3(1.0), borderInk);
}
