# The Primitive Atlas (draft)

**Status:** draft for Daniel's gate and for tonight's build, 2026-10-13 (shader school night).
**Written by:** Vandor (the claude seat), synthesising four bodies of evidence that other seats put on disk tonight:

- 42 private study notes, one per loved shader (`state/arsenal/shaders/study/<id>.md`, gitignored);
- 7 house census reports (`research/in-flight/shader-school-2026-10-13/arc-*.md`);
- 8 research reports (`research/reviewed/shader-school-2026-10-13/*.md`);
- Heimdall's blind half B on the unified module system (same folder).

**Companion document:** `unified-architecture-draft.md` (the machine that builds, wires, tests and ships these parts).

**The licence line, stated once and binding on everything below.** The loved shaders are other people's code, mostly
CC BY-NC-SA 3.0, and one (Warping - procedural 1, `4s23zz`) carries its author's own all-rights-reserved header. Nothing
in this document is their code. Every technique is described in our own words and in mathematics; a pointer such as
`image.glsl:42` names where to study it in the private corpus. The house library this atlas specifies is written fresh,
Apache-2.0, from the mathematics. Four loved shaders are CC0 and one is MIT; the house rule still says re-derive, so
they are treated exactly like the rest.

---

## 0. How to read this

Think of the house library as the parts room of an electronics workshop.

| workshop | here |
|---|---|
| a part with a datasheet (a resistor, an op-amp) | a **primitive**: one GLSL function with a contract |
| a labelled bin of similar parts | a **category** (for example "fractal sums") |
| a shelf of related bins | a **family** (for example "Noise and procedural fields") |
| a reference design or evaluation board that wires parts into something that works | a **group**: a composite recipe, such as "aurora curtain" |
| the application notes the best designers write | the **craft secrets**: tricks that recur across the loved shaders and live in no single datasheet |

Each primitive row gives six things:

- **Signature**: the house name and its GLSL types. Names follow the naming law in section 1.
- **Contract**: what it promises, in one sentence, including when it stops being honest.
- **Cost**: its cost class (0.2) and anything that multiplies it.
- **Loved**: which of Daniel's 42 loved shaders use the technique (short names; legend in 0.3). A dash means the house
  needs it but no loved shader shows it plainly.
- **Learn**: the best place to learn it. First the house research report and section (abbreviations in 0.4), then the
  primary source those reports cite.
- **P**: P0 (build tonight), P1 (next), P2 (later, or when a piece needs it).

### 0.1 Status key

| mark | meaning |
|---|---|
| **P0** | Build tonight. Either a foundation every other part stands on, a fix for a live defect (crawling dither, colour currency, the sine-hash family), or a part one of tonight's six P0 groups needs. |
| **P1** | Build next. Valuable and understood, but either it moves pixels on a look Daniel already approved (so it needs his gate first), or it is heavier than one night. |
| **P2** | Build when a piece asks for it. Specialised, expensive, or research-grade on this host. |

Nothing in the house library is built yet. `arsenal/web/glsl/` holds only the composer's browser twin (`modlib.js`) and
its README. The 31 bench chunks in `design/vfx-chunks/` are legacy parts the composer already reads in place.

### 0.2 Cost classes

Budget numbers come from GP section 3.8. This host's GPU (an AMD Radeon RX 9070 XT) has, in a perfect world, about
48,900 arithmetic operations per pixel per frame at 4K and 60 Hz, and about 12,200 at 4K and 240 Hz. Real shaders get a
fraction of that. Windows resets the GPU when one submission runs past 2 seconds, and this host has an AMD driver crash
history, so every loop has a constant ceiling (GP finding 8).

