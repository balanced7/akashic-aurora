# Arc census: the piano visualizer's rendering stack

Reader: one of seven, shader school night, 2026-10-13. Scope: `arsenal/web/piano.js` and the modules it renders
through (glass, lean layer, spectacle and its worlds and voicing, harmony renderer, looks registry and store,
recorder), `arsenal/pianolooks.py`, `piano.html` / `piano.css`, and the specs `PIANO-V2-SPEC.md`, `SPECTACLE.md`,
`SPECTACLE-DESIGN.md`, `VISUAL-QUALITY-BASELINE.md`, `ENVIRONMENT-PASS.md`, `HARMONY-MODES.md`.

Method: read-only. Every claim carries a `file:line`. Anything I concluded without reading it directly is marked
**(inferred)**. No corpus code was opened or copied; techniques below are described in words and maths.
Nothing was rendered, served or committed.

---

## 0. The short version (for Daniel)

Think of `piano.js` as one big motherboard with almost everything soldered on: the colour engine, the light model,
the keys, the trails, the sparks, the camera, the text overlay, the recorder and the debug port all live in one
5,480-line file (`arsenal/web/piano.js:8-11` lists its sections). It does have **two proper expansion slots**:
the *Scheme* slot (what draws the notes) and the *Instrument* slot (the body around the keys), each with a written
contract, hot-swapping, and a fuse that blows safely if a card misbehaves (`piano.js:1186-1229`, `1359-1371`).
And it has one big daughterboard bolted on with screws rather than a slot: **Spectacle**, the atmosphere
(worlds, weather, particles, water, harmony diagrams) (`piano/spectacle.js:46-445`).

The best-engineered reusable part in the whole stack is not a shader. It is the **looks registry**
(`piano/looks/registry.js:107-177`): every visual setting described once as data (id, group, label, type, choices,
"blocked while recording", apply order, how to read it, how to set it). That is the seed of "tweak one module and
everything updates". Today only the Studio drawer uses it; the top bar, the Atmosphere panel and Spectacle itself
each keep their own hand-copied lists of the same choices (section 9).

Two finished parts are sitting in the drawer unplugged: a constant-frame-rate WebCodecs MP4 recorder
(`piano/recorder.js`, used only by its test page) and a display-resolution policy (`web/lib/raster-policy.js`, used
by nothing but its test). The page instead records with MediaRecorder plus its own frame pacer, and fixed its
aliasing with a hand-built downsampling "smooth preview" (section 7).

---

## 1. File map

| File | Lines | What it is |
| --- | ---: | --- |
| `arsenal/web/piano.js` | 5480 | The page: theory (pure), colour, framing, key geometry, scene, keys, trails, sparks, key motion, camera, looks host, overlay, notes engine, Claude's hand, glass/lean/pool, MIDI, recording, UI, loop, `window.__piano` |
| `arsenal/web/piano/glass.js` | 318 | Unrecorded 2D canvas over the WebGL one; draws ghost rims and Claude's keys through a projective map. "Pure of the page" (`glass.js:21`) |
| `arsenal/web/piano/harmony-renderer.js` | 219 | Eight live harmony diagrams (Tonnetz, folds, spiral, stained glass, compass, rings, petals, yarn) as a camera-locked 3D layer plus a Canvas2D HUD |
| `arsenal/web/piano/spectacle.js` | 445 | The atmosphere host: themes, quality tiers, GPU particles, threads, veils, curtains, weather, impact rings, halo, material theming, its own settings panel |
| `arsenal/web/piano/spectacle-worlds.js` | 218 | Procedural scenery: ripple wave simulation, sky/galaxy, stars, moon, water, terrain, pines, fog banks, city towers, audio waveform |
| `arsenal/web/piano/spectacle-voicing.js` | 175 | Shared note-path GLSL, glass note labels with screen packing, leaders, voice links, mist, Nashville plaque |
| `arsenal/web/piano/spectacle-motion.js` | 142 | (read for context) the pure gesture model that drives Spectacle: per-key springs, impacts, energy/calm/tension |
| `arsenal/web/piano/moonwater.js` | 327 | (skimmed) the lake world: planar reflection, 3D noise fog, strands, labels |
| `arsenal/web/piano/looks/registry.js` | 383 | Every look setting as a descriptor; validated, ordered, serialized apply with read-back |
| `arsenal/web/piano/looks/store.js` | 293 | Saved looks: starters + server list, offline pending ops, rev/409 replay |
| `arsenal/pianolooks.py` | 219 | Server half: loopback-only GET/PUT, validation, atomic file write |
| `arsenal/web/piano/recorder.js` | 910 | WebCodecs constant-frame-rate MP4 recorder with MediaRecorder fallback. **Not imported by piano.js** |
| `arsenal/web/piano.html` | 225 | Top bar, stage, the three canvases, HUD, three.js r186 import map |
| `arsenal/web/piano.css` | 464 | Chrome styling; tokens copied from First Light |

---

## 2. One frame, in order

`renderFrame()` (`piano.js:4950-5062`) is the single per-frame entry. The loop around it (`piano.js:5074-5086`) runs on
`requestAnimationFrame`, caps itself at 60 fps when "60" refresh mode is chosen or a recording is running
(`piano.js:5080`), and stops when the tab is hidden (`piano.js:5076`, `5087-5091`).

1. **Clock.** `t = clock()`; `dt` clamped to 0..0.1 s (`piano.js:4951-4953`). The clock can be *held* by a test harness
   (`piano.js:676-679`), which is how pixel-identical receipts are made.
2. **Latency bookkeeping** (`piano.js:4954-4959`), catch-up reading after a stall (`4960`).
3. **Musical state.** Demo, cue player, Claude's band transport, hover gate, key tracker, then `currentInfo(t)` (the
   chord reading) (`piano.js:4962-4967`, `2831-2849`).
4. **Lean feed** (`piano.js:4968`), **Claude stage mix** (`4969`, `2996-3022`).
5. **Physics-ish updates.** Key springs and colours (`updateKeys`, `piano.js:980-1080`), floor pool (`3370-3386`),
   camera (`1134-1183`).
6. **Trail/spark uniforms and uploads** (`piano.js:4973-4976`).
7. **Per-key glow targets** from the shared light model, pedal smoothing, and writing the pedal history ring texture
   (`piano.js:4978-5000`).
8. **Light budget**: scan all trail slots, compute how much "old light" is on screen, ease a density uniform
   (`piano.js:5001-5010`).
