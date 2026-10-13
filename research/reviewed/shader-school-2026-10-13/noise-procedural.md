# Noise and procedural texture: a field manual for the house shader library

Status: current
Class: research
Arc: shader-school-2026-10-13 (one of eight researcher lanes; this lane is noise and procedural texture)
Written: 2026-10-13, Vandor (claude seat), for Daniel's "learn everything we can from these shaders" night

Everything below is written in my own words. Formulas are restated, not copied. No code from the corpus or from any
source with an unknown or non-commercial licence appears in this file; corpus shaders are cited only as `id/file:line`
pointers. The few direct quotes are under 15 words and attributed.

---

## 0. What you get from this report, in one screen

**The outcome.** A complete map of procedural noise, from the dice (hash functions) up through lattice noises
(value, gradient, simplex), cellular noise (Worley/Voronoi), fractal sums (fBm, ridged, billow, multifractals),
domain warping, divergence-free flow (curl and bitangent noise), dithering noise (blue noise, interleaved gradient
noise, R2), tileable/looping noise, analytic derivatives and anti-aliasing; then a 65-signature "primitive API" for
the house library, grouped into 11 modules; then the mistakes and what they look like on screen.

**Five findings that matter to the house tonight, before any of the theory:**

1. **Our hashes are the weakest link, and it is measurable.** Every house noise chunk sits on the `fract(sin(dot(...)) *
   43758.5)` hash (`design/vfx-chunks/hash31.glsl`, `triangular-dither.glsl`), and so do 123 of the 335 corpus shaders
   (37%). The peer-reviewed benchmark (Jarzynski and Olano, JCGT 2020) puts the trig hash at the bad end of the
   quality axis, and an integer hash (`pcg3d`) on the best speed/quality frontier. I ran a CPU-only probe (numpy,
   no GPU) of the house dither formula: with a perfectly accurate `sin`, its output is already white at time zero
   (spectral flatness 0.554, ideal for white noise is 0.561), but at one day of page uptime it falls to 0.244 and at
   four days to 0.131, with only 1,761 distinct values in a 512x512 tile. `pcg3d` stays at 0.559 with 258,687
   distinct values at the same uptime. Real GPU `sin` at those argument sizes is worse than exact, not better.
2. **`u_time` itself rots over multi-day uptime.** A 32-bit float has 24 significant bits. At 4 days of page uptime
   the smallest step `u_time` can take is 1/32 s, almost two 60 Hz frames; at a week it is 1/16 s (3.75 frames). Any
   animation driven by raw `u_time` begins to stutter, and any hash fed `u_time` loses its randomness (finding 1).
   The fix is cheap: wrap time host-side (or pass a phase), and make looping noise periodic in time so the wrap is
   seamless (section 10). The memory file on the 82-92 hour commit cycle tells us this host does reach these uptimes.
3. **The corpus licence classifier misses restrictive headers.** 33 corpus shaders (32 by iq, 1 by Kazimierz Pogoda,
   `mds3DX`) carry a header in which the author declares sole copyright and forbids hosting, sharing or use (iq's
   version also forbids AI training). In `meta.json`, 30 of them are labelled "CC-BY-NC-SA-3.0 (Shadertoy default)"
   with `explicit: false`, 2 are labelled an explicit "CC-BY-NC-SA" (`MdlGW7`, `tt2XzG`), and only 1, `4ttSWf`
   (Rainforest), is labelled `all-rights-reserved`. Examples of the mislabelled: `4s23zz` (iq, Warping - procedural 1),
   `4dlGDN`, `MdX3Rr` (Elevated), `XslGRr` (Clouds), `lsl3RH`. Related: `design/vfx-chunks/value-noise-3d.glsl` credits Rainforest as its origin. Its body is
   textbook value noise, so the fix is a fresh rewrite from the textbook definition plus a corrected credit line, not
   panic; but the credit as written points at an all-rights-reserved source.
4. **There is genuinely adoptable code, and it is better than what we have.** Stefan Gustavson and Ian McEwan's
   `psrdnoise` (tiling simplex noise with rotating gradients and exact derivatives) is MIT-licensed; so are
   `webgl-noise`, Dave Hoskins' "Hash without Sine", and three iq corpus shaders (`4sfGzS` value noise LUT, `ldl3W8`
   Voronoi distances, `Xd23Dh` Voronoise). Christoph Peters' blue-noise textures are CC0. Vendoring an MIT file with
   its notice intact is legal; whether the house prefers fresh rewrites anyway is Daniel's call (section 15.4).
5. **The house dither chunk contradicts the house's own floor.** `triangular-dither.glsl` feeds `u_time` into its hash,
   so it changes every frame; shader-craft floor 8 says per-frame jitter is crawling grain and was removed at Daniel's
   request. Its amplitude (1.6 code values peak) is also 1.6 times the textbook triangular dither width (1 code value).
   A static blue-noise or R2 mask at one code value, applied in output (sRGB) space, does the job without the crawl.

---

## 1. The mental model: what "noise" means in graphics

**Plain idea.** Procedural noise is the random-number generator of computer graphics, with one twist: it is not
random per pixel, it is random per *place*, and it changes smoothly as the place changes. Give it the same coordinate
and it returns the same value, forever, on every machine (if it is built well). Move the coordinate a little, the value
moves a little. Move it a lot, the value is unrelated. That combination (deterministic, smooth, unpredictable at
distance) is what makes clouds, marble, terrain, fire and water possible without storing a single image.

**Hardware analogy.** Think of a noise function as a texture unit fetching from an infinite random texture that is
never stored. The "texels" are pseudo-random numbers manufactured on demand by a hash of the integer address; the
"bilinear filter" is a smooth interpolation polynomial. Everything clever in this field is a variation on (a) how
the texels are manufactured, (b) where they sit (square grid, triangle grid, scattered points), and (c) how they are
filtered and stacked.

