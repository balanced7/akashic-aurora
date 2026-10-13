# 2D generative art, patterns and fractals — a shader school report

**Lane:** pattern-fractal-2d (one of eight shader-school researchers), 2026-10-13.
**Written for:** a capable programmer who has never written a shader, and for Daniel, who learns fast and likes the
hardware view. Terms are spelled out the first time they appear.
**Licence line:** everything below is written in my own words and mathematics. No corpus code was copied. Pointers like
`wsl3WB/image.glsl:16-33` point into `state/arsenal/shaders/corpus/shaders/` for study only. The GLSL in section 16 is
signatures only, written fresh for the house (Apache-2.0 house code).
**Verification:** formulas that matter were checked numerically with small read-only Python (scratchpad
`hexcheck.py`, `mathcheck.py`): the two-grid hex method against brute-force nearest centre (0 mismatches in 20,000
points), the hex border metric (max exactly 0.5 inside a cell), the box-fold identity, the Truchet corner choice, the
golfed rotation constants, and float32 overflow and zoom limits. Nothing was rendered on the GPU.

---

## 0. The mental model in one page

A **fragment shader** is a small program the graphics card (GPU) runs once for every pixel, all at the same time. It
receives the pixel's position and returns a colour. That is all. 2D generative art is the craft of designing that one
function, position in, colour out, so that the whole screen adds up to something beautiful.

Hardware view: picture a stadium of identical calculators, one per seat (pixel). Everyone runs the same program on their
own seat number. Nobody can see anybody else's answer, with one exception that matters a great deal later: seats are
grouped in **2×2 quads**, and each seat may peek at its quad-mates' values of any expression. That peek is how the GPU
gives you **derivatives** (how fast a value changes from one pixel to the next) for free.

Every strong 2D shader in this field, from The Book of Shaders exercises to Kali's fractals, is the same pipeline in
different costumes. Learn to see these seven layers and you can dissect anything and build anything:

| Layer | Question it answers | Typical tools |
|---|---|---|
| 1. Frame | Where is the origin, which way is up, how big is one pixel? | centring, aspect correction, pixel size |
| 2. Domain | How is space bent, folded, repeated, before anything is drawn? | rotation, polar coordinates, kaleidoscopes, `fract` tiling, folds, inversions |
| 3. Cell | Which tile/sector/iteration am I in, and what are my local coordinates? | cell id, local coordinates, per-cell random numbers |
| 4. Field | What is the distance (or value) of this point to the shape? | signed distance functions (SDFs), escape-time iteration, orbit traps |
| 5. Coverage | How much of this pixel does the shape cover? | antialiasing with pixel width, derivatives, analytic filtering |
| 6. Colour | What colour does the value become? | palettes, gradients, orbit-trap colouring |
| 7. Composite | How do layers stack, glow, and fit the display? | mixing, additive glow, tonemapping |

The expert's secret is not a bag of tricks. It is (a) keeping every layer honest about **units** (is this number in
pixels, in tile units, in radians?), and (b) keeping layer 5 honest: every edge drawn is a little **filter**, sized to one
pixel, measured in the right units.

---

## 1. The frame: coordinates you can trust

**The standard frame.** Take the pixel position, subtract half the canvas size, divide by half the canvas *height*. The
centre is now (0, 0), y runs from −1 to +1, and x runs a little further on a wide screen. Dividing both axes by the
*same* number (the height) is the **aspect correction**; dividing x by the width and y by the height is the classic
beginner mistake and turns every circle into an ellipse.

**One pixel, in these units,** is 2 divided by the canvas height. Write it down once, carry it everywhere. Whenever a
domain has *not* been warped (only shifted, rotated and uniformly scaled), this constant is the exact pixel size, and it
is cheaper and steadier than any derivative.

**When the domain is warped** (polar remaps, inversions, fractal folds, noise displacement), one screen pixel covers a
different amount of the warped space at every point. Then the pixel size must be measured: ask the GPU for the screen
derivatives of the warped coordinate and take their length (section 4.2).

**Time.** One clock (`u_time` in the house). Animation should be a function of time, not of frame count, so a still can be
reproduced (house shader-craft floor 8).

---

## 2. Shaping functions: the vocabulary of curves