9. **Stage tint**: background and fog drift 3% toward the mean colour of sounding notes (`piano.js:5011-5016`).
10. **Overlay update** (chord label, numbers, staff, Claude's chip: redraw only on change) (`piano.js:5018`, `2353-2432`).
11. **Spectacle update** (`piano.js:5020`), then **scheme and instrument update** (`piano.js:5021`, `1611-1629`),
    then the **gallery camera** (`piano.js:5022`).
12. **Draw.** `composer.render(dt)` (scene pass, bloom, output pass) (`piano.js:5028`); then the text overlay scene is
    drawn straight on top with `autoClear = false`, so text skips bloom and tone mapping (`piano.js:5030-5032`).
13. **DOM layers that are never recorded**: smooth preview copy (`piano.js:5033`), jam glass (`5034`), lean (`5035`).
14. **Recorder pacing**: request one captured frame per 1/60 s of accumulated time (`piano.js:5036-5043`).
15. **Stats** (fps, p95), REC timer, HUD at 5 Hz (`piano.js:5045-5061`).

**Analogy.** Steps 3-9 are the "simulation clock domain", 12 is the "render clock domain", 13-14 are "scanout and
capture". The house keeps these three domains in one function today; the recorder module was designed to make the
capture domain independent (section 7).

---

## 3. The render stack, layer by layer (back to front)

### 3.1 Renderer and post (the "GPU board settings")
- WebGL renderer with **no context antialiasing** and pixel ratio 1 (`piano.js:441-442`); quality comes from sizing the
  drawing buffer by `renderScale` instead (`piano.js:4363-4364`, `1274-1276`).
- **Tone mapping: Khronos PBR Neutral**, chosen because ACES "would push neon toward white" and damage the OKLCH palette
  (`piano.js:443-446`).
- **Composer**: a half-float render target with **4x MSAA** (`piano.js:474-475`) → scene pass → **UnrealBloom**
  (strength 0.45, radius 0, threshold 0.9; radius 0 "keeps the widest bloom mips light") (`piano.js:477-479`) → output
  pass (`480`). Spectacle overrides bloom every frame while enabled (strength `.42+force*.25+impact*...`, radius
  `.22+calm*.13`, threshold `.94`) and restores it when disabled (`spectacle.js:424`, `61`, `307`).
- **Reflections only environment**: a PMREM-filtered procedural "dark studio" (black box, four emissive strips)
  assigned per material, not as `scene.environment` (`piano.js:452-470`).
- **Fog and background** share one colour so the floor has no horizon (`piano.js:449-450`, `482-485`).

### 3.2 The stage and the instrument
- Lacquer body from rounded boxes with clearcoat physical material (`piano.js:493-513`), felt and a thin rail light.
- Lights: a hemisphere fill, a warm key light, a cool rim light (`piano.js:515-521`), and **three round-robin coloured
  point lights** that follow the newest notes (`piano.js:522-529`, `1081-1087`, decay `1074-1079`).
- **88 keys**: each a pivot group with a rounded-box mesh and its own physical material, plus two flat "ghost frame"
  meshes (a rectangle with a rectangular hole) for hover and hold rims (`piano.js:614-668`). Key x positions follow a
  real action: C-E split into 5 equal slots, F-B into 7 (`piano.js:425-435`).

### 3.3 Classic trails (the signature look)
One instanced quad per note, up to 640 of Daniel's plus 128 for replays (`piano.js:681-684`). The CPU writes only
**start, release and sound-end times** per instance; the vertex shader builds the column from the clock, so a trail
costs nothing per frame on the CPU (`piano.js:670-674`, `747-781`).

### 3.4 Sparks
2,400 points in a ring buffer; ballistic motion is evaluated analytically in the vertex shader from birth time
(`piano.js:909-973`).

### 3.5 Spectacle (atmosphere), when enabled
Sky, stars, moon, water, terrain, trees, fog banks, city towers (`spectacle-worlds.js`), GPU particles, note threads,
three veils, three curtains, weather, impact rings, halo constellation (`spectacle.js`), note glass labels, leaders,
links, mist, Nashville plaque (`spectacle-voicing.js`), the Moonwater lake world (`moonwater.js`), and the harmony
diagrams (`harmony-renderer.js`). Which subset draws depends on theme and chord-view mode (`spectacle.js:426-434`).

### 3.6 Scheme and instrument modules
Loaded by `import()` into the same scene; the classic trails and sparks are hidden while a scheme is active
(`piano.js:1399-1403`).

### 3.7 Text overlay (recorded)
Canvas2D layers uploaded as textures and drawn in a separate orthographic scene after the composer
(`piano.js:1747-1810`, `5030-5032`). Layouts per framing (`piano.js:1777-1786`).

### 3.8 DOM layers (never recorded)
Smooth preview copy (`piano.js:4168-4318`), jam glass (`glass.js`), lean (`piano.js:3071-3336`).

---

## 4. Primitive inventory, grouped by category

This is the "break the primitives down and group them" deliverable for this arc. Each entry: what it is in plain
words, the maths, where it lives, and whether something else in the house does the same thing.

### A. Time and motion

| Primitive | Plain words and maths | Where |
| --- | --- | --- |
| Frame-rate-independent smoothing ("damp") | Move a fraction of the way to a target, the fraction set by a time constant: `x += (target - x)(1 - e^(-dt/τ))`. Same result at 60 or 240 Hz. | `piano.js:292`; identical twin `approach` in `spectacle-motion.js:3` |
| Asymmetric attack/release smoothing | Two time constants: fast one way, slow the other (key glow rises in 12 ms, falls in 220 ms; light budget dims in 50 ms, recovers in 1.5 s) | `piano.js:1013-1014`, `5007` |
| Sub-stepped spring | Each key is a mass on a spring, integrated in steps of at most 1/240 s; stiffness 4200 / damping 118 pressing, 820 / 36 releasing (springy overshoot on the way up) | `piano.js:980-1007` |
| Two independent springs per key | Daniel's press and Claude's press move separately and the key shows the deeper one, so removing Claude leaves Daniel's frame exactly as if Claude never played | `piano.js:991-1012` |
| Spring field per key (Spectacle) | `v += (25(target - h) - 9v)·h`, 120 Hz substeps; emission phase integrates and never resets on re-strike | `spectacle-motion.js:105-118` |
| Holdable clock | A single `clock()` that a harness can freeze and step frame by frame | `piano.js:676-679`, `5217-5228` |
| Fixed-step simulation | Water advanced in exact 1/120 s steps from an accumulator, independent of display rate | `spectacle-worlds.js:36-47` |
| Settle / debounce for labels | Chord name waits 120 ms after a note-on, 300 ms after a release, so rolled chords don't flash partial names | `piano.js:2335-2351`, `2360-2362` |
| Slow ambient drift | Camera elevation and yaw wobble with incommensurate slow sines (0.13 and 0.071 rad/s) | `piano.js:1171-1172` |

### B. Light and colour

| Primitive | Plain words and maths | Where |
| --- | --- | --- |
| **Shared light model** | Brightness of a sounding note: `velFactor(v) · envelope(s) · state`. `velFactor = 0.35 + 0.65·v^0.8`. `envelope(s) = (1 + 0.7e^(-s/0.22)) · (0.5 + 0.5e^(-s/6))` (a bright strike that settles, then a slow sag like a struck string). State: finger 1.0, finger + pedal 1.45, pedal only 0.8. Release: `0.82e^(-g/0.14) + 0.18e^(-g/1.2)`. One JS object, pushed into GLSL as `#define`s so keys and trails can't disagree | `piano.js:701-719`, `742-746`; spec `PIANO-V2-SPEC.md:90-96` |
| **Light budget** (anti white-wall) | Old light on screen is measured analytically and capped. For each released column, the light it spends is the integral of its exponential afterglow over the visible age window, `G·(e^(-(a0-0.5)/G) - e^(-(a1-0.5)/G)) / screenSeconds` with `G = 3.2 s`; the sum sets a density factor `min(1, 1.2 / load)` that dims old light only, never fresh strikes or held notes | `piano.js:880-900`, `5001-5010`, shader use `817-820`; spec `PIANO-V2-SPEC.md:111-114` |
| **OKLCH vivid palette** | Pitch hue walks the circle of fifths (`200° + 30°·fifthsIndex`). For each hue, find the lightness where sRGB allows the most chroma (scan L, bisection on chroma against the sRGB cube), pull toward it, use 95% of the max chroma: no note is pastel | `piano.js:321-371` |
| Luminance equalization | Hues differ ~4.7x in luminance at full chroma, so pitch colours are scaled toward the palette's geometric-mean luminance with exponent 0.65: velocity decides brightness, not note name | `piano.js:372-398` |
| Text-safe colour | Same hue, lightness floor 0.68 for text on dark scrim, chroma refit to the gamut edge | `piano.js:399-412` |
| Capped secondary colour ("moonlight") | Claude's light is scaled so that, by luminance and by brightest channel, it is at most 0.75 of the dimmest pitch colour at that velocity | `piano.js:571-592`, `593-613` |
| Stage tint | Background and fog lean 3% toward the mean colour of sounding notes over 0.6 s | `piano.js:5011-5016` |
| Theme palettes (Spectacle) | Three colour roles per world (A body, B shadow, C accent) eased over 2.6 s, nudged by harmony (minor, tension, cadence) | `spectacle.js:11-18`, `366-369` |
| HSL fifths palette (harmony diagrams) | A separate palette: `HSL((0.48 + i·0.071) mod 1, 0.48, 0.65)` | `harmony-renderer.js:10` |
| Cosine "spectral" palette | `0.5 + 0.5·cos(phase vector + k·uv)` on glass label rims | `spectacle-voicing.js:87` |
| Tone mapping choice | Neutral (keeps hue) over ACES | `piano.js:443-444` |

### C. Shape and distance fields (SDF = signed distance field: "how far am I from the edge of the shape")

| Primitive | Plain words and maths | Where |
| --- | --- | --- |
| Rounded box SDF | `q = |p| - b + r`; distance = `|max(q,0)|` (the outside part) plus the larger of `q.x` and `q.y` when that is negative (the inside part), minus `r`; trail core = `1 - smoothstep(-0.025, 0.025, d)`; halo = `e^(-7·max(d,0)/w)` | `piano.js:788-806` (twin in `schemes/neon-trails.js:87-94`) |
| Analytic AA with `fwidth` | Rounded-rect label plates antialiased by the screen-space derivative of the distance | `spectacle-voicing.js:82-83`; plaque `142-143` |
| Point-sprite profiles | Gaussian core `e^(-38r²)` plus faint halo; oriented "shard" (rotate by velocity direction, anisotropic Gaussian); six-fold crystal `cos(3θ)^10`; square via Chebyshev distance `e^(-14·max(|x|,|y|))` | `spectacle.js:158-167` |
| Spark falloff | `smoothstep(0.5, 0, r)²` scaled by `(1-k)²` life | `piano.js:937-946` |
| Ring band | Gaussian band at radius 0.72 plus a fainter echo at 0.54, angular ripple `sin(18θ)` | `spectacle.js:286-290` |
| Rain streak / snow star | Streak = thin Gaussian across x; snow = `|cos 3θ|^8` | `spectacle.js:274-276` |

### D. Noise and hashing

| Primitive | Plain words | Where |
| --- | --- | --- |
| Arithmetic hash (no sine) | `fract`-multiply hash, 1D and 3D | `spectacle.js:21-22`; `moonwater.js:7` |
| Sine hash | `fract(sin(dot(p, k))·43758.5)` | `spectacle-worlds.js:51` |
| 2D value noise + 4-octave fbm with rotation | each octave rotated/scaled by a fixed 2x2 matrix to hide grid artefacts | `spectacle-worlds.js:52-53` |
| 3D value noise, 3 octaves ("mist noise") | | `moonwater.js:8-11` |
| CPU LCG streams with fixed seeds | deterministic star, tree, weather placement | `spectacle.js:255`; `spectacle-worlds.js:76`; `moonwater.js:40` |
| Seeded spark RNG (mulberry32) for receipts | | `piano.js:953-954`, `5229-5233` |

### E. Simulation

| Primitive | Plain words and maths | Where |
| --- | --- | --- |
| **GPU particles (ping-pong)** | Position and velocity in float textures (256 wide, 32k/65k/131k by quality), updated by fragment shaders each frame. Forces: a trig "curl-like" flow field, ripple-surface gradient push, pedal/theme buoyancy, pull to the note's x, radial impact blast; exponential drag; floor bounce | `spectacle.js:92-170`, tiers `19` |
| Per-key stochastic emission | A particle respawns when its life is over AND `fract(keyPhase + seed) < dt·(0.6 + v²·1.8)`: births spread in time, never a synchronized puff | `spectacle.js:35-37` |
| **Wave equation water** | 256² height/velocity field: discrete Laplacian, wave speed² 576 (24 units/s), damping `e^(-0.75·step)`, Gaussian drop impulses, absorbing border; fixed 1/120 s step with a CFL note (< 0.4) | `spectacle-worlds.js:9-49` |
| Gesture model | Groups strikes within 70 ms into impacts, strength `mean(v)²·sqrt(uniquePCs)·0.62`; energy, calm, force, presence, tension, cadence as smoothed signals | `spectacle-motion.js:40-49`, `119-139` |
| World journey with hysteresis | 4 s of a stable gesture before a change, at least 14 s between changes | `spectacle-motion.js:19-29` |

### F. Data buses to the GPU (instancing and data textures)

| Primitive | Plain words | Where |
| --- | --- | --- |
| Instanced attribute ring | Trail slots recycled in ring order; only times change; `needsUpdate` only when dirty | `piano.js:727-738`, `835-907` |
| Note state texture `uNotes` 88x2 float | row 0: x, velocity, sounding, held; row 1: start, end, style, pitch | `spectacle.js:65-67`, `390-395` |
| Key motion texture `uKeyMotion` 88x1 | spring height, speed, light, emission phase | `spectacle.js:68`; `spectacle-motion.js:33-34` |
| Pedal history ring texture | 512 samples at 60 Hz, sized to outlast trail life, so a shader can ask "was the pedal down when this stretch of column left the key" | `piano.js:689-696`, `792-795`, writer `4990-5000` |
| Label layout texture | CPU packs label boxes into an 88x1 float texture read by the vertex shader | `spectacle-voicing.js:26-27`, `52-55` |
| Audio waveform texture | 512 samples from the analyser | `spectacle-worlds.js:193-213` |

### G. Geometry and procedural scenery

| Primitive | Plain words | Where |
| --- | --- | --- |
| Rounded boxes | keys, body | `piano.js:496-505`, `532-533` |
| Frame-with-hole shape | ghost rims | `piano.js:614-629` |
| Sum-of-sines ridge × Gaussian depth envelope | CPU-built mountain heightfield | `spectacle-worlds.js:124-132` |
| Merged cone tiers, instanced 260x | pines, wind sway grows with height² | `spectacle-worlds.js:142-159` |
| One tower per key, instanced 88x | city world, height from the key spring | `spectacle-worlds.js:170-190` |
| Parametric ring surface with theme morphs | veils: circle, flame, orbit, hexagon, hanging veil, squircle, blended by soft one-hot weights | `spectacle.js:193-232` |
| Swept petal mesh | curved faceted petal | `harmony-renderer.js:31-35` |
| **Power diagram** (weighted Voronoi) | each pitch class owns a convex cell, clipped half-plane by half-plane (Sutherland-Hodgman), weights from loudness | `harmony-model.js:46-60`, used `harmony-renderer.js:95-102` |
| Tonnetz lattice | triangles of triads, edges deduplicated | `harmony-renderer.js:75-81` |

### H. Projection and screen space

| Primitive | Plain words and maths | Where |
| --- | --- | --- |
| **Lens shift instead of tilt** | `setViewOffset` moves the image down so the keyboard sits low and trails get the sky, without tilting perspective | `piano.js:1178-1180` |
| Fit-the-keys camera | `dist = span/2 / (tan(vfov/2)·aspect) + 7`; pan and zoom eased (1.2 s / 1.6 s), "hurry" down to 0.3 s when keys fall outside view | `piano.js:1121-1133`, `1167-1177` |
| Point size from projection | `uPx = height / (2·tan(fov/2))` so sprites keep world size | `piano.js:1182`; computed again `spectacle.js:387` |
| Off-centre unprojection | A camera-locked layer must unproject the screen centre because of the lens shift | `harmony-renderer.js:63-68` |
| Square-to-quad homography | Map the unit square onto a projected key top (Heckbert), so 2D rims match 3D perspective | `glass.js:57-79`, `83-101` |
| Greedy label packing with hysteresis | candidate grid search; cost = distance from anchor + 0.4 × distance from last frame's place | `spectacle-voicing.js:29-56` |
| Soft room limit | displacement compressed so it never leaves bounds: `dx' = sign(dx)·room·(1 - e^(-|dx|/room))` | `spectacle-voicing.js:16-17` (JS twin `37`) |
| Soft ceiling | `ceiling·(1 - e^(-height/ceiling))` | `spectacle-voicing.js:18-20` |
| Bezier ribbon in Canvas2D | the lean thread: a cubic lifted along the screen normal of the chord between keys, tapering width, glow by shadow blur | `piano.js:3222-3285` |

### I. Text and overlay

| Primitive | Plain words | Where |
| --- | --- | --- |
| Canvas2D layer → texture, drawn after bloom | crisp text that is still inside the recorded canvas | `piano.js:1791-1810`, `5030-5032` |
| Redraw only on content key change; fades as uniforms | | `piano.js:1750`, `2365-2389`, `2415-2430` |
| Software 2D canvas for determinism | GPU 2D canvases shared state and moved one pixel; `willReadFrequently` gives identical pixels | `piano.js:1803-1807` |
| SMuFL music font with fallback | Bravura from jsDelivr, 9 s timeout | `piano.js:1755-1772` |
| Glyph atlas | 11x8 cells of 128 px, mipmapped | `spectacle-voicing.js:57-65` |
| Held label through silence (dimmed) | pure function, pinned by a test | `harmony-renderer.js:189-219` |

### J. Capture and delivery
See section 7.

### K. Verification hooks
See section 8.

### L. Configuration and presets
See section 6.

### M. Plug-in contracts

| Contract | Shape | Where |
| --- | --- | --- |
| Scheme | `{id, name, create(ctx)}` → `noteOn, noteRelease, noteEnd, pedal, update(dt,t,frame), resize, setActive, dispose`; ctx gives THREE, scene, camera, renderer (proxied pixel ratio), clock, keyX, isBlack, noteColor, noteCss, KEY range, RAIL_Y, TRAIL_Z, framing | `piano.js:1189-1191`, `1248`, `1290-1294`; spec `PIANO-V2-SPEC.md:48-78` |
| Instrument | `{id, name, create(ctx)}` → `{group, update(dt,t,state), resize, setActive, dispose}` + hints (keyStyle, keySpan, floorY, hideHostBody), optional `optionsSpec`/`setOptions`, `views` for the gallery camera | `piano.js:1192-1194`, `1295-1338`, `1463-1475` |
| Instrument state | pressed, pedal, chord, a 64-entry strike ring, and a pooled `sounding` map that mirrors the page's own sound model exactly | `piano.js:1195-1210`, `1581-1600` |
| Error isolation | any throw in load/create/update disposes the module, toasts, falls back to the built-in; stored choice kept | `piano.js:1211-1215`, `1359-1371` |
| Race guard | a token per pick: a later pick wins, the earlier resolves false | `piano.js:1418`, `1431` |
| Pixel-ratio proxy | schemes see `getPixelRatio() × renderScale`, so their bands stay put at Ultra/Cinema | `piano.js:1274-1289` |

---

## 5. Where the GLSL lives and what it does

All shaders in this arc are **inline template strings** inside JavaScript (no `.glsl`/`.frag` files). Constants are
injected as `#define`s generated from JS (`piano.js:742-746`) or by string interpolation (`piano.js:793-794`).

| Shader | Location | Technique in my words |
| --- | --- | --- |
| Trail vertex | `piano.js:747-781` | Per instance: bottom of the column rises at `speed` since the sound ended, top rises since the strike (clamped to life); quad padded for halo; column-wide terms (release level, held fade, foot glow) computed once per vertex instead of per pixel. Culls by moving vertices off screen. |
| Trail fragment | `piano.js:782-829` | **Height is time**: `te = now - (y - base)/speed` recovers the moment each stretch left the key; brightness = velocity × envelope(te) × pedal state at te (from the pedal ring texture) × afterglow(age) × light-budget density (fresh stretches exempt). Rounded-box SDF core + exponential halo + a hot white filament only during the attack + a foot glow. Additive blending. |
| Spark vertex/fragment | `piano.js:923-947` | Analytic ballistic path with a sideways wobble and gravity `0.9·age²`; size by perspective; quadratic fade. |
| Particle velocity / position | `spectacle.js:100-135` (+ shared header `23-44`) | GPGPU ping-pong; force sum described in 4E; theme-specific forces blended by soft one-hot weights. |
| Particle draw | `spectacle.js:144-168` | Reads position texture in the vertex shader; sprite shape morphs with power and theme. |
| Threads | `spectacle.js:178-189` | 88 instanced strips along the shared note path; a wavy filament line inside a soft edge. |
| Veils | `spectacle.js:194-230` | A unit plane wrapped into a closed parametric curve per theme, twisting; weave and filament in the fragment. |
| Curtains | `spectacle.js:236-249` | Aurora bands: Gaussian band around a wandering centre line, fine filaments `pow(sin(315x),5)`. |
| Weather | `spectacle.js:258-278` | 9,000 seeded points; fall by modular wrap; impact pushes them radially. |
| Impact rings, halo | `spectacle.js:284-299` | |
| Ripple simulation | `spectacle-worlds.js:13-25` | Explicit wave equation step (section 4E). |
| Sky / galaxy | `spectacle-worlds.js:60-69` | fbm sky plus log-spiral arms `pow(0.5 + 0.5 sin(3a - 16r + ...), 3)` with dust fbm. Opaque on purpose so glass transmission refracts it (`70-73`). |
| Stars, moon | `spectacle-worlds.js:80-95` | |
| Water | `spectacle-worlds.js:98-121` | Vertex: sum of sines + simulated ripple height; fragment: sharp `pow(wave,18)` glints broken up by fbm, plus **glints from the ripple slope** (finite differences of the height texture). |
| Terrain, trees, fog banks, city | `spectacle-worlds.js:133-190` | Lambert-ish facet light, frost by height + fbm, mist by height, depth fade; city windows `pow(cos(9y),18)`; an MSAA lesson: clamp normalised coords before high powers because MSAA extrapolates varyings at thin edges (`182-184`). |
| Note path (shared chunk) | `spectacle-voicing.js:2-22` | One function used by threads, glass, leaders, links and mist: bend from sines + ripple gradient, soft room limit, soft ceiling, theme straightening (city) and recession (rain). |
| Glass labels, leaders, links, mist, plaque | `spectacle-voicing.js:75-148` | Clip-space placement from the layout texture; travelling Gaussian pulse along links. |
| Moonwater | `moonwater.js` (7 ShaderMaterials; skimmed) | Planar reflection via three's `Reflector` (`moonwater.js:1`, `141-150`), 18 stacked fog slices through 3D noise (`166`). |
| Harmony HUD | `harmony-renderer.js:39-41` | Full-screen textured quad. |

---

## 6. Presets, settings and UI surfaces

### 6.1 Where settings live (five stores)

| Store | Keys | Where |
| --- | --- | --- |
| Page localStorage | `arsenal.piano.colour`, `.framing`, `.scheme`, `.instrument`, `.instrument-options`, `.reader`, `.lean`, `.smooth-preview`, `.refresh`, cue prefs, jam view | `piano.js:324`, `419`, `1230`, `1297`, `306`, `3328`, `4194`, `5064`, `2873-2875` |
| Spectacle localStorage | one JSON blob `arsenal.piano.spectacle` | `spectacle.js:20`, `309` |
| Saved looks (browser copy) | `arsenal.piano.looks.cache` with pending ops | `store.js:21`, `128-145` |
| Saved looks (server) | `state/arsenal/looks/presets.json`, rev-numbered, atomic write | `pianolooks.py:18-19`, `168-219` |
| Studio/workbench order | camera order, instrument order | `workbench.js:7` |

### 6.2 The looks registry (the best seam in the arc)
- A look is **visual settings only**; key lock, minor numbering, reader, jam view and Claude prefs are excluded
  (`registry.js:5-7`).
- Every setting is a frozen descriptor: `id, group, label, type (choice|toggle|range), values|range, recBlocked, order,
  read(page), apply(page, value)` (`registry.js:107-177`).
- **Apply order was measured**, not guessed: framing → atmosphere (one patch, then a microtask) → colour → numbers →
  instrument → scheme, then **read back from the page, never from storage** (`registry.js:9-24`, `278-364`).
- One change at a time per page via a promise queue (`registry.js:254-262`).
- `snapshot`, `diff`, `validateValue`, `cleanLook` are pure (`registry.js:183-247`).

### 6.3 The store and server
- Offline-first: changes made while the server is away are kept as pending operations and replayed by look id; a 409
  (another window saved) reloads and replays once (`store.js:11-16`, `179-218`).
- Server: answers only to loopback Host and same Origin, JSON only, size-capped, validates every preset, writes whole
  file to a temp then `os.replace` with fsync, rev check under a lock (`pianolooks.py:59-84`, `110-164`, `193-219`).

### 6.4 UI surfaces that set the same things

| Surface | Built how | Where |
| --- | --- | --- |
| Top bar selects (colour, scheme, instrument, framing, numbers...) | static HTML + `fillLookSelect` | `piano.html:39-114`, `piano.js:1630-1647` |
| Atmosphere panel | `innerHTML` string built inside Spectacle, its own choice lists | `spectacle.js:329-358` |
| Studio "Looks" tab | rendered from the registry descriptors, but groups re-listed | `studio/studio.js:5-8`, `66-73`, `1074-1203` |
| Workbench | reuses host controls ("UI only") | `workbench.js:1-20` |
| HUD | `<dl>` updated at 5 Hz | `piano.html:185-200`, `piano.js:5059` |

Chrome styling: `piano.css` copies First Light's patch-bay tokens (`piano.css:1-23`; same values in
`first-light.css:9-23`); `deck.css:7` and `studio.css:8` each define `--claude: #C8DCFF` again.

