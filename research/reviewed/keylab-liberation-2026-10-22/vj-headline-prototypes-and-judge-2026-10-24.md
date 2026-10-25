# Headline Q-dance pass: three new scenes and the judge (2026-10-24)

Workflow run wf_82a5da4f-0f7 (task wvag23n2k), the Prototype and Judge phases; the studies and the brief are in vj-headline-qdance-brief-2026-10-24.md. Verbatim; local scratch paths shortened. Branches: Ritual Fire worktree-wf_82a5da4f-0f7-6 (acc9437c), Pyro Finale worktree-wf_82a5da4f-0f7-7 (1ed8a693), Guardian worktree-wf_82a5da4f-0f7-8 (da240222); not merged yet (registration, look v2 and the must-fix lists first).


---

## The judge (verbatim)

**Verdict: Ritual Fire is the one that would make Daniel say "headline" (8/10), Guardian is second with the highest ceiling (7/10), and Pyro Finale is not ready (5/10).** One plain caveat applies to all three: on today's page none of them looks headline. In the page receipt with look v1 on, each shows 0% true black, a black floor (p5) of 5–11 codes, 0% white-hot, and the generic pad shockwave and teal lasers drawn over the scene. They need the look-v2 page lane first.

## How I judged
- **Builders' moments:** I re-rendered every builder's moments with their own harnesses. My numbers match their reports within rounding.
- **Common harness:** I wrote my own harness, stateful like the page, writing strip v1 exactly as `vj.js buildStrip()` does plus the brief's strip v2. I ran it at 150 BPM with the same 25 moments for all three at 1080p, plus 60 fps traces, float-output probes and timings.
- **Setup:** headless Chrome on SwiftShader only, under the house GPU lock, ports 8941–8961. I wrote only under `judge/` and committed nothing.

## The bar, item by item (RF / Pyro / Guardian)
1. **One centred hero:**
   - Ritual Fire passes: it is centred 41–45% from the top, 0.0% left-right difference, and the bottom 20% stays unlit.
   - Pyro passes: the gate's eye sits 47% from the top. But its light sits high (light centroid 24–35% from the top).
   - Guardian partly passes: the mask is centred. But the halo's lower arc and the drop beams light the bottom 20% (99th-percentile luma there is 45 in the groove and 208 in the drop).
2. **True black:** all three pass.
   - Ritual Fire: 88% quiet, 87% groove.
   - Pyro: 86% quiet, 51% groove. But its float output is exactly zero on only 13% of the groove frame, because the smoke is a slow near-black haze.
   - Guardian: 91% quiet, 67% groove.
3. **Depth:**
   - Ritual Fire is weak: only the two ember layers' parallax and a dimmer far layer.
   - Pyro is strong: the black gate occludes lit pyro, and there is crane parallax.
   - Guardian is strong: the mask occludes the halo and beams, and the relief is shaded.
4. **Light has a source:**
   - Ritual Fire passes: the fire is the source, cores go white inside coloured halos, and the jets light the floor.
   - Pyro passes: the crown and comets come from hidden emitters.
   - Guardian partly passes: the beams come from behind the head, but the tube reflections read as painted white stripes.
5. **Colour:**
   - Ritual Fire passes: two families (orange and red) plus bone.
   - Pyro fails: 3 families on the kick frames and 4 on the drop without a flood.
   - Guardian passes: two families.
6. **Fidelity:**
   - Ritual Fire: strokes are 2–3 px with analytic edges and embers are round. But the flames look like smooth gel, with stray "antler" tongues and a blob touching the top edge at the drop.
   - Pyro: the bursts read as asterisks, and the CO2 reads as beige fog.
   - Guardian: the stripe highlights are hard-edged, and one crosses the right eye.
7. **Kick moves the world:**
   - Ritual Fire passes: ring +3.8%, the line clicks white, black floor +0.
   - Pyro passes: the crown aim steps and the spread springs +5°.
   - Guardian partly passes: eyes +60% and halo +4%, but its drop fan timing is derived from the beat count.
8. **Quiet state:**
   - Ritual Fire passes: 0.3% lit.
   - Pyro fails: 0.02% lit, below the 0.2% floor.
   - Guardian passes: 0.3% lit, eyes only.
9. **Pads:** all three stay within limits.
10. **Safety:** all three pass.
    - The 60 fps traces show no flashes of their own. Pyro's gated CO2 counts as exactly one flash.
    - Saturated red changes by at most 2.2% of the frame per 333 ms.
    - `vj2_verify --phase sets` passes 13/13 on each branch, with the look on.
