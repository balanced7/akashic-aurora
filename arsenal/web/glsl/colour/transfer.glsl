//! {"name": "colour-transfer", "kind": "helper", "cat": "H1", "family": "H", "version": "1.0.0", "order": 10,
//!  "license": "Apache-2.0",
//!  "credits": ["IEC 61966-2-1:1999, the sRGB standard (https://webstore.iec.ch/publication/6169; the formulas as summarised at https://en.wikipedia.org/wiki/SRGB): the piecewise transfer curve",
//!   "ITU-R BT.709 (https://www.itu.int/rec/R-REC-BT.709): the luminance weights of the sRGB primaries",
//!   "John Novak, 'What every coder should know about gamma' (https://blog.johnnovak.net/2016/09/21/what-every-coder-should-know-about-gamma/): why the maths happens in light, not in code values",
//!   "Bjorn Ottosson, 'A perceptual color space for image processing' (https://bottosson.github.io/posts/oklab/): why OKLab needs a cube root that survives negative light"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "srgbEncode and srgbDecode are the exact IEC 61966-2-1 curve and its inverse (round trip within 1e-6, HDR values above 1 continue the curve, negative input is black); luminance is Rec. 709 relative luminance and is honest only on LINEAR values; cbrtSigned is a cube root that keeps the sign and is finite everywhere.",
//!  "note": "Two currencies: light (linear, what adds and blends) and code values (encoded, what the screen stores). Do the maths in light, encode once at the very end, just before dither. Decode every texture, video frame and hand-picked colour before lighting it. Wrong looks like muddy dark middles in gradients and shrinking sparks (maths on code values), or washed-out greys with lifted blacks (encoded twice). Never luminance with the old (0.299, 0.587, 0.114) weights on linear light: blue greys out 58% too heavy.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "colour-transfer.card",
//!  "twin": "arsenal/shaders/twins/colour.py", "status": "P0",
//!  "exemplars": ["7d2fDW"], "learn": ["CP 1.3", "CP 1.4", "CP 2.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published formulas (credits above).
//
// WHY. A screen stores about 256 levels per channel, and the eye counts light in ratios, so the levels are spent on a
// curve: more of them in the darks, where the eye is fussy. That curve is the sRGB transfer function. It is like the
// pre-emphasis on a tape recorder: put it on exactly once on the way out, take it off exactly once on the way in, and
// never do arithmetic on the emphasised signal. Every surface that ends with srgbEncode speaks the same currency, which
// is what lets one palette or glow module look the same everywhere.

// Linear light to sRGB code values (the screen's currency). Below the knee the curve is a straight line, because a pure
// power has an infinite slope at black, which would amplify noise; above it, an offset 2.4 power that stays close to a
// 2.2 power over most of the range.
vec3 srgbEncode(vec3 lin) {
    vec3 light = max(lin, vec3(0.0));                     // negative light is black (and pow of a negative is NaN)
    vec3 toe = 12.92 * light;
    vec3 body = 1.055 * pow(light, vec3(1.0 / 2.4)) - 0.055;
    return mix(body, toe, lessThanEqual(light, vec3(0.0031308)));   // a select per channel, no arithmetic
}

// sRGB code values to linear light: the exact inverse. Use it on textures, video and colours picked by eye before any
// lighting, blending or blur.
vec3 srgbDecode(vec3 enc) {
    vec3 code = max(enc, vec3(0.0));
    vec3 toe = code / 12.92;
    vec3 body = pow((code + 0.055) / 1.055, vec3(2.4));
    return mix(body, toe, lessThanEqual(code, vec3(0.04045)));
}

// Relative luminance of linear Rec. 709 / sRGB light: how bright the colour looks, not the average of its channels.
// Green counts ten times blue.
float luminance(vec3 lin) {
    return dot(lin, vec3(0.2126, 0.7152, 0.0722));
}

// The cube root, sign kept. OKLab takes a cube root of cone responses that go negative for colours outside sRGB, and
// pow() of a negative number is undefined (NaN on most GPUs); this stays finite and continuous through zero.
vec3 cbrtSigned(vec3 x) {
    const float third = 1.0 / 3.0;
    vec3 magnitude = pow(abs(x), vec3(third));
    return sign(x) * magnitude;
}
