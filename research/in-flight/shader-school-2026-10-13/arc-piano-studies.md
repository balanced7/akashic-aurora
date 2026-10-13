# Arc census: the piano study pages and their shared pieces

Reader: Vandor (claude seat), one of seven readers, 2026-10-13 night.
Task: map the piano study pages so the house can build ONE shared module system
("tweak one module and have everything update", Daniel, tonight).

## The short version

The piano studies already contain about **a dozen reusable primitives that have been written
two to five times each**, in slightly different dialects. The best version of almost every
primitive already exists somewhere in the house; it just lives inside one page. The four
strongest shared-module precedents are also already here: the instrument catalogue
(`piano/instruments/catalog.js`), the injected shader-chunk API in `gyre-light-rays.mjs`,
the renderer-free `lib/flow/` toolkit, and the scheme host contract in `piano-next.js`.

Three landmines must be defused before anything is unified:

1. **`damp()` exists with two different argument orders.** `crystal-performance.mjs:2` is
   `damp(from, to, dt, tau)`; `piano.js:292`, `piano-lab-vfx.js:271`, `glass-piano.js:734`,
   `schemes/neon-trails.js:25` and `schemes/harmonic-wave.js:136` are `damp(current, target, tau, dt)`.
   Both `dt` and `tau` are small positive numbers, so a swapped call does not crash; it just
   smooths at the wrong rate. A unified helper must use named arguments.
2. **Motion equations are hand-copied between JavaScript and GLSL** (the shader language) and no
   test compares the two copies. Gyre's path lives in `gyre-motion.mjs:42-64` and again in
   `piano-gyre.js:91-111`; flight re-derives it a third time in `gyre-flight-motion.mjs:21-37`.
   Moonwater's CPU copy has already drifted from its GPU copy (details in the landmine section).
3. **"4K" means two different things.** Gyre and Wind use "4K fit" (aspect preserved inside
   3840 x 2160, `gyre-motion.mjs:77-81`); Crystal and Arbor force an exact 3840 x 2160 buffer
   and letterbox it (`piano-crystal-studies.js:184`, `piano-chord-tree.js:301`).

## Boundary of this read (what I looked at, what I could not see)

Read in full: `piano-gyre.{js,html,css}`, all six `piano/gyre-*` modules,
`piano-crystal-studies.{js,html}`, `piano/crystal-studies.js`, `piano/crystal-performance.mjs`,
`piano/solstice-canopy.js`, `piano/solstice-signals.mjs`, `piano-chord-tree.{js,html}`,
`piano/chord-tree-model.mjs`, `piano-wind.{js,html}`, `piano-wind-tunnel.html`,
`piano/wind-flow.mjs`, `piano/wind-tunnel.mjs`, `piano/wind-tunnel-worker.mjs`,
`piano/moonwater.js`, `piano/gallery-camera.js`, `piano/instruments/{catalog,crystal-study,aether,solstice,nocturne}.js`,
the four design notes (`GYRE.md`, `CRYSTAL-STUDIES.md`, `CHORD-TREE.md`, `WIND.md`),
`lib/flow/README.md`, and `arsenal/VISUAL-QUALITY-BASELINE.md`.

Read in part (sections that carry visual primitives): `piano-lab-vfx.js` lines 267-886 and
1237-1764; `piano-lab-res.js` lines 426-675 and 1993-2192; `piano-next.js` lines 1-13 and
429-677; `piano-lab-instruments.js` lines 1-219; `piano-lab-score.js` lines 1-103;
`play.js` lines 1-199 and 683-1152. `piano-lab-judge-head.js` and `piano-lab-judge-res.js`
were measured by `diff` against their siblings, not read line by line.

Not read: `lib/flow/*.mjs` bodies (trusted to their README), `piano/harmonic-voices.js`,
`piano/spectacle*.js`, `piano/instruments/glass-piano.js` beyond grep hits, the main
`piano.js` beyond grep hits, the CSS files beyond their design tokens. Nothing was rendered
(house rule: no GPU tonight), so every visual claim below is about **code**, not about what
the pixels look like. Anything I inferred rather than read is marked **(inferred)**.

## The family at a glance

