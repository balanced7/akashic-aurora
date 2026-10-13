# Colour science and post-processing for shaders

- **Shader school, 2026-10-13** -- one of eight topic reports written the night Daniel asked the house to
  "learn everything we can from these shaders and build out tooling to be able to build at that fidelity
  ourselves".
- **Topic:** what a pixel value means, colour spaces (sRGB, linear, HSV, OKLab/OKLCH), procedural
  palettes, exposure, tone mapping (Reinhard, Hejl, Hable, ACES fits, Uchimura, Lottes, AgX, Khronos
  PBR Neutral, GT7, tanh), bloom and glare (Kawase, dual filtering, the Call of Duty: Advanced
  Warfare mip chain), chromatic aberration, vignette, lens distortion, banding, dithering, film grain,
  colour grading and lookup tables.
- **Author:** Claude (the Vandor seat), as a research subagent. The sources were read on 2026-10-13. The
  corpus figures come from a read-only regex census of `state/arsenal/shaders/corpus` (335 shaders).
  No house code was changed, and nothing was rendered on the GPU.
- **Licence line:** everything below is written in our own words and mathematics. No corpus code is
  reproduced. Numeric constants are facts published by their authors, credited where they appear
  (OKLab: public domain or MIT; Narkowicz ACES fit: CC0 or MIT; Hill ACES fit: MIT; Hable piecewise
  curve: CC0; three.js tone-mapping chunk: MIT; GT7 2025 code: MIT; Tony McMapface: MIT or Apache-2.0).
  The primitive API in section 14 is new signatures only. The bodies still have to be written from the
  mathematics.

---

## 0. The one-page version

If you remember nothing else:

1. **There are two kinds of number in a colour pipeline, and mixing them is the root of most colour
   bugs.** *Scene-linear* numbers measure light: twice the number means twice the photons. *Display-encoded*
   numbers are what the monitor receives: they are bent by a transfer curve so that 8 bits are spent where
   the eye can tell the difference. Do the maths (lighting, blending, blurring, bloom) on light. Encode
   once, at the very end.
2. **Light has no ceiling, but a screen does.** A tone mapper (more accurately a *display transform*) is
   the soft limiter that squeezes unbounded light into the screen's 0..1. Without one, distinct bright
   things merge into one flat white plateau.
3. **Hue, lightness and saturation are not the same as the H, S and V of HSV.** HSV is a re-labelling
   of RGB. Pure blue and pure yellow have the same HSV "value", yet yellow is about 13 times brighter.
   For any operation the eye should read as "same brightness, different colour", use OKLab or OKLCH
   (Björn Ottosson, 2020).
4. **Every effect has a home in the chain.** Optical effects (bloom, chromatic aberration, vignette)
   live in scene-linear light *before* the tone mapper, because that is where a real lens does them.
   Look-grading lives on either side by design. Dithering lives *at the moment of quantisation*, in
   whatever encoding the value is stored in.
5. **Banding is a quantisation problem, and dither is the cure, but only when the dither is added before
   the rounding.** Adding grain after the image has already been rounded only adds noise on top of the bands.
6. **The corpus authors mostly work by eye in display space.** About three in four corpus shaders show
   no explicit encode step. None uses OKLab or AgX. Their looks are great, but their numbers do not
   compose. A house library has to be stricter than the shaders it learns from, because "tweak one
   module and everything updates" only works if every module speaks the same currency.

The rest of this report earns those six sentences.

---

## 1. What a pixel value means

### 1.1 Two currencies: light and code values

A renderer computes *radiance*, the amount of light arriving at the camera along each ray. That quantity
is **scene-linear**: it adds like light adds. Two lamps give twice the light of one, so the numbers
double. It is also **unbounded**: the sun is many thousands of times brighter than a white wall, and
nothing stops the number from being 4000.

A display takes a **code value**, usually 8 bits per channel (0..255, which shaders see as 0..1), and
turns it into light through a curve called the **EOTF** (electro-optical transfer function: "code in,
light out"). The inverse curve, from light to code, is the **OETF** (opto-electronic transfer
function). Encoding with the OETF and then decoding with the EOTF should return the light you started
with.

Hardware analogy: this is **companding**, exactly like mu-law in telephone audio. A phone line has
only 8 bits per sample, so quiet sounds get more of the codes and loud sounds fewer, because the ear
hears relative differences. The sRGB curve does the same for the eye. The curve is not "a correction
for old CRTs". It is a **compression codec for 8-bit storage**, and that is why it still exists.

### 1.2 Why the curve exists: the eye counts ratios

Perceived brightness is roughly a power of physical light (the exponent is about 1/2.2 to 1/3 over
ordinary ranges). Two consequences, both worth memorising:

- An sRGB-encoded 0.5 (code 128) is **about 21% of the light** of code 255, yet it *looks* about half as
  bright. Decoding gives ((0.5 + 0.055) / 1.055)^2.4 = 0.214.
- Middle grey, an 18% reflector (scene-linear 0.18), encodes to about 0.46, close to the middle of the
  code range. That is the whole point: the encoding spends half its codes below middle grey, where the
  eye is most sensitive.

What happens if you store *linear* light in 8 bits? The first non-zero linear step is 1/255 = 0.0039.
The first non-zero sRGB code decodes to linear 0.0003. The **darkest dozen sRGB codes all fit inside
the first linear code**, so a linear 8-bit buffer bands terribly in the shadows. Rule: **never store
linear light in fewer than 16 bits** (use RGBA16F, or R11G11B10F for HDR targets).

### 1.3 The sRGB transfer functions, exactly

sRGB is IEC 61966-2-1 (1999). Its primaries are the Rec.709 primaries (red x,y = 0.64, 0.33; green 0.30,
0.60; blue 0.15, 0.06), and its white point is D65 (0.3127, 0.3290).

Encoding (linear L to code value V, per channel, for L in 0..1):

```
V = 12.92 * L                         if L <= 0.0031308
V = 1.055 * L^(1/2.4) - 0.055         otherwise
```

Decoding (code value V to linear L):

```
L = V / 12.92                         if V <= 0.04045
L = ((V + 0.055) / 1.055)^2.4         otherwise
```

The straight segment near black exists because a pure power curve has an infinite slope at zero. That
is numerically awful and amplifies noise. The offset 2.4 power with a linear toe stays close to a 2.2
power over most of the range.

**The 2.2 controversy, plainly stated.** The standard defines the *encoding* as the piecewise curve
above. But it describes the *reference display* as a pure 2.2 power, with an 80 cd/m² screen in a
dim room. Real monitors ship both ways. Some follow the piecewise curve; many follow a pure 2.2. The
mismatch only matters in deep shadows (the ACES Central thread and the colour-science.org post in the
sources argue it in detail). Computed tonight:

| scene-linear | exact sRGB encode | pure 1/2.2 encode | 8-bit code (exact vs 2.2) |
|---|---|---|---|
| 0.0005 | 0.0065 | 0.0316 | 2 vs 8 |
| 0.001 | 0.0129 | 0.0433 | 3 vs 11 |
| 0.005 | 0.0610 | 0.0900 | 16 vs 23 |
| 0.01 | 0.0999 | 0.1233 | 25 vs 31 |
| 0.05 | 0.2478 | 0.2562 | 63 vs 65 |
| 0.18 | 0.4614 | 0.4587 | 118 vs 117 |
| 0.5 | 0.7354 | 0.7297 | 188 vs 186 |

Above about 5% light the two curves agree to within two codes. Below 1% they disagree by up to four
times: the `pow(1/2.2)` shortcut lifts the deep shadows. Neither is "wrong"; they are different
looks in the last stop of black. The house should pick one encoder and use it everywhere. The exact
piecewise curve is the safer default because it is what browsers assume when they colour-manage a canvas.

### 1.4 Luminance is not the average of R, G and B

The eye is far more sensitive to green than to blue. **Luminance** (Y, the physically defined
brightness) for linear Rec.709/sRGB primaries is

```
Y = 0.2126 R + 0.7152 G + 0.0722 B          (linear values only)
```

These three numbers are the middle row of the sRGB-to-XYZ matrix.

The other familiar triple, (0.299, 0.587, 0.114), is **Rec.601 luma**. It was defined for old
standard-definition video primaries and for *gamma-encoded* values. Using 601 weights on linear sRGB
over-weights red and blue: blue counts as 0.114 instead of 0.0722, 58% too bright. This is the most
common silent error in shader desaturation code. The house has two instances of it (section 13).

### 1.5 What mixing the currencies does on screen

