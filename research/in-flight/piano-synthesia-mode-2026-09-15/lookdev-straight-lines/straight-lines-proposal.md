# Straight lines, beefed up: proposal for Vandor

2026-09-15. Prototype only: every look is a runtime override script, and no tracked or product file was edited. `L2` = `C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/lookdev2`. Side-by-side sheet: `L2/choices-straight-portrait.jpg`.

## 1. What makes the original easy to read (never lose these)

1. **One straight lane per key.** You can drop a plumb line from any light to the key that made it. Nothing squiggles, so a chord reads as a bar chart of the hand.
2. **One colour per note, everywhere.** Key, light, letter and notehead share the OKLCH pitch hue, so no legend is needed.
3. **The column is the note's life.** It has a bright attack, then it sags, then it lets go, so history has a time axis.
4. **It is light, not UI.** It glows on a dark stage, and old light dims instead of stacking.

What it lacks: body, velocity (soft and hard p99 are .836 vs .837), finger vs pedal, contact at the key, depth, and words at the onset. Every look below had to add these without breaking rules 1-4.

## 2. Ranking (three blind judges: wow, rhythm-game, pianist-learning)

| Rank | Look | Judge scores | Mean | One line |
|---|---|---|---|---|
| 1 | **W - A: Classic, Beefed Up** | 7.5 / 8.0 / 7.4 | **7.63** | Second for every judge. The most faithful to the original and the clearest state grammar. It inherits the wrong name (Bbm11/Gb), the stage is static, and bars run into the type. |
| 2 | **X - B: Neon Highway** | 8.0 / 8.3 / 5.9 | 7.40 | The only real wow: the hit flashes, the amber lift line, the correct name. The rake squeezes history into a tangle, and hard bloom bleeds between lanes. |
| 3 | **Z - D: Poster Roll** | 6.0 / 6.6 / 8.4 | 7.00 | Best for teaching (formula line, role colour, stamps), but flat on pure black (median luma .004). It also tints idle keys, which is a bug. |
| 4 | **Y - C: Roll on Moonwater** | 6.5 / 6.2 / 6.4 | 6.37 | Beautiful, but the lake muddies saturation, the water reflection wobbles (squiggles again), and the hero drops out. |
| - | Classic / Upright baselines | 5.0-4.0 / 4.0-4.8 | - | Every look beats both. |

X and W tie on rank sum (6 each). W takes first because no judge put it below second, and it is the look Daniel actually asked for. All three judges independently named the same build: **W's lanes carrying X's contact and lift line, plus Z's words and role toggle.**

## 3. Build target for piano/roll.js: "Straight Roll"

- **Base:** W's glass tubes, finger core, hollow pedal rim and still glass floor.
- **From X:** the velocity attack (flash, streak, ring, sparks), the amber lift line, slow beat lines, and the chordread hero.
- **From Z:** formula line, Nashville chips, stamps on dark plates, role toggle, single onset base.
- **From Y:** history fade with height, note-lit mist, minimum rim pixel widths.
- **Fixes to W:** fade the roll before the meaning band; one label per chord; tint only sounding keys; velocity visible at rest through chroma, not white.