| Page | What it is | Render stack | Shaders live in | Presets / state | Measurement and capture | Tests |
| --- | --- | --- | --- | --- | --- | --- |
| **Gyre** `piano-gyre.html` | Kinetic light sculpture: a spinning, tilting, precessing bent arm leaves light trails; plus braid/pendulum worlds, rider camera, lightcraft squadron | three.js r186, no composer, `antialias:true` MSAA, ACES 1.15 (`piano-gyre.js:34-38`), no bloom by design (`GYRE.md:26`) | Inline template strings `piano-gyre.js:81-151`; ray materials `gyre-light-rays.mjs:8-38`; flight `gyre-flight.js:11-26` | URL params + versioned localStorage library `piano.gyre.presets.v1` (`gyre-presets.mjs:5-41`); 7 built-in studies (`gyre-motion.mjs:4-12`); 5 recipes in `arsenal/visual-references/2026-09-21/gyre-recipes.json` | Measure 10 s after 1 s warmup (`piano-gyre.js:345-356`); `canvas.dataset.frames/resources/flight` | `gyre_motion`, `gyre_presets`, `gyre_harmony`, `gyre_flight` |
| **Crystal Studies** `piano-crystal-studies.html` | Three art-directed glass grands (Aether, Solstice, Nocturne) with a playable 88-key action and an LED canopy that explains attack/held/pedal | three.js composer: half-float 4x MSAA target, UnrealBloom, SMAA, OutputPass; Neutral tone map 1.08 (`piano-crystal-studies.js:24-29,79-84`) | `crystal-studies.js:22-73` (ribbons), `:263-287` (dust); `solstice-canopy.js:10-31` (onBeforeCompile LED patch); base instrument `instruments/glass-piano.js` | URL `study`, `canopy`, `resolution` only; `STUDIES` table (`crystal-studies.js:6-19`) | Measure 15 s after 3 s warmup, CPU submit time included (`piano-crystal-studies.js:352-376`) | `piano_crystal_performance`, `piano_solstice_signals` |
| **Arbor** `piano-chord-tree.html` | A chord built as a 3D tree: root = trunk hue, each chord tone a labelled limb | Same composer recipe as Crystal (`piano-chord-tree.js:58-63`), ACES 1.08 | Material patches only: morph (`:73-79`), leaf wind (`:182-183`) | URL `root, quality, seventh, ext, sharp11, resolution` (`:285`) | Measure 10 s after 2 s warmup, CPU mean (`:312,358-371`) | `piano_chord_tree` |
| **Violet Aero** `piano-wind.html` | Violet light streams around a licensed concept car (authored paths) | No composer, `antialias:true`, ACES 1.12, RoomEnvironment (`piano-wind.js:18-29`), no bloom (`WIND.md:43`) | Inline `piano-wind.js:63-129` | URL (all settings) + 3 LOOKS (`wind-flow.mjs:4-8`), "copy link" | Measure 10 s after 1 s (`piano-wind.js:215-220,240`) | `wind_flow` |
| **Wind Tunnel** `piano-wind-tunnel.html` | Same page script in fluid mode (`body data-flow="fluid"`): a real 3D grid solver in a Worker | As Aero; solver in `wind-tunnel-worker.mjs` over `lib/flow/` | As Aero + `uSignal` speed colouring (`piano-wind.js:95,126`) | URL `yaw`, `colour`; FlowClip takes in IndexedDB + `.flowclip` files (`lib/flow/README.md:93-139`) | Measure + solver diagnostics in report (`piano-wind.js:217`) | `fluid_primitives`, `flow_clip` |
| **Moonwater** `piano/moonwater.js` | Not a page: a theme inside the main piano's Spectacle (`spectacle.js:5,84`) — lake reflection, fog slices, sky, voice strands, fifth-circle inlays | Lives in piano.js's composer; three `Reflector` | All inline, `moonwater.js:6-26,50-229` | Driven by piano settings (`theme`, `labels`, `intensity`, `quality`) (`:256-305`) | `stats()` (`:323-325`) | `piano_harmonic_voices` (tracker only) |
| **Piano (next)** `piano-next.html` | Frozen 2026-09-13 fork of piano.js that introduced the scheme host | Composer: MSAA 4 half-float, bloom, Output | Schemes in `piano/schemes/*.js` | localStorage scheme id | MediaRecorder REC (canvas only, `piano-next.js:7-9`) | THEORY block extracted by node tests (inferred from the marker at `:22`) |
| **Lab: VFX** `piano-lab-vfx.html` | Frozen fork with the five-tier "rarity" spectacle (rings, rail pulses, fountains, shafts, aurora, gold foil) | piano.js composer | `piano-lab-vfx.js:570-677` (trails+shimmer), `:1262-1541` (FX) | `?fx=auto` | REC; `window.__piano` | none found |
| **Lab: Resolution** `piano-lab-res.html` (+ `judge-res`, 7-line diff) | Frozen fork testing supersampling, area downsample, bloom at framing size, AA pass swaps | Composer + `FramingBloomPass` + `DownsamplePass` (`piano-lab-res.js:487-587`) | `:462-557` | `?scale ?msaa ?filter ?fixed` | `window.__piano.lab` sim/freeze/seed hooks (`:2144-2192`) | none found |
| **Lab: Judge head** `piano-lab-judge-head.html` | Frozen fork, baseline for A/B judging (inferred from name; 578 lines differ from lab-vfx) | as above | as above | | | none found |
| **Lab: Instruments** `piano-lab-instruments.html` | Mounts any catalogued instrument on a stage that mirrors piano.js | Composer: MSAA 4, bloom (0.45, 0, 0.9), Output (`piano-lab-instruments.js:124-129`) | none of its own | `?id` from catalogue | `window.__lab` | `piano_instrument_catalog_parity` |
| **Lab: Score** `piano-lab-score.html` | 2D canvas engraved score band; GPU only for texture-upload benchmarks | Canvas 2D | none | event files | `window.scoreLab`, percentile bench (`piano-lab-score.js:47`) | `score_lab` |
| **Play** `play.html` | MilkDrop-style instrument: GLSL fragment presets, audio features, video, feedback | Raw WebGL2, one context, per-preset ping-pong framebuffer pair, crossfade blit (`play.js:11-12,685-767,165-190`) | `arsenal/web/presets/*.frag` with a `//!` JSON header (`presets/aurora-ribbons.frag:2`), validated by `arsenal/presets.py` | Server `/api/presets`, 8 knobs `u_k1..u_k8` per preset (`play.js:1016`) | Take ledger events, `window.__play` | Python suites (not enumerated) |

## The primitives, grouped by category

Each entry: what it does in plain words (with the maths where it helps), where it lives, how
many copies exist, a hardware analogy, and which corpus shaders could teach it at a higher
level. Corpus pointers are by **title only** (I did not read their code tonight) and point into
`state/arsenal/shaders/corpus/shaders/<id>/`; their licences are mostly CC BY-NC-SA, so they are
study material, never paste material.

### A. Time and motion

**A1. Exponential damping (a "low-pass filter").** Move a value toward a target so that the
remaining gap shrinks by a factor of `exp(-dt/tau)` each frame. It is frame-rate independent:
two 8 ms frames give exactly the same result as one 16 ms frame. Hardware analogy: an RC
low-pass filter, with `tau` as the RC time constant.
Copies: `crystal-performance.mjs:2`, `piano.js:292`, `piano-lab-vfx.js:271`,
`glass-piano.js:734`, `neon-trails.js:25`, `harmonic-wave.js:136`, plus inline forms
`piano-gyre.js:341` (rate 1.7/s), `piano-chord-tree.js:336` (7/s), `gyre-flight.js:39,59`
(3/s, 5/s), `moonwater.js:261` (tau 3 s), `piano-crystal-studies.js:332` (tau 1.1 s).
**Two argument orders** (see landmine 1). An asymmetric variant (fast attack, slow release:
pick `tau` by whether the target is above or below) recurs at `crystal-studies.js:307`,
`solstice-signals.mjs:32`, `piano-lab-vfx.js:823`, `piano-lab-res.js:2036`.

