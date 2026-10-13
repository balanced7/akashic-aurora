//! {"name": "colour-tone", "kind": "helper", "cat": "H5", "family": "H", "version": "1.0.0", "order": 16,
//!  "license": "Apache-2.0",
//!  "credits": ["Erik Reinhard, Michael Stark, Peter Shirley and James Ferwerda, 'Photographic tone reproduction for digital images' (SIGGRAPH 2002): x / (1 + x)",
//!   "Krzysztof Narkowicz, 'ACES filmic tone mapping curve' (https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/): the rational fit and its 0.6 pre-exposure",
//!   "Khronos Group, Emmett Lalish, 'PBR Neutral' (https://github.com/KhronosGroup/ToneMapping/tree/main/PBR_Neutral): the neutral transform the piano's three.js renderer uses",
//!   "Orion Lawlor and Jon Genetti, 'Interactive volume rendering aurora on the GPU' (Journal of WSCG 2011, https://www.cs.uaf.edu/~olawlor/papers/2010/aurora/lawlor_aurora_2010.pdf): gamma on the colour's magnitude only",
//!   "Matt Taylor, 'Tone mapping' (https://64.github.io/tonemapping/): the survey the curve choices lean on"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Each tm* curve takes scene-linear light and returns display-linear 0..1 (not yet encoded: srgbEncode comes after); expose is the only brightness knob before them; every curve is finite for any finite input (tanh and the ACES fit clamp their argument where they have already reached 1) and tmTanh, tmExp, tmReinhard and tmAcesFit treat negative light as none; tmPbrNeutral is the Khronos formula exactly, so it matches three.js NeutralToneMapping on the piano; displayHueSafeGamma changes a colour's magnitude only, never its direction.",
//!  "note": "A tone curve is a limiter with a soft knee between unbounded light and the screen. Pick by content (CP 5.10): tanh or 1 - e^-x for glow fields tuned to live near 1 (no toe keeps the blacks deep); PBR Neutral for true colour and to agree with the piano's three.js scenes; the ACES fit only for a deliberate cinematic punch, accepting that per-channel curves turn bright orange yellow and blue neon cyan on the way to white. Re-expose when swapping curves: the same scene needs a different exposure under each. Wrong looks like a flat white plateau (no curve), grey highlights that never reach white (Reinhard), or washed-out greys (a curve applied to values already encoded).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "colour-tone.card",
//!  "twin": "arsenal/shaders/twins/tone.py", "status": "P0",
//!  "exemplars": ["4slGWM", "7cjGRR", "l3cfW4", "ldSfWV", "ffG3Rc", "ttScDc", "MfjyWK", "43jXWt", "WdB3Dw", "3XdXRr"],
//!  "learn": ["CP 4.1", "CP 5.2", "CP 5.4", "CP 5.5", "CP 5.7", "CP 5.10", "VA 7.2 family C", "study:WdB3Dw 6.10"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published formulas (credits above).
//
// WHY. Light in a scene has no ceiling and a screen does: 0..1. A tone curve is the limiter between them, an audio
// limiter with a soft knee: below the knee the signal passes nearly untouched, above it the gain eases off so nothing
// slams into the ceiling. Without one, distinct bright things merge into one flat white plateau. Order of the chain:
// expose (the gain knob), one curve, then grading, then srgbEncode, then dither.

// Exposure in camera stops: +1 doubles the light, -1 halves it. Brightness is set here, before the curve; a gamma knob
// after the curve changes contrast and saturation at the same time.
vec3 expose(vec3 lin, float ev) {
    return lin * exp2(ev);
}

// tanh per channel: slope 1 at black (no toe, so darks pass untouched), about 1.4 stops of headroom above 1 (0.99 by
// x = 2.66). Right for glow fields; wrong for lit scenes with real highlights. The argument is clamped at 10, where
// tanh already rounds to 1.0, because some drivers build tanh from exponentials that overflow to NaN past about 88.
vec3 tmTanh(vec3 x) {
    return tanh(clamp(x, 0.0, 10.0));
}

// 1 - e^-x per channel: film density saturating. Slope 1 at black, softer than tanh (0.99 by x = 4.6).
vec3 tmExp(vec3 x) {
    return 1.0 - exp(-max(x, vec3(0.0)));
}

// x / (1 + x) per channel: gentle, but approaches white slowly (0.99 needs x = 99), so highlights look a little grey.
vec3 tmReinhard(vec3 x) {
    vec3 light = max(x, vec3(0.0));
    return light / (1.0 + light);
}

// Narkowicz's rational fit to the ACES look, with the 0.6 pre-exposure that matches the reference inside. A real toe
// (slope 0.13 at black) and contrast; per-channel, so saturated lights skew toward the six primaries and secondaries on
// the way to white. The fit reaches 1 by 0.6x = 7.24; the clamp at 1000 only keeps aces * aces finite.
vec3 tmAcesFit(vec3 x) {
    vec3 pre = clamp(0.6 * x, 0.0, 1000.0);
    vec3 upper = pre * (2.51 * pre + 0.03);
    vec3 lower = pre * (2.43 * pre + 0.59) + 0.14;
    return clamp(upper / lower, 0.0, 1.0);
}

// Khronos PBR Neutral: a base colour under neutral light comes out as itself. A tiny toe removes the specular floor,
// everything is identity up to a knee of 0.76, and above it only the PEAK channel is compressed (Reinhard-like) while
// the colour drifts gently toward white. Hue around the white axis never turns. The transform the piano renders with.
vec3 tmPbrNeutral(vec3 x) {
    const float fresnel = 0.04;            // a dielectric's reflectance: the floor the toe removes
    const float knee = 0.8 - fresnel;      // compression starts here
    const float drift = 0.15;              // how fast a compressed peak drifts toward white
    float low = min(x.r, min(x.g, x.b));
    float toe = low <= 2.0 * fresnel ? low - low * low / (4.0 * fresnel) : fresnel;
    vec3 lifted = x - toe;
    float peak = max(max(lifted.r, lifted.g), lifted.b);
    if (peak <= knee) {
        return lifted;
    }
    float room = 1.0 - knee;
    float newPeak = 1.0 - room * room / (peak + room - knee);
    vec3 squeezed = lifted * (newPeak / peak);
    float toWhite = 1.0 - 1.0 / (drift * (peak - newPeak) + 1.0);
    return mix(squeezed, vec3(newPeak), toWhite);
}

// gain * sqrt(x): a root lifts faint accumulated glow into view and compresses bright sparks, with no filmic curve.
vec3 tmRootGain(vec3 x, float gain) {
    return gain * sqrt(max(x, vec3(0.0)));
}

// Gamma on the colour's magnitude only: c * |c|^(1/gamma - 1). Per-channel gamma lifts the weak channels more than the
// strong one and bleaches the tint of many summed dim emitters (an aurora of thousands of faint samples); this keeps
// the colour's direction, so its hue and saturation, and bends only how bright it is.
vec3 displayHueSafeGamma(vec3 c, float gamma) {
    return c * pow(max(length(c), 1.0e-10), 1.0 / gamma - 1.0);
}
