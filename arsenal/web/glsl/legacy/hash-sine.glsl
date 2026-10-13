//! {"name": "hash-sine", "kind": "helper", "legacy": true, "public": false,
//!  "cat": "A6", "family": "A", "version": "1.0.0", "order": 10,
//!  "license": "Apache-2.0",
//!  "ancestry": "the folk sine-dot hash of early Shadertoy shaders, with the (127.1, 311.7, 74.7) constants they made common; written here as this repository's own surfaces already write it (design/vfx-chunks/hash31.glsl, arsenal/web/shaders/first-light.frag, arsenal/web/presets/*.frag, arsenal/web/piano/spectacle-worlds.js, scripts/bench-aurora.html)",
//!  "credits": ["The Book of Shaders, chapter 10 'Random' by Patricio Gonzalez Vivo and Jen Lowe (https://thebookofshaders.com/10/): the fract(sin(dot)) idiom and why it only looks random",
//!   "Mark Jarzynski and Marc Olano, 'Hash Functions for GPU Rendering' (https://jcgt.org/published/0009/03/02/): the measurement that puts the trig hash at the low-quality end, which is why this file is legacy"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "LEGACY TWIN. hashSine21 is fract(sin(dot(p, (127.1, 311.7))) * 43758.5453) and hashSine31 is fract(sin(dot(p, (127.1, 311.7, 74.7))) * 43758.5453123), the same arithmetic as the house surfaces that use them, so adopting the library moves no pixel. In [0, 1). Honest only near the origin under highp: its randomness is the aliasing of a sine sampled far faster than it oscillates, so it depends on each GPU's sine, bands under mediump, and collapses into coarse steps and stripes once dot(p, k) grows past about 10^7 (big coordinates, or a clock fed into the hash).",
//!  "note": "Do not reach for this in new work: hash-pcg is the house hash (bit-exact everywhere, no decay). This file exists so a surface that already uses the sine hash can compose from the library without a pixel moving; swapping it for hash-pcg is a separate, gated step with before and after renders (every noise pattern it feeds will change). Its card shows why: white noise at the origin, steps and stripes far away. Note that (127.1, 311.7) and (12.9898, 78.233) are DIFFERENT hashes; the house uses both, and only the first is twinned here.",
//!  "targets": {"glsl": "100", "needs": []}, "card": "hash-sine.card",
//!  "twin": "arsenal/shaders/twins/hash.py", "status": "P0",
//!  "exemplars": ["4slGWM", "MdX3zr", "MsjfRG", "XsjXRm", "XtyXzW", "ldSfWV", "llK3Dy"],
//!  "learn": ["NP 2.2"]}
// Apache-2.0, Akashic Aurora. A legacy twin: the house's own long-standing arithmetic, kept so surfaces can adopt the
// library without a pixel moving. Not for new work.
//
// WHY THE SINE HASH IS LEGACY. sin(x) times a big number, keeping only the fraction, is a sine wave sampled so much
// faster than it oscillates that the samples look random: it is aliasing used on purpose. It works until x gets big,
// when a 32-bit float can only count x in coarse steps; then neighbouring pixels land on the same few steps and the
// "noise" turns into stripes. Like a cheap clock that is fine at power-on and drifts after a week of uptime.

// The 2D sine hash with the (127.1, 311.7) constants.
float hashSine21(vec2 p) {
    float phase = dot(vec2(127.1, 311.7), p);
    return fract(sin(phase) * 43758.5453);
}

// The 3D sine hash with the (127.1, 311.7, 74.7) constants: the bench chunk h31 and First Light's hash.
float hashSine31(vec3 p) {
    float phase = dot(vec3(127.1, 311.7, 74.7), p);
    return fract(sin(phase) * 43758.5453123);
}
