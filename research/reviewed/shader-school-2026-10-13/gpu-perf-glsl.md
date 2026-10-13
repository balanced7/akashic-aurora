# GPU performance and GLSL ES 3.00 / WebGL2 correctness, Shadertoy inputs, and audio-reactive technique

Shader school, 2026-10-13. One of eight topic reports. Written for Daniel and for any seat that will build the house
library's performance, correctness, input and audio modules (`arsenal/web/glsl/`, composed by `arsenal/shaders/modules.py`).

**Licence line.** Everything below is in my own words and mathematics. Pointers into the private corpus
(`state/arsenal/shaders/corpus/shaders/<id>/<file>:<line>`) are pointers only; no corpus code is reproduced. Short
quotations are under 15 words and attributed. The function signatures in section 14 are written fresh for the house.

**How this was made.** Primary sources first (AMD's own architecture and performance documents, the Khronos
specifications, the W3C Web Audio specification, Microsoft's driver documentation, the onset-detection papers by their
authors), then the best-known practitioners (Inigo Quilez, Fabrice Neyret, Emil Persson, Fabian Giesen). Facts about this
machine come from read-only queries (the adapter list from `Win32_VideoController`, the renderer string recorded in a
house check run). Nothing was rendered on the GPU, no browser was opened, no server was started.

---

## 0. How to read this

Sections 3 to 10 are the engine room: how a fragment shader actually executes, what branches, loops, precision and
textures really cost, how Chrome on Windows turns GLSL into GPU code, what breaks at compile time and how to measure
speed without vendor tools. Section 11 is the Shadertoy interface (inputs, keyboard, mouse, sound). Section 12 is
audio-reactive technique, aimed at the house target: a live piano visualizer. Section 13 is the gallery of mistakes as
they look on screen. Section 14 is the primitive API for the house library. Section 15 is what I would change in the
house tooling. Section 16 is the reading list.

### Eight findings that matter to the house tonight

1. **This machine sets a specific budget, and it is large but not infinite.** The adapter list shows an **AMD Radeon RX
   9070 XT** (RDNA 4: 64 compute units, 4,096 lanes, 1,536 vector registers per SIMD) driving **3840 x 2160 at 240 Hz**,
   plus a second adapter, the processor's integrated Radeon graphics. At 240 Hz a frame is 4.17 ms; a full 4K frame is
   8.29 million pixels; the card's single-issue arithmetic rate (about 24.3 trillion floating-point operations per second)
   divides out to roughly **12,200 operations per pixel per frame at 4K/240** in a perfect world, 48,900 at 60 Hz. The
   aurora bed at its half-resolution 720 x 450 gets about 25 times more per pixel. Section 3.8 does the arithmetic.
2. **The house's blind verification path never meets the compiler the live pages meet.** House shader checks record
   the renderer `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) ...), SwiftShader driver)`
   (`state/arsenal/shaders/check/20261013-030140.json:18`): GLSL is translated to SPIR-V and run on the CPU. A page in
   ordinary Chrome on this Windows host, on Chrome's long-standing default Direct3D 11 back end, goes GLSL to HLSL to
   Microsoft's FXC compiler to the AMD driver (section 8; confirm the back end from the live renderer string). So
   three classes of defect are invisible to the blind loop: compile-time explosions (FXC unrolling loops), Windows-only
   semantic differences (negative integer modulo, `clamp` of a NaN), and the 2-second GPU watchdog. A rough scan finds
   **50 of the 335 corpus shaders calling `texture()` inside a loop body**, the exact pattern FXC answers with
   "attempting to unroll the loop" (warning X3570); 24 corpus shaders already carry the usual unroll guard.
3. **The Web Audio analyser smooths per call, not per second.** The specification's smoothing step mixes each new
   spectrum with the previous one by a fixed fraction every time you ask for data. Asked once per animation frame, the
   default 0.8 is a 75 ms time constant at 60 Hz and **19 ms at 240 Hz**. `arsenal/web/play.js:1483` and
   `arsenal/web/edit/playback.js:86` already set it to 0, which is right; any new audio-reactive surface must do the same
   and smooth with the real frame time (section 12.5).
4. **`iSampleRate` in the house Shadertoy runtime is a constant 44,100** (`arsenal/web/shaderlab/toy-runtime.js:87`,
   bound at `:1217`). If the AudioContext feeding `setAudio` runs at 48 kHz (common on Windows), every shader that turns a
   spectrum texel into hertz is off by 8.8 per cent, which is **1.47 semitones**, and a sound shader would be pitched for
   the wrong clock if it were ever played. The fix is one line: bind the AudioContext's real `sampleRate`.
5. **Most Shadertoy feedback shaders are frame-locked.** 83 of the 103 multipass corpus shaders never read `iTimeDelta`
   or `iFrameRate`. Anything they integrate per frame (decay, advection, physics) runs four times faster on this 240 Hz
   display than on the 60 Hz it was tuned on. The cure is a per-frame factor derived from a per-second one:
   `k_frame = k_second ^ dt` (section 5.7).
6. **An 8-bit feedback trail never fully fades.** Multiplying a stored byte by 0.98 each frame stops changing it once
   0.02 times the byte is less than half a step: at **byte 24 or 25 (about a tenth of full brightness)**; which of the
   two depends on how the hardware rounds an exact half. At 0.99 it sticks near byte 50 (a fifth). The house runtime
   only falls back to RGBA8 with a warning (`toy-runtime.js:891`); house modules that decay must subtract a floor or
   use a half-float target.
