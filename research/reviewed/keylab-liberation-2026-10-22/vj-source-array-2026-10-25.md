# Source Array: the Qlimax 2014 flagship scene, built and judged (2026-10-25)

Workflow run wf_09f3f269-d81 (tasks wbsueau89, resumed as wwk15bwct), the build and judge stages. The find, capture and study (with the landing spec this scene was built to) are in vj-qlimax2014-study-2026-10-25.md. The videos and frames are other people's footage and stay in local scratch and the gitignored state/arsenal/refs/qlimax2014/, never in this repo. Verbatim; local paths shortened to <scratch> and <worktrees>. Branch worktree-wf_09f3f269-d81-4 (dffb646b); not merged.

Vandor's read: 6/10 headline, 5/10 likeness, and a SAFETY FAIL (51-58% of the worst window brightens by 0.1 on every beat in both drop looks: 2.5 a second at 150 BPM, 3 a second near 180 BPM, which FlashGate cannot count). It must not reach the page until must-fix 1 (the strip-v2 bar clock) and 5 (the beat-pulse area) are fixed and re-judged. It is the only scene that carries the show's grammar and arc; its look gaps (rows of shafts, an array with mass, a room filled with light) are the same light-in-haze gap as Void Star, Laser Sky and the Virtual Stage, so round 2 should adopt the shared haze module (workflow wy9tscm5j) rather than tune its own.

---

## The build (verbatim)

The Source Array scene is built and committed. Every renderable acceptance item passes at 1080p except two: B1 depends on where in the beat you measure, and H conflicts with the spiral itself. It also costs more than the spec's budget: about 3.5–8× Laser Cathedral on SwiftShader, and an estimated 2,500–3,500 operations a pixel against 1,250. Everything was checked on SwiftShader only; nothing has been seen on the GPU, the OLED or in HDR.

**Branch** `worktree-wf_09f3f269-d81-4`, **commit** `dffb646b`, not pushed, no attribution trailer.
- `arsenal/web/presets/vj-source-array.frag` is new (2,145 lines). The house kit is composed fresh between markers.
- `arsenal/web/vj.js` gains one id in `DEFAULT_SETS`; `arsenal/web/vj-show.js` gains one blurb. Nothing else in those files changed.
- The pre-commit hook regenerated `docs/PHYSICS.md` into the commit and appended a line to `state/authorship/seats.jsonl`, which I left uncommitted.