**A2. Easing curves.** Smoothstep `3x² − 2x³` (`wind-flow.mjs:10`, `piano-lab-vfx.js:1298`,
`piano-chord-tree.js:334`, `play.js:183`) and the quintic `6x⁵ − 15x⁴ + 10x³`
(`gyre-flight-motion.mjs:13`), which has zero acceleration at both ends.

**A3. Rise-hold-fall bump.** `fxBump(age, rise, hold, fall)` (`piano-lab-vfx.js:1299-1304`):
an attack/sustain/release envelope for one-shot effects. Analogy: a synthesizer envelope
generator. Only one copy; deserves to be shared.

**A4. The musical light envelope ("struck string").** Brightness `s` seconds after a strike is
`(1 + 0.7·e^(−s/0.22)) · (0.5 + 0.5·e^(−s/6))`, scaled by velocity `0.35 + 0.65·v^0.8`, times
1.45 while finger and pedal are both down, 0.8 when only the pedal holds it, with a two-speed
release (`piano-lab-vfx.js:542-550`). Daniel set the rule on 2026-09-13: brightest with finger
and pedal together, still lit under pedal alone, velocity always counts (`:535-536`). The
constants live once in JavaScript and are injected into GLSL as `#define`s through `glslF`
(`:551,572-576`), which is **the house's best existing answer to the CPU/GPU twin problem**:
one source of truth compiled into two languages, like a shared C header.

**A5. Rate limiting with tokens.** The rarity spectacle refills "tokens" per tier (Rare 3 per
10 s, Epic 2 per 45 s, Legendary 1 per 180 s) and spends one per firing
(`piano-lab-vfx.js:1668,1725-1730`). Analogy: a network QoS token bucket. Keeps fireworks rare.

### B. Paths and kinematics

**B1. Rotation hierarchy (spin → tilt → precession).** A point on the arm is rotated about Y
by `spin·t`, then about Z by `tilt + wobble·sin(2π·0.19·t)`, then about world Y by
`precession·t` (`gyre-motion.mjs:29-40`; the GLSL twin `orient()` at `piano-gyre.js:90`; the
visible rods use the same order through nested groups, `piano-gyre.js:50-51,322`). Analogy:
a gyroscope in a gimbal. Tested for invariants (`tests/gyre_motion.test.mjs:5-48`).

**B2. Closed-form ("analytic") emitter paths.** Every light position is a pure function of
time: the L-arm (`gyre-motion.mjs:13-18`), a three-strand torus braid
`R = 1 + reach/2 + r·cos b`, `(R cos a, r sin b, R sin a)` (`:48-52`), and a rosette
`R·(0.72 cos a + 0.28 cos(k a))` (`:54-57`). Because the path is a formula, the trail never
needs to be stored (see C1). Corpus teacher for parametric flowers/knots: none obvious by title.

**B3. Rigid rider camera.** Position, target and up are all pushed through the same rotation
(`gyre-motion.mjs:72-76`), so the bent leg stays fixed in view.

**B4. Parallel-transport frames on a closed rail.** Flight builds a rail from the trail
history, closes it with a Hermite curve that matches tangents at both ends
(`gyre-flight-motion.mjs:40-41`), carries a "right" vector along by minimal rotation
(`transport`, `:12`, `:46-48`), then spreads the leftover twist evenly over the lap so the
seam does not snap (`:49-50`). Arc-length lookup by binary search spaces the craft (`:53-58`).
This is the professional way to orient things along a curve. Arbor's tubes use Frenet frames
instead (`piano-chord-tree.js:86`), which can flip at inflection points **(inferred, not observed)**.

**B5. Smooth maximum for obstacle clearance.** Stream radius
`½·(a + b + √((a − b)² + 0.012))` stays outside both the seed radius and the body envelope
without a kink (`wind-flow.mjs:49`). Small, reusable, one copy.

**B6. Conservative envelope of a mesh.** Bin vertices along the car's length, take the max
height and width per bin, dilate with a ±6-bin max filter, then smooth with a triangle kernel
(`wind-flow.mjs:21-33`). Analogy: a guard band.

**B7. Formation choreography.** Arrowhead/fan/file/helix offsets, blended on a 40-second
cycle with a quintic ease, plus a periodic "break and regroup" (`gyre-flight-motion.mjs:61-68`).

### C. Light history (how a trail remembers the past)

Five different answers exist. They are the heart of the "afterimage" look and the most
valuable thing to name and share.

| Primitive | How it works | Where | Cost profile | Analogy |
| --- | --- | --- | --- | --- |
| **C1 Analytic history** | Each trail vertex stores only `(age, light id)`; the vertex shader evaluates the path at `t = now − age·memory` | `piano-gyre.js:105-111,133,152-163` | Zero CPU per frame; needs a closed-form path | Recompute instead of cache |
| **C2 Event-instanced columns** | One instance per note holds start, release and sound-end times; the shader builds the column from the clock | `piano-lab-vfx.js:507-744` (also in piano.js) | CPU touches a note 3 times in its life | A scoreboard of in-flight instructions |
| **C3 History texture** | Pedal level written into a 512-sample ring texture at 60 Hz; the shader asks "was the pedal down when this stretch left the key?" | `piano-lab-vfx.js:520-527,623-626`, writer `piano-lab-res.js:2021-2030` | One texel per frame | A trace buffer |
| **C4 CPU ring buffer** | 96 recent positions per engine, written at up to 45 Hz | `gyre-flight.js:17-20,47-51` | Rewrites positions every frame | A FIFO |
| **C5 Snapshot morph** | Two path textures (previous, current) and a blend uniform; the GPU interpolates | `piano-wind.js:45-50,77,108-112,133-153` | Upload only when the solver publishes | Double buffering |
| **C6 Feedback** | Each preset reads its own previous frame (`u_prev`) from a ping-pong framebuffer pair | `play.js:11-12,685-767` | One full-screen pass per frame | Front/back buffer swap |