7. **The piano lives below the FFT's resolution.** Shadertoy's spectrum row has 23.4 Hz per texel (a 2,048-point
   transform at 48 kHz, consistent with Inigo Quilez's own note in `Xds3Rr/image.glsl:26`). A semitone is narrower than
   one texel for **every key below G4 (key 47 of 88)**; the whole bottom octave sits in texels 1 and 2; 65 per cent of the
   512 texels lie above the piano's highest fundamental (C8 lands at texel 179). So: MIDI tells a shader *which* notes,
   audio tells it *how they sound*. The house listen DSP already does pitch the right way (a decimated 4,096-point
   transform at 6 kHz, 1.46 Hz per bin; `arsenal/web/piano/listen/dsp.js:17-19`).
8. **A runaway loop is a whole-machine risk here, not a tab crash.** Windows resets the GPU when a submission runs past
   2 seconds, and by default bug-checks the machine (a blue screen, code 0x117) on the sixth hang when five or more
   happen within one minute. With this host's AMD driver-crash history, every house loop has a constant ceiling, and any
   heavy offline render is split into tiles so no single draw approaches the limit (sections 8.6 and 10).

---

## 1. Vocabulary (spelled out once)

| term | meaning |
|---|---|
| **fragment shader** (Direct3D: pixel shader) | the program the GPU runs once for every pixel a draw covers; a Shadertoy `mainImage` is one |
| **lane** (thread, invocation) | one pixel's worth of execution inside the GPU |
| **SIMD** | single instruction, multiple data: one instruction decoder drives many arithmetic lanes in lock-step |
| **wave** (AMD: wavefront; NVIDIA: warp) | the group of lanes that execute one instruction stream together: 32 or 64 on AMD, 32 on NVIDIA |
| **CU / WGP / SM** | compute unit (AMD; two SIMD32 units each on RDNA), workgroup processor (two CUs), streaming multiprocessor (NVIDIA's equivalent) |
| **VGPR / SGPR** | vector register (one 32-bit value per lane) / scalar register (one value shared by the whole wave) |
| **occupancy** | how many waves are resident on a SIMD at once, out of its maximum (16 on RDNA 2 to 4) |
| **EXEC mask** | AMD's bit-per-lane switch saying which lanes an instruction actually affects |
| **divergence** | lanes of one wave wanting different paths through an `if` or a different number of loop trips |
| **quad** | a 2 x 2 block of pixels; the GPU always shades whole quads so it can take derivatives |
| **helper lane** | a quad member outside the triangle (or already finished) that runs anyway so its neighbours get derivatives |
| **derivative** | `dFdx`, `dFdy`, `fwidth`: the difference of a value between horizontally or vertically adjacent pixels in a quad |
| **latency / throughput** | how long one operation takes to come back / how many complete per unit time |
| **ULP** | unit in the last place: the gap between a floating-point number and the next representable one |
| **texel** | one element of a texture; its **centre** sits at integer + 0.5 in texel coordinates |
| **mipmap, LOD, lambda** | a pyramid of pre-shrunk copies of a texture; level of detail; the `log2` scale factor that picks a level |
| **render target, framebuffer** | a texture the GPU draws into; a set of them bound together |
| **ping-pong** | two textures alternated as read and write so a pass can see its own previous frame |
| **ANGLE** | Google's layer that runs WebGL on top of Direct3D, Vulkan, Metal or OpenGL |
| **HLSL, FXC, DXBC** | Direct3D's shading language; Microsoft's legacy HLSL compiler (`d3dcompiler_47.dll`); its bytecode |
| **TDR** | Windows' Timeout Detection and Recovery: the watchdog that resets a GPU that stops answering |
| **FFT, bin, window, hop** | fast Fourier transform; one frequency slot of its output; the taper applied to a block of samples; the step between blocks |
| **onset** | the moment a note starts; **spectral flux** is the standard way to detect one |

---

## 2. Credits (who taught what)

- **Kayvon Fatahalian** (Stanford/CMU), "From Shader Code to a Teraflop: How Shader Cores Work" (SIGGRAPH course
  slides): the three ideas behind every GPU core (strip control logic, share one instruction stream over many lanes,
  interleave many groups to hide stalls).
- **AMD**, the RDNA architecture slides (2019), the RDNA performance guide, and **François Guthmann**'s "Occupancy
  explained" (GPUOpen): wave32 and wave64, single-cycle issue, register-limited occupancy, when occupancy hurts.
- **Chips and Cheese**: RDNA 4's 192 KB register file and its allocation granularity.
- **NVIDIA**, "Life of a triangle" (developer article): warps, quads, the warp scheduler.
- **Fabian Giesen**, "A trip through the Graphics Pipeline 2011", parts 4 (texture samplers) and 8 (pixel processing):
  what a texture request carries, sampler latency, cache behaviour, quads and helper pixels.
- **Emil Persson** (Avalanche), "Low-level thinking in high-level shading languages" (GDC 2013): multiply-add form,
  free input modifiers, separating scalar and vector work, explicit branch intent, shader diffs in code review.
- **Inigo Quilez**: the conditional-move myth, the 8-bit precision of hardware texture filtering, smoother texture
  filtering by remapping the sub-texel fraction, and the Shadertoy sound-input convention (`Xds3Rr`).
- **Fabrice Neyret** ("shadertoy - unofficial" blog and the `llySRh` utility shader): compile-time explosions and the
  unroll guard, the catalogue of Windows/ANGLE incompatibilities, mipmap seams from `fract` and `atan`, iMouse and
  keyboard conventions, performance philosophy.
- **Khronos**: the GLSL ES 3.00 and OpenGL ES 3.0 specifications, the WebGL 1 and 2 specifications and extensions.
- **Microsoft**: the TDR documentation.
- **Alvaro Segura** (2011, ANGLE mailing list): texture sampling inside loops forcing the Direct3D compiler to unroll.
- **Mark Jarzynski and Marc Olano**, "Hash Functions for GPU Rendering" (JCGT 2020): why the sine hash is bad.
- **Christian Sigg and Markus Hadwiger**, "Fast Third-Order Texture Filtering" (GPU Gems 2, chapter 20).
- **W3C Audio Working Group**, the Web Audio API specification (the AnalyserNode pipeline, exactly).
- **Juan Pablo Bello, Laurent Daudet, Samer Abdallah, Chris Duxbury, Mike Davies, Mark Sandler** (2005 onset tutorial),
  **Simon Dixon** ("Onset detection revisited", 2006), **Sebastian Böck, Florian Krebs, Markus Schedl** (online onset
  detection, 2012), **Sebastian Böck and Gerhard Widmer** (SuperFlux, 2013): onset detection functions and peak picking.
- **Frédéric Patin**, "Beat Detection Algorithms": the energy-ratio beat detector with a variance-adapted threshold.
- **ciphrd**, "Audio analysis for advanced music visualization": refractory time and pulse persistence for visuals.
- **Gregg Tavares** (webgl2fundamentals): precision tests on real phones.

---

## 3. How a fragment shader actually runs

### 3.1 The three ideas (Fatahalian)

A CPU core spends most of its silicon on making *one* instruction stream fast: branch predictors, out-of-order
schedulers, big caches. A GPU core throws those away and spends the area on arithmetic lanes instead. Three ideas
follow, and everything else in this report is a consequence of them:

1. **Many simple cores.** Lots of small, slow-witted cores instead of a few clever ones.
2. **One instruction stream for many lanes (SIMD).** A single decoder feeds 32 or 64 lanes the same instruction; each
   lane works on a different pixel. Hardware analogy: one conductor and a row of 32 violinists reading the same sheet,
   each playing a different note of the chord.
3. **Interleave many groups to hide stalls.** When a wave waits hundreds of cycles for memory, the core switches to
   another resident wave that is ready. Analogy: a chef with 16 pans on the stove; while one simmers, stir another.

Two corollaries matter to every shader you write. The unit of execution is the *wave*, not the pixel, so the cost of a
pixel is really the cost of its whole wave. And the machine is only fast when it has *enough independent work resident*
to cover its waits, which is limited by how many registers each wave needs.

### 3.2 This host's GPU in numbers (RDNA 4, RX 9070 XT)

| quantity | value | source |
|---|---|---|
| compute units / lanes | 64 CUs (32 WGPs), 4,096 lanes = 128 SIMD32 units | Wikipedia RDNA 4 spec table; Chips and Cheese |
| boost clock | about 2.97 GHz | spec table |
| FP32 peak | 48.7 TFLOPS counting dual-issue, so about 24.3 single-issue | spec table (4,096 x 2 x 2 x 2.97 GHz) |
| texture units / render outputs | 256 TMUs, 128 ROPs | spec table |
| memory | 16 GB GDDR6, 256-bit, 640 GB/s; 64 MB Infinity Cache (L3), 8 MB L2 | spec table |
| vector register file | 192 KB per SIMD = 1,536 VGPRs (wave32 view), up to 256 per lane | Chips and Cheese |
| max waves per SIMD | 16 | Guthmann; Chips and Cheese |
| full occupancy | at 96 or fewer VGPRs per lane (1,536 / 16) | Chips and Cheese |
| max resident pixels | 128 SIMDs x 16 waves x 32 lanes = 65,536 lanes in flight | arithmetic |
| display | 3840 x 2160 at 240 Hz (frame time 4.17 ms) | `Win32_VideoController` |
| second adapter | "AMD Radeon(TM) Graphics" (the processor's integrated GPU) | `Win32_VideoController` |

A 4K frame (8.29 M pixels) therefore fills the machine about 127 times over; at 240 Hz that is 30,000 "full machine
loads" per second. That is why per-pixel cost multiplies so brutally.

**Which adapter draws the page is not guaranteed.** Chrome changed its default WebGL `powerPreference` to `low-power` in
Chrome 80, and on Windows the browser historically took whatever adapter the operating system gave it, with
`high-performance` honoured only under conditions (context-loss handlers registered). The house avatars request
`low-power`. On a two-adapter machine, read the renderer string (section 10.2) before trusting any frame-rate number.

### 3.3 The instruction clock: wave32, wave64 and the EXEC mask

AMD's RDNA slides give the core rhythm: each SIMD32 issues one instruction every cycle, a wave32 vector instruction
completes at one per cycle, and about five cycles of dependency latency are exposed, to be filled by other waves or by
independent instructions in the same wave. A **wave64** runs each vector instruction as two wave32 halves, and when one
half's EXEC bits are all zero that half is skipped. Which width a shader gets is the driver's choice; in 2019 AMD said
pixel shaders were usually compiled as wave64 and compute and vertex shaders as wave32, with the heuristic expected to
keep changing.

What this means for you:

- **Divergence granularity on this card is probably 64 pixels** (an 8 x 8 tile, though the exact pixel layout of a wave
  is not documented). On NVIDIA it is 32 (eight quads).
- **Instruction-level parallelism matters.** AMD's own note: graphics code often has three independent streams (R, G,
  B or X, Y, Z), so writing work as vectors rather than a single long chain of dependent scalars fills the exposed
  latency for free.

### 3.4 The register file and occupancy

Every resident wave owns its registers for its whole lifetime. The register file is fixed (1,536 VGPRs per SIMD here),
so the more registers a shader needs per lane, the fewer waves fit:

`waves_per_SIMD = min(16, floor(1536 / alloc(v)))`, where `alloc(v)` rounds the per-lane VGPR count `v` up to the
allocation block (24 registers on 1,536-register parts, per Chips and Cheese).

| VGPRs the compiler needs | allocated | waves per SIMD |
|---|---|---|
| up to 96 | up to 96 | 16 (full) |
| 97 to 120 | 120 | 12 |
| 121 to 144 | 144 | 10 |
| 145 to 168 | 168 | 9 |
| 169 to 192 | 192 | 8 |
| 256 (the maximum) | 256 | 6 |

Guthmann's worked example on a 1,536-register part: a shader at 120 VGPRs fits 12 waves; trim it to 118 and you get
13 (that example ignores the block rounding, so treat the table as the realistic one). A wave64 "counts double": it
holds twice the lanes, so it consumes twice the register file per wave.

Where registers go in a typical Shadertoy-style shader: every live variable at the worst point of the program, times
its component count. A raymarcher with its `map()` inlined into a loop, carrying a position, direction, accumulated
colour, a few material values and the loop counter, easily needs 60 to 120. Long-lived arrays, big structs and large
unrolled loops push it higher. Past 256 per lane the compiler **spills** to scratch memory, which is ordinary video
memory with all its latency: a cliff, not a slope.

**When occupancy does not matter.** Occupancy exists to hide memory latency. A pure arithmetic shader (most SDF
raymarchers with procedural noise and no textures) needs only enough waves to cover the five-cycle dependency gap, so
it runs fine at modest occupancy. A shader dominated by texture or buffer reads needs many waves. And Guthmann's
warning: if a shader is already bound by memory bandwidth, more waves only thrash the caches harder.

### 3.5 Latency hiding, with Little's law

Little's law from queueing theory: the amount of work in flight equals throughput times latency. Turned into a rule of
thumb for one SIMD: to keep it issuing while each wave waits `L` cycles for a texture and then does `A` cycles of
arithmetic before its next fetch, you need about

`waves_needed ≈ 1 + L / A`

waves resident. With a memory latency of 500 cycles (Giesen quotes 400 to 800 for a texture fetch through the sampler)
and 20 arithmetic instructions between fetches, that is about 26 waves, more than the 16 slots exist, so such a shader
stalls no matter what. The remedies, in order of power: issue independent fetches together (the hardware overlaps them,
so four fetches back-to-back cost about one latency, not four), put more arithmetic between dependent fetches, and cut
registers so more waves fit.

The texture unit itself is built for this: Giesen describes sampler pipelines long enough to keep a full memory round
trip in flight per sample, fed with requests in batches (he uses 16 per batch for 2D) rather than one at a time.

### 3.6 Quads, helper lanes and derivatives

The rasterizer hands the shader core whole 2 x 2 **quads**, never single pixels, because derivatives are computed by
subtracting neighbours inside the quad: `dFdx(v)` is the right pixel's `v` minus the left pixel's (or the reverse, for
the other column), and the same vertically. NVIDIA's article describes a 32-lane warp as eight quads.

Consequences:

- **Helper lanes.** At a triangle edge, quad members outside the triangle still run, purely to supply derivatives.
  Giesen estimates 25 to 75 per cent of the shading work in edge quads is wasted this way. A full-screen pass drawn as
  one oversized triangle (the house template) has no interior edge, so it wastes nothing; a pass drawn as two triangles
  pays along the diagonal.
- **Derivatives are only defined in uniform control flow.** The GLSL ES 3.00 specification says derivatives (and the
  implicit derivatives inside `texture()`) are undefined when the pixels of a quad take different paths. In practice the
  hardware still subtracts registers, but the neighbour's register may hold garbage because the neighbour skipped the
  code that set it. Rule: take derivatives *before* the branch or loop, pass them in.
- **`discard` and early `return` do not free the lane** while its quad-mates still need it for derivatives, and they do
  not shorten the wave unless every lane in it is done.

### 3.7 Divergence, as arithmetic

Inside a wave, an `if` whose condition differs between lanes runs *both* sides, each with the non-participating lanes
masked off. Giesen's summary: in the worst case you always execute both branches of every `if`. The cost of a branch is
therefore decided per wave, and the arithmetic is unforgiving.

If each pixel independently takes an expensive branch with probability `p`, the chance that a wave of `N` lanes has to
run it is `1 - (1 - p)^N`:

| p (per pixel) | wave32 pays | wave64 pays |
|---|---|---|
| 1% | 27% | 47% |
| 3% | 62% | 86% |
| 10% | 97% | 99.9% |

A branch that is "rare" per pixel is nearly *never* rare per wave. What saves real shaders is **spatial coherence**:
neighbouring pixels usually take the same path (the sky is all sky, the object is all object), so the waves that
straddle a boundary pay double and everything else pays once. Divergence cost lives on edges.

**Loops are the same thing in time.** A wave runs a loop until its *last* lane is done, so the wave's trip count is the
maximum over its lanes, not the average. For a raymarcher, pixels near silhouettes need many steps (the ray grazes the
surface and creeps), so every wave that touches a silhouette runs to the slowest pixel's step count. Hardware analogy: a
convoy moves at the speed of its slowest truck. This is why a heatmap of step counts (section 10.4) is the single most
useful picture of where a raymarcher's time goes.

**Uniform branches are nearly free.** A condition that is the same for every lane (anything computed only from
uniforms: `iMouse.z > 0.0`, `u_style == 2`) is evaluated once on the scalar unit and the wave jumps; no masking, no
double execution. Branch on uniforms freely.

### 3.8 Budget arithmetic for this machine

The useful mental model is a budget of arithmetic operations per pixel per frame:

`ops_per_pixel ≈ (lanes x 2 x clock) / (width x height x fps)`

with the factor 2 counting a fused multiply-add as two operations. For the 9070 XT single-issue (4,096 x 2 x 2.97 GHz =
24.3 x 10^12 per second):

| canvas | refresh | pixels per second | ideal ops per pixel per frame |
|---|---|---|---|
| 3840 x 2160 | 240 Hz | 1.99 x 10^9 | about 12,200 |
| 3840 x 2160 | 144 Hz | 1.19 x 10^9 | about 20,400 |
| 3840 x 2160 | 60 Hz | 0.50 x 10^9 | about 48,900 |
| 720 x 450 (the bed at half scale) | 240 Hz | 0.078 x 10^9 | about 313,000 |

Real shaders reach perhaps a quarter to a half of ideal once divergence, latency and texture stalls are counted, so
divide by 2 to 4. A typical raymarcher at 100 steps with a 30-operation distance function is about 3,000 operations for
the march alone; that fits 4K at 60 Hz comfortably and 4K at 240 Hz only just. The house's existing choices (bed below
display resolution, avatar at 64 px with a 48-step cap) are exactly right for this arithmetic.

---

## 4. Branches, loops and arithmetic

### 4.1 Selecting a value is not a branch

Inigo Quilez's article on GPU conditionals takes apart a myth that still circulates: that `x < y ? b : c` creates a
branch and should be rewritten as `mix(c, b, step(...))`. A select compiles to a compare plus a conditional move (on AMD
`v_cndmask_b32`; in Direct3D bytecode `movc`): no jump, no pipeline flush, one or two cycles. The `step`/`mix` version
computes the same compare and then adds multiplies and adds on top, so it is *slower*. Emil Persson makes the same point
from the console side: conditional assignment has been fast on every GPU for a long time, and `sign()` or `step()` used
to emulate it is rarely justified.

Rule: write the clear conditional; the compiler emits a select for value choices. Reach for structure only when you want
to *skip work*.

### 4.2 Real branches: when they pay

A real jump only pays when (a) it skips a large amount of work and (b) most waves agree. Early exit from a raymarch
loop on a hit, skipping a shadow ray when the surface faces away from the light, skipping the whole scene for pixels a
cheap bounding test rejects: all good. Persson's HLSL advice is to state the intent (`[branch]`) so the compiler errors
if it cannot honour it instead of silently flattening; GLSL has no such attribute, so the equivalent discipline is to
check the compiled output (section 10.6) for anything you rely on.

Fabrice Neyret's version for shader artists: the problem is never the `if` itself but what is inside it. Decide inside
the branch (set a few parameters), then do the heavy shared work once after it. Picking *which* material a pixel uses
in a branch and shading once afterwards costs one shading; shading inside each branch costs as many as the wave
diverges into.

### 4.3 Loops: unrolled, dynamic, and the compile-time bill

GLSL ES 3.00 (unlike ES 1.00) allows loops with bounds that are not compile-time constants. Compilers still love to
unroll: a loop with a constant bound gets its body copied that many times, the counter replaced by constants, which
removes the per-iteration compare-and-jump and lets constants fold. Neyret points out the hidden bill: functions also do
not exist on the GPU (there is no call stack), so every call is inlined, and nested unrolled loops multiply. A 64-step
loop calling a function that contains an 8-octave noise loop becomes 512 copies of the noise body. The results are:
minutes-long compiles, browser freezes, cryptic "too many registers" errors, or a driver that gives up.

Techniques, with their trade-offs:

- **The unroll barrier.** Make the bound unknowable at compile time while keeping its runtime value:
  `for (int i = 0; i < N + min(iFrame, 0); i++)`. `iFrame` is never negative, so the bound is `N`, but the compiler
  cannot prove it. Neyret popularised this; 24 corpus shaders carry it (often as a `ZERO` macro). Cost: a few
  instructions per iteration of loop overhead, which is negligible beside a raymarch step. Benefit: compile time and code
  size proportional to one body, not `N` bodies.
- **Select inside, shade after.** Keep loop bodies small: find the closest hit inside the loop, compute normals, shadows
  and lighting after it (Neyret).
- **Explicit-LOD sampling inside loops** (section 6.4; on Windows this one is not optional).
- **When to unroll on purpose.** Short loops (4 to 8 trips) with tiny bodies, where the per-trip overhead is a large
  fraction of the body, and loops over a small constant array where unrolling turns array reads into plain registers
  (section 4.4).

### 4.4 Arrays and dynamic indexing

A register file is not addressable memory. A local array indexed by a value the compiler can resolve (an unrolled
counter) becomes ordinary registers; indexed by a runtime value, it needs special relative-addressing instructions or,
commonly, gets moved to scratch memory. Neyret calls arrays "ultra-costly": they eat registers (killing occupancy) and
big ones break compilers. In Direct3D bytecode a dynamically indexed local array becomes an "indexable temp", which is
both slow and a frequent cause of slow compiles. ANGLE also inserts index clamping on every dynamic array access, as the
WebGL specification requires (section 8.3), so each access costs a clamp too.

Rules: prefer closed forms over tables; keep constant tables small and index them with unrolled counters; never keep a
large array alive across a loop; GLSL ES 3.00 forbids indexing an array of *samplers* with anything but a constant
expression, so `iChannel[i]`-style loops need an explicit branch per channel.

### 4.5 Arithmetic habits (Persson)

Persson's talk, built on reading Radeon disassembly, boils down to "what you write is what you get" (his phrase): the
compiler only knows the semantics of floating-point operations, not your intent, and most algebraic rewrites are unsafe
for IEEE floats, so it will not make them for you. His example: with `x = 0.2`, `sqrt(0.1 * (0.2 - x))` is exactly
zero, while the algebraically equal `sqrt(0.02 - 0.1 * x)` is the square root of a tiny negative number, a NaN, because
none of those constants is exact in binary. The habits that follow:

- **Write remaps in multiply-add form.** The hardware has a fused multiply-add (one instruction for `a * b + c`). A remap
  `(x - lo) / (hi - lo)` written as `x * s + o` with `s = 1/(hi - lo)` and `o = -lo * s` folded is one instruction; the
  intuitive form is a subtract, a reciprocal and a multiply. A divide is a reciprocal plus a multiply on most hardware, so
  fold additions into the multiply.
- **Put `abs()` and negation on inputs, `clamp(x, 0, 1)` on outputs.** On AMD hardware absolute value and negate are
  free modifiers on an instruction's *inputs*, and saturation is a free modifier on its *output*. `abs` on a value that
  is returned without further use costs an extra move.
- **Separate scalar from vector work.** `normalize(v) * 50.0` computes a reciprocal square root, then a vector
  multiply, then another vector multiply; computing the scalar factor `50.0 * inversesqrt(dot(v, v))` first and
  multiplying the vector once saves two multiplies per component. The same applies to every chain of scalar factors.
- **Reuse shared sub-expressions exactly.** `length(a - b)` and `distance(a, b)` share their dot product; `distance(b,
  a)` written elsewhere may not be recognised.
- **Merge transforms.** Chains of matrix transforms collapse into one matrix computed on the host.
- **Inverse trigonometry is a smell.** If you find `acos(dot(a, b))` followed by `cos(...)`, the angle was never needed.

These are small wins individually; Persson's point is that they are free, general, and add up on every pixel.

### 4.6 The cost of special functions

From AMD's RDNA performance guide: the transcendentals (`sin`, `cos`, `sqrt`, `log`, `exp`, reciprocal) run at a
quarter of the normal rate, though RDNA can run them alongside ordinary arithmetic; `atan` and `acos` can expand into
code taking over 100 cycles; `tan` expands into three transcendentals. Two practical consequences: a `pow(x, 2.0)` is
`exp2(2 * log2(x))`, two quarter-rate operations plus a multiply, where `x * x` is one full-rate multiply; and a
polar-coordinate effect that calls `atan` per pixel per step of a loop is spending a hundred cycles per call.

---

## 5. Precision

### 5.1 What a 32-bit float can hold

A 32-bit IEEE float stores a sign, an 8-bit exponent and a 23-bit fraction with an implied leading 1, so 24 significant
bits. The gap between a number `x` and the next one up is

`ulp(x) = 2^(floor(log2 |x|) - 23)`

so the *relative* spacing is about `2^-23 ≈ 1.19 x 10^-7` (seven decimal digits). The GLSL ES specification phrases the
same thing as a relative precision of `2^-24` (half a step, the rounding error). Concrete spacings:

| x | ulp(x) | what it means |
|---|---|---|
| 1 | 1.19 x 10^-7 | colours: far finer than any display |
| 1,000 | 6.1 x 10^-5 | pixel coordinates: fine |
| 3,600 (one hour, in seconds) | 2.4 x 10^-4 s | animation time after an hour: fine for slow motion |
| 86,400 (one day) | 0.0078 s | half a 60 Hz frame: `iDate.w` near midnight |
| 345,600 (four days) | 0.031 s | two 60 Hz frames: visible stutter in time-driven motion |
| 1,000,000 | 0.0625 | integers stored in floats lose fractions entirely past 2^24 |

### 5.2 The GLSL ES 3.00 precision rules

The specification's table (section 4.5.1):

| qualifier | float range | float precision | integer range |
|---|---|---|---|
| `highp` | IEEE single: about ±2^127 | relative 2^-24 | 32-bit two's complement |
| `mediump` (minimum) | ±2^14 (16,384) | relative 2^-10 | ±2^15 |
| `lowp` (minimum) | ±2 | absolute 2^-8 | ±2^8 |

And the defaults it predeclares (section 4.5.4), which surprise people:

- **The fragment language has no default float precision.** Every fragment shader must say `precision highp float;`
  (or qualify each declaration) or it does not compile.
- **The fragment default for `int` is `mediump`.** On a phone an `int` loop counter or hash state can be 16 bits unless
  you declare `precision highp int;`. Integer hashes (PCG and friends) need `highp`.
- **`sampler2D` and `samplerCube` default to `lowp`**, and a sampler's precision sets the precision of what the lookup
  returns. On desktop this is ignored; on mobile a float texture read through a `lowp` sampler can come back clamped to
  ±2 (MDN's best-practices page reports exactly this on iOS). Declare `precision highp sampler2D;` when textures carry
  data rather than colours.
- **`sampler3D`, `sampler2DArray`, the shadow samplers and all integer samplers have no default precision at all**: a
  shader that uses a volume texture without `precision highp sampler3D;` fails to compile.
- `gl_FragCoord` is declared `highp`, but copying it into a `mediump` variable rounds it.

Precision qualifiers are hints a desktop GPU is free to ignore (it computes everything in 32 bits), which is exactly why
mediump bugs ship: they cannot be seen on the machine that wrote them. Gregg Tavares measured a Pixel 2 XL using genuine
16-bit floats for both `mediump` and `lowp`. `gl.getShaderPrecisionFormat()` reports what a device really provides (a
precision of 23 bits for MEDIUM_FLOAT means it is secretly `highp`).

### 5.3 How accurate the built-in functions are

The specification gives error bounds for a short list (section 4.5.1): add, subtract, multiply correctly rounded;
divide within 2.5 ULP; `exp`/`exp2` within `3 + 2|x|` ULP; `log`/`log2` within 3 ULP outside [0.5, 2] and an absolute
error under 2^-21 inside it; `inversesqrt` within 2 ULP; `pow` inherits from `exp2(y * log2(x))`. Everything else,
explicitly including **the trigonometric functions, has undefined precision.** That one sentence explains why the
classic `fract(sin(x) * 43758.5)` hash differs between vendors, drivers and ANGLE back ends: the hash amplifies the
low-order bits of `sin` at large arguments, which is exactly where `sin`'s error is unspecified. Jarzynski and Olano's
benchmark puts that trigonometric hash among the visibly bad ones (banding, repeated patterns); the noise report in this
same folder covers the replacement (integer hashes such as `pcg3d`).

### 5.4 Half floats, and why a 4K screen breaks `mediump`

A 16-bit float has 10 fraction bits: `ulp16(x) = 2^(floor(log2 |x|) - 10)`, maximum 65,504.

| x | ulp16(x) |
|---|---|
| 1 | 0.00098 |
| 100 | 0.0625 |
| 1,000 | 0.5 |
| 2,048 to 4,095 | 2 |

So a pixel coordinate held in a genuine 16-bit float cannot even represent pixel centres (x.5) beyond 1,024, and at 4K
it moves in two-pixel steps: everything computed from it is blocky. Hash inputs, time, and anything scaled by a large
number fall apart long before that. On this desktop card `mediump` costs nothing and saves nothing in WebGL (RDNA's
double-rate packed 16-bit math is real, AMD's guide recommends it to cut register use, but WebGL gives you no reliable
way to ask for it). Hence the house floor: `highp` always.

### 5.5 The clock that rots

Animation is usually `sin(w * t)` or `fract(rate * t)`. The phase error is about `w x ulp(t)` from the time variable
alone, before the function adds its own. After one day of uptime `ulp(t)` is 7.8 ms; for a 10 Hz shimmer (`w = 62.8`)
that is half a radian of jitter, a visible stutter. Anything that multiplies time by a large constant before hashing it
(per-frame noise seeds) degrades much sooner. The noise report's numeric probe measured the house dither losing most of
its randomness at four days of uptime. This host does run for days (the memory file on the 82 to 92 hour commit cycle).

Remedies, best first:

1. **Compute phases on the host in double precision** and pass them wrapped: `phase = (rate * t) mod 1` computed in
   JavaScript (64-bit) and uploaded as a uniform in [0, 1). The shader never sees a large number.
2. **Wrap time on the host** at a period that is a common multiple of every animation period in the shader (or make
   looping motion periodic in time so the wrap is invisible).
3. **Split time into whole seconds and fraction** (two uniforms) when a shader needs many unrelated rates; the phase of
   a rate `f` is then `fract(fract(f) * T_whole + f * T_frac)`, because `floor(f) * T_whole` is a whole number of
   cycles and drops out. Its error is about `ulp(f)` plus `ulp(fract(f) * T_whole)` cycles: small, and no longer growing
   with uptime.

### 5.6 Sound-rate time: why `mainSound` grew an integer argument

A Shadertoy sound shader is called once per audio sample. At 48 kHz the sample period is 20.8 µs, but `ulp(150 s)` is
15.3 µs, so after two and a half minutes a float time can barely tell adjacent samples apart. Worse, the phase of a
4 kHz tone at t = 150 s is 600,000 cycles, where the float spacing is 0.0625 of a cycle: a 22-degree random phase error
on every sample, which is audible as noise and distortion. That is why Shadertoy's newer entry point passes the integer
sample index as well as the time (`vec2 mainSound(int samp, float time)`, see `4djSRW/sound.glsl:20` and
`4sSSWz/sound.glsl:288`), and why the house runtime derives its time from an integer sample count
(`toy-runtime.js:332-333`).

The exact-phase recipe for a stateless sound shader: split the integer index `k` into whole seconds and a remainder,
`q = k / sr` and `r = k - q * sr` (integers), then

`phase(f) = fract( fract(fract(f) * q) + f * r / sr )`

It works because `f * k / sr = f * q + f * r / sr`, and `floor(f) * q` is a whole number of cycles. Every product stays
small: `fract(f) * q` is at most 180 for three minutes of audio, and `f * r / sr` is at most `f`. I checked it in a
float32 simulation on the CPU (numpy, 20,000 random sample indices over 180 s at 48 kHz): for a 4 kHz tone the naive
form's worst phase error was 0.06 of a cycle (22 degrees), the split form's 0.0004 (0.14 degrees); for 440 Hz, 0.0067
against 0.000015. The split form's error is about `ulp(f)` cycles and does not grow with the song position. (The
frequency itself is rounded to float32, a tuning offset of at most 0.00012 Hz at 4 kHz, which no one can hear. A phase
*accumulator* is the usual audio answer, but a fragment shader has no state between samples, so the phase must be
computed in closed form.)

### 5.7 Storage precision: the formats a pass writes into

What a pass can store depends on its render target, and each format fails in its own way:

| target | bits | precision near 1.0 | fails as |
|---|---|---|---|
| RGBA8 (UNORM) | 8 per channel | 1/255 | trails that never fade, banding in slow fades |
| RGBA16F (half) | 16 per channel | about 0.001 | positions jitter past 1,024; tiny increments vanish |
| RGBA32F | 32 per channel | 1.2 x 10^-7 | effectively exact for visual state; 2x the bandwidth of 16F |

**The 8-bit decay stall, derived.** A feedback pass multiplies the stored value by `k` each frame and writes it back,
rounded to the nearest of 255 levels. A stored byte `b` stops changing when the decrement is less than half a step:
`(1 - k) * b < 0.5`, so the largest stuck level is about `ceil(0.5 / (1 - k)) - 1`, one level higher when the product
lands exactly on a half and the hardware rounds it up (with `k = 0.98` stored as the float 0.98000002, byte 25 lands
just above 24.5). For `k = 0.98` that is byte 24 or 25 (about 10 per cent grey); for `0.99`, about byte 50; for `0.95`,
about byte 10. On screen: a ghost of every trail stays forever as a dim haze.
Fixes: subtract a small constant as well as multiplying (`max(v * k - 1/255, 0)`), add blue-noise dither before the
write, or use a 16F target.

**The half-float equivalent** is harmless for ordinary decay (the stall needs `k` above about 0.9995) but bites
accumulation: adding a small increment `d` to a value `v` does nothing once `d < ulp16(v) / 2`, which is between
`v / 4096` and `v / 2048`. An exponential average with weight 0.01 therefore stops converging when it is within roughly
2 to 5 per cent of its target (1 per cent of the remaining gap has fallen under half a step). Positions stored in 16F
jitter by the ulp table above.

**Frame-rate independence.** A per-frame factor `k` tuned at 60 fps means "keep `k^60` per second". To get the same
look at any frame rate, derive the per-frame factor from a per-second one: `k_frame = k_second ^ dt`, or equivalently
`exp(dt * ln k_second)`. Likewise a smoothing weight `alpha = 1 - exp(-dt / tau)` for a time constant `tau` in seconds.
On this 240 Hz display a corpus shader that uses a bare per-frame factor decays four times faster than its author saw.

### 5.8 NaN and infinity

The specification lets an implementation flush tiny (subnormal) values to zero, does not require NaNs to be produced,
and does not require operations on a NaN to return a NaN. In practice desktop GPUs produce and propagate them, and the
sources are always the same: `sqrt` or `log` of a negative, `log(0)` (negative infinity), `pow` with a negative base,
`normalize` of a zero vector (0/0), `atan(0, 0)`, `0 * inf`, `inf - inf`, `acos` of a dot product that rounding pushed to
1.0000001.

Why it matters more in this house than in a still image: **NaN is contagious in feedback.** One pixel's NaN gets blurred
into its neighbours by the next frame's filtering, which makes them NaN, and the black (or white) blob grows forever
because no arithmetic ever turns NaN back into a number. Neyret's catalogue adds the portability twist: `clamp(NaN, 0, 1)`
came out 0 on Linux and 1 on Windows/ANGLE, because IEEE-2008 `min`/`max` return the non-NaN operand and the two
compilers emitted `min` and `max` in different orders. Persson notes that the Direct3D compiler may assume NaN never
happens and optimise accordingly, which can also delete a hand-written NaN test.

Rules: prevent at the source (the `safe*` primitives in section 14); in any pass that writes a feedback buffer, guard
every normalise, divide, root and power; as a last line of defence, replace non-finite values before the write (the
test `abs(x) <= 3.4e38` is false for both NaN and infinity) and accept that you must confirm on the target that the
compiler kept it.

### 5.9 Integers and the float-integer seam

- **`%` is undefined when either operand is negative** (GLSL ES 3.00, section 5.9, and the rounding of integer division
  is explicitly left undefined too). Neyret measured `-3 % 4` giving 1 on OpenGL and -3 on Windows/ANGLE. Any tiling or
  wrap that can see negative coordinates needs a floor-modulo written out.
- `int(x)` truncates toward zero, so `int(-0.5)` is 0, not -1; use `int(floor(x))` for cell indices.
- `round(x)` may be implemented as round-half-even (the specification allows it): `round(2.5)` can be 2. Use
  `floor(x + 0.5)` when ties matter.
- Float `mod(x, y)` is defined as `x - y * floor(x / y)` and takes the sign of `y`, so it is safe for negatives, but
  the divide's rounding can make `mod(33.0, 33.0)` return 33 instead of 0 (Neyret saw this for about one value in ten
  in that range). For exact integer-valued periodicity, use integers.
