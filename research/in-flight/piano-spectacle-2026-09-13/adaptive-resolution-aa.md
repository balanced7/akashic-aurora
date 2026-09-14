# Piano: adaptive resolution and anti-aliasing, prototyped and measured

2026-09-13 · lab build `arsenal/web/piano-lab-res.js` (+ `piano-lab-res.html`) · base commit `a886a0af` · three r186 ·
measured in headless Chrome (`--headless=new`) on ANGLE D3D11, AMD Radeon RX 9070 XT.

Daniel, tonight: "Can you reload the piano page and make it be perfectly un-aliased" and "Lets make the resolution be
adaptive to the render window". Recordings stay 1080x1920 (or 1920x1080) at 60 fps.

## 1. Answer first

**Recommendation: an adaptive drawing buffer + 2x supersampling (exact box filter, in linear light, after tone mapping) + MSAA 4,
with bloom pinned to the framing size; REC switches the buffer to exactly the framing size, renders it at 2x, and draws only the
60 frames a second the file keeps.** Live scene cap 5 MP, REC cap 8.3 MP; over a cap the factor drops to the largest whole number.

Why, in three numbers (all four window cases agree; tables in section 4):

1. **The biggest single fix is not an AA method, it is not letting the browser resample the canvas.** HEAD's fixed 1080x1920
   buffer, as the compositor actually shows it, has **2.9x to 3.4x the edge error** of the same MSAA 4 rendered at the canvas's
   real device-pixel size (edge MAE .0284 vs .0098 at 1280x900; .0259 vs .0076 at 2560x1440; .0246 vs .0074 at DPR 1.5;
   .0318 vs .0105 in 16:9). A screenshot of the adaptive canvas equals the drawing buffer read back directly, **MAE 0.000000**,
   in every case, including DPR 1.5 and fractional CSS positions, so the browser shows it 1:1.