**The idea (The Book of Shaders, chapter 5, Patricio Gonzalez Vivo and Jen Lowe).** Before drawing shapes, learn to bend
single numbers. A *shaping function* takes a number, usually in 0..1, and returns another number, usually in 0..1. Plot
it as a curve (graph the function as a thin line across the screen; the book's first exercise) and you can *see* it.
Every animation ease, every gradient, every edge is one of these curves.

The core set, with what each is for:

- **step(edge, x):** 0 below the edge, 1 above. A hard switch. Never use it for a visible edge (it aliases; see 4.1).
- **linear step:** clamp((x − a)/(b − a), 0, 1). A straight ramp. This is the *honest* antialiasing edge (section 4.3).
- **smoothstep(a, b, x):** the cubic 3t² − 2t³ of that ramp. Flat at both ends (first derivative zero), so it joins
  smoothly to constants. Its second derivative jumps at the ends, which shows up as a faint crease in lighting.
- **smootherstep** (Ken Perlin's quintic 6t⁵ − 15t⁴ + 10t³): flat in slope *and* curvature at both ends (C2 continuous).
  Use it for motion that must not "kick", and for bands you will stack.
- **Powers:** xᵏ bends the ramp toward the bottom (k > 1) or top (k < 1). Cheap and endlessly useful.
- **Sine and cosine:** the rhythm makers. sin(f·x + φ) has frequency f and phase φ; abs(sin) gives a bouncing ball;
  fract(x) gives a sawtooth; abs(fract(x) − 0.5)·2 gives a triangle wave.

**Inigo Quilez's remapping catalogue** (iquilezles.org/articles/functions) is the professional extension. In my words:

| Name | What it does | Formula, described |
|---|---|---|
| Almost identity | Leaves a signal alone above a threshold m, but floors it smoothly to a small value n below | cubic blend between n and x over [0, m] |
| Smooth absolute value | abs() with a rounded crease | √(x² + k²), or a quadratic inside |x| < k |
| Exponential impulse | Fast attack, slow decay; peaks at exactly 1 when x = 1/k | k·x·e^(1 − k·x) |
| Polynomial impulse | Same feel without exp | 2√k·x / (1 + k·x²), peak at x = 1/√k |
| Sustained impulse | Separate attack width and release rate | min of an attack ramp and an exponential release |
| Cubic pulse | A bump of half-width w around c that is *exactly zero* outside | 1 − t²(3 − 2t) with t = |x − c|/w, zero when t > 1 |
| Rational bump | Gaussian-like, never zero, very cheap | 1/(1 + k·x²) |
| Gain | S-curve (or inverse S) on [0, 1] that keeps 0, ½ and 1 fixed | two mirrored power curves meeting at ½ |
| Parabola | 0 → 1 → 0 bump on [0, 1] | (4x(1 − x))ᵏ |
| Power curve | Asymmetric bump (good for leaves, eyes) | xᵃ(1 − x)ᵇ normalised so the peak is 1 |
| Exponential step | A step whose sharpness you can dial | 2^(−2ⁿ·xⁿ) |
| Reinhard-style remap | Lifts the middle, keeps the ends | (k + 1)·x / (1 + k·x) |

Golan Levin's shaping-function pages (polynomial, exponential, circular, elliptic and Bézier shapers) and Kynd's equation
table are the other two references the book recommends; iq's **Graphtoy** is the tool for seeing them.

**Why continuity matters later.** A shaping function with a kink (abs, step, fract) has a derivative that jumps. Any
place you later take a derivative of it (antialiasing, lighting a height map) the kink shows up as a visible line. Pick
the curve with the continuity your *downstream* use needs: C0 for colour, C1 for anything lit or antialiased, C2 for
motion you will watch closely.

**Cost.** All of these are a handful of multiply-adds; `pow`, `exp`, `sin` run on the GPU's slower *transcendental* unit
(on most GPUs a quarter of the throughput of a multiply-add, like a CPU's divider), but one or two per pixel is free.

---

## 3. Distance fields in 2D: the core abstraction

**Definition.** A **signed distance function (SDF)** returns, for a point p, the distance to the nearest point of a shape:
negative inside, positive outside, zero exactly on the edge. The Book of Shaders introduces it gently (chapter 7: a circle
is "all points whose distance to the centre is less than r"). Inigo Quilez's 2D distance catalogue
(iquilezles.org/articles/distfunctions2d) is the reference list: circle, box, rounded box, segment, every regular
polygon, stars, arcs, rings, moons, hearts, vesicas, Bézier curves, ellipses, parabolas, and more, each marked exact or
bound.

**Why it is the right currency.** One number per pixel gives you *all* of these for free:

- the fill (distance < 0),
- an outline of any width (|distance| < w),
- a glow (a falloff of distance outside),
- a drop shadow (the same field sampled at an offset),
- and, crucially, the **antialiased edge**, because distance is already measured in the same units as the pixel size.

**Exact versus bound.** An *exact* SDF returns the true Euclidean distance everywhere. A *bound* only promises not to
exceed it. For 2D drawing the difference is visible: an outline drawn from a bound gets thinner or fatter where the bound
is loose, and glows get lopsided. Prefer exact shapes for anything stroked.

**The key geometric facts (in my words):**

- **Circle:** distance = |p| − r.
- **Box with half-size b:** fold p into the first quadrant with abs (the box is symmetric, so one quadrant is enough), take
  q = |p| − b. Outside, the distance is the length of q with negative parts clamped to zero; inside, it is the largest
  component of q (which is negative). Folding by symmetry before measuring is the single most reused idea in this whole
  report; it reappears as kaleidoscopes and as KIFS fractals.
- **Segment from a to b:** project p onto the line, clamp the projection parameter to [0, 1], measure to that point.
  (The house already has this as `segD` in `design/vfx-chunks/segment-distance.glsl`.)
- **Regular N-gon:** use polar angle to fold p into one wedge of angle 2π/N, mirror within the wedge, then you are measuring
  to a single straight edge (plus its corner). The Book of Shaders shows a compact variant credited to Andrew Baldwin that
  multiplies the radius by the cosine of the angle to the nearest edge normal; it gives the right zero set, but it is a
  bound, not an exact distance, near corners.
- **Hexagon:** the polygon recipe with N = 6, or the direct form in section 6.4.

**Combining shapes.** Union is the minimum of two distances, intersection the maximum, subtraction the maximum of one and
the negated other. *Rounding* subtracts a radius (grows the shape and rounds its corners); *onion* takes |d| − w (turns any
shape into an outline of thickness 2w). A **smooth minimum** blends two shapes with a fillet of size k (iq's polynomial
smin is the standard). The SDF lane's report (`sdf-raymarching.md`, section 12) defines these operators for the house
library; this report reuses them rather than redefining them.

**Common mistake: sign confusion.** Some sources use positive inside. Pick one convention (negative inside, as here) and
put it in every contract.

---

## 4. Antialiasing: the expert's core skill

### 4.1 What aliasing is, and the wagon-wheel analogy

A pixel is not a point; it is a little square of the screen. When a shader evaluates its function only at the pixel
centre and the function changes faster than one pixel (a hard edge, a stripe pattern finer than a pixel), the sampled
image lies. That lie is **aliasing**: stair-stepped edges ("jaggies"), crawling and shimmering edges in motion, and
**moiré** (big false patterns that appear when fine stripes are sampled too coarsely).

Analogy: a film camera filming a spinning wagon wheel shows it turning backwards, because it samples too slowly for the
spokes' speed. Audio engineers fix the same problem with an **anti-aliasing filter before the analogue-to-digital
converter**: remove frequencies above half the sample rate (the **Nyquist limit**) *before* sampling. Shaders do exactly
the same thing: average (filter) the function over the pixel's area, or remove detail finer than a pixel, before you
"sample" it.

### 4.2 Measuring the pixel: derivatives and `fwidth`

The GPU shades pixels in 2×2 quads and lets each pixel read its quad-neighbours' values of any expression:

- `dFdx(v)` is the change of v from this pixel to its horizontal neighbour; `dFdy(v)` likewise vertically.
- `fwidth(v)` is |dFdx(v)| + |dFdy(v)|.

So for any continuous quantity v, `fwidth(v)` (or better, the length of the pair (dFdx, dFdy)) tells you *how much v
changes across one pixel*: exactly the filter width you need. These are nearly free (the quad hardware is computing all
four pixels in lock-step anyway; Fabrice Neyret's "Usual tricks" notes the same).

What the experts know about them:

1. **They are coarse.** The difference is taken within the 2×2 block, so the resolution of a derivative is two pixels, and
   on many GPUs one derivative value is shared by a whole quad row or column. A sudden jump *inside* a quad poisons all four
   pixels: that is the source of 2-pixel-wide artefact lines.
2. **`fwidth` is the L1 norm, not the Euclidean length.** On a diagonal gradient it overestimates the true per-pixel
   change by up to √2 (about 41%). Lines drawn with `fwidth` therefore get thicker where the field slopes diagonally.
   Sébastien Durand's isoline study in the corpus says so in a comment and switches to the Euclidean length of the
   derivative pair for "nice result" (`Ms2XWc/image.glsl:6-7, 73-82`).
3. **Derivatives of discontinuous values are garbage.** The derivative of a cell id, of `fract(x)` at its wrap, of
   `floor(x)`, or of `atan(y, x)` at its ±π seam is a huge spike exactly at the discontinuity. The house already learned this
   the hard way: shader-craft floor 6 says *derivatives only on continuous values; fwidth of a cell id shreds whole rows; a
   tiling's edge width comes from the length of fwidth of the surface position*. The rule generalises: **take derivatives of
   the coordinate before you fold, tile or wrap it**, and carry that width through.
4. **Derivatives are undefined inside divergent control flow.** If some pixels of a quad take an `if` branch and others do
   not, a derivative computed inside that branch reads neighbours that never computed it. Compute footprints at the top of
   the shader, outside branches and early-outs.
5. **They are free only once.** Taking `fwidth` of an expression is cheap; recomputing an expensive function at an offset
   (finite differences) to get a gradient costs one extra evaluation per direction.

### 4.3 Coverage from a distance: the one-line antialiased edge

Given a signed distance d (negative inside) and the pixel size w in the same units, the fraction of the pixel covered by
the shape, for a straight edge under a box filter one pixel wide, is approximately

    coverage = clamp(0.5 − d / w, 0, 1).

This is the *linear step* from section 2, centred on the edge and one pixel wide. It is the right default. Fabrice Neyret
puts it simply: antialiasing is "easy in 2D shaders, as long as you can express shapes as distances" (Shadertoy
Unofficial, "Advanced tricks").

Variants and their trade-offs:

- **smoothstep(−w, w, −d)** gives a softer, two-pixel ramp. It hides jaggies more but blurs. Many shaders use it; it is a
  taste choice, not a correctness one.
- **Exact disk coverage.** Treating the pixel as a disk, the covered fraction of a straight edge has a closed form (the SDF
  lane provides `aaDiskCoverage`). It is the most accurate single-sample answer.
- **Blend in linear light.** Coverage is a fraction of *light*, so mix colours by coverage in linear RGB and encode to sRGB
  once at the end (the colour lane's `srgb_encode`). Mixing in the encoded space makes light-on-dark edges look too thin and
  dark-on-light edges too bold.

### 4.4 Making non-distance fields antialiasable: divide by the gradient

Many beautiful fields are not distances: implicit curves like sin(x)·cos(y) = 0.3, noise contours, polynomial curves. Their
value changes at different rates in different places, so a fixed threshold draws lines that are thin where the field is
steep and fat where it is flat. Inigo Quilez's fix (iquilezles.org/articles/distance): near the zero set, the first-order
Taylor expansion says

    distance ≈ |f(p)| / |∇f(p)|

(the value divided by the length of its gradient). Divide by the gradient and you have something in distance units again,
which section 4.3 can antialias at constant pixel width. The gradient can be analytic (best), finite differences (four
extra evaluations in 2D), or `dFdx`/`dFdy` of f (cheapest; the result is already in per-pixel units, so f divided by the
length of its screen derivative is directly "distance in pixels"). It fails far from the curve and where the gradient
vanishes (saddles), so clamp it.

### 4.5 Thin lines: never go below a pixel; fade instead

A line thinner than a pixel cannot be drawn honestly by a coverage ramp: it breaks into disconnected dots that flicker.
Emil Persson's **phone-wire antialiasing** (Avalanche Studios, "Graphics Gems for Games", Humus) solves it for 3D wires in
one sentence of logic: *clamp the drawn width to at least one pixel, and reduce the opacity by the ratio of true width to
drawn width*. A wire that should be a quarter-pixel wide is drawn one pixel wide at 25% opacity. On screen the energy is
right and the line stays connected. The same rule is essential for 2D grids, isolines and Truchet strokes.

Ben Golus's **"pristine grid"** ("The Best Darn Grid Shader (Yet)", 2023; the article refuses automated fetch, so this
summary is from his published gist and the widely-cited article) is the most complete treatment of procedural lines:

- measure the footprint *per axis* as the length of that coordinate's screen derivative pair (not `fwidth`);
- clamp the draw width between that footprint and half a cell, antialias over about one and a half footprints, and fade by
  target ÷ drawn width (phone-wire);
- for lines wider than half a cell, draw the *inverse* pattern and invert back, so wide lines stay correct;
- as the cells approach one pixel, **blend the result toward the pattern's average value** (for lines of relative width t,
  the average is t), which is what a correctly mip-mapped texture would do and is what kills moiré;
- combine the two axes as a union of coverages, not a sum.

### 4.6 Filter the whole pattern analytically when you can

For periodic patterns, you can often integrate the pattern over the pixel footprint in closed form. Inigo Quilez's
"filterable procedurals" and "checker filtering" articles show the method on checkerboards and grids:

1. Write the checker as the product of two square waves (each ±1, period 2).
2. The integral of a square wave is a **triangle wave** (accumulating +1 then −1 makes a ramp up then down).
3. A box filter of width w is "integral at the right edge minus integral at the left edge, divided by w".
4. Multiply the two filtered axes and remap from ±1 to 0..1.

The filter width comes from the derivatives of the *continuous* pattern coordinate. The result has no aliasing at any
distance and costs a few operations.

**Band-limiting** (iquilezles.org/articles/bandlimiting) is the same idea for waves: the average of cos(x) over an interval
of width w is cos(x) multiplied by sin(w/2)/(w/2) (a "sinc"). In practice: fade each cosine (or each noise octave) toward
zero once its period approaches the pixel footprint. The noise lane's `fbm_aa` does this per octave; this report adds the
same treatment for cosine palettes and stripe patterns (`aaCos`, section 16).

### 4.7 The seams: atan, fract and cell ids

The three classic seam bugs, and the fix for each:

- **The atan seam.** atan(y, x) jumps from +π to −π on the negative x-axis. Anything derived from it by `fwidth` (or a
  texture lookup using it, whose automatic level of detail comes from derivatives) shows a one- or two-pixel line along that
  axis. Fix: the angle's true footprint is simply the pixel size divided by the radius (an arc of length w at radius r spans
  w/r radians). Compute that analytically and never call `fwidth` on the angle. (`aaAngleFootprint`, section 16.)
- **The fract seam.** Same story at every tile boundary: `fract` wraps, derivatives spike, textures sampled with the wrapped
  coordinate pick the blurriest mip level along the seam. Fix: compute derivatives of the coordinate *before* `fract`, and
  pass them explicitly (texture gradient lookup) or use them as the AA width.
- **The cell-id seam.** Any value that is constant per cell and jumps between cells (an id, a random colour, a per-cell
  rotation) must never be differentiated. House floor 6 again.

### 4.8 When analytic AA is impossible: supersample, but adaptively

Some fields have no useful distance (chaotic fractal colourings, Xor-style glows, domain-warped noise mixed with hard
thresholds). Then the last resort is **supersampling**: evaluate k×k sub-pixel positions and average. It costs k² times
as much. Fabrice Neyret's "Advanced tricks" suggests the expert version: supersample only where it is needed, using
`fwidth` *of the output colour* as the detector (big neighbour differences mean an edge or detail worth more samples).
Temporal accumulation (jitter the sample inside the pixel each frame and blend frames) spreads the cost over time but is a
feedback effect, so a reproducible still needs cleared history and a fixed settle (house floor 8).

### 4.9 Fractals antialias through their distance estimate

Escape-time fractals (section 9) and folding fractals (section 10) can return a **distance estimate**. Once you have it,
fractal boundaries antialias exactly like circles (section 4.3). This is the single biggest quality jump between amateur and
expert fractal shaders: the amateur supersamples a noisy boundary; the expert shades a distance.

---

## 5. Polar coordinates, kaleidoscopes and symmetry

### 5.1 Polar coordinates

Radius r = |p| and angle θ = atan(p.y, p.x), in (−π, π]. In these coordinates:

- concentric rings are functions of r alone;
- rays and fans are functions of θ alone;
- **polar shapes** are "r less than some function of θ": r < a + b·cos(nθ) is a flower with n petals (The Book of Shaders,
  chapter 7); |cos(nθ/2)| gives sharper petals; smoothstep around the boundary gives soft edges (but measure AA width as
  explained in 4.4 and 4.7, because a polar boundary is not a distance);
- an **Archimedean spiral** is r − (k·θ / 2π) taken modulo the spacing k; a **logarithmic spiral** is the same in ln r.

Common mistakes: forgetting the order of atan's arguments (y first, then x); dividing by zero at the centre; drawing
angular stripes with a fixed width (they get thinner near the centre; their pixel width is r times the angular width).

### 5.2 Angular repetition and the kaleidoscope

**Repetition by angle.** Divide the circle into N sectors of angle s = 2π/N. Shift θ by half a sector, take it modulo s,
shift back, and every sector now holds a copy of whatever was drawn in the first one. The sector index (floor of the shifted
angle divided by s) is the **sector id**: keep it, because it is what lets each copy differ.

**Kaleidoscope (mirrored repetition).** After folding into a sector, take the absolute value of the angle relative to the
sector's centre line. Adjacent sectors are now mirror images, so content touching a sector edge meets its own reflection:
there is never a cut seam in the *value*. The house `kaleido` chunk does exactly this (`design/vfx-chunks/kaleido.glsl`)
but throws the sector id away.

**The crease, and how mrange removes it.** A mirror makes a crease: the value is continuous across the sector edge, but its
slope flips, so lit or antialiased content shows a hairline along every mirror. Mårten Rånge (mrange) in his CC0 shader
"Truchet + Kaleidoscope FTW" replaces the absolute value on the angle with a **smooth absolute value** (a polynomial
smooth max of a and −a), so the mirror is rounded within a chosen angular radius (`7lKSWW/image.glsl:83-97`, using the
hg_sdf mirror-repeat helper at `:75-81`). That is the professional kaleidoscope: `domKaleidoSoft` in section 16.

**Reflection folds (the general mirror).** Any mirror line through the origin with unit normal n: if the point is on the
negative side (its dot product with n is negative), subtract twice that dot product times n. Chaining several folds with
different normals builds any **dihedral symmetry** (the symmetry of a regular polygon) and, with translations and scaling
added, all the folding fractals in section 10. This "fold" is the atom of the whole field.

**Mercury's hg_sdf** (mercury.sexy/hg_sdf; MIT or CC BY-NC 4.0 at the user's choice since 2021) established the convention
the house adopts: domain operators modify the point in place and *return the cell or sector index*. Its polar repetition,
mirror, mirrored-repeat and octant-mirror operators are the cleanest published reference.

**Correctness caveat.** Inigo Quilez's domain-repetition article (iquilezles.org/articles/sdfrepetition) points out that
angular repetition, like grid repetition, is only exact if the copied content stays inside its sector and is symmetric;
otherwise the nearest copy may live in the neighbouring sector, and you must evaluate both the current and the adjacent
sector and take the minimum (two evaluations). The SDF lane's `domPolarCandidate` implements that.

### 5.3 Log-polar space and the Droste spiral

Map a point to (ln r, θ): the **log-polar** or complex-logarithm map. Its magic: *scaling the image becomes translation*
along the ln r axis, and rotation becomes translation along θ. Consequences:

- An infinitely self-similar zoom (a picture inside itself, the **Droste effect**) becomes a simple periodic tiling in
  log-polar space: take ln r modulo the log of the scale ratio.
- Bart de Smit and Hendrik Lenstra explained M. C. Escher's *Print Gallery* as exactly this: in log space, rotate and scale
  the tiling by a complex factor so that one full turn of the angle lands on the next scale level, then map back with the
  complex exponential. The result is Escher's twisted, spiralling zoom. Reinder Nijhoff's WebGL write-up implements it per
  pixel. In formula terms: the twist angle α satisfies tan α = ln(ratio)/(2π), and the log-space coordinate is multiplied by
  the complex number cos α · e^(iα) before exponentiating.
- Infinite-zoom animations ("tunnels" made of rings, spirals that never end) are translations in log-polar space.

Antialiasing caution: the pixel footprint in log-polar space is (pixel size)/r in both axes, so detail near the centre
becomes sub-pixel very fast; fade it (section 4.6) or the centre turns to noise.

### 5.4 Wallpaper groups and Wythoff (where to go next)

There are exactly 17 symmetry groups of the repeating plane (wallpaper groups) and each can be built from translations,
rotations, mirrors and glide reflections, i.e. from the folds above plus `fract`. The **Wythoff construction** builds
uniform tilings and polyhedra by folding into a triangle bounded by three mirrors and placing one generating point inside it.
Matt Zucker (mattz) built an interactive Wythoff explorer in the corpus (`Md3yRB`, header at `image.glsl:1-42`, crediting
knighty's polyhedra and gaz's 2D folding); it is the best worked study of fold-based symmetry.

---

## 6. Tiling, grids and lattices

### 6.1 Square grids

`fract(p·n)` repeats space n times; `floor(p·n)` is the cell id (The Book of Shaders, chapter 9). The cleaner, centred
form: subtract the *rounded* coordinate, so the local coordinate runs from −½ to +½ with the origin at the cell centre and
the id is the rounded value. Every shape drawn around the origin now appears in every cell, for the cost of one.

Classic variants:

- **Brick offset:** shift every other row by half a cell (detect odd rows with the cell id's parity).
- **Mirrored repetition:** flip the local coordinate in odd cells so neighbours meet as reflections. This is the trick that
  keeps an asymmetric shape *exact* with a single evaluation (iq's repetition article).
- **Limited repetition:** clamp the id to a range so you get exactly 5×4 windows instead of infinitely many (iq).
- **Per-cell transforms:** rotate, scale or recolour each cell by a random number derived from its id (The Book of
  Shaders' matrix chapter applies this inside cells).

**The neighbour problem (the most important correctness lesson in tiling).** Naive repetition evaluates only the cell the
pixel is in. If the shape in the neighbouring cell is bigger, rotated, offset or randomised, its edge may reach into this
cell, and the naive version cuts it off with a straight line at the cell border. Inigo Quilez's fix: evaluate this cell and
the neighbours on the side of the nearest boundary (2 cells in 1D, 4 in 2D, 8 in 3D) and take the minimum, at that
multiple of the cost. You can see BigWings doing exactly this in *Hexagone*, where hexagons of animated size overflow
their cells, so each layer is evaluated in the cell and all six neighbours (`wsl3WB/image.glsl:72-87`), and in *The
Universe Within*, where each cell's moving point is connected to the points of its 3×3 neighbourhood
(`lscczl/image.glsl:74-98`).

### 6.2 Per-cell randomness

Feed the cell id to a **hash** (a function that scrambles its input into an unpredictable-looking number). The old
Shadertoy idiom fract(sin(dot(id, k))·43758.5453) has two problems the house must avoid: it depends on how precisely each
GPU vendor computes sin of large numbers (so AMD and NVIDIA draw *different* patterns), and it degrades into visible
stripes and repeats for large ids. Mark Jarzynski and Marc Olano's "Hash Functions for GPU Rendering" (JCGT 2020)
measured the alternatives; integer hashes like PCG are both stable and fast. The noise lane already defines the house
hashes (`pcg2d`, `u01`, `hash33`); patterns here should call those. Dave Hoskins' MIT "Hash without Sine" (`4djSRW`) is
the corpus reference for float-only hashing.

### 6.3 Truchet tiles

**History.** Sébastien Truchet (1704) studied square tiles split diagonally into two colours and the patterns their
rotations make. Cyril Stanley Smith (1987) replaced the diagonal with **two quarter-circle arcs** centred on opposite
corners; tiles placed with random orientation join into continuous meandering curves, and the regions between them can be
two-coloured. The "10 PRINT" maze (a random choice of / or \ per cell) is the same idea with diagonals.

**The shader recipe (Smith tiles), in my words:**

1. Centred cell coordinate q in [−½, ½]², cell id from section 6.1.
2. One random bit per cell: if set, flip q horizontally. (This rotates the tile by 90°, since the tile is symmetric.)
3. The two arcs have radius ½ and are centred on the corners (½, ½) and (−½, −½). The nearer arc is the one whose corner
   lies on the same side of the anti-diagonal as q: pick the corner by the sign of q.x + q.y. (Checked numerically: this
   one-corner choice equals the minimum over both arcs at every point.)
4. Distance to the curve = | distance from q to that corner − ½ |. Draw a band of any width around zero (section 4.3).
5. **Path parameter.** The angle of q around the chosen corner, normalised over the quarter turn, runs 0..1 along the arc.
   Use it to texture the curve (scales, arrows, dashes).
6. **Flow direction.** For anything that moves along the curve, the direction must agree across tile borders. Multiply the
   path parameter's direction by the cell's checkerboard parity (+1 or −1 by whether the id's coordinates sum to even or
   odd) and by the flip bit. Martijn Steinrucken's Art of Code video "Truchet Tiling Explained" builds exactly this,
   ending with animated vines.

**Hexagonal Truchet.** On a hex grid, put three arcs per tile centred on alternate vertices (or connect edge midpoints with
arcs and lines), and randomly rotate or flip each tile. Shane's raymarched hexagonal Truchet (`4td3zj/image.glsl:32-72`)
uses the distance to the three relevant corners after a random flip and then "wraps" the height values (abs, cos of the
distance) to get banded ribbons; he credits Fabrice Neyret's and mattz's earlier versions.

**Weaves.** Two crossing families of strands with over/under decided by parity give woven Truchets; the parity trick is the
same as for flow direction.

**Multi-scale Truchet (Christopher Carlson, Bridges 2018).** Carlson generalised Smith's tiles to a family that can be
subdivided into four half-size tiles, recursively, while the curves still connect. The key idea is the **winged tile**: each
tile's motif extends small "wings" past its square at the connection points, and colours **invert at each level** of
subdivision; overlaid on their parent, the smaller tiles' wings hide the parent's motif exactly where they should. In a
shader: at each level decide by a hash whether this quad-tree cell subdivides; keep going to a fixed maximum depth (constant
loop bound, house floor 6); the deepest chosen level's tile is drawn, with the colour sign flipped once per level.

**Cost.** One cell, one hash, one or two distances: tens of operations. The neighbour problem does not arise as long as the
band stays inside the tile (arcs of radius ½ with a band narrower than the cell meet the borders cleanly).

### 6.4 Hexagonal grids

**Geometry first.** A regular hexagon with **inradius** a (centre to edge midpoint) has **circumradius** (centre to vertex)
2a/√3. Pack them pointy-top with centres one unit apart horizontally (a = ½); the next row sits ½ to the right and √3/2 up.
Amit Patel's Red Blob Games hexagon guide is the definitive reference for orientations, sizes and coordinate systems.

**Method A: two rectangular grids (BigWings / Shane).** The hex centres form two interleaved rectangular grids, each with
cell size (1, √3): one with centres at the cell centres, one shifted by half a cell in both directions. For each pixel:
find the nearest centre in each rectangular grid (centred repetition, section 6.1), keep the nearer of the two. The kept
offset is the local hex coordinate; position minus offset is the hex centre, a unique id. Verified numerically: identical to
brute-force nearest lattice point. BigWings' `HexCoords` (`wsl3WB/image.glsl:16-33`) is this method; his video "Hexagonal
Tiling Explained" teaches it. Cost: two centred repetitions and two dot products.

**Method B: skewed triangle lattice (Inigo Quilez, "Hexagons - distance").** Shear the plane so the hex lattice's
triangular sub-lattice becomes a square grid; split each square cell into two triangles by comparing the fractional
coordinates; each triangle belongs to one of three hexagons, decided by (i + j) mod 3. It is branch-free and yields the
distance to the hex border directly (`Xd2GR3/image.glsl:16-37`; note that file carries iq's restrictive notice, see
section 15).

**Method C: axial/cube rounding (Red Blob Games).** Multiply by the inverse of the hex basis matrix to get fractional axial
coordinates (q, r), set s = −q − r, round all three, then fix the one with the largest rounding error so q + r + s = 0 holds.
You get *integer* hex coordinates, which is what you need for neighbour arithmetic: the six neighbours are fixed offsets;
the hex distance between two cells is the largest of the three absolute coordinate differences; a ring of radius N has 6N
cells; rotating by 60° cycles the coordinates with a sign flip.

**Distance to the hex border.** With local offset q from the centre (pointy-top, inradius ½): the hex "norm" is
max(|q.x|, ½|q.x| + (√3/2)|q.y|). It is ½ on the border and 0 at the centre; border distance is ½ minus it. This norm also
gives **hex rings** (concentric hexagons) and is the hex analogue of the radius in polar coordinates; the angle of q gives
radial effects inside each hex.

**Triangle and other grids.** Equilateral triangle cells come from the same shear as Method B (each sheared square holds an
up and a down triangle; barycentric coordinates give edge distances directly). Shane's "Triangle Grid Contouring"
(`WtfGDX`) and bitless's "Cyberspace data warehouse" (`NlK3Wt`) are worked studies. Voronoi cells (jittered grids) belong to
the noise lane (`cell_f1f2`, `cell_edge`).

### 6.5 Infinite-zoom layering

The Universe Within (BigWings, `lscczl/image.glsl:126-140`) shows the standard way to make any tiled pattern zoom forever:
draw N copies at scales that grow exponentially with a per-layer depth z = fract(time + i/N); fade each layer in as z
leaves 0 and out as it approaches 1 (two smoothsteps). Because the layer that grows too big fades out exactly as a new small
one fades in, the zoom never ends and never pops. Combine with log-polar space (5.3) for spiral zooms.

---

## 7. Isolines and contour art

An **isoline** (contour line) is the set of points where a scalar field f equals some level. Topographic maps draw them every
Δ metres. In a shader:

1. Divide the field by the spacing: v = f/Δ. Levels are now at whole numbers.
2. Distance to the nearest level, in level units: |v − round(v)|.
3. Convert to pixels by dividing by the per-pixel change of v: the Euclidean length of its screen derivative pair (or an
   analytic gradient times the pixel size). This is section 4.4 applied to a periodic field.
4. Draw a band of the desired pixel width with the coverage ramp (4.3), clamping to one pixel and fading by ratio (4.5).
5. Where the lines are denser than about three pixels apart (the per-pixel change of v exceeds about ⅓), fade the lines
   toward their average coverage, or the map turns into moiré (4.5, Golus).
6. Major lines every m levels: repeat with v/m and a wider band.

Sine trick (Fabrice Neyret, `ldfczS/buf_a.glsl:24-31`): take v = sin(2π·k·n) of a noise value n; its zeros are the
isolines, and |v| divided by its own `fwidth` is a pixel distance, so a single smoothstep draws antialiased contours. It
inherits the √2 diagonal thickening of `fwidth` and doubles the line count (sin has two zeros per period); both are often
fine for art.

**Isolines of an SDF** are the expert's debug view (and an art style in their own right): draw bands of the distance every
Δ, colour inside and outside differently, and you can *see* whether a distance function is exact (bands evenly spaced and
parallel), a bound (bands squeezed), or broken (bands torn). The SDF lane's `dbgSlice` is this view.

**Common mistake.** Taking `fwidth` of an already-folded value (|v − round(v)|) instead of v: the fold creates a kink at
every half-level, and the width spikes there. Always differentiate the smooth field, then fold.

---

## 8. SDF text and glyphs

Text inside shaders comes in four grades, cheapest first.

**8.1 Procedural glyphs.** Digits and simple letters built from SDF primitives: a seven-segment display is seven capsules
switched on by a bit mask per digit; a 3×5 pixel font can be packed as 15 bits per glyph and looked up by cell (draw each
"on" bit as a rounded square). Strokes for real letterforms can be drawn as distances to line segments and **quadratic
Bézier curves** (iq gives an exact distance to a quadratic Bézier, which needs the roots of a cubic). These are
resolution-independent and need no textures; they are what the house should use for numeric readouts on the VFX bench.

**8.2 Single-channel SDF atlases (Chris Green, Valve, SIGGRAPH 2007).** The paper that made SDF text standard in games
(Team Fortress 2). The method, summarised from the paper:

- Rasterise each glyph at very high resolution (4096² in the paper) as in/out.
- For each texel of a *small* output texture (64² can suffice), search a limited neighbourhood for the nearest texel of the
  opposite state; that signed distance, scaled by a chosen **spread** and remapped so 0.5 is the edge, is stored in one 8-bit
  channel.
- Render with a threshold at 0.5. Bilinear filtering of a distance reconstructs straight edges far better than filtering
  coverage, so magnified glyphs stay crisp.
- With a shader: a smoothstep across the threshold whose width comes from screen derivatives gives antialiasing; a second
  threshold band gives an **outline**; a soft ramp outside gives a **glow**; a second lookup at an offset gives a **drop
  shadow**; all dynamically adjustable.
- Limitation: corners round off as resolution drops. The paper's remedy is to store two edges in two channels and combine
  them (AND), which foreshadows MSDF.

**Shadertoy's built-in font texture** is such an atlas: 1024² pixels, 16×16 glyphs indexed by character code, the
distance in the alpha channel with a bias of 127/255 representing zero (mattz documents this layout in
`XsVcDy/image.glsl:27-60`, and notes he could not get glyph edges cleanly antialiased, so he blurs the distance with a 3×3
Gaussian). The house's own atlas should not reuse Shadertoy's texture.

**8.3 Multi-channel SDF (MSDF, Viktor Chlumský, 2014 thesis; "Improved Corners with Multi-Channel Signed Distance Fields",
2018).** Three distance fields, each responsible for different edges, stored in RGB. The shader takes the **median** of the
three channels; that median reproduces sharp corners almost perfectly at the same resolution. Antialiasing uses the
**screen pixel range**: how many screen pixels one unit of stored distance spans, computed from the atlas size, the
generator's pixel range and the screen derivatives of the texture coordinate, clamped to at least 1. Then the coverage is
the median distance times that range, plus ½, clamped. The generator, `msdfgen` and `msdf-atlas-gen`, is MIT-licensed.
Amit Patel's 2026 Red Blob Games guide to SDF and MSDF fonts is the practical companion: distance range of about ±5% of the
em as a starting point, MSDF for the text layer, plain SDF (or the alpha channel of an MTSDF, which stores a true SDF
alongside the three channels) for glows and shadows, two passes when glows overlap neighbouring letters, and the warning
that every font and size combination must be tested.

**8.4 Exact vector coverage.** Will Dobbie's "GPU text rendering with vector textures" stores the glyph's quadratic Bézier
curves in a texture with a per-glyph grid of which curves cross each cell, and computes coverage per pixel by integrating
along rays (adding at entries, subtracting at exits). Sharp at every scale, more work per pixel. Commercial libraries
(for example Eric Lengyel's Slug) are the industrial version.

**Recommendation for the house:** MSDF atlas generated offline with `msdfgen` for any real text; procedural seven-segment
and segment glyphs for digits and diagrams; one shared `txt…` module so a single change to the AA or outline style updates
every surface that prints text.

---

## 9. Escape-time fractals: Mandelbrot, Julia and their colourings

### 9.1 The iteration and complex numbers as rotations

A complex number is a 2D vector (x, y) with a multiplication rule: multiplying by a complex number w *rotates by w's angle
and scales by w's length*. Written as a matrix, multiplication by w = (a, b) is the 2×2 matrix [[a, −b], [b, a]]; Shane's
Mandelbrot shader uses that form for the derivative update (`ttscWn/image.glsl:98`). Squaring a complex number doubles its
angle and squares its length.

- **Mandelbrot set:** for each pixel c, start at z = 0 and iterate z ← z² + c. If |z| stays bounded, c is in the set.
- **Julia set** for a fixed parameter c: start at z = the pixel and iterate the same map.
- Once |z| exceeds 2 the orbit is guaranteed to escape; iterating until |z|² > 4 ("bailout") and counting iterations is the
  classic **escape-time** picture.

Cheap interior tests (from the Wikipedia "Plotting algorithms" survey): a point is inside the main cardioid when, with
q = (x − ¼)² + y², q·(q + x − ¼) ≤ y²/4; it is inside the period-2 bulb when (x + 1)² + y² ≤ 1/16. Skipping those saves
the most expensive pixels (the ones that never escape) but only helps if *whole groups of pixels* skip: GPUs run pixels
in groups of 32 or 64 (wavefronts), and a group runs until its slowest member finishes. Fractal cost is set by the
boundary pixels in each group, like a convoy moving at its slowest truck.

### 9.2 Smooth iteration count (no bands)

Counting whole iterations gives flat colour bands. The **continuous** or **smooth iteration count** (iq's "msetsmooth";
also the Wikipedia survey) measures *how far past the bailout* the orbit went. Derivation in words:

- Far from the origin the "+ c" is negligible, so |z_{n+1}| ≈ |z_n|^d (d = 2 for the Mandelbrot set). Taking logs twice,
  log_d(log|z_n|) grows by exactly 1 per iteration.
- So the quantity μ = n − log_d( ln|z_n| / ln B ) (with B the bailout radius) is continuous across band boundaries: as a
  pixel needs one more iteration, the log-log term rises by one to compensate.
- With |z|² instead of |z| and base-2 logs, the formula becomes n − log₂(log₂|z|²) plus a constant, which iq writes in one
  line. Constants only shift the palette.
- **Use a large bailout** (hundreds or more; iq uses very large values for distance estimation). The approximation "z^d
  dominates" is poor near |z| = 2, and a small bailout leaves faint ripples at the old band edges.

### 9.3 Distance estimation

Track the derivative of the orbit with respect to the pixel: for the Mandelbrot set dz ← 2·z·dz + 1 starting from 0; for a
Julia set dz ← 2·z·dz starting from 1 (for degree p, replace 2z by p·z^(p−1)). At escape, the estimate is

    d ≈ |z| · ln|z| / |dz|.

Why: the **Hubbard–Douady potential** G = lim ln|z_n|/2ⁿ is a smooth function that is 0 on the set; dividing G by the
length of its gradient (section 4.4) gives a distance; working through the limit gives the formula. Koebe's ¼ theorem
brackets the true distance between half and twice this estimate (Wikipedia gives the bound form), so use **half of it**
whenever you step or march by it (never overshoot), and the full value for colouring. Inigo Quilez's "distancefractals"
article derives and tests it (and finds the more elaborate textbook formula loses precision near the boundary), and notes
that only |dz|² is needed for Julia sets, saving square roots. With d in pixel units (divide by the pixel size), the
boundary antialiases like any SDF (4.3), and thin filaments become visible at any zoom, which iteration counts alone never
achieve.

### 9.4 Orbit traps

Instead of *when* the orbit escaped, colour by *where it went*. Keep the minimum distance from every orbit point z_n to a
chosen shape, the **trap** (iq, "ftrapsgeometric"):

- **Point trap:** distance to a fixed point. Bubbles that follow the fractal's structure.
- **Line traps:** distance to the x-axis, the y-axis, or any line. Filaments and crosses.
- **Circle or ring traps:** | |z − c| − r |. Rings threading through the set.
- Any 2D SDF can be a trap (stars, boxes); **bitmap traps** sample a picture at the orbit points and stop at the first
  opaque hit (iq's 2002 competition image used a drawing of a bunny).
- Statistics other than the minimum (average, standard deviation) and multiple traps mixed with different palettes give
  the layered look of high-end fractal art.

Carrying a vec4 of four trap minima (point, x-line, y-line, circle) through the loop is the efficient habit; iq colours his
Mandelbulb with four such traps.

**Decorating in escaped space (Shane, `ttscWn`).** After the loop, the final z is a coordinate system that the fractal has
wrapped around itself. Draw an ordinary repeating pattern (circles, grid lines) in *that* space, and antialias it with a
width scaled by the derivative magnitude (the local stretch of the map; `ttscWn/image.glsl:136-157`). The general principle
behind it is worth memorising: **after any transform q = F(p), the pixel footprint in q is the pixel size times the local
stretch of F**; for complex-analytic maps that stretch is simply |dz|.

### 9.5 Palettes

The cosine palette colour(t) = a + b·cos(2π(c·t + d)) (iq, "palettes") is the workhorse: a is the mean colour, b the
contrast, c the frequency per channel, d the phase per channel. Integer c makes it cyclic, which suits iteration counts. It
returns display-referred values as tuned on screen (the colour lane's `pal_cos`). Fed with a smooth iteration count, a
distance, or a trap value, it gives most of the classic looks. Band-limit it when t changes faster than a pixel (4.6).

### 9.6 Precision: why deep zooms go blocky

A 32-bit float has 24 bits of mantissa: around |c| ≈ 1, neighbouring representable numbers are about 1.2·10⁻⁷ apart. With
1080 pixel rows, pixels stop being distinguishable once the view is about 10⁻⁴ high (checked: 2⁻²³ × 1080 ≈ 1.3·10⁻⁴),
i.e. a zoom of roughly ten thousand times from the full set. Beyond that the image breaks into blocks. Doubles buy roughly
another 10⁸ but are slow or absent in WebGL. Deep-zoom software uses **perturbation**: compute one reference orbit in high
precision on the CPU, then iterate only each pixel's small *difference* from it in ordinary floats; a power-series
approximation skips the early iterations (popularised by K. I. Martin's SuperFractalThing, 2013). For the house: shallow
zooms on the GPU, deep zooms are a CPU-reference-plus-GPU-delta design, not a shader tweak.

---

## 10. Folding fractals: IFS, KIFS, Kaliset, inversion, Apollonian, Mandelbox, Mandelbulb

These are the fractals of the demoscene and of Shadertoy's most-loved 3D work. They all share one loop shape:

    repeat N times:  fold space (abs, mirrors, inversions)  →  maybe rotate  →  scale and shift
    then:            measure distance to a simple shape, divide by the accumulated scale.

### 10.1 Why "divide by the accumulated scale" works

Folds (reflections), rotations and translations are **isometries**: they do not change distances (piecewise). Scaling by s
multiplies all distances by s. After n iterations the point lives in a space magnified sⁿ times, so a distance measured
there must be divided by sⁿ to be a distance in the original space. That single fact turns an **iterated function system
(IFS)** (a shape defined as the union of shrunken copies of itself, classically drawn by the "chaos game" on a CPU) into a
per-pixel distance estimate the GPU can draw or raymarch. Mikael Hvidtfeldt Christensen's (Syntopia) series "Distance
Estimated 3D Fractals" (2011, parts I–VIII; the blog currently fails TLS for automated fetch) is the canonical explanation;
part III, "Folding Space", builds the Sierpinski tetrahedron and Menger sponge from folds this way.

When the transform is *not* a uniform scale (a sphere inversion, a non-uniform stretch, a twist), you must track the local
stretch as a running derivative (the Mandelbox does this) and divide by that instead; if you cannot bound it, step by a
fraction (0.5–0.8) of the estimate when raymarching, or the march overshoots and you see holes and onion-skin layers.

### 10.2 2D KIFS: Sierpinski and Koch

**Sierpinski triangle.** Fold across the triangle's three symmetry lines, then scale by 2 about a vertex; repeat; distance
to a point (or small triangle) divided by 2ⁿ.

**Koch snowflake** (Martijn Steinrucken's "KIFS Fractals explained!" video; the community gist of his shader is CC BY-NC-SA,
read for understanding only). In words: first mirror and fold the plane so that all three sides of the snowflake map onto
one 120° sector. Then each iteration: scale by 3, shift so the middle third is centred, fold x with abs (the two outer
thirds become one), and reflect across the line at 60° that forms the bump. After n iterations, the distance to a horizontal
segment divided by 3ⁿ is the distance to the snowflake's edge. The folded coordinate left over at the end is also a texture
coordinate that follows the curve, which his video uses to texture the edge.

**General 2D KIFS** (`fracKifs2` in section 16): abs-fold, rotate by an angle, scale by s about an offset point; with two or
three parameters animated you get the endlessly-morphing "kaleidoscopic IFS" look.

### 10.3 Knighty's KIFS in 3D

Knighty posted "Kaleidoscopic (escape time) IFS" on Fractal Forums on 1 May 2010. The transforms: plane reflections that
fold space into the fundamental region of a Platonic solid's symmetry group (tetrahedral folds like "if x + y < 0, swap and
negate x and y"; octahedral folds via abs and sorting the coordinates), a rotation before and/or after the folds, and the
scale-about-a-centre step

    p ← s·p − C·(s − 1)

which scales by s while keeping the point C fixed. Escape-time bailout as in the Mandelbrot set; distance estimate of the
form (|p| − k)·s^(−n). Inserting the rotations is what makes these fractals "kaleidoscopic". Syntopia's *Menger Journey*
(`Mdf3z7/pass.glsl:55-66`) is the Menger sponge as a KIFS: abs fold, sort coordinates, scale by 3 about (1, 1, 1)-ish
offsets, a conditional shift on z, and a running minimum of length times 3^(−n−1).

### 10.4 Kali's family: the Kaliset, Star Nest, Fractal Land, Inversion Machine

Pablo Román Andrioli (Kali) found an astonishingly productive one-liner on Fractal Forums:

    p ← |p| / |p|² − c

(absolute value per component, divided by the squared length, minus a constant). It is a fold (abs) followed by an
**inversion** (dividing by |p|² flips space inside-out through the unit sphere) and a shift. Iterated, it is chaotic and
discontinuous, which is exactly why it reads as stars, nebulae, circuitry and lace. Ways to see it (defgsus's "kaliset
explorer" catalogues them): colour by the final p, by the average of p, by min/max of |p|, or by the accumulated *change*
in |p| from step to step.

- **Star Nest** (Kali, MIT licence, `XlfGRj/image.glsl`) is the whole technique in 60 lines: a volumetric march of 20 steps
  through space folded into a repeating tile (`:45`), at each step 17 Kaliset iterations (`:48`) accumulating the absolute
  change in length (`:49`), cubed for contrast, faded with distance, with "dark matter" holes. Because it is MIT it is the
  one Kali shader the house may adapt with attribution, though the house rule still says rewrite rather than paste.
- **Fractal Land** ("Amazing Surface" formula, `XsBXWt/image.glsl:34-40`) uses Kali's version of the **box fold**:
  |x + 1| − |x − 1| − x, which equals the Mandelbox's clamp-based box fold exactly (checked numerically), then a shift,
  a rotation, and a combined inversion-and-scale with the squared length clamped to [0.2, 1].
- **The Inversion Machine** (`4dsGD7/image.glsl:15-26`) shows how to keep a distance honest through an inversion: invert
  (p/|p|² times a scale), build simple repeating geometry in the inverted space with sin, measure distance there, then
  **multiply by |p|²/scale**, the inverse of the inversion's local stretch.
- JoshP's *Simplicity* (`lslGWr/pass.glsl:2-16`) is the 2D-slice variant from the Fractal Forums thread "very simple formula
  for fractal patterns": weight each iteration's change in squared length with an exponential and accumulate.

### 10.5 Circle inversion and the Apollonian gasket

**Inversion** in a circle of centre c and radius R sends a point at distance ρ from c to the point on the same ray at
distance R²/ρ. It maps circles to circles (or lines), preserves angles (it is **conformal**), and its local stretch is
R²/ρ². Chaining inversions generates all **Möbius transformations**, which preserve tangency, which is why they generate
circle packings.

**The Apollonian gasket.** Start with three mutually tangent circles; in each curved triangular gap add the circle tangent to
all three; repeat forever. **Descartes' circle theorem** gives the new circle's curvature (curvature = 1/radius, negative for
an enclosing circle): k₄ = k₁ + k₂ + k₃ ± 2·√(k₁k₂ + k₂k₃ + k₃k₁). The **complex Descartes theorem** gives its centre the
same way with curvature-weighted complex centres. If four mutually tangent circles have integer curvatures, every circle in
the gasket does. Its fractal (Hausdorff) dimension is about 1.3057.

Two ways to draw it in a shader:

- **Explicit:** build the circle list on the CPU with Descartes (a few hundred circles) and pass it as uniforms or a data
  texture; per pixel, find the nearest circle. Exact and controllable, limited depth.
- **Inversion iteration (Kleinian style):** repeatedly invert the pixel into a fundamental region bounded by circles, multiply
  a running stretch by each inversion's R²/ρ², and stop when the point lands in the region; distance = distance to the region's
  boundary divided by the stretch. Infinite depth, per-pixel cost proportional to depth.

**The Shadertoy "Apollonian" recipe** (iq's *Apollonian*, `4ds3zn/image.glsl:31-51`; and mrange's CC0 *Apollian with a twist*,
`Wl3fzM/image.glsl:18-32`, and its sequel `7d2fDW`) is a 3D or 4D cousin: repeat space with period 2 into a cube centred on
the origin, invert through a sphere with strength s/|p|², multiply the running scale by the same factor, repeat about 7–8
times, and return a small multiple of |p.y| divided by the running scale. Repetition followed by inversion packs ever-smaller
spheres into each other. mrange draws a 2D slice of a 4D version and animates the slice, which is why his images look like
breathing gaskets. iq colours with orbit traps (`:43`).

### 10.6 The Mandelbox (Tom Lowe, 2010)

Tom Lowe ("Tglad") defined it on Fractal Forums in 2010 (his "What is a Mandelbox?" page states the rules). Per iteration:

1. **Box fold:** for each coordinate, if it exceeds +1 reflect it to 2 minus itself; if below −1 reflect it to −2 minus
   itself. (Equivalently: clamp to [−1, 1], double, subtract the original.)
2. **Ball (sphere) fold:** with r = |p|: if r is below a minimum radius m (typically 0.5), scale p by 1/m² (a fixed scale);
   else if r is below 1, invert (scale by 1/r²); else leave it.
3. **Scale and add:** p ← s·p + c, where c is the pixel's 3D position (the Mandelbrot-style version) or a constant (a Julia
   version). Standard s = 2; s = −1.5 is the other famous member.

For the distance estimate, carry a running derivative dr: the box fold leaves it alone, the ball fold multiplies it by the
same factor it applied to p, and the scale step makes dr ← |s|·dr + 1. The estimate is |p|/|dr|. A neat implementation trick
seen in Dave Hoskins' *Remnant X* (`4sjSW1/image.glsl:13-57`): carry the derivative as the fourth component of a vec4, so
every multiplication applied to p automatically applies to it, and make the ball fold branch-free by multiplying by
clamp(max(m²/r², m²), 0, 1) and folding the leftover factor 1/m² into the scale constant (fixed radius normalised to 1;
the three cases come out as ×1/m², ×1/r² and ×1, exactly the three rules above). Lowe describes the set as a "map of continuous, locally
shape preserving Julia sets".

### 10.7 The Mandelbulb (Daniel White, Paul Nylander, 2007–2009)

Daniel White's history page tells the story: Rudy Rucker imagined a 3D Mandelbrot around 1990; White published a
spherical-coordinate formula on Fractal Forums in November 2007; Paul Nylander proposed raising the power to 8, which
produced the first 3D shape with "buds on buds" at every scale; David Makin's deep zooms confirmed it.

The iteration ("triplex power"): write z in spherical coordinates (r, θ, φ); raise r to the power n and multiply both angles
by n; convert back and add c. For the distance estimate track dr ← n·r^(n−1)·dr + 1, and use 0.5·ln(r)·r/dr (the half
version of 9.3, safe for marching; the corpus's `MdXSWn/image.glsl:34-59` is a textbook instance). Inigo Quilez's Mandelbulb
article adds two expert moves: a trig-free polynomial form of the power-8 step via repeated double-angle identities (about
5× faster on CPU), and colouring by four orbit traps (origin plus the three coordinate planes).

### 10.8 Raymarching folding fractals safely (and cheaply)

- Step by the distance estimate times 0.5–0.9 when the map is not a uniform scale; check for holes with the SDF lane's
  diagnostics (gradient error, overshoot count).
- Scale the hit threshold with distance (a constant number of pixels) so far detail does not cost infinite steps.
- Bound the fractal with a sphere or box and intersect analytically before marching.
- Budget, roughly: 64–256 steps × 8–15 iterations × about 30 operations ≈ 15,000–100,000 operations per pixel. At 1080p
  (about two million pixels) that is 30–200 billion operations per frame; a mid-range GPU peaks around ten trillion per
  second, so 3–20 ms at perfect efficiency and realistically several times more. On this host (AMD display-driver crash
  history, shader-craft floor 4): small canvases, capped steps, never two GPU contexts.

---

## 11. Xor's tiny-code idioms, decoded

Xor (GM Shaders, mini.gmshaders.com; "Modeling the World in 280 Characters", Codrops, June 2025) writes complete
raymarched scenes in under 300 characters. Reading them is the fastest way to learn which ingredients carry the image.
Here is the grammar, with the house version of each idiom.

**11.1 The skeleton (seen in `3XXSWS`, `wXjSRt`, `WcKXDV`).**

- *Ray direction in one expression:* normalise (2·pixel − resolution, with the third component set to the canvas height or
  zero minus it). The vertical field of view comes out at 90° without any camera code.
- *The loop:* one variable z is the distance travelled along the ray; each step samples p = z·direction, distorts it,
  computes a step size d, and advances z by d.
- *Step size as a "hollow, porous" distance:* d = small constant + |some distance| / k. The absolute value makes the surface
  hollow so the ray passes *through* it, the small constant (Xor calls it passthrough) guarantees progress, and dividing by
  k (4–7) takes many small steps inside the volume. This is not sphere tracing any more; it is a **volume sampler** whose step
  density follows the shape (Xor, "Volumetric Raymarching").
- *Glow by division:* each step adds colour/d. Where the ray passes near the surface, d is small and the contribution
  large: that is the luminous halo. It is a cheap stand-in for emission in a medium.
- *Colour by phase-shifted cosines:* cos(something + vec4(a, b, c, 0)) + 1: a cosine palette (9.5) with the phases written
  as constants.
- *Tonemap with tanh:* the accumulated colour is huge; tanh(colour²/k) squashes it into 0..1 with a soft shoulder.

**11.2 Turbulence** (Xor, "Turbulence"): "shift the coordinates with a sine wave, rotate, scale, and repeat." In each
octave, displace p by sin(frequency·(rotated p) + time + octave phase)/frequency along a direction perpendicular to the wave;
multiply the frequency by about 1.4–2 per octave; rotate the wave direction each octave so the waves never align. 7–9
octaves look like fluid, flame or smoke for a few dozen operations, with no noise texture. *Accretion* (`WcKXDV:27-28`)
adds the raymarch step index into the phase, which reads as refraction.

**11.3 Golf substitutions** (Xor, "Code Golfing"): x − fract(x) for floor, dot(v, v) for squared length, implicit casts
(vec4(1)), loops whose header does the work, ternaries instead of if/else. And two approximations that matter:

- **The rotation constant.** A 2×2 rotation is written as the cosine of the angle plus the offset vector (0, 11, 33, 0),
  reshaped into a mat2. This works because 11 is
  within 0.0044 of 4π − π/2 and 33 within 0.0133 of 10π + π/2, so those cosines are ± sin(a) to within about a hundredth of a
  radian. Checked: the determinant stays within 0.9% of 1, so a single use is fine, but nine chained uses drift by about 8%
  in scale. The house library uses an exact rotation.
- **Sine instead of cosine with offsets, swizzled sines instead of noise.** Fine for art; know they are periodic.

**11.4 What golfed code gets away with that the house must not.**

- **Uninitialised variables.** `for(O*=i; i++<50.;)` relies on i starting at 0 and O being whatever the driver left. In GLSL
  ES 3.00 an uninitialised local has an *undefined* value; most drivers happen to zero it. The house initialises every
  variable.
- **tanh overflow.** A shader whose accumulated colour gets very large can produce NaN (not-a-number) from tanh on some
  drivers, which displays as black pixels. SnoopethDuckDuck's *Zippy Zaps* ships a "safe tanh" that clamps the input to
  ±40 before tanh, with a comment telling readers to use it if they see black artefacts (`XXyGzh/common.glsl:1-3`). In
  float32, tanh(10) is already 1 to eight decimal places, so clamping to ±15 loses nothing.
- **Cost.** A 50–100-step loop with an 8-octave turbulence inside is 400–800 sine evaluations per pixel, on the
  transcendental unit. Tiny code, large bill: on this host, render these small and below display resolution (they are soft
  fields, so undersampling the background is allowed by floor 4).
- **No antialiasing.** Glow fields are soft and forgive it; hard edges in golfed code alias.

**11.5 The gateway tiny shaders.** kishimisu's "Shader Art Coding Introduction" (`mtyGWy`, with a YouTube tutorial) is the
best first shader to study: repeat space with fract, measure distance to the cell centre, turn it into rings with sin,
invert into a glow with a small constant divided by the distance raised to a power, colour with a cosine palette, loop four
times at increasing scale and add. Danilo Guanabara's *Creation* (`XsXXDn`, from a 1k demo) does radial displacement and
the same 1/distance glow per colour channel in 15 lines.

---

## 12. The Art of Code (Martijn Steinrucken, "BigWings") as a curriculum

Martijn Steinrucken runs the Art of Code YouTube channel and posts as BigWIngs on Shadertoy. His videos are the best
structured path from zero to this report's level; the ones verified tonight:

| Video | What it teaches |
|---|---|
| Shadertoy for Absolute Beginners (multi-part; parts 2–4 at youtube.com/watch?v= GgGBR4z8C9o, bigjgiavOM0, jKuXA0trQPE) | uv coordinates, circles with distance, smoothstep edges, remapping, building a smiley from SDF pieces (corpus `lsXcWn`) |
| Truchet Tiling Explained (2R7h76GoIJM) | cells, random flips, arc distance, path coordinate, checkerboard flow direction |
| Hexagonal Tiling Explained (VmrIDyYiJBA) | the two-grid hex method, hex distance, hex coordinates for effects |
| Voronoi (l-07BXzNdPw) | jittered points, nearest-cell search (noise lane) |
| KIFS Fractals explained! (il_Qg9AqQkE) | the Koch snowflake as folds, scale and reflect (10.2) |
| Ray marching camera and shapes (PBxuVlp7nuM, Ff0jJyyiVyw) | the 3D bridge (SDF lane) |

His shaders in the corpus are worked examples of the method: *The Universe Within* (`lscczl`, jittered network plus
infinite-zoom layers), *Hexagone* (`wsl3WB`, hex cells plus neighbour evaluation), *Heartfelt* (`ltffzl`, rain on glass),
*The Drive Home* (`MdfBRX`), *Smiley Tutorial* (`lsXcWn`).

**The BigWings way, distilled** (worth adopting as house method):

1. Start from the centred, aspect-correct frame and draw *one* cell's content first.
2. While developing, **visualise the plumbing**: show the local coordinate as red/green, the cell id as a colour, and draw
   the cell borders. Most bugs are visible immediately.
3. Name every magic number (`S()` for smoothstep, a remap helper), so parameters become controls.
4. When content crosses cell borders, loop over neighbours.
5. Build by layers (the seven layers of section 0), one idea per step.

---

## 13. Common mistakes, and how to see them on screen

| What you see | Cause | Fix |
|---|---|---|
| Circles are ellipses | x and y normalised by different sizes | divide both by the canvas height (section 1) |
| Stair-stepped, crawling edges | `step` or a fixed-width smoothstep in shape units | coverage ramp with the pixel size (4.3) |
| Edge softness changes with zoom or resolution | AA width given in shape units, not pixels | width = pixel size in the current units (1, 4.2) |
| Lines thicker on diagonals | `fwidth` (L1) used as the pixel size | Euclidean length of the derivative pair (4.2) |
| A hairline along the negative x-axis | `fwidth` or texture LOD of atan at the ±π seam | angular footprint = pixel size / radius (4.7) |
| Two-pixel lines at every tile border; "shredded rows" | derivative of fract, floor or a cell id | differentiate the continuous coordinate before folding (4.7, floor 6) |
| Shapes cut off by straight lines at cell borders | content larger than its cell, naive repetition | neighbour evaluation, or keep content inside, or mirrored repetition (6.1) |
| Random tiles form stripes far from the origin; AMD and NVIDIA differ | sin-based hash | integer hash (6.2) |
| Moiré and shimmer in distant or dense patterns | pattern finer than a pixel | analytic filtering or fade to average (4.5, 4.6) |
| Lines break into flickering dots | sub-pixel line width | phone-wire: clamp to one pixel, fade by ratio (4.5) |
| Hard colour bands in a fractal | integer iteration count | smooth iteration count with a large bailout (9.2) |
| Faint ripples at band edges | bailout too small for the smooth count | raise the bailout (9.2) |
| Fractal boundary is noisy sparkle | no distance estimate, no AA | distance estimate to pixels, coverage ramp (9.3) |
| Deep zoom turns into blocks | float32 precision (about ×10⁴ zoom) | perturbation design (9.6) |
| Holes, onion layers, flicker in a raymarched fractal | overestimating distance (non-uniform transform) | track the derivative; step by a fraction (10.1, 10.8) |
| Kaleidoscope shows thin lines at mirrors | crease from abs on the angle | soft abs on the angle (5.2) |
| Black speckles in a glowing golfed shader | tanh of a huge value (NaN on some drivers), or uninitialised variables | clamp before tanh; initialise everything (11.4) |
| Glyph corners rounded and blobby | single-channel SDF at low resolution | MSDF with median (8.3) |
| Glyph edges blurry or aliased at small sizes | wrong screen pixel range | compute the range from derivatives, clamp at least 1 (8.3) |

---

## 14. Methodology: how to dissect, and how to build at this fidelity

### 14.1 Dissecting any 2D shader (a checklist)

1. **Find the frame.** Where is the origin, what are the units, is there a pixel-size variable?
2. **List the domain operations in order** (rotate, polar, fold, repeat, invert, warp). Write them as a pipeline.
3. **Find the cell and its id.** What makes each copy different?
4. **Find the field.** Is it an exact distance, a bound, an iteration count, a trap, a glow accumulator?
5. **Find the coverage.** How is the edge antialiased, and in which units? Is anything differentiated after a fold?
6. **Find the colour mapping.** Palette, trap, distance bands?
7. **Find the composite.** Additive? Tonemapped? Gamma?
8. **Cost it.** Loops times iterations times operations; which pixels are slowest?

Write the answer as one line per layer. That line-per-layer description is exactly the module graph the house wants: a
`domain` module, a `source` module, a `mask` (coverage) and a `modifier` (colour).

### 14.2 Building at fidelity (the ladder)

1. Build the frame and a debug view (local coordinate as colour, ids as colour, cell borders).
2. Add one domain operation at a time; check its debug view after each.
3. Write the field as a *distance*; draw its isolines (section 7) to prove it is a distance.
4. Antialias with the pixel size; check at three resolutions and at extreme zoom.
5. Only then colour, glow and composite.
6. Profile the slowest pixels first (the boundary of a fractal, the densest region of a tiling).

### 14.3 Debug views every 2D module should support

- local coordinate as red/green; cell id hashed to a colour; cell or sector borders overlaid;
- distance isolines (inside and outside coloured differently);
- the pixel footprint as a heat map (shows where detail will alias);
- iteration count or step count as a heat map (the SDF lane's `dbgHeat`).

---

## 15. House notes from tonight's reading (findings, not changes)

Nothing below was edited; these are observations for whoever builds the library.

**15.1 The `hex-grid` chunk does not draw hexagons.** `design/vfx-chunks/hex-grid.glsl:5-14` uses the correct two-grid
lattice, but its edge measure is not the hex border distance for that lattice:

- it stretches x by 1.1547 (2/√3) before the lattice, which makes the cells non-regular;
- its edge expression takes the absolute value of x but not of y, so it is not symmetric: at local offset (0, +0.4) it reads
  0.40, at (0, −0.4) it reads 0.20 (checked numerically);
- its orientation matches flat-top hexagons while the lattice is pointy-top.

An ASCII rendering of where its border threshold fires (scratchpad `hexcheck.py`) shows small chevrons on one side of each
cell, not hexagon outlines; the correct metric (section 6.4) draws clean hexagons on the same lattice. Also: the pulse uses
`floor` of the rectangular coordinates rather than the hex id, so its value steps inside a hexagon; the line width is a fixed
0.02 in pattern units rather than a pixel width, so it aliases at small scales and blurs at large ones. If the chevron look
is loved, it deserves an honest name; otherwise rebuild it on `latHex` + `latHexEdge` + `aaStroke` (section 16).

**15.2 The `tanh-tonemap` chunk has no input clamp** (`design/vfx-chunks/tanh-tonemap.glsl:2`). Additive glow fields can get
large enough to risk the NaN-from-tanh black pixels described in 11.4. Clamping the input to about ±15 changes no visible
value.

**15.3 `kaleido` and `tile` throw away the cell and sector id** (`kaleido.glsl`, `tile.glsl`), so nothing downstream can vary
per copy. The library versions return the id (hg_sdf convention).

**15.4 The corpus licence classifier misses a restrictive notice.** 33 corpus shaders (32 by Inigo Quilez, 1 by Kazimierz
Pogoda, "morisil") carry the author's own notice ("I am the sole copyright owner of this Work"), which forbids hosting,
displaying, distributing or using the work in any commercial or non-commercial project, while permitting educational
linking with attribution; three of them also forbid training a neural network on the work. Most of their `meta.json`
files record "CC-BY-NC-SA-3.0 (Shadertoy default)" with `explicit: false`. Examples: `4ds3zn` (Apollonian), `Xd2GR3`
(Hexagons distance), `lss3Df`, `mds3DX`, `MdX3Rr` (Elevated), `XslGRr` (Clouds), `3lsSzf`, `WsSBzh`, `ld3Gz2`, `4ttSWf`; one,
`4s23zz` (Warping - procedural 1), is in the `sets.json` "loved" list. `4ttSWf` is labelled all-rights-reserved, but for
the wrong reason (its matched line is a comment about low-quality hashes). This matters for the "import them all into our
VFX tooling" plan: local study is within the notice's educational purpose; showing these in a shared or public gallery is
not. That is Daniel's call; the classifier should at least detect the notice (search for "sole copyright owner") and label
it.

**15.5 Licences of the references, for the library's own credits.**

| Source | Licence | What it means for the house |
|---|---|---|
| The Book of Shaders (text and site) | "All rights reserved" per its repository | learn from it; do not copy |
| LYGIA shader library | Prosperity (non-commercial) plus Patron licence for sponsors | do not vendor without a sponsorship decision |
| hg_sdf (Mercury) | MIT or CC BY-NC 4.0, user's choice | usable under MIT with credit |
| msdfgen, msdf-atlas-gen (Chlumský) | MIT | usable as offline tools |
| Star Nest (Kali, `XlfGRj`), Circuits (Kali, `XlX3Rj`) | MIT | adaptable with attribution |
| mrange's shaders (`Wl3fzM`, `7d2fDW`, `7lKSWW`, `NdKyDw`, `mtScRc`) | CC0 | free; credit anyway |
| iq's articles | no licence stated on the pages; some shaders MIT, others restricted (15.4) | treat the mathematics as knowledge, write our own code |
| Everything else in the corpus | mostly CC BY-NC-SA 3.0 | study only (house rule) |

---

## 16. The primitive API for the house library

### 16.1 Conventions (so modules compose and one change updates everything)

- **Where:** `arsenal/web/glsl/*.glsl`, resolved by `arsenal/shaders/modules.py` (dependencies are read from function
  names, so **every function name must be unique across the whole library**). Each module file carries the `//!` JSON header
  with `name`, `kind: "helper"`, `cat`, `license: "Apache-2.0"`, and a `credits` list naming who taught the technique (the
  linter requires both). No `#version`, no precision qualifiers (the host template declares `highp`), constant loop bounds
  (iteration counts are runtime values clamped to a `const int` maximum with `break`), no `?:` on structs, no derivative of a
  discontinuous value (shader-craft floors 1 and 6).
- **Naming** follows the SDF lane's camelCase prefixes where they overlap (`sd2…`, `ud2…`, `op…`, `dom…`, `aa…`, `dbg…`) and
  adds topic prefixes: `uv…` frame, `shp…` shaping, `lat…` lattices, `pat…` patterns, `iso…` contours, `txt…` text (never
  `gl_…`, which GLSL reserves), `cx…` complex, `frac…` fractals, `trap…` orbit traps, `glow…` golf-derived volume glow.
  Hashes and palettes are *reused* from the noise lane (`pcg2d`, `u01`) and the colour lane (`pal_cos`, `tm_tanh`), not
  redefined.
- **Units:** every distance is in the caller's current domain units; every `px` argument is the pixel footprint in those same
  units (from `uvPixel` or `uvFootprint`). Coverage is in [0, 1]. Signed distances are negative inside.
- **Domain operators** modify the point in place and return the cell, sector or orientation index (hg_sdf convention).
- **Cell ids are floats holding integers**, hashed with the noise lane's integer hashes after conversion; they are never
  differentiated.
- **Reused from sibling lanes** (do not duplicate): `sd2Box`, `ud2Segment`, `opRound`, `opOnion`, `opSmin`, `opSmax`,
  `domPolar`, `domPolarCandidate`, `aaDiskCoverage`, `dbgSlice`, `dbgHeat` (SDF lane); `pcg2d`, `u01`, `cell_f1f2`,
  `cell_edge`, `fbm_aa` (noise lane); `pal_cos`, `tm_tanh`, `srgb_encode` (colour lane).

### 16.2 Signatures and contracts (written fresh for the house)

**Module `uv2`** (cat `frame`)

| Signature | Contract |
|---|---|
| `vec2 uvCentered(vec2 fragCoord, vec2 resolution)` | Origin at canvas centre, y in [−1, 1], x scaled by the same factor (aspect-correct). |
| `float uvPixel(vec2 resolution)` | Size of one pixel in `uvCentered` units (2 / height); exact for any unwarped domain. |
| `float uvFootprint(vec2 p)` | Pixel footprint of a *continuous* coordinate: the larger of the lengths of its x and y screen derivatives. Never pass an id or a folded value. |

**Module `shaping`** (cat `math`)

| Signature | Contract |
|---|---|
| `float shpLinstep(float a, float b, float x)` | Linear 0→1 ramp from a to b, clamped; the box-filter edge. |
| `float shpSmoother(float a, float b, float x)` | Quintic ramp; zero slope and curvature at both ends (C2). |
| `float shpImpulse(float x, float k)` | Exponential impulse; 0 at x = 0, peak exactly 1 at x = 1/k, decays after. |
| `float shpPulse(float x, float centre, float halfWidth)` | Cubic bump, 1 at centre, exactly 0 beyond halfWidth (finite support). |
| `float shpGain(float x, float k)` | S-curve (k > 1) or inverse S (k < 1) on [0, 1]; fixes 0, ½ and 1; symmetric. |
| `float shpParabola(float x, float k)` | Bump 0 → 1 → 0 on [0, 1], sharpness k. |
| `float shpPowerCurve(float x, float a, float b)` | Asymmetric bump on [0, 1] with peak normalised to 1. |
| `float shpAlmostIdentity(float x, float threshold, float floorValue)` | Equals x above threshold; smoothly floored to floorValue below; C1. |
| `float shpSoftAbs(float x, float k)` | Creaseless |x|: within k of |x| everywhere, smooth at 0; for soft mirrors. |
| `float shpTri(float x)` | Triangle wave, period 1, range [0, 1]; the integral of a square wave. |

**Module `sdf2`** (cat `shape`; coordinate with the SDF lane, which owns `sd2Box` and `ud2Segment`)

| Signature | Contract |
|---|---|
| `float sd2Circle(vec2 p, float radius)` | Exact. |
| `float sd2RoundBox(vec2 p, vec2 halfSize, float cornerRadius)` | Exact; outer extent stays halfSize. |
| `float sd2Ngon(vec2 p, float inradius, float sides)` | Exact regular polygon, one vertex on +y, via sector fold. |
| `float sd2Hexagon(vec2 p, float inradius)` | Exact pointy-top hexagon, orientation matching `latHex`. |
| `float sd2Star(vec2 p, float outerRadius, float points, float innerRatio)` | Regular star; exact outside, bound inside. |
| `float sd2Arc(vec2 p, float radius, float halfAngle, float halfThickness)` | Exact arc band centred on +y, rounded ends. |
| `float sd2Bezier2(vec2 p, vec2 a, vec2 b, vec2 c)` | Exact unsigned distance to a quadratic Bézier (cubic solve); for glyph strokes. |

**Module `domain2`** (cat `domain`)

| Signature | Contract |
|---|---|
| `mat2 domRot2(float angle)` | Exact counter-clockwise rotation (never the golfed constant offsets). |
| `vec2 domToPolar(vec2 p)` | (radius, angle) with angle in (−π, π]. |
| `vec2 domFromPolar(vec2 radiusAngle)` | Inverse of `domToPolar`. |
| `float domKaleido(inout vec2 p, float sectors)` | Folds p into one mirrored sector around +x; adjacent sectors are reflections; returns sector index. |
| `float domKaleidoSoft(inout vec2 p, float sectors, float softness)` | As `domKaleido` with the mirror crease rounded over `softness` radians (mrange); returns sector index. |
| `float domFold2(inout vec2 p, vec2 unitNormal, float offset)` | Reflects p across the line {dot(p, n) = offset} if on its negative side; returns +1/−1 side. The KIFS atom. |
| `vec2 domRepeat2(inout vec2 p, vec2 period)` | Centred infinite repetition; p becomes local (−period/2..period/2); returns cell id. |
| `vec2 domRepeatMirror2(inout vec2 p, vec2 period)` | As above with odd cells mirrored so asymmetric content stays exact; returns cell id. |
| `vec2 domRepeatLimited2(inout vec2 p, vec2 period, vec2 idMin, vec2 idMax)` | Finite repetition by clamping the id; returns cell id. |
| `vec2 domRepeatCandidate2(vec2 p, vec2 period, int k, out vec2 cellId)` | Local point for the k-th (0..3) of the cells that can hold the nearest copy; caller takes the minimum. |
| `vec2 domBrick2(inout vec2 p, vec2 period, float rowShift)` | Repetition with alternate rows shifted by rowShift (fraction of a cell); returns cell id. |
| `vec2 domLogPolar(vec2 p)` | (ln radius, angle): scaling becomes translation; footprint is px / radius. |
| `vec2 domDroste(vec2 p, float scaleRatio, float turns)` | Escher/Droste remap: log-polar, twist so `turns` full turns span one scale ratio, tile, exponentiate. |
| `vec2 domInvert2(vec2 p, vec2 centre, float radiusSq, inout float stretch)` | Circle inversion; multiplies `stretch` by the local scale radiusSq/|p − centre|² so distances can be corrected. |
| `vec2 domTurb2(vec2 p, float time, int octaves, float freqGrowth, float amplitude)` | Xor-style turbulence: rotated sine displacement, frequency × growth per octave, amplitude / frequency. |

**Module `lattice`** (cat `domain`)

| Signature | Contract |
|---|---|
| `vec4 latHex(vec2 p)` | Pointy-top hexes, centres 1 apart: .xy = offset from nearest centre, .zw = that centre (unique id). Two-grid method. |
| `float latHexEdge(vec2 offset)` | Distance from a hex offset to its border: 0.5 at centre, 0 on the border (inradius 0.5). |
| `vec2 latHexAxial(vec2 centre)` | Integer axial coordinates (q, r) of a hex centre from `latHex`, for neighbour arithmetic and hashing. |
| `float latHexSteps(vec2 axialA, vec2 axialB)` | Number of hex steps between two cells (largest cube-coordinate difference). |
| `vec3 latTri(vec2 p, out vec2 cellId)` | Equilateral triangle cells (side 1): barycentric coordinates in the cell (min component = edge distance); cellId includes up/down orientation. |
| `float latParity(vec2 cellId)` | +1 or −1 checkerboard parity of a square-cell id; the flow-direction and weave sign. |

**Module `pattern`** (cat `pattern`, new)

| Signature | Contract |
|---|---|
| `vec3 patTruchet(vec2 p, uint seed)` | Smith quarter-arc Truchet on unit cells: .x = signed distance to the arc centre-line, .y = path parameter 0..1 continuous across tiles, .z = flow sign ±1. |
| `vec3 patTruchetHex(vec2 p, uint seed)` | Three-arc hexagonal Truchet on `latHex` cells; same outputs. |
| `vec4 patTruchetMulti(vec2 p, uint seed, float subdivideChance, int maxLevels)` | Carlson-style multi-scale Truchet: .x distance, .y level, .z colour sign (inverts per level), .w cell size. |
| `float patTenPrint(vec2 p, uint seed)` | Diagonal maze: distance to the cell's randomly chosen diagonal. |
| `vec3 patJitterNet(vec2 p, float time, uint seed, float px)` | "Universe Within" class network: jittered point per cell, lines to the 3×3 neighbourhood; .x line coverage, .y node glow, .z nearest-node id hash. |
| `vec2 patZoomLayer(float time, float layer, float layerCount)` | For infinite-zoom layering: .x scale for this layer, .y fade weight (0 at both ends of its life). |

**Module `aa2`** (cat `aa`)

| Signature | Contract |
|---|---|
| `float aaFill(float d, float px)` | Coverage of the inside of a signed distance; one-pixel linear ramp centred on the edge. |
| `float aaStroke(float d, float halfWidth, float px)` | Coverage of a band of half-width `halfWidth` around d = 0. |
| `float aaWire(float d, float widthPx, float px)` | Stroke never thinner than one pixel; opacity scaled by true / drawn width (phone-wire). |
| `float aaAngleFootprint(vec2 p, float px)` | Pixel footprint in radians at p (px / radius); seam-free replacement for `fwidth(atan(...))`. |
| `float aaImplicit(float f, vec2 gradient, float px)` | Coverage of the zero set of a non-distance field via f / |gradient| (first-order distance). |
| `float aaChecker(vec2 p, vec2 footprint)` | Box-filtered checkerboard (unit squares), value in [0, 1]; no aliasing at any distance. |
| `float aaGrid(vec2 p, vec2 lineWidth)` | Pristine grid (Golus): per-axis derivative footprints, phone-wire clamp, invert trick, fade to the mean as cells go sub-pixel. |
| `float aaCos(float x, float footprint)` | Band-limited cosine: cos(x) attenuated by the sinc of half the footprint; fades to 0 when a period fits in a pixel. |
| `float aaDetailFade(float px, float featureSize)` | 1 while the feature spans at least about 3 pixels, falling to 0 at one pixel; blend detail toward its mean by it. |

**Module `iso`** (cat `aa`)

| Signature | Contract |
|---|---|
| `float isoLines(float f, float spacing, float widthPx)` | Coverage of level lines of a continuous scalar every `spacing`; Euclidean screen derivative; phone-wire clamp; fades to the mean when lines are under ~3 px apart. |
| `float isoLinesGrad(float f, vec2 gradientPerPixel, float spacing, float widthPx)` | Same with an analytic gradient already in per-pixel units; no derivative instructions, safe inside branches. |
| `vec2 isoMajorMinor(float f, float spacing, float majorEvery, float widthPx)` | (minor, major) line coverages; major lines every `majorEvery` levels. |

**Module `text`** (cat `text`, new)

| Signature | Contract |
|---|---|
| `float txtAtlasSdf(sampler2D atlas, vec2 glyphUv, float charCode, float bias)` | Signed distance (atlas texels) to a glyph in a 16×16 single-channel SDF atlas; glyphUv in [0, 1]² inside the glyph cell. |
| `float txtMedian3(vec3 channels)` | Median of three MSDF channels: the reconstructed signed distance. |
| `float txtScreenPxRange(vec2 atlasUv, vec2 atlasSize, float pxRange)` | Screen pixels per stored distance unit (msdfgen convention) from derivatives of the continuous atlas coordinate; at least 1. |
| `float txtSeg7(vec2 p, float digit, float stroke)` | Seven-segment digit SDF in a cell of [−0.5, 0.5] × [−1, 1]; digits 0–9, other values blank. |
| `vec4 txtLayers(float d, float px, vec4 fill, vec4 outline, float outlineWidth, vec4 glow, float glowWidth)` | Fill, outline and glow composited (premultiplied) from one distance, after Green (2007). |

**Module `complex`** (cat `math`)

| Signature | Contract |
|---|---|
| `vec2 cxMul(vec2 a, vec2 b)` | Complex product (rotate by b's angle, scale by its length). |
| `vec2 cxSq(vec2 z)` | Complex square. |
| `vec2 cxDiv(vec2 a, vec2 b)` | Complex quotient; caller guards b ≠ 0. |
| `vec2 cxExp(vec2 z)` | Complex exponential. |
| `vec2 cxLog(vec2 z)` | Principal complex logarithm (ln |z|, arg z); seam on the negative real axis. |
| `vec2 cxPowReal(vec2 z, float n)` | z to a real power via polar form. |

**Module `escape`** (cat `fractal`, new)

| Signature | Contract |
|---|---|
| `float fracMandel(vec2 c, int maxIter, float bailout, out float smoothIter, out vec4 trap)` | Mandelbrot escape loop with derivative: returns the safe (half) distance estimate, 0 inside; smoothIter continuous; trap from `trapUpdate`. |
| `float fracJulia(vec2 z, vec2 c, int maxIter, float bailout, out float smoothIter, out vec4 trap)` | As above for the Julia set of c. |
| `float fracSmoothIter(float n, float zLenSq, float degree, float bailout)` | Continuous escape count from |z|² at escape; band-free across iterations. |
| `bool fracInMainBody(vec2 c)` | True inside the main cardioid or the period-2 bulb (skip iterating). |
| `vec4 trapUpdate(vec4 trap, vec2 z, vec2 point, float ringRadius)` | Running minima of distance to a point, the x-axis, the y-axis and a ring. |

**Module `kifs`** (cat `fractal`)

| Signature | Contract |
|---|---|
| `float fracKifs2(vec2 p, int iters, float scale, vec2 centre, float angle, out vec2 foldedP)` | 2D kaleidoscopic IFS (abs fold, rotate, scale about centre); distance to the base segment divided by scale^iters; foldedP for texturing. |
| `float fracKoch(vec2 p, int iters, out vec2 foldedP)` | Koch snowflake edge distance (sector fold, then scale 3, centre, abs, 60° reflection per iteration). |
| `float fracSierpinski2(vec2 p, int iters)` | Sierpinski triangle distance by three folds and scale 2 per iteration. |
| `float fracApollonian2(vec2 p, float strength, int iters, out float trap)` | Repeat-and-invert packing in a 2D slice; distance divided by the accumulated inversion stretch. |
| `float fracKali2(vec2 p, vec2 c, int iters, out vec3 stats)` | Kaliset iteration (abs, divide by squared length, subtract c); returns accumulated |change of length|; stats = (min, mean, final) length. |

**Module `fold3`** (cat `fractal`)

| Signature | Contract |
|---|---|
| `vec3 fracBoxFold(vec3 p, float limit)` | Reflects each coordinate beyond ±limit back inside (Mandelbox box fold). |
| `vec3 fracSphereFold(vec3 p, inout float dr, float minRadiusSq, float fixedRadiusSq)` | Mandelbox ball fold; applies the same factor to the running derivative dr. |
| `float fracMandelbox(vec3 p, float scale, float minRadius, int iters, out vec4 trap)` | Mandelbox distance estimate |p| / |dr|; c = the input point. |
| `float fracMandelbulb(vec3 p, float power, int iters, out vec4 trap)` | Triplex-power Mandelbulb; returns 0.5 ln r · r / dr (march-safe). |
| `float fracMenger(vec3 p, int iters)` | Menger sponge as a KIFS (abs, sort, scale 3); distance divided by 3^iters. |
| `vec3 fracTetraFold(vec3 p)` | The three plane reflections of the tetrahedral group (Sierpinski tetrahedron, Knighty KIFS). |

**Module `glow`** (cat `tone`)

| Signature | Contract |
|---|---|
| `float glowStep(float d, float passthrough, float density)` | Volume-sampler step: passthrough + |d| / density; never zero, so a golf-style march always advances. |
| `vec3 glowAccum(vec3 acc, vec3 colour, float stepLen, float minStep)` | Adds colour / max(stepLen, minStep); the 1/d halo with a floor against infinities. |

The colour lane's `tm_tanh` should clamp its input (15.2) so every glow field can use it safely.

**Module `debug2`** (cat `debug`)

| Signature | Contract |
|---|---|
| `vec3 dbgCells(vec2 local, vec2 cellId, vec2 period, float px)` | Local coordinate as red/green, id hashed to a tint, cell borders overlaid; the BigWings development view. |
| `vec3 dbgFootprint(float px, float featureSize)` | Heat map of how many pixels a feature spans (blue = safe, red = aliasing). |

### 16.3 Build order for this lane

1. `uv2`, `shaping`, `aa2` (`aaFill`, `aaStroke`, `aaWire`, `aaAngleFootprint`), `debug2`: honest edges first.
2. `domain2` and `lattice`: every tiling and kaleidoscope in the house rebuilt on them (the `hex-grid` and `kaleido` chunks
   first, 15.1 and 15.3).
3. `pattern` and `iso`: the generative vocabulary.
4. `complex`, `escape`, `kifs`: 2D fractals with distance-estimate AA.
5. `text`: MSDF plus seven-segment, so the bench can label itself.
6. `fold3` and `glow`: hand to the SDF lane's marcher.

---

## 17. Corpus map (pointers for study only)

| Technique | Pointer | Licence (as recorded) |
|---|---|---|
| Two-grid hex coordinates | `wsl3WB/image.glsl:16-33` (BigWings, Hexagone) | CC BY-NC-SA 3.0 |
| Neighbour evaluation for overflowing cells | `wsl3WB/image.glsl:72-87` | CC BY-NC-SA 3.0 |
| Skewed-lattice hex with border distance | `Xd2GR3/image.glsl:16-37` (iq) | author-restricted notice (15.4) |
| Jittered network, 3×3 neighbours, infinite zoom layers | `lscczl/image.glsl:39-140` (BigWings, The Universe Within) | CC BY-NC-SA 3.0 |
| Hexagonal Truchet height map | `4td3zj/image.glsl:32-72` (Shane) | CC BY-NC-SA 3.0 |
| Smooth kaleidoscope, mirror-repeat | `7lKSWW/image.glsl:75-97` (mrange) | CC0 |
| Square-grid Truchet distance | `7lKSWW/image.glsl:120-180` (mrange) | CC0 |
| Isolines: fwidth vs derivative length vs finite differences | `Ms2XWc/image.glsl:59-82` (Sébastien Durand) | CC BY-NC-SA 3.0 |
| Sine isolines with fwidth | `ldfczS/buf_a.glsl:24-31` (Fabrice Neyret) | CC BY-NC-SA 3.0 |
| Shadertoy SDF font atlas sampling | `XsVcDy/image.glsl:27-60` (mattz) | CC BY-NC-SA 3.0 |
| Wythoff construction, fold-based polyhedra | `Md3yRB` (mattz) | CC BY-NC-SA 3.0 |
| Mandelbrot derivative, distance, decoration in escaped space | `ttscWn/image.glsl:86-157` (Shane) | CC BY-NC-SA 3.0 |
| Kaliset volumetric (Star Nest) | `XlfGRj/image.glsl:40-62` (Kali) | MIT |
| Box-fold identity, "Amazing Surface" | `XsBXWt/image.glsl:34-40` (Kali) | CC BY-NC-SA 3.0 |
| Inversion with distance correction | `4dsGD7/image.glsl:15-26` (Kali) | CC BY-NC-SA 3.0 |
| Kaliset 2D field accumulation | `lslGWr/pass.glsl:2-16` (JoshP); `MdXSzS` (Dave Hoskins) | CC BY-NC-SA 3.0 |
| Apollonian repeat-and-invert | `Wl3fzM/image.glsl:18-32`, `7d2fDW` (mrange); `4ds3zn/image.glsl:31-51` (iq) | CC0; iq restricted |
| Mandelbox with derivative in w, branch-free ball fold | `4sjSW1/image.glsl:13-57` (Dave Hoskins, Remnant X) | CC BY-NC-SA 3.0 |
| Menger sponge KIFS | `Mdf3z7/pass.glsl:55-66` (Syntopia) | CC BY-NC-SA 3.0 |
| Mandelbulb distance estimate | `MdXSWn/image.glsl:34-59` (EvilRyu) | CC BY-NC-SA 3.0 |
| Golfed volume march, turbulence, tanh | `3XXSWS`, `wXjSRt`, `WcKXDV`, `3csSWB`, `msjXRK` (Xor) | CC BY-NC-SA 3.0 |
| Safe tanh | `XXyGzh/common.glsl:1-3` (SnoopethDuckDuck) | CC BY-NC-SA 3.0 |
| Gateway: fract repetition, 1/d glow, palette | `mtyGWy` (kishimisu); `XsXXDn` (Danilo Guanabara) | CC BY-NC-SA 3.0 |
| Other pattern studies | `NlK3Wt` hex cyberspace (bitless), `WtfGDX` triangle contouring (Shane), `llSyDh` hex maze flow (Shane), `MsVfz1` neon hexagons (Shane), `tlVGDt` octagrams, `Xsd3zf` snowflakes (foxes), `llVXRd` geodesic tiling (tdhooper), `Xt3yDS` isoline triangle (tdhooper), `MscSzf` noise contour, `NdKyDw` hex marching (mrange, CC0) | as recorded |

---

## 18. Sources

Primary and author-written first; tutorials after.

- https://thebookofshaders.com/05/ — Gonzalez Vivo and Lowe: shaping functions, plotting a function, step/smoothstep, sine rhythms.
- https://thebookofshaders.com/07/ — shapes from distance fields, polar shapes, N-gons (Andrew Baldwin's polygon form).
- https://thebookofshaders.com/09/ — fract tiling, brick offsets, Truchet rotation by cell, pattern history.
- https://github.com/patriciogonzalezvivo/thebookofshaders — the book's repository: "all rights reserved"; fractals chapter unfinished.
- https://github.com/patriciogonzalezvivo/lygia — LYGIA library layout and its Prosperity/Patron dual licence.
- https://iquilezles.org/articles/functions/ — Inigo Quilez's remapping catalogue: impulses, pulses, gain, parabola, power curve.
- https://iquilezles.org/articles/distfunctions2d/ — the 2D SDF catalogue, exact versus bound, rounding and onion.
- https://iquilezles.org/articles/distance/ — f/|∇f| for constant-width implicit curves and isolines.
- https://iquilezles.org/articles/sdfrepetition/ — domain repetition: neighbour checks, mirrored and limited repetition, angular repetition.
- https://iquilezles.org/articles/filterableprocedurals/ — analytic box filtering of procedural patterns.
- https://iquilezles.org/articles/checkerfiltering/ — the filtered checkerboard derivation (square wave → triangle wave).
- https://iquilezles.org/articles/bandlimiting/ — band-limiting cosines and fBm octaves by the pixel footprint.
- https://iquilezles.org/articles/palettes/ — the cosine palette and its four parameters.
- https://iquilezles.org/articles/msetsmooth/ — smooth iteration count for the Mandelbrot set.
- https://iquilezles.org/articles/distancefractals/ — distance estimation for Mandelbrot and Julia sets.
- https://iquilezles.org/articles/ftrapsgeometric/ — geometric orbit traps: point, line, circle, statistics.
- https://iquilezles.org/articles/ftrapsbitmap/ — bitmap orbit traps.
- https://iquilezles.org/articles/mandelbulb/ — Mandelbulb iteration, distance estimate, trig-free form, orbit-trap colouring.
- https://en.wikipedia.org/wiki/Plotting_algorithms_for_the_Mandelbrot_set — escape time, smooth colouring, DE bounds, cardioid test, perturbation.
- https://www.redblobgames.com/grids/hexagons/ — Amit Patel: hex orientations, axial and cube coordinates, rounding, distances, rotation.
- https://inspirnathan.com/posts/174-interactive-hexagon-grid-tutorial-part-5/ — the two-grid hex shader method, credited to the Art of Code.
- https://andrewhungblog.wordpress.com/2018/07/28/shader-art-tutorial-hexagonal-grids/ — hex grids and per-hex effects (credits Shane).
- https://www.youtube.com/watch?v=VmrIDyYiJBA — Martijn Steinrucken, "Hexagonal Tiling Explained" (Art of Code).
- https://www.youtube.com/watch?v=2R7h76GoIJM — Martijn Steinrucken, "Truchet Tiling Explained".
- https://www.youtube.com/watch?v=il_Qg9AqQkE — Martijn Steinrucken, "KIFS Fractals explained!" (the Koch snowflake).
- https://www.youtube.com/watch?v=l-07BXzNdPw — Martijn Steinrucken, Voronoi tutorial.
- https://clauswilke.com/art/post/shaders — Claus Wilke's learning path listing the Art of Code videos and iq resources.
- https://gist.github.com/tspringborg/076c4c4be63047dc8d83f95d3c9a881b — community copy of BigWings' Koch snowflake shader (CC BY-NC-SA; read for the algorithm).
- https://christophercarlson.com/portfolio/multi-scale-truchet-patterns/ — Christopher Carlson: winged tiles, colour inversion per level.
- https://archive.bridgesmathart.org/2018/bridges2018-39.html — Carlson, "Multi-Scale Truchet Patterns", Bridges 2018 paper.
- https://mercury.sexy/hg_sdf/ — Mercury's hg_sdf: domain operators that return cell ids; MIT or CC BY-NC 4.0.
- https://shadertoyunofficial.wordpress.com/2016/07/21/usual-tricks-in-shadertoyglsl/ — Fabrice Neyret: derivatives in 2×2 blocks, precision, LOD at seams.
- https://shadertoyunofficial.wordpress.com/2021/03/09/advanced-tricks/ — Fabrice Neyret: distance-based AA, adaptive supersampling by fwidth of the output.
- https://bgolus.medium.com/the-best-darn-grid-shader-yet-727f9278b9d8 — Ben Golus: the pristine grid (article refuses automated fetch).
- https://gist.github.com/bgolus/d49651f52b1dcf82f70421ba922ed064 — Golus's pristine grid shader: per-axis footprints, invert trick, moiré fade.
- https://www.humus.name/Articles/Persson_GraphicsGemsForGames.pdf — Emil Persson: phone-wire AA (clamp to a pixel, fade by coverage).
- https://steamcdn-a.akamaihd.net/apps/valve/2007/SIGGRAPH2007_AlphaTestedMagnification.pdf — Chris Green (Valve): SDF glyph textures, outlines, glows, shadows, two-channel corners.
- https://github.com/Chlumsky/msdfgen — Viktor Chlumský's MSDF generator (MIT): median reconstruction, pixel range.
- https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.13265 — Chlumský et al., "Improved Corners with Multi-Channel Signed Distance Fields" (CGF 2018).
- https://www.redblobgames.com/articles/sdf-fonts/ — Amit Patel: practical SDF/MSDF font rendering, AA, outlines, glow, pitfalls.
- https://wdobbie.com/post/gpu-text-rendering-with-vector-textures/ — Will Dobbie: exact coverage from Bézier curves stored in textures.
- https://reindernijhoff.net/2014/05/escher-droste-effect-webgl-fragment-shader/ — Reinder Nijhoff: the Escher/Droste spiral as a fragment shader.
- https://en.wikipedia.org/wiki/Droste_effect — the Droste effect and de Smit and Lenstra's explanation of Escher's Print Gallery.
- https://en.wikipedia.org/wiki/Apollonian_gasket — construction, Descartes' theorem, Möbius invariance, dimension.
- http://www.fractalforums.com/sierpinski-gasket/kaleidoscopic-(escape-time-ifs)/ — Knighty's original KIFS post (1 May 2010).
- http://blog.hvidtfeldts.net/index.php/2011/08/distance-estimated-3d-fractals-iii-folding-space/ — Syntopia: folding space, Sierpinski and Menger by folds (TLS failed tonight; cited from search summary).
- https://sites.google.com/site/mandelbox/what-is-a-mandelbox — Tom Lowe: the Mandelbox rules and parameters.
- https://www.skytopia.com/project/fractal/mandelbulb.html — Daniel White: the history of the Mandelbulb (Rucker, White, Nylander, Makin).
- https://defgsus.github.io/blog/2021/10/12/kaliset-explorer.html — the Kaliset formula and its colouring statistics.
- http://www.fractalforums.com/new-theories-and-research/very-simple-formula-for-fractal-patterns/ — Kali's thread behind the Kaliset family.
- https://jcgt.org/published/0009/03/02/ — Jarzynski and Olano, "Hash Functions for GPU Rendering" (JCGT 2020).
- https://mini.gmshaders.com/p/code-golfing — Xor: golf substitutions and their caveats.
- https://mini.gmshaders.com/p/turbulence — Xor: rotated sine-wave turbulence.
- https://mini.gmshaders.com/p/volumetric — Xor: volume marching with abs distance, passthrough and 1/d glow.
- https://mini.gmshaders.com/p/decoding-phosphor — Xor: a 258-character shader decoded step by step.
- https://mini.gmshaders.com/p/dot-noise — Xor: cheap golden-ratio "dot noise" and its limits.
- https://tympanus.net/codrops/2025/06/23/modeling-the-world-in-280-characters/ — Xor's Codrops essay on tiny shaders (fetch refused; cited from search summary).
