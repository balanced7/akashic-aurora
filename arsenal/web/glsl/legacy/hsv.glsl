//! {"name": "legacy-hsv", "kind": "helper", "legacy": true, "cat": "H3", "family": "H", "version": "1.0.0", "order": 14,
//!  "license": "Apache-2.0", "public": false,
//!  "ancestry": "Third-party technique: the branch-free RGB-to-HSV ordering is Sam Hocevar's (lolengine.net, 2013, published under the WTFPL) and the clamped triangle-wave HSV-to-RGB is the field's common form; the house pastes both, verbatim, in First Light (arsenal/web/shaders/first-light.frag), Play (arsenal/web/play.js) and its presets. This file is written fresh, with the same arithmetic in the same order, so a surface can adopt it without a pixel moving (pinned on SwiftShader against First Light's own text).",
//!  "credits": ["Sam Hocevar, 'Fast branchless RGB to HSV conversion in GLSL' (https://lolengine.net/blog/2013/07/27/rgb-to-hsv-in-glsl): the two compare-and-swaps that order the channels",
//!   "Alvy Ray Smith, 'Color gamut transform pairs' (SIGGRAPH 1978, Computer Graphics 12(3), pp. 12-19): HSV itself",
//!   "Bjorn Ottosson, 'Okhsv and Okhsl' (https://bottosson.github.io/posts/colorpicker/): why HSV is a knob, not a measure"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "hsvToRgb and rgbToHsv reproduce, operation for operation, the HSV pair the house pastes today (hue in turns; a grey's hue is 0; 1e-10 guards against a zero spread), so swapping a surface's inline copy for this module moves no pixel. HSV is a re-labelling of the RGB cube, so it stops being honest the moment it is asked about perception: V is the largest channel, not brightness.",
//!  "note": "A legacy twin: here so First Light, Play and the presets can compose the library without changing their look. For new work reach for colour-oklab instead (hueRotateOklch, mixOklch, palOklch): an HSV hue rotation turns blue (luminance 0.07) into yellow (0.93), a constant-V rainbow has bright bands at yellow, cyan and magenta and a dark trough at blue, and its triangle-wave seams show as thin bright Mach bands. HSV is fine as a hand knob for picking a hue by eye.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "legacy-hsv.card",
//!  "twin": "arsenal/shaders/twins/colour.py", "status": "P0",
//!  "exemplars": ["MdsXWM", "ffG3Rc"], "learn": ["CP 2.1", "CP 14.3"]}
// Apache-2.0, Akashic Aurora. Written fresh with the arithmetic of the house's pasted pair (see "ancestry" above).
//
// WHY A LEGACY TWIN. Ten house files paste their own copy of this pair. To let them compose the library instead without
// one pixel moving, this module performs the same floating-point operations in the same order (mix with step, the same
// constants, the same guards). Changing a surface to the perceptual version (OKLCH) is a separate step, behind Daniel's
// before-and-after, because it changes how the surface looks.

// HSV (hue in turns, saturation, value) to RGB. Each channel is a clamped triangle wave of hue, a third of a turn apart;
// the ramp is mixed toward white by 1 - S and scaled by V.
vec3 hsvToRgb(vec3 hsv) {
    const vec3 thirds = vec3(3.0, 2.0, 1.0) / 3.0;          // each channel's offset round the hue circle
    vec3 phase = fract(hsv.x + thirds);
    vec3 wave = abs(phase * 6.0 - 3.0);
    vec3 pure = clamp(wave - 1.0, 0.0, 1.0);                // the fully saturated colour of this hue
    return hsv.z * mix(vec3(1.0), pure, hsv.y);
}

// RGB to HSV (hue in turns). Two branch-free compare-and-swaps put the largest channel first, carrying the hue offset
// of the sextant it starts; the spread between the largest and the smaller of the other two sets hue and saturation.
vec3 rgbToHsv(vec3 rgb) {
    vec4 pair = mix(vec4(rgb.b, rgb.g, -1.0, 2.0 / 3.0), vec4(rgb.g, rgb.b, 0.0, -1.0 / 3.0), step(rgb.b, rgb.g));
    vec4 order = mix(vec4(pair.x, pair.y, pair.w, rgb.r), vec4(rgb.r, pair.y, pair.z, pair.x), step(pair.x, rgb.r));
    float spread = order.x - min(order.w, order.y);
    float guard = 1.0e-10;
    return vec3(abs(order.z + (order.w - order.y) / (6.0 * spread + guard)), spread / (order.x + guard), order.x);
}