11. **Chapters:**
    - Ritual Fire partly passes: its climax groove is only modestly brighter than the groove (7.2% lit against 5.4%).
    - Pyro and Guardian pass, with strongly distinct sections.

**Scorecard rows passed (`scorecard.json`):** Ritual Fire 30/30, Guardian 28/30, Pyro 25/30.
- Ritual Fire's groove lit share (5.4%) is only just above the 5% floor.
- Guardian fails on lit share in violet: 1.6% in the groove (target 5–25%) and 7.8% at the drop (target 15–45%). In green its groove reaches 6.9%.
- Pyro fails five rows:
  - quiet lit 0.02%;
  - groove lit 2.4%;
  - 3 colour families on the kick;
  - drop without a flood: 1.7% lit (by design, since the CO2 is its drop light);
  - drop without a flood: 4 colour families.

## Must-fix
**Ritual Fire**
1. Its header says `"grade":"two"`, so look v2's two-hue pull would recolour the fire. A green section already gives 3 families. Exempt the fire from the pull.
2. Break up the gel flames, and remove the stray tongues and the top-edge blob.
3. Make the climax read bigger than the groove.
4. Add a third depth cue.
5. Put an unroll barrier on the 6×24 pad-burst loop, or confirm the first frame compiles quickly on Daniel's Chrome.

**Guardian**
1. Raise the violet lit share to the scorecard range.
2. Keep the halo and beams out of the bottom 20%.
3. Make the material read as chrome: softer, curved reflections and a cavity term.
4. The drop fan's opening is timed from the beat count. On the page's count it is fully open on the first kick, so it should come from section progress or the first-kick-of-phrase signal instead.
5. Its light clock lives in the previous frame's alpha. The look-v2 lane must keep that alpha intact.

**Pyro Finale**
1. Its beat-in-bar uses `count % 4` with count taken as the beat index. The page writes count as beats fired, so it is off by one:
   - The last beat before the drop is lit: 84.5% true black against the spec's 95%.
   - The CO2 starts as if already 0.45 s in, so the frame jumps to 57.5% lit at +50 ms with no attack.
2. Lift quiet, groove and climax into range.
3. Hold two colour families.
4. Make the CO2 crisp white and keep the smoke local to the bursts.
5. Draw denser glittering shells instead of asterisks.
6. Cut the cost (see below), then take a real GPU timing with Daniel's OK before it enters a set.

**Shared**
- **Merge conflicts:** all three branches edit the same `DEFAULT_SETS` line in `vj.js`, the same spot in `vj-show.js`, and `docs/PHYSICS.md`. Leave registration to the Wave-2 page lane.
- **Strip v2 needs two fixes from the look-v2 lane:**
  - Texel 9.x is already used for the star count (`vj.js:1168`).
  - Strip v2 has no beat-in-phrase field, so all three scenes drift wherever the page's count is not aligned to bar 1.
- **`vj2_verify` gaps:** its new-set list is hard-coded (I patched it in a scratch copy), and its flash measurement starves on slow scenes. Ritual Fire and Pyro measured 0 flashes because they rendered only 18 and 7 frames while the gate granted 3.

## Tests, licence, cost
- **Tests, run on scratch exports of each branch:** all pass.
  - `node tests/vj_show.test.mjs`: 18/18.
  - `vj_core`: 153/153.
  - pytest on the preset, coupling and keylab VJ tests: 62 passed, 1 skipped.
  - `arsenal/presets.py` reports no problems for any of the three.
- **Licence line:** each new `.frag` scanned alone is CLEAN (exit 0). The full tree exits 1 on every branch, from the same 131 breaches already on master and none in the new files:
  - the 13 existing `vj-*.frag` files;
  - `vj.js` (10) and `vj-fx.js` (5);
  - `chordsense.py` (3);
  - `preset-gl.js` and `vj-core.js` (1 each).

  This blocks "licence-line exit 0" for every scene lane until the house clears it.
- **House kits:** current and verbatim against a fresh compose.
- **Float output:** finite and non-negative in all three; hot cores reach 6–22.
- **Cost, estimated from the code for an RX 6600-class card at 1080p (no GPU measurement):**

