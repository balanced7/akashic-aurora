# Judge: feasibility, performance and honesty (piano spectacle round, 2026-09-13/14)

Lens: which ideas fit this code and the light budget at 60 fps, which are expensive or fragile, whether the rarity scoring is
musically honest and robust to pedalled arpeggios, and whether the resolution/AA prototype's evidence holds up.

Daniel, verbatim: "Can you reload the piano page and make it be perfectly un-aliased, can we make it even more a visual
spectacle? Perhaps even having a rarity and fanciness scale xD" and "Lets make the resolution be adaptive to the render window".

What I read in full: `adaptive-resolution-aa.md`, `adaptive-resolution-aa.patch`, `design-theory-rarity.md`,
`design-vfx-director.md`, `design-loot-feel.md`, HEAD `piano.js` (light budget, spark sizing, recording path, overlay commit),
`PIANO-V2-SPEC.md` 6.1-6.2, `rec_probe.mjs`, `cdp.mjs`, `analyze_rec.py`, `aa_bench.mjs` (phrase), the theory lab's `sim.mjs`
and outputs. Images viewed: `aa-crops/B-2560x1440-pipeline-keys.png`, vfx `hook-v2/leg-2-+0.8s.jpg` and
`hook-v2/wash-1-leg+0.8s.jpg`, loot `mockups/loot-b-legendary-unlock.png`.

What I ran myself (headless Chrome only, `--headless=new` + the three anti-throttling flags; GET only against 8793; nothing
POSTed; no git add/commit; piano.js / piano.html / log.js / nashville.js / arsenal Python untouched):

1. **Theory-rarity sim re-run.** `node sim.mjs` in `design-theory-rarity-lab/` reproduces `sim-output.txt` byte for byte
   (CRLF ignored). Saved as `judge-feasibility-data/theory-rarity-sim-rerun.txt`.
2. **A true HEAD recording control.** Lab copy from HEAD: `arsenal/web/piano-lab-judge-head.{js,html}`. Three 4 s takes
   through HEAD's own REC button, demo playing, 1600x1000 window, with `fetch` to `/api/*` intercepted inside the page (no
   upload). Then the same driver against `piano-lab-res.html` (defaults: adaptive, REC 2x MSAA 4). Script
   `judge-feasibility-data/head_rec_control.mjs`; analyses `rec-analysis-head-control.json`, `rec-analysis-lab-same-driver.json`.
3. **An MSAA resolve experiment.** Lab copy of the resolution lab: `arsenal/web/piano-lab-judge-res.{js,html}`, identical except
   that `window.__judgeRt1` can set the composer's `renderTarget1` sample count. Frozen deterministic frame (aa_bench's phrase,
   seed 20260913), REC size 1080x1920 output / 2160x3840 scene. Script `msaa_resolve_probe.mjs`, result `msaa-resolve-probe.json`.

The four `piano-lab-judge-*` files in `arsenal/web/` are untracked lab copies and can be deleted once this round is closed.

---

## 1. Scores

| Design | Score | One line |
|---|---|---|
| theory-rarity | **8** | The only scorer that is actually a *rarity* scale and is honest about what it can claim; reproducible calibration; visual side thin and partly unmeasured. |
| vfx-director | **7** | The real spectacle, prototyped and measured with receipts and fixed defects; but its scorer is a loudness/block-strike scale wearing rarity's name, and its costs were measured on the old 1x pipeline. |
| loot-feel | **6** | Best layout and restraint thinking, near-free to render; but its DROP_TABLE rewards voicing size and has no habituation, so Daniel's normal pedalled two-hand playing would inflate to RARE/EPIC/LEGENDARY, and nothing was run on data. |

---

## 2. The resolution / AA prototype: does the evidence hold?

**Verdict: adopt, with three changes before merge.** The recommendation (adaptive device-pixel buffer, 2x supersampling with an
exact linear-light box downsample after tone mapping, MSAA 4 on the scene, bloom pinned to framing size, REC at exactly framing
size and paced to 60 fps) is sound, and its central evidence holds. Two claims needed correcting or strengthening, and one
measured optimisation is left on the table.