| class | what it is | rough size | example |
|---|---|---|---|
| **C0** | straight-line arithmetic: no loop, no texture | tens of operations; free | `shpSmoother`, `srgbEncode`, `sdBox` |
| **C1** | a small fixed loop: a constant bound of at most 32 over C0 bodies | hundreds | fBm octaves, a 3×3 cell search, 5 AO taps, 4 normal taps |
| **C2** | a march: one ray loop with a constant cap (at most 256) whose body calls a **hook**, a function the host provides (the scene's distance or density) | steps × hook cost | sphere tracing, a fog march |
| **C3** | nested: a loop inside a march (a light march per sample, a glass interior, fBm inside the hook) | the product of both caps; state both | a lit cloud |
| **C4** | stateful: owns render targets (feedback, simulation, a bloom pyramid, temporal accumulation) | per pass, per frame | stable fluids, phosphor trails |

Suffixes: **+Tn** means n texture fetches per call; **hook** means the primitive calls a host function
(`mapScene`, `densityAt`, `materialAt`), declared in its header so the composer can emit a prototype for it.

### 0.3 The 42 loved shaders (legend)

Licences are as the corpus records them (`state/arsenal/shaders/corpus/shaders/<id>/meta.json`), with the one known
correction. "Shadertoy default" means the code carries no licence line and Shadertoy's site default (CC BY-NC-SA 3.0)
applies.

| short name | id | author | licence | passes |
|---|---|---|---|---|
| AURORA | ttScDc | alro | MIT (explicit) | 3 |
| Aurora Lights | MsjfRG | Mattenii | CC BY-NC-SA (default) | 1 |
| Chromatic Curtains | ffG3Rc | Valdex (core follows nimitz's XtGGRt) | CC BY-NC-SA (default) | 1 |
| AuroraBorealis | MdBfzR | albertelwin | CC BY-NC-SA (default) | 1 |
| Cloud Ten | XtS3DD | nimitz | CC BY-NC-SA (explicit) | 1 |
| Dark Cloud | 4slGWM | FabriceNeyret2 ("enlightened dark cloud") | CC BY-NC-SA (explicit) | 1 |
| Volumetric Sample | tsScDG | suyoku | CC BY-NC-SA (default) | 1 |
| Dry Ice | WlVyRV | xjorma ("Dry ice 2") | CC BY-NC-SA (explicit) | 6 |
| Glitch Transform | XtyXzW | tdhooper | CC BY-NC-SA (default) | 1 |
| Bubble Rings | WdB3Dw | tdhooper | CC BY-NC-SA (default) | 1 |
| Geodesic | llVXRd | tdhooper ("Geodesic tiling") | CC BY-NC-SA (default) | 1 |
| Isoline Triangle | Xt3yDS | tdhooper | CC BY-NC-SA (default) | 1 |
| Isoline Simple | Ms2XWc | iapafoto | CC BY-NC-SA (explicit) | 1 |
| Apollonian | 7d2fDW | mrange ("Appolloian with a twist II") | CC0 (explicit) | 1 |
| Starry Planes | MfjyWK | mrange | CC0 (explicit) | 1 |
| Saturday | 43jXWt | mrange ("Saturday weirdness") | CC0 (explicit) | 3 |
| Just a Cube | 3XdXRr | mrange ("Just another cube") | CC0 (explicit) | 1 |
| Plasma Globe | XsjXRm | nimitz | CC BY-NC-SA (explicit) | 1 |
| Flame | MdX3zr | XT95 | CC BY-NC-SA (explicit) | 1 |
| Alien Core | 4tcXRr | glkt | CC BY-NC-SA (default) | 1 |
| Starship | l3cfW4 | Xor ("Starship [320]") | CC BY-NC-SA (default) | 1 |
| Satisfying | Mts3zM | nimitz ("Overly satisfying") | CC BY-NC-SA (explicit) | 1 |
| Discoteq | DtXfDr | supah ("Discoteq 2") | CC BY-NC-SA (default) | 1 |
| Sincos 3D | XfXGz4 | ChunderFPV | CC BY-NC-SA (default) | 1 |
| Blue Red Shiny | 7cjGRR | diatribes ("Blue Red Shiny 2") | CC BY-NC-SA (default) | 1 |
| Hex Glitch | lfscD7 | igneus | CC BY-NC-SA (default) | 4 |
| Pretty Hip | XsBfRW | Hadyn | CC BY-NC-SA (default) | 1 |
| Humanimation | ltdcW7 | pellicus ("[SH18] Humanimation") | CC BY-NC-SA (default) | 4 |
| Cube Lines | NslGRN | morimea | CC BY-NC-SA (explicit) | 1 |
| HAL 4000 | MtXczn | Manwe | CC BY-NC-SA (default) | 1 |
| Inercia | cs2GWD | 0b5vr ("20221105_inercia intended one", Inercia 2022 Shader Royale) | CC BY-NC-SA (default) | 1 |
| Data Warehouse | NlK3Wt | bitless ("Cyberspace data warehouse") | CC BY-NC-SA (default) | 1 |
| Hexagone | wsl3WB | BigWings (Martijn Steinrucken) | CC BY-NC-SA (explicit) | 1 |
| Heartfelt | ltffzl | BigWings | CC BY-NC-SA (explicit) | 1 |
| Rhodium | llK3Dy | Virgill ("Rhodium liquid carbon") | CC BY-NC-SA (default) | 2 |
| Marble | XsSGDh | mmalex | CC BY-NC-SA (default) | 1 |
| Warping | 4s23zz | iq ("Warping - procedural 1") | **all rights reserved** (the author's own header; the corpus meta wrongly says Shadertoy default) | 1 |
| Creation Stone | XdcyDM | mmerchante | CC BY-NC-SA (default) | 2 |
| RM Experiment 23 | 4lj3Ww | aiekick ("Ray Marching Experiment 23") | CC BY-NC-SA (explicit) | 1 |
| Sphere Intersect | XsfBRH | nt4t ("sphere intersect pub"; its flow field derives from Kali's Kaliset) | CC BY-NC-SA (default) | 1 |
| Oscillo Donut | ldSfWV | ttoinou ("OscilloStereoXY Trippy Donut") | CC BY-NC-SA (explicit) | 3 |
| Audio Eclipse | MdsXWM | airtight | CC BY-NC-SA (default) | 1 |

**Warping is study-only.** Its study note says never port or display it. Its techniques (two-level domain warping,
colouring from intermediate fields) are textbook and appear in NP section 8 with independent sources, so the house
learns them from the research report, not from that file. The Shelf (architecture section 9) must not show its renders.

### 0.4 Where to learn: abbreviations

| abbreviation | file (all under `research/reviewed/shader-school-2026-10-13/`) |
|---|---|
| **SR** | `sdf-raymarching.md`: distance fields, the marcher, shading from the field, silhouette antialiasing |
| **NP** | `noise-procedural.md`: hashes, lattice and cellular noise, fractal sums, warping, flow, dithering |
| **LM** | `lighting-materials.md`: diffuse, microfacet specular, Fresnel, shadows, AO, environment, glass, glow |
| **VA** | `volumes-atmosphere.md`: transmittance, phase functions, clouds, sky, fog, aurora, nebulae |
| **CP** | `color-post.md`: transfer functions, OKLab, palettes, exposure, tone mapping, bloom, lens, dither, grading |
| **PF** | `pattern-fractal-2d.md`: the 2D frame, shaping, 2D distance, antialiasing, polar, tiling, contours, text, fractals |
| **WS** | `water-sims-feedback.md`: feedback, temporal accumulation, automata, reaction-diffusion, ripples, fluids, particles, oceans |
| **GP** | `gpu-perf-glsl.md`: how a fragment shader runs, precision, textures, multipass, ANGLE on Direct3D 11, audio inputs |
| **study:id** | the private study note, `state/arsenal/shaders/study/<id>.md` (gitignored) |

Primary sources are named by author and title, the way the research reports cite them (for example "Hart 1996, Sphere
Tracing"; "Quilez, smooth minimum"). Inigo Quilez's articles are cited as "Quilez, <title>".

---

## 1. The naming law (and the collision ledger)

The composer (`arsenal/shaders/modules.py`, twin `arsenal/web/glsl/modlib.js`) refuses to load a library in which two
modules define the same function name (`Library.add`). Tonight that refusal takes the **whole** library down, which
would take every surface's shader down with it (the architecture fixes this with quarantine, section 4.3). So naming is
not style here; it is wiring. Seven laws:

1. **One owner per function name**, across `arsenal/web/glsl/` and `design/vfx-chunks/` together.
2. **Family prefixes.** Where the field has a common tongue the house speaks it (`sdBox`, `opSmin`, `fbm3`, `hash33`);
   elsewhere a short prefix names the family:

   | prefix | family / category | prefix | family / category |
   |---|---|---|---|
   | `safe*`, `imod*`, `rotate*` | core maths | `cam*` | cameras |
   | `uv*` | the 2D frame | `rm*` | marchers |
   | `shp*` | shaping curves | `ix*` | analytic intersections |
   | `clk*` | clocks and frame-rate independence | `nrm*` | normals |
   | `env*` | envelopes and timelines | `vis*` | shadows and occlusion |
   | `hash*`, `pcg*`, `u01` | hashes | `lit*` | light and material |
   | `noise*`, `fbm*`, `warp*` | noise, fractal sums, warps | `glow*` | emission and glow |
   | `dth*` | dither and jitter masks | `rig*` | lighting rigs |
   | `sd2*`, `aa*`, `iso*` | 2D distance, antialiasing, contours | `vol*`, `phase*`, `cloud*` | volumes |
   | `dom*` | domain operators (2D and 3D) | `sky*`, `fog*`, `aurora*` | atmosphere |
   | `lat*`, `pat*` | lattices and patterns | `srgb*`, `oklab*`, `oklch*`, `luminance` | colour transfer and perception |
   | `cx*`, `frac*` | complex numbers, fractals | `pal*` | palettes |
   | `txt*` | text | `tm*`, `expose`, `display*` | tone mapping and the display seam |
   | `sd*`, `sb*`, `ud*`, `op*` | 3D distance and combination | `grd*`, `vig*`, `ca*`, `bloom*`, `dither*` | grading and post |
   | `sim*`, `stn*`, `adv*`, `fld*`, `wave*`, `ptc*`, `acc*`, `fb*` | simulation and feedback | `gli*`, `crt*` | glitch and signal art |
   | `aud*`, `mus*`, `mouse*`, `key*` | inputs, audio, music | `cmp*` | compositing |
   | `dbg*`, `testcard*` | debug views and test cards | `mech*`, `path*`, `hist*`, `seq*`, `flk*` | motion and choreography |

3. **Dimension suffix** whenever a primitive exists in more than one dimension: `noiseValue2`, `noiseValue3`; `hashNM`
   maps N inputs to M outputs (`hash31`: vec3 in, float out). Overloads are allowed only inside one module.
4. **Exactness in the name** for distances (SR 12.1): `sd` is an exact signed distance, `sb` a signed bound that never
   overestimates, `ud` an exact unsigned distance. A marcher can trust the name.
5. **Domain operators take the position `inout` and return the cell or sector id** (SR 4.8, PF 16.1).
6. **Currency in the contract.** Everything is scene-linear light unless the name or contract says otherwise; a
   function that returns display-encoded values says so (`grdSCurveDisp`, `tmHejlEnc`).
7. **Legacy twins** live in `arsenal/web/glsl/legacy/`, reproduce a surface's existing maths exactly, and are named for
   what they are (`hashSine31`), never for what they replace. They exist so a surface can adopt the library without one
   pixel moving; upgrading to the canonical part is a separate, gated step.

### 1.1 The collision ledger

The eight research reports each proposed an API for their lane. Read together they define several names twice, and two
of them collide with legacy chunks. This ledger settles every one; the owner is the module that will define the name.

| proposed (report) | collides with | house owner and name | why |
|---|---|---|---|
| `ign` (NP, noise.dither) | `ign` (CP, post.dither) | `dthIgn` in `noise/dither-masks.glsl` | one mask, two consumers (march jitter and output dither) |
| `curl2(vec2, uint)` (NP, flow) | `curl2(sampler2D, ...)` (WS, stencil) | `noiseCurl2` (flow) and `stnCurl` (stencil) | different things: a velocity field versus measured vorticity |
| `lit_glowStep(d, stepLen, k)` (LM) | `glowStep(d, passthrough, density)` (PF) | `glowEmitStep` (emission per step) and `rmPassStep` (the step length of a pass-through march) | same name, opposite jobs |
| `fresnelSchlick(float, float)` (WS, water) | `lit_fresnelSchlick(vec3, float)` (LM) | `litFresnelSchlick`, float and vec3 overloads in one module | water is one dielectric case |
| `beerLambert` (WS), `lit_beer` (LM) | `vol_transmittance3` (VA) | `volTransmittance` / `volTransmittance3` | one law |
| `lit_luminance` (LM) | `luminance` (CP) | `luminance` in `colour/transfer.glsl` (Rec.709 weights on linear values) | one weighting, never Rec.601 |
| `pixelFootprint` (WS, ocean) | `camPixelAngle` (SR), `uvPixel` (PF) | `camPixelAngle` (3D, radians per pixel) and `uvPixel` (2D, units per pixel) | footprint at distance t is t × camPixelAngle |
| `safe_pow` (CP) | `safePow` (GP) | `safePow` | |
| `sanitize_hdr` (CP), `simSanitize` (WS) | `finiteOr` (GP) | `finiteOr` in `core/safe.glsl`; `simSanitize` becomes a two-line wrapper that also clamps | one guard before every feedback write |
| `debug_nan` (CP), `lit_debugNaN` (LM) | `rangeScope` (GP) | `dbgNaN` and `dbgRangeScope` in `debug/views.glsl` | |
| `dbgHeat` (SR) | `heatRamp`, `heatCount` (GP) | `dbgHeatRamp`, `dbgHeatCount` | |
| `ltSoftShadow` (SR) | `lit_softShadow`, `lit_softShadowTri` (LM) | `visSoftShadow` (angular-radius parameter, Aaltonen's triangulated estimate inside) | one shadow, one parameter that means something physical |
| `ltAO` (SR) | `lit_aoNormal` (LM) | `visAO` | |
| `ray_sphere` (VA) | `ixSphere` (SR) | `ixSphere`; `ixSphereAlt` for planet-scale radii | |
| `noise_value3` (VA) | `noise_value` (NP) | `noiseValue3` | |
| `noise_curl3` (VA) | `curl3` (NP) | `noiseCurl3` | |
| `noise_fbm3` (VA), `fbm` (NP) | legacy chunk `value-noise-3d` defines `fbm3` | `fbm3` in `noise/fbm.glsl`, **after** the legacy chunk's functions are renamed (architecture slice S2) | the canonical name is the field's name |
| `remap` (VA, cloud) | a generic word | `shpRemap` | it is a shaping curve, used far beyond clouds |
| `smooth_abs` (NP) | `shpSoftAbs` (PF) | `shpSoftAbs` | |
| `aa_threshold` (NP) | `aaFill` (PF) is the distance form | `aaStep` | a threshold on a non-distance value |
| `march_jitterStart` (VA) | `jitter_ign` (VA) | `rmJitterStart` (uses `dthIgn`) | |
| `lit_glowClosest` (LM) | `glow_exp` (CP) | `glowExp` | the same exp(-k·d) |
| `temporal_*` (VA) | `temporal` category (WS) | `acc*` (accumulation), `taa*` (temporal antialiasing) | two reports, one category |
| `vignette_corner` (CP) | legacy chunk `vignette-cubic` (a snippet, no function) | `vigCorner` | the chunk stays a snippet; the bench can call the function |

Legacy chunk functions tonight: `pR` (rot2), `segD` (segment-distance), `h31` (hash31), `fbm3` and `vn`
(value-noise-3d). Only `fbm3` collides with a canonical name. Two further traps: `moonwater.js:7` defines a function
named `hash31` with sine-free maths inline in a JavaScript string, so when Moonwater adopts the library its own helper
must move into a legacy module under a different name (`hashHoskins31`) before the canonical `hash31` is linked; and the
chunk `value-noise-3d` cites an all-rights-reserved source in its provenance (VA 12, house note 3), which the rename
slice also corrects.

---

## 2. The family map (one screen)

Thirteen families, 80 categories, 562 primitive rows (a row sometimes holds a small set of sibling functions, such as
the 2D and 3D versions of one noise). By status: 184 rows P0, 265 P1, 113 P2. Section 18 turns the P0 rows into 65
module files and about 215 functions.

```
A  Foundations ............ core maths · integers · compile guards · clocks · the 2D frame · shaping · hashes · debug views
B  Noise and fields ....... lattice noise · cellular · fractal sums · domain warp · flow · periodic and looping · dither masks
C  2D drawing ............. 2D distance · 2D antialiasing · contours · 2D domains · lattices · patterns · complex and 2D fractals · text
D  3D shape ............... distance shapes · lifting · combination · 3D domains · 3D fractals · surface detail
E  Rays ................... analytic intersection · cameras · marchers · normals · 3D antialiasing
F  Light and material ..... diffuse · specular · Fresnel · lights · visibility · environment · glass · thin film · glow · rigs · materials
G  Volumes and sky ........ integration · phase · cloud lighting · density shaping · volume marching · sky · fog and rays · aurora · nebula
H  Colour and finish ...... transfer · perceptual colour · legacy colour knobs · palettes · tone mapping · grading · lens and bloom · dither · the display seam
I  Motion ................. envelopes and timelines · flicker and clocks · waves · paths · analytic history · mechanical motion · sequencing
J  State and simulation ... simulation I/O · stencils · advection and fluids · waves and ripples · oceans · pattern sims · particles · temporal and feedback
K  Glitch and signal art .. address corruption · CRT and oscilloscope · parity compositing
L  Inputs and music ....... mouse and keyboard · audio spectrum · music ports (the house note bus) · state registers
M  Compositing ............ over and under · additive, screen and max · layer sorting
```

How the families stack, bottom to top, like a board: **A** is the power supply and the screws; **B**, **C** and **D**
make shapes and fields; **E** turns 3D shapes into pixels; **F** and **G** decide what light does there; **H** turns
light into a picture on a screen; **I** makes it move; **J** gives it memory; **K**, **L** and **M** are the
special-purpose daughterboards (signal corruption, the outside world, and layering).

---

## 3. Family A: Foundations

The screws, the power rails and the multimeter. Nothing here is pretty on its own; everything else is built from it.

### A1. Core maths (`core/const.glsl`, `core/safe.glsl`, `core/rotate.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `const float PI, TAU, PHI, SQRT3` | the constants every module uses, defined once (needs the composer to provide consts, architecture S1) | C0 | all | GP 5 | **P0** |
| `float dot2(vec2 v)` / `float dot2(vec3 v)` | squared length, so distance formulas take one square root | C0 | most SDF shaders | SR 12.2 | **P0** |
| `float safeDiv(float n, float d, float eps)` | n/d with abs(d) floored at eps and its sign kept; never Inf or NaN | C0 | — | GP 5.8 | **P0** |
| `vec3 safeNormalize(vec3 v, vec3 fallback)` (+vec2) | v/length(v) when dot(v,v) > 1e-24, else fallback; required in any pass that writes a feedback buffer | C0 | — | GP 5.8 | **P0** |
| `float safeSqrt(float x)` | sqrt(max(x,0)); rounding that pushes a value slightly negative gives 0, not NaN | C0 | Marble, Cube Lines (discriminants) | GP 5.8 | **P0** |
| `float safeAcos(float x)` | acos(clamp(x,-1,1)); unit dot products can exceed 1 by one ulp | C0 | — | GP 5.8 | **P0** |
| `float safePow(float b, float e)` | pow on max(b, 1e-30); defined for all inputs | C0 | — | GP 5.8 | **P0** |
| `float safeLog2(float x, float floorVal)` | log2(max(x, floorVal)); silence gives a finite floor, not -Inf | C0 | — | GP 5.8 | P1 |
| `vec4 finiteOr(vec4 v, vec4 fallback)` | replaces each non-finite component; the last guard before any feedback write, so one bad texel cannot poison a loop | C0 | Saturday, Oscillo Donut, Dry Ice (feedback shaders) | GP 5.8, WS 1.4 | **P0** |
| `mat2 rotate2(float a)` | exact counter-clockwise rotation; never the golfed constant-offset approximation | C0 | Glitch Transform, Geodesic, Sincos 3D, Blue Red Shiny, Starship (all rotate; three golf it) | PF 5.1 | **P0** |
| `mat3 rotateAxis(vec3 axis, float a)` | Rodrigues axis-angle rotation; axis must be unit length | C0 | Oscillo Donut | LM 1 | P1 |
| `mat3 rotateOnto(vec3 from, vec3 to)` | trig-free rotation taking one unit direction onto another; undefined for exactly opposite vectors (caller handles) | C0 | Saturday | SR 4.7 | P1 |
| `mat3 rotateEuler(vec3 rates, float t)` | three-axis rotation at incommensurate rates (a tumble that never visibly repeats) | C0 | HAL 4000, Saturday | craft secret 4 | P1 |

### A2. Integers, precision and compile guards (`core/int.glsl`, `core/compile.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `int imodFloor(int a, int b)` (+ivec2) | floor modulo for b > 0: result in [0,b) for any sign of a (the `%` operator is undefined for negatives and differs on ANGLE) | C0 | Dry Ice (its +100 guard is the hand-made version) | GP 5.9 | **P0** |
| `int cellIndex(float x)` | int(floor(x)); `int()` truncates toward zero, so int(-0.5) would wrongly be 0 | C0 | every tiling | GP 5.9 | **P0** |
| `int idivFloor(int a, int b)` | floor(a/b) for any sign of a | C0 | — | GP 5.9 | P1 |
| `float fmodFloor(float x, float m)` | x - m·floor(x/m), pushed back into [0,m) when rounding lands exactly on m | C0 | — | GP 5.9 | P1 |
| `float roundHalfUp(float x)` | floor(x + 0.5); `round()` may round halves to even | C0 | — | GP 5.9 | P1 |
| `int unrollBarrier(int n, int frame)` | n + min(frame, 0): equals n at run time but the compiler cannot see it, so the loop stays a loop (compile time and code size of one body under ANGLE's Direct3D compiler) | C0 | Volumetric Sample (the same idiom) | GP 4.3, 8.2 | **P0** |
| `float ulp32(float x)` / `float ulp16(float x)` | the spacing of float32 or float16 at x; a diagnostic for coarse coordinates and rotting clocks | C0 | — | GP 5.5 | P2 |

### A3. Clocks and frame-rate independence (`core/clock.glsl`)

83 of the 103 multipass corpus shaders are frame-locked: anything they integrate per frame runs four times faster on this
240 Hz display than at the 60 Hz they were tuned for (GP finding 5). These parts make every rate a per-second rate.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float clkPhase(float tWrapped, float hz)` | fract(hz·t) in cycles for a host-wrapped t; the host keeps t small so the phase never rots | C0 | — | GP 5.5 | **P0** |
| `float clkPhaseSplit(float tWhole, float tFrac, float hz)` | phase from whole seconds plus a fraction passed separately; error about ulp(hz) at any uptime | C0 | — | GP 5.5 | P1 |
| `float clkKeep(float keepPerSecond, float dt)` | pow(keepPerSecond, dt): a decay that looks the same at 60 Hz and 240 Hz | C0 | Dry Ice (clamp-then-damp), Oscillo Donut (phosphor 0.85), AURORA (state buffer) | WS 2.2, GP 5.7 | **P0** |
| `float clkAlpha(float dt, float tau)` | 1 - exp(-dt/tau): the blend weight of a one-pole smoother with time constant tau seconds | C0 | — | WS 3.1 | **P0** |
| `float clkStutter(float t, float period)` | floor(t/period): a seed that holds still, then jumps (the stutter tempo of glitch art) | C0 | Glitch Transform (0.6 s), Hex Glitch (drifting 7, 9, 11, 12-frame dice) | study:XtyXzW | P1 |
| `float clkStall8(float keepPerFrame)` | the level an 8-bit buffer stops decaying at under a per-frame multiply; a diagnostic | C0 | — | GP finding 6 | P2 |

### A4. The 2D frame (`core/frame.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 uvCentered(vec2 fragCoord, vec2 res)` | origin at the canvas centre, y in [-1,1], x scaled by the same factor: aspect-true, y up | C0 | nearly all | PF 1 | **P0** |
| `float uvPixel(vec2 res)` | the size of one pixel in uvCentered units (2/res.y); exact for any unwarped domain | C0 | Satisfying (resolution-aware softness), Isoline Triangle (resolution-relative weight) | PF 1 | **P0** |
| `float uvFootprint(vec2 p)` | pixel footprint of a continuous coordinate: the larger screen-derivative length. Never pass an id or a folded value (floor 6) | C0 | Isoline Simple, Humanimation | PF 4.2 | **P0** |
| `vec2 uvContain(vec2 uv, vec2 srcRes, vec2 dstRes, out float inside)` | letterboxed "contain" mapping of a source image (video) into the canvas; `inside` is 0 in the bars | C0 | — (house: `video_uv` pasted in 6 presets and play.js) | — | P1 |
| `vec2 uvSimilarity(vec2 p, vec2 centre, float zoom, float angle)` | one similarity transform from screen to view space, so zoom and spin are one call | C0 | Hex Glitch, Pretty Hip | study:lfscD7 4.10 | P1 |

### A5. Shaping curves (`core/shaping.glsl`)

The vocabulary of curves. Most "magic" in the loved shaders is a well-chosen curve applied after a dull field
(craft secret 3).

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float shpLinstep(float a, float b, float x)` | linear 0-to-1 ramp from a to b, clamped; the box-filter edge | C0 | many | PF 2 | **P0** |
| `float shpSmoother(float a, float b, float x)` | quintic ramp: zero slope and curvature at both ends (C2) | C0 | Volumetric Sample (quintic fade) | PF 2 | **P0** |
| `float shpImpulse(float x, float k)` | exponential impulse: 0 at x=0, exactly 1 at x=1/k, then decays | C0 | — | PF 2; Quilez, useful little functions | **P0** |
| `float shpPulse(float x, float centre, float halfWidth)` | cubic bump, 1 at centre, exactly 0 beyond halfWidth | C0 | — | PF 2 | **P0** |
| `float shpGain(float x, float k)` | S-curve (k>1) or inverse S (k<1) on [0,1] fixing 0, ½ and 1 | C0 | — | PF 2 | **P0** |
| `float shpParabola(float x, float k)` | bump 0→1→0 on [0,1] with sharpness k | C0 | Oscillo Donut (squared-parabola bell windows) | PF 2 | **P0** |
| `float shpPowerCurve(float x, float a, float b)` | asymmetric bump with peak normalised to 1 | C0 | — | PF 2 | P1 |
| `float shpAlmostIdentity(float x, float threshold, float floorValue)` | equals x above threshold, smoothly floored below; C1 | C0 | — | PF 2 | P1 |
| `float shpSoftAbs(float x, float k)` | creaseless abs: sqrt(x²+k); limits the high frequencies abs() creates in turbulence and mirrors | C0 | Starry Planes (smooth abs in the star) | PF 2, NP 12 | **P0** |
| `float shpTri(float x)` | triangle wave, period 1, range [0,1] | C0 | Plasma Globe, Satisfying, Chromatic Curtains, Rhodium | PF 2 | **P0** |
| `float shpRemap(float v, float a, float b, float c, float d)` | unclamped linear refit of [a,b] onto [c,d]; the carving tool that erodes edges and keeps cores | C0 | Cloud Ten (density remaps) | VA 2.2 | **P0** |
| `float shpInvPower(float d, float r, float k)` | (r/d)^k: a soft threshold with enormous gain. Valleys of mild noise become hot filaments; the same curve draws twinkling stars and glare (one primitive, four jobs) | C0 | AURORA, Chromatic Curtains (one-over-a-sum filaments) | VA 7.2; study:ttScDc 6.3 | **P0** |
| `float shpTentPow(float x, float centre, float width, float power)` | a linear tent shaped by an exponent; animating the exponent makes a band breathe | C0 | AuroraBorealis | study:MdBfzR | P1 |
| `float shpPadded(float a, float b, float pad, float x)` | smoothstep with plateaus at both ends, so a key lands and holds | C0 | Hex Glitch | study:lfscD7 4.9 | P1 |
| `float shpBandPass(float m, float offset)` | sin(π·m - offset), clamped: peaks mid-transition, so a mask draws rims, crusts and coastlines | C0 | Creation Stone | study:XdcyDM | P2 |

### A6. Hashes (`hash/pcg.glsl`, `legacy/hash-sine.glsl`, `legacy/hash-hoskins.glsl`)

The dice under everything. The house has the sine hash `fract(sin(dot(p, k)) · 43758.5453)` in 18 tracked files; it
bands under `mediump`, varies between GPUs and degrades with large inputs. The canonical family is integer hashing
(Jarzynski and Olano, JCGT 2020), bit-exact on every GPU.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `uint hashU1(uint x)` | PCG-style one-in-one-out hash, full avalanche on 32 bits | C0 | Hex Glitch (PCG streams) | NP 2.3; Jarzynski and Olano 2020 | **P0** |
| `uvec3 pcg3d(uvec3 v)` | three-in-three-out: the house default for lattice corners and per-pixel randomness | C0 | Inercia (a PCG3D-style hash on exact cell centres) | NP 2.3 | **P0** |
| `uvec4 pcg4d(uvec4 v)` | four-in-four-out for (x, y, z, seed) or (x, y, frame, seed) | C0 | Hex Glitch | NP 2.3 | **P0** |
| `uvec2 pcg2d(uvec2 v)` | two-in-two-out | C0 | — | NP 2.3 | P1 |
| `float u01(uint x)` (+uvec2, uvec3, uvec4) | top 24 bits scaled by 2^-24: an exact float in [0,1), never 1.0 | C0 | — | NP 2.4 | **P0** |
| `uvec3 cellU3(vec3 p)` (+`cellU2`) | floor to the integer cell and reinterpret as uint; negatives hash deterministically by two's-complement wrap | C0 | — | NP 2.4 | **P0** |
| `float hash21(vec2 p)`, `float hash31(vec3 p)`, `vec3 hash33(vec3 p)`, `vec2 hash22(vec2 p)` | float-facing wrappers over pcg on the cell of p; [0,1) | C0 | all | NP 15.2 | **P0** |
| `float hashBits31(vec3 p)` | hash of an arbitrary float position through its exact bit pattern | C0 | Inercia | NP 15.2 | P1 |
| `vec2 randDir2(uint h)` / `vec3 randDir3(uvec2 h)` | uniform unit vectors on the circle or sphere | C0 | — | NP 15.2 | P1 |
| `float rngNext(inout uint state)` | the next uniform number from a per-pixel integer state; advances the state | C0 | Hex Glitch (four-lane stream) | WS 8 | P1 |
| `vec2 rngGauss2(inout uint state)` | two standard-normal numbers by Box-Muller | C0 | — | WS 9.4 | P2 |
| `float hashSine21(vec2 p)`, `float hashSine31(vec3 p)` **(legacy twin)** | the sine-dot hash exactly as the house's 18 files write it; exists only so a surface can adopt the library without its pixels moving | C0 | Aurora Lights, Glitch Transform, Plasma Globe, Flame, Rhodium, Dark Cloud, Oscillo Donut | NP 2.2 | **P0** |
| `float hashHoskins31(vec3 p)` **(legacy twin)** | the sine-free arithmetic float hash family (Hoskins, "Hash without Sine", MIT) as Moonwater writes it, renamed | C0 | Volumetric Sample, Dry Ice, Creation Stone, Heartfelt | NP 2.2 | P1 |

### A7. Debug views and test cards (`debug/views.glsl`, `debug/testcards.glsl`)

Every loved shader that taught well also showed its own wiring: Glitch Transform's NORMALS, NO_GLITCH and GLITCH_MASK
switches, Dark Cloud's split-screen A/B with an energy-overflow flag, Dry Ice's flat view of the simulation buffer, RM
Experiment 23's contact-sheet tiling. The house makes that a rule: every module ships its "where am I wrong" views
(craft secret 13), and every host can switch to them.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 dbgHeatRamp(float t)` | a monotone, perceptually ordered dark-to-bright ramp for t in [0,1] | C0 | — | GP 10.4 | **P0** |
| `vec3 dbgHeatCount(float count, float budget)` | heat ramp of count/budget, magenta above budget: where the slow pixels are | C0 | — | GP 10.4; SR 9.1 | **P0** |
| `vec3 dbgRangeScope(vec4 c)` | magenta for NaN, cyan for Inf, blue for negative, red above 1, grey in range | C0 | Dark Cloud (overflow in pure red) | GP 10 | **P0** |
| `vec3 dbgNaN(vec3 c)` | magenta where any channel is NaN or Inf, else c | C0 | — | LM 16 | **P0** |
| `vec3 dbgSlice(float d, float spacing)` | sign colouring with iso-lines every spacing, for a plane sweep through a distance field; broken lines reveal broken fields | C0 | — | SR 9.1 | **P0** |
| `vec3 dbgCells(vec2 local, vec2 cellId, vec2 period, float px)` | local coordinate as red/green, id hashed to a tint, borders overlaid: the development view BigWings teaches | C0 | Hexagone, Heartfelt (by their author's method) | PF 14.3 | **P0** |
| `float dbgGradientError(vec3 p, float h)` **hook** | length of grad f minus 1: positive is overestimate risk, negative a loose bound | C1 | — | SR 9.1 | P1 |
| `float dbgOvershoots(vec3 ro, vec3 rd, vec2 tRange, int maxSteps)` **hook** | counts steps where the field turned negative after a positive step; non-zero means the field overestimates on that ray | C2 | — | SR 9.1 | P1 |
| `vec3 dbgFootprint(float px, float featureSize)` | heat map of how many pixels a feature spans (blue safe, red aliasing) | C0 | — | PF 14.3 | P1 |
| `vec3 dbgFalseStops(vec3 lin)` | false-colour bands per stop around 0.18 grey, like a camera's exposure view | C0 | — | CP 14.11 | P1 |
| `vec3 dbgClipZebra(vec3 disp, vec2 pixel, float limit)` / `vec3 dbgGamut(vec3 lin)` | zebra stripes where display values clip; highlight of out-of-gamut linear values | C0 | — | CP 14.11 | P1 |
| `vec3 testcardHueExposure(vec2 uv01)` / `vec3 testcardRamp(vec2 uv01)` | hue rows against exposure columns (shows a tone mapper's hue skews and path to white); stacked linear, encoded and OKLab ramps (shows banding) | C0 | — | CP 14.11 | P1 |
| `vec3 dbgMipLevel(vec2 uv, vec2 texSize)`, `vec3 dbgTileGrid(vec2 fc, float tilePx, vec3 base)`, `float dbgQuadDisagreement(float flag)` | texture LOD view; wave-tile grid; where a 2×2 quad is split by a branch | C0 | — | GP 6.2, 3.6 | P2 |

---

## 4. Family B: Noise and procedural fields

The house's fabric store. Hash in, field out. NP is the textbook for this whole family.

### B1. Lattice noise (`noise/value.glsl`, `noise/gradient.glsl`, `noise/simplex.glsl`, `noise/texture.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float noiseValue2(vec2 p, uint seed)` / `float noiseValue3(vec3 p, uint seed)` | signed value noise, quintic fade, integer-hashed corners, about [-1,1] | C0 (4 or 8 hashes) | Dry Ice, Flame (cosine fade), Rhodium, Dark Cloud, Volumetric Sample, Aurora Lights (a binomially smoothed lattice variant) | NP 3 | **P0** |
| `vec3 noiseValue2Deriv(vec2 p, uint seed)` / `vec4 noiseValue3Deriv(vec3 p, uint seed)` | value in .x plus the exact gradient | C0 | — | NP 11; Quilez, value noise derivatives | P1 |
| `float noiseGrad2(vec2 p, uint seed)` / `float noiseGrad3(vec3 p, uint seed)` | improved Perlin gradient noise: zero at lattice points, quintic fade | C0 | AURORA (1D Perlin) | NP 4; Perlin 2002, Improving Noise | **P0** |
| `vec3 noiseGrad2Deriv` / `vec4 noiseGrad3Deriv` | gradient noise plus exact gradient | C0 | — | NP 11 | P1 |
| `float noiseGrad1(float x, uint seed)` | 1D gradient noise for flicker and travelling pulses | C0 | AURORA, Plasma Globe (1D texture flicker) | NP 4 | P1 |
| `float noiseSimplex2(vec2 p, uint seed)` / `float noiseSimplex3(vec3 p, uint seed)` | simplex noise on the skewed lattice; no axis-aligned artefacts in 3D, cheaper than gradient noise there | C0 | Isoline Triangle (a tetrahedral simplex-style noise) | NP 5; Gustavson, Simplex noise demystified | P1 |
| `vec4 noiseSimplex3Deriv(vec3 p, uint seed)` | simplex value plus exact gradient | C0 | — | NP 5, 11 | P1 |
| `float noiseTex3(sampler2D tile, vec3 p)` | one-fetch 3D value noise from a 2D noise tile whose second channel is the first offset by (37,17) texels per z step; the house generates its own tile, and the shader lab's media stand-in already uses this layout | C0 +T1 | AURORA, Cloud Ten, Plasma Globe, Alien Core (direction-only biplanar texture noise), Starship | NP 3; GP 6 | P1 |
| `float noiseTriangle2(vec2 p, float t, int octaves)` | filament noise from octaves of a 2D triangle wave on a rotated, slowly warped domain: crease-y, texture-free, cheap enough to evaluate 50 times per pixel | C1 | Chromatic Curtains, Satisfying (both in nimitz's triangle-noise lineage) | VA 7.2 family B; study:Mts3zM | **P0** |
| `float noiseSineSum3(vec3 p, int octaves)` | textureless sum of sines and cosines with a fixed rotation between octaves: cheap filaments and relief | C1 | Blue Red Shiny (FM sine relief), Cloud Ten (sine-made macro ridges), HAL 4000 (cosine phase-modulated plasma) | VA 2.1 (`noise_spiral3`) | P1 |

### B2. Cellular noise (`noise/cellular.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 cellF1F2_2(vec2 p, float jitter, uint seed, out vec2 toNearest)` | Worley F1, F2 and the nearest cell's id in [0,1), with the vector to the nearest feature; cell-relative maths for precision | C1 (3×3) | Creation Stone (Worley warp in its inner landscape) | NP 6.2; Worley 1996 | P1 |
| `vec3 cellF1F2_3(vec3 p, float jitter, uint seed, out vec3 toNearest)` | the 3D version over 27 cells | C1 (27) | — | NP 6.2 | P1 |
| `float cellEdge2(vec2 p, float jitter, uint seed)` | exact distance to the nearest Voronoi wall (two passes); constant-width borders, unlike F2-F1 | C1 (9+25) | — | NP 6.3; Quilez, Voronoi edges | P1 |
| `float cellSmooth2(vec2 p, float jitter, float sharpness, uint seed)` | smooth F1 by an exponential smooth minimum; rounded creases | C1 | — | NP 6.4 | P2 |
| `float voronoise2(vec2 p, float jitter, float blend, uint seed)` | one function spanning cell noise, value noise and Voronoi | C1 (25) | — | NP 6.5 | P2 |
| `float cellF1Metric2(vec2 p, float jitter, float minkowskiP, uint seed)` | F1 under a Minkowski distance (1 Manhattan, 2 Euclidean, large Chebyshev) | C1 | — | NP 6.1 | P2 |
| `float noiseWorley3Tiled(vec3 p, float period)` | tileable inverted F1 (1-F1) as billows in [0,1], for cloud detail | C1 (27) | — | VA 2.1 | P1 |
| `float noisePerlinWorley(float perlin01, float worleyInv)` | Perlin dilated by inverted Worley: connected masses with cauliflower billows | C0 | — | VA 2.1; Schneider 2015 | P1 |

### B3. Fractal sums (`noise/fbm.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float gainFromHurst(float hurst, float lacunarity)` | lacunarity^(-hurst): H=1 gives 0.5 at L=2 (mountains), H=0.5 gives 0.707 (brown) | C0 | — | NP 7.1 | **P0** |
| `float fbm2(vec2 p, int octaves, float lacunarity, float gain, uint seed)` / `float fbm3(vec3 p, ...)` | normalised fBm of gradient noise, with a fixed rotation and a slightly detuned lacunarity per octave so the lattice never shows; divides by (1-G^n)/(1-G) | C1 (octaves ≤ 8) | Dark Cloud (rotation, lacunarity 2.01-2.03), Volumetric Sample (rotated fBm), Aurora Lights (normalised), Warping, Cloud Ten (two steep octaves), AURORA | NP 7.1; Quilez, fbm; Musgrave in Texturing and Modeling | **P0** |
| `vec3 fbm2Deriv(vec2 p, ...)` | fBm plus its world-space gradient through octave scale and rotation (chain rule) | C1 | — | NP 11 | P1 |
| `float fbmTurb3(vec3 p, ...)` | sum of absolute octave values (Perlin turbulence), normalised to [0,1]; fire and smoke creases | C1 | Flame, Alien Core | NP 7.2 | P1 |
| `float fbmBillow3(vec3 p, ...)` | per-octave 2·abs(n)-1; puffy clouds and rounded rocks | C1 | — | NP 7.2 | P1 |
| `float fbmRidged3(vec3 p, int octaves, float lacunarity, float hurst, float offset, float ridgeGain, uint seed)` | Musgrave ridged multifractal | C1 | AURORA (its inverted value fBm with squared octave frequencies is a ridged cousin) | NP 7.3 | P1 |
| `float fbmAA2(vec2 p, float footprint, int maxOctaves, ...)` | frequency-clamped fBm: fades each octave as it approaches the pixel's Nyquist limit, with a fractional last octave. Daniel's "pixel perfect, un-aliased" at 4K | C1 | — | NP 12 | P1 |
| `float fbmHybrid3`, `float fbmEroded2`, `float fbmCell2` | hybrid multifractal; derivative-damped "erosion" fBm; fractal Worley | C1 | — | NP 7.4, 7.5 | P2 |
| `float fbmFlow2(vec2 p, float t, int octaves)` | animated fBm whose octaves rotate and are pulled back toward the previous octave (flow noise) | C1 | Plasma Globe | NP 9.4; Perlin and Neyret 2001 | P2 |

### B4. Domain warping (`noise/warp.glsl`)

Bend the address before the lookup. The richest single trick in the procedural family.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 warpVec2(vec2 p, int octaves, uint seed)` | a decorrelated 2D displacement: two fBm at far-apart offsets | C1 ×2 | Warping, Dark Cloud (vector fBm by offsets) | NP 8 | **P0** |
| `float warpFbm2(vec2 p, float amount, int octaves, uint seed)` | one-level warp: fbm(p + amount·warpVec2(p)) | C1 ×3 | Aurora Lights (counter-sliding double warp), AuroraBorealis (two-level scrolled warp) | NP 8; Musgrave, domain distortion | **P0** |
| `float warpNested2(vec2 p, float amount, int octaves, uint seed, out vec2 q, out vec2 r)` | two-level nested warp, returning the intermediate fields q and r for colouring (5 fBm calls) | C1 ×5 | Warping (study-only; learn it from NP 8) | NP 8; Quilez, domain warping | **P0** |
| `vec2 warpShear2(vec2 p, float t, float amp, float speed)` | a warp whose two components slide in opposite directions, so folds shear like a curtain in a field instead of scrolling rigidly; useful amplitude is one feature width | C1 | Aurora Lights | study:MsjfRG 6.1-6.3 | P1 |
| `vec3 warpScaledBy(vec3 p, float mask, float amp, float t)` | noise displacement weighted by a mask (for example height): calm base, wild tip | C1 | Flame (turbulence proportional to height), Alien Core (radial-masked twist) | study:MdX3zr | P1 |
| `vec3 warpRayOrigin(vec3 ro, vec3 rd, float amp, float t)` | nudge the eye per pixel with smooth noise keyed on the ray direction: a fuzzy, churning silhouette on an analytic shape with no march | C1 | Dark Cloud | study:4slGWM 6.2 | P2 |
| `vec2 warpTexScroll2(sampler2D tex, vec2 p, float t)` | one scrolling texture read at a position nudged by another, so motion never looks like a rigid scroll | C0 +T2 | AuroraBorealis | study:MdBfzR | P2 |

### B5. Flow fields (`noise/flow.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 noiseCurl2(vec2 p, uint seed)` | divergence-free 2D velocity from one analytic-gradient noise evaluation: wind with no sources or sinks | C0 | — (house swarms) | NP 9.2; Bridson et al. 2007 | P1 |
| `vec3 noiseCurl3(vec3 p, uint seed)` | divergence-free 3D velocity from three decorrelated potentials | C0 ×3 | — | NP 9.2 | P1 |
| `vec3 noiseCurl3Fbm(vec3 p, int octaves, float lacunarity, float gain, uint seed)` | multi-octave turbulent curl with power-law amplitudes | C1 | — | NP 9.2 | P2 |
| `vec3 noiseBitangent3(vec3 p, uint seed)` | divergence-free velocity as cross(grad a, grad b): two evaluations instead of three | C0 ×2 | — | NP 9.3 | P2 |
| `float flowWallRamp(float t)` / `vec3 flowPsiNearWall(vec3 psi, vec3 n, float dist, float width)` | Bridson's boundary ramp; damps only the tangential potential near a wall so flow slides along it | C0 | — | NP 9.2 | P2 |
| `float noiseFlow2(vec2 p, vec2 period, float angle, out vec2 grad)` | periodic simplex with all gradients rotated by angle (flow noise) and an exact gradient; loops in angle | C0 | — | NP 9.4; Gustavson and McEwan, psrdnoise (MIT, reference oracle only) | P2 |

### B6. Periodic and looping noise (`noise/periodic.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float noiseGradTiled2(vec2 p, ivec2 period, uint seed)` | gradient noise repeating every period cells (cell ids wrapped before hashing, safe for negatives) | C0 | — | NP 10 | P1 |
| `float fbmTiled2(vec2 p, ivec2 period, int octaves, float gain, uint seed)` | tileable fBm: lacunarity exactly 2, period doubling per octave, octaves decorrelated by seed | C1 | — | NP 10 | P1 |
| `float noiseLoop3(vec3 p, float phase01, float radius, uint seed)` | a seamless time loop: the phase walks a circle in extra noise dimensions, so phase 0 and 1 match exactly and the host can wrap its clock | C0 | Isoline Triangle (dual-phase periodic noise for a perfect 2 s loop), Bubble Rings (a seamless loop by symmetry) | NP 10 | P1 |
| `float repeatDualPhase(float x, float period, float w)` | crossfade of two phase-shifted copies so a scroll wraps invisibly | C0 | Isoline Triangle | study:Xt3yDS | P1 |
| `float noiseTorus2(vec2 uv01, float radius, uint seed)` | seamless 2D tile via 4D noise on a flat torus | C0 | — | NP 10 | P2 |

### B7. Dither and jitter masks (`noise/dither-masks.glsl`)

Two consumers share these masks: march start jitter (banding becomes fine grain) and output dither (section H8). House
floor 8: static per pixel unless the host is accumulating frames, because per-frame jitter *is* crawling grain, which
Daniel had removed.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float dthIgn(vec2 pixel)` | Jimenez interleaved gradient noise in [0,1), static; every 3×3 block holds nearly all ninths | C0 | Chromatic Curtains (static jitter and static dither, exactly the house rule) | NP 13; Jimenez 2014 | **P0** |
| `float dthR2(vec2 pixel)` | Roberts R2 low-discrepancy mask, texture-free, static | C0 | — | NP 13.2; Roberts 2018 | **P0** |
| `float dthTriFromUniform(float u)` | inverse-CDF remap of a uniform to a triangular [-1,1] that keeps the mask's spatial spectrum | C0 | — | NP 13.3 | **P0** |
| `float dthIgnFrame(vec2 pixel, int frame)` | IGN shifted 5.588238 px per frame; **only** for temporal-accumulation hosts | C0 | AURORA (animated blue-noise offset), Dry Ice (per-frame start dither) | NP 13 | P1 |
| `float dthBlue(sampler2D tile, ivec2 pixel, int channel)` | texelFetch of a tiled CC0 blue-noise mask (Peters); one channel per decision | C0 +T1 | AURORA, Hex Glitch (blue noise with a random toroidal shift) | NP 13.2; Peters, free blue-noise textures | P1 |
| `float dthGoldenStep(float u, int frame)` | fract(u + frame·0.618...): decorrelates a mask across frames when frames are accumulated | C0 | AURORA (golden-ratio animation of blue noise) | NP 13.3 | P1 |
| `vec2 halton23(int index)` / `float vanDerCorputScrambled(uint i, uint scramble)` | low-discrepancy sequences for supersampling and shutter time | C0 | Hex Glitch (stratified shutter with a scrambled van der Corput jitter) | WS 3.3 | P2 |

---

## 5. Family C: 2D drawing

The pen, the ruler and the stencil. PF is the textbook; BigWings's "The Art of Code" lessons (PF 12) are the
curriculum Daniel can watch.

### C1. 2D distance shapes (`draw2/sdf2.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float sd2Circle(vec2 p, float r)` | exact signed distance, negative inside | C0 | Audio Eclipse (the occluding moon), Heartfelt (drops) | PF 3; Quilez, 2D distance functions | **P0** |
| `float sd2Box(vec2 p, vec2 halfSize)` | exact 2D box; the input for lifting operators | C0 | Inercia (2D box as a segment), Pretty Hip (inner box distance) | PF 3 | **P0** |
| `float sd2RoundBox(vec2 p, vec2 halfSize, float cornerRadius)` | exact; the outer extent stays halfSize | C0 | — (house: the piano trail's rounded box, two copies) | PF 3 | **P0** |
| `vec2 sd2Segment(vec2 p, vec2 a, vec2 b)` | exact distance in .x and the 0..1 parameter along the segment in .y | C0 | Oscillo Donut (squared distance and parameter), Plasma Globe (point to segment) | PF 3 | **P0** |
| `float sd2Hexagon(vec2 p, float inradius)` | exact pointy-top hexagon matching `latHex` orientation | C0 | Hexagone (folded hexagon outline), Hex Glitch | PF 3 | **P0** |
| `float sd2NormMorph(vec2 p, float r, float pNorm)` | distance-like field under a p-norm, so one knob morphs hexagon or square toward circle | C0 | Hex Glitch (hexagon to circle) | study:lfscD7 4.15 | P1 |
| `float sd2Ngon(vec2 p, float inradius, float sides)` | exact regular polygon via a sector fold | C0 | — | PF 3 | P1 |
| `float sd2Star(vec2 p, float outerRadius, float points, float innerRatio)` | regular star, exact outside, a bound inside; an inner ratio above 1 moves the smooth-mirror seam onto the valleys | C0 | Starry Planes | PF 3; study:MfjyWK 6.7 | P1 |
| `float sd2Arc(vec2 p, float r, float halfAngle, float halfThickness)` | exact arc band with rounded ends | C0 | Satisfying (arc-length-correct caps) | PF 3 | P1 |
| `float sd2Triangle(vec2 p, float r)` | equilateral triangle; the sharp-cornered bound variant keeps crisp vertices where a stroke weight changes | C0 | Isoline Triangle | PF 3 | P1 |
| `float sd2Superellipse(vec2 p, float r, float n)` | Lp-norm superellipse: one exponent from circle to rounded square | C0 | HAL 4000 (its 2D slices) | PF 3 | P1 |
| `float sd2Bezier2(vec2 p, vec2 a, vec2 b, vec2 c)` | exact unsigned distance to a quadratic Bézier (cubic solve) | C0 | — | PF 3; Quilez | P2 |

### C2. 2D antialiasing (`draw2/aa.glsl`)

The expert's core skill (PF 4). Every edge the house draws goes through one of these, so "un-aliased at any
resolution" (Daniel's ruling R4) is one module's job.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float aaFill(float d, float px)` | coverage of the inside of a signed distance: a one-pixel ramp centred on the edge | C0 | Isoline Triangle (exactly one pixel of ramp at every weight) | PF 4.3 | **P0** |
| `float aaStroke(float d, float halfWidth, float px)` | coverage of a band around d = 0 | C0 | Satisfying, Hexagone | PF 4.3 | **P0** |
| `float aaWire(float d, float widthPx, float px)` | a stroke never thinner than one pixel, with opacity scaled by true/drawn width (phone-wire antialiasing): hairlines fade instead of breaking | C0 | Isoline Triangle (sub-pixel hairlines as intensity) | PF 4.5 | **P0** |
| `float aaStep(float x, float edge)` | antialiased threshold of a non-distance value: smoothstep over plus or minus fwidth(x) | C0 | Pretty Hip (soft threshold wipe with headroom) | NP 12 | **P0** |
| `float aaImplicit(float f, vec2 gradient, float px)` | coverage of the zero set of any field via f/length(gradient) | C0 | Isoline Simple (gradient-length estimators) | PF 4.4 | P1 |
| `float aaAngleFootprint(vec2 p, float px)` | pixel footprint in radians at p (px/radius); a seam-free replacement for fwidth of atan | C0 | — | PF 4.7 | P1 |
| `float aaChecker(vec2 p, vec2 footprint)` | box-filtered checkerboard: no aliasing at any distance | C0 | Dry Ice (integer XOR checkerboard) | PF 4.6; Quilez, checkerboard filtering | P1 |
| `float aaGrid(vec2 p, vec2 lineWidth)` | the "pristine grid": per-axis footprints, phone-wire clamp, fade to mean as cells go sub-pixel | C0 | — | PF 4.6 | P1 |
| `float aaCos(float x, float footprint)` | band-limited cosine: attenuated by the sinc of half the footprint, 0 when a period fits in a pixel | C0 | Cube Lines (band-limited partials) | PF 4.6; Quilez, bandlimiting | P1 |
| `float aaDetailFade(float px, float featureSize)` | 1 while a feature spans at least about 3 pixels, 0 at one pixel; fade detail toward its mean | C0 | Starry Planes (anti-moiré threshold bias), Cube Lines | PF 4.5 | P1 |
| `float aaDiskCoverage(float signedDistance, float pixelRadius)` | the exact fraction of a pixel disk covered by a straight edge | C0 | — | SR 7 | P1 |

### C3. Contours and engraving (`draw2/iso.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float isoLines(float f, float spacing, float widthPx)` | coverage of level lines of a continuous scalar every spacing; isotropic screen derivative; phone-wire clamp; fades to the mean when lines are under about 3 px apart | C0 | Isoline Triangle, Isoline Simple, Humanimation (contour plasma) | PF 7 | P1 |
| `float isoLinesGrad(float f, vec2 gradPerPixel, float spacing, float widthPx)` | the same with an analytic gradient: no derivative instructions, safe inside branches and loops | C0 | — | PF 7 | P1 |
| `vec2 isoMajorMinor(float f, float spacing, float majorEvery, float widthPx)` | (minor, major) line coverages: the cartographic two-tier hierarchy | C0 | Isoline Simple (dim minors, bold majors, five to one) | PF 7 | P1 |
| `float isoPressure(float f, float spacing, float weightField, float px)` | lines whose stroke width is modulated by a second field, so the figure is drawn by pressure, not outline (engraving, guilloche) | C0 | Isoline Triangle | study:Xt3yDS 6.3 | P2 |

### C4. 2D domain operators (`draw2/domain2.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 domToPolar(vec2 p)` / `vec2 domFromPolar(vec2 ra)` | (radius, angle) with angle in (-π, π], and its inverse | C0 | Audio Eclipse, Satisfying, HAL 4000 | PF 5.1 | **P0** |
| `vec2 domRepeat2(inout vec2 p, vec2 period)` | centred infinite repetition; p becomes local; returns the cell id | C0 | Pretty Hip (square tiling), Heartfelt (tall cells), Hexagone | PF 6.1 | **P0** |
| `float domKaleido(inout vec2 p, float sectors)` | folds p into one mirrored sector; adjacent sectors are reflections; returns the sector index | C0 | Satisfying (per-ring rotation then mirror), HAL 4000 (angular window sectors) | PF 5.2 | **P0** |
| `float domRings(inout vec2 p, float spacing)` | polar repetition in radius: returns the ring id and leaves p in the ring's local frame | C0 | Satisfying (radial cell id; everything from the id) | PF 5.2 | P1 |
| `vec2 domRepeatMirror2(inout vec2 p, vec2 period)` | repetition with odd cells mirrored so asymmetric content is exact in one evaluation | C0 | — | PF 6.1 | P1 |
| `vec2 domRepeatLimited2(inout vec2 p, vec2 period, vec2 idMin, vec2 idMax)` | finite repetition by clamping the id | C0 | — | PF 6.1 | P1 |
| `vec2 domRepeatCandidate2(vec2 p, vec2 period, int k, out vec2 cellId)` | local point for the k-th (0..3) cell that can hold the nearest copy; the caller takes the minimum | C0 | — | PF 6.1 | P1 |
| `float domKaleidoSoft(inout vec2 p, float sectors, float softness)` | kaleidoscope with the mirror crease rounded | C0 | — | PF 5.2 | P1 |
| `float domFold2(inout vec2 p, vec2 n, float offset)` | reflect p across a line if it is on the negative side; returns the side: the KIFS atom | C0 | — | PF 10.2 | P1 |
| `vec2 domInvert2(vec2 p, vec2 centre, float radiusSq, inout float stretch)` | circle inversion, multiplying stretch so distances can be corrected | C0 | Cube Lines (sphere inversion puts the detail where it is filtered), Apollonian | PF 10.5 | P1 |
| `vec2 domTurb2(vec2 p, float t, int octaves, float growth, float amp)` | Xor-style turbulence: rotated sine displacement, frequency growing per octave, amplitude falling with frequency | C1 | Starship (by its author's idiom) | PF 11 | P1 |
| `vec2 domBrick2(inout vec2 p, vec2 period, float rowShift)` | repetition with alternate rows shifted | C0 | — | PF 6.1 | P2 |
| `vec2 domLogPolar(vec2 p)` / `vec2 domDroste(vec2 p, float scaleRatio, float turns)` | log-polar (scaling becomes translation); the Escher/Droste spiral | C0 | — | PF 5.3 | P2 |

### C5. Lattices (`draw2/lattice.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec4 latHex(vec2 p)` | pointy-top hexagons with centres 1 apart by the two-grid method: xy = offset from the nearest centre, zw = that centre (a unique id) | C0 | Hexagone, Data Warehouse (Shane's minimal hex grid), Hex Glitch (cube-style coordinates) | PF 6.4; Red Blob Games, Hexagonal Grids | **P0** |
| `float latHexEdge(vec2 offset)` | distance from a hex offset to its border: 0.5 at the centre, 0 on the border | C0 | Hexagone | PF 6.4 | **P0** |
| `vec2 latHexAxial(vec2 centre)` / `float latHexSteps(vec2 a, vec2 b)` | integer axial coordinates for neighbour arithmetic; hex distance in steps | C0 | Hex Glitch | PF 6.4 | P1 |
| `float latHexNeighbourMin(vec2 p, ...)` (template with a hook) | evaluate a shape in the cell and its six neighbours and keep the best, for shapes larger than their cell | C1 (7) | Hexagone (seven-cell neighbourhood sum) | PF 6.4 | P1 |
| `vec3 latTri(vec2 p, out vec2 cellId)` | equilateral triangle cells: barycentric coordinates (the minimum is the edge distance); the id includes up/down | C0 | Geodesic (skewed triangle lattice), RM Experiment 23 | PF 6.4 | P1 |
| `float latParity(vec2 cellId)` | +1 or -1 checkerboard parity of a square-cell id | C0 | Dry Ice, Hex Glitch | PF 6.3 | P1 |

### C6. Patterns (`draw2/pattern.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 patZoomLayer(float t, float layer, float layerCount)` | infinite-zoom conveyor: x = this layer's scale, y = its fade weight, zero at both ends of its life (multiply fade by life so approaching layers brighten) | C0 | Hexagone (three layers on a conveyor belt) | PF 6.5 | P1 |
| `float patCellDelay(vec2 cellId, vec2 centre, float speed)` | a delay per cell from the cell centre's distance, so whole tiles fire together and the wave front is quantised into a mosaic | C0 | Pretty Hip, Geodesic (per-panel animation keyed to the panel centre) | study:XsBfRW 6.4 | P1 |
| `float patRadialWave(float r, float t, vec2 freqs)` | two sines of different frequency in radius: beating, travelling rings that never quite repeat | C0 | Hexagone | study:wsl3WB | P1 |
| `vec3 patTruchet(vec2 p, uint seed)` | Smith quarter-arc Truchet: distance to the arc centre-line, a path parameter continuous across tiles, the flow sign | C0 | Marble (a Truchet maze painted on the sky so the glass has something to refract) | PF 6.3; Smith 1987 | P1 |
| `vec3 patTruchetHex(vec2 p, uint seed)` / `vec4 patTruchetMulti(vec2 p, uint seed, float chance, int levels)` | three-arc hexagonal Truchet; Carlson multi-scale Truchet | C0 / C1 | — | PF 6.3; Carlson 2018 | P2 |
| `float patTenPrint(vec2 p, uint seed)` | diagonal maze: distance to the cell's random diagonal | C0 | — | PF 6.3 | P2 |
| `vec3 patJitterNet(vec2 p, float t, uint seed, float px)` | a jittered point per cell linked to its 3×3 neighbours: line coverage, node glow, nearest-node id | C1 (9) | — | PF 12 | P2 |
| `float patRippleInterference(vec2 p, vec3 sources[4], float t)` | log-weighted sum of circular ripples from a few sources | C1 | Hex Glitch | study:lfscD7 4.16 | P2 |
| `float patFlashDecay(vec2 cellId, float t, float rate)` | thresholded per-tile sawtooth with a random phase: lights up, then fades, like an LED dance floor | C0 | Humanimation, Hexagone (disco floor) | study:ltdcW7 | P2 |
| `float patSubdivide(vec2 p, float n, float pen)` | subdivision with constant pen width: the line width scales by n while the grid scales by 1/n, so cells shatter and lines keep their thickness | C0 | Hex Glitch (the shatter storm) | study:lfscD7 4.14 | P2 |

### C7. Complex numbers and 2D fractals (`draw2/complex.glsl`, `draw2/fractal2.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 cxMul`, `cxSq`, `cxDiv`, `cxExp`, `cxLog`, `cxPowReal` | complex arithmetic on (re, im) pairs; the caller guards division by zero; cxLog's seam is the negative real axis | C0 | — | PF 9.1 | P1 |
| `float fracKali2(vec2 p, vec2 c, int iters, out vec3 stats)` | the Kaliset: abs, divide by squared length, subtract c, repeated; returns accumulated change of length. Clip outliers before accumulating | C1 | Sphere Intersect (a texture factory from one line) | PF 10.4 | P1 |
| `float fracApollonian2(vec2 p, float strength, int iters, out float trap)` | repeat-and-invert packing; distance divided by the accumulated inversion stretch | C1 | Apollonian | PF 10.5 | P1 |
| `float fracMandel(vec2 c, int maxIter, float bailout, out float smoothIter, out vec4 trap)` / `fracJulia` | escape-time sets with a distance estimate (for antialiasing), smooth iteration count and orbit traps | C1 (≤ 256) | — | PF 9 | P2 |
| `float fracKifs2`, `fracKoch`, `fracSierpinski2` | 2D kaleidoscopic IFS family; distance over scale^iters | C1 | Hex Glitch (a two-level IFS with a hex clip) | PF 10.2 | P2 |

### C8. Text (`draw2/text.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float txtSeg7(vec2 p, float digit, float stroke)` | a seven-segment digit distance in a [-0.5,0.5]×[-1,1] cell; lets the bench and every debug view label itself | C0 | Inercia (LED meters and dot matrix) | PF 8 | P1 |
| `float txtAtlasSdf(sampler2D atlas, vec2 glyphUv, float code, float bias)` / `float txtMedian3(vec3 msdf)` / `float txtScreenPxRange(...)` | single-channel and multi-channel SDF glyph atlases | C0 +T1 | — | PF 8; Green 2007; Chlumský, MSDF | P2 |
| `vec4 txtLayers(float d, float px, vec4 fill, vec4 outline, float ow, vec4 glow, float gw)` | fill, outline and glow from one distance, premultiplied | C0 | — | PF 8; Green 2007 | P2 |

---

## 6. Family D: 3D shape

Signed distance fields: a function that says how far any point is from the surface, which is all a marcher needs. SR is
the textbook; Quilez's distance-function articles and Mercury's hg_sdf library are the canon.

### D1. Distance shapes (`sdf/shapes.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float sdSphere(vec3 p, float r)` | exact | C0 | almost every SDF shader | SR 4.1 | **P0** |
| `float sdBox(vec3 p, vec3 halfSize)` | exact inside and outside | C0 | Inercia, Rhodium (a thin wide slab), Blue Red Shiny (wall lattice) | SR 4.1 | **P0** |
| `float sdRoundBox(vec3 p, vec3 halfSize, float cornerRadius)` | exact; outer extent stays halfSize | C0 | Inercia | SR 4.1 | **P0** |
| `float sdPlane(vec3 p, vec3 unitNormal, float offset)` | exact only when the normal is unit length (the caller's duty) | C0 | Humanimation (room planes), Sincos 3D | SR 4.1 | **P0** |
| `float sdTorusY(vec3 p, float ringRadius, float tubeRadius)` | exact torus in the xz plane | C0 | — (house `torus-ring` chunk) | SR 4.1 | **P0** |
| `float sdCapsule(vec3 p, vec3 a, vec3 b, float r)` | exact distance to a segment inflated by r | C0 | Humanimation (a capsule-skeleton figure), Plasma Globe (bolts are segments) | SR 4.1 | **P0** |
| `float sdCylinderY(vec3 p, float r, float halfHeight)` | exact capped cylinder | C0 | Inercia (knobs) | SR 4.1 | P1 |
| `float sdConeCappedY(vec3 p, float h, float rBottom, float rTop)` | exact cone frustum | C0 | Inercia (tapered knob) | SR 4.1 | P1 |
| `float sdRoundConeAB(vec3 p, vec3 a, vec3 b, float ra, float rb)` | two spheres joined by their tangent cone | C0 | — | SR 4.1 | P1 |
| `float sdHexPrismZ(vec3 p, float apothem, float halfDepth)` | exact hexagonal prism | C0 | Inercia (hex nut from three slabs is the cheap form) | SR 4.1 | P1 |
| `float sdOctahedron(vec3 p, float s)` | exact regular octahedron (not the cheap planar bound) | C0 | — | SR 4.1 | P1 |
| `float sbEllipsoid(vec3 p, vec3 radii)` | gradient-normalised bound: never exceeds the true distance, tight near the surface | C0 | Flame (an ellipsoid by squashing space) | SR 4.1 | P1 |
| `float sbPolyhedron(vec3 p, float r, int solidKind)` | generalised distance functions (Akleman and Chen, as in Mercury): the max of plane distances over a face-normal table | C1 (≤ 19 planes) | Glitch Transform (dodecahedron and icosahedron), Creation Stone | SR 4.1; Akleman and Chen | P1 |
| `float sbSuperquadric(vec3 p, vec3 r, float n)` | Lp-norm superellipsoid bound: n=2 sphere, large n rounded cube | C0 | Saturday (L4), Just a Cube (L8), HAL 4000 (cube/torus/sphere morph); house: four superquadric copies | SR 4.1 | P1 |
| `float sdHelix(vec3 p, float radius, float pitch, float tube)` | distance to a helix by its cross-section | C0 | Sincos 3D, Blue Red Shiny (neon spiral tubes) | SR 4.1 | P2 |
| `float udTriangle(vec3 p, vec3 a, vec3 b, vec3 c)` | exact unsigned distance to a triangle | C0 | — | SR 4.1 | P2 |

### D2. Lifting 2D to 3D (`sdf/lift.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 liftRevolveY(vec3 p, float offset)` | the 2D point at which to evaluate a 2D distance to revolve it about y; exact if the 2D field is | C0 | Inercia (turned knobs) | SR 4.2 | P1 |
| `float opExtrude(float d2, float z, float halfDepth)` | exact extrusion of a 2D distance along z | C0 | Inercia (2D box extruded) | SR 4.2 | P1 |
| `vec3 domElongate(vec3 p, vec3 halfLength, out float interior)` | stretch a shape without distorting its rounded ends | C0 | — | SR 4.3 | P2 |

### D3. Combination (`sdf/combine.glsl`)

Each operator states its exactness (SR 4.4): E exact, EO exact outside only, B a bound, X may overestimate.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float opUnion(float a, float b)` | min; EO (exact outside, unreliable deep inside: never use the interior for refraction or thickness) | C0 | all | SR 4.4 | **P0** |
| `float opIntersect(float a, float b)` | max; B | C0 | Alien Core (bars as two slabs), Blue Red Shiny (carved tunnel) | SR 4.4 | **P0** |
| `float opSubtract(float a, float b)` | a minus b; B. House order is "a minus b" (Quilez's opSubtraction uses the opposite order; flip on port) | C0 | Inercia (boolean carve), RM Experiment 23 (perforated shell) | SR 4.4 | **P0** |
| `vec2 opPick(vec2 a, vec2 b)` | union of (distance, material id) pairs keeping the nearer id | C0 | Humanimation (material-id union), Apollonian (1-bit material id) | SR 4.10 | **P0** |
| `float opSmin(float a, float b, float k)` | quadratic smooth union; k is the blend thickness in world units; conservative bound; order-dependent | C0 | Alien Core (a radius far larger than the parts turns sticks into sinew), Humanimation, Volumetric Sample (ground-fog skirt with k = 22) | SR 4.5; Quilez, smooth minimum | **P0** |
| `vec2 opSminMix(float a, float b, float k)` | opSmin in .x; the blend weight of b in .y for mixing materials with the same weight as the shape | C0 | Glitch Transform (material carried by the same weight) | SR 4.5 | **P0** |
| `float opSmax(float a, float b, float k)` | smooth intersection, -opSmin(-a,-b,k); bound | C0 | Bubble Rings (rounded intersection fillet), Geodesic (circular smooth max) | SR 4.5 | **P0** |
| `float opRound(float d, float r)` | d - r: rounds convex edges and grows the shape by r; exact if d is | C0 | — | SR 4.3 | **P0** |
| `float opOnion(float d, float thickness)` | a hollow shell; exact if d is; repeatable for concentric layers | C0 | Bubble Rings (thick shell), Flame (abs() shell) | SR 4.3 | **P0** |
| `float opUniformScale(float dAtScaledPoint, float scale)` | the caller evaluates the shape at p/scale; returns d·scale; exact. Non-uniform scale is only a bound | C0 | Alien Core (breathing by scaling the query point), Plasma Globe (fatten by shrinking space) | SR 4.7 | **P0** |
| `float opXor(float a, float b)` | exact inside and outside for exact inputs | C0 | Hex Glitch (2D parity layers) | SR 4.4 | P1 |
| `float opSminCircular(float a, float b, float k)` | a fillet that is exactly circular between perpendicular surfaces | C0 | — | SR 4.5 | P1 |
| `float opSminExp(float a, float b, float k)` | exponential smooth union: order-independent, slightly distorts shapes everywhere | C0 | Humanimation (limbs to torso) | SR 4.5 | P1 |
| `float opSsubtract(float a, float b, float k)` | smooth a minus b; bound | C0 | — | SR 4.5 | P1 |
| `float opDisplace(float d, float displacement, float lipschitz)` | (d + displacement)/(1 + lipschitz): stays a bound if the Lipschitz figure is honest (for a product-of-sines bump, amplitude × frequency) | C0 | Rhodium (noise-inflated, ×5 over-reporting hidden by blur), Flame, Alien Core, Just a Cube (micro-bump lattice) | SR 4.9 | P1 |
| `float opChamferUnion`, `opRoundUnionLocal`, `opStairsUnion`, `opGroove` | Mercury's right-angle operators: bevels, steps and grooves shaped in the (a,b) plane; valid only near perpendicular meetings | C0 | — | SR 4.6; Mercury hg_sdf | P2 |

### D4. 3D domain operators (`sdf/domain3.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 domRigid(vec3 p, mat3 rotation, vec3 position)` | the point in object space for an object placed by rotation then position (applies the inverse); exact | C0 | all placed objects | SR 4.7 | **P0** |
| `vec3 domMirror(vec3 p, vec3 axisMask)` | abs() on masked axes; exact if content does not cross the mirror planes | C0 | Blue Red Shiny (mirror the path-relative space so one quadrant covers the tunnel), Just a Cube (ceiling and floor share one line) | SR 4.8 | P1 |
| `vec3 domTwistY(vec3 p, float rate)` + `float lipTwist(float rate, float maxRadius)` | twist about y by rate radians per unit height; divide the result by lipTwist to stay a bound (sqrt(1+k²R²) is too small) | C0 | Glitch Transform (height-dependent twist), Rhodium, Marble (twisted vanes), Alien Core (radial-masked twist) | SR 4.9 | P1 |
| `vec3 domRepeat(inout vec3 p, vec3 period)` / `domRepeatLimited` | infinite or clamped-id grid repetition; single evaluation exact only for identical, cell-symmetric content | C0 | Blue Red Shiny (a lattice of boxes carved into architecture) | SR 4.8 | P1 |
| `float domPolar(inout vec2 p, float count)` | angular repetition around an axis; returns the sector id | C0 | Marble (seven vanes), Inercia | SR 4.8 | P1 |
| `float domReflect(inout vec3 p, vec3 n, float offset)` | fold across an arbitrary plane; returns the side | C0 | — | SR 4.8 | P1 |
| `vec3 domFoldIcosa(vec3 p)` | mirror folds into the 1/120 fundamental wedge of the icosahedral group, so one sliver of geometry tiles the sphere exactly and density is a free knob | C1 (about 5 folds) | Geodesic; house avatar core (written fresh, because the avatar's current core has CC BY-NC-SA ancestry) | SR 4.8; study:llVXRd 6.1 | P1 |
| `vec3 domInvert3(vec3 p, float radiusSq, inout float scale)` | sphere inversion with scale bookkeeping | C0 | Apollonian | PF 10.5 | P1 |
| `vec3 domRepeatCandidate(...)`, `domRepeatMirror(...)`, `domPolarCandidate(...)` | the seam-free repetition family (min over candidate cells; Fizzer's mirrored grid) | C1 | — | SR 4.8 | P2 |
| `vec3 domBend(vec3 p, float rate)` | bend about an axis; divide by lipTwist | C0 | — | SR 4.9 | P2 |

### D5. 3D fractals (`sdf/fractal3.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float fracApollonian3(vec3 p, float strength, int iters, out float trap)` | repeat-and-invert 3D packing; slicing it with a tumbling plane gives organic 2D morphing for free | C1 | Apollonian | PF 10.5 | P1 |
| `vec3 fracKaliset3(vec3 p, vec3 c, int iters, out float acc)` | the 3D Kaliset hot-flow field over a mirrored-fract tiling | C1 | Sphere Intersect | PF 10.4 | P2 |
| `vec3 fracBoxFold`, `fracSphereFold`, `float fracMandelbox`, `fracMandelbulb`, `fracMenger`, `vec3 fracTetraFold` | the folding-fractal family with running derivatives for march-safe distance | C1 | — | PF 10.3, 10.6-10.8 | P2 |

### D6. Surface detail (`sdf/detail.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float sdMicroBump(vec3 p, float amp, float freq)` | a product-of-sines bump lattice with a declared Lipschitz figure; sub-visible in the silhouette, visible in the normals (surface finish is a normal-step decision) | C0 | Just a Cube | SR 4.9; study:3XdXRr 6.6 | P1 |
| `float sbFbmDetail(vec3 p, float hostDistance, float footprint, int maxOctaves)` | grows octaves of a sphere-grid noise distance onto a host surface, stopping below the pixel footprint | C1 | — | SR 4.9 | P2 |
| `vec3 bumpTriplanar(sampler2D tex, vec3 p, vec3 n, float mip, float k)` | triplanar bump from a blurred mip (low-frequency waviness reads as hand-made, high frequency as dirty) | C0 +T3 | Creation Stone | SR 6.5 | P2 |

---

## 7. Family E: Rays

From a pixel to a point on a surface. The house rule underneath (shader-craft ceiling): **analytic before iterative**.
If a closed form exists, solve it; march only what has no formula.

### E1. Analytic intersection and bounds (`ray/intersect.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 ixSphere(vec3 ro, vec3 rd, vec3 centre, float r)` | entry and exit t by the precision-friendly perpendicular form; vec2(-1) on a miss; both roots are returned because glass and halos need the far one | C0 | Marble, Plasma Globe, Sphere Intersect, Dark Cloud (half-chord through a sphere), Dry Ice, Humanimation (bounding-sphere gate), Creation Stone (bounding-sphere exit) | SR 5.10; Quilez, intersectors | **P0** |
| `vec2 ixBox(vec3 roLocal, vec3 rdLocal, vec3 halfSize, out vec3 entryNormal)` | slab-method entry and exit in box space with a branchless entry normal | C0 | Cube Lines, Dry Ice, Inercia (cell exit distance), AURORA (slab bound for the aurora) | SR 5.10 | **P0** |
| `float ixPlane(vec3 ro, vec3 rd, vec3 n, float offset)` | hit distance along the ray, or -1 if parallel or behind; caps a march at the ground | C0 | Dry Ice (downward only), Hexagone (analytic floor with a mirrored hit), Starry Planes (every sheet is a plane) | SR 5.10 | **P0** |
| `vec2 ixSlabY(float oy, float dy, float y0, float y1)` | entry and exit of a horizontal slab; far < near means a miss. Bounds every layer effect (cloud deck, aurora shell) | C0 | AURORA (its box floor is the curtain's hem), Cloud Ten | VA 3.1 | **P0** |
| `vec2 ixShell(vec3 o, vec3 d, vec3 c, float rIn, float rOut)` | the first ray segment inside a spherical shell, camera inside, below or above | C0 | — | VA 3.1 | P1 |
| `vec2 rmClipToBox(vec3 ro, vec3 rd, vec3 centre, vec3 halfSize, vec2 tRange)` | narrows a march to the scene's bounding box; x > y means skip marching entirely | C0 | Humanimation (bounding-sphere gate), Creation Stone | SR 5.10 | P1 |
| `bool bvCanSkip(float boundDistance, float bestSoFar)` | true when an enclosed part cannot beat the current best distance | C0 | Humanimation (performance hygiene) | SR 5.10 | P1 |
| `vec2 ixSphereAlt(float r0, float mu0, float R)` | ray-sphere from radius and zenith cosine, precise at planet scale | C0 | — | VA 4.2 | P2 |
| `vec4 ixBilinearPatch(vec3 ro, vec3 rd, ...)` | ray against a hyperbolic-paraboloid saddle, both roots; its discriminant gives free silhouette lines | C0 | Cube Lines | study:NslGRN 6.5 | P2 |

### E2. Cameras (`ray/camera.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `mat3 camLookAt(vec3 ro, vec3 target, float roll)` | right-handed look-at basis (camera looks down its own -z), with roll | C0 | nearly all 3D loved shaders | SR 5.1 | **P0** |
| `vec3 camRay(vec2 fragCoord, vec2 res, mat3 basis, float focal)` | unit-length world ray through the pixel centre; focal sets the field of view (a large focal is the telephoto "jewel" look) | C0 | Bubble Rings (long lens), Volumetric Sample (telephoto), Plasma Globe, Starry Planes (field of view by focal constant) | SR 5.1 | **P0** |
| `float camPixelAngle(float fovY, float heightPx)` | radians subtended by one pixel; the footprint at distance t is t times this. Drives every epsilon and level of detail | C0 | AURORA (distance-scaled normal epsilon) | SR 5.1 | **P0** |
| `vec3 camOrbit(vec2 mouse01, float t, float radius, vec3 target)` | an orbit position from the mouse with an auto-yaw when untouched (the thumbnail shows a good pose, not iMouse zero) | C0 | Glitch Transform, Dry Ice, Marble, Geodesic, Plasma Globe, Creation Stone | SR 5.1 | P1 |
| `vec3 camOrthoRay(vec2 p, mat3 basis, float scale, out vec3 ro)` | orthographic ray: a product-shot look; every cell the same size on screen | C0 | Inercia | study:cs2GWD 6.9 | P1 |
| `vec3 pathLissajous3(float t, vec3 amp, vec3 freq, out vec3 vel, out vec3 acc)` | an analytic flight path with exact first and second derivatives, for a smooth look-direction and a banking roll | C0 | Starry Planes (exact derivatives), Blue Red Shiny (beating cosines) | study:MfjyWK 6.4 | P1 |
| `mat3 camBanked(vec3 vel, vec3 acc, float bankGain)` | a camera frame that banks into turns from the path's acceleration | C0 | Starry Planes, Cloud Ten (roll-coupled yaw) | study:MfjyWK | P1 |
| `vec2 camBarrel(vec2 p, float k)` | breathing barrel or curved-glass bulge of screen coordinates | C0 | Oscillo Donut (CRT glass), Data Warehouse (breathing barrel lens) | CP 7.2 | P1 |
| `vec3 camFootprint(...)` | world-space pixel footprint from neighbour rays (ray differentials), replacing dFdx for texture fetches inside loops | C0 | — | SR 6.5 | P2 |
| `vec3 camShake(float t, float period, float decay, float amp)` | a periodic decaying camera kick (also widens the depth-of-field disc: a cheap motion-blur stand-in) | C0 | Rhodium | study:llK3Dy | P2 |
| `vec3 camEdgeDroop(vec3 rd, float k)` | bend edge rays down for a curved planetary horizon | C0 | Cloud Ten | study:XtS3DD | P2 |

### E3. Marchers (`ray/march.glsl`)

A marcher calls the hook `float mapScene(vec3 p)` (or `vec2 mapSceneId(vec3 p)` for distance plus material) that the
host defines; the composer emits its prototype (architecture 4.2).

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float rmEpsilon(float t, float pixelAngle, float epsMin)` | hit threshold max(epsMin, c·pixelAngle·t): constant screen-space error | C0 | — | SR 5.1 | **P0** |
| `vec4 rmSphereTrace(vec3 ro, vec3 rd, vec2 tRange, float pixelAngle, float omega, int maxSteps)` **hook** | Hart sphere tracing with a step factor omega (1 exact; below 1 under-relaxed for fields that lie) and an explicit cap. Returns (t, steps, the smallest d/t seen, hit). The smallest d/t is the cone-tracking quantity for silhouette antialiasing and closest-approach glow | C2 | Glitch Transform (under-relaxation), Geodesic (0.9), Apollonian (0.6), RM Experiment 23 (0.5), Alien Core (half steps), Humanimation, Creation Stone | SR 5.2; Hart 1996 | **P0** |
| `float rmPassStep(float d, float passthrough, float density)` | the step of a pass-through march: passthrough + abs(d)/density, never zero, so a ray crosses surfaces and keeps collecting light | C0 | Bubble Rings (never stop at the surface), Flame (abs plus a minimum step) | PF 10.8 (`glowStep`) | **P0** |
| `float rmHybridStep(float sdf, float adaptive)` | max(sdf, adaptive): leap through empty space, take the fixed volume step inside | C0 | Volumetric Sample (one max() for empty-space skipping) | VA 3.2 (`march_stepSDF`) | **P0** |
| `float rmJitterStart(float tStart, float dt, float u)` | tStart + u·dt with u from a static mask: banding becomes fine grain | C0 | Dry Ice, Marble (jittered first inner step), Creation Stone (jittered step and IOR), AURORA | VA 3.5 | **P0** |
| `vec4 rmRelaxed(...)` **hook** | Keinert over-relaxation (omega about 1.2) with the overlap check and fallback | C2 | Plasma Globe (over-relaxed sphere tracing) | SR 5.3; Keinert et al. 2014 | P1 |
| `vec4 rmBacktrack(...)` **hook** | for fields that may overestimate: on a sign change, bisect inside the bracket; slower but hole-free | C2 | Saturday (backstep to the closest approach) | SR 5.6 | P1 |
| `vec4 rmCellClamped(vec3 ro, vec3 rd, vec3 cellSize, ...)` **hook** | clamps each step to the current cell's exit so every cell can hold a different animated object: a scene becomes a catalogue of modules on a grid | C2 | Inercia (the pegboard march) | study:cs2GWD 6.1 | P1 |
| `vec4 rmPlaneStack(vec3 ro, vec3 rd, float spacing, int layers)` **hook** | exact front-to-back walk over parallel analytic planes, each sampled by a 2D layer hook; no marching error, early exit when opaque | C2 (layers) | Starry Planes, HAL 4000 (Z-sliced contours), Chromatic Curtains (sheets) | study:MfjyWK 6.1 | P1 |
| `float rmHeightField(vec3 ro, vec3 rd, vec2 tRange, float slopeBound, int steps)` **hook** | slope-bounded stepping over a height function then regula-falsi refinement | C2 | HAL 4000 (terrain by vertical gap) | WS 9.6 | P1 |
| `vec2 rmScout(vec3 ro, vec3 rd, vec2 tRange, int steps)` **hook** | a coarse first pass that finds where the surface or volume begins; the real march starts just before it | C2 (small) | Cloud Ten (17-step scout) | study:XtS3DD 6.3 | P1 |
| `float rmRefine(vec3 ro, vec3 rd, float t, float pixelAngle, int iters)` **hook** | Keinert discontinuity reduction: pull the hit onto a consistent offset surface | C1 | — | SR 5.5 | P2 |
| `vec2 rmConePass(...)` **hook** | one coarse cone-marching pass whose result seeds child pixels (multipass) | C4 | — | SR 5.8 | P2 |
| `vec3 rmSecondaryOrigin(vec3 p, vec3 n, float fAtHit, float epsMin, float side)` | self-intersection-free origin for shadow, reflection and refraction rays | C0 | — | SR 5.7 | P1 |

### E4. Normals (`ray/normals.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 nrmTetra(vec3 p, float h)` **hook** | four-tap tetrahedron gradient, normalised, written as a loop so the scene is not inlined four times | C1 (4 hooks) | Blue Red Shiny, Humanimation (four-tap loop), Creation Stone | SR 6.1; Quilez, normals for an SDF | **P0** |
| `float nrmEps(float t, float pixelAngle, float materialScale)` | normal epsilon proportional to the pixel footprint (distant detail does not sparkle); a per-material scale doubles as a cheap bevel | C0 | AURORA (distance-scaled epsilon), Inercia (per-material epsilon) | SR 6.1 | **P0** |
| `vec3 nrmCentral(vec3 p, float h)` **hook** | six-tap central differences; reference and debug only | C1 (6) | Glitch Transform, Geodesic, HAL 4000, Saturday | SR 6.1 | P1 |
| `float nrmCurvature(vec3 p, float h)` **hook** | tetrahedral Laplacian estimate: an edge mask at one width rounds normals, at another scales texture (the jeweller's polishing wheel) | C1 (4) | Creation Stone | study:XdcyDM 6.2 | P1 |
| `vec3 nrmHeight2(vec2 p, float h)` **hook** | normal of a 2D height field by differences; resolution-independent bump relief | C1 (3-4) | Heartfelt, Warping, AURORA (bumped snow) | SR 6.1 | P1 |
| `vec3 nrmFacet(vec3 n, float steps)` | quantise a normal for a low-poly look while textures keep the smooth one | C0 | Humanimation | study:ltdcW7 | P2 |

### E5. 3D antialiasing (`ray/aa3.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float aaConeCoverage(float minDistOverT, float pixelAngle)` | silhouette coverage from the closest angular approach the march recorded (floor 6: hit or miss is a boolean, and the boolean is the staircase) | C0 | — (house avatar's cone tracking) | SR 7.2; Hart 1996 | **P0** |
| `float aaDiscriminantEdge(float disc, float px)` | an analytic edge distance from a ray-quadric discriminant: antialiasing, "don't refract at the rim" and darkened silhouettes from one number | C0 | Marble, Cube Lines | study:XsSGDh 6.2 | P1 |
| `int aaCoverageLayers(...)` **hook** | collects up to four front-to-back near-miss layers with coverage; the caller shades each | C2 | — | SR 7.2 | P2 |
| supersampling (host-level loop, not a function) | rotated-grid 4 sample or 2×2; cached supersampling that only repeats the expensive part at edges | C2 ×n | Dry Ice (rook pattern), Warping (2×2), Cube Lines (cached at edges) | SR 7.4 | P1 |

---

## 8. Family F: Light and material

What light does at a surface. LM is the textbook; Burley 2012, Karis 2013 and the Filament documentation are the
canon for physically based shading; Quilez's outdoor lighting article is the canon for the shader-art rig.

### F1. Diffuse (`light/diffuse.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float litLambert(vec3 n, vec3 l)` | max(dot(n,l),0); the house folds 1/π into light colours | C0 | most lit shaders | LM 2.1 | **P0** |
| `float litHalfLambert(vec3 n, vec3 l)` | (0.5·NoL+0.5)²: non-physical, keeps back faces shaped | C0 | Cube Lines (half-Lambert cool fill) | LM 2.2 | **P0** |
| `float litWrapDiffuse(vec3 n, vec3 l, float w)` | energy-normalised wrap lighting, max((NoL+w)/(1+w)², 0) | C0 | Glitch Transform (wrapped key), Warping (wrapped diffuse) | LM 2.2 | **P0** |
| `vec3 litHemisphere(vec3 n, vec3 skyCol, vec3 groundCol)` | sky/ground irradiance mixed by 0.5+0.5·n.y; exact for an unoccluded uniform dome | C0 | Warping, Geodesic (wrapped hemisphere ambient), Glitch Transform | LM 2.4 | **P0** |
| `float litDirDeriv(float fieldHere, float fieldTowardLight, float eps)` | NoL from one extra field sample toward the light: emboss and volume lighting without normals | C0 | Marble (emboss by directional density difference) | LM 2.5 | P1 |
| `vec3 litTerminatorScatter(float NoL, vec3 col, float width)` | a warm band just past the terminator for skin-like softness | C0 | — | LM 9.1 | P2 |
| `float litBurley(float NoL, float NoV, float LoH, float roughness)` | Disney diffuse: brightens rough surfaces at grazing angles | C0 | — | LM 2.3; Burley 2012 | P2 |

### F2. Specular (`light/specular.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float litBlinnPhong(vec3 n, vec3 h, float shininess)` | normalised Blinn-Phong, (s+8)/(8π)·max(NoH,0)^s: energy constant as the highlight sharpens | C0 | Inercia, Rhodium, RM Experiment 23 | LM 3.2 | **P0** |
| `float litShininessFromAlpha(float alpha)` | Blinn exponent equivalent to a microfacet width, 2/α² - 2 | C0 | — | LM 3.3 | P1 |
| `float litGgxD(float NoH, float alpha)`, `float litSmithVis(float NoV, float NoL, float alpha)`, `float litSmithVisFast(...)`, `vec3 litSpecGGX(vec3 n, vec3 v, vec3 l, vec3 F0, float alpha)` | the Cook-Torrance GGX lobe with height-correlated Smith visibility; alpha = roughness² | C0 | — | LM 4; Karis 2013; Filament | P1 |
| `float litGgxDAniso(...)` | anisotropic GGX for brushed metal | C0 | — | LM 4.2 | P2 |
| `float litSpecAAAlpha(vec3 n, float alpha)` | widen alpha by the screen-space normal variance (geometric specular antialiasing) | C0 | — | LM 4.8 | P2 |
| `vec3 litEnergyCompensation(vec3 F0, float Ewhite)` | restores the energy rough surfaces lose to multiple scattering | C0 | — | LM 4.7 | P2 |

### F3. Fresnel and rim (`light/fresnel.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float litFresnelSchlick(float cosTheta, float F0)` / `vec3 litFresnelSchlick(vec3 F0, float cosTheta)` | F0 + (1-F0)(1-cos)^5; use VoH inside the BRDF and NoV for environment light | C0 | Marble (with reflection occlusion), Just a Cube (squared, no floor: a dark mirror), Saturday (floored at 0.5: always polished metal), Cube Lines (soft inner, hard outer), Creation Stone | LM 5.3 | **P0** |
| `float litF0FromIor(float ior)` | ((ior-1)/(ior+1))²: water 0.02, glass 0.04, diamond about 0.17 | C0 | — | LM 5.2 | **P0** |
| `float litRim(float NoV, float power)` | (1-NoV)^power: an art rim term, deliberately not called Fresnel and never mixed into a physically based path. A small power (about 0.2) flattens a sphere into a glowing disc | C0 | RM Experiment 23 (flattened facing glow), Data Warehouse (inverted rim), Geodesic (faint white rim) | LM 5.6 | **P0** |
| `float litFresnelDielectric(float cosI, float eta)` | exact unpolarised Fresnel; 1 under total internal reflection | C0 | — | LM 5.4 | P1 |
| `vec3 litFresnelConductor(...)`, `vec3 litFresnelEdgeTint(...)` | metals by complex index, or by reflectivity and edge tint | C0 | — | LM 5.5 | P2 |

### F4. Lights (`light/lights.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float litInverseSquare(float dist, float radius)` | windowed inverse-square falloff that reaches zero at radius | C0 | Dry Ice (a light riding the white ball; even the ambient falls off), Apollonian (cos × inverse square gives 1/r³: a tighter pool), Volumetric Sample (orbiting coloured lights) | LM 6.2 | **P0** |
| `float litSpotCone(vec3 l, vec3 spotDir, float cosOuter, float cosInner)` | smooth, squared angular falloff | C0 | Humanimation (spotlight pool doubling as fog) | LM 6.2 | P1 |
| `bool litLuminanceCull(vec3 lightCol, float dist, float threshold)` | skip lights whose contribution falls below a threshold (makes nested marches affordable) | C0 | Volumetric Sample | study:tsScDG 6.9 | P1 |
| `vec3 litSphereLightPoint(vec3 toCenter, vec3 r, float radius)` / `float litAreaAlpha(...)` | Karis representative point for sphere lights; area-light normalisation (the divisor constant must be verified before pinning) | C0 | — | LM 6.3; Karis 2013 | P2 |
| `vec3 litLineLight(vec3 p, vec3 n, vec3 a, vec3 b, vec3 col)` | diffuse from a line-segment emitter (an aurora lighting snow) | C0 | AURORA | study:ttScDc 5.17 | P2 |

### F5. Visibility: shadows and occlusion (`light/visibility.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float visSoftShadow(vec3 ro, vec3 rd, vec2 tRange, float lightAngle, int maxSteps)` **hook** | light visibility in [0,1] by the closest-approach penumbra estimate (Aaltonen's triangulated form: fewer bands); lightAngle is the light's angular radius | C2 | Glitch Transform (penumbra at half strength), Rhodium (nearest-miss ratio), Inercia (marched hard shadows) | SR 6.2; LM 7.2; Quilez, soft shadows; Aaltonen 2018 | **P0** |
| `float visAO(vec3 p, vec3 n, float reach, float falloff)` **hook** | five samples along the normal (Evans, Quilez); 1 is fully open | C1 (5) | Glitch Transform, Humanimation (AO grounds the feet) | SR 6.3; LM 7.4; Evans 2006 | **P0** |
| `vec3 visColouredPenumbra(float shadow, vec3 exponents)` | per-channel power of the shadow so penumbrae warm before they darken | C0 | — | LM 7.2 | P1 |
| `float visSphereOcclusion(vec3 p, vec3 n, vec4 sphere)` | closed-form occlusion by a sphere; no march | C0 | Marble (analytic contact shadow) | LM 7.3 | P1 |
| `vec3 visAOMultiBounce(float ao, vec3 albedo)` | Jimenez's cubic fit: bright albedo recovers light; never darker than ao | C0 | — | LM 7.4; Jimenez 2016 | P1 |
| `float visSpecularOcclusion(float NoV, float ao, float alpha)` / `float visHorizonFade(vec3 r, vec3 nGeom, float k)` | Lagarde's specular AO; fade reflections that dip below the surface | C0 | Marble (reflection occlusion by direction) | LM 7.5; Lagarde and de Rousiers 2014 | P1 |
| `float visBoxSoftShadow(...)` | analytic soft shadow of a box from the minimum angular edge distance | C0 | Cube Lines | study:NslGRN | P2 |
| `float visShadow2D(vec2 p, vec2 light, ...)` **hook** | 2D sphere-traced shadow whose softness grows with the occluder's distance from the light; both branches stitched to meet | C2 | Apollonian | study:7d2fDW 6.1-6.2 | P2 |
| `float visSoftShadowInner(...)` **hook** | inner-and-outer penumbra variant that marches through thin occluders | C2 | — | SR 6.2 | P2 |

### F6. Environment (`light/env.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 litStudioEnv(vec3 dir, float roughness, StudioParams s)` | a procedural dark dome with soft boxes whose edges widen with roughness and whose rims are brighter than their centres (a real diffuser panel): the environment metals and glass need | C0 | Just a Cube (rim-bright soft box), Saturday (analytic studio), Creation Stone (up-facing soft box); house: five PMREM soft-box copies across the piano studies | LM 8.1 | **P0** |
| `vec3 litFloorPool(vec3 p, vec3 centre, float radius, vec3 col)` | an analytic pool of light on the floor plus a sky rim, so an object has weight with no visible ground edge | C0 | Just a Cube, Cube Lines (spotlight pool fading into the sky band); house: three floor-halo copies | LM 8.1 | **P0** |
| `vec3 litSkyLobes(vec3 rd, vec3 sunDir, vec4 lobes)` | a procedural sky of stacked exponential lobes; a very sharp lobe plus a broad one reads as a pinpoint plus bloom | C0 | Sphere Intersect, Cloud Ten (a sun of four lobes of different temperature) | VA 4.5 | P1 |
| `vec2 litEnvBRDFApprox(float NoV, float roughness)` | analytic split-sum scale and bias, so specular = prefiltered·(F0·A+B) with no table | C0 | — | LM 8.4; Karis 2013 | P1 |
| `vec3 litShIrradiance(vec3 n, vec3 sh[9])` / `vec3 litCubePrefiltered(...)` / `vec3 litIblSpecular(...)` | spherical-harmonic irradiance; mip-by-roughness cube fetch; split-sum with multiple scattering | C0 / +T1 | — | LM 8.2-8.4; Ramamoorthi and Hanrahan 2001 | P2 |

### F7. Translucency, glass and optics (`light/glass.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `bool litRefractTIR(vec3 i, vec3 n, float eta, out vec3 t)` | Snell refraction with eta = n_from/n_to; false on total internal reflection, so the caller reflects | C0 | Marble (sided refraction with an always-outward normal; a deliberately low IOR of 1.04), Cube Lines (refraction plus an internal mirror bounce), Creation Stone (jittered IOR) | LM 10.1 | **P0** |
| `vec3 litSigmaFromColour(vec3 colourAtDist, float dist)` | absorption coefficient -ln(c)/dist, so white light becomes colour c after dist | C0 | Marble (body tint makes the middle darker and greener: thick glass) | LM 9.4 | **P0** |
| `vec3 litGlassMarch(vec3 ro, vec3 rd, float ior, vec3 sigma, int bounces)` **hook** | two-sided glass: refract in, march the negated field, absorb by Beer, refract out or reflect on total internal reflection | C3 | Marble, Creation Stone (G-buffer split: solve the outer surface once, march the inside separately) | LM 10.2 | P1 |
| `float litThicknessSDF(vec3 p, vec3 dirIn, float reach, int taps)` **hook** | local thickness by marching inward; 0 paper-thin, 1 solid | C1 | Rhodium (thickness darkening; back-face translucency by a reverse march from beyond the object) | LM 9.3 | P1 |
| `vec3 litTranslucency(vec3 n, vec3 v, vec3 l, float thinness, vec4 params)` | back-lit translucency with the light vector distorted by the normal (Barré-Brisebois and Bouchard) | C0 | Rhodium | LM 9.2 | P1 |
| `vec3 litIorRGB(float iorD, float abbe)` / `vec3 litSpectrumToRgb(float lambdaNm)` | per-channel indices for three-channel dispersion; a smooth spectral weight that sums to white | C0 | Hex Glitch (one wavelength per sub-sample) | LM 10.3 | P1 |
| `vec3 litInteriorMap(vec3 roFace, vec3 rdFace, ...)` | a separate fake scene behind each face of a box: interior parallax for a few swizzles; darken face borders to hide portal seams | C1 | Cube Lines | study:NslGRN 6.2 | P2 |
| `vec3 litFakeGlassHaze(vec3 r, float t)` | two counter-animated noise layers keyed to the reflection direction with a -log contrast curve: reads as glass with gas inside, with no refraction at all | C1 | Plasma Globe | study:XsjXRm 6.9 | P2 |
| `float litCausticIsoline(float field, float width)` / `float litCausticAreaRatio(vec3 before, vec3 after)` | cheap caustic networks; physical caustic brightness from footprint area ratios | C0 | Marble (a fake caustic: no shadow through glass) | LM 10.4 | P2 |
| `float litIorCauchy(float lambdaNm, float iorD, float abbe)` | index at a wavelength from n_d and the Abbe number | C0 | — | LM 10.3 | P2 |

### F8. Thin film and iridescence (`light/thinfilm.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 litThinFilmPalette(float cosI, float thickness, vec3 phase)` | cosine-palette stylisation of iridescence; not physical and never washes out | C0 | Geodesic (depth-banded spectrum on groove walls: anodised titanium), Bubble Rings (rainbow by depth) | LM 11.3 | P1 |
| `vec3 litThinFilm(float cosI, float thicknessNm, float filmIor, float baseIor, int wavelengths)` | two-beam interference integrated over wavelengths to RGB; replaces F in the BRDF | C1 | — | LM 11.1-11.2; Belcour and Barla 2017 | P2 |

### F9. Glow and emission (`light/glow.glsl`)

The loved shaders' favourite trick (craft secret 2): light that comes from the march itself, not from lights.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 glowAccum(vec3 acc, vec3 colour, float d, float minD)` | adds colour/max(d, minD) per step: the 1/d halo with a floor against infinity | C0 per step | Blue Red Shiny (glow inside the distance function, picked up by every march), Audio Eclipse (1/d), Bubble Rings (surface-proximity spark) | LM 12.2 | **P0** |
| `float glowEmitStep(float density, float stepLen, float k)` | emission density × step length: brightness independent of step count (colour/d per step is the inverse-square special case) | C0 | Volumetric Sample | LM 12.2 | **P0** |
| `float glowExp(float minDist, float k)` | exp(-k·d) from the closest approach: stable, but cannot express depth | C0 | Just a Cube (glow from the minimum distance, with a hidden shell), Sincos 3D (running minimum) | LM 12.2 | **P0** |
| `float glowLorentz(float d, float k)` | k/(k+d²): a needle core with long tails; summed over many segments the tails become bloom with no blur pass | C0 | Oscillo Donut | CP 6.6 | **P0** |
| `float glowTwoGauss(float d, vec4 coreHalo)` | core Gaussian plus wide halo Gaussian, with widths and weights as parameters: the house's light-line profile, written seven times with different constants across the piano studies | C0 | — (house: Gyre, Wind, Moonwater, flight) | arc-piano-studies | **P0** |
| `vec3 glowHotCore(vec3 tint, float intensity)` | saturated tint at low intensity, whitening as intensity rises (neon and plasma read as bright, not just coloured) | C0 | Starship (tanh desaturates highlights by itself), Flame (overdrive), Oscillo Donut (phosphor overdrive), Rhodium | LM 12.3 | **P0** |
| `float glowStepCount(float steps, float maxSteps, float k)` | brightness from how long the ray loitered: walls, silhouettes and folds light themselves | C0 | Flame, Alien Core, Bubble Rings (the budget is the opacity) | study:MdX3zr 6.1 | **P0** |
| `float glowCompactWire(float d, float width, float k)` | (1 - abs(d)/width)^k on a compact support: a hair-thin glowing tube with a soft core and no tail | C0 | HAL 4000 (^28 lines) | study:MtXczn 6.3 | P1 |
| `float glowSoftCore(float d, float k)` | tanh(k/max(d,eps)): core capped at 1 with a long 1/d tail; additive glow that never explodes | C0 | — | CP 6.6 | P1 |
| `float glowPointInscatter(vec3 ro, vec3 rd, vec3 lightPos, float tmax)` | closed-form integral of 1/r² along a ray segment; halos cut off correctly behind a hit | C0 | — | LM 12.2 | P1 |
| `float glowComet(vec2 p, vec2 dir, float stretch)` | a one-sided anisotropic falloff (a max inside a length): a round glow becomes a comet with a tail | C0 | Starship | study:l3cfW4 6.1 | P1 |

### F10. Rigs (`light/rigs.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 rigStudio(LitSurface s, vec3 n, vec3 v, float ao, StudioParams sp)` | wrapped key + sky + back + rim + additive specular, with an emissive bypass; the product-shot rig every hero object can call | C0 | Glitch Transform (studio rig), Geodesic (studio with emissive bypass), Saturday | LM 6.4, 8.1 | **P0** |
| `vec3 rigOutdoor(LitSurface s, vec3 p, vec3 n, vec3 v, OutdoorRig r)` **hook** | Quilez's key (soft shadow, no AO) + sky (AO) + bounce (AO) + specular + multi-bounce AO | C2 | — | LM 6.4; Quilez, outdoor lighting | P1 |
| `vec3 rigComplementary(vec3 n, vec3 keyCol, vec3 fillCol, vec3 shadowCol)` | a complementary triad: cool fill, warm key and a hot colour in the shadow instead of black, so every surface carries colour | C0 | Cube Lines (red shadow glow), Humanimation (lit side takes the floor hue, shadow side the complement) | study:NslGRN 6.7 | P1 |

### F11. Materials (`light/material.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `struct LitMaterial`, `struct LitSurface`, `LitSurface litResolveMaterial(LitMaterial m, float alphaMin)` | the metallic workflow: diffuse=(1-metallic)·base, F0 from reflectance or base, alpha = clamp(roughness², alphaMin, 1) | C0 | — | LM 4.6 | P1 |
| `vec3 litShadeLight(LitSurface s, vec3 n, vec3 v, vec3 l, vec3 radiance)` | diffuse plus GGX for one light, NoL applied | C0 | — | LM 4.5 | P1 |
| `float litFurnace(LitSurface s, vec3 n, vec3 v)` | shading under a uniform white environment; must be 1 for albedo and F0 of 1 (dark rims are energy loss, bright rims double counting) | C0 | — | LM 16 | P1 |
| `float matSilkscreen(vec2 uvFace, ...)` | ticks, scales and logos as a mask in the material channel, not geometry: razor-sharp at no cost | C0 | Inercia | study:cs2GWD 6.3 | P2 |
| `vec3 matMultiplyReflection(vec3 base, vec3 reflected)` | base × reflected glow (not +): darker, more contrasted, reads as polished metal | C0 | Blue Red Shiny | study:7cjGRR 6.4 | P2 |

---

## 9. Family G: Volumes and sky

Light passing through stuff: fog, cloud, smoke, aurora, sky. VA is the textbook. One law sits under all of it,
Beer-Lambert: the fraction of light that survives a distance d through a medium of extinction σ is exp(-σ·d).

### G1. Integration (`volume/integrate.glsl`)

The house light bed integrates its fog in the naive order, which makes a dense slice about 35% too bright and makes the
look depend on the step size (VA 12, house note 1). These parts are the energy-conserving form, which costs nothing
extra.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float volTransmittance(float sigmaT, float dist)` / `vec3 volTransmittance3(vec3 sigmaT, float dist)` | Beer-Lambert exp(-σ·d), scalar or per channel | C0 | Volumetric Sample, Marble, Dark Cloud, Rhodium | VA 1.2 | **P0** |
| `float volOpacityFactor(float x)` | (1 - exp(-x))/x, numerically stable as x → 0: the kernel of every exact segment integral | C0 | — | VA 1.4 | **P0** |
| `struct VolAccum { vec3 L; vec3 T; }` + `VolAccum volAccumInit()` | front-to-back accumulator starting at L=0, T=1 | C0 | Cloud Ten, Marble, Dry Ice (front-to-back compositing) | VA 1.3 | **P0** |
| `void volStepScatter(inout VolAccum a, vec3 sigmaS, vec3 sigmaT, vec3 Lin, float dt)` | adds T·σs·Lin·dt·F(σt·dt) and multiplies T by exp(-σt·dt): brightness independent of the step size, so a quality tier changes cost, not exposure | C0 per step | Volumetric Sample (the single most important line in that shader) | VA 1.4; Hillaire 2015 | **P0** |
| `void volStepEmit(inout VolAccum a, vec3 emission, vec3 sigmaT, float dt)` | exact emission-plus-absorption segment; with σt = 0 it is T·emission·dt (aurora, nebula gas, fire) | C0 per step | AURORA (optically thin, additive only) | VA 1.4 | **P0** |
| `bool volSaturated(VolAccum a, float eps)` | true when max transmittance < eps: the early exit | C0 | Volumetric Sample (early exit everywhere) | VA 3.4 | **P0** |
| `vec3 volResolve(VolAccum a, vec3 background)` | L + T·background: scattered light is emission, the background is attenuated | C0 | Dark Cloud (the participating-media composite rule) | VA 1.3 | **P0** |
| `float volBeerShadowMap(float d, vec3 bsm)` | Hillaire's Beer shadow map lookup | C0 | — | VA 3.3 | P2 |

### G2. Phase functions (`volume/phase.glsl`)

Where scattered light turns. House convention: mu = dot(viewRayDir, dirToLight), so positive g glows around the light.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float phaseIso()` | 1/(4π) | C0 | — | VA 1.5 | **P0** |
| `float phaseHG(float mu, float g)` | normalised Henyey-Greenstein with mean cosine g | C0 | — | VA 1.5 | **P0** |
| `float phaseRayleigh(float mu)` | 3/(16π)·(1+mu²): molecular scattering, the blue sky | C0 | — | VA 1.5 | P1 |
| `float phaseSchlick(float mu, float g)` | cheap HG stand-in | C0 | — | VA 1.5 | P1 |
| `float phaseCornetteShanks(float mu, float g)` | the Mie-like aerosol lobe of the sky model | C0 | — | VA 1.5 | P1 |
| `float phaseDualHG(float mu, float gFwd, float gBack, float w)` | two lobes; keeps cloud detail when the sun is behind the camera | C0 | — | VA 1.5 | P1 |
| `float phaseSilverLining(float mu, float g, float intensity, float spread)` | Schneider-style art control for silver linings; not energy conserving | C0 | Cloud Ten (a painted silver lining keyed to thin, high density) | VA 1.5; Schneider 2015 | P1 |
| `float phaseDraine(...)`, `float phaseCloudMie(float mu, float diameterUm)` | Draine and the fitted droplet phase | C0 | — | VA 1.5 | P2 |
| `float litLommelSeeliger(float NoL, float NoV)` | single scattering for dusty, matte media | C0 | Dark Cloud | study:4slGWM | P2 |

### G3. Cloud lighting approximations (`volume/cloud-light.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float scatterTwoBeer(float tau, float k2, float w2)` | max(exp(-τ), w2·exp(-k2·τ)): cheap multiple-scatter brightening | C0 | — | VA 1.6; Schneider | P1 |
| `vec3 scatterOctaves(float tauLight, float mu, float g, vec3 sigmaS, float a, float b, float c, int N)` | Wrenninge's octave sum (requires a ≤ b) | C1 (≤ 3) | — | VA 1.6; Wrenninge 2013 | P1 |
| `float cloudPowder(float tau, float k)` / `float cloudBeerPowder(float tau)` / `float cloudPowderView(float powder, float mu)` | the powder effect (dark sun-facing edges), always faded toward the light through cloudPowderView | C0 | — | VA 1.7 | P1 |
| `float cloudEdgeAlbedo(float density, float lo, float hi, float minAlbedo)` | lower albedo where density is low: the physically based alternative to powder | C0 | Cloud Ten (albedo lerps to black with density, giving the dark belly for free) | VA 1.7 | P1 |

### G4. Density shaping (`volume/density.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float densFromSDF(float sdf, float softness)` | clamp(-sdf/softness, 0, 1): every distance-field modelling tool becomes a fog-modelling tool | C0 | Volumetric Sample (fog density from SDF depth) | VA 2.2 | **P0** |
| `float cloudHeightProfile(float h01, vec4 ramps)` | rise over [x,y], fall over [z,w]; zero at both ends so slab edges never show | C0 | — | VA 2.2 | P1 |
| `float cloudSlopedDeck(vec3 p, float slope, float noise)` | slope·y plus noise: an infinite cloud deck with a soft top whose density keeps growing with depth | C0 | Cloud Ten (the cloud is a floor, not objects) | study:XtS3DD 6.1 | P1 |
| `float cloudCoverage(float base, float coverage)` / `float cloudErode(float base, float detail, float strength)` / `float cloudProfileErode(float profile, float noise)` | coverage threshold; erode edges by detail only, preserving cores | C0 | — | VA 2.2; Schneider 2015, 2017 | P1 |
| `vec3 cloudWindOffset(vec3 p, vec3 wind, float t, float h01, float skew)` | advect the sample with wind and skew it with height | C0 | Volumetric Sample (shape noise drifts, density noise fixed in the world) | VA 2.2 | P1 |
| `float cloudTypeProfile(float h01, float type)` / `float cloudAnvil(...)` / `float noiseFold2(float n01, float k)` | stratus-to-cumulus profiles; anvil tops; folded noise for near-camera detail | C0 | — | VA 2.2 | P2 |

### G5. Volume marching (`volume/march.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float marchStepPoly(int i, float base, float scale, float power)` | layer i at base + scale·i^power: dense at the bright lower edge, sparse in the faint top (aurora sheets) | C0 | Chromatic Curtains (polynomial sheet spacing, nimitz lineage) | VA 7.2 family B | **P0** |
| `float volLightOneTap(vec3 p, vec3 toLight, float dist, float floorShadow)` **hook** | one density probe toward the light with a floor (shadows that never go black) | C0 + 1 hook | Cloud Ten (15% floor) | study:XtS3DD 6.6 | **P0** |
| `float volLightMarch(vec3 p, vec3 toLight, int n, float spacing, float farDist)` **hook** | n cone samples toward the light with growing spacing plus one far sample: the light's optical depth | C1 per sample (so C3 overall) | Dry Ice (secondary march toward the light), Volumetric Sample (per-sample shadow rays) | VA 3.3 | P1 |
| `float marchStepDistance(float t, float dtMin, float k)` / `float marchStepOptical(float sigmaT, float tauTarget, float dtMin, float dtMax)` | steps that grow with distance; steps that limit each step's optical depth | C0 | Cloud Ten (distance- and density-adaptive step) | VA 3.2 | P1 |
| `float lightDirDerivative(float densHere, float densTowardLight, float scale)` | one-sample lighting proxy: non-physical, very cheap | C0 | Marble (emboss), Cloud Ten (painted shading) | VA 3.3 | P1 |
| `float volHeightfieldDensity(vec3 p, sampler2D height, float slabTop)` | a 2D height map read as fog depth: a 2D simulation wearing a 3D costume | C0 +T1 | Dry Ice | study:WlVyRV 6.1 | P2 |
| `vec4 volSliceAligned(...)` **hook** | steps aligned to slices with fractional occupancy, for 2.5D media | C2 | Dry Ice | study:WlVyRV | P2 |

### G6. Sky and stars (`atmos/sky.glsl`, `atmos/stars.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 skyGradient(vec3 rd, vec3 toSun, vec3 zenith, vec3 horizon, vec3 sunTint)` | a sun-aware sky gradient with a warm horizon toward the sun | C0 | AURORA (pre-dawn gradient), Cloud Ten (sun-aware sky) | VA 4.1 | P1 |
| `vec3 skySunDisk(vec3 rd, vec3 toSun, float angRadius, vec3 luminance)` | sun disk with smooth limb darkening | C0 | — | VA 4.5 | P1 |
| `vec3 starsDirCells(vec3 rd, float density, float twinkle, float t)` | stars hashed per direction cell, each with an exponent that breathes (twinkle) and a sparse-selector power so only a sliver of cells light | C0 | AURORA, Aurora Lights (grid-cell stars), AuroraBorealis (power-threshold twinkle), Chromatic Curtains (sparse jittered antialiased stars), HAL 4000 (warp stars from parallax layers) | VA 4.5; craft secret 3 | P1 |
| `float skyMountainSilhouette(vec3 rd, float t, uint seed)` | an azimuth silhouette from 1D noise with a seam taper where the angle wraps | C1 | AURORA | study:ttScDc 5.15 | P2 |
| the atmosphere LUT family: `Atmos atmosEarth()`, `atmosMedium`, `atmosTransmittance`, `atmosSingleScatter`, `atmosMultiScatterPsi`, `atmosApply`, `vec2 atmosSkyViewUV` | Hillaire's production sky: transmittance LUT, multiple-scattering closed form, sky-view LUT, aerial perspective | C4 | — | VA 4.2-4.6; Hillaire 2020 | P2 |

### G7. Fog and light shafts (`atmos/fog.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 fogExp(vec3 col, vec3 fogCol, float dist, float k)` | mix(col, fogCol, 1-exp(-k·dist)): the classic distance fog | C0 | Rhodium (depth fade), Starry Planes (fade to black far, vanish near), Cube Lines (floor-to-sky fade) | VA 5.1 | **P0** |
| `vec3 fogAdditiveTint(vec3 col, vec3 tint, float dist, float k)` | add a distance tint instead of mixing: depth without darkening anything | C0 | Alien Core (additive violet), Blue Red Shiny (far red, near blue-white pulls the eye forward) | study:4tcXRr 6.7 | P1 |
| `float fogHeightTau(vec3 o, vec3 d, float t, float a, float b)` | analytic optical depth of a·exp(-b·y) along a ray, stable when the ray is level | C0 | — | VA 5.1; Quilez, better fog | P1 |
| `vec3 fogSplit(vec3 col, vec3 inCol, vec3 bExt, vec3 bIn, float dist)` / `vec3 fogSunTint(vec3 rd, vec3 toSun, vec3 away, vec3 toward, float sharp)` | separate extinction and in-scatter colours; fog warming toward the sun | C0 | Cloud Ten (clouds wear the sky's colour) | VA 5.1 | P1 |
| `vec3 raysRadial(sampler2D occ, vec2 uv, vec2 sunUV, int n, ...)` | Mitchell's screen-space god rays with a jittered first sample (fails off-screen) | C1 +Tn | Humanimation (jittered radial zoom blur) | VA 5.3; Mitchell 2007 | P2 |
| `float raysPatternShell(vec3 rd, ...)` | any direction-only pattern extruded through a shell is a set of light shafts from the centre | C1 | RM Experiment 23 | study:4lj3Ww 6.3 | P2 |
| `float fogMipLevel(vec2 uv, float fog)` | fog as "which mip rung to read" instead of a blur pass | C0 +T1 | Heartfelt (blur is free) | study:ltffzl 6.1 | P2 |

### G8. Aurora (`atmos/aurora.glsl`)

The house's signature subject (the project is named after it). VA section 7 gives the physics and three families of fake:
A, 2D stretched noise in height bands (cheap, painted on the sky); B, a stack of horizontal sheets sampling one 2D
footprint (curtains with parallax, correct from below); C, a true emissive volume (flyable).

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float auroraProfile(float altKm, float lowerEdgeKm, float scaleHKm)` | emission against altitude: a sharp rise at the lower edge (about 90-100 km), exponential decay above | C0 | AURORA (the hem is the box floor; the top fades) | VA 7.1, 7.3 | **P0** |
| `vec3 auroraLineColor(float altKm, float energetic)` | linear RGB emission by altitude: a purple N2+ fringe low (scaled by energetic), the 557.7 nm green body, 630 nm red high | C0 | Aurora Lights (bands in physical order), Chromatic Curtains (hue-only height masks) | VA 7.1 | **P0** |
| `float auroraRays(float along, float t, uint seed)` | field-aligned striation: 1D noise along the curtain, scrolling, stretched vertically | C0 | Chromatic Curtains (screen-space ray striation), Aurora Lights (anisotropic stretch: two layers, folds plus long rays) | VA 7.3 | **P0** |
| `vec3 displayHueSafeGamma(vec3 c, float gamma)` | gamma on colour magnitude only, c·length(c)^(1/γ-1): the hue of thousands of summed dim emitters survives | C0 | — | VA 7.2 family C; Lawlor and Genetti 2011 | **P0** |
| `float auroraFootprint(vec2 xzKm, float t, float foldAmt)` | 2D curtain intensity: a Gaussian around drifting, folded centre lines about 1 km wide | C1 | — | VA 7.3 | P1 |
| `vec3 auroraVolume(vec3 o, vec3 rd, float tNear, float tFar, float jitter)` **hook** | emission-only march of footprint × profile × line colour (family C) | C2 | AURORA | VA 7.2 family C | P1 |
| `float auroraRedLag(vec2 xzKm, float t, float lagSec)` | a time-lagged, blurred footprint for the slow 630 nm afterglow | C1 | — | VA 7.3 | P2 |

### G9. Nebulae (`atmos/nebula.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 nebulaLines(float hAlpha, float oIII, float sII, int palette)` / `vec3 nebulaStarGlow(vec3 p, vec3 starPos, vec3 col, float k)` / `void nebulaStep(inout VolAccum a, vec3 p, float gas, float dust, vec3 lineCol, float dt)` | emission-line colour (natural or Hubble false colour); star glow added inside the integral; gas emits, dust extinguishes | C0 per step | — | VA 8 | P2 |

---

## 10. Family H: Colour and finish

Turning light into a picture. CP's first lesson binds the whole family: there are two currencies, scene-linear light and
display-encoded code values; do the maths on light and encode once, at the very end. About three in four corpus shaders
never encode explicitly; their looks are great, but their numbers do not compose. The house library is stricter than
the shaders it learns from, because "tweak one module and everything updates" only works if every module speaks the
same currency.

### H1. Transfer functions (`colour/transfer.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 srgbEncode(vec3 lin)` | exact IEC 61966-2-1 piecewise encode; the last colour step before dither | C0 | Apollonian (exact sRGB encode) | CP 1.3 | **P0** |
| `vec3 srgbDecode(vec3 enc)` | exact inverse; apply to textures, video and hand-picked colours before any lighting or blending | C0 | — | CP 1.3 | **P0** |
| `float luminance(vec3 lin)` | Rec.709 weights (0.2126, 0.7152, 0.0722) on linear values; never Rec.601 weights | C0 | — | CP 1.4 | **P0** |
| `vec3 cbrtSigned(vec3 x)` | sign-preserving cube root; keeps OKLab finite for out-of-gamut input | C0 | — | CP 2.2 | **P0** |
| `vec3 gammaEncode(vec3 lin, float g)` / `vec3 gammaDecode(vec3 enc, float g)` | pure power, only where a pure-2.2 or square-root look is chosen deliberately | C0 | AURORA, Glitch Transform, Geodesic, Starry Planes and Saturday (sqrt), Dry Ice (sqrt) | CP 1.3 | P1 |
| `vec3 log2Shaper(vec3 lin, float c)` / `vec3 pqEncode(vec3 n)` | unbounded HDR to 0..1 for LUT lookup; SMPTE ST 2084 | C0 | — | CP 5.8 | P2 |

### H2. Perceptual colour (`colour/oklab.glsl`)

HSV is a re-labelling of RGB: pure blue and pure yellow have the same HSV value, yet yellow is about 13 times
brighter. For "same brightness, different colour", use OKLab and its polar form OKLCH (Ottosson 2020).

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 oklabFromLinear(vec3 lin)` / `vec3 linearFromOklab(vec3 lab)` | linear sRGB to OKLab and back; white maps to L=1, a=b=0; the result of the inverse may leave 0..1 | C0 | — (none of the corpus uses OKLab) | CP 2.2; Ottosson 2020 | **P0** |
| `vec3 oklchFromOklab(vec3 lab)` / `vec3 oklabFromOklch(vec3 lch)` | polar form with hue in turns (0..1), matching the palette convention | C0 | — | CP 2.2 | **P0** |
| `vec3 mixOklab(vec3 a, vec3 b, float t)` / `vec3 mixOklch(vec3 a, vec3 b, float t)` | perceptual blends of linear colours, returned linear; OKLCH takes the shortest hue arc and gamut-clips: the honest replacement for "HSV the short way round" | C0 | — | CP 2.4 | **P0** |
| `float hueDelta(float h0, float h1)` | signed shortest hue difference in turns, in [-0.5, 0.5) | C0 | — | CP 2.4 | **P0** |
| `bool inGamut(vec3 lin, float eps)` / `vec3 oklchClip(vec3 lch)` | gamut test; reduce chroma at fixed lightness and hue by bisection (6 to 8 steps) until in gamut, never shifting hue the way a per-channel clamp does. The GLSL twin of the piano's maxChroma bisection (piano.js:321-412) | C1 (≤ 8) | — | CP 2.3 | **P0** |
| `vec3 hueRotateOklch(vec3 lin, float turns)` | rotate hue at constant lightness and chroma, then gamut-clip | C1 | — | CP 2.4 | **P0** |
| `vec3 gradeSaturationOklab(vec3 lin, float s)` | scale OKLab a and b by s; lightness and hue untouched | C1 | — | CP 9.4 | P1 |

### H3. Legacy colour knobs (`legacy/hsv.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 hsvToRgb(vec3 hsv)` / `vec3 rgbToHsv(vec3 rgb)` **(legacy twin)** | branch-free HSV, exactly as the house pastes it in 10 files (First Light, Play and seven presets). Display knobs, not perception: V is not brightness | C0 | Audio Eclipse (branch-free HSV wheel), Chromatic Curtains (HSV hue rotation) | CP 2.1 | **P0** |
| `vec3 hsvToRgbSmooth(vec3 hsv)` | cubic-smoothed hue ramps, so there are no Mach bands at the sextant seams | C0 | — | CP 2.1 | P1 |

### H4. Palettes (`colour/palette.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 palCos(float t, vec3 a, vec3 b, vec3 c, vec3 d)` | Quilez's cosine palette a + b·cos(2π(c·t + d)); returns display values as tuned on screen; whole-number c loops seamlessly | C0 | Bubble Rings (rainbow by depth), Geodesic (spectrum), Hexagone (hashed sine palette), Satisfying (sine palette), Apollonian (travelling hue), Cube Lines (an eight-partial variant) | CP 3.1; Quilez, palettes | **P0** |
| `vec3 palCosLinear(float t, vec3 a, vec3 b, vec3 c, vec3 d)` | the same palette decoded to linear for lit pipelines | C0 | — | CP 3.1 | **P0** |
| `vec3 palOklch(float t, float L, float C, float h0, float turns)` | constant-lightness, constant-chroma hue sweep: the even rainbow HSV cannot give | C1 | — | CP 3.2 | **P0** |
| `vec3 palRamp3(float t, vec3 linA, vec3 linB, vec3 linC)` | three-stop gradient interpolated in OKLab; the shape of an analogous house palette | C0 | Chromatic Curtains (a three-colour paint stage with hue-only masks: cyan, electric blue, indigo, already analogous), AURORA (height colour ramp) | CP 3.2 | **P0** |
| `vec3 palHeatPowers(float x, vec3 exponents)` | one intensity to a hue-shifting colour by per-channel powers (channels saturate in sequence: dim is deep, hot is white): the cheapest convincing neon and ember there is | C0 | HAL 4000 (per-channel powers), Rhodium (1, 1/4, 1/16 ratios), Flame and Just a Cube (channels clip in order), Starship | craft secret 7 | **P0** |
| `vec3 palPitchFifths(float pitchClass, float octave, PitchPalette pp)` | the house note colour: hue walks the circle of fifths, each hue at the lightness that allows its maximum sRGB chroma, every hue pulled to one shared luminance. The GLSL twin of the piano's OKLCH palette; nine copies with different starting angles exist today, so C is a different colour on different surfaces | C1 (gamut clip) | — | arc-piano-core (3); arc-arcs | **P0** |
| `vec3 palBlackbody(float kelvin)` | Planckian colour, about 1000 to 40000 K, as linear RGB with max channel 1 | C0 | RM Experiment 23 (blackbody as the palette: colour-coherent by construction) | CP 3.2 | P1 |
| `vec3 palChannelPermute(vec3 c, float phase)` | palette morph by rotating or permuting channels | C0 | Cloud Ten (a different planet by channel permutation), Sincos 3D (channel rotate and square) | study:XtS3DD | P2 |
| `vec3 palHueMagnet(vec3 c, float targetHue, float strength)` | a sinusoidal hue remap that pulls everything toward one hue family | C1 | Hex Glitch | study:lfscD7 4.24 | P2 |

### H5. Exposure and tone mapping (`colour/tone.glsl`)

A tone mapper (more accurately a display transform) is the soft limiter that squeezes unbounded light into the screen's
0..1. CP 5.10 chooses per content: tanh or 1-exp(-x) for ambient glow fields; AgX or Khronos PBR Neutral for lit 3D;
the Hill ACES fit only for a deliberate cinematic punch. Whatever the choice, every surface calls **one** function
(`displayOut`, H9).

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 expose(vec3 lin, float ev)` | lin·2^ev: the only brightness knob before the display transform | C0 | Dark Cloud (HDR sun at 10 times), Blue Red Shiny (huge HDR then rescale) | CP 4.1 | **P0** |
| `vec3 tmTanh(vec3 x)` | tanh per channel: slope 1, no toe, about 1.4 stops of headroom; for glow fields tuned near 1 | C0 | Starship (square then tanh), Oscillo Donut (tanh as stability, shoulder and overdrive), Blue Red Shiny; house: cockpit bed and First Light | CP 5.2 | **P0** |
| `vec3 tmExp(vec3 x)` | 1 - exp(-x): film-density saturation | C0 | Chromatic Curtains (exponential tone map) | CP 5.2 | **P0** |
| `vec3 tmReinhard(vec3 x)` | x/(1+x) | C0 | — | CP 5.2 | **P0** |
| `vec3 tmAcesFit(vec3 x)` | Narkowicz 2016 rational fit (CC0), with the 0.6 pre-scale inside; per-channel hue skews | C0 | AURORA, Starry Planes, Saturday; house: five copies | CP 5.4; Narkowicz 2016 | **P0** |
| `vec3 tmPbrNeutral(vec3 x)` | Khronos PBR Neutral: identity below about 0.76, peak-only compression, no hue change. Matches the three.js Neutral tone mapping the piano uses, so GLSL and three.js surfaces can agree | C0 | — | CP 5.7 | **P0** |
| `vec3 tmRootGain(vec3 x, float gain)` | gain·sqrt(x): makes faint accumulated glow legible without a filmic curve | C0 | Bubble Rings (a stacked curve that collapses to a root gain), Just a Cube (sqrt with glow added last) | study:WdB3Dw 6.10 | **P0** |
| `vec3 tmSuperlinear(vec3 x, float k)` **(legacy twin)** | the house's superlinear highlight that runs before tanh (shader-craft ceiling: "superlinear highlight, then the tanh shoulder") | C0 | — | house chunk `superlinear-highlight` | **P0** |
| `vec3 tmAgx(vec3 x)` / `vec3 tmAgxLook(vec3 x, vec3 slope, vec3 power, float sat)` | AgX base and its look: graceful path to white, no hue skews | C0 | — | CP 5.6; Sobotka | P1 |
| `vec3 tmAcesHill(vec3 x)` | Hill's fit with input and output matrices: the recognisable cinematic look | C0 | — | CP 5.4 | P1 |
| `vec3 tmReinhardWhite(vec3 x, float white)` / `vec3 tmReinhardLum(vec3 x, float white)` | extended Reinhard; luminance-only Reinhard (exact hue) | C0 | — | CP 5.2 | P1 |
| `vec3 glowToneBloom(vec3 x, vec3 exps, vec3 weights)` | a sum of three power curves: a halo for a soft field with no extra pass | C0 | Chromatic Curtains (bufferless bloom) | study:ffG3Rc 6.6 | P1 |
| `vec3 tmHable(vec3 x, float white)`, `tmUchimura(...)`, `vec2 tmLottesSolve(...)` + `tmLottes(...)`, `tmMaxRgb(...)`, `tmHejlEnc(...)` | the filmic family with interpretable parameters; Hejl returns encoded values (never encode again) | C0 | — | CP 5.3 | P2 |

### H6. Grading (`colour/grade.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 grdSaturation(vec3 lin, float s)` | Y + s·(x - Y) with Rec.709 luminance; s=0 is true grey | C0 | — | CP 9.4 | **P0** |
| `vec3 grdAwayFrom(vec3 c, vec3 pivot, float k)` | mix past 1 away from a pivot (grey, or a second colour): saturation and overbright by extrapolation | C0 | Marble (saturation by extrapolating from grey), Flame (extrapolating mix), Data Warehouse (overbright birth), Pretty Hip (mix overshoot as a gradient) | craft secret 8 | **P0** |
| `vec3 grdSCurveDisp(vec3 disp, float amount)` | a smoothstep S-curve on display values mixed by amount (the classic finish); after encode, before dither | C0 | Marble (post stack), Cloud Ten, Humanimation, Alien Core | CP 9.5 | **P0** |
| `vec3 grdContrastLog(vec3 lin, float contrast, float pivot)` | pivot·(x/pivot)^contrast: contrast in log space, pivot fixed | C0 | — | CP 9.3 | P1 |
| `vec3 grdCdl(vec3 x, vec3 slope, vec3 offset, vec3 power, float sat)` | ASC CDL | C0 | — | CP 9.4 | P1 |
| `vec3 grdSplitTone(vec3 lin, vec3 shadowTint, vec3 highlightTint, float balance)` | luminance-weighted tints carrying no brightness | C0 | Inercia (split-tone S-curve) | CP 9.4 | P1 |
| `vec3 grdLiftedFinish(vec3 disp, float blackLift, float whiteCap)` | lifted blacks and capped whites: a 1-bit pattern reads as printed or projected material | C0 | Hex Glitch (0.1 and 0.9) | study:lfscD7 6.11 | P1 |
| `vec3 grdOverlay(vec3 disp, vec3 tint, float amount)` | overlay grade toward a tint | C0 | Hex Glitch (dusty teal) | study:lfscD7 4.23 | P2 |
| `vec3 grdLiftGammaGain(...)`, `vec3 grdWhiteBalance(...)`, `vec3 grdLut3d(sampler3D ...)`, `vec3 grdLutStrip(...)` | display-referred three-way; von Kries white balance; 3D LUT with the half-texel correction; WebGL1 strip fallback | C0 +T1 | — | CP 9.2, 9.4, 9.6 | P2 |

### H7. Lens and bloom (`post/lens.glsl`, `post/bloom.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float vigCorner(vec2 uv01, float aspect, float amount)` | aspect-correct radial falloff normalised by the real corner distance (the house cubic): flat centre, falls only near the corners | C0 | Hexagone (aspect vignette); house chunk `vignette-cubic` | CP 7.3 | **P0** |
| `float vigFrame(vec2 uv01, float power)` | separable (16xy(1-x)(1-y))^power: rectangular contours | C0 | Warping (edge-product vignette), Dry Ice (Quilez vignette) | CP 7.3 | P1 |
| `float vigCos4(vec2 p, float fovY)` | natural vignetting, physically sized | C0 | — | CP 7.3 | P1 |
| `vec2 lensDistort(vec2 p, float k1, float k2)` | Brown radial model on the sampling coordinate | C0 | — | CP 7.2 | P1 |
| `vec3 caRgb3(sampler2D src, vec2 uv, vec2 centre, float k)` / `vec3 caSpectral(...)` | lateral chromatic aberration, three taps or N spectral taps whose weights keep white white | C0 +T3..n | Hex Glitch (a radial zoom jitter standing in for CA) | CP 7.1 | P1 |
| `float karisWeight(vec3 lin)` / `vec3 bloomComposite(vec3 scene, vec3 bloom, float strength)` | firefly-suppression weight; energy-conserving bloom mix (about 0.04) | C0 | — | CP 6.2, 6.5 | P1 |
| `vec3 bloomDown13`, `bloomDown13Karis`, `bloomUpTent`, `blurDualDown`, `blurDualUp`, `blurKawase`, `streakKawase`, `bloomPrefilterKnee` | the pass-based bloom family (Jimenez's mip chain, Bjørge's dual filter, Kawase) | C4 +Tn | Hex Glitch (separable downsampled bloom with per-channel kernel shapes), Rhodium (HDR into a float buffer, then blur), Humanimation (screen-blend ring bloom, cross glow) | CP 6.3-6.5 | P2 |
| `vec3 lensFlareBlades(vec2 p, vec2 sunUV, int blades, ...)` | starburst and ghosts on the line through the screen centre, implying an iris | C1 | Cloud Ten (five-blade flare from a pentagonal gauge norm) | CP 6.7 | P2 |
| `vec4 bokehVogel(sampler2D src, vec2 uv, float coc, int taps)` | a depth-of-field gather on the golden-angle (sunflower) spiral; circle of confusion read from alpha | C4 +Tn | Rhodium | study:llK3Dy 6.3, 6.10 | P2 |

### H8. Dither and grain (`post/dither.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 ditherOut(vec3 enc, vec2 pixel, float levels)` | ±1 code value of triangular dither in the **encoded** space right before quantisation, from a static mask; eases to half a step near 0 and 1 so blacks do not lift. Replaces the house chunk `triangular-dither`, which is seeded by u_time and so crawls (it violates floor 8 and sits in the "filmic finish" group) | C0 | Chromatic Curtains (static dither), Marble (dither in its post stack), Oscillo Donut (static grain beats shimmering grain) | CP 8.2; NP 13.3 | **P0** |
| `vec3 ditherOutBlue(sampler2D blue, vec3 enc, vec2 pixel, float levels)` | the same contract with a CC0 blue-noise tile: the least visible still dither | C0 +T1 | — | CP 8.2 | P1 |
| `vec3 grainEnergy(vec3 lin, float g, float steps)` / `vec3 grainFilm(vec3 disp, vec2 pixel, float size, float amount)` | Lottes energy-preserving grain; midtone-weighted coherent grain, static unless a piece opts into animation | C0 | — | CP 8.4, 8.5 | P2 |

### H9. The display seam (`post/display-out.glsl`, a recipe)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 displayOut(vec3 sceneLin, vec2 pixel, float ev, int curve, float saturation, float vignette, float sCurve, float ditherLevels)` | the single house tail: exposure, display transform (`curve` selects tanh, exp, ACES fit, PBR Neutral, AgX when built), saturation, vignette, sRGB encode, S-curve look, static dither. Every surface ends with it, so one edit restyles everything; its params become the "Finish" panel on every page | C0 | the finishing stacks of Hex Glitch, Marble, Cloud Ten, Starry Planes, Inercia | CP 14.12 (`display_out`) | **P0** |

---

## 11. Family I: Motion and choreography

Most of the "cinematic" feel in the loved shaders is choreography, not rendering (craft secret 16). These parts make
time a first-class material: envelopes, flicker, paths and sequences, all pure functions of the one clock.

### I1. Envelopes and timelines (`motion/envelope.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float envRamp(float t, float start, float dur)` | clamp((t-start)/dur, 0, 1): keyframes written as maths | C0 | HAL 4000 (the whole film is a stack of these), Heartfelt | study:MtXczn 6.8 | **P0** |
| `float envWindow(float t, float a, float b, float soft)` | smoothstep in at a, out at b | C0 | Heartfelt (the story is smoothstep windows on one clock), Oscillo Donut (bell windows) | study:ltffzl 6.9 | **P0** |
| `float envCubicEase(float x)` / `float envSineEase(float x)` | cubic and sine in-out eases | C0 | HAL 4000 (cubic ease where it should feel inevitable), Geodesic (sine-eased parameter sequencer) | PF 2 | **P0** |
| `float envFlashSafe(float sinceLastFlash)` | 0 within 1/3 s of the previous full-field flash, ramping to 1: keeps large flashes at or below three per second (photosensitivity safety) | C0 | — | GP 12 | **P0** |
| `float envStrikeSag(float sinceOn, float sinceOff, float velocity, float held, float pedal, LightParams lp)` | the house LIGHT model in GLSL: velocity factor × a strike-then-sag envelope × finger and pedal state, with a floor; a new strike adds energy and never restarts the old (R2, R3, R10). Its JS twin is the piano's LIGHT (piano.js:701-719), which today reaches GLSL as generated #defines | C0 | — | arc-piano-core (1) | P1 |
| `float envAnticipate(float t, float windup, float hold, float spring)` | a Gaussian-eased wind-back, a hold, then a spring with a slow settle: rotation that feels physical | C0 | Hex Glitch ("KickDrop") | study:lfscD7 4.8 | P1 |
| `float envBreath(float x, float t, vec2 rates)` | a two-timescale brightness envelope travelling along x | C0 | Aurora Lights (fast fringe, slow body), AuroraBorealis (phase-coupled breathing) | study:MsjfRG 6.7 | P1 |
| `float envQuarterSine(float t, float start, float dur)` | quarter-sine segments staggered so each beat overlaps the next and reads as one mechanism | C0 | Data Warehouse | study:NlK3Wt 6.7 | P1 |
| `float envTwoStroke(float t, float period)` | fill outward then clear outward, with the polarity flip hidden at the fully lit state: one-way flow with no visible cut | C0 | Pretty Hip | study:XsBfRW 6.1-6.2 | P1 |
| `float envPowerOnSurge(float t, float dur)` | drive a variable past its normal range for a few seconds so the glow overshoots and settles, like old electronics | C0 | HAL 4000 | study:MtXczn 6.12 | P2 |

### I2. Flicker and organic clocks (`motion/flicker.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float flkIncommensurate(float t, vec4 freqs)` | fract of a sum of sinusoids with near-but-unequal frequencies: nervous, alive, perfectly repeatable | C0 | HAL 4000 | study:MtXczn 6.11 | P1 |
| `float flkExpPositional(float t, float pos, float rate)` | exponential flicker phased by position: reads as flashing (linear reads as wobbling), and prints flicker history along a tail | C0 | Starship | study:l3cfW4 6.4-6.5 | P1 |
| `float flkSignedLightning(float t, float rate)` | a frequency-modulated strobe times a sharpened periodic envelope, signed, so a storm darkens as well as flashes | C0 | Heartfelt | study:ltffzl 6.10 | P2 |
| `float flkStepHue(float t, float period)` | a stepped (not cycling) complementary hue clock: disco lights on the beat | C0 | Humanimation | study:ltdcW7 6.10 | P2 |
| `float flkStrobeBand(float x, float t, float period)` | a disco-floor strobe band | C0 | Hexagone | study:wsl3WB | P2 |

### I3. Waves and oscillators (`motion/wave.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float wavStackedTri(float x, float t, vec3 speeds)` | stacked travelling triangle waves: kinked corners give an electric snap that sines cannot | C0 | Plasma Globe | study:XsjXRm 6.2 | P1 |
| `float wavPinnedString(float x, float t, float freq, float amp)` | a travelling wave windowed to zero at both ends: a string or laser held at two points | C0 | Discoteq | study:DtXfDr 6.2 | P1 |
| `vec2 wavTwoCosineWander(float t, vec4 freqs, vec2 amp)` | a wandering 2D path from two cosines per axis | C0 | Dry Ice (emitter path) | study:WlVyRV | P1 |

### I4. Paths (`motion/path.glsl`)

`pathLissajous3` and `camBanked` live in E2. Here are the remaining motion paths.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 pathEpicycles(float t, vec3 radii, vec3 rates)` | chained rotating frames: three circles each in the frame of the previous one give a torus knot plus coil; scales to any number of nested voices | C0 | Oscillo Donut | study:ldSfWV 6.7 | P2 |
| `vec3 pathRider(vec3 basePos, mat3 frame, vec3 offset)` | a rigid rider offset in a moving frame (the house Gyre's rider camera) | C0 | — | arc-piano-studies | P1 |

### I5. Analytic history (`motion/history.glsl`)

When motion is a pure function of time, the past is a function call, not a history buffer (shader-craft ceiling).

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float histTrail(vec2 p, float t, float span, int samples)` **hook** | distance to the path a hooked `vec2 pathAt(float t)` traced over [t-span, t], as a chain of segments with a fading width: the house's analytic trail (three implementations today with different constants) | C1 (samples) | Heartfelt (paths as functions of height), Humanimation (16 time-shifted poses instead of stored ones) | arc-vfx-bench; shader-craft ceiling | P1 |
| `float histDelay(float t, float lagSec)` | read a pure-function motion in the past: secondary motion (soft tissue 50 to 75 ms behind) with no physics | C0 | Humanimation | study:ltdcW7 6.3-6.4 | P2 |

### I6. Mechanical motion and sequencing (`motion/mech.glsl`, `motion/sequence.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float mechSmoothSine(float t, float phase, float width)` | smoothstep of a sine: snap, hold, ease, chase and press-and-toggle are one formula with different widths and phases | C0 | Inercia | study:cs2GWD 6.4 | P1 |
| `float seqActs(float t, vec4 actStarts, out float actLocal)` | time-scripted acts with a clock that can freeze or decelerate (freezing time is a remap, not a state change) | C0 | Heartfelt, Sphere Intersect (scripted acts), HAL 4000 (match cut) | study:ltffzl 6.9 | P1 |
| `float seqParamMorph(float t, float hold, float travel, out int from, out int to)` | a parameter-space sequencer: scenes are presets, transitions are morphs between them | C0 | Geodesic | study:llVXRd 6.5 | P1 |
| `float mechStickSlip(float t, float cellRand)` | two motions fighting (a steady belt and a slow in-cell timer) so a drop hangs and then lets go | C0 | Heartfelt | study:ltffzl 6.3 | P2 |
| `ivec3 seqCoprime(float t, ivec3 periods)` | a scene counter with co-prime sub-cycles: combinations that do not repeat for minutes | C0 | Humanimation (periods 4, 5 and 6) | study:ltdcW7 6.7 | P2 |

---

## 12. Family J: State and simulation

A fragment shader forgets everything between frames; a simulation keeps its state in textures it reads back next frame
(WS 1). Everything in this family is C4: it needs the multipass runtime (architecture section 7) and obeys the feedback
floor (two history textures, ping-pong, the first read gated, rebuilt on resize) and the still rule (a reproducible
still is cleared history plus a fixed settle, never a seek).

### J1. Simulation input and output (`sim/io.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec4 simSanitize(vec4 v, float bound, vec4 fallback)` | finiteOr plus a magnitude clamp, so one bad texel cannot poison a feedback loop | C0 | Saturday, Oscillo Donut | WS 1.4 | **P0** |
| `vec4 simLoad(sampler2D s, ivec2 p, ivec2 size, bool wrap)` | exact texel read; out-of-range wraps (torus) or clamps; never filters | C0 +T1 | Dry Ice | WS 1.2 | P1 |
| `vec4 simSample(sampler2D s, vec2 pPix, vec2 size, bool wrap)` | manual bilinear read in pixel space, identical where float textures are not filterable | C0 +T4 | Dry Ice | WS 1.4 | P1 |
| `vec4 simHeader(vec2 res, float layoutVersion)` / `bool simNeedsInit(int frame, vec2 res, vec4 header, float layoutVersion)` | store the size and layout in texel (0,0); re-initialise after a resize or a layout change | C0 | — | WS 1.2 | P1 |
| `vec4 stateRead(sampler2D self, int slot)` / `bool stateIsSlot(vec2 fragCoord, int slot)` | slot-addressed registers in row 0 of a feedback buffer: write state at one pixel, the image elsewhere | C0 +T1 | AURORA (a mouse-integrating state buffer) | GP 12 | P1 |
| `float simDt(float frameDt, float fixedDt, float maxDt)` | a clamped simulation step for hosts without a fixed-step accumulator | C0 | — | WS 2.2 | P1 |

### J2. Stencils (`sim/stencil.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec4 stnLap5(sampler2D s, ivec2 p, ivec2 size)` | 5-point Laplacian in texel units | C0 +T5 | — | WS 5.1 | P1 |
| `float stnDiv(sampler2D vel, ivec2 p, ivec2 size)` | central-difference divergence of the .xy velocity | C0 +T4 | Dry Ice | WS 7.4 | P1 |
| `float stnCurl(sampler2D vel, ivec2 p, ivec2 size)` | scalar vorticity by central differences | C0 +T4 | — | WS 7.5 | P1 |
| `vec2 stnGrad(sampler2D s, ivec2 p, ivec2 size, int channel)` | central-difference gradient of one channel | C0 +T4 | — | WS 7.4 | P1 |
| `vec4 stnBlur9Axis(sampler2D s, ivec2 p, ivec2 size, ivec2 axis)` | one axis of a normalised 9-tap Gaussian; two passes make a separable blur | C0 +T9 | — | WS 5.4 | P1 |
| `vec4 stnLap9(...)` | isotropic 9-point Laplacian with no grid-axis bias | C0 +T9 | — | WS 5.1 | P2 |

### J3. Advection and fluids (`sim/fluid.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 advDepartRK2(sampler2D vel, vec2 pPix, float dt, vec2 size)` / `vec2 advDepartEuler(...)` | semi-Lagrangian backtrace: where the fluid at this pixel came from | C0 +T2 | Dry Ice | WS 7.3; Stam 1999 | P1 |
| `vec4 advectSL(sampler2D q, sampler2D vel, vec2 pPix, float dt, vec2 size)` | gather q at the departure point: unconditionally stable | C0 +T6 | Dry Ice (fused projection and advection) | WS 7.3 | P1 |
| `vec4 advDissipate(vec4 q, float rate, float dt)` | the stable fade q/(1 + rate·dt) | C0 | Dry Ice (clamp-then-damp equilibrium) | WS 7.5 | P1 |
| `float fldJacobiPressure(sampler2D pressure, sampler2D divergence, ivec2 p, ivec2 size)` / `vec2 fldProjectVelocity(vec2 w, sampler2D pressure, ivec2 p, ivec2 size)` | one Jacobi sweep of the pressure Poisson equation; subtract the pressure gradient for a divergence-free velocity | C0 +T5 | Dry Ice (warm-started, temporally amortised pressure solve) | WS 7.4; Harris, GPU Gems ch. 38 | P1 |
| `vec4 fldSplat(vec2 pPix, vec2 centrePix, float radiusPix, vec4 amount)` | Gaussian injection of velocity or dye | C0 | Dry Ice (a moving emitter that carves and pushes) | WS 7.5 | P1 |
| `float fldSponge(vec2 uv, float band, float strength, float dt)` | an absorbing border that soaks up flow or waves instead of reflecting them (it can be the only drag a system needs) | C0 | Dry Ice (vignette-as-sponge) | WS 6.2 | P1 |
| `vec2 fldVorticityForce(...)`, `vec2 fldBuoyancy(...)`, `vec2 fldWallVelocity(...)`, `vec3 fldBoxDeposit(...)`, `vec4 maccormackCombine(...)`, `vec2 advDepartRK4(...)` | confinement, buoyancy, walls, reintegration tracking, error-corrected advection | C0 | — | WS 7.5-7.8 | P2 |

### J4. Waves, ripples and oceans (`sim/wave.glsl`, `sim/ocean.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float waveStep(float hNow, float hPrev, float neighbourSum4, float courant2, float damping)` | explicit 2D wave equation step; courant2 at most 0.5 | C0 | — (house: Spectacle's 256² ripple at a fixed 1/120 s) | WS 6.1; Hugo Elias | P1 |
| `vec3 waveHeightNormal(sampler2D h, ivec2 p, ivec2 size, float scale)` | normal of a height texture | C0 +T4 | Heartfelt (water is a height map; light bending is its slope) | WS 6.3 | P1 |
| `float waveCausticRatio(vec3 pSurface, vec3 pFloor)` | caustic gain = area before refraction / area after | C0 | — | WS 6.3 | P2 |
| the ocean set: `waterOmega`, `omegaLooped`, `gerstnerWave`, `phillipsSpectrum`, `oceanH0`, `oceanHt`, `cmul`, `cexpi`, `fftStage`, `foldJacobian`, `waveExpSine`, `heightfieldNormal` | Gerstner and Tessendorf oceans, a Stockham FFT in passes, foam from the fold Jacobian | C0 to C4 | — | WS 9; Tessendorf 2001 | P2 |

### J5. Pattern simulations and particles (`sim/pattern.glsl`, `sim/particle.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `ivec2 ptcTexel(int id, int width)` / `int ptcId(ivec2 p, int width)` | the texel is the particle's identity | C0 | — (house: Spectacle's GPU particles) | WS 8.1 | P1 |
| `void ptcStepSymplectic(inout vec3 x, inout vec3 v, vec3 a, float dt)` | semi-implicit Euler: velocity first, so orbits do not spiral outward | C0 | — | WS 8.2 | P1 |
| `vec3 clampLength(vec3 v, float maxLen)` | limit a magnitude, keeping direction | C0 | — | WS 8.3 | P1 |
| `void ptcVerlet(...)`, `vec3 ptcBounce(...)`, `vec3 ptcRelaxToFlow(...)` | position Verlet; collision response; drag toward a flow field | C0 | — | WS 8.2-8.4; Latta 2004 | P2 |
| `vec2 rdGrayScott(...)`, `float lifeRule(...)`, `float leniaGrowth(...)`, `float leniaShell(...)`, `int countNeighbours8(...)` | reaction-diffusion; Life-like automata; Lenia | C0 +Tn | — | WS 4, 5; Pearson 1993; Chan 2019 | P2 |
| `float particleDwell(...)` (an idiom, not a function) | brightness from dwell time: uniform time steps plus additive glow reproduce a real beam (slow is bright) | — | Oscillo Donut | study:ldSfWV 6.2 | P2 |

### J6. Temporal accumulation and feedback (`sim/feedback.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec3 fbDecay(vec3 prev, float keep, float floorStep)` | multiply by keep, then subtract one 8-bit step so the buffer actually clears (an 8-bit trail at 0.98 sticks near a tenth of full brightness) | C0 | Oscillo Donut, Saturday | GP finding 6; house Play rule | **P0** |
| `vec2 fbWarp(vec2 uv, vec2 centre, float zoomPerSec, float rotPerSec, vec2 driftPerSec, float dt)` | MilkDrop-style per-step warp: where to read the previous frame | C0 | Saturday (a swirl that preserves radius, so recursion forms spirals) | WS 2.3 | P1 |
| `vec3 fbSoftGate(vec3 c, vec3 lo, vec3 hi)` | a per-channel smoothstep on the fed-back image: a noise gate and gain stage in one, stopping the classic white-out | C0 | Saturday (the single most transferable idea in that shader) | study:43jXWt 6.1 | P1 |
| `vec3 fbPhosphor(vec3 prev, vec3 beam, float keep)` | tanh(prev·keep + beam): bounded afterglow with a filmic shoulder | C0 | Oscillo Donut | study:ldSfWV 6.5-6.6 | P1 |
| `vec4 accProgressive(vec4 history, vec3 sample, bool reset)` / `vec4 accCapped(vec4 history, vec3 sample, float maxCount)` | cumulative mean with the count in alpha; a capped mean that becomes an exponential average | C0 | — | WS 3.1 | P1 |
| `vec3 fireflyClamp(vec3 c, float maxLuma)` | scale down any sample brighter than maxLuma (biased, removes fireflies) | C0 | — | WS 3.2 | P1 |
| the TAA set: `taaJitter`, `toYCoCg`, `fromYCoCg`, `neighbourhoodStats`, `clipToBox`, `sampleCatmullRom`, `lumaWeigh`, `lumaUnweigh`, `reprojectUV`, `historyTrust` | temporal antialiasing after Karis 2014 | C4 | — | WS 3.3; Karis 2014 | P2 |

---

## 13. Family K: Glitch and signal art

The central lesson from both glitch shaders: **corrupt the address, not the data** (craft secret 9). A glitch changes
the screen coordinate or the clock before the scene is evaluated, so it stays crisp at any resolution, needs no frame
buffer, and a "frozen" block can show a genuinely different moment of the scene.

### K1. Address corruption (`glitch/address.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec2 gliBlockGrid(vec2 p, vec2 blockSize, out vec2 blockId)` | snap to block centres; the block id seeds everything | C0 | Glitch Transform (snap to cell centre), Hex Glitch | study:XtyXzW | P1 |
| `float gliProbe(vec2 blockCentre, ...)` **hook** | sample a hooked probability field (for example a hidden 3D proxy object traced at each block's centre), so blocks stay screen-aligned but stick to the object | C0 + hook | Glitch Transform (its signature move: 3D mask, 2D blocks) | study:XtyXzW 6.2 | P1 |
| `float gliGate(float probability, float seed, float t, float period)` | a probability gate re-rolled on a stutter clock (`clkStutter`) | C0 | Glitch Transform | study:XtyXzW 6.6 | P1 |
| `vec2 gliBlockSwap(vec2 p, vec2 blockId, float amount, uint seed)` | branch-free block swap by coordinate displacement | C0 | Glitch Transform | study:XtyXzW | P1 |
| `vec2 gliHierarchy(vec2 p, vec3 levels, float t, uint seed)` | layered swaps where the finest fires only inside a medium one: small detail inside large structure, as codec errors cascade | C0 | Glitch Transform | study:XtyXzW 6.5 | P1 |
| `float gliFreezeTime(vec2 blockId, float t, float probability)` | per-block frozen time: the block shows a different moment of the scene | C0 | Glitch Transform | study:XtyXzW | P1 |
| `vec2 gliStaticJump(vec2 p, float t, uint seed)` | 8-bit static as a coordinate jump | C0 | Glitch Transform | study:XtyXzW | P1 |
| `vec3 gliScanStripes(vec2 p, float t, float intensity)` | scanline colour stripes as the one violent accent | C0 | Glitch Transform | study:XtyXzW 6.8 | P1 |
| `float gliEpoch(int frame, ivec4 periods, out vec4 dice)` | glitch epochs with sub-dice re-rolling on drifting periods, so no rhythm emerges | C0 | Hex Glitch | study:lfscD7 6.3 | P1 |
| `float gliRollingShutter(vec2 p, float t, float speed, float dir)` | a time skew by screen row that sweeps every state change across the screen as a moving seam | C0 | Hex Glitch | study:lfscD7 6.8 | P1 |
| `vec2 gliMacroblock(vec2 p, float t, uint seed)` | Bayer-dithered damage with random block sizes and a stuttering clock | C0 | Hex Glitch | study:lfscD7 4.22 | P2 |

### K2. CRT and oscilloscope (`glitch/crt.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float crtScanlines(vec2 pBulged, float lines, float strength)` | scanlines that bend with the glass | C0 | Oscillo Donut | study:ldSfWV 6.9 | P2 |
| `vec2 crtBezelMirror(vec2 p, float d, vec2 grad)` | mirror any point across any distance-field edge, p - 2·d·∇f: a bezel that reflects the screen | C0 | Oscillo Donut | study:ldSfWV 6.10 | P2 |
| `vec3 crtConvergence(sampler2D src, vec2 uv, float k)` | colour convergence fringes and a ghost | C0 +T3 | Oscillo Donut | study:ldSfWV | P2 |

### K3. Parity compositing (`composite/parity.glsl`)

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float cmpXor(float a, float b)` | even-odd combination of binary layers: no ordering decisions; overlaps create the complexity; near-equal inset copies make moiré | C0 | Hex Glitch (XOR everything), Hexagone (XOR one line from additive) | study:lfscD7 6.5 | P1 |

---

## 14. Family L: Inputs and music

### L1. Mouse and keyboard (`input/mouse.glsl`, `input/keyboard.glsl`)

114 corpus shaders read `iMouse`, which the bench shims to zero; thumbnails then show the "no input yet" pose. These
parts make that state explicit.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `bool mouseUntouched(vec4 mouse)` | all four components zero: no input yet (start-up and thumbnails), so show the designed demo pose | C0 | Glitch Transform, Dry Ice, Marble (orbit cameras) | GP 12 | **P0** |
| `bool mouseHeld(vec4 mouse)` / `bool mouseJustClicked(vec4 mouse)` / `vec2 mouseDragOrigin(vec4 mouse)` | Shadertoy's iMouse conventions | C0 | Isoline Simple (mouse-picked reference level), Hexagone (mouse time scrub), Dark Cloud (mouse to light direction) | GP 12 | **P0** |
| `bool keyDown(sampler2D kb, int code)` / `keyPressed` / `keyToggled` | rows 0, 1 and 2 of the 256×3 keyboard texture | C0 +T1 | — | GP 12 | P1 |
| `bool channelLoaded(vec3 channelRes)` / `bool resolutionChanged(vec2 res, vec2 stored)` | an asynchronously loaded texture has arrived; the canvas changed size | C0 | AURORA (a guard on texture size avoids a load-time flicker) | GP 12 | P1 |

### L2. Audio spectrum (`input/audio.glsl`)

Two facts from GP bind this category: the Web Audio analyser smooths per call, not per second (so the house sets its
smoothing to 0 and smooths with the real frame time); and the spectrum texture has 23.4 Hz per texel, so every key below
G4 is narrower than one texel. **MIDI tells a shader which notes; audio tells it how they sound.**

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `float audSpectrum(sampler2D a, float u)` | row 0 of the 512×2 audio texture at u across the bins; decibel-mapped 0..1, not amplitude | C0 +T1 | Audio Eclipse (linear spectrum per dot) | GP 12 | **P0** |
| `float audBand(sampler2D a, float hzLo, float hzHi, float sampleRate)` | mean linear magnitude over the bins in a band with texelFetch, at most 64 taps: box-filters many bins instead of aliasing | C1 +T≤64 | — (house Play) | GP 12 | **P0** |
| `float midiToHz(float m)` / `float hzToMidi(float hz)` / `float pianoKeyToHz(float key)` | equal temperament: 440·2^((m-69)/12); keys 1..88 | C0 | — (house piano) | GP 12 | **P0** |
| `float audSpectrumAtHz(sampler2D a, float hz, float sampleRate)` | row 0 at u = 4·hz/sampleRate; needs the real sample rate (the shader lab binds 44,100 today, 1.47 semitones off at 48 kHz) | C0 +T1 | — | GP finding 4 | P1 |
| `float audWave(sampler2D a, float u)` / `float audByteToDb(...)` / `float audByteToAmp(...)` | waveform row; byte to decibels; decibels to linear magnitude (required before summing bins) | C0 | — | GP 12 | P1 |
| `float audLogAxisHz(float x, float hzMin, float hzMax)` / `float audTiltDb(float hz, float dbPerOctave, float hzRef)` | log-frequency axis; pink-spectrum tilt so highs are not visually dead | C0 | — | GP 12 | P1 |
| `float envFollow(float prev, float x, float dt, float tauAttack, float tauRelease)` / `float peakHold(...)` | frame-rate-independent attack/release follower; meter peak hold | C0 | — | GP 12.5 | P1 |
| `float halfWaveRise(float now, float prev)` / `float onsetGate(float flux, float meanFlux, float k, float delta)` / `float pulseEnvelope(float since, float hold, float tau)` | spectral flux, an adaptive onset threshold, and the visual hit | C0 | — | GP 12 | P1 |
| `vec2 audLissajousXY(float t, vec3 phasors)` | XY synthesis where the sound is the picture: perfect sync by sharing one function, not by listening | C0 | Oscillo Donut | study:ldSfWV 6.1 | P2 |

### L3. Music ports: the house note bus, GPU side (`input/music.glsl`)

These are the house's own, from the piano arc. The piano census found five separate note-state models and the chord
reading pulled back through a debug door; the seam it proposes is one note bus with one canonical GPU note texture.

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec4 musNote(sampler2D notes, int key)` | one canonical GPU note texture: per key, velocity, held-by-finger, held-by-pedal and the time since onset (release time in a second row) | C0 +T1 | — | arc-piano-core seam 5 | P1 |
| `float musLight(sampler2D notes, int key, float t, LightParams lp)` | the house LIGHT for one key, from the note texture and `envStrikeSag`: keys, trails and every scheme read the same light | C0 +T2 | — | arc-piano-core (1) | P1 |
| `float musProtectMask(vec2 p, vec4 chordBox, vec4 staffBox, float soft)` | protect zones that keep effect light off the chord name and the staff | C0 | — | arc-piano-studies (protect masks) | P1 |
| `vec4 musHarmony(sampler2D harmony)` | tension, lushness, register and pace as typed inputs from the pure signal modules (harmony-feel.js, moment.js) | C0 +T1 | — | arc-daniel-voice (music input ports) | P2 |

---

## 15. Family M: Compositing

| signature | contract | cost | loved | learn | P |
|---|---|---|---|---|---|
| `vec4 cmpOver(vec4 front, vec4 back)` (straight alpha) / `vec4 cmpOverPremul(vec4 front, vec4 back)` | Porter-Duff over | C0 | Starry Planes (front-to-back over), Cube Lines (back-to-front over) | CP 6 | **P0** |
| `void cmpUnder(inout vec4 acc, vec4 layer)` | front-to-back accumulation with early-out when acc.a ≈ 1 | C0 | Starry Planes (opaque sheets plus early exit) | SR 7.2 | **P0** |
| `vec3 cmpAdd(vec3 a, vec3 b)` / `vec3 cmpScreen(vec3 a, vec3 b)` | additive (light-like, for optically thin emitters) and screen (bounded) | C0 | AURORA (additive only), Audio Eclipse (additive mixing without tone mapping), Humanimation (screen-blend bloom) | CP 6 | **P0** |
| `vec3 cmpMax(vec3 a, vec3 b)` | max, not add: overlapping lines never blow out to white | C0 | HAL 4000 (every layer within a family), Plasma Globe (thirteen bolts stay crisp) | craft secret 6 | **P0** |
| `vec4 cmpLumaAlpha(vec3 c, float power)` | luminance as alpha: bright lines opaque, gaps translucent, so stacked layers read as line drawings, not murky plastic | C0 | Cube Lines | study:NslGRN 6.6 | P1 |
| `vec3 cmpOccluderMask(vec3 back, float front, float k)` | exposure masking: a bright foreground hides faint background (stars × (1 - band)) | C0 | AuroraBorealis, Audio Eclipse (the moon is blacker than the sky) | study:MdBfzR 6.5 | P1 |
| `void cmpSort3(inout vec4 a, inout vec4 b, inout vec4 c)` | a three-layer sorting network for correct back-to-front order | C0 | Cube Lines | study:NslGRN | P2 |

---

## 16. Groups: the reference designs

A group is a **recipe module**: a GLSL function (kind `recipe`, in `arsenal/web/glsl/groups/`) that wires primitives
into something that works, and whose header declares the knobs a person turns. Because a group calls primitives rather
than copying them, a fix to `fbm3` or `displayOut` reaches every group that uses it, and through the groups every
surface (the architecture's section 11 explains how that change is made safe).

Each group card gives: what it is; the recipe as a chain of primitives; the knobs (each becomes a UI control with a unit
and a range); its tiers (cheaper and richer versions of the same look, chosen by cost class); the loved shaders that
exemplify it; where it lands in the house; its debug views; and its status.

### 16.1 The groups at a glance

| group | one line | tiers and cost | exemplars | house landing | P |
|---|---|---|---|---|---|
| **finish** | exposure → display transform → grade → encode → static dither: the one tail | C0 | Hex Glitch, Marble, Cloud Ten, Starry Planes, Inercia | every surface | **P0** |
| **aurora** | luminous curtains with a sharp hem, rays and height colour | band (C1), sheets (C2 over layers), volume (C2/C3) | Chromatic Curtains, AURORA, Aurora Lights, AuroraBorealis | cockpit bed, piano Spectacle, First Light, the site hero | **P0** (band, sheets); P1 (volume) |
| **neon-line** | a thin light line with a hot core, a halo and constant pixel width | C0 per segment, C1 per strip | Discoteq, Oscillo Donut, HAL 4000, Plasma Globe, Starship, Apollonian | piano trails, Gyre and Wind strips, activity line | **P0** |
| **studio-object** | a raymarched hero object under a product-shot light rig | C2 + C2 (shadow) | Just a Cube, Saturday, Glitch Transform, Creation Stone, Inercia, Rhodium | avatar, crystal studies, bench hero renders | **P0** |
| **glow-xray** | a pass-through march where light comes from lingering, not from lights | C2 | Bubble Rings, Flame, Alien Core, Blue Red Shiny, Sincos 3D | avatar states, bench, cockpit accents | **P0** |
| **hex-neon** | a hexagonal tiling with per-cell ids driving outline, size and colour | C0 to C1 | Hexagone, Data Warehouse, Hex Glitch, Pretty Hip, Geodesic | piano harmony floors, bench, site | **P0** |
| **volume-fog** | an energy-conserving fog or cloud with real shadows | C3 | Volumetric Sample, Cloud Ten, Dry Ice, Dark Cloud | cockpit bed (its naive integration), Spectacle worlds | P1 |
| **glass** | refraction, absorption and total internal reflection, with something behind the glass | C0 analytic, C3 marched | Marble, Cube Lines, Creation Stone, Plasma Globe | crystal grand, crystal studies, avatar shell | P1 |
| **warp-painting** | nested domain warp coloured from its intermediate fields, with a bump-lit relief | C1 ×5 | Warping (study-only), Aurora Lights, AuroraBorealis | First Light, Play presets, backgrounds | P1 |
| **contours** | any scalar field turned into even-weight engraved lines | C0 | Isoline Triangle, Isoline Simple, Humanimation | story layer, deck backgrounds, data views | P1 |
| **kaleido-rings** | polar ids where every ring rotates, mirrors and colours from its id | C0 | Satisfying, HAL 4000, Audio Eclipse | piano harmony modes, Play | P1 |
| **glitch-transition** | address corruption gated by a probability field on a stutter clock | C0 to C2 | Glitch Transform, Hex Glitch, Oscillo Donut | deck transitions, Edit mode, piano story moments | P1 |
| **feedback-trail** | ping-pong history with per-second decay, a warp and a soft gate | C4 | Saturday, Oscillo Donut, AURORA | Play, First Light, piano motion blur | P1 |
| **sky-dressing** | stars, sky gradient, sun lobes and an occluding horizon | C0 to C1 | AURORA, Aurora Lights, AuroraBorealis, Cloud Ten, Chromatic Curtains | aurora backdrops, Spectacle worlds | P1 |
| **zoom-conveyor** | infinite zoom from a few staggered layers on a conveyor belt | C0 × layers | Hexagone, HAL 4000, Starry Planes | Play, bench, deck interludes | P1 |
| **slice-wireframe** | an implicit surface drawn as glowing contours on depth slices | C1 × slices | HAL 4000; house orrery and superquadric slices | avatar alternatives, bench | P1 |
| **flight-tunnel** | an analytic path, a banked look-ahead camera and a carved lattice with glow in the field | C2 | Blue Red Shiny, Starry Planes, Cloud Ten | Gyre flight, deck interludes | P1 |
| **plasma-electric** | bolts from lines with crackle, a volume walk and max-combining | C2 | Plasma Globe, Flame | avatar "tool use" state, piano attacks | P1 |
| **fractal-lace** | an Apollonian slice or Kaliset field with neon lines and a lit wall | C1 to C2 | Apollonian, Sphere Intersect | backgrounds, deck | P2 |
| **audio-ring** | spectrum dots on a ring whose glow singularity hides behind an occluder | C1 | Audio Eclipse | Play, First Light | P1 |
| **pegboard** | a cell-clamped march where every cell holds a different animated module | C2 | Inercia | the bench's own module gallery | P2 |
| **rain-on-glass** | drop grids with stick-slip, trails, fused drops and mip fog | C1 | Heartfelt | piano atmosphere "rain", site | P2 |
| **scope-crt** | a beam with dwell brightness, phosphor feedback and a curved, reflecting screen | C4 | Oscillo Donut | activity line, Play | P2 |
| **fluid-fog-2d** | stable fluids in 2D, carved by emitters, rendered as a height-field volume | C4 | Dry Ice | cockpit bed (emitters carve fog), Spectacle | P2 |
| **dancer** | keyframed motion with delay lines and a capsule skeleton | C2 + C4 | Humanimation | story layer experiments | P2 |

### 16.2 finish (P0)

- **What:** the house display tail, as one recipe whose knobs are the "Finish" panel on every page.
- **Recipe:** `expose` → (optional `glowToneBloom` for soft fields) → display transform chosen by `curve` (`tmTanh`,
  `tmExp`, `tmAcesFit`, `tmPbrNeutral`; `tmAgx` when built) → `grdSaturation` → `vigCorner` → `srgbEncode` →
  `grdSCurveDisp` → `ditherOut` with `dthIgn` (static). Entry: `displayOut`.
- **Knobs:** exposure (stops, -4..4, 0); curve (choice); saturation (ratio, 0..2, 1); vignette (ratio, 0..1, 0.25);
  S-curve (ratio, 0..1, 0); dither (bits, 6..10, 8).
- **Presets:** "glow field" (tanh, the cockpit and First Light default), "true colour" (PBR Neutral: matches the piano's
  three.js Neutral), "cinema punch" (ACES fit), "legacy cockpit" (superlinear highlight then tanh, the current bed's
  exact chain via the legacy twin `tmSuperlinear`).
- **Exemplars:** the post stacks of Hex Glitch (gamma lift, lifted blacks, soft whites, vignette), Marble (dither,
  S-curve, gamma, vignette), Cloud Ten (S-curve, sRGB, vignette), Starry Planes (ACES then square root), Inercia
  (split-tone S-curve).
- **House landing:** every surface. It replaces the "filmic finish" group in `design/vfx-groups.json`, whose last link
  (`triangular-dither`) crawls.
- **Debug views:** `dbgFalseStops`, `dbgClipZebra`, `dbgGamut`, `testcardHueExposure` (P1 parts; the finish is usable
  without them).

### 16.3 aurora (P0 for the band and sheet tiers)

- **What:** luminous curtains: a sharp lower hem, vertical rays, colour by height (green body, red top, a purple fringe
  low), slow drift and travelling surges, additive over a dark sky.
- **Recipe, band tier (family A in VA 7.2, C1):** `uvCentered` → `warpShear2` (opposite slides) or `warpFbm2` →
  `noiseTriangle2` or `fbm2` stretched anisotropically → `shpInvPower` (narrow noise, steep transfer) → height bands
  from `auroraProfile` and `auroraLineColor` mapped to screen height → `auroraRays` → `envBreath` along x →
  `cmpAdd` over `skyGradient` → `displayHueSafeGamma` → `finish`.
- **Recipe, sheet tier (family B, C2 over layers):** `camRay` → for i in layers: `marchStepPoly(i)` height →
  `ixPlane` → 2D footprint (`noiseTriangle2` on a rotated, warped domain) → running average (a one-pole low-pass along
  height that removes sheet stepping) → `auroraLineColor` by layer height with exponential weight by index →
  `rmJitterStart` from `dthIgn` (static) → bowl-shaped sheets (a small offset that compresses toward the horizon) →
  optional mirrored pass for a lake → `cmpAdd` → `finish`.
- **Recipe, volume tier (family C, P1):** `ixSlabY` (the box floor is the hem) → `auroraVolume` with
  `volStepEmit` → `displayHueSafeGamma`.
- **Knobs:** intensity (ratio), hem height (world), curtain width (world), fold amount (ratio), ray strength (ratio),
  drift speed (per second, slow), energetic fringe (ratio), palette (choice of house palettes in `palRamp3` form),
  layers (count, cost-tagged).
- **Exemplars:** Chromatic Curtains (sheets: 26 evaluations of a 2D field give a curtain at 2D prices), AURORA (volume:
  the noise never sees height, so it extrudes into walls), Aurora Lights (band: narrow noise, steep transfer, opposite
  slides, stretch equals rays), AuroraBorealis (band: a powered tent, phase-coupled breathing).
- **House landing:** the cockpit light bed (an aurora by name, implemented nine times with three palettes; arc-arcs),
  the piano Spectacle aurora instrument, First Light's aurora-ribbons preset, the akashiclabs hero.
- **Debug views:** layer index as colour; footprint alone; the running average off; jitter off (shows banding).

### 16.4 neon-line (P0)

- **What:** a thin line of light, never thinner than a pixel, with a hot core that whitens with intensity and a halo
  whose falloff is a choice.
- **Recipe:** `sd2Segment` (or a hooked curve, sampled as segments) → profile chosen by `profile`: `glowTwoGauss`
  (the house's core plus halo), `glowLorentz` (needle core, long tails), `shpInvPower`, or `glowCompactWire` (no tail)
  → `aaWire` for the core's coverage → `glowHotCore` → combine by `cmpMax` (crisp, never white) or `cmpAdd` (light-like)
  → the caller's composite.
- **Knobs:** width (pixels, 0.5..8), halo (pixels, 0..64), profile (choice), core heat (ratio), combine (choice),
  defocus with distance (ratio: Discoteq's blur that grows toward the edges is a free depth cue).
- **Exemplars:** Discoteq (detuned additive family, pinned ends, fades not cuts), Oscillo Donut (Lorentzian beam, dwell
  brightness), HAL 4000 (compact-support wires, max not add), Plasma Globe (max across bolts), Starship (comet tails),
  Apollonian (neon line glow from a distance field).
- **House landing:** the piano trails and every study's strip extrusion (four near-identical copies) and core-plus-halo
  profile (seven copies with different constants), the activity line. This is the group with the most house copies.
- **Debug views:** footprint heat (`dbgFootprint`), core coverage alone, halo alone.

### 16.5 studio-object (P0)

- **What:** a raymarched hero object, lit like a product shot: soft boxes in its reflections, a floor pool, a soft
  shadow, and antialiased silhouettes.
- **Recipe:** `camLookAt` + `camRay` (telephoto by default) → `rmClipToBox` (P1; until then `ixSphere` as a bound) →
  `rmSphereTrace` over the hook `mapScene` (built from D1-D4 parts) → `nrmTetra` with `nrmEps` → `visSoftShadow` →
  `visAO` → `rigStudio` (wrapped key, sky, back, rim, specular) with `litStudioEnv` in the reflections and
  `litFresnelSchlick` → `litFloorPool` under it → `aaConeCoverage` from the march's smallest d/t → `fogExp` to the
  backdrop → `finish`.
- **Hooks:** `float mapScene(vec3 p)`; `vec3 materialAt(vec3 p, vec3 n, float id)`.
- **Knobs:** soft-box size and placement (world, turns), key angle (turns), Fresnel floor (ratio: Saturday's 0.5 makes
  everything polished metal; Just a Cube's 0 makes a dark mirror), shadow softness (light angle in degrees), AO reach
  (world), floor pool radius (world), march steps (count, cost-tagged), omega (ratio, under-relaxation for fields that
  lie).
- **Exemplars:** Just a Cube (rim-bright soft box, dark mirror, glow for free), Saturday (analytic studio, backstep
  march), Glitch Transform (wrapped key, half-strength shadows, five-tap AO, dual solids), Creation Stone (curvature
  polishing, up-facing reflections), Inercia (two lights, no ambient), Rhodium (soft shadow by nearest miss).
- **House landing:** the bench's hero renders, the crystal studies (their soft-box PMREM is the three.js twin of
  `litStudioEnv`), the avatar's lit styles.
- **Debug views:** `dbgHeatCount` of steps, normals as colour, AO alone, shadow alone, `dbgSlice` through `mapScene`.

### 16.6 glow-xray (P0)

- **What:** a march that never stops at the surface and lights everything it passes near: x-ray glass, flame, sinew.
- **Recipe:** `camRay` → loop with `rmPassStep` over the hook `mapScene` → per step `glowAccum` (proximity) and/or
  `glowEmitStep` → colour by depth with `palCos` (hue encodes depth, separating transparent layers) → `glowStepCount`
  as an optional rim → `tmRootGain` or `tmTanh` through `finish`.
- **Knobs:** budget (steps; the budget is the opacity), passthrough (world), density (ratio), spark width (world),
  palette (cosine coefficients as a preset), depth hue speed (turns per world unit).
- **Exemplars:** Bubble Rings (never stop at the surface; a slow field is a feature), Flame (brightness from step count;
  overdrive as a blackbody), Alien Core (the glow is the step count; a huge smooth-min radius turns sticks into sinew),
  Blue Red Shiny (glow inside the distance function, two falloff widths), Sincos 3D (the running minimum).
- **House landing:** avatar states (thinking versus tool use differ in kind of motion), bench sketches, cockpit accents.
- **Debug views:** steps heat, per-step contribution, field slice.

### 16.7 hex-neon (P0)

- **What:** a hexagonal tiling where each cell's id drives its size, spin, delay and colour, outlined in antialiased
  neon.
- **Recipe:** `uvCentered` → `latHex` (offset and centre id) → `hash21` of the id → `patCellDelay` or `patRadialWave`
  for a per-cell size → `rotate2` by an angle tied to size (Hexagone's breathing iris) → `sd2Hexagon` → `aaStroke` and a
  `glowExp` halo → `palCos` or `palPitchFifths` by id → optional `latHexNeighbourMin` for oversized shapes → `cmpAdd` or
  `cmpXor` → `finish`.
- **Knobs:** cell size (pixels or world), line width (pixels), wave speed (per second), size amplitude (ratio), spin
  coupling (ratio), palette (choice), combine (choice: additive light or XOR graphic).
- **Exemplars:** Hexagone (conveyor zoom, size-coupled spin, neighbour sum), Data Warehouse (hex to isometric cubes with
  three shades), Hex Glitch (cube coordinates, shatter storm, XOR layers), Pretty Hip (square cousin: per-cell delay,
  hidden polarity flip), Geodesic (the sphere version: fold first, tile once).
- **House landing:** the bench's legacy `hex-grid` chunk (rebuilt on `latHex`), piano harmony floors, deck backgrounds.
- **Debug views:** `dbgCells`.

### 16.8 The P1 and P2 groups, in brief

- **volume-fog (P1).** `ixSlabY` or `ixSphere` bounds → density from `fbm3` shaped by `shpRemap`, or `densFromSDF` →
  `rmHybridStep` → `volStepScatter` with `phaseHG` and `volLightOneTap` (or `volLightMarch` at C3) → `volSaturated` early
  exit → `volResolve` over `skyGradient` → `finish`. Knobs: density, coverage, softness, light angle, phase g, steps.
  Exemplars: Volumetric Sample (energy-conserving step, hybrid march, coloured lights inside fog), Cloud Ten (sloped
  deck, scout pass, clouds wear the sky), Dry Ice (2.5D fog with real self-shadow), Dark Cloud (no marching at all: a
  closed-form skin). Landing: the cockpit bed's fog (its integration is the naive form; changing it is a ceiling change
  for Daniel's gate).
- **glass (P1).** Analytic tier: `ixSphere` or `ixBox` → `litRefractTIR` → `volTransmittance3` with
  `litSigmaFromColour` → `litFresnelSchlick` with `visHorizonFade` → something behind it (a `patTruchet` sky, a floor
  with `visSphereOcclusion`) → `aaDiscriminantEdge`. Marched tier: `litGlassMarch`. Exemplars: Marble, Cube Lines,
  Creation Stone, Plasma Globe (fake haze). Landing: crystal grand and crystal studies, the avatar shell.
- **warp-painting (P1).** `warpNested2` → colour from q and r and a threshold on r → `nrmHeight2` bump →
  `litHemisphere` and `litWrapDiffuse` → `finish`. Learn it from NP 8; Warping is study-only.
- **contours (P1).** Any field → `isoMajorMinor` (or `isoPressure`) → multiply into the colour (lines inherit the hue) →
  park the palette seam under a major line.
- **kaleido-rings (P1).** `domRings` → per-ring `rotate2` then `domKaleido` → `sd2Arc` with arc-length-correct caps →
  `palCos` by id → crest-gated gloss.
- **glitch-transition (P1).** `gliBlockGrid` → `gliProbe` (a hidden proxy field) → `gliGate` on `clkStutter` →
  `gliHierarchy` → `gliBlockSwap`, `gliFreezeTime`, `gliStaticJump` → `gliScanStripes` → optional `gliRollingShutter`.
  The probability peaks on the transformation front, so the glitch serves the story.
- **feedback-trail (P1).** `fbWarp` → read previous → `fbSoftGate` → `fbDecay` with `clkKeep` → `simSanitize` → write;
  hue rotation stays outside the loop (Play rule).
- **sky-dressing (P1).** `skyGradient` + `starsDirCells` (exposure-masked by `cmpOccluderMask`) + `litSkyLobes` +
  optional `skyMountainSilhouette`.
- **zoom-conveyor (P1).** Three or more layers from `patZoomLayer`, each reseeded at birth, fade × life.
- **slice-wireframe (P1).** For each depth slice, a 2D contour of `sbSuperquadric` (or any field) drawn with
  `glowCompactWire`, combined with `cmpMax`, slices scrolled by the fractional part of time; neon by `palHeatPowers`.
  The house already has three Z-slice renderers (orrery, superquadric slices, HAL-style sketch) to consolidate here.
- **flight-tunnel (P1).** `pathLissajous3` → `camBanked` look-ahead → `domMirror` path-relative → `domRepeat` lattice
  carved by `opIntersect` → glow in the field (`glowAccum`) → `matMultiplyReflection` → `fogAdditiveTint`.
- **plasma-electric (P1).** Bolts as `sdCapsule` whose direction varies with radius → `wavStackedTri` crackle →
  short fixed-step volume walk from the hit → `cmpMax` across bolts → `litFakeGlassHaze`.
- **audio-ring (P1).** `domToPolar` ring placement → `audSpectrum` or `audBand` per dot → `glowAccum` (1/d) → an
  occluding `sd2Circle` that hides every singularity → hue wheel by angle → additive. Gain set from the sum, not one dot.
- **fractal-lace, pegboard, rain-on-glass, scope-crt, fluid-fog-2d, dancer (P2).** Specialised; each waits for a piece
  that asks for it. Their primitives are listed in families C7, D5, E3, J and K.

---

## 17. Craft secrets: the application notes

Tricks that recur across the loved shaders and belong to no single datasheet. Each names who teaches it and how the
library encodes it, so a secret becomes a part, a default, a lint rule or a debug view instead of folklore.

1. **Analytic before iterative.** A closed form is exact, stable as the camera moves and cheap; the budget then goes
   into what the eye reads. Cube Lines (every surface, even the shadow, is a formula: razor-stable edges), Starry Planes
   (16 exact ray-plane divisions instead of marching), Dark Cloud (the whole volume is two cosines and a closed-form
   integral), Sphere Intersect, Marble. *Encoded as:* family E1 first; `rmPlaneStack`; the module README's
   "analytic before iterative" convention; the `cost` field makes the price visible.
2. **Light from the march itself.** Glow from the closest approach, from step counts, or from emission added inside the
   distance function: no lights, no normals. Just a Cube, Flame, Alien Core, Bubble Rings, Blue Red Shiny, Sincos 3D.
   *Encoded as:* `rmSphereTrace` returns steps and the smallest d/t; `glowAccum`, `glowExp`, `glowStepCount`; the
   glow-xray group.
3. **Contrast is a decision made after the noise.** Make the field soft and narrow, then carve structure with a steep
   curve: an inverse power, a high power as a sparse selector (s^70 lets only the top sliver through: twinkling from a
   4% mix), a smoothstep window. AURORA, Aurora Lights, AuroraBorealis, Data Warehouse (pow 8 for sparse twinkles),
   HAL 4000. *Encoded as:* shaping parts (`shpInvPower`, `shpTentPow`, `shpRemap`) sit between noise and colour in every
   group, with their own knobs.
4. **Nothing in sync: incommensurate rates and detune.** Rates that never line up (0.05 × {1, 0.72, 1.45, ...} in
   Chromatic Curtains, ripples at +1 and -2 in AURORA, camera periods of 28 and 76 s in Cube Lines, counters of 4, 5 and
   6 in Humanimation, irrational tumble rates in Saturday, six detuned oscillators in Discoteq). A loop teaches its
   period in thirty seconds (shader-craft ceiling). *Encoded as:* motion knobs default to incommensurate ratios; a lint
   warning for two rates in a simple integer ratio within one module (P1).
5. **Hide every seam inside a saturated state or under a feature.** Pretty Hip puts its clock wrap in a fully empty
   frame and its polarity flip in a fully lit one; Isoline Simple parks the palette seam under a major contour; Audio
   Eclipse hides the 1/d singularity behind the moon; Starry Planes fades both ends of each sheet's life; Bubble Rings
   loops by symmetry. *Encoded as:* the house rule "put every cut inside a full or empty frame" in the motion parts'
   notes; `envTwoStroke`; the audio-ring group's occluder.
6. **Know when light should sum.** Optically thin emitters add (AURORA: overlapping folds brighter, stars through the
   curtain); line drawings take the max so crossings never blow out (HAL 4000, Plasma Globe). The piano's rule ("never
   sum light", Neon Trails excepted behind a density guard) is the same decision. *Encoded as:* every glow group has a
   `combine` knob (add, screen, max); the default is per group, never implicit.
7. **One scalar, a whole palette: channels that saturate in sequence.** Per-channel powers or ratios make hue shift
   with intensity (deep, then hot, then white): HAL 4000, Rhodium (1, 1/4, 1/16), Flame and Just a Cube (channels clip
   in order), Starship (tanh desaturates highlights by itself). *Encoded as:* `palHeatPowers`, `glowHotCore`.
8. **Extrapolating mix.** A mix factor outside [0,1] gives colours more saturated than either end, overbright births
   that cool, gradients from a two-colour palette. Flame, Marble, Data Warehouse, Pretty Hip. *Encoded as:*
   `grdAwayFrom`.
9. **Corrupt the address, not the data.** Glitches change the coordinate or the clock before evaluation, so they stay
   crisp, need no buffer, and frozen blocks show another moment. Glitch Transform, Hex Glitch. *Encoded as:* family K1;
   the glitch-transition group takes a hooked scene and a hooked probability field.
10. **One driver for everything.** One id (Satisfying: twenty animated rings from one rounding), one hash split into
    three dice (Inercia), one path (Starry Planes: stars centred on it, camera on it, twist from its curvature), one
    clock (Rhodium), coupled clocks (Hexagone: camera height and zoom share a sine), one colour constant (Just a Cube:
    the whole palette moves with one value). Coherence by construction. *Encoded as:* groups expose one driver knob and
    derive the rest; the param schema supports derived params.
11. **History as a function call.** When motion is a pure function of time, trails, lag and secondary motion are reads
    of the past, not stored frames: Humanimation (16 time-shifted poses; the belly 50 ms behind the hips), Heartfelt
    (paths as functions of screen height); the house's analytic trails. *Encoded as:* `histTrail`, `histDelay`; the
    feedback family is the fallback, not the default.
12. **Static grain, unless frames are being averaged.** Chromatic Curtains freezes both its march jitter and its dither
    per pixel; Oscillo Donut seeds its blur by position, not time. AURORA and Dry Ice animate theirs because their eye
    or buffer integrates frames. House floor 8 makes the first the default. *Encoded as:* `dthIgn`, `dthR2` static;
    `dthIgnFrame` only behind a host flag that says "this host accumulates"; lint flags `u_time` or a frame counter
    flowing into a hash.
13. **Debug views are instruments.** Glitch Transform's per-layer switches, Dark Cloud's A/B split and overflow flag, Dry
    Ice's flat buffer view, RM Experiment 23's contact sheet. *Encoded as:* family A7; every module header lists its debug
    views; every host can switch to them; the bench shows them beside the picture.
14. **Under-relax when the field lies, and let blur hide what is left.** A ×50 relief needs a 0.5 step (RM Experiment
    23); an approximate distance estimate needs 0.6 (Apollonian); Rhodium's field over-reports by five times and its
    depth of field hides the errors; Bubble Rings shows that a slow field can make an image richer. *Encoded as:* omega
    on `rmSphereTrace`; `opDisplace` and `lipTwist` carry honest Lipschitz figures; `dbgOvershoots` and
    `dbgGradientError` measure the lie.
15. **Deliberate macro, procedural micro.** The big shape is designed (Cloud Ten's ridges from one warped sine wave;
    Dry Ice's two scales of forcing; Flame's coarse moving noise over still fine noise; Volumetric Sample's moving shape
    noise over fixed density noise). Noise is the texture, never the composition. *Encoded as:* groups separate a
    "form" stage from a "detail" stage, each with its own knobs.
16. **Choreography is half the film.** Cloud Ten flies like a plane (yaw coupled to roll, a bob, a look-back); HAL 4000
    is a stack of clamp ramps with a match cut; Heartfelt is smoothstep windows on a clock that slows; Cube Lines curates
    its first frame. *Encoded as:* family I; `seqActs`; the camera parts with exact derivatives.
17. **A dark, tinted ground.** Plasma Globe sits on dark violet, Geodesic on deep navy, Rhodium's glow leaves a faint
    warm floor; none is pure black, yet none washes the frame. The house ceiling says "black stays black: no ambient, no
    floor wash". Both are true at once: a very dark *tinted* ground is not an ambient wash. (Section 20 asks Daniel.)
18. **Glass needs something behind it.** Marble paints a Truchet maze on the sky and a floor shadow so refraction is
    legible; Cube Lines builds a fake interior per face; Creation Stone renders an inner landscape. *Encoded as:* the
    glass group requires a backdrop hook.
19. **Sell the medium.** Oscillo Donut's scanlines, bezel reflection and lifted black; Hex Glitch's lifted blacks and
    capped whites; Heartfelt's fogged glass and parallax. The medium's artefacts are the authenticity. *Encoded as:*
    the scope-crt group; `grdLiftedFinish`.
20. **Learn the physics, then paint.** Aurora bands in the order oxygen and nitrogen emit them; a sun of four lobes of
    different temperature; candle flames blue at the base. Physically ordered colour reads as true even when the
    method is a fake. *Encoded as:* `auroraLineColor`, `palBlackbody`, `litSkyLobes`.
21. **Constant pixel width.** Lines that divide by their own screen derivative stay one pixel wide at every distance
    and angle (Isoline Triangle, Isoline Simple, Humanimation's contours); pens keep their width while a grid
    subdivides (Hex Glitch). *Encoded as:* family C2 and C3; Daniel's ruling R4 (pixel perfect, un-aliased).
22. **Cheap depth.** Parallax between layers (Heartfelt: glass scales about four times while the background moves 10%),
    a zoom gradient as perspective (Aurora Lights), a telephoto lens (Bubble Rings, Volumetric Sample), a conveyor of
    layers (Hexagone). *Encoded as:* `camRay` focal, `patZoomLayer`.
23. **Energy first, display last.** Dark Cloud sets its sun at ten times so small physical fractions read; Blue Red
    Shiny lets values be huge and rescales at the end; Rhodium blurs unclipped energy so highlights bloom into discs;
    Starry Planes paints HDR into a filmic curve. *Encoded as:* the currency law (section 1, law 6), `expose`, and the
    single `displayOut` tail.
24. **Cost lands where the eye looks.** Starry Planes' rays mostly stop on the first sheet, so only the axis pays for
    depth; Cube Lines supersamples only at edges; RM Experiment 23 gives thumbnails a third of the steps; Humanimation
    gates the body with a bounding sphere. *Encoded as:* the `cost` field and its tiers; `bvCanSkip`; quality tiers as
    a declared param class.

---

## 18. The P0 build manifest

What "build tonight" means, file by file, in the order the architecture's slices build it (`unified-architecture-draft.md`
section 15). Batch A is the floor of success for the night; batch B is the six P0 groups and what only they need.

### Batch A: foundations, colour and the finish (every surface needs these)

| file (under `arsenal/web/glsl/`) | functions |
|---|---|
| `core/const.glsl` | `PI`, `TAU`, `PHI`, `SQRT3` (after the composer learns to provide consts) |
| `core/safe.glsl` | `dot2`, `safeDiv`, `safeNormalize`, `safeSqrt`, `safeAcos`, `safePow`, `finiteOr` |
| `core/rotate.glsl` | `rotate2` |
| `core/int.glsl` | `imodFloor`, `cellIndex` |
| `core/compile.glsl` | `unrollBarrier` |
| `core/clock.glsl` | `clkPhase`, `clkKeep`, `clkAlpha` |
| `core/frame.glsl` | `uvCentered`, `uvPixel`, `uvFootprint` |
| `core/shaping.glsl` | `shpLinstep`, `shpSmoother`, `shpImpulse`, `shpPulse`, `shpGain`, `shpParabola`, `shpSoftAbs`, `shpTri`, `shpRemap`, `shpInvPower` |
| `hash/pcg.glsl` | `hashU1`, `pcg3d`, `pcg4d`, `u01`, `cellU2`, `cellU3`, `hash21`, `hash22`, `hash31`, `hash33` |
| `legacy/hash-sine.glsl` | `hashSine21`, `hashSine31` |
| `noise/value.glsl` | `noiseValue2`, `noiseValue3` |
| `noise/gradient.glsl` | `noiseGrad2`, `noiseGrad3` |
| `noise/fbm.glsl` | `gainFromHurst`, `fbm2`, `fbm3` (after slice S2 renames the legacy `fbm3`) |
| `noise/warp.glsl` | `warpVec2`, `warpFbm2`, `warpNested2` |
| `noise/dither-masks.glsl` | `dthIgn`, `dthR2`, `dthTriFromUniform` |
| `colour/transfer.glsl` | `srgbEncode`, `srgbDecode`, `luminance`, `cbrtSigned` |
| `colour/oklab.glsl` | `oklabFromLinear`, `linearFromOklab`, `oklchFromOklab`, `oklabFromOklch`, `mixOklab`, `mixOklch`, `hueDelta`, `inGamut`, `oklchClip`, `hueRotateOklch` |
| `legacy/hsv.glsl` | `hsvToRgb`, `rgbToHsv` |
| `colour/palette.glsl` | `palCos`, `palCosLinear`, `palOklch`, `palRamp3`, `palHeatPowers`, `palPitchFifths` |
| `colour/tone.glsl` | `expose`, `tmTanh`, `tmExp`, `tmReinhard`, `tmAcesFit`, `tmPbrNeutral`, `tmRootGain`, `displayHueSafeGamma` |
| `legacy/tone-superlinear.glsl` | `tmSuperlinear` |
| `colour/grade.glsl` | `grdSaturation`, `grdAwayFrom`, `grdSCurveDisp` |
| `post/vignette.glsl` | `vigCorner` |
| `post/dither.glsl` | `ditherOut` |
| `post/display-out.glsl` (recipe) | `displayOut` |
| `debug/views.glsl` | `dbgHeatRamp`, `dbgHeatCount`, `dbgRangeScope`, `dbgNaN`, `dbgSlice`, `dbgCells` |
| `composite/blend.glsl` | `cmpOver`, `cmpOverPremul`, `cmpUnder`, `cmpAdd`, `cmpScreen`, `cmpMax` |
| `motion/envelope.glsl` | `envRamp`, `envWindow`, `envCubicEase`, `envSineEase`, `envFlashSafe` |
| `input/mouse.glsl` | `mouseUntouched`, `mouseHeld`, `mouseJustClicked`, `mouseDragOrigin` |
| `input/audio.glsl` | `audSpectrum`, `audBand`, `midiToHz`, `hzToMidi`, `pianoKeyToHz` |
| `sim/feedback.glsl` | `simSanitize`, `fbDecay` |

### Batch B: the six P0 groups and their parts

| file (under `arsenal/web/glsl/`) | functions |
|---|---|
| `noise/triangle.glsl` | `noiseTriangle2` |
| `draw2/sdf2.glsl` | `sd2Circle`, `sd2Box`, `sd2RoundBox`, `sd2Segment`, `sd2Hexagon` |
| `draw2/aa.glsl` | `aaFill`, `aaStroke`, `aaWire`, `aaStep` |
| `draw2/domain2.glsl` | `domToPolar`, `domFromPolar`, `domRepeat2`, `domKaleido` |
| `draw2/lattice.glsl` | `latHex`, `latHexEdge` |
| `sdf/shapes.glsl` | `sdSphere`, `sdBox`, `sdRoundBox`, `sdPlane`, `sdTorusY`, `sdCapsule` |
| `sdf/combine.glsl` | `opUnion`, `opIntersect`, `opSubtract`, `opPick`, `opSmin`, `opSminMix`, `opSmax`, `opRound`, `opOnion`, `opUniformScale` |
| `sdf/domain3.glsl` | `domRigid` |
| `ray/intersect.glsl` | `ixSphere`, `ixBox`, `ixPlane`, `ixSlabY` |
| `ray/camera.glsl` | `camLookAt`, `camRay`, `camPixelAngle` |
| `ray/march.glsl` | `rmEpsilon`, `rmSphereTrace`, `rmPassStep`, `rmHybridStep`, `rmJitterStart` |
| `ray/normals.glsl` | `nrmTetra`, `nrmEps` |
| `ray/aa3.glsl` | `aaConeCoverage` |
| `light/diffuse.glsl` | `litLambert`, `litHalfLambert`, `litWrapDiffuse`, `litHemisphere` |
| `light/specular.glsl` | `litBlinnPhong` |
| `light/fresnel.glsl` | `litFresnelSchlick`, `litF0FromIor`, `litRim` |
| `light/lights.glsl` | `litInverseSquare` |
| `light/visibility.glsl` | `visSoftShadow`, `visAO` |
| `light/env.glsl` | `litStudioEnv`, `litFloorPool` |
| `light/glass.glsl` | `litRefractTIR`, `litSigmaFromColour` |
| `light/glow.glsl` | `glowAccum`, `glowEmitStep`, `glowExp`, `glowLorentz`, `glowTwoGauss`, `glowHotCore`, `glowStepCount` |
| `light/rigs.glsl` | `rigStudio` |
| `volume/integrate.glsl` | `VolAccum`, `volAccumInit`, `volOpacityFactor`, `volTransmittance`, `volTransmittance3`, `volStepScatter`, `volStepEmit`, `volSaturated`, `volResolve` |
| `volume/phase.glsl` | `phaseIso`, `phaseHG` |
| `volume/density.glsl` | `densFromSDF` |
| `volume/march.glsl` | `marchStepPoly`, `volLightOneTap` |
| `atmos/fog.glsl` | `fogExp` |
| `atmos/aurora.glsl` | `auroraProfile`, `auroraLineColor`, `auroraRays` |
| `groups/aurora-band.glsl`, `groups/aurora-sheets.glsl`, `groups/neon-line.glsl`, `groups/studio-object.glsl`, `groups/glow-xray.glsl`, `groups/hex-neon.glsl` | the six P0 recipes |

Batch A is 31 files and about 120 functions; batch B is 34 files (six of them group recipes) and about 95
functions. If the night is short, batch A alone is a complete win: it is every surface's
foundation and it retires the crawling dither, the colour-currency drift and the sine-hash sprawl.

---

## 19. Reverse index: what each loved shader teaches

For the Shelf (architecture section 9): each loved shader links to the groups it exemplifies and the parts it teaches
best. Bold marks the shader's signature lesson.

| shader | groups | parts it teaches best |
|---|---|---|
| AURORA | aurora (volume), sky-dressing | **noise extruded by spending its third dimension on time**; `ixSlabY` hem; `shpInvPower`; `dthBlue` + golden step; `litLineLight`; `nrmEps` |
| Aurora Lights | aurora (band), warp-painting | **narrow noise, steep transfer**; `warpShear2`; anisotropic stretch; physically ordered bands; `envBreath` |
| Chromatic Curtains | aurora (sheets), sky-dressing | **stacked sheets at 2D prices**; `marchStepPoly`; running average; `noiseTriangle2`; static jitter and dither; `glowToneBloom` |
| AuroraBorealis | aurora (band) | **a powered tent breathes**; sparse-selector twinkle; `cmpOccluderMask` |
| Cloud Ten | volume-fog, sky-dressing, flight-tunnel | **the cloud is a floor**; `rmScout`; clouds wear the sky; `volLightOneTap`; four-lobe sun; flight camera |
| Dark Cloud | volume-fog | **no marching at all**; `warpRayOrigin`; skin model; the media composite rule; debug A/B |
| Volumetric Sample | volume-fog | **the energy-conserving step** (`volStepScatter`); `rmHybridStep`; `densFromSDF`; coloured lights in fog |
| Dry Ice | fluid-fog-2d, volume-fog | **a 2D simulation in a 3D costume**; emitters carve; `fldSponge`; warm-started pressure; self-shadow |
| Glitch Transform | glitch-transition, studio-object | **3D mask, 2D blocks**; address corruption; hierarchical gating; debug defines; dual solids |
| Bubble Rings | glow-xray | **never stop at the surface; the budget is the opacity**; `opOnion`; `opSmax`; `palCos` by depth |
| Geodesic | hex-neon (sphere), studio-object | **fold first, tile once** (`domFoldIcosa`); per-panel animation; emissive seams; parameter-space sequencer |
| Isoline Triangle | contours | **any field becomes a drawing**; constant width; pressure strokes; `noiseLoop3` |
| Isoline Simple | contours | **smoothness of the slope matters**; major and minor lines; palette seam under a contour |
| Apollonian | fractal-lace | **shadows that fade with the caster's distance**; slicing 3D for 2D; light the wall, not the lines |
| Starry Planes | zoom-conveyor, flight-tunnel | **plane stacks instead of marching**; exact path derivatives; anti-moiré bias; fades at both ends |
| Saturday | feedback-trail, studio-object | **feedback through a soft threshold** (`fbSoftGate`); projected feedback; backstep march |
| Just a Cube | studio-object, glow-xray | **glow from the minimum distance**; rim-bright soft box; dark mirror; one colour constant |
| Plasma Globe | plasma-electric | **a bolt from a line**; triangle crackle; max not sum; fake glass; rotate the ray, not the object |
| Flame | glow-xray, plasma-electric | **brightness from step count**; overdrive as blackbody; extrapolating mix |
| Alien Core | glow-xray | **the glow is the step count**; huge smooth-min radius; radial-masked deformation |
| Starship | neon-line | **a lopsided distance is a trail** (`glowComet`); exponential flicker; square then tanh |
| Satisfying | kaleido-rings | **cell id, then everything from the id**; phase lag makes the wave; arc-length-correct caps |
| Discoteq | neon-line | **detune is the magic**; pinned ends; defocus toward the edges |
| Sincos 3D | glow-xray | **never let the step grow back** (running minimum); colour by subtraction |
| Blue Red Shiny | flight-tunnel, glow-xray | **glow inside the distance function**; carve, don't build; reflection as a multiplier |
| Hex Glitch | glitch-transition, hex-neon, finish | **wavelength, shutter time and sub-pixel are one random number**; XOR everything; constant pen width; anticipation |
| Pretty Hip | hex-neon (square) | **put every cut inside a full or empty frame**; delay by cell |
| Humanimation | dancer, contours | **motion is the character**; delay lines; three grades of joining; complementary room light |
| Cube Lines | glass | **exact maths, no marching**; interior mapping; band-limited spectral lines; discriminant outlines |
| HAL 4000 | slice-wireframe, zoom-conveyor | **slices instead of surfaces**; max not add; one scalar, a whole palette; the match cut |
| Inercia | pegboard, studio-object | **the pegboard march**; one hash, three dice; silkscreen not sculpture; no ambient |
| Data Warehouse | hex-neon | **a cube is three shades**; slide-by-height studs; staggered choreography |
| Hexagone | hex-neon, zoom-conveyor | **three layers on a conveyor belt**; size-coupled spin; a physical event with a graphic consequence |
| Heartfelt | rain-on-glass | **blur is free** (mip fog); water is a height map; stick-slip; signed lightning |
| Rhodium | studio-object, glass | **blur as error concealment**; alpha carries a message; reverse-march translucency; sunflower bokeh |
| Marble | glass | **glass is invisible without something behind it**; the discriminant's three jobs; low IOR on purpose |
| Warping | warp-painting | study-only: learn **intermediate layers are the palette** from NP 8 |
| Creation Stone | glass, studio-object | **curvature is the polishing wheel**; G-buffer split; blurred-mip normal distortion |
| RM Experiment 23 | pegboard (pattern bank) | **one pattern stamps and cuts**; light inside the object; direction-only god rays |
| Sphere Intersect | fractal-lace | **analytic where possible, procedural where it shows**; Kaliset texture factory; matcap mapping |
| Oscillo Donut | scope-crt, neon-line | **the sound is the picture**; dwell brightness; Lorentzian beam; tanh's three jobs |
| Audio Eclipse | audio-ring | **hide the singularity behind the occluder**; 1/d is the look; gain from the sum |

---

## 20. Tensions for Daniel's gate

The atlas does not decide taste. These are the places where the loved shaders, the house rules and Daniel's own
rulings pull in different directions; each needs his call, ideally with renders side by side.

1. **Black versus tinted dark.** The shader-craft ceiling says black stays black (no ambient, no floor wash); several
   loved shaders sit on a very dark tinted ground (violet, navy, a warm floor). Proposal: a `ground` knob in `finish`
   (a tint at a few percent of a stop), off by default for the cockpit, a choice for the media suite.
2. **Which display transform per surface.** CP 5.10 recommends tanh for glow fields and AgX or PBR Neutral for lit 3D.
   The piano uses three.js Neutral; Gyre, Wind and the chord tree use ACES. Moving any surface's curve moves pixels
   on approved looks.
3. **The hash swap.** Replacing the sine hash with PCG changes every noise pattern it feeds. The legacy twin keeps
   today's pixels; the upgrade per surface is his call, with before and after.
4. **HSV versus OKLCH for hue rotation.** The house rule says hue rotation is perceptual "HSV"; the research says
   OKLCH is the honest form. Same gate, same method.
5. **Glow versus glass** (arc-daniel-voice tension 1): glass for bodies, glow for lines, as separate composable
   groups; he swapped them once and restored the glow.
6. **Spectacle as a global dial**, not baked into groups: each group exposes intensity; a house-wide "spectacle" scales
   them together (his ruling R5: Full by default, Tasteful and Off one click away).
7. **Sum versus max** as the default combine for each glow group (craft secret 6).