| Scene | Ops per pixel | Estimated GPU time | Budget | SwiftShader per 1080p frame |
|---|---|---|---|---|
| Ritual Fire | 0.8–1.0k | 0.5–1 ms | in budget | 460–500 ms |
| Guardian | 0.9–1.2k (mask pixels about 3.4k) | 0.6–1.2 ms | in budget | 148–174 ms |
| Pyro Finale | about 5–6.5k by my count (builder said 4–4.5k) | about 3–6 ms | 2–3× over | 1.75–2.56 s |

For scale, Laser Cathedral takes 203–225 ms per frame on SwiftShader, so Pyro is 8–11× that. On the page receipt Pyro ran at 1.9 fps.

Files are in `<session scratchpad>\headline\judge\`:
- `sheets\judge-all-moments.png` – all three at the same moments, beside Hyperspace, Laser Cathedral, Synthwave Grid and Geometry Hall
- `sheets\judge-rf-vs-refs.png` – Ritual Fire beside its references
- `sheets\judge-pf-vs-refs.png` – Pyro Finale beside its references
- `sheets\judge-gd-vs-refs.png` – Guardian beside its references
- `sheets\judge-crops-1to1.png` – 1:1 crops at 1080p
- `sheets\judge-today-page.png` – each scene alone against today's page
- `common\<scene>\J01…J25.png` – the common moments, with `metrics.json` beside them
- `common\judge-log.json` – traces, float probes and timings
- `scorecard.json` – the scorecard rows
- `repro\{rf,pyro,gd}\out\` – the builders' moments re-rendered
- `vj2\{rf,pyro,gd}\vj2-judge\receipt.json` – the page receipts

---

## Builder: Ritual Fire (vj-ritual-fire) (verbatim)

Ritual Fire is built and committed: `acc9437c` on branch `worktree-wf_82a5da4f-0f7-6`, not pushed and not on master. It meets every acceptance line in the spec except one I can't fix from this lane: the full-tree licence scan already fails on master, for reasons that aren't in this scene. Everything here was rendered on SwiftShader only; no GPU timing has been taken.

**Commit contents**
- The new scene: `arsenal/web/presets/vj-ritual-fire.frag`.
- `arsenal/web/vj.js`: one line, the new id added to `DEFAULT_SETS`. Nothing else in that file is touched.
- `arsenal/web/vj-show.js`: one blurb added.
- `docs/PHYSICS.md`: a one-line "derived at" stamp the repo's pre-commit hook regenerates and stages on every commit.

The hooks also left some unstaged changes in the worktree that are not in the commit. They are a new line in `state/authorship/seats.jsonl` and line-ending-only changes to three docs. I left them alone.

**Final contact sheet:** `<session scratchpad>\headline\proto-vj-ritual-fire\final\contact-sheet-final.png`. It shows the references, round 1 against the final scene, the pad moments, a screenshot of today's page and 1:1 crops at 1920x1080. The sheet for each round is in `r1` to `r9` and `final` under the same folder. The 1.5 s, 60 fps motion check is in `motion\filmstrip.png`.

**How it answers each reference**
- **Q19 and Q13 (quiet, anti-climax):** the sigil alone in a blood-red line, with a faint red glow escaping past the ring and a highlight that travels down both sides every 7 s. 88% of the frame is true black, one hue family. The anti-climax adds one pair of pilot flames.
- **Q23 (groove):** a 16-tongue fire wreath around the bone-line sigil, three bronze-framed fire panels a side, and embers rising. 87% true black, 6.1% lit, 0.44% white-hot, two families (orange and red).
- **Q09, Q04, Q02 (the drop):** all three mirrored jet pairs fire together for three beats (1.2 s at 150 BPM). The wreath goes molten and the panels flare. On the first frame of the drop: 73% black, 16.1% lit, 4.1% white-hot, and black still shows between the tongues in the 1:1 crop.
- **D10 (all-red hall):** turning k7 to 0 switches the fire to a red-and-gold palette (Defqon register).
- **Build:** the sigil line heats toward orange, pilot flames light, and the last beat before the drop is 99.9% black except the pilots.

**Other acceptance numbers**
- **Kick:** the inner ring goes from 262 to 272 px 50 ms after the kick (+3.8%). The black floor stays at 0.
- **Mirror:** left-right difference is 0.00% at quiet and in the groove with k8 = 0.
- **Saturated red:** it changes by at most 0.7% of the frame in any 333 ms.
- **Motion run:** no flash. Mean brightness rises by at most 0.07 (the flash test is 0.1), and at most 17% of the frame brightens that much (the limit is 25%).
- **HDR path:** finite and non-negative, with hot cores at 11–13.
- **Today's page:** the existing page receipt (sets phase) passes. It compiles, renders, advances frames, answers pads, and the flash gate held at 2 per second.
- **Checks:** `arsenal/presets.py` reports no problems, and `tests/vj_show.test.mjs` passes 18 of 18.

**Licence line.** The scene scanned on its own is CLEAN (exit 0). In the full tree this file has 0 breaches, but `py -m arsenal shader licence-line` still exits 1. That is because of 131 breaches that are already on master, in the 13 existing `vj-*.frag` files, `vj.js` (10), `vj-fx.js` (5), `vj-core.js`, `lib/preset-gl.js` and `keylab/chordsense.py`. Someone needs to clean those up, preferably after the impact pass lands since it is editing several of those files.

**Decisions to check**
- **Jet positions:** I placed them at ±0.20, ±0.36, ±0.52 frame heights from centre. Read as fractions of the frame width, the outer pair would sit off-screen.
- **k8 is labelled "asymmetry", not "symmetry":** 0 is the strict mirror the acceptance requires, and raising it breaks the mirror.
- **Ember tails are drawn, not fed back:** they trail below the head, and k5 sets the tail length in seconds. They never break into dots.
- **Pads 7–12 bursts are mirrored:** pad 9 also bursts at 3 o'clock while k8 is below 0.5.
- **Today's page can't tell sections:** with the current strip the scene plays the groove look, and the full volley fires every 32 beats of the beat tracker's count, which doesn't know where bar 1 falls.
- **Sigil and fire modules:** I did not create `draw2/sigil` or `light/fire` as module files, because the modules lane owns those and the index. The code sits in a block in the scene marked as candidates for them. The house modules it does use are composed into a marked house-kit block.
- **Conflict for the look-v2 lane:** today's page already writes the star count into the strip texel the brief assigns to `dt` in strip v2.
- **Today's page still lifts the black and draws its own pad 1/2 effects:** the black lift and the generic shockwave and laser show over this scene (see the page screenshot). Both are look-v2 lane work.

**Cost (estimate, RX 6600-class card at 1080p).** About 950 operations per pixel on average in the groove, 1,100 at the drop, and 1,400 while a pad burst is live. The wreath is the most expensive part, at about 170 on average. Idle jets cost one shared branch each, because whether a jet is firing is now decided once per frame rather than per pixel. That fix halved the base cost on SwiftShader. At roughly 4.5 billion operations per second and about 50% efficiency, that is about 0.9 ms in the groove, 1.0–1.3 ms at the drop and under 2 ms with bursts. A quality define (`RF_QUALITY` 2/1/0) drops to about 0.7 ms at level 1. All 8 knob slots were taken by the spec, so the quality setting is a define in the file rather than a knob. On SwiftShader it takes 300–480 ms per 1080p frame, comparable to Laser Cathedral's 354 ms. That number is noisy because another lane was rendering at the same time.

**Known gaps**
- **Embers:** I didn't count them in a frame (the blob counter picked up sigil fragments). By construction there is at most one per cell, so no more than 206, and heads are at least 1.52 px wide.
- **Dim-orange pixels:** my brown-mud probe flags only the bronze frames (the spec's colour), the faint halo of the bone lines (an effect of the display curve) and the ember halos, not the flame bodies.

**With more time I would:**
1. Hand the sigil and fire code to the modules lane as real modules, with test cards, and recompose the kit.
2. Give the molten wreath real wisps. It still reads slightly liquid at 1:1; a half-resolution flame buffer or curl-noise movement would help, plus a fireball on jet ignition.
3. Run the 150 BPM demo with section marks through the page once strip v2 exists, plus the scorecard receipt once that lane ships.
4. Time it on Daniel's card, only with his OK.
5. Watch longer motion runs for flicker; I only checked 1.5 s.

---

## Builder: Pyro Finale (vj-pyro-finale) (verbatim)

I built Pyro Finale and committed it on the worktree branch. It passes the spec's per-scene acceptance list except where noted below. Two problems: by my operation count it costs about twice the brief's GPU budget, and the tree-wide licence-line check still exits 1. My file has no breaches; the 131 failures are in other files and were already on master.

**Branch:** `worktree-wf_82a5da4f-0f7-7` (not master, not pushed)
**Commit:** `1ed8a693`. It adds `arsenal/web/presets/vj-pyro-finale.frag` (generated by `build_frag.py` in the proto folder), registers the scene in `DEFAULT_SETS` in `arsenal/web/vj.js` (three-line edit, nothing else in that file), and adds a blurb in `arsenal/web/vj-show.js`. The pre-commit hook also regenerated `docs/PHYSICS.md` into the commit. After the commit the house hooks left unstaged changes I did not touch: a line appended to `state/authorship/seats.jsonl`, and three docs files that show as modified (`MODULE_INDEX.md`, `PORTS.md`, `PRIOR_ART.md`), apparently only line endings.

**Final contact sheet (1920x1080, 29 moments):** `<session scratchpad>\headline\proto-vj-pyro-finale\final\contact-sheet.png`. Next to it are `refs-vs-final.png` (each reference beside the frame that answers it), `before-after.png` (round 1 against the final) and `metrics.json`. Each round's sheet is kept in `round1` … `round11`.

**How it answers each reference**
- **D05 (gold fan wall behind a totem):** a euphoric climax, or Daniel's colour fader on gold, gives a gold and warm-white volley fan behind the black gate.
- **D08 (pink fans, guard silhouettes):** the pink register, with peony arcs over the gate. The smoke is lit pink only near the bursts, and the swept blades read as the side silhouettes.
- **D11 (vast comet fan):** the drop's full volley of 12 comets a side climbs on long, glittering, continuous trails at angles from 80° down to 25°.
- **D01 (green and white volleys):** the colour fader on green gives a green register with white-hot heads.
- **Q12 and Q15 (CO2 white-out):** six jets fire on the drop's first beat. With the page's flood granted, the frame is 70% lit at +0.5 s; refused, 1.9% (the limit is 25%). Using the page's flash rule on a 60 fps trace, the granted drop counts as exactly one flash. The refused drop and 4 s of climax count none, and that holds at 960x540, 480x270 and 320x180.
- **Q16 (radial beams from behind the hero):** 8 to 16 beams open from 10° to 120° over the drop's first beat, from a source behind the eye. That light also leaks through the ring around a black pupil.
- **Q13 (red ring in the void):** the anti-climax is 90.5% true black, 0.2% lit and one colour family. Only a beaded red ring shows in the eye, with occasional slow ring shells.

**Acceptance against the spec**
- **Build:** lit share rises 0.6, 2.4, 3.5, 4.1% at each two-bar step, and the last beat is 100% black.
- **Climax groove:** 54% true black, 0.52% white-hot, two colour families.
- **Gate:** pixels stay at code 3 or below outside the rim.
- **Mirror:** the left-right difference is 0.00% with k8 at 0.
- **Under the floor:** at most code 27 below the floor line, and none of it is beam light.
- **Page receipt:** `vj2_verify --phase sets` passes, using a temporary copy that treats this scene as new; the copy was deleted, nothing committed.
- **Tests:** `presets.py` reports no problems, and `tests/vj_show.test.mjs` passes 18/18.
- **Shortfalls, both from the brief's generic scorecard:**
  - With the flood refused, the drop's first beat is 0.8% lit against the generic 15–45%. This is by design: the CO2 is the drop's light.
  - The climax groove is 4.7% lit, just under the generic 5%.

**Cost (estimated from operation counts; I did not measure on a GPU)**
- A climax groove with 10 comets a side (the default) is about 4,000–4,500 operations per pixel. On an RX 6600 that is roughly 3–3.5 ms, rising to about 4 ms at the drop. The brief's budget was 2,500 operations, under 1.5 ms typical and under 3 ms at the drop.
- On Daniel's RX 9070 XT that is about 1.2–1.6 ms.
- Most of the cost is testing every comet for whether it can reach the pixel, plus drawing the four stars nearest it in each burst.
- Bounds: every loop is capped (12 comets, 6 volleys, 4 stars per burst, at most 8 noise layers), there is no raymarching, and the long loops use the unroll barrier.
- **Quality knobs:** k1 (volley size) is the live one: about 6 comets a side brings it to roughly 3,100 operations, around 2.4 ms on the 6600. Play's eight knobs were all taken, so a `QUALITY` constant in the file also trims the stars and noise layers.
- In software rendering (SwiftShader, which evaluates every branch whether taken or not) it is about 8 times slower than the heaviest existing scene: 230–670 ms per frame at 960x540.

**Things you should know**
- The section behaviour (build, drop, anti-climax, outro, kick and flood inputs) reads the planned version 2 of the page's data strip, which no page writes yet. I verified it only in my own harness that fakes those values. On today's page it plays as a single groove section driven by the music's level and the colour fader.
- Pads 7–10 set the burst type of the next volley by comparing seconds to beats at an assumed 150 BPM, so at other tempos the window drifts.
- The comet and burst helpers live inside the scene file. I did not create `draw2/pyro.glsl`, because adding a library module means updating `index.json`, which belongs to the modules lane.
- `vj2_verify.mjs` has its list of new scenes hard-coded to the wave-2 sets. The page lane needs a way to pass new scenes in.

**With more time**
- Cut the per-comet test cost: one coarse bound per volley, or a window of comets chosen by the pixel's fan angle, to get near 2,500 operations.
- Make the pyro denser for the D05/D08 wall look. The reference sheet shows we are still sparser than the photos.
- Make willows droop more and give the smoke more structure.
- Have the page tell the scene its tempo, so pyro physics and pad timing use real seconds.
- Measure on the real GPU, with Daniel's OK.
- Clear the 131 existing licence-line breaches in the other VJ files once the impact pass has merged.

---

## Builder: Guardian (vj-guardian) (verbatim)

Guardian is built and committed: branch `worktree-wf_82a5da4f-0f7-8`, commit `da240222` (no push, no attribution trailer). It's a black-chrome guardian mask of our own design inside a 32-segment LED halo. Light travels across its still metal, and on the drop the eyes open, the halo completes and a fan of beams opens from behind the head. It meets all seven Guardian acceptance items on my own harness. Two headline scorecard rows fall short in the violet palette (below).

**Files**
- `arsenal/web/presets/vj-guardian.frag`: new. The house kit is composed by `py -m arsenal shader lib compose` and sits between markers, with its own hash header.
- `arsenal/web/vj.js`: one id added to `DEFAULT_SETS`, nothing else.
- `arsenal/web/vj-show.js`: the blurb. The page keeps `BLURBS` here, not in `vj.js`.
- The pre-commit hook also bumped one line in `docs/PHYSICS.md` and appended a line to `state/authorship/seats.jsonl`. The second is left uncommitted in the worktree.

**Final contact sheet:** `<session scratchpad>/headline/proto-vj-guardian/r5-final/sheet-r5-final.png`

The same folder holds:
- `compare-refs-vs-guardian.png`: each reference beside our frame;
- `crops-1to1.png`: 1:1 crops at 1080p;
- `rounds-progression.png`: groove and drop across the rounds;
- `r1/` to `r4/`: sheets from each of four rounds;
- `vj2/vj2-20261024-225810/`: the page receipt.

**Rounds**
1. First light: the composition worked, but the metal showed one flat white slab and the mask read as a horned cartoon.
2. A crown of seven fins, side helm plates, a forehead medallion with onion rings, and a mouth grille slotted like teeth.
3. Chrome-like reflections from a crisp overhead softbox. The anti-climax chrome is now unlit, beams got soft shafts, and the eye kick was raised.
4. Polish: brighter groove ring, light from below so the lower face reads, and reversed `smoothstep` calls fixed (GLSL leaves those undefined).
5. Final, after a cost early-out.

**Acceptance (1080p, my harness with a 150 BPM conductor writing strip v2)**

| # | Item | Result | Target |
|---|---|---|---|
| 1 | Quiet: true black | 87.6% | ≥ 85% |
| 1 | Anti-climax: true black | 96.2% | ≥ 85% |
| 1 | Lit, quiet / anti-climax | 0.46% / 0.28% | 0.2–2% |
| 1 | Eyes are the brightest pixels (share of the brightest 0.1% inside the eye boxes), quiet / anti-climax | 100% / 94% | eyes brightest |
| 2 | Groove: true black | 66% | ≥ 40% |
| 2 | Groove: white-hot | 0.49% | 0.05–1% |
| 2 | Groove: hue families | 1 (violet) | ≤ 2 |
| 3 | Brightest 0.5% of mask pixels, centroid travel in 1 s | 20.5% of face width | ≥ 2% |
| 4 | Eye brightness at kick +50 ms | +60% | ≥ +50% |
| 4 | Eye brightness at +400 ms | 1.06× rest | back to groove level |
| 4 | Black-floor rise on the kick | 0 codes | ≤ 2 codes |
| 5 | Mirror difference, quiet and groove | 0.9% of pixels | < 3% |
| 7 | `arsenal/presets.py` problems | none | none |

- **Item 2:** the face reads in a quarter-size thumbnail; that's the reviewer's call.
- **Item 3:** the silhouette can't move, because the mask's shape functions take no time input.
- **Item 5:** the measure is my definition: the share of pixels differing from their mirror by more than 16 codes.
- **Item 6:** the mask is drawn over the fan, so beams appear only around the silhouette.
- **Item 7, licence line:** it finds zero hits in my files, after I rewrote four textbook idioms it flagged; one exempt signature remains in the composed kit. The command still exits 1, because 131 breaches already on master stay unchanged (the 13 older `vj-*.frag` files, `vj.js`, `vj-fx.js`, `vj-core.js`, `preset-gl.js`, `chordsense.py`). Someone needs to own those.

**Other checks**
- `tests/vj_show.test.mjs` passes 18/18; the Python preset tests pass.
- `vj2_verify --phase sets` passes all 13 checks, including flash gate 3, measured 1, and no flashes of its own. Its new-set list is hard-coded, so I added Guardian temporarily for the run and reverted that edit. The wave-2 page lane should add it for real.
- It also renders correctly in the live page today (strip v1, demo, look pass on) and in Play.

**Below the headline scorecard**
- **Violet groove lit:** 2.2%, against 5–25%. The same scene reaches 6.9–7.7% in teal or green.
- **Violet drop lit:** 9–10%, against 15–45%. The red and gold palette reaches 21%.
- Blue carries little weight in luma, which is what "lit" measures. The planned bloom in the page's new look should lift both, but that's untested.

**How it answers each reference**
- **Q20:** violet LED eyes in black chrome, between six dim tracery panels on knob k6.
- **Q01:** a halo of 32 arc segments with bulbs, chasing down one mirrored pair per beat.
- **Q04 and Q03:** a crown of fins inside the halo; the fan opening on the drop echoes Q03's feather fan, and the brass break carries Q04's warmth. There is no flame halo; that is a gap.
- **Q07:** the beam fan opens from behind the head and the mask hides its origin.
- **D04 and D07:** the mask is the stage centre; the Defqon red and gold drop is on the sheet.
- **Q25:** tube lights travel across the still metal on a clock kept in the feedback buffer, so a knob or a build changes the speed without the light jumping.

**Cost (estimate from an operation count)**
- About 830 operations per pixel on average in the groove and about 1,010 in the drop.
- Averaged over the mask's box that is about 1,540, close to the spec's 1,500, and about 330 outside it, against the spec's 400.
- Pixels actually on the mask cost about 3,400, because each of the four normal taps is about 600 operations; the spec assumed 200.
- On an RX 6600-class card at 1080p that should be about 0.65–0.95 ms in the groove and 0.8–1.2 ms in the drop. It has no raymarch and only 2-iteration loops.
- On SwiftShader (a CPU ranking, not a GPU number) it takes 172–191 ms per frame, alongside Reactor at 170 and Liquid Chrome at 180, and below Laser Cathedral at 282 and Lissajous Chords at 504. The first frame takes 131 ms, a one-off compile.
- All 8 knobs are already assigned by the spec, so the quality control is a compile-time `QUALITY` constant: 3 taps saves about 10%, and dome-only shading brings the average to about 350.

**Caveats**
- The strip v2 reader follows the brief's table exactly: row 2, texels 9–13, version 2, HDR output only when the float-target flag is set. If the look v2 lane changes that layout, the reader must follow.
- The light clock lives in the alpha of the three bottom-left pixels and the beam trail in alpha elsewhere. That is safe while the composite ignores set alpha.
- Pad 2 "native" only takes effect once the page's new accent overlay honours the header.
- Under strip v1 there are no sections, so the drop look comes only from pads 5–8.

**With more time**
- Q20-level sculpting: self-shadowing and a cavity term (the curvature the four taps already sample), and a flame or feather option for the halo.
- Cut the relief to about 250 operations per tap.
- Recompose with the coming `tmStage`, `draw2/sigil` and `light/beam` modules.
- Re-score on the planned headline receipt with real section marks.
- Take a real GPU timing on Daniel's card, with his OK.