Two rules the house already discovered here and should keep: pulse and colour are evaluated
**at each sample's emission time** so old light does not blink in sync (`GYRE.md:12`,
`piano-gyre.js:113`), and **displacement is exactly zero at the live emitter** and grows with
age (`gyre-motion.mjs:65-71`, tested at `tests/gyre_motion.test.mjs:77`).

**C7. Tail finishes.** Fade, flicker (value noise on stamp time, limited to old samples), and
dissolve (a noise threshold that rises with age, with a glowing edge
`exp(−((grain − threshold)·18)²)`) (`piano-gyre.js:115-130`). Shared by every Gyre material.

**C8. Light budget.** Old light (released columns past 0.6 s) may add up to 1.2 screen-heights
of full-brightness column; beyond that it is scaled down, fast to dim and slow to recover
(`piano-lab-vfx.js:544,719-737`; `piano-lab-res.js:2031-2036`). Keeps a long pedalled passage
from turning into a white wall. Analogy: a power limiter.

### D. Drawing thin light (strips, profiles, particles)

**D1. Screen-space strip extrusion.** To draw a ribbon of constant pixel width: project this
point and a point slightly ahead, take the screen-space direction between them, rotate it 90°,
and push the vertex sideways by `side · width · 2 / resolution · w`. Clamp to the near plane
(`z ≤ −0.08`) and fade near the camera (`smoothstep(.12,.5,−z)`).
**Four copies, nearly character-for-character:** `piano-gyre.js:133`,
`gyre-light-rays.mjs:10` (`projectRay`), `gyre-flight.js:23`, `piano-wind.js:76-83`.
Moonwater uses a cheaper view-space offset instead (`moonwater.js:183`).
Corpus teacher: `4slGz4` "Demo - Volumetric Lines" (iq) for the analytic alternative.

**D2. Two-Gaussian light profile.** Brightness across a strip
`exp(−s²·a) + k·exp(−s²·b)` with a narrow core and a wide halo. Copies with different
constants: `piano-gyre.js:138` (32 / 4 / 0.18), `piano-wind.js:91` (32 / 4 / 0.25),
`gyre-flight.js:24` (24 / 3 / 0.18), `gyre-light-rays.mjs:14` (38 / 5 / 0.12),
`moonwater.js:175` (210 / 14 / 0.10); round sprites use the same idea radially:
`piano-gyre.js:148`, `piano-wind.js:127`. One function with named parameters
(core sharpness, halo width, halo share) covers all of them.

**D3. Strip index-buffer builder.** "N strands × M samples × 2 sides → two triangles per step."
Four copies: `piano-gyre.js:152-163`, `gyre-light-rays.mjs:39-49`, `gyre-flight.js:17-20`,
`piano-wind.js:51-62`; `crystal-studies.js:75-90` is a fifth with UVs.

**D4. Particles: two schools.** Hardware point sprites with clamped size (Gyre sparks
`piano-gyre.js:143`, Wind sparks `piano-wind.js:114`, lab sparks `piano-lab-vfx.js:773`,
Moonwater fireflies `moonwater.js:200`) versus instanced quads, which the Crystal code calls a
rule: "Instanced quads, never hardware point sprites: stable soft coverage at any device pixel
ratio" (`crystal-studies.js:256-262`). The lab found the middle path: clamp a sprite to at least
2.5 px but scale its alpha by `min(1, px²/6.25)` so a tiny spark keeps its energy instead of
flickering (`piano-lab-vfx.js:1413-1416`). The house needs one policy.

**D5. Emission-time stamping (no swimming particles).** Fireflies are placed at fixed
timestamps `floor(time·rate − phase)` rather than a grid of ages that slides every frame
(`gyre-light-rays.mjs:25`; rationale `GYRE.md:33-34`). Each firefly therefore keeps its
identity until it dies. Corpus teacher: `WfcGWj` "Trailing the Twinkling Tunnel" (CC0).

**D6. Ballistic fountain with drag.** Displacement `v·(1 − e^(−0.9t))/0.9 − 4.2·t²` gives a
spray that slows and falls (`piano-lab-vfx.js:1409-1410`). Allocation is a ring of 2000 slots.

### E. Surfaces, geometry and materials

**E1. Thick parametric shell.** Give it any `surface(u, v) → xyz`; it offsets both faces along
the numerical normal and stitches the four edges (`crystal-studies.js:93-113`). Already passed
as a function into the Solstice canopy (`solstice-canopy.js:37,66`) — a ready-made shared part.

**E2. Tapered tube from a curve, with GPU morph targets.** Tubes keep a fixed vertex count; a
shape change writes the new positions into `goalPosition`/`goalNormal` attributes and a single
uniform `uShape` slides from old to new in the vertex shader (`piano-chord-tree.js:69-109,196-202`).
Analogy: double-buffered vertex data.

**E3. Material patching (`onBeforeCompile`).** Inject a few lines into a standard physically
based material instead of writing a whole shader: Solstice LED cells in an opal diffuser
(`solstice-canopy.js:10-33`), Arbor's morph and leaf wind (`piano-chord-tree.js:73-79,182-183`),
and a string-search patch that upgrades the glass piano's string edges to derivative-aware
antialiasing (`crystal-studies.js:214-220`). Always paired with a `customProgramCacheKey`.
The string-replace patch is fragile: if `glass-piano.js` changes the exact text
`smoothstep(1.0, 0.86, d)`, the replace silently does nothing **(inferred risk)**.