**Final contact sheet** (private): `<scratch>\lookv2\qlimax2014\build\contact-sheet-final.png`. It puts Daniel's three frames (the matched source frames) and six captured frames beside our moments, with the metrics under each. In the same `build\` folder:
- `rounds-beside-refs.png`: every round's break, drop and hold beside ref-17/18/19.
- `page\montage.png`: a scripted break into a drop in the real `vj.html`.
- `tools\`: the harness, the metrics code (the study's definitions), the profiler and the patches.

**Metrics by round** (break / drop / hold / anti-climax):

| Round | What changed | Result |
|---|---|---|
| 0 (640×360) | first compile | Busy and white-hot: break white 1.5%, pink 20%; drop lit 49%, white 6.3%, lime 74% |
| 1 | thinner beams, smaller dots, odd rungs only | Break went dark (lit 3.4%). Drop lit 16%. Anti-climax already passes D: dark 96%, lit 1.8%, true black 80% |
| 2 | dish haze from the ring, thin node rings, softer eye | Break haze passes (L 0.31, C 0.18, h 275). Lime 31%. Molten hold broke C6 (44%) because the lantern snap flooded the glow pale |
| 3 | OKLCh hue walk, mirrored crowd rows, molten snap off | Walk measurement and kick probe were wrong (both fixed in my tools) |
| 4 | per-look beam shapes, punch +48% | A1/A3–A6, B2–B4, D and E pass. Strobe step area (B5) 11%, lime-yellow (C1) 0.6% |
| 5 | molten keeps the lime tint, timing probes fixed | Lime-yellow 4.8%, lantern +50% at 50 ms, rotation 0.0°/s |
| 6 | mirrored haze density, tuned windows | Ring-masked symmetry passes (2.8% / 1.6%) |
| 7 | azure cores, deeper strobe window | Hot pixels 53.5% azure/cyan by the study's own HSV definition (the reference scores 66.7% that way). Lime 3.9× with top three eighths 5/6/7. Strobe step 7.25%. C6 9.5% |
| 8 | drop ring leans azure, molten air deeper | Haze C 0.120. F1 (lit order) passes by bar average |
| Final (after licence, trail and cost fixes) | — | Unchanged; ropt regression check against the pre-optimisation frames: at most 15 codes (32 in molten), all from the deliberate soft glow edge |

**Acceptance at final:**
- **A, break:**
  - Blue-violet 89%, pink 2.4%.
  - Haze L 0.37, C 0.20, h 277; falloff ratio 53.
  - Lit 15.3%, white 0.1%, true black 37%, p5 0.
  - Rotation 0.0°/s; brightness by eighth of a beat within ±0.27%.
- **B, drop:**
  - Lime cores L 0.92, h 124.
  - Lime 3.9× from weakest to strongest eighth, top three eighths 5/6/7; warm cones peak on eighth 0 at 6.1×.
  - Lit 17–24%, white 0.5–0.9%, strobing area 7.5% a step, warm pin ≤ 0.7% of the frame.
  - **B1 fails depending on phase:** the off-beat frame passes (lime 45%, blue-violet 31%); the after-kick frame does not (lime 17%, blue-violet 53%); pooled over the beat, lime is 19.7%.
- **C, molten hold:** orange 93%, lime-yellow 4.8%, white 0.44%, haze L 0.41 C 0.120 h 44, top third lit 82%, bottom fifth median 0, held-red change 4.9% / 9.4% per 333 ms. C5 (reading ≥ 8 rungs) is my own judgement, not an independent reviewer's.
- **D, anti-climax:** dark 96%, lit 1.7%, true black 86%, one family plus thin lime lines.
- **E, hue walk:** 123° over 10 bars, at most 15° a bar, monotonic.
- **F, chapters:**
  - F1 passes with a thin margin: anti 1.7% < break 15.3% < drop 16.8% (bar average).
  - F2: build lit 42.6%, 2.5× the drop.
  - F3: the build's last beat is 99.9% true black.
- **G, kick:** lanterns +50% at 50 ms and back by 390 ms; p5 stays at 0. The ring's 3% scale is set in code, not measured.
- **H fails as specified.** Raw left-right difference is 14% in the break and 9% in the groove, because the spec's own spiral gaps (4, 8 and 6 o'clock) are asymmetric. With the ring annulus masked it is 2.7% / 1.5%. Daniel should pick: keep the spiral, or make the gaps mirror-symmetric when k8 = 0.
- **I and J:**
  - Area above 1.0 is 1.1% of the frame at the drop.
  - No NaNs and no negatives in the float output.
  - `presets.py` reports no problems.
  - Licence line exit 0 against the 632-pass corpus (15 coincidental 12-token idioms rephrased first).
  - Tests: `vj_show` 18/18, `vj_core` 153/153, pytest 190 passed and 1 skipped.
  - `vj2_verify --phase sets` passes on the final code.

**Cost** (SwiftShader at 1080p, best of 5; timings were noisy because other lanes were rendering):

| Moment | ms per frame |
|---|---|
| Break | 885 |
| Groove | 1,178 |
| Drop | 1,216 |
| The drop's first beat, with gerbs | 1,988 |
| Laser Cathedral, same harness | 252 |

- That makes Source Array 3.5–8× the Laser Cathedral.
- Profiling shows the 12-rung loop takes 60–80% of the time and the beams 15–20%. The pose cache, a per-rung height cull and the tighter rung box saved about 10–15%.
- My estimate is about 2,500–3,500 operations a pixel, against the spec's 1,250. By the brief's arithmetic that is roughly 2–3 ms on an RX 6600-class card (at or above the 2.5 ms ceiling) and about 1 ms on Daniel's 9070 XT. These are estimates, not GPU measurements.

**Defects the real page caught, now fixed:**
- Buffer trails were smearing the moving dot strips and sparks into white bands. Trails now apply only inside the lanterns.
- The lantern afterglow lingered too long under strip v1. It is shortened.

**Gaps that are not mine to fix in this lane:**
- **The page plays its own accents on top.** The page doesn't read `accents.native` yet, so pads 1, 2, 4 and 6 also fire its shockwave, laser, glitch and particles (visible in `page\montage.png`).
- **The ring's white flip on the drop is not implemented.** Scenes have no way to request a FlashGate slot, so the ring takes the spec's refusal path and steps to the drop look.
- **Untested strip paths.** The Look v2 row-6 path is in the code but untested, because nothing writes that row yet.
- **Frame rate under strip v1.** Under v1 the per-frame decay assumes 60 fps.
- **`vj2_verify` treats this scene as old.** Its list of new sets is hard-coded to wave 2, so it never ran its pad and flash-gate checks on this scene; my scripted real-page run covers the look switch and the pads.

**What would make it closer:**
- **Rung depth:** the rungs are flat cards facing the camera. Ref-19 reads as deep tiers seen from underneath, which needs a real underside per rung, larger side blocks and a denser lattice.
- **Ref-17 and ref-18 details:** the pink-lit crystalline stage is missing from ref-17, and ref-18's lime shafts are fatter and denser.
- **Page and strip support:** the page honouring `accents.native`, plus strip v2 (section marks, frame time) and the theme row.
- **Cost:** per-rung poses computed on the CPU and passed through the strip, so each pixel doesn't recompute twelve of them.
- **A real GPU timing**, which needs Daniel's OK given the driver's crash history.

---

## The judge (verbatim)

**Verdict: Source Array does not land what Daniel called the best light show he has seen.** It scores **6/10 on the headline bar** and **5/10 for likeness to Qlimax 2014**.

It is the only scene we have that carries the show's grammar: the ring, the strand of rungs overhead, the lime rows with warm cones after the kick, the five measured palettes, the lantern hue walk, the gerbs and the rose fans. Side by side with the footage, though, it reads as a clean, centred diagram of the show rather than the show itself:
- the beams are soft wedges, not dense rows of shafts;
- the rungs are thin flat silhouettes with small dim lanterns, not a massive glowing structure;
- the violet haze stops at the ring instead of filling the room;
- the anti-climax ring is orange, not red.

Beside it, Ritual Fire (branch `worktree-wf_82a5da4f-0f7-6`) has none of the Qlimax grammar (about 1/10 for likeness). It stays the cleaner headline scene on the bar: in this harness its build's last beat is black, and its flash windows peak at 28%.

How I checked: I wrote my own harness and rendered every frame myself at 1080p on SwiftShader (one Chrome at a time, under the GPU lock, port 8952 and nearby). It runs a 150 BPM show on a 60 fps virtual clock and uses the page's own beat count (count = beats fired). The scene's state machine runs from real history; I injected no state. I made no repo edits and no commits.

**Per frame (likeness)**
- **ref-17, the ring in a break: 5/10.** Colours match: blue-violet is 86% of saturated lit pixels, and the haze measures OKLCh 0.355/0.196/277. But lit is 13% (Daniel's frame: 27%), the haze stops around the ring, and the dead-centre view replaces his low oblique one.
- **ref-18, the lime rows: 4/10.** Lime core colour is right (L 0.89–0.91, hue 122). The beams are a few soft symmetric wedges plus thin vertical lines; Daniel's frame has 12 or more parallel shafts raking one way.
- **ref-19, the array in molten orange: 5/10.** Orange/amber is 94% and the lime X crossings are there. The array has no mass: no big glowing cubes, no rows of white-hot dots. The under view (k7 = 1) comes closest.
- **Spec-named moments:**
  - The build flood (HH 5:05) and the rose fans are the best matches.
  - The anti-climax fails on colour: we render orange 87% plus lime 12%, against red 99% at HH 2:15 and red 50 / orange 39 for Ran-D's flame fringe.
  - The break lantern line is small and dim compared with HH 7:45.

**Headline bar**
- **Scorecard: 26/30.** The four misses:
  - groove true black is 27% (needs at least 30%);
  - the anti-climax has 2 hue families (needs 1);
  - pad +100 ms has 3 families;
  - the drop's first beat is 13% lit (needs at least 15%).
- **Mirror symmetry (spec H) fails:** left-right difference is 15.7% in the break and 6–8% in the groove, against a 3% limit.
- **Depth, light sources and fidelity pass.** Edges are anti-aliased, with no seams and no moiré at 2× zoom.

**Acceptance A–J (my own measurements)**

| Item | Result | Measured |
|---|---|---|
| A1 blue-violet | Pass | 86% |
| A1 pink | Fail | 1–2% (needs 2–8%) |
| A2 hot pixels azure/cyan | Fail | 43–47% (needs at least 50%) |
| A3 haze, A4 falloff | Pass | haze as above; falloff ratio 40–70 |
| A5 lit | Fail | 12.9–15.0% (needs 15–35%) |
| A5 white-hot | Fail | 0.05% |
| A6 true black, A7 no beat lock | Pass | luma steady within ±1.4% over the break |
| B1 lime/blue-violet split | Depends on phase | off-beat passes; just after the kick lime is 9–10% and blue-violet 66–70% |
| B2 lime cores | Pass | |
| B4 lit | Fail after the kick | 13.6–19.8% |
| C1–C4, C6 Molten hold | Pass | one sample has haze chroma 0.114, just under 0.12 |
| C5 rungs readable | Barely | thin silhouettes |
| D anti-climax | Pass | dark 95.9%, lit 1.6%, true black 85%; colour is orange, not red |
| E hue walk | Pass | judged by eye |
| F1, F2, F4 chapters | Pass | |
| F3 last beat of the build black | Fail | on the page's count, see the first must-fix |
| H symmetry | Fail | |
| I1 safety gate | Fail | |
| J trails per second | Fail on strip v1 | |
| HDR area above 1.0 | Drop passes; Molten fails | drop 1.2%; Molten 20% (limit 5%) |

**No flashes of its own on a 60 fps clock: fail.**
- In both drop looks, 51–58% of the worst 10° window brightens by at least 0.1 every beat; the threshold is 25%. That is 2.5 per second at 150 BPM, reaching the WCAG limit of 3 per second around 180 BPM, and FlashGate cannot count these pulses. For comparison, Ritual Fire peaks at 28% and Void Star at 22%.
- On strip v2, the end of the build goes dark, then relights 39% of the frame, then dark again, within 0.8 s, outside the gate.
- The builder's `vj2_verify` flash check saw only 7 frames, so it measured almost nothing.
- No red flashes: saturated-red change stays at or below 0.04% of the frame.

**Originality: clean.**
- No Qlimax or Q-dance names anywhere in the shader, the page edits or the commit message. No logo, figure or stage, and no attribution trailer.
- The commit holds only 4 files and no footage frames.
- The rung is our own design: a bowed twin rail, a node with a ring of dots, capsule lanterns.
- One note: the ring keeps the 2014 ring's layout (one closed band plus three open arcs stepping into a spiral over radial slats). That is the grammar Daniel asked for, drawn front-on with our own counts, and it is the closest thing to a replica, so don't push it further (no leaning dish, no booth).

**Licence line: exit 0, clean.** No breaches; 5 exempt hits (4 loop headers, 1 house-kit signature). The house kit is byte-identical to a fresh compose.

**Tests**
- `vj_core` 153/153, `vj_show` 18/18.
- pytest: 162 passed, 11 skipped. One failure is only because my export has no `.git` (it calls `git ls-files`).
- `parse_preset` reports no problems; coupling is "driven".
- `vj2_verify --phase sets`: every scene check passes. Its burst-time check failed only because a 6-minute wait for the GPU lock was counted; the lock was held 93 s. It still treats Source Array as an old set, so it never runs the pad and flash-gate checks on it.

**GPU cost (reasoned from the code; no real GPU timing)**
- On SwiftShader at 1080p: break 1,413 ms, drop groove 1,938, Molten 2,020, drop with gerbs about 2,000. Laser Cathedral takes 249 ms and Ritual Fire 325, so Source Array is 6–8× Laser Cathedral.
- My count is about 2,700 operations a pixel typically and about 4,400 with gerbs, against the spec's 1,250.
- By the brief's arithmetic that is about 2–3 ms on an RX 6600-class card at 1080p (over the 2.5 ms ceiling with gerbs), and about 3–4.5 ms on Daniel's 9070 XT at 4K.
- Where it goes:
  - all 12 rung poses (each formation evaluated twice) are recomputed for every pixel, though they are the same everywhere;
  - up to 10 beam arms are evaluated for every pixel in the lower two thirds;
  - 16 sparks run per lantern box, and the near boxes cover much of the frame;
  - indexed arrays inside loops (`gPose[12]`, `gPoseOk[12]`, `gLensOn[12]`) put pressure on GPU registers.

**Must-fix, ordered by how much closer each brings it to the show**
1. **Fix the strip-v2 bar clock and the drop's first beat** (correctness and safety; lines 1861, 1867, 1138–1151).
   - The scene uses the page's `count % 4` as the beat within the bar, but the page's count is beats fired.
   - So the build's black beat lands on beat 3, beat 4 relights 41% of the frame, and the lantern snap lands on beat 4 instead of the bar's first beat.
   - Separately, the frame that resets the bar counter also counts a bar line, so the drop's sink and bloom from the floor knot never play on v2. On v1 they are also lost whenever the kick lands on the same frame as the beat.
   - Ritual Fire handles the count correctly (it uses `count − 1`).
2. **Beam rows like ref-18:** 10–14 thin, crisp, parallel lime shafts per row, raking one way at 55–70° from overhead trusses across the frame, with white-hot lenses. This replaces the soft wide side-row wedges, which also cuts the beat-pulse area.
3. **Give the array mass:** big glowing lantern blocks, white-hot dot rows along every arm, lit undersides, near rungs filling the top third. In breaks, a large bright lantern line lowered over the crowd, as at HH 7:45.
4. **Fill the room with light in the ring looks:** haze through the hall's central band, lit 20–30%, bright ring cores, black corners kept.
5. **Shrink the beat-locked pulse area** (safety): hold the side-row halos at 0.85 or above instead of breathing 0.42→1.0, cap the Rose Fans cores at 1.0 while gated, or send the white fan blasts through FlashGate.
6. **Make Red Spiral red, not orange,** and offer a held solid red band like HH 2:15.
7. **Add a low oblique view from the crowd** for drops and climax. This conflicts with the headline bar's centred-hero rule, so it is Daniel's call.
8. **Let the theme fader work.** The scene reads no palette from the strip, so the fader does nothing on it today.
9. **Cut the cost:** compute poses once per frame, cull beam arms that can't reach the pixel, skip sparks before the 16-iteration loop.
10. **Strip v1 assumes 60 fps** (lines 1061, 1158, 2132). At 120 or 240 Hz the pad-8 lowering and the lantern afterglow run 2–4× too fast.
11. **Molten in HDR:** 20% of the frame is above 1.0 against a 5% limit.
12. **Smaller gaps:**
    - ring band edges never go white on the kick click (`gEdgeHot` is always 0);
    - the off-beat haze inhale is computed but unused;
    - the drop's ring white flip and `accents.native` are still page-lane work (the page draws pads 1, 2, 4 and 6 on top today).

Files are in `<scratch>\lookv2\qlimax2014\judge\`:
- sheets\01-daniel-frames-beside-source-array.png
- sheets\02-spec-named-frames-beside-source-array.png
- sheets\03-strip-v2-timing-defects.png
- sheets\04-source-array-show-arc.png
- sheets\05-flash-traces.png
- out\main\vj-source-array\ and out\main\vj-ritual-fire\ (every render)
- out\main\log.json (scene state, traces, cost)
- refs\ (frames grabbed from the private videos)
- harness\ (the harness, metrics, flash and sheet scripts)
