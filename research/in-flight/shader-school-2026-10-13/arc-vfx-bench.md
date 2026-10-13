# Arc census: the VFX bench and the cockpit shaders

Shader school, 2026-10-13. One of seven readers. Scope: `scripts/vfx.html`, `scripts/vfx_render.py`,
`scripts/vfx_ingest.py`, `scripts/aurora-shader.js`, `scripts/agent-avatar.js`, `scripts/activity-line.js`,
`design/vfx-chunks/*.glsl`, `design/vfx-sketches/*.frag`, `design/vfx-*.json`, the `/vfx` routes in
`scripts/bifrost_ui.py`, `design/CONTRACT.md`, the shader-craft skill and cookbook, the 2026-09-12 code map, and
the 2026-08-02 studio plan. I also looked one hop outside scope where the seam demanded it: the new
`arsenal/shaders/modules.py` (written tonight at 02:31), `core/learning/vfx_chunk_lessons.py`, and the shader
corpus metadata under `state/arsenal/shaders/corpus/`.

**Method.** Everything below was READ, not run, unless it says "ran". Nothing was rendered, no browser was opened,
no server was started, no git command that changes anything was run. Three small read-only commands were run:
`git ls-files` (which files are tracked), `py -m arsenal shader lib list|lint|show` (text output only), and a
short Python count over the corpus `meta.json` files. Claims marked **(inferred)** are my reasoning from the code,
not something I observed happen. Line numbers are as of 2026-10-13.

---

## 0. The answer in one page

**What this arc is.** The bench is a small shader workshop bolted onto the Bifrost console. Think of it as a
graphics card's test bench: one physical board (a single WebGL2 canvas owned by an `AgentAvatar` instance), a
library of parts (31 GLSL "chunks"), two ways to wire parts together (a linear chain and a typed node graph), a
scratch slot for whole shaders ("sketches"), and a camera rig (snapshot, contact sheet, permutation grid,
thumbnail strip, webm clip). A Python CLI can ask the open browser tab to render, the way a host CPU submits work
to a GPU queue, and gets a PNG path back. The three cockpit modules (the aurora light bed, the agent avatar, the
activity line) are the "production silicon" the bench was built to tune.

**What is already a module system, in all but name.** The `//!` JSON header on each chunk is already a part
datasheet: name, role, ports with types, category, order, provenance and a lesson-shaped note
(`design/vfx-chunks/*.glsl:1`). The bench already builds its UI from a parameter manifest
(`scripts/agent-avatar.js:574-591` feeding `scripts/vfx.html:399-410`). The graph already refuses illegal wiring
at connect time (`scripts/vfx.html:981-992`, `:1232-1245`). And tonight someone shipped
`arsenal/shaders/modules.py`, which reads `design/vfx-chunks` in place as its legacy library
(`arsenal/shaders/modules.py:47`) and resolves dependencies from the code instead of from prose.

**The four biggest findings.**

1. **The "import them all" door would break the licence line as built.** Ingest writes into
   `design/vfx-sketches/` (`scripts/bifrost_ui.py:594`, `:625-638`), and that folder is git-tracked (ran
   `git ls-files`). The corpus is mostly CC BY-NC-SA. Pushing the corpus through today's ingest would copy other
   people's code into tracked files. Imports must land under `state/` and the bench must learn a second sketch
   root. (Details in §7.1.)
2. **Today's ingest accepts about a third of the corpus.** Ran a read-only count over 335 corpus shaders: 114 are
   single-pass with no texture channel and import as-is; 206 reference `iChannel`; 103 have buffer passes; 51 have
   a Common pass; 114 read `iMouse` (shimmed to zero). The house already owns a working ping-pong feedback
   implementation (`scripts/aurora-shader.js:537-659`) that is the seed of a multipass runner. (§7.2.)
3. **Several things in the bench report confident answers they did not measure.** The stage HUD's "ms/frame" is
   the period of a 33 ms `setInterval`, not the frame cost (`scripts/vfx.html:2244-2254`). The graph's "use as
   mask" link draws a wire but the generated code never reads the mask (`scripts/vfx.html:925-927`, `:968-969`,
   `:1279`). The new module lint prints "31 modules, no floor broken" because it exempts every legacy chunk
   before checking anything (`arsenal/shaders/modules.py:282-286`, ran). And the library's own finishing group
   ships a per-frame dither that the house rules call crawling grain (§6, defects D1-D3, D6).
4. **The same primitive lives in many hand copies, with drift.** Twenty-four duplication clusters are listed in
   §5. The worst are the geodesic core (six copies), the analytic orbit trail (three implementations), the
   superquadric field (four), ACES (five), the `//!` header parser (four parsers, two of which read only the first
   line), and the bench's uniform preamble (three hand-maintained copies inside `vfx.html` that already disagree).

**The cleanest cut.** A small "shader host" (context, safe compile, fullscreen triangle, manifest-driven uniform
upload, a controllable clock, capture) extracted from `AgentAvatar`, plus one composer (the new
`modules.py`/`modlib.js` pair) replacing the bench's three codegen functions. Everything else in this report
hangs off those two seams. (§8.)

---

## 1. The parts list (surfaces)

### 1.1 The bench page, `scripts/vfx.html` (2256 lines, last modified 2026-08-12)

Three columns (`scripts/vfx.html:11`): left is the avatar codebook (style, state chips, identity, instance dials,
`:208-235`); centre is the stage canvas (420 px, `:31`, `:238-242`) with four cards beneath it: Compose (the
chain, `:243-273`), Graph (`:275-293`), Shader scratch (`:295-314`) and Hand-off (`:316-325`); right is
Parameters, Presets, the chat thread with claude and the Technique library (`:329-372`).

- **The host.** The bench does not have its own renderer. It drives the very same `AgentAvatar` the console
  mounts (`:375-379`) and uses its scratch-compile door `trySource` to run anything: compositions (`:810`),
  graphs (`:1307`), pasted shaders (`:1355`), thumbnails (`:1601`), CLI jobs (`:1684`, `:1711`, `:1727`,
  `:1822`). In hardware terms, the avatar is the bench's only GPU and every experiment borrows it.
- **The subject switch** (`:216-219`, `:427-543`): "free shader" versus "avatar", saved to server state
  (`design/vfx-bench.json`) so a reload comes back to what was showing (`:501-543`).
- **Chain composer** (`:606-888`): a source plus an ordered list of modifiers; helpers are hoisted
  (`:768-804`). Groups expand on drop rather than staying references (`:687-703`).
- **Graph composer** (`:891-1335`): typed sockets (vec3 colour = round dot, float mask = diamond, vec2 space =
  green square, `:123-137`), a drop-node-on-node "how should these relate" HUD (`:891-979`), cycle refusal at
  connect time (`:1021-1029`, `:1238`), 60-step undo with snapshot-before-mutation (`:995-1011`), and a
  topological-walk code generator that wraps each chunk body in its own block scope (`:1247-1301`).
- **Live preview** (`:1459-1500`): a second `AgentAvatar` (150 px) on hover, inheriting the bench's live
  parameters.
- **Thumbnails** (`:1502-1651`): each chunk rendered against a calibration ramp (`thumb-reference`) as an
  8-frame sprite strip, plus an optional 2 s webm via `MediaRecorder` (`:1869-1933`).
- **Render worker** (`:1655-1867`): the page polls `/vfx/job/next` every 900 ms and runs ops `snap sheet grid
  thumb sketch state script graph` (`:1670-1828`).
- **Capture rig**: `snap` composites onto the console background before export (`:1430-1449`); `renderSheet`
  tiles N frames over a time range with burned-in timestamps (`:1949-1981`); `renderGrid` sweeps two parameters
  at frozen time (`:1987-2019`).