---

## 7. Capture and delivery

### 7.1 What the page actually records
- **Rule: only the WebGL canvas is recorded**; everything that must be in a take is drawn into it
  (`piano.js:4-6`).
- `canvas.captureStream(0)` (manual frames) + `videoTrack.requestFrame()` from the render loop on a 1/60 s accumulator,
  so 144/240 Hz displays still give an even 60 fps file (`piano.js:4054-4058`, `5036-5043`); the loop itself caps to
  60 while recording (`5080`).
- Codec choice is **level-aware**: compute macroblocks per second for the actual canvas and pick an H.264 profile
  level that can carry it; above level 5.1 prefer VP9 WebM because this Chromium/AMD path stalls at 4K60 H.264
  (`piano.js:4025-4040`). Bitrate scales with pixel count (16 Mbps at 1080p) (`4076`).
- Audio: only the chosen input (cloned); any other track refuses the take, so Claude's voice can never leak in
  (`piano.js:4060-4071`).
- Upload to `POST /api/recordings?name=piano`, with a download-link fallback (`piano.js:4106-4131`).
- Measured limits on record: smooth 4K60 browser recording **not achieved**; Ultra (1440p) is the capture default;
  "render-loop fps alone is not evidence of encoded video cadence" (`SPECTACLE.md:147-157`).