| Parameter | Target | From |
|---|---|---|
| Lane | x = keyX(m), straight up; lean 0.10 rad (Luminous), 0 (Poster), ≤0.17 (Spectacle) | original / judges cap 8-10° |
| Plane, base | z -3.0; one base -0.10 for every bar, depth-occluded by its key, so onsets form one row with no foot pop | Z (replaces W's 0.56 lift) |
| Width | white 0.84, black 0.50 u; rim ≥ max(0.07 u, 2.4 px); black outline ≥ max(0.05 u, 1.6 px) | W + C |
| Speed | 6.5 u/s, calibrated once per framing to 180 px/s at the 36-key lens; never changed per frame | original / reconciliation |
| Body light | OKLab relight: L 0.48+0.30·v^0.8, chroma ×(1+0.40v), hue kept; glass diffuse 0.60+0.40·(0.85nz−0.30u), spec stripe 0.42 | X + W |
| State | finger+pedal ×1.22 (brightest); pedal-only hollow rim 1.05, fill α 0.24; ended dim 0.62 | W |
| Attack head | length W·(0.45+2.1v); flash v^1.35·2.2·e^(−age/0.16) | W |
| Contact flash | R 0.45+1.15v; streak 1.2+6.5v; duration 0.14+0.26v | X |
| Ring, sparks | ring R 0.25+age·(4+9v), 0.30+0.25v s; sparks round(3+36v²) | X |
| Mist | head gain 0.020+0.070v (τ 0.8 s); foot pool 0.020+0.060v (τ 0.40 s) | C |
| Key | tint only while sounding; strike 0.3·v^1.2·e^(−age/0.14) | W (fixes Z) |
| Beads | gap only when the note is struck again (new aEnd attribute), ≥ max(0.16 u, 5 px); length stays exact | X / C |
| Pedal lift | amber line, half-width 0.06 u ×1.1, glow 0.22·e^(−d/0.45); warm lane guides while held | X |
| History | desat 0.45, floor 0.30, afterglow 3.5 s; 9:16 fade uv 0.665-0.77 | C / W |
| Motion | beat lines every 2 s ×0.12 (cool); lane glow 0.85·e^(−s/1.1); no fine grid | X, calmed |
| Stage | navy gradient (W values); frame median ≥ .05; still glass reflection 0.28·e^(−y/5.5) | W |
| Bloom | threshold 0.88, strength 0.80, radius 0.20 | X / C |
| Blend | premultiplied: body occludes; halo emissive at α 0; white pass, then black pass | C / X |
| Words | chordread.js createReader; 60 ms groups; ≥3 pitch classes; 1.2 s pedal aggregate; stamps on dark pills ≥ 30 px | Z / X |
| Colour | page noteColor; `uRole` mix(aNote, aRole); a held bar keeps its colour | Z |

## 4. Three skins on one straight grammar

Lanes, colour, state, beads, lift line, onset rows and contact timing are **shared truth**. A skin only swaps the fragment chunk, the backdrop and the gains.

| | Luminous (P) | Poster (R) | Spectacle (S) |
|---|---|---|---|
| Bar | glass tube + bloom | flat ink, 2.2 px keyline, sparse hatch on pedal tails | pearl/silk tube, hotter filament |
| Lean | 0.10 rad | 0 | ≤0.17 rad + beat lines |
| Contact | flash + sparks + mist | cap tab + flash (no bloom) | full X package |
| Backdrop | navy + glass floor (lake optional, still water) | near-black gradient at median .05 (not pure black) | lake silhouette + haze |
| Words | softened R lettering | big type, formula line, chips | raised extensions; opt-in rare moment |

**Flag:** the reconciliation puts the lake behind Luminous. The judges found the lake dulls saturation and its ripple reintroduces squiggles. I propose making the lake opt-in, with still water.

## 5. Geometry, shaders, cost (250 bars, 1440p60 portrait)

- **Geometry:**
  - Share piano.js's 768-slot trail geometry and uPedalHist by reference; the only new attributes are `aEnd` and `aRole`.
  - Placement lives entirely in the vertex shader (bottom, hold and top all come from the clock), so there is zero CPU work per bar.
  - Uploads happen on note events only, via `addUpdateRange`.
- **Fragment:**
  - rounded-box SDF with fwidth anti-aliasing;
  - one pedal-texture fetch;
  - fake cylinder normal;
  - cap and flash;
  - hollow-rim branch.
  - The halo is emitted at α 0 in the same pass, which avoids W's separate glow quad that was 4.4× bar width.
- **Draws:** backdrop 1, floor 1, mirror 1 (body only, clipped to the 84-100% band), bars 2, flash+ring 2, sparks 1, label atlas 1, hero 1. That makes about 10, replacing the page's 2.

| Pass | Shaded fragments (est.) |
|---|---|
| Bars incl. in-pass halo (pad ≤0.3 W) | ~5 M |
| Floor (lanes, beats, lift, 1 texture fetch) | ~1.9 M |
| Mirror, body only | ≤1.5 M |
| Flash, ring, sparks (typical) | ~0.5 M |
| **Total** | **~9-10 M** (W as built: 20-25 M) |

- **CPU per frame:** uniform writes, a 1024-texel lane texture, ≤12 label projections, and the sounding-key loop; skip `trails.scan` when the roll is active.
- **Unmeasured.** Every number is an estimate. The page already runs 48-54 fps at 1440p before any roll, so acceptance stays a timed p95 ≤ 16.7 ms with 250 bars, not this table.

## 6. Frames for the side-by-side (portrait, same fixtures)

Quiet Db6/9 = `db69-v38` (t 1.60 s). Hard Gbmaj13#11 = `gbmaj13s11-v112` (t 1.60 s). Phrase frame 6 = `phrase-m6-v112` (t 5.42 s, m6 of m0-m7).

| Column | Directory (append `<frame>.jpg`) | Look sha |
|---|---|---|
| Original classic | `L2/baseline/classic/portrait/` | - |
| Upright Roll | `L2/baseline/upright/portrait/` | upright-roll.js d78d2f11, look 6c842383 |
| W - A | `L2/looks/A/portrait/` | A.js 4d07739b |
| X - B | `L2/looks/B/portrait/` | B.js a93c743b |
| Y - C | `L2/looks/C/portrait/` | C.js daed691f |
| Z - D (note) | `L2/looks/D/frames/note/portrait/` (role: `.../role/portrait/`) | D.js 1a78c9d6 |

- **Served bytes, all 18 frames:** piano.html 838dead0, piano.js 84bc05c6, spectacle.js 89b9aa2a, moonwater.js 00e5f656, all equal to disk now; changed_since_load empty.
- **Duplicates:** the looks/ copies are byte-identical to the renders/ copies.
- **Receipt:** `L2/tools/straight-sheet-receipt.json`.
- **Caveat:** X's hero came from a fetched chordread.js (1d7bf628) that another seat has since changed on disk (236917be).