- There are no implicit conversions: `float a = 1;` and `2 * x` with a float `x` are compile errors.

---

## 6. Textures

### 6.1 What a texture sample costs

A texture lookup is not a memory read; it is a request to a fixed-function unit. Giesen's anatomy: a 2D request carries
the coordinates and four derivatives (six floats); the sampler computes the level of detail, the addresses of the
needed texels, fetches them through a small dedicated cache (he cites 4 to 8 KB per sampler for that hardware
generation), converts and filters them, and returns the result hundreds of cycles later. With mipmapping on realistic
content he observed about **1.25 cache misses per bilinear request**, almost independent of cache size, because nearby
pixels reuse texels; point-sampled minified textures miss about once per texel. Filtering costs scale with the texel
footprint:

- nearest: 1 texel;
- bilinear: 4 texels, the full-rate case;
- trilinear: 2 bilinear lookups (two mip levels) plus a blend, so roughly half rate;
- anisotropic: several trilinear lookups along the stretched direction.

Wide formats cost more: a 32-bit-per-channel RGBA texel is 16 bytes, so caches hold a quarter as many texels as RGBA8
and many GPUs filter such formats at reduced rate. RDNA 4 has four texture units per CU (256 on the card), shared by
everything resident on that CU.

**Dependent reads are the latency killer.** A fetch whose coordinate depends on the result of a previous fetch
(domain-warped texture noise, a lookup table read with a texture-derived index) cannot be issued until the first one
returns; chains of them serialise the full latency. Independent fetches overlap.