### 2.1 What I checked in the patch and found correct

- **Bloom equivalence at 1x.** Stock `UnrealBloomPass` sizes `renderTargetBright` to round(w/2) and its high-pass samples the
  full-res input with a bilinear tap at the half-res texel centre, which is exactly the 2x2 average. `FramingBloomPass` feeds it
  an exact area average into a half-framing target, so at a 1080x1920 scene the glow is the same, and at any other scene size
  the glow keeps one shape. Its blend onto `readBuffer` with the stock `blendMaterial` matches the stock composite.
- **Downsample.** Separable, exact footprint weights with `texelFetch`, decode sRGB -> average -> encode. It filters in
  display-linear light after tone mapping, which is the right place (MSAA resolves in HDR before tone mapping, which is why MSAA 8
  did not beat MSAA 4 on bright additive edges). Loop bounds (24 taps, 12x12 box) cannot be exceeded under the pixel caps.
- **Composer bookkeeping.** `downsamplePass.enabled` toggling works with `EffectComposer.isLastEnabledPass`; `setViewOffset` in
  scene pixels is equivalent to HEAD; `uPx` in scene pixels keeps spark world size constant.
- **Light model untouched.** No changed line touches `LIGHT`, `uDensity`, `LIGHT_BUDGET` or the envelope. The wash check matches
  final-4 to 3-4 decimals and the sustain check matches HEAD with `?fixed=1&recscale=1`.
- **Visual evidence.** `B-2560x1440-pipeline-keys.png`: `none` and `msaa4` show stair-steps on black-key sides and the rail; SMAA
  softens but keeps crawl; `ss2-box+msaa4` is visibly closest to the 16-sample reference. It agrees with the numbers.
- **Metric caveat, acceptable.** The reference is built with the same post-tonemap box filter the winning method uses, so the
  edge-MAE metric structurally favours post-tonemap supersampling over HDR-resolve methods (MSAA, SSAA-in-HDR). That is
  defensible (the eye integrates display light, not HDR scene light), and the shimmer metric, which does not depend on the
  reference's filter shape in the same way, points the same direction (tent loses on shimmer too).

### 2.2 The "first take loses 2.3-2.6 s, pre-existing" claim: right conclusion, wrong evidence, now verified

The doc says the loss "reproduced with HEAD's own 1x pipeline". `rec_probe.mjs` shows that take was the **lab page** with
`set({ fixed: false, recScale: 1, msaa: 4 })`, which still runs `setRecordResolution(true)`: buffer resize from adaptive to
framing size, composer realloc and overlay rebuild right before `captureStream`. That is not HEAD's code path.

My control on an unmodified HEAD copy (same 1600x1000 window, demo playing, upload intercepted):

| page | take | frames in file | fps from pts | largest gap |
|---|---|---|---|---|
| HEAD (unmodified) | 1st | 92 | 22.80 | **2500 ms at 0.162 s** |
| HEAD | 2nd | 233 | 58.37 | 133 ms at 0.162 s |
| HEAD | 3rd | 231 | 57.57 | 134 ms at 0.162 s (+87 ms at 0.53 s) |
| lab-res defaults, same driver | 1st | 86 | 21.31 | 2588 ms at 0.169 s |
| lab-res | 2nd | 224 | 55.91 | **283 ms** at 0.171 s |
| lab-res | 3rd | 228 | 56.88 | **183 ms** at 0.153 s (+88 ms at 0.52 s) |

