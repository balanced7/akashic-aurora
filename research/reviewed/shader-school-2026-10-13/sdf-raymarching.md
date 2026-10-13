---
title: Signed distance fields and raymarching
kind: research report (full fidelity)
series: shader school 2026-10-13 (one of eight topic reports)
author: claude researcher seat
date: 2026-10-13
status: reviewed research; primary sources read in full where reachable
licence-note: >
  All prose, formulas-as-written and GLSL signatures here are original. No corpus code
  (state/arsenal/shaders/corpus) is reproduced; corpus references are file:line pointers only.
  Inigo Quilez states his article code snippets are MIT; Mercury's hg_sdf is "MIT OR CC-BY-NC-4.0".
  The house rule is stricter than either licence: we write our own.
---

# Signed distance fields and raymarching

## 0. How to read this

This report is meant to take a capable programmer who has never written a shader to the point
where they can read any Shadertoy raymarcher, say what every line is for, spot what is wrong with
it, and build a better one. It is long on purpose. Sections 3 to 7 teach; section 8 is the
"what does broken look like" table; section 9 is the dissection kit for our corpus; section 12 is
the primitive API the house library should ship.

**The one-paragraph version, for Daniel.** A signed distance field (SDF) is a function that, for
any point in space, answers one question: "how far is the nearest surface, and am I inside or
outside it?" Once you have that function, rendering is a game of safe jumps: stand at the camera,
ask the function how far the nearest surface is, and leap exactly that far along your line of
sight, because nothing can be closer than that. Repeat until the answer is "practically zero" (you
hit something) or you run out of road. That loop is called sphere tracing (or, loosely,
raymarching). Everything else in this report is either (a) how to write good distance functions,
(b) how to make the safe-jump loop take fewer, bigger, still-safe jumps, or (c) how to reuse the
distance function to get lighting effects (shadows, ambient occlusion, edge smoothing) that a
polygon renderer would pay dearly for.

**Hardware analogy that carries the whole topic.** The distance function is a *sonar ping*. A
submarine that pings and hears "nearest rock: 40 metres" can move 40 metres in any direction
without hitting anything. It does not know where the rock is, only that it is at least that far.
Sphere tracing is a submarine creeping down a channel by repeated pings. The cleverness in this
field is all about pinging less often and trusting each ping exactly as much as it deserves.

## 1. Vocabulary (spelled out once)

| Term | Plain meaning |
|---|---|
| **SDF, signed distance function/field** | A function `f(p)` of a 3D point `p`. Outside an object it returns the distance to the nearest surface (positive); inside it returns minus the distance to the nearest surface (negative); on the surface it returns zero. |
| **Isosurface / zero set** | The set of points where `f(p) = 0`: the visible surface. |
| **Distance bound** (or "signed distance bound", "SDF estimate") | A function that is *never larger* than the true distance (in absolute value) and is zero exactly on the surface. Safe for marching, just slower. Most real scene functions are bounds, not exact SDFs. |
| **Overestimate** | A field that sometimes claims more room than really exists. Dangerous: the marcher jumps through surfaces. |
| **Lipschitz constant `L`** | The maximum rate at which the function can change per unit of distance moved. A true SDF has `L = 1` ("speed limit 1"). If `L > 1`, dividing the function by `L` turns it back into a safe bound. |
| **Gradient `∇f`** | The direction in which `f` grows fastest, and how fast. For a true SDF its length is exactly 1 almost everywhere (the "Eikonal" property), and on the surface it points along the surface normal. |
| **Ray** | A starting point `ro` (ray origin) and a unit direction `rd`; points on it are `ro + t·rd` for distance `t`. |
| **Sphere tracing** | John C. Hart's name for the safe-jump loop: step `t` forward by `f(ro + t·rd)` each iteration. The empty ball of radius `f` around the current point is the "unbounding sphere". |
| **Raymarching** | The general family of "walk along the ray and test" methods; sphere tracing is the distance-aided member. In the demoscene the words are used interchangeably. |
| **Domain** | The input space of the function (the points `p`). "Domain operations" warp or fold `p` before evaluating a shape; they are how one object becomes infinitely many. |
| **CSG, constructive solid geometry** | Building shapes from booleans: union, intersection, subtraction. |
| **smin / smooth minimum** | A softened `min()` that melts two shapes together with a fillet. |
| **Cone tracing / cone marching** | Treating each pixel as a thin cone rather than a zero-width ray, so that "close enough to touch the pixel's footprint" is a meaningful stopping rule, and so that neighbouring pixels can share work. |
| **Pixel footprint** | How wide one pixel is, in world units, at distance `t` from the camera. Grows linearly with `t`. |
| **Map / scene function** | The conventional name (`map`, `sceneSDF`) for the single function that returns the distance to the whole scene. |

## 2. Where this came from (credits)

- **A. Ricci** combined implicit shapes with `min` and `max` (Quilez dates it 1972; Hart cites a
  1974 Ricci paper for the same min/max CSG); **B. and G. Wyvill (1989)** followed with
  soft-object combination. (History as summarised by Inigo Quilez.)
- **John C. Hart, Daniel Sandin, Louis Kauffman (SIGGRAPH 1989)**, "Ray tracing deterministic 3-D
  fractals": first distance-bounded marching, used for 3D fractals.
- **John C. Hart (The Visual Computer, 1996)**, "Sphere tracing: a geometric method for the
  antialiased ray tracing of implicit surfaces": the canonical paper. Lipschitz bounds, the
  convergence proof, convexity speed-ups, the triangle-inequality cache, and cone-traced
  antialiasing all live here.
- **William Donnelly (GPU Gems 2, 2005)**, per-pixel displacement mapping with distance functions:
  the idea arrives on GPUs.
- **Alex Evans ("Statix"), SIGGRAPH 2006 course**, fast approximate global illumination on dynamic
  scenes: the distance-field ambient-occlusion trick that Quilez later popularised.