- **Feed and chat** (`:2028-2149`): renders land in the thread under their reason; chat posts a real Bifrost
  message with the bench state and a snapshot path attached (`:2097-2125`).
- **Technique library** (`:2151-2165`): a hard-coded list of ten outside shaders and what each taught.

### 1.2 The CLI, `scripts/vfx_render.py` (293 lines)

Standard-library HTTP client. Verbs: `state thumb sheet grid sketch script graph ingest say`
(`scripts/vfx_render.py:180-258`); `--say` is attached to every verb but `say` automatically (`:264-266`). Prints
the PNG path on stdout and nothing else (`:147-150`). Distinguishes "no tab", "hidden tab" and "slow render"
(`:153-172`). The server address is hard-coded (`:42`).

### 1.3 The importer, `scripts/vfx_ingest.py` (148 lines)

Pure-text translation of a Shadertoy image shader into a bench program by WRAPPING, never editing: a fixed
preamble, `#define` shims for `iTime iResolution iMouse iTimeDelta iFrameRate iFrame iSampleRate iDate`, and a
`main()` that calls `mainImage` (`scripts/vfx_ingest.py:39-58`, `:124-133`). Refuses sound shaders by name
(`:84-87`), warns on `iChannel` (`:105-107`), passes through a shader that is already a bench program
(`:115-119`). No support for Common passes, buffers, textures, keyboard, or a live mouse.

### 1.4 The server routes, `scripts/bifrost_ui.py`

All file-backed stores use write-to-temp then atomic rename. GET routes `scripts/bifrost_ui.py:817-874`, POST
routes `:1308-1347`. Job queue `:206-220`; renderer lease (6 s, a visible tab displaces a hidden one, `legacy`
yields only to an equal) `:223-269`; feed capped at 300 `:317-374`; chunk reader `:543-562`; sketch store with
a bare-name whitelist so the write route cannot write anywhere `:594-638`; ingest `:641-660`; bench state with
merge-not-replace semantics `:663-715`; presets `:718-741`. Static routes for the three cockpit modules
`:799-816`. The console mounts the avatar at `:3605-3649`, the activity line at `:3651-3673`, and the aurora at
`:5618-5671`.

### 1.5 The cockpit modules

| module | what it draws | technique stack | cost governance |
|---|---|---|---|
| `scripts/aurora-shader.js` (681) | Full-screen light bed: three swarms of six emitters flying through fog, with trails | Ray-marched participating medium (26 steps), value-noise density with a height falloff, emitters both light and carve the fog in one loop, analytic trails in screen space, superlinear highlight then tanh, cubic vignette, optional ping-pong motion blur | Half resolution by default (`:519-526`), counts injected into GLSL from JS (`:332-343`), hidden tab stops (`:533`) |
| `scripts/agent-avatar.js` (844) | The agent's face: a geodesic shell of hex tiles (or a glass marble with orbiters) driven by a state codebook | Sphere-traced SDF with icosahedral folding and a hex tiling, superquadric body morph, cone-tracking silhouette AA, tetrahedral normals, closed-form far-side layer, HSV short-way colour easing | 48-step cap, low-power context, `MAX_LIVE = 6`, consecutive-slow-frame watchdog, native device pixels capped at 320 (`:40`, `:233-247`, `:684-707`, `:789-818`) |
| `scripts/activity-line.js` (233) | The fleet's "voice": a waveform whose shape says LIVE, FLAT (measured zero) or DOTTED (no sensor) | Six enveloped sine lines, thickness in pixels, aspect-normalised x, a dash pattern for "unsensed" | Tiny strip at half scale, leaky slow-frame counter (`:188-191`) |

All three share the same seam: `isSupported()` then `new X(canvas)`, `start()`, `setState`/`setRate`/`setTint`,
`stop()`, `destroy()`; the status layer owns WHEN, the shader owns the LOOK (`scripts/aurora-shader.js:13-17`,
`scripts/agent-avatar.js:14-18`, `scripts/activity-line.js:28-33`).

### 1.6 The stores, `design/vfx-*.json`

`vfx-bench.json` (subject `avatar`, sketch `orrery`), `vfx-compositions.json` (one: `aurora-plasma`),
`vfx-graphs.json` (one: `blend-demo`, which carries an unwired `radial-mask` node), `vfx-groups.json` (one:
`filmic finish`), `vfx-presets.json` (empty). The 2026-08-02 audit counted three saves in the bench's whole life,
two of them identical (`research/in-flight/vfx-studio-synthesis-and-plan-2026-08-02.md:170-190`). Nothing has
changed since.

### 1.7 The captures on disk

`design/vfx-thumbs/` holds 19 PNG sprite strips and **no webm clips** (ran `ls`). The seven domain chunks and
`superquadric-slices` have no thumbnail, so the palette index predates them **(inferred from the file list)**.
`design/vfx-snaps/` holds 62 PNGs, the evidence trail of the August arcs.

---

## 2. The primitive census, grouped by what each thing DOES

Two classification axes already exist and they are different questions:

- **`kind`** is the part's ROLE in the pipeline, defined by its ports: `helper` (a function, no ports),
  `source` (space in, colour and alpha out), `domain` (space in, space out), `modifier` (colour in, colour out),
  `blend` (two colours in, one out), `mask` (space in, a single number out). Counts: 4 helper, 7 source,
  7 domain, 8 modifier, 3 blend, 2 mask = 31.
