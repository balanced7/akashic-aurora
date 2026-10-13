//! {"name": "debug-views", "kind": "helper", "cat": "debug", "order": 20, "version": "0.1.0",
//!  "license": "Apache-2.0", "credits": [], "cost": "O(1)",
//!  "note": "TEST FIXTURE for tests/test_glsl_cards*.py, not the house module: a heat ramp and a distance-field view."}
// Apache-2.0, Akashic Aurora. Written fresh for the card tests; it stands in for debug/views.glsl, which the library
// has not built yet. It calls core-shaping and uses core-const, so a card that uses only this module still pulls both.

// A dark-to-bright ramp for t in [0, 1]: red climbs first, then green, then blue (black, red, yellow, white). Every
// channel only rises, so brightness never dips anywhere along the ramp.
vec3 dbgHeatRamp(float t) {
    float s = clamp(t, 0.0, 1.0);
    return vec3(shpLinstep(0.0, 0.4, s), shpLinstep(0.3, 0.75, s), shpLinstep(0.65, 1.0, s));
}

// A signed distance made visible: warm inside, cool outside, a soft band every `spacing`, and a bright line where d
// crosses zero, one pixel wide whatever the zoom. A field that is not a true distance shows bands that bunch or spread.
vec3 dbgSlice(float d, float spacing) {
    vec3 tint = d < 0.0 ? vec3(0.85, 0.5, 0.25) : vec3(0.3, 0.55, 0.85);
    tint *= 0.75 + 0.25 * cos(TAU * d / spacing);
    float px = max(fwidth(d), 1e-6);
    float edge = 1.0 - shpLinstep(0.5 * px, 1.5 * px, abs(d));
    return mix(tint, vec3(1.0), edge);
}
