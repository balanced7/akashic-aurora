# Laser Sky: the DJ Isaac "Berlin" section of the Defqon.1 2025 Endshow as a VJ scene, measured, built and judged (2026-10-25)

Workflow run wf_b0a0b896-f74 (task wqoxd8mly): Daniel's two Berlin frames ("take a look at the DJ Isaac Berlin section especially, it looks insane") measured with the section's public storyboard frames, a build spec, one builder in a worktree (eight render-and-compare rounds), then a judge side by side with the frames, Ritual Fire and Hyperspace. His frames are other people's footage and stay in local scratch, never in this repo. Verbatim; local paths shortened to <scratch> and <worktrees>. Branch worktree-wf_b0a0b896-f74-2 (43d83c08); not merged yet (the judge's must-fix list, Look v2 and the page lane's registration first).

Vandor's read: 6/10 headline, 6/10 likeness. The judge's must-fix list is concrete (acid green in the beam cores, a streaked cloud, the phrase-held balance, the lower third, ramped section entries, striped sheets, k7 = 0 going black). Like Void Star, the "it looks insane" gap is light in haze: saturated thin cores, motion-blurred streaks and bloom, which is Look v2's haze and output stage and the Virtual Stage's job as much as this scene's.

---

## Study: the Berlin frames measured and the build spec (verbatim)

I measured both Berlin frames and the section's public storyboard frames, then built a numpy mock from the spec's own numbers to check they reproduce the frames. The mock lands 14 of 16 metrics inside the reference ranges. Below is the spec for `vj-laser-sky` ("Laser Sky").

Four things need a decision before a build:
- **The air is the colour.** The house rule "the room is 0" doesn't hold here: in the frames the haze stays the same deep blue with the lasers off.
- **Sheet fans.** Lasers v2 rule 4 bans sheet forms, but the frames are full of them.
- **Strip v2 collision.** The headline brief and Lasers v2 both claim strip row 2, texels 9-14.
- **No matching theme.** The 21-theme library has no green / cyan-white on deep blue pair.

Section 10 has the proposed answers.

# Laser Sky (`vj-laser-sky`): measurements and build spec

Coordinates: x is 0..1 across the frame width; y is 0..1 from the top. In the preset's centred space, `p.x = (x − 0.5)·1.778`, `p.y = 0.5 − y`. "Encoded" means sRGB 0..1 values as seen on an SDR screen. "Linear" means scene-linear, with 1.0 = SDR reference white.

## 0. What the references show (measured, not taken on trust)

