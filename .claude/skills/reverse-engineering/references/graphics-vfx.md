# Graphics and VFX: frames, looks, effects — the operator's guide

Reading a frame of our own build, and reverse engineering a *look* or an *effect* from video or
screenshots. Distilled from `research/reviewed/reverse-engineering-2026-10-13/graphics-vfx.md` (the
full report, five worked examples with receipts in `graphics-vfx-receipts/`, every URL). **Not legal
advice**; the legal note is below, the full map in `method-legal-cleanroom.md`. GPU frame debugging on
this host is **Daniel's decision** (AMD TDR history; house renders run on SwiftShader under the GPU
lock, never port 8793).

**Never on the host:** "An untrusted sample (any file under study that the house did not build or record itself, unless Daniel has ruled that kind of file trusted) is never run, parsed, decoded or extracted on this machine: it is handled only inside a disposable VM or sandbox that is reverted afterwards, and it is kept outside the repo."

## The one-page version

1. **A frame is a recipe; a frame debugger is a logic analyser on the bus that carries it.** The CPU
   sends the GPU a command list (bind this shader, bind these textures, set this blend mode, draw these
   triangles into that target). A capture records the list with every argument and replays it, so you
   can stop after any command and read every "register" (pipeline state) and "memory bank" (textures,
   targets). It is a logic analyser, not an oscilloscope: **replay does not reproduce real timing** —
   that needs a timing capture or a profiler.
2. **Frame debuggers are for our own builds, our own pages and open-source projects.** RenderDoc's
   author limits it to debugging your own programs; online games with anti-cheat are never a target.
   For other people's games, the lawful and usually sufficient evidence is their behaviour on screen
   (our recordings; public video, which is an untrusted sample and so VM work) plus what their authors
   published.
3. **A screenshot is display-referred; the look was made scene-referred.** By the time a frame reaches
   video it is tone-mapped, clipped, gamma-encoded, 8-bit, usually chroma-subsampled and compressed.
   **Decode the display transform to light before any brightness/falloff/blur/energy measurement, and
   name the clip** (anything that reached white is gone). Measured: treating code values as light more
   than doubled a falloff estimate (126.5 km vs a true 55 km); the right curve gave 57.5 km.
4. **Calibrate every ruler on a look we built before pointing it at one we did not.** Each worked
   example measured a frame whose answer the house knows and reported the ruler's error. Some rulers
   are excellent (a Hald LUT grade reproduced within 1 code value; cleaned phase correlation recovered
   shake within 0.09 px); some are traps (a bloom threshold fitted from a screenshot came out 2.83
   against a true 1.0).
5. **Decompose before you measure.** Effects are layers (two textures scrolling at different speeds, a
   glow on a core, sparks over smoke, a shake over a hit-stop). Measuring the sum as one thing gives a
   confident wrong number (shake: 44 px of error before the moving particles were removed, 0.09 px
   after).