**E4. Physical glass looks.** Transmission, thickness, IOR 1.46, attenuation colour,
iridescence, dispersion, clearcoat (`crystal-studies.js:116-122,198-206`;
`moonwater.js:243-244`). Three studies differ only by a spec row (`crystal-studies.js:6-19`),
which is the right shape for a preset.

**E5. Mesh envelope + grouped static meshes.** Load a GLB, orient by a named part, normalise
length, merge by material (`piano-wind.js:253-283`).

### F. Atmosphere and environment

**F1. Studio environment from soft boxes.** Build a tiny scene of bright rectangles, bake it
with PMREM (a pre-filtered reflection map) and dispose the boxes. Four copies:
`piano-crystal-studies.js:41-56`, `piano-chord-tree.js:47-53`, `piano-lab-vfx.js:408-423`
(also `piano.js:451-465` and `piano-lab-instruments.js:109-122`); Wind uses three.js's
`RoomEnvironment` instead (`piano-wind.js:28-29`).

**F2. Analytic floor pool / halo.** A plane whose fragment shader is a Gaussian disc,
additively blended — fake bounce light without another render (`piano-crystal-studies.js:66-77`,
`piano-gyre.js:169-170`, `piano-wind.js:31-38`).

**F3. Procedural sky.** Moon disc with crater noise, halo, fbm clouds with a lit rim, hashed
star grid (`moonwater.js:50-64`). Corpus teachers: `3l23Rh` "Protean clouds", `XslGRr`
"Clouds", `MdBfzR`/`XtGGRt`/`ttScDc` auroras (ttScDc is MIT).

**F4. Fog as stacked sheets.** Eighteen depth-tested planes sample one continuous 3D fbm
density, lit by the same eight note lamps (`moonwater.js:149-166`). A bounded, cheap volumetric.
Corpus teachers: `tdjBR1` "Volumetric lighting", `4slGWM` "enlightened dark cloud".

**F5. Planar reflection with ripples.** three.js `Reflector` with a custom shader: ripple
texture gradient perturbs the mirror lookup, Fresnel `0.13 + 0.77·(1 − n·v)³`, and the HUD,
labels and listed objects are hidden during the mirror render (`moonwater.js:112-147`).
Corpus teacher: `MdlXz8` "Tileable Water Caustic".

**F6. Heightfield terrain + instanced trees with wind sway.** (`moonwater.js:67-106`).
Corpus teacher: `tdjyzz` "Tree in the wind" (CC BY-SA).

**F7. Aurora curtain.** A folded curtain whose hem is a sum of three sines and whose rays fade
upward (`piano-lab-vfx.js:1483-1509`); Nocturne's ribbons aim at the same image
(`crystal-studies.js:48-52`). Corpus teachers: `ffG3Rc` "Chromatic Aurora Curtains",
`XtGGRt` "Auroras", `MsjfRG` "Aurora Lights".

**F8. Hash and noise.** A sine hash (`piano-gyre.js:118-119`), Dave Hoskins' style fract hash
`hash31` (`moonwater.js:7`) and its 2D sibling in the play blit (`play.js:174-178`), trilinear
value noise and a three-octave fbm (`moonwater.js:8-11`). Sine hashes lose precision at large
arguments on some GPUs **(general knowledge, not observed here)**; one shared noise chunk
should standardise on the fract-hash family.

### G. Colour

**G1. Pitch colour by the circle of fifths — five variants.** Every surface orders the twelve
pitch classes by fifths (`pc·7 mod 12`) so a key's notes form a coherent arc of hue. Variants:
OKLCH at each hue's most colourful lightness, then luminance-equalised toward the palette's
geometric mean so velocity, not note name, decides brightness (`piano-lab-vfx.js:277-353`,
also `piano.js`); a simplified OKLCH copy (`piano-lab-instruments.js:58-83`); HSL hue
`(38 + 30·fifths) mod 360` (`chord-tree-model.mjs:7`); a two-colour lerp by fifth index
(`piano-crystal-studies.js:94-97`); HSL per voice (`moonwater.js:266`). The OKLCH version is the
most careful and should be the one shared module.

**G2. Three-stop palettes evaluated per sample.** `mix(mix(A, B, smoothstep(0,.6,h)), C,
smoothstep(.57,1,h))` with `h` drifting by light index and time (`piano-gyre.js:73,113`); the
same formula is repeated on the CPU for the LED heads (`:327`).

**G3. Tone mapping is not agreed.** ACES at 1.15 / 1.12 / 1.08 (Gyre, Wind, Arbor) versus
Neutral at 1.08 / 1.0 (Crystal, piano family). The piano family wrote down why: Neutral keeps
OKLCH hues, ACES pushes neon toward white (`piano-lab-vfx.js:396`).

### H. Music into signals (adapters)

The same input — notes, velocities, pedal — is turned into visual signals in seven ways.
These are the "sensors" of a shared system; each one is small and testable.