- **Inigo Quilez (iq)**: from 2007 onward turned SDFs into an art-directed medium (Slisesix, 4 KB
  procedural image, 1st place Euskal 2008; nvscene 2008 talk "Rendering Worlds with Two
  Triangles"), and has since documented primitives, smooth minimum, repetition, shadows, normals,
  bounding, interior distances and filtering on iquilezles.org.
- **Mercury demogroup** (hg_sdf library, released 2015, used in their 64 KB intros): the
  "distance bound discipline" and the right-angle combination operators (chamfer, stairs,
  columns, groove, tongue, engrave, pipe). hg_sdf points readers to Hart and to Enhanced Sphere
  Tracing as the papers to build a tracer from. (We did not verify which Mercury members are
  among the Enhanced Sphere Tracing authors, so we make no such claim.)
- **Benjamin Keinert, Henry Schäfer, Johann Korndörfer, Urs Ganse, Marc Stamminger (STAG 2014)**,
  "Enhanced Sphere Tracing": over-relaxation, screen-space candidate selection, dynamic epsilon,
  discontinuity reduction, convex-object shortcut.
- **Seven / Fulcrum (Revision 2012)**, "Rendering Mandelbox fractals faster with cone marching":
  multi-pass coarse-to-fine depth.
- **Csaba Bálint and Gábor Valasek (Eurographics 2018 short paper)**, "Accelerating Sphere
  Tracing": planar-extrapolation stepping and resolution ramps.
- **Sebastian Aaltonen (GDC 2018, Claybook)**: the improved soft-shadow penumbra estimate
  (credited by Quilez); SDF ray tracing in a shipped game.
- **Shadertoy community** credited inside individual techniques below (Paulo Falcão, Paul Malin,
  Thomas Hooper, Clément "Klems" Baticle, Fizzer, Jakob "jt" Thomsen, nurof3n, Nicolas Klenert and
  others).

## 3. The mathematics of a distance field

### 3.1 Definition and sign convention

Let `S` be a surface enclosing a solid. The signed distance function is

- `f(p) = +dist(p, S)` when `p` is outside,
- `f(p) = −dist(p, S)` when `p` is inside,
- `f(p) = 0` on `S`.

`dist(p, S)` is ordinary straight-line (Euclidean) distance to the closest point of `S`. The house
convention, like everyone's, is **negative inside**.

Three properties fall out of this definition and are worth memorising, because every technique
later leans on one of them:

1. **The empty-ball property.** No surface point lies within `|f(p)|` of `p`. That is the whole
   reason a marcher may jump `f(p)` along any direction.
2. **The Eikonal property.** Wherever the closest surface point is unique, the gradient has length
   exactly 1: walk one unit straight away from the surface and the distance grows by one unit.
3. **The gradient is the normal.** On the surface, `∇f` points along the outward surface normal.
   Off the surface it points directly away from the nearest surface point.

### 3.2 Exact fields versus bounds, and the Lipschitz idea

A function is **Lipschitz with constant `L`** if `|f(a) − f(b)| ≤ L·|a − b|` for all points `a`, `b`.
Think of `L` as a speed limit on how fast the field may change as you move. An exact SDF has
`L = 1`.

**Hart's Theorem 1 (in our words):** if `f` is zero exactly on the surface and has Lipschitz
constant at most `L`, then `f / L` never exceeds the true distance. So any well-behaved implicit
function becomes safe to sphere-trace once you divide by its speed limit. Proof sketch: take the
closest surface point `y`; `f(y) = 0`, so `|f(p)| = |f(p) − f(y)| ≤ L·|p − y| = L·dist(p, S)`.

This splits all scene functions into three bins that the house library must label explicitly
(section 12 encodes the bin in the function's name prefix):

| Bin | Meaning | Marcher consequence |
|---|---|---|
| **Exact** | `f` equals the true signed distance | Fastest; shadows/AO calibrated; physics correct |
| **Bound** | `f` never exceeds the true distance, zero on the surface | Always correct picture, more steps; shadows/AO slightly too dark/wide |
| **Overestimate** | `f` sometimes exceeds the true distance | Holes, missing chunks, flicker. Needs a backtracking marcher or a fix |

Mercury's rule of thumb (from the hg_sdf comments, paraphrased): keep every gradient at most 1 and
as close to 1 as you can; underestimates will happen, which is why "distance bound" is the honest
name; never paper over a violation by multiplying the whole result by a fudge factor.

### 3.3 Lipschitz arithmetic: the rules you actually use

These are from Hart's appendices, restated:

- **Sum:** `L(f + g) ≤ L(f) + L(g)`.
- **Composition:** `L(f ∘ q) ≤ L(f) · L(q)`. If you warp space with a map `q` and evaluate `f(q(p))`,
  the speed limit is multiplied by how much `q` can stretch distances (the largest singular value of
  its Jacobian matrix, the matrix of partial derivatives).
- **Uniform scale by `s`:** evaluate `f(p / s)` and multiply the result by `s`. Exact.
- **Non-uniform scale by `(sx, sy, sz)`:** evaluate `f(p / s)` and multiply by `min(sx, sy, sz)`. Only a
  bound (Jamie Wong's tutorial gives the same rule).
- **Rotation and translation:** exact (they do not stretch space). Apply the *inverse* transform to `p`.
- **Displacement:** `f(p) + A·g(p)` where the pattern `g` has gradient length at most `G`: speed
  limit is at most `1 + A·G`, so divide by `1 + A·G`. Example: the classic
  `sin(ωx)·sin(ωy)·sin(ωz)` bump with amplitude `A` has gradient length at most `A·ω`, so divide by
  `1 + A·ω`.
- **Twist** about the y axis at rate `k` radians per unit height. The warp's Jacobian is a shear of
  size `k·r` at radius `r` from the axis. Its largest singular value is
  `σ(k, r) = (k·r + sqrt(k²·r² + 4)) / 2`. So within a radius `R`, divide the distance by
  `σ(k, R)`. Two traps: (1) twist is not Lipschitz over all of space (the stretch grows without
  limit with radius), so you must bound the region, which Hart also points out; (2) the tempting
  formula `sqrt(1 + k²r²)` *underestimates* the stretch (we checked numerically: at `k·r = 1` the true
  value is 1.618, the tempting one is 1.414), so it leaves the field overestimating.
- **Bend** is the same shear story along a different axis, with the same correction.

Quilez's practical advice (distfunctions article) matches the maths: reach the shape with exact
operations (elongate, round, onion, union) and tight bounds (intersection, subtraction) first, and
use distortion or displacement only for the last small amount, so the field stays near-Euclidean
and the marcher stays fast.

### 3.4 When you only have an implicit function: `f / |∇f|`

Many lovely shapes are written as "some expression equals zero" without being distances (noise
surfaces, trigonometric blobs, fractal formulas). Quilez's "distance" article gives the first-order
fix: by Taylor expansion near the surface, the distance is approximately `|f(p)| / |∇f(p)|`. This
gives constant-thickness outlines in 2D and usable marching in 3D. It is an *estimate*, not a
guaranteed bound (Hart cites Taubin's result that it becomes exact as you approach the surface).
Fractal "distance estimators" (Mandelbulb, Julia sets) are the same idea with the derivative
carried along the iteration; Quilez's "Computing the SDF of fractals" covers the formulas.

## 4. Building shapes

### 4.1 The primitives and why they work

Every exact primitive is a small geometry proof. Learn three and the rest read easily.

**Sphere.** Distance to the centre minus the radius: `|p − c| − r`. Exact everywhere.

**Box** (centred at the origin, half-sizes `b`). Fold the point into the positive octant with
`abs()`, because a box is symmetric in all three axes. Let `q = |p| − b` (componentwise).

- If every component of `q` is negative, you are inside; the nearest face is the one you are
  closest to, so the distance is the largest (least negative) component of `q`.
- Otherwise, only the positive components matter (you are past those faces); the distance to the
  nearest point of the box is the length of `max(q, 0)`.

The exact formula is "length of the positive part" plus "largest component, clamped to at most 0".
This *positive part plus clamped interior* pattern recurs constantly (cylinders, extrusions,
elongations).

**Rounded box.** Shrink the box by `r` and subtract `r` (move to a different isosurface). The
result keeps its outer size and gets radius-`r` edges. Exact.

**Capsule / segment.** Project `p` onto the segment `a→b`, clamping the projection parameter to
`[0, 1]`, then take distance to that closest point minus the radius. Exact. (The house already has
the 2D version as `design/vfx-chunks/segment-distance.glsl`.)

**Torus** (in the xz plane). Reduce to 2D: the point's distance from the y axis minus the ring
radius, paired with its height; the torus is then a circle in that 2D plane. Exact.

**Plane.** `dot(p, n) + h` with `n` a *unit* normal. Exact. If `n` is not unit length, the field is
scaled wrong; that is a classic silent bug.

**Cones, capped cylinders, hexagonal prisms, octahedra, pyramids, triangles, quads** all exist in
exact form (Quilez's 3D SDF page lists them and marks exact versus bound). Pattern: exploit
symmetry with `abs()`, reduce to a 2D problem by revolving (`length(p.xz)`), then find the closest
point on a few line segments.

**Ellipsoid** is the famous exception: no closed-form exact distance. Quilez's ellipsoid article
compares two bounds. Stretching space into a sphere and multiplying by the smallest radius is a
weak bound (very slow marching, shadows too wide). Dividing the stretched-sphere value by its
gradient length (one extra square root) is a much tighter bound that "lives in the same distance
universe" as exact primitives, so shadow and occlusion parameters stay consistent. Use the second.

### 4.2 Lifting 2D to 3D keeps exactness

Quilez's key observation: **revolution** (feed a 2D SDF the coordinates
`(length(p.xz) − offset, p.y)`) and **extrusion** (combine a 2D distance with the depth `|z| − h`
using the box's positive-part-plus-interior pattern) produce *exact* 3D SDFs from exact 2D ones,
and they are usually cheaper than building the same shape from 3D booleans, which are only bounds.
Much of the 3D catalogue is literally a revolved or extruded 2D shape.

### 4.3 Rounding, onion, elongation (exact modifiers)

- **Round / inflate:** `f − r`. Moves to a different isosurface, rounding every convex edge.
  Exact if `f` was exact. To keep overall size, shrink the source by `r` first.
- **Onion / shell:** `|f| − thickness`. Turns a solid into a hollow shell of given thickness;
  repeat for concentric layers. Exact.
- **Elongation:** cut the shape at the origin along chosen axes, pull the halves apart by `h`, and
  bridge the gap. Done by evaluating the base shape at `p − clamp(p, −h, h)`. Exact outside; for 2D
  and 3D elongations this simple form leaves a zero-distance core inside, so Quilez gives a
  second form that adds back the clamped interior term (the box pattern again). A capsule is an
  elongated sphere.

### 4.4 Booleans, and which are honest

For distances `a` and `b` to two shapes:

| Operation | Formula | Exactness |
|---|---|---|
| Union | `min(a, b)` | Exact **outside only**. Inside it can be badly wrong |
| Intersection | `max(a, b)` | Bound |
| Subtraction ("a minus b") | `max(a, −b)` | Bound |
| Xor | `max(min(a, b), −max(a, b))` | Exact both sides |

**The argument-order trap.** Sources disagree on subtraction's argument order. Quilez's
`opSubtraction(a, b)` removes `a` from `b`; Mercury's difference removes `b` from `a`. The house
library fixes one convention (section 12: `opSubtract(a, b)` is "a minus b") and every port from a
source must be checked against it.

**Why union is wrong inside.** Inside the union, the nearest *boundary of the union* may be a
part of one shape's surface that is buried inside the other, which does not count. Quilez's
"interior distances" article shows the field becoming nonsense in the deep interior. It rarely
hurts plain opaque rendering (normals sample near the surface), but it breaks anything that
reads the inside: refraction, thickness for subsurface scattering, inside-out rooms modelled as
"negate the union of boxes". His fixes: model the negative space instead; keep separate exact
interior and exterior models; build 2D outlines from exact segments and arcs, then revolve or
extrude; or derive one exact formula for the compound shape (his catalogue's crosses, arcs, pies
and horseshoes exist precisely for this).

**Xor is always exact.** Jakob Thomsen ("jt") noticed xor never seemed to break; Quilez proved
it. In our words: split into the four sign cases of `a` and `b`; in every case the expression
reduces to a `min` of two *non-negative* numbers (with an overall sign), and `min` of exterior
distances is exact.

### 4.5 Smooth blending: the smooth minimum

The smooth minimum `smin(a, b, k)` behaves like `min` far from where the shapes meet but melts them
together with a fillet of thickness about `k` near the junction. Quilez's article is the
definitive treatment; its structure, restated:

**The direct-difference ("DD") family.** Most smooth minima can be written as
`smin = b − k·g((b − a)/k)` for a "kernel" `g` that behaves like a softened ramp `max(x, 0)`:
it tends to 0 for very negative `x` and to `x` for very positive `x`. If `g` were exactly the ramp,
you would get plain `min`.

**Normalisation makes `k` mean something.** At the junction (`a = b`) the smooth minimum dips
below `min(a, b)` by `k·g(0)`. Dividing `k` by `g(0)` up front makes the parameter equal to the
*maximum thickening in world units*, the same across all variants. A practical bonus: the bounding
box of a smooth union is the two shapes' boxes inflated by exactly `k`.

**The clamped-difference ("CD") subfamily** forces the kernel to join the ramp perfectly at
`x = ±1` (value and slope), so the blend has *no effect at all* once the shapes are `k` apart.
Quadratic, cubic, quartic and "circular" kernels are CD; exponential, sigmoid and root kernels are
not (they slightly distort shapes everywhere; Quilez calls that lack of rigidity).

**Why smooth minima are safe to march.** The gradient of a DD smooth minimum is a weighted
average (linear interpolation) of the two input gradients, and the average of two unit vectors is
never longer than 1. So these blends never overestimate; they are conservative bounds. The cost
is that the under-estimation band stretches to infinity along the "Voronoi edge" between the two
shapes, so rays travelling along that seam slow down.

**Property table (from Quilez's analysis, restated):**

| Variant | Rigid (no effect when far apart) | Local (slow region bounded) | Conservative (never overestimates) | Order-independent |
|---|---|---|---|---|
| Quadratic polynomial | yes | no | yes | no |
| Cubic polynomial | yes | no | yes | no |
| Quartic polynomial | yes | no | yes | no |
| Circular (CD kernel) | yes | no | yes | no |
| Exponential | no | no | yes | **yes** |
| Sigmoid | no | no | yes | no |
| Root | no | no | yes | no |
| Circular-geometric (Mercury round) | yes | **yes** | **no** | yes |

Non-associativity matters in practice: `smin(a, smin(b, c))` differs from `smin(smin(a, b), c)`, so
reordering a list of blends changes the model.

**Material blending.** The same weight that blends distances can blend materials: a smooth minimum
that also returns "how much of `b`" (0 to 1) lets snow fade into stone exactly where the shapes
melt together (Quilez's bridge-and-snow example). Gradients follow the same weight, which gives
analytic normals for blended shapes without extra samples.

**History note.** Quilez derived the quadratic smooth minimum around 2011-2012 and shared it on
Shadertoy in 2013; Media Molecule (the Dreams team) later published an optimised form that he now
uses. The circular-geometric form came from Mercury's hg_sdf.

**Smooth maximum** is `−smin(−a, −b, k)`; smooth intersection and smooth subtraction follow.

### 4.6 Mercury's right-angle operators

hg_sdf takes a different view of blends. Assume the two surfaces meet at roughly a right angle.
Then `(a, b)` is a perfectly good local 2D coordinate system whose origin is the intersection
edge, and *any 2D distance function evaluated in that coordinate system shapes the edge*:

- **Chamfer:** a 45-degree flat bevel: union is `min(min(a, b), (a + b − r)·√½)`.
- **Round:** a quarter circle of radius `r` fitted into the corner (the circular-geometric blend).
- **Columns, stairs:** repeated small round or square profiles along the edge.
- **Groove, tongue, engrave, pipe:** carve a channel along the edge, raise a ridge, cut lettering-like
  grooves, or keep only a pipe along the intersection curve.

Mercury's own caveat (paraphrased from the source comments): these return correct distance
bounds only while the two gradients are near perpendicular; beyond about 30 degrees off, the
Lipschitz condition fails, worst for close parallel surfaces. Quilez's analysis of the round
variant shows it overestimates in convex regions (holes in renders) yet has the attractive
property that its slow region is bounded. His suggested remedy: let the marcher back-track by
testing `|f|` instead of `f` (section 5.6).

### 4.7 Placing things: transforms and scale

- **Rigid transforms are exact.** To place an object, apply the *inverse* of its placement to the
  sample point.
- **Uniform scale:** `s · f(p / s)`.
- **Non-uniform scale is not an SDF operation.** Use `min(scale) · f(p / scale)` as a bound, or
  better, use a primitive with the anisotropy built in (an ellipsoid bound, an elongation, a box with
  different half-sizes).

### 4.8 Symmetry and domain repetition (one object, infinitely many copies)

**Mirror symmetry.** Replace `p.x` by `|p.x|` and you model half the object; the other half
appears for free. Exact if the half does not cross the mirror plane, otherwise a bound. Mercury
generalises this into folds across arbitrary planes and octants.

**Grid repetition.** Make space periodic with period `s`: the cell index is `id = round(p / s)` and
the local coordinate is `q = p − s·id`. Evaluate the object once at `q`. The integer `id` is a free
per-instance identifier: hash it to vary size, colour, rotation, animation phase. Cost: constant,
whatever the number of copies.

**The trap, and its proper fix (Quilez's repetition article).** A point only "sees" the copy in its
own cell. If copies differ (size, rotation, jitter) or are not symmetric about the cell
boundaries, the nearest copy may be in a neighbouring cell, so the field overestimates. On screen:
holes and cracks that crawl as the camera moves, shadows with bites taken out. The fix is to also
evaluate the neighbours that *could* be closer. Only the neighbours on the near side matter (pick
them with `sign(q)`), so you need 2 cells in 1D, 4 in 2D, 8 in 3D (not 3, 9, 27). Valid while each
copy fits within half a cell of its centre; bigger copies need a wider ring.

**Mirrored repetition** (first seen by Quilez from Fizzer): flip the local coordinate in every odd
cell. Neighbouring copies become mirror images, so they meet symmetrically at every boundary and
one evaluation is exact again. Artistic constraint: alternating copies are mirrored.

**Limited repetition.** Do not intersect an infinite grid with a container box (correct picture
but a wrong, slow field). Instead clamp the cell index to the allowed range before computing `q`;
copies outside the range simply become the edge copy seen from further away. One extra line.

**Rotational (polar) repetition.** Repeat in angle around an axis: compute the angle, the sector
index, rotate the point into the sector. Because this is 1D repetition, a correct version
evaluates two sectors (current and nearest neighbour); single-evaluation versions show seams at
sector boundaries unless the content is symmetric. Quilez's reminder: on GPUs, trigonometry is
cheap, so do not contort code to avoid `atan`.

**Other parametrisations.** Anything you can parametrise you can repeat: along a rectangle's
perimeter (temple colonnades), Fibonacci points on a sphere (Quilez credits the "Spherical
Fibonacci Mapping" paper, ACM doi 10.1145/2816795.2818131), recursive grids (the Menger sponge is
repeated negative boxes).

**Precision warning (ours).** Repetition far from the origin loses floating-point precision: at a
coordinate of 10,000 a 32-bit float resolves only about a thousandth of a unit, so fine detail
inside each cell becomes stair-stepped and jittery. Keep the camera near the origin and move the
world (or wrap the camera position by a multiple of the period).

### 4.9 Deformation and procedural detail

**Twist and bend** are domain warps; correct them by their Lipschitz factor (section 3.3).
Hart's appendix and Quilez both warn they break exactness.

**Displacement** adds a pattern to the distance. Divide by `1 + A·G` or accept the risk.

**fBM detail done right (Quilez, "FBM detail in SDFs").** Adding fractal noise to an SDF is not an
SDF (sums are not distances) and fails as amplitudes or frequencies grow. His replacement: build a
noise that *is* an SDF (an infinite grid of random-radius spheres, each smaller than half a cell
so only the 8 corner spheres of the current cell need checking), then for each octave (each layer
twice the frequency, half the size): clip the new layer to a slightly inflated copy of the current
surface with a smooth maximum, and merge it in with a smooth minimum. Detail grows *on* the surface
rather than floating in space. A rotation between octaves hides grid alignment. Level of detail is
built in: stop adding octaves once the octave's size falls below the pixel footprint. Carving
(subtracting octaves) gives eroded rock. Known artefact: occasional floating fragments
("flyovers") or pinholes.

### 4.10 Materials and IDs

Return `(distance, materialId)` pairs and let the union keep the id of the nearer part. Mercury's
FAQ suggests the cheaper alternative of recording id and local coordinates in globals whenever a
part wins, then shading once at the end. Better still for cost: march with a distance-only
function and evaluate material once at the hit point.

### 4.11 The hg_sdf conventions (worth adopting as house style)

Mercury published their structure so code stays readable and reusable:

- Every distance function is named `f…`, takes the point first, is centred at the origin with y up.
- Every domain operation is named `p…`, takes the point as an in-out first argument, modifies it in
  place, and *returns the cell index* when it partitions space.
- Every combination operator is named `fOp…` and comes in union, intersection and difference
  flavours.
- Patterns: stay Lipschitz; use few primitives and combine them; multiply objects by repeating
  space ("a loop inside your distance function" is usually a mistake unless it is a fractal); at
  right-angle meetings, shape the edge in the `(a, b)` coordinate system.
- Debugging advice (paraphrased from their FAQ): sweep a plane through the scene coloured by
  distance with regular iso-lines, and visualise how far the gradient length departs from 1. That
  map shows exactly which parts of the field are broken.

## 5. The marcher

### 5.1 From pixel to ray, and the pixel footprint

A pinhole camera: for each pixel compute a point on an image plane at focal distance `F` in front
of the eye, and normalise the direction. **The direction must be unit length**, or every distance
the marcher reads is in the wrong units (it will overstep or understep by the length factor).

For later sections we need the **pixel angle** `α`: the angle one pixel subtends. With vertical
field of view `φ` and image height `H` pixels, `α ≈ 2·tan(φ/2) / H`. In the common Shadertoy setup
where the image plane spans −1 to +1 vertically at distance `F`, `α = 2 / (H·F)`. The pixel
footprint at distance `t` is about `α·t`, its radius `α·t/2`.

### 5.2 The basic sphere-tracing loop

In words:

1. Start at `t = tmin` (0 for camera rays, a small offset for secondary rays).
2. Evaluate `d = f(ro + t·rd)`.
3. If `d` is below the hit threshold, report a hit at `t`.
4. Otherwise `t ← t + d`.
5. Stop with "miss" if `t > tmax` or the step budget runs out.

**Hit threshold should grow with distance.** A fixed epsilon such as 0.001 is too strict far
away (wasted steps, sparkling noise) and arbitrary up close. Use `ε(t) = c·α·t`, a fraction of
the pixel footprint: the error is then constant *on screen*. Quilez's 2008 slides make exactly
this point (world-space error shrinks as one over distance on screen, so stepping proportionally to
distance gives constant screen-space error), and Keinert et al. stop when the unbounding sphere
is smaller than half a pixel. Quilez's primitives shader uses `|f| < 0.0001·t`
(`state/arsenal/shaders/corpus/shaders/Xds3zN/image.glsl:436`).

**Convergence.** Hart proves sphere tracing converges to the *first* root along the ray (it cannot
skip a surface if the field is a bound) and that convergence is linear in general, quadratic only
when the ray hits the surface head-on. The expensive pixels are **grazing rays near silhouettes**:
the surface is close (small steps) but the ray is not approaching it fast. Quilez's 2008 step-count
heat map of Slisesix shows exactly this: cheap interiors, expensive outlines.

**Hart's convexity speed-up.** If the nearest object is convex, the ray cannot hit it before it
reaches the tangent plane at the nearest point. So from a point where the distance is `d` and the
outward gradient is `n`, you may step `d / (−n·rd)` (the distance to that plane along the ray)
instead of `d`. If `n·rd ≥ 0` the ray is moving away and can never hit that convex object. This
behaves like Newton's method and converges much faster. The most important everyday instance is
the **ground plane**: a ray nearly parallel to the floor creeps forever by constant tiny steps, so
intersect the floor analytically and cap `tmax` with it (Quilez's primitives shader does this,
`Xds3zN/image.glsl:412-419`).

### 5.3 Over-relaxation (Keinert et al. 2014)

Step `ω·d` instead of `d`, with `ω` between 1 and 2. Most of the time the field is a loose bound
and the bigger step is still safe. Safety check: consecutive unbounding spheres must overlap. If
the previous radius plus the current radius is less than the step just taken, there is an
unexamined gap between them where a surface may hide. Then step back to where a plain step would
have landed (`t_prev + r_prev`), set `ω = 1`, and continue normally.

Measured on a GTX Titan at 1280×720 with an 80-iteration cap: a city scene went from 20.4 ms to
16.8 ms; a jewel scene from 3.47 ms to 2.98 ms; their GPU path tracer from 118 ms to 102 ms per
sample. They found `ω ≈ 1.2` best; larger values fall back too often. Hardware analogy:
overclocking with a watchdog: run fast, detect the fault cheaply, drop to stock clocks.

### 5.4 Planar extrapolation (Bálint and Valasek 2018)

Observation: the costliest case is creeping towards a nearly flat surface. Use the last two
distances to estimate the local slope and predict the next one.

Derivation (ours, matching their equation 1): suppose the surface is locally flat, so distance
falls linearly with `t` at slope `s = (r_prev − r_cur) / step_prev`. Choose the next step `D` so
that the next unbounding sphere just touches the current one: `D = r_cur + r_next`. With
`r_next = r_cur − s·D`, solving gives `r_next = r_cur·(1 − s)/(1 + s)`, and the step is
`D = r_cur + ω·r_next`. Parallel motion (`s ≈ 0`) gives nearly double steps; head-on (`s ≈ 1`)
gives ordinary steps. If the actual new radius shows the spheres do not overlap (possible missed
surface, concave case), fall back to a plain step. We checked numerically that for a flat floor the
prediction is exact.

Results: up to 50% better error-per-time than Hart's and Keinert's versions on their benchmarks;
equal to Keinert's on the Mandelbulb fractal (non-smooth fields gain little). Guard the first
iteration and the denominator.

### 5.5 Picking the best point when you run out of steps, and smoothing the result

- **Screen-space candidate selection (Keinert et al.).** Track the step where `f/t` (unbounding
  radius divided by distance, so proportional to its size on screen) was smallest. If the loop
  runs out of iterations, shade *that* point instead of the last one, which on grazing rays is
  often in mid-air behind the object. This removes the thin fringe of "wrong surface" pixels that
  hugs silhouettes when step caps are low. Same criterion, used as the stopping rule: stop when the
  radius is below half a pixel.
- **Discontinuity reduction (Keinert et al.).** Termination leaves each pixel's hit point a
  slightly different distance from the true surface, and that difference jumps between pixels;
  procedural textures read from the hit point then show contour-line artefacts. Three iterations of
  `p ← p + rd·(f(p) − err(t))`, where `err(t)` is the permitted screen-space error at that distance,
  pull every hit onto a consistent offset surface. Cheap, big visual win with textures.

### 5.6 Marchers for fields that overestimate

Sometimes you want an operator that overestimates (Mercury's local round blend, heavy
displacement, an ellipsoid stretch hack). Then:

- Test `|f|` against the threshold instead of `f`, so a ray that overshot into a solid (negative `f`)
  still stops, and step by `f` (which is negative inside) so it walks back out. Quilez suggests
  exactly this for the circular-geometric blend.
- Better, when `f` turns negative, you have bracketed the surface between the last positive and the
  current negative `t`: finish with a few bisection or secant steps.
- The 20 corpus shaders that use the `abs(h) <` test are doing the first of these (section 9).

Quilez's terrain article shows the bracket-and-interpolate idea for heightfields: when a step lands
below the terrain, interpolate linearly between the last two samples for the crossing point.

### 5.7 Secondary rays: offsets, refraction, inside-out tracing

- **Self-intersection ("acne").** A shadow or reflection ray started exactly at the hit point
  immediately reads a near-zero distance and reports a hit. Start at `tmin` a few epsilons out, or
  offset the origin along the normal.
- **Dynamic epsilon (Keinert et al.).** Because hit points stop at variable distances from the
  surface, a fixed offset is wrong. Offset by `2·max(ε_min, |f(p)|)` along the normal. Small `ε_min`
  causes numeric trouble and many tiny steps away from the surface; it is easier to tune than a
  global epsilon.
- **Tracing inside a solid** (refraction, thickness): flip the sign of the field (`−f`) so the
  interior looks like empty space and the far wall looks like a surface. Keinert's listing detects
  the starting sign automatically.
- **Convex objects in a convex bounding volume (Keinert et al.).** When a refracted ray starts
  inside the object, do not march through the interior; jump to where the ray exits the bounding
  volume and march *backwards* to the surface. About 10% faster in their glass test.

### 5.8 Cone marching: let neighbouring pixels share the empty space

**The idea (Seven/Fulcrum, Revision 2012).** Neighbouring pixels' rays start at the same point and
their first few unbounding spheres overlap almost completely, but on a GPU each pixel marches alone,
so all that shared knowledge is thrown away. Cone marching recovers it:

1. Split rendering into depth passes and a colour pass.
2. The first depth pass runs at a tiny resolution (say 1/16 or 1/32 of the final). Each low-res
   pixel is a *wide cone*. March along the cone's centre line and stop when the distance becomes
   smaller than the cone's radius at that `t`: something touches the cone, so this coarse pixel can
   say nothing more precise. Store `t`.
3. Each following pass doubles the resolution *exactly*, starts each thinner cone at the `t` stored
   by its parent, and continues. Cones that ran out of range (sky) are marked and skipped later.
4. The final pass at full resolution does ordinary marching from the inherited `t`; then colour.

Why exact doubling matters: child cones must nest inside their parent cone, or a child can start
beyond a surface that only its parent's neighbour saw. Seven's slides show a 5-pixel middle pass
skipping an object for exactly this reason. Pad the framebuffer to a multiple of 16 or 32.

Reported speed-ups (Mandelbox scenes): about 30% if the same total step budget is split over the
passes; about 50% if cheap low-res passes get generous budgets; about 100% if low-res passes get
many steps and the final pass fewer (distant open areas look deeper, dense areas lose some
precision). Four to five passes are enough; the very smallest resolutions are not worth the
framebuffer switch. Costs: primary visibility only (shadows, AO, reflections do not benefit);
early-outs show as square blocks in any "iteration glow" effect; thin details can fall between
cones; with an inexact field you may add a per-pass "thinner cone" fudge (more in the coarse
passes), trading speed against holes punched through thin parts.

**Bálint and Valasek's version** folds the cone into the field itself: marching
`F(t) = (f(ro + t·rd) − β·t) / (1 + β)`, where `β` is the cone's radius per unit distance, is a
valid 1D distance bound that stops exactly when the cone touches geometry; no special termination
test. They report up to 20% gains from a two-resolution schedule, putting about one eighth of the
iterations in the low-resolution pass.

**In production.** Sebastian Aaltonen's Claybook talks (GDC 2018; Digital Dragons 2018, which he
says covers its "coarse RT" in more detail) describe SDF ray tracing in a shipped game with a
coarse tracing stage ahead of the full-resolution one. We did not re-read those slides for this
report; treat the details as a pointer for the next study pass.

**Hardware analogy.** This is a hierarchical Z-buffer, or a mip chain for empty space: answer the
question for big tiles first and only refine where the tile was inconclusive.

### 5.9 Other accelerators (and one honest negative result)

- **Segment tracing (Galin, Guérin, Paris, Peytavie, 2020).** Instead of one global speed limit,
  compute a *local* Lipschitz bound over the next segment of the ray (they derive bounds for
  skeletal primitives and blend operators), then take the largest safe step. Large reductions in
  field evaluations for blended implicit scenes. (Abstract-level reading for this report.)
- **Non-linear sphere tracing (Seyb, Jacobson, Nowrouzezahrai, Jarosz, SIGGRAPH Asia 2019).** To
  render a deformed SDF without the Lipschitz penalty, trace a *curved* ray through the undeformed
  space. (Title and abstract only for this report.)
- **Binary-search ray partitioning (Quilez, 2018/2022).** Test the middle of the ray segment: if the
  distance there exceeds half the segment length, the whole segment is empty; otherwise split and
  recurse, front half first (later made stackless with node-number arithmetic, after Archee's and
  "fad"'s shaders; Nicolas Klenert's refinement shrinks segments by the measured empty space). It
  works, but uses *more* field evaluations than the plain loop. Quilez's conclusion: the naive loop
  is hard to beat for single rays; gains come from sharing work across rays (cones, packets) or
  from culling work inside the field (bounding volumes).

### 5.10 Bounding volumes and analytic accelerators

The marcher's cost is steps × cost of one field evaluation. Bounding volumes cut the second factor.

**Early skip (Quilez, "SDF bounding volumes").** Before evaluating an expensive part, compute the
distance to a cheap shape that encloses it (sphere, box). If that bound distance is already larger
than the best distance found so far, the part cannot win: skip it. Variants:

- Reuse a primitive the part already contains, inflated, as its own bound (Quilez reports an 8×
  speed-up on his Happy Jumping character, `3lsSzf`).
- Half-spaces as bounds for infinite things: a plane above the tallest pebble bounds the ground.
- Recursive bounds and full bounding-volume hierarchies (BVHs) or k-d trees for very complex fields
  (triangle meshes as SDFs). His one-night experiments: a BVH over a mesh runs a Stanford Bunny at
  full frame rate on a GeForce 1070; a procedural k-d tree was workable but slow. Branches and
  stack registers are expensive on WebGL and mobile, so do not over-nest.
- Quilez's primitives shader wraps each row of objects in a box test (`Xds3zN/image.glsl:347-384`).

**Hart's triangle-inequality cache.** Keep each object's last distance. As the ray advances by
`Δ`, that object's distance can have shrunk by at most `Δ`. So `old − Δ` is a free lower bound;
only re-evaluate objects whose lower bound could be the minimum. Hart measured more than double the
convergence rate on many-object scenes, 60% combined with the convexity step.

**Analytic range clipping.** Intersect the ray analytically with the scene's bounding box and the
ground plane first, and march only inside `[tmin, tmax]`; skip the march entirely on a miss
(`Xds3zN/image.glsl:425-430`). Keinert's path tracer also traces walls and mirror spheres
analytically and marches only the SDF parts.

**Analytic intersection formulas** (derive once, reuse forever; Quilez's "intersectors" page lists
twenty):

- **Sphere** centre `c`, radius `r`: let `oc = ro − c`, `b = oc·rd`, `q = oc − b·rd` (the vector from
  the centre to the closest point on the ray). Then `h = r² − q·q`; miss if `h < 0`; otherwise
  `t = −b ± √h`. Computing `h` from the perpendicular `q` instead of `b² − (oc·oc − r²)` avoids
  subtracting two huge numbers, so it keeps precision for small spheres seen from far away
  (Quilez's precision note, restated).
- **Box** (in box space, half-size `b`), the slab method: per axis the ray is inside the slab
  between `t = (−b − ro)/rd` and `t = (b − ro)/rd`; the entry is the largest of the per-axis entries,
  the exit the smallest of the per-axis exits; hit if entry < exit and exit > 0. Precompute `1/rd`
  when many boxes share axes.
- **Plane** `n·p + h = 0`: `t = −(n·ro + h)/(n·rd)`, valid when positive.

### 5.11 GPU realities

- **Divergence: the convoy rule.** GPUs run pixels in lockstep groups (32 or 64 lanes). A group
  finishes when its *slowest* pixel finishes, so one grazing silhouette ray holds up its neighbours.
  Keinert et al. flag this as the open problem; cone marching and bounding volumes help because
  they shorten the worst rays.
- **Compile-time blow-up.** The normal estimator calls the scene function 4-6 times; the compiler
  may inline it each time, multiplying code size and sometimes crashing WebGL compilers. Thomas
  Hooper's trick (Clément "Klems" Baticle's variation is widely used): put the calls in a loop
  whose start is a value the compiler cannot know is zero (e.g. `min(frame, 0)`), so the scene
  function is compiled once. Eleven corpus shaders use it (section 9).
- **This host's watchdog.** Windows resets a GPU that does not finish a frame within about two
  seconds (TDR), and this machine has an AMD display-driver crash history. A raymarcher is exactly
  the kind of shader that can blow that budget: high resolution × hundreds of steps × an expensive
  field, or an uncapped loop. House floor 4 in `.claude/skills/shader-craft/SKILL.md`: cap steps,
  keep canvases small, never add a raymarcher casually. Every loop in our library has a hard
  iteration cap as a parameter.

## 6. Shading from the field

The field is a free spatial query: "how much room is there around this point in this direction?"
That single question powers normals, shadows, occlusion and thickness.

### 6.1 Normals

The normal is the normalised gradient, estimated by finite differences.

- **Central differences:** six samples, `f(p ± h·axis)` per axis. Unbiased.
- **Forward differences:** four samples. Biased (shading shifts slightly).
- **Tetrahedron technique** (seen by Quilez from Paulo Falcão on Pouet around 2008, then Paul Malin
  on Shadertoy): four samples at the corners of a regular tetrahedron, `k₁ = (1,−1,−1)`,
  `k₂ = (−1,−1,1)`, `k₃ = (−1,1,−1)`, `k₄ = (1,1,1)`. Why it works (our derivation): expand each sample
  to first order, `f(p + h·kᵢ) ≈ f(p) + h·kᵢ·∇f`. Then `Σ kᵢ·f(p + h·kᵢ) ≈ f(p)·Σkᵢ + h·(Σ kᵢkᵢᵀ)·∇f`.
  For this tetrahedron `Σkᵢ = 0` and `Σ kᵢkᵢᵀ = 4·I` (we checked), so the sum is `4h·∇f`: a
  central-difference-quality gradient for the price of forward differences.

**Choose `h` from the pixel footprint, not a constant.** Quilez's normals article shows the
difference dramatically on distant cliffs: a constant tiny `h` samples detail far smaller than a
pixel, so distant normals shimmer (aliasing); a constant large `h` blurs the foreground. Use
`h ≈ α·t` (a pixel's width at the hit). This is a cheap form of level of detail.

**Heightfield terrains** (`y = g(x, z)`): the normal is the normalised
`(g(x−h) − g(x+h), 2h, g(z−h) − g(z+h))`, four height samples.

**Analytic gradients** are faster when available; Quilez publishes "distance plus gradient"
versions of many primitives, and the smooth minimum's gradient is the blend weight applied to the
two input gradients.

### 6.2 Soft shadows

**Hard shadow:** sphere-trace from the surface point toward the light; any hit means shadow.

**Penumbra for free (Quilez).** While marching the shadow ray, the ratio `h/t` (distance to the
nearest surface over distance travelled) is approximately the *angle* by which the ray clears that
occluder, as seen from the shading point. A light of angular radius `θ_L` is fully visible only if
every occluder clears by more than `θ_L`. So the shadow factor `min over steps of (k·h/t)`,
clamped to `[0, 1]`, estimates the visible fraction of the light with `k ≈ 1/tan θ_L` (our reading
of his "k is inversely related to light size" observation). Calibration: `k = 8` is a big soft light
about 7 degrees in radius; the real sun (about 0.27 degrees) is `k ≈ 215`. Contact shadows come out
sharp and distant ones soft, as in reality, from a single ray.

**Aaltonen's improvement (GDC 2018).** Sampling only at the step points misses the true closest
approach between steps, which shows up as light leaking in bands that match the step pattern,
especially behind sharp corners. Use the previous and current unbounding circles: their
intersection estimates where the nearest surface is. Derivation (ours): with the previous circle of
radius `r₁` centred one step (`r₁`) behind the current point, and the current circle of radius `r₂`,
the circles meet at a distance `y = r₂²/(2r₁)` behind the current point, at a half-chord height
`d = √(r₂² − y²)`. Use `d / (w·(t − y))` as the penumbra sample, with `w` the light size. Quilez's
reference implementation is the corpus shader "Soft Shadow Variation" (`lsKcDD`).

**Inner penumbra (nurof3n, extended by Quilez).** Let the shadow ray continue *through* thin
occluders (step by a clamped positive amount rather than `h`), allow the penumbra term to go
negative (to −1) inside geometry, and remap the range `[−1, 1]` with a smoothstep. Shadows then get
both outer and inner penumbrae and look close to a ground-truth area light.

**Practicalities.** Clamp the shadow step between a minimum (avoid stalling near surfaces) and a
maximum (avoid leaping over thin occluders); Quilez's primitives shader clamps to `[0.01, 0.2]` and
takes 24 steps (`Xds3zN/image.glsl:449-466`). Cap `tmax` with an analytic plane above the scene
(line 452). Shadows depend on the field being *calibrated*: bounds make shadows too dark and too
wide (the ellipsoid article's broken cap shadows).

### 6.3 Ambient occlusion from the field

Alex Evans' trick (2006), popularised by Quilez in 2008: walk a few steps out along the normal. At
distance `δᵢ` along the normal, an unoccluded surface reads `f = δᵢ`; nearby geometry makes it read
less. Sum the shortfalls with decaying weights (nearer samples matter more):
`occ = Σ wᵢ·(δᵢ − f(p + n·δᵢ))`, `AO = clamp(1 − K·occ, 0, 1)`. Five samples. In Quilez's 2008
numbers, primary rays to AO cost about 3 to 1, versus about 1 to 2000 for a ray-traced AO in a
conventional renderer. It is a 3D query, not the screen-space trick. Corpus reference:
`Xds3zN/image.glsl:493`.

### 6.4 Thickness, proximity and "painted" lighting

- **Thickness / fake subsurface scattering:** march a short distance *into* the object (negated
  field) to estimate how thick it is; thin parts glow (Quilez's "Cell", 2013).
- **Proximity-driven materials:** the field tells every point how close other geometry is; use it to
  grow moss, wetness or snow in crevices (Quilez's k-d tree Sponza experiment).
- **Painted light:** many of Quilez's best images fake bounce light by hand-placed colour terms and
  a three-light rig (key, fill, bounce) rather than computing global illumination. That is an
  artistic choice the house should respect: physically wrong, deliberately beautiful.

### 6.5 Texturing and filtering: ray differentials

GPUs pick texture mip levels from pixel-to-pixel differences (`dFdx`, `dFdy`) computed on 2×2 pixel
quads. In a raymarcher, neighbouring pixels can hit different objects, so at silhouettes those
differences are huge and the GPU picks the blurriest mip: a dark or wrong-coloured outline around
every object. Quilez's fix ("ray differentials and textures"): also build the rays through the
right and upper neighbour pixels, intersect them with the *tangent plane* at the hit point, and
use the differences of those analytic hits as the derivatives (perspective camera:
`dP/dx = t·(rdₓ·(rd·n)/(rdₓ·n) − rd)`, same for y). Pass them to an explicit-gradient texture fetch.
Chain-rule them through your texture mapping (planar, triplanar). Quilez's primitives shader uses
the same footprint to filter its checkerboard analytically (`Xds3zN/image.glsl:509, 519`).

This is also house floor 6 in shader-craft: derivatives only of continuous quantities; a
derivative of a cell id or of anything downstream of a marched silhouette shreds rows.

## 7. Antialiasing silhouettes

### 7.1 The problem

One ray per pixel is a point sample. Edges stair-step and, worse, thin or distant features flicker
as the camera moves. Supersampling (2×2 or 3×3 rays per pixel, `Xds3zN/image.glsl:623`) fixes it at
4-9 times the cost.

### 7.2 Hart's cone-traced coverage (1996)

Hart showed sphere tracing almost gives you cone tracing (after John Amanatides' 1984 cone
tracing) for free at silhouettes:

1. Treat the pixel as a cone whose radius at distance `t` is the pixel radius `r_p(t)`.
2. A grazing ray's unbounding spheres shrink, slip inside the cone's radius, then grow again as the
   ray passes the object. The point where the sphere was smallest *relative to the pixel* is the
   best "representative" sample of the near miss.
3. Assume the surface is locally flat at the pixel's scale. Then the fraction of the pixel disk
   covered is the area of a disk of radius `r` cut by a straight edge at signed distance `d` from the
   centre. With `x = d/r` clamped to `[−1, 1]`, the covered fraction on the far side is
   `(arccos x − x·√(1 − x²)) / π`. (A plain smoothstep from −1 to 1 approximates it within about
   0.04; a linear ramp of slope 2/π within about 0.06; we checked both.)
4. Treat that coverage as opacity, shade the representative point, and keep marching (Hart steps
   by `f + r_p`, tracing the "inner cover" offset surface). Composite the near-misses and the final
   hit front to back (Porter-Duff "over").

Hart notes the limits: it only fixes silhouette (geometric) aliasing, not texture aliasing, and
with a loose *bound* the spheres may shrink below the pixel too early; a local estimate like
`f/|∇f|` is a better coverage distance there.

### 7.3 Quilez's "Antialias, sort of" (2014, `llXGR4`)

Same principle with ray differentials: at each near-intersection estimate how much of the pixel's
footprint the geometry covers, then composite the partial coverages front to back. One ray, smooth
edges.

### 7.4 Cheap partial fixes

Keinert's best-candidate selection (5.5) removes the worst silhouette fringes. Footprint-sized
normal epsilon (6.1) and filtered textures (6.5) remove shading aliasing. Level-of-detail cut-offs
in fractal detail (4.9) remove geometric aliasing at the source. Temporal accumulation is outside
this topic.

## 8. Common mistakes and what they look like on screen

| What you see | Likely cause | Fix |
|---|---|---|
| Holes, missing slabs, background showing through solid objects; worse when moving | Field **overestimates**: non-uniform scale, displacement or twist without Lipschitz correction, naive repetition of varying/rotated copies, Mercury round blend, wrong `opSubtract` order | Correct by the Lipschitz factor; neighbour-checked or mirrored repetition; backtracking marcher (`abs` test plus bisection) |
| A thin halo or "skin" of floor colour or wrong normals hugging silhouettes | Step budget runs out on grazing rays; shading the last point (in mid-air) | Raise steps; best-candidate selection; analytic range clipping; over-relaxation |
| Distant objects vanish into a band of misses or sky | Step cap too low, or fixed epsilon too small far away | `ε ∝ t`; cone marching; more steps for coarse passes |
| Bloated, blobby or merged details near the camera; gaps where things touch | Epsilon too large up close | Footprint-scaled epsilon with a small floor |
| Sparkle, noise, shimmering normals on distant detail | Normal epsilon constant and tiny; sampling sub-pixel detail | `h ∝ α·t`; LOD cut-off for detail octaves |
| Soft, mushy edges and wrong lighting on thin features | Normal epsilon too large | Smaller `h`, footprint-based with a cap |
| Black speckles or moiré on lit surfaces | Shadow/reflection rays start inside the surface (acne) | `tmin` offset, or offset origin along the normal by `2·max(ε_min, |f|)` |
| Light leaking through shadows in bands that follow the march steps, worst at sharp corners | Soft shadow misses the closest approach between samples | Aaltonen's two-circle estimate; clamp shadow step size |
| Shadows too dark and too wide, AO too strong around some objects | Those parts of the field are loose bounds (ellipsoid stretch, heavy smooth unions) | Tighter bounds (gradient-normalised ellipsoid); exact primitives |
| Cracks or slices at grid-cell boundaries; copies cut off by invisible planes | Repetition with copies bigger than half a cell, asymmetric, or varied per cell | 2ⁿ neighbour evaluation; mirrored repetition; larger cells |
| Seams at fixed angles around a rotational pattern | Single-evaluation polar repetition with asymmetric content | Evaluate two sectors |
| Contour-line or "terraced" artefacts in procedural textures | Hit points sit at varying distances from the surface | Keinert discontinuity reduction (3 fixed-point iterations) |
| Dark one-pixel outline around objects on textured surfaces | Hardware derivatives across depth discontinuities pick the smallest mip | Ray differentials and explicit-gradient fetches |
| Refraction, thickness or inside-out rooms look nonsensical | Union (`min`) interior is not a distance field | Model the negative space; exact compound primitives; xor where it fits |
| Fine detail turns jittery or stair-stepped far from the origin | 32-bit float precision at large coordinates | Keep the camera near the origin; wrap positions by the repetition period |
| Rendering slows to a crawl near the horizon | Rays parallel to the ground creep by tiny steps | Intersect the ground plane analytically; Hart's convex step |
| The shape changes when you reorder blends | Smooth minima are not associative | Fix the order, or use the exponential blend where order must not matter |
| Shader takes ages to compile or crashes in the browser | Scene function inlined many times by the normal/AO code | Non-constant-zero loop start (Hooper/Klems) |
| Whole screen black or inverted | Camera starts inside a solid; ray direction not normalised; plane normal not unit | Check `f(ro)` sign; normalise; flip the field for inside tracing |
| `t += d * 0.5` "fixes" the holes and halves the frame rate | A fudge factor hiding a broken field | Find and fix the overestimating operator (Mercury's rule) |
| Display driver resets on this host | Uncapped or huge loop × resolution × field cost | Hard caps, small canvas, bounding volumes (shader-craft floor 4) |

## 9. Debugging and dissection kit

### 9.1 Views every bench should offer

1. **Step-count heat map.** Colour each pixel by how many steps it took. Shows silhouette cost,
   horizon creep, and whether an accelerator helped. (Quilez's 2008 Slisesix map; Keinert's
   figures.)
2. **Distance slice.** Sweep a plane through the scene; colour by sign, draw iso-lines every fixed
   distance. Broken fields show discontinuous or bunched iso-lines (Quilez's repetition article uses
   exactly this view to show the incorrect field).
3. **Gradient-length error.** Colour `|∇f| − 1`: positive means the field is changing faster than a
   distance can (overestimate risk), negative means a loose bound (slow marching). Mercury's FAQ
   names this the most useful single diagnostic.
4. **Overshoot counter.** Count the steps on which `f` came back negative. Non-zero means the field
   overestimates somewhere along that ray.
5. **Hit-distance error.** `f` at the final hit point, scaled up (Keinert's figure 9). Shows where
   discontinuity reduction is needed.

### 9.2 Corpus fingerprints (for the import tool)

We ran a small read-only census over the 324 shaders in `state/arsenal/shaders/corpus/shaders/`
(regular-expression matches on `image.glsl`; indicative, not exhaustive). These patterns are good
first-pass tags for "what techniques does this shader use":

| Fingerprint | What it indicates | Corpus hits |
|---|---|---|
| `calcNormal` / `getNormal` names | SDF marcher with numeric normals | 41 |
| tetrahedron offsets (`.xyy` style swizzles with `k`/`e`) | tetrahedron or central-difference normals | 38 |
| `smin` / smooth union names | smooth blending | 34 |
| `bound` words | hand bounding volumes | 33 |
| `mod(p…` / `round(p/s)` | domain repetition | 21 / 1 |
| `abs(h) <` termination | backtracking-tolerant marcher | 20 |
| `softshadow` names | field soft shadows | 19 |
| `calcAO` names | field ambient occlusion | 19 |
| `dFdx` / `fwidth` | screen derivatives (audit these at silhouettes) | 18 |
| `sdBox` / `sdSphere` | iq-style primitive vocabulary | 17 / 17 |
| `min(iFrame, 0)` | anti-inlining loop trick | 11 |
| `t += d * 0.x` | understep fudge factor (smell: broken field) | 11 |
| `sdTorus` / capsule | primitive vocabulary | 10 / 7 |
| `atan` then `mod`/`floor` | polar repetition | 10 |
| `iBox` / `iSphere` | analytic intersectors as accelerators | 4 |
| `pMod…` / `fOp…` | Mercury hg_sdf vocabulary | 2 / 3 |
| `omega` / relax | over-relaxation (rare in the corpus) | 4, mostly verbal |

Suggested tag set for the import UI: `sdf.exact-primitives`, `sdf.smooth-blend`, `sdf.repetition`,
`sdf.repetition-polar`, `sdf.deform`, `march.basic`, `march.backtrack`, `march.fudge-factor`,
`march.relaxed`, `accel.bounding`, `accel.analytic`, `light.normals-tetra`, `light.softshadow`,
`light.ao`, `aa.supersample`, `aa.cone`, `filter.ray-differentials`, `compile.anti-inline`.

## 10. Cost model and budgets

`frame cost ≈ pixels × (primary steps + shading queries) × cost(field)`.

- Quilez's 2008 numbers for Slisesix at 1280×720: about 50 million field evaluations per image;
  60% for primary rays (about 17 steps per ray on average), 40% for lighting and shading.
- Shading queries per hit: normal 4 (tetrahedron) or 6; AO 5; each soft shadow 16-64; each
  reflection a full extra march.
- Typical caps in good shaders: primary 64-128 steps (Quilez's primitives shader: 70 inside a
  clipped range), shadows 16-32, AO 5.
- Best levers in order: (1) shrink `cost(field)` with bounding volumes and exact primitives;
  (2) shrink the march range analytically; (3) footprint-scaled epsilon; (4) cone/coarse passes for
  primary rays; (5) over-relaxation or planar extrapolation; (6) only then, fewer pixels.

## 11. What the best practitioners actually do

- **Quilez:** exact primitives first, the smallest possible distortion last; quadratic smooth
  minimum as the default blend (his reasons: it is cheap, its fillet is nearly circular, and it is
  conservative); domain repetition with per-cell ids for all multitudes (plants inside plants, piano
  keys, freckles); bounding volumes reused from the model's own primitives; footprint-aware
  epsilons, normals and textures; soft shadows and field AO, then painted bounce light; supersample
  only when the budget allows. He is also candid that he will make a shader 4× slower for a 10%
  prettier image when it is art, not a product.
- **Mercury:** treat the field as a contract (every `f…` returns a valid bound); give operators
  names and consistent signatures; shape edges in the `(a, b)` plane; visualise gradient error.
- **Keinert et al.:** keep the field honest and spend cleverness in the marcher: relax steps,
  choose the best candidate, refine hits.
- **Demosceners (Seven, Fizzer and others):** share work between neighbouring pixels (cone
  marching), and make repetition exact by symmetry (mirrored cells).
- **Shadertoy craft:** anti-inlining loops (Hooper, Klems); `abs`-tolerant termination for fields
  that are knowingly inexact; clamped step sizes in shadows.

## 12. The primitive API for the house library

### 12.1 Naming law (the exactness contract is in the name)

| Prefix | Meaning | Promise |
|---|---|---|
| `sd…` | exact signed distance | equals the true distance (inside and outside unless noted) |
| `ud…` | exact unsigned distance | equals the true distance, no inside |
| `sb…` | signed bound | never exceeds the true distance; zero set exact |
| `op…` | combines distances | tagged **E** exact, **EO** exact outside only, **B** bound, **X** may overestimate |
| `dom…` | domain transform | returns or modifies the point; returns cell/sector id where it partitions space |
| `lift…` | 2D-to-3D lifting | exact if the 2D input is exact |
| `rm…` | ray marching | hard iteration cap is always a parameter (TDR floor) |
| `ix…` | analytic ray intersection | returns `(tNear, tFar)` or a miss sentinel `vec2(-1.0)` |
| `bv…` | bounding helpers | conservative culling decisions |
| `lt…` | light queries from the field | results in `[0, 1]` unless noted |
| `aa…` | coverage and antialiasing | coverage in `[0, 1]` |
| `cam…` | camera and pixel footprint | |
| `dbg…` | diagnostic views | never shipped in a live surface |

Library rules:

- GLSL ES 3.00, `precision highp float` (shader-craft floor 1).
- Scene-dependent modules (`rm…`, `lt…`, `aa…`, `dbg…`) call a host-provided
  `float sceneSDF(vec3 p);` declared by prototype before inclusion. GLSL has no function
  pointers, so neighbour-correct repetition is exposed as "candidate" functions the caller loops
  over (`k` from 0 to 7) taking the minimum.
- `op…` argument order: `opSubtract(a, b)` is **a minus b** everywhere. Sources with the other
  order must be flipped on port.
- Smooth-blend `k` is always the **blend thickness in world units** (normalised).
- Every `rm…`, `lt…` loop starts from a non-constant zero (anti-inlining) and takes an explicit step
  cap.
- Each function becomes one `design/vfx-chunks`-style file with the `//! {JSON}` header; proposed
  `cat` values: `shape` (sd/ud/sb/lift), `field` (op), `domain` (dom), plus new `march`, `light`,
  `accel`, `aa`, `debug` (house currently has blend, colour, domain, field, frame, mask, math,
  motion, noise, shape, tone).

### 12.2 Signatures and contracts

**Camera and footprint (`cam`, cat `math`)**

| Signature | Contract |
|---|---|
| `float camPixelAngle(float fovY, float heightPx)` | Angle in radians subtended by one pixel at screen centre; footprint at distance `t` is `t·angle`. |
| `vec3 camRay(vec2 fragCoord, vec2 resolution, mat3 camToWorld, float focal)` | Unit-length world-space ray direction through the pixel centre. |
| `void camFootprint(vec3 rd, vec3 rdx, vec3 rdy, vec3 nor, float t, out vec3 dPdx, out vec3 dPdy)` | World-space pixel footprint at a hit, from neighbour rays intersected with the tangent plane; feeds explicit-gradient texture fetches. |
| `float dot2(vec3 v)` | Squared length; helper for single-square-root formulas. |

**Exact and bounded shapes (`sd`, `ud`, `sb`, cat `shape`)**

| Signature | Contract |
|---|---|
| `float sdSphere(vec3 p, float radius)` | Exact. Centred at origin. |
| `float sdBox(vec3 p, vec3 halfSize)` | Exact inside and outside. |
| `float sdRoundBox(vec3 p, vec3 halfSize, float cornerRadius)` | Exact; outer extent stays `halfSize`, edges rounded by `cornerRadius`. |
| `float sdBoxFrame(vec3 p, vec3 halfSize, float barHalfWidth)` | Exact; the 12 edges of a box as square bars. |
| `float sdPlane(vec3 p, vec3 unitNormal, float offset)` | Exact only if `unitNormal` has length 1 (caller's duty). |
| `float sdTorusY(vec3 p, float ringRadius, float tubeRadius)` | Exact; ring in the xz plane. |
| `float sdCapsule(vec3 p, vec3 a, vec3 b, float radius)` | Exact; segment `a→b` inflated by `radius`. |
| `float sdCylinderY(vec3 p, float radius, float halfHeight)` | Exact capped cylinder along y. |
| `float sdConeCappedY(vec3 p, float halfHeight, float radiusBottom, float radiusTop)` | Exact frustum along y. |
| `float sdRoundConeAB(vec3 p, vec3 a, vec3 b, float radiusA, float radiusB)` | Exact; two spheres joined by their tangent cone. |
| `float sdHexPrismZ(vec3 p, float apothem, float halfDepth)` | Exact hexagonal prism along z. |
| `float sdOctahedron(vec3 p, float size)` | Exact (not the cheap planar bound). |
| `float udTriangle(vec3 p, vec3 a, vec3 b, vec3 c)` | Exact unsigned distance to a triangle. |
| `float sbEllipsoid(vec3 p, vec3 radii)` | Bound, gradient-normalised (tight near the surface); zero set exact. |
| `float sbPolyhedron(vec3 p, float radius, int solidKind)` | Bound; Platonic/Archimedean solids from face-normal sets (generalised distance functions, after Akleman and Chen, as used by Mercury). |
| `float sd2Box(vec2 p, vec2 halfSize)` | Exact 2D box; input for lifting. |
| `float ud2Segment(vec2 p, vec2 a, vec2 b)` | Exact unsigned 2D segment distance (house already has `segD`). |

**Lifting and exact modifiers (`lift`, `op`, `dom`, cat `shape` / `field`)**

| Signature | Contract |
|---|---|
| `vec2 liftRevolveY(vec3 p, float offset)` | Returns the 2D point at which to evaluate a 2D SDF so the shape is revolved about y; exact if the 2D SDF is. |
| `float opExtrude(float dist2D, float z, float halfDepth)` | Exact extrusion of a 2D distance along z. |
| `vec3 domElongate(vec3 p, vec3 halfLength, out float interiorTerm)` | Point to evaluate the base shape at; add `interiorTerm` to its result for exact interior distances. |
| `float opRound(float d, float radius)` | `d − radius`; exact if `d` is exact. |
| `float opOnion(float d, float thickness)` | Hollow shell of given thickness; exact if `d` is exact. |
| `float opUniformScale(float dAtScaledPoint, float scale)` | Caller evaluates the shape at `p/scale`; returns the corrected distance. Exact. |

**Combination (`op`, cat `field`)**

| Signature | Contract |
|---|---|
| `float opUnion(float a, float b)` | EO: exact outside, unreliable deep inside. |
| `float opIntersect(float a, float b)` | B. |
| `float opSubtract(float a, float b)` | B. **a minus b.** |
| `float opXor(float a, float b)` | E: exact inside and outside. |
| `vec2 opPick(vec2 a, vec2 b)` | `(distance, materialId)` union keeping the nearer id; EO. |
| `float opSmin(float a, float b, float k)` | Quadratic CD smooth union; `k` = blend thickness (world units); B, conservative, rigid, order-dependent. |
| `vec2 opSminMix(float a, float b, float k)` | As `opSmin`, plus `.y` = weight of `b` in `[0, 1]` for blending materials and gradients. |
| `float opSminCircular(float a, float b, float k)` | CD smooth union with an exactly circular fillet between perpendicular surfaces; B, conservative. |
| `float opSminExp(float a, float b, float k)` | Exponential smooth union; order-independent; non-rigid (slightly distorts shapes everywhere); B. |
| `float opSmax(float a, float b, float k)` | Smooth intersection, `−opSmin(−a, −b, k)`; B. |
| `float opSsubtract(float a, float b, float k)` | Smooth "a minus b"; B. |
| `float opChamferUnion(float a, float b, float radius)` | 45-degree bevel; bound only when surfaces meet near 90 degrees (within about 30). |
| `float opRoundUnionLocal(float a, float b, float radius)` | Circular-geometric local fillet; X: overestimates in convex regions, needs `rmBacktrack`. |
| `float opStairsUnion(float a, float b, float radius, float steps)` | Stepped fillet in the `(a, b)` plane; same right-angle caveat. |
| `float opGroove(float a, float b, float depth, float width)` | Cut a channel of `b`'s profile into `a`; right-angle caveat. |
| `float opDisplace(float d, float displacement, float displacementLipschitz)` | `(d + displacement) / (1 + displacementLipschitz)`; B if the Lipschitz figure is honest. |

**Domain (`dom`, cat `domain`)**

| Signature | Contract |
|---|---|
| `vec3 domRigid(vec3 p, mat3 rotation, vec3 position)` | Point in object space for an object placed by `rotation` then `position`; exact. |
| `vec3 domMirror(vec3 p, vec3 axisMask)` | `abs()` on axes where the mask is 1; exact if content does not cross the planes, else B. |
| `float domReflect(inout vec3 p, vec3 unitNormal, float offset)` | Fold across an arbitrary plane; returns which side the point came from (±1). |
| `vec3 domRepeat(inout vec3 p, vec3 period)` | Infinite grid; returns cell id. Single evaluation: exact only for identical, cell-symmetric content. |
| `vec3 domRepeatLimited(inout vec3 p, vec3 period, vec3 idMin, vec3 idMax)` | Finite grid by clamping the id; same symmetry caveat; field correct outside the grid. |
| `vec3 domRepeatCandidate(vec3 p, vec3 period, int k, out vec3 cellId)` | Local point for the k-th (0..7) of the cells that can host the nearest copy; caller mins 8 results; correct for varied or asymmetric copies within half a cell. |
| `vec3 domRepeatMirror(inout vec3 p, vec3 period)` | Grid with every other cell mirrored (Fizzer); single evaluation, boundaries match; returns cell id. |
| `float domPolar(inout vec2 p, float count)` | Rotational repetition into one sector; returns sector id; single evaluation, symmetric content only. |
| `vec2 domPolarCandidate(vec2 p, float count, int k, out float sectorId)` | k = 0, 1: the two sectors that can host the nearest copy; caller takes the min. |
| `vec3 domTwistY(vec3 p, float rate)` | Twist about y by `rate` radians per unit; pair with `lipTwist`. |
| `float lipTwist(float rate, float maxRadius)` | Stretch factor `(k·R + sqrt(k²R² + 4))/2`; divide the twisted distance by it (valid within `maxRadius`). |
| `vec3 domBendX(vec3 p, float rate)` | Bend in the xy plane; pair with `lipTwist(rate, maxExtent)` (same shear bound). |
| `float sbFbmDetail(vec3 p, float hostDistance, float footprint, int maxOctaves)` | Grows sphere-grid SDF octaves onto the host with smooth max/min; stops when an octave is smaller than `footprint`; B within smooth-op limits; may create small flyovers. |

**Marching (`rm`, cat `march`)**

| Signature | Contract |
|---|---|
| `float rmEpsilon(float t, float pixelAngle, float epsMin)` | Hit threshold `max(epsMin, c·pixelAngle·t)`; constant screen-space error. |
| `vec4 rmSphereTrace(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, int maxSteps)` | Hart sphere tracing; returns `(t, steps, bestScreenError, hitFlag)`; requires a bound field. |
| `vec4 rmRelaxed(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, float omega, int maxSteps)` | Keinert over-relaxation with overlap check and fallback, plus best-candidate selection; same return layout. `omega` around 1.2. |
| `vec4 rmPlanar(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, float omega, int maxSteps)` | Bálint-Valasek planar extrapolation with fallback; same return layout. |
| `vec4 rmBacktrack(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, int maxSteps, int bisectSteps)` | For fields that may overestimate: `abs` termination, then bisection inside the bracket on a sign change. |
| `float rmRefine(vec3 ro, vec3 rd, float t, float pixelAngle, int iters)` | Keinert discontinuity reduction; returns refined `t` (3 iterations recommended). |
| `vec2 rmConePass(vec3 ro, vec3 rd, float tStart, float tMax, float coneSlope, int maxSteps)` | One coarse cone-marching pass; returns `(t, status)` where `t` is a safe start for child pixels, status 0 touched / 1 out of range. Passes must double resolution exactly. |
| `vec3 rmSecondaryOrigin(vec3 p, vec3 nor, float fAtHit, float epsMin, float side)` | Self-intersection-free origin: offset `2·max(epsMin, |f|)` along the normal (`side` = +1 out, −1 in). |

**Analytic accelerators (`ix`, `bv`, cat `accel`)**

| Signature | Contract |
|---|---|
| `vec2 ixSphere(vec3 ro, vec3 rd, vec3 centre, float radius)` | Entry and exit `t`, precision-friendly perpendicular form; `vec2(-1.0)` on miss. |
| `vec2 ixBox(vec3 roLocal, vec3 rdLocal, vec3 halfSize, out vec3 entryNormal)` | Slab-method entry and exit in box space; `vec2(-1.0)` on miss. |
| `float ixPlane(vec3 ro, vec3 rd, vec3 unitNormal, float offset)` | Hit distance, or −1 if parallel or behind. |
| `vec2 rmClipToBox(vec3 ro, vec3 rd, vec3 centre, vec3 halfSize, vec2 tRange)` | Narrows the march range to the box; `x > y` means skip marching. |
| `bool bvCanSkip(float boundDistance, float bestSoFar)` | True when the enclosed part cannot beat the current best; conservative. |

**Lighting from the field (`lt`, cat `light`)**

| Signature | Contract |
|---|---|
| `vec3 ltNormal(vec3 p, float h)` | Tetrahedron 4-tap gradient, normalised; anti-inlining loop; pass `h ≈ pixelAngle·t`. |
| `vec3 ltNormalCentral(vec3 p, float h)` | 6-tap central differences; reference and debug. |
| `float ltSoftShadow(vec3 ro, vec3 rd, vec2 tRange, float lightAngle, int maxSteps)` | Penumbra visibility in `[0, 1]` using Aaltonen's two-circle closest-approach estimate; `lightAngle` = light's angular radius. |
| `float ltSoftShadowInner(vec3 ro, vec3 rd, vec2 tRange, float lightAngle, vec2 stepClamp, int maxSteps)` | Inner-and-outer penumbra variant (nurof3n / Quilez), smooth remap over `[−1, 1]`. |
| `float ltAO(vec3 p, vec3 nor, float reach, float falloff)` | Five-sample field ambient occlusion in `[0, 1]` (1 = open). |
| `float ltThickness(vec3 p, vec3 inwardDir, float reach, int steps)` | Approximate material thickness by marching the negated field; for fake translucency. |

**Antialiasing (`aa`, cat `aa`)**

| Signature | Contract |
|---|---|
| `float aaDiskCoverage(float signedDistance, float pixelRadius)` | Exact fraction of a pixel disk covered by a straight edge at that signed distance (inside negative). |
| `int aaCoverageLayers(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, int maxSteps, out vec4 tLayer, out vec4 alphaLayer)` | Hart-style cone march collecting up to four front-to-back near-miss layers and their coverage; returns the layer count; caller shades and composites "over". |

**Diagnostics (`dbg`, cat `debug`)**

| Signature | Contract |
|---|---|
| `vec3 dbgSlice(float d, float isoSpacing)` | Colour by sign with iso-lines every `isoSpacing`; plane-sweep view. |
| `float dbgGradientError(vec3 p, float h)` | `|∇f| − 1`; positive = overestimate risk, negative = loose bound. |
| `vec3 dbgHeat(float steps, float maxSteps)` | Step-count heat map colour. |
| `float dbgOvershoots(vec3 ro, vec3 rd, vec2 tRange, int maxSteps)` | Number of steps where the field returned negative after a positive step. |

### 12.3 What to build first

1. `cam`, `sdSphere/sdBox/sdPlane/sdCapsule`, `opUnion/opSmin/opSminMix`, `rmSphereTrace`,
   `ltNormal`, `ltSoftShadow`, `ltAO`, `dbgHeat`, `dbgSlice`: a complete, honest marcher.
2. `domRepeat*`, `domPolar*`, `opXor`, lifting: the multiplication tools.
3. `rmRelaxed`, `rmClipToBox`, `ixBox/ixPlane/ixSphere`, `bvCanSkip`: speed.
4. `aaDiskCoverage`, `aaCoverageLayers`, `camFootprint`: edges and textures.
5. `rmConePass` with a bench harness that renders the pass pyramid at small sizes (TDR care).

## 13. Corpus map: where to study each technique (pointers only)

| Technique | Corpus pointer | Licence (meta.json) |
|---|---|---|
| Reference primitives, bounding boxes inside the scene function | `Xds3zN/image.glsl:27-330, 347-384` (iq, "Raymarching - Primitives") | MIT |
| Analytic box and plane range clipping before marching | `Xds3zN/image.glsl:397, 408-430` | MIT |
| Distance-scaled hit threshold | `Xds3zN/image.glsl:436` | MIT |
| Soft shadow with clamped steps and plane bound | `Xds3zN/image.glsl:449-466` | MIT |
| Tetrahedron normal with anti-inlining loop | `Xds3zN/image.glsl:469-490`, `#define ZERO` at `:338` | MIT |
| Field ambient occlusion | `Xds3zN/image.glsl:493` | MIT |
| Ray differentials and analytically filtered checkers | `Xds3zN/image.glsl:509, 519, 640` | MIT |
| Supersampling loop | `Xds3zN/image.glsl:623` | MIT |
| Heavy smooth-minimum character, bounding reuse | `3lsSzf/image.glsl:32` (iq, Happy Jumping) | CC BY-NC-SA 3.0 |
| Aaltonen-improved soft shadow | `lsKcDD` (iq, Soft Shadow Variation) | CC BY-NC-SA 3.0 |
| Organic SDF portrait, elongation, many techniques | `WsSBzh` (iq, Selfie Girl) | CC BY-NC-SA 3.0 |
| Ellipsoid bound in a character | `ld3Gz2:29` (iq, Snail) | CC BY-NC-SA 3.0 |
| Raymarched 3D field terrain with soft shadows | `MdBGzG` (iq, Canyon) | CC BY-NC-SA 3.0 |
| Symmetry used to evaluate a fraction of an object | `tt2XzG` (iq, Sphere Gears) | CC BY-NC-SA |
| hg_sdf-style domain ops in the wild | `4sVczV`, `4sXBRn` (`pMod…`), `WljSWz`, `XtyXzW`, `wtcSzN` (`fOp…`) | CC BY-NC-SA |
| Backtracking-tolerant termination | `3tXXRn:115`, `4sS3zG:286`, `4ts3z2:94` | CC BY-NC-SA |
| Understep fudge factors (study as smells) | `MdBGzG:132`, `WsSBzh:103`, `ld3Gz2:181` | CC BY-NC-SA |
| Step-by-step raymarching tutorial | `4dSfRc` (reinder, [SH17C] Raymarching tutorial) | CC BY-NC-SA 4.0 |
| Hybrid SDF and voxel traversal | `dtVSzw` (gelami) | CC BY-NC-SA 3.0 |
| Analytic intersectors used alongside marching | `4tjGRh`, `MtX3Ws`, `tt2XzG` | CC BY-NC-SA |

## 14. Sources

Primary sources were read directly for this report unless marked otherwise.

- https://iquilezles.org/articles/distfunctions/ - Quilez's catalogue of exact and bound 3D SDFs and operators; exactness labels, revolution/extrusion, elongation, rounding, onion, booleans, scale, repetition, deformation advice. States article snippets are MIT.
- https://iquilezles.org/articles/smin/ - Smooth minimum in depth: DD and CD families, kernels, normalisation of `k`, gradients, conservativeness, circular variants, property table, material mix factor, history.
- https://iquilezles.org/articles/sdfrepetition/ - Domain repetition, cell ids, why naive repetition breaks, 2ⁿ neighbour fix, mirrored repetition (Fizzer), limited repetition by clamping ids, rotational and other parametrisations.
- https://iquilezles.org/articles/raymarchingdf/ - History of SDF raymarching (Ricci, Wyvill, Hart, Evans, Crane) and an annotated gallery of techniques per shader.
- https://iquilezles.org/articles/nvscene2008/ and https://iquilezles.org/articles/nvscene2008/rwwtt.pdf - "Rendering Worlds with Two Triangles": distance-aided marching, screen-space-constant error, cost numbers, Evans-style AO, early soft shadows, demoscene context.
- https://iquilezles.org/articles/normalsSDF/ - Central, forward and tetrahedron normals; derivation; footprint-scaled epsilon; anti-inlining trick (Hooper, Klems).
- https://iquilezles.org/articles/rmshadows/ - Soft shadows from `h/t`, light size, Aaltonen's improvement, inner-penumbra variant (nurof3n).
- https://iquilezles.org/articles/sdfbounding/ - Bounding volumes for SDFs: early skip, reuse of primitives, half-spaces, BVH and k-d tree experiments.
- https://iquilezles.org/articles/interiordistance/ - Why union interiors are wrong and five ways to cope.
- https://iquilezles.org/articles/sdfxor/ - Proof that xor of two SDFs is an exact SDF (with Jakob Thomsen).
- https://iquilezles.org/articles/distance/ - Distance estimation `|f|/|∇f|` for arbitrary implicits.
- https://iquilezles.org/articles/ellipsoids/ - Two ellipsoid bounds compared; why the gradient-normalised one is preferred.
- https://iquilezles.org/articles/fbmsdf/ - fBM detail that stays an SDF: sphere-grid noise grown with smooth max/min, LOD, carving.
- https://iquilezles.org/articles/terrainmarching/ - Heightfield marching, distance-proportional steps, linear interpolation of the crossing, terrain normals.
- https://iquilezles.org/articles/filteringrm/ - Ray differentials for texture filtering in raymarchers.
- https://iquilezles.org/articles/binarysearchsdf/ - Binary-search ray partitioning and stackless traversal; honest negative result versus the plain loop.
- https://iquilezles.org/articles/intersectors/ - Analytic ray intersectors for twenty primitives, with a sphere precision note.
- https://iquilezles.org/articles/boxfunctions/ - Box distance, gradient, intersection and occlusion functions.
- https://iquilezles.org/articles/distfunctions2d/ - The 2D SDF catalogue used for revolution and extrusion (skimmed; another report covers 2D in depth).
- https://graphics.stanford.edu/courses/cs348b-20-spring-content/uploads/hart.pdf - Hart 1996, "Sphere tracing": Lipschitz theory, convergence proof, convexity step, triangle-inequality cache, cone-traced antialiasing, deformation bounds. (Published: The Visual Computer 12(10):527-545, doi:10.1007/s003710050084.)
- https://diglib.eg.org/handle/10.2312/stag.20141233.001-008 - Keinert, Schäfer, Korndörfer, Ganse, Stamminger 2014, "Enhanced Sphere Tracing": over-relaxation, screen-space candidate, dynamic epsilon, discontinuity reduction, convex shortcut, timings.
- https://people.inf.elte.hu/csabix/publications/articles/eurographics-2018-shortpaper.pdf - Bálint and Valasek 2018, "Accelerating Sphere Tracing": planar-extrapolation steps, cone-folded field, resolution ramps.
- http://www.fulcrum-demo.org/wp-content/uploads/2012/04/Cone_Marching_Mandelbox_by_Seven_Fulcrum_LongVersion.pdf - Seven/Fulcrum, cone marching slides (Revision 2012): multi-pass depth, exact doubling, speed-ups, artefacts, fudge factors.
- https://mercury.sexy/hg_sdf/ - Mercury's hg_sdf library and page: naming conventions, Lipschitz discipline, right-angle combination operators, domain operators, debugging FAQ. Dual licence MIT OR CC-BY-NC-4.0.
- https://jamie-wong.com/2016/07/15/ray-marching-signed-distance-functions/ - Jamie Wong's beginner tutorial: loop, normals, Phong, camera, CSG, rigid and uniform scaling, the non-uniform scaling bound.
- https://www.pouet.net/topic.php?which=8785 - Pouet thread on computing the viewing-cone radius per distance from field of view and resolution.
- https://www.pouet.net/topic.php?which=7931 - The Pouet "Raymarching Toolbox" thread, the demoscene's long-running collection of tricks (linked from hg_sdf; not re-read for this report).
- https://x.com/SebAaltonen/status/978189264520441856 - Sebastian Aaltonen's GDC 2018 Claybook slides announcement (SDF ray tracing in a shipped game; coarse tracing; shadows). Slides not re-read; claims here are limited to what Quilez and Aaltonen's posts state.
- https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.13951 - Galin, Guérin, Paris, Peytavie 2020, "Segment Tracing Using Local Lipschitz Bounds" (abstract-level reading).
- https://dl.acm.org/doi/10.1145/3355089.3356502 - Seyb, Jacobson, Nowrouzezahrai, Jarosz 2019, "Non-linear sphere tracing for rendering deformed signed distance fields" (title/abstract only).
- https://www.shadertoy.com/view/Xds3zN - Quilez's "Raymarching - Primitives" (MIT; in our corpus): the reference implementation of most of the above.
- https://www.shadertoy.com/view/llXGR4 - Quilez's "Antialias, sort of" (2014): coverage-based silhouette antialiasing with ray differentials (described on raymarchingdf; not in our corpus).

## 15. Open questions for the house

1. Do we adopt Mercury's naming (`f…`, `p…`, `fOp…`) or the prefix law above? The prefix law encodes
   exactness, which Mercury's does not; recommend the prefix law, with Mercury names as aliases in
   comments for searchability.
2. The import tool could compute a *field-quality score* per corpus shader by running the gradient
   error and overshoot diagnostics headless at tiny resolution on CPU or in a capped GPU job. That
   would let the UI sort the corpus by "honest fields" versus "fudged fields". It needs the GPU-lock
   discipline (`arsenal/GPU-LOCK.md`) before any GPU run.
3. Cone marching needs a multi-pass harness (render targets at 1/16, 1/8, ... resolution). Our live
   surfaces are single-pass today; the module manifest would need a "passes" field.