### 7.2 The unplugged recorder (`piano/recorder.js`)
- Constant frame rate by **slots**: one frame per 1/fps of wall time; a missed or refused slot is filled with a repeat
  of the previous picture, so the file is truly CFR and audio stays in sync (`recorder.js:8-13`).
- Backpressure: refuse captures when the encoder holds more than 0.5 s (`recorder.js:15-18`, `49-50`).
- Warm encoder (three frames pushed at creation), MP4 streamed in 8 MiB blob parts with a reserved moov compacted at
  stop, partial-take recovery, audio clock mapping (`recorder.js:20-40`, `681-805`).
- Muxer: mediabunny 1.56.2 from jsDelivr (`recorder.js:42-46`).
- **Only `recorder-test.html` imports it** (grep across `arsenal/web`); the spec intended piano-next to wire it in phase
  B (`PIANO-V2-SPEC.md:208-210`). Its own `pickMime` (`recorder.js:808-814`) is the older version without the
  level-aware logic that `piano.js:4025-4040` grew.

### 7.3 Display delivery
- **Smooth preview**: when the drawing buffer is more than 1.8x the shown pixels, a 2D canvas copies each frame
  through a chain of exact halvings (bilinear at exactly one half is a 2x2 box average), measured 0.6 ms vs 4.0 ms for
  the browser's mipmapped "high" quality, and smoother (`piano.js:4168-4193`, `4253-4309`). Never recorded.