| Adapter | Output | Where |
| --- | --- | --- |
| Performance state ("host contract") | `{pressed, sounding, pedal, notes, chord}` with strike serials | `crystal-performance.mjs:4-33`; same shape rebuilt in `piano-lab-instruments.js:194-207` |
| Per-channel MIDI with sustain latching | sounding note list; all-notes-off and reset handled | `gyre-harmony.mjs:11-25` (the only channel-aware one; Crystal's inline handler at `piano-crystal-studies.js:285-307` ignores channels) |
| Harmony shape | `[fullness, closeness, pitch-hue]` in 0..1 | `gyre-harmony.mjs:3-9` |
| 3 × 12 light matrix | attack / held / pedal-only per pitch class, octaves merged by max | `solstice-signals.mjs:8-40` |
| 88-note envelope array | damped per-key level, uploaded as `uNotes[88]` | `crystal-studies.js:304-310` |
| Voice texture | 88 × 3 float texture of voice position, colour, phase | `moonwater.js:34,264-267` |
| Rarity score | chord colour, span, mass, accent, novelty, fatigue, crescendo arc → tier 0-4 | `piano-lab-vfx.js:1674-1728` |

### I. Composition and text

**I1. Protect zones.** Effects multiply their light by a soft super-ellipse mask so nothing
glows over the chord name or the staff (`piano-lab-vfx.js:1251-1285`). Analogy: keep-out zones
on a circuit board. Rule stated at `:1246-1247`.

**I2. Labels.** DOM labels placed by projection with greedy overlap rejection
(`piano-chord-tree.js:315-327`); GPU label quads from a canvas glyph atlas plus leader lines
and a packing routine (`moonwater.js:204-222,276-283`); canvas HUD with fit-to-width font sizing
(`moonwater.js:312-318`); tier banner and a gold-foil sweep shader that uses the label's own
alpha as a mask (`piano-lab-vfx.js:1521-1588`).

**I3. "Recorded means in the canvas."** Everything that must appear in a recording is drawn
into WebGL because MediaRecorder captures only the canvas (`piano-next.js:7-9`).

### J. Post-processing and antialiasing

Three post "profiles" exist, chosen per page on purpose:

1. **Clean:** renderer MSAA, no bloom, no composer (Gyre, Wind). `GYRE.md:26`, `WIND.md:43`.
2. **Bloom + SMAA:** half-float 4x MSAA target → UnrealBloom → SMAA → Output (Crystal, Arbor).
3. **Piano:** half-float 4x MSAA → UnrealBloom (radius 0, threshold 0.9) → Output; the lab adds
   supersampling with an exact-footprint area downsample done in linear light, and bloom kept
   at the framing size so the glow has one shape at any window size
   (`piano-lab-res.js:437-456,487-587`). The comment records the measured choice: 2x
   supersampling + MSAA 4 was closest to a 16-sample reference (`:438-440`).

Shader-level antialiasing worth sharing: derivative-widened rings that keep their energy
(`piano-lab-vfx.js:1330-1333`), `fwidth` edges on ribbons and LED cells
(`crystal-studies.js:63-65`, `solstice-canopy.js:22-23`), and a **static per-pixel dither**
that breaks banding without crawling (`play.js:161-187`).

### K. Cameras

Orbit with damping and limits (every page); follow-the-music span camera with a **lens shift
instead of a tilt** so the keys sit low and the light gets the sky (`piano-next.js:649-677`,
`piano-lab-vfx.js:861-886`); rider (`gyre-motion.mjs:72-76`); chase and pilot with banking and
damped slerp (`gyre-flight.js:53-60`); gallery drift (`gallery-camera.js:18-40`, which is the
extracted form of `piano-crystal-studies.js:316-334`). Aspect fitting appears as a field-of-view
widening `fov = 2·atan(tan(base/2)·max(1, k/aspect))` with three different `k`
(`piano-gyre.js:189` k=1.1, `piano-chord-tree.js:304` k=0.9, `piano-wind.js:201` k=1.35) and as
a distance push `max(1, 1.55/aspect)` (`piano-crystal-studies.js:329`, `gallery-camera.js:28`).

### L. Fluid

`lib/flow/` is a renderer-free toolkit: a staggered (MAC) velocity grid with semi-Lagrangian
transport and preconditioned conjugate-gradient pressure projection, a signed-distance volume
with a column-hull adapter for meshes, RK2 streamline tracing, an artistic wake force, and the
FlowClip recording format (16-bit quantised, checksummed) (`lib/flow/README.md:8-30,93-139`).
It is the house's model of a well-made shared module: no DOM, no three.js, documented
contract, honest limits. Corpus teachers: `MdSczK` "Multistep Fluid Simulation", `tsKXR3`
"Multiscale MIP Fluid", `XddSRX` "Suture Fluid" (MIT), `MdGBWG` "Global Wind Circulation"
(CC BY-SA).

## Page shell and UI: one anatomy, written four times

Every study page has the same skeleton:

- **Header:** a back-link brand, an edition label, Pause render, Fullscreen
  (`piano-gyre.html:10`, `piano-chord-tree.html:12`, `piano-wind.html:6`; Crystal has no
  pause, `piano-crystal-studies.html:16`).
- **Control panel:** eyebrow + large serif title + sections of sliders whose `<output>` shows a
  formatted value (`piano-gyre.html:13-72`, `piano-chord-tree.html:15-24`, `piano-wind.html:15-24`).
- **Scene overlays:** caption, "DRAG TO ORBIT" hint, loading and error boxes.
- **Footer:** resolution select, live status (`W × H · fps · AA`), Measure button and report.

The lifecycle code is copied per page: error overlay (`piano-gyre.js:14-16`,
`piano-crystal-studies.js:16-21`, `piano-chord-tree.js:14-16`, `piano-wind.js:16-17`);
fullscreen (`piano-gyre.js:309`, `piano-crystal-studies.js:339-342`, `piano-chord-tree.js:297`,
`piano-wind.js:242`); pause with true rAF cancellation (`piano-gyre.js:297-302`,
`piano-chord-tree.js:233-251`, `piano-wind.js:224-229`; Crystal keeps scheduling frames,
`piano-crystal-studies.js:377-379`); device-pixel-ratio change detection per frame
(`piano-gyre.js:339`, `piano-wind.js:213`) or by a one-second poll
(`piano-crystal-studies.js:197-198`, `piano-chord-tree.js:307-308`); and the measurement loop
with four different warmups and windows (1+10 s, 3+15 s, 2+10 s, 1+10 s).

**Parameters are described in three places at once.** Gyre's spin range is in the HTML
(`piano-gyre.html:29`), in the preset validator (`gyre-presets.mjs:6`), and URL parsing reads
the HTML's own `min`/`max` back (`piano-gyre.js:19-21`). Value formatting is one long chain of
conditions per slider id (`piano-gyre.js:194`). Which sliders force a fresh exposure is a
hand-kept list (`:282`); Wind keeps its own "rebuild only for clearance, wake and density" list
(`piano-wind.js:230-231`). A single parameter schema (id, label, range, step, unit, group,
uniform name, and **cost class**: uniform / buffer rewrite / geometry rebuild / reset) would
generate the slider, the formatter, the URL codec and the validator.

**Five preset systems:** Gyre's versioned local library (best guarantees: validates before
applying, never overwrites on failure, additive versioning, `gyre-presets.mjs:1,10-41`);
Wind's LOOKS + copied link; Crystal's study table; Play's server preset list with a `//!` JSON
header declaring eight named knobs (`presets/aurora-ribbons.frag:2`, `play.js:771-810`); and
the main piano's looks registry/store (`piano.js:3650`). The Play header is the closest thing
the house has to a portable shader-preset schema.