- **`cat`** is the part's FAMILY, what it does to the picture: `blend colour domain field frame mask math motion
  noise shape tone` (ran `py -m arsenal shader lib list`).

A unified library needs both: role decides where a part can be plugged in (the socket shape), family decides
where a person looks for it in a palette. The 2026-08-02 plan already said the palette should be organised by
what parts DO (`vfx-studio-synthesis-and-plan-2026-08-02.md:266-269`). Below I extend the family axis to cover
every primitive I found, including the ones that live inside the cockpit modules and sketches and were never
chunked. Each entry: what it is in plain words, the maths where it helps, and where it lives.

### 2.1 Space (moving the coordinates before anything is drawn)

These are like the address-translation stage in a memory controller: they change WHERE a source looks, not what
it draws. Order matters: a space operation must run before the source samples.

| primitive | in my words | where |
|---|---|---|
| Centred aspect-true frame | `uv = (2·fragCoord − res) / res.y`: origin at centre, y up, one unit = half the height | `design/vfx-sketches/fibshell.frag:58`, `scripts/agent-avatar.js:230`, `scripts/vfx.html:792` |
| 2D rotation in place | rotate a vector by angle a with one cos, one sin | `design/vfx-chunks/rot2.glsl:2`, `scripts/agent-avatar.js:75` |
| Swirl | rotation angle falls with radius, `a = k/(1+2r) + ωt`, so the centre holds and the rim drags | `design/vfx-chunks/swirl.glsl:2-5` |
| Kaleidoscope | fold the polar angle into one wedge of width 2π/n and mirror it | `design/vfx-chunks/kaleido.glsl:2-6` |
| Tile | `fract` of scaled space, so one object becomes a lattice that animates in step | `design/vfx-chunks/tile.glsl:2-3` |
| Fisheye | radial power curve, `r → r^p`, pincushion below 1, barrel above | `design/vfx-chunks/fisheye.glsl:2-3` |
| Ripple | radial displacement whose phase depends on radius AND time, so it travels | `design/vfx-chunks/ripple.glsl:2-3` |
| Orbit (camera drift) | translate the whole domain around a small Lissajous path | `design/vfx-chunks/orbit.glsl:2` |
| Zoom pulse | breathing scale about the centre | `design/vfx-chunks/zoom-pulse.glsl:2` |
| Icosahedral fold | mirror 3D space through the icosahedron's symmetry planes so one face's worth of work covers the whole sphere | `scripts/agent-avatar.js:79-88` (CC-BY-NC-SA lineage, see §7.1) |
| Hex/triangle lattice on a face | skew to a hex basis, `floor`/`fract`, pick the closest triangle | `scripts/agent-avatar.js:90-111` (same lineage) |
| Spherical Fibonacci lattice | point k of N at height `y = 1 − 2(k+½)/N`, azimuth `k · golden angle`; then a windowed nearest-two search to get cell and edge distance | `design/vfx-sketches/fibshell.frag:33-38`, `:48-55`, `:101-112` (clean-room, published maths) |

### 2.2 Noise and fields (making texture out of nothing)

| primitive | in my words | where |
|---|---|---|
| sin-fract hash | `fract(sin(dot(p, k)) · big)`: cheap pseudo-random; bands under `mediump` | `design/vfx-chunks/hash31.glsl:2`, `scripts/aurora-shader.js:217` |
| 3D value noise + 3-octave fbm | trilinear interpolation of hashed lattice corners with a smoothstep fade; sum of three octaves | `design/vfx-chunks/value-noise-3d.glsl:2-7`, duplicated in `scripts/agent-avatar.js:333-340` |
| Quintic value noise (textureless) | same idea with the 6t⁵−15t⁴+10t³ fade, written in the expanded polynomial form; two octaves only because it runs inside a march | `scripts/aurora-shader.js:176-194` |
| 2D gradient noise + 4-octave fbm | Perlin-style, gradients dotted with offsets | `scripts/aurora-shader.js:105-131` (**dead code**, see D8) |
| Domain warp | sample noise at a position already displaced by noise; folds clouds into sheets and filaments | `design/vfx-chunks/plasma-field.glsl:2-8`, `scripts/agent-avatar.js:377-383`, curtains in `design/vfx-sketches/aurora-bus.frag:85-107` |
| Smoothed hash + value noise + octave-limited fbm | the curtain engine Daniel brought, computed rather than texture-fetched | `design/vfx-sketches/aurora-bus.frag:41-75` |
| Noise mask | fbm thresholded through a smoothstep into a 0..1 field | `design/vfx-chunks/noise-mask.glsl:2` |
| Radial mask | `1 − smoothstep(a, b, |uv|)` | `design/vfx-chunks/radial-mask.glsl:2` |
| Calibration ramp | luminance 0..2.2 across x, identity hue across y, banded and slowly rotating, so tone and space operators both have something to show | `design/vfx-chunks/thumb-reference.glsl:2-12` |

### 2.3 Shape (what is in the picture)

| primitive | in my words | where |
|---|---|---|
| Sphere tracing a signed distance field | step along the ray by the distance to the nearest surface; 48 steps | `scripts/agent-avatar.js:240-247`, `design/vfx-chunks/torus-ring.glsl:4-10` |
| Smooth max (rounded intersection) | `smax(a,b,r)` blends two half-spaces with a corner radius | `scripts/agent-avatar.js:77`, `:150`, `:157-158` |
| Hex tile SDF with shape axes | tile = intersection of edge planes and a shell; corner radius gives hexagon→disc, a 6-fold cosine of the edge-frame angle gives star or scallop | `scripts/agent-avatar.js:117-158` |
| Superquadric radius in a direction | for a unit direction d, radius `(Σ|dᵢ|ⁿ)^(−1/n)`; swap it in for the sphere radius and the tiling never notices | `scripts/agent-avatar.js:138-142` |
| Superquadric field with a revolution hollow | `(Σ|xᵢ|ⁿ + l)² − k·8·(x²+y²)`, with n = 8−6k and l = 3.8k−2, so ONE parameter k walks cube → sphere → torus | `design/vfx-sketches/hal-superquadric.frag:30-41`, `design/vfx-chunks/superquadric-slices.glsl`, `design/vfx-sketches/orrery.frag:79-88` |
| Z-sliced isosurface rendering | evaluate the field on a fixed ladder of depth planes, keep the brightest thin contour (`(1−|d|)⁴`), dim far slices; reads as glowing see-through wire, flat cost | `design/vfx-sketches/hal-superquadric.frag:58-72`, `design/vfx-sketches/orrery.frag:175-188` |
| Closed-form ray-sphere | solve the quadratic, no march; used for the glass marble, the far-side layer and the clean-room shells | `design/vfx-chunks/sphere-glass.glsl:3-6`, `scripts/agent-avatar.js:284-293`, `:366-371`, `design/vfx-sketches/fibshell.frag:83-92` |
| Torus SDF | `length(vec2(length(q.xz) − R, q.y)) − r` | `design/vfx-chunks/torus-ring.glsl:7` |
| Flat hex grid | the avatar's lattice flattened to 2D, nearest of two offset lattices | `design/vfx-chunks/hex-grid.glsl:2-12` |
| 2D box SDF | with `d = |p| - b`: the length of d's positive part, plus the larger of `d.x` and `d.y` when both are negative (zero outside) | `design/vfx-sketches/dna-palindrome.frag`, `dna-rotate.frag`, `palindrome-guillotine.frag` (three copies) |
| Ray to 3D segment distance | closest approach between a ray and a segment, with depth | `design/vfx-sketches/orrery.frag:66-74` |
| Per-pixel nearest-atom depth test | every atom tested, nearest wins, so occlusion is real | `design/vfx-sketches/dna-helix.frag:24-26` (stated in the header; body not read in full) |

### 2.4 Motion (how things move without repeating)

| primitive | in my words | where |
|---|---|---|
| Incommensurate rates | drive drift with rates whose ratios are irrational-looking (0.083, 0.061, 0.047) so no period is learnable | `scripts/agent-avatar.js:193`, `design/vfx-sketches/orrery.frag:134` |
| Golden-angle spacing | phase offset `i · 2.39996` so no two orbiters bunch | `scripts/agent-avatar.js:353`, `design/vfx-chunks/orbit-swarm.glsl:8` |
| Analytic trail | the path is a function of time, so the past is `path(t − k·dt)`: no history buffer | GPU version `design/vfx-chunks/orbit-swarm.glsl:2-21` and `scripts/agent-avatar.js:347-358`, `:402-423`; CPU-projected version `scripts/aurora-shader.js:475-504` + `:276-290` |
| Intertwined swarm centres | circle in xz while oscillating in y at a different rate; three centres 120° apart | `scripts/aurora-shader.js:463-473` |
| Kepler-coupled orbits | angular speed ∝ r^−1.5, an eccentric outer ring fast at perihelion | `design/vfx-sketches/orrery.frag:200-218` |
| Travelling waves over a tiling | phase = tile-centre height or angular distance from a drifting pole, minus time | `design/vfx-sketches/orrery.frag:129-139` |
| Exponential easing on elapsed time | `k = 1 − exp(−dt/τ)` per frame, so a transition takes the same wall time at 60 Hz and 144 Hz | `scripts/agent-avatar.js:754-767`, `scripts/activity-line.js:193` |
| Hue easing the short way round | convert to HSV, wrap the hue difference into ±½, lerp; avoids violet→green passing through brown | `scripts/agent-avatar.js:601-626`, `:769-780` |
| Deterministic clock rewind | `_t0 = now − T` makes the next draw show exactly time T; the basis of every capture | `scripts/vfx.html:1941-1944`, `:1964` |

### 2.5 Light and medium

| primitive | in my words | where |
|---|---|---|
| Participating-medium march with Beer-Lambert | accumulate `scatter += T·a·light`, `T *= exp(−a)`, stop at T < 0.02 | `scripts/aurora-shader.js:219-263` |
| Emitters that light AND carve | one loop over particles gives both the inverse-square light at a point and a multiplicative "wake" that removes medium near each particle | `scripts/aurora-shader.js:237-254` |
| High density threshold | take only the top of the noise range so fog has empty space between banks (measured: 46% of screen lit was wrong) | `scripts/aurora-shader.js:229-235` |
| Inverse-square line glow | `g = w/(d + w/2)`, squared, faded along the trail | `scripts/aurora-shader.js:284-287`, `design/vfx-chunks/orbit-swarm.glsl:14-16` |
| Glow falloff `(r/d)^i` and gaussian stars | hashed cells with flicker | `design/vfx-sketches/aurora-bus.frag:77`, `:79`, `:122-127` |
| Classic three-term lighting + fresnel | diffuse, sky ambient, back light, `(1+n·rd)²` rim tinted by state | `scripts/agent-avatar.js:252-263` |
| Tetrahedral normals | four SDF samples on a tetrahedron instead of six | `scripts/agent-avatar.js:222-226` |
| Volumetric marble interior | 16 steps inside the sphere, domain-warped density, identity colour inside, state colour as the light | `scripts/agent-avatar.js:365-400` |

### 2.6 Colour and meaning

| primitive | in my words | where |
|---|---|---|
| Identity gradient (WHO) | two colours per agent lifted from the console's chip gradients; ramped diagonally at 135° to match the CSS | `scripts/agent-avatar.js:469-490`, `:174-176` |
| State tint (WHAT) | one colour per diagnosed state, carried by the lines | `scripts/agent-avatar.js:437-458`, `:179-182` |
| Desaturate for unsensed/dead | mix toward luma by `u_sat` | `design/vfx-chunks/desaturate-unsensed.glsl:2`, `scripts/agent-avatar.js:176`, `:180` |
| Identity wash | pull the image toward the identity gradient without overriding state | `design/vfx-chunks/identity-wash.glsl:2` |
| Channel rotate | `c·.4 + c.brg·.6 + c²`: iridescence that SHIFTS HUE, so never on a state-bearing object | `design/vfx-chunks/channel-rotate.glsl:2` |
| Cosine palette | `a + b·cos(2π(c·t + d))` | `scripts/agent-avatar.js:113-114`, `design/vfx-sketches/fibcore.frag` (`rgbCycle`) |
| Analogous LUT | piecewise ramp indigo → periwinkle → violet | `scripts/aurora-shader.js:135-158` (**dead code**, D8) |
| Swarm identities | two cool, one warm accent at lower gain | `scripts/aurora-shader.js:41-46` |

### 2.7 Tone and finish (the last stages before the screen)

| primitive | in my words | where |
|---|---|---|
| Superlinear highlight | `c += 0.85·c²`: darks untouched, crests bloom | `design/vfx-chunks/superlinear-highlight.glsl:2`, `scripts/aurora-shader.js:306` |
| tanh shoulder | maps [0,∞) to [0,1) and never clips; must come after the highlight | `design/vfx-chunks/tanh-tonemap.glsl:2`, `scripts/aurora-shader.js:307` |
| ACES fit | the Narkowicz rational curve | `design/vfx-sketches/fibshell.frag:46`, `orrery.frag:51`, `aurora-bus.frag:78`, `fibcore.frag`, `daniil-snowfield.frag` |
| Overdrive into the tonemap | multiply by ~1.25 before ACES: glow, not tint | `design/vfx-sketches/fibshell.frag:145-146` |
| Filmic lift/roll | `pow(c, .8)` then remap into [.06, .94]; fights a true-black brief | `design/vfx-chunks/filmic-curve.glsl:2-3` |
| Cubic vignette normalised by the true corner | `1 − (d/d_corner)³` blended at 60%; dividing by 0.7071 instead blacks out widescreen sides | `design/vfx-chunks/vignette-cubic.glsl:2-6`, `scripts/aurora-shader.js:309-315` |
| Gamma | `pow(c, 1/2.2)` | `scripts/agent-avatar.js:295`, `:427` |

### 2.8 Antialiasing, sampling and noise-shaping

| primitive | in my words | where |
|---|---|---|
| Cone tracking | during the march keep `min(d/t)`, the closest angular approach; turns the boolean hit/miss silhouette into coverage | `scripts/agent-avatar.js:235-247`, `:266-273` |
| Edge width from a CONTINUOUS coordinate | `fwidth` of the surface position, never of a cell id | `design/vfx-sketches/fibshell.frag:113-115` |
| Pixel-sized line thickness | derive width from `1/res.y`, never a full-screen constant | `scripts/activity-line.js:59-67` |
| Static per-pixel march jitter | offset the march start by a hash of the pixel only; kills banding without grain | `scripts/aurora-shader.js:211-221` |
| Interleaved gradient noise dither | `fract(52.98·fract(dot(p, (0.0671, 0.0058))))` ±0.006, static per pixel | `design/vfx-sketches/fibshell.frag:43`, `:147`; `orrery.frag:50`, `:245` |
| Triangular dither (per frame) | difference of two hashes; **seeded by time, so it crawls** | `design/vfx-chunks/triangular-dither.glsl:3-5` (see D2) |
| Native device pixels for the subject, undersample the field | the avatar at 1 backing pixel per device pixel (cap 320), the fog at half | `scripts/agent-avatar.js:677-710`, `scripts/aurora-shader.js:506-527` |

### 2.9 Composition (putting pieces together)

| primitive | in my words | where |
|---|---|---|
| Add / screen / mix blends | light adds; screen `1−(1−a)(1−b)` brightens without clipping; mix is a 50/50 average | `design/vfx-chunks/add-blend.glsl`, `screen-blend.glsl`, `mix-blend.glsl` |
| Block-scoped chunk bodies | each chunk sees `uv col alpha` (and `colB`, `m`) as locals and writes them back; the graph wraps bodies and never rewrites them | `scripts/vfx.html:1247-1285` |
| Before/after crossfade tile | every thumbnail fades the effect in and out against the untouched reference; a domain op fades the COORDINATE, not the image | `scripts/vfx.html:1528-1569` |
| Occlusion by the shell | segment midpoint behind the sphere dims to 30%, does not vanish | `scripts/agent-avatar.js:415-419`, `design/vfx-sketches/orrery.frag:226` |

### 2.10 Feedback and multipass

| primitive | in my words | where |
|---|---|---|
| Ping-pong history | render into texture A while sampling B, blit, swap; rebuild both on resize and gate the first read | `scripts/aurora-shader.js:537-659` |
| Zero-cost off path | at `u_motion ≈ 0` skip the offscreen round trip entirely | `scripts/aurora-shader.js:609-620` |

This is the only multipass machinery in the house that I found. It is the seed for importing buffer-based
Shadertoy shaders (§7.2).

### 2.11 Driver and governance patterns (JS side)

| pattern | where |
|---|---|
| Fullscreen triangle from `gl_VertexID`, no vertex buffer | `scripts/aurora-shader.js:76-81`, `scripts/agent-avatar.js:43`, `scripts/activity-line.js:37` |
| Feature gate (`isSupported`: WebGL2 and not reduced-motion) | `scripts/aurora-shader.js:366-376`, `scripts/agent-avatar.js:492-497` (the activity line's gate lacks the reduced-motion half, D4) |
| Safe compile: link the new program before deleting the old | `scripts/agent-avatar.js:647-675` |
| Uniform registry where a missing uniform is a harmless no-op | `scripts/agent-avatar.js:300-314`, `:668-671` |
| Counts injected from one JS constant into GLSL | `scripts/aurora-shader.js:332-343` |
| Tunable manifest that the UI builds itself from | `scripts/agent-avatar.js:568-591`, consumed at `scripts/vfx.html:399-410` |
| State codebook as a data table | `scripts/agent-avatar.js:435-458` |
| Static avatars SNAP, live ones ease | `scripts/agent-avatar.js:628-642` |
| Consecutive-slow-frame watchdog, reset on start | `scripts/agent-avatar.js:789-830` |
| Live-instance cap | `scripts/agent-avatar.js:40-41`, `:823` |
| Hidden tab does zero GPU work | `scripts/aurora-shader.js:533`, `scripts/agent-avatar.js:712-716`, `scripts/activity-line.js:225-230` |
| Draw and read in the same tick (drawing buffer not preserved) | `scripts/vfx.html:1425-1431`, `:1966-1969` |
| Composite onto the deployment background before export | `scripts/vfx.html:1432-1443` |
| Record on a timer, not rAF (rAF throttles in hidden tabs) | `scripts/vfx.html:1923-1930` |
| Render-farm lease | `scripts/bifrost_ui.py:223-269` |

---

## 3. The binding rules this arc carries (methodology and taste)

These are rulings with their source, written to be lifted straight into a shared module contract.

**Ratified by Daniel (taste and scope).**
- One UI scale; 24 dp grid; tokens for spacing and type; colour ROLES, alarm colours only on alarms
  (`design/CONTRACT.md:44-66`).
- Motion budget: at most 24 concurrently animating elements; animate only transform and opacity; off-screen
  animates nothing; ONE rAF scheduler for the page; reduced-motion disables ambient motion
  (`design/CONTRACT.md:68-82`).
- The axis law: no number ships without a label, a unit, a hover explanation, a freshness stamp and a dead state
  that LOOKS dead (`design/CONTRACT.md:93-104`).
- No fps number you did not observe from a visible window (`design/CONTRACT.md:121-125`).
- Crawling grain was removed at his request, not turned down (`.claude/skills/shader-craft/SKILL.md:87-90`).
- "Make sure it's separate from our avatar" is why the bench has a subject switch (`scripts/vfx.html:427-437`).
- Media suite ruling (memory, 2026-09-13): no forbidden-tool rules for the media suite; best and most stable
  wins. Note this is in tension with the shader-craft floor "no Three.js, no CDN" (`SKILL.md:39-41`), which is a
  cockpit rule; a unified module system needs to say which surfaces each floor binds.

**Shader-craft floors (blind-checkable).** House template (`#version 300 es` on line 1, `highp`, fullscreen
triangle); one seam; a colour means one thing (`u_tint` is always state, `u_id0/u_id1` always identity); cost is
pixels × steps × emitters on a host with an AMD driver crash history, so never open a second GPU context to look
at your own work; the watchdog counts consecutive slow frames; derivatives only of continuous values; cone
tracking for silhouettes; counts injected once; `if/else` never `?:` on a struct; ping-pong for feedback; static
jitter, never per-frame; one clock (`SKILL.md:37-93`).

