# Water, fluids and feedback simulations on the GPU

Shader school, 2026-10-13. One of eight topic reports. Written for a capable programmer who has never written a shader, aiming at expert level.

Scope: Tessendorf's FFT ocean, Gerstner (trochoidal) waves, heightfield ray marching in the style of TDM's Seascape (ideas only), Jos Stam's stable fluids in ping-pong buffers, Gray-Scott reaction-diffusion, particle systems stored in textures, cellular automata, feedback trails, temporal accumulation and TAA (Karis 2014), progressive path-tracing accumulation, and the Shadertoy multipass conventions (Buffer A-D, Common, float precision, iFrame reset).

Licence line, as the house rules require: everything below is in our own words and our own mathematics. Pointers such as `Ms2SD1/image.glsl:135` refer to files in `state/arsenal/shaders/corpus/shaders/` (other people's code, mostly CC BY-NC-SA 3.0, read only, never copied into tracked files). The primitive signatures in section 12 are written fresh for the house library.

---

## 0. The whole topic in one paragraph

A fragment shader is a factory that computes every pixel at once and remembers nothing. Every technique in this report is a way of giving that factory a memory. You write the state of a world (heights, velocities, chemical concentrations, particle positions, an accumulated image) into a texture; next frame the shader reads that texture and writes the next state into another one; the two textures swap roles; repeat. That swap is called ping-pong, and it turns a stateless pixel machine into a simulator. Once you have memory, three families appear. Physical simulations (waves, fluids, particles) step a set of differential equations forward in time. Pattern simulations (reaction-diffusion, cellular automata) apply a local rule over and over until structure emerges. Temporal accumulation (feedback trails, TAA, progressive path tracing) uses the memory to average many noisy or jittered frames into one clean one. Oceans sit slightly apart: the best ones are not simulated step by step at all, they are evaluated in closed form as a sum of waves at any time t, then rendered by marching rays against the resulting height field.

---

## 1. The machine model: how a pixel factory keeps state

### 1.1 Why the GPU forgets

A fragment shader runs once per pixel per frame with no access to its neighbours' results and no way to write anywhere except its own output pixel. Think of thousands of identical workers on an assembly line who each receive a ticket (the pixel coordinate), may read from any shelf in the warehouse (textures), but may only place their finished part in their own bin (the output pixel). They cannot leave notes for each other inside one frame.

Two consequences shape everything:

1. **Gather, not scatter.** A pixel can read anywhere but write only to itself. So every simulation has to be phrased as "what value ends up at my cell?" (gather) rather than "where does my value go?" (scatter). This is why the classic fluid advection runs backwards in time (section 7.3) and why drawing particles in a pure fragment shader is awkward (section 8).
2. **Memory lives in textures between frames.** You cannot read and write the same texture in one pass, so you keep two: last frame's state (read) and this frame's state (write), and swap. This is double buffering, the same trick a graphics card uses for the front and back framebuffer, or two SRAM banks in a ping-pong DMA engine.

So a simulation is a function `S(n+1) = F(S(n))` evaluated in parallel per texel, where `S` is a texture and `F` is your shader.

### 1.2 Shadertoy's multipass conventions

Shadertoy is the lingua franca of the shader world, and its conventions are the de facto standard the corpus is written in. What follows is distilled mainly from Fabrice Neyret's "Shadertoy unofficial" notes and the corpus itself.

- **Tabs.** `Image` is what you see. `Buffer A`, `B`, `C`, `D` are off-screen passes, each producing one RGBA texture the size of the canvas. `Common` is code pasted at the top of every tab (the house's equivalent is the module library: one definition, many consumers). `Cube A` is a cubemap buffer, six faces, which notes describe as half precision.
- **Order and the one-frame lag.** Each frame runs A, then B, C, D, then Image. A buffer can read any buffer (including itself) through `iChannel0..3`. If Buffer A reads Buffer B, it sees B's output from the *previous* frame, because B has not run yet this frame. If Buffer C reads Buffer A, it sees A from *this* frame. Coupled fields (velocity in A, pressure in B) therefore drift one frame out of phase unless you order them deliberately. Self-reads are always last frame: that is the feedback loop.
- **Precision.** Buffers are floats, not bytes, and not clamped to [0,1]. Neyret's notes say they are ordinary 32-bit floats on most systems, except some old mobile devices. Pavel Dobryakov's widely used WebGL fluid deliberately uses 16-bit half floats for speed and mobile reach. Plan for either (section 1.4).
- **Filtering and wrap per input.** Each channel input has a filter (nearest, linear, mipmap) and wrap (clamp, repeat). Buffers do not get mipmaps unless you choose the mipmap filter. State that is *data* (particle records, cellular-automaton cells, packed integers) must be read with `texelFetch` or nearest filtering; state that is a *field you sample between cells* (velocity, dye) wants linear.
- **Pixel centres.** `fragCoord` arrives at pixel centres (integer + 0.5). `texelFetch(buf, ivec2(fragCoord), 0)` reads exactly your own texel. `texture(buf, fragCoord / iResolution.xy)` also lands on the centre. Any arithmetic that drops the 0.5 (using `floor(fragCoord)/iResolution`, or `(fragCoord - 0.5)/res`) puts you on a texel corner; with linear filtering, every frame then averages four texels and shifts the image half a pixel. Visible symptom: the whole simulation slowly slides diagonally and goes soft.
- **iFrame, initialisation and reset.** Frame 0 is when you write the initial state. Neyret notes that textures load asynchronously, so if your initial state is built from an image, initialise over the first ~30 frames. The corpus uses `iFrame < 1`, `< 5`, `< 10` (e.g. `XddSRX/buf_a.glsl:160`, `ldd3DB/buffer_a.glsl:14`, `WdyGzy/buffer_a.glsl:48`). A user-triggered reset reads the keyboard texture (`XddSRX/buf_a.glsl:37-39`, space bar). cornusammonis also seeds a tiny amount of noise at init because a perfectly uniform start blew up through precision effects (`tsKXR3/buffer_a.glsl:191`).
- **Resolution changes.** Buffers do not stay valid across a resize (going fullscreen). Robust shaders store the resolution in a reserved texel and re-initialise when it changes. alro's MIT-licensed `NdS3zK/buffer_a.glsl:1-60` keeps mouse state, camera position and a resolution-changed flag in the first four pixels of Buffer A; reinder's Himalayas (`MdGfzh/common.glsl:60-82`) stores the previous camera matrix rows in texels (2,0) to (4,0) for reprojection. This "state texels in a corner" pattern is the shader equivalent of a control register block.
- **iMouse.** `xy` is the current position while dragging; `zw` is where the click started; the signs of `z` and `w` encode button-down and click-this-frame.
- **Keyboard texture.** A 256 x 3 texture: row 0 key held, row 1 key pressed this frame, row 2 toggle; the key code selects the column.
- **iTimeDelta.** The real frame time. A simulation stepped with raw `iTimeDelta` explodes the first time the browser stutters. Use a fixed step (and substeps if the frame is long) or clamp it; the house's Moonwater does exactly this (`arsenal/web/piano/spectacle-worlds.js:36-46`: accumulate time, step at a fixed 1/120 s, cap the backlog at 1/30 s).

### 1.3 Storage budget

Each buffer gives you four floats per pixel. Four buffers give sixteen. That is your register file. Experts pack aggressively: velocity in `.xy`, a scalar in `.z`, a second scalar in `.w`; or two 16-bit integers per float channel when you need more fields than channels (Mykhailo Moroz packs particle position and velocity this way, `WtfyDj/common.glsl:70-95`). Packed data must never be read with a linear filter, because the average of two packed numbers is garbage.

### 1.4 Number formats, and the three ways they bite

A float is a mantissa (significant digits) and an exponent, like a scientific-notation display with a fixed number of digits. The number of digits is everything here:

| format | significant bits | relative spacing near 1.0 | largest value | integers exact up to |
|---|---|---|---|---|
| 8-bit unorm (RGBA8) | 8 | 1/255 ~ 0.004 | 1.0 | n/a |
| half float (fp16) | 11 | 2^-10 ~ 0.001 | 65 504 | 2 048 |
| float (fp32) | 24 | 2^-23 ~ 1.2e-7 | ~3.4e38 | 16 777 216 |

**Bite 1, the stuck residue (8-bit).** A trail that fades by multiplying by d each frame: an 8-bit value v becomes round(v*d). It stops changing when v*(1-d) < 0.5, i.e. when v < 0.5/(1-d). For d = 0.98 that is v < 25, about 10% grey. The trail never fully fades; a ghost of everything ever drawn stays on screen. Fixes: float buffers, subtract a small constant as well as multiply, or add per-pixel noise before rounding (dither) so the rounding is unbiased on average.

**Bite 2, the precision stall (fp16).** A running average m(n) = m(n-1) + (x - m(n-1))/n stops moving once the correction is smaller than half the spacing between representable numbers. For fp16 near 1.0 that spacing is ~0.001, so with noise whose deviation is about the size of the mean, the average freezes after roughly two thousand frames and keeps its residual noise forever. fp32 pushes that to millions. Same story for particle positions stored in pixels: in fp16, between 1024 and 2048 the spacing is a whole pixel, so a particle near x = 1900 can only sit on integer pixels and moves in visible jumps.

**Bite 3, NaN poisoning (all floats).** NaN (not a number) comes from 0/0, `normalize(vec2(0))`, `sqrt` or `log` of a negative, `pow` of a negative base. In a feedback loop it is permanent and contagious: blur, advection and the Laplacian all read neighbours, so one NaN texel becomes a black (or white) square that grows every frame. Guard at the source (cornusammonis writes a safe normalise that returns zero for a zero vector, `XddSRX/buf_a.glsl:42-44`) and sanitise at the end of the step. Overflow in fp16 (anything above 65 504, easy with an HDR sun) produces infinity, then NaN one operation later.

### 1.5 Safety budget on this host

This machine has an AMD display-driver crash history. Windows resets the driver (TDR) if one GPU job runs for about two seconds. Iterative sims are where you hit that: a pixel shader that loops over all particles costs pixels x particles. At 1920 x 1080 with 4 096 particles that is about 8.5 billion inner iterations per frame, a guaranteed reset. Keep loops bounded, keep particle counts small when every pixel loops over them (iapafoto's shoal uses 40, `ldd3DB/common.glsl:1`), and treat "number of fetches per pixel x pixels" as the cost you budget.

---

## 2. Feedback trails: the simplest simulation

### 2.1 The loop

Read last frame, change it a little, draw new things on top, write it back:

`C(n+1)(x) = d * C(n)(W(x)) + new(x)`

`d` is the decay (how much survives a frame), `W` is a warp (where each pixel looks in the previous frame). With `W` = identity you get pure trails: moving objects leave a fading comet tail. With `W` = a slight zoom toward the centre plus a slight rotation you get the classic tunnel-of-echoes look. Ryan Geiss built Winamp's MilkDrop on exactly this model: every frame the previous image is warped through a coarse mesh (zoom, rotation, warp, centre, translation, stretch, all animatable per frame and per vertex), darkened by `decay` (his recommended value is 0.98), and then new waveforms and shapes are drawn on top. MilkDrop 2 split this into a warp shader (writes the feedback canvas) and a composite shader (reads it for display only), and added three progressively blurred copies of the canvas for glow. That split is worth copying: **the feedback state and the displayed image are different things**, so display effects (tone mapping, vignettes, colour grading) never leak into the loop and compound.

### 2.2 Frame-rate independence

A decay of 0.98 per frame means one thing at 60 fps and another at 144 fps. Specify a half-life h in seconds instead and convert:

`d = exp(-ln(2) * dt / h)`

Same for zoom and rotation: make them per-second rates multiplied by dt.

### 2.3 What makes feedback look expensive

- **Warp by a field, not a formula.** Sample the previous frame at `x - k * v(x)` where `v` is a slowly changing vector field (curl noise, section 8.4, is ideal because it never piles colour into sinks). This is a fluid without the pressure solve and already reads as smoke.
- **Blur in the loop, a little.** A 3x3 blur inside the loop is diffusion; it rounds edges into soft plumes. Too much turns everything to fog.
- **Colour drift.** Rotate hue a little each pass, so older material shifts colour with age, giving a free "time" encoding.
- **Advected coordinates.** Instead of carrying colour, carry the *texture coordinate* each pixel came from, advect that, and look up an image through it at display time. Wyatt's Lattice Boltzmann shader does this (`WdyGzy/buffer_b.glsl`, `buffer_d.glsl`): the picture smears along the flow but stays sharp, because colour is never resampled repeatedly. Re-seed coordinates periodically or they stretch without limit.

### 2.4 Mistakes and how they look

- Trails that never fully clear: the 8-bit residue (1.4).
- Image creeping diagonally and softening: half-texel offset (1.2).
- Brightness exploding to white: decay times the sum of additions is above 1; the loop gain must stay below 1, just like an audio feedback loop through a microphone.
- Colour saturating to one hue: any per-channel gain above 1 compounds; keep channel gains equal or compensate.

---

## 3. Temporal accumulation: averaging through time

### 3.1 Two kinds of average

**Cumulative (progressive) average.** Every new frame is an equally weighted sample of the same answer:

`m(n) = m(n-1) + (x(n) - m(n-1)) / n`

Error falls like 1/sqrt(n): four times the samples halves the noise. This is how a path tracer converges. Alan Wolfe (demofox) in "Casual Shadertoy Path Tracing" stores this in Buffer A, mixes the new sample in with weight 1/(frame+1), keeps the sample count in the alpha channel, and resets the count when the space bar is pressed or the camera changes.

**Exponential moving average (EMA).** Constant weight alpha for the newest frame:

`s(t) = alpha * x(t) + (1 - alpha) * s(t-1) = alpha * sum over k of (1 - alpha)^k * x(t-k)`

This is a one-pole low-pass filter, the digital twin of an RC circuit: a capacitor charging through a resistor. It has fixed storage and forgets the past gradually, which is what you want when the scene can change. Three numbers make it intuitive:

- **Effective sample count.** For independent noisy inputs, the output variance is alpha/(2 - alpha) times the input variance. So an EMA behaves like an average of `N = (2 - alpha)/alpha` frames. alpha = 0.1 is about 19 frames; alpha = 0.04 (the low end Brian Karis describes for UE4's TAA) is about 49.
- **Half-life.** A sample's weight halves after ln(2)/(-ln(1 - alpha)) ~ 0.69/alpha frames: ~7 frames at 0.1, ~17 at 0.04. That is how long a ghost lingers.
- **Frame-rate independence.** `alpha = 1 - exp(-dt / tau)` with tau in seconds.

Karis's slides show that for small alpha the EMA approaches the simple average, which is why the two methods blend naturally: **start with 1/n and switch to a fixed alpha once 1/n drops below it.** loicvdb's "Path traced GI" does this with a capped sample count in alpha (`Wt3XRX/buffer_c.glsl:104-114`), which also lets old samples age out when lighting changes.

### 3.2 Progressive path tracing, the practical rules

- **Seeds.** Each pixel needs a different random sequence each frame: hash the pixel coordinate together with the frame number into an integer state and draw numbers from an integer hash (Wolfe uses a Wang hash). Correlated seeds show up as structured noise: diagonal streaks or a fixed pattern that never averages away.
- **Reset on change.** Any camera move, resize or parameter change invalidates the average. Store the camera in state texels and compare.
- **Accumulate in linear light.** Average radiance, then tone-map and gamma-encode only in the Image pass. Averaging gamma-encoded values darkens edges and shifts colours.
- **Fireflies.** Rare, very bright paths (a diffuse bounce that happens to hit the sun) produce single white pixels that take thousands of frames to average out. Clamping each sample's luminance removes them at the price of slightly darker, biased results. loicvdb clamps indirect light more strictly while the sample count is low (`Wt3XRX/buffer_c.glsl:114`).
- **Temporal reuse with a moving camera.** Instead of resetting, reproject: find where this pixel's surface point was last frame, fetch the old average there, and continue it. loicvdb stores world positions in a separate buffer (`Wt3XRX/buffer_b.glsl`), projects the hit point into the previous camera, searches a 3x3 neighbourhood of the previous frame for the texel whose stored position is closest, and only trusts it if the distance is below a threshold scaled by the pixel's footprint (`Wt3XRX/buffer_c.glsl:64-86`). That is the same idea as TAA's history rejection, done with geometry instead of colour.

### 3.3 TAA: temporal anti-aliasing (Karis 2014, and what followed)

TAA turns the EMA into a supersampler. Brian Karis presented Unreal Engine 4's version at SIGGRAPH 2014 (Advances in Real-Time Rendering); Lasse Jon Fuglsang Pedersen's GDC 2016 talk on Playdead's INSIDE is the clearest worked implementation; Marco Salvi's GDC 2016 talk added variance clipping; Emilio Lopez's 2022 blog and the Yang, Liu and Salvi survey (2020) collect the field. The pipeline:

1. **Jitter.** Each frame, shift the projection by a sub-pixel offset so each pixel's single sample lands at a different spot inside the pixel. The offsets come from a low-discrepancy sequence so samples never clump in space or time; Karis found Halton(2,3) good enough (8 samples), Pedersen ended on the first 16 of Halton(2,3). The Halton number for index i in base b is the radical inverse: write i in base b, mirror the digits around the decimal point.
2. **Reconstruct the current sample.** Karis notes a box filter is unstable under motion and uses a Gaussian fit to Blackman-Harris, `W(x) = exp(-2.29 x^2)`, about two pixels wide.
3. **Reproject.** Find where this pixel's surface was last frame: world position from depth, multiplied by last frame's view-projection matrix (static scenes), or a per-pixel velocity buffer for moving objects. Remove the jitter from the velocity, or a still image streaks.
4. **Dilate velocity at edges.** A silhouette pixel half-covered by a moving object should move with the object. Both Karis and Pedersen take the velocity of the front-most (closest depth) texel in the 3x3 neighbourhood.
5. **Sample the history with a sharp filter.** Bilinear resampling blurs a little every frame and the blur compounds; a Catmull-Rom bicubic (negative lobes) holds sharpness. Implementations reduce it to 9 or 5 bilinear taps.
6. **Constrain the history.** History is only trustworthy if it looks like something the current frame could contain. Take the min and max colour of the current frame's 3x3 neighbourhood: a box in colour space. If history falls outside, it is stale (disocclusion, lighting change) and is pulled in. Karis's refinements, all adopted by Pedersen: average the 3x3 box with the 5-tap "+" box so the result looks round instead of square; build the box in YCoCg (luma plus two chroma axes; Y = (R + 2G + B)/4, Co = (R - B)/2, Cg = (-R + 2G - B)/4), where luma varies a lot and chroma little, so the box is tighter; and **clip instead of clamp**: move the history colour along the line toward the box centre until it touches the box, instead of clamping each channel, which piles colours into the box's corners. Clip toward centre in math: with centre c = (min+max)/2 and half-extent e = (max-min)/2, let v = history - c and m = the largest of |v_i/e_i|; if m > 1 the clipped history is c + v/m.
7. **Variance clipping (Salvi).** Replace min/max with mean mu and standard deviation sigma of the neighbourhood, box = mu +/- gamma * sigma, gamma around 1. Tighter on noisy content, so less ghosting. ThomasSchander's "Enscape Cube" does this in YCoCg with gamma 0.75 and a history weight of 0.95 (`4dSBDt/buffer_c.glsl:28-53`).
8. **Blend.** Final = mix(current, constrained history, 1 - alpha), alpha around 0.04 to 0.1.
9. **Fight HDR flicker with luminance weighting.** A tiny very bright highlight dominates any average and flickers as jitter moves it in and out of the pixel. Karis weights each sample by `1/(1 + luma)`, or equivalently maps colour through the reversible curve `T(c) = c/(1 + luma)` before averaging and `T^-1(c) = c/(1 - luma)` after. Bright samples count less, chroma is preserved.
10. **Anti-flicker.** When history is near the clamp boundary, a missing sub-pixel feature gets clamped every few frames, a sawtooth that reads as flicker. Karis lowers the blend factor where history is close to being clamped.
11. **Fallbacks.** Pedersen blends the output (not the history) toward a motion-blurred current frame as on-screen speed rises, trusting history fully below 2 pixels per frame and not at all above 15. Karis's "responsive AA" stencil flag gives small particles almost no history.

Karis's slide title "Temporal AA is a firewall" names the architectural consequence: put TAA before bloom, depth of field and other post effects so they receive stable, anti-aliased input. A second consequence he highlights is the free denoiser: any stochastic effect (screen-space reflections with few steps, soft shadows, volumetrics) can use one noisy sample per pixel per frame and let TAA average it.

**TAA artifacts and their on-screen signatures**

| artifact | what you see | usual cause | usual fix |
|---|---|---|---|
| ghosting | a faint copy of an object trailing behind it | history not rejected after disocclusion | neighbourhood clip, variance clip, depth/ID tests |
| smearing | moving surfaces look motion-blurred and lose texture | missing or wrong velocity | velocity for everything that moves, dilation |
| blur | a static image slowly loses sharpness | bilinear history resampling compounding | Catmull-Rom history, mild sharpen |
| flicker | static thin bright lines pulse | repeated clamping of sub-pixel features | luminance weighting, anti-flicker blend reduction |
| crawling | edges shimmer during slow camera pans | too few jitter positions, or jitter not removed from velocity | longer Halton cycle, unjitter |
| streaks on still images | a stationary scene drifts or streaks | velocity imprecision | high-precision velocity buffer |

On Shadertoy, iq's "Rainforest" and reinder's "Himalayas" use a stripped-down version: dither the ray inside the pixel, reproject the hit into the previous camera (stored in state texels), blend 1/8 new with 7/8 old, and skip history when the mouse or resolution changed (`MdGfzh/buffer_c.glsl:156-170`, credited by reinder to iq's `4ttSWf`).

---

## 4. Cellular automata: rules on a grid

### 4.1 Discrete automata

Each texel is a cell; the rule reads the eight neighbours and returns the new state. Conway's Game of Life: count live neighbours n; a dead cell is born if n = 3; a live cell survives if n = 2 or 3; otherwise it is dead. Written as birth/survival sets this is B3/S23, and every other "Life-like" rule is another pair of sets, which a bitmask encodes cheaply (birth mask with bit 3 set, survival mask with bits 2 and 3 set).

GPU specifics: read neighbours with `texelFetch` (never a linear filter, which would blend states); decide the topology (wrap with modulo for a torus, or treat outside as dead); keep the state exactly 0 or 1. Extra channels make it pretty for free: store age (frames since birth) or a slowly decaying "trail" of recent life in another channel, and colour by those. That is how most beautiful Life shaders are lit.

### 4.2 Continuous automata

Stephan Rafler's **SmoothLife** (2011) replaces the 3x3 count with two filled discs, an inner disc (the cell) and an outer ring (the neighbourhood), and the birth/survival sets with smooth intervals of ring filling; it produced the first reported gliders in a continuous 2D automaton. Bert Wang-Chak Chan's **Lenia** (2019) generalises further:

`A(t + dt) = clip(A(t) + dt * G(K * A(t)), 0, 1)`

where `K * A` is a convolution of the state with a ring-shaped kernel of radius R (a smooth bump on a ring, possibly several rings with different peak heights), dt = 1/T, and the growth function is a bell curve shifted to [-1, 1]: `G(u) = 2 exp(-(u - mu)^2 / (2 sigma^2)) - 1`. Life is the special case R = T = 1 with a rectangular kernel. Chan's best-known creature, Orbium, lives at roughly mu ~ 0.15, sigma ~ 0.015, R ~ 13, T ~ 10 (check the paper before relying on these).

Cost: the kernel is large (radius 13 means ~530 taps per pixel). On Shadertoy that is fine at moderate resolution; for big kernels people separate it, compute it at lower resolution, or use FFT convolution.

### 4.3 Mistakes

- Life dies instantly or fills the screen: neighbour reads off by one texel (half-texel offset again) or the cell counts itself.
- Patterns look square-biased: using only 4 neighbours, or an anisotropic stencil.
- Lenia blobs flicker and die: dt too large for the chosen sigma.

---

## 5. Reaction-diffusion: Turing patterns from two chemicals

### 5.1 Gray-Scott

Two chemicals, A (food) and B (the reproducer). As Karl Sims explains it, two B's convert an A into another B, A is fed in everywhere, B is removed everywhere, and both diffuse, A faster than B. In equations (Pearson 1993; R. P. Munafo's notation):

- `dA/dt = D_A * lap(A) - A*B^2 + f*(1 - A)`
- `dB/dt = D_B * lap(B) + A*B^2 - (k + f)*B`

Term by term: `lap` (the Laplacian) is "how much my neighbours exceed me", so `D * lap` is diffusion. `A*B^2` is the reaction. `f*(1 - A)` feeds A back toward 1. `(k + f)*B` removes B. Karl Sims's working values: `D_A = 1.0, D_B = 0.5, f = 0.055, k = 0.062, dt = 1.0`, a 3x3 Laplacian with centre weight -1, edge neighbours 0.2, diagonal neighbours 0.05. Start with A = 1, B = 0 everywhere and a small seeded patch of B = 1.

Explicit Euler (new = old + dt * rate) is only stable if diffusion cannot move more than the cell holds in one step. With the plain 5-point Laplacian `(sum of 4 neighbours - 4*centre)/h^2` the 2D limit is `D * dt / h^2 <= 1/4`; with Sims's normalised stencil (whose weights already sum to zero with a centre of -1), `D * dt <= 1` is the comfortable bound, which is why his D_A = 1, dt = 1 sits right at the edge. Symptom of exceeding it: a checkerboard that grows and explodes.

**Isotropy.** The 5-point Laplacian has a slight square bias, visible as patterns preferring the grid axes. A 9-point stencil (edges weighted 4/6, corners 1/6, centre -20/6, all over h^2) is much rounder; cornusammonis uses exactly these weights (`XddSRX/buf_a.glsl:81-83`).

### 5.2 The parameter map

Everything interesting lives in a small window of (f, k). Pearson classified it; Munafo extended the classification and maps it interactively in "xmorphia". Selected classes with representative values from Munafo's page:

| class | f | k | behaviour |
|---|---|---|---|
| alpha | 0.010 | 0.047 | wavelets and fledgling spirals, chaotic |
| delta | 0.030-0.042 | 0.055-0.059 | true Turing patterns, hexagonal arrays of spots |
| epsilon | 0.018-0.022 | 0.055-0.059 | unstable spots that divide (mitosis) and die out |
| kappa | 0.050-0.058 | 0.063 | widening stripes, hedgerow mazes |
| lambda | 0.026-0.034 | 0.061-0.065 | solitons reproducing into hexagonal grids |
| mu | 0.046-0.058 | 0.065 | worms growing from their ends |
| xi | 0.010-0.014 | 0.041-0.047 | large sustained spirals, like the Belousov-Zhabotinsky reaction |
| pi | 0.062 | 0.061 | stable stripes, loops and spots |
| "U-skate world" | ~0.062 | ~0.0609 | Munafo's most studied region; outcome depends on initial conditions |
| rho / sigma | 0.090-0.110 | 0.052-0.059 | "soap bubbles" bordered by stripes |

Experts vary f and k across the image (a gradient map) to show several regimes in one picture, add anisotropic diffusion so patterns align to a flow, or advect the chemicals with a velocity field.

### 5.3 Making it look good

Treat B as a height field: compute its gradient, build a normal, and light it. The flat black-and-white pattern becomes embossed enamel, and with a specular term and a palette it reads as coral, skin or lacquer. Colour by `B`, by `A - B`, or by the gradient direction.

### 5.4 Flexi's variant: diffusion by blur

Flexi's "expansive reaction-diffusion" (`4dcGW2`) does not solve Gray-Scott. It diffuses by a separable 9-tap Gaussian blur in two passes (horizontal in Buffer B, vertical in Buffer C, `4dcGW2/buf_b.glsl`), reacts using the difference between the sharp field and its blurred version (a difference of Gaussians: an activator that spreads short and an inhibitor that spreads long, Turing's mechanism in its most direct form), and pushes the field along the gradient of the blurred copy so patterns grow outward (`4dcGW2/buf_a.glsl:108-117`). Separable blur costs 2 x 9 taps instead of 81, and wide blurs give large-scale patterns cheaply. Repeating the trick at several blur radii is Jonathan McCabe's multi-scale Turing pattern idea.

---

## 6. Wave-equation ripples: interactive water in one buffer

### 6.1 Derivation

Small surface waves obey the wave equation `d2h/dt2 = c^2 * lap(h)`: acceleration of the surface is proportional to how much it sticks up relative to its neighbours. Discretise time with a centred difference and space with the 5-point Laplacian:

`h(n+1) = 2*h(n) - h(n-1) + r^2 * (N + S + E + W - 4*h(n))`, with `r = c * dt / dx` (the Courant number)

This needs two time levels, so store `h(n)` and `h(n-1)` in two channels of one buffer. Stability (the CFL condition: information may not cross more than one cell per step) requires `r^2 <= 1/2` in 2D. Now set `r^2` exactly to 1/2: the `2*h(n)` and `-4*h(n)/2` cancel, leaving

`h(n+1) = (N + S + E + W)/2 - h(n-1)`

which is precisely Hugo Elias's famous 1990s "2D water" rule: half the neighbour sum minus the old value, then multiply by a damping factor slightly below 1. It is the wave equation running exactly at its stability limit, which is why it is so lively and why it needs damping to stay tame.

The house already runs a variant: Moonwater's 256 x 256 height/velocity field (`arsenal/web/piano/spectacle-worlds.js:9-25`) uses the equivalent first-order form (velocity += c^2 * lap(h) * dt, then h += velocity * dt, a symplectic Euler step), adds a weak restoring spring and exponential damping, absorbs waves in a soft "sponge" band near the edges instead of reflecting them, and keeps the Courant number below 0.4 by stepping at 120 Hz.

### 6.2 Obstacles and depth (iWave)

Jerry Tessendorf's iWave method (in "Simulating Ocean Water" and his Game Programming Gems article) uses the same explicit two-level update, but replaces the Laplacian term with a convolution kernel equal to `g * sqrt(-lap)` so that every wavelength travels at the speed deep water would give it (dispersion). His surprising practical finding: to make waves reflect off an object, simply multiply the height field by a mask that is 0 inside the object and 1 outside (soft at the edges) after every step. Reflections and diffraction around the object appear correctly. Shallow bottoms are handled by swapping in kernels built for each depth.

### 6.3 Rendering ripples

- **Normals** by central differences of h.
- **Refraction**: offset the lookup of the pool-floor image by the surface slope times a depth factor.
- **Caustics** (the bright dancing net on the floor): each small patch of surface bends light onto a patch of floor; by conservation of energy the floor brightness scales with the ratio of the two areas, `I_floor ~ I_light * A_surface / A_floor`. Evan Wallace's WebGL Water renders a mesh of refracted surface points onto the floor and computes that area ratio per pixel with screen-space derivatives (the size of the dFdx/dFdy parallelogram before and after refraction). In a pure fragment shader you can approximate the same ratio from the Jacobian of the refraction map (how much the offset field stretches or squeezes).

---

## 7. Stable fluids: Stam's method in ping-pong buffers

### 7.1 The equations, in plain words

Incompressible flow (smoke, ink in water) obeys the Navier-Stokes equations:

- `du/dt = -(u . grad)u - grad(p)/rho + nu * lap(u) + F`
- `div(u) = 0`

Read left to right: velocity u changes because it is carried along by itself (advection), pushed from high to low pressure, smoothed by viscosity nu, and pushed by external forces F. The second line says the fluid neither compresses nor expands: as much flows into any cell as flows out. Anything carried by the flow (dye, smoke density, temperature) obeys the simpler advection-diffusion equation `dq/dt = -(u . grad)q + kappa * lap(q) + sources`.

### 7.2 Operator splitting

Jos Stam's insight (SIGGRAPH 1999 "Stable Fluids", and the game-ready GDC 2003 "Real-Time Fluid Dynamics for Games") is to apply each term separately, in sequence, each with a method that can never blow up regardless of time step. Mark Harris's GPU Gems chapter 38 (2004) maps it onto textures, which is the version everyone on Shadertoy descends from:

1. **Add forces** (mouse splats, buoyancy, vorticity confinement).
2. **Advect** velocity by itself, and dye by velocity.
3. **Diffuse** (often skipped for smoke; advection already smears more than enough).
4. **Project**: remove the divergence so the field is incompressible again.

The projection rests on the Helmholtz-Hodge decomposition: any vector field w is exactly a divergence-free part u plus the gradient of a scalar p. Solve for p from `lap(p) = div(w)`, subtract `grad(p)`, and what is left is divergence-free.

Order varies between implementations. Harris applies advection, diffusion, forces, then projection. Pavel Dobryakov's MIT-licensed WebGL fluid, a good modern reference, runs curl, vorticity force, divergence, pressure warm start, 20 pressure iterations, gradient subtraction, then advection of velocity and dye. The essential rule: **project after forces and before the velocity is used to advect dye**, so the dye is carried by an incompressible field.

### 7.3 Advection: run time backwards

The forward idea ("move each cell's contents along its velocity") is a scatter, unstable and unsuited to a GPU. Stam's semi-Lagrangian method is a gather: to find the new value at cell x, trace a virtual particle backwards along the velocity to where it came from and read the old field there with bilinear interpolation:

`q_new(x) = q_old(x - dt * u(x))`

Because the result is always an interpolation of existing values, it can never exceed the old minimum or maximum: unconditionally stable. This is the single most important trick in real-time fluids.

Upgrades:

- **Better backtrace.** Plain Euler traces a straight line, so fast swirls lose angular momentum. A midpoint (second-order Runge-Kutta) trace samples velocity at the halfway point: `x_mid = x - (dt/2) u(x)`, `x_dep = x - dt * u(x_mid)`. trirop's "Multistep Fluid Simulation" uses fourth-order Runge-Kutta for the trace (`MdSczK/buf_a.glsl:7-14`); Wyatt's Lattice Boltzmann shader traces in two half steps (`WdyGzy/buffer_a.glsl:15-19`).
- **Less blur: MacCormack.** Every bilinear read is a small blur, and it compounds every frame: this numerical diffusion is why naive fluids look like thick syrup. Selle, Fedkiw, Kim, Liu and Rossignac (2008) fix it cheaply: advect forward to get phi_hat; advect phi_hat backward to get phi_back; the difference between phi_back and the original is twice the error, so correct `phi_new = phi_hat + (phi_original - phi_back)/2`; then clamp the result to the min and max of the four texels the forward read used, falling back to plain semi-Lagrangian where the clamp triggers. Costs one extra advection pass; dye stays crisp.
- **Dissipation.** Multiply by `1/(1 + rate * dt)` (Dobryakov) or `exp(-rate * dt)` per step so dye fades and velocity calms.

### 7.4 Diffusion and pressure: the Jacobi solver

Both implicit diffusion and the pressure equation are Poisson-type systems, solved with **Jacobi iteration**: each texel repeatedly replaces its value by a weighted average of its neighbours plus a source term, ping-ponging between two textures.

- Implicit diffusion (Stam): `x = (x0 + a*(N + S + E + W)) / (1 + 4a)` with `a = dt * nu / h^2`, about 20 iterations. Implicit means you ask "what field, diffused forward, gives what I have now?", which can never overshoot.
- Pressure (Harris): `p = (p_N + p_S + p_E + p_W - h^2 * div) / 4`, 20 to 80 iterations; then `u = w - (p_E - p_W, p_N - p_S) / (2h)`; divergence by central differences `div = ((u_E - u_W) + (v_N - v_S)) / (2h)`.

**Why so many iterations, and why it is still never enough.** Each Jacobi iteration moves information exactly one cell, like a rumour passed hand to hand. A pressure disturbance cannot "feel" a wall 100 cells away in fewer than 100 iterations, and the smoothest error modes shrink by a factor of only about `cos(pi/N)` per iteration, roughly `1 - 4.9/N^2`, so full convergence on an N-cell grid takes on the order of N^2/5 iterations (thousands at N = 128). Everyone stops early. The fluid is then slightly compressible, which looks like springiness or local "breathing". Experts hide this four ways:

1. **Warm start.** Start the solve from last frame's pressure (scaled down a bit: Dobryakov multiplies by 0.8) instead of zero. Most of the answer carries over.
2. **Amortise across frames.** Do one or a few iterations per frame and let the solve converge over time. cornusammonis's "Suture Fluid" (MIT, `XddSRX/buf_a.glsl:79-170`) is the extreme: one buffer holds velocity and a running pressure-like scalar, each frame does one smoothing step of each plus advection, and it rotates the velocity by an angle proportional to local curl to amplify vortices. One pass per frame, wildly organic results.
3. **Multigrid through mipmaps.** Large-scale pressure needs coarse grids, exactly like a cache hierarchy where the far-away answer lives in a bigger, coarser level. cornusammonis's "Multiscale MIP Fluid" (`tsKXR3/common.glsl:13-99`) reads the buffer's mipmap levels with `textureLod` and combines turbulence, curl, confinement and pressure-like terms across all scales with per-scale weight functions.
4. **Bake the iterations into one kernel.** k Jacobi iterations starting from zero pressure are a fixed linear function of the divergence: a single (wide) convolution. trirop precomputed the weights of 20 iterations and evaluates them as one stencil of several hundred taps (`MdSczK/buf_c.glsl`, about 1 200 lines of weights), trading memory traffic for the pass count Shadertoy limits.

### 7.5 Forces that make it look alive

- **Splats.** Add `amount * exp(-|x - centre|^2 / r^2)` to velocity (in the drag direction) and to dye.
- **Buoyancy.** `F = (alpha * (T - T_ambient) - beta * density) * up`: hot gas rises, heavy smoke sinks.
- **Vorticity confinement** (Fedkiw, Stam and Jensen 2001). Numerical diffusion kills small swirls; this puts the energy back exactly where swirls already are. Compute scalar vorticity `w = dv/dx - du/dy`; find `N = grad|w| / |grad|w||`, the direction pointing toward stronger swirl; add force `eps * h * (N_y * w, -N_x * w)` (the 2D form of N cross w). Dobryakov's default strength is 30. Too much and the flow turns into boiling noise.
- **Curl noise forcing** (section 8.4): a divergence-free stirring that needs no projection.

### 7.6 Boundaries

Harris's walls: velocity at the border is the negative of the interior neighbour (no-slip: the average across the wall is zero), pressure equals the interior neighbour (pure Neumann: no pressure gradient into the wall). Shadertoy shortcuts: wrap everything with `fract()` (a torus, no walls at all: `XddSRX` does this), or force velocity to a value in a border band (`MdSczK/buf_a.glsl:24-27` makes a wind tunnel). Arbitrary obstacles: an obstacle mask, velocity set to the obstacle's own velocity inside it, pressure copied from the fluid side.

### 7.7 Resolution and layout

Velocity is smooth, dye is detailed: simulate velocity at low resolution and advect dye at high resolution. Dobryakov defaults to a 128 simulation grid and a 1024 dye grid. A typical four-buffer Shadertoy layout: A = velocity advection plus forces; B = divergence plus one or more pressure iterations; C = more pressure iterations; D = projection plus dye advection; Image = shading. Plan where the one-frame lags fall (1.2).

### 7.8 Two other families worth knowing

- **Lattice Boltzmann.** Instead of velocity and pressure, store populations of particles moving in fixed directions. Wyatt's minimal version keeps four (right, left, up, down) in RGBA: velocity is the difference of opposite pairs, pressure is their mean, and each step streams populations to neighbours and relaxes them toward equilibrium (`WdyGzy/buffer_a.glsl:7-50`). No global pressure solve: everything is local, which suits a GPU perfectly.
- **Reintegration tracking** (Mykhailo Moroz, "michael0884" on Shadertoy). Each cell stores a little blob of fluid: mass, centre of mass and velocity. Each step, a cell looks at its neighbours, moves each neighbour's blob forward by its velocity, treats it as a small box of half-width about 0.55 to 0.6 pixels, and keeps the part of the box that overlaps itself: mass is the overlap area, position and velocity are mass-weighted averages. Because overlap fractions always sum to one, **mass is conserved exactly**, which semi-Lagrangian advection cannot promise. Pressure forces come from an SPH-style sum over neighbours with a chosen equation of state (ideal gas for smoke, a stiff curve for water). It captures droplets and free surfaces at near-pixel precision. The neighbour search radius must cover the fastest blob's motion per step. Corpus: `WtfyDj` ("Paint streams"), especially `common.glsl:136-192`.

### 7.9 Mistakes and their signatures

| symptom | cause |
|---|---|
| fine checkerboard in pressure or velocity | collocated central differences decouple odd and even cells; use a staggered grid, the 9-point stencil, or a little smoothing |
| fluid looks like syrup, swirls die in a second | numerical diffusion of bilinear advection; MacCormack, vorticity confinement, higher resolution |
| dye greys out to a uniform mush | dye dissipation too low, or repeated resampling; MacCormack, advect coordinates instead |
| everything slowly drifts one way | half-texel offset in the backtrace, or asymmetric boundary handling |
| sudden explosion to white or black squares | NaN from a normalise of zero, or dt spike from raw iTimeDelta |
| ink leaks through walls | boundary conditions applied before advection instead of after, or obstacle mask not used in advection |
| flow "breathes" and bounces | pressure under-converged; warm start, more iterations, multigrid |
| mass disappears (water level drops) | semi-Lagrangian is not conservative; reintegration tracking or periodic renormalisation |

---

## 8. Particles stored in textures

### 8.1 Stateless versus stateful

Lutz Latta's "Building a Million-Particle System" (GDC 2004) is the founding text. **Stateless** particles are a closed-form function of their birth time: position(t) = start + v0*t + g*t^2/2. Free to evaluate anywhere, but they cannot react to the world. **Stateful** particles store position and velocity in floating-point textures, one texel per particle (the texel coordinate *is* the particle's identity), double buffered, and integrate each frame in a fragment pass. Latta also keeps static attributes (birth time, type) in a separate texture that needs no double buffering.

### 8.2 Integrators

- **Euler**: `v += a*dt; x += v*dt` (do velocity first: the semi-implicit or symplectic variant, which keeps orbits from spiralling outward).
- **Verlet**: `x_new = 2x - x_prev + a*dt^2`. No velocity storage, velocity is implicit in the two positions, very stable for constraints (cloth, hair), but collisions must be handled by moving positions.

### 8.3 Forces and collisions (Latta's catalogue)

Gravity and wind as constant accelerations; attraction or repulsion to points; following a flow field with Stokes drag `F = 6*pi*eta*r*(v_flow - v)`, which in practice means "relax velocity toward the flow"; collisions against planes or height fields: split velocity into normal and tangent parts, `v_n = (v . n) n`, `v_t = v - v_n`, then `v' = -e*v_n + (1 - mu)*v_t` with restitution e and friction mu. Clamp acceleration and speed (iapafoto's fish do, `ldd3DB/buffer_a.glsl:38-44`); unbounded forces are the usual cause of particles vanishing to infinity (and NaN).

### 8.4 Curl noise: the best free flow field

Robert Bridson, Jim Hourihan and Marcus Nordenstam (SIGGRAPH 2007) showed that if you take a smooth noise field psi and use its rotated gradient as velocity, `v = (d psi/dy, -d psi/dx)`, the field is divergence-free by construction: particles swirl and never bunch into sinks or tear apart at sources. It is the cheapest way to make particles and feedback warps look like real fluid, no solver needed. Obstacles bend it by ramping psi to zero near surfaces.

### 8.5 The gather problem: drawing particles in a fragment shader

A fragment shader cannot "draw a dot at the particle's position". Options, from simple to clever (Moroz's "Overview of Shadertoy particle algorithms" catalogues these):

1. **Loop over all particles per pixel.** Fine for tens; ruinous for thousands (1.5). iapafoto's shoal: 40 fish stored in row 0 (`.xy` position, `.zw` velocity, texels outside the row discarded), O(N^2) forces in Buffer A, and the Image pass loops all 40 to draw each fish as a signed-distance shape (`ldd3DB`).
2. **Voronoi tracking.** Each pixel stores the IDs of the few particles nearest to it; each frame it updates that list from its own and its neighbours' lists (a jump-flood style propagation, reusing last frame as the first guess). Drawing and neighbour search become local. Linear cost, but particles moving more than the search radius per frame get lost.
3. **Particles as cells.** One particle per pixel that hops between cells (cellular-automaton tracking), or the reintegration tracking of 7.8, where the "particle" is a mass blob in each cell.
4. **Real scatter.** Outside Shadertoy (WebGL2 and three.js, which the house uses), draw particles as points whose vertex shader reads position from the state texture: the standard GPU particle architecture, millions at once. Latta sorted for alpha blending with a GPU odd-even merge sort spread over many frames.

### 8.6 Mistakes

- Particles snapping to whole pixels: fp16 position storage (1.4); store positions relative to a tile or in fp32.
- All particles collapsing to one point or exploding: forces without clamps, or zero-distance division in pairwise forces (iapafoto adds a tiny random push when two fish coincide).
- Invisible GPU timeouts: per-pixel loops over too many particles (1.5).

---

## 9. Oceans

### 9.1 The physics you need

Water particles under a passing wave move in near circles, not up and down. Waves are dispersive: their speed depends on wavelength. With wavenumber k = 2*pi/wavelength and angular frequency omega, the **dispersion relation** is:

- deep water: `omega^2 = g * k`
- finite depth D: `omega^2 = g * k * tanh(k * D)` (reduces to deep water when kD is large)
- capillary ripples (around 1 cm): `omega^2 = g * k * (1 + k^2 * L^2)`, L a small surface-tension length

Phase speed is `c = omega/k = sqrt(g/k)` in deep water: long swells outrun short chop, like a prism separating colours. Getting this relation right is most of why a simulated sea "moves right"; random speeds look like jelly.

### 9.2 Gerstner (trochoidal) waves

Fournier and Reeves brought them to graphics in 1986; Tessendorf's notes and Mark Finch's GPU Gems chapter 1 are the standard references. Each surface point, labelled by its rest position x0, moves in a circle:

- horizontal: `x = x0 - sum_i (k_i/|k_i|) * A_i * sin(k_i . x0 - omega_i * t + phi_i)`
- vertical: `y = sum_i A_i * cos(k_i . x0 - omega_i * t + phi_i)`

Why crests sharpen: for one wave along x, `dx/dx0 = 1 - k*A*cos(theta)`. At the crest (theta = 0) this is smallest, so surface points bunch together at the top (sharp crest) and spread apart at the bottom (broad trough). If k*A > 1 it goes negative: the surface folds through itself and forms a loop; Tessendorf's phrase for it is that "the insides of the wave surface are outside". So the dimensionless **steepness** s = k*A must stay below 1, and for a sum of waves the steepnesses must add up to at most 1 (Finch normalises with a global Q shared across waves; Jasper Flick's Catlike Coding tutorial parameterises each wave by steepness directly, A = s/k).

Normals come analytically: differentiate the displaced position with respect to the two rest coordinates (two tangent vectors), cross them. No finite differences, no extra evaluations.

Choosing waves (Finch): pick a median wavelength, draw wavelengths between half and double it, keep amplitude proportional to wavelength, take speed from the dispersion relation, and draw directions within a cone around the wind. Geometry carries a few big waves; most visible detail comes from many small waves in a normal map. And filter: a mesh edge must be shorter than half the shortest wave it carries, so fade out waves shorter than about four edge lengths.

**Looping**: if every omega is a whole multiple of `omega0 = 2*pi/T`, the sea repeats after T seconds. Tessendorf quantises: `omega_bar(k) = floor(omega(k)/omega0) * omega0`; the longer T, the closer to true dispersion.

### 9.3 Sum-of-sines without the loops: shader tricks

Most Shadertoy oceans are not Gerstner; they displace height only, using shaped waves:

- **Sharpened sine** (Finch): `A * ((sin(theta) + 1)/2)^p`, p > 1 sharpens crests.
- **Exponential sine** (afl_ext, MIT, `MdXyzX/image.glsl:16-21`): `exp(sin(x) - 1)` has a pointed crest at 1 and a long flat trough near e^-2. Its derivative is simply itself times cos(x), so normals are cheap.
- **Drag** (afl_ext, `MdXyzX/image.glsl:24-56`): after each octave, nudge the sample position along the wave direction by that octave's slope times a drag factor. Later, smaller octaves then bunch up on the crests of earlier ones, imitating how short waves ride and cluster on long ones. One line, a large realism gain.
- **Octave rotation and lacunarity**: rotate and scale coordinates between octaves by a fixed matrix so directions never align; amplitude falls faster than frequency rises.
- **Ridged chop** (TDM's Seascape, `Ms2SD1/image.glsl:66-72`): build each octave from `1 - |sin|` blended with `|cos|` and raised to a "choppy" power, domain-warped by noise, summed for two opposite time directions so the sea neither scrolls nor stands still. Choppiness relaxes toward 1 with each finer octave (`Ms2SD1/image.glsl:86`).

### 9.4 Tessendorf's statistical FFT ocean

Oceanographers model the sea as a random field whose energy at each wavevector follows a measured spectrum. Tessendorf's 2001 course notes (rev. 2004), used for Waterworld and Titanic, turn that into graphics:

1. **Height as a Fourier sum.** `h(x, t) = sum over k of h~(k, t) * exp(i k . x)`, with k on an N x M grid, `k = (2*pi*n/Lx, 2*pi*m/Lz)`. An inverse FFT evaluates the whole grid at once.
2. **Spectrum.** Tessendorf's Phillips spectrum: `P(k) = A * exp(-1/(k L)^2) / k^4 * |k_hat . w_hat|^2`, where `L = V^2/g` is the largest wave a wind of speed V can raise and w_hat is the wind direction. The cosine-squared factor kills waves perpendicular to the wind (raising it to a higher power aligns them more). Multiply by `exp(-k^2 l^2)` with a small length l to suppress the tiniest waves, which the raw formula handles badly.
3. **Random amplitudes.** `h0(k) = (xi_r + i xi_i) * sqrt(P(k)/2)`, with xi independent standard Gaussian draws (Box-Muller from two uniforms on the GPU).
4. **Animation in closed form.** `h~(k, t) = h0(k) exp(i omega(k) t) + conj(h0(-k)) exp(-i omega(k) t)`. Pairing k with -k this way keeps the final height real. Any time t can be computed directly with no simulation history.
5. **Slopes exactly.** `grad h = sum of i k h~ exp(i k . x)`: two more inverse FFTs. Tessendorf prefers this to finite differences, which misrepresent the shortest waves.
6. **Choppiness.** Horizontal displacement `D(x, t) = sum of -i (k/|k|) h~ exp(i k . x)`; final point = `x + lambda * D`. The same bunching as Gerstner, now for a statistical sea; lambda scales it.
7. **Foam from folding.** The Jacobian of the map x -> x + lambda*D is `J = Jxx*Jyy - Jxy^2` with `Jxx = 1 + lambda dDx/dx`, `Jyy = 1 + lambda dDz/dz`, `Jxy = lambda dDx/dz`. Where J < 0 the surface has folded: whitecaps. Tessendorf goes further: the smaller eigenvalue `J- = (Jxx + Jyy)/2 - sqrt(((Jxx - Jyy)/2)^2 + Jxy^2)` turning negative signals folding, and its eigenvector gives the direction of the fold. In practice foam = a smoothstep of (threshold - J), accumulated with slow decay in a feedback texture so it lingers and streaks (a feedback trail, section 2, painted onto the ocean).
8. **Sizes.** Grids from 16 to 2048 (128 to 512 suffice usually). Patch sizes from 10 m to 2 km. Tessendorf: grid spacing need not go below about 2 cm, should be far smaller than V^2/g, and the secret of realistic waves is as many grid points as you can afford. The patch tiles seamlessly, which shows as repetition near the horizon; production renderers layer several patches of incommensurate sizes ("cascades") to hide it (see Tcheblokov's War Thunder talk via gasgiant's reference list).
9. **Better spectra.** Christopher Horvath (DigiPro 2015) replaced Phillips with empirical spectra (JONSWAP and TMA, which includes depth) plus a directional spreading model with a "swell" parameter that elongates waves into parallel trains, the current state of practice.

**Interactivity limit**: the FFT gives the whole surface or nothing; it cannot respond to a boat. That is what iWave (6.2) is for, and production combines both.

### 9.5 The GPU FFT

The inverse FFT is log2(N) "butterfly" passes along rows then log2(N) along columns, ping-ponging between two textures; each pass combines pairs of entries with a twiddle factor `exp(+/- 2 pi i j / 2^(s+1))`. Pack two complex numbers per RGBA texel so one transform carries, say, height and one displacement component. The Stockham ordering avoids a separate bit-reversal pass. A sign flip of (-1)^(x+y) recentres the zero frequency. At N = 256 that is 16 passes per transform: trivial in WebGL2 with real render targets, awkward on Shadertoy with four buffers (people either run one stage per buffer per frame, accepting latency, evaluate a small direct transform per pixel, or skip FFT for sum-of-sines). Fynn-Jorin Flugge's 2017 thesis walks through a full GPU pipeline.

### 9.6 Rendering the sea: heightfield ray marching

With a height function H(x, z), a camera ray `p(t) = o + t*d` hits the sea where the gap `f(t) = p_y(t) - H(p_x(t), p_z(t))` crosses zero. Signed-distance sphere tracing does not apply directly because H is not a distance. The ideas that matter:

- **A safe step from a slope bound.** If the surface slope never exceeds s, the gap can shrink at most at rate `|d_y| + s*|d_xz|` per unit of t, so stepping `t += f(t) / (|d_y| + s*|d_xz|)` can never jump through the surface. Smaller divisor = faster but riskier. Inigo Quilez's terrain-marching article covers the related practical forms: grow the step with distance, interpolate between the last two samples for the hit.
- **Bracket and refine.** TDM's Seascape never steps blindly: it evaluates the gap at the start and at a far point, then repeatedly interpolates the zero crossing between a point known to be above the surface and one known to be below (regula falsi), keeping whichever side the new point lands on (`Ms2SD1/image.glsl:135-158`). 32 iterations converge on smooth water.
- **Bound the search.** Water lives between two planes (crest height and trough depth). Intersect those planes analytically first and march only the slab between (afl_ext, `MdXyzX/image.glsl:181-196`). If the march fails, fall back to the top plane: far away, nobody can tell.
- **Two levels of detail.** March with a cheap height (Seascape: 3 octaves; afl_ext: 12) and compute normals with an expensive one (5 octaves; 36). The silhouette needs little detail; the lighting needs a lot (`Ms2SD1/image.glsl:14-15`, `MdXyzX/image.glsl:9-10`).
- **Normal epsilon grows with distance.** A fixed finite-difference step samples sub-pixel detail far away and sparkles. Use the pixel footprint: about `t * 2*tan(fov/2) / resolution_y`. Seascape scales its epsilon with squared distance (`Ms2SD1/image.glsl:175`); the effect is the same, a free distance-based filter.

### 9.7 Shading water

Tessendorf decomposes what the camera sees above the sea into reflected sun, reflected sky and light scattered up out of the water body, weighted by the Fresnel reflectivity r and transmissivity t = 1 - r.

- **Fresnel.** Schlick's approximation `F = F0 + (1 - F0)(1 - cos theta)^5`. For water (refractive index ~1.33), `F0 = ((n - 1)/(n + 1))^2 ~ 0.02`: looking straight down you see 2% reflection and the body colour; at grazing angles the sea becomes a mirror of the sky. This one curve is the most important water-shading term. Seascape uses a cheaper cubic curve capped at 0.5 (`Ms2SD1/image.glsl:109-110`), an artistic choice.
- **Body colour and absorption.** Light through water decays per channel by Beer-Lambert, `T = exp(-sigma * distance)`, red absorbed fastest: depth turns blue-green. Add a scatter term brighter on wave tops (where light passes through thin water, Seascape adds a height-based tint, `Ms2SD1/image.glsl:117-118`).
- **Sun glitter far away.** Tessendorf notes that distant sun reflections spread into a broad diffuse patch, because the many waves smaller than a pixel act like microfacets (Cox and Munk's glitter studies). Shader version: shrink the specular exponent (widen the highlight) with distance; Seascape does this (`Ms2SD1/image.glsl:120`).
- **Foam** from the Jacobian (9.4), from steepness, or from shore distance.
- **Tone mapping last.** Water has a sun reflection thousands of times brighter than the body colour; render in linear HDR and tone-map at the end (afl_ext uses an ACES fit, `MdXyzX/image.glsl:152-167`).

### 9.8 Ocean mistakes and their signatures

| symptom | cause |
|---|---|
| black sparkles or inside-out crests | Gerstner steepness sum above 1, or FFT chop lambda too high (J < 0 everywhere) |
| the sea moves like jelly | frequencies not from the dispersion relation |
| visible tiling near the horizon | one FFT patch; add cascades or blend in noise |
| shimmering noise far away | normal epsilon and octave count not reduced with distance |
| holes or floating crest slivers at grazing angles | heightfield march overshoot; lower the step factor, add bracketing refinement |
| waves all aligned like a corrugated roof | directions without spread, or an octave matrix without rotation |
| flat dull water | no Fresnel, or reflections not in HDR |

---

## 10. Methodology: how to build any of these, and how to make them house modules

### 10.1 The simulation kernel contract

Every simulation in this report has the same five parts. Making that shape explicit is how one module change can reach every surface:

1. **State layout.** Which texture, which channel holds what, which texels are reserved for header data (resolution, frame, camera). Write it down as a table at the top of the shader.
2. **Init.** A pure function of pixel coordinate (and seed) that writes a valid first state. Must also run on reset and on resize.
3. **Step.** A pure function from old state to new state using only local reads (plus a few global uniforms). Fixed dt. Substeps when the frame is long.
4. **Inject.** Forces, splats, mouse, audio, MIDI: kept separate from the physics so the same step serves every input source (the piano's note impulses and a mouse drag are the same splat).
5. **Render.** Reads state, never writes it. All look (tone map, palette, grain) lives here.

A host runner then owns the plumbing once, for every sim: ping-pong targets, float format detection with fp16 fallback, fixed-step accumulator, reset/resize detection, a NaN guard, and a GPU time budget. Today Moonwater has its own copy of this plumbing (`spectacle-worlds.js:11-48`); it is the natural first consumer.

### 10.2 Debug views every sim should ship with

- Velocity as colour (hue = direction, brightness = speed).
- Divergence in red/blue (should be near zero after projection).
- Pressure, vorticity, the Jacobian, chemical B alone.
- A NaN detector: paint any non-finite texel magenta.
- A conservation meter: the 1x1 top mip level of the mass channel is its average; watch it over time to see leaks.

### 10.3 Tuning discipline

- Parameters in physical or per-second units, never per frame.
- Change one thing, watch it for ten seconds (sims have slow modes).
- Find the stability edge deliberately (raise dt until it breaks), then back off by a factor of two.
- Keep a parameter preset bank: Gray-Scott's (f, k) table above is literally a preset bank.

### 10.4 Suggested learning path (build in this order)

1. Feedback trail with half-life decay and a curl-noise warp. Learn ping-pong, texel centres, frame-rate independence.
2. Game of Life with an age channel. Learn texelFetch, exact state, wrap modes.
3. Gray-Scott with the 9-point Laplacian, f/k gradient map, embossed lighting. Learn stability limits and parameter maps.
4. Wave-equation ripples with mouse drops, obstacle mask, refraction and caustics. Learn second-order time stepping and CFL.
5. Stable fluid: velocity + dye at two resolutions, Jacobi pressure with warm start, vorticity confinement, then MacCormack. Learn the projection and numerical diffusion.
6. Particles in a texture driven by the fluid's velocity. Learn integrators and the gather problem.
7. Gerstner sea with analytic normals; then a heightfield-marched sum-of-sines sea with drag, Fresnel, absorption, distance LOD.
8. Progressive path tracer with reset; then reprojection.
9. TAA on top of the sea: jitter, reprojection, YCoCg variance clip, luminance weighting.
10. FFT ocean in WebGL2 with Jacobian foam accumulated in a feedback texture.

---

## 11. Common mistakes: symptom to cause to fix

| what you see | likely cause | fix |
|---|---|---|
| image slides diagonally and softens over time | half-texel offset in feedback read | read at `fragCoord` (centres) or with texelFetch |
| trails never fully disappear, grey residue | 8-bit buffer rounding | float buffer, subtract an epsilon, or dither |
| black or white squares that grow | NaN or Inf in the loop | guard normalise/sqrt/log/division, sanitise the state |
| sim explodes when the tab stutters | raw iTimeDelta as dt | fixed step, clamp, substeps |
| sim garbage after fullscreen | buffers invalid after resize | store resolution in a header texel and re-init |
| initial image missing or black | texture not loaded at frame 0 | initialise over the first ~30 frames |
| coupled fields jitter or lag | Shadertoy pass order lag | reorder passes, or accept a consistent one-frame lag |
| checkerboard growth | explicit step too large (diffusion/RD/wave) | reduce dt below the stability bound |
| patterns prefer grid axes | 5-point Laplacian | isotropic 9-point stencil |
| fluid looks like syrup | numerical diffusion | MacCormack, vorticity confinement, more resolution |
| path tracer stops improving, keeps noise | fp16 accumulation stall | fp32 accumulation, or EMA |
| structured noise that never averages away | correlated random seeds | integer hash of (pixel, frame) |
| white single-pixel sparks in a path tracer | fireflies | per-sample luminance clamp |
| ghost copies behind moving objects (TAA) | stale history | neighbourhood clip / variance clip |
| driver reset or frozen tab | too much work per pixel per frame | bound loops; budget fetches x pixels |

---

## 12. Primitive API for the house library

These are fresh signatures for `arsenal/web/glsl/` modules, grouped by the `cat` field they would carry in their `//!` header. Conventions: positions in **pixel space** (integer + 0.5 is a texel centre) unless named `uv`; `size` is the texture size in texels; every function is pure; a function that needs a scene-specific height calls a host-provided `float sceneHeight(vec2 xz, int lod)` (the module resolver reads that dependency from the call). Contracts are one line each.

### sim-io (state plumbing every simulation shares)

- `vec4 simLoad(sampler2D s, ivec2 p, ivec2 size, bool wrap)` - exact texel read; out-of-range coordinates wrap (torus) or clamp; never filters.
- `vec4 simSample(sampler2D s, vec2 pPix, vec2 size, bool wrap)` - manual bilinear read at a pixel-space position, identical on hosts where float textures are not filterable.
- `vec4 simHeader(vec2 res, float layoutVersion)` - value to store in texel (0,0) so the next frame can detect resize or layout change.
- `bool simNeedsInit(int frame, vec2 res, vec4 header, float layoutVersion)` - true on the first frames, after a resize, or when the stored layout version differs.
- `bool simKey(sampler2D keyboard, int keyCode, int row)` - keyboard texture query; row 0 held, 1 pressed this frame, 2 toggled.
- `vec4 simSanitize(vec4 v, float bound, vec4 fallback)` - replaces NaN/Inf components with the fallback and clamps magnitudes to the bound, so one bad texel cannot poison the loop.
- `uint simHash(uvec3 v)` - well-mixed integer hash of (x, y, frame) for per-pixel per-frame seeds.
- `float simRand(inout uint state)` - next uniform number in [0,1) from a per-pixel integer state.
- `vec2 simGauss2(inout uint state)` - two independent standard Gaussian numbers (Box-Muller).
- `float simDt(float frameDt, float fixedDt, float maxDt)` - clamped step for hosts that cannot substep.
- `float decayFromHalfLife(float halfLifeSec, float dt)` - frame-rate independent per-step multiplier exp(-ln2 dt/h).

### stencil (finite differences)

- `vec4 lap5(sampler2D s, ivec2 p, ivec2 size)` - 5-point Laplacian in texel units (neighbour sum minus four times centre).
- `vec4 lap9(sampler2D s, ivec2 p, ivec2 size)` - isotropic 9-point Laplacian (edges 4/6, corners 1/6, centre -20/6).
- `float div2(sampler2D vel, ivec2 p, ivec2 size)` - central-difference divergence of the .xy velocity.
- `float curl2(sampler2D vel, ivec2 p, ivec2 size)` - scalar vorticity dv/dx - du/dy by central differences.
- `vec2 grad2(sampler2D s, ivec2 p, ivec2 size, int channel)` - central-difference gradient of one channel.
- `vec4 blur9Axis(sampler2D s, ivec2 p, ivec2 size, ivec2 axis)` - one axis of a normalised 9-tap Gaussian; two calls make a separable blur.

### advect

- `vec2 departEuler(vec2 pPix, vec2 velPix, float dt)` - one-step backtrace of a semi-Lagrangian departure point.
- `vec2 departRK2(sampler2D vel, vec2 pPix, float dt, vec2 size)` - midpoint backtrace, keeps swirls round.
- `vec2 departRK4(sampler2D vel, vec2 pPix, float dt, vec2 size)` - fourth-order backtrace for fast rotating flow.
- `vec4 advectSL(sampler2D q, sampler2D vel, vec2 pPix, float dt, vec2 size)` - gather q at the RK2 departure point; never exceeds old min/max.
- `void advectBounds(sampler2D q, vec2 pPix, vec2 size, out vec4 lo, out vec4 hi)` - min/max of the four texels a bilinear read at pPix uses.
- `vec4 maccormackCombine(vec4 fwd, vec4 back, vec4 orig, vec4 lo, vec4 hi)` - fwd + (orig - back)/2, clamped to [lo, hi].
- `vec4 dissipate(vec4 q, float rate, float dt)` - q / (1 + rate dt).

### fluid

- `float jacobiPressure(sampler2D pressure, sampler2D divergence, ivec2 p, ivec2 size)` - one Jacobi sweep of lap(p) = div with Neumann edges.
- `vec2 projectVelocity(vec2 w, sampler2D pressure, ivec2 p, ivec2 size)` - subtract the pressure gradient, leaving a divergence-free velocity.
- `vec2 vorticityForce(sampler2D curlTex, ivec2 p, ivec2 size, float strength)` - confinement force pushing toward stronger nearby swirl.
- `vec2 buoyancyForce(float temperature, float ambient, float density, float lift, float weight)` - upward force from heat minus weight of smoke.
- `vec4 splat(vec2 pPix, vec2 centrePix, float radiusPix, vec4 amount)` - Gaussian injection of velocity or dye.
- `vec2 wallVelocity(vec2 vInterior, vec2 wallNormal, float slip)` - slip 0 gives no-slip (negated), slip 1 removes only the normal component.
- `vec2 curlNoise2(vec2 p, float t)` - divergence-free velocity from the rotated gradient of a noise stream function.
- `vec3 boxDeposit(vec2 cellMinPix, vec2 blobCentrePix, float halfWidth)` - reintegration tracking: overlap centre (xy) and mass fraction (z) of a moved blob inside a cell.

### wave (interactive surface waves)

- `float waveStep(float hNow, float hPrev, float neighbourSum4, float courant2, float damping)` - explicit 2D wave equation; courant2 = (c dt/dx)^2 must be at most 0.5.
- `vec3 heightNormal(sampler2D h, ivec2 p, ivec2 size, float heightScale)` - surface normal of a height texture by central differences.
- `float spongeAbsorb(vec2 uv, float bandWidth, float strength, float dt)` - per-step multiplier that soaks up waves near the borders instead of reflecting them.
- `float causticRatio(vec3 pSurface, vec3 pFloor)` - brightness gain = area before refraction / area after, from dFdx/dFdy of both positions.

### ocean

- `float waterOmega(float k, float depth)` - dispersion relation; depth at or below zero means deep water.
- `float omegaLooped(float omega, float periodSec)` - quantise to whole multiples of 2 pi / T so the sea loops exactly.
- `vec3 gerstnerWave(vec2 x0, vec2 dir, float wavelength, float steepness, float t, inout vec3 tangentX, inout vec3 tangentZ)` - displacement of one trochoidal wave; accumulates analytic tangents for the normal.
- `float phillipsSpectrum(vec2 k, vec2 windDir, float windSpeed, float amplitude, float smallWaveLen)` - Tessendorf's spectrum with the small-wave cutoff.
- `vec2 oceanH0(vec2 gauss, float spectrum)` - initial complex amplitude (xi_r + i xi_i) sqrt(P/2).
- `vec2 oceanHt(vec2 h0k, vec2 h0MinusK, float omega, float t)` - time evolution pairing k with -k so the field stays real.
- `vec2 cmul(vec2 a, vec2 b)` - complex multiply.
- `vec2 cexpi(float angle)` - exp(i angle) as (cos, sin).
- `vec4 fftStage(sampler2D src, ivec2 p, int stage, int n, bool horizontal, bool inverse)` - one radix-2 Stockham butterfly stage, two complex values per RGBA.
- `float foldJacobian(float dDxdx, float dDzdz, float dDxdz, float lambda)` - Jacobian of the choppy map; below zero means folding (foam).
- `float waveExpSine(float x, out float slope)` - sharp-crest profile exp(sin x - 1) and its derivative.
- `float heightMarch(vec3 ro, vec3 rd, float tNear, float tFar, float slopeBound, int steps)` - slope-bounded march then regula-falsi refinement against sceneHeight; returns hit t or -1.
- `vec3 heightfieldNormal(vec2 xz, float eps, int lod)` - normal of sceneHeight by central differences at the given level of detail.
- `float pixelFootprint(float t, float fovY, float resY)` - world size of one pixel at distance t, for epsilon and LOD choice.

### water-shade

- `float fresnelSchlick(float cosTheta, float f0)` - reflectance; water f0 is about 0.02.
- `vec3 beerLambert(vec3 sigma, float distance)` - per-channel transmittance through water.
- `float glitterExponent(float baseExponent, float distance, float falloff)` - specular exponent widening with distance to mimic sub-pixel waves.

### pattern (reaction-diffusion and cellular automata)

- `vec2 grayScott(vec2 ab, vec2 lapAB, float feed, float kill, vec2 diffusion, float dt)` - one explicit Gray-Scott step for chemicals (A, B).
- `int countNeighbours8(sampler2D s, ivec2 p, ivec2 size, float threshold)` - live neighbours with exact texel reads.
- `float lifeRule(float alive, int n, int birthMask, int surviveMask)` - generic Life-like rule; B3/S23 is birth 1<<3, survive (1<<2)|(1<<3).
- `float leniaGrowth(float u, float mu, float sigma)` - bell-shaped growth mapping onto [-1, 1].
- `float leniaShell(float r)` - smooth ring kernel profile on 0..1, zero at both ends.

### particle

- `ivec2 particleTexel(int id, int width)` - texel that stores particle id.
- `int particleId(ivec2 p, int width)` - inverse of particleTexel.
- `void stepSymplectic(inout vec3 x, inout vec3 v, vec3 a, float dt)` - velocity first, then position.
- `void stepVerlet(inout vec3 x, inout vec3 xPrev, vec3 a, float dt)` - position Verlet, velocity implicit.
- `vec3 bounce(vec3 v, vec3 n, float restitution, float friction)` - split normal and tangent velocity, reflect and damp.
- `vec3 relaxToFlow(vec3 v, vec3 vFlow, float rate, float dt)` - Stokes-style drag toward a flow field.
- `vec3 clampLength(vec3 v, float maxLen)` - speed or acceleration limiter.

### temporal (feedback, accumulation, TAA)

- `vec4 accumulateProgressive(vec4 history, vec3 sample, bool reset)` - cumulative mean with the sample count in alpha.
- `vec4 accumulateCapped(vec4 history, vec3 sample, float maxCount)` - cumulative mean that becomes an EMA after maxCount samples.
- `float emaAlpha(float dt, float tauSec)` - frame-rate independent blend weight.
- `vec2 feedbackWarp(vec2 uv, vec2 centre, float zoomPerSec, float rotPerSec, vec2 driftPerSec, float dt)` - MilkDrop-style per-step warp of where to read the previous frame.
- `vec2 halton23(int index)` - point of the Halton(2,3) sequence in [0,1)^2.
- `vec2 taaJitter(int frame, int cycle)` - sub-pixel offset in [-0.5, 0.5) pixels for this frame.
- `vec3 toYCoCg(vec3 rgb)` - luma/chroma transform for colour boxes.
- `vec3 fromYCoCg(vec3 ycocg)` - inverse transform.
- `void neighbourhoodStats(sampler2D cur, ivec2 p, ivec2 size, out vec3 mean, out vec3 sd, out vec3 lo, out vec3 hi)` - 3x3 moments and rounded min/max in YCoCg.
- `vec3 clipToBox(vec3 history, vec3 lo, vec3 hi)` - move history toward the box centre until it lies inside.
- `vec4 sampleCatmullRom(sampler2D s, vec2 uv, vec2 size)` - sharp bicubic history fetch from 9 bilinear taps.
- `vec3 lumaWeigh(vec3 c)` - reversible c/(1+luma) map before averaging.
- `vec3 lumaUnweigh(vec3 c)` - inverse c/(1-luma) after averaging.
- `vec2 reprojectUV(vec3 worldPos, mat4 prevViewProj)` - where this surface point was on screen last frame.
- `float historyTrust(float speedPix, float fullBelow, float noneAbove)` - 1 below fullBelow pixels/frame, 0 above noneAbove.
- `vec3 fireflyClamp(vec3 c, float maxLuma)` - scale down samples brighter than maxLuma.

---

## 13. Corpus map for this topic

All in `state/arsenal/shaders/corpus/shaders/`. Licence from each `meta.json`; NC means CC BY-NC-SA, study only.

| technique | shader | author | licence | where to look |
|---|---|---|---|---|
| ridged-chop sea, regula-falsi heightfield march, distance LOD | `Ms2SD1` Seascape | Alexander Alekseev (TDM) | NC | `image.glsl:66-106`, `135-158`, `175` |
| exp-sine waves with drag, slab-bounded march | `MdXyzX` Very fast procedural ocean | afl_ext | MIT | `image.glsl:16-75`, `181-199` |
| state texels, resolution-change detection, periodic heightmap buffer | `NdS3zK` OCEAN ELEMENTAL | alro | MIT | `buffer_a.glsl:1-60`, `buffer_b.glsl` |
| single-pass curl-rotation fluid, 9-point Laplacian, safe normalise | `XddSRX` Suture Fluid | cornusammonis | MIT | `buf_a.glsl:42-44`, `79-170` |
| multiscale fluid through mipmaps | `tsKXR3` Multiscale MIP Fluid | cornusammonis | NC | `common.glsl:13-99`, `buffer_a.glsl:191` |
| RK4 backtrace, baked 20-iteration pressure kernel | `MdSczK` Multistep Fluid Simulation | Robert Schuetze (trirop) | NC | `buf_a.glsl:7-14`, `buf_b.glsl`, `buf_c.glsl` |
| four-population lattice Boltzmann, advected coordinates | `WdyGzy` Lattice Boltzmann | wyatt | NC | `buffer_a.glsl:7-50`, `buffer_b.glsl` |
| reintegration tracking with SPH pressure | `WtfyDj` Paint streams | Mykhailo Moroz (michael0884) | NC | `common.glsl:26-31`, `136-192` |
| difference-of-Gaussians reaction-diffusion, separable blur | `4dcGW2` expansive reaction-diffusion | Flexi | NC | `buf_a.glsl:108-119`, `buf_b.glsl` |
| particles in a texture row, O(N^2) forces | `ldd3DB` Interactive Shoal of fish | Sebastien Durand (iapafoto) | NC | `buffer_a.glsl:13-45`, `image.glsl:21-23` |
| path-traced GI with reprojection and capped sample count | `Wt3XRX` Path traced GI | loicvdb | NC | `buffer_c.glsl:58-117` |
| variance-clipped TAA in YCoCg | `4dSBDt` Enscape Cube | ThomasSchander | NC | `buffer_c.glsl:28-53` |
| stored camera, reprojection, mouse/resize rejection | `MdGfzh` Himalayas | Reinder Nijhoff | NC (4.0) | `common.glsl:56-82`, `buffer_c.glsl:156-170` |
| reprojection original | `4ttSWf` Rainforest | Inigo Quilez | all rights reserved (read only) | `buffer_a.glsl:916+` |
| temporal accumulation plus bilateral denoise | `dsGBzW` Screen Space Horizon GI | Mathis | NC | `image.glsl:14`, `buffer_a.glsl:147-154` |
| Shadertoy uniforms, keyboard, state tricks | `llySRh` iResolution, iMouse, iDate, etc | Fabrice Neyret | NC | `image.glsl` |
| fluid-like motion without a solver | `4sGSDw` Sinuous, `MdG3Dd`, `MtKSWW`, `4tGfDW` | nimitz | NC | buffers A-D |
| tileable caustic by iterated warping | `MdlXz8` Tileable Water Caustic | Dave Hoskins (after joltz0r) | NC | `image.glsl` |
| other fluid studies | `Xst3Dj` Viscous Fingering, `WlVyRV` Dry ice 2, `MsGSRd` spilled, `WdVXWy` molten bismuth, `MlVfDR` Fluid Mosaic, `fljBWc` Liquid Toy, `MdGBWG` Global Wind Circulation (CC BY-SA) | various | mostly NC | buffers |

The house's own instance: Moonwater's ripple field, `arsenal/web/piano/spectacle-worlds.js:9-48` (Apache-2.0, ours).

---

## 14. Sources

Primary sources first, then tutorials and production talks.

- https://jtessen.people.clemson.edu/reports/papers_files/coursenotes2004.pdf - Jerry Tessendorf, "Simulating Ocean Water" (SIGGRAPH course notes 2001, rev. 2004): Gerstner waves, dispersion, the FFT ocean, Phillips spectrum, choppy displacement, Jacobian folding and eigenvalues, looping by quantised frequencies, iWave, ocean optics.
- https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models - Mark Finch (GPU Gems 1, ch. 1): sum of sines, sharpened sines, Gerstner with steepness Q, analytic normals, wave selection, edge-length filtering.
- https://catlikecoding.com/unity/tutorials/flow/waves/ - Jasper Flick: derivation of Gerstner waves from circular orbits, steepness, tangent frames, summing waves.
- https://dl.acm.org/doi/10.1145/2791261.2791267 - Christopher Horvath (DigiPro 2015), "Empirical directional wave spectra for computer graphics": JONSWAP/TMA spectra, directional spreading, the swell parameter.
- https://github.com/gasgiant/FFT-Ocean/blob/main/references.md - Ivan Pensionerov's reference list for a GPU FFT ocean (links to Flugge, Tcheblokov, Gamper).
- https://tore.tuhh.de/bitstream/11420/1439/1/GPGPU_FFT_Ocean_Simulation.pdf - Fynn-Jorin Flugge (2017), realtime GPGPU FFT ocean: the butterfly-pass pipeline on the GPU.
- https://iquilezles.org/articles/terrainmarching/ - Inigo Quilez, raymarching height-field terrains: stepping, interpolation, distance-scaled steps.
- https://www.dgp.toronto.edu/public_user/stam/reality/Research/pub.html - Jos Stam's publications: "Stable Fluids" (SIGGRAPH 1999) and "Real-Time Fluid Dynamics for Games" (GDC 2003): semi-Lagrangian advection, implicit diffusion, projection.
- https://pdfs.semanticscholar.org/5127/ac7b58e36ffd13ca4437fc123c6a018dc436.pdf - Stam's GDC 2003 slides: why explicit diffusion is unstable, Gauss-Seidel solve, density and velocity solvers.
- https://developer.nvidia.com/gpugems/gpugems/part-vi-beyond-triangles/chapter-38-fast-fluid-dynamics-simulation-gpu - Mark Harris (GPU Gems 1, ch. 38): stable fluids in textures, Jacobi formulas, boundaries, vorticity confinement, buoyancy.
- https://www.dgp.toronto.edu/public_user/stam/reality/Research/pdf/smoke.pdf - Fedkiw, Stam and Jensen (SIGGRAPH 2001), "Visual Simulation of Smoke": vorticity confinement.
- https://faculty.cc.gatech.edu/~jarek/papers/maccormack.pdf - Selle, Fedkiw, Kim, Liu and Rossignac (2008): the unconditionally stable MacCormack advection with limiter.
- https://www.cs.ubc.ca/~rbridson/fluidsimulation/ - Robert Bridson's fluid simulation notes and book: the complete grid-fluid foundation (staggered grids, pressure, boundaries).
- https://www.cs.ubc.ca/~rbridson/docs/bridson-siggraph2007-curlnoise.pdf - Bridson, Hourihan and Nordenstam (2007), "Curl-Noise for Procedural Fluid Flow": divergence-free velocity from a noise potential.
- https://github.com/PavelDoGreat/WebGL-Fluid-Simulation - Pavel Dobryakov (MIT): a production-quality WebGL fluid; pass order, half-float targets, dissipation, pressure warm start, defaults.
- https://michaelmoroz.github.io/Reintegration-Tracking/ - Mykhailo Moroz: reintegration tracking, mass-conserving particle-in-cell advection with SPH forces.
- https://michaelmoroz.github.io/TODO/2021-3-13-Overview-of-Shadertoy-particle-algorithms/ - Moroz: survey of particle algorithms possible in Shadertoy's gather-only model.
- https://www.gamedeveloper.com/programming/building-a-million-particle-system - Lutz Latta (GDC 2004): stateless versus stateful GPU particles, integrators, collision response, GPU sorting.
- https://www.karlsims.com/rd.html - Karl Sims: Gray-Scott explained plainly, working parameters, the 3x3 Laplacian weights.
- http://www.mrob.com/pub/comp/xmorphia/index.html - Robert Munafo's xmorphia: Gray-Scott equations and the (F, k) parameter map.
- http://www.mrob.com/pub/comp/xmorphia/pearson-classes.html - Munafo's extended Pearson classification with representative parameters.
- https://www.science.org/doi/10.1126/science.261.5118.189 - John Pearson (Science 1993), "Complex Patterns in a Simple System": the original Gray-Scott pattern survey.
- https://arxiv.org/pdf/1111.1567 - Stephan Rafler (2011), SmoothLife: Conway's Life generalised to continuous space.
- https://en.wikipedia.org/wiki/Lenia - overview of Bert Wang-Chak Chan's Lenia (Complex Systems, 2019): update rule, kernel shells, growth function.
- https://web.archive.org/web/20160418004149/http://freespace.virgin.net/hugo.elias/graphics/x_water.htm - Hugo Elias, the classic two-buffer 2D water ripple algorithm.
- https://medium.com/@evanwallace/rendering-realtime-caustics-in-webgl-2a99a29a0b2c - Evan Wallace: caustics from the area ratio of refracted surface patches, in his WebGL Water demo.
- https://www.geisswerks.com/milkdrop/milkdrop_preset_authoring.html - Ryan Geiss: MilkDrop's feedback model (warp mesh, decay, warp and composite shaders, blur textures).
- https://advances.realtimerendering.com/s2014/ - SIGGRAPH 2014 Advances course page: Brian Karis, "High Quality Temporal Supersampling" (slides and video).
- https://de45xmedrsdbp.cloudfront.net/Resources/files/TemporalAA_small-59732822.pdf - Karis's TAA slides (PDF): Halton jitter, EMA, luminance weighting, Gaussian reconstruction, velocity dilation, shaped YCoCg clip, anti-flicker.
- https://s3.amazonaws.com/arena-attachments/655504/c5c71c5507f0f8bf344252958254fb7d.pdf - Lasse Jon Fuglsang Pedersen (GDC 2016), "Temporal Reprojection Anti-Aliasing in INSIDE": a complete worked TAA, clip toward centre, motion-blur fallback, sample-sequence experiments.
- https://www.elopezr.com/temporal-aa-and-the-quest-for-the-holy-trail/ - Emilio Lopez (2022): the most complete practical TAA guide (jitter, history filters, rejection methods, flicker, camera cuts).
- https://onlinelibrary.wiley.com/doi/10.1111/cgf.14018 - Yang, Liu and Salvi (Computer Graphics Forum 2020), "A Survey of Temporal Antialiasing Techniques".
- https://blog.demofox.org/2020/05/25/casual-shadertoy-path-tracing-1-basic-camera-diffuse-emissive/ - Alan Wolfe: progressive accumulation in a Shadertoy buffer, seeding, cosine sampling.
- https://blog.demofox.org/2020/06/06/casual-shadertoy-path-tracing-2-image-improvement-and-glossy-reflections/ - Wolfe: sample count in alpha, keyboard reset.
- https://shadertoyunofficial.wordpress.com/2016/07/20/special-shadertoy-features/ - Fabrice Neyret: buffer precision, pass order, initialisation, resize, mouse and keyboard encodings.
- https://inspirnathan.com/posts/62-shadertoy-tutorial-part-15/ - Nathan Vaughn: a gentle introduction to Shadertoy channels, textures and buffers.