**Design tokens differ per page:** Gyre `--accent:#a4eddb` with DM Sans + Instrument Serif
(`piano-gyre.css:1-2`); Crystal per-study `--accent` set from JS (`piano-crystal-studies.js:161`);
Arbor `--hue` driven by the chord root (`piano-chord-tree.css` root, `piano-chord-tree.js:264`);
Wind hard-codes violet with Inter (`piano-wind.css`); Play has a full light/dark token set with
Archivo and JetBrains Mono (`play.css`). Arbor's "accent follows the content" idea is worth
keeping as a token rule.

## Duplication ledger

1. Screen-space strip extrusion — 4 copies (D1).
2. Two-Gaussian light profile — 7 copies with different constants (D2).
3. Strip index-buffer builder — 5 copies (D3).
4. Exponential damping — 6 named functions in 2 argument orders + 6 inline forms (A1).
5. Studio soft-box environment — 5 copies (F1).
6. Pitch-by-fifths colour — 5 variants (G1).
7. Key geometry `KEY` / `BLACK_CENTER` / `keyX` — `piano.js:425-431`,
   `piano-crystal-studies.js:86-91`, `piano-lab-vfx.js:378-388` (+ res, judge, next),
   `piano-lab-instruments.js:45-55`; `glass-piano.js:1927` has a different linear fallback if the
   host does not pass `keyX`.
8. Frame statistics — `frameStats` (`crystal-performance.mjs:35-43`) shared by four pages, but
   `piano-lab-res.js:2062-2071` and `piano-lab-score.js:47` compute their own percentiles; the
   GPU-name lookup via `WEBGL_debug_renderer_info` is copied five times.
9. Resolution sizing — `bufferSize` (`gyre-motion.mjs:77-81`, imported by Wind from a
   Gyre-specific module, `piano-wind.js:7`) versus Crystal's and Arbor's own resize functions.
10. Page lifecycle (error, fullscreen, pause, visibility, reduced motion, DPR, measure) — 4 copies.
11. The demo progression in D♭ — `piano-crystal-studies.js:209-214` and
    `piano-lab-instruments.js:87-93`, with different voicings.
12. MIDI input — `gyre-harmony.mjs:11-25`, `piano-crystal-studies.js:285-307`, each lab fork's
    MIDI section, `play.js:2015+`.
13. CPU/GPU twin equations — Gyre path (JS `gyre-motion.mjs:42-71`, GLSL `piano-gyre.js:91-111`,
    flight JS again `gyre-flight-motion.mjs:21-37`); Gyre LED colour (`piano-gyre.js:113` vs
    `:327-330`); Moonwater voice path (`moonwater.js:17-25` vs `:252-254`).
14. **Four near-complete forks of the main piano** (`piano-next.js`, `piano-lab-vfx.js`,
    `piano-lab-res.js`, `piano-lab-judge-head.js`, ~1,900-2,450 lines each) plus
    `piano-lab-judge-res.js`, which differs from `piano-lab-res.js` by 7 lines
    (`piano-lab-res.js:614-616`). Their experiments either landed in `piano.js` under other
    names (light budget, pedal history, OKLCH colour: grep counts) or stayed only in the fork
    (rarity spectacle, supersample + area downsample, scheme host by that name). They are
    frozen snapshots; keep them until Daniel decides, since the house rule is to ask before
    deleting functionality.

## Landmines (things that would bite a unification)

1. **`damp` argument order** — see the top. Fix by a named-argument helper
   (`damp({from, to, dt, tau})`) and leave the old exports as thin adapters.
2. **CPU/GPU drift is untested.** No test in `tests/` mentions GLSL for Gyre (the only GLSL-text
   test is `piano_light_vandor.test.mjs:595-598`). The baseline admits the twins are kept in
   sync by hand (`VISUAL-QUALITY-BASELINE.md:29`).
3. **Moonwater's CPU twin has already drifted.** The GPU strand adds a ripple-wind term
   `wind·2.5` to the bend and compresses the sideways displacement into the space available
   (`moonwater.js:20-24`); the CPU copy used to place labels and the eight note lamps omits
   both (`:252-254`, used at `:272,287`). Labels and lamps can therefore sit slightly off their
   drawn strands when the water is rippling. **Effect size not measured (no render tonight).**
