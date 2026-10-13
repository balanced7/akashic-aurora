//! {"name": "post-dither", "kind": "helper", "cat": "H8", "family": "H", "version": "1.0.0", "order": 25,
//!  "license": "Apache-2.0",
//!  "credits": ["Mikkel Gjøl, 'Banding in Games: A Noisy Rant' (Playdead, http://loopit.dk/banding_in_games.pdf): triangular noise of one code value, added in the space that is quantised, eased at the ends",
//!   "Jorge Jimenez, 'Next Generation Post Processing in Call of Duty: Advanced Warfare' (http://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare): the interleaved gradient noise mask",
//!   "colour and post report, sections 8.1-8.3 (research/reviewed/shader-school-2026-10-13/color-post.md)"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "ditherOut adds triangular noise of at most one code value (1 / (levels - 1)) to an ENCODED colour, from a mask that never moves, so the rounding of the canvas write becomes unbiased: the mean over an area is the value asked for. Within one code value of 0 or 1 the noise eases to half a code value of uniform noise, so black rounds to black and white to white. levels below 2 means off (the colour comes back unchanged). Honest only right before the write; dither applied after a quantisation, or before more maths, adds noise and fixes nothing.",
//!  "note": "The last line of every finish: after srgbEncode and the S-curve, before the canvas write (display-out). Static on purpose: per-frame dither is the crawling grain Daniel asked to remove (shader-craft floor 8), and at one code value a still mask is invisible. Pass levels 256 for an 8-bit canvas. Wrong looks like bands in slow dark gradients (no dither, or dither before an 8-bit buffer), a lifted grey floor in black (no easing at the ends), or a fizz that moves when nothing else does (a clock in the seed).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "post-dither.card",
//!  "twin": "arsenal/shaders/twins/finish.py", "status": "P0", "exemplars": ["ffG3Rc", "XsSGDh", "ldSfWV"],
//!  "learn": ["CP 8.2", "NP 13.3"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics and the articles credited above.
//
// WHY. An 8-bit canvas is a staircase with 256 steps. A gradient that climbs slower than one step across many pixels
// shows each step as a band, and the eye is an edge detector. Dither is the audio engineer's trick: add a whisper of
// noise before the rounding, so the rounding error is random instead of a staircase, and the eye averages it back
// into the smooth value. Triangular noise (two uniform dice summed) is the shape whose noise looks the same at every
// brightness, so the picture does not show clean and noisy stripes.

// Dither an encoded colour (0..1 display values) for a write to a canvas with `levels` code values per channel.
// pixel is the fragment coordinate; the mask depends on nothing else.
vec3 ditherOut(vec3 enc, vec2 pixel, float levels) {
    if (levels < 2.0) return enc;                          // off
    float steps = levels - 1.0;                            // code values above zero
    float mask = dthIgn(pixel);                            // a still mask in [0, 1)
    float tri = dthTriFromUniform(mask);                   // the same mask, reshaped to a triangle on [-1, 1]
    float halfStep = 0.499 * (2.0 * mask - 1.0);           // uniform, a hair inside half a code value
    vec3 room = clamp(min(enc, 1.0 - enc) * steps, 0.0, 1.0);   // 1 where the whole triangle fits inside 0..1
    vec3 noise = mix(vec3(halfStep), vec3(tri), room);
    return clamp(enc + noise / steps, 0.0, 1.0);
}