6. **Read the authors before reading the pixels.** VFX culture is generous (Real Time VFX, GDC talks,
   Riot's style guide). Order of trust: the effect's author explaining it → an informed teardown → our
   measurement → our guess. The measurement's job is to confirm the shipped version matches.
7. **Mechanics and techniques are free to learn; assets and distinctive presentation are not.** Rebuild
   from measured behaviour in our own art, never from extracted assets (*Tetris v. Xio* protected a
   game's visual expression of its rules down to the ghost piece and garbage lines).

## Concepts (the frame vocabulary, with hardware analogies)

- **Draw call** — one work order ("run this program over these triangles"; often two per sprite or one
  fullscreen triangle). Analogy: one DMA + one kernel launch.
- **Shader** — the small program each worker runs (vertex places corners, fragment decides pixel
  colour, compute is general). Analogy: microcode.
- **Pipeline state** — every switch read while drawing (blend mode: does this pixel *add* or
  *replace*?; depth test; culling; which textures in which slots). Analogy: the register file. **Most
  "why does it look like that" answers live here, not in the shader.**
- **Render target** — an off-screen picture a pass draws into and a later pass reads (bloom, shadows,
  a G-buffer, every Shadertoy "buffer"). Its **format** matters: an 8-bit target clips at 1.0; a float
  target keeps light brighter than white — what makes bloom possible.
- **Pass** — a group of draws into one target for one purpose (shadows → main scene → transparent
  effects → post → UI). Particles are the classic **overdraw** problem (many large transparent quads
  over the same pixels), the first thing that kills frame rate on a phone.

**How a game effect is built (layers):** core (bright centre, often additive) + glow + secondary
(sparks, debris, smoke) + distortion (heat-haze) + light + decal + camera (shake, hit-stop) + sound.
Particles are camera-facing quads textured from a **flipbook** (read its rate: often 12–30 fps,
independent of the game's). Diablo III layered greyscale textures scrolling at randomised speeds,
multiplied, then coloured by a gradient map (motion without visible repetition; recolour per skill
without new textures — the house aurora card uses the same dual-scroll trick). **Erosion/dissolve**: a
noise texture vs a rising threshold. **Blend modes:** additive (light, order-independent), alpha
(smoke, order-dependent), premultiplied. **Timing** (Riot's style guide): anticipation → climax →
dissipation, readability above theme, value/saturation/size tiers by gameplay importance — the most
transferable knowledge for an Archero-style game where dodging projectiles *is* the game.

**Scene-referred vs display-referred:** *light* (scene-linear; double the number, double the photons)
vs *code values* (display-encoded). A captured frame is code values. Decode the transfer curve
(sRGB, a power, or the game's own; if unknown, measure it on something known in the frame or report
display-referred). Video adds limited range, BT.709, 4:2:0 chroma and codec smear; `arsenal.media
probe` reports codec/fps/keyframes — check the colour range before trusting a black level.

## The method

1. Route the target; write down what it is, where it came from, and the **permission basis** (ours /
   open source / licence allows study / public footage watched for measurement only).
2. Write the question checklist before looking (stage lengths in frames? how many elements and which
   blend mode? palette and saturation vs the scene? does it bloom, from what brightness? camera shake
   or hit-stop, how long? cost in draws/overdraw?).
3. Summary first: for a capture, the pass list + draw counts, then the render-target list with
   formats; for footage, a contact sheet and storyboard (`media grab --sheet`/`shots`,
   `arsenal storyboard`), then pick the few frames that matter.
4. Decompose into layers (passes in a capture; core/glow/sparks/smoke/distortion/camera in footage),
   noting which evidence isolates each (a separate draw; a distinct colour, scale or speed).
5. **Calibrate the ruler, then measure** — run the script on a known look (a house card, a CPU twin
   frame, a synthetic) and record its error. **Measure in light, not code values.**
6. Inspect resources and configuration alongside code (blend state, texture contents, uniform values,
   target formats); never infer behaviour from names (a `fire_glow` texture may be a distortion map; a
   `bloom` function may be a vignette).
7. Corroborate with a different evidence type; and always, at the end, **rebuild and measure the
   rebuild with the same ruler** (an A/B under one tool is the strongest evidence a look study produces).
8. Keep the ledger; revisit the checklist.
9. Rebuild clean-room: the study writes a behaviour spec (numbers, timings, layer structure); the
   rebuild uses our own code and art; label every design choice the evidence did not dictate.

## Tools (licences/cost as published; none installed here — bounded negative)

**Daniel's decision:** installing any of these (RenderDoc, PIX, the Radeon tools, Effekseer, mpv or
FFmpeg builds beyond what the house already has).

**Frame debuggers / profilers (native, Daniel's GPU call):** **RenderDoc** (Baldur Karlsson, MIT) —
capture one frame, replay, event browser, pipeline state, texture viewer with overlays (wireframe,
depth/stencil, NaN/Inf/negative, clipping, quad overdraw, pixel history), shader debugging; full
Python API (`.rdc` files, iterate actions, read state, save textures); Vulkan/D3D11/D3D12/GL. **PIX**
(Microsoft, free) — D3D12 GPU captures **and timing captures** (CPU/GPU timelines, stalls);
`pixtool.exe`. **Radeon GPU Profiler** (AMD) — timing truth on RDNA (occupancy, barriers, per-instruction
timing). **Radeon GPU Analyzer** (AMD, MIT) — offline compiler: a shader in, RDNA machine code +
register pressure out (a static cost check without running). Nsight is NVIDIA-only (not useful here).

**Browser frame inspection (WebGL/WebGPU):** **Spector.js** (Babylon.js team, MIT) — capture one
frame's GL commands with state, shader source as the page compiled it, textures, targets; library form
(`captureCanvas`, `onCapture` → JSON). Stops at 10,000 GL calls; its repo now ships an MCP server (in
this house, point it only at our own pages). **WebGPU Inspector** (Brendan Duncan, MIT) — WebGPU
objects, capture, multi-frame record, a Claude Code plugin (if we ever move to WebGPU).
**webgl-helpers** (greggman, MIT) — tiny injectable scripts: per-frame draw/vertex/upload stats, log
every draw, dump every shader's source (the cheapest instrument for a headless lane). Chrome DevTools
Rendering tab for frame stats. **Note:** a native capture of Chrome shows **ANGLE's translated**
shaders (HLSL/SPIR-V), not the page's GLSL — capture at the WebGL layer with Spector.js for the page's
own code.

**Video/still analysis:** house `media` verbs (probe, grab/sheet, filmstrip, shots, cut) and `arsenal`
verbs (storyboard, motion, boost, floors); **mpv** (`.`/`,` frame step — but prefer extraction to
backward stepping); **FFmpeg filters** (`signalstats`, `waveform`, `vectorscope`, `freezedetect`,
`mpdecimate`, `scdet`, `haldclutsrc`/`haldclut`, `lut3d`, `zscale`); numpy/OpenCV/scikit-learn/SciPy/
PyAV for the measuring scripts.

**Rebuild bench:** the house shader school (`py -m arsenal shader dissect`/`census`/`render`/
`filmstrip`/`check`/`atlas`/`shelf`/`card`) and the GLSL module library (Apache-2.0, SwiftShader under
the lock); **Effekseer** (MIT particle editor); engine particle systems and their open samples (Unity
VFX Graph, Niagara Content Examples, Godot, Effekseer); Blender for pre-rendered flipbooks and gradient
maps. **CPU twins** (`arsenal/shaders/twins/`) are a calibration engine: any house module produces
frames with known parameters at any time step, on the CPU, without the GPU lock (reproduced a GPU-path
card within 1 code value).

## Reverse engineering a look (what a screenshot can and cannot give)

- **Palette:** OKLab k-means, area-weighted (clusters colours the way the eye does).
- **Grade, if we can run the pipeline:** feed an **identity Hald CLUT** through it; what comes back
  *is* the colour transform, read out as a LUT (level-8 worst error 1 code value). **Two tests catch
  anything a LUT cannot capture:** place the Hald image at two positions (a vignette changes the
  answer) and render it at 1-px vs 4-px cells (any blur/bloom mixes neighbours). Both zero → the LUT is
  the look; anything else → spatial parts to separate first.
- **Grade, footage only:** the operator is not identifiable from one graded image, only its
  fingerprints — black/white points, tint of shadows/mids/highlights (split toning), saturation vs
  lightness, hue shifts of memory colours. Rebuild with a small explicit grade and compare statistics.
- **Bloom:** read in decoded light. Cores clip (four emitters of very different brightness all read
  255); **halos remember** (energy survives where the core clipped); the tail shape distinguishes a
  single Gaussian from a mip chain (the long tail is the chain's signature). **You cannot fit the
  threshold or strength from an 8-bit frame** (biased 2.83 vs a true 1.0) — read the float bloom target
  in a capture of our own build, or render a bloom test card of known emitters.
- **Layered scrolling:** column/row correlation split by spatial scale, after removing travelling
  envelopes; sample faster than half a feature per step. Quote **directions** and rough speeds;
  thresholded-together layers do not translate rigidly at either layer's speed.
- **Particle counts:** connected components (undercount) and local maxima (overcount) bracket the
  truth; report the bracket and trend, density above a few hundred.
- **Hit-stop:** blurred structural frame difference (zero-difference tests fail on real footage with
  grain/UI/compression); mask animated UI.
- **Screen shake:** phase correlation against a pre-shake reference **after** removing the moving
  foreground (a grey-level opening or median).
- **Timing:** in frames at the true frame rate; stage lengths (anticipation/climax/dissipation) are the
  most transferable numbers. Easing: track a feature's position, fit the curve family, report the
  residual.

## Routing table (graphics/VFX)

Markers as in the master table: **(VM)** is VM-only whatever the file; **(trusted on host; untrusted → VM)**
runs on the host only for files we built or recorded, or that Daniel has ruled trusted.

| Artifact or question | First tool | Evidence | What it cannot tell you |
|---|---|---|---|
| Our WebGL page: "what does this frame do?" | Spector.js (later a headless SwiftShader lane) | Every GL call with state, shaders as compiled, textures, targets, counts | GPU timing; how the real GPU rounds/orders |
| Our WebGL page: "why does it drop frames?" | Chrome Rendering tab, then a capture | FPS, dropped/partial frames, GPU memory | Which draw is expensive (needs capture + profiler) |
| Our WebGPU page | WebGPU Inspector | Objects, capture, frame times | Native-driver behaviour |
| Shader source we own/may study | `py -m arsenal shader dissect --atlas` | Techniques with file:line + confidence, cost, dead code, atlas parts | How it looks in motion; runtime-only bugs |
| Our native/engine build (Daniel's GPU call) | RenderDoc | Event list, state, every target, overdraw, pixel history, shader debug | Real timing; CPU-side logic |
| Our D3D12 build: "where's the time?" | PIX timing; on AMD, Radeon GPU Profiler | CPU/GPU timelines, stalls, occupancy | Visual correctness |
| A video of an effect/game (trusted on host; untrusted → VM) | `media probe` → `grab --sheet`/`shots`, `arsenal storyboard` | Frame rate, range, cuts, contact sheets | Above the clip; hidden passes; exact params |
| A still: "palette and grade?" (trusted on host; untrusted → VM) | OKLab k-means + tone statistics | Palette shares, black/white points, tint by band, saturation curve | The grade operator; HDR values |
| A grade from a pipeline we can run | Identity Hald CLUT (FFmpeg `haldclutsrc`) | The exact per-pixel transform as a LUT | Spatial effects (position + neighbour tests flag them) |
| Bloom in a frame (trusted on host; untrusted → VM) | Radial profile in light; for our build the float target | Presence, unclipped-emitter bloom, tail shape, radii | Threshold/strength from an 8-bit frame |
| Layered scrolling/drifting textures (trusted on host; untrusted → VM) | Column/row correlation split by scale, envelopes removed | Direction per layer, rough speeds | Exact speeds when thresholded together |
| Particle counts (trusted on host; untrusted → VM) | Connected components + local maxima | A bracket and its trend | Exact count under heavy additive overlap |
| Hit-stop (trusted on host; untrusted → VM) | Blurred structural frame difference | Held frames and spans | Intent; hold vs dropped-frame stutter |
| Screen shake (trusted on host; untrusted → VM) | Phase correlation after removing moving foreground | Per-frame offsets, amplitude, decay | Shake with no static world; UI |
| "How did they make this effect?" | The author's talk/post; Real Time VFX; then Game Art Tricks | Intent, constraints, technique | Whether the shipped version matches |
| An open sample project (VFX Graph/Niagara/Godot) | Its own editor, then a capture of our build of it | The full recipe | Nothing hidden; asset licences still apply |
| A commercial game's files or process | **Stop.** Route to its behaviour on screen + authors' material | (rows above) | Not a frame-debugger or extraction target here |

## Lessons (trigger-phrased)

- Use when measuring any falloff, glow radius or gradient from a screenshot/video, before fitting:
  decode the display transform to light first and say which transform you assumed. Don't when the
  transform is unknown — measure it on something known in the frame first.
- Use when a new measuring script is written, before pointing it at a target: run it on a look the
  house built with known parameters and record its error beside every later result. Don't skip it
  because the target "looks simple" — every ruler failed once before calibration caught it.
- Use when a colour look comes from a pipeline we can run, before hand-matching curves: push a level-8
  identity Hald CLUT through it, read back the LUT, run the position and neighbour tests. Don't when
  either test is non-zero — the look has spatial parts to separate first.
- Use when estimating a bloom threshold/strength, before fitting on screenshots: read the float bloom
  target in a capture of our own build, or render a test card. Don't when only 8-bit frames exist —
  report "halo only on clipped emitters, threshold at or above white" instead of a number.
- Use when estimating camera shake from footage, before phase correlation: remove the moving
  foreground first. Don't when no static world is in view.
- Use when reporting a particle count, before writing a number: give the bracket (connected components
  low, local maxima high). Don't when additive particles overlap heavily — report density.
- Use when someone proposes attaching RenderDoc/PIX or any capture layer, before launching: confirm
  the program is our build / open source / permitted and that Daniel has ruled on GPU use. Don't when
  the target is any online game, anything with DRM/anti-tamper, or the aim is to take assets.
- Use when reading shader code from a native capture of a browser, before treating it as the page's
  code: it is ANGLE's translation — capture at the WebGL layer with Spector.js.
- Use when quoting how long a GPU frame/pass takes, before using a frame debugger's replay numbers:
  take a timing capture or profiler trace.
- Use when matching a reference look for a house game, before copying colours/shapes: take numbers
  (timings, contrast tiers, ranges), not assets or the distinctive arrangement of another game's screens.

## Host safety

The never-on-host rule at the top governs every frame, clip and capture here. In practice: our own
recordings, house renders and captures of our own pages are trusted and are read on the host with the
`arsenal.media` and `arsenal` verbs; downloaded footage, other people's screenshots, and any `.rdc`,
PIX or Spector capture we did not make ourselves are untrusted samples, because a decoder or capture
loader is attack surface, so they are opened only in a disposable VM or sandbox. No VM is enabled today
(**Daniel's decision:** enabling one). Frames, clips and captures stay out of the repo: ours go under
an ignored path such as `state/re/<case>/` (check with `git check-ignore -v <path>`; parts of
`state/` are tracked), never into `research/`, `docs/` or a fence.

## Gaps (build proposals)

Frame capture of our own WebGL pages (inject Spector.js through `Page.addScriptToEvaluateOnNewDocument`
in the headless SwiftShader lane — the hook already exists in `lab_shot.mjs`); a `look` verb (palette +
tone card, same verb on reference and rebuild for an A/B); a `hald` verb (make identity Hald images,
read back a LUT, export `.cube`, position/neighbour tests); a bloom ruler + bloom test card; game-feel
measurements in `motion` (held/dropped frames with timing, shake, easing fits, flipbook rate, layer
drift); a particle counter; a look-study ledger; native frame debugging (RenderDoc Python API, Daniel's
GPU ruling); Radeon GPU Analyzer for static shader cost beside the dissector's estimates; an A/B
compare view in the Shader Lab Workbench.

## Legal note (not legal advice; US, EU and UK orientation, dated 2026-10-13)

In the **US**, studying a program to reach its unprotected ideas can be fair use (*Sega v.
Accolade*, 9th Cir. 1992; *Sony v. Connectix*, 9th Cir. 2000), but a EULA or terms of service can
forbid reverse engineering and be enforced (*Bowers v. Baystate*, Fed. Cir. 2003; *Davidson v.
Jung*, 8th Cir. 2005), and DMCA §1201 separately bans circumventing access controls; its exemptions
(§1201(f), (g), (j); 37 C.F.R. §201.40) excuse only the act, under their stated conditions, never
tools. In the **EU and UK**, a lawful user may observe, study and test a program (Directive
2009/24/EC art. 5(3); CDPA s.50BA) and decompile for interoperability within art. 6's limits (CDPA
s.50B), and contract terms against those rights are void (art. 8; CDPA s.296A). In **both**,
trade-secret law allows reverse engineering a lawfully obtained product unless a valid contract
forbids it (18 U.S.C. 1839(6)(B); Directive 2016/943 art. 3(1)(b)), and ideas, methods and observed
facts are free, while code, art, audio and text are protected and a distinctive look may be protected
(*Tetris Holding v. Xio*, D.N.J. 2012, including as trade dress; republishing a whole extracted table
is a separate question in
the EU, where a database right can apply). **For this domain:** frame debuggers are for our own
builds and pages (RenderDoc's author declines to discuss captures of software you did not create,
and a game with anti-cheat is never a target); a look is measured from behaviour on screen, never
extracted from files; most of the house shader corpus is CC BY-NC-SA 3.0, which forbids commercial
use (study only); and a distinctive visual presentation may be protected expression or trade dress
(*Tetris v. Xio*). The full map with its caveats is `method-legal-cleanroom.md`; anything we ship
that leans on someone else's product goes past a lawyer first.

## Sources

Full report: `research/reviewed/reverse-engineering-2026-10-13/graphics-vfx.md` (five worked examples
with receipts, every URL). Authors credited: Baldur Karlsson (RenderDoc), the Babylon.js team
(Spector.js), Brendan Duncan (WebGPU Inspector), greggman (webgl-helpers), Björn Ottosson (OKLab),
Jorge Jimenez (Advanced Warfare bloom), Julian Love and Nick Seavert (Diablo VFX), Jin Yang / Riot (the
VFX style guide), Simon Trümpler (Game Art Tricks), Adrian Courrèges (graphics studies), Nijman,
Jonasson & Purho (game feel), the Real Time VFX community, Effekseer, and **morluto/rea** for the
evidence discipline. Companion house report: `research/reviewed/shader-school-2026-10-13/color-post.md`.