4. **Two meanings of 4K** (top of report). Pick one name per behaviour: "4K fit" and "exact 4K".
5. **Point sprites vs quads** has a stated rule in one file and the opposite practice in four.
6. **Crystal has no true pause**; the other three study pages do (baseline requires "true
   pause", `VISUAL-QUALITY-BASELINE.md:35,75`).
7. **Fragile string patch** on `glass-piano.js` shader text (`crystal-studies.js:217-219`).
8. **Tone mapping differs** between surfaces; a shared colour module has to carry the tone
   mapper as part of the look, or colours will shift when a primitive moves between pages.
9. **Licence on the corpus:** `MlKSWm` "Sparks drifting" is all-rights-reserved; study the
   idea only. Everything else listed above is CC BY-NC-SA unless marked.

## Seams: where a shared module system can be cut in cleanly

Ordered from least to most disruptive. Every cut keeps the old import path working through a
re-export shim, so no page has to change on day one.

1. **`lib/core/`** — `damp` (named args), easing, `bump`, token bucket, seeded random
   (`piano-lab-res.js:2171-2179`, `moonwater.js:41`). Source: A1-A5.
2. **`lib/perf/`** — `frameStats` (move from `crystal-performance.mjs:35-43`, re-export there),
   one measurement runner with configurable warmup/window, GPU name lookup, report shape.
3. **`lib/render/stage.mjs`** — `bufferSize` (from `gyre-motion.mjs:77-81`), DPR watch,
   pause/visibility/reduced-motion, fullscreen, error overlay, shader-error hook. Gyre's loop
   (`piano-gyre.js:297-358`) is the most complete reference.
4. **`lib/render/studio-env.mjs` and `lib/render/post.mjs`** — the soft-box PMREM (F1) and the
   three post profiles (J), selected by name. Bring `FramingBloomPass` and `DownsamplePass`
   (`piano-lab-res.js:487-587`) in as optional pieces.
5. **`lib/glsl/` chunks** — strip extrusion, two-Gaussian profile, tail finish, hash/noise/fbm,
   fwidth helpers, OKLCH, protect masks, palette mix. The injection API already exists:
   `createRayMeshes(THREE, {common, tailFragment, uniforms, ...})` (`gyre-light-rays.mjs:6`,
   called at `piano-gyre.js:168`). Pin "defined once" with a text test modelled on
   `piano_light_vandor.test.mjs:595-598`.
6. **`lib/geometry/`** — strip builder (D3), thick shell (E1, already passed as a function),
   tapered tube with morph targets (E2).
7. **`lib/music/`** — performance state (`crystal-performance.mjs:4-33`), channel-aware MIDI
   (`gyre-harmony.mjs:11-25`), and the signal adapters of section H as separate small modules.
8. **`lib/color/pitch.mjs`** — the OKLCH luminance-equalised fifths colour from
   `piano-lab-vfx.js:277-353`, with the others re-expressed as options.
9. **`lib/params/`** — one parameter schema that generates sliders, formatting, URL codec and
   validation, plus Gyre's library guarantees (`gyre-presets.mjs`). Adopt Play's `//!` header as
   the on-disk format for shader presets.
10. **Module contracts for whole visuals** — the scheme contract
    (`noteOn, noteRelease, noteEnd, pedal, update, resize, setActive, dispose`,
    `piano-next.js:460,601-608`) and the instrument contract (`create(ctx)` with `views.hero`,
    `piano/instruments/crystal-study.js:4-23`) let a study run inside the main piano. Crystal
    already does this; Gyre, Arbor and Aero could become schemes or instruments the same way,
    registered in the catalogue that already enforces "one list, three readers"
    (`piano/instruments/catalog.js:1-35`).
11. **One-source constants for CPU and GPU** — generalise the `#define` injection of
    `piano-lab-vfx.js:551,572-576` so path constants are written once. For whole functions, a
    tiny shared expression set that emits both JavaScript and GLSL is possible **(inferred
    feasibility, not prototyped)**.

## Binding rules found (with sources)

- Daniel's baseline: fidelity, beauty, fluidity, elegance, performance, trust; native pixels,
  60 fps floor, never silently lower resolution; true pause; explicit save vs update
  (`arsenal/VISUAL-QUALITY-BASELINE.md:4-17,35-37`).
- Inspect the actual render in motion before calling visual work done; preserve the user's
  live view and saved work (`arsenal/web/AGENTS.md:1-15`).
- Gyre: designed motion, not physics; geometry allocated once; no full-screen bloom
  (`GYRE.md:10,26`). Wind and the flow toolkit: authored or bounded, never claimed as CFD
  (`WIND.md:34-36`, `lib/flow/README.md:17,26,64-79,91`).
- Spectacle rules: every effect a pure function of the clock; nothing flashes the whole frame;
  effect light avoids the chord name and staff; bodies stay under the bloom threshold
  (`piano-lab-vfx.js:1246-1247`).
- Light model, Daniel 2026-09-13: brightest with finger and pedal; lit under pedal alone;
  velocity always counts (`piano-lab-vfx.js:535-536,641-643`).
- Recordings capture only the canvas, so recorded content is drawn in WebGL (`piano-next.js:7-9`).
- Crystal: instanced quads instead of point sprites (`crystal-studies.js:256`).
- Neutral tone mapping preserves OKLCH hues (`piano-lab-vfx.js:396`).
- Dither is static per pixel, never per frame (`play.js:163-164`).
- Adding an instrument is one edit to the catalogue, pinned by a parity test
  (`piano/instruments/catalog.js:26-29`).
- GPU lock: one headless render at a time, bursts under 3 minutes (`arsenal/GPU-LOCK.md:1-25`).
- Media suite ruling (memory, 2026-09-13): no forbidden-tool rules; best, most stable, most
  reliable wins, three.js or any renderer.
- Tonight's house rules: never copy corpus code into tracked files; describe techniques in
  words and maths.

## Suggested first cuts (safe, small, high leverage)

1. Named-argument `damp` in `lib/core/` with both old signatures kept as adapters, plus a test
   that pins equivalence. Defuses landmine 1 before anything else moves.
2. Move `frameStats` and `bufferSize` into neutral modules with re-exports; Wind stops
   importing from Gyre.
3. Extract the strip-extrusion and two-Gaussian chunks into `lib/glsl/`, switch Gyre's ray
   materials first (they already receive chunks by injection), and add the "defined once" pin.
4. Write the parameter schema for Gyre only, generating its sliders and URL codec, and prove
   preset round-trips are unchanged with the existing `gyre_presets` suite.
5. Add a CPU/GPU parity check for Moonwater's label anchor (landmine 3) before deciding whether
   to fix the CPU copy or move labels onto the GPU.
