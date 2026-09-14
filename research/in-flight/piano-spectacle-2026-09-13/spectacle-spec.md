# Piano spectacle: build spec (rarity tiers, stage effects, adaptive resolution)

Status: build spec, 2026-09-14. It merges the judged design round into one system. Nothing in `arsenal/` was edited to
write it; the only new files are this spec and `spec-calibration-lab/` beside it (pure node re-runs of the round's labs
under the merged rules). Nothing was committed.

Target: `arsenal/web/piano.js` (three.js r186, one ES module) and `piano.html`, **after the practice-log / Nashville
build lands and is committed**. That build is editing `piano.js`, `piano.html`, `piano/log.js`, `piano/nashville.js` and
the arsenal Python files now; every line number and layout number below that comes from its working copy must be re-read
once it lands.

Daniel, verbatim, tonight:
> "Can you reload the piano page and make it be perfectly un-aliased, can we make it even more a visual spectacle? Perhaps
> even having a rarity and fanciness scale xD"
>
> "Lets make the resolution be adaptive to the render window"

Rules from earlier tonight that still bind every line of this spec:
> "notes dont stay lit if I have sustain pressed, when I hold sustain and other notes it should be brighest when I am
> pressing sustain and note at same time, velocity should be a factor as well"
>
> "Can you make the piano note colors more saturated and visible? also the bloom doesn't seem to decay or go down, it just
> stacks" (fixed in a886a0af: the shared `LIGHT` envelope, `LIGHT_BUDGET`, the gamut-mapped palette; PIANO-V2-SPEC section 2)

Also binding: 60 fps (or native refresh) at 1080x1920 on the RX 9070 XT; recordings are 1080x1920 at 60 fps for TikTok;
everything that matters is inside the recorded canvas; the chord name and staff stay readable; the frame never washes out.

Sources merged here, all in `research/in-flight/piano-spectacle-2026-09-13/`:

| Source | What it contributed |
|---|---|
| `design-theory-rarity.md` + `design-theory-rarity-lab/` | the score (fanciness x familiarity + novelty), honesty gates, bloom merge, banner gate, log plumbing |
| `design-vfx-director.md` + `prototype-vfx/` + receipts `state/arsenal/receipts/piano-spectacle/vfx/` | the stage effects, light rules, house lights, gold-only-for-Legendary, AA discipline for effects |
| `design-loot-feel.md` + `mockups/` | TikTok safe zones, the reveal in the rest, voice-leading credit, restraint rules, collision receipt, the long game |
| `adaptive-resolution-aa.md` + `.patch` + `adaptive-resolution-data/` + `aa-crops/` | the resolution and AA pipeline, recording plan, measurement harness |
| `judge-delight-and-viewer.md` | scores 8.5 / 7.5 / 6, merged system, cuts |
| `judge-feasibility-performance-honesty.md` + `judge-feasibility-data/` | scores 8 / 7 / 6, three merge conditions for the AA patch, HEAD recording control, MSAA resolve probe |
| `spec-calibration-lab/` (new, this spec) | merged-rule session sim, F major example table, note-level bloom tracker sim |

---

## 0. The system in one screen

1. **Foundation first (phase 0).** Merge the adaptive-resolution patch with three changes: MSAA only on the scene
   target, a pre-allocated REC pipeline plus encoder warm-up, and a frame-time governor. Nothing below is tuned until
   this pipeline is in, because every effect's pixel constants and every light number depend on it.
2. **The tier is about the chord.** `Φ = F × h + novelty`. F (fanciness) is what the chord is as music; h (familiarity)
   dims what Daniel plays all the time; novelty is a checkable claim ("first this session", "rare for you", "first time
   ever"). Velocity and the crescendo arc never change the tier; they size the effect.
3. **One event per harmonic gesture.** A pedalled arpeggio, a rolled chord and a block chord are each one event. The
   boundary is a gesture (pedal lift, bass change, block strike, rest), not a clock. Measured: one event per bar at 0.33,
   0.50 and 0.65 s a note; pedal-point changes stay separate.
4. **Rationed.** One banner gate: 6 s apart, tier cooldowns (Rare 12 s, Epic 30 s, Legendary 120 s), no Legendary in
   the first 45 s, per-chord limits, an inflation guard that only tightens. Daniel-style play (synthetic): about 11 Rare,
   3 Epic and 1.5 Legendary banners per 10 minutes, zero while he loops.
5. **Tier is shown as stage, not as HUD.** Effects use the empty stage (floor ring, rail, light shafts behind the
   columns, a gold hem ribbon) in the chord's own pitch colours. **Gold means Legendary and nothing else.** House lights
   dim old columns so the spectacle adds contrast, not luma. Text is drawn after bloom and never enters the light budget.
6. **Every banner says why**, in music words, and names the chord and its Nashville number, so a personal tier is honest
   on a public clip.
7. **The reveal in the rest.** A phrase that earned Epic or better gets one calm card in the silence after it.
8. **Modes:** Off (byte-identical to today) / Tasteful / Full, persisted. History is recorded in every mode. No
   summon-a-tier control exists outside a lab test hook that refuses to run during REC.

---

## 1. Decision log (where the round disagreed, what this spec decides, and why)

| # | Question | Decision | Why |
|---|---|---|---|
| D1 | Adopt the AA patch as is? | Adopt, with the three changes of section 3.3, before any effect work | Both judges; the MSAA-on-post-targets fix is measured pixel-identical (MAE 0) and 23% cheaper at REC size |
| D2 | Scorer: theory's music score, vfx's intensity score, or loot's DROP_TABLE? | Theory's `Φ = F·h + bonus`, with the velocity accent removed from F | Judge 2: vfx's strike and accent gates lock out rolled voicings (Daniel's style) and turn rarity into loudness; loot's +3 voicing points make his habitual Dm11/G LEGENDARY every time and have no familiarity |
| D3 | Judge 1 wanted performance as gates for Epic and Legendary | No velocity gate. Instead, a **passing** event (replaced before it settled) keeps its tier in the log but is presented at most as the Uncommon sheen. The climax is honoured by intensity (effect size) and by the phrase card | Keeps velocity out of the tier (all three designs agree on that) while a fancy chord brushed in passing still cannot fire a Legendary |
| D4 | How far can novelty lift? | At most one tier above the no-novelty tier. Exception: "first time ever" may lift two tiers, only into Legendary or Mythic | Judge 1. A plain one-tier cap would make Mythic unreachable (it always sits two above its base). Measured: changes 4 of 215 cells in the example table (all "first ever" Epic to Rare); never bound in the session sims |
| D5 | Token buckets (vfx) or banner gate (theory)? | The banner gate, plus vfx's "no Legendary in the first ~45 s" | Judge 2: one mechanism. The gate's tier cooldowns already bound Epic and Legendary rates; measured rates in 4.4 |
| D6 | Bloom merge window | Gesture boundaries, adaptive settle, the richest committed reading | Judge 2 flagged the fixed 1.6 s window; the note-level sim confirms it splits slow bars into 3.2-3.75 events and the spec tracker holds 1.00 (4.2) |
| D7 | Common rail pulse on every chord change (noise) | Suppressed on home chords (a Common event with h < 0.75) | Judge 1 concern. Measured 8.6 pulses a minute for Daniel-style play (of 30 events), 0.5 a minute on a triad loop |
| D8 | Where does the banner go in 9:16? All three designs picked y 485-595 | The other build has since put its Nashville row there (layer y 471-601). The banner **borrows that slot** for its hold: the row crossfades out, and the number moves into the banner's first line | No free band exists between the chips (436) and the clef top (586). The number stays visible. Open question Q1 |
| D9 | Camera push | Legendary only, 3%, no yaw, skipped on fast pans; none on Epic | Judge 2 (seasick risk at 5.5% with yaw); restraint makes Legendary read |
| D10 | Aurora | Gold hem ribbon only; upper haze cut. Dispersion fringe cut. Fountain capped at 600 | Both judges |
| D11 | Theory's key rim, bloom +0.1, spark count x1.5 | Cut | Keys keep pitch colours (sustain meaning); bloom lifts are what Daniel complained about |
| D12 | Loot's in-canvas HUD (medallion, gauge, pips tag, rarity bar, orange Legendary) | Cut from the canvas. Kept: safe-zone map, collision receipt, rest reveal, voice-leading credit, restraint rules | Both judges |
| D13 | Dex, haul card, unlock banners | Deferred to phase 5, off canvas, after the log vocabulary exists | Both judges |
| D14 | Summon pad / staged Mythic (vfx E16), time dilation (E14) | Cut. A lab-only `force()` hook exists for receipts and refuses during REC | A staged tier on a public clip is a false claim; E14 touches the LIGHT time base |
| D15 | Reason words | Corrected vocabulary (2.3): "borrowed from F minor", "secondary dominant (leads to Dm)", "altered tension"; no "chromatic mediant" | Judge 2 found three theory slips in the design text |

---

## 2. Glossary (plain words)

### 2.1 Music words (examples in F major: F G A Bb C D E)

| Word | Plain meaning | F major example |
|---|---|---|
| Triad | Three notes stacked in thirds: root, 3rd, 5th | F = F A C; Dm = D F A |
| Root | The note a chord is named after | F in Fmaj7 |
| Seventh chord | A triad plus the 7th above the root | Bbmaj7 = Bb D F A |
| maj7 / 7 | maj7 adds the note a half step below the root's octave (dreamy); a plain 7 adds the note a whole step below (bluesy, wants to move) | Fmaj7 has E; F7 has Eb |
| Extension (9, 11, 13) | Notes past the 7th: the 2nd, 4th and 6th an octave up. Lush colour | Dm9 adds E to Dm7 |
| Altered dominant | A dominant (7) chord with its 5th or 9th bent a half step (b9, #9, b5, #5, #11): maximum tension | A7b9 = A C# E G Bb |
| Altered tension | One of those bent notes; it can sit outside the key while the chord's root and type are in it | C7b9's Db |
| Inversion | The same chord with another chord note in the bass | F/A |
| Slash chord / foreign bass | "Chord/bass". An inversion if the bass is a chord note; a **foreign bass** if it is not, which stacks two harmonies | C/G is an inversion; Bb/C has a foreign bass |
| Voicing | How the notes are spread: close, open, dense | Fmaj9 over two octaves is open |
| Diatonic | Made only of notes of the key's scale | Gm7, Am7, Bbmaj7 |
| Borrowed chord | Taken from the parallel key (F minor for F major) | Bbm (the "sad four"), Eb, Db, Ab, Gm7b5 |
| Secondary dominant | The dominant ("five") chord of another chord in the key, leading into it | A7 leads to Dm; D7 leads to Gm |
| Chromatic mediant | A major or minor chord whose root is a third away and that shares few notes with the key | For F: A, Ab, D, Db |
| Neapolitan | The major chord a half step above the tonic | Gb major in F |
| Pedal point | A bass note held (often by the pedal) while chords change above it | Low C under F/C, Gm/C, C7 |
| Nashville number | A chord named by its scale step in the key, so a habit reads the same in every key | Bbmaj7 = 4maj7; F/A = 1/3; A7 = 3⁷ |
| Voice leading | How each note moves to the next chord. Smooth = common notes kept and the top voice moving a step or less | F → C/E → Dm → Bbmaj7 |
| Crescendo | Getting louder over several chords | Bbmaj9/D 96 → C9sus4 102 → Fmaj9 120 |

### 2.2 System words

| Word | Plain meaning |
|---|---|
| Committed chord | The chord name the overlay actually shows, after its settle (120 ms after a note-on, 300 ms after a release) |
| harmonySet | The notes that name the harmony: finger-held notes, pedal-held notes struck in the last 1.5 s, and the lowest pedal note when it is the bass (PIANO-V2-SPEC 6.1) |
| Event (bloom) | One harmonic gesture: a pedalled arpeggio, a rolled chord or a block chord, however many names it passes through |
| Passing event | An event replaced by the next one before it settled |
| Fanciness F | A number for what the chord is, as music: colour + bass + voicing + distance from the key |
| Familiarity h | 0.5 to 1.0. Falls as a chord becomes one Daniel plays a lot, tonight or across his log |
| Novelty bonus | A small lift for a claim the data can back, printed on the banner |
| Φ (phi) | The score that picks the tier: F × h + novelty |
| Tier | Common, Uncommon, Rare, Epic, Legendary, Mythic |
| Banner gate | The rule deciding whether a scored tier gets its banner now, or falls back to the quiet look |
| Cooldown | Minimum seconds since the last banner of that tier or higher |
| Inflation guard | Raises the Rare-and-up thresholds when too many rare events pile up; it can only make tiers stricter |
| Intensity I | 0.6 to 1.0: how big an effect is drawn inside its tier, from velocity and the crescendo arc |
| Light budget | `LIGHT_BUDGET`: how much old light the trails may show at once; old light dims first, fresh strikes and held keys never |
| House lights | A tier dimming old columns through the light budget while it plays |
| Bloom threshold | 0.9 linear: light above it glows. Only thin crests may cross it |
| Protect mask | A soft shape that fades effect light before it reaches the chord name, staff and banner |
| Drawing buffer | The canvas's real pixel grid |
| Supersampling (SS 2x) | Rendering the scene at twice the width and height, then averaging each output pixel's 2x2 footprint |
| MSAA 4 | Four coverage samples per pixel on geometry edges |
| Governor | Picks the highest quality step whose measured frame cost fits the display's refresh |
| REC pipeline | A second, always-allocated render path at the recording size |

### 2.3 Reason vocabulary (what the banner may say)

At most two reasons on the banner, in this priority order. The HUD shows all of them.

1. **Novelty, when it lifted the tier** (always printed then): "first time ever" / "rare for you" / "first time tonight" /
   "first this session" / "back again".
2. **Relation to the key** (only when the key is locked, or the tracker is "sure" or "fair"), from `harmonicRole(info, key)`:
   - "borrowed from F minor": not diatonic, and every chord tone is in the parallel key's scale (natural minor, or major
     for a minor key);
   - "secondary dominant (leads to Dm)": a major or dominant-type chord (suffix "", 7, 9, 13, 7b9, 7#9, 7#5, 7b5, 7#11,
     7sus4, 9sus4) whose root is a perfect fifth above the root of a diatonic chord on scale degrees 2 to 6 of a major key
     (3 to 7 of a minor key, where the chord on 2 is diminished), naming that target with the overlay's spelling;
   - "altered tension": diatonic root and type, and every outside note is a b9, #9, #11/b5, #5 or b13 of the chord's root;
   - "far outside the key": K ≥ 2.25 and none of the above;
   - "outside the key": K ≥ 1.5 and none of the above;
   - "one note outside the key": 0 < K < 1.5 and none of the above.