**Recompute can beat fetch.** Neyret's performance post: with so many arithmetic units sharing small caches,
recomputing a value is often faster than reading it back from a texture, even a cached one.

### 6.2 Mipmaps and the level-of-detail formula

The OpenGL ES 3.0 specification (section 3.8.10) defines the level the hardware picks. With `u, v` the texture
coordinates in texels (normalised coordinates times the texture size):

`rho = max( sqrt( (du/dx)^2 + (dv/dx)^2 ), sqrt( (du/dy)^2 + (dv/dy)^2 ) )`

`lambda = log2(rho) + bias`, clamped to the texture's LOD range.

In words: how many texels does one screen pixel step across, in the worse of the two screen directions? `lambda <= 0`
means magnified (one texel covers several pixels; the magnification filter applies). `lambda = 1` means each pixel
spans two texels, so level 1 (half size) is used, and so on. The `bias` argument of `texture()` shifts it; `textureLod`
replaces it; `textureGrad` lets you supply the four derivatives yourself.

Why mipmaps matter for speed as well as quality: without them, a minified texture is sampled at scattered texels, so
every pixel misses the cache and the image shimmers (aliasing). MDN's best-practice page puts the memory cost at about
30 per cent extra and calls the cache improvement major. `generateMipmap` only works on formats that are both
colour-renderable and filterable.

### 6.3 Seams: `fract`, `atan` and the derivative jump

The most recognisable texture bug in shader art: a thin line of wrong colour along every tile boundary of a repeating
texture, or along one ray of a polar effect. Cause: the coordinate passed to `texture()` jumps from 0.99 to 0.0 between
two adjacent pixels (`fract(uv * 4.0)`), or from π to -π (`atan`). The quad's derivative sees a jump of nearly a whole
texture width, `rho` becomes enormous, the hardware picks the smallest mip level, and that quad samples the texture's
average colour. Because derivatives are computed per 2 x 2 quad, the line is one or two pixels wide, and it can appear
or vanish when the window is resized (the seam falls inside a quad or between two).

Fixes (Neyret's classical corner cases, in my words):

- Sample with `textureGrad(tex, fract(uv), dFdx(uv), dFdy(uv))`: the position wraps, but the derivatives come from the
  continuous coordinate, so the LOD never sees the jump.
- Or compute the LOD yourself from the continuous coordinate (section 14, `mipLevel`) and use `textureLod`.
- For angles, measure the derivative of the angle and, where its magnitude exceeds π, replace it by its distance to
  2π (the jump is fake, the true change is small).

### 6.4 Derivatives, control flow, and `texture()` inside loops

Two rules, one from the specification and one from the Direct3D compiler, point the same way:

1. Implicit derivatives (`texture()` without `Lod` or `Grad`) are undefined in non-uniform control flow. Inside a
   raymarch loop, neighbouring pixels are on different iterations, so a mipmapped `texture()` there picks garbage levels:
   speckled sparkles at random pixels.
2. FXC treats a derivative-using sample instruction inside a loop whose trip count varies as a reason to try to unroll
   the loop (warning X3570, "attempting to unroll the loop"), and fails or crawls if it cannot. Alvaro Segura reported
   in 2011 that rewriting the in-loop lookups to an explicit-LOD form took a WebGL application's compile from more than a
   minute (with repeated browser timeout alerts) to a couple of seconds. Neyret's compatibility notes still recommend
   `texelFetch` or `textureLod` inside non-unrollable loops on Windows/ANGLE.

So inside any loop or data-dependent branch: `textureLod` (with a LOD computed outside), `textureGrad` (with gradients
computed outside), or `texelFetch`. The corpus count: 83 shaders already use `textureLod`, only 2 use `textureGrad`, and
my approximate scan finds 50 that still call `texture()` inside a loop body (for example `4slGz4`, `4dSGW1`, `7dyyRy`,
`DtjSWh`); these are the ones most likely to compile slowly or sparkle on Windows.

### 6.5 Texel centres, `texelFetch`, and the 8-bit secret of bilinear filtering

- **Texel centres** sit at integer + 0.5 in texel units, so in normalised coordinates texel `i` of `n` is at
  `(i + 0.5) / n`. A lookup at `i / n` lands on the border between two texels and blends them under linear filtering.
  Neyret's warning: switching the sampler to nearest only hides an imprecise index; the index formula must be exact.
- **`texelFetch(sampler, ivec2, lod)`** reads one texel by integer index: no filtering, no wrapping, no derivatives, and
  no LOD selection. It is the right tool for data textures (keyboard, audio, state stored in buffers, lookup tables).
  Out-of-range indices return zero in WebGL2 (the specification requires a defined, testable result), never someone
  else's memory.
- **Hardware bilinear weights have only 8 fractional bits.** Inigo Quilez's article on hardware interpolation: the
  filter's blend weight is quantised to 1/256 of a texel, so a strongly magnified smooth texture (a heightfield, a lookup
  table, a 512-texel spectrum stretched across 3,840 pixels, 7.5 pixels per texel) becomes a staircase of 256 steps
  between texels, and anything derived from its slope (normals, lighting) shows the steps loudly. The fix is to fetch
  the four texels with `texelFetch` and blend in full float precision: four fetches instead of one.
- **Smoother magnification for one fetch.** Quilez's improved filtering: map the sub-texel fraction through a smooth
  curve (he uses the quintic `x^3 (6x^2 - 15x + 10)`, whose first and second derivatives vanish at the ends) before the
  hardware lookup, so the interpolant has continuous slope at texel boundaries. Cost: a little arithmetic and one fetch.
  Caveat: the remapped coordinate has distorted derivatives, so pair it with `textureGrad` using the original
  coordinate's derivatives, or with `textureLod`.
- **Bicubic in four fetches.** Sigg and Hadwiger (GPU Gems 2, chapter 20) rewrite the 16-tap cubic B-spline filter as
  four weighted *bilinear* lookups at cleverly offset positions, letting the hardware do the inner blends: 4 fetches
  instead of 16 in 2D, 8 instead of 64 in 3D. The 8-bit weight caveat above still applies to the inner blends.

### 6.6 sRGB textures

If a texture's internal format is sRGB (`SRGB8_ALPHA8`), the hardware converts to linear light as part of filtering;
the specification prefers conversion before filtering and allows after. Filtering in linear light is correct; filtering
sRGB-encoded bytes darkens edges between bright and dark texels. Shadertoy's per-channel `srgb` switch requests this
decode. In the house corpus **no input sets `srgb` to true** (all 852 channel inputs have it false), so
virtually every Shadertoy shader treats texture bytes as display-ready values; the colour report in this folder covers
the linear pipeline.

### 6.7 Why a texture reads black: completeness

A texture the GL considers *incomplete* returns (0, 0, 0, 1) from every lookup (OpenGL ES 3.0, section 3.8.13; WebGL2
requires the same). The common ways to make one:

- a minification filter that needs mipmaps (`*_MIPMAP_*`) on a texture whose mip chain was never generated;
- `LINEAR` filtering on a 32-bit float texture without the `OES_texture_float_linear` extension enabled (RGBA32F is not
  filterable in core WebGL2; RGBA16F is);
- integer textures with any filter other than `NEAREST`.

On screen: a pass that renders pure black in one browser or machine and correct in another. The house runtime avoids
the second trap by only choosing RGBA32F buffers when linear filtering of them is available (`toy-runtime.js:618-621`).

### 6.8 What WebGL2 does not have

WebGL2 is OpenGL ES 3.0, so it lacks `textureGather` (ES 3.1; AMD's advice to use Gather4 for single-channel reads does
not apply), compute shaders, storage buffers and image load/store. Workarounds live in fragment passes; true compute is
WebGPU's territory.

### 6.9 Bandwidth arithmetic for full-screen buffers

| format | one 4K buffer | read + write per frame at 60 Hz | at 240 Hz |
|---|---|---|---|
| RGBA32F | 132.7 MB | 15.9 GB/s | 63.7 GB/s |
| RGBA16F | 66.4 MB | 8.0 GB/s | 31.9 GB/s |
| RGBA8 | 33.2 MB | 4.0 GB/s | 15.9 GB/s |

Against 640 GB/s of memory bandwidth, one 32F buffer at 4K/240 is 10 per cent of the card before any filtering taps.
Four Shadertoy-style buffers, each read with a few taps, approach half the card. A 4K 32F buffer is also twice the size
of the 64 MB Infinity Cache, so it streams from memory every frame. Lessons: run simulation buffers at lower resolution
than the display, store colour history in 16F, and store only state that needs 32 bits in 32F.

---

## 7. Float render targets and multipass

### 7.1 The extensions, exactly

- **`EXT_color_buffer_float`** makes R16F, RG16F, RGBA16F, R32F, RG32F, RGBA32F and R11F_G11F_B10F renderable in
  WebGL2. RGB16F (three channels) is *not*. Values written are not clamped to [0, 1]. Read-back uses `RGBA`/`FLOAT`.
- **`OES_texture_float_linear`** allows linear filtering (and mipmapped filtering) of 32-bit float textures.
- **`EXT_float_blend`** is required to *blend* into 32-bit float targets; 16-bit float blending comes with 16-bit
  rendering (MDN's best-practices page).
- Desktop-class GPUs support all of these; many phones support only half-float rendering.

### 7.2 Feedback loops are an error in WebGL

OpenGL ES calls rendering into a texture while sampling the same texture undefined behaviour. WebGL turns it into an
`INVALID_OPERATION` error at draw time, so the draw simply does not happen. Hence **ping-pong**: two textures, read one,
write the other, swap each frame. Two consequences people forget: a pixel a pass does not write (because of `discard`,
or a scissor) keeps whatever the *write* target held, which is the frame before last; and both textures must be cleared
and resized together.

### 7.3 Shadertoy's multipass model

Buffers A to D run in that fixed order each frame, then the Image pass. A pass reading an earlier pass sees this
frame's result; reading itself or a later pass, it sees the previous frame (the house runtime labels every read this
way: `stats().reads`). Neyret's notes: buffers are 32-bit float, unclamped, cleared to zero at start, not
re-initialised on resize, and media textures may take several frames to arrive. The Cube A pass renders six faces of
1,024 x 1,024 in half float. Initialisation belongs under `iFrame == 0`, not a time test, because Shadertoy's preview
thumbnails start at `iTime = 10` with `iFrame = 0`.

### 7.4 Choosing formats for house passes

| what the pass stores | format | why |
|---|---|---|
| simulation state (positions, velocities, accumulated time) | RGBA32F | 16F jitter and stalls (section 5.7) |
| colour history (motion blur, trails, temporal accumulation) | RGBA16F | enough precision, half the bandwidth, always filterable |
| final LDR colour, masks | RGBA8 | display precision; dither before writing smooth gradients |

### 7.5 Reading results back without stalling

`readPixels` into a JavaScript array forces the CPU to wait for the GPU to finish everything queued. MDN's pattern is
asynchronous: read into a pixel-pack buffer, insert a fence, poll the fence on later frames, then copy out. The house's
deterministic stills already run off-screen on SwiftShader, where this does not matter; any live probe that reads
pixels from the real GPU should use the fence pattern.

---

## 8. ANGLE on Direct3D 11: how Chrome on Windows runs a shader

### 8.1 The chain

