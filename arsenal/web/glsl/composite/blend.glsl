//! {"name": "composite-blend", "kind": "helper", "cat": "M1", "family": "M", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Thomas Porter and Tom Duff, 'Compositing Digital Images' (SIGGRAPH 1984, https://doi.org/10.1145/800031.808606): over, and why premultiplied colour makes it one line",
//!   "colour and post report, section 6 and 1.6 (research/reviewed/shader-school-2026-10-13/color-post.md): light adds, screen bounds; the canvas is premultiplied",
//!   "the HAL 4000 study (https://www.shadertoy.com/view/MtXczn, Manwe): max, not add, keeps crossing lines crisp"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "cmpOver is Porter-Duff over for straight (unpremultiplied) colour and returns straight colour; cmpOverPremul is the same for premultiplied colour (rgb already times alpha) and is associative; cmpUnder adds a premultiplied layer BEHIND an accumulator (front-to-back) and leaves an accumulator at alpha >= 0.998 untouched; cmpAdd is light adding to light (unbounded); cmpScreen clamps both inputs to 0..1 and returns 0..1; cmpMax is the per-channel maximum. Honest for alpha in 0..1; colours in linear light for add and max, display values for screen.",
//!  "note": "Pick by what the layers ARE. Emitters in the same space add (cmpAdd): two lamps are twice the light. Lines that should stay lines when they cross take cmpMax, so a crossing never blooms to white. Translucent sheets stack with over: back-to-front with cmpOverPremul, or front-to-back with cmpUnder inside a march, breaking the loop once alpha passes about 0.998. Screen is for display values only; on HDR light it stops being bounded. Wrong looks like dark fringes round soft edges (straight colour handed to the premultiplied form), white-out where lines cross (add where max was meant), or a march that never stops costing (no early break).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "composite-blend.card",
//!  "twin": "arsenal/shaders/twins/finish.py", "status": "P0",
//!  "exemplars": ["MfjyWK", "NslGRN", "ttScDc", "MdsXWM", "ltdcW7", "MtXczn", "XsjXRm"],
//!  "learn": ["CP 6", "SR 7.2", "craft secret 6"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics credited above.
//
// WHY. A mixing desk for pictures. Each layer is a channel strip; how two strips combine decides whether they read as
// light (add), as glass (over), as ink lines (max) or as a bounded glow (screen). Premultiplied colour is the studio
// convention because it makes "over" a single multiply-add, the same at every step of a stack.

// Straight alpha: rgb is the colour, a the coverage. The result is straight too.
vec4 cmpOver(vec4 front, vec4 back) {
    float behind = back.a * (1.0 - front.a);               // how much of the back still shows
    float alpha = front.a + behind;
    vec3 sum = front.rgb * front.a + back.rgb * behind;    // premultiplied sum
    return alpha > 0.0 ? vec4(sum / alpha, alpha) : vec4(0.0);
}

// Premultiplied alpha: rgb is already colour times coverage. Associative: a stack can be merged in any grouping.
vec4 cmpOverPremul(vec4 front, vec4 back) {
    return front + back * (1.0 - front.a);
}

// Front-to-back: the accumulator holds what is nearer; the layer (premultiplied) goes behind it. The caller breaks
// its march when acc.a passes 0.998 (under half an 8-bit step of light is left to gather); a late layer is a no-op.
void cmpUnder(inout vec4 acc, vec4 layer) {
    if (acc.a >= 0.998) return;
    acc += layer * (1.0 - acc.a);
}

// Light adding to light.
vec3 cmpAdd(vec3 a, vec3 b) {
    return a + b;
}

// Screen: 1 - (1 - a)(1 - b), a brightening that can never pass 1.
vec3 cmpScreen(vec3 a, vec3 b) {
    vec3 da = clamp(a, 0.0, 1.0);
    vec3 db = clamp(b, 0.0, 1.0);
    return 1.0 - (1.0 - da) * (1.0 - db);
}

// The brighter of the two, channel by channel: crossings stay as bright as one line, never brighter.
vec3 cmpMax(vec3 a, vec3 b) {
    vec3 brighter = max(a, b);
    return brighter;
}
