//! {"name": "motion-envelope", "kind": "helper", "cat": "I1", "family": "I", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Manwe's HAL 4000 (https://www.shadertoy.com/view/MtXczn) and BigWings' Heartfelt (https://www.shadertoy.com/view/ltffzl): a whole film written as ramps and windows on one clock",
//!   "Robert Penner's easing equations (http://robertpenner.com/easing/): the cubic in-out ease",
//!   "WCAG 2.3.1, Three Flashes or Below Threshold (https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html): the flash gate",
//!   "Mattenii's Aurora Lights (https://www.shadertoy.com/view/MsjfRG) and albertelwin's AuroraBorealis (https://www.shadertoy.com/view/MdBfzR): a fast fringe over a slow body, breathing along the curtain"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Pure functions of a clock in seconds, each returning 0..1: envRamp is clamp((t - start) / dur), with dur <= 0 an instant switch just after start; envWindow rises from 0 at a to 1 at a + soft and falls from 1 at b - soft to 0 at b, exactly 0 outside [a, b]; envCubicEase and envSineEase are in-out eases on a clamped 0..1 input with e(1 - x) = 1 - e(x); envFlashSafe is 0 until a third of a second after the last full-field flash and 1 from half a second on; envBreath is a slow body plus a faster fringe travelling along x (in body wavelengths) at rates (cycles per second). Honest while the host keeps t small (wrap it); the flash gate is only as good as the host's record of the last flash.",
//!  "note": "Keyframes as maths: start, length, shape, all editable numbers on the one clock, so a scene can be scrubbed or frozen by remapping t (never by state). Multiply a big flash by envFlashSafe(since the last one) and the host cannot exceed three flashes a second, the photosensitivity line. envBreath is the curtain's breathing: mostly on, with a few dim stretches drifting slowly and brighter patches coming and going three or so times faster. Wrong looks like a pop at a keyframe (a ramp where an ease was meant), a window that leaks before its act (soft wider than the act), or a flicker that strobes harder on a faster display (the host fed frames, not seconds).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "motion-envelope.card",
//!  "twin": "arsenal/shaders/twins/envelope.py", "status": "P0",
//!  "exemplars": ["MtXczn", "ltffzl", "ldSfWV", "llVXRd", "MsjfRG", "MdBfzR"],
//!  "learn": ["study:MtXczn 6.8", "study:ltffzl 6.9", "PF 2", "GP 12.10", "study:MsjfRG 6.7"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the public articles credited above.
//
// WHY. A synthesiser's envelope generator for pictures: one clock goes in, a shape between 0 and 1 comes out, and
// whatever it multiplies (brightness, size, a colour mix) follows that shape. A whole scene is a stack of these on the
// same clock, which is why it can be scrubbed backwards or frozen without any memory of the past.

// 0 before start, 1 after start + dur, a straight line between. dur <= 0 switches at once, just after start.
float envRamp(float t, float start, float dur) {
    return clamp((t - start) / max(dur, 1e-6), 0.0, 1.0);
}

// An act: in from a over `soft` seconds, out by b over `soft` seconds; exactly 0 outside [a, b].
float envWindow(float t, float a, float b, float soft) {
    float s = max(soft, 1e-6);                             // smoothstep needs its edges apart
    return smoothstep(a, a + s, t) * (1.0 - smoothstep(b - s, b, t));
}

// Cubic in-out: slow start, the steepest point at the middle, slow arrival. Feels inevitable.
float envCubicEase(float x) {
    float u = clamp(x, 0.0, 1.0);
    float back = 2.0 - 2.0 * u;                            // the distance still to go, doubled
    return u < 0.5 ? 4.0 * u * u * u : 1.0 - 0.5 * back * back * back;
}

// Sine in-out: half a cosine wave, gentler at the ends than the cubic.
float envSineEase(float x) {
    float u = clamp(x, 0.0, 1.0);
    return 0.5 - 0.5 * cos(PI * u);
}

// The flash gate: multiply a large-area flash by this, with the seconds since the last one that fired.
float envFlashSafe(float sinceLastFlash) {
    return smoothstep(1.0 / 3.0, 0.5, sinceLastFlash);
}

// Two-timescale breathing travelling along x (x in body wavelengths; rates = (body, fringe) in cycles per second).
float envBreath(float x, float t, vec2 rates) {
    // the body: two waves at unrelated spacings, so the dim stretches never line up into a pattern
    float bodyWave = 0.6 * sin(TAU * fract(x - rates.x * t)) + 0.4 * sin(TAU * fract(2.37 * x + 0.71 - 1.3 * rates.x * t));
    float body = smoothstep(-0.9, 0.0, bodyWave);       // mostly on, dims where both waves dip
    // the fringe: shorter spacing, its own rate, and a threshold that leaves only brief bright patches
    float fringeWave = 0.6 * sin(TAU * fract(3.1 * x - rates.y * t)) + 0.4 * sin(TAU * fract(5.3 * x + 0.29 + 0.7 * rates.y * t));
    float fringe = smoothstep(0.35, 0.9, fringeWave);
    return (body + 0.5 * fringe) / 1.5;
}