**Ceiling (taste, Daniel's gate).** Simulate the cause, not three symptoms; threshold high so black stays
black; analogous palette with coral as the one warm accent; HSV short-way easing; analytic trails; identity in
the body, state in the lines; thinking and tool use differ in KIND of motion; incommensurate drift;
superlinear-then-tanh; undersample the field, never the subject; spend the march once (`SKILL.md:95-118`).

**The loop.** Sketch in the bench, render through the open tab, numbers beside the image never as a gate, pin
the contract red first (`SKILL.md:120-142`). The 2026-08-02 plan adds: the take strip first, a render ledger
under it, diagnostic metrics must have a chroma axis and a canary that refuses to report when all inputs agree
(`vfx-studio-synthesis-and-plan-2026-08-02.md:219-286`, `:312-324`), and "any proposal that lowers the cost of
producing a render without raising the bar for showing it to Daniel is a net negative" (`:333-337`).

**Format rules.** A `.frag` has `#version` on line 1 and never a `//!` header above it; `//!` is for chunks only,
because chunks are concatenated, never compiled standalone (`.claude/skills/shader-craft/references/house-glsl-cookbook.md:88-93`).
Ingest wraps, never edits (`scripts/vfx_ingest.py:20-23`). A group is stored expanded, so editing it never
changes a saved picture (`scripts/bifrost_ui.py:179-182`, `scripts/vfx.html:687-690`).

**Licence.** The geodesic core is CC-BY-NC-SA and gated before any public use (`SKILL.md:117-118`,
`house-glsl-cookbook.md:67-69`). Techniques transfer; code, copy, brand and assets do not.

**Pins.** `tests/test_vfx_feed_and_lease.py` (module globals `_VFX_LEASE _VFX_FEED _VFX_FEED_SEQ _VFX_JOBS
_VFX_SEQ` cannot be renamed), `tests/test_vfx_ingest.py` (13 tests), `tests/test_shader_craft_skill_cites_live_surfaces.py`
(p0-p7: every path exists, every quoted line is in source and in HEAD, every module keeps its entry points,
every sketch speaks the bench dialect, CLI verbs and flags still exist), `tests/test_hero_avatar_mount_is_race_free.py`,
and tonight's `tests/test_glsl_modules.py` plus `tests/glsl_modlib_parity.mjs`.

---

## 4. The bench's parameter bus, and why it matters for "tweak one module"

The bench has no per-module parameters. Every chunk reads the AVATAR's uniforms, so the avatar's knobs act as a
shared parameter bus (`scripts/vfx.html:785-789`). Chunks then give those knobs unrelated meanings:

| avatar knob | what it means to the avatar | what chunks use it for |
|---|---|---|
| `u_sub` | tile subdivision | kaleido fold count (`kaleido.glsl:2`), tile repeat count (`tile.glsl:2`), hex-grid density (`hex-grid.glsl:3`), ripple frequency (`ripple.glsl:3`), slice count (`superquadric-slices.glsl:6`) |
| `u_round` | hexagon→disc | fisheye lens power (`fisheye.glsl:3`) |
| `u_star` | tile star/scallop | swirl twist (`swirl.glsl:3`) |
| `u_pulse` | breathing | zoom amount (`zoom-pulse.glsl:2`), orbit radius (`orbit.glsl:2`), ripple amplitude (`ripple.glsl:3`) |
| `u_spin` | rotation rate | swirl rate, orbit-swarm rate, torus spin |
| `u_gap` | tile separation | hex-grid line width (`hex-grid.glsl:8`) |

Consequence **(inferred)**: in a composition of kaleido + tile + hex-grid, one "subdivision" slider moves three
unrelated effects at once, and the slider is labelled for the avatar. This is the opposite of "tweak one module
and everything updates": it is "tweak one knob and three modules change by accident". The new module format
fixes this at the source by requiring a module to declare every uniform it reads as a param
(`arsenal/shaders/modules.py:298-302`), but that check is skipped for legacy chunks (D6). A unified system needs
per-instance params with namespaced uniforms (for example `u_kaleido_folds`), generated by the composer.

---

## 5. Duplication map (the same idea, implemented in several places)

| # | concept | copies |
|---|---|---|
| 1 | Geodesic core (icosahedral fold, hex lattice, hex tile SDF, map, normals) | `scripts/agent-avatar.js:73-226`; `design/vfx-sketches/fat-edges.frag` (a fork with wider edges and no superquadric); `geodesic-original.frag`, `geodesic-neon-blue.frag`, `geodesic-neon-full.frag`, `geodesic-ident-edges.frag` (four ~726-line files that differ in a handful of palette lines, ran `diff`) |
| 2 | 3D value noise + fbm | `design/vfx-chunks/hash31.glsl` + `value-noise-3d.glsl`; `scripts/agent-avatar.js:333-340` |
| 3 | Other value noises | `scripts/aurora-shader.js:179-194` (quintic); `design/vfx-sketches/aurora-bus.frag:41-75`; `daniil-snowfield.frag:73+` |
| 4 | Segment distance | `design/vfx-chunks/segment-distance.glsl`; `scripts/agent-avatar.js:342-346`; `scripts/aurora-shader.js:196-200` |
| 5 | 2D rotation `pR` | `design/vfx-chunks/rot2.glsl`; `scripts/agent-avatar.js:75` and `:341`; `design/vfx-sketches/orrery.frag:52`; `fat-edges.frag` |
| 6 | Orbiting emitters with analytic trails | `design/vfx-chunks/orbit-swarm.glsl` (constants differ: radius 1.30 vs 1.34); `scripts/agent-avatar.js:347-358`, `:402-423`; `scripts/aurora-shader.js:463-504` + `:276-290` (CPU-side, different maths) |
| 7 | Superquadric field | `design/vfx-sketches/hal-superquadric.frag:30-41`; `design/vfx-chunks/superquadric-slices.glsl`; `design/vfx-sketches/orrery.frag:79-88`; radius-in-direction form `scripts/agent-avatar.js:138-142` |
| 8 | Z-slice renderer | `hal-superquadric.frag:58-72`; `superquadric-slices.glsl:8-21`; `orrery.frag:175-188` and `:231-237` |
| 9 | Spherical Fibonacci lattice + nearest-two | `fibshell.frag:33-55`; `fibcore.frag` (`fibPt`, `nearest2`); `orrery.frag:43-64` |
| 10 | ACES | `fibshell.frag:46`; `fibcore.frag`; `orrery.frag:51`; `aurora-bus.frag:78`; `daniil-snowfield.frag` |
| 11 | Interleaved gradient noise | `fibshell.frag:43`; `fibcore.frag`; `orrery.frag:50` |
| 12 | Closed-form glass sphere | `design/vfx-chunks/sphere-glass.glsl`; `scripts/agent-avatar.js:366-371`; far-side layer `:284-293`; the clean-room shells |
| 13 | Superlinear + tanh + cubic vignette | chunks `superlinear-highlight`, `tanh-tonemap`, `vignette-cubic`; `scripts/aurora-shader.js:304-315` |
| 14 | 2D box SDF and if-chain sequence data | `dna-palindrome.frag`, `dna-rotate.frag`, `palindrome-guillotine.frag`, `palindrome-story.frag` |
| 15 | Fullscreen-triangle vertex shader | `scripts/aurora-shader.js:76-81` and `:351-355`; `scripts/agent-avatar.js:43`; `scripts/activity-line.js:37` |
| 16 | Compile and link helper | `scripts/aurora-shader.js:421-461` and `:580-600`; `scripts/agent-avatar.js:647-675`; `scripts/activity-line.js:97-104` |
| 17 | `isSupported` gate | three copies, one missing the reduced-motion check (D4) |
| 18 | Resolution policy (dpr cap, scale global, minimum 0.35) | `scripts/aurora-shader.js:519-526`; `scripts/agent-avatar.js:684-707`; `scripts/activity-line.js:156-165` (shares the avatar's global with a different meaning, D5) |
| 19 | Frame watchdog | avatar (consecutive streak, permanent) `scripts/agent-avatar.js:804-818`; activity line (leaky counter, restartable) `scripts/activity-line.js:188-191`; aurora none (`_frames` counter only, `:401`, `:642`) |
| 20 | The bench's uniform preamble | `scripts/vfx.html:785-789` (no `u_thick`), `:1290-1294` (no `u_thick`), `:1571-1575` (has `u_thick`); `scripts/agent-avatar.js:669-670` (lookup list); `:49-71` (declarations) |
| 21 | The `//!` header parser | `scripts/bifrost_ui.py:554-555` (first line only); `core/learning/vfx_chunk_lessons.py:44-47` (first line only); `arsenal/shaders/modules.py:118-136` (multi-line); `arsenal/web/glsl/modlib.js` (browser twin, pinned to the Python) |
| 22 | Shadertoy shim block | generated by `scripts/vfx_ingest.py:49-58`, then baked as text into every ingested sketch (`aurora-bus.frag:7-15`, `fibshell.frag:7-15`, and so on), so changing a shim does not update past imports |
| 23 | Identity colours | `scripts/agent-avatar.js:469-477`; `scripts/aurora-shader.js:41-46`; hard-coded literals in `fibshell.frag:62-64`, `fibcore.frag`, `orrery.frag:95-98`; the CSS `.av` gradients in `scripts/bifrost_ui.py` (cited as the source at `agent-avatar.js:460-464`) |
| 24 | Colour tokens | the bench defines its own `--bg --panel --acc ...` (`scripts/vfx.html:4-8`) rather than importing the console's tokens or the `design/CONTRACT.md` set |

---

## 6. Defects and drift found by reading

Each is "read" (I traced the code path) unless marked **(inferred)**. None was run.

- **D1. The graph's "use as mask" does nothing to the picture.** `linkOptions` offers it (`scripts/vfx.html:925-927`);
  `applyLink` wires the mask's float output into the blend's `colB` port with type `float`
  (`:968-969`), which itself breaks the stated rule that a mask can never enter a colour socket (`:983-984`);
  codegen then always reads the upstream node's `_col` for `colB` (`:1279`), which for a mask is zero; and
  `mix-blend` has no mask input anyway, it mixes at a constant 0.5 (`design/vfx-chunks/mix-blend.glsl:2`).
  Net effect **(inferred)**: "use as mask" halves the brightness. The saved `blend-demo` graph carries an unwired
  `radial-mask` (`design/vfx-graphs.json`), consistent with someone trying and giving up **(inferred)**.
- **D2. The house's own finishing group crawls.** `triangular-dither` seeds both hashes with `u_time`
  (`design/vfx-chunks/triangular-dither.glsl:3-4`), which is per-frame jitter, the exact "crawling film grain"
  the floors forbid (`SKILL.md:87-90`). It is the last step of `filmic finish` (`design/vfx-groups.json`) and of
  `aurora-plasma` (`design/vfx-compositions.json`). Heimdall's blind half proposes this group as the first shared
  module, `vfx.tone` (`research/reviewed/shader-school-2026-10-13/heimdall-unified-module-system-blind-half-b.md:89`);
  it should go in with a static dither (interleaved gradient noise, as fibshell uses) or not at all.
- **D3. The stage HUD's frame cost is a timer period.** It accumulates gaps between `setInterval(..., 33)` calls
  (`scripts/vfx.html:2244-2254`), so it reads about 33 ms whatever the GPU does. The comment calls it "measured
  frame cost, not a guess". This is a gauge that lies under the axis law (`design/CONTRACT.md:93-104`).
- **D4. The activity line ignores reduced motion.** Its `isSupported` only checks WebGL2
  (`scripts/activity-line.js:145-150`); the skill says every module's gate is false under reduced motion
  (`SKILL.md:42-45`) and the contract says reduced motion disables all ambient motion (`design/CONTRACT.md:82`).
- **D5. One global, two meanings.** `AKASHIC_AVATAR_SCALE` accepts (0, 2] and defaults to 1.0 in the avatar
  (`scripts/agent-avatar.js:685-686`) but accepts (0, 1] and defaults to 0.5 in the activity line
  (`scripts/activity-line.js:157-158`). Setting it to 1.5 sharpens the avatar and silently resets the line to 0.5.
- **D6. The new module lint is vacuous on the whole current library.** `lint` returns no problems for any
  non-library module (`arsenal/shaders/modules.py:282-286`), and all 31 modules today are legacy chunks
  (`arsenal/web/glsl/` holds only `modlib.js`, ran `ls`). Ran: "31 modules, no floor broken". The checks that
  exist (licence, credits, `#version`, precision, declared uniforms, `:288-302`) also cannot see per-frame jitter,
  `fwidth` of a cell id, or `?:` on a struct, which are the floors that actually bit us. This is the confident
  instrument the 2026-08-02 plan warned about (`vfx-studio-synthesis-and-plan-2026-08-02.md:312-324`).
- **D7. Three bench preambles already disagree.** The thumbnail preamble declares `u_thick`
  (`scripts/vfx.html:1575`); the chain and graph preambles do not (`:785-789`, `:1290-1294`). A chunk that reads
  `u_thick` would thumbnail fine and fail to compile in a composition **(inferred)**. None of the three declares
  `u_cube` or `u_hole`, which the avatar uploads (`scripts/agent-avatar.js:670`, `:741-742`).
- **D8. The aurora carries a dead curtain.** `hash2`, `noise`, `fbm` and `auroraColor` are defined
  (`scripts/aurora-shader.js:105-158`) and never called by `main` (ran grep). The file header still describes the
  aurora as a flowing curtain with a blackbody LUT invariant (`:1-11`), and the cookbook describes the live
  palette as that LUT (`house-glsl-cookbook.md:29-30`). The live colour comes from `SWARM_COL` (`:41-46`). This is
  the "header comment as source of truth" trap the cookbook itself lists (`:253-254`).
- **D9. FOCAL is written twice.** The JS projection uses `FOCAL = 1.35` (`scripts/aurora-shader.js:33`, `:500`);
  the march hard-codes `1.35` (`:209`). Change one and the trails stop lining up with the fog they sit in
  **(inferred)**. The file's own rule is "counts are injected, never duplicated" (`:332-335`).
- **D10. The aurora's state fade is frame-rate dependent.** `stateLerp += 0.016/1.5` per frame (`:607`), so the
  "~1.5 s" fade takes about 0.6 s on a 144 Hz panel **(inferred from arithmetic)**. The avatar fixed the same bug
  with elapsed-time easing (`scripts/agent-avatar.js:754-764`). The motion-blur feedback weight is per frame too,
  so trail length also varies with refresh rate **(inferred)**.
- **D11. The avatar declares five uniforms nothing sets.** `u_layers u_bob u_pillar u_orbit u_morph`
  (`scripts/agent-avatar.js:67-71`) are not in the lookup list (`:669-670`), not uploaded, not read by any shader
  (ran grep). They describe orrery features that live in a sketch.
- **D12. Bench chat goes to every agent.** The page posts `target:'claude'` (`scripts/vfx.html:2116`); the
  handler reads `to` and defaults to `all` (`scripts/bifrost_ui.py:1508`). Already flagged by the 09-12 code map;
  still present.
- **D13. CLI jobs break the subject switch's promise.** The `thumb` op always restores `geodesic`
  (`scripts/vfx.html:1719`); `sheet`, `grid` and `graph` compile something and never call `setSubject`
  (`:1680-1707`, `:1818-1826`). After a CLI thumbnail the label can say "free shader, running orrery" while the
  avatar is on screen **(inferred)**, which is the exact dishonesty the switch was built to remove (`:427-437`).
  `generateThumbs` likewise throws away a running sketch (`:1639-1641`) despite promising not to cost working
  state.
- **D14. The bench-state note and the bench-state disagree.** `design/vfx-bench.json` says "refresh lands here"
  for orrery, but `subject` is `avatar`, and `loadBench` restores a sketch only when the subject is `shader`
  (`scripts/vfx.html:526-542`). A refresh shows the avatar.
- **D15. Two CSS rules share the class `.hud`.** The stage HUD (`scripts/vfx.html:32-34`) and the link HUD
  (`:145-150`) collide **(inferred visual)**: the stage readout inherits a blue-bordered box, and the link HUD
  inherits `bottom:10px`, which together with an inline `top` stretches it to the bottom of the graph canvas.
- **D16. The preview may run two loops after a tab switch (inferred).** The hover preview drives its own rAF loop
  (`scripts/vfx.html:1494-1499`) on an `AgentAvatar` that was never started, but every avatar's visibility handler
  calls `start()` on show (`scripts/agent-avatar.js:714`), so a hide/show would start a second loop on the preview
  and take a slot from `MAX_LIVE`.
- **D17. Small stale facts.** The activity line says "five sine evaluations ... five lines" (`scripts/activity-line.js:23-24`;
  cookbook `:20`) and draws six (`:81`, `i <= 5`). The server's chunk comment names three roles
  (`scripts/bifrost_ui.py:160-166`); there are six. Heimdall's half says the chunks are 33 and "never
  machine-loaded anywhere" (`heimdall-unified-module-system-blind-half-b.md:22`); there are 31 and the bench
  loads them (`scripts/bifrost_ui.py:543-562` → `scripts/vfx.html:820-856`), as does recall
  (`core/learning/vfx_chunk_lessons.py:36-53`).
- **D18. Idle GPU work is a known, parked wish.** Nothing gates on idle; eased avatars never arrive and redraw
  forever; the aurora takes the two-pass blur path every frame by default (`docs/WISHLIST.md:1203`, W182, parked
  at Daniel's instruction). Any shared host should make idle-parking a built-in rather than a per-module chore.

---

## 7. What Daniel's ask needs from this arc

### 7.1 The licence line runs straight through the ingest door

- Ingest stores into `design/vfx-sketches/` (`scripts/bifrost_ui.py:594`, `:625-638`), which is tracked (ran
  `git ls-files`: all 20 sketches and all 31 chunks are tracked). The corpus is 286 of 335 CC BY-NC-SA, 21 CC0,
  19 MIT, 4 CC-BY-SA, 3 all-rights-reserved, 2 CC-BY (ran the count over `meta.json`).
- Therefore "import them all into our vfx tooling" must NOT reuse today's store. It needs a second sketch root
  under `state/` (untracked), and the bench's sketch list must show where each sketch lives and under what
  licence. The `meta.json` already carries `license` per shader.
- Already-tracked third-party material, for whoever owns the licence gate (not acted on): the four
  `geodesic-*.frag` files are ports of llVXRd (CC-BY-NC-SA); `daniil-curtains.frag` says "verbatim"
  (`:17`); `daniil-snowfield.frag` says "faithful port" (`:17-28`); `agent-avatar.js` adapts llVXRd
  (`:8-9`). The clean-room alternatives exist: `fibshell.frag`, `fibcore.frag` and `orrery.frag` state "no llVXRd
  lineage" and rebuild from published maths (`fibshell.frag:19-22`, `fibcore.frag` header).
- One more data-hygiene note: `aurora-bus.frag` bakes real ledger message ids and agent names into a shader
  (`:26-31`, `:38`). That is a story-shader, but it is fleet data in a tracked graphics file.

### 7.2 What it would take to import the corpus (ran a read-only count)

| corpus feature | count of 335 | today | what to build |
|---|---|---|---|
| single image pass, no channels | 114 | imports as-is | nothing |
| reads `iMouse` | 114 | shimmed to zero (`vfx_ingest.py:52`) | a scripted mouse path as a uniform, so mouse-driven shaders show their motion |
| a Common pass | 51 | not concatenated | prepend Common to every pass (pure text, cheap) |
| buffer passes | 103 | refused by warning | a multipass runner: N ping-pong targets, each pass reads the others' previous frames; generalise `scripts/aurora-shader.js:537-659` |
| texture inputs | 261 inputs | warned | local media cache under `state/`, with licence; cubemaps (35) and volumes (9) need more |
| keyboard, music, video, sound | 40 + 44 + 2 + 21 | refused or ignored | out of scope for a picture bench |

A deterministic still for a multipass shader needs the same protocol the cookbook gives for the aurora: reset
the history, settle a fixed number of frames, then capture (`house-glsl-cookbook.md:52-58`). Today's `--t` seek
is not enough once feedback is involved.

### 7.3 "Break down the primitives and group them by category"

§2 is that breakdown for this arc. The proposed taxonomy for the shared library:

- **Role (socket shape), seven values:** function, field (source), space (domain), filter (modifier), blend,
  mask, and a new **pass** role for anything that owns a render target (feedback, buffers, bloom).
- **Family (palette shelf), ten values:** Space, Noise & fields, Shape, Motion, Light & medium, Colour &
  meaning, Tone & finish, Sampling & AA, Composition, Feedback. Each module gets one family; a module that
  genuinely spans two (the swarm both lights and moves) picks its primary and lists the other as a tag.
- **Tier**, so a palette can be honest about cost on this host: cheap (no loop), loop-bounded (fixed small
  loop, like Z-slices), march (sphere tracing or volume), multipass. The 08-02 plan's warning that N live mini
  windows are a trap on this host (`vfx-studio-synthesis-and-plan-2026-08-02.md:301-304`) makes tier a
  first-class field rather than a note.

---

## 8. Seams: clean places to cut one shared module system in

In order of leverage. Each names the exact lines where the cut goes.

1. **One composer, in the browser.** Replace `buildGLSL` (`scripts/vfx.html:768-804`), `buildGraphGLSL`
   (`:1250-1301`) and `thumbShaderFor` (`:1522-1583`) with calls to `arsenal/web/glsl/modlib.js`, which already
   resolves dependencies from the code and is pinned byte-for-byte to the Python composer
   (`arsenal/shaders/modules.py:26-29`). This deletes three uniform preambles (D7), the "include every helper"
   shortcut (`scripts/vfx.html:777-783`) and the prose dependencies. Keep the block-scope wrapping
   (`:1272-1284`): it is the right calling convention and should be written into the module spec as the snippet
   ABI (`uv col alpha colB m` in, written back out).
2. **One header parser.** Point `_vfx_chunks_read` (`scripts/bifrost_ui.py:543-562`) and `_chunk_headers`
   (`core/learning/vfx_chunk_lessons.py:36-53`) at `arsenal.shaders.modules.parse_module`. Today both read only
   line 1, so the moment anyone adds a multi-line header to `design/vfx-chunks/` (which `modules.py` allows,
   `:15-16`), the bench marks the chunk `broken` (`bifrost_ui.py:561`) and recall silently skips it **(inferred)**.
   This must land before any multi-line header is written into that folder.
3. **A shader host extracted from `AgentAvatar`.** The bench already treats the avatar as a generic GPU host.
   Cut `_compile` (`scripts/agent-avatar.js:647-675`), `_resize` (`:677-710`), `_draw`'s upload half
   (`:718-747`), and `_tick`/`start`/`stop`/watchdog (`:749-833`) into one `ShaderHost` with: safe compile,
   fullscreen triangle, uniforms uploaded from a param manifest, a controllable clock (`_t0`), visibility and
   idle parking, one watchdog policy, and an optional ping-pong pass list. Then `AgentAvatar`, `AuroraShader`,
   `ActivityLine`, the bench stage, the hover preview and a future multipass importer are all thin clients.
   This retires duplication rows 15-19 and defects D4, D5, D10, D16, D18 in one move.
4. **Params are a manifest, the UI is generated.** The bench already builds sliders from `AgentAvatar.PARAMS`
   (`scripts/vfx.html:399-410`). Generalise: each module declares its params (name, uniform, range, default,
   label, unit), the composer namespaces the uniforms per node, and the bench's Parameters panel renders the
   selected node's params. This is how "tweak one module and everything updates" becomes true without "tweak one
   knob and three modules change" (§4). The axis law gives the label and unit fields for free.
5. **A capture service.** `snap`, `renderSheet`, `renderGrid`, `recordClip` and the deterministic clock
   (`scripts/vfx.html:1430-1449`, `:1894-1933`, `:1935-2019`) plus the job queue and lease
   (`scripts/bifrost_ui.py:195-374`) are a general "render this host at these times and give me a file" door.
   Any other arc's surface (the piano, first-light, presentation scenes) could register as a renderable subject
   instead of each growing its own screenshot path. The subject list would replace the hard-coded
   `avatar|shader` check (`scripts/bifrost_ui.py:705-706`).
6. **Meaning tables as shared data.** The state codebook (`scripts/agent-avatar.js:437-458`), identity table
   (`:469-490`), swarm identities (`scripts/aurora-shader.js:41-46`) and the CSS chip gradients should be one
   JSON that every surface reads, so a colour cannot drift between the console chip, the avatar, the bed and a
   sketch (row 23). Sketches would receive identity as uniforms instead of literals.
7. **The stores.** Heimdall proposes mapping `design/vfx-*.json` onto `arsenal.graph/v0`. Agreed on shape, with
   the 08-02 audit's caution attached: three saves in the bench's whole life says the storage problem is that
   saving costs a name, not that storage is badly organised (`vfx-studio-synthesis-and-plan-2026-08-02.md:180-190`).
   The take strip (S2) and render ledger (S1) remain the first thing worth building on top.
8. **Ingest gets a destination and a pass model.** `vfx_ingest.rewrite` stays pure text (it is well pinned,
   13 tests); add Common concatenation and a pass list output, and give `_vfx_ingest` a root parameter so corpus
   imports land in `state/` (§7.1).

---

## 9. Ranked recommendations for the morning

1. Before anything imports the corpus: give ingest a `state/` destination and make the bench list both roots
   with licence shown (seam 8, §7.1). This is a licence-line guard, not a feature.
2. Point the two first-line header readers at `parse_module` (seam 2) before any multi-line header lands in
   `design/vfx-chunks`.
3. Replace `triangular-dither`'s time seed with a static one before `filmic finish` becomes the shared tone
   module (D2). Give the module lint real teeth for legacy chunks, at least warnings for per-frame `u_time` inside
   a hash, `fwidth` near `floor`, and undeclared uniforms (D6).
4. Swap the bench's three codegen paths for `modlib.js` (seam 1), and fix the mask path while doing it (D1).
5. Extract the shader host (seam 3). Pin RED first: the three modules keep their public entry points (p3 of the
   skill test already asserts this).
6. Generate per-node params (seam 4) so the parameter bus stops leaking between modules.
7. Small honest fixes that need no design: the HUD metric (D3), the activity line's reduced-motion gate (D4),
   the scale global (D5), FOCAL injection (D9), the chat `to` field (D12), subject honesty after CLI jobs (D13),
   the dead curtain code and its two stale descriptions (D8). Per house practice, ask before deleting the dead
   curtain functions; they may be wanted for a style.

---

## 10. Sources read

`scripts/vfx.html` (all), `scripts/vfx_render.py` (all), `scripts/vfx_ingest.py` (all), `scripts/aurora-shader.js`
(all), `scripts/agent-avatar.js` (all), `scripts/activity-line.js` (all), `design/vfx-chunks/*.glsl` (all 31),
`design/vfx-sketches/*.frag` (ringpulse, hal-superquadric, aurora-bus, fat-edges, orrery, fibshell in full;
fibcore, dna-*, palindrome-*, daniil-* headers; geodesic-* header and diff), `design/vfx-*.json` (all),
`scripts/bifrost_ui.py:140-269`, `:536-741`, `:1495-1519`, `:3600-3709`, `:5615-5674` and the full `vfx` grep,
`design/CONTRACT.md`, `.claude/skills/shader-craft/SKILL.md`, `references/house-glsl-cookbook.md`,
`research/in-flight/vfx-system-code-map-2026-09-12.md`, `research/in-flight/vfx-studio-synthesis-and-plan-2026-08-02.md`,
`arsenal/shaders/modules.py:1-167`, `:280-303`, `core/learning/vfx_chunk_lessons.py:1-64`,
`research/reviewed/shader-school-2026-10-13/heimdall-unified-module-system-blind-half-b.md` (grep only),
`docs/WISHLIST.md` (grep only), `state/arsenal/shaders/corpus/shaders/*/meta.json` (counted, no code copied).
