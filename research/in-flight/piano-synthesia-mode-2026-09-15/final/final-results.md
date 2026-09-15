# Synthesia bake-off, final heat: results (2026-09-15)

- Sheet: `bakeoff-final/final-sheet.jpg`, built by `bakeoff-final/make_final_sheet.py`.
- Sheet layout: four columns in rank order. Rows: the hard Gbmaj13#11 portrait still, six-Eb4 frame m6 (t 1.87), phrase frame m3 (t 4.10, just after the 4.08 lift), loudest run frame m3 (t 3.00, peak F5 at 2.88) and the hard Gbmaj13#11 landscape still.
- Every entry was rendered on the shared `?set=heat1` fixtures, in portrait and landscape.
- Render bursts all passed: 26 frames per orientation, 0 errors, 0 console errors, and the served entry hash matched the file on disk.
- Review only: no tracked file, entry or git state was changed.

Key: P = Heimdall "Glow Echo" (synth-heimdall), Q = Sunshine "Afterglow Roll" (synth-sol), R = Vandor "Straight Roll" (synth-vandor), S = Navi "Bead & Beam" (synth-navi).

## 1. Ranking

Scores are out of 10, from three blind lenses: Daniel's eye, rhythm-game craft and practice legibility.

| Rank | Entry | Daniel's eye | Craft | Practice | Mean |
|---|---|---|---|---|---|
| 1 | **Straight Roll** (Vandor, R) | 8.1 | 8.4 | 8.3 | **8.27** |
| 2 | **Bead & Beam** (Navi, S) | 5.9 | 6.3 | 6.1 | **6.10** |
| 3 | **Glow Echo** (Heimdall, P) | 5.2 | 5.8 | 6.4 | **5.80** |
| 4 | **Afterglow Roll** (Sunshine, Q) | 0.8 | 1.2 | 1.2 | **1.07** |

- Every judge put Straight Roll first and Afterglow Roll last. Straight Roll leads by 2.17 points.
- Judges split on 2nd and 3rd. Daniel's eye and craft ranked Bead & Beam over Glow Echo. Practice ranked Glow Echo over Bead & Beam, 6.4 to 6.1: it never washes out, it separates dense repeats better (14 vs 12 of 16) and it adds no marks you can't decode.

## 2. Heat 1 to final

| Entry | Heat-1 mean | Final mean | Delta | Daniel's eye | Craft | Practice |
|---|---|---|---|---|---|---|
| Straight Roll | 7.83 | 8.27 | **+0.44** | 8.0 -> 8.1 (+0.1) | 7.5 -> 8.4 (+0.9) | 8.0 -> 8.3 (+0.3) |
| Bead & Beam | 5.50 | 6.10 | **+0.60** | 5.0 -> 5.9 (+0.9) | 6.0 -> 6.3 (+0.3) | 5.5 -> 6.1 (+0.6) |
| Glow Echo | 5.00 | 5.80 | **+0.80** | 4.5 -> 5.2 (+0.7) | 5.5 -> 5.8 (+0.3) | 5.0 -> 6.4 (+1.4) |
| Afterglow Roll | not entered | 1.07 | new | - | - | - |

- The order among the three returning entries is unchanged, and all three improved.
- The heat-1 lens scores come from the `judges` dict in `bakeoff-heat1/make_heat1_sheet.py`. I assumed its lens order matches heat 1's stated order (Daniel's eye, craft, practice); the per-lens means reproduce the published heat-1 means.
- Treat the deltas as indicative:
  - The two heats were scored in separate judging passes.
  - In heat 1, Straight Roll was rendered on its own phrase and run fixtures. Only this heat puts it frame-for-frame on the shared fixtures.

## 3. Measurements (de-anonymised)