On Windows, Chrome's WebGL has for years defaulted to ANGLE's Direct3D 11 back end (the renderer string ends in
`Direct3D11 vs_5_0 ps_5_0, D3D11`). The back end is the browser's choice and can change between versions (the house
checks ran Chrome 155), so confirm it from the renderer string on this machine before relying on any of this section.
The journey of one fragment shader:

1. **ANGLE's validator and translator** parse GLSL ES 3.00, enforce WebGL's extra rules, and rewrite the tree: clamp
   every dynamic array index, zero-initialise variables, apply driver-bug workarounds.
2. **Translation to HLSL**, Direct3D's language.
3. **FXC** (`d3dcompiler_47.dll`, present on this host) compiles HLSL to DXBC bytecode, with aggressive optimisation and
   unrolling.
4. **The AMD driver** compiles DXBC to RDNA machine code.

Fabrice Neyret describes the same pipeline from the Shadertoy side: driver workarounds, then GLSL to HLSL, then several
rewrite and optimisation passes. Every stage is a place where your shader's meaning or cost can change.

### 8.2 Compile time is a first-class cost

FXC is slow on big unrolled code. Measured cases: a GitHub issue on the OneJS project recorded the first draw of a large
interpreter-loop shader blocking Chrome's main thread for **7.55 seconds** on ANGLE D3D11, against 84 ms for an ordinary
shader and 0.1 ms for the second draw (the compiled program was cached); Segura's 2011 report went from over a minute to
a couple of seconds by removing gradient samples from loops. Remedies:

- **`KHR_parallel_shader_compile`**: compile and link, then poll `COMPLETION_STATUS_KHR` on later frames instead of
  blocking (MDN's best-practices page). The CSS fallback stays up until the program is ready, which matches the house's
  "the fallback never disappears early" floor.
- **Check only the link status**, and only if linking failed: the ES 3.0 rules make the linker report every error, and
  querying compile status forces a synchronous round trip.
- **Shrink what FXC sees:** unroll barriers, explicit-LOD sampling in loops, small loop bodies, few arrays.

### 8.3 What WebGL guarantees that native GL does not

From the WebGL specifications:

- **Local and global variables start at zero** (0.0, `vec4(0.0)`, 0, false). Native GLSL ES leaves them undefined.
  Neyret still advises always initialising, including `out` parameters: other platforms (iOS) produced garbage.
- **Out-of-range array reads** return a value from the program's own storage or zero; writes are dropped or land in the
  program's own storage. Never another process's memory. On Windows/ANGLE, Neyret observed "strange non-local side
  effects" from out-of-range accesses, consistent with "lands in the program's own storage".
- **Feedback loops** are draw-time errors (section 7.2).
- **Identifiers starting with `webgl_` or `_webgl_` are reserved**; WebGL2 allows tokens up to 1,024 characters; struct
  nesting is limited (WebGL 1 requires support for at least four levels).
- **An incomplete texture or undefined texel fetch returns zero or (0, 0, 0, 1)**, never garbage.

### 8.4 Semantic differences seen on Windows/ANGLE

Neyret's catalogue, the ones that bite:

| construct | OpenGL (Linux, older macOS) | Windows / ANGLE |
|---|---|---|
| `-3 % 4` | 1 | -3 (and the specification says undefined) |
| `int(x)` vs `int(floor(x))` for negative `x` | sometimes equal | different |
| `clamp(NaN, 0., 1.)` | 0 | 1 |
| `x = (x = y) * x` (assignment inside an expression) | one evaluation order | possibly the other |
| out-of-range array access | clamped | odd non-local effects |
| a `return` inside only one branch of a function | fine | early WebGL2 compilers crashed or miscompiled |

### 8.5 Seeing what the translator did

- **The renderer string.** `gl.getExtension('WEBGL_debug_renderer_info')` then `UNMASKED_RENDERER_WEBGL` gives the full
  ANGLE string: vendor, adapter, back end. It is the only proof of which GPU and which compiler ran the page.
- **The translated source.** `WEBGL_debug_shaders.getTranslatedShaderSource()` returns ANGLE's output (the HLSL on
  this host), but browsers restrict it to privileged contexts for privacy, so it is a developer-machine tool.
- **Forcing another back end** is a Chrome command-line flag (`--use-angle=...`); Neyret's `llySRh` header lists the
  forms. Not to be run here; noted for completeness.

### 8.6 The watchdog: TDR and context loss

Windows' documentation: the GPU scheduler gives a submitted task about **two seconds** to finish or be pre-empted;
otherwise the driver is reset, every application loses its device, and the user sees "Display driver stopped responding
and has recovered". After **five or more hangs within one minute**, the sixth bug-checks the machine (stop code 0x117).
For a browser this means a `webglcontextlost` event at best; Chrome also blocks WebGL for a page that keeps losing its
context.

Implications for this house, with its documented AMD TDR history:

- A per-pixel loop with no constant ceiling is a machine-level hazard: a shader that hangs only under some input (a
  degenerate ray, a NaN that never satisfies the exit test) can fire repeatedly once per draw.
- Cost of one draw is roughly `pixels x per-pixel cost`. At 4K, a shader that needs one million operations per pixel is
  8.3 x 10^12 operations, about a third of a second on this card at ideal speed and seconds in practice: inside TDR
  range. Offline high-resolution renders must be split into tiles (scissor rectangles), each a separate submission.
- Every loop in a house module has a constant upper bound (the house floor already says so) and a finite exit even when
  its inputs are NaN (`for` with a counter, never `while (d > eps)` alone).

---

## 9. Compile-time pitfalls: a checklist

| symptom | cause | fix |
|---|---|---|
| shader fails before line 1 | anything (even a blank line from a JavaScript template string) before `#version 300 es` | the directive must be the first line, followed by a newline |
| "no precision specified for (float)" | fragment shaders have no default float precision | `precision highp float;` in the template |
| "no precision specified" on a `sampler3D` or `isampler2D` | those sampler types have no default precision | `precision highp sampler3D;` etc. |
| "cannot convert from 'const int' to 'float'" | no implicit conversions in GLSL ES | write `1.0`, or construct: `float(i)` |
| `texture2D`, `gl_FragColor` undeclared | ES 1.00 names removed in 3.00 | `texture`, and `out vec4 outColor;` |
| "'sample'/'filter'/'input'/'output'/'common'/'half'/'active' : reserved word" | GLSL reserves them for the future | rename the variable |
| global initialised from a uniform fails | global initialisers must be constant expressions | initialise inside `main` |
| "index expression must be constant" on samplers | sampler arrays only accept constant indices | branch per channel |
| `?:` on a struct or array fails | not allowed by ESSL (house trap list) | `if`/`else` |
| recursion fails | static and dynamic recursion are forbidden | rewrite as a loop with an explicit small stack |
| compile takes seconds to minutes, tab freezes | unrolled loops times inlined functions; `texture()` in loops on D3D | unroll barrier, explicit-LOD sampling, smaller bodies, parallel compile |
| hundreds of errors with no useful hint | register exhaustion after unrolling (Neyret) | as above; fewer live variables and arrays |
| red tab, no message, on Shadertoy | a missing `}` pushing the error into the hidden footer, or a `#define`d `mainImage` (Neyret) | the house runtime maps errors back to pass lines (`mappedLog`) |
| syntax error on a line with only a comment | a `$`, quote, `@` or non-ASCII character inside a `#define` comment | remove the character |
| link error about precision mismatch | a uniform declared with different precision in two stages | match precisions |

---

## 10. Profiling without GPU tools

### 10.1 What you cannot see, and why frame rate lies

Without vendor tools (Radeon GPU Profiler, PIX, Nsight) you cannot see occupancy, cache hit rates or per-instruction
stalls. And frame rate from `requestAnimationFrame` is quantised by vertical sync: on this 240 Hz display anything that
finishes in under 4.17 ms reads as 240 fps, so 0.3 ms and 4 ms of GPU work look identical. Note too that browsers coarsen
`performance.now()` for security (to 100 µs or so without cross-origin isolation).

The house rule stands: report no fps you did not observe from a visible window or a trace, and a blind seat measures
structure, not speed.

### 10.2 First, identify the machine

Read the full renderer string (section 8.5). On this host it decides between the discrete RX 9070 XT, the integrated
Radeon, and SwiftShader, three machines that differ by orders of magnitude in speed and differ in compiler.

### 10.3 Experiments that need nothing but a clock

- **The resolution test.** Render at full size, then with each dimension halved. If GPU time drops to about a quarter,
  the pass is bound by per-pixel work (almost always, for full-screen shaders). If it barely moves, the cost is
  elsewhere (CPU, uploads, synchronisation).
- **Amplify until it shows.** To defeat vsync quantisation, draw the pass `n` times per frame (into an off-screen target)
  and raise `n` until the frame rate drops below the refresh rate; then GPU time per draw is about
  `frame_time / n`. Keep each frame's total far below the TDR limit.
- **Ablation (bisection).** Replace parts with constants and measure the difference: return a constant from `map()`,
  remove the shadow pass, halve the step cap. The part whose removal saves the most is the target.
- **Timer queries where the browser allows them.** `EXT_disjoint_timer_query_webgl2` brackets draws with
  `TIME_ELAPSED_EXT` queries whose results arrive a frame or more later; discard any result taken while
  `GPU_DISJOINT_EXT` was set. Browsers withdrew GPU timer queries for a period over timing-attack concerns (the 2018
  "GLitch" research among them); Chrome has since exposed them again in some configurations, and Firefox has not
  shipped the WebGL2 variant. Always feature-test.