Doing maths on encoded values is like adding decibels to get loudness: the units are logarithmic-ish,
so averages come out wrong. Specifically (John Novak's article catalogues these with pictures):

- **Gradients and blends between saturated colours go dark and muddy in the middle.** A red-to-green
  blend done on encoded values dips to a dark olive. The same blend in linear light stays bright yellow
  in the middle. Ottosson shows the same effect for green and magenta.
- **Blur and downsampling darken bright detail.** Averaging a white pixel with a black one in encoded
  space gives 0.5 encoded, which is 21% light, when the true average is 50%. Bright sparks shrink and
  dim; text looks too heavy or too thin.
- **Antialiased edges look ropy.** The coverage fraction is light, not code value.
- **Lighting looks plastic.** A Lambert falloff computed on encoded albedo gives too-fast terminators
  and blown highlights. Inigo Quilez's outdoor-lighting article makes the same point from the artist's
  side: light in linear space and the falloffs come out right without hand tuning.

The opposite mistake is **double encoding**: encoding a value that is already encoded. The result is
washed out, grey and low in contrast, and the blacks lift to grey. The classic way to cause it is to
apply `pow(1/2.2)` after a tone mapper that already bakes gamma in (the Hejl / Burgess-Dawson curve;
see 5.3).

### 1.6 WebGL specifics that bite

- A WebGL canvas has **no automatic sRGB encode** on the default framebuffer. The browser assumes the
  canvas already holds sRGB-encoded values. If your shader computes linear light and writes it out
  unencoded, the image is too dark and too contrasty: 0.18 grey shows as 0.18 *encoded*, which is
  2.7% light.
- Textures holding images (photos, video frames, UI colours picked in a colour picker) are
  **encoded**. Decode them before lighting or blending: use an `SRGB8_ALPHA8` internal format, which
  decodes in hardware, or decode in the shader.
- HDR intermediate targets need `RGBA16F` plus `EXT_color_buffer_float` to render into. Without that
  extension the chain falls back to 8 bits and bands.
- `precision highp float;` always. Mediump is 16-bit on many mobile GPUs. HDR values over about 65,000
  overflow to infinity, and hashes band into blocks (a trap the house cookbook already records).
- The canvas is composited with **premultiplied alpha** by default. If a shader outputs alpha below 1,
  its RGB must already be multiplied by alpha, or the edges glow bright.
- `pow(x, y)` is **undefined for negative x** and produces NaN (not-a-number). So does
  `pow(x, 1.0/3.0)` inside an OKLab conversion when a channel has gone negative. NaNs then spread
  through any blur or bloom as growing black (or white) squares. Clamp with `max(x, 0.0)` before every
  power, or use a sign-preserving cube root.

---

## 2. Colour models: RGB, HSV and HSL, OKLab and OKLCH

### 2.1 HSV and HSL: useful knobs, poor colour science

HSV (hue, saturation, value) and HSL (hue, saturation, lightness) are not colour spaces in the
perceptual sense. They are re-labellings of the RGB cube into a cylinder. Ottosson's point is that
they are remappings of RGB rather than models of vision, so they inherit every weakness of the RGB
they wrap. Their definitions:

- **Value** V = max(R, G, B). **HSV saturation** S = (max - min) / max.
- **Hue** is the angle around a hexagon whose corners are R, Y, G, C, B, M. Inside each 60-degree
  sextant one channel rises or falls linearly.
- The usual branch-free GPU form computes each channel as a clamped triangle wave of hue:
  `c_k = clamp(|6 * fract(h + k/3) - 3| - 1, 0, 1)` for k = 0, 1, 2. That ramp is then mixed toward
  white by (1 - S) and scaled by V.

The pitfalls, each visible on screen:

1. **Value is not brightness.** Pure blue (0, 0, 1) and pure yellow (1, 1, 0) both have V = 1. Their
   luminances are 0.072 and 0.928, a factor of about 13; their OKLab lightness is 0.45 and 0.97. A
   "constant V" rainbow therefore shows bright bands at yellow, cyan and magenta and a dark trough at
   blue.
2. **Mach bands at the sextant seams.** The triangle wave has corners at every multiple of 1/6, and the
   eye picks out those slope discontinuities as thin bright lines in a hue sweep. Inigo Quilez's
   "smooth HSV" fix replaces the piecewise-linear ramp with its cubic smoothstep, x²(3 - 2x), which
   makes the ramps smooth (C1-continuous) across the seams at almost no cost.
3. **Hue wraps.** Hue 0.95 and hue 0.05 are neighbours. Interpolate the difference along the shorter
   arc, or the transition sweeps the wrong way through the whole rainbow.
4. **Hue is undefined at grey.** When max = min, hue is 0/0. Pick a convention and never feed a grey
   pixel's hue to anything that animates.
5. **Blue drifts to purple as it lightens or desaturates** (Ottosson's colour-picker post). The
   hexagon's "blue" direction is not a constant perceived hue.
6. **HSV rotation does not preserve luminance.** Rotating blue by 180 degrees in HSV gives yellow at the
   same V and S, but at about 13 times the luminance.

When HSV is fine: as an *input UI* for picking a hue by eye, and for quick "rainbow by index" colouring
where perceptual evenness does not matter. When it is not: animating between state colours, rotating
hue on an image, desaturating, or building a palette where steps must look evenly spaced.

### 2.2 Perceptual spaces, and why OKLab won

A **uniform colour space** (UCS) is one where equal distances look like equal differences, with axes
for lightness and two opponent colour axes (red-green, yellow-blue). The 1976 classics, CIELAB and
CIELUV, have two famous flaws. Their lightness is acceptable, but their hue lines bend: blending blue
toward white in CIELAB passes through purple. The modern appearance model CAM16 is more accurate but
expensive and numerically fragile.

**OKLab** (Björn Ottosson, December 2020) was designed to be simple and to predict lightness, chroma
and hue well. His derivation, summarised:

- **Structure:** linear RGB goes to an LMS cone-response space by a 3x3 matrix; each channel goes
  through a cube root, a compressive non-linearity like the eye's; a second 3x3 matrix produces
  L (lightness), a (green to red) and b (blue to yellow). Two matrix multiplies and three cube roots:
  about the cost of one `pow` per channel.
- **Fitting:** the two matrices and the exponent were optimised against data generated from CAM16
  (colours of equal lightness, and colours of equal chroma) and against the Ebner-Fairchild data on
  uniform perceived hue. Error was measured in CIEDE2000. The constraints were that D65 white maps to
  L = 1 with a = b = 0, and that chroma scales like CIEDE2000. The exponent landed at about 1/3.
- **Result:** hue lines stay straight, so blue to white stays blue, and blends and gradients look even.

The conversion from **linear sRGB** (the combined matrix, which folds sRGB-to-XYZ into the LMS matrix,
as published by Ottosson):

```
l = 0.4122214708 R + 0.5363325363 G + 0.0514459929 B
m = 0.2119034982 R + 0.6806995451 G + 0.1073969566 B
s = 0.0883024619 R + 0.2817188376 G + 0.6299787005 B
l' = cbrt(l),  m' = cbrt(m),  s' = cbrt(s)
L = 0.2104542553 l' + 0.7936177850 m' - 0.0040720468 s'
a = 1.9779984951 l' - 2.4285922050 m' + 0.4505937099 s'
b = 0.0259040371 l' + 0.7827717662 m' - 0.8086757660 s'
```

The inverse cubes the cone values on the way back:

```
l' = L + 0.3963377774 a + 0.2158037573 b
m' = L - 0.1055613458 a - 0.0638541728 b
s' = L - 0.0894841775 a - 1.2914855480 b
l = l'^3,  m = m'^3,  s = s'^3
R =  4.0767416621 l - 3.3077115913 m + 0.2309699292 s
G = -1.2684380046 l + 2.6097574011 m - 0.3413193965 s
B = -0.0041960863 l - 0.7034186147 m + 1.7076147010 s
```

Verified tonight in Python: white gives L = 1.0000 with a = b = 0, and 0.18 grey gives L = 0.5646.
The primaries land at L = 0.628 (red), 0.866 (green), 0.452 (blue) and 0.968 (yellow).

**OKLCH** is OKLab in polar form: C = sqrt(a² + b²) (chroma, how colourful) and h = atan2(b, a) (hue
angle). Going back: a = C cos h and b = C sin h.

What OKLab gives a shader artist:

- **Gradients and blends** (mix in OKLab): even-looking ramps with no muddy middle and no purple drift.
- **Hue rotation at constant lightness** (rotate h in OKLCH): the honest version of "change the colour
  but not the brightness".
- **Saturation changes** (scale C, or scale a and b): saturating or desaturating without hue drift or
  lightness pumping.
- **Lightness-only edits** (L): contrast and brightness without touching colour.

The caveat: **the sRGB gamut is a lumpy shape inside OKLab.** Raising chroma, or rotating a saturated
colour's hue at fixed L, can leave the gamut: the RGB result has channels below 0 or above 1. Two
consequences follow. Use a sign-preserving cube root so negative intermediate values do not become
NaN. And clip back into the gamut properly (2.3), not by clamping each channel.

### 2.3 Gamut, the cusp, and clipping without hue shifts

For each hue, the sRGB gamut's cross-section in the lightness-chroma plane is roughly a triangle. Its
corners are black (L = 0), white (L = 1) and a **cusp**, the most colourful displayable colour of that
hue. The cusp sits at very different lightness for different hues: yellow's cusp is near L = 0.97,
blue's near L = 0.45. That is the geometric reason HSV's V lies about brightness.

Ottosson's gamut-clipping post compares strategies for pulling an out-of-gamut colour back inside
while holding hue fixed:

- **Per-channel clamp** (what `clamp(rgb, 0, 1)` does) shifts hue badly. It is the colour-space version
  of "the notorious six" (section 5.5).
- **Keep L, reduce C** until inside: preserves lightness and loses colourfulness.
- **Project toward a point on the grey axis** (L = 0.5, or the cusp's L): better behaved for very bright
  or very dark colours.
- **Adaptive projection** (his recommendation, alpha = 0.05) blends the two: lightness is kept for mid
  values and projected for extremes. The cusp is found with a polynomial guess plus one Halley step.

For a house library, a cheap and robust option is a **bisection on chroma at fixed L and h**: six to
eight steps, each a conversion to RGB and an in-gamut test. It is exact enough, simple to verify, and
costs nothing compared with a raymarch.

### 2.4 Which space for which job

| job | space | why |
|---|---|---|
| lighting, blending light, blur, bloom, CA, vignette, motion blur, TAA | scene-linear RGB | light adds linearly |
| gradients between two designer colours, palettes, state-colour transitions | OKLab (mix) or OKLCH (shortest-arc hue) | even perceived steps, no muddy middle, no purple drift |
| hue rotation of an image | OKLCH (rotate h, then gamut-clip) | constant lightness |
| saturation and desaturation | OKLab (scale a, b) or linear with Rec.709 luminance | no hue drift |
| contrast | log2 of scene-linear, around middle grey | contrast is a ratio |
| quantisation, dither, 8-bit storage | display-encoded (sRGB) | codes are spent perceptually |
| picking colours by hand | HSV or OKHSV in the *UI*; store the result as linear | knobs for humans, numbers for maths |

---

## 3. Procedural palettes

### 3.1 The cosine palette (Inigo Quilez)

Quilez's palette article gives a four-vector recipe that has become shader folklore:

```
colour(t) = a + b * cos( 2 pi (c t + d) )        (per channel; a, b, c, d are RGB vectors)
```

Read each channel as an oscillator (the hardware picture is three LFOs with a shared clock):

- **a: bias.** The channel's centre brightness.
- **b: amplitude.** How far the channel swings. The channel ranges over [a - b, a + b], so
  `a = b = 0.5` uses the full 0..1 and no channel ever clips.
- **c: frequency.** How many cycles the channel completes as t goes from 0 to 1. Quilez recommends
  whole or half numbers so palettes cycle cleanly. With a whole number in every channel, the palette is
  periodic over [0, 1] with infinitely smooth continuity, so `fract(t)` wraps seamlessly.
- **d: phase.** Where in its cycle each channel starts. Phases spread by thirds, (0, 1/3, 2/3), give a
  rainbow. Phases close together, such as (0, 0.1, 0.2), give two-hue gradients. One channel phase
  shifted by a half inverts that channel against the others.

Why it is so good for procedural work: it is **one line, has no branches, and is smooth in t**. Its
derivative, -2 pi c b sin(...), is bounded, so it never makes a sudden jump. Twelve numbers describe a
whole palette, which makes it **animatable** (lerp the parameters) and **storable** (a palette is a row in a
table). Quilez also notes that on a GPU a cosine is fast, faster than any attempt to approximate it.
The corpus confirms the idiom: his "Palettes" shader (ll2GD3) is the reference, and the census found
it in 15 shaders (Happy Jumping 3lsSzf, Cubescape Msl3Rr, reinder's raymarching tutorial 4dSfRc, and
others).

**The trap no one mentions: which currency is the palette in?** Quilez's palettes are tuned by eye on
a canvas that shows the values directly, so the parameters are *display-encoded* colours. If a lit,
linear-workflow shader uses the palette output as albedo and then encodes at the end, every palette
looks paler and less saturated than the reference. Fix: a house palette function returns display
values by contract, and a sibling decodes to linear (`pal_cos_lin`) for lit pipelines. Name the
currency in the function, never in a comment.

**Perceptual weakness.** Because it oscillates in RGB, a cosine rainbow has the HSV problem: its
lightness pumps up and down with hue. For an evenly bright sweep, see 3.2.

### 3.2 Perceptual palettes

- **OKLCH sweep:** fix L and C and run h from h0 over some number of turns. Every step has the same
  perceived lightness and colourfulness, the property the HSV rainbow lacks. Gamut-clip each sample,
  because constant chroma is not reachable at every hue for a given L.
- **Multi-stop OKLab ramp:** two or three designer colours mixed in OKLab. This is what CSS Color 4's
  `oklch()` interpolation does, and it is the right tool for the house's "analogous, never a rainbow"
  rule (cookbook, Palette).
- **Blackbody ramp** (fire, stars, hot metal): the colour of a radiator at temperature T. Planck's law
  integrated against the eye's colour matching functions gives a chromaticity curve that runs from red
  (about 1000 K) through orange and white (about 6500 K, D65) to blue-white. A small fitted
  approximation is plenty for shaders. Normalise it so the brightest channel is 1, and drive intensity
  separately (a hotter emitter is also *brighter*, by Stefan-Boltzmann, T⁴).

### 3.3 Grading tricks the corpus uses by hand

Pointers only (corpus files, never copied):

- **Colour-multiply grade before compression.** iq's Happy Jumping (3lsSzf, image.glsl near line 485)
  multiplies by a warm triple, compresses with a scaled Reinhard, encodes with `pow(0.4545)`, applies a
  smoothstep-shaped S-curve *after* encoding, and finishes with the separable frame vignette (7.3).
- **Per-channel power as split toning.** nimitz's Protean clouds (3l23Rh, image.glsl:139) raises each
  channel to a slightly different power (about 0.55 to 0.65). Because a power below 1 lifts darks more
  than brights, unequal exponents tint shadows and highlights differently: a two-tone grade from one
  line.
- **Channel-swizzle interpolation as hue shift.** The same shader lerps between `col.bgr` and `col.rgb`.
  That is a cheap, wildly non-perceptual hue rotation, controlled by a parameter.
- **mrange's tail** (Neonwave sunrise 7dyyRy, around lines 362-386): HSV colouring, `tanh` soft limits
  on additive glows, the Narkowicz ACES fit, then the *exact* sRGB encoder. It is the most "correct"
  chain in the corpus by this report's standards.

---

## 4. Exposure: from scene to camera

### 4.1 Stops, EV and middle grey

A **stop** is a doubling of light. Exposure in a renderer is just a multiply, `exposed = light * 2^EV`,
done in scene-linear before the tone mapper. Every tone mapper assumes a convention for where middle
grey (0.18) sits. Exposure is how you put the scene's "middle" there.

### 4.2 Physical camera exposure (Frostbite)

Sébastien Lagarde and Charles de Rousiers' "Moving Frostbite to Physically Based Rendering" (SIGGRAPH
2014 course) gives the photographic chain. The exposure value at ISO 100 is

```
EV100 = log2( N² / t * 100 / S )          (N = f-number, t = shutter seconds, S = ISO)
```

The saturation-based speed rule says the sensor clips at luminance L_max = (78 / (q S)) * 2^EV100,
with lens transmission q = 0.65 and S = 100. That is where the famous constant comes from: 78 / 65 =
**1.2**. Hence

```
exposure = 1 / (1.2 * 2^EV100)
```

From a measured average scene luminance, with the reflected-light meter constant K = 12.5:

```
EV100 = log2( L_avg * 100 / 12.5 )     which gives     exposure = 1 / (9.6 * L_avg)
```

(Bruno Opsenica's auto-exposure article uses the same 9.6.)

### 4.3 Automatic exposure

- **Log-average ("key") method** (Erik Reinhard et al. 2002, "Photographic Tone Reproduction for
  Digital Images"). Average the *logarithm* of luminance over the frame, with a small delta to avoid
  log 0, and exponentiate: L_avg = exp(mean(log(delta + Y))). Then scale so that L_avg lands on the
  **key** a: L = (a / L_avg) * Y. a = 0.18 is a normal scene; Reinhard's low-key and high-key examples
  roughly halve or double it. The geometric mean is used because a single sun pixel would wreck an
  arithmetic mean.
- **Histogram method** (Opsenica). Build a 256-bin histogram of log2 luminance with compute-shader
  atomics, leave out the near-black bin, and take the weighted average of the rest in log space.
  Engines often also trim a percentile at each end. It is more robust than the log average to small
  extreme regions.
- **Temporal adaptation.** Never jump. Move the adapted value toward the target with
  `adapted += (target - adapted) * (1 - exp(-dt / tau))`. This is frame-rate independent; a fixed lerp
  factor is not. Use different taus for brightening and darkening, as eyes do.

### 4.4 The single-pass reality (Shadertoy and the house bench)

Without a reduction pass there is no average luminance, so single-pass shaders use **fixed exposure
constants** chosen by eye. A recurring corpus pattern is accumulating glow across a raymarch to huge
values and dividing by a large constant just before a soft limiter (Xor's Singularity 3csSWB, mrange's
"Clearly a bug" 33cGDj). That constant *is* the exposure. Name it as one in house code.

---

## 5. Tone mapping, or the display transform

### 5.1 The job

A tone mapper maps [0, infinity) scene-linear to [0, 1] display-linear, before the encode. A good one:

1. **Holds the midtones near-linear**, so the image keeps its contrast where the eye looks.
2. **Rolls highlights off smoothly** (the *shoulder*), so bright things keep detail instead of clipping
   flat.
3. Optionally **compresses deep shadows** (the *toe*), which is the "filmic" crunch.
4. Gives saturated bright colours a **path to white**: a very bright red light should end up whitish,
   as it does on film and in the eye, rather than a flat saturated blob.
5. Avoids **hue skews** on that path.

Hardware analogy: a tone mapper is an **audio limiter with a soft knee**. Below the knee the signal
passes untouched. Above it, gain reduction rises smoothly, and the output can never exceed full scale.

Alex Tardif argues that the very word misleads; in his words, "There is no 'tone' being 'mapped'"
(Reframing Tonemapping in Games). His recommendation is to separate a **neutral compression step**
(the display rendering transform) from the **look** (grading), so artists are not fighting a look baked
into the compressor.

### 5.2 The simple curves, with their maths

All take x >= 0 per channel unless noted. "Slope at 0" tells you whether there is a toe: slope 1 means
the darks pass through linearly.

- **Reinhard:** f(x) = x / (1 + x). Slope at 0 is 1, f(1) = 0.5, and 1 - f(x) = 1/(1 + x), so it
  approaches white *slowly*: 0.99 needs x = 99. It never reaches white, so images look slightly grey
  in the highlights.
- **Extended Reinhard** with white point W: f(x) = x (1 + x/W²) / (1 + x). Check: f(W) = 1. Clamp above W.
- **Luminance-only Reinhard:** compute the curve on luminance Y and scale the colour by f(Y)/Y. This
  preserves hue and saturation exactly, which is both its strength and its flaw (5.5). Reinhard-Jodie
  (Matt Taylor's write-up) blends the per-channel and luminance versions.
- **tanh shoulder:** f(x) = tanh(x). Slope at 0 is 1, with no toe, and it is the most linear of all in
  the darks. But 1 - tanh(x) is about 2e^(-2x), so it reaches 0.99 by x = 2.66. **It has about 1.4
  stops of headroom above 1.0.** That makes it perfect for additive glow fields that are tuned to sit
  below about 2 and then explode (Xor, mrange), and poor for physically lit scenes with real
  highlights. The house bed uses it, which is right for an ambient field.
- **Exponential:** f(x) = 1 - e^(-x). Slope at 0 is 1, f(1) = 0.632, and it reaches 0.99 by x = 4.6.
  It is the classic photographic "film density saturates" curve: Poisson exposure of grains. In the
  census, 41 shaders use it, often for fog and absorption as well as tone.
- **Algebraic:** f(x) = x / sqrt(1 + x²). Like tanh near 0 but with a longer tail (0.99 at about 7).

### 5.3 The filmic family

- **Hejl / Burgess-Dawson (Jim Hejl and Richard Burgess-Dawson, via John Hable's blog).** A rational
  fit to a film response that has the 2.2 encoding *baked in*. Compute x = max(0, input - 0.004), then
  f(x) = x (6.2x + 0.5) / (x (6.2x + 1.7) + 0.06). **Its output is already display-encoded: do not
  encode it again** (double-encoding gives washed-out greys). Middle grey 0.18 lands at 0.51 encoded.
- **Uncharted 2 (John Hable).** With A = 0.15, B = 0.50, C = 0.10, D = 0.20, E = 0.02, F = 0.30,
  define u(x) = ((x (Ax + CB) + DE) / (x (Ax + B) + DF)) - E/F. The output is u(2x) / u(W) with an
  exposure bias of 2 and white point W = 11.2. There is a gentle toe and a long shoulder, and it needs
  an encode afterwards.
- **Hable's piecewise power curves (2017, code CC0).** Three segments (toe, linear, shoulder), each of
  the form y = e^(ln A + B ln x), offset and scaled. Junctions are matched in value and slope: for the
  toe, B = m x0 / y0 and ln A = ln y0 - B ln x0. Artists get five intuitive controls (toe strength,
  toe length, shoulder strength in stops, shoulder length, shoulder angle) and the curve is exactly
  invertible. Hable argues for applying it **per channel**, so overexposed colours desaturate toward
  white.
- **Uchimura (Hajime Uchimura, Gran Turismo Sport, CEDEC 2017).** An explicit toe, linear and shoulder
  blend with photographer-friendly parameters: P max brightness 1.0, a contrast 1.0, m start of the
  linear section 0.22, l its length 0.4, c black tightness 1.33, b pedestal 0. With l0 = (P - m) l / a,
  S0 = m + l0, S1 = m + a l0 and C2 = a P / (P - S1):

  ```
  toe      T(x) = m (x/m)^c + b
  linear   L(x) = m + a (x - m)
  shoulder S(x) = P - (P - S1) exp( -C2 (x - S0) / P )
  weights  w0 = 1 - smoothstep(0, m, x),  w2 = step(m + l0, x),  w1 = 1 - w0 - w2
  out      = T w0 + L w1 + S w2
  ```

  With these defaults middle grey passes through almost unchanged (0.18 to 0.179). The curve is
  linear through the mids, and the shoulder converges fast (0.99 by x = 2.3), so it suits scenes
  exposed so that highlights sit near 1 to 3.
- **Lottes (Timothy Lottes, AMD, GDC 2016).** A tone mapper built from two primitives: a power for
  contrast (the toe) and a generalised Reinhard for the shoulder:

  ```
  z = x^a                     (a = contrast)
  y = z / (z^d * b + c)       (d = shoulder; b, c anchor the curve)
  ```

  The two anchors are "middle grey maps to midOut" and "hdrMax maps to 1". Each is linear in b and c, so
  they solve in closed form. Write zm = midIn^a and zh = hdrMax^a. Then b = (zh midOut - zm) /
  ((zh^d - zm^d) midOut) and c = zh - zh^d b. Commonly quoted defaults are a = 1.6, d = 0.977,
  hdrMax = 8, midIn = 0.18 and midOut = 0.267. (Computed tonight: 0.267 is exactly where the unscaled
  Narkowicz ACES fit sends 0.18.) Lottes' practical point: **drive a "brightness" setting through
  midOut, before the tone mapper.** A gamma knob after tone mapping changes contrast and saturation at
  the same time.

### 5.4 ACES and its two famous fits

ACES (the Academy Color Encoding System) is the film industry's colour pipeline. Its display path is
a Reference Rendering Transform (RRT, the "look") followed by an Output Device Transform (ODT, the
display). The full transforms are long. Games use fits:

- **Krzysztof Narkowicz (2016, CC0 or MIT):** f(x) = x (2.51x + 0.03) / (x (2.43x + 0.59) + 0.14),
  clamped to [0, 1]. Its peak fit error is 0.0138. It includes a pre-exposure so that 1.0 maps to about
  0.8; to match the reference, multiply the input by 0.6 first. Properties computed tonight: slope at
  0 is 0.21 (a real toe that crushes darks), middle grey goes to 0.267 (0.140 with the 0.6 pre-scale),
  and the curve hits 1.0 at x = 7.24. Narkowicz himself warns that a luminance-only fit over-saturates
  bright colours. Applied per channel, it also skews hues.
- **Stephen Hill (BakingLab, MIT):** an input matrix (sRGB to the ACES working space AP1, folding in
  the white-point change and the RRT's saturation tweak), a rational curve
  `(v (v + 0.0245786) - 0.000090537) / (v (0.983729 v + 0.4329510) + 0.238081)`, and an output matrix
  back to sRGB. This is the more faithful fit, and the one three.js uses for "ACESFilmic" (with an
  input divided by 0.6).

Matrix coefficients (Hill, rows):

```
in  = [0.59719 0.35458 0.04823; 0.07600 0.90834 0.01566; 0.02840 0.13383 0.83777]
out = [1.60475 -0.53108 -0.07367; -0.10208 1.10813 -0.00605; -0.00327 -0.07276 1.07602]
```

ACES gives a strong, contrasty, "cinematic" look, and that is both why it spread and why people left
it. The look is baked into the compressor, and saturated lights skew hue on the way to white.

### 5.5 Per-channel versus hue-preserving: the core trade-off

This is the deepest idea in the topic.

**Per-channel curves** (Reinhard per channel, Hable, the ACES fits, tanh) compress each of R, G and B
independently. Take a bright orange light, (4, 2, 0.4) times k. As k grows, the red channel saturates
first, green catches up, and blue lags far behind. The channel *ratios* change, so the **hue changes**:
orange goes to yellow, and then to white. Pure-ish colours get pushed toward the nearest of the six
primaries and secondaries (R, Y, G, C, B, M) before going white. The name **"the notorious six"** for
this was popularised by Troy Sobotka in the work that led to AgX. On screen: fire turns lemon yellow, blue neon turns cyan-white, skin in strong
sun goes orange-yellow. There is an upside. The same mechanism gives a *path to white*, which reads as
"very bright".

**Hue-preserving curves** (luminance-only or max-RGB) keep the ratios exactly. Hue is perfect, but a
saturated light never reaches white: it becomes a flat, posterised blob of maximum-saturation colour.
Saturated colours can also exceed the gamut at the top.

The modern answer is **hue-preserving compression plus a deliberate, controlled path to white**:

- **Lottes' max-RGB split:** tone-map max(R, G, B) and keep the ratio rgb / max separately. Then push
  the ratio toward white as a function of the tone-mapped maximum (his "crosstalk"), in a power-warped
  space so the brighter channels move first. That warp is his *indirect* path to white, which keeps
  saturation longer than a direct lerp.
- **Khronos PBR Neutral** (5.7): compresses the peak channel and adds a separate, gentle desaturation.
- **AgX** (5.6): per-channel, but *after* rotating and insetting the primaries, so the six skews are
  tamed.
- **GT7 (Polyphony Digital, 2025, MIT code):** runs a per-channel curve and *also* a version that keeps
  chroma in a perceptual space (ICtCp or Jzazbz), with chroma faded in highlights. It then **blends the
  two** (blend ratio 0.6). The published defaults include an SDR paper white of 250 nits and a chroma
  fade from 0.98 to 1.16.

### 5.6 AgX (Troy Sobotka, with Eary Chow and others; Blender's default since 4.0)

AgX (the chemical symbol of silver halide) is a display transform built to give a graceful path to
white without the six. Its structure, as implemented in Filament and three.js (MIT, constants from
Blender's configuration):

1. **Inset.** Multiply linear Rec.709 (or Rec.2020) by an "inset" matrix that pulls the primaries
   slightly toward each other and rotates them a little. This mixes a bit of every channel into every
   other, so a per-channel curve now desaturates toward white *gracefully* instead of snapping to the
   six.
2. **Log encode.** Take log2 of each channel, clamp it to [-12.47393, +4.026069] and normalise to 0..1.
   The range is measured from 1.0, and middle grey lands at (log2 0.18 + 12.47393) / 16.5 = 0.606, so
   the window is exactly **10 stops below middle grey and 6.5 above** (16.5 stops in all).
3. **Sigmoid.** Apply the base contrast curve. The real-time versions use a degree-6 polynomial fitted
   to Blender's curve, with coefficients 15.5, -40.14, 31.96, -6.868, 0.4298, 0.1191 and -0.00232 from
   x^6 down to x^0.
4. **Outset.** Apply an inverse-ish matrix to restore purity. It is deliberately *not* the exact
   inverse; the mismatch counteracts a drift toward magenta in bright values (Allen Pestaluky's Godot
   notes).
5. **Encoding.** The output is display-encoded (about gamma 2.2). Pipelines that encode later apply
   `pow(x, 2.2)` here to get back to display-linear.
6. **Looks.** "Punchy" and "Golden" are ASC CDL grades (slope, offset, power, then saturation; 9.4)
   applied in the encoded domain.

Computed tonight on neutral grey: 0.18 lands at about 0.50 encoded (0.215 linear). The curve reaches
0.95 only around x = 9.4. Its long shoulder keeps highlight detail, and it looks flatter and greyer
than ACES out of the box. That is by design: the look is meant to be added on top. darktable's AgX
module exposes the inner controls (attenuation and rotation of the primaries, pivot, contrast, toe
and shoulder powers, purity restore) if you want to see what each does.

### 5.7 Khronos PBR Neutral (Emmett Lalish and Khronos, 2024)

Designed for **product rendering**: a base colour under neutral white light should come out *exactly*
the base colour, so an e-commerce sofa matches its fabric swatch. The algorithm, per pixel:

```
x = min(R, G, B)
f = x - x²/(4 F)    if x <= 2F,   else  F             (F = 0.04, a dielectric's Fresnel reflectance)
rgb -= f                                              (removes the specular "floor" from the toe)
p = max(R, G, B)
if p <= Ks: done                                      (Ks = 0.8 - F = 0.76)
pn  = 1 - (1 - Ks)² / (p + 1 - 2 Ks)                  (Reinhard-like compression of the peak only)
rgb *= pn / p
g   = 1 - 1 / (Kd (p - pn) + 1)                       (Kd = 0.15)
rgb = mix(rgb, vec3(pn), g)                           (gentle desaturation toward white)
```

Below the knee it is the identity, apart from the tiny toe. Hue around the white axis is never
changed, the function is smooth (continuous derivatives) and it is analytically invertible. It does
no gamut mapping. Use it when the colours are the product and you want highlights to roll off without a
"look". Avoid it for moody scenes that want a filmic toe.

### 5.8 LUT-based display transforms

**Tony McMapface** (Tomasz Stachowiak, MIT or Apache-2.0) ships as a 48³ 3D LUT sampled through an
`x/(x+1)` shaper. It aims to be understated and hue-preserving, deliberately models the
Helmholtz-Kohlrausch effect (saturated colours look brighter than their luminance), and outputs linear
values. It is a good example of the "bake a complex transform into a texture" pattern (9.6).

### 5.9 The comparison table (computed tonight)

Neutral grey input; display-linear output unless noted. "x for 0.99" is how hard you must drive the
input to get within 1% of white, a measure of highlight headroom.

| operator | f(0.18) | encoded f(0.18) | f(1) | slope at 0 | x for 0.95 | x for 0.99 |
|---|---|---|---|---|---|---|
| Reinhard x/(1+x) | 0.153 | 0.427 | 0.500 | 1.00 | 19.0 | 99.4 |
| tanh | 0.178 | 0.459 | 0.762 | 1.00 | 1.84 | 2.66 |
| 1 - exp(-x) | 0.165 | 0.443 | 0.632 | 1.00 | 3.02 | 4.64 |
| x / sqrt(1 + x²) | 0.177 | 0.458 | 0.707 | 1.00 | 3.05 | 7.04 |
| ACES Narkowicz (no pre-scale) | 0.267 | 0.553 | 0.804 | 0.22 | 2.88 | 5.60 |
| ACES Narkowicz x 0.6 | 0.140 | 0.410 | 0.673 | 0.13 | 4.78 | 9.31 |
| ACES Hill (grey axis) | 0.106 | 0.358 | 0.619 | ~0 (toe) | 6.50 | 16.1 |
| Hable Uncharted 2 (bias 2, W 11.2) | 0.128 | 0.393 | 0.493 | 0.77 | 4.55 | 5.38 |
| Uchimura GT (defaults) | 0.179 | 0.460 | 0.828 | 0.12 | 1.58 | 2.33 |
| Lottes (1.6, 0.977, 8, 0.18 to 0.267) | 0.267 | 0.554 | 0.806 | ~0.05 | 3.27 | 6.50 |
| Khronos PBR Neutral | 0.140 | 0.410 | 0.869 | ~0 | 1.71 | 6.38 |
| AgX base (decoded with 2.2) | 0.215 | 0.501 | 0.590 | ~0 | 9.40 | 15.3 |
| Hejl / Burgess-Dawson | (output already encoded: 0.508) | - | 0.841 enc. | - | - | - |

How to read it: the curves split cleanly into **"darks untouched, short headroom"** (tanh, exp,
Uchimura) and **"crushed toe, long headroom"** (Hill ACES, AgX). The first group suits glow and
abstract fields that live near 1. The second suits physically lit scenes with real highlights. The
same scene needs **different exposure** under each, so swapping a tone mapper without re-exposing is
not a fair comparison (Matt Taylor makes the same point).

### 5.10 Choosing for the house

| content | default | why |
|---|---|---|
| ambient glow fields (the aurora bed, First Light, abstract sketches) | tanh, or 1 - exp(-x), after a named exposure | no toe keeps the deep blacks the brief wants; the fields are tuned to live near 1 |
| lit 3D scenes (raymarched objects, the avatar, three.js scenes) | AgX plus an optional look, or Khronos PBR Neutral for "true colour" pieces | graceful path to white with no hue skews; separates compression from look |
| a cinematic "punch" look on purpose | Hill ACES fit | the look people recognise; accept the hue skews |
| artist-tunable curve with presets | Lottes or Uchimura | interpretable parameters; mid-grey anchoring makes presets portable |

Whatever the choice, it must be **one function** that every surface calls (section 14, `display_out`).

---

## 6. Bloom, glare and scattering

### 6.1 The physics: a point is never a point

A real lens and the eye spread every point of light into a **point spread function** (PSF). The PSF
has a sharp core and a long, faint tail, caused by scattering in the glass and in the eye's cornea,
lens and retina, by diffraction at the aperture, and by reflections between lens elements. Greg
Spencer, Peter Shirley, Kurt Zimmerman and Donald Greenberg's "Physically-Based Glare Effects for
Digital Images" (SIGGRAPH 1995) modelled the eye's version: bloom from scattering, *flare lines*
(radial streaks) and the *lenticular halo* (a rainbow ring) from diffraction. Their key insight is
that glare **raises perceived brightness beyond what the display can show**. It is a brightness cue the
brain reads as "this is brighter than white". That is why bloom matters.

Mathematically, bloom is the **convolution** of the HDR image with the PSF. A heavy-tailed PSF is
well approximated by a **sum of Gaussians of doubling width**, and that is exactly what a mip-chain
bloom computes. Hardware analogy: it is a cache hierarchy (L1, L2, L3, each a coarser copy). Each
level is cheap because it is small, and summing the levels rebuilds a wide kernel no single pass could
afford.

### 6.2 Threshold or energy conservation?

- **Classic bloom:** threshold (keep only pixels above 1.0), blur, add back on top. It is cheap and
  controllable, but a hard threshold makes bloom pop on and off as values cross it, and *adding* adds
  energy.
- **Soft knee:** replace the threshold with a quadratic ramp around it. With brightness b = max channel,
  threshold T and knee width k, the contribution is max(b - T, ramp) / b, where
  ramp = clamp(b - T + k, 0, 2k)² / (4k). The bloom then fades in smoothly.
- **Energy-conserving bloom** (Jorge Jimenez's COD:AW approach, popularised by the LearnOpenGL guest
  article): no threshold at all. Blur the *whole* HDR image and composite with
  `out = mix(scene, bloom, s)`, with s around 0.04. The blur preserves total energy, so the mix
  redistributes a fraction s of every pixel's light to its neighbourhood and no light is created.
  Because the image is HDR, the bright things dominate the blur anyway. This is the physically
  motivated default for lit scenes. Thresholded bloom stays an art tool.

### 6.3 Masaki Kawase's filters (GDC 2003, DOUBLE-S.T.E.A.L. / Wreckless)

- **Kawase blur:** downsample to a quarter by a quarter, then repeatedly apply a 4-tap kernel whose taps
  sit on the **diagonals at distance (i + 0.5) texels** on iteration i, ping-ponging between two
  textures. Each tap lands between four texels, so the bilinear filter averages those four for free:
  4 fetches buy 16 texels. Iterating with growing offsets approximates a large Gaussian. Hardware
  analogy: it gets its parallelism from the texture unit, a fixed-function adder already sitting in
  the pipe. Marius Bjørge's comparison used the distance sequence 0, 1, 2, 3, 4, 4, 5, 6, 7. Intel's
  blur investigation measured a 127x127 Kawase blur at half resolution in 0.5 ms against 3 ms for a
  Gaussian (Radeon R9-290X), and noted there is no general formula mapping a target Gaussian to Kawase
  offsets; presets are empirical.
- **Kawase light streaks** (as transcribed in Chris Oat's GDC Europe 2003 notes): for each streak
  direction, sample along the direction with sample s weighted by a^(b s), where attenuation a is about
  0.9 to 0.95 and b = 4^(n - 1) on pass n. The kernel's reach grows fourfold per pass, so three passes
  of four samples reach 64 texels. Run one streak per direction (four or six for a star) and combine.
  The direction can even come from a per-pixel map: Wreckless used a wiper-scratch groove map so
  streaks followed the windscreen.

### 6.4 Dual filtering (Marius Bjørge, ARM, SIGGRAPH 2015)

Built for bandwidth-starved mobile GPUs:

- **Downsample** (each pass halves resolution): the centre tap, weight 1/2, plus four taps at the
  half-texel diagonals, weight 1/8 each.
- **Upsample** (each pass doubles resolution): eight taps, four at the diagonal half-texel positions
  with weight 2 and four on the axes at one texel with weight 1, all divided by 12.

With 8 passes (down then up) it matched a 97x97 Gaussian at about 50 dB PSNR, like Kawase, and it was
more temporally stable than naive mip generation. Measured on a Mali-T760 MP8 at 1080p: Gaussian
41.9 ms, box 21.4 ms, Kawase 4.5 ms, dual filter **2.8 ms**. At 720p the dual filter took 1.7 ms. Its
bandwidth chart puts it among the lowest-traffic methods compared.

### 6.5 The Call of Duty: Advanced Warfare mip chain (Jorge Jimenez, SIGGRAPH 2014)

The current reference for quality bloom:

- **Downsample with a 13-tap filter.** It reads as five overlapping 2x2 box averages: one centred box
  (weight 0.5) and four corner boxes (0.125 each). In the LearnOpenGL write-up that is the centre tap
  at 0.125, the four outer corners at 0.03125, the four outer edges at 0.0625 and the four inner
  diagonals at 0.125, summing to 1. It suppresses the aliasing and pulsing a plain 2x2 box causes.
- **Karis average on the first downsample only.** Weight each 2x2 box by 1/(1 + luma) and renormalise.
  This tames **fireflies**: lone ultra-bright sub-pixels (a specular glint) that would otherwise bloom
  into a flickering blob as they move between pixels. The trick is Brian Karis's from Unreal's temporal
  AA. (LearnOpenGL's variant computes luma on encoded values and scales it by 1/4.)
- **Upsample with a 3x3 tent** (weights 1-2-1 / 2-4-2 / 1-2-1, divided by 16). The radius is given in
  texture-space units, so the blur scales consistently across mips. Each level adds the upsampled
  coarser level to itself, E' = E; D' = D + up(E'); and so on down to A, using additive blending.
- **Composite with `mix(scene, bloom, s)`**, with no threshold (6.2).
- Formats: R11G11B10F is enough (no alpha, about 6 significant bits of mantissa). Use 5 or 6 mips at
  1080p. Clamp to at least a tiny positive value to stop NaN or black-pixel holes from propagating.

Jimenez's same talk introduced **interleaved gradient noise** (8.3) for stable sampling.

### 6.6 Bloom without multipass: what the corpus does

Shadertoy shaders can have multiple buffers but cannot allocate a mip chain of render targets, and
the house bench currently **refuses multi-pass buffers** (cookbook, Outside shaders). The corpus shows
two answers:

1. **An atlas pyramid in one buffer.** sonicether's "Gargantua With HDR Bloom" (lstSRS) packs
   successively halved copies of the image into one buffer with padding between tiles to stop bleed
   (buf_b.glsl around line 150 describes it). It then reconstructs bloom from eight octaves, each read
   with bicubic filtering and weighted individually (image.glsl lines 85-99). This is the
   Jimenez pyramid flattened into a texture atlas.
2. **Analytic glow inside the field.** Most single-pass glow in the corpus is not post-processing at
   all. While raymarching, each step adds an emitter's colour times a falloff of the distance to it:
   1/d², k/(k + d²) (a Lorentzian, the same shape as a scattering PSF's tail), exp(-k d), or a tanh of
   k/d to cap the core. The tone mapper then has to handle the large sums. This is "bloom computed at
   the source", and it is correct by construction: it is the PSF integrated along the view ray.
   Examples: Xor's 3D Fire (3XXSWS) and Singularity (3csSWB), mrange's Neonwave sunrise (7dyyRy, the
   `tanh_approx(k / d)` glows). For the house's single-pass surfaces this is *the* bloom primitive.

Corpus census: 14 shaders mention bloom, and 17 have a lens flare or ghosts (P_Malin's Meta CRT
4dlyWX, mu6k's Lens Flare Example 4sX3Rs, reinder's Planet Shadertoy 4tjGRh).

### 6.7 Lens flares, ghosts and starbursts

John Chapman's "pseudo lens flare" (2013) is the standard screen-space flare:

1. Downsample and threshold the bright parts.
2. **Flip** the image through the centre (texcoord to 1 - texcoord): real ghosts appear mirrored
   through the optical axis.
3. Generate **ghosts** by sampling along the vector toward the centre at several spacings (the ghost
   count and *dispersal*), weighted radially so only near-centre sources throw ghosts.
4. Add a **halo** by sampling at a fixed distance toward the centre (a ring).
5. Add **chromatic distortion** by fetching R, G and B at slightly different offsets along the same
   direction.
6. Blur, upsample, multiply by a **lens-dirt** texture, add a **starburst** texture rotated with the
   camera, and composite *before* tone mapping.

**Diffraction spikes:** a polygonal aperture with N straight blades makes N spikes if N is even and
2N if N is odd, because opposite edges of an odd polygon are not parallel. Six blades give a
six-pointed star; seven give fourteen points. A physically plausible starburst is the Fourier
transform of the aperture shape: compute it offline once, then use it as a texture.

### 6.8 Costs at a glance

| technique | passes | taps per pixel per pass | note |
|---|---|---|---|
| separable Gaussian (linear sampling) | 2 per level | about n/2 | reference quality; cost grows with radius |
| Kawase | 4 to 9 | 4 | fastest for large radii; empirical presets |
| dual filter | 2 log2(scale) | 5 down, 8 up | best bandwidth; very stable |
| COD:AW mip chain | 2 per mip | 13 down, 9 up | best quality and stability; the default for HDR |
| analytic in-field glow | 0 | 1 per emitter per march step | single pass; only for emitters you know about |
| Kawase streaks | 3 per direction | 4 | stylised star glare |

---

## 7. Lens imperfections: chromatic aberration, distortion, vignette

### 7.1 Chromatic aberration (CA)

Glass bends short wavelengths more than long ones (dispersion). That gives two kinds of aberration:

- **Axial (longitudinal) CA:** colours focus at different depths, giving coloured fringes on
  out-of-focus edges. It is mostly a depth-of-field effect.
- **Lateral (transverse) CA:** magnification differs by wavelength, so the red, green and blue images
  are slightly different *sizes*. Fringes are **zero at the optical centre and grow toward the edges**,
  pointing radially. This is the one post-processing imitates.

Implementations:

- **3-tap RGB split:** sample red at uv, green at c + (uv - c)(1 + k) and blue at c + (uv - c)(1 + 2k),
  where c is the centre. knarkowicz's Speed Drive 80 (4ldGz4, image.glsl) does exactly this as its
  final pass. It is cheap, but large k shows three separate ghost images ("3D glasses").
- **Spectral N-tap:** sample N times along the radial displacement, at parameter t_i in [0, 1], and
  weight each sample by a spectral colour w(t_i) that runs red, then green, then blue. The essential
  detail is to **normalise the weights per channel**, so that the sum over i of w_c(t_i) equals 1 for
  each channel c. Then a flat white region stays white and only *edges* fringe. Unity's
  post-processing stack drives the colours from a small spectral lookup texture (its docs recommend
  the tiny 3x1 ones it ships) and takes more samples at higher intensities.
- **Where:** in scene-linear HDR before tone mapping, so a bright highlight's fringe has the right
  strength. Keep it to a couple of pixels at the corners at 1080p; scale k with resolution. Never apply
  it to UI or text.

### 7.2 Lens distortion

The Brown-Conrady radial model: r_d = r (1 + k1 r² + k2 r⁴). k1 < 0 gives barrel distortion (wide
angle, edges bow out); k1 > 0 gives pincushion. Distort the *sampling* coordinate, not the output.
Expect to zoom slightly to hide the black corners barrel distortion exposes. Lateral CA is simply this
with a slightly different k per channel.

### 7.3 Vignette

Three kinds exist physically. **Natural vignetting** follows the cos⁴ law. **Optical vignetting** comes
from the lens barrel clipping oblique bundles. **Mechanical vignetting** comes from hoods and filters.
The natural one is derivable:

An image point at distance r from the centre of a sensor at focal distance f sees the aperture at
angle theta, with tan(theta) = r/f. Illuminance falls as cos⁴(theta). One cos comes from the oblique
angle at the sensor, one from the aperture's foreshortening, and two from the inverse-square of the
longer path. Since cos(theta) = f / sqrt(f² + r²):

```
V(r) = 1 / (1 + r²/f²)²         with f = 1 / tan(fov / 2) when r is measured in half-heights
```

Computed: with a 60-degree vertical field of view, the top edge receives 56% of the centre's light and
a 16:9 corner 18%. At 40 degrees, 78% and 42%. **A physically sized vignette is far stronger than
artists expect**, which is why real cameras correct it and why a gentle, art-directed one reads better.

Shader idioms (pointers):

- **Separable frame vignette** (iq, nimitz, knarkowicz; 45 corpus shaders): with q in 0..1 screen
  coordinates, v = (16 qx qy (1 - qx)(1 - qy))^p with a small p (0.1 to 0.3), often mixed as
  0.5 + 0.5v. The product of two parabolas is 1 at the centre and 0 on every edge, and its contours
  follow the rectangle of the frame rather than a circle. It feels like a picture frame, not a lens.
- **The house's cubic** (design/vfx-chunks/vignette-cubic.glsl): aspect-corrected radial distance,
  normalised by the *actual* corner distance, then 1 - d³ mixed in at 60%. It is flat across the middle
  and falls only near the corners. The chunk's note records the widescreen bug it prevents.
- **Where:** a lens vignette belongs in scene-linear before tone mapping, because the tone mapper's
  shoulder then rolls the darkened corners off naturally. A graphic "frame" vignette can be a
  display-space grade. Do not do both by accident.

---

## 8. Banding, dithering and grain

### 8.1 Why bands appear

An 8-bit channel has 256 levels. A smooth gradient that changes by less than one level (one **LSB**,
least significant bit) across many pixels becomes a staircase, and the eye, which is very good at edges,
sees each step as a band. Bands are worst:

- in **dark gradients**, where the eye compares ratios and a one-code step is a large ratio;
- in **slow, large gradients**: skies, fog, vignettes, glows, screen fades;
- when anything was **rounded at reduced precision in the middle of the chain**: an 8-bit intermediate
  target, an 8-bit LUT, or mediump maths.

Mikkel Gjøl (Playdead; "Banding in Games: A Noisy Rant", revision 5) works through the statistics.
Plain truncation, `floor`, is biased half an LSB dark on average. Rounding is unbiased, but every value
within half an LSB snaps to the same code, so the bands remain.

### 8.2 Dither, properly

Adding noise *before* rounding makes the rounding error random instead of structured. On average over
an area (the eye integrates), the original value comes back. That is dither. Audio engineers have done
it before bit-depth reduction for decades, and Gjøl draws the analogy explicitly. The details matter:

- **Uniform noise of one LSB** removes the bias, but the *amount* of visible noise depends on where the
  signal sits between codes: almost none when the signal is exactly on a code, most halfway between.
  The noise therefore varies with the image. This is **noise modulation**, and it shows as alternating
  clean and noisy stripes inside a gradient.
- **Triangular noise** (TPDF, triangular probability density) is the sum of two independent uniform
  noises. Its error power is the same everywhere regardless of the signal (Lipshitz et al. 1992, cited
  by Gjøl), so the noise looks uniform. Gjøl says in hindsight this was the essential ingredient of
  Playdead's banding-free look. Gaussian noise has no advantage here and adds more visible noise.
- **Range:** GPUs *round* when writing to a UNORM target, so the triangular dither should span
  **[-1, +1) LSB**, which is `hash1 + hash2 - 1` in LSB units.
- **Boundaries:** near 0 and 1 the clamp eats one side of the noise. The average then drifts and
  blacks lift. The fix is to **blend to a half-LSB uniform dither near the extremes** (the
  computergraphics.stackexchange answer Gjøl cites).
- **Dither in the space you quantise in.** If the final write is an encoded 8-bit canvas, add the
  noise *after* the sRGB encode. If the target is an hardware sRGB texture that encodes on write, add
  it in encoded space and then decode. Gjøl's rule, in short: the noise goes into whichever space the
  value will be quantised in.
- **Dither after quantisation does nothing.** Adding grain to an image that has already been rounded
  only adds noise on top of the bands. The "LDR film grain at the end of the frame" mistake.
- **Every quantising write needs it:** each 8-bit intermediate in a post chain, not only the last one.

### 8.3 Where the noise comes from

| source | cost | quality | note |
|---|---|---|---|
| white hash (sin-fract, integer hash) | ALU, tiny | fine for 1-LSB dither | sin-based hashes need highp; integer hashes (PCG-style) are more robust |
| **interleaved gradient noise** (Jimenez 2014) | 2 multiply-adds and 2 fracts | every 3x3 block holds nearly evenly spaced values | ign(x, y) = fract(52.9829189 * fract(0.06711056 x + 0.00583715 y)); animate by offsetting x and y by 5.588238 per frame, frame index modulo 64 (Alan Wolfe) |
| ordered (Bayer) matrix | ALU or tiny LUT | regular cross-hatch pattern | the retro look; poor as invisible dither |
| **blue noise texture** (void-and-cluster) | one texture fetch | the least visible: energy only at high frequencies the eye blurs | Christoph Peters publishes free CC0 textures from 16x16 to 1024x1024 |

Blue noise is the gold standard for still dither. IGN is the best ALU-only choice and is designed to
cooperate with temporal accumulation.

### 8.4 Lottes' energy-preserving grain (GDC 2016 and the GPUOpen follow-up)

Timothy Lottes reframes dither as grain sized to the *largest* step the display encoding can make:

```
rcpStep = 1 / (steps - 1)                                   (steps = 256 for 8 bits)
black   = 0.5 * toLinear(rcpStep)                           (how negative still rounds to zero)
biggest = 0.75 * (toLinear(1 + rcpStep) - 1)                (largest linear step, times an overlap)
out     = colour + grain * min(colour + black, biggest)     (grain in -1..1, colour linear)
```

The `min` limits the grain near black so it never lifts the black level, while letting a constant
amount of grain cover the largest step elsewhere. His slides show the method at **3 bits per
channel** with no visible banding, a good stress test. For HDR transfer functions (PQ), the steps are
so uneven that he shifts to an **asymmetrical grain distribution**, or grain that adapts per channel to
the local step size. His grain textures are pre-shaped for a perfectly balanced distribution, and the
grain is animated with a per-frame offset (a Halton sequence over 1024 frames) so it never
visibly repeats.

### 8.5 Film grain as a look

Real film grain comes from silver-halide crystals. It is most visible in the **midtones** of the
print, weaker in deep shadow and blown highlight. It has a **size** relative to the frame, and in
colour film each layer has its own grain. Martins Upitis' grain post (2013) builds grain from
coherent noise (simplex) rather than per-pixel white noise, so there are visible "particles" with a
size control, and weights it by luminance. The practical rules:

- Add grain in a **perceptual (encoded) space**, or scale it by a luminance curve. A constant amplitude
  in linear light is enormous in the highlights and invisible in the shadows.
- Grain must be **at least about one pixel in size** (blurred or value noise) to read as film rather
  than as sensor noise.
- **Temporal grain crawls.** The house has already ruled on this: per-frame jitter *is* the crawling
  grain Daniel asked to remove (cookbook, Jitter). House default: static dither, with animated grain
  opt-in per piece. At a real 1-LSB amplitude temporal dither is usually invisible, but a visible grain
  look must be a choice, not a side effect.

Corpus census: 44 shaders have some dither or quantisation term (an upper bound; the regex also catches
`/255.0` used for other purposes). Only 4 mention grain.

---

## 9. Colour grading

### 9.1 Where grading lives

- **Scene-referred grading** (on scene-linear light, before the tone mapper): exposure, white
  balance, contrast in log space, and most saturation work. It behaves like adjusting a camera and
  lights, and it survives any display.
- **Display-referred grading** (after the tone mapper, on 0..1 values): lift, gamma and gain, final
  LUTs, and stylised curves. This is like grading a print.

ACES and AgX both assume the look is applied on top of a neutral transform. Lottes adds that
brightness should be set before the curve, not by a gamma after it.

### 9.2 White balance

The eye adapts to the illuminant, and a camera's white balance imitates that. The principled method
is the **von Kries transform**: convert linear RGB to a cone space (LMS), divide by the source white's
LMS, multiply by the target white's, and convert back. Bradford and CAT02 are the standard cone
matrices for this. Multiplying R, G and B directly is a cruder approximation that shifts saturated
colours more. Warm/cool and tint sliders map to a white point along and across the Planckian
(blackbody) locus.

### 9.3 Contrast belongs in log space

Contrast is a ratio. In log2 space around a pivot p (middle grey 0.18):

```
y = p * (x / p)^k          (k > 1 adds contrast, k < 1 removes it; p stays fixed)
```

That is just a power curve anchored at grey. "Contrast" done as a lerp around 0.5 on linear values
pivots in the wrong place (0.5 linear is about 0.74 encoded) and clips.

### 9.4 Saturation, ASC CDL, lift/gamma/gain, split toning

- **Saturation (linear):** y = Y + s (x - Y), with Y the Rec.709 luminance of the *linear* colour.
  With s = 0 you get the correct grey; with s > 1 out-of-gamut values can appear and need a clip.
- **Saturation (perceptual):** scale OKLab's a and b by s. Lightness and hue are unchanged by
  construction.
- **ASC CDL** (the American Society of Cinematographers' Colour Decision List, v1.2): per channel,
  out = clamp(in * slope + offset)^power. Then saturation uses the Rec.709 luma weights,
  out = Y + sat (out - Y). Ten numbers describe a grade, and that is what AgX's "looks" are. Clamp
  negative values before the power.
- **Lift, gamma, gain** (display-referred): lift raises the blacks, gain scales the whites, gamma bends
  the mids. One common form is y = gain (x + lift (1 - x))^(1/gamma). Per-channel versions give the
  classic teal shadows and orange highlights.
- **Split toning / shadows, midtones, highlights:** weight each tint by a smooth function of luminance
  (for example, shadows weighted by 1 - smoothstep(0, 1/3, Y), highlights by smoothstep(0.55, 1, Y),
  midtones by what remains). Per-channel powers are the cheap version (3.3).

### 9.5 The S-curve after encoding

105 corpus shaders contain the smoothstep polynomial x²(3 - 2x). Many of those are noise interpolation
rather than grading, but the "encode, then S-curve the encoded image" move (iq's signature finish) is
common. It adds midtone contrast and saturation in display space, crushes the last few percent at both
ends, and is cheap. Treat it as a look, applied after the tone mapper and before dither.

### 9.6 Lookup tables (LUTs)

A **1D LUT** maps each channel independently (curves, transfer functions). A **3D LUT** maps any colour
to any colour, including cross-channel operations like saturation, hue shifts and film emulation.
Jeremy Selan's GPU Gems 2 chapter (Sony Pictures Imageworks) is still the clearest treatment.

- **Bake a chain:** start from an identity cube, run the entire grading chain on it once, and store the
  result. Applying the grade then costs **one 3D texture fetch per pixel**, no matter how many
  operators were baked in. Selan measured about a 100x speedup over evaluating the chain. Hardware
  analogy: a precomputed ROM in place of combinational logic.
- **Sizes:** 16³ to 33³ for display-referred grades (32³ is the classic size; 33³ puts a sample
  exactly on mid-codes); 48³ to 64³ for display transforms (Tony McMapface is 48³; Lottes moved from
  32³ to 64³ for 10-bit output).
- **Sample at texel centres:** u = x (N - 1)/N + 1/(2N), so that x = 0 hits the centre of the first
  texel and x = 1 the centre of the last. Without this correction, the ends of the range clamp and the
  middle drifts. Selan reports the error as visibly significant on small cubes.
- **WebGL:** WebGL2 has `sampler3D`, so use it. The WebGL1 fallback is an unwrapped strip (Unreal's
  256x16 layout for 16³): the blue coordinate picks two slices, each sampled bilinearly in red and green,
  then blended by the fractional blue. That is manual trilinear filtering.
- **HDR input needs a shaper.** A LUT covers a bounded cube, and scene-linear is unbounded and
  perceptually lopsided. Lottes plotted the error: feeding linear in directly is terrible, a square
  root is better, and the PQ curve (SMPTE ST 2084) is very good but costs about 15 transcendental
  operations. A cheap **log2 shaper**, log2(x c + 1) / log2(c + 1) with c around 2^19 to 2^20, matches
  PQ's error profile. Tony McMapface uses x / (x + 1). AgX's log2 window (5.6) is the same idea.
- **Precision:** store grading LUTs in 16-bit float or 10-bit. 8-bit LUTs band.
- Trilinear interpolation can cut across the neutral axis and tint greys slightly. Film-industry tools
  use **tetrahedral** interpolation (four corners instead of eight) to keep greys neutral. That needs
  a manual implementation in the shader.

---

## 10. The whole pipeline, in order, with reasons

```
scene-linear HDR (radiance, unbounded)              <- lighting, emission, analytic glow, fog
  |  bloom / glare (mip chain, energy-conserving)    <- optics, needs HDR highlights
  |  chromatic aberration, lens distortion           <- optics (distort the sampling coordinates)
  |  natural vignette (cos^4 or art-directed)        <- optics, before the shoulder
  |  exposure (x 2^EV, auto or fixed)                <- puts middle grey where the curve expects it
  |  white balance, log-space contrast, saturation   <- scene-referred grade
  v
display transform (AgX / PBR Neutral / ACES fit / tanh)   -> display-linear 0..1
  |  look (CDL, LUT, S-curve, split tone)            <- display-referred grade
  |  frame vignette (if graphic rather than optical)
  v
encode (exact sRGB OETF)                              -> display-encoded 0..1
  |  dither (TPDF or blue noise, about 1 LSB, boundary-aware)   <- AT the quantisation step
  v
write to the 8-bit canvas (the browser assumes sRGB)
```

Two equivalences. A tone mapper that bakes in the encode (Hejl, AgX before linearisation) moves the
encode line up into itself. And a film-grain look can replace the dither if it is added before
quantisation and has at least 1 LSB of amplitude everywhere.

---

## 11. Common mistakes and how to see them on screen

| what you see | what is wrong | fix |
|---|---|---|
| everything too dark and contrasty, mid-greys near black | linear light written to the canvas unencoded | encode once at the end |
| washed out, grey blacks, no punch | encoded twice (encode after Hejl or AgX output, or decoding a texture that was already linear) | track the currency in function names (`_enc` suffix) |
| a muddy dark band between two bright colours in a gradient or blend | mixing encoded values | mix in linear for light, OKLab for designer gradients |
| blue turns purple as it is lightened or desaturated | HSV, HSL or CIELAB manipulation | OKLab / OKLCH |
| bright bands at yellow, cyan and magenta in a "rainbow" | HSV value is not brightness; triangle-wave Mach bands | OKLCH sweep, or smooth HSV at least |
| a hue animation flashes bright or dark mid-transition | HSV or RGB interpolation between state colours | `mix_oklch` with shortest-arc hue |
| saturated lights turn yellow, cyan or magenta as they brighten | per-channel tone mapping (the notorious six) | AgX, PBR Neutral, max-RGB with crosstalk, or accept as a look |
| saturated lights become flat neon blobs with no core | hue-preserving tone map with no path to white | add crosstalk or desaturation in highlights |
| highlights clip to a flat white plateau, shapes merge | no tone mapper, or `clamp` as the tone mapper | any shoulder |
| grey, low-contrast highlights that never reach white | plain Reinhard (0.99 needs x = 99) | extended Reinhard with a white point, or a curve with real convergence |
| black squares that grow over a few frames, or full-screen flashes | NaN or Inf (pow of a negative, cube root of a negative, divide by zero) spreading through blur or feedback | clamp before pow and cbrt; sanitise before bloom; debug with a NaN-to-magenta view |
| bloom pulses or flickers as small bright things move | fireflies | Karis average on the first downsample, 13-tap downsample |
| bloom pops on and off as an object crosses a brightness level | hard threshold | soft knee, or no threshold with an energy-conserving mix |
| bloom looks blocky or boxy | too few levels or a box upsample | tent upsample, more mips, dual filter |
| everything got brighter when bloom was added | additive composite | `mix(scene, bloom, s)` |
| stepped rings in dark gradients, skies, glows and vignettes | quantisation with no dither, or dither applied after quantisation | TPDF or blue-noise dither at each 8-bit write |
| alternating clean and noisy stripes inside a dithered gradient | uniform dither (noise modulation) | triangular PDF |
| lifted, noisy blacks after dithering | symmetric dither clamped at 0 | boundary-aware dither (blend to half-LSB uniform near 0 and 1) |
| shimmering, crawling fine noise | per-frame dither or grain at visible amplitude | static per-pixel noise (house rule), or IGN with temporal accumulation |
| greys with a colour cast after a LUT | missing half-texel correction, or trilinear across the neutral axis | the u = x(N-1)/N + 1/(2N) mapping; tetrahedral sampling |
| the sides of a widescreen image go black | vignette normalised by a square's corner (0.7071) | normalise by the real corner (the house chunk does) |
| CA shows three offset ghost images | 3-tap split with too large a k | spectral N-tap with normalised weights; keep it to a couple of pixels |
| a desaturated image is the wrong grey (reds and blues too light) | Rec.601 luma weights on linear values | Rec.709 luminance weights, or OKLab L |
| everything bands in blocks on some machines | `mediump` | `highp` |
| bright fringes around semi-transparent canvas edges | non-premultiplied output into a premultiplied canvas | multiply RGB by alpha before output |

---

## 12. What the corpus does, and does not

A read-only regex census over the 335 imported shaders, with comments stripped (scratch script in this
session's scratchpad, not in the repo). The counts are signatures in the code, so they are indicative
upper bounds, not exact:

| signature | shaders | examples |
|---|---|---|
| encode with `pow(..., 1/2.2)` or 0.4545 | 66 | iq Happy Jumping 3lsSzf, NuSan Corridor Travel 3sXyRN |
| encode with `sqrt` (gamma-2 shortcut) | 15 | mrange 3XdXRr, iq 4sfGzS, Shane 4tlSzl |
| exact piecewise sRGB encode | 7 | mrange 7dyyRy / 7d2fDW, iq Pacman Ms3XWN, gelami dtVSzw |
| **no recognisable encode at all** | **247 (74%)** | the norm; many tune in display space (gammas hidden behind a `#define` are missed) |
| 1 - exp(-x) | 41 | Xor 3csSWB, Kali 4dsGD7, Shane 4s3SRN |
| Narkowicz ACES fit (2.51 / 2.43) | 18 | edankwan 3sySRK, mrange 43jXWt, ThomasSchander 4dSBDt |
| tanh soft limit | 15 | Xor 3XXSWS, mrange 33cGDj, diatribes 7cjGRR |
| Reinhard x/(1+x) | 10 | iq 3lsSzf and Msl3Rr, Maurogik Wtc3W2 |
| Hejl / Burgess-Dawson | 6 | Duke MdKXzc / MsVXWW, reinder lscBW4 |
| Hable / Uncharted 2 | 4 | mrange (four shaders) |
| Hill ACES fit | 1 | afl_ext MdXyzX |
| **OKLab / OKLCH** | **0** | |
| **AgX** | **0** | |
| cosine palette | 15 | iq ll2GD3 (the reference), 3lsSzf, Msl3Rr |
| HSV | 17 | mrange (several), airtight MdsXWM |
| separable 16xy(1-x)(1-y) vignette | 45 | iq, nimitz 3l23Rh, knarkowicz 4ldGz4 |
| bloom (any) | 14 | sonicether lstSRS (atlas pyramid), ThomasSchander 4dSBDt |
| lens flare or ghosts | 17 | P_Malin 4dlyWX, mu6k 4sX3Rs |

Reading: the corpus is a **library of looks**, not of colour management. Its masters (iq, mrange,
nimitz, Shane, Xor, knarkowicz) are consistent *within* each shader, tuned by eye on the final
display, and that is exactly why their pieces cannot be snapped together without re-tuning. The two
modern tools of this topic, OKLab and AgX, appear nowhere. That is the gap the house library can fill,
and it gives us a way to *improve on* the corpus rather than only imitate it. Licences: 286 of 335 are
CC BY-NC-SA (Shadertoy's default); 21 CC0 and 19 MIT. Techniques transfer; code does not.

**Dissection tags.** For the vfx tooling's "break down the primitives and group them by category",
these signatures make a first colour/post tagger. Each tag maps to a primitive in section 14:
`enc.srgb_exact`, `enc.pow22`, `enc.sqrt`, `enc.none`; `tm.reinhard`, `tm.exp`, `tm.tanh`,
`tm.aces_fit`, `tm.aces_hill`, `tm.hejl`, `tm.hable`, `tm.none`; `pal.cosine`, `pal.hsv`;
`grade.scurve`, `grade.channel_pow`, `grade.multiply`, `grade.saturation`; `post.vignette_frame`,
`post.vignette_radial`, `post.ca`, `post.flare`, `post.bloom_atlas`, `post.glow_analytic`;
`dither.hash`, `dither.ign`, `dither.blue`. A shader's tag set is its colour fingerprint. Two shaders
with different fingerprints will not look right side by side until they are moved to the house chain.

---

## 13. House findings (applied to our own code)

These are observations for the morning, not changes. Nothing was edited.

1. **The house speaks two colour currencies.** `scripts/aurora-shader.js` (around line 307) and
   `arsenal/web/shaders/first-light.frag` (around lines 99-120) end with `tanh`, a vignette and
   `outColor = col`, with **no encode**. `scripts/agent-avatar.js` (lines 295 and 427) and the sketches
   `design/vfx-sketches/aurora-bus.frag:182` and `daniil-snowfield.frag:366` **do** encode with
   `pow(1/2.2)`. The bed is not wrong (its colours were tuned in display space, and tanh is acting as a
   display-space soft clip). But **one shared palette, glow or bloom module would look different on
   each surface.** That defeats "tweak one module and have everything update" at the root. The
   remedy is a declared house contract: modules compute scene-linear, and every surface ends with the
   same `display_out()` (exposure, display transform, look, encode, dither). The bed's existing look
   can be kept closely by re-tuning its constants once against a before-and-after still.
2. **The "filmic finish" group** (`design/vfx-groups.json`: superlinear-highlight, tanh-tonemap,
   vignette-cubic, triangular-dither) has no encode step. Today that makes its dither *correctly
   placed*: it sits immediately before the canvas's 8-bit write, in the space that gets quantised. The
   trap comes the day an encode is added. If the dither stays in front of the encode, its amplitude is
   stretched by the slope of the sRGB curve: roughly 13 times too strong in the deepest darks and about
   half strength near white (8.2). The dither must move to after the encode in the same change.
3. **"Perceptual" HSV hue rotation is not perceptual.** First Light's header says the
   RGB-to-HSV-to-RGB rotation keeps "luminance and saturation" intact. HSV rotation keeps *V* and HSV-S.
   Luminance can change by a factor of 13 (blue to yellow), OKLab lightness from 0.45 to 0.97. The
   cookbook's "ease through HSV the short way round" rule correctly avoids the grey RGB midpoint, but
   it keeps the lightness pumping. **OKLCH shortest-arc interpolation** (`mix_oklch`) is the drop-in
   upgrade that fixes both: no grey midpoint and constant lightness.
4. **Rec.601 weights on linear values.** `design/vfx-chunks/desaturate-unsensed.glsl` and the
   aurora bed's "error" state (`aurora-shader.js` around line 299) use (0.299, 0.587, 0.114). Those are
   the weights for the old Rec.601 video primaries. Our colours have sRGB (Rec.709) primaries, so
   (0.2126, 0.7152, 0.0722) is correct whether the values are linear (luminance) or encoded (luma). As
   written, a pure-blue identity desaturates to a grey 58% heavier than it should be (0.114 against
   0.0722), and a green one to a grey 18% darker (0.587 against 0.7152).
5. **The triangular-dither chunk animates with time** (`u_time` in both hashes). At 1.6/255 that is
   below most people's visibility threshold, but it contradicts the house's own no-crawl floor
   (cookbook, Jitter). Decide deliberately: make it static, or document the exception.
6. **A stale comment.** `first-light.frag` says GLSL ES 3.00 has no vec3 overload of `tanh`. It does:
   the hyperbolic functions take genType, as the cookbook already states. The per-component code is
   harmless; the comment will mislead the next author.

---

## 14. The primitive API: what the house library should provide

Format: GLSL ES 3.00 signatures written fresh for the house (`arsenal/web/glsl/*.glsl`, Apache-2.0 house
code), each with a one-line contract. Grouping follows the module categories the library uses (`cat`).
Two naming laws make the currency impossible to forget:

- functions that take or return **display-encoded** values carry `_enc` (or say `srgb_` / `_disp`);
- everything else is **scene-linear** by contract.

### 14.1 Transfer functions and luminance (module `color-transfer`, cat `colour`)

```glsl
float srgb_encode(float lin);            // exact IEC 61966-2-1 OETF; lin <= 0 -> 0; the ONE encoder every surface uses
vec3  srgb_encode(vec3 lin);             // per-channel overload of the above
float srgb_decode(float enc);            // exact inverse; for textures and picked colours before lighting
vec3  srgb_decode(vec3 enc);             // per-channel overload
vec3  gamma_encode(vec3 lin, float g);   // pure power 1/g, negative-safe; only where a pure-2.2 look is wanted on purpose
vec3  gamma_decode(vec3 enc, float g);   // pure power g, negative-safe
float luminance(vec3 lin);               // Rec.709/sRGB linear weights (0.2126, 0.7152, 0.0722); never 601 on linear
vec3  log2_shaper(vec3 lin, float c);    // log2(x*c + 1)/log2(c + 1): unbounded HDR to 0..1 for LUT lookup (Lottes)
vec3  log2_shaper_inv(vec3 s, float c);  // exact inverse of log2_shaper
vec3  pq_encode(vec3 nits_over_10k);     // SMPTE ST 2084 inverse EOTF; HDR output and high-precision LUT shaping
vec3  safe_pow(vec3 x, vec3 p);          // pow on max(x, 0); NaN-proof building block for every curve below
vec3  cbrt_signed(vec3 x);               // sign-preserving cube root; keeps OKLab finite for out-of-gamut input
```

### 14.2 Perceptual colour (module `color-oklab`, cat `colour`)

```glsl
vec3  lin_to_oklab(vec3 lin);            // linear sRGB to OKLab (L, a, b); Ottosson 2020 matrices; out-of-gamut safe
vec3  oklab_to_lin(vec3 lab);            // OKLab back to linear sRGB; may leave 0..1, so clip when it matters
vec3  oklab_to_oklch(vec3 lab);          // (L, C, h) with h in TURNS 0..1, matching the palette convention
vec3  oklch_to_oklab(vec3 lch);          // inverse of the above
vec3  mix_oklab(vec3 linA, vec3 linB, float t);   // perceptual blend of two linear colours; even steps, no muddy middle
vec3  mix_oklch(vec3 linA, vec3 linB, float t);   // shortest-arc hue, lerped L and C; constant-lightness state transitions
float hue_delta(float h0, float h1);     // signed shortest difference between two hues in turns, in [-0.5, 0.5)
vec3  oklch_clip(vec3 lch);              // reduce C at fixed L and h until linear sRGB is in gamut (bisection); returns linear
bool  in_gamut(vec3 lin, float eps);     // all channels within [-eps, 1 + eps]
vec3  hue_rotate_oklch(vec3 lin, float turns);    // rotate hue at constant lightness, then clip; the honest "change colour, keep brightness"
```

### 14.3 Legacy cylindrical models (module `color-hsv`, cat `colour`)

```glsl
vec3  hsv_to_rgb(vec3 hsv);              // standard branch-free HSV; values are display-ish knobs, NOT perceptual
vec3  hsv_to_rgb_smooth(vec3 hsv);       // cubic-smoothed hue ramps (iq's idea): no Mach bands at the sextant seams
vec3  rgb_to_hsv(vec3 rgb);              // inverse; hue of a pure grey is defined as 0
```

### 14.4 Palettes (module `palette`, cat `colour`)

```glsl
vec3  pal_cos(float t, vec3 a, vec3 b, vec3 c, vec3 d);      // iq cosine palette; returns DISPLAY values as tuned on screen
vec3  pal_cos_lin(float t, vec3 a, vec3 b, vec3 c, vec3 d);  // same palette decoded to linear, for lit and blended pipelines
vec3  pal_oklch(float t, float L, float C, float h0, float turns);   // constant-lightness hue sweep, gamut-clipped; returns linear
vec3  pal_ramp3(float t, vec3 linA, vec3 linB, vec3 linC);   // three-stop gradient interpolated in OKLab; analogous house palettes
vec3  pal_blackbody(float kelvin);       // Planckian chromaticity (about 1000 to 40000 K), max channel = 1; brightness is separate
```

### 14.5 Exposure (module `exposure`, cat `tone`)

```glsl
vec3  expose(vec3 lin, float ev);                  // lin * 2^ev; the only brightness knob before the display transform
float ev100_from_camera(float fNumber, float shutterSec, float iso);   // log2(N^2/t * 100/S)
float ev100_from_avg_luminance(float lavg);        // log2(lavg * 100 / 12.5); reflected-light meter, K = 12.5
float exposure_from_ev100(float ev100);            // 1 / (1.2 * 2^ev100); saturation-based speed (q = 0.65)
float adapt_luminance(float prev, float target, float dt, float tau);  // frame-rate-independent exponential approach
```

### 14.6 Display transforms (module `tonemap`, cat `tone`)

All take exposed scene-linear and return **display-linear 0..1** unless the name says `_enc`.

```glsl
vec3  tm_reinhard(vec3 x);                        // x/(1+x) per channel; never quite reaches white
vec3  tm_reinhard_white(vec3 x, float white);     // extended Reinhard; f(white) = 1, clamped above
vec3  tm_reinhard_lum(vec3 x, float white);       // extended Reinhard on Rec.709 luminance; exact hue and saturation, no path to white
vec3  tm_tanh(vec3 x);                            // slope 1, no toe, about 1.4 stops headroom; for glow fields tuned near 1
vec3  tm_exp(vec3 x);                             // 1 - exp(-x); slope 1, softer than tanh (0.99 at x = 4.6)
vec3  tm_aces_fit(vec3 x);                        // Narkowicz 2016 rational fit (CC0); input pre-scaled by 0.6 inside; hue skews
vec3  tm_aces_hill(vec3 x);                       // Hill RRT+ODT fit with in/out matrices (MIT); the "ACESFilmic" look
vec3  tm_hable(vec3 x, float white);              // Uncharted 2 filmic curve normalised by its value at white
vec3  tm_uchimura(vec3 x, float P, float a, float m, float l, float c, float b);  // GT toe/linear/shoulder; defaults 1, 1, .22, .4, 1.33, 0
vec2  tm_lottes_solve(float contrast, float shoulder, float midIn, float midOut, float hdrMax);  // closed-form (b, c); compute once, not per pixel
vec3  tm_lottes(vec3 x, float contrast, float shoulder, vec2 bc);   // z = x^contrast; z/(z^shoulder * b + c), per channel
vec3  tm_maxrgb(vec3 x, float contrast, float shoulder, vec2 bc, float crosstalk, float sat, float crossSat);  // Lottes max-RGB with indirect path to white
vec3  tm_agx(vec3 x);                             // AgX base: inset, log2 window [-12.47, +4.03], sigmoid, outset, decoded to display-linear
vec3  tm_agx_look(vec3 x, vec3 slope, vec3 power, float sat);       // AgX with a CDL look applied in its encoded domain (Punchy/Golden-style)
vec3  tm_pbr_neutral(vec3 x);                     // Khronos PBR Neutral: identity below 0.76, peak compression, gentle desaturation
vec3  tm_hejl_enc(vec3 x);                        // Hejl/Burgess-Dawson; returns ENCODED values, never encode again
```

### 14.7 Grading (module `grade`, cat `grade`)

```glsl
vec3  grade_white_balance(vec3 lin, vec3 srcWhiteLin, vec3 dstWhiteLin);  // von Kries scaling in a cone (LMS) space
vec3  grade_contrast_log(vec3 lin, float contrast, float pivot);           // pivot * (x/pivot)^contrast; pivot defaults to 0.18
vec3  grade_saturation(vec3 lin, float s);        // luminance-preserving lerp with Rec.709 weights; s = 0 gives the true grey
vec3  grade_saturation_oklab(vec3 lin, float s);  // scale OKLab chroma; lightness and hue untouched
vec3  grade_cdl(vec3 x, vec3 slope, vec3 offset, vec3 power, float sat);  // ASC CDL v1.2: SOP per channel, then Rec.709 saturation
vec3  grade_lift_gamma_gain(vec3 disp, vec3 lift, vec3 gamma, vec3 gain); // display-referred three-way corrector
vec3  grade_split_tone(vec3 lin, vec3 shadowTint, vec3 highlightTint, float balance);  // luminance-weighted tints; tints carry no brightness
vec3  grade_scurve_disp(vec3 disp, float amount); // smoothstep S-curve on display values, mixed by amount (the iq finish)
vec3  grade_lut3d(sampler3D lut, vec3 coord01, float size);   // half-texel-corrected 3D LUT fetch: coord*(N-1)/N + 0.5/N
vec3  grade_lut_strip(sampler2D lut, vec3 coord01, float size);  // N*N by N unwrapped LUT with manual blue-slice blend (WebGL1 path)
```

### 14.8 Lens optics (module `post-optics`, cat `optics`)

```glsl
float vignette_cos4(vec2 pHalfHeights, float fovY);   // natural cos^4 falloff: 1/(1 + r^2/f^2)^2, f = 1/tan(fovY/2)
float vignette_frame(vec2 uv01, float power);         // separable 16xy(1-x)(1-y) frame vignette raised to power; graphic
float vignette_corner(vec2 uv01, float aspect, float amount);  // aspect-correct radial, normalised by the REAL corner (house cubic)
vec2  lens_distort(vec2 pCentered, float k1, float k2);        // Brown radial r(1 + k1 r^2 + k2 r^4); distort sampling coords
vec3  ca_rgb3(sampler2D src, vec2 uv, vec2 center, float k);   // 3-tap lateral CA, zero at centre, grows radially
vec3  ca_spectral(sampler2D src, vec2 uv, vec2 center, float k, int taps);  // N-tap spectral CA, per-channel weights sum to 1
vec3  spectral_weight(float t);                       // smooth red-to-green-to-blue ramp over t in 0..1, each channel with equal integral
```

### 14.9 Bloom, blur and glare (module `post-bloom`, cat `bloom`)

Multi-pass (needs render targets; these become usable once the bench accepts buffers):

```glsl
vec3  bloom_down13(sampler2D src, vec2 uv, vec2 texel);        // Jimenez 13-tap downsample (five weighted 2x2 boxes)
vec3  bloom_down13_karis(sampler2D src, vec2 uv, vec2 texel);  // first-level variant, boxes weighted by 1/(1 + luminance)
vec3  bloom_up_tent(sampler2D src, vec2 uv, vec2 texel, float radius);   // 3x3 tent upsample, radius in texture units
vec3  blur_dual_down(sampler2D src, vec2 uv, vec2 halfTexel);  // Bjorge downsample: centre 1/2 + four diagonals 1/8
vec3  blur_dual_up(sampler2D src, vec2 uv, vec2 halfTexel);    // Bjorge upsample: 4 diagonals x2 + 4 axis taps x1, /12
vec3  blur_kawase(sampler2D src, vec2 uv, vec2 texel, float iteration);  // 4 diagonal taps at (iteration + 0.5) texels
vec3  streak_kawase(sampler2D src, vec2 uv, vec2 texel, vec2 dir, float pass, float atten);  // 4 taps, weight atten^(b s), b = 4^(pass-1)
vec3  bloom_prefilter_knee(vec3 lin, float threshold, float knee);    // soft quadratic threshold; art tool, not physics
float karis_weight(vec3 lin);                                 // 1/(1 + luminance); firefly suppression weight
vec3  bloom_composite(vec3 scene, vec3 bloom, float strength);  // mix(scene, bloom, strength): energy-conserving, no light created
vec3  sanitize_hdr(vec3 c);                                   // NaN/Inf/negative to 0, clamp to a large finite max; run before any blur
```

Single-pass (works on today's bench):

```glsl
float glow_lorentz(float d, float k);     // k/(k + d^2): analytic PSF tail around a distance-field emitter
float glow_exp(float d, float k);         // exp(-k d): tighter analytic halo
float glow_soft_core(float d, float k);   // tanh(k / max(d, eps)): bright core capped at 1, long tail
```

### 14.10 Dither and grain (module `post-dither`, cat `frame`)

```glsl
float ign(vec2 pixel);                    // interleaved gradient noise (Jimenez 2014) in 0..1; static per pixel
float ign_frame(vec2 pixel, float frame); // IGN offset 5.588238 px per frame (frame mod 64) for temporal accumulation
float noise_tpdf(vec2 pixel);             // triangular-PDF noise in [-1, 1) from two decorrelated uniforms
vec3  dither_enc(vec3 enc, vec2 pixel, float levels);   // TPDF dither in the ENCODED space at 1 LSB, blending to half-LSB uniform near 0 and 1
vec3  dither_enc_blue(sampler2D blue, vec3 enc, vec2 pixel, float levels);  // same, from a tiled blue-noise texture (Peters, CC0)
vec3  grain_energy(vec3 lin, float g, float steps);     // Lottes energy-preserving grain: lin + g*min(lin + black, biggest)
vec3  grain_film(vec3 disp, vec2 pixel, float size, float amount);  // midtone-weighted coherent grain in display space; STATIC unless opted in
```

### 14.11 Measurement and debug views (module `color-debug`, cat `debug`)

These are the dissection tools: views that make colour bugs visible on the bench.

```glsl
vec3  debug_nan(vec3 c);                  // magenta where any channel is NaN, cyan where Inf; passthrough otherwise
vec3  debug_false_stops(vec3 lin);        // false-colour map of stops relative to 0.18 grey (like a camera's false-colour mode)
vec3  debug_clip_zebra(vec3 disp, vec2 pixel, float limit);  // diagonal stripes where display values exceed limit
vec3  debug_gamut(vec3 lin);              // highlights pixels whose linear RGB left 0..1 before the display transform
vec3  testcard_hue_exposure(vec2 uv01);   // rows of hues by columns of +/- stops around grey; THE tone-mapper test card (shows the notorious six)
vec3  testcard_ramp(vec2 uv01);           // linear-light, encoded and OKLab ramps stacked; the gradient and banding test
```

### 14.12 The single seam (module `display`, cat `tone`)

```glsl
vec3  display_out(vec3 sceneLin, vec2 pixel);  // THE house tail: exposure, display transform, look, sRGB encode, dither, all from shared uniforms
```

This one function is what makes "tweak one module and have everything update" true for colour. The
bed, the avatar, First Light, the sketches and the three.js scenes would all end with it, and its
choices (which transform, which look, how much dither) come from one set of house uniforms or presets.
Changing the house look then means editing one module, and every surface follows.

### 14.13 Mapping the existing bench chunks onto the library

| chunk today | becomes | change in behaviour |
|---|---|---|
| `tanh-tonemap` | `tm_tanh` inside `display_out` | none, once inputs are linear |
| `filmic-curve` | `grade_lift_gamma_gain` / `grade_cdl` | the same lift/roll, now parameterised |
| `superlinear-highlight` | stays a scene-linear modifier before the transform | none |
| `vignette-cubic` | `vignette_corner` | none |
| `triangular-dither` | `dither_enc` | moves after the encode, static by default, boundary-aware |
| `desaturate-unsensed` | `grade_saturation` (Rec.709) or `grade_saturation_oklab` | correct grey for blue and red identities |
| `channel-rotate` | `hue_rotate_oklch` | brightness held constant |
| `identity-wash` | `grade_split_tone`, or a multiply in linear | unchanged look, explicit currency |

---

## 15. A study path, from zero to expert

These are exercises for the bench, under the house GPU-lock rules. They were not run tonight.

1. **The two-currency ramp.** Draw a horizontal ramp of linear 0..1, written raw on the top half and
   encoded on the bottom. Find where each looks "half grey". (Answer: about 0.21 raw, 0.5 encoded.)
2. **Three blends.** Red to green as raw, linear-then-encoded, and OKLab. Name the muddy one.
3. **The tone-mapper test card.** Rows of saturated hues, with exposure rising from -4 to +8 stops
   left to right. Run every transform in 5.9. Watch for the six: which ones turn orange to yellow, and
   which keep a path to white?
4. **Headroom by eye.** Make a glow field whose peaks reach 2, 8 and 50. Compare tanh, AgX and Reinhard,
   and re-expose each fairly.
5. **Three-bit banding.** Quantise to 3 bits per channel (Lottes' stress test). Compare no dither,
   uniform, TPDF, TPDF in the wrong space, and blue noise. At 3 bits every mistake in section 8 is
   obvious; at 8 bits it is merely there.
6. **Bloom from scratch.** Build the mip chain (13-tap down, Karis on level 0, tent up, `mix`
   composite). Then swap in the dual filter and Kawase and compare stability on a moving spark.
7. **Analytic glow.** Rebuild a single-pass glow with `glow_lorentz` and compare it with the
   multi-pass bloom on the same emitter.
8. **Spectral CA.** Implement the N-tap version with normalised weights. Check that a flat white
   region stays white, and that the fringes appear only at edges and grow toward the corners.
9. **Bake a LUT.** Bake a CDL look plus `tm_agx` into a 33³ LUT behind a log2 shaper. Compare against
   the ALU path with the difference view. Then remove the half-texel correction and watch greys drift.
10. **OKLCH state transitions.** Replace one avatar state's HSV ease with `mix_oklch` and look at the
    midpoint frames side by side.

---

## 16. Sources

Primary sources first. Every entry was read on 2026-10-13 unless marked otherwise.

**Colour spaces and encoding**

- https://bottosson.github.io/posts/oklab/ -- Björn Ottosson's OKLab: design goals, the fitting
  procedure against CAM16 and Ebner-Fairchild data, the exact matrices, OKLCH, and comparisons with
  CIELAB, CAM16 and IPT (code public domain or MIT).
- https://bottosson.github.io/posts/colorwrong/ -- Ottosson on how software mixes colour wrongly:
  sRGB blending, hue drift toward white, and why HSV and HSL inherit RGB's flaws.
- https://bottosson.github.io/posts/colorpicker/ -- Ottosson's analysis of HSV and HSL failures and the
  construction of OKHSV and OKHSL (gamut cusp, triangle-to-square remap; MIT code).
- https://bottosson.github.io/posts/gamutclipping/ -- hue-preserving gamut clipping in OKLab: chroma
  reduction, point projection, adaptive projection, and finding the cusp (MIT code).
- https://blog.johnnovak.net/2016/09/21/what-every-coder-should-know-about-gamma/ -- John Novak's
  plain explanation of gamma encoding and every way gamma-incorrect maths shows on screen.
- https://en.wikipedia.org/wiki/SRGB -- the exact sRGB transfer functions, primaries, D65 white,
  XYZ matrix, and the 80 cd/m² reference display.
- https://community.acescentral.com/t/srgb-piece-wise-eotf-vs-pure-gamma/4024 -- the long industry
  debate on whether sRGB displays decode with the piecewise curve or a pure 2.2 power (read via search
  summary).
- https://www.colour-science.org/posts/srgb-eotf-pure-gamma-22-or-piece-wise-function/ -- the
  colour-science.org take on the same question (read via search summary).

**Palettes and artist practice**

- https://iquilezles.org/articles/palettes/ -- Inigo Quilez's cosine palette: formula, parameter roles,
  integer frequencies for loops, and the GPU cost of cosine.
- https://iquilezles.org/articles/outdoorslighting/ -- Quilez on lighting in linear space,
  albedo around 0.2, sun, sky and bounce light colours, and gamma at the end.
- https://www.shadertoy.com/view/MsS3Wc -- Quilez's "Smooth HSV" idea, cubic-smoothed hue ramps
  (corpus-style licence: technique only; not fetched tonight).

**Tone mapping**

- https://www-old.cs.utah.edu/docs/techreports/2002/pdf/UUCS-02-001.pdf -- Reinhard, Stark, Shirley and
  Ferwerda 2002: log-average key, the x/(1+x) operator, the white point, and dodging and burning (the
  link returned 404 tonight; formulas from the published paper).
- https://64.github.io/tonemapping/ -- Matt Taylor's survey: Reinhard variants, luminance versus
  per-channel, Reinhard-Jodie, Uncharted 2, both ACES fits, camera response curves.
- http://filmicworlds.com/blog/filmic-tonemapping-operators/ -- John Hable's originals: Reinhard,
  Hejl / Burgess-Dawson (gamma baked in), Uncharted 2 constants.
- http://filmicworlds.com/blog/filmic-tonemapping-with-piecewise-power-curves/ -- Hable's piecewise
  power curve: segment form, junction fitting, artist controls, the per-channel argument (code CC0).
- https://knarkowicz.wordpress.com/2016/01/06/aces-filmic-tone-mapping-curve/ -- Krzysztof Narkowicz's
  ACES rational fit, its pre-exposure, error and saturation caveat (CC0 or MIT).
- https://github.com/TheRealMJP/BakingLab/blob/master/BakingLab/ACES.hlsl -- Stephen Hill's ACES fit
  with input and output matrices (MIT, in Matt Pettineo's BakingLab).
- https://raw.githubusercontent.com/mrdoob/three.js/dev/src/renderers/shaders/ShaderChunk/tonemapping_pars_fragment.glsl.js
  -- three.js tone-mapping chunk (MIT): Reinhard, Cineon (Hejl), ACES Filmic (Hill), AgX (via Filament,
  with constants) and Neutral, side by side.
- https://github.com/KhronosGroup/ToneMapping/tree/main/PBR_Neutral -- the Khronos PBR Neutral
  specification: equations, constants, design goal of exact base-colour reproduction (check the
  repository's licence file before vendoring any file).
- https://github.com/sobotka/AgX -- Troy Sobotka's AgX repository (the origin of the transform).
- https://docs.darktable.org/usermanual/development/en/module-reference/processing-modules/agx/ --
  darktable's AgX module: what primaries attenuation and rotation, log range, pivot, toe and shoulder
  powers and purity restore do.
- https://github.com/godotengine/godot/pull/106940 -- Godot's AgX work (Allen Pestaluky): middle-grey
  anchoring, white and contrast controls, why inset and outset deliberately mismatch.
- https://iolite-engine.com/blog_posts/minimal_agx_implementation -- Benjamin Wrensch's minimal AgX
  (page content was thin tonight; cited as the widely used real-time reference).
- https://alextardif.com/Tonemapping.html -- Alex Tardif's "Reframing Tonemapping in Games": display
  transform versus look, per-channel skews, the notorious six.
- https://gpuopen.com/wp-content/uploads/2016/03/GdcVdrLottes.pdf -- Timothy Lottes (AMD, GDC 2016):
  variable dynamic range, building a tone mapper from contrast and shoulder with a closed-form anchor,
  max-RGB plus crosstalk, LUT shaper error plots, energy-preserving dither.
- https://www.slideshare.net/nikuque/hdr-theory-and-practicce-jp -- Hajime Uchimura's CEDEC 2017 "HDR
  theory and practice" (the GT tonemapper; formula verified via search and a public gist).
- http://cdn2.gran-turismo.com/data/www/pdi_publications/PracticalHDRandWCGinGTS_20181222.pdf --
  "Practical HDR and Wide Color Techniques in Gran Turismo SPORT" (TLS error tonight; not read).
- https://blog.selfshadow.com/publications/s2025-shading-course/ -- SIGGRAPH 2025 Physically Based
  Shading course: Yasutomi, Suzuki and Uchimura's GT7 tone mapping talk, with MIT-licensed reference
  code (pdi/supplemental/gt7_tone_mapping.cpp; summary read).
- https://github.com/h3r2tic/tony-mc-mapface -- Tomasz Stachowiak's LUT-based display transform (48³,
  x/(x+1) shaper, MIT or Apache-2.0).

**Exposure**

- https://seblagarde.wordpress.com/2015/07/14/siggraph-2014-moving-frostbite-to-physically-based-rendering/
  -- Lagarde and de Rousiers' Frostbite PBR notes: EV100, the 1.2 factor, physical camera exposure
  (formulas confirmed via search).
- https://bruop.github.io/exposure/ -- Bruno Opsenica: histogram-based auto-exposure in compute,
  temporal adaptation, the 9.6 constant.

**Bloom, blur and glare**

- http://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare -- Jorge
  Jimenez (SIGGRAPH 2014): mip-chain bloom, Karis average, tent upsample, interleaved gradient noise.
- https://learnopengl.com/Guest-Articles/2022/Phys.-Based-Bloom -- an implementable walkthrough of the
  COD:AW bloom: 13-tap weights, Karis average, tent upsample, mix composite, formats.
- https://www.froyok.fr/blog/2024-01-breakdown-syndicate/resources/presentations/siggraph2015-mmg-marius-slides.pdf
  -- Marius Bjørge (ARM, SIGGRAPH 2015): Kawase versus dual filtering, with quality (PSNR), stability and
  Mali-T760 timings.
- https://www.chrisoat.com/papers/Oat-ScenePostprocessing.pdf -- Chris Oat (ATI, GDC Europe 2003):
  Kawase's bloom and light-streak filters with the a^(b s) weighting, plus a classic tone-and-vignette
  pass.
- https://www.intel.com/content/www/us/en/developer/articles/technical/an-investigation-of-fast-real-time-gpu-based-image-blur-algorithms.html
  -- Intel's comparison of Gaussian (linear sampling), Kawase and moving-average blurs, with timings.
- http://john-chapman-graphics.blogspot.com/2013/02/pseudo-lens-flare.html -- John Chapman's
  screen-space lens flare: ghosts, halo, chromatic distortion, dirt, starburst.
- https://www.semanticscholar.org/paper/Physically-based-glare-effects-for-digital-images-Spencer-Shirley/3a9134bf0a67915e6e38be19b69031b50232753a
  -- Spencer, Shirley, Zimmerman and Greenberg (SIGGRAPH 1995): the eye's PSF, flare lines, lenticular
  halo, glare as a brightness cue (abstract level).

**Lens effects**

- https://en.wikipedia.org/wiki/Chromatic_aberration -- axial versus lateral chromatic aberration, and
  why lateral CA grows with distance from the optical axis.
- https://docs.unity3d.com/Packages/com.unity.postprocessing@3.4/manual/Chromatic-Aberration.html --
  Unity's spectral-LUT chromatic aberration: intensity versus sample count, fast mode.
- http://devlog-martinsh.blogspot.com/2013/05/image-imperfections-and-film-grain-post.html -- Martins
  Upitis on coherent-noise film grain, grain size, luminance weighting, and companion lens
  imperfections.

**Banding, dither and grain**

- http://loopit.dk/banding_in_games.pdf -- Mikkel Gjøl (Playdead): quantisation bias, uniform versus
  triangular dither, noise modulation, the [-1, 1) range, boundary handling, dithering in the
  quantisation space, blending.
- https://gpuopen.com/learn/vdr-follow-up-fine-art-of-film-grain/ -- Timothy Lottes on grain as
  quantisation-aware dither: amplitude from the step size, black protection, temporal offsets.
- https://blog.demofox.org/2022/01/01/interleaved-gradient-noise-a-different-kind-of-low-discrepancy-sequence/
  -- Alan Wolfe on IGN: the 3x3 property, the constants, temporal animation, versus blue noise.
- https://momentsingraphics.de/BlueNoise.html -- Christoph Peters' free CC0 blue-noise textures
  (void-and-cluster), from 16x16 to 1024x1024.
- https://bartwronski.com/2016/10/30/dithering-part-one-simple-quantization/ -- Bart Wronski's
  dithering series (cited by Gjøl; further reading, not read tonight).

**Grading and LUTs**

- https://developer.nvidia.com/gpugems/gpugems2/part-iii-high-quality-rendering/chapter-24-using-lookup-tables-accelerate-color
  -- Jeremy Selan (GPU Gems 2, ch. 24): 1D versus 3D LUTs, sizes, the half-texel formula, shaper LUTs for
  HDR, baking a grading chain.
- https://en.wikipedia.org/wiki/ASC_CDL -- the ASC Colour Decision List: slope, offset and power per
  channel plus saturation (v1.2).

**Corpus pointers** (other people's code under `state/arsenal/shaders/corpus`, cited by id and file,
never copied): iq 3lsSzf, ll2GD3, Msl3Rr; nimitz 3l23Rh; mrange 7dyyRy, 33cGDj, 43jXWt; Xor 3csSWB,
3XXSWS; sonicether lstSRS; knarkowicz 4ldGz4; afl_ext MdXyzX; Duke MdKXzc; P_Malin 4dlyWX; mu6k
4sX3Rs; reinder 4tjGRh.