- **Raster policy** (`web/lib/raster-policy.js:1-30`): a pure module that separates "display raster follows the
  window" from "capture tier is fixed". It documents that /piano sized its buffer from the capture tier (7.73x more
  pixels than shown). Imported by nothing except `tests/raster_policy.test.mjs` (repo grep).
- Quality tiers: Studio 1080p ×1, Ultra ×4/3, Cinema ×2, which also set particle counts (`spectacle.js:19`).

---

## 8. Tests and receipts

### 8.1 Receipt hooks built into the page (`window.__piano`)
- Held clock with single-frame stepping and optional hash (`piano.js:5215-5228`).
- Seeded sparks (`5229-5233`), FNV-1a hash of the whole drawing buffer plus a 16x9 brightness grid and a
  moonlight-pixel count (`5409-5428`), region readback in framing pixels (`5265-5281`), a state digest of every key's
  tilt/colour/rims plus camera, density, tint (`5198-5214`), `looks({render, geometry})` with draw calls and triangles
  (`1696-1745`), `keyQuad` projections (`5309-5326`), `gpu()` renderer string (`5327-5332`), `snapshot()` JPEG
  (`5154`).
- Lanes that drive them: `arsenal/lanes/alias_verify.mjs`, `jam_verify.mjs`, `jam_timing.mjs` (directory listing).