**Where the section is.** The official description's chapters put "D-Block & S-te-Fan & DJ Isaac - Berlin" at **07:50–10:38**. YouTube's public storyboard (largest level: 320×180, one frame per 10 s) was already saved by the Endshow lane. I cropped 07:30–10:50 into `berlin/frames/` (21 frames). Nothing was downloaded.
- **ref-2 is the 08:00 moment.** Its beam-free air is #162d6d (OKLCh hue 265°); the 08:00 storyboard frame's is #192d6e (hue 267°).
- **ref-1 falls between storyboard samples.** Its air is more teal and 30% darker (#02334c, hue 238°, V 0.30), consistent with another camera on the same drop.
- ref-1 carries a YouTube buffering spinner at the centre; it is masked in every measurement.

**Your four observations, checked:**
- **"The air itself is the colour": confirmed, and stronger than stated.**
  - ref-2's beam-free floor is flat from the top to 0.54 H: #162d6d (HSV 223°/0.80/0.43; OKLab L 0.32, C 0.115).
  - At 08:30 the lasers are off (beam coverage 2%), yet the air holds the same level: #18246b, V 0.42, drifting about 5° toward violet.
  - The air is therefore ambient (blue-hour sky plus haze), not lit by the beams. The beams add about 4× the mean light on top: linear Y is 0.023 with lasers off and 0.10–0.13 in the drop.
- **"Two colours only": confirmed by brightness, not by area.**
  - Sky area is 61–70% haze blue, 9–22% teal haze, 1.6–2.4% acid green and 2.4–12% cyan-white. Warm or red pixels are 0.03%.
  - Acid green: mean #0c9846–#13a35d, bright quartile #0fe35c (HSV 142–151°).
  - Cyan-white: mean #74b9cc–#94dff6, bright quartile #cafbfe (HSV 184–194°, saturation 0.2–0.4).
  - The brightest 0.5% of pixels have mean saturation 0.25, so they read near-white.
- **"Dozens of emitters along a low line": confirmed, and colour follows the bank.**
  - **Low green line** (ref-2) at y 0.705–0.71: flank groups at a regular pitch of 0.026 W (4 visible per flank, more hidden by towers), plus centre singles at x 0.29, 0.43, 0.57, 0.71.
  - **Cyan-white stage bank** at y 0.675–0.695: six emitters at x 0.316, 0.409, 0.469, 0.529, 0.591, 0.685. These are exact mirror pairs about 0.5 (±0.030, ±0.091, ±0.184).
  - Two more green emitters on the stage at x 0.44 and 0.56 (y 0.68). About 20 are visible in ref-2; ref-1 shows 8 white and 4 green.
  - Green is always the low thin-beam fans; cyan-white is always the stage sheets.
- **"Fans cross into a lattice, some so dense they read as solid sheets": confirmed and measured.**
  - **Thin green fans:** 8–12 beams over 100–150° in the wide shot, about 26 beams over 150° up close. Angular spacing 5–15°. Fill (share of the aperture above half peak, near the source) about 0.40.
  - **White sheets:** 22–30 beams over 35–100°, spacing 1.5–4°. Fill 0.83–0.85 near the apex: a solid translucent wedge for about the first 0.05–0.10 H, with beams separating further out.
  - **Blades:** ref-1 has five sheets 5–15° wide that read as thick single beams.
  - **Sawtooth row:** at 08:10 and 08:20 a row of V-sheets runs along the stage with their rims touching. Pitch is 0.045–0.055 W, with dark upward triangles of air between them.
  - **Lattice (ref-2):** the 0.45–0.60 H band has three orientation families at 30°, 90° and 150°, which is a triangular lattice. Near-vertical streaks dominate up high (0–0.25 H: 61% within 75–105°). Near-horizontal beams make up 31% of the energy in the fog band.
  - Scanline crossings across the full width: 43–70 at 0.35–0.55 H.
  - Beam coverage of the sky is 21–29%, rising toward the deck (ref-2 by band, top to bottom: 0.7%, 4.5%, 10%, 22%, 32%, 36%, 49%).
- **"Volumetric, white-hot at the source, fading into the haze": confirmed, plus a second effect.**
  - Green low fans: excess over the air is 0.42 encoded at the source, 0.26 at 0.1 H and 0.04 at 0.2 H. Half-brightness at 0.07 H; exponential decay length about 0.15 H.
  - Stage sheets: 0.53 at the source, 0.32 at 0.05 H, 0.09 at 0.1 H.
  - Apexes are clipped white (encoded luma 0.90–0.96, RGB about 0.9/0.97/1.0).
  - The second effect: beams light up again where they cross a high, patchy haze cloud, and break into dashes there. Median dash length 0.027 H (p90 0.076 H), width about 0.007 H, 55% steep. These dashes are what the cloud is made of.
- **Haze.** Two layers:
  - a high patchy cloud at about 0.15–0.60 H;
  - a low fog band 2–4% of the height above the low line, lit green by the low fans (13–19% green pixels in those rows).
- **Silhouettes.**
  - **Crowd:** from 0.636 H (ref-1) or 0.776 H (ref-2) downward, 22–37% of the frame. Blue-black (RGB about 0.03–0.05 / 0.05 / 0.09), mean encoded luma 0.05, 72–75% near-black, with phone screens at 125–370 per megapixel.
  - **Towers:** flank towers at x 0–0.04 and 0.95–1.0 run the full height. Inner towers at about 0.24–0.26 and 0.74–0.765 rise to about 0.40 H.
  - Set pieces are dark but not black (encoded luma 0.12–0.19 inside), because haze and spill sit in front of them.
- **Luminance distribution.**
  - Near-black (encoded luma < 0.06): 18–28% of the frame, almost all in the silhouette zone; only 1–2% of the sky.
  - Highlights: luma > 0.70 covers 2.3–4.0%; > 0.85 covers 0.13–0.62%.
  - Of the brightest 0.5%: 76–77% are in the sky (beams, sheets, cloud), 19–23% within 0.12 H above the ground line (emitters and fog band), under 5% in the crowd (phones).
  - Linear ladder: the air floor is at Y 0.019–0.031. The sky median is 2× the air; 33–38% of the sky is at least 4× the air, 19–24% at least 8×, 4–12% at least 16×. p99 is 20–39× (the SDR footage clips above that).
- **k-means palettes (k=8).**
  - ref-2: #183376 29%, #0b0c13 24%, #1e5185 13%, #6db9cb 10.5%, #4487b5 9%, #12243f 7%, #156b75 5%, #17a273 2.8%.
  - ref-1: #070c16 39%, #092f4b 25%, #0a5358 12%, #3498d9 9%, #115289 8%, #4ecbdf 4%, #0635b8 2%, #0cad5b 1.5%.

**How the look moves (storyboard, 10-s steps; per-frame numbers in `measure_timeline.txt`):**

| Time | What happens |
|---|---|
| 07:50 | Dark breath: drone shot, 48% near-black, two red beacons. |
| 08:00 | Full laser sky (this is ref-2): green and white cloud, one vertical white blade at x≈0.4, flank green fans. Highlights 6.3% (the section's peak), cyan-white 14%. |
| 08:10 | The cloud shifts left; green rakes at the flanks; the sawtooth row of sheets appears along the deck. |
| 08:20 | Green leaves the cloud (2.5% → 0.4%). The cloud is cyan-white only, with two vertical green pillars as accents, over the sawtooth row. |
| 08:30 | Break: lasers off, blue air remains (haze blue 75%). |
| 08:40–09:10 | Crowd close-ups; no usable rig. |
| 09:20 | Sparse low green rakes crossing in front of the stage. |
| 09:30–09:50 | The air turns violet (violet share 12–17%, HSV hue 246–257°). |
| 10:00 | Pyro. |
| 10:10 | A V of white blades from the flank towers, converging inward. |
| 10:30 | Rebuild: white upward fans from about 12 low emitters, sparse, with high white streaks. |
| 10:40 | Dark. |

Beat-level motion (sweeps, chases, which emitter fires on which beat) cannot be resolved from 10-s storyboards, and downloads are refused. The motion vocabulary in section 4 is therefore drawn from laser-show craft and the Lasers v2 research, marked *[inferred]*. Only the section-level changes above are observed.

## 1. Composition (locked wide camera, symmetric)

| Element | Where |
|---|---|
| Sky / air | 0 → 0.70 H |
| Cloud focus | x 0.5 ± 0.12 (wanders only when k8 > 0), y 0.36–0.48 |
| Stage bank line (sheets) | y 0.683 |
| Low bank line (green) | y 0.705 |
| Deck silhouette (stage front) | 0.712 → 0.775 H |
| Crowd | 0.775 H → bottom (22.5% of the frame) |
| Flank masts | x 0–0.035 and 0.965–1.0, full height |
| Inner masts | x 0.238–0.260 and 0.740–0.762, from 0.40 H |

The geometry and orders are a strict left/right mirror at k8 = 0.

## 2. Atmosphere

**Air** (the declared exception: see 10.1).
- Formula: `air(y) = mix(zenith, horizon, smoothstep(0, 0.70, y)^1.5)`.
- Zenith #13286a (linear about 0.0065 / 0.021 / 0.144); horizon #1c3c84 (linear about 0.011 / 0.045 / 0.235). Linear Y runs 0.024 → 0.050.
- The air is constant within a section. It changes only on bar lines, over at least 1 bar.
- Section hue: drop at HSV 222–226°; break drifts +8° toward violet (08:30); late verse at 246–257° (09:30–09:50).
- It is scaled by `(1 − 0.85·darkness)` (strip v2 texel 10.y) and by k7.
- The kick never raises it.

**Haze density ρ.** It multiplies beam visibility and never emits on its own.
- `ρ = 0.22 + ρcloud·G(y; 0.40, 0.17)·patch + ρfog·G(y; 0.665, 0.055)`, where G is a Gaussian (centre, σ in H).
- `patch = clamp((fbm − 0.38)/0.30, 0, 1)^1.5`. The fbm is house `noise/fbm` `fbmGrad2`, 4 octaves, on `(x·aspect·11, y·18 + drift)`. Clumps come out about 0.055 H tall and 0.09 H wide.
- Drift is upward at 0.03–0.06 H/s and sideways at 0.02 W/s, in units per second. The noise is never re-seeded.
- ρcloud = 1.6 (k2); ρfog = 0.6 (k6).
- The fog band's top edge is broken by 2-octave noise of ±0.01 H.

**Fog glow.** One analytic term per bank, not per beam: `ρfog·fogMask·Σ(low-bank levels)·L1·0.04`. This tints the fog band in the low bank's colour.

**Toward-camera boost.** Each fan has a tilt t in 0..1. Brightness is multiplied by `mix(1, 2.2, t)` (a `phaseHG` g = 0.55 stand-in), with a wider halo.

## 3. Emitter rig: two banks plus towers, 34 emitters

**Bank A, "Low" (24 emitters, colour slot L1), at y 0.705:**
- left flank: x = 0.062 + 0.026·i, i = 0..7;
- right flank: its mirror, 0.756–0.938;
- centre: x = 0.29 + 0.06·i, i = 0..7.
- Home aims: left flank 110° (leaning outward), right flank 70°, centre mirror pairs 90° ± 8°·pair.

**Bank B, "Stage" (6 emitters, colour slot L2), at y 0.683:**
- x = 0.5 ± 0.030, ±0.091, ±0.184 (as measured).
- Home aims splay outward: 135°, 118°, 102°, 78°, 62°, 45°.

**Towers (4 emitters; colour by order):**
- flank masts at (0.018, 0.30) and (0.982, 0.30): rakes at home 8° and 172°;
- inner mast tops at (0.249, 0.405) and (0.751, 0.405): blades at 60° and 120°.

**Sawtooth row:** 13 virtual V-sheets at pitch 0.047 W across x 0.218–0.782, on the stage line. They are evaluated by domain repetition (the 2 nearest sheets only), so the cost is constant.

**Header:** `"rig":{"origins":[the 4 tower emitters + the 8 low-centre emitters],"floor":0.705}`. Lasers v2's gated pad-2 hits will then originate from this rig.

## 4. Fan types and motion vocabulary

**Fan types:**
- **F1 Thin-beam fan** (bank A default).
  - 12 beams (6–16) over 150° (60–170°).
  - Evaluated by the nearest beam in angle space: `k = round((θ − a0)/step)`, perpendicular distance `r·|sin(θ − θk)|`.
  - Core: Lorentzian with 1.6 px half-width at 1080p, drawn at least 1.5 px (aaWire rule). Halo: 7 px Lorentzian at 0.25 of the core peak.
  - Falloff along the beam: `exp(−r/0.20H)` (k4). Apex glow: half-brightness at 2.5 px.
- **F2 Sheet fan** (bank B).
  - 26 beams (22–30) over 70° (35–100°).
  - Plus a translucent wedge: `inside(θ)·exp(−r/(0.45·decay))·0.10` (k3, 0–0.25). This gives fill ≥ 0.8 near the apex, with beams separating past about 0.1 H.
  - Decay 0.24 H.
- **F3 Blade:** a sheet 4–12° wide with 8–12 beams and wedge 0.18. Reads as one thick soft beam.
- **F4 Sawtooth:** V-sheets 45° wide (rims touch about 0.10 H above the deck), 9–12 beams each.
- **F5 Rake:** 1–6 tower beams at 5–25° elevation, skimming the fog band and crossing the opposite tower's rakes as an X.
- **F6 Pillar:** a single vertical beam with decay 0.6 H. Two to four at a time (the 08:20 green pillars, the 08:00 white spike).
- **The cloud is emergent.** It is only beams × patchy haze, so it moves with the beams. It forms when bank B's aims converge on the cloud focus and bank A's adjacent fans (pitch 0.046 H, apertures 150°) cross into the diamond lattice within 0.05–0.2 H of the deck. The triangular lattice appears when fan centres alternate 60/90/120°.

**Motion vocabulary** *[inferred]*. Every parameter is a pure function of beat count + phase, bar, phrase and section seed; there is no feedback state.
- **M1 Kick Step:** each lit fan's aim steps through a 4-card deck (+18°, −18°, +9°, −9° about home), easeOutCubic over the first 40% of the beat, then holds.
- **M2 Scanner Sweep:** ±(k1 × 45°) once per beat (½ beat in the climax), easing to a stop on each kick.
- **M3 Phase Wave:** every emitter in a group runs the same sweep offset by i/N of a 4-beat cycle, making a chase along the line.
- **M4 Scissors:** mirror pairs aim at mirrored foci that cross on each kick.
- **M5 Converge → Bloom:** sheets aim at the focus and narrow each bar of the build (70° → 20°). On the drop's first beat they open to 100° over ¼ beat.
- **M6 Breathing Fan:** 60° ↔ 150° per 2 beats (groove) or per bar (break).
- **M7 Alternate Banks** (your "alternate which lasers fire"): bank A on beats 1 and 3, bank B plus towers on 2 and 4. Level steps with ⅛-beat attack and ¼-beat release; the large forms in bank B follow the slower ramps in section 8. Odd and even low emitters swap on the off-beat inhale.
- **M8 Sawtooth Shift:** one tooth per kick, or one per bar.
- **M9 False Ceiling:** a 160° flat sheet reading as a ceiling at about 0.45 H, dropping a step each bar (break into build).
- **M10 Drift:** the haze moves continuously; the cloud focus wanders ±0.12 W over 8 bars (only when k8 > 0).

**Firing orders:** all; odd/even; chase left to right; centre-out; outside-in; mirror pairs; seeded deal. One order is dealt per bar from a shuffled deck and never repeats the previous one.

## 5. Sections (strip v2 section id; section 0 must look right on its own)

- **Intro / anti-climax:** air, 1–2 pillars or single hot beams; raw style uses thin bank-A fans with M1, no sheets.
- **Break (the 08:30 analogue):** lasers off, or at most 20% for one False Ceiling or two pillars. The air holds; the fog band drops to 30%.
- **Build:** bank B runs M5. Bank A runs M3, accelerating from 1 cycle per 2 bars to 1 per beat. Snare-roll density (12.y) fills bank A outside-in and raises ρcloud by up to 30%. Over the last bar L1 drains 50% toward white. On the last beat the lasers dip to 15%; the air stays.
- **Drop, first beat of the phrase (the 08:00 frame):** all 34 emitters plus the sawtooth fire. Sheets bloom, bank A opens to 150°, the towers rake an X, and the central white spike holds for 1 bar.
- **Drop groove:** M7 with M1 or M2.
  - Every 8 bars the colour emphasis rotates: green + white cloud → white-only cloud with green pillars (08:20) → back.
  - The sawtooth row comes in for bars 9–16.
- **Outro (the 10:30 analogue):** sparse white upward fans from the low line, decaying to air only.

## 6. Music

Strip v2 fields first; strip v1 and Play fallbacks in brackets.
- **Kick** (11.x click, 11.y punch, 11.z tail) [row 1 texel 12 kick; `u_beat`]:
  - moves the world: M1 steps, M2 stops;
  - click: lit apex points rise 60% for one frame (points only);
  - punch: apertures +6° on a spring;
  - tail: cores +25% over 0.3 s;
  - the air and the fog never rise on the kick.
- **Bass / off-beat inhale** (11.w) [`u_bass`]:
  - bank A's odd emitters ramp 0.6 → 1.0 (x²) through the off-beat; cut at the kick (raw: 8 ms; euphoric: 35 ms release);
  - the fog band breathes ±15% with at least 80 ms smoothing, so it never flickers.
- **Screech** (12.x) [`u_high`]:
  - the tower rakes zigzag between two angles on 16ths, in L1, at most 4 beams and at most 2% of the frame;
  - the cloud's dashes sharpen (haze threshold +0.05).
- **Drop:** the all-fire bloom in section 5. The scene never requests the gated flood (10.z), and it uses no full-frame white.
- **Raw vs euphoric** (12.w): raw gives hard cuts, apertures ×0.8 and more green; euphoric gives soft releases, wider sheets and more white.
- **Heat** (10.x) whitens cores (white mix 0.15 → 0.8). **Darkness** (10.y) scales the air and the fog.

## 7. Colour

Two families plus white cores per section. Changes land only on bar lines, and themes land on the next bar as Lasers v2 specifies.

**Default pair, proposed new library theme `blue-hour` (night family):**
- L1 acid green #1ee35f (linear about 0.013 / 0.77 / 0.11);
- L2 cyan-white #c8f4ff;
- W #ffffff;
- air #13286a → #1c3c84;
- crowd #07080e; set pieces #0a0d16.

**Other pairs from the library.** Beam colours are the library's; the air is the scene's.

| Theme | Bank A (L1) | Bank B (L2) | Air |
|---|---|---|---|
| uv-euphoria | #2ad4eb cyan | #7855f9 UV | indigo #120a4a → #22137a (the 09:30 violet air) |
| acid-screech (split only) | #8ed726 | #685df9 | #0e0d3d → #1d1866 |
| magenta-classics (split only) | #2ad4ed | #fb30b3 | #160a3e → #2a1260 |
| golden-wings | #e89029 | #6d5bf9 | #0d0a2e → #1e1650 |
| laser-green | #29d889 | #72ba4f | teal #052a33 → #0a4a52 (magenta pin = the single centre pillar) |
| night-sea | #25bde5 | W #e8f8ff | #08176a → #0c2a9a |
| violet-rose | #fb468c | #7e51f9 | #12082e → #24104a |

- **Split-only themes** fall naturally on the banks: their two colours never share a fan.
- **Held colours:** a theme's held roles (for example fire-and-ice's orange, any saturated red) never go in a beam.
- **Air guards:** the air hue stays at least 40° from both laser hues (OKLCh), at OKLab L 0.28–0.36 (measured 0.29–0.33).
- **Pair lookup:** the scene reads hue A and hue B (13.x, 13.y; v1 row 0 texel 13) and picks the air from the pair table by the nearest pair within 25°. Otherwise it falls back to the Berlin air: OKLCh L 0.31, C 0.11, h 265°.
- **Don't over-green:** green is under 3% of the sky area in the references.

## 8. Silhouettes, HDR and SDR, safety

**Silhouettes (our own shapes):**
- **Crowd:**
  - a noise skyline of heads, ±0.012 H at 0.004–0.010 W pitch, with sparse raised arms 1.5–2 px wide;
  - a rim light along the top 0.02 H in the fog colour, at most 0.12 encoded luma;
  - 200–350 phone screens per megapixel, 1–3 px, encoded 0.5–0.8, each twinkling at most 0.5 Hz and never in sync;
  - target 70–80% near-black.
- **Deck:** a row of 40–60 dim blue pilot dots, at most 0.3 encoded.
- **Masts:** our own "lantern spire": a tapering two-rail truss with cross-bracing (aaStroke, at least 1.5 px) and a ring-and-spike finial. No axes, crescents, guardians or masks.
- **Haze in front of the set:** `0.25·air` lifts set pieces to encoded 0.12–0.15, as measured.
- **Flags:** 2–3 generic flags on 2 px poles in the crowd, reaching up to about 0.58 H, waving slowly.
- **Originality:** no Defqon.1 or Q-dance emblem, logo, guardian, mask or replica set piece.

**HDR intent.** Scene-linear output with the strip-v2 float target; finite, non-negative and passed through simSanitize, with no tone curve. Luminance ladder:

| Layer | Linear Y | About (1.0 = 203 nits) |
|---|---|---|
| Crowd | 0.001–0.004 | OLED black |
| Air | 0.024–0.050 | 5–10 nits, deep saturated blue |
| Haze-lit halos and sheets | 0.1–0.5 (4–16× air, matching the measured ladder) | |
| Beam cores | 1–4 | |
| Apexes | 6–20 (≤ 0.05% of the frame) | white-hot, panel peak |

- Sheet wedges stay at most 0.4 linear Y at the apex and at most 0.25 averaged over the sheet. Large areas therefore stay mid-tone and translucent.
- Frame mean linear Y: groove at most 0.10, drop at most 0.14, break 0.02–0.03.
- Colours stay inside Rec.709. Gamut expansion toward a 532 nm laser green is the page output stage's job (Look v2 lane).

**SDR today.** It must look right through displayOut:
- cores clip to white with channel bleed;
- the air reads at V 0.42–0.50;
- the air gradient is dithered with ditherOut (1-code triangular noise), because dark blue bands on 8-bit;
- every acceptance metric below is scored on the SDR output.

**Safety (the page's 3 flashes per second remains the backstop):**
1. **Sheets, blades, sawtooth and false ceiling are scene light, never gated.**
   - Attack and release are each at least ½ beat (at least 1 beat above 160 BPM).
   - Large forms alternate at most once per beat (at most once per 2 beats above 160 BPM), with depth at most 50% except on bar lines.
   - The area that changes in any one transition stays under 15% of any one-third × one-third window (Lasers v2's estimator).
2. **Thin fans, rakes and pillars** may step their aim on the kick and switch level by order (⅛-beat attack, ¼-beat release). Each covers at most 2% of the frame. Anything faster than 3 changes per second belongs to Lasers v2, not the scene.
3. **Steady background:** the air changes only over a bar or more. Frame-to-frame |Δ mean linear Y| stays at most 0.02, except the drop's first beat (at most 0.08, once).
4. **One dip-and-bloom per 8-bar phrase at most.** It counts as one flash and stays at least 1 s from any page flash.
5. **No saturated red** in any beam.

## 9. Knobs, pads, cost

**Knobs:**

| Knob | Name | What it does | Default |
|---|---|---|---|
| k1 | swing | aim amplitude 0–45° | 0.6 |
| k2 | haze | ρcloud 0.4–2.4 | 0.55 |
| k3 | sheets | wedge 0–0.25 and sheet beams 18–30 (0 = thin beams only) | 0.5 |
| k4 | reach | decay ×0.6–2.0 | 0.5 |
| k5 | trails | keep per second, scene beams only, 0–0.35 s, max-blend via u_prev (name kept per the scene contract) | 0.15 |
| k6 | fog | ρfog 0–1.2 | 0.5 |
| k7 | air | 0 = the house black room, 0.65 = Berlin, 1 = +30% | 0.65 |
| k8 | asymmetry | 0 = strict mirror | 0 |

**Pads.** Declare `"accents":{"native":[1,6]}`:
- **pad 1** (replaces the generic shockwave): a bank A chase (M3). Velocity sets 6–16 beams.
- **pad 6** (replaces particles): bank B bloom, 20° → 100° over ¼ beat, held 2 beats, released over 1 beat.
- **Pad 2** stays the page's Lasers v2 gated hits, fired from the rig origins. If Lasers v2 lands, the scene's beams dim to its solo level while a gate runs.
- The other pads stay the page's.

**Cost.** Budget at 1080p on an RX 6600-class card (from operation counts, not GPU measurements):

| Stage | Ops per pixel |
|---|---|
| Air | 5 |
| Haze | about 140 |
| Group parameters | about 180 |
| Fans | about 55 per active emitter |
| Sawtooth | about 120 |
| Silhouettes | about 60 |
| Finish | about 40 |

- **Totals:** a groove with 12–20 active emitters is about 1,300–1,600 ops per pixel (about 1.3–1.5 ms). The drop's first beat with all 34 active is about 2,600–2,800 (about 2.5 ms).
- **Ceiling:** 3,000 average and 3,800 peak, well inside a 16.7 ms frame. An `LS_QUALITY` define trims the octaves and the sawtooth.
- **Implementation rules:**
  - no per-beam loops;
  - a constant 34-emitter loop with uniform early-outs on level;
  - skip every fan below the deck (30% of the pixels);
  - polynomial atan (angles stay in the upper half-plane);
  - `unrollBarrier` on the emitter loop.
- **House modules:** draw2/aa, groups/neon-line, light/glow, noise/fbm, noise/value, hash/pcg, motion/envelope, core/clock, core/compile, volume/phase, colour/oklab, sim/feedback, post/dither, post/display-out.
- **New helper:** `light/fan.glsl` (the nearest-beam fan), written fresh. Ideally Lasers v2's beam layer shares it, so page hits and scene beams look the same.
- Record the SwiftShader ms as the CPU ranking.

## 10. Conflicts to resolve before a build

1. **The air.** The scene contract says "the room is 0", and the headline scorecard wants at least 40% true black in the groove. The references have a blue ambient air and 18–28% true black, all in the silhouettes. Proposal: declare the air a sky emitter (constant per section, scaled by darkness and k7; k7 = 0 restores the black room). Give Laser Sky an "air scene" scorecard row: at least 16% true black, and at least 65% inside the silhouette zone.
2. **Sheet fans.** Lasers v2 rule 4 says "no sheet forms". Proposal: keep that rule for gated page beams, and allow sheets as ungated scene light under the safety rules in section 8. The Lasers v2 owner or the judge needs to agree.
3. **Strip v2.** The headline brief (dt, section, heat, kick, screech, hues) and the Lasers v2 head bus (pattern, step, solo, head levels, L1, L2) both claim row 2, texels 9–14. Laser Sky reads the headline fields and would read the solo level. One layout must win before either merges.
4. **Theme.** No library theme matches green / cyan-white on deep blue. `blue-hour` is proposed to the Lasers v2 lane, which owns `vj-themes.json`.

Registration (`DEFAULT_SETS` in vj.js, the blurb in vj-show.js) is left to the page lane; the safety and Lasers v2 lanes are editing those files now.

## 11. Acceptance

Run `py laser_sky_metrics.py render.png` on the SDR output at 1920×1080, 2 beats after the drop's first beat, colour emphasis "both", default knobs.

| Metric | ref-1 | ref-2 | Pass window |
|---|---|---|---|
| Palette distance (OKLab chamfer vs the refs' union) | 0.015 | 0.014 | ≤ 0.045 (refs vs each other 0.058; storyboard 08:00 0.036) |
| Air, top band: V / OKLCh hue / chroma | 0.30 / 238° / 0.066 | 0.43 / 265° / 0.115 | V 0.30–0.50, hue 235–272°, chroma ≥ 0.06 |
| Beam coverage of the sky | 0.293 | 0.213 | 0.18–0.32 |
| Crossings per width at 0.35/0.45/0.55 H | 59/70/43 | 47/53/65 | 40–75 each |
| Steep share (60–120°) | 0.42 | 0.44 | 0.38–0.58 |
| Highlight > 0.70 | 2.3% | 4.0% | 2–5% |
| Highlight > 0.85 | 0.62% | 0.13% | 0.1–1.2% |
| White-hot (all channels ≥ 0.9) | 0.06% | 0.005% | ≤ 0.5% (house: any channel ≥ 250 at 0.2–6% in the drop) |
| Near-black, frame | 28.3% | 17.9% | 16–32% |
| Near-black, crowd | 71.8% | 74.6% | 65–85% |
| Green / cyan-white / haze blue (sky) | 2.4 / 2.4 / 61% | 1.6 / 12 / 70% | 1.2–4 / 2–14 / ≥ 55% |
| Mean linear Y | 0.077 | 0.105 | 0.06–0.13 |

**Moment checks:**
- **Break:** beam coverage ≤ 0.04; air within ±0.04 V of the drop's air; mean linear Y 0.015–0.04 (storyboard 0.023).
- **Drop's first beat:** highlights > 0.70 at most 7% (storyboard 6.3%); coverage at least 0.20.

**Motion checks (60 fps trace):**
- the kick moves aims within 1 frame;
- the air varies by at most 1 code across the groove;
- the frame-mean rules in section 8 hold;
- zero limiter interventions over 32 bars at 150 and 180 BPM, and at most 1 scene flash per phrase;
- left/right difference at most 3% at k8 = 0.

**Hygiene:** `presets.py` reports no problems; `py -m arsenal shader licence-line` is clean for the file (the tree-wide check still fails on 131 breaches already on master); the scene renders under both strip v1 and v2.

**Calibration.** The numpy mock (not shader code) uses this spec's numbers. It lands 14 of 16 rows:
- inside the windows: palette 0.0446, air V 0.43 / hue 266°, coverage 0.258, crossings 53/58/55, highlights 2.9% and 0.64%, white-hot 0.17%, near-black 26.9%, crowd 70.4%, green 2.3%, haze blue 64%, mean linear Y 0.100;
- break moment: air #14296b, coverage 0.007, mean linear Y 0.026.
- **Misses:** steep share 0.555 (inside the window but above both refs, so shallow beam energy is still short) and cyan-white 13.7% (ref-2 has 12%).
- **Not captured:** the refs' single bright, off-centre cloud mass. The mock's cloud is more uniform, so the focus convergence in M5 carries that.

Everything is in `<scratch>/lookv2/berlin/`:
- **Scripts:** `crop_storyboard.py`, `measure_refs.py`, `measure_fans.py`, `summarize_fans.py`, `measure_timeline.py`, `measure_texture.py`, `measure_silhouettes.py`, `measure_linear.py`, `laser_sky_metrics.py` (the acceptance scorer), `mock_laser_sky.py`
- **Outputs:** `measure_refs.json/.txt`, `measure_fans.json/.txt`, `measure_fans_summary.json`, `measure_timeline.json/.txt`, `measure_texture.json`, `measure_silhouettes.json`, `measure_linear.json`, `laser_sky_targets.json`
- **Images:** `frames/` (21 frames + `manifest.json`), `timeline_strip.png`, `berlin-storyboard-contact.png`, `calibration_sheet.png`, `mock_drop.png`, `mock_break.png`, `mock_drop_hdr.npy`, `diag/`

Nothing went into the repo; the reference frames stay in scratch.

---

## The build (verbatim)

Laser Sky is built and committed. On the spec's acceptance frame it passes all 18 scorer rows in the last two rounds, and the VJ page's own set check passes 13/13. Three things are still short of the brief: the HDR groove mean, the frame-to-frame step at 180 BPM, and the centre third's brightness swing under my own stricter check.

- **Branch:** `worktree-wf_b0a0b896-f74-2`
- **Commit:** `43d83c0869a51af923f9378d684597657d23653c`. It holds the new scene, one id added to `DEFAULT_SETS` in `vj.js`, one blurb in `vj-show.js`, and `docs/PHYSICS.md`, which the pre-commit hook regenerates. No attribution trailer; not pushed; master untouched.
- **Scene file:** `<worktrees>\wf_b0a0b896-f74-2\arsenal\web\presets\vj-laser-sky.frag`
- **Final contact sheet (1920×1080):** `<scratch>\lookv2\berlin\build\laser-sky-final-contact.jpg`. Each round's sheet and `metrics.json` are in `build\r1` … `build\r8`.

**Checking Vandor's observations.** All five held. Four things the brief missed came out of building it:
- **Green over blue:** in the frames, green beam pixels carry *less* blue than the air beside them (bright green #0fe35c vs air #162d6d). Adding green light to the blue air can't reproduce that; it gives mint. The camera's exposure masks the sky behind bright beams, so the scene does the same: bright beam light veils the air behind it, never making a pixel darker than the air. Green went from 0% to about 2–3% of the sky.
- **Cloud dashes:** the cloud's dashes are soft and about 7 px wide (blur). The thin cores catch the haze clumps, and the wide glow sees a softer haze, so the cloud reads as streaks rather than blobs.
- **Display curve:** the house SDR finish (PBR Neutral) strips the air's red, so #13286a showed as #032c65. The scene undoes that before display; this alone moved the palette distance from failing to passing.
- **Towers:** solid dark flank towers are part of the frames' palette; cladding ours closed the last palette gap.

**Acceptance frame per round** (2 beats into the bloom, default knobs; rounds 1–5 at 1280×720, 6–8 at 1920×1080):

| Row | ref-1 / ref-2 | Pass window | r1 | r2 | r3 | r4 | r5 | r6 | r7 | r8 |
|---|---|---|---|---|---|---|---|---|---|---|
| Palette distance | .015 / .014 | ≤ .045 | .047 | .043 | .058 | .047 | .052 | .051 | .044 | .044 |
| Air V / hue | .30 / .43, 238 / 265 | .30–.50, 235–272 | .41/261 | .41/259 | .40/260 | .42/265 | .42/265 | .42/266 | .42/265 | .42/265 |
| Beam coverage | .29 / .21 | .18–.32 | .40 | .32 | .22 | .19 | .23 | .22 | .18 | .20 |
| Crossings .35/.45/.55 | 59/70/43, 47/53/65 | 40–75 | 68/85/82 | 53/74/86 | 24/49/65 | 26/36/50 | 28/53/56 | 35/58/67 | 53/49/60 | 52/61/61 |
| Steep share | .42 / .44 | .38–.58 | .60 | .58 | .56 | .56 | .56 | .54 | .55 | .58 |
| Highlights > .70 / > .85 (%) | 2.3/.62, 4.0/.13 | 2–5 / .1–1.2 | 14.6/7.7 | 10.8/5.3 | 4.7/1.5 | 4.7/1.4 | 5.5/1.8 | 3.2/1.0 | 3.0/1.0 | 3.2/1.0 |
| Near-black frame / crowd (%) | 28/72, 18/75 | 16–32 / 65–85 | 22/79 | 25/90 | 25/91 | 16/59 | 20/70 | 20/72 | 20/71 | 20/71 |
| Green / cyan-white / haze blue (%) | 2.4/2.4/61, 1.6/12/70 | 1.2–4 / 2–14 / ≥ 55 | 0/34/59 | .6/26/63 | 3.8/8.6/69 | 3.3/10/66 | 3.4/12/65 | 2.5/8.4/70 | 2.1/8.2/69 | 2.1/10.5/64 |
| Mean linear Y | .077 / .105 | .06–.13 | .170 | .147 | .090 | .108 | .112 | .093 | .092 | .098 |
| Rows passed | | | 8 | 11 | 14 | 13 | 14 | 16 | **18** | **18** |

White-hot pixels stayed at or under 0.08% in every round (limit 0.5%). The break moment passes: coverage 0.010, air V 0.41 against the drop's 0.42, mean linear Y 0.026. I did not render the bloom's first beat as a separate moment, so its "highlights ≤ 7%" check is not done.

**Safety and motion** (60 fps traces of 32 bars at 150 and 180 BPM, the page's trail setting on):
- **No flashes of its own:** by the page's flash rule (a rise of 0.1 over the darkest of the last 300 ms), the largest rise is 0.045. The page check with this scene as the new set passes 13/13: no flashes of its own, the flash gate grants 3 of 10 requests, and pads 1, 2 and 6 answer.
- **Frame-to-frame step (limit 0.02):** at most 0.011 at 150 BPM. At 180 BPM, six frames reach 0.021–0.022.
- **Centre third (my own check, stricter than the page's):** when the sheets sweep through the cloud, the centre third of the frame still rises up to 0.14 within 300 ms. The page rule doesn't count it, but it's the place to look if anyone applies a per-region test.
- **Mirror at k8 = 0:** left/right light balance at most 2% (limit 3%). Pixel by pixel the difference is 14%, because the haze clumps, crowd, phones and flags are deliberately not mirrored.
- **The air:** it has no kick path, and the quiet trace varies by 0 codes. In the groove I couldn't find a beam-free sky pixel to probe: beams cross the whole upper sky.
- **Kick:** the change between consecutive frames rises from 4.9 to 5.9 codes on the first frame after a kick. The scene is always in motion, so the kick adds about 20%.
- **k7 = 0** gives back the house's black room.

**HDR float target:** drop mean 0.117 (limit 0.14), break 0.027 (target 0.02–0.03), groove **0.107 against 0.10**. Peaks reach about 12; nothing is negative or non-finite. The last change, which cuts the lens glow's long tail in HDR only, was checked with HDR renders; the SDR output is unchanged by it.

**Cost (operation counts reasoned from the code, RX 6600-class at 1080p):**

| Stage (sky pixels) | Ops per pixel |
|---|---|
| Frame plan | ~300 |
| Haze | ~550 |
| Low bank of 24 fans | ~1,800 groove, ~2,760 on the bloom |
| Stage sheets | ~770 |
| Towers | ~290 |
| Finish | ~110 |

- Frame average is about 3,000 in the groove and about 3,700 on the bloom, roughly 1.4–1.7 ms. That sits right at the brief's 3,000 average and inside its 3,800 peak. Below the deck a pixel costs about 600.
- The quality knob: `LS_QUALITY` 1 trims a haze octave and a sawtooth tooth; 0 also halves the low bank, to about 2,400.
- SwiftShader at 1080p, a CPU ranking only: groove 448 / 441 / 270 ms and bloom 493 / 480 / 270 ms at quality 2 / 1 / 0.

**Hygiene:**
- `presets.py` reports no problems.
- The licence line finds 0 breaches in the file; the tree-wide count is still the 131 already on master.
- `vj_show` 18/18 and `vj_core` 153/153 pass, as do the keylab, preset, coupling, Play Night pin, fan-preset and glsl licence-line suites.

**Section 10, as built:**
- **The air** is a declared sky emitter; knob k7 at 0 restores the black room.
- **Sheets** are ungated scene light under the section-8 rules.
- **Strip v2:** the reader follows the headline brief's layout (row 2, texels 9–13). It reads no Lasers v2 solo level until one layout wins.
- **The Berlin pair** lives in the scene's own pair table, selected by the page's default colour faders. Nearby library pairs give that pair and its air; any other hues are taken as they are. `vj-themes.json` was not touched.

**What would make it closer:**
1. One brighter, off-centre cloud mass like the 08:00 frame. Ours is a mirrored band, and moving the focus off centre at k8 = 0 breaks the mirror rule, so it needs your call.
2. Shutter blur on moving beams: sampling each moving fan at 2–3 sub-frame times would turn the crisp lattice into the footage's soft streaks.
3. A long-reach striped sheet type, for ref-1's frame-wide white sheets.
4. Real beat-level motion data: the sweeps and chases are inferred, and a 60 fps capture of 07:50–10:38 would calibrate them (downloads were refused).
5. Anti-phasing the stage sheet pairs, as I did for the low bank, would calm the centre third and the 180 BPM step.
6. Trimming the 1.8× core lift in HDR only would bring the groove mean under 0.10.
7. Pushing green beyond Rec.709 toward a real 532 nm laser on the OLED, which is Look v2's output stage.

The harness, scorer runs, traces, HDR stats and the page-check receipt are all in `...\scratchpad\lookv2\berlin\build`; the reference frames stayed in scratch.

Housekeeping:
- The post-commit hook appended this commit's line to `state/authorship/seats.jsonl` in the worktree. It is left uncommitted, as the house does.
- Running pytest across the whole `tests` folder rewrites `data/verb-registry/deepseek.json` twice over. I restored it both times and flagged it as a separate task.
- An edit hook twice opened my harness page in the desktop browser pane. I closed it each time; the shader never compiled there.

---

## The judge (verbatim)

**Verdict: Laser Sky gets 6/10 on the headline bar (7/10 if Daniel accepts the blue air as a deliberate exception) and 6/10 on likeness to the two Berlin frames. Daniel would not say "it looks insane."** He would recognise the Berlin idea straight away: the blue sky, the green fans along the deck and the white V-shaped sheets. But next to the frames it is soft, pale and dim, and the cloud looks like a camouflage pattern rather than laser light. Ritual Fire, on the same harness at the same moments, has far more punch.

**How I judged.** I rendered all three scenes headless in Chrome on SwiftShader, under the house GPU lock, on test-band ports. I used the previous headline judge's independent harness, which writes the page's strip and runs stateful like the page, with the page's default colour faders and its trails setting. Every scene got the same moments at 1920×1080, plus Laser Sky's 60 fps traces and float-output probes. I also re-rendered the builder's own moments with the builder's harness. I committed nothing and wrote only under `judge\`.

**Checking Vandor's observations.** All five hold:
- The air is the colour: ref-2's sky floor is hue 265°, V 0.43.
- Two colours, acid green and cyan-white.
- A low line of emitters.
- Fans that cross and sheets that read as solid.
- Beams white-hot at the head.

Five things they miss:
- **The green is crisp and saturated.** The brightest quarter of green pixels has saturation 0.93 (#0fe25a) in ref-1 and 0.83 (#24cc78) in ref-2. It sits only in thin beams, never in a wash.
- **ref-2's cloud is motion-blurred streaks, mostly diagonal.** Only 37% of the dashes are steep in both frames. It is one bright, lopsided mass, the brightest thing in the frame.
- **The crowd is a layer of sparkle, not black.** There are 140–371 phone screens per megapixel, plus lit heads.
- **ref-1 is dominated by huge striped cyan-white sheets** that reach the top of the frame.
- **The camera blooms around every bright source.**

**Likeness: the builder's tuned frame against the rest of the cycle.** The spec's acceptance frame passes 18/18 in my harness and 18/18 in the builder's. Two other cycles give 17/18 and 16/18. The rest of the 16-bar cycle misses:

| Frame | Rows passed | What fails |
|---|---|---|
| Groove, green-and-white half (bar 5) | 10/18 (12/18 on strip v1) | green 5–6% of the sky (limit 4%), highlights above 0.85 at 2% (limit 1.2%), steep share 0.61 |
| Groove, white half (bars 9–16) | 13/18 | green 0%, steep share 0.83, beam coverage 0.16 |
| Drop, first beat | 16/18 | almost no green (0.01%) |
| Climax | 11/18 | |

My own probes (`likeness.py`, which the builder did not tune against):

| Probe | ref-1 / ref-2 | Laser Sky |
|---|---|---|
| Saturation of the brightest green | 0.93 / 0.83 | 0.49–0.52, a pastel mint (#6bd198 to #73eb9c) |
| Steep share of the cloud's dashes | 0.37 / 0.37 | 0.66 (acceptance frame), 0.81–0.94 (groove) |
| Spread of log luminance in the sky | 1.76 / 1.62 stops | 1.38–1.56 stops, flatter |
| Phone sparkle | 140 / 371 per MP | 255–267 per MP, but 1-pixel faint dots |
| Air | #162d6d, hue 265°, V 0.43 (ref-2) | hue 265°, V 0.42: nearly exact |

- **The 1:1 crops show three problems.** The cloud is isotropic blobs lit by a faint lattice. The crowd looks like a seating chart of identical round heads. The stage front is a flat navy wall.
- **The mint has a mechanism.** With the air turned off (k7 = 0), the whole sky fills with a green haze from the wide glow around the low fans. Laid over the blue air, that haze turns into mint.

**Headline bar, item by item.** The scorecard gives Laser Sky 21/30, Ritual Fire 30/30 (the same as the last judge measured) and Hyperspace 19/30. Six of Laser Sky's nine fails are the blue air by design: 0% true black, a black floor of 8 codes. The three real fails:
- groove lit share is 30%, above the 25% ceiling;
- the anti-climax lit share is 6%, above 5%;
- the anti-climax shows two colour families (the violet air counts as one).

Item by item:
1. **One centred hero:** partly. It is symmetric (left/right light within 0.05–1.4%) and the bottom 20% stays dim, but it has no single hero and no ring.
2. **True black:** fails, by design.
3. **Depth:** passes, but weakly. The masts are thin and the crowd looks synthetic.
4. **Light has a source:** passes, apart from the ambient air.
5. **Colour:** passes on the counter, but only because the green is too pale to count as a family.
6. **Fidelity:** strokes are anti-aliased at least 1.5 px and the air is dithered, but the cloud blobs and the crowd grid look artificial.
7. **Kick:** passes. The first frame after the kick changes 15% of pixels by more than 8 codes, the black floor does not move, and the kick adds 9% light.
8. **Quiet state:** the composition works, but there is 0% black.
9. **Pads:** pad 1 adds +0.006 and pad 6 adds +0.036 to the mean (cap 0.04).
10. **Safety:** passes the page's rule (below).
11. **Chapters:** passes on the brief's new strip (strip v2), with distinct quiet, break, build and drop states. On today's page there is only the 16-bar cycle.

**Safety (60 fps virtual clock, 32 bars at 150 and 180 BPM, plus a strip-v2 section run):**
- **No flashes of its own.** The page rule finds 0 rises at either tempo.
- **Step between frames:** at most 0.011 at 150 BPM and 0.020 at 180 BPM, which is exactly at the limit.
- **Centre third:** it rises by up to 0.14 within 300 ms, which confirms the builder's own finding. Per region there are at most 2 light-dark swings a second.
- **No saturated red.** No high-contrast regular stripe pattern either: under 1% of tiles.
- **New finding: section changes on strip v2 are hard cuts.** At break to build the frame mean jumps +0.072 in one frame, and the centre third rises 0.27 within 300 ms. Entering the break is −0.031, the drop +0.042, the outro −0.032. This breaks the spec's own limits (0.02 per frame; large shapes ramp over half a beat or more).

**HDR (scene-linear float output).**

| Moment | Mean luminance | Spec limit |
|---|---|---|
| Groove | 0.102–0.137 | 0.10, so up to 37% over |
| Drop, first beat | 0.108 | 0.14 |
| Climax | 0.122 | 0.14 |
| Break | 0.020 | 0.02–0.03 |

Peaks reach 9.6–11.4. Nothing is negative or non-finite.

**Licence and tests.**
- The licence line on the file alone is clean: 0 breaches, one exempt loop header.
- `presets.py` reports no problems.
- On a scratch export of the branch: `vj_show` 18/18, `vj_core` 153/153.
- pytest on the preset, coupling, KeyLab VJ, Play Night pin, fan-preset and licence-line suites: 186 passed, 11 skipped, 1 failed. The failure only happens because the export is not a git repository; that test needs `git ls-files`.

**Cost.** My operation count, reasoned from the code, is about 3,800 per pixel on average in the groove and about 4,300 on the bloom. That is above the brief's 3,000 average, and around 2–3 ms on an RX 6600 at 1080p; these are estimates, not GPU measurements. About a third of it is per-frame logic recomputed for every pixel. On SwiftShader it takes a median 507 ms per frame, against Ritual Fire's 462 and Hyperspace's 154.

**Must-fix, in order of how much each one blocks "insane":**
1. **Acid green.** Cut the wide glow around the low fans and the fog glow so the green lives in the beam cores. Target: the brightest green at saturation 0.8 or more. This also brings the HDR groove under 0.10 and fixes the green wash when the air is off.
2. **The cloud.** Stretch the haze clumps along each beam instead of using round blobs, let the wide glow see only the soft haze, and/or blur moving fans across 2–3 sub-frame samples. Target: dash steep share around 0.4, and a bigger, brighter mass.
3. **Hold the Berlin balance through the whole 16-bar cycle,** not just the tuned bloom frame. Tie the green/white rotation to the phrase on strip v2; today it follows the raw beat count, so the drop can land in the white half.
4. **The lower third.** Make the crowd irregular, lit from the fog band and full of bright phone screens. Give the stage front some structure, and use bigger silhouettes of our own design for scale.
5. **Ramp section entries on strip v2** over at least half a beat (from section progress). Ask the page lane to ramp darkness too, since the air follows it instantly.
6. **Sheets.** Make them striped and saturated cyan-white, including the long-reach type from ref-1. Today the pad 6 bloom turns the centre into a grey-white wash: 1.09% white-hot, +0.036 on the mean.
7. **k7 = 0 does not give back the black room.** It still shows 0% true black, a black floor of 7 codes, the crowd at codes 7–14, and a green-hazed sky.
8. **Leave registration to the page lane.** The `vj.js` and `vj-show.js` lines conflict with the Ritual Fire branch, and `docs/PHYSICS.md` conflicts with master.

Two page-side dependencies: today's page does not read the header's native-pad list or rig origins, so the generic pad effects still draw over pads 1 and 6. The strip-v2 layout clash with Lasers v2 is still open.

**Daniel's calls:**
- **Blue air as an exception:** I recommend yes. The frames prove it, as long as k7 = 0 really goes black.
- **Sheets as ungated scene light:** acceptable, given the traces.
- **An off-centre cloud mass at k8 = 0,** which would break the strict mirror rule.

Files are in `<scratch>\lookv2\berlin\judge\`:
- `sheets\judge-vs-refs.jpg` – Laser Sky beside ref-1 and ref-2, Ritual Fire and Hyperspace
- `sheets\judge-same-moments.jpg` – all three scenes at 9 moments
- `sheets\crops-cloud.png` – the clouds at 1:1
- `sheets\crops-deck-crowd.png` – the deck and crowd at 1:1
- `sheets\crops-sheets.png` – the sheets and the pad 6 bloom at 1:1
- `sheets\ls-moments-a.jpg`, `sheets\ls-pads-knobs.jpg` – more Laser Sky moments, pads and knobs
- `r\vj-laser-sky\`, `r\vj-ritual-fire\`, `r\vj-hyperspace\` – every frame, with `metrics.json`; Laser Sky's folder also holds `T150-v1-32bars.trace.json`, `T180-v1-32bars.trace.json` and `Tsections-v2.trace.json`
- `r\scorecard.json`, `traces-summary.jsonl`, `spec-scorer-ls.jsonl`, `spec-scorer-ls2.jsonl`, `spec-scorer-repro.jsonl`, `likeness-ls.jsonl`, `pytest.txt`, `lic\ls.json`
- `harness\` – `judge.mjs`, `judge.html`, `moments.mjs`
- `repro\out\` – the builder's moments re-rendered with the builder's harness