2. **2x supersampling + MSAA 4 halves what is left.** Against a 16-samples-a-pixel reference it had the lowest edge error in
   all four cases (.0087 / .0070 / .0070 / .0087 vs MSAA 4's .0175 / .0148 / .0143 / .0164) and roughly 45% less edge shimmer
   under a slow camera pan (.0061 / .0053 / .0053 / .0047 vs .0108 / .0096 / .0096 / .0094).
3. **It is affordable.** 2.2-2.4 ms a frame at the 9:16 live sizes tested; 5.3 ms (p95 5.8) at 1080x1920 for recording.
   MSAA 8, SMAA, FXAA, three's "TAA" addon, a tent filter and 1.5x all lost to it (section 5 says why).

"Perfectly un-aliased" is not literally reached: edge error vs the 16-sample reference is .007, not 0, and the clearcoat
specular on key bevels still sparkles faintly (open issue 6). It is the cleanest option that holds 240 Hz live at 9:16 and 60 fps
in recordings on this GPU.

The look is otherwise unchanged: the wash check matches HEAD's `final-4` receipt shot by shot to 3-4 decimals, and the sustain
check reproduces HEAD's key glow (.943 / 1.167 / .750 / .518 / .592 / 1.065 vs .946 / 1.167 / .742 / .517 / .593 / 1.068) once the
test's timing artefact is removed (section 7).

Deliverables:

- `research/in-flight/piano-spectacle-2026-09-13/adaptive-resolution-aa.patch`: `git diff` of `piano.js` at `a886a0af` against
  the lab file, paths rewritten to `arsenal/web/piano.js` (422 lines added, 26 removed). Verified: applied to a clean copy of the
  base it reproduces the lab file exactly (ignoring CRLF, which `core.autocrlf=true` adds). It does **not** apply to the current
  working copy, which the other build is editing (imports and overlay text code); see section 8.
- `research/in-flight/piano-spectacle-2026-09-13/aa-crops/`: 4x/3x nearest-neighbour crop sheets for every case.
- `research/in-flight/piano-spectacle-2026-09-13/adaptive-resolution-data/`: every bench JSON, recording analyses, the
  generated tables, and the scripts (`scripts/aa_bench.mjs`, `rec_probe.mjs`, `analyze_rec.py`, `crops.py`, `tables.py`,
  `cdp.mjs`, `smoke.mjs`).
- Receipts: `state/arsenal/receipts/piano-wash/lab-res-2x/`, `state/arsenal/receipts/piano-sustain/lab-res-2x`,
  `lab-res-2x-solo`, `lab-res-rec1-solo`, `lab-res-fixed1-solo`.

## 2. What was wrong with HEAD's resolution

- `renderer.setPixelRatio(1)` and a composer target fixed at 1080x1920 (or 1920x1080) whatever the window; `fitCanvas()` then
  set the canvas's CSS size, so the compositor scaled the picture to fit: 1080x1920 shown at 378x672 (2.86x down), 711x1264
  (1.52x down), 693x1232 device pixels at DPR 1.5 (1.56x down), or 1920x1080 stretched to 2240x1260 (1.17x up). Canvas layers
  are scaled with a plain bilinear filter and no mipmaps, so a downscale aliases thin, high-contrast detail (key gaps, the rail
  line, staff lines, text stems) and an upscale blurs it. The crops show both.
- The overlay (chord name, note chips, staff) is a 2D canvas at framing resolution, so it went through the same resample.
- Bloom kernels are sized in texels, so simply resizing the pipeline would have changed the glow's shape with the window.

## 3. Design (what the lab build does)

All in `arsenal/web/piano-lab-res.js`; section `resolution` right after the camera.

**Adaptive buffer.**
- `fitCanvas()` sizes the canvas's CSS box to whole device pixels in the framing's exact aspect (`9n x 16n` device pixels for
  9:16, via gcd), so the buffer never needs a non-uniform scale.
- A `ResizeObserver` on the canvas with `{ box: "device-pixel-content-box" }` reads the device-pixel box the browser actually laid
  out and sets `RES.display`; `applyResolution()` sizes everything from it. The observer runs after layout and before paint,
  and the handler renders a frame at once, so a resize never shows a cleared canvas.
- If `devicePixelContentBoxSize` and CSS size x DPR disagree by more than 2 px, the handler uses CSS size x DPR. Under a real
  device scale factor they agree (the first carries the browser's pixel snapping and is preferred); under DevTools device
  emulation the first reports CSS pixels.
- DPR changes (another monitor, browser zoom): a `matchMedia("(resolution: Xdppx)")` listener re-snaps the CSS box and re-arms
  itself; the observer then fires with the new device-pixel size. A stage `ResizeObserver` still drives `fitCanvas()`.
- `applyFraming()` resets `RES.display`, so the new framing renders at framing size until the observer measures the new box
  (before that frame paints).
- `RES.maxOutput` = 3840x2160: past it the buffer is capped and the browser upsamples.

**Scene resolution and the downsample.**
- The composer renders at `output x RES.scale` (default 2; `?scale=`, `localStorage arsenal.piano.renderScale`) with MSAA
  `RES.msaa` (default 4; `?msaa=`).
- `OutputPass` tone maps at scene resolution. When scene and output differ, `DownsamplePass` runs a separable filter with
  exact footprint weights (`texelFetch`, a CDF per texel, so any ratio is an exact area average), decoding sRGB to linear first
  and encoding at the end. Filter 0 is box (default), 1 is tent with a 1-output-pixel radius (`?filter=tent`).
- When scale is 1 the pass is disabled and `OutputPass` renders to the screen exactly as in HEAD.
- Pixel caps: live `RES.maxInternal` = 5 MP, REC `RES.maxInternalRec` = 8.3 MP. If the wanted factor does not fit, it drops to
  the largest whole factor that does (`floor`), and below 1x only when 1x itself is over the cap. The reason: 1.5x measured no
  better than MSAA 4 alone (section 5).

**Bloom pinned to the framing size.**
- `FramingBloomPass` wraps the stock `UnrealBloomPass`: `setSize()` always sizes the bloom to `framing.w x framing.h`.
- The scene is area-averaged (`boxDownMaterial`, exact footprint weights) into a half-framing-size HDR target that becomes the
  bloom's input. At a 1080x1920 scene that is exactly the 2x2 average the stock high-pass took with its own bilinear tap.
- The stock pass blurs and composites; its final blend lands on the small target. Its composite is then added over the
  full-resolution scene with the stock `blendMaterial`.
- Result: the glow has one shape at every window size and in recordings, and costs what it cost in HEAD.

**Pixel-sized things.**
- `sparkUniforms.uPx` comes from the scene target's height (point sprites are sized in scene pixels). The max point size is
  1024 here, never reached.
- The camera's lens-shift view offset is expressed in scene pixels (`setViewOffset(W, H, 0, -shift*H, W, H)`), so a jittering
  pass adds sub-pixel offsets in real pixels.
- Trail columns and halos are analytic in world units, so they keep their look at any resolution.

**Overlay at output resolution, pixel-snapped.**
- `makeLayer()` gives each layer one canvas texel per output pixel and snaps its quad to whole output pixels; the quad stays laid
  out in framing units.
- `drawLabel`/`drawStaff` start with `ctx.setTransform(sx, 0, 0, sy, 0, 0)`.
- Canvas `shadowBlur` ignores the transform, so both glow blurs are multiplied by `shadowScale`.
- At the framing size `sx = sy = 1`, so a recording's overlay is byte-for-byte HEAD's drawing.
- The overlay draws after the downsample, at output resolution.

**Recording.**
- `startRecording()` calls `setRecordResolution(true)` before `canvas.captureStream(0)`. The buffer becomes exactly the
  framing size, the scene renders at `RES.recScale` (default 2; `?recscale=`), and the track is created at 1080x1920.
- `finishRecording()` (and the failure path) switch back.
- While REC runs, `loop()` draws only when the 60 fps accumulator says a frame is due, so the GPU does not render 240 frames a
  second at 2160x3840 that the file throws away.
- **The live view during REC** shows exactly the recorded frames, at 60 fps, scaled by the browser into the same CSS box, which
  is what HEAD always showed, and returns to the adaptive buffer on stop.
- `snapshot()` now returns what a recording would contain: the framing size at the REC scale. `{ native: true }` returns the
  live buffer, `{ png: true }` a PNG.

**HUD.** The render row reads e.g. `711x1264 (9:16) · scene 1422x2528 MSAA 4 · three r186`, with `, REC` while recording.

**Lab-only additions** (keep for tests or strip at merge; about 150 lines):
- `LAB` flags; `clockOverride`.
- `window.__piano.lab.{res, set, freeze, unfreeze, seed, sim, grab, bench, record}`.
- `setLabAA()`, which dynamically imports `TAARenderPass`, `SMAAPass` and `FXAAPass` (the app never loads them).
- `?fixed=1` (HEAD behaviour: framing-size buffer scaled by the browser).
- A `rec.probe` path in `finishRecording()` that returns the file instead of uploading it. The lab never POSTed anything to
  the server.

## 4. Method

**One frozen, deterministic frame.**
- `lab.seed(20260913)` replaces `Math.random`, so the sparks come out identical.
- `lab.sim(events, 6.65)` plays a fixed phrase on a scripted 60 fps clock starting at t = 1000 s, without drawing:
  - two pedalled bars (F/A then C/G, arpeggio, melody, pedal changed on the bar);
  - then a spread F chord (41 53 57 60 65 69 72 77, v110) at 6.2 s with the pedal re-caught.
- It freezes 0.45 s after the chord: 8 notes sounding, 28-30 live trails, sparks in flight, label "F".
- Every configuration renders this identical state in the same page.

**Reference.**
- The same frame at 4x per axis: 16 ordered-grid samples a pixel, no MSAA, tone mapped at 4x.
- Exact 4x4 area average in linear light, done by the lab's own `DownsamplePass`, to the canvas's native size: 1512x2688,
  2844x5056, 2772x4928, 8960x5040.
- The overlay is hidden in the pipeline comparison because it is drawn at output resolution after the downsample, identically
  in every config.

**Metrics.** Computed in the page on `gl.readPixels` of the drawing buffer.
- MAE: mean absolute RGB difference in sRGB code values / 255.
- Edge MAE: the same over pixels where the reference's Sobel luma gradient exceeds 0.25, dilated 1 px (4-9% of the frame).
- PSNR.

**Shimmer.**
- The camera (look target and position together) pans 12 frames at 0.37 output pixels per frame at the key line (world step
  = 0.37 / (canvas width / camera span)), with the scene clock frozen.
- Each frame is compared to its own per-frame reference. Shimmer = mean over pixels and frame pairs of |e(f) - e(f-1)|, where e
  is the signed error against the reference.
- It counts only flicker the ideal image does not have. Edge shimmer uses the union of the two frames' edge masks.
- For scale, the reference itself changes by .0027 / .0016 / .0016 / .0011 between pan frames.

**Display path (what the eye gets).**
- `Page.captureScreenshot` of the viewport, cropped at the canvas's device-pixel rectangle, overlay on.
- Alignment was searched over +-2 device pixels on the adaptive buffer; best offset (0,0), MAE 0 in all four cases.
- Compared to a 4x reference with the overlay drawn at native size.
- Configs: HEAD's fixed buffer (`fixed: true, recScale 1, MSAA 4`), adaptive MSAA 4, adaptive 2x box, adaptive 1.5x+MSAA 4.

**Frame cost.**
- `lab.bench(n)`: `renderFrame()` plus a 1-pixel `readPixels` to synchronise with the GPU.
- Native sizes: 10 warm-up frames, then median/p95 of 40.
- Recording size (`rec_probe.mjs`): three runs of 60; median of the medians, worst p95.
- The headless GPU is Daniel's GPU while he uses the desktop, so treat costs as relative. Headless `requestAnimationFrame` ran
  at 240 Hz.

**Configurations.**
- none (MSAA 0); MSAA 4 (HEAD's AA); MSAA 8 (`MAX_SAMPLES` is 8).
- FXAA and SMAA from three/addons, inserted after `OutputPass` as they require display-encoded input; SMAA + MSAA 4.
- "TAA x4 / x8": `TAARenderPass` with `accumulate = false`, which three implements as `SSAARenderPass`: 2^level jittered scene
  renders a frame, averaged in HDR. three's WebGL TAA addon has no reprojection ("no TRAA implementation" in its own header),
  its accumulate mode only converges on a still scene and calls `clearViewOffset()` (which would drop our lens shift). This
  scene never holds still (camera drift, rising trails, sparks), so non-accumulating is the only usable mode.
- SS 1.5x and 2x with box or tent; SS 1.5x and 2x box + MSAA 4.

**Window cases.**

| case | window | DPR | framing | canvas buffer | note |
|---|---|---|---|---|---|
| A | 1280x900 | 1 | 9:16 | 378x672 | the topbar wraps to several rows at this width |
| B | 2560x1440 | 1 | 9:16 | 711x1264 | CSS x = 913.5 (fractional) |
| C | 1600x1000 | 1.5 (`--force-device-scale-factor`) | 9:16 | 693x1232 | CSS box 462 x 821.333 |
| D | 2560x1440 | 1 | 16:9 | 2240x1260 | |

## 5. Results

The tables are generated from `adaptive-resolution-data/aa-bench-*.json` by `scripts/tables.py`. **(best)** marks the lowest edge MAE.

### A: window 1280x900, DPR 1, 9:16, buffer 378x672, reference scene 1512x2688

| config | scene px | MSAA | MAE | edge MAE | PSNR dB | shimmer | edge shimmer | ms median | ms p95 |
|---|---|---|---|---|---|---|---|---|---|
| none | 378x672 | 0 | 0.00305 | 0.02531 | 34.15 | 0.00228 | 0.01944 | 0.9 | 1.5 |
| msaa4 | 378x672 | 4 | 0.00266 | 0.01750 | 38.83 | 0.00146 | 0.01081 | 0.9 | 1.4 |
| msaa8 | 378x672 | 8 | 0.00275 | 0.01819 | 38.60 | 0.00146 | 0.01084 | 1 | 1.2 |
| fxaa | 378x672 | 0 | 0.00321 | 0.02718 | 34.73 | 0.00209 | 0.01752 | 0.9 | 1.4 |
| smaa | 378x672 | 0 | 0.00276 | 0.02219 | 35.84 | 0.00192 | 0.01560 | 0.8 | 1.3 |
| smaa+msaa4 | 378x672 | 4 | 0.00300 | 0.02131 | 36.76 | 0.00191 | 0.01555 | 0.9 | 1.4 |
| taa-x4 | 378x672 | 0 | 0.00283 | 0.01666 | 38.92 | 0.00118 | 0.00916 | 1.4 | 1.8 |
| taa-x8 | 378x672 | 0 | 0.00309 | 0.01789 | 38.48 | 0.00113 | 0.00854 | 2.3 | 2.9 |
| ss1.5-box | 567x1008 | 0 | 0.00192 | 0.01578 | 38.29 | 0.00152 | 0.01243 | 0.9 | 1.2 |
| ss1.5-tent | 567x1008 | 0 | 0.00221 | 0.01889 | 37.73 | 0.00155 | 0.01270 | 0.9 | 1.3 |
| ss1.5-box+msaa4 | 567x1008 | 4 | 0.00182 | 0.01412 | 39.73 | 0.00125 | 0.00961 | 1 | 1.3 |
| ss2-box | 756x1344 | 0 | 0.00130 | 0.01045 | 40.55 | 0.00102 | 0.00859 | 0.9 | 1.1 |
| ss2-tent | 756x1344 | 0 | 0.00191 | 0.01614 | 38.90 | 0.00131 | 0.01087 | 0.9 | 1.2 |
| ss2-box+msaa4 **(best)** | 756x1344 | 4 | 0.00119 | 0.00872 | 43.37 | 0.00079 | 0.00612 | 1.3 | 1.9 |

Display path (overlay on; screenshot vs buffer MAE 0):

| as displayed | buffer | scene px | MAE | edge MAE | PSNR dB | shimmer | edge shimmer |
|---|---|---|---|---|---|---|---|
| HEAD fixed 1080x1920 MSAA 4 | 1080x1920 | 1080x1920 | 0.00510 | 0.02843 | 30.26 | 0.00146 | 0.00712 |
| adaptive MSAA 4 | 378x672 | 378x672 | 0.00263 | 0.00978 | 38.84 | 0.00143 | 0.00618 |
| adaptive 2x box | 378x672 | 756x1344 | 0.00130 | 0.00582 | 40.55 | 0.00101 | 0.00487 |
| adaptive 1.5x box + MSAA 4 | 378x672 | 567x1008 | 0.00180 | 0.00788 | 39.74 | 0.00123 | 0.00551 |

### B: window 2560x1440, DPR 1, 9:16, buffer 711x1264, reference scene 2844x5056

| config | scene px | MSAA | MAE | edge MAE | PSNR dB | shimmer | edge shimmer | ms median | ms p95 |
|---|---|---|---|---|---|---|---|---|---|
| none | 711x1264 | 0 | 0.00174 | 0.02314 | 37.23 | 0.00125 | 0.01835 | 0.9 | 1.2 |
| msaa4 | 711x1264 | 4 | 0.00141 | 0.01484 | 42.29 | 0.00079 | 0.00956 | 1 | 1.3 |
| msaa8 | 711x1264 | 8 | 0.00144 | 0.01554 | 42.00 | 0.00079 | 0.00965 | 1 | 1.6 |
| fxaa | 711x1264 | 0 | 0.00182 | 0.02492 | 38.17 | 0.00110 | 0.01540 | 0.9 | 1.2 |
| smaa | 711x1264 | 0 | 0.00155 | 0.01939 | 39.62 | 0.00101 | 0.01360 | 0.9 | 1.3 |
| smaa+msaa4 | 711x1264 | 4 | 0.00161 | 0.01891 | 39.86 | 0.00103 | 0.01425 | 1.1 | 1.7 |
| taa-x4 | 711x1264 | 0 | 0.00143 | 0.01338 | 42.54 | 0.00070 | 0.00829 | 1.6 | 2.2 |
| taa-x8 | 711x1264 | 0 | 0.00160 | 0.01442 | 42.03 | 0.00068 | 0.00771 | 2.5 | 3.2 |
| ss1.5-box | 1067x1896 | 0 | 0.00125 | 0.01573 | 41.06 | 0.00091 | 0.01227 | 1 | 1.4 |
| ss1.5-tent | 1067x1896 | 0 | 0.00145 | 0.01952 | 40.33 | 0.00092 | 0.01239 | 1 | 1.4 |
| ss1.5-box+msaa4 | 1067x1896 | 4 | 0.00123 | 0.01449 | 42.23 | 0.00080 | 0.01008 | 1.6 | 2 |
| ss2-box | 1422x2528 | 0 | 0.00072 | 0.00913 | 43.45 | 0.00056 | 0.00764 | 1.1 | 1.8 |
| ss2-tent | 1422x2528 | 0 | 0.00109 | 0.01566 | 41.67 | 0.00073 | 0.01025 | 1.2 | 1.8 |
| ss2-box+msaa4 **(best)** | 1422x2528 | 4 | 0.00065 | 0.00702 | 46.84 | 0.00044 | 0.00527 | 2.4 | 3.1 |

| as displayed | buffer | scene px | MAE | edge MAE | PSNR dB | shimmer | edge shimmer |
|---|---|---|---|---|---|---|---|
| HEAD fixed 1080x1920 MSAA 4 | 1080x1920 | 1080x1920 | 0.00310 | 0.02590 | 34.01 | 0.00075 | 0.00498 |
| adaptive MSAA 4 | 711x1264 | 711x1264 | 0.00140 | 0.00762 | 42.29 | 0.00078 | 0.00504 |
| adaptive 2x box | 711x1264 | 1422x2528 | 0.00072 | 0.00468 | 43.45 | 0.00055 | 0.00400 |
| adaptive 1.5x box + MSAA 4 | 711x1264 | 1067x1896 | 0.00122 | 0.00747 | 42.24 | 0.00079 | 0.00534 |

### C: window 1600x1000, DPR 1.5, 9:16, buffer 693x1232, reference scene 2772x4928

| config | scene px | MSAA | MAE | edge MAE | PSNR dB | shimmer | edge shimmer | ms median | ms p95 |
|---|---|---|---|---|---|---|---|---|---|
| none | 693x1232 | 0 | 0.00173 | 0.02264 | 37.13 | 0.00129 | 0.01839 | 0.8 | 1.1 |
| msaa4 | 693x1232 | 4 | 0.00137 | 0.01434 | 42.36 | 0.00081 | 0.00960 | 1 | 1.5 |
| msaa8 | 693x1232 | 8 | 0.00140 | 0.01489 | 42.15 | 0.00082 | 0.00972 | 1.1 | 1.5 |
| fxaa | 693x1232 | 0 | 0.00185 | 0.02497 | 37.95 | 0.00113 | 0.01545 | 0.9 | 1.3 |
| smaa | 693x1232 | 0 | 0.00155 | 0.01914 | 39.51 | 0.00103 | 0.01360 | 0.9 | 1.7 |
| smaa+msaa4 | 693x1232 | 4 | 0.00158 | 0.01838 | 39.93 | 0.00107 | 0.01441 | 1.1 | 1.8 |
| taa-x4 | 693x1232 | 0 | 0.00138 | 0.01300 | 42.53 | 0.00072 | 0.00841 | 1.6 | 2.2 |
| taa-x8 | 693x1232 | 0 | 0.00154 | 0.01394 | 42.11 | 0.00071 | 0.00779 | 2.6 | 3.2 |
| ss1.5-box | 1040x1848 | 0 | 0.00128 | 0.01571 | 41.04 | 0.00095 | 0.01235 | 1 | 1.7 |
| ss1.5-tent | 1040x1848 | 0 | 0.00148 | 0.01948 | 40.26 | 0.00097 | 0.01247 | 1 | 1.5 |
| ss1.5-box+msaa4 | 1040x1848 | 4 | 0.00128 | 0.01504 | 41.82 | 0.00085 | 0.01032 | 1.4 | 2.1 |
| ss2-box | 1386x2464 | 0 | 0.00073 | 0.00891 | 43.66 | 0.00057 | 0.00764 | 1.1 | 1.5 |
| ss2-tent | 1386x2464 | 0 | 0.00114 | 0.01600 | 41.39 | 0.00076 | 0.01028 | 1.1 | 1.3 |
| ss2-box+msaa4 **(best)** | 1386x2464 | 4 | 0.00065 | 0.00697 | 46.95 | 0.00046 | 0.00533 | 2.2 | 2.6 |

| as displayed | buffer | scene px | MAE | edge MAE | PSNR dB | shimmer | edge shimmer |
|---|---|---|---|---|---|---|---|
| HEAD fixed 1080x1920 MSAA 4 | 1080x1920 | 1080x1920 | 0.00303 | 0.02461 | 34.72 | 0.00077 | 0.00498 |
| adaptive MSAA 4 | 693x1232 | 693x1232 | 0.00136 | 0.00735 | 42.36 | 0.00080 | 0.00506 |
| adaptive 2x box | 693x1232 | 1386x2464 | 0.00073 | 0.00456 | 43.66 | 0.00057 | 0.00401 |
| adaptive 1.5x box + MSAA 4 | 693x1232 | 1040x1848 | 0.00127 | 0.00775 | 41.83 | 0.00084 | 0.00546 |

### D: window 2560x1440, DPR 1, 16:9, buffer 2240x1260, reference scene 8960x5040

| config | scene px | MSAA | MAE | edge MAE | PSNR dB | shimmer | edge shimmer | ms median | ms p95 |
|---|---|---|---|---|---|---|---|---|---|
| none | 2240x1260 | 0 | 0.00150 | 0.02748 | 36.63 | 0.00096 | 0.01687 | 1.1 | 2 |
| msaa4 | 2240x1260 | 4 | 0.00105 | 0.01635 | 41.50 | 0.00063 | 0.00937 | 1.7 | 2.4 |
| msaa8 | 2240x1260 | 8 | 0.00109 | 0.01717 | 41.30 | 0.00061 | 0.00893 | 2.3 | 3.3 |
| fxaa | 2240x1260 | 0 | 0.00154 | 0.02858 | 37.81 | 0.00085 | 0.01444 | 1.1 | 1.8 |
| smaa | 2240x1260 | 0 | 0.00136 | 0.02423 | 38.30 | 0.00083 | 0.01384 | 1.4 | 2 |
| smaa+msaa4 | 2240x1260 | 4 | 0.00121 | 0.02034 | 39.98 | 0.00082 | 0.01367 | 2.2 | 2.9 |
| taa-x4 | 2240x1260 | 0 | 0.00086 | 0.01363 | 43.81 | 0.00052 | 0.00731 | 2.8 | 3.4 |
| taa-x8 | 2240x1260 | 0 | 0.00100 | 0.01495 | 43.30 | 0.00050 | 0.00659 | 4.6 | 5.6 |
| ss1.5-box | 3360x1890 | 0 | 0.00098 | 0.01768 | 41.11 | 0.00062 | 0.01001 | 1.7 | 2.4 |
| ss1.5-tent | 3360x1890 | 0 | 0.00120 | 0.02307 | 40.34 | 0.00062 | 0.01053 | 2 | 3 |
| ss1.5-box+msaa4 | 3360x1890 | 4 | 0.00087 | 0.01514 | 43.00 | 0.00051 | 0.00765 | 4.4 | 5.3 |
| ss2-box | 4480x2520 | 0 | 0.00064 | 0.01152 | 42.66 | 0.00043 | 0.00674 | 2.9 | 3.9 |
| ss2-tent | 4480x2520 | 0 | 0.00101 | 0.01974 | 41.06 | 0.00054 | 0.00896 | 2.7 | 3.6 |
| ss2-box+msaa4 **(best)** | 4480x2520 | 4 | 0.00053 | 0.00869 | 45.75 | 0.00034 | 0.00465 | 8.2 | 8.8 |

| as displayed | buffer | scene px | MAE | edge MAE | PSNR dB | shimmer | edge shimmer |
|---|---|---|---|---|---|---|---|
| HEAD fixed 1920x1080 MSAA 4 | 1920x1080 | 1920x1080 | 0.00271 | 0.03182 | 35.32 | 0.00080 | 0.00801 |
| adaptive MSAA 4 | 2240x1260 | 2240x1260 | 0.00104 | 0.01046 | 41.51 | 0.00063 | 0.00606 |
| adaptive 2x box | 2240x1260 | 4480x2520 | 0.00064 | 0.00737 | 42.66 | 0.00043 | 0.00436 |
| adaptive 1.5x box + MSAA 4 | 2240x1260 | 3360x1890 | 0.00087 | 0.00968 | 43.00 | 0.00051 | 0.00495 |

Case D's 2x + MSAA 4 (11.3 MP) is over the 5 MP live cap, so the recommended build runs 1x MSAA 4 there (1.7 ms); see open issue 3.

### Crops

`aa-crops/<case>-pipeline-{keys,feet-sparks,sky}.png` show reference, none, MSAA 4, SMAA, TAA x4, 1.5x+MSAA 4, 2x, 2x+MSAA 4,
each labelled with its numbers. `aa-crops/<case>-display-{keys,feet-sparks,sky,label,staff}.png` show the display path.

What they show:
- `B-2560x1440-pipeline-keys.png`: stair-steps on black-key sides and the rail line with none. MSAA 4 leaves visible steps on
  the black-key bevel highlights (shader aliasing). SMAA softens the edges but keeps crawling steps. 2x+MSAA 4 is the closest to
  the reference.
- `D-2560x1440-16x9-display-keys.png`: HEAD's 1920x1080 buffer stretched to 2240x1260 is visibly soft. Adaptive is crisp.
- `B-2560x1440-display-label.png`: the chord name lands in the same place in HEAD and adaptive; adaptive glyph edges are
  sharper.

Full-frame stills live in the scratch run folders; the final-chord recording-size snapshots
(`state/arsenal/receipts/piano-wash/lab-res-2x/07-final-chord.jpg` vs `final-4/07-final-chord.jpg`) are visually the same
picture.

## 6. What the numbers say about each option

- **Adaptive buffer (no browser resample).** The largest win of the lot: display-path edge error falls to about a third,
  whole-frame PSNR rises 8.3 / 8.3 / 7.6 / 6.2 dB. At 9:16 the fixed buffer's shimmer was already low only because the
  compositor's downscale blurs everything; at 16:9, where it upscales, HEAD's edge shimmer is .0080 vs .0061.
- **MSAA 8 is not better than MSAA 4** (slightly worse edge MAE in all four cases, at 0.1-0.6 ms more). MSAA resolves before
  tone mapping, in HDR. On the bright additive columns, lit keys and clearcoat highlights, a pixel that is part 8.0 and part 0.0
  resolves to 2.0, which Neutral tone mapping still maps to near white. Extra coverage samples do not show; filtering after tone
  mapping does. That is why supersampling with a post-tonemap downsample wins.
- **SMAA and FXAA** are worse than MSAA 4 on every metric, and FXAA's edge MAE is worse than no AA. Both blur the analytic column
  edges and speculars they cannot tell from geometry, and neither is temporal. SMAA + MSAA 4 is worse than MSAA 4 alone.
- **three's TAA (non-accumulating = jittered SSAA).**
  - x4 beats MSAA 4 by about 10% on edge error and shimmer, at 4 scene renders (1.6-2.8 ms).
  - x8 has less shimmer but more edge error than x4 (its 8-sample pattern averages in HDR too).
  - Both lose to 2x box at similar or lower cost.
  - A real TAA with reprojection does not exist for WebGLRenderer in three/addons (TRAA is WebGPU/TSL). It would ghost on
    exactly this content: fast-rising additive columns, sparks, and a follow camera.
- **Tent vs box.** The tent is worse on shimmer too, not only on MAE against a box reference, so this is not just reference
  bias: a wider kernel blurs detail the box keeps without calming the flicker.
- **1.5x** is poor for its cost. At a non-integer ratio each output pixel's footprint straddles scene texels differently, so
  edge error is no better than MSAA 4 (B: .0145 vs .0148). Hence the whole-factor rule in the caps.
- **2x box + MSAA 4.** Best in every case; the MSAA on top buys a further 20-25% edge error and about 30% shimmer over 2x
  alone.

## 7. Recording, cost, and the look checks

### Frame cost at 1080x1920 (REC size), headless, nothing else on the GPU

Run 1 is from the first probe; run 2 is the second solo probe.

| pipeline | scene | run 1 median / p95 ms | run 2 median / p95 ms |
|---|---|---|---|
| HEAD 1x MSAA 4 | 1080x1920 | 1.2 / 1.7 | 1.3 / 2.2 |
| 1x MSAA 8 | 1080x1920 | 1.6 / 2.0 | 1.6 / 2.7 |
| 1.5x box | 1620x2880 | 1.3 / 1.8 | 1.3 / 2.2 |
| 1.5x box + MSAA 4 | 1620x2880 | 3.0 / 3.5 | 3.3 / 4.1 |
| 2x box | 2160x3840 | 1.8 / 2.3 | 1.8 / 2.7 |
| **2x box + MSAA 4** | 2160x3840 | **5.3 / 5.8** | **5.9 / 7.0** |
| TAA x4 (1x) | 1080x1920 | 2.0 / 2.5 | 2.1 / 3.0 |
| SMAA (1x) | 1080x1920 | 1.1 / 1.4 | 1.2 / 1.8 |

Most of the MSAA 4 cost at 2x is the multisampled half-float resolve of an 8.3 MP target.

### Real recordings through `startRecording()`

`lab.record(4)` runs the real REC path for 4 s with the demo playing, and returns the file instead of uploading it. Files are
checked with PyAV (`analyze_rec.py`).

**Every file:**
- Track settings: width 1080, height 1920, aspectRatio .5625.
- Container `video/mp4;codecs=avc1.640028`; stream 1080x1920 h264; every decoded frame 1080x1920.
- After stop the live buffer returns to the adaptive size (459x816 in that 1600x1000 window).

| run | take (order in page) | REC scale | loop fps during REC (p95 ms) | frames requested | frames in file | fps from pts | largest gaps |
|---|---|---|---|---|---|---|---|
| unpaced, shared GPU | 1st | 1x MSAA 4 | 240 (4.3) | 240 | 92 | 22.85 | 2483 ms |
| unpaced, shared GPU | 2nd | 1.5x MSAA 4 | 238 (4.5) | 242 | 234 | 58.52 | 150 ms |
| unpaced, shared GPU | 3rd | 2x MSAA 4 | 153 (14.5) | 239 | 231 | 57.8 | 149 ms |
| unpaced, solo | 1st | 1x MSAA 4 | 240 (4.3) | 240 | 104 | 25.86 | 2283 ms at 0.166 s |
| unpaced, solo | 2nd | 1.5x MSAA 4 | 238 (4.4) | 242 | 234 | 58.68 | 133 ms at 0.137 s |
| unpaced, solo | 3rd | 2x MSAA 4 | 151 (15.1) | 238 | 230 | 57.8 | 129 ms at 0.197 s, 6 gaps > 25 ms |
| **paced (final code)** | 1st | 2x MSAA 4 | 60 (20.8) | 241 | 86 | 21.45 | 2563 ms at 0.166 s |
| **paced (final code)** | 2nd | 1x MSAA 4 | 60 (20.8) | 240 | 235 | 58.62 | 117 ms at 0.158 s |
| **paced (final code)** | 3rd | 2x MSAA 4 | 60 (16.8) | 235 | 233 | 58.41 | 124 ms at 0.001 s, 2 gaps > 25 ms |

In the paced rows the "loop p95" is the interval between drawn frames, about 16.7 ms by design, not GPU time.

Findings:
- **Size:** REC produces exactly 1080x1920.
- **Pacing:** without it, 2x + MSAA 4 on a 240 Hz loop drew 151 fps with a 15 ms p95 and left six stutters over 25 ms in the file.
  With it, 2x records as cleanly as 1x (58.4 vs 58.6 fps from timestamps, two gaps each).
- **First take after page load:** it loses about 2.3-2.6 s starting 0.17 s in, whatever the scale, pacing or GPU contention.
  In the first two probes that first take was HEAD's own 1x pipeline, so this is **pre-existing, not caused by this change**:
  most likely the H.264 MediaRecorder encoder warming up. Every take also has one 115-150 ms hitch in its first quarter second.
  Open issue 1.

### Look unchanged: wash check (lab default 2x + MSAA 4, snapshots at 1080x1920) vs HEAD's `final-4`

| shot | luma HEAD > lab | white | lit | litSat | upper | keysSat |
|---|---|---|---|---|---|---|
| 01-bar1 | .1249 > .1247 | .0086 > .0086 | .1421 > .1427 | .4866 > .4868 | .1006 > .1005 | .3115 > .3116 |
| 02-bar4-changes | .1251 > .1253 | .0083 > .0083 | .1178 > .1184 | .4445 > .4450 | .1056 > .1056 | .2773 > .2776 |
| 03-bar8-changes | .1263 > .1265 | .0083 > .0083 | .1170 > .1175 | .4473 > .4465 | .1075 > .1075 | .2840 > .2833 |
| 04-hold-2bars | .1197 > .1201 | .0096 > .0095 | .1698 > .1703 | .6247 > .6240 | .0988 > .0989 | .4537 > .4528 |
| 05-hold-6bars | .1376 > .1377 | .0075 > .0075 | .1855 > .1856 | .6722 > .6713 | .1202 > .1202 | .5707 > .5683 |
| 06-hold-8bars | .1447 > .1447 | .0076 > .0076 | .1867 > .1867 | .6445 > .6442 | .1206 > .1206 | .5316 > .5289 |
| 07-final-chord | .1481 > .1486 | .0039 > .0039 | .1218 > .1228 | .4802 > .4798 | .1175 > .1180 | .2896 > .2892 |
| 08-lift+0.0s | .0899 > .0901 | 0 > 0 | .0644 > .0649 | .1318 > .1330 | .0573 > .0573 | .0882 > .0908 |
| 09-lift+2s | .0824 > .0826 | 0 > 0 | .0553 > .0558 | .1352 > .1367 | .0419 > .0420 | .0891 > .0912 |
| 10-lift+5s | .0837 > .0839 | 0 > 0 | .0566 > .0570 | .1316 > .1331 | .0416 > .0417 | .0914 > .0934 |

Summary:
- HEAD: peak white .0096 (04), min lit saturation .1316, peak upper .1206, lift clears .354.
- Lab: peak white .0095 (04), min lit saturation .133, peak upper .1206, lift clears .353.
- Events 388/388, no errors.
- Light budget, bloom decay and saturation are unchanged. Saturation reads marginally higher because supersampled edges mix
  less grey into lit pixels.
- Lab min fps 216 was one snapshot sample, taken while `snapshot()` resized its render targets.

### Look unchanged: sustain check (key glow)

| run | held v100 | held + pedal | pedal only early | pedal only 3 s | held v30 | held v127 | storm min / max |
|---|---|---|---|---|---|---|---|
| HEAD `final-sustain-3` | .946 | 1.167 | .742 | .517 | .593 | 1.068 | .540 / .977 |
| lab 2x, shared GPU | .920 | 1.148 | .703 | .506 | .578 | 1.040 | .538 / .902 |
| lab 2x, solo | .922 | 1.149 | .696 | .506 | .578 | 1.040 | .539 / .911 |
| lab `?recscale=1`, solo | .930 | 1.157 | .725 | .511 | .583 | 1.052 | .539 / .938 |
| **lab `?fixed=1&recscale=1`, solo** | **.943** | **1.167** | **.750** | **.518** | **.592** | **1.065** | **.540 / .979** |

The glow values are a pure function of time since the note event, and sustain_check reads `stats()` after its snapshot.
- The lab's `snapshot()` resizes the pipeline to 1080x1920 at the REC scale and back: two reallocations of 8.3 MP MSAA targets
  at 2x. That delays the reading, and the envelope has decayed a little further by then.
- The readings recover in step with the resize removed: 2x, then 1x, then no resize at all (`fixed`). With no resize they
  match HEAD within sampling jitter.
- The patch changes no line of the light model (checked: no added or removed line touches `LIGHT`, `glowLevel`, `lightLevel`,
  `envelope`, `releaseLevel`, `velFactor`, `glowTarget`, `uDensity` or `LIGHT_BUDGET`).

### Final sizing check (final code)

`scripts/final_check.mjs` checks the final code: window 2560x1440, demo playing, HUD read then hidden for the screenshot
(it overlaps a 16:9 canvas). "Screenshot vs buffer" is the MAE between a page screenshot and `readPixels` of the same frame,
best of +-2 device pixels.

| step | device box | buffer | scene | MSAA | downsample | CSS box | screenshot vs buffer | HUD render row |
|---|---|---|---|---|---|---|---|---|
| 9:16, DPR 1 | 711x1264 | 711x1264 | 1422x2528 | 4 | yes | 711 x 1264 | 0 | `711x1264 (9:16) · scene 1422x2528 MSAA 4` |
| 16:9, DPR 1 (2x is 11.3 MP, over the 5 MP live cap) | 2240x1260 | 2240x1260 | 2240x1260 | 4 | no | 2240 x 1260 | 0 | `2240x1260 (16:9) · scene 2240x1260 MSAA 4` |
| back to 9:16, runtime DPR 1 -> 1.5 (CDP emulation) | 1143x2032 | 1143x2032 | 1143x2032 (2x is 9.3 MP, over the cap) | 4 | no | 762 x 1354.67 | .0034 | `1143x2032 (9:16) · scene 1143x2032 MSAA 4` |
| window resized to 1600x1000, DPR 1 | 513x912 | 513x912 | 1026x1824 | 4 | yes | 513 x 912 | 0 | `513x912 (9:16) · scene 1026x1824 MSAA 4` |

- `snapshot()` afterwards returns 1080x1920, and the live buffer is back at 513x912. No errors.
- In the first run of this check the DPR step sized the buffer to 762x1355: under `Emulation.setDeviceMetricsOverride`,
  `devicePixelContentBoxSize` reports CSS pixels. The `matchMedia` listener did fire (the CSS box re-snapped to 762 x 1354.67,
  i.e. 1143x2032 device pixels).
- `onCanvasBox()` now falls back to CSS size x DPR when the two disagree by more than 2 px, which fixed it (row above).
- The remaining .0034 is how emulation composites. With a real device scale factor (case C, `--force-device-scale-factor=1.5`,
  CSS 462 x 821.333) the screenshot equals the buffer exactly.

## 8. Merging it

1. Wait for the other build to land its `piano.js` changes.
   - As of this writing it adds imports (hunk at line 9/17).
   - It changes `drawRuns`, `measureRuns` and `drawLabel`.
   - It grows the `overlay` object and `LAYOUT`.
   - It touches the notes engine.
2. Apply `adaptive-resolution-aa.patch` with `git apply -3` against `a886a0af`'s blob, or port the hunks by hand. Expect
   conflicts at the import line, `drawRuns` (the `shadowBlur` line), `drawLabel` (the `setTransform` lines) and `makeLayer`.
3. Rules for any new overlay drawing the other build added:
   - Draw inside `drawLabel`/`drawStaff`, after their `setTransform`, or call `ctx.setTransform(layer.sx, 0, 0, layer.sy, 0, 0)`
     yourself.
   - Multiply `shadowBlur` (and `shadowOffsetX/Y`, if used) by `shadowScale`.
   - Create layers with `makeLayer()`, so they get one texel per output pixel and pixel snapping.
   - A new Canvas2D texture made outside `makeLayer()` needs the same treatment, or it will be resampled like HEAD's overlay.
4. Decide on the lab-only code. Recommended: keep the query params (`scale`, `recscale`, `msaa`, `filter`) and the `snapshot()`
   options. Keep `__piano.lab` if the receipts should keep working (`sim`/`grab`/`bench` were the whole measurement harness).
   Drop `setLabAA`, `LAB.aa*`, `?fixed=1` and the `taa/smaa/fxaa` branches.
5. `piano.css` says "The canvas backing store is fixed at 1080x1920 or 1920x1080"; update that comment when merging. Not
   edited here, because the other build owns the page files.
6. Re-run on the merged page: `wash_check.mjs` (compare to `final-4`), `sustain_check.mjs` with `?fixed=1&recscale=1` for exact
   glow parity, `scripts/aa_bench.mjs` (quality) and `scripts/rec_probe.mjs <port> 9:16 reconly` (file size, fps, gaps).
7. Look at it on Daniel's real monitor: HDR, real refresh rate, real compositor. Headless screenshots prove the 1:1 mapping
   in Chrome's compositor, not in his display chain.

## 9. Open issues

1. **The first recording after a page load loses about 2.3-2.6 s of frames** (starting 0.17 s in), and every take has one
   115-150 ms hitch at the start. It reproduced with HEAD's own 1x pipeline, so it predates this work. Likely cause: H.264
   MediaRecorder encoder start-up. Candidate fix: warm the encoder when the page arms REC (a short throwaway `MediaRecorder`
   on a canvas stream at framing size, or start recording 0.5 s before showing "REC" and trim). Must be verified in Daniel's real
   (non-headless) Chrome, since headless may take a different encoder path.
2. **Merge conflict with the running build** (section 8). The patch is against `a886a0af`.
3. **The live cap is a pixel count, not a frame-time governor.**
   - 16:9 at 2560x1440 (2240x1260) falls to 1x MSAA 4 (1.7 ms), although 2x without MSAA would fit at 2.9 ms (edge .0115,
     shimmer .0067 vs .0164 / .0094).
   - A governor that measures real frame time on Daniel's display and picks the step (2x+MSAA 4, then 2x, then 1x+MSAA 4) would
     be better than a fixed 5 MP.
   - All costs here come from a headless GPU shared with his desktop session.
4. **The live view during REC is browser-scaled and 60 fps.** That is by design and matches what HEAD showed, but on a 240 Hz
   monitor recording will look less fluid than live play.
5. **`snapshot()` resizes the render targets twice per call** (tens of ms at 2x). That is harmless live, but a test that reads
   `stats()` right after a snapshot sees slightly later values. Use `?fixed=1&recscale=1` for exact glow parity, or read stats
   before snapshotting.
6. **Residual aliasing.**
   - Clearcoat and specular highlights on key bevels are shader aliasing that only more samples reduce; specular AA (roughness
     widened by normal variance) would target it directly.
   - Sparks below 1 px still twinkle slightly.
   - The FXAA shader logs an X3595/X4000 warning, in the lab only.
7. **HDR.** The canvas remains an 8-bit sRGB SDR surface; nothing here uses the HDR monitor's range.
8. **A 1280-wide window wraps the topbar onto several rows**, leaving a 378x672 canvas. That is layout, not resolution, but it
   caps sharpness on small windows.
9. **A runtime DPR change was only exercised through CDP device emulation.** Emulation composites with a small resample
   (MAE .0034), and needed the CSS x DPR fallback. A real change (dragging the window to another monitor, browser zoom) could
   not be driven headless. A startup DPR of 1.5 was exact. Check once on Daniel's machine: press Ctrl+= / Ctrl+- with the HUD
   (H) open, and the render row should show a buffer that is the canvas's CSS size times the zoom.