### 8.2 Node and Python tests touching this arc
`tests/piano_looks_registry.test.mjs` (fake page, apply order), `piano_looks_store.test.mjs` (fake server, offline,
409), `test_arsenal_looks_route.py` (HTTP route), `piano_harmony_modes.test.mjs` (Tonnetz topology, weighted cells),
`piano_spectacle.test.mjs` (gesture model), `piano_harmonic_voices.test.mjs`, `piano_label_holds_through_silence`,
`piano_instrument_state.test.mjs`, `piano_string_envelope.test.mjs`, `piano_lean.test.mjs`, `raster_policy.test.mjs`
(headers read). Pure modules are imported directly; **piano.js itself cannot be imported**, so tests slice functions
out of its source text (`piano_instrument_state.test.mjs:13`, `21`; the THEORY block markers `piano.js:40`, `286`).

### 8.3 Gaps (inferred from what exists)
- No shader-level test: the trail shader's light model agreement with `lightLevel()` is guarded by shared `#define`s,
  not by a test (inferred: no test found reading `piano.js:747-829`).
- Spectacle has no reset/seed seam, so pixel-exact atmosphere replay is not established (`SPECTACLE.md:198-202`).

---

## 9. Duplication (same concept, several places)

1. **Smoothing helper**: `damp` (`piano.js:292`) and `approach` (`spectacle-motion.js:3`) are the same function;
   `clamp` twice (`piano.js:290`, `spectacle-motion.js:2`).
