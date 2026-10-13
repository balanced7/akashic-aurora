//! {"name": "legacy-tone-superlinear", "kind": "helper", "legacy": true, "cat": "H5", "family": "H", "version": "1.0.0",
//!  "order": 18, "license": "Apache-2.0", "public": false,
//!  "ancestry": "The bench chunk superlinear-highlight (design/vfx-chunks/superlinear-highlight.glsl, the statement col += col * col * 0.85), which its own header records as taken from the c*c term of a wave shader Daniil pasted. The maths is a one-line polynomial; this file is written fresh and reproduces it operation for operation (pinned on SwiftShader against the chunk's own statement).",
//!  "credits": ["the house bench chunk superlinear-highlight and the shader-craft ceiling 'superlinear highlight, then the tanh shoulder' (.claude/skills/shader-craft/SKILL.md)"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "tmSuperlinear(x, k) is x + k x^2 per channel, the bench chunk's arithmetic in the bench chunk's order (k = 0.85 reproduces it), for scene-linear light before a shoulder such as tmTanh; it has no ceiling of its own and is honest only with a curve after it.",
//!  "note": "Squaring leaves the dark two-thirds nearly untouched and pays out only at the crests, so mids sink toward black while bright nodes bloom: the picture gets darker and more striking at once instead of trading one for the other. Put it BEFORE the tanh shoulder (tmTanh), never after, or the shoulder gets re-expanded into a flat white plateau. A legacy twin: here so the bench's filmic-finish group and First Light can compose the library without a pixel moving.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "legacy-tone-superlinear.card",
//!  "twin": "arsenal/shaders/twins/tone.py:tmSuperlinear", "status": "P0",
//!  "exemplars": [], "learn": ["house chunk superlinear-highlight"]}
// Apache-2.0, Akashic Aurora. Written fresh with the arithmetic of the bench chunk (see "ancestry" above).
//
// WHY. A glow field that is bright everywhere reads as fog; one that is dark with hot crests reads as light. Adding a
// small square term is the cheapest way to get there: like an amplifier driven a little into its expansion region, quiet
// signals pass almost unchanged while loud peaks grow faster than linearly. The shoulder after it (tmTanh) then rolls
// those peaks off so they never clip flat.

// x + k x^2 per channel. At k = 0.85 a value of 0.2 grows by 17% while a value of 1 grows by 85%.
vec3 tmSuperlinear(vec3 x, float k) {
    return x + x * x * k;
}