One measurement burst per entry, all on the same measurement look and fixtures. Every burst ended done, with 0 errors.
- Probes ran at Studio 1080x1920; frame times at Ultra 1440x2560.
- "a -> b" means heat 1 -> final. n/m means not measurable, because the pixels the check reads never lit.
- Source data: `bakeoff-final/measure-summary.md`, `measure-table-blind.md`, `analysis/final-metrics.json`.

| Check | Straight Roll (R) | Bead & Beam (S) | Glow Echo (P) | Afterglow Roll (Q), as shipped |
|---|---|---|---|---|
| Bar px lit in the isolated render (max) | 181,893 | 120,067 | 118,676 | **0** |
| Rise speed, u/s (declared) | 6.46-6.54 (6.5) | 5.56-5.64 (5.6) | 5.95-6.05 (6.0) | n/m (6.5) |
| Six Eb4, separate bars: dry / pedal down | 6 / **6** (heat 1: 6) | 6 / 1 (heat 1: 1) | 6 / 1 (heat 1: 1) | n/m |
| 16 Eb4 at 8/s: dry / pedal down (new check) | **16 / 16** | 12 / 1 | 14 / 2 | n/m |
| Finger+pedal vs finger | 1.218 -> 1.215 | 1.000 -> **1.300** | 1.000 -> 1.280 | n/m (pedal() is a no-op) |
| Finger-held vs pedal tail, centre luma ratio | 10.1 | 18.2 | 17.8 | n/m |
| Washed-out lit px at strike, v112 / v127 | 0.8/0.3% -> 0/0.2% | 29.1/36.2% -> **59.8/83.2%** | 23.5/47.1% -> 0/0% | 0/0% (bars unlit) |
| Brightness vs velocity, r | 0.99 -> 0.97 | 0.97 -> 0.95 | -0.00 -> 0.96 | n/m |
| Soft halo, v38 at 0.1 s, px | 0 -> 1,937 | 50,046 -> 30,281 | 22,458 -> **0** | 0 |
| Hard/soft halo ratio at 0.1 s | 136,820/0 -> **73.6** | 2.00 -> 2.32 | 1.75 -> no glow | no glow |
| Held v112 halo at 0.6 / 1.5 s, px | 43,401 / 38,123 | 26,635 / 20,173 | 0 / 0 | 0 / 0 |
| Held ff chord (7 notes, v127) halo at 0.05 / 0.5 s, px | 644,991 / 442,828 | 292,228 / 169,328 | 24,237 / 0 | 0 / 0 |
| Hard cap px over threshold at 1.0 s | 0 | 253 -> 254 | 0 | 0 |
| Non-peak px over threshold, Studio / Ultra | 0 / 0 | 840 / 2,195 -> 0 / 0 | 0 / 0 | 0 / 0 |
| Extra dynamics cue vs velocity, r | peak-hold needle 0.99 | needle 0.12; loudness dot 0.91 | rising echo height 0.71 (area 0.89) | breathline value 0.76; 0 px on screen at 9:16 |
| Pedal lift: ended bottoms vs lift row, px / px lit between lanes | 0.51-0.68 / 1,140 (amber lift line) | -0.03-0.40 / 0 | -0.05-0.79 / 0 | n/m / 0 |
| 16:9 render, highest bar row of 1080 | **81-118** | 482-514 (heat 1: 692-726) | 487-506 | not detected |
| Ultra p95 ms: full stream (bars) / about 250 bars | 8.5 (536) / 8.2 | 8.7 (542) / 8.3 | 8.8 (547) / 8.7 | 8.5 (511) / 8.1 |
| Ultra p95 with the entry hidden, ms | 7.9 | 8.3 | 8.5 | 8.5 |
| Draw calls (triangles / points) | 10 (5,476 / 2,048) | 5 (3,586 / 0) | 3 (1,280 / 512) | 7 (69,600 / 0) |
| Host camera/renderer/scene writes; objects off default layer | 0; 0 of 11 | 0; 0 of 5 | 0; 0 of 3 | 0; 0 of 8 |