- **Confirmed pre-existing:** the first-take ~2.5 s hole and a ~133 ms start hitch on every take are in HEAD itself
  (MediaRecorder / H.264 start-up is the likely cause; the prototype's warm-the-encoder-on-arm fix stands).
- **New, small regression:** on warm takes the lab's start hitch is 50-150 ms longer and the file loses 5-9 frames per 4 s
  against HEAD in this one run (shared GPU, n=1 per condition, so treat as indicative). The obvious cause is the REC-start
  reallocation of two 2160x3840 RGBA16F 4-sample targets (about 265 MB each) plus the overlay rebuild. Fix: allocate the REC-size
  targets when REC is armed (or keep a dedicated REC composer alive) so starting REC is a pointer swap, not an allocation.

### 2.3 Measured optimisation the prototype missed: MSAA on post-pass targets

`EffectComposer` clones its render target, so **both** `renderTarget1` and `renderTarget2` are 4-sample MSAA. With the
downsample enabled there are two swaps per frame, so the RenderPass always writes `renderTarget2` and only the full-screen
`OutputPass` writes `renderTarget1`. A full-screen quad gains nothing from MSAA, but it pays an 8.3 MP multisample resolve.

| REC size, frozen frame, 3 x 60 frames after warm-up | median ms | p95 ms | pixels vs shipped lab |
|---|---|---|---|
| 2x MSAA 4, rt1 MSAA 4 (lab as shipped) | 6.3 / 6.4 / 6.5 (repeat 6.5 / 6.4 / 6.4) | 7.0-7.3 | reference |
| **2x MSAA 4, rt1 no MSAA** | **4.9 / 4.9 / 4.9** (repeat 4.9 / 4.9 / 4.9) | 5.7-5.9 | **MAE 0, max abs diff 0** |
| 2x, no MSAA | 2.1 / 2.1 / 2.0 | 2.8-3.3 | (different AA) |
| 1x MSAA 4 fixed (HEAD-equivalent) | 1.5 / 1.6 / 1.4 | 2.6-2.8 | (different AA) |

About **23% off the recommended pipeline, pixel-identical**. The bloom blend still lands on the MSAA scene target (another
resolve); a dedicated MSAA scene target that is resolved once, with all post passes on single-sample targets, should save more,
but I did not measure that. Note that at 1x (downsample disabled, one swap per frame) the targets alternate roles, so the
single-sample rt1 is only safe while the downsample runs; a dedicated scene target avoids that trap.

### 2.4 Other feasibility notes on the prototype

- **The fixed 5 MP live cap will often choose 1x on Daniel's real screen.** Example: a fullscreen 9:16 canvas on a
  2160-px-tall display is 1215x2160 = 2.6 MP; 2x is 10.5 MP, so it floors to 1x MSAA 4. The doc's own tables show 2x *without*
  MSAA (edge .0091 at case B) beats 1x MSAA 4 (.0148) at 2.0-2.9 ms. Replace the fixed cap with a frame-time governor with the
  ladder 2x+MSAA 4 -> 2x -> 1x+MSAA 4, measured on his display and refresh rate.
- `snapshot()` now reallocates twice per call. That changes receipt timing (sustain values shift by up to .05 at 2x). Keep
  `?fixed=1&recscale=1` as the parity mode for glow receipts, or read `stats()` before snapshotting.
- The merge is a hand 3-way onto the other build's `piano.js`; every new overlay canvas must go through `makeLayer()` and scale
  `shadowBlur`. All three spectacle designs add overlay canvases (banner, foil, tag, bar), so this rule binds them.
- Residual shader aliasing on clearcoat bevels and sub-pixel sparks is honestly reported; "perfectly un-aliased" is not literally
  met and the doc says so.

---

## 3. Design-by-design judgement

### 3.1 theory-rarity (8/10)

**Strengths (feasibility, honesty):**
- A real two-axis model: intrinsic fanciness F (colour by TEMPLATES suffix, bass by the template's own letter steps, a
  deliberately small capped voicing term, key distance by counted outside notes) times familiarity h, plus a novelty ladder of
  claims the data can back. It is the only design where a chord Daniel loops becomes Common, which is what "rarity" means.
- Evidence gates are concrete: tracker "unsure" -> K = 0; mid-modulation uses the kinder key; template cost >= 4.2 caps at Rare;
  pedal-blend > 40% caps F; "first time ever" and Mythic need >= 2,000 logged chords and never trust localStorage.
- The failure history is recorded (surprisal failed because a long tail of individually rare lush chords is collectively
  common). That is good epistemics.
- Pedalled-arpeggio robustness is layered and measured: bloom merge (1,112 name changes -> 278 events, 1 Rare banner in 10 min),
  familiarity, per-identity caps, cooldowns, inflation guard (can only make tiers stricter). The sim reproduces exactly.
- Correct music-theory corrections of the brief (Bb is 4 in F; the overlay names Bb F A C D E as Dm9/Bb).
- Cheap: pure module, one score per committed event, banner is an overlay layer after OutputPass.
- Flags the cross-build hazard precisely: `performance.py` rejects unknown event kinds and drops the whole batch.

**Weaknesses:**
- **Depends on `Theory.harmonySet`, which does not exist.** Only `piano/schemes/harmonic-wave.js` has a local `harmonySet`.
  The 40% pedal-blend cap is the only guard until it lands.
- **The bloom merge is tempo-tuned.** `window = 1.6 s` and the sim steps notes at 0.33 s. A slow pedalled bar (for example 8
  notes over a 3.4 s bar at 70 bpm) exceeds the window and `maxLen 2.5 s`, so one bar becomes two or three events. Worse,
  harmonySet drops pedal-held notes older than 1.5 s (except the lowest), so late in a slow bar the committed set can *shrink*,
  which breaks the superset test and starts a new bloom. The gates absorb it, but the "one bar = one event" property is not
  tested at slow tempi.
- **Presentation is under-built and partly unmeasured:**
  - The Legendary "bloom +0.1 paid for by lowering the density target" claim is asserted, not measured. Bloom strength is not
    linear in trail density, and a bloom lift is exactly what Daniel complained about.
  - A Rare "tier-colour rim on the chord's keys" puts a UI colour on keys, which muddles the key-glow meaning Daniel asked for
    (brightest under finger + pedal, velocity-scaled).
  - Epic "spark count x1.5 at unchanged brightness" still adds additive light.
  - Daniel asked for *more spectacle*; this design's scene side is a ring pulse and a camera push.
- **Banner placement collides.** A 980x110 box centred at y 540 spans 485-595; the treble clef top is about y 586 (loot mockup
  finding M1), and ledger-line accidentals above the staff reach higher (visible in vfx `wash-1-leg+0.8s.jpg`).
- **Small theory slips:** "Emaj7/G# (chromatic mediant)" in F is wrong (E is a half step below F, a leading-tone major chord; the
  chromatic mediants of F are A, Ab, D, Db). The K table says E major scores 3.0, but E G# B has two outside notes, so
  K = 2.25. The reason "borrowed note" is used for b9 tensions (C7b9's Db), which are altered tensions, not borrowed notes.
- Many knobs (h's two smoothsteps, bandShare, ladder cutoffs, inflation guard) on a synthetic style mix, with no real data yet
  (the log started tonight).

### 3.2 vfx-director (7/10)

**Strengths:**
- Actually built and looked at: Rare and Legendary in a lab, four round-1 defects found in snapshots and fixed (dark mask
  rectangle, shimmer to white, 40-column white bar, aurora mush), re-measured. `leg-2-+0.8s.jpg` reads well: gold foil name, clean
  banner, shaft fan, glitter at the feet, staff readable.
- Integrates with the existing light model instead of fighting it: house lights multiply the density target and ride the
  existing fast-dim / slow-recover damping. Dense wash + Legendary held to +29% luma (v1 +62%), staff 0.29 against the 0.6 bar;
  near-white share falls during a Legendary.
- Uses empty stage (floor, rail, back wall) and depth tests so nothing covers key fronts; text effects after OutputPass.
- Good AA discipline for effects: ring width clamped to 2*fwidth with energy kept, fwidth-widened beams, 2.5 px point minimum
  with area-scaled alpha, twinkle under 2 Hz, everything clock-driven.
- Honest about its limits: bench noise larger than effect cost, no visible-window fps, scorer overfit, compile hitch, shared
  palette uniform, conflict with strict schemes.

**Weaknesses:**
- **The scorer is an intensity scale, not rarity or fanciness.** Rare needs >= 3 notes struck within 80 ms; Epic needs >= 4
  struck plus a +12 accent; Legendary needs >= 5 struck plus +22 accent or velocity 112. A rolled or arpeggiated lush voicing,
  which is how Daniel plays pedalled chords, can never reach Rare. A loud block triad with an arc can reach Legendary. That is
  robust to pedalled arpeggios only because it ignores them. Calling the result "Legendary" on a public video is a claim about
  the chord that the scorer does not measure. The token governor also rations by time, not by musical rarity. Tuned on its own
  authored 70 s of music.
- **Costs measured on the old pipeline.** All benches are at 1x MSAA 4 1080x1920. Under the recommended 2x pipeline the large
  additive quads pay about 4x fill: shafts (~35% of frame), aurora (~60%), floor ring (~25-30%), plus a 7-loop and a 3-sine shader.
  REC at 60 fps will still fit (4.9-6.4 ms base), but it needs a re-bench at 2160x3840, and live at high refresh it competes with
  the governor.
- Scope and fragility: 12 effects, about five new shader programs, per-slot palette bug, compile hitch (needs `compileAsync`),
  and additive rings/shafts violate spec 6.2's "never sum light" for strict schemes, so a per-scheme blend policy is required.
- House lights dim pedal-only columns by up to 35% for ~3.5 s (`fresh = max(vHeld, ...)` keeps only finger-held and fresh
  stretches at full price). That is consistent with the LIGHT model but should be checked against Daniel's sustain rule with the
  sustain receipt during a forced Legendary.
- A 5.5% push with +1.3 deg yaw on a follow camera is the most likely effect to read as seasick in a recording.
- The banner's y 490-590 zone collides with ledger-line accidentals above the staff in the wash receipt.

### 3.3 loot-feel (6/10)

**Strengths:**
- The most careful layout work: TikTok header, button column and caption zones mapped against LAYOUT and the real receipts;
  five mockup findings (clef collision, foil muddying the name, pips too small, card showing the barline) that paper would have
  missed; an automatable collision receipt (R8) at k = 0.5/1/2.
- Near-free and light-budget-proof by construction: everything is overlay after OutputPass with normal blending; the only 3D
  change is a rail hue shift at equal luminance; Canvas2D redraws on events only.
- Strong restraint rules: the chord name is never moved or delayed; no sounds; no fail states; no randomness or near-miss;
  Show / Practice / Off.
- Two genuinely good musical ideas: combo credit for smooth voice leading (rewards playing, not vocabulary), and the phrase
  cash-out landing in the rest (good for the player, and a natural TikTok cut point).
- Honest separation on paper: "NEW" means new since logging began, stated on the dex page.

**Weaknesses:**
- **DROP_TABLE inflates on Daniel's style and is not rarity.** Voicing points (+1 for 5+ notes, +1 for 2 octaves, +1 for 3
  octaves) are what pedalled two-hand playing produces by default. By its own table a two-hand Bbmaj7 is RARE, a wide Fmaj9 is
  RARE, and the Dm11/G in receipt 04 is LEGENDARY. There is no familiarity term. The repeat guard covers only the current and
  previous two chords, so a four-chord loop re-tags RARE/EPIC every pass. Rule 6 ("replaying a chord doesn't re-drop") contradicts
  section 5.4.
- **The calibration story contradicts itself.** The tier is declared intrinsic ("the same for every viewer"), yet the cutoffs are
  to be moved until Daniel's histogram hits 50/25/15/7/2.5%. That makes it relative to him after all. And with his lush default,
  hitting 50% Common means raising cutoffs until "LEGENDARY" no longer matches the doc's own examples.
- **Nothing was run on data.** Unlike the other two, no scorer ran on any phrase or sim. Mockup A's EPIC label disagrees with its
  own table (self-noted).
- **Scope creep across builds:** chord-dex page, Python twin, `/api/performance/dex`, Moves page, shiny / best roll, session
  haul card. All depend on the log lane, which is in flight.
- Persistent in-canvas chrome (combo medallion, vertical gauge, phrase socket) adds clutter to every recorded frame.
- A secondary dominant (E7 in C) is called "borrowed".
- Visual spectacle is mostly UI; it adds little to the 3D stage Daniel asked to be "more a visual spectacle".

---

## 4. Must-haves, merged into one system

1. **Pipeline first.** Merge the adaptive-resolution work (with 2.2-2.4 changes) before authoring effects, so every effect is
   tuned in the final pixel pipeline. All pixel constants (spark minimum, banner canvas, ring fwidth) are in output pixels via
   one scale k; all overlay canvases go through `makeLayer()`.
2. **One pure scorer module (`piano/rarity.js`), node-tested**, built on theory-rarity's model:
   - F = colour by TEMPLATES suffix + bass by letter steps + small capped voicing + key distance gated by tracker confidence + a
     small performance term;
   - h = familiarity (a looped chord becomes home tonight);
   - a novelty ladder of checkable claims; "first time ever" and Mythic only from the practice log with >= 2,000 chords;
   - honesty caps (template cost, pedal blend);
   - key-relative identity via Nashville numbers.

   Velocity and vfx's crescendo **arc** scale the *size* of the effect, never the tier. All three designs agree on velocity.
3. **One event per committed harmonic event.** Promote `harmonySet` into Theory first (the local copy in `harmonic-wave.js` is
   the seed), then theory-rarity's bloom merge with upgrade-only banners. Make the merge settle-based rather than a fixed 1.6 s
   window, and add a slow-tempo test (3-4 s bars).
4. **One banner gate:** 6 s minimum spacing, tier cooldowns, per-identity caps, blocked events fall back to a glint, and the
   inflation guard may only tighten. This replaces vfx's token buckets.
5. **Presentation ladder**, overlay text after OutputPass and scene light paid from the budget:
   - Uncommon: loot's rarity bar or glint under the name (no scene light).
   - Rare: tier word with pips, plus a banner with theory's plain-words reasons; vfx rail pulse and floor shockwave (cheap, and
     they use the empty stage).
   - Epic: adds vfx light shafts and a foil glint clipped to glyph alpha.
   - Legendary: adds vfx gold foil name, gold rail, rings and house lights (the budget pays), and a small camera push of 2.5-3%
     with no yaw.
   - Mythic: theory's gate, with the tier word in the chord's own pitch hues and vfx's aurora hem only.
   - Gold means Legendary only. Tier colour appears only in UI chrome, always with a word and pips, never on keys or trails.
6. **Light rules from vfx:**
   - only thin crests cross the bloom threshold; bodies stay under it;
   - house lights instead of a bloom lift;
   - effects scale down with the number of columns they touch;
   - a per-scheme blend policy (strict schemes get normal-blend hairlines);
   - spectacle Off is byte-identical.
7. **Phrase cash-out in the rest** (loot), passed through the same gate, as the TikTok loop point.
8. **Layout from loot:** the TikTok safe-zone map and the R8 collision receipt. Resolve one banner zone against the Nashville row,
   the clef, and ledger-line content above the staff. All three designs picked the same 485-595 gap.
9. **Engineering hygiene:**
   - `renderer.compileAsync` precompile at boot;
   - a per-slot palette DataTexture;
   - clock-driven animation only;
   - OKLab palette blends;
   - an R toggle plus Show / Practice / Off.
10. **Calibration on Daniel's real logs** by offline replay (all three designs agree). Freeze and version the tier table (loot's
    DROP_TABLE versioning idea applied to the rarity table). Add `rarity` to `performance.py` KINDS before the client sends it.