**The precise definition** (Ares Lagae and co-authors' 2010 survey, which I paraphrase): a noise is a *stationary*
random process (its statistics are the same everywhere), usually *isotropic* (the same in every direction), whose
character is fully described by its **power spectrum**: how much energy each spatial frequency carries. Phase is
random and carries no useful information. Ken Perlin and Eric Hoffert described a single noise as white noise
band-limited to roughly one octave. That is the key to the whole subject: a single noise call is one "band" on a
graphic equaliser; fractal sums (section 6) are the whole equaliser.

**The power spectrum, for a hardware person.** It is the frequency-response plot of the pattern. White noise: flat (all
frequencies equal, like hiss). A single Perlin octave: a bump centred near one frequency. Fractal Brownian motion: a
straight downward slope on a log-log plot (like pink or brown noise in audio). Blue noise: low at the bottom, flat at the
top (the opposite of brown). If you remember only one thing, remember that **every noise design decision is a decision
about this curve**, and every aliasing bug is energy above the pixel grid's Nyquist frequency (half the sampling rate).

**The families** (Lagae et al.'s classification, extended):

| family | how it is built | examples | character |
|---|---|---|---|
| lattice noise | random values or gradients at grid points, interpolated | value noise, Perlin gradient noise, simplex noise | smooth, band-pass, cheap |
| point-process noise | random points scattered in space, function of distances to them | Worley/cellular/Voronoi, sparse convolution, Gabor noise | cells, cracks, spots; Gabor is filterable |
| explicit noise | precomputed and stored | noise textures, wavelet noise, blue-noise masks | fastest lookup, finite, must tile |
| structured composition | built from the above | fBm, ridged, warping, curl | the looks artists actually ship |

---

## 2. Hashing: the dice under everything

### 2.1 Why a hash and not a random-number generator

A classic pseudo-random number generator (PRNG) is a sequence: number 1000 is computed from number 999. A GPU runs
millions of pixels in parallel, and pixel 1000 cannot wait for pixel 999. So graphics uses a **hash**: a function from
an address (pixel coordinate, lattice point, particle id, frame number) straight to a random-looking number. Mark
Jarzynski and Marc Olano (JCGT 2020) list the requirements: fast, parallel, random-looking *when fed adjacent inputs*
(which most data-structure hashes are not), and able to take N-dimensional input and give M-dimensional output.

**Analogy.** A good hash is like the index-scrambling function in a CPU cache or a DRAM controller's bank hash:
neighbouring addresses must land in unrelated slots, or you get pathological patterns. A hash that maps neighbours to
neighbours is how you get stripes.

### 2.2 The families of GPU hash

1. **Trig hash**, `fract(sin(dot(p, k)) * big)`. A sine wave sampled far faster than it oscillates, then multiplied up
   so the fractional part looks random. Its randomness is *aliasing*: it depends on exactly how the GPU computes `sin`
   for large arguments, which is not standardised. iq notes in his MIT-licensed `4sfGzS/image.glsl` header that this
   kind of hash used to come out differently per platform, browser, driver and GPU. JCGT 2020 measured "trig" at the
   low-quality end. Dave Hoskins wrote his family precisely to get a hash that is, in his words, "the same on all
   systems and doesn't rely on trig functions" (`4djSRW`, MIT).
2. **Float arithmetic hashes without sine** (Hoskins 2014). Multiply by small irrational-ish constants, take `fract`,
   mix the components with a dot product against a shifted copy, take `fract` again. Fast, portable, decent for noise;
   JCGT measured `hashwithoutsine` as better than trig but not on the high-quality frontier. Hoskins' naming scheme is
   worth stealing: `hashOI` where O is the output dimension and I the input dimension (`hash13` = one float out, three
   in). 61 corpus shaders (18%) use this naming.
3. **Integer hashes** (need GLSL ES 3.00 / WebGL 2, which the house targets). They work on 32-bit unsigned integers
   with multiplies, xors and shifts, so the result is bit-exact on every GPU. The family includes LCG (linear
   congruential: multiply-add), xorshift, the Wang hash, iq's integer hashes, xxHash32, and PCG (Melissa O'Neill's
   permuted congruential generator, 2014: an LCG step followed by a data-dependent shift-xor-multiply "output
   permutation" that hides the LCG's weak low bits).
4. **Permutation tables** (Perlin 1985): a shuffled array of 0..255, applied nested per axis,
   `P[P[P[x]+y]+z]`. Excellent quality for noise, but needs a table (a texture or a constant array).
5. **Permutation polynomials mod 289** (Ian McEwan, David Sheets, Mark Richardson, Stefan Gustavson, "Efficient
   computational noise in GLSL", 2012). Replace the table with the polynomial `(34x^2 + x) mod 289`, which permutes
   0..288 and stays exact in single-precision floats (289 = 17^2 keeps every intermediate under 2^24). In 2022
   Gustavson and McEwan found the old polynomial caused diagonal streaks and switched to `(34x^2 + 10x) mod 289`.
   Useful if you are stuck on WebGL 1 (no integers); otherwise integer hashes win.
6. **Texture lookup tables.** A 256x256 RGBA noise texture, fetched with `texelFetch` or at exact texel centres. iq's
   trick (credited by him to Dave Hoskins) stores in the green channel a copy of the red channel shifted by (37, 17)
   texels, so one 2D fetch at `xy + (37,17)*z` returns two adjacent z-slices of a 3D value noise at once (`4sfGzS`,
   MIT, lines 98 and 107; also the three methods in `XslGRr/image.glsl:34-36`). Fastest when the shader is
   arithmetic-bound, slowest when it is memory-bound; precision pitfalls if filtering or mipmapping is left on. The
   single most-bound texture in the corpus (69 bindings) is Shadertoy's small RGBA noise LUT.

### 2.3 What the benchmark found (Jarzynski and Olano, JCGT 2020)

Method, in brief: quality = number of failed tests out of the 160 in TestU01 BigCrush (L'Ecuyer and Simard), the
standard battery for random-number quality; speed = GPU time per call in Unreal Engine 4 on a GTX 1080, each hash
chained 10,000 times so the compiler cannot delete it. Multi-dimensional inputs were fed in Morton (Z-curve) order so
repetition along any axis is caught. Over 100 variants were tested. Findings, restated:

- **Linear combination destroys quality.** Turning a 1D hash into an N-D hash by hashing `a*x + b*y + c*z` (the
  common shortcut) produced repeating patterns for every hash they tried; XOR-combining was not much better.
- **Nesting preserves quality** (`hash(x + hash(y + hash(z)))`, Perlin's original approach), at N times the cost.
- **Native multi-dimensional hashes are best when you need several outputs.** They introduced `pcg3d` and `pcg4d`.
- Their recommended spanning set, fastest to best: 1-in-1-out: iqint1, pcg, xxhash32, pcg3d, pcg4d. 2-in-1-out:
  iqint3, xxhash32 (multibyte), pcg3d, pcg4d. 3-in-1-out: pcg3d16, xxhash32 (multibyte), pcg3d, pcg4d. 4-in-1-out:
  xxhash32 (multibyte), pcg4d. N-in-N-out: pcg3d, pcg4d.
- Nathan Reed (2021) updated his long-standing advice accordingly: PCG replaces the Wang hash as his default
  1-in-1-out GPU hash, being slightly faster and much better.

**How pcg3d works, in words** (so the house can write its own from the description): treat the three 32-bit lanes as
the state of a tiny cipher. Step one, advance every lane with the classic Numerical Recipes LCG (multiply by 1664525,
add 1013904223). Step two, cross-mix: each lane in turn adds the product of the other two (x gets y times z, then y gets
z times the new x, then z gets the new x times the new y). Step three, fold the high bits into the low bits with a
right-shift-by-16 xor on every lane (multiplication only pushes information upward, so this brings it back down).
Step four, cross-mix once more. The authors describe it as an unbalanced generalised Feistel network: the same family
as real block ciphers, cut down to a few multiply-adds. `pcg4d` is the four-lane version with the obvious cyclic mixing.
**Analogy:** it is a toy version of the memory-encryption scrambler in a modern CPU, run once per lookup.

### 2.4 Using an integer hash from float code

- **Lattice addresses:** `ivec = ivec(floor(p))`, then reinterpret as `uvec` (two's-complement wrap makes negative
  cells hash fine). Add a seed into one lane (or xor it in) to get independent streams.
- **Continuous inputs** (non-lattice floats): `floatBitsToUint(p)` gives the exact bit pattern; hash that.
- **Back to float in [0,1):** keep the top 24 bits and scale by 2^-24, which is exact in a 32-bit float. (Scaling all
  32 bits by 2^-32 rounds the top values up to exactly 1.0, a subtle bug when you index arrays with it.)
- **Several random numbers from one address:** use the extra lanes of `pcg3d`/`pcg4d`, or re-hash the output. Do not
  derive them by adding constants to the input of a weak hash (JCGT calls this the "translated" method).

### 2.5 The house probe (CPU only, numpy, no GPU)

I emulated the house's `triangular-dither.glsl` hash in float32 (every operation rounded to float32, but `sin`
computed *exactly* on the rounded argument, a best case for the trig hash) over a 512x512 pixel tile, and compared it
with `pcg3d(pixel x, pixel y, frame)`. "Spectral flatness" is the geometric mean of the 2D power spectrum divided by its
arithmetic mean: for ideal white noise it is about 0.561 (e to the minus Euler's constant), lower means the energy has
collected into some frequencies, which the eye sees as pattern.

| case | distinct values (of 262,144) | spectral flatness |
|---|---|---|
| fract(sin), t = 0 | 8,339 | 0.554 |
| fract(sin), t = 1 hour | 7,827 | 0.547 |
| fract(sin), t = 1 day | 3,397 | 0.244 |
| fract(sin), t = 4 days | 1,761 | 0.131 |
| fract(sin), t = 1 week | 1,261 | 0.131 |
| fract(sin), static per pixel, far corner of a 4K frame | 8,381 | 0.522 |
| pcg3d, frame 0 | 258,740 | 0.562 |
| pcg3d, frame 20,736,000 (about 4 days at 60 Hz) | 258,687 | 0.559 |

Two more facts fell out of the probe. First, the trig hash's output is coarse even at time zero: when the sine is above
about 0.75 in magnitude, the product exceeds 32,768, and a float32 there can only express steps of 1/256, so half the
outputs live on an 8-bit grid. Second, the dot product inside the hash grows with time: at 4 days it is about
5.4 x 10^7, where a float32 can only count in steps of 4. Neighbouring pixels then differ by only a few of those steps,
and the "randomness" collapses into structure. The static per-pixel jitter that the shader-craft cookbook uses (no time
term) is fine at 4K under `highp`, which agrees with the cookbook; the damage comes from feeding time into the hash.
The probe script is my own code (numpy only, no GPU), saved in this session's scratchpad at
`C:\Users\L5\AppData\Local\Temp\claude\E--\9d62784c-bd34-488c-a370-94b7d333fbb9\scratchpad\hashprobe.py`; it is
the seed of the `noise.hash` CPU twin (section 15.1) and should move into the library's test folder when that exists.

---

## 3. Lattice noise I: value noise

**Idea.** Put a random number at every integer grid point. To evaluate between them, blend the surrounding corners
with a smooth curve. In 1D, with `i = floor(x)`, `f = x - i`, corner values `a = h(i)`, `b = h(i+1)`:

  n(x) = a + (b - a) s(f)

where s is the **fade curve** (also called the interpolant or smoothstep). In 2D with corners a (0,0), b (1,0), c (0,1),
d (1,1) and `u = s(fx)`, `v = s(fy)`, expanding the bilinear blend gives a polynomial that is easy to differentiate:

  n = a + (b - a) u + (c - a) v + (a - b - c + d) u v

and in 3D the same pattern with eight corners and terms in u, v, w, uv, vw, wu, uvw (iq writes the eight coefficients
k0..k7 explicitly in his "value noise derivatives" article).

**The fade curve is not a detail.** Two standard choices:

- cubic Hermite, s(t) = 3t^2 - 2t^3, slope s'(t) = 6t(1 - t). First derivative is zero at the ends (so no visible
  creases in the value), but the second derivative, 6 - 12t, is +6 at one end and -6 at the other: a jump.
- quintic, s(t) = 6t^5 - 15t^4 + 10t^3, slope s'(t) = 30 t^2 (1 - t)^2. First *and* second derivatives vanish at both
  ends. Ken Perlin introduced it in "Improving Noise" (2002) because, on a noise-displaced surface, the shading normal
  is itself a derivative, so a second-derivative jump in height shows up as a first-derivative jump in lighting: you
  see the grid in the highlights.

**Derivatives** (iq, "value noise derivatives"): differentiate the polynomial. Name the corner terms `k1 = b - a`,
`k2 = c - a` and `k3 = a - b - c + d` (so the value is `a + k1·u + k2·v + k3·u·v`); then in 2D
`dn/dx = s'(fx)·(k1 + k3·v)` and `dn/dy = s'(fy)·(k2 + k3·u)`. One evaluation
gives value and gradient; central differences would need four extra evaluations in 2D (six in 3D).

**Character and cost.** Value noise is the cheapest lattice noise (2^N hashes and a few multiply-adds) and the easiest
to make tile and to differentiate. Its weaknesses are visible: it is blobby, grid-aligned shapes (plus signs, diamonds)
show through, and it carries a lot of low-frequency energy, so an fBm of value noise looks softer and "cloudier" than an
fBm of gradient noise. It is the right choice for volumetric fog and clouds, where it is evaluated hundreds of times per
pixel and nobody inspects individual octaves; the house fog uses it for exactly this reason (`value-noise-3d` note).

**A naming trap.** A once-popular web tutorial (Hugo Elias) called fractal value noise "Perlin noise", and the label
spread. Gustavson's 2005 tutorial opens by warning about misinformed explanations. When a shader says "perlin", read
the code: values at the corners means value noise; dot products with corner gradients means Perlin noise.

---

## 4. Lattice noise II: gradient (Perlin) noise, original and improved

**Idea** (Ken Perlin, "An Image Synthesizer", SIGGRAPH 1985; Academy Award 1997). Instead of a random *value* at each
grid point, store a random *slope* (gradient vector g). Each corner contributes a linear ramp that is zero at the
corner and tilts along its gradient; blend the ramps with the fade curve. In 1D: `n(x) = lerp( g_i f, g_{i+1} (f - 1),
s(f) )`. In 2D, each corner contributes `r = g . (x - corner)`, and the four ramps are blended exactly as in value noise.

**Why it looks better than value noise.** Because every corner pins the value to zero, the noise crosses zero on every
lattice point, which kills the low-frequency drift that makes value noise blobby; the result is closer to band-pass (one
octave of energy), with sharper, more varied features. The price: the grid is still faintly visible (all zero
crossings on lattice points; Lagae et al. found its value histogram is distorted for exactly this reason, and from the
small gradient set).

**Improved noise (Perlin 2002) fixed two defects**, which I restate:

1. The cubic fade curve's second-derivative jump (section 3), visible as faceted highlights on displaced surfaces; fixed
   with the quintic curve.
2. A randomly oriented gradient table clumps: near-axis-aligned gradients happen to align with neighbours and make
   splotches of anomalously high values. Fix: drop the random table entirely and use the 12 vectors from the centre of a
   cube to the midpoints of its edges, (plus or minus 1, plus or minus 1, 0) and permutations, chosen by the
   permutation-table hash mod 12. They avoid both the axes and the long diagonals, and a dot product with them needs no
   multiplications. To avoid a modulo-12, pad to 16 with four repeats that form a regular tetrahedron, which adds no bias.
   Perlin measured the improved version about 10% faster on a Pentium 3.

**Range.** With unit-length gradients in N dimensions the theoretical bound is plus or minus sqrt(N)/2 (0.707 in 2D,
0.866 in 3D), reached only at a cell centre with every gradient aimed at it, so real output is much narrower. With
Perlin's 12 edge vectors, 3D output stays within about plus or minus 1. Never assume [-1, 1] or [0, 1]: measure your
implementation's histogram once and normalise (section 15, analysis tools).

**Derivatives** (iq, "gradient noise derivatives"). Two parts, by the product rule: the blend of the corner
*gradients* (the derivative of the ramps), plus the fade-curve slopes times the differences of the corner *ramp values*
(the derivative of the weights). In 2D, with ramp values r00, r10, r01, r11 and gradients g00..g11:

  grad n = [ g00 + u (g10 - g00) + v (g01 - g00) + u v (g00 - g10 - g01 + g11) ]
         + ( s'(fx) [ r10 - r00 + v (r00 - r10 - r01 + r11) ] , s'(fy) [ r01 - r00 + u (r00 - r10 - r01 + r11) ] )

**Cost.** 2^N hashes (4 in 2D, 8 in 3D, 16 in 4D) plus 2^N dot products and 2^N - 1 lerps. That exponential growth is
why 4D gradient noise is expensive, and is the reason simplex noise exists.

**Later refinements worth knowing by name.** Andrew Kensler, Aaron Knoll and Peter Shirley, "Better Gradient Noise"
(2008): a better hash, a separate gradient table, and a wider reconstruction kernel for better band-limiting. Robert
Cook and Tony DeRose, "Wavelet Noise" (Pixar, 2005): nearly perfectly band-limited noise built in a preprocess, for
film-grade anti-aliasing. Both matter mainly for filtering (section 12).

---

## 5. Lattice noise III: simplex noise

**Idea** (Perlin, SIGGRAPH 2001 course notes "Noise hardware"; explained clearly by Stefan Gustavson, "Simplex noise
demystified", 2005). A square grid cell has 4 corners in 2D, 8 in 3D, 16 in 4D: 2^N. The simplest shape that tiles
N-space, the **simplex** (triangle in 2D, tetrahedron in 3D), has only N + 1 corners. Evaluate a contribution from each
of those corners and *add* them instead of interpolating along each axis in turn, and the cost grows as N^2 instead of
2^N. **Analogy:** going from a cache line that touches 2^N banks to one that touches N + 1.

**Step 1: which simplex am I in?** Skew space along its main diagonal so the triangle grid becomes a square grid of
right-isoceles triangles. With F_N = (sqrt(N + 1) - 1)/N, skew by adding `(x + y + ...) * F_N` to every coordinate;
`floor` gives the cell. Unskew with G_N = (1 - 1/sqrt(N + 1))/N by subtracting `(i + j + ...) * G_N`. In 2D,
F = (sqrt 3 - 1)/2, about 0.366, and G = (3 - sqrt 3)/6, about 0.211; in 3D the factors become the tidy 1/3 and 1/6;
in 4D, (sqrt 5 - 1)/4 and (5 - sqrt 5)/20. Within the skewed cell, **sort the fractional coordinates by size**: the
simplex's corners are reached by stepping one unit along the largest axis, then the next largest, and so on (in 2D, one
comparison, x > y, picks the lower or upper triangle; in 3D, 6 orderings; in 4D, 24).

**Step 2: the kernel.** Each corner contributes its gradient ramp times a radial falloff that reaches zero before the
neighbouring simplex: `c = max(0, r^2 - |d|^2)^k * (g . d)`, with d the vector from the corner to the point. Sum the
N + 1 contributions and multiply by an empirical constant to fill about [-1, 1] (Gustavson's 2D: r^2 = 0.5, k = 4,
scale 70).

**A real bug in the reference.** Perlin's 3D reference used r^2 = 0.6 and k = 4. Gustavson and McEwan (JCGT 2022),
following Brian Sharpe (2012), point out that 0.6 is too large: each corner's influence leaks across simplex faces, so
the noise and its gradient are discontinuous there. Their fix is r^2 = 0.5 with k = 3 (similar look, no seams). If you
copy an old simplex implementation, check this constant first.

**Derivative** (Gustavson and McEwan, Table 2, restated generally). With w = r^2 - |d|^2 per corner, the contribution
`w^k (g . d)` has gradient `w^k g - 2k w^(k-1) (g . d) d`. Summing that over corners gives the exact gradient at a small
extra cost, because w, w^(k-1) and (g . d) are already computed. Second derivatives add about 18-20%.

**Character.** No square-grid artifacts, a well-defined continuous gradient everywhere, cheap in 3D and 4D, a slightly
different "feel" from Perlin noise (Gustavson notes it is not a drop-in replacement: feature size and value statistics
differ, and a 3D slice of 4D simplex noise is not the same as 3D simplex noise).

**Its own artifacts.** The simplex grid has planes where the character changes; in Perlin's orientation they are
off-axis, but in Gustavson and McEwan's axis-aligned tiling grid they are the planes of constant x, y or z, with
period one half. Their warning, quoted: the common z-slice demo "looks its absolute worst in this exact scenario"
(Gustavson and McEwan 2022). Rotate or skew the input before slicing.

**Patent.** US patent 6,867,776 covered simplex noise in 3D and above; it expired in January 2022. OpenSimplex (Kurt
Spencer) exists because of it; it is no longer necessary for legal reasons.

**Speed reference** (Gustavson and McEwan 2022, Table 3). `psrdnoise` 2D runs at 0.37 ns per value on an AMD Vega 10
laptop GPU and 0.017 ns on an RTX 3080; 3D is roughly three times the cost of 2D. They report a single 2D noise value
is comparable in speed to a single 2D texture fetch on the GPUs they tested: the "texture is always faster" intuition is
out of date.

---

## 6. Cellular noise: Worley, Voronoi and their descendants

### 6.1 The basis functions

**Idea** (Steven Worley, "A Cellular Texture Basis Function", SIGGRAPH 1996). Scatter feature points through space.
At any location x, define F1(x) as the distance to the nearest point, F2(x) to the second nearest, and Fn to the n-th.
The places where F1 switches from one point to another are exactly the cell walls of the **Voronoi diagram** of the
points. Properties, restated from the paper: every Fn is continuous; F1 <= F2 <= F3 ...; the gradient of Fn is simply
the unit vector from the n-th nearest point toward x (cheap bump mapping for free).

**The looks:**
- F1: round bumps around each point; polka dots, scales, "stone" when thresholded.
- F2 - F1: zero on the cell walls; veins, cracks, cell outlines, "flagstone" grout.
- Linear mixes C1 F1 + C2 F2 + C3 F3 + C4 F4: Worley generated dozens and found low n (up to 4) distinct and useful.
- Cell id: the hashed identity of the nearest point, constant over a cell; colour each cell differently.
- Fractal F1 (sum over octaves): "crumpled paper or tinfoil"; Worley reports a bumped, reflective plane with it reads
  convincingly as seawater.
- Other distance metrics: Manhattan (sum of absolute differences) makes rectangular "spaceship hull" channels;
  Chebyshev (largest component) makes square cells; Minkowski p-norms interpolate between them.

### 6.2 The GPU implementation

Worley's original used a Poisson-distributed count per cube (mean density about 3-4, clamped to 1..9) and an early-out
over neighbouring cubes. Shaders simplify: **exactly one point per grid cell**, placed at the cell corner plus a hashed
offset scaled by a **jitter** in [0, 1]. Then search the neighbourhood: 3x3 cells in 2D, 3x3x3 in 3D, keeping the
smallest (and second smallest) distance. Compare squared distances and take one square root at the end.

**Correctness of the search** (my own analysis, worth knowing): with full jitter (1.0), the nearest point is almost
always within the 3x3 block, but not provably: the own cell's point can be up to sqrt 2 (1.41) away while a point two
cells away can be just over 1.0 away. The rare misses show as small cut corners in the cell pattern. F2 misses more often.
Remedies: reduce jitter to about 0.8-0.9 (cheapest, slightly more regular), widen to 5x5 for F2 or edges (25 cells
instead of 9), or accept rare errors where they will not be seen.

**Precision.** Compute everything relative to the current cell (integer part removed first), not in absolute
coordinates: iq calls this out in his edges article, and it matters far from the origin.

### 6.3 Exact distance to cell borders (iq, "Voronoi edges")

F2 - F1 is zero on the walls, but it is *not* a distance: its slope depends on how far apart the two points are, so a
threshold on it gives lines whose width wobbles from cell to cell. The true distance from x to the wall between its
nearest point a and a neighbour b is the distance to their perpendicular bisector plane. With x at the origin:

  distance = ( (a + b)/2 ) . (b - a)/|b - a|

iq's algorithm takes two passes: first find the nearest point a (3x3), then measure that bisector distance to every
neighbour b around a's cell (5x5) and keep the minimum. The two-pass structure matters because the second-nearest point
jumps discontinuously inside a cell, so a single pass measures the wrong wall near triple junctions. MIT reference:
`ldl3W8`. This is the primitive for clean, constant-width cracks, grout and glowing cell outlines.

### 6.4 Smooth Voronoi (iq, "Smooth Voronoi")

`min` makes F1 a crease function (its derivative jumps on cell walls), which is hard to filter and to shade. Replace the
hard minimum with a smooth minimum over all neighbours:

- exponential form: F = -(1/k) ln( sum_i exp(-k d_i) ). k around 32 looks like ordinary Voronoi with rounded creases;
  k around 4 is very soft. It is order-independent (associative).
- inverse-power form: F = ( sum_i d_i^(-p) )^(-1/p), with p around 16.
- polynomial smooth-min: cheaper, but no longer order-independent (harmless in a fixed loop order).

Strong decay means 3x3 still suffices; a very sharp k may need 5x5.

### 6.5 Voronoise (iq): one function, four patterns

Two knobs span four classic patterns. u (0..1) is the jitter: grid-aligned points or random points. v (0..1) is the
blend: hard nearest-point selection or smooth weighted averaging. Each neighbour gets a random value h_i and a weight
`w_i = (1 - smoothstep(0, sqrt 2, d_i))^(1 + 63 (1 - v)^4)`; the result is `sum w_i h_i / sum w_i`. Corners: (u=0,v=0)
cell noise (flat squares), (u=0,v=1) value noise, (u=1,v=0) Voronoi cell colours, (u=1,v=1) a jittered noise iq calls
voronoise. MIT reference: `Xd23Dh`. Pedagogically priceless: it shows value noise and Voronoi are the same machine.

### 6.6 Related point-process noises

**Sparse convolution / Gabor noise** (Lagae, Lefebvre, Drettakis, Dutre 2009): splat many random kernels; with a
Gabor kernel (a Gaussian times a cosine) you control orientation and frequency band directly, and because each kernel is
a Gaussian in frequency space it can be filtered analytically. Costly (many impulses per cell), but it is the noise to
reach for when you need anisotropic, filterable texture (brushed metal, wood grain, woven straw).

---

## 7. Fractal sums: fBm, turbulence, ridged, billow, multifractals

### 7.1 Fractional Brownian motion (fBm)

**Idea.** One noise call is one band. Real surfaces have detail at every scale, smaller detail being weaker. So add
copies of the noise at doubling frequency and shrinking amplitude:

  F(x) = sum over i = 0..n-1 of  G^i * N( L^i x )

- **octaves** n: how many bands.
- **lacunarity** L (Latin for "gap"): frequency ratio between bands; about 2. F. Kenton Musgrave notes it is almost
  always left near 2.0, which, as in music, is one octave per band.
- **gain** G (also "persistence"): amplitude ratio between bands; about 0.5.
- **Hurst exponent** H: the fractal parameter behind the gain, G = L^(-H) (iq writes G = 2^(-H) for L = 2). Musgrave
  calls H "1 minus the fractal increment"; the surface's fractal dimension is about 3 - H.

**What H does** (iq, "fBm"). The self-similarity rule is: zoom in horizontally by a factor U, and the vertical detail
shrinks by U^(-H). For a 1D profile the power spectrum falls as f^-(2H + 1):

| H | gain at L = 2 | spectral slope | sounds like | looks like |
|---|---|---|---|---|
| 0 | 1.0 | -3 dB per octave (pink) | rain | rough, noisy |
| 0.5 | 0.707 | -6 dB per octave (brown) | indoor rain | stock-market charts; "anisotropic" zoom |
| 1 | 0.5 | -9 dB per octave (iq calls it "yellow") | engine behind a door | mountains and clouds |

iq measured real mountain silhouettes with an FFT and found about -9 dB per octave, H = 1: a mountain twice as tall is
twice as wide. That is why G = 0.5 is the near-universal default. **Analogy:** fBm is a graphic equaliser where every
fader is set by one slope knob (H); lacunarity is how far apart the faders' centre frequencies are; octaves is how many
faders are in the rack.

**Normalisation.** The amplitudes sum to (1 - G^n)/(1 - G); divide by that to keep the range stable as you change
octaves (otherwise adding octaves brightens the image).

**How many octaves.** Musgrave's rule: about log2(screen resolution) - 2 for terrain seen from unit distance (6 to 10),
because the Nyquist limit is half the pixel rate and a noise band's highest content is about half its lattice rate.
Beyond that you pay for detail you cannot see and get sparkle (section 12). Musgrave also allows a fractional last octave
(blend the final band in by the remainder) so the octave count can change smoothly with distance.

**Octave hygiene (the craft).**
- **Detune the lacunarity** (2.01, 2.02, 2.03 in successive octaves, as iq does): with exactly 2.0, lattice points of
  every octave coincide at the origin and along grid lines, and peaks stack up.
- **Rotate each octave** by an angle that is not a multiple of 90 degrees. The ubiquitous matrix with rows (0.8, 0.6),
  (-0.6, 0.8) is a rotation by about 36.87 degrees (a 3-4-5 triangle); 47 corpus shaders (14%) use it, often pre-scaled
  to (1.6, 1.2) to fold the lacunarity in. Without rotation, each octave's grid artifacts align and reinforce.
- **Offset each octave** (or hash with a per-octave seed), because gradient noise is zero at the origin for *every*
  octave: without offsets fBm(0) is exactly 0 and there is a visible pinch.
- **Cost** is octaves times the basis cost. Early-out when the remaining amplitude is below one code value of output.

**Analytic derivative of fBm with rotation** (the chain rule, as iq's terrain shaders use it): if octave i evaluates
N(A_i x) with A_i = (L M)^i (scale L, rotation M), its gradient with respect to x is A_i^T times the noise gradient. For a
rotation, the transpose is the inverse rotation, so keep a running matrix (the product of inverse rotations times L^i)
alongside the running sample point and accumulate `G^i * A_i^T * gradN`. Pointer: `4ttSWf/buffer_a.glsl:196-198`
(Rainforest: a rotation and its inverse kept side by side; all-rights-reserved, read only).

### 7.2 Turbulence and billow

- **Turbulence** (Perlin 1985): sum of absolute values, sum G^i |N(L^i x)|. The absolute value folds each band at its
  zero crossings, making sharp V-shaped creases: fire, smoke wisps. Perlin's original marble was sin(x + turbulence).
- **Billow**: the same fold remapped to [-1, 1] (2|N| - 1 per octave): puffy, cauliflower clouds and rounded rocks.

### 7.3 Ridged noise and the ridged multifractal

- **Ridged noise**: invert the fold, (1 - |N|), usually squared to sharpen: crests become sharp mountain ridges.
- **Ridged multifractal** (Musgrave, in Ebert et al., "Texturing and Modeling: A Procedural Approach"): each octave's
  signal is (offset - |N|)^2, scaled by a **weight** derived from the previous octave's signal times a gain and clamped
  to [0, 1]. Where the coarse octave is low (valleys), finer octaves are suppressed; on ridges they are kept. Rough
  areas get rougher and smooth areas smoother: real terrain's heterogeneity. Typical starting values: H about 1, offset
  about 1, gain about 2.

### 7.4 Hybrid multifractal and heterogeneous terrain

Musgrave's notes ("Procedural Fractal Terrains") describe the **hybrid multifractal**: each octave is (N + offset)
times its spectral weight, added in proportion to a running weight that is multiplied by each new signal and capped at 1.
Peaks and valleys end up with different roughness, like mountains rising from plains. Suggested start: H 0.25, offset
0.7. He reports building Bryce 4's "ridges", "Mordor" and "shattered hills" terrains from this skeleton with different
bases (1 - |Perlin|, Worley distance-squared, Worley distance). His candid footnote is a lesson in itself: the function
did not do what he intended (valleys are defined by derivatives, not low values), but the look was good, so it stayed.

### 7.5 Derivative-damped fBm ("erosion" fBm, iq)

Accumulate each octave's analytic derivative, d, and divide the next octave's contribution by (1 + |d|^2). On steep
slopes the fine octaves fade; on flat ground they stay: an erosion-like look for almost no cost. iq reports analytic
normals give up to a 6x speedup over central differences in volumetric raymarching. Pointer: `MdX3Rr/buffer_a.glsl:70`
(Elevated, iq; read only).

---

## 8. Domain warping: bend the address before the lookup

**Idea.** Instead of evaluating f(p), evaluate f(p + h(p)) where h is itself noise (a vector-valued displacement).
Musgrave called it **domain distortion** (Bryce's "lava" terrain is fBm distorted by fBm, with a distortion around 0.3);
iq's article "Domain warping" (2002) made it the signature look of the demoscene and Shadertoy.

**Hardware analogy:** it is bending the address bus before the memory read. The memory (the base pattern) is ordinary;
the crookedness comes from the address.

**The construction** (iq, restated). A 2D displacement needs two decorrelated scalars, so evaluate fBm twice at two
arbitrary far-apart offsets (iq uses offsets like (0, 0) and (5.2, 1.3); the numbers mean nothing except "far apart"):

- level 1: q = ( fbm(p), fbm(p + o1) ), result fbm(p + 4q).
- level 2: r = ( fbm(p + 4q + o2), fbm(p + 4q + o3) ), result fbm(p + 4r).

Each level folds the pattern further: marble, smoke, gas giants, flowing paint. **The intermediates are free colour
data**: iq colours by the final value, then mixes palette entries by the length of q and by components of r, so different
"flow layers" get different hues. That is the trick behind the lush colour in his warping shaders (pointers: `4s23zz`,
`lsl3RH`; restrictive headers, read only). Animate by feeding time into the inner level only; the outer levels carry the
motion along.

**Cost.** Level 2 costs five fBm calls (two for q, two for r, one final): five times octaves noise evaluations. A
6-octave, 2-level warp is 30 noise calls per pixel. Use fewer octaves in the inner layers; they are smoothed by the
outer ones anyway.

**Derivatives under warping.** Chain rule through the Jacobian of the warp: grad f(p + h(p)) = (I + J_h)^T grad f. With
analytic fBm gradients that is exact but costly; in practice most artists use finite differences here.

**Mistake to see.** Warping *raises* the effective frequency where the warp compresses space (the Jacobian stretches),
so a well-filtered fBm becomes aliased after warping: you see sparkle and thread-like streaks along the flow. Keep warp
amounts moderate or reduce inner octaves.

**Relatives.** Warping an SDF (signed distance field) makes organic shapes; warping Voronoi makes cells look like
living tissue (`4tlSzl`, Shane's Combustible Voronoi, read only). Advection-style warping (small scales carried by large
scales) is Perlin and Neyret's flow noise (section 9.4).

---

## 9. Flow: curl noise, bitangent noise, flow noise

### 9.1 Why ordinary noise makes bad wind

If particles follow the gradient of a noise field, they slide downhill and pile up in the valleys ("sinks", which
Robert Bridson calls gutters). Real air and water are **incompressible**: what flows into a region flows out
(divergence zero). **Analogy:** a sealed coolant loop with no reservoirs and no leaks.

### 9.2 Curl noise (Bridson, Hourihan, Nordenstam, SIGGRAPH 2007)

Use noise as a **potential**, and take the velocity to be its curl. A vector-calculus identity guarantees the curl of
anything smooth has zero divergence, so the flow is incompressible by construction.

- **2D:** the potential is one scalar psi (the fluid-dynamics "stream function"; its contour lines are the streamlines).
  Velocity v = ( d psi/dy, - d psi/dx ): the gradient rotated by 90 degrees. With an analytic-gradient noise this costs
  one noise evaluation.
- **3D:** the potential is a vector (psi1, psi2, psi3), three decorrelated noises (the same noise at large offsets is
  fine). Velocity v = ( d psi3/dy - d psi2/dz, d psi1/dz - d psi3/dx, d psi2/dx - d psi1/dy ).
- **Scale.** For noise N(x/L) the vortices are about L across and speeds about 1/L; scale psi for the speed you want.
- **Octaves.** Adding octaves with a power-law falloff resembles physical (Kolmogorov) turbulence, by the authors'
  argument; it is not just an artistic choice.
- **Finite differences** were the paper's choice (step about 10^-4 of the domain size, fine in single precision). With
  analytic-gradient noise (simplex or `psrdnoise`), 3D curl costs three noise-with-gradient evaluations instead of
  twelve or more plain ones.
- **Modulate the potential, never the velocity.** Multiplying v by a mask breaks incompressibility (particles clump
  again); multiplying psi by a mask keeps it.
- **Boundaries.** For a solid the flow must slide along, not through: multiply the potential by a smooth odd ramp of the
  distance to the wall, r(t) = (15t - 10t^3 + 3t^5)/8 for |t| < 1 and plus or minus 1 beyond (zero at the wall, flat at
  plus or minus 1), with width about the noise scale. In 3D ramp down only the components of psi tangent to the wall and
  keep the normal component. The paper also gives potentials for rigid motion, vortex rings and vortex curves.

### 9.3 Bitangent noise (Ivan DeWolf 2005; popularised by atyuwen, MIT)

Take two scalar noises a and b with analytic gradients; the velocity v = grad a x grad b (cross product) is
divergence-free too (the divergence expands to terms containing curl(grad a) and curl(grad b), both identically zero).
Cost: two noise-with-gradient evaluations instead of three. The streamlines lie along the intersection of a's and b's
level sets. Good default for 3D particle swarms.

### 9.4 Flow noise (Ken Perlin and Fabrice Neyret, SIGGRAPH 2001 sketch)

Animate a 2D noise by **rotating every lattice gradient** by an angle that grows with time (finer octaves rotate faster),
and advect fine octaves along the coarse octaves' flow ("pseudo-advection"). The pattern swirls and billows in place
instead of sliding or boiling. Gustavson and McEwan's `psrdnoise` implements rotation as a single added angle in 2D
and extends it, non-trivially, to 3D (a per-vertex random rotation axis). Because rotation is periodic, the animation
loops exactly (period 2 pi in the angle).

**Why not just slice 3D noise and move along z?** Gustavson and McEwan (citing Cook and DeRose and the projection-slice
theorem) explain that a 2D slice of band-limited 3D noise gains low-frequency content: the slice "pops", changes
character, and is no longer band-pass, so octave clamping (section 12) is wrong for it. Rotating gradients keeps the
band and costs less. In the corpus, nimitz's "Noise animation - Flow" (`MdlXRS/image.glsl:31`, read only) is an
explicitly flow-noise-inspired rotate-and-advect fBm.

**Corpus note.** Search the corpus for "curl" and what you find is mostly grid fluid *simulation* (vorticity
confinement, `4tGfDW`; curl terms in a feedback warp, `ldcSDB/buf_a.glsl:54`), not curl noise. Procedural
divergence-free noise is a gap the house library can fill.

---

## 10. Tileable and looping noise

**Why it matters here.** Seamless textures baked to images; backgrounds that loop; animations that repeat exactly; and,
for this house, **time that can be wrapped** before float precision rots it (finding 2).

**Technique 1: lattice wrap.** Hash `mod(cell, P)` instead of `cell`, with P an integer number of cells. The noise
repeats every P cells. Use float `mod` or a positive integer remainder: in GLSL ES 3.00 the `%` operator on negative
integers is undefined, so `((i % P) + P) % P` or float `mod`. Works for value, gradient and cellular noise (wrap the cell
index before hashing the feature point).

**fBm that tiles** needs every octave to tile *at the same physical period*: octave i has period P L^i cells, so L
must be an integer (exactly 2, no detuning) and you cannot rotate octaves by arbitrary angles (a rotated lattice does
not tile on the axis grid). Decorrelate octaves with **per-octave seeds** instead of rotation and detuning. That is the
key design difference between `fbm` and `fbm_tiled` in the API below.

**Technique 2: periodic simplex (`psrdnoise`).** Gustavson and McEwan restructured the grids: their 2D grid tiles over
any integer period in x and any *even* integer period in y; their 3D grid is axis-aligned and tiles with any integer
period on x, y, z (Perlin's rotated orientation also tiles, but only in multiples of 3). MIT licensed, with derivatives
and flow rotation. Mind the axis-aligned-plane artifact (section 5).

**Technique 3: the flat torus.** To make a seamless 2D tile from non-periodic noise, map the tile coordinates (u, v)
in [0, 1) to a 4D point (R cos 2 pi u, R sin 2 pi u, R cos 2 pi v, R sin 2 pi v) and evaluate 4D noise. This embedding is
the "Clifford torus", which is intrinsically flat, so the pattern is not stretched; feature size is set by R (the tile
is 2 pi R noise-units around). Cost: one 4D noise per octave (simplex 4D: 5 corners; gradient 4D: 16). For a **looping
animation**, do the same with time only: put time on a circle (R cos 2 pi t/T, R sin 2 pi t/T) and add it as extra
dimensions to the spatial coordinates.

**Technique 4: cross-fading copies.** Blend f(x), f(x - W), f(y - H) ... with linear weights. Seamless but the middle of
the tile loses contrast (averaging independent noise lowers variance) and the result is no longer stationary. Avoid
except for quick bakes.

**Breaking repetition of a stored texture** (iq, "Texture repetition"): per-tile random offset and rotation with
blended borders (4 fetches), Voronoi-bombed randomly transformed copies (9 fetches), or a low-frequency noise selecting
between 8 virtual variations (2 fetches). All three need explicit derivatives passed to `textureGrad` because the
transformations break automatic mip selection.

**The time-wrap recipe for the house.** Keep host-side time as a 64-bit double (JavaScript numbers already are), pass
`u_time = t mod T` to the shader (T a few hours, or the loop period), and make every time-driven noise either periodic
in T (technique 1 or 3 in the time axis, or rotation by 2 pi t/T) or tolerant of a jump at the wrap. Then the shader
never sees a large float. The float32 rot table:

| page uptime | smallest u_time step | 60 Hz frames per step |
|---|---|---|
| 1 hour | 0.00024 s | 0.01 |
| 1 day | 0.0078 s | 0.47 |
| 4 days | 0.031 s | 1.88 |
| 1 week | 0.0625 s | 3.75 |
| 30 days | 0.25 s | 15 |

---

## 11. Analytic derivatives: getting the slope for free

**Why.** The derivative of a noise field is what you need for lighting a bumped or displaced surface (the normal),
for curl and bitangent flow, for erosion-style fBm, for anti-aliasing (the gradient sets how fast the value changes per
pixel), and for raymarching heightfields (step size from slope).

**Analogy.** Finite differences run the whole pipeline again for every axis (two to six extra evaluations); analytic
derivatives are like a fused multiply-add that returns two results from one pass through the silicon, because the slope
is built from intermediate values the value computation already has in registers.

**The formulas in this report:** value noise (section 3), gradient noise (section 4), simplex (section 5), fBm with
rotation (7.1), warping (8), Worley F1 (unit vector from the point, 6.1). **Normals of a heightfield** y = h(x, z):
n = normalise(-dh/dx, 1, -dh/dz). **For an SDF displaced by noise**, add the noise gradient to the SDF gradient before
normalising (approximately valid when the displacement is small relative to curvature).

**The fade curve decides derivative quality.** With the cubic curve, the derivative is continuous but its own slope
jumps on grid lines; highlights computed from analytic normals then show the grid even more clearly than finite
differences would. Use the quintic curve whenever derivatives are consumed.

**Always verify.** Compare analytic gradients to central differences (step about 10^-3 of a cell) on the CPU twin;
relative error should be under 10^-3. Most derivative bugs are a missing chain-rule factor (frequency, rotation, or the
fade-curve slope).

---

## 12. Anti-aliasing and filtering procedural noise

**The problem.** A texture has mipmaps; a procedural function does not. Ask fBm for 12 octaves at a pixel that covers
a whole lattice cell of octave 8, and octaves 9 to 12 alias into sparkle, moire, and shimmering crawl when the camera
or time moves. **Analogy:** sampling audio without the anti-aliasing low-pass filter before the ADC (analogue-to-digital
converter).

**Frequency clamping** (Norton, Rockwood, Skolmoski 1982, as surveyed by Lagae et al.). Fade out each octave as its
frequency approaches the pixel's Nyquist limit. Estimate the pixel footprint in noise space with screen-space
derivatives, `w = max(length(dFdx(p)), length(dFdy(p)))` (or `fwidth`), and weight octave i (frequency f_i) by a factor
that is 1 when f_i w is below about 0.25 and 0 above about 0.5 (a smoothstep between). Use Musgrave's fractional-octave
blend so the fade is continuous. Limits, from the survey: Perlin noise is only *weakly* band-limited, so clamping
needs tuning; it is isotropic, so a surface at a grazing angle must choose between blur and residual aliasing; and a
2D slice of 3D noise is not band-limited at all.

**Non-linear operations re-alias.** abs (turbulence, ridges), thresholds, sine waves (marble) and colour ramps all
create new high frequencies after you filtered. Remedies: smooth the fold (`sqrt(n*n + e)` instead of `abs(n)` lowers
the crease), build thresholds with `smoothstep(t - w, t + w, n)` where w comes from `fwidth(n)`, and filter the *colour
ramp* instead of the noise (Rhoades et al. 1992: average the ramp over the value range the pixel spans, conveniently
with a mipmapped 1D ramp texture).

**Filterable by design:** Gabor noise (analytic filtering of each kernel), wavelet noise (band-limited octaves),
psrdnoise gradients (exact derivatives for analytic anti-aliasing). **The fallback** is supersampling: correct but costs
the whole shader 4 to 16 times.

---

## 13. Dithering noise: blue noise, IGN, R2, and quantisation

### 13.1 The problem: banding

An 8-bit output has 256 levels per channel. A dark, smooth gradient may span only a dozen levels across the screen, so
the eye sees steps ("banding"). Raymarched fog has a second, worse version: a fixed step size makes depth contours
("march banding").

**Dither** adds a small noise *before* the rounding, so the error turns into fine-grained noise instead of contour
lines. Dither theory from audio (Lipshitz, Wannamaker, Vanderkooy 1992) gives the numbers. Let one code value (one
"LSB", least significant bit) be D = 1/255:

- **Uniform (RPDF) dither**, plus or minus D/2: removes banding, but the visibility of the noise still depends on the
  signal level (noise modulation). Error variance D^2/12.
- **Triangular (TPDF) dither**, plus or minus D (the difference of two independent uniforms): the error's mean and
  variance become independent of the signal. Variance D^2/6. This is the textbook choice. More amplitude than plus or
  minus one code value only adds grain.

**Where:** in the *output encoding* space (after the sRGB transfer function), right before the 8-bit write, because
that is where the rounding happens. Dithering in linear space before encoding puts the wrong amount of noise in the
shadows.

**Analogy:** this is noise-shaping in a sigma-delta audio DAC: you cannot remove quantisation error, but you can push it
to frequencies where the receiver (ear or eye) does not look.

### 13.2 Which noise: white, Bayer, blue, IGN, R2

- **White noise** (any good hash): unbiased, but clumpy; clumps are low-frequency, which the eye sees.
- **Bayer (ordered) matrix**: perfectly even, but its energy sits at a few frequencies, so you see a crosshatch.
- **Blue noise**: random but with almost no low-frequency energy; the error looks like fine, even grain that the eye's
  own blur averages away (Christoph Peters: blurring blue noise returns nearly the original value). Generated offline
  by Robert Ulichney's **void-and-cluster** algorithm (SPIE 1993): place pixels one at a time in brightness order, each
  time filling the biggest "void" of a Gaussian-blurred mask. Peters recommends a Gaussian width of 1.9 pixels as the
  balance between isotropy and visible order, publishes tileable textures from 16^2 to 1024^2 in 8 and 16 bits with 1-4
  channels, all **CC0** (public domain). Generation cost grows fast (about n^2 log n): 64^2 in seconds, 1024^2 in days,
  so ship his textures rather than generating at runtime. 19 corpus bindings use Shadertoy's blue-noise texture, e.g.
  as a raymarch start offset in `DtdSz7/buffer_b.glsl:281`.
- **Interleaved gradient noise (IGN)**, Jorge Jimenez (Activision, "Next Generation Post Processing in Call of Duty:
  Advanced Warfare", SIGGRAPH 2014): one line of arithmetic on the pixel coordinate,
  `fract(52.9829189 * fract(0.06711056 x + 0.00583715 y))`. Alan Wolfe's analysis: every 3x3 block holds nearly all of
  0/9..8/9, like an imperfect sudoku whose error drifts across the screen. Designed for temporal anti-aliasing (TAA)
  history rejection; animated by shifting the pixel coordinate by 5.588238 times (frame mod 64). Jimenez reportedly
  tuned the constants by hand.
- **R2 sequence** (Martin Roberts, "The unreasonable effectiveness of quasirandom sequences"): a two-dimensional
  golden-ratio stride. With rho = 1.3247179572 (the plastic number, the real root of x^3 = x + 1),
  mask(x, y) = fract( x / rho + y / rho^2 ) = fract( 0.7548776662 x + 0.5698402910 y ). Even, cheap, texture-free;
  Roberts' article demonstrates it as a dither mask against blue noise. **Analogy:** a memory interleave stride chosen
  so no two nearby requests hit the same bank.

### 13.3 Rules of use (Peters, Wolfe, and house doctrine)

- **Tile in screen space with `texelFetch`** at the integer pixel coordinate masked by the texture size; no filtering,
  no mipmaps, linear (not sRGB) storage.
- **Never use the same channel for two decisions in one frame** (Peters): they become correlated. Use R, G, B, A for
  four quantities; more need more textures.
- **Uniform to triangular without losing the blue spectrum:** pass the blue-noise value u through the inverse
  cumulative distribution of the triangle: t = sqrt(2u) - 1 for u < 0.5, else 1 - sqrt(2 - 2u). The ranking (and
  therefore the spatial spectrum) is preserved, the histogram becomes triangular.
- **Over time** (only when something accumulates frames, such as TAA): offset by the golden ratio conjugate,
  u_t = fract(u + 0.6180339887 t), or cycle different textures. Spatiotemporal blue noise (Alan Wolfe, Nathan Morrical,
  Tomas Akenine-Moller, Ravi Ramamoorthi, EGSR 2022) is blue in space *and* time.
- **House doctrine:** the house has no temporal accumulation, and shader-craft floor 8 forbids per-frame jitter
  (crawling grain). So the house default is a **static** blue-noise or R2 mask, at plus or minus one code value
  (triangular), in output space, last in the chain. IGN's strengths are temporal; it works as a static mask too, but its
  sudoku drift can show faint diagonal structure at high contrast, so compare it against blue noise on a dark ramp.
- **Raymarch jitter:** offset the march start by (mask value times step length), static per pixel. Blue noise turns
  march banding into the finest possible grain. (Monte Carlo renderers go further: Eric Heitz, Laurent Belcour and
  co-authors, 2019, scramble per-pixel Sobol sequences so the *error* is blue noise in screen space.)
- **Know your panel.** Frost Kiwi's banding article reports that on 6-bit panels with their own temporal dithering,
  shader dither can interfere with the panel's; test on the real display.

---

## 14. Common mistakes and how they look on screen

| what you see | likely cause | fix |
|---|---|---|
| diagonal stripes or moire in "random" grain, worse far from the origin or after hours of uptime | `fract(sin)` hash fed large coordinates or growing time | integer hash (`pcg3d`); wrap time host-side |
| grain or noise differs between two machines or browsers | trig hash depends on the GPU's `sin` | integer hash |
| blocky "random" tiles, or two neighbouring cells with identical values | `mediump` precision, or float lattice coordinates past 2^24 | `highp`; integer cell ids; keep coordinates small |
| repeating pattern every N cells in a hash or noise | 1D hash fed a linear combination of coordinates (JCGT Fig. 6) | native N-D hash or nesting |
| faceted highlights, grid-aligned creases in lighting on a noise-displaced surface | cubic fade curve (second-derivative jump) | quintic fade curve |
| plus signs, diamonds and boxy blobs aligned to the axes | value noise, or fBm without per-octave rotation | gradient or simplex basis; rotate octaves |
| a pinch or symmetric feature at the origin | every octave of gradient noise is zero at (0,0) | per-octave offsets or seeds |
| peaks that stack into unnatural regular bumps | lacunarity exactly 2.0, octaves share lattice points | detune to 2.01-2.03 (non-tiling case) |
| fine sparkle in the distance, shimmer when moving | too many octaves for the pixel footprint | frequency clamping with `fwidth`; fewer octaves |
| sharp glittering crease lines on ridges or turbulence | `abs()` creates frequencies above Nyquist | smooth abs; anti-aliased thresholds; filter the ramp |
| animated 2D noise "boils" and pops, changes character | 2D slice of 3D noise moved along z | rotating gradients (flow noise / `psrdnoise` alpha) |
| grid-plane artifacts in a slice of tiling 3D simplex noise at z near multiples of 0.5 | axis-aligned simplex grid (Gustavson and McEwan) | skew or rotate the input before slicing |
| faint seams along triangle edges in simplex noise or its normals | 3D kernel radius 0.6 (Perlin's reference) | r^2 = 0.5, cube power |
| cut corners on Voronoi cells, wrong F2 | 3x3 search with full jitter | jitter about 0.85, or 5x5 search |
| cell outlines whose thickness wobbles from cell to cell | F2 - F1 used as a distance | iq's bisector edge distance |
| jittery Voronoi borders far from the origin | absolute-coordinate distance math | cell-relative coordinates |
| seams in a "tileable" fBm | non-integer lacunarity, octave rotation, or non-integer period | integer lacunarity, per-octave seeds, integer periods |
| washed-out middle of a cross-faded tile | averaging independent noise lowers variance | lattice wrap or flat-torus mapping |
| over-bright or clipped fBm when octaves change | no normalisation by the amplitude sum | divide by (1 - G^n)/(1 - G) |
| particles collect in lines and clumps | gradient-noise velocity has divergence; or velocity (not potential) was masked | curl or bitangent noise; mask the potential |
| noisy, jittering curl velocities | finite-difference step too small for float32 | analytic gradients, or step about 10^-4 of the domain |
| stretched, threaded streaks in a warped pattern | warp too strong for the octave count (compression aliasing) | lower warp amount or inner octaves |
| visible crawling grain | per-frame dither or jitter (time in the hash) | static mask (house floor 8) |
| dither visible as noise in shadows but not highlights | dithered in linear space before sRGB encode | dither in output encoding space |
| two dithered quantities showing correlated patterns | same blue-noise channel reused | separate channels or textures |
| animation stutters after days of uptime | float32 `u_time` precision | wrap time, periodic noise in time |

---

## 15. The primitive API for the house library

### 15.1 Design rules

- **One family per module file** in `arsenal/web/glsl/` (the house library the resolver in `arsenal/shaders/modules.py`
  composes). Dependencies are read from the code, so a module calling `pcg3d` pulls in the hash module automatically.
  GLSL overloading by parameter type is allowed and used (`noise_grad(vec2)` and `noise_grad(vec3)` in one module).
- **Range convention:** base noises return *signed* values roughly in [-1, 1] and are histogram-measured and
  normalised; hashes and masks return [0, 1). Helper names never hide which.
- **Derivative convention:** the `_d` variant returns the value in `.x` and the gradient in `.yz` (2D) or `.yzw` (3D),
  in world space (chain rule already applied).
- **Integers under the floats:** every lattice noise hashes integer cell ids with `pcg3d`/`pcg4d`; no trig hash
  anywhere in the library. Seeds are `uint`.
- **No macros that hide calls** (the resolver cannot see through them); basis choice is in the function name.
- **Every module carries a CPU twin** (numpy) for tests: determinism, range histogram, derivative check against central
  differences, periodicity check (seam difference exactly zero), spectral flatness for hashes (about 0.56), radially
  averaged power spectrum for noises, and a float32 long-uptime check. These are the "dissect" tools Lagae et al.
  recommend (periodogram plus amplitude histogram), and they run without touching the GPU.

### 15.2 The modules and signatures

All signatures below are written fresh for the house. The contract is one line.

**Module `noise.hash`** (integer hashing, the dice)
- `uint hash_u(uint x)`: PCG-style 1-in-1-out hash (LCG step plus permuted output); full avalanche on all 32 bits.
- `uvec2 pcg2d(uvec2 v)`: 2-in-2-out integer hash; every output bit depends on both inputs.
- `uvec3 pcg3d(uvec3 v)`: Jarzynski-Olano 3-in-3-out hash; default for lattice corners and per-pixel randomness.
- `uvec4 pcg4d(uvec4 v)`: 4-in-4-out hash; use for (x, y, z, seed) or (x, y, frame, seed).
- `float u01(uint x)`: top 24 bits to a float in [0, 1), exactly representable, never 1.0.
- `vec3 u01(uvec3 x)`: per-lane version of u01 (overloads for uvec2 and uvec4 likewise).
- `uvec3 cell_u(vec3 p)`: floor to integer cell and reinterpret as uint (two's-complement wrap makes negatives safe).
- `vec3 hash33(ivec3 cell, uint seed)`: three uniform values in [0, 1) for a lattice cell and stream seed.
- `float hash_f(vec3 p)`: hash of an arbitrary float position via its exact bit pattern; [0, 1).
- `vec2 rand_dir2(uint h)`: uniformly distributed unit vector on the circle from a hash.
- `vec3 rand_dir3(uvec2 h)`: uniformly distributed unit vector on the sphere from two hash words.

**Module `noise.fade`** (interpolants)
- `vec3 fade3(vec3 t)`: cubic Hermite 3t^2 - 2t^3 per component; C1, cheap, not for derivatives.
- `vec3 fade3_d(vec3 t)`: slope of fade3, 6t(1 - t).
- `vec3 fade5(vec3 t)`: quintic 6t^5 - 15t^4 + 10t^3; C2, the default.
- `vec3 fade5_d(vec3 t)`: slope of fade5, 30t^2(1 - t)^2.

**Module `noise.lattice`** (value and gradient noise)
- `float noise_value(vec2 p, uint seed)`: signed value noise, quintic fade, integer-hashed corners (vec3 overload).
- `vec3 noise_value_d(vec2 p, uint seed)`: value noise plus exact gradient in .yz (vec3 overload returns vec4).
- `float noise_grad(vec2 p, uint seed)`: improved Perlin gradient noise, quintic fade, unbiased gradient set (vec3 overload).
- `vec3 noise_grad_d(vec2 p, uint seed)`: gradient noise plus exact gradient (vec3 overload returns vec4).

**Module `noise.simplex`**
- `float noise_simplex(vec2 p, uint seed)`: 2D simplex noise with a seam-free kernel; about [-1, 1].
- `float noise_simplex(vec3 p, uint seed)`: 3D simplex noise, kernel r^2 = 0.5, cubic falloff (no face seams).
- `vec4 noise_simplex_d(vec3 p, uint seed)`: 3D simplex value plus exact gradient (vec2 overload returns vec3).
- `float noise_flow(vec2 p, vec2 period, float angle, out vec2 grad)`: periodic simplex with rotating gradients (flow noise) and exact gradient; period 0 disables tiling.
- `float noise_flow(vec3 p, vec3 period, float angle, out vec3 grad)`: 3D version; avoid axis-aligned slices.

**Module `noise.cellular`**
- `vec3 cell_f1f2(vec2 p, float jitter, uint seed, out vec2 to_nearest)`: (F1, F2, nearest cell id in [0,1)) and the vector to the nearest feature point.
- `vec3 cell_f1f2(vec3 p, float jitter, uint seed, out vec3 to_nearest)`: 3D version (27-cell search).
- `float cell_edge(vec2 p, float jitter, uint seed)`: exact distance to the nearest Voronoi wall (two-pass bisector method).
- `float cell_smooth(vec2 p, float jitter, float sharpness, uint seed)`: smooth F1 via exponential smooth-minimum; order-independent.
- `float voronoise(vec2 p, float jitter, float blend, uint seed)`: iq-style generalisation spanning cell noise, value noise and Voronoi.
- `float cell_f1_metric(vec2 p, float jitter, float minkowski_p, uint seed)`: F1 under a Minkowski distance (1 = Manhattan, 2 = Euclidean, large = Chebyshev).

**Module `noise.fractal`**
- `float gain_from_hurst(float hurst, float lacunarity)`: returns lacunarity^(-hurst); H = 1 gives 0.5 at L = 2.
- `float fbm(vec2 p, int octaves, float lacunarity, float gain, uint seed)`: normalised fBm of gradient noise with per-octave rotation, detune and offset (vec3 overload).
- `vec3 fbm_d(vec2 p, int octaves, float lacunarity, float gain, uint seed)`: fBm value plus world-space gradient via the chain rule through octave rotations.
- `float fbm_simplex(vec3 p, int octaves, float lacunarity, float gain, uint seed)`: fBm on the simplex basis (cheaper in 3D).
- `float fbm_turbulence(vec3 p, int octaves, float lacunarity, float gain, uint seed)`: sum of absolute values, normalised to [0, 1].
- `float fbm_billow(vec3 p, int octaves, float lacunarity, float gain, uint seed)`: per-octave 2|n| - 1, puffy clouds; about [-1, 1].
- `float fbm_ridged(vec3 p, int octaves, float lacunarity, float hurst, float offset, float ridge_gain, uint seed)`: Musgrave ridged multifractal with clamped feedback weight.
- `float fbm_hybrid(vec3 p, int octaves, float lacunarity, float hurst, float offset, uint seed)`: Musgrave hybrid multifractal (smooth valleys, rough peaks).
- `float fbm_eroded(vec2 p, int octaves, uint seed)`: derivative-damped fBm, each octave divided by (1 + squared accumulated slope).
- `float fbm_cell(vec2 p, int octaves, float lacunarity, float gain, float jitter, uint seed)`: fractal Worley F1 ("crumpled foil", sea surface).
- `float fbm_aa(vec2 p, float footprint, int max_octaves, float lacunarity, float gain, uint seed)`: frequency-clamped fBm that fades octaves at the pixel's Nyquist limit.

**Module `noise.warp`**
- `vec2 warp_vec(vec2 p, int octaves, uint seed)`: decorrelated 2D displacement field made of two fBm at far-apart offsets.
- `float warp_fbm(vec2 p, float amount, int octaves, uint seed)`: one-level domain warp, fbm(p + amount * warp_vec(p)).
- `float warp_nested(vec2 p, float amount, int octaves, uint seed, out vec2 q, out vec2 r)`: two-level nested warp returning both intermediates for colouring.

**Module `noise.flow`** (divergence-free)
- `vec2 curl2(vec2 p, uint seed)`: 2D curl of a gradient-noise stream function, from analytic gradients (one evaluation).
- `vec3 curl3(vec3 p, uint seed)`: 3D curl of three decorrelated noise potentials, analytic (three evaluations).
- `vec3 curl3_fbm(vec3 p, int octaves, float lacunarity, float gain, uint seed)`: multi-octave turbulent curl field (power-law octaves).
- `vec3 bitangent3(vec3 p, uint seed)`: divergence-free velocity as the cross product of two noise gradients (two evaluations).
- `float wall_ramp(float t)`: Bridson's odd quintic ramp, (15t - 10t^3 + 3t^5)/8 clamped to plus or minus 1.
- `vec3 psi_near_wall(vec3 psi, vec3 wall_normal, float dist, float width)`: damps only the tangential part of a 3D potential near a solid wall.

**Module `noise.dither`** (masks and quantisation)
- `float ign(vec2 pixel)`: Jimenez interleaved gradient noise in [0, 1); static.
- `float ign(vec2 pixel, int frame)`: animated IGN (5.588238 pixel stride per frame, frame mod 64); temporal pipelines only.
- `float r2_mask(vec2 pixel)`: Roberts R2 low-discrepancy mask in [0, 1); static, texture-free.
- `float blue_mask(sampler2D tex, ivec2 pixel, int channel)`: texelFetch of a tiled CC0 blue-noise texture, one channel per decision.
- `float tri_from_uniform(float u)`: inverse-CDF remap of [0,1) to a triangular [-1,1] that preserves the mask's spectrum.
- `float golden_step(float u, int frame)`: fract(u + frame * 0.6180339887), for decorrelating a mask across frames.
- `vec3 dither_out(vec3 encoded, float mask01, float bits)`: adds triangular plus or minus one code value in output-encoded space, last before the write.

**Module `noise.periodic`**
- `float noise_grad_tiled(vec2 p, ivec2 period, uint seed)`: gradient noise repeating every `period` cells (lattice wrap, safe for negatives).
- `float fbm_tiled(vec2 p, ivec2 period, int octaves, float gain, uint seed)`: tileable fBm (lacunarity exactly 2, per-octave seeds, no rotation).
- `vec3 cell_f1f2_tiled(vec2 p, ivec2 period, float jitter, uint seed)`: Worley F1, F2, id repeating every `period` cells.
- `float noise_torus(vec2 uv01, float radius, uint seed)`: seamless tile via 4D simplex noise on a flat torus.
- `float noise_loop(vec3 p, float phase01, float radius, uint seed)`: seamless time loop (phase on a circle as extra dimensions).

**Module `noise.filter`**
- `float octave_weight(float freq, float footprint)`: 1 for well-sampled octaves, smoothly 0 as freq * footprint approaches 0.5.
- `float aa_threshold(float x, float edge)`: anti-aliased step using fwidth(x) as the transition width.
- `float smooth_abs(float x, float k)`: crease-free absolute value, sqrt(x^2 + k), for turbulence and ridges.

### 15.3 Groupings for the bench UI (tweak one, everything updates)

The bench can expose the families as one card each with shared knobs, because the parameters mean the same thing
everywhere:

| card | shared knobs | what it shows |
|---|---|---|
| Dice | hash, seed | hash image, bit-plane view, spectral flatness |
| Basis | basis (value, gradient, simplex, cellular, voronoise), frequency, fade | one octave, its histogram and radial spectrum |
| Fractal | octaves, lacunarity, gain or Hurst, style (fBm, turbulence, billow, ridged, hybrid, eroded) | the stack, per-octave solo and mute |
| Warp | amount, levels, inner octaves | q and r as false colour |
| Flow | potential basis, octaves, curl or bitangent | streamlines and a particle preview |
| Tile and loop | period, loop length, torus radius | 2x2 tiled preview with seam overlay |
| Finish | dither mask (blue, R2, IGN), bits, static or temporal | banding test ramp |

Each card is a view onto the same module code, so a fix in `noise.hash` reaches every noise above it.

### 15.4 Adopt or write fresh: the licence picture

| source | licence | what we could adopt | note |
|---|---|---|---|
| `psrdnoise` (Gustavson, McEwan) | MIT | tiling simplex, flow rotation, exact gradients | the best-documented periodic simplex there is |
| `webgl-noise` (McEwan, Gustavson et al.) | MIT | classic and simplex noise, cellular | uses the older mod-289 polynomial |
| Hash without Sine (Hoskins), `4djSRW` | MIT | float hash family and naming | superseded by integer hashes for quality |
| iq `4sfGzS`, `ldl3W8`, `Xd23Dh` | MIT | value-noise LUT trick, Voronoi edges, Voronoise | MIT notice must travel with any copy |
| Peters' blue-noise textures | CC0 | the masks themselves | no conditions |
| JCGT paper code (pcg3d) | paper CC BY-ND | algorithm description only | re-implement from the description; algorithm ideas are not copyright |
| bitangent noise (atyuwen) | MIT | optimised 3D/4D implementation | |
| iq's warping, Elevated, Clouds, Rainforest and 29 more | restrictive headers | nothing; pointers only | see finding 3 |
| everything else in the corpus | CC BY-NC-SA (mostly) | nothing; pointers only | house LICENSE LINE |

My recommendation is to write the house modules fresh from the mathematics in this report (it is all here), and treat
the MIT sources as reference oracles in the CPU-twin tests (compare outputs statistically, never copy text). That keeps
every tracked file clean of third-party text and costs little. If Daniel prefers to vendor `psrdnoise` directly, MIT
allows it with the notice kept intact.

---

## 16. Where these techniques live in the corpus (pointers only)

Census over the 335 corpus shaders (a shader counts once if any of its passes matches):

| technique | shaders | share |
|---|---|---|
| `fract(sin(...))` trig hash | 123 | 37% |
| fBm by name | 63 | 19% |
| Hoskins-style `hashOI` names | 61 | 18% |
| octave rotation matrix (0.8, 0.6) family | 47 | 14% |
| Voronoi / Worley / cellular by name | 25 | 7% |
| `uint` / `uvec` integer arithmetic | 25 | 7% |
| simplex by name | 17 | 5% |
| noise with derivatives by name | 15 | 4% |
| "curl" (mostly fluid simulation, not curl noise) | 10 | 3% |
| quintic fade curve | 7 | 2% |
| PCG hashes | 4 | 1% |

The pattern is clear: the corpus is overwhelmingly trig-hashed, cubic-faded and fBm-driven; derivative-aware,
integer-hashed, divergence-free work is rare. Study pointers:

- Hash comparison: `XlGcRh/common.glsl:622` (Jarzynski's own shader; PCG and friends side by side).
- Hash without sine family and naming: `4djSRW/common.glsl` (MIT).
- Value noise three ways (integer hash, float hash, LUT): `4sfGzS/image.glsl:26` onward (MIT); the LUT path at 98/107.
- Texture-LUT noise variants: `XslGRr/image.glsl:34-36` (read only).
- Voronoi exact interior distance: `ldl3W8/image.glsl` (MIT). Voronoise: `Xd23Dh/image.glsl` (MIT).
- Derivative-damped terrain fBm: `MdX3Rr/buffer_a.glsl:57,70` (read only).
- Derivative chain rule through rotated octaves: `4ttSWf/buffer_a.glsl:196-198` (all rights reserved; read only).
- Domain warping with colour from intermediates: `4s23zz/image.glsl`, `lsl3RH/image.glsl` (restrictive headers; read only).
- Flow-noise-inspired animation: `MdlXRS/image.glsl:31` (nimitz; read only).
- Blue-noise raymarch offset: `DtdSz7/buffer_b.glsl:281` (read only).
- Animated Voronoi fire and Voronoi heightmaps: `4tlSzl`, `ldtGWj` (Shane; read only).

---

## 17. Recommendations for the house, ranked

1. **Build `noise.hash` first and retire the trig hash.** Port `h31` callers to `pcg3d`-based helpers; keep the old
   chunk until each surface is migrated and compared side by side. Cheapest change with the widest effect.
2. **Wrap `u_time` host-side** on every long-lived surface (aurora light bed, avatar, cockpit backgrounds), and give the
   wrap a period that the time-driven noises respect. This prevents the multi-day stutter.
3. **Replace `triangular-dither`** with a static blue-noise (CC0) or R2 mask at plus or minus one code value,
   triangular, applied in output encoding space; this also resolves the floor-8 contradiction and fulfils the
   "blue-noise dither on dark gradients" item planned in shader-craft's craft study III.
4. **Rewrite `value-noise-3d` from the textbook** with the integer hash and the quintic fade (the house's volumetric
   fog is a derivative consumer if it ever lights its density), and correct its credit line.
5. **Fix the corpus licence classifier**: any header containing "sole copyright owner", "cannot use this Work", or
   "train AI" should set `license: all-rights-reserved, explicit: true`, and that rule must win over a Creative
   Commons line found in another pass of the same shader (`MdlGW7/buffer_a.glsl:2` and `tt2XzG/sound.glsl:2` carry a
   CC line while their image passes carry the restrictive header; the classifier picked the CC line). When passes
   disagree, the most restrictive licence governs the shader. Re-run over
   the 33 hits listed in finding 3.
6. **Ship the CPU twins with the modules** (numpy references plus tests); they are the only safe way to "render" noise
   on this host while the GPU stays off-limits, and they double as the dissection tools Daniel asked for.
7. **Then the looks:** `fbm` family with clamping, `cell_edge`, `warp_nested`, `curl3`/`bitangent3` for the swarms, and
   `noise_flow` for living backgrounds that loop exactly.

---

## 18. Sources

Primary papers and authors' own articles first, then tutorials.

1. Ken Perlin, "An Image Synthesizer", SIGGRAPH 1985. https://doi.org/10.1145/325165.325247 : the origin of gradient noise, turbulence, and noise-based marble.
2. Ken Perlin, "Improving Noise", SIGGRAPH 2002. https://mrl.cs.nyu.edu/~perlin/paper445.pdf : the quintic fade curve and the 12 cube-edge gradients, with reasons.
3. Ken Perlin, improved noise reference implementation. https://mrl.cs.nyu.edu/~perlin/noise/ : the canonical permutation-table implementation (Java).
4. Ken Perlin, "Noise hardware", SIGGRAPH 2002 course 36 notes. https://www.csee.umbc.edu/~olano/s2002c36/ch02.pdf : simplex noise as first presented.
5. Stefan Gustavson, "Simplex noise demystified", 2005. https://cgvr.cs.uni-bremen.de/teaching/cg_literatur/simplexnoise.pdf : skewing, simplex traversal, kernels, explained with figures.
6. Stefan Gustavson and Ian McEwan, "Tiling Simplex Noise and Flow Noise in Two and Three Dimensions", JCGT 11(1), 2022. https://jcgt.org/published/0011/01/02/ : periodic simplex grids, rotating gradients, exact derivatives, the 0.6 kernel bug, GPU timings.
7. psrdnoise repository (MIT). https://github.com/stegu/psrdnoise : the reference GLSL for item 6, with a WebGL tutorial gallery.
8. Ian McEwan, David Sheets, Mark Richardson, Stefan Gustavson, "Efficient computational noise in GLSL", JGT 2012. https://ar5iv.labs.arxiv.org/html/1204.1461 : texture-free noise with permutation polynomials mod 289.
9. webgl-noise repository (MIT). https://github.com/stegu/webgl-noise : the classic GLSL noise collection from item 8.
10. Steven Worley, "A Cellular Texture Basis Function", SIGGRAPH 1996. https://cedric.cnam.fr/~cubaud/PROCEDURAL/worley.pdf : F1..Fn, cell ids, metrics, fractal Worley, and the looks they make.
11. Mark Jarzynski and Marc Olano, "Hash Functions for GPU Rendering", JCGT 9(3), 2020. https://jcgt.org/published/0009/03/02/ : BigCrush quality vs GPU speed for 100+ hashes; pcg3d and pcg4d; the Pareto frontier.
12. Nathan Reed, "Hash Functions for GPU Rendering" (blog, 2021). https://www.reedbeta.com/blog/hash-functions-for-gpu-rendering/ : a practitioner's reading of item 11; PCG replaces the Wang hash.
13. Melissa O'Neill, "PCG: A Family of Simple Fast Space-Efficient Statistically Good Algorithms for Random Number Generation", 2014. https://www.cs.hmc.edu/tr/hmc-cs-2014-0905.pdf : the permuted congruential idea behind pcg hashes.
14. Dave Hoskins, "Hash without Sine" (Shadertoy, MIT). https://www.shadertoy.com/view/4djSRW : portable float hashes and the hashOI naming convention.
15. Inigo Quilez, "fBm". https://iquilezles.org/articles/fbm/ : Hurst exponent, gain, spectra in dB per octave, why H = 1 for mountains.
16. Inigo Quilez, "Domain warping". https://iquilezles.org/articles/warp/ : nested warps and colouring by intermediates (the page returned 404 during this research; content summarised from long familiarity and his corpus shaders).
17. Inigo Quilez, "Value noise derivatives". https://iquilezles.org/articles/morenoise/ : the polynomial form of value noise, its analytic gradient, eroded fBm.
18. Inigo Quilez, "Gradient noise derivatives". https://iquilezles.org/articles/gradientnoise/ : analytic gradient of Perlin-style noise.
19. Inigo Quilez, "Voronoi edges". https://iquilezles.org/articles/voronoilines/ : why F2 - F1 is not a distance; the two-pass bisector method.
20. Inigo Quilez, "Smooth Voronoi". https://iquilezles.org/articles/smoothvoronoi/ : exponential and power smooth-minimum Voronoi.
21. Inigo Quilez, "Voronoise". https://iquilezles.org/articles/voronoise/ : one function spanning cell noise, value noise and Voronoi.
22. Inigo Quilez, "Texture repetition". https://iquilezles.org/articles/texturerepetition/ : three ways to hide tiling in stored textures, and the textureGrad requirement.
23. F. Kenton Musgrave, "Procedural Fractal Terrains" (course notes). https://www.classes.cs.uchicago.edu/archive/2015/fall/23700-1/final-project/MusgraveTerrain00.pdf : fBm parameters, octave-count rule, hybrid multifractal, domain distortion.
24. David Ebert, F. Kenton Musgrave, Darwyn Peachey, Ken Perlin, Steven Worley, "Texturing and Modeling: A Procedural Approach", 3rd ed., 2002 (book) : the ridged multifractal and the classic procedural toolkit.
25. Ares Lagae, Sylvain Lefebvre, Rob Cook, Tony DeRose, George Drettakis, David Ebert, J.P. Lewis, Ken Perlin, Matthias Zwicker, "A Survey of Procedural Noise Functions", CGF 2010. https://www.cs.umd.edu/~zwicker/publications/SurveyProceduralNoise-CGF10.pdf : the formal definition, families, spectral control, filtering, and analysis tools.
26. Robert Cook and Tony DeRose, "Wavelet Noise", SIGGRAPH 2005. https://doi.org/10.1145/1073204.1073264 : band-limited noise and the slice-projection problem.
27. Robert Bridson, Jim Hourihan, Marcus Nordenstam, "Curl-Noise for Procedural Fluid Flow", SIGGRAPH 2007. https://www.cs.ubc.ca/~rbridson/docs/bridson-siggraph2007-curlnoise.pdf : divergence-free flow from potentials, boundaries, vortex primitives.
28. atyuwen, "bitangent_noise" (MIT). https://github.com/atyuwen/bitangent_noise : divergence-free noise from two gradients (credits Ivan DeWolf, 2005).
29. Ken Perlin and Fabrice Neyret, "Flow Noise", SIGGRAPH 2001 sketch. http://evasion.imag.fr/Publications/2001/PN01/ : rotating gradients and pseudo-advection.
30. Christoph Peters, "Free blue noise textures". https://momentsingraphics.de/BlueNoise.html : void-and-cluster in practice, usage rules, CC0 textures.
31. Robert Ulichney, "Void-and-cluster method for dither array generation", SPIE 1993. https://doi.org/10.1117/12.152707 : the original blue-noise mask algorithm.
32. Alan Wolfe, "Interleaved Gradient Noise: A Different Kind of Low Discrepancy Sequence" (2022). https://blog.demofox.org/2022/01/01/interleaved-gradient-noise-a-different-kind-of-low-discrepancy-sequence/ : why IGN works and how to animate it.
33. Alan Wolfe, "Generating Blue Noise Textures With Void And Cluster" (2019). https://blog.demofox.org/2019/06/25/generating-blue-noise-textures-with-void-and-cluster/ : a readable walk through generation.
34. Jorge Jimenez, "Next Generation Post Processing in Call of Duty: Advanced Warfare", SIGGRAPH 2014 Advances course. http://advances.realtimerendering.com/s2014/index.html : the origin of IGN.
35. Alan Wolfe, Nathan Morrical, Tomas Akenine-Moller, Ravi Ramamoorthi, "Spatiotemporal Blue Noise Masks", EGSR 2022. https://cseweb.ucsd.edu/~ravir/stbn.pdf : blue noise in space and time for temporal accumulation.
36. Eric Heitz, Laurent Belcour, Victor Ostromoukhov, David Coeurjolly, Jean-Claude Iehl, "A Low-Discrepancy Sampler that Distributes Monte Carlo Errors as a Blue Noise in Screen Space", 2019. https://eheitzresearch.wordpress.com/762-2/ : blue-noise error distribution for path tracing.
37. Martin Roberts, "The Unreasonable Effectiveness of Quasirandom Sequences". https://extremelearning.com.au/unreasonable-effectiveness-of-quasirandom-sequences/ : the R2 sequence and its use as a dither mask (page refused automated fetch during this research; constants are mathematical).
38. Frost Kiwi, "How to (and how not to) fix color banding". https://blog.frost.kiwi/GLSL-noise-and-radial-gradient/ : practical banding fixes with IGN, and the 6-bit panel interference trap.
39. Bart Wronski, "Dithering part three: real world 2D quantization dithering". https://bartwronski.com/2016/10/30/dithering-part-three-real-world-2d-quantization-dithering/ : dithering choices compared on real images.
40. Patricio Gonzalez Vivo and Jen Lowe, "The Book of Shaders", chapters 10-13. https://thebookofshaders.com/11/ (noise), https://thebookofshaders.com/12/ (cellular), https://thebookofshaders.com/13/ (fBm) : the gentlest interactive introduction.
41. US patent 6,867,776 ("Standard for Perlin noise"). https://patents.google.com/patent/US6867776B2/en : the 3D+ simplex noise patent, expired January 2022.