- **Compile timing.** Time from `linkProgram` to `COMPLETION_STATUS_KHR` true (or to the first draw's return) catches
  FXC blow-ups (section 8.2).

### 10.4 Make the cost visible: heatmaps

The most valuable picture is the shader drawing its own cost. Count loop trips, texture fetches or branch entries in a
variable and output `heat(count / budget)` instead of the colour:

- **step heatmap** for raymarchers: silhouettes and grazing floors glow; that is where waves stall (section 3.7);
- **fetch heatmap** for texture-heavy passes;
- **branch map**: colour pixels by which branch they took; overlay an 8 x 8 grid to judge how many 64-lane waves
  straddle the boundary;
- **range scope**: show NaN, infinity, negatives and values above 1 in loud colours (section 14's `rangeScope`); one
  frame of this finds most black-blob bugs;
- **mip-level map**: colour by `lambda` to see where textures are minified, magnified, or hitting the seam bug.

These are cheap to add as a bench mode and run perfectly on SwiftShader: the counts are deterministic even when the
speed is not.

### 10.5 Static cost estimates

Before anything runs, a module's cost class can be read from the source: loop bounds times the work per trip, the count
of texture fetches (and dependent chains), the count of transcendentals (quarter rate) and inverse trig (100+ cycles).
This is what the house header's `cost` field should carry (`per-step`, with the bound).

### 10.6 Offline compilation: the vendor compiler without the GPU

AMD's **Radeon GPU Analyzer (RGA)** is an offline compiler: in its `vk-offline` mode it compiles GLSL (through Khronos'
glslang) for a chosen target, including **gfx1201, this card's RDNA 4 chip**, and reports register use (VGPRs, SGPRs,
spills) and the machine-code listing, with a "live VGPR" view showing where register pressure peaks. It never executes
anything on a GPU. That makes it the right tool for this host: the one way to learn a house module's real register
count and occupancy class with zero driver risk. A Shadertoy-style fragment needs a small wrapper to become Vulkan GLSL
(`#version 450`, explicit locations, uniforms in a block). Persson's practice at Avalanche is the model for using it:
attach a per-shader instruction-and-register diff to every code review, so a change that silently doubles a shader's
cost is caught when it is made. (RGA is a download from GPUOpen; installing it is Daniel's call.)

---

## 11. Shadertoy input conventions

### 11.1 The uniforms

| uniform | type | meaning |
|---|---|---|
| `iResolution` | vec3 | viewport in pixels; z is pixel aspect (1.0) |
| `iTime` | float | seconds since start |
| `iTimeDelta` | float | seconds since the previous frame |
| `iFrameRate` | float | frames per second |
| `iFrame` | int | frame counter, 0 on the first frame |
| `iMouse` | vec4 | see 11.4 |
| `iDate` | vec4 | year, month (0-based), day, seconds since midnight |
| `iChannel0..3` | sampler2D / samplerCube / sampler3D | the four inputs |
| `iChannelResolution[4]` | vec3 | size of each input; 0 until it has loaded |
| `iChannelTime[4]` | float | playback time of a video or sound input |
| `iSampleRate` | float | the audio sample rate (typically 44,100 or 48,000) |

`fragCoord` is the pixel centre (integer + 0.5), origin bottom-left. `fragColor` must be fully written; Neyret's
standing advice is to initialise it even when it "seems to work".

### 11.2 Per-channel sampler settings

Each input carries `filter` (nearest, linear, mipmap), `wrap` (clamp, repeat), `vflip` (upload the image flipped so
uv (0, 0) is its bottom-left corner as you see it) and `srgb` (decode to linear on sampling), plus an `internal` format
word. What the corpus actually uses (all 852 inputs, `meta.json` sampler fields):

| input kind | most common setting |
|---|---|
| buffer | linear / clamp (339), nearest / clamp (81); 12 use mipmap, which costs a mip build of a float buffer every frame |
| texture | mipmap / repeat (210 across both vflip settings) |
| music, musicstream | linear / clamp (44) |
| keyboard | linear / clamp (31), nearest (9) |
| any kind with `srgb: true` | none |

A keyboard or audio texture read with `texture()` at a non-centre coordinate under linear filtering blends neighbouring
keys, rows or bins; this is why the reliable idiom is `texelFetch`.

### 11.3 The keyboard texture

A 256 x 3 single-channel texture; the value is in `.x`, 0 or 1 (stored as a byte):

- **row 0**: the key is down now;
- **row 1**: the key went down this frame (true for exactly one frame);
- **row 2**: toggle state, flipping on each press.

The column is the browser's legacy `keyCode`: letters are their uppercase ASCII codes (A = 65), digits 48 to 57,
space 32, arrows 37 (left) to 40 (down), shift 16, control 17, alt 18. Read with `texelFetch(kb, ivec2(code, row), 0)`.
Neyret's utility shader defines exactly these three readers and the modifier keys (`llySRh/image.glsl:168-175`); the
house runtime implements the same layout (`toy-runtime.js:494-500`).

### 11.4 The mouse

`iMouse.xy` is the current position while a button is held (and the last position after release). `abs(iMouse.zw)` is
where the press started. The signs carry the button state: `z > 0` while held, `w > 0` only on the frame of the click,
`z < 0` after release (Neyret's macros, `llySRh/image.glsl:182-184`). At start-up, and in Shadertoy's thumbnails, all
four are zero, which is neither "pressed" nor "released": test for that case explicitly and show a demo state, or the
thumbnail is the boring corner of the parameter space.

### 11.5 The audio input texture

A music, music-stream or microphone input arrives as a **512 x 2** texture:

- **row 0, the spectrum**: 512 magnitudes, each a byte produced by the browser's analyser (section 12.2), so the value
  is *decibels mapped linearly to 0..1*, not amplitude. The 512 texels span 0 to a quarter of the sample rate: Inigo
  Quilez's note in `Xds3Rr/image.glsl:26` gives 48 kHz / 4 across 512 texels, about 23 Hz per texel. So texel
  `i = 512 x 4 x f / sr`, and in normalised coordinates `u = 4 f / sr`.
- **row 1, the waveform**: the most recent 512 samples, one texel per mono sample (`Xds3Rr/image.glsl:29`), stored as
  bytes where 128 is silence (the Web Audio byte mapping, section 12.2).

With `texture()`, row 0 is at `v = 0.25` and row 1 at `v = 0.75` (texel centres of a two-texel-high image), the form
`4slGz4/image.glsl:85,114` uses; with `texelFetch`, `ivec2(i, 0)` and `ivec2(i, 1)`.

Practical notes:

- Never mipmap this texture: level 1 averages the spectrum row with the waveform row.
- Byte quantisation of the spectrum is 70 dB / 255 = 0.27 dB per step at the default analyser range: fine for display,
  coarse for differences (onset detection on bytes is noisy).
- Browsers block audio autoplay until the user interacts. Neyret detects a blocked stream by comparing
  `iChannelResolution` (already set) with `textureSize` (still 1 x 1); `llySRh/image.glsl:281`.
- Shadertoy's analyser smoothing setting is not documented. The house runtime passes through whatever the host analyser
  produced (`setAudio`), which is the right design: smoothing belongs to the host, explicitly (section 12.5).

### 11.6 Sound output shaders

A shader that defines `vec2 mainSound(int samp, float time)` (or the older `vec2 mainSound(float time)`) is a sound
generator: it returns the left and right amplitudes in [-1, 1] for the sample at that index and time, at the rate
`iSampleRate`. Shadertoy renders the sound ahead of playback, for a fixed length (commonly cited as 180 seconds), so a
sound shader cannot react to the mouse, the keyboard or the image passes. Hardware analogy: 180 s at 48 kHz is 8.64
million samples, almost exactly one 4K frame of pixels (8.29 million), and that is how the GPU sees it: one very large
image whose pixels are audio samples. Precision is the craft here (section 5.6). The house runtime compiles sound passes
but never plays them (`stats().unsupported`).

### 11.7 Smaller conventions that save hours

- Initialise on `iFrame == 0`, and re-initialise when `iResolution` changes (store the previous resolution in a buffer
  texel and compare).
- A texture's arrival is `iChannelResolution[i].x > 0` (`llySRh/image.glsl:187`); loads are asynchronous and can take
  many frames.
- Use `iChannelTime` for video-synchronised effects, not `iTime`.
- Use `iTimeDelta` for anything integrated over frames; smooth micro-freezes with a slow average of it (Neyret).
- Make the shader interesting at `iTime = 10` and `iFrame = 0`: that is the thumbnail.

---

## 12. Audio-reactive technique

### 12.1 Signal basics in five formulas

- **Sampling and Nyquist.** At sample rate `fs`, frequencies up to `fs / 2` are representable (24 kHz at 48 kHz).
- **Bin width.** An `N`-point FFT has bins `fs / N` apart: 23.4 Hz for `N = 2048` at 48 kHz.
- **Window length.** The same FFT looks at `N / fs` seconds: 42.7 ms. Time and frequency resolution trade one for the
  other: `bin width x window length = 1`. Finer pitch costs latency.
- **Decibels.** `dB = 20 log10(amplitude)` for amplitudes, `10 log10(power)` for powers; every 6 dB is a factor of two in
  amplitude. Loudness perception is roughly logarithmic, which is why visual mappings should start from dB, not raw
  magnitude (Bello et al. make the same argument for onset detection: differences of log energy track perceived
  loudness changes).
- **RMS.** Root-mean-square level of a block of samples, `sqrt(mean(x^2))`; in dB relative to full scale,
  `20 log10(rms)`. Computed over a short block (5 to 10 ms) it is the fastest loudness signal there is, faster than any
  FFT.

### 12.2 The Web Audio AnalyserNode, exactly

The W3C specification defines the pipeline precisely; every audio-reactive WebGL page is built on it:

1. Take the most recent `fftSize` samples (`N`), down-mixed to mono.
2. **Blackman window:** multiply sample `n` by `w(n) = a0 - a1 cos(2 pi n / N) + a2 cos(4 pi n / N)` with `alpha = 0.16`,
   `a0 = (1 - alpha)/2 = 0.42`, `a1 = 0.5`, `a2 = alpha/2 = 0.08`. The window tapers both ends to zero to reduce leakage,
   which also means the *newest* samples carry almost no weight (section 12.4).
3. **Fourier transform** scaled by `1/N`, keeping bins `0 .. N/2 - 1`.
4. **Smoothing over time:** `X_smooth[k] = tau x X_prev[k] + (1 - tau) x |X[k]|`, where `tau` is
   `smoothingTimeConstant` (default 0.8) and `X_prev` is the result of the *previous computation*. Non-finite results are
   reset to zero.
5. **To decibels:** `Y[k] = 20 log10(X_smooth[k])`.
6. **To bytes** (for `getByteFrequencyData`): `b[k] = floor( 255 / (maxDb - minDb) x (Y[k] - minDb) )`, clipped to 0..255,
   with defaults `minDecibels = -100`, `maxDecibels = -30`.
7. **Waveform bytes** (`getByteTimeDomainData`): `b = floor(128 x (1 + x))`, clipped, so silence is 128.
8. The analysis is recomputed at most once per render quantum (128 samples); two calls in one quantum return the same
   data.

Defaults: `fftSize` 2048, smoothing 0.8, dB range -100 to -30.

**Inverting the bytes in a shader.** A spectrum byte `v` in 0..1 maps back to `dB = minDb + v (maxDb - minDb)` (with the
defaults, `-100 + 70 v`) and to linear amplitude `10^(dB / 20)`. A shader that raises the texture value to a power is
shaping *decibels*, which is fine for looks; a shader that sums bins to get "energy" must convert to linear first, or it
is adding logarithms.

### 12.3 Smoothing is per call: the frame-rate trap

Step 4 runs once per *request*, not per unit time. If a page asks once per animation frame at rate `F`, the effective
time constant is

`T = -(1 / F) / ln(tau)`

| tau | 60 Hz | 144 Hz | 240 Hz |
|---|---|---|---|
| 0.8 (default) | 74.7 ms | 31.1 ms | 18.7 ms |
| 0.5 | 24.0 ms | 10.0 ms | 6.0 ms |

The same page looks calm on a 60 Hz laptop and twitchy on this 240 Hz display, and drops frames make it change
character mid-song. The fix the house already applies in `play.js` and `edit/playback.js`: set `smoothingTimeConstant`
to 0 and smooth explicitly with the measured `dt` (12.5). If a page must keep the analyser's smoothing, convert a desired
time constant per frame: `tau_call = exp(-dt / T)`.

### 12.4 Latency: where the milliseconds go

Visual response to a note is the sum of:

- **analysis window**: a 2,048-sample window at 48 kHz spans 42.7 ms; with the Blackman taper, a transient in the last
  few milliseconds barely registers, so spectral response lags the attack by roughly a quarter to a half of the window
  (10 to 20 ms);
- **smoothing**: a further one or more time constants;
- **audio output latency**: the AudioContext's `baseLatency` and `outputLatency` (the house records them;
  `arsenal/web/piano/cues.js:1780`);
- **frame scheduling and display**: one to two frames (4 to 8 ms at 240 Hz).

So the fast paths are: MIDI note-on events (no analysis at all), and short-block RMS from the time-domain data
(`getFloatTimeDomainData` over the newest few hundred samples). The FFT is for colour and texture, not for timing.
For drum-like hits, Böck and colleagues' online detectors work at 100 frames per second (10 ms hops) and report onsets
about one frame early relative to human annotation.

### 12.5 Smoothing done right

The workhorse is a **one-pole low-pass** (an exponential moving average), made frame-rate independent:

`y = y + (x - y) x alpha`, with `alpha = 1 - exp(-dt / tau)`

and made musical by making it **asymmetric**: a short `tau` when the input rises (attack, 5 to 20 ms) and a long one
when it falls (release, 100 to 500 ms). That is exactly the ballistics of an analogue VU meter or a compressor's
envelope follower, and it is why good visualizers "hit" fast and "breathe out" slowly. Two companions:

- **peak hold**: `p = max(x, p - fall x dt)`, a peak that decays linearly, for meters and sparkle triggers;
- **pulse envelope** for discrete events: 1 at the onset, held briefly, then `exp(-(t - hold) / tau)`.

Where state lives: on the host, these are three floats per band in JavaScript, which is trivial; inside a pure Shadertoy
shader there is no state, so it goes in a feedback buffer: reserve a row of pixels in Buffer A as registers (pixel
`(slot, 0)` holds band `slot`'s smoothed value, previous value and peak), read them with `texelFetch` of the buffer's own
previous frame, and write the updated values only at those pixels.

### 12.6 Mapping frequency to the screen

- **Log axis.** Pitch is logarithmic: an octave is a doubling. A screen coordinate `x` in [0, 1] maps to
  `f = fmin (fmax / fmin)^x`, and then to the texel `u = 4 f / sr` on the Shadertoy texture.
- **Low end: too few bins.** At 23.4 Hz per bin, the octave from 27.5 to 55 Hz occupies bins 1.2 to 2.3: a log display
  stretches two bins across a hundred pixels. Interpolate smoothly between bins (section 6.5's smooth filtering; or a
  cubic), and accept that no detail exists there.
- **High end: too many bins.** Above a few kHz, one pixel covers several bins; point-sampling then aliases (flickering
  bars). Average the bins under each pixel (a box filter over the pixel's frequency span) instead.
- **Filter banks.** Böck, Krebs and Schedl found that summing FFT bins into semitone-spaced overlapping triangular
  filters (82 bands from 27.5 Hz to 16 kHz) improved onset detection over raw bins, and that Mel, Bark and constant-Q
  layouts performed about equally. For a piano visualizer a semitone filter bank is also the natural *display* basis:
  one band per key.
- **Spectral tilt.** Music's power falls with frequency (roughly pink: equal power per octave means each linear bin holds
  less as frequency rises). A display that looks top-heavy-dead can add `s x log2(f / fref)` dB with `s` around 3 dB per
  octave. (Böck's filters were deliberately left un-normalised, which emphasises highs for the same reason.)

### 12.7 The piano versus the FFT

Key `n` of 88 has frequency `f(n) = 440 x 2^((n - 49) / 12)`: A0 is 27.5 Hz, C8 is about 4,186 Hz; in MIDI numbering,
`f(m) = 440 x 2^((m - 69) / 12)`. Adjacent semitones differ by `f x (2^(1/12) - 1)`, about 5.9 per cent of `f`: 1.64 Hz
at A0.

With 23.4 Hz bins, a semitone is narrower than a bin for every `f` below 394 Hz, which is G4, key 47. To *separate* two
adjacent notes you want at least two bins per semitone, which pushes the limit to about 790 Hz (G5). To resolve A0's
semitone at all you need a window of about `fs / 1.64 ≈ 0.6 s`, a latency no visual can afford. Meanwhile 65 per cent of
Shadertoy's 512 texels sit above C8's fundamental (they hold harmonics, hammer noise and room).

The conclusion for the house: **notes come from MIDI; timbre comes from audio.** MIDI gives exact pitch, exact onset
time and velocity with zero analysis latency. The audio spectrum gives what MIDI cannot: brightness (how much energy
sits high), the pedal's sustain bloom, the room, the decay. When there is no MIDI (a recording), pitch needs a long,
decimated transform like the house listen DSP's chroma path (a 4,096-point FFT at 6 kHz, 1.46 Hz per bin, resolving
semitones from about A1) and accepts its quarter-second hop.

### 12.8 Onsets and beats

**Detection functions** (Bello et al.'s taxonomy, in increasing sophistication):

- **energy envelope and its derivative**: rectify or square the signal, smooth, take the first difference so sudden
  rises become narrow peaks; better on the log of the energy;
- **high-frequency content** (Masri): weight each bin by its frequency before summing, since attack transients are
  broadband and stand out where steady tones have little energy; good for percussive onsets, including piano hammers;
- **spectral flux**: for each bin, the positive part of the change in magnitude since the previous frame, summed over
  bins: `SF(n) = sum_k H(|X(n, k)| - |X(n - 1, k)|)` with the half-wave rectifier `H(x) = (x + |x|) / 2`. Dixon found
  the L1 norm (plain sum) better than squares and, on a large piano data set, spectral flux and the complex-domain method
  marginally best;
- **log-compressed, filtered flux** (Böck et al. 2012): apply `log(lambda x |X| + 1)` and the semitone filter bank before
  the difference; the best simple online method in their tests;
- **SuperFlux** (Böck and Widmer 2013): compare each bin against the *maximum* of its neighbouring bins in the previous
  frame, so a vibrato or pitch glide moving energy to an adjacent bin no longer reads as an onset; up to 60 per cent fewer
  false positives on vibrato-heavy music. The house listen DSP's onset path already uses this
  (`arsenal/web/piano/listen/dsp.js:10-14`).

**Peak picking.** Dixon's offline rule selects frame `n` when it is the maximum within `±w` frames, exceeds the mean
over a window reaching further into the past by a margin `delta`, and exceeds a decaying threshold of past values.
Online (live) use cannot look into the future, so Böck et al. set the future window to zero and add a minimum distance
since the last onset; their onsets then come out one frame early, which they compensate by reporting one frame later.

**Adaptive thresholds for visuals.** Frédéric Patin's classic energy beat detector compares the instant energy of a
1,024-sample block against the average over the last 43 blocks (about one second at 44.1 kHz) and fires when
`E > C x <E>`, with `C` adapted to the history's variance `V` by a fitted line `C = -0.0025714 V + 1.5142857`. The
constants were fitted to his signal scaling, so refit them to yours; the idea (a louder threshold when the history is
steady, a lower one when it is already busy) is what transfers. He also splits the spectrum into subbands with widths
growing linearly with index, so each band can beat independently. ciphrd's visualizer-oriented version adds two rules
that matter for the eye: ignore new peaks for 0.375 s after one (a 160 BPM ceiling) and let the visual pulse persist
for 0.25 s.

**Where to compute.** On the host, always, when a host exists: the analysis needs history, sorting, medians and
branching that waste a fragment shader's lanes, and its result is a handful of numbers. Pass them as uniforms (or a tiny
"feature texture"). Only a pure Shadertoy shader, which has no host, should do onset detection on the GPU, using the
state-row pattern from 12.5.

### 12.9 The waveform row

The waveform is the newest 512 samples, unsynchronised with the signal's period, so a drawn oscilloscope jitters left
and right every frame. A hardware oscilloscope solves this with a **trigger**: start the trace at a rising zero
crossing. Do the search on the host (scan the time-domain array for the first sign change from negative to positive
after a small offset) and pass the offset as a uniform; a fragment shader would have to scan per pixel.

### 12.10 Mapping to visuals, and the flash rule

- Map from dB or log energy through a curve (smoothstep, a soft knee), not linearly from magnitude; quiet passages must
  still move something, loud ones must not clip everything to white.
- Separate the **slow** layer (envelope: overall brightness, density, camera drift) from the **fast** layer (onsets:
  sparks, hits) so the piece breathes and punctuates.
- **Photosensitivity.** WCAG 2.3.1 (Three Flashes or Below Threshold) says content should not flash more than three times
  in any one-second period unless the flashes are below the general and red flash thresholds. A beat-synced full-field
  flash at 160 BPM is 2.7 flashes per second; with double-time hi-hats it is over the line. Enforce a refractory interval
  of at least a third of a second for large-area luminance flashes on the host, and respect `prefers-reduced-motion` as
  the house already does.

### 12.11 A house contract for audio into shaders

What I would standardise so every surface reads audio the same way:

1. **Host side** (JavaScript): one AnalyserNode per source with `smoothingTimeConstant = 0`; the real `sampleRate`
   from the AudioContext bound to `iSampleRate`/`u_sampleRate`; the listen DSP's onset and chroma frames; MIDI events.
2. **Feature uniforms** (a small block of `vec4`s): RMS (dB), three band envelopes (low under 200 Hz, mid 200 Hz to
   2 kHz, high above, matching the listen DSP's bands), the onset pulse per band, beat phase, and the sustain-pedal state;
   all already smoothed with `dt`-correct attack and release.
3. **Shadertoy-compatible texture** (512 x 2, the house runtime's `packAudioTexture`) for corpus shaders and anything
   that wants per-bin detail.
4. **A note texture** (88 x 2, say): per key, current velocity envelope and time since note-on, written from MIDI. This
   is the piano's real spectrum, at zero latency and perfect resolution.

---

## 13. Common mistakes, as they look on screen

| what you see | likely cause | section |
|---|---|---|
| a 1 to 2 pixel line along every tile edge of a repeating texture | mip LOD from the derivative of `fract(uv)` | 6.3 |
| a seam along one ray of a radial or spiral effect | `atan` jump from π to -π in the derivative | 6.3 |
| random sparkles or a few wrong-coloured pixels inside a raymarched object | implicit-derivative `texture()` inside the march loop | 6.4 |
| a black blob that grows a little every frame | NaN in a feedback buffer (normalise of zero, sqrt of negative) | 5.8 |
| black on one machine, fine on another | incomplete texture: float filtering without the extension, or mipmap filter with no mips | 6.7 |
| a shape mirrored or shifted for negative coordinates on Windows only | integer `%` or `int()` on negatives | 5.9 |
| trails that never completely fade, a dim haze over everything | per-frame decay in an 8-bit buffer stalls at a small level | 5.7 |
| animation that stutters after the page has been open for days | float time losing precision; hashes of time losing randomness | 5.5 |
| everything runs four times too fast on the 240 Hz monitor | per-frame constants without `iTimeDelta` | 5.7 |
| an audio-reactive page calm on a laptop, twitchy on this display | analyser smoothing is per call | 12.3 |
| frequency bands land a semitone and a half off | sample rate assumed 44.1 kHz while the context runs at 48 kHz | 12, finding 4 |
| flickering bars at the top of a log spectrum | point-sampling many bins per pixel | 12.6 |
| a staircase in a smooth gradient read from a magnified texture | 8-bit hardware filter weights | 6.5 |
| blocky, two-pixel-stepped image on a phone only | `mediump` coordinates or hashes | 5.4 |
| a seconds-long freeze when an effect first appears (Windows) | FXC compiling unrolled loops | 8.2 |
| the screen flickers, all GPU windows go black, "display driver recovered" | a draw ran past the 2-second TDR limit | 8.6 |
| a mouse-driven shader whose thumbnail is boring or black | `iMouse` is all zero at start | 11.4 |
| key presses register on the wrong key or two keys | `texture()` at non-centre coordinates with linear filtering | 11.2 |
| spectrum bars where the waveform should be (or the reverse) | rows swapped: row 0 spectrum at v = 0.25, row 1 waveform at v = 0.75 | 11.5 |
| an oscilloscope trace that slides left and right | no trigger on the waveform | 12.9 |
| motion that looks smooth, then hitches during heavy scenes | frame-rate-dependent integration plus dropped frames | 5.7 |

---

## 14. The primitive API for the house library

### 14.1 Design rules

- One module file per family in `arsenal/web/glsl/<category>/`, with the house `//!` JSON header (name, kind `helper`,
  `cat`, `order`, `license: Apache-2.0`, `credits`, `cost`, `note`). Names in the field's common camelCase.
- Pure functions; no globals; no `#version` or `precision` (the host template owns line 1 and declares `highp`).
- Every loop has a constant bound stated in `cost`; no implicit-derivative `texture()` inside a loop or a data-dependent
  branch; derivatives only of continuous values, and only in uniform control flow.
- Each module gets a CPU twin for its tests (numpy), as the noise report proposes: exactness of the safe functions at
  their edge cases (zero, negative, NaN inputs), the integer modulo against Python's floor modulo for negative inputs,
  phase functions against float64, decay stall levels against the derivation.
- Signatures only below; bodies are to be written fresh from the mathematics in the referenced sections.

### 14.2 `safe` (category `math-safe`): correctness in feedback passes

```glsl
float safeDiv(float num, float den, float eps);   // num / den with |den| floored at eps, sign kept (0 counts as +): never Inf or NaN
vec2  safeNormalize(vec2 v, vec2 fallback);       // v / |v| when dot(v, v) > 1e-24, else fallback: never NaN
vec3  safeNormalize(vec3 v, vec3 fallback);       // as above in 3D: use in every pass that writes a feedback buffer
float safeSqrt(float x);                          // sqrt(max(x, 0.0)): rounding-negative inputs give 0, not NaN
float safePow(float base, float e);               // pow(max(base, 1e-30), e): defined for all inputs; negative bases clamp to the floor
float safeLog2(float x, float floorVal);          // log2(max(x, floorVal)): silence gives a finite floor, not -Inf
float safeAtan2(float y, float x);                // atan(y, x) with the (0, 0) case defined as 0
float safeAcos(float x);                          // acos of x clamped into [-1, 1] first: dot products of unit vectors can exceed 1 by an ulp
bool  isFiniteF(float x);                         // abs(x) <= 3.4028235e38: false for NaN and both infinities
vec4  finiteOr(vec4 v, vec4 fallback);            // replaces each non-finite component: the last guard before a feedback write
```

### 14.3 `int-math` (category `math-int`): portable integer arithmetic

```glsl
int   imodFloor(int a, int b);                    // floor modulo for b > 0: result in [0, b) for any sign of a (% is undefined for negatives)
ivec2 imodFloor(ivec2 a, int b);                  // component-wise floor modulo: tile and wrap indices that may go negative
int   idivFloor(int a, int b);                    // floor(a / b) for b > 0 and any a (integer / rounding is undefined for negatives)
float fmodFloor(float x, float m);                // x - m * floor(x / m), pushed back into [0, m) when rounding lands exactly on m
float roundHalfUp(float x);                       // floor(x + 0.5): round() may round halves to even
int   cellIndex(float x);                         // int(floor(x)): int() truncates toward zero, so int(-0.5) would be 0
```

### 14.4 `precision-time` (category `time`): clocks and phases that do not rot

```glsl
float ulp32(float x);                             // spacing of float32 at x: exp2(floor(log2(abs(x))) - 23.0); a diagnostic
float ulp16(float x);                             // spacing of float16 at x: exp2(floor(log2(abs(x))) - 10.0); what mediump means on a phone
float phaseCycles(float tWrapped, float hz);      // fract(hz * t) for host-wrapped t, in cycles [0, 1)
float phaseSplit(float tWhole, float tFrac, float hz);  // fract(fract(fract(hz) * tWhole) + hz * tFrac): exact phase from whole seconds plus fraction
float phaseFromSample(int sampleIndex, float hz, float sampleRate); // mainSound phase from an integer index split into seconds and remainder; error about ulp(hz) cycles at any song position
float perFrameKeep(float keepPerSecond, float dt);      // pow(keepPerSecond, dt): frame-rate independent decay factor
float expAlpha(float dt, float tau);              // 1 - exp(-dt / tau): blend weight of a one-pole smoother with time constant tau seconds
float decayStallLevel8(float keepPerFrame);       // about (ceil(0.5 / (1 - k)) - 1) / 255: the level an 8-bit buffer stops decaying at (one step higher on exact ties)
```

### 14.5 `texel` (category `texture`): sampling that is correct in loops and at seams

```glsl
vec4  texelClamped(sampler2D s, ivec2 p, int lod);      // texelFetch with p clamped into the level's size: no out-of-range reads
vec2  texelCenterUv(ivec2 p, vec2 size);                // (vec2(p) + 0.5) / size: hits texel p exactly under any filter
float mipLevel(vec2 uv, vec2 texSize);                  // lambda = log2(max(|dFdx(uv)| * size, |dFdy(uv)| * size)); call in uniform flow, use the result inside loops
vec4  sampleTiled(sampler2D s, vec2 uvContinuous);      // textureGrad(s, fract(uv), dFdx(uv), dFdy(uv)): repeat tiling without seam lines
vec4  samplePolar(sampler2D s, vec2 radiusAngle01);     // like sampleTiled for (radius, angle/2pi): the angle's derivative is unwrapped across the jump
vec4  sampleBilinearExact(sampler2D s, vec2 uv);        // four texelFetch plus full-float blending: for LUTs, heightfields, magnified spectra
vec4  sampleQuintic(sampler2D s, vec2 uv, vec2 size);   // one fetch at a quintic-remapped sub-texel position, gradients from the original uv
vec4  sampleBSpline(sampler2D s, vec2 uv, vec2 size);   // cubic B-spline from four bilinear fetches (Sigg and Hadwiger); inner weights still 8-bit
vec2  uvFlipV(vec2 uv);                                 // vec2(uv.x, 1.0 - uv.y): for media uploaded without vflip
```

### 14.6 `toy-input` (category `input`): the Shadertoy interface, readable

```glsl
bool  keyDown(sampler2D kb, int keyCode);         // row 0 of the 256x3 keyboard texture; keyCode = browser keyCode (A=65, space=32, left=37)
bool  keyPressed(sampler2D kb, int keyCode);      // row 1: true only on the frame the key went down
bool  keyToggled(sampler2D kb, int keyCode);      // row 2: flips on each press
bool  mouseHeld(vec4 mouse);                      // iMouse.z > 0
bool  mouseJustClicked(vec4 mouse);               // iMouse.w > 0: the click frame only
bool  mouseUntouched(vec4 mouse);                 // all four components zero: no input yet, so show the demo state
vec2  mouseDragOrigin(vec4 mouse);                // abs(iMouse.zw): where the current or last press started
bool  channelLoaded(vec3 channelResolution);      // iChannelResolution[i].x > 0: the asynchronous load has arrived
bool  resolutionChanged(vec2 res, vec2 storedRes);// compare with the resolution a buffer stored last frame: re-initialise on true
```

### 14.7 `audio-read` (category `audio`): decoding the audio texture honestly

```glsl
float audioSpectrum(sampler2D a, float u);                         // row 0 at u in [0, 1] across 512 bins, linear between bins: decibel-mapped 0..1
float audioSpectrumAtHz(sampler2D a, float hz, float sampleRate);  // row 0 at u = 4 hz / sampleRate (512 texels span 0..sampleRate/4); 0 above that
float audioWave(sampler2D a, float u);                             // row 1 mapped to [-1, 1] with 128 as zero
float audioByteToDb(float v, float minDb, float maxDb);            // minDb + v (maxDb - minDb): the inverse of getByteFrequencyData (defaults -100, -30)
float audioByteToAmp(float v, float minDb, float maxDb);           // 10^(dB / 20): linear magnitude, for sums, bands and flux
float audioBand(sampler2D a, float hzLo, float hzHi, float sampleRate); // mean linear magnitude over the bins in [hzLo, hzHi); texelFetch, at most 64 taps
float audioLogAxisHz(float x, float hzMin, float hzMax);           // hzMin (hzMax / hzMin)^x: a log-frequency screen axis
float audioTiltDb(float hz, float dbPerOctave, float hzRef);       // dbPerOctave log2(hz / hzRef): pink-spectrum compensation
float midiToHz(float midi);                                        // 440 2^((m - 69) / 12)
float hzToMidi(float hz);                                          // 69 + 12 log2(hz / 440)
float pianoKeyToHz(float key);                                     // keys 1..88: 440 2^((k - 49) / 12); A0 = 27.5, C8 = 4186
float rmsToDbfs(float rms);                                        // 20 log10(max(rms, 1e-9))
```

### 14.8 `audio-state` (category `audio`): envelopes, onsets and state in a buffer

```glsl
float envFollow(float prev, float x, float dt, float tauAttack, float tauRelease); // asymmetric one-pole: fast up, slow down, frame-rate independent
float peakHold(float prev, float x, float dt, float fallPerSecond); // max(x, prev - fall dt): meter-style peak
float halfWaveRise(float now, float prev);        // max(now - prev, 0): one bin's spectral-flux term (rises only)
float onsetGate(float flux, float meanFlux, float k, float delta); // 1 when flux > k meanFlux + delta (adaptive threshold); the caller owns the refractory time
float pulseEnvelope(float sinceOnset, float hold, float tauRelease); // 1 for hold seconds after an onset, then exp(-(t - hold) / tau)
vec4  stateRead(sampler2D self, int slot);        // texelFetch(self, ivec2(slot, 0), 0): slot-addressed registers in row 0 of a feedback buffer
bool  stateIsSlot(vec2 fragCoord, int slot);      // true only at the pixel storing slot: write state there, image elsewhere
float flashSafeGain(float sinceLastFlash);        // 0 within 1/3 s of the previous full-field flash, ramping to 1: at most three flashes per second
```

### 14.9 `perf-debug` (category `debug`): making cost and correctness visible

```glsl
int   unrollBarrier(int n, int frame);            // n + min(frame, 0): equals n at runtime but is unknown to the compiler, so loops stay loops
vec3  heatRamp(float t);                          // a monotone dark-to-bright ramp for t in [0, 1], perceptually ordered
vec3  heatCount(float count, float budget);       // heatRamp(count / budget), magenta above budget: where the slow pixels are
vec3  rangeScope(vec4 c);                         // magenta NaN, cyan Inf, blue negative, red above 1, grey in range: a value-range oscilloscope
vec3  mipLevelColor(vec2 uv, vec2 texSize);       // colours by mipLevel: blue magnified, green near level 0, red heavily minified
vec3  tileGrid(vec2 fragCoord, float tilePx, vec3 base); // overlays a tilePx grid (8 for wave64-sized tiles) to judge how many waves straddle a boundary
float quadDisagreement(float flag);               // fwidth(flag) for a 0/1 flag computed in uniform flow: non-zero where a quad is split by a branch
```

### 14.10 Host-side contracts (JavaScript, for the same modules)

Not GLSL, but part of the same seam and worth fixing in one place: `iSampleRate` from `AudioContext.sampleRate`; analyser
`smoothingTimeConstant = 0`; phases and wrapped time computed in float64 and uploaded; `KHR_parallel_shader_compile`
polling before a program replaces its CSS fallback; the renderer string recorded beside every performance number; a
flash limiter for large-area luminance pulses.

---

## 15. What I would change in the house tooling

These are proposals for whoever builds tomorrow; none were applied tonight.

1. **Bind the real sample rate** in `toy-runtime.js` (`SAMPLE_RATE` is a constant 44,100; finding 4) and let `setAudio`
   carry the rate it was analysed at.
2. **Teach `py -m arsenal shader lib lint` the blind-checkable traps from this report**, each a regular-expression or
   small-parser check the house can run without a GPU: implicit-derivative `texture()` inside a loop body or a branch
   on non-uniform data; `%` on integer operands that can be negative; per-frame decay or integration constants in a
   buffer pass that never reads `iTimeDelta`; `normalize`, `sqrt`, `pow`, `log`, `acos` without a guard in a pass that
   writes a feedback buffer; missing precision for `sampler3D` and integer samplers; reserved words as identifiers;
   global initialisers that read uniforms; any `mediump`; `while` loops without a counter; local arrays dynamically
   indexed inside loops; nested constant-bound loops whose product exceeds a threshold (a compile-time risk score).
3. **A "D3D risk" column in the corpus census**: the 50 `texture()`-in-loop shaders and the 28 that use the `%`
   operator are the ones to watch when a page shows them live on this machine. (Both counts come from a rough
   comment-stripped text scan, not a parser; treat them as a watch list, not a verdict.)
4. **A heat mode in the VFX bench and the shader lab**: one switch that replaces the output with step counts, fetch
   counts or the range scope (section 10.4). It is deterministic on SwiftShader, so a blind seat can read it as numbers.
5. **Offline register counts with RGA** (section 10.6), if Daniel approves the download: a module's VGPR count and
   occupancy class for gfx1201 in its header, and a shader diff on every change, Persson style.
6. **A budget calculator** next to the bench: pixels times refresh rate times per-pixel cost against this card's
   24.3 TFLOPS single-issue, so "will this run at 4K/240" has an answer before anything runs.
7. **The audio contract of 12.11**: one analyser policy, one feature block, one note texture, used by every surface.
8. **Tile any heavy offline render** so no single submission approaches the TDR window; the GPU lock already serialises
   renders, and this bounds each one.

---

## 16. Sources

GPU architecture and execution

- https://courses.cs.washington.edu/courses/cse558/11wi/lectures/05_gpuArchShaderCores_BPS_2011.pdf - Kayvon Fatahalian: how shader cores work, the three ideas.
- https://gpuopen.com/download/RDNA_Architecture_public.pdf - AMD RDNA architecture slides: single-cycle issue, exposed latency, wave64 as two halves, pixel shaders usually wave64, VGPR occupancy.
- https://gpuopen.com/learn/rdna-performance-guide/ - AMD RDNA performance guide: transcendental rates, atan and acos cost, helper lanes, FP16, discard.
- https://gpuopen.com/learn/occupancy-explained/ - François Guthmann (AMD): occupancy, register limits, when occupancy hurts.
- https://chipsandcheese.com/p/dynamic-register-allocation-on-amds - Chips and Cheese: RDNA 4's 192 KB register file, 1,536 VGPRs, allocation blocks.
- https://en.wikipedia.org/wiki/RDNA_4 - RX 9070 XT specification table (CUs, lanes, TMUs, clocks, caches, bandwidth, TFLOPS).
- https://developer.nvidia.com/content/life-triangle-nvidias-logical-pipeline - NVIDIA: warps, quads, warp scheduling, register-limited residency.
- https://fgiesen.wordpress.com/2011/07/04/a-trip-through-the-graphics-pipeline-2011-part-4/ - Fabian Giesen: texture samplers, latency, cache misses per request, filter costs.
- https://fgiesen.wordpress.com/2011/07/10/a-trip-through-the-graphics-pipeline-2011-part-8/ - Fabian Giesen: quads, helper pixels, divergence, latency hiding.

Shader writing practice

- http://www.humus.name/Articles/Persson_LowLevelThinking.pdf - Emil Persson, GDC 2013: multiply-add form, modifiers, scalar/vector separation, branch intent, shader diffs.
- https://iquilezles.org/articles/gpuconditionals/ - Inigo Quilez: selects are not branches; step/mix is slower.
- https://iquilezles.org/articles/hwinterpolation/ - Inigo Quilez: 8-bit hardware filter weights and manual interpolation.
- https://iquilezles.org/articles/texture/ - Inigo Quilez: smoother texture filtering by remapping the sub-texel fraction.
- https://shadertoyunofficial.wordpress.com/2017/11/19/avoiding-compiler-crash-or-endless-compilation/ - Fabrice Neyret: unrolling, inlining, the ANGLE pipeline, the unroll barrier.
- https://shadertoyunofficial.wordpress.com/2016/07/22/compatibility-issues-in-shadertoy-webglsl/ - Fabrice Neyret: undefined behaviours and Windows/ANGLE differences.
- https://shadertoyunofficial.wordpress.com/2019/01/26/classical-corner-cases/ - Fabrice Neyret: texel centres, iMouse, initialisation, mip seams, derivatives in branches.
- https://shadertoyunofficial.wordpress.com/2023/11/26/performance-tricks/ - Fabrice Neyret: performance philosophy, arrays, multipass caching.
- https://shadertoyunofficial.wordpress.com/2016/07/20/special-shadertoy-features/ - Fabrice Neyret: keyboard, sound, buffers, mouse and cubemap conventions.
- https://shadertoyunofficial.wordpress.com/2018/03/26/puzzling-compilation-errors-in-shadertoy/ - Fabrice Neyret: cryptic compile errors and their causes.
- https://jcgt.org/published/0009/03/02/ - Mark Jarzynski and Marc Olano: GPU hash quality and speed; the trig hash is poor.
- https://developer.nvidia.com/gpugems/gpugems2/part-iii-high-quality-rendering/chapter-20-fast-third-order-texture-filtering - Christian Sigg and Markus Hadwiger: bicubic from four bilinear fetches.

Specifications and platform

- https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf - GLSL ES 3.00: precision table and defaults, function accuracy, NaN rules, derivatives and control flow, `%`, the version line, reserved words.
- https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf - OpenGL ES 3.0.6: the LOD formula, texture completeness, sRGB decode, incomplete textures return (0,0,0,1).
- https://registry.khronos.org/webgl/specs/latest/1.0/ - WebGL 1: zero-initialised variables, out-of-range access rules, feedback loops as errors, token limits.
- https://registry.khronos.org/webgl/specs/latest/2.0/ - WebGL 2: 1,024-character tokens, defined texel-fetch results.
- https://registry.khronos.org/webgl/extensions/EXT_color_buffer_float/ - which float formats are renderable.
- https://registry.khronos.org/webgl/extensions/OES_texture_float_linear/ - filtering 32-bit float textures.
- https://registry.khronos.org/webgl/extensions/EXT_disjoint_timer_query_webgl2/ - GPU timer queries and the disjoint flag.
- https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices - MDN: precision by platform, parallel compile, float targets, mipmaps, async readback.
- https://developer.mozilla.org/en-US/docs/Web/API/WEBGL_debug_shaders - the translated-source extension and its privacy restriction.
- https://webgl2fundamentals.org/webgl/lessons/webgl-precision-issues.html - Gregg Tavares: precision on real phones, getShaderPrecisionFormat.
- https://groups.google.com/g/webgl-dev-list/c/ZDms8ZQGl3o - Chrome's default WebGL powerPreference change to low-power.
- https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery - Microsoft: the 2-second TDR and the five-hangs-per-minute bug check.

ANGLE and compile time

- https://www.khronos.org/webgl/public-mailing-list/public_webgl/1104/msg00030.php - Alvaro Segura: texture sampling in loops forcing unrolling; minutes to seconds.
- https://github.com/Singtaa/OneJS/issues/130 - a measured 7.55 s first-draw FXC compile on ANGLE D3D11.
- https://bugzilla.mozilla.org/show_bug.cgi?id=1237676 - a WebGL2 report of explicit-LOD lookups in loops being treated as derivative-dependent on ANGLE.
- https://gpuopen.com/rga/ - AMD Radeon GPU Analyzer: offline compilation, register usage and ISA for RDNA targets.
- https://github.com/GPUOpen-Tools/radeon_gpu_analyzer - RGA releases, including gfx1201 (RDNA 4) support and `vk-offline` mode.

Audio

- https://www.w3.org/TR/webaudio/ - Web Audio API: the AnalyserNode's window, transform, per-block smoothing, dB and byte mappings, defaults.
- https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode/smoothingTimeConstant - MDN: smoothing default and range.
- https://hajim.rochester.edu/ece/sites/zduan/teaching/ece472/reading/Bello_2005.pdf - Bello et al., 2005: the onset-detection tutorial (energy, HFC, spectral and phase methods).
- https://www.dafx.de/paper-archive/2006/papers/p_133.pdf - Simon Dixon, 2006: spectral flux, complex domain, peak picking.
- https://www.cp.jku.at/research/papers/Boeck_etal_ISMIR_2012.pdf - Böck, Krebs and Schedl, 2012: online onset detection, log filtered flux, online peak picking.
- https://phenicx.upf.edu/system/files/publications/Boeck_DAFx-13.pdf - Böck and Widmer, 2013: SuperFlux vibrato suppression.
- https://www.flipcode.com/misc/BeatDetectionAlgorithms.pdf - Frédéric Patin: energy beat detection, variance-adapted threshold, subbands, comb filters.
- https://ciphrd.com/articles/audio-analysis-for-advanced-music-visualization/ - ciphrd: refractory time and pulse persistence for visualizers.
- https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html - WCAG 2.3.1: at most three flashes per second.

Shadertoy interface (pointers into the private corpus; read for conventions, not copied)

- https://www.shadertoy.com/view/Xds3Rr - Inigo Quilez, "Input - Sound": the 512 x 2 layout and about 23 Hz per texel (`Xds3Rr/image.glsl:23-29`).
- https://www.shadertoy.com/view/llySRh - Fabrice Neyret's utilities: keyboard rows, mouse signs, load detection (`llySRh/image.glsl:168-187,281`).
- https://github.com/NatronGitHub/openfx-misc/blob/master/Shadertoy/Shadertoy.md - the Natron port's documented uniform list.
