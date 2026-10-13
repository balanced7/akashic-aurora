//! {"name": "display-out", "kind": "recipe", "cat": "H9", "family": "H", "version": "1.0.0", "order": 60,
//!  "license": "Apache-2.0",
//!  "credits": ["colour and post report, sections 10 and 14.12 (research/reviewed/shader-school-2026-10-13/color-post.md): the whole chain in order, and the one seam every surface ends with",
//!   "Ryan Geiss, MilkDrop's split of warp and composite (https://www.geisswerks.com/milkdrop/milkdrop_preset_authoring.html): the finish is display-only and never feeds back"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "entry": "vec3 displayOut(vec3 sceneLin, vec2 pixel, vec2 res, float ev, int curve, float saturation, float vignette, float sCurve, float ditherLevels)",
//!  "params": [
//!   {"name": "ev", "label": "Exposure", "unit": "stops", "range": [-4, 4], "default": 0, "step": 0.05, "group": "finish",
//!    "help": "Brightness before the display curve, in camera stops: +1 doubles the light."},
//!   {"name": "curve", "label": "Display curve", "group": "finish", "default": 0,
//!    "choices": [{"value": 0, "label": "Glow field (tanh)"}, {"value": 1, "label": "Film density (1 - e^-x)"},
//!                {"value": 2, "label": "Cinema punch (ACES fit)"}, {"value": 3, "label": "True colour (PBR Neutral)"}],
//!    "help": "How unbounded light is squeezed into the screen. Glow field suits soft emitters; True colour matches the piano's three.js Neutral."},
//!   {"name": "saturation", "label": "Saturation", "unit": "ratio", "range": [0, 2], "default": 1, "step": 0.01, "group": "finish",
//!    "help": "0 is true grey (Rec. 709 luminance), 1 leaves colour alone, 2 doubles its distance from grey."},
//!   {"name": "vignette", "label": "Vignette", "unit": "ratio", "range": [0, 1], "default": 0.25, "step": 0.01, "group": "finish",
//!    "help": "How much the corners darken. The middle of the frame is never touched."},
//!   {"name": "sCurve", "label": "S-curve", "unit": "ratio", "range": [0, 1], "default": 0, "step": 0.01, "group": "finish",
//!    "help": "A gentle contrast look on the finished picture: deeper shadows, brighter highlights."},
//!   {"name": "ditherLevels", "label": "Dither", "group": "finish", "default": 256,
//!    "choices": [{"value": 0, "label": "Off"}, {"value": 64, "label": "6 bits"}, {"value": 128, "label": "7 bits"},
//!                {"value": 256, "label": "8 bits (a normal screen)"}, {"value": 512, "label": "9 bits"},
//!                {"value": 1024, "label": "10 bits"}],
//!    "help": "The screen's depth the dither is sized for. 8 bits is right for a normal canvas; Off shows the bands."}],
//!  "contract": "displayOut turns scene-linear light into the bytes a canvas writes, in the house order: expose, display curve (0 tanh, 1 1-e^-x, 2 ACES fit, 3 PBR Neutral; any other value is tanh until AgX is built), saturation, vignette, exact sRGB encode, S-curve look, static dither. Its result is always finite and inside 0..1 for finite input; negative light is treated as none. Honest only as the very last step before the canvas: feeding its output back into a buffer, or encoding it again, double-applies the look.",
//!  "note": "Every surface ends with this one call, so its params are the Finish panel on every page and one edit restyles everything. Glow field (tanh) is the cockpit and First Light default; True colour (PBR Neutral) matches the piano's three.js scenes so a GLSL surface and a three.js one can agree. Wrong looks like washed-out mids (the input was already encoded), bands in dark gradients (dither off), or a look that compounds every frame (the finish was put inside a feedback loop).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "display-out.card",
//!  "twin": "arsenal/shaders/twins/finish.py", "status": "P0",
//!  "exemplars": ["lfscD7", "XsSGDh", "XtS3DD", "MfjyWK", "cs2GWD"], "learn": ["CP 14.12", "CP 10"]}
// Apache-2.0, Akashic Aurora. Written fresh: a wiring of house helpers, each credited in its own module.
//
// WHY. The display chain is a mastering desk: the gain knob (exposure) comes first, then the limiter (the display
// curve) that keeps the loudest light from clipping, then the colour and frame touches, then the converter (sRGB
// encode) that speaks the screen's language, and last the dither that hides the converter's 256 steps. Put any of
// them out of order and the picture still shows, just subtly wrong everywhere. One function means one order.

// The house tail. sceneLin is scene-linear light (unbounded, >= 0); pixel is the fragment coordinate; res is the
// canvas size in pixels. The rest are the Finish panel's params, in header order.
vec3 displayOut(vec3 sceneLin, vec2 pixel, vec2 res, float ev, int curve, float saturation, float vignette,
                float sCurve, float ditherLevels) {
    vec3 light = expose(max(sceneLin, vec3(0.0)), ev);
    vec3 shown;                                            // display-linear, 0..1
    if (curve == 1) {
        shown = tmExp(light);
    } else if (curve == 2) {
        shown = tmAcesFit(light);
    } else if (curve == 3) {
        shown = tmPbrNeutral(light);
    } else {
        shown = tmTanh(light);
    }
    shown = grdSaturation(shown, saturation);
    shown *= vigCorner(pixel / res, res.x / res.y, vignette);
    vec3 enc = srgbEncode(clamp(shown, 0.0, 1.0));
    enc = clamp(grdSCurveDisp(enc, sCurve), 0.0, 1.0);
    return ditherOut(enc, pixel, ditherLevels);
}
