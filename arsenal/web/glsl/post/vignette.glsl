//! {"name": "post-vignette", "kind": "helper", "cat": "H7", "family": "H", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["the house chunk vignette-cubic (design/vfx-chunks/vignette-cubic.glsl): the cubic falloff and the normalisation by the real corner distance",
//!   "colour and post report, section 7.3 (research/reviewed/shader-school-2026-10-13/color-post.md): where a vignette belongs in the chain"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "vigCorner returns a brightness multiplier: exactly 1 at the centre, 1 - 0.8306 * amount in every corner of any aspect, flat across the middle and falling only near the corners; amount 0.6 is the legacy chunk exactly. Honest for amount in [0, 1] and aspect > 0; outside that it is still finite but no longer a vignette.",
//!  "note": "Reach for it as the frame's last darkening, after the display curve and before the sRGB encode (display-out does exactly that). The aspect matters: normalising by 0.7071 instead of the real corner blacks out the sides of a widescreen canvas, which is the bug the house chunk was written to stop. Wrong looks like a dark ring that starts near the centre (a smoothstep would do that) or black side bars on a 16:9 page.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "post-vignette.card",
//!  "twin": "arsenal/shaders/twins/finish.py", "status": "P0", "exemplars": ["wsl3WB"], "learn": ["CP 7.3"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics; the house chunk vignette-cubic is the reference.
//
// WHY. A picture frame, not a lens: the centre of the image is where the eye works, so it stays untouched, and the
// darkening gathers only in the corners where it pulls the eye back in. Think of the cubic as a dimmer whose knob is
// almost dead for the first half of its travel and then turns quickly.

// The house cubic. uv01 runs 0..1 across the canvas (y up); aspect is width / height.
float vigCorner(vec2 uv01, float aspect, float amount) {
    vec2 fromCentre = (uv01 - 0.5) * vec2(aspect, 1.0);   // aspect-true: a circle stays a circle
    float cornerReach = length(vec2(0.5 * aspect, 0.5));  // how far away the real corner is
    float reach = length(fromCentre) / cornerReach;        // 0 at the centre, 1 in every corner
    float fall = clamp(0.94 * reach, 0.0, 1.0);            // 0.94 keeps a little light in the very corner
    return mix(1.0, 1.0 - fall * fall * fall, amount);
}
