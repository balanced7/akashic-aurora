//! {"name": "colour-grade", "kind": "helper", "cat": "H6", "family": "H", "version": "1.0.0", "order": 22,
//!  "license": "Apache-2.0",
//!  "credits": ["ITU-R BT.709 (https://www.itu.int/rec/R-REC-BT.709): the luminance a saturation change must hold still",
//!   "American Society of Cinematographers, ASC CDL v1.2 (summary at https://en.wikipedia.org/wiki/ASC_CDL): saturation as a lerp about Rec. 709 luma",
//!   "Inigo Quilez's signature finish, a smoothstep S-curve on encoded values, as the colour and post report describes it (section 9.5); his linear-light practice behind it at https://iquilezles.org/articles/outdoorslighting/",
//!   "the colour and post report, section 3.3 and craft secret 8 (research/reviewed/shader-school-2026-10-13/color-post.md): saturation and overbright by extrapolating away from grey"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "grdSaturation works on LINEAR light and never changes Rec. 709 luminance (s = 0 is the true grey, s = 1 leaves the colour alone, s > 1 may leave the gamut); grdAwayFrom is c + k (c - pivot), floored at 0 because light is never negative (k = 0 leaves c alone); grdSCurveDisp takes and returns DISPLAY (encoded) values: a smoothstep S-curve mixed in by amount, with 0 and 1 and the middle 0.5 held fixed.",
//!  "note": "Grade in the right currency: saturation on linear light before the encode, the S-curve on display values after it and before dither. grdAwayFrom with a grey pivot is a strong saturation and contrast push (a dull texture turns candy); with a second colour as the pivot it pushes away from that colour. Wrong looks like a desaturation that darkens blue and brightens green (Rec. 601 weights on linear light), or crushed, posterised ends (an S-curve stacked twice).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "colour-grade.card",
//!  "twin": "arsenal/shaders/twins/colour.py", "status": "P0",
//!  "exemplars": ["XsSGDh", "MdX3zr", "NlK3Wt", "XsBfRW", "XtS3DD", "ltdcW7", "4tcXRr"],
//!  "learn": ["CP 9.4", "CP 9.5", "craft secret 8"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics (credits above).
//
// WHY. Grading is the mixing desk after the recording: it changes how a picture feels without changing what is in it.
// Each control works in the currency it was designed for, so it moves the one thing its name promises: saturation
// moves colourfulness and not brightness, the S-curve moves contrast in the space the eye sees.

// Saturation about Rec. 709 luminance: Y + s (x - Y). Luminance is untouched for every s, so a desaturated blue keeps
// blue's darkness and a desaturated green keeps green's brightness.
vec3 grdSaturation(vec3 lin, float s) {
    float y = luminance(lin);
    return vec3(y) + s * (lin - vec3(y));
}

// Push a colour away from a pivot: c + k (c - pivot), a mix that runs past its end. With a grey pivot, colourfulness
// and contrast both rise; values may pass 1 (overbright, for a tone curve to catch) but never go below 0.
vec3 grdAwayFrom(vec3 c, vec3 pivot, float k) {
    return max(c + k * (c - pivot), vec3(0.0));
}

// The classic finish on DISPLAY values: blend toward x^2 (3 - 2x) by amount. Deeper shadows, brighter highlights,
// a little more saturation in the mids; 0, the middle 0.5 and 1 stay where they are.
vec3 grdSCurveDisp(vec3 disp, float amount) {
    vec3 curved = smoothstep(0.0, 1.0, disp);   // exactly x^2 (3 - 2x) on disp clamped to 0..1
    return mix(disp, curved, amount);
}
