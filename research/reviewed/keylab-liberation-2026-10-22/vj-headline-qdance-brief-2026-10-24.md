# Headline Q-dance pass: the four studies and the art-direction brief (2026-10-24)

Workflow run wf_82a5da4f-0f7 (tasks w1oz8rkkk, wvag23n2k). All texts verbatim; local scratch paths shortened. The 40 reference images are other people's work: they stay in the session scratchpad and are never committed (only their names and descriptions appear here). The private Shadertoy corpus is cited by id for learning only; no corpus code is reproduced.

Daniel (verbatim, 2026-10-24): "I like your presets the best, would you mind going through and making them truly headline qdance worthy xD" and "no expense spared, research everything you need to, compare to actual visuals and shows, use our shadertoy presets and learnings too, i am sure we can make an amazing thing"


---

## The art-direction brief (verbatim)

# Headline brief: making the VJ scenes Q-dance headline-worthy

Art director's brief, 2026-10-24. It is for Daniel and for the shader builders. I made no repo edits and no commits, and touched nothing on the KeyLab or on ports 8793/8794. My scratch files are in `<session scratchpad>\headline\` (the calibration scripts `ad_calib.py` and `ad_calib2.py`, and `brief\new_scenes.json`, which holds the JSON at the end, already checked).

## For Daniel, in plain words

Your scenes have good ideas. They do not yet look like a headline show, for two reasons.

- **There is no true black anywhere.** I checked every scene at every moment. Not one pixel reaches true black.
- **Nothing gets white-hot.** In every groove frame, no pixel reaches white.

Q-dance's own LED content is the opposite. It is 34–48% true black, with one lit symbol in the centre. Its few highlights burn white, and its colour comes in pairs that hold for a phrase.

So the plan has three parts:
1. **Fix the shared look once.** Real black, real white-hot light, one display curve, proper glow, and one colour grade per section. Every scene gets better the same day.
2. **Rebuild each scene around one hero in the centre.** Each is tied to real show references.
3. **Add three scenes in Q-dance's own grammar:** Ritual Fire, Pyro Finale and Guardian.

Two of my recommendations replace a scene's look: LED Wall becomes Torn Red, and Synthwave Grid becomes Laser Sea. Both keep the parts you play today (the pads, the beat lurch, the composition). Those two are your call.

## What I checked myself