3. **Colour** (from C): "altered dominant" (C ≥ 4.5); "sharp eleven" (maj7#11, 7#11); "altered fifth" (7b5, 7#5,
   maj7#5); "rich extension" (C ≥ 2.75); "seventh colour" (C ≥ 2.0).
4. **Bass** (B ≥ 1.25): "foreign bass" / "7th in the bass" / "colour note in the bass".
5. "wide voicing" (V ≥ 0.75); "pedal point".

Never: "accented" (velocity is not a reason), "chromatic mediant" (not computed), "borrowed note" (replaced).

---

## 3. Phase 0: adaptive resolution, anti-aliasing and recording

### 3.1 The chosen approach (from `adaptive-resolution-aa.md`, adopted)

1. **Adaptive drawing buffer.**
   - `fitCanvas()` snaps the canvas's CSS box to whole device pixels in the framing's exact aspect (9n x 16n).
   - A `ResizeObserver` with `{ box: "device-pixel-content-box" }` sizes the buffer. It falls back to CSS size x DPR
     when the two disagree by more than 2 px.
   - `matchMedia("(resolution: Xdppx)")` re-snaps on a DPR change.
   - The buffer is capped at 3840x2160.
2. **Scene at 2x with MSAA 4, box downsample in linear light after tone mapping** (`DownsamplePass`, exact footprint
   weights, sRGB decode, average, encode). At scale 1 it is disabled and the pipeline equals HEAD.
3. **Bloom pinned to the framing size** (`FramingBloomPass` sizes the stock `UnrealBloomPass` to 1080x1920 or 1920x1080).
   The glow has one shape live, in a small window and in the file.
4. **Pixel-sized things follow the scene target:** sparks' `uPx`, the lens-shift view offset in scene pixels; overlay layers
   get one canvas texel per output pixel via `makeLayer()`, `ctx.setTransform(sx, 0, 0, sy, 0, 0)`, and `shadowBlur` x
   `shadowScale`.
5. **Recording at exactly the framing size**, scene at `recScale` 2, paced to 60 drawn frames a second.

Evidence (headless, ANGLE D3D11, RX 9070 XT, frozen deterministic frame, 16-samples-a-pixel reference):

| Measure | HEAD | Adopted |
|---|---|---|
| Display-path edge MAE, windows A / B / C (DPR 1.5) / D (16:9) | .0284 / .0259 / .0246 / .0318 | .0098 / .0076 / .0074 / .0105 (adaptive MSAA 4) |
| Screenshot vs drawing buffer | browser resample | MAE 0.000000 in all four cases |
| Pipeline edge MAE A / B / C / D, best of 14 configs | MSAA 4: .0175 / .0148 / .0143 / .0164 | SS 2x box + MSAA 4: .0087 / .0070 / .0070 / .0087 |
| Edge shimmer under a 0.37 px/frame pan | MSAA 4: .0108 / .0096 / .0096 / .0094 | .0061 / .0053 / .0053 / .0047 |
| Cost at 1080x1920 output, median / p95 | 1.2 / 1.7 ms | 5.3 / 5.8 ms (second run 5.9 / 7.0) |
| Wash check vs `final-4` | peak white .0096, min lit sat .1316, lift clears .354 | .0095, .133, .353; events 388/388 |
| Sustain glow, parity mode | .946 / 1.167 / .742 / .517 / .593 / 1.068 | .943 / 1.167 / .750 / .518 / .592 / 1.065 |

MSAA 8, SMAA, FXAA, three's TAA addon (non-accumulating), tent filters and 1.5x all lost (reasons in the AA doc section 6).

**Say this to Daniel plainly:** "perfectly un-aliased" is not literally reached. Edge error against the 16-sample
reference is about .007, not 0. What remains is specular sparkle on the glossy key bevels and sub-pixel sparks (3.6).

### 3.2 Merging the patch

1. Wait for the other build's commit. The patch is against `a886a0af` (blob `de585129`).
2. `git apply -3 research/in-flight/piano-spectacle-2026-09-13/adaptive-resolution-aa.patch`, or port by hand. Expected
   conflicts, from the working copy read on 2026-09-14:
   - the import block (the other build adds `./piano/log.js` and `./piano/nashville.js`);
   - `drawRuns` / `measureRuns` (the other build added per-run `letterSpacing`; keep both, and multiply the glow
     `shadowBlur` 38 by `shadowScale`);
   - `drawLabel` (keep the other build's "Numbers only" branch; add `setTransform` + `shadowScale` at the top);
   - the overlay object (the other build added `nns: makeLayer(L.nns)` and `drawNumbers`).
3. **The other build's `drawNumbers(layer, info)` must also start with** `ctx.setTransform(layer.sx, 0, 0, layer.sy, 0, 0);
   shadowScale = layer.sy;`, or the Nashville row will be drawn at framing scale into an output-scale canvas.
   `keyCaptionRuns` sets `letterSpacing` in pixels; check at k = 0.5 that the caption's width scales with the transform
   (receipt R7 measures it).
4. **Drop** `setLabAA`, `LAB.aa*`, the TAA/SMAA/FXAA imports and branches, the tent filter and non-integer scales.
   **Keep** `?scale`, `?recscale`, `?msaa`, `?fixed=1` (the parity mode for glow receipts), `snapshot({native, png})`,
   and `window.__piano.lab.{res, set, freeze, unfreeze, seed, sim, grab, bench, record}`. They are the whole measurement
   harness. Attach `__piano.lab` only when the page URL has `?lab=1`.
5. Update the stale `piano.css` comment ("The canvas backing store is fixed at 1080x1920...").
6. Copy the receipt drivers into the repo, because the originals live in a temporary session scratchpad:
   `wash_check.mjs` and `sustain_check.mjs` (from `C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/`), and `aa_bench.mjs`,
   `rec_probe.mjs`, `analyze_rec.py`, `cdp.mjs` (from `adaptive-resolution-data/scripts/`) go to
   `arsenal/lanes/piano-receipts/`.

### 3.3 The three required changes

**C1. MSAA only where geometry is drawn.**
- Today `EffectComposer` clones its target, so both `renderTarget1` and `renderTarget2` are 4-sample. Only the
  `RenderPass` needs samples; `OutputPass` writes a full-screen quad into an 8.3 MP multisample target for nothing.
- Measured (judge 2, `judge-feasibility-data/msaa-resolve-probe.json`): at REC size, `renderTarget1` single-sample took the
  median from 6.3-6.5 ms to **4.9 ms** (p95 5.7-5.9), **MAE 0, max abs diff 0**.
- Build it robustly, not by relying on the swap order (at 1x the targets alternate roles): a `MsaaScenePass` owns
  `sceneTarget` (HalfFloat, `samples: RES.msaa`) and renders the scene into it. It then hands the resolved texture on as
  `readBuffer`, either by copy or by rendering into the single-sample composer buffer with `renderer.setRenderTarget` and
  a resolve blit. The composer's own targets are created with `samples: 0`. `FramingBloomPass`'s blend then lands on a
  single-sample target.
- Acceptance: R0.4.

**C2. A pre-allocated REC pipeline, a no-realloc snapshot, and an encoder warm-up.**
- Why:
  - Judge 2's HEAD control (`rec-analysis-head-control.json`) confirms the first take after page load loses about 2.5 s
    (92 frames, a 2500 ms hole at 0.162 s), and every take has a ~133 ms start hitch.
  - The lab's REC-start reallocation lengthened warm-take hitches to 183-283 ms and lost 5-9 more frames per 4 s (n=1,
    shared GPU).
- **REC pipeline.**
  - At boot idle (after `loadFonts`, via `requestIdleCallback` with a 2 s timeout), build `recComposer`:
    - its own `sceneTarget` at framing x `recScale` with MSAA;
    - single-sample post targets;
    - a `FramingBloomPass` (shares the bloom settings), `OutputPass` and `DownsamplePass`;
    - an 8-bit RGBA `recOutput` target at the framing size.
  - Keep it for the page's life. Estimated VRAM at 2160x3840: MSAA colour ~265 MB, MSAA depth ~130 MB, resolved scene
    and two post targets ~200 MB. That is about 600 MB of the card's 16 GB.
  - If allocation throws or the context is lost, fall back to allocating at REC start with `recScale` 1 and toast once.
- **REC start** becomes:
  - `renderer.setSize(framing.w, framing.h, false)` (the drawing buffer change is unavoidable, because `captureStream`
    records the canvas);
  - switch the active composer pointer to `recComposer`;
  - `overlay.build()` at k = 1;
  - then `canvas.captureStream(0)`.
- **REC stop** switches back.
- **`snapshot()`** renders the REC pipeline into `recOutput`, draws the overlay scene into the same target, reads it with
  `readRenderTargetPixels`, and encodes a JPEG (or PNG) through a 1080x1920 2D canvas. The live drawing buffer, `RES.output`
  and the live composer are untouched.
  - This removes the timing shift the glow receipts saw (the AA doc section 7): snapshot no longer reallocates.
- **Encoder warm-up.** At boot idle, after the REC pipeline:
  - create a detached 1080x1920 `<canvas>` (2D context);
  - `captureStream(0)`;
  - `new MediaRecorder` with the same MIME and 16 Mbps;
  - draw and `requestFrame()` 30 frames at 60 fps;
  - `stop()`, and discard the blob.

  Repeat on framing change (1920x1080).
- **If R0.6 still shows a first-take hole after warm-up:** switch REC to `piano/recorder.js` (WebCodecs, constant frame
  rate: frame n stamped at n/60 s, PIANO-V2-SPEC section 3), provided that lane's own receipt has passed. A CFR encoder
  cannot open a wall-clock hole; that is the root-cause fix, and MediaRecorder stays as its fallback.

**C3. A frame-time governor for the live view** (replaces the fixed 5 MP cap).
- **Ladder:** L0 SS 2x + MSAA 4 · L1 SS 2x, no MSAA · L2 1x + MSAA 4 · L3 1x, no MSAA.
- **Hard safety cap:** 16 MP scene pixels.
- Why a ladder: the fixed cap floors to 1x on large windows (a fullscreen 1215x2160 canvas; 16:9 at 2240x1260), although
  2x without MSAA beats 1x MSAA 4 (edge .0091 vs .0148 at case B; .0115 vs .0164 at D) at 1.1-2.9 ms.
- **Refresh period P:** the median `requestAnimationFrame` interval over the last 120 frames, clamped to 4.1-16.7 ms.
- **Calibrate:**
  - When: at boot, after any resize, framing or DPR change (debounced 500 ms), and never while notes sound (wait until 2 s
    of silence) or during REC.
  - For each step from L0 down, render 12 frames synced by a 1-pixel `readPixels` and take the median.
  - Pick the first step whose median ≤ 0.45 · P. About 20-40 ms of work, invisible in silence.
- **Watchdog:** if the p95 frame interval over a 3 s window exceeds 1.5 · P in two consecutive windows, step down one
  rung. Step up only by recalibration.
- **Frozen during REC** (REC uses the REC pipeline and its own 60 fps pacing).
- **Overrides:** `?res=L0..L3` pins a step; `localStorage arsenal.piano.resStep` = "auto" | "L0".."L3".
- **HUD render row**, e.g.: `711x1264 (9:16) · scene 1422x2528 MSAA 4 · L0 · 2.4 ms / budget 1.9 ms`.

### 3.4 Recording plan

| Aspect | Plan |
|---|---|
| File size | Exactly the framing size: 1080x1920 (or 1920x1080), H.264 in MP4 (`avc1.640028` measured), 16 Mbps |
| Scene | `recScale` 2: 2160x3840, MSAA 4 on the scene target only, box downsample; bloom at the framing size |
| Cost | ≤ 5.0 ms median at REC size after C1 (4.9 ms measured), plus effects (budget in 5.5) |
| Pacing | While REC runs, the loop draws only when the 60 fps accumulator says a frame is due; each drawn frame calls `requestFrame()`. Measured: 58.41 fps from file timestamps at 2x (unpaced was 151 fps with 6 stutters) |
| Live view during REC | The recorded frames, at 60 fps, scaled by the browser into the unchanged CSS box (as HEAD always did) |
| Spectacle during REC | Identical to live: every effect is a function of the clock. The governor and the framing are frozen. The mode never changes on its own. `force()` refuses |
| Overlay in REC | Drawn at k = 1, byte-identical to HEAD's drawing plus the banner layer |
| Stop | Back to the adaptive buffer and the live composer, with no allocation |
| Snapshot | Always the REC pipeline, at the framing size, with no live-buffer change (C2) |
| First take | Encoder warm-up at boot idle (C2); recorder.js as the root-cause fallback |
| Audio | Unchanged (the audio input track, as HEAD) |

### 3.5 What phase 0 does not do

- **HDR:** the canvas stays 8-bit sRGB. The TikTok deliverable is SDR H.264; an HDR live view (a float16 canvas with
  extended tone mapping) is a separate decision.
- **The topbar wrapping at 1280-wide windows** (378x672 canvas) is layout, not resolution; out of scope.

### 3.6 Optional phase 0b: specular anti-aliasing on the keys

- The remaining shimmer sits on the glossy key bevels, where the eye rests.
- Widen roughness by the screen-space variance of the normal in the key materials (`onBeforeCompile`:
  `roughness = sqrt(roughness² + min(2σ², 0.18))` with `σ² = 0.25·(dot(dFdx(n),dFdx(n)) + dot(dFdy(n),dFdy(n)))`).
- Accept only if R0.3's key-crop edge shimmer falls by at least 20% and the wash check still matches.

---

## 4. Rarity

### 4.1 Tiers

| Tier | Ink (hairlines, gems) | Word colour | Gems | Φ at least | F at least | Extra gate |
|---|---|---|---|---|---|---|
| Common | none | none | 0 | | | |
| Uncommon | `#6FDC9A` (HUD, Tasteful chip only) | none (no banner) | 1 | 2.0 | | |
| Rare | `#79B8FF` | ivory `#F4F1EA` | 2 | 4.0 (+raise) | 2.0 | |
| Epic | `#C79BFF` | ivory | 3 | 5.25 (+raise) | 3.0 | |
| Legendary | `#FFC766` | gold foil gradient, top (1.00, 0.93, 0.70) to foot (0.93, 0.60, 0.20) | 4 | 6.75 (+raise) | 5.0 | novelty bonus ≥ 1.25, or F ≥ 7 |
| Mythic | each letter in a chord tone's own trail colour, `noteCss(m, 110)`, low to high | same | 5 | 8.0 (+raise) | 5.5 | "first time ever" (log source, ≥ 2,000 logged events); at most once per session |

- Tier ink appears only on the banner's 3 px hairlines and 5 px gems, never on keys, trails or scene light. Blue and
  violet are also pitch colours, so ink always travels with a word.
- Gold scene light appears only on Legendary and Mythic.

### 4.2 What counts as one event

**Committed chords only.**
- Rarity hooks the overlay's commit: the moment `overlay.shown` takes a new name.
- Eligible: `kind === "chord"`, not a power chord (`suffix "5"`), at least 3 pitch classes, detected over `harmonySet`.
  Notes, intervals, clusters and power chords never score.
- From MIDI input only. The Demo never scores. Computer keys score on screen but never write history.

**Dependency (phase 1): `Theory.harmonySet` does not exist in piano.js yet.**
- Promote it into the THEORY block from `piano/schemes/harmonic-wave.js`, with PIANO-V2-SPEC 6.1's three tests.
- `currentInfo()` detects over it.
- **Re-detect when a pedal-held note crosses the 1.5 s recency edge** (set `detectDirty` from a per-note timer); otherwise
  the label never notices the harmony thinning.
- Note for harmonySet's owner (not decided here): at 0.65 s a note, harmonySet ages early arpeggio notes out mid-bar, so
  the label shows thinner readings (the sim's committed names include `Cadd9/D`, `Bbadd9/C`). A tempo-aware recency
  (for example `max(1.5 s, 3 × median inter-onset interval)`, capped at 4 s) is worth testing.

**The bloom tracker (the spec's version).** `spec-calibration-lab/bloom-sim.mjs` models its boundaries, adaptive settle
and richest-reading choice; the passing-event return path below is not in that sim and gets its own node test (R1):

```js
// Called on every overlay commit with the committed info; tick() every frame.
// ctx: { pedalLifted (since the previous commit), lastOnT (newest note-on time), blockStrike }
//   blockStrike: 3+ note-ons within 80 ms whose newest is after the previous commit's newest note-on
function createBloomTracker({ settleMin = 0.4, settleMax = 1.0, maxLen = 8, restGap = 1.2 } = {}) {
  let bloom = null;
  return {
    commit(info, t, ctx, F /* intrinsic(info).F */) {
      const pcs = pitchClasses(info), bassPc = mod(info.notes[0].midi, 12);
      const joins = bloom && !ctx.pedalLifted && bassPc === bloom.bassPc && !ctx.blockStrike
                 && t - bloom.t0 <= maxLen && ctx.lastOnT - bloom.lastOnT <= restGap
                 && overlap(pcs, bloom.lastPcs) >= 2;            // a real change under a held pedal and bass splits
      if (joins) {
        const ioi = ctx.lastOnT - bloom.lastOnT;
        if (ioi > 0.02) bloom.ioi = ioi;
        Object.assign(bloom, { lastPcs: pcs, lastChange: t, lastOnT: ctx.lastOnT });
        if (F >= bloom.best.F) bloom.best = { info, F };         // the richest committed reading, latest on ties
        return null;
      }
      const ended = bloom && bloom.scoredBest !== bloom.best ? { ...bloom.best, passing: !bloom.scoredBest } : null;
      bloom = { t0: t, lastChange: t, lastPcs: pcs, bassPc, lastOnT: ctx.lastOnT, ioi: 0, best: { info, F }, scoredBest: null };
      return ended;                                               // an unscored bloom is scored now, as PASSING
    },
    tick(t) {
      if (!bloom) return null;
      const settle = Math.min(settleMax, Math.max(settleMin, 1.3 * bloom.ioi));
      if (t - bloom.lastChange < settle || bloom.scoredBest === bloom.best) return null;
      const upgradeOf = bloom.scoredBest;                         // non-null: the bloom grew after it was scored
      bloom.scoredBest = bloom.best;
      return { ...bloom.best, passing: false, upgradeOf };
    },
  };
}
```

Rules around it:
- **Passing events.** A bloom replaced before it settled is scored with `passing: true`. Its tier is logged and counted,
  but it is presented at most as the Uncommon sheen, and it never takes a banner or scene effect above Uncommon.
- **Upgrades replace, they do not add.** Session counts move from the old identity to the new one. The gate allows a
  banner only if the tier is strictly higher than the tier this bloom already presented. An on-screen banner updates in
  place with a 120 ms crossfade.
- **A pedal lift ends the bloom** (spec 6.2's one visible clearing).

Measured (`spec-calibration-lab/bloom-sim-output.txt`, 160 bars each, harmonySet and overlay settle modelled at 10 ms):

| Case | Expected events a bar | Design tracker: events / scorings a bar | Spec tracker (adaptive settle): events / scorings a bar |
|---|---|---|---|
| Pedalled arpeggio bars, 0.33 s a note (bar ~2.3 s) | 1 | 1.25 / 1.00 | **1.00 / 1.00** |
| Pedalled arpeggio bars, 0.50 s a note (bar ~3.4 s) | 1 | 3.23 / 4.50 | **1.00 / 2.00** |
| Pedalled arpeggio bars, 0.65 s a note (bar ~4.3 s) | 1 | 3.75 / 3.00 | **1.00 / 1.75** |
| Rolled chords (150 ms roll), re-pedalled | 1 | 1.00 / 1.00 | 1.00 / 1.00 |
| Block chords, re-pedalled | 1 | 1.00 / 1.00 | 1.00 / 1.00 |
| Pedal point F/C → Gm/C → C7 over a held low C, no lift | 3 | 3.00 / 3.00 | 3.00 / 3.00 |

Scorings above 1.0 at slow tempi are upgrades (for example F, then Fmaj9 as the bloom completes). They replace counts
and can only show a banner if the tier rises. With a fixed 0.4 s settle the same tracker scored 3.00 and 2.50 a bar.

### 4.3 The score

**Pure module `arsenal/web/piano/rarity.js`** (no DOM, no three.js), node-tested like THEORY. It starts from
`design-theory-rarity-lab/rarity.mjs`, with the merged changes marked `// MERGED`.

```js
export const RARITY_TABLE = "rarity/1";     // stored on every logged event; a retune is a new version

// C, chord colour by Theory.TEMPLATES suffix (a node test fails if any TEMPLATES suffix is missing here)
export const COLOUR = {
  "": 0, m: 0, sus2: 0.75, sus4: 0.75,
  "6": 1.25, add9: 1.25, "7": 1.25, m7: 1.25, dim: 1.25, m6: 1.5, "m(add9)": 1.5, "7sus4": 1.75, add11: 1.75,
  maj7: 2.0, aug: 2.0, m7b5: 2.25, "6/9": 2.25, dim7: 2.5, "m6/9": 2.5,
  "9": 2.75, m9: 2.75, maj9: 3.0, "9sus4": 3.0, "m(maj7)": 3.25, "11": 3.25, m11: 3.25,
  "13": 3.5, m13: 3.5, maj13: 3.75, "maj7#11": 4.0, "7#11": 4.0, "7b5": 4.0, "7#5": 4.0, "maj7#5": 4.25,
  "7b9": 4.5, "7#9": 4.5,
};

function bassScore(info) {                  // B: the bass, by the template's own letter steps
  if (!info.bass) return 0;
  const rel = mod(pcOf(info.bass) - pcOf(info.root), 12);
  const tone = TEMPLATES.filter((t) => t.suffix === info.suffix).flatMap((t) => t.tones).find(([s]) => s === rel);
  if (!tone) return 1.75;                   // foreign bass
  const steps = tone[1];
  if (steps === 2) return 0.75;             // 3rd in the bass
  if (steps === 4) return 0.5;              // 5th in the bass
  if (steps === 6 || (steps === 5 && info.suffix === "dim7")) return 1.25;  // 7th in the bass
  return 1.5;                               // a colour note in the bass
}

function voicingScore(notes) {              // V, capped at 1.0; deliberately small (Daniel plays wide by default)
  const span = notes.at(-1).midi - notes[0].midi, count = notes.length;
  let V = (span >= 24 ? 0.25 : 0) + (span >= 36 ? 0.25 : 0) + (count >= 6 ? 0.25 : 0) + (count >= 8 ? 0.25 : 0);
  if (count >= 3 && notes[1].midi - notes[0].midi >= 7) V += 0.15;
  return Math.min(V, 1.0);
}

function keyScore(info, pcs, key) {         // K, capped at 3.0
  const scale = (key.mode === "major" ? [0, 2, 4, 5, 7, 9, 11] : [0, 2, 3, 5, 7, 8, 10, 11]).map((s) => mod(key.tonic + s, 12));
  const outside = pcs.filter((pc) => !scale.includes(pc)).length;
  const nv = nashville(info, key, { minor: "tonic" });          // identity and K never depend on the display option
  return { K: Math.min(3, 0.75 * outside + (nv && !nv.diatonic ? 0.75 : 0)), outside, nv };
}

// ev: { info, keyView: { key, confidence, locked, candidate }, pedalBlendShare, pedalPoint }
export function intrinsic(ev) {
  const { info } = ev;
  if (!info || info.kind !== "chord" || info.suffix === "5" || distinctPcs(info) < 3) return { scorable: false, F: 0 };
  const pcs = distinctPcs(info);
  const C = COLOUR[info.suffix], B = bassScore(info), V = voicingScore(info.notes);
  let K = 0, nv = null, role = null;
  const kv = ev.keyView;
  const usable = kv.key && (kv.locked || kv.confidence !== "unsure");
  if (usable) {
    ({ K, nv } = keyScore(info, pcs, kv.key));
    if (kv.candidate && !kv.locked) K = Math.min(K, keyScore(info, pcs, parseKey(kv.candidate.name)).K);  // mid-modulation: the kinder key
    if (!kv.locked && kv.confidence === "fair") K *= 0.6;
    role = harmonicRole(info, pcs, kv.key, nv);             // section 2.3
  }
  const P = ev.pedalPoint ? 0.2 : 0;                         // MERGED: no velocity accent in fanciness
  let F = C + B + V + K + P, cap = null;
  if (ev.pedalBlendShare > 0.4) { F = Math.min(F, 2.0); cap = "pedal blend"; }    // a smear, not a chosen voicing
  if (info.cost >= 4.2)         { F = Math.min(F, 3.0); cap = cap || "uncertain reading"; }  // strained reading: at most Rare
  return { scorable: true, F, core: C + B + K, parts: { C, B, V, K, P }, nv, role, cap };
}
```

- `pedalPoint`: the bass is pedal-held (key up), struck more than 1.5 s ago, under at least 2 finger-held upper notes.
- `pedalBlendShare`: the share of the event's pitch classes that come only from pedal-held notes older than 0.8 s.

**Personal rarity** (unchanged from the design; `c` counts come from 4.5):

```js
// c = { Ns, ns1, ns2, lastSeenAgo, Nh, nh1, nh2, bandShare }
export function personal(c) {
  const w = Math.min(1, 600 / Math.max(c.Nh, 1));              // history counts as at most ~600 events of evidence
  const N = c.Ns + w * c.Nh;
  const blended = N >= 20 ? (0.7 * (c.ns1 + w * c.nh1) + 0.3 * (c.ns2 + w * c.nh2)) / N : 0;
  const tonight = c.Ns >= 20 ? (0.7 * c.ns1 + 0.3 * c.ns2) / c.Ns : 0;
  const share = Math.max(blended, tonight);                    // looping it now makes it home tonight
  const lifeShare = c.Nh > 0 ? c.nh2 / c.Nh : 0;
  const mature = c.source === "log" && c.Nh >= 2000;           // never from localStorage
  const firstSession = c.ns2 === 0, oftenForYou = mature && lifeShare >= 0.01;
  let bonus = 0, novelty = null;
  if (mature && c.nh2 === 0 && firstSession)                     { bonus = 2.0;  novelty = "first time ever"; }
  else if (mature && lifeShare < 1 / 500 && firstSession)        { bonus = 1.25; novelty = "rare for you"; }
  else if (!mature && c.Ns >= 150 && firstSession)               { bonus = 1.25; novelty = "first time tonight"; }
  else if (c.Ns >= 40 && firstSession && !oftenForYou)           { bonus = 0.75; novelty = "first this session"; }
  else if (!firstSession && c.lastSeenAgo >= 150 && !oftenForYou) { bonus = 0.4;  novelty = "back again"; }
  const h = Math.max(0.5, 1 - 0.45 * smoothstep(0.03, 0.12, share) - 0.25 * smoothstep(0.10, 0.30, c.bandShare));
  return { h, bonus, novelty, lifetimeFirst: novelty === "first time ever" };
}
```

**The tier:**

```js
export const TIERS = [
  { name: "Common",    phi: -Infinity, F: 0 },
  { name: "Uncommon",  phi: 2.0,  F: 0 },
  { name: "Rare",      phi: 4.0,  F: 2.0 },
  { name: "Epic",      phi: 5.25, F: 3.0 },
  { name: "Legendary", phi: 6.75, F: 5.0, personal: true },     // novelty bonus >= 1.25, unless F >= 7
  { name: "Mythic",    phi: 8.0,  F: 5.5, lifetimeFirst: true },
];
function tierOf(F, pers, raise) {
  const phi = F * pers.h + pers.bonus;
  let rank = 0;
  TIERS.forEach((t, i) => {
    if (i === 0) return;
    if (phi < t.phi + (t.phi >= 4.0 ? raise : 0) || F < t.F) return;
    if (t.personal && !(pers.bonus >= 1.25 || F >= 7)) return;
    if (t.lifetimeFirst && !pers.lifetimeFirst) return;
    rank = i;
  });
  return { rank, phi };
}
export function scoreTier(F, pers, raise = 0) {                  // MERGED: the novelty lift cap
  const withN = tierOf(F, pers, raise);
  const base = tierOf(F, { ...pers, bonus: 0, novelty: null, lifetimeFirst: false }, raise);
  let rank = Math.min(withN.rank, base.rank + 1);
  if (pers.novelty === "first time ever" && withN.rank >= 4 && withN.rank <= base.rank + 2) rank = withN.rank;
  return { rank, tier: TIERS[rank].name, phi: withN.phi, liftedByNovelty: rank > base.rank };
}
```

If `liftedByNovelty`, the novelty reason is the first reason on the banner, always.

**Intensity (effect size, never tier):**

```js
// running velocity distribution of Daniel's strikes over the last 120 s (min 20 samples; defaults p10 40, p90 100)
I = 0.6 + 0.4 * smoothstep(p10, p90, event.peakVelocity);
// the arc (from vfx): this event is the 3rd or later in a run where each event's peak velocity is >= the previous + 4,
// all within 12 s, ending at >= 105
if (arc) I = 1.0;
```

I multiplies:
- rail pulse gain;
- ring gains;
- fountain count;
- shaft gain;
- shimmer gain;
- hem gain;
- camera push.

It does not scale:
- the banner, the foil or the sheen (text is information);
- house lights (they pay for light, and shrinking them would only add light).

### 4.4 Banner gate, cooldowns and target frequencies

```js
function createRarityGate() {
  const COOL = { Rare: 12, Epic: 30, Legendary: 120 };  // s since the last banner of THIS tier or higher
  // A scored event gets a banner only if ALL hold:
  //   - tier >= Rare, not passing, and spectacle mode is Full (Tasteful uses the chip, section 5.3)
  //   - >= 6 s since the previous banner ended its hold (one banner at a time, never stacked)
  //   - the tier cooldown
  //   - Legendary: >= 45 s since the session's first scored event (warm-up)
  //   - Mythic: none shown yet this session
  //   - per identity id2: >= 90 s since its last banner, and < 3 banners this session
  //   - an upgrade: its tier is strictly higher than the tier its bloom already presented
  // A blocked Rare+ event falls back to the Uncommon look (sheen). It is still logged and counted.
  // Inflation guard: count Rare+ scored events in the last 300 s; above 15, Rare+ Φ floors rise by
  //   0.25 per 5 extra, capped at +0.75 ("strict +0.5" in the HUD). It can only tighten.
}
```

There is deliberately no showcase or recording multiplier. What is recorded is what he played.

**Target frequencies and what the merged rules measure** (`spec-calibration-lab/merged-sim-output.txt`; synthetic style
mix 58% F/A-C/G-Dm-Bbmaj7 loop, 22% everyday colour, 12% lush, 6% borrowed, 2% altered; one event every ~2 s):

| Scenario (10 min) | Common | Uncommon | Rare | Epic | Legendary | Mythic | Banners R / E / L / M |
|---|---|---|---|---|---|---|---|
| A′ Daniel style, first session, no log | 84.2% | 7.1% | 7.7% | 1.0% | 0% | 0% | 14 / 2 / 0 / 0 |
| B′ Daniel style, 10th session (2,727 events of history) | 81.0% | 9.8% | 6.9% | 2.0% | 0.3% | 0% | 10 / 4 / 1 / 0 |
| G′ B′ over 20 seeds | | | | | | | **10.8 (6-16) / 2.9 (1-5) / 1.5 (0-3) / 0** |
| C′ Plain triad loop F C Dm Bb | 100% | 0 | 0 | 0 | 0 | 0 | 0 / 0 / 0 / 0 |
| D′ Explorer mix, with history | 48.5% | 34.9% | 11.0% | 4.3% | 1.3% | 0% | 17 / 5 / 1 / 0 |
| E′ Explorer mix, no history | 47.7% | 40.1% | 7.0% | 5.0% | 0.3% | 0% | 10 / 9 / 0 / 0 |

- Rail pulses a minute (home-chord suppression, 5.2): 8.6 (6.7-9.8) for G′, against 30 events a minute; 0.5 on the triad loop.
- The novelty cap never bound in these sims (the vocabulary is closed); it is a guard for real new vocabulary.
- Mythic is 0 by construction in closed vocabulary.

| Tier | Target share of events | Banners per 10 min (Daniel style) | On a 60 s TikTok |
|---|---|---|---|
| Common | ~80% | none | |
| Uncommon | ~10% | none (sheen only) | several sheens |
| Rare | ~7% | ~10 (about one a minute) | usually one |
| Epic | ~2% | 2-3 | sometimes one |
| Legendary | ~0.3-0.5% | 1-2; 0 while looping; none in the first 45 s | a lucky clip |
| Mythic | new vocabulary only | ≤ 1 a session; expected a few a month once the log has ≥ 2,000 events | the clip he posts |

**Every number here is synthetic.** Phase 4 replays Daniel's first three real logged sessions and re-reads the table
before `rarity/1` is frozen.

### 4.5 Personal rarity from the practice log

**Identity.**
- `id1` = the key-relative Nashville text with its bass ("4maj7/3"); `id2` = without the bass ("4maj7").
- Always computed with `nashville(info, key, { minor: "tonic" })`, so the Minor display setting cannot fork identities.
- Without a usable key: `name:Dm9/Bb`, counted separately and never mixed with numbers.
- Novelty reads `id2`: a new inversion of an old chord is not "new".

**Counts.**
- `Ns, ns1, ns2, lastSeenAgo`: in memory, this page session, scored events only (upgrades move counts).
- `Nh, nh1, nh2, bandShare`: from the vocabulary.
- `source`: "log" | "local" | "none".

**Order of operations (cross-build hazard).** `performance.py` rejects unknown event kinds with a 400 and drops the whole
batch (`KINDS = ("on", "off", "pedal", "chord", "sound_end")` today).

1. The log lane adds `"rarity"` to `KINDS`, with validation for the fields below, and restarts the server.
2. The log lane adds `GET /api/performance/vocabulary`.
3. Only then does the client send `rarity` events. The client feature-detects step 2 (a GET, like `hasLogRoutes()`), and
   sends nothing of kind `rarity` without it.

**Event** (sent through `perfLog`, behind the existing `logged()` guard, so the demo never writes one):

```json
{ "t_ms": 761200, "kind": "rarity", "table": "rarity/1",
  "id1": "6m9/4", "id2": "6m9", "name": "Dm9/Bb", "key": "F major", "key_conf": "sure", "locked": false,
  "core": 4.5, "F": 4.9, "h": 0.98, "bonus": 0.75, "phi": 5.55, "tier": "Epic", "novelty": "first this session",
  "reasons": ["first this session", "rich extension", "foreign bass"],
  "passing": false, "banner": true, "upgrade_of": null }
```

`upgrade_of` is the `t_ms` of the event this one replaces; the analyzer moves its counts.

**Vocabulary route** (recomputed at session close from `rarity` events, cached at
`state/arsenal/performance/vocabulary.json`):

```json
{ "api": "arsenal.performance.vocabulary/v0", "table": "rarity/1", "events": 5123, "sessions": 17,
  "by_id2": { "4maj7": 812, "6m9": 51 }, "by_id1": { "4maj7/3": 40 }, "by_name_nokey": { "Dm9/Bb": 3 },
  "by_suffix": { "m11": 17 }, "core_hist": { "bucket": 0.25, "counts": [] },
  "first_seen": { "4maj7#11": "20260914-201502-1a2b3c4d" }, "updated_at": "..." }
```

**Before the route exists:**
- The client keeps `localStorage arsenal.piano.rarity.v1` (same shape, try/catch, capped at 200 identities) with
  `source: "local"`.
- It feeds familiarity and "first this session" / "back again" / "first time tonight" only.
- "rare for you", "first time ever" and Mythic are off until `source: "log"` and `events ≥ 2000`.
- Legacy `chord` events are label changes, not bloom-merged events, so they never count toward `Nh`.

**Privacy:** everything stays under `state/arsenal/` on this machine.

### 4.6 Examples in F major

Merged rule, real `Theory.detect` names and Nashville numbers (`spec-calibration-lab/merged-examples-output.md`).

Context columns:
- **start:** the first chords of a session, no log;
- **home:** 15% of everything he plays;
- **occ.:** 0.5% of his history, first this session;
- **rare:** 0.1% of his history, first this session;
- **first:** never in 5,000 logged events.

| Chord (voicing) | Number | F | start | home | occ. | rare | first | Reasons (at most two) |
|---|---|---|---|---|---|---|---|---|
| F/A | 1/3 | 1.15 | Common | Common | Common | Uncommon | Uncommon | |
| C/G | 5/2 | 0.90 | Common | Common | Common | Uncommon | Uncommon | |
| Dm | 6m | 0.15 | Common | Common | Common | Common | Uncommon | |
| Gm7 / C7 / Am7 | 2m7 / 5⁷ / 3m7 | 1.40 | Common | Common | Uncommon | Uncommon | Uncommon | |
| Eb | ♭7 | 1.50 | Common | Common | Uncommon | Uncommon | Uncommon | borrowed from F minor |
| Bbm | 4m | 1.65 | Common | Common | Uncommon | Uncommon | Uncommon | borrowed from F minor |
| Bb/C | 4/5 | 1.90 | Common | Common | Uncommon | Uncommon | Uncommon | foreign bass |
| Bbmaj7 / Fmaj7 | 4maj7 / 1maj7 | 2.15 | Uncommon | Common | Uncommon | Uncommon | Rare | seventh colour |
| Dm9 | 6m9 | 2.90 | Uncommon | Common | Uncommon | Rare | Rare | rich extension |
| A7 | 3⁷ | 2.90 | Uncommon | Common | Uncommon | Rare | Rare | secondary dominant (leads to Dm) |
| Fmaj7/E | 1maj7/7 | 3.40 | Uncommon | Common | Rare | Rare | Rare* | seventh colour · 7th in the bass |
| C13 | 5¹³ | 3.65 | Uncommon | Uncommon | Rare | Rare | Rare* | rich extension |
| Gm7b5 | 2ø7 | 3.90 | Uncommon | Uncommon | Rare | Rare | Rare* | borrowed from F minor · seventh colour |
| Fmaj9, spread over 3+ octaves | 1maj9 | 4.00 | Rare | Uncommon | Rare | Epic | Epic | rich extension · wide voicing |
| Bbmaj7#11 | 4maj7♯11 | 4.15 | Rare | Uncommon | Rare | Epic | Epic | sharp eleven |
| Dbmaj7 / Abmaj7 | ♭6maj7 / ♭3maj7 | 4.40 | Rare | Uncommon | Rare | Epic | Epic | borrowed from F minor · seventh colour |
| Gbmaj7 (Neapolitan) | ♭2maj7 | 4.40 | Rare | Uncommon | Rare | Epic | Epic | far outside the key · seventh colour |
| Dm9/Bb (his Bb F A C D E) | 6m9/4 | 4.90 | Rare | Uncommon | Epic | Epic | Epic | rich extension · foreign bass |
| C7b9 | 5⁷♭⁹ | 5.40 | Epic | Uncommon | Epic | Epic | Legendary | altered dominant · altered tension |
| C7#5 | 5⁷♯⁵ | 5.50 | Epic | Uncommon | Epic | Legendary | Legendary | outside the key · altered fifth |
| Emaj7/G# | 7maj7/♯2 | 6.15 | Epic | Uncommon | Epic | Legendary | Mythic | far outside the key · seventh colour |
| A7b9 / E7#9 | 3⁷♭⁹ / 7⁷♯⁹ | 6.40 | Epic | Uncommon | Epic | Legendary | Mythic | secondary dominant (leads to Dm / Am) · altered dominant |
| B7#11 (tritone away) | ♯4⁷♯¹¹ | 7.15 | Legendary | Uncommon | Legendary | Legendary | Mythic | far outside the key · sharp eleven |

- `*` marks a cell that changed from the design's table (Epic to Rare) under the novelty cap.
- When novelty lifted the tier, it replaces the second reason, for example `rare for you · altered dominant`.
- The brief's sketch "EPIC · Bbmaj9#11 · b7" is wrong twice. In F a Bb-rooted chord is 4, not ♭7. And the overlay names
  Bb F A C D E as `Dm9/Bb` (TEMPLATES has no maj9#11). The banner shows the overlay's name:
  `RARE · Dm9/Bb · 6m⁹/4` / `rich extension · foreign bass`.

---

## 5. Spectacle

### 5.1 Principles every effect obeys

1. **Contrast is the spectacle; light is a budget.** Epic and Legendary dim old columns through the existing budget
   damping (fast dim 0.05 s, slow recovery 1.5 s). Fresh strikes, held keys and column feet keep full price.
2. **Use the empty stage first:** the floor below the keys, the rail line, the back wall behind the columns. The sky
   between the rail and the staff is shared. The chord name, the Nashville row / banner slot and the staff are protected.
3. **Colour belongs to the chord.** Every effect takes the chord's pitch colours (low to high, `noteColor`). Tier is scale,
   motion and count. Gold is the only non-pitch light and means Legendary (and Mythic, which contains Legendary).
4. **Only thin crests cross the bloom threshold** (0.9 linear): ring crests, spark cores, the rail's core. Bodies stay
   under it: ring body x0.32, shaft bodies ≤ 0.3 linear, hem glow ≤ 0.35.
5. **Protect by shape.** A super-ellipse mask with a 6-9% feather limits effect light:
   - ≤ 12% at the heart of the chord name;
   - ≤ 35% under the banner plate;
   - ≤ 45% inside the staff;
   - 100% elsewhere.

   A rectangular stencil showed as a dark box in vfx round 1.
6. **Clock-driven.** Every envelope is a function of `clock()` seconds (the lab's `clockOverride` works), never of frame
   counts.
7. **Nothing thin enough to alias:**
   - ring widths `we = max(w, 2·fwidth(d))` with energy kept (x w/we);
   - beam widths `+ 0.7·fwidth(angle)`;
   - points at least 2.5 output px (= 2.5 x `RES.internal.h / RES.output.h` scene px), with alpha x covered area;
   - twinkle < 2 Hz;
   - `uRes` from the active composer's read buffer.
8. **Effects scale with what they touch:** the shimmer's gain x `min(1, 8 / columns under the chord)`.
9. **Never:** a full-screen flash or fade, screen shake, whole-frame chromatic aberration, a camera move that crops a
   sounding key, anything over the key fronts, tier ink as scene light, a strobe, light added on a pedal lift.
10. **A pedal lift during a treatment** fades that treatment's scene parts over 0.3 s (the one visible clearing). Its text
    finishes.
11. **Spectacle Off is byte-identical to today.**

### 5.2 The ladder (Full mode)

Times are from the trigger: the moment the gate presents the event (its settle).

| Tier | Adds (each tier keeps everything below it) | Visible for |
|---|---|---|
| **Common** | E1 rail fronts, one pair, gain 0.45 x I. **Skipped when h < 0.75** (a home chord) or the event is passing | 0.6-1.0 s |
| **Uncommon** (also the fallback for a blocked or passing Rare+) | E1 two pairs (echo +0.12 s) at 0.8; E2 ember lift (90 sparks); E13 name sheen (350 ms) | ~1.9 s |
| **Rare** | E1 at 1.0; E3 ring 1 (R 26 u, 1.7 s); E4 fountain 300; E5 column shimmer; E6 banner (hold 1.8 s) | ~2.6 s |
| **Epic** | E1 at 1.1; E3 ring 2 (+0.18 s, R 32, 1.9 s); E7 seven-shaft fan (0.9); E9 house lights −15%; E4 fountain 520; banner hold 2.6 s | ~3.3 s |
| **Legendary** | **Gold.** E11 foil chord name with sheen; E12 gold rail; E1 at 1.25 with a third echo (+0.26 s); ring 1 gold at 1.35; ring 3 thin gold (+0.36 s, R 38, 2.2 s); E4 fountain 600 (55% gold); E7 shafts 1.2 with a gold centre beam and 55% gold side beams; E5 two shimmer bands, gold tint; E10 gold hem ribbon; E9 house lights −35%; E8 camera push 3%; banner with a letter-by-letter reveal, hold 3.4 s | ~5.2 s |
| **Mythic** | Everything Legendary has; E10 hem in the chord's pitch colours drifting along the hem, instead of gold; tier word letters in the chord tones' colours; banner line 2 begins `FIRST TIME EVER`; hold 4.0 s | ~5.5 s |

**Legendary timeline:**

```
0.00  gold rail on (0.1 s); rail fronts x3 (+0.12, +0.26); ring 1 gold; fountain 600 over 0.55 s
      house lights begin to dim (0.25 s to -35%); camera push begins (1.0 s ease)
0.03  shimmer band leaves the rail (3.2x trail speed); second band at +0.45 s
0.05  shafts shoot up at 42 u/s; banner in (0.14 s), letters revealed 60 ms apart
0.10  foil in on the chord name (0.18 s); hem ribbon fades in (0.9 s)
0.18  ring 2          0.20-1.20  foil sheen sweeps left to right          0.36  ring 3 (thin gold)
1.00  camera at full push, holds 0.6 s
1.70  shafts start to fade (out by 3.3)       1.80  gold rail fades (1.4 s)
1.60  camera starts home (1.8 s smoothstep, home at 3.40)
2.45  house lights recover (1.2 s, then the budget's own 1.5 s)
3.18  foil out (0.8 s)      3.20  hem starts out (gone by 5.2)      3.59  banner out (0.5 s; in 0.05-0.19, hold 3.4)
5.20  everything idle
```

### 5.3 Modes

| | Off | Tasteful | Full |
|---|---|---|---|
| Scoring, HUD line, practice-log `rarity` events | yes | yes | yes |
| Common rail pulse | | | yes (home chords skipped) |
| Uncommon | | E13 sheen | E1 x2, E2, E13 |
| Rare | | E1 at 0.8, ring 1 at 0.7, **chip** (one-line compact banner, hold 1.6 s) | full Rare |
| Epic | | + shafts at 0.6, house lights −15%, chip hold 2.2 s | full Epic |
| Legendary | | + E11 foil name, E12 gold rail, ring 3 gold, house lights −25%, chip hold 3.0 s | full Legendary |
| Mythic | | + chip tier word in chord colours, `FIRST TIME EVER` | full Mythic |
| Fountain, ember, shimmer, hem, camera push, phrase card | | none | yes |
| Scene draw calls added at peak | 0 | ≤ 3 | ≤ 5 |

**Settings:**
- **Storage:** `localStorage arsenal.piano.spectacle` = `"off" | "tasteful" | "full"`. Default `"full"`; open question Q3.
  Read and write through the existing `safeGet` / `safeSet`.
- **Top bar:** `<label class="field" for="spectacle-select">Spectacle <select id="spectacle-select">` with Off /
  Tasteful / Full, in the same pattern as the other build's `nns-select`; `blur()` after change.
- **Hotkey:** **Backquote** (`` ` ``) cycles Off → Tasteful → Full. H and F are taken, and the letters Z S X D C V G B N
  J M L Q W E R T Y U I O P plus Digit 2 3 5 6 7 9 0 are computer-key notes.
- **Query override for receipts:** `?spectacle=off|tasteful|full` (not persisted).
- **REC never changes the mode.**

### 5.4 Effects catalogue (constants)

| ID | Effect | Tiers | Object | Blend | Pass | Depth test | Draws | Share of the 9:16 frame while alive |
|---|---|---|---|---|---|---|---|---|
| E1 | Rail fronts | Common+ | 58 x 1.4 u quad at the rail (z −3.26) | additive | main, before bloom | yes | 1 | ~1% |
| E2 | Ember lift | Uncommon | the E4 points system | additive | main | yes | shared | small |
| E3 | Floor shockwave rings | Rare+ | 260 x 260 u plane at y −2.27 | additive | main | yes (the piano occludes the middle) | 1 | 25-30% |
| E4 | Spark fountain | Rare+ | Points, cap 2000 | additive | main | yes | 1 | column feet |
| E5 | Column shimmer | Rare+ | the trail shader (scheme hook) | as the trails | main | as the trails | 0 | the chord's columns |
| E6 | Banner / chip | Rare+ | Canvas2D layer via `makeLayer()` | alpha | overlay, after OutputPass | no | 1 | the banner slot |
| E7 | Light shafts | Epic+ | 70 x 40 u quad behind the columns (z TRAIL_Z − 0.7) | additive | main | yes | 1 | ~35% |
| E8 | Camera push | Legendary+ | follow-camera offsets | | | | 0 | |
| E9 | House lights | Epic+ | multiplies the light-budget density target | | | | 0 | |
| E10 | Hem ribbon | Legendary+ | 150 x 60 u plane at z −30, hem only | additive | main | yes (the floor hides its foot) | 1 | ~15% (hem band) |
| E11 | Foil chord name | Legendary+ | mesh sampling the label's own texture | alpha | overlay | no | 1 | the label glyphs |
| E12 | Gold rail | Legendary+ | uniforms of E1 | as E1 | | | 0 | |
| E13 | Name sheen | Uncommon+ | the E11 mesh with an ivory palette | alpha | overlay | no | (shared) | the label glyphs |

**E1 rail fronts:**
- Six slots `(cx, t0, speed, gain, paletteRow)`; speed 36-44 u/s.
- Head gaussian σ 0.42 u; wake 18%; decay τ 0.55 s; life ≤ 1.8 s.
- Vertical profile: core σ 0.042 u plus a 22% halo `e^(−6|dy|)`.
- Colour maps the palette along the chord's own x span (each stretch lit in the colour of the key below).
- Fades at |x| 25.6-26.6. Never lights key tops.

**E2 ember lift:** 90 sparks split across the chord's notes; up 1.8-4 u/s; life 1.0-1.9 s.

**E3 rings:**
- Radius `R·(1 − e^(−age/0.5))`; width `w₀·(0.35 + 1.2·age/dur)`; sharp outer front (gaussian at 0.3·w), exponential inner
  wake, a hot crest line; life `(1 − age/dur)²`; body x0.32.
- The palette wheels twice around the angle, drifting 1.5 steps/s.
- Fades by camera distance 55-130 u (the ShaderMaterial has no scene fog).

| Ring | When | R (u) | Duration | w₀ | Gain | Colour |
|---|---|---|---|---|---|---|
| 1 | Rare+, t0 | 26 | 1.7 s | 0.55 | 1.0 (Legendary 1.35) | palette; gold on Legendary |
| 2 | Epic+, t0 + 0.18 s | 32 | 1.9 s | 0.80 | 0.7 | palette |
| 3 | Legendary+, t0 + 0.36 s | 38 | 2.2 s | 0.35 | 0.6 | thin gold |

**E4 fountain:**
- Counts: Rare 300 over 0.35 s; Epic 520; Legendary 600 over 0.55 s, 55% gold.
- Motion: up 9 / 10 / 11 u/s x (0.45-1.0); gravity 8.4 u/s²; life 1.0-2.3 s; size 0.14-0.40 u.
- Spawns at z −3.22, behind the key backs.
- Upload with `BufferAttribute.updateRanges`, one range per trigger.

**E5 shimmer** (Neon Trails' `spectacle()` hook):
- Band at 3.2x trail speed; σ 0.8 u + 0.5 u/s; colour lifted 15% toward white.
- Gain = stretch energy x 1.6 (clamped to 1) x `min(1, 8 / columns under the chord)`.
- Legendary: a second band at +0.45 s with a gold tint. No dispersion fringe.
- One uniform branch in the trail fragment shader, active ≤ 2.6 s.

**E6 banner / chip:** section 5.6.

**E7 shafts:**
- Seven angular gaussians across ±0.51 rad, width 0.03-0.06 rad + 0.7·fwidth(angle); sway at incommensurate phases.
- Radial `e^(−r/15)`, faded in at r 0.4-2.2 (no hot origin); moving motes 0.8-1.0.
- Front 42 u/s; envelope in 0.3 s, hold to 1.7 s, out by 3.3 s.
- Gain Epic 0.9, Legendary 1.2, x I.

**E8 camera push:**
- Legendary: distance x (1 − 0.03·I), elevation +0.012 rad, yaw 0; rise 1.0 s, hold 0.6 s, return 1.8 s (smoothstep).
- 16:9: push x 0.6.
- Skipped when the follow camera's target moves faster than 1.5 u/s.
- Never reduces the follow margin below 2 u around the sounding span.

**E9 house lights:**
- `densityTarget *= dim`, with `dim = 1 − 0.15·bumpEpic − 0.35·bumpLegendary` (Tasteful Legendary: 0.25).
- bumpEpic: rise 0.25 s, hold 1.8 s, fall 1.0 s. bumpLegendary: rise 0.25 s, hold 2.2 s, fall 1.2 s.
- Key glow does not read `uDensity`, so the sustain brightness rule on keys is untouched by construction (receipt R4).

**E10 hem ribbon:**
- Hem height = three sines (spatial 0.09 / 0.23 / 0.57, temporal 0.31 / 0.53 / 0.97), waving just above the rail.
- Glow below the hem line `e^(−h/1.2)`; **no curtain above**.
- Envelope in 0.9 s, hold to 3.2 s, out by 5.2 s.
- Gold-leaning palette on Legendary; the chord's pitch colours on Mythic.

**E11 foil name:**
- Samples the label canvas: glyph cores only (alpha ≥ 0.78), main line only (uv above the note chips).
- Vertical gradient (1.00, 0.93, 0.70) → (0.93, 0.60, 0.20); diagonal sheen 0.2 → 1.2 s.
- Timing: in 0.18 s, hold 2.9 s, out 0.8 s. Never changes glyph shape or position.

**E12 gold rail:** holds gold at 0.9 for 1.7 s, fades over 1.4 s; pulse heads ride over it.

**E13 sheen:** the E11 mesh with an ivory highlight at 35% alpha, clipped to glyph alpha (loot M3), 350 ms.

**Per-slot palettes.**
- A 8 x 8 RGBA `DataTexture`: each row holds the colours of one trigger, low to high.
- Effect slots carry a row index, so a second trigger never recolours rings in flight.
- Palette blends happen in OKLab in the shader (linear sRGB → OKLab → mix → back), never in RGB.

**Per-scheme blend policy.** Ask the active scheme `blendPolicy()` → `"additive"` (Neon Trails, today's piano.js) or
`"strict"`. Under strict (Upright Roll, PIANO-V2-SPEC 6.2):
- rings and shafts become normal-blend hairlines;
- the hem becomes a normal-blend line;
- the fountain and shimmer are off;
- text effects are unchanged.

**Precompile.**
- At boot, after the scene is built: set every effect mesh `visible = true` with zero gains, then
  `await renderer.compileAsync(scene, camera)` and `compileAsync(overlayScene, overlayCam)`.
- Render one frame through the REC pipeline at idle, then hide the meshes.
- Every effect mesh stays invisible whenever it cannot be lit, so an idle frame pays nothing.

### 5.5 Budgets

| Budget | Limit | Measured so far |
|---|---|---|
| Mean luma during a Legendary vs the same frame with spectacle Off | ≤ +0.06 | vfx v2: +0.059 at the peak (0.138 → 0.197), 1x pipeline |
| Near-white share (min channel > 0.85) | ≤ the Off frame's + 0.0005 | vfx v2: fell from 0.0084 to 0.0013-0.0054 |
| Staff box mean luma | ≤ 0.35 (spec hard limit 0.6) | vfx v2: 0.229 peak; dense wash + Legendary 0.291-0.305 |
| Chord-name band, non-text pixels | ≤ Off + 0.035 | vfx v2: 0.042 → 0.058 |
| Dense wash (40 notes in 4 s, pedal down) + Legendary | luma ≤ +30% vs Off; no row in y 150-1370 with white share > 0.05 | vfx v2: +29% (v1 +62% with a white bar) |
| GPU, REC pipeline (2160x3840 MSAA 4 scene), Full, stacked Legendary + Epic + Rare over a dense wash | Δmedian ≤ 1.0 ms, Δp95 ≤ 1.5 ms over Off | not measured at 2x: vfx measured +0.2-0.3 ms at 1x; the large additive quads pay about 4x fill at 2x (judge 2) |
| GPU, 1x 1080x1920 | Δp95 ≤ 0.3 ms | vfx v1: idle 1.165, Legendary 1.378, stacked 1.463 ms |
| First trigger after boot | frame ≤ steady p95 + 2 ms (no compile hitch) | requires the precompile |
| Draw calls at peak | scene +5, overlay +2 (banner, foil) | vfx: 5 + 2 |
| Canvas2D redraws | banner/chip only on a present or upgrade, at most 1 per 60 ms of letter reveal | |
| CPU per frame | tracker tick + gate O(1); scoring O(notes) per commit; fountain upload once per trigger | |
| VRAM | effects: forward-rendered, no targets; REC pipeline ~600 MB (3.3) | |

### 5.6 Placement

All overlay coordinates are **reference pixels** (1080x1920 or 1920x1080). Layers are created through `makeLayer()` and
drawn under `ctx.setTransform(sx, 0, 0, sy, 0, 0)`, with `shadowBlur` x `shadowScale`. Scene effects are world-space and
follow the camera.

**9:16 map** (existing elements measured from HEAD `LAYOUT`, the other build's working copy, and loot's layout map
`mockups/loot-e-layout-map.png`):

| Element | Box (reference px) | Notes |
|---|---|---|
| TikTok header | y 0-150 | never text |
| TikTok button column | x ≥ 916, y 800-1596 | covers the staff's right barline (pre-existing) |
| TikTok caption band | y ≥ 1596 | garnish only (the floor ring's front arc lives here) |
| Chord label layer | x 10-1070, y 148-488; glyphs ≈ y 205-365 | sacred: never moved, covered, delayed |
| Note chips | y 392-436 | |
| **Nashville row (other build)** | layer x 10-1070, y 471-601; `size 76`, baseline ≈ y 552 | re-read after that build lands |
| Staff layer | x 110-970, y 500-1100; lines y 620-980; G clef top ≈ y 586 | ledger notes and accidentals above the staff reached y ≈ 540 in `hook-v2/wash-1-leg+0.8s.jpg` |
| Pedal mark | x 177-345, y 990-1086 | |
| Rail / keys | rail y ≈ 1370; keys y 1370-1590 | |
| **Banner, two-line form** | plate x centred, width = content + 64 (max 860, inside x 110-970), **y 478-576**, radius 18, `rgba(8, 8, 12, 0.72)` | line 1 baseline y 524; line 2 baseline y 564; 10 px clear of the clef top |
| **Banner, compact one-line form** | plate y 486-536; baseline y 520 | used when the staff's ink top < 580, in Tasteful (the chip), and for the phrase card's second line if it overflows |
| E1 rail fronts | along the rail, y ≈ 1360-1380 | |
| E3 rings | front arc y ≈ 1600-1850; back arc rises behind the rail, y ≈ 1250-1370 | `hook-v2/rare-1`, `rare-2`, `leg-1` |
| E4 fountain | column feet, y ≈ 1170-1370 | |
| E7 shafts | from the rail up to ≈ y 700, faded by the staff protect mask | |
| E10 hem ribbon | y ≈ 950-1150, behind the columns | |

**Banner typography.**
- **Line 1:**
  - gems (5 px diamonds in tier ink, 1-5 as the tier column);
  - the tier word (Archivo 700, 38 px, caps, letter-spacing 0.32 em, ivory, or gold foil for Legendary, or chord colours
    for Mythic), with 3 px tier-ink hairlines fading outward from its flanks;
  - `·`, then the chord name drawn with the label's own `nameRuns` / `suffixRuns` at 38 px;
  - `·`, then the Nashville number with the other build's `numberRuns` at 38 px, only when the key is locked, "sure" or
    "fair".
- **Line 2:** at most two reasons (2.3), 24 px, caps, letter-spacing 0.08 em, `rgba(244, 241, 234, 0.62)`, joined by ` · `.
- **Overflow order:** drop the number, then shrink to 34 px, then keep one reason. A novelty reason that lifted the tier
  is never dropped.
- **Timing:** in 0.14 s (scale-x 0.94 → 1.0 over 0.35 s); hold per tier; out 0.5 s.
- **The Nashville row** fades to 0 over 120 ms before the banner fades in, and back over 250 ms after it fades out. When
  the row is Off or has no key, nothing crossfades.
- **Staff ink top:** `drawStaff` records `layer.inkTop` (reference y of the topmost drawn glyph: ledger lines,
  accidentals, noteheads, clefs) so the banner can choose its form.

**16:9 map:**

| Element | Box (reference px) |
|---|---|
| Chord label | x 50-950, y 41-351, left-aligned |
| Nashville row (other build) | layer x 50-950, y 332-452, `size 64`, baseline ≈ y 406, text from x 80 |
| Staff | x 1240-1880, y 12-532 |
| **Banner** | plate x 60 to content + 60 (max 880), **y 344-440**; line 1 baseline y 384 (34 px); line 2 baseline y 424 (22 px); left-aligned at x 80 |
| Scene effects | as 9:16 in world space; camera push x 0.6 |

There are no TikTok zones in 16:9. A 5% title-safe margin is kept.

**The phrase card (the reveal in the rest), Full only:**
- **A phrase** is the run of scored events between rests. A rest is 1.2 s with nothing sounding, or 3.0 s with no
  note-on while only pedal-held notes ring.
- **Grade:** the highest tier among the phrase's settled (non-passing) events. Lift it one tier (to at most Epic) when
  the phrase has ≥ 6 settled events and ≥ 60% of its changes are **smooth**: at least 2 pitch classes in common, and the
  top voice moves ≤ 2 semitones.
- **Shown when** the grade is ≥ Epic, the phrase has ≥ 4 settled events, no banner is on screen, and no card appeared in
  the last 60 s.
- **Where:** the banner slot. The label sits at 0.62 alpha in a rest (existing overlay behaviour).
- **Text:**
  - line 1 `PHRASE · EPIC`, with gems and hairlines;
  - line 2 facts only, at most three: `{n} chords · {k} outside the key · smooth voice leading`. `{k}` counts events with
    a key reason. "smooth voice leading" appears only when ≥ 60% of the changes were smooth.
- **Timing:** in 0.2 s, hold 2.2 s, out 0.6 s. A note-on fades it out over 0.25 s. It never enters history.

**Meter and discovery UI.**
- **Meter:** no in-canvas meter, gauge or combo (cut by both judges). The HUD, which is not recorded, gets one line:
  `rarity 10R 3E 1L 0M · strict +0 · log 5,123 · last EPIC A7b9 (outside the key, first this session) · spectacle full`.
- **Discovery:** in phase 5 only, section 6, P5.

### 5.7 Integration points in piano.js (after the other build lands)

- **New modules:** `arsenal/web/piano/rarity.js` (pure) and `arsenal/web/piano/spectacle.js` (the director).
- **`spectacle.js`** exports
  `createSpectacle({ THREE, scene, overlayScene, camera, renderer, clock, keyX, noteColor, noteCss, trailUniforms, RES,
  LAYOUT, makeLayer, nameRuns, suffixRuns, numberRuns })`, which returns:
  - `present(event)`: from the gate `{ tier, presentTier, banner, chip, info, number, reasons, notes, intensity, t }`;
  - `update(dt, t, frame)`: before `composer.render`;
  - `cameraOffset()` → `{ push, elev }`;
  - `densityMultiplier()` → `dim`;
  - `nnsCover()` → 0..1, which the overlay multiplies into the Nashville row's opacity;
  - `setMode(mode)`, `resize(framing)`, `layout()` (rectangles for R7), `stats()`, `precompile()`, `dispose()`;
  - `force(tier, opts)`: lab only.
- **Engine:** `noteOn` pushes its time into a 16-entry ring buffer (for `blockStrike`). `overlay.update` calls
  `onCommit(shown, t, { grew })` when `shown` changes.
- **`renderFrame`**, after `overlay.update`:
  1. `const ev = bloom.commit(...) ?? bloom.tick(t)`;
  2. score it (`intrinsic`, `personal`, `scoreTier`);
  3. `gate.decide`;
  4. `logged(log => log.rarity(...))` once the route exists;
  5. `spectacle.present(...)`;
  6. `spectacle.update(dt, t, frame)`;
  7. `densityTarget *= spectacle.densityMultiplier()` before the existing damping.
- **`updateCamera`** applies `spectacle.cameraOffset()` after the follow-camera maths.
- **`window.__piano`:**
  - `rarity: { stats(), events(n) }`;
  - `spectacle: { mode, setMode(m), layout(), stats() }`;
  - `spectacle.force(tier, { notes, reasons })` exists only with `?lab=1`, refuses while `rec.state !== "idle"`, and
    never logs.
- **Scheme host (piano-next):** an optional instance method `spectacle(tier, t, notes, slot)` (Neon Trails implements
  E5) and `blendPolicy()`.

---

## 6. Phased build plan

Each phase ends with its receipts green, snapshots looked at, and a report. Vandor commits.

| Phase | Scope | Files | Exit receipts |
|---|---|---|---|
| **P0 Foundation** | Merge the AA patch (3.2) with C1, C2, C3; move the receipt drivers into `arsenal/lanes/piano-receipts/`; update the `piano.css` comment. Optional P0b specular AA (3.6) | `arsenal/web/piano.js`, `piano.css`, `arsenal/lanes/piano-receipts/*` | R0.1-R0.7 |
| **P1 Theory plumbing** | `Theory.harmonySet` in THEORY with 6.1 tests; `currentInfo` over it; re-detect at the 1.5 s edge; `piano/rarity.js` (score, bloom tracker, gate, intensity, reasons) with node tests; commit hook and strike ring buffer; HUD rarity line; `__piano.rarity`. No visuals | `piano.js`, `piano/rarity.js`, `tests/fixtures/rarity_cases.json`, node tests beside the Nashville tests | R1 |
| **P2 Spectacle core** | `piano/spectacle.js` with E1, E3 (ring 1), E6 banner and chip with the Nashville crossfade, E9, E11, E12, E13; modes and settings; precompile; per-slot palettes; protect mask; `inkTop` | `piano.js`, `piano.html` (select), `piano/spectacle.js` | R2, R4, R7, R8, R9, and R5 at the P2 set |
| **P3 Full ladder** | E2, E3 rings 2-3, E4, E5 (trail shader hook), E7, E8, E10, Mythic look, phrase card, per-scheme blend policy | `piano/spectacle.js`, `piano.js` (trail shader hook) | R3, R5 full, R6, R0.6 with effects |
| **P4 History** | Log lane: `rarity` in `KINDS` (server first), the vocabulary route, analyzer upgrade handling. Client: feature detection, `rarity` events, local fallback. `arsenal/lanes/rarity_replay.mjs` replays `state/arsenal/performance/*/events.jsonl` through `rarity.js`. After Daniel's first three real sessions, re-read 4.4 and freeze `rarity/1` with a dated receipt | `arsenal/performance.py`, `serve.py` (log lane), `piano/log.js`, `piano/rarity.js`, `arsenal/lanes/rarity_replay.mjs` | R9 (log parts), R10 |
| **P5 Long game (deferred; needs Daniel)** | `/web/piano-dex.html` chord-dex (chord types with silhouettes, best reading, first found "since logging began"); "first m11 in your log" as a banner reason, ≤ 3 a session, with a starter deck of everyday types; a summoned session haul card that includes home chords; `GET /api/performance/dex` | new page, log lane routes | its own receipts, specified then |
| **P6 On Daniel's machine** | Visible Chrome at native refresh with him: HUD fps, Ctrl+= DPR change, first recording after reload, 30 minutes of real KeyLab play for feel and noise | none | R11 |

Dependencies:
- P0 waits for the other build's commit.
- P1 needs P0 only for the receipts' harness.
- P2 needs P1.
- P3 needs P2.
- P4's server half can land any time after the other build, but the client never sends `rarity` before it.
- P5 needs P4 plus Daniel's answer on the starter deck.

---

## 7. Acceptance receipts

All headless:
- Chrome with `--headless=new` plus `--disable-backgrounding-occluded-windows --disable-renderer-backgrounding
  --disable-background-timer-throttling`, a temp `--user-data-dir` and `--mute-audio`;
- GET only against Daniel's server on 8793, or the builder's own server on another port;
- never a visible window, never the app's browser pane.

Snapshots go to `state/arsenal/receipts/piano-spectacle/build/<receipt>/`, with a `receipt.json` of every number.

### R0 Foundation

| ID | Check | Pass |
|---|---|---|
| R0.1 | `wash_check.mjs` (55 s pedalled F major, 10 shots) on the merged page vs `state/arsenal/receipts/piano-wash/final-4/` | every shot: \|Δluma\| ≤ 0.002, \|Δwhite\| ≤ 0.0005, \|Δlit saturation\| ≤ 0.005; peak white ≤ 0.0096; lift clears ≥ 0.35; events 388/388; no page errors |
| R0.2 | `sustain_check.mjs` in parity mode `?fixed=1&recscale=1`, and again in default mode | parity: held v100 0.946 ± 0.01, held + pedal 1.167 ± 0.01, pedal-only early 0.742 ± 0.015, pedal-only 3 s 0.517 ± 0.01, v30 0.593 ± 0.01, v127 1.068 ± 0.01. Both modes: held + pedal > v127 > held v100 > pedal-only early > v30 > pedal-only 3 s. Default mode within ± 0.03 of parity (snapshot no longer reallocates) |
| R0.3 | `aa_bench.mjs` (frozen frame, seed 20260913, 16-sample reference) at L0, windows A 1280x900, B 2560x1440, C 1600x1000 DPR 1.5, D 2560x1440 16:9 | edge MAE A ≤ 0.0092, B ≤ 0.0075, C ≤ 0.0075; D at the step the governor picked, within 10% of that step's value in the AA doc tables; edge shimmer at L0 B ≤ 0.0056; display-path screenshot vs buffer MAE = 0 in A-D |
| R0.4 | `msaa_resolve_probe.mjs` against the merged page and the lab as shipped, REC size, 3 x 60 frames after warm-up | pixel MAE 0 and max diff 0; median ≤ 5.0 ms, p95 ≤ 6.0 ms |
| R0.5 | Governor: demo playing 30 s in each window case | the HUD step equals the highest step whose calibrated median ≤ 0.45 · P; live p95 frame interval ≤ 1.25 · P; `?res=L0` pins; report steps and ms |
| R0.6 | `rec_probe.mjs`: three 5 s takes in 9:16 and one in 16:9, demo playing, upload intercepted in-page; PyAV `analyze_rec.py` | track settings and every decoded frame exactly 1080x1920 (1920x1080); average fps from pts ≥ 58.0; ≥ 290 frames per 5 s; **first take after page load: largest gap ≤ 150 ms**; start hitch ≤ 150 ms on every take (HEAD 133); ≤ 2 gaps > 25 ms per take; live buffer back to adaptive after stop |
| R0.7 | Snapshot: 10 calls | each returns 1080x1920; `renderer.info.memory.textures` and `RES.output` unchanged across calls; no frame over 50 ms during the calls |

### R1 Scorer (node, no browser)

| Check | Pass |
|---|---|
| Every `TEMPLATES` suffix has a `COLOUR` entry | exact |
| The 4.6 table (voicing, key, context → tier) reproduces | 100% of 215 cells |
| `merged-sim.mjs` G′ | Rare 10.8, Epic 2.9, Legendary 1.5, Mythic 0 banners per 10 min; C′ 0 banners |
| `bloom-sim.mjs` spec tracker (adaptive settle) | events a bar 1.00 in every arpeggio, roll and block case; 3.00 for the pedal point; scorings ≤ 2.0 a bar |
| A passing A7b9 (250 ms between F and Dm) | logged as Epic, presented as at most Uncommon, no banner |
| Gate invariants over randomized sessions | no two banners within 6 s; Legendary spacing ≥ 120 s; no Legendary before 45 s; ≤ 1 Mythic a session; ≤ 3 banners per identity; an upgrade banners only on a tier rise |
| Honesty | "first time ever", "rare for you" and Mythic never with `source ≠ "log"` or `events < 2000`; tracker "unsure" and unlocked gives K = 0 and no key reason; template cost ≥ 4.2 caps at Rare; a lifted tier always lists its novelty first |
| Reason words | A7 in F → "secondary dominant (leads to Dm)"; Eb → "borrowed from F minor"; C7b9 → "altered tension"; Emaj7/G# → "far outside the key"; no "accented", "chromatic mediant", "borrowed note" |
| Identity | the same chord with Minor numbering "tonic" vs "relative" gives the same id1/id2 |

### R2-R11 Spectacle and history

| ID | Check | Pass |
|---|---|---|
| R2 | **Light during Legendary.** `spectacle_check.mjs` plays the wash_check score with `?lab=1` and `__piano.spectacle.force("Legendary")` every 3 s; the same seeded run with `?spectacle=off`; shots at +0.3, +0.8, +1.4, +2.2 s after each force | per shot vs Off: Δmean luma ≤ +0.06; white share ≤ Off + 0.0005; staff box luma ≤ 0.35; chord-name band non-text luma ≤ Off + 0.035; chord glyph alpha mask identical outside the foil window; events 388/388 |
| R3 | **Dense wash stress.** 40 notes in 4 s across three octaves, pedal down, Legendary forced at +0.8 s and Epic at +1.6 s | mean luma ≤ 1.30 x Off; staff box ≤ 0.35; no row in y 150-1370 with white share > 0.05; every staff notehead detected by the existing check |
| R4 | **Sustain rule unchanged.** `sustain_check.mjs` with a forced Legendary 0.2 s before each reading vs the same run Off | key glow values within ± 0.01 of Off; the ordering of R0.2 holds; a pedal-only trail stretch's luma dims ≤ 35% and is back to ≥ 95% within 4.0 s |
| R5 | **Frame time.** `__piano.lab.bench` (1-pixel sync) at REC size and at 1x 1080x1920: idle, held chord, Rare, Epic, Legendary, stacked (Legendary + Epic + Rare), stacked over a dense wash; Full vs Off | REC size: Δmedian ≤ 1.0 ms, Δp95 ≤ 1.5 ms. 1x: Δp95 ≤ 0.3 ms. The first forced Legendary after boot ≤ steady p95 + 2 ms. `rec_probe` with forces every 3 s: average fps ≥ 58.0, no gap > 50 ms after the start hitch |
| R6 | **Noise.** (a) The wash_check score looped for 9 minutes, Full; (b) the spec 6.6 pedal storm, 60 s; (c) the merged-sim Daniel-style event stream replayed through the page (`lab.sim` with detect) | (a) Legendary 0, Epic ≤ 1, banners ≤ 1 a minute, zero overlapping banners; (b) ≤ 2 banners, zero overlaps; (c) Common rail pulses ≤ 12 a minute; phrase cards ≤ 1 a minute |
| R7 | **Layout collisions.** `__piano.spectacle.layout()` rectangles vs the label glyph box (`measureRuns`), chips, the Nashville row, the staff ink box (with `inkTop`), the pedal mark and TikTok zones, both framings, k = 0.5, 1, 2 (outputs 540x960, 1080x1920, 2160x3840); plus a high-ledger case (C6-C7 with flats) | zero intersections for the banner, chip and phrase card; the high-ledger case selects the compact form; at k = 1 the label, staff and Nashville layers are byte-identical with spectacle Off |
| R8 | **Off is byte-identical.** Seeded frozen frame (`lab.seed`, `sim`, `freeze`) with `?spectacle=off` vs the P0 build | MAE 0, max diff 0, at L0 and L2 and in a snapshot |
| R9 | **Honesty at runtime.** Demo 60 s; computer keys 30 s; `force()` during REC; a banner audit over R6(a) | 0 `rarity` events from the demo and computer keys; `force()` returns false during REC and never logs; 100% of banners whose tier novelty lifted show that novelty; no `rarity` POST before the vocabulary route answers 200 |
| R10 | **History round trip** (own server, temp performance root) | open → events with `rarity` → close → `vocabulary.json` counts match, with upgrades moved; a 400 for a malformed `rarity` event drops nothing else in a later batch; the replay tool reproduces the page's tiers for a recorded session |
| R11 | **On Daniel's machine** (P6, with him) | HUD fps ≥ 0.95 x refresh in 9:16 fullscreen, Full, while playing; Ctrl+= changes the HUD buffer to CSS size x zoom; the first recording after a reload has no hole (PyAV); he judges 30 minutes of play for noise |

### Snapshots to look at (with the Read tool) before calling a phase done

| Phase | File (under `state/arsenal/receipts/piano-spectacle/build/`) | What to see |
|---|---|---|
| P0 | `p0/aa-crops/B-keys.png` (the aa-crops format) | key edges closest to the reference; compare `aa-crops/B-2560x1440-pipeline-keys.png` |
| P0 | `p0/wash/04-hold-2bars.jpg` vs `piano-wash/final-4/04-hold-2bars.jpg` | the same picture |
| P2 | `p2/rare-+0.25s.jpg`, `p2/rare-+0.6s.jpg` | the ring's front arc under the keys, then its back arc behind the rail; banner in the Nashville slot with the number; staff readable |
| P2 | `p2/legendary-+0.3s.jpg` | gold foil name, gold rail, banner with gems; reference `vfx/hook-v2/leg-1-+0.3s.jpg` |
| P2 | `p2/high-ledger-banner.jpg` | the compact form clear of the accidentals (the collision in `vfx/hook-v2/wash-1-leg+0.8s.jpg` is gone) |
| P2 | `p2/tasteful-legendary-+0.8s.jpg`, `p2/off-baseline.jpg` | the chip; Off equal to P0 |
| P3 | `p3/legendary-+0.8s.jpg`, `p3/legendary-+2.2s.jpg` | shafts, rings, hem ribbon without an upper haze, fountain at the feet |
| P3 | `p3/wash-legendary-+0.8s.jpg` | busy, not washed; every notehead visible |
| P3 | `p3/wide-legendary-+0.8s.jpg` | 16:9 |
| P3 | `p3/phrase-card.jpg` | the calm card in a rest |
| P3 | `p3/mythic-+0.8s.jpg` (forced, lab) | tier word in chord colours, `FIRST TIME EVER`, hem in pitch colours |

---

## 8. Open questions for Daniel (three, each with a recommended default)

1. **Where should the rarity banner sit on the vertical frame?** The gap between the chord name and the staff now holds
   your live Nashville numbers.
   - **Recommended:** for its 2-3 seconds the banner takes the Nashville row's place. The row fades out and back, and
     the banner's first line carries the number (`EPIC · A7♭9 · 3⁷♭⁹`), so nothing disappears.
   - Alternative: a banner lower down, between the staff and the keys, over the rising columns.
2. **Should tiers be personal on recordings?** The same chord can be Epic tonight and Uncommon next month, once it has
   become one of yours.
   - **Recommended:** yes, always with the reason printed in the frame ("first this session", "rare for you"), so a
     viewer reads what it means.
   - Alternative: recordings use fanciness alone (no familiarity, no novelty), identical for everyone.
3. **Which spectacle level by default, live and recording?**
   - **Recommended:** Full (rings, fountain, light shafts, gold Legendary, the phrase card), rationed as in section 4.4.
   - Alternative: Tasteful (rings, sheen and a one-line chip; no fountain, shafts at 60%, no camera push, no card), with
     Full one click or the `` ` `` key away.

## Daniel's decisions (2026-09-14, answered in chat)

- **Banner spot:** the recommended placement. For its 2-3 seconds the rarity banner takes the Nashville number row's place and carries the number (e.g. "EPIC · A7b9 · 3 7b9"), then the row fades back.
- **Personal or fanciness:** "I think a mix of both, We can make it a toggle". Build a Rarity setting, persisted in localStorage `arsenal.piano.rarity`:
  - **Mix** (the default): Φ = F × h + novelty, as specified above.
  - **Fanciness only:** F with h = 1 and no novelty bonus, so the same chord gets the same tier for everyone.
  - The banner's reason line names what drove the tier in either mode.
- **Default spectacle:** Full, live and when recording. It is rationed as specified, and Tasteful and Off stay one click (or the ` key) away.