2. **Note colour**: OKLCH vivid palette (`piano.js:321-412`) vs HSL fifths palette (`harmony-renderer.js:10`) vs theme
   triads (`spectacle.js:11-18`) vs cosine spectral (`spectacle-voicing.js:87`). The diagrams do not use the page's
   pitch colours.
3. **Classic trails twice**: inline in `piano.js:670-907` and as `schemes/neon-trails.js` (shader at `87-94`), which
   lacks the pedal-history and light-budget features (grep finds no `pedalAt`/`uDensity` in it); used by
   `piano-next.js:456`.
4. **Scheme list three ways**: `piano.js:1233-1242` (8 ids, two of them probes with no file on disk), `registry.js:50-51`
   (6 ids), and the `schemes/` directory (7 modules incl. `neon-trails` and `harmonic-wave`, which neither list
   offers). The instrument list had the same disease and was cured by `instruments/catalog.js:1-35`.
5. **Choice lists hand-copied**: colours (`piano.html:54-58`, `piano.js:325`, `registry.js:58`), themes
   (`spectacle.js:11-18`, `registry.js:123-127`), quality (`spectacle.js:19`, `registry.js:173-176`), weather
   (`spectacle.js:50`, `316`, `340`; `registry.js:128-131`), labels (`spectacle.js:317`, `347`; `registry.js:142-146`),
   framing sizes (`piano.js:415-418`, `studio.js:81`), look groups (`registry.js:32-37`, `studio.js:67-73`).
6. **Key geometry constants**: `piano.js:425-429` and again in `glass.js:27-28`; ghost colours `piano.js:541-546` and
   `glass.js:30-32`.
7. **Noise/hash**: three families in three files (`spectacle.js:21-22`, `spectacle-worlds.js:51-53`,
   `moonwater.js:6-11`).
8. **Rounded box SDF**: `piano.js:788-791`, `schemes/neon-trails.js:87`; rounded-rect with fwidth in
   `spectacle-voicing.js:82-83` and `142-143`.
9. **Soft one-hot theme weight** `1 - smoothstep(0, 0.6, |uTheme - k|)`: 14 occurrences across `piano/*.js` (grep),
   plus a CPU re-implementation (`spectacle-voicing.js:34`).
10. **Note path in two languages**: GLSL `spectacle-voicing.js:7-22` and its JS mirror `32-39` (needed for label
    anchors). The baseline names this pattern as acceptable but drift-prone (`VISUAL-QUALITY-BASELINE.md:29`).
11. **Point-scale maths**: `piano.js:1182` and `spectacle.js:387` compute the same `height/(2 tan(fov/2))`.
12. **Note-state models, five**: page `sounding` (`piano.js:2669`), looks mirror (`1263`, `1585-1600`), Spectacle
    gesture model (`spectacle-motion.js:32`), harmony state (`harmony-renderer.js:7`, `61`), Moonwater voice tracker
    (`moonwater.js:33`).
13. **Canvas-to-texture HUDs, four**: overlay layers (`piano.js:1791-1810`), harmony HUD (`harmony-renderer.js:37-43`,
    `136-182`), Nashville plaque (`spectacle-voicing.js:133-148`), Moonwater HUD (`moonwater.js:226-229`).
14. **Reading the page back through the debug door**: harmony renderer and voicing poll `window.__piano.stats()`
    (`harmony-renderer.js:133`, `spectacle-voicing.js:162`) instead of being handed the reading.
15. **Stage setup copied**: `piano-lab-instruments.js:4`, `101-127` "mirrors piano.js"; other pages build their own
    composer/bloom/tone mapping (`piano-crystal-studies.js:26`, `80-82`; `piano-chord-tree.js:30`, `59-61`;
    `piano-gyre.js:37`).
16. **Bloom threshold as folklore**: schemes say "the host's bloom threshold is 0.9" in comments
    (`schemes/synth-heimdall.js:51`, `synth-navi.js:58`, `upright-roll.js:28`) but it is not in the scheme context, and
    Spectacle sets 0.94 while enabled (`spectacle.js:424`).
17. **pickMime twice**: `piano.js:4025-4040` (level-aware) and `recorder.js:808-814` (older).
18. **Preset systems**: looks registry/store/server (above) vs Gyre presets in localStorage only
    (`gyre-presets.mjs:5-36`) vs First Light `.frag` presets (`arsenal/web/presets/`, listing only).
19. **CSS tokens**: `piano.css:7-23` copies `first-light.css:9-23`; `--claude` defined in `deck.css:7` and
    `studio.css:8`; Studio copies deck text helpers (`studio.js:84`).

---

## 10. Seams: clean places to cut a shared module

Ordered by payoff for "tweak one module and everything updates".

1. **Settings schema as the single source of choices** (`registry.js:107-177`). Make the descriptors the only list of
   themes, qualities, weathers, colours, framings and labels; have `spectacle.configure` validate against them
   (`spectacle.js:310-327`), and generate the Atmosphere panel (`spectacle.js:334-348`), the top-bar selects
   (`piano.html:52-70`) and Studio groups (`studio.js:67-73`) from them. The registry already proves the pattern works
   and is tested without a browser.
2. **Light model module** (`piano.js:701-719`). Export the constants, the JS functions and a generated GLSL chunk from
   one file; trails, keys, neon-trails and every scheme import it. Tests then import it instead of slicing source.
3. **Colour module** (`piano.js:321-412`, `569-613`). Pure maths except a `THREE.Color` target. Harmony diagrams,
   glass, Spectacle accents and other arcs could all take pitch colour from one place.