11. **Receipts before shipping:**
    - `wash_check` with a forced Legendary every 3 s;
    - `sustain_check` during a forced Legendary;
    - chord-name band within 5%;
    - `rec_probe` at 2x with effects live (60 fps file, no new gaps);
    - banners per 10 minutes on a replayed log.

## 5. Cut (or defer)

- Loot's DROP_TABLE as the tier source (voicing-size points, no habituation).
- Loot's chord-dex page, Python twin, `/api/performance/dex`, Moves page, shiny / best roll, session haul card: defer until the
  log vocabulary exists and the in-canvas system has proven itself.
- Loot's always-on combo medallion, gauge and phrase socket in Show mode (clutter on every recorded frame). At most, Practice
  mode or cash-out only.
- vfx's tier gates on notes struck within 80 ms and on accent or velocity (they turn rarity into loudness and lock out rolled
  voicings). Keep the arc only as an effect-size multiplier.
- vfx's aurora upper haze, dispersion fringe, 5.5% push with yaw, 900-spark fountain, E14 time dilation (it touches the LIGHT
  time base), and E16 summoned "Mythic" (a staged Mythic contradicts the honesty rule; theory-rarity rightly refuses any
  showcase multiplier).
- theory-rarity's tier-colour key rim, its Epic spark count x1.5, and its Legendary bloom +0.1.
- From the resolution merge: `setLabAA`, the TAA/SMAA/FXAA branches and the tent / 1.5x options. Keep the `scale`, `recscale` and
  `msaa` query params and the lab hooks the receipts need.

