# Void Star: Daniel's favourite frame as a VJ scene, built and judged (2026-10-24)

Workflow run wf_efc8de18-20b (task wsb3to6ey): one builder in a worktree with render-and-compare rounds, then a judge side by side with Daniel's frames (his frames are other people's footage and stay in local scratch, never in this repo). Verbatim; local scratch paths shortened to <scratch>. Branch worktree-wf_efc8de18-20b-1 (ceaaabce); not merged yet (registration, Look v2 and the judge's list first).

Vandor's read: the judge's core point is that the "holey carp" look needs huge soft beams glowing in haze with blinding white roots. That is volumetric light, which belongs to Look v2's haze and to the Virtual Stage lane, not to more 2D wedges.

---

## The build (verbatim)

Void Star is built and committed on the lane branch. The real `vj.html` page runs it with no errors, and the licence line is clean on the file. All checks ran on SwiftShader only, so it has not been seen on the GPU, the OLED or in HDR.

- **Branch:** `worktree-wf_efc8de18-20b-1`
- **Commit:** `ceaaabce9cb7799c7894e022b38a95e7fabf568f`. Not pushed, master untouched.
- **Files:** the new `arsenal/web/presets/vj-void-star.frag`, one `DEFAULT_SETS` id in `vj.js` (appended last), one blurb in `vj-show.js`. The pre-commit hook also regenerated and committed a one-line change to `docs/PHYSICS.md`.
- **Final contact sheet:** `<scratch>\lookv2\voidstar\contact-sheet-final.png` (1920x1080 frames, each beside the ref it answers). The real-page frames are in `...\voidstar\page-final\montage.png`.

**What the scene is.** All the geometry is ours; no logos, masks or stage replicas.
- **The cage:** two interlocked tetrahedra inside the cube of their tips, a counter-rotating octahedron, two gyroscope hoops and a halo ring with mandala dots. It is projected analytically, with no ray march.
- **The beams:** a mirrored V of translucent sheet beams from the cage, plus thin strong line beams.
- **The chandelier:** a lantern of our design that hides the beams behind it.
- **Ornaments and accents:** spiky suns, starbursts, and two cross-beam banks that slice diagonally on accents.
- **Palette (k8):** Void (the default), Ring, Temple (with sparkler fountains), and House, which follows the page's palette faders.
- **Music:** a "drive" level is stored in the feedback buffer's alpha, the house convention.
  - The first kick after a break opens the V within half a beat.
  - The top of the drive lowers the chandelier with every light on, and settles the tumbling cage face-on into its hexagram.
  - The kick swells and heats the cage and steps the sheets; the bass widens the fans.
  - Quiet is the cage alone, barely lit.
- **Output:** standard display output under strip v1 and in Play; scene-linear HDR only under strip v2 with a float target. Quality is on k7.

**Tests:**
- `node tests/vj_show.test.mjs`: 18/18
- `node tests/vj_core.test.mjs`: 153/153
- pytest (presets, coupling, keylab_vj): 62 passed, 1 skipped
- `parse_preset` reports no problems; the coupling check says "driven"
- Licence line, run on the file alone: CLEAN, 0 breaches, 0 exempt. A whole-tree run shows 0 findings in my file, but many breaches already in `vj.js` (lines 110-287, its shader strings, which I didn't touch).

**Metrics per round.** pal = palette distance, hue = hue distance, NB = near-black share, TB = true black share. Rounds 1-4 were 1280x720; 5 and final were 1920x1080.

| Round | Groove pal / hue | Drop pal / hue | Ring groove pal / hue | Temple groove pal / hue |
|---|---|---|---|---|
| 1 | 3.3 / 0.26 | 3.9 / 0.09 | 6.1 / 0.87 | 5.8 / 0.86 |
| 2 | 4.6 / 0.33 | 4.1 / 0.24 | 5.8 / 0.95 | 4.3 / 0.04 |
| 3 | 4.4 / 0.22 | 4.7 / 0.11 | 6.0 / 0.90 | 4.2 / 0.04 |
| 4 | 4.6 / 0.16 | 3.2 / 0.11 | 5.7 / 0.69 | 4.4 / 0.04 |
| 5 | 4.3 / 0.17 | 3.0 / 0.10 | 5.8 / 0.71 | 4.3 / 0.04 |
| final | 5.0 / 0.21 | 3.0 / 0.11 | 6.4 / 0.71 | 4.3 / 0.04 |

The groove palette distance got worse (5.0 against 4.3 in round 5) because the final round tightened the cage's glow to save cost. I kept that trade.

Final frames against ref-14, which measures NB 0.645, TB 0.02, lit 3.0%, highlight 0.07%:

| Moment | NB | TB | Lit | White-hot | Highlight |
|---|---|---|---|---|---|
| Quiet | 0.976 | 0.963 | 0.3% | — | — |
| Groove | 0.70 | 0.54 | 4.1% | 0.14% | 0.47% |
| Kick +50 ms | — | — | — | 0.16% | — |
| Drop | 0.58 | 0.375 | 7.9% | 0.22% | — |
| Pad | — | 0.49 | 7.0% | — | — |

- The kick's white-hot share (0.16%) is just under the brief's 0.2% floor; it was 0.20% in round 4.
- Temple keeps NB 0.39 where ref-12 has 0.01, because the brief makes darkness the default.

**Cost.** I estimate about 1-2 ms at 1080p on an RX 6600-class card from the code (about 700 operations a pixel, every loop bound constant). That is not measured. On SwiftShader at 1080p (best of 7 frames, a CPU ranking only) it is about 1.6 times the Laser Cathedral:

| Scene | Groove | Pad | Quiet |
|---|---|---|---|
| Void Star | 281 ms | 261 ms | 251 ms |
| Laser Cathedral | 177 ms | 168 ms | 163 ms |

**What would make it closer:**
1. Volumetric sheets (smoky density, light spilling into the haze). Ours are flat 2D wedges.
2. A larger, properly lit 3D chandelier. Ours is a flat 2D lantern.
3. More depth layers: a lit ring frame round the cage, and foreground silhouettes.
4. Ring look: an offset neon ring and denser beam bundles. Its red still dominates (hue distance 0.71).
5. Temple: the roof fixtures fanning down, which aren't in our grammar.
6. A real check on the rig: 60 fps on the GPU, and HDR on the OLED once the look-v2 page and strip v2 land.

**Things you should know:**
- In the page check, today's page adds a brownish lift on each kick plus grain, which raises the black in every drop frame. That comes from the page itself (its per-hit centre lift), not from the scene; the brief's look v2 removes it.
- The header declares pad 2 native for a future page that reads `accents.native`.
- The commit hook left unstaged edits in the worktree: line-ending-only changes in `docs/MODULE_INDEX.md`, `PORTS.md` and `PRIOR_ART.md`, and one appended line in `state/authorship/seats.jsonl`. I didn't commit or revert them.
- The reference frames and all my tools (harness, metrics, sheets) stay in `...\scratchpad\lookv2\voidstar\`.

---

## The judge (verbatim)

**Verdict: Void Star is a good scene, and it does not yet get the "holey carp" reaction.** It scores 7/10 on the headline bar and 6.5/10 for likeness to ref-14. Daniel would recognise his frame at once and probably like it, most of all the cage alone in silence and the drop where the chandelier comes down. He would not be floored by it. What made the photo hit was huge soft beams glowing in haze with blinding white roots, and a big chandelier full of white lights. Here the beams are flat, hard-edged wedges with bright outlines, and in the groove the chandelier is a dim wire bowl cut off by the top edge. On today's page it looks weaker still: true black drops to 0.1%, nothing reaches white-hot, and pads 1–2 draw the page's orange rings and teal lasers over the scene.

All renders are my own: 1080p, headless SwiftShader only, under the house GPU lock, one Chrome at a time, test-band ports 8971/8972/8976. I ran a continuous 150 BPM show (silence, break, groove, build, drop, anti-climax) on a 60 fps virtual clock. The strip is written the way `vj.js buildStrip()` writes it (v1, plus the brief's v2), and the drive builds up from the music rather than being injected. Ritual Fire (acc9437c) and Hyperspace (master) ran through the same harness at the same moments. I made no repo writes and no commits; the builder's branch has not been pushed.

**Scores**
- **Headline bar, 7/10.** The scorecard passes 27/30 on strip v1 and 26/30 on strip v2. Ritual Fire scored 30/30 and Guardian 28/30 under the earlier judge.
  - Passes:
    - one centred hero (light centroid x 49.8–50.4%, y 46–48%);
    - quiet: 97% true black, 0.3% lit;
    - groove: 50% true black, floor (p5) 0;
    - white-hot share in range: 0.33% in the groove, 0.43% on the kick;
    - every beam has a visible source;
    - the kick moves the world: the cage swells 4.5% and the sheets step to new angles;
    - pads stay in the scene's world: +0.013 mean luminance, 47% black kept;
    - colour: 2 families in Void and Temple.
  - Fails:
    - anti-climax: 58–60% true black (needs ≥70%) and 2 colour families (needs 1);
    - drop's first beat: only 6.2% lit on v1 and 7.8% on v2 (needs 15–45%);
    - groove without the chord-change cross beams: 4.0% lit (needs ≥5%);
    - mirror symmetry: 5.6–6.5% of pixels differ left to right in the groove, because the cage tumbles (needs <3%).
- **Likeness to ref-14, 6.5/10.**

  | Part | Score | Why |
  |---|---|---|
  | Composition | 8 | Very close: cage centre, V up to a chandelier, suns either side, starbursts |
  | Black | 8 | |
  | Cage | 7 | Crisp and white-hot, with a magenta heart. It tumbles in the groove and only settles into the hexagram at the drop, with two unequal triangles |
  | Sheet beams | 5 | Violet and cyan-white are right, but they read as vector graphics rather than light in haze |
  | Chandelier | 4 / 6 | 4 in the groove, 6 at the drop |
  | Colour | 7 | |

- **Ring beside ref-13, 5/10.** The ring sits centred around the cage and the beams fan in a symmetric V. Ref-13 has the ring off-centre and beams slicing diagonally one way.
- **Temple beside ref-12, 5/10.** The single orange family, the haze and the sparkler fountains read well. There are no roof fans, and true black is only 5%.
- **Against the others, same harness:**
  - Ritual Fire: 86–87% black, perfectly symmetric, the v2 anti-climax goes 88% black, the v2 drop's first beat is 15.7% lit.
  - Hyperspace: 0% true black, 28–55% left-right difference, the bottom of the frame lit, and the known seam is visible.

  Void Star answers Daniel's frame better; Ritual Fire is the stronger headline scene on the bar.

**Checks**
- **Originality:** clean. There are no Q-dance or Qlimax logos, emblems, masks or text. The cage (two interlocked tetrahedra, a cube, an octahedron, hoops), the lantern chandelier and the flower-like suns are our own drawings. The layout echoes ref-14 on purpose, as asked. The one borrowed motif is the gold star in each sun's centre, which is generic.
- **Licence line:** CLEAN on the file alone (0 breaches, 0 exempt).
- **Tests:** `vj_show` 18/18, `vj_core` 153/153, pytest 62 passed and 1 skipped. `parse_preset` reports no problems and the coupling check says "driven". `vj2_verify --phase sets` passes 13/13, but on SwiftShader it saw only 22 frames, so its flash measurement had little to go on.
- **No flashes of its own:** pass.
  - Traces at 1080p-equivalent stroke widths (960×540) show at most 4.9% of the frame brightening by 0.1 within 333 ms; the mean brightness rises by at most 0.015.
  - The worst 10° window reaches 21–22% on kicks and chord-change beams. It crosses 25% once (26.9%), at the drop's first beat on strip v2, and never repeats.
  - Saturated red changes by at most 0.55% of the frame per 333 ms.
- **HDR:** all values finite, hot cores 16–27. No pixel is ever exactly 0 (minimum 1.6e-6), which breaks the brief's "unlit = 0" rule; on screen it still rounds to black.
- **Cost:** about 1.8k operations a pixel by my count; the builder estimated 650–800.
  - That is roughly 1–2.5 ms at 1080p on an RX 6600-class card. On Daniel's 9070 XT at 4K it is about 1.5–3.7 ms: fine at 60–120 Hz, but heavy against a 240 Hz frame of 4.2 ms.
  - SwiftShader takes 356 ms a frame, 2.1× Laser Cathedral (builder said 1.6×). Ritual Fire takes 307–468 ms and Hyperspace 112–164 ms.
  - Quiet costs 94% of the groove, so the fixed work every pixel repeats dominates: 7 sin/cos pairs and 5 matrix products for the poses, plus about 25 texture reads. It still needs one real GPU timing and a first-frame compile check, with Daniel's OK.

**Must-fix**
1. **Sheets** (`vj-void-star.frag` around lines 1048–1057): drop or dim the bright outline on each sheet edge. Give each sheet a white-hot root at the cage that fades upward (today the top is still 59% of the root), plus a soft haze texture. The beam roots should be the brightest things in the frame.
2. **Chandelier:** make it a second hero. Bigger, a dark silhouette in front of the beams, blazing white lights, and partly visible in the groove instead of clipped at y 0.425.
3. **Drive frame rate:** make it frame-rate independent on strip v1, where `gDt` is fixed at 1/60. At Daniel's 240 Hz the drop pumps every beat (the drop amount swings 0.47→1.0), so the chandelier bobs about 144 px at 4K and the cage wobbles. A CPU twin and GPU runs agree on this. Also smooth the drop amount.
4. **Chapters on strip v1:** with the page's own demo music the drive sits at 0.45, so the chandelier never lowers; with louder auto-gained bands, an ordinary groove can look like the drop. The drop should come from contrast against a slow average, not absolute level, or Void Star should wait for strip v2. On v2 the drop holds steadily at 0.95.
5. **Anti-climax:** `gPres = max(drive, smoothstep(0.04,0.30,level))` lights the full cage, sheets and ornaments in any break at level 0.3 or more. Tie them to the drive (and the section on v2) to reach ≥70% black and 1 colour family.
6. **Cross-beam banks:** the emitters sit at y −0.40, in the bottom 20% and below the scene's own declared rig floor (−0.30). They also fire on every chord change, breaks included. Raise them and limit them to the groove and drop.
7. **Drop's first beat:** give it a gated, bigger moment to reach 15% lit or more.
8. **Ring look:** 4 colour families (red, orange suns, periwinkle beams, magenta hoop) against a limit of 2. Recolour the suns and the second hoop into the red family.
9. **Temple look:** 5% true black. Cut the haze and fountain glow back to near the beams, or have Daniel sign off on Temple as a flood-look exception.

**Should-fix**
- Mirror symmetry in the groove: 5.6–6.5% left-right difference (11–14% at the drop).
- Strokes under 1.5 px: cube bars 1.36 px (l.938), octahedron 1.45, hoops 1.4 (l.986), starburst spokes 1.2 (l.1253), chandelier tracery 1.2–1.3, fountain sparks 1.3.
- Trails fade per frame, not per second (l.1359); at 240 Hz they vanish.
- `pow(sin(PI*s),0.75)` (l.1218) can produce NaN, because `sin` goes slightly negative at s = 1. Clamp it to ≥ 0.
- HDR output should be exactly 0 where unlit.
- The header comment names Qlimax twice, quoting Daniel. Strip it if the brief's "no name anywhere" is meant literally.
- Registration conflicts with the other new scenes' one-line edits to `DEFAULT_SETS`.

**Builder's report, corrected**
- Kick white-hot is 0.43%, above the brief's 0.2% floor.
- Temple's true black is 5%. The builder's 0.39 is the looser "near-black" measure, not true black.
- The builder's injected groove drive of 0.47 is realistic; my show produced 0.55–0.60.

Files are in <scratch>\lookv2\voidstar\judge\:
- sheets\judge-vs-vs-ref14.png
- sheets\judge-vs-ring-temple.png
- sheets\judge-vs-rf-hs.png
- sheets\judge-vs-crops-1to1.png
- sheets\judge-vs-page-today.png
- crops\quick-vs-ref14.png
- out\vj-void-star\, out\vj-ritual-fire\, out\vj-hyperspace\ (frames)
- out\log.json
- analyse.txt
- scorecard.json
- traces.json
- drive_sim.py
- drive_sim.json
- vj2\vj2-judge\receipt.json
- lic-file.txt
- harness\ (vsj.html, vsj.mjs, plans.mjs)