4. **Key geometry module** (`piano.js:423-437`) shared with `glass.js:27-28` and every instrument/scheme (they already
   get `keyX` through ctx; the glass doesn't).
5. **GLSL chunk library**: hash/noise/fbm (3 families), rounded-box SDF, fwidth-AA rounded rect, Gaussian sprite
   profiles, soft one-hot weight, soft room limit, soft ceiling, cosine palette. All currently inline strings; a
   `glsl/*.js` set of exported strings would let any surface `import` a chunk (the house already composes chunks by
   string concatenation, e.g. `notePathGLSL + ...` at `spectacle.js:179`).
6. **Note bus** (`piano.js:2693-2801`). Today `noteOn` calls each consumer by hand (Spectacle `2702`, trails `2712`,
   keys `2715-2718`, sparks `2719`, lights `2720`, camera `2721`, looks `2722`). An emitter with the scheme contract's
   guarantees (`PIANO-V2-SPEC.md:73-76`) plus one canonical GPU note texture (`spectacle.js:65-68`) would let the five
   note-state models (duplication 12) subscribe instead of re-deriving.
7. **Stage kit** (`piano.js:439-529`): renderer settings, composer, bloom, tone mapping, environment map, lights, as a
   factory that returns them plus a **readable bloom threshold** in the scheme context (fixes duplication 16), reused
   by the lab pages (duplication 15).
8. **Layer registry**: replace the heuristic search that hides Spectacle's note layers by attribute names and render
   orders 3/14/15/30 (`piano.js:1552-1580`) with named layers that declare their role (world, notes, theory, hud).
9. **Camera rig**: the follow camera (`piano.js:1089-1183`), Spectacle's drift that writes `camera.position` after it
   (`spectacle.js:389`), the gallery camera that pre-empts it (`piano.js:1135`, `gallery-camera.js`) and the harmony
   HUD's unprojection (`harmony-renderer.js:63-68`) are four writers/readers of one camera. The baseline asks for no
   competing camera owners (`VISUAL-QUALITY-BASELINE.md:39`).
10. **Delivery module**: frame pacer + recorder (`piano.js:4021-4131`, `5036-5043`) + `recorder.js` + smooth preview
    (`piano.js:4168-4318`) + `raster-policy.js`. One owner for "what size do we render, how do we show it, how do we
    record it".
11. **Receipt harness** (`piano.js:676-679`, `953-954`, `5198-5281`, `5409-5428`): held clock, seeded RNG, buffer hash,
    region readback, digest. Generic to any canvas surface (Gyre, First Light, the VFX bench).
12. **Scheme catalogue** on the model of `instruments/catalog.js`, with the same parity test.
13. **Canvas HUD layer** primitive (duplication 13) and a **pushed reading** instead of `__piano.stats()` polling.
14. **Preset service**: generalize `store.js` + `pianolooks.py` (rev, 409 replay, offline pending, atomic write) with
    a per-surface schema; Gyre and First Light presets could ride it.

---

## 11. Binding rules and taste found in the sources

- Read the visual quality baseline before changing visuals; inspect the actual render in motion; report dimensions,
  timing and limits; a passing suite alone does not establish quality (`arsenal/web/AGENTS.md`, whole file).
- The six-quality standard: fidelity, beauty, fluidity, elegance, performance (native pixels, 60 fps minimum, never
  silently lower resolution for an fps claim), trust (`VISUAL-QUALITY-BASELINE.md:10-17`).
- A new strike adds energy and never erases its predecessors (`VISUAL-QUALITY-BASELINE.md:27`;
  `SPECTACLE-DESIGN.md:3-6`, `122-126`).
- Keep CPU and GPU representations in agreement; invariant tests guard drift (`VISUAL-QUALITY-BASELINE.md:29`).
- No duplicate render loops, no competing camera owners, settings UI out of the recorded canvas
  (`VISUAL-QUALITY-BASELINE.md:39`).
- Do not add an idle animation floor indiscriminately; musical performance may need genuine rest
  (`VISUAL-QUALITY-BASELINE.md:65`). (Note the tension with a house lesson recalled tonight that generative presets
  should have an idle sine floor; the baseline scopes that to standalone sculptures.)
- Scheme rules: solid = finger-held, hollow = pedal-held but never dim; never sum light except Neon Trails behind its
  density guard; only attacks and finger-held cores may cross the bloom threshold; a pedal lift is one visible
  clearing; chord name and staff sit in a protected band; everything driven by the clock, never frame counts
  (`PIANO-V2-SPEC.md:230-238`).
- Daniel's brightness rule: brightest with finger and pedal together, pedal-held still clearly lit, velocity always
  counts (`piano.js:701-703`; `PIANO-V2-SPEC.md:90-95`).
- Everything that must be in a recording is drawn into the WebGL canvas (`piano.js:4-6`); modules never change while
  REC runs (`piano.js:1214-1215`).
- Neutral tone mapping, because ACES pushes neon toward white (`piano.js:443-444`).
- One foreground owner: never two note layers or two headings (`HARMONY-MODES.md:34-37`; who-draws-what rule
  `piano.js:1216-1229`).
- The design fails if soft playing loses its focal form, a strike erases an old one, hard playing merely gets whiter,
  or scenery overwhelms the gesture; review stills and motion (`SPECTACLE-DESIGN.md:133-135`).
- Original shaders only; no third-party shader bodies or assets copied (`spectacle.js:9-10`; `SPECTACLE.md:173-178`).
- Libraries only from jsDelivr at an exact verified version (`PIANO-V2-SPEC.md:29`; three r186 pinned
  `piano.html:20-28`).
- One catalogue, not copies: "a copy that records where it was copied from still drifts, and drifts silently"
  (`instruments/catalog.js:22-24`; `registry.js:52-56`).
- Smooth 4K60 browser recording is not achieved; Ultra is the capture default; render fps is not encoded cadence
  (`SPECTACLE.md:155-157`).
- Studio house rule: clickables blur after a pointer click so letter keys return to the note keyboard
  (`studio/studio.js:16-17`).

---

## 12. Things that look stale or unfinished

- `ENVIRONMENT-PASS.md:9-12` specifies a "Lightfall performance view"; no code by that name exists in `arsenal/web`
  (grep). Possibly renamed or unbuilt **(inferred)**.
- `drawGlass(t)` is called with an argument its definition ignores (`piano.js:5034` vs `3046`). Harmless.
- `PIANO-V2-SPEC.md:26` says "do not edit piano.js; build piano-next"; the swap evidently happened in reverse (piano.js
  grew to 5,480 lines and kept its inline trails while piano-next kept neon-trails) **(inferred from file sizes and
  the scheme lists)**.

---

## 13. Read vs inferred

Read directly: every line range cited above. Skimmed by structure only: `moonwater.js` (head and grep of its
materials), `studio/studio.js` (header and registry calls), `workbench.js` and `gallery-camera.js` (headers), the
instrument and scheme modules (line counts and greps). Inferred and marked: the missing shader test (8.3), the
Lightfall status and the piano-next history (12).