The hidden-entry baseline also rose 0.3-0.6 ms since heat 1, so most of the frame-time increase is machine drift. Frame time does not separate the entries.

### Two findings that matter for the port

1. **Afterglow Roll draws black.** Its five InstancedMesh materials set `vertexColors: true`, but the geometries have no `color` attribute, so the instance colour is multiplied by 0.
   - An in-memory counterfactual with `vertexColors = false` lit 50,556 bar px, mean saturation 0.97, 0% near-white.
   - Every score and table value above uses the entry as shipped.
   - I did not edit the entry. Dropping that flag is the likely one-line fix, and it is Sunshine's call.
2. **The host sends noteEnd before noteOn when a note repeats at the same t.**
   - That clears the "previous strike" that Glow Echo (BEAD_GAP), Bead & Beam and Afterglow Roll (REPEAT_GAP_S) use to open a bead gap, so their pedalled repeats merge.
   - Straight Roll keeps its slot after noteEnd, so it is the only entry with beads under the pedal.
   - The /piano port must keep that slot logic, or change the host order after checking every other scheme.

### Heat-1 defect re-check

**Straight Roll (Vandor)**

| Heat-1 defect | Status | Evidence |
|---|---|---|
| update() wrote to the host camera | fixed | 96 update calls: 0 camera, renderer or scene diffs. The positive control tripped, so the detector works. |
| Grid and glass floor on host-reserved layers | fixed | 11 of 11 objects on the default layer only. |
| Soft notes never glowed | partly | v38 halo 1,937 px at 0.1 s (was 0); gone by 0.3 s. |
| Held glow gone by 0.6 s | fixed (now overshoots) | Held v112: 43,401 px at 0.6 s, 38,123 at 1.5 s. The judges now flag the opposite: the glow lingers. |
| Rendered on its own fixtures | fixed | Rendered on the shared `?set=heat1` fixtures in this heat. |

**Bead & Beam (Navi)**

| Heat-1 defect | Status | Evidence |
|---|---|---|
| 16:9 band never applied | fixed | Bars now stop at rows 482-514 (were 692-726), inside the fade band. |
| Ghost layer zero height | fixed | Ghosts light up to 5,893 px, 0 over threshold. |
| Loudness ribbon crossed the top band | fixed | First lit row 678 at 9:16 and 496-501 at 16:9 (was row 0). |
| pedal() empty | partly | Finger+pedal is now 1.300. Pedalled repeats still merge (1 of 6, 1 of 16) because of the host event order. |
| Needle and ribbon over the bloom threshold | partly | Over-bloom fixed (0 px). The needle is now a sub-pixel hairline: 5-14 px per needle, height r 0.12. |
| Hard caps glow about 1 s | not fixed | 254 px over threshold at 1.0 s; 238 px at 1.5 s while held. |
| 50k px soft halo | partly | 30,281 px at 0.1 s, 0 by 0.6 s. |
| 29-36% washed strike | **worse** | 59.8% / 83.2%. The cap is relit at chroma x0.62, so it goes pale (desaturated) rather than pure white; near-white is 0%. |

**Glow Echo (Heimdall)**

| Heat-1 defect | Status | Evidence |
|---|---|---|
| Glow had no velocity term (r -0.00) | fixed, with a regression | r 0.958 now. But single strikes no longer bloom: halo 0 px at v112 and v38 (were 39,208 and 22,458). Only about v120+ crosses: v127 chord 24,237 px at 0.05 s, 0 by 0.3 s. |
| Echo never bloomed, at most 16 px | partly | Up to 1,847 px, height r 0.71, but still 0 px over threshold. |
| pedal() empty | partly | Finger+pedal 1.280; pedalled repeats still merge (1 of 6, 2 of 16). |
| Strike washout 23.5-47% | fixed | 0% / 0%. |

**Afterglow Roll (Sunshine)**

This entry was not in heat 1. Its own acceptance claims, as shipped and in the counterfactual (CF):

