//! {"name": "composite-parity", "kind": "helper", "cat": "K3", "family": "K", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Wikipedia, 'Even-odd rule' (https://en.wikipedia.org/wiki/Even%E2%80%93odd_rule): a point is inside when an odd number of boundaries enclose it",
//!   "Wikipedia, 'Exclusive or' (https://en.wikipedia.org/wiki/Exclusive_or): the truth table, and why XOR is associative and commutative",
//!   "Hex Glitch study (https://www.shadertoy.com/view/lfscD7): five binary layers combined by XOR need no ordering decisions, and near-equal inset copies make moire (the technique, read in words; no code taken)",
//!   "Hexagone study (https://www.shadertoy.com/view/wsl3WB, Martijn Steinrucken): the exclusive blend is one line away from the additive one and gives a graphic mood (the technique, read in words)"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "cmpXor(a, b) = a (1 - b) + b (1 - a) with both inputs clamped to [0, 1]: on 0 and 1 it is the XOR truth table; on coverages it is the fraction of the pixel covered by exactly one of two independently placed shapes, so antialiased edges combine without a jagged seam. Equivalently 1 - 2 cmpXor(a, b) = (1 - 2a)(1 - 2b), a signed product, so any number of layers can be combined in any grouping and any order with the same result; cmpXor(a, 0) = a and cmpXor(a, 1) = 1 - a. The result lies in [0, 1].",
//!  "note": "The graphic combine: layers of ink where an overlap cancels instead of piling up, the even-odd rule a vector font uses for its holes. Combine COVERAGES (aaFill of a distance, a mask), not lit colours, then colour the result: XOR of light is not light. It needs no draw order, so a pile of shapes, stripes and rings becomes a pattern of its own (two copies of a ring set at nearly the same scale give moire for free). Use it where a picture should read as print or op-art; for light that adds use cmpAdd, for lines that cross cleanly cmpMax. Wrong looks like a one-pixel dark seam along every shared edge (two hard steps XORed instead of two coverages), colours that go negative or past white (unclamped inputs), or an overlap that brightens (add where XOR was meant).",
//!  "targets": {"glsl": "100", "needs": []}, "card": "composite-parity.card",
//!  "twin": "arsenal/shaders/twins/parity.py", "status": "P1",
//!  "exemplars": ["lfscD7", "wsl3WB"],
//!  "learn": ["study:lfscD7 6.5", "study:wsl3WB 4.7"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics credited above.
//
// WHY. A light switch at each end of a staircase: flip either and the light changes, whatever the other one says.
// That is XOR, and it is why a pile of overlapping shapes combined this way never needs a draw order. Written on
// coverages it is also the antialiased form: a pixel half covered by each of two shapes is half lit, not striped.

// Exactly one of two coverages: a (1 - b) + b (1 - a).
float cmpXor(float a, float b) {
    float first = clamp(a, 0.0, 1.0);
    float second = clamp(b, 0.0, 1.0);
    return first + second - 2.0 * first * second;
}