**Sources, fetched today.** The decisions below depend on these, and each said what the studies reported:
- TWOFIFTYK, about their Qlimax work (https://twofiftyk.com/en/project/qlimax):
  - nearly an hour of timecoded visuals for 17 shows, with no content reused;
  - TouchDesigner keeping visuals, lights and lasers in sync;
  - one VJ on timecode and one playing live;
  - lights and lasers aimed at moving stage parts.
- Syncronorm (https://www.syncronorm.com/newsitem/qlimax-2023-interview): the Qlimax 2023 lighting told its story through the contrast of light and darkness. Its "illusionist" led the crowd into the "void".
- Backbone/TPi (https://www.backbone-international.com/talks/tpi-qlimax/): two layers of LED, the header wall translucent, used to build big looks.
- Vision Impossible (https://www.vision-impossible.nl/portfolio/qlimax/): doing Qlimax since 2005, and describing its themes as dark and immersive.
- Jonas Schmidt, via Hard News on the 3voor12 documentary (https://hardnews.nl/en/3voor12-documentary-reveals-the-creative-process-behind-the-defqon-1-endshow/): each scene sometimes gives the crowd what it expects and sometimes the exact opposite, always chasing contrast.
- AVIXA (https://www.avixa.org/explore/articles/the-illusion-of-3d-on-led-walls-how-content-and-perspective-create-immersive-visuals): depth on a flat wall comes from forced perspective, foreshortening, shading and shadows, lighting contrast, depth of field and motion parallax.
- Rick Jacobs, the one direct quote I use: "black is your friend" (https://resolume.com/blog/14343).
- The safety rules come from `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\vj-festival-lessons-2026-10-24.md`, which I read: ITU-R BT.1702, WCAG 2.3.1 and the Epilepsy Society.

**Code, checked against the repo.**
- Every preset ends with a tone curve, `pow(1/2.2)` and a clamp. Example: `vj-laser-cathedral.frag:199-203`.
- The scenes paint a faint room colour. Example: `vj-laser-cathedral.frag:139`, `vec3(0.0012,0.0015,0.003)`.
- Trails fade per frame, not per second: `prev*keep - 1.5/255`.
- The composite adds a soft centre lift on every hit and an edge breath from the metronome (`vj.js:282-283`), then a second shoulder (`:284-285`).
- The look pass makes its glow from decoded display values: `smoothstep(0.12,0.55)` in `vj-fx.js` PREFILTER. Its grain and dither are re-seeded every frame (`u_seed = frame*7.13`).
- Play accepts only its own uniform list, with constant loop bounds (`arsenal/presets.py`). So any new VJ data must travel in the 16×6 strip (row 2 has free texels 9–14), never as new uniforms. Unknown header keys are ignored, so new header fields are safe for Play.
- The audit's two seams are real:
  - Hyperspace: `vj-hyperspace.frag:160` puts `atan` into value noise, so the noise jumps at ±π.
  - Particle Galaxy: `vj-particle-galaxy.frag:148` uses `sin(pattern·0.5)`, which takes half the angle.
- The house display chain exists (`glsl/post/display-out.glsl`), and so does `tmPbrNeutral` (`glsl/colour/tone.glsl:59`). There is no `tmAgX` and no 2D star shape yet.

**My own measurement.** This corrects a misread in the studies.

The Q-dance study's "near-black" means linear luminance below 0.01, which is roughly sRGB code 25. By that loose test, several of our grooves are already 60–98% "near-black". So the gap is not "too much light". It is grey instead of black, and no white-hot. I re-measured the references and our audit frames on stricter, LED-relevant tests:

| | True black (max channel ≤ 3) | Lit (luma > 64) | White-hot (any channel ≥ 250) | Colour families ≥ 10% |
|---|---|---|---|---|
| Qlimax 2024 LED content renders, Q20–Q25 (TWOFIFTYK) | **34–48%** | 5–17% | 0.03–0.6% | 1 (two renders show 3) |
| Qlimax and Defqon.1 stage photos at climax (Q10–Q12, Q16–Q17, D05–D12) | 0–13% (photos of a hazy hall) | 21–52% | 1.5–26% | 2 (a few 4) |
| **Our 13 scenes, groove** | **0.0% in all 13** | 0.1–36% | **0.00% in all 13** | 1–4 |

Our scenes are LED content, so the TWOFIFTYK renders are the class to compare against. The stage photos tell us about climaxes and flood moments, not about black levels.

---

## 1. The headline bar

A reviewer applies this checklist to the before/after contact sheets and to the scorecard from the receipt (section 5). "Headline" thresholds apply to scenes whose role is `headline`. Piano/worship scenes get the relaxations noted.

1. **Composition: one hero, in the centre, in a ring.**
   - **Pass if:** one symmetric subject, centred within ±3% of the width, with its centre 40–50% down from the top. The hero is 35–90% of the frame height. The side thirds carry only echoes or texture. Strict mirror symmetry by default, with a left-right difference under 3% at quiet and groove. The bottom 20% stays dim, because the DJ booth and crowd hide it and beams dim below the audience line.
   - **Evidence:** the Qlimax frames all have one symmetric central subject. The 2024 LED layout is a central disc plus three panels each side (I saw this in the renders). The ILDA practice of dimming below the audience is in the festival-lessons file.
   - **References:** Q19, Q21, Q23, Q25, Q01, D06.
2. **True blacks and contrast.**
   - **Pass if:** true black (max channel ≤ 3/255) is at least 60% at quiet, 70% in an anti-climax and 30% in the groove. The black floor (5th-percentile luma) is ≤ 2. No room colour: unlit means exactly 0.
   - **Evidence:** the TWOFIFTYK renders measure 34–48% true black; ours measure 0%. Syncronorm (light against darkness), Vision Impossible (dark and immersive) and Jacobs (black is your friend) agree. LED walls emit light, so code 0 is about zero nits, and dimmed walls lose bit depth near black. That is why the rule is black plus lit structure, not slow near-black gradients (Brompton, via the craft study).
   - **References:** Q20, Q25, Q13, Q19.
3. **Depth.**
   - **Pass if:** at least two of these cues show on the sheet:
     - near black occluders overlapping a lit far layer;
     - perspective converging on the hero;
     - parallax between two or more layers;
     - a far layer with lower contrast;
     - shading or shadow on the hero.
   - **Evidence:** AVIXA's cue list; Backbone's two LED layers with a translucent front; the speaker stacks that hang in front of the light in Q17.
   - **References:** Q17, D09, Q11, Q16.
4. **Lighting: light has a source.**
   - **Pass if:**
     - every beam or glow traces back to a visible origin (a head, the hero, a rim);
     - air is lit only where a beam passes through it, with no ambient wash;
     - cores go white-hot inside coloured halos: white-hot pixels 0.05–1.5% in the groove, 0.2–6% on a kick or drop;
     - beams radiate from the hero.
   - **Evidence:** ILDA and Laserworld (beams exist only in haze); Corbin Sharpe (designing for how light reads in haze); the Q-dance study's rule that everything radiates from the hero.
   - **References:** Q16, Q17, Q24, Q10.
5. **Colour discipline.**
   - **Pass if:** at most two hue families make up 10% or more of the saturated lit pixels, plus white or warm white. The palette is held for a phrase and changes at sections. Red is held, never flashed; white or gold carries the flash.
   - **Evidence:**
     - Ed Warren works with two colours at once (lessons file, [H]).
     - The Q-dance preview-frame timelines show single-hue runs of 8–17 s, which fits 8-bar phrases at 150 BPM.
     - My family counts: most reference frames have 1–2 families.
     - The saturated-red flash rule in BT.1702 and WCAG.
   - **References:** Q19 (one family), Q24 (teal and green), Q17 (red and orange).
6. **Fidelity and anti-aliasing.**
   - **Pass if:**
     - no stroke under 1.5 px at 1080p (2 px preferred), with analytic coverage on every edge;
     - no angle-wrap seams, no step-count contours, no moiré, no banding (static dither);
     - no dotted trail copies, and every decay measured per second.
   - **Evidence:** the audit crops (the Hyperspace seam, the Lissajous facets, the Geometry Hall floor contours, the dotted note trails). LED pixel grids and cameras shimmer on thin, high-contrast lines (doitvision, [M]).
   - **References:** the audit crops, as the "before".
7. **Kick-locked motion.**
   - **Pass if:**
     - the kick changes the world within one frame of the beat (scale, aim, position or shape);
     - the black floor rises by no more than 2 codes on the kick;
     - tails clear within one beat (400 ms at 150 BPM);
     - full-frame light comes only on the first kick of a phrase, and only through the gate;
     - the reverse bass is an off-beat inhale that the next kick cuts off.
   - **Evidence:** the lessons file (the kick is weight, not light; hit-stop; long tails at 150 BPM); the hardstyle kick anatomy from the Q-dance study ([M]); Vroomen and Keetels (a late picture is noticed first).
   - **References:** Q10 and Q11 (fans and rings that move), the Q25 loop.
8. **The quiet state is still a composition.**
   - **Pass if:** with no music, the hero sits at rest (linework, embers or eyes), 0.2–5% of the frame is lit, at least 60% is true black, and something moves slowly. Light moving over a still object counts.
   - **Evidence:** the anti-climax frames Q13 and Q14; Q19; the 13-second TWOFIFTYK loop, where the object stays still while a highlight travels across it.
   - **References:** Q13, Q14, Q19, Q25.
9. **Pads read on top.**
   - **Pass if:** a pad is visible within one frame and lands inside the scene's world, from the scene's own rig points and in the section's palette. It adds no more than 0.04 to the mean linear luminance and no more than 25% to the lit area, unless it is a gated flood. It keeps at least half of the groove's true black, and its bright part is gone within about one beat.
   - **Evidence:** today pads 1 and 2 raise the mean 2.6–16× and paint the same yellow target and corner fan over every scene (audit, `overview--4-pad.png`). Jacobs warns against stacking layers; Pyrotecnico warns that repeated big effects wear out.
   - **References:** `audit\overview--4-pad.png` as the "before".
10. **The safety gate is untouched.**
    - **Pass if:**
      - every full-field flash goes through `FlashGate`, at most 3 per second;
      - CO2 and flood moments each spend a slot;
      - saturated-red area changes by less than 10% of the frame per 333 ms outside the gate;
      - no pattern of more than 5 light-dark stripe pairs covering over 25% of the frame oscillates or reverses (flow in one direction only, at low contrast);
      - a rest comes after about 5 s of flashing;
      - `vj2_verify` passes its flash test with the look on.
    - **Evidence:** BT.1702-3, WCAG 2.3.1 and the Epilepsy Society, all [H] in the lessons file.
11. **Chapters.** This one goes beyond the requested ten.
    - **Pass if:** the scene shows three visibly different states (anti-climax, groove, climax) and returns to the same look when a section comes back.
    - **Evidence:** the Q-dance study found that each edition's centre object changes form through the night and that its reveals are staged ([M]). Brad Schiller (lessons file): repeat a look when its section returns.

### The headline scorecard (the receipt computes it; the moments are listed in section 5)

| Measure | How | Quiet | Anti-climax | Groove | Kick +50 ms | Pad +100 ms | Drop "one" |
|---|---|---|---|---|---|---|---|
| True black | share of pixels with max(R,G,B) ≤ 3 | ≥ 60% | ≥ 70% | ≥ 30% | ≥ 0.85 × groove | ≥ 0.5 × groove | flood exempt; the "later" frame is back within 5 points of groove |
| Black floor | 5th-percentile luma (0–255) | ≤ 2 | ≤ 2 | ≤ 2 | ≤ groove + 2 | ≤ 6 | — |
| Lit | luma > 64 | 0.2–5% | 0.1–5% | 5–25% | ≤ 1.6 × groove | groove + ≤ 25 points | 15–45% without a flood |
| White-hot | any channel ≥ 250 | ≤ 0.5% | ≤ 0.5% | 0.05–1.5% | 0.2–6% | ≤ 8% | ≤ 10% unless a gated flood |
| Families | hue families ≥ 10% of lit pixels with saturation > 0.25 | ≤ 2 | 1 | ≤ 2 | ≤ 2 | ≤ 2 | ≤ 2 |
| Added light | mean linear luminance above groove | — | — | — | ≤ +60% | ≤ +0.04 absolute | gated |

Piano and worship scenes (role `piano`): families are free (pitch colours are the content), groove true black is at least 40%, and strokes are at least 2 px. These thresholds are [L] starting points, calibrated on the TWOFIFTYK renders and on the stage photos.

---

## 2. The shared look v2 (one lane, in the page)

### 2a. The scene contract v2: what every `.frag` does

1. **Output.**
   - When the strip says version 2 and the target is float, the scene writes scene-linear HDR light: finite, at least 0, passed through `simSanitize`, with no tone curve, no `pow` and no clamp.
   - Otherwise (Play, strip v1, or the RGBA8 fallback) it finishes through `displayOut`.
   - This makes merge order irrelevant: the old page and the new page both show it correctly.
2. **Exposure convention.**
   - Hero bodies 0.1–0.5 linear.
   - Halos 0.3–1.
   - Cores 4–20 (these go white-hot after the curve).
   - Unlit areas 0.
3. **The room is 0.** Any "air" is light scattered from a visible source.
4. **Trails** use a keep-per-second rate: `clkKeep(keepPerSecond, dt)` with `dt` from the strip (1/60 in Play). The 1.5/255 floor step applies only when the target is 8-bit.
5. **Colour.** Two families per section from palette slots 0 and 1, plus a white or warm-white core. Pitch colours appear only in piano scenes, or as accents under 2% of the area.
6. **The kick** comes in through the strip's kick envelopes (2c) and moves the world. The hero's own light may rise by up to 60% on a kick; the background never rises. Camera weight (zoom punch, shake, hit-stop) belongs to the impact pass in the page, so scenes do not shake themselves.
7. **Edges.**
   - Analytic coverage (`draw2/aa`) on every edge, with strokes of at least 1.5 px (2 px preferred).
   - Cone coverage (`ray/aa3` `aaConeCoverage`) on raymarched silhouettes.
   - Every function of `atan` must repeat exactly every 2π: use integer multiples of the angle, or sample noise on (cos, sin).
8. **Code hygiene.**
   - Constant loop bounds.
   - `core/compile` `unrollBarrier` on march loops, because ANGLE's D3D compiler unrolls loops and can freeze the first frame for seconds.
   - Any analytic glare must be shadowed too. The arsenal probe's glare shone straight through its monolith.
9. **New header fields.** Play ignores unknown keys, so these are safe.
   - `"output":"hdr"`
   - `"role":"headline"|"piano"|"both"`
   - `"rig":{"origins":[[x,y],...],"floor":y}` (where pad accents may originate)
   - `"accents":{"native":[pads]}` (pads the scene draws itself, which the overlay skips)
   - `"grade":"two"|"free"`
   - Keep `k5` named `trails`, so the page's trails fader still finds it.
10. **House code is composed, not pasted.**
    - Run `py -m arsenal shader lib compose <names> --target webgl2` and put its output into a marked "house kit" block at the top of the `.frag`. The file stays single and loadable in Play.
    - The composed header carries each module's version and sha256, and the receipt recomposes it to check it is current. Arsenal Finding 2: today the presets paste reduced copies, so a module fix never reaches them.
11. **Originality.** No Q-dance or Defqon.1 logo, emblem, name or replica set piece anywhere. Only our own sigils, masks and gates.
12. **Licence.** Never copy corpus code. Run `py -m arsenal shader licence-line` and get exit 0.
    - Known traps: `mainImage` boilerplate (the VJ host template avoids it), stock march-loop lines, and constant vectors such as `vec3(0.0,0.0,1.0)`, because numbers are compared by value.
    - Textbook idioms go into `licence_line_allow.json` only after review.

### 2b. The page pipeline, in order

Each set's output is brought to linear light first: legacy sets are decoded with `pow 2.2` (their own encode), HDR sets pass through. Then:
1. The transition mixes in linear light.
2. The composite:
   - runs the geometry operations unchanged (glitch, kaleidoscope, freeze, shock bend);
   - adds the accent overlay v2 in linear light;
   - **removes** the per-hit centre lift (`vj.js:283`);
   - **removes** the edge breath unless the metronome is switched on (`:282`);
   - **removes** the second shoulder (`:284-285`).
3. Bloom: a pyramid from the HDR composite.
4. The final pass, in this order:
   1. exposure (master brightness becomes EV, from −2 to +1 stops; today a multiplier caps white at 230/255);
   2. `tmStage(heat)`;
   3. the section grade, in OKLab;
   4. the vignette (`vigCorner`, at most 0.25);
   5. an exact sRGB encode (`colour/transfer` `srgbEncode`);
   6. invert (pad), the gated flash to white, and the kill multiplier (which must reach true 0);
   7. a static dither (`post/dither` `ditherOut`);
   8. the canvas.

The page builds these shaders from the house modules through `glsl/modlib.js`, the browser twin of the composer, rather than pasting GLSL into strings.

**The tone map: `tmStage`, a house function built from Khronos PBR Neutral, with two changes.**

- **Why Neutral.**
  - It compresses only the peak channel and drifts toward white along the colour's own line, so saturated laser blue, orange and red keep their hue as they get hotter. The craft study computed hue shifts of about ±13° for Neutral, against −38° to +40° for ACES and for clipping, where blue turns cyan and orange turns yellow just when a hit is hottest.
  - It is the identity below the knee, so existing scenes barely change.
  - A path to white also takes hot red cores out of the "saturated red" class sooner, which helps the flash rule.
- **Change 1: drift becomes `heat`** (0.15 → 0.8), driven by section. Low heat keeps colour exact in breaks; high heat whitens cores on drops. That is one big knob.
- **Change 2: the toe.** Neutral's min-channel toe (`tone.glsl:65-66`) darkens dim haze unevenly by hue. I computed it: neutral grey 0.02 becomes 0.0025 (8× darker) and 0.05 becomes 0.0156, while a saturated beam halo with a zero channel is untouched. White beams would lose their air while coloured beams kept theirs.
  - Replace it with a toe on the peak: `x *= p/(p + 0.0015)`, where `p = max(r,g,b)`.
  - This is monotonic and never changes hue. It sends the old floors to code 2 or below (0.0012 → 0.00053, about code 2) and keeps 93% at 0.02.
- **Knee:** 0.8. **Peak compression:** Neutral's formula.
- **Lane M** adds `tmStage` to `colour/tone.glsl` and a `curve 4` option to `post/display-out.glsl`. Both are additive, and nothing else changes.
- **Later:** one A/B against AgX plus a punchy look on the raymarched scenes, on the real output screen, chosen by Daniel's eye. AgX is not in the library yet, and its constants were not verified.
- **Rejected:** the ACES fit (hue skew, magnified on a big wall) and Reinhard (grey highlights).

**Bloom with a threshold.**
- Input: the HDR composite.
- Prefilter at half resolution: a soft knee on the maximum channel (threshold 1.0 scene-linear, knee 0.5), with a Karis average (1/(1+luma)) on the first downsample only, so stars don't flicker in the glow.
- Six levels, from 1/2 to 1/64 resolution: dual-filter 5-tap downsamples and 3×3 tent upsamples.
- Two lobes:
  - **tight** (levels 1–2): the hot-core halo, always on, weight 0.6;
  - **wide** (levels 4–6): air, from 0 to 0.5 by section.
- **Keep the existing cap** on the glow's mean contribution (0.025), now measured in linear light.
- **New floor test:** bloom may lift the 5th-percentile luma by at most 1 code.
- **Sources:** Bjørge, SIGGRAPH 2015; Jimenez, SIGGRAPH 2014 (both via `research/reviewed/shader-school-2026-10-13/color-post.md`).

**Haze.** None from the page. A global haze lifts black, which breaks bar item 2. Haze lives inside scenes, as light scattered from their own beams over a static density that moves in units per second. The wide bloom lobe is the only global "air", and it is capped. A half-resolution volume pass (craft §4.4) waits until Rose Window's analytic in-scatter has failed its acceptance.

**Grain, vignette and dither.**
- Grain is **off** on the wall. Today it is re-seeded every frame (`vj-fx.js:180`, seed at `:320`). The audit measured fine noise roughly tripling in flat dark areas, and Daniel had per-frame grain removed once before.
- The vignette stays at 0.25 or less and touches only the outer ring.
- The dither is static (one mask) and is the last operation before the write.
- Colour split (chromatic aberration) only on pads hit at velocity 0.8 or more, capped at 3 px at 1080p. Never on the kick: the audit crop shows red and blue fringes on thin beams.

**One grade per section.** This is analytic and done in OKLab; a lookup table can come later.
- Saturation in linear light (`grdSaturation`).
- Exposure.
- A **two-hue pull**: for pixels with chroma above a small threshold, pull the hue toward the section's two anchor hues, weighted softly so no hue edge appears. Near-neutrals (white, bone) are left alone.
- Scenes with `"grade":"free"` (the piano ones) skip the pull.

Starting points [L]:

| Section | Hues | Pull | Heat | Saturation | EV | Wide bloom | Darkness |
|---|---|---|---|---|---|---|---|
| Intro | key only | 0.8 | 0.2 | 0.9 | −0.5 | 0 | 0.85 |
| Anti-climax | red #ab0a1c + bone | 1.0 | 0.3 | 1.0 | −0.5 | 0 | 0.9 |
| Break / melodic | P9 brass or P4 jewel | 0.6 | 0.15 | 0.85 | −0.3 | 0.2 | 0.6 |
| Build | the drop's pair, draining to white in the last bar | 0.7 | 0.2 → 0.6 | 0.8 → 1.1, then 0.6 in the last bar | 0 | 0.1 → 0.4 | 0.7 → 0.4; last beat black |
| Drop / climax | the section's pair | 0.7 | 0.6–0.8 | 1.1 | 0 | 0.5 | 0.3 |
| Outro | the anti-climax or intro look exactly | | | | | | |
| Piano / worship role | free | 0 | 0.15 | 1.0 | 0 | 0.15 | 0.5 |

Palette hex values come from the Q-dance study's table P1–P9, which it measured from the references. In the headline role, the palette changes at phrase and section boundaries. Chords may nudge hue by up to ±15° (lessons rule 6). The piano role keeps a palette per chord.

**Accent overlay v2.**
- **Pad 1, shockwave:** one analytic ring, 2–4 px core, in hue A with a white-hot core. Motion blur is analytic (the ring's width stretches by its speed times frame time), not stacked feedback copies. Bright for at most one beat.
- **Pad 2, laser burst:** origins are dealt from the scene's `rig.origins`, beams aim into the frame, dim below `rig.floor`, and use hue B. A beam's sweep within a frame is drawn as an analytic wedge, not as max-of-trail ribbons.
- Pads the scene lists as native are skipped.
- The overlay adds at most 0.04 mean linear luminance unless the flash is gated.

### 2c. Strip v2: free texels in row 2; VERSION becomes 2

| Texel | x | y | z | w |
|---|---|---|---|---|
| 9 | dt (s) | section id (0 groove/unknown, 1 intro, 2 break, 3 build, 4 drop, 5 anti-climax, 6 outro) | section progress 0..1 | bar within the phrase |
| 10 | heat 0..1 | darkness 0..1 (1 = hero only) | gated flood envelope 0..1 | float target 0/1 |
| 11 | kick click (one frame) | kick punch (spring value) | kick tail (0.2–0.4 s) | off-beat inhale (cut at the kick) |
| 12 | screech (high-band envelope) | build tension (snare-roll density) | first-kick-of-phrase pulse | raw (0) to euphoric (1) |
| 13 | hue A (turns) | hue B (turns) | grade pull | reserved |
| 14 | Lissajous ratios (a, b, c, d) from the CPU | | | |

- Until a section detector exists, sections come from transport marks (Daniel taps "drop next" or "break"). Our beat tracker beat_a does not claim where bar 1 falls (lessons file). Every scene must look right with section 0 and no marks.
- The page also needs a 150 BPM hardstyle demo with section marks, for receipts.

### 2d. Costs and modules

Estimates for an RX 6600 class card at 1080p, not GPU measurements (all of this has run on SwiftShader only):

| Piece | Estimated ms |
|---|---|
| Composite (accents, kaleidoscope, freeze) | 0.2–0.5 |
| Overlay v2 (particles capped) | ≤ 0.5 |
| Bloom pyramid | 0.2–0.4 |
| Final pass (exposure, `tmStage`, OKLab grade, vignette, encode, dither) | ≤ 0.1 |
| **Look v2 total** | **about 1–1.5**, leaving about 5 ms for one scene and about 3 ms for the cued scene during a transition, inside a 16.7 ms frame |

Daniel's RX 9070 XT is about 2.7 times faster.

Modules: `colour/tone` (`expose`, `tmStage`), `colour/oklab`, `colour/grade`, `colour/transfer`, `post/vignette`, `post/dither`, `post/display-out`, `motion/envelope` (`envFlashSafe`), `sim/feedback` (`simSanitize`), `core/clock`.

---

## 3. Per scene: all 13

The file ids stay the same, so pad maps, the tour and receipts keep working. Only the header `name` and the blurbs change. Every scene also meets the contract in 2a and the scorecard. The acceptance lines below are the extras for each scene. Budgets are estimates in operations per pixel and GPU milliseconds at 1080p on an RX 6600 class card.

| Scene | Verdict | New name | Role | Priority |
|---|---|---|---|---|
| laser-cathedral | upgrade (rebuild in 3D) | Rose Window | headline | 1 |
| hyperspace | upgrade | Ring Portal | headline | 2 |
| reactor | upgrade | Eclipse | headline | 3 |
| geometry-hall | upgrade | Star Cage | headline | 4 |
| liquid-chrome | upgrade (rebuild in 3D) | Relic | both | 8 |
| fractal-bloom | upgrade | Star Flower | headline | 9 |
| synthwave-grid | **replace the look** (Daniel's call) | Laser Sea | headline | 10 |
| led-wall | **replace the look** (Daniel's call) | Torn Red | headline | 11 |
| particle-galaxy | upgrade | Galaxy Finale | both | 12 |
| chord-constellations | upgrade (restyle) | Sigil | both | 13 |
| aurora-curtains | keep and polish | Vigil | worship | 14 |
| lissajous-chords | keep, fix, add a laser-graphics mode | Lissajous Chords | piano | 15 |
| note-rain | keep and polish | Note Rain | piano | 16 |

Priorities 5–7 are the three new scenes in section 4.

### 3.1 vj-laser-cathedral → "Rose Window" (upgrade; highest ceiling)
- **Target.** You look down a black nave at a rose window of our own tracery, the hero: centred 45% from the top and 55% of the frame high, with mirrored lancet windows either side. Lasers come from real heads on the floor line, the truss and the side towers. They cross in an X through the rose on drops and open as a crown from behind it. The air stays black until a beam passes through it. Borrows from Q16 (white beams bursting from the rose), Q17 (laser X through the rose, black speaker stacks in front), Q18 (tracery and sparklers), Q24 (beams only, LED almost off) and Q21 (faceted star in the window).
- **Geometry.**
  - A camera on the nave axis with a narrow field of view (about 35°), for monumentality.
  - The rose is an emissive disc on the far plane: `domKaleido` with 12 sectors, polar rings, and `latHex` cells with dark lead lines at least 3 px wide over jewel glass, around a star from `draw2/sigil`.
  - Two pointed-arch lancets per side.
  - Columns and hanging speaker boxes are pure-black occluders in front, giving depth by overlap.
- **Light.**
  - Twelve heads (one per pad) at real positions: 4 on the floor line, 4 on the truss, 2 on each tower.
  - 3D beams with analytic in-scatter (new `light/beam.glsl`: closest approach of the view ray to the beam axis, weighted by `phaseHG` with g between 0.5 and 0.7, so beams pointing at the camera glow more).
  - A static fbm haze, denser near the floor.
  - The columns shadow the beams behind them.
  - Idle beams are no longer always on. Their count follows the section and the darkness macro: 2 in an anti-climax, 4 in the groove, 12 in a climax. This fixes "there is no black to cut from".
- **Palette.** P4 jewel glass plus one beam key: orange (Q17), green (Q24) or white (Q16). Two families at most.
- **Camera.** Locked, with a slow push from 1.00 to 1.04 in breaks.
- **Music.**
  - The kick steps the beam foci. Keep this: it is the best beat grammar in the rig.
  - Click: the rose's lead lines go white for one frame. Punch: the rose star scales +4%. Tail: the glass brightens +35% over 300 ms.
  - Off-beat: haze density inhales ±10%.
  - Screech: fast, thin white scans from the truss heads.
  - Anti-climax: the rose is dark except a red ring line (Q19, Q13), with two thin beams.
  - Build: beams converge on the rose and two mirrored sparkler fountains rise; the last beat is black.
  - Drop: the X through the rose, plus a 12-beam crown from behind it.
- **Pads.** Each pad fans its own head from its real position (keep this). Native for pad 2.
- **Modules.** `groups/neon-line`, `light/glow`, `volume/phase`, `ray/camera`, `ray/intersect` (`ixBox`, `ixPlane`), `draw2/domain2`, `draw2/lattice`, `draw2/aa`, `noise/fbm`, `sim/feedback`, `core/clock`; new: `light/beam`, `draw2/sigil`, `draw2/pyro` (sparklers).
- **Learn from (corpus).** DtXfDr (detuned pinned strings; blur that grows toward the edges), tsScDG (the in-scatter weight; telephoto monumentality), WlVyRV (self-shadowing is what sells depth), MdsXWM (light behind a black occluder).
- **Budget.** About 3,000 operations per pixel, about 2 ms.
- **Accept.**
  - The rose is readable at quiet (0.5–5% lit, centred, 42–48% from the top).
  - The groove shows black occluders over lit beams.
  - Every beam ends at a visible head.
  - No beam above 30% brightness in the bottom 20%.
  - Groove true black at least 30% (0% today).
  - Pad frames keep at least half of the groove's black.

### 3.2 vj-hyperspace → "Ring Portal" (upgrade; best base, quick win)
- **Target.** Keep the streaking stars and the kick that stretches them, which is the one kick in the rig that changes the world. Add a portal of 6–8 rings studded with bulbs along a gently curving path, and make space black. Borrows from Q11 (rings receding toward the star, a beam through them), the Qlimax 2023 "void" story (Syncronorm) and D09 (an eye at the vanishing point).
- **Fix the seam.** Line 160 feeds `a/TAU·6` into value noise, so it jumps at ±π. Make every angular term repeat every 2π.
- **Remove the lift.** Drop the nebula's room lift and the constant floor at `:165`. The nebula becomes faint wisps near the rings (at most 0.02) or goes off.
- **Rings.** Exact ray-to-plane hits, at most 8 planes, with bulbs at least 2 px across.
- **Near dust.** A sparse, fast layer for parallax.
- **The vanishing point stays dark** (a small black disc behind the last ring), except on a jump. Feedback runs per second and in HDR.
- **Music.**
  - The kick stretches the streaks (keep this) and moves the rings forward one spacing on an eased step. Click: the bulbs go white for one frame.
  - Off-beat: the field of view inhales +2%.
  - Build: the rings converge. Drop: they stop dead and the streaks reach maximum.
  - Anti-climax: one distant red ring and sparse stars.
- **Pads.** Hyperjump stays, in the section's hues.
- **Palette.** P2 violet with amber (Q11).
- **Modules.** `ray/camera` (`camBanked`, `pathLissajous3`), `ray/intersect` (`ixPlane`), `draw2/sdf2`, `draw2/domain2`, `light/glow`, `hash/pcg`, `sim/feedback`, `core/clock`.
- **Learn from.** MfjyWK Starry planes (one path drives everything; exact plane hits; banking; the licence line applies even though it is CC0), wsl3WB (layers on a conveyor).
- **Budget.** About 1,500 operations per pixel, about 1 ms.
- **Accept.**
  - In the 1:1 crop left of the vanishing point, no row-to-row jump above 4 codes.
  - Groove true black at least 30%, with p5 at most 2 (25 today).
  - At least 4 rings visible.
  - The median of the centre 5% at most code 20 in the groove.

### 3.3 vj-reactor → "Eclipse" (upgrade)
- **Target.** A perfectly black disc. A corona escapes its rim from emitters hidden behind it. A thin spiked crown sits behind it, in the void. At rest, a thin red ring; on the drop, the corona blazes molten white-gold. Borrows from Q19, Q13, Q23 (a spiked ring), Q04 (a flame halo) and Q12.
- **Geometry.**
  - The disc's radius is 0.17 of the frame height, centred 45% from the top, and it is exactly 0.
  - The corona: 48 emitters just inside the rim, glowing with two-Gaussian falloff past the edge (the MdsXWM trick). Each sector's strength comes from a band, mirrored: bass at the bottom, highs at the top.
  - The spiked ring (`draw2/sigil`) sits at 0.32 of the frame height, with a 2–3 px stroke, lit only by the corona.
  - The x-ray shells stay only as thin, crisp latitude and longitude lines, and only in climaxes. The pink blur goes.
  - The bass no longer tints the whole room.
- **Palette.** P1 held red in anti-climaxes, P2 for the opener, P3 in climaxes.
- **Music.**
  - Click: a white rim for one frame. Punch: the spiked ring scales +5% on a spring. Tail: the corona brightens +40% over 300 ms.
  - The first kick of a phrase in a drop sends one crisp analytic shock ring, never stacked rings.
  - Off-beat: the corona inhales +3%.
  - Screech: plasma crackle from the rim, at most 2% of the frame.
- **Pads.** Twelve prominences, comet-shaped flares at the clock positions, kept within 1.6 times the disc radius.
- **Modules.** `draw2/sdf2`, `draw2/sigil`, `draw2/domain2`, `light/glow`, `colour/palette`, `groups/glow-xray`, `hash/pcg`, `sim/feedback`, `core/clock`.
- **Learn from.** MdsXWM, XsjXRm, l3cfW4.
- **Budget.** About 1,000 operations per pixel, ≤ 0.7 ms.
- **Accept.**
  - Disc pixels are code 0 at every moment.
  - True black at least 60% in the groove and 85% in an anti-climax.
  - In the 1:1 crop, the ring's halo is no wider than 3 times its stroke.
  - At most one shock ring visible.
  - The red-area rule holds.

### 3.4 vj-geometry-hall → "Star Cage" (upgrade)
- **Target.** A hall of black zigzag trusses converges on a circular light "eye" at the vanishing point. The chord's solid hangs in a cage of rings, backlit, so the eye's rays stream around it. Borrows from D09 (sawtooth trusses converging on a circular eye), D10 (the same hall in red), Q11 (a star object in rings) and Q05.
- **Geometry and light.**
  - The trusses are triangle-wave beams (`shpTri`) with small bulbs, drawn as black silhouettes against the lit air.
  - The eye is an emissive ring on the far plane, 45% from the top, and it is the key light.
  - Rays from the eye are scattered along the view rays, shadowed by the solid's analytic bound. The arsenal probe's lesson applies: glare must be shadowed.
  - The solid keeps the chord-to-solid mapping. It is 35–45% of the frame height, dark glass with edges at least 2 px, using `aaConeCoverage`.
  - The floor becomes an analytic plane, which fixes the step-count contours.
  - The grey fog goes. Only the eye lights the air.
- **Music.**
  - The solid snaps on the beat (keep this). The eye's tail lasts 300 ms. The truss bulbs chase one step.
  - Build: the dolly speeds up and the rings converge. Drop: the dolly stops dead and the eye flares.
  - Anti-climax: the eye is a thin red ring.
- **Palette.** P6/P3 orange-red, or P2 violet.
- **Modules.** `ray/march`, `ray/normals`, `ray/aa3`, `ray/intersect`, `ray/camera`, `sdf/shapes` (`sbPolyhedron`), `sdf/domain3`, `volume/phase`, `volume/integrate` (`volStepScatter`), `light/glow`, `core/compile` (`unrollBarrier`), `core/shaping`.
- **Learn from.** NlK3Wt, 4tcXRr (edges glowing by step count), tsScDG, WlVyRV.
- **Budget.** ≤ 4 ms: 64 bounded march steps plus 16 in-scatter steps with static jitter.
- **Accept.**
  - At least 3 converging truss lines are readable.
  - The eye's centre is 42–50% from the top.
  - Groove true black at least 25% (0% today, floor at 22).
  - No floor contours and no notched edges in the 1:1 crop.

### 3.5 vj-liquid-chrome → "Relic" (upgrade, rebuilt in 3D)
- **Target.** One hero: a relic of black chrome or brass (our own faceted star medallion), still at the centre while light travels over it. In builds it melts into liquid-metal blobs that orbit and converge. On the drop they snap back into the relic with two glints. Borrows from Q25 (brass Flower of Life: the object stays still, a highlight travels, two glints fade over about 0.5 s), Q21 (a faceted star), Q20 (black chrome) and Q-dance's chapter transformations.
- **Geometry.**
  - Raymarched: the relic is a 2D star profile (`draw2/sigil`) extruded with a bevel.
  - The liquid state is 5–7 spheres joined by smooth union.
  - A "melt" value morphs between the two, driven by section, with spring overshoot on the snap.
  - An `ixSphere` bound skips about 70% of the pixels.
- **Material.** Fresnel with a coloured F0 (brass), or a neutral F0 of 0.25 (black chrome), under 3 tube lights that travel, over a black floor. Silhouettes use cone coverage.
- **Music.**
  - On the first kick of a bar: two glints that rise and fade over 0.5 s.
  - Punch: the relic rotates 1/16 of a turn on an eased step.
  - Tail: the strips brighten +30%.
  - Off-beat: the strips breathe.
- **Pads.** In the liquid state, pads throw metal drops in from the rim (this survives from today). In the relic state, each pad lights one facet.
- **Palette.** P9 brass in breaks, P4 bronze, or black chrome with strips in the key colour.
- **Modules.** `sdf/shapes`, `sdf/combine`, `ray/march`, `ray/normals`, `ray/aa3`, `ray/intersect`, `light/fresnel`, `light/specular`, `light/env`, `groups/studio-object`, `core/compile`, `draw2/sigil`.
- **Learn from.** llK3Dy (keep reflections in HDR before any blur), 3XdXRr, 43jXWt, 4tcXRr.
- **Budget.** ≤ 3 ms on average, 5 ms at most.
- **Accept.**
  - One hero mass 40–70% of the frame height.
  - Groove true black at least 45%.
  - White-hot 0.1–1%.
  - Light travels at rest (the Guardian test in section 4: the silhouette is still while the brightest pixels move).
  - No stair-steps or brown halo on the silhouette.
  - The build and drop frames show liquid, then the relic.

### 3.6 vj-fractal-bloom → "Star Flower" (upgrade)
- **Target.** A white-gold star flower with a small hero star at its heart. It opens one level of petals at a time on the beat. At rest it is mostly black lace; at the peak comes a rare white bloom. Borrows from Q15 (white kaleidoscopic petals, the rare flood), Q03 (a feather fan), Q22 (fractal feathers) and Q04.
- **Changes.**
  - Fade out any level whose line spacing at that pixel is under 4 px, so there is no moiré.
  - Lines at least 2 px.
  - Smooth-min across the orbit traps, which removes the notches and wedges.
  - The centre star (12% of the frame height) is always present.
  - Break: 1–2 levels of bone linework. Build: one level per bar. Drop: full bloom with warm-white cores. A white flood happens only through the gated flood.
  - The kick pushes the petals outward +4%, instead of today's density swing from 8% to 42% lit.
- **Palette.** P2 violet with P3 gold, going white at the peak.
- **Modules.** `draw2/domain2` (`domKaleido`), `draw2/aa`, `draw2/sigil`, `light/glow`, `colour/palette`, `sim/feedback`.
- **Learn from.** MfjyWK (fine rings fading into glow instead of shimmering), Ms2XWc and XsSGDh (anti-aliasing).
- **Budget.** ≤ 0.6 ms.
- **Accept.**
  - No line under 2 px and no moiré.
  - Groove 8–25% lit with at least 40% true black.
  - The hero is visible at every moment.
  - Kick: density changes by at most 1.3×, while scale changes by 3–8%.

### 3.7 vj-synthwave-grid → "Laser Sea" (replace the look, keep the composition; Daniel's call)
- **Target.** Keep the audit's best composition: horizon, focal point, a perspective floor that lurches on the beat. Replace the outrun look. The sun becomes a dark ring "eye" at the vanishing point, and the neon grid becomes a sheet of laser light rolling toward you, in night blue or laser green, under a black sky. Borrows from D13 (ice-blue laser sea), D02 (green laser carpet), Q24, Q06 (cones landing) and D09.
- **Geometry.**
  - The sky is black.
  - The eye is a ring from `draw2/sigil` around a dark disc, 18% of the frame height, at eye level 45% from the top.
  - The mountains go, or stay as a black ridge with only a rim of light.
  - The sea is an analytic plane: a fan of lines from the eye, with low contrast between lines, so it reads as a glowing surface with fine structure.
  - The beat lurch survives: the wave front advances one wavelength per beat.
  - Keys send ripples from their column (the musical mapping survives).
  - Climax: 4–6 beam cones from above land on the sea.
- **Music.**
  - Kick: a crest travels from the eye toward the camera, in one direction only.
  - Off-beat: the sheet's brightness inhales.
  - Pads fan out from the eye (native).
- **Palette.** P7 (#051083 → #1cbde6), or P5 green with one magenta pin.
- **Safety.**
  - The sea is a large striped area. Its lines only flow toward the viewer.
  - Michelson contrast between lines stays at or below 0.4 over more than 25% of the frame.
  - The crest band never covers more than 15% of the frame.
- **Modules.** `ray/intersect` (`ixPlane`), `draw2/sigil`, `groups/neon-line`, `volume/phase`, `noise/value`, `sim/feedback`, `core/clock`.
- **Learn from.** MfjyWK, DtXfDr, ldSfWV (a Lorentzian beam).
- **Budget.** ≤ 1 ms.
- **Accept.**
  - The sky is at least 80% true black, and the whole groove at least 35%.
  - Groove lit at most 25% (36% today).
  - The kick's lit ratio at most 1.3 (today 1.44, with the floor jumping from 19 to 35).
  - No reversing stripes.

### 3.8 vj-led-wall → "Torn Red" (replace the look; Daniel's call)
- **Target.** The dot matrix becomes a halftone screen. Big mirrored graphic shapes (a sun ring, sawtooth borders, a field split by a torn edge) are drawn as red dots of varying size on black, with small white bars as hit accents. This is the graphic register of the RED stage branding, in our own shapes. Borrows from D03 (torn red paper, sawtooth, halftone, stencil), D05's card, D12's torn overlays and D10.
- **What stays.** The cell grid, the 12 panels, one panel per pad, and the travelling chases. This is what Daniel plays today.
- **What changes.**
  - Dot size follows the tone of a shape field underneath. Pitch at least 8 px at 1080p, dots at least 3 px.
  - **Unlit dots are 0.** Today they show as grey dots.
  - The sawtooth borders shift one tooth on the kick.
  - The sun ring's dot tone pulses +15% in a ring travelling outward.
  - The torn edge breathes on the off-beat and sweeps across at a section change.
  - Red is held (#db0001 / #ee0406), white (#fbfcfc) is the accent, gold (#e89029) is optional.
- **Modules.** `draw2/domain2` (`domRepeat2`), `draw2/aa` (`aaFill`), `core/shaping` (`shpTri`), `noise/value`, `hash/pcg`, `draw2/sigil`.
- **Learn from.** The house Play preset `halftone-pop.frag` (our own).
- **Budget.** ≤ 0.5 ms.
- **Accept.**
  - Off dots are code 0, and there is no moiré in the 1:1 crop.
  - Groove true black at least 40%.
  - The red-area rule holds.
  - Families: red plus white (plus gold).

### 3.9 vj-particle-galaxy → "Galaxy Finale" (upgrade; finale and melodic role)
- **Target.** The galaxy as the last room of the night: a small white-gold core, black lanes between the arms, round stars and a slow camera tilt. The Qlimax 2017 temple ended on a galaxy, according to reviews [M]. It also borrows from Q05 and D01 (comet volleys, for the novae).
- **Fix the seam.** Line 148's `sin(pattern·0.5)` takes half the angle. Use only whole multiples.
- **Stars.** Round points at least 1.5 px, rotated analytically. The feedback rotation that smears them into "rice grains" goes.
- **Black.** No room colour, and true black between the arms.
- **Camera.** One turn of orbit per 32 bars.
- **Music.** The kick flares the core with a 300 ms tail. The novae become comet bursts (`draw2/pyro`).
- **Palette.** A gold core with violet arms.
- **Modules.** `hash/pcg`, `draw2/domain2`, `light/glow`, `ray/camera`, `draw2/pyro`, `sim/feedback`.
- **Learn from.** Xdl3D2 (one star per grid cell), XlfGRj Star Nest. Study only.
- **Budget.** ≤ 1 ms.
- **Accept.** No seam. Round stars at least 1.5 px. Groove true black at least 40%. At most 2 families.

### 3.10 vj-chord-constellations → "Sigil" (upgrade, restyled; piano, intro and anti-climax)
- **Target.** The chord draws a sacred-geometry sigil in bone or gold line on black:
  - the circle of fifths becomes a ruled double ring with rune ticks;
  - the chord's polygon becomes a thick gold line;
  - each note becomes a small four-point star.

  It fills 70% of the frame height and draws itself again at each chord change. Borrows from Q14 (a gold line mandala on the LED), the Q11/Q12 sigil cards and Q25's travelling light.
- **Lines.** 2.5–3 px (1 px today), and the figure is 70% of the height.
- **Colour.** Bone #bfae9f and gold #dbcab5. A knob decides whether pitch colours appear, only on the star cores.
- **Light.** A highlight travels along the drawn lines.
- **The pedal star's strings stay,** as thin gold threads.
- **Music.** The kick steps the outer ticks round one tick and clicks white on the polygon. At a chord change the old sigil fades without the frame going darker.
- **Modules.** `draw2/sdf2`, `draw2/sigil`, `draw2/aa`, `light/glow`, `sim/feedback`.
- **Learn from.** MfjyWK.
- **Budget.** ≤ 0.5 ms.
- **Accept.**
  - No line under 2 px.
  - The figure at least 60% of the frame height.
  - Groove 1–8% lit, with at least 70% true black.

### 3.11 vj-aurora-curtains → "Vigil" (keep and polish; worship and melodic break)
- **Target.** Curtains rising out of pure black over still, dark water, with two families per section and nothing that reads as landscape wallpaper. Borrows from Q25 (stillness with moving light) and the P9/P4/P7 palettes.
- **Hems.** Each hem fades out over about 3% of the height. The dark hills go: below the hems is black.
- **Water.** A soft horizon 72% from the top, with broken, static glints, instead of a hard line.
- **Pads.** Light shafts rising from inside the curtains, in their hues, instead of stage-light bars.
- **Music.** A hardstyle kick sends a brightness wave along the curtains. In worship, the sustain pedal slowly brightens them.
- **Modules.** `groups/aurora-band`, `atmos/aurora`, `colour/oklab` (`mixOklch` for the palette travel), `core/clock`.
- **Learn from.** ffG3Rc, XtGGRt (how far apart the sheets sit).
- **Budget.** ≤ 1 ms.
- **Accept.**
  - No step above 30 codes along a hem or along the horizon in the 1:1 crop.
  - At most 2 families.
  - Groove true black at least 40%.
  - A visible travelling wave, with the kick frame's mean at most 1.3× the groove.

### 3.12 vj-lissajous-chords (keep for piano and fix; laser-graphics mode later)
- **The downbeat must not darken.** Keep the old figure at full brightness until the new one is at least 50% drawn. The kick frame is at 0.61× of the groove today.
- **Facets.** Use 64 coarse segments, then refine the nearest 2 with 8 sub-segments each.
- **Chord analysis.** Move `chordVoices` out of the per-pixel loop: the strip's texel 14 from the page; until then, outside the segment loop.
- **Stroke and size.** Strokes 2–3 px, the figure 60–70% of the height, the graticule off by default.
- **Kick.** The figure scales +4% and steps its rotation.
- **Laser-graphics mode** for hardstyle: one colour (P5 green or red), white-hot head.
- **Budget.** From the most expensive scene (an estimated 2–5 ms) to ≤ 1.5 ms.
- **Accept.**
  - The kick frame's lit share is at least the groove's.
  - No creases in the 1:1 crop.
  - The SwiftShader cost probe at most half of today's.

### 3.13 vj-note-rain (keep and polish; piano)
- Remove the room colour.
- Bars at least 3 px.
- Draw the halo from each bar's own distance, which removes the ghost lines beside the bars.
- At a chord change, draw one thin line instead of the per-pitch checker stripe.
- **Budget.** ≤ 0.5 ms.
- **Accept.** At least 70% true black. No stripe pattern at a chord change.

---

## 4. Three new scenes in Q-dance's grammar (prototype now)

I chose these from the references, not from the examples in the task.
- **Masks** recur in at least eight of the references: Q01, Q03, Q04, Q07, Q08, Q20, D04, D06/D07. That makes the mask the most frequent kind of hero.
- **Fire** and **pyro finales** carry Defqon.1's rituals and Qlimax's flames.
- **Power Hour** is a daytime carnival with confetti, by the study's evidence, so it is not a shader look. Its red, black and gold register lives in Ritual Fire's P6 option and in Torn Red.

Each scene below is the full spec. The same text is in NEW_SCENES_JSON.

### 4.1 vj-ritual-fire: "Ritual Fire"

**Answers to:** Q09 (mirrored flame jets at the base of a hanging ornament), Q23 (a sigil in a fire wreath with framed fire side panels), Q02 (the LED carries the fire), Q04 (a hero inside a flame mandala), Q19 and Q13 (the red symbol alone in black, for the anti-climax), D10 (the all-red hall).

**Target.** A sigil of our own design (a seven-point star in a double ring with a band of tick-mark runes) hangs dead centre, its centre 44% from the top and its ring 55% of the frame height, drawn in bone line on black. A wreath of fire breathes around it. Below it three mirrored pairs of flame jets stand on the floor line and fire in pairs, only when spent. The outer sixth of each side holds three framed fire panels that echo the jets. Embers rise through still air. At rest it is a red-and-bone symbol in the void; at the drop it is molten fire with black between the tongues.

**Geometry** (2D, centred space p = (uv − 0.5)·(aspect, 1), strict mirror on x unless k8 is raised):
- **Sigil:** a ring (annulus) with a 2.5 px stroke; a 7-point star polygon (new `draw2/sigil.glsl`) with a 3 px stroke; a rune band of 36 ticks by polar repeat. Every edge goes through `aaStroke`.
- **Wreath:** a polar flame field in which the distance above the ring is the flame's height.
  - 14–20 tongues, an even count so it mirrors.
  - Turbulence grows with height.
  - Channels are overdriven through `palHeatPowers`, so colour runs ember → orange → yellow → white with no brown.
  - Threshold the field so black shows between the tongues.
- **Jets:** 3 pairs at ±0.20, ±0.36 and ±0.52 of the frame width from centre, based on the floor line 80% from the top. Each is a tapered column 2–4% of the frame width wide and up to 45% of the frame high, by velocity. Noise is advected upward at a rate in units per second.
- **Side panels:** 3 squares per side inside the outer 17% of the width, with a thin bronze frame (#8e7165) and fire inside at 25% intensity at rest.
- **Embers:** 2 layers of a cell-grid gather (`hash/pcg` `cellU2`).
  - At most 1 ember per cell.
  - Rising 0.08–0.2 frame heights per second, with a slow sideways drift (`noise/warp`).
  - A head plus an upward comet tail, flickering exponentially.
  - At least 1.5 px wide, and no more than 250 visible.

**Light.** Only the fire emits; the room colour is exactly 0. The jets light a thin floor glow (1/d falloff), and the sigil's ring catches the wreath as a rim. No haze is painted: the only air is a soft glow term around each jet, bounded to its box. Output is scene-linear HDR under the strip-v2 contract (no tone curve, no `pow`, no clamp beyond `simSanitize`). In Play or with strip v1, it finishes through `displayOut`.

**Palette.**
- Anti-climax: P1 (blood red #ab0a1c held, bone #bfae9f lines, ember #d9534d).
- Groove and climax: P3 molten (#d63b09 → #ea7720 → #fec141, core #fff3d6).
- Defqon register: P6 (red #db0001 with gold #e89029).
- Fire always comes from the heat ramp. The section hue tints only the sigil line and the base of the flames.

**Camera.** Locked and symmetric. No shake inside the scene: the page's impact pass owns camera weight.

**Music** (strip v2 fields; fall back to `gPulse`, `u_bass` and `u_high` when absent):
- **Kick:**
  - click: the sigil line goes white-hot for one frame (thin, at most 3 px);
  - punch: ring and star scale +4% on a spring (6 Hz, damping 0.4);
  - tail: wreath brightness +40%, decaying over 300 ms, so it is gone within one beat at 150 BPM.
- **Off-beat (reverse bass):** the wreath inhales (tongue height +8%). It is cut instantly at the next kick when the style is raw, or released over 35 ms when it is euphoric.
- **Screech (high band):** thin crackle along the star's edges, white or acid green, at most 2% of the frame. Each bolt's offset follows a triangle wave; take the maximum of bolts, never the sum.
- **Build:** embers multiply with the snare roll; pilot flames appear at the jet bases; the sigil line heats toward orange. On the last beat before the drop everything except the pilot flames goes to zero (one beat of black).
- **Drop (the one, the first kick of the phrase):** all three jet pairs fire together for 1.2 s, the wreath goes full molten and the side panels flare. After that the jets fire only on pads or on the first kick of each phrase (rationed).
- **Anti-climax:** the sigil in red line, one pilot pair, sparse embers. At least 85% of the frame black.
- **Pads:** pads 1–3 fire jet pairs (outer, middle, inner); pads 4–6 flare the left panels, the right panels, or both; pads 7–12 throw ember bursts from the ring at the pad's clock position. Velocity sets height and count. Declare accents native for pads 1 and 2, so the page's generic shockwave and laser stay off.

**Knobs.** k1 fire height, k2 embers, k3 wreath, k4 jet reach, k5 trails (ember tails, keep per second), k6 side panels, k7 heat bias, k8 symmetry.

**House modules.** `draw2/sdf2`, `draw2/sigil` (new), `draw2/domain2` (`domToPolar`, `domKaleido`), `draw2/aa`, `colour/palette` (`palHeatPowers`), `light/glow` (`glowHotCore`, `glowTwoGauss`), `noise/value`, `noise/fbm`, `noise/warp`, `hash/pcg`, `motion/envelope`, `core/clock` (`clkKeep`), `sim/feedback` (`fbDecay`, `simSanitize`); a new `light/fire.glsl` (flame column, polar wreath), written fresh.

**Learn from** (corpus, study only, no code):
- MdX3zr Flame: brightness from how long a ray lingers; channels clipping in order; turbulence growing with height.
- 3XXSWS: sine-octave turbulence and a tanh finish.
- l3cfW4 Starship: a lopsided falloff for comet tails; exponential flicker.
- MdsXWM Audio Eclipse: glow escaping past a black occluder.
- XsjXRm Plasma Globe: crackle from a direction that depends on radius; the maximum of bolts.

**Budget.** About 1,500 operations per pixel on average (the wreath about 150, the jets and panels only inside their boxes, the embers about 400). By the craft study's arithmetic that is under 1 ms at 1080p on an RX 6600 class card, and under 2 ms at the drop. These are estimates, not GPU measurements.

**Acceptance** (before/after sheet at 1080p, the 150 BPM demo with section marks, plus the headline scorecard):
1. Quiet and anti-climax: at least 75% true black. The sigil alone is lit, in one hue family plus bone.
2. Groove: at least 40% true black, at most 2 families, white-hot 0.05–1.5%.
3. Drop-one frame:
   - lit share 15–40%;
   - white-hot 0.3–5%;
   - at least 20% true black;
   - black visible between the flame tongues in a 1:1 crop.
4. Kick against groove: the ring's radius differs by 3–8%, and the black floor (p5) rises by at most 2 codes.
5. Outside a gated flood, the saturated-red area changes by less than 10% of the frame between any two frames 333 ms apart. Saturated red means R/(R+G+B) at least 0.8 and luma above 20.
6. In the 1:1 crop, flames run red → orange → yellow → white, with no brown or grey mud.
7. Embers are round and at least 1.5 px, with no visible grid. Their tails are continuous, not dotted.
8. With k8 = 0, the left-right mirror difference is under 3% at quiet and in the groove.
9. `arsenal/presets.py` lists no problems (so Play loads it), and `py -m arsenal shader licence-line` exits 0.

**Originality.** Our own sigil and layout. No Q-dance or Defqon.1 logo, emblem, name or replica set piece.

### 4.2 vj-pyro-finale: "Pyro Finale"

**Answers to:** D05 (a gold fan-pyro wall rising behind a totem in smoke), D08 (pink fans behind the stage with guard silhouettes), D11 (a vast white-gold comet fan), D01 (mirrored green and white comet volleys), Q12 and Q15 (the CO2 white-out on the peak hit), Q16 (radial beams from behind the hero), Q13 (the red ring in the void, for the anti-climax).

**Target.** A monumental gate of our own design stands as a pure black silhouette against a sky lit only by the pyro. Behind it mirrored volleys of gold comets climb and burst, and a crown of laser beams opens from behind its central eye. On the drop's first beat a CO2 white-out (a gated flood) swallows the frame and clears into a two-colour finale. At the end it cuts to black.

**Geometry** (2D in parallax layers, strict mirror):
- **Gate:** a stepped tower with a central circular eye and two swept blades either side, built from boxes, rounded boxes and a circle. Its base is on the floor line 82% from the top and its top is 30% from the top. Its colour is exactly 0, except a rim line of at most 3 px on its upper edges, lit by whatever burns behind it.
- **Comets:**
  - Up to 12 per side, launched from emitters behind the gate along rays 20–80° above horizontal.
  - Ballistic: position = start + velocity·t + 0.5·gravity·t². This is a pure function of the time since launch, so no state is kept.
  - A white-gold head (`glowHotCore`) with a lopsided tail along the velocity.
  - At the apex, a burst of 12–24 sparks: peony, willow or crossette, dealt per volley from a deck. The sparks fall under gravity and fade over 1.2–1.8 s through the heat ramp into the section's accent colour.
- **Laser crown:** 8–16 beams from a point just behind the eye. The spread opens from 10° to 120° over one beat at the drop. A neon core with a Lorentzian halo, brighter toward the camera (`volume/phase` `phaseHG`, g = 0.6). At most 20% brightness below the floor line.
- **Smoke:** a very slow, static fbm band behind the gate. It moves in units per second and is never re-seeded. It is lit only by the comets and bursts (the sum of their glows at quarter strength), and is black when nothing burns.
- **CO2:** six mirrored floor jets. Their plumes rise with an 80 ms attack and fade over 1.2 s, in warm white #fff3d6, with density from warped noise. Full strength comes only through the page's gated flood envelope. Without a grant the plumes render at no more than 20%, which is never a flash.

**Light.** Only the pyro, the beams and the CO2 emit; the room colour is 0. Output is scene-linear HDR under the strip-v2 contract, with `displayOut` in Play.

**Palette.**
- Build: P3 molten gold (#e89029, #efbc62).
- Climax: P8 pink pyro (#85063f, #c33661, flash #d3797e) or P6 red and gold, by section.
- Finale: warm white and gold.
- Anti-climax: P1, a thin red ring in the gate's eye and nothing else.

**Camera.** Locked wide. During volleys, a slow crane-up of 1–2% over 8 bars. The page owns hit-stop and shake.

**Music.**
- **Build:** the launch rate doubles every two bars with the snare roll, with small, low bursts. Colour drains toward white in the last bar. On the last beat before the drop the scene goes to zero (one beat of black).
- **Drop, the one:** the crown opens, a full mirrored volley launches, and the CO2 white-out is requested through the gate.
- **Climax groove:** volleys only on the first kick of each bar (rationed). The crown's aim steps on each kick.
- **Kick:**
  - click: the gate's rim line flashes white for one frame;
  - punch: the crown spread widens 5° on a spring;
  - tail: comet heads +30% over 300 ms.
- **Off-beat:** the smoke's backlight inhales +15%, cut at the next kick.
- **Screech:** thin white crackle between the crown's beam tips, at most 2% of the frame.
- **Anti-climax:** the gate black, its eye a thin red ring, single slow comet pairs. At least 85% black.
- **Outro end:** everything to black over one beat, and hold.
- **Pads:** pads 1–6 launch comet pairs, outer to inner, with velocity setting apex height and spark count. Pads 7–10 choose the burst type of the next volley. Pads 11 and 12 stay with the page (kill, next). Declare accents native for pad 2: the crown replaces the generic laser burst.

**Knobs.** k1 volley size, k2 burst size, k3 crown, k4 smoke, k5 trails (keep per second, spark tails only), k6 CO2 strength (still gated), k7 gravity, k8 symmetry.

**House modules.** `draw2/sdf2`, `draw2/aa`, `draw2/domain2`, `light/glow`, `groups/neon-line`, `volume/phase` (`phaseHG`), `noise/fbm`, `noise/warp`, `hash/pcg`, `colour/palette` (`palHeatPowers`), `motion/envelope` (`envRamp`; the gate's grant arrives through the strip), `core/clock`, `sim/feedback`; a new `draw2/pyro.glsl` (ballistic comet, burst and ember helpers), written fresh.

**Learn from** (corpus, study only, no code):
- l3cfW4 Starship: comet tails by lopsided falloff; exponential flicker; square, then tanh.
- WlVyRV Dry ice 2: fog as a height map that emitters carve, for the CO2.
- MdsXWM Audio Eclipse: light escaping past a black occluder, for the gate's rim.
- 4lj3Ww: shafts from a pattern that depends only on direction, for the air around the crown.

**Budget.** About 2,500 operations per pixel on average. Every burst is bounded by its radius, so pixels outside it skip it. Under 1.5 ms typical and under 3 ms at the drop, at 1080p on an RX 6600 class card (estimates).

**Acceptance** (before/after sheet at 1080p, the 150 BPM demo with section marks, plus the headline scorecard):
1. Anti-climax: at least 85% true black, lit 0.1–3%, one family (red).
2. Build: the lit share rises at every two-bar step. The last beat before the drop is at least 95% true black.
3. Drop one, with the gate granting: the CO2 frame is at least 40% lit, and the receipt's flash log counts it as one flash. No more than 3 flashes in any second, pad 3 included. With the gate refusing: lit at most 25%.
4. Climax groove: at least 20% true black, white-hot 0.5–6%, at most 2 families plus white.
5. The gate's pixels are code 3 or below, except a rim at most 3 px wide.
6. Volleys are mirrored (left-right difference under 3% with k8 = 0). Tails are continuous, not dotted.
7. No beam is brighter than 20% of its peak below the floor line.
8. `arsenal/presets.py` lists no problems, and `py -m arsenal shader licence-line` exits 0.

**Originality.** Our own gate silhouette. No Q-dance or Defqon.1 logo, emblem, name or replica set piece.

### 4.3 vj-guardian: "Guardian"

**Answers to:** Q20 (a black-chrome biomechanical mask with glowing violet eyes between tracery side panels), Q01 (a face under a halo of LED arc segments), Q04 and Q03 (a mask inside a flame or feather halo), Q07 (a face backed by a fan of beams), D04 and D07 (the mask as the stage's centre), Q25 (light travelling over still metal).

**Target.** A colossal mask of our own design (symmetric, biomechanical, black chrome with engraved tracery) fills the centre of the frame inside a halo of arc segments. In the quiet only its two eyes burn in the black. In the groove light travels slowly across its still metal. On the drop the eyes open fully, the halo completes and a fan of beams opens behind the head.

**Geometry** (2.5D relief, frontal, strict mirror):
- **Mask:** a height field H(p) built from mirrored primitives:
  - forehead dome, brow ridge, nose ridge, cheek plates, mouth plate, chin;
  - eye sockets as ellipses tilted 12° and subtracted;
  - engraved grooves: concentric onion lines on the forehead plate, lattice tracery on the cheeks;
  - two biomechanical tubes along the jaw.

  The mask is 70% of the frame height, centred 48% from the top. Normals come from central differences of H (4 evaluations), only inside the mask's bounding box.
- **Eyes:** two almond-shaped emitters inside the sockets. Lids (a scale on their height) close during builds and open on the drop.
- **Halo:** a ring of 24–36 thick arc segments (`aaStroke`) behind the head, 90% of the frame height, with small bulbs. The segments chase in mirrored pairs from the top.
- **Beam fan (climax):** 8–16 beams from behind the head's centre, occluded by the mask's silhouette so they appear only around it.
- **Side panels (k6):** three square panels per side in the outer 15% of the width, with dim tracery icons. Texture only.

**Light and material.**
- Black chrome (a neutral F0 of 0.25, low roughness) under two or three tube lights, whose reflections travel slowly across the relief: one full pass across the face every 8–16 s.
- A rim light from the halo behind.
- In melodic breaks the material turns to brass (a coloured F0, palette P9) with one warm travelling highlight.
- The eyes emit (`glowTwoGauss`) and light nothing except a faint rim on their sockets.
- The room colour is 0, so unlit chrome reads as black.
- Output is scene-linear HDR under the strip-v2 contract, with `displayOut` in Play.

**Palette.**
- Opener: P2 celestial violet (eyes #540982 → #5435d9, halo periwinkle #696fc2).
- Defqon register: P6 red and gold.
- Green section: P5 (#05d987 with one magenta pin).
- Breaks: P9 brass.
- Eyes and halo carry the key colour; the beams carry the second hue or the same one.

**Camera.** Locked and frontal, with a slow push-in from 1.00 to 1.05 across a build. The page owns shake and hit-stop.

**Music.**
- **Kick:**
  - click: the eyes' inner cores go white for one frame;
  - punch: the halo scales +4% on a spring;
  - tail: eye glow +50%, decaying over 250–350 ms in the key colour.
- **Off-beat:** the eyes inhale (glow radius +10%). The next kick cuts this off when the style is raw; when it is euphoric it releases over 35 ms.
- **Screech:** thin crackle runs along the engraved grooves, white or acid, at most 2% of the frame.
- **Build:** the travelling lights speed up, one pair of halo segments lights per bar, and the lids narrow. The last beat is black except the slits of the eyes.
- **Drop:** the lids open, the halo completes, the beam fan opens over one beat, and the grooves ignite in the key colour for one phrase.
- **Anti-climax:** the chrome unlit, the eyes only, two halo segments at the top. At least 85% black.
- **Melodic break or worship:** brass, one slow highlight, soft warm eyes, no beams.
- **Pads:** pads 1–4 flare halo quadrants, 5–8 open sectors of the beam fan, and 9–12 light groove zones (forehead, left cheek, right cheek, chin), in the section's colours. Declare accents native for pad 2.

**Knobs.** k1 travel speed, k2 eye glow, k3 halo, k4 beams, k5 trails (keep per second, beams only), k6 side panels, k7 material (chrome to brass), k8 relief depth.

**House modules.** `draw2/sdf2` (`sd2Circle`, `sd2RoundBox`, `sd2Segment`), `sdf/combine` (smooth unions of the 2D distances), `draw2/domain2` (mirror, polar repeat), `draw2/lattice` (`latHex` for the tracery), `draw2/aa`, `light/fresnel` (`litFresnelSchlick` with a coloured F0), `light/specular`, `light/env` (`litStudioEnv` as the tube rig), `light/glow`, `groups/neon-line` (beams), `hash/pcg`, `noise/value` (static wear only), `motion/envelope`, `core/clock`.

**Learn from** (corpus, study only, no code):
- 3XdXRr: a dark mirror under a softbox that is brighter at its rim.
- 43jXWt: a giant softbox with a soft fade.
- 4tcXRr Alien Core: edges glowing by step count, for the grooves.
- MdsXWM Audio Eclipse: light escaping past a black occluder, for the halo and the fan behind the head.
- llK3Dy: keep reflections in HDR before any blur.

**Budget.** About 1,500 operations per pixel inside the mask's box (H at about 200 operations, times 4, plus shading) and about 400 outside. Under 1 ms on average at 1080p on an RX 6600 class card (estimate).

**Acceptance** (before/after sheet at 1080p, the 150 BPM demo with section marks, plus the headline scorecard):
1. Quiet and anti-climax: at least 85% true black. The two eyes are the brightest pixels. Lit 0.2–2%.
2. Groove: at least 40% true black, at most 2 families, white-hot 0.05–1%. The face reads in a quarter-size thumbnail (the reviewer's call).
3. Light over still metal: between two frames 1 s apart at rest, the mask's silhouette pixels are unchanged, while the centroid of the brightest 0.5% of mask pixels moves by at least 2% of the face's width.
4. Kick: eye brightness at least +50% at 50 ms, and back to the groove level within 400 ms. The black floor rises by at most 2 codes.
5. Left-right mirror difference under 3% at quiet and in the groove.
6. Drop frame: beams appear only around the silhouette, never across the face.
7. `arsenal/presets.py` lists no problems, and `py -m arsenal shader licence-line` exits 0.

**Originality.** An original mask. No replica of any Q-dance or Defqon.1 mask, emblem, logo or name.

---

## 5. The build plan (starts after the impact pass merges)

**First.**
- Rebase on the merged impact pass and re-read the merged `vj.js`, `vj-core.js`, `vj-fx.js`, `vj-stage.js` and every preset it touched. Scene lanes must keep its kick-weight work (zoom punch, hit-stop, shake), not undo it.
- Tag the pre-upgrade commit (`git tag vj-scenes-v2-baseline`), so any old look can be restored in one command. This matters for the two "replace" verdicts.

### Wave 0: three lanes in parallel, on disjoint files

| Lane | Files (only this lane edits them) | Work | Receipts |
|---|---|---|---|
| **L: Look v2** (page; size L, two commits) | `arsenal/web/vj.js`, `vj-core.js`, `vj-fx.js`, `vj-show.js`, `vj-stage.js`, `tests/vj_core.test.mjs` | <ul><li>Commit 1, pipeline: linear normalisation, HDR composite, removing the lift and the shoulder, bloom pyramid, final pass through modlib-composed `displayOut` and `tmStage`, static dither, grain off, colour split limited to pads, strip v2 with `dt`.</li><li>Commit 2, show: overlay v2, section grade, heat and darkness macros, gated flood, transport marks, a 150 BPM hardstyle demo with sections.</li></ul> | <ul><li>`vj2_verify` all phases with the look on (flash gate included).</li><li>Strip v2 unit tests.</li><li>Every legacy scene through the new chain within 3 codes of the mean before, apart from the lifts that were removed.</li><li>The bloom floor test (p5 lift at most 1 code).</li><li>Overlay pad tests (bar item 9).</li></ul> |
| **M: Modules** (size M) | new: `glsl/draw2/sigil.glsl`, `glsl/light/beam.glsl`, `glsl/draw2/pyro.glsl`, `glsl/light/fire.glsl`; additions: `tmStage` in `glsl/colour/tone.glsl`, `curve 4` in `glsl/post/display-out.glsl`; test cards in `glsl/cards/`; **the only lane that runs** `py -m arsenal shader lib index --write` | Publish the function signatures on day 0, so scene lanes can code against them. Write them fresh from papers and our own maths. | <ul><li>A rendered test card for each.</li><li>`lib lint`.</li><li>`licence-line` exit 0.</li><li>Composed by both twins, byte for byte (`tests/test_glsl_modules.py`).</li></ul> |
| **R: Receipt** (size M) | new: `arsenal/lanes/vj3_headline.mjs`, `arsenal/lanes/vj3_scorecard.py` | <ul><li>Promote the audit lane's virtual 60 fps clock (scratch `audit\audit_render.mjs`, `sheets.py`, `crops.py`) and my metrics (scratch `ad_calib2.py`): true black, p5, lit, white-hot, families, Δp5 on the kick, the pad's added light, saturated-red area change per 333 ms, L/R symmetry, a thin-stroke proxy, a seam probe left of centre, kit freshness.</li><li>Moments: quiet, anti-climax, groove, kick +50 ms, off-beat, the last beat of the build, the drop one, pad 1+2 +100 ms, later +3 s.</li><li>1080p sheets plus 1:1 crops.</li></ul> | Run it on today's 13 scenes: this is the "before". |

### Wave 1: scene lanes, ordered by biggest win

Each lane owns exactly one `.frag`, plus any new module files it creates. It never touches `index.json` and never edits another lane's files.

Order:
1. Rose Window
2. Ring Portal
3. Eclipse
4. Star Cage
5. Ritual Fire (new)
6. Pyro Finale (new)
7. Guardian (new)
8. Relic
9. Star Flower
10. Laser Sea
11. Torn Red
12. Galaxy Finale
13. Sigil
14. Vigil
15. Lissajous Chords
16. Note Rain

Try new scenes without editing the page with `vj.html?sets=vj-ritual-fire,...`; the `?sets=` query already exists.

**Concurrency.**
- Up to 4 lanes may write code at once, but **at most 2 may render at once**, under the house GPU lock. The audit saw parallel SwiftShader renders outside the lock make its screenshots time out while Daniel was playing.
- Headless Chrome with `--use-angle=swiftshader` only, and never the Claude app's browser pane.
- One test-band port per lane, in 8900–8999.

**A scene lane is done when:**
1. `arsenal/presets.py` reports no problems: it loads in Play, uses only Play's uniforms and has constant loop bounds.
2. `py -m arsenal shader licence-line` exits 0.
3. Its house-kit block is current.
4. Its `vj3_headline` before/after sheet passes the scorecard for its role, plus the scene's own acceptance list.
5. `vj2_verify --phase sets --sets <id>` passes: it compiles, the picture is not black, frames advance, it answers pads, and the flash gate holds.
6. Its cost is recorded: SwiftShader milliseconds, an estimated operation count within budget, and no first-frame compile hitch.
7. It renders correctly under both strip v1 and strip v2, so merge order doesn't matter.
8. Commits carry no Co-Authored-By or Claude attribution.

### Wave 2: the page lane again (small)
- Register the 3 new ids in `DEFAULT_SETS`, with names and blurbs (`vj-show.js` `BLURBS`).
- Build two tours from the `role` field: headline, and worship/piano.
- Run the full receipt over all 16 sets.

### Daniel's calls
- **Replacing two looks:** Synthwave Grid → Laser Sea, and LED Wall → Torn Red. Both keep his controls, and the baseline tag keeps the old looks.
- **The display curve:** `tmStage` against AgX later, chosen by eye on the real output screen.
- **Sections:** whether they come from his transport taps until a detector exists.
- **GPU timings on his card:** any real GPU measurement needs his OK, given the AMD driver's crash history. Every millisecond figure in this brief is an estimate.

### Gaps, stated plainly
- No measurement at the speed of the kick from real shows: YouTube refused downloads, so every kick claim is [L].
- No tone-curve test on a real wall.
- No primary source from a hardstyle VJ on how content behaves beat by beat.
- The reference measurements are of JPEG photos and renders, with camera exposure baked in. True black is calibrated only on the TWOFIFTYK LED renders, which are our own class of content.
- The budgets are estimates from operation counts.

```NEW_SCENES_JSON
[
{"id": "vj-ritual-fire", "name": "Ritual Fire", "spec": "ANSWERS TO: Q09 (mirrored flame jets at the base of a hanging ornament), Q23 (a sigil in a fire wreath with framed fire side panels), Q02 (the LED carries the fire), Q04 (a hero inside a flame mandala), Q19 and Q13 (the red symbol alone in black, for the anti-climax), D10 (the all-red hall).\n\nTARGET: A sigil of our own design (a seven-point star in a double ring with a band of tick-mark runes) hangs dead centre, its centre 44% from the top and its ring 55% of the frame height, drawn in bone line on black. A wreath of fire breathes around it. Below it three mirrored pairs of flame jets stand on the floor line and fire in pairs, only when spent. The outer sixth of each side holds three framed fire panels that echo the jets. Embers rise through still air. At rest it is a red-and-bone symbol in the void; at the drop it is molten fire with black between the tongues.\n\nGEOMETRY (2D, centred space p = (uv - 0.5) * (aspect, 1), strict mirror on x unless k8 is raised):\n- Sigil: ring = annulus with a 2.5 px stroke; star = 7-point star polygon (new draw2/sigil.glsl), 3 px stroke; rune band = 36 ticks by polar repeat; every edge through aaStroke.\n- Wreath: a polar flame field in which the distance above the ring is the flame's height; 14 to 20 tongues, an even count so it mirrors; turbulence grows with height; channels overdriven through palHeatPowers so colour runs ember to orange to yellow to white with no brown; threshold the field so black shows between the tongues.\n- Jets: 3 pairs at x = +-0.20, +-0.36, +-0.52 of the frame width from centre, base on the floor line 80% from the top; each a tapered column 2 to 4% of the frame width wide, up to 45% of the frame high by velocity; noise advected upward at a rate in units per second.\n- Side panels: 3 squares per side inside the outer 17% of the width, a thin bronze frame (#8e7165), fire inside at 25% intensity at rest.\n- Embers: 2 layers of a cell-grid gather (hash/pcg cellU2), at most 1 ember per cell, rising 0.08 to 0.2 frame heights per second with a slow sideways drift (noise/warp); a head plus an upward comet tail; exponential flicker; at least 1.5 px wide; no more than 250 visible.\n\nLIGHT: only the fire emits; the room colour is exactly 0. The jets light a thin floor glow (1/d falloff), and the sigil's ring catches the wreath as a rim. No painted haze: the only air is a soft glow term around each jet, bounded to its box. Output scene-linear HDR under the strip-v2 contract (no tone curve, no pow, no clamp beyond simSanitize); in Play or with strip v1, finish through displayOut.\n\nPALETTE: anti-climax P1 (blood red #ab0a1c held, bone #bfae9f lines, ember #d9534d); groove and climax P3 molten (#d63b09 to #ea7720 to #fec141, core #fff3d6); Defqon register P6 (red #db0001 with gold #e89029). Fire always comes from the heat ramp; the section hue tints only the sigil line and the base of the flames.\n\nCAMERA: locked and symmetric. No in-scene shake: the page's impact pass owns camera weight.\n\nMUSIC (strip v2 fields; fall back to gPulse, u_bass and u_high when absent):\n- Kick: click = the sigil line goes white-hot for one frame (thin, at most 3 px); punch = ring and star scale +4% on a spring (6 Hz, damping 0.4); tail = wreath brightness +40% decaying over 300 ms, gone within one beat at 150 BPM.\n- Off-beat (reverse bass): the wreath inhales (tongue height +8%), cut instantly at the next kick when raw, released over 35 ms when euphoric.\n- Screech (high band): thin crackle along the star's edges (a bolt whose offset follows a triangle wave; take the max of bolts, never the sum), white or acid green, at most 2% of the frame.\n- Build: embers multiply with the snare roll; pilot flames appear at the jet bases; the sigil line heats toward orange; on the last beat before the drop everything except the pilot flames goes to zero (one beat of black).\n- Drop (the one, first kick of the phrase): all three jet pairs fire together for 1.2 s, the wreath goes full molten and the side panels flare. After that the jets fire only on pads or on the first kick of each phrase (rationed).\n- Anti-climax: the sigil in red line, one pilot pair, sparse embers; at least 85% of the frame black.\n- Pads: pads 1 to 3 fire jet pairs (outer, middle, inner); pads 4 to 6 flare the left panels, the right panels, or both; pads 7 to 12 throw ember bursts from the ring at the pad's clock position. Velocity sets height and count. Declare accents native for pads 1 and 2 so the page's generic shockwave and laser stay off.\n\nKNOBS: k1 fire height, k2 embers, k3 wreath, k4 jet reach, k5 trails (ember tails, keep per second), k6 side panels, k7 heat bias, k8 symmetry.\n\nHOUSE MODULES: draw2/sdf2, draw2/sigil (new), draw2/domain2 (domToPolar, domKaleido), draw2/aa, colour/palette (palHeatPowers), light/glow (glowHotCore, glowTwoGauss), noise/value, noise/fbm, noise/warp, hash/pcg, motion/envelope, core/clock (clkKeep), sim/feedback (fbDecay, simSanitize); new light/fire.glsl (flame column, polar wreath), written fresh.\n\nLEARN FROM (corpus, study only, no code): MdX3zr Flame (brightness from dwell, channels clipping in order, turbulence growing with height); 3XXSWS (sine-octave turbulence, a tanh finish); l3cfW4 Starship (lopsided falloff for comet tails, exponential flicker); MdsXWM Audio Eclipse (glow escaping past a black occluder); XsjXRm Plasma Globe (crackle from a radius-dependent direction, max of bolts).\n\nBUDGET: about 1,500 operations per pixel on average (wreath about 150, jets and panels only inside their boxes, embers about 400): under 1 ms at 1080p on an RX 6600-class card by the craft study's arithmetic, under 2 ms at the drop. Estimates, not GPU measurements.\n\nACCEPTANCE (before/after sheet at 1080p, the 150 BPM demo with section marks, plus the headline scorecard):\n1. Quiet and anti-climax: at least 75% true black; the sigil alone is lit; one hue family plus bone.\n2. Groove: at least 40% true black; at most 2 families; white-hot 0.05 to 1.5%.\n3. Drop-one frame: lit share 15 to 40%, white-hot 0.3 to 5%, at least 20% true black, black visible between the flame tongues in a 1:1 crop.\n4. Kick against groove: the ring's radius differs by 3 to 8%; the black floor (p5) rises by at most 2 codes.\n5. Saturated-red area (R/(R+G+B) at least 0.8 and luma above 20) changes by less than 10% of the frame between any two frames 333 ms apart, outside a gated flood.\n6. Flames run red to orange to yellow to white in the 1:1 crop, with no brown or grey mud.\n7. Embers are round, at least 1.5 px, with no visible grid; tails continuous, not dotted.\n8. Left-right mirror difference under 3% at quiet and groove with k8 = 0.\n9. arsenal/presets.py lists no problems (Play loads it); py -m arsenal shader licence-line exits 0.\n\nORIGINALITY: our own sigil and layout; no Q-dance or Defqon.1 logo, emblem, name or replica set piece."},
{"id": "vj-pyro-finale", "name": "Pyro Finale", "spec": "ANSWERS TO: D05 (a gold fan-pyro wall rising behind a totem in smoke), D08 (pink fans behind the stage with guard silhouettes), D11 (a vast white-gold comet fan), D01 (mirrored green and white comet volleys), Q12 and Q15 (the CO2 white-out on the peak hit), Q16 (radial beams from behind the hero), Q13 (the red ring in the void, for the anti-climax).\n\nTARGET: A monumental gate of our own design stands as a pure black silhouette against a sky lit only by the pyro. Behind it mirrored volleys of gold comets climb and burst, and a crown of laser beams opens from behind its central eye. On the drop's first beat a CO2 white-out (a gated flood) swallows the frame and clears into a two-colour finale. At the end it cuts to black.\n\nGEOMETRY (2D in parallax layers, strict mirror):\n- Gate: a stepped tower with a central circular eye and two swept blades either side, built from boxes, rounded boxes and a circle; its base on the floor line 82% from the top, its top 30% from the top; colour exactly 0 except a rim line of at most 3 px on its upper edges, lit by whatever burns behind it.\n- Comets: up to 12 per side, launched from emitters behind the gate along rays 20 to 80 degrees above horizontal, ballistic (position = start + velocity * t + 0.5 * gravity * t^2), a pure function of time since launch so no state is kept; a white-gold head (glowHotCore) with a lopsided tail along the velocity. At the apex a burst of 12 to 24 sparks (peony, willow or crossette, dealt per volley from a deck); the sparks fall under gravity and fade over 1.2 to 1.8 s through the heat ramp into the section accent.\n- Laser crown: 8 to 16 beams from a point just behind the eye; the spread opens from 10 to 120 degrees over one beat at the drop; a neon core with a Lorentzian halo, brighter toward the camera (volume/phase phaseHG, g = 0.6); at most 20% brightness below the floor line.\n- Smoke: a very slow static fbm band behind the gate (moves in units per second, never re-seeded), lit only by the comets and bursts (the sum of their glows at quarter strength); black when nothing burns.\n- CO2: six floor jets (mirrored) whose plumes rise with an 80 ms attack and fade over 1.2 s, warm white #fff3d6, density from warped noise. Full strength only through the page's gated flood envelope; without a grant the plumes render at no more than 20% (never a flash).\n\nLIGHT: only pyro, beams and CO2 emit; room colour 0. Scene-linear HDR output under the strip-v2 contract; displayOut in Play.\n\nPALETTE: build P3 molten gold (#e89029, #efbc62); climax P8 pink pyro (#85063f, #c33661, flash #d3797e) or P6 red and gold, by section; finale warm white and gold; anti-climax P1 (a thin red ring in the gate's eye and nothing else).\n\nCAMERA: locked wide; during volleys a slow crane-up of 1 to 2% over 8 bars; the page owns hit-stop and shake.\n\nMUSIC:\n- Build: the launch rate doubles every two bars with the snare roll, bursts small and low; colour drains toward white in the last bar; on the last beat before the drop the scene goes to zero (one beat of black).\n- Drop, the one: the crown opens, a full mirrored volley launches, and the CO2 white-out is requested through the gate.\n- Climax groove: volleys only on the first kick of each bar (rationed); the crown's aim steps on each kick.\n- Kick: click = the gate's rim line flashes white for one frame; punch = crown spread +5 degrees on a spring; tail = comet heads +30% over 300 ms.\n- Off-beat: the smoke's backlight inhales +15%, cut at the next kick.\n- Screech: thin white crackle between the crown's beam tips, at most 2% of the frame.\n- Anti-climax: the gate black, its eye a thin red ring, single slow comet pairs; at least 85% black.\n- Outro end: everything to black over one beat, and hold.\n- Pads: pads 1 to 6 launch comet pairs (outer to inner), velocity sets apex height and spark count; pads 7 to 10 choose the burst type of the next volley; pads 11 and 12 stay with the page (kill, next). Declare accents native for pad 2 (the crown replaces the generic laser burst).\n\nKNOBS: k1 volley size, k2 burst size, k3 crown, k4 smoke, k5 trails (keep per second, spark tails only), k6 CO2 strength (still gated), k7 gravity, k8 symmetry.\n\nHOUSE MODULES: draw2/sdf2, draw2/aa, draw2/domain2, light/glow, groups/neon-line, volume/phase (phaseHG), noise/fbm, noise/warp, hash/pcg, colour/palette (palHeatPowers), motion/envelope (envRamp; the gate's grant arrives through the strip), core/clock, sim/feedback; new draw2/pyro.glsl (ballistic comet, burst and ember helpers), written fresh.\n\nLEARN FROM (corpus, study only, no code): l3cfW4 Starship (comet tails by lopsided falloff, exponential flicker, square then tanh); WlVyRV Dry ice 2 (fog as a height map that emitters carve, for the CO2); MdsXWM Audio Eclipse (light escaping past a black occluder, for the gate's rim); 4lj3Ww (shafts from a direction-only pattern, for the air around the crown).\n\nBUDGET: about 2,500 operations per pixel on average, every burst bounded by its radius so pixels outside it skip it; under 1.5 ms typical and under 3 ms at the drop at 1080p on an RX 6600-class card (estimates).\n\nACCEPTANCE (before/after sheet at 1080p, the 150 BPM demo with section marks, plus the headline scorecard):\n1. Anti-climax: at least 85% true black; lit 0.1 to 3%; one family (red).\n2. Build: lit share rises across the build at every two-bar step; the last beat before the drop is at least 95% true black.\n3. Drop one with the gate granting: the CO2 frame is at least 40% lit and the receipt's flash log counts it as one flash; no more than 3 flashes in any second, pad 3 included. With the gate refusing: lit at most 25%.\n4. Climax groove: at least 20% true black, white-hot 0.5 to 6%, at most 2 families plus white.\n5. The gate's pixels are code 3 or below except a rim at most 3 px wide.\n6. Volleys mirrored (left-right difference under 3% with k8 = 0); tails continuous, not dotted.\n7. No beam brighter than 20% of its peak below the floor line.\n8. arsenal/presets.py lists no problems; py -m arsenal shader licence-line exits 0.\n\nORIGINALITY: our own gate silhouette; no Q-dance or Defqon.1 logo, emblem, name or replica set piece."},
{"id": "vj-guardian", "name": "Guardian", "spec": "ANSWERS TO: Q20 (a black-chrome biomechanical mask with glowing violet eyes between tracery side panels), Q01 (a face under a halo of LED arc segments), Q04 and Q03 (a mask inside a flame or feather halo), Q07 (a face backed by a fan of beams), D04 and D07 (the mask as the stage's centre), Q25 (light travelling over still metal).\n\nTARGET: A colossal mask of our own design (symmetric, biomechanical, black chrome with engraved tracery) fills the centre of the frame inside a halo of arc segments. In the quiet only its two eyes burn in the black. In the groove light travels slowly across its still metal. On the drop the eyes open full, the halo completes and a fan of beams opens behind the head.\n\nGEOMETRY (2.5D relief, frontal, strict mirror):\n- Mask: a height field H(p) built from mirrored primitives (forehead dome, brow ridge, eye sockets as ellipses tilted 12 degrees and subtracted, nose ridge, cheek plates, mouth plate, chin) plus engraved grooves (concentric onion lines on the forehead plate, lattice tracery on the cheeks) and two biomechanical tubes along the jaw. Mask height 70% of the frame, centre 48% from the top. Normals from central differences of H (4 evaluations), only inside the mask's bounding box.\n- Eyes: two almond emitters inside the sockets; lids (a scale on their height) close during builds and open on the drop.\n- Halo: a ring of 24 to 36 thick arc segments (aaStroke) behind the head, 90% of the frame height, with small bulbs; the segments chase in mirrored pairs from the top.\n- Beam fan (climax): 8 to 16 beams from behind the head's centre, occluded by the mask silhouette so they appear only around it.\n- Side panels (k6): three square panels per side in the outer 15% of the width with dim tracery icons; texture only.\n\nLIGHT AND MATERIAL: black chrome (F0 0.25 neutral, low roughness) under two or three tube lights whose reflections travel slowly across the relief (one full pass across the face every 8 to 16 s); a rim light from the halo behind. In melodic breaks the material turns to brass (a coloured F0, palette P9) with one warm travelling highlight. The eyes emit (glowTwoGauss) and light nothing except a faint socket rim. Room colour 0; unlit chrome reads black. Scene-linear HDR output under the strip-v2 contract; displayOut in Play.\n\nPALETTE: opener P2 celestial violet (eyes #540982 to #5435d9, halo periwinkle #696fc2); Defqon register P6 red and gold; green section P5 (#05d987 with one magenta pin); breaks P9 brass. Eyes and halo carry the key; the beams carry the second hue or the same.\n\nCAMERA: locked frontal; a slow push-in from 1.00 to 1.05 across a build; the page owns shake and hit-stop.\n\nMUSIC:\n- Kick: click = the eyes' inner cores go white for one frame; punch = halo scale +4% on a spring; tail = eye glow +50% decaying over 250 to 350 ms in the key colour.\n- Off-beat: the eyes inhale (glow radius +10%), cut at the next kick when raw or released over 35 ms when euphoric.\n- Screech: thin crackle runs along the engraved grooves, white or acid, at most 2% of the frame.\n- Build: the travelling lights speed up, one pair of halo segments lights per bar, the lids narrow; the last beat is black except the eye slits.\n- Drop: the lids open, the halo completes, the beam fan opens over one beat, and the grooves ignite in the key colour for one phrase.\n- Anti-climax: chrome unlit, eyes only, two halo segments at the top; at least 85% black.\n- Melodic break or worship: brass, one slow highlight, soft warm eyes, no beams.\n- Pads: pads 1 to 4 flare halo quadrants, 5 to 8 open beam-fan sectors, 9 to 12 light groove zones (forehead, left cheek, right cheek, chin), in the section's colours. Declare accents native for pad 2.\n\nKNOBS: k1 travel speed, k2 eye glow, k3 halo, k4 beams, k5 trails (keep per second, beams only), k6 side panels, k7 material (chrome to brass), k8 relief depth.\n\nHOUSE MODULES: draw2/sdf2 (sd2Circle, sd2RoundBox, sd2Segment), sdf/combine (smooth unions of the 2D distances), draw2/domain2 (mirror, polar repeat), draw2/lattice (latHex for tracery), draw2/aa, light/fresnel (litFresnelSchlick with a coloured F0), light/specular, light/env (litStudioEnv as the tube rig), light/glow, groups/neon-line (beams), hash/pcg, noise/value (static wear only), motion/envelope, core/clock.\n\nLEARN FROM (corpus, study only, no code): 3XdXRr (a dark mirror under a softbox brighter at its rim); 43jXWt (a giant softbox with a soft fade); 4tcXRr Alien Core (edges glowing by step count, for the grooves); MdsXWM Audio Eclipse (light escaping past a black occluder, for the halo and fan behind the head); llK3Dy (keep reflections in HDR before any blur).\n\nBUDGET: about 1,500 operations per pixel inside the mask box (H at about 200 operations, times 4, plus shading) and about 400 outside; under 1 ms average at 1080p on an RX 6600-class card (estimate).\n\nACCEPTANCE (before/after sheet at 1080p, the 150 BPM demo with section marks, plus the headline scorecard):\n1. Quiet and anti-climax: at least 85% true black; the two eyes are the brightest pixels; lit 0.2 to 2%.\n2. Groove: at least 40% true black; at most 2 families; white-hot 0.05 to 1%; the face reads in a quarter-size thumbnail (reviewer's call).\n3. Light over still metal: between two frames 1 s apart at rest, the mask's silhouette pixels are unchanged while the centroid of the brightest 0.5% of mask pixels moves by at least 2% of the face width.\n4. Kick: eye brightness at least +50% at 50 ms and back to the groove level within 400 ms; the black floor rises by at most 2 codes.\n5. Left-right mirror difference under 3% at quiet and groove.\n6. Drop frame: beams appear only around the silhouette, never across the face.\n7. arsenal/presets.py lists no problems; py -m arsenal shader licence-line exits 0.\n\nORIGINALITY: an original mask; no replica of any Q-dance or Defqon.1 mask, emblem, logo or name."}
]
```

---

## Study: qdance (verbatim)

I've built the library and saved 40 public reference images to scratch. The core finding is that Q-dance headline visuals are mostly darkness: a single lit symbol sits at the centre, each section holds one or two colours, and every effect (beams, lasers, flames, pyro, CO2) radiates from that symbol. Pure white floods are rare and come only on the peak hit.

Nothing in the repo, the KeyLab or the 8793/8794 servers was touched, and nothing was committed. All images and working files are in scratch. YouTube refused video downloads (HTTP 403), so I stopped there and did not try to get round it. That means I could not measure anything at the speed of the kick. My timing evidence comes from YouTube's preview frames, which are one frame every 2 to 10 seconds, plus one 13-second loop that a content studio published.

**How sure I am:** [H] means an official or first-party source, or my own measurement of official images. Note that web pages came to me through a fetch tool's summary, not as the raw page. [M] means trade press, a review, or a search-result summary. [L] means my own inference or a starting number to tune by ear. Measured numbers come from edited aftermovies, so camera exposure, sky and crowd are part of the frame.

---

## 1. Ten design rules

1. **Darkness is the default; light is spent.** [H, measured] In the Qlimax 2023 anthem show, half of all frames are at least 83% near-black. 72% of frames are at least 60% black, and only 11% are full floods (less than 10% black). Qlimax 2023 Warface DJ set: half of all frames are at least 90% black, and only 1% of frames have a bright highlight. The studio's 2024 LED content renders are 61–75% black. Qlimax 2023 was designed around "light and darkness"; the 2023 storyline had an "illusionist" figure leading the crowd into "the void" (Syncronorm). The 2020 online edition was framed as a "dark ritual"; director Daan Jansen: "We wanted to make a trip." (eventinspiration.nl, my translation) [M]. *Target for us [L]:* 70–85% near-black at rest and in anti-climaxes, 30–50% in climaxes, under 10% only on a rationed flood.
2. **One hero, dead centre, inside a ring.** [H] Every Qlimax frame has one symmetric subject at centre: a face, mask, star, sphere, skull or rose window. Usually a halo, ring or spiked corona sits behind it (Q01, Q04, Q11, Q17, Q19, Q23). Defqon.1 2025's RED stage is built the same way: a 20 m circle above a 7 m mask (Backbone).
3. **Hero plus mirrored side panels.** [H] The 2024 LED content layout (TWOFIFTYK renders, Q20–Q25) is a central disc plus three square panels down each side. The side panels carry texture only (fire, nebula, gargoyle icons, tracery). Defqon.1 façades follow the same rule: a centre mask with flanking towers.
4. **Two colours per section, held for a phrase.** [H, measured] Preview-frame timelines show single-hue runs averaging 8–17 s per video. That fits 8-bar phrases at 150 BPM (12.8 s) [L]. Sections change colour, for example in the Qlimax 2023 anthem show: violet → red → white peak → green → orange. Pairs seen: red LED with blue-violet lasers; green LED with green lasers; orange flames with blue-lit structure (D07).
5. **Everything radiates from the hero.** [H] Beam fans, laser crowns and pyro fans start at or behind the centre object (Q10, Q16, Q17, D05, D08). In the Qlimax 2023 anthem show, a laser fan spreads from the star like a crown (frames at 210 s and 220 s).
6. **When beams carry the frame, the LED goes dark or matches their colour.** [H] Q24 shows green lasers with the LED nearly off except one small magenta diamond. The 2023 green section shows green lasers with green LED mandalas.
7. **The LED extends the physical effect.** [H] When flames fire, the LED shows fire: Q02 is a word set in fire; Q23's side panels are fire. At the peak, a CO2 burst arrives with a white LED flood (Q12, Q15).
8. **Hide, then reveal; transform in chapters.** [M] A curtain drops at the opening (Qlimax 2017, 2019, 2022, 2023). A 2017 review criticised that edition because the stage was visible on entry. The centre object transforms through the night:
   - 2016: peacock → raven → phoenix → celestial being (360 Show Design / Spark Creative Studio, which are design studios) [H];
   - 2018: the geisha head opened to reveal a new stage [M];
   - 2017: the temple opened room by room, ending on a galaxy [M].
9. **Contrast over constancy.** Q-dance's head of creative, Jonas Schmidt: "Sometimes you do what people expect, and sometimes the exact opposite." (3voor12 documentary, via Hard News) [H]. His end shows build, then cut everything to silence [M].
10. **The stage itself moves.** Qlimax set pieces move on hoists (Backbone [H]). Defqon.1's 2024 indoor BLUE stage hung 58 motorised hoists (CyberMotion [H]). TWOFIFTYK aimed lights and lasers at the moving parts using TouchDesigner [H].

## 2. Shows and their visual identities

**Qlimax themes**, from Wikipedia [H]:

| Year | Theme |
|---|---|
| 2002 | Cosmos / Infection |
| 2003 | Follow the Leader / The Prophecy |
| 2004 | Destiny's Path |
| 2005 | Science & Religion |
| 2006 | The Darkside |
| 2007 | The Power of the Mind |
| 2008 | Next Dimensional World |
| 2009 | The Nature of Our Mind |
| 2010 | Alternate Reality |
| 2011 | Experiment Dome |
| 2012 | Fate or Fortune |
| 2013 | Immortal Essence |
| 2014 | The Source Code of Creation |
| 2015 | Equilibrium |
| 2016 | Rise of the Celestials |
| 2017 | Temple of Light |
| 2018 | The Game Changer |
| 2019 | Symphony of Shadows |
| 2020 | The Source (online) |
| 2021 | Distorted Reality (online) |
| 2022 | The Reawakening |
| 2023 | Enter the Void |
| 2024 | The Final Prophecy (last edition) |

Visual identities I could check:
- **2016** — celestial mask with feather fan, flame halo.
- **2017** — white temple with a central sphere, cool white/blue beams.
- **2018** — giant geisha face in amber [M on the "Ghost in the Shell" inspiration].
- **2019** — bone arches and a skull medallion, violet→pink; hologram, aerialist and choir (Backbone). The teaser art carried a Latin line about darkness and "the machine" [M].
- **2022** — insect-like ornament; orange; huge ring frames.
- **2023** — star-shaped stage in a 3D cage; rings tunnel; gold sigil cards [M].
- **2024** — "Dark Star": cathedral, stained glass, the Qlimax "blades", the Defqon.1 skull, a rose window; 17 shows of content referencing earlier editions [H].

**Qlimax's graphic language** [H, measured]: thin bone or parchment linework (#bfae9f to #dbcab5) on near-black. Shapes are sacred geometry: triangle-in-circle, star, spiral, Flower of Life, pentagram, a rune border. Type is an ornamental uncial serif. The star core glows warm white (#f9e5c5).

**Defqon.1 themes** [H, defqon1.se]:

| Year | Theme |
|---|---|
| 2012 | World of Madness |
| 2013 | Weekend Warriors |
| 2014 | Survival of the Fittest |
| 2015 | No Guts No Glory |
| 2016 | Dragonblood |
| 2017 | Victory Forever |
| 2018 | Maximum Force |
| 2019 | One Tribe |
| 2020 / 2022 | Primal Energy |
| 2023 | Path of the Warrior |
| 2024 | Power of the Tribe |
| 2025 | Where Legends Rise (RED stage 197 × 48 m, 4 black steel swords, 10 "guards", 2 × 45 m pyro trusses) |
| 2026 | Sacred Oath — cancelled after the first red heat warning in the Netherlands; the 26-minute endshow was filmed on the empty field (DJ Mag, via search) [M] |

- **Stage colour codes** [H, Wikipedia]: RED main, BLUE indoor/raw, BLACK hardcore, UV euphoric/uptempo, YELLOW, INDIGO, MAGENTA classics, PURPLE, GREEN.
- **Rituals** [H, Spark Creative Studio]: The Gathering, Power Hour (invented 2013), the Endshow and the Closing Ceremony were designed as the festival's "pillars".
- **Power Hour** is daytime carnival: red confetti, humour, the crowd's left-right dance [M]. It is not a shader look; at most it is a "sway" pad.
- **The Endshow** is timecoded [H, Syncronorm]. The RED has about 1,800 structural lights plus 600 show lights, and fireworks are handmade by a family firm in Valencia [H, 3voor12].
- **Brand graphics** [H, measured]: red #db0001, black, white, the cyan used for BLUE stage cards #0adbef, gold/beige accents in 2026. Also torn paper, sawtooth borders, halftone dots and distressed stencil type.

## 3. Derived craft

- **Composition:**
  - strict mirror symmetry;
  - the hero at centre;
  - a dark crowd band across the bottom 20–35% with hands and phones in silhouette;
  - hanging speaker stacks as black silhouettes in front of the light (a cheap scale cue);
  - one-point perspective in halls (D09 zigzag trusses converging on a circular LED "eye");
  - layered depth: a translucent header LED wall over the main wall (Backbone).
- **Lighting:**
  - narrow volumetric beams in haze, in mirrored diagonals;
  - beam cones landing in the crowd (Q06);
  - laser X's through the hero (Q17);
  - laser "sheets" or a "sea" over the crowd (D02, D13);
  - flame jets in mirrored pairs at the base (Q09);
  - vertical sparkler fountains (Q18);
  - comet fans behind the stage (D05, D08, D11);
  - a CO2 white-out at the peak;
  - lightning is not a staple in the references.
- **Motion:**
  - opening reveals;
  - chapter transformations;
  - hoisted rings and set pieces;
  - beams sweeping in mirrored pairs;
  - fans opening on the drop.
  - Calm moments move *light over a still object*. In the TWOFIFTYK loop (13 s, silent), a brass Flower of Life never moves; a highlight travels across it, and two soft glints rise in one frame and decay over about 0.5 s.
- **Texture:**
  - brass and bronze;
  - black chrome (biomechanical);
  - faceted silver glass;
  - gothic carved stone;
  - exoskeleton;
  - Defqon.1's carved and painted tribal wood in red, gold and black;
  - haze everywhere.

## 4. Palette library (hex values measured from the references)

| Palette | Near-black / ground | Key | Accent | Flash or core | When to use |
|---|---|---|---|---|---|
| **P1 Void Ritual** | #000000, #0d0a0b, #351015 | blood red #ab0a1c (hold it) | ember #d9534d, bone line #bfae9f | — | anti-climax, intro (Q13, Q19) |
| **P2 Celestial Violet** | #190e5d, #2e1f3e | #5435d9 | magenta #860b5e, periwinkle #696fc2 | cool white #d2d1e5 | openers (Q01, Q05, Q08, Q11) |
| **P3 Molten** | #510a05, #531c08 | #d63b09 → #ea7720 | #fec141 | #f9e5c5 / #fff3d6 | finales, endshows (Q07, Q09, D05) |
| **P4 Cathedral Jewel** | #261e22 | glass #37102d, #860b5e, #41397b, #131b55 | bronze #8e7165 | #f9e5c5 | 2024 cathedral look; also suits worship piano |
| **P5 Laser Green** | teal haze #032521, #054343 | #05d987 | #72ba4f | one magenta pin #c33661 | green laser sections (Q24, Q06) |
| **P6 RED Tribe** | #020001, wine #520a1e | #db0001 | gold #e89029 / #efbc62 | white #fbfcfc; BLUE stage cyan #0adbef | Defqon.1 register (D03, D06) |
| **P7 Night Sea** | #051083 | #0155bc | #1592d9 | #1cbde6 | laser sea, dusk (D13) |
| **P8 Pink Pyro** | #460b20 | #85063f | #c33661 | #d3797e | 2025–26 endshows (D08, D12) |
| **P9 Brass Break** | #281911 | #543a28 | #8e7165 | glint #f9e5c5 | melodic break, piano (Q25) |

**How colour shifts** [H for the measurements, L for the section labels]: the Qlimax 2023 anthem show holds a red block that is 80–99% black (150–180 s). Floods come at about 125 s, 200 s, 250–270 s and 350–365 s, and the night ends in orange and warm white. Rule: anti-climax = one hue, mostly black; climax = two hues plus a short white peak; finale = warm. **Hold red, flash white or gold**: under the flash standards, any change to or from saturated red counts as a flash.

## 5. Motif library, with build notes

House modules are named as `folder/file` from `arsenal/web/glsl/`. Studies are the notes on the private Shadertoy corpus under `state/arsenal/shaders/study/`, learned from and not copied.

1. **Hero in a ring / eclipse corona** (Q01, Q04, Q19, Q23, D06).
   - `draw2/sdf2` circle, `draw2/domain2` kaleidoscope for the spikes, `light/glow` two-Gaussian glow.
   - Corona trick from "Audio Eclipse" (study MdsXWM): put the light sources just behind a black disc, so only their soft 1/distance glow shows and the hard spike never does.
   - **Gap:** we have no 2D star shape function; write one fresh.
2. **Crown of beams** (Q10, Q16).
   - `draw2/domain2` polar coordinates; narrow angular Gaussian beams; haze from drifting `noise/fbm`; brightness by angle from the Henyey-Greenstein phase function in `volume/phase`.
   - Even beam counts of 6–24, mirrored; the fan opens on the drop.
3. **Lasers in haze, laser sheet or sea** (Q17, Q24, D02, D13).
   - Thin segment from `draw2/sdf2` with the `neonProfile` core-and-halo; haze from `noise/warp`.
   - From "Discoteq 2" (study DtXfDr): strings pinned at both ends, slightly detuned against each other.
   - From "Starry planes" (study MfjyWK): exact ray-plane intersection for the sea.
   - Dim below the crowd line, as real shows do. Never sweep the whole frame.
4. **Flame pairs and LED fire** (Q02, Q09, Q23, D11).
   - From "Flame" (study MdX3zr): brightness from how many ray steps a ray spends inside the flame; push a warm colour past 1 so channels clip in order (a cheap hot-metal ramp); turbulence grows with height.
   - `colour/palette` `palHeatPowers` (a fire palette) already exists.
5. **Pyro fans, sparkler fountains, embers** (D05, D08, Q18).
   - From "Starship" (study l3cfW4): stretch each glow's falloff on one side to make a comet trail; flicker exponentially; square the brightness, then soft-limit it with tanh.
6. **CO2 white-out** (Q12, Q15).
   - Rising plumes with an attack of 100 ms or less and a 1–1.5 s fade.
   - From "Dry ice 2" (study WlVyRV): a flat 2D fog map read as height, where the emitters carve the fog.
   - Use it as a mask to swap scenes underneath. It spends one flash slot.
7. **Stained glass / rose window** (Q16–Q18, Q21).
   - Polar kaleidoscope plus `draw2/lattice` hex cells with thick dark lead lines and jewel colours.
   - **Gap:** we have no radial-blur or god-ray module; a radial zoom on `sim/feedback` could stand in.
8. **Sacred-geometry linework** (Q14, Q25): anti-aliased (`draw2/aa`) circles, triangles and stars that draw themselves on, in bone or gold on black. Belongs to anti-climaxes and intros.
9. **Metal under moving light** (Q20, Q21, Q25): `light/specular` and `light/fresnel`; the object stays still and the light travels. From "Alien Core" (study 4tcXRr): edges glow by step count.
10. **Masks and glowing eyes** (Q01, Q03, Q07, Q20, D04): a mirrored mask silhouette, or just two eyes glowing in the dark.
11. **Rings tunnel / zigzag hall** (Q11, D09): exact plane slices; triangle-wave zigzags (`core/shaping` `shpTri`); rings converge during the build and stop dead on the drop.
12. **Electric crackle** (no Q-dance reference): "Plasma Globe" (study XsjXRm) — a bolt from a straight line whose angle shifts with radius by triangle waves; take the maximum of bolts, not their sum. Use it only for screeches.
13. **Tribal graphic cards** (D03): sawtooth edges, torn-paper noise masks and halftone, for titles and section cards only.

## 6. Hardstyle's anatomy, mapped to visuals

**Music sources:** Wikipedia; Hardwave Studios (kick); Hardcultr (reverse bass); producer blogs for structure [M/L]. Visual mappings are [L] unless marked.

- **Intro:** veil or curtain, symbol draws on, the rest black; reveal on the first kick (curtain evidence [M]).
- **Kick** (click 1–8 kHz; punch 80–200 Hz; pitched tail of 200–400 ms, usually tuned to E–G; 150–160 BPM).
  - Click → a one-frame edge spark.
  - Punch → the hero's ring scales by +3–8%.
  - Tail → glow that fades over 200–400 ms, coloured by the kick's pitch.
  - A full-frame flash only on the first kick of a phrase.
- **Reverse bass:** sits on the off-beat and is cut off by each kick; raw ducks almost instantly, euphoric over about 30–40 ms. The corona or haze "inhales" on the off-beat and cuts at the next kick: a hard cut for raw, a soft release for euphoric. Keep it small and coloured.
- **Screech** (C5–C7, a low-frequency oscillator sweeping the filter): thin, high, jagged lines (lasers, sigil strokes, crackle) whose jaggedness follows that oscillator, in acid green or white.
- **Anti-climax** (no melody; kicks plus screech): palette P1, 85–99% black, angular, thin lasers, the symbol alone (Q13, Q19; the Defqon.1 2026 endshow at 920 s).
- **Melodic break / vocals:** motion slows to breathing; light moves over metal; faces and masks; P4 or P9. This is the bridge to worship piano.
- **Build** (snare "drum roll" with note values halving — Solberg [H]): rings converge, beams close towards the centre, sparks rise, colour drains towards white, strobe subdivisions double within the safety gate, then one beat of black before the drop.
- **Climax:** the fan opens wide, flames fire in pairs, a CO2 white-out on the "one", then settle into the section's two-colour pair, and the hero moves to its next form.
- **Mid-outro:** repeat the anti-climax look exactly, so the section keeps its identity.
- **Endshow:** P3 molten, everything at once, then cut to black and silence (Schmidt [M]).
- **Through the night** [M]: tempo rises over a Qlimax night, which closes with the hardest set; a "night arc" macro control would capture this.

## 7. Our 13 scenes against this language (upgrade direction [L])

| Scene | Direction |
|---|---|
| laser-cathedral | rose window plus laser X from the hero (Q16/Q17), P4 |
| reactor | Dark Star eclipse corona plus CO2 peak (Q19, Q12) |
| geometry-hall | star stage in a cage, zigzag hall (Q11, D09) |
| hyperspace | Enter the Void rings tunnel |
| particle-galaxy | Temple of Light finale — the galaxy as the last "room" |
| fractal-bloom | feather fan / white star flower (Q03, Q15, Q22) |
| chord-constellations | sigil linework drawn by the chords |
| liquid-chrome | brass or black-chrome metal with travelling glints |
| note-rain | sparkler fountains and embers |
| lissajous-chords | laser graphics |
| led-wall | hero-plus-side-panels layout and tribal cards |
| synthwave-grid | laser sea over a crowd line, in a fire or ritual horizon |
| aurora-curtains | the melodic-break / worship register |

The house's own summary of Daniel's taste (`research/in-flight/shader-school-2026-10-13/arc-daniel-voice.md`) asks for a dark stage, one luminous subject, saturated colour that decays, and clean edges. That is the Qlimax grammar.

## 8. Who makes it

- **Q-dance creative:** Jonas Schmidt, head of creative.
- **Spark Creative Studio / Mark Rietveld:** Qlimax 2016 and 2017 concepts; the Defqon.1 ritual pillars.
- **360 Show Design:** Qlimax 2016 key visual.
- **Voutloos (Frank Burghout):** Qlimax 2017 key visual.
- **Backbone International:** stage design and technical production — Qlimax 2019, 2022, 2024; Defqon.1 2025.
- **TWOFIFTYK:** Qlimax 2024 content — about an hour of timecoded visuals across 17 shows with no content reused, TouchDesigner, two VJs (one on timecode, one live).
- **Vision Impossible:** Qlimax show design and VJing since 2005, "dark and immersive".
- **Happy Technology (lighting designer Robbert-Jan Vernooij):** lighting, pre-programmed in Depence.
- **LaserImage / Jeroen Winnubst:** lasers.
- **Lucas Gerritsen:** pyro.
- **Lights in Motion and Close-Act Theatre:** fire performers and creatures, Defqon.1 2016.

**Headline acts' own content:** I found no studio credits.
- Sub Zero Project says its live concepts join visuals, production and show into one experience; "Our World" has four themed worlds [M].
- Daytime RED sets show stage décor, not LED content.
- Phuture Noize's "Black Mirror Society" is the one artist look visible: a red/blue split in the artwork [M] and pink-magenta fluid textures on the LED (D15).

## 9. Safety notes for this look [H, from the house research file]

- Red-heavy Defqon.1 looks must change red slowly or over small areas.
- A CO2 or white flood spends a flash slot.
- Moving laser sheets and zigzag patterns over 25% of the screen count as risky stripes; keep them low-contrast or flowing in one direction.
- Strobes stay thin.

## 10. Gaps

- No measurement at the speed of the kick (video download refused). Every claim about kicks is [L].
- No primary interview with a Q-dance VJ about content behaviour beat by beat.
- Anti-climax structure comes only from producer blogs.
- Q-dance's own site renders in JavaScript, so official wording came via EDM Identity and search summaries.
- The stage shown in D07 is not confirmed.
- Measurements include sky and crowd.

---

## Reference images (40)

All in `<session scratchpad>/headline/refs/`. "YT" means the official Q-dance YouTube video at youtube.com/watch?v=ID; "@" marks a preview frame at that time.

- **Q01 qlimax-2014_headhunterz-show_led-face-in-halo** (YT BtDJuU7_6K4). A colossal LED-mapped bust sits dead centre under a broken arc of LED halo segments, with black speaker silhouettes either side and a black crowd band. Royal violet #5435d9 on violet-black, 41% black, no beams. Motion implied: the halo segments chase while the face holds still.
- **Q02 qlimax-2015_aftermovie_fire-led-angular-frame** (YT npaIH2mEBok). A wide angular lattice of LED strips frames a central diamond, and the wall shows one word burning in realistic fire, mirrored. Wine-red and orange, 52% black, cool blue beams at the edges as a complement. Flames rise and the type burns: the LED extending the pyro.
- **Q03 qlimax-2016_anthem-show_celestial-mask-feather-fan** (YT j0Waw8wzZgI). A pale celestial mask sits inside a giant gold-ivory feather fan, with pyro plumes along an overhead arc and blue-violet beams fanning into the crowd. Many hoist lines point to set pieces that move. Its stage transformed peacock → raven → phoenix → celestial over the night.
- **Q04 qlimax-2016_key-visual_celestial-mask-flame-halo** (360showdesign.com). Poster: a silver-headdressed female mask inside a radiating orange flame mandala, with a small star sigil above the brow. 66% black, molten #b56038 and #861f12. It is the template for a hero inside a corona.
- **Q05 qlimax-2017_aftermovie_temple-of-light-white-blue-beams** (YT ezo52rokchw). A white ornamental temple with a geodesic sphere at centre, and dozens of white and periwinkle beams in mirrored diagonals. Only 19% black: a cool, light edition (#696fc2, #172580, #d2d1e5). The beams sweep in pairs and a ring moved round the sphere.
- **Q06 qlimax-2017_crowd_green-beam-cones-in-haze** (hardstylemag.com 2017 party report). Five green cones (#05d987) land in the crowd, the centre one tallest, with pink secondary beams and bat-wing truss silhouettes. 42% black; the crowd is lit only where the cones land. Implied motion: the cones pan across the floor.
- **Q07 qlimax-2018_aftermovie_geisha-face-amber-beams** (YT eN6AmWhdwrc). A giant porcelain geisha face with red eye make-up and a mechanical crown is backed by an amber fan of beams. Monochrome orange #ea7720 / #d15a10 plus white, 27% black. The head later opened to reveal a stage.
- **Q08 qlimax-2019_stage_symphony-of-shadows-violet-symmetry** (Backbone / TPi). Bone-like arches surround a central skull-mask medallion, with flames at the booth and mirrored white beam diagonals. A two-colour split runs violet on the left to pink on the right (#2e1f3e → #b87897), 26% black.
- **Q09 qlimax-2022_stage_insect-ornament-orange-flames** (Backbone). An exoskeleton cage ornament hangs at centre, six flame jets fire in mirrored pairs, and huge ring frames stand at the sides. All orange-red (#510a05 → #d63b09) with tiny cyan accents. The ornament moved and flickered.
- **Q10 qlimax-2022_stage_radial-pink-beams-ring-frames** (Backbone). Radial pink beam fans spread from behind the booth and from two giant side rings. Rose monochrome, 44% black. The fans open and rotate, and the side rings echo the hero's ring.
- **Q11 qlimax-2023_aftermovie_star-object-rings-lasers** (YT kY3sJMNus6Y). Five bulb-studded rings recede like a portal in front of a violet star, a white beam shoots through them and amber fans radiate. The sigil card fills the right half. 34% black, magenta #860b5e.
- **Q12 qlimax-2023_anthem-show_white-violet-burst-co2** (YT VpysSw98H0I). The peak: the star wheel blazes warm white (#f1ddc5), with vertical CO2 jets, sparks and violet edges. 33% black: the climax frame.
- **Q13 qlimax-2023_anthem-show_void-anticlimax-red-ring** (YT VpysSw98H0I @1:40). The whole frame is near-black except a tiny red ring and a few red points (#592d34). Stillness: the void before a hit.
- **Q14 qlimax-2023_anthem-show_gold-line-mandala-on-led** (@1:50). A gold line-drawn star-in-circle sigil glows on the LED, 79% black (#757950). The symbol itself is the content.
- **Q15 qlimax-2023_anthem-show_white-star-flood-peak** (@3:20). Warm-white kaleidoscopic petals fill the frame through CO2 haze, with crowd silhouettes at the bottom. 3% black, 22% bright highlights: the rare flood.
- **Q16 qlimax-2024_caseheader_radial-white-beams-cathedral** (twofiftyk.com Qlimax case page). Gothic stained-glass side lancets frame a rose window bursting white beams, with sparkler fountains and strict symmetry. Bronze and rose, 42% black.
- **Q17 qlimax-2024_orange-laser-x-through-rose-window** (TWOFIFTYK). Orange lasers cross in an X through the rose window, white spots fall in mirrored diagonals, smoke rises and the side windows glow red. 44% black.
- **Q18 qlimax-2024_blue-stained-glass-blades-sparklers** (TWOFIFTYK). Indigo and cobalt tracery surrounds a blue-beamed star, with two sparkler fountains and pale curved blades at the booth. 65% black.
- **Q19 qlimax-2024_red-pentagram-alone-in-black** (TWOFIFTYK). A red pentagram disc with small red side panels, 93% black (#ab0a1c). The minimal, breathing moment.
- **Q20 qlimax-2024_led-content_biomech-mask-violet-eyes** (TWOFIFTYK render). A black-chrome biomechanical mask with violet eyes (#540982), flanked by six violet tracery side panels. 75% black.
- **Q21 qlimax-2024_led-content_stained-glass-star** (TWOFIFTYK render). A faceted silver star in a leaded rose window, with gargoyle medallions in the side panels. 61% black.
- **Q22 qlimax-2024_led-content_psychedelic-owl** (TWOFIFTYK render). A symmetric fractal-feather owl in teal, green and blue, with blue nebula side panels. 67% black.
- **Q23 qlimax-2024_led-content_flaming-skull-star** (TWOFIFTYK render). A skull in a fire wreath with a star on its brow and a spiked ring, with framed fire in the side panels. 66% black, #c44626.
- **Q24 qlimax-2024_green-lasers-teal-haze** (TWOFIFTYK). Cyan beams fall onto the crowd and green lasers fan from the booth, while the LED is almost off apart from one magenta diamond. 62% black.
- **Q25 qlimax-2024_led-content_brass-flower-of-life-loop** (frame from TWOFIFTYK's 13 s public loop). A brass Flower of Life sits in a gothic arch with pentagram-wheel side panels. 75% black. The object is still; a highlight travels across the metal, with two soft glints.
- **D01 defqon1-2016_endshow_green-fireworks-dragon-stage** (YT HkSmJQMudS4). A green-lit Dragonblood stage with symmetric volleys of green and white comets and hands in the foreground. Green #38ae6d against a teal sky, 26% black.
- **D02 defqon1-2017_endshow_green-laser-sheet-aerial** (YT 3skZxOjrJ9c). From above: a green laser carpet lies over the crowd with magenta and gold pyro above a red stage. The sheet ripples.
- **D03 defqon1-2024_brand_torn-red-zigzag-graphics** (YT s8sOPRZAQfc thumbnail). Brand system: torn red paper (#ee0406), black, white stencil type, halftone, sawtooth zigzags, the Defqon.1 emblem, and the booth arch lined with bulbs.
- **D04 defqon1-2019_endshow_tribal-mask-pyro-fan** (YT nahoiz-jL4A). A tribal totem mask under a white laser lattice, with low flame jets and comets. Fully saturated red and magenta, 0% black.
- **D05 defqon1-2023_closing-ritual_gold-pyro-wall** (YT wy1NIznsLZI). A gold fan-pyro wall rises behind a cathedral-like totem in orange smoke, beside the red sawtooth card. Gold #e89029 and red #fd0102, 33% black.
- **D06 defqon1-2025_red-stage-day_mask-circle-swords-flames** (Backbone). In daylight the 197 m RED shows its 20 m circle over the mask, flaming totem towers and guard statues, all carved red, gold and black décor. In daylight the décor is the palette; the LED barely reads.
- **D07 defqon1-2025_night_blue-mask-block-in-pyro-wall** (Backbone; stage not confirmed). A blocky mask structure lit blue-violet from inside, wrapped in orange-gold pyro and smoke, with magenta laser lines: a blue-versus-orange complementary pair. 10% black.
- **D08 defqon1-2025_endshow_pink-pyro-fans-guards** (Backbone). Magenta and pink firework fans rise behind the RED, with guard statues holding blue-lit halberds in silhouette. 31% black.
- **D09 defqon1-2025_gathering-blue_orange-zigzag-beam-tunnel** (Backbone; matches the Gathering 2025 video). A hangar of sawtooth trusses converges on a circular LED eye at the vanishing point, with white beams and sparks in orange-red. 21% black.
- **D10 defqon1-2025_gathering-blue_red-spiral-eye-pyro** (Backbone). The same hall all in red: a spiral LED eye with overhead bursts. 33% black.
- **D11 defqon1-2025_endshow_aerial-fan-pyro-fire-ring** (Backbone). From the air: a vast white-gold comet fan rises behind the stage while flame posts ring the field. 45% black.
- **D12 defqon1-2026_endshow_red-dragon-wings** (YT fLWY-Sxb1bE). A dragon head with wings in red and magenta, pink fireworks and torn-paper overlays. 18% black.
- **D13 defqon1-2026_endshow_ice-blue-laser-sea** (@19:20). A blue laser "sea" rolls over the empty field (#051083 to #1cbde6). 43% black.
- **D14 defqon1-2026_endshow_led-dragon-green-red** (@16:00). The dragon façade is textured in red against green, with black between. 63% black.
- **D15 defqon1-2018_phuture-noize-bms_purple-haze-pink-led** (YT 8MM-D0LzPgY). On the indoor BLUE stage, white cones fall through violet haze while a long LED band shows pink fluid texture, with pyramids carrying the emblem. 34% black.

## Files

All under `<session scratchpad>/headline/`. Scratch only: these images are other people's work and must never be committed.
- `refs/` — the 40 reference images.
- `refs-contact-sheet.jpg` — all 40 on one page.
- `work/` — 64 official thumbnails, 41 press photos, 19 preview-frame timelines (`mos_*.jpg`, `q23_detail.jpg`, `d26_detail.jpg`), the TWOFIFTYK loop, and the measuring scripts `palette.py`, `timeline.py` and `agg.py`.

## Sources

- Qlimax: https://en.wikipedia.org/wiki/Qlimax
- Defqon.1: https://en.wikipedia.org/wiki/Defqon.1_Festival ; https://defqon1.se/en/articles/defqon-1-anthems/
- Hardstyle: https://en.wikipedia.org/wiki/Hardstyle
- Studios:
  - https://twofiftyk.com/en/project/qlimax
  - https://www.vision-impossible.nl/portfolio/qlimax/
  - https://www.backbone-international.com/talks/tpi-qlimax/
  - https://www.backbone-international.com/portfolio/qlimax-2/
  - https://www.backbone-international.com/cases/qlimax-2019/
  - https://www.backbone-international.com/portfolio/defqon-1-weekend-festival-2025/
  - https://360showdesign.com/qlimax-2016-rise-of-the-celestials/
  - https://sparkcreativestudio.nl/qlimax-2016-rise-of-the-celestials
  - https://sparkcreativestudio.nl/qlimax-2017-the-temple-of-light
  - https://sparkcreativestudio.nl/defqon1-weekend-festival-festiflow-and-show-design
- Production:
  - https://www.syncronorm.com/newsitem/qlimax-2023-interview
  - https://www.syncronorm.com/newsitem/defqon1-depence
  - https://cyber-motion.com/showcases/cybermotion-at-defqon-1-redefining-festival-innovation/
  - https://www.tpimagazine.com/defqon-1-2020-at-home-with-clf-lighting/
- Laser and pyro teams:
  - https://grandfinale.nl/jeroen-winnubst
  - https://grandfinale.nl/defqon1-2018
  - https://www.lightsinmotion.nl/en/defqon-1/
- Interviews:
  - https://hardnews.nl/en/3voor12-documentary-reveals-the-creative-process-behind-the-defqon-1-endshow/
  - https://hardnews.nl/en/the-bosses-of-q-dance-and-sensation-about-end-shows/
  - https://festileaks.com/2022/01/jonas-schmidt-is-show-creator-bij-q-dance-in-essentie-speel-ik-met-de-emotie-van-80-000-man/
  - https://www.eventinspiration.nl/klaar-is-case-s-werelds-grootste-indoor-hardstylefeest-qlimax-werd-unieke-online-audiovisuele-trip/
- Reviews:
  - https://hardstylemag.com/party-report-qlimax-2017-immersing-light/
  - https://hardstylemag.com/review-qlimax-2022-the-reawakening/
  - https://hardstylemag.com/6-things-you-missed-if-you-skipped-qlimax/
  - https://www.hardstylereport.com/reports/qlimax-2017-the-temple-of-light/
  - https://hardnews.nl/en/qlimax-2018-was-a-real-game-changer/
  - https://hardnews.nl/en/this-is-what-we-know-about-qlimax-2019-so-far/
- News:
  - https://ufo-network.com/2024/11/26/qlimax-the-final-prophecy-2024/
  - https://edmidentity.com/2024/07/27/q-dance-qlimax-the-final-prophecy/
  - https://djmag.com/news/defqon1-share-2026-endshow-filmed-without-audience-after-heatwave-cancellation-watch (via search only)
- Artists:
  - https://www.bandwagon.asia/articles/sub-zero-project-open-up-about-4444-of-a-kind-our-world-pushing-hardstyle-beyond-its-borders
  - https://edmidentity.com/2018/06/14/phuture-noize-black-mirror-society/ (via search only)
- Music:
  - https://hardwavestudios.com/learn/sound-design/hardstyle-kick-synthesis
  - https://www.hardcultr.com/producer-talk/reverse-bass-hardstyle-explained-2026/
  - https://www.lucidsamples.com/blog/hardstyle-samples-make-hardstyle-track
- Earlier house research (safety rules, Solberg): `E:/AI-Setup/research/reviewed/keylab-liberation-2026-10-22/vj-festival-lessons-2026-10-24.md`

---

## Study: audit (verbatim)

None of the 13 scenes is headline-ready yet. The best scores about 6/10 and most score 3–5. What holds them back most is two things every scene shares:

- **No true black.** In 11 of 13 scenes no pixel of the groove frame is darker than 8/255.
- **Flat and small.** Only 3 scenes have a camera moving through a world.

GPU cost is not the limit. My estimate is that every scene holds 60 fps at 1080p on an RX 6600-class card with most of the budget unused, so there is room to spend several times more per pixel.

**Strongest bases:**
- **Hyperspace**: it has a camera, a world, and a kick that stretches the stars instead of brightening the screen.
- **Geometry Hall**: real raymarched 3D, one hero object, a camera moving down the hall.
- **Laser Cathedral**: the right language for hardstyle (lasers, fans, aim that steps on the beat, one laser head per pad). It is the least polished as built, but has the highest ceiling once rebuilt in 3D.
- **Aurora Curtains**: for worship piano.

**Weakest on a headline wall:** Chord Constellations, LED Wall and Note Rain. They work as piano and worship teaching visuals; I'd keep them there and leave them out of a hardstyle set.

## How I rendered it, and the limits

- **What was judged:** a copy of `arsenal/web` at commit 4fdd2d47, taken at 16:15, identical to HEAD. The impact lane's edits are not in these frames. Hashes are in `snapshot-sha256.txt`.
- **How:** headless Chrome on SwiftShader (the renderer string was checked on every page), under the house GPU lock, one burst per scene, port 8962. The KeyLab and ports 8793/8794 were not touched, and nothing in the repo was changed.
- **Virtual clock:** I replaced the page's clock so every frame advances exactly 1/60 s, whatever SwiftShader's real speed. Trails, envelopes and the demo's beats are therefore what a 60 fps GPU would show. The 720p and 1080p frames came out with identical numbers, which confirms the captures are reproducible.
- **The moments:**
  - quiet: 2 s in, nothing playing
  - groove: the page's demo (112 bpm, D-flat), half a beat after the kick on beat 3
  - kick: 50 ms after a downbeat; the demo's downbeat also changes chord
  - pad: 100 ms after pads 1 (shockwave) and 2 (laser burst) at full velocity
  - later: 3 s after the pad hit
  - two extra frames with the look pass off
- **Resolution:** all 13 at 1280×720; all moments at 1920×1080 for 9 scenes; a 1080p groove frame with 1:1 crops for all 13.

I stopped the full 1080p pass before Fractal Bloom, Geometry Hall, Particle Galaxy and Lissajous. Two other lanes (`vj_impact_nopunch.mjs` and `vj_adv.mjs`) were running SwiftShader renders at the same time on private `--lock-dir` folders, outside the house lock. The CPU contention made one of my screenshots time out, and you are playing live. Stopping left the house lock held by a dead process; I reaped it and it is now free. No orphan Chrome was left.

Other limits:
- These are single frames. I judged motion from the code and from the trail copies visible in the frames.
- The demo runs at 112 bpm, not 150, so the decays will overlap more at hardstyle tempo.
- Pads 3–8 (flash, glitch, strobe, particles, kaleidoscope, freeze) were not exercised.
- I could not watch official aftermovies. The comparison to real shows rests on published design write-ups and interviews (Sources below).

## The headline bar, from sources

1. **Darkness is the canvas.**
   - Qlimax 2023's design played on the contrast between light and darkness ([Syncronorm](https://www.syncronorm.com/newsitem/qlimax-2023-interview)).
   - Vision Impossible has done show design, motion graphics and VJing for Qlimax since 2005, and describes its themes as dark and immersive ([Vision Impossible](https://www.vision-impossible.nl/portfolio/qlimax/)).
   - Rick Jacobs, Nicky Romero's VJ: "black is your friend" ([Resolume](https://resolume.com/blog/14343)).
2. **Depth is built in.**
   - Qlimax added a second LED layer and a translucent header wall to create depth ([Backbone/TPi](https://www.backbone-international.com/talks/tpi-qlimax/)).
   - On a flat wall, depth comes from forced perspective, foreshortening, shading and shadows, motion parallax and sharp contrast ([AVIXA](https://www.avixa.org/explore/articles/the-illusion-of-3d-on-led-walls-how-content-and-perspective-create-immersive-visuals)).
3. **Content is made for the show and tightly synced.** The final Qlimax had about an hour of timecoded visuals across 17 shows with no content reused. One VJ ran the timecode and another played live, and TouchDesigner synced the visuals with lights, lasers and moving stage parts ([TWOFIFTYK](https://twofiftyk.com/en/project/qlimax)).
4. **Colour discipline.** Ed Warren keeps to two colours at once ([EDM.com](https://edm.com/interviews/skrillex-fred-again-four-tet-msg-rave-how-ed-warren-designed-lighting-lasers/)).
5. **Lasers come from real places.** Stage lasers come from projector positions, side projectors often mirror each other, and beams are read in haze ([ILDA](https://www.ilda.com/resources/Safety/audience-scanning_overview_latest.pdf), via `research/reviewed/keylab-liberation-2026-10-22/vj-festival-lessons-2026-10-24.md`).

## The shared pipeline and the look pass (this affects all 13)

### Is it HDR? Is there a real tone map?

No to both. The chain from scene to screen is:
1. Each scene tone-maps itself (`1 - exp(-k·x)`, k between 1.1 and 1.3) and writes display values clamped to 0–1.
2. The composite decodes those, adds the accent overlay in linear light, and applies a second soft shoulder (unchanged below 0.8, tanh above).
3. It re-encodes, applies saturation in display space, inverts, flashes, and multiplies by master brightness 0.9, then clamps.
4. The look pass decodes again, adds bloom and vignette, encodes, adds grain, and clamps.

That is three curves and four transfer conversions in a row. The RGBA16F buffers never hold anything brighter than white, so nothing downstream can tell a hot laser core from a pale wash. The house's own colour notes say the opposite: do the light maths in scene-linear, then apply one display transform once (`research/reviewed/shader-school-2026-10-13/color-post.md`, sections 0 and 5.10). The house module that does exactly this, `displayOut` in `arsenal/web/glsl/post/display-out.glsl`, is not used by the VJ rig.

### Colour space and black level

- **Plain power 2.2, not the sRGB curve.** Near black it lifts dark values about 3×. Linear 0.001 becomes 11/255 here, against 3/255 with sRGB.
- **Every scene paints a faint room colour** of 0.0006–0.013 linear (for example `vj-chord-constellations.frag:111`, `vj-laser-cathedral.frag:139`, `vj-reactor.frag:146`).
- **Measured effect:** the darkest 5% of the groove frames sits at 8–25/255, and 11 of 13 have 0% of pixels at or below 8/255. Only LED Wall at rest (1.9) and the vignetted corners of Fractal Bloom reach black.
- **On an LED wall:** at 2.2 gamma, 13–25/255 is about 0.2–0.9% of peak, roughly 3–13 nits on a 1500-nit wall. In a dark hall that is a glowing coloured rectangle, not black.
- **Master brightness 0.9** caps whites, including the flash, at 230/255 before bloom.

### The composite adds a coloured lift on every kick and every beat

- A centre glow on each kick or snare: `vj.js:283` and `:1353`, up to 0.06 linear, fading over 150 ms.
- A frame-edge glow on each beat: `vj.js:282` and `:1351`, about 28/255 at the edges at the beat peak.
- **Measured on Chord Constellations**, which has nothing of its own in the centre: from groove to kick, the centre rose from 21.0 to 31.6/255 and the edges from 17.4 to 20.6.
- So each kick fogs the middle of the frame instead of landing. At 150 bpm the 150 ms glow barely fades before the next kick.

### Bloom

- **Threshold:** a soft knee from linear luminance 0.12 to 0.55 (`vj-fx.js:114`). On these already-tone-mapped values, that means anything brighter than about display 0.38 (mid-grey) starts to glow.
- **Shape:** two levels, at 1/4 and 1/16 resolution, roughly 10 px and 35 px spread at 1080p.
- **Strength:** 0.30 at the default look amount of 0.55, with its average contribution capped at 0.025.
- **Measured:** it changes the groove frame's mean luminance by 0–13% (Liquid Chrome 12.8%, Synthwave 5.5%, the rest 4% or less). It is visible on pad hits, not on the scenes. There is no wide halo and no "brighter than white" read.

### Grain and colour split

- **Grain is regenerated every frame** (`vj-fx.js:320`, `:180`). It roughly triples the fine noise in flat dark areas (Reactor 0.33 → 0.94 code values; Hyperspace 0.34 → 1.12). The shader-craft record says per-frame grain was removed once at your request.
- **The colour split fires on every kick** (driven by `hit.pulse`), up to about 9 px at the corners at 1080p. On thin beams it reads as red and blue fringes: `crops/hyperspace-pad-beam-zoom.png`.

### Accent overlay (the same in all 13 scenes)

- **Pads 1+2 overwhelm the scene.** They raise the frame's mean luminance 2.6–16× (Laser Cathedral 0.0096 → 0.157; Chord Constellations 0.0067 → 0.103). The overlay, not the scene, becomes the show.
- **It ignores the scene's world.** Every scene gets the same yellow ring target and the same 12-beam fan from a corner, regardless of its perspective. That is two more colours on top of the scene's own.
- **Its trails make copies, not motion blur.** It keeps about 0.87 of the previous frame and takes the max, so each frame's position stays visible:
  - moving beams become ribbons of 4–5 parallel lines
  - the shockwave becomes a target of 6–8 concentric rings
  - the note sparks become dotted lines
  
  Evidence: `crops/shockwave-ring-stack-lookoff.png`, `crops/note-glint-dotted-trails.png`.

### Colour count

Scenes use all 4 palette colours at once, and several add the 12 pitch colours on top. That is well past the two-colour discipline.

## Scores (headline-ready, 1–10)

| Rank | Scene | Score | Groove mean Y | Kick ÷ groove | Pad ÷ groove | Black floor q/g/k | Lit % (groove) |
|---|---|---|---|---|---|---|---|
| 1 | Hyperspace | 6 | 0.033 | 1.58 | 6.6 | 12/25/33 | 8.5 |
| 2 | Geometry Hall | 5 | 0.021 | 3.50 | 7.6 | 16/23/25 | 3.3 |
| 3 | Synthwave Grid | 5 | 0.078 | 1.44 | 2.6 | 16/19/35 | 35.8 |
| 4 | Aurora Curtains | 5 (7 for worship) | 0.032 | 1.30 | 4.1 | 8/11/15 | 20.5 |
| 5 | Particle Galaxy | 4 | 0.015 | 1.48 | 8.6 | 10/12/14 | 4.0 |
| 6 | Laser Cathedral | 4 (highest ceiling) | 0.010 | 1.64 | 16.4 | 12/14/17 | 1.6 |
| 7 | Reactor | 4 | 0.026 | 2.13 | 6.2 | 11/17/21 | 18.7 |
| 8 | Lissajous Chords | 3 (6–7 for piano) | 0.027 | **0.61** | 4.3 | 12/12/15 | 11.7 |
| 9 | Liquid Chrome | 3 | 0.028 | 1.55 | 5.0 | 15/17/19 | 6.3 |
| 10 | Fractal Bloom | 3 | 0.020 | 3.03 (density breath) | 6.5 | 10/6/17 | 8.5 |
| 11 | Note Rain | 2 (5 for piano) | 0.012 | 1.34 | 9.5 | 10/13/16 | 2.6 |
| 12 | LED Wall | 2 | 0.018 | 1.37 | 8.0 | 2/8/12 | 7.6 |
| 13 | Chord Constellations | 2 (6 for piano) | 0.007 | 1.49 | 15.4 | 13/15/17 | 0.1 |

Black floor is the 5th-percentile display luma (out of 255) for quiet, groove and kick. Lit means brighter than 64/255. The kick and pad numbers include the shared composite lift.

**Cost.** The table is a SwiftShader (CPU) ranking of each scene's own pass at 1080p with all pads active, not a GPU measurement. An empty pass costs 11 ms. The GPU column is my estimate from counting operations; an RX 6600 has about 70k ideal operations per pixel per frame at 1080p60.

| Scene | SwiftShader ms | Estimated GPU ms |
|---|---|---|
| Lissajous | 790 | 2–5 |
| Laser Cathedral | 355 | 1–2 |
| Geometry Hall | 307 | 1–2 |
| Galaxy | 263–277 | ≤1 |
| Hyperspace | 238–246 | ≤1 |
| Reactor | 213–223 | ≤1 |
| Aurora | 204–221 | ≤1 |
| Chord Constellations | 195 | ≤1 |
| Synthwave | 185–193 | ≤1 |
| Liquid Chrome | 157–264 | ≤1 |
| Note Rain | 127–139 | ≤1 |
| Fractal Bloom | 115 | ≤1 |
| LED Wall | 74 | ≤1 |

The overlay's particle loop can add about 10k operations per pixel where particles are active. The only combination I'd want a real GPU timer on is Lissajous during a transition (two scenes render at once) with particles held.

## Each scene

**1. Hyperspace — 6.** Streaks with white-hot heads and coloured tails pour toward the viewer. This is the one scene where the kick changes the world rather than the brightness (the streaks stretch), and the pad's hyperjump reads well.
1. A hard horizontal seam in the nebula, left of the vanishing point, in every frame. Cause: the angle wraps from +π to −π there (`vj-hyperspace.frag:160–161`).
2. The nebula and the feedback lift the background to 25/255 in the groove and 45–49 on a pad hit: brown-teal fog, not space.
3. Thin depth. Each angular cell holds one star; there are 3 layers and no near dust or parallax planes, and the feedback leaves dashed echoes. It reads as a generic starfield screensaver.

Cost: about 6 streak evaluations plus 2 noise calls per pixel; cheap.

**2. Geometry Hall — 5.** A raymarched hall with a camera dolly. The chord picks the solid (3 notes a tetrahedron, 4 an octahedron, 5+ an icosahedron) and it snaps on the beat. The kick reads strongly (3.5×, with the chord-change pop).
1. The hall is invisible: flat grey fog at about 22/255, pillars as faint strips. The floor grid shows step-count banding contours (`crops/geometry-hall-floor-moire.png`).
2. The faces are flat and muddy: little lighting, no reflections, no light in the air. The solid fills about 25% of the frame height in the groove.
3. Silhouettes have no anti-aliasing beyond the edge band; the house cone-tracing module `ray/aa3.glsl` would fix this. The 1:1 crop shows a notch in one edge.

Cost: up to 64 steps of about 200 operations each (the icosahedron has 20 face planes), roughly 13k per pixel; fine.

**3. Synthwave Grid — 5.** The best composition of the 13: horizon, a sun as the focal point, a perspective grid, and a grid that lurches on the beat.
1. Washed out. The sky takes a pastel teal-green from the palette, the sun is near white, a grey haze band sits at the horizon, and 36% of the frame is lit in the groove: no black space.
2. The kick pumps the whole frame: +44% mean luminance, with the black floor rising from 19 to 35/255. It passes the house flash gate (which looks for a 0.1 rise in mean luminance), but on a bright wall it deserves a check against the broadcast rule's 25%-of-screen area test.
3. Outrun nostalgia is a genre mismatch for a dark Q-dance show. The pad laser fans are 2D, and the overlay adds a second, unrelated fan.

Cheap.

**4. Aurora Curtains — 5 (7 for worship).** The most naturally beautiful: layered curtains, a colour ramp by height, a lake reflection, the best black floor (8–11/255).
1. Low energy: the kick adds only 30% brightness and nothing ever hits.
2. The curtain hems read as dark hills, and the lake is a hard line, so it looks like a landscape wallpaper.
3. Three colours at once. The pad columns read like stage-light bars stuck onto the sky.

Cheap.

**5. Particle Galaxy — 4.** A clear bright core, a tilted disc, and stars that light up when you play their pitch class.
1. A hard colour seam on one side of the disc, from the same angle wrap: `sin(pattern·0.5)` at `vj-particle-galaxy.frag:148` (`crops/galaxy-arm-colour-seam.png`).
2. The stars render as smeared streaks ("rice grains") from the feedback rotation and read as noise at arena distance. The camera never moves.
3. The kick only flares the core (+48%). The arms are a soft smear on a muddy room colour.

**6. Laser Cathedral — 4 as built, highest ceiling.** Hot beam cores with a halo, aim that steps on the beat, and each pad firing its own head as a fan. At 1080p the pad fans are the most laser-show-like thing in the rig (`crops/laser-cathedral-pad-1080-topleft-1to1.png`).
1. Flat 2D. Twelve heads float as dots on a 4×3 screen grid, beams are lines in screen space, there is no stage origin, no perspective and no light in the air, and the arches are effectively invisible.
2. The idle beams are always on, so there is no black to cut from. The floor is 12–17/255 purple-brown, with four colours at once.
3. The kick has no weight (+64%, foci step).

Cost: the second most expensive per pixel, still fine.

**7. Reactor — 4.** A centred focal core; the kick reads (2.1×).
1. A small, soft blob on coloured fog (floor 17–21/255; the bass tints the whole room), with no environment or scale.
2. The shells read as blurry pink rings, not crisp glass (see the 1:1 crop). The shockwave stacks rings in the feedback.
3. The scene's own pad jets are tiny and buried under the overlay.

**8. Lissajous Chords — 3 (6–7 for piano).** A distinctive musical identity (the chord's just ratios drawn as an oscilloscope figure), single-colour discipline, and a neon beam with a hot head.
1. **The downbeat makes it darker.** The chord change restarts the figure's draw-on, so the kick frame has only 61% of the groove's light.
2. The polyline facets are visible, and the glow shows creases where the nearest segment switches (`crops/lissajous-faceting.png`).
3. One thin figure in a graticule, taking about 30% of the frame.

Cost: the most expensive. Up to 320 segments per pixel over about 85% of the pixels, and the whole chord analysis (`chordVoices`) is recomputed for every pixel even though it is the same for the whole frame; it belongs on the CPU as uniforms.

**9. Liquid Chrome — 3.** The environment-mapped chrome reads as glossy.
1. Weak composition: 5–7 small marbles scattered, no hero mass.
2. 2D metaballs with a faked surface normal read as pearls or plastic, not liquid metal; the 1:1 crop shows soft rims with a brown halo.
3. Muddy teal background (17/255) and low colourfulness (8.6).

**10. Fractal Bloom — 3.** Filling the frame and unfolding one level per beat is a good idea. Fully open, it becomes a dense lace of 1-px pastel lines with no focal point and risks moiré. The 1:1 crops show dark notches and triangular halo wedges where the nearest trap switches. The main musical event is a density swing (8% → 42% lit) rather than an impact. Colourfulness is low (14).

**11. Note Rain — 2 (5 for piano).** Mostly empty (2.6% lit) with thin bars. Ghost glow lines appear beside the bars, and the chord-change line draws a coloured checker stripe across the frame. No camera.

**12. LED Wall — 2.** A coarse LED matrix simulated on a real LED wall reads as a retro VU meter. The unlit dots stay visible, and the pads light rectangles.

**13. Chord Constellations — 2 (6 for piano).** 0.1% of the frame is lit: a few 1-px lines, invisible at festival distance.

## Images and data

Base folder: `<session scratchpad>\headline\audit\`

- **Contact sheets, one per scene (720p, all 13, 6 moments each with numbers):** `vj-<scene>--sheet.png`, e.g. `<session scratchpad>\headline\audit\vj-hyperspace--sheet.png`
- **1080p contact sheets (9 scenes):** `sheets1080\vj-<scene>--sheet.png`
- **Overviews:** `overview--2-groove.png`, `overview--4-pad.png`, `overview--1-quiet.png`, `overview--hd-groove-1080.png` (all 13 at 1080p)
- **Raw frames:** `frames\` (720p, 7 per scene), `frames1080\` (9 scenes), `frames-hd\` (1080p groove, all 13)
- **Crops:**
  - `crops\montage-detail-1..4.png` (1:1 at 1080p) and `crops\montage-dark-x4-1..4.png` (darkest area, brightened ×4)
  - `crops\hyperspace-pad-beam-zoom.png`, `crops\shockwave-ring-stack-lookoff.png`, `crops\note-glint-dotted-trails.png`
  - `crops\lissajous-faceting.png`, `crops\galaxy-arm-colour-seam.png`, `crops\geometry-hall-floor-moire.png`
  - `crops\laser-cathedral-pad-1080-topleft-1to1.png`
- **Numbers:** `metrics.json`, `sheets1080\metrics.json`, `crops.json`; cost log `frames-cost\log-1792875307225.json`; render logs `frames\log-1792874590545.json`, `run720.log`, `run1080.log`, `run1080full.log`
- **Machinery:** `audit_render.mjs` (virtual clock, moments, cost probe), `web\cost.html`, `sheets.py`, `crops.py`, `table.py`, `snapshot-sha256.txt`

## Sources

- TWOFIFTYK, Qlimax: https://twofiftyk.com/en/project/qlimax
- Backbone/TPi, Qlimax: https://www.backbone-international.com/talks/tpi-qlimax/
- Syncronorm, Qlimax 2023: https://www.syncronorm.com/newsitem/qlimax-2023-interview
- Vision Impossible, Qlimax: https://www.vision-impossible.nl/portfolio/qlimax/
- AVIXA, 3D illusion on LED walls: https://www.avixa.org/explore/articles/the-illusion-of-3d-on-led-walls-how-content-and-perspective-create-immersive-visuals
- Rick Jacobs on Resolume: https://resolume.com/blog/14343
- Ed Warren on EDM.com: https://edm.com/interviews/skrillex-fred-again-four-tet-msg-rave-how-ed-warren-designed-lighting-lasers/
- ILDA audience scanning: https://www.ilda.com/resources/Safety/audience-scanning_overview_latest.pdf
- House: `research/reviewed/keylab-liberation-2026-10-22/vj-festival-lessons-2026-10-24.md`, `research/reviewed/shader-school-2026-10-13/color-post.md`, the shader-craft skill, and `arsenal/web/glsl/` (`displayOut`, `tmPbrNeutral`, `ray/aa3`)

Corpus study notes I'd learn techniques from (techniques only, no code):

| Scene | Study notes |
|---|---|
| Laser Cathedral | WlVyRV "Dry ice 2", tsScDG volumetric sample, DtXfDr "Discoteq 2" |
| Hyperspace | MfjyWK "Starry planes" (CC0) |
| Reactor | XsjXRm "Plasma Globe" |
| Liquid Chrome | llK3Dy "Rhodium liquid carbon" |
| Lissajous | ldSfWV "OscilloStereoXY Trippy Donut" |
| Geometry Hall | NlK3Wt "Cyberspace data warehouse", 4tcXRr "Alien Core" |

---

## Study: arsenal (verbatim)

# Headline hardstyle visuals: what our own shader arsenal can build, technique by technique (2026-10-24)

This lane was read-only on the repo. Nothing tracked was changed. I wrote scratch files only, plus the job and run records the render harness keeps under `state/` (gitignored). Lab server on port 8931, headless Chrome on SwiftShader, the house GPU lock respected; that lock was busy with the headline-audit lane for about 20 minutes.

## 0. What I checked, and five findings

**What we have:**
- **The house module library** (`E:\AI-Setup\arsenal\web\glsl\`): 68 modules and 68 test cards.
- **The atlas** (`E:\AI-Setup\arsenal\shaders\atlas.json`): it now lists 581 parts in 81 categories, not 566.
  - P0 199, P1 265, P2 117 parts; 25 groups.
  - By matching function names to library code, about 240 parts exist today: P0 198 of 199, P1 37 of 265, P2 5 of 117.
  - 6 of the 25 groups are built: aurora-band, aurora-sheets, glow-xray, hex-neon, neon-line, studio-object.
- **Shader Shool notes:** 42 study notes, 6 research reports and the in-flight drafts.
- **Presets:** 13 VJ presets and 8 Play presets.
- **The private corpus:** 335 shaders, read as learning only. No corpus code was copied anywhere.

**Finding 1. The VJ pipeline throws away HDR before the look pass.**
- Every VJ preset clamps to 0..1 and encodes its own output (`pow(col, 1/2.2)` or `1 - exp(-x)` and then `clamp`). Example: the end of `vj-geometry-hall.frag`.
- `vj-fx.js` POST then decodes that clamped output with `pow 2.2` and thresholds the bloom on display values (luminance 0.12 to 0.55). This happens even when the framebuffer is RGBA16F.
- So a laser core at 20 times white and a white wall at 1.0 bloom the same.
- White-hot cores, beams in haze, fire and lens effects all need scene-linear HDR to reach the look pass. The order there should be: bloom on linear HDR, then one tone curve (`post/display-out.glsl` already does exactly this chain), then a static dither.
- This is a seam ruling for whoever owns `vj.js` and `vj-fx.js`; the impact lane is editing them now.

**Finding 2. The VJ presets don't compose the library; they paste reduced copies of it.**
- `vj-laser-cathedral.frag` says so itself: "neon-line.glsl, reduced here".
- The composer works today. I verified `py -m arsenal shader lib compose <42 modules> --target webgl2`: exit 0, 2,464 lines, the `mapScene` and `densityAt` hook prototypes written in.
- Using it means a module fix reaches every VJ scene.

**Finding 3. The library is strong on physics plumbing and has almost no headline content.**
- Strong: volume integration, phase functions, fog, glow profiles, marchers, normals, cone AA, SDF ops, tone curves, dither, feedback decay.
- Missing: no fire, no lightning, no beam-in-haze, no smoke group, no bloom chain, no GGX, no lens module, no curl or cellular noise, no 3D noise texture, no particle or starfield module.

**Finding 4. The house kit composes, compiles and renders together (receipt).**
- I wrote a scratch probe scene: the composed kit plus about 100 fresh lines.
  - A colonnade, a monolith with a ring, six spot beams, and a backlight.
  - Haze in a 32-step jittered march using `volStepScatter` and `phaseHG`.
  - The monolith's god-ray shadow is one closed-form `ixBox` test per step.
  - The finish is `displayOut` with the ACES fit.
- It compiled on SwiftShader (`compile ok`, 2,559 lines) and rendered at t = 0 and t = 2.
  - Mean luma was 10.4 out of 255, so the black space survived the haze.
  - The CPU frame times (94 and 144 ms at 480×270) say nothing about GPU cost.
- The frame shows a pitfall: a glare I added after the march shines straight through the monolith. Any analytic glare must be shadowed too.

**Finding 5. The licence guard is strict on fresh code.**
- `licence_line.py` found 5 breaches in my roughly 100 lines of fresh probe code.
  - The `mainImage` boilerplate matches 298 corpus shaders.
  - A plain 32-step raymarch loop header followed by its first ray-step line matches 30. (The code itself is left out of this record: quoted, it trips the same guard.)
  - Constant vectors such as `vec3(0.0, 0.0, 1.0)` trip it, because numbers are compared by value.
- What helps:
  - The VJ host template (`main()`, `u_res`) avoids the `mainImage` boilerplate.
  - `licence_line_allow.json` holds 2 entries today and is the sanctioned place for textbook idioms.
  - Budget a licence-line pass for every new module.

## 1. The cost model used below

- **Mid-range reference:** about 10 to 13 TFLOPS FP32 single-issue (RTX 3060 class). Effective throughput is about a quarter to a half of peak (method from `gpu-perf-glsl.md` §3.8).
- **Rule of thumb at 1080p:** about 0.5 ms per 1,000 operations per pixel. A 64-step march over a 100-operation field is therefore about 3 ms.
- **The budget:** the VJ page renders two sets during a transition, plus the look pass. So each scene should stay under about 6 ms at 1080p on mid-range.
- **Daniel's own card:** an RX 9070 XT (about 24 TFLOPS single-issue, per the house report) at 4K costs about twice mid-range at 1080p. Render the scenes at 1080p internally and let the VJ watchdog's scale rule handle the rest.
- **What these numbers are:** every ms figure is an estimate from operation counts. None is a GPU measurement.

## 2. The technique menu

Each entry gives:
- **Have:** the house module that implements it (all paths under `E:\AI-Setup\arsenal\web\glsl\`).
- **Missing:** what is not in the library (atlas ids).
- **Teachers:** the corpus shaders that teach it best (study only, no code).
- **Cost:** at 1080p on mid-range.
- **Pitfalls.**

Some entries add a **Real shows** anchor with a source.

### 1. Volumetric light shafts and god rays

- **Have:**
  - `volume/integrate.glsl`: `volStepScatter`, the energy-conserving segment, so brightness doesn't depend on the step count. Also `volStepEmit` and `volResolve`.
  - `volume/phase.glsl`: `phaseHG`.
  - `volume/march.glsl`: `volLightOneTap`.
  - `ray/march.glsl`: `rmJitterStart`, `rmPassStep`.
  - `noise/dither-masks.glsl`: `dthIgn`, a static jitter.
  - `ray/intersect.glsl`: `ixBox`, `ixSphere`, `rmClipToBox`, used as analytic occluders and bounds.
  - House precedent: `scripts/aurora-shader.js`, a 26-step marched medium where the god rays come from the cause.
- **Missing:**
  - Shaft functions: `raysRadial` (G7.05), `raysPatternShell` (G7.06), the `rays_litFraction` template.
  - Light helpers: `litSpotCone` (F4.02), `glowPointInscatter` (F9.10, analytic in-scatter), `volLightMarch` (G5.03).
  - The `volume-fog` group (P1).
  - A baked light volume (WebGL2 `TEXTURE_3D`).
- **Teachers:**
  - `XlBSRz` (SebH): energy-conserving against naive integration side by side; a per-step shadow march and why it is expensive.
  - `tsScDG`:
    - `T_before - T_after` as the in-scatter weight;
    - `max(fixed, sdf)` steps for both view and shadow rays;
    - a telephoto lens that makes the subject monumental.
  - `tdjBR1`: bakes density and light into a low-resolution volume once, then marches cheap lookups.
  - `cdG3Wd` (Xor, Dust): one stochastic shadow probe per pixel from a random point along the ray, accumulated over frames.
  - `4lj3Ww`: a pattern that depends only on direction, extruded through a shell, gives radial shafts with no shadow rays.
  - `WlVyRV`: real self-shadowing is what sells depth.
- **Cost:**
  - Analytic spot or point in-scatter: about 50 to 100 operations per light, so 12 lights cost about 0.3 to 0.6 ms.
  - A 24 to 32-step jittered march with analytic cones and occluders: about 3 to 4 ms at full resolution, about 1 ms at half resolution with an upsample.
  - The same march with an SDF shadow probe per step: about 10 times that; not viable live. Bake it or keep it analytic.
  - Screen-space radial blur with 32 to 48 taps at quarter resolution: about 0.3 to 0.5 ms.
- **Pitfalls:**
  - Fixed step positions give concentric rings: use a static jitter.
  - Per-frame jitter gives crawling grain (shader-craft floor 8).
  - Lighting by "add, then dim" changes brightness with the step count.
  - The phase cosine is `mu = dot(viewDir, toLight)`; flip it and the glow lands on the wrong side.
  - Screen-space shafts draw in front of foreground objects and flicker near the frame edge.
  - The inverse-square spike at the beam's apex.
  - An unshadowed glare shows through occluders (seen in the probe).
  - A beam aimed into the lens is a full-frame flash.
- **Real shows:** Qlimax 2023 was designed around "the contrast between light and darkness" ([Syncronorm](https://www.syncronorm.com/newsitem/qlimax-2023-interview)).

### 2. Fog and haze

- **Have:** `atmos/fog.glsl` (`fogExp` only), `atmos/sky.glsl`, `volume/density.glsl` (`densFromSDF`), and the noise family (value, gradient, fbm, warp, triangle).
- **Missing:**
  - `fogHeightTau` (G7.03): analytic floor-pooling stage haze, stable for horizontal rays.
  - `fogSplit` and `fogSunTint` (G7.04).
  - `fogMipLevel` (G7.07).
  - Tileable 3D noise (B6) and a 3D noise-texture bake.
- **Teachers:**
  - `3l23Rh` (Protean clouds): density-driven steps, cheap deformed-grid noise; the author says it runs at 1080p.
  - `XtS3DD`: clouds take the sky's colour; a scout march first.
  - `4slGWM`: no march at all; a dense core plus a ramped skin.
  - `tsScDG`: a ground-fog skirt from one smooth union with a huge k.
  - `ltffzl`: fog chosen by which mip level to read.
- **Cost:** analytic fog is about 10 to 40 operations, effectively free. Noise haze is paid only inside the beam march.
- **Pitfalls:**
  - A fog colour that doesn't match the backdrop leaves a seam.
  - Use the ray's travel distance, not view depth.
  - An ambient haze lift destroys the black space (shader-craft ceiling: "46% of the screen lit was wrong").
  - Haze should modulate slowly, never with per-frame noise.
- **Real shows:** beams need haze to exist at all ([ILDA](https://www.ilda.com/hazefoglasers.htm), [Laserworld FAQ](https://www.laserworld.com/en/laser-technical-faq/1132-do-i-need-fog-or-haze-to-make-the-laser-beams-visible.html)).

### 3. Fire and embers

- **Have:**
  - `colour/palette.glsl` `palHeatPowers`: channels saturate in turn, from ember to white.
  - `light/glow.glsl` `glowHotCore` and `glowStepCount`.
  - `volStepEmit`.
  - `groups/glow-xray.glsl`, which has an Ember palette.
  - `rmPassStep`, `noise/warp.glsl`, `motion/envelope.glsl`.
- **Missing:** no fire module, and no fire category in the atlas. Specifically:
  - blackbody colour from a temperature;
  - a turbulence domain (successive sine waves of growing frequency);
  - flame-shape helpers (turbulence that grows with height, upward advection);
  - curl noise (B5) for embers;
  - cellular noise (B2);
  - `glowComet` (F9.11);
  - the flicker module (I2);
  - the `plasma-electric` group (P1).
- **Teachers:**
  - `MdX3zr` (Flame):
    - brightness is how long the ray lingered;
    - `abs` plus a minimum step lets the ray pass through the shell;
    - overdriven channels clip in order, like a blackbody;
    - turbulence proportional to height.
  - `3XXSWS` (Xor, 3D Fire): a hollow cone, sine turbulence octaves, glow from 1/d, `tanh` at the end.
  - `MsXGRf` (iq, Flames): inverted and twisted space. Restrictive licence: look only.
  - `XsXSWS`: 2D flame columns.
  - `MlKSWm`: sparks on an offset scrolling cell grid; fire colour from f, f³ and f⁹. All rights reserved: study only.
  - `Wtc3W2`: the flame as a deformed ellipsoid SDF marched as emission, area lights, mip bloom.
  - `lsySzd` / `MdKXzc`: an explosion volume.
  - `l3cfW4`: comet tails and exponential flicker.
- **Cost:**
  - A 2D flame field: about 0.2 to 0.4 ms.
  - A turbulent shell march: about 2 to 3 ms.
  - An fbm volume with arithmetic 3D noise: 30 ms or more. Viable only with a 3D noise texture (2 to 4 ms) or at half resolution.
  - Embers: about 0.1 ms.
- **Pitfalls:**
  - Add the fire as light; don't alpha-blend it.
  - Colours must come from channels saturating in order; a hue lerp passes through mud.
  - Leave black between the tongues.
  - A full-frame fire wash is a saturated-red flash candidate. Keep flames in bounded areas and gate the big bursts.
  - Re-seeding noise each frame makes the flame boil.
  - Rise speeds counted per frame run four times too fast at 240 Hz.
- **Real shows:** the Defqon.1 Endshow is a fully timecoded 20-minute show of lights, flamethrowers, lasers and fireworks ([Lights in Motion](https://www.lightsinmotion.nl/en/defqon-1/)). The 2026 endshow was filmed without an audience ([DJ Mag](https://djmag.com/news/defqon1-share-2026-endshow-filmed-without-audience-after-heatwave-cancellation-watch)).

### 4. Smoke

- **Have:** the volume family, `densFromSDF`, the noise family, and `sim/feedback.glsl` (`fbDecay`, `simSanitize`).
- **Missing:**
  - Cloud lighting (G3: powder, multiple-scattering octaves).
  - Density shaping (G4.02 to G4.06).
  - `volLightMarch`, curl noise, stable fluids (J3), the `fluid-fog-2d` group.
  - A 3D noise texture.
- **Teachers:**
  - `3l23Rh`, `XtS3DD`, `tsScDG`, `4slGWM`.
  - `WlVyRV`: a 2D simulation in a 3D costume.
  - `XslGRr` (iq, Clouds): slab bounds, octave level of detail, a one-sample derivative light. Restrictive licence.
  - `4s23zz`: the warp's intermediate fields are the palette.
- **Cost:**
  - Arithmetic-noise volume: about 25 ms.
  - With a 3D noise texture: about 2 ms, or 0.5 ms at half resolution.
  - A 2D stable-fluids pass: about 0.3 to 0.6 ms, but multipass.
- **Pitfalls:**
  - Grey "dirty cotton": no multiple scattering, albedo too low.
  - Hard slab tops; visible tiling.
  - 8-bit simulations get stuck around byte 24 or 25.
  - One NaN poisons the loop.
  - Smoke that fills the frame kills contrast. Light it from behind, with the beams.

### 5. Lightning

- **Have:**
  - `groups/neon-line.glsl`: a Lorentzian core and halo, `neonPathStep` for polylines, max-combine.
  - `draw2/sdf2.glsl` `sd2Segment`.
  - `noise/triangle.glsl` and `core/shaping.glsl` `shpTri`, for crackle.
  - `glowHotCore`.
  - `motion/envelope.glsl` `envFlashSafe`, the flash gate.
  - `hash/pcg.glsl`.
- **Missing:**
  - A bolt generator: a midpoint-displaced polyline with branches and a per-strike seed.
  - `flkSignedLightning` (I2.03).
  - A scene-flash helper that goes through the flash gate.
- **Teachers:**
  - `XsjXRm` (Plasma Globe):
    - the segment's direction depends on the radius, so one line becomes a bolt;
    - triangle waves, not sines;
    - fatten the bolt by shrinking space;
    - a short fixed-step walk makes it glow;
    - max across the 13 bolts.
  - `ldlXRS`: a domain displaced by two ridged fbm calls.
  - `XXyGzh`: a `tanh`-warped coordinate loop.
  - `ltffzl`: the exemplar for lightning flicker.
- **Cost:**
  - Four 2D bolts of 16 segments: about 0.8 ms, or about 0.2 ms with a bounding box per bolt.
  - A 3D globe-style render: 3 to 5 ms.
- **Pitfalls:**
  - A sky-wide flash is a full-frame flash: no more than 3 per second, never saturated red.
  - Each return stroke counts as its own flash.
  - Additive bolts wash out; combine with max.
  - Time a bolt's life in seconds, not frames.

### 6. Monumental SDF architecture and ritual objects

- **Have:**
  - `sdf/shapes.glsl`: box, round box, cylinder, capped cone, torus, capsule, hex prism, octahedron, `sbPolyhedron` (19 planes), `sbSuperquadric`.
  - `sdf/combine.glsl`: smooth min, smooth max, onion, `opDisplace` with its Lipschitz figure.
  - `sdf/domain3.glsl`: limited repetition, polar, mirror, twist with `lipTwist`, bend, `domFoldIcosa`, inversion.
  - `ray/march.glsl` (sphere trace, relaxed, backtrack), `ray/normals.glsl`, `light/visibility.glsl`.
  - `groups/studio-object.glsl` and `groups/glow-xray.glsl`.
- **Missing:**
  - Lifting 2D to 3D (D2: revolve and extrude, for columns, arches, extruded sigils).
  - Surface detail (D6).
  - 3D fractals (D5: Menger, Mandelbox, KIFS, Apollonian).
  - Architectural seams (D3.16: chamfer, stairs, groove).
  - `sdHelix`: the atlas places it in `sdf/shapes.glsl`, but the file doesn't have it.
  - The pegboard march `rmCellClamped` (E3.08).
- **Teachers:**
  - `tsScDG`: a 16° telephoto lens from high up makes the subject monumental.
  - `ldScDh` (iq, Greek Temple): false perspective; ambient occlusion and bounce light painted by hand. Restrictive licence.
  - `WlKXzm` (Orbital Megastructure, CC0): bounding boxes, symmetry, scale cues that make it feel big.
  - `XtsSWs` (Skyline, CC0).
  - Fractal flythroughs: `Mdf3z7`, `4s3SRN`, `XsBXWt`, `tsXBzS`.
  - `ttKGDt` (Phantom Star): IFS box folds, polar repetition, glow without stopping at surfaces.
  - `7cjGRR`: carve, don't build.
  - `llVXRd`: fold first, tile once.
  - `cs2GWD`: a catalogue of modules on a grid.
  - `4lj3Ww`: a pierced reliquary with a molten core.
- **Cost:**
  - 96 steps over a 60 to 150-operation field, plus normals, AO and one soft shadow: about 4 to 10 ms.
  - An IFS march: about 5 ms.
  - Levers, in this order: bounding volumes, analytic range clipping, a footprint epsilon, relaxation, and only then fewer pixels.
- **Pitfalls:**
  - Fields that overestimate distance leave holes: divide by the Lipschitz figure.
  - On ANGLE, the D3D compiler unrolls loops, which can freeze the first frame for seconds: use `core/compile.glsl` `unrollBarrier`.
  - The 2-second GPU watchdog is a whole-machine risk on this host.
  - Scale needs a telephoto lens, a slow push, fog and repetition. AVIXA lists the cues: forced perspective, shading and shadows, motion parallax, lighting and depth of field ([AVIXA](https://www.avixa.org/explore/articles/the-illusion-of-3d-on-led-walls-how-content-and-perspective-create-immersive-visuals)).
- **Real shows:**
  - Qlimax 2017's theme was "Temple of Light" ([Behance trailer](https://www.behance.net/gallery/70209969/Qlimax-Temple-of-light-thematic-trailer/modules/412439477); the page returned 403, so this rests on the search summary).
  - Qlimax used two LED layers, the header wall translucent ([Backbone/TPi](https://www.backbone-international.com/talks/tpi-qlimax/)).

### 7. Metallic and PBR shading

- **Have:**
  - `light/fresnel.glsl`: Schlick with a coloured F0.
  - `light/specular.glsl`: normalised Blinn-Phong only.
  - `light/diffuse.glsl`.
  - `light/env.glsl`: an analytic softbox studio and a floor pool.
  - `light/rigs.glsl`: `rigStudio`, `LitSurface`.
  - `light/lights.glsl`, `light/visibility.glsl`, `light/glass.glsl`.
- **Missing:**
  - GGX D and Smith visibility (F2.03): no microfacet model at all.
  - Specular AA (F2.05) and energy compensation (F2.06).
  - The material module (F11).
  - The analytic environment BRDF (F6.04).
  - Thin film (F8).
  - Area and tube lights (F4.04, F4.05), which is how laser tubes and LED strips would appear in chrome.
- **Teachers:**
  - `3XdXRr` (CC0): a dark mirror, a softbox brighter at its rim.
  - `43jXWt` (CC0) and `XljGDz` (CC0): a giant softbox with a soft fade.
  - `lscBW4`: split-sum image-based lighting.
  - `4sSfzK`: a physically based shading teaching UI.
  - `llK3Dy`, `WdVXWy` (thin-film flow), and `7cjGRR` (reflection used as a multiplier).
- **Cost:** about 50 operations per light, so 12 lights are about 0.3 ms on the pixels that hit something. A true reflection is a second march, which doubles the cost.
- **Pitfalls:**
  - Metal with nothing to reflect looks black: design the environment first.
  - F0 of 0.04 for dielectrics, a coloured F0 for metals.
  - Tiny highlights sparkle at 4K.
  - Roughness must be squared.

### 8. Tunnels

- **Have:**
  - `ray/camera.glsl`: `camBanked`, `pathLissajous3`, `camBarrel`.
  - `draw2/domain2.glsl` and `sdf/domain3.glsl`: polar and repetition.
  - `groups/glow-xray.glsl`, `groups/hex-neon.glsl`.
  - The presets `vj-hyperspace` and `feedback-tunnel`.
- **Missing:** the `flight-tunnel` and `zoom-conveyor` groups (P1), the plane-stack march (E3.09), `pathRider` (I4.02).
- **Teachers:**
  - `MfjyWK` (CC0): at most 16 exact ray-plane hits; one path drives everything; exact derivatives for banking.
  - `7cjGRR`, `WfcGWj` (CC0 gyroid cave).
  - `wsl3WB`: three layers on a conveyor belt.
  - `ttKGDt`, `3sXyRN` / `tdjfDR`, `MtXczn`.
- **Cost:**
  - A 2D polar tunnel: free.
  - A plane stack: about 0.3 ms.
  - An SDF tunnel: 2 to 3 ms.
  - An IFS tunnel: about 5 ms.
- **Pitfalls:**
  - The vanishing point becomes a hot spot: keep the centre dark.
  - Fast forward motion over striped walls hits the stripe rule. Smooth flow in one direction is exempt in BT.1702.
  - Set speeds per second.
  - Golfed rotation matrices drift.

### 9. Laser beams with haze scattering

- **Have:**
  - `groups/neon-line.glsl`: Lorentzian and two-Gaussian profiles, `aaWire`, a hot core, max-combine, defocus.
  - `composite/blend.glsl` `cmpMax`.
  - `phaseHG`.
  - `vj-laser-cathedral.frag` already draws 12 heads with fans at constant cost per head, and its halos scale with `res.y / 1080`.
- **Missing:**
  - A 3D beam module: the view ray's closest approach to a beam segment, plus the in-scatter integral across the beam's chord. With `phaseHG`, beams pointing toward the camera would glow brighter, as real ones do.
  - Sheet, cone and fan shapes.
  - Dimming for beams aimed at the lens.
  - Haze speckle along the beam.
- **Teachers:**
  - `4slGz4` (iq, Volumetric Lines): analytic ray-to-segment distance, audio sync. Restrictive licence.
  - `ldSfWV`: a Lorentzian beam; brightness is dwell time.
  - `DtXfDr`: detuned pinned strings; blur that grows toward the edges.
  - `MtXczn`: max, not add.
  - `l3cfW4`, `XfXGz4`.
- **Cost:** 2D fans about 0.3 to 0.5 ms; 48 analytic 3D beams about 1 ms, plus about 0.2 ms for haze.
- **Pitfalls:**
  - Beams look like scratches on glass unless the halo is modulated by haze.
  - Added crossings blow out to white.
  - A beam that sweeps the frame is a flash.
- **Real shows:** design for how the light looks in the haze (Corbin Sharpe, [EDM Identity](https://edmidentity.com/2026/01/22/levity-lasers-corbin-sharpe-interview/)).

### 10. Particle fields

- **Have:** `hash/pcg.glsl` (`cellU2`, `cellU3`), `draw2/domain2.glsl` `domRepeat2`, `draw2/lattice.glsl`, `draw2/pattern.glsl` `patCellDelay`, the glow profiles.
- **Missing:**
  - `starsDirCells` (G6.03).
  - A gather-based particle module.
  - Curl noise.
  - `glowComet`.
  - Particle simulation (J5). The host is fragment-only, so stateful particles need a points pipeline added.
- **Teachers:**
  - `Xdl3D2` (CC0): a 2D grid marched with one star per cell.
  - `MlKSWm`, `l3cfW4`.
  - `XlfGRj` (Star Nest, MIT).
  - `MslGWN`, `MdsXWM`, `Mts3zM`.
- **Cost:** a 2D three-layer gather about 0.25 ms; a 3D grid march 0.5 to 1 ms.
- **Pitfalls:**
  - "Oatmeal": every particle unique, and all of them look the same.
  - A visible grid when particles sit at cell centres.
  - Sub-pixel twinkle: clamp the size to 1 px and dim instead.
  - The sine hash collapses at large coordinates.

### 11. Feedback trails

- **Have:**
  - `sim/feedback.glsl`: `fbDecay` with its floor step, `simSanitize`.
  - `core/clock.glsl`: `clkKeep`, `clkAlpha`.
  - `cmpMax`, and the `u_prev` ping-pong buffer.
- **Missing:**
  - `fbWarp`, `fbSoftGate`, `fbPhosphor`, `fireflyClamp` (J6.02 to J6.06).
  - The `feedback-trail` group.
  - Analytic motion blur.
- **Teachers:**
  - `43jXWt`: a soft threshold that prevents white-out.
  - `ldSfWV`: phosphor; `tanh` bounds the loop.
  - `ltdcW7`: history computed as a function of time, with no buffer.
  - `MdSGDm` (MIT): analytic motion blur.
- **Cost:** about 0.1 ms.
- **Pitfalls:**
  - Decay set per frame runs four times faster at 240 Hz.
  - 8-bit residue never fades.
  - NaN.
  - Full-frame trails keep bright area on screen, which matters for flash accounting.

### 12. Glow and bloom

- **Have:**
  - In-field: `light/glow.glsl`, `groups/glow-xray.glsl`, `groups/neon-line.glsl`.
  - Post: the two-level bloom in `vj-fx.js`, whose mean is capped so it can never add a flash. Keep that cap.
- **Missing:**
  - `post/bloom.glsl` (H7.06 to H7.07): the Karis-weighted 13-tap mip chain, tent upsample, dual and Kawase filters, anamorphic streaks.
  - `glowToneBloom` (H5.12).
  - The HDR seam (finding 1).
- **Teachers:**
  - `lstSRS`: four passes, bicubic upsampling.
  - `Wtc3W2`: bloom from jittered mip reads.
  - `llK3Dy`: HDR before the blur.
  - `MdsXWM`.
- **Cost:** a mip chain about 0.4 to 0.8 ms; today's bloom about 0.2 to 0.3 ms.
- **Pitfalls:**
  - Bloom on clipped values (the VJ rig today).
  - Fireflies make it flicker.
  - Bloom as a fog over everything.

### 13. Filmic tone mapping

- **Have:**
  - `colour/tone.glsl`: `tmTanh`, `tmExp`, `tmReinhard`, `tmAcesFit`, `tmPbrNeutral`, `displayHueSafeGamma`.
  - `legacy/tone-superlinear.glsl`.
  - `post/display-out.glsl`, `colour/grade.glsl`.
- **Missing:** AgX (H5.09), Hable, Uchimura and Lottes (H5.13), a LUT path. The VJ presets use none of the existing curves.
- **Teachers:** `ttScDc`, `MfjyWK` and `43jXWt` (the ACES fit); `l3cfW4` and `ldSfWV` (`tanh` whitens hot cores); `lsySzd`.
- **Cost:** free.
- **Pitfalls:**
  - Per-channel curves shift the hue of saturated highlights; hue-preserving curves lose the white-hot core. Choose per element: lasers want white cores, washes want their hue kept.
  - Tone-map once. Today it happens in each preset and again implicitly in the look pass.
  - The superlinear lift goes before `tanh`, never after.

### 14. Dithering against banding

- **Have:** `noise/dither-masks.glsl` (`dthIgn`, `dthR2`, triangular), `post/dither.glsl` (`ditherOut`), all static.
- **Missing:** a blue-noise texture (H8.02); `grainEnergy` and `grainFilm` (H8.03).
- **Teachers:** `ffG3Rc`, `XsSGDh`, `ldSfWV`, `XdcyDM` (dither both the refraction index and the step length).
- **Cost:** free.
- **Pitfalls:**
  - Per-frame dither crawls; it was removed from the house surfaces at Daniel's request.
  - `vj-fx.js` POST re-seeds both its 8-bit dither and its grain with `u_seed` every frame. Check that against shader-craft floor 8.
  - Dither after the encode, at the final 8-bit write.
  - Haze and smoke gradients are where banding shows.

### 15. Anti-aliasing for SDF edges

- **Have:**
  - `draw2/aa.glsl`: `aaFill`, `aaStroke`, `aaWire`.
  - `core/frame.glsl`: `uvPixel`, `uvFootprint`.
  - `ray/aa3.glsl`: `aaConeCoverage`, from the closest approach the march already recorded, and `aaDiscriminantEdge`.
- **Missing:** supersampling (E5.04), TAA (J6.07), specular AA, iso-line drawing (C3).
- **Teachers:** `NslGRN` (exact intersections, no march, razor-stable), `XsSGDh`, `Ms2XWc`, `mtScRc` (CC0, FXAA on a fractal).
- **Cost:** analytic and cone coverage are free; 2×2 supersampling costs 4×; FXAA or TAA about 0.2 to 0.3 ms.
- **Pitfalls:**
  - `fwidth` of a cell id shreds whole rows.
  - A hit-or-miss boolean is a staircase.
  - TAA ghosts on beat cuts.

### 16. Depth of field

- **Have:** only `neon-line`'s `defocus` parameter.
- **Missing:** `bokehVogel` (H7.09); circle of confusion in alpha.
- **Teachers:**
  - `llK3Dy`: the scene pass writes the blur amount into alpha; HDR makes defocused highlights into discs; the blur also hides a broken distance field.
  - `4d2Xzw`: a golden-angle spiral gather.
  - `DtXfDr`: fake depth of field from distance to the edge.
- **Cost:** 32 to 48 taps at half resolution, 0.4 to 0.8 ms.
- **Pitfalls:**
  - LDR input gives grey smudges.
  - Foreground bleeds over a sharp background.
  - A focus pull on a hit is impact without adding light (festival lesson 9).

### 17. Lens and sensor effects

- **Have:**
  - `post/vignette.glsl` `vigCorner`; `ray/camera.glsl` `camBarrel`.
  - `vj-fx.js`: aberration on hits, vignette, grain.
  - The Play preset `chromatic-bloom`.
- **Missing:**
  - `post/lens.glsl`: distortion, RGB and spectral aberration, flare ghosts, flare blades.
  - Anamorphic streaks and halation.
  - CRT (K2) and rolling shutter (K1.10).
- **Teachers:**
  - `4sX3Rs` (Unlicense header): analytic ghosts along the line through the centre.
  - `XtS3DD`: a sun core in halos with a pinpoint.
  - `lfscD7`: wavelength equals shutter time, so colour appears only where the image changes.
  - `ldSfWV`: CRT.
- **Cost:** about 0.1 to 0.3 ms each.
- **Pitfalls:**
  - Aberration everywhere looks cheap; use it on hits only.
  - A flare needs an on-screen source and occlusion.
  - Normalise the vignette by the real corner distance.
  - Flares count toward flash area.

## 3. How the menu combines (headline recipes)

- **Anti-climax, "dark ritual":**
  - Monumental SDF nave under a telephoto lens, a slow push, analytic height haze.
  - A backlit monolith whose shafts are cast by analytic occluders.
  - Two colours, mostly black.
  - The kick is mass (camera shove, hit-stop); the screech is thin, high 3D beams.
- **Climax:**
  - Flame columns as discrete bounded bursts on phrase hits, embers on curl noise, smoke lit from behind.
  - Beam fans through the smoke, white-hot cores through `tanh` or ACES, then HDR bloom.
- **Build into the drop:** lightning inside a cloud deck (flashes gated), cutting to a plane-stack or IFS tunnel on the drop.

**Real-show reference for live versus timecoded content:** TWOFIFTYK made nearly an hour of timecoded visuals for 17 Qlimax shows in TouchDesigner and split VJ duty between timecode and live; "not a single piece of content was recycled" ([TWOFIFTYK](https://twofiftyk.com/en/project/qlimax)).

## 4. Gaps we must write ourselves (ranked by headline impact)

1. **The HDR seam (a ruling).** Presets output scene-linear, unclamped light into RGBA16F. The look pass does bloom, then one `displayOut` curve, then a static dither. Keep the bloom mean cap, measured in linear.
2. **Compose VJ scenes from the library** with `shader lib compose`, instead of pasting reduced copies.
3. **`post/bloom.glsl`:** the Karis 13-tap mip chain, tent upsample, anamorphic streak, `fireflyClamp`, an HDR sanitiser.
4. **A beam-in-haze module:** 3D analytic beams, chord in-scatter with `phaseHG`, `litSpotCone`, `glowPointInscatter`, `fogHeightTau`, attenuation for beams aimed at the lens.
5. **A 3D noise texture bake** (WebGL2 `TEXTURE_3D`, tileable noise B6) plus curl noise (B5) and cellular noise (B2). This is the 5 to 10× lever for fire and smoke.
6. **Fire:** a blackbody colour, a turbulence domain, a flame-column shape, embers (cell grid, curl drift, `glowComet`, flicker), and a bounded-burst envelope that goes through the flash gate.
7. **Lightning:** a branching bolt generator, `flkSignedLightning`, and a gated scene flash (the `plasma-electric` group).
8. **The `volume-fog` group:** cloud lighting (G3), density shaping (G4), `volLightMarch`, and a baked light-volume path.
9. **Architecture:** `sdf/lift.glsl` (revolve, extrude), D3.16 seams, `sdf/fractal3.glsl` (KIFS, Menger, Mandelbox), `sdHelix`, `rmCellClamped`.
10. **Materials:** GGX and Smith, the environment BRDF approximation, `light/material.glsl`, thin film, tube and line lights.
11. **`post/lens.glsl`:** distortion, aberration, flare ghosts and blades, `bokehVogel` with circle of confusion in alpha.
12. **Feedback extras:** `fbWarp`, `fbSoftGate`, `fbPhosphor`; analytic motion blur.
13. **Particles:** `starsDirCells` and a gather particle module. A host points pipeline only if stateful particles are wanted.
14. **Tone:** AgX; blue-noise dither.
15. **Process:** a test card for each new module, a licence-line allowlist review for textbook idioms, and a ruling on the per-frame grain and dither in the VJ look pass.

## Files

- Module library: `E:\AI-Setup\arsenal\web\glsl\`
- Atlas: `E:\AI-Setup\arsenal\shaders\atlas.json`
- Shader School notes: `E:\AI-Setup\state\arsenal\shaders\study\`
- Research reports: `E:\AI-Setup\research\reviewed\shader-school-2026-10-13\`
- Festival lessons: `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\vj-festival-lessons-2026-10-24.md`
- Look pass: `E:\AI-Setup\arsenal\web\vj-fx.js`
- Probe, all in `<session scratchpad>\`:
  - `headline-kit.glsl`
  - `headline-probe.frag`
  - `probe-main.glsl`
  - `probe-render\t0.00.png`
  - `probe-render\t2.00.png`
  - `probe-render2.json`
  - `ll.json` (licence-line report)
- Harness records the render wrote:
  - `E:\AI-Setup\state\arsenal\shaders\jobs\local-headline-probe-30a427559f.json`
  - `E:\AI-Setup\state\arsenal\shaders\runs\20261024-16*`

## Sources

- https://www.syncronorm.com/newsitem/qlimax-2023-interview
- https://www.backbone-international.com/talks/tpi-qlimax/
- https://twofiftyk.com/en/project/qlimax
- https://www.vision-impossible.nl/portfolio/qlimax/
- https://www.lightsinmotion.nl/en/defqon-1/
- https://djmag.com/news/defqon1-share-2026-endshow-filmed-without-audience-after-heatwave-cancellation-watch
- https://www.avixa.org/explore/articles/the-illusion-of-3d-on-led-walls-how-content-and-perspective-create-immersive-visuals
- https://www.ilda.com/hazefoglasers.htm
- https://www.laserworld.com/en/laser-technical-faq/1132-do-i-need-fog-or-haze-to-make-the-laser-beams-visible.html
- https://edmidentity.com/2026/01/22/levity-lasers-corbin-sharpe-interview/
- https://www.behance.net/gallery/70209969/Qlimax-Temple-of-light-thematic-trailer/modules/412439477

---

## Study: craft (verbatim)

# Real-time headline craft: technique and GPU budget guide for the KeyLab VJ rig

This was read-only study. I wrote nothing to the repo, opened no browser and touched no server. Code references are to commit ce0f492b (2026-10-23). The impact pass may move these lines.

Confidence tags: **[H]** I read the primary source. **[M]** a secondary source or a search summary. **[C]** computed today from our own files. **[L]** my inference or a starting number to tune by eye.

## 0. The short version

Our scenes have strong ideas. What keeps them from reading as headline content is the picture pipeline, not the design. I measured 22 receipt frames (`state/arsenal/receipts/vj2-20261023-073216/set-*.png`) [C]:
- **No pixel anywhere is true black.** The darkest 1% sits at code 10 to 25 out of 255.
- **No pixel reaches white-hot.** Zero pixels are above 247, and the brightest 0.1% tops out at 235.
- **Many scenes use three or four colour families at once** (aurora curtains, laser cathedral, LED wall, liquid chrome, note rain). Ed Warren works with two.

Three causes, all visible in the code:
- **Every preset clips per channel.** Each one ends with `col = pow(col, 1/2.2); outColor = clamp(col, 0, 1)` (for example `vj-laser-cathedral.frag:201-203`). Light above 1.0 is cut off before the bloom or any tone curve sees it, so hot cores cannot exist, and saturated colours skew in hue on the way up.
- **The "near-black" floors are authored in linear light.** The laser cathedral's nave is `vec3(0.0012, 0.0015, 0.003)`, and the 1/2.2 encode lifts that to codes 12 to 18. On an LED wall dimmed to 1,000 nits, that is roughly 2 to 4 nits of grey glow across the whole wall in a dark hall [C].
- **Trails fade per frame, not per second** (`prev * keep - 1.5/255` in all 11 VJ presets that have trails). There is no `u_dt` uniform. On the host's 240 Hz monitor, every trail is about 4 times shorter than it was tuned to be.

The studios behind big shows (Notch, Unreal through disguise, TouchDesigner) share four habits:
- they render in floating-point linear light and apply one display curve, once;
- they grade with lookup tables;
- their glow takes a threshold and is built at several scales;
- every output is locked to a common clock.

Top five changes, in order:
1. Scenes output HDR linear light, with one shared display curve and a true black floor.
2. A multi-scale bloom fed by that HDR light.
3. A static blue-noise mask for dither and jitter, plus a minimum line width.
4. A colour grade per section, stored as a 3D lookup table.
5. GPU timer queries and a governor that adjusts resolution both ways.

On an RX 6600 at 1080p60, the arithmetic leaves room for all of it. Allow about 5 ms for the scene, about 1.5 ms for all post-processing, and keep at least 4 ms of headroom.

---

## 1. Our frames against the headline bar (measured today) [C]

| set | darkest 1% (code) | brightest 0.1% (code) | lit share, code > 51 | colour families ≥ 10% |
|---|---|---|---|---|
| laser cathedral | 13.7 | 103 | 5.9% | 4 |
| chord constellations | 14.8 | 72 | 0.4% | 3 |
| geometry hall | 20.9 | 187 | 12.4% | 1 |
| hyperspace | 21.9 | 218 | 28.1% | 3 |
| synthwave grid | 16.5 | 200 | 48.4% | 2 |
| aurora curtains | 10.9 | 167 | 31.7% | 4 |
| liquid chrome | 15.3 | 229 | 7.0% | 4 |
| fractal bloom | 5.6 | 136 | 43.5% | 2 |

- Share of pixels below code 4 is **0.0% in every set**.
- Share above code 247 is **0.00% in every set**.

Caveats: these are SwiftShader single frames at 960×540, under the demo, with the default look pass on. They show the pipeline's range, not the art.

The house's own taste rules already say this. shader-craft's ceiling: "a black background stays black where nothing lights it", and 46% of the screen lit "was wrong". The black-space and two-colour lessons in `vj-festival-lessons-2026-10-24.md` say the same.

**What headline content looks like on these measures [L, to calibrate against real show frames if Daniel approves fetching a few]:**
- darkest 1% at code 0 to 2;
- small white-hot cores (about 0.1 to 2% of pixels above 250 on a drop);
- lit share of about 5 to 20% in breaks and 20 to 50% at drop peaks;
- at most two colour families plus white.

---

## 2. How the studios behind headline shows actually work

- **Q-dance, Qlimax 2024 (TWOFIFTYK).**
  - TouchDesigner kept visuals, lights, lasers and moving stage parts in sync.
  - Nearly an hour of timecoded visuals covered 17 shows, and no content was reused.
  - VJ work was split: one operator ran the timecode, one played live. [H] https://twofiftyk.com/en/project/qlimax
- **Qlimax stage design.**
  - Two layers of LED, with a translucent header wall in front, built "big looks" in combination with light. [H] https://www.backbone-international.com/talks/tpi-qlimax/
  - The 2023 lighting told a story through the contrast of light and darkness. [H] https://www.syncronorm.com/newsitem/qlimax-2023-interview
- **Defqon.1.** Every stage show is timecoded and programmed in advance in Depence (Happy Technology). [H] https://www.syncronorm.com/newsitem/defqon1-depence
- **Phish at Sphere (Moment Factory).**
  - Canvas of 16K × 16K.
  - Unreal Engine ran through disguise RenderStream on 31 rxII render nodes, plus 23 gx3 servers for Notch and video.
  - The show director busked content live from a grandMA3; every clip or real-time scene could be called up at any moment. [H] https://plsn.com/articles/inside-the-design/phish-live-at-sphere/
  - Pre-rendering a 16K canvas was impractical, which is why real-time was chosen. [M; Epic's own page returned 403] https://www.unrealengine.com/spotlights/moment-factory-redefines-live-concerts-with-real-time-visuals-for-phish-at-sphere
- **Notch's post-processing vocabulary** (the de facto real-time show toolkit):
  - Tone Map, with Reinhard, Filmic and camera-exposure models;
  - Glow, Glow 2, Physical Glow and FFT Glow, with luminance thresholds;
  - Film Grading and Apply Colour LUT;
  - Vector Blur for motion blur, and Tilt Shift;
  - Dither, FXAA, Frame Feedback and Feedback Blur. [H list] https://manual.notch.one/2026.1/en/docs/reference/nodes/post-fx/ ; [M tone-map detail] https://manual.notch.one/1.0/en/docs/reference/nodes/post-fx/colour/tone-map/
- **Unreal Engine.**
  - Its filmic tonemapper matches the ACES standard, with Slope, Toe, Shoulder, Black Clip and White Clip controls. [H] https://dev.epicgames.com/documentation/en-us/unreal-engine/color-grading-and-the-filmic-tonemapper-in-unreal-engine
  - Grading uses a 16³ 3D lookup table, blended through post-process volumes. [M] https://dev.epicgames.com/documentation/unreal-engine/using-lookup-tables-for-color-grading-in-unreal-engine
- **TouchDesigner.** Artists render into 16-bit float textures, which hold values outside 0 to 1. [M] https://docs.derivative.ca/Pixel_Formats
- **disguise.**
  - Outputs are framelocked and genlocked.
  - A server below its target refresh rate is, by definition, dropping frames, and the operator interface shows this per server. [M] https://help.disguise.one/designer/configuration/genlock-configuration
- **Excision.** Each scene is built around a camera move, such as an elevator dropping. [H via earlier research] https://resolume.com/blog/14554

**What this says for us:** the same pipeline everywhere, in this order:
1. float linear light;
2. exposure;
3. one display curve;
4. a lookup-table grade;
5. glow with a threshold;
6. vector motion blur;
7. antialiasing;
8. dither;
9. a locked output cadence.

Content is hybrid: authored hero moments plus live layers. A single fragment shader per scene can follow this whole order.

---

## 3. LED-wall realities that change the rules

1. **True black is free, and it is the most powerful colour.** LEDs emit light, so code 0 is about 0 nits. Our floors of code 12 to 18 become a lit grey slab on a dimmed wall [C, assuming the processor applies gamma 2.2]. Fix the floor first.
2. **Night walls run dimmed, and dimmed walls lose bit depth at the bottom.**
   - Outdoor panels rated 5,000 nits or more are typically run at a few hundred to about 2,000 nits at night. [M] https://www.ticketfairy.com/blog/led-power-and-thermal-planning-for-festival-screens-calculating-nits-pitch-and-sightlines-for-day-and-night
   - At reduced brightness, the linear PWM drivers lose effective bit depth. The result is banding, colour shifts and speckle in dark areas. Brompton sells Extended Bit Depth (up to 3.3 extra bits) and Dark Magic (26-bit processing) specifically to fight it. [H] https://www.bromptontech.com/when-brighter-is-not-better/ , https://www.bromptontech.com/features/dark-magic/
   - **Rule [L]:** never rely on large, slow, near-black gradients. Use black, plus lit structure. Dither the output with a static mask.
3. **Thin lines and fine patterns shimmer or moiré on the LED pixel grid,** and on the livestream cameras that film it. Thin strokes and high-contrast fine patterns are the classic problem. [M] https://www.doitvision.com/moire-effect-on-led-screens/
   - This adds to the stripe-pattern rule in the safety standard (BT.1702, already in the lessons doc).
   - **Rule [L]:** lines at least 2 to 3 px at 1080p, with analytic antialiasing; no full-frame fine stripes. Fractal bloom, at 43% lit with fine filigree, is the set most at risk.
4. **Bloom raises the whole wall's black.** A wide glow over a building-sized emitter turns black into milk. Keep the wide lobe weak.
   - Our look pass already caps the glow's mean contribution at 0.025 (`vj-show.js:113`). That cap is good safety engineering; keep it.
   - **Add a floor test [L]:** bloom should lift the darkest 5% of pixels by no more than about 1 code value.
5. **Frame cadence is visible at wall scale.** Pros genlock everything. In a browser that means a steady, even cadence at the output display's rate. Judder across a wall reads as broken.
6. **Saturation is strong on narrow-band LEDs.** The saturated-red rule (R/(R+G+B) ≥ 0.8 counts as a flash at any brightness) interacts with the tone curve; see section 4.1.

---

## 4. Techniques, translated to one fragment shader per scene in WebGL2

### 4.1 HDR linear light and one display curve (which one reads best on LEDs)

**What.**
- A new header flag `"output":"hdr"`: the scene writes finite linear light to its RGBA16F target, with no pow and no clamp. Run it through the house's `simSanitize`.
- Trails accumulate in linear light. The composite adds accents in linear light and drops its per-channel shoulder (`vj.js:284`).
- The display stage then runs, once: exposure, curve, grade, sRGB encode, dither.
- Legacy presets (no flag) keep today's path, so Play compatibility is untouched.
- RGBA16F, RG16F, R16F, the 32-bit variants and R11F_G11F_B10F are all renderable under `EXT_color_buffer_float`, which the page already requests (`vj.js:514`). [H] https://registry.khronos.org/webgl/extensions/EXT_color_buffer_float/

**Which curve.** Nobody publishes a tone-curve comparison made on festival LED walls, so this is reasoned from curve properties plus my own computation.

I pushed five stage colours through each curve at 1× to 16× exposure (formulas from `arsenal/web/glsl/colour/tone.glsl`) [C]. Values are hue shift in degrees (OKLab) at 4× / 8×.

| curve | laser blue | orange | hardstyle red | red stays "saturated" (R/RGB ≥ 0.8) up to |
|---|---|---|---|---|
| hard clip (today) | −59 / −58 (blue turns cyan) | +40 / +40 (orange turns yellow) | +8 / +25 | 2× |
| tanh per channel | −47 / −57 | +37 / +39 | +7 / +21 | 2× |
| ACES fit | −38 / −43 | +33 / +35 | +10 / +22 | ~2.5× |
| PBR Neutral (drift 0.15) | +7 / +10 | −8 / −11 | −7 / −9 | about 1.5× |
| Neutral plus "heat" (drift 0.6) | +11 / +12 | −12 / −14 | −10 / −10 | about 1.2× |

**Reading it:**
- Per-channel curves, including today's clip, push saturated colours toward the "notorious six". That breaks a two-colour palette exactly when a hit is hottest.
- Khronos PBR Neutral keeps hue within about ±13° and whitens along the colour's own line.
- It is the identity below 0.76, so existing scenes barely change. Its quadratic toe crushes lifted grey floors while leaving saturated colours alone. Example [C]: the laser cathedral's floor maps to about (0.00001, 0.0003, 0.0018).
- A path to white also takes hot red cores out of the "saturated red" class sooner, which helps the flash gate.

Sources:
- PBR Neutral: [H] https://www.khronos.org/news/press/khronos-pbr-neutral-tone-mapper-released-for-true-to-life-color-rendering-of-3d-products
- AgX replaced Filmic as Blender's default for exactly this saturated-highlight behaviour. [H] https://developer.blender.org/docs/release_notes/4.0/color_management/
- AgX has a long shoulder: in the house's own colour report, 1.0 maps to 0.59 and it looks greyer until a look is added (`research/reviewed/shader-school-2026-10-13/color-post.md` §5.6, §5.9).

**Recommendation [L]:**
- **One house display curve for all VJ scenes:** PBR Neutral with a "heat" control (its drift parameter, 0.15 to 0.8), driven by section. Low heat in breaks keeps colour exact; high heat on drops gives white-hot laser cores. That is one big knob, in the spirit of Pagano.
- Expose each scene to a mid-grey anchor so that switching curves stays fair.
- Run a single A/B with AgX plus a punchy look on the raymarched scenes (geometry hall, liquid chrome, reactor) on the real output TV or wall, and let Daniel choose by eye.
- Avoid the ACES fit (hue skew, magnified by a big wall) and Reinhard (grey highlights). The 46 corpus shaders that use ACES show it is the Shadertoy default, not the studio default.
- **House work:** add a `drift` argument to `tmPbrNeutral` and add `tmAgX` to `colour/tone.glsl` (written fresh from the Blender and Filament constants); route everything through `post/display-out.glsl`.

**Cost:** under 0.1 ms.

### 4.2 Bloom done right

**Today** (`vj-fx.js:99-131, 251-257`):
- two levels only, at 1/4 and 1/16 resolution;
- a threshold on display values that were already clipped;
- separable 9-tap Gaussians.

So a thin laser cannot get the tight, hot halo that makes it read as light: the finest level is already 4 px wide.

**What to build.**
- **Input:** the HDR composite, before the display curve.
- **Prefilter at 1/2 resolution:**
  - a soft-knee threshold on the maximum channel (threshold about 1.0 scene-linear, knee about 0.5) [L];
  - a Karis average (weight 1/(1+luma)) on the first downsample only, so sparkly stars and particles do not flicker in the glow.
- **Pyramid:** six levels from 1/2 down to 1/64.
  - Downsample: dual-filter 5-tap (Bjørge 2015), or the COD:AW 13-tap.
  - Upsample: an 8-tap or 3×3 tent, accumulating up the chain.
- **Two lobes with separate weights:**
  - tight (levels 1-2), the hot-core halo, on in every section;
  - wide (levels 4-6), the haze glow, weak and added mainly on drops.
- **Keep the existing mean cap.** Store levels as RGBA16F or R11F_G11F_B10F.
- **In the scenes themselves**, keep the analytic glow at the source (k/(k+d²), tanh(k/d)). It is the correct point-spread tail and costs nothing extra.
  - Corpus, learn-only: mrange's Neonwave sunrise `7dyyRy`; sonicether's Gargantua HDR bloom `lstSRS` (an atlas pyramid).

**Sources:**
- Bjørge, "Bandwidth-Efficient Rendering", SIGGRAPH 2015: dual filter at 1080p took 2.8 ms on a Mali-T760, against 41.9 ms for a Gaussian. [H via the house colour report §6.4]
- Jimenez, "Next Generation Post Processing in Call of Duty: Advanced Warfare", SIGGRAPH 2014. [H via §6.5] http://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare
- Spencer et al. 1995: glare reads as "brighter than white". [H via §6.1]

**Cost on an RX 6600:** about 0.2 to 0.4 ms [L; scaled from Bjørge's mobile number, measure it]. Bandwidth about 27 MB per frame [C].

### 4.3 Temporal antialiasing and accumulation in the feedback buffer

1. **Make decay rate-independent first.**
   - Pass `u_dt`, and compute `keep = pow(keepPerSecond, u_dt)`. The house's `clkKeep` and `fbDecay` (`glsl/sim/feedback.glsl`) already exist.
   - On RGBA16F linear light, the 1.5/255 floor step is no longer needed; a tiny absolute floor is enough.
   - Today, laser cathedral's keep of 0.685 per frame has a half-life of 30 ms at 60 Hz and 7.6 ms at 240 Hz [C].
2. **Do analytic antialiasing before any temporal method.**
   - fwidth-based coverage, with a minimum stroke of 1.5 to 2 px (house `draw2/aa.glsl`; shader-craft floor 6).
   - Cone-traced silhouettes for raymarched shapes.
   - This alone removes most LED shimmer, at no cost.
3. **Antialiasing over time (TAA), for the raymarched scenes and specular sparkle.**
   - Jitter the pixel centre per frame through `u_jitter`, using an 8-phase Halton(2,3) sequence.
   - Run a resolve pass with its own history pair.
   - Clamp the history to the 3×3 neighbourhood's min and max in YCoCg, and blend about 10 to 15% of the new frame into it.
   - Corpus, learn-only: Enscape Cube `4dSBDt` does exactly this, with YCoCg clamping and a 5% new-frame weight.
   - **Do not fold TAA into the trail buffer.** Trails use max() over time, which dilates edges rather than averaging them.
   - **Beat-aware reset [L]:** on an accent, glitch, cut or flash frame, set the blend weight to 1 so the hit lands crisp and is not smeared by history. With a 10% weight at 60 fps, history responds over about 160 ms, which is long next to a 400 ms beat.
   - Sources: Karis, "High Quality Temporal Supersampling" (SIGGRAPH 2014 Advances course) [M]; Yang et al., "A Survey of Temporal Antialiasing Techniques" (2020) http://behindthepixels.io/assets/files/TemporalAA.pdf [M]; Playdead's INSIDE TAA (MIT, GDC 2016) https://github.com/playdeadgames/temporal [H].
   - **Cost:** about 0.3 to 0.5 ms per scene, plus 33 to 50 MB per frame [L/C].
4. **Accumulate expensive stochastic effects.** Haze, soft shadows, glossy chrome and defocus each take one jittered sample per pixel per frame, blended into history (Hillaire: about 5% new per frame) [M]. Reproject the history through the camera, which is analytic in our rig: `prevUV = camPrev⁻¹(cam(uv))`.

### 4.4 Volumetrics at half resolution, then upsampled

- **Mechanism.**
  - A header field `"passes":[{"id":"vol","scale":0.5}]` runs the same shader with `u_pass = 1` into a half-resolution RGBA16F target.
  - The main pass reads it as `u_vol` and draws the sharp parts at full resolution: beam cores, edges, stars.
  - This keeps one file per scene.
- **Shader-craft ceiling rule:** "Undersample soft low-frequency fields, never the subject."
- **Upsampling.**
  - Bilinear is enough for haze.
  - Where haze meets sharp occluders, use a joint bilateral upsample guided by a full-resolution luminance or occluder mask (Kopf et al., "Joint Bilateral Upsampling", SIGGRAPH 2007).
- **Combine with 4.3 point 4:** march-start jitter plus accumulation.
- **Precedents:**
  - Guerrilla rendered Horizon Zero Dawn's clouds at reduced resolution, refreshed a fraction of the pixels each frame and reprojected the rest.
  - A follow-up paper measured half-resolution, 8 steps, jitter and TAA at **7.5 ms, against 297.7 ms** for full resolution at 128 steps on its hardware. [H] https://arxiv.org/html/1609.05344v1
  - Hillaire 2015 (Frostbite): Halton jitter along the ray, the same offset for every step of a ray, about 5% new per frame. [M] https://advances.realtimerendering.com/s2015/
- **House modules:** `volume/march.glsl` (marchStepPoly, volLightOneTap).
- **First user:** laser cathedral's haze, where beams in smoke are the look.
- **Cost:** 1 ms at half resolution buys about 4 times the per-pixel work of 1 ms at full resolution.

### 4.5 Blue-noise dithering and jitter

- **Today:**
  - The composite's dither is static (`vj.js:293`), but it is applied before more maths in a 16F target, where it does nothing useful (house dither rule: dither only right before the write).
  - The look pass's grain and dither change every frame (`vj-fx.js:180-181`, seed `:320`). That is the crawling grain Daniel had removed (shader-craft floor 8).
- **Fix.**
  - One static blue-noise mask, generated in-house with void-and-cluster (Ulichney 1993; 64² or 128² RGBA in numpy, house-written under Apache-2.0). That avoids any licence question.
  - Christoph Peters' CC0 textures are an alternative, but fetching them needs Daniel's OK.
  - **Final dither:** the static mask, triangular-remapped, 1 code value, the last line before the canvas write (house `post/dither.glsl`).
  - **March jitter:** static when nothing accumulates; animated by a golden-ratio offset per frame only under accumulation or TAA, which averages it away.
  - **Grain:** off by default on the wall.
- **Sources:** NVIDIA, spatiotemporal blue noise (Wolfe et al. 2022). [M] https://developer.nvidia.com/blog/rendering-in-real-time-with-spatiotemporal-blue-noise-textures-part-1 ; Peters 2016 (CC0). [M]
- **Cost:** one texture fetch.

### 4.6 A colour grade per section (lookup table)

- **What.** A 32³ 3D texture (WebGL2 supports 3D textures and can render into their layers), baked whenever the section's look changes. Crossfade two tables during transitions. Apply after the display curve, in encoded space.
- **What the grade contains [L]:**
  - lift, gamma and gain, and saturation (ASC CDL; house `colour/grade.glsl`);
  - a split tone;
  - one hue-family restriction in OKLab, which enforces the two-colour rule.
- **Colour script [L, from the lessons doc]:**
  - break: desaturated or one tint;
  - build: saturation and contrast rising, temperature moving toward the drop palette;
  - drop: the full palette, with heat high;
  - anti-climax: red and black monochrome (Defqon.1's RED stage code).
- **Cost:** under 0.1 ms; 128 KB at 8 bits per channel.

### 4.7 Depth of field and motion blur, cheaply

- **Analytic defocus for signed-distance scenes [L].**
  - Defocus is a bigger, dimmer kernel: circle of confusion = f(depth); stroke and particle width = max(px, CoC); intensity × (px/width)² for points, or px/width for lines.
  - It costs nothing and is energy-correct.
  - A focus pull is a camera gesture: rack focus on the drop.
- **Raymarched scenes:** Gustafsson's single-pass bokeh at half resolution. [H] https://blog.voxagon.se/2018/05/04/bokeh-depth-of-field-in-single-pass.html
- **Camera motion blur.**
  - In the composite, take per-pixel velocity from the analytic camera (zoom punch is radial, shake is directional, orbit is tangential), with 6 to 12 taps along it, blue-noise offset.
  - Skip entirely under 0.5 px of motion, so the path at rest is byte-identical (shader-craft floor 7). This is Notch's Vector Blur idea.
  - Reference: McGuire et al., "A Reconstruction Filter for Plausible Motion Blur" (I3D 2012) [M].
- **Object motion (beam sweeps):** analytic in the scene, either a closed-form sweep or 4 to 8 time sub-samples for the fast element only ("when motion is analytic the past is a function call", shader-craft ceiling).

### 4.8 Camera language

Semantics from StudioBinder [M]: a push-in builds intimacy and tension, a crane up feels triumphant, an arc reveals dimension, a pull-out reveals context.
https://www.studiobinder.com/camera-shots/camera-movements/push-in-shot/ , https://www.studiobinder.com/camera-shots/camera-movements/crane-shot/

Mapping for the rig [L]:
- **Shared uniforms:** `u_cam` (zoom, roll, offset, crane tilt) and `u_camPrev`, used for reprojection and blur.
- **Break:** a slow push-in, about 1.00 to 1.06 zoom over 16 bars with ease-in-out; no shake; soft far layer.
- **Build:** an accelerating push-in, crane rising toward the vanishing point, shake trauma building with the snare roll, focus racking onto the subject.
- **Drop downbeat:**
  - a cut or 1-frame whip into a wide pull-out or crane-up reveal, with spring overshoot (about 6 to 8 Hz, damping 0.3 to 0.5);
  - 50 to 100 ms of hit-stop (as in the lessons doc);
  - then a slow orbit, about 1 turn per 16 to 32 bars.
  - Kick: a vertical shove (trauma squared). Reverse bass: a small zoom breath on the off-beat.
- **Anti-climax:** a locked-off camera with hard cuts. Large-luminance cuts go through the flash gate.
- **Caution:** keep continuous roll slow on a wall that fills the audience's view [L].

### 4.9 Composition on a wide LED wall [L unless noted]

- Hero form inside the centre 60% of the width. The outer thirds carry mirrored echoes; the earlier research cites ILDA's mirrored side projectors.
- Do not put the hero at the bottom centre, where the DJ booth hides it. Put the vanishing point at about 40 to 45% of the height.
- Make key forms at least a tenth of the wall's height. The back of the crowd reads silhouettes and value, not texture.
- Depth: near, mid and far layers with parallax; the far layer lower in contrast and tinted toward the haze colour. Forced perspective to a central sweet spot. [M] https://www.avixa.org/explore/articles/the-illusion-of-3d-on-led-walls-how-content-and-perspective-create-immersive-visuals
- Black space and two colours, keeping lit share inside the section's band (section 1).

---

## 5. Frame pacing and GPU budget

**RX 6600 arithmetic [C]:**
- 1,792 lanes × 2 × 2.491 GHz = **8.93 TFLOPS**; 224 GB/s; 32 MB Infinity Cache. [M] https://www.techspot.com/specs/gpu/236446-amd-radeon-rx-6600.html
- 1080p60 is 124.4 M pixels per second, so about **71,800 ideal operations per pixel per frame** for the whole frame. Assume 30% efficiency for a realistic figure.
- The host's RX 9070 XT (single-issue, from the house GPU report) is about 2.7 times faster in arithmetic and 2.9 times in bandwidth. **Rule of thumb: a pass measured at X ms on the host is about 2.7 X ms on an RX 6600.**
- **Bandwidth is not the limit.** One 1080p RGBA16F target is 16.6 MB. Our whole frame moves about 175 MB (about 290 MB with TAA and a transition running), which is 10 to 17 GB/s at 60 fps, or 5 to 8% of the card. Arithmetic in the scene shaders is the limit.

**Per-pass budget, RX 6600 at 1080p60 (16.7 ms frame)** [L allocations; operations per pixel at 30% efficiency are C]:

| pass | GPU ms | what it buys |
|---|---|---|
| scene, full resolution | 5.0 | about 6,500 operations per pixel (for example 64 march steps × 80 operations, plus shading) |
| scene volume layer, half resolution | 1.0 | about 5,200 operations per half-res pixel; about 10 to 20 effective samples once accumulated |
| cued scene during a transition, at 0.7 scale | 3.0 | about 7,900 operations per pixel; only for the two beats of a switch |
| overlay accents | 0.5 | |
| composite plus camera blur plus TAA resolve | 0.8 | |
| bloom pyramid | 0.4 | |
| display curve, lookup table, dither, output | 0.3 | |
| safety-gate reduction plus asynchronous read-back | 0.1 | |
| **typical / during a transition** | **about 8 / about 11** | leaves at least 5 ms for Chrome's compositor and spikes |

**Measuring in the page.**
- **GPU timer queries.** Feature-test `EXT_disjoint_timer_query_webgl2`. It is present on about 87% of Windows and 82% of Chrome devices surveyed, and essentially absent in Firefox. [H] https://web3dsurvey.com/webgl2/extensions/EXT_disjoint_timer_query_webgl2
  - Keep a ring of queries, one per pass. Only one time-elapsed query can be open at once, so they cannot nest.
  - Read results 2 to 3 frames later, and discard any result taken while the disjoint flag is set:
    ```js
    gl.beginQuery(ext.TIME_ELAPSED_EXT, q); /* draw */ gl.endQuery(ext.TIME_ELAPSED_EXT);
    // frames later:
    if (gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE) && !gl.getParameter(ext.GPU_DISJOINT_EXT))
      ms = gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6;
    ```
- **Frame cadence.** rAF-gap p50, p95, p99, worst gap and missed-frame % (gap above 1.5 times the refresh interval). The HUD shows only p95 today (`vj.js:1631`).
- **Outside the browser:** PresentMon (open source) records true present and display intervals on Windows. [M] https://github.com/GameTechDev/PresentMon . Installing it is Daniel's call.
- **On the 240 Hz host,** use the house's "draw N times" method to beat vsync quantisation (house GPU report §10.3).

**Pacing rules [L, built on sources]:**
1. **Render at the output device's native resolution, not the operator monitor's.** Today the backing store is CSS size × DPR (capped at 2) × scale (`vj.js:623-625`). At 150% Windows scaling on the 4K monitor, full screen is 3840×2160, four times 1080p.
2. **Lock to the output display's refresh, or cap evenly.** Render 1 of every N rAF ticks, never with setTimeout. Even cadence beats a high average. All motion runs on `u_time` and `u_dt`.
3. **Use a governor driven by GPU time, not by rAF gaps.**
   - Today's watchdog only steps down, at 2× the budget, and never recovers (`vj.js:1564-1569`).
   - Step scale in eighths between 0.625 and 1.0, with hysteresis (down when p90 > budget for 1 s; up when under 70% for 3 s), and always show it on the HUD (Visual Quality Baseline: never lower resolution silently).
   - Upscale with bilinear, or an edge-aware spatial upscaler such as FSR 1 (MIT) [M].
4. **No synchronous stalls in the live loop.** No `readPixels`, `getError` or `checkFramebufferStatus` per frame. [H] https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices
   - The output probe does a full-frame synchronous `readPixels` (`vj.js:1373`). That is fine for receipts, but the "grown-up gate" must reduce on the GPU to about 120×68 and read back through a pixel-pack buffer and a fence, one frame late.
5. **Warm every program with one draw** into a 1×1 target at load, so the driver's first-use compile does not hitch on a set switch (house GPU report §8.2) [L].
6. **Budget the transition, not the steady state.** Both scenes render during a switch (`vj.js:1517-1519`). Render the cued scene at reduced scale.
7. **Multi-monitor:** confirm the rAF rate on the output display itself. Mixed-refresh setups can pace differently [L; measure].

---

## 6. Corpus and house library

**Corpus, learn-only.** The licence line holds even for the MIT and CC0 entries, because the shingle guard checks the whole corpus.

| id | what it teaches |
|---|---|
| `4dSBDt` | TAA with YCoCg clamping (Enscape Cube) |
| `WsSBzh` | iq's cheap reprojection average, no clipping (Selfie Girl) |
| `7tjSDh` | blue noise plus reprojection in a laser tracer |
| `lstSRS` | HDR bloom pyramid in an atlas |
| `7dyyRy` | analytic tanh(k/d) glows |
| `XtGGRt`, `ffG3Rc` | aurora sheet spacing |
| `4dlyWX` | lens flare |
| `DtjSWh` | bokeh plus temporal accumulation |

Counts: 46 corpus shaders use ACES; 1 uses AgX; none use Kawase.

**House modules to reuse:**
- `colour/tone.glsl` (add drift/heat and AgX)
- `post/display-out.glsl` (the one seam)
- `post/dither.glsl`
- `colour/grade.glsl`
- `colour/oklab.glsl`
- `sim/feedback.glsl`
- `volume/march.glsl`
- `light/glow.glsl`
- `draw2/aa.glsl`
- `hash/pcg.glsl`

**To build, house-written from the papers:** `post-bloom` (spec in the colour report §14.9), `post-taa`, the blue-noise mask, the lookup-table bake, the camera rig. Every new shader must pass `arsenal/shaders/licence_line.py`.

---

## 7. Ranked build list, with acceptance checks

Sequence these after the impact pass lands: items 1 to 3 touch the same files it is editing now.

1. **HDR contract, the Neutral-plus-heat display curve, black floors, and `u_dt` trails.** Size M.
   - Done when the receipt scorecard shows: darkest 1% ≤ code 2; ≥ 0.1% of pixels above 250 on drop frames; trail half-life equal at 60 and 240 Hz.
2. **Bloom pyramid from HDR,** with tight and wide lobes and the mean cap kept. Size S-M.
   - Done when the bloom lifts the darkest 5% by ≤ 1 code and the timer shows ≤ 0.4 ms (scaled to an RX 6600).
3. **Static blue-noise mask, removal of per-frame grain and dither, a minimum line width in every preset.** Size S.
   - Done when a still scene shows no frame-to-frame change and no line thinner than 1.5 px.
4. **Section lookup-table grade and colour script.** Size M.
   - Done when there are at most 2 colour families at 10% weight per section.
5. **GPU timer HUD, two-way governor, fixed output resolution, even cadence cap, asynchronous gate read-back.** Size M.
   - Done when frame-time p95 ≤ 16.7 ms and missed frames ≤ 1% through a transition on the output display.
6. **Camera rig, section camera language, and analytic camera motion blur.** Size M.
7. **Half-resolution volume pass with jittered accumulation and beat-aware history reset;** first user: laser cathedral haze. Size L.
8. **TAA for the raymarched scenes.** Size M-L.
9. **Analytic defocus and focus pull.** Size S-M.

**Headline scorecard to add to the VJ receipts [L]:**
- darkest 1% and brightest 0.1%;
- hot share and lit share per section;
- colour-family count;
- line shimmer (frame-to-frame luminance spread on thin edges with the camera still);
- GPU ms per pass;
- p95/p99 frame gap and missed-frame %;
- flash-gate statistics.

---

## 8. Gaps, stated plainly

- **No frame-level comparison against real show footage.** That would mean downloading frames from an official Qlimax or Defqon.1 aftermovie, which needs Daniel's OK. My targets in section 1 are a calibration starting point.
- **No GPU timings measured.** This lane is SwiftShader-only. The RX 6600 numbers are arithmetic plus estimates tagged [L]. The bloom cost is extrapolated from mobile numbers.
- **No tone-curve test on an actual LED wall or TV.** AgX was not computed in my table, because I did not verify its constants today. The table is single-colour ramps, not perceptual testing.
- **Thin primary sources:**
  - Q-dance content studios beyond TWOFIFTYK, and hardstyle-specific visual craft, still lack a first-hand source (as in the earlier research).
  - Epic's Phish page returned 403; I used PLSN instead.
  - The Notch tone-map detail, the festival LED brightness numbers and the timer-query re-enable history are [M].
- **Code references** are to commit ce0f492b. The impact pass is editing these files now.

## Sources (beyond those cited inline)

- Bjørge, "Bandwidth-Efficient Rendering" (SIGGRAPH 2015); Jimenez, COD:AW post-processing (SIGGRAPH 2014); Spencer et al., "Physically-Based Glare Effects" (SIGGRAPH 1995); Lottes, HDR colour pipelines (GDC 2016). All via the house report `research/reviewed/shader-school-2026-10-13/color-post.md`.
- Karis, "High Quality Temporal Supersampling" (SIGGRAPH 2014); Kopf et al., "Joint Bilateral Upsampling" (SIGGRAPH 2007); McGuire et al., I3D 2012; Ulichney, void-and-cluster (1993). All cited from standard bibliography [M].
- House files used as reference:
  - `research/reviewed/shader-school-2026-10-13/gpu-perf-glsl.md` (§3.8, §8.2, §10)
  - `.claude/skills/shader-craft/SKILL.md` (floors 6-8, ceiling)
  - `arsenal/VISUAL-QUALITY-BASELINE.md`
  - `research/reviewed/keylab-liberation-2026-10-22/vj-festival-lessons-2026-10-24.md`

Scratch computation (not in the repo): `<session scratchpad>\hc\curves.py`