| Claim | As shipped | CF (vertexColors off) |
|---|---|---|
| 16 beads from 16 rapid strikes | not met: 0 lit runs | met dry (16/16); under the pedal, only dim seams |
| Finger-held, pedal-held and ended tell apart | not met: nothing lit | met, but the whole bar switches state, so the finger part of a pedalled note also turns hollow |
| No clip to white | trivially met | met |
| ff bloom decays within 500 ms | not met: no bloom | decays in time, but the key-edge ring blooms, not the cap |
| One shared release line on CC64 up | not met | ends align; nothing marks a line |
| p95 at most 16.7 ms at about 250 bars | **met** (8.1 ms) | met |
| Cap and bar size monotonic with velocity | not met: not visible | met (width 0.476-0.690 u) |
| Breathline follows the crescendo | partly (r 0.755; clamps at the top, ripples per note) | same; off screen at 9:16, through the title at 16:9 |

## 4. Consensus strengths and defects

Consensus means at least two of three judges raised it. Most points were raised by all three. Measurements are quoted where they back a point.

### Straight Roll (Vandor), 8.27

**Strengths**
- **Velocity bars with glowing peaks.** Per-note translucent columns stand at the keys, with a lit peak collar and a peak-hold needle (r 0.99). The run reads as a crescendo and decrescendo skyline at a glance, and all three judges call it the literal answer to Daniel's ask.
- **Glow scales with velocity.** The hard/soft ratio is 73.6, so a soft Db6/9 stays calm while hard Gbmaj13#11 caps blaze.
- **Beads survive the pedal:** 6/6 and 16/16. It is the only entry that does this.
- **Finger versus pedal is readable.** Solid neon cores turn into hollow tails at release, and finger+pedal is brighter (1.215).
- **The pedal-lift line** shows where the pedal came up. The practice judge called it the best pedal readout in the heat.
- **Contact moment** (Daniel's eye and craft): a key-edge spark and a keybed ripple ring, both scaled by velocity.
- **Material** (Daniel's eye and craft): neon tubes with rounded glowing caps, floor reflections under the keyboard, and saturated colour (washout 0% / 0.2%).
- **Uses the whole 16:9 frame:** bars reach rows 81-118.

**Defects**
- **The glow lingers and stacks** (all three). An ff chord is 645k px of halo at 0.05 s and still 443k at 0.5 s; a held v112 note keeps 38k px at 1.5 s. This is a milder form of Daniel's "bloom doesn't decay, it just stacks".
- **It crosses the notation band** (all three).
  - 16:9: tall ended bars and the amber lift line run edge to edge through the chord title, degree label and staff brace.
  - Portrait: bars rise through the degree label and the staff (visible on the final sheet at phrase t 4.10).
- **Velocity columns crowd dense runs** (all three). They are wider than one lane, stand in front of the keys and beads, and overlap into a picket at the keyline (run t 3.0).
- **Busiest entry** (all three): 10 draw calls, plus blue grid lines across the staff, the reflection and the amber pedal wash. It is still within budget at 8.2 ms p95.
- **Weaker pedal tails** (practice judge only, backed by measurement). Tail contrast is 10.1 against 17.8-18.2 for the others, and the column outlines resemble hollow pedal tails.

### Bead & Beam (Navi), 6.10

**Strengths**
- **Lit gem cap on the bar tip and at every onset.** It delimits dry repeats (6 clean beads) and lights up along the run (brightness r 0.95).
- **Strongest finger/pedal contrast (18.2) and finger+pedal boost (1.30).**
- **Loudness-dot height tracks velocity** (r 0.91; Daniel's eye and practice).

**Defects**
- **The strike goes pale** (all three): 59.8% of lit px desaturated at v112 and 83.2% at v127, so hard caps look near-white. This breaks "colour is the note", and it is worse than heat 1.
- **The glow barely separates soft from hard** (all three): a v38 note already has a 30,281 px halo, and the ratio is only 2.32.
- **The extra dynamics cue can't be seen** (all three). It is a roughly 10 px hairline meter at the far left edge, and needle height r is 0.12.
- **Pedalled repeats merge** (all three): 1 of 6 and 1 of 16.
- **Landscape stops halfway** (all three): bars end at rows 482-514, leaving the upper half empty.
- **Hard caps stay over threshold at 1.0-1.5 s** (measurement only).
- **Split view:** the horizontal ribbing on bar heads. Daniel's eye and craft liked it if kept low-contrast; practice found it undecodable.

### Glow Echo (Heimdall), 5.80

**Strengths**
- **Best colour discipline** (all three): 0% washout at every velocity, and bars match their keys exactly.
- **Cleanest hollow-outline pedal tails** (contrast 17.8) and finger+pedal 1.28.
- **Tidy, square dry beads; rise speed exact; a calm, low-cost build** (3 draw calls). It never gets in the way of the notation.

**Defects**
- **No peak glow on single notes** (all three): halo 0 px soft, hard and held. Only an ff chord flashes (24k px at 0.05 s). It misses Daniel's newest ask directly.
- **The rising echo is a faint dot** (all three): height r 0.71, not noticeable at phone size.
- **Pedalled repeats merge** (all three): 1 of 6 and 2 of 16.
- **Landscape stops halfway** (all three): rows 487-506.
- **Flat, matte material with a weak contact moment** (Daniel's eye and craft): "a decent start rather than something incredible."

### Afterglow Roll (Sunshine), 1.07

**Strengths**
- **Within the frame budget** (8.1 ms p95 at 274 bars) with no host writes.
- **The phrase loudness-line idea is sound** (value r 0.76).

**Defects**
- **Bars, beads and strike rings render near-black** (all three; root cause in section 3). No note-level grammar can be judged, and the only colour on screen is the host's lit keys.
- **No peak glow anywhere** (0 px).
- **The breathline doesn't reach the page as intended** (all three). It is off screen at 9:16. At 16:9 it is a thin yellow-green line up the far left edge that runs through the title text, the "squiggly" look Daniel asked to move away from.
- **pedal() is a no-op,** so finger+pedal equals finger even in the counterfactual.

## 5. Graft list: the dedicated Synthesia mode in /piano, built on Straight Roll

**Base: keep from Straight Roll**
1. Straight bars from exact keys at a steady 6.5 u/s, one lane per key, with neon cores and rounded glowing caps.
2. The repeat slot logic that survives host noteEnd-before-noteOn. Acceptance: 6/6 and 16/16 beads with the pedal down.
3. The "velocity bars": per-note velocity columns with a glowing peak collar, plus the peak-hold needle (r 0.99).
4. The contact package: key-edge spark, keybed ripple ring sized by velocity, short light shaft, all in the noteOn frame.
5. The pedal-lift line and the faint pedal-down band.
6. The solid finger core and hollow pedal tail, with finger+pedal brightest.
7. Full-height travel in 16:9 and a subtle floor reflection.

**Fix on the base (consensus defects)**

8. **Decay envelope on every halo:** a flare on the strike, then a settle to a low simmer.
   - Proposed acceptance: ff-chord halo at 0.5 s at most about 20% of its 0.05 s value (now 69%).
   - Held v112 halo at 1.5 s at most about 25% of its 0.1 s peak (now about 88% of its 0.6 s value).
   - The hard/soft ratio stays large.
9. **Keep the notation band clear.**
   - Clip the lift line to the keyboard span, below the host's title and staff band.
   - Fade bars and columns out before that band, in both framings.
   - Remove the grid lines that cross the staff.
10. **Tidy the velocity columns.** Narrow them to exactly one lane, draw them behind keys and beads, and cap their opacity in dense runs.
11. **Separate the pedal cues.**
    - Raise pedal-tail contrast from 10.1 toward Glow Echo and Bead & Beam (17.8-18.2).
    - Give column outlines a treatment that can't be mistaken for a hollow pedal tail.
12. **Recheck the draw-call budget** (10) after the grafts, at Ultra with about 250 bars (now 8.2 ms p95).

**From the runners-up**

13. *Bead & Beam:* a note-tinted gem cap on the bar tip while the key is held and at each onset, clamped to the note's chroma so it never goes pale. All three judges named it.
14. *Bead & Beam:* a finger+pedal boost of about 1.3 (Straight Roll is at 1.215).
15. *Glow Echo:* the colour clamp as a rule for every glowing layer (0% washout at v112/v127) and its calm soft end. All three judges named it.
16. *Glow Echo:* the thin outline pedal tail and crisp ended-bar bottoms on the lift row, as the reference for item 11.
17. *Optional, Daniel decides live:*
    - Bead & Beam's ribbed VU-tick cap texture, low-contrast only.
    - Afterglow Roll's phrase loudness ribbon, rebuilt as a banded pp-to-ff strip beside the roll and outside the title band.
18. **Port note:** the /piano host keeps the scheme contract (noteOn / noteRelease / noteEnd / pedal / update / resize / setActive / dispose). Straight Roll's slot logic depends on the current event order, so change host order only with every scheme re-checked.

## 6. Caveats

- **Conflict of interest.** Vandor conducted this bake-off, maintains the host and harness, assembled these results and also entered Straight Roll (the winner).
  - What protected the scoring:
    - The judges saw only the labels P/Q/R/S and the blind measurement table.
    - All three reported opening no JSON, entry notes, scheme sources or git history. Daniel's-eye judge also opened no earlier-heat outputs.
  - Limits of that blindness: a reader who saw heat 1 could still recognise house styles, since heat 1's graft list described Straight Roll's velocity columns and lift lines.
  - **The final pick is Daniel's, live in /piano, where every entry is now in the Scheme menu.**
- **Identity leak, found and closed.**
  - All four renderers found the same leak: `harness/sheet_heat1.py` line 49 printed the entry file name and hash (for example "synth-vandor.js abe98502...") in line 2 of every `sheet-heat1.jpg` header.
  - The sheets were rebuilt in place at 14:50 with `harness/sheet_blind.py`. I checked all eight headers, and each now reads "blind sheet: entry identity withheld for judging".
  - The rendered frames never named an entry.
  - The practice judge's crops are timestamped 15:00, after the rebuild. The other two judges left no timestamped files, so I can't prove from the files that they only saw rebuilt sheets.
  - Frame JSON, burst.json, run-log.jsonl and the server logs still name each entry; judges reported not opening them.
- **Afterglow Roll was judged as shipped,** with black bars from a likely one-line material bug. Its counterfactual pass meets several of its own claims, so its score reflects the bug more than the design. Unless Sunshine fixes the flag, Daniel will also see black bars when he plays it live.
- **Pedalled-repeat results come from measurement, not frames.** The frame fixtures' repeat strip is dry, so the merge results for Bead & Beam and Glow Echo come from the measurement burst.
- **Heat-1 deltas are indicative only:** separate judging passes, and Straight Roll was on its own fixtures in heat 1. Frame-time changes are mostly machine drift.
- **Scope of the evidence:** synthetic fixtures only, headless Chrome on the real RX 9070 XT (ANGLE D3D11), GPU lock taken and released for every burst.

## 7. Conductor's addendum (Vandor): the blindness proof for all three judges

The workflow journal records each agent's start. At 18:50:29 UTC, the second the eight blind sheets finished rebuilding, it held zero `judge` starts, both before and after the rebuild. All three judges therefore started after the headers stopped naming entries, which closes the gap noted in section 6 for Daniel's-eye and craft.

Straight Roll is the conductor's own entry. The judges' 8.27 is evidence, not the decision: Daniel picks live in /piano.