## 6. Concerns

- `Theory.harmonySet` does not exist; all three scorers assume it.
- Effect costs were measured only at 1x; re-bench vfx's large additive quads at 2160x3840.
- REC-start reallocation lengthens the start hitch (warm takes: lab 183-283 ms vs HEAD 133 ms, n=1). Pre-allocate REC targets
  on arm.
- The fixed 5 MP live cap drops to 1x on large windows; use a frame-time governor with a 2x-without-MSAA step.
- Banner y zone collisions (clef top ~586, ledger accidentals, the Nashville row from the other build).
- House lights dim pedal-only columns; verify against the sustain rule.
- Calibration in all three is synthetic or authored; the practice log started tonight.
- Cross-build ordering: `rarity` must be added to `performance.py` KINDS before the client sends it, or whole batches drop.
- Theory slips in the rarity doc (the "chromatic mediant" label, E major K, "borrowed note" for b9) must be fixed before any
  reason text ships; loot's "borrowed" for secondary dominants likewise.
- snapshot() reallocation shifts receipt timing; keep a parity mode.
- VRAM churn: two 265 MB MSAA targets at REC size are allocated and freed on every REC start/stop and every snapshot.
- HDR: nothing uses Daniel's HDR monitor; out of scope tonight, but worth stating so it is not assumed.

## 7. Receipts index (this judge)

| What | Where |
|---|---|
| HEAD recording control script | `judge-feasibility-data/head_rec_control.mjs` |
| HEAD control PyAV analysis | `judge-feasibility-data/rec-analysis-head-control.json`, takes `head-control-takes.json` |
| Lab with the same driver | `judge-feasibility-data/rec-analysis-lab-same-driver.json`, takes `lab-same-driver-takes.json` |
| MSAA resolve experiment | `judge-feasibility-data/msaa_resolve_probe.mjs`, `msaa-resolve-probe.json` |
| Theory sim re-run (byte-identical) | `judge-feasibility-data/theory-rarity-sim-rerun.txt` |
| Lab copies (untracked, deletable) | `arsenal/web/piano-lab-judge-head.{js,html}`, `arsenal/web/piano-lab-judge-res.{js,html}` |

MP4 takes themselves are in the session scratchpad (`judge/head-rec/`, `judge/lab-rec/`), not in the repo.
